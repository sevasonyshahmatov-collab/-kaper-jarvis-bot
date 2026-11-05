/* JARVIS v3a — единый подвал для всех страниц. Подключение: одна строка после nav.js
   <script src="…/assets/footer.js"></script>. Заменяет старый <footer> страницы (оставляя его #foot — дату данных, если страница её пишет),
   а если подвала нет — добавляет в конец <body>. Стили подтягивает сам (footer.css). */
(()=>{
const SRC=(document.currentScript&&document.currentScript.src)||new URL('assets/footer.js',location.href).href;
const U=p=>new URL('../'+p,SRC).href;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
try{const l=document.createElement('link');l.rel='stylesheet';l.href=new URL('footer.css',SRC).href;document.head.appendChild(l)}catch(e){}
const COLS=[
 ['Хоккей',[['Матчи','hockey/index.html'],['КХЛ','hockey/league.html?lg=khl'],['НХЛ','hockey/league.html?lg=nhl'],['Игроки','hockey/players.html'],['Тренды','hockey/trends.html'],['Прогноз КХЛ на сегодня','hockey/forecast-khl.html'],['Прогноз НХЛ на сегодня','hockey/forecast-nhl.html']]],
 ['Футбол',[['Матчи','football/index.html'],['Лиги','football/league.html?lg=epl'],['Лига чемпионов','football/ucl.html'],['Тренды','football/trends.html'],['Прогноз АПЛ на сегодня','football/forecast-epl.html']]],
 ['JARVIS',[['Матчи дня','matches.html'],['Мой JARVIS','me/index.html'],['Прогноз на сегодня','forecast.html'],['Как считает модель','model.html'],['Словарь терминов','glossary.html']]]
];
const TG='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 3.2 2.9 10.4c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.7c.3-1.3-.5-1.9-1.4-1.5ZM8.3 13.2l9.6-6c.5-.3.9-.1.5.2l-8.2 7.4-.3 3.4-1.6-5Z"/></svg>';
const old=document.querySelector('footer');
const keep=old&&old.querySelector('#foot');
const f=document.createElement('footer');f.className='jvf';f.setAttribute('aria-label','Подвал сайта');
f.innerHTML=`<div class="wrap"><div class="jvf-top">
  <div class="jvf-brand"><a class="jvf-logo" href="${esc(U('index.html'))}" aria-label="JARVIS, на главную"><span>JARVIS</span></a>
   <p>Прогнозы на хоккей и футбол по расчёту, а не наугад. Бесплатно.</p>
   <a class="jvf-tg" href="https://t.me/jarvibet" target="_blank" rel="noopener">${TG}<span>Telegram @jarvibet</span></a></div>
  <nav class="jvf-cols" aria-label="Разделы сайта">${COLS.map(c=>`<div><b>${esc(c[0])}</b>${c[1].map(l=>`<a href="${esc(U(l[1]))}">${esc(l[0])}</a>`).join('')}</div>`).join('')}</nav>
 </div>
 <div class="jvf-bot"><p class="jvf-data">Данные: ESPN, НХЛ, приложение КХЛ. Линии и расчёт обновляются дважды в день.</p><span class="jvf-slot"></span><span class="jvf-age" title="Сайт только для совершеннолетних">18+</span></div></div>`;
if(keep){keep.className='jvf-note';f.querySelector('.jvf-slot').replaceWith(keep)}
if(old)old.replaceWith(f);else document.body.appendChild(f);
})();
