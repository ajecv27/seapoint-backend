"""Regional high-resolution rain with a truthful longer-range GFS tail.

The providers own downloads, cache validation and image generation. This small
service only chooses between their already-published snapshots. Every frame
keeps its source, grid bounds and model issue time; clients must not interpolate
across provider/model boundaries.
"""
from copy import deepcopy
from datetime import datetime, timezone
import logging
import math
import re
import time

LOG = logging.getLogger(__name__)
HOUR = 3600
HORIZON = 48 * HOUR
PROVIDERS = {
    'noaa-gfs': {
        'source': 'NOAA GFS', 'resolution_km': 28,
        'bounds': [[10.0, -68.0], [23.0, -55.0]],
        'period_seconds': 0, 'value_semantics': 'instantaneous_rate',
        'maximum_step': 120,
        'name': re.compile(r'\d{10}-\d{3}(?:-s2)?\.png'),
    },
    'arome-antilles': {
        'source': 'Météo-France AROME Antilles', 'resolution_km': 2.5,
        'bounds': [[10.0, -68.0], [22.9, -55.0]],
        'period_seconds': HOUR, 'value_semantics': 'previous_hour_mean',
        'maximum_step': 48,
        'name': re.compile(r'arome-\d{10}-\d{3}-v1\.png'),
    },
}


