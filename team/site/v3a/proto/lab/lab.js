/* JARVIS · «Лаборатория»: доска Гальтона, размерные метки, цифры-«прибор». Без звуков. Один canvas на странице. */
(function(){
'use strict';
var D=document,W=window,RM=W.matchMedia&&W.matchMedia('(prefers-reduced-motion: reduce)').matches;
var TOUCH=W.matchMedia&&W.matchMedia('(hover:none)').matches;
var NS='http://www.w3.org/2000/svg';
var T=W.JV_TODAY||{matches:[],days:[]},M=W.JV_MODEL||{},L=W.JV_LINES||{},CS=W.CLUB_SET||{};
var G=W.gsap;
if(G){try{G.registerPlugin(W.ScrambleTextPlugin,W.DrawSVGPlugin)}catch(e){}}
var HAS_SCR=!!(G&&W.ScrambleTextPlugin),HAS_DRAW=!!(G&&W.DrawSVGPlugin);
function $(s,r){return (r||D).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||D).querySelectorAll(s))}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function pc(x){return Math.round(x*100)}
function od(x){return x==null?'—':String(x.toFixed(2)).replace('.',',')}
function tm(t){return t.slice(11,16)}
var MON=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
function dlabel(d){var p=d.split('-');return +p[2]+' '+MON[+p[1]-1]}
function club(id){var c=CS[id];return c?c.a1:'#6b7480'}
function emb(id,cls){return '<img src="../../assets/em/'+id+'.webp" alt="" width="40" height="40" loading="lazy" onerror="this.style.visibility=\'hidden\'"'+(cls?' class="'+cls+'"':'')+'>'}
function matches(){
  var out=[];
  (T.matches||[]).forEach(function(m){
    if(m.lg!=='khl'&&m.lg!=='nhl')return;
    var mo=M[m.key];if(!mo)return;
    out.push({m:m,mo:mo,ln:L[m.key]||null,p:[mo.p1,mo.x,mo.p2],id:m.key});
  });
  out.sort(function(a,b){return a.m.t<b.m.t?-1:a.m.t>b.m.t?1:0});
  return out;
}
var ALL=matches();
function find(key){for(var i=0;i<ALL.length;i++)if(ALL[i].id===key)return ALL[i]}
var DAY_KEY='khl|2026-11-05|avangard|cska';

