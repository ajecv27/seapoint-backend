import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:seapoint/trip_journal.dart';
import 'package:seapoint/trip_recorder.dart';
import 'package:seapoint/trip_storage_io.dart';

void main() {
  final start = DateTime.utc(2026, 11, 14, 12);
  final route = [
    [0.0, 0.0],
    [0.0, .1]
  ];
  DateTime at(int seconds) => start.add(Duration(seconds: seconds));
  GpsFix fix(int seconds, {double? metres}) => GpsFix(
      latitude: 0,
      longitude: (metres ?? seconds * 10) / 6371008.8 * 180 / 3.141592653589793,
      timestamp: at(seconds),
      accuracyMetres: 2,
      speedMetresPerSecond: 10,
      speedAccuracyMetresPerSecond: .2,
      courseDegrees: 90,
      courseAccuracyDegrees: 5);
  String journal() =>
      TripJournal.start(start, route, initialFix: fix(0)) +
      TripJournal.fix(fix(10), at(10), 0, false) +
      TripJournal.fix(fix(20), at(20), 0, false);

  test('replay preserves measured track, knots, heading and completed summary',
      () {
    final saved = TripJournal.recover(journal() + TripJournal.stop(at(30)));
    final summary = saved.recorder.snapshot(at(9000));
    expect(saved.recorder.running, false);
    expect(summary.elapsed, const Duration(seconds: 30));
    expect(summary.distanceNm, closeTo(200 / 1852, 1e-9));
    expect(summary.maximumSpeedKnots, closeTo(10 * 3600 / 1852, 1e-9));
    expect(summary.averageSpeedKnots, closeTo(200 / 1852 * 120, 1e-9));
    expect(summary.acceptedFixCount, 3);
    expect(saved.recorder.segments.single.length, 3);
    expect(saved.partial, false);
  });

  test('resuming never joins unrecorded travel even after a brief restart', () {
    final text = journal() +
        TripJournal.resume(at(21)) +
        TripJournal.fix(fix(22, metres: 10000), at(22), 0, false) +
        TripJournal.fix(fix(23, metres: 10010), at(23), 0, false);
    final saved = TripJournal.recover(text);
    expect(saved.recorder.distanceNm, closeTo(210 / 1852, 1e-9));
    expect(saved.recorder.segments.length, 2);
    expect(saved.recorder.snapshot(at(23)).gpsGapCount, 1);
    expect(saved.recorder.snapshot(at(23)).maximumSpeedKnots,
        closeTo(10 * 3600 / 1852, 1e-9));
  });

  test('interrupted tail recovers prefix and finishing uses the saved clock',
      () {
    final saved = TripJournal.recover(
        '${journal()}${TripJournal.clock(at(25), 0, false)}{"event":"fix"');
    expect(saved.partial, true);
    expect(saved.savedAt, at(25));
    expect(saved.recorder.stop(saved.savedAt).elapsed,
        const Duration(seconds: 25));
    expect(
        saved.recorder.snapshot(at(3600)).elapsed, const Duration(seconds: 25));
  });

  test(
      'bad fixes and middle corruption cannot advance time or add later travel',
      () {
    final invalid = GpsFix(
        latitude: 95, longitude: 0, timestamp: at(1000), accuracyMetres: 2);
    for (final tail in [
      TripJournal.fix(invalid, at(1000), 0, false),
      '{bad json}\n',
      '{"event":"clock","at":0,"leg":0,"arrived":false}\n',
    ]) {
      final saved = TripJournal.recover(
          journal() + tail + TripJournal.clock(at(2000), 0, false));
      expect(saved.partial, true);
      expect(saved.recorder.stop(saved.savedAt).elapsed,
          const Duration(seconds: 20));
      expect(saved.recorder.distanceNm, closeTo(200 / 1852, 1e-9));
    }
  });

  test('unsupported headers and malformed routes are rejected', () {
    for (final text in [
      '',
      '{}\n',
      '{"v":2,"event":"start"}\n',
      '{"v":1,"event":"start","at":1794657600000,"route":[[95,0],[0,0]]}\n'
    ]) {
      expect(() => TripJournal.recover(text), throwsFormatException);
    }
  });

  test('route progress survives replay and stale speed clears on resume', () {
    final saved =
        TripJournal.recover(journal() + TripJournal.clock(at(21), 0, true));
    expect(saved.arrived, true);
    expect(saved.recorder.snapshot(at(21)).currentSpeedKnots, isNotNull);
    saved.recorder.resumeAfterInterruption();
    expect(saved.recorder.snapshot(at(21)).currentSpeedKnots, isNull);
    expect(saved.recorder.snapshot(at(21)).gpsHeadingDegrees, isNull);
  });

  test('save queue preserves start, fixes and stop across slow storage',
      () async {
    final gate = Completer<void>();
    final storage = MemoryStorage()..gate = gate;
    final store = TripStore(storage);
    final begin =
        store.begin(TripJournal.start(start, route, initialFix: fix(0)));
    final point = store.record(TripJournal.fix(fix(10), at(10), 0, false));
    final end = store.finish(at(20));
    await Future<void>.delayed(Duration.zero);
    expect(storage.operations, ['replace']);
    gate.complete();
    await Future.wait([begin, point, end]);
    expect(storage.operations, ['replace', 'append', 'append', 'complete']);
    final saved = await TripStore(storage).load();
    expect(saved!.recorder.snapshot(at(1000)).elapsed,
        const Duration(seconds: 20));
  });

  test('failed appends seal the journal; validated recovery repairs its tail',
      () async {
    final storage = MemoryStorage();
    final store = TripStore(storage);
    await store.begin(journal());
    storage.failAppend = true;
    await expectLater(
        store.record(TripJournal.clock(at(25), 0, false)), throwsStateError);
    final damaged = storage.text;
    await expectLater(
        store.record(TripJournal.clock(at(26), 0, false)), throwsStateError);
    expect(storage.text, damaged);
    storage.failAppend = false;
    final restarted = TripStore(storage);
    final saved = (await restarted.load())!;
    expect(saved.partial, true);
    await restarted.resume(saved, at(30));
    await restarted
        .record(TripJournal.fix(fix(31, metres: 10000), at(31), 0, false));
    final repaired = (await TripStore(storage).load())!;
    expect(repaired.partial, false);
    expect(repaired.recorder.distanceNm, closeTo(200 / 1852, 1e-9));
    expect(repaired.recorder.segments.length, 2);
  });

  test(
      'finishing a recovered trip excludes time away and preserves its saved readings',
      () async {
    final storage = MemoryStorage()..text = journal();
    final store = TripStore(storage);
    final saved = (await store.load())!;
    final before = saved.recorder.snapshot(saved.savedAt);
    await store.finishRecovered(saved);
    final restored = (await TripStore(storage).load())!;
    final after = restored.recorder.snapshot(at(36000));
    expect(after.elapsed, before.elapsed);
    expect(after.currentSpeedKnots, before.currentSpeedKnots);
    expect(after.gpsHeadingDegrees, before.gpsHeadingDegrees);
    expect(after.maximumSpeedKnots, before.maximumSpeedKnots);
    expect(after.averageSpeedKnots, before.averageSpeedKnots);
  });

  group('real private files', () {
    late Directory directory;
    setUp(() async {
      directory = await Directory.systemTemp.createTemp('seapoint-trip-test-');
    });
    tearDown(() async {
      await directory.delete(recursive: true);
    });

    test('new instances recover active and last completed trips from disk',
        () async {
      final first = TripStore(FileTripStorage(directory));
      await first.begin(journal());
      final active = (await TripStore(FileTripStorage(directory)).load())!;
      expect(active.recorder.running, true);
      await first.finish(at(30));
      final done = (await TripStore(FileTripStorage(directory)).load())!;
      expect(done.recorder.running, false);
      expect(done.recorder.snapshot(at(10000)).elapsed,
          const Duration(seconds: 30));
      final next = TripStore(FileTripStorage(directory));
      await next.begin(TripJournal.start(at(100), route));
      await next.discard();
      final previous = (await TripStore(FileTripStorage(directory)).load())!;
      expect(previous.recorder.running, false);
      expect(previous.recorder.snapshot(at(10000)).distanceNm,
          closeTo(200 / 1852, 1e-9));
    });

    test('abandoned staging file cannot replace a valid saved trip', () async {
      final first = TripStore(FileTripStorage(directory));
      await first.begin(journal());
      await File('${directory.path}/active-v1.next').writeAsString('{broken');
      final saved = (await TripStore(FileTripStorage(directory)).load())!;
      expect(saved.recorder.distanceNm, closeTo(200 / 1852, 1e-9));
      expect(saved.partial, false);
    });

    test('oversized files are refused before reading or overwriting them',
        () async {
      final file = File('${directory.path}/active-v1.jsonl');
      final handle = await file.open(mode: FileMode.write);
      await handle.truncate(TripJournal.maximumBytes + 1);
      await handle.close();
      await expectLater(
          TripStore(FileTripStorage(directory)).load(), throwsFormatException);
      expect(await file.length(), TripJournal.maximumBytes + 1);
    });
  });
}

class MemoryStorage implements TripStorage {
  String? text;
  bool failAppend = false;
  Completer<void>? gate;
  final operations = <String>[];
  @override
  Future<String?> read() async => text;
  @override
  Future<void> replace(String record) async {
    operations.add('replace');
    await gate?.future;
    text = record;
  }

  @override
  Future<void> append(String record) async {
    operations.add('append');
    if (failAppend) {
      text = '${text!}{broken';
      throw StateError('Disk full');
    }
    text = text! + record;
  }

  @override
  Future<void> complete() async {
    operations.add('complete');
  }

  @override
  Future<void> discard() async {
    text = null;
  }
}
