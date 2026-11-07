/* Шапка ?hh=9 «Плитки» (макет, 07.11), только хоккей. Подключается из hero2.js (JVH2.mount). Слева заголовок, кнопка, плашки лиг;
   справа бенто-сетка: «Матч дня» (самая уверенная модель) + до 6 плиток ближайшего игрового дня. Фон неподвижный (hero9.css). */
(()=>{
'use strict';
const H=window.JVH2;if(!H)return;
const {esc,f2,pct,plural,MON,BASE,BTN}=H;
const lgName={khl:'КХЛ',nhl:'НХЛ'};
const lgImg=k=>`<img class="h9-li" src="${BASE}../lg/${esc(k)}.webp" alt="" width="20" height="20">`;
const em=src=>`<span class="h9-e"><img src="${esc(src)}" alt="" width="64" height="64"></span>`;
const meta=(m,ref)=>{const d=m.t.slice(0,10),pre=d===ref?'':`${+d.slice(8)} ${MON[+d.slice(5,7)-1]} · `;return `${pre}${m.t.slice(11,16)} · ${lgName[m.lg]||m.lg}`};
const who=m=>m.top.i===0?m.hn:m.top.i===2?m.an:'Ничья';
const names=m=>`${esc(m.hn)} — ${esc(m.an)}`;
const BG=`<svg class="h9-rink" viewBox="0 0 1200 520" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false"><g fill="none" stroke="currentColor" stroke-width="2.5">
<rect x="20" y="20" width="1160" height="480" rx="180"/><path d="M600 20V500" stroke-width="7"/><path d="M420 20V500M780 20V500" stroke-width="9"/><path d="M95 40V480M1105 40V480"/>
<circle cx="600" cy="260" r="92"/><circle cx="240" cy="130" r="74"/><circle cx="240" cy="390" r="74"/><circle cx="960" cy="130" r="74"/><circle cx="960" cy="390" r="74"/>
<path d="M95 212A48 48 0 0 1 95 308M1105 212A48 48 0 0 0 1105 308"/></g>
<g fill="currentColor"><circle cx="600" cy="260" r="9"/><circle cx="240" cy="130" r="8"/><circle cx="240" cy="390" r="8"/><circle cx="960" cy="130" r="8"/><circle cx="960" cy="390" r="8"/><circle cx="500" cy="130" r="7"/><circle cx="500" cy="390" r="7"/><circle cx="700" cy="130" r="7"/><circle cx="700" cy="390" r="7"/></g></svg>`;

function big(m,ref){
 const t=m.top,cells=m.pr?[['П1',0],['Х',1],['П2',2]].map(([l,i])=>`<span class="h9-c${t&&t.i===i?' hit':''}"><i>${l}</i><b class="num">${pct(m.pr[i])}<small>%</small></b></span>`).join(''):'';
 return `<a class="h9-t h9-big" href="#matches" data-key="${esc(m.key)}"><span class="h9-pair">${em(m.hc)}${em(m.ac)}</span>
  <b class="h9-bn">${names(m)}</b><span class="h9-bm num">${esc(meta(m,ref))}</span>${cells?`<span class="h9-cs">${cells}</span>`:''}</a>`;
}
function small(m,ref){
 const t=m.top;
 return `<a class="h9-t h9-sm" href="#matches" data-key="${esc(m.key)}"><span class="h9-pair">${em(m.hc)}${em(m.ac)}</span>
  <span class="h9-tm">${names(m)}</span><span class="h9-mt num">${esc(meta(m,ref))}</span>
  ${t?`<span class="h9-pc num">${pct(t.p)}<small>%</small></span><span class="h9-bt"><i>${esc(who(m))}</i><b class="num">${t.k!=null?f2(t.k):'—'}</b></span>`:'<span class="h9-pc none">—</span>'}</a>`;
}

H.mount=(N,hero,M,S)=>{
 const conf=m=>m.top?m.top.p:-1;
 const day=M.day||[],t0=M.top||day[0]||null;
 const rest=t0?day.filter(m=>m!==t0).sort((a,b)=>conf(b)-conf(a)).slice(0,6).sort((a,b)=>a.t<b.t?-1:1):[];
 const ref=t0?t0.t.slice(0,10):'';
 const cnt=k=>(M.base||[]).filter(m=>m.t.slice(0,10)===M.d0&&m.lg===k).length;
 const pills=['khl','nhl'].map(k=>{const n=cnt(k);return `<a class="h9-pill" href="league.html?lg=${k}">${lgImg(k)}<b>${lgName[k]}</b><span class="num">${n?`${n} ${plural(n,'матч','матча','матчей')}`:'нет матчей'}</span></a>`}).join('');
 const grid=t0?`<div class="h9-grid${rest.length%2?' odd':''}">${big(t0,ref)}${rest.map(m=>small(m,ref)).join('')}</div>`:`<div class="h9-grid"><div class="h9-t h9-none"><b>Ближайших матчей нет</b></div></div>`;
 const root=document.createElement('div');root.className='h9';root.dataset.sp=S;
 root.innerHTML=`<div class="h9-bg" aria-hidden="true">${BG}</div><div class="h9-in"><div class="h9-l"><h1 class="h9-h"><span>${esc(M.h[0])}</span> <span>${esc(M.h[1])}</span></h1>
  <p class="h9-sub">Вероятность каждого исхода считает модель.</p>${BTN}<div class="h9-pills">${pills}</div></div>${grid}</div>`;
 hero.append(root);
 /* страницы матчей: адреса из data/matchlinks.js; пока файл не пришёл, плитка ведёт на список «Матчи» ниже */
 const link=()=>{const L=window.JV_MATCHLINKS||{};root.querySelectorAll('a[data-key]').forEach(a=>{const u=L[a.dataset.key];if(u)a.href='../'+u})};
 if(window.JV_MATCHLINKS)link();else{const s=document.createElement('script');s.src=BASE+'../../data/matchlinks.js';s.onload=link;document.head.append(s)}
};
})();
