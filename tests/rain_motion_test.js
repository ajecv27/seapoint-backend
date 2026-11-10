'use strict';
const assert=require('node:assert/strict');
const {computeMotion}=require('../rain_motion.js');
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
 const clear=frame();const born=computeMotion(clear,a,opts);const died=computeMotion(a,clear,opts);assert.equal(born.mode,'nearest');assert.equal(died.mode,'nearest');
 assert.equal(computeMotion(clear,clear,opts).mode,'stationary');
 assert.throws(()=>computeMotion(clear,{width:10,height:10,data:new Uint8Array(1)},opts));
}
console.log('All rain motion tests passed');
