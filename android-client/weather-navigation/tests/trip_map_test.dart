import 'package:flutter_test/flutter_test.dart';
import 'package:seapoint/trip_map.dart';
import 'package:seapoint/trip_recorder.dart';

GpsFix fix(double lat, double lon) => GpsFix(
    latitude: lat,
    longitude: lon,
    timestamp: DateTime.utc(2026),
    accuracyMetres: 3);

void main() {
  test('GPS gaps remain separate lines with longitude first', () {
    final result = tripTrackGeoJson([
      [fix(17, -61), fix(17.1, -61.1)],
      [fix(18, -62), fix(18.1, -62.1)],
      [fix(19, -63)],
    ]);
    final geometry = result['features'][0]['geometry'];
    expect(geometry['type'], 'MultiLineString');
    expect(geometry['coordinates'], [
      [
        [-61.0, 17.0],
        [-61.1, 17.1]
      ],
      [
        [-62.0, 18.0],
        [-62.1, 18.1]
      ],
    ]);
  });
  test('one GPS point cannot imply a travelled line', () {
    expect(
        tripTrackGeoJson([
          [fix(17, -61)]
        ])['features'],
        isEmpty);
  });
  test('boat feature carries GPS course and real coordinates', () {
    final result =
        boatGeoJson(latitude: 17.2, longitude: -61.8, courseDegrees: 123);
    expect(result['features'][0]['properties']['course'], 123);
    expect(result['features'][0]['geometry']['coordinates'], [-61.8, 17.2]);
    expect(
        boatGeoJson(
            latitude: null, longitude: null, courseDegrees: 0)['features'],
        isEmpty);
  });

  Map<String, dynamic> marker({
    bool navigating = true,
    double? heading = 90,
    bool arrowAvailable = true,
  }) =>
      navigationMarkerGeoJson(
        latitude: 17.2,
        longitude: -61.8,
        navigating: navigating,
        phoneHeadingDegrees: heading,
        arrowAvailable: arrowAvailable,
      );

  test('idle and stopped navigation use the circle even with a compass reading',
      () {
    final idle = marker(navigating: false);
    expect(idle['features'][0]['properties'],
        {'directional': false, 'heading': 0.0});
    expect(marker()['features'][0]['properties']['directional'], isTrue);
    expect(
        marker(navigating: false)['features'][0]['properties']['directional'],
        isFalse);
  });

  test('active arrow follows phone rotation while GPS position stays fixed',
      () {
    final east = marker();
    final west = marker(heading: 270);
    expect(east['features'][0]['properties'],
        {'directional': true, 'heading': 90.0});
    expect(west['features'][0]['properties'],
        {'directional': true, 'heading': 270.0});
    expect(east['features'][0]['geometry']['coordinates'], [-61.8, 17.2]);
    expect(west['features'][0]['geometry'], east['features'][0]['geometry']);
  });

  test(
      'phone heading is normalized relative to north without camera correction',
      () {
    expect(marker(heading: 450)['features'][0]['properties']['heading'], 90.0);
    expect(marker(heading: -90)['features'][0]['properties']['heading'], 270.0);
    expect(marker(heading: 360)['features'][0]['properties']['heading'], 0.0);
  });

  test('unavailable compass or arrow image falls back to the circle', () {
    for (final heading in [null, double.nan, double.infinity]) {
      expect(marker(heading: heading)['features'][0]['properties'],
          {'directional': false, 'heading': 0.0});
    }
    expect(
        marker(arrowAvailable: false)['features'][0]['properties']
            ['directional'],
        isFalse);
  });

  test('navigation marker waits for a valid GPS position', () {
    for (final lat in [null, double.nan, 91.0]) {
      expect(
          navigationMarkerGeoJson(
              latitude: lat,
              longitude: -61.8,
              navigating: true,
              phoneHeadingDegrees: 90)['features'],
          isEmpty);
    }
  });
}
