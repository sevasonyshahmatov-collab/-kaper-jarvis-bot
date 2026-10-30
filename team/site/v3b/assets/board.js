/* JARVIS v3b — «Тактическая доска».
   Меловая схема на canvas: линии поля/катка прорисовываются сами, фишки ходят по схемам атак, стрелки передач,
   пометки тренера. Схема меняется под раздел (section[data-play]). prefers-reduced-motion — статичный рисунок. */
(()=>{
'use strict';
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const TAU=Math.PI*2;
const clamp=(v,a=0,b=1)=>Math.min(b,Math.max(a,v));
const eio=t=>t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;
const eout=t=>1-Math.pow(1-t,3);
const arc=(cx,cy,r,a0,a1)=>{const n=Math.max(10,Math.ceil(Math.abs(a1-a0)*r*1.6)),p=[];for(let i=0;i<=n;i++){const a=a0+(a1-a0)*i/n;p.push([cx+r*Math.cos(a),cy+r*Math.sin(a)])}return p};
const box=(x0,y0,x1,y1)=>[[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]];

/* ── разметка ─────────────────────────────────────────── */
const GEO={
 football(){const W=105,H=68,c=H/2,L=[];
  L.push({p:box(0,0,W,H)},{p:[[W/2,0],[W/2,H]]},{p:arc(W/2,c,9.15,-Math.PI/2,1.5*Math.PI)},{dot:[W/2,c]});
  const a=Math.acos(5.5/9.15);
  [[0,1],[W,-1]].forEach(([x,d])=>{
   L.push({p:[[x,c-20.16],[x+d*16.5,c-20.16],[x+d*16.5,c+20.16],[x,c+20.16]]});
   L.push({p:[[x,c-9.16],[x+d*5.5,c-9.16],[x+d*5.5,c+9.16],[x,c+9.16]]});
   L.push({dot:[x+d*11,c]});
   L.push({p:d>0?arc(11,c,9.15,-a,a):arc(W-11,c,9.15,Math.PI-a,Math.PI+a)});
   L.push({p:[[x,c-3.66],[x-d*1.6,c-3.66],[x-d*1.6,c+3.66],[x,c+3.66]]});
  });
  L.push({p:arc(0,0,1.2,0,Math.PI/2)},{p:arc(W,0,1.2,Math.PI/2,Math.PI)},{p:arc(W,H,1.2,Math.PI,1.5*Math.PI)},{p:arc(0,H,1.2,1.5*Math.PI,TAU)});
  return {W,H,L,goal:[[W,c],[0,c]]}},
 hockey(){const W=61,H=26,R=8.5,c=H/2,L=[];
  const rim=[...arc(R,R,R,Math.PI,1.5*Math.PI),...arc(W-R,R,R,1.5*Math.PI,TAU),...arc(W-R,H-R,R,0,Math.PI/2),...arc(R,H-R,R,Math.PI/2,Math.PI)];rim.push(rim[0]);
  L.push({p:rim},{p:[[W/2,0],[W/2,H]],c:'red'},{p:[[17.7,0],[17.7,H]],c:'blue'},{p:[[W-17.7,0],[W-17.7,H]],c:'blue'});
  L.push({p:[[4,1.3],[4,H-1.3]],c:'red'},{p:[[W-4,1.3],[W-4,H-1.3]],c:'red'});
  L.push({p:arc(W/2,c,4.57,-Math.PI/2,1.5*Math.PI),c:'blue'},{dot:[W/2,c],c:'blue'});
  [10,W-10].forEach(x=>[c-6.7,c+6.7].forEach(y=>{L.push({p:arc(x,y,4.57,-Math.PI/2,1.5*Math.PI),c:'red'},{dot:[x,y],c:'red'})}));
  [19.6,W-19.6].forEach(x=>[c-6.7,c+6.7].forEach(y=>L.push({dot:[x,y],c:'red'})));
  L.push({p:arc(4,c,1.83,-Math.PI/2,Math.PI/2),c:'red'},{p:arc(W-4,c,1.83,Math.PI/2,1.5*Math.PI),c:'red'});
  L.push({p:[[4,c-.92],[3,c-.92],[3,c+.92],[4,c+.92]]},{p:[[W-4,c-.92],[W-3,c-.92],[W-3,c+.92],[W-4,c+.92]]});
  return {W,H,L,goal:[[W-4,c],[4,c]]}}
};

/* ── класс доски ─────────────────────────────────────── */
class Board{
 constructor(cv,o){this.cv=cv;this.g=cv.getContext('2d');this.o=Object.assign({pad:.06,alpha:1,sport:'football'},o);
  this.geo=GEO[this.o.sport]();this.plays=o.plays;this.cur=null;this.prev=null;this.t0=performance.now();this.tl=0;this.on=true;
  this.seed=7;this.font=false;this.resize();
  if(document.fonts&&document.fonts.load)document.fonts.load('700 28px Caveat').then(()=>{this.font=true;this.kick()}).catch(()=>{});
  (this.o.box?new ResizeObserver(()=>{this.resize();this.kick()}).observe(cv):addEventListener('resize',()=>{clearTimeout(this.rt);this.rt=setTimeout(()=>{this.resize();this.kick()},120)}));
  if(this.o.box){new IntersectionObserver(e=>{this.on=e[0].isIntersecting;this.kick()}).observe(cv)}
  document.addEventListener('visibilitychange',()=>this.kick());
  this.set(this.o.start||Object.keys(this.plays)[0]);
 }
 rnd(){this.seed=(this.seed*16807)%2147483647;return this.seed/2147483647}
 colors(){const s=getComputedStyle(this.cv);const v=n=>s.getPropertyValue(n).trim();
  this.C={chalk:v('--chalk')||'#eef0e6',mark:v('--mark')||'#f3d061',red:v('--rink-red')||'#e2726e',blue:v('--rink-blue')||'#7fb0e6',opp:v('--red')||'#ff8a73'}}
 resize(){const r=this.o.box?this.cv.getBoundingClientRect():{width:innerWidth,height:innerHeight};
  const d=Math.min(2,devicePixelRatio||1);this.w=r.width;this.h=r.height;this.cv.width=Math.round(r.width*d);this.cv.height=Math.round(r.height*d);this.g.setTransform(d,0,0,d,0,0);
  const G=this.geo,top=this.o.top||0,ah=this.h-top;this.rot=ah>this.w*1.05;const GW=this.rot?G.H:G.W,GH=this.rot?G.W:G.H,pad=this.o.pad;
  this.s=Math.min(this.w*(1-2*pad)/GW,ah*(1-2*pad)/GH);
  this.ox=(this.w-GW*this.s)/2+(this.o.shift&&!this.rot?this.o.shift*this.w:0);this.oy=top+(ah-GH*this.s)/2;
  this.colors();this.seed=11;
  // линии разметки: дробим на шаги ~9 px, дрожание мела — один раз на размер
  this.lines=G.L.map((l,i)=>{if(l.dot)return {dot:this.P(...l.dot),c:l.c,i};const pts=[];
   for(let k=0;k<l.p.length-1;k++){const a=this.P(...l.p[k]),b=this.P(...l.p[k+1]),n=Math.max(1,Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/9));
    for(let j=0;j<n;j++){const t=j/n;pts.push([a[0]+(b[0]-a[0])*t+(this.rnd()-.5)*.9,a[1]+(b[1]-a[1])*t+(this.rnd()-.5)*.9])}}
   pts.push(this.P(...l.p[l.p.length-1]));return this.measure({pts,c:l.c,i})});
 }
 measure(o){const c=[0];for(let i=1;i<o.pts.length;i++)c.push(c[i-1]+Math.hypot(o.pts[i][0]-o.pts[i-1][0],o.pts[i][1]-o.pts[i-1][1]));o.cum=c;o.len=c[c.length-1];return o}
 P(x,y){return this.rot?[this.ox+(this.geo.H-y)*this.s,this.oy+x*this.s]:[this.ox+x*this.s,this.oy+y*this.s]}
 set(id){if(!this.plays[id]||(this.cur&&this.cur.id===id))return;
  if(this.cur){this.prev=this.cur;this.prev.out=performance.now()}
  this.cur={id,pl:this.plays[id],t0:performance.now()};this.kick();if(this.o.onPlay)this.o.onPlay(this.plays[id])}
 kick(){if(RM){this.draw(performance.now(),true);return}
  if(!this.raf&&this.on&&!document.hidden){const f=now=>{this.raf=0;if(!this.on||document.hidden)return;this.draw(now,false);this.raf=requestAnimationFrame(f)};this.raf=requestAnimationFrame(f)}}
 stroke(pts,cum,len,p){if(p<=0||pts.length<2)return;const g=this.g,lim=len*p;g.beginPath();g.moveTo(pts[0][0],pts[0][1]);
  for(let i=1;i<pts.length;i++){if(cum[i]<=lim)g.lineTo(pts[i][0],pts[i][1]);else{const t=(lim-cum[i-1])/((cum[i]-cum[i-1])||1);g.lineTo(pts[i-1][0]+(pts[i][0]-pts[i-1][0])*t,pts[i-1][1]+(pts[i][1]-pts[i-1][1])*t);break}}
  g.stroke()}
 chalk(fn,col,w,a){const g=this.g;g.strokeStyle=col;g.lineCap='round';g.lineJoin='round';
  g.globalAlpha=a;g.lineWidth=w;fn();g.globalAlpha=a*.35;g.lineWidth=w*2.2;g.save();g.translate(.6,.5);fn();g.restore();g.globalAlpha=1}
 draw(now,still){const g=this.g,C=this.C,base=this.o.alpha;g.clearRect(0,0,this.w,this.h);
  const T=(now-this.t0)/1000,lw=Math.max(1.4,Math.min(2.2,this.s*.17));
  // 1. разметка рисуется сама
  this.lines.forEach((l,k)=>{const p=still?1:eout(clamp((T-.15-k*.09)/1.1));if(p<=0)return;const col=l.c==='red'?C.red:l.c==='blue'?C.blue:C.chalk;
   if(l.dot){g.globalAlpha=.42*base*p;g.fillStyle=col;g.beginPath();g.arc(l.dot[0],l.dot[1],Math.max(2,this.s*.28),0,TAU);g.fill();g.globalAlpha=1;return}
   this.chalk(()=>this.stroke(l.pts,l.cum,l.len,p),col,lw,.36*base)});
  const intro=still?1:clamp((T-1.2)/.6);
  if(this.prev){const k=still?0:1-clamp((now-this.prev.out)/450);if(k>0)this.layer(this.prev,now,k*intro,still,true);else this.prev=null}
  if(this.cur)this.layer(this.cur,now,intro*(still?1:clamp((now-this.cur.t0)/500)),still,false);
 }
 layer(st,now,a,still,leaving){if(a<=0)return;const g=this.g,C=this.C,pl=st.pl,base=this.o.alpha;
  const t=still?0:(now-st.t0)/1000,D=pl.dur||6.5,cyc=2*D+1.4,tc=still?0:t%cyc;
  // зона раздела — штриховка мелом
  if(pl.zone){const [x0,y0,x1,y1]=pl.zone,a0=this.P(x0,y0),a1=this.P(x1,y1),L=Math.min(a0[0],a1[0]),Tp=Math.min(a0[1],a1[1]),Wd=Math.abs(a1[0]-a0[0]),Ht=Math.abs(a1[1]-a0[1]);
   const pr=still?1:eout(clamp(t/1.2));g.save();g.beginPath();g.rect(L,Tp,Wd*pr,Ht);g.clip();g.strokeStyle=C.chalk;g.globalAlpha=.085*a*base;g.lineWidth=1.2;g.beginPath();
   for(let x=L-Ht;x<L+Wd;x+=10){g.moveTo(x,Tp+Ht);g.lineTo(x+Ht,Tp)}g.stroke();g.restore();g.globalAlpha=1}
  // фишки: позиция по ключевым точкам «туда-обратно»
  const u=still?0:Math.max(0,tc-.4)/D,ping=u<1?u:u<2?2-u:0,q=eio(clamp(ping));
  const pos=k=>{if(k.length===1)return k[0];const s=q*(k.length-1),i=Math.min(k.length-2,Math.floor(s)),f=s-i;return [k[i][0]+(k[i+1][0]-k[i][0])*f,k[i][1]+(k[i+1][1]-k[i][1])*f]};
  // стрелки передач и рывков
  (pl.arrows||[]).forEach((ar,i)=>{const d=ar.d!=null?ar.d:.5+i*.55,p=still?1:eout(clamp((tc-d)/.75));const fade=still?1:1-clamp((tc-(cyc-.8))/.6);if(p<=0||fade<=0)return;
   const A=this.P(...ar.f),B=this.P(...ar.t),mx=(A[0]+B[0])/2,my=(A[1]+B[1])/2,dx=B[0]-A[0],dy=B[1]-A[1],len=Math.hypot(dx,dy)||1,bend=(ar.c||0)*this.s;
   const cx=mx-dy/len*bend,cy=my+dx/len*bend,pts=[];for(let j=0;j<=28;j++){const s=j/28,z=1-s;pts.push([z*z*A[0]+2*z*s*cx+s*s*B[0],z*z*A[1]+2*z*s*cy+s*s*B[1]])}
   const o=this.measure({pts}),col=ar.s==='shot'?C.mark:C.chalk,al=(ar.s==='shot'?.95:.7)*a*fade*base;
   g.setLineDash(ar.s==='run'?[5,7]:[]);this.chalk(()=>this.stroke(o.pts,o.cum,o.len,p),col,ar.s==='shot'?2.4:1.8,al);g.setLineDash([]);
   if(p>.97){const e=pts[28],b=pts[25],an=Math.atan2(e[1]-b[1],e[0]-b[0]),h=Math.max(7,this.s*.9);g.strokeStyle=col;g.globalAlpha=al;g.lineWidth=2;g.beginPath();
    g.moveTo(e[0]-h*Math.cos(an-.45),e[1]-h*Math.sin(an-.45));g.lineTo(e[0],e[1]);g.lineTo(e[0]-h*Math.cos(an+.45),e[1]-h*Math.sin(an+.45));g.stroke();g.globalAlpha=1}});
  const r=Math.max(6.5,Math.min(12,this.s*.95));
  (pl.us||[]).forEach((k,i)=>{const [x,y]=this.P(...pos(k));g.globalAlpha=.92*a*base;g.fillStyle=C.mark;g.beginPath();g.arc(x,y,r,0,TAU);g.fill();
   if(r>8&&!this.o.box){g.fillStyle=getComputedStyle(this.cv).getPropertyValue('--mark-ink')||'#111';g.font=`800 ${Math.round(r*1.05)}px "Sofia Sans",sans-serif`;g.textAlign='center';g.textBaseline='middle';g.fillText(String(i+(pl.n0||2)),x,y+.5)}g.globalAlpha=1});
  (pl.them||[]).forEach(k=>{const [x,y]=this.P(...pos(k)),h=r*.72;g.strokeStyle=C.chalk;g.globalAlpha=.7*a*base;g.lineWidth=2.4;g.lineCap='round';g.beginPath();g.moveTo(x-h,y-h);g.lineTo(x+h,y+h);g.moveTo(x+h,y-h);g.lineTo(x-h,y+h);g.stroke();g.globalAlpha=1});
  if(pl.ball){const [x,y]=this.P(...pos(pl.ball));g.globalAlpha=a*base;g.fillStyle=this.o.sport==='hockey'?'#05080d':'#ffffff';g.strokeStyle=C.chalk;g.lineWidth=1.5;g.beginPath();g.arc(x,y,Math.max(3.2,r*.42),0,TAU);g.fill();g.stroke();g.globalAlpha=1}
  // пометки тренера
  if(this.font&&!this.o.box)(pl.notes||[]).forEach((n,i)=>{const d=n.d!=null?n.d:1.4+i*.6,p=still?1:eout(clamp((tc-d)/.9)),fade=still?1:1-clamp((tc-(cyc-.8))/.6);if(p<=0||fade<=0)return;
   const [x,y]=this.P(...n.at),fs=Math.round(Math.max(18,Math.min(32,this.s*2.3)));g.font=`700 ${fs}px Caveat,cursive`;g.textBaseline='alphabetic';g.textAlign='left';
   const w=g.measureText(n.txt).width;const X=Math.min(Math.max(8,x),this.w-w-8);g.save();g.beginPath();g.rect(X-4,y-fs,(w+10)*p,fs*1.5);g.clip();
   g.globalAlpha=.95*a*fade*base;g.fillStyle=n.c==='chalk'?C.chalk:C.mark;g.fillText(n.txt,X,y);g.strokeStyle=g.fillStyle;g.lineWidth=1.6;g.beginPath();g.moveTo(X,y+6);g.quadraticCurveTo(X+w*.5,y+9,X+w,y+5);g.stroke();g.restore();g.globalAlpha=1});
 }
}

/* ── схемы: координаты в метрах поля (105×68) и катка (61×26) ── */
const F={
 build:{name:'Схема: розыгрыш от обороны',dur:6,n0:2,
  us:[[[12,14],[22,10],[30,8]],[[12,54],[24,58],[34,60]],[[20,30],[30,26],[40,28]],[[34,22],[46,18],[56,16]],[[34,46],[46,50],[58,52]],[[46,34],[58,30],[66,34]]],
  them:[[[60,20],[54,22]],[[60,48],[54,46]],[[70,34],[64,34]],[[78,24],[72,26]]],
  ball:[[20,30],[30,26],[46,18],[58,30]],
  arrows:[{f:[20,30],t:[46,18],c:-3},{f:[46,18],t:[66,34],c:4},{f:[34,46],t:[58,52],s:'run'}],
  notes:[{at:[60,12],txt:'тотал 2,5 — 62 %'}]},
 wing:{name:'Схема: атака флангом',dur:6.5,zone:[70,0,105,22],
  us:[[[58,8],[78,6],[92,10]],[[52,22],[66,18],[84,22]],[[60,36],[74,32],[90,30]],[[50,50],[64,44],[80,40]],[[40,30],[52,30],[64,32]]],
  them:[[[84,16],[90,16]],[[88,28],[94,30]],[[86,40],[92,38]],[[76,26],[82,26]]],
  ball:[[52,22],[78,6],[92,10],[90,30]],
  arrows:[{f:[52,22],t:[80,6],c:-2},{f:[80,6],t:[94,12],s:'run',c:-1},{f:[94,12],t:[90,30],c:3},{f:[90,30],t:[105,34],s:'shot',d:2.4}],
  notes:[{at:[66,62],txt:'6 матчей сегодня',c:'chalk'}]},
 press:{name:'Схема: высокий прессинг',dur:5.5,zone:[70,10,105,58],
  us:[[[66,20],[80,24]],[[66,48],[80,44]],[[62,34],[78,34]],[[56,14],[70,16]],[[56,54],[70,52]],[[50,34],[64,30]]],
  them:[[[92,22],[90,24]],[[92,46],[90,44]],[[98,34],[97,34]],[[84,34],[86,30]]],
  ball:[[98,34],[92,22],[84,34]],
  arrows:[{f:[66,20],t:[88,26],s:'run'},{f:[66,48],t:[88,42],s:'run'},{f:[62,34],t:[82,34],s:'run'}],
  notes:[{at:[58,8],txt:'7 турниров — одна модель'}]},
 shape:{name:'Схема: 4-3-3 против 4-4-2',dur:7,
  us:[[[20,10],[24,12]],[[18,26],[22,26]],[[18,42],[22,42]],[[20,58],[24,56]],[[36,20],[40,22]],[[34,34],[38,34]],[[36,48],[40,46]],[[50,12],[56,14]],[[52,34],[58,34]],[[50,56],[56,54]]],
  them:[[[86,12],[82,12]],[[86,26],[82,26]],[[86,42],[82,42]],[[86,56],[82,56]],[[72,12],[68,14]],[[72,28],[68,28]],[[72,40],[68,40]],[[72,56],[68,54]],[[62,28],[60,28]],[[62,40],[60,40]]],
  arrows:[{f:[52,34],t:[60,34],s:'run',d:1}],
  notes:[{at:[6,64],txt:'1. Ман Сити   2. Реал   3. Бавария',c:'chalk'}]},
 xg:{name:'Схема: удары и ожидаемые голы',dur:6,zone:[88.5,13.84,105,54.16],
  us:[[[80,30],[88,32]],[[84,46],[92,42]],[[74,20],[86,18]],[[70,38],[80,36]]],
  them:[[[96,28],[98,30]],[[96,40],[98,38]],[[103,34],[103,34]]],
  ball:[[70,38],[84,46],[92,42]],
  arrows:[{f:[70,38],t:[84,46],c:2},{f:[88,32],t:[105,32],s:'shot',d:1.6},{f:[92,42],t:[105,36],s:'shot',d:2.2}],
  notes:[{at:[56,10],txt:'10 000 розыгрышей'},{at:[56,62],txt:'порог 60 %',c:'chalk',d:2.4}]},
 counter:{name:'Схема: контратака',dur:5,
  us:[[[30,40],[56,34],[86,30]],[[26,20],[52,16],[82,18]],[[24,56],[50,54],[80,46]]],
  them:[[[60,44],[50,42]],[[62,24],[54,26]],[[72,34],[66,34]]],
  ball:[[30,40],[56,34],[82,18],[86,30]],
  arrows:[{f:[30,40],t:[56,34],s:'run'},{f:[56,34],t:[82,18],c:-3},{f:[82,18],t:[105,32],s:'shot',d:2}],
  notes:[{at:[8,10],txt:'обещано 62,5 → зашло 60,9 %'}]},
 corner:{name:'Схема: угловой',dur:5,zone:[88.5,13.84,105,54.16],
  us:[[[105,0],[105,0]],[[84,30],[96,32]],[[82,40],[94,38]],[[86,24],[98,28]],[[80,48],[92,44]]],
  them:[[[100,30],[100,30]],[[100,38],[100,38]],[[96,34],[97,34]],[[103,34],[103,34]]],
  ball:[[105,0],[96,32]],
  arrows:[{f:[105,0],t:[96,32],c:5},{f:[96,32],t:[105,34],s:'shot',d:1.8}],
  notes:[{at:[50,12],txt:'@jarvibet'}]}
};
const H={
 breakout:{name:'Схема: выход из зоны',dur:6,n0:2,
  us:[[[8,7],[16,5],[26,6]],[[8,19],[14,21],[22,20]],[[14,13],[24,13],[34,12]],[[22,4],[32,5],[42,6]],[[22,22],[32,21],[44,20]]],
  them:[[[26,10],[22,11]],[[26,17],[22,16]],[[34,13],[30,13]]],
  ball:[[8,7],[14,13],[22,4],[42,6]],
  arrows:[{f:[8,7],t:[14,13],c:-1},{f:[14,13],t:[22,4],c:1},{f:[22,4],t:[42,6],s:'run'},{f:[22,22],t:[44,20],s:'run'}],
  notes:[{at:[34,-1.4],txt:'58 % — победа Локомотива'}]},
 cycle:{name:'Схема: игра в зоне',dur:6.5,zone:[43.3,0,61,26],
  us:[[[56,6],[57,13],[56,20]],[[50,4],[46,8],[50,12]],[[46,22],[50,18],[46,14]],[[45,13],[44,6],[45,20]],[[52,14],[54,12],[52,16]]],
  them:[[[54,10],[55,13]],[[54,16],[55,14]],[[48,10],[48,12]],[[48,16],[48,14]]],
  ball:[[56,6],[57,13],[56,20],[45,20]],
  arrows:[{f:[56,6],t:[56,20],c:2},{f:[56,20],t:[45,20],c:-1},{f:[45,20],t:[57,13],s:'shot',d:2.3}],
  notes:[{at:[20,24],txt:'КХЛ днём, НХЛ ночью',c:'chalk'}]},
 forecheck:{name:'Схема: форчек 2-1-2',dur:5.5,zone:[43.3,0,61,26],
  us:[[[44,8],[54,7]],[[44,18],[54,19]],[[38,13],[47,13]],[[33,6],[42,6]],[[33,20],[42,20]]],
  them:[[[57,10],[56,11]],[[57,16],[56,15]],[[53,13],[52,13]]],
  ball:[[57,10],[57,16]],
  arrows:[{f:[44,8],t:[54,9],s:'run'},{f:[44,18],t:[54,17],s:'run'},{f:[38,13],t:[48,13],s:'run'}],
  notes:[{at:[8,4],txt:'2 лиги — одна модель'}]},
 umbrella:{name:'Схема: большинство 1-3-1',dur:7,zone:[43.3,0,61,26],
  us:[[[45,13],[46,13]],[[50,5],[51,6]],[[52,13],[53,13]],[[50,21],[51,20]],[[56,13],[56.5,12]]],
  them:[[[53,9],[54,10]],[[53,17],[54,16]],[[49,11],[50,12]],[[49,15],[50,14]]],
  ball:[[45,13],[50,5],[52,13],[50,21],[45,13]],
  arrows:[{f:[45,13],t:[50,5],c:-1},{f:[50,5],t:[50,21],c:3},{f:[50,21],t:[57,13],s:'shot',d:2.2}],
  notes:[{at:[4,24],txt:'1. Локомотив 1612   2. СКА 1598',c:'chalk'}]},
 shots:{name:'Схема: броски и расчёт',dur:6,zone:[49,6.3,61,19.7],
  us:[[[48,8],[52,9]],[[48,18],[52,17]],[[44,13],[47,13]],[[54,6],[55,8]],[[54,20],[55,18]]],
  them:[[[55,11],[56,12]],[[55,15],[56,14]],[[56.5,13],[56.5,13]]],
  ball:[[44,13],[48,8],[52,9]],
  arrows:[{f:[44,13],t:[48,8],c:-1},{f:[52,9],t:[57,13],s:'shot',d:1.5},{f:[52,17],t:[57,13.6],s:'shot',d:2.1}],
  notes:[{at:[4,4],txt:'коридор кэфов 1,6–2,3'},{at:[4,24],txt:'10 000 розыгрышей',c:'chalk',d:2.4}]},
 rush:{name:'Схема: выход два в одного',dur:5,
  us:[[[24,8],[40,9],[52,10]],[[24,18],[40,17],[52,16]]],
  them:[[[44,13],[50,13]],[[40,4],[46,6]]],
  ball:[[24,8],[40,9],[52,16]],
  arrows:[{f:[24,8],t:[46,9],s:'run'},{f:[40,9],t:[52,16],c:2},{f:[52,16],t:[57,13],s:'shot',d:2}],
  notes:[{at:[4,4],txt:'октябрь: 108 ✓  42 ✕'}]},
 faceoff:{name:'Схема: вбрасывание',dur:5,
  us:[[[30.5,13],[30.5,13]],[[30.5,9],[28,8]],[[30.5,17],[28,18]],[[26,10],[22,9]],[[26,16],[22,17]]],
  them:[[[31.5,13],[31.5,13]],[[33,9],[35,8]],[[33,17],[35,18]]],
  ball:[[30.5,13],[27,13]],
  arrows:[{f:[30.5,13],t:[26,13],c:1},{f:[26,13],t:[20,6],s:'run'}],
  notes:[{at:[36,24],txt:'@jarvibet'}]}
};

/* ── общее для страниц ───────────────────────────────── */
window.JB={RM,Board,PLAYS:{football:F,hockey:H},
 esc:t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]),
 f1:(v,d=1)=>v.toFixed(d).replace('.',','),
 plural:(n,a,b,c)=>{const k=n%100,j=n%10;return k>10&&k<20?c:j===1?a:j>1&&j<5?b:c},
 ring:()=>'<svg viewBox="0 0 120 60" aria-hidden="true"><path pathLength="1" d="M14 34C10 16 44 5 72 7c26 2 44 12 40 27-4 16-40 22-66 19C22 50 6 42 12 26c3-7 10-12 18-15"/></svg>',
 two:n=>String(n).padStart(2,'0'),
 at:min=>{const two=n=>String(n).padStart(2,'0'),base=Math.ceil(Date.now()/6e5)*6e5,d=new Date(base+min*6e4+3*3600e3);return `${d.getUTCFullYear()}-${two(d.getUTCMonth()+1)}-${two(d.getUTCDate())} ${two(d.getUTCHours())}:${two(d.getUTCMinutes())}`},
 atMs:t=>Date.parse(t.replace(' ','T')+':00+03:00')};

