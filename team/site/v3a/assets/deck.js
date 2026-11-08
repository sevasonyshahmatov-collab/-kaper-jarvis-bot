/* JARVIS v3a — «Колода матчей» (matches.html).
   Данные: data/today.js, lines.js, model.js (через assets/lines.js → window.JVL), клубы: assets/data/teams-lite.js (хоккей) и football/data/football-lite.js (футбол);
   подробности клуба (игроки, личные встречи) подгружаются при открытии панели: assets/data/club/<slug>.js, football/data/club/<id>.js.
   Нет данных — блок не показываем. Ничего не выдумываем. */
(()=>{
'use strict';
const J=window.JVL;if(!J)return;
const esc=J.esc,p0=J.p0,f1=J.f1,f2=J.f2;
const TH=window.JV_TEAMS&&window.JV_TEAMS.teams||{},FB=window.JV_FOOT||{teams:{},leagues:{},tables:{},h2h:{}};
const $=id=>document.getElementById(id);
const root=document.querySelector('.dk');
const mqRM=matchMedia('(prefers-reduced-motion: reduce)'),mqM=matchMedia('(max-width: 980px)');
const syncRM=()=>root.classList.toggle('rm',mqRM.matches);syncRM();
if(mqRM.addEventListener)mqRM.addEventListener('change',syncRM);

/* ── данные матчей ── */
const TD=J.TD||{matches:[],days:[]};
/* начавшиеся матчи не показываем: после стартового свистка линия уже лайв (1,05 / 15 / 46) */
const NOWMSK=(()=>{const d=new Date(Date.now()+(new Date().getTimezoneOffset()+180)*6e4),p=n=>String(n).padStart(2,'0');return d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+' '+p(d.getHours())+':'+p(d.getMinutes())})();
const ALL=(TD.matches||[]).filter(m=>m&&m.key&&m.h&&m.a&&!(m.t&&String(m.t).slice(0,16)<=NOWMSK)).slice().sort((a,b)=>String(a.t).localeCompare(String(b.t))||a.key.localeCompare(b.key));
const isH=m=>m.lg==='khl'||m.lg==='nhl';
const LGN={khl:'КХЛ',nhl:'НХЛ'};
const lgName=m=>isH(m)?LGN[m.lg]:((FB.leagues[m.lg]||{}).short||(FB.leagues[m.lg]||{}).name||m.lg.toUpperCase());
const lgFull=m=>isH(m)?LGN[m.lg]:((FB.leagues[m.lg]||{}).name||lgName(m));
const team=(m,s)=>isH(m)?TH[s]:FB.teams[s];
const emUrl=(m,s)=>isH(m)?`assets/em/${encodeURIComponent(s)}.webp`:`assets/fc/${encodeURIComponent(s)}.webp`;
const lgIcon=m=>`assets/lg/${encodeURIComponent(m.lg)}.webp`;
const clubHref=(m,s)=>isH(m)?`team/index.html?id=${encodeURIComponent(s)}`:`football/team.html?id=${encodeURIComponent(s)}`;
const lgHref=m=>isH(m)?`hockey/league.html?lg=${encodeURIComponent(m.lg)}`:(m.lg==='ucl'?'football/ucl.html':`football/league.html?lg=${encodeURIComponent(m.lg)}`);
const emImg=(m,s,n)=>`<img src="${emUrl(m,s)}" alt="" loading="lazy" decoding="async" onerror="this.replaceWith(Object.assign(document.createElement('span'),{textContent:this.dataset.i}))" data-i="${esc((n||s).slice(0,2).toUpperCase())}">`;
const D2=n=>String(n).padStart(2,'0');
const MON=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
const dayLabel=t=>{const d=String(t).slice(0,10),days=TD.days||[];if(d===days[0])return 'Сегодня';if(d===days[1])return 'Завтра';return +d.slice(8,10)+' '+MON[+d.slice(5,7)-1]};
const shortDate=d=>String(d).slice(8,10)+'.'+String(d).slice(5,7)+'.'+String(d).slice(2,4);
const info=m=>({ln:J.line(m.key),md:J.model(m.key)});

/* ── фильтр, состояние ── */
let list=ALL.slice(),cur=0,filter='all',openDrawer=false;
const q=new URLSearchParams(location.search);
{const sp=q.get('s')||'',fp=q.get('f')||'';if(/^(hockey|football)$/.test(fp))filter=fp;else if(sp==='h')filter='hockey';else if(sp==='f')filter='football'}
const applyFilter=()=>{list=ALL.filter(m=>filter==='all'||(filter==='hockey')===isH(m))};

/* ── карточка ── */
const pick=(m,md)=>{if(!md)return null;const a=[[md.p1,'Победа: '+m.hn],[md.x,isH(m)?'Ничья в основное время':'Ничья'],[md.p2,'Победа: '+m.an]].filter(x=>x[0]!=null);
  if(!a.length)return null;return a.sort((x,y)=>y[0]-x[0])[0]};
/* рисунок поля для варианта «Стекло»: лёд (синие и красная линии, круги вбрасывания) или футбольная разметка; едва заметный */
const RINK='<svg class="dk-field" viewBox="0 0 200 100" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><rect x="3" y="3" width="194" height="94" rx="28" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="100" y1="3" x2="100" y2="97" stroke="#ff5d6c" stroke-width="1.6"/><line x1="70" y1="3" x2="70" y2="97" stroke="#4cc2ff" stroke-width="1.4"/><line x1="130" y1="3" x2="130" y2="97" stroke="#4cc2ff" stroke-width="1.4"/><circle cx="100" cy="50" r="14" fill="none" stroke="#4cc2ff" stroke-width="1.2"/><circle cx="42" cy="28" r="9" fill="none" stroke="#ff5d6c" stroke-width="1"/><circle cx="42" cy="72" r="9" fill="none" stroke="#ff5d6c" stroke-width="1"/><circle cx="158" cy="28" r="9" fill="none" stroke="#ff5d6c" stroke-width="1"/><circle cx="158" cy="72" r="9" fill="none" stroke="#ff5d6c" stroke-width="1"/><line x1="16" y1="3" x2="16" y2="97" stroke="#ff5d6c" stroke-width="1"/><line x1="184" y1="3" x2="184" y2="97" stroke="#ff5d6c" stroke-width="1"/></svg>';
const PITCH='<svg class="dk-field" viewBox="0 0 200 100" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.2"><rect x="4" y="4" width="192" height="92"/><line x1="100" y1="4" x2="100" y2="96"/><circle cx="100" cy="50" r="15"/><rect x="4" y="24" width="30" height="52"/><rect x="166" y="24" width="30" height="52"/><rect x="4" y="38" width="11" height="24"/><rect x="185" y="38" width="11" height="24"/><path d="M34 40a15 15 0 0 1 0 20M166 40a15 15 0 0 0 0 20"/></g></svg>';
/* цвета клубов для карточки: те же, что у фона матча (data/deckbg/index.json), пока индекс не загрузился — расчёт pickPair */
function cardCols(m){const e=BGIDX&&BGIDX[m.key];if(e&&e.c)return e.c;const [a,b]=pickPair(m);return [hsl2css(a[0],a[1],a[2]),hsl2css(b[0],b[1],b[2])]}
const cardVars=(el,m)=>{const [c1,c2]=cardCols(m);el.style.setProperty('--h1',c1);el.style.setProperty('--h2',c2)};
function cardHtml(m,i,n){const {ln,md}=info(m),pk=pick(m,md),fl=J.fair(ln),mx=fl?Math.max(...fl):0;
  /* выделяем исход, который выбрала модель (нет модели — фаворит линии) */
  const mo=md?[md.p1,md.x,md.p2]:null,mm=mo?Math.max(...mo.filter(v=>v!=null)):0;
  let ql='';
  if(ln){const hasX=!!ln.x,cells=[['П1',ln.p1,0]].concat(hasX?[['Х',ln.x,1]]:[],[['П2',ln.p2,2]]);
   ql=`<div class="dk-ql${hasX?'':' two'}">${cells.map(c=>`<span class="${(mo?mo[c[2]]===mm:fl&&fl[c[2]]===mx)?'fav':''}"><small>${c[0]}</small><b>${f2(c[1])}</b></span>`).join('')}</div>
   <p class="dk-src">Линия: ${esc(J.srcLabel(ln))}</p>`}
  else ql=`<p class="dk-src">Линии на этот матч пока нет</p>`;
  const t=String(m.t||'');
  return `<div class="dk-cf">
  <div class="dk-ctop">
   ${isH(m)?RINK:PITCH}
   <span class="dk-wm l">${emImg(m,m.h,m.hn)}</span><span class="dk-wm r">${emImg(m,m.a,m.an)}</span>
   <span class="dk-no" aria-hidden="true">№ ${D2(i+1)}</span>
   <div class="dk-ct"><span class="dk-lg"><img src="${lgIcon(m)}" alt="" onerror="this.remove()">${esc(lgName(m))}</span><span class="dk-dt"><b>${esc(dayLabel(t))}</b> · ${esc(t.slice(11,16))} МСК</span></div>
   <div class="dk-cm">
    <div class="dk-tm"><span class="dk-em">${emImg(m,m.h,m.hn)}</span><b>${esc(m.hn)}</b><i>дома</i></div>
    <span class="dk-vs">—</span>
    <div class="dk-tm"><span class="dk-em">${emImg(m,m.a,m.an)}</span><b>${esc(m.an)}</b><i>в гостях</i></div>
   </div>
  </div>
  <div class="dk-cbot">${ql}
  ${pk?`<p class="dk-pick">Самый вероятный исход по модели<b>${esc(pk[1])} · <em>${p0(pk[0])} %</em></b></p>`:''}</div>
  </div>`}

const deck=$('dk-deck'),stage=$('dk-stage');
let W=340;
function measure(){const sw=stage.clientWidth,mob=mqM.matches;
  const byH=Math.floor((innerHeight-(mob?330:350))/1.61);
  W=mob?Math.max(220,Math.min(320,document.documentElement.clientWidth-96)):Math.max(270,Math.min(410,Math.round(sw*.66),byH));
  root.style.setProperty('--W',W+'px')}
/* колода: стопка лицом к зрителю. Задние (до 3) ниже на 12 px и уже (0,95 / 0,90 / 0,85), темнее. Смахнутая карточка (i<0) улетает влево-вверх с поворотом */
const FLY=()=>`translate3d(${-W*.78}px,${-W*.18}px,0) rotate(-13deg)`;
function pose(i){
  if(root.classList.contains('rm'))return {t:'none',o:i===0?1:0,z:i===0?5:0,dim:0,pe:i===0};
  if(i<0)return {t:FLY(),o:0,z:i===-1?30:0,dim:0,pe:false,fly:true};
  const k=Math.min(i,4),H=W*1.4,sc=1-.05*k;
  return {t:`translate3d(0,${(12*k+H*.05*k).toFixed(1)}px,0) scale(${sc})`,o:i>3?0:1,z:20-i,dim:Math.min(.5,.13*k),pe:i<=3}}
function layout(){
  deck.querySelectorAll('.dk-card').forEach((el,k)=>{const i=k-cur,p=pose(i);
    el.style.transform=p.t;el.style.opacity=p.o;el.style.zIndex=p.z;el.style.setProperty('--dim',p.dim);el.style.pointerEvents=p.pe?'auto':'none';
    el.classList.toggle('on',i===0);el.classList.toggle('gone',i<0);el.style.transition='';el.setAttribute('aria-hidden',i===0?'false':'true');
    if(i!==0)el.setAttribute('aria-hidden',p.pe?'false':'true');
  });
  const n=list.length;
  $('dk-cur').textContent=D2(n?cur+1:0);$('dk-tot').textContent=D2(n);
  $('dk-bar').parentNode.style.setProperty('--p',n>1?'1':'1');
  $('dk-bar').style.setProperty('--p',n?((cur+1)/n):0);
  $('dk-prev').disabled=cur<=0;$('dk-next').disabled=cur>=n-1;
}
function build(){
  measure();
  deck.innerHTML=list.map((m,i)=>`<li class="dk-card" data-sp="${isH(m)?'hockey':'football'}" data-i="${i}" aria-label="Матч ${i+1} из ${list.length}: ${esc(m.hn)} — ${esc(m.an)}">${cardHtml(m,i,list.length)}</li>`).join('');
  deck.querySelectorAll('.dk-card').forEach((el,k)=>cardVars(el,list[k]));
  layout();
}
function counts(){const h=ALL.filter(isH).length,f=ALL.length-h;
  document.querySelectorAll('#dk-filter button').forEach(b=>{const k=b.dataset.f;b.querySelector('small').textContent=k==='all'?ALL.length:k==='hockey'?h:f;
    b.setAttribute('aria-pressed',String(k===filter))})}

/* ── колонка «О встрече» ── */
/* знак лиги водяным знаком в шапке блока (владелец 04.11): НХЛ, КХЛ, ЛЧ, АПЛ… */
const LGLOGO={}; /* официальные логотипы лиг — assets/lg/<лига>.webp (владелец 04.11) */
const formOf=(m,s)=>{const T=team(m,s);if(!T)return null;
  const g=(T.games||[]).filter(x=>typeof x.gf==='number'&&typeof x.ga==='number').slice(-5);
  if(!g.length)return null;return g.map(x=>({d:x.d,o:x.o,h:x.h,gf:x.gf,ga:x.ga,x:x.x,r:x.gf>x.ga?'w':x.gf<x.ga?'l':'d'}))};
const nameOf=(m,s)=>{const T=team(m,s);return T&&(T.n||T.name)||s};
const formHtml=(m,s)=>{const f=formOf(m,s);if(!f)return '';
  const dots=f.map(x=>{const t=`${shortDate(x.d)} ${x.h?'дома':'в гостях'} с ${nameOf(m,x.o)}: ${x.gf}:${x.ga}${x.x?' '+x.x:''}`;
    return `<i class="${x.r}" title="${esc(t)}" aria-label="${esc(t)}"></i>`});
  while(dots.length<5)dots.unshift('<i class="e"></i>');
  return `<div class="dk-form" role="img" aria-label="Форма, последние 5 матчей, слева раньше">${dots.join('')}</div>`};
/* место и очки: в кубках — по таблице турнира, иначе по лиге клуба */
function standing(m,s){
  if(isH(m)){const T=TH[s];if(!T||T.place==null)return null;return {pl:T.place,pts:T.pts,gp:T.gp,sub:T.conf||'',lg:LGN[m.lg]}}
  const rows=FB.tables&&FB.tables[m.lg],r=rows&&rows.find(x=>x.id===s);
  if(r)return {pl:r.place,pts:r.pts,gp:r.gp,sub:'',lg:lgFull(m)};
  const T=FB.teams[s];if(T&&T.place!=null&&T.lg)return {pl:T.place,pts:T.pts,gp:T.gp,sub:'',lg:(FB.leagues[T.lg]||{}).name||''};
  return null}
function teamRow(m,s,n){const st=standing(m,s),T=team(m,s);
  const sub=st?`${st.pl}-е место · ${st.pts} ${pl(st.pts,['очко','очка','очков'])} · ${st.gp} ${pl(st.gp,['матч','матча','матчей'])}`:(T?'':'нет данных по клубу');
  return `<div class="dk-trow"><img class="em" src="${emUrl(m,s)}" alt="" onerror="this.outerHTML='<span class=ph></span>'"><div><b>${esc(n)}</b><small>${esc(sub)}${st&&st.sub?' · '+esc(st.sub):''}</small></div>${formHtml(m,s)}</div>`}
function pl(n,f){n=Math.abs(n)%100;const a=n%10;return n>10&&n<20?f[2]:a>1&&a<5?f[1]:a===1?f[0]:f[2]}

/* страница матча по понятному адресу (генерирует seo/build_match.py → data/matchlinks.js) */
function matchLink(m){const u=(window.JV_MATCHLINKS||{})[m.key||`${m.lg}|${String(m.t||'').slice(0,10)}|${m.h}|${m.a}`];return u?`<a class="dk-mpage" href="${esc(u)}">Страница матча: форма, личные встречи, расчёт ›</a>`:''}
function infoHtml(m){const {ln,md}=info(m);let h='';
  const t=String(m.t||'');
  h+=`<div class="dk-ihead"><img class="dk-lgwm" src="assets/lg/${esc(LGLOGO[m.lg]||m.lg+'.webp')}" alt="" aria-hidden="true" onerror="this.remove()"><p class="dk-ik">О встрече</p><h2 class="dk-ih">${esc(m.hn)} — ${esc(m.an)}<small>${esc(lgFull(m))} · ${esc(dayLabel(t))}, ${esc(t.slice(11,16))} МСК${m.arena&&m.arena.name?' · '+esc(m.arena.name)+(m.arena.city?', '+esc(m.arena.city):''):''}</small></h2>${matchLink(m)}</div>`;
  h+=`<div class="dk-blk"><h3>Таблица и форма</h3>${teamRow(m,m.h,m.hn)}${teamRow(m,m.a,m.an)}</div>`;
  if(md){
    const rows=[[md.p1,'П1 · '+m.hn],[md.x,isH(m)?'Х · ничья в осн. время':'Х · ничья'],[md.p2,'П2 · '+m.an]].filter(r=>r[0]!=null),mx=Math.max(...rows.map(r=>r[0]));
    h+=`<div class="dk-blk"><h3>Модель JARVIS · вероятности</h3>${rows.map(r=>`<div class="dk-pb${r[0]===mx?' top':''}"><span title="${esc(r[1])}">${esc(r[1])}</span><em><i style="--w:${p0(r[0])}%"></i></em><b>${p0(r[0])} %</b></div>`).join('')}`;
    const kv=[];
    if(md.over!=null&&md.tot!=null)kv.push(`Тотал ${f1(md.tot)}: больше <b>${p0(md.over)} %</b>, меньше <b>${100-p0(md.over)} %</b>`);
    if(!isH(m)&&md.btts!=null)kv.push(`Обе забьют: <b>${p0(md.btts)} %</b>`);
    if(isH(m)&&md.w1!=null&&md.w2!=null)kv.push(`Победа с ОТ/буллитами: ${esc(m.hn)} <b>${p0(md.w1)} %</b>, ${esc(m.an)} <b>${p0(md.w2)} %</b>`);
    if(Array.isArray(md.lam)&&md.lam.length===2)kv.push(`Ожидаемые голы: ${esc(m.hn)} <b>${f1(md.lam[0])}</b>, ${esc(m.an)} <b>${f1(md.lam[1])}</b>`);
    if(kv.length)h+=`<div class="dk-kv" style="flex-direction:column;gap:6px">${kv.map(x=>`<span>${x}</span>`).join('')}</div>`;
    h+=`<p class="dk-note">${esc(J.verName(md.ver||''))||'Модель JARVIS'}${md.t?', расчёт от '+esc(J.hhmm(md.t))+' МСК':''}. Это оценка вероятностей, а не обещание исхода.</p></div>`}
  if(ln){
    const hasX=!!ln.x;
    h+=`<div class="dk-blk"><h3>Линия</h3><div class="dk-lnq"><span><small>П1</small><b>${f2(ln.p1)}</b></span>${hasX?`<span><small>Х</small><b>${f2(ln.x)}</b></span>`:''}<span><small>П2</small><b>${f2(ln.p2)}</b></span>`+
     (ln.tot!=null&&ln.over?`<span><small>ТБ ${f1(ln.tot)}</small><b>${f2(ln.over)}</b></span><span><small>ТМ ${f1(ln.tot)}</small><b>${f2(ln.under)}</b></span>`:'')+`</div>
     <p class="dk-note">Линия: ${esc(J.srcLabel(ln))}</p></div>`}
  else h+=`<div class="dk-blk"><h3>Линия</h3><p class="dk-note" style="margin:0">Линии на этот матч пока нет.</p></div>`;
  h+=`<button type="button" class="dk-more" id="dk-more">Подробная статистика<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h15m-6-6 6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>`;
  return h}
const infoEl=$('dk-info');let swTimer=0;
function renderInfo(animate){
  const m=list[cur];
  const put=()=>{infoEl.innerHTML=m?infoHtml(m):'<p class="dk-empty">Матчей в этом окне нет.</p>';infoEl.scrollTop=0;infoEl.classList.remove('sw');const b=$('dk-more');if(b)b.onclick=()=>openPanel()};
  /* футбольные клубы: игры сезона лежат в файле клуба — подгружаем при выборе матча и дорисовываем форму */
  if(m&&!isH(m)&&!(team(m,m.h)||{}).games){const k=m.key;Promise.all([m.h,m.a].map(x=>loadScript(`football/data/club/${encodeURIComponent(x)}.js`))).then(()=>{if(list[cur]&&list[cur].key===k&&!infoEl.classList.contains('sw'))put()})}
  clearTimeout(swTimer);
  if(animate&&!root.classList.contains('rm')){infoEl.classList.add('sw');swTimer=setTimeout(put,190)}else put()}


/* ── фон под матч: цвета клубов → «шёлк» (логика баннеров: слева хозяева, справа гости, между ними перелив) ── */
const hex2rgb=h=>{h=String(h).replace('#','');if(h.length===3)h=h.replace(/./g,'$&$&');const n=parseInt(h,16);return isNaN(n)||h.length!==6?null:[n>>16&255,n>>8&255,n&255]};
function rgb2hsl(r,g,b){r/=255;g/=255;b/=255;const mx=Math.max(r,g,b),mn=Math.min(r,g,b),l=(mx+mn)/2;let h=0,s=0;
  if(mx!==mn){const d=mx-mn;s=l>.5?d/(2-mx-mn):d/(mx+mn);h=mx===r?(g-b)/d+(g<b?6:0):mx===g?(b-r)/d+2:(r-g)/d+4;h*=60}return [h,s,l]}
function hsl2css(h,s,l){h=((h%360)+360)%360;return `hsl(${h.toFixed(0)} ${(s*100).toFixed(0)}% ${(l*100).toFixed(0)}%)`}
const hueD=(a,b)=>{const d=Math.abs(a-b)%360;return d>180?360-d:d};
function candsOf(m,sl){let a=[];
  if(isH(m)){const C=(window.JV_CLUBS||{})[sl];if(C)a=a.concat(C);const T=TH[sl];if(T&&T.colors)a=a.concat(T.colors)}
  else{const T=FB.teams[sl];if(T&&T.c)a=a.concat(T.c)}
  return a.map(hex2rgb).filter(Boolean).map(c=>rgb2hsl(c[0],c[1],c[2]))}
/* яркий, но не светлый: насыщенность не ниже .55, светлота .30–.40, чтобы белый текст читался */
const norm=([h,s,l])=>[h,Math.min(.85,Math.max(.55,s)),Math.min(.40,Math.max(.30,l))];
const score=([h,s,l])=>s>=.25&&l>.1&&l<.93?s*(1-Math.abs(l-.42)):-1;
function pickPair(m){
  const A=candsOf(m,m.h).sort((x,y)=>score(y)-score(x)),B=candsOf(m,m.a).sort((x,y)=>score(y)-score(x));
  let a=A[0]&&score(A[0])>0?A[0]:null,b=B[0]&&score(B[0])>0?B[0]:null;
  /* нет цвета (белый, чёрный, серый клуб) — нейтральный стальной оттенок */
  if(!a)a=[218,.3,.34];if(!b)b=[222,.3,.26];
  /* похожие цвета (синий против синего) — берём другой цвет гостей, иначе сдвигаем оттенок и яркость */
  if(hueD(a[0],b[0])<32&&Math.abs(a[2]-b[2])<.2){
    const alt=B.find(c=>score(c)>0&&hueD(a[0],c[0])>=40);
    if(alt)b=alt;else b=[b[0]+34,b[1],b[2]+.1]}
  a=norm(a);b=norm(b);
  if(Math.abs(a[2]-b[2])<.05&&hueD(a[0],b[0])<50){a[2]=Math.max(.28,a[2]-.04);b[2]=Math.min(.42,b[2]+.05)}
  return [a,b]}
const bgL=[...document.querySelectorAll('.dk-bg')];let bgCur=-1,bgKey='';
/* картинки фона: data/deckbg/<ключ>.webp (тот же код, что у баннеров Telegram, см. daily/deck_bg.py); нет файла — CSS-фон по цветам клубов */
let BGIDX=null,bgSeq=0;
const bgUrl=m=>{const e=BGIDX&&BGIDX[m.key];return e?`data/deckbg/${e.f}${mqM.matches?'-m':''}.webp`:null};
const bgPre=i=>{const m=list[i];const u=m&&bgUrl(m);if(u){const im=new Image();im.src=u}};
function applyBg(dir){const m=list[cur];if(!m||m.key===bgKey)return;bgKey=m.key;
  const [a,b]=pickPair(m),mix=[(a[0]+b[0])/2%360,Math.min(.6,(a[1]+b[1])/2),Math.min(.3,(a[2]+b[2])/2-.02)];
  const url=bgUrl(m),my=++bgSeq;
  const show=img=>{if(my!==bgSeq)return;
    const nxt=bgL[(bgCur+1)%2],old=bgCur>=0?bgL[bgCur]:null,rm=root.classList.contains('rm');
    nxt.style.setProperty('--c1',hsl2css(a[0],a[1],a[2]));nxt.style.setProperty('--c2',hsl2css(b[0],b[1],b[2]));nxt.style.setProperty('--cm',hsl2css(mix[0],mix[1],mix[2]));
    nxt.classList.toggle('img',!!img);nxt.style.backgroundImage=img?`url("${img}")`:'';root.classList.toggle('bgimg',!!img);
    const fl=nxt.querySelector('.fl');
    if(!rm&&old){fl.style.transition='none';nxt.style.setProperty('--dx',(dir||0)*9+'vw');void fl.offsetWidth;fl.style.transition='';nxt.style.zIndex=2;old.style.zIndex=1;nxt.classList.add('on');
      requestAnimationFrame(()=>nxt.style.setProperty('--dx','0vw'));
      const o=old;setTimeout(()=>{if(o!==bgL[bgCur])o.classList.remove('on')},800)}
    else{nxt.style.setProperty('--dx','0vw');nxt.classList.add('on');nxt.style.zIndex=2;if(old){old.classList.remove('on');old.style.zIndex=1}}
    bgCur=(bgCur+1)%2;
    bgPre(cur+1);bgPre(cur-1)};
  if(url){const im=new Image();im.onload=()=>show(url);im.onerror=()=>show(null);im.src=url}else show(null)}
try{fetch('data/deckbg/index.json').then(r=>r.ok?r.json():null).then(j=>{if(j&&j.bg){BGIDX=j.bg;bgKey='';applyBg(0);deck.querySelectorAll('.dk-card').forEach((el,k)=>list[k]&&cardVars(el,list[k]))}}).catch(()=>{})}catch(e){}

/* ── переключение ── */
let lockUntil=0;
function go(to,opt={}){const n=list.length;if(!n)return;to=Math.max(0,Math.min(n-1,to));if(to===cur)return false;
  const dir=to>cur?1:-1;cur=to;layout();renderInfo(true);applyBg(dir);
  try{const u=new URL(location.href);u.searchParams.set('k',list[cur].key);history.replaceState(null,'',u)}catch(e){}
  lockUntil=performance.now()+(root.classList.contains('rm')?0:520);return true}
const step=d=>go(cur+d);

/* колесо мыши / тачпад: накопление, блокировка на время анимации, инерцию тачпада не считаем за новый жест */
let acc=0,lastT=0,quiet=false,lastAbs=0;
$('dk-main').addEventListener('wheel',e=>{
  if(mqM.matches||openDrawer||e.ctrlKey)return;
  const dy=Math.abs(e.deltaY)>=Math.abs(e.deltaX)?e.deltaY:e.deltaX;if(!dy)return;
  e.preventDefault();
  const now=performance.now(),gap=now-lastT;lastT=now;
  if(gap>160){acc=0;quiet=false}
  if(now<lockUntil){lastAbs=Math.abs(dy);return}
  if(quiet&&Math.abs(dy)<=lastAbs*1.2&&Math.abs(dy)<100){lastAbs=Math.abs(dy);return} /* хвост инерции */
  quiet=false;
  acc+=dy;
  if(Math.abs(acc)>=40||Math.abs(dy)>=100){const d=acc>0?1:-1;acc=0;if(go(cur+d)){quiet=true;lastAbs=Math.abs(dy)}}
},{passive:false});

/* клавиатура */
addEventListener('keydown',e=>{
  if(e.key==='Escape'&&openDrawer){closePanel();return}
  if(openDrawer||e.altKey||e.ctrlKey||e.metaKey)return;
  const tg=e.target&&e.target.tagName;if(/^(INPUT|TEXTAREA|SELECT)$/.test(tg||''))return;
  if(e.key==='ArrowRight'||e.key==='ArrowDown'&&e.target===stage){e.preventDefault();step(1)}
  else if(e.key==='ArrowLeft'||e.key==='ArrowUp'&&e.target===stage){e.preventDefault();step(-1)}
  else if(e.key==='Home'&&e.target===stage){e.preventDefault();go(0)}
  else if(e.key==='End'&&e.target===stage){e.preventDefault();go(list.length-1)}
});
$('dk-prev').onclick=()=>step(-1);$('dk-next').onclick=()=>step(1);

/* перетаскивание: верхняя карточка идёт за пальцем с поворотом; дальше порога — улетает, иначе пружинит назад */
let sx=0,sy=0,sid=null,moved=false,drag=false,topEl=null,t0=0;
stage.addEventListener('pointerdown',e=>{if(openDrawer||(e.pointerType==='mouse'&&e.button!==0))return;sx=e.clientX;sy=e.clientY;sid=e.pointerId;moved=false;drag=false;t0=performance.now();topEl=deck.children[cur]||null});
stage.addEventListener('pointermove',e=>{if(sid!==e.pointerId||!topEl||root.classList.contains('rm'))return;
  const dx=e.clientX-sx,dy=e.clientY-sy;
  if(!drag){if(Math.abs(dx)>9&&Math.abs(dx)>Math.abs(dy)*1.1){drag=true;moved=true;topEl.style.transition='none';try{stage.setPointerCapture(e.pointerId)}catch(_){}}else return}
  const r=Math.max(-14,Math.min(14,dx*.07));
  topEl.style.transform=`translate3d(${dx}px,${dy*.25}px,0) rotate(${r}deg)`;topEl.style.opacity=String(Math.max(.35,1-Math.abs(dx)/(W*1.6)))});
const endDrag=e=>{if(sid!==e.pointerId)return;sid=null;
  const dx=e.clientX-sx;
  if(!drag){return}
  drag=false;const v=Math.abs(dx)/Math.max(1,performance.now()-t0);
  topEl.style.transition='';
  if((Math.abs(dx)>Math.min(90,W*.28)||v>.6)&&Math.abs(dx)>24){if(!step(dx<0?1:-1))layout()}else layout();
  setTimeout(()=>{moved=false},50)};
stage.addEventListener('pointerup',endDrag);
stage.addEventListener('pointercancel',e=>{if(sid===e.pointerId){sid=null;if(drag){drag=false;layout()}}});
/* клик по карточке: в ряду — выбрать, выбранная — открыть подробности */
deck.addEventListener('click',e=>{if(moved){moved=false;return}
  const c=e.target.closest('.dk-card');if(!c)return;const i=+c.dataset.i;
  if(i===cur)openPanel();else go(i)});
$('dk-filter').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;filter=b.dataset.f;
  const key=list[cur]&&list[cur].key;applyFilter();const k=list.findIndex(m=>m.key===key);cur=k>=0?k:0;counts();build();renderInfo(false);bgKey='';applyBg(0);
  try{const u=new URL(location.href);u.searchParams.delete('f');filter==='all'?u.searchParams.delete('s'):u.searchParams.set('s',filter==='hockey'?'h':'f');history.replaceState(null,'',u)}catch(e2){}});

