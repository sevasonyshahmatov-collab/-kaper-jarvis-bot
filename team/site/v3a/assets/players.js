/* Раздел «Игроки» (03.11): фильтры по лиге, команде, рынку, дом/выезд; «n из N», форма, следующий соперник.
   Есть составы (D.lu): N — матчи, где игрок вышел на поле; рынки: забьёт, 1+ в створ, 2+ удара, гол+пас, карточка.
   Нет составов — старый режим: N — матчи команды, рынки «Забьёт» и «Карточка». */
(()=>{
const D=window.JV_PLAYERS,$=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const crest=s=>`../assets/fc/${encodeURIComponent(s)}.webp`;
// портреты «как в НХЛ» (голова и плечи, без фона): data/ph/<id>.webp, список готовых — data/headshots.json (players_headshots.py);
// нет портрета — инициалы (фото Commons напрямую больше не показываем)
let PH={};
const photo=id=>PH[id]&&PH[id].ok?`data/ph/${encodeURIComponent(id)}.webp`:'';
const ini=n=>n.split(/\s+/).filter(Boolean).map(w=>w[0]).slice(0,2).join('').toUpperCase();
const col=T=>{const c=Array.isArray(T.c)?T.c[0]:T.c;return c?'#'+String(c).replace('#',''):'var(--paper-3)'};
// фото игрока (ESPN); нет фото — инициалы на цвете клуба; эмблема — значком в углу
// светлый цвет клуба (белый «Осер» и т.п.) — инициалы тёмные
const lite=h=>{const m=/^#([0-9a-f]{6})$/i.exec(h);if(!m)return false;const n=parseInt(m[1],16);return (0.299*(n>>16)+0.587*(n>>8&255)+0.114*(n&255))>170};
const avatar=(p,T)=>`<div class="av${lite(col(T))?' lite':''}" style="--c:${col(T)}">${photo(p.id)?`<img class="ph" src="${photo(p.id)}" alt="" loading="lazy" onerror="this.remove()">`:''}<img class="bd" src="${crest(p.t)}" alt="" loading="lazy"></div>`;
const LGN={...D.leagues};
const URLT=new URLSearchParams(location.search).get('team')||'';
const LU=!!D.lu;
const MN={sg:'забивал',st:'бил в створ',s2:'бил 2+ раза по воротам',ga:'забивал или отдавал пас',cr:'получал карточку'};
const st={m:'sg',lg:'',tm:D.teams[URLT]?URLT:'',ha:'',so:'rate',q:'',lim:30};
$('season').textContent=D.season;
const lgs=['',...Object.keys(LGN).filter(k=>D.players.some(p=>p.lg===k))];
$('lg').innerHTML=lgs.map(k=>`<button type="button" data-l="${k}" aria-pressed="${!k}">${k?esc(LGN[k]):'Все лиги'}</button>`).join('');
function teamOpts(){const ts=Object.entries(D.teams).filter(([s,t])=>!st.lg||t.lg===st.lg).sort((a,b)=>a[1].n.localeCompare(b[1].n,'ru'));
  $('tm').innerHTML='<option value="">Все</option>'+ts.map(([s,t])=>`<option value="${s}"${s===st.tm?' selected':''}>${esc(t.n)}</option>`).join('')}
// n из N для текущего рынка и места
function hit(p){
  if(LU)return(st.ha==='home'?p.mh:st.ha==='away'?p.ma:p.m)[st.m];
  if(st.m==='cr'){if(!st.ha)return p.cr;return null}
  return st.ha?p[st.ha]:p.sg}
function render(){
  document.querySelector('.pl').dataset.m=st.m;
  const q=st.q.trim().toLowerCase();
  let L=D.players.filter(p=>(!st.lg||p.lg===st.lg)&&(!st.tm||p.t===st.tm)&&(!q||p.n.toLowerCase().includes(q)));
  if(!LU){if(st.m==='cr'){L=L.filter(p=>p.cr[0]>0);if(st.ha)$('ha').value=st.ha=''}else L=L.filter(p=>p.G>0)}
  L=L.map(p=>({p,h:hit(p)})).filter(x=>x.h&&x.h[0]>0&&x.h[1]>=(st.ha?3:6));
  const tot=p=>st.m==='cr'?p.y+2*p.r:st.m==='st'?p.SoT:st.m==='s2'?p.S:st.m==='ga'?p.G+p.A:p.G;
  const val=x=>st.so==='n'?x.h[0]:st.so==='G'?tot(x.p):x.h[0]/x.h[1];
  L.sort((a,b)=>val(b)-val(a)||b.h[0]-a.h[0]||a.p.n.localeCompare(b.p.n));
  $('meta').textContent=`${L.length} игроков · данные на ${(b=>{const m=/(\d{4})-(\d\d)-(\d\d)[ T](\d\d:\d\d)/.exec(String(b||''));return m?+m[3]+' '+['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'][+m[2]-1]+', '+m[4]+' МСК':String(b||'')})(D.built)}`;
  $('list').innerHTML=L.slice(0,st.lim).map((x,i)=>{const p=x.p,T=D.teams[p.t]||{},h=x.h,pc=Math.round(100*h[0]/h[1]);
    const F=[...(LU?p.ff[st.m]:p.f)],ok=c=>LU?c==='1':st.m==='cr'?c==='c':c==='g',F5=F.slice(-5),pl_=F.filter(c=>c!=='x').length;
    const strip=`<div class="bars">${F.map((c,j)=>{const o=D.teams[p.fo[j]];const t=(o?o.n:'')+(c==='x'?' — не играл':ok(c)?' — '+(MN[st.m]).replace(/^\S+/,'да'):' — нет');
      return `<i class="${ok(c)?'g':c==='x'?'x':''}" style="--h:${ok(c)?1:c==='x'?.04:.08}" title="${esc(t)}"></i>`}).join('')}</div><small>5 матчей: <b>${F5.filter(ok).length}/${F5.length}</b> · 10: <b>${F.filter(ok).length}/${LU?pl_:F.length}</b></small>`;
    const nx=p.nx&&D.teams[p.nx.o];
    const sub=LU?`${p.pos?esc(p.pos)+' · ':''}${p.N} матч.${p.mn?` · ${p.mn} мин`:''} · ${st.m==='cr'?`${p.y} жёлт.${p.r?` · ${p.r} красн.`:''}`:st.m==='st'?`${p.SoT} в створ из ${p.S}`:st.m==='s2'?`${p.S} ударов`:st.m==='ga'?`${p.G} гол. + ${p.A} пас.`:`${p.G} гол.`}`:st.m==='cr'?`${p.y} жёлт.${p.r?` · ${p.r} красн.`:''}`:`${p.G} ${p.G%10===1&&p.G%100!==11?'гол':p.G%10>=2&&p.G%10<=4&&(p.G%100<12||p.G%100>14)?'гола':'голов'}${p.pen?` · ${p.pen} с пен.`:''}`;
    return `<article class="pr" role="listitem">
      <span class="rk">${i+1}</span>${avatar(p,T)}
      <div class="nm"><b>${esc(p.n)}</b><span>${esc(T.n||'')} · ${sub}</span></div>
      <div class="hit" aria-label="${h[0]} из ${h[1]} ${LU?'сыгранных матчей':'матчей'}"><b>${h[0]}<small>из ${h[1]}</small></b><div class="bar"><i style="width:${pc}%"></i></div></div>
      <div class="strip" aria-label="Последние 10 матчей">${strip}</div>
      <div class="ha">${LU?`Дома <b>${p.mh[st.m][0]}/${p.mh[st.m][1]}</b> · В гостях <b>${p.ma[st.m][0]}/${p.ma[st.m][1]}</b>`:st.m==='sg'?`Дома <b>${p.home[0]}/${p.home[1]}</b> · В гостях <b>${p.away[0]}/${p.away[1]}</b>`:`Карточка в ${pc}% матчей`}</div>
      <div class="nx">${nx?`<img src="${crest(p.nx.o)}" alt="" loading="lazy"><span>Далее: <b>${esc(nx.n)}</b><br>${p.nx.h?'дома':'в гостях'}, ${p.nx.d.slice(8,10)}.${p.nx.d.slice(5,7)}</span>`:''}</div>
    </article>`}).join('');
  $('more').hidden=L.length<=st.lim}
$('mk').onclick=e=>{const b=e.target.closest('button');if(!b)return;st.m=b.dataset.m;st.lim=30;
  $('mk').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));$('ha').disabled=!LU&&st.m==='cr';render()};
$('lg').onclick=e=>{const b=e.target.closest('button');if(!b)return;st.lg=b.dataset.l;st.tm='';st.lim=30;
  $('lg').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));teamOpts();render()};
$('tm').onchange=e=>{st.tm=e.target.value;st.lim=30;render()};
$('ha').onchange=e=>{st.ha=e.target.value;render()};
$('so').onchange=e=>{st.so=e.target.value;render()};
$('q').oninput=e=>{st.q=e.target.value;st.lim=30;render()};
$('more').onclick=()=>{st.lim+=30;render()};
if(!LU)$('mk').querySelectorAll('button').forEach(b=>{if(!['sg','cr'].includes(b.dataset.m))b.hidden=true});
teamOpts();render();
fetch('data/headshots.json').then(r=>r.ok?r.json():{}).then(j=>{PH=j||{};render()}).catch(()=>{});
})();
