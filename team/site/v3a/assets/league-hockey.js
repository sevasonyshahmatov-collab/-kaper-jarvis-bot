/* JARVIS v3a — страница хоккейной лиги: hockey/league.html?lg=<khl|nhl>.
   Данные: assets/data/teams.js (таблица), team/season.json (матчи сезона), hockey/data/{khl,nhl}_players.json (игроки). Время матчей московское. Без кэфов и ставок. */
(()=>{
'use strict';
const D=window.JV_TEAMS||{teams:{}};
const $=id=>document.getElementById(id);
const esc=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const plural=(n,a,b,c)=>{const k=n%100,j=n%10;return k>10&&k<20?c:j===1?a:j>1&&j<5?b:c};
const f1=(v,d=1)=>(+v).toFixed(d).replace('.',',');
const LGS={khl:{name:'КХЛ',full:'Континентальная хоккейная лига',gm:68,conf:['Запад','Восток'],json:'khl_players.json',all:'players_khl.html'},
 nhl:{name:'НХЛ',full:'Национальная хоккейная лига',gm:82,conf:['Восток','Запад'],json:'nhl_players.json',all:'players.html'}};
const P=new URLSearchParams(location.search),LG=(P.get('lg')||'').toLowerCase(),L=LGS[LG],THEME=P.get('theme');
const tq=/^(arena|a|b|c)$/.test(THEME||'')?`&theme=${THEME}`:'';
const lgp=k=>`<span class="lgp ${k}"><img src="../assets/lg/${k}.webp" alt=""></span>`;
const em=s=>`<img class="em" src="../assets/em/${esc(s)}.webp" alt="" loading="lazy" width="64" height="64">`;
const thref=s=>`../team/index.html?id=${encodeURIComponent(s)}${tq}`;
const MON=['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'],WD=['вс','пн','вт','ср','чт','пт','сб'];
const day=d=>{const [y,m,dd]=d.slice(0,10).split('-').map(Number),x=new Date(Date.UTC(y,m-1,dd));return {d:dd,mon:MON[m-1],wd:WD[x.getUTCDay()]}};
const dd=t=>`${t.slice(8,10)}.${t.slice(5,7)}`;

if(!L){
 document.title='Лига не найдена · JARVIS';
 $('hero').innerHTML=`<a class="crumb" href="index.html#leagues"><span aria-hidden="true">←</span> Хоккей · Лиги</a>
  <div class="lgname" data-rv><h1>Такой лиги нет</h1><p class="lead">Выберите турнир:</p></div>
  <ul class="chips"><li><a href="league.html?lg=khl${tq}">${lgp('khl')}КХЛ</a></li><li><a href="league.html?lg=nhl${tq}">${lgp('nhl')}НХЛ</a></li></ul>`;
 document.querySelectorAll('.lgsec').forEach(e=>{e.hidden=true;e.removeAttribute('data-zone')});document.querySelector('.nav').hidden=true;return;
}
document.title=`${L.name} — таблица, матчи, бомбардиры · JARVIS`;
const TM=Object.entries(D.teams).filter(([,t])=>t.lg===LG).map(([id,t])=>({id,...t}));
const byName=Object.fromEntries(TM.map(t=>[t.name,t.id])),nm=s=>(D.teams[s]||{}).name||s;
const ABBR={};TM.forEach(t=>{ABBR[LG==='nhl'?(t.id.startsWith('nhl_')?t.id.slice(4).toUpperCase():t.id==='minnesota'?'MIN':t.id==='dallas'?'DAL':t.id.toUpperCase()):t.id]=t.id});
const sk='<span class="lgsk" style="display:none"></span>';

function build(SE,PL){
 /* матчи: одна запись на игру (со стороны хозяев) */
 const M=[],U=[];
 Object.entries(SE[LG]||{}).forEach(([name,t])=>{const h=byName[name];t.games.forEach(g=>{if(g.h!==1)return;const a=byName[g.o];
  if(g.gf==null)U.push({t:g.d,h,a});else M.push({d:g.d,h,a,gf:g.gf,ga:g.ga,x:g.x||''})})});
 M.sort((a,b)=>a.d<b.d?1:a.d>b.d?-1:0);
 /* в расписании КХЛ в season.json будущих игр нет — берём ближайший матч каждого клуба из файла игроков */
 if(!U.length&&PL.next)Object.entries(PL.next).forEach(([s,n])=>{if(n&&n.h===1&&D.teams[s]&&D.teams[n.o])U.push({t:n.d,h:s,a:n.o})});
 U.sort((a,b)=>a.t<b.t?-1:a.t>b.t?1:0);
 const gpMax=TM.reduce((a,t)=>Math.max(a,t.gp||0),0);
 const FUT=U.filter(m=>JV.left(m.t)>-2*3600);
 let list=[],head='';
 if(FUT.length){const f=FUT[0],end=Date.parse(f.t.slice(0,10)+'T00:00:00+03:00')+3*864e5;list=FUT.filter(m=>JV.atMs(m.t)<end);
  const a=day(f.t),z=day(list[list.length-1].t);head=`${a.d} ${a.mon}${a.d===z.d&&a.mon===z.mon?'':' — '+z.d+' '+z.mon}`}

 $('hero').innerHTML=`
  <a class="crumb" href="index.html#lg-${LG}${tq}"><span aria-hidden="true">←</span> Хоккей · Лиги и клубы</a>
  <div class="lgrow" data-rv><span class="lgbig ${LG}"><img src="../assets/lg/${LG}.webp" alt=""></span>
   <div class="lgname"><p class="tmlg">${L.full} · сезон ${esc(PL.season||'2026/27')}</p><h1>${L.name}</h1></div></div>
  <ul class="facts" aria-label="Коротко" data-rv>
   <li><b class="num">${TM.length}</b><span>${plural(TM.length,'клуб','клуба','клубов')} в лиге</span></li>
   <li><b class="num">${M.length}</b><span>${plural(M.length,'матч сыгран','матча сыграно','матчей сыграно')} в сезоне</span></li>
   <li><b class="num">${gpMax}<small style="font-size:.42em;color:var(--ink-3)"> / ${L.gm}</small></b><span>игр у лидера по числу матчей</span></li>
   <li><b class="num">${list.length}</b><span>${plural(list.length,'матч','матча','матчей')} в ближайшие 3 дня</span></li></ul>
  <ul class="chips" aria-label="Другие лиги" data-rv>${Object.keys(LGS).map(k=>`<li><a href="league.html?lg=${k}${tq}"${k===LG?' aria-current="page"':''}>${lgp(k)}${LGS[k].name}</a></li>`).join('')}</ul>`;

 /* таблица */
 let mode='conf';
 $('tableBox').innerHTML=`
  <div class="sec-head" data-rv><h2>Турнирная таблица</h2><p>${lgp(LG)}${L.name}, сезон ${esc(PL.season||'2026/27')}</p></div>
  <div class="lgsw tabs" role="tablist" id="tbSw" aria-label="Вид таблицы"><button class="tab" role="tab" type="button" data-m="conf" aria-selected="true">По конференциям</button><button class="tab" role="tab" type="button" data-m="all" aria-selected="false">Вся лига</button></div>
  <div id="tbBody"></div><ul class="lkey" id="tbKey"></ul>`;
 const tbl=(rows,zone)=>`<div class="tabscroll lgtbl"><table class="ltab"><thead><tr><th>#</th><th>Клуб</th><th>И</th><th class="hm">В</th><th class="hm">П</th><th>Шайбы</th><th class="hm">РШ</th><th>О</th></tr></thead><tbody>${rows.map((t,i)=>{const d=t.gf-t.ga;
  return `<tr class="${zone&&i<8?'z1':''}"><td>${i+1}</td><td><a href="${thref(t.id)}">${em(t.id)}<span>${esc(t.name)}</span></a></td><td>${t.gp}</td><td class="hm">${t.w}</td><td class="hm">${t.l}</td><td>${t.gf}:${t.ga}</td><td class="hm gd">${d>0?'+'+d:d}</td><td class="pt">${t.pts}</td></tr>`}).join('')}</tbody></table></div>`;
 const draw=()=>{
  if(mode==='conf')$('tbBody').innerHTML=`<div class="confs">${L.conf.map(c=>`<section class="conf"><h3 class="lgconf">${c}</h3>${tbl(TM.filter(t=>t.conf===c).sort((a,b)=>a.place-b.place),true)}</section>`).join('')}</div>`;
  else $('tbBody').innerHTML=tbl(TM.slice().sort((a,b)=>b.pts-a.pts||b.w-a.w||a.gp-b.gp||(b.gf-b.ga)-(a.gf-a.ga)),false);
  $('tbKey').innerHTML=mode==='conf'?'<li><i style="background:#0d7a48"></i>Плей-офф</li>':''};
 $('tbSw').addEventListener('click',e=>{const b=e.target.closest('.tab');if(!b||b.dataset.m===mode)return;mode=b.dataset.m;$('tbSw').querySelectorAll('.tab').forEach(x=>x.setAttribute('aria-selected',x===b));draw()});draw();

 /* строки матчей */
 const row=(m,fut)=>{const hw=!fut&&m.gf>m.ga,aw=!fut&&m.ga>m.gf,left=fut?JV.left(m.t):0;
  const when=fut?`${esc(m.t.slice(11))}${left<=0?'<small class="live">идёт</small>':''}`:`${dd(m.d)}<small>${esc(m.d.slice(11))}</small>`;
  return `<li class="lgm"><span class="when num">${when}</span><a class="t" href="${thref(m.h)}">${em(m.h)}<span class="${hw?'w':''}">${esc(nm(m.h))}</span></a>
   <span class="s num${fut?' vs':''}">${fut?'—':m.gf+':'+m.ga+(m.x?`<small>${m.x==='Б'?'буллиты':'овертайм'}</small>`:'')}</span>
   <a class="t a" href="${thref(m.a)}">${em(m.a)}<span class="${aw?'w':''}">${esc(nm(m.a))}</span></a></li>`};
 let html='',prev='';list.slice(0,40).forEach(m=>{const dk=m.t.slice(0,10);if(dk!==prev){prev=dk;const d=day(m.t);html+=`<li class="dayh" aria-hidden="true">${d.wd}, ${d.d} ${d.mon}</li>`}html+=row(m,true)});
 $('nextBox').innerHTML=`
  <div class="sec-head" data-rv><h2>Ближайшие матчи</h2><p>${lgp(LG)}${L.name}: ${list.length?`${list.length} ${plural(list.length,'матч','матча','матчей')}, ${head}. Время московское.`:'расписание появится позже.'}</p></div>
  ${list.length?`<ul class="lgml" data-rv>${html}</ul>`:'<p class="lgempty">В ближайшие дни матчей нет.</p>'}`;
 {const STEP=10;let n=STEP;$('resultsBox').innerHTML=`
  <div class="sec-head" data-rv><h2>Последние результаты</h2><p>${lgp(LG)}${L.name}: сыгранные матчи, новые сверху. Жирным выделен победитель; под счётом — овертайм или буллиты.</p></div>
  <ul class="lgml" id="rsList"></ul><div class="lgmore"><button class="btn btn-line" type="button" id="rsMore" hidden></button></div>`;
  const ul=$('rsList'),more=$('rsMore');const dr=()=>{ul.innerHTML=M.slice(0,n).map(m=>row(m,false)).join('')||'<li class="lgempty">Сыгранных матчей пока нет.</li>';more.hidden=n>=M.length;more.textContent=`Показать ещё ${Math.min(STEP,M.length-n)}`};
  more.addEventListener('click',()=>{n+=STEP;dr()});dr()}

 /* статистика */
 {const n=M.length,sum=M.reduce((a,m)=>a+m.gf+m.ga,0),ot=M.filter(m=>m.x==='ОТ').length,so=M.filter(m=>m.x==='Б').length,hw=M.filter(m=>m.gf>m.ga).length,aw=n-hw,pc=v=>n?Math.round(v/n*100):0;
  const reg=n-ot-so,hp=pc(hw),ap=n?100-hp:0,rp=pc(reg),op=pc(ot),sp=n?100-rp-op:0;
  $('statsBox').innerHTML=`<div class="sec-head" data-rv><h2>Статистика лиги</h2><p>${lgp(LG)}${L.name}, сезон ${esc(PL.season||'2026/27')}: считаем по ${n} ${plural(n,'сыгранному матчу','сыгранным матчам','сыгранным матчам')}.</p></div>
   <ul class="lgst" data-rv>
    <li><b class="num">${n?f1(sum/n,2):'—'}</b><span>голов за матч</span><em>всего ${sum}</em></li>
    <li><b class="num">${pc(ot+so)}<small>%</small></b><span>матчей дошли до овертайма</span><em>${ot} в овертайме, ${so} по буллитам</em></li>
    <li><b class="num">${hp}<small>%</small></b><span>побед хозяев</span><em>${hw} из ${n}</em></li>
    <li><b class="num">${n?f1(M.filter(m=>m.gf+m.ga>5).length/n*100,0):'—'}<small>%</small></b><span>матчей с тоталом больше 5,5</span><em>${M.filter(m=>m.gf+m.ga>5).length} из ${n}</em></li></ul>
   <div class="lgbar" data-rv><h3>Победы хозяев и гостей</h3>
    <div class="bar" role="img" aria-label="Победы хозяев ${hp} %, гостей ${ap} %"><i class="h" style="flex:${hw||.0001}">${hp>=8?hp+'%':''}</i><i class="a" style="flex:${aw||.0001}">${ap>=8?ap+'%':''}</i></div>
    <ul><li style="--k:#1d7a45">Победы хозяев: ${hp}% (${hw})</li><li style="--k:#1c63c4">Победы гостей: ${ap}% (${aw})</li></ul></div>
   <div class="lgbar" data-rv><h3>Как заканчиваются матчи</h3>
    <div class="bar" role="img" aria-label="Основное время ${rp} %, овертайм ${op} %, буллиты ${sp} %"><i class="h" style="flex:${reg||.0001}">${rp>=8?rp+'%':''}</i><i class="o" style="flex:${ot||.0001}">${op>=8?op+'%':''}</i><i class="d" style="flex:${so||.0001}">${sp>=8?sp+'%':''}</i></div>
    <ul><li style="--k:#1d7a45">Основное время: ${rp}%</li><li style="--k:#b8761a">Овертайм: ${op}%</li><li style="--k:#6b7585">Буллиты: ${sp}%</li></ul></div>
   <p class="note lgnote">Расчёт по сыгранным матчам сезона ${esc(PL.season||'2026/27')}.</p>`}

 /* игроки */
 const ini=n=>{const w=String(n).replace(/[^\p{L}\s'-]/gu,'').split(/[\s-]+/).filter(Boolean);return ((w[0]||'')[0]||'').toUpperCase()+((w.length>1?w[1]:'')[0]||'').toUpperCase()};
 const PS=(PL.players||[]).map(p=>{const lg=p.log||[];const s=i=>lg.reduce((a,r)=>a+(r[i]||0),0);
  const tid=LG==='nhl'?ABBR[p.t]:p.t,toiG=LG==='nhl'?(()=>{const t=lg.filter(r=>r[7]);return t.length?t.reduce((a,r)=>a+r[7],0)/t.length/60:null})():p.toi_avg;
  return {n:p.n,t:tid,img:p.img,gp:LG==='nhl'?lg.length:(p.gp||0),g:s(4),a:s(5),sog:s(6),pim:s(8),toi:toiG}}).filter(p=>p.t&&D.teams[p.t]);
 const who=(p,big)=>`<span class="pc"><span class="av">${esc(ini(p.n))}${p.img?`<img src="${esc(p.img)}" alt="" loading="lazy" referrerpolicy="no-referrer">`:''}</span><span><b>${esc(p.n)}</b><a href="${thref(p.t)}">${em(p.t)}<span>${esc(nm(p.t))}</span></a></span></span>`;
 let sortK='pts';
 const SK=[['pts','По очкам'],['g','По голам'],['a','По передачам']];
 const withP=PS.map(p=>({...p,pts:p.g+p.a}));
 $('playersBox').innerHTML=`
  <div class="sec-head" data-rv><h2>Бомбардиры и лидеры</h2><p>${lgp(LG)}${L.name}, сезон ${esc(PL.season||'2026/27')}: очки (голы + передачи), броски и время на льду. Данные матчей клубов.</p></div>
  <div class="lgsw tabs" role="tablist" id="plSw" aria-label="Сортировка">${SK.map(([k,t])=>`<button class="tab" role="tab" type="button" data-k="${k}" aria-selected="${k===sortK}">${t}</button>`).join('')}</div>
  <div class="tabscroll" id="plTop" style="max-width:1000px"></div>
  <div class="lgcard" style="margin-top:clamp(28px,3.4vw,48px)" id="plMore"></div>
  <a class="btn btn-ink lgall" href="../hockey/${L.all}">Все игроки ${L.name} →</a>`;
 const top=()=>{const r=withP.slice().sort((a,b)=>b[sortK]-a[sortK]||b.pts-a.pts||b.g-a.g||a.gp-b.gp).slice(0,15);
  const th=(k,t)=>`<th class="${k===sortK?'on':''}${k==='gp'?' hm':''}">${t}</th>`;
  $('plTop').innerHTML=`<table class="lgpt"><thead><tr><th>#</th><th>Игрок</th>${th('gp','И')}${th('g','Г')}${th('a','П')}${th('pts','О')}</tr></thead><tbody>${r.map((p,i)=>`<tr><td class="r">${i+1}</td><td class="pl">${who(p)}</td><td class="hm">${p.gp}</td><td class="${sortK==='g'?'on':''}">${p.g}</td><td class="${sortK==='a'?'on':''}">${p.a}</td><td class="${sortK==='pts'?'on':''}">${p.pts}</td></tr>`).join('')}</tbody></table>`;
  $('plTop').querySelectorAll('.av img').forEach(i=>i.addEventListener('error',()=>i.remove()))};
 $('plSw').addEventListener('click',e=>{const b=e.target.closest('.tab');if(!b||b.dataset.k===sortK)return;sortK=b.dataset.k;$('plSw').querySelectorAll('.tab').forEach(x=>x.setAttribute('aria-selected',x===b));top()});top();
 const mini=(title,arr,val,sub)=>`<div data-rv><h3>${title}</h3><ol class="lgpl">${arr.map((p,i)=>`<li><span class="r num">${i+1}</span><span class="av">${esc(ini(p.n))}${p.img?`<img src="${esc(p.img)}" alt="" loading="lazy" referrerpolicy="no-referrer">`:''}</span><span class="who"><b>${esc(p.n)}</b><a href="${thref(p.t)}">${em(p.t)}<span>${esc(nm(p.t))}</span></a></span><span class="val num">${val(p)}<small>${sub(p)}</small></span></li>`).join('')}</ol></div>`;
 const toiL=PS.filter(p=>p.toi&&p.gp>=5).sort((a,b)=>b.toi-a.toi).slice(0,10);
 const first=LG==='nhl'?mini('Броски по воротам · топ-10',PS.slice().sort((a,b)=>b.sog-a.sog||a.gp-b.gp).slice(0,10),p=>p.sog,p=>`за ${p.gp} ${plural(p.gp,'игру','игры','игр')}`)
  :mini('Штрафные минуты · топ-10',PS.filter(p=>p.pim>0).sort((a,b)=>b.pim-a.pim||a.gp-b.gp).slice(0,10),p=>p.pim,p=>`за ${p.gp} ${plural(p.gp,'игру','игры','игр')}`);
 $('plMore').innerHTML=first+mini('Время на льду · топ-10',toiL,p=>{const t=Math.round(p.toi*60);return Math.floor(t/60)+':'+String(t%60).padStart(2,'0')},p=>'в среднем за игру');
 $('plMore').querySelectorAll('.av img').forEach(i=>i.addEventListener('error',()=>i.remove()));
 JV.reveal();
}
Promise.all([fetch('../team/season.json').then(r=>r.json()),fetch('data/'+L.json).then(r=>r.json()).catch(()=>({players:[]}))]).then(([se,pl])=>build(se,pl))
 .catch(e=>{console.error(e);$('hero').innerHTML='<p class="lgempty">Данные загрузить не удалось.</p>'});
})();

/* пересчитать «свет арены» после отрисовки (иначе герой бледный до первой прокрутки) */
for(const t of [50,400,1200])setTimeout(()=>{dispatchEvent(new Event("resize"));dispatchEvent(new Event("scroll"))},t);
