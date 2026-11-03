/* Раздел «Игроки» (прототип 03.11): фильтры по лиге, команде, рынку, дом/выезд; «n из N», форма, следующий соперник */
(()=>{
const D=window.JV_PLAYERS,$=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const crest=s=>`../assets/fc/${encodeURIComponent(s)}.webp`;
// фото — Wikimedia Commons (свободные лицензии), карта ESPN id → файл: data/photos.json (players_photos_fetch.py)
let PH={};
const photo=id=>PH[id]?`https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(PH[id])}?width=200`:'';
const ini=n=>n.split(/\s+/).filter(Boolean).map(w=>w[0]).slice(0,2).join('').toUpperCase();
const col=T=>{const c=Array.isArray(T.c)?T.c[0]:T.c;return c?'#'+String(c).replace('#',''):'var(--paper-3)'};
// фото игрока (ESPN); нет фото — инициалы на цвете клуба; эмблема — значком в углу
const avatar=(p,T)=>`<div class="av" style="--c:${col(T)}"><span>${esc(ini(p.n))}</span>${photo(p.id)?`<img class="ph" src="${photo(p.id)}" alt="" loading="lazy" onerror="this.remove()">`:''}<img class="bd" src="${crest(p.t)}" alt="" loading="lazy"></div>`;
const LGN={...D.leagues};
const st={m:'sg',lg:'',tm:'',ha:'',so:'rate',q:'',lim:30};
$('season').textContent=D.season;
const lgs=['',...Object.keys(LGN).filter(k=>D.players.some(p=>p.lg===k))];
$('lg').innerHTML=lgs.map(k=>`<button type="button" data-l="${k}" aria-pressed="${!k}">${k?esc(LGN[k]):'Все лиги'}</button>`).join('');
function teamOpts(){const ts=Object.entries(D.teams).filter(([s,t])=>!st.lg||t.lg===st.lg).sort((a,b)=>a[1].n.localeCompare(b[1].n,'ru'));
  $('tm').innerHTML='<option value="">Все</option>'+ts.map(([s,t])=>`<option value="${s}">${esc(t.n)}</option>`).join('')}
// n из N для текущего рынка и места
function hit(p){
  if(st.m==='cr'){if(!st.ha)return p.cr;return null}
  return st.ha?p[st.ha]:p.sg}
function render(){
  document.querySelector('.pl').dataset.m=st.m;
  const q=st.q.trim().toLowerCase();
  let L=D.players.filter(p=>(!st.lg||p.lg===st.lg)&&(!st.tm||p.t===st.tm)&&(!q||p.n.toLowerCase().includes(q)));
  if(st.m==='cr'){L=L.filter(p=>p.cr[0]>0);if(st.ha)$('ha').value=st.ha=''}else L=L.filter(p=>p.G>0);
  L=L.map(p=>({p,h:hit(p)})).filter(x=>x.h&&x.h[1]>=(st.ha?3:6));
  const val=x=>st.so==='n'?x.h[0]:st.so==='G'?(st.m==='cr'?x.p.y+2*x.p.r:x.p.G):x.h[0]/x.h[1];
  L.sort((a,b)=>val(b)-val(a)||b.h[0]-a.h[0]||a.p.n.localeCompare(b.p.n));
  $('meta').textContent=`${L.length} игроков · ${st.m==='cr'?'получал карточку':'забивал'} хотя бы в одном матче${st.ha==='home'?' дома':st.ha==='away'?' в гостях':''} · данные на ${D.built}`;
  $('list').innerHTML=L.slice(0,st.lim).map((x,i)=>{const p=x.p,T=D.teams[p.t]||{},h=x.h,pc=Math.round(100*h[0]/h[1]);
    const strip=[...p.f].map((c,j)=>{const o=D.teams[p.fo[j]];const t=(o?o.n:'')+(c==='g'?' — забил':c==='c'?' — карточка':'');
      return `<i class="${c==='-'?'':c}" title="${esc(t)}">${c==='g'?'Г':c==='c'?'К':''}</i>`}).join('');
    const nx=p.nx&&D.teams[p.nx.o];
    const sub=st.m==='cr'?`${p.y} жёлт.${p.r?` · ${p.r} красн.`:''}`:`${p.G} ${p.G%10===1&&p.G%100!==11?'гол':p.G%10>=2&&p.G%10<=4&&(p.G%100<12||p.G%100>14)?'гола':'голов'}${p.pen?` · ${p.pen} с пен.`:''}`;
    return `<article class="pr" role="listitem">
      <span class="rk">${i+1}</span>${avatar(p,T)}
      <div class="nm"><b>${esc(p.n)}</b><span>${esc(T.n||'')} · ${sub}</span></div>
      <div class="hit" aria-label="${h[0]} из ${h[1]} матчей"><b>${h[0]}<small>из ${h[1]}</small></b><div class="bar"><i style="width:${pc}%"></i></div></div>
      <div class="strip" aria-label="Последние 10 матчей">${strip}</div>
      <div class="ha">${st.m==='sg'?`Дома <b>${p.home[0]}/${p.home[1]}</b> · В гостях <b>${p.away[0]}/${p.away[1]}</b>`:`Карточка в ${pc}% матчей`}</div>
      <div class="nx">${nx?`<img src="${crest(p.nx.o)}" alt="" loading="lazy"><span>Далее: <b>${esc(nx.n)}</b><br>${p.nx.h?'дома':'в гостях'}, ${p.nx.d.slice(8,10)}.${p.nx.d.slice(5,7)}</span>`:''}</div>
    </article>`}).join('');
  $('more').hidden=L.length<=st.lim}
$('mk').onclick=e=>{const b=e.target.closest('button');if(!b)return;st.m=b.dataset.m;st.lim=30;
  $('mk').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));$('ha').disabled=st.m==='cr';render()};
$('lg').onclick=e=>{const b=e.target.closest('button');if(!b)return;st.lg=b.dataset.l;st.tm='';st.lim=30;
  $('lg').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));teamOpts();render()};
$('tm').onchange=e=>{st.tm=e.target.value;st.lim=30;render()};
$('ha').onchange=e=>{st.ha=e.target.value;render()};
$('so').onchange=e=>{st.so=e.target.value;render()};
$('q').oninput=e=>{st.q=e.target.value;st.lim=30;render()};
$('more').onclick=()=>{st.lim+=30;render()};
teamOpts();render();
fetch('data/photos.json').then(r=>r.ok?r.json():{}).then(j=>{PH=j||{};render()}).catch(()=>{});
})();
