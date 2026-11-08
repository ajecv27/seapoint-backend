import json,os,re
from urllib.request import urlopen,Request
from playwright.sync_api import sync_playwright
base_url=os.environ.get('SEAPOINT_TEST_URL','http://127.0.0.1:8000').rstrip('/')
errors=[]
asset_cache={}
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
 page.on('pageerror',lambda e:errors.append(str(e)))
 # Fetch external assets with the environment's configured CA trust; Chromium
 # has a separate trust store. TLS remains verified by urllib.
 def external(route):
  try:
   url=route.request.url
   if url not in asset_cache:
    with urlopen(Request(url,headers={'User-Agent':route.request.headers.get('user-agent','SeaPoint/1.0'),'Referer':base_url+'/'}),timeout=25) as r:
     asset_cache[url]=(r.status,r.read(),r.headers.get('Content-Type','application/octet-stream'))
   status,body,kind=asset_cache[url]
   route.fulfill(status=status,body=body,content_type=kind)
  except Exception:
   route.abort()
 page.route(re.compile(r'https://.*'),external)
 page.goto(base_url+'/radar?lat=17.12&lon=-61.8&name=Antigua',wait_until='domcontentloaded',timeout=60000)
 page.wait_for_selector('.leaflet-container',timeout=30000)
 page.locator('#forecast').click()
 page.wait_for_function("!document.getElementById('timeline').disabled",timeout=120000)
 print('STATE',json.dumps(page.evaluate("({frames:active.length,first:active[0].time,last:active.at(-1).time,mode:document.getElementById('mode').textContent,detail:document.getElementById('detail').textContent})")))
 page.locator('#play').click()
 before=page.locator('#timeline').input_value()
 page.wait_for_timeout(1800)
 after=page.locator('#timeline').input_value()
 assert int(after)>int(before),(before,after)
 page.locator('#play').click()
 page.locator('#timeline').evaluate("e=>{e.value=e.max;e.dispatchEvent(new Event('input',{bubbles:true}));}")
 assert page.locator('#mode').inner_text()=='FORECAST'
 assert page.locator('#timeline').input_value()==page.locator('#timeline').get_attribute('max')
 assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
 if os.environ.get('RADAR_SCREENSHOT'):
  page.screenshot(path=os.environ['RADAR_SCREENSHOT'],full_page=True)
 print('PASS playback advances, pause, future-time scrubbing, forecast label, mobile width')
 # A failed observation provider must still leave the forecast usable.
 other=browser.new_page(viewport={'width':390,'height':844})
 other.on('pageerror',lambda e:errors.append(str(e)))
 other.route(re.compile(r'https://.*'),external)
 other.route('**/radar-frames',lambda route:route.fulfill(status=503,json={'error':'test outage'}))
 other.goto(base_url+'/radar?lat=17.12&lon=-61.8&name=Antigua',wait_until='domcontentloaded')
 other.wait_for_function("!document.getElementById('timeline').disabled",timeout=90000)
 assert other.locator('#mode').inner_text()=='FORECAST'
 print('PASS observation outage leaves forecast usable')
 other.close()
 # Neither provider returning data must not be presented as clear weather.
 failed=browser.new_page(viewport={'width':390,'height':844})
 failed.on('pageerror',lambda e:errors.append(str(e)))
 failed.route(re.compile(r'https://.*'),external)
 failed.route('**/radar-frames',lambda route:route.fulfill(status=503,json={'error':'test outage'}))
 failed.route('**/forecast-frames',lambda route:route.fulfill(status=503,json={'status':'unavailable','frames':[]}))
 failed.goto(base_url+'/radar?lat=17.12&lon=-61.8&name=Antigua',wait_until='domcontentloaded')
 failed.wait_for_function("document.getElementById('mode').textContent==='UNAVAILABLE'",timeout=30000)
 assert failed.locator('#timeline').is_disabled()
 assert failed.locator('#play').is_disabled()
 assert failed.locator('#clock').inner_text()=='No frames available'
 print('PASS combined outage disables playback and shows unavailable, not dry')
 failed.close()
 print('PAGE ERRORS',errors)
 assert not errors
 browser.close()
