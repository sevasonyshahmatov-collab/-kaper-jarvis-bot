/* Варианты первого блока страниц «Хоккей» и «Футбол» (макет, 07.11): ?hh=1..9 (9 «Плитки» — только хоккей, hero9.js). Без параметра файл ничего не делает.
   1 Игрок · 2 Бенто · 3 Лента матчей · 4 Колода · 5 Центр. hh=0 — как сейчас (виден только переключатель).
   Данные те же, что у старой шапки: хоккей — JVL (today.js + lines.js + model.js), футбол — JVF.D.up после foot-index.js.
   Подключён в <head> ДО herobg.js: если в адресе нет hbg, дописывает его (фон «Колода лиг»), и herobg.js его подхватывает. */
(()=>{
'use strict';
let q=null,P=null;try{P=new URLSearchParams(location.search);q=P.get('hh')}catch(e){}
if(q===null)return;
const SCR=document.currentScript,BASE=SCR&&SCR.src?new URL('.',SCR.src).href:'';
const HOME=!/\/(hockey|football)\//.test(location.pathname);   // на главной работают только 0, 6, 7 (8 — только хоккей и футбол)
const HK=/\/hockey\//.test(location.pathname);   // 9 «Плитки» — только хоккей
const N0=/^[0-9]$/.test(q)?+q:0,N=HOME&&(N0<6||N0>7)||N0===9&&!HK?0:N0,de=document.documentElement;
const BG={4:'2'};            // фон по умолчанию для вариантов: 1 «Колода лиг», у «Колоды» — «Свет арены» (карточки не спорят с фоном)
if(N>=6&&P.get('hbg')!==null){try{P.delete('hbg');history.replaceState(null,'',location.pathname+(P.toString()?'?'+P.toString():'')+location.hash)}catch(e){}}
if(N&&N<6&&P.get('hbg')===null){try{P.set('hbg',BG[N]||'1');history.replaceState(null,'',location.pathname+'?'+P.toString()+location.hash)}catch(e){}}
if(N)de.dataset.hh=N;

const NAMES=['Как сейчас','Игрок','Бенто','Лента матчей','Колода','Центр','Протокол','Космос','Арена','Плитки'];
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const HOVER=matchMedia('(hover:hover) and (pointer:fine)').matches;

function switcher(){
 const el=document.createElement('nav');el.className='hh-sw';el.setAttribute('aria-label','Вариант первого блока');
 el.innerHTML='<span>Шапка</span>'+NAMES.map((t,i)=>(HOME&&((i>0&&i<6)||i>7))||(i===9&&!HK)?'':`<a href="#" data-n="${i}" title="${i} — ${t}"${i===N?' aria-current="true"':''}>${i}</a>`).join('')+`<em>${N} — ${NAMES[N]}</em>`;
 el.addEventListener('click',e=>{const a=e.target.closest('a');if(!a)return;e.preventDefault();
  const u=new URL(location.href);u.searchParams.set('hh',a.dataset.n);if(+a.dataset.n>=6||a.dataset.n==='0')u.searchParams.delete('hbg');else if(u.searchParams.get('hbg')===null)u.searchParams.set('hbg',BG[a.dataset.n]||'1');location.href=u.toString()});
 document.body.append(el);
}

/* ── данные ── */
const esc=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const f2=v=>v==null||isNaN(v)?'—':(+v).toFixed(2).replace('.',',');
const pct=v=>Math.round(v*100);
const plural=(n,a,b,c)=>{const k=n%100,j=n%10;return k>10&&k<20?c:j===1?a:j>1&&j<5?b:c};
const left=t=>Math.round((Date.parse(t.replace(' ','T')+':00+03:00')-Date.now())/1000);
const mskDay=ms=>new Date(ms+3*3600e3).toISOString().slice(0,10);
const MON=['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'];
const LGP=id=>`<span class="lgp ${esc(id)}"><img src="${BASE}../lg/${esc(id)}.webp" alt=""></span>`;

function hockey(){
 const {TD,L,M}=window.JVL;
 const all=(TD.matches||[]).filter(m=>m.lg==='khl'||m.lg==='nhl').sort((a,b)=>a.t<b.t?-1:1);
 const fresh=all.filter(m=>left(m.t)>-3*3600),src=fresh.length?fresh:all;
 const list=src.map(m=>{const md=M[m.key]||null,ln=L[m.key]||null;let top=null,pr=null;
  if(md){pr=[md.p1,md.x,md.p2];const i=pr.indexOf(Math.max(...pr));
   top={i,p:pr[i],s:['П1','Х','П2'][i],word:i===0?`${m.hn} — победа`:i===2?`${m.an} — победа`:'Ничья в основное время',k:ln?[ln.p1,ln.x,ln.p2][i]:null}}
  return {key:m.key,lg:m.lg,t:m.t,hn:m.hn,an:m.an,hc:`../assets/em/${m.h}.webp`,ac:`../assets/em/${m.a}.webp`,pr,k:ln?[ln.p1,ln.x,ln.p2]:null,lam:md&&md.lam||null,top,xl:'Ничья'}});
 const leagues=[['khl','КХЛ'],['nhl','НХЛ']];
 return {list,leagues,three:true};
}
function football(){
 const F=window.JVF,D=F.D,LGK=Object.keys(D.leagues);
 const FUT=D.up.filter(m=>LGK.includes(m.lg)&&left(m.t)>-2*3600).sort((a,b)=>a.t<b.t?-1:1);
 const win={};LGK.forEach(k=>{win[k]=[...new Set(FUT.filter(m=>m.lg===k).map(m=>m.t.slice(0,10)))].slice(0,3)});
 const UP=FUT.filter(m=>win[m.lg].includes(m.t.slice(0,10)));
 const best=m=>{const A=F.nm(m.h),B=F.nm(m.a),tk=m.tt&&m.tt[0]===m.ot,
  c=[{i:0,p:m.pr[0],word:`${A} — победа`,s:'П1',k:m.k&&m.k[0]},{i:2,p:m.pr[2],word:`${B} — победа`,s:'П2',k:m.k&&m.k[2]},
   {i:3,p:m.ov,word:`Тотал больше ${F.fx(m.ot,1)}`,s:'ТБ',k:tk?m.tt[1]:null},{i:4,p:1-m.ov,word:`Тотал меньше ${F.fx(m.ot,1)}`,s:'ТМ',k:tk?m.tt[2]:null}],
  ck=c.filter(x=>x.k);return (ck.length?ck:c).sort((a,b)=>b.p-a.p)[0]};
 const list=UP.map(m=>({lg:m.lg,t:m.t,hn:F.nm(m.h),an:F.nm(m.a),hc:F.crest(m.h),ac:F.crest(m.a),pr:m.pr,k:m.k||null,lam:m.xg||null,top:best(m),xl:'Ничья'}));
 return {list,leagues:LGK.map(k=>[k,D.leagues[k].name]),three:true};
}

const LGN={khl:'КХЛ',nhl:'НХЛ',epl:'АПЛ',laliga:'Ла Лига',seriea:'Серия А',bundesliga:'Бундеслига',ligue1:'Лига 1',rpl:'РПЛ',ucl:'Лига чемпионов',uel:'Лига Европы'};
function home(){
 const {TD,L,M}=window.JVL;
 const all=(TD.matches||[]).filter(m=>m.t&&m.h&&m.a).sort((a,b)=>a.t<b.t?-1:1);
 const fresh=all.filter(m=>left(m.t)>-3*3600),src=fresh.length?fresh:all;
 const list=src.map(m=>{const md=M[m.key]||null,ln=L[m.key]||null;let top=null,pr=null;
  if(md&&md.p1!=null){pr=[md.p1,md.x,md.p2];const i=pr.indexOf(Math.max(...pr));
   top={i,p:pr[i],s:['П1','Х','П2'][i],word:i===0?`${m.hn} — победа`:i===2?`${m.an} — победа`:'Ничья в основное время',k:ln?[ln.p1,ln.x,ln.p2][i]:null}}
  return {lg:m.lg,t:m.t,hn:m.hn,an:m.an,pr,k:ln?[ln.p1,ln.x,ln.p2]:null,top,sp:m.lg==='khl'||m.lg==='nhl'?'h':'f'}});
 const ids=[...new Set(list.map(m=>m.lg))];
 return {list,leagues:ids.map(k=>[k,LGN[k]||k]),three:true};
}
function model(sport){
 const d=sport==='home'?home():sport==='football'?football():hockey();
 d.list.forEach(m=>{if(!m.sp)m.sp=sport==='football'?'f':'h'});
 const up=d.list.filter(m=>left(m.t)>0),base=up.length?up:d.list;
 const d0=base.length?base[0].t.slice(0,10):'';
 let day=base.filter(m=>m.t.slice(0,10)===d0);if(day.length<3)day=base.slice(0,6);
 const total=day.length,conf=m=>m.top?m.top.p:-1;
 if(day.length>12)day=day.slice().sort((a,b)=>conf(b)-conf(a)).slice(0,12).sort((a,b)=>a.t<b.t?-1:1);
 const top=day.slice().sort((a,b)=>conf(b)-conf(a))[0]||null;
 const byConf=day.slice().sort((a,b)=>conf(b)-conf(a));
 const rest=day.filter(m=>m!==top);
 const today=mskDay(Date.now());
 const lgs=d.leagues.filter(([k])=>day.some(m=>m.lg===k));
 return {...d,base,day,top,byConf,rest,total,nowDay:d0===today,d0,next:up[0]||null,lgs,nModel:day.filter(m=>m.top).length};
}

/* ── кирпичики ── */
const tm=m=>m.t.slice(11,16);
const when=m=>{const d=m.t.slice(0,10);return d===mskDay(Date.now())?tm(m):`${+d.slice(8)} ${MON[+d.slice(5,7)-1]} · ${tm(m)}`};
const E=(src,cls='')=>`<span class="e ${cls}"><img src="${esc(src)}" alt="" width="64" height="64"></span>`;
const bar=p=>`<span class="hpb"><i style="--w:${pct(p)}%"></i></span>`;
const BTN='<a class="btn btn-tg" href="https://t.me/jarvibet" target="_blank" rel="noopener">Получать прогнозы — бесплатно</a>';
function cdStr(m){const s=left(m.t);if(s<=0)return '00:00';const h=Math.floor(s/3600),mi=Math.floor(s%3600/60);return String(h).padStart(2,'0')+':'+String(mi).padStart(2,'0')}
function inStr(m){const s=left(m.t),mi=Math.floor(s/60);return mi<60?`${mi} мин`:`${Math.floor(mi/60)} ч ${String(mi%60).padStart(2,'0')} мин`}
const heading=(h,cls='')=>`<p class="ht ${cls}" role="heading" aria-level="1"><span>${esc(h[0])}</span> <i>${esc(h[1])}</i></p>`;
const link=(cls,inner)=>`<a class="${cls}" href="#matches">${inner}</a>`;
const noData='<p class="nod">Матчи появятся после обновления данных.</p>';

/* ── 1. Игрок ── */
const stripIn=m=>{const t=m.top;return `<a class="st-in" href="#matches">
   <span class="st-when">${LGP(m.lg)}<time class="num">${esc(when(m))}</time></span>
   <span class="st-teams">${E(m.hc)}<b>${esc(m.hn)}</b><s>—</s><b>${esc(m.an)}</b>${E(m.ac)}</span>
   ${t?`<span class="st-bet"><b>${esc(t.word)}</b><span class="hpm">${bar(t.p)}<em class="num">${pct(t.p)} %</em></span></span><span class="st-k num">${f2(t.k)}</span>`:'<span class="st-bet"><b>Расчёта пока нет</b></span>'}</a>`};
function v1(M,S){
 const pic=S==='football'?'../proto/home/players/football.webp':'../proto/home/players/hockey.webp';
 const feat=M.byConf.filter(m=>m.top).slice(0,4);
 return `<div class="stage">
  <div class="txt">${heading(M.h)}<div class="hcta">${BTN}</div></div>
  <div class="hpl"><i class="disc" aria-hidden="true"></i><img class="plr" src="${pic}" alt="" draggable="false"></div></div>
  <div class="strip" id="v1s">${feat.length?stripIn(feat[0]):noData}${feat.length>1?`<div class="hdots" role="group" aria-label="Другие матчи">${feat.map((m,i)=>`<button type="button" aria-pressed="${i===0}" aria-label="${esc(m.hn)} — ${esc(m.an)}"></button>`).join('')}</div>`:''}</div>
  ${S==='football'?'<p class="hcr">Фото: Kylian Mbappé — Bryan Berlin, CC BY-SA 4.0, Wikimedia Commons</p>':''}`;
}
function v1init(root,M){
 const feat=M.byConf.filter(m=>m.top).slice(0,4),box=root.querySelector('#v1s');if(feat.length<2)return;
 box.querySelector('.hdots').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
  const i=[...b.parentNode.children].indexOf(b),t=document.createElement('div');t.innerHTML=stripIn(feat[i]);box.querySelector('.st-in').replaceWith(t.firstChild);
  [...b.parentNode.children].forEach((x,j)=>x.setAttribute('aria-pressed',j===i))});
}

