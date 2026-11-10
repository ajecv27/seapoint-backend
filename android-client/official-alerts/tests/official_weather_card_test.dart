import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:seapoint/official_weather_card.dart';

Widget app(Widget card, {double scale = 1}) => MaterialApp(
      theme: ThemeData(useMaterial3: true),
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context)
            .copyWith(textScaler: TextScaler.linear(scale)),
        child: child!,
      ),
      home: Scaffold(body: SingleChildScrollView(child: card)),
    );

void main() {
  testWidgets(
      'one official entry keeps both warning status and complete outlook',
      (tester) async {
    await tester.pumpWidget(app(OfficialWeatherCard(
      warningStatus: 'No warnings reported by the SeaPoint alert feed',
      outlookText: 'Tonight: Partly cloudy with a 40% chance of showers.',
      sourceDetails: 'Issued today. Full outlook remains available.',
      hasActiveWarnings: false,
      onOpenBulletin: () {},
    )));
    expect(find.text('Official Weather'), findsOneWidget);
    expect(
        find.text('Alerts: No warnings reported by the SeaPoint alert feed',
            findRichText: true),
        findsOneWidget);
    expect(
        find.text(
            'Synopsis: Tonight: Partly cloudy with a 40% chance of showers.',
            findRichText: true),
        findsOneWidget);
    expect(find.byIcon(Icons.open_in_new), findsOneWidget);
    expect(find.byType(InkWell), findsOneWidget);
    expect(find.byType(Card), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
      'active warnings and cached qualification remain fully visible at large text',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(320, 640));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    const warnings =
        'High Surf Warning • Small Craft Warning (cached — status unverified)';
    await tester.pumpWidget(app(
        OfficialWeatherCard(
          warningStatus: warnings,
          outlookText:
              'Validity unverified · Tonight: Scattered showers may develop.',
          sourceDetails: 'Source checked earlier. Full official outlook.',
          hasActiveWarnings: true,
          onOpenBulletin: () {},
        ),
        scale: 2));
    final warning = find.text('Alerts: $warnings', findRichText: true);
    expect(warning, findsOneWidget);
    final warningText = tester.widget<RichText>(warning);
    expect(warningText.maxLines, isNull);
    expect(warningText.overflow, isNot(TextOverflow.ellipsis));
    final outlook = find.text(
        'Synopsis: Validity unverified · Tonight: Scattered showers may develop.',
        findRichText: true);
    expect(outlook, findsOneWidget);
    expect(tester.widget<RichText>(outlook).maxLines, isNull);
    expect(find.byIcon(Icons.warning_amber_rounded), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('unknown services cannot turn into a no-warning claim',
      (tester) async {
    await tester.pumpWidget(app(OfficialWeatherCard(
      warningStatus: 'Warning service unavailable — status unverified',
      outlookText: 'Official bulletin unavailable; pull down to retry.',
      sourceDetails: 'Outlook validity unverified.',
      hasActiveWarnings: false,
      onOpenBulletin: () {},
    )));
    expect(
        find.text('Alerts: Warning service unavailable — status unverified',
            findRichText: true),
        findsOneWidget);
    expect(
        find.text(
            'Synopsis: Official bulletin unavailable; pull down to retry.',
            findRichText: true),
        findsOneWidget);
    expect(
        find.textContaining('No warnings', findRichText: true), findsNothing);
    expect(find.textContaining('No alerts', findRichText: true), findsNothing);
  });

  testWidgets(
      'header, warnings, outlook and external icon share the same single action',
      (tester) async {
    var opened = 0;
    await tester.pumpWidget(app(OfficialWeatherCard(
      warningStatus: 'Small Craft Advisory',
      outlookText: 'Today: Showers are possible.',
      sourceDetails: 'Full source metadata and outlook.',
      hasActiveWarnings: true,
      onOpenBulletin: () => opened++,
    )));
    for (final target in [
      find.text('Official Weather'),
      find.text('Alerts: Small Craft Advisory', findRichText: true),
      find.text('Synopsis: Today: Showers are possible.', findRichText: true),
      find.byIcon(Icons.open_in_new),
    ]) {
      await tester.tap(target);
      await tester.pumpAndSettle();
    }
    expect(opened, 4);
    expect(find.byType(InkWell), findsOneWidget);
    expect(find.byType(AlertDialog), findsNothing);
  });

  testWidgets(
      'major watches, warnings and advisories remain fully named above the synopsis',
      (tester) async {
    const alerts =
        'Tropical Storm Watch • Hurricane Warning • Small Craft Advisory';
    await tester.pumpWidget(app(OfficialWeatherCard(
      warningStatus: alerts,
      outlookText:
          'Drier air should bring more stable weather, with daytime showers still possible.',
      sourceDetails: 'Official source coverage checked.',
      hasActiveWarnings: true,
      onOpenBulletin: () {},
    )));
    expect(find.text('Alerts: $alerts', findRichText: true), findsOneWidget);
    expect(
        find.text(
            'Synopsis: Drier air should bring more stable weather, with daytime showers still possible.',
            findRichText: true),
        findsOneWidget);
    expect(find.byIcon(Icons.open_in_new), findsOneWidget);
  });

  testWidgets('long press retains full source and issue information',
      (tester) async {
    const metadata = 'Antigua & Barbuda Meteorological Service\n'
        'Warnings checked: 14:00\nOutlook issued: today\n'
        'Full outlook: A longer original synopsis with its qualifications.';
    await tester.pumpWidget(app(OfficialWeatherCard(
      warningStatus: 'Checking official alerts...',
      outlookText: 'Checking the official island forecast…',
      sourceDetails: metadata,
      hasActiveWarnings: false,
      onOpenBulletin: () {},
    )));
    await tester.longPress(find.text(
        'Synopsis: Checking the official island forecast…',
        findRichText: true));
    await tester.pumpAndSettle();
    expect(find.text(metadata), findsOneWidget);
  });
}
