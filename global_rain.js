/* Global forecast tiles and the existing fine regional field, composed only
 * for the visible map. Neither the whole world nor 48 canvases load at start. */
(function(root,factory){
 'use strict';const api=factory(root);
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(root)root.SeaPointGlobalRain=api;
})(typeof globalThis==='object'?globalThis:this,function(root){
 'use strict';
 const TILE=256,LIMIT=85.0511287798066;
 function project(lat,lon,z){
  lat=Math.max(-LIMIT,Math.min(LIMIT,lat));const size=TILE*2**z;
  return {x:(lon+180)/360*size,y:(1-Math.asinh(Math.tan(lat*Math.PI/180))/Math.PI)/2*size};
 }
 function tilePlan(nw,se,z){
  if(![nw.x,nw.y,se.x,se.y,z].every(Number.isFinite)||se.x<=nw.x||se.y<=nw.y||!Number.isInteger(z)||z<0||z>4)throw new Error('Invalid global map view');
  const count=2**z,tiles=[];
  const left=Math.floor(nw.x/TILE),right=Math.ceil(se.x/TILE)-1;
  const top=Math.max(0,Math.floor(nw.y/TILE)),bottom=Math.min(count-1,Math.ceil(se.y/TILE)-1);
  if((right-left+1)*Math.max(0,bottom-top+1)>256)throw new Error('Global map view is too large');
  for(let x=left;x<=right;x++)for(let y=top;y<=bottom;y++)tiles.push({x,y,z,wrappedX:((x%count)+count)%count});
  return tiles;
 }
 function overlap(a,b){
  const left=Math.max(a.left,b.left),right=Math.min(a.right,b.right),top=Math.max(a.top,b.top),bottom=Math.min(a.bottom,b.bottom);
  return right>left&&bottom>top?{left,right,top,bottom}:null;
 }
 class ImagePool{
  constructor(maximum){this.maximum=maximum;this.entries=new Map();this.queue=[];this.active=0;}
  get(url){
   if(this.entries.has(url)){const value=this.entries.get(url);this.entries.delete(url);this.entries.set(url,value);return value;}
   const promise=new Promise((resolve,reject)=>{
    // A fast scrub can supersede many views before their requests start.
    if(this.queue.length>=32)this.queue.shift().reject(new Error('Forecast view superseded'));
    this.queue.push({url,resolve,reject});this.drain();
   });
   this.entries.set(url,promise);
   promise.catch(()=>{if(this.entries.get(url)===promise)this.entries.delete(url);});
   while(this.entries.size>this.maximum)this.entries.delete(this.entries.keys().next().value);
   return promise;
  }
  drain(){
   while(this.active<4&&this.queue.length){
    const task=this.queue.shift();this.active++;
    const image=new Image();image.crossOrigin='anonymous';image.decoding='async';
    const finish=(error)=>{clearTimeout(timer);image.onload=image.onerror=null;this.active--;error?task.reject(error):task.resolve(image);this.drain();};
    const timer=setTimeout(()=>{image.src='';finish(new Error('Global rain tile timed out'));},20000);
    image.onload=()=>finish();image.onerror=()=>finish(new Error('Global rain tile unavailable'));image.src=task.url;
   }
  }
 }
 const tiles=new ImagePool(64),regions=new ImagePool(4),canvases=new Map();
 function touch(layer){
  canvases.delete(layer);canvases.set(layer,true);
  for(const candidate of canvases.keys()){
   if(canvases.size<=4)break;
   if(candidate===layer||candidate.opacity>0||candidate._pending||candidate.options.isActive?.())continue;
   canvases.delete(candidate);candidate._viewKey=null;
   if(candidate.canvas){candidate.canvas.width=1;candidate.canvas.height=1;}
  }
 }
 function viewOf(map){
  const size=map.getSize(),z=Math.max(0,Math.min(4,Math.floor(map.getZoom())));
  const factor=2**(z-map.getZoom()),bounds=map.getPixelBounds();
  const nw={x:bounds.min.x*factor,y:bounds.min.y*factor},se={x:bounds.max.x*factor,y:bounds.max.y*factor};
  const scale=Math.min(1.5,1024/Math.max(size.x,size.y));
  return {z,nw,se,width:Math.max(1,Math.round(size.x*scale)),height:Math.max(1,Math.round(size.y*scale)),bounds:map.getBounds(),key:[map.getZoom(),size.x,size.y,nw.x.toFixed(5),nw.y.toFixed(5)].join(':')};
 }
 async function mosaic(frame,view,current){
  const sx=view.width/(view.se.x-view.nw.x),sy=view.height/(view.se.y-view.nw.y);
  const plan=tilePlan(view.nw,view.se,view.z),template=frame.global_tiles.url_template;
  const images=await Promise.all(plan.map(tile=>tiles.get(template.replace('{z}',tile.z).replace('{x}',tile.wrappedX).replace('{y}',tile.y))));
  if(!current())throw new Error('Forecast view superseded');
  // Allocate the viewport only after its downloads complete, so superseded
  // pending views do not each retain a full screen-sized pixel buffer.
  const canvas=document.createElement('canvas');canvas.width=view.width;canvas.height=view.height;
  const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';
  plan.forEach((tile,i)=>ctx.drawImage(images[i],(tile.x*TILE-view.nw.x)*sx,(tile.y*TILE-view.nw.y)*sy,TILE*sx,TILE*sy));
  // Replace the global pixels inside the regional footprint. Transparent
  // regional rain means no rain there, so the global field must be cleared.
  const nw=project(frame.bounds[1][0],frame.bounds[0][1],view.z),se=project(frame.bounds[0][0],frame.bounds[1][1],view.z);
  const world=TILE*2**view.z,viewRect={left:view.nw.x,right:view.se.x,top:view.nw.y,bottom:view.se.y};
  const patches=[];
  for(let wrap=Math.floor((view.nw.x-se.x)/world);wrap<=Math.ceil((view.se.x-nw.x)/world);wrap++){
   const region={left:nw.x+wrap*world,right:se.x+wrap*world,top:nw.y,bottom:se.y};
   const rect=overlap(viewRect,region);if(rect)patches.push({rect,region});
  }
  if(patches.length){
   const image=await regions.get(frame.url);
   for(const {rect,region}of patches){
    const dx=(rect.left-view.nw.x)*sx,dy=(rect.top-view.nw.y)*sy,dw=(rect.right-rect.left)*sx,dh=(rect.bottom-rect.top)*sy;
    ctx.clearRect(dx,dy,dw,dh);
    ctx.drawImage(image,(rect.left-region.left)/(region.right-region.left)*image.width,(rect.top-region.top)/(region.bottom-region.top)*image.height,(rect.right-rect.left)/(region.right-region.left)*image.width,(rect.bottom-rect.top)/(region.bottom-region.top)*image.height,dx,dy,dw,dh);
   }
  }
  return canvas;
 }
 let Layer;
 function createLayer(frame,options){
  if(!root.L)throw new Error('Global rain requires the map library');
  if(!Layer){const L=root.L;Layer=L.Layer.extend({
   initialize(frame,options){this.frame=frame;this.options=options||{};this.opacity=0;this._generation=0;this._viewKey=null;this._pending=null;this._retryAt=0;},
   onAdd(map){this._map=map;this.canvas=L.DomUtil.create('canvas','global-rain-view');this.canvas.width=this.canvas.height=1;this.canvas.style.cssText='position:absolute;pointer-events:none;opacity:0;';map.getPane('overlayPane').appendChild(this.canvas);},
   onRemove(){this._generation++;canvases.delete(this);if(this.canvas)this.canvas.remove();this._map=null;},
   getEvents(){return {moveend:this._move,zoomend:this._move,viewreset:this._reset};},
   _move(){this._reset();if(this.opacity>0)this.ensureView().catch(()=>{});},
   _reset(){
    if(!this._map||!this._bounds||!this.canvas)return;
    const nw=this._map.latLngToLayerPoint(this._bounds.getNorthWest()),se=this._map.latLngToLayerPoint(this._bounds.getSouthEast());
    L.DomUtil.setPosition(this.canvas,nw);this.canvas.style.width=Math.max(1,se.x-nw.x)+'px';this.canvas.style.height=Math.max(1,se.y-nw.y)+'px';
   },
   setOpacity(opacity){this.opacity=opacity;if(this.canvas)this.canvas.style.opacity=String(opacity);if(opacity>0&&this._map)this.ensureView().catch(()=>{});return this;},
   getElement(){return this.canvas;},
   isReadyForView(){return !!(this._map&&this._viewKey===viewOf(this._map).key);},
   viewFailed(){return Date.now()<this._retryAt;},
   async ensureView(){
    if(!this._map)throw new Error('Forecast view was removed');
    const view=viewOf(this._map);
    if(this._viewKey===view.key){touch(this);return this.canvas;}
    if(this._pending&&this._pendingKey===view.key)return this._pending;
    if(Date.now()<this._retryAt)throw new Error('Forecast view is retrying');
    const generation=++this._generation;this._pendingKey=view.key;
    const task=mosaic(this.frame,view,()=>!!this._map&&generation===this._generation).then(image=>{
     if(!this._map||generation!==this._generation)throw new Error('Forecast view superseded');
     this.canvas.width=image.width;this.canvas.height=image.height;this.canvas.getContext('2d').drawImage(image,0,0);
     this._bounds=view.bounds;this._viewKey=view.key;this._reset();touch(this);this.fire('load');return this.canvas;
    }).catch(error=>{if(generation===this._generation){this._retryAt=Date.now()+2000;this.fire('error');}throw error;}).finally(()=>{if(generation===this._generation){this._pending=null;touch(this);}});
    this._pending=task;return task;
   }
  });}
  return new Layer(frame,options);
 }
 function stats(){return {tileCache:tiles.entries.size,regionalCache:regions.entries.size,canvases:canvases.size,activeRequests:tiles.active+regions.active};}
 return {createLayer,project,tilePlan,overlap,stats};
});
