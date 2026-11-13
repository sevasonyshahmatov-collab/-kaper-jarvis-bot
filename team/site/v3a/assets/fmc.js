/* Страница матча (футбол): блок «Сравнение команд» (владелец 13.11, по образцу хоккейного assets/mc.js).
   Данные — football/data/football-club.js (таблица чемпионата: игры, голы, очки; raw[2] — очки за игру в последних 5, raw[3] / raw[4] — дома / в гостях).
   Подключает assets/nav.js на страницах /epl/…, /laliga/… и других футбольных; пересборка страниц не нужна.
   Еврокубки: клубы из разных лиг — у каждого показатели и место в своём чемпионате. */
(()=>{
const hero=document.querySelector('main>.mx-hero');if(!hero||document.querySelector('.mx-cmp'))return;
const ids=[...hero.querySelectorAll('img[src*="/fc/"]')].map(i=>decodeURIComponent((/\/fc\/([^/.]+)\.webp/.exec(i.getAttribute('src'))||[])[1]||'')).filter((v,i,a)=>v&&a.indexOf(v)===i);
if(ids.length<2)return;
const base=(document.querySelector('script[src*="assets/nav.js"]')||{}).src||'';
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const go=()=>{
 const F=window.JV_FOOT||{},TT=F.teams||{},LG=F.leagues||{},H=TT[ids[0]],A=TT[ids[1]];
 if(!H||!A||!H.gp||!A.gp)return;
 const ln=t=>{const l=LG[t.lg]||{};return l.short||l.name||t.lg};
 const one=H.lg===A.lg;
 const pool=t=>Object.values(TT).filter(x=>x.lg===t.lg&&x.gp);
 const f=(v,d)=>v==null?'—':(+v).toFixed(d).replace('.',',');
 /* [подпись, значение для хозяев, для гостей, знаков, меньше — лучше, считать место] */
 const pg=k=>t=>t[k]/t.gp;
 const M=[
  ['Забивает за игру',pg('gf'),pg('gf'),2,0,1],
  ['Пропускает за игру',pg('ga'),pg('ga'),2,1,1],
  ['Очки за игру',pg('pts'),pg('pts'),2,0,1],
  ['Форма: очки за игру в последних 5',t=>t.raw&&t.raw[2],t=>t.raw&&t.raw[2],2,0,1],
  ['Очки за игру: хозяева дома, гости в гостях',t=>t.raw&&t.raw[3],t=>t.raw&&t.raw[4],2,0,0]];
 const rank=(t,get,low)=>{const v=get(t);return 1+pool(t).filter(x=>{const y=get(x);return y!=null&&(low?y<v:y>v)}).length};
 const rows=M.map(([n,gh,ga,d,low,rk])=>{const a=gh(H),b=ga(A);if(a==null||b==null)return'';
  const wa=low?b:a,wb=low?a:b,sh=wa+wb>0?Math.max(18,Math.min(82,100*wa/(wa+wb))):50;
  const win=a===b?0:(low?a<b:a>b)?1:2;
  const r=(t,get)=>rk?`<small>${rank(t,get,low)}-е ${one?'место':'· '+esc(ln(t))}</small>`:'';
  return `<div class="mc-row${win===1?' wh':win===2?' wa':''}" role="row"><b class="mc-v h" role="cell">${f(a,d)}${r(H,gh)}</b><span class="mc-n" role="rowheader">${n}</span><b class="mc-v a" role="cell">${f(b,d)}${r(A,ga)}</b>
   <span class="mc-bar" aria-hidden="true"><i style="width:${sh.toFixed(1)}%"></i><i></i></span></div>`}).join('');
 if(!rows)return;
 const rec=t=>`${t.place}-е место · ${t.w}–${t.d}–${t.l}`;
 const em=id=>`<img src="${base.replace(/nav\.js.*$/,'')}fc/${encodeURIComponent(id)}.webp" alt="" width="40" height="40" loading="lazy">`;
 const sec=document.createElement('section');sec.className='fc-sec mx-cmp';sec.setAttribute('aria-labelledby','mt-cmp');
 sec.innerHTML=`<div class="wrap"><h2 id="mt-cmp">Сравнение команд</h2>
  <div class="mc" role="table" aria-label="Показатели сезона: ${esc(H.n)} и ${esc(A.n)}">
   <div class="mc-head" role="row"><span class="h" role="columnheader">${em(ids[0])}<b>${esc(H.n)}</b><small>${rec(H)}</small></span><span class="mid" role="columnheader">${one?'Сезон '+esc(ln(H)):'Сезон в чемпионатах'}</span><span class="a" role="columnheader"><small>${rec(A)}</small><b>${esc(A.n)}</b>${em(ids[1])}</span></div>
   ${rows}
  </div>
  <p class="mc-note">${one?`Показатели чемпионата, место — среди ${pool(H).length} клубов ${esc(ln(H))}.`:`Показатели в своих чемпионатах: ${esc(H.n)} — ${esc(ln(H))}, ${esc(A.n)} — ${esc(ln(A))}.`} Рядом с названием клуба — место в таблице и победы–ничьи–поражения.</p></div>`;
 const after=document.getElementById('mt-form');const ref=after?after.closest('section'):document.querySelector('main>.mx-info');
 if(ref)ref.after(sec);else document.getElementById('main').appendChild(sec);
};
if(window.JV_FOOT)go();else{const s=document.createElement('script');s.src=base.replace(/assets\/nav\.js.*$/,'football/data/football-club.js');s.onload=go;document.head.appendChild(s)}
})();
