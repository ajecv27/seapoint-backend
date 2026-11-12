"""Phone startup: optional map/GPU downloads must not hide usable weather UI.

All weather and delayed assets are intercepted in the test browser; no fixtures
are served to app users. The retained baseline isolates the same 10s asset delay.
"""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.request import urlopen
from playwright.sync_api import sync_playwright
from browser_motion import PNG, external_asset, fixture_png, fixture_server, scrub

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from radar_view import radar_page
OUT=Path(os.environ.get('SEAPOINT_STARTUP_OUTPUT',ROOT/'test-output'/'startup'))
OUT.mkdir(parents=True,exist_ok=True)
BASELINE=Path(os.environ.get('SEAPOINT_STARTUP_BASELINE',OUT/'radar_view-before.py'))
MAPLIBRE='https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js'
PLUGIN='https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js'

class StartupPage:
    def __init__(self,browser,fixture,html,*,hold_seconds=0,plugin_failure=False,critical_failure=False):
        self.page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=2)
        self.errors=[];self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.add_init_script('window.__nativeReady=[];window.SeaPointRadar={postMessage:(value)=>window.__nativeReady.push({value,ms:performance.now()})};')
        self.held=[];self.hold_seconds=hold_seconds
        now=time.time();first=int(now//3600*3600);latest=int(now//600*600)
        self.future=[{'time':first+i*3600,'url':f'/startup-image/{i}.png'}for i in range(50)]
        self.images={i:fixture_png(i%10,640)for i in range(50)}
        observed=[{'time':latest-(7-i)*600,'path':f'/radar-cors/{i}'}for i in range(8)]
        page=self.page
        page.route(re.compile(r'https://.*'),external_asset)
        page.route('**/radar?*',lambda r:r.fulfill(body=html,content_type='text/html'))
        page.route('**/radar-frames',lambda r:r.fulfill(json={'host':fixture,'frames':observed}))
        page.route('**/forecast-frames',lambda r:r.fulfill(json={'status':'ready','source':'NOAA GFS','units':'mm/h','model_run':int(now-6*3600),'fetched_at':int(now),'bounds':[[10,-68],[23,-55]],'resolution_km':28,'forecast_until':int(now+48*3600),'coverage_complete':True,'frames':self.future}))
        page.route('**/startup-image/*.png',lambda r:r.fulfill(body=self.images[int(r.request.url.rsplit('/',1)[-1][:-4])],content_type='image/png'))
        page.route('**/basemap-style',lambda r:r.fulfill(json={'version':8,'sources':{},'layers':[{'id':'test-background','type':'background','paint':{'background-color':'#193e5f'}}]}))
        page.route('https://server.arcgisonline.com/**',lambda r:r.fulfill(body=PNG,content_type='image/png'))
        def optional(route):
            if self.hold_seconds:self.held.append((route,route.request.url));return
            self.release_one(route,route.request.url)
        page.route(MAPLIBRE,optional)
        page.route('**/rain-motion.js?*',optional)
        if plugin_failure:page.route(PLUGIN,lambda r:r.abort())
        if critical_failure:page.route('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',lambda r:r.abort())
        page.goto(fixture+'/radar?lat=17.12&lon=-61.8&name=Startup',wait_until='commit',timeout=30000)

    def release_one(self,route,url):
        data=(ROOT/'rain_motion.js').read_bytes()if '/rain-motion.js?' in url else MAPLIBRE_BYTES
        route.fulfill(body=data,content_type='text/javascript')

    def release(self):
        self.hold_seconds=0
        for route,url in self.held:self.release_one(route,url)
        self.held=[]

    def ready_ms(self):
        return self.page.evaluate('window.__nativeReady.find(message=>message.value==="ready")?.ms')

    def usable(self):
        page=self.page
        page.wait_for_function('radarFrames.length===8&&predictionFrames.length>=49&&!document.getElementById("play").disabled',timeout=15000)
        assert page.locator('#map').is_visible()and page.locator('#zoom-in').is_visible()
        page.locator('#play').click();before=page.evaluate('position')
        page.wait_for_function('(before)=>playing&&position>before',arg=before,timeout=5000)
        page.locator('#play').click()
        assert page.evaluate('forecastCoverageComplete()')
        assert not self.errors,self.errors


def main():
    global MAPLIBRE_BYTES
    with urlopen(MAPLIBRE,timeout=25)as response:MAPLIBRE_BYTES=response.read()
    current=radar_page(17.12,-61.8,'Startup')
    results={}
    with fixture_server()as fixture,sync_playwright()as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
        if BASELINE.exists():
            spec=importlib.util.spec_from_file_location('startup_before',BASELINE)
            baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
            old=StartupPage(browser,fixture,baseline.radar_page(17.12,-61.8,'Startup'),hold_seconds=10)
            old.page.wait_for_timeout(10000)
            assert old.ready_ms()is None,'Baseline unexpectedly ready with critical scripts held'
            old.release();old.page.wait_for_function('window.__nativeReady.some(message=>message.value==="ready")',timeout=15000)
            results['baseline_ready_ms']=old.ready_ms();old.page.close()
        new=StartupPage(browser,fixture,current,hold_seconds=10)
        new.page.wait_for_function('window.__nativeReady.some(message=>message.value==="ready")',timeout=5000)
        results['progressive_ready_ms']=new.ready_ms()
        assert new.page.evaluate('window.seapointBootReady===true')
        assert results['progressive_ready_ms']<5000,results
        new.usable();assert new.held,'Optional resources were not actually held'
        new.page.screenshot(path=str(OUT/'usable-while-optional-loading.png'))
        new.page.wait_for_timeout(max(0,10000-results['progressive_ready_ms']))
        new.release()
        new.page.wait_for_function('flatBasemap!==null&&rainMotionRenderer!==null',timeout=20000)
        scrub(new.page,new.future[2]['time']+1800)
        new.page.wait_for_function('seapointMotionState().renderer?.state==="ready"&&seapointMotionState().kind==="forecast"',timeout=20000)
        assert new.page.locator('#rain-motion-canvas').is_visible()
        assert not new.errors,new.errors
        results['delayed_assets_recovered']=True;new.page.close()
        print('PASS native UI ready and weather playable during10s optional map/motion delay; both optional resources recover afterward',flush=True)
        failure=StartupPage(browser,fixture,current,plugin_failure=True)
        failure.page.wait_for_function('window.__nativeReady.some(message=>message.value==="ready")',timeout=5000)
        failure.usable()
        failure.page.wait_for_function('document.getElementById("basemap-status").textContent.includes("temporarily unavailable")',timeout=15000)
        assert failure.page.evaluate('flatBasemap===null&&playing===false')
        assert failure.page.evaluate('forecastCoverageComplete()')and not failure.errors,failure.errors
        results['optional_plugin_failure_keeps_weather']=True;failure.page.close()
        critical=StartupPage(browser,fixture,current,critical_failure=True)
        critical.page.wait_for_function('window.__nativeReady.some(message=>message.value==="error")',timeout=5000)
        assert critical.ready_ms()is None and critical.page.evaluate('window.seapointBootReady!==true&&window.seapointBootFailed===true')
        results['critical_failure_notifies_native_retry']=True;critical.page.close();browser.close()
    (OUT/'verification.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results),flush=True)

if __name__=='__main__':main()
