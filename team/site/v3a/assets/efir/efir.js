/* JARVIS · тема «Эфир»: поведение. Грузится efir-loader.js только при ?theme=efir. Без библиотек.
   Что делает: фон-клинья, шапка (часы эфира), цвета клубов из assets/club/themes.js, сцена матча дня на главной,
   строки-титры с клиньями, метки разделов, пересчёт цифр, блик, появление при прокрутке, переход-клин между страницами.
   Публичное: window.JVEfir = {cols, cv, emUrl, scramble, reveal, setPageColors, tag}. */
(function(){
'use strict';
var D=document,W=window,H=D.documentElement;
if(!H.classList.contains('efir'))return;
var SRC=(D.currentScript&&D.currentScript.src)||'',BASE=SRC.replace(/efir\.js.*$/,''),ROOT=new URL('../../',BASE||location.href).href;
var RM=W.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
var J=W.JV_TODAY||{matches:[],days:[]},M=W.JV_MODEL||{},L=W.JV_LINES||{},C={};
var LGN={khl:'КХЛ',nhl:'НХЛ',epl:'АПЛ',laliga:'Ла Лига',seriea:'Серия А',bundesliga:'Бундеслига',ligue1:'Лига 1',ucl:'Лига чемпионов',uel:'Лига Европы',rpl:'РПЛ'};
var MON=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
function $(s,r){return (r||D).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||D).querySelectorAll(s))}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function isH(m){return m.lg==='khl'||m.lg==='nhl'}
function pct(v){return Math.round(v*100)}
function num1(n){return String(n).replace('.',',')}
function ep(m){var p=m.t.split(/[- :]/).map(Number);return Date.UTC(p[0],p[1]-1,p[2],p[3]-3,p[4])}
function hhmm(m){return m.t.slice(11,16)}
function dlabel(m){var p=m.t.slice(0,10).split('-').map(Number);return p[2]+' '+MON[p[1]-1]}
function byKey(k){for(var i=0;i<J.matches.length;i++)if(J.matches[i].key===k)return J.matches[i]}
function emUrl(m,s){return ROOT+'assets/'+(isH(m)?'em':'fc')+'/'+m[s]+'.webp'}
function emImg(m,s,cls){return '<img class="'+cls+'" data-s="'+s+'" src="'+emUrl(m,s)+'" alt="" decoding="async">'}
function clubUrl(m){return ROOT+(isH(m)?'hockey':'football')+'/index.html#matches'}

/* ——— цвета клубов (из assets/club/themes.js: dk — тёмный, a1 — яркий) ——— */
function h2r(h){h=h.replace('#','');return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)]}
function r2hsl(c){var r=c[0]/255,g=c[1]/255,b=c[2]/255,mx=Math.max(r,g,b),mn=Math.min(r,g,b),l=(mx+mn)/2,h=0,s=0,d=mx-mn;if(d){s=l>.5?d/(2-mx-mn):d/(mx+mn);h=mx===r?(g-b)/d+(g<b?6:0):mx===g?(b-r)/d+2:(r-g)/d+4;h*=60}return [h,s,l]}
function hsl(h,s,l){return 'hsl('+Math.round(h)+' '+Math.round(s*100)+'% '+Math.round(l*100)+'%)'}
function dist(a,b){var x=h2r(a),y=h2r(b);return Math.hypot(x[0]-y[0],x[1]-y[1],x[2]-y[2])}
function hash(s){var h=0;for(var i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))>>>0;return h}
function lift(hex){var q=r2hsl(h2r(hex));return hsl(q[0],Math.max(q[1],.6),.56)}
function pair(m,s,other){
  var id=m[s],c=C[id];
  if(isH(m)&&c){var d=c.dk,b=c.a1;if(other&&C[other]&&dist(b,C[other].a1)<150&&s==='a')b=lift(c.dk);return [d,b]}
  var h=hash(id)%360;if(s==='a'&&Math.abs(h-hash(m.h)%360)<70)h=(h+140)%360;
  return [hsl(h,.5,.15),hsl(h,.68,.48)]}
