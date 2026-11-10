import 'package:flutter_test/flutter_test.dart';
import 'package:seapoint/trip_recorder.dart';

void main() {
  final start = DateTime.utc(2026, 11, 9, 12);
  GpsFix fix(
    double metresEast,
    int seconds, {
    double accuracy = 2,
    double? speed = 10,
    double? speedAccuracy = .2,
    double? course = 90,
  }) =>
      GpsFix(
        latitude: 0,
        longitude: metresEast / 6371008.8 * 180 / 3.141592653589793,
        timestamp: start.add(Duration(seconds: seconds)),
        accuracyMetres: accuracy,
        speedMetresPerSecond: speed,
        speedAccuracyMetresPerSecond: speedAccuracy,
        courseDegrees: course,
        courseAccuracyDegrees: 5,
      );

  test('records actual distance and reports knots and GPS course', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0));
    for (var seconds = 10; seconds <= 40; seconds += 10) {
      expect(
        recorder.addFix(
          fix(seconds * 10, seconds),
          now: start.add(Duration(seconds: seconds)),
        ),
        isTrue,
      );
    }
    final result = recorder.snapshot(start.add(const Duration(seconds: 40)));
    expect(result.distanceNm, closeTo(400 / 1852, .000001));
    expect(result.currentSpeedKnots, closeTo(10 * 3600 / 1852, .000001));
    expect(result.maximumSpeedKnots, closeTo(10 * 3600 / 1852, .000001));
    expect(result.gpsHeadingDegrees, 90);
    expect(result.recordedLegCount, 4);
    expect(recorder.segments.single.length, 5);
  });

  test('overall average includes stopped time; stopping freezes summary', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0));
    recorder.addFix(fix(100, 10), now: start.add(const Duration(seconds: 10)));
    final result = recorder.stop(start.add(const Duration(seconds: 20)));
    expect(result.elapsed, const Duration(seconds: 20));
    expect(result.averageSpeedKnots, closeTo(100 / 1852 * 3600 / 20, .000001));
    expect(result.endedAt, start.add(const Duration(seconds: 20)));
    expect(
      recorder.snapshot(start.add(const Duration(hours: 1))),
      same(result),
    );
    expect(recorder.stop(start.add(const Duration(hours: 1))), same(result));
    expect(
      recorder.addFix(
        fix(200, 30),
        now: start.add(const Duration(seconds: 30)),
      ),
      isFalse,
    );
    expect(recorder.distanceNm, result.distanceNm);
  });

  test(
    'poor, stale, future, malformed and out-of-order fixes are rejected',
    () {
      final recorder = TripRecorder();
      recorder.start(start, initialFix: fix(0, 0));
      expect(
        recorder.addFix(
          fix(10, 1, accuracy: 200),
          now: start.add(const Duration(seconds: 1)),
        ),
        isFalse,
      );
      expect(
        recorder.addFix(
          fix(10, 1),
          now: start.add(const Duration(seconds: 12)),
        ),
        isFalse,
      );
      expect(
        recorder.addFix(
          fix(10, 20),
          now: start.add(const Duration(seconds: 12)),
        ),
        isFalse,
      );
      expect(
        recorder.addFix(
          GpsFix(
            latitude: double.nan,
            longitude: 0,
            timestamp: start.add(const Duration(seconds: 12)),
            accuracyMetres: 2,
          ),
          now: start.add(const Duration(seconds: 12)),
        ),
        isFalse,
      );
      expect(
        recorder.addFix(
          fix(140, 14),
          now: start.add(const Duration(seconds: 14)),
        ),
        isTrue,
      );
      expect(
        recorder.addFix(
          fix(130, 13),
          now: start.add(const Duration(seconds: 14)),
        ),
        isFalse,
      );
      expect(
        recorder
            .snapshot(start.add(const Duration(seconds: 14)))
            .acceptedFixCount,
        2,
      );
    },
  );

  test('teleports do not create a black trail or speed record', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0, speed: 0));
    expect(
      recorder.addFix(
        fix(5000, 1, speed: 0),
        now: start.add(const Duration(seconds: 1)),
      ),
      isFalse,
    );
    expect(recorder.distanceNm, 0);
    expect(
      recorder
          .snapshot(start.add(const Duration(seconds: 1)))
          .maximumSpeedKnots,
      isNull,
    );
    expect(recorder.lastAcceptedFix!.longitude, 0);
  });

  test('GPS stationary jitter does not accumulate distance or false peaks', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0, accuracy: 5, speed: 0));
    for (var second = 1; second <= 20; second++) {
      recorder.addFix(
        fix(second.isEven ? 2 : -2, second, accuracy: 5, speed: 0),
        now: start.add(Duration(seconds: second)),
      );
    }
    final result = recorder.snapshot(start.add(const Duration(seconds: 20)));
    expect(result.distanceNm, 0);
    expect(result.maximumSpeedKnots, isNull);
    expect(result.currentSpeedKnots, 0);
    expect(result.gpsHeadingDegrees, isNull);
    expect(result.recordedLegCount, 0);
  });

  test(
    'reliable zero velocity rejects a contradictory GPS coordinate jump',
    () {
      final recorder = TripRecorder();
      recorder.start(start, initialFix: fix(0, 0, speed: 0));
      expect(
        recorder.addFix(
          fix(20, 1, speed: 0),
          now: start.add(const Duration(seconds: 1)),
        ),
        isFalse,
      );
      expect(recorder.distanceNm, 0);
      expect(
        recorder
            .snapshot(start.add(const Duration(seconds: 1)))
            .maximumSpeedKnots,
        isNull,
      );
    },
  );

  test('uncertain stationary fixes without GPS speed do not add travel', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0, accuracy: 10, speed: null));
    for (var second = 1; second <= 20; second++) {
      recorder.addFix(
        fix(second.isEven ? 10 : -10, second, accuracy: 10, speed: null),
        now: start.add(Duration(seconds: second)),
      );
    }
    final result = recorder.snapshot(start.add(const Duration(seconds: 20)));
    expect(result.distanceNm, 0);
    expect(result.maximumSpeedKnots, isNull);
    expect(result.gpsHeadingDegrees, isNull);
  });

  test('trusted zero speed prevents gradual GPS drift from adding travel', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0, speed: 0));
    for (var second = 1; second <= 20; second++) {
      recorder.addFix(
        fix(second.toDouble(), second, speed: 0),
        now: start.add(Duration(seconds: second)),
      );
    }
    final result = recorder.snapshot(start.add(const Duration(seconds: 20)));
    expect(result.distanceNm, 0);
    expect(result.recordedLegCount, 0);
    expect(result.maximumSpeedKnots, isNull);
  });

  test('decelerating to zero still records the final stop location', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0, speed: 10));
    expect(
      recorder.addFix(
        fix(50, 10, speed: 0),
        now: start.add(const Duration(seconds: 10)),
      ),
      isTrue,
    );
    final result = recorder.snapshot(start.add(const Duration(seconds: 10)));
    expect(result.distanceNm, closeTo(50 / 1852, .000001));
    expect(result.currentSpeedKnots, 0);
    expect(result.recordedLegCount, 1);
  });

  test('resuming travel cannot count previously suppressed stationary drift',
      () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0, speed: 0));
    for (var second = 1; second <= 20; second++) {
      recorder.addFix(
        fix(second.toDouble(), second, speed: 0),
        now: start.add(Duration(seconds: second)),
      );
    }
    recorder.addFix(
      fix(21, 21, speed: 1),
      now: start.add(const Duration(seconds: 21)),
    );
    expect(recorder.distanceNm, 0);
    recorder.addFix(
      fix(24, 24, speed: 1),
      now: start.add(const Duration(seconds: 24)),
    );
    expect(recorder.distanceNm, closeTo(4 / 1852, .000001));
    expect(recorder.segments.length, 2);
    expect(
      recorder.snapshot(start.add(const Duration(seconds: 24))).gpsGapCount,
      0,
    );
  });

  test('repeated course without fresh speed cannot prolong GPS heading', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0));
    for (var second = 1; second <= 11; second++) {
      recorder.addFix(
        fix(0, second, speed: null),
        now: start.add(Duration(seconds: second)),
      );
    }
    final result = recorder.snapshot(start.add(const Duration(seconds: 11)));
    expect(result.currentSpeedKnots, isNull);
    expect(result.gpsHeadingDegrees, isNull);
  });

  test('a cached fix before start cannot count travel before the trip', () {
    final recorder = TripRecorder();
    final tripStart = start.add(const Duration(seconds: 10));
    recorder.start(tripStart, initialFix: fix(0, 0));
    expect(recorder.lastAcceptedFix, isNull);
    expect(recorder.addFix(fix(100, 10), now: tripStart), isTrue);
    final result = recorder.snapshot(tripStart);
    expect(result.distanceNm, 0);
    expect(result.elapsed, Duration.zero);
    expect(recorder.segments.single.length, 1);
  });

  test('an initial velocity does not become a maximum before movement', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0, speed: 60));
    final result = recorder.snapshot(start);
    expect(result.maximumSpeedKnots, isNull);
    expect(result.distanceNm, 0);
  });

  test('slow GPS movement derives speed and course across track samples', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0, speed: null, course: null));
    for (var second = 1; second <= 20; second++) {
      recorder.addFix(
        fix(second.toDouble(), second, speed: null, course: null),
        now: start.add(Duration(seconds: second)),
      );
      if (second >= 6) {
        final result = recorder.snapshot(start.add(Duration(seconds: second)));
        expect(result.currentSpeedKnots, closeTo(3600 / 1852, .000001));
        expect(result.gpsHeadingDegrees, closeTo(90, .000001));
      }
    }
    final result = recorder.snapshot(start.add(const Duration(seconds: 20)));
    expect(result.distanceNm, closeTo(18 / 1852, .000001));
    expect(result.maximumSpeedKnots, closeTo(3600 / 1852, .000001));
  });

  test(
    'a velocity spike contradicted by displacement does not set max speed',
    () {
      final recorder = TripRecorder();
      recorder.start(start, initialFix: fix(0, 0));
      recorder.addFix(
        fix(100, 10),
        now: start.add(const Duration(seconds: 10)),
      );
      recorder.addFix(
        fix(110, 11, speed: 60),
        now: start.add(const Duration(seconds: 11)),
      );
      final result = recorder.snapshot(start.add(const Duration(seconds: 11)));
      expect(result.maximumSpeedKnots, closeTo(10 * 3600 / 1852, .000001));
      expect(result.currentSpeedKnots, closeTo(10 * 3600 / 1852, .000001));
    },
  );

  test('GPS outages start a new segment and never bridge missing travel', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0));
    recorder.addFix(fix(100, 10), now: start.add(const Duration(seconds: 10)));
    recorder.addFix(fix(1000, 50), now: start.add(const Duration(seconds: 50)));
    recorder.addFix(fix(1100, 60), now: start.add(const Duration(seconds: 60)));
    final result = recorder.snapshot(start.add(const Duration(seconds: 60)));
    expect(recorder.segments.length, 2);
    expect(result.distanceNm, closeTo(200 / 1852, .000001));
    expect(result.gpsGapCount, 1);
    expect(result.recordedLegCount, 2);
    expect(result.elapsed, const Duration(seconds: 60));
  });

  test('current speed and GPS course expire while totals remain', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0));
    recorder.addFix(fix(100, 10), now: start.add(const Duration(seconds: 10)));
    final stale = recorder.snapshot(start.add(const Duration(seconds: 21)));
    expect(stale.currentSpeedKnots, isNull);
    expect(stale.gpsHeadingDegrees, isNull);
    expect(stale.maximumSpeedKnots, isNotNull);
    expect(stale.distanceNm, greaterThan(0));
  });

  test('missing GPS course is derived from clear measured GPS movement', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0));
    recorder.addFix(
      fix(100, 10, course: -1),
      now: start.add(const Duration(seconds: 10)),
    );
    expect(
      recorder
          .snapshot(start.add(const Duration(seconds: 10)))
          .gpsHeadingDegrees,
      closeTo(90, .000001),
    );
  });

  test(
    'reset starts a clean trip and backwards wall clock cannot reduce duration',
    () {
      final recorder = TripRecorder();
      recorder.start(start, initialFix: fix(0, 0));
      recorder.addFix(
        fix(100, 10),
        now: start.add(const Duration(seconds: 10)),
      );
      expect(
        recorder.snapshot(start.add(const Duration(seconds: 5))).elapsed,
        const Duration(seconds: 10),
      );
      recorder.stop(start.add(const Duration(seconds: 20)));
      recorder.start(start.add(const Duration(hours: 1)));
      expect(recorder.running, isTrue);
      expect(recorder.distanceNm, 0);
      expect(recorder.segments, isEmpty);
      expect(
        recorder
            .snapshot(start.add(const Duration(hours: 1)))
            .maximumSpeedKnots,
        isNull,
      );
    },
  );

  test('segment lists cannot be mutated by the map layer', () {
    final recorder = TripRecorder();
    recorder.start(start, initialFix: fix(0, 0));
    expect(() => recorder.segments.clear(), throwsUnsupportedError);
    expect(() => recorder.segments.first.clear(), throwsUnsupportedError);
  });
}
