/* «Коллекционные карточки»: раздача с переворотом (GSAP), наклон за курсором / пальцем / гироскопом (rAF, только transform и CSS-переменные),
   голо-блик на градиентах по углу, переворот при нажатии. prefers-reduced-motion: статичные карточки, переход без анимации. */
(()=>{
'use strict';
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const DEMO=/[?&]demo/.test(location.search);
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const cards=$$('.card');
const touchy=matchMedia('(hover:none)').matches;
if(touchy)$('.cd-hint').innerHTML='Проведи пальцем по карточке · нажми, чтобы открыть раздел';

/* ── данные главной ─────────────────────────────────────────── */
(()=>{
 const H=window.HOME;if(!H||!H.J)return;
 const e=H.esc,all=H.all();
 $('#cd-date').textContent=H.dateStr();$('#cd-upd').textContent=H.upd();
 const fmt=n=>n.toFixed(1).replace('.',',');
 const k=(m)=>m.ln&&m.bi>=0?[m.ln.p1,m.ln.x,m.ln.p2][m.bi]:null;
 const li=m=>{
  const p=m.md?`${H.pct(m.best)}<small>${m.bi===1?'ничья':e(m.who)}${k(m)?', кэф '+H.f2(k(m)):''}</small>`:'<small>расчёт скоро</small>';
  return `<li><a href="${m.href}"><time>${m.hm}<small>${m.day==='сегодня'?m.lgn:m.day}</small></time><span class="nm"><span>${e(m.hn)}</span><span>${e(m.an)}</span></span><span class="pk${m.best>=.6?' hi':''}">${p}</span></a></li>`;
 };
 [['hk',true,'#cd-h-list'],['fb',false,'#cd-f-list']].forEach(([c,hk,sel])=>{
  const list=all.filter(m=>m.hockey===hk),td=list.filter(m=>m.day==='сегодня'),use=td.length?td:list;
  const n=use.length,el=$('.card.'+c);
  el.querySelector('[data-cnt]').textContent=n?(td.length?`${n} ${H.pl(n,'матч','матча','матчей')} сегодня`:`${n} ${H.pl(n,'матч','матча','матчей')} впереди`):'сегодня матчей нет';
  const lam=use.map(m=>m.md&&m.md.lam?m.md.lam[0]+m.md.lam[1]:null).filter(v=>v!=null);
  if(lam.length)el.querySelector('[data-stat]').textContent='ср. тотал по модели '+fmt(lam.reduce((a,b)=>a+b,0)/lam.length);
  $(sel).innerHTML=list.length?list.slice(0,5).map(li).join(''):'<li class="none">Матчей пока нет.</li>';
 });
})();

/* ── наклон ─────────────────────────────────────────────────── */
const MAX=15,clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const S=cards.map((el,i)=>({el,i,rx:0,ry:0,tx:0,ty:0,mx:50,my:50,tmx:50,tmy:50,s:1,ts:1,ptr:false,rect:null,ph:i*2.1}));
let orient=null,dealt=RM;
const setRect=s=>{s.rect=s.el.getBoundingClientRect()};
S.forEach(s=>{
 const el=s.el;
 const move=e=>{
  const r=s.rect||(setRect(s),s.rect);
  const px=clamp((e.clientX-r.left)/r.width,0,1),py=clamp((e.clientY-r.top)/r.height,0,1);
  s.ptr=true;s.ty=(px-.5)*2*MAX;s.tx=-(py-.5)*2*MAX;s.tmx=px*100;s.tmy=py*100;s.ts=1.035;
 };
 const leave=()=>{s.ptr=false;s.ts=1};
 el.addEventListener('pointerenter',e=>{setRect(s);move(e)});
 el.addEventListener('pointerdown',e=>{setRect(s);move(e)});
 el.addEventListener('pointermove',move);
 el.addEventListener('pointerleave',leave);
 el.addEventListener('pointercancel',leave);
 el.addEventListener('pointerup',e=>{if(e.pointerType!=='mouse')leave()});
 el.addEventListener('click',e=>{
  if(e.metaKey||e.ctrlKey||e.shiftKey||e.button)return;
  if(RM||!window.gsap)return;
  e.preventDefault();
  if(s.busy)return;s.busy=true;
  const fl=el.querySelector('.flip');
  gsap.to(fl,{rotateY:180,duration:.7,ease:'power2.inOut',onComplete:()=>{
   if(DEMO)setTimeout(()=>{gsap.to(fl,{rotateY:0,duration:.7,ease:'power2.inOut',onComplete:()=>{s.busy=false}})},900);
   else setTimeout(()=>{location.href=el.href},220);
  }});
 });
});
addEventListener('resize',()=>S.forEach(setRect));
addEventListener('scroll',()=>S.forEach(s=>{s.rect=null}),{passive:true});

/* гироскоп: на iOS нужно разрешение по нажатию */
const btn=$('#cd-tilt');
function onOri(e){
 if(e.gamma==null||e.beta==null)return;
 orient={ry:clamp(e.gamma/30,-1,1)*MAX,rx:clamp((e.beta-50)/30,-1,1)*-MAX};
}
if(touchy&&!RM&&'DeviceOrientationEvent'in window){
 if(typeof DeviceOrientationEvent.requestPermission==='function'){
  btn.hidden=false;
  btn.addEventListener('click',()=>{DeviceOrientationEvent.requestPermission().then(r=>{if(r==='granted'){addEventListener('deviceorientation',onOri);btn.hidden=true}}).catch(()=>{})});
 }else addEventListener('deviceorientation',onOri);
}

function frame(t){
 S.forEach(s=>{
  let tx=s.tx,ty=s.ty,tmx=s.tmx,tmy=s.tmy;
  if(!s.ptr){
   if(orient){tx=orient.rx;ty=orient.ry}
   else{const a=t/1000;ty=Math.sin(a*.8+s.ph)*6;tx=Math.cos(a*.6+s.ph)*4}
   tmx=50+ty/MAX*45;tmy=50-tx/MAX*45;
  }
  const k=s.ptr?.14:.07;
  s.rx+=(tx-s.rx)*k;s.ry+=(ty-s.ry)*k;s.mx+=(tmx-s.mx)*k;s.my+=(tmy-s.my)*k;s.s+=(s.ts-s.s)*.12;
  const hi=.2+.8*Math.min(1,Math.hypot(s.rx,s.ry)/MAX);
  const st=s.el.style;
  st.setProperty('--rx',s.rx.toFixed(2));st.setProperty('--ry',s.ry.toFixed(2));
  st.setProperty('--mx',s.mx.toFixed(1));st.setProperty('--my',s.my.toFixed(1));
  st.setProperty('--hi',hi.toFixed(2));st.setProperty('--s',s.s.toFixed(3));
 });
 requestAnimationFrame(frame);
}
if(RM){S.forEach(s=>{const st=s.el.style;st.setProperty('--mx',38);st.setProperty('--my',30);st.setProperty('--hi',.5)})}
else requestAnimationFrame(frame);

/* ── раздача: карточки летят рубашкой вверх и переворачиваются ── */
if(!RM&&window.gsap){
 const deckW=$('.cd-deck').getBoundingClientRect().width;
 gsap.set('.card',{opacity:0});
 gsap.set('.flip',{rotateY:180});
 const tl=gsap.timeline({delay:.15});
 cards.forEach((c,i)=>{
  const dir=i?1:-1,t=i*.22;
  tl.fromTo(c,{x:-dir*deckW*.22,y:-260,rotation:-dir*24,scale:.7,opacity:0},{x:0,y:0,rotation:0,scale:1,opacity:1,duration:.95,ease:'power3.out'},t);
  tl.to(c.querySelector('.flip'),{rotateY:0,duration:1,ease:'power2.inOut'},t+.7);
 });
 setTimeout(()=>{gsap.set('.card',{opacity:1})},4000);
}
})();
