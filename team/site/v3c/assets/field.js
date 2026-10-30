/* JARVIS v3c — поле частиц на canvas 2D.
   Частицы = «розыгрыши» модели. Каждая секция задаёт фигуру (data-shape): поле/каток в перспективе, сеть,
   орбиты, волна, точечная гистограмма 10 000 розыгрышей, кольцо итогов, самолётик Telegram.
   Частицы пружинят к своей точке фигуры, «дышат» и расступаются от курсора.
   Телефон — меньше частиц и без курсора; prefers-reduced-motion — фигура рисуется один раз, без цикла. */
(()=>{
const cv=document.getElementById('field');if(!cv)return;
const g=cv.getContext('2d',{alpha:false});
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const FINE=matchMedia('(hover:hover) and (pointer:fine)').matches;
const sport=document.documentElement.dataset.sport||'football';
const css=getComputedStyle(document.documentElement);
const BG=css.getPropertyValue('--bg').trim()||'#02070b';
const PAL={football:['#3fe7ab','#d6fff0','#139a6e'],hockey:['#9edcff','#eef8ff','#4b86e0'],both:['#3fe7ab','#9edcff','#e9f4f1']}[sport];

let W=0,H=0,DPR=1,N=0,P=[],shape='hero',opts={},t0=performance.now(),mx=-1e4,my=-1e4,raf=0,running=false,dim=1,dimT=1;
const weak=(navigator.hardwareConcurrency||8)<=4||(navigator.deviceMemory||8)<=3;
function count(){const w=innerWidth;let n=w<520?620:w<900?1200:w<1500?2200:2600;if(weak)n=Math.round(n*.6);return n}

/* ── фигуры: каждая возвращает функцию (i,t)->[x,y] и, если нужно, цвет-группу ── */
const rnd=(a=1)=>Math.random()*a;
const desk=()=>W>=960;
function region(){ // где рисовать фигуру: на компьютере — правая часть, на телефоне — весь экран, ниже
  return desk()?{x:W*.56,y:H*.12,w:W*.4,h:H*.5}:{x:W*.08,y:H*.14,w:W*.84,h:H*.4}}

// отрезки линий фигуры → равномерные точки
function sampleSegs(segs,n){const L=segs.map(s=>Math.hypot(s[2]-s[0],s[3]-s[1])),T=L.reduce((a,b)=>a+b,0),out=[];
  for(let k=0;k<n;k++){let d=Math.random()*T,j=0;while(d>L[j]&&j<L.length-1){d-=L[j];j++}const s=segs[j],q=L[j]?d/L[j]:0;out.push([s[0]+(s[2]-s[0])*q,s[1]+(s[3]-s[1])*q])}return out}
function arc(cx,cy,r,a0,a1,steps=28,sx=1){const s=[];for(let i=0;i<steps;i++){const a=a0+(a1-a0)*i/steps,b=a0+(a1-a0)*(i+1)/steps;s.push([cx+Math.cos(a)*r*sx,cy+Math.sin(a)*r,cx+Math.cos(b)*r*sx,cy+Math.sin(b)*r])}return s}
const rect=(x,y,w,h)=>[[x,y,x+w,y],[x+w,y,x+w,y+h],[x+w,y+h,x,y+h],[x,y+h,x,y]];

// поле в координатах u∈[0,1] (длина), v∈[0,1] (ширина); соотношение 105×68
function pitchSegs(){const k=68/105,s=[...rect(0,0,1,1),[.5,0,.5,1],...arc(.5,.5,.087,0,Math.PI*2,40,k)];
  const bw=16.5/105,bh=40.3/68,gw=5.5/105,gh=18.3/68;
  s.push(...rect(0,.5-bh/2,bw,bh),...rect(1-bw,.5-bh/2,bw,bh),...rect(0,.5-gh/2,gw,gh),...rect(1-gw,.5-gh/2,gw,gh));
  s.push(...arc(11/105,.5,.087,-.92,.92,12,k),...arc(1-11/105,.5,.087,Math.PI-.92,Math.PI+.92,12,k));return s}
// каток 60×30, скруглённые углы
function rinkSegs(){const r=.28,k=30/60,s=[];const rx=r*k;
  s.push([rx,0,1-rx,0],[rx,1,1-rx,1],[0,r,0,1-r],[1,r,1,1-r]);
  s.push(...arc(rx,r,r,Math.PI,Math.PI*1.5,10,k),...arc(1-rx,r,r,Math.PI*1.5,Math.PI*2,10,k),...arc(1-rx,1-r,r,0,Math.PI*.5,10,k),...arc(rx,1-r,r,Math.PI*.5,Math.PI,10,k));
  s.push([.5,0,.5,1],[.5,0,.5,1],[.375,0,.375,1],[.625,0,.625,1],[.06,.04,.06,.96],[.94,.04,.94,.96]);
  s.push(...arc(.5,.5,.15,0,Math.PI*2,36,k));
  for(const [cx,cy] of [[.2,.27],[.2,.73],[.8,.27],[.8,.73]])s.push(...arc(cx,cy,.15,0,Math.PI*2,30,k));
  s.push(...arc(.06,.5,.06,-Math.PI/2,Math.PI/2,10,k),...arc(.94,.5,.06,Math.PI/2,Math.PI*1.5,10,k));return s}

// перспектива: плоскость (u,v) → экран, с медленным поворотом
function persp(u,v,t,box,yaw,asp=.65){const a=yaw+Math.sin(t*.00011)*.035,X=u-.5,Y=(v-.5)*asp,c=Math.cos(a),sn=Math.sin(a),rX=X*c-Y*sn,rY=(X*sn+Y*c)/asp;
  const z=1+(rY+.5)*1.7,s=1/z;return [box.cx+rX*box.w*s,box.hy+(box.by-box.hy)*s]}

const SH={
 field(n,type){ // поле/каток: 82% точек на линиях, остальное — «дыхание» внутри
  const segs=type==='rink'?rinkSegs():pitchSegs(),line=Math.round(n*.9),pts=sampleSegs(segs,line);
  while(pts.length<n)pts.push([rnd(),rnd()]);
  return (i,t)=>{const D=desk(),box=D?{cx:W*.52,w:W*1.08,hy:H*.36,by:H*1.08}:{cx:W*.5,w:W*1.7,hy:H*.5,by:H*1.08};
   const p=pts[i];return persp(p[0],p[1],t,box,-.04,type==='rink'?.5:.65)}},
 split(n){ // главная: слева поле, справа каток
  const a=sampleSegs(rinkSegs(),Math.ceil(n/2)),b=sampleSegs(pitchSegs(),Math.floor(n/2));
  return (i,t)=>{const D=W>=760,left=i<a.length,p=left?a[i]:b[i-a.length];
   const box=D?{cx:left?W*.27:W*.73,w:W*.38,hy:H*.58,by:H*1.12}:{cx:W*.5,w:W*.9,hy:left?H*.42:H*.70,by:left?H*.68:H*.98};
   return persp(p[0],p[1],t,box,left?.06:-.06,left?.5:.65)}},
 network(n){ // нейросеть: узлы слоями и связи между соседними слоями
  const L=[3,5,6,5,3],nodes=[];L.forEach((c,li)=>{for(let j=0;j<c;j++)nodes.push([li/(L.length-1),(j+.5)/c,li])});
  const edges=[];nodes.forEach((a,ia)=>nodes.forEach((b,ib)=>{if(b[2]===a[2]+1)edges.push([a[0],a[1],b[0],b[1]])}));
  const ne=Math.round(n*.55),pts=sampleSegs(edges,ne).map(p=>[p[0],p[1],Math.random()]);
  while(pts.length<n){const nd=nodes[pts.length%nodes.length],a=rnd(Math.PI*2),r=Math.pow(rnd(),.6)*.03;pts.push([nd[0]+Math.cos(a)*r,nd[1]+Math.sin(a)*r*1.6,-1])}
  return (i,t)=>{const R=region(),p=pts[i];let u=p[0],v=p[1];
   if(p[2]>=0){const q=(p[2]+t*.00008)%1;} // сигнал бежит по связям — фаза в alpha
   return [R.x+u*R.w,R.y+v*R.h]}},
 orbit(n){ // орбиты: лиги вращаются вокруг одной модели
  const rings=[.18,.3,.42,.5],sp=[1,-.7,.5,-.35];const pts=[];for(let i=0;i<n;i++){const r=i%rings.length;pts.push([r,rnd(Math.PI*2),(rnd()-.5)*.02])}
  return (i,t)=>{const R=region(),c=[R.x+R.w/2,R.y+R.h/2],s=Math.min(R.w,R.h*1.4),p=pts[i],rr=rings[p[0]]+p[2],a=p[1]+t*.00012*sp[p[0]];
   return [c[0]+Math.cos(a)*rr*s,c[1]+Math.sin(a)*rr*s*.42]}},
 wave(n){ // сила команд: линии силы — несколько волн разной амплитуды
  const k=7,pts=[];for(let i=0;i<n;i++)pts.push([rnd(),i%k]);
  return (i,t)=>{const R=region(),p=pts[i],amp=.05+p[1]*.012;
   return [R.x+p[0]*R.w,R.y+R.h*(.15+p[1]*.11)+Math.sin(p[0]*7+t*.0007+p[1]*.7)*amp*R.h]}},
 hist(n,o){ // точечная гистограмма: каждая точка — доля из 10 000 розыгрышей
  const pr=o.p||[.1,.2,.3,.2,.1,.05,.03,.02],B=pr.length,sum=pr.reduce((a,b)=>a+b,0),cnt=pr.map(v=>Math.round(v/sum*n));
  let d=n-cnt.reduce((a,b)=>a+b,0);cnt[cnt.indexOf(Math.max(...cnt))]+=d;
  const mxc=Math.max(...cnt),pts=[];
  cnt.forEach((c,b)=>{for(let j=0;j<c;j++)pts.push([b,j])});
  return (i,t)=>{const R=region(),p=pts[i]||[0,0],bw=R.w/B,dot=Math.sqrt(bw*.78*R.h*.9/mxc),cols=Math.max(1,Math.floor(bw*.78/dot)),
   x0=R.x+p[0]*bw+bw*.11,row=Math.floor(p[1]/cols),col=p[1]%cols;
   return [x0+col*dot,R.y+R.h-row*dot]}},
 ring(n,o){ // кольцо итогов: доля «зашло» ярче и плотнее
  const f=o.p||.6;return (i,t)=>{const R=region(),c=[R.x+R.w/2,R.y+R.h/2],r=Math.min(R.w,R.h)*.44,q=i/n,
   a=-Math.PI/2+q*Math.PI*2+Math.sin(t*.0003)*.02,band=(i*7919%100)/100,rr=r*(q<f?(.9+band*.12):(.97+band*.05));
   return [c[0]+Math.cos(a)*rr,c[1]+Math.sin(a)*rr]}},
 plane(n){ // самолётик Telegram
  const P=[[.02,.46],[.96,.06],[.8,.92],[.52,.7],[.38,.92],[.36,.64],[.86,.16],[.32,.6],[.02,.46]],segs=[];
  for(let i=0;i<P.length-1;i++)segs.push([P[i][0],P[i][1],P[i+1][0],P[i+1][1]]);
  const pts=sampleSegs(segs,Math.round(n*.8));while(pts.length<n)pts.push([rnd(),rnd()]);
  return (i,t)=>{const R=region(),s=Math.min(R.w,R.h*1.3)*.8,p=pts[i],dx=Math.sin(t*.0005)*8,dy=Math.cos(t*.0004)*10;
   return [R.x+(R.w-s)/2+p[0]*s+dx,R.y+(R.h-s*.8)/2+p[1]*s*.8+dy]}},
 dust(n){const pts=[];for(let i=0;i<n;i++)pts.push([rnd(),rnd(),rnd()]);
  return (i,t)=>{const p=pts[i];return [p[0]*W+Math.sin(t*.0002+p[2]*9)*20,((p[1]*H-t*.008*p[2])%H+H)%H]}}
};

let target=null;
function build(){const n=N,name=shape;
 if(name==='hero')target=SH.field(n,sport==='hockey'?'rink':'pitch');
 else if(name==='split')target=SH.split(n);
 else if(SH[name])target=SH[name](n,opts);else target=SH.dust(n);
 dimT=opts.dim!=null?opts.dim:(name==='hero'||name==='split'?1:desk()?.75:.4)}

function resize(){DPR=Math.min(innerWidth<760?1.25:1.6,devicePixelRatio||1);W=innerWidth;H=innerHeight;cv.width=Math.round(W*DPR);cv.height=Math.round(H*DPR);g.setTransform(DPR,0,0,DPR,0,0);
 const n=count();if(n!==N){const old=P;N=n;P=[];for(let i=0;i<N;i++){const o=old[i];P.push(o||{x:rnd(W),y:rnd(H),vx:0,vy:0,s:1+rnd(1.6),c:Math.random()<.78?0:Math.random()<.6?1:2,ph:rnd(6.28)})}}
 build();if(RM)drawStatic()}

function step(now){const t=now-t0;dim+=(dimT-dim)*.05;
 g.globalCompositeOperation='source-over';g.globalAlpha=1;g.fillStyle=BG;g.globalAlpha=.34;g.fillRect(0,0,W,H);g.globalAlpha=1;
 g.globalCompositeOperation='lighter';
 const k=.018,damp=.86,rep=FINE?130:0,rep2=rep*rep;
 const buckets=[[],[],[]];
 for(let i=0;i<N;i++){const p=P[i],tp=target(i,t),br=Math.sin(t*.0011+p.ph)*1.6;
  let ax=(tp[0]+br-p.x)*k,ay=(tp[1]+Math.cos(t*.0009+p.ph)*1.6-p.y)*k;
  if(rep){const dx=p.x-mx,dy=p.y-my,d2=dx*dx+dy*dy;if(d2<rep2&&d2>1){const f=(1-d2/rep2)*2.2/Math.sqrt(d2);ax+=dx*f;ay+=dy*f}}
  p.vx=(p.vx+ax)*damp;p.vy=(p.vy+ay)*damp;p.x+=p.vx;p.y+=p.vy;
  buckets[shape==='split'?(i<N/2?1:0):p.c].push(p)}
 for(let c=0;c<3;c++){g.fillStyle=PAL[c];const B=buckets[c];
  for(let j=0;j<B.length;j++){const p=B[j],sp=Math.min(1,Math.abs(p.vx)+Math.abs(p.vy));g.globalAlpha=Math.min(1,(.6+sp*.4)*dim);const s=p.s+sp*.6;g.fillRect(p.x-s/2,p.y-s/2,s,s)}}
 g.globalAlpha=1;
 raf=requestAnimationFrame(step)}

function drawStatic(){g.globalCompositeOperation='source-over';g.globalAlpha=1;g.fillStyle=BG;g.fillRect(0,0,W,H);g.globalCompositeOperation='lighter';
 for(let i=0;i<N;i++){const tp=target(i,0),p=P[i];p.x=tp[0];p.y=tp[1];g.fillStyle=PAL[shape==='split'?(i<N/2?1:0):p.c];g.globalAlpha=.55*dimT;g.fillRect(p.x-p.s/2,p.y-p.s/2,p.s,p.s)}g.globalAlpha=1}

function start(){if(RM||running)return;running=true;raf=requestAnimationFrame(step)}
function stop(){running=false;cancelAnimationFrame(raf)}

// фигура по секции в центре экрана
function set(name,o={}){if(name===shape&&JSON.stringify(o)===JSON.stringify(opts))return;shape=name;opts=o;build();if(RM)drawStatic()}
function burst(){if(RM)return;for(const p of P){p.vx+=(Math.random()-.5)*26;p.vy-=6+Math.random()*22}}

const secs=[...document.querySelectorAll('[data-shape]')];
function pick(){const mid=innerHeight*.5;let best=null;for(const s of secs){const r=s.getBoundingClientRect();if(r.top<=mid&&r.bottom>=mid){best=s;break}}
 if(!best)return;let o={};try{o=best.dataset.opts?JSON.parse(best.dataset.opts):{}}catch(e){}
 if(best._opts)o=best._opts;set(best.dataset.shape,o)}
addEventListener('scroll',()=>{if(!pick.q){pick.q=1;requestAnimationFrame(()=>{pick.q=0;pick()})}},{passive:true});
addEventListener('resize',()=>{clearTimeout(resize.t);resize.t=setTimeout(resize,150)});
if(FINE)addEventListener('pointermove',e=>{mx=e.clientX;my=e.clientY},{passive:true});
document.addEventListener('pointerleave',()=>{mx=my=-1e4});
document.addEventListener('visibilitychange',()=>document.hidden?stop():start());

// просадка кадров — вдвое меньше частиц
let fr=0,acc=0,last=performance.now();
function watch(now){const d=now-last;last=now;if(running){acc+=d;fr++;if(fr===90){if(acc/fr>26&&N>400){N=Math.round(N*.6);P.length=N;build()}fr=0;acc=0}}requestAnimationFrame(watch)}

shape=secs[0]?.dataset.shape||'hero';
resize();pick();start();if(!RM)requestAnimationFrame(watch);
window.Field={set,burst,refresh:pick};
})();
