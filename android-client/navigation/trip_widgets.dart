import 'package:flutter/material.dart';

import 'trip_recorder.dart';

/// Live readings from the recorded GPS trip, arranged for a compact map panel.
class TripStatsGrid extends StatelessWidget {
  const TripStatsGrid({super.key, required this.summary});

  final TripSummary summary;

  @override
  Widget build(BuildContext context) {
    return _MetricGrid(
      columns: 3,
      metrics: [
        _Metric('Current speed', _number(summary.currentSpeedKnots, 1, 'kt')),
        _Metric('Maximum speed', _number(summary.maximumSpeedKnots, 1, 'kt')),
        _Metric('Average speed', _number(summary.averageSpeedKnots, 1, 'kt')),
        _Metric('GPS heading', _heading(summary.gpsHeadingDegrees)),
        _Metric('Distance travelled', _number(summary.distanceNm, 2, 'NM')),
        _Metric('Elapsed time', _duration(summary.elapsed)),
      ],
    );
  }
}

/// A completed trip's measured distance and overall average, including stops.
class TripSummaryDialog extends StatelessWidget {
  const TripSummaryDialog({super.key, required this.summary});

  final TripSummary summary;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF102D40),
      title: const Text('Trip summary', style: TextStyle(color: Colors.white)),
      insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      content: SizedBox(
        width: 340,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _MetricGrid(
                columns: 2,
                metrics: [
                  _Metric('Average speed',
                      _number(summary.averageSpeedKnots, 1, 'kt')),
                  _Metric('Maximum speed',
                      _number(summary.maximumSpeedKnots, 1, 'kt')),
                  _Metric('Distance travelled',
                      _number(summary.distanceNm, 2, 'NM')),
                  _Metric('Travel time', _duration(summary.elapsed)),
                ],
              ),
              const SizedBox(height: 14),
              const Text(
                'Average includes stops.',
                style: TextStyle(color: Colors.white70, fontSize: 13),
              ),
              if (summary.gpsGapCount > 0) ...[
                const SizedBox(height: 8),
                Text(
                  'GPS gaps: ${summary.gpsGapCount}. '
                  'Distance excludes unrecorded sections.',
                  style: const TextStyle(color: Colors.white70, fontSize: 13),
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Done', style: TextStyle(color: Color(0xFF76D5FF))),
        ),
      ],
    );
  }
}

class _Metric {
  const _Metric(this.label, this.value);

  final String label;
  final String value;
}

class _MetricGrid extends StatelessWidget {
  const _MetricGrid({required this.columns, required this.metrics});

  final int columns;
  final List<_Metric> metrics;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      const gap = 8.0;
      final width = (constraints.maxWidth - gap * (columns - 1)) / columns;
      return Wrap(
        spacing: gap,
        runSpacing: gap,
        children: [
          for (final metric in metrics)
            SizedBox(width: width, child: _MetricTile(metric: metric)),
        ],
      );
    });
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({required this.metric});

  final _Metric metric;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '${metric.label}: ${metric.value}',
      excludeSemantics: true,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                metric.label,
                style: const TextStyle(color: Colors.white70, fontSize: 11),
              ),
              const SizedBox(height: 4),
              SizedBox(
                width: double.infinity,
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: Text(
                    metric.value,
                    maxLines: 1,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w600,
                      fontSize: 18,
                      fontFeatures: [FontFeature.tabularFigures()],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

String _number(double? value, int places, String unit) {
  if (value == null || !value.isFinite || value < 0) return '--';
  return '${value.toStringAsFixed(places)} $unit';
}

String _duration(Duration value) {
  final seconds = value.inSeconds < 0 ? 0 : value.inSeconds;
  final hours = (seconds ~/ 3600).toString().padLeft(2, '0');
  final minutes = ((seconds ~/ 60) % 60).toString().padLeft(2, '0');
  final remaining = (seconds % 60).toString().padLeft(2, '0');
  return '$hours:$minutes:$remaining';
}

String _heading(double? degrees) {
  if (degrees == null || !degrees.isFinite || degrees < 0) return '--';
  final rounded = degrees.round() % 360;
  const points = [
    'N',
    'NNE',
    'NE',
    'ENE',
    'E',
    'ESE',
    'SE',
    'SSE',
    'S',
    'SSW',
    'SW',
    'WSW',
    'W',
    'WNW',
    'NW',
    'NNW',
  ];
  final cardinal = points[((rounded + 11.25) / 22.5).floor() % points.length];
  return '${rounded.toString().padLeft(3, '0')}° $cardinal';
}
