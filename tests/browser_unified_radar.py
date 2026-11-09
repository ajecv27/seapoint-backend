"""Unified observation-to-48-hour playback checks with test-only fixtures.

Only this browser test intercepts weather providers. No fixture weather is
returned by the application or deployed to real users.
"""
import base64
import os
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get('SEAPOINT_TEST_URL', 'http://127.0.0.1:8000').rstrip('/')
BASE_ORIGIN = urlsplit(BASE_URL).netloc
PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
asset_cache = {}
errors = []


def external_asset(route):
    """Fetch through the managed CA trust while keeping TLS verification on."""
    url = route.request.url
    try:
        own_origin = urlsplit(url).netloc == BASE_ORIGIN
        if own_origin or url not in asset_cache:
            request = Request(url, headers={
                'User-Agent': route.request.headers.get('user-agent', 'SeaPoint/1.0'),
                'Referer': BASE_URL + '/',
            })
            try:
                response = urlopen(request, timeout=25)
            except HTTPError as error:
                response = error
            with response:
                result = (response.status, response.read(),
                          response.headers.get('Content-Type', 'application/octet-stream'))
            if not own_origin:
                asset_cache[url] = result
        else:
            result = asset_cache[url]
        status, body, content_type = result
        route.fulfill(status=status, body=body, content_type=content_type,
                      headers={'Access-Control-Allow-Origin': '*'})
    except Exception:
        route.abort()


