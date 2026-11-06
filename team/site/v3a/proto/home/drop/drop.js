/* Шаблон «Матчи падают»: фишки матчей дня падают на лёд (хоккей) и газон (футбол). Своя 2D-физика, без библиотек. */
(()=>{
'use strict';
const H=window.HOME,$=id=>document.getElementById(id);
if(!H||!H.J)return;
const e=H.esc,RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const clamp=(v,a,b)=>v<a?a:v>b?b:v;
$('dr-date').textContent=H.dateStr();
$('dr-upd').textContent=H.upd()?H.upd()+'.':'';

/* ───────── отбор матчей ───────── */
const all=H.all().filter(m=>m.md&&m.bi>=0&&m.best>0);
const small=innerWidth<640,cap=small?10:14,per=cap/2;
function pick(list,quota){
 const td=list.filter(m=>m.day==='сегодня'),later=list.filter(m=>m.day!=='сегодня');
 const out=td.slice(0,quota);
 if(out.length<Math.min(5,quota))out.push(...later.slice(0,Math.min(5,quota)-out.length));
 return out;
}
const hAll=all.filter(m=>m.hockey),fAll=all.filter(m=>!m.hockey);
const nh=Math.min(hAll.length,cap-Math.min(fAll.length,per)),nf=Math.min(fAll.length,cap-nh);
const hk=pick(hAll,nh),fb=pick(fAll,nf);
const chosen=hk.concat(fb);
const cnt=(l,el,fb2)=>{const n=l.filter(m=>m.day==='сегодня').length;el.textContent=n?`${n} ${H.pl(n,'матч','матча','матчей')} сегодня`:l.length?`${l.length} ${H.pl(l.length,'матч','матча','матчей')} скоро`:fb2};
cnt(hAll,$('dr-ch'),'КХЛ и НХЛ');cnt(fAll,$('dr-cf'),'топ-лиги Европы');
$('st-h').textContent=hk.length?`${hk.length} ${H.pl(hk.length,'матч','матча','матчей')}`:'';
$('st-f').textContent=fb.length?`${fb.length} ${H.pl(fb.length,'матч','матча','матчей')}`:'';

/* ───────── список ниже первого экрана ───────── */
(function list(){
 const col=(cls,title,arr)=>`<div class="nx-col ${cls}"><h3>${title}</h3>${arr.length?arr.map(m=>{
  const k=m.ln&&m.bi>=0?[m.ln.p1,m.ln.x,m.ln.p2][m.bi]:null;
  return `<a class="nr" href="${m.href}" aria-label="${e(m.hn)} — ${e(m.an)}, ${m.hm} МСК">
   <span class="xtm">${m.hm}</span>
   <span class="xpr"><span class="cr"><img src="${m.hc}" alt="" loading="lazy"></span><span class="cr"><img src="${m.ac}" alt="" loading="lazy"></span></span>
   <span class="nm">${e(m.hn)}<i>—</i>${e(m.an)}<small>${m.day==='сегодня'?m.lgn:m.day+', '+m.lgn} · ${m.bi===1?'ничья':e(m.who)}</small></span>
   <span class="pk">${H.pct(m.best)}%<small>${k?'кэф '+H.f2(k):''}</small></span><i class="xbar" style="--w:${H.pct(m.best)}"></i></a>`}).join(''):'<p class="nx-none">Ближайших матчей нет.</p>'}</div>`;
 $('nx').innerHTML=col('h','Хоккей',hAll.slice(0,6))+col('f','Футбол',fAll.slice(0,6));
 const rows=document.querySelectorAll('.nr');
 if('IntersectionObserver' in window&&!RM){const io=new IntersectionObserver(es=>es.forEach(x=>{if(x.isIntersecting){x.target.classList.add('shown');io.unobserve(x.target)}}),{threshold:.3});rows.forEach(r=>io.observe(r))}
 else rows.forEach(r=>r.classList.add('shown'));
})();

/* ───────── сцена ───────── */
const stage=$('stage'),toks=$('toks'),shadows=$('shadows'),tip=$('tip'),fx=$('fx'),post=$('post'),ctx=fx.getContext('2d');
if(!chosen.length){$('st-none').hidden=false;return}
let W=0,Hh=0,G=0,XM=0,HD=0,SC=1,GR=2000,dMin=50,dMax=110;
const T=[];
let seed=20261106;const rnd=()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296};
const outLab=m=>m.bi===0?'П1':m.bi===1?'Х':'П2';

chosen.forEach((m,i)=>{
 const a=document.createElement('a');
 a.className='tk '+(m.hockey?'h':'f');a.href=m.href;a.draggable=false;
 a.setAttribute('aria-label',`${m.hn} — ${m.an}, ${m.hm} МСК. Модель: ${outLab(m)}, ${H.pct(m.best)} %`);
 a.innerHTML=`<span class="tkb"><span class="rim"></span><span class="xface"><span class="pair"><span class="cr"><img src="${m.hc}" alt="" draggable="false"></span><span class="cr"><img src="${m.ac}" alt="" draggable="false"></span></span><b>${H.pct(m.best)}<small>%</small></b></span></span>`;
 toks.appendChild(a);
 const s=document.createElement('i');s.className='sh';shadows.appendChild(s);
 T.push({m,el:a,rim:a.firstChild.firstChild,sh:s,h:m.hockey,x:0,y:0,vx:0,vy:0,r:30,rot:rnd()*6.28,on:false,t0:0,drag:false,moved:0,cool:0,i});
});
/* порядок падения: хоккей и футбол вперемешку */
{const ord=T.map((_,i)=>i).sort(()=>rnd()-.5);ord.forEach((i,k)=>{T[i].t0=.15+k*.095+rnd()*.06})}

function layout(first){
 const r=stage.getBoundingClientRect(),ow=W,oh=Hh;
 const nw=r.width,nh2=r.height;
 if(!first&&Math.abs(nw-W)<2&&Math.abs(nh2-Hh)<2)return;
 W=nw;Hh=nh2;G=Math.round(Hh*.8);XM=W/2;HD=Math.round(Hh*.17);
 SC=clamp(Hh/700,.55,1.05);GR=2000*SC+400;
 dMin=clamp(W*.085,46,72);dMax=clamp(W*.185,88,152);
 post.style.top=(G-HD)+'px';post.style.height=HD+'px';
 fx.width=Math.round(W*Math.min(devicePixelRatio||1,1.5));fx.height=Math.round(Hh*Math.min(devicePixelRatio||1,1.5));
 T.forEach(t=>{
  const k=clamp((t.m.best-.34)/.5,0,1);
  const d=Math.round(dMin+(dMax-dMin)*Math.pow(k,.85));
  t.r=d/2;
  const px=t.el.style;px.width=px.height=d+'px';px.fontSize=(d/10)+'px';
  const s=t.sh.style;s.width=d*1.7+'px';s.height=d*.34+'px';
  if(!first&&ow){t.x=t.x/ow*W;t.y=t.y/oh*Hh}
 });
 if(first)T.forEach(t=>{
  const half=t.h?[t.r+8,XM-t.r-14]:[XM+t.r+14,W-t.r-8];
  t.x=half[0]+rnd()*Math.max(1,half[1]-half[0]);t.y=-t.r-12;t.vx=(rnd()-.5)*160;t.vy=120+rnd()*160;
 });
 wake();
}

/* ───────── физика ───────── */
const parts=[];
function burst(x,y,v,ice){
 if(RM)return;const n=Math.min(9,2+(v/110|0));
 for(let i=0;i<n&&parts.length<90;i++){const a=-Math.PI*(.12+.76*rnd());const s=(60+rnd()*160)*SC;
  parts.push({x:x+(rnd()-.5)*14,y:y,vx:Math.cos(a)*s,vy:Math.sin(a)*s,l:1,c:ice?'234,248,255':'150,240,190',z:1+rnd()*2.2})}
}
let time=0;
function substep(dt){
 time+=dt;
 for(const t of T){
  if(!t.on){if(time>=t.t0){t.on=true;t.el.classList.add('on-s')}else continue}
  t.cool-=dt;t.touch=false;
  if(t.drag){
   const nx=t.x+(t.tx-t.x)*Math.min(1,26*dt),ny=t.y+(t.ty-t.y)*Math.min(1,26*dt);
   t.vx=(nx-t.x)/dt;t.vy=(ny-t.y)/dt;t.x=nx;t.y=ny;continue;
  }
  t.vy+=GR*dt;
  t.vx*=Math.exp(-.05*dt);
  t.x+=t.vx*dt;t.y+=t.vy*dt;
  const ice=t.x<XM;
  /* пол */
  if(t.y+t.r>G){
   t.y=G-t.r;
   if(t.vy>0){
    const eK=t.h?(ice?.3:.2):(ice?.6:.68);
    if(t.vy>70*SC+30){if(t.vy>200)burst(t.x,G,t.vy,ice);t.vy=-t.vy*eK}else t.vy=0;
   }
   const mu=t.h?(ice?.2:3.4):(ice?.35:1.25);
   t.vx*=Math.exp(-mu*dt);t.touch=true;
  }
  /* стены */
  if(t.x-t.r<0){t.x=t.r;if(t.vx<0)t.vx=-t.vx*.5}
  if(t.x+t.r>W){t.x=W-t.r;if(t.vx>0)t.vx=-t.vx*.5}
  /* центральный борт (капсула) */
  {const cy=clamp(t.y,G-HD,G),dx=t.x-XM,dy=t.y-cy,dd=Math.hypot(dx,dy),rr=t.r+5;
   if(dd<rr&&dd>.001){const nx=dx/dd,ny=dy/dd;t.x+=nx*(rr-dd);t.y+=ny*(rr-dd);const vn=t.vx*nx+t.vy*ny;if(vn<0){t.vx-=1.4*vn*nx;t.vy-=1.4*vn*ny}t.touch=true}}
 }
 /* столкновения кругов */
 for(let it=0;it<3;it++){
  for(let a=0;a<T.length;a++){const p=T[a];if(!p.on)continue;
   for(let b=a+1;b<T.length;b++){const q=T[b];if(!q.on)continue;
    const dx=q.x-p.x,dy=q.y-p.y,rr=p.r+q.r;
    if(dx>rr||dx<-rr||dy>rr||dy<-rr)continue;
    const d2=dx*dx+dy*dy;if(d2>=rr*rr||d2<1e-6)continue;
    const d=Math.sqrt(d2),nx=dx/d,ny=dy/d,pen=rr-d;
    const ip=p.drag?0:1/(p.r*p.r),iq=q.drag?0:1/(q.r*q.r),is=ip+iq;if(!is)continue;
    p.x-=nx*pen*ip/is;p.y-=ny*pen*ip/is;q.x+=nx*pen*iq/is;q.y+=ny*pen*iq/is;
    const vn=(q.vx-p.vx)*nx+(q.vy-p.vy)*ny;
    if(vn<0){
     const e0=(vn<-60?(p.h&&q.h?.28:.5):0),j=-(1+e0)*vn/is;
     p.vx-=j*ip*nx;p.vy-=j*ip*ny;q.vx+=j*iq*nx;q.vy+=j*iq*ny;
     if(-vn>260&&!RM&&p.cool<=0){burst((p.x+q.x)/2,(p.y+q.y)/2,-vn*.5,p.x<XM);p.cool=q.cool=.15}
    }
    p.touch=q.touch=true;
   }}
 }
 for(const t of T){if(!t.on||t.drag)continue;
  if(t.touch&&Math.abs(t.vx)+Math.abs(t.vy)<26){const k=Math.exp(-6*dt);t.vx*=k;t.vy*=k}
 }
}
let raf=0,last=0,calm=0,hovered=null;
function render(dt){
 for(const t of T){
  if(!t.on)continue;
  const sp=t.vx/t.r*(t.h?.55:1);
  t.rot+=(sp+(RM?0:(t.h?.5:.35)))*dt;
  t.el.style.transform=`translate3d(${(t.x-t.r).toFixed(1)}px,${(t.y-t.r).toFixed(1)}px,0)`;
  t.rim.style.transform=`rotate(${t.rot.toFixed(3)}rad)`;
  const hgt=clamp((G-(t.y+t.r))/(Hh*.6),0,1),o=1-hgt*.85,w=1-hgt*.45;
  t.sh.style.opacity=t.y<-t.r?0:o.toFixed(2);
  t.sh.style.transform=`translate3d(${(t.x-t.r*.85).toFixed(1)}px,${(G-t.r*.12).toFixed(1)}px,0) scale(${w.toFixed(2)},1)`;
 }
 if(hovered)placeTip(hovered);
 /* частицы */
 if(parts.length||ctx._d){
  const k=fx.width/W;ctx.setTransform(k,0,0,k,0,0);ctx.clearRect(0,0,W,Hh);
  for(let i=parts.length-1;i>=0;i--){const p=parts[i];p.vy+=GR*.7*dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.l-=dt*1.9;
   if(p.l<=0||p.y>G+30){parts.splice(i,1);continue}
   ctx.fillStyle=`rgba(${p.c},${(p.l*.9).toFixed(2)})`;ctx.fillRect(p.x,p.y,p.z,p.z)}
  ctx._d=parts.length>0;
 }
}
function frame(ts){
 const dt=Math.min(.034,(ts-last)/1000||.016);last=ts;
 const n=2;for(let i=0;i<n;i++)substep(dt/n);
 render(dt);
 let mv=0,act=false;for(const t of T){if(!t.on){act=true;continue}mv=Math.max(mv,Math.abs(t.vx)+Math.abs(t.vy));if(t.drag)act=true}
 if(mv<4&&!act&&!parts.length){calm+=dt}else calm=0;
 if(calm>.8){raf=0;return}
 raf=requestAnimationFrame(frame);
}
function wake(){calm=0;if(RM){settle();return}if(!raf){last=performance.now();raf=requestAnimationFrame(frame)}}
function settle(){ /* без движения: фишки сразу лежат */
 time=1e3;T.forEach(t=>{t.on=true;t.el.classList.add('on-s')});
 for(let i=0;i<500;i++)substep(1/60);
 T.forEach(t=>{t.vx=t.vy=0});render(.016);
}

/* ───────── подпись при наведении ───────── */
let tipW=0,tipH=0;
function showTip(t){
 const m=t.m;
 tip.innerHTML=`<span class="t1">${m.hm} МСК · ${m.day==='сегодня'?'':m.day+' · '}${m.lgn}</span><b>${e(m.hn)} — ${e(m.an)}</b><span class="t3">Модель: ${outLab(m)}${m.bi===1?'':' ('+e(m.who)+')'} · ${H.pct(m.best)} %</span>`;
 tipW=tip.offsetWidth;tipH=tip.offsetHeight;hovered=t;t.el.classList.add('hov');tip.classList.add('on');placeTip(t);
}
function hideTip(t){if(hovered===t){hovered=null;tip.classList.remove('on')}t.el.classList.remove('hov')}
function placeTip(t){
 const lift=t.r*.18+4;let x=clamp(t.x-tipW/2,6,W-tipW-6),y=t.y-t.r-tipH-lift-8;
 if(y<6)y=Math.min(t.y+t.r+10,Hh-tipH-6);
 tip.style.transform=`translate3d(${x.toFixed(1)}px,${y.toFixed(1)}px,0)`;
}

/* ───────── указатель: толкать, бросать, нажать ───────── */
const local=ev=>{const r=stage.getBoundingClientRect();return[ev.clientX-r.left,ev.clientY-r.top]};
let flickPrev=null;
T.forEach(t=>{
 const el=t.el;
 el.addEventListener('dragstart',ev=>ev.preventDefault());
 el.addEventListener('pointerenter',ev=>{if(ev.pointerType!=='touch')showTip(t)});
 el.addEventListener('pointerleave',()=>{if(!t.drag)hideTip(t)});
 el.addEventListener('focus',()=>showTip(t));el.addEventListener('blur',()=>hideTip(t));
 el.addEventListener('pointerdown',ev=>{
  if(ev.button!==0&&ev.pointerType==='mouse')return;
  const [px,py]=local(ev);
  t.drag=true;t.moved=0;t.dx=px-t.x;t.dy=py-t.y;t.tx=t.x;t.ty=t.y;t.hist=[{t:ev.timeStamp,x:px,y:py}];t.down=ev.timeStamp;
  el.classList.add('drag');try{el.setPointerCapture(ev.pointerId)}catch(_){}
  showTip(t);wake();
 });
 el.addEventListener('pointermove',ev=>{
  if(!t.drag)return;
  const [px,py]=local(ev);
  t.tx=clamp(px-t.dx,t.r,W-t.r);t.ty=clamp(py-t.dy,-t.r,G-t.r);
  const h=t.hist,l=h[h.length-1];t.moved+=Math.hypot(px-l.x,py-l.y);
  h.push({t:ev.timeStamp,x:px,y:py});while(h.length>2&&ev.timeStamp-h[0].t>90)h.shift();
 });
 const up=ev=>{
  if(!t.drag)return;
  t.drag=false;el.classList.remove('drag');try{el.releasePointerCapture(ev.pointerId)}catch(_){}
  const h=t.hist,a=h[0],b=h[h.length-1],dtv=Math.max(.016,(b.t-a.t)/1000);
  const vmax=2600*SC;
  if(t.moved>7&&ev.type==='pointerup'){t.vx=clamp((b.x-a.x)/dtv,-vmax,vmax);t.vy=clamp((b.y-a.y)/dtv,-vmax,vmax)}
  if(ev.pointerType==='touch')hideTip(t);else if(!el.matches(':hover'))hideTip(t);
  wake();
 };
 el.addEventListener('pointerup',up);el.addEventListener('pointercancel',up);
 el.addEventListener('click',ev=>{if(t.moved>7)ev.preventDefault()});
});
/* быстрый взмах мышью — щелчок по фишке */
stage.addEventListener('pointermove',ev=>{
 if(ev.pointerType!=='mouse')return;
 const [px,py]=local(ev),n=ev.timeStamp;
 if(flickPrev){
  const dt=(n-flickPrev.t)/1000;
  if(dt>0&&dt<.1){
   const vx=(px-flickPrev.x)/dt,vy=(py-flickPrev.y)/dt,sp=Math.hypot(vx,vy);
   if(sp>650){
    for(const t of T){if(!t.on||t.drag||t.cool>0)continue;
     if(Math.hypot(t.x-px,t.y-py)<t.r+6){const k=.3*Math.min(1,sp/1800);t.vx+=vx*k;t.vy+=vy*k*.8-60*SC;t.cool=.25;wake()}}
   }
  }
 }
 flickPrev={t:n,x:px,y:py};
});
stage.addEventListener('pointerleave',()=>{flickPrev=null});
/* тычок в пустое место — волна, фишки подпрыгивают */
stage.addEventListener('pointerdown',ev=>{
 if(ev.target.closest('.tk'))return;
 const [px,py]=local(ev);let any=false;
 for(const t of T){if(!t.on||t.drag)continue;
  const dx=t.x-px,dy=t.y-py,d=Math.hypot(dx,dy);if(d>340*Math.max(SC,.7))continue;
  const f=1-d/(340*Math.max(SC,.7));t.vx+=dx/(d||1)*520*f*SC;t.vy-=(300+260*f)*f*SC+80;any=true}
 if(any)wake();
});
/* кнопки с игроками: наклон за курсором и «привет» от своей площадки */
document.querySelectorAll('.xdoor').forEach(d=>{
 const k=d.dataset.k;
 if(!RM){
  d.addEventListener('pointermove',ev=>{if(ev.pointerType==='touch')return;const r=d.getBoundingClientRect(),x=(ev.clientX-r.left)/r.width-.5,y=(ev.clientY-r.top)/r.height-.5;
   d.style.setProperty('--ry',(x*11).toFixed(1)+'deg');d.style.setProperty('--rx',(-y*9).toFixed(1)+'deg')});
  d.addEventListener('pointerleave',()=>{d.style.setProperty('--ry','0deg');d.style.setProperty('--rx','0deg');stage.classList.remove('hot-h','hot-f')});
 }
 d.addEventListener('pointerenter',ev=>{
  if(ev.pointerType==='touch')return;
  stage.classList.add(k==='h'?'hot-h':'hot-f');
  if(RM)return;let any=false;
  for(const t of T){if(!t.on||t.drag||t.h!==(k==='h'))continue;t.vy-=(330+rnd()*170)*SC;t.vx+=(rnd()-.5)*140;any=true}
  if(any)wake();
 });
 d.addEventListener('pointerleave',()=>stage.classList.remove('hot-h','hot-f'));
});

new ResizeObserver(()=>{if(W)layout(false)}).observe(stage);
layout(true);
if(RM)settle();
/* вкладка вернулась из фона: не прыгать на накопленный dt */
document.addEventListener('visibilitychange',()=>{if(!document.hidden)last=performance.now()});
window.__drop={T,wake};
})();
