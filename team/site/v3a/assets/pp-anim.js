/* Выезд профиля игрока (хоккей и футбол, владелец 14.11). Стили — pp-anim.css (подключает сам). Ждёт, пока player.js / fplayer.js
   заполнит шапку, затем: шапка выезжает, строки по очереди, цифры «досчитываются» от нуля; блоки ниже — при входе в экран, один раз. */
(()=>{
if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
const SRC=(document.currentScript&&document.currentScript.src)||'';
try{const l=document.createElement('link');l.rel='stylesheet';l.href=new URL('pp-anim.css',SRC||location.href).href;document.head.appendChild(l)}catch(e){}
const main=document.getElementById('main');if(!main)return;
const count=b=>{const t=b.textContent.trim();if(!/^\d{1,4}$/.test(t))return;const v=+t;if(!v)return;const t0=performance.now(),D=650;
 const f=n=>{const k=Math.min(1,(n-t0)/D),e=1-Math.pow(1-k,3);b.textContent=String(Math.round(v*e));if(k<1)requestAnimationFrame(f);else b.textContent=t};b.textContent='0';requestAnimationFrame(f)};
const go=h=>{
 if(h.dataset.ppa)return;h.dataset.ppa=1;document.documentElement.classList.add('ppa');
 [...h.querySelectorAll('.pp-txt>*')].forEach((e,i)=>e.style.setProperty('--pi',i));
 [...h.querySelectorAll('.pp-hs>div')].forEach((e,i)=>e.style.setProperty('--pi',4+i));
 h.classList.add('ppa-go');setTimeout(()=>h.querySelectorAll('.pp-hs b').forEach(count),260);
 // блоки ниже шапки
 if(!('IntersectionObserver' in window))return;
 const io=new IntersectionObserver(es=>es.forEach(en=>{if(!en.isIntersecting)return;en.target.classList.add('ppa-in');io.unobserve(en.target)}),{rootMargin:'0px 0px -8% 0px'});
 const vh=innerHeight;
 main.querySelectorAll('.pp-sec,.pp-cta,.nxs').forEach(sec=>{
  const items=sec.querySelectorAll(':scope .pp-tiles>*');
  const list=items.length?[sec.querySelector('h2'),...items].filter(Boolean):[sec];
  list.forEach((e,i)=>{if(e.getBoundingClientRect().top<vh*.92)return;e.style.setProperty('--pi',Math.min(i,8));e.classList.add('ppa-w');io.observe(e)});
 });
};
const find=()=>{const h=main.querySelector('.pp-hero');if(h){go(h);return true}return false};
if(!find()){const mo=new MutationObserver(()=>{if(find())mo.disconnect()});mo.observe(main,{childList:true});setTimeout(()=>mo.disconnect(),15000)}
})();
