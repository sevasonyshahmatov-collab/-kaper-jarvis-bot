/* JARVIS · «Эфир»: данные, рендер, анимации. Без внешних библиотек. */
(function(){
'use strict';
var D=document,W=window;
var J=W.JV_TODAY||{matches:[],days:[]},M=W.JV_MODEL||{},L=W.JV_LINES||{},C=W.CLUB_SET||{};
var RM=W.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
var FEAT='khl|2026-11-05|avangard|cska';
var LGN={khl:'КХЛ',nhl:'НХЛ',epl:'АПЛ',laliga:'Ла Лига',seriea:'Серия А',bundesliga:'Бундеслига',ligue1:'Лига 1',ucl:'Лига чемпионов',uel:'Лига Европы',rpl:'РПЛ'};
var MON=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
var WD=['воскресенье','понедельник','вторник','среда','четверг','пятница','суббота'];
function $(s,r){return (r||D).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||D).querySelectorAll(s))}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function isH(m){return m.lg==='khl'||m.lg==='nhl'}
function pct(v){return Math.round(v*100)}
function kef(n){return n==null?'—':Number(n).toFixed(2).replace('.',',')}
function num1(n){return String(n).replace('.',',')}
function ep(m){var p=m.t.split(/[- :]/).map(Number);return Date.UTC(p[0],p[1]-1,p[2],p[3]-3,p[4])}
function hhmm(m){return m.t.slice(11,16)}
function dlabel(m){var p=m.t.slice(0,10).split('-').map(Number);return p[2]+' '+MON[p[1]-1]}
function wday(m){var p=m.t.slice(0,10).split('-').map(Number);return WD[new Date(Date.UTC(p[0],p[1]-1,p[2])).getUTCDay()]}
function byKey(k){for(var i=0;i<J.matches.length;i++)if(J.matches[i].key===k)return J.matches[i]}
function emUrl(m,s){var id=m[s];return '../../assets/'+(isH(m)?'em':'fc')+'/'+id+'.webp'}
function emImg(m,s,cls,vt){return '<img class="'+(cls||'em')+'" data-s="'+s+'" src="'+emUrl(m,s)+'" alt="" loading="lazy" decoding="async" onerror="this.outerHTML=\'<span class=&quot;em em--i&quot;>'+esc((m[s==='h'?'hn':'an']||'').slice(0,2).toUpperCase())+'</span>\'">'}

/* ——— цвета клубов ——— */
function h2r(h){h=h.replace('#','');return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)]}
function r2hsl(c){var r=c[0]/255,g=c[1]/255,b=c[2]/255,mx=Math.max(r,g,b),mn=Math.min(r,g,b),l=(mx+mn)/2,h=0,s=0,d=mx-mn;if(d){s=l>.5?d/(2-mx-mn):d/(mx+mn);h=mx===r?(g-b)/d+(g<b?6:0):mx===g?(b-r)/d+2:(r-g)/d+4;h*=60}return [h,s,l]}
function hsl(h,s,l){return 'hsl('+Math.round(h)+' '+Math.round(s*100)+'% '+Math.round(l*100)+'%)'}
function dist(a,b){var x=h2r(a),y=h2r(b);return Math.hypot(x[0]-y[0],x[1]-y[1],x[2]-y[2])}
function hash(s){var h=0;for(var i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))>>>0;return h}
function lift(hex){var q=r2hsl(h2r(hex));return hsl(q[0],Math.max(q[1],.6),.56)}
function pair(m,s,other){
  var id=m[s],c=C[id];
  if(isH(m)&&c){var d=c.dk,b=c.a1;
    if(other&&C[other]&&dist(b,C[other].a1)<150&&s==='a'){b=lift(c.dk)}
    return [d,b]}
  var h=hash(id)%360; if(s==='a'&&Math.abs(h-hash(m.h)%360)<70)h=(h+140)%360;
  return [hsl(h,.5,.15),hsl(h,.68,.48)]}
