'use strict';
const assert=require('node:assert/strict');
const {computeMotion,computeMidpointField,RainMotionRenderer}=require('../rain_motion.js');
function frame(width=256,height=256,blobs=[]){
  const data=new Uint8ClampedArray(width*height*4);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    let alpha=0;
    for(const b of blobs){const d=((x-b.x)/b.rx)**2+((y-b.y)/b.ry)**2;
      let v=d<1?Math.max(0,1-d)*.8:0;
      const texture=.78+.22*Math.sin((x-b.x)*.22)*Math.cos((y-b.y)*.18);v*=texture;
      alpha=Math.max(alpha,v);
    }
    const at=(y*width+x)*4;data[at]=75;data[at+1]=160;data[at+2]=240;data[at+3]=Math.round(alpha*255);
  }return {width,height,data};
}
function median(values){values.sort((a,b)=>a-b);return values[Math.floor(values.length/2)];}
function nearFlow(result,x,y,radius=3){const found=[];
 for(let gy=0;gy<result.gridHeight;gy++)for(let gx=0;gx<result.gridWidth;gx++){
  const px=(gx+.5)*result.width/result.gridWidth,py=(gy+.5)*result.height/result.gridHeight,at=(gy*result.gridWidth+gx)*3;
  if(Math.hypot(px-x,py-y)<radius&&result.forward[at+2]>.15)found.push([result.forward[at],result.forward[at+1]]);
 }
 return found.length?[median(found.map(v=>v[0])),median(found.map(v=>v[1]))]:null;
}
const opts={workingSize:128,gridSize:20,maxDisplacement:18};
{
 const a=frame(256,256,[{x:80,y:100,rx:35,ry:32}]);
 const b=frame(256,256,[{x:108,y:112,rx:35,ry:32}]);
 const result=computeMotion(a,b,opts);console.log('Translation',result.mode,result.matchedFraction,result.preparationMs,nearFlow(result,40,50,10));
 assert.equal(result.mode,'motion');
 const flow=nearFlow(result,40,50,10);assert(flow);assert(Math.abs(flow[0]-14)<2);assert(Math.abs(flow[1]-6)<2);
}
{
 const a=frame(256,256,[{x:65,y:65,rx:30,ry:26},{x:180,y:185,rx:26,ry:30}]);
 const b=frame(256,256,[{x:89,y:65,rx:30,ry:26},{x:162,y:173,rx:26,ry:30}]);
 const result=computeMotion(a,b,opts);console.log('Independent',result.mode,result.matchedFraction,result.preparationMs,nearFlow(result,32.5,32.5,10),nearFlow(result,90,92.5,10));
 assert.equal(result.mode,'motion');assert(nearFlow(result,32.5,32.5,10)[0]>8);assert(nearFlow(result,90,92.5,10)[0]<-5);
}
{
 const a=frame(256,256,[{x:80,y:100,rx:35,ry:32}]);const r=computeMotion(a,a,opts);assert.equal(r.mode,'stationary');assert(r.forward.every(v=>v===0));
 assert(r.backward.every(v=>v===0));assert(r.common.every(v=>v===0));assert.equal(r.matchedFraction,1);
 const clear=frame();const born=computeMotion(clear,a,opts);const died=computeMotion(a,clear,opts);assert.equal(born.mode,'blend');assert.equal(died.mode,'blend');
 for(const unmatched of [born,died]){
  assert.equal(unmatched.matchedFraction,0);
  assert(unmatched.forward.every(v=>v===0));assert(unmatched.backward.every(v=>v===0));assert(unmatched.common.every(v=>v===0));
 }
 assert.equal(computeMotion(clear,clear,opts).mode,'stationary');
 assert.throws(()=>computeMotion(clear,{width:10,height:10,data:new Uint8Array(1)},opts));
}
{
 // Most wet pixels are a new cell, but the smaller observed match must still
 // move. A scene-wide confidence cutoff previously discarded this motion.
 const a=frame(256,256,[{x:45,y:52,rx:20,ry:20}]);
 const b=frame(256,256,[{x:55,y:56,rx:20,ry:20},{x:172,y:165,rx:70,ry:75}]);
 const result=computeMotion(a,b,{workingSize:160,gridSize:24,maxDisplacement:18});
 assert.equal(result.mode,'motion');assert(result.matchedFraction>0&&result.matchedFraction<.18);
 const flow=nearFlow(result,45*160/256,52*160/256,10);
 assert(flow);assert(Math.abs(flow[0]-10*160/256)<2);assert(Math.abs(flow[1]-4*160/256)<2);
}
{
 // The full regional image can request a finer, bounded field.
 const a=frame(256,128,[{x:90,y:60,rx:35,ry:28}]);
 const b=frame(256,128,[{x:110,y:68,rx:35,ry:28}]);
 const result=computeMotion(a,b,{workingSize:160,gridSize:32,maxDisplacement:18});
 assert.equal(result.mode,'motion');assert.equal(result.width,160);assert.equal(result.height,80);
 assert.equal(result.gridWidth,32);assert.equal(result.gridHeight,16);
 assert(result.forward instanceof Float32Array);assert(result.backward instanceof Float32Array);assert(result.common instanceof Float32Array);
 assert.equal(result.forward.length,32*16*3);assert.equal(result.backward.length,32*16*3);assert.equal(result.common.length,32*16*3);
 assert.deepEqual(result.common,computeMidpointField(result));
 assert.notEqual(result.common.buffer,result.forward.buffer);assert.notEqual(result.common.buffer,result.backward.buffer);
 const capped=computeMotion(a,b,{workingSize:512,gridSize:128});
 assert.equal(capped.width,256);assert.equal(capped.height,128);
 assert.equal(capped.gridWidth,64);assert.equal(capped.gridHeight,32);
 assert.equal(capped.forward.length,64*32*3);assert.equal(capped.common.length,64*32*3);
 const defaults=computeMotion(a,b);
 assert.equal(defaults.width,256);assert.equal(defaults.gridWidth,64);assert.equal(defaults.maxDisplacement,24);
}
async function testPrefetch(){
 const a=frame(64,64,[{x:25,y:30,rx:12,ry:10}]),b=frame(64,64,[{x:29,y:32,rx:12,ry:10}]);
 const motion=computeMotion(a,b,opts),canvas={width:17,height:19,getContext:()=>null};
 const renderer=new RainMotionRenderer(canvas,{cacheSize:99});
 renderer.supported=true;renderer._state='ready';renderer._generation=7;
 const previous={key:'previous',motion};renderer._pair=previous;
 let calls=0,complete,uploads=0;
 renderer._compute=()=>{calls++;return new Promise(resolve=>{complete=resolve;});};
 renderer.gl={activeTexture(){},bindTexture(){},pixelStorei(){},texParameteri(){},texImage2D(){uploads++;},deleteTexture(){}};
 renderer.textures=[1,2,3];
 const prefetched=renderer.prefetchPair(a,b,'next');
 assert.equal(calls,1);assert.equal(renderer._pair,previous);assert.equal(renderer._generation,7);
 assert.equal(renderer.stats.state,'ready');assert.equal(renderer.stats.pending,false);
 assert.equal(canvas.width,17);assert.equal(canvas.height,19);assert.equal(uploads,0);
 // Advancing while prefetch is pending shares the worker computation.
 const prepared=renderer.preparePair(a,b,'next');assert.equal(calls,1);
 complete(motion);assert.equal(await prefetched,true);assert.equal(await prepared,true);
 assert.equal(renderer._pair.key,'next');assert.equal(uploads,3);assert.equal(renderer._inflight.size,0);
 const current=renderer._pair,generation=renderer._generation;
 renderer._compute=async()=>{calls++;return motion;};
 for(let n=0;n<6;n++)assert.equal(await renderer.prefetchPair(a,b,'ahead-'+n),true);
 assert.equal(renderer._pair,current);assert.equal(renderer._generation,generation);assert.equal(uploads,3);
 assert.equal(renderer._cache.size,4);assert.equal(await renderer.prefetchPair(a,b,'ahead-5'),true);assert.equal(calls,7);
 renderer._compute=async()=>{throw new Error('Expected worker failure');};
 assert.equal(await renderer.prefetchPair(a,b,'failed'),false);assert.equal(renderer._state,'ready');
 assert.equal(renderer._error,null);assert.equal(renderer._pair,current);
 assert.equal(await renderer.prefetchPair(a,{width:1,height:1,data:new Uint8Array(4)},'invalid'),false);
 renderer._compute=()=>new Promise(resolve=>{complete=resolve;});
 const disposed=renderer.prefetchPair(a,b,'late');renderer.dispose();complete(motion);
 assert.equal(await disposed,false);assert.equal(renderer._cache.size,0);assert.equal(renderer._inflight.size,0);

 // Background preparation must not supersede a queued visible demand.
 const priority=new RainMotionRenderer({getContext:()=>null},{cacheSize:4});
 priority.supported=true;priority._worker={postMessage(){},terminate(){}};
 const active=priority._motionFor(a,b,'active',false);
 const ahead=priority._motionFor(a,b,'ahead',false);
 assert.equal(priority._queuedJob.priority,false);
 assert.equal(priority._motionFor(a,b,'ahead',true),ahead);
 assert.equal(priority._queuedJob.priority,true);
 const blocked=priority._motionFor(a,b,'background',false);
 await assert.rejects(blocked,/superseded/);assert.equal(priority._queuedJob.key,'ahead');
 priority._finishJob({id:priority._activeJob.id,value:motion});await active;
 assert.equal(priority._activeJob.key,'ahead');
 priority._finishJob({id:priority._activeJob.id,value:motion});await ahead;
 assert.equal(priority._inflight.size,0);
 const activeAgain=priority._motionFor(a,b,'active-again',false);
 const superseded=priority._motionFor(a,b,'requeue',false);
 const rejected=assert.rejects(superseded,/superseded/);
 const other=priority._motionFor(a,b,'other',true),otherRejected=assert.rejects(other,/superseded/);
 // Reusing a superseded key in the same tick must enqueue fresh work.
 const requeued=priority._motionFor(a,b,'requeue',true);
 assert.notEqual(requeued,superseded);assert.equal(priority._queuedJob.key,'requeue');
 priority._finishJob({id:priority._activeJob.id,value:motion});await activeAgain;
 priority._finishJob({id:priority._activeJob.id,value:motion});await requeued;
 await rejected;await otherRejected;assert.equal(priority._inflight.size,0);priority.dispose();
}
testPrefetch().then(()=>console.log('All rain motion tests passed')).catch(error=>{console.error(error);process.exitCode=1;});
