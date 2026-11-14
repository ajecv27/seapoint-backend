import 'dart:async';
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:seapoint/routing_api.dart';

void main() {
  final uri = Uri.parse(
      '$hostedRoutingUrl/route?start_lat=17&start_lon=-62&end_lat=17&end_lon=-61.8');
  test('default routing is hosted HTTPS with explicit local overrides retained',
      () {
    expect(routingBaseUrl(''), hostedRoutingUrl);
    expect(routingBaseUrl('http://127.0.0.1:8083///'), 'http://127.0.0.1:8083');
  });
  test('warming replies retry the same coordinates and then return the route',
      () async {
    var calls = 0;
    final client = MockClient((request) async {
      expect(request.url, uri);
      calls++;
      return calls == 1
          ? http.Response(
              jsonEncode({'retryable': true, 'retry_after_s': 2}), 503)
          : http.Response('{"status":"ok","points":[]}', 200);
    });
    final waits = <Duration>[];
    final response =
        await requestMarineRoute(uri, client: client, pause: (wait) async {
      waits.add(wait);
    });
    expect(response.statusCode, 200);
    expect(calls, 2);
    expect(waits, [const Duration(seconds: 2)]);
  });
  test('land errors and unavailable data do not trigger retry loops', () async {
    for (final status in [400, 503]) {
      var calls = 0;
      final client = MockClient((_) async {
        calls++;
        return http.Response('{"status":"error","retryable":false}', status);
      });
      expect(
          (await requestMarineRoute(uri, client: client)).statusCode, status);
      expect(calls, 1);
    }
  });
  test('busy replies are bounded and excessive retry delays are clamped',
      () async {
    var calls = 0;
    final client = MockClient((_) async {
      calls++;
      return http.Response('{"retryable":true,"retry_after_s":100}', 429);
    });
    await requestMarineRoute(uri, client: client, pause: (wait) async {
      expect(wait, const Duration(seconds: 3));
    });
    expect(calls, 16);
  });
  test('changing the route stops subsequent retries', () async {
    var current = true, calls = 0;
    final client = MockClient((_) async {
      calls++;
      return http.Response('{"retryable":true}', 503);
    });
    await expectLater(
        requestMarineRoute(uri,
            client: client,
            isCurrent: () => current,
            pause: (_) async {
              current = false;
            }),
        throwsA(isA<RoutingRequestCancelled>()));
    expect(calls, 1);
  });
  test(
      'network failures, timeouts and unreadable responses have complete messages',
      () async {
    final cases = [
      MockClient((_) async => throw http.ClientException('test outage')),
      MockClient((_) async => throw TimeoutException('test timeout')),
      MockClient((_) async => http.Response('<html>unavailable</html>', 503)),
    ];
    for (final client in cases) {
      await expectLater(requestMarineRoute(uri, client: client),
          throwsA(isA<RoutingRequestException>()));
    }
  });
}