class RegionalForecastMaps:
    def __init__(self, gfs=None, arome=None, clock=None):
        # Lazy imports keep this selector independently testable while the
        # provider modules retain their own optional decoding dependencies.
        self.clock = clock or time.time
        if gfs is None:
            from forecast_maps import ForecastMaps
            gfs = ForecastMaps(clock=self.clock)
        if arome is None:
            from arome_maps import AromeMaps
            arome = AromeMaps(clock=self.clock)
        self.gfs = gfs
        self.arome = arome

    @staticmethod
    def _snapshot(provider):
        try:
            result = provider.snapshot()
            return result if isinstance(result, dict) else {'status': 'unavailable'}
        except Exception:
            LOG.exception('A forecast provider snapshot is unavailable')
            return {'status': 'unavailable'}

    @staticmethod
    def _frames(snapshot, provider, now):
        spec = PROVIDERS[provider]
        run = snapshot.get('model_run')
        fetched = snapshot.get('fetched_at')
        if (snapshot.get('status') != 'ready' or
                snapshot.get('units') != 'mm/h' or
                snapshot.get('bounds') != spec['bounds'] or
                snapshot.get('resolution_km') != spec['resolution_km'] or
                type(run) is not int or run <= 0 or run % (6 * HOUR) or
                not 0 <= now - run < 24 * HOUR or
                type(fetched) is not int or not run <= fetched <= now + 60 or
                not isinstance(snapshot.get('frames'), list)):
            return []
        end = math.ceil(now / HOUR) * HOUR + HORIZON
        cycle = datetime.fromtimestamp(run, timezone.utc).strftime('%Y%m%d%H')
        frames = {}
        # Bound malformed provider responses independently of disk validation.
        for frame in snapshot['frames'][:122]:
            if not isinstance(frame, dict):
                continue
            stamp, url = frame.get('time'), frame.get('url')
            if (type(stamp) is not int or not now - HOUR <= stamp <= end or
                    not isinstance(url, str) or not url.startswith('/forecast-frame/')):
                continue
            step, remainder = divmod(stamp - run, HOUR)
            name = url.removeprefix('/forecast-frame/')
            if (remainder or not 1 <= step <= spec['maximum_step'] or
                    not spec['name'].fullmatch(name)):
                continue
            # Validate URL timestamp/step identity, not just the filename shape.
            expected = (f'arome-{cycle}-{step:03d}-v1.png' if provider == 'arome-antilles'
                        else f'{cycle}-{step:03d}-s2.png')
            legacy = f'{cycle}-{step:03d}.png'
            if name != expected and not (provider == 'noaa-gfs' and name == legacy):
                continue
            frames[stamp] = {
                'time': stamp, 'url': url, 'provider': provider,
                'source': spec['source'], 'model_run': run,
                'bounds': deepcopy(spec['bounds']),
                'resolution_km': spec['resolution_km'],
                'period_seconds': spec['period_seconds'],
                'value_semantics': spec['value_semantics'],
            }
        return [frames[key] for key in sorted(frames)]

    @staticmethod
    def _segments(frames):
        segments = []
        for frame in frames:
            previous = segments[-1] if segments else None
            if (previous and previous['provider'] == frame['provider'] and
                    previous['model_run'] == frame['model_run'] and
                    previous['end_time'] + HOUR == frame['time']):
                previous['end_time'] = frame['time']
                previous['frame_count'] += 1
                continue
            segments.append({
                key: deepcopy(frame[key]) for key in (
                    'provider', 'source', 'model_run', 'bounds',
                    'resolution_km', 'period_seconds', 'value_semantics')
            } | {'start_time': frame['time'], 'end_time': frame['time'],
                 'frame_count': 1})
        return segments

    def snapshot(self):
        now = self.clock()
        snapshots = {
            'noaa-gfs': self._snapshot(self.gfs),
            'arome-antilles': self._snapshot(self.arome),
        }
        fields = {key: self._frames(value, key, now)
                  for key, value in snapshots.items()}
        # Regional detail replaces matching GFS timestamps, never a larger
        # interval containing missing AROME hours. GFS remains the full tail.
        chosen = {frame['time']: frame for frame in fields['noaa-gfs']}
        chosen.update({frame['time']: frame for frame in fields['arome-antilles']})
        frames = [chosen[key] for key in sorted(chosen)]
        if not frames or frames[-1]['time'] <= now:
            loading = any(value.get('status') == 'loading' for value in snapshots.values())
            return {
                'status': 'loading' if loading else 'unavailable', 'frames': [],
                'bounds': deepcopy(PROVIDERS['noaa-gfs']['bounds']),
                'source': 'Météo-France AROME Antilles / NOAA GFS',
                'units': 'mm/h', 'retry_seconds': 15,
                'coverage_complete': False, 'horizon_hours': 48,
            }
        used = list(dict.fromkeys(frame['provider'] for frame in frames))
        bounds = [
            [max(PROVIDERS[key]['bounds'][0][0] for key in used),
             max(PROVIDERS[key]['bounds'][0][1] for key in used)],
            [min(PROVIDERS[key]['bounds'][1][0] for key in used),
             min(PROVIDERS[key]['bounds'][1][1] for key in used)],
        ]
        complete = (frames[0]['time'] <= now and
                    frames[-1]['time'] >= now + HORIZON and
                    all(right['time'] - left['time'] == HOUR
                        for left, right in zip(frames, frames[1:])))
        sources = [{
            'provider': key, 'source': PROVIDERS[key]['source'],
            'model_run': snapshots[key]['model_run'],
            'resolution_km': PROVIDERS[key]['resolution_km'],
            'bounds': deepcopy(PROVIDERS[key]['bounds']),
            'period_seconds': PROVIDERS[key]['period_seconds'],
            'value_semantics': PROVIDERS[key]['value_semantics'],
        } for key in used]
        return {
            'status': 'ready', 'source': ' + '.join(PROVIDERS[key]['source'] for key in used),
            'sources': sources, 'model_run': frames[0]['model_run'],
            'fetched_at': min(snapshots[key]['fetched_at'] for key in used),
            'units': 'mm/h', 'bounds': bounds,
            # The single legacy value conservatively describes the coarsest
            # part; the range/frames/segments describe actual regional detail.
            'resolution_km': max(PROVIDERS[key]['resolution_km'] for key in used),
            'resolution_range_km': sorted({PROVIDERS[key]['resolution_km'] for key in used}),
            'frames': frames, 'coverage_segments': self._segments(frames),
            'forecast_until': min(int(now + HORIZON), frames[-1]['time']),
            'coverage_complete': complete, 'horizon_hours': 48,
            'updating': any(value.get('updating') or value.get('status') == 'loading'
                            for value in snapshots.values()),
            'provider_status': {
                key: ('ready' if fields[key] else
                      'loading' if value.get('status') == 'loading' else 'unavailable')
                for key, value in snapshots.items()},
        }

    def image(self, name):
        if (not isinstance(name, str) or len(name) > 128 or
                '/' in name or '\\' in name):
            return None
        return self.arome.image(name) if name.startswith('arome-') else self.gfs.image(name)
