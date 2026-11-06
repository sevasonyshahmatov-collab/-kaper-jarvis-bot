/* JARVIS · «Эфир» — раздел ФУТБОЛА: поведение. Грузит efir-loader.js только на страницах с data-sport="football" при ?theme=efir.
   Что делает: цвета клубов из эмблем (fc-colors.js) → переменные --hd/--hb/--ad/--ab страницы; клинья на строках матчей;
   hero «в эфире» (гигантские названия, цвета меняются вместе с табло); шапка клуба и матча; метки/появление при прокрутке. */
(function(){
'use strict';
var D=document,W=window,H=D.documentElement;
if(!H.classList.contains('efir')||H.getAttribute('data-sport')!=='football')return;
var FC=W.EF_FC||{},NEU=['#242b3d','#8794ad'];
var LGC={epl:['#2a0f42','#8a3fc7','#062e1f','#00c46a'],laliga:['#2a0f14','#ff4b44','#1b1f2b','#8b95a8'],seriea:['#08265e','#2f8fe0','#08265e','#2fb8ff'],
  bundesliga:['#5a0810','#e0343f','#1a1a1a','#d9d9d9'],ligue1:['#06142e','#2a5ccc','#2b2e06','#dae025'],rpl:['#0a2053','#2d6be0','#4a150b','#e8452c'],
  ucl:['#0a1a52','#2d5bd8','#0a1a52','#7fb2ff'],uel:['#1a0f07','#e0600a','#1a0f07','#ff9a3a']};
function $(s,r){return (r||D).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||D).querySelectorAll(s))}
function fcol(id){return FC[id]||NEU}
function idOf(img){var m=img&&/\/fc\/([^\/.?]+)\.webp/.exec(img.getAttribute('src')||'');return m?m[1]:''}
function d3(a,b){function h(x){return [1,3,5].map(function(i){return parseInt(x.substr(i,2),16)})}var p=h(a),q=h(b);return Math.hypot(p[0]-q[0],p[1]-q[1],p[2]-q[2])}
function pairOf(ia,ib){var a=fcol(ia),b=fcol(ib);if(ib&&d3(a[1],b[1])<120)b=['#1b2338','#8794ad'];return {a:a,b:b}}
function vars(c){return '--hd:'+c.a[0]+';--hb:'+c.a[1]+';--ad:'+c.b[0]+';--ab:'+c.b[1]}
function setPage(c){var s=H.style;s.setProperty('--hd',c.a[0]);s.setProperty('--hb',c.a[1]);s.setProperty('--ad',c.b[0]);s.setProperty('--ab',c.b[1])}
function setLg(k){var c=LGC[k];if(c)setPage({a:[c[0],c[1]],b:[c[2],c[3]]})}

/* ——— строки матчей: клинья клубов по краям (только интерактивное: матч, строка лиги, результат) ——— */
function rows(){
  $$('.match:not([data-ef]),.lgm:not([data-ef]),.resl li:not([data-ef])').forEach(function(r){
    r.setAttribute('data-ef','1');
    var im=$$('img.em',r).map(idOf).filter(Boolean);if(im.length<2)return;
    var c=pairOf(im[0],im[1]);r.setAttribute('style',(r.getAttribute('style')||'')+';'+vars(c));
    r.classList.add('ef-row');
    r.insertAdjacentHTML('afterbegin','<i class="w w--h"></i><i class="w w--a"></i>')})}

/* ——— hero с табло (главная футбола, ЛЧ/ЛЕ): гигантские названия и цвета матча на табло ——— */
function hero(){
  var hh=$('.hero'),card=$('#mcard');if(!hh||!card)return;
  var last='';
  function sync(){
    var tm=$$('.face .tm',card);if(tm.length<2)return;
    var ids=tm.map(function(t){return idOf(t.querySelector('img'))}),names=tm.map(function(t){var s=t.querySelector('span');return s?s.textContent.trim():''});
    var key=ids.join('|');if(key===last)return;last=key;
    var c=pairOf(ids[0],ids[1]);setPage(c);
    $$('.ef-stage__big',hh).forEach(function(e){e.remove()});
    ['h','a'].forEach(function(s,i){var e=D.createElement('span');e.className='ef-stage__big ef-stage__big--'+s;e.setAttribute('aria-hidden','true');e.textContent=(names[i]||'').split(' ')[0];hh.appendChild(e)})}
  sync();new MutationObserver(sync).observe(card,{childList:true,subtree:true})}

/* ——— метки разделов и появление при прокрутке ——— */
function tags(){
  var m=$('#model .ef-tag');if(m&&/3 шага/.test(m.textContent))m.lastChild.textContent='Расчёт модели';
  $$('.sec-head,.lgbar,.lgst>li,.hv>div,.facts li,.wallh,.xb').forEach(function(e){if(!e.classList.contains('ef-rv')&&!e.closest('.ef-in-skip')&&!e.closest('.match')&&!e.closest('.hero'))e.classList.add('ef-rv')});
  if(W.JVEfir)W.JVEfir.reveal()}

/* ——— цвета страницы ——— */
function colors(){
  var q=new URLSearchParams(location.search),lg=q.get('lg'),th=H.getAttribute('data-theme');
  if(/league\.html$/.test(location.pathname)&&lg)setLg(lg);
  else if(th==='ucl'||th==='uel')setLg(th);
  if(W.JV_TEAM_ID){var id=W.JV_TEAM_ID;setPage({a:fcol(id),b:['#1b2338','#8794ad']})}
  else if(/team\.html$/.test(location.pathname)&&q.get('id'))setPage({a:fcol(q.get('id').replace(/-/g,'_')),b:['#1b2338','#8794ad']})}

function start(){
  colors();hero();rows();tags();
  var t=0,main=$('main')||D.body;
  new MutationObserver(function(){cancelAnimationFrame(t);t=requestAnimationFrame(function(){rows();tags()})}).observe(main,{childList:true,subtree:true});
  var pg=W.EF_PAGE;if(pg)pg()}
function boot(){var n=0;(function w(){if(W.JVEfir||n++>40){start();return}setTimeout(w,50)})()}
if(D.readyState==='loading')D.addEventListener('DOMContentLoaded',boot);else boot();
})();
