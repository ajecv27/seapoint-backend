import 'dart:convert';

import 'package:flutter/foundation.dart';

import 'trip_recorder.dart';

/// Only local trip measurements are stored here. No route or track is uploaded.
class TripRecovery {
  const TripRecovery(
      {required this.recorder,
      required this.route,
      required this.savedAt,
      required this.activeLeg,
      required this.arrived,
      required this.validJournal,
      required this.partial});

  final TripRecorder recorder;
  final List<List<double>> route; // latitude, longitude
  final DateTime savedAt;
  final int activeLeg;
  final bool arrived;
  final String validJournal;
  final bool partial;
}

/// An append-only journal can recover its complete prefix after an interrupted
/// write. Replay uses the original receipt times and the same GPS filters.
class TripJournal {
  static const maximumBytes = 64 * 1024 * 1024;
  static const maximumRoutePoints = 20000;

  static String _line(Map<String, Object?> event) => '${jsonEncode(event)}\n';
  static int _epoch(DateTime time) => time.toUtc().millisecondsSinceEpoch;

  static String start(DateTime time, List<List<double>> route,
      {GpsFix? initialFix}) {
    _route(route);
    return _line({
      'v': 1,
      'event': 'start',
      'at': _epoch(time),
      'route': route,
      'fix': initialFix == null ? null : _encodeFix(initialFix)
    });
  }

  static String fix(GpsFix fix, DateTime receivedAt, int leg, bool arrived) =>
      _line({
        'event': 'fix',
        'at': _epoch(receivedAt),
        'fix': _encodeFix(fix),
        'leg': leg,
        'arrived': arrived
      });

  static String clock(DateTime time, int leg, bool arrived) => _line(
      {'event': 'clock', 'at': _epoch(time), 'leg': leg, 'arrived': arrived});

  static String resume(DateTime time) =>
      _line({'event': 'resume', 'at': _epoch(time)});
  static String stop(DateTime time) =>
      _line({'event': 'stop', 'at': _epoch(time)});

  static Map<String, Object?> _encodeFix(GpsFix fix) {
    double? finite(double? value) =>
        value != null && value.isFinite ? value : null;
    return {
      'lat': fix.latitude,
      'lon': fix.longitude,
      'at': _epoch(fix.timestamp),
      'accuracy': fix.accuracyMetres,
      'speed': finite(fix.speedMetresPerSecond),
      'speedAccuracy': finite(fix.speedAccuracyMetresPerSecond),
      'course': finite(fix.courseDegrees),
      'courseAccuracy': finite(fix.courseAccuracyDegrees)
    };
  }

  static double _number(Object? value) {
    if (value is! num || !value.isFinite) {
      throw const FormatException('Invalid trip measurement');
    }
    return value.toDouble();
  }

  static DateTime _time(Object? value) {
    if (value is! int || value < 0 || value > 253402300799999) {
      throw const FormatException('Invalid trip time');
    }
    return DateTime.fromMillisecondsSinceEpoch(value, isUtc: true);
  }

  static List<List<double>> _route(Object? value) {
    if (value is! List ||
        value.length < 2 ||
        value.length > maximumRoutePoints) {
      throw const FormatException('Invalid saved route');
    }
    return value.map((point) {
      if (point is! List || point.length != 2) {
        throw const FormatException('Invalid route point');
      }
      final lat = _number(point[0]), lon = _number(point[1]);
      if (lat.abs() > 90 || lon.abs() > 180) {
        throw const FormatException('Invalid route coordinates');
      }
      return [lat, lon];
    }).toList(growable: false);
  }

  static GpsFix _decodeFix(Object? value) {
    if (value is! Map) throw const FormatException('Invalid saved GPS fix');
    double? optional(String key) =>
        value[key] == null ? null : _number(value[key]);
    return GpsFix(
        latitude: _number(value['lat']),
        longitude: _number(value['lon']),
        timestamp: _time(value['at']),
        accuracyMetres: _number(value['accuracy']),
        speedMetresPerSecond: optional('speed'),
        speedAccuracyMetresPerSecond: optional('speedAccuracy'),
        courseDegrees: optional('course'),
        courseAccuracyDegrees: optional('courseAccuracy'));
  }

