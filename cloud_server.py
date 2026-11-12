import json
import os
import re
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from html import escape, unescape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from threading import Lock
from time import time as unix_time
from urllib.parse import parse_qs, quote, unquote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from pypdf import PdfReader
from forecast_runtime import ForecastRuntime
from official_alerts import OfficialAlertService, parse_marine_locations, parse_marine_cancellations
from radar_view import radar_page
from basemap_service import basemap_document

FORECAST_MAPS = ForecastRuntime()


SOURCE = "https://www.antiguamet.com/Daily_FCast.html"
MARINE_STATUS = "https://www.antiguamet.com/Marine.html"
RAINVIEWER_API = "https://api.rainviewer.com/public/weather-maps.json"
WORLDTIDES_API = "https://www.worldtides.info/api/v3"

MARINE_BULLETINS = {
    "High Surf Advisory":
        "https://www.antiguamet.com/Antigua_Met_files/HighSurfADVISORY.pdf",
    "High Surf Warning":
        "https://www.antiguamet.com/Antigua_Met_files/HighSurfWARNING.pdf",
    "Small Craft Advisory":
        "https://www.antiguamet.com/Antigua_Met_files/SmallCraftADVISORY.pdf",
    "Small Craft Warning":
        "https://www.antiguamet.com/Antigua_Met_files/SmallCraftWARNING.pdf",
}

OPENWEATHER_API_KEY = os.environ.get(
    "OPENWEATHER_API_KEY",
    "",
).strip()

WORLDTIDES_API_KEY = os.environ.get(
    "WORLDTIDES_API_KEY",
    "",
).strip()

ANTIGUA_TIME = ZoneInfo("America/Antigua")

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

TIDE_CACHE = {}
TIDE_CACHE_LOCK = Lock()
TIDE_CACHE_TTL_SECONDS = 3600


def fetch(url, timeout=20):
    request = Request(
        url,
        headers={"User-Agent": "SeaPoint/0.1"},
    )

    with urlopen(
        request,
        timeout=timeout,
    ) as response:
        return response.read()


def normalize_text(text):
    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def pdf_to_text(data):
    reader = PdfReader(
        BytesIO(data)
    )

    parts = []

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            parts.append(page_text)

    return "\n".join(parts)


def get_current_marine_links():
    try:
        page = fetch(
            MARINE_STATUS
        ).decode(
            "utf-8",
            errors="ignore",
        )

        anchors = re.findall(
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            page,
            re.IGNORECASE | re.DOTALL,
        )

        found = {}

        for href, label_html in anchors:
            label = normalize_text(
                unescape(
                    re.sub(
                        r"<[^>]+>",
                        " ",
                        label_html,
                    )
                )
            )

            for name in MARINE_BULLETINS:
                if name.lower() in label.lower():
                    found[name] = urljoin(
                        MARINE_STATUS,
                        href,
                    )

        return found or dict(
            MARINE_BULLETINS
        )

    except Exception:
        return dict(
            MARINE_BULLETINS
        )


def parse_issue_datetime(text):
    pattern = re.compile(
        r"(\d{1,2}:\d{2}\s*(?:am|pm))\s+"
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
        r"(\d{1,2})\s+"
        r"([A-Za-z]+),?\s+"
        r"(\d{4})",
        re.IGNORECASE,
    )

    match = pattern.search(text)

    if not match:
        return None, None

    value = (
        f"{match.group(1).upper()} "
        f"{match.group(2)} "
        f"{match.group(3)} "
        f"{match.group(4)}"
    )

    for date_format in (
        "%I:%M %p %d %B %Y",
        "%I:%M %p %d %b %Y",
    ):
        try:
            result = datetime.strptime(
                value,
                date_format,
            )

            return (
                result.replace(
                    tzinfo=ANTIGUA_TIME,
                ),
                match,
            )

        except ValueError:
            pass

    return None, None


def bulletin_applies_to_antigua(
    text,
    issue_match,
):
    if issue_match is None:
        return False

    after_issue = text[
        issue_match.end():
    ]

    end_match = re.search(
        r"Locations\s+to\s+be\s+affected:|Timing:",
        after_issue,
        re.IGNORECASE,
    )

    if end_match:
        after_issue = after_issue[
            :end_match.start()
        ]

    return re.search(
        r"\bAntigua\b",
        after_issue,
        re.IGNORECASE,
    ) is not None


