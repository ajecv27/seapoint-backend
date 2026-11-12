import 'dart:math' as math;

/// One measured GPS fix. Speeds are metres/second; course is GPS course over
/// ground, never the phone's magnetic compass direction.
class GpsFix {
  const GpsFix({
    required this.latitude,
    required this.longitude,
    required this.timestamp,
    required this.accuracyMetres,
    this.speedMetresPerSecond,
    this.speedAccuracyMetresPerSecond,
    this.courseDegrees,
    this.courseAccuracyDegrees,
  });

  final double latitude;
  final double longitude;
  final DateTime timestamp;
  final double accuracyMetres;
  final double? speedMetresPerSecond;
  final double? speedAccuracyMetresPerSecond;
  final double? courseDegrees;
  final double? courseAccuracyDegrees;
}

class TripSummary {
  const TripSummary({
    required this.startedAt,
    required this.endedAt,
    required this.elapsed,
    required this.distanceNm,
    required this.averageSpeedKnots,
    required this.maximumSpeedKnots,
    required this.currentSpeedKnots,
    required this.gpsHeadingDegrees,
    required this.acceptedFixCount,
    required this.recordedLegCount,
    required this.gpsGapCount,
  });

  final DateTime? startedAt;
  final DateTime? endedAt;
  final Duration elapsed;
  final double distanceNm;

  /// Overall average, including time stopped and GPS outages.
  final double averageSpeedKnots;
  final double? maximumSpeedKnots;
  final double? currentSpeedKnots;
  final double? gpsHeadingDegrees;
  final int acceptedFixCount;
  final int recordedLegCount;
  final int gpsGapCount;
}

class TripRecorder {
  TripRecorder({
    this.maximumAccuracyMetres = 50,
    this.maximumPlausibleSpeedMetresPerSecond = 80,
    this.maximumSpeedAccuracyMetresPerSecond = 3,
    this.minimumTrackMovementMetres = 3,
    this.staleAfter = const Duration(seconds: 10),
    this.segmentGap = const Duration(seconds: 30),
  });

  static const metresPerNauticalMile = 1852.0;
  static const metresPerSecondToKnots = 3600 / metresPerNauticalMile;

  final double maximumAccuracyMetres;
  final double maximumPlausibleSpeedMetresPerSecond;
  final double maximumSpeedAccuracyMetresPerSecond;
  final double minimumTrackMovementMetres;
  final Duration staleAfter;
  final Duration segmentGap;

  final List<List<GpsFix>> _segments = [];
  DateTime? _startedAt;
  DateTime? _endedAt;
  DateTime? _latestClock;
  GpsFix? _lastAcceptedFix;
  double _distanceMetres = 0;
  double? _maximumSpeedMps;
  double? _currentSpeedMps;
  double? _gpsCourse;
  DateTime? _speedMeasuredAt;
  DateTime? _courseMeasuredAt;
  int _fixCount = 0;
  int _recordedLegCount = 0;
  int _gapCount = 0;
  bool _running = false;
  bool _needsTrackReanchor = false;
  TripSummary? _finished;

  bool get running => _running;
  GpsFix? get lastAcceptedFix => _lastAcceptedFix;
  double get distanceNm => _distanceMetres / metresPerNauticalMile;
  List<List<GpsFix>> get segments => List.unmodifiable(
        _segments.map((segment) => List<GpsFix>.unmodifiable(segment)),
      );

  /// Start a new recording. An initial fix must be measured at or after the
  /// start, so cached pre-trip travel cannot inflate the new trip.
  void start(DateTime now, {GpsFix? initialFix}) {
    reset();
    _startedAt = now;
    _latestClock = now;
    _running = true;
    if (initialFix != null) addFix(initialFix, now: now);
  }

  void reset() {
    _segments.clear();
    _startedAt = null;
    _endedAt = null;
    _latestClock = null;
    _lastAcceptedFix = null;
    _distanceMetres = 0;
    _maximumSpeedMps = null;
    _currentSpeedMps = null;
    _gpsCourse = null;
    _speedMeasuredAt = null;
    _courseMeasuredAt = null;
    _fixCount = 0;
    _recordedLegCount = 0;
    _gapCount = 0;
    _running = false;
    _needsTrackReanchor = false;
    _finished = null;
  }

  bool _validFix(GpsFix fix, DateTime now) {
    return fix.latitude.isFinite &&
        fix.longitude.isFinite &&
        fix.latitude >= -90 &&
        fix.latitude <= 90 &&
        fix.longitude >= -180 &&
        fix.longitude <= 180 &&
        fix.accuracyMetres.isFinite &&
        fix.accuracyMetres >= 0 &&
        fix.accuracyMetres <= maximumAccuracyMetres &&
        (_startedAt == null || !fix.timestamp.isBefore(_startedAt!)) &&
        now.difference(fix.timestamp) <= staleAfter &&
        fix.timestamp.difference(now) <= const Duration(seconds: 2);
  }

