"""Hourly AROME Antilles rain from public Météo-France model packages.

Images contain preceding-one-hour mean mm/h, obtained from successive cumulative
surface precipitation fields. The model ends at H+48 from its run, not 48 hours
from a request; a separate service may supply a longer-model tail.
"""
from concurrent.futures import ThreadPoolExecutor
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

from forecast_maps import ForecastMaps, rgba, sample_rates

UTC = timezone.utc
SOURCE = 'Météo-France AROME Antilles'
BOUNDS = [[10.0, -68.0], [22.9, -55.0]]
HOST = 'https://meteofrance-pnt.s3.rbx.io.cloud.ovh.net/pnt'
MANIFEST_NAME = 'manifest-arome-v1.json'
MAX_PACKAGE_BYTES = 10_000_000
MAX_RECORD_BYTES = 3_000_000
MAX_MANIFEST_BYTES = 32_768
MAX_IMAGE_BYTES = 4_000_000
LOG = logging.getLogger(__name__)


def read_package(url):
    request = Request(url, headers={'User-Agent': 'SeaPoint-AROME/1.0'})
    with urlopen(request, timeout=35) as response:
        if response.status != 200:
            raise ValueError('Unexpected AROME package response')
        data = response.read(MAX_PACKAGE_BYTES + 1)
    if not 16 <= len(data) <= MAX_PACKAGE_BYTES or data[:4] != b'GRIB':
        raise ValueError('Invalid or oversized AROME package')
    return data


def package_url(cycle, hour):
    stamp = cycle.strftime('%Y-%m-%dT%H:%M:%SZ')
    name = f'arome-om-ANTIL__0025__SP1__{hour:03d}H__{stamp}.grib2'
    return f'{HOST}/{stamp}/arome-om/ANTIL/0025/SP1/{name}'


def _validate_handle(ec, handle, cycle_epoch, hour):
    if type(cycle_epoch) is not int or cycle_epoch % 21600 or type(hour) is not int or not 0 <= hour <= 48:
        raise ValueError('Invalid AROME run or forecast hour')
    cycle = datetime.fromtimestamp(cycle_epoch, UTC)
    expected = cycle + timedelta(hours=hour)
    if (ec.codes_get(handle, 'shortName') != 'tp' or
            ec.codes_get(handle, 'units') != 'kg m**-2' or
            ec.codes_get(handle, 'typeOfLevel') != 'surface' or
            ec.codes_get(handle, 'stepType') != 'accum' or
            ec.codes_get(handle, 'startStep') != 0 or
            ec.codes_get(handle, 'endStep') != hour or
            ec.codes_get(handle, 'dataDate') != int(cycle.strftime('%Y%m%d')) or
            ec.codes_get(handle, 'dataTime') != cycle.hour * 100 or
            ec.codes_get(handle, 'validityDate') != int(expected.strftime('%Y%m%d')) or
            ec.codes_get(handle, 'validityTime') != expected.hour * 100):
        raise ValueError('Unexpected AROME precipitation field or timestamp')
    if (ec.codes_get(handle, 'gridType') != 'regular_ll' or
            (ec.codes_get(handle, 'Ni'), ec.codes_get(handle, 'Nj')) != (945, 529) or
            ec.codes_get(handle, 'iScansNegatively') != 0 or
            ec.codes_get(handle, 'jScansPositively') != 0):
        raise ValueError('Unexpected AROME grid')
    for key, expected_value in (
        ('latitudeOfFirstGridPointInDegrees', 22.9),
        ('latitudeOfLastGridPointInDegrees', 9.7),
        ('longitudeOfFirstGridPointInDegrees', 284.7),
        ('longitudeOfLastGridPointInDegrees', 308.3),
        ('iDirectionIncrementInDegrees', .025),
        ('jDirectionIncrementInDegrees', .025),
    ):
        if abs(ec.codes_get(handle, key) - expected_value) > 1e-7:
            raise ValueError('Unexpected AROME coordinates')