def parse_descriptor(
    descriptor,
    issue_datetime,
):
    descriptor = normalize_text(
        descriptor
    )

    lower = descriptor.lower()
    target_date = None

    full_date = re.search(
        r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        descriptor,
        re.IGNORECASE,
    )

    if full_date:
        day, month, year = (
            full_date.groups()
        )

        for date_format in (
            "%d %B %Y",
            "%d %b %Y",
        ):
            try:
                target_date = datetime.strptime(
                    f"{day} {month} {year}",
                    date_format,
                ).date()
                break

            except ValueError:
                pass

    if target_date is None:
        weekday_match = re.search(
            r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
            descriptor,
            re.IGNORECASE,
        )

        if weekday_match:
            weekday = WEEKDAYS[
                weekday_match.group(1).lower()
            ]

            days_ahead = (
                weekday
                - issue_datetime.weekday()
            ) % 7

            target_date = (
                issue_datetime.date()
                + timedelta(
                    days=days_ahead,
                )
            )

    if target_date is None:
        if "tomorrow" in lower:
            target_date = (
                issue_datetime.date()
                + timedelta(days=1)
            )

        elif any(
            term in lower
            for term in (
                "today",
                "tonight",
                "this evening",
                "this afternoon",
            )
        ):
            target_date = (
                issue_datetime.date()
            )

        else:
            return None

    explicit_time = re.search(
        r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
        descriptor,
        re.IGNORECASE,
    )

    if explicit_time:
        hour = int(
            explicit_time.group(1)
        )
        minute = int(
            explicit_time.group(2)
            or 0
        )

        meridiem = (
            explicit_time
            .group(3)
            .lower()
        )

        if (
            meridiem == "pm"
            and hour != 12
        ):
            hour += 12

        elif (
            meridiem == "am"
            and hour == 12
        ):
            hour = 0

        target_time = time(
            hour,
            minute,
        )

    elif "mid-morning" in lower:
        target_time = time(
            10,
            0,
        )

    elif "dawn" in lower:
        target_time = time(
            6,
            0,
        )

    elif (
        "morning" in lower
        or "noon" in lower
    ):
        target_time = time(
            12,
            0,
        )

    elif "afternoon" in lower:
        target_time = time(
            18,
            0,
        )

    elif "evening" in lower:
        target_time = time(
            21,
            0,
        )

    else:
        target_time = time(
            23,
            59,
        )

    return datetime.combine(
        target_date,
        target_time,
        tzinfo=ANTIGUA_TIME,
    )