/* ---------- ГЕНЕРАТОР СЛУЧАЙНЫХ ---------- */
function rng(seed){var a=seed>>>0;return function(){a=(a+0x6D2B79F5)>>>0;var t=a;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296}}
var BIN=[3.0,3.0,3.0];
/* ---------- ДОСКА ГАЛЬТОНА ---------- */
function Galton(cv,opt){
  this.cv=cv;this.ctx=cv.getContext('2d');this.o=opt||{};this.R=11;this.pk=[];this.go=false;this.vis=true;this.t0=0;this.pauseAt=0;this.raf=0;this.counts=[0,0,0];
  var self=this;
  if('IntersectionObserver' in W){new IntersectionObserver(function(es){self.vis=es[0].isIntersecting;if(self.vis)self.resume();},{threshold:0.01}).observe(cv)}
  D.addEventListener('visibilitychange',function(){if(!D.hidden)self.resume()});
  var rt;W.addEventListener('resize',function(){clearTimeout(rt);rt=setTimeout(function(){if(self.cv.isConnected&&self.W!==self.cv.parentElement.clientWidth-16){self.rebuild()}},150)});
}
Galton.prototype.layout=function(){
  var par=this.cv.parentElement,w=Math.max(220,par.clientWidth-16);
  this.W=w+16;this.cw=w;
  var dx=w/12;this.dx=dx;this.dy=dx*0.62;this.top=dx*0.9;
  this.r=Math.max(2.4,dx*0.115);
  this.pegBot=this.top+this.R*this.dy+dx*0.15;
  this.binH=dx*2.7;this.h=Math.round(this.pegBot+this.binH);
  var dpr=Math.min(W.devicePixelRatio||1,1.5);this.dpr=dpr;
  this.cv.width=Math.round(w*dpr);this.cv.height=Math.round(this.h*dpr);
  this.cv.style.width=w+'px';this.cv.style.height=this.h+'px';
};
Galton.prototype.rebuild=function(){
  if(!this.p)return;
  var done=!this.go;this.layout();this.plan(this.p,this.n,this.seed);
  if(done||RM){this.finish()}else{this.start(true)}
};
Galton.prototype.plan=function(p,n,seed){
  this.p=p;this.n=n;this.seed=seed;
  var rnd=rng(seed),R=this.R,dx=this.dx,r=this.r;
  var cum=[p[0]/(p[0]+p[1]+p[2]),(p[0]+p[1])/(p[0]+p[1]+p[2])];
  var wts=[];for(var k=0;k<4;k++){var c=1,kk=k;wts.push(null)}
  var binom=[1,11,55,165,330,462,462,330,165,55,11,1];
  var cols=Math.max(4,Math.floor((4*dx-4)/(2*r))),h=[[],[],[]];
  for(var b=0;b<3;b++){for(var c2=0;c2<cols;c2++)h[b].push(0)}
  var iv=this.o.interval||(n>200?15:28);this.iv=iv;this.STEP=this.o.step||82;this.FALL=240;
  this.total=this.STEP*R+this.FALL;
  var pk=[],cnt=[0,0,0];
  for(var i=0;i<n;i++){
    var u=rnd(),b2=u<cum[0]?0:u<cum[1]?1:2;
    var ws=0,j;for(j=0;j<4;j++)ws+=binom[b2*4+j];
    var v=rnd()*ws,s=0;for(j=0;j<4;j++){s+=binom[b2*4+j];if(v<=s)break}
    if(j>3)j=3;var kslot=b2*4+j;
    var path=[];for(var q=0;q<R;q++)path.push(q<kslot?1:0);
    for(var q2=R-1;q2>0;q2--){var z=Math.floor(rnd()*(q2+1)),tmp=path[q2];path[q2]=path[z];path[z]=tmp}
    var sx=(kslot+0.5)*dx,best=1e9,bc=0;
    for(var c3=0;c3<cols;c3++){
      var cx=b2*4*dx+2+r+c3*2*r+((4*dx-4)-cols*2*r)/2,sc=h[b2][c3]*1.5+Math.abs(cx-sx)/(2*r)*0.5+rnd()*0.6;
      if(sc<best){best=sc;bc=c3}
    }
    var fx=b2*4*dx+2+r+bc*2*r+((4*dx-4)-cols*2*r)/2,fy=this.h-2-r-h[b2][bc]*2*r*0.92;
    h[b2][bc]++;cnt[b2]++;
    pk.push({t:i*iv+rnd()*8,b:b2,path:path,fx:fx,fy:fy,done:false});
  }
  this.pk=pk;this.final=cnt;this.counts=[0,0,0];this.landed=0;
};
Galton.prototype.dev=function(p,seed,n){
  var rnd=rng(seed),c=[0,0,0],s=p[0]+p[1]+p[2];
  for(var i=0;i<n;i++){var u=rnd();c[u<p[0]/s?0:u<(p[0]+p[1])/s?1:2]++}
  var m=0;for(var k=0;k<3;k++)m=Math.max(m,Math.abs(c[k]/n-p[k]/s));return m;
};
/* первый розыгрыш — «стартовый»: подбираем зерно, чтобы выборка была близка к расчёту; повтор — любое зерно */
Galton.prototype.run=function(p,n,first){
  this.layout();
  var seed;
  if(first){var bs=1,bd=9;for(var s=1;s<160;s++){var d=this.dev(p,s*7919,n);if(d<bd){bd=d;bs=s*7919}}seed=bs}
  else seed=(Math.random()*4e9)|0;
  this.plan(p,n,seed);
  if(RM){this.finish();return}
  this.start();
};
Galton.prototype.start=function(keep){
  this.go=true;this.t0=performance.now()-(keep?(this.keepT||0):0);
  if(!keep){this.counts=[0,0,0];this.landed=0}
  this.tick();
};
Galton.prototype.resume=function(){
  if(!this.go||this.raf)return;if(!this.vis||D.hidden)return;
  this.t0+=performance.now()-this.pauseAt;this.tick();
};
Galton.prototype.tick=function(){
  var self=this;
  this.raf=requestAnimationFrame(function(now){
    self.raf=0;
    if(!self.vis||D.hidden){self.pauseAt=now;return}
    self.frame(now-self.t0);
    if(self.go)self.tick();
  });
};
Galton.prototype.finish=function(){
  this.go=false;var pk=this.pk;for(var i=0;i<pk.length;i++)pk[i].done=true;
  this.counts=this.final.slice();this.landed=pk.length;this.draw(1e9);this.emit(true);
};
Galton.prototype.emit=function(done){if(this.o.onUpdate)this.o.onUpdate(this.counts,this.n,done)};
Galton.prototype.frame=function(el){
  this.keepT=el;var pk=this.pk,ch=false;
  for(var i=0;i<pk.length;i++){var q=pk[i];if(!q.done&&el-q.t>=this.total){q.done=true;this.counts[q.b]++;this.landed++;ch=true}}
  this.draw(el);
  if(ch)this.emit(this.landed>=pk.length);
  if(this.landed>=pk.length){this.go=false}
};
var PC=['#ffb15e','#aab3be','#7ec3ff'];
Galton.prototype.draw=function(el){
  var c=this.ctx,dx=this.dx,dy=this.dy,r=this.r,R=this.R,w=this.cw,h=this.h;
  c.setTransform(this.dpr,0,0,this.dpr,0,0);c.clearRect(0,0,w,h);
  /* лотки */
  c.strokeStyle='#3b434d';c.lineWidth=1;c.beginPath();
  for(var k=0;k<=3;k++){var x=Math.min(w-0.5,Math.max(0.5,k*4*dx));c.moveTo(x,this.pegBot);c.lineTo(x,h)}
  c.moveTo(0,h-0.5);c.lineTo(w,h-0.5);c.stroke();
  /* шкала лотков */
  c.fillStyle='#3b434d';for(var t=1;t<10;t++){var yy=h-t*(this.binH/10);c.fillRect(0,yy,t%5?3:6,1);c.fillRect(w-(t%5?3:6),yy,t%5?3:6,1)}
  /* колышки */
  c.fillStyle='#667280';c.beginPath();
  var pr=Math.max(1.4,dx*0.04);
  for(var i=0;i<R;i++)for(var a=0;a<=i;a++){var px=w/2+(a-i/2)*dx,py=this.top+i*dy;c.moveTo(px+pr,py);c.arc(px,py,pr,0,6.2832)}
  c.fill();
  /* входное отверстие */
  c.fillStyle='#9ba6b2';c.beginPath();c.moveTo(w/2-5,0);c.lineTo(w/2+5,0);c.lineTo(w/2,6);c.fill();
  /* шайбы */
  var pk=this.pk;
  for(var b=0;b<3;b++){
    c.fillStyle=PC[b];c.beginPath();
    for(var j=0;j<pk.length;j++){
      var q=pk[j];if(q.b!==b)continue;
      var e=el-q.t;if(e<0)continue;
      var X,Y;
      if(q.done){X=q.fx;Y=q.fy}
      else if(e>=this.STEP*R){
        var u=Math.min(1,(e-this.STEP*R)/this.FALL),sx=this.sxy(q,R);
        X=sx[0]+(q.fx-sx[0])*u;Y=sx[1]+(q.fy-sx[1])*u*u;
      }else{
        var s=Math.floor(e/this.STEP),u2=(e-s*this.STEP)/this.STEP,a1=this.sxy(q,s),a2=this.sxy(q,s+1);
        X=a1[0]+(a2[0]-a1[0])*(1-(1-u2)*(1-u2));
        Y=a1[1]+(a2[1]-a1[1])*(0.3*u2+0.7*u2*u2)-Math.sin(u2*3.1416)*dy*0.14*(s>0?1:0);
      }
      c.moveTo(X+r,Y);c.arc(X,Y,r,0,6.2832);
    }
    c.fill();
  }
};
Galton.prototype.sxy=function(q,j){
  var rs=0;for(var i=0;i<j;i++)rs+=q.path[i];
  return [this.cw/2+(rs-j/2)*this.dx,this.top+(j-0.5)*this.dy];
};

