"""Browser regressions for the production 008→009 rain discontinuity.

Uses the original full regional production PNGs, then checks current-pair GPU
isolation, full-field map placement, prefetching and animation-clock buffering.
Run against a local backend with SEAPOINT_TEST_URL; MODULE_ONLY skips the app.
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
from pathlib import Path
from urllib.request import urlopen

from PIL import Image
from playwright.sync_api import sync_playwright

from browser_motion import (
    OUTPUT, fixture_server, open_radar_fixture, png_image,
    premultiplied_difference, scrub,
)


# Provenance: unchanged SeaPoint regional PNG renders of public NOAA GFS PRATE,
# 2026-11-10 18Z model, forecast hours 008/009. These are the two actual source
# frames from the reported production discontinuity. Fetch fixed model URLs and
# pin their bytes; avoid storing production imagery in the source repository.
PRODUCTION_SHA256 = (
    'baae37f6555524eb78057f02b88cfd76c64243c354fc98fd7b7c32454e9befc9',
    'a787530c64bf1fc94ad8577292ff1401c47ba3dd0cad92d4aa5f33185bda26a0',
)


def production_sources():
    local = Path(os.environ.get('SEAPOINT_REGRESSION_FIXTURES','/tmp/radar-visible-diag-b'))
    cache = OUTPUT/'smooth-fixtures'
    cache.mkdir(exist_ok=True)
    source = os.environ.get('SEAPOINT_REGRESSION_SOURCE_URL','https://seapoint-backend.onrender.com').rstrip('/')
    images = {}
    for index,digest in enumerate(PRODUCTION_SHA256):
        filename = f'production-{index+8:03d}.png'
        candidates = [local/filename,local/f'forecast-3-source-{index}.png',cache/filename]
        data = next((p.read_bytes() for p in candidates if p.exists()),None)
        if data is None:
            url = f'{source}/forecast-frame/2026111018-{index+8:03d}.png'
            try:
                with urlopen(url,timeout=30) as response:
                    data=response.read()
            except Exception as error:
                raise RuntimeError('Pinned production regression PNG is unavailable; set '
                    'SEAPOINT_REGRESSION_FIXTURES to the retained diagnostic directory') from error
        assert hashlib.sha256(data).hexdigest()==digest,{'fixture':filename,'error':'Source image bytes changed'}
        (cache/filename).write_bytes(data)
        images[f'/real-forecast/{filename}']=data
    return images


def visible_pixels(image):
    """RGBA in visible premultiplied space; hidden RGB must not count."""
    converted = image.convert('RGBA')
    pixels = converted.get_flattened_data() if hasattr(converted, 'get_flattened_data') else converted.getdata()
    return [(r * a / 255, g * a / 255, b * a / 255, a) for r, g, b, a in pixels]


def mean_visible_difference(a, b):
    aa, bb = visible_pixels(a), visible_pixels(b)
    return sum(abs(x-y) for p, q in zip(aa, bb) for x, y in zip(p, q)) / (4 * len(aa))


def wet_interior_seams(image, jump=30):
    """Count new sharp colour cuts inside opaque rain, excluding cell edges.

    The retained source pair has only 1/2 such adjacent edges. Its broken warp
    had 134; this detects visible rectangular patch seams independently of time
    continuity and permits moderate gradient changes from actual motion.
    """
    pixels=visible_pixels(image)
    width,height=image.size
    pairs=sharp=0
    for y in range(height):
        for x in range(width):
            at=y*width+x
            if pixels[at][3]<=180:continue
            neighbours=[]
            if x+1<width:neighbours.append(at+1)
            if y+1<height:neighbours.append(at+width)
            for other in neighbours:
                if pixels[other][3]<=180:continue
                pairs+=1
                if max(abs(pixels[at][c]-pixels[other][c]) for c in range(3))>jump:sharp+=1
    return {'sharp_edges':sharp,'wet_pairs':pairs,'rate':sharp/max(1,pairs)}


def blend_image(a, b, t):
    pixels = []
    for aa, bb in zip(visible_pixels(a), visible_pixels(b)):
        values = [(1-t)*x+t*y for x, y in zip(aa, bb)]
        alpha = values[3]
        pixels.append(tuple(round(v*255/alpha) if alpha else 0 for v in values[:3]) + (round(alpha),))
    image = Image.new('RGBA', a.size)
    image.putdata(pixels)
    return image


def wait_rendered(page):
    page.wait_for_function('''() => {
      const s=seapointMotionState();
      return ['moving','stationary','blending'].includes(s.state) && !s.buffering &&
        getComputedStyle(document.getElementById('rain-motion-canvas')).display!=='none';
    }''', timeout=30000)


LOAD_REAL = r'''async () => {
  async function imageData(name){
    const image=new Image();image.src='/real-forecast/'+name;await image.decode();
    const c=document.createElement('canvas');c.width=image.naturalWidth;c.height=image.naturalHeight;
    const ctx=c.getContext('2d',{willReadFrequently:true});ctx.drawImage(image,0,0);
    return ctx.getImageData(0,0,c.width,c.height);
  }
  window.realA=await imageData('production-008.png');
  window.realB=await imageData('production-009.png');
  window.realC=await imageData('2.png');
  motion=SeaPointRainMotion.createRenderer(canvas,{cacheSize:4});
  const begin=performance.now();
  const ok=await motion.preparePair(realA,realB,'production-008-009');
  return {ok,elapsed:performance.now()-begin,stats:motion.stats,
    work:[motion._pair.motion.width,motion._pair.motion.height],
    grid:[motion._pair.motion.gridWidth,motion._pair.motion.gridHeight]};
}'''


def check_production_pair(browser, fixture_base):
    page = browser.new_page(viewport={'width':390,'height':844})
    page.goto(fixture_base+'/harness', wait_until='load')
    result = page.evaluate(LOAD_REAL)
    assert result['ok'] and result['stats']['worker'], result
    assert result['work'] == [256,256] and result['grid'] == [64,64], result
    assert result['stats']['mode'] == 'motion' and result['stats']['matchedFraction'] > .1, result
    sources = [png_image(page.evaluate('png(realA)')),png_image(page.evaluate('png(realB)'))]
    frames = {}
    for value in [0,.25,.49,.5,.51,.75,1]:
        rendered = page.evaluate('(t)=>draw(t)',value)
        assert rendered['ok'], rendered['stats']
        frames[value] = png_image(rendered['png'])
    for value, source in [(0,sources[0]),(1,sources[1])]:
        difference = premultiplied_difference(frames[value],source)
        assert difference[0]<=1 and difference[1]<=2, difference
    endpoint_change = mean_visible_difference(*sources)
    midpoint_change = mean_visible_difference(frames[.49],frames[.51])
    step_ratio = midpoint_change/endpoint_change
    assert .001 < step_ratio < .18, {'49_51_ratio':step_ratio,'stats':result}
    # A static fade is continuous too. Real matched features must also warp.
    warp_change = mean_visible_difference(frames[.5],blend_image(*sources,.5))
    warp_ratio = warp_change/endpoint_change
    assert warp_ratio > .025, {'warp_vs_static_blend_ratio':warp_ratio,'stats':result}
    assert mean_visible_difference(frames[.25],frames[.75]) > midpoint_change * 4
    for value,label in [(.49,'49'),(.5,'50'),(.51,'51')]:
        frames[value].save(OUTPUT/f'smooth-production-{label}.png')
    print(f"PASS actual GFS008→009 full-field endpoints; 49→51 change {step_ratio:.3f} of endpoint change; motion-vs-fade signal {warp_ratio:.3f}; worker {result['elapsed']:.1f}ms",flush=True)

    seams=wet_interior_seams(frames[.5])
    assert seams['rate']<.00045,{'error':'New sharp seams inside wet rain patches','seams':seams}
    print(f"PASS real midpoint preserves smooth rain interiors: {seams['sharp_edges']} sharp edges / {seams['wet_pairs']} wet adjacent pairs",flush=True)

    # A prefetch may fill the worker/cache but must not change the current GPU.
    prefetch = page.evaluate('''async () => {
      motion.render(.49);const before=canvas.toDataURL();const current=motion.stats;
      const compute=motion._compute.bind(motion);let computations=0;
      motion._compute=(...args)=>{computations++;return compute(...args);};
      const task=motion.prefetchPair(realB,realC,'next-009-010');
      const during=motion.stats;motion.render(.49);const unchangedDuring=before===canvas.toDataURL();
      const ok=await task;motion.render(.49);const unchangedAfter=before===canvas.toDataURL();
      const after=motion.stats;
      const activated=await motion.preparePair(realB,realC,'next-009-010');
      return {ok,activated,computations,current,during,after,unchangedDuring,unchangedAfter,final:motion.stats};
    }''')
    assert prefetch['ok'] and prefetch['activated'] and prefetch['computations']==1, prefetch
    assert prefetch['unchangedDuring'] and prefetch['unchangedAfter'], prefetch
    assert prefetch['during']['pending'] is False, prefetch
    assert prefetch['during']['key'] == prefetch['after']['key'] == prefetch['current']['key'],prefetch
    assert prefetch['after']['cacheSize'] <= 4 and prefetch['final']['key']=='next-009-010',prefetch
    print('PASS next-pair prefetch preserves current GPU pixels/key and activates the cached worker result once',flush=True)

    # Global and local unmatched pixels both use continuous premultiplied
    # blending. The lower cell is independently matched and must still move.
    unmatched = page.evaluate('''async () => {
      const a=fixture(80),b=fixture(96),extra=fixture(200,40);
      for(let i=0;i<a.data.length;i+=4)if(extra.data[i+3])
        for(let c=0;c<4;c++)a.data[i+c]=extra.data[i+c];
      const localOK=await motion.preparePair(a,b,'local-unmatched');
      motion.render(.49);const left=canvas.toDataURL();motion.render(.51);const right=canvas.toDataURL();
      const local={ok:localOK,stats:motion.stats,left,right};
      const globalOK=await motion.preparePair(fixture(35),fixture(220),'global-unmatched');
      motion.render(.49);const globalLeft=canvas.toDataURL();motion.render(.51);const globalRight=canvas.toDataURL();
      return {local,global:{ok:globalOK,stats:motion.stats,left:globalLeft,right:globalRight}};
    }''')
    for label,point in [('local',(200,40)),('global',(35,128))]:
        case=unmatched[label]
        assert case['ok'],case['stats']
        if label=='local':assert case['stats']['mode']=='motion',case['stats']
        else:assert case['stats']['mode']=='blend',case['stats']
        aa=png_image(case['left']).getchannel('A').getpixel(point)
        bb=png_image(case['right']).getchannel('A').getpixel(point)
        assert 90<aa<170 and 90<bb<170 and abs(aa-bb)<12,{'case':label,'alpha49':aa,'alpha51':bb}
    local_alpha=png_image(unmatched['local']['right']).getchannel('A')
    assert local_alpha.getpixel((88,128))>150
    print('PASS globally unmatched fields and local unmatched rain blend continuously while a matched neighbour moves',flush=True)

    # The older async completion must not upload old textures after a scrub.
    superseded = page.evaluate('''async () => {
      const old=motion.preparePair(fixture(45),fixture(65),'stale-old');
      const fresh=motion.preparePair(fixture(150),fixture(170),'fresh-current');
      const results=await Promise.all([old,fresh]);motion.render(.5);
      return {results,key:motion.stats.key,png:canvas.toDataURL()};
    }''')
    assert superseded['results']==[False,True] and superseded['key']=='fresh-current',superseded['results']
    image=png_image(superseded['png'])
    alpha=image.getchannel('A')
    assert alpha.getpixel((160,128))>140 and alpha.getpixel((55,128))<20
    page.evaluate('motion.dispose()')
    page.close()
    print('PASS superseded pair completion cannot replace the latest selected pair textures',flush=True)


def inspect_field(page):
    return page.evaluate('''() => {
      const s=seapointMotionState(), b=rainMotionOverlay._bounds;
      const nw=map.latLngToLayerPoint(b.getNorthWest()),se=map.latLngToLayerPoint(b.getSouthEast());
      const canvas=rainMotionOverlay._canvas,at=L.DomUtil.getPosition(canvas);
      return {state:s,bounds:[[b.getSouth(),b.getWest()],[b.getNorth(),b.getEast()]],
        dimensions:[canvas.width,canvas.height],work:[rainMotionRenderer._pair.motion.width,rainMotionRenderer._pair.motion.height],
        grid:[rainMotionRenderer._pair.motion.gridWidth,rainMotionRenderer._pair.motion.gridHeight],
        placementError:Math.max(Math.abs(at.x-nw.x),Math.abs(at.y-nw.y),
          Math.abs(parseFloat(canvas.style.width)-(se.x-nw.x)),Math.abs(parseFloat(canvas.style.height)-(se.y-nw.y))),
        png:canvas.toDataURL()};
    }''')


def check_full_map_and_prefetch(browser, fixture_base, sources):
    page, _, future = open_radar_fixture(browser,fixture_base,forecast_images={
        12:sources['/real-forecast/production-008.png'],13:sources['/real-forecast/production-009.png']})
    target=future[12]['time']+1800
    scrub(page,target);wait_rendered(page)
    reference=inspect_field(page)
    for lat,lon,zoom,label in [(17.12,-61.8,10.5,'Antigua'),(16.2,-61.5,9,'other-coast'),(13.2,-60.3,7.5,'southern-rain'),(17,-61.5,6,'regional')]:
        page.evaluate('([lat,lon,zoom])=>map.setView([lat,lon],zoom,{animate:false})',[lat,lon,zoom])
        wait_rendered(page)
        current=inspect_field(page)
        assert current['bounds']==[[10,-68],[23,-55]],current
        assert current['dimensions']==[640,640] and current['work']==[256,256] and current['grid']==[64,64],current
        assert current['placementError']<=1,current['placementError']
        assert current['state']['pair']==reference['state']['pair'],current['state']
        assert current['png']==reference['png'],{'view':label,'state':current['state']}
        assert page.evaluate('playing') is False and page.evaluate('position')==target
        page.screenshot(path=str(OUTPUT/f'smooth-full-field-{label}.png'))
    print('PASS original full regional field/bounds/pair/GPU pixels stay stable across Antigua, another coast, southern rain and zoom6',flush=True)

    # Use real playback to trigger the app's one-pair-ahead cache path.
    scrub(page,future[12]['time']+100);wait_rendered(page)
    prefetch=page.evaluate('''() => {
      const a=predictionFrames.find(f=>f.time===position-position%3600),i=predictionFrames.indexOf(a);
      const b=predictionFrames[i+1],c=predictionFrames[i+2];
      window.testNextKey=motionPairKey(b,c);window.testCurrentKey=seapointMotionState().pair;
      return {next:testNextKey,current:testCurrentKey};
    }''')
    page.locator('#play').click()
    page.wait_for_function('rainMotionRenderer._cache.has(testNextKey)',timeout=15000)
    page.locator('#play').click()
    assert page.evaluate('rainMotionRenderer.stats.key')==prefetch['current'],prefetch
    assert page.evaluate('rainMotionRenderer.stats.cacheSize')<=4
    print('PASS playing app computes the following pair into its bounded cache before the current hour ends',flush=True)
    assert not page.test_errors,page.test_errors
    page.close()


def check_buffered_clock(browser, fixture_base):
    page,_,future=open_radar_fixture(browser,fixture_base)
    # Force a slow field calculation and a missed prefetch, as on a slow device.
    # Images remain actual loaded source pairs and computation stays in a worker.
    page.evaluate('''() => {
      const compute=rainMotionRenderer._compute.bind(rainMotionRenderer);
      rainMotionRenderer._compute=(...args)=>new Promise(resolve=>setTimeout(resolve,700)).then(()=>compute(...args));
      rainMotionRenderer.prefetchPair=async()=>false;
    }''')
    start=future[20]['time']+3400
    scrub(page,start);wait_rendered(page)
    page.evaluate('''() => {
      window.clockSamples=[];window.clockSampleEnd=performance.now()+7000;
      const watch=ms=>{const s=seapointMotionState();clockSamples.push({ms,position,playing,buffering:s.buffering,key:s.renderer.key});
        if(performance.now()<clockSampleEnd)requestAnimationFrame(watch);};requestAnimationFrame(watch);
    }''')
    page.locator('#play').click()
    page.wait_for_timeout(6900)
    page.locator('#play').click()
    samples=page.evaluate('clockSamples')
    live=[s for s in samples if s['playing']]
    assert len(live)>20, len(live)
    assert max(s['position'] for s in live)>=future[22]['time'],{'start':start,'last':live[-1]}
    assert len({s['key'] for s in live if s['key']})>=3
    buffers=[s for s in live if s['buffering']]
    assert len(buffers)>4,live
    for a,b in zip(live,live[1:]):
        advance=b['position']-a['position']
        assert advance>=0,{'previous':a,'next':b}
        assert advance<=min(b['ms']-a['ms'],100)*2.16+5,{'previous':a,'next':b}
    stalled=False
    for index,a in enumerate(buffers):
        for b in buffers[index+1:]:
            if b['ms']-a['ms']>=400 and abs(b['position']-a['position'])<.01:
                stalled=True;break
        if stalled:break
    assert stalled,{'buffers':buffers[:8]}
    intervals=[b['ms']-a['ms'] for a,b in zip(live,live[1:])]
    print(f'PASS 700ms cold-pair buffer keeps Play active, freezes model time, resumes without catch-up and crosses two hourly boundaries; RAF median {statistics.median(intervals):.1f}ms',flush=True)
    (OUTPUT/'smooth-buffer-clock.json').write_text(json.dumps(samples,indent=2))
    assert not page.test_errors,page.test_errors
    page.close()


def check_delayed_observed_tiles(browser, fixture_base):
    page,observed,_=open_radar_fixture(browser,fixture_base)
    scrub(page,observed[3]['time']+300);wait_rendered(page)
    page.wait_for_function('motionJob===null')
    page.evaluate('''() => {
      window.observedCaptures=[];
      const capture=captureRainFrame;
      captureRainFrame=async(...args)=>{
        const result=await capture(...args);
        if(args[0].kind==='observed')observedCaptures.push({frame:key(args[0]),
          loading:args[1].isLoading(),alpha:result.pixels.data.reduce((n,v,i)=>n+(i%4===3?v:0),0)});
        return result;
      };
    }''')
    pattern=fixture_base+'/radar-cors/**'
    for action,label in [('map.setView([17,-61.5],6,{animate:false})','zoom'),
                         ('map.panBy([300,0],{animate:false})','partial pan')]:
        held=[]
        def hold(route):
            held.append(route)
        page.route(pattern,hold)
        previous=page.evaluate('seapointMotionState().pair')
        page.evaluate('() => {observedCaptures=[];'+action+';}')
        page.wait_for_timeout(1300)
        assert held,{'action':label,'error':'No new source tiles requested'}
        waiting=page.evaluate('({state:seapointMotionState(),captures:observedCaptures,job:!!motionJob,failed:motionFailures.has(motionWanted.id)})')
        page.unroute(pattern,hold)
        for route in held:
            route.continue_()
        assert waiting['captures']==[],{'action':label,'waiting':waiting}
        assert waiting['job'] is True and waiting['failed'] is False,{'action':label,'waiting':waiting}
        wait_rendered(page)
        page.wait_for_function('motionJob===null')
        restored=page.evaluate('({state:seapointMotionState(),captures:observedCaptures,failed:motionFailures.has(motionWanted.id)})')
        assert restored['state']['pair']!=previous and restored['failed'] is False,{'action':label,'restored':restored}
        assert len(restored['captures'])>=2 and not any(c['loading'] for c in restored['captures']),restored
        if label=='partial pan':
            assert sum(c['alpha'] for c in restored['captures'])>0,restored
        assert page.evaluate('playing') is False
    assert not page.test_errors,page.test_errors
    page.close()
    print('PASS observed zoom/partial-pan await source tiles held 1.3s, then capture the complete current view without a 60s fallback lock',flush=True)


def main():
    sources=production_sources()
    with fixture_server(sources) as fixture_base,sync_playwright() as playwright:
        browser=playwright.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,
            args=['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
        check_production_pair(browser,fixture_base)
        if os.environ.get('SEAPOINT_MOTION_MODULE_ONLY')!='1':
            check_full_map_and_prefetch(browser,fixture_base,sources)
            check_buffered_clock(browser,fixture_base)
            check_delayed_observed_tiles(browser,fixture_base)
        browser.close()
    print('PASS production smooth-flow browser regressions completed',flush=True)


if __name__=='__main__':
    main()
