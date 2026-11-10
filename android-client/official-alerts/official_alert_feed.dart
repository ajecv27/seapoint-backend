import 'dart:convert';

/// Named alerts and the sources' coverage are separate facts: an empty legacy
/// or failed response cannot establish that there are no official warnings.
class OfficialAlertFeed {
  OfficialAlertFeed._(
      {required this.alerts,
      required this.links,
      required this.status,
      required this.sourceMetadata});

  factory OfficialAlertFeed.fromJson(Map<String, dynamic> json) {
    final rawAlerts = json['alerts'];
    if (rawAlerts is! List ||
        rawAlerts.any((alert) => alert is! String || alert.trim().isEmpty)) {
      throw const FormatException('Missing or invalid official alerts list');
    }
    final alerts =
        rawAlerts.cast<String>().map((alert) => alert.trim()).toSet().toList();
    final links = <String, String>{};
    if (json['links'] is Map) {
      for (final entry in (json['links'] as Map).entries) {
        if (entry.key is! String || entry.value is! String) continue;
        final uri = Uri.tryParse((entry.value as String).trim());
        if (uri != null &&
            uri.scheme == 'https' &&
            uri.userInfo.isEmpty &&
            const ['antiguamet.com', 'www.antiguamet.com']
                .contains(uri.host.toLowerCase())) {
          links[(entry.key as String).trim()] = uri.toString();
        }
      }
    }
    var stated = json['status'];
    if (stated == 'ready' &&
        json['checked'] is Map &&
        (json['checked'] as Map).values.any((source) => source is Map
            ? source['state'] == 'unknown' || source['cached'] == true
            : source is String &&
                (source.contains('error') || source.contains('unavailable')))) {
      stated = 'partial';
    }
    return OfficialAlertFeed._(
      alerts: List.unmodifiable(alerts),
      links: Map.unmodifiable(links),
      status: const ['ready', 'partial', 'unavailable'].contains(stated)
          ? stated as String
          : 'unknown',
      sourceMetadata: Map.unmodifiable(Map<String, dynamic>.from(json)
        ..remove('alerts')
        ..remove('links')
        ..remove('status')),
    );
  }

  factory OfficialAlertFeed.fromLegacyCache(List<dynamic> alerts,
          {DateTime? checkedAt}) =>
      OfficialAlertFeed.fromJson({
        'alerts': alerts,
        if (checkedAt != null) 'checked_at': checkedAt.toUtc().toIso8601String()
      });

  final List<String> alerts;
  final Map<String, String> links;
  final String status;
  final Map<String, dynamic> sourceMetadata;
  static const maximumUnknownExpiryAge = Duration(hours: 6);

  Map<String, dynamic> _map(String key) => sourceMetadata[key] is Map
      ? Map<String, dynamic>.from(sourceMetadata[key] as Map)
      : {};
  Map<String, dynamic> _source(String? key) {
    final value = key == null ? null : _map('checked')[key];
    return value is Map ? Map<String, dynamic>.from(value) : {};
  }

  DateTime? _time(Object? value) =>
      value is String ? DateTime.tryParse(value)?.toUtc() : null;

  String? _sourceKey(String name,
      {OfficialAlertFeed? other,
      Map<String, String> fallbackLinks = const {}}) {
    final mapped = _map('alert_sources')[name];
    if (mapped is String) return mapped;
    for (final report in [this, if (other != null) other]) {
      for (final entry in report._map('checked').entries) {
        if (entry.value is! Map) continue;
        final source = entry.value as Map;
        if (source['alerts'] is List &&
            (source['alerts'] as List).contains(name)) {
          return entry.key;
        }
        final link = links[name] ?? fallbackLinks[name];
        if (link != null && source['url'] == link) return entry.key;
      }
    }
    if ((other?._map('checked') ?? {}).containsKey('marine:$name')) {
      return 'marine:$name';
    }
    return null;
  }

  DateTime? _observedAt(String name, {DateTime? fallback}) {
    final saved = _map('client_alert_observed_at');
    if (saved.containsKey(name)) return _time(saved[name]);
    return _time(_source(_sourceKey(name))['checked_at']) ??
        _time(sourceMetadata['checked_at']) ??
        fallback?.toUtc();
  }