/* ── 2. Бенто ── */
function v2(M,S){
 const t=M.top,nx=M.next;
 const lgTiles=S==='football'
  ?`<div class="bt lgs"><ul>${M.leagues.map(([k,n])=>`<li><a href="league.html?lg=${esc(k)}" title="${esc(n)}" aria-label="${esc(n)}">${LGP(k)}</a></li>`).join('')}</ul></div>`
  :M.leagues.map(([k,n])=>`<a class="bt lg ${k}" href="league.html?lg=${k}">${LGP(k)}<b>${esc(n)}</b><span class="num">${M.day.filter(m=>m.lg===k).length}</span></a>`).join('');
 return `<div class="bento">
  <div class="bt ttl">${heading(M.h)}<div class="hcta">${BTN}</div></div>
  <a class="bt big" href="#matches">${t?`<div class="bh">${LGP(t.lg)}<time class="num">${esc(when(t))}</time></div>
   <div class="bmt">${E(t.hc,'xl')}<s>—</s>${E(t.ac,'xl')}</div>
   <div class="bn"><b>${esc(t.hn)}</b><b>${esc(t.an)}</b></div>
   <div class="bb"><b>${esc(t.top.word)}</b><span class="hpm">${bar(t.top.p)}<em class="num">${pct(t.top.p)} %</em></span><span class="hk num">${f2(t.top.k)}</span></div>`:noData}</a>
  <div class="bt num1"><b class="num">${M.total}</b><span>${plural(M.total,'матч','матча','матчей')} ${M.nowDay?'сегодня':'в ближайший день'}</span></div>
  ${lgTiles}
  <div class="bt cdt">${nx?`<span>Следующий матч через</span><b class="num" data-cd="${esc(nx.t)}">${cdStr(nx)}</b>`:'<span>Ближайших матчей пока нет</span>'}</div>
 </div>`;
}

