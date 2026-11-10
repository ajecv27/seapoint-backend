"""Real-browser rain-motion checks using explicit test-only weather fixtures.

The first checks inspect WebGL output pixels, so a fading pair of stationary
images cannot pass merely because its average centroid lies between the blobs.
The application never returns these fixtures to users. Set SEAPOINT_TEST_URL to
an already running local SeaPoint backend for the map integration checks.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import math
import os
from pathlib import Path
import re
import statistics
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get('SEAPOINT_TEST_URL', 'http://127.0.0.1:8784').rstrip('/')
OUTPUT = Path(os.environ.get('SEAPOINT_MOTION_TEST_OUTPUT', ROOT / 'test-output'))
OUTPUT.mkdir(parents=True, exist_ok=True)
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
ASSET_CACHE = {}

HARNESS = r'''<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;background:#000;color:white}canvas{display:block;width:256px;height:256px}#source{display:none}</style>
<script src="/rain_motion.js"></script><canvas id="output" width="256" height="256"></canvas>
<script>
const canvas=document.getElementById('output');
function fixture(cx=80,cy=128,side=256){
 const c=document.createElement('canvas');c.width=c.height=side;
 const ctx=c.getContext('2d'), data=ctx.createImageData(side,side);
 for(let y=0;y<side;y++)for(let x=0;x<side;x++){
  const dx=(x-cx)/7,dy=(y-cy)/11, r=dx*dx+dy*dy;
  const alpha=r<15?Math.round(255*Math.exp(-r/2)):0;
  const i=(y*side+x)*4;
  if(alpha){data.data[i]=245;data.data[i+1]=70+Math.round(25*Math.exp(-r));data.data[i+2]=30;data.data[i+3]=alpha;}
 }
 return data;
}
function png(data){const c=document.createElement('canvas');c.width=data.width;c.height=data.height;c.getContext('2d').putImageData(data,0,0);return c.toDataURL('image/png');}
function create(){window.motion=SeaPointRainMotion.createRenderer(canvas,{workingSize:128,gridSize:16,maxDisplacement:20,cacheSize:4});return {supported:motion.supported,stats:motion.stats};}
async function prepare(a,b,key='translation'){window.frameA=fixture(a);window.frameB=fixture(b);return await motion.preparePair(frameA,frameB,key);}
function draw(t){const ok=motion.render(t);return {ok,png:canvas.toDataURL('image/png'),stats:motion.stats};}
</script>'''


def fixture_png(index=0, side=256):
    """A translated coloured Gaussian; no forecast fixtures enter the backend."""
    cx = (80 + index * 4) if side == 256 else (280 + index * 6)
    cy = 128 if side == 256 else 294
    sigma_x, sigma_y = ((7, 11) if side == 256 else (18, 28))
    image = Image.new('RGBA', (side, side))
    pixels = image.load()
    for y in range(max(0, cy - sigma_y * 4), min(side, cy + sigma_y * 4 + 1)):
        for x in range(max(0, cx - sigma_x * 4), min(side, cx + sigma_x * 4 + 1)):
            r = ((x - cx) / sigma_x) ** 2 + ((y - cy) / sigma_y) ** 2
            alpha = round(255 * math.exp(-r / 2)) if r < 15 else 0
            if alpha:
                pixels[x, y] = (245, 70 + round(25 * math.exp(-r)), 30, alpha)
    output = BytesIO()
    image.save(output, 'PNG')
    return output.getvalue()


@contextmanager
def fixture_server(extra_images=None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith('/harness'):
                content, kind = HARNESS.encode(), 'text/html'
            elif self.path.split('?')[0] == '/rain_motion.js':
                content, kind = (ROOT / 'rain_motion.js').read_bytes(), 'text/javascript'
            elif extra_images and self.path.split('?')[0] in extra_images:
                content, kind = extra_images[self.path.split('?')[0]], 'image/png'
            elif self.path.startswith('/real-forecast/'):
                name = self.path.rsplit('/', 1)[-1]
                content, kind = (ROOT / 'tests' / 'real-forecast' / name).read_bytes(), 'image/png'
            elif self.path.startswith('/radar-'):
                parts = self.path.split('/')
                content, kind = fixture_png(int(parts[2])), 'image/png'
            else:
                content, kind = PNG, 'image/png'
            self.send_response(200)
            if self.path.startswith('/radar-cors/'):
                self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()


def png_image(url):
    return Image.open(BytesIO(base64.b64decode(url.split(',', 1)[1]))).convert('RGBA')


def premultiplied_difference(first, second):
    """Compare visible RGBA; unpremultiplication can round tiny-alpha RGB."""
    worst_alpha = worst_color = 0
    first_pixels = first.get_flattened_data() if hasattr(first, 'get_flattened_data') else first.getdata()
    second_pixels = second.get_flattened_data() if hasattr(second, 'get_flattened_data') else second.getdata()
    for a, b in zip(first_pixels, second_pixels):
        worst_alpha = max(worst_alpha, abs(a[3] - b[3]))
        for channel in range(3):
            worst_color = max(worst_color, abs(a[channel] * a[3] / 255 - b[channel] * b[3] / 255))
    return worst_alpha, worst_color


def strong_components(image, threshold=140):
    alpha = image.getchannel('A')
    remaining = {(x, y) for y in range(image.height) for x in range(image.width)
                 if alpha.getpixel((x, y)) >= threshold}
    components = []
    while remaining:
        todo = [remaining.pop()]
        points = []
        while todo:
            x, y = todo.pop()
            points.append((x, y))
            for neighbour in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    todo.append(neighbour)
        if len(points) >= 4:
            components.append(points)
    return components


def check_module(browser, fixture_base):
    page = browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(fixture_base + '/harness', wait_until='load')
    created = page.evaluate('create()')
    assert created['supported'], created
    started = time.monotonic()
    assert page.evaluate('prepare(80,112)'), page.evaluate('motion.stats')
    prepared_ms = (time.monotonic() - started) * 1000
    left = page.evaluate('draw(0)')
    middle = page.evaluate('draw(.5)')
    right = page.evaluate('draw(1)')
    assert left['ok'] and middle['ok'] and right['ok']
    source_left = png_image(page.evaluate('png(frameA)'))
    source_right = png_image(page.evaluate('png(frameB)'))
    for result, source in [(left, source_left), (right, source_right)]:
        difference = premultiplied_difference(png_image(result['png']), source)
        assert difference[0] <= 1 and difference[1] <= 2, difference
    image = png_image(middle['png'])
    components = strong_components(image)
    assert len(components) == 1, {'components': len(components), 'stats': middle['stats']}
    center = sum(x for x, _ in components[0]) / len(components[0])
    assert abs(center - 96) <= 4, {'center': center, 'stats': middle['stats']}
    alpha = image.getchannel('A')
    assert alpha.getpixel((96, 128)) >= 150, {'center_alpha': alpha.getpixel((96, 128)), 'stats': middle['stats']}
    assert max(alpha.getpixel((80, 128)), alpha.getpixel((112, 128))) < 110
    image.save(OUTPUT / 'motion-translated-midpoint.png')
    page.evaluate('draw(.5)')
    page.screenshot(path=str(OUTPUT / 'motion-translated-mobile.png'))
    print(f'PASS translated rain forms one midpoint feature, not two fade ghosts; preparation {prepared_ms:.1f} ms', flush=True)

    assert page.evaluate('prepare(96,96,"stationary")')
    static_start = png_image(page.evaluate('draw(0).png'))
    static_middle = png_image(page.evaluate('draw(.5).png'))
    assert premultiplied_difference(static_start, static_middle)[0] <= 1
    assert premultiplied_difference(static_start, static_middle)[1] <= 2
    print('PASS stationary rain does not dim midway through premultiplied interpolation', flush=True)

    for index in range(7):
        assert page.evaluate('(i)=>prepare(80+i,100+i,"bounded-"+i)', index)
        assert page.evaluate('motion.stats.cacheSize') <= 4, page.evaluate('motion.stats')
    timings = page.evaluate('''() => {
      const samples=[];
      for(let i=0;i<45;i++){
        const start=performance.now();motion.render((i%15)/14);
        const gl=canvas.getContext('webgl2')||canvas.getContext('webgl');if(gl)gl.finish();
        samples.push(performance.now()-start);
      }
      return samples;
    }''')
    ordered = sorted(timings)
    print(f'PASS pair cache bounded to4; mobile-viewport software-GPU render median {statistics.median(timings):.2f} ms, p95 {ordered[int(.95*(len(ordered)-1))]:.2f} ms (cloud browser, not phone hardware)', flush=True)
    if (ROOT / 'tests' / 'real-forecast' / '0.png').exists():
        actual = page.evaluate('''async () => {
          async function pixels(url){
            const image=new Image();image.src=url;await image.decode();
            const c=document.createElement('canvas');c.width=image.naturalWidth;c.height=image.naturalHeight;
            const ctx=c.getContext('2d',{willReadFrequently:true});ctx.drawImage(image,0,0);
            return ctx.getImageData(0,0,c.width,c.height);
          }
          window.realA=await pixels('/real-forecast/0.png');window.realB=await pixels('/real-forecast/1.png');
          const began=performance.now();const ok=await motion.preparePair(realA,realB,'actual-GFS');
          return {ok,elapsed:performance.now()-began,stats:motion.stats};
        }''')
        assert actual['ok'], actual
        for stamp,t,source in [('start',0,'realA'),('midpoint',.5,None),('end',1,'realB')]:
            rendered=page.evaluate('(t)=>draw(t)',t)
            assert rendered['ok'],rendered
            result=png_image(rendered['png'])
            assert result.getchannel('A').getbbox() is not None
            if source:
                reference=png_image(page.evaluate('(name)=>png(window[name])',source))
                difference=premultiplied_difference(result,reference)
                assert difference[0]<=1 and difference[1]<=2,difference
            result.save(OUTPUT/f'motion-real-GFS-{stamp}.png')
        page.evaluate('draw(.5)')
        page.screenshot(path=str(OUTPUT/'motion-real-GFS-mobile.png'))
        print(f"PASS actual cached GFS640 rain fields render with original endpoints; {actual['stats']['mode']} mode, matching fraction {actual['stats']['matchedFraction']:.3f}, worker preparation {actual['elapsed']:.1f} ms",flush=True)
    assert not errors, errors
    page.evaluate('motion.dispose()')
    page.close()

    unsupported = browser.new_page(viewport={'width': 390, 'height': 844})
    unsupported.add_init_script('''(() => {
      const original=HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext=function(type,...args){
        return String(type).startsWith('webgl')?null:original.call(this,type,...args);
      };
    })();''')
    unsupported.goto(fixture_base + '/harness', wait_until='load')
    result = unsupported.evaluate('create()')
    assert result['supported'] is False, result
    assert unsupported.evaluate('motion.render(.5)') is False
    unsupported.close()
    print('PASS missing WebGL reports unsupported instead of fabricating movement', flush=True)


def external_asset(route):
    url = route.request.url
    origin = route.request.headers.get('origin','')
    cache_key = (url,origin)
    try:
        if cache_key not in ASSET_CACHE:
            request_headers = {'User-Agent':'SeaPoint-browser-motion/1.0','Referer':BASE_URL+'/'}
            if origin:
                request_headers['Origin'] = origin
            request = Request(url,headers=request_headers)
            try:
                response = urlopen(request, timeout=25)
            except HTTPError as error:
                response = error
            with response:
                ASSET_CACHE[cache_key] = (response.status, response.read(),
                    {name: value for name, value in response.headers.items()
                     if name.lower() in ('content-type', 'access-control-allow-origin',
                                         'access-control-allow-credentials', 'vary')})
        status, data, headers = ASSET_CACHE[cache_key]
        route.fulfill(status=status, body=data, headers=headers)
    except Exception:
        route.abort()


def open_radar_fixture(browser, fixture_base, cors=True, forecast_gap=False, webgl=True, forecast_images=None):
    page = browser.new_page(viewport={'width':390,'height':844}, device_scale_factor=2)
    page.test_errors = []
    page.on('pageerror', lambda error: page.test_errors.append(str(error)))
    if not webgl:
        page.add_init_script('''(() => {
          const original=HTMLCanvasElement.prototype.getContext;
          HTMLCanvasElement.prototype.getContext=function(type,...args){
            return String(type).startsWith('webgl')?null:original.call(this,type,...args);
          };
        })();''')
    page.route(re.compile(r'https://.*'), external_asset)
    now = time.time()
    latest = int(now // 600 * 600)
    observed = [{'time':latest-(7-i)*600,'path':f'/radar-{ "cors" if cors else "no-cors"}/{i}'} for i in range(8)]
    first_hour = int(now // 3600 * 3600) + (3600 if forecast_gap else 0)
    future = [{'time':first_hour+i*3600,'url':f'/fixture-forecast/{i}.png'} for i in range(51)]
    page.route('**/radar-frames',lambda route:route.fulfill(json={'host':fixture_base,'frames':observed}))
    page.route('**/forecast-frames',lambda route:route.fulfill(json={
        'status':'ready','source':'NOAA GFS','units':'mm/h','model_run':int(now-6*3600),
        'fetched_at':int(now),'resolution_km':28,'bounds':[[10,-68],[23,-55]],'frames':future}))
    images = {f'/fixture-forecast/{i}.png':
              (forecast_images or {}).get(i) or fixture_png(i,640) for i in range(51)}
    page.route('**/fixture-forecast/*.png',lambda route:route.fulfill(body=images[urlsplit(route.request.url).path],content_type='image/png'))
    page.route('**/basemap-style',lambda route:route.fulfill(json={
        'version':8,'sources':{},'layers':[{'id':'test-background','type':'background','paint':{'background-color':'#183d63'}}]}))
    page.route('https://server.arcgisonline.com/**',lambda route:route.fulfill(body=PNG,content_type='image/png'))
    page.goto(BASE_URL+'/radar?lat=17.12&lon=-61.8&name=Motion%20test',wait_until='domcontentloaded',timeout=60000)
    page.wait_for_function('radarFrames.length===8&&predictionFrames.length>=48&&!document.getElementById("play").disabled',timeout=60000)
    page.wait_for_function('typeof window.seapointMotionState==="function"',timeout=10000)
    return page, observed, future


def scrub(page, value):
    page.locator('#timeline').evaluate('(e,v)=>{e.value=String(v);e.dispatchEvent(new Event("input",{bubbles:true}));}', value)


def canvas_visible(page):
    return page.locator('#rain-motion-canvas').is_visible()


def check_integration(browser, fixture_base):
    page, obs, future = open_radar_fixture(browser,fixture_base)
    latest = obs[-1]['time']
    target = future[4]['time']+1800
    scrub(page,target)
    page.wait_for_function('window.seapointMotionState().state==="moving" && getComputedStyle(document.getElementById("rain-motion-canvas")).display!=="none"',timeout=30000)
    assert page.evaluate('playing') is False
    assert page.evaluate('position') == target
    page.wait_for_timeout(350)
    assert page.evaluate('position') == target
    assert page.evaluate('window.seapointMotionState().kind') == 'forecast'
    assert canvas_visible(page)
    print('PASS paused forecast scrubbing renders interpolated rain at the exact selected timestamp',flush=True)
    for index in range(6,12):
        scrub(page,future[index]['time']+1800)
        page.wait_for_function('window.seapointMotionState().state==="moving"',timeout=30000)
        state=page.evaluate('window.seapointMotionState()')
        assert state['renderer']['cacheSize']<=4,state
        assert state['captureCacheSize']<=24,state
    print('PASS successive forecast pairs retain bounded flow and pixel-image caches',flush=True)

    page.locator('#play').click()
    before = page.evaluate('position')
    center = page.evaluate('[map.getCenter().lat,map.getCenter().lng]')
    page.mouse.move(155,340);page.mouse.down();page.mouse.move(230,405,steps=10);page.mouse.up()
    page.wait_for_timeout(300)
    assert page.evaluate('playing') is True and page.evaluate('position')>before
    assert page.evaluate('[map.getCenter().lat,map.getCenter().lng]')!=center
    for selector in ['#zoom-in','#zoom-out']:
        before=page.evaluate('position');zoom=page.evaluate('map.getZoom()')
        page.locator(selector).click();page.wait_for_timeout(350)
        assert page.evaluate('playing') is True and page.evaluate('position')>before
        assert page.evaluate('map.getZoom()')!=zoom
    page.locator('#play').click()
    page.screenshot(path=str(OUTPUT/'motion-map-mobile.png'))
    print('PASS pan and zoom retain uninterrupted timelapse playback',flush=True)

    scrub(page,latest)
    assert page.evaluate('mapStatus') == 'OBSERVED'
    assert not canvas_visible(page), page.evaluate('window.seapointMotionState()')
    scrub(page,latest+1)
    assert page.evaluate('mapStatus') == 'FORECAST'
    state=page.evaluate('window.seapointMotionState()')
    assert 'observed' not in json.dumps(state.get('pair','')),state
    print('PASS exact observations use real frames and source handoff does not morph radar into model data',flush=True)
    assert not page.test_errors,page.test_errors
    page.close()

    gap,gap_obs,_=open_radar_fixture(browser,fixture_base,forecast_gap=True)
    scrub(gap,gap_obs[-1]['time']+60)
    assert gap.evaluate('mapStatus') == 'GAP'
    assert not canvas_visible(gap)
    assert gap.locator('#notice').is_visible()
    gap.close()
    print('PASS coverage gaps never receive synthetic in-between rain',flush=True)

    for args,label in [({'webgl':False},'WebGL unavailable'),({'cors':False},'CORS pixel access denied')]:
        fallback, fallback_obs, _=open_radar_fixture(browser,fixture_base,**args)
        scrub(fallback,fallback_obs[2]['time']+300)
        fallback.wait_for_timeout(1800)
        assert fallback.evaluate('mapStatus')=='OBSERVED'
        assert not canvas_visible(fallback),fallback.evaluate('window.seapointMotionState()')
        visible=fallback.evaluate('Array.from(loaded.values()).filter(layer=>layer.options.opacity>0).length')
        assert visible==2,{'visible':visible,'state':fallback.evaluate('window.seapointMotionState()')}
        assert fallback.evaluate('window.seapointMotionState().state')=='blending'
        opacities=[]
        for fraction in [.49,.51]:
            scrub(fallback,fallback_obs[2]['time']+600*fraction)
            opacities.append(fallback.evaluate('Array.from(loaded.values()).filter(layer=>layer.options.opacity>0).map(layer=>layer.options.opacity)'))
        assert all(len(pair)==2 for pair in opacities),opacities
        assert max(abs(a-b) for a,b in zip(*opacities))<.03,opacities
        scrub(fallback,fallback_obs[2]['time'])
        assert fallback.evaluate('Array.from(loaded.values()).filter(layer=>layer.options.opacity>0).length')==1
        scrub(fallback,fallback_obs[2]['time']+300)
        fallback.locator('#play').click();before=fallback.evaluate('position')
        fallback.wait_for_function('(before)=>playing&&position>before',arg=before,timeout=4000)
        assert fallback.evaluate('playing') is True and fallback.evaluate('position')>before, fallback.evaluate('({playing,position,state:seapointMotionState()})')
        fallback.close()
        print(f'PASS {label}: two real rain layers blend smoothly and playback continues',flush=True)


def main():
    with fixture_server() as fixture_base, sync_playwright() as playwright:
        browser=playwright.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,
            args=['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
        check_module(browser,fixture_base)
        if os.environ.get('SEAPOINT_MOTION_MODULE_ONLY')!='1':
            check_integration(browser,fixture_base)
        browser.close()
    print('PASS rain-motion browser checks completed',flush=True)


if __name__=='__main__':
    main()