function cols(m){var a=pair(m,'h'),b=pair(m,'a',m.h);return {hd:a[0],hb:a[1],ad:b[0],ab:b[1]}}
function cv(c){return '--hd:'+c.hd+';--hb:'+c.hb+';--ad:'+c.ad+';--ab:'+c.ab}
function mot(id){var c=C[id];return c&&c.m?'url("'+new URL('../../assets/club/m/'+c.m[0]+'.svg',D.baseURI).href+'")':'none'}
function setPageColors(m){var c=cols(m),r=D.documentElement.style;r.setProperty('--hd',c.hd);r.setProperty('--hb',c.hb);r.setProperty('--ad',c.ad);r.setProperty('--ab',c.ab)}

/* ——— время ——— */
function mskNow(){return new Date().toLocaleTimeString('ru-RU',{timeZone:'Europe/Moscow',hour:'2-digit',minute:'2-digit'})}
function p2(n){return (n<10?'0':'')+n}
function cd(m){var s=Math.floor((ep(m)-Date.now())/1000);
  if(s<=0)return s>-10800?'идёт':'старт был '+hhmm(m);
  var d=Math.floor(s/86400),h=Math.floor(s%86400/3600),mi=Math.floor(s%3600/60),se=s%60;
  return (d?d+' д ':'')+p2(h)+':'+p2(mi)+':'+p2(se)}
function tickCd(){$$('[data-cd]').forEach(function(e){var m=byKey(e.dataset.cd);if(m)e.textContent=cd(m)})}

/* ——— цифры: «пересчёт» ——— */
function scramble(el,final,dur,delay){
  final=String(final);if(RM||!el){if(el)el.textContent=final;return}
  var t0=null,n=final.length;el.textContent=final.replace(/\d/g,'0');
  setTimeout(function(){requestAnimationFrame(function f(t){if(t0===null)t0=t;var k=Math.min(1,(t-t0)/dur),lock=Math.floor(k*k*(3-2*k)*n),o='';
    for(var i=0;i<n;i++){var ch=final[i];o+=/\d/.test(ch)&&i>=lock?Math.floor(Math.random()*10):ch}
    el.textContent=k>=1?final:o;if(k<1)requestAnimationFrame(f)})},delay||0)}
function runNums(root){$$('[data-num]',root).forEach(function(e,i){scramble(e,e.dataset.num,900,i*250)})}

/* ——— разметка матча ——— */
function pr(k){var m=M[k];return m?{a:pct(m.p1),x:pct(m.x),b:pct(m.p2),mx:m.p1>=m.x&&m.p1>=m.p2?0:m.p2>=m.x?2:1}:null}
function rowHTML(m,i){
  var c=cols(m),p=pr(m.key),l=L[m.key]||{},mx=p?p.mx:-1;
  var n=p?'<div class="n"><span class="'+(mx===0?'mx':'')+'"><small>П1</small><b>'+p.a+'</b></span><span class="'+(mx===1?'mx':'')+'"><small>Х</small><b>'+p.x+'</b></span><span class="'+(mx===2?'mx':'')+'"><small>П2</small><b>'+p.b+'</b></span></div><div class="seg"><i class="'+(mx===0?'mx':'')+'" style="flex:'+p.a+'"></i><i class="'+(mx===1?'mx':'')+'" style="flex:'+p.x+'"></i><i class="'+(mx===2?'mx':'')+'" style="flex:'+p.b+'"></i></div>':'<small>пример данных</small>';
  return '<a class="row vt-link" href="match.html?k='+encodeURIComponent(m.key)+'" style="--i:'+i+';'+cv(c)+'" data-vd="'+c.hd+'" data-vb="'+c.hb+'"><i class="w w--h"></i><i class="w w--a"></i>'+
  '<span class="row__t"><b>'+hhmm(m)+'</b><small>'+esc(LGN[m.lg]||m.lg)+'</small></span>'+
  '<span class="row__tm row__tm--h">'+emImg(m,'h')+'<b>'+esc(m.hn)+'</b></span>'+
  '<span class="row__m">'+n+'</span>'+
  '<span class="row__tm row__tm--a">'+emImg(m,'a')+'<b>'+esc(m.an)+'</b></span>'+
  '<span class="row__o"><span><small>П1</small><b>'+kef(l.p1)+'</b></span><span><small>Х</small><b>'+kef(l.x)+'</b></span><span><small>П2</small><b>'+kef(l.p2)+'</b></span></span></a>'}
