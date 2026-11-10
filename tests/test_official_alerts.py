import concurrent.futures
from datetime import datetime, timedelta, timezone
import threading
import unittest

from official_alerts import MARINE_PRODUCTS, SOURCES, OfficialAlertService, parse_marine_cancellations, parse_marine_locations, parse_statement

NOW = datetime(2026, 11, 10, 16, tzinfo=timezone.utc)  # noon ECT
URL = SOURCES['tropical:warning']


def statement(body, issued='10:00 AM ECT TUE, NOV 10, 2026'):
    return f'<html><title>TROPICAL CYCLONE WARNING STATEMENT</title><body><p>ANTIGUA AND BARBUDA METEOROLOGICAL SERVICES</p><p>{issued}</p><p>{body}</p></body></html>'


def inactive_marine():
    return {name: {'active': False, 'reason': 'not_listed', 'url': url} for name, url in MARINE_PRODUCTS.items()}


def inactive_pages():
    return statement('NO WATCHES OR WARNINGS ARE IN EFFECT FOR ANTIGUA AND BARBUDA.')


class MarineLocationTests(unittest.TestCase):
    def parse(self, heading):
        prefix = 'ANTIGUA AND BARBUDA METEOROLOGICAL SERVICES ISSUE 10 AM NOV 10 2026 '
        text = prefix + heading + ' Locations to be affected: Northern shores Timing: Until 6 PM for Antigua. Synopsis: Barbados.'
        return parse_marine_locations(text, len(prefix))

    def test_barbuda_only_and_combined_scopes(self):
        self.assertEqual(self.parse('Small Craft Warning is in effect for Barbuda.'), ['Barbuda'])
        self.assertEqual(self.parse('Small Craft Advisory for Antigua and Barbuda.'), ['Antigua', 'Barbuda'])
        self.assertEqual(self.parse('Antigua and Barbuda'), ['Antigua', 'Barbuda'])

    def test_foreign_and_issuer_header_do_not_supply_local_coverage(self):
        self.assertEqual(self.parse('Small Craft Warning for the BVI.'), [])
        self.assertEqual(self.parse('Antigua and Barbuda Meteorological Services Small Craft Warning for the BVI.'), [])
        self.assertEqual(self.parse('This bulletin has an unreadable area.'), [])

    def test_excluded_island_not_in_scope(self):
        self.assertEqual(self.parse('Small Craft Warning for Barbuda, excluding Antigua.'), ['Barbuda'])
        self.assertEqual(self.parse('Small Craft Warning for Antigua and Barbuda except Barbuda.'), ['Antigua'])
        self.assertEqual(self.parse('Small Craft Warning for all Leeward islands except Antigua.'), [])


class MarineCancellationTests(unittest.TestCase):
    def parse(self, body, product='Small Craft Warning'):
        prefix = 'ANTIGUA AND BARBUDA METEOROLOGICAL SERVICES SMALL CRAFT WARNING HAS BEEN CANCELLED FOR BARBUDA. ISSUED 10AM '
        return parse_marine_cancellations(prefix + body + ' Timing: Until 6 PM. Synopsis: Improving.', len(prefix), product)

    def test_affirmative_discontinuation_for_local_island(self):
        self.assertEqual(self.parse('THE SMALL CRAFT WARNING FOR ANTIGUA HAS BEEN DISCONTINUED.'), ['Antigua'])
        self.assertEqual(self.parse('THE MET OFFICE HAS DISCONTINUED THE HIGH SURF ADVISORY FOR ANTIGUA AND BARBUDA.', 'High Surf Advisory'), ['Antigua', 'Barbuda'])

    def test_negated_and_future_cancellations_are_not_current(self):
        for body in ('THE SMALL CRAFT WARNING FOR ANTIGUA HAS NOT BEEN CANCELLED.', 'THE SMALL CRAFT WARNING FOR ANTIGUA WILL BE CANCELLED AT 6PM.', 'IF CONDITIONS IMPROVE THE SMALL CRAFT WARNING FOR ANTIGUA WILL BE CANCELLED.'):
            with self.subTest(body=body):
                self.assertEqual(self.parse(body), [])

    def test_mixed_barbuda_cancellation_does_not_cancel_antigua(self):
        self.assertEqual(self.parse('THE SMALL CRAFT WARNING FOR BARBUDA HAS BEEN CANCELLED WHILE A SMALL CRAFT WARNING REMAINS IN EFFECT FOR ANTIGUA.'), ['Barbuda'])

    def test_issuer_before_issue_and_later_timing_cannot_cancel(self):
        self.assertEqual(self.parse('SMALL CRAFT WARNING FOR ANTIGUA. Timing: THE SMALL CRAFT WARNING FOR ANTIGUA HAS BEEN CANCELLED.'), [])

    def test_exclusions_and_other_products_cannot_cancel_requested_product(self):
        self.assertEqual(self.parse('THE SMALL CRAFT WARNING FOR ANTIGUA AND BARBUDA EXCEPT ANTIGUA HAS BEEN CANCELLED.'), ['Barbuda'])
        self.assertEqual(self.parse('THE HIGH SURF ADVISORY FOR ANTIGUA HAS BEEN CANCELLED.'), [])
        self.assertEqual(self.parse('A SMALL CRAFT WARNING REMAINS IN EFFECT FOR ANTIGUA WHILE THE HIGH SURF ADVISORY FOR ANTIGUA HAS BEEN CANCELLED.'), [])


