import 'trip_recorder.dart';

/// Each GPS segment stays separate so an outage never draws an invented leg.
Map<String, dynamic> tripTrackGeoJson(Iterable<List<GpsFix>> segments) {
  final lines = segments
      .where((segment) => segment.length >= 2)
      .map(
        (segment) =>
            segment.map((fix) => [fix.longitude, fix.latitude]).toList(),
      )
      .toList();
  return {
    'type': 'FeatureCollection',
    'features': [
      if (lines.isNotEmpty)
        {
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
}) =>
    {
      'type': 'FeatureCollection',
      'features': [
        if (latitude != null && longitude != null)
          {
            'type': 'Feature',
            'properties': {'course': courseDegrees},
            'geometry': {
              'type': 'Point',
              'coordinates': [longitude, latitude]
            },
          },
      ],
    };

/// Phone orientation controls only the active navigation arrow. GPS course
/// remains independent in the trip recorder and statistics. A missing compass
/// or unavailable arrow asset uses the original location circle instead.
Map<String, dynamic> navigationMarkerGeoJson({
  required double? latitude,
  required double? longitude,
  required bool navigating,
  required double? phoneHeadingDegrees,
  bool arrowAvailable = true,
}) {
  final directional = navigating &&
      arrowAvailable &&
      phoneHeadingDegrees != null &&
      phoneHeadingDegrees.isFinite;
  final validPosition = latitude != null &&
      longitude != null &&
      latitude.isFinite &&
      longitude.isFinite &&
      latitude >= -90 &&
      latitude <= 90 &&
      longitude >= -180 &&
      longitude <= 180;
  return {
    'type': 'FeatureCollection',
    'features': [
      if (validPosition)
        {
          'type': 'Feature',
          'properties': {
            'directional': directional,
            // This is north-relative. Map-aligned rotation handles camera bearing.
            'heading':
                directional ? (phoneHeadingDegrees % 360 + 360) % 360 : 0.0,
          },
          'geometry': {
            'type': 'Point',
            'coordinates': [longitude, latitude]
          },
        },
    ],
  };
}
