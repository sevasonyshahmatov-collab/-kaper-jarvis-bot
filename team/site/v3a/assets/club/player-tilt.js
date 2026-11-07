/* Объёмная шапка профиля игрока (владелец 06.11): наклон за курсором/пальцем, слои (без блика — владелец 07.11) на разной глубине
   (номер — дальше, текст — ближе, фото — ближе всех). prefers-reduced-motion — без движения. */
(()=>{
 if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 const go=h=>{
  if(h.dataset.tilt)return;h.dataset.tilt=1;
  const wrap=h.parentElement;wrap.style.perspective='2600px';
  const L=[['.pp-no',-14],['.pp-txt',8],['.pp-photo',22]].map(([s,d])=>[h.querySelector(s),d]).filter(x=>x[0]);
  let tx=0,ty=0,cx=0,cy=0,raf=0,on=false;
  const tick=()=>{cx+=(tx-cx)*.12;cy+=(ty-cy)*.12;
   h.style.transform=`rotateX(${(-cy*3.2).toFixed(2)}deg) rotateY(${(cx*2.6).toFixed(2)}deg) scale(${on?1.008:1})`;
   for(const [el,d] of L)el.style.translate=`${(cx*d).toFixed(1)}px ${(cy*d*.6).toFixed(1)}px`;
   raf=(Math.abs(tx-cx)+Math.abs(ty-cy)>.002||on)?requestAnimationFrame(tick):0};
  const mv=e=>{const b=h.getBoundingClientRect();tx=Math.max(-1,Math.min(1,(e.clientX-b.left)/b.width*2-1));ty=Math.max(-1,Math.min(1,(e.clientY-b.top)/b.height*2-1));on=true;if(!raf)raf=requestAnimationFrame(tick)};
  h.addEventListener('pointermove',mv);h.addEventListener('pointerdown',mv);
  h.addEventListener('pointerleave',()=>{tx=ty=0;on=false;if(!raf)raf=requestAnimationFrame(tick)});
 };
 const find=()=>{const h=document.querySelector('.pp-hero');if(h)go(h);return!!h};
 if(!find())new MutationObserver((m,o)=>{if(find())o.disconnect()}).observe(document.body,{childList:true,subtree:true});
})();
