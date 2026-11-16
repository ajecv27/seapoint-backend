import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'package:seapoint/live_guidance.dart';

void main() {
  const plan = [
    LatLng(17.18, -61.93),
    LatLng(17.10, -61.94),
    LatLng(17.05, -61.94),
    LatLng(17.05, -61.80),
    LatLng(17.05, -61.75)
  ];
  const current = LatLng(17.0501, -61.78);
  Map<String, dynamic> payload() => {
        'status': 'ok',
        'guidance_version': liveGuidanceVersion,
        'coastline_dataset': 'caribbean-osm-gshhg-20261114-v1',
        'coastline_policy': 'osm-primary-gshhg-unmatched-v1',
        'depth_checked': false,
        'active_leg': 3,
        'arrived': false,
        'origin_radius_m': 30,
        'points': [
          [-61.78, 17.0501],
          [-61.75, 17.05]
        ]
      };

  test('bypassed first three waypoints choose final eastbound leg', () {
    expect(guidanceLeg(current, plan, 0, 4), 3);
    final result = LiveGuidance.parse(payload(), current, plan, 0);
    expect(guidanceBearing(current, result.points[1]), closeTo(90, 1));
    // The old static first leg points approximately south, behind the vessel.
    expect(guidanceBearing(plan[0], plan[1]), greaterThan(180));
  });
  test('early trip stays on leg one; a resumed later leg cannot rewind', () {
    expect(guidanceLeg(const LatLng(17.15, -61.935), plan, 0, 4), 0);
    expect(guidanceLeg(plan[0], plan, 3, 4), 3);
  });
  test(
      'off-plan position can skip obsolete legs without touching every waypoint',
      () {
    expect(guidanceLeg(const LatLng(17.045, -61.78), plan, 0, 4), 3);
  });
  test('parallel segment ambiguity keeps earliest leg', () {
    const parallel = [
      LatLng(17, -62),
      LatLng(17, -61.99),
      LatLng(17.00008, -61.99),
      LatLng(17.00008, -62)
    ];
    expect(guidanceLeg(const LatLng(17.00006, -61.995), parallel, 0, 5), 0);
  });
  test('course uses the live origin inside the checked water corridor', () {
    final guidance = LiveGuidance.parse(payload(), current, plan, 0);
    const moved = LatLng(17.0502, -61.78);
    expect(guidance.covers(moved), isTrue);
    expect(guidance.from(moved).first, moved);
    expect(guidance.from(moved).last, plan.last);
    expect(guidanceBearing(moved, plan.last),
        greaterThan(guidanceBearing(current, plan.last)));
    expect(guidance.covers(const LatLng(17.051, -61.78)), isFalse);
  });
  test(
      'wrong source, target, origin, progress and nonfinite radius are rejected',
      () {
    for (final change in <Map<String, dynamic>>[
      {'coastline_dataset': 'unverified'},
      {'depth_checked': true},
      {'active_leg': 0},
      {'origin_radius_m': double.nan},
      {'origin_radius_m': 61},
      {
        'points': [
          [-61.78, 17.0501],
          [-61.74, 17.05]
        ]
      },
      {
        'points': [
          [-61.77, 17.0501],
          [-61.75, 17.05]
        ]
      },
      {
        'points': [
          [double.infinity, 17.05],
          [-61.75, 17.05]
        ]
      },
    ]) {
      expect(
          () => LiveGuidance.parse({...payload(), ...change}, current, plan, 3),
          throwsFormatException);
    }
  });
  test(
      'POST sends only current position and route, without trip track or stats',
      () async {
    final client = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/routing/guidance');
      final sent = jsonDecode(request.body) as Map;
      expect(sent.keys.toSet(),
          {'position', 'planned', 'active_leg', 'accuracy_m', 'previous'});
      expect(sent['position'], [-61.78, 17.0501]);
      expect(sent['planned'].last, [-61.75, 17.05]);
      return http.Response(jsonEncode(payload()), 200);
    });
    final result = await requestLiveGuidance(
        'https://example.test', current, plan, 0, 4, [],
        client: client);
    expect(result.leg, 3);
  });
  test('network or backend failure never invents a direct guidance line',
      () async {
    final client =
        MockClient((_) async => http.Response('{"status":"error"}', 503));
    await expectLater(
        requestLiveGuidance('https://example.test', current, plan, 0, 4, [],
            client: client),
        throwsFormatException);
  });
}
