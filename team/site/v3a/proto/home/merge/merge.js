/* Голо-карточки «Хоккей / Футбол» на первом экране главной. Раздача с переворотом (GSAP), медленное покачивание само по себе,
   наклон за курсором и пальцем, переворот при нажатии и переход в раздел. reduced-motion — статично. */
(()=>{
'use strict';
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const cards=$$('.mg-deck .card');
if(!cards.length)return;

/* счётчики матчей на карточках */
(()=>{
 const H=window.HOME;if(!H||!H.J)return;
 /* «N матчей сегодня» — все матчи сегодняшнего дня по Москве, как на текущей главной (аудит 08.11: одно правило везде) */
 const all=H.all(),fmt=n=>n.toFixed(1).replace('.',',');
 const T=new Date(Date.now()+3*3600e3).toISOString().slice(0,10);
 const raw=((H.J.TD&&H.J.TD.matches)||[]).filter(m=>m.t&&m.h&&m.a);
 [['hk',true],['fb',false]].forEach(([c,hk])=>{
  const list=all.filter(m=>m.hockey===hk),td=raw.filter(m=>H.isH(m)===hk&&m.t.slice(0,10)===T),use=td.length?td:list;
  const n=use.length,el=$('.mg-deck .card.'+c);if(!el)return;
  el.querySelector('[data-cnt]').textContent=n?`${n} ${H.pl(n,'матч','матча','матчей')} ${td.length?'сегодня':'впереди'}`:'сегодня матчей нет';
  const lam=use.map(m=>{const md=m.md||H.J.M[m.key];return md&&md.lam?md.lam[0]+md.lam[1]:null}).filter(v=>v!=null);
  if(lam.length)el.querySelector('[data-stat]').textContent='ср. тотал по модели '+fmt(lam.reduce((a,b)=>a+b,0)/lam.length);
 });
})();

/* переворот при нажатии → раздел */
cards.forEach(el=>el.addEventListener('click',e=>{
 if(e.metaKey||e.ctrlKey||e.shiftKey||e.button||RM||!window.gsap)return;
 e.preventDefault();if(el.dataset.busy)return;el.dataset.busy=1;
 gsap.to(el.querySelector('.flip'),{rotateY:180,duration:.7,ease:'power2.inOut',onComplete:()=>setTimeout(()=>{location.href=el.href},200)});
}));
addEventListener('pageshow',e=>{if(e.persisted&&window.gsap)cards.forEach(el=>{delete el.dataset.busy;gsap.set(el.querySelector('.flip'),{rotateY:0})})});

/* наклон за курсором / пальцем (просьба владельца 08.11); без курсора — медленное покачивание.
   Голо-полосы переливаются от угла наклона. */
const MAX=14,clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const S=cards.map((el,i)=>({el,ph:i*2.1,rx:0,ry:0,tx:0,ty:0,mx:50,my:50,tmx:50,tmy:50,s:1,ts:1,ptr:false,rect:null}));
S.forEach(s=>{
 const el=s.el;
 const move=e=>{
  const r=s.rect||(s.rect=el.getBoundingClientRect());
  const px=clamp((e.clientX-r.left)/r.width,0,1),py=clamp((e.clientY-r.top)/r.height,0,1);
  s.ptr=true;s.ty=(px-.5)*2*MAX;s.tx=-(py-.5)*2*MAX;s.tmx=px*100;s.tmy=py*100;s.ts=1.03;
 };
 const leave=()=>{s.ptr=false;s.ts=1};
 el.addEventListener('pointerenter',e=>{s.rect=el.getBoundingClientRect();move(e)});
 el.addEventListener('pointerdown',e=>{s.rect=el.getBoundingClientRect();move(e)});
 el.addEventListener('pointermove',move);
 el.addEventListener('pointerleave',leave);
 el.addEventListener('pointercancel',leave);
 el.addEventListener('pointerup',e=>{if(e.pointerType!=='mouse')leave()});
});
addEventListener('resize',()=>S.forEach(s=>{s.rect=null}));
addEventListener('scroll',()=>S.forEach(s=>{s.rect=null}),{passive:true});
function frame(t){
 const a=t/1000;
 S.forEach(s=>{
  let tx=s.tx,ty=s.ty,tmx=s.tmx,tmy=s.tmy;
  if(!s.ptr){ty=Math.sin(a*.5+s.ph)*7;tx=Math.cos(a*.37+s.ph)*4;tmx=50+ty/MAX*45;tmy=50-tx/MAX*45}
  const k=s.ptr?.14:.06;
  s.rx+=(tx-s.rx)*k;s.ry+=(ty-s.ry)*k;s.mx+=(tmx-s.mx)*k;s.my+=(tmy-s.my)*k;s.s+=(s.ts-s.s)*.12;
  const st=s.el.style;
  st.setProperty('--rx',s.rx.toFixed(2));st.setProperty('--ry',s.ry.toFixed(2));
  st.setProperty('--mx',s.mx.toFixed(1));st.setProperty('--my',s.my.toFixed(1));
  st.setProperty('--hi',(.2+.6*Math.min(1,Math.hypot(s.rx,s.ry)/MAX)).toFixed(2));
  st.setProperty('--s',s.s.toFixed(3));
 });
 requestAnimationFrame(frame);
}
if(RM)S.forEach(s=>{const st=s.el.style;st.setProperty('--mx',38);st.setProperty('--my',30);st.setProperty('--hi',.5)});
else requestAnimationFrame(frame);

/* раздача: рубашкой вверх и переворот */
if(!RM&&window.gsap){
 const w=$('.mg-deck').getBoundingClientRect().width;
 gsap.set(cards,{opacity:0});gsap.set(cards.map(c=>c.querySelector('.flip')),{rotateY:180});
 const tl=gsap.timeline({delay:.15});
 cards.forEach((c,i)=>{const d=i?1:-1,t=i*.22;
  tl.fromTo(c,{x:-d*w*.22,y:-220,rotation:-d*20,scale:.75,opacity:0},{x:0,y:0,rotation:0,scale:1,opacity:1,duration:.9,ease:'power3.out'},t);
  tl.to(c.querySelector('.flip'),{rotateY:0,duration:.9,ease:'power2.inOut'},t+.65);
 });
 setTimeout(()=>gsap.set(cards,{opacity:1}),4000);
}
})();
