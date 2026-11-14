/* «Мозг» модели на странице «Как считает модель» (владелец 14.11): объёмная сеть-мозг из двух полушарий медленно вращается,
   по связям бегут импульсы: слева входят данные (форма, броски, вратари, составы, линия), справа выходят исходы (П1 · Х · П2, тотал).
   Canvas, только пока блок на экране; «уменьшить движение» — один неподвижный кадр. Место: <div class="md-brain"> в .md-top. */
(()=>{
'use strict';
const box=document.querySelector('.md-brain');if(!box)return;
const cv=document.createElement('canvas');cv.setAttribute('role','img');
cv.setAttribute('aria-label','Схема: данные о матче проходят через сеть модели и превращаются в вероятности исходов');box.appendChild(cv);
const ctx=cv.getContext('2d');const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const FB=/[?&]s=f/.test(location.search);
const IN=FB?['Форма','Удары и xG','Составы','Дом / выезд','Линия']:['Форма','Броски','Вратари','Составы','Линия'];
const OUT=FB?['П1 · Х · П2','Тотал','Обе забьют']:['П1 · Х · П2','Тотал','Победа с ОТ'];
/* точки мозга: два полушария (эллипсоиды) с извилистым шумом, плюс мозжечок сзади-снизу */
let seed=7;const rnd=()=>(seed=(seed*16807)%2147483647)/2147483647;
const P=[];
for(let h=-1;h<=1;h+=2)for(let i=0;i<78;i++){
 const u=rnd()*2-1,t=rnd()*Math.PI*2,r=Math.sqrt(1-u*u),k=.9+.12*Math.sin(t*5+u*7);
 let x=r*Math.cos(t)*.62*k,y=u*.68*k,z=r*Math.sin(t)*.95*k;
 x=x+h*.36;if(Math.abs(x)<.05)x=h*.05;                     /* щель между полушариями */
 if(y>.25)y=.25+(y-.25)*.8;P.push({x,y:-y*.85+.02,z,h})}
for(let i=0;i<16;i++){const t=rnd()*Math.PI*2,u=rnd();P.push({x:Math.cos(t)*.28*u,y:.5+rnd()*.12,z:-.55+Math.sin(t)*.2*u,h:0})}
/* связи: по 3 ближайших соседа */
const E=[],adj=P.map(()=>[]);
P.forEach((a,i)=>{const d=P.map((b,j)=>[j,(a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2]).filter(x=>x[0]!==i).sort((p,q)=>p[1]-q[1]).slice(0,3);
 d.forEach(([j])=>{if(!adj[i].includes(j)){E.push([i,j]);adj[i].push(j);adj[j].push(i)}})});
let W=0,H=0,dpr=1,ang=0,vis=true,last=0;
const size=()=>{const r=box.getBoundingClientRect();dpr=Math.min(2,devicePixelRatio||1);W=r.width;H=r.height;cv.width=W*dpr;cv.height=H*dpr;cv.style.width=W+'px';cv.style.height=H+'px'};
const pr=[];
const project=()=>{const ca=Math.cos(ang),sa=Math.sin(ang),tl=Math.sin(ang*.7)*.18,ct=Math.cos(tl),st=Math.sin(tl);
 const cx=W*.5,cy=H*.5,S=W<520?Math.min(W*.27,H*.4):Math.min(W*.33,H*.5);
 P.forEach((p,i)=>{let x=p.x*ca+p.z*sa,z=-p.x*sa+p.z*ca,y=p.y*ct-z*st;z=p.y*st+z*ct;const f=2.6/(2.6+z);pr[i]={x:cx+x*S*f,y:cy+y*S*f,z,f}})};
/* импульсы: идут цепочкой по связям */
const pulses=[];
const spawn=(from)=>{const i=from!=null?from:Math.floor(rnd()*P.length);const n=adj[i];if(!n.length)return;pulses.push({a:i,b:n[Math.floor(Math.random()*n.length)],t:0,hops:3+Math.floor(Math.random()*5),sp:.9+Math.random()*.8})};
const leftMost=()=>pr.map((p,i)=>[i,p.x]).sort((a,b)=>a[1]-b[1]).slice(0,10).map(x=>x[0]);
const rightMost=()=>pr.map((p,i)=>[i,p.x]).sort((a,b)=>b[1]-a[1]).slice(0,10).map(x=>x[0]);
const css=getComputedStyle(document.documentElement);
const C1='#3ee0ff',C2=(css.getPropertyValue('--sport')||'#3ee0ff').trim()||'#3ee0ff';
const FONT=(css.getPropertyValue('--display')||'Inter, Arial, sans-serif').trim();
let inT=0,outFlash=OUT.map(()=>0);
const draw=dt=>{
 ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);project();
 {const g=ctx.createRadialGradient(W/2,H/2,0,W/2,H/2,Math.min(W,H)*.5);g.addColorStop(0,'rgba(62,160,255,.16)');g.addColorStop(1,'rgba(62,160,255,0)');ctx.fillStyle=g;ctx.fillRect(0,0,W,H)}  /* свечение за мозгом */
 const L=leftMost(),R=rightMost();
 /* подписи входов и выходов */
 const lx=Math.max(8,W*.02),rx=W-Math.max(8,W*.02),fs=Math.max(11,Math.min(14,W/36));
 ctx.font=`600 ${fs}px ${FONT}`;ctx.textBaseline='middle';
 const iy=IN.map((_,k)=>H*(.2+k*.6/(IN.length-1))),oy=OUT.map((_,k)=>H*(.32+k*.36/(OUT.length-1)));
 IN.forEach((s,k)=>{const t=pr[L[k%L.length]];ctx.strokeStyle='rgba(62,224,255,.16)';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(lx+ctx.measureText(s).width+8,iy[k]);
  ctx.bezierCurveTo(W*.24,iy[k],W*.22,t.y,t.x,t.y);ctx.stroke();ctx.fillStyle='rgba(234,243,255,.72)';ctx.textAlign='left';ctx.fillText(s,lx,iy[k])});
 OUT.forEach((s,k)=>{const t=pr[R[k%R.length]];ctx.strokeStyle='rgba(62,224,255,.16)';ctx.beginPath();ctx.moveTo(t.x,t.y);
  ctx.bezierCurveTo(W*.78,t.y,W*.76,oy[k],rx-ctx.measureText(s).width-8,oy[k]);ctx.stroke();
  const g=outFlash[k];ctx.fillStyle=`rgba(${g>0?'62,224,255':'234,243,255'},${.72+g*.28})`;ctx.textAlign='right';ctx.fillText(s,rx,oy[k])});
 /* связи */
 E.forEach(([i,j])=>{const a=pr[i],b=pr[j],d=(a.f+b.f)/2;ctx.strokeStyle=`rgba(120,200,255,${(.1+.3*(d-.75)).toFixed(3)})`;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke()});
 /* узлы (дальние — тусклее) */
 pr.map((p,i)=>[p,i]).sort((a,b)=>b[0].z-a[0].z).forEach(([p])=>{const al=Math.max(.15,Math.min(1,(p.f-.72)*2.2));ctx.fillStyle=`rgba(180,225,255,${al.toFixed(2)})`;ctx.beginPath();ctx.arc(p.x,p.y,1.5+2.2*p.f*p.f,0,7);ctx.fill()});
 /* импульсы */
 if(!RM){inT+=dt;if(inT>.11){inT=0;spawn(Math.random()<.45?L[Math.floor(Math.random()*L.length)]:null)}}
 ctx.globalCompositeOperation='lighter';
 for(let k=pulses.length-1;k>=0;k--){const q=pulses[k];q.t+=dt*q.sp*2.2;
  if(q.t>=1){if(--q.hops<=0||!adj[q.b].length){if(R.includes(q.b)){const o=Math.floor(Math.random()*OUT.length);outFlash[o]=1}pulses.splice(k,1);continue}
   const n=adj[q.b].filter(j=>j!==q.a);q.a=q.b;q.b=(n.length?n:adj[q.b])[Math.floor(Math.random()*(n.length||adj[q.b].length))];q.t=0}
  const a=pr[q.a],b=pr[q.b],x=a.x+(b.x-a.x)*q.t,y=a.y+(b.y-a.y)*q.t;
  const g=ctx.createRadialGradient(x,y,0,x,y,9);g.addColorStop(0,'rgba(120,240,255,.95)');g.addColorStop(.35,'rgba(62,224,255,.45)');g.addColorStop(1,'rgba(62,224,255,0)');
  ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,9,0,7);ctx.fill();
  ctx.strokeStyle='rgba(62,224,255,.55)';ctx.lineWidth=1.4;ctx.beginPath();ctx.moveTo(a.x+(b.x-a.x)*Math.max(0,q.t-.35),a.y+(b.y-a.y)*Math.max(0,q.t-.35));ctx.lineTo(x,y);ctx.stroke()}
 ctx.globalCompositeOperation='source-over';
 outFlash=outFlash.map(v=>Math.max(0,v-dt*1.6));
};
const loop=t=>{const dt=Math.min(.05,(t-(last||t))/1000);last=t;ang+=dt*.32;draw(dt);if(vis)requestAnimationFrame(loop);else last=0};
size();addEventListener('resize',()=>{size();if(RM)draw(0)});
if(RM){ang=.5;for(let i=0;i<14;i++)spawn();draw(0);return}
for(let i=0;i<8;i++)spawn();
if('IntersectionObserver' in window)new IntersectionObserver(es=>{const v=es[0].isIntersecting;if(v&&!vis){vis=true;requestAnimationFrame(loop)}vis=v}).observe(box);
requestAnimationFrame(loop);
})();
