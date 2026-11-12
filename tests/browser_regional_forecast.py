"""Provider-aware phone playback checks. All weather is isolated test data."""
from pathlib import Path
import json, os, re, time
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from browser_motion import BASE_URL, OUTPUT, PNG, external_asset, fixture_png, fixture_server, scrub

class RegionalFixture:
    def __init__(self, browser, fixture):
        self.page = browser.new_page(viewport={'width':390,'height':844}, device_scale_factor=2)
        self.errors=[]; self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.regional=False; self.held=[]; self.hold=True
        now=time.time(); self.run=int((now-6*3600)//21600*21600)
        self.first=int(now//3600*3600); self.until=int(now+48*3600)
        self.last=int((self.run+48*3600-self.first)//3600)
        self.images={i:fixture_png(i%10,640) for i in range(50)}
        latest=int(now//600*600)
        observed=[{'time':latest-(7-i)*600,'path':f'/radar-cors/{i}'} for i in range(8)]
        self.page.route(re.compile(r'https://.*'),external_asset)
        self.page.route('**/radar-frames',lambda r:r.fulfill(json={'host':fixture,'frames':observed}))
        self.page.route('**/forecast-frames',self.manifest)
        self.page.route('**/finer-fixture/*.png',self.image)
        self.page.route('**/basemap-style',lambda r:r.fulfill(json={'version':8,'sources':{},'layers':[{'id':'background','type':'background','paint':{'background-color':'#193e5f'}}]}))
        self.page.route('https://server.arcgisonline.com/**',lambda r:r.fulfill(body=PNG,content_type='image/png'))
        self.page.goto(BASE_URL+'/radar?lat=17.12&lon=-61.8&name=Regional%20test',wait_until='domcontentloaded',timeout=60000)
        self.page.wait_for_function('predictionFrames.length===50&&pending.size===0',timeout=60000)

    def manifest(self, route):
        frames=[]
        for i in range(50):
            local=self.regional and i<=self.last
            frames.append({'time':self.first+i*3600,'url':f'/finer-fixture/{"arome" if local else "gfs"}-{i}.png',
                           'provider':'arome-antilles' if local else 'noaa-gfs',
                           'model_run':self.run if local else self.run-21600,
                           'bounds':[[10,-68],[22.9 if local else 23,-55]],
                           'resolution_km':2.5 if local else 28,'period_seconds':3600 if local else 0})
        route.fulfill(json={'status':'ready','source':'Regional test','model_run':self.run,
                           'fetched_at':int(time.time()),'units':'mm/h','resolution_km':28,
                           'bounds':[[10,-68],[22.9,-55]],'frames':frames,
                           'forecast_until':self.until,'coverage_complete':True,'horizon_hours':48,'updating':not self.regional})

    def image(self, route):
        name=urlsplit(route.request.url).path.rsplit('/',1)[-1]
        source,index=name[:-4].split('-'); index=int(index)
        if source=='arome' and index==7 and self.hold:
            self.held.append(route);return
        route.fulfill(body=self.images[index],content_type='image/png')

    def release(self):
        self.hold=False
        for route in self.held:route.fulfill(body=self.images[7],content_type='image/png')
        self.held=[]


def main():
    with fixture_server() as fixture,sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
        test=RegionalFixture(browser,fixture);page=test.page
        assert page.evaluate('forecastCoverageComplete()')
        test.regional=True
        page.wait_for_function('predictionFrames.find(f=>f.time===forecast[2].time)?.provider==="arome-antilles"',timeout=30000)
        page.wait_for_function('pending.size>0',timeout=10000)
        retained=page.evaluate('(time)=>predictionFrames.find(f=>f.time===time).provider',test.first+7*3600)
        assert retained=='noaa-gfs',retained
        assert page.evaluate('timelineEnd')==test.until
        test.release();page.wait_for_function('pending.size===0&&forecastCoverageComplete()',timeout=45000)
        fields=page.evaluate('(last)=>({first:predictionFrames[2],tail:predictionFrames[last+1],keys:new Set(predictionFrames.map(key)).size,info:document.getElementById("model-run").textContent})',test.last)
        assert fields['first']['model_run']==test.run and fields['first']['bounds']==[[10,-68],[22.9,-55]],fields
        assert fields['tail']['model_run']==test.run-21600 and fields['tail']['bounds']==[[10,-68],[23,-55]],fields
        assert fields['keys']==50 and 'Météo-France' in fields['info'] and 'NOAA GFS' in fields['info'],fields
        assert page.evaluate('sameForecastSource({provider:"arome-antilles",model_run:1,bounds:[]},{provider:"noaa-gfs",model_run:1,bounds:[]})') is False
        print('PASS automatic regional upgrade retries a complete GFS forecast while the regional cache builds; preserves GFS during a held regional image; per-source model times, bounds and 48-hour horizon survive',flush=True)
        scrub(page,test.first+2*3600+1800)
        page.wait_for_function('seapointMotionState().state==="moving"',timeout=15000)
        assert page.evaluate('rainMotionOverlay._bounds.getNorth()')==22.9
        page.locator('#play').click();before=page.evaluate('position')
        page.mouse.move(160,350);page.mouse.down();page.mouse.move(210,390,steps=8);page.mouse.up()
        page.wait_for_function('(old)=>playing&&position>old',arg=before,timeout=5000)
        page.locator('#zoom-out').click();page.wait_for_timeout(350)
        assert page.evaluate('playing')
        page.locator('#play').click()
        print('PASS regional rain uses its true geographic bounds and keeps playback active during pan and zoom',flush=True)
        scrub(page,test.first+(test.last+.25)*3600);page.wait_for_timeout(250)
        assert not page.locator('#rain-motion-canvas').is_visible()
        visible=page.evaluate('Array.from(visibleLayers).filter(layer=>layer.options.opacity>0).length')
        assert visible==1,visible
        assert page.evaluate('timelineEnd')==test.until
        assert not test.errors,test.errors
        page.screenshot(path=str(OUTPUT/'regional-handoff-mobile.png'))
        print('PASS the regional/GFS handoff displays one actual frame and never morphs across models; full 48-hour endpoint retained',flush=True)
        page.close();browser.close()

if __name__=='__main__':main()
