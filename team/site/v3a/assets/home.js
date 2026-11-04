/* JARVIS v3a — первый экран главной: ближайшие матчи из data/today.js + lines.js + model.js (читаются через assets/lines.js, window.JVL). */
(()=>{
'use strict';
const q=new URLSearchParams(location.search);
const V=q.get('v')==='2'?2:1;
document.documentElement.dataset.v=V;
const J=window.JVL;
const $=id=>document.getElementById(id);
const TDAT=(J&&J.TD)||{matches:[]};
const esc=J?J.esc:s=>String(s);
const pl=(n,a,b,c)=>{const k=n%100,j=n%10;return k>10&&k<20?c:j===1?a:j>1&&j<5?b:c};
const mskNow=()=>new Date(Date.now()+3*3600e3);
const ymd=d=>d.toISOString().slice(0,10);
const atMs=t=>Date.parse(String(t).replace(' ','T')+':00+03:00');
const isH=m=>m.lg==='khl'||m.lg==='nhl';
const LG={khl:'КХЛ',nhl:'НХЛ',epl:'АПЛ',laliga:'Ла Лига',seriea:'Серия А',bundesliga:'Бундеслига',ligue1:'Лига 1',rpl:'РПЛ',ucl:'Лига чемпионов',uel:'Лига Европы'};
const crest=(m,s)=>`assets/${isH(m)?'em':'fc'}/${encodeURIComponent(s)}.webp`;
const dayLbl=(t,today)=>{const d=t.slice(0,10);if(d===today)return '';const tm=ymd(new Date(Date.parse(today+'T00:00:00Z')+864e5));return d===tm?'завтра':J.ddmm(t)};

const T=ymd(mskNow());
$('hm-date').textContent=mskNow().toLocaleDateString('ru-RU',{weekday:'long',day:'numeric',month:'long',timeZone:'UTC'}).replace(/^./,c=>c.toUpperCase());
const all=(TDAT.matches||[]).filter(m=>m.t&&m.h&&m.a);

/* счётчики на кнопках-входах */
(()=>{
 const cnt=(arr,el,fallback)=>{const td=arr.filter(m=>m.t.slice(0,10)===T).length;
  el.textContent=td?`${td} ${pl(td,'матч','матча','матчей')} сегодня`:arr.length?`${arr.length} ${pl(arr.length,'матч','матча','матчей')} в ближайшие дни`:fallback};
 cnt(all.filter(isH),$('cnt-h'),'КХЛ и НХЛ');cnt(all.filter(m=>!isH(m)),$('cnt-f'),'топ-лиги Европы');
})();

/* выбор 6 ближайших: по 3 хоккея и футбола (в футболе — Лига чемпионов впереди), по времени */
function pick(){
 const now=Date.now(),fresh=all.filter(m=>atMs(m.t)>now-2*3600e3);
 const src=fresh.length?fresh:all;
 const by=(a,b)=>atMs(a.t)-atMs(b.t);
 const rank=m=>m.lg==='ucl'?0:m.lg==='uel'?2:1;
 const h=src.filter(isH).sort(by).slice(0,3);
 const f=src.filter(m=>!isH(m)).sort((a,b)=>by(a,b)||rank(a)-rank(b)).slice(0,3);
 let r=h.concat(f);
 if(r.length<6){const seen=new Set(r.map(m=>m.key));r=r.concat(src.filter(m=>!seen.has(m.key)).sort(by).slice(0,6-r.length))}
 return r.sort(by);
}
const f2=v=>J.f2(v);
function row(m){
 const ln=J.L[m.key],md=J.M[m.key],hockey=isH(m);
 const d=dayLbl(m.t,T),hm=m.t.slice(11,16);
 let qs='',info='';
 if(ln){
  const fl=J.fair(ln),mx=fl?Math.max(...fl):0;
  const cells=[['П1',ln.p1,0],['Х',ln.x,1],['П2',ln.p2,2]].filter(c=>c[1]);
  qs=`<div class="hm-q" aria-label="Линия: ${cells.map(c=>c[0]+' '+f2(c[1])).join(', ')}">${cells.map(c=>`<i class="${fl&&fl[c[2]]===mx?'fav':''}"><small>${c[0]}</small>${f2(c[1])}</i>`).join('')}</div>`;
  info+=`<span>Линия: ${esc(J.srcLabel(ln))}</span>`;
 }
 if(md){
  const arr=[['П1',md.p1],['Х',md.x],['П2',md.p2]].filter(c=>c[1]!=null&&!(c[0]==='Х'&&ln&&!ln.x&&hockey&&false)),best=arr.reduce((a,b)=>b[1]>a[1]?b:a);
  const who=best[0]==='П1'?m.hn:best[0]==='П2'?m.an:'ничья';
  info=`<span>Модель: <b>${best[0]} · ${J.p0(best[1])}&nbsp;%</b> (${esc(who)})</span>`+info;
 }
 if(!ln&&!md)info='<span>Линия и расчёт — скоро</span>';
 return `<li><a class="hm-row" href="${hockey?'hockey':'football'}/index.html#matches" aria-label="${esc(m.hn)} — ${esc(m.an)}, ${hm} МСК">
  <div class="hm-t">${hm}<small>${d||'МСК'}</small></div>
  <div class="hm-m"><div class="hm-tm"><img src="${crest(m,m.h)}" alt="" width="24" height="24" loading="lazy"><span>${esc(m.hn)}</span></div><div class="hm-tm"><img src="${crest(m,m.a)}" alt="" width="24" height="24" loading="lazy"><span>${esc(m.an)}</span></div></div>
  ${qs}
  <div class="hm-info"><span class="hm-tag">${esc(LG[m.lg]||m.lg)}</span>${info}</div></a></li>`;
}
function render(){
 const list=$('hm-list');
 if(!J||!all.length){list.innerHTML='<li class="hm-soon">Скоро: матчи с расчётом модели появятся после ближайшего обновления данных.</li>';return}
 list.innerHTML=pick().map(row).join('');
 const b=TDAT.built;
 $('hm-upd').textContent=b?`данные: ${J.ddmm(b)} в ${b.slice(11,16)} МСК`:'';
}
render();
})();
