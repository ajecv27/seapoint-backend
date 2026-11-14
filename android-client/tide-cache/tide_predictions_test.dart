import 'dart:async';
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:seapoint/tide_predictions.dart';

void main() {
  var now = DateTime.utc(2026, 11, 14, 16);
  final uri = Uri.parse('https://backend.invalid/tides?lat=17.12&lon=-61.8');
  const key = 'seapoint_tides_17.12000_-61.80000';
  Map<String, dynamic> prediction({bool legacy = false, int count = 28}) {
    final local = now.subtract(const Duration(hours: 4));
    final start = DateTime.utc(local.year, local.month, local.day, 4)
            .millisecondsSinceEpoch ~/
        1000;
    return {
      'ok': true,
      'copyright': 'retained attribution',
      'datum': 'CD',
      'extremes': List.generate(
          count,
          (i) => {
                'dt': start + i * 21600,
                'type': i.isEven ? 'Low' : 'High',
                'height': .3
              }),
      if (!legacy) ...{
        'coverage_start': start,
        'coverage_end': start + 7 * 86400,
        'fetched_at': now.millisecondsSinceEpoch ~/ 1000,
      },
    };
  }

  Future<void> cache(Map<String, dynamic> data) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(key, jsonEncode(data));
    await prefs.setInt('${key}_saved_at', now.millisecondsSinceEpoch);
  }

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    now = DateTime.utc(2026, 11, 14, 16);
  });

  test('legacy saved predictions are reused without extending their dates',
      () async {
    await cache(prediction(legacy: true));
    final prefs = await SharedPreferences.getInstance();
    final original = prefs.getInt('${key}_saved_at');
    var calls = 0;
    final client = TidePredictionClient(
        clock: () => now,
        client: MockClient((_) async {
          calls++;
          return http.Response('{}', 500);
        }));
    now = now.add(const Duration(hours: 6));
    for (var i = 0; i < 4; i++) {
      final result = await client.load(uri, cacheKey: key);
      expect(result.coversForecast, true);
      expect((result.payload!['extremes'] as List).length, 28);
    }
    expect(calls, 0);
    expect(prefs.getInt('${key}_saved_at'), original);
  });

  test('refresh and app restart make only one daily request per location',
      () async {
    var calls = 0;
    final transport = MockClient((request) async {
      expect(
          request.headers['X-SeaPoint-Tide-Client'] ??
              request.headers['x-seapoint-tide-client'],
          'a' * 32);
      calls++;
      return http.Response(jsonEncode(prediction()), 200);
    });
    TidePredictionClient make() => TidePredictionClient(
        clock: () => now, client: transport, createId: () => 'a' * 32);
    final first = make();
    expect((await first.load(uri, cacheKey: key)).coversForecast, true);
    now = now.add(const Duration(hours: 7));
    expect((await first.load(uri, cacheKey: key)).coversForecast, true);
    expect((await make().load(uri, cacheKey: key)).coversForecast, true);
    expect(calls, 1);
  });

  test('new Antigua calendar day fetches the newly displayed seventh day',
      () async {
    var calls = 0;
    final client = TidePredictionClient(
        clock: () => now,
        client: MockClient((_) async {
          calls++;
          return http.Response(jsonEncode(prediction()), 200);
        }));
    await client.load(uri, cacheKey: key);
    now = DateTime.utc(2026, 11, 15, 3, 59);
    await client.load(uri, cacheKey: key);
    expect(calls, 1);
    now = DateTime.utc(2026, 11, 15, 4);
    expect((await client.load(uri, cacheKey: key)).coversForecast, true);
    expect(calls, 2);
  });

  test(
      'a request crossing local midnight does not mark the new window complete',
      () async {
    now = DateTime.utc(2026, 11, 15, 3, 59, 55);
    final previousWindow = prediction();
    final client = TidePredictionClient(
        clock: () => now,
        client: MockClient((_) async {
          now = DateTime.utc(2026, 11, 15, 4, 0, 5);
          return http.Response(jsonEncode(previousWindow), 200);
        }));
    final result = await client.load(uri, cacheKey: key);
    expect(result.coversForecast, false);
    expect(result.checkedAt, now);
  });

  test('switching back to a saved bay reuses that bay prediction', () async {
    var calls = 0;
    final client = TidePredictionClient(
        clock: () => now,
        client: MockClient((_) async {
          calls++;
          return http.Response(jsonEncode(prediction()), 200);
        }));
    await client.load(uri, cacheKey: key);
    await client.load(uri.replace(query: 'lat=17.2&lon=-61.9'),
        cacheKey: 'bay-b');
    await client.load(uri, cacheKey: key);
    expect(calls, 2);
  });

  test('credit pause survives app restart and suppresses other bay requests',
      () async {
    var calls = 0;
    final transport = MockClient((_) async {
      calls++;
      return http.Response(
          jsonEncode({
            'ok': false,
            'reason': 'credits_exhausted',
            'retry_at':
                now.add(const Duration(hours: 6)).millisecondsSinceEpoch ~/ 1000
          }),
          503);
    });
    TidePredictionClient make() =>
        TidePredictionClient(clock: () => now, client: transport);
    expect((await make().load(uri, cacheKey: key)).payload, isNull);
    await make().load(uri, cacheKey: 'bay-b');
    now = now.add(const Duration(hours: 5));
    await make().load(uri, cacheKey: key);
    expect(calls, 1);
  });

  test(
      'failed update retains partial predictions and the original saved timestamp',
      () async {
    await cache(prediction(legacy: true));
    final prefs = await SharedPreferences.getInstance();
    final original = prefs.getString(key);
    final originalTime = prefs.getInt('${key}_saved_at');
    now = now.add(const Duration(days: 2));
    final client = TidePredictionClient(
        clock: () => now,
        client: MockClient((_) async => http.Response('{"ok":false}', 503)));
    final result = await client.load(uri, cacheKey: key);
    expect(result.coversForecast, false);
    expect((result.payload!['extremes'] as List).length, 28);
    expect(result.notice, TidePredictionClient.unavailableNotice);
    expect(prefs.getString(key), original);
    expect(prefs.getInt('${key}_saved_at'), originalTime);
  });

  test('simultaneous refreshes share a single request and installation ID',
      () async {
    var calls = 0, ids = 0;
    final completion = Completer<http.Response>();
    final client = TidePredictionClient(
        clock: () => now,
        createId: () {
          ids++;
          return 'b' * 32;
        },
        client: MockClient((_) {
          calls++;
          return completion.future;
        }));
    final first = client.load(uri, cacheKey: key);
    final second = client.load(uri, cacheKey: key);
    await Future<void>.delayed(const Duration(milliseconds: 10));
    completion.complete(http.Response(jsonEncode(prediction()), 200));
    expect((await first).coversForecast, true);
    expect((await second).coversForecast, true);
    expect(calls, 1);
    expect(ids, 1);
  });

  test(
      'outages, invalid JSON and invalid coverage never replace a saved prediction',
      () async {
    for (final kind in ['network', 'json', 'coverage']) {
      SharedPreferences.setMockInitialValues({});
      now = DateTime.utc(2026, 11, 14, 16);
      await cache(prediction());
      final prefs = await SharedPreferences.getInstance();
      final original = prefs.getString(key);
      now = now.add(const Duration(days: 1));
      var calls = 0;
      final client = TidePredictionClient(
          clock: () => now,
          client: MockClient((_) async {
            calls++;
            if (kind == 'network') throw http.ClientException('test outage');
            if (kind == 'json') {
              return http.Response('<html>outage</html>', 503);
            }
            return http.Response(
                jsonEncode({...prediction(), 'coverage_end': 999999999999}),
                200);
          }));
      expect((await client.load(uri, cacheKey: key)).coversForecast, false);
      await client.load(uri, cacheKey: key);
      expect(calls, 1);
      expect(prefs.getString(key), original);
    }
  });

  test('fully expired saved tides do not pretend to cover new dates', () async {
    await cache(prediction());
    now = now.add(const Duration(days: 8));
    final client = TidePredictionClient(
        clock: () => now,
        client: MockClient((_) async => http.Response('{"ok":false}', 503)));
    expect((await client.load(uri, cacheKey: key)).payload, isNull);
  });

  test('a successful empty event list stays empty and remains cached',
      () async {
    var calls = 0;
    final client = TidePredictionClient(
        clock: () => now,
        client: MockClient((_) async {
          calls++;
          return http.Response(jsonEncode(prediction(count: 0)), 200);
        }));
    final result = await client.load(uri, cacheKey: key);
    expect(result.coversForecast, true);
    expect(result.payload!['extremes'], isEmpty);
    await client.load(uri, cacheKey: key);
    expect(calls, 1);
  });

  test(
      'scheduled refresh follows local calendar days and failed-attempt backoff',
      () {
    expect(
        shouldCheckTides(
            now: now,
            checkedAt: now.subtract(const Duration(hours: 3)),
            attemptedAt: null),
        false);
    expect(
        shouldCheckTides(
            now: now,
            checkedAt: now.subtract(const Duration(days: 1)),
            attemptedAt: null),
        true);
    expect(
        shouldCheckTides(
            now: now,
            checkedAt: null,
            attemptedAt: now.subtract(const Duration(minutes: 2))),
        false);
  });
  test(
      'manual refresh can recheck a paused provider without repurchasing a valid forecast',
      () async {
    var calls = 0;
    final transport = MockClient((request) async {
      calls++;
      if (calls == 1) {
        return http.Response(
            jsonEncode({
              'ok': false,
              'reason': 'credits_exhausted',
              'retry_at':
                  now.add(const Duration(hours: 6)).millisecondsSinceEpoch ~/
                      1000
            }),
            503);
      }
      expect(
          request.headers['X-SeaPoint-Tide-Probe'] ??
              request.headers['x-seapoint-tide-probe'],
          '1');
      return http.Response(jsonEncode(prediction()), 200);
    });
    final client = TidePredictionClient(clock: () => now, client: transport);
    await client.load(uri, cacheKey: key);
    now = now.add(const Duration(minutes: 2));
    expect(
        (await client.load(uri, cacheKey: key, retryPaused: true))
            .coversForecast,
        true);
    expect(
        (await SharedPreferences.getInstance())
            .getInt('seapoint_tide_provider_retry_at_v2'),
        isNull);
    await client.load(uri, cacheKey: key, retryPaused: true);
    expect(calls, 2);
  });
}