/* ── панель «Подробная статистика» ── */
const dr=$('dk-drawer'),scrim=$('dk-scrim'),dbody=$('dk-dbody');let lastFocus=null,tok=0;
function openPanel(){const m=list[cur];if(!m||openDrawer)return;openDrawer=true;lastFocus=document.activeElement;
  $('dk-dh').textContent=`${m.hn} — ${m.an}`;
  dbody.innerHTML='<p class="dk-load">Загружаем данные клубов…</p>';
  dr.removeAttribute('inert');scrim.hidden=false;void scrim.offsetWidth;scrim.classList.add('show');dr.classList.add('open');
  document.body.style.overflow='hidden';
  setTimeout(()=>$('dk-x').focus({preventScroll:true}),60);
  const my=++tok;
  loadDetail(m).then(d=>{if(my===tok&&openDrawer)dbody.innerHTML=detailHtml(m,d)})}
function closePanel(){if(!openDrawer)return;openDrawer=false;tok++;scrim.classList.remove('show');dr.classList.remove('open');dr.setAttribute('inert','');
  document.body.style.overflow='';setTimeout(()=>{if(!openDrawer)scrim.hidden=true},500);
  try{lastFocus&&lastFocus.focus({preventScroll:true})}catch(e){}}
$('dk-x').onclick=closePanel;scrim.onclick=closePanel;
/* клик вне панели (в том числе по карточкам) закрывает её */
document.addEventListener('pointerdown',e=>{if(openDrawer&&!dr.contains(e.target)&&!e.target.closest('.dk-more'))closePanel()},true);

