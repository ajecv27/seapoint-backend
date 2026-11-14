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
<p><a href="https://www.data.gouv.fr/datasets/paquets-arome-outre-mer-antilles-resolution-0-025deg" target="_blank" rel="noopener">Météo-France AROME Antilles</a> supplies the regional forecast on a 2.5 km grid. It shows mean rain rate over each preceding forecast hour. Source: Météo-France, Etalab Open Licence 2.0.</p><p><a href="https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast" target="_blank" rel="noopener">NOAA GFS</a> supplies worldwide rain in the published map, the final hours of the rolling 48-hour outlook, and the fallback outside the finer regional data. Its grid is approximately 28 km and shows instantaneous precipitation rate in water-equivalent mm/h; colder regions can include frozen precipitation. Model changes use actual frames, without morphing one model into another. Motion interpolation adds no forecast resolution.</p>
<p id="coverage-details">Forecast coverage: eastern Caribbean, 10–23°N and 68–55°W. Forecast rain rates use mm/h. The timeline moves from observed radar into model forecasts; the label and legend identify each source.</p><p id="model-run"></p><p id="basemap-status">Loading map…</p><p>Map data: <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap contributors</a> · <a href="https://openmaptiles.org/" target="_blank" rel="noopener">© OpenMapTiles</a>. Map service: <a href="https://openfreemap.org/" target="_blank" rel="noopener">OpenFreeMap</a>. Terrain shading: Esri, USGS, NOAA.</p>
</section>
<footer id="player" aria-label="Animation controls"><div class="player-row">
<button id="play" aria-label="Play animation" disabled><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 4 14 8-14 8Z" fill="currentColor" stroke="none"/></svg></button><div class="time-block"><div id="clock">Loading radar</div><div id="detail">Observed rain</div></div>
<button id="jump-latest" aria-label="Go to now" disabled><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 5 10 7-10 7ZM19 5v14"/></svg></button>
</div><div class="scrubber"><span id="now-marker" hidden aria-label="Now"></span><input id="timeline" type="range" min="0" max="1" step="1" value="0" aria-label="Weather map time" disabled></div>
<div class="timeline-labels"><span id="start">Recent observations</span><span class="zone">Antigua time</span><span id="end">Latest</span></div></footer>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" onerror="window.seapointBootFailed=true;if(window.SeaPointRadar)window.SeaPointRadar.postMessage('error');"></script>
<script>
'use strict';
const config=__CONFIG__;
document.title='SeaPoint Rain Map · '+config.name;
const map=L.map('map',{zoomControl:false,attributionControl:false,zoomSnap:.5,zoomDelta:.5}).setView([config.lat,config.lon],10.5);
let flatBasemap=null,terrainLayer=null,optionalDisposed=false;
const optionalResources=new Map();
function optionalResource(url,stylesheet=false){
 if(optionalResources.has(url))return optionalResources.get(url);
 const task=new Promise((resolve,reject)=>{
  const node=document.createElement(stylesheet?'link':'script');
  if(stylesheet){node.rel='stylesheet';node.href=url;}else{node.src=url;node.async=true;}
  const finish=error=>{clearTimeout(timer);node.onload=node.onerror=null;if(error){node.remove();reject(error);}else resolve();};
  const timer=setTimeout(()=>finish(new Error('Map resource timed out')),30000);
  node.onload=()=>finish();node.onerror=()=>finish(new Error('Map resource unavailable'));
  document.head.appendChild(node);
 }).catch(error=>{optionalResources.delete(url);throw error;});
 optionalResources.set(url,task);return task;
}
function dismissCredits(){document.getElementById('credits-notice').hidden=true;}
function presentCredits(){
 const credit=document.getElementById('credits-notice');credit.hidden=false;
 setTimeout(()=>{if(!credit.contains(document.activeElement))dismissCredits();},5000);
}
map.once('movestart',dismissCredits);
function loadFlatBasemap(){
 if(optionalDisposed||flatBasemap)return;
 try{
  flatBasemap=L.maplibreGL({style:'/basemap-style',interactive:false,attributionControl:false}).addTo(map);
  flatBasemap.getMaplibreMap().once('load',()=>{document.getElementById('basemap-status').textContent='';presentCredits();loadTerrain();});
  flatBasemap.getMaplibreMap().on('error',()=>{
   document.getElementById('basemap-status').textContent='Base map is temporarily unavailable; weather layers remain available.';
  });
 }catch(_){
  document.getElementById('basemap-status').textContent='This device could not load the map-style basemap.';
 }
}
function loadTerrain(){
 if(optionalDisposed||terrainLayer)return;
 map.createPane('terrain');map.getPane('terrain').style.zIndex=250;
 map.getPane('terrain').style.mixBlendMode='multiply';map.getPane('terrain').style.pointerEvents='none';
 terrainLayer=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}',{pane:'terrain',opacity:.24,maxNativeZoom:16,maxZoom:12,attribution:'Terrain: Esri, USGS, NOAA'}).addTo(map);
}
async function loadOptionalMap(attempt=0){
 try{
  await Promise.all([optionalResource('https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css',true),optionalResource('https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js')]);
  await optionalResource('https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js');
  loadFlatBasemap();
 }catch(_){
  if(optionalDisposed)return;
  document.getElementById('basemap-status').textContent=attempt?'Base map is temporarily unavailable; weather layers remain available.':'Base map is reconnecting; weather layers remain available.';
  if(!attempt)setTimeout(()=>{if(!optionalDisposed)loadOptionalMap(1);},5000);
 }
}
L.circleMarker([config.lat,config.lon],{pane:'markerPane',radius:8,color:'#fff',weight:3,fillColor:'#1498ff',fillOpacity:1}).addTo(map).bindPopup(document.createTextNode(config.name));
const $=id=>document.getElementById(id);
const timeFormatter=new Intl.DateTimeFormat('en-US',{timeZone:'America/Antigua',weekday:'short',hour:'numeric',minute:'2-digit'});
const format=t=>timeFormatter.format(new Date(t*1000));
let observed=[],forecast=[],active=[],radarFrames=[],predictionFrames=[],playing=false,position=0,lastTick=0,holdUntil=0,holdAction='',loading=false,revision=0;
let timelineStart=0,timelineEnd=0,firstPlay=true;
let forecastMeta=null,forecastRetry=null,visibleLayers=new Set(),forecastState='preparing',forecastEverPublished=false,forecastMetadataHealthy=false;
let activationPromise=null,activationQueued=false,observedLoading=false,forecastRetryRequested=false,lastRecovery=0;
const FORECAST_RETRY_MS=15000,FORECAST_DEADLINE_MS=45000;
let lastLegendKind='',lastDetail='',mapStatus='LOADING';
function setMapStatus(value){mapStatus=value;map.getContainer().dataset.status=value;}
const loaded=new Map(),pending=new Map();
const provider=f=>f.provider||'noaa-gfs';
const key=f=>f.kind+':'+provider(f)+':'+(f.model_run||'')+':'+f.time+':'+f.url+':'+(f.global_tiles?.url_template||'');
const sameForecastSource=(a,b)=>provider(a)===provider(b)&&a.model_run===b.model_run&&a.global_tiles?.model_run===b.global_tiles?.model_run&&JSON.stringify(a.bounds)===JSON.stringify(b.bounds);
const radarTileSize=window.devicePixelRatio>=2?512:256;
// Only one full-resolution pair is uploaded to the GPU. Flow fields are kept
// in a bounded worker cache; no extra forecast images are generated or fetched.
const MotionOverlay=L.Layer.extend({
 onAdd(map){this._map=map;this._canvas=L.DomUtil.create('canvas','rain-motion-canvas');this._canvas.id='rain-motion-canvas';this._canvas.style.cssText='position:absolute;pointer-events:none;display:none;opacity:.78;';map.getPane('overlayPane').appendChild(this._canvas);},
 onRemove(){this._canvas.remove();},
 getEvents(){return {zoomend:this._reset,viewreset:this._reset};},
 setBounds(bounds){this._bounds=L.latLngBounds(bounds);this._reset();},
 _reset(){if(!this._bounds||!this._map)return;const nw=this._map.latLngToLayerPoint(this._bounds.getNorthWest()),se=this._map.latLngToLayerPoint(this._bounds.getSouthEast());L.DomUtil.setPosition(this._canvas,nw);this._canvas.style.width=Math.max(1,se.x-nw.x)+'px';this._canvas.style.height=Math.max(1,se.y-nw.y)+'px';}
});
const rainMotionOverlay=new MotionOverlay().addTo(map);
let rainMotionRenderer=null;
async function loadOptionalMotion(attempt=0){
 try{
  await optionalResource('/rain-motion.js?v=6');
  if(optionalDisposed||rainMotionRenderer||!window.SeaPointRainMotion)return;
  rainMotionRenderer=SeaPointRainMotion.createRenderer(rainMotionOverlay._canvas,{cacheSize:4,workingSize:256,gridSize:64,maxDisplacement:24});
  motionStatus=rainMotionRenderer.supported?'idle':'unsupported';
  if(active.length&&!motionViewChanging)render();
 }catch(_){
  if(optionalDisposed)return;
  motionStatus='unsupported';
  if(!attempt)setTimeout(()=>{if(!optionalDisposed)loadOptionalMotion(1);},5000);
 }
}
let motionViewChanging=false,motionViewRevision=0,motionReadyKey='',motionJob=null,motionWanted=null,motionBuffered=false,motionPrefetch=null;
const motionPrefetchedKeys=new Set();
let motionStatus=rainMotionRenderer&&rainMotionRenderer.supported?'idle':'unsupported';
const motionFailures=new Map(),readableTiles=new Map();
window.seapointMotionState=()=>({supported:!!(rainMotionRenderer&&rainMotionRenderer.supported),state:motionStatus,kind:motionWanted&&motionWanted.a.kind,pair:motionReadyKey,viewChanging:motionViewChanging,buffering:motionBuffered,prefetching:!!motionPrefetch,captureCacheSize:readableTiles.size,renderer:rainMotionRenderer&&rainMotionRenderer.stats});
function hideRainMotion(){rainMotionOverlay._canvas.style.display='none';}
function motionPairKey(a,b){return key(a)+'|'+key(b)+(a.kind==='observed'||a.global_tiles?'|view:'+motionViewRevision:'');}
function readableTile(image){
 const url=image.currentSrc||image.src;if(readableTiles.has(url))return readableTiles.get(url);
 const task=new Promise((resolve,reject)=>{const copy=new Image();copy.crossOrigin='anonymous';copy.decoding='async';const timer=setTimeout(()=>{copy.src='';reject(new Error('Radar pixels unavailable'));},6000);copy.onload=()=>{clearTimeout(timer);resolve(copy);};copy.onerror=()=>{clearTimeout(timer);reject(new Error('Radar pixels unavailable'));};copy.src=url;});
 readableTiles.set(url,task);while(readableTiles.size>24)readableTiles.delete(readableTiles.keys().next().value);return task;
}
async function captureRainFrame(frame,layer){
 const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d',{willReadFrequently:true});
 if(frame.kind==='forecast'){
  if(frame.global_tiles){
   const image=await layer.ensureView();canvas.width=image.width;canvas.height=image.height;ctx.drawImage(image,0,0);
   return {pixels:ctx.getImageData(0,0,canvas.width,canvas.height),bounds:layer._bounds};
  }
  const image=layer.getElement();if(!image||!image.naturalWidth)throw new Error('Forecast image unavailable');
  canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;ctx.drawImage(image,0,0);
  return {pixels:ctx.getImageData(0,0,canvas.width,canvas.height),bounds:frame.bounds||forecastMeta.bounds};
 }
 // A new zoom starts downloading tiles before moveend. Capture only after
 // that load settles, so slow tiles do not disable movement for this view.
 if(layer.isLoading&&layer.isLoading())await new Promise((resolve,reject)=>{
  const finish=()=>{clearTimeout(timer);layer.off('load',finish);resolve();};
  const timer=setTimeout(()=>{layer.off('load',finish);reject(new Error('Radar tiles still loading'));},6000);
  layer.on('load',finish);
  if(!layer.isLoading())finish();
 });
 const rect=map.getContainer().getBoundingClientRect();
 const scale=Math.min(window.devicePixelRatio||1,2,1024/Math.max(rect.width,rect.height));
 canvas.width=Math.max(1,Math.round(rect.width*scale));canvas.height=Math.max(1,Math.round(rect.height*scale));
 ctx.scale(scale,scale);
 const tiles=Object.values(layer._tiles||{}).filter(tile=>{const image=tile.el;if(!image||!image.complete||!image.naturalWidth)return false;const r=image.getBoundingClientRect();return r.width>0&&r.height>0&&r.right>rect.left&&r.left<rect.right&&r.bottom>rect.top&&r.top<rect.bottom;});
 if(!tiles.length)throw new Error('Visible radar tiles unavailable');
 const images=await Promise.all(tiles.map(tile=>readableTile(tile.el)));
 for(let i=0;i<tiles.length;i++){const r=tiles[i].el.getBoundingClientRect();ctx.drawImage(images[i],r.left-rect.left,r.top-rect.top,r.width,r.height);}
 return {pixels:ctx.getImageData(0,0,canvas.width,canvas.height),bounds:map.getBounds()};
}
function prefetchFollowingMotion(a,b){
 if(!playing||motionPrefetch||!rainMotionRenderer||!rainMotionRenderer.prefetchPair||motionViewChanging)return;
 const pool=b.kind==='forecast'?predictionFrames:radarFrames,index=pool.indexOf(b),next=pool[index+1];
 if(!next||next.kind!==b.kind||next.time-b.time>(b.kind==='observed'?900:5400)||(b.kind==='forecast'&&!sameForecastSource(b,next)))return;
 const id=motionPairKey(b,next);if(motionPrefetchedKeys.has(id))return;
 const first=loaded.get(key(b)),second=loaded.get(key(next));if(!first||!second)return;
 motionPrefetchedKeys.add(id);while(motionPrefetchedKeys.size>8)motionPrefetchedKeys.delete(motionPrefetchedKeys.values().next().value);
 const job={id,view:motionViewRevision};motionPrefetch=job;
 Promise.all([captureRainFrame(b,first),captureRainFrame(next,second)]).then(frames=>{
  if(motionViewChanging||((b.kind==='observed'||b.global_tiles)&&job.view!==motionViewRevision))return;
  return rainMotionRenderer.prefetchPair(frames[0].pixels,frames[1].pixels,id);
 }).catch(()=>{}).finally(()=>{if(motionPrefetch===job)motionPrefetch=null;});
}
function boundedMotionFailure(id){motionFailures.set(id,Date.now()+60000);while(motionFailures.size>12)motionFailures.delete(motionFailures.keys().next().value);}
function startMotionPreparation(){
 if(motionJob||!motionWanted||motionViewChanging||!rainMotionRenderer||!rainMotionRenderer.supported)return;
 const job=motionWanted;motionJob=job;motionReadyKey='';
 // Playback retains its last presentation until the next pair is ready.
 // Replacing it with the pair's first source image makes rain jump backwards.
 if(!playing)hideRainMotion();
 motionStatus='preparing';
 Promise.all([captureRainFrame(job.a,job.first),captureRainFrame(job.b,job.second)]).then(async frames=>{
  if(motionWanted!==job||motionViewChanging)return;
  if(frames[0].pixels.width!==frames[1].pixels.width||frames[0].pixels.height!==frames[1].pixels.height)throw new Error('Frame dimensions differ');
  const prepared=await rainMotionRenderer.preparePair(frames[0].pixels,frames[1].pixels,job.id);
  if(motionWanted!==job||motionViewChanging)return;
  if(!prepared){boundedMotionFailure(job.id);motionStatus='unmatched';return;}
  rainMotionOverlay.setBounds(frames[0].bounds);motionReadyKey=job.id;motionStatus='ready';
 }).catch(()=>{boundedMotionFailure(job.id);if(motionWanted===job)motionStatus='unavailable';}).finally(()=>{
  motionJob=null;
  if(motionWanted&&motionWanted!==job)startMotionPreparation();
  // Also update a paused scrubbed view once its motion field is ready.
  if(!motionViewChanging)render();
 });
}
function renderMotionPair(a,b,first,second,blend){
 if(!rainMotionRenderer||!rainMotionRenderer.supported||motionViewChanging)return false;
 const id=motionPairKey(a,b);
 if((motionFailures.get(id)||0)>Date.now())return false;
 if(!motionWanted||motionWanted.id!==id)motionWanted={a,b,first,second,id};
 if(motionReadyKey!==id){startMotionPreparation();motionBuffered=playing&&!!motionJob;return false;}
 if(!rainMotionRenderer.render(blend)){motionStatus='unavailable';return false;}
 first.setOpacity(0);second.setOpacity(0);rainMotionOverlay._canvas.style.display='block';motionStatus=rainMotionRenderer.stats.mode==='motion'?'moving':rainMotionRenderer.stats.mode==='stationary'?'stationary':'blending';prefetchFollowingMotion(a,b);return true;
}
map.on('movestart zoomstart',()=>{motionViewChanging=true;hideRainMotion();if(active.length)render();});
map.on('moveend zoomend',()=>{motionViewChanging=false;motionViewRevision++;motionWanted=null;hideRainMotion();if(active.length)render();});
window.addEventListener('pagehide',event=>{if(!event.persisted){optionalDisposed=true;if(rainMotionRenderer)rainMotionRenderer.dispose();}readableTiles.clear();});

