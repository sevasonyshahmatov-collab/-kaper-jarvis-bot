/* «Раскол»: шов-диагональ едет за курсором / пальцем, сторона под ним выходит вперёд, нажатие — «влёт» в раздел. */
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const sp=$('sp'),ice=$('ice'),turf=$('turf'),fx=$('fx'),scr=$('scr'),veil=$('veil'),sg=$('sg'),sl=$('sl'),hI=$('hI'),hT=$('hT');
const SD={I:{half:ice,w:$('wI'),pl:$('plI'),u:$('uI'),hit:hI,asp:846/1100,over:.012,key:'ice'},
          T:{half:turf,w:$('wT'),pl:$('plT'),u:$('uT'),hit:hT,asp:493/900,over:.004,key:'turf'}};
/* игрок = обёртка (размытие через CSS-переход) + тёмная копия-силуэт, которой гасим яркость прозрачностью (дёшево для GPU) */
for(const K of['I','T']){const s=SD[K],im=s.pl,w=document.createElement('div');w.className='pw';
 im.parentNode.insertBefore(w,im);w.appendChild(im);const dk=im.cloneNode();dk.className='pd';dk.removeAttribute('id');w.appendChild(dk);s.pw=w;s.pd=dk;s.pl=w;s.im=[im,dk]}
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v)),lerp=(a,b,t)=>a+(b-a)*t;
let W=0,H=0,V=false,DPR=1;
const S={p:.5,t:.09,tp:.5,tt:.09,dive:0,win:0,lock:false};
let lastIn=-1e9,ptr={x:-999,y:-999},vis=true,side='';

/* ---------- данные: счётчики и список ближайших матчей ---------- */
(()=>{
 const Hm=window.HOME;if(!Hm||!Hm.J)return;
 const all=Hm.all();if(!all.length)return;
 const T=(()=>{const d=new Date(Date.now()+3*3600e3);return d.toISOString().slice(0,10)})();
 const cnt=(arr,el,fb)=>{const td=arr.filter(m=>m.t.slice(0,10)===T).length;
  el.textContent=td?`${td} ${Hm.pl(td,'матч','матча','матчей')} сегодня`:arr.length?`${arr.length} ${Hm.pl(arr.length,'матч','матча','матчей')} в ближайшие дни`:fb};
 cnt(all.filter(m=>m.hockey),$('cnt-h'),'КХЛ и НХЛ');cnt(all.filter(m=>!m.hockey),$('cnt-f'),'топ-лиги Европы');
 const e=Hm.esc,at=m=>Date.parse(m.t.replace(' ','T')+':00+03:00');
 const now=Date.now(),fresh=all.filter(m=>at(m)>now-2*3600e3),src=fresh.length?fresh:all;
 const rows=src.filter(m=>m.hockey).slice(0,4).concat(src.filter(m=>!m.hockey).slice(0,4)).sort((a,b)=>at(a)-at(b));
 $('td-upd').textContent=Hm.upd();
 $('td-list').innerHTML=rows.map(m=>{
  const k=m.ln&&m.bi>=0?[m.ln.p1,m.ln.x,m.ln.p2][m.bi]:null;
  const p=m.md?`<b class="${m.best>=.6?'hi':''}">${Hm.pct(m.best)}<small>%</small></b>`:'';
  return `<li class="${m.hockey?'ih':'if'}"><a href="${m.href}"><time>${m.hm}<small>${m.day==='сегодня'?m.lgn:m.day}</small></time>
   <span class="nm"><span><img src="${m.hc}" alt="" loading="lazy">${e(m.hn)}</span><span><img src="${m.ac}" alt="" loading="lazy">${e(m.an)}</span></span>
   <span class="pk">${p}${m.md?(m.bi===1?'ничья':e(m.who))+(k?', кэф '+Hm.f2(k):''):'расчёт скоро'}</span></a></li>`}).join('')||'<li class="td-soon">Матчей пока нет</li>';
})();