function cols(m){var a=pair(m,'h'),b=pair(m,'a',m.h);return {hd:a[0],hb:a[1],ad:b[0],ab:b[1]}}
function cv(c){return '--hd:'+c.hd+';--hb:'+c.hb+';--ad:'+c.ad+';--ab:'+c.ab}
function mot(m,s){var c=C[m[s]];return c&&c.m?'url("'+ROOT+'assets/club/m/'+c.m[0]+'.svg")':'none'}
function setPageColors(m){var c=cols(m),r=H.style;r.setProperty('--hd',c.hd);r.setProperty('--hb',c.hb);r.setProperty('--ad',c.ad);r.setProperty('--ab',c.ab)}

/* ——— время и цифры ——— */
function mskNow(){return new Date().toLocaleTimeString('ru-RU',{timeZone:'Europe/Moscow',hour:'2-digit',minute:'2-digit'})}
function p2(n){return (n<10?'0':'')+n}
function cd(m){var s=Math.floor((ep(m)-Date.now())/1000);
  if(s<=0)return s>-10800?'идёт':'старт '+hhmm(m);
  var d=Math.floor(s/86400),h=Math.floor(s%86400/3600),mi=Math.floor(s%3600/60),se=s%60;
  return (d?d+' д ':'')+p2(h)+':'+p2(mi)+':'+p2(se)}
function tickCd(){$$('[data-cd]').forEach(function(e){var m=byKey(e.dataset.cd);if(m)e.textContent=cd(m)})}
function scramble(el,final,dur,delay){
  final=String(final);if(RM||!el){if(el)el.textContent=final;return}
  var t0=null,n=final.length;el.textContent=final.replace(/\d/g,'0');
  setTimeout(function(){requestAnimationFrame(function f(t){if(t0===null)t0=t;var k=Math.min(1,(t-t0)/dur),lock=Math.floor(k*k*(3-2*k)*n),o='';
    for(var i=0;i<n;i++){var ch=final[i];o+=/\d/.test(ch)&&i>=lock?Math.floor(Math.random()*10):ch}
    el.textContent=k>=1?final:o;if(k<1)requestAnimationFrame(f)})},delay||0)}
function runNums(root){$$('[data-num]',root).forEach(function(e,i){scramble(e,e.dataset.num,900,i*250)})}

/* ——— появление при прокрутке: .ef-rv → .ef-in; внутри — пересчёт [data-num] ——— */
var io=null;
function reveal(root){
  var els=$$('.ef-rv:not(.ef-in)',root||D);
  if(!('IntersectionObserver' in W)||RM){els.forEach(function(e){e.classList.add('ef-in');runNums(e)});return}
  if(!io)io=new IntersectionObserver(function(en){en.forEach(function(x){if(x.isIntersecting){var e=x.target;e.classList.add('ef-in');runNums(e);io.unobserve(e)}})},{threshold:.12,rootMargin:'0px 0px -6% 0px'});
  els.forEach(function(e){io.observe(e)})}

/* ——— метка раздела ——— */
function tag(text,dark){return '<span class="ef-tagw"><span class="ef-tag'+(dark?' ef-tag--dark':'')+'"><i></i>'+esc(text)+'</span></span>'}

/* ——— сцена матча дня ——— */
function pr(k){var m=M[k];return m?{a:pct(m.p1),x:pct(m.x),b:pct(m.p2),mx:m.p1>=m.x&&m.p1>=m.p2?0:m.p2>=m.x?2:1}:null}
function pickFeat(){
  var now=Date.now(),fresh=J.matches.filter(function(m){return ep(m)>now-2*3600e3}),src=fresh.length?fresh:J.matches;
  src=src.slice().sort(function(a,b){return ep(a)-ep(b)});
  var withM=src.filter(function(m){return M[m.key]}),h=withM.filter(isH);
  return h[0]||withM[0]||src[0]}
