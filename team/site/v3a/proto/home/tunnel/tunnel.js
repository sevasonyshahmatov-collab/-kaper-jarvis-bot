/* Шаблон «Туннель»: прогресс прокрутки сцены (0..1) управляет холстом-туннелем, раскрытием развилки и игроками. */
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const clamp=(v,a=0,b=1)=>v<a?a:v>b?b:v;
const sm=t=>t*t*(3-2*t);
const rng=(p,a,b)=>clamp((p-a)/(b-a));
const RM=matchMedia('(prefers-reduced-motion:reduce)').matches;
const scene=$('scene'),stick=$('stick'),cv=$('tun'),ctx=cv.getContext('2d'),title=$('title'),hint=$('hint'),credit=$('credit');
const arH=$('ar-h'),arF=$('ar-f'),mob=matchMedia('(max-width:760px)');
const arenas=[arH,arF].map(el=>({el,plr:el.querySelector('.plr'),kids:[...el.querySelector('.txt').children]}));
const hd=$('hd');
function hh(){document.documentElement.style.setProperty('--hh',Math.round(hd.getBoundingClientRect().height)+'px')}
hh();addEventListener('resize',hh);if('ResizeObserver' in window)new ResizeObserver(hh).observe(hd);
if(RM)document.documentElement.classList.add('rm');

