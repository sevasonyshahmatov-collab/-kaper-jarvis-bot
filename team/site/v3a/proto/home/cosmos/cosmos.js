/* Космос: гофрированная лента на чистом WebGL2. Проход 1 — лента (цвет + радиус размытия), проход 2 — дымка, глубина резкости, зерно. Мышь не используется. */
(()=>{
'use strict';
/* ───────── данные: строка статуса и список матчей ───────── */
const H=window.HOME;
function lists(){
 const strip=document.getElementById('strip'),rows=document.getElementById('rows');
 if(!H){strip.hidden=true;return}
 const all=H.all().filter(m=>m.pr);
 const today=all.filter(m=>m.day==='сегодня');
 const list=(today.length?today:all).slice(0,8);
 const upd=()=>{
  const now=Date.now(),next=all.map(m=>Date.parse(m.t.replace(' ','T')+':00+03:00')).filter(t=>t>now).sort((a,b)=>a-b)[0];
  const n=today.length||all.length;
  let s=`Сегодня ${n} ${H.pl(n,'матч','матча','матчей')}`;
  if(next){const d=Math.max(0,Math.round((next-now)/6e4));s+=` · ближайший через ${String(Math.floor(d/60)).padStart(2,'0')}:${String(d%60).padStart(2,'0')}`}
  strip.textContent=s;
 };
 upd();setInterval(upd,3e4);
 rows.innerHTML=list.length?list.map(m=>{
  const k=m.ln&&m.bi>=0?[m.ln.p1,m.ln.x,m.ln.p2][m.bi]:null;
  const who=m.bi===1?'Ничья':'Победа: '+m.who;
  return `<li><span class="t">${m.hm}</span><span class="m">${H.esc(m.hn)} — ${H.esc(m.an)}<small>${m.lgn}</small></span><span class="o">${H.esc(who)}</span><span class="p">${H.pct(m.best)} %</span><span class="k">${k?H.f2(k):''}</span></li>`
 }).join(''):'<li class="empty">Матчи появятся после обновления данных.</li>';
}
try{lists()}catch(e){console.warn(e)}

/* ───────── WebGL ───────── */
const cv=document.getElementById('cv');
const gl=cv.getContext('webgl2',{antialias:false,alpha:false,powerPreference:'high-performance'});
if(!gl){document.documentElement.classList.add('nogl');return}
const mobile=matchMedia('(max-width:760px)').matches||/Mobi|Android/i.test(navigator.userAgent);
const still=matchMedia('(prefers-reduced-motion:reduce)').matches;
const DPR=Math.min(window.devicePixelRatio||1,mobile?1.25:1.5);

const VS1=`#version 300 es
precision highp float;
in vec2 a;
uniform float T,asp,dist,rot,K;
uniform vec2 off;
out vec3 vN,vV;out float vR,vD,vU;
vec3 C(float u){
 float x=mix(-4.8,4.8,u);
 float y=1.35*sin(u*3.0+T)+0.3*sin(u*7.0-2.0*T);
 float z=2.0*sin(u*2.2+T+1.0)+0.4*sin(u*5.0+T);
 return vec3(x,y,z);}
float ridge(float u){float r=sin(u*K*6.2831853);return clamp(r*1.7,-1.0,1.0);}
vec3 P(float u,float w,out float rg){
 vec3 c=C(u);
 vec3 tg=normalize(C(u+.002)-C(u-.002));
 vec3 b0=normalize(cross(tg,vec3(0,1,0))),n0=cross(b0,tg);
 float th=1.5*sin(u*2.5+T)+u*3.0;
 vec3 b=b0*cos(th)+n0*sin(th),n=-b0*sin(th)+n0*cos(th);
 float ang=w*6.2831853;
 rg=ridge(u);
 float tp=smoothstep(0.0,.06,u)*smoothstep(1.0,.94,u);
 float wd=0.95*(0.3+0.7*tp)*(1.0+0.18*sin(u*4.0-T));
 vec3 loc=(b*cos(ang)*wd+n*sin(ang)*0.34)*(1.0+0.12*rg);
 return c+loc;}
vec3 xf(vec3 p){
 float cr=cos(rot),sr=sin(rot);
 p=vec3(p.x*cr-p.y*sr,p.x*sr+p.y*cr,p.z);
 return p+vec3(off,0.0);}
void main(){
 float u=a.x,w=a.y,e=.0015,r0,r1,r2,r3,r4;
 vec3 p=P(u,w,r0);
 vec3 du=P(u+e,w,r1)-P(u-e,w,r2);
 vec3 dw=P(u,w+.004,r3)-P(u,w-.004,r4);
 vec3 n=normalize(cross(du,dw));
 float cr=cos(rot),sr=sin(rot);
 n=vec3(n.x*cr-n.y*sr,n.x*sr+n.y*cr,n.z);
 vec3 wp=xf(p);
 vec3 v=wp-vec3(0,0,dist);
 vN=n;vV=normalize(-v);vR=r0;vU=u;vD=-v.z;
 float f=3.1;
 gl_Position=vec4(v.x*f/asp,v.y*f,(-v.z-0.5)*1.002-1.0,-v.z);
}`;
const FS1=`#version 300 es
precision highp float;
in vec3 vN,vV;in float vR,vD,vU;
uniform float dim,focus,asp;uniform vec2 res1;
layout(location=0) out vec4 o0;layout(location=1) out vec4 o1;
void main(){
 vec3 n=normalize(vN),v=normalize(vV);
 if(dot(n,v)<0.0)n=-n;
 vec3 L=normalize(vec3(-0.55,0.75,0.65)),F=normalize(vec3(0.8,-0.3,0.4));
 float d=max(dot(n,L),0.0),d2=max(dot(n,F),0.0);
 vec3 H=normalize(L+v);float sp=pow(max(dot(n,H),0.0),48.0);
 vec3 r=reflect(-v,n);
 float env=smoothstep(-0.2,0.9,r.y)*0.5+smoothstep(0.5,1.0,dot(r,normalize(vec3(.4,.5,.8))))*0.6;
 float fr=pow(1.0-max(dot(n,v),0.0),3.0);
 float ao=0.62+0.38*(vR*0.5+0.5);
 vec3 col=vec3(.012,.014,.018)+pow(d,1.4)*vec3(.62,.66,.72)+d2*vec3(.04,.05,.08)+sp*vec3(1.0)*1.1+env*vec3(.14,.16,.20)+fr*vec3(.14,.2,.3);
 col*=ao*ao;
 float lm=smoothstep(.12,.62,gl_FragCoord.x/res1.x);
 float lw=res1.x/res1.y<1.1?mix(1.0,.28,smoothstep(.5,.78,gl_FragCoord.y/res1.y)):mix(.2,1.0,lm);
 float hz=smoothstep(7.0,17.0,vD);
 col=mix(col,vec3(.19,.21,.24),hz*.65);
 float tp=smoothstep(0.0,.1,vU)*smoothstep(1.0,.9,vU);
 col*=dim*lw*(0.5+0.5*tp);
 o0=vec4(col,1.0);
 o1=vec4(clamp(abs(vD-focus)*0.09,0.0,1.0),0,0,1);
}`;
const VS2=`#version 300 es
in vec2 p;out vec2 uv;void main(){uv=p*.5+.5;gl_Position=vec4(p,0,1);}`;
const FS2=`#version 300 es
precision highp float;
in vec2 uv;out vec4 o;
uniform sampler2D tc,tr;uniform vec2 res;uniform float T,gt,asp,dim,R;
float h(vec2 p){p=fract(p*vec2(.1031,.103));p+=dot(p,p.yx+33.33);return fract((p.x+p.y)*p.x);}
float nz(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
 return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+1.),f.x),f.y);}
float fbm(vec2 p){float s=0.,a=.5;for(int i=0;i<4;i++){s+=a*nz(p);p=p*2.03+7.1;a*=.5;}return s;}
void main(){
 vec2 q=(uv-.5)*vec2(asp,1.);
 /* дымка */
 float sm=fbm(q*1.5+vec2(T*.12,-T*.07))*.6+fbm(q*3.+vec2(-T*.09,T*.1)+3.)*.4;
 vec3 bg=vec3(.028,.03,.034)+vec3(.085,.092,.105)*smoothstep(.25,.85,sm)*(1.-smoothstep(.1,.95,length(q-vec2(.18*asp,.0))));
 /* глубина резкости: сборка по кругу, радиус зависит от соседних пикселей */
 float c0=texture(tr,uv).r;
 vec4 acc=vec4(0.);float ws=0.;
 const int N=28;
 for(int i=0;i<N;i++){
  float fi=float(i)+.5,rr=sqrt(fi/float(N)),an=fi*2.39996+h(uv*res)*0.9;
  vec2 d=vec2(cos(an),sin(an))*rr;
  vec2 s=uv+d*R/res*vec2(1.,1.);
  float cs=texture(tr,s).r;
  float w=smoothstep(rr-.25,rr+.05,max(cs,c0*.5));
  vec4 cc=texture(tc,s);
  acc+=vec4(cc.rgb,cc.a)*w;ws+=w;
 }
 acc/=max(ws,1e-3);
 float cov=acc.a;
 vec3 col=bg*(1.-cov)+acc.rgb*(1.-.0);
 /* лёгкий хлопок дымки поверх ленты у краёв */
 float vg=smoothstep(1.15,.25,length(q*vec2(.8,1.)));
 col*=.55+.45*vg;
 col*=1.-(1.-dim)*.5;
 /* зерно, 24 к/с */
 float g=h(uv*res+floor(gt*24.)*17.3)-.5;
 col+=g*.05*(1.-col*.6);
 col+=(h(uv*res*1.7+3.)-.5)/255.;
 o=vec4(max(col,0.),1.);
}`;
function sh(t,s){const x=gl.createShader(t);gl.shaderSource(x,s);gl.compileShader(x);if(!gl.getShaderParameter(x,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(x));return x}
function prog(v,f){const p=gl.createProgram();gl.attachShader(p,sh(gl.VERTEX_SHADER,v));gl.attachShader(p,sh(gl.FRAGMENT_SHADER,f));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p));return p}
let P1,P2;
try{P1=prog(VS1,FS1);P2=prog(VS2,FS2)}catch(e){console.warn(e);document.documentElement.classList.add('nogl');return}
const U=(p,n)=>gl.getUniformLocation(p,n);

/* сетка ленты */
const NU=mobile?340:760,NW=mobile?28:44;
const K=mobile?34:62;
const verts=new Float32Array((NU+1)*(NW+1)*2);
let k=0;for(let i=0;i<=NU;i++)for(let j=0;j<=NW;j++){verts[k++]=i/NU;verts[k++]=j/NW}
const idx=new Uint32Array(NU*NW*6);k=0;
for(let i=0;i<NU;i++)for(let j=0;j<NW;j++){const a=i*(NW+1)+j,b=a+NW+1;idx.set([a,b,a+1,a+1,b,b+1],k);k+=6}
const vao1=gl.createVertexArray();gl.bindVertexArray(vao1);
let b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,verts,gl.STATIC_DRAW);
let loc=gl.getAttribLocation(P1,'a');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
b=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,b);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,idx,gl.STATIC_DRAW);
const nIdx=idx.length;
const vao2=gl.createVertexArray();gl.bindVertexArray(vao2);
b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
loc=gl.getAttribLocation(P2,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);