/* ---------- ИНДИКАТОРЫ ПОД ДОСКОЙ ---------- */
function bindBoard(root,galton,item){
  var cells=$$('.bins .cell',root);
  function upd(c,n,done){
    for(var i=0;i<3;i++){
      var span=$('.cnt',cells[i]);if(span)span.textContent=c[i];
      var pe=$('.smp',cells[i]);if(pe)pe.textContent=n?Math.round(c[i]/Math.max(1,c[0]+c[1]+c[2])*100)+' %':'—';
    }
    var s=$('.sum',root);if(s)s.textContent=(c[0]+c[1]+c[2]);
  }
  return upd;
}

/* ---------- РАЗМЕРНЫЕ МЕТКИ (наведение / нажатие) ---------- */
function mk(n,a){var e=D.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);return e}
function dims(el){
  var w=Math.round(el.offsetWidth),h=Math.round(el.offsetHeight),p=16;
  var s=el._dims;
  if(!s){s=el._dims=mk('svg',{'class':'dims','aria-hidden':'true'});el.appendChild(s)}
  s.setAttribute('width',w+p*2);s.setAttribute('height',h+p*2);s.setAttribute('viewBox','0 0 '+(w+p*2)+' '+(h+p*2));
  while(s.firstChild)s.removeChild(s.firstChild);
  var y=7,x=7,L1=p,R1=w+p,T1=p,B1=h+p;
  var ps=[
   'M'+L1+' '+y+'H'+R1,'M'+L1+' '+(y-4)+'V'+(y+4),'M'+R1+' '+(y-4)+'V'+(y+4),
   'M'+x+' '+T1+'V'+B1,'M'+(x-4)+' '+T1+'H'+(x+4),'M'+(x-4)+' '+B1+'H'+(x+4),
   'M'+L1+' '+(T1+9)+'V'+T1+'H'+(L1+9),'M'+(R1-9)+' '+T1+'H'+R1+'V'+(T1+9),'M'+L1+' '+(B1-9)+'V'+B1+'H'+(L1+9),'M'+(R1-9)+' '+B1+'H'+R1+'V'+(B1-9)
  ];
  ps.forEach(function(d){s.appendChild(mk('path',{d:d}))});
  var t1=mk('text',{x:(L1+R1)/2,y:y+3.5});t1.textContent='W '+w;s.appendChild(t1);
  var t2=mk('text',{x:x-3.5,y:(T1+B1)/2,transform:'rotate(-90 '+(x-3.5)+' '+(T1+B1)/2+')'});t2.textContent='H '+h;s.appendChild(t2);
  return s;
}
function dimsOn(el){
  if(RM)return;
  var s=dims(el);
  if(HAS_DRAW){G.killTweensOf(s);G.set(s,{opacity:1});G.fromTo($$('path',s),{drawSVG:'0%'},{drawSVG:'100%',duration:.25,ease:'power2.out',overwrite:true})}
  else s.style.opacity=1;
}
function dimsOff(el){
  var s=el._dims;if(!s)return;
  if(G)G.to(s,{opacity:0,duration:.15,overwrite:true});else s.style.opacity=0;
}
function scramble(el){
  if(RM||!HAS_SCR)return;
  $$('[data-scr]',el).forEach(function(n){
    var f=n.getAttribute('data-scr');
    G.to(n,{duration:.4,scrambleText:{text:f,chars:'0123456789',speed:.7},overwrite:true});
  });
}
function hoverUnit(el){
  var on=false;
  el.addEventListener('pointerenter',function(e){
    if(e.pointerType==='touch')return;
    on=true;dimsOn(el);scramble(el);
  });
  el.addEventListener('pointerleave',function(){if(on){on=false;dimsOff(el)}});
  el.addEventListener('pointerdown',function(e){if(e.pointerType==='touch'){dimsOn(el);scramble(el);setTimeout(function(){dimsOff(el)},900)}});
}

