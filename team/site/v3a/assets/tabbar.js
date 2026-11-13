/* JARVIS v3a — нижняя панель разделов на телефоне (до 900 px) (задание 14.11, п. 1).
   Подключает nav.js (одна точка для всех страниц). Панель: Главная · Хоккей · Футбол · Итоги · Ещё;
   «Ещё» — лист снизу (не выше 70 % экрана): остальные разделы, поиск, соцсети (assets/social.js).
   Закрывается нажатием мимо, свайпом вниз и клавишей Esc. На компьютере ничего не меняется — верхнее меню как было. */
(()=>{
if(window.__JV_TB)return;window.__JV_TB=1;
const SRC=(document.currentScript&&document.currentScript.src)||new URL('assets/tabbar.js',location.href).href;
const U=p=>new URL('../'+p,SRC).href;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const de=document.documentElement,sport=de.dataset.sport||'';
const path=location.pathname.replace(/\/+$/,'/'),file=path.split('/').pop()||'index.html';
const dir=path.split('/').slice(-2,-1)[0]||'';
const isHome=!sport&&file==='index.html'&&!/\/(me|search|live|team)\/$/.test(path)&&!/^(khl|nhl|epl|laliga|seriea|bundesliga|ligue1|rpl|ucl|uel)$/.test(dir);
const cur=file==='results.html'?'res':sport==='hockey'?'h':sport==='football'?'f':isHome?'home':'';
try{const l=document.createElement('link');l.rel='stylesheet';l.href=new URL('tabbar.css',SRC).href;document.head.appendChild(l)}catch(e){}
/* соцсети — общий файл адресов */
if(!window.JV_SOCIAL){const s=document.createElement('script');s.src=new URL('social.js',SRC).href;s.defer=true;document.head.appendChild(s)}

const I={
 home:'<path d="M3.5 11 12 4l8.5 7"/><path d="M6 9.5V20h4.5v-5.5h3V20H18V9.5"/>',
 h:'<ellipse cx="12" cy="9" rx="7.5" ry="3"/><path d="M4.5 9v4c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V9"/>',
 f:'<circle cx="12" cy="12" r="8.5"/><path d="m12 7.6 3.6 2.6-1.4 4.2H9.8l-1.4-4.2z"/><path d="M12 3.5v4.1M20.2 9.6l-4.6.6M17 19.2l-2.8-4.8M7 19.2l2.8-4.8M3.8 9.6l4.6.6"/>',
 res:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
 more:'<circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>'
};
const ic=k=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${I[k]}</svg>`;
const T=[['home','Главная','index.html'],['h','Хоккей','hockey/index.html'],['f','Футбол','football/index.html'],['res','Итоги','results.html']];
const bar=document.createElement('nav');bar.className='tb';bar.setAttribute('aria-label','Разделы сайта');
bar.innerHTML=T.map(([k,n,h])=>`<a class="tb-i" href="${esc(U(h))}"${cur===k?' aria-current="page"':''}>${ic(k)}<span>${n}</span></a>`).join('')+
 `<button type="button" class="tb-i tb-more" aria-haspopup="dialog" aria-expanded="false" aria-controls="tb-sheet">${ic('more')}<span>Ещё</span></button>`;

/* «Ещё»: разделы, которых нет в панели. Тренды, сравнение и игроки — свои у хоккея и футбола */
const two=(n,hk,fb)=>`<div class="tbs-two"><b>${n}</b><a href="${esc(U(hk))}"${sport==='hockey'&&file===hk.split('/').pop()?' aria-current="page"':''}>Хоккей</a><a href="${esc(U(fb))}"${sport==='football'&&file===fb.split('/').pop()?' aria-current="page"':''}>Футбол</a></div>`;
const one=(n,h,f)=>`<a class="tbs-a" href="${esc(U(h))}"${file===f&&!sport?' aria-current="page"':''}>${n}</a>`;
const sh=document.createElement('div');sh.className='tbs-wrap';sh.hidden=true;
sh.innerHTML=`<div class="tbs-bg"></div><div class="tbs" id="tb-sheet" role="dialog" aria-modal="true" aria-label="Ещё разделы" tabindex="-1">
 <div class="tbs-grip" aria-hidden="true"><i></i></div>
 <div class="tbs-in">
  <button type="button" class="tbs-search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/></svg><span>Поиск: клуб, игрок, матч</span></button>
  <div class="tbs-g">${one('Матчи дня','matches.html','matches.html')}${one('Прогноз на сегодня','forecast.html','forecast.html')}</div>
  ${two('Тренды','hockey/trends.html','football/trends.html')}
  ${two('Сравнение','hockey/compare.html','football/compare.html')}
  ${two('Игроки','hockey/players.html','football/players.html')}
  <div class="tbs-g">${one('Мой JARVIS','me/index.html','')}${one('Как считает модель','model.html','model.html')}${one('Словарь терминов','glossary.html','glossary.html')}</div>
  <p class="tbs-h" data-social-head hidden>Мы в сети</p><div data-social="sheet" hidden></div>
  <button type="button" class="tbs-close">Закрыть</button>
 </div></div>`;

function mount(){
 if(!document.body||document.querySelector('.tb'))return;
 document.body.appendChild(bar);document.body.appendChild(sh);de.classList.add('has-tb');
 const more=bar.querySelector('.tb-more'),box=sh.querySelector('.tbs'),inn=sh.querySelector('.tbs-in');
 let last=null;
 const open=o=>{if(o===!sh.hidden)return;
  if(o){last=document.activeElement;if(window.JV_SOCIAL)JV_SOCIAL.fill(sh);sh.hidden=false;de.classList.add('tbs-open');
   requestAnimationFrame(()=>requestAnimationFrame(()=>sh.classList.add('on')));more.setAttribute('aria-expanded','true');
   setTimeout(()=>{const f=box.querySelector('a,button');f&&f.focus({preventScroll:true})},30)}
  else{sh.classList.remove('on');more.setAttribute('aria-expanded','false');de.classList.remove('tbs-open');box.style.transform='';
   const done=()=>{if(!sh.classList.contains('on'))sh.hidden=true};
   matchMedia('(prefers-reduced-motion: reduce)').matches?done():setTimeout(done,260);
   if(last&&last.focus)try{last.focus({preventScroll:true})}catch(e){}}};
 more.addEventListener('click',()=>open(sh.hidden));
 sh.querySelector('.tbs-bg').addEventListener('click',()=>open(false));
 sh.querySelector('.tbs-close').addEventListener('click',()=>open(false));
 sh.querySelector('.tbs-search').addEventListener('click',()=>{open(false);const b=document.querySelector('#hd .sbtn');if(b)setTimeout(()=>b.click(),40)});
 document.addEventListener('keydown',e=>{if(sh.hidden)return;
  if(e.key==='Escape'){e.preventDefault();open(false);more.focus()}
  /* Tab не уходит из листа, пока он открыт */
  if(e.key==='Tab'){const f=[...box.querySelectorAll('a,button')].filter(x=>x.offsetParent);if(!f.length)return;
   const a=f[0],z=f[f.length-1];if(e.shiftKey&&document.activeElement===a){e.preventDefault();z.focus()}else if(!e.shiftKey&&document.activeElement===z){e.preventDefault();a.focus()}}});
 /* свайп вниз: тянем лист, отпустили ниже 70 px — закрыть */
 let y0=null,dy=0;
 box.addEventListener('touchstart',e=>{if(inn.scrollTop>0&&!e.target.closest('.tbs-grip'))return;y0=e.touches[0].clientY;dy=0;box.style.transition='none'},{passive:true});
 box.addEventListener('touchmove',e=>{if(y0===null)return;dy=Math.max(0,e.touches[0].clientY-y0);if(dy>0)box.style.transform=`translateY(${dy}px)`},{passive:true});
 box.addEventListener('touchend',()=>{if(y0===null)return;y0=null;box.style.transition='';if(dy>70)open(false);else box.style.transform=''},{passive:true});
 addEventListener('resize',()=>{if(innerWidth>900&&!sh.hidden)open(false)});
}
if(document.body)mount();else document.addEventListener('DOMContentLoaded',mount);
})();
