from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from forecast_maps import ForecastMaps, precipitation_range, rgba
from radar_view import radar_page


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = datetime(2026, 11, 8, 22, tzinfo=timezone.utc).timestamp()
        self.cycle = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
        self.reads = []

    def reader(self, url, byte_range=None):
        self.reads.append((url, byte_range))
        return (b'1:0:d=x:PRATE:surface:12 hour fcst:\n2:10:d=x:APCP:surface:6-12 hour acc fcst:\n'
                if url.endswith('.idx') else b'GRIB')

    def service(self, **kwargs):
        return ForecastMaps(directory=self.tmp.name, reader=kwargs.get('reader', self.reader),
                            renderer=lambda data, stamp: b'PNG-fixture', clock=lambda: self.now)

    def test_selects_instantaneous_rate_not_accumulation_or_average(self):
        index = ('1:0:x:PRATE:surface:6-12 hour ave fcst:\n'
                 '2:10:x:PRATE:surface:12 hour fcst:\n3:30:x:APCP:surface:acc fcst:\n')
        self.assertEqual(precipitation_range(index), (10, 29))
        with self.assertRaises(ValueError):
            precipitation_range('1:0:x:PRATE:surface:6-12 hour ave fcst:\n2:50:x:END:\n')

    def test_forecast_contains_real_timestamps_and_24_future_hours(self):
        service = self.service()
        service._build(self.cycle)
        result = service.snapshot()
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['units'], 'mm/h')
        self.assertGreaterEqual(result['frames'][-1]['time'], self.now + 86400)
        self.assertTrue(all(b['time'] - a['time'] == 3600
                            for a, b in zip(result['frames'], result['frames'][1:])))
        self.assertEqual(len(self.reads), 52)
        self.assertEqual(service.image(result['frames'][0]['url'].split('/')[-1]), b'PNG-fixture')

    def test_cached_images_avoid_more_provider_requests(self):
        service = self.service()
        service._build(self.cycle)
        service._build(self.cycle)
        self.assertEqual(len(self.reads), 52)

    def test_failed_refresh_keeps_valid_forecast_and_backs_off(self):
        service = self.service()
        service._build(self.cycle)
        old = service.manifest
        def fail(*args):
            raise OSError('Provider unavailable')
        service.reader = fail
        self.now += 6 * 3600
        with self.assertLogs('forecast_maps', level='ERROR'):
            service._build(datetime(2026, 11, 8, 18, tzinfo=timezone.utc))
        self.assertIs(service.manifest, old)
        self.assertFalse(service.building)
        self.assertGreater(service.retry_after, self.now)

    def test_missing_forecast_never_claims_clear_weather(self):
        service = self.service()
        service.retry_after = self.now + 300
        self.assertEqual(service.snapshot()['status'], 'unavailable')
        self.assertEqual(service.snapshot()['frames'], [])

    def test_expired_forecasts_are_not_served(self):
        service = self.service()
        service._build(self.cycle)
        self.now += 86400
        service.retry_after = self.now + 300
        self.assertEqual(service.snapshot()['frames'], [])

    def test_path_traversal_and_missing_frame_are_rejected(self):
        service = self.service()
        for name in ['../requirements.txt', '/etc/passwd', '2026110812-001.png/..', '2026110812-001.png']:
            self.assertIsNone(service.image(name))

    def test_color_scale_and_dry_transparency(self):
        result = rgba(np.array([[0., .05, .1, 2.5, 60., np.nan]]))
        self.assertEqual(result[0, 0, 3], 0)
        self.assertEqual(result[0, 1, 3], 0)
        self.assertEqual(result[0, 2, 3], 200)
        self.assertEqual(result[0, 5, 3], 0)
        self.assertEqual(result[0, 3, :3].tolist(), [106, 78, 211])

    def test_location_name_cannot_inject_script(self):
        page = radar_page(17.12, -61.8, '</script><script>alert(1)</script>')
        self.assertNotIn('"</script><script>', page)
        self.assertIn('\\u003c/script>', page)


if __name__ == '__main__':
    unittest.main()