/* ---------- КАРТОЧКА МАТЧА ---------- */
var CH=0;
function card(it,opt){
  opt=opt||{};var m=it.m,p=it.p,ln=it.ln,mx=p[0]>=p[1]&&p[0]>=p[2]?0:p[2]>=p[1]?2:1;
  var s=p[0]+p[1]+p[2],a=document.createElement('article');
  a.className='unit card';a.setAttribute('data-key',it.id);a.tabIndex=0;
  a.style.setProperty('--club',club(m.h));
  var odds=[ln&&ln.p1,ln&&ln.x,ln&&ln.p2],lab=['П1','Х','П2'];
  var cells='';for(var i=0;i<3;i++){
    cells+='<div class="cell c'+(i+1)+(i===mx?' top':'')+'"><small>'+lab[i]+'</small><b class="tn"><span data-scr="'+pc(p[i])+'">'+pc(p[i])+'</span><u>%</u></b><em>кэф '+od(odds[i])+'</em></div>';
  }
  CH++;var id=String(CH).padStart(2,'0');
  a.innerHTML='<i class="scr a"></i><i class="scr b"></i>'+
   '<div class="plate"><span>CH-'+id+'</span><span><b>'+(m.lg==='khl'?'КХЛ':'НХЛ')+'</b> · '+tm(m.t)+' МСК</span></div>'+
   '<div class="teams"><div class="tm">'+emb(m.h)+'<b>'+esc(m.hn)+'</b></div><i>—</i><div class="tm r">'+emb(m.a)+'<b>'+esc(m.an)+'</b></div></div>'+
   '<div class="read">'+cells+'</div>'+
   '<div class="gauge" aria-hidden="true"><i style="flex:'+(p[0]/s*100).toFixed(1)+'"></i><i style="flex:'+(p[1]/s*100).toFixed(1)+'"></i><i style="flex:'+(p[2]/s*100).toFixed(1)+'"></i></div>'+
   '<div class="act"><span class="t">тотал '+String(it.mo.tot).replace('.',',')+': больше '+pc(it.mo.over)+' %</span>'+(opt.mini?'<button type="button" class="tgl" aria-expanded="false">Розыгрыш</button>':'<a href="match.html">Матч →</a>')+'</div>'+
   (opt.mini?'<div class="mini well"><div class="host"></div><div class="meta"><span><b class="cnt">0</b>П1</span><span><b class="cnt">0</b>Х</span><span><b class="cnt">0</b>П2</span></div><div class="act" style="padding:10px 0 0"><span class="t">выборка из <span class="nn">150</span> шайб</span><a href="match.html">Матч →</a></div></div>':'');
  hoverUnit(a);
  return a;
}
/* кнопка «в текст»: неразрывный % */

