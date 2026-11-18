/* 17.11 — варианты фона для сравнения: ?bg=a|b|c в адресе (запоминается на время вкладки, ?bg=0 — вернуть обычный). Стили — nav.css, разметка льда — v3a.js */
(()=>{const d=document.documentElement;try{const q=new URLSearchParams(location.search).get('bg');if(q!==null)sessionStorage.setItem('jv-bg',/^[abcn]$/.test(q)?q:'0');let b=sessionStorage.getItem('jv-bg');if(b===null)b='n';if(b&&b!=='0')d.dataset.bg=b;else delete d.dataset.bg}catch(e){d.dataset.bg='n'}})(); /* 17.11: «Ночная арена» — основная тема */
/* единый набор иконок сайта (17.11): Tabler Icons, MIT, https://tabler.io/icons — контур 1,75 px, скругления.
   JVI('имя','класс') → <svg>; нет имени — пустая строка */
/* данные разделов (17.11): черновик берёт свежие файлы основного сайта — бот обновляет их там. JVD(адрес) → тот же файл без /draft/;
   свои файлы черновика (фото КХЛ hockey/data/kph) не трогаем */
window.JVD=u=>{try{const a=new URL(u,location.href),m=a.pathname.match(/^(.*)\/draft\/((?:hockey|football|assets)\/data\/(?!kph\/).*)$/);if(a.origin!==location.origin||!m)return u;a.pathname=m[1]+'/'+m[2];return a.href}catch(e){return u}};
window.JVI=(()=>{const P={"up": "<path d=\"M6 15l6 -6l6 6\"/>", "ok": "<path d=\"M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0\"/> <path d=\"M9 12l2 2l4 -4\"/>", "no": "<path d=\"M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0\"/> <path d=\"M10 10l4 4m0 -4l-4 4\"/>", "ret": "<path d=\"M9 14l-4 -4l4 -4\"/> <path d=\"M5 10h11a4 4 0 1 1 0 8h-1\"/>", "streak": "<path d=\"M12 12c2 -2.96 0 -7 -1 -8c0 3.038 -1.773 4.741 -3 6c-1.226 1.26 -2 3.24 -2 5a6 6 0 1 0 12 0c0 -1.532 -1.056 -3.94 -2 -5c-1.786 3 -2.791 3 -4 2z\"/>", "pl": "<path d=\"M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0\"/> <path d=\"M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2\"/>", "tot": "<path d=\"M7 3l0 18\"/> <path d=\"M10 6l-3 -3l-3 3\"/> <path d=\"M20 18l-3 3l-3 -3\"/> <path d=\"M17 21l0 -18\"/>", "btts": "<path d=\"M7 10h14l-4 -4\"/> <path d=\"M17 14h-14l4 4\"/>", "goals": "<path d=\"M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0\"/> <path d=\"M12 7a5 5 0 1 0 5 5\"/> <path d=\"M13 3.055a9 9 0 1 0 7.941 7.945\"/> <path d=\"M15 6v3h3l3 -3h-3v-3z\"/> <path d=\"M15 9l-3 3\"/>", "cor": "<path d=\"M5 5a5 5 0 0 1 7 0a5 5 0 0 0 7 0v9a5 5 0 0 1 -7 0a5 5 0 0 0 -7 0v-9z\"/> <path d=\"M5 21v-7\"/>", "wl": "<path d=\"M5 12l-2 0l9 -9l9 9l-2 0\"/> <path d=\"M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7\"/> <path d=\"M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6\"/>", "ot": "<path d=\"M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0\"/> <path d=\"M12 12l3 2\"/> <path d=\"M12 7v5\"/>", "cs": "<path d=\"M11.46 20.846a12 12 0 0 1 -7.96 -14.846a12 12 0 0 0 8.5 -3a12 12 0 0 0 8.5 3a12 12 0 0 1 -.09 7.06\"/> <path d=\"M15 19l2 2l4 -4\"/>", "outcome": "<path d=\"M7 20l10 0\"/> <path d=\"M6 6l6 -1l6 1\"/> <path d=\"M12 3l0 17\"/> <path d=\"M9 12l-3 -6l-3 6a3 3 0 0 0 6 0\"/> <path d=\"M21 12l-3 -6l-3 6a3 3 0 0 0 6 0\"/>", "win": "<path d=\"M8 21l8 0\"/> <path d=\"M12 17l0 4\"/> <path d=\"M7 4l10 0\"/> <path d=\"M17 4v8a5 5 0 0 1 -10 0v-8\"/> <path d=\"M5 9m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0\"/> <path d=\"M19 9m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0\"/>", "model": "<path d=\"M9 5h-2a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-12a2 2 0 0 0 -2 -2h-2\"/> <path d=\"M9 3m0 2a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v0a2 2 0 0 1 -2 2h-2a2 2 0 0 1 -2 -2z\"/> <path d=\"M9 17v-5\"/> <path d=\"M12 17v-1\"/> <path d=\"M15 17v-3\"/>"};
 return (n,c)=>P[n]?`<svg class="jvi${c?' '+c:''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[n]}</svg>`:''})();