function bugInner(m){
  var p=pr(m.key),l=L[m.key],o=M[m.key];
  return '<span class="bug__top"><b>'+esc(LGN[m.lg]||m.lg)+'</b><span>'+dlabel(m)+', '+hhmm(m)+' МСК</span></span>'+
  '<span class="bug__names"><span>'+esc(m.hn)+'</span><em>VS</em><span>'+esc(m.an)+'</span></span>'+
  '<span class="bug__clock"><small>До матча</small><b data-cd="'+m.key+'">'+cd(m)+'</b></span>'+
  (p?'<span class="bug__p"><div class="'+(p.mx===0?'mx':'')+'"><small>П1</small><b>'+p.a+' %</b></div><div class="'+(p.mx===1?'mx':'')+'"><small>Х</small><b>'+p.x+' %</b></div><div class="'+(p.mx===2?'mx':'')+'"><small>П2</small><b>'+p.b+' %</b></div></span>':'')+
  (o&&o.tot?'<span class="bug__tot"><span>Тотал '+num1(o.tot)+': <b>больше '+pct(o.over)+' %</b></span><b>Расчёт модели</b></span>':'')}
function stageHTML(m,opt){
  opt=opt||{};var c=cols(m);
  return '<div class="stage'+(opt.lg?' stage--lg':'')+'" style="'+cv(c)+'"><div class="wedge wedge--h" style="--mot:'+mot(m.h)+'"></div><div class="wedge wedge--a" style="--mot:'+mot(m.a)+'"></div>'+
  emImg(m,'h','stage__em stage__em--h')+emImg(m,'a','stage__em stage__em--a')+
  '<b class="stage__nm stage__nm--h">'+esc(m.hn)+'</b><b class="stage__nm stage__nm--a">'+esc(m.an)+'</b>'+
  '<a class="bug glass gl vt-link" href="match.html?k='+encodeURIComponent(m.key)+'" data-vd="'+c.hd+'" data-vb="'+c.hb+'" aria-label="Расчёт модели: '+esc(m.hn)+' — '+esc(m.an)+'">'+bugInner(m)+'</a></div>'}

/* ——— появление ——— */
var io=null;
function observe(){
  var els=$$('.rv,.rows,.calc,[data-reveal]');
  if(!('IntersectionObserver' in W)||RM){els.forEach(function(e){e.classList.add('in');if(e.matches('.calc,[data-reveal]'))runNums(e)});return}
  io=new IntersectionObserver(function(en){en.forEach(function(x){if(x.isIntersecting){var e=x.target;e.classList.add('in');if(e.matches('.calc,[data-reveal]'))runNums(e);io.unobserve(e)}})},{threshold:.12,rootMargin:'0px 0px -6% 0px'});
  els.forEach(function(e){io.observe(e)})}
W.__jvReveal=function(root){observe()};

/* ——— общее ——— */
function common(){
  var t=$('[data-clock]');if(t){t.textContent=mskNow();setInterval(function(){t.textContent=mskNow()},20000)}
  tickCd();setInterval(tickCd,1000);
  var f=byKey(FEAT);if(f)setPageColors(f);
  /* клик: запоминаем цвет для клина перехода */
  D.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a');W.__lastLink=a||null;
    try{if(a&&a.dataset.vd)sessionStorage.setItem('jvvt',JSON.stringify([a.dataset.vd,a.dataset.vb]));else sessionStorage.removeItem('jvvt')}catch(x){}},true);
  /* лёгкий параллакс клиньев */
  var st=$('.stage:not(.stage--mini)');
  if(st&&!RM&&matchMedia('(hover:hover) and (pointer:fine)').matches){
    var wh=$('.wedge--h',st),wa=$('.wedge--a',st),tx=0,cx=0,run=false,vis=true;
    new IntersectionObserver(function(e){vis=e[0].isIntersecting}).observe(st);
    st.addEventListener('pointermove',function(e){var r=st.getBoundingClientRect();tx=((e.clientX-r.left)/r.width-.5)*2;if(!run){run=true;requestAnimationFrame(loop)}});
    st.addEventListener('pointerleave',function(){tx=0;if(!run){run=true;requestAnimationFrame(loop)}});
    var loop=function(){cx+=(tx-cx)*.08;var v=cx*14;wh.style.translate=(-v)+'px';wa.style.translate=(v)+'px';
      if(Math.abs(tx-cx)>.002&&vis&&!D.hidden)requestAnimationFrame(loop);else run=false}}
}
/* переход между страницами */
W.addEventListener('pageswap',function(e){
  if(!e.viewTransition)return;
  $$('[style*="view-transition-name"]').forEach(function(x){x.style.viewTransitionName=''});
  var a=W.__lastLink;if(!a||!a.classList.contains('vt-link'))return;
  var h=a.querySelector('[data-s="h"]'),b=a.querySelector('[data-s="a"]');
  if(!h&&a.classList.contains('bug')){var s=a.parentNode;h=$('.stage__em--h',s);b=$('.stage__em--a',s)}
  if(h)h.style.viewTransitionName='em-h';if(b)b.style.viewTransitionName='em-a'});
