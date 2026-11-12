"""Regional forecast images from public NOAA GFS; no weather API key needed."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import logging
import math
import os
from pathlib import Path
import re
import threading
import time
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image

UTC = timezone.utc
BOUNDS = [[10.0, -68.0], [23.0, -55.0]]
HOST = 'https://noaa-gfs-bdp-pds.s3.amazonaws.com'
LOG = logging.getLogger(__name__)
HORIZON_HOURS = 48
# Version public image URLs as well as the private manifest so old styles are
# neither restored after restart nor reused from a browser's image cache.
RENDER_STYLE = 's2'
MANIFEST_NAME = f'manifest-{RENDER_STYLE}.json'
MAX_MANIFEST_BYTES = 32_768
MAX_IMAGE_BYTES = 4_000_000


def read_url(url, byte_range=None):
    headers = {'User-Agent': 'SeaPoint-Forecast/1.0'}
    if byte_range:
        headers['Range'] = f'bytes={byte_range[0]}-{byte_range[1]}'
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        if byte_range and response.status != 206:
            raise ValueError('Provider did not honor the GRIB byte range')
        data = response.read(4_000_001)
        if len(data) > 4_000_000:
            raise ValueError('Unexpected forecast record size')
        return data


def precipitation_range(index):
    lines = index.splitlines()
    for i, line in enumerate(lines[:-1]):
        # Instantaneous precipitation RATE, not accumulated rainfall or a
        # multi-hour average. Each displayed value is converted to mm/hour.
        if ':PRATE:surface:' in line and 'ave' not in line and 'acc' not in line:
            return int(line.split(':')[1]), int(lines[i + 1].split(':')[1]) - 1
    raise ValueError('No instantaneous precipitation-rate field')


def rgba(rates):
    """Forecast scale in mm/hour, with a continuous light-rain opacity edge.

    The same thresholds and colours describe intensity. Opacity rises smoothly
    from 0 at 0.1 mm/hour to the existing 200 at 0.6, avoiding a solid outline
    around every tiny amount of forecast drizzle.
    """
    levels = np.array([0.1, 0.5, 2.5, 7.5, 15, 30, 60])
    colors = np.array([[100, 210, 255], [45, 140, 245], [106, 78, 211],
                       [215, 55, 143], [255, 158, 70], [255, 230, 65], [255, 255, 190]])
    pixels = np.zeros((*rates.shape, 4), dtype=np.uint8)
    safe_rates = np.where(np.isfinite(rates), rates, 0)
    for channel in range(3):
        pixels[..., channel] = np.interp(safe_rates, levels, colors[:, channel]).astype(np.uint8)
    edge = np.clip((safe_rates - 0.1) / 0.5, 0, 1)
    opacity = 200 * edge * edge * (3 - 2 * edge)
    pixels[..., 3] = np.rint(np.where(np.isfinite(rates), opacity, 0)).astype(np.uint8)
    return pixels


def sample_rates(values, x, y):
    """Sample the model grid for display without creating new extrema.

    Catmull-Rom curves soften the bilinear grid's corners. Clamping each output
    to its four surrounding model values prevents cubic ringing from creating
    stronger rainfall, negative rates, or wet islands inside a dry grid cell.
    This is spatial display interpolation, not additional forecast resolution.
    Longitude wraps at the global grid seam; latitude clamps at the poles.
    """
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = (x - x0)[None, :], (y - y0)[:, None]
    height, width = values.shape

    def cubic(a, b, c, d, t):
        return b + 0.5 * t * (c - a + t *
               (2 * a - 5 * b + 4 * c - d + t * (3 * (b - c) + d - a)))

    rows = []
    for dy in (-1, 0, 1, 2):
        yy = np.clip(y0 + dy, 0, height - 1)[:, None]
        samples = [values[yy, ((x0 + dx) % width)[None, :]]
                   for dx in (-1, 0, 1, 2)]
        rows.append(cubic(*samples, fx))
    interpolated = cubic(*rows, fy)
    neighbors = [values[np.clip(y0 + dy, 0, height - 1)[:, None],
                        ((x0 + dx) % width)[None, :]]
                 for dy in (0, 1) for dx in (0, 1)]
    return np.maximum(0, np.clip(interpolated, np.minimum.reduce(neighbors),
                                 np.maximum.reduce(neighbors)))


def render_grib(data, expected_time):
    import eccodes as ec
    handle = ec.codes_new_from_message(data)
    try:
        valid = datetime.strptime(
            str(ec.codes_get(handle, 'validityDate')) +
            f"{ec.codes_get(handle, 'validityTime'):04d}", '%Y%m%d%H%M').replace(tzinfo=UTC)
        if int(valid.timestamp()) != expected_time:
            raise ValueError('Forecast timestamp mismatch')
        if ec.codes_get(handle, 'shortName') != 'prate' or ec.codes_get(handle, 'stepType') != 'instant':
            raise ValueError('Unexpected precipitation field')
        if ec.codes_get(handle, 'units') != 'kg m**-2 s**-1':
            raise ValueError('Unexpected precipitation units')
        ni, nj = ec.codes_get(handle, 'Ni'), ec.codes_get(handle, 'Nj')
        if (ni, nj) != (1440, 721) or ec.codes_get(handle, 'jScansPositively') or ec.codes_get(handle, 'iScansNegatively'):
            raise ValueError('Unexpected GFS grid')
        values = ec.codes_get_values(handle).reshape(nj, ni)
        south, west = BOUNDS[0]
        north, east = BOUNDS[1]
        # Sample into Web Mercator so the image aligns with Leaflet's map.
        width = height = 640
        top = math.asinh(math.tan(math.radians(north)))
        bottom = math.asinh(math.tan(math.radians(south)))
        latitudes = np.degrees(np.arctan(np.sinh(np.linspace(top, bottom, height))))
        longitudes = np.linspace(west % 360, east % 360, width)
        y = (90 - latitudes) / 0.25
        x = longitudes / 0.25
        rates = sample_rates(values, x, y) * 3600
        output = BytesIO()
        Image.fromarray(rgba(rates)).save(output, format='PNG')
        return output.getvalue()
    finally:
        ec.codes_release(handle)


class ForecastMaps:
    def __init__(self, directory=None, reader=None, renderer=None, clock=None, horizon_hours=48):
        if type(horizon_hours) is not int or not 48 <= horizon_hours <= 72:
            raise ValueError('Forecast horizon must be between 48 and 72 hours')
        self.horizon_hours = horizon_hours
        self.directory = Path(directory or os.environ.get(
            'SEAPOINT_FORECAST_CACHE', Path(__file__).with_name('forecast-cache')))
        self.reader = reader or read_url
        self.renderer = renderer or render_grib
        self.clock = clock or time.time
        self.lock = threading.Lock()
        self.building = False
        self.retry_after = 0
        self.manifest = None
        self.generation = None
        self._restore()

    @staticmethod
    def _valid_png(data):
        if not 0 < len(data) <= MAX_IMAGE_BYTES:
            return False
        try:
            with Image.open(BytesIO(data)) as image:
                if image.format != 'PNG' or image.size != (640, 640):
                    return False
                image.verify()
            # PNG chunk checks alone do not detect an invalid compressed
            # pixel stream. Decode the bounded image as the browser must.
            with Image.open(BytesIO(data)) as image:
                image.load()
            return True
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
            return False

    def _cached_image_valid(self, path):
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_IMAGE_BYTES:
                return False
            with path.open('rb') as image:
                return self._valid_png(image.read(MAX_IMAGE_BYTES + 1))
        except OSError:
            return False

    def _restore(self):
        """Only restore complete, local manifests produced by this service."""
        path = self.directory / MANIFEST_NAME
        try:
            if path.is_symlink() or not path.is_file():
                return
            with path.open('rb') as cached:
                content = cached.read(MAX_MANIFEST_BYTES + 1)
            if len(content) > MAX_MANIFEST_BYTES:
                return
            manifest = json.loads(content)
            if (not isinstance(manifest, dict) or
                    set(manifest) != {'source', 'model_run', 'fetched_at', 'units',
                                      'resolution_km', 'bounds', 'frames'} or
                    manifest['source'] != 'NOAA GFS' or manifest['units'] != 'mm/h' or
                    type(manifest['resolution_km']) is not int or manifest['resolution_km'] != 28 or
                    manifest['bounds'] != BOUNDS):
                return
            model_run, fetched_at = manifest['model_run'], manifest['fetched_at']
            now = self.clock()
            if (type(model_run) is not int or type(fetched_at) is not int or
                    model_run <= 0 or model_run % (6 * 3600) or
                    not 0 <= now - model_run < 24 * 3600 or
                    not model_run <= fetched_at <= now):
                return
            frames = manifest['frames']
            if not isinstance(frames, list) or not 2 <= len(frames) <= self.horizon_hours + 2:
                return
            cycle = datetime.fromtimestamp(model_run, UTC)
            previous = None
            for frame in frames:
                if (not isinstance(frame, dict) or set(frame) != {'time', 'url'} or
                        type(frame['time']) is not int or not isinstance(frame['url'], str)):
                    return
                stamp = frame['time']
                hour, remainder = divmod(stamp - model_run, 3600)
                expected = f'/forecast-frame/{cycle:%Y%m%d%H}-{hour:03d}-{RENDER_STYLE}.png'
                if (remainder or not 1 <= hour <= 120 or frame['url'] != expected or
                        (previous is not None and stamp - previous != 3600) or
                        not self._cached_image_valid(self.directory / expected.rsplit('/', 1)[-1])):
                    return
                previous = stamp
            if not frames[0]['time'] <= fetched_at <= frames[-1]['time'] or frames[-1]['time'] <= now:
                return
            self.manifest = manifest
            self.generation = cycle.strftime('%Y%m%d%H')
        except (OSError, ValueError, TypeError, OverflowError, RecursionError):
            # A cache is optional. Malformed/interrupted files must not prevent
            # the server from starting or turn old images into current data.
            return

    def snapshot(self):
        now = self.clock()
        # Allow publication time, then select a six-hourly model run.
        cycle = datetime.fromtimestamp(now - 5 * 3600, UTC)
        cycle = cycle.replace(hour=cycle.hour // 6 * 6, minute=0, second=0, microsecond=0)
        generation = cycle.strftime('%Y%m%d%H')
        required_end = math.ceil(now / 3600) * 3600 + self.horizon_hours * 3600
        with self.lock:
            manifest = self.manifest
            refresh = (self.generation != generation or not manifest or
                       manifest['frames'][-1]['time'] < required_end)
            if refresh and not self.building and now >= self.retry_after:
                self.building = True
                threading.Thread(target=self._build, args=(cycle,), daemon=True).start()
            if manifest and now - manifest['model_run'] < 24 * 3600:
                frames = [f for f in manifest['frames'] if now - 3600 <= f['time'] <= required_end]
                if frames:
                    return dict(manifest, frames=frames, status='ready', updating=self.building,
                                forecast_until=min(int(now + self.horizon_hours * 3600), frames[-1]['time']),
                                coverage_complete=frames[-1]['time'] >= now + self.horizon_hours * 3600,
                                horizon_hours=self.horizon_hours)
            return dict(status='loading' if self.building else 'unavailable', frames=[],
                        bounds=BOUNDS, source='NOAA GFS', retry_seconds=15)

    def _build(self, cycle):
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            now = self.clock()
            first = max(1, int((now - cycle.timestamp()) // 3600))
            frames = []
            # Include the current hour, the full horizon, and a final bracketing
            # hour so a request between whole hours still has future coverage.
            for hour in range(first, first + self.horizon_hours + 2):
                stamp = int((cycle + timedelta(hours=hour)).timestamp())
                name = f"{cycle:%Y%m%d%H}-{hour:03d}-{RENDER_STYLE}.png"
                path = self.directory / name
                if not self._cached_image_valid(path):
                    base = f'{HOST}/gfs.{cycle:%Y%m%d}/{cycle:%H}/atmos/gfs.t{cycle:%H}z.pgrb2.0p25.f{hour:03d}'
                    index = self.reader(base + '.idx').decode('utf-8')
                    data = self.reader(base, precipitation_range(index))
                    png = self.renderer(data, stamp)
                    if not self._valid_png(png):
                        raise ValueError('Invalid rendered forecast image')
                    temporary = path.with_suffix('.tmp')
                    temporary.write_bytes(png)
                    temporary.replace(path)
                frames.append(dict(time=stamp, url='/forecast-frame/' + name))
            manifest = dict(source='NOAA GFS', model_run=int(cycle.timestamp()),
                            fetched_at=int(self.clock()), units='mm/h',
                            resolution_km=28, bounds=BOUNDS, frames=frames)
            temporary = self.directory / (MANIFEST_NAME + '.tmp')
            temporary.write_text(json.dumps(manifest, separators=(',', ':')), encoding='utf-8')
            temporary.replace(self.directory / MANIFEST_NAME)
            with self.lock:
                self.manifest = manifest
                self.generation = cycle.strftime('%Y%m%d%H')
            # Keep recently published frames for clients already playing them.
            for path in self.directory.glob('*.png'):
                if self.clock() - path.stat().st_mtime > 2 * 86400:
                    path.unlink(missing_ok=True)
        except Exception:
            LOG.exception('Forecast preparation failed; preserving any valid cached forecast')
            with self.lock:
                self.retry_after = self.clock() + 300
        finally:
            with self.lock:
                self.building = False

    def image(self, name):
        if not re.fullmatch(r'\d{10}-\d{3}(?:-s2)?\.png', name):
            return None
        path = self.directory / name
        return path.read_bytes() if path.is_file() else None
