import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:seapoint/navigation_boat_marker.dart';

void main() {
  test('Android pixels convert to logical GPS anchor at all phone densities',
      () {
    for (final d in [1.0, 2.0, 3.0, 3.5]) {
      expect(logicalBoatPosition(100 * d, 200 * d, d, android: true),
          const Offset(100, 200));
    }
    expect(logicalBoatPosition(100, 200, 3, android: false),
        const Offset(100, 200));
  });
  testWidgets(
      'visible needle has a fixed logical size and rotates with phone and map',
      (tester) async {
    await tester.pumpWidget(const MaterialApp(
        home:
            Center(child: NavigationBoatMarker(heading: 120, mapBearing: 30))));
    expect(tester.getSize(find.byType(CustomPaint).last), const Size(34, 34));
    final transform = tester.widget<Transform>(find.descendant(
        of: find.byType(NavigationBoatMarker),
        matching: find.byType(Transform)));
    expect(
        transform.transform.entry(0, 0), closeTo(math.cos(math.pi / 2), 1e-6));
    expect(transform.transform.entry(1, 0), closeTo(1, 1e-6));
    expect(
        find.descendant(
            of: find.byType(NavigationBoatMarker),
            matching: find.byType(IgnorePointer)),
        findsOneWidget);
  });
}
