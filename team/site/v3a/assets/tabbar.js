/* JARVIS v3a — нижняя панель разделов на телефоне (до 900 px) и правило «одна жёлтая кнопка на экране» (задание 14.11, п. 1–2).
   Подключает nav.js (одна точка для всех страниц). Панель: Главная · Хоккей · Футбол · Итоги · Ещё;
   «Ещё» — лист снизу (не выше 70 % экрана): остальные разделы, поиск, соцсети (assets/social.js).
   Закрывается нажатием мимо, свайпом вниз и клавишей Esc. На компьютере ничего не меняется — верхнее меню как было. */
(()=>{
if(window.__JV_TB)return;window.__JV_TB=1;
const SRC=(document.currentScript&&document.currentScript.src)||new URL('assets/tabbar.js',location.href).href;
const U=p=>new URL('../'+p,SRC).href;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const de=document.documentElement,sport=de.dataset.sport||'';
const path=location.pathname.replace(/\/+$/,'/'),file=path.split('/').pop()||'index.html';
const dir=path.split('/').slice(-2,-1)[0]||'';
const isHome=!sport&&file==='index.html'&&!/\/(me|search|live|team)\/$/.test(path)&&!/^(khl|nhl|epl|laliga|seriea|bundesliga|ligue1|rpl|ucl|uel)$/.test(dir);
const cur=file==='results.html'?'res':sport==='hockey'?'h':sport==='football'?'f':isHome?'home':'';
try{const l=document.createElement('link');l.rel='stylesheet';l.href=new URL('tabbar.css',SRC).href;document.head.appendChild(l)}catch(e){}
/* соцсети — общий файл адресов */
if(!window.JV_SOCIAL&&!document.querySelector('script[src*="social.js"]')){const s=document.createElement('script');s.src=new URL('social.js',SRC).href;s.defer=true;document.head.appendChild(s)}

const I={
 home:'<path d="M5 12l-2 0l9 -9l9 9l-2 0"/> <path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7"/> <path d="M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6"/>',
 h:'<ellipse cx="12" cy="9" rx="7.5" ry="3"/><path d="M4.5 9v4c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V9"/>',
 f:'<path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"/> <path d="M12 7l4.76 3.45l-1.76 5.55h-6l-1.76 -5.55z"/> <path d="M12 7v-4m3 13l2.5 3m-.74 -8.55l3.74 -1.45m-11.44 7.05l-2.56 2.95m.74 -8.55l-3.74 -1.45"/>',
 res:'<path d="M3 13a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v6a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1z"/> <path d="M15 9a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v10a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1z"/> <path d="M9 5a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v14a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1z"/> <path d="M4 20h14"/>',
 more:'<path d="M5 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/> <path d="M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/> <path d="M19 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/>'
};
const ic=k=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${I[k]}</svg>`;
const T=[['home','Главная','index.html'],['h','Хоккей','hockey/index.html'],['f','Футбол','football/index.html'],['res','Итоги','results.html']];
const bar=document.createElement('nav');bar.className='tb';bar.setAttribute('aria-label','Разделы сайта');
bar.innerHTML=T.map(([k,n,h])=>`<a class="tb-i" href="${esc(U(h))}"${cur===k?' aria-current="page"':''}>${ic(k)}<span>${n}</span></a>`).join('')+
 `<button type="button" class="tb-i tb-more" aria-haspopup="dialog" aria-expanded="false" aria-controls="tb-sheet">${ic('more')}<span>Ещё</span></button>`;

/* «Ещё» (переделано 15.11, владелец: «панель стрёмная и неудобная»): список строк как в настройках телефона —
   иконка · название · стрелка; группы по смыслу (общее, Хоккей, Футбол, Сайт); заголовок и крестик сверху, поиск — строкой */
const RI={
 cal:'<path d="M4 7a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2v-12z"/> <path d="M16 3v4"/> <path d="M8 3v4"/> <path d="M4 11h16"/> <path d="M11 15h1"/> <path d="M12 15v3"/>',
 star:'<path d="M12 17.75l-6.172 3.245l1.179 -6.873l-5 -4.867l6.9 -1l3.086 -6.253l3.086 6.253l6.9 1l-5 4.867l1.179 6.873z"/>',
 trend:'<path d="M3 17l6 -6l4 4l8 -8"/> <path d="M14 7l7 0l0 7"/>',
 vs:'<path d="M7 10h14l-4 -4"/> <path d="M17 14h-14l4 4"/>',
 ppl:'<path d="M9 7m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0"/> <path d="M3 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"/> <path d="M16 3.13a4 4 0 0 1 0 7.75"/> <path d="M21 21v-2a4 4 0 0 0 -3 -3.85"/>',
 me:'<path d="M19.5 12.572l-7.5 7.428l-7.5 -7.428a5 5 0 1 1 7.5 -6.566a5 5 0 1 1 7.5 6.572"/>',
 model:'<path d="M9 5h-2a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-12a2 2 0 0 0 -2 -2h-2"/> <path d="M9 3m0 2a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v0a2 2 0 0 1 -2 2h-2a2 2 0 0 1 -2 -2z"/> <path d="M9 17v-5"/> <path d="M12 17v-1"/> <path d="M15 17v-3"/>',
 book:'<path d="M3 19a9 9 0 0 1 9 0a9 9 0 0 1 9 0"/> <path d="M3 6a9 9 0 0 1 9 0a9 9 0 0 1 9 0"/> <path d="M3 6l0 13"/> <path d="M12 6l0 13"/> <path d="M21 6l0 13"/>'
};
const ri=k=>`<svg class="tbs-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${RI[k]}</svg>`;
const chev='<svg class="tbs-ch" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9.5 6 6 6-6 6"/></svg>';
const isCur=(h,sp)=>{const f=h.split('/').pop();return file===f&&(sp?sport===sp:(!sport&&!/^(hockey|football)$/.test(dir)))};
const row=(k,n,h,sp)=>`<a class="tbs-r" href="${esc(U(h))}"${isCur(h,sp)?' aria-current="page"':''}>${ri(k)}<span>${n}</span>${chev}</a>`;
const grp=(t,rows)=>`<section class="tbs-sec">${t?`<h3 class="tbs-t">${t}</h3>`:''}<div class="tbs-list">${rows.join('')}</div></section>`;
const sh=document.createElement('div');sh.className='tbs-wrap';sh.hidden=true;
sh.innerHTML=`<div class="tbs-bg"></div><div class="tbs" id="tb-sheet" role="dialog" aria-modal="true" aria-labelledby="tbs-title" tabindex="-1">
 <div class="tbs-grip" aria-hidden="true"><i></i></div>
 <div class="tbs-head"><b id="tbs-title">Разделы</b><button type="button" class="tbs-x" aria-label="Закрыть"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M18 6l-12 12"/> <path d="M6 6l12 12"/></svg></button></div>
 <div class="tbs-in">
  <button type="button" class="tbs-search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0"/> <path d="M21 21l-6 -6"/></svg><span>Найти клуб, игрока или матч</span></button>
  ${grp('',[row('cal','Матчи дня','matches.html'),row('star','Прогноз на сегодня','forecast.html')])}
  ${grp('Хоккей',[row('trend','Тренды','hockey/trends.html','hockey'),row('vs','Сравнение клубов','hockey/compare.html','hockey'),row('ppl','Игроки','hockey/players.html','hockey')])}
  ${grp('Футбол',[row('trend','Тренды','football/trends.html','football'),row('vs','Сравнение клубов','football/compare.html','football'),row('ppl','Игроки','football/players.html','football')])}
  ${grp('Сайт',[row('me','Мой JARVIS — избранное','me/index.html'),row('model','Как считает модель','model.html'),row('book','Словарь терминов','glossary.html')])}
  <p class="tbs-h" data-social-head hidden>Мы в сети</p><div data-social="sheet" hidden></div>
 </div></div>`;

function mount(){
 if(!document.body||document.querySelector('.tb'))return;
 document.body.appendChild(bar);document.body.appendChild(sh);de.classList.add('has-tb');
 const more=bar.querySelector('.tb-more'),box=sh.querySelector('.tbs'),inn=sh.querySelector('.tbs-in');
 let last=null;
 const open=o=>{if(o===!sh.hidden)return;
  if(o){last=document.activeElement;if(window.JV_SOCIAL)JV_SOCIAL.fill(sh);sh.hidden=false;de.classList.add('tbs-open');
   requestAnimationFrame(()=>requestAnimationFrame(()=>sh.classList.add('on')));more.setAttribute('aria-expanded','true');
   setTimeout(()=>{try{box.focus({preventScroll:true})}catch(e){}},30)}
  else{sh.classList.remove('on');more.setAttribute('aria-expanded','false');de.classList.remove('tbs-open');box.style.transform='';
   const done=()=>{if(!sh.classList.contains('on'))sh.hidden=true};
   matchMedia('(prefers-reduced-motion: reduce)').matches?done():setTimeout(done,260);
   if(last&&last.focus)try{last.focus({preventScroll:true})}catch(e){}}};
 more.addEventListener('click',()=>open(sh.hidden));
 sh.querySelector('.tbs-bg').addEventListener('click',()=>open(false));
 sh.querySelector('.tbs-x').addEventListener('click',()=>open(false));
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
 one1();
}
/* ── одна жёлтая кнопка на экране: кнопка подписки в шапке видна, только когда другие жёлтые кнопки (первый экран, блок подписки) ушли из вида ── */
function one1(){
 const hb=document.querySelector('#hd .btn-tg');if(!hb)return;
 /* проверяем по месту на экране: так же ловятся кнопки, которые страница перерисовывает (колода «Матчей дня») */
 const SEL='main .btn-tg, main .hm-tg, main .get8, main .mt-rem-b, .dk-more';
 /* низ экрана — над нижней панелью: кнопка, закрытая панелью, не видна (главная на телефоне — 16.11) */
 const vis=el=>{const r=el.getBoundingClientRect(),tb=document.querySelector('.tb'),tr=tb&&tb.getBoundingClientRect(),bot=tr&&tr.height?Math.min(innerHeight,tr.top):innerHeight;if(r.width<1||r.height<1||r.bottom<=0||r.top>=bot-8)return false;const c=getComputedStyle(el);return c.visibility!=='hidden'&&c.display!=='none'};
 let t=0;const upd=()=>{t=0;hb.classList.toggle('tb-hide',[...document.querySelectorAll(SEL)].some(vis))};
 const later=()=>{if(!t)t=requestAnimationFrame(upd)};
 addEventListener('scroll',later,{passive:true});addEventListener('resize',later);addEventListener('load',later);
 setInterval(upd,800);upd();
}
if(document.body)mount();else document.addEventListener('DOMContentLoaded',mount);
})();
