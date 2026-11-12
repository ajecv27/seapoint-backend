from copy import deepcopy
from datetime import datetime, timezone
import unittest

from forecast_service import RegionalForecastMaps, HOUR, HORIZON

RUN = int(datetime(2026, 11, 11, 18, tzinfo=timezone.utc).timestamp())
NOW = RUN + 6 * HOUR + 300


def report(provider='gfs', *, run=RUN, first=6, last=None):
    arome = provider == 'arome'
    if last is None:
        last = 48 if arome else 55
    cycle = datetime.fromtimestamp(run, timezone.utc).strftime('%Y%m%d%H')
    return {
        'status': 'ready', 'source': 'Météo-France AROME Antilles' if arome else 'NOAA GFS',
        'model_run': run, 'fetched_at': NOW - 100, 'units': 'mm/h',
        'bounds': [[10, -68], [22.9 if arome else 23, -55]],
        'resolution_km': 2.5 if arome else 28,
        'frames': [{'time': run + step * HOUR,
                    'url': '/forecast-frame/' +
                    (f'arome-{cycle}-{step:03d}-v1.png' if arome
                     else f'{cycle}-{step:03d}-s2.png')}
                   for step in range(first, last + 1)],
        'forecast_until': min(NOW + HORIZON, run + last * HOUR),
    }


class Provider:
    def __init__(self, value):
        self.value = value
        self.calls = 0
        self.images = []

    def snapshot(self):
        self.calls += 1
        if isinstance(self.value, Exception):
            raise self.value
        return deepcopy(self.value)

    def image(self, name):
        self.images.append(name)
        return name.encode()


