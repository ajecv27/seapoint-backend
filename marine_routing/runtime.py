"""Keep routing CPU work isolated from weather HTTP requests on the same host."""
from collections import OrderedDict
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import uuid

BOUNDS = (-94.0, 5.0, -55.0, 34.0)
DATASET = 'caribbean-osm-gshhg-20261114-v1'


class RoutingRuntime:
    def __init__(self, *, command=None, clock=None, startup_timeout=45,
                 route_timeout=22, memory_mb=320, cache_seconds=900):
        self.command = command or [sys.executable, '-m', 'marine_routing.worker']
        self.clock = clock or time.monotonic
        self.startup_timeout = startup_timeout
        self.route_timeout = route_timeout
        self.memory_bytes = memory_mb * 1024 * 1024
        self.cache_seconds = cache_seconds
        self._lock = threading.Lock()
        self._gate = threading.Lock()
        self._process = None
        self._messages = None
        self._ready = False
        self._starting = False
        self._closed = False
        self._retry_at = 0
        self._cache = OrderedDict()
        self._build = None

    def start(self):
        with self._lock:
            if self._closed or self._starting or self.clock() < self._retry_at:
                return
            if self._ready and self._process is not None and self._process.poll() is None:
                return
            self._starting = True
            self._ready = False
        threading.Thread(target=self._boot, name='seapoint-routing-startup', daemon=True).start()

    @staticmethod
    def _read(process, messages):
        try:
            for line in iter(lambda: process.stdout.readline(1048577), ''):
                if len(line) > 1048576:
                    break
                try:
                    data = json.loads(line)
                    if not isinstance(data, dict):
                        break
                    messages.put_nowait(data)
                except (ValueError, queue.Full):
                    break
        finally:
            try:
                messages.put_nowait({'type': 'unavailable'})
            except queue.Full:
                pass

    def _boot(self):
        process = None
        try:
            env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
                       SEAPOINT_ROUTE_TIMING='0', PYTHONUNBUFFERED='1')
            process = subprocess.Popen(self.command, cwd=Path(__file__).resolve().parents[1],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding='utf-8', bufsize=1, env=env)
            messages = queue.Queue(maxsize=4)
            with self._lock:
                closed = self._closed
                if not closed:
                    self._process, self._messages = process, messages
            if closed:
                self._retire(process)
                return
            threading.Thread(target=self._read, args=(process, messages),
                             name='seapoint-routing-protocol', daemon=True).start()
            message = messages.get(timeout=self.startup_timeout)
            if (message.get('type') != 'ready' or message.get('dataset') != DATASET or
                    not isinstance(message.get('build'), str) or process.poll() is not None):
                raise RuntimeError('Routing data unavailable')
            with self._lock:
                if self._closed or self._process is not process:
                    return
                self._build = message['build']
                self._ready = True
                self._starting = False
        except Exception:
            self._retire(process, backoff=15)

    def _retire(self, process, *, backoff=0):
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=1)
            except Exception:
                try:
                    process.kill()
                    process.wait(timeout=1)
                except Exception:
                    pass
            for stream in (process.stdin, process.stdout):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass
        with self._lock:
            if process is None or self._process is process:
                self._ready = self._starting = False
                self._process = self._messages = None
                self._retry_at = self.clock() + backoff

    def health(self):
        self.start()
        with self._lock:
            ready = self._ready and self._process is not None and self._process.poll() is None
            status = 'ready' if ready else 'loading' if self._starting else 'unavailable'
            return {'status': status, 'service': 'seapoint-marine-routing',
                    'routing_build': self._build, 'coastline_dataset': DATASET,
                    'coverage': list(BOUNDS), 'region': 'caribbean', 'depth_checked': False}

    @staticmethod
    def _point(point):
        if not isinstance(point, (tuple, list)) or len(point) != 2:
            raise ValueError('Invalid route coordinates')
        lon, lat = point
        if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in point):
            raise ValueError('Invalid route coordinates')
        if not (BOUNDS[0] <= lon <= BOUNDS[2] and BOUNDS[1] <= lat <= BOUNDS[3]):
            raise ValueError('Choose start and destination within Caribbean routing coverage')
        return (float(lon), float(lat))

    @staticmethod
    def _rss(process):
        try:
            for line in Path(f'/proc/{process.pid}/status').read_text().splitlines():
                if line.startswith('VmRSS:'):
                    return int(line.split()[1]) * 1024
        except (OSError, ValueError):
            pass
        return 0

    @staticmethod
    def _error(message, status=503, *, retryable=False):
        return status, {'status': 'error', 'error': message,
                        'retryable': retryable, 'retry_after_s': 2 if retryable else 0}

    def route(self, start, finish):
        try:
            start, finish = self._point(start), self._point(finish)
            if start == finish:
                raise ValueError('Choose two different locations')
        except ValueError as error:
            return self._error(str(error), 400)
        key = (start, finish)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None and cached[0] > self.clock():
                self._cache.move_to_end(key)
                return 200, cached[1]
        self.start()
        if not self._gate.acquire(blocking=False):
            return self._error('Routing is busy. Please try again shortly.', 429, retryable=True)
        process = None
        try:
            with self._lock:
                process, messages = self._process, self._messages
                ready = self._ready
                loading = self._starting
            if not ready or process is None or process.poll() is not None:
                return self._error('Routing is warming up. Please try again shortly.' if loading
                                   else 'Routing is temporarily unavailable. Please try again later.', retryable=loading)
            token = uuid.uuid4().hex
            process.stdin.write(json.dumps({'id': token, 'start': start, 'finish': finish}, allow_nan=False) + '\n')
            process.stdin.flush()
            deadline = self.clock() + self.route_timeout
            while self.clock() < deadline:
                try:
                    message = messages.get(timeout=min(.25, max(.01, deadline - self.clock())))
                except queue.Empty:
                    if process.poll() is not None or self._rss(process) > self.memory_bytes:
                        break
                    continue
                if message.get('type') == 'unavailable' or message.get('id') != token:
                    break
                status, body = message.get('status'), message.get('body')
                if status not in (200, 400, 503, 504) or not isinstance(body, dict):
                    break
                if status == 200:
                    if body.get('status') != 'ok' or body.get('coastline_dataset') != DATASET:
                        break
                    with self._lock:
                        self._cache[key] = (self.clock() + self.cache_seconds, body)
                        self._cache.move_to_end(key)
                        while len(self._cache) > 64:
                            self._cache.popitem(last=False)
                if status in (503, 504) or self._rss(process) > self.memory_bytes:
                    self._retire(process)
                return status, body
            self._retire(process)
            return self._error('Route calculation took too long. Try a shorter route or move the endpoints into open water.', 504)
        except (OSError, ValueError):
            self._retire(process)
            return self._error('Routing is temporarily unavailable. Please try again.')
        finally:
            self._gate.release()

    def close(self):
        with self._lock:
            self._closed = True
            self._ready = self._starting = False
            process = self._process
        self._retire(process)
