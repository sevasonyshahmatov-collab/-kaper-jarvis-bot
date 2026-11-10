/* JARVIS v3a — страница футбольного клуба: football/team.html?id=<slug>. Данные — football/data/football.js (ESPN + расчёт модели).
   Разметка и стили — те же, что у хоккейной страницы команды (team.css); общие части — foot-kit.js. */
(()=>{
'use strict';
const {D,esc,fx,plural,T:TM,nm,CI,LGP,LGI,teamHref,day,dd,played,rOf,RES,RESF,gamesOf,stats,h2h,dots,radar,palette,clubColors,crest}=JVF;
const P=new URLSearchParams(location.search),ID=(P.get('id')||window.JV_TEAM_ID||'').toLowerCase();
const T=TM[ID];
const $=id=>document.getElementById(id);
const AX=D.axes;
if(!T){
 document.title='Клуб не найден · JARVIS';
 document.querySelector('.tmhero').classList.add('none');
 $('hero').innerHTML=`<header class="tmid tmnone" data-rv><a class="crumb" href="index.html#leagues"><span aria-hidden="true">←</span> Лиги и клубы</a><h1>Такого клуба нет</h1>
  <p class="lead">${ID?`По адресу «${esc(ID)}» клуба не нашлось.`:'В адресе не указан клуб.'} Выберите клуб на странице «Футбол»: там все ${Object.keys(TM).length} клубов шести лиг.</p>
  <div class="hero-cta"><a class="btn btn-tg" href="index.html#leagues">Лиги и клубы</a></div></header>`;
 ['table','games','players','picks'].forEach(id=>{const e=$(id);e.hidden=true;e.removeAttribute('data-zone')});
 document.documentElement.classList.add('tm-none');document.querySelector('.nav').hidden=true;return}
const lg=T.lg,L=D.leagues[lg],LN=L.name;
const cupOnly=!!L.cup;
let CTX=new URLSearchParams(location.search).get('ctx');
if(!JVF.CTXS.includes(CTX))CTX='league';
if(cupOnly)CTX=lg;
if(CTX!=='league'&&!(T.cups||[]).includes(CTX))CTX='league';
const CUP=CTX==='league'?null:CTX,EFF=CUP||lg,EL=D.leagues[EFF],EN=EL.name;
const inCtx=g=>CUP?g.c===CUP:(cupOnly?true:!g.c);
const oppCtx=g=>CUP?g.c===CUP:!g.c;
{const dh=document.documentElement;if(CUP){dh.dataset.theme=CUP;document.body.classList.add('ctx-cup');{const rh={table:'lt',trends:'lt',totals:'lt',next:'band',games:'lt'};Object.keys(rh).forEach(k=>{const e=document.getElementById(k);if(e)e.classList.add(rh[k])})}
 if(CUP==='ucl'){const sg=document.querySelector('.seg'),su=sg&&sg.querySelector('.seg-ucl');if(su){sg.querySelectorAll('a').forEach(x=>x.removeAttribute('aria-current'));su.setAttribute('aria-current','page')};const gu=[...document.querySelectorAll('.gnav a,.mpanel a')].filter(x=>/ucl\.html/.test(x.getAttribute('href')||''));if(gu.length){document.querySelectorAll('.gnav a[aria-current],.mpanel a[aria-current]').forEach(x=>x.removeAttribute('aria-current'));gu.forEach(x=>x.setAttribute('aria-current','page'))}}   /* кнопки «ЛЧ» в шапке больше нет (меню 08.11) — без неё страница падала пустой (09.11) */const s1=document.createElement('script');s1.src='../assets/ucl-sky.js';document.body.appendChild(s1)}
 else if(dh.dataset.theme==='ucl'||dh.dataset.theme==='uel'){dh.dataset.theme='arena'}}
const ctxHref=k=>k===lg?`team.html?id=${encodeURIComponent(ID)}`:`team.html?id=${encodeURIComponent(ID)}&ctx=${k}`;
const RC=CUP?(D.tables[CUP]||[]).find(x=>x.id===ID)||{place:0,gp:0,w:0,d:0,l:0,gf:0,ga:0,pts:0}:T;
const CX=CUP?(T.cx||{})[CUP]:null;
const AXS=CUP?D.axesCup:D.axes;
const PAL=document.documentElement.dataset.pal,pv=k=>{const v=getComputedStyle(document.documentElement).getPropertyValue(k).trim();return /^#[0-9a-f]{3,6}$/i.test(v)?v:null};
const CP=CUP?(CUP==='ucl'?{stops:['#0b1a4a','#081340','#06102e'],text:'#ffffff',acc:'#5fd8ff',accL:'#5fd8ff',base:'#0b1a4a'}:{stops:['#2a1608','#150d06','#0a0704'],text:'#ffffff',acc:'#ffa04a',accL:'#ffa04a',base:'#2a1608'}):palette(clubColors(T)),acc=PAL&&pv('--ink')||CP.acc;
document.title=`${T.n}${CUP?' · '+EN:''} — матчи сезона, место в таблице, сила команды · JARVIS`;
{const st=document.body.style;[['--c1',CP.stops[0]],['--c2',CP.stops[1]],['--c3',CP.stops[2]],['--con',CP.text],['--cacc',CP.acc],['--team',CP.accL],['--cbase',CP.base]].forEach(([k,v])=>st.setProperty(k,v));
 document.body.classList.toggle('on-light',CP.text!=='#ffffff');
 const m=document.querySelector('meta[name=theme-color]');if(m)m.content=CP.stops[0];
}
document.body.dataset.lg=lg;
const all=T.games.slice().sort((a,b)=>a.d<b.d?1:-1).reverse();
const ctxAll=all.filter(inCtx),real=ctxAll.filter(played),future=ctxAll.filter(g=>!played(g)),S=stats(ID,inCtx);
const listAll=(CUP||cupOnly)?ctxAll:all;
/* реальная линия рынка и расчёт модели из data/lines.js и data/model.js — для матчей окна данных; кэфы и вероятности — с точки зрения клуба */
const hm=t=>{const m=Date.parse(t);return isNaN(m)?'':new Date(m+3*36e5).toISOString().slice(11,16)};
T.games.filter(g=>!played(g)).forEach(g=>{const hh=g.h?ID:g.o,aa=g.h?g.o:ID,key=`${g.c||lg}|${g.d.slice(0,10)}|${hh}|${aa}`,ln=(window.JV_LINES||{})[key],md=(window.JV_MODEL||{})[key],sw=a=>g.h?a:[a[2],a[1],a[0]];
 if(ln){g.k=sw([ln.p1,ln.x,ln.p2]);g.kn=`Линия, ${hm(ln.t)}`}
 else if(g.k)g.kn='Линия на матч';  /* источник не называем (владелец 05.11) */
 if(md){g.pr=sw([md.p1,md.x,md.p2]);g.ov=md.over;g.ot=md.tot;g.bt=md.btts}});
const startMs=d=>Date.parse(d.slice(0,10)+'T'+(d.slice(11,16)||'00:00')+':00+03:00');
const nextG=future.find(g=>startMs(g.d)>Date.now()-3*36e5)||future[0];
const pts=g=>g.gf>g.ga?3:g.gf===g.ga?1:0;
const TGICO='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 3.2 2.9 10.4c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.8 5.6c.2.6.9.8 1.4.4l2.6-2.2 4.8 3.5c.6.4 1.4.1 1.6-.7l3.1-15.1c.2-1-.7-1.7-1.6-1.3z"/></svg>';
const followBtn=(cls='')=>`<a class="follow ${cls}" href="https://t.me/jarvibet?start=follow_${encodeURIComponent(ID)}" target="_blank" rel="noopener" title="Прогноз и итог матча — в Telegram">${TGICO}<span>Прогнозы на матчи клуба — в Telegram</span></a>`;
const bd=(D.built||'').slice(0,10),bdd=bd?day(bd):null,asOf=bdd?`на ${bdd.d} ${bdd.mon}`:'';
const tbl0=Object.fromEntries((D.tables[EFF]||[]).map(r=>[r.id,r])),leagueRows=EL.ids.map(s=>({...TM[s],...(tbl0[s]||{})})).sort((a,b)=>a.place-b.place);
const cupLab=k=>(D.leagues[k]||{}).short||k;
const swH=(!cupOnly&&(T.cups||[]).length)?`<ul class="ctxsw" aria-label="Турнир: лига или еврокубок">${[lg,...T.cups].map(k=>{const r=k===lg?T:(D.tables[k]||[]).find(x=>x.id===ID);
  return `<li><a href="${ctxHref(k)}"${k===EFF?' aria-current="page"':''}>${LGP(k)}<span>${esc(D.leagues[k].name)}</span><small>${r?r.place+'-е место':''}</small></a></li>`}).join('')}</ul>`:'';
const eloLine=CX?`<p class="eloline"><b>${CX.e}</b>Elo · ${CX.r}-е место в рейтинге Европы${CX.est?' (оценка)':''}<small>Club Elo, на ${bdd?bdd.d+' '+bdd.mon:''}</small></p>`:'';
/* серия: победы, матчи без поражений или поражения — от 3 */
const streak=(()=>{const a=real;const run=f=>{let n=0;for(let i=a.length-1;i>=0&&f(a[i]);i--)n++;return n};
 const w=run(g=>g.gf>g.ga),u=run(g=>g.gf>=g.ga),l=run(g=>g.gf<g.ga);
 if(w>=3)return {k:'w',n:w,t:'Серия побед',seq:a.slice(-w)};
 if(u>=3)return {k:'u',n:u,t:'Без поражений',seq:a.slice(-u)};
 if(l>=3)return {k:'l',n:l,t:'Серия поражений',seq:a.slice(-l)};return null})();
const streakHtml=streak?`<p class="tmstreak ${streak.k}" aria-label="${streak.t}: ${streak.n}"><span class="sk">${streak.t}:</span><b class="num">${streak.n}</b><span class="dots" aria-hidden="true">${streak.seq.slice(-10).map(g=>`<i class="${g.gf>g.ga?'w':g.gf===g.ga?'d':'l'}"></i>`).join('')}</span></p>`:'';

/* ── 1. шапка клуба + шестиугольник силы ── */
$('hero').innerHTML=`
 <header class="tmid" data-rv>
  <div class="tmtop"><a class="crumb" href="${CUP==='ucl'?'ucl.html':'index.html#lg-'+encodeURIComponent(EFF)}"><span aria-hidden="true">←</span> ${CUP==='ucl'?'Лига чемпионов':'Лиги и клубы · '+esc(EN)}</a>${followBtn('in-hero')}</div>
  <div class="tmrow"><span class="tmcrest">${CI(ID)}</span>
   <div class="tmname">${swH?swH+`<p class="tmlg"><a class="lglnk" href="league.html?lg=${esc(EFF)}" title="Страница лиги">${esc(EN)}: страница лиги</a></p>`:`<p class="tmlg"><a class="lglnk" href="league.html?lg=${esc(EFF)}" title="Страница лиги">${LGP(EFF)}<span>${esc(EN)}</span></a><span class="dot">·</span><span>сезон ${esc(D.season)}</span></p>`}<h1 class="tmh1"><span class="l">${esc(T.n)}</span></h1></div></div>
  <div class="tmplace"><b class="num">${RC.place}</b><span>-е место<br>${CUP?'в общем этапе':'в лиге'}: ${esc(EN)}</span></div>
  <ul class="tmpills" aria-label="Коротко о сезоне">
   <li><b class="num">${RC.pts}</b><span>${plural(RC.pts,'очко','очка','очков')}</span></li>
   <li><b class="num">${RC.gp}</b><span>${plural(RC.gp,'игра','игры','игр')}</span></li>
   <li><b class="num">${RC.w}–${RC.d}–${RC.l}</b><span>победы–ничьи–поражения</span></li>
   <li><b class="num">${RC.gf}:${RC.ga}</b><span>мячи</span></li></ul>
  ${streakHtml}
 </header>
 <div class="tmpower" data-rv>
  <div class="ph"><h2 class="h3">Шестиугольник силы${CUP?' · '+esc(EL.short):''}</h2></div>
  <div class="rad">${radar([{v:CUP?CX.axes:T.axes,c:acc,name:T.n}],AXS)}</div>
  <div class="legend"><span><i style="border-color:${esc(acc)}"></i>${esc(T.n)}</span><span><i class="d"></i>${CUP?'середина турнира':'середина лиги'}</span></div>${eloLine}
 </div>`;
JV.fitH1(document.querySelector('.tmh1'),30);   /* название клуба без разрыва слова (09.11) */

/* ── плашка «Игроки команды» под формой → football/players.html?team=<id> (владелец 03.11) ── */
const plTop=(T.sc||[]).slice(0,3);
const plIni=n=>String(n).split(/\s+/).filter(Boolean).map(w=>w[0]).slice(0,2).join('').toUpperCase();
const plCard=()=>`<a class="plcard" href="players.html?team=${encodeURIComponent(ID)}" aria-label="Все игроки ${esc(T.n)}: голы и карточки «n из N»">
  <span class="sl">Игроки: ${esc(T.n)}</span>
  ${plTop.length?`<ol class="pltop">${plTop.map(x=>`<li><i class="pav">${esc(plIni(x.n))}</i><b>${esc(x.n)}</b><span><em>${x.g}</em> ${plural(x.g,'гол','гола','голов')}</span></li>`).join('')}</ol>`:''}
  <span class="plgo">Все игроки, фото и «n из N»: забьёт, карточка <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></span></a>`;

/* ── 2. место в таблице и статистика ── */
const A=CUP?CX.axes:T.axes,AXT=CUP?D.axesCup:AX,f2=v=>fx(v,2),f1=v=>fx(v,1);
const tile=(lab,val,unit,i,sub)=>`<div class="st"><span class="sl">${lab}</span><b class="num">${val}<small>${unit}</small></b>
  ${i!=null&&A[i]!=null?`<span class="bar" aria-label="${A[i]} из 100"><i style="--w:${A[i]}%"></i></span><span class="ss">${esc(AXT[i])} — <b>${A[i]}</b> из 100 ${CUP?'среди участников: '+esc(EN):'в лиге: '+esc(EN)}</span>`:`<span class="ss">${sub||''}</span>`}</div>`;
const ZONE={epl:[[1,4,'z1'],[5,5,'z2'],[18,20,'z4']],laliga:[[1,4,'z1'],[5,6,'z2'],[18,20,'z4']],seriea:[[1,4,'z1'],[5,6,'z2'],[18,20,'z4']],
 bundesliga:[[1,4,'z1'],[5,6,'z2'],[16,16,'z3'],[17,18,'z4']],ligue1:[[1,3,'z1'],[4,5,'z2'],[16,16,'z3'],[17,18,'z4']],rpl:[[1,3,'z1'],[15,16,'z4']],ucl:[[1,8,'z1'],[9,24,'z2'],[25,36,'z4']],uel:[[1,8,'z1'],[9,24,'z2'],[25,36,'z4']]}[lg]||[];
const zc=p=>(ZONE.find(x=>p>=x[0]&&p<=x[1])||[])[2]||'';
const last5=real.slice(-5);
const homeG=real.filter(g=>g.h),awayG=real.filter(g=>!g.h);
const ppg=a=>a.length?a.reduce((s,g)=>s+pts(g),0)/a.length:null;
$('tableBox').innerHTML=`
 <div class="sec-head" data-rv><h2>Место в таблице</h2></div>
 <div class="tmgrid">
  <div class="tmtable" data-rv><table class="table stand">
   <thead><tr><th>#</th><th>Клуб</th><th class="ra">И</th><th class="ra hide-s">В</th><th class="ra hide-s">Н</th><th class="ra hide-s">П</th><th class="ra hide-s">Мячи</th><th class="ra">О</th></tr></thead>
   <tbody>${leagueRows.map(x=>`<tr class="${x.id===ID?'me':''} ${zc(x.place)}"${x.id===ID?' aria-current="true"':''}><td>${x.place}</td>
    <td><a class="cl" href="${teamHref(x.id,CUP)}">${CI(x.id)}<span>${esc(x.n)}</span></a></td><td class="ra">${x.gp}</td><td class="ra hide-s">${x.w}</td><td class="ra hide-s">${x.d}</td><td class="ra hide-s">${x.l}</td>
    <td class="ra hide-s">${x.gf}:${x.ga}</td><td class="ra pts">${x.pts}</td></tr>`).join('')}</tbody></table></div>
  <div class="tmstats" id="stats" data-rv>
   <div class="stg">
    ${CUP?tile('Сила: рейтинг Elo',CX.e,'',0).replace(/ из 100 среди участников/,' из 100 среди участников'):''}
    ${tile('Забивает за игру',S.gf==null?'—':f2(S.gf),'',CUP?1:0)}
    ${tile('Пропускает за игру',S.ga==null?'—':f2(S.ga),'',CUP?2:1)}
    ${CUP?'':tile('Очки за игру',f2(S.ppg),'',5)}
    ${tile('Удары за игру',S.sh==null?'—':f1(S.sh),'',null,S.sot==null?'':`в створ — ${f1(S.sot)}; соперники — ${f1(S.shA)}`)}
    ${tile('Угловые за игру',S.cor==null?'—':f1(S.cor),'',null,S.corA==null?'':`соперники — ${f1(S.corA)}`)}
    ${tile('Дома · в гостях',`${f2(ppg(homeG))}`,` · ${f2(ppg(awayG))}`,null,'очков за игру дома и на выезде')}
   </div>
   <div class="formbox"><span class="sl">Форма — последние 5 игр</span>
    <ol class="frm" aria-label="Последние 5 игр, слева раньше">${last5.map(g=>{const r=rOf(g),t=`${RESF[r]}: ${nm(g.o)} ${g.gf}:${g.ga}`;return `<li class="${r}" title="${esc(t)}" aria-label="${esc(t)}"><b><img src="${crest(g.o)}" alt="" loading="lazy"></b><span>${g.gf}:${g.ga}</span></li>`}).join('')}</ol>
    <p class="ss">За 5 игр — <b>${last5.reduce((s,g)=>s+pts(g),0)} ${plural(last5.reduce((s,g)=>s+pts(g),0),'очко','очка','очков')}</b>.</p></div>
   ${''/* плашка «Игроки» скрыта до готовности портретов (владелец 04.11): ${plCard()} */}
  </div>
 </div>`;

/* ── 3. матчи сезона ── */
const kf=v=>v==null?'—':f2(v);
const cb=g=>g.c?`<span class="cupb ${esc(g.c)}" title="${esc(D.leagues[g.c].name)}">${esc(cupLab(g.c))}</span>`:'';
const row=g=>{const t=day(g.d),opp=`<a class="op" href="${teamHref(g.o,g.c||CUP)}">${CI(g.o)}<span>${esc(nm(g.o))}</span>${cb(g)}</a>`;
 const when=`<span class="gd"><b>${t.d} ${t.mon}</b><small>${t.wd}${t.tm?' · '+t.tm:''}</small></span>`;
 const ha=`<span class="ha ${g.h?'h':'a'}" title="${g.h?'дома':'в гостях'}">${g.h?'Д':'В'}</span>`;
 if(played(g)){const r=rOf(g);return `<li class="g ${g.h?'home':'away'}">${when}${ha}${opp}<span class="sc num">${g.gf}:${g.ga}</span><span class="rs ${r}" title="${RESF[r]}">${RES[r]}</span></li>`}
 return `<li class="g fut ${g.h?'home':'away'}">${when}${ha}${opp}${g.k?`<span class="kxw"><span class="kx num" aria-label="Линия: победа ${esc(T.n)} ${kf(g.k[0])}, ничья ${kf(g.k[1])}, победа соперника ${kf(g.k[2])}"><span><small>П</small>${kf(g.k[0])}</span><span><small>Х</small>${kf(g.k[1])}</span><span><small>П</small>${kf(g.k[2])}</span></span>${g.kn||g.pr?`<small class="kn">${g.kn?esc(g.kn):''}${g.pr?`${g.kn?' · ':''}модель: ${g.pr.map(v=>Math.round(v*100)).join(' · ')} %`:''}</small>`:''}</span>`
  :g.pr?`<span class="kx3 num" aria-label="Расчёт модели: победа ${esc(T.n)} ${Math.round(g.pr[0]*100)} %, ничья ${Math.round(g.pr[1]*100)} %, победа соперника ${Math.round(g.pr[2]*100)} %">${g.pr.map(v=>Math.round(v*100)).join(' · ')} %</span>`:''}</li>`};
const wins=real.filter(g=>g.gf>g.ga).length,draws=real.filter(g=>g.gf===g.ga).length,losses=real.length-wins-draws;
const gfS=real.reduce((a,g)=>a+g.gf,0),gaS=real.reduce((a,g)=>a+g.ga,0);
$('gamesBox').innerHTML=`
 <div class="sec-head" data-rv><h2>Матчи сезона</h2></div>
 <ul class="gsum" aria-label="Итоги сыгранных матчей" data-rv>
  <li><b class="num">${real.length}</b><span>${plural(real.length,'матч','матча','матчей')} сыграно</span></li>
  <li class="w"><b class="num">${wins}</b><span>${plural(wins,'победа','победы','побед')}</span></li>
  <li><b class="num">${draws}</b><span>${plural(draws,'ничья','ничьи','ничьих')}</span></li>
  <li class="l"><b class="num">${losses}</b><span>${plural(losses,'поражение','поражения','поражений')}</span></li>
  <li><b class="num">${gfS}:${gaS}</b><span>мячи забито : пропущено</span></li></ul>
 <div class="gfilter" role="group" aria-label="Какие матчи показать" data-rv><div class="seg"><button type="button" aria-pressed="true" data-f="all">Все</button><button type="button" aria-pressed="false" data-f="home">Дома</button><button type="button" aria-pressed="false" data-f="away">В гостях</button></div></div>
 <div class="glist" id="glist" data-f="all">
  ${listAll.some(g=>!played(g))?`<h3 class="gh">Ближайшие<span>${listAll.filter(g=>!played(g)).length}</span></h3><ol class="gs">${listAll.filter(g=>!played(g)).map(row).join('')}</ol>`:''}
  <h3 class="gh">Сыгранные<span>${listAll.filter(played).length}</span></h3>
  <ol class="gs">${listAll.filter(played).reverse().map(row).join('')}</ol>
 </div>`;
document.querySelectorAll('.gfilter button').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.gfilter button').forEach(x=>x.setAttribute('aria-pressed',x===b));$('glist').dataset.f=b.dataset.f}));

/* ── 4. наши ставки: боевых итогов по клубам пока нет — честно говорим об этом ── */
$('picksBox').innerHTML=`
 <div class="sec-head" data-rv><h2>Наши ставки на ${esc(T.n)}</h2></div>
 <div class="pkempty" data-rv><p>На матчи ${esc(T.n)} ставок канала пока не было. Как только модель найдёт ставку — она появится здесь и в канале.</p><a class="btn btn-ink" href="https://t.me/jarvibet" target="_blank" rel="noopener">Открыть канал в Telegram</a></div>`;

/* ── 2а. следующий матч ── */
if(nextG){
 const t=day(nextG.d),oh=nextG.h,k=nextG.k,o=nextG.o;
 const cr2=(sl,cls)=>`<span class="nmc ${cls}"><a href="${teamHref(sl,CUP)}"><span class="nmcr">${CI(sl)}</span><b>${esc(nm(sl))}</b></a></span>`;
 const mdl=nextG.pr?`<p class="mdl" aria-label="Расчёт модели"><span>1Х2: <b>${nextG.pr.map(v=>Math.round(v*100)).join(' · ')} %</b></span><span>тотал больше ${fx(nextG.ot||2.5,1)}: <b>${Math.round(nextG.ov*100)} %</b></span><span>обе забьют: <b>${Math.round(nextG.bt*100)} %</b></span></p>`:'';
 $('nextBox').innerHTML=`
  <div class="sec-head" data-rv><h2>Следующий матч</h2></div>
  <article class="nmatch" data-rv aria-label="${esc(T.n)} — ${esc(nm(o))}, ${t.d} ${t.mon}, ${t.tm} МСК">
   <div class="nmteams">${cr2(oh?ID:o,'a')}<span class="nmmid"><span class="nmdt"><b>${t.d} ${t.mon}</b><small>${t.wd}${t.tm?' · '+t.tm+' МСК':''}</small></span><span class="nmha ${oh?'h':'a'}">${oh?'Дома':'В гостях'}</span></span>${cr2(oh?o:ID,'b')}</div>
   <div class="nmside">
    ${k?`<div class="nmline"><span class="sl">${nextG.kn?esc(nextG.kn):'Линия на матч'}</span><ol class="kx" aria-label="Линия: ${esc(T.n)} ${kf(k[0])}, ничья ${kf(k[1])}, ${esc(nm(o))} ${kf(k[2])}">${k.map((v,i)=>`<li><b class="num">${kf(v)}</b><small>${['П1','Х','П2'][i]}</small></li>`).join('')}</ol>${mdl}</div>`
     :`<div class="nmline"><span class="sl">Линия появится ближе к матчу</span>${mdl}</div>`}
    <div class="nmcd" id="nmcd"><span class="sl">До начала</span><b class="num" id="nmcdv">—</b></div>
    <div class="nmrow"><a class="btn btn-line nmgo" id="nmgo" href="${JV.matchPage('../',nextG.c||lg,nextG.d,oh?ID:o,oh?o:ID)}" data-fb="index.html#matches">Разбор матча</a>
     <a class="nmrem" href="${JV.ics((oh?T.n:nm(o))+' — '+(oh?nm(o):T.n),nextG.d,120)}" download="match.ics" title="Событие в календаре телефона, напоминание за 15 минут">${JV.BELL}<span>Напомнить</span></a></div>
   </div></article>
  <details class="nmh2h" id="nmh2h" hidden></details>`;
 $('next').hidden=false;
 {const go=$('nmgo');if(go)fetch(go.href,{method:'HEAD'}).then(r=>{if(!r.ok){go.href=go.dataset.fb;go.textContent='Все матчи тура'}}).catch(()=>{go.href=go.dataset.fb;go.textContent='Все матчи тура'})}   /* страницы матча ещё нет — к матчам тура, как было */
 /* градиент цветов клубов как у хоккея и карточек «Матчи дня»: слева хозяева, справа гости, стык — по колонке с датой (владелец 09.11) */
 {const box=document.querySelector('#nextBox .nmatch'),mid=box&&box.querySelector('.nmmid');
  const h2r=h=>{h=String(h||'').replace('#','');if(h.length===3)h=h.replace(/./g,'$&$&');const n=parseInt(h,16);return isNaN(n)||h.length!==6?null:[n>>16&255,n>>8&255,n&255]};
  const hsl=([r,g,b])=>{r/=255;g/=255;b/=255;const x=Math.max(r,g,b),n=Math.min(r,g,b),l=(x+n)/2;let h=0,s=0;if(x!==n){const d=x-n;s=l>.5?d/(2-x-n):d/(x+n);h=x===r?(g-b)/d+(g<b?6:0):x===g?(b-r)/d+2:(r-g)/d+4;h*=60}return [h,s,l]};
  const sc=([h,s,l])=>s>=.25&&l>.1&&l<.93?s*(1-Math.abs(l-.42)):-1,hd=(a,b)=>{const d=Math.abs(a-b)%360;return d>180?360-d:d};
  const cands=id=>((TM[id]||{}).c||[]).map(h2r).filter(Boolean).map(hsl).sort((x,y)=>sc(y)-sc(x));
  const H=oh?ID:o,A=oh?o:ID,CA=cands(H),CB=cands(A);
  let a=CA[0]&&sc(CA[0])>0?CA[0]:[218,.3,.34],b=CB[0]&&sc(CB[0])>0?CB[0]:[222,.3,.26];
  if(hd(a[0],b[0])<32&&Math.abs(a[2]-b[2])<.2){const alt=CB.find(c=>sc(c)>0&&hd(a[0],c[0])>=40);b=alt||[b[0]+34,b[1],b[2]+.1]}
  const nm_=([h,s,l])=>`hsl(${Math.round(h)} ${Math.round(Math.min(.85,Math.max(.55,s))*100)}% ${Math.round(Math.min(.40,Math.max(.30,l))*100)}%)`;
  if(box&&mid){box.classList.add('grad');box.style.setProperty('--h1',nm_(a));box.style.setProperty('--h2',nm_(b));
   const fit=()=>{const r=box.getBoundingClientRect(),q=mid.getBoundingClientRect();if(r.width)box.style.setProperty('--mx',((q.left+q.width/2-r.left)/r.width*100).toFixed(1)+'%')};
   fit();addEventListener('resize',fit);if(document.fonts)document.fonts.ready.then(fit)}}
 const cdv=$('nmcdv'),st0=startMs(nextG.d);
 const tick=()=>{const df=st0-Date.now();if(isNaN(st0)||df<=0){cdv.textContent=isNaN(st0)?'—':'матч начался';return}
  const m=Math.floor(df/6e4),d1=Math.floor(m/1440),hh=Math.floor(m%1440/60),mm=m%60;
  cdv.innerHTML=(d1?`${d1}<small>${plural(d1,'день','дня','дней')}</small> `:'')+`${hh}<small>ч</small> ${mm}<small>мин</small>`};
 tick();setInterval(tick,30000);
}

/* ── 2б. тренды: «n из N» по сыгранным матчам, последние 10 / весь сезон, все / дома / в гостях ── */
{const box=$('trendsBox'),st={per:'l10',ven:'all'};
 const DEF=[
  {id:'ov',t:'Тотал больше 2,5',ok:g=>g.gf+g.ga>2.5},
  {id:'un',t:'Тотал меньше 2,5',ok:g=>g.gf+g.ga<2.5},
  {id:'bt',t:'Обе команды забили',ok:g=>g.gf>0&&g.ga>0},
  {id:'win',t:'Победа',ok:g=>g.gf>g.ga},
  {id:'dr',t:'Ничья',ok:g=>g.gf===g.ga},
  {id:'nl',t:'Не проиграла',ok:g=>g.gf>=g.ga},
  {id:'sc2',t:'Забила 2 и больше',ok:g=>g.gf>=2},
  {id:'cs',t:'Сухой матч (не пропустила)',ok:g=>g.ga===0}];
 const calc=()=>{let a=real.filter(g=>st.ven==='all'||(st.ven==='home'?g.h:!g.h));if(st.per==='l10')a=a.slice(-10);
  const r=DEF.map(d=>({...d,N:a.length,n:a.filter(d.ok).length,seq:a.map(d.ok)})).filter(x=>x.N>=1);
  return r.sort((x,y)=>Math.abs(y.n/y.N-.5)-Math.abs(x.n/x.N-.5))};
 const unit={all:'',home:' домашних',away:' гостевых'};
 const draw=()=>{const r=calc(),scope=st.per==='l10'?`последних${unit[st.ven]}`:`${unit[st.ven]?unit[st.ven].trim()+' ':''}матчей сезона`;
  $('trList').innerHTML=r.length?r.map(x=>{const txt=`${x.t} — ${x.n} из ${x.N} ${scope}`;
   return `<li class="tr" aria-label="${esc(txt)}"><span class="trt">${esc(x.t)}</span><span class="trd" aria-hidden="true">${x.seq.map(v=>`<i class="${v?'y':'n'}"></i>`).join('')}</span>
   <span class="trn"><b class="num">${x.n} из ${x.N}</b><small>${esc(scope)}${x.N<5?' · мало матчей':''}</small></span></li>`}).join('')
   :`<li class="tr none">В таком срезе пока нет сыгранных матчей.</li>`};
 if(real.length>=1){
  box.innerHTML=`<div class="sec-head" data-rv><h2>Тренды${real.length<5?'<span class="fewn">мало матчей</span>':''}</h2></div>
   <div class="trctl" data-rv><div class="gfilter"><div class="seg" id="trPer" role="group" aria-label="Период"><button type="button" aria-pressed="true" data-v="l10">Последние 10</button><button type="button" aria-pressed="false" data-v="all">Весь сезон</button></div></div>
    <div class="gfilter"><div class="seg" id="trVen" role="group" aria-label="Где играли"><button type="button" aria-pressed="true" data-v="all">Все</button><button type="button" aria-pressed="false" data-v="home">Дома</button><button type="button" aria-pressed="false" data-v="away">В гостях</button></div></div></div>
   <ol class="trs" id="trList" data-rv></ol>`;
  $('trends').hidden=false;
  for(const [id,key] of [['trPer','per'],['trVen','ven']])$(id).addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
   st[key]=b.dataset.v;document.querySelectorAll('#'+id+' button').forEach(x=>x.setAttribute('aria-pressed',x===b));draw()});
  draw()}}

/* ── 2б². тоталы и дом/выезд: гистограммы мячей ── */
{const box=$('totalsBox'),sec=$('totals'),st={per:'all',ven:'all'};
 if(box&&sec&&real.length>=1){
 const pc=(n,N)=>N?Math.round(n/N*100)+'%':'—';
 const hist=(title,sub,vals,labels,lines,N)=>{
  const n=labels.length,cnt=labels.map((_,i)=>vals.filter(v=>Math.min(v,n-1)===i).length),mx=Math.max(1,...cnt);
  const ln=lines.map(l=>{const k=vals.filter(v=>v>l.t).length;return {...l,k,txt:`больше ${String(l.t).replace('.',',')} — ${k} из ${N}`}});
  return `<figure class="hg" role="img" aria-label="${esc(title)}: ${esc(labels.map((l,i)=>l+' — '+cnt[i]).join(', '))}">
   <figcaption><b>${esc(title)}</b><small>${esc(sub)}</small></figcaption>
   <div class="hp" style="--n:${n}">${cnt.map(c=>`<span class="hc"><i class="hb" style="height:${(c/mx*76).toFixed(1)}%"></i><b class="hn num" style="bottom:calc(${(c/mx*76).toFixed(1)}% + 3px)">${c}</b></span>`).join('')}
    ${ln.map(l=>`<span class="hl" style="left:${(l.pos/n*100).toFixed(2)}%"><em>${esc(String(l.t).replace('.',','))}</em></span>`).join('')}</div>
   <div class="hx" style="--n:${n}">${labels.map(l=>`<span>${esc(l)}</span>`).join('')}</div>
   <ul class="hlg">${ln.map(l=>`<li><i></i>${esc(l.txt)}</li>`).join('')}</ul></figure>`};
 const draw=()=>{
  let a=real.filter(g=>st.ven==='all'||(st.ven==='home'?g.h:!g.h));if(st.per==='l10')a=a.slice(-10);
  const N=a.length,scope=st.per==='l10'?`последних ${N}`:`${N}`,unit={all:'матчей',home:'домашних матчей',away:'гостевых матчей'}[st.ven];
  const tot=a.map(g=>g.gf+g.ga),avgT=N?tot.reduce((x,y)=>x+y,0)/N:0,avgF=N?a.reduce((x,g)=>x+g.gf,0)/N:0,avgA=N?a.reduce((x,g)=>x+g.ga,0)/N:0;
  const sub=`${scope} ${unit}`;
  $('tsOut').innerHTML=N<1?`<p class="tsnone">В таком срезе пока нет сыгранных матчей.</p>`:`
   <div class="tsbig"><div><b class="num">${f2(avgT)}</b><span>средний тотал матча</span></div><div><b class="num">${f2(avgF)}</b><span>забивает ${esc(T.n)} за игру</span></div><div><b class="num">${f2(avgA)}</b><span>пропускает за игру</span></div></div>
   <div class="hgs">
    ${hist('Сколько мячей в матчах',sub,tot,['0','1','2','3','4','5+'],[{t:1.5,pos:2},{t:2.5,pos:3},{t:3.5,pos:4}],N)}
    ${hist(`Индивидуальный тотал ${T.n}`,sub,a.map(g=>g.gf),['0','1','2','3','4+'],[{t:0.5,pos:1},{t:1.5,pos:2}],N)}
    ${hist('Сколько пропускает',sub,a.map(g=>g.ga),['0','1','2','3','4+'],[{t:0.5,pos:1},{t:1.5,pos:2}],N)}
   </div>`};
 box.innerHTML=`<div class="sec-head" data-rv><h2>Тоталы и дом/выезд${real.length<5?'<span class="fewn">мало матчей</span>':''}</h2></div>
  <div class="trctl" data-rv><div class="gfilter"><div class="seg" id="tsPer" role="group" aria-label="Период"><button type="button" aria-pressed="true" data-v="all">Весь сезон</button><button type="button" aria-pressed="false" data-v="l10">Последние 10</button></div></div>
   <div class="gfilter"><div class="seg" id="tsVen" role="group" aria-label="Где играли"><button type="button" aria-pressed="true" data-v="all">Все</button><button type="button" aria-pressed="false" data-v="home">Дома</button><button type="button" aria-pressed="false" data-v="away">В гостях</button></div></div></div>
  <div id="tsOut" data-rv></div>
  <h3 class="dvh" data-rv>Дома и в гостях</h3><div class="dvg" id="haBox" data-rv></div>`;
 sec.hidden=false;
 for(const [id,key] of [['tsPer','per'],['tsVen','ven']])$(id).addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
  st[key]=b.dataset.v;document.querySelectorAll('#'+id+' button').forEach(x=>x.setAttribute('aria-pressed',x===b));draw()});
 const side=h=>{const a=real.filter(g=>!!g.h===h),N=a.length,w=a.filter(g=>g.gf>g.ga).length,d=a.filter(g=>g.gf===g.ga).length,l=N-w-d;
  const gf=N?a.reduce((x,g)=>x+g.gf,0)/N:0,ga=N?a.reduce((x,g)=>x+g.ga,0)/N:0,tt=gf+ga,o25=a.filter(g=>g.gf+g.ga>2.5).length,bt=a.filter(g=>g.gf>0&&g.ga>0).length;
  return {N,w,d,l,wp:N?w/N:0,gf,ga,tt,o25,bt,form:a.slice(-5)}};
 const H=side(true),Aw=side(false);
 const best=(k,hi)=>H.N&&Aw.N&&H[k]!==Aw[k]?((H[k]>Aw[k])===hi?'h':'a'):'';
 const rows=[['Матчей',s=>s.N,null],['Победы–ничьи–поражения',s=>`${s.w}–${s.d}–${s.l}`,null],['Побед, %',s=>pc(s.w,s.N),'wp',null,1],['Забито за игру',s=>f2(s.gf),'gf',null,1],['Пропущено за игру',s=>f2(s.ga),'ga',null,0],
  ['Средний тотал',s=>f2(s.tt),null],['Тотал больше 2,5, % матчей',s=>pc(s.o25,s.N),null,s=>`${s.o25} из ${s.N}`],['Обе забили, % матчей',s=>pc(s.bt,s.N),null,s=>`${s.bt} из ${s.N}`]];
 const card=(s,name,cls)=>`<article class="dvc ${cls}" aria-label="${name}"><h4>${name}</h4><dl>${rows.map(([t,fn,k,sm,hi])=>{const bst=k&&best(k,!!hi)===(cls==='h'?'h':'a');
  return `<div class="${bst?'bst':''}"><dt>${esc(t)}</dt><dd><b class="num">${esc(fn(s))}</b>${sm?`<small>${esc(sm(s))}</small>`:''}</dd></div>`}).join('')}</dl>
  <div class="dvf"><span>Форма, последние 5</span><span class="dvd">${s.form.map(g=>{const r=rOf(g);return `<i class="${r==='w'?'y':r==='d'?'d':'n'}" title="${esc(g.gf+':'+g.ga)}" aria-label="${RESF[r]} ${esc(g.gf+':'+g.ga)}"></i>`}).join('')||'—'}</span></div></article>`;
 $('haBox').innerHTML=card(H,'Дома','h')+card(Aw,'В гостях','a');
 draw()}else if(sec)sec.hidden=true}

