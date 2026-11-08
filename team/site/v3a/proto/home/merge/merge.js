/* Голо-карточки «Хоккей / Футбол» на первом экране главной. Раздача с переворотом (GSAP), медленное покачивание само по себе,
   переворот при нажатии и переход в раздел. За курсором не наклоняются, блика при наведении нет. reduced-motion — статично. */
(()=>{
'use strict';
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const cards=$$('.mg-deck .card');
if(!cards.length)return;

/* счётчики матчей на карточках */
(()=>{
 const H=window.HOME;if(!H||!H.J)return;
 const all=H.all(),fmt=n=>n.toFixed(1).replace('.',',');
 [['hk',true],['fb',false]].forEach(([c,hk])=>{
  const list=all.filter(m=>m.hockey===hk),td=list.filter(m=>m.day==='сегодня'),use=td.length?td:list;
  const n=use.length,el=$('.mg-deck .card.'+c);if(!el)return;
  el.querySelector('[data-cnt]').textContent=n?`${n} ${H.pl(n,'матч','матча','матчей')} ${td.length?'сегодня':'впереди'}`:'сегодня матчей нет';
  const lam=use.map(m=>m.md&&m.md.lam?m.md.lam[0]+m.md.lam[1]:null).filter(v=>v!=null);
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

/* покачивание: голо-полосы переливаются от угла наклона */
const MAX=9,S=cards.map((el,i)=>({el,ph:i*2.1}));
function frame(t){
 const a=t/1000;
 S.forEach(s=>{
  const ry=Math.sin(a*.5+s.ph)*MAX,rx=Math.cos(a*.37+s.ph)*MAX*.55;
  const st=s.el.style;
  st.setProperty('--rx',rx.toFixed(2));st.setProperty('--ry',ry.toFixed(2));
  st.setProperty('--mx',(50+ry/MAX*40).toFixed(1));st.setProperty('--my',(50-rx/MAX*40).toFixed(1));
  st.setProperty('--hi',(.25+.45*Math.min(1,Math.hypot(rx,ry)/MAX)).toFixed(2));
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
