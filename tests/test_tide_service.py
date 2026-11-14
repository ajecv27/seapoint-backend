from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import json
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError

from tide_service import TideService, TideUnavailable, coverage

A, B = 'a'*32, 'b'*32


class TideServiceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.now = datetime(2026,11,14,16,tzinfo=timezone.utc).timestamp()
        self.calls = []
        self.failure = None
        def fetch(lat,lon,date):
            self.calls.append((lat,lon,date))
            if self.failure:
                raise self.failure
            start, _, _ = coverage(self.now)
            return {'status':200,'responseDatum':'CD','copyright':'retain attribution',
                    'extremes':[{'dt':start+i*21600,'height':.3+i*.001,
                                 'type':'High' if i%2 else 'Low'}for i in range(28)]}
        self.fetch = fetch
        self.service = self.make()

    def make(self, **kwargs):
        return TideService(self.fetch,directory=self.directory,provider_key='test-only-key',
                           clock=lambda:self.now,**kwargs)

    def test_same_day_repeated_and_restarted_requests_use_one_prediction(self):
        first = self.service.get(A,17.12,-61.8)
        self.assertEqual(len(first['extremes']),28)
        self.assertEqual(first['copyright'],'retain attribution')
        self.now += 8*3600
        self.assertEqual(self.service.get(A,17.12,-61.8),first)
        self.assertEqual(self.make().get(A,17.12,-61.8),first)
        self.assertEqual(len(self.calls),1)

    def test_refreshes_only_when_calendar_coverage_no_longer_includes_all_seven_days(self):
        first = self.service.get(A,17.12,-61.8)
        self.now += 86400
        second = self.service.get(A,17.12,-61.8)
        self.assertEqual(second['coverage_end']-first['coverage_end'],86400)
        self.assertEqual(len(self.calls),2)
        self.assertEqual(self.calls[-1][2],'2026-11-15')

    def test_data_is_never_shared_between_installations(self):
        self.service.get(A,17.12,-61.8)
        self.service.get(B,17.12,-61.8)
        self.assertEqual(len(self.calls),2)
        rows = self.service._db()
        with rows as db:
            saved = db.execute('SELECT client FROM cache').fetchall()
        self.assertEqual(len(saved),2)
        self.assertNotIn(A,str(saved))

    def test_no_identifier_or_invalid_coordinates_never_call_provider(self):
        for token in ['', 'bad', 'A'*32]:
            with self.assertRaises(TideUnavailable) as caught:
                self.service.get(token,17.12,-61.8)
            self.assertEqual(caught.exception.status,428)
        for lat,lon in [(float('nan'),0),(91,0),(17,181),(True,0)]:
            with self.assertRaises(ValueError):self.service.get(A,lat,lon)
        self.assertEqual(self.calls,[])

    def test_normalized_location_and_request_coordinates_agree(self):
        self.service.get(A,17.120001,-61.800001)
        self.service.get(A,17.120002,-61.800002)
        self.assertEqual(self.calls,[(17.12,-61.8,'2026-11-14')])

    def test_simultaneous_refreshes_coalesce_to_one_provider_request(self):
        entered, release = threading.Event(), threading.Event()
        def slow(*args):entered.set();release.wait(3);return self.fetch(*args)
        self.service.fetcher = slow
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.service.get,A,17.12,-61.8)
            self.assertTrue(entered.wait(1))
            second = pool.submit(self.service.get,A,17.12,-61.8)
            time.sleep(.03);release.set()
            self.assertEqual(first.result(),second.result())
        self.assertEqual(len(self.calls),1)

    def test_exhausted_credits_pause_all_locations_and_survive_restart(self):
        self.failure = HTTPError('https://provider.invalid/?key=do-not-expose',402,'Payment',{},
                                 BytesIO(b'{"error":"Insufficient credits"}'))
        with self.assertRaises(TideUnavailable) as caught:self.service.get(A,17.12,-61.8)
        self.assertEqual(caught.exception.reason,'credits_exhausted')
        self.assertNotIn('do-not-expose',json.dumps(caught.exception.payload()))
        self.assertEqual(self.service.status()['status'],'paused')
        for service,token in [(self.service,A),(self.make(),B)]:
            with self.assertRaises(TideUnavailable):service.get(token,17.2,-61.9)
        self.assertEqual(len(self.calls),1)
        self.now += 21601
        self.failure = None
        self.assertTrue(self.service.get(A,17.2,-61.9)['ok'])

    def test_provider_json_credit_error_uses_same_pause(self):
        self.service.fetcher = lambda *args:{'status':400,'error':'Not enough credits for this request'}
        with self.assertRaises(TideUnavailable) as caught:self.service.get(A,17.12,-61.8)
        self.assertEqual(caught.exception.reason,'credits_exhausted')

    def test_failed_refresh_keeps_existing_events_without_extending_coverage(self):
        first = self.service.get(A,17.12,-61.8)
        self.now += 86400
        self.failure = HTTPError('https://provider.invalid',402,'Payment',{},BytesIO(b'{}'))
        partial = self.service.get(A,17.12,-61.8)
        self.assertEqual(partial['extremes'],first['extremes'])
        self.assertEqual(partial['coverage_end'],first['coverage_end'])
        self.assertEqual(partial['fetched_at'],first['fetched_at'])
        self.assertEqual(partial['availability'],'cached_partial')

    def test_daily_budget_caps_new_calls_but_keeps_cached_predictions_usable(self):
        self.service = self.make(daily_limit=2)
        self.service.get(A,17.12,-61.8)
        self.service.get(B,17.12,-61.8)
        with self.assertRaises(TideUnavailable) as caught:self.service.get(A,17.3,-61.9)
        self.assertEqual(caught.exception.status,429)
        self.assertTrue(self.service.get(A,17.12,-61.8)['ok'])
        self.assertEqual(len(self.calls),2)

    def test_transient_outage_is_backed_off_for_same_location(self):
        self.failure = OSError('test network outage')
        for _ in range(2):
            with self.assertRaises(TideUnavailable):self.service.get(A,17.12,-61.8)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.service.status()['status'],'ready')

    def test_manual_recheck_after_funding_is_limited_and_clears_the_pause(self):
        self.failure = HTTPError('https://provider.invalid',402,'Payment',{},BytesIO(b'{}'))
        with self.assertRaises(TideUnavailable):self.service.get(A,17.12,-61.8)
        with self.assertRaises(TideUnavailable):self.service.get(A,17.12,-61.8,retry_paused=True)
        self.assertEqual(len(self.calls),1)
        self.now += 61
        self.failure = None
        self.assertTrue(self.service.get(A,17.12,-61.8,retry_paused=True)['ok'])
        self.assertEqual(self.service.status()['status'],'ready')
        self.assertTrue(self.service.get(B,17.2,-61.9)['ok'])


if __name__=='__main__':unittest.main()
