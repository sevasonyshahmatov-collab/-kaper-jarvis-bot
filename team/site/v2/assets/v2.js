/* JARVIS v2 — общее поведение: объёмные плашки (наклон с пружиной), появление, шапка, линия маршрута,
   липкая кнопка Telegram, вихрь 360° между спортами, раскрытие портала, Lenis на компьютере. */
(()=>{
 const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
 const FINE=matchMedia('(hover:hover) and (pointer:fine)').matches;
 const H=document.documentElement;
 const ss={get(k){try{return sessionStorage.getItem(k)}catch(e){return null}},set(k,v){try{sessionStorage.setItem(k,v)}catch(e){}},del(k){try{sessionStorage.removeItem(k)}catch(e){}}};

 /* вихрь: прилетели с другого спорта — докручиваем поворот и снимаем размытие */
 if(!RM&&ss.get('jv-vortex')){ss.del('jv-vortex');H.classList.add('v-in');setTimeout(()=>H.classList.remove('v-in'),1200)}
 const fx=()=>{if(!document.querySelector('.whirl')){const w=document.createElement('div');w.className='whirl';const f=document.createElement('div');f.className='fade';document.body.append(w,f)}};
 fx();
 window.__vortex=href=>{if(RM){location.href=href;return}ss.set('jv-vortex','1');H.classList.add('v-out');setTimeout(()=>{location.href=href},900)};
 document.addEventListener('click',e=>{const a=e.target.closest&&e.target.closest('a[data-vortex]');if(!a||e.metaKey||e.ctrlKey||e.shiftKey||e.button)return;e.preventDefault();window.__vortex(a.href)});
 addEventListener('pageshow',e=>{if(e.persisted)H.classList.remove('v-out','v-in')});

 /* шапка, липкая кнопка Telegram */
 const hd=document.getElementById('hd'),tg=document.getElementById('tgbar'),endZone=document.querySelector('[data-tg-hide]');
 const onScroll=()=>{const y=scrollY;hd&&hd.classList.toggle('scrolled',y>40);
  if(tg){let on=y>innerHeight*1.2;if(endZone){const r=endZone.getBoundingClientRect();if(r.top<innerHeight&&r.bottom>0)on=false}tg.classList.toggle('on',on)}};
 addEventListener('scroll',onScroll,{passive:true});onScroll();

 /* появление один раз */
 if(!RM&&'IntersectionObserver' in window){const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{rootMargin:'0px 0px -8% 0px'});
  const watch=()=>document.querySelectorAll('.rv:not(.in)').forEach(el=>io.observe(el));watch();window.__rv=watch}
 else{document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'));window.__rv=()=>document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))}

 /* линия маршрута: подсветка остановки и перелёт по нажатию */
 const route=document.querySelector('.route');
 if(route){const links=[...route.querySelectorAll('a[href^="#"]')],bar=route.querySelector('i');
  const mark=id=>{let k=-1;links.forEach((a,i)=>{const on=a.dataset.seg===id;a.classList.toggle('on',on);if(on){k=i;a.setAttribute('aria-current','step')}else a.removeAttribute('aria-current')});
   if(k>=0&&bar)bar.style.setProperty('--rp',links.length>1?k/(links.length-1):0)};
  document.addEventListener('cam:seg',e=>mark(e.detail.id));
  if(window.__cam)mark(window.__cam.seg);
  links.forEach(a=>a.addEventListener('click',e=>{const t=document.querySelector(a.getAttribute('href'));if(!t)return;e.preventDefault();go(t)}))}
 function go(t){if(window.__lenis)window.__lenis.scrollTo(t,{offset:0,duration:1.6});else t.scrollIntoView({behavior:RM?'auto':'smooth',block:'start'})}
 window.__go=go;

 /* объёмные плашки .dp: наклон к курсору (мышь — при наведении, палец — при нажатии), возврат пружиной, тень по высоте */
 if(!RM){
  const MAX=7,K=170,D=17;               // жёсткость и затухание пружины
  const live=new Set();
  const st=new WeakMap();
  const S=el=>{let s=st.get(el);if(!s){s={x:0,y:0,l:0,vx:0,vy:0,vl:0,tx:0,ty:0,tl:0};st.set(el,s)}return s};
  const aim=(el,e,lift)=>{const r=el.getBoundingClientRect(),s=S(el);const nx=(e.clientX-r.left)/r.width-.5,ny=(e.clientY-r.top)/r.height-.5;
   s.tx=clamp(-ny,-.5,.5)*2*MAX*(el.dataset.tilt?+el.dataset.tilt:1);s.ty=clamp(nx,-.5,.5)*2*MAX*(el.dataset.tilt?+el.dataset.tilt:1);s.tl=lift;live.add(el);kick()};
  const rest=el=>{const s=S(el);s.tx=s.ty=0;s.tl=0;live.add(el);kick()};
  const clamp=(v,a,b)=>v<a?a:v>b?b:v;
  let raf=0,last=0;
  const kick=()=>{if(!raf){last=performance.now();raf=requestAnimationFrame(step)}};
  function step(now){const dt=Math.min(.032,(now-last)/1000);last=now;raf=0;
   live.forEach(el=>{const s=S(el);
    s.vx+=((s.tx-s.x)*K-s.vx*D)*dt;s.vy+=((s.ty-s.y)*K-s.vy*D)*dt;s.vl+=((s.tl-s.l)*K-s.vl*D)*dt;
    s.x+=s.vx*dt;s.y+=s.vy*dt;s.l+=s.vl*dt;
    const done=Math.abs(s.tx-s.x)+Math.abs(s.ty-s.y)+Math.abs(s.tl-s.l)<.01&&Math.abs(s.vx)+Math.abs(s.vy)+Math.abs(s.vl)<.01;
    if(done){s.x=s.tx;s.y=s.ty;s.l=s.tl;live.delete(el)}
    el.style.transform=s.x||s.y||s.l?`perspective(1000px) rotateX(${s.x.toFixed(2)}deg) rotateY(${s.y.toFixed(2)}deg) translateZ(${(s.l*18).toFixed(1)}px)`:'';
    el.style.setProperty('--lift',Math.max(0,s.l).toFixed(3))});
   if(live.size)raf=requestAnimationFrame(step)}
  if(FINE){
   document.addEventListener('pointermove',e=>{const el=e.target.closest&&e.target.closest('.dp');if(el)aim(el,e,1)},{passive:true});
   document.addEventListener('pointerout',e=>{const el=e.target.closest&&e.target.closest('.dp');if(el&&!el.contains(e.relatedTarget))rest(el)},{passive:true});
  }else{
   let cur=null;
   document.addEventListener('pointerdown',e=>{const el=e.target.closest&&e.target.closest('.dp');if(!el||e.target.closest('input'))return;cur=el;aim(el,e,.6)},{passive:true});
   document.addEventListener('pointermove',e=>{if(cur)aim(cur,e,.6)},{passive:true});
   ['pointerup','pointercancel'].forEach(t=>document.addEventListener(t,()=>{if(cur){rest(cur);cur=null}}));
  }
  // магнит кнопки Telegram (только мышь)
  if(FINE)document.querySelectorAll('.btn-tg').forEach(b=>{b.addEventListener('pointermove',e=>{const r=b.getBoundingClientRect();b.style.translate=`${(((e.clientX-r.left)/r.width-.5)*10).toFixed(1)}px ${(((e.clientY-r.top)/r.height-.5)*8).toFixed(1)}px`});b.addEventListener('pointerleave',()=>b.style.translate='')});
 }

 /* Lenis 1.1.20 — только компьютер с мышью; CDN недоступен — прокрутка обычная */
 if(FINE&&!RM&&innerWidth>=900){
  const add=src=>new Promise((ok,no)=>{const e=document.createElement('script');e.src=src;e.async=false;e.onload=ok;e.onerror=no;document.head.appendChild(e)});
  const start=()=>add('https://cdn.jsdelivr.net/npm/lenis@1.1.20/dist/lenis.min.js').then(()=>{
   const lenis=new Lenis({lerp:.09});window.__lenis=lenis;const raf=t=>{lenis.raf(t);requestAnimationFrame(raf)};requestAnimationFrame(raf)}).catch(()=>{});
  const goL=()=>'requestIdleCallback' in window?requestIdleCallback(start,{timeout:1200}):setTimeout(start,300);
  document.readyState==='complete'?goL():addEventListener('load',goL);
 }
})();
