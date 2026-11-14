import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

DateTime _tideDay(DateTime value) {
  final local = value.toUtc().subtract(const Duration(hours: 4));
  return DateTime.utc(local.year, local.month, local.day, 4);
}

bool shouldCheckTides({
  required DateTime now,
  required DateTime? checkedAt,
  required DateTime? attemptedAt,
}) {
  if (checkedAt != null && _tideDay(checkedAt) == _tideDay(now)) {
    return false;
  }
  return attemptedAt == null ||
      now.difference(attemptedAt) >= const Duration(minutes: 10);
}

class TidePredictionResult {
  const TidePredictionResult(
      this.payload, this.coversForecast, this.notice, this.checkedAt);
  final Map<String, dynamic>? payload;
  final bool coversForecast;
  final String? notice;
  final DateTime checkedAt;
}

class TidePredictionClient {
  TidePredictionClient({
    http.Client? client,
    Future<SharedPreferences> Function()? preferences,
    DateTime Function()? clock,
    String Function()? createId,
  })  : _client = client,
        _preferences = preferences ?? SharedPreferences.getInstance,
        _clock = clock ?? DateTime.now,
        _createId = createId ?? _randomId;

  static const _identityKey = 'seapoint_tide_installation_v1';
  static const _creditPauseKey = 'seapoint_tide_provider_retry_at_v2';
  static const unavailableNotice = 'Tide updates temporarily unavailable';
  final http.Client? _client;
  final Future<SharedPreferences> Function() _preferences;
  final DateTime Function() _clock;
  final String Function() _createId;
  final _inflight = <String, Future<TidePredictionResult>>{};
  Future<String>? _identity;

  static String _randomId() {
    final random = Random.secure();
    return List.generate(
            16, (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'))
        .join();
  }

  Future<String> _installation(SharedPreferences prefs) =>
      _identity ??= (() async {
        var value = prefs.getString(_identityKey);
        if (value == null || !RegExp(r'^[a-f0-9]{32}$').hasMatch(value)) {
          value = _createId();
          if (!RegExp(r'^[a-f0-9]{32}$').hasMatch(value)) {
            throw const FormatException('Invalid tide installation identifier');
          }
          if (!await prefs.setString(_identityKey, value)) {
            throw StateError('Could not retain tide installation identifier');
          }
        }
        return value;
      })();

  Future<TidePredictionResult> load(Uri uri,
      {required String cacheKey, bool retryPaused = false}) {
    final current = _inflight[cacheKey];
    if (current != null) return current;
    final request = _load(uri, cacheKey, retryPaused);
    _inflight[cacheKey] = request;
    return request.whenComplete(() => _inflight.remove(cacheKey));
  }

  bool _covers(Map<String, dynamic>? payload, DateTime now) {
    if (payload == null) return false;
    final start = payload['coverage_start'];
    final end = payload['coverage_end'];
    final day = _tideDay(now).millisecondsSinceEpoch ~/ 1000;
    return start is num && end is num && start <= day && end >= day + 7 * 86400;
  }

  Map<String, dynamic>? _cached(
      SharedPreferences prefs, String key, DateTime now) {
    final raw = prefs.getString(key);
    final saved = prefs.getInt('${key}_saved_at');
    if (raw == null || saved == null || saved > now.millisecondsSinceEpoch) {
      return null;
    }
    try {
      final data = jsonDecode(raw);
      if (data is! Map<String, dynamic> ||
          data['ok'] != true ||
          data['extremes'] is! List) {
        return null;
      }
      // Migrate the existing phone cache using the original retrieval time.
      // Re-reading a saved prediction must never extend its date coverage.
      final day = _tideDay(DateTime.fromMillisecondsSinceEpoch(saved));
      data['coverage_start'] ??= day.millisecondsSinceEpoch ~/ 1000;
      data['coverage_end'] ??=
          day.add(const Duration(days: 7)).millisecondsSinceEpoch ~/ 1000;
      data['fetched_at'] ??= saved ~/ 1000;
      final end = data['coverage_end'];
      return end is num && end > now.millisecondsSinceEpoch ~/ 1000
          ? data
          : null;
    } on FormatException {
      return null;
    }
  }

  Future<TidePredictionResult> _load(
      Uri uri, String key, bool retryPaused) async {
    final prefs = await _preferences();
    final now = _clock();
    final seconds = now.millisecondsSinceEpoch ~/ 1000;
    final saved = _cached(prefs, key, now);
    if (_covers(saved, now)) {
      return TidePredictionResult(saved, true, null, now);
    }
    final globalPause = prefs.getInt(_creditPauseKey) ?? 0;
    final locationPause = prefs.getInt('${key}_retry_at_v2') ?? 0;
    if (!retryPaused && (globalPause > seconds || locationPause > seconds)) {
      return TidePredictionResult(saved, false, unavailableNotice, now);
    }
    final connection = _client ?? http.Client();
    try {
      final identity = await _installation(prefs);
      final response = await connection.get(uri, headers: {
        'X-SeaPoint-Tide-Client': identity,
        if (retryPaused) 'X-SeaPoint-Tide-Probe': '1',
      }).timeout(const Duration(seconds: 30));
      final dynamic decoded = jsonDecode(response.body);
      final data =
          decoded is Map<String, dynamic> ? decoded : <String, dynamic>{};
      final retry = data['retry_at'];
      final retryAt = retry is num
          ? retry.toInt().clamp(seconds + 60, seconds + 86400)
          : seconds + 900;
      final reason = data['reason'];
      if (reason == 'credits_exhausted' ||
          reason == 'credentials_unavailable') {
        await prefs.setInt(_creditPauseKey, retryAt);
      }
      if (response.statusCode != 200 ||
          data['ok'] != true ||
          data['extremes'] is! List) {
        await prefs.setInt('${key}_retry_at_v2', retryAt);
        return TidePredictionResult(saved, false, unavailableNotice, _clock());
      }
      if (reason != 'credits_exhausted' &&
          reason != 'credentials_unavailable') {
        await prefs.remove(_creditPauseKey);
      }
      final start = data['coverage_start'];
      final end = data['coverage_end'];
      final fetched = data['fetched_at'];
      if (start is! num ||
          end is! num ||
          fetched is! num ||
          end <= start ||
          end - start > 8 * 86400 ||
          fetched > seconds + 60) {
        throw const FormatException('Invalid tide coverage');
      }
      final receivedAt = _clock();
      final complete = _covers(data, receivedAt);
      if (!complete) {
        await prefs.setInt('${key}_retry_at_v2', retryAt);
      }
      await prefs.setString(key, jsonEncode(data));
      await prefs.setInt('${key}_saved_at', fetched.toInt() * 1000);
      if (complete) {
        await prefs.remove('${key}_retry_at_v2');
      }
      return TidePredictionResult(
          data, complete, complete ? null : unavailableNotice, receivedAt);
    } catch (_) {
      await prefs.setInt('${key}_retry_at_v2', seconds + 900);
      return TidePredictionResult(saved, false, unavailableNotice, _clock());
    } finally {
      if (_client == null) connection.close();
    }
  }
}
