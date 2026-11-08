/* «Ближайшие матчи» — три вида на выбор владельца: ?m=1 «Лицом к лицу», ?m=2 «Билеты», ?m=3 «Табло по времени».
   Данные — window.HOME (proto/home/common.js): тот же список, что на главной. Подписей минимум, без эффектов при наведении. */
(()=>{
'use strict';
const H=window.HOME,box=document.getElementById('mt');
if(!box)return;
const q=new URLSearchParams(location.search),V=['1','2','3'].includes(q.get('m'))?+q.get('m'):1;
document.documentElement.dataset.m=V;
document.querySelectorAll('.mt-sw a').forEach(a=>{if(+a.dataset.m===V)a.setAttribute('aria-current','true')});
if(!H||!H.J){box.innerHTML='<p class="mt-none">Матчи появятся после обновления данных.</p>';return}
const e=H.esc,f2=H.f2,pc=v=>H.pct(v);
const upd=document.getElementById('mt-upd');if(upd)upd.textContent=H.upd();

/* 8 ближайших: по 4 хоккея и футбола, по времени */
const all=H.all(),now=Date.now();
const by=(a,b)=>a.t<b.t?-1:a.t>b.t?1:0;
let L=all.filter(m=>m.hockey).slice(0,4).concat(all.filter(m=>!m.hockey).slice(0,4));
if(L.length<8){const s=new Set(L.map(m=>m.key));L=L.concat(all.filter(m=>!s.has(m.key)).slice(0,8-L.length))}
L.sort(by);
if(!L.length){box.innerHTML='<p class="mt-none">Сегодня матчей нет.</p>';return}

const crest=(src,cls)=>`<img class="${cls}" src="${src}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">`;
const kef=(m,i)=>{const ln=m.ln;if(!ln)return '';const v=[ln.p1,ln.x,ln.p2][i];return v?f2(v):''};
const OUT=['П1','Х','П2'];
const pick=m=>m.pr?{o:OUT[m.bi],p:pc(m.best),k:kef(m,m.bi),who:m.bi===1?'ничья':m.bi===0?m.hn:m.an}:null;
const when=m=>m.day==='сегодня'?m.hm:`${m.hm}<small>${e(m.day)}</small>`;

/* 1 — лицом к лицу: эмблемы крупно, полоса шансов модели П1 / Х / П2, кэф под своим исходом */
function v1(){
 return `<ul class="mt1">${L.map(m=>{
  const pr=m.pr;
  const bar=pr?`<div class="bar">${pr.map((p,i)=>p==null?'':`<i class="${i===m.bi?'on':''}" style="flex:${Math.max(p,.06)}"><b>${pc(p)}%</b><small>${OUT[i]}${kef(m,i)?' · '+kef(m,i):''}</small></i>`).join('')}</div>`:'<div class="bar none">расчёт скоро</div>';
  return `<li class="${m.hockey?'hk':'fb'}"><a href="${m.href}">
   <div class="fo">
    <span class="tm">${crest(m.hc,'cr')}<b>${e(m.hn)}</b></span>
    <span class="mid"><time>${when(m)}</time><em>${e(m.lgn)}</em></span>
    <span class="tm aw">${crest(m.ac,'cr')}<b>${e(m.an)}</b></span>
   </div>${bar}</a></li>`}).join('')}</ul>`;
}

/* 2 — билеты: корешок со временем, команды, справа исход модели крупно */
function v2(){
 return `<ul class="mt2">${L.map(m=>{const p=pick(m);
  return `<li class="${m.hockey?'hk':'fb'}"><a href="${m.href}">
   <div class="stub"><time>${when(m)}</time><em>${e(m.lgn)}</em></div>
   <div class="body">
    <span class="tm">${crest(m.hc,'cr')}<b>${e(m.hn)}</b></span>
    <span class="tm">${crest(m.ac,'cr')}<b>${e(m.an)}</b></span>
   </div>
   <div class="pk">${p?`<b>${p.p}<small>%</small></b><span>${p.o} · ${e(p.who)}</span>${p.k?`<em>${p.k}</em>`:''}`:'<span>расчёт скоро</span>'}</div>
  </a></li>`}).join('')}</ul>`;
}

/* 3 — табло по времени: слева час, справа матчи этого часа плитками */
function v3(){
 const g=[];L.forEach(m=>{const k=m.day+' '+m.hm;let x=g.find(y=>y.k===k);if(!x)g.push(x={k,m,list:[]});x.list.push(m)});
 return `<ol class="mt3">${g.map(x=>`<li><time>${x.m.hm}${x.m.day!=='сегодня'?`<small>${e(x.m.day)}</small>`:''}</time><div class="slot">${x.list.map(m=>{const p=pick(m);
  return `<a class="ch ${m.hockey?'hk':'fb'}" href="${m.href}">
   <span class="crs">${crest(m.hc,'cr')}${crest(m.ac,'cr')}</span>
   <span class="nm"><b>${e(m.hn)}</b><b>${e(m.an)}</b></span>
   ${p?`<span class="pk"><b>${p.p}%</b><small>${p.o}${p.k?' · '+p.k:''}</small></span>`:''}
  </a>`}).join('')}</div></li>`).join('')}</ol>`;
}
box.innerHTML=[v1,v2,v3][V-1]();
})();