/* ---------- ПОЯВЛЕНИЕ ПРИ ПРОКРУТКЕ ---------- */
function reveal(){
  var els=$$('.rv');
  if(RM||!('IntersectionObserver' in W)){els.forEach(function(e){e.classList.add('in')});return}
  var io=new IntersectionObserver(function(es){es.forEach(function(x){if(x.isIntersecting){x.target.classList.add('in');io.unobserve(x.target)}})},{rootMargin:'0px 0px -6% 0px',threshold:.05});
  els.forEach(function(e,i){io.observe(e)});
}
function stagger(sel,step){
  $$(sel).forEach(function(e,i){e.style.transitionDelay=(i*(step||60))+'ms'});
}

/* ---------- ЛИНЕЙКА СЛЕВА ---------- */
function ruler(){
  var r=$('.ruler i');if(!r)return;var tk=0;
  function up(){tk=0;var h=D.documentElement,max=h.scrollHeight-W.innerHeight,y=W.scrollY||0,v=max>0?y/max:0;
    r.style.transform='translateY('+(v*(W.innerHeight-20)+10).toFixed(1)+'px)';r.textContent=String(Math.round(y/10)).padStart(3,'0')}
  W.addEventListener('scroll',function(){if(!tk)tk=requestAnimationFrame(up)},{passive:true});up();
}

/* ---------- ТАЙМЕР ---------- */
function countdown(el,t){
  var to=Date.parse(t.replace(' ','T')+':00+03:00');
  var cs=$$('b',el),lab=$('.tlab',el);
  function up(){
    var d=to-Date.now();
    if(d<=0){cs.forEach(function(b){b.textContent='00'});if(lab)lab.textContent=d>-3*3600e3?'матч идёт или только начался':'матч сыгран';return}
    var h=Math.floor(d/3600e3),mi=Math.floor(d%3600e3/60e3),s=Math.floor(d%60e3/1e3);
    cs[0].textContent=String(h).padStart(2,'0');cs[1].textContent=String(mi).padStart(2,'0');cs[2].textContent=String(s).padStart(2,'0');
  }
  up();setInterval(up,1000);
}

/* ---------- ГЛАВНОЕ ТАБЛО (главная и матч) ---------- */
function mainBoard(){
  var root=$('#board');if(!root)return null;
  var it=find(root.getAttribute('data-key')||DAY_KEY);if(!it)return null;
  var cv=$('canvas',root),n=W.innerWidth<640?150:300;
  var nn=$('.nn',root);if(nn)nn.textContent=n;
  var g=new Galton(cv,{onUpdate:function(c,total,done){
    var cells=$$('.bins .cell',root),tot=c[0]+c[1]+c[2];
    for(var i=0;i<3;i++){
      $('.cnt',cells[i]).textContent=c[i];
      $('.smp',cells[i]).textContent=tot?Math.round(c[i]/tot*100)+' %':'0 %';
    }
    var s=$('.sum',root);if(s)s.textContent=tot;
    root.classList.toggle('done',done);
  }});
  var first=true;
  function go(){g.run(it.p,n,first);first=false}
  /* запуск, когда прибор виден */
  if('IntersectionObserver' in W&&!RM){
    var io=new IntersectionObserver(function(es){if(es[0].isIntersecting){io.disconnect();go()}},{threshold:.2});io.observe(cv);
  }else go();
  var btn=$('#replay',root);
  if(btn)btn.addEventListener('click',function(){go()});
  return g;
}