W.addEventListener('pagereveal',function(e){
  if(!e.viewTransition)return;
  try{var c=JSON.parse(sessionStorage.getItem('jvvt')||'null');if(c){D.documentElement.style.setProperty('--vd',c[0]);D.documentElement.style.setProperty('--vb',c[1])}}catch(x){}
  D.documentElement.classList.add('vt');
  e.viewTransition.finished.then(function(){D.documentElement.classList.remove('vt')},function(){D.documentElement.classList.remove('vt')})});

/* ——— главная ——— */
function home(){
  var f=byKey(FEAT),h=$('#hero-stage');if(h&&f)h.innerHTML=stageHTML(f,{lg:true});
  var box=$('#rows'),cur='all';
  function list(){
    var a=J.matches.slice().sort(function(x,y){return ep(x)-ep(y)});
    if(cur==='h')a=a.filter(isH);else if(cur==='f')a=a.filter(function(m){return !isH(m)});
    else a=a.filter(function(m){return isH(m)}).slice(0,6).concat(a.filter(function(m){return !isH(m)}).slice(0,2));
    a.sort(function(x,y){return ep(x)-ep(y)});
    return a.slice(0,cur==='all'?8:10)}
  function draw(){box.classList.remove('in');box.innerHTML=list().map(rowHTML).join('');
    if(io)io.observe(box);else box.classList.add('in');
    if(RM||!io)box.classList.add('in')}
  $$('.filters .chip').forEach(function(b){b.addEventListener('click',function(){cur=b.dataset.f;$$('.filters .chip').forEach(function(x){x.setAttribute('aria-pressed',x===b)});draw()})});
  if(location.hash==='#f'){cur='f';$$('.filters .chip').forEach(function(x){x.setAttribute('aria-pressed',x.dataset.f==='f')})}
  draw();
}