const loaded={};
function loadScript(src){return loaded[src]||(loaded[src]=new Promise(res=>{const s=document.createElement('script');s.src=src;s.onload=()=>res(true);s.onerror=()=>res(false);document.head.appendChild(s)}))}
function loadDetail(m){
  const sl=[m.h,m.a];
  if(isH(m))return Promise.all([...sl.map(s=>loadScript(`assets/data/club/${encodeURIComponent(s)}.js`)),
    ...sl.map(s=>fetch(`hockey/data/players/${encodeURIComponent(s)}.json`).then(r=>r.ok?r.json():{}).catch(()=>({})))]).then(r=>({ph:[r[2]||{},r[3]||{}]}));
  return Promise.all(sl.map(s=>loadScript(`football/data/club/${encodeURIComponent(s)}.js`))).then(()=>({ph:[{},{}]}))}

/* шестиугольник силы: наложение двух команд */
function axesFor(m){
  if(isH(m)){const A=window.JV_TEAMS.axes,a=TH[m.h],b=TH[m.a];if(A&&a&&b&&a.axes&&b.axes)return {names:A,a:a.axes,b:b.axes};return null}
  const a=FB.teams[m.h],b=FB.teams[m.a];if(!a||!b)return null;
  if((m.lg==='ucl'||m.lg==='uel')&&FB.axesCup){const ca=a.cx&&a.cx[m.lg],cb=b.cx&&b.cx[m.lg];if(ca&&cb&&ca.axes&&cb.axes&&!ca.est&&!cb.est)return {names:FB.axesCup,a:ca.axes,b:cb.axes,cup:true}}
  if(a.axes&&b.axes&&FB.axes)return {names:FB.axes,a:a.axes,b:b.axes};return null}
