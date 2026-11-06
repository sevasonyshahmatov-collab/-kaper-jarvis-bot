/* JARVIS · «Лайт» (?theme=lite): поведение. Грузится efir-loader.js только при ?theme=lite, всё под html.lite.
   Делает ровно две вещи:
   1) главная: стеклянное табло «Матч дня» (строится из JV_TODAY / JV_MODEL, как в Эфире, без правки HTML);
   2) страницы клубов: два клина клубных цветов за шапкой (цвета хоккея — из --k-* тела, футбола — из fc-colors.js).
   Карточки при наведении — только CSS (lite.css). Без библиотек. */
(function(){
'use strict';
var D=document,W=window,H=D.documentElement;
if(!H.classList.contains('lite'))return;
var SRC=(D.currentScript&&D.currentScript.src)||'',ROOT=new URL('../../',SRC||location.href).href;
var J=W.JV_TODAY||{matches:[],days:[]},M=W.JV_MODEL||{},C={};
var LGN={khl:'КХЛ',nhl:'НХЛ',epl:'АПЛ',laliga:'Ла Лига',seriea:'Серия А',bundesliga:'Бундеслига',ligue1:'Лига 1',ucl:'Лига чемпионов',uel:'Лига Европы',rpl:'РПЛ'};
var MON=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
function $(s,r){return (r||D).querySelector(s)}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function isH(m){return m.lg==='khl'||m.lg==='nhl'}
function pct(v){return Math.round(v*100)}
function ep(m){var p=m.t.split(/[- :]/).map(Number);return Date.UTC(p[0],p[1]-1,p[2],p[3]-3,p[4])}
function hhmm(m){return m.t.slice(11,16)}
function dlabel(m){var p=m.t.slice(0,10).split('-').map(Number);return p[2]+' '+MON[p[1]-1]}
function p2(n){return (n<10?'0':'')+n}
function cd(m){var s=Math.floor((ep(m)-Date.now())/1000);
  if(s<=0)return s>-10800?'идёт':'старт '+hhmm(m);
  var d=Math.floor(s/86400),h=Math.floor(s%86400/3600),mi=Math.floor(s%3600/60),se=s%60;
  return (d?d+' д ':'')+p2(h)+':'+p2(mi)+':'+p2(se)}
function byKey(k){for(var i=0;i<J.matches.length;i++)if(J.matches[i].key===k)return J.matches[i]}

/* цвета клуба: хоккей — CLUB_SET (dk, a1), футбол — EF_FC ([тёмный, яркий]); нет данных — холодный серый */
function clubCol(m,s){
  var id=m[s],c=C[id],f=W.EF_FC&&W.EF_FC[id];
  if(isH(m)&&c)return c.a1;
  if(!isH(m)&&f)return f[1];
  return s==='h'?'#4a78c9':'#c94a5e'}
function pickFeat(){
  var now=Date.now(),fresh=J.matches.filter(function(m){return ep(m)>now-2*3600e3}),src=fresh.length?fresh:J.matches;
  src=src.slice().sort(function(a,b){return ep(a)-ep(b)});
  var withM=src.filter(function(m){return M[m.key]}),h=withM.filter(isH);
  return h[0]||withM[0]||src[0]}

/* ——— 1. стеклянное табло матча дня (главная) ——— */
function glassHTML(m){
  var o=M[m.key],em=function(s){return '<img src="'+ROOT+'assets/'+(isH(m)?'em':'fc')+'/'+m[s]+'.webp" alt="" decoding="async" onerror="this.style.display=\'none\'">'};
  var p=o?{a:pct(o.p1),x:pct(o.x),b:pct(o.p2),mx:o.p1>=o.x&&o.p1>=o.p2?0:o.p2>=o.x?2:1}:null;
  var cell=function(i,l,v){return '<div'+(p.mx===i?' class="mx"':'')+'><small>'+l+'</small><b>'+v+' %</b></div>'};
  return '<a class="lt-glass lt-gl" style="--lt-a:'+clubCol(m,'h')+';--lt-b:'+clubCol(m,'a')+'" href="'+ROOT+(isH(m)?'hockey':'football')+'/index.html#matches" aria-label="Матч дня: '+esc(m.hn)+' — '+esc(m.an)+'">'+
  '<span class="lt-glass__top"><b>Матч дня · '+esc(LGN[m.lg]||m.lg)+'</b><span>'+dlabel(m)+', '+hhmm(m)+' МСК</span></span>'+
  '<span class="lt-glass__names"><span>'+em('h')+'<i>'+esc(m.hn)+'</i></span><em>VS</em><span>'+em('a')+'<i>'+esc(m.an)+'</i></span></span>'+
  '<span class="lt-glass__clock"><small>До матча</small><b data-lt-cd="'+esc(m.key)+'">'+cd(m)+'</b></span>'+
  (p?'<span class="lt-glass__p">'+cell(0,'П1',p.a)+cell(1,'Х',p.x)+cell(2,'П2',p.b)+'</span>':'')+
  (o&&o.tot?'<span class="lt-glass__foot"><span>Тотал '+String(o.tot).replace('.',',')+': <b>больше '+pct(o.over)+' %</b></span><b>Расчёт модели</b></span>':'')+'</a>'}
function buildGlass(){
  var aside=$('.hm-today');
  if(!aside||$('.lt-glass')||!J.matches||!J.matches.length)return;
  var f=pickFeat();if(!f)return;
  /* табло — над списком «Ближайшие матчи», в той же колонке (список переезжает в обёртку вместе с id) */
  var col=D.createElement('div');col.className='lt-rcol';
  aside.parentNode.insertBefore(col,aside);
  col.insertAdjacentHTML('beforeend',glassHTML(f));col.appendChild(aside);
  var tick=function(){var e=$('[data-lt-cd]');if(!e)return;var m=byKey(e.getAttribute('data-lt-cd'));if(m)e.textContent=cd(m)};
  setInterval(tick,1000)}

/* ——— 2. клинья в шапке клуба ——— */
function teamId(){
  var id=W.JV_TEAM_ID;
  if(!id){try{id=new URLSearchParams(location.search).get('id')}catch(e){}}
  return (id||'').toLowerCase()}
function buildWedges(){
  var hero=$('.tmhero');if(!hero||$('.lt-wedge',hero))return;
  var id=teamId(),f=W.EF_FC&&W.EF_FC[id];
  if(f){H.style.setProperty('--lt-a',f[1]);H.style.setProperty('--lt-b',f[0])}
  hero.insertAdjacentHTML('afterbegin','<i class="lt-wedge lt-wedge--1" aria-hidden="true"></i><i class="lt-wedge lt-wedge--2" aria-hidden="true"></i>')}

/* ——— запуск ——— */
function loadScript(src,cb){var s=D.createElement('script');s.src=src;s.onload=s.onerror=cb;D.head.appendChild(s)}
function need(ok,src,next){if(ok)next();else loadScript(src,next)}
function start(){
  if($('.hm-doors'))need(W.CLUB_SET,ROOT+'assets/club/themes.js',function(){C=W.CLUB_SET||{};
    need(W.EF_FC,ROOT+'assets/efir/fc-colors.js',buildGlass)});
  if($('.tmhero')){
    var kind=W.JV_TEAM_KIND||(D.body.getAttribute('data-field')==='football'?'f':'h');
    if(kind==='f')need(W.EF_FC,ROOT+'assets/efir/fc-colors.js',buildWedges);else buildWedges()}}
if(D.readyState==='loading')D.addEventListener('DOMContentLoaded',start);else start();
})();
