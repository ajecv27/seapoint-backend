"""Embedded radar/forecast player shared by the existing Flutter WebView."""
import json


def radar_page(latitude, longitude, location_name):
    config = json.dumps(dict(lat=latitude, lon=longitude, name=location_name)).replace('<', '\\u003c')
    return HTML.replace('__CONFIG__', config)


HTML = r'''<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>SeaPoint Rain Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
:root{color-scheme:dark;--panel:rgba(30,39,49,.94);--line:rgba(255,255,255,.18);--blue:#158ef5;--safe:env(safe-area-inset-bottom,0px)}
*{box-sizing:border-box}html,body{height:100%;width:100%;margin:0;overflow:hidden;font-family:Arial,Helvetica,sans-serif;background:#153856;color:#fff}
button,input{font:inherit}button{cursor:pointer;-webkit-tap-highlight-color:transparent;touch-action:manipulation}button:focus-visible,input:focus-visible,a:focus-visible{outline:3px solid #8ad6ff;outline-offset:3px}button:disabled{opacity:.4;cursor:default}[hidden]{display:none!important}
#map{position:absolute;inset:0;height:100%;width:100%;z-index:0;background:#163957}.leaflet-image-layer{image-rendering:auto}.leaflet-container{font-family:Arial,Helvetica,sans-serif}.leaflet-control-attribution{background:rgba(17,29,40,.78)!important;color:#dce6ed!important;font-size:9px!important;max-width:94vw;line-height:1.35!important;padding:3px 6px!important;border-radius:5px}.leaflet-control-attribution a{color:#dce6ed!important}.leaflet-bottom.leaflet-right{bottom:calc(5px + var(--safe));right:8px}.leaflet-popup-content{color:#17384c}
#legend{position:absolute;inset:0 0 auto;z-index:700;height:35px;background:linear-gradient(90deg,#64d2ff,#2d8cf5,#6a4ed3,#d7378f,#ff9e46,#ffe641);box-shadow:0 1px 8px #0003;display:flex;align-items:center;justify-content:space-around;color:white;font-weight:700;text-shadow:0 1px 3px #000,0 0 5px #0009;font-size:14px}
#legend.radar{background:linear-gradient(90deg,#cec087,#00a3e0,#005588,#ffaa00,#c10000,#ff77ff)}
.mode-switch{position:absolute;top:50px;left:50%;transform:translateX(-50%);z-index:700;display:flex;padding:4px;gap:4px;background:var(--panel);border:1px solid var(--line);border-radius:30px;box-shadow:0 4px 18px #0004}
.mode-switch button{min-height:44px;min-width:112px;display:flex;align-items:center;justify-content:center;gap:8px;border:0;border-radius:24px;background:transparent;color:#d6dfe5;font-size:14px;font-weight:600;transition:background .15s}
.mode-switch button.active{color:white;background:var(--blue);box-shadow:0 2px 8px #0015}.icon{width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;flex-shrink:0}
.location-pill{position:absolute;top:114px;left:12px;z-index:650;max-width:calc(100% - 127px);border-radius:18px;background:rgba(24,37,49,.85);padding:8px 11px;display:flex;align-items:center;gap:6px;box-shadow:0 2px 8px #0002}.location-pill span{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.location-pill .icon{width:14px;height:14px}
#mode{position:absolute;top:116px;right:12px;z-index:650;font-size:10px;font-weight:bold;letter-spacing:.6px;border:1px solid var(--line);padding:8px 10px;border-radius:18px;background:rgba(24,37,49,.85);color:#d4f3ff}
.notice{position:absolute;top:163px;left:50%;transform:translateX(-50%);z-index:650;background:rgba(24,37,49,.93);border:1px solid var(--line);padding:9px 13px;border-radius:15px;font-size:12px;line-height:1.4;text-align:center;max-width:calc(100% - 80px);width:max-content;pointer-events:none}
.map-tools{position:absolute;right:12px;bottom:calc(191px + var(--safe));z-index:650;display:flex;flex-direction:column;gap:8px}.round{height:46px;width:46px;border-radius:50%;border:1px solid var(--line);display:flex;align-items:center;justify-content:center;color:#fff;background:var(--panel);box-shadow:0 2px 10px #0003}.round .icon{width:23px;height:23px}#recenter{background:var(--blue);border-color:transparent}#zoom-in,#zoom-out{font-size:25px;font-weight:300}
.source-tools{position:absolute;left:12px;bottom:calc(184px + var(--safe));z-index:650;display:flex;align-items:center;gap:7px}#model-chip{background:var(--panel);border:1px solid var(--line);padding:8px 11px;border-radius:12px;line-height:1.3;font-size:11px;font-weight:600;text-shadow:0 1px 2px #0004}#model-chip small{display:block;color:#b8c8d6;font-size:10px;font-weight:400}
#player{position:absolute;bottom:calc(33px + var(--safe));left:12px;right:12px;z-index:700;max-width:760px;margin:auto;padding:13px 14px 10px;background:var(--panel);border:1px solid var(--line);border-radius:23px;box-shadow:0 5px 25px #0005;backdrop-filter:blur(12px)}
.player-row{display:flex;align-items:center;gap:10px}.time-block{flex:1;min-width:0;text-align:center}#clock{font-size:18px;line-height:1.3;font-weight:600;color:#fff}#detail{font-size:10px;color:#b7c7d4;line-height:1.4;margin-top:3px}#play,#jump-latest{height:44px;width:44px;flex-shrink:0;display:flex;align-items:center;justify-content:center;border:0;background:transparent;color:#fff;border-radius:50%}#play{font-size:25px}#play .icon{width:30px;height:30px}#jump-latest .icon{width:21px;height:21px}
.scrubber{height:36px;display:flex;align-items:center;position:relative;margin-top:2px}.scrubber::before{content:'';position:absolute;height:13px;left:7px;right:7px;background:repeating-linear-gradient(90deg,transparent 0,transparent calc(6.25% - 2px),#ffffff38 calc(6.25% - 2px),#ffffff38 6.25%);pointer-events:none}
#timeline{position:relative;width:100%;height:36px;margin:0;appearance:none;-webkit-appearance:none;background:transparent;cursor:pointer;touch-action:pan-y}#timeline::-webkit-slider-runnable-track{height:3px;border-radius:4px;background:#b3c7d84d}#timeline::-webkit-slider-thumb{-webkit-appearance:none;width:7px;height:25px;margin-top:-11px;border-radius:3px;background:#219cff;box-shadow:0 0 0 4px #219cff22}#timeline::-moz-range-track{height:3px;background:#b3c7d84d}#timeline::-moz-range-thumb{height:25px;width:7px;border:0;border-radius:3px;background:#219cff}
.timeline-labels{display:flex;justify-content:space-between;font-size:10px;color:#acbbc9;gap:8px}.timeline-labels span{white-space:nowrap}.timeline-labels .zone{color:#d8e5ef}
#source-panel{position:absolute;left:12px;right:12px;bottom:calc(244px + var(--safe));z-index:800;max-width:420px;max-height:50%;overflow:auto;background:#202b36f5;border:1px solid var(--line);border-radius:20px;box-shadow:0 5px 22px #0006;padding:16px;color:#d5e2eb;font-size:12px;line-height:1.5}#source-panel h2{color:white;font-size:15px;margin:0 45px 12px 0}#source-panel p{margin:8px 0}#source-panel a{color:#8acbff}#source-close{float:right;width:44px;height:44px;margin:-10px -10px 0 0;border:0;border-radius:50%;background:transparent;color:white;font-size:26px}#availability{color:#99d7ff}
@media(min-width:800px){.mode-switch{top:54px}#player{padding:14px 20px 11px}.map-tools{right:22px}.source-tools{left:22px}}
@media(max-width:340px){#clock{font-size:15px}.mode-switch button{min-width:100px}.timeline-labels{font-size:9px}#player{left:8px;right:8px;padding-left:10px;padding-right:10px}}
@media(max-height:500px){#legend{height:27px;font-size:12px}.mode-switch{top:35px}.mode-switch button{min-height:44px;min-width:100px}.location-pill{top:41px;max-width:calc(50% - 134px)}#mode{top:48px}.notice{top:93px;max-width:70%}.map-tools{bottom:calc(150px + var(--safe));gap:5px;right:10px}.round{height:44px;width:44px}.source-tools{bottom:calc(148px + var(--safe));left:10px}#player{bottom:calc(25px + var(--safe));padding:6px 14px;border-radius:20px;max-width:600px}#clock{font-size:16px}#detail{font-size:10px;margin-top:0}.scrubber{margin-top:0;height:30px}#timeline{height:30px}.timeline-labels{font-size:9px}#source-panel{bottom:calc(140px + var(--safe));max-height:53%}}
@media(prefers-reduced-motion:reduce){button{transition:none}}
</style></head><body>
<div id="map" aria-label="SeaPoint rain map"></div>
<div id="legend" class="radar" aria-label="Rain intensity"><span>Rain</span><span>Light</span><span>Moderate</span><span>Heavy</span></div>
<nav class="mode-switch" aria-label="Map layer">
<button id="observed" class="active" aria-pressed="true"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a9 9 0 1 0 9 9M12 7a5 5 0 1 0 5 5M12 12l8-8"/><circle cx="12" cy="12" r="1.5"/></svg>Radar</button>
<button id="forecast" aria-pressed="false"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 14a4 4 0 0 1 0-8 5.5 5.5 0 0 1 10.5 1.5A3.5 3.5 0 0 1 18 14ZM8 17l-1 3m6-3-1 3m6-3-1 3"/></svg>Forecast</button>
</nav>
<div class="location-pill"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 10c0 6-8 11-8 11S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg><span id="title">SeaPoint</span></div>
<span id="mode" role="status">LOADING</span>
<div id="notice" class="notice" role="status">Loading observed radar…</div>
<div class="map-tools" aria-label="Map controls">
<button id="zoom-in" class="round" aria-label="Zoom in">+</button><button id="zoom-out" class="round" aria-label="Zoom out">−</button>
<button id="recenter" class="round" aria-label="Center on selected location"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.5"/><path d="M12 1v4m0 14v4M1 12h4m14 0h4"/></svg></button>
</div>
<div class="source-tools"><button id="info-toggle" class="round" aria-label="Map sources and forecast details" aria-controls="source-panel" aria-expanded="false"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/></svg></button><div id="model-chip">RADAR<small>RainViewer</small></div></div>
<section id="source-panel" hidden aria-labelledby="source-title"><button id="source-close" aria-label="Close map details">×</button><h2 id="source-title">Map sources</h2><div id="availability" role="status">Checking weather data…</div>
<p><a href="https://www.rainviewer.com/" target="_blank" rel="noopener">RainViewer</a> supplies recent observed radar. Coverage varies.</p>
<p><a href="https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast" target="_blank" rel="noopener">NOAA GFS</a> supplies the hourly precipitation forecast, up to 24 hours ahead. Its grid is approximately 28 km; smooth blending adds no spatial detail.</p>
<p>Forecast coverage: eastern Caribbean, 10–23°N and 68–55°W. Forecast rain rates use mm/h. Radar colours use RainViewer’s scale.</p><p id="model-run"></p>
</section>
<footer id="player" aria-label="Animation controls"><div class="player-row">
<button id="play" aria-label="Play animation" disabled><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 4 14 8-14 8Z" fill="currentColor" stroke="none"/></svg></button><div class="time-block"><div id="clock">Loading radar</div><div id="detail">Observed rain</div></div>
<button id="jump-latest" aria-label="Go to latest radar frame" disabled><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 5 10 7-10 7ZM19 5v14"/></svg></button>
</div><div class="scrubber"><input id="timeline" type="range" min="0" max="1" step="1" value="0" aria-label="Weather map time" disabled></div>
<div class="timeline-labels"><span id="start">Recent observations</span><span class="zone">Antigua time</span><span id="end">Latest</span></div></footer>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>
'use strict';
const config=__CONFIG__;
document.getElementById('title').textContent=config.name;
const map=L.map('map',{zoomControl:false,zoomSnap:.5,zoomDelta:.5}).setView([config.lat,config.lon],10.5);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxNativeZoom:18,maxZoom:12,attribution:'Imagery: Esri, Maxar, Earthstar Geographics'}).addTo(map);
map.createPane('placeLabels');map.getPane('placeLabels').style.zIndex=450;map.getPane('placeLabels').style.pointerEvents='none';
L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',{maxNativeZoom:18,maxZoom:12,pane:'placeLabels',attribution:'Labels: Esri'}).addTo(map);
L.circleMarker([config.lat,config.lon],{pane:'markerPane',radius:8,color:'#fff',weight:3,fillColor:'#1498ff',fillOpacity:1}).addTo(map).bindPopup(document.createTextNode(config.name));
const $=id=>document.getElementById(id);
const timeFormatter=new Intl.DateTimeFormat('en-US',{timeZone:'America/Antigua',weekday:'short',hour:'numeric',minute:'2-digit'});
const format=t=>timeFormatter.format(new Date(t*1000));
let observed=[],forecast=[],active=[],selection='observed',playing=false,position=0,lastTick=0,loading=false,revision=0;
let forecastMeta=null,forecastRetry=null,visibleLayers=new Set();
let lastLegendKind='',lastDetail='';
const loaded=new Map(),pending=new Map();
const key=f=>f.kind+':'+f.time;
function notify(){if(window.SeaPointRadar)window.SeaPointRadar.postMessage('ready');}
notify();
function announce(message){$('availability').textContent=message;}
function setPlaying(value){playing=value;lastTick=0;$('play').innerHTML=value?'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 4v16m8-16v16" stroke-width="4"/></svg>':'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 4 14 8-14 8Z" fill="currentColor" stroke="none"/></svg>';$('play').setAttribute('aria-label',value?'Pause animation':'Play animation');}
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
 if(lastLegendKind===kind)return;
 lastLegendKind=kind;$('legend').classList.toggle('radar',kind==='observed');
 $('legend').setAttribute('aria-label',kind==='forecast'?'Forecast rain intensity, mm per hour':'Observed radar intensity, RainViewer scale');
 $('model-chip').innerHTML=kind==='forecast'?'GFS<small>28 km model</small>':'RADAR<small>RainViewer</small>';
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
 $('clock').textContent=format(position);
 $('mode').textContent=shown.kind==='forecast'?'FORECAST':'OBSERVED';
 const detail=shown.kind==='forecast'?'Forecast rain · hourly model':'Observed radar · '+format(shown.time);
 if(detail!==lastDetail){$('detail').textContent=detail;lastDetail=detail;}
 legend(shown.kind);
 const outside=shown.kind==='forecast'&&!L.latLngBounds(forecastMeta.bounds).intersects(map.getBounds());
 $('notice').hidden=!outside;if(outside)$('notice').textContent='Outside the eastern Caribbean forecast coverage';
 return true;
}
async function activate(){
 const token=++revision;setPlaying(false);cleanLayers();
 legend(selection);
 active=(selection==='observed'?observed:forecast).slice().sort((a,b)=>a.time-b.time);
 for(const layer of visibleLayers)layer.setOpacity(0);visibleLayers.clear();
 $('mode').textContent='LOADING';
 $('jump-latest').disabled=true;
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
 position=selection==='observed'?active.at(-1).time:Math.min(active.at(-1).time,Math.max(Date.now()/1000,active[0].time));
 $('timeline').min=String(active[0].time);$('timeline').max=String(active.at(-1).time);
 $('start').textContent=format(active[0].time);$('end').textContent=format(active.at(-1).time);
 $('timeline').disabled=false;$('play').disabled=active.length<2;$('jump-latest').disabled=false;
 $('jump-latest').setAttribute('aria-label',selection==='observed'?'Go to latest radar frame':'Go to forecast start');
 lastDetail='';render();
}
for(const mode of ['observed','forecast'])$(mode).onclick=()=>{
 selection=mode;for(const id of ['observed','forecast']){$(id).classList.toggle('active',id===mode);$(id).setAttribute('aria-pressed',String(id===mode));}activate();
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
 if(selection==='observed'&&(previous!==observed.map(key).join(',')||!active.length))await activate();
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
  $('model-run').textContent='Forecast model run: '+format(data.model_run)+' Antigua time.';
  if(selection==='forecast'&&(changed||!active.length))await activate();
 }catch(_){announce(forecast.length?'Forecast update unavailable; retaining cached forecast through '+format(forecast.at(-1).time):'Forecast temporarily unavailable. Observed radar remains available.');}
 finally{loading=false;}
}
loadObserved();loadForecast();setInterval(loadObserved,300000);setInterval(loadForecast,900000);
map.on('movestart',()=>setPlaying(false));
$('zoom-in').onclick=()=>map.zoomIn();$('zoom-out').onclick=()=>map.zoomOut();
$('recenter').onclick=()=>map.setView([config.lat,config.lon],10.5);
$('jump-latest').onclick=()=>{if(!active.length)return;setPlaying(false);position=selection==='observed'?active.at(-1).time:Math.min(active.at(-1).time,Math.max(Date.now()/1000,active[0].time));render();};
function showInfo(show){$('source-panel').hidden=!show;$('info-toggle').setAttribute('aria-expanded',String(show));if(show)$('source-close').focus();else $('info-toggle').focus();}
$('info-toggle').onclick=()=>showInfo($('source-panel').hidden);
$('source-close').onclick=()=>showInfo(false);
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('source-panel').hidden)showInfo(false);});

</script></body></html>'''