/* ── 2в. сравнение с соперником следующего матча ── */
if(nextG){
 const o=nextG.o,O=TM[o],SO=stats(o,oppCtx),ctxF=g=>oppCtx(g);
 const RO=CUP?(D.tables[CUP]||[]).find(x=>x.id===o)||O:O,OX=CUP?(O.cx||{})[CUP]:null;
 const ppgF=(t,home)=>{const a=gamesOf(t,g=>(t===ID?inCtx(g):oppCtx(g))&&!!g.h===!!home);return a.length?a.reduce((x,g)=>x+pts(g),0)/a.length:0};
 const cur=h2h(ID,o).filter(r=>r.s==='2026/27'),old=h2h(ID,o).filter(r=>r.s!=='2026/27');
 const mine=r=>({d:r.d,h:r.h===ID?1:0,gf:r.h===ID?r.hs:r.as,ga:r.h===ID?r.as:r.hs,s:r.s});
 const C=cur.map(mine),Ol=old.map(mine);
 const rec=a=>[a.filter(g=>g.gf>g.ga).length,a.filter(g=>g.gf===g.ga).length,a.filter(g=>g.gf<g.ga).length];
 const [cw,cd,cl]=rec(C),[tw,td,tl_]=rec(C.concat(Ol)),tot=C.length+Ol.length;
 const c1=PAL&&pv('--ink')||(CUP?(CUP==='ucl'?'#19c8ff':'#ff9a3c'):palette(clubColors(T)).accL),c2=PAL&&pv('--ink-3')||(CUP?(CUP==='ucl'?'#ff3fa4':'#e6ebf5'):palette(clubColors(O)).accL);
 const near=!CUP&&Math.hypot(...JVF.rgb(c1).map((v,i)=>v-JVF.rgb(c2)[i]))<110;
 const nT=esc(T.n),nO=esc(O.n);
 const sumCur=C.length?`в этом сезоне ${cw}–${cd}–${cl}`:'в этом сезоне ещё не встречались';
 const sumAll=tot?` · с прошлым сезоном ${tw}–${td}–${tl_}`:'';
 const rad=`<div class="cmpad"><div class="rad">${radar([{v:CUP?CX.axes:T.axes,c:c1,name:T.n},{v:CUP&&OX?OX.axes:O.axes,c:c2,name:O.n,dash:near}],AXS)}</div>
  <div class="legend cmpleg"><span>${CI(ID)}<b style="color:${esc(c1)}">${nT}</b></span><span>${CI(o)}<b style="color:${esc(c2)}">${nO}</b></span><span><i class="d"></i>${CUP?'середина турнира':'середина лиги'}</span></div></div>`;
 const sgn=v=>v>0?'+'+v:v<0?'−'+Math.abs(v):'0';
 const pl=t=>{const g=gamesOf(t,t===ID?inCtx:oppCtx).slice(0,5);return g.reduce((a,x)=>a+pts(x),0)};
 const stk=t=>{const a=gamesOf(t,t===ID?inCtx:oppCtx).slice().reverse();let n=0;for(let i=a.length-1;i>=0&&a[i].gf>=a[i].ga;i--)n++;return n};
 const rows=[];const add=(lab,a,b,x,y,dir)=>{if(a!=null&&b!=null&&a!=='—'&&b!=='—')rows.push([lab,a,b,x,y,dir])};
 if(CUP&&OX){add('Сила: рейтинг Club Elo',CX.e,OX.e,CX.e,OX.e,1);add('Место в рейтинге Европы',`${CX.r}-е`,`${OX.r}-е`,CX.r,OX.r,-1)}
 add('Место в таблице',`${RC.place}-е`,`${RO.place}-е`,RC.place,RO.place,-1);
 add('Очки',RC.pts,RO.pts,RC.pts,RO.pts,1);
 add('Игры',RC.gp,RO.gp,0,0,0);
 add('Победы–ничьи–поражения',`${RC.w}–${RC.d}–${RC.l}`,`${RO.w}–${RO.d}–${RO.l}`,RC.w/Math.max(1,RC.gp),RO.w/Math.max(1,RO.gp),1);
 add('Очки за игру',f2(S.ppg),f2(SO.ppg),S.ppg,SO.ppg,1);
 add('Мячи за игру',f2(S.gf),f2(SO.gf),S.gf,SO.gf,1);
 add('Пропущено за игру',f2(S.ga),f2(SO.ga),S.ga,SO.ga,-1);
 add('Разница мячей',sgn(RC.gf-RC.ga),sgn(RO.gf-RO.ga),RC.gf-RC.ga,RO.gf-RO.ga,1);
 add('Форма: очки за 5 игр',pl(ID),pl(o),pl(ID),pl(o),1);
 add('Очки дома · очки в гостях',`${f2(ppgF(ID,1))} · ${f2(ppgF(ID,0))}`,`${f2(ppgF(o,1))} · ${f2(ppgF(o,0))}`,0,0,0);
 if(S.sh!=null&&SO.sh!=null){add('Удары за игру',f1(S.sh),f1(SO.sh),S.sh,SO.sh,1);add('Удары в створ за игру',f1(S.sot),f1(SO.sot),S.sot,SO.sot,1);add('Угловые за игру',f1(S.cor),f1(SO.cor),S.cor,SO.cor,1);add('Владение, %',Math.round(S.pos),Math.round(SO.pos),S.pos,SO.pos,1)}
 add('Матчей с тоталом больше 2,5',Math.round(S.ov*100)+' %',Math.round(SO.ov*100)+' %',0,0,0);
 add('Матчей, где забили обе',Math.round(S.bt*100)+' %',Math.round(SO.bt*100)+' %',0,0,0);
 add('Сухих матчей',Math.round(S.cs*100)+' %',Math.round(SO.cs*100)+' %',S.cs,SO.cs,1);
 add('Матчей подряд без поражения',stk(ID),stk(o),stk(ID),stk(o),1);
 const cell=(v,x,y,dir,c,side)=>{const m=side?y:x,h=side?x:y,w=dir&&Math.abs(m-h)>1e-9&&(dir>0?m>h:m<h);
  return `<td class="${w?'lead':''}"${w?` style="--c:${esc(c)}"`:''}><span class="num">${esc(v)}</span></td>`};
 const tbl=`<table class="cmpt"><caption class="sr">Статистика сезона: ${nT} и ${nO}</caption>
  <thead><tr><th scope="col" class="cl">Показатель</th><th scope="col" style="--c:${esc(c1)}">${CI(ID)}<span>${nT}</span></th><th scope="col" style="--c:${esc(c2)}">${CI(o)}<span>${nO}</span></th></tr></thead>
  <tbody>${rows.map(r=>`<tr><th scope="row" class="cl">${esc(r[0])}</th>${cell(r[1],r[3],r[4],r[5],c1,0)}${cell(r[2],r[3],r[4],r[5],c2,1)}</tr>`).join('')}</tbody></table>`;
 const item=(g,nx)=>{const t=day(g.d),h=g.h,r=nx?null:rOf(g);return `<li class="g h2g ${nx?'nx ':''}${h?'home':'away'}"><span class="gd"><b>${t.d} ${t.mon}</b><small>${t.wd}${nx&&t.tm?' · '+t.tm+' МСК':g.s?' · '+g.s:''}</small></span>
  <span class="ha ${h?'h':'a'}" title="${h?'дома':'в гостях'}">${h?'Д':'В'}</span><span class="hv">${h?'Дома':'В гостях'}</span>
  ${nx?`<span class="rs nxt">следующий</span>`:`<span class="sc num">${g.gf}:${g.ga}</span><span class="rs ${r}" title="${RESF[r]}">${RES[r]}</span>`}</li>`};
 const mt=C.length?`<ol class="gs h2l">${C.map(g=>item(g,0)).join('')}${item({d:nextG.d,h:nextG.h},1)}</ol>`
  :`<p class="cmpno">В этом сезоне ещё не встречались.</p><ol class="gs h2l">${item({d:nextG.d,h:nextG.h},1)}</ol>`;
 const oldHtml=Ol.length?`<h4 class="note" style="margin:14px 0 6px">Прошлый сезон, 2025/26</h4><ol class="gs h2l">${Ol.slice().reverse().map(g=>item(g,0)).join('')}</ol>`:'';
 const dt=$('nmh2h');
 dt.innerHTML=`<summary><span class="h2cr">${CI(ID)}${CI(o)}</span><span class="h2st"><b>Сравнение: ${nT} — ${nO}</b><small>${sumCur}${sumAll}</small></span><span class="h2ar" aria-hidden="true">▾</span></summary>
  <div class="h2in cmp">
   <section class="cmps"><h3>Сила команд${CUP?' в '+esc(EL.short):''}</h3>${rad}</section>
   <section class="cmps"><h3>Статистика сезона</h3><div class="cmpw" tabindex="0" role="region" aria-label="Статистика клубов, листается вбок">${tbl}</div></section>
   <section class="cmps"><h3>Матчи между клубами</h3>${mt}${oldHtml}${tot?`<p class="note cmpall">С прошлым сезоном: ${tw}–${td}–${tl_} в ${tot} ${plural(tot,'матче','матчах','матчах')}.</p>`:''}</section>
  </div>`;
 dt.hidden=false}