function radarHtml(m){const ax=axesFor(m);if(!ax)return '';
  let names=ax.names,A=ax.a,B=ax.b;
  if(ax.cup&&names.length===A.length+1){names=names.slice(1)}
  const n=Math.min(names.length,A.length,B.length);if(n<3)return '';
  const R=110,C=150,pt=(i,v)=>{const a=-Math.PI/2+i*2*Math.PI/n,r=R*Math.max(0,Math.min(100,v))/100;return [C+r*Math.cos(a),C+r*Math.sin(a)]};
  const poly=(arr)=>arr.slice(0,n).map((v,i)=>pt(i,v).map(x=>x.toFixed(1)).join(',')).join(' ');
  const rings=[25,50,75,100].map(k=>`<polygon class="rg" points="${Array.from({length:n},(_,i)=>pt(i,k).map(x=>x.toFixed(1)).join(',')).join(' ')}"/>`).join('');
  const spokes=Array.from({length:n},(_,i)=>{const p=pt(i,100);return `<line class="ra" x1="${C}" y1="${C}" x2="${p[0].toFixed(1)}" y2="${p[1].toFixed(1)}"/>`}).join('');
  const labs=Array.from({length:n},(_,i)=>{const a=-Math.PI/2+i*2*Math.PI/n,x=C+(R+26)*Math.cos(a),y=C+(R+18)*Math.sin(a);return `<text class="rl" x="${x.toFixed(1)}" y="${y.toFixed(1)}">${esc(names[i])}</text>`}).join('');
  const cA='var(--dk-ca,#ffc21a)',cB=isH(m)?'var(--dk-cb,#4cc2ff)':'var(--dk-cb,#3dd68c)';
  return `<section class="dk-sec"><h3>Сила команд</h3>
   <div class="dk-leg"><span style="--c:${cA}">${esc(m.hn)}</span><span style="--c:${cB}">${esc(m.an)}</span></div>
   <svg class="dk-radar" viewBox="-10 -4 320 308" role="img" aria-label="Шестиугольник силы: ${esc(m.hn)} и ${esc(m.an)}">${rings}${spokes}
    <polygon class="pa" style="--c:${cB};animation-delay:.08s" points="${poly(B)}"/><polygon class="pa" style="--c:${cA}" points="${poly(A)}"/>${labs}</svg>
   <div class="dk-axv">${Array.from({length:n},(_,i)=>`<span>${esc(names[i])}: <b style="color:${cA}">${Math.round(A[i])}</b> / <b style="color:${cB}">${Math.round(B[i])}</b></span>`).join('')}</div>
   </section>`}