window.seapointToggleInfo=()=>showInfo($('source-panel').hidden);
window.seapointUseNativeInfo=()=>{$('info-toggle').hidden=true;};
function notify(){window.seapointBootReady=true;if(window.SeaPointRadar)window.SeaPointRadar.postMessage('ready');}
function announce(message){$('availability').textContent=message;}
function observationEnd(){return radarFrames.length?radarFrames.at(-1).time:-Infinity;}
function validGlobalFrame(frame,now){
 const g=frame.global_tiles;if(!g)return true;
 const hour=(frame.time-g.model_run)/3600;
 const cycle=Number.isFinite(g.model_run)?new Date(g.model_run*1000).toISOString().slice(0,13).replace(/\D/g,''):'';
 return Number.isInteger(g.model_run)&&g.model_run%21600===0&&now-g.model_run>=-60&&now-g.model_run<24*3600&&Number.isFinite(g.fetched_at)&&g.fetched_at>=g.model_run&&g.fetched_at<=now+60&&Number.isInteger(hour)&&hour>=1&&hour<=120&&g.max_zoom===4&&g.tile_size===256&&g.units==='mm/h'&&g.url_template==='data/world/'+cycle+'-'+String(hour).padStart(3,'0')+'-g1/{z}/{x}/{y}.png';
}
function validForecastFrame(frame,now=Date.now()/1000){
 return Number.isFinite(frame.model_run)&&now-frame.model_run>=-60&&now-frame.model_run<24*3600&&frame.time>=now-3600&&frame.time<=Math.ceil(now/3600)*3600+48*3600&&validGlobalFrame(frame,now);
}
function forecastCoverageComplete(){
 if(!forecastMeta||forecastMeta.coverage_complete===false||!forecast.length||!predictionFrames.some(f=>f.time>Date.now()/1000))return false;
 const ready=new Set(predictionFrames.map(key));
 return forecast[0].time<=Date.now()/1000+60&&forecast.every((frame,i)=>validForecastFrame(frame)&&ready.has(key(frame))&&(!i||frame.time-forecast[i-1].time<=5400))&&predictionFrames.at(-1).time>=Date.now()/1000+48*3600;
}
function updateForecastStatus(){
 const future=predictionFrames.filter(frame=>validForecastFrame(frame)&&frame.time>Date.now()/1000);
 if(future.length){
  const end=Math.min(timelineEnd,future.at(-1).time);
  announce(forecastState==='reconnecting'?'Forecast update unavailable; retaining loaded forecast through '+format(end)+'. Retrying automatically…':'Forecast available through '+format(end)+' · hourly data with display motion interpolation.'+(forecastCoverageComplete()?'':' Updating forecast coverage…'));
  const sources=new Map();
  for(const frame of predictionFrames){
   const id=provider(frame)+':'+frame.model_run;
   if(!sources.has(id))sources.set(id,frame);
  }
  $('model-run').textContent=[...sources.values()].map(frame=>(provider(frame)==='arome-antilles'?'Météo-France AROME Antilles (~2.5 km, hourly mean rain)':'NOAA GFS (~28 km, instantaneous rain)')+': model issued '+format(frame.model_run)+' Antigua time.').join(' ');
 }else{
  announce(forecastState==='preparing'?'Preparing the 48-hour forecast.':'Forecast temporarily unavailable. Reconnecting automatically…');
  $('model-run').textContent='';
 }
 lastDetail='';if(active.length)render();
}
function scheduleForecastRetry(){
 if(forecastMetadataHealthy&&forecastCoverageComplete()&&!forecastMeta?.updating){clearTimeout(forecastRetry);forecastRetry=null;return;}
 if(forecastRetry!==null)return;
 forecastRetry=setTimeout(()=>{forecastRetry=null;loadForecast();},FORECAST_RETRY_MS);
}
window.seapointForecastState=()=>({loading,retryScheduled:forecastRetry!==null,state:forecastState,frameCount:predictionFrames.length,coverageComplete:forecastCoverageComplete(),metadataHealthy:forecastMetadataHealthy});
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
 if(frame.kind==='forecast'&&frame.global_tiles){
  const layer=SeaPointGlobalRain.createLayer(frame,{isActive:()=>visibleLayers.has(layer)}).addTo(map);loaded.set(id,layer);
  layer.on('load',()=>{if(motionWanted&&(motionWanted.first===layer||motionWanted.second===layer))motionFailures.delete(motionWanted.id);if(!motionViewChanging)render();});
  layer.on('error',()=>{if(!motionViewChanging)render();});
  return Promise.resolve(layer);
 }
 const task=new Promise((resolve,reject)=>{
  let layer,successes=0,settled=false;
  const finish=ok=>{if(settled)return;settled=true;clearTimeout(timeout);if(ok){loaded.set(id,layer);resolve(layer);}else{if(layer)map.removeLayer(layer);reject(new Error('Map frame unavailable'));}};
  const timeout=setTimeout(()=>finish(false),25000);
  if(frame.kind==='forecast'){
   layer=L.imageOverlay(frame.url,frame.bounds||forecastMeta.bounds,{opacity:0,interactive:false,attribution:provider(frame)==='arome-antilles'?'Forecast: Météo-France, Etalab Open Licence 2.0':'Forecast: NOAA GFS'});
   layer.once('load',()=>finish(true));layer.once('error',()=>finish(false));
  }else{
   layer=L.tileLayer(frame.url,{opacity:0,tileSize:256,maxNativeZoom:7,maxZoom:12,className:'rain-overlay',attribution:'Radar: RainViewer'});
   layer.on('tileload',()=>{successes++;});layer.once('load',()=>finish(successes>0));
   layer.on('load',()=>{
    if(motionWanted&&(motionWanted.first===layer||motionWanted.second===layer)&&motionFailures.has(motionWanted.id)){
     motionFailures.delete(motionWanted.id);if(!motionViewChanging)render();
    }
   });
  }
  layer.addTo(map);
 });pending.set(id,task);task.finally(()=>pending.delete(id)).catch(()=>{});return task;
}
function cleanLayers(){
 const keep=new Set([...observed,...forecast,...radarFrames,...predictionFrames].map(key));
 for(const [id,layer]of loaded)if(!keep.has(id)&&!visibleLayers.has(layer)){map.removeLayer(layer);loaded.delete(id);}
}
function legend(kind){
 if(lastLegendKind===kind)return;
 lastLegendKind=kind;$('legend').classList.toggle('radar',kind==='observed');
 $('legend').setAttribute('aria-label',kind==='forecast'?'Forecast rain intensity, mm per hour':'Observed radar intensity, RainViewer scale');
}
function render(){
 motionBuffered=false;
 if(!active.length)return false;
 const kind=radarFrames.length&&position<=observationEnd()?'observed':'forecast';
 const pool=kind==='observed'?radarFrames:predictionFrames.some(frame=>validForecastFrame(frame)&&frame.time>Date.now()/1000)?predictionFrames.filter(frame=>validForecastFrame(frame)):[];
 $('timeline').value=String(Math.round(position));$('clock').textContent=format(position);
 if(!pool.length||position<pool[0].time||position>pool.at(-1).time){
  hideRainMotion();motionWanted=null;
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
 const gap=b.time-a.time;
 if(!first||!second||(position>a.time&&position<b.time&&gap>(kind==='observed'?900:5400))){
  hideRainMotion();motionWanted=null;for(const layer of visibleLayers)layer.setOpacity(0);visibleLayers.clear();
  setMapStatus('GAP');$('detail').textContent='Weather frame unavailable · retrying';lastDetail='';
  $('notice').textContent='No frame available at the selected time';$('notice').hidden=false;return true;
 }
 const waitingViews=[first,second].filter(layer=>layer.isReadyForView&&!layer.isReadyForView());
 if(waitingViews.length){
  for(const layer of waitingViews)layer.ensureView().catch(()=>{});
  motionBuffered=playing;$('notice').hidden=false;
  $('notice').textContent=waitingViews.some(layer=>layer.viewFailed())?'Weather tiles unavailable. Retrying…':'Loading forecast for this map area…';
  return false;
 }
 // Original timestamps show the actual image. Verified patterns move;
 // weak matches grow/dissipate continuously rather than jumping at halfway.
 const canInterpolate=a!==b && gap>0 && gap<=(kind==='observed'?900:5400) && (kind!=='forecast'||sameForecastSource(a,b)) && blend>0 && blend<1;
 const motionRendered=canInterpolate&&renderMotionPair(a,b,first,second,blend);
 if(motionBuffered){
  // Keep both the GPU pixels and source-layer opacities untouched. The clock
  // buffers too, so no earlier frame appears while a worker catches up.
  $('notice').textContent='Preparing smooth rain playback…';$('notice').hidden=false;
  return false;
 }
 const next=new Set([first,second]);for(const layer of visibleLayers)if(!next.has(layer))layer.setOpacity(0);
 if(!motionRendered){
  hideRainMotion();
  if(first===second){first.setOpacity(.78);}
  else if(canInterpolate){
   // A smooth, opacity-corrected image transition remains usable without GPU
   // motion or readable pixels; no unverified path is assigned to a rain cell.
   const upper=.78*blend;first.setOpacity(.78*(1-blend)/(1-upper));second.setOpacity(upper);
   motionStatus='blending';
  }else{const actual=blend<.5?first:second;first.setOpacity(actual===first ? .78 : 0);second.setOpacity(actual===second ? .78 : 0);}
 }
 visibleLayers=next;setMapStatus(kind==='forecast'?'FORECAST':'OBSERVED');
 const waiting=!predictionFrames.some(frame=>validForecastFrame(frame)&&frame.time>Date.now()/1000);
 const detail=kind==='forecast'?'Forecast rain · hourly model':waiting?'Radar · '+(forecastState==='preparing'?'Preparing 48-hour forecast…':'Reconnecting forecast…'):'Observed radar · '+format(shown.time);
 if(detail!==lastDetail){$('detail').textContent=detail;lastDetail=detail;}
 legend(kind);
 const outside=kind==='forecast'&&!shown.global_tiles&&!L.latLngBounds(shown.bounds||forecastMeta.bounds).intersects(map.getBounds());
 $('notice').hidden=!outside&&!motionBuffered;if(outside)$('notice').textContent='Outside the eastern Caribbean forecast coverage';else if(motionBuffered)$('notice').textContent='Preparing smooth rain playback…';
 return !motionBuffered;
}
function updateNowMarker(){
 const fraction=(Date.now()/1000-timelineStart)/(timelineEnd-timelineStart);
 $('now-marker').hidden=!Number.isFinite(fraction)||fraction<0||fraction>1;
 if(!$('now-marker').hidden)$('now-marker').style.left=(fraction*100)+'%';
}
function publishReadyFrames(finished=false){
 const now=Date.now()/1000;
 const readyObserved=observed.filter(frame=>frame.time>=now-3*3600&&loaded.has(key(frame))).sort((a,b)=>a.time-b.time);
 // Keep valid downloaded images during a failed update. A successful image
 // replaces only its own timestamp; different model runs never morph together.
 const byTime=new Map(predictionFrames.filter(frame=>validForecastFrame(frame,now)&&loaded.has(key(frame))).map(frame=>[frame.time,frame]));
 for(const frame of forecast)if(validForecastFrame(frame,now)&&loaded.has(key(frame)))byTime.set(frame.time,frame);
 let readyForecast=[...byTime.values()].sort((a,b)=>a.time-b.time);
 if(!readyForecast.some(frame=>frame.time>now))readyForecast=[];
 const cutoff=readyObserved.length?readyObserved.at(-1).time:-Infinity;
 const combined=[...readyObserved,...readyForecast.filter(frame=>frame.time>cutoff)].sort((a,b)=>a.time-b.time);
 const hadFrames=active.length>0,changed=active.map(key).join(',')!==combined.map(key).join(',');
 radarFrames=readyObserved;predictionFrames=readyForecast;active=combined;
 if(!active.length){
  hideRainMotion();motionWanted=null;for(const layer of visibleLayers)layer.setOpacity(0);visibleLayers.clear();
  if(finished){
   setPlaying(false);setMapStatus('UNAVAILABLE');$('clock').textContent='Playback unavailable';
   $('detail').textContent=forecastState==='preparing'?'Preparing 48-hour forecast…':'Reconnecting forecast…';
   $('notice').textContent='Weather images unavailable. Retrying automatically…';$('notice').hidden=false;
  }
  $('play').disabled=$('timeline').disabled=$('jump-latest').disabled=true;
  cleanLayers();updateForecastStatus();return;
 }
 timelineStart=radarFrames.length?radarFrames[0].time:Math.max(now,predictionFrames[0].time);
 const endpoint=predictionFrames.at(-1);
 timelineEnd=endpoint?Math.min(endpoint.forecast_until||now+48*3600,endpoint.time):observationEnd();
 if(timelineEnd<timelineStart)timelineEnd=timelineStart;
 if(!hadFrames||(firstPlay&&radarFrames.length&&!playing))position=radarFrames.length?observationEnd():timelineStart;
 position=Math.min(timelineEnd,Math.max(timelineStart,position));
 if(changed){
  revision++;
  const published=new Set([...radarFrames,...predictionFrames].map(key));
  if(motionWanted&&(!published.has(key(motionWanted.a))||!published.has(key(motionWanted.b)))){motionWanted=null;hideRainMotion();}
 }
 $('timeline').min=String(Math.floor(timelineStart));$('timeline').max=String(Math.floor(timelineEnd));
 $('start').textContent=format(timelineStart);$('end').textContent=format(timelineEnd);
 $('timeline').disabled=$('play').disabled=timelineEnd<=timelineStart;$('jump-latest').disabled=false;
 if(timelineEnd<=timelineStart&&playing)setPlaying(false);
 $('jump-latest').setAttribute('aria-label','Go to now');
 if(predictionFrames.some(frame=>frame.time>now))forecastEverPublished=true;
 if(forecastMetadataHealthy&&forecastCoverageComplete())forecastState='ready';
 updateNowMarker();updateForecastStatus();cleanLayers();
}
function activate(){
 if(activationPromise){activationQueued=true;return activationPromise;}
 activationQueued=false;
 const orderedForecast=forecast.slice().sort((a,b)=>a.time-b.time);
 // Get the near-now frames and the actual endpoint early, without increasing
 // the four-image download limit. Unloaded intervals stay visibly unavailable.
 const preferred=[...orderedForecast.slice(0,3),...orderedForecast.slice(-1),...orderedForecast.slice(3,-1)];
 const seen=new Set(),queue=[...observed.slice().sort((a,b)=>a.time-b.time),...preferred].filter(frame=>{const id=key(frame);if(seen.has(id)||loaded.has(id))return false;seen.add(id);return true;});
 publishReadyFrames();
 const worker=async()=>{
  while(queue.length){
   const frame=queue.shift(),id=key(frame);
   if(![...observed,...forecast].some(candidate=>key(candidate)===id))continue;
   try{await frameLayer(frame);}catch(_){if(frame.kind==='forecast')forecastState='reconnecting';}
   publishReadyFrames();
  }
 };
 activationPromise=Promise.all(Array.from({length:Math.min(4,queue.length)},worker)).finally(()=>{
  activationPromise=null;publishReadyFrames(true);scheduleForecastRetry();
  if(activationQueued){activationQueued=false;activate();}
 });
 return activationPromise;
}
$('play').onclick=()=>setPlaying(!playing);
$('timeline').oninput=()=>{setPlaying(false);firstPlay=false;position=Number($('timeline').value);render();};
function tick(ms){
 if(playing&&active.length>1){
  if(lastTick){
   if(holdUntil){
    if(ms>=holdUntil){
     position=holdAction==='forecast'&&predictionFrames.length?Math.max(observationEnd()+1,predictionFrames[0].time):timelineStart;
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
    if(render()===false){position=motionBuffered&&motionWanted?Math.max(old,Math.min(candidate,motionWanted.a.time)):old;$('timeline').value=String(Math.round(position));$('clock').textContent=format(position);holdUntil=0;holdAction='';}
   }
  }
  lastTick=ms;
 }else lastTick=0;
 requestAnimationFrame(tick);
}requestAnimationFrame(tick);
async function fetchWeatherJson(url,deadline){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),deadline);
 try{
  const response=await fetch(url,{signal:controller.signal,cache:'no-store'});
  const data=await response.json();return {response,data};
 }finally{clearTimeout(timer);}
}
async function loadObserved(){
 if(observedLoading)return;observedLoading=true;
 const previous=observed.map(key).join(',');
 try{
  const {response,data}=await fetchWeatherJson('/radar-frames',30000);if(!response.ok||!Array.isArray(data.frames))throw new Error();
  const now=Date.now()/1000;
  observed=data.frames.filter(f=>Number.isFinite(f.time)&&f.path&&f.time<=now+60&&f.time>=now-3*3600).slice(-8).map(f=>({kind:'observed',time:f.time,url:(data.host||'https://tilecache.rainviewer.com')+f.path+'/'+radarTileSize+'/{z}/{x}/{y}/2/1_1.png'}));
 }catch(_){observed=observed.filter(frame=>frame.time>=Date.now()/1000-3*3600);}
 finally{observedLoading=false;}
 if(previous!==observed.map(key).join(',')||!radarFrames.length)activate();
}
async function loadForecast(){
 if(loading){forecastRetryRequested=true;return;}
 loading=true;forecastRetryRequested=false;clearTimeout(forecastRetry);forecastRetry=null;
 try{
  // Render may need a cold start. Bound both headers and JSON parsing while
  // giving that startup time to finish; an aborted request retries itself.
  const {response,data}=await fetchWeatherJson('/forecast-frames',FORECAST_DEADLINE_MS);
  if(response.status===202){forecastMetadataHealthy=false;forecastState=forecastEverPublished?'reconnecting':'preparing';publishReadyFrames(!activationPromise);return;}
  if(!response.ok||data.status!=='ready'||!Array.isArray(data.frames)||!Array.isArray(data.bounds)||data.bounds.length!==2||data.bounds.some(point=>!Array.isArray(point)||point.length!==2||!point.every(Number.isFinite))||!Number.isFinite(data.model_run)||(data.forecast_until!==undefined&&!Number.isFinite(data.forecast_until)))throw new Error();
  const now=Date.now()/1000;
  const validBounds=b=>Array.isArray(b)&&b.length===2&&b.every(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite))&&b[0][0]<b[1][0]&&b[0][1]<b[1][1]&&b.every(p=>Math.abs(p[0])<=85&&Math.abs(p[1])<=180);
  const upcoming=data.frames.map(f=>({...f,kind:'forecast',provider:f.provider||'noaa-gfs',model_run:f.model_run??data.model_run,bounds:f.bounds||data.bounds,forecast_until:data.forecast_until})).filter(f=>Number.isFinite(f.time)&&f.url&&validBounds(f.bounds)&&['arome-antilles','noaa-gfs'].includes(f.provider)&&validForecastFrame(f,now));
  if(upcoming.length<2||!upcoming.some(frame=>frame.time>now)||(data.forecast_until!==undefined&&data.forecast_until<=now))throw new Error();
  if(upcoming.some(frame=>frame.global_tiles))await optionalResource('/global-rain.js?v=2');
  $('coverage-details').textContent=upcoming.some(frame=>frame.global_tiles)?'Forecast coverage: worldwide between 85°S and 85°N. NOAA GFS supplies global rain (~28 km model grid), with finer AROME Antilles data (~2.5 km) in its Caribbean footprint when available. Tiles load for the visible area and nearby motion context. Rain rates use mm/h. Observed radar coverage varies by location.':'Forecast coverage: eastern Caribbean, 10–23°N and 68–55°W. Rain rates use mm/h. Observed radar coverage varies by location.';
  forecastMetadataHealthy=true;forecastMeta=data;forecast=upcoming.sort((a,b)=>a.time-b.time);
  forecastState=forecastEverPublished?'updating':'preparing';
  // A ready manifest does not mean its images have arrived. The activation
  // drain publishes each successful image and retries holes in an unchanged run.
  activate();updateForecastStatus();
 }catch(_){
  forecastMetadataHealthy=false;forecastState='reconnecting';forecast=forecast.filter(frame=>validForecastFrame(frame));
  publishReadyFrames(!activationPromise);updateForecastStatus();
 }finally{
  loading=false;
  if(forecastRetryRequested||!forecastMetadataHealthy||!forecastCoverageComplete()||forecastMeta?.updating)scheduleForecastRetry();
 }
}
function refreshAfterResume(){
 const now=Date.now();if(now-lastRecovery<3000)return;lastRecovery=now;
 publishReadyFrames();loadObserved();loadForecast();
}
// These run inside the hosted page, so a phone recovers independently of the
// original laptop or a native WebView lifecycle callback.
document.addEventListener('visibilitychange',()=>{if(document.hidden)setPlaying(false);else refreshAfterResume();});
window.addEventListener('online',refreshAfterResume);
window.addEventListener('pageshow',refreshAfterResume);
window.addEventListener('focus',()=>{if(!document.hidden)refreshAfterResume();});
loadObserved();loadForecast();setInterval(loadObserved,300000);setInterval(loadForecast,900000);
setInterval(()=>{publishReadyFrames(!loading&&!activationPromise);updateNowMarker();scheduleForecastRetry();},60000);
$('zoom-in').onclick=()=>map.zoomIn();$('zoom-out').onclick=()=>map.zoomOut();
$('recenter').onclick=()=>map.setView([config.lat,config.lon],10.5);
// Let the basic map and controls paint before optional GPU/map resources load.
requestAnimationFrame(()=>{notify();loadOptionalMap();loadOptionalMotion();});
$('jump-latest').onclick=()=>{if(!active.length)return;setPlaying(false);firstPlay=false;position=radarFrames.length?observationEnd():Math.min(timelineEnd,Math.max(Date.now()/1000,timelineStart));render();};
function showInfo(show){dismissCredits();$('source-panel').hidden=!show;$('info-toggle').setAttribute('aria-expanded',String(show));if(show)$('source-close').focus();else $('info-toggle').focus();}
$('info-toggle').onclick=()=>showInfo($('source-panel').hidden);
$('source-close').onclick=()=>showInfo(false);
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('source-panel').hidden)showInfo(false);});

</script></body></html>'''
