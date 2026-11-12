/* Страница матча (хоккей): блок «Сравнение команд» — показатели сезона двух клубов встречными полосами и место в лиге
   (владелец 12.11, по образцу матч-центра nhl.com). Данные — assets/data/teams-lite.js (raw: голы за игру, пропущено за игру,
   доля отражённых бросков, большинство, меньшинство). Подключает assets/nav.js на страницах /khl/… и /nhl/…; пересборка не нужна. */
(()=>{
const hero=document.querySelector('main>.mx-hero');if(!hero||document.querySelector('.mx-cmp'))return;
const ids=[...hero.querySelectorAll('img[src*="/em/"]')].map(i=>decodeURIComponent((/\/em\/([^/.]+)\.webp/.exec(i.getAttribute('src'))||[])[1]||'')).filter((v,i,a)=>v&&a.indexOf(v)===i);
if(ids.length<2)return;
const base=(document.querySelector('script[src*="assets/nav.js"]')||{}).src||'';
const go=()=>{
 const TT=(window.JV_TEAMS||{}).teams||{},H=TT[ids[0]],A=TT[ids[1]];
 if(!H||!A||!H.raw||!A.raw||H.lg!==A.lg)return;
 const nhl=H.lg==='nhl',LG=nhl?'НХЛ':'КХЛ',all=Object.values(TT).filter(t=>t.lg===H.lg&&t.raw);
 const f=(v,d)=>v==null?'—':(+v).toFixed(d).replace('.',',');
 /* [подпись, значение из команды, знаков, единица, меньше — лучше] */
 const M=[
  ['Забивает за игру',t=>t.raw[0],2,'',0],
  ['Пропускает за игру',t=>t.raw[1],2,'',1],
  ['Вратари: отражённые броски',t=>t.raw[2]==null?null:t.raw[2]*100,1,' %',0],
  nhl?['Реализация большинства',t=>t.raw[3]==null?null:t.raw[3]*100,1,' %',0]:['Голы в большинстве за игру',t=>t.raw[3],2,'',0],
  nhl?['Надёжность меньшинства',t=>t.raw[4]==null?null:t.raw[4]*100,1,' %',0]:['Пропускает в меньшинстве за игру',t=>t.raw[4],2,'',1],
  ['Средний тотал матчей',t=>t.tr&&t.tr.tot,2,'',-1]];
 const rank=(get,low,v)=>1+all.filter(t=>{const x=get(t);return x!=null&&(low?x<v:x>v)}).length;
 const rows=M.map(([n,get,d,u,low])=>{const a=get(H),b=get(A);if(a==null||b==null)return'';
  /* длина полос — доля значения; для «меньше — лучше» длиннее у того, кто лучше */
  const wa=low===1?b:a,wb=low===1?a:b,sh=wa+wb>0?Math.max(18,Math.min(82,100*wa/(wa+wb))):50;
  const win=low===-1||a===b?0:(low?a<b:a>b)?1:2;
  const rk=(v)=>low===-1?'':`<small>${rank(get,low,v)}-е место в ${LG}</small>`;
  return `<div class="mc-row${win===1?' wh':win===2?' wa':''}" role="row"><b class="mc-v h" role="cell">${f(a,d)}${u}${rk(a)}</b><span class="mc-n" role="rowheader">${n}</span><b class="mc-v a" role="cell">${f(b,d)}${u}${rk(b)}</b>
   <span class="mc-bar" aria-hidden="true"><i style="width:${sh.toFixed(1)}%"></i><i></i></span></div>`}).join('');
 if(!rows)return;
 const rec=(t,k)=>t.tr&&t.tr[k]?`${t.tr[k][0]}–${t.tr[k][1]}`:'—';
 const em=id=>`<img src="${base.replace(/nav\.js.*$/,'')}em/${encodeURIComponent(id)}.webp" alt="" width="40" height="40" loading="lazy">`;
 const sec=document.createElement('section');sec.className='fc-sec mx-cmp';sec.setAttribute('aria-labelledby','mt-cmp');
 sec.innerHTML=`<div class="wrap"><h2 id="mt-cmp">Сравнение команд</h2>
  <div class="mc" role="table" aria-label="Показатели сезона: ${H.name} и ${A.name}">
   <div class="mc-head" role="row"><span class="h" role="columnheader">${em(ids[0])}<b>${H.name}</b><small>дома ${rec(H,'home')}</small></span><span class="mid" role="columnheader">Сезон ${LG}</span><span class="a" role="columnheader"><small>в гостях ${rec(A,'away')}</small><b>${A.name}</b>${em(ids[1])}</span></div>
   ${rows}
  </div>
  <p class="mc-note">Показатели регулярного сезона, место — среди ${all.length} клубов ${LG}. «Дома» и «в гостях» — победы–поражения.</p></div>`;
 const after=document.getElementById('mt-form');const ref=after?after.closest('section'):document.querySelector('main>.mx-info');
 if(ref)ref.after(sec);else document.getElementById('main').appendChild(sec);
};
if(window.JV_TEAMS)go();else{const s=document.createElement('script');s.src=base.replace(/nav\.js.*$/,'data/teams-lite.js');s.onload=go;document.head.appendChild(s)}
})();
