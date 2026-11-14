import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

const hostedRoutingUrl = 'https://seapoint-backend.onrender.com';

String routingBaseUrl(String override) => override.isEmpty
    ? hostedRoutingUrl
    : override.replaceFirst(RegExp(r'/+$'), '');

class RoutingRequestException implements Exception {
  const RoutingRequestException(this.message);
  final String message;
  @override
  String toString() => message;
}

class RoutingRequestCancelled implements Exception {}

/// The same HTTPS endpoint works on the phone without a USB connection or
/// local Docker service. Retry only explicitly transient warming/busy replies.
Future<http.Response> requestMarineRoute(
  Uri uri, {
  http.Client? client,
  Duration budget = const Duration(seconds: 55),
  Future<void> Function(Duration)? pause,
  bool Function()? isCurrent,
}) async {
  final connection = client ?? http.Client();
  final elapsed = Stopwatch()..start();
  final delay = pause ?? Future<void>.delayed;
  try {
    for (var attempt = 0; attempt < 16; attempt++) {
      if (isCurrent != null && !isCurrent()) throw RoutingRequestCancelled();
      final remaining = budget - elapsed.elapsed;
      if (remaining <= Duration.zero) throw TimeoutException('Routing timeout');
      final response = await connection.get(uri).timeout(remaining);
      if (isCurrent != null && !isCurrent()) throw RoutingRequestCancelled();
      dynamic body;
      try {
        body = jsonDecode(response.body);
      } on FormatException {
        throw const RoutingRequestException(
          'The routing service could not respond. Please try again shortly.',
        );
      }
      final retry =
          (response.statusCode == 429 || response.statusCode == 503) &&
              body is Map &&
              body['retryable'] == true;
      if (!retry || attempt == 15) return response;
      final suggested = body['retry_after_s'];
      final seconds = suggested is num ? suggested.toInt().clamp(1, 3) : 2;
      final wait = Duration(seconds: seconds);
      if (elapsed.elapsed + wait >= budget) return response;
      await delay(wait);
    }
    throw const RoutingRequestException(
        'Routing is busy. Please try again shortly.');
  } on TimeoutException {
    throw const RoutingRequestException(
      'Routing is taking too long. Check your connection and try again.',
    );
  } on http.ClientException {
    throw const RoutingRequestException(
      'Could not connect to routing. Check your internet connection and try again.',
    );
  } finally {
    if (client == null) connection.close();
  }
}