/* фон страницы + смена схем под раздел */
JB.page=sport=>{const cv=document.getElementById('board');if(!cv)return;const cap=document.getElementById('cap');
 const b=new Board(cv,{sport,plays:JB.PLAYS[sport],alpha:innerWidth<700?.55:1,shift:.04,top:64,
  onPlay:pl=>{if(!cap)return;cap.classList.add('swap');setTimeout(()=>{cap.textContent=pl.name;cap.classList.remove('swap')},RM?0:380)}});
 const secs=[...document.querySelectorAll('[data-play]')];
 const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)b.set(e.target.dataset.play)}),{rootMargin:'-45% 0px -50% 0px'});
 secs.forEach(s=>io.observe(s));JB.board=b;
 // доска уходит в тень, когда читаешь плотный раздел
 const veil=()=>{const k=clamp(scrollY/(innerHeight*.8));cv.style.opacity=(1-k*.45).toFixed(3)};addEventListener('scroll',veil,{passive:true});veil();
};
/* появление элементов раздела */
JB.reveal=()=>{const els=document.querySelectorAll('.rv,.match,.chalkbars,.steps>li,.circ');
 if(!('IntersectionObserver' in window)||RM){els.forEach(e=>e.classList.add('in'));return}
 const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{rootMargin:'0px 0px -12% 0px'});
 els.forEach(e=>io.observe(e))};
/* вкладки в шапке: тень при прокрутке */
addEventListener('scroll',()=>{const h=document.getElementById('hd');if(h)h.style.background=scrollY>8?'color-mix(in srgb,var(--bg) 96%,transparent)':''},{passive:true});
})();