/* ── 3. Лента ── */
function v3(M,S){
 const card=(m,big)=>{const t=m.top;return `<a class="mc${big?' big':''}" href="#matches">
   <span class="mh">${LGP(m.lg)}<time class="num">${esc(when(m))}</time></span>
   <span class="mtm">${E(m.hc)}<b>${esc(m.hn)}</b></span><span class="mtm">${E(m.ac)}<b>${esc(m.an)}</b></span>
   ${t?`<span class="mb"><b>${esc(t.word)}</b><span class="hpm">${bar(t.p)}<em class="num">${pct(t.p)} %</em></span><span class="hk num">${f2(t.k)}</span></span>`:'<span class="mb"><b>Расчёта пока нет</b></span>'}</a>`};
 const arrows='<span class="ar"><button type="button" data-d="-1" aria-label="Назад"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3L5 8l5 5"/></svg></button><button type="button" data-d="1" aria-label="Вперёд"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 3l5 5-5 5"/></svg></button></span>';
 const ord=M.top?[M.top,...M.rest]:M.rest;
 return `<div class="head">${heading(M.h)}<div class="hcta">${BTN}${arrows}</div></div>
  <div class="lane" id="v3l" tabindex="0" aria-label="Матчи дня">${ord.length?ord.map((m,i)=>card(m,i===0&&!!m.top)).join(''):noData}</div>`;
}
function v3init(root){
 const L=root.querySelector('#v3l'),btns=root.querySelectorAll('.ar button');
 btns.forEach(b=>b.addEventListener('click',()=>{const c=L.querySelector('.mc:not(.big)')||L.firstElementChild;L.scrollBy({left:(+b.dataset.d)*(c?c.offsetWidth+14:300)*2,behavior:RM?'auto':'smooth'})}));
 let down=false,x0=0,s0=0,moved=0;
 L.addEventListener('pointerdown',e=>{if(e.pointerType!=='mouse'||e.button)return;down=true;x0=e.clientX;s0=L.scrollLeft;moved=0});
 addEventListener('pointermove',e=>{if(!down)return;const dx=e.clientX-x0;moved=Math.max(moved,Math.abs(dx));if(moved>5)L.classList.add('drag');L.scrollLeft=s0-dx});
 addEventListener('pointerup',()=>{if(!down)return;down=false;L.classList.remove('drag')});
 L.addEventListener('click',e=>{if(moved>5){e.preventDefault();moved=0}},true);
 L.addEventListener('dragstart',e=>e.preventDefault());
 const upd=()=>{const max=L.scrollWidth-L.clientWidth-2;btns[0]&&(btns[0].disabled=L.scrollLeft<2);btns[1]&&(btns[1].disabled=L.scrollLeft>=max)};
 L.addEventListener('scroll',upd,{passive:true});upd();
}

