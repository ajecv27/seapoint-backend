"""Exercise the built Pages site at a repository subpath with Render blocked."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
import time

from playwright.sync_api import sync_playwright
from browser_motion import PNG, scrub

SITE=Path(os.environ['SEAPOINT_STATIC_SITE']).resolve()
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-output/static-site'
OUT.mkdir(parents=True,exist_ok=True)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


def main():
    manifest=json.loads((SITE/'data/latest.json').read_text())
    results={}
    with tempfile.TemporaryDirectory() as directory:
        (Path(directory)/'seapoint-backend').symlink_to(SITE,target_is_directory=True)
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=directory))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{server.server_port}/seapoint-backend/'
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,
                args=['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
            def page_for(*,offset=0,stale=False,invalid_coordinates=False):
                page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
                page.errors=[];page.requests=[]
                page.on('pageerror',lambda error:page.errors.append(str(error)))
                page.on('request',lambda request:page.requests.append(request.url))
                page.add_init_script(f'const realNow=Date.now;Date.now=()=>realNow()+{int(offset*1000)};window.SeaPointRadar={{postMessage:(message)=>window.nativeReady=message}};')
                # Real static HTML, vendor libraries, model PNGs and manifest;
                # isolate external basemap assets so tile networks cannot affect
                # the Render-independence and source timestamp assertions.
                page.route(re.compile(r'https://.*'),lambda r:r.abort())
                page.route('https://server.arcgisonline.com/**',lambda r:r.fulfill(body=PNG,content_type='image/png'))
                page.route('**/basemap-style.json',lambda r:r.fulfill(json={'version':8,'sources':{},'layers':[{'id':'water','type':'background','paint':{'background-color':'#193e5f'}}]}))
                latest=int((time.time()+offset)//600*600)
                observed=[{'time':latest-i*600,'path':f'/observed/{i}'}for i in range(7,-1,-1)]
                page.route('https://api.rainviewer.com/public/weather-maps.json',lambda r:r.fulfill(json={'host':base.rstrip('/'),'radar':{'past':observed}},headers={'Access-Control-Allow-Origin':'*'}))
                page.route('**/observed/**',lambda r:r.fulfill(body=PNG,content_type='image/png',headers={'Access-Control-Allow-Origin':'*'}))
                if stale:
                    data=dict(manifest,published_at=int(time.time()-90000))
                    page.route('**/data/latest.json?*',lambda r:r.fulfill(json=data))
                suffix='?lat=NaN&lon=999&name=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E'if invalid_coordinates else '?lat=17.12&lon=-61.8&name=Antigua'
                page.goto(base+suffix,wait_until='commit')
                page.wait_for_function('window.nativeReady==="ready"',timeout=5000)
                page.wait_for_function('radarFrames.length===8',timeout=10000)
                return page
            page=page_for(offset=3600)
            page.wait_for_function('forecastCoverageComplete()&&predictionFrames.length>=49',timeout=30000)
            assert page.evaluate('timelineEnd===forecastMeta.forecast_until&&timelineEnd-Date.now()/1000>=48*3600-60'),page.evaluate('({timelineEnd,now:Date.now()/1000,until:forecastMeta.forecast_until})')
            assert page.evaluate('forecastMeta.published_at')==manifest['published_at']
            assert {f['model_run']for f in page.evaluate('predictionFrames')}<={f['model_run']for f in manifest['frames']}
            assert not any('onrender.com'in url for url in page.requests),page.requests
            page.wait_for_function('rainMotionRenderer!==null',timeout=10000)
            target=page.evaluate('predictionFrames[5].time+1800')
            scrub(page,target)
            page.wait_for_function('seapointMotionState().renderer?.state==="ready"',timeout=20000)
            page.locator('#play').click()
            before=page.evaluate('position')
            page.locator('#zoom-out').click()
            page.locator('#map').hover(position={'x':150,'y':260})
            page.mouse.down();page.mouse.move(230,300,steps=8);page.mouse.up()
            page.wait_for_function('(before)=>playing&&position>before',arg=before,timeout=10000)
            page.locator('#play').click()
            page.locator('#info-toggle').click()
            assert 'Data published'in page.locator('#model-run').inner_text()
            assert not page.errors,page.errors
            page.screenshot(path=str(OUT/'static-radar-at-subpath.png'))
            results['render_blocked_full_48_hours_after_one_hour']=True
            results['real_forecast_images_and_motion_loaded']=True
            results['pan_and_zoom_preserve_playback']=True
            results['requests']=len(page.requests)
            page.close()
            stale=page_for(stale=True)
            stale.wait_for_function('forecastState==="reconnecting"&&!loading',timeout=10000)
            assert stale.evaluate('predictionFrames.length===0&&radarFrames.length===8')
            assert not stale.errors,stale.errors
            results['stale_publication_rejected_observations_retained']=True
            stale.close()
            invalid=page_for(invalid_coordinates=True)
            assert invalid.evaluate('config.lat===17.12&&config.lon===-61.8')
            assert invalid.locator('#map img[src="x"]').count()==0
            results['query_location_validation']=True
            invalid.close();browser.close()
        server.shutdown()
    (OUT/'verification.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results))

if __name__=='__main__':main()