  /// A names-only rollback cache must keep the original observation clock,
  /// rather than the receipt time of a failed/incomplete later refresh.
  DateTime? get oldestAlertObservation {
    DateTime? oldest;
    for (final name in alerts) {
      final observed = _observedAt(name);
      if (observed == null) return null;
      if (oldest == null || observed.isBefore(oldest)) {
        oldest = observed;
      }
    }
    return oldest;
  }

  DateTime? _expiresAt(String name) =>
      _time(_map('client_alert_expires')[name]) ??
      _time(_source(_sourceKey(name))['expires']);
  DateTime? _freshUntil(String name) =>
      _time(_map('client_alert_fresh_until')[name]) ??
      _time(_source(_sourceKey(name))['fresh_until']);

  /// Fresh successful source checks may update observation clocks. Failed or
  /// cached checks reuse the original clock, never extending stale alerts.
  OfficialAlertFeed recordingObservation(DateTime receivedAt,
      {OfficialAlertFeed? previous}) {
    final observed = <String, dynamic>{};
    final expires = <String, String>{};
    final freshUntil = <String, String>{};
    for (final name in alerts) {
      final source = _source(_sourceKey(name));
      final fresh = source['state'] == 'active' && source['cached'] != true;
      final sourceTime = _time(source['checked_at']);
      final previousTime = previous?._observedAt(name);
      DateTime? when;
      if (fresh) {
        when = sourceTime ??
            _time(sourceMetadata['checked_at']) ??
            receivedAt.toUtc();
      } else if (previous?.alerts.contains(name) == true) {
        when = previousTime == null
            ? sourceTime
            : sourceTime == null || previousTime.isBefore(sourceTime)
                ? previousTime
                : sourceTime;
      } else if (source['cached'] == true || source['state'] == 'unknown') {
        when = sourceTime;
      } else {
        when = sourceTime ??
            _time(sourceMetadata['checked_at']) ??
            receivedAt.toUtc();
      }
      observed[name] = when?.toIso8601String();
      final expiry =
          _expiresAt(name) ?? (fresh ? null : previous?._expiresAt(name));
      final limit =
          _freshUntil(name) ?? (fresh ? null : previous?._freshUntil(name));
      if (expiry != null) expires[name] = expiry.toIso8601String();
      if (limit != null) freshUntil[name] = limit.toIso8601String();
    }
    return OfficialAlertFeed.fromJson({
      ...toJson(),
      'client_alert_observed_at': observed,
      'client_alert_expires': expires,
      'client_alert_fresh_until': freshUntil
    });
  }

  bool _validCachedName(String name, DateTime now,
      {DateTime? fallbackCheckedAt}) {
    final expiry = _expiresAt(name);
    final freshnessLimit = _freshUntil(name);
    if (expiry != null && !now.isBefore(expiry)) return false;
    if (freshnessLimit != null && !now.isBefore(freshnessLimit)) return false;
    if (expiry != null) return true;
    final observed = _observedAt(name, fallback: fallbackCheckedAt);
    return observed != null &&
        now.difference(observed) < maximumUnknownExpiryAge &&
        observed.difference(now) <= const Duration(minutes: 2);
  }

  OfficialAlertFeed validCachedAlertsAt(DateTime now,
      {DateTime? fallbackCheckedAt}) {
    final kept = alerts
        .where((name) => _validCachedName(name, now.toUtc(),
            fallbackCheckedAt: fallbackCheckedAt))
        .toList();
    if (kept.length == alerts.length) return this;
    return OfficialAlertFeed.fromJson({
      ...toJson(),
      'alerts': kept,
      'links': {
        for (final name in kept)
          if (links[name] != null) name: links[name]
      },
      'status': status == 'ready' ? 'partial' : status,
      'expired_cached_alerts':
          alerts.where((name) => !kept.contains(name)).toList(),
      if (sourceMetadata['retained_alerts'] is List)
        'retained_alerts': (sourceMetadata['retained_alerts'] as List)
            .where(kept.contains)
            .toList()
    });
  }

