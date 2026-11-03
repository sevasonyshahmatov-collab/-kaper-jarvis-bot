/* JARVIS v3a — «Тренды дня»: общий движок для football/trends.html и hockey/trends.html.
   Данные: футбол — window.JV_TRENDS_F (football/trends_build.py) + window.JV_PLAYERS; хоккей — window.JV_TEAMS + hockey/data/*_players.json.
   Тренды считаются в браузере из матчей сезона; ни кэфов, ни ставок здесь нет. ?now=2026-11-03 12:00 — подменить «сейчас» (МСК). */
(()=>{
'use strict';
const SPORT=document.body.dataset.field;           // football | hockey
const FB=SPORT==='football';
const $=s=>document.querySelector(s);
const esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const plural=(n,a,b,c)=>{const k=n%100,j=n%10;return k>10&&k<20?c:j===1?a:j>1&&j<5?b:c};
const MON=['янв.','февр.','мар.','апр.','мая','июн.','июл.','авг.','сент.','окт.','нояб.','дек.'];
const atMs=d=>Date.parse(d.replace(' ','T')+':00+03:00');
const Q=new URLSearchParams(location.search);
let NOW=Date.now();
if(/^\d{4}-\d\d-\d\d( \d\d:\d\d)?$/.test(Q.get('now')||''))NOW=atMs((Q.get('now')+' 12:00').slice(0,16));
const mskDay=ms=>new Date(ms+3*3600e3).toISOString().slice(0,10);
const TODAY=mskDay(NOW),TOMORROW=mskDay(NOW+864e5);
const when=d=>{const day=d.slice(0,10),t=d.slice(11,16);
  if(atMs(d)<=NOW)return 'идёт, начало '+t;
  if(day===TODAY)return 'сегодня, '+t; if(day===TOMORROW)return 'завтра, '+t;
  return +day.slice(8)+' '+MON[+day.slice(5,7)-1]+', '+t};

/* ── настройки по виду спорта ──────────────────────────────── */
const CFG=FB?{
  lgs:['epl','laliga','seriea','bundesliga','ligue1','rpl','ucl','uel'],
  em:s=>'../assets/fc/'+s+'.webp', team:s=>'team.html?id='+s,
  types:{streak:'Серии',tb:'ТБ 2.5',tm:'ТМ 2.5',btts:'Обе забьют',cs:'Сухие матчи',fs:'Забивает первым',sc:'Забивает',cor:'Угловые',pl:'Игроки'},
  lgName:{}, 
}:{
  lgs:['khl','nhl'],
  em:s=>'../assets/em/'+s+'.webp', team:s=>'../team/index.html?id='+s,
  types:{streak:'Серии',wl:'Дома и в гостях',tb:'ТБ 5.5',tm:'ТМ 5.5',g3:'Забивает 3+',ga3:'Пропускает 3+',ot:'Овертаймы',pl:'Игроки'},
  lgName:{khl:'КХЛ',nhl:'НХЛ'},
};

/* ── математика трендов ────────────────────────────────────── */
const wilson=(k,n)=>{const p=k/n;return (p+1/(2*n)-Math.sqrt(p*(1-p)/n+1/(4*n*n)))/(1+1/n)};
const sum=a=>a.reduce((x,y)=>x+y,0);
const strongDef=(k,n)=>(k===n&&n>=5)||(n>=6&&k/n>=.85);
const SC={home:'домашних',away:'выездных',all:'последних'};
/* g — [дата, дома, забито, пропущено, ...доп.]; метрики описаны ниже; выбирается лучший из «дома/в гостях» и «последние матчи» */
function ratio(games,home,M){
  const out=[];
  for(const m of M){
    let best=null;
    const scopes=m.venueOnly?['v']:['v','a'];
    for(const sc of scopes){
      let list=sc==='v'?games.filter(g=>!!g[1]===home):games;
      if(m.has)list=list.filter(m.has);
      list=list.slice(-(m.win||8));
      const n=list.length;if(n<(m.minN||5))continue;
      const seq=list.map(g=>m.pred(g)?1:0),k=sum(seq);
      if(k/n<(m.minPct||.7))continue;
      const c={k,n,seq,sc:sc==='a'?'all':(home?'home':'away'),score:(m.w||1)*wilson(k,n)+(sc==='v'?.0001:0)};
      if(!best||c.score>best.score)best=c;
    }
    if(!best)continue;
    out.push({type:m.id,tag:m.tag,html:m.f(best.k,best.n,SC[best.sc]),big:best.k+'<small>/'+best.n+'</small>',seq:best.seq,score:best.score,
      strong:(m.strong||strongDef)(best.k,best.n)});
  }
  return out;
}
/* серии: games по возрастанию даты; res(g) → 'w' | 'd' | 'l' */
function runs(games,res,home){
  const r=games.map(res).reverse();
  const len=f=>{let i=0;while(i<r.length&&f(r[i]))i++;return i};
  const seq=games.slice(-8).map(g=>({w:1,d:2,l:0})[res(g)]);
  const o=[],W=len(x=>x==='w'),U=len(x=>x!=='l'),N=len(x=>x!=='w'),L=len(x=>x==='l');
  const mk=(L,html,score,strong)=>o.push({type:'streak',tag:'Серия',html,big:L+'<small> подряд</small>',seq,score,strong});
  if(W>=4)mk(W,`<b>${W}</b> ${plural(W,'победа','победы','побед')} подряд`,.5+.05*(W-3),W>=5);
  if(U>=4&&U>W&&!(U===W))mk(U,`<b>${U}</b> ${plural(U,'матч','матча','матчей')} без поражений`,.45+.04*(U-3),U>=7);
  if(L>=4)mk(L,`<b>${L}</b> ${plural(L,'поражение','поражения','поражений')} подряд`,.5+.05*(L-3),L>=5);
  else if(N>=4)mk(N,`<b>${N}</b> ${plural(N,'матч','матча','матчей')} без побед`,.4+.04*(N-3),N>=7);
  return o;
}
const B=(k,n)=>`<b>${k} из ${n}</b>`;

/* ── метрики футбола: g = [d, дома, gf, ga, первым(1/-1/0), угловых, кубок] ─ */
const FM=[
  {id:'tb',tag:'ТБ 2.5',pred:g=>g[2]+g[3]>=3,f:(k,n,s)=>`ТБ 2.5 в ${B(k,n)} ${s} матчей`},
  {id:'tm',tag:'ТМ 2.5',pred:g=>g[2]+g[3]<=2,f:(k,n,s)=>`ТМ 2.5 в ${B(k,n)} ${s} матчей`},
  {id:'btts',tag:'Обе забьют',pred:g=>g[2]>0&&g[3]>0,f:(k,n,s)=>`обе команды забивали в ${B(k,n)} ${s} матчей`},
  {id:'cs',tag:'Сухие матчи',pred:g=>g[3]===0,f:(k,n,s)=>`не пропускал в ${B(k,n)} ${s} матчей`},
  {id:'fs',tag:'Забивает первым',pred:g=>g[4]===1,f:(k,n,s)=>`забивал первым в ${B(k,n)} ${s} матчей`},
  {id:'sc',tag:'Забивает',minPct:.9,w:.8,pred:g=>g[2]>0,f:(k,n,s)=>`забивал в ${B(k,n)} ${s} матчей`},
  {id:'cor',tag:'Угловые 9.5+',has:g=>g[5]!=null,pred:g=>g[5]>=10,f:(k,n,s)=>`угловых 10 и больше за матч — в ${B(k,n)} ${s} матчей`},
];
/* ── метрики хоккея: g = [d, дома, gf, ga, x] ─────────────────── */
const HM=[
  {id:'tb',tag:'ТБ 5.5',pred:g=>g[2]+g[3]>=6,f:(k,n,s)=>`ТБ 5.5 в ${B(k,n)} ${s} матчей`},
  {id:'tm',tag:'ТМ 5.5',pred:g=>g[2]+g[3]<=5,f:(k,n,s)=>`ТМ 5.5 в ${B(k,n)} ${s} матчей`},
  {id:'g3',tag:'Забивает 3+',pred:g=>g[2]>=3,f:(k,n,s)=>`забивал 3 и больше в ${B(k,n)} ${s} матчей`},
  {id:'ga3',tag:'Пропускает 3+',pred:g=>g[3]>=3,f:(k,n,s)=>`пропускал 3 и больше в ${B(k,n)} ${s} матчей`},
  {id:'ot',tag:'Овертаймы',win:10,minN:8,minPct:.4,pred:g=>!!g[4],f:(k,n,s)=>`доходил до овертайма или буллитов в ${B(k,n)} ${s} матчей`,strong:(k,n)=>k/n>=.5},
  {id:'wl',tag:'Победы',venueOnly:true,pred:g=>g[2]>g[3],f:(k,n,s)=>`побеждал в ${B(k,n)} ${s} матчей`},
  {id:'wl',tag:'Поражения',venueOnly:true,pred:g=>g[2]<g[3],f:(k,n,s)=>`проигрывал в ${B(k,n)} ${s} матчей`},
];

/* ── данные ─────────────────────────────────────────────────── */
const S={lgInfo:{},teams:{},matches:[],trends:[],notes:[],ready:false};
function loadFootball(){
  const D=window.JV_TRENDS_F;if(!D)return false;
  CFG.lgs.forEach(id=>{const l=D.leagues[id];S.lgInfo[id]={id,name:l?l.s:id,full:l?l.n:id}});
  for(const s in D.teams)S.teams[s]={slug:s,name:D.teams[s].n,lg:D.teams[s].lg,g:D.teams[s].g};
  S.all=D.up.map(u=>({lg:u[0],d:u[1],h:u[2],a:u[3]}));
  S.built=D.built;return true;
}
function loadHockey(){
  const D=window.JV_TEAMS;if(!D)return false;
  CFG.lgs.forEach(id=>{S.lgInfo[id]={id,name:CFG.lgName[id],full:CFG.lgName[id]}});
  const seen=new Set();S.all=[];
  for(const s in D.teams){const t=D.teams[s],gs=t.games||[];
    S.teams[s]={slug:s,name:t.name,lg:t.lg,g:gs.filter(g=>g.gf!=null).map(g=>[g.d,g.h,g.gf,g.ga,g.x||''])};
    for(const g of gs)if(g.gf==null&&g.h===1){const k=g.d+s+g.o;if(!seen.has(k)){seen.add(k);S.all.push({lg:t.lg,d:g.d,h:s,a:g.o})}}}
  S.built=D.built;return true;
}
/* ближайшие 2 дня по каждой лиге; нет матчей в окне — ближайшие 10 */
function pickMatches(){
  const lo=NOW-3*3600e3,hi=NOW+48*3600e3,out=[];S.notes=[];S.fallback=[];S.empty=[];
  for(const id of CFG.lgs){
    const list=S.all.filter(m=>m.lg===id&&atMs(m.d)>=lo&&S.teams[m.h]&&S.teams[m.a]).sort((a,b)=>a.d<b.d?-1:a.d>b.d?1:0);
    const inw=list.filter(m=>atMs(m.d)<=hi);
    if(inw.length)out.push(...inw);
    else if(list.length){out.push(...list.slice(0,10));S.fallback.push(id)}
    else S.empty.push(id);
  }
  out.sort((a,b)=>a.d<b.d?-1:a.d>b.d?1:0);
  out.forEach((m,i)=>m.i=i);
  S.matches=out;
}

/* ── сборка трендов ─────────────────────────────────────────── */
function teamTrends(m,slug,home){
  const T=S.teams[slug];if(!T)return[];
  const games=T.g.slice().sort((a,b)=>a[0]<b[0]?-1:1);
  const res=FB?g=>g[2]>g[3]?'w':g[2]===g[3]?'d':'l':g=>g[2]>g[3]?'w':'l';
  const L=[...runs(games,res,home),...ratio(games,home,FB?FM:HM)];
  return L.map(t=>({...t,m,slug,who:T.name,pl:false}));
}
function playerTrends(){
  const out=[];const byTeam={};
  S.matches.forEach(m=>{(byTeam[m.h]=byTeam[m.h]||[]).push(m);(byTeam[m.a]=byTeam[m.a]||[]).push(m)});
  const add=(slug,name,cands)=>{ // cands: {id,tag,k,n,seq,f}
    const ms=byTeam[slug];if(!ms)return;
    let best=null;
    for(const c of cands){if(c.n<5||c.k/c.n<.7)continue;c.score=wilson(c.k,c.n);if(!best||c.score>best.score)best=c}
    if(!best)return;
    out.push({type:'pl',tag:best.tag,html:best.f,big:best.k+'<small>/'+best.n+'</small>',seq:best.seq,score:best.score,
      strong:best.k/best.n>=.8,m:ms[0],slug,who:name,pl:true,teamName:S.teams[slug]&&S.teams[slug].name});
  };
  if(FB&&window.JV_PLAYERS){
    for(const p of window.JV_PLAYERS.players){
      if(!p.f||!byTeam[p.t])continue;
      const c=[];
      for(const w of [5,10]){if(p.f.length<w)continue;const s=[...p.f.slice(-w)].map(x=>x==='g'?1:0),k=sum(s);
        c.push({tag:'Забивает',k,n:w,seq:s,f:`забивал в ${B(k,w)} последних матчей`})}
      if(p.sg&&p.sg[1]>=8)c.push({tag:'Забивает',k:p.sg[0],n:p.sg[1],seq:[...p.f].map(x=>x==='g'?1:0).slice(-8),f:`забил в ${B(p.sg[0],p.sg[1])} матчей сезона`});
      add(p.t,p.n,c);
    }
  }
  if(!FB&&S.nhl){
    for(const p of S.nhl){
      if(!byTeam[S.abbr[p.t]])continue;
      const log=p.log.filter(r=>r[7]>0).slice(-10);if(log.length<5)continue;
      const c=[];
      for(const w of [5,8,10]){const l=log.slice(-w);if(l.length<w&&w!==log.length)continue;
        const n=l.length;
        let s=l.map(r=>r[4]+r[5]>=1?1:0);c.push({tag:'Очко',k:sum(s),n,seq:s,f:`очко в ${B(sum(s),n)} последних матчей`});
        s=l.map(r=>r[6]>=3?1:0);c.push({tag:'3+ броска',k:sum(s),n,seq:s,f:`3 и больше бросков в ${B(sum(s),n)} последних матчей`});
        s=l.map(r=>r[4]>=1?1:0);c.push({tag:'Забивает',k:sum(s),n,seq:s,f:`забивал в ${B(sum(s),n)} последних матчей`});
      }
      add(S.abbr[p.t],p.n,c);
    }
  }
  if(!FB&&S.khl){
    for(const p of S.khl){
      if(!byTeam[p.t]||p.gp!==p.log.length)continue;     // в логе КХЛ нет данных, кто играл: берём только тех, кто сыграл все матчи
      const log=p.log.slice(-10);if(log.length<5)continue;
      const c=[];
      for(const w of [5,8,10]){const l=log.slice(-w);if(l.length<w)continue;
        let s=l.map(r=>r[4]+r[5]>=1?1:0);c.push({tag:'Очко',k:sum(s),n:w,seq:s,f:`очко в ${B(sum(s),w)} последних матчей`});
        s=l.map(r=>r[4]>=1?1:0);c.push({tag:'Забивает',k:sum(s),n:w,seq:s,f:`забивал в ${B(sum(s),w)} последних матчей`});
      }
      add(p.t,p.n,c);
    }
  }
  /* не больше 4 игроков на клуб */
  const cnt={};return out.sort((a,b)=>b.score-a.score).filter(t=>{cnt[t.slug]=(cnt[t.slug]||0)+1;return cnt[t.slug]<=4});
}
function build(){
  S.trends=[];
  S.matches.forEach(m=>{S.trends.push(...teamTrends(m,m.h,true),...teamTrends(m,m.a,false))});
  S.trends.push(...playerTrends());
  S.trends.sort((a,b)=>b.score-a.score||a.m.i-b.m.i);
  S.trends.forEach((t,i)=>{t.id=i});
}

/* ── интерфейс ──────────────────────────────────────────────── */
const ST={lg:'all',type:'all',strong:Q.get('strong')==='1',sort:Q.get('sort')==='match'?'match':'power',limit:30};
if(CFG.lgs.includes(Q.get('lg')))ST.lg=Q.get('lg');
if(Q.get('type')&&CFG.types[Q.get('type')])ST.type=Q.get('type');
const PAGE=30;
const lgp=id=>`<span class="lgp ${id==='nhl'?'nhl':id==='khl'?'khl':''}"><img src="../assets/lg/${id}.webp" alt=""></span>`;
const crest=(slug,cls)=>`<img src="${CFG.em(slug)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">`;
const link=(slug,name)=>`<a href="${CFG.team(slug)}">${esc(name)}</a>`;
const initials=n=>n.split(/\s+/).map(w=>w[0]).filter(Boolean).slice(0,2).join('').toUpperCase();
const dots=seq=>`<span class="sdots" role="img" aria-label="Последние матчи: ${seq.map(x=>x===1?'да':x===2?'ничья':'нет').join(', ')}">${seq.map(x=>`<i class="${x===1?'h':x===2?'d':'m'}"></i>`).join('')}</span>`;

function pass(t,skip){
  if(skip!=='lg'&&ST.lg!=='all'&&t.m.lg!==ST.lg)return false;
  if(skip!=='type'&&ST.type!=='all'&&t.type!==ST.type)return false;
  if(ST.strong&&!t.strong)return false;
  return true;
}
function row(t,ctx){
  const m=t.m,H=S.teams[m.h],A=S.teams[m.a];
  const em=t.pl?`<span class="tr-em pl" aria-hidden="true">${esc(initials(t.who))}</span>`:`<a class="tr-em" href="${CFG.team(t.slug)}" tabindex="-1" aria-hidden="true">${crest(t.slug)}</a>`;
  const who=t.pl?`${esc(t.who)} (${link(t.slug,t.teamName||'')})`:link(t.slug,t.who);
  const meta=ctx?'':`<span>${lgp(m.lg)} ${link(m.h,H.name)} — ${link(m.a,A.name)}</span><span>${when(m.d)}</span>`;
  return `<li class="tr${t.strong?' strong':''}">${em}<div class="tr-b"><p class="tr-t">${who}: ${t.html}</p>
<p class="tr-m"><span class="tg${t.strong?' s':''}">${esc(t.tag)}${t.strong?' · сильный':''}</span>${meta}</p></div>
<div class="tr-s">${dots(t.seq)}<b class="tr-n num">${t.big}</b></div></li>`;
}
function matchHead(m){
  const H=S.teams[m.h],A=S.teams[m.a];
  return `<li class="tg-match" aria-hidden="false" style="list-style:none"><div class="tms">${crest(m.h)}${crest(m.a)}</div>
<h3>${link(m.h,H.name)} — ${link(m.a,A.name)}</h3><p>${lgp(m.lg)} ${esc(S.lgInfo[m.lg].full)} · ${when(m.d)}</p></li>`;
}
function chip(cls,pressed,label,count,attrs){
  return `<button type="button" class="tab ${cls}" aria-pressed="${pressed}" ${attrs}>${label}<span class="c num">${count}</span></button>`;
}
function renderBar(){
  const L=S.trends;
  const cL=id=>L.filter(t=>pass(t,'lg')&&(id==='all'||t.m.lg===id)).length;
  $('#fLg').innerHTML=chip('',ST.lg==='all','Все лиги',cL('all'),'data-lg="all"')+
    CFG.lgs.map(id=>chip('',ST.lg===id,lgp(id)+esc(S.lgInfo[id].name),cL(id),`data-lg="${id}"`)).join('');
  const cT=id=>L.filter(t=>pass(t,'type')&&(id==='all'||t.type===id)).length;
  $('#fType').innerHTML=chip('',ST.type==='all','Все типы',cT('all'),'data-type="all"')+
    Object.keys(CFG.types).map(id=>chip('',ST.type===id,esc(CFG.types[id]),cT(id),`data-type="${id}"`)).join('');
  $('#fStrong').setAttribute('aria-pressed',ST.strong);
  $('#fSortP').setAttribute('aria-pressed',ST.sort==='power');
  $('#fSortM').setAttribute('aria-pressed',ST.sort==='match');
}
function render(){
  renderBar();
  const list=S.trends.filter(t=>pass(t));
  const ms=new Set(list.map(t=>t.m.i));
  const mAll=S.matches.filter(m=>ST.lg==='all'||m.lg===ST.lg);
  $('#sum').innerHTML=`<b class="num">${list.length}</b><span>${plural(list.length,'тренд','тренда','трендов')} в ${mAll.length} ${plural(mAll.length,'матче','матчах','матчах')}</span>`+
    `<span>время московское</span>`+(S.built?`<span>данные на ${esc(String(S.built).slice(0,16))}</span>`:'');
  /* плашки: лиги без матчей и лиги с запасным окном */
  const plates=[];
  const nm=id=>S.lgInfo[id].name;
  const fb=S.fallback.filter(id=>ST.lg==='all'||ST.lg===id),em=S.empty.filter(id=>ST.lg==='all'||ST.lg===id);
  if(fb.length)plates.push(`<b>${fb.map(nm).join(', ')}:</b> в ближайшие 2 дня матчей нет, показаны ближайшие 10 матчей лиги.`);
  if(em.length)plates.push(`<b>${em.map(nm).join(', ')}:</b> будущих матчей в данных нет — тренды появятся, когда выйдет расписание.`);
  $('#plates').innerHTML=plates.map(p=>`<p class="tr-plate">${p}</p>`).join('');
  const box=$('#tlist');
  if(!list.length){
    const noM=mAll.length===0;
    box.innerHTML=`<li class="tr-empty"><b>${noM?'Матчей пока нет':'Под фильтры ничего не подошло'}</b>${noM?'В этой лиге нет матчей в расписании. Загляните позже или выберите другую лигу.':'Сильные тренды бывают не в каждом матче. Снимите «Только сильные» или выберите другой тип.'}</li>`;
    $('#more').hidden=true;return;
  }
  const lim=ST.limit;let html='';
  if(ST.sort==='power'){
    html=list.slice(0,lim).map(t=>row(t,false)).join('');
    $('#more').hidden=list.length<=lim;
  }else{
    const part=list.slice().sort((a,b)=>a.m.i-b.m.i||b.score-a.score).slice(0,lim);
    let cur=-1;
    for(const t of part){if(t.m.i!==cur){cur=t.m.i;html+=matchHead(t.m)}html+=row(t,true)}
    $('#more').hidden=list.length<=lim;
  }
  box.innerHTML=html;
}
function sync(){
  const p=new URLSearchParams();
  if(ST.lg!=='all')p.set('lg',ST.lg);if(ST.type!=='all')p.set('type',ST.type);if(ST.strong)p.set('strong','1');if(ST.sort==='match')p.set('sort','match');
  if(Q.get('now'))p.set('now',Q.get('now'));
  try{history.replaceState(null,'',location.pathname+(p.toString()?'?'+p:''))}catch(e){}
}
function bind(){
  document.addEventListener('click',e=>{
    const b=e.target.closest('button');if(!b)return;
    if(b.dataset.lg){ST.lg=b.dataset.lg}
    else if(b.dataset.type){ST.type=b.dataset.type}
    else if(b.id==='fStrong'){ST.strong=!ST.strong}
    else if(b.id==='fSortP'){ST.sort='power'}
    else if(b.id==='fSortM'){ST.sort='match'}
    else if(b.id==='more'){ST.limit+=PAGE;render();return}
    else return;
    ST.limit=PAGE;render();sync();
  });
}

/* ── запуск ─────────────────────────────────────────────────── */
function fail(msg){$('#tlist').innerHTML=`<li class="tr-empty"><b>Данные не загрузились</b>${msg}</li>`;$('#sum').innerHTML=''}
function start(){
  if(!(FB?loadFootball():loadHockey()))return fail('Файл с матчами сезона не найден. Обновите страницу позже.');
  pickMatches();build();bind();render();sync();
}
start();
if(!FB){   // игроков хоккея читаем отдельно: файлы большие, страница работает и без них
  const ab=s=>({minnesota:'MIN',dallas:'DAL'})[s]||s.replace('nhl_','').toUpperCase();
  S.abbr={};Object.keys(S.teams).forEach(s=>{if(S.teams[s].lg==='nhl')S.abbr[ab(s)]=s});
  // S.abbr: аббревиатура → slug; в игроках НХЛ p.t — аббревиатура, поэтому для byTeam нужен обратный поиск
  const get=u=>fetch(u).then(r=>r.ok?r.json():Promise.reject()).then(j=>j.players);
  Promise.allSettled([get('data/nhl_players.json'),get('data/khl_players.json')]).then(([n,k])=>{
    if(n.status==='fulfilled')S.nhl=n.value;if(k.status==='fulfilled')S.khl=k.value;
    if(S.nhl||S.khl){build();render()}
  });
}
})();