def extract_precipitation(package_bytes, cycle_epoch, hour):
    """Keep only a validated surface precipitation GRIB from a bounded package."""
    import eccodes as ec
    if not isinstance(package_bytes, bytes) or not 16 <= len(package_bytes) <= MAX_PACKAGE_BYTES:
        raise ValueError('Invalid AROME package size')
    # Walking GRIB2 message boundaries avoids decoding or persisting unrelated
    # fields. The selected message is still validated by ecCodes below.
    offset = 0
    while offset < len(package_bytes):
        header = package_bytes[offset:offset + 16]
        if len(header) != 16 or header[:4] != b'GRIB' or header[7] != 2:
            raise ValueError('Invalid AROME GRIB framing')
        length = int.from_bytes(header[8:16], 'big')
        if length < 20 or offset + length > len(package_bytes):
            raise ValueError('Truncated AROME GRIB message')
        message = package_bytes[offset:offset + length]
        if message[-4:] != b'7777':
            raise ValueError('Invalid AROME GRIB ending')
        handle = ec.codes_new_from_message(message)
        try:
            if ec.codes_get(handle, 'shortName') == 'tp':
                _validate_handle(ec, handle, cycle_epoch, hour)
                if len(message) > MAX_RECORD_BYTES:
                    raise ValueError('Oversized AROME precipitation record')
                return message
        finally:
            ec.codes_release(handle)
        offset += length
    raise ValueError('AROME package has no surface precipitation field')


def decode_accumulation(record, cycle_epoch, hour):
    """Return accumulated mm and a conservative full GRIB packing quantum."""
    import eccodes as ec
    if (not isinstance(record, bytes) or not 20 <= len(record) <= MAX_RECORD_BYTES or
            record[:4] != b'GRIB' or record[7] != 2 or
            int.from_bytes(record[8:16], 'big') != len(record) or record[-4:] != b'7777'):
        raise ValueError('Invalid AROME precipitation record framing')
    handle = ec.codes_new_from_message(record)
    try:
        _validate_handle(ec, handle, cycle_epoch, hour)
        values = ec.codes_get_values(handle)
        if values.size != 945 * 529:
            raise ValueError('AROME precipitation grid size differs')
        if ec.codes_get(handle, 'bitmapPresent'):
            missing = ec.codes_get(handle, 'missingValue')
            if np.any(values == missing):
                raise ValueError('AROME precipitation coverage is incomplete')
        if not np.all(np.isfinite(values)) or np.min(values) < 0 or np.max(values) > 20_000:
            raise ValueError('Invalid AROME precipitation values')
        # A constant field has no packed deviations and no quantization noise.
        quantum = (0.0 if ec.codes_get(handle, 'bitsPerValue') == 0 else
                   2.0 ** ec.codes_get(handle, 'binaryScaleFactor') *
                   10.0 ** -ec.codes_get(handle, 'decimalScaleFactor'))
        if not math.isfinite(quantum) or not 0 <= quantum <= .05:
            raise ValueError('AROME precipitation precision is insufficient')
        return values.reshape(529, 945), quantum
    finally:
        ec.codes_release(handle)


def hourly_rates(previous, current, cycle_epoch, hour):
    """Difference same-run hourly accumulations; reject resets or missing data."""
    if type(hour) is not int or not 1 <= hour <= 48:
        raise ValueError('Invalid hourly rain interval')
    a, qa = decode_accumulation(previous, cycle_epoch, hour - 1)
    b, qb = decode_accumulation(current, cycle_epoch, hour)
    increment = b - a
    # Independently packed fields can each truncate by a full packing quantum.
    # Only this bounded numerical noise can be clipped; a model reset fails.
    if np.min(increment) < -(qa + qb + 1e-9):
        raise ValueError('AROME cumulative precipitation decreased')
    return np.maximum(increment, 0)


