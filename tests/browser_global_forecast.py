"""World delivery, regional masking, longitude wrap, retries and memory bounds.

All rain is explicit test-only data: a global red field and a dry regional field.
This isolates geography and delivery from whether a real city is rainy today.
"""
from io import BytesIO
import json,os,re,sys,time
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright
from browser_motion import PNG,external_asset,fixture_server,scrub
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from radar_view import radar_page
OUT=ROOT/'test-output/global';OUT.mkdir(parents=True,exist_ok=True)

def encoded(size,color):
 out=BytesIO();Image.new('RGBA',size,color).save(out,format='PNG');return out.getvalue()


def main():
 now=time.time();run=int((now-6*3600)//21600*21600);first=int(now//3600*3600)
 cycle=time.strftime('%Y%m%d%H',time.gmtime(run));frames=[]
 for i in range(50):
  stamp=first+i*3600;hour=(stamp-run)//3600;regional=hour<=48
  frames.append({'time':stamp,'url':f'/region/{i}.png','provider':'arome-antilles'if regional else'noaa-gfs','model_run':run,'bounds':[[10,-68],[22.9 if regional else 23,-55]],'resolution_km':2.5 if regional else 28,
   'global_tiles':{'url_template':f'data/world/{cycle}-{hour:03d}-g1/{{z}}/{{x}}/{{y}}.png','model_run':run,'fetched_at':int(now),'units':'mm/h','max_zoom':4,'tile_size':256}})
 red=encoded((256,256),(220,30,50,200));clear=encoded((640,640),(0,0,0,0))
 state={'fail':False};requests=[];errors=[]
 with fixture_server()as base,sync_playwright()as p:
  browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
  page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
  page.on('pageerror',lambda error:errors.append(str(error)))
  page.on('request',lambda request:requests.append(request.url))
  page.route(re.compile(r'https://.*'),external_asset)
  for name,entry in json.loads((ROOT/'static_site/vendor.json').read_text()).items():
   file=Path(os.environ.get('SEAPOINT_STATIC_SITE',ROOT/'_site'))/'vendor'/name
   if name.endswith(('.js','.css'))and file.exists():
    def local_asset(path):return lambda r:r.fulfill(body=path.read_bytes(),content_type='text/css'if path.suffix=='.css'else'text/javascript')
    page.route(entry['url'],local_asset(file))
  page.route('**/radar?*',lambda r:r.fulfill(body=radar_page(17.12,-61.8,'World test'),content_type='text/html'))
  page.route('**/rain-motion.js?*',lambda r:r.fulfill(body=(ROOT/'rain_motion.js').read_bytes(),content_type='text/javascript'))
  page.route('**/global-rain.js?*',lambda r:r.fulfill(body=(ROOT/'global_rain.js').read_bytes(),content_type='text/javascript'))
  page.route('**/radar-frames',lambda r:r.fulfill(json={'host':base,'frames':[]}))
  page.route('**/forecast-frames',lambda r:r.fulfill(json={'status':'ready','source':'world fixture','units':'mm/h','model_run':run,'fetched_at':int(now),'bounds':[[10,-68],[22.9,-55]],'forecast_until':int(now+48*3600),'coverage_complete':True,'global_coverage':True,'frames':frames}))
  page.route('**/region/*.png',lambda r:r.fulfill(body=clear,content_type='image/png'))
  def tile(route):
   if state['fail']:route.abort()
   else:route.fulfill(body=red,content_type='image/png')
  page.route('**/data/world/**/*.png',tile)
  page.route('**/basemap-style',lambda r:r.fulfill(json={'version':8,'sources':{},'layers':[{'id':'water','type':'background','paint':{'background-color':'#193e5f'}}]}))
  page.route('https://server.arcgisonline.com/**',lambda r:r.fulfill(body=PNG,content_type='image/png'))
  page.goto(base+'/radar?lat=17.12&lon=-61.8',wait_until='commit')
  page.wait_for_function("typeof predictionFrames!=='undefined'&&predictionFrames.length===50&&rainMotionRenderer!==null",timeout=30000)
  def ready():
   page.wait_for_function("seapointMotionState().renderer?.state==='ready'&&!seapointMotionState().buffering&&getComputedStyle(rainMotionOverlay._canvas).display!=='none'",timeout=20000)
  def alpha():
   return page.evaluate("() => {const a=rainMotionRenderer._pair.a;const c=rainMotionOverlay._canvas;const gl=c.getContext('webgl');const p=new Uint8Array(c.width*c.height*4);gl.readPixels(0,0,c.width,c.height,gl.RGBA,gl.UNSIGNED_BYTE,p);let sum=0;for(let i=3;i<p.length;i+=4)sum+=p[i];return sum/(c.width*c.height);}")
  scrub(page,frames[3]['time']+1800);ready()
  assert alpha()<1,'Global rain was left underneath the dry fine regional field'
  initial=[url for url in requests if '/data/world/'in url]
  assert len(initial)<=12,{'startup_world_tile_requests':len(initial)}
  page.evaluate('map.setView([51.5,-.12],6,{animate:false})');ready()
  assert alpha()>180,'Global rain missing in London'
  page.locator('#play').click();old=page.evaluate('position')
  page.evaluate('map.panBy([80,40],{animate:false})')
  page.wait_for_function('(old)=>playing&&position>old',arg=old,timeout=15000)
  page.locator('#play').click();ready()
  results={'regional_dry_field_replaces_global_rain':True,'startup_world_tile_requests':len(initial),'London_global':True,'pan_does_not_pause':True}
  for label,lat,lon,zoom in [('New York',40.7,-74,5),('Sydney',-33.9,151.2,5),('Cape Town',-33.9,18.4,5),('date line',0,179.8,2)]:
   page.evaluate('([lat,lon,z])=>map.setView([lat,lon],z,{animate:false})',[lat,lon,zoom]);ready();assert alpha()>180,label
   assert not page.locator('#notice').is_visible(),(label,page.locator('#notice').inner_text())
   results[label]=True
  urls=[u for u in requests if '/2/'in u and '/data/world/'in u]
  assert any('/2/0/'in u for u in urls)and any('/2/3/'in u for u in urls),'Date-line tile wrapping not exercised'
  page.evaluate('map.setView([40.7,-74],6,{animate:false})');ready()
  for index in range(5,15):
   scrub(page,frames[index]['time']+1800);ready()
  stats=page.evaluate('SeaPointGlobalRain.stats()')
  assert stats['canvases']<=4 and stats['tileCache']<=64 and stats['regionalCache']<=4,stats
  results['bounded_memory']=stats
  state['fail']=True
  scrub(page,frames[18]['time']+1800)
  page.wait_for_function("document.getElementById('notice').textContent.includes('unavailable')",timeout=10000)
  assert page.locator('#notice').is_visible()
  state['fail']=False;page.evaluate('setPlaying(true)');ready()
  page.evaluate('setPlaying(false)');results['missing_tiles_recover_without_claiming_clear']=True
  assert not errors,errors
  results['errors']=errors
  page.screenshot(path=str(OUT/'global-delivery.png'))
  browser.close()
 (OUT/'verification.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))

if __name__=='__main__':main()
