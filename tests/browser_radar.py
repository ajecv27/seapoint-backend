"""Mobile browser smoke checks against a running SeaPoint backend."""
import json
import os
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright


base_url = os.environ.get('SEAPOINT_TEST_URL', 'http://127.0.0.1:8000').rstrip('/')
base_origin = urlsplit(base_url).netloc
errors = []
asset_cache = {}


def external(route):
    """Use the managed environment's CA trust without disabling TLS checks."""
    try:
        url = route.request.url
        own_origin = urlsplit(url).netloc == base_origin
        # Never freeze a loading forecast or an outage response in the test cache.
        if own_origin or url not in asset_cache:
            request = Request(url, headers={
                'User-Agent': route.request.headers.get('user-agent', 'SeaPoint/1.0'),
                'Referer': base_url + '/',
            })
            try:
                response = urlopen(request, timeout=25)
            except HTTPError as error:
                # An HTTP failure is still a real response the player must handle.
                response = error
            with response:
                result = (response.status, response.read(),
                          response.headers.get('Content-Type', 'application/octet-stream'))
            if not own_origin:
                asset_cache[url] = result
        else:
            result = asset_cache[url]
        status, body, content_type = result
        route.fulfill(status=status, body=body, content_type=content_type)
    except Exception:
        route.abort()


def attach(page):
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route(re.compile(r'https://.*'), external)


def open_map(page):
    page.goto(base_url + '/radar?lat=17.12&lon=-61.8&name=Antigua',
              wait_until='domcontentloaded', timeout=60000)
    page.wait_for_selector('.leaflet-container', timeout=30000)


def check_layout(page):
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    viewport = page.viewport_size
    map_box = page.locator('#map').bounding_box()
    player_box = page.locator('#player').bounding_box()
    legend_box = page.locator('#legend').bounding_box()
    assert map_box and map_box['width'] >= viewport['width'] - 2, map_box
    assert map_box['height'] >= viewport['height'] - 2, map_box
    assert player_box and player_box['x'] >= 0 and player_box['y'] >= 0, player_box
    assert player_box['x'] + player_box['width'] <= viewport['width'] + 1, player_box
    assert player_box['y'] + player_box['height'] <= viewport['height'] + 1, player_box
    assert player_box['y'] > viewport['height'] / 2, player_box
    assert legend_box and legend_box['y'] + legend_box['height'] < player_box['y'], legend_box
    for selector in ['#play', '#recenter', '#info-toggle', '#observed', '#forecast']:
        box = page.locator(selector).bounding_box()
        assert box and box['width'] >= 44 and box['height'] >= 44, (selector, box)
    timeline_box = page.locator('#timeline').bounding_box()
    assert timeline_box and timeline_box['height'] >= 28, timeline_box


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'),
        headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1)
    attach(page)
    open_map(page)
    assert page.locator('#all').count() == 0
    assert 'Past + forecast' not in page.locator('body').inner_text()
    assert page.locator('#observed').get_attribute('aria-pressed') == 'true'
    assert page.locator('#forecast').get_attribute('aria-pressed') == 'false'
    assert page.locator('#source-panel').is_hidden()
    page.locator('#info-toggle').click()
    assert page.locator('#source-panel').is_visible()
    page.locator('#info-toggle').click()
    assert page.locator('#source-panel').is_hidden()
    page.locator('#recenter').click()
    check_layout(page)

    page.locator('#forecast').click()
    assert page.locator('#forecast').get_attribute('aria-pressed') == 'true'
    assert page.locator('#observed').get_attribute('aria-pressed') == 'false'
    page.wait_for_function("!document.getElementById('timeline').disabled", timeout=120000)
    assert page.locator('#mode').inner_text() == 'FORECAST'
    assert page.evaluate("""() => {
        let markerPane, imagePane;
        map.eachLayer(layer => {
            if (layer instanceof L.CircleMarker) markerPane=layer.getPane();
            if (layer instanceof L.ImageOverlay) imagePane=layer.getPane();
        });
        return markerPane && imagePane &&
            Number(getComputedStyle(markerPane).zIndex)>Number(getComputedStyle(imagePane).zIndex);
    }""")
    print('STATE', json.dumps(page.evaluate(
        "({frames:active.length,first:active[0].time,last:active.at(-1).time,"
        "mode:document.getElementById('mode').textContent,"
        "detail:document.getElementById('detail').textContent})")))

    page.locator('#play').click()
    before = page.locator('#timeline').input_value()
    page.wait_for_timeout(1800)
    after = page.locator('#timeline').input_value()
    assert int(after) > int(before), (before, after)
    page.locator('#play').click()
    paused = page.locator('#timeline').input_value()
    page.wait_for_timeout(300)
    assert page.locator('#timeline').input_value() == paused
    page.locator('#timeline').evaluate(
        "e=>{e.value=e.max;e.dispatchEvent(new Event('input',{bubbles:true}));}")
    assert page.locator('#mode').inner_text() == 'FORECAST'
    assert page.locator('#timeline').input_value() == page.locator('#timeline').get_attribute('max')
    check_layout(page)
    if os.environ.get('RADAR_SCREENSHOT'):
        page.screenshot(path=os.environ['RADAR_SCREENSHOT'], full_page=True)
    page.set_viewport_size({'width': 844, 'height': 390})
    page.wait_for_timeout(300)
    check_layout(page)
    print('PASS two modes, source details, full-map portrait/landscape layout, playback, pause, scrubbing')

    # Default Radar remains explicit; users can select Forecast during a radar outage.
    other = browser.new_page(viewport={'width': 390, 'height': 844})
    attach(other)
    other.route('**/radar-frames', lambda route: route.fulfill(status=503, json={'error': 'test outage'}))
    open_map(other)
    other.locator('#forecast').click()
    assert other.locator('#forecast').get_attribute('aria-pressed') == 'true'
    other.wait_for_function("!document.getElementById('timeline').disabled", timeout=90000)
    assert other.locator('#mode').inner_text() == 'FORECAST'
    print('PASS observation outage leaves selected forecast usable')
    other.close()

    failed = browser.new_page(viewport={'width': 390, 'height': 844})
    attach(failed)
    failed.route('**/radar-frames', lambda route: route.fulfill(status=503, json={'error': 'test outage'}))
    failed.route('**/forecast-frames', lambda route: route.fulfill(
        status=503, json={'status': 'unavailable', 'frames': []}))
    open_map(failed)
    failed.wait_for_function("document.getElementById('mode').textContent==='UNAVAILABLE'", timeout=30000)
    assert failed.locator('#timeline').is_disabled()
    assert failed.locator('#play').is_disabled()
    assert failed.locator('#clock').inner_text() == 'No frames available'
    failed.locator('#forecast').click()
    failed.wait_for_function("document.getElementById('mode').textContent==='UNAVAILABLE'", timeout=30000)
    assert failed.locator('#timeline').is_disabled()
    assert failed.locator('#play').is_disabled()
    print('PASS combined outage disables both modes and shows unavailable, not dry')
    failed.close()
    print('PAGE ERRORS', errors)
    assert not errors
    browser.close()
