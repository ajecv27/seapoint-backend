import json
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError

from openweather_current import CurrentWeather, WeatherUnavailable


class CurrentWeatherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.database = Path(self.tmp.name) / 'cache.sqlite3'
        self.now = 1794176813
        self.calls = 0

    def fetch(self, lat, lon):
        self.calls += 1
        return {'data': [{'dt': self.now, 'temp': 24.9, 'feels_like': 25.9,
                          'humidity': 94, 'weather': [{'description': 'light rain'}]}]}

    def service(self, **kwargs):
        return CurrentWeather(key='secret-test-key', database=self.database,
                              clock=lambda: self.now, fetch=kwargs.pop('fetch', self.fetch), **kwargs)

    def test_real_response_shape_and_shared_cache(self):
        result = self.service().get(17.12, -61.8)
        self.assertEqual(result['current']['temp'], 24.9)
        self.assertEqual(result['current']['description'], 'light rain')
        self.assertEqual(self.service().get(17.12, -61.8), result)
        self.assertEqual(self.calls, 1)
        self.assertNotIn('secret-test-key', json.dumps(result))

    def test_concurrent_cache_miss_only_fetches_once(self):
        service = self.service()
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(lambda _: service.get(17.12, -61.8), range(8)))
        self.assertEqual(self.calls, 1)

    def test_cache_expiry_and_location_isolation(self):
        service = self.service()
        service.get(17.12, -61.8)
        service.get(17.13, -61.8)
        self.assertEqual(self.calls, 2)
        self.now += 900
        service.get(17.12, -61.8)
        self.assertEqual(self.calls, 3)

    def test_budget_survives_service_restart_and_resets_next_day(self):
        self.service(daily_limit=1).get(17.12, -61.8)
        with self.assertRaises(WeatherUnavailable):
            self.service(daily_limit=1).get(17.13, -61.8)
        self.assertEqual(self.calls, 1)
        self.now += 86400
        self.service(daily_limit=1).get(17.13, -61.8)
        self.assertEqual(self.calls, 2)

    def test_invalid_coordinates_never_make_upstream_calls(self):
        for lat, lon in [(None, 0), ('nan', 0), (0, 'inf'), (91, 0), (0, -181)]:
            with self.assertRaises(ValueError):
                self.service().get(lat, lon)
        self.assertEqual(self.calls, 0)

    def test_auth_error_is_sanitized_and_puts_requests_on_cooldown(self):
        def fail(lat, lon):
            self.calls += 1
            raise HTTPError('https://example.com?appid=secret-test-key', 401, 'Unauthorized', {}, None)
        service = self.service(fetch=fail)
        for lat in [17.12, 17.13]:
            with self.assertRaises(WeatherUnavailable) as error:
                service.get(lat, -61.8)
            self.assertNotIn('secret-test-key', str(error.exception))
        self.assertEqual(self.calls, 1)
        self.now += 3600
        with self.assertRaises(WeatherUnavailable):
            service.get(17.12, -61.8)
        self.assertEqual(self.calls, 2)

    def test_old_or_malformed_data_is_not_presented_as_current(self):
        for payload in [{'data': []}, {'data': [{'dt': self.now - 7201, 'temp': 25}]},
                        {'data': [{'dt': self.now, 'temp': '25'}]}]:
            with self.subTest(payload=payload):
                database = Path(self.tmp.name) / f'malformed-{len(list(Path(self.tmp.name).iterdir()))}.sqlite3'
                service = CurrentWeather(key='test', database=database,
                                         clock=lambda: self.now, fetch=lambda a, b: payload)
                with self.assertRaises(WeatherUnavailable):
                    service.get(17.12, -61.8)

    def test_missing_key_never_calls_upstream(self):
        service = self.service()
        service.key = ''
        with self.assertRaises(WeatherUnavailable):
            service.get(17.12, -61.8)
        self.assertEqual(self.calls, 0)


if __name__ == '__main__':
    unittest.main()