/* ——— хоккей ——— */
function hockey(){
  var hk=J.matches.filter(isH).sort(function(a,b){return ep(a)-ep(b)}),f=byKey(FEAT);
  var tk=$('.ticker__in');
  if(tk){var s=hk.map(function(m){var p=pr(m.key);return '<a href="match.html?k='+encodeURIComponent(m.key)+'" class="vt-link"><i>'+(LGN[m.lg])+'</i><b>'+hhmm(m)+'</b> '+esc(m.hn)+' — '+esc(m.an)+(p?' <em>'+p.a+' / '+p.x+' / '+p.b+'</em>':'')+'</a>'}).join('');tk.innerHTML=s+s}
  /* матч дня */
  var md=$('#mday');if(md&&f){var c=cols(f);md.setAttribute('style',cv(c));
    md.innerHTML='<div class="stage stage--mini"><div class="wedge wedge--h" style="--mot:'+mot(f.h)+'"></div><div class="wedge wedge--a" style="--mot:'+mot(f.a)+'"></div>'+emImg(f,'h','stage__em stage__em--h')+emImg(f,'a','stage__em stage__em--a')+'<span class="vs">VS</span></div>'+
    '<div class="mday__box"><span class="tag"><i></i>'+LGN[f.lg]+' · '+hhmm(f)+' МСК</span><div><b style="font:700 19px/1.2 var(--f-d)">Прогноз дня</b><div style="color:var(--mute);margin-top:4px">'+esc(f.hn)+' — '+esc(f.an)+'</div></div>'+
    '<div><small style="color:var(--mute)">До матча</small><div class="big" data-cd="'+f.key+'">'+cd(f)+'</div></div>'+
    '<p style="color:var(--mute);font-size:13.5px">Посты с прогнозами выходят в канале: КХЛ — до 08:00 МСК, НХЛ — до 14:00.</p>'+
    '<a class="btn btn-wrap vt-link" style="width:max-content" href="match.html?k='+encodeURIComponent(f.key)+'" data-vd="'+c.hd+'" data-vb="'+c.hb+'">Расчёт модели</a></div>'}
  var st=$('[data-stats]');if(st){var k=hk.length;st.querySelector('[data-num-a]').dataset.num=k;st.querySelector('[data-num-b]').dataset.num=hk.filter(function(m){return M[m.key]&&L[m.key]}).length}
  /* колода */
  var dk=$('#deck');
  if(dk){
    var day0=J.days[0],cur=0,flt='all',cards=[];
    function pool(){return hk.filter(function(m){return m.t.slice(0,10)===day0&&(flt==='all'||m.lg===flt)})}
    function build(){var a=pool();dk.querySelector('.deck__st').innerHTML=a.map(function(m){var c=cols(m);
      return '<a class="dcard vt-link" href="match.html?k='+encodeURIComponent(m.key)+'" data-vd="'+c.hd+'" data-vb="'+c.hb+'" style="'+cv(c)+'" tabindex="-1">'+
      '<div class="wedge wedge--h" style="--mot:'+mot(m.h)+'"></div><div class="wedge wedge--a" style="--mot:'+mot(m.a)+'"></div>'+emImg(m,'h','stage__em stage__em--h')+emImg(m,'a','stage__em stage__em--a')+
      '<b class="stage__nm stage__nm--h">'+esc(m.hn)+'</b><b class="stage__nm stage__nm--a">'+esc(m.an)+'</b><span class="bug glass gl">'+bugInner(m)+'</span></a>'}).join('');
      cards=$$('.dcard',dk);cur=0;pos()}
    function pos(){var n=cards.length;cards.forEach(function(c,i){var d=i-cur;c.dataset.p=d===0?'0':d===1?'1':d===2?'2':d<0?'-':'x';c.tabIndex=d===0?0:-1;c.setAttribute('aria-hidden',d!==0)});
      $('.deck__cnt',dk).textContent=p2(Math.min(cur+1,n))+' / '+p2(n)}
    function go(d){var n=cards.length;cur=Math.max(0,Math.min(n-1,cur+d));pos()}
    $('.dprev',dk).addEventListener('click',function(){go(-1)});$('.dnext',dk).addEventListener('click',function(){go(1)});
    dk.addEventListener('keydown',function(e){if(e.key==='ArrowRight'){go(1);e.preventDefault()}if(e.key==='ArrowLeft'){go(-1);e.preventDefault()}});
    var x0=null,moved=false;
    dk.addEventListener('pointerdown',function(e){x0=e.clientX;moved=false});
    dk.addEventListener('pointerup',function(e){if(x0===null)return;var dx=e.clientX-x0;x0=null;if(Math.abs(dx)>48){moved=true;go(dx<0?1:-1)}});
    dk.addEventListener('click',function(e){if(moved){e.preventDefault();moved=false}},true);
    var lastW=0;dk.addEventListener('wheel',function(e){if(Math.abs(e.deltaX)>Math.abs(e.deltaY)&&Date.now()-lastW>400){lastW=Date.now();go(e.deltaX>0?1:-1);e.preventDefault()}},{passive:false});
    $$('.chip[data-lg]').forEach(function(b){b.addEventListener('click',function(){flt=b.dataset.lg;$$('.chip[data-lg]').forEach(function(x){x.setAttribute('aria-pressed',x===b)});build()})});
    build();
    var rb=$('#today-rows');if(rb)rb.innerHTML=hk.filter(function(m){return m.t.slice(0,10)===day0}).map(rowHTML).join('')
  }
  /* клубы */
  var seen={};['khl','nhl'].forEach(function(lg){var box=$('#clubs-'+lg);if(!box)return;var h='';
    hk.forEach(function(m){if(m.lg!==lg)return;['h','a'].forEach(function(s){var id=m[s];if(seen[id])return;seen[id]=1;var p=pair(m,s),nm=m[s==='h'?'hn':'an'];
      h+='<div class="cl" title="'+esc(nm)+'" style="--hd:'+p[0]+';--hb:'+p[1]+'">'+emImg(m,s)+'<span>'+esc(nm)+'</span></div>'})});
    box.innerHTML=h;$$('.cl .em',box).forEach(function(i){i.className='';i.removeAttribute('data-s')})});
  /* лист таблицы */
  var sh=$('.sheet__r');if(sh){var sl=$$('.sheet__sl>*',sh),i=0,dots=$('.dots',sh);dots.innerHTML=sl.map(function(){return '<i></i>'}).join('');
    function show(n){i=(n+sl.length)%sl.length;sl.forEach(function(e,k){e.classList.toggle('on',k===i)});$$('i',dots).forEach(function(e,k){e.classList.toggle('on',k===i)});$('.cnt',sh).textContent=(i+1)+' / '+sl.length}
    $('.sprev',sh).addEventListener('click',function(){show(i-1)});$('.snext',sh).addEventListener('click',function(){show(i+1)});show(0)}
  /* прогноз модели */
  var mt=$('#mt');if(mt){mt.innerHTML=hk.map(function(m,k){var p=pr(m.key),l=L[m.key],c=cols(m);if(!p)return '';
    var v=[p.a,p.x,p.b][p.mx],nm=['П1 · победа '+m.hn,'Х · ничья в основное время','П2 · победа '+m.an][p.mx],o=l?[l.p1,l.x,l.p2][p.mx]:null,sh='';
    if(o&&l){var s=1/l.p1+1/l.x+1/l.p2;sh=Math.round(1/o/s*100)}
    return '<a class="mt__r rv vt-link" style="--i:'+(k%8)+';'+cv(c)+'" data-vd="'+c.hd+'" data-vb="'+c.hb+'" href="match.html?k='+encodeURIComponent(m.key)+'"><time>'+hhmm(m)+'<small>'+dlabel(m)+'</small></time><b>'+esc(m.hn)+' — '+esc(m.an)+'</b>'+
    '<span class="scale"><i style="width:'+Math.min(v,100)+'%"></i>'+(sh?'<s style="left:'+sh+'%" title="доля линии без маржи"></s>':'')+'</span>'+
    '<span class="lbl"><b>'+v+' %</b>'+(sh?'линия '+sh+' %':'без линии')+'</span></a>'}).join('')}
}