/* 17.11 — фото игроков КХЛ, вырезанные заранее (hockey/data/kph/<папка>_<номер>.webp, без белого фона и каймы; список готовых — kph/index.js).
   Есть готовый файл — показываем его, нет (новый игрок) — как раньше: фото с khl.ru и фильтр #jvko. Определяем раньше остальных скриптов страницы.
   ?v=N — при переобработке фото номер увеличиваем: sw.js хранит картинки «навсегда» по адресу, без смены адреса посетитель увидит старую копию. */
(()=>{const S=document.currentScript&&document.currentScript.src;if(!S||document.documentElement.dataset.sport==='football')return;
 try{if(document.readyState==='loading')document.write('<script src="'+new URL('../hockey/data/kph/index.js',S).href+'"><\/script>')}catch(e){}
 window.JV_KPH=u=>{const m=/khl\.ru\/img\/teamplayers_db\/(\d+)\/(\d+)\.jpg/.exec(u||''),I=window.JV_KPH_IDX;return m&&I&&I[m[1]+'_'+m[2]]?new URL('../hockey/data/kph/'+m[1]+'_'+m[2]+'.webp?v=2',S).href:u}})();
/* Фото игроков КХЛ с www.khl.ru — на белом фоне. Владелец 14.11: «чтобы ни у кого сзади не было белого фона». Вырезать фон у себя
   нельзя (khl.ru не отдаёт фото нашим серверам), поэтому белое делается прозрачным прямо при показе: SVG-фильтр #jvko
   (CSS в v3a.css: img[src*="khl.ru/img/teamplayers_db"]). Пиксели не читаются скриптом — работает и с чужими картинками. */
(()=>{const add=()=>{if(document.getElementById('jvko'))return;const d=document.createElement('div');d.setAttribute('aria-hidden','true');
 d.style.cssText='position:absolute;width:0;height:0;overflow:hidden';
 d.innerHTML='<svg width="0" height="0" focusable="false"><filter id="jvko" x="0" y="0" width="1" height="1" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  -3 -3 -3 8.4 0"/><feComponentTransfer><feFuncA type="linear" slope="1.6" intercept="-.15"/></feComponentTransfer></filter></svg>';
 document.body.appendChild(d)};document.body?add():document.addEventListener('DOMContentLoaded',add)})();
/* JARVIS v3a — общая шапка для всех страниц. Подключается ПЕРЕД v3a.js.
   Рисует: логотип, переключатель Хоккей/Футбол, разделы вида спорта, Telegram, кнопку «Меню» (телефон).
   Меню-якоря страницы (.nav внутри <header id="hd">) переносит во вторую полосу под шапкой.
   Вид спорта и раздел берёт из <html data-sport> и адреса страницы. */
/* уменьшенная эмблема (assets/em/s/, 128 px; список 13.11, п. 7) не нашлась — новый клуб до пересборки: берём полную */
document.addEventListener('error',e=>{const i=e.target;if(i&&i.tagName==='IMG'&&/\/em\/s\//.test(i.src)&&!i.dataset.emf){i.dataset.emf=1;
 i.addEventListener('load',()=>{i.style.visibility=''},{once:true});i.src=i.src.replace('/em/s/','/em/')}},true);
