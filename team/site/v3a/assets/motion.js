/* JARVIS v3a — движение плашек и активных кнопок (17.11). Подключает assets/nav.js на всех страницах; стили — в nav.css («17.11 — motion.js»).
   Приёмы взяты из галереи DesignBookmark Motion (https://designbookmark.com/motion) и переложены под сайт:
   • «Parallax ticket» → плитки клубов (.clb) и карточки тройки лидеров (.pod): карточка наклоняется к курсору, слои (эмблема, номер, фото)
     смещаются каждый на свою глубину, по поверхности идёт блик за курсором; нажатие чуть вдавливает карточку.
   • «Tab pill» → подложка активной кнопки: у неё две пружины, по одной на край. Край по ходу движения жёсткий, второй мягкий —
     подложка тянется к новой кнопке и подтягивает «хвост». В шапке и переключателях лиг она ещё и идёт за курсором.
   Всё на transform/width одного элемента, один requestAnimationFrame, который останавливается, когда пружины успокоились.
   prefers-reduced-motion: наклона нет, подложка встаёт на место сразу. Нет скрипта — работает прежний вид (стили без .has-pill). */
(()=>{
'use strict';
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
const fine=matchMedia('(hover:hover) and (pointer:fine)').matches;
const S=(x,k=400,c=30)=>({x,v:0,t:x,k,c});
const step=(s,dt)=>{const a=-s.k*(s.x-s.t)-s.c*s.v;s.v+=a*dt;s.x+=s.v*dt};
const rest=(s,e=.01)=>Math.abs(s.x-s.t)<e&&Math.abs(s.v)<e*4;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const comps=new Set();let raf=0,last=0;
function loop(now){const dt=Math.min((now-last)/1000,1/30);last=now;
 comps.forEach(c=>{for(let k=0;k<4;k++)c.frame(dt/4);c.render();if(c.idle()){comps.delete(c);if(c.done)c.done()}});
 raf=comps.size?requestAnimationFrame(loop):0}
const wake=c=>{comps.add(c);if(!raf){last=performance.now();raf=requestAnimationFrame(loop)}};

/* ── подложка активной кнопки ── */
function pill(box,o){
 if(box.__pill)return;box.__pill=1;
 const p=document.createElement(box.tagName==='UL'?'li':'span');p.className='mpill';p.setAttribute('aria-hidden','true');box.prepend(p);box.classList.add('has-pill');
 const A=S(0),B=S(0);let cur=null,y=0;
 const items=()=>[...box.querySelectorAll(o.items)].filter(e=>e.offsetWidth);
 const geo=el=>{const r=el.getBoundingClientRect(),b=box.getBoundingClientRect();
  return{l:r.left-b.left+box.scrollLeft-box.clientLeft,w:r.width,t:r.top-b.top+box.scrollTop-box.clientTop,h:r.height}};
 const c={frame(dt){step(A,dt);step(B,dt)},
  render(){p.style.transform=`translate(${A.x.toFixed(2)}px,${y.toFixed(2)}px)`;p.style.width=Math.max(0,B.x-A.x).toFixed(2)+'px'},
  idle:()=>rest(A,.05)&&rest(B,.05)};
 function go(el,snap){
  const all=items();all.forEach(e=>e.classList.toggle('pill-on',e===el));
  if(!el){p.style.opacity='0';cur=null;return}
  const g=geo(el),dir=g.l>=A.t?1:-1,was=cur;cur=el;
  A.t=g.l;B.t=g.l+g.w;y=g.t;p.style.height=g.h.toFixed(2)+'px';p.style.opacity='1';
  if(dir>0){B.k=620;B.c=40;A.k=170;A.c=19}else{A.k=620;A.c=40;B.k=170;B.c=19}
  if(snap||reduce||!was){A.x=A.t;B.x=B.t;A.v=B.v=0}
  c.render();wake(c)}
 const sync=snap=>go(items().find(o.active)||null,snap);
 sync(true);
 let t=0;const later=()=>{clearTimeout(t);t=setTimeout(()=>sync(false),0)};
 new MutationObserver(later).observe(box,{subtree:true,childList:true,attributes:true,attributeFilter:['aria-selected','aria-pressed','aria-current','hidden']});
 if('ResizeObserver' in window)new ResizeObserver(()=>{if(cur&&!box.matches(':hover'))sync(true)}).observe(box);
 if(document.fonts&&document.fonts.ready)document.fonts.ready.then(()=>sync(true));
 /* кнопки могут «въезжать» при появлении блока (data-rv) — после переходов и чуть позже встаём на место заново */
 const settle=()=>{if(!box.matches(':hover'))sync(true)};
 box.addEventListener('transitionend',e=>{if(e.target!==p&&e.propertyName==='transform')settle()});box.addEventListener('animationend',settle);
 [300,900,2000,4000].forEach(ms=>setTimeout(settle,ms));
 if(o.hover&&fine){
  box.addEventListener('pointerover',e=>{const it=items().find(i=>i===e.target||i.contains(e.target)||(i.parentElement!==box&&i.parentElement.contains(e.target)));if(it&&it!==cur)go(it)});
  box.addEventListener('pointerleave',()=>sync(false));
  box.addEventListener('focusin',e=>{const it=items().find(i=>i===e.target);if(it)go(it)});
  box.addEventListener('focusout',()=>{if(!box.matches(':hover'))later()})}
}
const cur=e=>e.hasAttribute('aria-current');
const PILLS=[
 ['.gnav',{items:':scope>a,:scope>.gdd>a',active:cur,hover:true}],
 ['.lghero .chips',{items:':scope>li>a',active:cur,hover:true}],
 ['.pl-lgsw',{items:':scope>a',active:cur,hover:true}],
 ['.lgsw',{items:':scope>.tab',active:e=>e.getAttribute('aria-selected')==='true'}],
 ['.pl-tabs',{items:':scope>button',active:e=>e.getAttribute('aria-pressed')==='true'}]];
const scan=()=>PILLS.forEach(([sel,o])=>document.querySelectorAll(sel).forEach(b=>{if(!b.__pill&&b.querySelector(o.items))pill(b,o)}));

/* ── наклон плашки за курсором ── */
const LAYERS=[['.wm',1,.05],['.wms',1,.05],['.no',.55,0],['.cut',-.6,.03]];
function tilt(el){
 if(el.__tilt)return el.__tilt;
 const big=el.classList.contains('pod'),MAX=big?6:9,DEPTH=big?16:12;
 const RX=S(0,220,18),RY=S(0,220,18),G=S(0,300,26),L=S(1,300,18),H=S(0,260,22);
 let hover=false,nx=0,ny=0,gx=50,gy=30;
 const glare={style:{setProperty(){}}}; /* блик при наведении убран по просьбе: «засветов нигде не должно быть» */
 const layers=()=>LAYERS.map(([s,d,z])=>[el.querySelector(':scope>'+s),d,z]).filter(l=>l[0]);
 let ls=layers();
 const c={
  frame(dt){RX.t=hover?-ny*MAX:0;RY.t=hover?nx*MAX:0;G.t=hover?1:0;H.t=hover?1:0;[RX,RY,G,L,H].forEach(s=>step(s,dt))},
  render(){
   el.style.transform=`perspective(900px) rotateX(${RX.x.toFixed(3)}deg) rotateY(${RY.x.toFixed(3)}deg) translateY(${(-4*H.x).toFixed(2)}px) scale(${L.x.toFixed(4)})`;
   const ox=RY.x/MAX,oy=-RX.x/MAX;
   ls.forEach(([n,d,z])=>{n.style.transform=`translate(${(ox*DEPTH*d).toFixed(2)}px,${(oy*DEPTH*d).toFixed(2)}px) scale(${(1+z*H.x).toFixed(4)})`});
   glare.style.setProperty('--g',clamp(G.x,0,1).toFixed(3));glare.style.setProperty('--gx',gx.toFixed(1)+'%');glare.style.setProperty('--gy',gy.toFixed(1)+'%')},
  idle:()=>!hover&&[RX,RY,G,H].every(s=>rest(s,.004))&&rest(L,.0005),
  done(){el.classList.remove('tilting');el.style.transform='';ls.forEach(l=>{l[0].style.transform=''})}};
 const on=e=>{const r=el.getBoundingClientRect();nx=clamp((e.clientX-r.left)/r.width*2-1,-1,1);ny=clamp((e.clientY-r.top)/r.height*2-1,-1,1);
  gx=(nx+1)*50;gy=(ny+1)*50;if(!hover){hover=true;ls=layers();el.classList.add('tilting')}wake(c)};
 el.addEventListener('pointermove',on);
 el.addEventListener('pointerleave',()=>{hover=false;L.t=1;wake(c)});
 el.addEventListener('pointerdown',()=>{L.t=.97;wake(c)});
 el.addEventListener('pointerup',()=>{L.t=1;wake(c)});
 return el.__tilt={on}}
if(fine&&!reduce)document.addEventListener('pointerover',e=>{const el=e.target&&e.target.closest&&e.target.closest('.clb,.pod');if(el&&!el.__tilt)tilt(el).on(e)},{passive:true});

/* ── магнитная кнопка («Magnetic button») — «Получать прогнозы» ──
   В радиусе притяжения кнопка сдвигается на долю пути к курсору, а подпись — ещё чуть дальше (ощущение глубины); вне радиуса обе
   пружинят на место. Радиус и сила меньше, чем в образце: кнопка стоит в плотной шапке и не должна убегать от соседних. */
const MAGS=new Set();
function magnet(el){
 if(el.__mag)return;el.__mag=1;el.classList.add('magn');MAGS.add(el);
 const R=80,bx=S(0,170,13),by=S(0,170,13),lx=S(0,220,15),ly=S(0,220,15),sc=S(1,400,18);let near=false,down=false;
 const c={frame(dt){[bx,by,lx,ly,sc].forEach(s=>step(s,dt))},
  render(){el.style.transform=`translate(${bx.x.toFixed(2)}px,${by.x.toFixed(2)}px) scale(${sc.x.toFixed(4)})`;
   for(const k of el.children)k.style.transform=`translate(${lx.x.toFixed(2)}px,${ly.x.toFixed(2)}px)`},
  idle:()=>!near&&!down&&[bx,by,lx,ly].every(s=>rest(s,.02))&&rest(sc,.0005),
  done(){el.style.transform='';for(const k of el.children)k.style.transform=''}};
 el.__magMove=(x,y)=>{if(!el.offsetWidth)return;const r=el.getBoundingClientRect(),cx=r.left+r.width/2-bx.x,cy=r.top+r.height/2-by.x,dx=x-cx,dy=y-cy;
  const d=Math.hypot(Math.max(Math.abs(dx)-r.width/2,0),Math.max(Math.abs(dy)-r.height/2,0)),pull=d<R?1-d/R:0;
  if(!pull&&!near)return;near=pull>0;
  bx.t=clamp(dx*.16,-9,9)*pull;by.t=clamp(dy*.3,-6,6)*pull;lx.t=clamp(dx*.07,-4,4)*pull;ly.t=clamp(dy*.14,-3,3)*pull;
  if(!down)sc.t=1+.04*pull;wake(c)};
 el.__magOff=()=>{if(!near)return;near=false;bx.t=by.t=lx.t=ly.t=0;if(!down)sc.t=1;wake(c)};
 el.addEventListener('pointerdown',()=>{down=true;sc.t=.95;wake(c)});
 const up=()=>{if(!down)return;down=false;sc.t=near?1.04:1;sc.v=3;wake(c)};
 el.addEventListener('pointerup',up);el.addEventListener('pointerleave',up)}
if(fine&&!reduce){
 addEventListener('pointermove',e=>{if(e.pointerType==='touch')return;MAGS.forEach(el=>el.__magMove(e.clientX,e.clientY))},{passive:true});
 document.documentElement.addEventListener('pointerleave',()=>MAGS.forEach(el=>el.__magOff()))}
const scanMag=()=>{if(fine&&!reduce)document.querySelectorAll('a.btn-tg').forEach(magnet)};

/* ── «Ночная арена» (?bg=n): контраст. Блок с непрозрачным светлым фоном получает класс .n-light (внутри — тёмный текст),
   с тёмным — .n-dark (светлый текст); переменные цвета для них задаёт nav.css. Размечаем по фактическому цвету, поэтому работает на любой странице. */
const NIGHT=document.documentElement.dataset.bg==='n';
function tone(){
 if(!NIGHT)return;
 const P=c=>{const m=/rgba?\(([^)]+)\)/.exec(c);if(!m)return null;const a=m[1].split(/[, /]+/).map(Number);return a.length>3&&a[3]<.9?null:a};
 const L=a=>{const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(a[0])+.7152*f(a[1])+.0722*f(a[2])};
 document.querySelectorAll('main *,.nxs *,.mpanel,.gdd-m').forEach(el=>{
  if(el.classList.contains('mpill')||el.classList.contains('n-clear')||el.closest('.clb,.pod,svg'))return;
  const cs=getComputedStyle(el);let c=P(cs.backgroundColor);
  if(!c&&cs.backgroundImage.startsWith('linear-gradient')){const m=/rgba?\([^)]+\)/.exec(cs.backgroundImage);c=m&&P(m[0])}
  const H=h=>{h=h.trim();if(/^#[0-9a-f]{6}$/i.test(h))return[1,3,5].map(i=>parseInt(h.substr(i,2),16));const r=P(h);return r};
  const ik=H(cs.getPropertyValue('--ink'));
  if(c&&ik&&Math.abs(c[0]-ik[0])+Math.abs(c[1]-ik[1])+Math.abs(c[2]-ik[2])<3)c=null; /* «инверсная» кнопка: фон = --ink, не трогаем */
  const l=c?L(c):-1,dk=l>=0&&l<.2;let lt=l>.5;
  if(lt&&(el.tagName==='SECTION'||el.classList.contains('sec')||el.offsetWidth>innerWidth*.92&&el.offsetHeight>innerHeight*.5)){el.classList.add('n-clear');lt=false}
  if(lt!==el.classList.contains('n-light'))el.classList.toggle('n-light',lt);
  if(dk!==el.classList.contains('n-dark'))el.classList.toggle('n-dark',dk)})}

let st=0,tt=0;const sched=()=>{clearTimeout(st);st=setTimeout(()=>{scan();scanMag()},80);clearTimeout(tt);tt=setTimeout(tone,350)};
tone();addEventListener('load',()=>setTimeout(tone,400));
scanMag();addEventListener('load',scanMag);
scan();document.addEventListener('DOMContentLoaded',scan);addEventListener('load',scan);
if('MutationObserver' in window)new MutationObserver(sched).observe(document.documentElement,{subtree:true,childList:true});
})();
