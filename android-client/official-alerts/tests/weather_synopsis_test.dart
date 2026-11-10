import 'package:flutter_test/flutter_test.dart';
import 'package:seapoint/weather_synopsis.dart';

void main() {
  test(
      'official drier-air outlook retains its shower caveat in a short synopsis',
      () {
    const bulletin = 'As a drier airmass moves into the area, generally stable '
        'conditions should return. However as the winds remain light, daytime '
        'heating and available moisture may generate periods of cloudiness and showers.';
    final result = weatherOutlookSynopsis(bulletin);
    expect(result,
        'More stable weather is expected, but daytime showers remain possible.');
    expect(result.length, lessThan(110));
    expect(result, isNot(contains('...')));
  });

  test('unknown outlook preserves complete wording and uncertainty', () {
    expect(
        weatherOutlookSynopsis(
            'A weak trough may bring scattered showers tonight. '
            'Conditions should improve tomorrow.'),
        'A weak trough may bring scattered showers tonight. Conditions should improve tomorrow.');
  });

  test('negative statements never become a positive shower or thunder claim',
      () {
    expect(
        weatherOutlookSynopsis(
            'No showers or thunderstorms are expected tonight.'),
        'No showers or thunderstorms are expected tonight.');
    expect(
        weatherOutlookSynopsis(
            'Drier air will not prevent heavy rain later today.'),
        'Drier air will not prevent heavy rain later today.');
  });

  test('source probability stays numeric and unchanged', () {
    expect(
        weatherOutlookSynopsis(
            'Partly cloudy skies with a 40 percent or moderate chance of showers.'),
        'Partly cloudy with a 40% chance of showers.');
    expect(weatherOutlookSynopsis('A 12.5 percent chance of rain overnight.'),
        'A 12.5% chance of rain overnight.');
  });

  test('short outlook without final punctuation becomes a complete statement',
      () {
    expect(weatherOutlookSynopsis('Today: Fair to partly cloudy skies'),
        'Today: Fair to partly cloudy.');
  });

  test('important later precipitation caveat survives a longer outlook', () {
    expect(
        weatherOutlookSynopsis('Generally settled conditions should return. '
            'Winds will remain light. However, heavy showers and thunderstorms may develop this afternoon.'),
        'Generally settled conditions should return. Winds will remain light. However, heavy showers and thunderstorms may develop this afternoon.');
  });

  test('negated thunderstorms cannot hide a later positive shower caveat', () {
    expect(
        weatherOutlookSynopsis('Generally settled conditions should return. '
            'No thunderstorms are expected. However, showers may develop this afternoon.'),
        'Generally settled conditions should return. No thunderstorms are expected. However, showers may develop this afternoon.');
  });

  test('the daytime qualifier survives a standalone light-wind shower sentence',
      () {
    expect(
        weatherOutlookSynopsis('However as the winds remain light, daytime '
            'heating and available moisture may generate periods of cloudiness and showers.'),
        'Daytime cloud and showers remain possible in light winds.');
  });

  test('negation and timing stay intact when selecting an important caveat',
      () {
    expect(
        weatherOutlookSynopsis(
            'Dry weather is likely today. Winds will remain light. '
            'No thunderstorms are expected until tomorrow.'),
        'Dry weather is likely today. Winds will remain light. No thunderstorms are expected until tomorrow.');
  });

  test('cross-sentence geographic and confidence qualifiers stay with the risk',
      () {
    const source = 'Generally stable conditions are expected. '
        'Heavy rain may develop tomorrow. '
        'This risk is limited to isolated mountain areas. '
        'Confidence in this forecast is low.';
    expect(weatherOutlookSynopsis(source), source);
  });

  test('separate afternoon showers and overnight thunder risks both survive',
      () {
    const source = 'Generally settled conditions should return. '
        'Showers may develop this afternoon. Thunderstorms remain possible overnight.';
    expect(weatherOutlookSynopsis(source), source);
  });

  test('abbreviated times and place names do not drop forecast fragments', () {
    const timed = 'Generally settled conditions should return. '
        'Showers may develop after 6 p.m. tomorrow.';
    const place = 'Showers are confined to St. Lucia tomorrow.';
    expect(weatherOutlookSynopsis(timed), timed);
    expect(weatherOutlookSynopsis(place), place);
  });

  test('full unfamiliar sentences retain their grammatical subject', () {
    expect(weatherOutlookSynopsis('Partly cloudy skies are expected tonight.'),
        'Partly cloudy skies are expected tonight.');
    expect(weatherOutlookSynopsis('No clear skies are expected.'),
        'No clear skies are expected.');
  });

  test(
      'the real evening bulletin selects its complete concise tonight forecast',
      () {
    const bulletin = 'Antigua & Barbuda National Forecast '
        'Synopsis: As a drier airmass moves into the area, generally stable '
        'conditions should return. However as the winds remain light, daytime '
        'heating and available moisture may generate periods of cloudiness and showers. '
        'Weather tonight: Partly cloudy skies with a 40 percent or moderate chance of showers. '
        'Weather tomorrow: Partly cloudy to cloudy skies with a 60 percent or moderate chance of showers. '
        'Winds: Southeast at 7 to 15 km/h. Seas: 0.9 to 1.5 meters.';
    final extracted = extractOfficialWeatherOutlook(bulletin);
    expect(extracted, contains('daytime heating and available moisture'));
    expect(
        extracted, contains('Tonight: Partly cloudy skies with a 40 percent'));
    expect(extracted,
        contains('Tomorrow: Partly cloudy to cloudy skies with a 60 percent'));
    expect(extracted, isNot(contains('Winds:')));
    expect(extracted, isNot(contains('Seas:')));
    expect(weatherOutlookSynopsis(extracted),
        'Tonight: Partly cloudy with a 40% chance of showers.');
  });

  test('today takes precedence over tonight with original numeric probability',
      () {
    const bulletin =
        'Synopsis: Moisture may bring occasional unsettled weather. '
        'Weather today: Partly cloudy skies with a 30 percent or low chance of showers. '
        'Weather tonight: Cloudy skies with a 70 percent or high chance of rain. '
        'Weather tomorrow: Scattered thunderstorms are possible. Winds: Easterly.';
    final extracted = extractOfficialWeatherOutlook(bulletin);
    expect(weatherOutlookSynopsis(extracted),
        'Today: Partly cloudy with a 30% chance of showers.');
    expect(extracted, contains('70 percent'));
    expect(extracted, contains('Scattered thunderstorms are possible.'));
  });

  test('tomorrow is used only when no today or tonight forecast exists', () {
    const bulletin = 'Synopsis: Drier air is approaching. '
        'Weather tomorrow: Mainly fair skies with a 10 percent chance of showers. '
        'Winds: Northeast at 10 knots.';
    expect(weatherOutlookSynopsis(extractOfficialWeatherOutlook(bulletin)),
        'Tomorrow: Mainly fair skies with a 10% chance of showers.');
  });

  test(
      'chosen forecast keeps geographic, time and confidence qualifiers together',
      () {
    const source = 'A trough may affect the islands. '
        'Today: Heavy showers may develop after 6 p.m. '
        'This risk is limited to isolated mountain areas. Confidence is low. '
        'Tonight: Dry conditions are expected.';
    expect(
        weatherOutlookSynopsis(source),
        'Today: Heavy showers may develop after 6 p.m. '
        'This risk is limited to isolated mountain areas. Confidence is low.');
  });

  test(
      'old cached synopsis plus Today section receives the same concise result',
      () {
    const source = 'Moisture may affect the islands.  '
        'Today: Clear skies with a 5 percent chance of rain.';
    expect(weatherOutlookSynopsis(source),
        'Today: Clear with a 5% chance of rain.');
  });

  test(
      'official card synopsis uses the airmass discussion, not a period forecast',
      () {
    const source = 'As a drier airmass moves into the area, generally stable '
        'conditions should return. However as the winds remain light, daytime '
        'heating and available moisture may generate periods of cloudiness and showers. '
        'Tonight: Partly cloudy skies with a 40 percent chance of showers. '
        'Tomorrow: Showers are possible.';
    expect(officialWeatherSynopsis(source),
        'Drier air should bring more stable weather, with daytime showers still possible.');
    expect(officialWeatherSynopsis(source), isNot(contains('Tonight:')));
  });

  test(
      'official synopsis retains unfamiliar geographic and confidence qualifiers',
      () {
    const synopsis = 'A trough may bring heavy rain after 6 p.m. '
        'This risk is limited to isolated mountain areas. Confidence is low.';
    expect(
        officialWeatherSynopsis('$synopsis Today: Fair conditions elsewhere.'),
        synopsis);
  });

  test('official synopsis cannot relabel a standalone forecast as a synopsis',
      () {
    expect(officialWeatherSynopsis('Today: Cloudy with showers.'),
        'Official synopsis unavailable; open the bulletin for details.');
    expect(officialWeatherSynopsis('Synopsis: Tonight: Fair conditions.'),
        'Official synopsis unavailable; open the bulletin for details.');
  });

  test('old synopsis-only cache continues to work for the official card', () {
    expect(officialWeatherSynopsis('No thunderstorms are expected tonight.'),
        'No thunderstorms are expected tonight.');
    expect(
        officialWeatherSynopsis(
            'Stable conditions should return. How... Today: Clear skies.'),
        'Read the official bulletin for the complete synopsis.');
  });

  test('clipped sources do not display an unfinished or misleading forecast',
      () {
    expect(weatherOutlookSynopsis('Stable conditions should return. How...'),
        'Read the official bulletin for the complete outlook.');
    expect(weatherOutlookSynopsis('Heavy rain may…'),
        'Read the official bulletin for the complete outlook.');
  });

  test(
      'whitespace and optional section heading are normalized without invention',
      () {
    expect(
        weatherOutlookSynopsis(
            '  Synopsis:  Clear skies\n with light winds.  '),
        'Clear with light winds.');
    expect(weatherOutlookSynopsis('   '), isEmpty);
  });
}
