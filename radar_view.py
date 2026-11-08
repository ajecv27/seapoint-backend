"""Embedded radar/forecast player shared by the existing Flutter WebView."""
import json


def radar_page(latitude, longitude, location_name):
    config = json.dumps(dict(lat=latitude, lon=longitude, name=location_name)).replace('<', '\\u003c')
    return HTML.replace('__CONFIG__', config)


HTML = r'''<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SeaPoint Rain Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
*{box-sizing:border-box}html,body{height:100%;margin:0;font-family:Arial,sans-serif;color:#183b50}
body{display:flex;flex-direction:column;background:#eef5f8}header,footer{padding:10px 12px;background:#fff;z-index:500}
header{box-shadow:0 1px 5px #0002}h1{font-size:16px;margin:0 0 8px}#map{height:100%;width:100%}
.map-wrap{position:relative;flex:1;min-height:160px}.notice{position:absolute;top:12px;left:50%;transform:translateX(-50%);z-index:450;background:#fffffff0;padding:8px 12px;border-radius:12px;font-size:12px;width:max-content;max-width:85%;text-align:center;pointer-events:none}
.row{display:flex;gap:8px;align-items:center}button{border:1px solid #b5ced9;background:white;border-radius:20px;color:#174b60;padding:8px 12px;cursor:pointer;font-size:13px}
button.active{background:#087d9d;color:white;border-color:#087d9d}button:disabled{opacity:.5;cursor:default}
#play{height:44px;width:44px;flex-shrink:0;background:#087d9d;color:white;font-size:18px;border:0}
#clock{font-size:14px;font-weight:bold}#detail,#availability{font-size:11px;margin-top:4px;color:#586d78;line-height:1.35}
#timeline{width:100%;accent-color:#087d9d;margin:12px 0 4px}.labels{display:flex;justify-content:space-between;font-size:11px}
.source{font-size:10px;color:#586d78;margin-top:8px;line-height:1.4}.source a{color:#087d9d}
#legend{margin-top:7px;font-size:10px}.gradient{height:7px;border-radius:4px;background:linear-gradient(90deg,#64d2ff,#2d8cf5,#6a4ed3,#d7378f,#ff9e46,#ffe641,#ffffbe);margin:4px 0}
#mode{margin-left:auto;font-size:11px;white-space:nowrap}.leaflet-image-layer{image-rendering:auto}
@media(max-height:500px){header,footer{padding:6px 10px}.source{margin-top:3px}#availability{display:none}}
</style></head><body>
<header><h1 id="title">SeaPoint Rain Map</h1><div class="row">
<button id="all" class="active" aria-pressed="true">Past + forecast</button>
<button id="observed" aria-pressed="false">Radar</button>
<button id="forecast" aria-pressed="false">Forecast</button><span id="mode">Loading</span>
</div><div id="legend"></div></header>
<div class="map-wrap"><div id="map"></div><div id="notice" class="notice" role="status">Loading observed radar…</div></div>
<footer><div class="row"><button id="play" aria-label="Play animation" disabled>▶</button>
<div><div id="clock">Preparing weather map</div><div id="detail">Forecast extends up to 24 hours ahead</div></div></div>
<input id="timeline" type="range" min="0" max="1" step="1" value="0" aria-label="Weather map time" disabled>
<div class="labels"><span id="start">Past</span><span id="end">+24 hours</span></div>
<div id="availability" role="status"></div>
<div class="source"><a href="https://www.rainviewer.com/" target="_blank" rel="noopener">RainViewer</a>: observed radar, coverage varies.
<a href="https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast" target="_blank" rel="noopener">NOAA GFS</a>: hourly model forecast, approximately 28 km grid; smooth blending adds no spatial detail.
Forecast overlay covers the eastern Caribbean (10–23°N, 68–55°W).</div></footer>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>
'use strict';
const config=__CONFIG__;
document.getElementById('title').textContent='Rain Map · '+config.name;
const map=L.map('map').setView([config.lat,config.lon],7);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',{maxNativeZoom:10,maxZoom:12,attribution:'Basemap: Esri, GEBCO, NOAA'}).addTo(map);
map.createPane('placeLabels');map.getPane('placeLabels').style.zIndex=450;map.getPane('placeLabels').style.pointerEvents='none';
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}',{maxNativeZoom:10,maxZoom:12,pane:'placeLabels',attribution:'Place labels: Esri'}).addTo(map);
L.marker([config.lat,config.lon]).addTo(map).bindPopup(document.createTextNode(config.name));
const $=id=>document.getElementById(id);
const format=t=>new Intl.DateTimeFormat('en-US',{timeZone:'America/Antigua',weekday:'short',hour:'numeric',minute:'2-digit'}).format(new Date(t*1000));
let observed=[],forecast=[],active=[],selection='all',playing=false,position=0,lastTick=0,loading=false,revision=0;
let forecastMeta=null,forecastRetry=null,visibleLayers=new Set();
const loaded=new Map(),pending=new Map();
const key=f=>f.kind+':'+f.time;
function notify(){if(window.SeaPointRadar)window.SeaPointRadar.postMessage('ready');}
notify();
function announce(message){$('availability').textContent=message;}
function setPlaying(value){playing=value;lastTick=0;$('play').textContent=value?'❚❚':'▶';$('play').setAttribute('aria-label',value?'Pause animation':'Play animation');}
function frameLayer(frame){
 const id=key(frame);if(loaded.has(id))return Promise.resolve(loaded.get(id));if(pending.has(id))return pending.get(id);
 const task=new Promise((resolve,reject)=>{
  let layer,successes=0,settled=false;
  const finish=ok=>{if(settled)return;settled=true;clearTimeout(timeout);if(ok){loaded.set(id,layer);resolve(layer);}else{if(layer)map.removeLayer(layer);reject(new Error('Map frame unavailable'));}};
  const timeout=setTimeout(()=>finish(false),25000);
  if(frame.kind==='forecast'){
   layer=L.imageOverlay(frame.url,forecastMeta.bounds,{opacity:0,interactive:false,attribution:'Forecast: NOAA GFS'});
   layer.once('load',()=>finish(true));layer.once('error',()=>finish(false));
  }else{
   layer=L.tileLayer(frame.url,{opacity:0,maxNativeZoom:7,maxZoom:12,attribution:'Radar: RainViewer'});
   layer.on('tileload',()=>{successes++;});layer.once('load',()=>finish(successes>0));
  }
  layer.addTo(map);
 });pending.set(id,task);task.finally(()=>pending.delete(id)).catch(()=>{});return task;
}
function cleanLayers(){
 const keep=new Set([...observed,...forecast].map(key));
 for(const [id,layer]of loaded)if(!keep.has(id)&&!visibleLayers.has(layer)){map.removeLayer(layer);loaded.delete(id);}
}
function legend(kind){
 $('legend').innerHTML=kind==='forecast'?'<div class="labels"><span>Forecast rain intensity · mm/h</span><span>Light → Heavy</span></div><div class="gradient"></div><div class="labels"><span>0.1</span><span>2.5</span><span>15</span><span>60+</span></div>':'Observed radar · RainViewer intensity colours · coverage varies';
}
function render(){
 if(!active.length)return;
 const index=active.findIndex(f=>f.time>=position);
 const high=index<0?active.length-1:index,low=Math.max(0,high-1);
 const a=active[low],b=active[high];
 const blend=b.time>a.time?Math.max(0,Math.min(1,(position-a.time)/(b.time-a.time))):1;
 const shown=blend<0.5?a:b;
 const first=loaded.get(key(a)),second=loaded.get(key(b));
 if(!first||!second){$('notice').textContent='Buffering weather frames…';$('notice').hidden=false;return false;}
 const next=new Set([first,second]);for(const layer of visibleLayers)if(!next.has(layer))layer.setOpacity(0);
 if(first===second){first.setOpacity(.78);}else if(a.kind!==b.kind){first.setOpacity(blend<.5?.78:0);second.setOpacity(blend<.5?0:.78);}else{first.setOpacity(.78*(1-blend));second.setOpacity(.78*blend);}
 visibleLayers=next;
 $('timeline').value=String(Math.round(position));
 $('clock').textContent=format(position)+' · Antigua time';
 $('mode').textContent=shown.kind==='forecast'?'FORECAST':'OBSERVED';
 $('detail').textContent=shown.kind==='forecast'?'GFS forecast · blended hourly frames · model run '+format(forecastMeta.model_run):'Observed radar · '+format(shown.time)+' · not a forecast';
 legend(shown.kind);
 const outside=shown.kind==='forecast'&&!L.latLngBounds(forecastMeta.bounds).intersects(map.getBounds());
 $('notice').hidden=!outside;if(outside)$('notice').textContent='Outside the eastern Caribbean forecast coverage';
 return true;
}
async function activate(){
 const token=++revision;setPlaying(false);cleanLayers();
 active=(selection==='observed'?observed:selection==='forecast'?forecast:[...observed,...forecast]).slice().sort((a,b)=>a.time-b.time);
 $('play').disabled=$('timeline').disabled=true;
 if(!active.length){for(const layer of visibleLayers)layer.setOpacity(0);visibleLayers.clear();$('mode').textContent='UNAVAILABLE';$('clock').textContent='No frames available';$('detail').textContent='';$('notice').textContent=selection==='forecast'?'Forecast is preparing or temporarily unavailable':'Weather frames temporarily unavailable';$('notice').hidden=false;return;}
 $('notice').textContent='Preparing smooth playback…';$('notice').hidden=false;
 const results=[];
 // Limit concurrent image requests on phones; preload before enabling playback.
 for(let i=0;i<active.length;i+=4){
  results.push(...await Promise.allSettled(active.slice(i,i+4).map(frameLayer)));
  if(token!==revision)return;
 }
 const failed=results.some(r=>r.status==='rejected');
 // Do not bridge an unavailable hour with a misleading continuous forecast.
 const badKinds=new Set(active.filter((f,i)=>results[i].status==='rejected').map(f=>f.kind));
 active=active.filter(f=>!badKinds.has(f.kind));
 if(!active.length){$('notice').textContent='Weather images unavailable. Retry shortly.';$('clock').textContent='Playback unavailable';$('mode').textContent='UNAVAILABLE';return;}
 if(failed)announce('One image source is unavailable; showing the available source only.');
 position=active[0].time;$('timeline').min=String(active[0].time);$('timeline').max=String(active.at(-1).time);
 $('start').textContent=format(active[0].time);$('end').textContent=format(active.at(-1).time);
 $('timeline').disabled=false;$('play').disabled=active.length<2;render();
}
for(const mode of ['all','observed','forecast'])$(mode).onclick=()=>{
 selection=mode;for(const id of ['all','observed','forecast']){$(id).classList.toggle('active',id===mode);$(id).setAttribute('aria-pressed',String(id===mode));}activate();
};
$('play').onclick=()=>setPlaying(!playing);
$('timeline').oninput=()=>{setPlaying(false);position=Number($('timeline').value);render();};
function tick(ms){
 if(playing&&active.length>1){
  if(lastTick){const candidate=position+Math.min(ms-lastTick,100)*1.8;const old=position;position=candidate>active.at(-1).time?active[0].time:candidate;if(render()===false)position=old;}
  lastTick=ms;
 }else lastTick=0;
 requestAnimationFrame(tick);
}requestAnimationFrame(tick);
document.addEventListener('visibilitychange',()=>{if(document.hidden)setPlaying(false);});
async function loadObserved(){
 const previous=observed.map(key).join(',');
 try{
  const response=await fetch('/radar-frames');if(!response.ok)throw new Error();const data=await response.json();
  const now=Date.now()/1000;
  observed=(data.frames||[]).filter(f=>Number.isFinite(f.time)&&f.path&&f.time<=now+60&&f.time>=now-3*3600).slice(-8).map(f=>({kind:'observed',time:f.time,url:(data.host||'https://tilecache.rainviewer.com')+f.path+'/256/{z}/{x}/{y}/2/1_1.png'}));
 }catch(_){observed=[];announce('Observed radar unavailable; forecast may still be available.');}
 if(previous!==observed.map(key).join(',')||!active.length)await activate();
}
async function loadForecast(){
 if(loading)return;loading=true;
 try{
  const response=await fetch('/forecast-frames');const data=await response.json();
  if(response.status===202){announce('Preparing the 24-hour forecast. Radar remains available.');clearTimeout(forecastRetry);forecastRetry=setTimeout(loadForecast,15000);return;}
  if(!response.ok||data.status!=='ready')throw new Error();
  forecastMeta=data;const now=Date.now()/1000;
  const upcoming=(data.frames||[]).filter(f=>Number.isFinite(f.time)&&f.url&&f.time>=now-3600&&f.time<=now+24*3600).map(f=>({...f,kind:'forecast'}));
  if(upcoming.length<2)throw new Error();
  const changed=upcoming.map(key).join(',')!==forecast.map(key).join(',');forecast=upcoming;
  announce('Forecast available through '+format(forecast.at(-1).time)+' · hourly data, smoothly blended.');
  if(changed)await activate();
 }catch(_){announce(forecast.length?'Forecast update unavailable; retaining cached forecast through '+format(forecast.at(-1).time):'Forecast temporarily unavailable. Observed radar remains available.');}
 finally{loading=false;}
}
loadObserved().then(loadForecast);setInterval(loadObserved,300000);setInterval(loadForecast,900000);
map.on('movestart',()=>setPlaying(false));
</script></body></html>'''