def render_hour(previous, current, cycle_epoch, hour):
    values = hourly_rates(previous, current, cycle_epoch, hour)
    south, west = BOUNDS[0]
    north, east = BOUNDS[1]
    top = math.asinh(math.tan(math.radians(north)))
    bottom = math.asinh(math.tan(math.radians(south)))
    latitudes = np.degrees(np.arctan(np.sinh(np.linspace(top, bottom, 640))))
    longitudes = np.linspace(west % 360, east % 360, 640)
    x = (longitudes - 284.7) / .025
    y = (22.9 - latitudes) / .025
    # Bounds lie entirely inside this regional grid. Do not wrap longitudes at
    # a regional edge or paint missing coverage as zero rain.
    if min(x) < -1e-7 or max(x) > 944 + 1e-7 or min(y) < -1e-7 or max(y) > 528 + 1e-7:
        raise ValueError('Requested image lies outside AROME coverage')
    rates = sample_rates(values, np.clip(x, 0, 944), np.clip(y, 0, 528))
    output = BytesIO()
    Image.fromarray(rgba(rates)).save(output, format='PNG')
    return output.getvalue()


class AromeMaps:
    def __init__(self, directory=None, reader=None, renderer=None, clock=None):
        self.directory = Path(directory or os.environ.get('SEAPOINT_AROME_CACHE', Path(__file__).with_name('arome-cache')))
        self.reader = reader or read_package
        self.renderer = renderer or render_hour
        self.clock = clock or time.time
        self.lock = threading.Lock()
        self.building = False
        self.retry_after = 0
        self.manifest = None
        self.generation = None
        self._restore()

    _valid_png = staticmethod(ForecastMaps._valid_png)
    _cached_image_valid = ForecastMaps._cached_image_valid

    @staticmethod
    def _image_name(cycle, hour):
        return f'arome-{cycle:%Y%m%d%H}-{hour:03d}-v1.png'

    def _restore(self):
        path = self.directory / MANIFEST_NAME
        try:
            if path.is_symlink() or not path.is_file():
                return
            with path.open('rb') as cached:
                raw = cached.read(MAX_MANIFEST_BYTES + 1)
            if len(raw) > MAX_MANIFEST_BYTES:
                return
            manifest = json.loads(raw)
            if (not isinstance(manifest, dict) or
                    set(manifest) != {'source', 'provider', 'model_run', 'fetched_at', 'units', 'resolution_km', 'bounds', 'period_seconds', 'value_semantics', 'forecast_from_run_hours', 'frames'} or
                    manifest['source'] != SOURCE or manifest['provider'] != 'arome' or
                    manifest['units'] != 'mm/h' or manifest['resolution_km'] != 2.5 or
                    manifest['bounds'] != BOUNDS or manifest['period_seconds'] != 3600 or
                    manifest['value_semantics'] != 'previous_hour_mean' or manifest['forecast_from_run_hours'] != 48):
                return
            run, fetched = manifest['model_run'], manifest['fetched_at']
            now = self.clock()
            if (type(run) is not int or run % 21600 or type(fetched) is not int or
                    not 0 <= now - run < 86400 or not run <= fetched <= now):
                return
            cycle = datetime.fromtimestamp(run, UTC)
            frames = manifest['frames']
            if not isinstance(frames, list) or not 2 <= len(frames) <= 48:
                return
            previous = None
            for frame in frames:
                if not isinstance(frame, dict) or set(frame) != {'time', 'url'} or type(frame['time']) is not int:
                    return
                hour, remainder = divmod(frame['time'] - run, 3600)
                expected = '/forecast-frame/' + self._image_name(cycle, hour)
                if (remainder or not 1 <= hour <= 48 or frame.get('url') != expected or
                        previous is not None and frame['time'] - previous != 3600 or
                        not self._cached_image_valid(self.directory / expected.rsplit('/', 1)[-1])):
                    return
                previous = frame['time']
            if frames[-1]['time'] != run + 48 * 3600 or not frames[0]['time'] <= fetched <= frames[-1]['time'] or frames[-1]['time'] <= now:
                return
            self.manifest = manifest
            self.generation = cycle.strftime('%Y%m%d%H')
        except (OSError, ValueError, TypeError, OverflowError, RecursionError):
            return

    def snapshot(self):
        now = self.clock()
        cycle = datetime.fromtimestamp(now - 5 * 3600, UTC)
        cycle = cycle.replace(hour=cycle.hour // 6 * 6, minute=0, second=0, microsecond=0)
        generation = cycle.strftime('%Y%m%d%H')
        with self.lock:
            manifest = self.manifest
            if (self.generation != generation or not manifest) and not self.building and now >= self.retry_after:
                self.building = True
                threading.Thread(target=self._build, args=(cycle,), daemon=True).start()
            if manifest and 0 <= now - manifest['model_run'] < 86400:
                frames = [f for f in manifest['frames'] if f['time'] >= now - 3600]
                if frames and frames[-1]['time'] > now:
                    until = min(int(now + 48 * 3600), frames[-1]['time'])
                    return dict(manifest, frames=frames, status='ready', updating=self.building,
                                forecast_until=until, coverage_complete=until >= now + 48 * 3600,
                                horizon_hours=48)
            return dict(status='loading' if self.building else 'unavailable', frames=[], source=SOURCE,
                        provider='arome', bounds=BOUNDS, units='mm/h', resolution_km=2.5, retry_seconds=15)

    def _record(self, cycle, hour):
        path = self.directory / f'arome-{cycle:%Y%m%d%H}-{hour:03d}.grib2'
        epoch = int(cycle.timestamp())
        try:
            if path.is_symlink() or path.stat().st_size > MAX_RECORD_BYTES:
                raise ValueError('Unsafe AROME record cache')
            record = path.read_bytes()
            decode_accumulation(record, epoch, hour)
            return record
        except Exception:
            # A bounded local record is optional. ecCodes raises several
            # library-specific decode errors; any such corruption must fetch
            # the source again rather than poison future refresh attempts.
            pass
        package = self.reader(package_url(cycle, hour))
        record = extract_precipitation(package, epoch, hour)
        decode_accumulation(record, epoch, hour)
        temporary = path.with_suffix('.tmp')
        temporary.write_bytes(record)
        temporary.replace(path)
        return record

    def _build(self, cycle):
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            now = self.clock()
            first = max(1, int((now - cycle.timestamp()) // 3600))
            if first >= 48:
                raise ValueError('AROME run has no remaining forecast')
            missing = [hour for hour in range(first, 49)
                       if not self._cached_image_valid(self.directory / self._image_name(cycle, hour))]
            needed = sorted({h for hour in missing for h in (hour - 1, hour)})
            with ThreadPoolExecutor(max_workers=3) as pool:
                records = dict(zip(needed, pool.map(lambda h: self._record(cycle, h), needed)))
            frames = []
            epoch = int(cycle.timestamp())
            for hour in range(first, 49):
                name = self._image_name(cycle, hour)
                path = self.directory / name
                if hour in missing:
                    png = self.renderer(records[hour - 1], records[hour], epoch, hour)
                    if not self._valid_png(png):
                        raise ValueError('Invalid rendered AROME image')
                    stage = path.with_suffix('.tmp')
                    stage.write_bytes(png)
                    stage.replace(path)
                frames.append({'time': epoch + hour * 3600, 'url': '/forecast-frame/' + name})
            manifest = dict(source=SOURCE, provider='arome', model_run=epoch, fetched_at=int(self.clock()),
                            units='mm/h', resolution_km=2.5, bounds=BOUNDS, period_seconds=3600,
                            value_semantics='previous_hour_mean', forecast_from_run_hours=48, frames=frames)
            temporary = self.directory / (MANIFEST_NAME + '.tmp')
            temporary.write_text(json.dumps(manifest, separators=(',', ':')), encoding='utf-8')
            temporary.replace(self.directory / MANIFEST_NAME)
            with self.lock:
                self.manifest = manifest
                self.generation = cycle.strftime('%Y%m%d%H')
            for pattern in ('arome-*.png', 'arome-*.grib2'):
                for path in self.directory.glob(pattern):
                    if self.clock() - path.stat().st_mtime > 2 * 86400:
                        path.unlink(missing_ok=True)
        except Exception:
            LOG.exception('AROME preparation failed; preserving any valid previous forecast')
            with self.lock:
                self.retry_after = self.clock() + 300
        finally:
            with self.lock:
                self.building = False

    def image(self, name):
        if not isinstance(name, str) or not re.fullmatch(r'arome-\d{10}-\d{3}-v1\.png', name):
            return None
        path = self.directory / name
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_IMAGE_BYTES:
                return None
            return path.read_bytes()
        except OSError:
            return None
