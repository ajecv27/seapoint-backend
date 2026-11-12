import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:seapoint/official_alert_feed.dart';

void main() {
  test('all named official alert categories and their canonical links survive',
      () {
    final names = [
      'Tropical Storm Watch',
      'Tropical Storm Warning',
      'Hurricane Watch',
      'Hurricane Warning',
      'Small Craft Advisory',
      'Small Craft Warning',
      'Flash Flood Warning'
    ];
    final report = OfficialAlertFeed.fromJson({
      'alerts': names,
      'links': {
        for (final name in names)
          name: 'https://www.antiguamet.com/${Uri.encodeComponent(name)}.pdf'
      },
      'status': 'ready',
      'checked_at': '2026-11-10T01:00:00Z',
      'coverage': {'marine': 'ready', 'cyclone': 'ready', 'general': 'ready'},
    });
    expect(report.alerts, names);
    expect(report.links.length, names.length);
    for (final name in names) {
      expect(report.statusText(), contains(name));
    }
    expect(report.statusText(), isNot(contains('unverified')));
  });

  test('only a ready empty report may state no active alerts were reported',
      () {
    final ready = OfficialAlertFeed.fromJson({'alerts': [], 'status': 'ready'});
    expect(ready.statusText(),
        contains('No active watches, warnings or advisories'));
    for (final status in ['partial', 'unavailable', 'unknown']) {
      final report =
          OfficialAlertFeed.fromJson({'alerts': [], 'status': status});
      expect(report.statusText(), contains('unverified'));
      expect(report.statusText(), isNot(contains('No active')));
    }
  });

  test(
      'legacy empty success with failed source checks cannot imply an all-clear',
      () {
    final report = OfficialAlertFeed.fromJson({
      'alerts': [],
      'checked': {
        'Small Craft Warning': 'error',
        'High Surf Warning': 'bulletin_error'
      },
    });
    expect(report.status, 'unknown');
    expect(report.statusText(), 'Official alert coverage unverified');
    expect(report.toJson()['checked'],
        containsPair('High Surf Warning', 'bulletin_error'));
  });

  test('partial and unavailable coverage still show every reported active name',
      () {
    for (final status in ['partial', 'unavailable']) {
      final report = OfficialAlertFeed.fromJson({
        'alerts': ['Hurricane Watch', 'Small Craft Warning'],
        'status': status,
      });
      expect(report.statusText(),
          contains('Hurricane Watch • Small Craft Warning'));
      expect(report.statusText(), contains('unverified'));
    }
  });

  test('cached ready data is always explicitly unverified', () {
    final active = OfficialAlertFeed.fromJson({
      'alerts': ['Hurricane Warning'],
      'status': 'ready'
    });
    expect(active.statusText(cached: true),
        'Hurricane Warning (cached — status unverified)');
    final empty = OfficialAlertFeed.fromJson({'alerts': [], 'status': 'ready'});
    expect(
        empty.statusText(cached: true), contains('current status unverified'));
    expect(empty.statusText(cached: true), isNot(contains('No active')));
  });

  test('source status, coverage and alert URLs round trip in the cached report',
      () {
    final report = OfficialAlertFeed.fromJson({
      'alerts': ['Tropical Storm Watch'],
      'links': {'Tropical Storm Watch': 'https://www.antiguamet.com/watch.pdf'},
      'status': 'partial',
      'checked_at': '2026-11-10T01:00:00Z',
      'coverage': {'cyclone': true, 'marine': false},
      'diagnostics': ['Marine source unavailable'],
    });
    final cached = OfficialAlertFeed.fromJson(
        jsonDecode(jsonEncode(report.toJson())) as Map<String, dynamic>);
    expect(cached.links, report.links);
    expect(cached.status, 'partial');
    expect(cached.sourceMetadata, report.sourceMetadata);
    expect(cached.sourceDetails, contains('Marine source unavailable'));
    expect(cached.statusText(cached: true),
        contains('cached — status unverified'));
  });

  test('non-web or credential-bearing URLs cannot become launch targets', () {
    final report = OfficialAlertFeed.fromJson({
      'alerts': ['Hurricane Watch'],
      'status': 'ready',
      'links': {
        'Hurricane Watch': 'javascript:alert(1)',
        'A': 'file:///etc/passwd',
        'B': 'https://user:password@example.com/a.pdf',
        'C': 'https://www.antiguamet.com/c.pdf',
        'D': 'https://unrelated.example/false-warning.pdf'
      },
    });
    expect(report.links, {'C': 'https://www.antiguamet.com/c.pdf'});
  });

  test(
      'incomplete refresh retains earlier warnings and links as explicitly unverified',
      () {
    final clock = DateTime.utc(2026, 11, 10, 1);
    final previous = OfficialAlertFeed.fromJson({
      'checked_at': clock.toIso8601String(),
      'alerts': ['Small Craft Warning'],
      'links': {
        'Small Craft Warning': 'https://www.antiguamet.com/small-craft.pdf'
      },
      'status': 'ready',
    });
    final partial = OfficialAlertFeed.fromJson({
      'alerts': ['Hurricane Watch'],
      'links': {'Hurricane Watch': 'https://www.antiguamet.com/hurricane.pdf'},
      'status': 'partial',
    }).retainingUnverifiedAlerts(previous, now: clock);
    expect(partial.alerts, ['Hurricane Watch', 'Small Craft Warning']);
    expect(partial.links.length, 2);
    expect(partial.statusText(), contains('includes cached alerts'));
    expect(partial.statusText(), contains('unverified'));
    final unavailable =
        OfficialAlertFeed.fromJson({'alerts': [], 'status': 'unavailable'})
            .retainingUnverifiedAlerts(previous, now: clock);
    expect(unavailable.alerts, ['Small Craft Warning']);
    final ready = OfficialAlertFeed.fromJson({'alerts': [], 'status': 'ready'})
        .retainingUnverifiedAlerts(previous, now: clock);
    expect(ready.alerts, isEmpty);
  });

  test('invalid alerts cannot silently become an empty verified result', () {
    for (final value in [
      null,
      'none',
      [null],
      ['']
    ]) {
      expect(
          () =>
              OfficialAlertFeed.fromJson({'alerts': value, 'status': 'ready'}),
          throwsFormatException);
    }
  });

  test(
      'legacy cached names are kept, with unknown coverage and no verification',
      () {
    final report = OfficialAlertFeed.fromLegacyCache(['Small Craft Advisory']);
    expect(report.status, 'unknown');
    expect(report.statusText(cached: true),
        'Small Craft Advisory (cached — status unverified)');
  });
  test(
      'a verified inactive source clears its cached warning despite unrelated unknown coverage',
      () {
    final clock = DateTime.utc(2026, 11, 10, 1);
    final previous = OfficialAlertFeed.fromJson({
      'alerts': ['Small Craft Warning'],
      'status': 'ready',
      'alert_sources': {'Small Craft Warning': 'marine:Small Craft Warning'},
      'checked': {
        'marine:Small Craft Warning': {
          'state': 'active',
          'checked_at': clock.toIso8601String(),
          'alerts': ['Small Craft Warning']
        }
      },
    }).recordingObservation(clock);
    final next = OfficialAlertFeed.fromJson({
      'alerts': [],
      'status': 'partial',
      'checked': {
        'marine:Small Craft Warning': {'state': 'inactive', 'alerts': []},
        'tropical:watch': {'state': 'unknown', 'reason': 'source_error'}
      },
    }).retainingUnverifiedAlerts(previous,
        now: clock.add(const Duration(minutes: 5)));
    expect(next.alerts, isEmpty);
    expect(next.statusText(), contains('unverified'));
  });

  test('changed active source names replace the earlier island watch', () {
    final clock = DateTime.utc(2026, 11, 10, 1);
    final previous = OfficialAlertFeed.fromJson({
      'alerts': ['Tropical Storm Watch — Antigua'],
      'status': 'ready',
      'alert_sources': {'Tropical Storm Watch — Antigua': 'tropical:watch'},
      'checked': {
        'tropical:watch': {
          'state': 'active',
          'checked_at': clock.toIso8601String(),
          'alerts': ['Tropical Storm Watch — Antigua']
        }
      },
    }).recordingObservation(clock);
    final next = OfficialAlertFeed.fromJson({
      'alerts': ['Hurricane Watch — Barbuda'],
      'status': 'partial',
      'alert_sources': {'Hurricane Watch — Barbuda': 'tropical:watch'},
      'checked': {
        'tropical:watch': {
          'state': 'active',
          'checked_at': clock.add(const Duration(minutes: 5)).toIso8601String(),
          'alerts': ['Hurricane Watch — Barbuda']
        },
        'flood:watch': {'state': 'unknown'}
      },
    })
        .recordingObservation(clock.add(const Duration(minutes: 5)),
            previous: previous)
        .retainingUnverifiedAlerts(previous,
            now: clock.add(const Duration(minutes: 5)));
    expect(next.alerts, ['Hurricane Watch — Barbuda']);
  });

  test('unknown source retains a watch only within its explicit expiry', () {
    final clock = DateTime.utc(2026, 11, 10, 1);
    final previous = OfficialAlertFeed.fromJson({
      'alerts': ['Hurricane Watch — Antigua'],
      'status': 'ready',
      'alert_sources': {'Hurricane Watch — Antigua': 'tropical:watch'},
      'checked': {
        'tropical:watch': {
          'state': 'active',
          'checked_at': clock.toIso8601String(),
          'expires': clock.add(const Duration(hours: 1)).toIso8601String(),
          'alerts': ['Hurricane Watch — Antigua']
        }
      },
    }).recordingObservation(clock);
    final unresolved = OfficialAlertFeed.fromJson({
      'alerts': [],
      'status': 'partial',
      'checked': {
        'tropical:watch': {'state': 'unknown', 'reason': 'source_error'}
      }
    });
    expect(
        unresolved
            .retainingUnverifiedAlerts(previous,
                now: clock.add(const Duration(minutes: 30)))
            .alerts,
        ['Hurricane Watch — Antigua']);
    final expired = unresolved.retainingUnverifiedAlerts(previous,
        now: clock.add(const Duration(hours: 1)));
    expect(expired.alerts, isEmpty);
    expect(expired.statusText(), contains('unverified'));
    final offline =
        previous.validCachedAlertsAt(clock.add(const Duration(hours: 1)));
    expect(offline.alerts, isEmpty);
    expect(offline.status, 'partial');
  });

  test('failed refreshes cannot renew the six-hour original observation clock',
      () {
    final clock = DateTime.utc(2026, 11, 10, 1);
    final original = OfficialAlertFeed.fromJson({
      'alerts': ['Small Craft Advisory'],
      'status': 'ready',
      'checked_at': clock.toIso8601String()
    }).recordingObservation(clock);
    final fiveHours = clock.add(const Duration(hours: 5));
    final failed = OfficialAlertFeed.fromJson({
      'alerts': [],
      'status': 'partial',
      'checked_at': fiveHours.toIso8601String()
    })
        .recordingObservation(fiveHours, previous: original)
        .retainingUnverifiedAlerts(original, now: fiveHours);
    expect(failed.alerts, ['Small Craft Advisory']);
    expect(failed.oldestAlertObservation, clock);
    final sevenHours = clock.add(const Duration(hours: 7));
    final failedAgain = OfficialAlertFeed.fromJson({
      'alerts': [],
      'status': 'partial',
      'checked_at': sevenHours.toIso8601String()
    })
        .recordingObservation(sevenHours, previous: failed)
        .retainingUnverifiedAlerts(failed, now: sevenHours);
    expect(failedAgain.alerts, isEmpty);
    expect(failedAgain.statusText(), contains('unverified'));
  });

  test(
      'backend cached-source times are not replaced by the latest refresh time',
      () {
    final clock = DateTime.utc(2026, 11, 10, 1);
    final now = clock.add(const Duration(hours: 7));
    final report = OfficialAlertFeed.fromJson({
      'alerts': ['Small Craft Warning'],
      'status': 'partial',
      'checked_at': now.toIso8601String(),
      'alert_sources': {'Small Craft Warning': 'marine:Small Craft Warning'},
      'checked': {
        'marine:Small Craft Warning': {
          'state': 'unknown',
          'cached': true,
          'checked_at': clock.toIso8601String(),
          'alerts': ['Small Craft Warning']
        }
      },
    }).recordingObservation(now).validCachedAlertsAt(now);
    expect(report.alerts, isEmpty);
    expect(report.statusText(), contains('unverified'));
  });

  test('freshly renewed source data cannot inherit an old expired lifetime',
      () {
    final clock = DateTime.utc(2026, 11, 10, 1);
    final previous = OfficialAlertFeed.fromJson({
      'alerts': ['Small Craft Warning'],
      'status': 'ready',
      'alert_sources': {'Small Craft Warning': 'marine:Small Craft Warning'},
      'checked': {
        'marine:Small Craft Warning': {
          'state': 'active',
          'checked_at': clock.toIso8601String(),
          'expires': clock.add(const Duration(hours: 1)).toIso8601String()
        }
      },
    }).recordingObservation(clock);
    final now = clock.add(const Duration(hours: 2));
    final renewed = OfficialAlertFeed.fromJson({
      'alerts': ['Small Craft Warning'],
      'status': 'ready',
      'alert_sources': {'Small Craft Warning': 'marine:Small Craft Warning'},
      'checked': {
        'marine:Small Craft Warning': {
          'state': 'active',
          'checked_at': now.toIso8601String()
        }
      },
    }).recordingObservation(now, previous: previous).validCachedAlertsAt(now);
    expect(renewed.alerts, ['Small Craft Warning']);
  });

  test('legacy marine names can be cleared using the checked canonical URL',
      () {
    final clock = DateTime.utc(2026, 11, 10, 1);
    const link =
        'https://www.antiguamet.com/Antigua_Met_files/SmallCraftWARNING.pdf';
    final previous = OfficialAlertFeed.fromLegacyCache(['Small Craft Warning'],
        checkedAt: clock);
    final next = OfficialAlertFeed.fromJson({
      'alerts': [],
      'status': 'partial',
      'checked': {
        'marine:small_craft': {'state': 'inactive', 'url': link, 'alerts': []}
      },
    }).retainingUnverifiedAlerts(previous,
        now: clock.add(const Duration(minutes: 5)),
        fallbackLinks: {'Small Craft Warning': link});
    expect(next.alerts, isEmpty);
  });

  test('ready cannot override an explicit unknown or cached source diagnostic',
      () {
    final report = OfficialAlertFeed.fromJson({
      'alerts': [],
      'status': 'ready',
      'checked': {
        'tropical:watch': {'state': 'unknown', 'cached': true}
      },
    });
    expect(report.status, 'partial');
    expect(report.statusText(), contains('unverified'));
  });

  test(
      'HTTP 503 structured partial/unavailable reports preserve coverage diagnostics',
      () {
    for (final status in ['partial', 'unavailable']) {
      final report = parseOfficialAlertResponse(
          503,
          jsonEncode({
            'alerts': [],
            'status': status,
            'checked': {
              'tropical:watch': {'state': 'unknown', 'reason': 'source_error'}
            },
          }));
      expect(report.status, status);
      expect(report.statusText(), contains('unverified'));
      expect(report.sourceDetails, contains('source_error'));
    }
    expect(() => parseOfficialAlertResponse(503, '<html>Unavailable</html>'),
        throwsFormatException);
    expect(() => parseOfficialAlertResponse(503, '{"alerts":[]}'),
        throwsFormatException);
    expect(() => parseOfficialAlertResponse(500, '{}'), throwsStateError);
  });
  test(
      'unknown-expiry names drop at the six-hour boundary without a verified absence claim',
      () {
    final clock = DateTime.utc(2026, 11, 10, 1);
    final report = OfficialAlertFeed.fromJson({
      'alerts': ['Small Craft Advisory'],
      'status': 'ready',
      'checked_at': clock.toIso8601String()
    }).recordingObservation(clock);
    final expired =
        report.validCachedAlertsAt(clock.add(const Duration(hours: 6)));
    expect(expired.alerts, isEmpty);
    expect(expired.statusText(), contains('unverified'));
    expect(expired.statusText(), isNot(contains('No active')));
  });
  test(
      'an older original source check cannot be renewed by a later legacy observation',
      () {
    final original = DateTime.utc(2026, 11, 10, 1);
    final later = original.add(const Duration(hours: 2));
    final previous = OfficialAlertFeed.fromLegacyCache(['Small Craft Warning'],
        checkedAt: later);
    final now = original.add(const Duration(hours: 7));
    final next = OfficialAlertFeed.fromJson({
      'alerts': ['Small Craft Warning'],
      'status': 'partial',
      'checked_at': now.toIso8601String(),
      'alert_sources': {'Small Craft Warning': 'marine:Small Craft Warning'},
      'checked': {
        'marine:Small Craft Warning': {
          'state': 'unknown',
          'cached': true,
          'checked_at': original.toIso8601String()
        }
      },
    }).recordingObservation(now, previous: previous).validCachedAlertsAt(now);
    expect(next.alerts, isEmpty);
  });

  test(
      'a cached source without its original clock cannot borrow the latest attempt time',
      () {
    final now = DateTime.utc(2026, 11, 10, 1);
    final report = OfficialAlertFeed.fromJson({
      'alerts': ['Hurricane Watch — Antigua'],
      'status': 'partial',
      'checked_at': now.toIso8601String(),
      'alert_sources': {'Hurricane Watch — Antigua': 'tropical:watch'},
      'checked': {
        'tropical:watch': {'state': 'unknown', 'cached': true}
      },
    }).recordingObservation(now).validCachedAlertsAt(now);
    expect(report.alerts, isEmpty);
    expect(report.statusText(), contains('unverified'));
  });
}
