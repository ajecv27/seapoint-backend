"""Per-installation tide caching and bounded WorldTides requests."""
from concurrent.futures import Future, TimeoutError
from contextlib import contextmanager
from datetime import datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

VERSION = 'tide-cache-v2'
ZONE = ZoneInfo('America/Antigua')


class TideUnavailable(Exception):
    def __init__(self, reason, retry_at, status=503):
        self.reason, self.retry_at, self.status = reason, int(retry_at), status
        super().__init__('New tide predictions unavailable')

    def payload(self):
        return {'ok': False, 'error': str(self), 'reason': self.reason,
                'retry_at': self.retry_at, 'service_version': VERSION}


def coverage(now):
    start = datetime.fromtimestamp(now, ZONE).replace(hour=0, minute=0, second=0, microsecond=0)
    return int(start.timestamp()), int((start + timedelta(days=7)).timestamp()), start.date().isoformat()


class TideService:
    def __init__(self, fetcher, *, directory, provider_key='', clock=None, daily_limit=50):
        self.fetcher = fetcher
        self.directory = Path(directory)
        self.clock = clock or time.time
        # A changed key starts a new account-state namespace; the key is never stored.
        self.account = hashlib.sha256(provider_key.encode()).hexdigest()[:20]
        self.daily_limit = max(1, int(daily_limit))
        self._lock = threading.Lock()
        self._provider_gate = threading.Lock()
        self._inflight = {}

    @contextmanager
    def _db(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = self.directory/'state.sqlite3'
        db = sqlite3.connect(path, timeout=5)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        db.execute('CREATE TABLE IF NOT EXISTS cache (client TEXT, location TEXT, payload TEXT, '
                   'expires INTEGER, saved INTEGER, PRIMARY KEY(client,location))')
        db.execute('CREATE TABLE IF NOT EXISTS state (name TEXT PRIMARY KEY, value TEXT)')
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _read(db, name, default):
        row = db.execute('SELECT value FROM state WHERE name=?', (name,)).fetchone()
        return json.loads(row[0]) if row else default

    @staticmethod
    def _write(db, name, value):
        db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (name,json.dumps(value)))

    @staticmethod
    def _identity(token, latitude, longitude):
        if not isinstance(token, str) or not re.fullmatch(r'[a-f0-9]{32}', token):
            raise TideUnavailable('client_update_required', 0, 428)
        if (isinstance(latitude, bool) or isinstance(longitude, bool) or
                not all(isinstance(x, (int,float)) and math.isfinite(x) for x in (latitude,longitude)) or
                not -90 <= latitude <= 90 or not -180 <= longitude <= 180):
            raise ValueError('Invalid tide coordinates')
        lat, lon = round(latitude,4), round(longitude,4)
        return hashlib.sha256(token.encode()).hexdigest(), f'{lat:.4f},{lon:.4f}', lat, lon

    def status(self):
        now = self.clock()
        with self._lock, self._db() as db:
            pause = self._read(db, 'pause:'+self.account, {})
        paused = pause.get('until',0) > now
        return {'service_version': VERSION, 'status': 'paused' if paused else 'ready',
                'reason': pause.get('reason') if paused else None,
                'retry_at': pause.get('until',0) if paused else 0}

    def _cached(self, client, location, now):
        with self._lock, self._db() as db:
            # Keep only predictions that still cover future dates, with a fixed size bound.
            db.execute('DELETE FROM cache WHERE expires<=?', (int(now),))
            row = db.execute('SELECT payload FROM cache WHERE client=? AND location=?', (client,location)).fetchone()
            return json.loads(row[0]) if row else None

    def _reserve(self, now, key, retry_paused=False):
        start, end, date = coverage(now)
        with self._lock, self._db() as db:
            pause = self._read(db, 'pause:'+self.account, {})
            if pause.get('until',0) > now:
                if not retry_paused or pause.get('probe_after',0) > now:
                    raise TideUnavailable(pause['reason'], pause['until'])
                pause['probe_after'] = int(now+60)
                self._write(db, 'pause:'+self.account, pause)
            failure = self._read(db, 'failure:'+key, {})
            if failure.get('until',0) > now:
                raise TideUnavailable('upstream_unavailable', failure['until'])
            usage = self._read(db, 'usage:'+self.account, {})
            count = usage.get('count',0) if usage.get('date') == date else 0
            if count >= self.daily_limit:
                raise TideUnavailable('daily_limit', start+86400, 429)
            self._write(db, 'usage:'+self.account, {'date':date,'count':count+1})
        return start, end, date

    def _record_failure(self, error, key, now):
        text = ''
        status = 0
        if isinstance(error, HTTPError):
            status = error.code
            try:
                data = json.loads(error.read(8192))
                text = str(data.get('error','')).lower()
            except (ValueError, OSError, AttributeError):
                pass
        else:
            text = str(error).lower()
            status = getattr(error,'status',0)
        exhausted = status == 402 or ('credit' in text and any(
            marker in text for marker in ('insufficient','exhaust','not enough','no remaining','no credit','deplet','balance')))
        reason = 'credits_exhausted' if exhausted else 'credentials_unavailable' if status in (401,403) else 'upstream_unavailable'
        until = int(now + (6*3600 if exhausted or status in (401,403) else 15*60))
        with self._lock, self._db() as db:
            if exhausted or status in (401,403):
                self._write(db, 'pause:'+self.account, {'reason':reason,'until':until,'probe_after':int(now+60)})
            else:
                self._write(db, 'failure:'+key, {'until':until})
        # No upstream body, API URL, token or key is returned to the phone/logs.
        return TideUnavailable(reason, until)

    def get(self, token, latitude, longitude, *, retry_paused=False):
        client, location, lat, lon = self._identity(token,latitude,longitude)
        now = self.clock()
        cached = self._cached(client,location,now)
        start, end, _ = coverage(now)
        if cached and cached['coverage_start'] <= start and cached['coverage_end'] >= end:
            return cached
        key = hashlib.sha256((client+location).encode()).hexdigest()
        with self._lock:
            future = self._inflight.get(key)
            leader = future is None
            if leader:
                future = self._inflight[key] = Future()
        if not leader:
            try:
                return future.result(timeout=25)
            except TimeoutError:
                raise TideUnavailable('busy', now+60)
        try:
            if not self._provider_gate.acquire(timeout=.25):
                raise TideUnavailable('busy', now+60)
            try:
                latest = self._cached(client,location,self.clock())
                current_start, current_end, _ = coverage(self.clock())
                if latest and latest['coverage_start'] <= current_start and latest['coverage_end'] >= current_end:
                    future.set_result(latest)
                    return latest
                # Recheck after the gate: another request may have paused this account.
                start, end, date = self._reserve(self.clock(), key, retry_paused)
                try:
                    data = self.fetcher(lat,lon,date)
                    if not isinstance(data,dict) or data.get('status') != 200:
                        error = RuntimeError(str(data.get('error','Invalid tide response')) if isinstance(data,dict) else 'Invalid tide response')
                        error.status = data.get('status',0) if isinstance(data,dict) else 0
                        raise error
                    events = data.get('extremes')
                    if not isinstance(events,list):
                        raise ValueError('Invalid tide response')
                    for event in events:
                        if (not isinstance(event,dict) or str(event.get('type','')).lower() not in ('high','low') or
                                not isinstance(event.get('dt'),(int,float)) or not math.isfinite(event['dt']) or
                                not isinstance(event.get('height'),(int,float)) or not math.isfinite(event['height'])):
                            raise ValueError('Invalid tide event')
                    payload = {name:data.get(name) for name in ('requestLat','requestLon','responseLat','responseLon',
                               'timezone','station','atlas','callCount','copyright')}
                    payload.update(ok=True, requestLat=lat, requestLon=lon,
                                   datum=data.get('responseDatum'), extremes=sorted(events,key=lambda e:e['dt']),
                                   coverage_start=start, coverage_end=end, fetched_at=int(self.clock()),
                                   service_version=VERSION)
                except Exception as error:
                    raise self._record_failure(error,key,self.clock()) from None
                with self._lock, self._db() as db:
                    db.execute('DELETE FROM state WHERE name=?', ('pause:'+self.account,))
                    db.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?,?,?)',
                               (client,location,json.dumps(payload),end,int(self.clock())))
                    db.execute('DELETE FROM cache WHERE rowid IN (SELECT rowid FROM cache ORDER BY saved DESC LIMIT -1 OFFSET 512)')
                future.set_result(payload)
                return payload
            finally:
                self._provider_gate.release()
        except TideUnavailable as error:
            if cached:
                partial = dict(cached, availability='cached_partial', reason=error.reason, retry_at=error.retry_at)
                future.set_result(partial)
                return partial
            future.set_exception(error)
            raise
        except Exception:
            error = TideUnavailable('upstream_unavailable',self.clock()+900)
            future.set_exception(error)
            raise error from None
        finally:
            with self._lock:
                self._inflight.pop(key,None)