/* ——— матч ——— */
function match(){
  var q=new URLSearchParams(location.search).get('k')||FEAT,m=byKey(q)||byKey(FEAT),feat=m.key===FEAT;
  setPageColors(m);var c=cols(m);
  D.title=m.hn+' — '+m.an+': прогноз на матч '+dlabel(m)+', '+(LGN[m.lg]||'')+' | JARVIS';
  var hs=$('#m-stage');
  hs.innerHTML='<div class="stage stage--lg" style="'+cv(c)+'"><div class="wedge wedge--h" style="--mot:'+mot(m.h)+'"></div><div class="wedge wedge--a" style="--mot:'+mot(m.a)+'"></div>'+
   emImg(m,'h','stage__em stage__em--h')+emImg(m,'a','stage__em stage__em--a')+'<b class="stage__nm stage__nm--h">'+esc(m.hn)+'</b><b class="stage__nm stage__nm--a">'+esc(m.an)+'</b>'+
   '<div class="bug glass gl" style="padding:0"><span class="bug__top"><b>'+esc(LGN[m.lg]||m.lg)+'</b><span>'+dlabel(m)+', '+hhmm(m)+' МСК</span></span><span class="bug__names"><span>'+esc(m.hn)+'</span><em>VS</em><span>'+esc(m.an)+'</span></span><span class="bug__clock"><small>До матча</small><b data-cd="'+m.key+'">'+cd(m)+'</b></span></div></div>';
  $$('.stage__em',hs).forEach(function(e){e.style.viewTransitionName=e.dataset.s==='h'?'em-h':'em-a'});
  $('#m-h1').textContent=m.hn+' — '+m.an;$('#m-sub').textContent='прогноз на матч '+dlabel(m);
  $('#m-bc').textContent=m.hn+' — '+m.an;
  var ar=m.arena;$('#m-when').innerHTML=dlabel(m)+', '+wday(m)+'<span>'+hhmm(m)+' МСК</span>';
  $('#m-lg').textContent=LGN[m.lg]||m.lg;
  $('#m-arena').innerHTML=ar&&ar.name?esc(ar.name)+', '+esc(ar.city||'')+(ar.capacity?'<span>вместимость '+String(ar.capacity).replace(/(\d)(?=(\d{3})$)/,'$1 ')+'</span>':''):(typeof ar==='string'?esc(ar):'—');
  $('#m-upd').textContent='Данные обновлены '+J.built.slice(8,10)+'.'+J.built.slice(5,7)+' в '+J.built.slice(11,16)+' МСК.';
  /* модель */
  var o=M[m.key],l=L[m.key];
  if(o){var p=pr(m.key),mxs=[p.a,p.x,p.b];
    var cl=[[c.hd,c.hb],['#262c3d','#8d97b0'],[c.ad,c.ab]];
    $('#m-cols').innerHTML=[['П1','победа хозяев',p.a],['Х','ничья в основное время',p.x],['П2','победа гостей',p.b]].map(function(r,i){
      return '<div class="col '+(i===1?'col--x':'')+'" style="--k:'+i+'"><span class="col__n"><span data-num="'+r[2]+'">'+r[2]+'</span><sup>%</sup></span><div class="col__bar"><i style="--v:'+r[2]+'%;--cd:'+cl[i][0]+';--cb:'+cl[i][1]+';transition-delay:'+(i*.28)+'s"></i></div><b class="nm">'+r[0]+'</b><small>'+r[1]+'</small></div>'}).join('');
    $('#m-tot').innerHTML=(o.tot?'<div class="tot__p"><small>Тотал '+num1(o.tot)+'</small><b>больше <span data-num="'+pct(o.over)+'">'+pct(o.over)+'</span> %</b></div>':'')+
     (o.lam?'<div class="xg"><small style="color:var(--mute)">Ожидаемые голы</small><div class="xg__r"><span>'+esc(m.hn)+'</span><i style="--c:'+c.hb+';--v:'+(o.lam[0]/Math.max(o.lam[0],o.lam[1]))+'"></i><b>'+num1(o.lam[0])+'</b></div><div class="xg__r"><span>'+esc(m.an)+'</span><i style="--c:'+c.ab+';--v:'+(o.lam[1]/Math.max(o.lam[0],o.lam[1]))+'"></i><b>'+num1(o.lam[1])+'</b></div></div>':'');
  }
  /* кэфы */
  if(l){var s=1/l.p1+1/l.x+1/l.p2,t=l.over&&l.under?1/l.over+1/l.under:0;
    var od=[['П1',l.p1,pct(1/l.p1/s),o&&pct(o.p1)],['Х',l.x,pct(1/l.x/s),o&&pct(o.x)],['П2',l.p2,pct(1/l.p2/s),o&&pct(o.p2)]];
    if(l.over)od.push(['Тотал '+num1(l.tot)+': больше',l.over,pct(1/l.over/t),o&&pct(o.over)]);
    if(l.under)od.push(['меньше',l.under,pct(1/l.under/t),o&&pct(1-o.over)]);
    $('#m-odds').innerHTML=od.map(function(r,i){return '<button type="button" class="odd" aria-pressed="false"><small>'+r[0]+'</small><b>'+kef(r[1])+'</b><span class="imp">Линия: '+r[2]+' %'+(r[3]!=null?' · модель: '+r[3]+' %':'')+'</span></button>'}).join('');
    $$('.odd').forEach(function(b){b.addEventListener('click',function(){b.setAttribute('aria-pressed',b.getAttribute('aria-pressed')!=='true')})})}
  /* только для матча дня: форма, очные, таблица */
  if(!feat){$$('[data-feat]').forEach(function(e){e.hidden=true});var n=$('#m-note');n.hidden=false}
  /* другие матчи */
  var ot=J.matches.filter(function(x){return x.lg===m.lg&&x.key!==m.key&&x.t.slice(0,10)===m.t.slice(0,10)});
  $('#m-other').innerHTML=ot.map(rowHTML).join('');
  $('#m-other-h').textContent='Другие матчи '+(LGN[m.lg]||'')+' в этот день';
}

D.addEventListener('DOMContentLoaded',function(){
  var pg=D.body.dataset.page;
  if(pg==='home')home();if(pg==='hockey')hockey();if(pg==='match')match();
  common();observe();
  $$('[data-reveal],.calc').forEach(function(e){});
});
})();
