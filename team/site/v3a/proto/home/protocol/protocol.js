/* «Протокол дня»: матчи дня печатаются на чеке по мере прокрутки. Данные — те же, что на главной (common.js). */
(()=>{
const H=window.HOME,$=id=>document.getElementById(id);
if(!H||!H.J)return;
const e=H.esc,J=H.J;
const mskNow=new Date(Date.now()+3*3600e3);
const ddmm=`${String(mskNow.getUTCDate()).padStart(2,'0')}.${String(mskNow.getUTCMonth()+1).padStart(2,'0')}`;
const built=J.TD&&J.TD.built;

/* выборка: матчи с расчётом; ближайшие дни, пока не наберётся 6; до 14 — самые уверенные, по времени */
const all=H.all().filter(m=>m.md&&m.bi>=0);
const days=[...new Set(all.map(m=>m.t.slice(0,10)))];
let pick=[];
for(const d of days){pick=pick.concat(all.filter(m=>m.t.slice(0,10)===d));if(pick.length>=6)break}
if(pick.length>14)pick=pick.slice().sort((a,b)=>b.best-a.best).slice(0,14);
pick.sort((a,b)=>a.t<b.t?-1:a.t>b.t?1:0);

$('pr-date').textContent=H.dateStr();
$('pr-upd').textContent=built?`модель обновлена ${built.slice(11,16)} МСК`:'модель обновлена';
const lgs=[...new Set(pick.map(m=>m.lgn))];
$('pr-lg').innerHTML=lgs.length?lgs.slice(0,3).map(e).join(' · ')+(lgs.length>3?'<br>'+lgs.slice(3,6).map(e).join(' · '):''):'КХЛ · НХЛ';
const nh=all.filter(m=>m.hockey).length,nf=all.length-nh;
if(nh)$('cnt-h').textContent=`${nh} ${H.pl(nh,'матч','матча','матчей')} с расчётом`;
if(nf)$('cnt-f').textContent=`${nf} ${H.pl(nf,'матч','матча','матчей')} с расчётом`;

/* штрих-код из ключей матчей: одинаковые данные дают одинаковый рисунок */
function barcode(seed){
 let h=2166136261;for(const c of seed){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}
 const rnd=()=>{h^=h<<13;h^=h>>>17;h^=h<<5;return (h>>>0)/4294967296};
 let x=0,s='',digits='';
 while(x<236){const w=1+Math.floor(rnd()*3.4),g=1+Math.floor(rnd()*2.6);s+=`<rect x="${x}" y="0" width="${w}" height="46"/>`;x+=w+g}
 for(let i=0;i<12;i++)digits+=Math.floor(rnd()*10);
 return {svg:`<svg viewBox="0 0 ${x} 46" preserveAspectRatio="none" fill="#111110" aria-hidden="true">${s}</svg>`,digits:digits.replace(/(\d{4})(?=\d)/g,'$1 ')};
}

const row=m=>{
 const k=m.ln?[m.ln.p1,m.ln.x,m.ln.p2][m.bi]:null;
 const lab=m.bi===0?'П1':m.bi===1?'Х':'П2';
 return `<div class="pr-r pr-m${m.best>=.6?' hi':''}"><time>${m.hm}</time><span class="tm">${e(m.hn)} — ${e(m.an)}</span><span class="pk"><b>${lab} ${H.pct(m.best)}%</b><i>${k?H.f2(k):'—'}</i></span></div>`;
};
let html=`<div class="pr-r pr-top"><b>JARVIS · ПРОТОКОЛ · ${ddmm}</b><span>прогнозы по расчёту модели</span></div>`;
let gk='';
for(const m of pick){
 const k=m.t.slice(0,10)+m.lg;
 if(k!==gk){gk=k;html+=`<div class="pr-r pr-h"><span>${e(m.lgn)}</span><span>${m.day==='сегодня'?'':m.day}</span></div>`}
 html+=row(m);
}
if(!pick.length)html+='<p class="pr-r pr-none">Расчёт на ближайшие матчи появится утром.</p>';
else{
 const avg=Math.round(pick.reduce((s,m)=>s+m.best,0)/pick.length*100),n=pick.length;
 const bc=barcode(pick.map(m=>m.key).join('|'));
 html+=`<div class="pr-r pr-tot">Итого: <b>${n} ${H.pl(n,'матч','матча','матчей')}</b><br>средняя уверенность <b>${avg}&nbsp;%</b></div>
 <div class="pr-r pr-bar">${bc.svg}<span>${bc.digits}</span></div>
 <div class="pr-r pr-cta"><a class="btn btn-tg" href="https://t.me/jarvibet" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 3.2 2.9 10.4c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.7c.3-1.3-.5-1.9-1.4-1.5ZM8.3 13.2l9.6-6c.5-.3.9-.1.5.2l-8.2 7.4-.3 3.4-1.6-5Z"/></svg>Получать прогнозы — бесплатно</a></div>`;
}
const hd=document.getElementById('hd');
const setHH=()=>{if(hd)document.documentElement.style.setProperty('--hh',hd.offsetHeight+'px')};setHH();
const body=$('body'),sheet=$('sheet'),feed=$('feed'),rc=$('rc'),scene=$('scene');
body.innerHTML=html;
const steps=[...body.children];
$('pr-N').textContent=String(pick.length).padStart(2,'0');

const still=matchMedia('(prefers-reduced-motion: reduce)').matches;
if(still){sheet.style.height='auto';$('pr-n').textContent=String(pick.length).padStart(2,'0');return}

let ends=[],avail=0,cur=0,tgt=0,raf=0,stepsShown=0;
function measure(){
 ends=steps.map(s=>s.offsetTop+s.offsetHeight);
 avail=rc.clientHeight-14-8;
}
function target(){
 const r=scene.getBoundingClientRect(),run=r.height-innerHeight;
 const p=Math.min(1,Math.max(0,-r.top/Math.max(1,run)));
 const f=Math.min(1,p/.86),n=steps.length;
 const k=Math.max(1,Math.ceil(f*n-1e-6));
 const last=ends[k-1]||0;
 /* высота листа — до конца напечатанной строки; ниже подтягиваем лист вверх, чтобы свежая строка была на виду */
 return {h:last,k:Math.min(k,pick.length+0)};
}
function frame(){
 raf=0;
 const t=target();tgt=t.h;
 cur+=(tgt-cur)*.2;if(Math.abs(tgt-cur)<.4)cur=tgt;
 sheet.style.height=cur+'px';
 const off=Math.max(0,cur-avail);
 feed.style.transform=off?`translate3d(0,${-off}px,0)`:'';
 /* счётчик: сколько матчей уже на листе */
 let c=0;for(const s of steps)if(s.classList.contains('pr-m')&&s.offsetTop+s.offsetHeight<=cur+1)c++;
 const el=$('pr-n');const v=String(c).padStart(2,'0');if(el.textContent!==v)el.textContent=v;
 if(cur!==tgt)raf=requestAnimationFrame(frame);
}
const kick=()=>{if(!raf)raf=requestAnimationFrame(frame)};
addEventListener('scroll',kick,{passive:true});
addEventListener('resize',()=>{setHH();measure();kick()});
document.fonts&&document.fonts.ready.then(()=>{measure();kick()});
setHH();measure();kick();
})();