(()=>{
const hd=document.getElementById('hd');if(!hd)return;
const SRC=(document.currentScript&&document.currentScript.src)||new URL('assets/nav.js',location.href).href;
const U=p=>new URL('../'+p,SRC).href;
const path=location.pathname.replace(/\/+$/,''),file=path.split('/').pop()||'index.html';
const dir=path.split('/').slice(-2,-1)[0]||'';
const q=new URLSearchParams(location.search);
const sport=document.documentElement.dataset.sport||'';

const SECTIONS={};
/* Шапка разделов (владелец 10.11). Пункт: [id, имя, адрес] или [id, имя, адрес, [подпункты]] — группа с выпадающим списком. */
{
  /* владелец 10.11 (2): Матчи · Лиги (внутри КХЛ и НХЛ с их разделами) · Тренды · Выбрать матч (карусель «Матчи дня»).
     «Как считаем» — в подвале и в тексте разделов; игроки — внутри лиг. Подпункт с [4-м элементом] — колонка лиги со своими разделами. */
  document.documentElement.classList.add('nav2');
  /* «Игроки» — отдельная страница всех игроков лиги, а не прокрутка к блоку на странице лиги (владелец 13.11) */
  const PLP={khl:'hockey/players_khl.html',nhl:'hockey/players.html'};
  const LS=(lg,base)=>[['Клубы','#clubs'],['Матчи','#next'],['Результаты','#results'],['Игроки','#players'],['Статистика','#stats']].map(([n,h])=>['',n,h==='#players'&&PLP[lg]?PLP[lg]:base+lg+h]);
  const FL=[['epl','АПЛ'],['laliga','Ла Лига'],['seriea','Серия А'],['bundesliga','Бундеслига'],['ligue1','Лига 1'],['rpl','РПЛ']];
  SECTIONS.hockey=[['m','Матчи','hockey/index.html',[['m','Ближайшие матчи','hockey/index.html'],['fc','Прогноз на сегодня — списком','hockey/forecast-khl.html']]],
    ['lg','Лиги','hockey/league.html?lg=khl',[['khl','КХЛ','hockey/league.html?lg=khl',LS('khl','hockey/league.html?lg=')],['nhl','НХЛ','hockey/league.html?lg=nhl',LS('nhl','hockey/league.html?lg=')]]],
    ['tr','Тренды','hockey/trends.html'],['deck','Выбрать матч','matches.html?s=h'],['kup','Купон','hockey/kupon.html']];
  SECTIONS.football=[['m','Матчи','football/index.html',[['m','Ближайшие матчи','football/index.html'],['fc','Прогноз на сегодня — списком','football/forecast-epl.html']]],
    ['lg','Лиги','football/league.html?lg=epl',[...FL.map(([k,n])=>['lg-'+k,n,'football/league.html?lg='+k]),['ucl','Лига чемпионов','football/ucl.html'],['pl','Игроки','football/players.html']]],
    ['tr','Тренды','football/trends.html'],['deck','Выбрать матч','matches.html?s=f']];
}
/* какой пункт активен */
function active(){
  if(window.JV_ACT!==undefined)return window.JV_ACT; /* страницы по понятным адресам (/khl/ska/, /khl/<матч>/) сами задают раздел */
  if(!sport)return '';
  if(dir==='team'){const id=q.get('id')||'',T=window.JV_TEAMS&&JV_TEAMS.teams&&JV_TEAMS.teams[id];
    return T&&T.lg==='nhl'||/^nhl_/.test(id)?'nhl':'khl'}
  if(file==='team.html')return 'lg';
  if(file==='matches.html')return 'deck';
  if(file==='kupon.html')return 'kup';
  if(/^forecast-/.test(file))return 'fc';   /* «Прогноз на сегодня» в меню разделов (владелец 09.11: «как туда попасть?») */
  if(file==='index.html')return 'm';
  if(file==='ucl.html')return 'ucl';
  if(file==='league.html'){const l=q.get('lg')||'';return sport==='hockey'?(l==='nhl'?'nhl':'khl'):(l==='ucl'?'ucl':'lg-'+(l||'epl'))}
  if(/^players/.test(file)||file==='photo-credits.html')return 'lg'; /* игроки — внутри «Лиг» */
  if(file==='trends.html')return 'tr';
  if(file==='model.html')return 'mod';
  return '';
}
const act=active();
/* логотип «JARVIS | раздел» как на баннерах Telegram (выбор владельца 04.11): NHL, КХЛ, ХОККЕЙ, ФУТБОЛ, ЛЧ */
const LSEC=(()=>{if(!sport)return null;
  if(act==='nhl')return ['NHL','nhl'];if(act==='khl')return ['КХЛ','khl'];if(act==='ucl')return ['ЛЧ','ucl'];
  return sport==='hockey'?['ХОККЕЙ','h']:['ФУТБОЛ','f']})();
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const home=(file==='index.html'&&!sport&&dir!=='hockey'&&dir!=='football');
const link=(s,cur)=>`<a href="${esc(U(s[2]))}"${cur===s[0]?' aria-current="page"':''}>${esc(s[1])}</a>`;
const has=(s,cur)=>s[0]===cur||!!s[3]&&s[3].some(x=>has(x,cur));
const inG=(s,cur)=>!!s[3]&&has(s,cur);
const CARET='<svg class="cr" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5 6 7.5 9 4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const col=(x,cur)=>`<div class="gcol"><a class="gch" href="${esc(U(x[2]))}"${cur===x[0]?' aria-current="page"':''}>${/^(khl|nhl)$/.test(x[0])?`<span class="gli" aria-hidden="true"><img src="${esc(U('assets/lg/'+x[0]+'.webp'))}" alt=""></span>`:''}${esc(x[1])}</a>${x[3].map(y=>`<a href="${esc(U(y[2]))}">${esc(y[1])}</a>`).join('')}</div>`;
const top=(s,cur)=>{if(!s[3])return link(s,cur);const cols=s[3].filter(x=>x[3]),rest=s[3].filter(x=>!x[3]);
  return `<div class="gdd${inG(s,cur)?' on':''}"><a href="${esc(U(s[2]))}" aria-haspopup="true"${inG(s,cur)?' aria-current="true"':''}>${esc(s[1])}${CARET}</a><div class="gdd-m${cols.length?' wide':''}${!cols.length&&rest.length>5?' grid':''}">${cols.length?`<div class="gcols">${cols.map(x=>col(x,cur)).join('')}</div>`:''}${rest.map(x=>link(x,cur)).join('')}</div></div>`};
const STAR='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M12 17.75l-6.172 3.245l1.179 -6.873l-5 -4.867l6.9 -1l3.086 -6.253l3.086 6.253l6.9 1l-5 4.867l1.179 6.873z"/></svg>';
const TG='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 3.2 2.9 10.4c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.7c.3-1.3-.5-1.9-1.4-1.5ZM8.3 13.2l9.6-6c.5-.3.9-.1.5.2l-8.2 7.4-.3 3.4-1.6-5Z"/></svg>';

/* page-local меню-якоря: забираем до перерисовки */
const local=hd.querySelector('.nav');
if(local)local.remove();

const sec=SECTIONS[sport]||null;
const mseg=`<div class="mgrp mseg"><a href="${esc(U('hockey/index.html'))}"${sport==='hockey'?' aria-current="true"':''}>Хоккей</a><a href="${esc(U('football/index.html'))}"${sport==='football'?' aria-current="true"':''}>Футбол</a></div>`;
const panel=(sec?[sec]:[SECTIONS.hockey,SECTIONS.football]).map((list,i)=>{
  const name=sec?'':(i?'Футбол':'Хоккей');
  return `<div class="mgrp">${name?`<b>${name}</b>`:''}${list.map(s=>s[3]?`<div class="msub"><b>${esc(s[1])}</b>${s[3].map(x=>link(x,sec?act:'')).join('')}</div>`:link(s,sec?act:'')).join('')}</div>`}).join('');

hd.innerHTML=`<div class="wrap hdrow">
  <div class="logo lg2"><a class="lw" href="${esc(U('index.html'))}" aria-label="JARVIS — выбор: хоккей или футбол">JARVIS</a>${LSEC?`<s aria-hidden="true">|</s><a href="${esc(U(sport+'/index.html'))}" aria-label="${sport==='hockey'?'Хоккей':'Футбол'} — главная раздела"><em class="ls-${LSEC[1]}">${esc(LSEC[0])}</em></a>`:''}</div>
  <nav class="seg" aria-label="Вид спорта">
    <a href="${esc(U('hockey/index.html'))}"${sport==='hockey'?' aria-current="true"':''}>Хоккей</a>
    <a href="${esc(U('football/index.html'))}"${sport==='football'?' aria-current="true"':''}>Футбол</a>
  </nav>
  ${sec?`<nav class="gnav" aria-label="Разделы сайта">${sec.map(s=>top(s,act)).join('')}</nav>`:'<span class="gnav-sp"></span>'}
  <a class="hd-me" href="${esc(U('me/index.html'))}"${file==='index.html'&&dir==='me'?' aria-current="page"':''} title="Мой JARVIS — избранные клубы">${STAR}<span>Мой JARVIS</span></a>
  <button type="button" class="sbtn" aria-label="Поиск по сайту" aria-haspopup="dialog" aria-expanded="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0"/> <path d="M21 21l-6 -6"/></svg><span class="sb-t">Поиск</span><kbd aria-hidden="true">/</kbd></button>
  <a class="btn btn-tg" href="https://t.me/jarvibet" target="_blank" rel="noopener" aria-label="Получать прогнозы в Telegram — бесплатно">${TG}<span>Получать прогнозы<span class="tl"> — бесплатно</span></span></a>
  <button type="button" class="mbtn" id="mbtn" aria-expanded="false" aria-controls="mpanel"><span class="mi" aria-hidden="true"></span><span class="mt">Меню</span></button>
</div>
<div class="mpanel" id="mpanel" hidden>${mseg}<a class="mme" href="${esc(U('me/index.html'))}">${STAR}<span>Мой JARVIS</span></a><button type="button" class="msearch" id="msearch"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0"/> <path d="M21 21l-6 -6"/></svg><span>Поиск: клуб, игрок, матч</span></button>${panel}<a class="mtg" href="https://t.me/jarvibet" target="_blank" rel="noopener">${TG}<span>Получать прогнозы — бесплатно</span></a></div>`;
/* на телефоне в шапке место отдано кнопке подписки: переключатель спорта и поиск живут в меню */
/* шапка всегда в одну строку (09.11: на 1440–1920 px кнопка уезжала за край): если не влезает — компактнее по шагам, в крайнем случае пункты в «Меню» */
{const row=hd.querySelector('.hdrow'),L=['hd-c1','hd-c2','hd-c3'];
 const fit=()=>{if(!row)return;row.classList.remove(...L);if(innerWidth<=1100)return;for(const c of L){if(row.scrollWidth<=row.clientWidth+1)break;row.classList.add(c)}};
 fit();addEventListener('resize',fit);if(document.fonts)document.fonts.ready.then(fit)}
{const ms=document.getElementById('msearch');if(ms)ms.addEventListener('click',()=>{const sb=hd.querySelector('.sbtn');if(sb){document.getElementById('mbtn').click();sb.click()}})}

/* выпадающие группы — на сенсорных экранах первое касание открывает список */
hd.querySelectorAll('.gdd>a').forEach(a=>a.addEventListener('click',e=>{if(matchMedia('(hover:none)').matches){const g=a.parentNode;if(!g.classList.contains('open')){e.preventDefault();hd.querySelectorAll('.gdd.open').forEach(x=>x.classList.remove('open'));g.classList.add('open')}}}));
document.addEventListener('click',e=>{if(!e.target.closest('.gdd'))hd.querySelectorAll('.gdd.open').forEach(x=>x.classList.remove('open'))});
/* поиск (assets/search.js + search.css) — единственная точка подключения */
try{const l=document.createElement('link');l.rel='stylesheet';l.href=new URL('search.css?v=3',SRC).href;document.head.appendChild(l);
  const s=document.createElement('script');s.src=new URL('search.js?v=3',SRC).href;s.defer=true;document.head.appendChild(s)}catch(e){}
/* нижняя панель разделов на телефоне + «одна жёлтая кнопка» (assets/tabbar.js, 14.11) — тоже одна точка подключения */
try{const s=document.createElement('script');s.src=new URL('tabbar.js',SRC).href;document.head.appendChild(s)}catch(e){}
/* движение плашек и активных кнопок (assets/motion.js, 17.11) — одна точка подключения */
try{const s=document.createElement('script');s.src=new URL('motion.js',SRC).href;document.head.appendChild(s)}catch(e){}

/* вторая полоса — якоря страницы */
let sub=null;
if(local&&sport&&file==='index.html'&&(dir==='hockey'||dir==='football'))local.remove();
else if(local){
  sub=document.createElement('div');sub.className='subbar';
  const w=document.createElement('div');w.className='wrap';
  local.setAttribute('aria-label','Разделы страницы');w.appendChild(local);sub.appendChild(w);hd.appendChild(sub);
  /* ссылки на скрытые/отсутствующие блоки не показываем */
  const refresh=()=>{let n=0;local.querySelectorAll('a[href^="#"]').forEach(a=>{const t=document.getElementById(a.getAttribute('href').slice(1));
    const ok=!!t&&!t.hidden;a.hidden=!ok;if(ok)n++});sub.hidden=!n};
  let tm=0;const sched=()=>{clearTimeout(tm);tm=setTimeout(refresh,60)};
  /* подсвеченный при прокрутке пункт держим в видимой части полосы (на телефоне она листается вбок) */
  if('MutationObserver' in window)new MutationObserver(ms=>{for(const m of ms){const a=m.target;if(a.classList&&a.classList.contains('on')&&local.scrollWidth>local.clientWidth){
    local.scrollTo({left:Math.max(0,a.offsetLeft-(local.clientWidth-a.offsetWidth)/2),behavior:'auto'});break}}}).observe(local,{subtree:true,attributes:true,attributeFilter:['class']});
  refresh();document.addEventListener('DOMContentLoaded',refresh);addEventListener('load',refresh);
  if('MutationObserver' in window)new MutationObserver(sched).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['hidden']});
}

