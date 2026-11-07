/* Фон для шапки ?hh=8 «Арена» (макет, 07.11): библиотека shaders (MIT, Shader Effects Inc.), только бесплатные компоненты.
   Работает на WebGPU. Нет navigator.gpu / адаптера / инициализация упала / prefers-reduced-motion → остаётся CSS-фолбэк (hero8.css),
   который всегда лежит под холстом: холст проявляется только после onReady. Курсор не используется (ни один слой не читает мышь).
   JVSh.mount(host, canvas, 'ice'|'pitch') → Promise<boolean>; JVSh.preset(kind, w, h) — описание слоёв (его же проверяет тест tools/test_hero8.mjs). */
(()=>{
'use strict';
const SCR=document.currentScript,BASE=SCR&&SCR.src?new URL('.',SCR.src).href:'';
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;

/* Иней: форма — скруглённый прямоугольник ровно по холсту. Поле SDF квадратное и равно scale·высота холста,
   поэтому scale ≥ ширина/высота, а половины сторон — в долях поля (radius = полуширина, height = полувысота). */
const frostGeom=(w,h)=>{
 const asp=Math.max(.2,w/Math.max(1,h)),scale=Math.max(asp,1)*1.02;
 return {scale,shape:JSON.stringify({type:'roundedRectSDF',radius:+(asp/(2*scale)*1.004).toFixed(4),height:+(1/(2*scale)*1.004).toFixed(4),rounding:0.02})};
};

function preset(kind,w,h){
 const ice=kind==='ice',L=[];
 L.push({type:'SolidColor',id:'bg',props:{color:ice?'#05080c':'#040806'}});
 /* лучи прожекторов сверху: центры чуть выше кадра, очень медленно */
 const ray=ice?'#a9cdee':'#e4f3d8';
 L.push({type:'Godrays',id:'rays1',props:{center:{x:.26,y:-.28},density:.3,intensity:.7,spotty:.45,speed:.07,rayColor:ray,backgroundColor:'transparent',opacity:.36,blendMode:'screen'}});
 L.push({type:'Godrays',id:'rays2',props:{center:{x:.74,y:-.3},density:.26,intensity:.65,spotty:.4,speed:.05,rayColor:ray,backgroundColor:'transparent',opacity:.3,blendMode:'screen'}});
 if(ice){
  /* лёгкая дымка по всему кадру */
  L.push({type:'Fog',id:'fog',props:{colorA:'#2b3d4f',colorB:'#0d1620',seed:3,speed:.18,turbulence:.45,detail:8,blending:.5,mouseInfluence:0,opacity:.34,blendMode:'screen'}});
  /* иней у краёв: маска — радиальный градиент (белый центр), перевёрнутая по яркости: центр чистый */
  L.push({type:'RadialGradient',id:'clear',props:{colorA:'#ffffff',colorB:'#000000',center:{x:.5,y:.5},radius:.9,aspect:1.4,visible:false}});
  const g=frostGeom(w||1440,h||900);
  L.push({type:'Frost',id:'frost',props:{shapeType:'roundedRectSDF',shape:g.shape,scale:g.scale,center:{x:.5,y:.5},iceColor:'#9fc8ea',density:.5,absorption:.35,scatter:.5,
   frostAmount:.85,frostDepth:.1,frostScale:1.1,frostRoughness:3,sparkle:.35,gloss:.25,fresnel:.05,ambient:.25,edgeSoftness:.05,speed:.12,
   maskSource:'clear',maskType:'luminanceInverted',opacity:.78,blendMode:'screen'}});
 }else{
  /* низкий туман над газоном: дымка видна только в нижней половине (маска — вертикальный градиент по яркости) */
  L.push({type:'LinearGradient',id:'low',props:{colorA:'#000000',colorB:'#ffffff',start:{x:.5,y:.42},end:{x:.5,y:1},visible:false}});
  L.push({type:'Fog',id:'fog',props:{colorA:'#2f5a3c',colorB:'#0c1a12',seed:11,speed:.2,turbulence:.5,detail:9,blending:.45,mouseInfluence:0,opacity:.55,blendMode:'screen',maskSource:'low',maskType:'luminance'}});
 }
 L.push({type:'FilmGrain',id:'grain',props:{strength:ice?.32:.3,bias:2.2,animated:false}});
 return {components:L};
}

/* ── CSS-фолбэк: зерно и иней рисуем на canvas один раз (детерминированно), дальше это просто фоновые картинки ── */
const rng=a=>()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296};
function noiseTile(){
 const c=document.createElement('canvas');c.width=c.height=128;const x=c.getContext('2d');if(!x)return '';
 const im=x.createImageData(128,128),r=rng(7);
 for(let i=0;i<im.data.length;i+=4){const v=r()*255|0;im.data[i]=im.data[i+1]=im.data[i+2]=v;im.data[i+3]=70+(r()*120|0)}
 x.putImageData(im,0,0);return c.toDataURL('image/png');
}
function frostTex(w,h){
 const k=Math.min(1,1100/Math.max(1,w));w=Math.max(240,w*k|0);h=Math.max(240,h*k|0);   // текстура до ~1100 px по ширине, растягивается CSS-ом
 const c=document.createElement('canvas');c.width=w;c.height=h;const x=c.getContext('2d');if(!x)return null;
 const r=rng(42);x.lineCap='round';
 const U=Math.min(w,h)/800;                                   // единица масштаба: на узком экране кристаллы мельче
 const branch=(px,py,a,len,d)=>{
  if(len<4*U||d>3)return;
  const n=Math.max(2,Math.round(len/(10*U))),sx=Math.cos(a)*len/n,sy=Math.sin(a)*len/n;let cx=px,cy=py;
  for(let i=0;i<n;i++){
   const nx=cx+sx*(.85+r()*.3),ny=cy+sy*(.85+r()*.3);
   x.strokeStyle=`rgba(${205+(r()*40|0)},${228+(r()*22|0)},255,${(.3-d*.06)*(1-i/n*.7)})`;x.lineWidth=Math.max(.7,(1.7-d*.4)*U);
   x.beginPath();x.moveTo(cx,cy);x.lineTo(nx,ny);x.stroke();
   if(i>0&&i%2===0&&r()<.7){const side=r()<.5?-1:1;branch(nx,ny,a+side*(.8+r()*.35),len*(.34+r()*.2),d+1);branch(nx,ny,a-side*(.8+r()*.35),len*(.3+r()*.18),d+1)}
   cx=nx;cy=ny}
 };
 const N=Math.round(70*Math.min(2,Math.max(.7,(w+h)/1800)));
 for(let i=0;i<N;i++){
  const e=r()*4|0;let u=r();u=u<.5?.5*Math.pow(2*u,1.9):1-.5*Math.pow(2*(1-u),1.9);   // семена жмутся к углам
  let px,py,a;                                                  // точка на периметре и направление внутрь
  if(e===0){px=u*w;py=0;a=Math.PI/2}else if(e===1){px=w;py=u*h;a=Math.PI}else if(e===2){px=u*w;py=h;a=-Math.PI/2}else{px=0;py=u*h;a=0}
  a+=(r()-.5)*.8;branch(px,py,a,(70+r()*120)*U,0)}
 return c;
}
function paint(host,kind){
 try{
  host.style.setProperty('--sh-noise',`url(${noiseTile()})`);
  if(kind==='ice'){
   let prev='';const draw=()=>{const b=host.getBoundingClientRect(),c=frostTex(b.width,b.height);if(!c)return;c.toBlob(bl=>{if(!bl)return;const u=URL.createObjectURL(bl);host.style.setProperty('--sh-frost',`url(${u})`);if(prev)URL.revokeObjectURL(prev);prev=u},'image/png')};
   draw();let rt=0,lw=host.clientWidth;
   addEventListener('resize',()=>{if(host.classList.contains('gl-on')||host.clientWidth===lw)return;clearTimeout(rt);rt=setTimeout(()=>{lw=host.clientWidth;draw()},250)});
  }
 }catch(e){console.warn("hero8 paint",e)}
}

async function mount(host,cv,kind){
 paint(host,kind);
 if(RM||!('gpu' in navigator))return false;
 const off=()=>{try{host.classList.remove('gl-on');host.classList.add('gl-off')}catch(e){}};
 try{
  const mod=await import(BASE+'vendor/shaders.min.js');
  const sup=await mod.getWebGPUSupport();if(!sup.supported){off();return false}
  const r=host.getBoundingClientRect();
  cv.style.width='100%';cv.style.height='100%';         // библиотека не должна «заморозить» размер в пикселях
  let inst=null,dead=false;
  const fail=()=>{dead=true;off();try{inst&&inst.destroy()}catch(e){}};
  inst=await mod.createShader(cv,preset(kind,r.width,r.height),{disableTelemetry:true,onReady:()=>{if(!dead)host.classList.add('gl-on')},onError:code=>{if(['unsupported','no-adapter','no-device','init-failed','device-lost','out-of-memory','gpu-error','render-failed','limit-exceeded','unrecoverable','rebuild_failed'].includes(code)&&inst&&inst.getFailureReason())fail()}});
  if(dead||inst.getFailureReason()){fail();return false}
  document.addEventListener('visibilitychange',()=>{if(dead)return;document.hidden?inst.pause():inst.resume()});
  if(kind==='ice'){
   /* иней медленно нарастает ~45 с и остаётся; пересчёт формы при изменении размера */
   const t0=performance.now(),DUR=45000;
   const iv=setInterval(()=>{if(dead||document.hidden)return;const k=Math.min(1,(performance.now()-t0)/DUR);inst.update('frost',{frostDepth:.1+.32*(1-Math.pow(1-k,2))});if(k>=1)clearInterval(iv)},250);
   let rt=0;
   if('ResizeObserver' in window)new ResizeObserver(()=>{clearTimeout(rt);rt=setTimeout(()=>{if(dead)return;const b=host.getBoundingClientRect();inst.update('frost',frostGeom(b.width,b.height))},150)}).observe(host);
  }
  return true;
 }catch(e){off();return false}
}
window.JVSh={mount,preset,frostGeom,frostTex};
})();