/* ---------- ГЛАВНАЯ ---------- */
function pageHome(){
  mainBoard();
  var box=$('#cards-home');
  if(box){
    var day=T.days&&T.days[0],list=ALL.filter(function(x){return x.m.t.slice(0,10)===day}).filter(function(x){return x.m.lg==='khl'});
    var more=ALL.filter(function(x){return x.m.t.slice(0,10)===day&&x.m.lg==='nhl'}).slice(0,3);
    list=list.concat(more).slice(0,6);
    box.innerHTML='';list.forEach(function(it){var c=card(it);c.classList.add('rv');box.appendChild(c);
      c.addEventListener('click',function(e){if(!e.target.closest('a'))location.href='match.html'});
      c.addEventListener('keydown',function(e){if(e.key==='Enter')location.href='match.html'});
    });
    stagger('#cards-home .card',70);
  }
}

/* ---------- ХОККЕЙ ---------- */
function pageHockey(){
  /* бегущая строка */
  var tk=$('#ticker .tr');
  if(tk&&ALL.length){
    var day=T.days&&T.days[0],list=ALL.filter(function(x){return x.m.t.slice(0,10)===day});
    var h='';list.forEach(function(x){h+='<span>'+(x.m.lg==='khl'?'КХЛ':'НХЛ')+' · '+tm(x.m.t)+' · '+esc(x.m.hn)+' <b>'+pc(x.p[0])+'</b> / '+pc(x.p[1])+' / <u>'+pc(x.p[2])+'</u> '+esc(x.m.an)+'</span>'});
    tk.innerHTML=h+h;
  }
  /* матч дня */
  var md=find(DAY_KEY);
  if(md){var mdt=$('#mday-time');if(mdt)countdown(mdt,md.m.t);}
  var khl=ALL.filter(function(x){return x.m.lg==='khl'}).length,nhl=ALL.length-khl;
  var st=$('#st-all');if(st)st.textContent=ALL.length;
  var sl=$('#st-line');if(sl)sl.textContent=ALL.filter(function(x){return x.ln}).length;
  /* список дня */
  var box=$('#cards-hockey'),tabs=$('#daytabs'),shared=null,openCard=null,sg=null;
  function sharedBoard(){
    if(shared)return shared;
    var cv=D.createElement('canvas');cv.setAttribute('role','img');cv.setAttribute('aria-label','Мини-доска розыгрыша: 150 шайб по долям модели');
    shared=new Galton(cv,{interval:30,step:70,onUpdate:function(c){
      if(!openCard)return;var sp=$$('.meta .cnt',openCard);for(var i=0;i<3;i++)sp[i].textContent=c[i];
    }});
    return shared;
  }
  function closeMini(c){c.classList.remove('open');var b=$('.tgl',c);if(b)b.setAttribute('aria-expanded','false')}
  function toggle(c,it){
    if(c.classList.contains('open')){closeMini(c);openCard=null;return}
    if(openCard)closeMini(openCard);
    openCard=c;c.classList.add('open');$('.tgl',c).setAttribute('aria-expanded','true');
    var host=$('.host',c),g=sharedBoard();
    host.appendChild(g.cv);$('.nn',c).textContent=150;
    var sp=$$('.meta .cnt',c);sp.forEach(function(s){s.textContent=0});
    g.run(it.p,150,true);
    dimsOn(c);
  }
  function render(day){
    if(!box)return;box.innerHTML='';openCard=null;
    var list=ALL.filter(function(x){return x.m.t.slice(0,10)===day});
    list.forEach(function(it){
      var c=card(it,{mini:true});c.classList.add('rv');box.appendChild(c);
      c.addEventListener('click',function(e){if(e.target.closest('a'))return;toggle(c,it)});
      c.addEventListener('keydown',function(e){if(e.key==='Enter'&&e.target===c)toggle(c,it)});
    });
    stagger('#cards-hockey .card',50);
    $$('#cards-hockey .rv').forEach(function(e){requestAnimationFrame(function(){e.classList.add('in')})});
  }
  if(tabs&&T.days){
    T.days.forEach(function(d,i){
      var b=D.createElement('button');b.type='button';b.setAttribute('role','tab');b.setAttribute('aria-selected',i?'false':'true');b.textContent=dlabel(d)+(i===0?' · сегодня':'');
      b.addEventListener('click',function(){$$('button',tabs).forEach(function(x){x.setAttribute('aria-selected','false')});b.setAttribute('aria-selected','true');render(d)});
      tabs.appendChild(b);
    });
    render(T.days[0]);
  }
  /* клубы */
  ['khl','nhl'].forEach(function(lg){
    var host=$('#lgs-'+lg);if(!host)return;var seen={},h='';
    ALL.forEach(function(x){if(x.m.lg!==lg)return;[[x.m.h,x.m.hn],[x.m.a,x.m.an]].forEach(function(t){if(seen[t[0]])return;seen[t[0]]=1;
      h+='<a href="#" style="--club:'+club(t[0])+'" aria-label="'+esc(t[1])+'">'+emb(t[0])+'<span>'+esc(t[1])+'</span></a>'});});
    host.innerHTML=h;$$('a',host).forEach(function(a){a.addEventListener('click',function(e){e.preventDefault()});hoverUnit(a)});
  });
  /* таблица прогноза */
  var tb=$('#ptable tbody');
  if(tb){
    var h2='';ALL.forEach(function(x){
      var s=x.p[0]+x.p[1]+x.p[2],ticks='';
      if(x.ln&&x.ln.p1&&x.ln.x&&x.ln.p2){var q=[1/x.ln.p1,1/x.ln.x,1/x.ln.p2],qs=q[0]+q[1]+q[2];ticks='<s style="left:'+(q[0]/qs*100).toFixed(1)+'%"></s><s style="left:'+((q[0]+q[1])/qs*100).toFixed(1)+'%"></s>'}
      h2+='<tr><td class="n">'+x.m.t.slice(5,10).split('-').reverse().join('.')+' '+tm(x.m.t)+'</td><td>'+esc(x.m.hn)+' — '+esc(x.m.an)+'</td><td class="hide-s"><div class="pbar" role="img" aria-label="П1 '+pc(x.p[0])+' %, Х '+pc(x.p[1])+' %, П2 '+pc(x.p[2])+' %"><i style="flex:'+(x.p[0]/s*100)+'"></i><i style="flex:'+(x.p[1]/s*100)+'"></i><i style="flex:'+(x.p[2]/s*100)+'"></i>'+ticks+'</div></td><td class="n">'+pc(x.p[0])+' / '+pc(x.p[1])+' / '+pc(x.p[2])+'</td><td class="n hide-s">'+pc(x.mo.over)+' %</td></tr>';
    });
    tb.innerHTML=h2;
  }
  /* листы таблицы */
  var sb=$('#sheet-body'),stabs=$('#sheet-tabs');
  if(sb&&stabs){
    var SH={
     'Эло':['Рейтинг Эло','Сила каждой команды одним числом. Рейтинг пересчитывается после каждого матча: победа над сильным соперником стоит больше, чем над слабым.',['Все команды лиги в одном списке','Как менялась сила команды за сезон','Поправка на игру: броски в створ и шайбы сверх ожидания']],
     'Прогнозы':['Прогнозы на все матчи','Все матчи ближайших дней на одном листе: время по Москве, прогноз модели, коэффициенты и вероятность. После игры рядом появляется счёт.',['КХЛ и НХЛ','Расчёт модели рядом с линией','Обновляется каждое утро']],
     'Что заходит':['Что заходит у команд','Как часто у каждой команды случается то или иное событие за сезон: победа, тотал больше или меньше, игра в овертайм.',['Видно сильные и слабые стороны каждой команды','Конструктор матча: выбираешь две команды и видишь, что вероятнее в их игре']],
     'Расписание':['Расписание и результаты','Все матчи сезона с датой и временем по Москве. У сыгранных стоит счёт, отмечены овертаймы и буллиты.',['Сегодня, завтра и вся неделя','Ночные матчи НХЛ собраны в один игровой день']],
     'История':['История ставок','Каждый прогноз остаётся в таблице: зашёл или нет и по какому кэфу. Видно, как часто модель угадывает и как менялся банк на дистанции.',['Точность модели по фаворитам и аутсайдерам','Ничего не удаляется']]
    };
    Object.keys(SH).forEach(function(k,i){
      var b=D.createElement('button');b.type='button';b.setAttribute('role','tab');b.setAttribute('aria-selected',i?'false':'true');b.textContent=k;
      b.addEventListener('click',function(){$$('button',stabs).forEach(function(x){x.setAttribute('aria-selected','false')});b.setAttribute('aria-selected','true');show(k)});
      stabs.appendChild(b);
    });
    function show(k){var s=SH[k];sb.innerHTML='<h3>'+s[0]+'</h3><p>'+s[1]+'</p><ul>'+s[2].map(function(x){return '<li>'+x+'</li>'}).join('')+'</ul>';
      if(G&&!RM)G.fromTo(sb,{opacity:0,y:8},{opacity:1,y:0,duration:.3,ease:'power2.out'})}
    show('Эло');
  }
}

