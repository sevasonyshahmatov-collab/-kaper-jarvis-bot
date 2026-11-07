/* Карточки лиг: LeagueCards.mount(el, [{id,name,full,cnt,href,logo,club,photo,photoCls,clubs:[{n,src,href}],cols}]).
   Наклон за курсором / пальцем (rAF, только transform и CSS-переменные), слоистый параллакс, переворот по нажатию на карточку,
   кнопка и эмблемы на обороте — обычные ссылки. prefers-reduced-motion: без наклона. */
(()=>{
'use strict';
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const MAX=14,clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const ARROW='<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.6" aria-hidden="true"><path d="M3 10h13M11 4l6 6-6 6"/></svg>';
/* фактура: наклонные полосы цветов клуба; у Локомотива — красная диагональ с белой кромкой, у Каролины — красная с серебряной */
const TEX=id=>id==='khl'
 ?'<svg class="tex" viewBox="0 0 100 140" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><path d="M-10 150 L60 -10 L100 -10 L100 40 L30 150Z" fill="#d6001c"/><path d="M-10 150 L60 -10 L66 -10 L-4 150Z" fill="#fff" opacity=".9"/><path d="M30 150 L100 40 L100 50 L38 150Z" fill="#fff" opacity=".55"/><path d="M0 0H100V28L0 62Z" fill="#06173a" opacity=".55"/></svg>'
 :'<svg class="tex" viewBox="0 0 100 140" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><path d="M-10 150 L60 -10 L100 -10 L100 40 L30 150Z" fill="#c8102e"/><path d="M-10 150 L60 -10 L66 -10 L-4 150Z" fill="#a2aaad" opacity=".95"/><path d="M30 150 L100 40 L100 50 L38 150Z" fill="#a2aaad" opacity=".5"/><path d="M0 0H100V28L0 62Z" fill="#000" opacity=".45"/></svg>';

function html(l){
 const pl=l.photo?`<img class="pl${l.photoCls?' '+l.photoCls:''}" src="${l.photo}" alt="" draggable="false">`:`<img class="pl emb" src="${l.club}" alt="" draggable="false">`;
 const grid=l.clubs.map(c=>`<a href="${c.href}" title="${esc(c.n)}" aria-label="${esc(c.n)}: страница команды"><img src="${c.src}" alt="" loading="lazy" width="64" height="64"></a>`).join('');
 const n=l.clubs.length;
 return `<div class="lcard ${l.id}" id="lg-${l.id}" tabindex="0" role="group" aria-roledescription="карточка" aria-label="${esc(l.name)}: нажми, чтобы увидеть клубы" data-lg="${l.id}" style="--cols:${l.cols}">
 <div class="shd"></div>
 <div class="tilt"><div class="flip">
  <div class="face front">
   <div class="art">${TEX(l.id)}<i class="holo"></i></div>
   ${pl}
   <div class="frame"></div>
   <div class="top"><img class="lgl" src="${l.logo}" alt=""><img class="clb" src="${l.club}" alt=""></div>
   <div class="txt"><h3>${esc(l.name)}</h3><p class="cn">${esc(l.cnt)}</p>
    <a class="open" href="${l.href}">Страница лиги ${ARROW}</a></div>
  </div>
  <div class="face back" inert><div class="bk">
   <header><img src="${l.logo}" alt=""><b>${esc(l.name)}</b><span>${n} ${l.pl(n)}</span></header>
   <div class="cg" style="--n:${l.cols}">${grid}</div>
   <a class="open" href="${l.href}">Страница лиги ${ARROW}</a>
  </div></div>
 </div></div>
</div>`;
}

function mount(el,leagues){
 el.innerHTML=leagues.map(html).join('');
 const cards=[...el.querySelectorAll('.lcard')];
 const S=cards.map((c,i)=>({c,rx:0,ry:0,tx:0,ty:0,fx:50,tfx:50,s:1,ts:1,ptr:false,rect:null,ph:i*2.1,vis:true}));
 S.forEach(s=>{
  const c=s.c,front=c.querySelector('.front'),back=c.querySelector('.back');
  const flip=on=>{c.classList.toggle('is-flip',on);if(on){front.setAttribute('inert','');back.removeAttribute('inert')}else{back.setAttribute('inert','');front.removeAttribute('inert')}
   c.setAttribute('aria-label',c.getAttribute('aria-label').replace(/:.*/,on?': клубы лиги, нажми, чтобы вернуть':': нажми, чтобы увидеть клубы'))};
  c.addEventListener('click',e=>{if(e.target.closest('a'))return;flip(!c.classList.contains('is-flip'))});
  c.addEventListener('keydown',e=>{if(e.target!==c)return;if(e.key==='Enter'||e.key===' '){e.preventDefault();flip(!c.classList.contains('is-flip'))}else if(e.key==='Escape')flip(false)});
  if(RM)return;
  const rect=()=>{s.rect=c.getBoundingClientRect()};
  const move=e=>{
   const r=s.rect||(rect(),s.rect);
   const px=clamp((e.clientX-r.left)/r.width,0,1),py=clamp((e.clientY-r.top)/r.height,0,1);
   s.ptr=true;s.ty=(px-.5)*2*MAX;s.tx=-(py-.5)*2*MAX;s.ts=1.03;
  };
  const leave=()=>{s.ptr=false;s.ts=1};
  c.addEventListener('pointerenter',e=>{rect();move(e)});
  c.addEventListener('pointerdown',e=>{rect();move(e)});
  c.addEventListener('pointermove',move);
  c.addEventListener('pointerleave',leave);
  c.addEventListener('pointercancel',leave);
  c.addEventListener('pointerup',e=>{if(e.pointerType!=='mouse')leave()});
 });
 if(RM){S.forEach(s=>{s.c.style.setProperty('--hi','.4')});return}
 addEventListener('resize',()=>S.forEach(s=>{s.rect=null}));
 addEventListener('scroll',()=>S.forEach(s=>{s.rect=null}),{passive:true});
 /* крутим кадры только пока карточки на экране */
 let run=false;
 const frame=t=>{
  S.forEach(s=>{
   let tx=s.tx,ty=s.ty;
   if(!s.ptr){const a=t/1000;ty=Math.sin(a*.8+s.ph)*5;tx=Math.cos(a*.6+s.ph)*3.5}
   const k=s.ptr?.14:.07;
   s.rx+=(tx-s.rx)*k;s.ry+=(ty-s.ry)*k;s.s+=(s.ts-s.s)*.12;
   const st=s.c.style;
   st.setProperty('--rx',s.rx.toFixed(2));st.setProperty('--ry',s.ry.toFixed(2));
   st.setProperty('--fx',(50+s.ry/MAX*45+s.rx/MAX*15).toFixed(1));            /* фольга зависит от угла наклона, не от точки под курсором */
   st.setProperty('--hi',(.2+.8*Math.min(1,Math.hypot(s.rx,s.ry)/MAX)).toFixed(2));
   st.setProperty('--s',s.s.toFixed(3));
  });
  if(run)requestAnimationFrame(frame);
 };
 new IntersectionObserver(es=>{const on=es.some(e=>e.isIntersecting);if(on&&!run){run=true;requestAnimationFrame(frame)}else if(!on)run=false},{rootMargin:'80px'}).observe(el);
}
window.LeagueCards={mount};
})();
