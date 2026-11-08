"""Regional forecast images from public NOAA GFS; no weather API key needed."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
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
    """Consistent forecast scale, mm/hour. Transparent means less than 0.1."""
    levels = np.array([0.1, 0.5, 2.5, 7.5, 15, 30, 60])
    colors = np.array([[100, 210, 255], [45, 140, 245], [106, 78, 211],
                       [215, 55, 143], [255, 158, 70], [255, 230, 65], [255, 255, 190]])
    pixels = np.zeros((*rates.shape, 4), dtype=np.uint8)
    safe_rates = np.where(np.isfinite(rates), rates, 0)
    for channel in range(3):
        pixels[..., channel] = np.interp(safe_rates, levels, colors[:, channel]).astype(np.uint8)
    pixels[..., 3] = np.where(np.isfinite(rates) & (rates >= 0.1), 200, 0)
    return pixels


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
        y0, x0 = np.floor(y).astype(int), np.floor(x).astype(int)
        fy, fx = (y - y0)[:, None], (x - x0)[None, :]
        # Interpolation only smooths the display; it does not add model detail.
        a = values[y0[:, None], x0[None, :]]
        b = values[y0[:, None], (x0 + 1)[None, :]]
        c = values[(y0 + 1)[:, None], x0[None, :]]
        d = values[(y0 + 1)[:, None], (x0 + 1)[None, :]]
        rates = ((a * (1 - fx) + b * fx) * (1 - fy) +
                 (c * (1 - fx) + d * fx) * fy) * 3600
        output = BytesIO()
        Image.fromarray(rgba(rates)).save(output, format='PNG')
        return output.getvalue()
    finally:
        ec.codes_release(handle)


class ForecastMaps:
    def __init__(self, directory=None, reader=None, renderer=None, clock=None):
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

    def snapshot(self):
        now = self.clock()
        # Allow publication time, then select a six-hourly model run.
        cycle = datetime.fromtimestamp(now - 5 * 3600, UTC)
        cycle = cycle.replace(hour=cycle.hour // 6 * 6, minute=0, second=0, microsecond=0)
        generation = cycle.strftime('%Y%m%d%H')
        with self.lock:
            manifest = self.manifest
            refresh = (self.generation != generation or not manifest or
                       manifest['frames'][-1]['time'] < now + 23 * 3600)
            if refresh and not self.building and now >= self.retry_after:
                self.building = True
                threading.Thread(target=self._build, args=(cycle,), daemon=True).start()
            if manifest and now - manifest['model_run'] < 24 * 3600:
                frames = [f for f in manifest['frames'] if now - 3600 <= f['time'] <= now + 24 * 3600]
                if frames:
                    return dict(manifest, frames=frames, status='ready', updating=self.building)
            return dict(status='loading' if self.building else 'unavailable', frames=[],
                        bounds=BOUNDS, source='NOAA GFS', retry_seconds=15)

    def _build(self, cycle):
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            now = self.clock()
            first = max(1, int((now - cycle.timestamp()) // 3600))
            frames = []
            for hour in range(first, first + 26):
                stamp = int((cycle + timedelta(hours=hour)).timestamp())
                name = f"{cycle:%Y%m%d%H}-{hour:03d}.png"
                path = self.directory / name
                if not path.exists():
                    base = f'{HOST}/gfs.{cycle:%Y%m%d}/{cycle:%H}/atmos/gfs.t{cycle:%H}z.pgrb2.0p25.f{hour:03d}'
                    index = self.reader(base + '.idx').decode('utf-8')
                    data = self.reader(base, precipitation_range(index))
                    png = self.renderer(data, stamp)
                    temporary = path.with_suffix('.tmp')
                    temporary.write_bytes(png)
                    temporary.replace(path)
                frames.append(dict(time=stamp, url='/forecast-frame/' + name))
            manifest = dict(source='NOAA GFS', model_run=int(cycle.timestamp()),
                            fetched_at=int(self.clock()), units='mm/h',
                            resolution_km=28, bounds=BOUNDS, frames=frames)
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
        if not re.fullmatch(r'\d{10}-\d{3}\.png', name):
            return None
        path = self.directory / name
        return path.read_bytes() if path.is_file() else None