  static TripRecovery recover(String text) {
    if (text.length > maximumBytes || utf8.encode(text).length > maximumBytes) {
      throw const FormatException('Saved trip exceeds storage limit');
    }
    final lines = const LineSplitter().convert(text);
    if (lines.isEmpty) throw const FormatException('Empty saved trip');
    final first = jsonDecode(lines.first);
    if (first is! Map || first['v'] != 1 || first['event'] != 'start') {
      throw const FormatException('Unsupported saved trip');
    }
    final route = _route(first['route']);
    var savedAt = _time(first['at']);
    var recorder = TripRecorder();
    recorder.start(savedAt,
        initialFix: first['fix'] == null ? null : _decodeFix(first['fix']));
    if (first['fix'] != null && recorder.lastAcceptedFix == null) {
      throw const FormatException('Invalid initial saved GPS fix');
    }
    var leg = 0;
    var arrived = false;
    var partial = false;
    final valid = StringBuffer('${lines.first}\n');
    for (final line in lines.skip(1)) {
      try {
        final event = jsonDecode(line);
        if (event is! Map || !recorder.running) {
          throw const FormatException('Unexpected trip event');
        }
        final at = _time(event['at']);
        if (at.isBefore(savedAt)) {
          throw const FormatException('Trip time moved backwards');
        }
        final hasLeg = event['event'] == 'fix' || event['event'] == 'clock';
        final nextLeg = hasLeg ? event['leg'] : leg;
        final nextArrived = hasLeg ? event['arrived'] : arrived;
        if (nextLeg is! int ||
            nextLeg < 0 ||
            nextLeg > route.length - 2 ||
            nextArrived is! bool) {
          throw const FormatException('Invalid saved route progress');
        }
        switch (event['event']) {
          case 'fix':
            if (!recorder.addFix(_decodeFix(event['fix']), now: at)) {
              throw const FormatException('Saved GPS fix failed validation');
            }
            break;
          case 'clock':
            recorder.snapshot(at);
            break;
          case 'resume':
            recorder.snapshot(at);
            recorder.resumeAfterInterruption();
            break;
          case 'stop':
            recorder.stop(at);
            break;
          default:
            throw const FormatException('Unknown saved trip event');
        }
        savedAt = at;
        leg = nextLeg;
        arrived = nextArrived;
        valid.writeln(line);
      } on FormatException {
        // Do not join points across a corrupt/truncated record or accept later
        // records after it. The recoverable prefix remains available.
        partial = true;
        recorder = recover(valid.toString()).recorder;
        break;
      }
    }
    return TripRecovery(
        recorder: recorder,
        route: route,
        savedAt: savedAt,
        activeLeg: leg,
        arrived: arrived,
        validJournal: valid.toString(),
        partial: partial);
  }
}

abstract class TripStorage {
  Future<String?> read();
  Future<void> replace(String record);
  Future<void> append(String record);
  Future<void> complete();
  Future<void> discard();
}

/// Serialize writes so a slow save cannot overtake a stop or a new trip.
/// A failed append seals that journal until recovery or a new trip; later
/// records must never be appended after a possibly truncated line.
class TripStore {
  TripStore(this.storage);
  final TripStorage storage;
  Future<void> _pending = Future.value();
  bool _open = false;
  bool _faulted = false;

  Future<void> _queue(Future<void> Function() action) {
    final result = _pending.then((_) => action());
    _pending = result.catchError((Object _) {
      _faulted = true;
    });
    return result;
  }

  Future<TripRecovery?> load() async {
    await _pending;
    final text = await storage.read();
    if (text == null) return null;
    final saved = await compute(TripJournal.recover, text,
        debugLabel: 'SeaPoint trip recovery');
    _open = saved.recorder.running;
    return saved;
  }

  Future<void> begin(String record) => _queue(() async {
        _open = false;
        await storage.replace(record);
        _faulted = false;
        _open = true;
      });

  void _requireOpen() {
    if (!_open || _faulted) throw StateError('Trip saving unavailable');
  }

  Future<void> record(String record) => _queue(() async {
        _requireOpen();
        await storage.append(record);
      });

  Future<void> resume(TripRecovery saved, DateTime now) => _queue(() async {
        // Replacing from the validated prefix also removes any incomplete tail.
        await storage.replace(saved.validJournal);
        _faulted = false;
        _open = true;
        await storage.append(TripJournal.resume(now));
      });

  Future<void> finish(DateTime at) => _queue(() async {
        _requireOpen();
        await storage.append(TripJournal.stop(at));
        _open = false;
        await storage.complete();
      });

  Future<void> finishRecovered(TripRecovery saved) => _queue(() async {
        await storage.replace(saved.validJournal);
        _faulted = false;
        await storage.append(TripJournal.stop(saved.savedAt));
        _open = false;
        await storage.complete();
      });

  Future<void> discard() => _queue(() async {
        await storage.discard();
        _open = false;
        _faulted = false;
      });
}