/* меню на телефоне */
const btn=document.getElementById('mbtn'),pn=document.getElementById('mpanel');
const setOpen=o=>{pn.hidden=!o;btn.setAttribute('aria-expanded',o?'true':'false');hd.classList.toggle('menu-open',o);document.documentElement.classList.toggle('menu-open',o);btn.querySelector('.mt').textContent=o?'Закрыть':'Меню'};
btn.addEventListener('click',e=>{e.stopPropagation();setOpen(pn.hidden)});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!pn.hidden){setOpen(false);btn.focus()}});
document.addEventListener('click',e=>{if(!pn.hidden&&!pn.contains(e.target))setOpen(false)});
addEventListener('resize',()=>{if(innerWidth>1100&&!pn.hidden)setOpen(false)});

/* страницы без v3a.js: тень шапки при прокрутке */
if(!window.JV){const on=()=>hd.classList.toggle('stuck',scrollY>8);addEventListener('scroll',on,{passive:true});on()}
/* строки вкладок, которые не влезают по ширине (14.11, п. 3): затухание у края, где ещё есть вкладки, и прокрутка к активной.
   Любая полоса с прокруткой вбок: подменю страницы, вкладки лиг, переключатели — находим сами, пересчитываем при изменениях. */
{const SEL='.subbar .nav,[role="tablist"],.tabs,.lg-tabs,.chips';
 const mark=el=>{const ov=el.scrollWidth>el.clientWidth+2;el.classList.toggle('xf',ov);if(!ov){el.classList.remove('xf-l','xf-r');return}
  el.classList.toggle('xf-l',el.scrollLeft>4);el.classList.toggle('xf-r',el.scrollLeft+el.clientWidth<el.scrollWidth-4)};
 const toAct=el=>{const a=el.querySelector('[aria-current="page"],[aria-current="true"],[aria-selected="true"],a.on,.on');if(!a||el.scrollWidth<=el.clientWidth+2)return;
  const l=a.offsetLeft-el.offsetLeft;if(l<el.scrollLeft+8||l+a.offsetWidth>el.scrollLeft+el.clientWidth-40)el.scrollLeft=Math.max(0,l-(el.clientWidth-a.offsetWidth)/2)};
 const scan=first=>document.querySelectorAll(SEL).forEach(el=>{const ox=getComputedStyle(el).overflowX;if(ox!=='auto'&&ox!=='scroll')return;
  if(!el.dataset.xf){el.dataset.xf=1;el.addEventListener('scroll',()=>mark(el),{passive:true});first=true}if(first)toAct(el);mark(el)});
 let t=0;const later=()=>{clearTimeout(t);t=setTimeout(()=>scan(false),120)};
 addEventListener('load',()=>scan(true));addEventListener('resize',later);document.addEventListener('DOMContentLoaded',()=>scan(true));
 if('MutationObserver' in window)new MutationObserver(later).observe(document.documentElement,{subtree:true,childList:true});
 setTimeout(()=>scan(true),900)}