def open_fixture(browser, radar=True, future=True, forecast_gap=False):
    page = browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=3)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route(re.compile(r'https://.*'), external_asset)
    now = time.time()
    latest = int(now // 600 * 600)
    observed = [{'time': latest - (7 - i) * 600, 'path': '/fixture/' + str(i)}
                for i in range(8)]
    first_hour = int(now // 3600 * 3600) + (3600 if forecast_gap else 0)
    # Include the current model-hour bracket plus enough hourly frames for the
    # full 48h range even when a wall-clock hour changes while the test loads.
    forecast = [{'time': first_hour + i * 3600,
                 'url': '/fixture-forecast/' + str(i) + '.png'} for i in range(51)]
    if radar:
        page.route('**/radar-frames', lambda route: route.fulfill(json={
            'host': 'https://radar-fixture.test', 'frames': observed,
        }))
    else:
        page.route('**/radar-frames', lambda route: route.fulfill(
            status=503, json={'error': 'test-only provider outage'}))
    if future:
        page.route('**/forecast-frames', lambda route: route.fulfill(json={
            'status': 'ready', 'source': 'NOAA GFS', 'units': 'mm/h',
            'model_run': int(now - 6 * 3600), 'fetched_at': int(now),
            'resolution_km': 28, 'bounds': [[10, -68], [23, -55]],
            'frames': forecast,
        }))
    else:
        page.route('**/forecast-frames', lambda route: route.fulfill(
            status=503, json={'status': 'unavailable', 'frames': []}))
    page.route('https://radar-fixture.test/**', lambda route: route.fulfill(
        body=PNG, content_type='image/png'))
    page.route('**/fixture-forecast/*.png', lambda route: route.fulfill(
        body=PNG, content_type='image/png'))
    page.route('**/basemap-style', lambda route: route.fulfill(json={
        'version': 8, 'sources': {},
        'layers': [{'id': 'test-background', 'type': 'background',
                    'paint': {'background-color': '#183d63'}}],
    }))
    page.route('https://server.arcgisonline.com/**', lambda route: route.fulfill(
        body=PNG, content_type='image/png'))
    page.goto(BASE_URL + '/radar?lat=17.12&lon=-61.8&name=Unified%20test',
              wait_until='domcontentloaded', timeout=60000)
    page.wait_for_selector('.leaflet-container', timeout=30000)
    return page, observed, forecast


def scrub(page, value):
    page.locator('#timeline').evaluate(
        '(element,value)=>{element.value=String(value);'
        'element.dispatchEvent(new Event("input",{bubbles:true}));}', value)


def playing_at(page, value):
    # Changing the starting point avoids waiting through the entire two-day
    # forecast. All subsequent movement/holds use the real animation loop.
    page.evaluate('(value)=>{setPlaying(false);firstPlay=false;position=value;render();setPlaying(true);}', value)


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'),
        headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
    page, obs, future = open_fixture(browser)
    latest = obs[-1]['time']
    page.wait_for_function(
        "active.some(f=>f.kind==='observed') && active.some(f=>f.kind==='forecast') && "
        "!document.getElementById('timeline').disabled && mapStatus==='OBSERVED'", timeout=60000)
    assert page.locator('#observed').count() == 0
    assert page.locator('#forecast').count() == 0
    assert page.locator('.mode-switch').count() == 0
    assert page.evaluate('Math.abs(position-observed.at(-1).time)<=1')
    assert page.evaluate("active.filter(f=>f.kind==='forecast').every(f=>f.time>observed.at(-1).time)")
    assert float(page.locator('#timeline').get_attribute('min')) == obs[0]['time']
    end = float(page.locator('#timeline').get_attribute('max'))
    assert end >= time.time() + 48 * 3600 - 40, end - time.time()
    print('PASS single Radar timeline starts at latest observation and extends 48h', flush=True)
    page.locator('#play').click()
    page.wait_for_function('position<=observed[0].time+150', timeout=3000)
    assert page.evaluate('mapStatus') == 'OBSERVED'
    page.locator('#play').click()
    print('PASS first Play begins the complete observation-to-forecast loop', flush=True)

    scrub(page, latest - 600)
    page.wait_for_function("mapStatus==='OBSERVED'")
    assert 'observed' in page.locator('#detail').inner_text().lower()
    scrub(page, time.time() + 24 * 3600)
    page.wait_for_function("mapStatus==='FORECAST'", timeout=30000)
    assert 'forecast' in page.locator('#detail').inner_text().lower()
    assert page.evaluate('playing===false')
    assert page.evaluate("""() => {
        let markerPane, forecastPane;
        map.eachLayer(layer=>{
            if(layer instanceof L.CircleMarker)markerPane=layer.getPane();
            if(layer instanceof L.ImageOverlay)forecastPane=layer.getPane();
        });
        return markerPane && forecastPane &&
            Number(getComputedStyle(markerPane).zIndex)>Number(getComputedStyle(forecastPane).zIndex);
    }""")
    print('PASS past/future scrubbing changes source label and preserves marker visibility', flush=True)

    # The first second after observations must already use forecast images,
    # rather than crossfading a measured radar image with model precipitation.
    scrub(page, latest + 1)
    page.wait_for_function("mapStatus==='FORECAST'")
    assert page.evaluate("Array.from(visibleLayers).every(layer=>layer instanceof L.ImageOverlay)")
    assert page.evaluate("Array.from(loaded.values()).filter(layer=>layer instanceof L.TileLayer).every(layer=>layer.options.opacity===0)")
    print('PASS source boundary never blends radar tiles with forecast images', flush=True)

    page.locator('#jump-latest').click()
    page.wait_for_function("mapStatus==='OBSERVED'")
    assert abs(page.evaluate('position') - latest) <= 1
    playing_at(page, latest - 60)
    page.wait_for_function(
        "Math.abs(position-observed.at(-1).time)<=1 && holdUntil>performance.now()", timeout=5000)
    page.wait_for_timeout(700)
    assert abs(page.evaluate('position') - latest) <= 1
    page.wait_for_function('position>observed.at(-1).time+1', timeout=4000)
    assert page.evaluate('mapStatus') == 'FORECAST'
    assert page.evaluate('position') > latest
    page.locator('#play').click()
    frozen = page.evaluate('position')
    page.wait_for_timeout(350)
    assert page.evaluate('position') == frozen
    print('PASS latest radar holds, continues into forecasts without wrapping, and pause freezes', flush=True)

    playing_at(page, end - 60)
    page.wait_for_function(
        "position>=Number(document.getElementById('timeline').max)-1 && holdUntil>performance.now()",
        timeout=3000)
    page.wait_for_timeout(600)
    assert abs(page.evaluate('position') - end) <= 1
    page.wait_for_function('position<=active[0].time+120', timeout=3500)
    page.evaluate('setPlaying(false)')
    print('PASS only the final forecast endpoint loops to the oldest observation', flush=True)

    page.evaluate('window.seapointUseNativeInfo()')
    assert page.locator('#info-toggle').is_hidden()
    page.evaluate('window.seapointToggleInfo()')
    assert page.locator('#source-panel').is_visible()
    page.evaluate('window.seapointToggleInfo()')
    assert page.locator('#source-panel').is_hidden()
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    print('PASS compact layout and native-header info bridge remain usable', flush=True)
    page.close()

    radar_only, obs, _ = open_fixture(browser, future=False)
    radar_only.wait_for_function("mapStatus==='OBSERVED' && !document.getElementById('play').disabled", timeout=45000)
    assert float(radar_only.locator('#timeline').get_attribute('max')) == obs[-1]['time']
    assert radar_only.evaluate("active.every(f=>f.kind==='observed')")
    radar_only.locator('#play').click()
    radar_only.wait_for_timeout(700)
    assert radar_only.evaluate('mapStatus') == 'OBSERVED'
    radar_only.close()
    print('PASS radar-only outage fallback makes no future-data claim', flush=True)

    future_only, _, _ = open_fixture(browser, radar=False)
    future_only.wait_for_function("mapStatus==='FORECAST' && !document.getElementById('play').disabled", timeout=60000)
    assert future_only.evaluate("active.every(f=>f.kind==='forecast')")
    assert float(future_only.locator('#timeline').get_attribute('max')) >= time.time() + 48 * 3600 - 40
    future_only.close()
    print('PASS forecast-only outage fallback retains 48h playback', flush=True)

    # Deliberately omit the current model-hour bracket in this test response.
    # The resulting coverage gap must be labelled unavailable, not interpolated
    # across different providers or displayed as clear weather.
    gap, gap_obs, _ = open_fixture(browser, forecast_gap=True)
    gap.wait_for_function(
        "active.some(f=>f.kind==='forecast') && mapStatus==='OBSERVED' && "
        "!document.getElementById('timeline').disabled", timeout=60000)
    assert gap.evaluate('predictionFrames[0].time>observationEnd()+60')
    scrub(gap, gap_obs[-1]['time'] + 60)
    gap.wait_for_function("mapStatus==='GAP'")
    assert gap.locator('#notice').is_visible()
    assert 'No frame' in gap.locator('#notice').inner_text()
    assert gap.evaluate('visibleLayers.size===0')
    assert gap.evaluate("Array.from(loaded.values()).every(layer=>layer.options.opacity===0)")
    available_future = gap.evaluate('predictionFrames[0].time+1800')
    scrub(gap, available_future)
    gap.wait_for_function("mapStatus==='FORECAST'")
    assert gap.evaluate("Array.from(visibleLayers).every(layer=>layer instanceof L.ImageOverlay)")
    gap.close()
    print('PASS missing model-hour gap is explicit and later forecast scrubbing recovers', flush=True)

    missing, _, _ = open_fixture(browser, radar=False, future=False)
    missing.wait_for_function("mapStatus==='UNAVAILABLE'", timeout=30000)
    assert missing.locator('#play').is_disabled()
    assert missing.locator('#timeline').is_disabled()
    assert missing.locator('#clock').inner_text() == 'No frames available'
    missing.close()
    assert not errors, errors
    print('PASS combined outage shows unavailable, not dry; no JavaScript errors', flush=True)
    browser.close()