/* буфер сцены */
let W=0,Hh=0,fbo,tc,tr,rb;
function tex(){const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA8,W,Hh,0,gl.RGBA,gl.UNSIGNED_BYTE,null);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);return t}
function resize(force){
 const cw=cv.clientWidth,ch=cv.clientHeight;
 const nw=Math.round(cw*DPR),nh=Math.round(ch*DPR);
 if(!force&&nw===W&&Math.abs(nh-Hh)<120*DPR)return;
 W=cv.width=nw;Hh=cv.height=nh;
 if(fbo){gl.deleteFramebuffer(fbo);gl.deleteTexture(tc);gl.deleteTexture(tr);gl.deleteRenderbuffer(rb)}
 tc=tex();tr=tex();rb=gl.createRenderbuffer();gl.bindRenderbuffer(gl.RENDERBUFFER,rb);gl.renderbufferStorage(gl.RENDERBUFFER,gl.DEPTH_COMPONENT16,W,Hh);
 fbo=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,fbo);
 gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,tc,0);
 gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT1,gl.TEXTURE_2D,tr,0);
 gl.framebufferRenderbuffer(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.RENDERBUFFER,rb);
 gl.drawBuffers([gl.COLOR_ATTACHMENT0,gl.COLOR_ATTACHMENT1]);
}
resize(true);

