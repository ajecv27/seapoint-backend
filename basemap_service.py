"""Cache the public map style; tiles and fonts load directly in the map."""
import json
import threading
import time
from urllib.request import Request, urlopen

from basemap_style import style_document

_lock = threading.Lock()
_cached = None
_checked = 0


def basemap_document():
    global _cached, _checked
    with _lock:
        if _cached is not None and time.monotonic() - _checked < 21600:
            return _cached
        try:
            request = Request('https://tiles.openfreemap.org/styles/liberty', headers={
                'User-Agent': 'SeaPoint/1.0 (+https://seapoint-backend.onrender.com)',
                'Referer': 'https://seapoint-backend.onrender.com/',
            })
            with urlopen(request, timeout=15) as response:
                document = json.load(response)
            _cached = style_document(document)
            _checked = time.monotonic()
        except Exception:
            if _cached is None:
                raise
        return _cached