function bugHTML(m){
  var p=pr(m.key),o=M[m.key],c=cols(m);
  return '<a class="ef-glass ef-gl" href="'+clubUrl(m)+'" data-vd="'+c.hd+'" data-vb="'+c.hb+'" aria-label="Расчёт модели: '+esc(m.hn)+' — '+esc(m.an)+'">'+
  '<span class="ef-glass__top"><b>'+esc(LGN[m.lg]||m.lg)+'</b><span>'+dlabel(m)+', '+hhmm(m)+' МСК</span></span>'+
  '<span class="ef-glass__names"><span>'+esc(m.hn)+'</span><em>VS</em><span>'+esc(m.an)+'</span></span>'+
  '<span class="ef-glass__clock"><small>До матча</small><b data-cd="'+esc(m.key)+'">'+cd(m)+'</b></span>'+
  (p?'<span class="ef-glass__p"><div class="'+(p.mx===0?'mx':'')+'"><small>П1</small><b><span data-num="'+p.a+'">'+p.a+'</span> %</b></div><div class="'+(p.mx===1?'mx':'')+'"><small>Х</small><b><span data-num="'+p.x+'">'+p.x+'</span> %</b></div><div class="'+(p.mx===2?'mx':'')+'"><small>П2</small><b><span data-num="'+p.b+'">'+p.b+'</span> %</b></div></span>':'')+
  (o&&o.tot?'<span class="ef-glass__foot"><span>Тотал '+num1(o.tot)+': <b>больше '+pct(o.over)+' %</b></span><b>Расчёт модели</b></span>':'')+'</a>'}
function stageHTML(m){
  var c=cols(m);
  return '<div class="ef-stage" id="ef-stage" style="'+cv(c)+'"><div class="wedge wedge--h" style="--mot:'+mot(m,'h')+'"></div><div class="wedge wedge--a" style="--mot:'+mot(m,'a')+'"></div>'+
  '<span class="ef-stage__big ef-stage__big--h" aria-hidden="true">'+esc(m.hn.split(' ')[0])+'</span><span class="ef-stage__big ef-stage__big--a" aria-hidden="true">'+esc(m.an.split(' ')[0])+'</span>'+
  emImg(m,'h','ef-stage__em ef-stage__em--h')+emImg(m,'a','ef-stage__em ef-stage__em--a')+
  '<b class="ef-stage__nm ef-stage__nm--h">'+esc(m.hn)+'</b><b class="ef-stage__nm ef-stage__nm--a">'+esc(m.an)+'</b>'+bugHTML(m)+'</div>'}
function buildStage(){
  var hm=$('.hm'),today=$('.hm-today');if(!hm||!today||$('#ef-stage'))return;
  var f=pickFeat();if(!f)return;
  setPageColors(f);
  today.insertAdjacentHTML('beforebegin',stageHTML(f));
  var st=$('#ef-stage');
  $$('.ef-stage__em',st).forEach(function(i){i.onerror=function(){i.style.display='none'}});
  runNums(st);tickCd();parallax(st)}
function parallax(st){
  if(RM||!matchMedia('(hover:hover) and (pointer:fine)').matches)return;
  var wh=$('.wedge--h',st),wa=$('.wedge--a',st),tx=0,cx=0,run=false,vis=true;
  new IntersectionObserver(function(e){vis=e[0].isIntersecting}).observe(st);
  var loop=function(){cx+=(tx-cx)*.08;var v=cx*14;wh.style.translate=(-v)+'px';wa.style.translate=v+'px';
    if(Math.abs(tx-cx)>.002&&vis&&!D.hidden)requestAnimationFrame(loop);else run=false};
  st.addEventListener('pointermove',function(e){var r=st.getBoundingClientRect();tx=((e.clientX-r.left)/r.width-.5)*2;if(!run){run=true;requestAnimationFrame(loop)}});
  st.addEventListener('pointerleave',function(){tx=0;if(!run){run=true;requestAnimationFrame(loop)}})}

