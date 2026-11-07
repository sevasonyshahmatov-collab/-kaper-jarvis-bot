/* Шапки ?hh=6 «Протокол» и ?hh=7 «Космос» (макет, 07.11) для хоккея, футбола и главной. Вызывается из hero2.js (JVH2.mount).
   6 — светлый монохром: тонкий огромный заголовок, лист-протокол печатается при прокрутке (липкая сцена).
   7 — тёмная шапка с лентой WebGL (ribbon.js), курсивное слово в заголовке, строка «Сегодня N матчей», матч дня тонкой строкой. */
(()=>{
'use strict';
const H=window.JVH2;if(!H)return;
const {esc,f2,pct,plural,left,mskDay,MON,LGN,LGP,cdStr,BASE,RM,HOME}=H;
const $=(r,s)=>r.querySelector(s);
const lab=t=>{if(t.s==='ТБ'||t.s==='ТМ'){const x=/(\d+[.,]?\d*)\s*$/.exec(t.word);return t.s+(x?' '+x[1]:'')}return t.s};
const dayLbl=t=>{const d=t.slice(0,10),n=mskDay(Date.now());if(d===n)return '';if(d===mskDay(Date.now()+864e5))return 'завтра';return `${+d.slice(8)} ${MON[+d.slice(5,7)-1]}`};
const ddmm=()=>{const n=mskDay(Date.now());return n.slice(8)+'.'+n.slice(5,7)};
const ru=n=>`${n} ${plural(n,'матч','матча','матчей')}`;
const TG='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 3.2 2.9 10.4c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.7c.3-1.3-.5-1.9-1.4-1.5ZM8.3 13.2l9.6-6c.5-.3.9-.1.5.2l-8.2 7.4-.3 3.4-1.6-5Z"/></svg>';
const CTA=`<a class="btn btn-tg" href="https://t.me/jarvibet" target="_blank" rel="noopener">${TG}<span>Получать прогнозы — бесплатно</span></a>`;

/* на главной старая шапка скрыта стилями; якорь «Сегодня» переносим на новый блок */
function hideOld(hero){if(!HOME)return;const a=hero.querySelector('aside#today');if(a)a.removeAttribute('id')}

/* выборка протокола: ближайшие дни, пока не наберётся 6; до 12 самых уверенных, по времени */
function pickList(M){
 const all=M.base.filter(m=>m.top),days=[...new Set(all.map(m=>m.t.slice(0,10)))];
 let p=[];for(const d of days){p=p.concat(all.filter(m=>m.t.slice(0,10)===d));if(p.length>=6)break}
 const n=p.length;
 if(p.length>12)p=p.slice().sort((a,b)=>b.top.p-a.top.p).slice(0,12);
 p.sort((a,b)=>a.t<b.t?-1:1);
 return {p,n};
}
const nextOf=M=>M.base.find(m=>left(m.t)>0)||null;

/* ═══ 6. Протокол ═══ */
const barcode=seed=>{let h=2166136261;for(const c of seed){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}
 const rnd=()=>{h^=h<<13;h^=h>>>17;h^=h<<5;return (h>>>0)/4294967296};let x=0,s='',d='';
 while(x<236){const w=1+Math.floor(rnd()*3.4),g=1+Math.floor(rnd()*2.6);s+=`<rect x="${x}" y="0" width="${w}" height="46"/>`;x+=w+g}
 for(let i=0;i<12;i++)d+=Math.floor(rnd()*10);
 return {svg:`<svg viewBox="0 0 ${x} 46" preserveAspectRatio="none" fill="#111110" aria-hidden="true">${s}</svg>`,digits:d.replace(/(\d{4})(?=\d)/g,'$1 ')}};

function v6(hero,M,S){
 const {p,n}=pickList(M);
 const sp={hockey:'КХЛ и НХЛ',football:'топ-лиги',home:''};
 const lead=`Модель разыгрывает каждый матч${sp[S]?' '+sp[S]:''} тысячи раз. Прокрутите: справа печатается протокол дня — исход, вероятность и кэф по каждой игре.`;
 const lgs=[...new Set(p.map(m=>LGN[m.lg]||m.lg))];
 const built=window.JVL&&window.JVL.TD&&window.JVL.TD.built;
 const root=document.createElement('div');root.className='h6';root.dataset.sp=S;if(HOME)root.id='today';
 let html=`<div class="pr-r pr-top"><b>JARVIS · ПРОТОКОЛ · ${ddmm()}</b><span>прогнозы по расчёту модели</span></div>`;
 let gk='';
 for(const m of p){
  const k=m.t.slice(0,10)+m.lg;
  if(k!==gk){gk=k;html+=`<div class="pr-r pr-h"><span>${esc(LGN[m.lg]||m.lg)}</span><span>${esc(dayLbl(m.t))}</span></div>`}
  html+=`<div class="pr-r pr-m${m.top.p>=.6?' hi':''}"><time>${m.t.slice(11,16)}</time><span class="tm">${esc(m.hn)} — ${esc(m.an)}</span><span class="pk"><b>${esc(lab(m.top))} ${pct(m.top.p)}%</b><i>${m.top.k?f2(m.top.k):'—'}</i></span></div>`;
 }
 if(!p.length)html+='<p class="pr-r pr-none">Расчёт на ближайшие матчи появится утром.</p>';
 else{
  const avg=Math.round(p.reduce((s,m)=>s+m.top.p,0)/p.length*100),bc=barcode(p.map(m=>m.lg+m.t+m.hn).join('|'));
  html+=`<div class="pr-r pr-tot">Итого: <b>${ru(p.length)}</b>${n>p.length?` из ${n}`:''}<br>средняя уверенность <b>${avg}&nbsp;%</b></div>
  <div class="pr-r pr-bar">${bc.svg}<span>${bc.digits}</span></div>
  <div class="pr-r pr-cta">${CTA}</div>`;
 }
 const cnt=s=>M.base.filter(m=>m.top&&m.sp===s).length,nh=cnt('h'),nf=cnt('f');
 const arrow='<svg viewBox="0 0 40 20" fill="none" stroke="currentColor" stroke-width="1.2" aria-hidden="true"><path d="M0 10h37M30 3l7 7-7 7"/></svg>';
 const doors=HOME?`<div class="pr-doors"><a class="pr-door" href="hockey/index.html"><span class="pr-dn">Хоккей</span><span class="pr-dc">${nh?ru(nh)+' с расчётом':'КХЛ · НХЛ'}</span>${arrow}</a><a class="pr-door" href="football/index.html"><span class="pr-dn">Футбол</span><span class="pr-dc">${nf?ru(nf)+' с расчётом':'топ-лиги Европы'}</span>${arrow}</a></div>`:'';
 root.innerHTML=`<section class="pr-scene" aria-label="Протокол дня"><div class="pr-stage">
  <div class="pr-left"><h1 class="pr-ht"><span>${esc(M.h[0])}</span><span>${esc(M.h[1])}</span></h1>
   <div class="pr-bt"><p class="pr-lede">${lead}</p>
    <div class="pr-meta"><p>${ddmm()}<br>${built?`модель обновлена ${esc(built.slice(11,16))} МСК`:'модель обновлена'}</p>
     <p>${lgs.slice(0,3).map(esc).join(' · ')||'КХЛ · НХЛ'}${lgs.length>3?'<br>'+lgs.slice(3,6).map(esc).join(' · '):''}</p>
     <p class="pr-cnt" aria-hidden="true">напечатано<br><b class="pr-n">00</b> / ${String(p.length).padStart(2,'0')}</p></div></div></div>
  <div class="pr-rc"><div class="pr-sway"><div class="pr-feed"><i class="pr-clip" aria-hidden="true"></i><div class="pr-zig top" aria-hidden="true"></div>
   <article class="pr-sheet" aria-label="Протокол дня"><div class="pr-body">${html}</div></article><div class="pr-zig" aria-hidden="true"></div></div></div></div>
 </div></section>${doors}`;
 hero.append(root);hideOld(hero);
 sheet(root,p.length);
}

function sheet(root,total){
 const scene=$(root,'.pr-scene'),stage=$(root,'.pr-stage'),sh=$(root,'.pr-sheet'),feed=$(root,'.pr-feed'),rc=$(root,'.pr-rc'),body=$(root,'.pr-body'),cn=$(root,'.pr-n'),ht=$(root,'.pr-ht');
 const steps=[...body.children],hd=document.getElementById('hd');
 /* заголовок: самая длинная строка занимает ширину колонки */
 const fit=()=>{const box=ht.parentNode;ht.style.fontSize='100px';const w=box.clientWidth;let m=0;
  ht.querySelectorAll('span').forEach(s=>{s.style.display='inline-block';m=Math.max(m,s.getBoundingClientRect().width);s.style.display=''});
  const cap=innerWidth<=900?innerWidth*.14:innerWidth*.088;ht.style.fontSize=Math.max(34,Math.min(cap,100*w/Math.max(1,m)*.99))+'px'};
 const geo=()=>{const top=hd?hd.offsetHeight:0,y=scene.getBoundingClientRect().top+scrollY;
  document.documentElement.style.setProperty('--hh',top+'px');
  const h=Math.max(540,innerHeight-Math.max(top,Math.min(y,innerHeight*.4)));
  stage.style.setProperty('--sh',h+'px');scene.style.setProperty('--run',Math.round(innerHeight*1.0+steps.length*16)+'px');return top};
 if(RM){sh.style.height='auto';cn.textContent=String(total).padStart(2,'0');geo();fit();addEventListener('resize',()=>{geo();fit()});return}
 let ends=[],avail=0,cur=0,raf=0,hh=0;
 const measure=()=>{fit();hh=geo();ends=steps.map(s=>s.offsetTop+s.offsetHeight);avail=rc.clientHeight-22};
 const frame=()=>{raf=0;
  const r=scene.getBoundingClientRect(),run=r.height-stage.offsetHeight,p=Math.min(1,Math.max(0,(hh-r.top)/Math.max(1,run)));
  const n=steps.length,k=Math.max(Math.min(3,n),Math.ceil(Math.min(1,p/.86)*n-1e-6)),tgt=ends[k-1]||0;
  cur+=(tgt-cur)*.2;if(Math.abs(tgt-cur)<.4)cur=tgt;
  sh.style.height=cur+'px';const off=Math.max(0,cur-avail);feed.style.transform=off?`translate3d(0,${-off}px,0)`:'';
  let c=0;for(const s of steps)if(s.classList.contains('pr-m')&&s.offsetTop+s.offsetHeight<=cur+1)c++;
  const v=String(c).padStart(2,'0');if(cn.textContent!==v)cn.textContent=v;
  if(cur!==tgt)raf=requestAnimationFrame(frame)};
 const kick=()=>{if(!raf)raf=requestAnimationFrame(frame)};
 addEventListener('scroll',kick,{passive:true});
 addEventListener('resize',()=>{measure();kick()});
 document.fonts&&document.fonts.ready.then(()=>{measure();kick()});
 measure();kick();
}

/* ═══ 7. Космос ═══ */
function v7(hero,M,S){
 const [l1,l2]=M.h,w=l2.split(' '),last=w.pop();
 const h1=S==='home'?'Прогнозы по <em>расчёту</em>,<br>а не наугад':`${esc(l1)}:<br>${esc(w.join(' '))}${w.length?' ':''}<em>${esc(last)}</em>`;
 const t=M.top;
 const root=document.createElement('div');root.className='h7';root.dataset.sp=S;if(HOME)root.id='today';
 const strip=()=>{const x=nextOf(M);return `${M.nowDay?'Сегодня':'В ближайший день'} ${ru(M.total)}${x?` · ближайший через ${cdStr(x)}`:''}`};
 const day=!t?'':`<a class="cs-md" href="${HOME?(t.sp==='f'?'football':'hockey')+'/index.html':'#matches'}"><span class="cs-mt"><time class="num">${t.t.slice(11,16)}</time>${LGP(t.lg)}</span><b class="cs-mm">${esc(t.hn)} — ${esc(t.an)}</b><span class="cs-mo">${esc(t.top.word)}</span><span class="cs-mp num">${pct(t.top.p)} %</span><span class="cs-mk num">${f2(t.top.k)}</span></a>`;
 const go=HOME?'<div class="cs-go"><a href="hockey/index.html">Хоккей <span aria-hidden="true">→</span></a><a href="football/index.html">Футбол <span aria-hidden="true">→</span></a></div>':'';
 root.innerHTML=`<div class="cs-top"><canvas class="cs-cv" aria-hidden="true"></canvas>
  <div class="cs-in"><div class="cs-copy"><h1 class="cs-h">${h1}</h1><p>Вероятность каждого исхода считает модель. Прогнозы приходят в Telegram до матча.</p>${CTA}</div>
  <p class="cs-strip" id="cs-strip">${strip()}</p></div></div>
  <div class="cs-bar">${day}${go}</div><div class="cs-fade" aria-hidden="true"></div>`;
 hero.append(root);hideOld(hero);
 const el=$(root,'#cs-strip');setInterval(()=>{if(!document.hidden)el.textContent=strip()},30000);
 const s=document.createElement('script');s.src=BASE+'ribbon.js';
 s.onload=()=>window.JVRibbon&&window.JVRibbon.mount($(root,'.cs-top'),$(root,'.cs-cv'),S==='football'?'pitch':'ice');
 document.head.append(s);
}

H.mount=(N,hero,M,S)=>{(N===6?v6:v7)(hero,M,S)};
})();
