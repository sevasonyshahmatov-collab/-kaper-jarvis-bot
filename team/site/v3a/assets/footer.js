/* JARVIS v3a — единый подвал для всех страниц. Подключение: одна строка после nav.js
   <script src="…/assets/footer.js"></script>. Заменяет старый <footer> страницы (оставляя его #foot — дату данных, если страница её пишет),
   а если подвала нет — добавляет в конец <body>. Стили подтягивает сам (footer.css). */
(()=>{
const SRC=(document.currentScript&&document.currentScript.src)||new URL('assets/footer.js',location.href).href;
const U=p=>new URL('../'+p,SRC).href;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
try{const l=document.createElement('link');l.rel='stylesheet';l.href=new URL('footer.css',SRC).href;document.head.appendChild(l)}catch(e){}
/* соцсети (Telegram, YouTube, Instagram) — адреса в одном файле assets/social.js, плитки появятся сами (14.11, п. 7) */
if(!window.JV_SOCIAL&&!document.querySelector('script[src*="social.js"]'))try{const s=document.createElement('script');s.src=new URL('social.js',SRC).href;s.defer=true;document.head.appendChild(s)}catch(e){}
const COLS=[
 ['Хоккей',[['Матчи','hockey/index.html'],['КХЛ','hockey/league.html?lg=khl'],['НХЛ','hockey/league.html?lg=nhl'],['Игроки','hockey/players.html'],['Тренды','hockey/trends.html'],['Сравнение','hockey/compare.html'],['Прогноз КХЛ на сегодня','hockey/forecast-khl.html'],['Прогноз НХЛ на сегодня','hockey/forecast-nhl.html']]],
 ['Футбол',[['Матчи','football/index.html'],['Лиги','football/league.html?lg=epl'],['Лига чемпионов','football/ucl.html'],['Тренды','football/trends.html'],['Сравнение','football/compare.html'],['Прогноз АПЛ на сегодня','football/forecast-epl.html']]],
 ['JARVIS',[['Матчи дня','matches.html'],['Итоги прогнозов','results.html'],['Мой JARVIS','me/index.html'],['Прогноз на сегодня','forecast.html'],['Как считает модель','model.html'],['Словарь терминов','glossary.html']]]
];
const TG='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 3.2 2.9 10.4c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.7c.3-1.3-.5-1.9-1.4-1.5ZM8.3 13.2l9.6-6c.5-.3.9-.1.5.2l-8.2 7.4-.3 3.4-1.6-5Z"/></svg>';
const old=document.querySelector('footer');
const keep=old&&old.querySelector('#foot');
const f=document.createElement('footer');f.className='jvf';f.setAttribute('aria-label','Подвал сайта');
f.innerHTML=`<div class="wrap"><div class="jvf-top">
  <div class="jvf-brand"><a class="jvf-logo" href="${esc(U('index.html'))}" aria-label="JARVIS, на главную"><span>JARVIS</span></a>
   <p>Прогнозы на хоккей и футбол по расчёту, а не наугад. Бесплатно.</p>
   <div class="jvf-soc" data-social="row"><a class="jvf-tg" href="https://t.me/jarvibet" target="_blank" rel="noopener">${TG}<span>Telegram @jarvibet</span></a></div>
   <button class="jvf-inst" id="jvf-inst" type="button" hidden><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11m0 0-4-4m4 4 4-4M5 19h14"/></svg><span>Установить на экран</span></button>
   <p class="jvf-ios" id="jvf-ios" hidden></p></div>
  <nav class="jvf-cols" aria-label="Разделы сайта">${COLS.map(c=>`<div><b>${esc(c[0])}</b>${c[1].map(l=>`<a href="${esc(U(l[1]))}">${esc(l[0])}</a>`).join('')}</div>`).join('')}</nav>
 </div>
 <div class="jvf-bot"><p class="jvf-data">Данные: ESPN, НХЛ, приложение КХЛ. Линии и расчёт обновляются дважды в день.</p><span class="jvf-slot"></span><span class="jvf-age" title="Сайт только для совершеннолетних">18+</span></div></div>`;
if(keep){keep.className='jvf-note';f.querySelector('.jvf-slot').replaceWith(keep)}
if(old)old.replaceWith(f);else document.body.appendChild(f);
/* «Что дальше» в конце страниц лиг, трендов, игроков, клубов и итогов (14.11, п. 8). Не нужен на главной, в разделах
   Хоккей / Футбол, «Матчах дня», «Прогнозе на сегодня» и на странице матча — там свой следующий шаг */
{const pth=location.pathname,fl=pth.split('/').pop()||'index.html',sp=document.documentElement.dataset.sport||'';
 const skip=/\/\d{4}-\d\d-\d\d-[^/]+\/(index\.html)?$/.test(pth)||/^(matches|forecast.*|404|offline|model|glossary|photo-credits)\.html$/.test(fl)||(fl==='index.html'&&(!sp||/\/(hockey|football)\/(index\.html)?$/.test(pth)))&&!/\/team\/(index\.html)?$/.test(pth);
 const want=/^(results|league|trends|player|players.*|team|ucl|compare)\.html$/.test(fl)||/\/team\/(index\.html)?$/.test(pth)||(sp&&/\/(khl|nhl|epl|laliga|seriea|bundesliga|ligue1|rpl|ucl|uel)\/[^/]+\/(index\.html)?$/.test(pth));
 if(want&&!skip)try{const s=document.createElement('script');s.src=new URL('next.js',SRC).href;s.defer=true;document.head.appendChild(s)}catch(e){}}
/* ── «Установить на экран» и работа без интернета (идеи 37–38) ──
   sw.js лежит в корне сайта; на file:// и в старых браузерах ничего не делаем. ?sw=off — снять регистрацию (для отладки). */
try{if('serviceWorker' in navigator&&/^https?:$/.test(location.protocol)){
 if(/[?&]sw=off(?:&|$)/.test(location.search))navigator.serviceWorker.getRegistrations().then(rs=>rs.forEach(r=>r.unregister()));
 else addEventListener('load',()=>navigator.serviceWorker.register(U('sw.js'),{scope:U('')}).catch(()=>{}))}}catch(e){}
const ib=f.querySelector('#jvf-inst'),ih=f.querySelector('#jvf-ios');let dp=null;
const alone=(window.matchMedia&&matchMedia('(display-mode: standalone)').matches)||navigator.standalone===true;
if(!alone){
 addEventListener('beforeinstallprompt',e=>{e.preventDefault();dp=e;ib.hidden=false});
 addEventListener('appinstalled',()=>{dp=null;ib.hidden=true});
 const ua=navigator.userAgent,ios=/iPad|iPhone|iPod/.test(ua)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
 if(ios&&/Safari/.test(ua)&&!/CriOS|FxiOS|EdgiOS|YaBrowser/.test(ua))ib.hidden=false;
 ib.addEventListener('click',()=>{if(dp){dp.prompt();dp.userChoice.then(()=>{dp=null;ib.hidden=true}).catch(()=>{})}
  else{ih.textContent='В Safari нажмите «Поделиться», затем «На экран „Домой“».';ih.hidden=!ih.hidden}})}
/* нет сети — честная строка под шапкой: данные сохранённые */
const net=()=>{let b=document.getElementById('jv-off');if(navigator.onLine){if(b)b.remove();return}
 if(!b){b=document.createElement('p');b.id='jv-off';b.className='jv-off';b.setAttribute('role','status');b.textContent='Нет интернета — показываем сохранённые данные.';
  const h=document.getElementById('hd');(h&&h.parentNode?h.parentNode:document.body).insertBefore(b,h?h.nextSibling:document.body.firstChild)}};
addEventListener('online',net);addEventListener('offline',net);net();
})();
