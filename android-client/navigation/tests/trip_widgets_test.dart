import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:seapoint/trip_recorder.dart';
import 'package:seapoint/trip_widgets.dart';

TripSummary trip({
  double? current = 8.4,
  double? maximum = 14.2,
  double? heading = 273,
  int gaps = 0,
  Duration elapsed = const Duration(hours: 1, minutes: 2, seconds: 3),
}) {
  final start = DateTime.utc(2026, 11, 9);
  return TripSummary(
    startedAt: start,
    endedAt: start.add(elapsed),
    elapsed: elapsed,
    distanceNm: 6.78,
    averageSpeedKnots: 6.5,
    maximumSpeedKnots: maximum,
    currentSpeedKnots: current,
    gpsHeadingDegrees: heading,
    acceptedFixCount: 100,
    recordedLegCount: 90,
    gpsGapCount: gaps,
  );
}

Widget app(Widget child, {double scale = 1}) {
  return MaterialApp(
    builder: (context, child) => MediaQuery(
      data:
          MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(scale)),
      child: child!,
    ),
    home: Scaffold(
      backgroundColor: const Color(0xFF102D40),
      body: Align(
        alignment: Alignment.topCenter,
        child: Padding(padding: const EdgeInsets.all(8), child: child),
      ),
    ),
  );
}

Future<void> openSummary(
  WidgetTester tester,
  TripSummary summary, {
  double scale = 1,
}) async {
  await tester.pumpWidget(app(Builder(builder: (context) {
    return TextButton(
      onPressed: () => showDialog<void>(
        context: context,
        builder: (_) => TripSummaryDialog(summary: summary),
      ),
      child: const Text('Finish trip'),
    );
  }), scale: scale));
  await tester.tap(find.text('Finish trip'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('live GPS statistics show nautical units in three columns',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(320, 640));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(app(TripStatsGrid(summary: trip())));

    for (final value in [
      '8.4 kt',
      '14.2 kt',
      '6.5 kt',
      '273° W',
      '6.78 NM',
      '01:02:03'
    ]) {
      expect(find.text(value), findsOneWidget);
    }
    final current = tester.getTopLeft(find.text('Current speed'));
    final maximum = tester.getTopLeft(find.text('Maximum speed'));
    final average = tester.getTopLeft(find.text('Average speed'));
    final heading = tester.getTopLeft(find.text('GPS heading'));
    final distance = tester.getTopLeft(find.text('Distance travelled'));
    final elapsed = tester.getTopLeft(find.text('Elapsed time'));
    expect(current.dy, maximum.dy);
    expect(current.dy, average.dy);
    expect(current.dx, lessThan(maximum.dx));
    expect(maximum.dx, lessThan(average.dx));
    expect(heading.dy, greaterThan(current.dy));
    expect(heading.dy, distance.dy);
    expect(heading.dy, elapsed.dy);
    expect(tester.takeException(), isNull);
  });

  testWidgets('missing GPS readings stay unavailable and north wraps to zero',
      (tester) async {
    await tester.pumpWidget(app(TripStatsGrid(
      summary: trip(current: null, maximum: null, heading: null),
    )));
    expect(find.text('--'), findsNWidgets(3));

    await tester.pumpWidget(app(TripStatsGrid(summary: trip(heading: 359.7))));
    expect(find.text('000° N'), findsOneWidget);
  });

  testWidgets('live panel fits narrow phones with large text and long trips',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(320, 640));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(app(
      TripStatsGrid(
          summary: trip(
              elapsed: const Duration(hours: 125, minutes: 4, seconds: 9))),
      scale: 2,
    ));
    expect(find.text('125:04:09'), findsOneWidget);
    expect(find.text('GPS heading'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
      'finished summary explains average, omits absent gaps, and closes',
      (tester) async {
    await openSummary(tester, trip());
    expect(find.text('Trip summary'), findsOneWidget);
    for (final value in ['14.2 kt', '6.5 kt', '6.78 NM', '01:02:03']) {
      expect(find.text(value), findsOneWidget);
    }
    expect(find.text('Average includes stops.'), findsOneWidget);
    expect(find.textContaining('GPS gaps:'), findsNothing);
    expect(find.text('Current speed'), findsNothing);
    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();
    expect(find.text('Trip summary'), findsNothing);
  });

  testWidgets(
      'summary scrolls at large text and explains GPS gaps only when present',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(320, 568));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await openSummary(tester, trip(gaps: 2, maximum: null), scale: 2);
    expect(find.text('--'), findsOneWidget);
    final gapNote = find.text(
      'GPS gaps: 2. Distance excludes unrecorded sections.',
    );
    expect(gapNote, findsOneWidget);
    await tester.ensureVisible(gapNote);
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();
    expect(find.text('Trip summary'), findsNothing);
  });
}
