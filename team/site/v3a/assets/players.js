/* Раздел «Игроки» (03.11): фильтры по лиге, команде, рынку, дом/выезд; «n из N», форма, следующий соперник.
   Есть составы (D.lu): N — матчи, где игрок вышел на поле; рынки: забьёт, 1+ в створ, 2+ удара, гол+пас, карточка.
   Нет составов — старый режим: N — матчи команды, рынки «Забьёт» и «Карточка». */
(()=>{
/* 13.11: данные по лигам — football/data/plg/meta.js (лиги, клубы) + plg/<лига>.js (players_split.py); грузим только нужную лигу,
   «Все лиги» — все файлы. Старый data/players.js (всё сразу) тоже понимаем. */
const M=window.JV_PLAYERS_META||window.JV_PLAYERS,D={...M,players:M.players||[]},$=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const crest=s=>`../assets/fc/${encodeURIComponent(s)}.webp`;
const crestS=s=>`../assets/fc/s/${encodeURIComponent(s)}.webp`;   /* мелкие (до 40 px), аудит 20.11 */
// портреты «как в НХЛ» (голова и плечи, без фона): data/ph/<id>.webp, список готовых — data/headshots.json (players_headshots.py);
// нет портрета — инициалы (фото Commons напрямую больше не показываем)
let PH={};
const photo=id=>PH[id]&&PH[id].ok?(window.JVD||(u=>u))(`data/ph/${encodeURIComponent(id)}.webp${PH[id].src?'?v='+encodeURIComponent(PH[id].src):''}`):'';   /* ?v=tm — фото с Transfermarkt, мимо старой копии в кэше */
const ini=n=>n.split(/\s+/).filter(Boolean).map(w=>w[0]).slice(0,2).join('').toUpperCase();
const col=T=>{const c=Array.isArray(T.c)?T.c[0]:T.c;return /^#?[0-9a-f]{6}$/i.test(String(c||''))?'#'+String(c).replace('#',''):'var(--paper-3)'};   /* только #rrggbb — цвет приходит из данных ESPN */
// фото игрока (ESPN); нет фото — инициалы на цвете клуба; эмблема — значком в углу
// светлый цвет клуба (белый «Осер» и т.п.) — инициалы тёмные
const lite=h=>{const m=/^#([0-9a-f]{6})$/i.exec(h);if(!m)return false;const n=parseInt(m[1],16);return (0.299*(n>>16)+0.587*(n>>8&255)+0.114*(n&255))>170};
const avatar=(p,T)=>`<div class="av${lite(col(T))?' lite':''}" style="--c:${col(T)}">${photo(p.id)?`<img class="ph" src="${photo(p.id)}" alt="" loading="lazy" onerror="this.remove()">`:''}<img class="bd" src="${crestS(p.t)}" alt="" loading="lazy" onerror="if(!this.dataset.f){this.dataset.f=1;this.src=this.src.replace('/fc/s/','/fc/')}else this.remove()"></div>`;
const LGN={...D.leagues};
const URLT=new URLSearchParams(location.search).get('team')||'';
const LU=!!D.lu;
const MN={sg:'забивал',st:'бил в створ',s2:'бил 2+ раза по воротам',ga:'забивал или отдавал пас',cr:'получал карточку'};
const URLL=(new URLSearchParams(location.search).get('lg')||'').toLowerCase();
const st={m:'sg',lg:'',tm:D.teams[URLT]?URLT:'',ha:'',so:'rate',q:'',lim:30};
$('season').textContent=D.season;
const lgs=['',...(M.lgs||Object.keys(LGN).filter(k=>D.players.some(p=>p.lg===k||(p.cu||[]).includes(k))))];
/* ?lg=epl — сразу игроки этой лиги (13.11, вкладка «Игроки» на странице лиги); ?team= — лига клуба */
if(lgs.includes(URLL)&&URLL)st.lg=URLL;else if(st.tm&&lgs.includes(D.teams[st.tm].lg))st.lg=D.teams[st.tm].lg;
$('lg').innerHTML=lgs.map(k=>`<button type="button" data-l="${k}" aria-pressed="${k===st.lg}">${k?esc(LGN[k]):'Все лиги'}</button>`).join('');
/* выбранная лига — в адресе страницы (ссылкой можно поделиться, «назад» возвращает к ней) */
const syncURL=()=>{try{const u=new URL(location.href);st.lg?u.searchParams.set('lg',st.lg):u.searchParams.delete('lg');st.tm?u.searchParams.set('team',st.tm):u.searchParams.delete('team');history.replaceState(null,'',u)}catch(e){}};
function teamOpts(){const cupT=new Set(st.lg?D.players.filter(p=>(p.cu||[]).includes(st.lg)).map(p=>p.t):[]);const ts=Object.entries(D.teams).filter(([s,t])=>!st.lg||t.lg===st.lg||cupT.has(s)).sort((a,b)=>a[1].n.localeCompare(b[1].n,'ru'));
  $('tm').innerHTML='<option value="">Все</option>'+ts.map(([s,t])=>`<option value="${s}"${s===st.tm?' selected':''}>${esc(t.n)}</option>`).join('')}
// n из N для текущего рынка и места
function hit(p){
  if(LU)return(st.ha==='home'?p.mh:st.ha==='away'?p.ma:p.m)[st.m];
  if(st.m==='cr'){if(!st.ha)return p.cr;return null}
  return st.ha?p[st.ha]:p.sg}
let ready=!!M.players,tok=0;const got={},V=encodeURIComponent(M.built||'');
const part=k=>got[k]||(got[k]=new Promise((ok,no)=>{const s=document.createElement('script');s.src=(window.JVD||(u=>u))(`data/plg/${encodeURIComponent(k)}.js?v=${V}`);s.onload=ok;s.onerror=()=>{delete got[k];no()};document.head.appendChild(s)}));
function load(){
  if(M.players){teamOpts();render();return}
  const t=++tok,ks=st.lg?[st.lg]:(M.own||M.lgs);ready=false;$('meta').textContent='Загружаем игроков…';
  Promise.all(ks.map(part)).then(()=>{if(t!==tok)return;const seen=new Set(),L=[];
    for(const k of ks)for(const p of (window.JV_PLG||{})[k]||[])if(!seen.has(p.id)){seen.add(p.id);L.push(p)}
    D.players=L;ready=true;teamOpts();render()}).catch(()=>{if(t===tok)$('meta').textContent='Не удалось загрузить игроков — обновите страницу.'})}
function render(){
  if(!ready)return;
  document.querySelector('.pl').dataset.m=st.m;
  const q=st.q.trim().toLowerCase();
  let L=D.players.filter(p=>(!st.lg||p.lg===st.lg||(p.cu||[]).includes(st.lg))&&(!st.tm||p.t===st.tm)&&(!q||p.n.toLowerCase().includes(q)));
  if(!LU){if(st.m==='cr'){L=L.filter(p=>p.cr[0]>0);if(st.ha)$('ha').value=st.ha=''}else L=L.filter(p=>p.G>0)}
  L=L.map(p=>({p,h:hit(p)})).filter(x=>x.h&&x.h[0]>0&&x.h[1]>=(st.ha?3:6));
  const tot=p=>st.m==='cr'?p.y+2*p.r:st.m==='st'?p.SoT:st.m==='s2'?p.S:st.m==='ga'?p.G+p.A:p.G;
  const val=x=>st.so==='n'?x.h[0]:st.so==='G'?tot(x.p):x.h[0]/x.h[1];
  L.sort((a,b)=>val(b)-val(a)||b.h[0]-a.h[0]||a.p.n.localeCompare(b.p.n));
  $('meta').textContent=`${L.length} игроков${['ucl','uel'].includes(st.lg)?' · «n из N» по всем турнирам сезона':''} · данные на ${(b=>{const m=/(\d{4})-(\d\d)-(\d\d)[ T](\d\d:\d\d)/.exec(String(b||''));return m?+m[3]+' '+['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'][+m[2]-1]+', '+m[4]+' МСК':String(b||'')})(D.built)}`;
  /* 17.11: тройка лидеров крупными карточками в цвете клуба (как в хоккее), остальные — прежними строками */
  const view=L.slice(0,st.lim),podN=view.length>=3?3:0,MKN={sg:'Забивал',st:'В створ',s2:'2+ удара',ga:'Гол+пас',cr:'Карточка'};
  const pod=view.slice(0,podN).map((x,i)=>{const p=x.p,T=D.teams[p.t]||{},h=x.h,c=col(T),hex=/^#/.test(c)?c:'#1d2a44',lt=lite(hex);
    const extra=st.m==='cr'?[['Жёлтые',p.y],['Красные',p.r||0]]:st.m==='st'||st.m==='s2'?[['Удары',p.S],['В створ',p.SoT]]:[['Голы',p.G],...(LU?[['Пасы',p.A]]:[])];
    return `<article class="pod fb pod${i+1}" role="listitem" style="--kb:${hex};--ko:${lt?'#10161f':'#fff'};--ko2:${lt?'rgba(16,22,31,.72)':'rgba(255,255,255,.78)'}"><img class="wm" src="${crest(p.t).replace('/fc/','/fc/l/')}" alt="" aria-hidden="true" loading="lazy" onerror="if(!this.dataset.f){this.dataset.f=1;this.src=this.src.replace('/fc/l/','/fc/')}else this.remove()"><i class="wms" aria-hidden="true" style="--em:url('${crest(p.t)}')"></i>
      ${photo(p.id)?`<img class="cut" src="${photo(p.id)}" alt="" loading="lazy" onerror="this.remove()">`:''}
      <span class="prk"><b>${i+1}</b><small>место</small></span>
      <div class="pnm"><b><a href="player.html?id=${encodeURIComponent(p.id)}" title="Профиль игрока">${esc(p.n)}</a></b><span><img class="te" src="${crestS(p.t)}" alt="" loading="lazy" onerror="if(!this.dataset.f){this.dataset.f=1;this.src=this.src.replace('/fc/s/','/fc/')}else this.remove()">${esc(T.n||'')}${p.pos?' · '+esc(p.pos):''}</span></div>
      <dl class="pst"><div class="on"><dt>${MKN[st.m]||''}</dt><dd>${h[0]}<small style="font-size:.5em;font-weight:700;opacity:.6"> из ${h[1]}</small></dd></div>${extra.filter(e=>e[1]!=null).map(e=>`<div><dt>${e[0]}</dt><dd>${e[1]}</dd></div>`).join('')}</dl>
    </article>`}).join('');
  $('list').innerHTML=(podN?`<div class="podium">${pod}</div>`:'')+view.slice(podN).map((x,i0)=>{const i=i0+podN,p=x.p,T=D.teams[p.t]||{},h=x.h,pc=Math.round(100*h[0]/h[1]);
    const F=[...(LU?p.ff[st.m]:p.f)],ok=c=>LU?c==='1':st.m==='cr'?c==='c':c==='g',F5=F.slice(-5),pl_=F.filter(c=>c!=='x').length;
    const strip=`<div class="bars">${F.map((c,j)=>{const o=D.teams[p.fo[j]];const t=(o?o.n:'')+(c==='x'?' — не играл':ok(c)?' — '+(MN[st.m]).replace(/^\S+/,'да'):' — нет');
      return `<i class="${ok(c)?'g':c==='x'?'x':''}" style="--h:${ok(c)?1:c==='x'?.04:.08}" title="${esc(t)}"></i>`}).join('')}</div><small>5 матчей: <b>${F5.filter(ok).length}/${F5.length}</b> · 10: <b>${F.filter(ok).length}/${LU?pl_:F.length}</b></small>`;
    const nx=p.nx&&D.teams[p.nx.o];
    const sub=LU?`${p.pos?esc(p.pos)+' · ':''}${p.N} матч.${p.mn?` · ${p.mn} мин`:''} · ${st.m==='cr'?`${p.y} жёлт.${p.r?` · ${p.r} красн.`:''}`:st.m==='st'?`${p.SoT} в створ из ${p.S}`:st.m==='s2'?`${p.S} ударов`:st.m==='ga'?`${p.G} гол. + ${p.A} пас.`:`${p.G} гол.`}`:st.m==='cr'?`${p.y} жёлт.${p.r?` · ${p.r} красн.`:''}`:`${p.G} ${p.G%10===1&&p.G%100!==11?'гол':p.G%10>=2&&p.G%10<=4&&(p.G%100<12||p.G%100>14)?'гола':'голов'}${p.pen?` · ${p.pen} с пен.`:''}`;
    return `<article class="pr" role="listitem">
      <span class="rk">${i+1}</span>${avatar(p,T)}
      <div class="nm"><b><a href="player.html?id=${encodeURIComponent(p.id)}" title="Профиль игрока">${esc(p.n)}</a></b><span>${esc(T.n||'')} · ${sub}</span></div>
      <div class="hit" aria-label="${h[0]} из ${h[1]} ${LU?'сыгранных матчей':'матчей'}"><b>${h[0]}<small>из ${h[1]}</small></b><div class="bar"><i style="width:${pc}%"></i></div></div>
      <div class="strip" aria-label="Последние 10 матчей">${strip}</div>
      <div class="ha">${LU?`Дома <b>${p.mh[st.m][0]}/${p.mh[st.m][1]}</b> · В гостях <b>${p.ma[st.m][0]}/${p.ma[st.m][1]}</b>`:st.m==='sg'?`Дома <b>${p.home[0]}/${p.home[1]}</b> · В гостях <b>${p.away[0]}/${p.away[1]}</b>`:`Карточка в ${pc}% матчей`}</div>
      <div class="nx">${nx?`<img src="${crestS(p.nx.o)}" alt="" loading="lazy" onerror="if(!this.dataset.f){this.dataset.f=1;this.src=this.src.replace('/fc/s/','/fc/')}else this.remove()"><span>Далее: <b>${esc(nx.n)}</b><br>${p.nx.h?'дома':'в гостях'}, ${p.nx.d.slice(8,10)}.${p.nx.d.slice(5,7)}</span>`:''}</div>
    </article>`}).join('');
  $('list').classList.toggle('first',!render.shown);render.shown=1;   /* появление — только при первом показе (ревью анимаций 17.11) */
  $('more').hidden=L.length<=st.lim}
$('mk').onclick=e=>{const b=e.target.closest('button');if(!b)return;st.m=b.dataset.m;st.lim=30;
  $('mk').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));$('ha').disabled=!LU&&st.m==='cr';render()};
$('lg').onclick=e=>{const b=e.target.closest('button');if(!b)return;st.lg=b.dataset.l;st.tm='';st.lim=30;
  $('lg').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));syncURL();load()};
$('tm').onchange=e=>{st.tm=e.target.value;st.lim=30;render();syncURL()};
$('ha').onchange=e=>{st.ha=e.target.value;render()};
$('so').onchange=e=>{st.so=e.target.value;render()};
$('q').oninput=e=>{st.q=e.target.value;st.lim=30;render()};
$('more').onclick=()=>{st.lim+=30;render()};
if(!LU)$('mk').querySelectorAll('button').forEach(b=>{if(!['sg','cr'].includes(b.dataset.m))b.hidden=true});
load();
fetch((window.JVD||(u=>u))('data/headshots.json')).then(r=>r.ok?r.json():{}).then(j=>{PH=j||{};render()}).catch(()=>{});
})();