/* ——— строки «Ближайшие матчи» (их рисует home.js): клинья клубов, шаг появления ——— */
function decorateRows(){
  $$('.hm-row:not([data-ef])').forEach(function(a,i){
    a.setAttribute('data-ef','1');
    var nm=$$('.hm-tm span',a).map(function(s){return s.textContent.trim()}),tm=(a.querySelector('.hm-t')||{}).firstChild;tm=tm?tm.textContent.trim():'';
    var m=J.matches.filter(function(x){return x.hn===nm[0]&&x.an===nm[1]&&hhmm(x)===tm})[0]||J.matches.filter(function(x){return x.hn===nm[0]&&x.an===nm[1]})[0];
    if(m){var c=cols(m);a.setAttribute('style',cv(c));a.dataset.vd=c.hd;a.dataset.vb=c.hb}
    a.insertAdjacentHTML('afterbegin','<i class="w w--h"></i><i class="w w--a"></i>');
    a.classList.add('ef-rv');a.style.setProperty('--i',i);
    /* владелец 05.11: источник линии не называем */
    $$('.hm-info > span',a).forEach(function(s){if(/^Линия:/.test(s.textContent))s.remove()});
  });
  reveal($('.hm-list'))}

/* ——— тексты и метки ——— */
var TAGS={doubts:'Отвечаем прямо',model:'Модель · 3 шага',honest:'Итоги дня',faq:'Вопросы · 4'};
function decorateText(){
  var h1=$('.hm h1');
  if(h1&&!h1.querySelector('.ln')){
    var t=h1.textContent.trim(),k=t.indexOf('а не наугад'),a=k>0?t.slice(0,k).trim():t,b=k>0?'а не наугад':'';
    var l1,l2,m1=/^(Прогнозы на хоккей) (.+)$/.exec(a);
    if(m1){l1=m1[1];l2=m1[2]}else{var w=a.split(' '),mid=Math.ceil(w.length/2);l1=w.slice(0,mid).join(' ');l2=w.slice(mid).join(' ')}
    var l=[l1,l2].map(function(s){return '<span class="ln"><span>'+esc(s)+'</span></span>'}).join('');
    h1.setAttribute('aria-label',t);
    h1.innerHTML=l+(b?'<span class="ln"><span class="ef-it">'+b+'</span></span>':'')}
  /* курсивный акцент — последнее слово заголовков разделов */
  $$('.sec-head h2,.faq h2,.sub h2').forEach(function(h){
    if(h.querySelector('.ef-it'))return;var w=h.innerHTML.replace(/&nbsp;/g,' ').trim().split(' ');if(w.length<2)return;
    var last=w.pop();h.innerHTML=w.join(' ')+' <span class="ef-it">'+last+'</span>'});
  /* метки разделов */
  Object.keys(TAGS).forEach(function(id){
    var s=D.getElementById(id);if(!s||s.querySelector('.ef-tagw'))return;
    var host=s.querySelector('.sec-head')||s.querySelector('.faq > div');if(!host)return;
    host.insertAdjacentHTML('afterbegin',tag(TAGS[id]))});
  var th=$('.hm-th');if(th&&!th.querySelector('.ef-tagw'))th.insertAdjacentHTML('afterbegin',tag('Расписание эфира'));
  var sb=$('.sub .wrap > div');if(sb&&!sb.querySelector('.ef-tagw'))sb.insertAdjacentHTML('afterbegin',tag('Эфир в Telegram'));
  /* нейтральная подпись вместо «Линия с источником указана» */
  $$('.hm-proof li').forEach(function(li){if(/Линия с источником/.test(li.textContent))li.textContent='Линия обновляется дважды в день'});
  var nt=$('.hm-note');if(nt&&!/справка, не рекомендация/.test(nt.textContent))nt.textContent+=' Линия обновляется дважды в день; кэфы — справка, не рекомендация.';
  /* секции появляются по очереди */
  $$('.sec-head,.steps>li,.obj-grid details,.soon,.sub .wrap>*,.sub li,.faq details,.faq>div>h2').forEach(function(e,i){if(!e.closest('.hm'))e.classList.add('ef-rv')});
  $$('.steps>li,.obj-grid details,.sub li,.faq details').forEach(function(e){var i=Array.prototype.indexOf.call(e.parentNode.children,e);e.style.setProperty('--i',i)});
  reveal()}