class StatementTests(unittest.TestCase):
    def parse(self, body, issued='10:00 AM ECT TUE, NOV 10, 2026', now=NOW):
        return parse_statement(statement(body, issued), URL, now)

    def test_current_tropical_storm_watch(self):
        result = self.parse('A TROPICAL STORM WATCH REMAINS IN EFFECT FOR ANTIGUA AND BARBUDA. A WATCH MEANS THAT CONDITIONS ARE POSSIBLE WITHIN 48 HOURS.')
        self.assertEqual(result['state'], 'active')
        self.assertEqual(result['alerts'], ['Tropical Storm Watch — Antigua and Barbuda'])

    def test_current_hurricane_warning(self):
        result = self.parse('A HURRICANE WARNING IS NOW IN EFFECT FOR ANTIGUA AND BARBUDA.')
        self.assertEqual(result['alerts'], ['Hurricane Warning — Antigua and Barbuda'])

    def test_mixed_islands_keep_separate_severity(self):
        result = self.parse('A TROPICAL STORM WARNING REMAINS IN EFFECT FOR BARBUDA WHILE A TROPICAL STORM WATCH REMAINS IN EFFECT FOR ANTIGUA. A TROPICAL STORM WARNING MEANS CONDITIONS ARE EXPECTED.')
        self.assertEqual(result['alerts'], ['Tropical Storm Warning — Barbuda', 'Tropical Storm Watch — Antigua'])
        self.assertNotIn('Tropical Storm Warning — Antigua and Barbuda', result['alerts'])

    def test_and_separated_declarations_keep_locality(self):
        result = self.parse('A TROPICAL STORM WATCH REMAINS IN EFFECT FOR ANTIGUA AND TROPICAL STORM WARNING IS NOW IN EFFECT FOR BARBUDA; SEE WARNING STATEMENT FOR BARBUDA.')
        self.assertCountEqual(result['alerts'], ['Tropical Storm Watch — Antigua', 'Tropical Storm Warning — Barbuda'])

    def test_old_cyclone_is_unknown_not_active(self):
        result = self.parse('A TROPICAL STORM WARNING REMAINS IN EFFECT FOR BARBUDA.', issued='11:26 PM ECT THU, OCT 9, 2025')
        self.assertEqual((result['state'], result['alerts']), ('unknown', []))
        self.assertEqual(result['reason'], 'stale_bulletin')

    def test_expired_flood_is_verified_inactive(self):
        result = self.parse('A FLASH FLOOD ADVISORY IS IN EFFECT FOR MINOR FLOODING IN LOW LYING AND FLOOD PRONE AREAS OF ANTIGUA AND BARBUDA, UNTIL 5PM TODAY.', issued='12:45 PM ECT SUN, NOV 8, 2026')
        self.assertEqual((result['state'], result['reason']), ('inactive', 'expired'))

    def test_expiry_with_tomorrow_and_ordinal_date(self):
        result = self.parse('A FLASH FLOOD WATCH IS IN EFFECT FOR LOW LYING AND FLOOD PRONE AREAS OF ANTIGUA, BARBUDA, MONTSERRAT AND ANGUILLA UNTIL 12 MIDDAY TOMORROW WEDNESDAY 11TH NOVEMBER 2026.')
        self.assertEqual(result['state'], 'active')
        self.assertEqual(result['expires'], '2026-11-11T16:00:00+00:00')

    def test_bvi_flood_does_not_borrow_issuer_locality(self):
        result = self.parse('A FLASH FLOOD WARNING REMAINS IN EFFECT FOR THE BVI UNTIL 6AM TOMORROW WEDNESDAY NOVEMBER 11 2026. ANTIGUA AND BARBUDA METEOROLOGICAL SERVICES WILL CONTINUE MONITORING.')
        self.assertEqual((result['state'], result['alerts']), ('inactive', []))
        self.assertEqual(result['reason'], 'not_for_antigua_or_barbuda')

    def test_cancelled_local_warning(self):
        result = self.parse('THE ANTIGUA AND BARBUDA METEOROLOGICAL SERVICES HAS DISCONTINUED THE FLASH FLOOD ADVISORY FOR LOW LYING AND FLOOD PRONE AREAS OF ANTIGUA AND BARBUDA.')
        self.assertEqual((result['state'], result['reason']), ('inactive', 'cancelled'))

    def test_mixed_cancelled_barbuda_does_not_cancel_active_antigua(self):
        result = self.parse('THE HURRICANE WARNING FOR BARBUDA HAS BEEN CANCELLED WHILE A HURRICANE WARNING REMAINS IN EFFECT FOR ANTIGUA.')
        self.assertEqual(result['alerts'], ['Hurricane Warning — Antigua'])
        self.assertEqual(result['cancelled_alerts'], ['Hurricane Warning — Barbuda'])

    def test_negated_cancellation_does_not_clear_active_warning(self):
        result = self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA. THE HURRICANE WARNING FOR ANTIGUA HAS NOT BEEN CANCELLED.')
        self.assertEqual(result['alerts'], ['Hurricane Warning — Antigua'])
        self.assertEqual(result.get('cancelled_alerts', []), [])

    def test_future_cancellation_does_not_clear_active_warning(self):
        result = self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA. THE HURRICANE WARNING FOR ANTIGUA WILL BE CANCELLED AT 6PM.')
        self.assertEqual(result['alerts'], ['Hurricane Warning — Antigua'])
        self.assertEqual(result.get('cancelled_alerts', []), [])

    def test_conditional_cancellation_does_not_clear_active_warning(self):
        for ending in ('IF CONDITIONS IMPROVE THE HURRICANE WARNING FOR ANTIGUA WILL BE CANCELLED.', 'IF THE HURRICANE WARNING FOR ANTIGUA HAS BEEN CANCELLED, RESIDENTS MAY RESUME ACTIVITIES.'):
            with self.subTest(ending=ending):
                result = self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA. ' + ending)
                self.assertEqual(result['alerts'], ['Hurricane Warning — Antigua'])
                self.assertEqual(result.get('cancelled_alerts', []), [])

    def test_future_issue_is_unknown(self):
        result = self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA.', issued='2:00 PM ECT TUE, NOV 10, 2026')
        self.assertEqual((result['state'], result['reason']), ('unknown', 'future_issue'))

    def test_static_heading_definition_and_conditional_are_not_declarations(self):
        for body in ['HURRICANE WARNING. A HURRICANE WARNING MEANS THAT CONDITIONS ARE EXPECTED.', 'BE PREPARED IF A FLASH FLOOD WARNING IS ISSUED FOR ANTIGUA.', 'HURRICANE WARNING IS IN EFFECT: THIS IS A DEFINITION FOR ANTIGUA.']:
            with self.subTest(body=body):
                self.assertEqual(self.parse(body)['state'], 'unknown')

    def test_unreadable_dates_and_explicit_invalid_timing_are_unknown(self):
        self.assertEqual(self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA.', issued='DATE UNKNOWN')['reason'], 'issue_date_unreadable')
        self.assertEqual(self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA UNTIL SOMETIME TONIGHT.')['reason'], 'timing_unreadable')
        self.assertEqual(self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA.', issued='10:00 AM ECT TUE, NOV 32, 2026')['state'], 'unknown')

    def test_next_update_bounds_freshness(self):
        result = self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA. THE NEXT ADVISORY WILL BE AT 11 AM.')
        self.assertEqual((result['state'], result['reason']), ('unknown', 'stale_bulletin'))

    def test_explicit_no_warning_never_activates(self):
        for body in ('No hurricane warning is in effect for Antigua.', 'No tropical storm watch is now in effect for Antigua.', 'There is not a hurricane warning is in effect for Antigua.'):
            with self.subTest(body=body):
                self.assertNotEqual(self.parse(body)['state'], 'active')
                self.assertEqual(self.parse(body)['alerts'], [])

    def test_excluded_island_not_treated_as_covered(self):
        result = self.parse('A HURRICANE WARNING IS IN EFFECT FOR BARBUDA, EXCLUDING ANTIGUA.')
        self.assertEqual(result['alerts'], ['Hurricane Warning — Barbuda'])
        result = self.parse('A HURRICANE WARNING IS IN EFFECT FOR ALL LEEWARD ISLANDS EXCEPT ANTIGUA.')
        self.assertNotEqual(result['state'], 'active')
        result = self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA AND BARBUDA EXCEPT BARBUDA.')
        self.assertEqual(result['alerts'], ['Hurricane Warning — Antigua'])

    def test_expiry_timestamp_cannot_replace_unreadable_issue_header(self):
        result = self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA UNTIL 5PM ECT TUE, NOV 10, 2026.', issued='ISSUED AT UNREADABLE TIME')
        self.assertEqual((result['state'], result['reason']), ('unknown', 'issue_date_unreadable'))
        result = self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA. THE NEXT ADVISORY WILL BE AT 5PM ECT TUE, NOV 10, 2026.', issued='ISSUED AT UNREADABLE TIME')
        self.assertEqual((result['state'], result['reason']), ('unknown', 'issue_date_unreadable'))

    def test_future_start_is_verified_not_started(self):
        result = self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA FROM 6PM TODAY UNTIL 11PM TODAY.')
        self.assertEqual((result['state'], result['reason']), ('inactive', 'not_started'))
        self.assertEqual(result['starts'], '2026-11-10T22:00:00+00:00')

    def test_future_forecast_conditions_do_not_delay_current_watch(self):
        result = self.parse('A HURRICANE WATCH IS IN EFFECT FOR ANTIGUA. HURRICANE CONDITIONS ARE POSSIBLE FROM 6PM TODAY UNTIL 11PM TODAY.')
        self.assertEqual(result['alerts'], ['Hurricane Watch — Antigua'])
        self.assertNotIn('starts', result)
        self.assertNotIn('expires', result)

    def test_cancel_one_island_leaves_other_island(self):
        result = self.parse('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA AND BARBUDA. THE HURRICANE WARNING FOR ANTIGUA HAS BEEN CANCELLED.')
        self.assertEqual(result['alerts'], ['Hurricane Warning — Barbuda'])

    def test_foreign_scope_cannot_borrow_later_instruction_locality(self):
        result = self.parse('A FLASH FLOOD WARNING IS IN EFFECT FOR THE BVI AND ANTIGUA RESIDENTS SHOULD MONITOR CONDITIONS.')
        self.assertEqual(result['state'], 'inactive')
        self.assertEqual(result['alerts'], [])

    def test_script_text_cannot_activate_warning(self):
        result = self.parse('<script>A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA.</script>HURRICANE WARNING')
        self.assertEqual(result['state'], 'unknown')


class ServiceTests(unittest.TestCase):
    def service(self, marine=None, fetcher=None, clock=None, **kwargs):
        return OfficialAlertService(marine or inactive_marine, fetcher=fetcher or (lambda url: inactive_pages()), clock=clock or (lambda: NOW), **kwargs)

    def test_explicit_marine_locations_qualify_label_without_changing_source_id(self):
        def load():
            data = inactive_marine()
            data['Small Craft Warning'] = {'active': True, 'reason': 'active', 'locations': ['Barbuda'], 'expires': '2026-11-10T18:00:00+00:00'}
            return data
        result = self.service(marine=load).snapshot()
        self.assertEqual(result['alerts'], ['Small Craft Warning — Barbuda'])
        self.assertEqual(result['alert_sources']['Small Craft Warning — Barbuda'], 'marine:Small Craft Warning')

    def test_marine_area_checks_have_independent_expiry_and_future_start(self):
        def load():
            data = inactive_marine()
            data['Small Craft Warning'] = {'area_checks': {
                'Antigua': {'active': True, 'reason': 'active', 'expires': '2026-11-10T15:00:00+00:00'},
                'Barbuda': {'active': True, 'reason': 'active', 'starts': '2026-11-10T15:00:00+00:00', 'expires': '2026-11-10T18:00:00+00:00'},
            }}
            data['High Surf Warning'] = {'area_checks': {
                'Antigua': {'active': True, 'reason': 'active', 'starts': '2026-11-10T17:00:00+00:00', 'expires': '2026-11-10T19:00:00+00:00'},
                'Barbuda': {'active': False, 'reason': 'not_for_antigua_or_barbuda'},
            }}
            return data
        result = self.service(marine=load).snapshot()
        self.assertEqual(result['alerts'], ['Small Craft Warning — Barbuda'])
        self.assertEqual(result['alert_sources']['Small Craft Warning — Barbuda'], 'marine:Small Craft Warning:Barbuda')
        self.assertEqual(result['checked']['marine:Small Craft Warning:Antigua']['reason'], 'expired')
        self.assertEqual(result['checked']['marine:High Surf Warning:Antigua']['reason'], 'not_started')

    def test_marine_area_source_outage_retains_only_unexpired_island(self):
        current = [NOW]
        outage = [False]
        def load():
            data = inactive_marine()
            data['Small Craft Warning'] = {'active': False, 'reason': 'bulletin_error'} if outage[0] else {'area_checks': {
                'Antigua': {'active': True, 'reason': 'active', 'expires': '2026-11-10T16:05:00+00:00'},
                'Barbuda': {'active': True, 'reason': 'active', 'expires': '2026-11-10T18:00:00+00:00'},
            }}
            return data
        service = self.service(marine=load, clock=lambda: current[0], cache_ttl=0)
        first = service.snapshot()
        self.assertCountEqual(first['alerts'], ['Small Craft Warning — Antigua', 'Small Craft Warning — Barbuda'])
        current[0] += timedelta(minutes=10)
        outage[0] = True
        second = service.snapshot()
        self.assertEqual(second['alerts'], ['Small Craft Warning — Barbuda'])
        self.assertEqual(second['checked']['marine:Small Craft Warning:Barbuda']['state'], 'unknown')
        self.assertEqual(second['checked']['marine:Small Craft Warning:Barbuda']['checked_at'], first['checked']['marine:Small Craft Warning:Barbuda']['checked_at'])

    def test_ambiguous_marine_locations_and_legacy_antigua_only_absence_are_unknown(self):
        for value in ({'active': True, 'reason': 'active', 'locations': []}, {'active': False, 'reason': 'not_for_antigua'}):
            with self.subTest(value=value):
                def load():
                    data = inactive_marine()
                    data['Small Craft Warning'] = value
                    return data
                result = self.service(marine=load).snapshot()
                self.assertEqual(result['checked']['marine:Small Craft Warning']['state'], 'unknown')
                self.assertEqual(result['alerts'], [])

    def test_all_verified_inactive_is_ready(self):
        result = self.service().snapshot()
        self.assertEqual((result['status'], result['alerts']), ('ready', []))
        self.assertEqual(result['coverage']['sources_verified'], 10)

    def test_all_failures_are_unavailable_not_clear(self):
        def fail(*args):
            raise OSError('offline')
        result = self.service(marine=fail, fetcher=fail).snapshot()
        self.assertEqual((result['status'], result['alerts']), ('unavailable', []))
        self.assertTrue(all(value['state'] == 'unknown' for value in result['checked'].values()))

    def test_legacy_marine_parser_failures_are_unknown(self):
        for reason in ('bulletin_error', 'issue_date_unreadable', 'timing_unreadable', 'invalid_timing'):
            with self.subTest(reason=reason):
                loader = lambda: {name: {'active': False, 'reason': reason} for name in MARINE_PRODUCTS}
                result = self.service(marine=loader).snapshot()
                self.assertEqual(result['status'], 'partial')
                self.assertEqual(result['checked']['marine:Small Craft Advisory']['state'], 'unknown')

    def test_partial_active_preserves_link_and_source(self):
        def load():
            data = inactive_marine()
            data['Small Craft Advisory'] = {'active': True, 'reason': 'active', 'expires': '2026-11-10T18:00:00+00:00'}
            return data
        def fetch(url):
            if url == SOURCES['tropical:watch']:
                return statement('A TROPICAL STORM WATCH IS IN EFFECT FOR ANTIGUA.')
            raise OSError('offline')
        result = self.service(marine=load, fetcher=fetch).snapshot()
        self.assertEqual(result['status'], 'partial')
        for name in ('Small Craft Advisory', 'Tropical Storm Watch — Antigua'):
            self.assertIn(name, result['alerts'])
            self.assertTrue(result['links'][name].startswith('https://www.antiguamet.com/'))
            self.assertIn(name, result['checked'][result['alert_sources'][name]]['alerts'])

    def test_cached_source_only_retained_until_original_expiry(self):
        current = [NOW]
        fail = [False]
        def fetch(url):
            if url == SOURCES['tropical:watch']:
                if fail[0]:
                    raise OSError('offline')
                return statement('A TROPICAL STORM WATCH IS IN EFFECT FOR ANTIGUA UNTIL 1 PM TODAY.')
            return inactive_pages()
        service = self.service(fetcher=fetch, clock=lambda: current[0], cache_ttl=0)
        first = service.snapshot()
        fail[0] = True
        current[0] += timedelta(minutes=10)
        second = service.snapshot()
        source = second['checked']['tropical:watch']
        self.assertIn('Tropical Storm Watch — Antigua', second['alerts'])
        self.assertEqual(source['state'], 'unknown')
        self.assertTrue(source['cached'])
        self.assertEqual(source['checked_at'], first['checked']['tropical:watch']['checked_at'])
        current[0] += timedelta(hours=1)
        self.assertNotIn('Tropical Storm Watch — Antigua', service.snapshot()['alerts'])

    def test_verified_inactive_clears_old_marine_despite_other_unknown_sources(self):
        current = [NOW]
        is_active = [True]
        def load():
            data = inactive_marine()
            data['Small Craft Advisory'] = {'active': is_active[0], 'reason': 'active' if is_active[0] else 'expired', 'expires': '2026-11-10T18:00:00+00:00'}
            return data
        def fail(url):
            raise OSError('offline')
        service = self.service(marine=load, fetcher=fail, clock=lambda: current[0], cache_ttl=0)
        self.assertIn('Small Craft Advisory', service.snapshot()['alerts'])
        is_active[0] = False
        current[0] += timedelta(minutes=10)
        result = service.snapshot()
        self.assertNotIn('Small Craft Advisory', result['alerts'])
        self.assertEqual(result['checked']['marine:Small Craft Advisory']['alerts'], [])

    def test_cache_expires_at_alert_boundary_before_five_minutes(self):
        current = [NOW]
        def fetch(url):
            if url == SOURCES['tropical:warning']:
                return statement('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA UNTIL 12:01 PM TODAY.')
            return inactive_pages()
        service = self.service(fetcher=fetch, clock=lambda: current[0])
        self.assertIn('Hurricane Warning — Antigua', service.snapshot()['alerts'])
        current[0] += timedelta(minutes=2)
        result = service.snapshot()
        self.assertEqual(result['alerts'], [])
        self.assertEqual(result['checked']['tropical:warning']['reason'], 'expired')

    def test_newer_cancellation_remains_effective_during_source_outage(self):
        current = [NOW]
        failure = [False]
        def fetch(url):
            if url == SOURCES['tropical:warning']:
                return statement('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA AND BARBUDA UNTIL 8PM TODAY.', issued='9:00 AM ECT TUE, NOV 10, 2026')
            if url == SOURCES['tropical:watch']:
                if failure[0]:
                    raise OSError('offline')
                return statement('THE HURRICANE WARNING FOR ANTIGUA HAS BEEN CANCELLED.')
            return inactive_pages()
        service = self.service(fetcher=fetch, clock=lambda: current[0], cache_ttl=0)
        first = service.snapshot()
        self.assertEqual(first['alerts'], ['Hurricane Warning — Barbuda'])
        failure[0] = True
        current[0] += timedelta(minutes=10)
        second = service.snapshot()
        self.assertEqual(second['alerts'], ['Hurricane Warning — Barbuda'])
        self.assertEqual(second['checked']['tropical:warning']['alerts'], second['alerts'])

    def test_negated_cancellation_cannot_enter_persistent_cross_source_ledger(self):
        current = [NOW]
        outage = [False]
        def fetch(url):
            if url == SOURCES['tropical:warning']:
                return statement('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA.', issued='9:00 AM ECT TUE, NOV 10, 2026')
            if url == SOURCES['tropical:watch']:
                if outage[0]:
                    raise OSError('offline')
                return statement('THE HURRICANE WARNING FOR ANTIGUA HAS NOT BEEN CANCELLED.')
            return inactive_pages()
        service = self.service(fetcher=fetch, clock=lambda: current[0], cache_ttl=0)
        self.assertEqual(service.snapshot()['alerts'], ['Hurricane Warning — Antigua'])
        outage[0] = True
        current[0] += timedelta(minutes=10)
        self.assertEqual(service.snapshot()['alerts'], ['Hurricane Warning — Antigua'])

    def test_changed_active_source_replaces_previous_severity(self):
        current = [NOW]
        level = ['WATCH']
        def fetch(url):
            if url == SOURCES['tropical:warning']:
                return statement(f'A HURRICANE {level[0]} IS IN EFFECT FOR ANTIGUA.')
            return inactive_pages()
        service = self.service(fetcher=fetch, clock=lambda: current[0], cache_ttl=0)
        self.assertEqual(service.snapshot()['alerts'], ['Hurricane Watch — Antigua'])
        level[0] = 'WARNING'
        current[0] += timedelta(minutes=10)
        self.assertEqual(service.snapshot()['alerts'], ['Hurricane Warning — Antigua'])

    def test_duplicate_pages_do_not_duplicate_island_alerts(self):
        def fetch(url):
            if url == SOURCES['tropical:warning']:
                return statement('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA.')
            if url == SOURCES['tropical:watch']:
                return statement('A HURRICANE WARNING IS IN EFFECT FOR ANTIGUA AND BARBUDA.', issued='9:00 AM ECT TUE, NOV 10, 2026')
            return inactive_pages()
        result = self.service(fetcher=fetch).snapshot()
        self.assertCountEqual(result['alerts'], ['Hurricane Warning — Antigua', 'Hurricane Warning — Barbuda'])
        for name in result['alerts']:
            self.assertIn(name, result['checked'][result['alert_sources'][name]]['alerts'])

    def test_cache_singleflight_and_defensive_copy(self):
        calls = [0]
        calls_lock = threading.Lock()
        def fetch(url):
            with calls_lock:
                calls[0] += 1
            return inactive_pages()
        service = self.service(fetcher=fetch)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: service.snapshot(), range(8)))
        self.assertEqual(calls[0], len(SOURCES))
        results[0]['alerts'].append('mutated')
        self.assertEqual(service.snapshot()['alerts'], [])


if __name__ == '__main__':
    unittest.main()
