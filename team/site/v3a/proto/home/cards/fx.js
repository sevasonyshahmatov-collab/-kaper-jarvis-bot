/* Главная, карточки «Хоккей» и «Футбол» (владелец 16.11).
   1) Пар: над головой и плечами игроков поднимаются и тают полупрозрачные клубы (canvas в каждой карточке).
      Стоит на паузе, когда карточек нет на экране или вкладка скрыта; при «Уменьшении движения» — выключен.
   2) Прожектор: при наведении мышью (на телефоне — при нажатии) сверху на карточку падает луч,
      первый экран и вторая карточка плавно темнеют. Стили — fx.css. */
(()=>{
const deck=document.querySelector('.mg-deck');if(!deck)return;
const hm=deck.closest('.hm')||deck.parentNode;
const cards=[...deck.querySelectorAll('.card')];if(!cards.length)return;
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ── прожектор ── */
const sp=document.createElement('div');sp.className='fx-spot';sp.setAttribute('aria-hidden','true');hm.appendChild(sp);
let tmo=0;
const on=card=>{clearTimeout(tmo);const h=hm.getBoundingClientRect(),r=card.getBoundingClientRect();
  sp.style.setProperty('--fx',(r.left+r.width/2-h.left)+'px');sp.style.setProperty('--fy',(r.top+r.height*.45-h.top)+'px');
  sp.style.setProperty('--fw',r.width+'px');sp.style.setProperty('--fh',r.height+'px');sp.style.setProperty('--ft',Math.max(0,r.top-h.top)+'px');
  hm.classList.add('fx-on');cards.forEach(c=>{c.classList.toggle('fx-dim',c!==card);c.classList.toggle('fx-lit',c===card)})};
const off=()=>{clearTimeout(tmo);hm.classList.remove('fx-on');cards.forEach(c=>c.classList.remove('fx-dim','fx-lit'))};
cards.forEach(c=>{
  c.addEventListener('pointerenter',e=>{if(e.pointerType==='mouse')on(c)});
  c.addEventListener('pointerleave',e=>{if(e.pointerType==='mouse')off()});
  c.addEventListener('pointerdown',e=>{if(e.pointerType!=='mouse'){on(c);tmo=setTimeout(off,1600)}});
  c.addEventListener('pointercancel',off);              // палец начал листать страницу — свет гаснет
  c.addEventListener('focus',()=>on(c));c.addEventListener('blur',off);
});
addEventListener('pageshow',off);                         // возврат «назад» из раздела — без включённого света

/* ── пар ── */
if(RM)return;
const EM={hk:[[.61,-.085,1],[.36,.06,.22],[.86,.08,.22]],fb:[[.51,-.06,1],[.27,.15,.22],[.77,.15,.22]]};   // макушка и края плеч — не на лицо  // [x, y, вес] — доли карточки
const X0=-.15,Y0=-.4;                                   // canvas: x −15…115 %, y −40…60 % карточки
const P=[];
cards.forEach(card=>{const f=card.querySelector('.face.front');if(!f)return;
  const cv=document.createElement('canvas');cv.className='fx-steam';cv.setAttribute('aria-hidden','true');f.appendChild(cv);
  P.push({card,cv,c:cv.getContext('2d'),em:EM[card.dataset.k]||EM.hk,ps:[],acc:Math.random()})});
const size=p=>{const r=p.card.getBoundingClientRect(),d=Math.min(devicePixelRatio||1,2);p.cw=r.width;p.ch=r.height;
  p.w=r.width*1.3;p.h=r.height;p.cv.width=Math.max(1,Math.round(p.w*d));p.cv.height=Math.max(1,Math.round(p.h*d));p.c.setTransform(d,0,0,d,0,0)};
P.forEach(size);addEventListener('resize',()=>P.forEach(size));
const rate=matchMedia('(max-width:600px)').matches?9:13;   // клубов в секунду на карточку
let vis=true,last=performance.now();
if('IntersectionObserver' in window)new IntersectionObserver(es=>{vis=es.some(e=>e.isIntersecting)}).observe(deck);
const spawn=p=>{const s=p.em.reduce((a,e)=>a+e[2],0);let r=Math.random()*s,e=p.em[0];for(const x of p.em){if((r-=x[2])<=0){e=x;break}}
  p.ps.push({x:(e[0]-X0+(Math.random()-.5)*.10)*p.cw,y:(e[1]-Y0-Math.random()*.015)*p.ch,r:p.cw*(.028+Math.random()*.026),
    vx:(Math.random()-.5)*p.cw*.04,vy:-p.ch*(.05+Math.random()*.04),t:0,life:1.9+Math.random()*1.3,ph:Math.random()*6.283,a:.13+Math.random()*.09})};
const tick=now=>{const dt=Math.min(.05,(now-last)/1000);last=now;
  if(vis&&!document.hidden)for(const p of P){
    p.acc+=dt*rate;while(p.acc>=1){p.acc--;if(p.ps.length<70)spawn(p)}
    const c=p.c;c.clearRect(0,0,p.w,p.h);p.ps=p.ps.filter(q=>(q.t+=dt)<q.life);
    for(const q of p.ps){const k=q.t/q.life;q.x+=(q.vx+Math.sin(q.ph+q.t*2.2)*p.cw*.02)*dt;q.y+=q.vy*dt;
      const rr=q.r*(1+k*2.6),a=q.a*(k<.15?k/.15:Math.pow(1-(k-.15)/.85,1.6));   // быстро проявляется у головы и таетif(a<=.002)continue;
      const g=c.createRadialGradient(q.x,q.y,0,q.x,q.y,rr);g.addColorStop(0,'rgba(238,244,252,'+a.toFixed(3)+')');
      g.addColorStop(.5,'rgba(238,244,252,'+(a*.5).toFixed(3)+')');g.addColorStop(1,'rgba(238,244,252,0)');
      c.fillStyle=g;c.beginPath();c.arc(q.x,q.y,rr,0,6.283);c.fill()}}
  requestAnimationFrame(tick)};
requestAnimationFrame(tick);
})();