/* ---------- МАТЧ ---------- */
function pageMatch(){
  var g=mainBoard();
  var it=find(DAY_KEY);if(!it)return;
  var mo=it.mo,lam=mo.lam||[2.3,2.4];
  /* стрелки-циферблаты ожидаемых голов */
  $$('.dial').forEach(function(d,i){
    var v=lam[i],ar=$('.arc',d),nd=$('.needle',d);
    var fr=Math.min(1,v/5);
    var ang=fr*Math.PI,ex=100-80*Math.cos(ang),ey=100-80*Math.sin(ang);
    if(ar)ar.setAttribute('d','M20 100A80 80 0 0 1 '+ex.toFixed(2)+' '+ey.toFixed(2));
    var tg=$('.ticks',d);if(tg&&!tg.firstChild){var th='';for(var q=0;q<=10;q++){var aa=q/10*Math.PI,c=Math.cos(aa),s2=Math.sin(aa),r1=q%2?86:90;th+='<path d="M'+(100-r1*c).toFixed(1)+' '+(100-r1*s2).toFixed(1)+'L'+(100-96*c).toFixed(1)+' '+(100-96*s2).toFixed(1)+'"/>';if(q%2==0)th+='<text x="'+(100-107*c).toFixed(1)+'" y="'+(103-107*s2).toFixed(1)+'">'+(q/2)+'</text>'}tg.innerHTML=th}
    if(nd&&!RM&&G){G.fromTo(nd,{rotation:-90},{rotation:-90+fr*180,duration:1.2,ease:'power3.out',svgOrigin:'100 100',paused:true,id:'n'+i});}
    d._go=function(){
      if(RM||!G){if(nd)nd.setAttribute('transform','rotate('+(-90+fr*180)+' 100 100)');return}
      var tw=G.getById('n'+i);tw&&tw.play();
      if(HAS_DRAW&&ar){G.fromTo(ar,{drawSVG:'0%'},{drawSVG:(fr*100)+'%',duration:1.2,ease:'power3.out'})}
      var out=$('b',d),o={v:0};
      G.to(o,{v:v,duration:1.2,ease:'power3.out',onUpdate:function(){out.textContent=o.v.toFixed(1).replace('.',',')}});
    };
  });
  var dl=$('.xg');
  if(dl){
    var shown=false;
    var run=function(){if(shown)return;shown=true;$$('.dial').forEach(function(d){d._go()})};
    if('IntersectionObserver' in W&&!RM){var io=new IntersectionObserver(function(es){if(es[0].isIntersecting){io.disconnect();run()}},{threshold:.3});io.observe(dl)}else run();
  }
  /* гистограмма тотала: распределение Пуассона по сумме ожидаемых голов; доля «больше» — из модели */
  var hs=$('#hist');
  if(hs){
    var lt=lam[0]+lam[1],ps=[],e0=Math.exp(-lt),pk=e0;
    for(var k=0;k<=11;k++){ps.push(pk);pk=pk*lt/(k+1)}
    var mx=Math.max.apply(null,ps),W0=560,H0=190,bw=W0/12,thr=mo.tot,h='';
    ps.forEach(function(v,k){
      var hh=Math.round(v/mx*(H0-40)),over=k>thr;
      h+='<g class="col" style="transition-delay:'+(k*35)+'ms"><rect class="'+(over?'bar-o':'bar-u')+'" x="'+(k*bw+5)+'" y="'+(H0-18-hh)+'" width="'+(bw-10)+'" height="'+hh+'"/></g><text x="'+(k*bw+bw/2)+'" y="'+(H0-3)+'" text-anchor="middle">'+k+'</text>';
    });
    var tx=(Math.floor(thr)+1)*bw;
    h+='<line class="thr" x1="'+tx+'" x2="'+tx+'" y1="6" y2="'+(H0-18)+'"/><text x="'+(tx+6)+'" y="16">порог '+String(thr).replace('.',',')+'</text>';
    hs.setAttribute('viewBox','0 0 '+W0+' '+H0);hs.innerHTML=h;
  }
}

/* ---------- ОБЩЕЕ ---------- */
function init(){
  D.documentElement.classList.add('js');
  var pg=D.body.getAttribute('data-page');
  ruler();
  $$('.hov').forEach(hoverUnit);
  if(pg==='home')pageHome();else if(pg==='hockey')pageHockey();else if(pg==='match')pageMatch();
  reveal();W.__labOK=1;
  /* лёгкий «въезд» героя */
  if(G&&!RM){
    var hh=$$('.hero [data-in]');
    if(hh.length)G.from(hh,{opacity:0,y:16,duration:.7,stagger:.08,ease:'power3.out',delay:.05,clearProps:'all'});
  }
}
if(D.readyState==='loading')D.addEventListener('DOMContentLoaded',init);else init();
})();
