import 'package:flutter_test/flutter_test.dart';
import 'package:seapoint/trip_map.dart';
import 'package:seapoint/trip_recorder.dart';

GpsFix fix(double lat, double lon) => GpsFix(latitude: lat, longitude: lon,
  timestamp: DateTime.utc(2026), accuracyMetres: 3);

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
      [[-61.0, 17.0], [-61.1, 17.1]],
      [[-62.0, 18.0], [-62.1, 18.1]],
    ]);
  });
  test('one GPS point cannot imply a travelled line', () {
    expect(tripTrackGeoJson([[fix(17, -61)]])['features'], isEmpty);
  });
  test('boat feature carries GPS course and real coordinates', () {
    final result = boatGeoJson(latitude: 17.2, longitude: -61.8, courseDegrees: 123);
    expect(result['features'][0]['properties']['course'], 123);
    expect(result['features'][0]['geometry']['coordinates'], [-61.8, 17.2]);
    expect(boatGeoJson(latitude: null, longitude: null, courseDegrees: 0)['features'], isEmpty);
  });
}
