import 'trip_recorder.dart';

/// Each GPS segment stays separate so an outage never draws an invented leg.
Map<String, dynamic> tripTrackGeoJson(Iterable<List<GpsFix>> segments) {
  final lines = segments.where((segment) => segment.length >= 2).map(
    (segment) => segment.map((fix) => [fix.longitude, fix.latitude]).toList(),
  ).toList();
  return {
    'type': 'FeatureCollection',
    'features': [
      if (lines.isNotEmpty) {
        'type': 'Feature',
        'properties': <String, dynamic>{},
        'geometry': {'type': 'MultiLineString', 'coordinates': lines},
      },
    ],
  };
}

/// GPS course is measured clockwise from true north. It is independent of the
/// phone compass and the map camera bearing.
Map<String, dynamic> boatGeoJson({
  required double? latitude,
  required double? longitude,
  required double courseDegrees,
}) => {
  'type': 'FeatureCollection',
  'features': [
    if (latitude != null && longitude != null) {
      'type': 'Feature',
      'properties': {'course': courseDegrees},
      'geometry': {'type': 'Point', 'coordinates': [longitude, latitude]},
    },
  ],
};