/* ---------- размеры ---------- */
const MS={wI:[1,1],wT:[1,1],uI:[1,1],uT:[1,1]};
function measure(){
 document.documentElement.style.setProperty('--hdh',($('hd').getBoundingClientRect().height||64)+'px');
 W=sp.clientWidth;H=sp.clientHeight;V=W<=760;DPR=Math.min(2,window.devicePixelRatio||1);
 for(const k of['I','T']){const s=SD[k];MS['w'+k]=[s.w.offsetWidth,s.w.offsetHeight];MS['u'+k]=[s.u.offsetWidth,s.u.offsetHeight];
  for(const i of s.im){i.style.height=H+'px';i.style.width=H*s.asp+'px'}s.pw.style.height=H+'px';s.pw.style.width=H*s.asp+'px'}
 fx.width=W*DPR;fx.height=H*DPR;
 drawScratches();seed();
 render(0);
}
function rnd(a){return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function drawScratches(){
 scr.width=W;scr.height=H;const c=scr.getContext('2d'),r=rnd(7);c.lineCap='round';
 for(let i=0;i<110;i++){const x=r()*W,y=r()*H,R=120+r()*Math.max(W,H)*.9,a=r()*6.28,sw=.18+r()*.7;
  c.strokeStyle=`rgba(235,248,255,${.03+r()*.1})`;c.lineWidth=.5+r()*1.1;c.beginPath();c.arc(x,y,R,a,a+sw);c.stroke()}
 for(let i=0;i<7;i++){const x=r()*W,y=r()*H,R=Math.max(W,H)*(1+r()),a=r()*6.28;
  c.strokeStyle='rgba(255,255,255,.07)';c.lineWidth=2.2;c.beginPath();c.arc(x,y,R,a,a+.25);c.stroke()}
 for(let i=0;i<26;i++){const x=r()*W,y=r()*H,g=c.createRadialGradient(x,y,0,x,y,7+r()*10);
  g.addColorStop(0,'rgba(255,255,255,.5)');g.addColorStop(1,'rgba(255,255,255,0)');c.fillStyle=g;c.fillRect(x-20,y-20,40,40)}
}

/* ---------- геометрия шва ---------- */
const off=()=>S.t*W*1.6;
const seamAt=(q,pc)=>V?pc*H+off()*(1-2*q/W):(pc+S.t)*W-2*S.t*W*q/H; /* q: y (десктоп) или x (телефон) */
function side_(x,y){const pc=S.p;return V?(y<seamAt(x,pc)?'ice':'turf'):(x<seamAt(y,pc)?'ice':'turf')}

/* ---------- кадр ---------- */

function render(){
 const d=S.dive,p=S.p,pc=clamp(p,.27,.73),t=S.t;
 /* обрезка половин и зон нажатия */
 let ci,ct,x1,y1,x2,y2;
 if(!V){const xt=(p+t)*W,xb=(p-t)*W;
  ci=`polygon(0 0,${xt}px 0,${xb}px ${H}px,0 ${H}px)`;ct=`polygon(${xt}px 0,${W}px 0,${W}px ${H}px,${xb}px ${H}px)`;x1=xt;y1=0;x2=xb;y2=H}
 else{const o=off(),yL=p*H+o,yR=p*H-o;
  ci=`polygon(0 0,${W}px 0,${W}px ${yR}px,0 ${yL}px)`;ct=`polygon(0 ${yL}px,${W}px ${yR}px,${W}px ${H}px,0 ${H}px)`;x1=0;y1=yL;x2=W;y2=yR}
 ice.style.clipPath=hI.style.clipPath=ci;hT.style.clipPath=ct;
 const dx=x2-x1,dy=y2-y1,L=Math.hypot(dx,dy)||1,ex=dx/L*30,ey=dy/L*30;
 for(const l of[sg,sl]){l.setAttribute('x1',x1-ex);l.setAttribute('y1',y1-ey);l.setAttribute('x2',x2+ex);l.setAttribute('y2',y2+ey)}
 sg.style.opacity=sl.style.opacity=d>0?String(1-d):'';
 const g=(pc-.5)/.2; /* вес льда, -1..1 */

 for(const K of['I','T']){
  const s=SD[K],isI=K==='I',f=isI?g:-g;let k=(clamp(f,-1,1)+1)/2;
  const win=S.win===(isI?1:-1);if(S.win)k=win?lerp(k,1,d):lerp(k,0,d);
  const [ww,wh]=MS['w'+K],[uw,uh]=MS['u'+K],pw0=H*s.asp;
  let cxW,yW,scW,cxP,s0,bot,cxU,yU,scU,opU=1;
  if(!V){
   yW=Math.max(.27*H,150);const sw=seamAt(yW,pc),av=isI?sw*.8:(W-sw)*.76;
   cxW=isI?sw*.4:sw+(W-sw)*.62;scW=Math.min(av/ww,.7+.5*k);
   const sp_=seamAt(.55*H,pc);cxP=isI?sp_*.66:sp_+(W-sp_)*.34;
   s0=(H-90)/H*(.8+.2*k)*(isI?1.02:.98);bot=H+s.over*H;
   const su=seamAt(.87*H,pc),au=(isI?su:W-su)*.8;cxU=isI?su*.4:su+(W-su)*.62;yU=.87*H;scU=Math.min(1,au/uw)*(.86+.14*k);
  }else{
   const o=off(),top0=86;
   cxW=W/2;scW=(W*.94/ww)*(.74+.26*k);
   if(isI){const bottom=pc*H-o-6;yW=top0+wh*scW/2+Math.max(0,(bottom-top0)*.04);
    const sy=seamAt(W*.62,pc);cxP=W*.64;s0=Math.max(.3,(sy-top0-18)/H)*(.8+.2*k);bot=sy+H*.004;
    cxU=W*.3;yU=Math.max(top0+wh*scW+uh/2+10,sy-uh/2-18);}
   else{const topT=pc*H+o+6;yW=Math.max(H-142,topT+wh*scW/2+6);
    const sy=seamAt(W*.36,pc);cxP=W*.36;s0=Math.max(.05,(H-sy-6)/H)*(.84+.16*k);bot=H+H*.004;
    cxU=W/2;yU=H-uh/2-34;}
   scU=Math.min(1,W*.46/uw);opU=clamp((k-.2)/.35,0,1);
  }
  /* влёт: победитель летит на камеру, проигравший гаснет */
  let sdv=s0,botY=bot,ox=cxP,wScale=scW,wop=1,pop=1;
  if(S.win){
   if(win){sdv=s0*(1+d*d*2.3);ox=lerp(cxP,W/2,d);botY=bot*(1-d)+(.4*H+sdv*pw0/s.asp*.78)*d;wScale=scW*(1+d*1.3);cxW=lerp(cxW,W/2,d);yW=lerp(yW,.5*H,d);wop=1-clamp((d-.5)*2,0,1)}
   else{wop=pop=1-d}
  }
  const uop=S.win?clamp(1-d*3,0,1):opU;
  s.w.style.zIndex=V&&!isI?3:1;
  s.w.style.transform=`translate3d(${cxW-ww/2}px,${yW-wh/2}px,0) scale(${wScale})`;s.w.style.opacity=wop;
  s.pl.style.transform=`translate3d(${ox-pw0/2}px,${botY-H}px,0) scale(${sdv})`;s.pl.style.opacity=pop;
  s.pd.style.opacity=(.62*(1-k)).toFixed(3);
  const far=k<.35;if(s.far!==far){s.far=far;s.pw.classList.toggle('far',far)}
  s.u.style.transform=`translate3d(${cxU-uw/2}px,${yU-uh/2}px,0) scale(${scU})`;s.u.style.opacity=uop;
  s.u.style.pointerEvents='none';
 }
}

/* ---------- частицы: снег на льду, пыльца на газоне, искры на шве ---------- */
const fc=fx.getContext('2d');let P=[];
function seed(){
 const r=rnd(11),n=clamp(Math.round(W*H/15000),34,100);P=[];
 for(let i=0;i<n;i++)P.push({x:r()*W,y:r()*H,vx:(r()-.5)*8,vy:6+r()*14,s:.8+r()*1.8,a:.25+r()*.45,k:0});
}
function spark(){const q=Math.random(),pc=S.p;let x,y;
 if(!V){y=q*H;x=seamAt(y,pc)}else{x=q*W;y=seamAt(x,pc)}
 const an=Math.random()*6.28,sp_=14+Math.random()*34;
 P.push({x,y,vx:Math.cos(an)*sp_,vy:Math.sin(an)*sp_-6,s:1+Math.random()*1.6,a:.9,k:1,life:.5+Math.random()*.7})}
function fxStep(dt){
 fc.setTransform(DPR,0,0,DPR,0,0);fc.clearRect(0,0,W,H);
 if(Math.random()<dt*28&&!S.lock)spark();
 const pc=S.p,hover=ptr.x>-900;
 for(let i=P.length-1;i>=0;i--){const q=P[i];
  if(q.k){q.life-=dt;if(q.life<=0){P.splice(i,1);continue}}
  if(hover){const dx=q.x-ptr.x,dy=q.y-ptr.y,d2=dx*dx+dy*dy;if(d2<14000&&d2>1){const f=(1-d2/14000)*160*dt/Math.sqrt(d2);q.vx+=dx*f;q.vy+=dy*f}}
  q.vx*=1-dt*.5;q.x+=q.vx*dt;q.y+=q.vy*dt*(q.k?1:1);
  if(!q.k){q.vy=lerp(q.vy,8+q.s*5,dt*.6);if(q.y>H+6)q.y=-6;if(q.x<-6)q.x=W+6;if(q.x>W+6)q.x=-6}
  const inIce=V?q.y<seamAt(q.x,pc):q.x<seamAt(q.y,pc);
  const a=q.k?q.a*clamp(q.life*2,0,1):q.a*(inIce?1:.8);
  fc.fillStyle=q.k?`rgba(255,221,120,${a})`:inIce?`rgba(225,243,255,${a})`:`rgba(235,255,190,${a*.8})`;
  fc.beginPath();fc.arc(q.x,q.y,q.s*(q.k?clamp(q.life*2,.4,1):1),0,6.283);fc.fill();
 }
}

/* ---------- цикл ---------- */
let prev=0;
function frame(now){
 requestAnimationFrame(frame);
 if(!vis)return;
 const dt=Math.min(.05,(now-prev)/1000||.016);prev=now;
 if(!S.lock){
  if(now-lastIn>2400){const t=now/1000;S.tp=.5+.075*Math.sin(t*.55);S.tt=.09+.016*Math.sin(t*.4+1)}
  const k=1-Math.exp(-dt*5.5);S.p=lerp(S.p,S.tp,k);S.t=lerp(S.t,S.tt,k);
  const sd=ptr.x>-900?side_(ptr.x,ptr.y):'';if(sd!==side){side=sd;sp.dataset.h=sd}
 }
 render();fxStep(dt);
}

/* ---------- ввод ---------- */
function point(cx,cy,touch){
 const r=sp.getBoundingClientRect(),x=cx-r.left,y=cy-r.top;ptr.x=x;ptr.y=y;lastIn=performance.now();
 const fx_=clamp(x/W,0,1),fy=clamp(y/H,0,1);
 /* под курсором — та половина, что растёт; шов уходит за её край, но качается вслед за движением */
 if(V&&touch){S.tp=clamp(.5+(fx_-.5)*1.1,.3,.7);S.tt=.09+(fx_-.5)*-.06} /* телефон: горизонтальный свайп (вертикальный листает страницу) */
 else if(V){S.tp=clamp(.5+(.5-fy)*.95,.3,.7);S.tt=.09+(fx_-.5)*.05}
 else{S.tp=clamp(.5+(.5-fx_)*.95,.3,.7);S.tt=.09+(fy-.5)*.04}
}
if(!RM){
 sp.addEventListener('pointermove',e=>{if(e.pointerType!=='touch')point(e.clientX,e.clientY)},{passive:true});
 sp.addEventListener('pointerleave',e=>{if(e.pointerType!=='touch'){ptr.x=ptr.y=-999;sp.dataset.h='';side='';lastIn=performance.now()-1200}},{passive:true});
 const tf=e=>{const t=e.touches[0];if(t)point(t.clientX,t.clientY,true)};
 sp.addEventListener('touchstart',tf,{passive:true});sp.addEventListener('touchmove',tf,{passive:true});
 sp.addEventListener('touchend',()=>{ptr.x=ptr.y=-999},{passive:true});
}
/* клавиатура: фокус на половине выводит её вперёд */
for(const K of['I','T']){const h=SD[K].hit;
 h.addEventListener('focus',()=>{if(h.matches(':focus-visible')){sp.dataset.f=SD[K].key;if(!RM){lastIn=performance.now();S.tp=K==='I'?.68:.32}}});
 h.addEventListener('blur',()=>{sp.dataset.f=''})}

/* влёт */
sp.addEventListener('click',e=>{
 const a=e.target.closest('.hit');if(!a||e.ctrlKey||e.metaKey||e.shiftKey||e.button>0)return;
 e.preventDefault();if(S.lock)return;
 const isI=a.dataset.s==='ice';S.lock=true;S.win=isI?1:-1;sp.classList.add('diving');veil.className='veil '+(isI?'ice':'turf');
 if(RM||!window.gsap){veil.style.transition='opacity .2s';veil.style.opacity=1;setTimeout(()=>{location.href=a.href},220);return}
 const tl=gsap.timeline({onComplete:()=>{location.href=a.href}});
 tl.to(S,{dive:1,duration:.95,ease:'power3.in'},0)
   .to(S,{p:isI?1.7:-.7,t:0,duration:.95,ease:'power3.in'},0)
   .to(veil,{opacity:1,duration:.28,ease:'power1.in'},.72);
});
addEventListener('pageshow',e=>{if(e.persisted||S.lock){S.lock=false;S.win=0;S.dive=0;S.p=S.tp=.5;veil.style.opacity=0;veil.style.transition='';sp.classList.remove('diving')}});

/* пауза, когда экран не виден */
if('IntersectionObserver'in window)new IntersectionObserver(es=>{vis=es[0].isIntersecting}).observe(sp);
let rt;addEventListener('resize',()=>{clearTimeout(rt);rt=setTimeout(measure,80)});
measure();if(document.fonts&&document.fonts.ready)document.fonts.ready.then(measure);
if(RM){S.p=.5;S.t=.09;render()}else requestAnimationFrame(frame);
})();
