"""Playback speed and map-interaction checks with test-only weather fixtures.

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


def check_running(page, before, action):
    action()
    page.wait_for_timeout(350)
    assert page.evaluate('playing') is True
    assert page.evaluate('position') > before


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'),
        headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
    page, obs, future = open_fixture(browser)
    page.wait_for_function(
        "radarFrames.length===8 && predictionFrames.length>=48 && "
        "!document.getElementById('play').disabled && mapStatus==='OBSERVED'", timeout=60000)

    # Check actual elapsed playback, not the application's configured constant.
    page.locator('#play').click()
    before = page.evaluate('position')
    started = time.monotonic()
    page.wait_for_timeout(3000)
    after = page.evaluate('position')
    observed_rate = (after - before) / (time.monotonic() - started)
    assert 335 <= observed_rate <= 385, observed_rate
    print('PASS modest radar speed increase:', round(observed_rate), 'timeline seconds/second', flush=True)
    page.locator('#play').click()
    frozen = page.evaluate('position')
    page.wait_for_timeout(300)
    assert page.evaluate('position') == frozen

    scrub(page, time.time() + 6 * 3600)
    page.locator('#play').click()
    before = page.evaluate('position')
    started = time.monotonic()
    page.wait_for_timeout(1800)
    after = page.evaluate('position')
    forecast_rate = (after - before) / (time.monotonic() - started)
    assert 1990 <= forecast_rate <= 2310, forecast_rate
    print('PASS modest forecast speed increase:', round(forecast_rate), 'timeline seconds/second', flush=True)

    center = page.evaluate('[map.getCenter().lat,map.getCenter().lng]')
    before = page.evaluate('position')
    page.mouse.move(165, 330)
    page.mouse.down()
    page.mouse.move(245, 405, steps=12)
    page.mouse.up()
    page.wait_for_timeout(400)
    assert page.evaluate('playing') is True
    assert page.evaluate('position') > before
    assert page.evaluate('[map.getCenter().lat,map.getCenter().lng]') != center
    print('PASS dragging the map keeps timelapse running', flush=True)

    for control in ['#zoom-in', '#zoom-out']:
        zoom = page.evaluate('map.getZoom()')
        before = page.evaluate('position')
        check_running(page, before, lambda control=control: page.locator(control).click())
        assert page.evaluate('map.getZoom()') != zoom
    print('PASS zoom in/out keeps timelapse running', flush=True)

    before = page.evaluate('position')
    check_running(page, before, lambda: page.locator('#recenter').click())
    page.wait_for_function("map.latLngToContainerPoint([config.lat,config.lon]).distanceTo(map.getSize().divideBy(2))<2", timeout=5000)
    print('PASS recenter keeps timelapse running', flush=True)

    target = page.locator('#info-toggle').bounding_box()
    icon = page.locator('#info-toggle .icon').bounding_box()
    assert target and target['width'] >= 44 and target['height'] >= 44, target
    assert icon and icon['width'] <= 18 and icon['height'] <= 18, icon
    visible_circle = page.evaluate("""() => {
        const style=getComputedStyle(document.getElementById('info-toggle'),'::before');
        const border=style.boxSizing==='border-box'?0:parseFloat(style.borderLeftWidth)+parseFloat(style.borderRightWidth);
        return [parseFloat(style.width)+border,parseFloat(style.height)+border];
    }""")
    assert visible_circle == [34, 34], visible_circle
    print('PASS compact info icon keeps a 44px touch target', flush=True)

    page.locator('#play').click()
    frozen = page.evaluate('position')
    page.wait_for_timeout(300)
    assert page.evaluate('position') == frozen
    assert not errors, errors
    print('PASS explicit pause still works; no JavaScript errors', flush=True)
    browser.close()
