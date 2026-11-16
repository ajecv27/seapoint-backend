// SEAPOINT_LIVE_GUIDANCE_V1
import 'dart:convert';
import 'dart:math' as math;
import 'package:http/http.dart' as http;
import 'package:maplibre_gl/maplibre_gl.dart';

const liveGuidanceVersion = 'live-coast-guidance-v1';

double guidanceDistance(LatLng a, LatLng b) {
  final dx = (b.longitude - a.longitude) *
      111320 *
      math.cos(a.latitude * math.pi / 180);
  final dy = (b.latitude - a.latitude) * 111132;
  return math.sqrt(dx * dx + dy * dy);
}

double guidanceBearing(LatLng a, LatLng b) {
  final lat1 = a.latitude * math.pi / 180;
  final lat2 = b.latitude * math.pi / 180;
  final lon = (b.longitude - a.longitude) * math.pi / 180;
  return (math.atan2(
                  math.sin(lon) * math.cos(lat2),
                  math.cos(lat1) * math.sin(lat2) -
                      math.sin(lat1) * math.cos(lat2) * math.cos(lon)) *
              180 /
              math.pi +
          360) %
      360;
}

/// Match later segments even if a waypoint was bypassed. An equally close
/// parallel segment keeps its earlier index; progress cannot move backwards.
int guidanceLeg(
    LatLng position, List<LatLng> plan, int minimum, double accuracy) {
  final distances = <double>[];
  for (var i = minimum; i < plan.length - 1; i++) {
    final a = plan[i];
    final b = plan[i + 1];
    final sx = 111320 * math.cos(position.latitude * math.pi / 180);
    final dx = (b.longitude - a.longitude) * sx;
    final dy = (b.latitude - a.latitude) * 111132;
    final px = (position.longitude - a.longitude) * sx;
    final py = (position.latitude - a.latitude) * 111132;
    final squared = dx * dx + dy * dy;
    final t =
        squared == 0 ? 0.0 : ((px * dx + py * dy) / squared).clamp(0.0, 1.0);
    distances
        .add(math.sqrt(math.pow(px - t * dx, 2) + math.pow(py - t * dy, 2)));
  }
  if (distances.isEmpty) return minimum;
  final closest = distances.reduce(math.min);
  final tolerance = closest <= 150
      ? math.max(12, accuracy * 1.5)
      : math.max(100, accuracy * 2);
  var leg = minimum + distances.indexWhere((d) => d <= closest + tolerance);
  final radius = math.max(15, math.min(35, accuracy * 1.5));
  while (leg < plan.length - 2 &&
      guidanceDistance(position, plan[leg + 1]) <= radius) {
    leg++;
  }
  return leg;
}

class LiveGuidance {
  const LiveGuidance(this.points, this.leg, this.arrived, this.originRadius);
  final List<LatLng> points;
  final int leg;
  final bool arrived;
  final double originRadius;

  /// Only move the line's origin inside the water corridor certified by the
  /// server. Outside it, request a new check instead of drawing across land.
  bool covers(LatLng position) =>
      guidanceDistance(position, points.first) <= math.max(0.15, originRadius);

  List<LatLng> from(LatLng position) => [position, ...points.skip(1)];

  static LiveGuidance parse(Map<String, dynamic> body, LatLng origin,
      List<LatLng> planned, int minimum) {
    if (body['status'] != 'ok' ||
        body['guidance_version'] != liveGuidanceVersion ||
        body['coastline_dataset'] != 'caribbean-osm-gshhg-20261114-v1' ||
        body['coastline_policy'] != 'osm-primary-gshhg-unmatched-v1' ||
        body['depth_checked'] != false ||
        body['active_leg'] is! int ||
        body['arrived'] is! bool ||
        body['points'] is! List ||
        body['origin_radius_m'] is! num) {
      throw const FormatException('Unverified guidance response');
    }
    final leg = body['active_leg'] as int;
    final raw = body['points'] as List;
    final radius = (body['origin_radius_m'] as num).toDouble();
    if (leg < minimum ||
        leg >= planned.length - 1 ||
        raw.length < 2 ||
        raw.length > 4098 ||
        !radius.isFinite ||
        radius < 0 ||
        radius > 60) {
      throw const FormatException('Invalid guidance bounds');
    }
    final points = raw.map((p) {
      if (p is! List || p.length != 2 || p[0] is! num || p[1] is! num) {
        throw const FormatException('Invalid guidance point');
      }
      final lon = (p[0] as num).toDouble();
      final lat = (p[1] as num).toDouble();
      if (!lon.isFinite ||
          !lat.isFinite ||
          lon < -94 ||
          lon > -55 ||
          lat < 5 ||
          lat > 34) {
        throw const FormatException('Guidance outside checked coverage');
      }
      return LatLng(lat, lon);
    }).toList(growable: false);
    if (guidanceDistance(origin, points.first) > 0.15 ||
        guidanceDistance(planned.last, points.last) > 0.15) {
      throw const FormatException('Guidance endpoints changed');
    }
    return LiveGuidance(points, leg, body['arrived'] as bool, radius);
  }
}

Future<LiveGuidance> requestLiveGuidance(String baseUrl, LatLng position,
    List<LatLng> planned, int minimum, double accuracy, List<LatLng> previous,
    {http.Client? client}) async {
  final connection = client ?? http.Client();
  List<List<double>> coordinates(List<LatLng> points) =>
      points.map((p) => [p.longitude, p.latitude]).toList();
  try {
    final response = await connection
        .post(Uri.parse('$baseUrl/routing/guidance'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'position': [position.longitude, position.latitude],
              'planned': coordinates(planned),
              'active_leg': minimum,
              'accuracy_m': accuracy,
              'previous': coordinates(previous)
            }))
        .timeout(const Duration(seconds: 28));
    if (response.statusCode != 200 || response.body.length > 1000000) {
      throw const FormatException('Guidance temporarily unavailable');
    }
    return LiveGuidance.parse(jsonDecode(response.body) as Map<String, dynamic>,
        position, planned, minimum);
  } finally {
    if (client == null) connection.close();
  }
}
