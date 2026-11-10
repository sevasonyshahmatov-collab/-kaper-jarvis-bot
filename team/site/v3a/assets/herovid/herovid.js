/* Варианты первого экрана «Хоккей» / «Футбол» с видео (макет, 10.11): ?hv=0..4. Без параметра файл ничего не делает.
   Подключается в <head>: ставит html[data-hv] и html[data-hbg] (старые canvas фона не создаются — v3a.js, particles.js). */
(()=>{
'use strict';
let q=null;try{q=new URLSearchParams(location.search).get('hv')}catch(e){}
if(q===null)return;
const N=/^[1-4]$/.test(q)?+q:0,de=document.documentElement,SRC=document.currentScript&&document.currentScript.src,BASE=SRC?new URL('.',SRC).href:'';
const SP=/\/football\//.test(location.pathname)?'football':'hockey';
if(N){de.dataset.hvsp=SP;de.dataset.hv=N;de.dataset.hbg='v'}
const NAMES=['Как сейчас','1 · Кино','2 · Табло в центре','3 · Панель расчёта','4 · Афиша'];
const go=()=>{
 const hero=document.querySelector('.hero');
 if(N&&hero){const bg=document.createElement('div');bg.className='hv-bg';bg.setAttribute('aria-hidden','true');
  /* вариант 1: фото владельца (10.11) вместо эскиза — медленный наезд на CSS, без видео */
  if(N===1){bg.classList.add('hv-photo');const im=new Image();im.alt='';im.src=BASE+SP+'-photo.jpg';bg.appendChild(im);hero.prepend(bg)}
  else{
  const poster=BASE+SP+'-'+N+'.jpg';bg.style.backgroundImage='url("'+poster+'")';
  const still=matchMedia('(prefers-reduced-motion: reduce)').matches||(navigator.connection&&navigator.connection.saveData);
  if(!still){const v=document.createElement('video');v.muted=true;v.loop=true;v.playsInline=true;v.autoplay=true;v.preload='metadata';v.poster=poster;v.src=BASE+SP+'-'+N+'.mp4';
   bg.appendChild(v);const p=v.play();if(p&&p.catch)p.catch(()=>{})}
  hero.prepend(bg)}}
 const sw=document.createElement('nav');sw.className='hv-sw';sw.setAttribute('aria-label','Варианты первого экрана');
 sw.innerHTML='<b>Первый экран</b>'+NAMES.map((n,i)=>{const u=new URL(location.href);u.searchParams.set('hv',i);u.hash='';return '<a href="'+u.pathname+u.search+'"'+(i===N?' aria-current="true"':'')+'>'+n+'</a>'}).join('');
 document.body.appendChild(sw)};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',go);else go();
})();
