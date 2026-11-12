"""AROME source semantics, truthful coverage, and cache recovery regressions."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

import arome_maps as am

UTC = timezone.utc
CYCLE = datetime(2026, 11, 11, 18, tzinfo=UTC)


def png_bytes():
    output = BytesIO()
    Image.new('RGBA', (640, 640), (75, 109, 228, 200)).save(output, 'PNG')
    return output.getvalue()


def grib_bytes(hour=6, value=2.0, parameter=52, **overrides):
    """Create a real, deterministic source-grid record, without network fixtures."""
    import eccodes as ec
    handle = ec.codes_grib_new_from_samples('regular_ll_sfc_grib2')
    try:
        settings = {
            'centre': 'lfpw', 'tablesVersion': 15, 'localTablesVersion': 0,
            'discipline': 0, 'parameterCategory': 1,
            'parameterNumber': parameter, 'stepType': 'accum',
            'dataDate': 20261111, 'dataTime': 1800,
            'Ni': 945, 'Nj': 529,
            'latitudeOfFirstGridPointInDegrees': 22.9,
            'longitudeOfFirstGridPointInDegrees': 284.7,
            'latitudeOfLastGridPointInDegrees': 9.7,
            'longitudeOfLastGridPointInDegrees': 308.3,
            'iDirectionIncrementInDegrees': .025,
            'jDirectionIncrementInDegrees': .025,
            'iScansNegatively': 0, 'jScansPositively': 0,
            'startStep': 0, 'endStep': hour,
        }
        settings.update(overrides)
        for key, setting in settings.items():
            ec.codes_set(handle, key, setting)
        ec.codes_set_values(handle, np.full(int(settings['Ni']) * int(settings['Nj']), value))
        return ec.codes_get_message(handle)
    finally:
        ec.codes_release(handle)


class AromeFieldTests(unittest.TestCase):
    def test_selects_and_decodes_total_precipitation_from_surface_package(self):
        rain = grib_bytes(value=2)
        # Another valid GRIB record must not be mistaken for precipitation.
        other = grib_bytes(value=5, parameter=1)
        selected = am.extract_precipitation(other + rain, int(CYCLE.timestamp()), 6)
        values, quantum = am.decode_accumulation(selected, int(CYCLE.timestamp()), 6)
        self.assertEqual(values.shape, (529, 945))
        np.testing.assert_allclose(values, 2)
        self.assertGreaterEqual(quantum, 0)
        self.assertLess(quantum, .1)

    def test_mismatched_model_hour_and_source_grid_are_rejected(self):
        good = grib_bytes()
        for cycle, hour in [(int(CYCLE.timestamp()) + 21600, 6),
                            (int(CYCLE.timestamp()), 7)]:
            with self.subTest(cycle=cycle, hour=hour), self.assertRaises(ValueError):
                am.decode_accumulation(good, cycle, hour)
        for bad in [grib_bytes(startStep=3),
                    grib_bytes(Ni=944),
                    grib_bytes(jScansPositively=1),
                    grib_bytes(iDirectionIncrementInDegrees=.05)]:
            with self.subTest(length=len(bad)), self.assertRaises(ValueError):
                am.decode_accumulation(bad, int(CYCLE.timestamp()), 6)

    def test_non_precipitation_or_non_grib_package_cannot_become_a_dry_forecast(self):
        for content in [b'<html>Provider error</html>', b'', grib_bytes(parameter=1)]:
            with self.subTest(length=len(content)), self.assertRaises(ValueError):
                am.extract_precipitation(content, int(CYCLE.timestamp()), 6)

    def test_hourly_difference_is_mm_per_hour_not_accumulated_or_per_second(self):
        previous = np.full((529, 945), .5)
        current = np.full((529, 945), 2.0)
        with patch.object(am, 'decode_accumulation', side_effect=[(previous, .001), (current, .001)]):
            result = am.render_hour(b'previous', b'current', int(CYCLE.timestamp()), 6)
        image = Image.open(BytesIO(result)).convert('RGBA')
        self.assertEqual(image.size, (640, 640))
        # 1.5 mm in exactly one hour is 1.5 mm/h, midway between palette .5/2.5.
        self.assertEqual(image.getpixel((320, 320)), (75, 109, 228, 200))

    def test_only_quantization_bounded_accumulation_decreases_are_clipped(self):
        previous = np.full((529, 945), .5)
        with patch.object(am, 'decode_accumulation', side_effect=[
            (previous, .01), (previous - .015, .01)
        ]):
            result = am.render_hour(b'previous', b'current', int(CYCLE.timestamp()), 6)
        self.assertIsNone(Image.open(BytesIO(result)).getchannel('A').getbbox())
        with patch.object(am, 'decode_accumulation', side_effect=[
            (previous, .01), (previous - .1, .01)
        ]), self.assertRaises(ValueError):
            am.render_hour(b'previous', b'current', int(CYCLE.timestamp()), 6)


class AromeCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = datetime(2026, 11, 12, 1, 30, tzinfo=UTC).timestamp()
        self.reads = []
        self.png = png_bytes()
        self.extract = patch.object(am, 'extract_precipitation',
                                    side_effect=lambda data, cycle, hour: data)
        self.extract.start()
        self.addCleanup(self.extract.stop)
        self.decode = patch.object(am, 'decode_accumulation',
                                   return_value=(np.zeros((529, 945)), .001))
        self.decode.start()
        self.addCleanup(self.decode.stop)

    def reader(self, url):
        self.reads.append(url)
        return b'GRIB-private-unit-fixture'

    def service(self, **kwargs):
        return am.AromeMaps(directory=self.temp.name,
                            reader=kwargs.get('reader', self.reader),
                            renderer=kwargs.get('renderer', lambda *args: self.png),
                            clock=lambda: self.now)

    def build(self):
        service = self.service()
        service._build(CYCLE)
        self.assertIsNotNone(service.manifest)
        return service

    def test_source_horizon_ends_at_run_plus_48_not_48_from_request(self):
        service = self.build()
        result = service.snapshot()
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['resolution_km'], 2.5)
        self.assertEqual(result['bounds'], [[10.0, -68.0], [22.9, -55.0]])
        self.assertEqual(result['units'], 'mm/h')
        self.assertEqual(result['frames'][-1]['time'], int(CYCLE.timestamp() + 48 * 3600))
        self.assertEqual(result['forecast_until'], result['frames'][-1]['time'])
        self.assertLess(result['forecast_until'], self.now + 48 * 3600)
        self.assertFalse(result['coverage_complete'])
        self.assertTrue(all(b['time'] - a['time'] == 3600
                            for a, b in zip(result['frames'], result['frames'][1:])))
        self.assertTrue(all('arome-' in frame['url'] for frame in result['frames']))
        self.assertEqual(service.image(result['frames'][0]['url'].rsplit('/', 1)[-1]), self.png)
        self.assertIsNone(service.image('../outside.png'))
        self.assertIsNone(service.image('/tmp/source.png'))

    def test_restart_uses_verified_local_manifest_without_new_downloads(self):
        service = self.build()
        self.reads.clear()
        with patch.object(am.threading, 'Thread') as worker:
            restarted = self.service()
            self.assertEqual(restarted.snapshot()['status'], 'ready')
            worker.assert_not_called()
        self.assertEqual(restarted.manifest, service.manifest)
        self.assertEqual(self.reads, [])

    def test_repeat_build_reuses_cached_images_and_extracted_records(self):
        service = self.build()
        downloaded = len(self.reads)
        service._build(CYCLE)
        self.assertEqual(len(self.reads), downloaded)
        # Whole SP1 packages should not be retained in the production cache.
        self.assertFalse(any('__SP1__' in p.name for p in Path(self.temp.name).iterdir()))

    def test_corrupt_or_missing_image_cannot_be_restored_as_current_forecast(self):
        service = self.build()
        image = Path(self.temp.name) / service.manifest['frames'][0]['url'].rsplit('/', 1)[-1]
        image.write_bytes(b'not a png')
        self.assertIsNone(self.service().manifest)
        image.unlink()
        self.assertIsNone(self.service().manifest)

    def test_manifest_cannot_reference_external_images_or_change_source_times(self):
        service = self.build()
        valid = service.manifest
        manifest_path = Path(self.temp.name) / am.MANIFEST_NAME
        for field, value in [('url', 'https://other.example/fake.png'),
                             ('url', '/forecast-frame/../outside.png'),
                             ('time', valid['frames'][0]['time'] + 1)]:
            candidate = json.loads(json.dumps(valid))
            candidate['frames'][0][field] = value
            manifest_path.write_text(json.dumps(candidate))
            with self.subTest(field=field, value=value):
                self.assertIsNone(self.service().manifest)
        manifest_path.write_text('{' * 100)
        self.assertIsNone(self.service().manifest)

    def test_failed_new_cycle_preserves_last_valid_forecast_and_backs_off(self):
        service = self.build()
        before = json.loads(json.dumps(service.manifest))
        disk_before = (Path(self.temp.name) / am.MANIFEST_NAME).read_bytes()
        self.now = datetime(2026, 11, 12, 8, tzinfo=UTC).timestamp()
        def unavailable(_):
            raise OSError('test provider outage')
        service.reader = unavailable
        service._build(datetime(2026, 11, 12, 0, tzinfo=UTC))
        self.assertEqual(service.manifest, before)
        self.assertEqual((Path(self.temp.name) / am.MANIFEST_NAME).read_bytes(), disk_before)
        self.assertGreater(service.retry_after, self.now)
        result = service.snapshot()
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['model_run'], before['model_run'])
        self.assertTrue(result['frames'])
        self.assertLess(result['forecast_until'], self.now + 48 * 3600)

    def test_stale_model_is_not_advertised_as_fresh_after_restart(self):
        service = self.build()
        self.now = CYCLE.timestamp() + 24 * 3600
        restarted = self.service()
        restarted.retry_after = self.now + 300
        self.assertIsNone(restarted.manifest)
        self.assertEqual(restarted.snapshot()['frames'], [])

    def test_corrupt_extracted_record_is_refetched_when_an_image_needs_rebuilding(self):
        service = self.build()
        image = Path(self.temp.name) / service.manifest['frames'][0]['url'].rsplit('/', 1)[-1]
        image.unlink()
        record = sorted(Path(self.temp.name).glob('*.grib2'))[0]
        record.write_bytes(b'corrupt record')
        self.reads.clear()
        def decode(data, *args):
            if data == b'corrupt record':
                raise ValueError('cached GRIB framing invalid')
            return np.zeros((529, 945)), .001
        with patch.object(am, 'decode_accumulation', side_effect=decode):
            service._build(CYCLE)
        self.assertEqual(len(self.reads), 1)
        self.assertEqual(image.read_bytes(), self.png)
        self.assertNotEqual(record.read_bytes(), b'corrupt record')

    def test_provider_parallelism_is_bounded_to_three_requests(self):
        active = peak = 0
        lock = threading.Lock()
        def delayed_reader(url):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            try:
                time.sleep(.003)
                return b'GRIB-private-unit-fixture'
            finally:
                with lock:
                    active -= 1
        service = self.service(reader=delayed_reader)
        service._build(CYCLE)
        self.assertIsNotNone(service.manifest)
        self.assertGreaterEqual(peak, 2)
        self.assertLessEqual(peak, 3)

    def test_only_one_background_build_starts_for_repeated_snapshots(self):
        service = self.service()
        with patch.object(am.threading, 'Thread') as worker:
            service.snapshot()
            service.snapshot()
            self.assertEqual(worker.call_count, 1)


if __name__ == '__main__':
    unittest.main()