/* ——— шапка: часы эфира ——— */
function header(){
  var lg=$('.hd .logo');if(!lg||$('.ef-air'))return;
  lg.insertAdjacentHTML('afterend','<span class="ef-air" aria-hidden="true">ЭФИР <em>МСК <i data-ef-clock style="font-style:normal">'+mskNow()+'</i></em></span>');
  setInterval(function(){var t=$('[data-ef-clock]');if(t)t.textContent=mskNow()},20000)}

/* ——— переход между страницами ——— */
function transitions(){
  D.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a');W.__efLink=a||null;
    try{if(a&&a.dataset.vd)sessionStorage.setItem('jv-efvt',JSON.stringify([a.dataset.vd,a.dataset.vb]));else sessionStorage.removeItem('jv-efvt')}catch(x){}},true);
  W.addEventListener('pageswap',function(e){
    if(!e.viewTransition)return;
    $$('[style*="view-transition-name"]').forEach(function(x){x.style.viewTransitionName=''});
    var a=W.__efLink;if(!a||!a.dataset.vd)return;
    var st=a.closest('.ef-stage')||a.parentNode,h=$('.ef-stage__em--h',st),b=$('.ef-stage__em--a',st);
    if(h)h.style.viewTransitionName='em-h';if(b)b.style.viewTransitionName='em-a'});
  W.addEventListener('pagereveal',function(e){
    if(!e.viewTransition)return;
    try{var c=JSON.parse(sessionStorage.getItem('jv-efvt')||'null');if(c){H.style.setProperty('--vd',c[0]);H.style.setProperty('--vb',c[1])}}catch(x){}
    H.classList.add('ef-vt');
    var off=function(){H.classList.remove('ef-vt')};e.viewTransition.finished.then(off,off)})}

/* ——— старт ——— */
function start(){
  H.classList.add('ef-js');
  var bg=D.createElement('div');bg.className='ef-bgw';bg.setAttribute('aria-hidden','true');bg.innerHTML='<i></i><i></i>';D.body.insertBefore(bg,D.body.firstChild);
  var vt=D.createElement('div');vt.className='ef-vtw';vt.setAttribute('aria-hidden','true');D.body.appendChild(vt);
  header();decorateText();buildStage();decorateRows();transitions();
  /* строки home.js могут перерисоваться */
  var list=$('.hm-list');if(list)new MutationObserver(function(){decorateRows()}).observe(list,{childList:true});
  tickCd();setInterval(tickCd,1000);
  W.JVEfir={cols:cols,cv:cv,emUrl:emUrl,scramble:scramble,reveal:reveal,setPageColors:setPageColors,tag:tag,pair:pair,mot:mot};
}
function boot(){
  var go=function(){if(D.body)start();else D.addEventListener('DOMContentLoaded',start)};
  if(W.CLUB_SET){C=W.CLUB_SET;go();return}
  var s=D.createElement('script');s.src=ROOT+'assets/club/themes.js';
  s.onload=function(){C=W.CLUB_SET||{};go()};s.onerror=function(){go()};D.head.appendChild(s)}
if(D.readyState==='loading')D.addEventListener('DOMContentLoaded',boot);else boot();
})();
