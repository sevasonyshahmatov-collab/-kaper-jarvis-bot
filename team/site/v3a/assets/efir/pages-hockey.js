/* JARVIS · «Эфир» · раздел ХОККЕЙ: поведение. Грузится efir-loader.js (только ?theme=efir, html[data-sport=hockey]). Без библиотек. */
(function(){
'use strict';
var D=document,W=window,H=D.documentElement,P=location.pathname;
if(!H.classList.contains('efir'))return;
var RM=W.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
function $(s,r){return (r||D).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||D).querySelectorAll(s))}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function ep(m){var p=m.t.split(/[- :]/).map(Number);return Date.UTC(p[0],p[1]-1,p[2],p[3]-3,p[4])}
function waitFor(cond,cb,n){n=n||0;if(cond())return cb();if(n>80)return;setTimeout(function(){waitFor(cond,cb,n+1)},100)}

var page=/\/hockey\/(index\.html)?$/.test(P)?'index':/\/hockey\/league\.html$/.test(P)?'league':/\/hockey\/trends/.test(P)?'trends':/\/hockey\/player\.html/.test(P)?'player':/\/hockey\/players/.test(P)?'players':/\/hockey\/forecast-/.test(P)?'forecast':/\/(khl|nhl)\/\d{4}-/.test(P)?'match':(/\/team\/(index\.html)?$/.test(P)||/\/(khl|nhl)\/[a-z0-9-]+\/(index\.html)?$/.test(P))?'club':'other';

/* строки матчей (.match): клинья клубов, цвета */
function decorateMatches(){
  var J=W.JV_TODAY||{matches:[]};
  $$('.match:not([data-ef]),.mr:not([data-ef])').forEach(function(el){
    el.setAttribute('data-ef','1');
    var nm=$$('.team span',el).map(function(s){return s.textContent.trim()});
    var m=J.matches.filter(function(x){return x.hn===nm[0]&&x.an===nm[1]})[0];
    if(m){var c=W.JVEfir.cols(m);el.setAttribute('style',W.JVEfir.cv(c));el.dataset.vd=c.hd;el.dataset.vb=c.hb}
    if(el.classList.contains('match'))el.insertAdjacentHTML('afterbegin','<i class="w w--h"></i><i class="w w--a"></i>');
  });
}
function watchMatches(){
  decorateMatches();
  $$('#mlist,.mlist,#modelbox,.mrows').forEach(function(l){new MutationObserver(function(){decorateMatches()}).observe(l,{childList:true,subtree:true})});
}