/* активная вкладка подменю — в видимую часть */
addEventListener('load',()=>{const a=hd.querySelector('.subbar a.on');if(a&&a.scrollIntoView)try{a.scrollIntoView({block:'nearest',inline:'center'})}catch(e){}});
})();

/* страница матча: «Поделиться» (11.11) — системное окно телефона, на компьютере ссылка копируется; картинка превью — og.jpg матча */
(function(){
/* цвета клубов с баннера — на всю страницу (фон и плитки вида 3, assets/matchx.css) */
{const h=document.querySelector('main>.mx-hero');if(h)['--hc','--ac'].forEach(k=>{const v=h.style.getPropertyValue(k);if(v)h.parentNode.style.setProperty(k,v)})}
const box=document.querySelector('.mx-info .wrap');if(!box)return;
let row=box.querySelector('.mt-rem');
if(!row){row=document.createElement('div');row.className='mt-rem';box.appendChild(row)}
const b=document.createElement('button');b.type='button';b.className='mt-share';
b.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"/> <path d="M7 9l5 -5l5 5"/> <path d="M12 4l0 12"/></svg><span>Поделиться матчем</span>';
const lab=b.lastChild,say=t=>{lab.textContent=t;setTimeout(()=>{lab.textContent='Поделиться матчем'},2200)};
b.addEventListener('click',()=>{
 const url=location.origin+location.pathname,title=(document.querySelector('h1')||{}).textContent||document.title;
 if(navigator.share&&matchMedia('(pointer:coarse)').matches){navigator.share({title:title.trim(),url}).catch(()=>{});return}
 const done=()=>say('Ссылка скопирована'),old=()=>{const i=document.createElement('input');i.value=url;document.body.appendChild(i);i.select();let ok=false;try{ok=document.execCommand('copy')}catch(e){}i.remove();ok?done():say('Не получилось — скопируйте адрес')};
 if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(url).then(done,old);else old();
});
const first=row.querySelector('.mt-rem-b');first?first.after(b):row.prepend(b);
})();

