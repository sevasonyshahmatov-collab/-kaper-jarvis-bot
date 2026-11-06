/* Фон первого экрана: веер приглушённых карточек лиг (CSS-дрейф, только transform) и ледяная пыль (canvas, мало частиц, без реакции на курсор).
   prefers-reduced-motion: веер статичный, пыль не рисуется. Пыль останавливается, когда первый экран ушёл за экран. */
(()=>{
'use strict';
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const fan=document.getElementById('cd-fan');
if(fan){
 /* лига, x%, y%, поворот°, размер (множитель), размытие px, период дрейфа с, сдвиг по x/y (vmin), поворот дрейфа */
 const F=[['khl',3,6,-17,1.15,1.5,34,2.2,1.6,5],['epl',13,34,-7,1.3,.8,41,1.6,2.4,-4],['laliga',2,62,13,1.05,2,37,2.4,-1.8,6],['ucl',14,76,22,.85,3.2,45,1.4,-2,-5],
  ['nhl',86,5,16,1.1,1.6,38,-2.2,1.8,-5],['seriea',76,31,7,1.25,.8,43,-1.8,2.2,4],['bundesliga',91,59,-13,1.05,2,35,-2,-2,-6],['ligue1',77,75,-21,.9,3.2,47,-1.4,1.6,5]];
 fan.innerHTML=F.map(([lg,x,y,r,s,b,d,dx,dy,dr],i)=>
  `<div class="fw" style="--x:${x}%;--y:${y}%;--s:${s};--i:${i}"><div class="fd" style="--r:${r};--dx:${dx}vmin;--dy:${dy}vmin;--dr:${dr};--d:${d}s;--dl:${-i*5}s"><div class="fk" style="--b:${b}px"><img src="../../../assets/lg/${lg}.webp" alt="" draggable="false"><i></i></div></div></div>`).join('');
}

const cv=document.getElementById('cd-dust');
if(cv&&!RM){
 const ctx=cv.getContext('2d'),hero=cv.parentElement;
 let W=0,H=0,P=[],vis=true,raf=0,last=0;
 const small=matchMedia('(max-width:820px)').matches,N=small?22:38;
 const init=()=>{P=Array.from({length:N},()=>({x:Math.random()*W,y:Math.random()*H,r:.5+Math.random()*1.1,vy:2+Math.random()*5,vx:(Math.random()-.5)*3,a:.12+Math.random()*.25,ph:Math.random()*6.28,sp:.4+Math.random()*.8}))};
 const size=()=>{const dpr=Math.min(devicePixelRatio||1,1.5);W=hero.clientWidth;H=hero.clientHeight;cv.width=W*dpr;cv.height=H*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);if(!P.length)init()};
 const draw=t=>{
  raf=0;if(!vis)return;
  const dt=Math.min(.05,(t-last)/1000||.016);last=t;
  ctx.clearRect(0,0,W,H);ctx.fillStyle='#d6e8ff';
  for(const p of P){
   p.y+=p.vy*dt;p.x+=(p.vx+Math.sin(t/1800*p.sp+p.ph)*4)*dt;
   if(p.y>H+4){p.y=-4;p.x=Math.random()*W}
   if(p.x<-4)p.x=W+4;if(p.x>W+4)p.x=-4;
   ctx.globalAlpha=p.a*(.55+.45*Math.sin(t/1400*p.sp+p.ph));
   ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,6.283);ctx.fill();
  }
  raf=requestAnimationFrame(draw);
 };
 size();new ResizeObserver(size).observe(hero);
 new IntersectionObserver(es=>{vis=es[0].isIntersecting;if(vis&&!raf){last=performance.now();raf=requestAnimationFrame(draw)}}).observe(hero);
 raf=requestAnimationFrame(draw);
}
})();
