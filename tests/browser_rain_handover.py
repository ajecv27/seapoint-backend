"""An unfinished motion pair must not replace the displayed rain with its past.

Use a delayed worker result at an hour boundary, with actual production renderer
code and synthetic translated rain to measure the visible displacement.
"""
import json,os,re,sys,time
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_motion import PNG,external_asset,fixture_png,fixture_server,scrub,png_image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from radar_view import radar_page
OUT=Path(os.environ.get('SEAPOINT_HANDOVER_OUTPUT',ROOT/'test-output/handover'));OUT.mkdir(parents=True,exist_ok=True)


def main():
    now=time.time();first=int(now//3600*3600)
    future=[{'time':first+i*3600,'url':f'/handover/{i}.png'}for i in range(50)]
    images={i:fixture_png(i,640)for i in range(50)}
    with fixture_server()as base,sync_playwright()as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
        page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.route(re.compile(r'https://.*'),external_asset)
        for name,entry in json.loads((ROOT/'static_site/vendor.json').read_text()).items():
            local=Path(os.environ.get('SEAPOINT_STATIC_SITE',ROOT/'_site'))/'vendor'/name
            if name.endswith(('.js','.css')) and local.exists():
                def local_asset(path):
                    return lambda route:route.fulfill(body=path.read_bytes(),content_type='text/css'if path.suffix=='.css'else'text/javascript')
                page.route(entry['url'],local_asset(local))
        page.route('**/radar?*',lambda r:r.fulfill(body=radar_page(17.12,-61.8,'Handover'),content_type='text/html'))
        page.route('**/rain-motion.js?*',lambda r:r.fulfill(body=(ROOT/'rain_motion.js').read_bytes(),content_type='text/javascript'))
        page.route('**/radar-frames',lambda r:r.fulfill(json={'host':base,'frames':[]}))
        page.route('**/forecast-frames',lambda r:r.fulfill(json={'status':'ready','source':'NOAA GFS','units':'mm/h','model_run':int((now-6*3600)//21600*21600),'fetched_at':int(now),'bounds':[[10,-68],[23,-55]],'forecast_until':int(now+48*3600),'coverage_complete':True,'frames':future}))
        page.route('**/handover/*.png',lambda r:r.fulfill(body=images[int(r.request.url.rsplit('/',1)[-1][:-4])],content_type='image/png'))
        page.route('**/basemap-style',lambda r:r.fulfill(json={'version':8,'sources':{},'layers':[{'id':'water','type':'background','paint':{'background-color':'#193e5f'}}]}))
        page.route('https://server.arcgisonline.com/**',lambda r:r.fulfill(body=PNG,content_type='image/png'))
        page.goto(base+'/radar?lat=17.12&lon=-61.8',wait_until='commit')
        try:
            page.wait_for_function("typeof predictionFrames!=='undefined'&&predictionFrames.length===50&&rainMotionRenderer!==null",timeout=15000)
        except Exception:
            print(json.dumps({'errors':errors,'state':page.evaluate("({title:document.title,body:document.body.innerText.slice(-250),forecast:typeof predictionFrames!=='undefined'?predictionFrames.length:null,motion:typeof rainMotionRenderer!=='undefined'?rainMotionRenderer?.stats:null})")}),flush=True)
            raise
        scrub(page,future[4]['time']-1)
        page.wait_for_function('seapointMotionState().renderer?.state==="ready"&&seapointMotionState().state==="moving"',timeout=20000)
        before=page.evaluate('''() => {
          window.requestAnimationFrame=()=>0;
          const canvas=rainMotionOverlay._canvas;
          return {png:canvas.toDataURL(),display:getComputedStyle(canvas).display,layers:Array.from(visibleLayers).map(l=>l.options.opacity)};
        }''')
        page.wait_for_timeout(100)
        held=page.evaluate('''stamp => {
          const prepare=rainMotionRenderer.preparePair.bind(rainMotionRenderer);
          rainMotionRenderer.preparePair=(...args)=>new Promise(resolve=>{window.releaseHandover=()=>prepare(...args).then(resolve);});
          rainMotionRenderer.prefetchPair=()=>Promise.resolve(false);
          playing=true;lastTick=0;position=stamp;
          const accepted=render(),canvas=rainMotionOverlay._canvas;
          return {accepted,png:canvas.toDataURL(),display:getComputedStyle(canvas).display,layers:Array.from(visibleLayers).map(l=>l.options.opacity),buffering:motionBuffered};
        }''',future[4]['time']+60)
        assert held['buffering']and held['accepted']is False,held
        assert held['display']!='none','Visible rain was removed while waiting for a new pair'
        assert held['png']==before['png'],'The previous presentation was overwritten while buffering'
        assert held['layers']==before['layers'],'Fallback image changed while the next pair was not ready'
        page.wait_for_function('typeof window.releaseHandover==="function"',timeout=10000)
        page.evaluate('window.releaseHandover()')
        page.wait_for_function('!motionJob&&seapointMotionState().state==="moving"',timeout=10000)
        after=png_image(page.evaluate('rainMotionOverlay._canvas.toDataURL()'))
        original=png_image(before['png'])
        def center(image):
            alpha=image.getchannel('A');weights=list(alpha.get_flattened_data())if hasattr(alpha,'get_flattened_data')else list(alpha.getdata())
            return sum((i%image.width)*v for i,v in enumerate(weights))/sum(weights)
        delta=center(after)-center(original)
        assert -.15<=delta<=1.5,{'hour_boundary_pixel_shift':delta}
        assert not errors,errors
        result={'held_display_unchanged':True,'hour_boundary_shift_pixels':delta,'playing':page.evaluate('playing'),'errors':errors}
        (OUT/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
        browser.close()

if __name__=='__main__':main()