def get_timing_window(
    text,
    issue_datetime,
    applies_to_antigua,
    target_island="Antigua",
):
    timing_match = re.search(
        r"Timing:\s*(.*?)(?=Synopsis:)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if not timing_match:
        return None, None

    timing_text = normalize_text(
        timing_match.group(1)
    )

    lower = timing_text.lower()

    island_index = lower.find(
        target_island.lower()
    )

    if island_index >= 0:
        until_index = lower.rfind(
            "until",
            0,
            island_index,
        )

        if until_index < 0:
            return None, None

        descriptor_end = island_index

        for_index = lower.find(
            " for ",
            until_index,
            island_index,
        )

        if for_index >= 0:
            descriptor_end = for_index

        expiry_descriptor = (
            timing_text[
                until_index
                + len("until"):
                descriptor_end
            ]
        )

        from_index = lower.rfind(
            "from",
            0,
            until_index,
        )

        start_descriptor = None

        if from_index >= 0:
            between = lower[
                from_index:
                until_index
            ]

            if " for " not in between:
                start_descriptor = (
                    timing_text[
                        from_index
                        + len("from"):
                        until_index
                    ]
                )

    else:
        if (
            not applies_to_antigua
            or " for " in lower
        ):
            return None, None

        until_match = re.search(
            r"\buntil\s+(.+?)(?:[.;]|$)",
            timing_text,
            re.IGNORECASE,
        )

        if not until_match:
            return None, None

        expiry_descriptor = (
            until_match.group(1)
        )

        from_match = re.search(
            r"\bfrom\s+(.+?)\s+until\b",
            timing_text,
            re.IGNORECASE,
        )

        start_descriptor = (
            from_match.group(1)
            if from_match
            else None
        )

    expiry = parse_descriptor(
        expiry_descriptor,
        issue_datetime,
    )

    start = (
        parse_descriptor(
            start_descriptor,
            issue_datetime,
        )
        if start_descriptor
        else issue_datetime
    )

    return start, expiry


def check_alert(item):
    name, url = item
    try:
        text = normalize_text(pdf_to_text(fetch(url)))
        issued, issue_match = parse_issue_datetime(text)
        if issued is None or issue_match is None:
            return name, {"active": False, "reason": "issue_date_unreadable", "url": url}
        locations = parse_marine_locations(text, issue_match.end())
        if not locations:
            return name, {"active": False, "reason": "local_scope_unverified", "url": url}
        cancelled = parse_marine_cancellations(text, issue_match.end(), name)
        header = re.split(r"Timing\s*:|Synopsis\s*:", text[issue_match.end():], maxsplit=1, flags=re.I)[0]
        ambiguous_cancel = False
        for sentence in re.split(r"[.;]|\bWHILE\b", header, flags=re.I):
            marker = re.search(r"\b(?:CANCELLED|CANCELED|DISCONTINUED|LIFTED)\b", sentence, re.I)
            if marker and not cancelled and not re.search(r"\b(?:NO|NOT|IF|UNLESS|WHEN|WILL|WOULD)\b", sentence[:marker.start()], re.I):
                ambiguous_cancel = True
        now = datetime.now(ANTIGUA_TIME)
        checks = {}
        for island in ("Antigua", "Barbuda"):
            result = {"active": False, "url": url}
            if island in cancelled:
                result["reason"] = "cancelled"
            elif island not in locations:
                result["reason"] = "not_for_antigua_or_barbuda"
            elif ambiguous_cancel:
                result["reason"] = "cancellation_status_unverified"
            else:
                start, expiry = get_timing_window(text, issued, True, target_island=island)
                if start is None or expiry is None:
                    result["reason"] = "timing_unreadable"
                elif start > expiry:
                    result["reason"] = "invalid_timing"
                elif issued > now:
                    result["reason"] = "future_issue"
                else:
                    result.update(starts=start.isoformat(), expires=expiry.isoformat())
                    if now < start:
                        result["reason"] = "not_started"
                    elif now >= expiry:
                        result["reason"] = "expired"
                    else:
                        result.update(active=True, reason="active")
            checks[island] = result
        return name, {"active": any(c["active"] for c in checks.values()),
                      "reason": "area_checks", "area_checks": checks, "url": url}
    except Exception:
        return name, {"active": False, "reason": "bulletin_error", "url": url}


def get_rainviewer_frames():
    data = json.loads(
        fetch(
            RAINVIEWER_API
        ).decode(
            "utf-8"
        )
    )

    radar = (
        data.get("radar")
        or {}
    )

    frames = (
        radar.get("past")
        or []
    )

    return {
        "host": data.get(
            "host",
            "https://tilecache.rainviewer.com",
        ),
        "frames": frames,
    }


def get_tides(
    latitude,
    longitude,
):
    if not WORLDTIDES_API_KEY:
        raise RuntimeError(
            "WorldTides API key is not configured"
        )

    if not -90 <= latitude <= 90:
        raise ValueError(
            "Latitude must be between -90 and 90"
        )

    if not -180 <= longitude <= 180:
        raise ValueError(
            "Longitude must be between -180 and 180"
        )

    cache_key = (
        round(latitude, 4),
        round(longitude, 4),
    )

    now = unix_time()

    with TIDE_CACHE_LOCK:
        cached = TIDE_CACHE.get(
            cache_key
        )

        if (
            cached
            and now - cached["saved_at"]
            < TIDE_CACHE_TTL_SECONDS
        ):
            return cached["payload"]

    params = urlencode({
        "date": "today",
        "days": 7,
        "lat": f"{latitude:.6f}",
        "lon": f"{longitude:.6f}",
        "datum": "CD",
        "key": WORLDTIDES_API_KEY,
    })

    url = (
        f"{WORLDTIDES_API}"
        f"?extremes&localtime&{params}"
    )

    data = json.loads(
        fetch(
            url,
            timeout=20,
        ).decode(
            "utf-8"
        )
    )

    status = data.get(
        "status",
        200,
    )

    if status != 200:
        raise RuntimeError(
            data.get(
                "error",
                "WorldTides request failed",
            )
        )

    extremes = data.get(
        "extremes"
    ) or []

    extremes = sorted(
        extremes,
        key=lambda event: event.get(
            "dt",
            0,
        ),
    )

    payload = {
        "ok": True,
        "requestLat": data.get(
            "requestLat",
            latitude,
        ),
        "requestLon": data.get(
            "requestLon",
            longitude,
        ),
        "responseLat": data.get(
            "responseLat"
        ),
        "responseLon": data.get(
            "responseLon"
        ),
        "timezone": data.get(
            "timezone"
        ),
        "datum": data.get(
            "responseDatum"
        ),
        "station": data.get(
            "station"
        ),
        "atlas": data.get(
            "atlas"
        ),
        "callCount": data.get(
            "callCount"
        ),
        "copyright": data.get(
            "copyright",
            "",
        ),
        "extremes": extremes,
    }

    with TIDE_CACHE_LOCK:
        TIDE_CACHE[cache_key] = {
            "saved_at": now,
            "payload": payload,
        }

    return payload


def _legacy_radar_page(
    latitude,
    longitude,
    location_name,
):
    safe_name_html = escape(
        location_name
    )

    safe_name_js = json.dumps(
        location_name
    )

    openweather_available = json.dumps(
        bool(
            OPENWEATHER_API_KEY
        )
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SeaPoint Rain Radar</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
* {{ box-sizing: border-box; }}
html, body {{
    width: 100%;
    height: 100%;
    margin: 0;
    font-family: Arial, sans-serif;
    background: #eef5f8;
}}
body {{
    display: flex;
    flex-direction: column;
    overflow: hidden;
}}
.topbar {{
    z-index: 1000;
    background: rgba(255,255,255,0.97);
    padding: 10px 12px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.14);
}}
.title-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}}
.title {{
    font-size: 17px;
    font-weight: 700;
    color: #123c50;
}}
.live-badge {{
    border-radius: 999px;
    background: #e6f4f8;
    color: #087d9d;
    padding: 5px 9px;
    font-size: 12px;
    font-weight: 700;
}}
.legend-wrap {{ margin-top: 8px; }}
.legend-labels {{
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: #5d6f78;
    margin-bottom: 3px;
}}
.legend-bar {{
    height: 8px;
    border-radius: 999px;
    background: linear-gradient(
        90deg,
        #68d8ff 0%,
        #2ca25f 32%,
        #ffe066 58%,
        #ff922b 76%,
        #d6336c 100%
    );
}}
.map-wrap {{
    position: relative;
    flex: 1 1 auto;
    min-height: 280px;
}}
#map {{
    width: 100%;
    height: 100%;
}}
.loading {{
    position: absolute;
    z-index: 800;
    left: 50%;
    top: 16px;
    transform: translateX(-50%);
    background: rgba(255,255,255,0.95);
    border-radius: 999px;
    padding: 7px 12px;
    font-size: 12px;
    color: #123c50;
    box-shadow: 0 1px 5px rgba(0,0,0,0.15);
    white-space: nowrap;
}}
.bottom-panel {{
    z-index: 1000;
    background: rgba(255,255,255,0.98);
    padding: 10px 12px 12px;
    box-shadow: 0 -1px 6px rgba(0,0,0,0.14);
}}
.control-row {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
.play-button {{
    width: 46px;
    height: 46px;
    flex: 0 0 46px;
    border: 0;
    border-radius: 50%;
    background: #087d9d;
    color: white;
    font-size: 18px;
    cursor: pointer;
}}
.time-block {{
    min-width: 0;
    flex: 1;
}}
.frame-time {{
    font-weight: 700;
    color: #123c50;
    font-size: 14px;
}}
.frame-status {{
    margin-top: 2px;
    color: #6a7c85;
    font-size: 11px;
}}
#timeline {{
    width: 100%;
    margin-top: 9px;
    accent-color: #087d9d;
}}
.timeline-labels {{
    display: flex;
    justify-content: space-between;
    color: #6a7c85;
    font-size: 10px;
    margin-top: -1px;
}}
.source {{
    margin-top: 7px;
    color: #71828a;
    font-size: 10px;
    line-height: 1.3;
}}
.source a {{ color: #087d9d; }}
@media (max-width: 520px) {{
    .title {{ font-size: 15px; }}
}}
</style>
</head>
<body>
<div class="topbar">
    <div class="title-row">
        <div class="title">Rain Radar — {safe_name_html}</div>
        <div class="live-badge" id="nowBadge">RADAR</div>
    </div>
    <div class="legend-wrap">
        <div class="legend-labels">
            <span>Light rain</span>
            <span>Moderate</span>
            <span>Heavy rain</span>
        </div>
        <div class="legend-bar"></div>
    </div>
</div>

<div class="map-wrap">
    <div id="map"></div>
    <div class="loading" id="loadingMessage">Loading radar frames…</div>
</div>

<div class="bottom-panel">
    <div class="control-row">
        <button
            id="playPause"
            class="play-button"
            type="button"
            aria-label="Pause radar animation"
        >❚❚</button>
        <div class="time-block">
            <div id="frameTime" class="frame-time">Loading…</div>
            <div id="frameStatus" class="frame-status">Preparing radar animation</div>
        </div>
    </div>
    <input
        id="timeline"
        type="range"
        min="0"
        max="0"
        value="0"
        step="1"
        aria-label="Radar timeline"
    >
    <div class="timeline-labels">
        <span>Past</span>
        <span>Now</span>
    </div>
    <div class="source">
        Development radar:
        <a href="https://www.rainviewer.com/" target="_blank" rel="noopener">RainViewer</a>.
        Production source will be replaced before commercial release.
    </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const locationName = {safe_name_js};

const map = L.map('map', {{ zoomControl: true }}).setView(
    [{latitude}, {longitude}],
    7
);

L.tileLayer(
    'https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
    {{
        maxZoom: 18,
        attribution: '&copy; OpenStreetMap contributors'
    }}
).addTo(map);

L.marker([{latitude}, {longitude}])
    .addTo(map)
    .bindPopup(locationName);

let frames = [];
let layers = [];
let radarHost = '';
let frameIndex = 0;
let playing = true;
let timer = null;
let refreshToken = 0;
let currentFramesKey = '';

const radarOpacity = 0.72;

const playPause = document.getElementById('playPause');
const timeline = document.getElementById('timeline');
const frameTime = document.getElementById('frameTime');
const frameStatus = document.getElementById('frameStatus');
const loadingMessage = document.getElementById('loadingMessage');
const nowBadge = document.getElementById('nowBadge');

function notifyApp(message) {{
    if (
        window.SeaPointRadar &&
        window.SeaPointRadar.postMessage
    ) {{
        window.SeaPointRadar.postMessage(message);
    }}
}}

function formatAntiguaTime(unixSeconds) {{
    return new Intl.DateTimeFormat('en-US', {{
        timeZone: 'America/Antigua',
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
    }}).format(
        new Date(unixSeconds * 1000)
    );
}}

function makeLayer(frame, opacity, onLoad) {{
    const layer = L.tileLayer(
        radarHost +
        frame.path +
        '/256/{{z}}/{{x}}/{{y}}/2/1_1.png',
        {{
            opacity: opacity,
            maxNativeZoom: 7,
            maxZoom: 18,
            attribution: 'Radar: RainViewer'
        }}
    );

    if (onLoad) {{
        layer.once('load', onLoad);
    }}

    layer.addTo(map);

    const element = layer.getContainer();

    if (element) {{
        element.style.transition =
            'opacity 420ms linear';
    }}

    return layer;
}}

function showFrame(index, animate = true) {{
    if (
        index < 0 ||
        index >= frames.length ||
        !layers[index]
    ) {{
        return;
    }}

    const previous = layers[frameIndex];
    const next = layers[index];

    next.bringToFront();

    if (
        animate &&
        previous &&
        previous !== next
    ) {{
        next.setOpacity(0);

        requestAnimationFrame(() =>
            requestAnimationFrame(() => {{
                next.setOpacity(radarOpacity);
                previous.setOpacity(0);
            }})
        );

    }} else {{
        layers.forEach((layer, n) => {{
            if (layer) {{
                layer.setOpacity(
                    n === index ? radarOpacity : 0
                );
            }}
        }});
    }}

    frameIndex = index;
    timeline.value = String(index);

    frameTime.textContent =
        formatAntiguaTime(frames[index].time) +
        ' Antigua time';

    const latest =
        index === frames.length - 1;

    frameStatus.textContent = latest
        ? 'Latest observed radar frame (not a forecast)'
        : 'Earlier observed radar frame';

    nowBadge.textContent =
        latest ? 'LATEST' : 'PAST';
}}

function stopTimer() {{
    if (timer) {{
        clearTimeout(timer);
    }}

    timer = null;
}}

function playbackStep() {{
    if (
        !playing ||
        frames.length < 2
    ) {{
        return;
    }}

    timer = setTimeout(() => {{
        const next =
            (frameIndex + 1) % frames.length;

        showFrame(next, true);
        playbackStep();

    }}, 1100);
}}

function startPlayback(holdLatest = false) {{
    stopTimer();

    playing = true;

    playPause.textContent = '❚❚';

    playPause.setAttribute(
        'aria-label',
        'Pause radar animation'
    );

    if (holdLatest) {{
        timer = setTimeout(
            playbackStep,
            2500
        );
    }} else {{
        playbackStep();
    }}
}}

function pausePlayback() {{
    playing = false;
    stopTimer();

    playPause.textContent = '▶';

    playPause.setAttribute(
        'aria-label',
        'Play radar animation'
    );
}}

playPause.addEventListener('click', () => {{
    if (playing) {{
        pausePlayback();
    }} else {{
        startPlayback();
    }}
}});

timeline.addEventListener('input', () => {{
    pausePlayback();

    showFrame(
        Number(timeline.value),
        false
    );
}});

async function loadRadarFrames() {{
    const token = ++refreshToken;

    try {{
        const response = await fetch(
            '/radar-frames',
            {{cache: 'no-store'}}
        );

        if (!response.ok) {{
            throw new Error(
                'Radar data unavailable'
            );
        }}

        const data = await response.json();

        const upcoming = (data.frames || [])
            .filter(
                f =>
                    Number.isFinite(f.time) &&
                    f.path
            )
            .sort(
                (a, b) => a.time - b.time
            )
            .slice(-6);

        if (!upcoming.length) {{
            throw new Error(
                'No recent observations'
            );
        }}

        const key = upcoming
            .map(f => f.time)
            .join(',');

        if (key === currentFramesKey) {{
            return;
        }}

        if (token !== refreshToken) {{
            return;
        }}

        currentFramesKey = key;

        radarHost = data.host ||
            'https://tilecache.rainviewer.com';

        stopTimer();

        const oldLayers = layers;

        layers = Array(
            upcoming.length
        ).fill(null);

        frames = upcoming;

        const latestIndex =
            frames.length - 1;

        frameIndex = latestIndex;
        timeline.max = String(latestIndex);

        let settled = false;

        const latestReady = () => {{
            if (
                settled ||
                token !== refreshToken
            ) {{
                return;
            }}

            settled = true;

            oldLayers.forEach(layer => {{
                if (layer) {{
                    map.removeLayer(layer);
                }}
            }});

            showFrame(
                latestIndex,
                false
            );

            loadingMessage.style.display =
                'none';

            notifyApp('ready');

            let remaining = latestIndex;
            let started = false;

            const begin = () => {{
                if (
                    started ||
                    token !== refreshToken
                ) {{
                    return;
                }}

                started = true;

                if (playing) {{
                    startPlayback(true);
                }}
            }};

            if (!remaining) {{
                begin();
            }}

            for (
                let i = 0;
                i < latestIndex;
                i++
            ) {{
                layers[i] = makeLayer(
                    frames[i],
                    0,
                    () => {{
                        remaining--;

                        if (remaining === 0) {{
                            begin();
                        }}
                    }}
                );
            }}

            setTimeout(begin, 8000);
        }};

        layers[latestIndex] = makeLayer(
            frames[latestIndex],
            radarOpacity,
            latestReady
        );

        setTimeout(
            latestReady,
            12000
        );

    }} catch (error) {{
        if (!layers.some(Boolean)) {{
            loadingMessage.textContent =
                'Recent radar temporarily unavailable';

            frameStatus.textContent =
                'Showing current precipitation if available';

            if ({openweather_available}) {{
                L.tileLayer(
                    '/radar-tile/{{z}}/{{x}}/{{y}}.png',
                    {{
                        opacity: 0.72,
                        maxZoom: 18,
                        attribution: '© OpenWeather'
                    }}
                ).addTo(map);

                loadingMessage.style.display =
                    'none';

                notifyApp('ready');

            }} else {{
                notifyApp('error');
            }}

            pausePlayback();

            playPause.disabled = true;
            timeline.disabled = true;
        }}
    }}
}}

loadRadarFrames();

setInterval(
    loadRadarFrames,
    300000
);
</script>
</body>
</html>
"""


def fetch_radar_tile(
    z,
    x,
    y,
):
    if not OPENWEATHER_API_KEY:
        raise RuntimeError(
            "OpenWeather radar API key is not configured"
        )

    url = (
        "https://tile.openweathermap.org/"
        f"map/precipitation_new/"
        f"{z}/{x}/{y}.png"
        f"?appid="
        f"{quote(OPENWEATHER_API_KEY)}"
    )

    return fetch(
        url
    )


def load_official_marine_alerts():
    links = dict(MARINE_BULLETINS)
    links.update(get_current_marine_links())
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        for name, result in executor.map(check_alert, links.items()):
            results[name] = dict(result, url=links.get(name, MARINE_BULLETINS.get(name)))
    return results


OFFICIAL_ALERTS = OfficialAlertService(marine_loader=load_official_marine_alerts)


class Handler(
    BaseHTTPRequestHandler
):

    def send_cors_headers(
        self,
    ):
        self.send_header(
            "Access-Control-Allow-Origin",
            "*",
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, HEAD, OPTIONS",
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )

    def send_json(
        self,
        data,
        status=200,
    ):
        content = json.dumps(
            data,
            indent=2,
        ).encode(
            "utf-8"
        )

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_cors_headers()

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.send_header(
            "Content-Length",
            str(len(content)),
        )

        self.end_headers()

        self.wfile.write(
            content
        )

    def send_content(
        self,
        content,
        content_type,
        status=200,
        cache_control="no-store",
    ):
        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_cors_headers()

        self.send_header(
            "Cache-Control",
            cache_control,
        )

        self.send_header(
            "Content-Length",
            str(len(content)),
        )

        self.end_headers()

        self.wfile.write(
            content
        )

    def do_HEAD(self):
        self.send_response(
            200
        )

        self.send_cors_headers()

        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(
            204
        )

        self.send_cors_headers()

        self.end_headers()

    def do_GET(self):
        parsed = urlparse(
            self.path
        )

        path = parsed.path

        query = parse_qs(
            parsed.query
        )

        if path == "/rain-look-preview":
            self.send_content(
                Path(__file__).with_name("rain-look-preview.html").read_bytes(),
                "text/html; charset=utf-8")
            return

        if path == "/rain-look-preview-v1.mp4":
            self.send_content(
                Path(__file__).with_name("rain-look-preview-v1.mp4").read_bytes(),
                "video/mp4", cache_control="public, max-age=3600, immutable")
            return

        if path == "/rain-motion.js":
            script = Path(__file__).with_name("rain_motion.js").read_bytes()
            self.send_content(script, "text/javascript; charset=utf-8",
                              cache_control="public, max-age=300")
            return

        if path == "/basemap-style":
            try:
                self.send_json(basemap_document())
            except Exception:
                self.send_json({"error": "Map style temporarily unavailable"}, 503)
            return

        if path == "/forecast-frames":
            data = FORECAST_MAPS.snapshot()
            self.send_json(data, 200 if data["status"] == "ready" else
                           202 if data["status"] == "loading" else 503)
            return

        if path.startswith("/forecast-frame/"):
            image = FORECAST_MAPS.image(path.removeprefix("/forecast-frame/"))
            if image is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(image)))
            self.send_header("Cache-Control", "public, max-age=86400, immutable")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(image)
            return

        if path in (
            "/",
            "/health",
        ):
            self.send_json({
                "status": "ok",
                "service": "SeaPoint Alerts",
                "tides": bool(
                    WORLDTIDES_API_KEY
                ),
            })

            return

        if path == "/alerts":
            try:
                data = OFFICIAL_ALERTS.snapshot()
                # Older clients also see an unavailable state instead of an
                # empty/all-clear feed when any required coverage is unknown.
                complete = data["status"] == "ready"
                self.send_json(data, 200 if complete or data["alerts"] else 503)
            except Exception:
                self.send_json({
                    "alerts": [], "links": {}, "alert_sources": {},
                    "status": "unavailable", "checked": {},
                    "error": "Official alert verification is unavailable",
                }, 503)
            return

        if path == "/tides":
            try:
                latitude = float(
                    query.get(
                        "lat",
                        [""],
                    )[0]
                )

                longitude = float(
                    query.get(
                        "lon",
                        [""],
                    )[0]
                )

                self.send_json(
                    get_tides(
                        latitude,
                        longitude,
                    )
                )

            except ValueError as error:
                self.send_json(
                    {
                        "ok": False,
                        "error":
                            str(error),
                    },
                    400,
                )

            except Exception as error:
                print(
                    f"Tides error: {error}"
                )

                self.send_json(
                    {
                        "ok": False,
                        "error":
                            "Tide data unavailable",
                    },
                    502,
                )

            return

        if path == "/radar-frames":
            try:
                self.send_json(
                    get_rainviewer_frames()
                )

            except Exception as error:
                self.send_json(
                    {
                        "host": "",
                        "frames": [],
                        "error":
                            str(error),
                    },
                    502,
                )

            return

        if path == "/radar":
            try:
                latitude = float(
                    query.get(
                        "lat",
                        ["17.12"],
                    )[0]
                )

                longitude = float(
                    query.get(
                        "lon",
                        ["-61.85"],
                    )[0]
                )

                location_name = (
                    query.get(
                        "name",
                        ["Antigua"],
                    )[0]
                )

                content = radar_page(
                    latitude,
                    longitude,
                    location_name,
                ).encode(
                    "utf-8"
                )

                self.send_content(
                    content,
                    "text/html; charset=utf-8",
                )

            except Exception as error:
                self.send_json(
                    {
                        "error":
                            str(error),
                    },
                    500,
                )

            return

        if path.startswith(
            "/radar-tile/"
        ):
            try:
                parts = (
                    path
                    .strip("/")
                    .split("/")
                )

                if len(parts) != 4:
                    self.send_error(
                        404
                    )
                    return

                z = int(
                    parts[1]
                )

                x = int(
                    parts[2]
                )

                y_text = parts[3]

                if not y_text.endswith(
                    ".png"
                ):
                    self.send_error(
                        404
                    )
                    return

                y = int(
                    y_text.removesuffix(
                        ".png"
                    )
                )

                content = fetch_radar_tile(
                    z,
                    x,
                    y,
                )

                self.send_content(
                    content,
                    "image/png",
                    cache_control=
                        "public, max-age=300",
                )

            except Exception as error:
                self.send_json(
                    {
                        "error":
                            str(error),
                    },
                    503,
                )

            return

        if path.startswith(
            "/marine-alert/"
        ):
            alert_name = unquote(
                path.removeprefix(
                    "/marine-alert/"
                )
            )

            url = MARINE_BULLETINS.get(
                alert_name
            )

            if url is None:
                self.send_error(
                    404
                )
                return

            try:
                content = fetch(
                    url
                )

                self.send_content(
                    content,
                    "application/pdf",
                )

            except Exception as error:
                self.send_json(
                    {
                        "error":
                            str(error),
                    },
                    502,
                )

            return

        if path == "/bulletin":
            try:
                content = fetch(
                    SOURCE
                )

                self.send_content(
                    content,
                    "text/html; charset=utf-8",
                )

            except Exception as error:
                self.send_json(
                    {
                        "error":
                            str(error),
                    },
                    502,
                )

            return

        self.send_error(
            404
        )


PORT = int(
    os.environ.get(
        "PORT",
        "8000",
    )
)

print(
    f"SeaPoint backend running on port {PORT}"
)

# Bind HTTP before importing providers or restoring their image caches.
server = ThreadingHTTPServer(
    (
        "0.0.0.0",
        PORT,
    ),
    Handler,
)
FORECAST_MAPS.start()
server.serve_forever()