  DateTime _clock(DateTime now) {
    if (_latestClock == null || now.isAfter(_latestClock!)) _latestClock = now;
    return _latestClock!;
  }

  /// Returns false for rejected fixes. They do not move the recorded trail,
  /// inflate statistics, or replace the last trustworthy GPS reading.
  bool addFix(GpsFix fix, {required DateTime now}) {
    if (!_running) return false;
    final clock = _clock(now);
    if (!_validFix(fix, clock)) return false;
    final previous = _lastAcceptedFix;
    if (previous != null && !fix.timestamp.isAfter(previous.timestamp)) {
      return false;
    }

    final seconds = previous == null
        ? 0.0
        : fix.timestamp.difference(previous.timestamp).inMicroseconds / 1e6;
    final gap = previous != null &&
        fix.timestamp.difference(previous.timestamp) > segmentGap;
    final displacement = previous == null ? 0.0 : distanceMetres(previous, fix);
    final accuracyAllowance = previous == null
        ? fix.accuracyMetres
        : previous.accuracyMetres + fix.accuracyMetres;
    if (previous != null &&
        !gap &&
        displacement >
            maximumPlausibleSpeedMetresPerSecond * seconds +
                accuracyAllowance * 2) {
      return false;
    }

    double? reportedSpeed = _reportedSpeed(fix);
    final previousReportedSpeed =
        previous == null ? null : _reportedSpeed(previous);
    final previouslyStationary =
        previousReportedSpeed != null && previousReportedSpeed <= .3;
    final segmentSpeed = seconds > 0 ? displacement / seconds : 0.0;
    if (reportedSpeed != null && previous != null && !gap) {
      // Reject a velocity spike contradicted by the measured displacement,
      // allowing for the coordinate accuracy at the sampling interval.
      final tolerance = math.max(
        2.0,
        accuracyAllowance / seconds + reportedSpeed * .3,
      );
      if ((reportedSpeed - segmentSpeed).abs() > tolerance) {
        if (reportedSpeed <= .3 &&
            previouslyStationary &&
            fix.speedAccuracyMetresPerSecond != null &&
            fix.speedAccuracyMetresPerSecond! <= 1) {
          return false;
        }
        // A valid zero reading can mark the end of deceleration; instantaneous
        // velocity need not match the average velocity over this whole leg.
        if (reportedSpeed > .3) reportedSpeed = null;
      }
    }

    var moved = false;
    GpsFix? trackAnchor;
    var trackDisplacement = 0.0;
    var trackUncertainty = 0.0;
    final stationaryNoise =
        reportedSpeed != null && reportedSpeed <= .3 && previouslyStationary;
    if (!gap && _needsTrackReanchor && !stationaryNoise && previous != null) {
      // GPS can drift while stopped. Resume from the last stationary fix,
      // without turning that suppressed drift into a travelled line later.
      _segments.add([previous]);
      _needsTrackReanchor = false;
    }
    if (_segments.isEmpty || gap) {
      if (gap) _gapCount++;
      _segments.add([fix]);
    } else {
      final anchor = _segments.last.last;
      final metres = distanceMetres(anchor, fix);
      final uncertainty = math.sqrt(
        anchor.accuracyMetres * anchor.accuracyMetres +
            fix.accuracyMetres * fix.accuracyMetres,
      );
      final threshold = math.max(
        minimumTrackMovementMetres,
        reportedSpeed == null ? uncertainty * 2 : math.min(15.0, uncertainty),
      );
      if (metres >= threshold && !stationaryNoise) {
        trackAnchor = anchor;
        trackDisplacement = metres;
        trackUncertainty = uncertainty;
        _segments.last.add(fix);
        _distanceMetres += metres;
        _recordedLegCount++;
        moved = true;
      }
    }
    if (stationaryNoise) _needsTrackReanchor = true;

    _lastAcceptedFix = fix;
    _fixCount++;
    double? derivedSpeed;
    if (trackAnchor != null) {
      final trackSeconds =
          fix.timestamp.difference(trackAnchor.timestamp).inMicroseconds / 1e6;
      final value = trackSeconds > 0 ? trackDisplacement / trackSeconds : null;
      if (value != null && value <= maximumPlausibleSpeedMetresPerSecond) {
        derivedSpeed = value;
      }
    }
    final speed = reportedSpeed ?? derivedSpeed;
    if (speed != null) {
      _currentSpeedMps = speed;
      _speedMeasuredAt = fix.timestamp;
    } else if (gap) {
      _currentSpeedMps = null;
      _speedMeasuredAt = null;
    }
    final movingSpeed = reportedSpeed != null && reportedSpeed > .3
        ? reportedSpeed
        : derivedSpeed;
    if (moved && movingSpeed != null && movingSpeed > .3) {
      _maximumSpeedMps = math.max(_maximumSpeedMps ?? 0, movingSpeed);
    }

    final course = fix.courseDegrees;
    final courseAccuracy = fix.courseAccuracyDegrees;
    final validCourse = course != null &&
        course.isFinite &&
        course >= 0 &&
        course < 360 &&
        (courseAccuracy == null ||
            courseAccuracy.isFinite &&
                courseAccuracy >= 0 &&
                courseAccuracy <= 45) &&
        _speedMeasuredAt != null &&
        fix.timestamp.difference(_speedMeasuredAt!) <= staleAfter &&
        (_currentSpeedMps ?? 0) >= .5;
    if (validCourse) {
      _gpsCourse = course;
      _courseMeasuredAt = fix.timestamp;
    } else if (trackAnchor != null &&
        (_currentSpeedMps ?? 0) >= .5 &&
        trackDisplacement >= math.max(5.0, trackUncertainty * 2)) {
      _gpsCourse = _bearingDegrees(trackAnchor, fix);
      _courseMeasuredAt = fix.timestamp;
    } else if (gap || reportedSpeed != null && reportedSpeed <= .3) {
      _gpsCourse = null;
      _courseMeasuredAt = null;
    }
    return true;
  }