/* личные встречи */
function h2hRows(m){
  if(isH(m)){const T=TH[m.h],r=T&&T.h2h&&T.h2h[m.a];if(!r||!r.length)return null;
    return r.slice(0,5).map(x=>{const hh=x[1]===1;return {d:x[0],host:hh?m.h:m.a,hs:hh?x[2]:x[3],as:hh?x[3]:x[2],x:x[4],gH:x[2],gA:x[3]}})}
  const H=FB.h2h||{},r=H[m.h+'|'+m.a]||H[m.a+'|'+m.h];if(!r||!r.length)return null;
  return r.slice().sort((a,b)=>b.d.localeCompare(a.d)).slice(0,5).map(x=>({d:x.d,host:x.h,hs:x.hs,as:x.as,x:'',s:x.s,gH:x.h===m.h?x.hs:x.as,gA:x.h===m.h?x.as:x.hs}))}
function h2hHtml(m){const rows=h2hRows(m);if(!rows)return '';
  let wh=0,wa=0,dd=0;rows.forEach(r=>{r.gH>r.gA?wh++:r.gH<r.gA?wa++:dd++});
  const sum=`Из ${rows.length} ${pl(rows.length,['последней встречи','последних встреч','последних встреч'])}: ${esc(m.hn)} — <b>${wh}</b>${dd?`, ничьих — <b>${dd}</b>`:''}, ${esc(m.an)} — <b>${wa}</b>.`;
  return `<section class="dk-sec"><h3>Личные встречи</h3><p class="dk-h2hs">${sum}</p><ul class="dk-h2h">${rows.map(r=>{
    const hn=r.host===m.h?m.hn:m.an,an=r.host===m.h?m.an:m.hn;
    return `<li><time>${shortDate(r.d)}</time><span>${esc(hn)} — ${esc(an)}</span><b>${r.hs}:${r.as}${r.x?`<em>${esc(r.x)}</em>`:''}</b></li>`}).join('')}</ul></section>`}