/* страница матча КХЛ / НХЛ: «Сравнение команд» (assets/mc.js, 12.11) — подгружается сам, пересборка страниц не нужна */
(function(){if(!document.querySelector('main>.mx-hero')||!/\/(khl|nhl)\//.test(location.pathname))return;
const b=(document.currentScript&&document.currentScript.src)||new URL('assets/nav.js',location.href).href;
const s=document.createElement('script');s.src=new URL('mc.js',b).href;document.head.appendChild(s)})();

/* полоса при прокрутке на страницах матча и клуба (assets/stickbar.js, 12.11) */
(function(){if(!document.querySelector('main>.mx-hero')&&!/\/team\/(index\.html)?$/.test(location.pathname))return;
const b=(document.currentScript&&document.currentScript.src)||new URL('assets/nav.js',location.href).href;
const s=document.createElement('script');s.src=new URL('stickbar.js',b).href;document.head.appendChild(s)})();

/* углы (12.11): по умолчанию прямые; ?corners=round — прежние скругления (запоминается), ?corners=sharp — обратно */
(function(){let c=null;try{c=new URLSearchParams(location.search).get('corners');if(c==='round')localStorage.setItem('jv-corners','round');else if(c)localStorage.removeItem('jv-corners');c=localStorage.getItem('jv-corners')}catch(e){}
if(c==='round')document.documentElement.dataset.corners='round'})();

/* переход по ссылке с якорем (#players, #table…): блоки страницы дорисовываются после загрузки данных, и браузер останавливался выше
   нужного места (13.11, владелец: «нажимаю „Игроки“ — не попадаю к игрокам»). Пока страница растёт, возвращаемся к якорю;
   как только человек сам тронул прокрутку — больше не вмешиваемся. */
(function(){let id=decodeURIComponent(location.hash.slice(1));if(!id||!window.ResizeObserver)return;
let stop=false,t0=Date.now();const off=()=>{stop=true};
['wheel','touchstart','keydown','mousedown'].forEach(e=>addEventListener(e,off,{passive:true,once:true}));
const go=()=>{if(stop)return;if(Date.now()-t0>8000){ro.disconnect();return}
 let el=null;try{el=document.getElementById(id)}catch(e){}if(!el)return;
 const mt=(parseFloat(getComputedStyle(el).scrollMarginTop)||0)+(parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop)||0),want=el.getBoundingClientRect().top-mt;
 if(Math.abs(want)>4)scrollBy({top:want,behavior:'auto'})};
const ro=new ResizeObserver(go);ro.observe(document.documentElement);if(document.body)ro.observe(document.body);
addEventListener('load',()=>{go();setTimeout(go,400);setTimeout(go,1500)});
addEventListener('hashchange',()=>{id=decodeURIComponent(location.hash.slice(1));stop=false;t0=Date.now();go()})})();

