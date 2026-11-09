"""Radar pacing check using explicit test fixtures against a local backend.

No synthetic weather is exposed by the application: only this browser test
intercepts provider responses and substitutes eight ten-minute fixture frames.
"""
import base64
import os
import re
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get('SEAPOINT_TEST_URL', 'http://127.0.0.1:8780').rstrip('/')
TRANSPARENT_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
asset_cache = {}


def external_asset(route):
    """Retain managed-environment TLS verification for external JS/CSS."""
    url = route.request.url
    try:
        if url not in asset_cache:
            request = Request(url, headers={
                'User-Agent': route.request.headers.get('user-agent', 'SeaPoint/1.0'),
                'Referer': BASE_URL + '/',
            })
            try:
                response = urlopen(request, timeout=25)
            except HTTPError as error:
                response = error
            with response:
                asset_cache[url] = (response.status, response.read(),
                                    response.headers.get('Content-Type', 'application/octet-stream'))
        status, data, content_type = asset_cache[url]
        route.fulfill(status=status, body=data, content_type=content_type,
                      headers={'Access-Control-Allow-Origin': '*'})
    except Exception:
        route.abort()


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'),
        headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=3)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route(re.compile(r'https://.*'), external_asset)

    latest = int(time.time() // 600 * 600)
    frames = [{'time': latest - (7 - i) * 600, 'path': '/fixture/' + str(i)} for i in range(8)]
    page.route('**/radar-frames', lambda route: route.fulfill(json={
        'host': 'https://radar-fixture.test', 'frames': frames,
    }))
    page.route('https://radar-fixture.test/**', lambda route: route.fulfill(
        body=TRANSPARENT_PNG, content_type='image/png'))
    page.route('**/forecast-frames', lambda route: route.fulfill(
        status=503, json={'status': 'unavailable', 'frames': []}))
    page.route('**/basemap-style', lambda route: route.fulfill(json={
        'version': 8, 'sources': {},
        'layers': [{'id': 'test-background', 'type': 'background',
                    'paint': {'background-color': '#183d63'}}],
    }))
    page.route('https://server.arcgisonline.com/**', lambda route: route.fulfill(
        body=TRANSPARENT_PNG, content_type='image/png'))
    page.goto(BASE_URL + '/radar?lat=17.12&lon=-61.8&name=Pacing%20test',
              wait_until='domcontentloaded', timeout=60000)
    page.wait_for_function("!document.getElementById('play').disabled", timeout=30000)
    assert page.evaluate('mapStatus') == 'OBSERVED'
    assert page.evaluate('radarTileSize') == 512
    assert page.locator('#timeline').input_value() == str(latest)

    page.locator('#play').click()
    before = int(page.locator('#timeline').input_value())
    page.wait_for_timeout(3000)
    after = int(page.locator('#timeline').input_value())
    advancement = after - before
    assert 600 <= advancement <= 1100, advancement
    print('PASS 3 seconds of radar playback advances', advancement,
          'timeline seconds (expected about 900)', flush=True)

    page.locator('#play').click()
    frozen = page.locator('#timeline').input_value()
    page.wait_for_timeout(400)
    assert page.locator('#timeline').input_value() == frozen
    print('PASS pause freezes radar position', flush=True)

    # Scrub near the final observation, then observe the actual latest-frame
    # pause and subsequent loop rather than calling animation internals.
    page.locator('#timeline').evaluate(
        "e=>{e.value=Number(e.max)-60;e.dispatchEvent(new Event('input',{bubbles:true}));}")
    page.locator('#play').click()
    page.wait_for_function(
        "document.getElementById('timeline').value===document.getElementById('timeline').max",
        timeout=3000)
    reached_latest = time.monotonic()
    page.wait_for_timeout(1000)
    assert page.locator('#timeline').input_value() == str(latest)
    page.wait_for_function(
        "Number(document.getElementById('timeline').value)<Number(document.getElementById('timeline').max)",
        timeout=3500)
    hold_seconds = time.monotonic() - reached_latest
    assert 2.2 <= hold_seconds <= 3.4, hold_seconds
    print('PASS latest observation holds before looping:', round(hold_seconds, 2), 'seconds', flush=True)

    page.locator('#play').click()
    frozen = page.locator('#timeline').input_value()
    page.wait_for_timeout(300)
    assert page.locator('#timeline').input_value() == frozen
    assert not errors, errors
    print('PASS final pause; no JavaScript errors', flush=True)
    browser.close()