/* ── 4. Колода ── */
const LGC={khl:['#17408f','#0a1632'],nhl:['#2a3340','#0b0e14'],epl:['#4a2582','#150a2a'],laliga:['#8a2433','#2a0a10'],seriea:['#14508f','#07182c'],bundesliga:['#8f2a2a','#2a0c0c'],ligue1:['#1f4a8f','#0a1830'],rpl:['#1f6a4f','#08251c'],ucl:['#123a85','#060f2a'],uel:['#a0551a','#2a1406']};
function v4(M,S){
 const deck=(M.top?[M.top,...M.rest]:M.rest).slice(0,5);
 const face=m=>{const c=LGC[m.lg]||LGC.khl,t=m.top;
  return `<div class="kc" style="--c1:${c[0]};--c2:${c[1]}"><div class="ktl"><div class="inn">
   <div class="fc fr"><span class="kh">${LGP(m.lg)}<time class="num">${esc(when(m))}</time></span>
    <span class="kp">${E(m.hc,'xl')}<b>${esc(m.hn)}</b></span><s>—</s><span class="kp">${E(m.ac,'xl')}<b>${esc(m.an)}</b></span>
    <button type="button" class="kf" aria-label="Перевернуть карточку"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 8a6 6 0 0 1 10.5-3M16 12a6 6 0 0 1-10.5 3M14.5 2v3h-3M5.5 18v-3h3"/></svg></button></div>
   <div class="fc bk">${m.pr?`<span class="kh"><b>${esc(m.hn)} — ${esc(m.an)}</b></span><div class="pr3">${[['П1',0],['Х',1],['П2',2]].map(([l,i])=>`<span class="${t&&t.i===i?'hit':''}"><i style="--h:${pct(m.pr[i])}%"></i><b class="num">${pct(m.pr[i])}</b><em>${l}</em><small class="num">${m.k?f2(m.k[i]):'—'}</small></span>`).join('')}</div>
    ${t?`<p class="kw"><b>${esc(t.word)}</b><span class="num">${f2(t.k)}</span></p>`:''}`:'<span class="kh"><b>Расчёта пока нет</b></span>'}
    <button type="button" class="kf" aria-label="Перевернуть карточку"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 8a6 6 0 0 1 10.5-3M16 12a6 6 0 0 1-10.5 3M14.5 2v3h-3M5.5 18v-3h3"/></svg></button></div>
  </div></div></div>`};
 const facts=`<ul class="facts"><li><b class="num">${M.total}</b><span>${plural(M.total,'матч','матча','матчей')} ${M.nowDay?'сегодня':'впереди'}</span></li><li><b class="num">${M.nModel}</b><span>с расчётом модели</span></li><li><b class="num">${M.lgs.length||M.leagues.length}</b><span>${plural(M.lgs.length||M.leagues.length,'лига','лиги','лиг')}</span></li></ul>`;
 return `<div class="lft">${heading(M.h)}<div class="hcta">${BTN}</div>${facts}</div>
  <div class="fan" id="v4f">${deck.length?deck.map(face).join(''):noData}</div>`;
}
function v4init(root){
 const fan=root.querySelector('#v4f'),cs=[...fan.querySelectorAll('.kc')];if(!cs.length)return;
 let order=cs.slice();
 const place=()=>order.forEach((c,i)=>{c.dataset.p=i;c.style.zIndex=10-i;c.classList.toggle('is-top',i===0);if(i)c.classList.remove('flipped')});
 place();
 cs.forEach(c=>c.addEventListener('click',e=>{
  if(c.dataset.p==='0'){c.classList.toggle('flipped');return}
  order=[c,...order.filter(x=>x!==c)];place()}));
 /* наклон верхней карточки за курсором: только мышь, ±10°, без свечения */
 if(!HOVER||RM)return;
 let tx=0,ty=0,cx=0,cy=0,raf=0;
 const set=()=>{const t=order[0].querySelector('.ktl');cx+=(tx-cx)*.14;cy+=(ty-cy)*.14;t.style.transform=`rotateX(${cx.toFixed(2)}deg) rotateY(${cy.toFixed(2)}deg)`;
  raf=(Math.abs(tx-cx)>.02||Math.abs(ty-cy)>.02)?requestAnimationFrame(set):0};
 root.addEventListener('pointermove',e=>{const r=order[0].getBoundingClientRect();
  const px=Math.max(-1,Math.min(1,(e.clientX-(r.left+r.width/2))/(r.width*1.4))),py=Math.max(-1,Math.min(1,(e.clientY-(r.top+r.height/2))/(r.height*1.4)));
  ty=px*10;tx=-py*10;if(!raf)raf=requestAnimationFrame(set)});
 root.addEventListener('pointerleave',()=>{tx=0;ty=0;if(!raf)raf=requestAnimationFrame(set)});
}

