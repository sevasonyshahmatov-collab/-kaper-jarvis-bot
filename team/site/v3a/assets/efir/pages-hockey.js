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
function start(){var f=boot[page];if(f)f()}
waitFor(function(){return W.JVEfir},start);
})();