/* ── туннель на canvas: перспективная проекция, рёбра-арки, потолочные лампы, свет в конце ─────── */
let W=0,H=0,dpr=1;
function size(){
 dpr=Math.min(window.devicePixelRatio||1,1.5);
 W=cv.clientWidth;H=cv.clientHeight;
 cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);
}
const A=1,B=.6,S=1.25,ZE=15.5,CAM_MAX=ZE-.5;
function draw(tp,t,vx,vy){
 ctx.setTransform(dpr,0,0,dpr,0,0);
 const pulse=RM?.9:.86+.14*Math.sin(t*5.4)*.6+.07*Math.sin(t*13.1+1);
 const f=Math.max(H,W*.9)*.95,cx=W/2+vx,cy=H/2+vy;
 const cam=tp*CAM_MAX,ze=ZE-cam;
 const P=(X,Y,z)=>[cx+X*f/z,cy+Y*f/z];
 ctx.fillStyle='#02050b';ctx.fillRect(0,0,W,H);
 const zn=.3,[ex,ey]=P(A,B,ze);const exW=ex-cx,exH=ey-cy;
 /* стены: тёмная база + свет из проёма вдоль всей длины */
 const quads=[
  [[-A,-B],[-A,B],'l'],[[A,-B],[A,B],'r'],[[-A,-B],[A,-B],'t'],[[-A,B],[A,B],'b']];
 for(const [p0,p1,s] of quads){
  const a=P(p0[0],p0[1],zn),b=P(p1[0],p1[1],zn),c=P(p1[0],p1[1],ze),d=P(p0[0],p0[1],ze);
  ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.lineTo(c[0],c[1]);ctx.lineTo(d[0],d[1]);ctx.closePath();
  ctx.fillStyle=s==='b'?'#0b1424':s==='t'?'#070d18':'#0a1322';ctx.fill();
  const mid=[(c[0]+d[0])/2,(c[1]+d[1])/2],nm=[(a[0]+b[0])/2,(a[1]+b[1])/2];
  const zg=Math.max(.9,ze*.32),ng=P((p0[0]+p1[0])/2,(p0[1]+p1[1])/2,zg);
  const g=ctx.createLinearGradient(mid[0],mid[1],ng[0],ng[1]);
  const k=(s==='b'?.55:.45)*pulse;
  g.addColorStop(0,`rgba(190,222,255,${k})`);g.addColorStop(.45,`rgba(70,130,220,${k*.32})`);g.addColorStop(1,'rgba(20,40,90,0)');
  ctx.fillStyle=g;ctx.fill();
 }
 /* линии перспективы по полу и потолку */
 ctx.lineWidth=1;ctx.strokeStyle=`rgba(120,170,255,${.16*pulse})`;ctx.beginPath();
 for(const x of [-.66,-.33,0,.33,.66]){const a=P(x,B,zn),b=P(x,B,ze);ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);}
 ctx.stroke();
 /* проём: яркий свет, пульсирует («гул») */
 const er=Math.hypot(exW,exH);
 const bloom=ctx.createRadialGradient(cx,cy,0,cx,cy,Math.max(er*2.6,40));
 bloom.addColorStop(0,`rgba(210,232,255,${.55*pulse})`);bloom.addColorStop(.35,`rgba(110,170,255,${.22*pulse})`);bloom.addColorStop(1,'rgba(40,80,200,0)');
 ctx.globalCompositeOperation='lighter';ctx.fillStyle=bloom;ctx.fillRect(0,0,W,H);ctx.globalCompositeOperation='source-over';
 ctx.fillStyle='#fff';
 const eg=ctx.createRadialGradient(cx,cy,0,cx,cy,Math.max(er,1));
 eg.addColorStop(0,'#ffffff');eg.addColorStop(.55,'#eaf5ff');eg.addColorStop(1,'#a9d0ff');
 ctx.fillStyle=eg;ctx.fillRect(cx-exW,cy-exH,exW*2,exH*2);
 /* арки и лампы: от дальних к ближним */
 const k0=Math.floor(cam/S)+1;
 const n=Math.ceil((ze+S)/S);
 for(let i=n;i>=0;i--){
  const zk=(k0+i)*S-cam;if(zk<.34||zk>=ze-.02)continue;
  const near=clamp(1-zk/ze*.0-zk/9,0,1);
  const fogA=clamp(1.15-zk/ze,.35,1);
  /* лампы на потолке в промежутке до следующей арки (сначала, чтобы арки закрывали дальний край) */
  const idx=k0+i;
  const fl=.82+.18*Math.sin(t*9+idx*2.3)*(idx%3===0?1:.3);
  for(const side of [1]){
   const z0=zk+S*.3,z1=zk+S*.75;
   if(z0<.34)continue;
   const l=[P(-.26,-B+.01,z0),P(.26,-B+.01,z0),P(.26,-B+.01,z1),P(-.26,-B+.01,z1)];
   const fa=Math.min(1,fogA+.3)*pulse*fl;
   ctx.globalCompositeOperation='lighter';
   const gl=[P(-.5,-B,z0),P(.5,-B,z0),P(.5,-B,z1),P(-.5,-B,z1)];
   ctx.fillStyle=`rgba(80,140,255,${.16*fa})`;ctx.beginPath();gl.forEach((p,j)=>j?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.fill();
   ctx.globalCompositeOperation='source-over';
   ctx.fillStyle=`rgba(236,246,255,${fa})`;ctx.beginPath();l.forEach((p,j)=>j?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.fill();
   /* отражение на мокром полу */
   const r=[P(-.2,B-.01,z0),P(.2,B-.01,z0),P(.2,B-.01,z1),P(-.2,B-.01,z1)];
   ctx.fillStyle=`rgba(170,210,255,${.22*fa})`;ctx.beginPath();r.forEach((p,j)=>j?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.fill();
  }
  /* арка: тёмное кольцо с подсвеченной внутренней кромкой */
  const o=[P(-A,-B,zk),P(A,-B,zk),P(A,B,zk),P(-A,B,zk)];
  const q=.1,inn=[P(-A+q,-B+q*.6,zk),P(A-q,-B+q*.6,zk),P(A-q,B-q*.6,zk),P(-A+q,B-q*.6,zk)];
  ctx.beginPath();o.forEach((p,j)=>j?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();
  inn.forEach((p,j)=>j?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();
  ctx.fillStyle=`rgb(${8+10*near|0},${14+16*near|0},${28+30*near|0})`;ctx.fill('evenodd');
  ctx.lineWidth=Math.max(1,.012*f/zk);ctx.strokeStyle=`rgba(120,175,255,${.5*fogA*pulse})`;
  ctx.beginPath();inn.forEach((p,j)=>j?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.stroke();
 }
 /* виньетка и общий «заход в свет» */
 const v=ctx.createRadialGradient(cx,cy,Math.min(W,H)*.3,cx,cy,Math.hypot(W,H)*.62);
 v.addColorStop(0,'rgba(0,0,0,0)');v.addColorStop(1,`rgba(0,2,8,${.6*(1-rng(tp,.8,1))})`);
 ctx.fillStyle=v;ctx.fillRect(0,0,W,H);
}

/* ── сцена: состояние по прогрессу прокрутки ─────────────────────────────────────────── */
let target=0,cur=0,mx=0,my=0,smx=0,smy=0,last=0,live=false;
function progress(){
 const r=scene.getBoundingClientRect(),stickH=stick.offsetHeight;
 return clamp(-r.top/Math.max(1,r.height-stickH-0));
}
function setFork(p,t){
 const open=sm(rng(p,.42,.76)),pl=sm(rng(p,.52,.82)),ui=sm(rng(p,.74,.9));
 const vert=mob.matches,g=.35,inset=(1-open)*(vert?24:34);
 const edge=50-50*open;
 arenas.forEach((a,i)=>{
  const first=i===0;
  let cp;
  if(!vert)cp=first?`inset(${inset}% ${50+g}% ${inset}% ${edge}%)`:`inset(${inset}% ${edge}% ${inset}% ${50+g}%)`;
  else cp=first?`inset(${edge}% ${(1-open)*24}% ${50+g}% ${(1-open)*24}%)`:`inset(${50+g}% ${(1-open)*24}% ${edge}% ${(1-open)*24}%)`;
  a.el.style.clipPath=cp;
  a.el.style.opacity=clamp(open*3);
  /* лёгкий пульс света арены («гул») */
  a.el.style.setProperty('--hum',(.5+.5*Math.sin(t*5.4+(first?0:1.3))).toFixed(3));
  const dir=vert?0:(first?1:-1);
  const sc=.62+.38*pl;
  a.plr.style.opacity=clamp(pl*1.6);
  a.plr.style.transform=`translate3d(${dir*(1-pl)*38}%,${vert?(first?-1:1)*(1-pl)*10:(1-pl)*8}%,0) scale(${sc})`;
  a.kids.forEach((k,n)=>{const u=sm(rng(p,.74+n*.025,.88+n*.01));k.style.opacity=u;k.style.transform=`translate3d(0,${(1-u)*26}px,0)`});
  a.el.classList.toggle('on',ui>.6);
 });
 credit.style.opacity=ui;
}
function render(t){
 const p=cur;
 const tp=rng(p,0,.62);
 /* заголовок отъезжает назад: уменьшается к точке схода и гаснет */
 const tt=rng(p,.0,.3);
 title.style.opacity=(1-sm(rng(p,.04,.3))).toFixed(3);
 title.style.transform=`translate3d(${-smx*8}px,${-smy*6}px,0) scale(${1-.78*sm(tt)})`;
 hint.style.opacity=1-rng(p,.0,.05);
 draw(tp,t,smx*26,smy*14);
 setFork(p,t);
}

function frame(ts){
 const t=ts/1000,dt=Math.min(.05,t-last||.016);last=t;
 target=progress();
 const k=1-Math.pow(.0009,dt);           /* сглаживание не зависит от частоты кадров */
 cur+=(target-cur)*k;if(Math.abs(target-cur)<1e-4)cur=target;
 smx+=(mx-smx)*(1-Math.pow(.01,dt));smy+=(my-smy)*(1-Math.pow(.01,dt));
 render(t);
 requestAnimationFrame(frame);
}
addEventListener('pointermove',e=>{mx=(e.clientX/innerWidth-.5)*2;my=(e.clientY/innerHeight-.5)*2},{passive:true});
addEventListener('pointerleave',()=>{mx=my=0});
addEventListener('resize',size);

/* ── данные: счётчики матчей и список ────────────────────────────────────────────────── */
function data(){
 const Hm=window.HOME;if(!Hm||!Hm.J)return;
 const e=Hm.esc,all=Hm.all();
 $('lh-date').textContent=Hm.dateStr();
 $('upd').textContent=Hm.upd()?Hm.upd()+'.':'';
 if(!all.length)return;
 const cnt=(l,el,fb)=>{const n=l.filter(m=>m.day==='сегодня').length;el.textContent=n?`${n} ${Hm.pl(n,'матч','матча','матчей')} сегодня`:l.length?`${l.length} ${Hm.pl(l.length,'матч','матча','матчей')} скоро`:fb};
 cnt(all.filter(m=>m.hockey),$('cnt-h'),'КХЛ и НХЛ');cnt(all.filter(m=>!m.hockey),$('cnt-f'),'топ-лиги Европы');
 const rest=all.filter(m=>m.md);
 const hk=rest.filter(m=>m.hockey).slice(0,5),fb=rest.filter(m=>!m.hockey).slice(0,5);
 const rows=hk.concat(fb).sort((a,b)=>a.t.localeCompare(b.t)).slice(0,8);
 $('rows').innerHTML=rows.map((m,i)=>{
  const k=m.ln&&m.bi>=0?[m.ln.p1,m.ln.x,m.ln.p2][m.bi]:null;
  const cells=[['П1',m.pr[0]],['Х',m.pr[1]],['П2',m.pr[2]]].filter(c=>c[1]!=null&&!(c[0]==='Х'&&m.hockey&&!(m.ln&&m.ln.x)));
  const tops=[0,1,2].map(j=>m.bi===j);
  const bar=[['П1',m.pr[0],0],['Х',m.pr[1],1],['П2',m.pr[2],2]].filter(c=>c[1]!=null&&!(c[0]==='Х'&&m.hockey&&!(m.ln&&m.ln.x)));
  return `<a class="row ${m.hockey?'h':'f'}" style="--i:${i}" href="${m.href}" aria-label="${e(m.hn)} — ${e(m.an)}, ${m.hm} МСК">
   <span class="tm">${m.hm}<small>${m.day==='сегодня'?m.lgn:m.day}</small></span>
   <span class="tt"><span class="cr"><img src="${m.hc}" alt="" width="40" height="40" loading="lazy"><img src="${m.ac}" alt="" width="40" height="40" loading="lazy"></span><span class="nm">${e(m.hn)}<i>—</i>${e(m.an)}</span></span>
   <span class="br"><span class="bar">${bar.map(c=>`<span class="${c[2]===m.bi?'top':''}" style="flex:${Math.max(c[1],.04)}"></span>`).join('')}</span><span class="pc">${bar.map(c=>`<span>${c[0]} <b>${Hm.pct(c[1])}%</b></span>`).join('')}</span></span>
   <span class="pk">${Hm.pct(m.best)}<small>%</small><span>${m.bi===1?'ничья':e(m.who)}${k?` · кэф ${Hm.f2(k)}`:''}</span></span></a>`;
 }).join('');
 const els=[...document.querySelectorAll('.row')];
 if(RM||!('IntersectionObserver' in window))els.forEach(r=>r.classList.add('in'));
 else{const io=new IntersectionObserver(es=>es.forEach(x=>{if(x.isIntersecting){x.target.classList.add('in');io.unobserve(x.target)}}),{threshold:.15});els.forEach(r=>io.observe(r))}
}
data();

size();
if(RM){
 draw(.22,0,0,0);
 addEventListener('resize',()=>draw(.22,0,0,0));
}else{
 cur=target=progress();
 requestAnimationFrame(frame);
}
})();
