/* JARVIS v3a — «ледяная крошка над ареной»: живой фон первого экрана темы arena (31.10).
   Свой код на чистом WebGL2, без зависимостей. Тысячи частиц ледяной пыли дрейфуют с параллаксом по глубине,
   редкие мягкие пятна боке, две «ленты» из плотных частиц текут по дугам разметки льда и медленно извиваются.
   Цвет лент — лига матча в карточке «Прогноз дня» (#board.khl / .nhl): КХЛ синий + красный, НХЛ серебро + белый,
   смена плавная. Мышь — только лёгкий параллакс и отталкивание частиц, без свечения у курсора.
   При прокрутке частицы редеют и тают вместе с «включением света» (JV.lit). Нет WebGL2 — остаётся прежний фон.
   Пауза: скрытая вкладка, первый экран уехал и свет включён. prefers-reduced-motion — один статичный кадр. */
(()=>{
'use strict';
const doc=document.documentElement;
if(doc.dataset.theme!=='arena'||!document.querySelector('.hero'))return;
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const cv=document.createElement('canvas');
cv.id='snow';cv.setAttribute('aria-hidden','true');
cv.style.cssText='position:fixed;inset:0;width:100vw;height:100lvh;z-index:-1;pointer-events:none;opacity:0;transition:opacity 1.2s ease';
const gl=cv.getContext('webgl2',{alpha:true,antialias:false,premultipliedAlpha:true,powerPreference:'high-performance'});
if(!gl)return;
const small=Math.min(innerWidth,innerHeight)<620;
const DPR=Math.min(devicePixelRatio||1,1.5);
const N_DUST=small?1100:4200,N_RIB=small?1100:4200,N_BOKEH=small?14:36;   // на ленту

const VS=`#version 300 es
precision highp float;
in vec4 aS; in float aT;
uniform vec2 uRes; uniform float uTime,uDpr,uLit,uScroll; uniform vec2 uPar,uMouse; uniform vec3 uC0,uC1;
out float vA; out vec3 vC; out float vSoft;
const float TAU=6.2831853;
vec2 repel(vec2 p,float k){vec2 d=p-uMouse;float l=length(d);float r=150.;if(l<r&&l>.01)p+=d/l*pow(1.-l/r,2.)*44.*k;return p;}
void main(){
 float s1=aS.x,s2=aS.y,s3=aS.z,s4=aS.w,t=uTime,W=uRes.x,H=uRes.y;
 vec2 p;float a,sz;vec3 c;vSoft=0.;
 if(aT<.5){                                  // ледяная пыль
  float d=.25+.75*s3;
  vec2 v=vec2(4.+sin(s4*TAU)*7.,9.+20.*d);
  p=vec2(s1*W,s2*H)+v*t+vec2(sin(t*.3+s1*20.)*14.*d,0.);
  p.y-=uScroll*.35*d;
  vec2 m=vec2(60.);p=mod(p+m,uRes+2.*m)-m;
  p+=uPar*34.*d;
  p=repel(p,d);
  sz=mix(1.2,3.8,pow(s4,3.))*mix(.6,1.35,d);
  a=(.3+.7*s4)*mix(.3,1.,d)*(.72+.28*sin(t*(1.+s2*3.)+s1*40.));
  a*=mix(1.,.6,clamp(p.y/H,0.,1.));          // в лучах прожекторов сверху ярче
  c=mix(vec3(.72,.86,1.),vec3(1.),s2);
 }else if(aT<1.5||aT>2.5){                   // ленты по дугам разметки льда
  float k=aT>2.5?1.:0.;
  float u=fract(s1+t*(.010+.007*s4));
  float R=.95*max(W,H),port=step(W,H);
  float yT=mix(.34,.19,port)*H,yB=mix(.74,.27,port)*H;           // вершина верхней дуги, низ нижней
  vec2 C=k<.5?vec2(.3*W,yT+R):vec2(mix(.52,.7,port)*W,yB-R);
  float sp=asin(clamp(W*.78/R,0.,1.))+.16;
  float th=k<.5?mix(-1.5708-sp,-1.5708+sp,u):mix(1.5708+sp,1.5708-sp,u);
  float wig=min(W,H);
  R+=sin(u*9.+t*.42+k*2.)*.045*wig+sin(u*3.7-t*.23+k)*.06*wig;
  th+=sin(t*.17+k*3.)*.05;
  vec2 n=vec2(cos(th),sin(th));
  float env=sin(3.14159*u);
  float w=(.028*wig+.02*wig*sin(u*12.+t*.55+k))*(.35+.65*env);
  p=C+n*(R+(s2+s3-1.)*w*2.)+vec2(-n.y,n.x)*(s4-.5)*6.;
  p+=uPar*26.;
  p=repel(p,.45);
  sz=mix(1.1,2.8,pow(s3,2.));
  a=(.5+.5*s2)*smoothstep(0.,.1,u)*smoothstep(1.,.9,u)*(.5+.5*env);
  c=k<.5?uC0:uC1; if(s4>.88)c=mix(c,vec3(1.),.65);
 }else{                                      // мягкое боке
  float d=.2+.5*s3;
  p=vec2(s1*W,s2*H)+vec2(sin(t*.05+s4*9.)*40.,cos(t*.04+s1*7.)*30.);
  p.y-=uScroll*.15;p+=uPar*14.*d;
  sz=mix(36.,110.,s4)*(small()?.7:1.);
  a=mix(.035,.09,s3);c=vec3(.70,.84,1.);vSoft=1.;
 }
 a*=step(uLit*1.05,fract(s1*7.31+s3*3.17)); // с «включением света» часть частиц пропадает
 vA=a;vC=c;
 gl_PointSize=sz*uDpr;
 gl_Position=vec4(p/uRes*2.-1.,0.,1.)*vec4(1.,-1.,1.,1.);
}`.replace('small()?.7:1.',small?'.7':'1.');
const FS=`#version 300 es
precision mediump float;
in float vA; in vec3 vC; in float vSoft; out vec4 o;
void main(){vec2 q=gl_PointCoord*2.-1.;float r=dot(q,q);if(r>1.)discard;
 float a=vSoft>.5?exp(-r*2.6)*(1.-r):smoothstep(1.,.15,r);
 a*=vA;o=vec4(vC*a,a);}`;
function sh(t,s){const x=gl.createShader(t);gl.shaderSource(x,s);gl.compileShader(x);if(!gl.getShaderParameter(x,gl.COMPILE_STATUS)){console.warn('particles:',gl.getShaderInfoLog(x));return null}return x}
const vs=sh(gl.VERTEX_SHADER,VS),fs=sh(gl.FRAGMENT_SHADER,FS);if(!vs||!fs)return;
const pr=gl.createProgram();gl.attachShader(pr,vs);gl.attachShader(pr,fs);gl.linkProgram(pr);
if(!gl.getProgramParameter(pr,gl.LINK_STATUS)){console.warn('particles:',gl.getProgramInfoLog(pr));return}
gl.useProgram(pr);
// частицы: [s1,s2,s3,s4, тип] — тип 0 пыль, 1 и 3 — ленты, 2 — боке; всё движение считает шейдер
const N=N_DUST+N_RIB*2+N_BOKEH,buf=new Float32Array(N*5);
let seed=7;const rnd=()=>(seed=(seed*16807)%2147483647)/2147483647;
for(let i=0;i<N;i++){const o=i*5;for(let j=0;j<4;j++)buf[o+j]=rnd();
 buf[o+4]=i<N_BOKEH?2:i<N_BOKEH+N_DUST?0:i<N_BOKEH+N_DUST+N_RIB?1:3}
const vb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vb);gl.bufferData(gl.ARRAY_BUFFER,buf,gl.STATIC_DRAW);
const la=gl.getAttribLocation(pr,'aS'),lt=gl.getAttribLocation(pr,'aT');
gl.enableVertexAttribArray(la);gl.vertexAttribPointer(la,4,gl.FLOAT,false,20,0);
gl.enableVertexAttribArray(lt);gl.vertexAttribPointer(lt,1,gl.FLOAT,false,20,16);
const U={};['uRes','uTime','uDpr','uLit','uScroll','uPar','uMouse','uC0','uC1'].forEach(n=>U[n]=gl.getUniformLocation(pr,n));
gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE);gl.disable(gl.DEPTH_TEST);