/* лидеры */
function leadersOf(m,s,ph){
  const T=team(m,s);if(!T)return null;
  if(isH(m)){const sk=T.pl&&T.pl.sk;if(!sk||!sk.length)return null;
    return sk.slice().sort((a,b)=>(b.pts-a.pts)||(b.g-a.g)).slice(0,3).map(p=>({n:p.n,sub:`${p.pos||''} · ${p.g} г + ${p.a} п · ${p.gp} и`.replace(/^ · /,''),v:p.pts,u:'очк.',img:ph&&ph[p.n]}))}
  const sc=T.sc;if(!sc||!sc.length)return null;
  return sc.slice(0,3).map(p=>({n:p.n,sub:p.p?`${p.p} с пенальти`:'',v:p.g,u:'голов'}))}
function leadersHtml(m,d){
  const A=leadersOf(m,m.h,d.ph[0]),B=leadersOf(m,m.a,d.ph[1]);if(!A&&!B)return '';
  const col=(s,n,L,c)=>L?`<div><h4 style="--c:${c}"><i></i>${esc(n)}</h4><ul class="dk-ld">${L.map(p=>`<li>${p.img?`<img src="${esc(p.img)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.outerHTML='<span class=ph></span>'">`:`<span class="ph">${esc(p.n.split(/\s+/).map(w=>w[0]).slice(0,2).join(''))}</span>`}<div><b>${esc(p.n)}</b>${p.sub?`<small>${esc(p.sub)}</small>`:''}</div><strong title="${p.u}">${p.v}</strong></li>`).join('')}</ul></div>`:'';
  return `<section class="dk-sec"><h3>${isH(m)?'Лидеры по очкам (гол + передача)':'Лучшие бомбардиры клуба в лиге'}</h3><div class="dk-two">${col(m.h,m.hn,A,'var(--dk-ca,#ffc21a)')}${col(m.a,m.an,B,isH(m)?'var(--dk-cb,#4cc2ff)':'var(--dk-cb,#3dd68c)')}</div></section>`}