  double? _reportedSpeed(GpsFix fix) {
    final value = fix.speedMetresPerSecond;
    final accuracy = fix.speedAccuracyMetresPerSecond;
    if (value == null ||
        !value.isFinite ||
        value < 0 ||
        value > maximumPlausibleSpeedMetresPerSecond) {
      return null;
    }
    if (accuracy != null &&
        (!accuracy.isFinite ||
            accuracy < 0 ||
            accuracy > maximumSpeedAccuracyMetresPerSecond)) {
      return null;
    }
    return value;
  }

  TripSummary snapshot(DateTime now) {
    if (_finished != null) return _finished!;
    final clock = _clock(now);
    final elapsed =
        _startedAt == null ? Duration.zero : clock.difference(_startedAt!);
    final hours =
        elapsed.inMicroseconds / Duration.microsecondsPerSecond / 3600;
    final freshSpeed = _speedMeasuredAt != null &&
        clock.difference(_speedMeasuredAt!) <= staleAfter;
    final freshCourse = _courseMeasuredAt != null &&
        clock.difference(_courseMeasuredAt!) <= staleAfter;
    return TripSummary(
      startedAt: _startedAt,
      endedAt: _endedAt,
      elapsed: elapsed,
      distanceNm: distanceNm,
      averageSpeedKnots: hours > 0 ? distanceNm / hours : 0,
      maximumSpeedKnots: _maximumSpeedMps == null
          ? null
          : _maximumSpeedMps! * metresPerSecondToKnots,
      currentSpeedKnots: freshSpeed && _currentSpeedMps != null
          ? _currentSpeedMps! * metresPerSecondToKnots
          : null,
      gpsHeadingDegrees: freshSpeed && freshCourse ? _gpsCourse : null,
      acceptedFixCount: _fixCount,
      recordedLegCount: _recordedLegCount,
      gpsGapCount: _gapCount,
    );
  }

  TripSummary stop(DateTime now) {
    if (_finished != null) return _finished!;
    _endedAt = _clock(now);
    final result = snapshot(_endedAt!);
    _running = false;
    _finished = result;
    return result;
  }

  static double distanceMetres(GpsFix a, GpsFix b) {
    const radians = math.pi / 180;
    final latitude = (b.latitude - a.latitude) * radians;
    final longitude = (b.longitude - a.longitude) * radians;
    final haversine = math.sin(latitude / 2) * math.sin(latitude / 2) +
        math.cos(a.latitude * radians) *
            math.cos(b.latitude * radians) *
            math.sin(longitude / 2) *
            math.sin(longitude / 2);
    return 6371008.8 * 2 * math.asin(math.sqrt(haversine.clamp(0.0, 1.0)));
  }

  static double _bearingDegrees(GpsFix a, GpsFix b) {
    const radians = math.pi / 180;
    final first = a.latitude * radians;
    final second = b.latitude * radians;
    final delta = (b.longitude - a.longitude) * radians;
    final y = math.sin(delta) * math.cos(second);
    final x = math.cos(first) * math.sin(second) -
        math.sin(first) * math.cos(second) * math.cos(delta);
    return (math.atan2(y, x) / radians + 360) % 360;
  }
}