  /// Source-specific verified inactivity clears its old warning even if an
  /// unrelated source is unavailable. Only unresolved, unexpired names survive.
  OfficialAlertFeed retainingUnverifiedAlerts(
    OfficialAlertFeed? previous, {
    DateTime? now,
    Map<String, String> fallbackLinks = const {},
  }) {
    if (status == 'ready' || previous == null) return this;
    final clock = (now ?? DateTime.now()).toUtc();
    final retained = <String>[];
    final sources = _map('alert_sources');
    final observed = _map('client_alert_observed_at');
    final expires = _map('client_alert_expires');
    final freshUntil = _map('client_alert_fresh_until');
    for (final name
        in previous.alerts.where((name) => !alerts.contains(name))) {
      final sourceKey =
          previous._sourceKey(name, other: this, fallbackLinks: fallbackLinks);
      final source = _source(sourceKey);
      if (source['state'] == 'inactive' || source['state'] == 'active') {
        continue;
      }
      if (!previous._validCachedName(name, clock)) continue;
      retained.add(name);
      if (sourceKey != null) sources[name] = sourceKey;
      final when = previous._observedAt(name);
      final end = previous._expiresAt(name);
      final limit = previous._freshUntil(name);
      if (when != null) observed[name] = when.toIso8601String();
      if (end != null) expires[name] = end.toIso8601String();
      if (limit != null) freshUntil[name] = limit.toIso8601String();
    }
    if (retained.isEmpty) return this;
    return OfficialAlertFeed.fromJson({
      ...toJson(),
      'alerts': [...alerts, ...retained],
      'links': {...previous.links, ...links},
      'alert_sources': sources,
      'client_alert_observed_at': observed,
      'client_alert_expires': expires,
      'client_alert_fresh_until': freshUntil,
      'retained_alerts': retained
    });
  }

  String statusText(
      {bool cached = false, bool verifying = false, bool unavailable = false}) {
    final names = alerts.join(' • ');
    if (verifying) {
      return alerts.isEmpty
          ? 'Checking official alert coverage...'
          : '$names (verifying official coverage...)';
    }
    if (cached) {
      return alerts.isEmpty
          ? 'No alerts in the saved report — current status unverified'
          : '$names (cached — status unverified)';
    }
    final effectiveStatus = unavailable ? 'unavailable' : status;
    if (sourceMetadata['retained_alerts'] is List &&
        (sourceMetadata['retained_alerts'] as List).isNotEmpty) {
      return '$names (includes cached alerts; source checks incomplete — status unverified)';
    }
    final hasSourceCache = _map('checked')
        .values
        .any((source) => source is Map && source['cached'] == true);
    if (hasSourceCache && alerts.isNotEmpty) {
      return '$names (includes cached alerts — status unverified)';
    }
    switch (effectiveStatus) {
      case 'ready':
        return alerts.isEmpty
            ? 'No active watches, warnings or advisories reported by the checked sources'
            : names;
      case 'partial':
        return alerts.isEmpty
            ? 'Official alert checks incomplete — status unverified'
            : '$names (additional alert checks incomplete — status unverified)';
      case 'unavailable':
        return alerts.isEmpty
            ? 'Official warning sources unavailable — status unverified'
            : '$names (latest alert check unavailable — status unverified)';
      default:
        return alerts.isEmpty
            ? 'Official alert coverage unverified'
            : '$names (coverage unverified)';
    }
  }

  Map<String, dynamic> toJson() =>
      {...sourceMetadata, 'alerts': alerts, 'links': links, 'status': status};

  String get sourceDetails {
    final description = switch (status) {
      'ready' => 'All configured alert sources checked',
      'partial' => 'Some official alert checks are incomplete',
      'unavailable' => 'Official alert sources unavailable',
      _ => 'Official source coverage unverified',
    };
    final details = <String>['Alert coverage: $description'];
    for (final key in [
      'checked_at',
      'coverage',
      'checked',
      'sources',
      'diagnostics'
    ]) {
      if (sourceMetadata[key] != null) {
        details.add('$key: ${jsonEncode(sourceMetadata[key])}');
      }
    }
    return details.join('\n');
  }
}

/// The backend uses 503 for incomplete empty coverage, protecting older clients
/// from false absence claims. Its structured diagnostics remain useful here.
OfficialAlertFeed parseOfficialAlertResponse(int statusCode, String body) {
  if (statusCode != 200 && statusCode != 503) {
    throw StateError('Official alert service returned $statusCode');
  }
  final decoded = jsonDecode(body);
  if (decoded is! Map<String, dynamic>) {
    throw const FormatException('Invalid official alert report');
  }
  if (statusCode == 503 &&
      decoded['status'] != 'partial' &&
      decoded['status'] != 'unavailable') {
    throw const FormatException(
        'Unavailable service omitted alert coverage status');
  }
  return OfficialAlertFeed.fromJson(decoded);
}