/* страница футбольного матча: «Сравнение команд» (assets/fmc.js, 13.11) — подгружается сам, пересборка страниц не нужна */
(function(){if(!document.querySelector('main>.mx-hero')||!/\/(epl|laliga|seriea|bundesliga|ligue1|rpl|ucl|uel)\//.test(location.pathname))return;
const b=(document.currentScript&&document.currentScript.src)||new URL('assets/nav.js',location.href).href;
const s=document.createElement('script');s.src=new URL('fmc.js',b).href;document.head.appendChild(s)})();

/* 18.11 владелец: «шестиугольники — в цвета клубов». Пара цветов для двух клубов: акцент клуба из /assets/data/clubs.js
   (JV_CLUBS[id][2]); если цвета соперников похожи — у гостей берётся второй цвет клуба (осветлённый) или запасной. */
window.JVPair=function(a,b,da,db){
  const C=window.JV_CLUBS||{},hex=s=>{const m=/^#?([0-9a-f]{6})$/i.exec(s||'');if(!m)return null;const n=parseInt(m[1],16);return[n>>16,n>>8&255,n&255]},
   d=(x,y)=>Math.hypot(x[0]-y[0],x[1]-y[1],x[2]-y[2]),lum=x=>(.2126*x[0]+.7152*x[1]+.0722*x[2])/255,
   sat=x=>{const mx=Math.max(...x),mn=Math.min(...x);return mx?(mx-mn)/mx:0},
   toh=x=>'#'+x.map(v=>Math.round(v).toString(16).padStart(2,'0')).join(''),
   lift=x=>{let y=x.slice();for(let i=0;i<12&&lum(y)<.3;i++)y=y.map(v=>v+(255-v)*.12);return y},
   /* варианты клуба: основной, второй, акцент — осветлённые для тёмного фона; сначала самые насыщенные (цвет клуба, а не бледный) */
   opts=id=>(C[id]||[]).map(hex).filter(Boolean).map(lift).map(x=>({x,s:sat(x)+(lum(x)>.92?-.2:0)})).sort((p,q)=>q.s-p.s);
  const A=opts(a),B=opts(b),ca=A.length?A[0].x:hex(da);
  let cb=(B.find(o=>!ca||d(o.x,ca)>=110)||{}).x;
  if(!cb){const f=hex(db);cb=f&&ca&&d(f,ca)>=110?f:(ca&&d(hex('#ffffff'),ca)>=110?hex('#ffffff'):hex('#4cc2ff'))}
  return [ca?toh(ca):da,cb?toh(cb):db]};
