/* JARVIS · «Эфир» — общие страницы (matches, model, glossary, forecast, me, 404). Грузится efir-loader.js после efir.js.
   Только оформление: метки разделов, курсивный акцент, появление при прокрутке, клинья в строках, цвета клубов.
   Логику, данные и тексты не меняет. Ждёт window.JVEfir (его ставит efir.js после загрузки цветов клубов). */
(function(){
'use strict';
var D=document,H=D.documentElement;
if(!H.classList.contains('efir'))return;
function $(s,r){return (r||D).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||D).querySelectorAll(s))}
var tries=0;
(function wait(){
  if(window.JVEfir&&D.body)return go(window.JVEfir);
  if(++tries>100)return;            /* 10 секунд */
  setTimeout(wait,100)})();

function ep(m){var p=m.t.split(/[- :]/).map(Number);return Date.UTC(p[0],p[1]-1,p[2],p[3]-3,p[4])}
function tagBefore(el,text,dark){if(!el||!el.parentNode)return;var host=el.parentNode;
  if(host.querySelector(':scope > .ef-tagw'))return;
  el.insertAdjacentHTML('beforebegin',window.JVEfir.tag(text,dark))}
function accent(h){
  if(!h||h.querySelector('.ef-it'))return;
  var w=h.textContent.trim().split(/\s+/);if(w.length<2||h.children.length)return;
  var last=w.pop();h.innerHTML=w.join(' ')+' <span class="ef-it">'+last.replace(/[&<>]/g,'')+'</span>'}
function rv(els){els.forEach(function(e,i){if(e.classList.contains('ef-rv'))return;e.classList.add('ef-rv');e.style.setProperty('--i',i%8)})}

function go(E){
  var path=location.pathname,J=window.JV_TODAY||{matches:[]};
  /* цвет страницы: ближайший матч из данных (если данные подключены) */
  if(J.matches&&J.matches.length&&!H.style.getPropertyValue('--hb')){
    var now=Date.now(),src=J.matches.filter(function(m){return ep(m)>now-2*3600e3});
    src=(src.length?src:J.matches).slice().sort(function(a,b){return ep(a)-ep(b)});
    if(src[0])E.setPageColors(src[0])}

  if($('#dk-deck'))matches(E);
  if(D.body.classList.contains('md'))model(E);
  if(D.body.classList.contains('fc'))forecast(E);
  if(D.body.classList.contains('me-page'))me(E);
  if($('.nf'))rv($$('.nf > *'));
  E.reveal()}

/* ——— Матчи дня ——— */
function matches(E){
  var h1=$('.dk-h1');
  if(h1)tagBefore(h1,'Матчи дня · Эфир');
  var deck=$('#dk-deck');
  /* цвета фона и клиньев следуют за карточкой впереди */
  function sync(){
    var c=$('.dk-card.on',deck)||$('.dk-card',deck);if(!c)return;
    var a=c.style.getPropertyValue('--h1').trim(),b=c.style.getPropertyValue('--h2').trim();
    if(!a||!b)return;var r=H.style;
    r.setProperty('--hb',a);r.setProperty('--ab',b);
    r.setProperty('--hd','color-mix(in srgb,'+a+' 30%,#0b1020)');r.setProperty('--ad','color-mix(in srgb,'+b+' 30%,#0b1020)')}
  var mo=new MutationObserver(sync);
  mo.observe(deck,{subtree:true,attributes:true,attributeFilter:['class','style'],childList:true});
  sync();setTimeout(sync,600)}

/* ——— Модель ——— */
function model(E){
  var T={steps:'Модель · 3 шага',how:'Как считаем',live:'Живой пример',blind:'Слепые зоны',faq:'Вопросы · 6'};
  Object.keys(T).forEach(function(id){var s=D.getElementById(id);if(!s)return;var h=$('h2',s);tagBefore(h,T[id]);accent(h)});
  var cta=$('.md-cta h2');if(cta){tagBefore(cta,'Эфир в Telegram');accent(cta)}
  rv($$('.md-top .wrap > *'));
  $$('.md-sec .wrap > h2, .md-sec .wrap > .ef-tagw').forEach(function(e){e.classList.add('ef-rv')});
  rv($$('.md-steps li,.md-how article,.md-blind li,.md-faq details,.md-pair,.md-warn,.md-picker,.md-demo,.md-cta .wrap > *'));
  /* демо перерисовывается model.js при выборе матча — новое содержимое уже видно, ничего не скрываем */
}

/* ——— Прогноз и словарь ——— */
function forecast(E){
  var crumb=$('.fc-crumbs span[aria-current]'),h1=$('.fc-top h1');
  var label=crumb?crumb.textContent.trim():'';
  if(h1)tagBefore(h1,/Словарь/i.test(label)?'Словарь · Термины':'Прогноз · Сегодня');
  rv($$('.fc-top .wrap > *:not(.ef-tagw)'));
  var tags={'Хоккей':'Хоккей · лиги','Футбол':'Футбол · лиги'};
  $$('.fc-hub-col h2').forEach(function(h){tagBefore(h,tags[h.textContent.trim()]||h.textContent.trim())});
  $$('.fc-hub li').forEach(function(li,i){li.classList.add('ef-rv');li.style.setProperty('--i',i%8)});
  var gl=$('.gl-h');if(gl)tagBefore(gl,'Оглавление · 28');
  rv($$('.gl-toc,.gl-t,.fc-how .wrap > *,.fc-note,.fc-links'));
  $$('.gl-t').forEach(function(e,i){e.style.setProperty('--i',i%2)});
  /* строки матчей (страницы лиг): клинья клубов */
  $$('.fc-m').forEach(function(a,i){
    if(a.querySelector(':scope > .w'))return;
    a.insertAdjacentHTML('afterbegin','<i class="w w--h"></i><i class="w w--a"></i>');
    a.classList.add('ef-rv');a.style.setProperty('--i',i%8)});
  $$('.fc-sec h2').forEach(function(h){if(h.closest('.fc-hub-col'))return})}

/* ——— Мой JARVIS ——— */
function me(E){
  var T={clubs:'Избранное · клубы',next:'Расписание · мои матчи',since:'С прошлого визита',login:'Эфир в Telegram'};
  Object.keys(T).forEach(function(id){var s=D.getElementById(id);if(!s)return;var head=$('.me-head',s),h=$('h2',s);
    var host=head||h;if(!host)return;if(!$('.ef-tagw',s)){host.insertAdjacentHTML('beforebegin',E.tag(T[id]))}});
  rv($$('.me-top .wrap > *'));
  rv($$('.me-sec .wrap > .ef-tagw,.me-head,.me-add,.me-login > *'));
  /* списки рисует me.js: новое содержимое появляется по очереди */
  ['clubsBox','nextBox','sinceBox'].forEach(function(id){var b=D.getElementById(id);if(!b)return;
    function dec(){var items=$$('.me-card,.me-m,.me-empty,.me-day',b);items.forEach(function(e,i){if(!e.classList.contains('ef-rv')){e.classList.add('ef-rv');e.style.setProperty('--i',i%8)}});E.reveal(b)}
    new MutationObserver(dec).observe(b,{childList:true});dec()})}
})();
