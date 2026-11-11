/* SeaPoint rain-frame display interpolation. Source endpoints are unchanged;
 * matched image features move between them. This adds no forecast resolution. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.SeaPointRainMotion = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';

  // Share one source-derived displacement field at the temporal midpoint.
  // Self-contained for the Blob worker and for directional coverage checks.
  function computeMidpointField(motion) {
    const common = new Float32Array(motion.forward.length);
    const sums = new Float64Array(motion.gridWidth*motion.gridHeight*5);
    const radius=2, gxScale=motion.gridWidth/motion.width, gyScale=motion.gridHeight/motion.height;

    const interpolated=(field,x,y)=>{
      let wx=0,wy=0,confidence=0;
      const bx=Math.floor(x),by=Math.floor(y),fx=x-bx,fy=y-by;
      for(let yy=0;yy<2;yy++)for(let xx=0;xx<2;xx++){
        const gx=Math.max(0,Math.min(motion.gridWidth-1,bx+xx)),gy=Math.max(0,Math.min(motion.gridHeight-1,by+yy));
        const i=(gy*motion.gridWidth+gx)*3,weight=(xx?fx:1-fx)*(yy?fy:1-fy),cw=field[i+2]*weight;
        wx+=field[i]*cw;wy+=field[i+1]*cw;confidence+=cw;
      }
      return [confidence>1e-8?wx/confidence:0,confidence>1e-8?wy/confidence:0,confidence];
    };
    const smooth=(lo,hi,v)=>{v=Math.max(0,Math.min(1,(v-lo)/(hi-lo)));return v*v*(3-2*v);};
    for(const [field,reverse,sign] of [[motion.forward,motion.backward,1],[motion.backward,motion.forward,-1]]) {
      for(let gy=0;gy<motion.gridHeight;gy++)for(let gx=0;gx<motion.gridWidth;gx++) {
        const i=(gy*motion.gridWidth+gx)*3,dx=field[i],dy=field[i+1];
        let confidence=field[i+2];
        if(confidence<.08)continue;
        // Missing reverse coverage is absence of evidence, not zero velocity.
        // Confident contradictory endpoint matches still reject this path.
        const opposite=interpolated(reverse,gx+dx*gxScale,gy+dy*gyScale);
        confidence*=1-smooth(.5,2,Math.hypot(dx+opposite[0],dy+opposite[1]))*smooth(.02,.08,opposite[2]);
        if(confidence<.08)continue;
        // Both observed directions contribute at the same temporal midpoint.
        const mx=gx+.5*dx*gxScale,my=gy+.5*dy*gyScale;
        for(let y=Math.max(0,Math.floor(my)-radius);y<=Math.min(motion.gridHeight-1,Math.ceil(my)+radius);y++) {
          for(let x=Math.max(0,Math.floor(mx)-radius);x<=Math.min(motion.gridWidth-1,Math.ceil(mx)+radius);x++) {
            const distance=(x-mx)**2+(y-my)**2;if(distance>radius*radius)continue;
            const weight=Math.exp(-distance/2),wc=weight*confidence,j=(y*motion.gridWidth+x)*5;
            sums[j]+=wc*dx*sign;sums[j+1]+=wc*dy*sign;sums[j+2]+=wc;sums[j+3]+=weight;sums[j+4]+=wc*(dx*dx+dy*dy);
          }
        }
      }
    }
    // Conflicting neighbouring trajectories blend instead of defining a warp.
    const varianceLimit=.5*Math.min(motion.width/motion.gridWidth,motion.height/motion.gridHeight)**2;
    for(let i=0,j=0;i<common.length;i+=3,j+=5)if(sums[j+2]>1e-8) {
      const dx=sums[j]/sums[j+2],dy=sums[j+1]/sums[j+2];
      common[i]=dx;common[i+1]=dy;
      common[i+2]=sums[j+2]/sums[j+3]*Math.exp(-Math.max(0,sums[j+4]/sums[j+2]-dx*dx-dy*dy)/varianceLimit);
    }
    return common;
  }

  // Self-contained apart from the shared midpoint helper embedded in the worker.
  function computeMotion(a, b, options) {
    const started = Date.now();
    const opts = options || {};
    if (!a || !b || !Number.isInteger(a.width) || !Number.isInteger(a.height) || a.width < 1 || a.height < 1 || a.width !== b.width || a.height !== b.height ||
        !a.data || !b.data || a.data.length !== a.width * a.height * 4 ||
        b.data.length !== b.width * b.height * 4) throw new Error('Rain frame sizes differ');
    const fullWidth = a.width, fullHeight = a.height;
    const scale = Math.min(1, Math.max(48, Math.min(256, opts.workingSize || 256)) / Math.max(fullWidth, fullHeight));
    const width = Math.max(12, Math.round(fullWidth * scale));
    const height = Math.max(12, Math.round(fullHeight * scale));
    const gridSize = Math.max(4, Math.min(64, Math.round(opts.gridSize || 64)));
    const longest = Math.max(width, height);
    const gridWidth = Math.max(4, Math.round(gridSize * width / longest));
    const gridHeight = Math.max(4, Math.round(gridSize * height / longest));
    const limit = Math.max(2, Math.min(32, opts.maxDisplacement || 24));
    const count = gridWidth * gridHeight;
    const forward = new Float32Array(count * 3), backward = new Float32Array(count * 3);
    let difference = 0;
    for (let i = 0; i < a.data.length; i += 4) {
      const aa = a.data[i + 3] / 255, ba = b.data[i + 3] / 255;
      difference += Math.abs(aa - ba);
      for (let c = 0; c < 3; c++) difference += Math.abs(a.data[i + c] * aa - b.data[i + c] * ba) / 255;
    }
    const result = {forward, backward, common:new Float32Array(count * 3), gridWidth, gridHeight, width, height,
      maxDisplacement: limit, matchedFraction: 0, mode: 'blend', preparationMs: 0};
    if (difference / (fullWidth * fullHeight) < 0.000001) {
      result.mode = 'stationary'; result.matchedFraction = 1;
      result.preparationMs = Date.now() - started; return result;
    }
    function shrink(image) {
      const output = new Float32Array(width * height);
      for (let y = 0; y < height; y++) {
        const y0 = Math.floor(y * fullHeight / height), y1 = Math.max(y0 + 1, Math.floor((y + 1) * fullHeight / height));
        for (let x = 0; x < width; x++) {
          const x0 = Math.floor(x * fullWidth / width), x1 = Math.max(x0 + 1, Math.floor((x + 1) * fullWidth / width));
          let sum = 0, n = 0;
          for (let yy = y0; yy < y1; yy++) for (let xx = x0; xx < x1; xx++) {
            const i = (yy * fullWidth + xx) * 4, data = image.data;
            sum += (data[i + 3] / 255) * (.45 + (data[i] * .25 + data[i + 1] * .2 + data[i + 2] * .1) / 255); n++;
          }
          output[y * width + x] = sum / n;
        }
      }
      return {data: output, width, height};
    }
    function pyramid(image) {
      const levels = [image];
      while (levels.length < 3) {
        const previous = levels[levels.length - 1];
        const w = Math.floor(previous.width / 2), h = Math.floor(previous.height / 2);
        const data = new Float32Array(w * h);
        for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
          const at = y * 2 * previous.width + x * 2;
          data[y * w + x] = (previous.data[at] + previous.data[at + 1] +
            previous.data[at + previous.width] + previous.data[at + previous.width + 1]) / 4;
        }
        levels.push({data, width: w, height: h});
      }
      return levels;
    }
    const pa = pyramid(shrink(a)), pb = pyramid(shrink(b));
    function score(source, target, cx, cy, dx, dy, radius) {
      const sx = Math.round(cx), sy = Math.round(cy), tx = sx + dx, ty = sy + dy;
      if (sx - radius < 0 || sy - radius < 0 || sx + radius >= source.width || sy + radius >= source.height ||
          tx - radius < 0 || ty - radius < 0 || tx + radius >= target.width || ty + radius >= target.height) return null;
      let sa = 0, sb = 0, saa = 0, sbb = 0, sab = 0, n = 0;
      for (let y = -radius; y <= radius; y += 2) for (let x = -radius; x <= radius; x += 2) {
        const av = source.data[(sy + y) * source.width + sx + x];
        const bv = target.data[(ty + y) * target.width + tx + x];
        sa += av; sb += bv; saa += av * av; sbb += bv * bv; sab += av * bv; n++;
      }
      const va = saa - sa * sa / n, vb = sbb - sb * sb / n;
      if (sa < .08 || sb < .08 || va < .001 || vb < .001) return null;
      const correlation = Math.max(-1, Math.min(1, (sab - sa * sb / n) / Math.sqrt(va * vb)));
      // Normalized correlation tolerates genuine intensity growth, while a tiny
      // zero-displacement preference resolves ambiguous flat/straight edges.
      return {correlation, value: correlation - (dx * dx + dy * dy) * .000001};
    }
    function estimate(source, target) {
      const field = new Float32Array(count * 3);
      for (let gy = 0; gy < gridHeight; gy++) for (let gx = 0; gx < gridWidth; gx++) {
        const cx = (gx + .5) * width / gridWidth, cy = (gy + .5) * height / gridHeight;
        // Every candidate uses this same source patch. A dry/flat patch cannot
        // pass the final correlation check, so avoid searching it at all.
        const sx = Math.round(cx), sy = Math.round(cy), full = source[0];
        if (sx - 5 < 0 || sy - 5 < 0 || sx + 5 >= width || sy + 5 >= height) continue;
        let sum = 0, squares = 0, samples = 0;
        for (let y = -5; y <= 5; y += 2) for (let x = -5; x <= 5; x += 2) {
          const value = full.data[(sy + y) * width + sx + x];
          sum += value; squares += value * value; samples++;
        }
        if (sum < .08 || squares - sum * sum / samples < .001) continue;
        let dx = 0, dy = 0, best = null;
        for (let level = 2; level >= 0; level--) {
          const factor = Math.pow(2, level), image = source[level], other = target[level];
          const px = cx / factor, py = cy / factor;
          const search = level === 2 ? Math.ceil(limit / factor) : 3;
          const centerX = level === 2 ? 0 : dx * 2, centerY = level === 2 ? 0 : dy * 2;
          const radius = level === 2 ? 3 : 5;
          let candidate = null, foundX = 0, foundY = 0;
          for (let yy = centerY - search; yy <= centerY + search; yy++) for (let xx = centerX - search; xx <= centerX + search; xx++) {
            if (Math.abs(xx * factor) > limit || Math.abs(yy * factor) > limit) continue;
            const scored = score(image, other, px, py, xx, yy, radius);
            if (scored && (!candidate || scored.value > candidate.value)) {candidate = scored; foundX = xx; foundY = yy;}
          }
          if (candidate) {dx = foundX; dy = foundY; best = candidate;}
          else {dx = centerX; dy = centerY; best = null;}
        }
        if (!best || best.correlation < .78) continue;
        const zero = score(source[0], target[0], cx, cy, 0, 0, 5);
        if (zero && zero.correlation > .99998 && best.correlation - zero.correlation < .00001) {dx = 0; dy = 0;}
        const i = (gy * gridWidth + gx) * 3;
        field[i] = dx; field[i + 1] = dy; field[i + 2] = best.correlation;
      }
      return field;
    }
    const rawForward = estimate(pa, pb), rawBackward = estimate(pb, pa);
    function nearest(field, x, y, cells) {
      const gx = x * gridWidth / width - .5, gy = y * gridHeight / height - .5;
      let chosen = -1, distance = Infinity;
      const minX = Math.max(0, Math.floor(gx) - cells), maxX = Math.min(gridWidth - 1, Math.ceil(gx) + cells);
      const minY = Math.max(0, Math.floor(gy) - cells), maxY = Math.min(gridHeight - 1, Math.ceil(gy) + cells);
      for (let yy = minY; yy <= maxY; yy++) for (let xx = minX; xx <= maxX; xx++) {
        const at = (yy * gridWidth + xx) * 3;
        if (field[at + 2] < .78) continue;
        const d = (gx - xx) * (gx - xx) + (gy - yy) * (gy - yy);
        if (d < distance) {distance = d; chosen = at;}
      }
      return chosen < 0 ? null : {index: chosen, distance};
    }
    function verify(own, reverse, output) {
      for (let gy = 0; gy < gridHeight; gy++) for (let gx = 0; gx < gridWidth; gx++) {
        const i = (gy * gridWidth + gx) * 3;
        if (!own[i + 2]) continue;
        const cx = (gx + .5) * width / gridWidth, cy = (gy + .5) * height / gridHeight;
        const opposite = nearest(reverse, cx + own[i], cy + own[i + 1], 1);
        if (!opposite || opposite.distance > 3.5) continue;
        const ri = opposite.index;
        const error = Math.hypot(own[i] + reverse[ri], own[i + 1] + reverse[ri + 1]);
        if (error > 3) continue;
        output[i] = own[i]; output[i + 1] = own[i + 1];
        output[i + 2] = Math.min(own[i + 2], reverse[ri + 2]) * (1 - error / 6);
      }
    }
    verify(rawForward, rawBackward, forward); verify(rawBackward, rawForward, backward);
    function rejectOutliers(field) {
      const original = field.slice();
      for (let gy = 0; gy < gridHeight; gy++) for (let gx = 0; gx < gridWidth; gx++) {
        const i = (gy * gridWidth + gx) * 3;
        if (original[i + 2] < .15) continue;
        const neighbors = [];
        let similar = 0;
        for (let yy = Math.max(0, gy - 1); yy <= Math.min(gridHeight - 1, gy + 1); yy++) {
          for (let xx = Math.max(0, gx - 1); xx <= Math.min(gridWidth - 1, gx + 1); xx++) {
            if (xx === gx && yy === gy) continue;
            const at = (yy * gridWidth + xx) * 3;
            if (original[at + 2] < .15) continue;
            neighbors.push([original[at], original[at + 1]]);
            if (Math.hypot(original[i] - original[at], original[i + 1] - original[at + 1]) < 3) similar++;
          }
        }
        let reject = Math.hypot(original[i], original[i + 1]) > Math.max(4, limit * .35) && similar < 2;
        if (neighbors.length >= 4) {
          const xs = neighbors.map(v => v[0]).sort((a, b) => a - b);
          const ys = neighbors.map(v => v[1]).sort((a, b) => a - b);
          reject = reject || Math.hypot(original[i] - xs[Math.floor(xs.length / 2)],
            original[i + 1] - ys[Math.floor(ys.length / 2)]) > 4;
        }
        if (reject) {field[i] = 0; field[i + 1] = 0; field[i + 2] = 0;}
      }
    }
    rejectOutliers(forward); rejectOutliers(backward);
    function fill(field, image) {
      const original = field.slice();
      for (let gy = 0; gy < gridHeight; gy++) for (let gx = 0; gx < gridWidth; gx++) {
        const i = (gy * gridWidth + gx) * 3;
        if (original[i + 2] > .15) continue;
        const x = Math.min(width - 1, Math.floor((gx + .5) * width / gridWidth));
        const y = Math.min(height - 1, Math.floor((gy + .5) * height / gridHeight));
        if (image.data[y * width + x] < .02) continue;
        const candidate = nearest(original, x, y, 3);
        if (!candidate || candidate.distance > 8) continue;
        const at = candidate.index;
        // Only propagate a matched feature locally through the same wet area.
        field[i] = original[at]; field[i + 1] = original[at + 1];
        field[i + 2] = original[at + 2] * Math.max(.35, 1 - Math.sqrt(candidate.distance) / 5);
      }
    }
    fill(forward, pa[0]); fill(backward, pb[0]);
    function regularize(field) {
      const original = field.slice();
      const varianceLimit = .5 * Math.pow(Math.min(width / gridWidth, height / gridHeight), 2);
      for (let gy = 0; gy < gridHeight; gy++) for (let gx = 0; gx < gridWidth; gx++) {
        const i = (gy * gridWidth + gx) * 3;
        if (original[i + 2] < .15) continue;
        let weight = 0, dx = 0, dy = 0, squares = 0;
        for (let yy = Math.max(0, gy - 2); yy <= Math.min(gridHeight - 1, gy + 2); yy++) {
          for (let xx = Math.max(0, gx - 2); xx <= Math.min(gridWidth - 1, gx + 2); xx++) {
            const at = (yy * gridWidth + xx) * 3;
            if (original[at + 2] < .15) continue;
            const w = original[at + 2] * Math.exp(-((gx - xx) ** 2 + (gy - yy) ** 2) / 2);
            weight += w; dx += original[at] * w; dy += original[at + 1] * w;
            squares += (original[at] ** 2 + original[at + 1] ** 2) * w;
          }
        }
        dx /= weight; dy /= weight;
        field[i] = dx; field[i + 1] = dy;
        // Conflicting nearby matches cannot define a reliable deformation.
        // Keep coherent motion; smoothly blend uncertain growth/dissipation.
        field[i + 2] *= Math.exp(-Math.max(0, squares / weight - dx * dx - dy * dy) / varianceLimit);
      }
    }
    regularize(forward); regularize(backward);
    let wet = 0, matched = 0, hasMotion = false;
    for (let gy = 0; gy < gridHeight; gy++) for (let gx = 0; gx < gridWidth; gx++) {
      const i = (gy * gridWidth + gx) * 3;
      if (Math.max(forward[i + 2], backward[i + 2]) >= .15) hasMotion = true;
      const x = Math.min(width - 1, Math.floor((gx + .5) * width / gridWidth));
      const y = Math.min(height - 1, Math.floor((gy + .5) * height / gridHeight));
      if (Math.max(pa[0].data[y * width + x], pb[0].data[y * width + x]) > .02) {
        wet++; if (Math.max(forward[i + 2], backward[i + 2]) >= .15) matched++;
      }
    }
    result.matchedFraction = wet ? matched / wet : 0;
    // A small matched cell still moves even when most of the scene is growing
    // or dissipating. Confidence is applied locally by the renderer.
    result.mode = hasMotion ? 'motion' : 'blend';
    result.common = computeMidpointField(result);
    result.preparationMs = Date.now() - started;
    return result;
  }

  const vertexSource = 'attribute vec2 a_position;varying vec2 v_uv;void main(){gl_Position=vec4(a_position,0.,1.);v_uv=vec2((a_position.x+1.)*.5,(1.-a_position.y)*.5);}';
  const fragmentSource = `
    #ifdef GL_FRAGMENT_PRECISION_HIGH
    precision highp float;
    #else
    precision mediump float;
    #endif
    varying vec2 v_uv;
    uniform sampler2D u_a,u_b,u_common;
    uniform vec2 u_work,u_image;
    uniform float u_limit,u_t,u_mode;
    vec4 imageAt(sampler2D tex,vec2 uv){
      if(uv.x<0.||uv.x>1.||uv.y<0.||uv.y>1.)return vec4(0.);
      return texture2D(tex,uv);
    }
    vec3 flowAt(sampler2D tex,vec2 uv){
      vec4 v=texture2D(tex,clamp(uv,vec2(0.),vec2(1.)));
      vec2 movement=v.b>.001?(v.rg*255.-128.)/127./v.b:vec2(0.);
      // Packing error is largest at a confidence boundary; keep the inverse
      // solve inside the observed displacement range and fade that error out.
      movement=clamp(movement,vec2(-1.),vec2(1.))*smoothstep(.02,.08,v.b);
      return vec3(movement*u_limit/u_work,v.b);
    }
    vec4 premultiply(vec4 color){return vec4(color.rgb*color.a,color.a);}
    // Interpolate visible colour in premultiplied space. Straight RGBA
    // interpolation darkens rain where transparent texels have zeroed RGB.
    vec4 premultipliedAt(sampler2D tex,vec2 uv){
      vec2 at=uv*u_image-.5,cell=floor(at),fraction=fract(at),base=(cell+.5)/u_image;
      vec2 step=1./u_image;
      vec4 a=premultiply(imageAt(tex,base)),b=premultiply(imageAt(tex,base+vec2(step.x,0.)));
      vec4 c=premultiply(imageAt(tex,base+vec2(0.,step.y))),d=premultiply(imageAt(tex,base+step));
      return mix(mix(a,b,fraction.x),mix(c,d,fraction.x),fraction.y);
    }
    void main(){
      vec4 originalA=imageAt(u_a,v_uv),originalB=imageAt(u_b,v_uv);
      if(u_t<=0.){gl_FragColor=originalA;return;}
      if(u_t>=1.){gl_FragColor=originalB;return;}
      vec4 color=mix(premultiply(originalA),premultiply(originalB),u_t);
      if(u_mode>.5){
        // One inverse map keeps the two observed endpoint samples aligned.
        vec2 midpoint=v_uv;
        for(int i=0;i<8;i++){
          midpoint=mix(midpoint,v_uv-(u_t-.5)*flowAt(u_common,midpoint).xy,.5);
        }
        vec3 f=flowAt(u_common,midpoint);
        float confidence=smoothstep(.08,.25,f.z);
        // Suppress inverse solutions that do not reach this output pixel.
        confidence*=1.-smoothstep(.5,2.,length((midpoint+(u_t-.5)*f.xy-v_uv)*u_work));
        vec4 warped=mix(premultipliedAt(u_a,midpoint-.5*f.xy),premultipliedAt(u_b,midpoint+.5*f.xy),u_t);
        color=mix(color,warped,confidence);
      }
      gl_FragColor=color.a>.00001?vec4(color.rgb/color.a,color.a):vec4(0.);
    }`;

  function createRenderer(canvas, options) {
    return new RainMotionRenderer(canvas, options);
  }
  class RainMotionRenderer {
    constructor(canvas, options) {
      this.canvas = canvas; this.options = Object.assign({workingSize:256,gridSize:64,maxDisplacement:24,cacheSize:4}, options);
      this.supported = false; this._disposed = false; this._generation = 0; this._cache = new Map();
      this._inflight = new Map();
      this._worker = null; this._workerUrl = null; this._activeJob = null; this._queuedJob = null; this._jobId = 0;
      this._state = 'unsupported'; this._pair = null; this._pendingKey = null; this._pendingPromise = null;
      try {
        const gl = canvas.getContext('webgl', {alpha:true,premultipliedAlpha:false,antialias:false,preserveDrawingBuffer:true});
        if (!gl) return; this.gl = gl;
        const shader = (type, source) => {const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
          if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;};
        const vs = shader(gl.VERTEX_SHADER, vertexSource), fs = shader(gl.FRAGMENT_SHADER, fragmentSource);
        const program = gl.createProgram(); gl.attachShader(program,vs); gl.attachShader(program,fs); gl.linkProgram(program);
        gl.deleteShader(vs); gl.deleteShader(fs);
        if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
        this.program = program; this.buffer=gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,this.buffer);
        gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);
        this.position=gl.getAttribLocation(program,'a_position'); this.uniforms={};
        for(const name of ['a','b','common','work','image','limit','t','mode'])this.uniforms[name]=gl.getUniformLocation(program,'u_'+name);
        this.textures=Array.from({length:3},()=>gl.createTexture());
        canvas.addEventListener('webglcontextlost', this._onLost = event => {event.preventDefault();this.supported=false;this._state='context-lost';});
        this.supported=true; this._state='idle';
        if(typeof Worker==='function' && typeof Blob==='function' && typeof URL==='function') {
          const code='const computeMidpointField='+computeMidpointField.toString()+';const computeMotion='+computeMotion.toString()+';self.onmessage=function(event){const job=event.data;try{const value=computeMotion(job.a,job.b,job.options);self.postMessage({id:job.id,value:value},[value.forward.buffer,value.backward.buffer,value.common.buffer]);}catch(error){self.postMessage({id:job.id,error:String(error)});}};';
          this._workerUrl=URL.createObjectURL(new Blob([code],{type:'application/javascript'}));
          this._worker=new Worker(this._workerUrl);
          this._worker.onmessage=event=>this._finishJob(event.data);
          this._worker.onerror=()=>this._workerFailure();
        }
      } catch(error) {this.supported=false;this._state='unsupported';this._error=String(error);}
    }
    get stats() {
      return Object.freeze({state:this._state,cacheSize:this._cache.size,pending:!!this._pendingPromise,
        matchedFraction:this._pair?this._pair.motion.matchedFraction:0,confidence:this._pair?this._pair.motion.matchedFraction:0,
        mode:this._pair?this._pair.motion.mode:'blend',preparationMs:this._pair?this._pair.motion.preparationMs:0,
        worker:!!this._worker,width:this.canvas.width,height:this.canvas.height,key:this._pair?this._pair.key:null,error:this._error||null});
    }
    _finishJob(message) {
      const job=this._activeJob;if(!job||message.id!==job.id)return;
      this._activeJob=null; message.error?job.reject(new Error(message.error)):job.resolve(message.value);
      if(this._queuedJob){const next=this._queuedJob;this._queuedJob=null;this._sendJob(next);}
    }
    _sendJob(job) {
      this._activeJob=job;
      this._worker.postMessage({id:job.id,a:job.a,b:job.b,options:this.options},[job.a.data.buffer,job.b.data.buffer]);
    }
    _workerFailure() {
      if(this._worker)this._worker.terminate();this._worker=null;this._error='Motion worker unavailable';
      if(this._activeJob){this._activeJob.reject(new Error(this._error));this._activeJob=null;}
      if(this._queuedJob){this._queuedJob.reject(new Error(this._error));this._queuedJob=null;}
    }
    _compute(a,b,key,priority) {
      if(!this._worker)return Promise.reject(new Error('Motion worker unavailable'));
      return new Promise((resolve,reject)=>{
        if(this._activeJob&&this._queuedJob&&this._queuedJob.priority&&!priority){reject(new Error('Motion pair superseded'));return;}
        const job={id:++this._jobId,key,priority,a:{width:a.width,height:a.height,data:a.data.slice()},b:{width:b.width,height:b.height,data:b.data.slice()},resolve,reject};
        if(this._activeJob){
          if(this._queuedJob){this._inflight.delete(this._queuedJob.key);this._queuedJob.reject(new Error('Motion pair superseded'));}
          this._queuedJob=job;
        }
        else this._sendJob(job);
      });
    }
    _validPair(a,b) {
      return !!(a&&b&&Number.isInteger(a.width)&&Number.isInteger(a.height)&&a.width>0&&a.height>0&&a.width===b.width&&a.height===b.height&&a.data&&b.data&&a.data.length===a.width*a.height*4&&b.data.length===b.width*b.height*4);
    }
    _motionFor(a,b,key,priority) {
      const cached=this._cache.get(key);
      if(cached){this._cache.delete(key);this._cache.set(key,cached);return Promise.resolve(cached);}
      if(this._inflight.has(key)){
        if(priority&&this._queuedJob&&this._queuedJob.key===key)this._queuedJob.priority=true;
        return this._inflight.get(key);
      }
      if(!priority&&this._activeJob&&this._queuedJob&&this._queuedJob.priority)return Promise.reject(new Error('Motion pair superseded'));
      const promise=this._compute(a,b,key,priority).then(motion=>{
        if(this._disposed)throw new Error('Motion renderer disposed');
        this._cache.set(key,motion);
        const maximum=Math.max(1,Math.min(4,this.options.cacheSize||4));
        while(this._cache.size>maximum)this._cache.delete(this._cache.keys().next().value);
        return motion;
      }).finally(()=>{if(this._inflight.get(key)===promise)this._inflight.delete(key);});
      this._inflight.set(key,promise);return promise;
    }
    async prefetchPair(a,b,key) {
      if(!this.supported||this._disposed||!this._validPair(a,b))return false;
      try{await this._motionFor(a,b,String(key),false);return this.supported&&!this._disposed;}
      catch(error){return false;}
    }
    async preparePair(a,b,key) {
      if(!this.supported||this._disposed)return false;
      if(!this._validPair(a,b))return false;
      key=String(key);
      if(this._pendingKey===key&&this._pendingPromise)return this._pendingPromise;
      if(this._pair&&this._pair.key===key&&!this._pendingPromise)return true;
      const generation=++this._generation;this._pendingKey=key;this._state='preparing';
      const promise=(async()=>{
        let motion;
        try{motion=await this._motionFor(a,b,key,true);}catch(error){
          if(generation!==this._generation||this._disposed)return false;
          this._error=String(error);this._state='unavailable';return false;
        }
        if(generation!==this._generation||this._disposed||!this.supported)return false;
        const gl=this.gl;this.canvas.width=a.width;this.canvas.height=a.height;
        const upload=(index,w,h,data)=>{
          gl.activeTexture(gl.TEXTURE0+index);gl.bindTexture(gl.TEXTURE_2D,this.textures[index]);
          gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);
          gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
          gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,w,h,0,gl.RGBA,gl.UNSIGNED_BYTE,data);
        };
        upload(0,a.width,a.height,a.data);upload(1,b.width,b.height,b.data);
        const pack=field=>{
          const bytes=new Uint8Array(motion.gridWidth*motion.gridHeight*4);
          for(let i=0,j=0;i<field.length;i+=3,j+=4){
            const confidence=Math.max(0,Math.min(1,field[i+2]));
            bytes[j]=Math.round(128+Math.max(-1,Math.min(1,field[i]/motion.maxDisplacement))*confidence*127);
            bytes[j+1]=Math.round(128+Math.max(-1,Math.min(1,field[i+1]/motion.maxDisplacement))*confidence*127);
            bytes[j+2]=Math.round(confidence*255);bytes[j+3]=255;
          }return bytes;
        };

        upload(2,motion.gridWidth,motion.gridHeight,pack(motion.common));
        this._pair={key,motion};this._state='ready';this._error=null;return true;
      })();
      this._pendingPromise=promise;
      try{return await promise;}finally{if(generation===this._generation){this._pendingPromise=null;this._pendingKey=null;}}
    }
    render(t) {
      if(!this.supported||this._disposed||!this._pair)return false;
      t=Math.max(0,Math.min(1,Number(t)));if(!Number.isFinite(t))return false;
      const gl=this.gl,motion=this._pair.motion;
      gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.useProgram(this.program);gl.disable(gl.BLEND);
      gl.bindBuffer(gl.ARRAY_BUFFER,this.buffer);gl.enableVertexAttribArray(this.position);gl.vertexAttribPointer(this.position,2,gl.FLOAT,false,0,0);
      ['a','b','common'].forEach((name,index)=>{gl.activeTexture(gl.TEXTURE0+index);gl.bindTexture(gl.TEXTURE_2D,this.textures[index]);gl.uniform1i(this.uniforms[name],index);});
      gl.uniform2f(this.uniforms.work,motion.width,motion.height);gl.uniform2f(this.uniforms.image,this.canvas.width,this.canvas.height);gl.uniform1f(this.uniforms.limit,motion.maxDisplacement);
      gl.uniform1f(this.uniforms.t,t);gl.uniform1f(this.uniforms.mode,motion.mode==='motion'?1:0);
      gl.drawArrays(gl.TRIANGLE_STRIP,0,4);return gl.getError()===gl.NO_ERROR;
    }
    dispose() {
      if(this._disposed)return;this._disposed=true;this._generation++;this._state='disposed';this.supported=false;
      this._workerFailure();if(this._workerUrl)URL.revokeObjectURL(this._workerUrl);
      if(this._onLost)this.canvas.removeEventListener('webglcontextlost',this._onLost);
      if(this.gl){for(const texture of this.textures||[])this.gl.deleteTexture(texture);if(this.buffer)this.gl.deleteBuffer(this.buffer);if(this.program)this.gl.deleteProgram(this.program);}
      this._cache.clear();this._inflight.clear();this._pair=null;
    }
  }
  return {computeMotion,computeMidpointField,createRenderer,RainMotionRenderer};
});