/* ── 3б. игроки: бомбардиры и карточки по данным матчей лиги ── */
{const pbox=$('playersBox'),sc=(CUP?(T.scx||{})[CUP]:T.sc)||[],cd=(CUP?(T.cdx||{})[CUP]:T.cd)||[];
 if(!sc.length&&!cd.length){$('players').hidden=true;$('players').removeAttribute('data-zone')}
 else{
 const st={tab:sc.length?'sc':'cd'};
 const top=sc[0];
 const lead=top?`<ul class="plead" data-rv><li><span class="sl">Лучший бомбардир</span><b class="pln">${esc(top.n)}</b><span class="plv"><b class="num">${top.g}</b><small>${esc(plural(top.g,'гол','гола','голов'))}</small></span><span class="ss">${top.p?`в том числе с пенальти — ${top.p}`:'без пенальти'}</span></li>
  <li><span class="sl">Забили в сезоне</span><b class="pln">${sc.length}${sc.length>=12?'+':''} ${esc(plural(sc.length,'игрок','игрока','игроков'))}</b><span class="plv"><b class="num">${RC.gf}</b><small>${esc(plural(RC.gf,'мяч','мяча','мячей'))}</small></span><span class="ss">всего забито клубом</span></li>${cd[0]?`<li><span class="sl">Больше всего карточек</span><b class="pln">${esc(cd[0].n)}</b><span class="plv"><b class="num">${cd[0].y+cd[0].r}</b><small>${esc(plural(cd[0].y+cd[0].r,'карточка','карточки','карточек'))}</small></span><span class="ss">жёлтых — ${cd[0].y}, красных — ${cd[0].r}</span></li>`:''}</ul>`:'';
 const render=()=>{
  $('plTable').innerHTML=st.tab==='sc'?`<table class="table pltab"><thead><tr><th class="c1">#</th><th class="c2 tx">Игрок</th><th class="ra">Голы</th><th class="ra">С пенальти</th></tr></thead>
   <tbody>${sc.map((p,i)=>`<tr><td class="c1 num">${i+1}</td><td class="c2 pn">${esc(p.n)}</td><td class="ra num on">${p.g}</td><td class="ra num">${p.p||'—'}</td></tr>`).join('')}</tbody></table>`
  :`<table class="table pltab"><thead><tr><th class="c1">#</th><th class="c2 tx">Игрок</th><th class="ra">Жёлтые</th><th class="ra">Красные</th></tr></thead>
   <tbody>${cd.map((p,i)=>`<tr><td class="c1 num">${i+1}</td><td class="c2 pn">${esc(p.n)}</td><td class="ra num on">${p.y||'—'}</td><td class="ra num">${p.r||'—'}</td></tr>`).join('')}</tbody></table>`;
  document.querySelectorAll('#plTabs button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.t===st.tab))};
 pbox.innerHTML=`<div class="sec-head" data-rv><h2>Игроки</h2></div>
  ${lead}
  <div class="gfilter" role="group" aria-label="Что показать" data-rv><div class="seg" id="plTabs">${sc.length?`<button type="button" aria-pressed="true" data-t="sc">Бомбардиры<small>${sc.length}</small></button>`:''}${cd.length?`<button type="button" aria-pressed="false" data-t="cd">Карточки<small>${cd.length}</small></button>`:''}</div></div>
  <div class="plwrap" id="plTable" data-rv tabindex="0" role="region" aria-label="Таблица игроков, листается вбок"></div>`;
 $('plTabs').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;st.tab=b.dataset.t;render()});
 render()}}

$('foot').textContent=`Данные ESPN ${asOf} · © JARVIS, @jarvibet`;
})();
