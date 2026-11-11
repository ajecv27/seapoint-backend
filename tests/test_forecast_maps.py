from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import tempfile
import math
import unittest
from unittest.mock import patch
import zlib

import numpy as np
from PIL import Image

from forecast_maps import ForecastMaps, precipitation_range, rgba
from radar_view import radar_page


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = datetime(2026, 11, 8, 22, tzinfo=timezone.utc).timestamp()
        self.cycle = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
        self.reads = []
        output = BytesIO()
        Image.new('RGBA', (640, 640), (100, 210, 255, 200)).save(output, format='PNG')
        self.png = output.getvalue()

    def reader(self, url, byte_range=None):
        self.reads.append((url, byte_range))
        return (b'1:0:d=x:PRATE:surface:12 hour fcst:\n2:10:d=x:APCP:surface:6-12 hour acc fcst:\n'
                if url.endswith('.idx') else b'GRIB')

    def service(self, **kwargs):
        return ForecastMaps(directory=self.tmp.name, reader=kwargs.get('reader', self.reader),
                            renderer=lambda data, stamp: self.png, clock=lambda: self.now)

    def cached_manifest(self):
        return Path(self.tmp.name) / 'manifest.json'

    def save_manifest(self, manifest):
        self.cached_manifest().write_text(json.dumps(manifest), encoding='utf-8')

    def test_selects_instantaneous_rate_not_accumulation_or_average(self):
        index = ('1:0:x:PRATE:surface:6-12 hour ave fcst:\n'
                 '2:10:x:PRATE:surface:12 hour fcst:\n3:30:x:APCP:surface:acc fcst:\n')
        self.assertEqual(precipitation_range(index), (10, 29))
        with self.assertRaises(ValueError):
            precipitation_range('1:0:x:PRATE:surface:6-12 hour ave fcst:\n2:50:x:END:\n')

    def test_forecast_contains_real_timestamps_and_48_future_hours(self):
        service = self.service()
        service._build(self.cycle)
        result = service.snapshot()
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['units'], 'mm/h')
        self.assertEqual(result['forecast_until'], int(self.now + 48 * 3600))
        self.assertEqual(result['horizon_hours'], 48)
        self.assertTrue(result['coverage_complete'])
        self.assertGreaterEqual(result['frames'][-1]['time'], self.now + 48 * 3600)
        self.assertTrue(all(b['time'] - a['time'] == 3600
                            for a, b in zip(result['frames'], result['frames'][1:])))
        self.assertEqual(len(self.reads), 100)
        self.assertEqual(service.image(result['frames'][0]['url'].split('/')[-1]), self.png)

    def test_build_brackets_48_hours_between_hourly_timestamps(self):
        self.now += 23 * 60
        service = self.service()
        service._build(self.cycle)
        self.assertGreater(service.manifest['frames'][-1]['time'], self.now + 48 * 3600)
        result = service.snapshot()
        self.assertGreaterEqual(result['frames'][-1]['time'], self.now + 48 * 3600)
        self.assertLessEqual(result['frames'][-1]['time'], math.ceil((self.now + 48 * 3600) / 3600) * 3600)
        self.assertEqual(result['forecast_until'], int(self.now + 48 * 3600))
        self.assertEqual(len(self.reads), 100)

    def test_cached_images_avoid_more_provider_requests(self):
        service = self.service()
        service._build(self.cycle)
        service._build(self.cycle)
        self.assertEqual(len(self.reads), 100)

    def test_restart_restores_forecast_without_provider_requests_or_build(self):
        service = self.service()
        service._build(self.cycle)
        self.reads.clear()
        with patch('forecast_maps.threading.Thread') as worker:
            restored = self.service()
            result = restored.snapshot()
            worker.assert_not_called()
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(restored.manifest, service.manifest)
        self.assertTrue(result['coverage_complete'])
        self.assertEqual(self.reads, [])

    def test_restart_rejects_expired_manifest(self):
        service = self.service()
        service._build(self.cycle)
        self.now = self.cycle.timestamp() + 24 * 3600
        restored = self.service()
        restored.retry_after = self.now + 300
        self.assertIsNone(restored.manifest)
        self.assertEqual(restored.snapshot()['frames'], [])

    def test_restart_rejects_malformed_or_oversized_json(self):
        for content in ('{', '[]', '[' * 2000 + ']' * 2000, ' ' * 32769):
            with self.subTest(content=content[:20]):
                self.cached_manifest().write_text(content, encoding='utf-8')
                self.assertIsNone(self.service().manifest)

    def test_restart_checks_schema_model_run_timestamps_and_local_frame_urls(self):
        service = self.service()
        service._build(self.cycle)
        valid = service.manifest
        invalid = []
        for field, value in [('source', 'Different model'), ('units', 'in/h'),
                             ('resolution_km', True), ('bounds', [[0, 0], [1, 1]]),
                             ('model_run', int(self.now + 3600)),
                             ('model_run', int(self.cycle.timestamp()) + 3600),
                             ('model_run', True), ('fetched_at', int(self.now + 1)),
                             ('fetched_at', int(self.cycle.timestamp()) - 1),
                             ('frames', valid['frames'] + [valid['frames'][-1]])]:
            candidate = json.loads(json.dumps(valid))
            candidate[field] = value
            invalid.append((field + ':' + str(value)[:30], candidate))
        for field, value in [('url', '/forecast-frame/../outside.png'),
                             ('url', 'https://example.test/frame.png'),
                             ('url', '/forecast-frame/2026110818-010.png'),
                             ('time', valid['frames'][0]['time'] + 1),
                             ('time', True)]:
            candidate = json.loads(json.dumps(valid))
            candidate['frames'][0][field] = value
            invalid.append((field + ':' + str(value), candidate))
        candidate = json.loads(json.dumps(valid))
        del candidate['frames'][1]
        invalid.append(('missing hour', candidate))
        candidate = json.loads(json.dumps(valid))
        candidate['unexpected'] = 'field'
        invalid.append(('unexpected field', candidate))
        for label, manifest in invalid:
            with self.subTest(label=label):
                self.save_manifest(manifest)
                self.assertIsNone(self.service().manifest)

    def test_restart_rejects_missing_corrupt_oversized_or_symlink_images(self):
        service = self.service()
        service._build(self.cycle)
        path = Path(self.tmp.name) / service.manifest['frames'][0]['url'].split('/')[-1]
        path.unlink()
        self.assertIsNone(self.service().manifest)
        for data in (b'', b'not a PNG', self.png[:-8], b'x' * 4_000_001):
            path.write_bytes(data)
            self.assertIsNone(self.service().manifest)
        path.unlink()
        other = Path(self.tmp.name) / 'outside.png'
        other.write_bytes(self.png)
        path.symlink_to(other)
        self.assertIsNone(self.service().manifest)

    def test_restart_rejects_png_with_valid_chunks_but_undecodable_pixels(self):
        service = self.service()
        service._build(self.cycle)
        malformed = bytearray(self.png[:8])
        offset = 8
        while offset < len(self.png):
            size = int.from_bytes(self.png[offset:offset + 4], 'big')
            kind = self.png[offset + 4:offset + 8]
            payload = self.png[offset + 8:offset + 8 + size]
            if kind == b'IDAT':
                payload = b'x' * len(payload)
            malformed.extend(size.to_bytes(4, 'big') + kind + payload +
                             zlib.crc32(kind + payload).to_bytes(4, 'big'))
            offset += size + 12
        # Chunk checks alone accept this PNG, but browsers cannot decode it.
        with Image.open(BytesIO(malformed)) as image:
            image.verify()
        path = Path(self.tmp.name) / service.manifest['frames'][0]['url'].split('/')[-1]
        path.write_bytes(malformed)
        self.assertIsNone(self.service().manifest)

    def test_restart_rejects_symlinked_manifest(self):
        service = self.service()
        service._build(self.cycle)
        other = Path(self.tmp.name) / 'other.json'
        self.cached_manifest().rename(other)
        self.cached_manifest().symlink_to(other)
        self.assertIsNone(self.service().manifest)

    def test_corrupt_cached_image_is_rebuilt_instead_of_republished(self):
        service = self.service()
        service._build(self.cycle)
        path = Path(self.tmp.name) / service.manifest['frames'][0]['url'].split('/')[-1]
        path.write_bytes(b'incomplete image')
        service._build(self.cycle)
        self.assertEqual(len(self.reads), 102)
        self.assertEqual(path.read_bytes(), self.png)

    def test_failed_atomic_manifest_publication_preserves_previous_disk_and_memory(self):
        service = self.service()
        service._build(self.cycle)
        previous = service.manifest
        previous_disk = self.cached_manifest().read_bytes()
        replace = Path.replace

        def fail_manifest(path, target):
            if path.name == 'manifest.json.tmp':
                raise OSError('Disk publication failed')
            return replace(path, target)

        self.now += 3600
        with patch.object(Path, 'replace', fail_manifest), self.assertLogs('forecast_maps', level='ERROR'):
            service._build(self.cycle)
        self.assertIs(service.manifest, previous)
        self.assertEqual(self.cached_manifest().read_bytes(), previous_disk)
        self.assertFalse(service.building)
        self.assertGreater(service.retry_after, self.now)
        self.assertEqual(self.service().manifest, previous)

    def test_failed_refresh_reports_actual_remaining_forecast_coverage(self):
        service = self.service()
        service._build(self.cycle)
        self.now += 6 * 3600
        service.reader = lambda *args: (_ for _ in ()).throw(OSError('Provider unavailable'))
        with self.assertLogs('forecast_maps', level='ERROR'):
            service._build(datetime(2026, 11, 8, 18, tzinfo=timezone.utc))
        result = service.snapshot()
        self.assertEqual(result['status'], 'ready')
        self.assertFalse(result['coverage_complete'])
        self.assertFalse(result['updating'])
        self.assertEqual(result['forecast_until'], result['frames'][-1]['time'])
        self.assertLess(result['forecast_until'], self.now + 48 * 3600)

    def test_restart_serves_shorter_valid_cache_while_extending_in_background(self):
        service = self.service()
        service._build(self.cycle)
        self.now += 2 * 3600
        restored = self.service()
        with patch('forecast_maps.threading.Thread') as worker:
            result = restored.snapshot()
            worker.assert_called_once()
        self.assertEqual(result['status'], 'ready')
        self.assertTrue(result['updating'])
        self.assertFalse(result['coverage_complete'])
        self.assertEqual(result['forecast_until'], result['frames'][-1]['time'])
        self.assertEqual(len(self.reads), 100)

    def test_hourly_extension_reuses_all_but_one_cached_frame(self):
        self.now = datetime(2026, 11, 8, 20, 23, tzinfo=timezone.utc).timestamp()
        service = self.service()
        service._build(self.cycle)
        self.assertEqual(len(self.reads), 100)
        with patch('forecast_maps.threading.Thread') as worker:
            service.snapshot()
            worker.assert_not_called()
            self.now += 3600
            service.snapshot()
            worker.assert_called_once()
        service._build(self.cycle)
        self.assertEqual(len(self.reads), 102)
        self.assertGreaterEqual(service.snapshot()['frames'][-1]['time'], self.now + 48 * 3600)

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
