import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:seapoint/trip_recorder.dart';
import 'package:seapoint/trip_widgets.dart';

void main() {
  for (final entry in {
    'Continue trip': TripRecoveryChoice.resume,
    'Finish saved trip': TripRecoveryChoice.finish,
    'Discard': TripRecoveryChoice.discard
  }.entries) {
    testWidgets('saved trip returns ${entry.value.name} with no overflow',
        (tester) async {
      tester.view.physicalSize = const Size(320, 640);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      TripRecoveryChoice? result;
      final recorder = TripRecorder()..start(DateTime.utc(2026, 11, 14));
      final summary = recorder.snapshot(DateTime.utc(2026, 11, 14, 1));
      await tester.pumpWidget(MaterialApp(
        builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context)
                .copyWith(textScaler: const TextScaler.linear(1.5)),
            child: child!),
        home: Builder(
            builder: (context) => Scaffold(
                body: TextButton(
                    child: const Text('Open'),
                    onPressed: () async {
                      result = await showDialog<TripRecoveryChoice>(
                          context: context,
                          barrierDismissible: false,
                          builder: (_) => TripRecoveryDialog(
                              summary: summary, partial: true));
                    }))),
      ));
      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();
      expect(find.text('Saved trip found'), findsOneWidget);
      expect(find.textContaining('Travel while SeaPoint was closed'),
          findsOneWidget);
      await tester.tap(find.text(entry.key));
      await tester.pumpAndSettle();
      expect(result, entry.value);
      expect(tester.takeException(), isNull);
    });
  }
}