/* последние 5 матчей */
function lastHtml(m){const fa=formOf(m,m.h),fb=formOf(m,m.a);if(!fa&&!fb)return '';
  const col=(s,n,f,c)=>f?`<div><h4 style="--c:${c}"><i></i>${esc(n)}</h4><ul class="dk-lg5">${f.slice().reverse().map(x=>`<li class="${x.r}"><span><small>${shortDate(x.d)}</small>${x.h?'':'@ '}${esc(nameOf(m,x.o))}</span><b>${x.gf}:${x.ga}${x.x?' '+esc(x.x):''}</b></li>`).join('')}</ul></div>`:'';
  return `<section class="dk-sec"><h3>Последние 5 матчей</h3><div class="dk-two">${col(m.h,m.hn,fa,'var(--dk-ca,#ffc21a)')}${col(m.a,m.an,fb,isH(m)?'var(--dk-cb,#4cc2ff)':'var(--dk-cb,#3dd68c)')}</div></section>`}

function linksHtml(m){return `<section class="dk-sec"><h3>Страницы сайта</h3><div class="dk-links">
  <a href="${clubHref(m,m.h)}">${esc(m.hn)}</a><a href="${clubHref(m,m.a)}">${esc(m.an)}</a><a href="${lgHref(m)}">${esc(lgFull(m))}</a></div></section>`}
