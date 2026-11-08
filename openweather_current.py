"""One Call 4.0 current conditions; key and upstream quota stay server-side."""
import json
import math
import os
from pathlib import Path
import sqlite3
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class WeatherUnavailable(Exception):
    pass


class CurrentWeather:
    TTL = 900

    def __init__(self, key=None, database=None, daily_limit=900, fetch=None, clock=None):
        self.key = key if key is not None else os.environ.get('OPENWEATHER_API_KEY', '')
        self.database = str(database or os.environ.get(
            'OPENWEATHER_CACHE_DB', Path(__file__).with_name('openweather-cache.sqlite3')))
        self.daily_limit = min(900, max(0, int(daily_limit)))
        self.fetch = fetch or self._fetch
        self.clock = clock or time.time
        self.lock = threading.Lock()

    def _fetch(self, latitude, longitude):
        query = urlencode(dict(lat=latitude, lon=longitude, units='metric', appid=self.key))
        request = Request('https://api.openweathermap.org/data/4.0/onecall/current?' + query,
                          headers={'User-Agent': 'SeaPoint/1.0'})
        with urlopen(request, timeout=12) as response:
            return json.load(response)

    @staticmethod
    def _number(value, low, high):
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and low <= value <= high)

    def get(self, latitude, longitude):
        try:
            latitude, longitude = float(latitude), float(longitude)
        except (ValueError, TypeError):
            raise ValueError('Invalid coordinates') from None
        if not (self._number(latitude, -90, 90) and self._number(longitude, -180, 180)):
            raise ValueError('Invalid coordinates')
        if not self.key:
            raise WeatherUnavailable('OpenWeather is not configured')
        # Keep locations distinct; no silent snapping to a different bay.
        location = f'{latitude:.5f},{longitude:.5f}'
        with self.lock, sqlite3.connect(self.database, timeout=20) as db:
            db.execute('CREATE TABLE IF NOT EXISTS cache (location TEXT PRIMARY KEY, saved REAL, payload TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS budget (day INTEGER PRIMARY KEY, calls INTEGER)')
            db.execute('CREATE TABLE IF NOT EXISTS cooldown (id INTEGER PRIMARY KEY, until REAL)')
            db.commit()
            # Serialize quota reservation across worker processes sharing this database.
            db.execute('BEGIN IMMEDIATE')
            now = self.clock()
            cached = db.execute('SELECT saved, payload FROM cache WHERE location=?', (location,)).fetchone()
            if cached and 0 <= now - cached[0] < self.TTL:
                return json.loads(cached[1])
            cooldown = db.execute('SELECT until FROM cooldown WHERE id=1').fetchone()
            if cooldown and now < cooldown[0]:
                raise WeatherUnavailable('OpenWeather temporarily unavailable')
            day = int(now // 86400)
            used = db.execute('SELECT calls FROM budget WHERE day=?', (day,)).fetchone()
            if used and used[0] >= self.daily_limit or self.daily_limit == 0:
                raise WeatherUnavailable('OpenWeather daily budget reached')
            db.execute('INSERT INTO budget VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET calls=calls+1', (day,))
            db.execute('DELETE FROM budget WHERE day < ?', (day - 2,))
            db.execute('DELETE FROM cache WHERE saved < ?', (now - 86400,))
            db.commit()  # Count failed upstream attempts too.
            try:
                payload = self.fetch(latitude, longitude)
                rows = payload.get('data') if isinstance(payload, dict) else None
                row = rows[0] if isinstance(rows, list) and rows else None
                if not isinstance(row, dict) or not self._number(row.get('dt'), now - 7200, now + 300):
                    raise ValueError('Missing or old current conditions')
                # Validate every displayed value; never persist the upstream URL or key.
                limits = {'temp': (-100, 70), 'feels_like': (-150, 100), 'humidity': (0, 100)}
                current = {k: row[k] for k, bounds in limits.items()
                           if self._number(row.get(k), *bounds)}
                if 'temp' not in current:
                    raise ValueError('Missing current temperature')
                weather = row.get('weather')
                if isinstance(weather, list) and weather and isinstance(weather[0], dict):
                    description = weather[0].get('description')
                    if isinstance(description, str):
                        current['description'] = description[:160]
                result = dict(source='OpenWeather', latitude=latitude, longitude=longitude,
                              dt=row['dt'], fetched_at=int(now), current=current)
            except Exception as error:
                delay = 3600 if isinstance(error, HTTPError) and error.code in (401, 403, 429) else 300
                db.execute('INSERT OR REPLACE INTO cooldown VALUES (1, ?)', (now + delay,))
                db.commit()
                # Upstream exceptions can include the key in their URL. Never expose them.
                raise WeatherUnavailable('OpenWeather temporarily unavailable') from None
            db.execute('INSERT OR REPLACE INTO cache VALUES (?, ?, ?)',
                       (location, now, json.dumps(result)))
            db.commit()
            return result