const u1={T:U(P1,'T'),asp:U(P1,'asp'),dist:U(P1,'dist'),rot:U(P1,'rot'),K:U(P1,'K'),off:U(P1,'off'),dim:U(P1,'dim'),focus:U(P1,'focus'),res1:U(P1,'res1')};
const u2={tc:U(P2,'tc'),tr:U(P2,'tr'),res:U(P2,'res'),T:U(P2,'T'),gt:U(P2,'gt'),asp:U(P2,'asp'),dim:U(P2,'dim'),R:U(P2,'R')};
const CYCLE=26;let sS=0;

function draw(sec){
 const asp=W/Hh,wide=asp>1.1;
 const ph=sec*Math.PI*2/CYCLE;
 const dist=wide?7.4:12.5;
 const dim=1-.85*sS;
 gl.bindFramebuffer(gl.FRAMEBUFFER,fbo);gl.viewport(0,0,W,Hh);
 gl.clearBufferfv(gl.COLOR,0,[0,0,0,0]);gl.clearBufferfv(gl.COLOR,1,[0,0,0,0]);gl.clearBufferfi(gl.DEPTH_STENCIL,0,1,0);
 gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LESS);gl.disable(gl.CULL_FACE);gl.depthMask(true);
 gl.useProgram(P1);gl.bindVertexArray(vao1);
 gl.uniform1f(u1.T,ph);gl.uniform1f(u1.asp,asp);gl.uniform1f(u1.dist,dist+sS*5);gl.uniform1f(u1.K,K);
 gl.uniform1f(u1.rot,wide?-.12:-1.0);
 gl.uniform2f(u1.off,wide?2.0:0.1,wide?-.5:-2.6+sS*1.2);gl.uniform2f(u1.res1,W,Hh);
 gl.uniform1f(u1.dim,dim);gl.uniform1f(u1.focus,wide?dist+0.2:dist+0.2);
 gl.drawElements(gl.TRIANGLES,nIdx,gl.UNSIGNED_INT,0);
 gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,W,Hh);gl.disable(gl.DEPTH_TEST);
 gl.useProgram(P2);gl.bindVertexArray(vao2);
 gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,tc);gl.uniform1i(u2.tc,0);
 gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,tr);gl.uniform1i(u2.tr,1);
 gl.uniform2f(u2.res,W,Hh);gl.uniform1f(u2.T,sec*.3);gl.uniform1f(u2.gt,sec);gl.uniform1f(u2.asp,asp);gl.uniform1f(u2.dim,dim);
 gl.uniform1f(u2.R,(mobile?9:13)*DPR);
 gl.drawArrays(gl.TRIANGLES,0,3);
}

/* прокрутка: лента уходит в глубину и темнеет */
let sT=0;const onScroll=()=>{sT=Math.min(1,Math.max(0,scrollY/(innerHeight*.9)))};
addEventListener('scroll',onScroll,{passive:true});onScroll();

let run=false,raf=0,last=0,clock=still?9:0;
function frame(ts){
 raf=0;if(!run)return;
 const dt=last?Math.min(.1,(ts-last)/1e3):0;last=ts;clock+=dt;
 sS+=(sT-sS)*Math.min(1,dt*5);
 if(sT>.98&&sS>.97){/* лента полностью ушла: кадр не считаем */}else draw(clock);
 raf=requestAnimationFrame(frame);
}
function start(){if(still||run)return;run=true;last=0;raf=requestAnimationFrame(frame)}
function stop(){run=false;if(raf)cancelAnimationFrame(raf);raf=0}
function vis(){document.hidden?stop():start()}
document.addEventListener('visibilitychange',vis);
addEventListener('resize',()=>{resize();draw(clock)});
if(still){sS=sT;draw(clock);addEventListener('scroll',()=>{sS=sT;draw(clock)},{passive:true})}else{start()}
window.__cosmos={draw:(s)=>{sS=sT;resize(true);draw(s)},stop,start};
})();