// цвета лент по лиге матча в карточке «Прогноз дня»
const LGC={khl:[[.36,.62,1.],[1.,.36,.42]],nhl:[[.80,.85,.92],[1.,1.,1.]]};
const board=document.getElementById('board');
const lgNow=()=>board&&board.classList.contains('nhl')?'nhl':'khl';
let col=JSON.parse(JSON.stringify(LGC[lgNow()]));

let W=0,H=0;
function size(){W=innerWidth;H=innerHeight;cv.width=Math.round(W*DPR);cv.height=Math.round(H*DPR);gl.viewport(0,0,cv.width,cv.height)}
size();addEventListener('resize',()=>{size();if(RM)frame(performance.now())});
// мышь: плавно, только параллакс и отталкивание
let mx=-9999,my=-9999,px=0,py=0,tpx=0,tpy=0,smx=-9999,smy=-9999;
addEventListener('pointermove',e=>{if(e.pointerType==='touch')return;mx=e.clientX;my=e.clientY;tpx=(mx/W-.5)*-2;tpy=(my/H-.5)*-2},{passive:true});
document.addEventListener('pointerleave',()=>{mx=my=-9999;tpx=tpy=0});

let heroVis=true,raf=0,t0=performance.now(),last=t0;
const lit=()=>Math.max(0,Math.min(1,window.JV&&typeof JV.lit==='number'?JV.lit:0));
function frame(now){
 const dt=Math.min(.05,(now-last)/1000);last=now;
 const L=lit();cv.style.opacity=String(Math.max(0,1-L*1.15));
 const tc=LGC[lgNow()],kk=1-Math.exp(-dt*2.2);
 for(let r=0;r<2;r++)for(let j=0;j<3;j++)col[r][j]+=(tc[r][j]-col[r][j])*(RM?1:kk);
 px+=(tpx-px)*Math.min(1,dt*3);py+=(tpy-py)*Math.min(1,dt*3);
 if(mx<-999){smx=-9999;smy=-9999}else{smx=smx<-999?mx:smx+(mx-smx)*Math.min(1,dt*8);smy=smy<-999?my:smy+(my-smy)*Math.min(1,dt*8)}
 gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);
 gl.uniform2f(U.uRes,W,H);gl.uniform1f(U.uTime,RM?40:(now-t0)/1000+40);gl.uniform1f(U.uDpr,DPR);gl.uniform1f(U.uLit,L);
 gl.uniform1f(U.uScroll,scrollY);gl.uniform2f(U.uPar,px,py);gl.uniform2f(U.uMouse,smx,smy);
 gl.uniform3fv(U.uC0,col[0]);gl.uniform3fv(U.uC1,col[1]);
 gl.drawArrays(gl.POINTS,0,N);
 fps(now);
}
// приблизительный замер к/с (для проверки): window.__snowFps
let fc=0,ft=0;function fps(now){fc++;if(!ft)ft=now;if(now-ft>=1000){window.__snowFps=Math.round(fc*1000/(now-ft));fc=0;ft=now}}
const want=()=>!document.hidden&&(heroVis||lit()<.98);
function loop(now){raf=0;frame(now);if(want())raf=requestAnimationFrame(loop)}
function kick(){if(!RM&&!raf&&want()){last=performance.now();raf=requestAnimationFrame(loop)}}
document.addEventListener('visibilitychange',kick);
addEventListener('scroll',()=>{if(RM)frame(performance.now());else kick()},{passive:true});
if('IntersectionObserver' in window)new IntersectionObserver(es=>{heroVis=es[0].isIntersecting;kick()}).observe(document.querySelector('.hero'));
if(board)new MutationObserver(()=>{if(RM)frame(performance.now());else kick()}).observe(board,{attributes:true,attributeFilter:['class']});
cv.addEventListener('webglcontextlost',e=>{e.preventDefault();cancelAnimationFrame(raf);raf=0;cv.remove()});
const arena=document.getElementById('arena')||document.querySelector('.arena-bg');
(arena&&arena.parentNode?arena.after(cv):document.body.prepend(cv));
requestAnimationFrame(()=>{cv.style.opacity='1';if(RM)frame(performance.now());else kick()});
})();
