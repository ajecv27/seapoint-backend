from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

from forecast_runtime import ForecastRuntime


class Service:
    def __init__(self):
        self.snapshot_calls = 0
        self.image_calls = []
        self.report = {'status': 'ready', 'frames': [{'time': 1}], 'horizon_hours': 48}

    def snapshot(self):
        self.snapshot_calls += 1
        return self.report

    def image(self, name):
        self.image_calls.append(name)
        return b'cached-image'


class ForecastRuntimeTests(unittest.TestCase):
    def wait_ready(self, runtime):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            report = runtime.snapshot()
            if report['status'] == 'ready':
                return report
            threading.Event().wait(.005)
        self.fail('Forecast runtime did not become ready')

    def test_import_does_not_load_forecast_providers_or_numerical_decoders(self):
        source = '''import sys
import forecast_runtime
assert not any(name in sys.modules for name in
    ['forecast_service', 'forecast_maps', 'arome_maps', 'numpy', 'PIL', 'eccodes'])
forecast_runtime.ForecastRuntime()
assert 'forecast_service' not in sys.modules
'''
        result = subprocess.run([sys.executable, '-c', source],
                                cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_slow_provider_import_and_restore_do_not_block_forecast_requests(self):
        entered, release = threading.Event(), threading.Event()
        service = Service()
        def factory():
            entered.set()
            release.wait(2)
            return service
        runtime = ForecastRuntime(factory=factory)
        self.addCleanup(release.set)
        self.assertTrue(runtime.start())
        self.assertTrue(entered.wait(1))
        started = time.monotonic()
        report = runtime.snapshot()
        self.assertIsNone(runtime.image('arome-frame.png'))
        self.assertLess(time.monotonic() - started, .2)
        self.assertEqual(report['status'], 'loading')
        self.assertEqual(report['frames'], [])
        self.assertFalse(report['coverage_complete'])
        self.assertNotIn('forecast_until', report)
        release.set()
        self.assertEqual(self.wait_ready(runtime), service.report)
        self.assertEqual(runtime.image('arome-frame.png'), b'cached-image')
        self.assertEqual(service.image_calls, ['arome-frame.png'])

    def test_concurrent_initial_requests_start_only_one_provider_service(self):
        entered, release = threading.Event(), threading.Event()
        calls = []
        def factory():
            calls.append(1)
            entered.set()
            release.wait(2)
            return Service()
        runtime = ForecastRuntime(factory=factory)
        self.addCleanup(release.set)
        with ThreadPoolExecutor(max_workers=12) as pool:
            reports = list(pool.map(lambda _: runtime.snapshot(), range(24)))
        self.assertTrue(entered.wait(1))
        self.assertEqual(len(calls), 1)
        self.assertTrue(all(report['status'] == 'loading' for report in reports))
        release.set()
        self.wait_ready(runtime)
        self.assertFalse(runtime.start())
        self.assertEqual(len(calls), 1)

    def test_failed_initialization_retries_after_backoff_without_false_coverage(self):
        clock = [100.0]
        failed, release = threading.Event(), threading.Event()
        calls = []
        def factory():
            calls.append(1)
            if len(calls) == 1:
                failed.set()
                raise OSError('test cache restore failure')
            release.wait(2)
            return Service()
        runtime = ForecastRuntime(factory=factory, clock=lambda: clock[0])
        self.addCleanup(release.set)
        with patch('forecast_runtime.LOG.exception'):
            runtime.start()
            self.assertTrue(failed.wait(1))
            deadline = time.monotonic() + 1
            while runtime.snapshot()['status'] != 'unavailable' and time.monotonic() < deadline:
                threading.Event().wait(.005)
        report = runtime.snapshot()
        self.assertEqual(report['status'], 'unavailable')
        self.assertEqual(report['frames'], [])
        self.assertFalse(report['coverage_complete'])
        clock[0] = 114.9
        self.assertFalse(runtime.start())
        self.assertEqual(len(calls), 1)
        clock[0] = 115.0
        self.assertTrue(runtime.start())
        self.assertEqual(runtime.snapshot()['status'], 'loading')
        release.set()
        self.wait_ready(runtime)
        self.assertEqual(len(calls), 2)

    def test_slow_initial_warm_snapshot_does_not_block_http_readers(self):
        entered, release = threading.Event(), threading.Event()
        class SlowWarm(Service):
            def snapshot(self):
                if not self.snapshot_calls:
                    entered.set()
                    release.wait(2)
                return super().snapshot()
        service = SlowWarm()
        runtime = ForecastRuntime(factory=lambda: service)
        self.addCleanup(release.set)
        runtime.start()
        self.assertTrue(entered.wait(1))
        self.assertEqual(runtime.snapshot()['status'], 'loading')
        self.assertIsNone(runtime.image('cached.png'))
        release.set()
        self.assertEqual(self.wait_ready(runtime), service.report)

    def test_ready_snapshot_and_image_failures_do_not_remove_a_valid_service(self):
        service = Service()
        runtime = ForecastRuntime(factory=lambda: service)
        self.wait_ready(runtime)
        with patch.object(service, 'snapshot', side_effect=OSError('test read failure')):
            with patch('forecast_runtime.LOG.exception'):
                report = runtime.snapshot()
            self.assertEqual(report['status'], 'unavailable')
            self.assertFalse(report['coverage_complete'])
        with patch.object(service, 'image', side_effect=OSError('test image read failure')):
            with patch('forecast_runtime.LOG.exception'):
                self.assertIsNone(runtime.image('cached.png'))
        self.assertEqual(runtime.snapshot(), service.report)
        self.assertEqual(runtime.image('cached.png'), b'cached-image')


if __name__ == '__main__':
    unittest.main()
