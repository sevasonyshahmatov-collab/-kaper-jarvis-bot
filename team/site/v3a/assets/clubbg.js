/* JARVIS v3a — живой фон шапки клуба (страница команды, 31.10): медленный «жидкий» mesh-градиент из фирменных цветов
   клуба + лёгкое зерно. Свой шейдер на WebGL (по мотивам mesh-градиентов Paper Shaders / React Bits — идея, не код):
   4 цветовых пятна медленно плавают, поле слегка «течёт» (domain warp), цвета смешиваются по обратному расстоянию.
   Цвета — из палитры team.js (--c1..--c3, проверены на контраст текста ≥ 4,5:1) и приглушённый акцент клуба,
   который при необходимости затемняется до того же контраста. Эмблема-водяной знак и текст остаются поверх.
   Пауза вне экрана и на скрытой вкладке, ~30 к/с, рендер в пониженном разрешении (телефон — ещё ниже);
   prefers-reduced-motion — статичный кадр; нет WebGL — остаётся прежний CSS-градиент. Без реакции на курсор. */
(()=>{
'use strict';
const hero=document.querySelector('.tmhero');if(!hero)return;
const cs=getComputedStyle(document.body),v=n=>cs.getPropertyValue(n).trim();
const C1=v('--c1'),C2=v('--c2'),C3=v('--c3'),ACC=v('--cacc'),TXT=v('--con')||'#ffffff';
if(!C1||!C3)return;
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const rgb=h=>{h=h.replace('#','');if(h.length===3)h=h.replace(/(.)/g,'$1$1');const n=parseInt(h,16);return [n>>16&255,n>>8&255,n&255]};
const mix=(a,b,t)=>a.map((x,i)=>x+(b[i]-x)*t);
const lum=c=>{const l=c.map(x=>{x/=255;return x<=.03928?x/12.92:((x+.055)/1.055)**2.4});return .2126*l[0]+.7152*l[1]+.0722*l[2]};
const cr=(a,b)=>{const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)};
const T=rgb(TXT),dark=lum(T)<.3,need=c=>cr(T,c)>=4.5&&cr(mix(T,c,.25),c)>=4.5;
// четвёртое пятно — акцент клуба, приглушённый вторым цветом; подгоняем, пока текст поверх читается
let c4=mix(rgb(ACC||C3),rgb(C2),.62);
for(let k=0;k<14&&!need(c4);k++)c4=mix(c4,dark?[255,255,255]:[0,0,0],.12);
const COLS=[rgb(C1),rgb(C2),rgb(C3),c4].map(c=>c.map(x=>x/255));

const cv=document.createElement('canvas');cv.className='tmbg';cv.setAttribute('aria-hidden','true');
const gl=cv.getContext('webgl',{alpha:false,antialias:false,premultipliedAlpha:false,preserveDrawingBuffer:false});
if(!gl)return;
const VS='attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}';
const FS=`precision mediump float;
uniform vec2 uRes;uniform float uT;uniform vec3 uC[4];
float hash(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}
void main(){
 vec2 uv=gl_FragCoord.xy/uRes;float asp=uRes.x/uRes.y;vec2 q=vec2(uv.x*asp,uv.y);
 float t=uT*.1;
 q+=.09*vec2(sin(q.y*2.7+t*1.3),cos(q.x*2.2-t*1.1));      // поле медленно течёт
 q+=.04*vec2(sin(q.y*5.1-t*.9),cos(q.x*4.3+t*.7));
 vec2 P[4];
 P[0]=vec2(.18*asp,.82)+vec2(sin(t*.9),cos(t*.7))*.18;
 P[1]=vec2(.80*asp,.25)+vec2(cos(t*.6+1.3),sin(t*.8+.4))*.20;
 P[2]=vec2(.95*asp,.90)+vec2(sin(t*.5+2.1),cos(t*.65+1.7))*.16;
 P[3]=vec2(.45*asp,.35)+vec2(cos(t*.75+.8),sin(t*.55+2.6))*.22;
 vec3 col=vec3(0.);float ws=0.;
 for(int i=0;i<4;i++){float d=distance(q,P[i]);float w=1./(pow(d,2.2)+.035);col+=uC[i]*w;ws+=w;}
 col/=ws;
 col+=(hash(gl_FragCoord.xy+fract(uT*7.)*91.)-.5)*.035;   // зерно
 gl_FragColor=vec4(col,1.);
}`;
function sh(t,s){const x=gl.createShader(t);gl.shaderSource(x,s);gl.compileShader(x);return gl.getShaderParameter(x,gl.COMPILE_STATUS)?x:(console.warn('clubbg:',gl.getShaderInfoLog(x)),null)}
const vs=sh(gl.VERTEX_SHADER,VS),fs=sh(gl.FRAGMENT_SHADER,FS);if(!vs||!fs)return;
const pr=gl.createProgram();gl.attachShader(pr,vs);gl.attachShader(pr,fs);gl.linkProgram(pr);if(!gl.getProgramParameter(pr,gl.LINK_STATUS))return;
gl.useProgram(pr);
const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
const lp=gl.getAttribLocation(pr,'p');gl.enableVertexAttribArray(lp);gl.vertexAttribPointer(lp,2,gl.FLOAT,false,0,0);
const uRes=gl.getUniformLocation(pr,'uRes'),uT=gl.getUniformLocation(pr,'uT');
gl.uniform3fv(gl.getUniformLocation(pr,'uC'),new Float32Array(COLS.flat()));

const SCALE=Math.min(innerWidth,innerHeight)<620?.45:.6;
function size(){const r=hero.getBoundingClientRect();cv.width=Math.max(2,Math.round(r.width*SCALE));cv.height=Math.max(2,Math.round(r.height*SCALE));gl.viewport(0,0,cv.width,cv.height);gl.uniform2f(uRes,cv.width,cv.height)}
const t0=performance.now();let raf=0,vis=true,lastDraw=0;
function draw(now){gl.uniform1f(uT,RM?12:(now-t0)/1000+12);gl.drawArrays(gl.TRIANGLES,0,3)}
function loop(now){raf=0;if(now-lastDraw>=31){lastDraw=now;draw(now)}if(vis&&!document.hidden)raf=requestAnimationFrame(loop)}
const kick=()=>{if(RM||raf||!vis||document.hidden)return;raf=requestAnimationFrame(loop)};
hero.prepend(cv);
size();draw(performance.now());hero.classList.add('has-bg');
if('ResizeObserver' in window)new ResizeObserver(()=>{size();draw(performance.now())}).observe(hero);
if('IntersectionObserver' in window)new IntersectionObserver(es=>{vis=es[0].isIntersecting;kick()}).observe(hero);
document.addEventListener('visibilitychange',kick);
cv.addEventListener('webglcontextlost',e=>{e.preventDefault();cancelAnimationFrame(raf);cv.remove();hero.classList.remove('has-bg')});
kick();
})();
