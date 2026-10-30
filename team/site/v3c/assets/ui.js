/* JARVIS v3c — общее поведение: появление при прокрутке, счётчики, кольца, магнитные кнопки, шапка, наклон табло. */
(()=>{
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const FINE=matchMedia('(hover:hover) and (pointer:fine)').matches;
const fmt=(v,d)=>{const s=v.toFixed(d).replace('.',',');return s.replace(/\B(?=(\d{3})+(?!\d))/g,' ')};

// счётчик: data-count="11000" data-dec="1" data-suf=" %"
function count(el){const to=parseFloat(el.dataset.count),d=+(el.dataset.dec||0),suf=el.dataset.suf||'',pre=el.dataset.pre||'';
 if(RM){el.textContent=pre+fmt(to,d)+suf;return}
 const t0=performance.now(),D=+(el.dataset.dur||1600);
 const f=now=>{const q=Math.min(1,(now-t0)/D),e=1-Math.pow(1-q,4);el.textContent=pre+fmt(to*e,d)+suf;if(q<1)requestAnimationFrame(f)};requestAnimationFrame(f)}

// кольцо: <circle class="fg" data-p="0.62">
function ring(el){el.style.strokeDashoffset=(1-parseFloat(el.dataset.p)).toFixed(4)}

const io=new IntersectionObserver(es=>es.forEach(e=>{if(!e.isIntersecting)return;const el=e.target;io.unobserve(el);
 el.classList.add('in');
 el.querySelectorAll('[data-count]').forEach(count);if(el.dataset.count)count(el);
 el.querySelectorAll('circle[data-p]').forEach(ring);
 el.dispatchEvent(new CustomEvent('seen'))}),{rootMargin:'0px 0px -12% 0px',threshold:.01});
function observe(root=document){root.querySelectorAll('.rv,[data-in]').forEach(el=>{if(!el._obs){el._obs=1;io.observe(el)}})}
observe();

// шапка темнеет после первого экрана; липкая кнопка Telegram — после второго
const hd=document.getElementById('hd'),tg=document.getElementById('tgbar');let lastY=0;
addEventListener('scroll',()=>{const y=scrollY;hd&&hd.classList.toggle('solid',y>40);
 if(tg)tg.classList.toggle('show',y>innerHeight*1.4&&(innerHeight+y)<document.body.scrollHeight-200);lastY=y},{passive:true});

// магнитные кнопки: тянутся к курсору с пружинной инерцией
if(FINE&&!RM)document.querySelectorAll('[data-mag]').forEach(b=>{let tx=0,ty=0,cx=0,cy=0,raf=0;
 const loop=()=>{cx+=(tx-cx)*.18;cy+=(ty-cy)*.18;b.style.setProperty('--tx',cx.toFixed(2)+'px');b.style.setProperty('--ty',cy.toFixed(2)+'px');
  if(Math.abs(tx-cx)>.05||Math.abs(ty-cy)>.05)raf=requestAnimationFrame(loop);else raf=0};
 b.addEventListener('pointermove',e=>{const r=b.getBoundingClientRect();tx=(e.clientX-r.left-r.width/2)*.32;ty=(e.clientY-r.top-r.height/2)*.42;if(!raf)raf=requestAnimationFrame(loop)});
 b.addEventListener('pointerleave',()=>{tx=ty=0;if(!raf)raf=requestAnimationFrame(loop)})});

// табло «Прогноз дня» слегка наклоняется за курсором
if(FINE&&!RM)document.querySelectorAll('[data-tilt]').forEach(c=>{
 c.addEventListener('pointermove',e=>{const r=c.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;c.style.transform=`perspective(900px) rotateY(${(x*7).toFixed(2)}deg) rotateX(${(-y*7).toFixed(2)}deg)`});
 c.addEventListener('pointerleave',()=>{c.style.transform=''})});

window.UI={observe,count,fmt,RM,FINE};
})();
