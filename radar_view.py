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
<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css">
<style>
:root{color-scheme:dark;--panel:rgba(30,39,49,.64);--line:rgba(255,255,255,.16);--blue:rgba(21,142,245,.78);--safe:env(safe-area-inset-bottom,0px)}
*{box-sizing:border-box}html,body{height:100%;width:100%;margin:0;overflow:hidden;font-family:Arial,Helvetica,sans-serif;background:#153856;color:#fff}
button,input{font:inherit}button{cursor:pointer;-webkit-tap-highlight-color:transparent;touch-action:manipulation}button:focus-visible,input:focus-visible,a:focus-visible{outline:3px solid #8ad6ff;outline-offset:3px}button:disabled{opacity:.4;cursor:default}[hidden]{display:none!important}
#map{position:absolute;inset:0;height:100%;width:100%;z-index:0;background:#163957}.leaflet-image-layer{image-rendering:auto}.rain-overlay{filter:blur(1.3px);image-rendering:auto}.leaflet-container{font-family:Arial,Helvetica,sans-serif}.leaflet-control-attribution{background:rgba(17,29,40,.78)!important;color:#dce6ed!important;font-size:9px!important;max-width:94vw;line-height:1.35!important;padding:3px 6px!important;border-radius:5px}.leaflet-control-attribution a{color:#dce6ed!important}.leaflet-bottom.leaflet-right{bottom:calc(5px + var(--safe));right:8px}.leaflet-popup-content{color:#17384c}
#legend{position:absolute;inset:0 0 auto;z-index:700;height:28px;background:linear-gradient(90deg,#64d2ff,#2d8cf5,#6a4ed3,#d7378f,#ff9e46,#ffe641);box-shadow:0 1px 8px #0003;display:flex;align-items:center;justify-content:space-around;color:white;font-weight:700;text-shadow:0 1px 3px #000,0 0 5px #0009;font-size:12px}
#legend.radar{background:linear-gradient(90deg,#cec087,#00a3e0,#005588,#ffaa00,#c10000,#ff77ff)}


.icon{width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;flex-shrink:0}
.notice{position:absolute;top:163px;left:50%;transform:translateX(-50%);z-index:650;background:rgba(24,37,49,.70);border:1px solid var(--line);padding:9px 13px;border-radius:15px;font-size:12px;line-height:1.4;text-align:center;max-width:calc(100% - 80px);width:max-content;pointer-events:none}
.map-tools{position:absolute;right:12px;bottom:calc(164px + var(--safe));z-index:650;display:flex;flex-direction:column;gap:8px}.round{height:46px;width:46px;border-radius:50%;border:1px solid var(--line);display:flex;align-items:center;justify-content:center;color:#fff;background:var(--panel);box-shadow:0 2px 10px #0003}.round .icon{width:23px;height:23px}#recenter{background:var(--blue);border-color:transparent}#zoom-in,#zoom-out{font-size:25px;font-weight:300}
#player{position:absolute;bottom:calc(8px + var(--safe));left:12px;right:12px;z-index:700;max-width:760px;margin:auto;padding:13px 14px 10px;background:var(--panel);border:1px solid var(--line);border-radius:23px;box-shadow:0 5px 25px #0005;backdrop-filter:blur(12px)}
.player-row{display:flex;align-items:center;gap:10px}.time-block{flex:1;min-width:0;text-align:center}#clock{font-size:18px;line-height:1.3;font-weight:600;color:#fff}#detail{font-size:10px;color:#b7c7d4;line-height:1.4;margin-top:3px}#play,#jump-latest{height:44px;width:44px;flex-shrink:0;display:flex;align-items:center;justify-content:center;border:0;background:transparent;color:#fff;border-radius:50%}#play{font-size:25px}#play .icon{width:30px;height:30px}#jump-latest .icon{width:21px;height:21px}
.scrubber{height:36px;display:flex;align-items:center;position:relative;margin-top:2px}.scrubber::before{content:'';position:absolute;height:13px;left:7px;right:7px;background:repeating-linear-gradient(90deg,transparent 0,transparent calc(6.25% - 2px),#ffffff38 calc(6.25% - 2px),#ffffff38 6.25%);pointer-events:none}
#timeline{position:relative;width:100%;height:36px;margin:0;appearance:none;-webkit-appearance:none;background:transparent;cursor:pointer;touch-action:pan-y}#timeline::-webkit-slider-runnable-track{height:3px;border-radius:4px;background:#b3c7d84d}#timeline::-webkit-slider-thumb{-webkit-appearance:none;width:7px;height:25px;margin-top:-11px;border-radius:3px;background:#219cff;box-shadow:0 0 0 4px #219cff22}#timeline::-moz-range-track{height:3px;background:#b3c7d84d}#timeline::-moz-range-thumb{height:25px;width:7px;border:0;border-radius:3px;background:#219cff}
.timeline-labels{display:flex;justify-content:space-between;font-size:10px;color:#acbbc9;gap:8px}.timeline-labels span{white-space:nowrap}.timeline-labels .zone{color:#d8e5ef}
#source-panel{position:absolute;left:auto;right:12px;top:112px;bottom:auto;width:calc(100% - 24px);z-index:800;max-width:420px;max-height:calc(100% - 270px);overflow:auto;background:#202b36d6;border:1px solid var(--line);border-radius:20px;box-shadow:0 5px 22px #0006;padding:16px;color:#d5e2eb;font-size:12px;line-height:1.5}#source-panel h2{color:white;font-size:15px;margin:0 45px 12px 0}#source-panel p{margin:8px 0}#source-panel a{color:#8acbff}#source-close{float:right;width:44px;height:44px;margin:-10px -10px 0 0;border:0;border-radius:50%;background:transparent;color:white;font-size:26px}#availability{color:#99d7ff}
@media(min-width:800px){#player{padding:14px 20px 11px}.map-tools{right:22px}}
@media(max-width:340px){#clock{font-size:15px}.timeline-labels{font-size:9px}#player{left:8px;right:8px;padding-left:10px;padding-right:10px}}
@media(max-height:500px){#legend{height:23px;font-size:11px}.notice{top:93px;max-width:70%}.map-tools{bottom:calc(126px + var(--safe));gap:5px;right:10px}.round{height:44px;width:44px}#player{bottom:calc(8px + var(--safe));padding:6px 14px;border-radius:20px;max-width:600px}#clock{font-size:16px}#detail{font-size:10px;margin-top:0}.scrubber{margin-top:0;height:30px}#timeline{height:30px}.timeline-labels{font-size:9px}#source-panel{top:94px;bottom:auto;max-height:calc(100% - 224px)}}

#info-toggle{position:absolute;top:54px;right:12px;z-index:750;width:44px;height:44px;background:transparent;border:0;box-shadow:none;}
#info-toggle::before{content:"";position:absolute;inset:5px;background:var(--panel);border:1px solid var(--line);border-radius:50%;z-index:-1;}
#info-toggle .icon{width:18px;height:18px;}
#credits-notice{position:absolute;top:112px;left:12px;z-index:650;max-width:calc(100% - 24px);padding:6px 9px;border-radius:10px;background:#1e2731bf;color:#c4d9e6;font-size:10px;line-height:1.5;}
#credits-notice a{color:inherit;}
@media(max-height:500px){#info-toggle{top:38px;}#credits-notice{top:92px;}}
#now-marker{position:absolute;z-index:3;height:17px;width:2px;top:9px;background:#ffffffa6;pointer-events:none;}#now-marker::before{content:"Now";position:absolute;top:-11px;left:-9px;font-size:8px;color:#dce8f0;white-space:nowrap;}
@media(prefers-reduced-motion:reduce){button{transition:none}}
</style></head><body>
<div id="map" aria-label="SeaPoint rain map"></div>
<div id="legend" class="radar" aria-label="Rain intensity"><span>Rain</span><span>Light</span><span>Moderate</span><span>Heavy</span></div>
<div id="credits-notice" hidden><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap contributors</a> · <a href="https://openmaptiles.org/" target="_blank" rel="noopener">© OpenMapTiles</a></div>
<div id="notice" class="notice" role="status">Loading observed radar…</div>
<div class="map-tools" aria-label="Map controls">
<button id="zoom-in" class="round" aria-label="Zoom in">+</button><button id="zoom-out" class="round" aria-label="Zoom out">−</button>
<button id="recenter" class="round" aria-label="Center on selected location"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.5"/><path d="M12 1v4m0 14v4M1 12h4m14 0h4"/></svg></button>
</div>
<button id="info-toggle" class="round" aria-label="Map information and credits" aria-controls="source-panel" aria-expanded="false"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/></svg></button>
<section id="source-panel" hidden aria-labelledby="source-title"><button id="source-close" aria-label="Close map details">×</button><h2 id="source-title">Map information &amp; credits</h2><div id="availability" role="status">Checking weather data…</div>
<p><a href="https://www.rainviewer.com/" target="_blank" rel="noopener">RainViewer</a> supplies recent observed radar. Coverage varies.</p>
<p><a href="https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast" target="_blank" rel="noopener">NOAA GFS</a> supplies the hourly precipitation forecast, up to 48 hours ahead. Its grid is approximately 28 km; smooth blending adds no spatial detail.</p>
<p>Forecast coverage: eastern Caribbean, 10–23°N and 68–55°W. Forecast rain rates use mm/h. The timeline moves from observed radar into model forecasts; the label and legend identify each source.</p><p id="model-run"></p><p id="basemap-status"></p><p>Map data: <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap contributors</a> · <a href="https://openmaptiles.org/" target="_blank" rel="noopener">© OpenMapTiles</a>. Map service: <a href="https://openfreemap.org/" target="_blank" rel="noopener">OpenFreeMap</a>. Terrain shading: Esri, USGS, NOAA.</p>
</section>
<footer id="player" aria-label="Animation controls"><div class="player-row">
<button id="play" aria-label="Play animation" disabled><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 4 14 8-14 8Z" fill="currentColor" stroke="none"/></svg></button><div class="time-block"><div id="clock">Loading radar</div><div id="detail">Observed rain</div></div>
<button id="jump-latest" aria-label="Go to now" disabled><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 5 10 7-10 7ZM19 5v14"/></svg></button>
</div><div class="scrubber"><span id="now-marker" hidden aria-label="Now"></span><input id="timeline" type="range" min="0" max="1" step="1" value="0" aria-label="Weather map time" disabled></div>
<div class="timeline-labels"><span id="start">Recent observations</span><span class="zone">Antigua time</span><span id="end">Latest</span></div></footer>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<script src="https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js"></script><script>
'use strict';
const config=__CONFIG__;
document.title='SeaPoint Rain Map · '+config.name;
const map=L.map('map',{zoomControl:false,attributionControl:false,zoomSnap:.5,zoomDelta:.5}).setView([config.lat,config.lon],10.5);
let flatBasemap=null;
function dismissCredits(){document.getElementById('credits-notice').hidden=true;}
function presentCredits(){
 const credit=document.getElementById('credits-notice');credit.hidden=false;
 setTimeout(()=>{if(!credit.contains(document.activeElement))dismissCredits();},5000);
}
map.once('movestart',dismissCredits);
function loadFlatBasemap(){
 try{
  flatBasemap=L.maplibreGL({style:'/basemap-style',interactive:false,attributionControl:false}).addTo(map);
  flatBasemap.getMaplibreMap().once('load',presentCredits);
  flatBasemap.getMaplibreMap().on('error',()=>{
   document.getElementById('basemap-status').textContent='Base map is temporarily unavailable; weather layers remain available.';
  });
 }catch(_){
  document.getElementById('basemap-status').textContent='This device could not load the map-style basemap.';
 }
}
loadFlatBasemap();
map.createPane('terrain');map.getPane('terrain').style.zIndex=250;
map.getPane('terrain').style.mixBlendMode='multiply';map.getPane('terrain').style.pointerEvents='none';
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}',{pane:'terrain',opacity:.24,maxNativeZoom:16,maxZoom:12,attribution:'Terrain: Esri, USGS, NOAA'}).addTo(map);
L.circleMarker([config.lat,config.lon],{pane:'markerPane',radius:8,color:'#fff',weight:3,fillColor:'#1498ff',fillOpacity:1}).addTo(map).bindPopup(document.createTextNode(config.name));
const $=id=>document.getElementById(id);
const timeFormatter=new Intl.DateTimeFormat('en-US',{timeZone:'America/Antigua',weekday:'short',hour:'numeric',minute:'2-digit'});
const format=t=>timeFormatter.format(new Date(t*1000));
let observed=[],forecast=[],active=[],radarFrames=[],predictionFrames=[],playing=false,position=0,lastTick=0,holdUntil=0,holdAction='',loading=false,revision=0;
let timelineStart=0,timelineEnd=0,firstPlay=true;
let forecastMeta=null,forecastRetry=null,visibleLayers=new Set();
let lastLegendKind='',lastDetail='',mapStatus='LOADING';
function setMapStatus(value){mapStatus=value;map.getContainer().dataset.status=value;}
const loaded=new Map(),pending=new Map();
const key=f=>f.kind+':'+f.time+':'+f.url;
const radarTileSize=window.devicePixelRatio>=2?512:256;
window.seapointToggleInfo=()=>showInfo($('source-panel').hidden);
window.seapointUseNativeInfo=()=>{$('info-toggle').hidden=true;};
function notify(){if(window.SeaPointRadar)window.SeaPointRadar.postMessage('ready');}
notify();
function announce(message){$('availability').textContent=message;}
function observationEnd(){return radarFrames.length?radarFrames.at(-1).time:-Infinity;}
function setPlaying(value){
 playing=value;lastTick=0;holdUntil=0;holdAction='';
 if(value&&active.length){
  if(firstPlay&&radarFrames.length||position>=timelineEnd){position=timelineStart;render();}
  firstPlay=false;
 }
 $('play').innerHTML=value?'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 4v16m8-16v16" stroke-width="4"/></svg>':'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 4 14 8-14 8Z" fill="currentColor" stroke="none"/></svg>';
 $('play').setAttribute('aria-label',value?'Pause animation':'Play animation');
}
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
   layer=L.tileLayer(frame.url,{opacity:0,tileSize:256,maxNativeZoom:7,maxZoom:12,className:'rain-overlay',attribution:'Radar: RainViewer'});
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
}
function render(){
 if(!active.length)return false;
 const kind=radarFrames.length&&position<=observationEnd()?'observed':'forecast';
 const pool=kind==='observed'?radarFrames:predictionFrames;
 $('timeline').value=String(Math.round(position));$('clock').textContent=format(position);
 if(!pool.length||position<pool[0].time||position>pool.at(-1).time){
  for(const layer of visibleLayers)layer.setOpacity(0);visibleLayers.clear();
  setMapStatus('GAP');$('detail').textContent='No weather frame for this time';lastDetail='';
  $('notice').textContent='No frame available at the selected time';$('notice').hidden=false;return true;
 }
 const index=pool.findIndex(f=>f.time>=position);
 const high=index<0?pool.length-1:index,low=Math.max(0,high-1);
 const a=pool[low],b=pool[high];
 const blend=b.time>a.time?Math.max(0,Math.min(1,(position-a.time)/(b.time-a.time))):1;
 const shown=blend<.5?a:b;
 const first=loaded.get(key(a)),second=loaded.get(key(b));
 if(!first||!second){$('notice').textContent='Buffering weather frames…';$('notice').hidden=false;return false;}
 const next=new Set([first,second]);for(const layer of visibleLayers)if(!next.has(layer))layer.setOpacity(0);
 if(first===second)first.setOpacity(.78);
 else{first.setOpacity(.78*(1-blend));second.setOpacity(.78*blend);}
 visibleLayers=next;setMapStatus(kind==='forecast'?'FORECAST':'OBSERVED');
 const detail=kind==='forecast'?'Forecast rain · hourly model':'Observed radar · '+format(shown.time);
 if(detail!==lastDetail){$('detail').textContent=detail;lastDetail=detail;}
 legend(kind);
 const outside=kind==='forecast'&&!L.latLngBounds(forecastMeta.bounds).intersects(map.getBounds());
 $('notice').hidden=!outside;if(outside)$('notice').textContent='Outside the eastern Caribbean forecast coverage';
 return true;
}
function updateNowMarker(){
 const fraction=(Date.now()/1000-timelineStart)/(timelineEnd-timelineStart);
 $('now-marker').hidden=!Number.isFinite(fraction)||fraction<0||fraction>1;
 if(!$('now-marker').hidden)$('now-marker').style.left=(fraction*100)+'%';
}
async function activate(){
 const token=++revision;
 const candidatesObserved=observed.slice().sort((a,b)=>a.time-b.time);
 const candidatesForecast=forecast.slice().sort((a,b)=>a.time-b.time);
 const all=[...candidatesObserved,...candidatesForecast];
 if(!all.length){
  if(active.length)return; // A transient metadata failure must not erase usable images.
  setMapStatus('UNAVAILABLE');$('clock').textContent='No frames available';$('detail').textContent='';
  $('notice').textContent='Weather frames temporarily unavailable';$('notice').hidden=false;
  $('play').disabled=$('timeline').disabled=$('jump-latest').disabled=true;return;
 }
 if(!active.length){$('notice').textContent='Preparing weather playback…';$('notice').hidden=false;}
 const results=[];
 for(let i=0;i<all.length;i+=4){
  results.push(...await Promise.allSettled(all.slice(i,i+4).map(frameLayer)));
  if(token!==revision)return;
 }
 const failedKinds=new Set(all.filter((f,i)=>results[i].status==='rejected').map(f=>f.kind));
 const readyObserved=failedKinds.has('observed')?[]:candidatesObserved;
 const readyForecast=failedKinds.has('forecast')?[]:candidatesForecast;
 const cutoff=readyObserved.length?readyObserved.at(-1).time:-Infinity;
 const combined=[...readyObserved,...readyForecast.filter(f=>f.time>cutoff)].sort((a,b)=>a.time-b.time);
 if(!combined.length){
  if(active.length){announce('Weather update unavailable; retaining loaded images.');return;}
  setMapStatus('UNAVAILABLE');$('clock').textContent='Playback unavailable';$('notice').textContent='Weather images unavailable. Retry shortly.';$('notice').hidden=false;return;
 }
 const hadFrames=active.length>0;
 radarFrames=readyObserved;predictionFrames=readyForecast;active=combined;
 timelineStart=radarFrames.length?radarFrames[0].time:Math.max(Date.now()/1000,predictionFrames[0].time);
 timelineEnd=predictionFrames.length?Math.min(forecastMeta.forecast_until||Date.now()/1000+48*3600,predictionFrames.at(-1).time):observationEnd();
 if(timelineEnd<timelineStart)timelineEnd=timelineStart;
 if(!hadFrames||(firstPlay&&radarFrames.length&&!playing))position=radarFrames.length?observationEnd():timelineStart;
 position=Math.min(timelineEnd,Math.max(timelineStart,position));
 $('timeline').min=String(Math.floor(timelineStart));$('timeline').max=String(Math.floor(timelineEnd));
 $('start').textContent=format(timelineStart);$('end').textContent=format(timelineEnd);
 $('timeline').disabled=timelineEnd<=timelineStart;$('play').disabled=timelineEnd<=timelineStart;$('jump-latest').disabled=false;
 $('jump-latest').setAttribute('aria-label','Go to now');
 updateNowMarker();cleanLayers();lastDetail='';render();
 if(failedKinds.size)announce('One weather source is unavailable; showing the available coverage.');
}
$('play').onclick=()=>setPlaying(!playing);
$('timeline').oninput=()=>{setPlaying(false);firstPlay=false;position=Number($('timeline').value);render();};
function tick(ms){
 if(playing&&active.length>1){
  if(lastTick){
   if(holdUntil){
    if(ms>=holdUntil){
     position=holdAction==='forecast'?Math.max(observationEnd()+1,predictionFrames[0].time):timelineStart;
     holdUntil=0;holdAction='';render();
    }
   }else{
    const inObserved=radarFrames.length&&position<=observationEnd();
    const rate=inObserved?360:2160;
    const candidate=position+Math.min(ms-lastTick,100)*rate/1000;
    const old=position;
    if(inObserved&&predictionFrames.length&&timelineEnd>observationEnd()&&candidate>observationEnd()){
     position=observationEnd();holdAction='forecast';holdUntil=ms+2500;
    }else if(candidate>=timelineEnd){
     position=timelineEnd;holdAction='loop';holdUntil=ms+(inObserved?2500:1500);
    }else position=candidate;
    if(render()===false){position=old;holdUntil=0;holdAction='';}
   }
  }
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
  observed=(data.frames||[]).filter(f=>Number.isFinite(f.time)&&f.path&&f.time<=now+60&&f.time>=now-3*3600).slice(-8).map(f=>({kind:'observed',time:f.time,url:(data.host||'https://tilecache.rainviewer.com')+f.path+'/'+radarTileSize+'/{z}/{x}/{y}/2/1_1.png'}));
 }catch(_){observed=[];announce('Observed radar unavailable; forecast may still be available.');}
 if(previous!==observed.map(key).join(',')||!radarFrames.length)await activate();
}
async function loadForecast(){
 if(loading)return;loading=true;
 try{
  const response=await fetch('/forecast-frames');const data=await response.json();
  if(response.status===202){announce('Preparing the 48-hour forecast. Radar remains available.');clearTimeout(forecastRetry);forecastRetry=setTimeout(loadForecast,15000);return;}
  if(!response.ok||data.status!=='ready')throw new Error();
  forecastMeta=data;const now=Date.now()/1000;
  const upcoming=(data.frames||[]).filter(f=>Number.isFinite(f.time)&&f.url&&f.time>=now-3600&&f.time<=Math.ceil(now/3600)*3600+48*3600).map(f=>({...f,kind:'forecast'}));
  if(upcoming.length<2)throw new Error();
  const changed=upcoming.map(key).join(',')!==forecast.map(key).join(',');forecast=upcoming;
  announce('Forecast available through '+format(forecast.at(-1).time)+' · hourly data, smoothly blended.');
  $('model-run').textContent='Forecast model run: '+format(data.model_run)+' Antigua time.';
  if(changed||!predictionFrames.length)await activate();
 }catch(_){announce(forecast.length?'Forecast update unavailable; retaining cached forecast through '+format(forecast.at(-1).time):'Forecast temporarily unavailable. Observed radar remains available.');}
 finally{loading=false;}
}
loadObserved();loadForecast();setInterval(loadObserved,300000);setInterval(loadForecast,900000);setInterval(updateNowMarker,60000);
$('zoom-in').onclick=()=>map.zoomIn();$('zoom-out').onclick=()=>map.zoomOut();
$('recenter').onclick=()=>map.setView([config.lat,config.lon],10.5);
$('jump-latest').onclick=()=>{if(!active.length)return;setPlaying(false);firstPlay=false;position=radarFrames.length?observationEnd():Math.min(timelineEnd,Math.max(Date.now()/1000,timelineStart));render();};
function showInfo(show){dismissCredits();$('source-panel').hidden=!show;$('info-toggle').setAttribute('aria-expanded',String(show));if(show)$('source-close').focus();else $('info-toggle').focus();}
$('info-toggle').onclick=()=>showInfo($('source-panel').hidden);
$('source-close').onclick=()=>showInfo(false);
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('source-panel').hidden)showInfo(false);});

</script></body></html>'''
