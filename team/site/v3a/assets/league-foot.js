/* JARVIS v3a — страница футбольной лиги: football/league.html?lg=<epl|laliga|seriea|bundesliga|ligue1|rpl|ucl|uel>.
   Данные — football/data/football.js (JV_FOOT: таблицы, матчи клубов, расписание), игроки — data/players.js (JV_PLAYERS) и data/photos.json.
   Без кэфов и ставок. Время матчей московское. */
(()=>{
'use strict';
const {D,esc,fx,plural,T,nm,CI,LGP,LGI,teamHref,day,dd,played}=JVF;
const $=id=>document.getElementById(id);
const LG=(new URLSearchParams(location.search).get('lg')||'').toLowerCase(),L=D.leagues[LG];
const KEYS=Object.keys(D.leagues);

/* ── нет такой лиги ── */
if(!L){
 document.title='Лига не найдена · JARVIS';
 $('hero').innerHTML=`<a class="crumb" href="index.html#leagues"><span aria-hidden="true">←</span> Футбол · Лиги</a>
  <div class="lgname" data-rv><h1>Такой лиги нет</h1><p class="lead">${LG?`По адресу «${esc(LG)}» лиги не нашлось.`:'В адресе не указана лига.'} Выберите турнир:</p></div>
  <ul class="chips">${KEYS.map(k=>`<li><a href="league.html?lg=${esc(k)}">${LGP(k)}${esc(D.leagues[k].name)}</a></li>`).join('')}</ul>`;
 document.querySelectorAll('.lgsec').forEach(e=>{e.hidden=true;e.removeAttribute('data-zone')});
 document.querySelector('.nav').hidden=true;
 return;
}

const CUP=!!L.cup,LN=L.name,ids=L.ids;
const sel=g=>CUP?g.c===LG:!g.c;                     // матч этого турнира (в таблице клуба вперемешку лига и еврокубки)
const tref=s=>teamHref(s,CUP?LG:'');
document.title=`${LN} — таблица, матчи, бомбардиры · JARVIS`;

/* все сыгранные матчи турнира: берём по одной записи (с точки зрения хозяев) */
const M=[];ids.forEach(i=>(T[i]?T[i].games:[]).forEach(g=>{if(g.h===1&&sel(g)&&played(g))M.push({d:g.d,h:i,a:g.o,gf:g.gf,ga:g.ga})}));
M.sort((a,b)=>a.d<b.d?1:a.d>b.d?-1:0);
const tb=D.tables[LG]||[];
const gpMax=tb.reduce((a,r)=>Math.max(a,r.gp),0);
const tours=CUP?8:(ids.length-1)*2;                  // туров в сезоне: круговой турнир в два круга; общий этап ЛЧ и ЛЕ — 8 туров

/* ── шапка лиги ── */
$('hero').innerHTML=`
 <a class="crumb" href="${CUP?'ucl.html':'index.html#leagues'}"><span aria-hidden="true">←</span> ${CUP&&LG==='ucl'?'Лига чемпионов':'Футбол · Лиги и клубы'}</a>
 <div class="lgrow" data-rv>
  <span class="lgbig ${esc(LG)}"><img src="${LGI(LG)}" alt=""></span>
  <div class="lgname"><p class="tmlg">${esc(L.full)} · сезон ${esc(D.season)}</p><h1>${esc(LN)}</h1></div>
 </div>
 <ul class="facts" aria-label="Коротко" data-rv>
  <li><b class="num">${ids.length}</b><span>${plural(ids.length,'клуб','клуба','клубов')} в ${CUP?'общем этапе':'лиге'}</span></li>
  <li><b class="num">${gpMax}<small style="font-size:.42em;color:var(--ink-3)"> / ${tours}</small></b><span>${CUP?'сыграно туров общего этапа':'сыграно туров из '+tours}</span></li>
  <li><b class="num">${M.length}</b><span>${plural(M.length,'матч сыгран','матча сыграно','матчей сыграно')} в сезоне</span></li>
  <li><b class="num" id="fUp">—</b><span id="fUpl">матчей в ближайшие 7 дней</span></li>
 </ul>
 <ul class="chips" aria-label="Другие лиги" data-rv>${KEYS.map(k=>`<li><a href="league.html?lg=${esc(k)}"${k===LG?' aria-current="page"':''}>${LGP(k)}${esc(D.leagues[k].name)}</a></li>`).join('')}</ul>`;
JV.fitWords('.lgname h1');   /* длинное название лиги — без разрыва слова (09.11) */

/* ── таблица: общая / дома / в гостях ── */
const ZONE={epl:[[1,4,'z1','Лига чемпионов'],[5,5,'z2','Лига Европы'],[18,20,'z4','Вылет']],laliga:[[1,4,'z1','Лига чемпионов'],[5,6,'z2','Лига Европы'],[18,20,'z4','Вылет']],
 seriea:[[1,4,'z1','Лига чемпионов'],[5,6,'z2','Лига Европы'],[18,20,'z4','Вылет']],bundesliga:[[1,4,'z1','Лига чемпионов'],[5,6,'z2','Лига Европы'],[16,16,'z3','Стыковые матчи'],[17,18,'z4','Вылет']],
 ligue1:[[1,3,'z1','Лига чемпионов'],[4,5,'z2','Лига Европы'],[16,16,'z3','Стыковые матчи'],[17,18,'z4','Вылет']],rpl:[[1,3,'z1','Еврокубки по рейтингу'],[15,16,'z4','Вылет']],
 ucl:[[1,8,'z1','Сразу в 1/8 финала'],[9,24,'z2','Плей-офф'],[25,36,'z4','Выбыли']],uel:[[1,8,'z1','Сразу в 1/8 финала'],[9,24,'z2','Плей-офф'],[25,36,'z4','Выбыли']]}[LG]||[];
const ZC={z1:'#0d7a48',z2:'#1c63c4',z3:'#d9822b',z4:'#c4303b'};
const plRow=Object.fromEntries(tb.map(r=>[r.id,r]));
function rowsFor(mode){
 if(mode==='all')return ids.map(s=>({...(plRow[s]||{place:99,gp:0,w:0,d:0,l:0,gf:0,ga:0,pts:0}),id:s})).sort((a,b)=>a.place-b.place);
 const r=ids.map(s=>{const o={id:s,gp:0,w:0,d:0,l:0,gf:0,ga:0,pts:0};
  (T[s]?T[s].games:[]).forEach(g=>{if(!sel(g)||!played(g)||(mode==='home'?g.h!==1:g.h===1))return;
   o.gp++;o.gf+=g.gf;o.ga+=g.ga;if(g.gf>g.ga){o.w++;o.pts+=3}else if(g.gf===g.ga){o.d++;o.pts++}else o.l++});return o});
 r.sort((a,b)=>b.pts-a.pts||(b.gf-b.ga)-(a.gf-a.ga)||b.gf-a.gf||(T[a.id].n<T[b.id].n?-1:1));
 r.forEach((o,i)=>o.place=i+1);return r}
let mode='all';
const MODES=[['all','Общая'],['home','Дома'],['away','В гостях']];
$('tableBox').innerHTML=`
 <div class="sec-head" data-rv><h2>${CUP?'Общий этап':'Турнирная таблица'}</h2></div>
 <div class="lgsw tabs" role="tablist" id="tbSw" aria-label="Какая таблица">${MODES.map(([k,t])=>`<button class="tab" role="tab" type="button" data-m="${k}" aria-selected="${k===mode}">${t}</button>`).join('')}</div>
 <div class="tabscroll lgtbl" id="tbBody"></div><ul class="lkey" id="tbKey"></ul>`;
function drawTable(){
 const rows=rowsFor(mode);
 $('tbBody').innerHTML=`<table class="ltab"><thead><tr><th>#</th><th>Клуб</th><th>И</th><th class="hm">В</th><th class="hm">Н</th><th class="hm">П</th><th>Мячи</th><th class="hm">РМ</th><th>О</th></tr></thead><tbody>${rows.map(t=>{
  const zc=mode==='all'?(ZONE.find(x=>t.place>=x[0]&&t.place<=x[1])||[])[2]||'':'',d=t.gf-t.ga;
  return `<tr class="${zc}"><td>${t.place}</td><td><a href="${tref(t.id)}">${CI(t.id)}<span>${esc(nm(t.id))}</span></a></td><td>${t.gp}</td><td class="hm">${t.w}</td><td class="hm">${t.d}</td><td class="hm">${t.l}</td><td>${t.gf}:${t.ga}</td><td class="hm gd">${d>0?'+'+d:d}</td><td class="pt">${t.pts}</td></tr>`}).join('')}</tbody></table>`;
 const seen=[];if(mode==='all')ZONE.forEach(x=>{if(!seen.find(s=>s[3]===x[3]))seen.push(x)});
 $('tbKey').innerHTML=seen.map(x=>`<li><i style="background:${ZC[x[2]]}"></i>${esc(x[3])}</li>`).join('')+`<li>И — игры, РМ — разница мячей, О — очки${mode==='all'?'':'; '+(mode==='home'?'только домашние':'только гостевые')+' матчи'}; по данным ESPN на ${esc((D.built||'').slice(8,10))}.${esc((D.built||'').slice(5,7))}</li>`}
$('tbSw').addEventListener('click',e=>{const b=e.target.closest('.tab');if(!b||b.dataset.m===mode)return;mode=b.dataset.m;
 $('tbSw').querySelectorAll('.tab').forEach(x=>x.setAttribute('aria-selected',x===b));drawTable()});
drawTable();

/* ── строка матча: время или дата слева, команды со ссылками, счёт или тире ── */
const MON=['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'];
function mrow(m,fut){const hw=!fut&&m.gf>m.ga,aw=!fut&&m.ga>m.gf,left=fut?JV.left(m.t):0;
 const when=fut?`${esc(m.t.slice(11))}${left<=0?'<small class="live">идёт</small>':''}`:`${dd(m.d)}<small>${esc(m.d.slice(11))}</small>`;
 return `<li class="lgm"><span class="when num">${when}</span>
  <a class="t" href="${tref(m.h)}">${CI(m.h)}<span class="${hw?'w':''}">${esc(nm(m.h))}</span></a>
  <span class="s num${fut?' vs':''}">${fut?'—':m.gf+':'+m.ga}</span>
  <a class="t a" href="${tref(m.a)}">${CI(m.a)}<span class="${aw?'w':''}">${esc(nm(m.a))}</span></a></li>`}

/* ── ближайший тур: матчи лиги в ближайшие 7 дней ── */
{const FUT=D.up.filter(m=>m.lg===LG&&JV.left(m.t)>-2*3600).sort((a,b)=>a.t<b.t?-1:a.t>b.t?1:0);
 let list=[],head='';
 if(FUT.length){const f=FUT[0],end=Date.parse(f.t.slice(0,10)+'T00:00:00+03:00')+7*864e5;
  list=FUT.filter(m=>JV.atMs(m.t)<end);const a=day(f.t),z=day(list[list.length-1].t);
  head=`${a.d} ${a.mon}${a.d===z.d&&a.mon===z.mon?'':' — '+z.d+' '+z.mon}`}
 $('fUp').textContent=list.length;$('fUpl').textContent=plural(list.length,'матч','матча','матчей')+' в ближайшие 7 дней';
 let html='',prev='';const CAP=40;
 list.slice(0,CAP).forEach(m=>{const dk=m.t.slice(0,10);if(dk!==prev){prev=dk;const d=day(m.t);html+=`<li class="dayh" aria-hidden="true">${d.wd}, ${d.d} ${d.mon}</li>`}html+=mrow(m,true)});
 $('nextBox').innerHTML=`
  <div class="sec-head" data-rv><h2>Ближайший тур</h2></div>
  ${list.length?`<ul class="lgml" data-rv>${html}</ul>${list.length>CAP?`<p class="note lgnote">Показаны первые ${CAP} матчей.</p>`:''}`:'<p class="lgempty">В ближайшие дни матчей нет.</p>'}`}

/* ── последние результаты ── */
{const STEP=10;let n=STEP;const box=$('resultsBox');
 box.innerHTML=`
  <div class="sec-head" data-rv><h2>Последние результаты</h2></div>
  <ul class="lgml" id="rsList"></ul><div class="lgmore"><button class="btn btn-line" type="button" id="rsMore" hidden></button></div>`;
 const ul=$('rsList'),more=$('rsMore');
 const draw=()=>{ul.innerHTML=M.length?M.slice(0,n).map(m=>mrow(m,false)).join(''):'<li class="lgempty">Сыгранных матчей пока нет.</li>';
  more.hidden=n>=M.length;more.textContent=`Показать ещё ${Math.min(STEP,M.length-n)}`};
 more.addEventListener('click',()=>{n+=STEP;draw()});draw()}

/* ── статистика лиги ── */
{const n=M.length,sum=M.reduce((a,m)=>a+m.gf+m.ga,0),pc=v=>n?Math.round(v/n*100):0;
 const ov=M.filter(m=>m.gf+m.ga>2).length,bt=M.filter(m=>m.gf>0&&m.ga>0).length;
 const hw=M.filter(m=>m.gf>m.ga).length,dr=M.filter(m=>m.gf===m.ga).length,aw=n-hw-dr;
 const hp=pc(hw),dp=pc(dr),ap=n?100-hp-dp:0;
 const blank=M.filter(m=>m.gf+m.ga===0).length;
 $('statsBox').innerHTML=`
  <div class="sec-head" data-rv><h2>Статистика лиги</h2></div>
  <ul class="lgst" data-rv>
   <li><b class="num">${n?fx(sum/n,2):'—'}</b><span>голов за матч</span><em>всего ${sum}</em></li>
   <li><b class="num">${pc(ov)}<small>%</small></b><span>матчей с тоталом больше 2,5</span><em>${ov} из ${n}</em></li>
   <li><b class="num">${pc(bt)}<small>%</small></b><span>матчей, где забили обе</span><em>${bt} из ${n}</em></li>
   <li><b class="num">${blank}</b><span>${plural(blank,'матч','матча','матчей')} 0:0</span><em>${pc(blank)}% от всех</em></li>
  </ul>
  <div class="lgbar" data-rv><h3>Чем заканчиваются матчи</h3>
   <div class="bar" role="img" aria-label="Победы хозяев ${hp} %, ничьи ${dp} %, победы гостей ${ap} %"><i class="h" style="flex:${hw||.0001}">${hp>=8?hp+'%':''}</i><i class="d" style="flex:${dr||.0001}">${dp>=8?dp+'%':''}</i><i class="a" style="flex:${aw||.0001}">${ap>=8?ap+'%':''}</i></div>
   <ul><li style="--k:#1d7a45">Победы хозяев: ${hp}% (${hw})</li><li style="--k:#6b7585">Ничьи: ${dp}% (${dr})</li><li style="--k:#1c63c4">Победы гостей: ${ap}% (${aw})</li></ul></div>`}

/* ── игроки: бомбардиры и карточки (данные подгружаем отдельно: файл тяжёлый) ── */
const pbox=$('playersBox');
pbox.innerHTML=`
 <div class="sec-head" data-rv><h2>Бомбардиры и карточки</h2></div>
 <div class="lgcard" id="plCols"><div><h3>Бомбардиры</h3><p class="lgempty">Загружаем игроков…</p></div></div>`;
const ini=n=>{const w=String(n).replace(/[^\p{L}\s'-]/gu,'').split(/[\s-]+/).filter(Boolean);return ((w[0]||'')[0]||'').toUpperCase()+((w.length>1?w[w.length-1]:'')[0]||'').toUpperCase()};
const loadJS=src=>new Promise((ok,no)=>{const s=document.createElement('script');s.src=src;s.onload=ok;s.onerror=no;document.body.appendChild(s)});
Promise.all([loadJS('data/pl/'+LG+'.js'),fetch('data/photos.json').then(r=>r.json()).catch(()=>({}))]).then(([,ph])=>{
 const all=(window.JV_PLAYERS&&JV_PLAYERS.players||[]).filter(p=>p.lg===LG);
 const photo=p=>ph[p.id]?`<img src="https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(ph[p.id])}?width=200" alt="" loading="lazy" referrerpolicy="no-referrer">`:'';
 const who=p=>`<span class="av">${esc(ini(p.n))}${photo(p)}</span><span class="who"><b>${esc(p.n)}</b><a href="${tref(p.t)}">${CI(p.t)}<span>${esc(nm(p.t))}</span></a></span>`;
 const sc=all.filter(p=>p.G>0).sort((a,b)=>b.G-a.G||a.pen-b.pen||(a.n<b.n?-1:1)).slice(0,15);
 const cd=all.filter(p=>p.y+p.r>0).sort((a,b)=>(b.y+b.r*2)-(a.y+a.r*2)||b.r-a.r||(a.n<b.n?-1:1)).slice(0,10);
 $('plCols').innerHTML=`
  <div data-rv><h3>Бомбардиры · топ-15</h3>${sc.length?`<ol class="lgpl">${sc.map((p,i)=>`<li><span class="r num">${i+1}</span>${who(p)}<span class="val num">${p.G}<small>${p.pen?`с пенальти ${p.pen}`:'голов'}${p.sg?` · в ${p.sg[0]} из ${p.sg[1]}`:''}</small></span></li>`).join('')}</ol>`:'<p class="lgempty">Голов пока нет.</p>'}</div>
  <div data-rv><h3>Карточки · топ-10</h3>${cd.length?`<ol class="lgpl">${cd.map((p,i)=>`<li><span class="r num">${i+1}</span>${who(p)}<span class="val cds"><span class="cd num"><i></i>${p.y}</span>${p.r?`<span class="cd r num"><i></i>${p.r}</span>`:''}</span></li>`).join('')}</ol>`:'<p class="lgempty">Карточек пока нет.</p>'}</div>`;
 $('plCols').querySelectorAll('.av img').forEach(i=>i.addEventListener('error',()=>i.remove()));
 JV.reveal($('plCols'));
 /* ссылка «Все игроки лиги» скрыта до готовности портретов (владелец 04.11) */
}).catch(()=>{$('plCols').innerHTML='<p class="lgempty">Игроков загрузить не удалось.</p>'});
})();

/* пересчитать «свет арены» после отрисовки (иначе герой бледный до первой прокрутки) */
for(const t of [50,400,1200])setTimeout(()=>{dispatchEvent(new Event("resize"));dispatchEvent(new Event("scroll"))},t);