function detailHtml(m,d){return radarHtml(m)+h2hHtml(m)+leadersHtml(m,d)+lastHtml(m)+linksHtml(m)}

/* ── оформление карточки: ?card=1|2|3 (1 «Цвета клубов» — по умолчанию, 2 «Стекло», 3 «Билет») ── */
{let c=q.get('card');if(!/^[123]$/.test(c||''))c='3'; /* выбор владельца 04.11 — «Билет»; ?card=1|2 — для сравнения */root.dataset.card=c;
 const sw=document.getElementById('dk-cards');
 const mark=()=>sw&&sw.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.c===root.dataset.card)));
 if(sw){mark();sw.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;root.dataset.card=b.dataset.c;mark();
   try{const u=new URL(location.href);u.searchParams.set('card',b.dataset.c);history.replaceState(null,'',u)}catch(_){}})}}

/* ── запуск ── */
function init(){
  const sub=$('dk-sub');
  sub.textContent=ALL.length?`${ALL.length} ${pl(ALL.length,['матч','матча','матчей'])} на сегодня и завтра`:'';
  applyFilter();
  const k=q.get('k');if(k){const i=list.findIndex(m=>m.key===k);if(i>=0)cur=i}
  counts();build();renderInfo(false);applyBg(0);
  let rt=0;addEventListener('resize',()=>{clearTimeout(rt);rt=setTimeout(()=>{measure();layout()},80)});
  if(mqM.addEventListener)mqM.addEventListener('change',()=>{measure();layout()});
  if(window.ResizeObserver)new ResizeObserver(()=>{const w=W;measure();if(w!==W)layout()}).observe(stage);
}
if(ALL.length)init();else{$('dk-info').innerHTML='<p class="dk-empty">Матчей в окне пока нет — данные обновляются дважды в день.</p>'}
})();
