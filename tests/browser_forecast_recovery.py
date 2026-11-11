"""Phone-browser forecast availability regressions with isolated weather fixtures.

Run a local backend with SEAPOINT_TEST_URL. Every weather response and image in
these checks is intercepted in the test page; none is served to real users.
The tests exercise recovery through timers and browser lifecycle events rather
than reloading the page or calling the application's loading functions.
"""
from __future__ import annotations

import os
import re
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from browser_motion import BASE_URL, OUTPUT, PNG, external_asset, fixture_png, fixture_server, scrub


class RecoveryFixture:
    """Control manifest failures and individual outstanding image requests."""

    def __init__(self, browser, fixture_base, *, actions=None, held=(), failed=(), observed=True, frame_count=9, model_age=6*3600):
        self.page = browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.actions = list(actions or ['ready'])
        self.requests = []
        self.image_requests = []
        self.image_urls = []
        self.held = set(held)
        self.failed = set(failed)
        self.pending_images = []
        self.image = fixture_png(1)
        now = time.time()
        latest = int(now // 600 * 600)
        first_hour = int(now // 3600 * 3600)
        self.observed = [{'time': latest-(7-i)*600, 'path': f'/radar-cors/{i}'} for i in range(8)] if observed else []
        self.future = [{'time': first_hour+i*3600, 'url': f'/fixture-recovery/{i}.png'} for i in range(frame_count)]
        self.manifest = {
            'status': 'ready', 'source': 'NOAA GFS', 'units': 'mm/h',
            'model_run': int(now-model_age), 'fetched_at': int(now),
            'resolution_km': 28, 'bounds': [[10, -68], [23, -55]],
            'forecast_until': first_hour+max(48, frame_count-1)*3600, 'frames': self.future,
        }
        # Availability should work on a phone even if GPU motion is unavailable.
        self.page.add_init_script('''(() => {
          const original=HTMLCanvasElement.prototype.getContext;
          HTMLCanvasElement.prototype.getContext=function(type,...args){
            return String(type).startsWith('webgl')?null:original.call(this,type,...args);
          };
          window.__fixtureWeatherTicks=0;
          const requestFrame=window.requestAnimationFrame.bind(window);
          window.requestAnimationFrame=callback=>requestFrame(stamp=>{
            if(callback.name==='tick')window.__fixtureWeatherTicks++;
            callback(stamp);
          });
          window.__fixtureHidden=false;
          Object.defineProperty(document,'hidden',{configurable:true,get:()=>window.__fixtureHidden});
          Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>window.__fixtureHidden?'hidden':'visible'});
        })();''')
        self.page.route(re.compile(r'https://.*'), external_asset)
        self.page.route('**/radar-frames', lambda route: route.fulfill(json={'host': fixture_base, 'frames': self.observed}))
        self.page.route('**/forecast-frames', self.manifest_request)
        self.page.route('**/fixture-recovery/*.png', self.image_request)
        self.page.route('**/basemap-style', lambda route: route.fulfill(json={
            'version': 8, 'sources': {}, 'layers': [{'id': 'test-background', 'type': 'background',
                'paint': {'background-color': '#183d63'}}]}))
        self.page.route('https://server.arcgisonline.com/**', lambda route: route.fulfill(body=PNG, content_type='image/png'))
        self.page.goto(BASE_URL+'/radar?lat=17.12&lon=-61.8&name=Recovery%20test',
            wait_until='domcontentloaded', timeout=60000)
        self.page.wait_for_function('typeof window.seapointMotionState==="function"', timeout=15000)

    def manifest_request(self, route):
        action = self.actions[min(len(self.requests), len(self.actions)-1)]
        self.requests.append({'at': time.monotonic(), 'action': str(action)})
        if action == 'network':
            route.abort('internetdisconnected')
        elif action == 'invalid-json':
            route.fulfill(status=200, body='{broken', content_type='application/json')
        elif action == 'preparing':
            route.fulfill(status=202, json={'status': 'loading'})
        elif action == '503':
            route.fulfill(status=503, json={'status': 'unavailable'})
        else:
            route.fulfill(json=self.manifest if action == 'ready' else action)

    def image_request(self, route):
        index = int(urlsplit(route.request.url).path.rsplit('/', 1)[-1].split('.')[0].split('-')[0])
        self.image_requests.append(index)
        self.image_urls.append(route.request.url)
        if index in self.held:
            # Returning without fulfilling leaves this individual image in flight;
            # other network responses and the page's main thread keep running.
            self.pending_images.append((index, route))
        elif index in self.failed:
            route.fulfill(status=503, body='test-only missing image', content_type='text/plain')
        else:
            route.fulfill(body=self.image, content_type='image/png')

    def release(self, indices=None):
        release = self.held.copy() if indices is None else set(indices)
        self.held.difference_update(release)
        keep = []
        for index, route in self.pending_images:
            if index in release:
                route.fulfill(body=self.image, content_type='image/png')
            else:
                keep.append((index, route))
        self.pending_images = keep

    def wait_observed(self, timeout=10000):
        self.page.wait_for_function('radarFrames.length>=2&&!document.getElementById("play").disabled', timeout=timeout)

    def wait_forecast(self, count=2, timeout=35000):
        self.page.wait_for_function('(count)=>predictionFrames.length>=count', arg=count, timeout=timeout)

    def snapshot(self):
        return self.page.evaluate('''() => ({
          observed:radarFrames.map(f=>f.time),forecast:predictionFrames.map(f=>f.time),
          timelineEnd,position,mapStatus,playing,
          availability:document.getElementById('availability').textContent,
          notice:document.getElementById('notice').textContent,
          detail:document.getElementById('detail').textContent,
          end:document.getElementById('end').textContent,
          expectedEnd:format(timelineEnd),
          playDisabled:document.getElementById('play').disabled,
          navigationCount:performance.getEntriesByType('navigation').length
        })''')

    def lifecycle(self, event):
        if event != 'hidden':
            # A real return from another app occurs after the initial pageshow
            # recovery event; allow its short duplicate-event guard to expire.
            self.page.wait_for_load_state('load', timeout=10000)
            self.page.wait_for_timeout(3200)
        if event == 'visible':
            self.page.evaluate('''() => {
              window.__fixtureHidden=false;
              document.dispatchEvent(new Event('visibilitychange'));
            }''')
        elif event == 'hidden':
            self.page.evaluate('''() => {
              window.__fixtureHidden=true;
              document.dispatchEvent(new Event('visibilitychange'));
            }''')
        else:
            self.page.evaluate('window.dispatchEvent(new Event("online"))')

    def close(self):
        assert not self.errors, self.errors
        self.page.close()


def check_retry(browser, fixture_base, failure):
    case = RecoveryFixture(browser, fixture_base, actions=[failure])
    case.wait_observed()
    case.page.wait_for_load_state('load', timeout=10000)
    assert not case.snapshot()['forecast'], case.snapshot()
    case.actions = ['ready']
    case.wait_forecast()
    state = case.snapshot()
    assert len(case.requests) >= 2, case.requests
    assert case.requests[1]['at']-case.requests[0]['at'] < 60, case.requests
    assert state['navigationCount'] == 1 and not state['playDisabled'], state
    scrub(case.page, case.future[3]['time'])
    assert case.snapshot()['mapStatus'] == 'FORECAST', case.snapshot()
    case.close()
    print(f'PASS {failure} forecast response recovers automatically on the same phone page within one minute', flush=True)


def check_lifecycle_recovery(browser, fixture_base):
    for event in ['visible', 'online']:
        case = RecoveryFixture(browser, fixture_base, actions=['503'])
        case.wait_observed()
        case.actions = ['ready']
        if event == 'visible':
            case.lifecycle('hidden')
            assert case.page.evaluate('document.hidden')
        began = time.monotonic()
        case.lifecycle(event)
        case.wait_forecast(timeout=10000)
        assert len(case.requests) >= 2 and time.monotonic()-began < 10, case.requests
        assert case.snapshot()['navigationCount'] == 1, case.snapshot()
        case.close()
        print(f'PASS {event} browser event retries a failed forecast without a reload', flush=True)


def check_progressive_images(browser, fixture_base):
    case = RecoveryFixture(browser, fixture_base, held=range(9))
    case.wait_observed(timeout=10000)
    assert not case.snapshot()['forecast'], case.snapshot()
    # The pending forecast must not stall starting observed playback.
    case.page.locator('#play').click()
    before = case.page.evaluate('position')
    case.page.wait_for_function('(before)=>playing&&position>before', arg=before, timeout=4000)
    assert case.snapshot()['mapStatus'] == 'OBSERVED', case.snapshot()
    case.page.locator('#play').click()
    # Release near-future images while the distant horizon remains in flight.
    case.release([0, 1, 2, 3])
    case.wait_forecast(count=2, timeout=10000)
    state = case.snapshot()
    assert case.held and state['timelineEnd'] <= case.future[3]['time'], state
    assert state['timelineEnd'] < case.manifest['forecast_until'], state
    assert state['end'] == state['expectedEnd'], state
    if 'available through' in state['availability'].lower():
        assert state['expectedEnd'] in state['availability'], state
    target = case.future[1]['time']
    scrub(case.page, target)
    assert case.snapshot()['mapStatus'] == 'FORECAST', case.snapshot()
    case.page.screenshot(path=str(OUTPUT/'forecast-partial-phone.png'))
    case.release()
    case.wait_forecast(count=9, timeout=10000)
    case.close()
    print('PASS observed radar plays during slow forecast downloads; loaded near-future images become usable before the entire horizon', flush=True)


def check_failed_image_gap(browser, fixture_base):
    case = RecoveryFixture(browser, fixture_base, failed={3})
    case.wait_forecast(count=8, timeout=15000)
    state = case.snapshot()
    assert case.future[3]['time'] not in state['forecast'], state
    assert case.future[2]['time'] in state['forecast'] and case.future[4]['time'] in state['forecast'], state
    # Neither the failed hour nor the wide interval around it is clear weather.
    for target in [case.future[3]['time'], case.future[3]['time']+900]:
        scrub(case.page, target)
        state = case.snapshot()
        assert state['mapStatus'] == 'GAP', state
        assert case.page.locator('#notice').is_visible(), state
        assert case.page.evaluate('Array.from(loaded.values()).every(layer=>!layer.options.opacity)'), state
    scrub(case.page, case.future[4]['time'])
    assert case.snapshot()['mapStatus'] == 'FORECAST', case.snapshot()
    case.failed.clear()
    case.wait_forecast(count=9, timeout=35000)
    assert len(case.requests) >= 2, case.requests
    scrub(case.page, case.future[3]['time'])
    assert case.snapshot()['mapStatus'] == 'FORECAST', case.snapshot()
    case.close()
    print('PASS one failed PNG preserves other hours, marks the gap, and recovers that hour on the same page', flush=True)


def check_all_images_failed(browser, fixture_base):
    case = RecoveryFixture(browser, fixture_base, failed=range(9))
    case.wait_observed()
    case.page.wait_for_function('forecast.length>=9&&pending.size===0', timeout=15000)
    state = case.snapshot()
    assert not state['forecast'] and state['timelineEnd'] == case.observed[-1]['time'], state
    assert state['mapStatus'] == 'OBSERVED' and not state['playDisabled'], state
    assert 'available through' not in state['availability'].lower(), state
    case.close()
    print('PASS all forecast PNG failures leave observed playback available without advertising an unloaded horizon', flush=True)

    empty = RecoveryFixture(browser, fixture_base, failed=range(9), observed=False)
    empty.page.wait_for_function('mapStatus==="UNAVAILABLE"&&pending.size===0', timeout=15000)
    state = empty.snapshot()
    assert state['playDisabled'] and not state['forecast'], state
    assert empty.page.locator('#notice').is_visible(), state
    assert 'available through' not in state['availability'].lower(), state
    empty.close()
    print('PASS complete image outage presents unavailable weather instead of an empty clear-weather forecast', flush=True)


def check_stale_manifest(browser, fixture_base):
    now = int(time.time())
    expired = {
        'status': 'ready', 'source': 'NOAA GFS', 'units': 'mm/h',
        'model_run': now-3*86400, 'forecast_until': now-86400,
        'bounds': [[10, -68], [23, -55]],
        'frames': [{'time': now-86400+i*3600, 'url': f'/fixture-recovery/{i}.png'} for i in range(3)],
    }
    case = RecoveryFixture(browser, fixture_base, actions=[expired])
    case.wait_observed()
    case.page.wait_for_function('''() => {const s=seapointForecastState();
      return s.state==='reconnecting'&&!s.loading;}''', timeout=10000)
    state = case.snapshot()
    assert not state['forecast'] and state['timelineEnd'] == state['observed'][-1], state
    assert state['mapStatus'] == 'OBSERVED' and not state['playDisabled'], state
    assert 'available through' not in state['availability'].lower(), state
    assert not case.image_requests, case.image_requests
    case.close()
    print('PASS a ready manifest with expired source timestamps does not advertise future coverage', flush=True)


def check_loaded_forecast_retained(browser, fixture_base):
    case = RecoveryFixture(browser, fixture_base)
    case.wait_forecast(count=9, timeout=15000)
    original = case.snapshot()['forecast']
    target = case.future[4]['time']
    scrub(case.page, target)
    # Simulate an outage after the page has a valid future horizon.
    case.actions = ['503']
    count = len(case.requests)
    case.lifecycle('online')
    case.page.wait_for_function('''() => {const s=seapointForecastState();
      return s.state==='reconnecting'&&!s.loading;}''', timeout=10000)
    assert len(case.requests) > count, case.requests
    state = case.snapshot()
    assert state['forecast'] == original and state['mapStatus'] == 'FORECAST', state
    assert state['position'] == target and not state['playDisabled'], state
    case.close()
    print('PASS a later manifest outage retains loaded future imagery and the selected forecast time', flush=True)


    replacement = RecoveryFixture(browser, fixture_base)
    replacement.wait_forecast(count=9, timeout=15000)
    original = replacement.snapshot()['forecast']
    target = replacement.future[4]['time']
    scrub(replacement.page, target)
    replacement.failed = set(range(9))
    broken = dict(replacement.manifest)
    broken['frames'] = [dict(frame, url=frame['url'].replace('.png', '-refresh.png')) for frame in replacement.future]
    replacement.actions = [broken]
    count = len(replacement.requests)
    replacement.lifecycle('online')
    replacement.page.wait_for_function('!loading&&pending.size===0', timeout=15000)
    assert len(replacement.requests) > count and any('-refresh.png' in url for url in replacement.image_urls), {
        'manifests': replacement.requests, 'images': replacement.image_urls}
    state = replacement.snapshot()
    assert state['forecast'] == original and state['mapStatus'] == 'FORECAST', state
    assert state['position'] == target and not state['playDisabled'], state
    assert replacement.page.evaluate('Array.from(loaded.values()).some(layer=>layer.options.opacity>0)'), state
    for frame_index in [2, 7]:
        scrub(replacement.page, replacement.future[frame_index]['time'])
        state = replacement.snapshot()
        assert state['mapStatus'] == 'FORECAST' and not replacement.page.locator('#notice').is_visible(), state
        assert replacement.page.evaluate('Array.from(loaded.values()).some(layer=>layer.options.opacity>0)'), state
    replacement.close()
    print('PASS an image outage in a replacement model retains the previously loaded valid future', flush=True)


def check_full_horizon_outage(browser, fixture_base):
    case = RecoveryFixture(browser, fixture_base, frame_count=50)
    case.wait_forecast(count=50, timeout=20000)
    case.page.wait_for_function('seapointForecastState().coverageComplete', timeout=10000)
    scrub(case.page, case.future[4]['time'])
    original = case.snapshot()
    case.actions = ['503']
    count = len(case.requests)
    case.lifecycle('online')
    case.page.wait_for_function('''() => {const s=seapointForecastState();
      return s.state==='reconnecting'&&!s.loading&&s.retryScheduled&&s.metadataHealthy===false;}''', timeout=10000)
    state = case.snapshot()
    assert len(case.requests) > count and state['forecast'] == original['forecast'], state
    assert state['position'] == original['position'] and state['mapStatus'] == 'FORECAST', state
    count = len(case.requests)
    case.actions = ['ready']
    case.page.wait_for_function('''() => {const s=seapointForecastState();
      return s.coverageComplete&&s.metadataHealthy&&!s.loading&&!s.retryScheduled;}''', timeout=35000)
    assert len(case.requests) > count and case.snapshot()['navigationCount'] == 1, case.requests
    case.close()
    print('PASS a complete loaded 48-hour horizon retains imagery during metadata outage and still retries to healthy', flush=True)


def check_forecast_expires_during_hold(browser, fixture_base):
    case = RecoveryFixture(browser, fixture_base, model_age=24*3600-30)
    case.wait_forecast(count=9, timeout=15000)
    case.wait_observed()
    scrub(case.page, case.observed[-1]['time']-1)
    case.page.locator('#play').click()
    case.page.wait_for_function('playing&&holdAction==="forecast"', timeout=5000)
    case.page.evaluate('''() => {
      const originalNow=Date.now.bind(Date);
      Date.now=()=>originalNow()+31000;
      publishReadyFrames(true);
    }''')
    assert not case.snapshot()['forecast'], case.snapshot()
    # Let the pending source-transition hold expire naturally. A throw inside
    # tick would stop this named RAF callback while map-library RAFs continue.
    case.page.wait_for_timeout(3000)
    before = case.page.evaluate('({ticks:window.__fixtureWeatherTicks,position})')
    case.page.wait_for_function('(before)=>window.__fixtureWeatherTicks>before.ticks+2&&playing&&position>before.position',
        arg=before, timeout=4000)
    state = case.snapshot()
    assert state['mapStatus'] == 'OBSERVED' and not state['playDisabled'], state
    case.close()
    print('PASS forecast expiration during the radar-to-forecast hold keeps the observed animation clock alive', flush=True)


def main():
    with fixture_server() as fixture_base, sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), headless=True,
            args=['--no-sandbox', '--enable-unsafe-swiftshader'])
        for failure in ['preparing', '503', 'network', 'invalid-json']:
            check_retry(browser, fixture_base, failure)
        check_lifecycle_recovery(browser, fixture_base)
        check_progressive_images(browser, fixture_base)
        check_failed_image_gap(browser, fixture_base)
        check_all_images_failed(browser, fixture_base)
        check_stale_manifest(browser, fixture_base)
        check_loaded_forecast_retained(browser, fixture_base)
        check_full_horizon_outage(browser, fixture_base)
        check_forecast_expires_during_hold(browser, fixture_base)
        browser.close()
    print('PASS forecast availability recovery browser checks completed', flush=True)


if __name__ == '__main__':
    main()