/* ── 5. Центр ── */
function v5(M,S){
 const t=M.top,nx=M.next;
 const chips=(M.lgs.length?M.lgs:M.leagues).map(([k,n])=>`<li><a href="league.html?lg=${esc(k)}">${LGP(k)}${esc(n)}</a></li>`).join('');
 return `${heading(M.h)}
  <div class="hrow"><ul class="hchips">${chips}</ul>${nx?`<p class="nx">Ближайший матч через <b class="num" data-in="${esc(nx.t)}">${inStr(nx)}</b></p>`:''}</div>
  ${t?`<a class="mc" href="#matches"><span class="c3"><span class="tt">${E(t.hc,'xl')}<b>${esc(t.hn)}</b></span>
   <span class="mid">${LGP(t.lg)}<time class="num">${esc(when(t))}</time></span><span class="tt">${E(t.ac,'xl')}<b>${esc(t.an)}</b></span></span>
   <span class="mb"><b>${esc(t.top.word)}</b><span class="hpm">${bar(t.top.p)}<em class="num">${pct(t.top.p)} %</em></span><span class="hk num">${f2(t.top.k)}</span></span></a>`:noData}`;
}

/* ── сборка ── */
function build(){
 const hero=document.querySelector(HOME?'section.hm':'section.hero');if(!hero||!N)return;
 const S=HOME?'home':document.body.dataset.field==='football'?'football':'hockey';
 const old=hero.querySelector('h1');
 const lines=old&&!HOME?[...old.querySelectorAll('.ln')].map(x=>x.textContent.trim()):[];
 let M;try{M=model(S)}catch(e){console.warn('hero2: нет данных',e);M={day:[],rest:[],byConf:[],top:null,leagues:[],lgs:[],total:0,nModel:0,next:null,list:[]}}
 M.h=S==='home'?['Прогнозы','по расчёту']:lines.length===2?lines:(S==='football'?['Футбол:','топ-лиги и РПЛ']:['Хоккей:','КХЛ и НХЛ']);
 if(N>=6){if(N!==9)M.h=M.h.map(x=>x.replace(/:$/,''));window.JVH2.mount(N,hero,M,S);return}
 const root=document.createElement('div');root.className=`h2 h2-v${N}`;root.dataset.sp=S;
 root.innerHTML=[null,v1,v2,v3,v4,v5][N](M,S);
 hero.append(root);
 ({1:v1init,3:v3init,4:v4init}[N]||(()=>{}))(root,M);
 /* отсчёт: обновляем раз в 20 с, цифры меняются без анимации */
 const tick=()=>{root.querySelectorAll('[data-cd]').forEach(el=>{const v=cdStr({t:el.dataset.cd});if(el.textContent!==v)el.textContent=v});
  root.querySelectorAll('[data-in]').forEach(el=>{const v=inStr({t:el.dataset.in});if(el.textContent!==v)el.textContent=v})};
 if(root.querySelector('[data-cd],[data-in]'))setInterval(()=>{if(!document.hidden)tick()},20000);
}
/* варианты 6 и 7 лежат в отдельных файлах: общий код — hero2b.js, лента WebGL — ribbon.js (только для 7) */
if(N>=6){
 window.JVH2={esc,f2,pct,plural,left,mskDay,MON,LGN,LGP,BTN:'<a class="btn btn-tg" href="https://t.me/jarvibet" target="_blank" rel="noopener">Получать прогнозы — бесплатно</a>',cdStr,BASE,RM,HOME};
 const add=(t,a)=>{const e=document.createElement(t);Object.assign(e,a);document.head.append(e);return e};
 add('link',{rel:'stylesheet',href:BASE+(N===8?'hero8.css':N===9?'hero9.css':'hero2b.css')});
 if(N===7)add('link',{rel:'stylesheet',href:'https://fonts.googleapis.com/css2?family=Literata:ital,opsz,wght@1,7..72,300;1,7..72,400&display=swap'});
}
document.addEventListener('DOMContentLoaded',()=>{
 const go=()=>{try{build()}catch(e){console.warn('hero2:',e)}switcher()};
 if(N>=6){const s=document.createElement('script');s.src=BASE+(N===9?'hero9.js':'hero2b.js');s.onload=go;s.onerror=switcher;document.head.append(s)}else go();
});
})();