class RegionalForecastTests(unittest.TestCase):
    def service(self, gfs=None, arome=None):
        return RegionalForecastMaps(
            gfs=Provider(report() if gfs is None else gfs),
            arome=Provider(report('arome') if arome is None else arome),
            clock=lambda: NOW)

    def test_regional_detail_and_gfs_tail_keep_exact_48_hour_horizon(self):
        service = self.service()
        result = service.snapshot()
        self.assertEqual(result['status'], 'ready')
        self.assertTrue(result['coverage_complete'])
        self.assertEqual(result['forecast_until'], NOW + HORIZON)
        self.assertEqual(len(result['frames']), 50)
        self.assertEqual(result['bounds'], [[10, -68], [22.9, -55]])
        self.assertEqual(result['resolution_range_km'], [2.5, 28])
        self.assertEqual(result['resolution_km'], 28)
        self.assertEqual(service.gfs.calls, 1)
        self.assertEqual(service.arome.calls, 1)
        for frame in result['frames']:
            step = (frame['time'] - RUN) // HOUR
            expected = 'arome-antilles' if step <= 48 else 'noaa-gfs'
            self.assertEqual(frame['provider'], expected)
            self.assertEqual(frame['model_run'], RUN)
            self.assertEqual(frame['period_seconds'], HOUR if step <= 48 else 0)
            self.assertEqual(frame['value_semantics'],
                             'previous_hour_mean' if step <= 48 else 'instantaneous_rate')
        segments = result['coverage_segments']
        self.assertEqual([segment['provider'] for segment in segments],
                         ['arome-antilles', 'noaa-gfs'])
        self.assertEqual(segments[0]['end_time'], RUN + 48 * HOUR)
        self.assertEqual(segments[1]['start_time'], RUN + 49 * HOUR)

    def test_missing_regional_hour_uses_gfs_without_losing_future_hours(self):
        arome = report('arome')
        arome['frames'] = [frame for frame in arome['frames']
                           if frame['time'] != RUN + 12 * HOUR]
        result = self.service(arome=arome).snapshot()
        self.assertTrue(result['coverage_complete'])
        self.assertEqual(len(result['frames']), 50)
        selected = {frame['time']: frame for frame in result['frames']}
        self.assertEqual(selected[RUN + 12 * HOUR]['provider'], 'noaa-gfs')
        self.assertEqual(selected[RUN + 11 * HOUR]['provider'], 'arome-antilles')
        self.assertEqual(selected[RUN + 13 * HOUR]['provider'], 'arome-antilles')
        self.assertEqual(len(result['coverage_segments']), 4)

    def test_preparing_regional_model_leaves_gfs_complete_and_playable(self):
        result = self.service(arome={'status': 'loading', 'frames': []}).snapshot()
        self.assertEqual(result['source'], 'NOAA GFS')
        self.assertTrue(result['coverage_complete'])
        self.assertTrue(result['updating'])
        self.assertEqual(result['bounds'], [[10, -68], [23, -55]])
        self.assertTrue(all(frame['provider'] == 'noaa-gfs' for frame in result['frames']))

    def test_stale_or_future_regional_issue_cannot_replace_current_gfs(self):
        for run in [RUN - 24 * HOUR, RUN + 12 * HOUR]:
            with self.subTest(run=run):
                result = self.service(arome=report('arome', run=run)).snapshot()
                self.assertEqual(result['source'], 'NOAA GFS')
                self.assertTrue(result['coverage_complete'])

    def test_regional_only_reports_actual_end_not_fictitious_48_hours(self):
        result = self.service(gfs={'status': 'unavailable', 'frames': []}).snapshot()
        self.assertEqual(result['status'], 'ready')
        self.assertFalse(result['coverage_complete'])
        self.assertEqual(result['forecast_until'], RUN + 48 * HOUR)
        self.assertLess(result['forecast_until'], NOW + HORIZON)
        self.assertEqual(result['resolution_km'], 2.5)

    def test_missing_hour_in_both_sources_is_not_complete_coverage(self):
        gfs, arome = report(), report('arome')
        for value in [gfs, arome]:
            value['frames'] = [frame for frame in value['frames']
                               if frame['time'] != RUN + 12 * HOUR]
        result = self.service(gfs=gfs, arome=arome).snapshot()
        self.assertFalse(result['coverage_complete'])
        self.assertEqual(len(result['frames']), 49)
        self.assertEqual(result['forecast_until'], NOW + HORIZON)

    def test_invalid_source_metadata_and_wrong_grib_url_cannot_override_gfs(self):
        for key, value in [('units', 'kg/m2'), ('resolution_km', 1),
                           ('bounds', [[10, -68], [23, -55]]),
                           ('fetched_at', NOW + HOUR)]:
            with self.subTest(key=key):
                arome = report('arome')
                arome[key] = value
                result = self.service(arome=arome).snapshot()
                self.assertEqual(result['source'], 'NOAA GFS')
        arome = report('arome')
        arome['frames'][0]['url'] = arome['frames'][1]['url']
        result = self.service(arome=arome).snapshot()
        self.assertEqual(result['frames'][0]['provider'], 'noaa-gfs')

    def test_no_past_only_or_false_ready_results(self):
        result = self.service(gfs={'status': 'ready', 'frames': []},
                              arome={'status': 'loading', 'frames': []}).snapshot()
        self.assertEqual(result['status'], 'loading')
        self.assertEqual(result['frames'], [])
        self.assertFalse(result['coverage_complete'])
        past = report(last=6)
        result = self.service(gfs=past, arome={'status': 'unavailable'}).snapshot()
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['frames'], [])

    def test_provider_exception_does_not_remove_other_valid_source(self):
        with self.assertLogs('forecast_service', level='ERROR'):
            result = self.service(arome=RuntimeError('temporary outage')).snapshot()
        self.assertTrue(result['coverage_complete'])
        self.assertEqual(result['source'], 'NOAA GFS')

    def test_images_delegate_without_reading_other_provider_or_unsafe_paths(self):
        service = self.service()
        self.assertEqual(service.image('arome-2026111118-006-v1.png'),
                         b'arome-2026111118-006-v1.png')
        self.assertEqual(service.image('2026111118-055-s2.png'),
                         b'2026111118-055-s2.png')
        for name in ['../private', 'arome-../x', r'arome-..\x', None]:
            self.assertIsNone(service.image(name))
        self.assertEqual(service.arome.images, ['arome-2026111118-006-v1.png'])
        self.assertEqual(service.gfs.images, ['2026111118-055-s2.png'])

    def test_different_model_runs_remain_attached_to_each_source_frame(self):
        now = NOW + 6 * HOUR
        gfs = report(first=12, last=61)
        arome = report('arome', run=RUN + 6 * HOUR)
        for value in [gfs, arome]:
            value['fetched_at'] = int(now - 100)
        result = RegionalForecastMaps(gfs=Provider(gfs), arome=Provider(arome),
                                      clock=lambda: now).snapshot()
        self.assertTrue(result['coverage_complete'])
        self.assertEqual(len(result['frames']), 50)
        self.assertEqual(result['model_run'], RUN + 6 * HOUR)
        for frame in result['frames']:
            self.assertEqual(frame['model_run'],
                             RUN + 6 * HOUR if frame['provider'] == 'arome-antilles' else RUN)


if __name__ == '__main__':
    unittest.main()