var boot={};
boot.index=function(){
  var J=W.JV_TODAY||{matches:[]},now=Date.now();
  var hs=J.matches.filter(function(m){return m.lg==='khl'||m.lg==='nhl'}).sort(function(a,b){return ep(a)-ep(b)});
  var f=hs.filter(function(m){return ep(m)>now-2*3600e3})[0]||hs[0];
  if(f)W.JVEfir.setPageColors(f);
  watchMatches();
};
/* метки разделов: тексты по id секции; секции рисует JS страницы, поэтому следим за появлением */
function tagSections(map){
  function run(){
    Object.keys(map).forEach(function(id){
      var sec=D.getElementById(id);if(!sec)return;
      var h=$('.sec-head',sec);if(!h||h.querySelector('.ef-tagw'))return;
      h.insertAdjacentHTML('afterbegin',W.JVEfir.tag(map[id]));
    });
  }
  run();
  $$('main').forEach(function(m){new MutationObserver(run).observe(m,{childList:true,subtree:true})});
}
boot.club=function(){
  tagSections({table:'Таблица · сезон',trends:'Тренды · форма',totals:'Тоталы · шайбы',next:'Следующий матч',games:'Матчи сезона',players:'Игроки',picks:'Наши прогнозы'});
  watchMatches();
};
/* страница матча: цвета клубов, сцена (клинья + гигантские названия), метки разделов, цифры, появление */
function emId(a){var i=a&&a.querySelector('img'),m=i&&/\/em\/([a-z0-9_]+)\.webp/.exec(i.getAttribute('src')||'');return m?m[1]:''}
boot.match=function(){
  var tms=$$('.mt-tm'),top=$('.fc-top');if(tms.length<2||!top)return;
  var lg=(/\/(khl|nhl)\//.exec(P)||[])[1]||'khl',ids=tms.map(emId);
  var c=W.JVEfir.cols({h:ids[0],a:ids[1],lg:lg}),r=H.style;
  r.setProperty('--hd',c.hd);r.setProperty('--hb',c.hb);r.setProperty('--ad',c.ad);r.setProperty('--ab',c.ab);
  var nm=tms.map(function(a){return ((a.querySelector('span')||{}).textContent||'').trim().split(' ')[0]});
  top.insertAdjacentHTML('afterbegin','<div class="mt-stage" aria-hidden="true"><i class="wedge wedge--h"></i><i class="wedge wedge--a"></i><b class="mt-big h">'+esc(nm[0])+'</b><b class="mt-big a">'+esc(nm[1])+'</b></div>');
  var vs=$('.mt-vs');if(vs)vs.textContent='VS';
  prepSections();
};
function prepSections(){
  var T={'mt-md':'Расчёт модели · линия','mt-pv':'Коротко о матче','mt-form':'Форма · 5 матчей','mt-h2h':'Личные встречи','mt-tbl':'Положение в таблице','mt-oth':'В этот день'};
  $$('.fc-sec').forEach(function(s,i){
    var h=$('h2',s);if(h&&T[h.id]&&!$('.ef-tagw',s))h.insertAdjacentHTML('beforebegin',W.JVEfir.tag(T[h.id]));
    if(h&&!h.querySelector('.ef-it')){var w=h.innerHTML.trim().split(' ');if(w.length>1){var l=w.pop();h.innerHTML=w.join(' ')+' <span class="ef-it">'+l+'</span>'}}
    var wr=$('.wrap',s);if(!wr)return;
    $$('.wrap > *',s).forEach(function(e,k){if(e.classList.contains('ef-tagw'))return;e.classList.add('ef-rv');e.style.setProperty('--i',k)});
  });
  /* вероятности модели: пересчёт цифр, максимум отмечен */
  $$('.fc-pm').forEach(function(pm){
    var li=$$('.fc-nums li',pm),best=-1,bi=-1;
    li.forEach(function(x,i){var b=$('b',x),v=parseInt(b.textContent,10);if(v>best){best=v;bi=i}b.innerHTML='<span data-num="'+v+'">'+v+'</span> %'});
    if(li[bi])li[bi].classList.add('mx');
  });
  W.JVEfir.reveal();
}
/* лига: цвета клиньев по лиге; строки .lgm — цвета клубов по эмблемам */
function decorateLgm(lg){
  $$('.lgm:not([data-ef])').forEach(function(el){
    el.setAttribute('data-ef','1');
    var ids=$$('.t img',el).map(function(i){var m=/\/em\/([a-z0-9_]+)\.webp/.exec(i.getAttribute('src')||'');return m?m[1]:''});
    if(ids.length>1&&ids[0]&&ids[1]){var c=W.JVEfir.cols({h:ids[0],a:ids[1],lg:lg});el.setAttribute('style',W.JVEfir.cv(c))}
    el.insertAdjacentHTML('afterbegin','<i class="wd h"></i><i class="wd a"></i>');
  });
}
boot.league=function(){
  var lg=new URLSearchParams(location.search).get('lg')==='nhl'?'nhl':'khl',r=H.style;
  var C=lg==='nhl'?['#10151f','#5b6b86','#2b3446','#d3dbea']:['#0d2a78','#2d57c9','#7a1220','#e0434f'];
  r.setProperty('--hd',C[0]);r.setProperty('--hb',C[1]);r.setProperty('--ad',C[2]);r.setProperty('--ab',C[3]);
  decorateLgm(lg);
  $$('main').forEach(function(m){new MutationObserver(function(){decorateLgm(lg)}).observe(m,{childList:true,subtree:true})});
};
/* прогноз на сегодня: строки .fc-m красим по эмблемам, сцена из клиньев первого матча */
function emIds(el){return $$('img',el).map(function(i){var m=/\/em\/([a-z0-9_]+)\.webp/.exec(i.getAttribute('src')||'');return m?m[1]:''}).filter(Boolean)}
boot.forecast=function(){
  var lg=/forecast-nhl/.test(P)?'nhl':'khl',first=true,top=$('.fc-top');
  $$('.fc-m').forEach(function(el){
    var ids=emIds(el);if(ids.length<2)return;
    var c=W.JVEfir.cols({h:ids[0],a:ids[1],lg:lg});el.setAttribute('style',W.JVEfir.cv(c));
    if(first){first=false;var r=H.style;r.setProperty('--hd',c.hd);r.setProperty('--hb',c.hb);r.setProperty('--ad',c.ad);r.setProperty('--ab',c.ab)}
  });
  if(top&&!$('.mt-stage'))top.insertAdjacentHTML('afterbegin','<div class="mt-stage" aria-hidden="true"><i class="wedge wedge--h"></i><i class="wedge wedge--a"></i></div>');
  var T={};$$('.fc-sec h2').forEach(function(h){if(h.id)T[h.id]=h.id});
  prepSections();
};
/* игрок: клубный цвет из .pp, метки разделов */
boot.player=function(){
  function paint(){
    var pp=$('.pp');if(!pp)return;
    var c=getComputedStyle(pp).getPropertyValue('--c').trim();
    if(c){H.style.setProperty('--hb',c);H.style.setProperty('--hd',c)}
    var map=['Сезон · цифры','Рынки · «n из N»','Форма · матчи','Следующий матч','Линия'],i=0;
    $$('.pp-sec').forEach(function(s,k){var h=$('h2',s);if(h&&!$('.ef-tagw',s)){h.insertAdjacentHTML('beforebegin',W.JVEfir.tag(map[k]||'Игрок'))}});
  }
  paint();
  var m=$('main');if(m)new MutationObserver(paint).observe(m,{childList:true,subtree:true});
};
function start(){var f=boot[page];if(f)f()}
waitFor(function(){return W.JVEfir},start);
})();
