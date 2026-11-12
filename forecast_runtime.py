"""Start forecast providers without holding up the HTTP shell or weather routes.

Only the initializer imports numerical/GRIB providers and restores their image
caches. The runtime publishes no forecast until that initialization completes;
the providers continue to own image generation, freshness and coverage checks.
"""
import logging
import threading
import time

LOG = logging.getLogger(__name__)


def _regional_service():
    from forecast_service import RegionalForecastMaps
    return RegionalForecastMaps()


class ForecastRuntime:
    def __init__(self, factory=None, clock=None, retry_seconds=15):
        self.factory = factory or _regional_service
        self.clock = clock or time.monotonic
        self.retry_seconds = retry_seconds
        self._lock = threading.Lock()
        self._service = None
        self._starting = False
        self._retry_at = 0

    def start(self):
        """Begin at most one initializer, returning without waiting for it."""
        with self._lock:
            if self._service is not None or self._starting or self.clock() < self._retry_at:
                return False
            self._starting = True
            worker = threading.Thread(target=self._initialize,
                                      name='seapoint-forecast-startup', daemon=True)
            try:
                worker.start()
            except Exception:
                self._starting = False
                self._retry_at = self.clock() + self.retry_seconds
                LOG.exception('Could not start forecast initialization')
                return False
            return True

    def _initialize(self):
        try:
            service = self.factory()
            # Restored images become available and missing forecasts begin their
            # existing background builds before this service is published.
            service.snapshot()
        except Exception:
            LOG.exception('Forecast initialization failed; HTTP service remains available')
            with self._lock:
                self._starting = False
                self._retry_at = self.clock() + self.retry_seconds
            return
        with self._lock:
            self._service = service
            self._starting = False

    def _placeholder(self, loading):
        return {
            'status': 'loading' if loading else 'unavailable',
            'frames': [], 'bounds': [[10.0, -68.0], [23.0, -55.0]],
            'source': 'Météo-France AROME Antilles / NOAA GFS',
            'units': 'mm/h', 'coverage_complete': False, 'horizon_hours': 48,
            'retry_seconds': self.retry_seconds, 'updating': loading,
        }

    def snapshot(self):
        self.start()
        with self._lock:
            service, loading = self._service, self._starting
        if service is None:
            return self._placeholder(loading)
        try:
            return service.snapshot()
        except Exception:
            LOG.exception('Forecast snapshot unavailable')
            return self._placeholder(False)

    def image(self, name):
        self.start()
        with self._lock:
            service = self._service
        if service is None:
            return None
        try:
            return service.image(name)
        except Exception:
            LOG.exception('Forecast image unavailable')
            return None
