/* JARVIS v3a — страница «Футбол»: прогноз дня, ближайшие матчи, лиги и клубы. Данные — JV_FOOT (ESPN + расчёт модели по голам сезона). */
(()=>{
'use strict';
const {D,esc,fx,pc,plural,T,nm,CI,LGI,LGP,teamHref,day,dd,played,rOf,RES,RESF,gamesOf,stats,h2h,dots}=JVF;
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const $=id=>document.getElementById(id);
const LGK=Object.keys(D.leagues);
const chev='<svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 5l5 5 5-5"/></svg>';
const k2=v=>v==null?'—':fx(v,2);
const mskDay=ms=>new Date(ms+3*3600e3).toISOString().slice(0,10);

/* ── цифры в первом экране ── */
{const gp=Object.values(T).reduce((a,t)=>a+t.games.filter(played).length,0)/2;
 $('fN').textContent=Object.keys(T).length;$('fG').textContent=Math.round(gp);$('fL').textContent=LGK.length;
 $('chips').innerHTML=LGK.map(k=>`<li><a href="#lg-${esc(k)}">${LGP(k)}${esc(D.leagues[k].name)}</a></li>`).join('')}

/* ── ближайшие матчи: с этого момента, первые 4 игровых дня ── */
const now=Date.now();
const FUT=D.up.filter(m=>JV.left(m.t)>-2*3600).sort((a,b)=>a.t<b.t?-1:1);
const days=[...new Set(FUT.map(m=>m.t.slice(0,10)))].slice(0,4);
const UP=FUT.filter(m=>days.includes(m.t.slice(0,10)));
const today=mskDay(now),isToday=UP.some(m=>m.t.slice(0,10)===today);
{const f=UP[0];
 if(!UP.length){$('mh').textContent='Ближайшие матчи';$('mpt').textContent='Ближайшие матчи';$('mlead').textContent='Расписание обновится в начале следующего тура.'}
 else if(!isToday){const d=day(f.t);$('mh').textContent='Ближайшие матчи';$('mpt').textContent='Ближайшие матчи';
  $('mlead').textContent=`Сегодня матчей лиг нет, ближайший тур — с ${d.d} ${d.mon}. Нажми на строку: форма, последние матчи и личные встречи сезона.`}
 if(f)$('mpc').textContent=f.t.slice(11);$('lpc').textContent=f?f.t.slice(11):''}

/* бегущая строка */
{const L=UP.slice(0,10);
 if(L.length)JV.ticker($('ticker'),L.map(m=>{const d=day(m.t),tag=m.t.slice(0,10)===today?'':`<span class="tm2">${d.d} ${d.mon}</span>`;
  return `${tag}<time>${esc(m.t.slice(11))}</time>${LGP(m.lg)}${CI(m.h,'tc')}${esc(nm(m.h))} — ${esc(nm(m.a))}${CI(m.a,'tc')}<span class="kq">${m.k?m.k.map(v=>fx(v,2)).join(' · '):pcs(m.pr)}</span>`}));
 else $('ticker').hidden=true}
function pcs(p){return p.map(v=>Math.round(v*100)).join(' · ')+' %'}

/* ── карточка «Прогноз дня»: сильнейший вывод модели по рынкам 1Х2 и тотал 2,5 ── */
function best(m){const A=nm(m.h),B=nm(m.a),c=[{p:m.pr[0],t:`${A} — победа`,s:'П1',k:m.k&&m.k[0]},{p:m.pr[2],t:`${B} — победа`,s:'П2',k:m.k&&m.k[2]},
  {p:m.ov,t:'Тотал больше 2,5',s:'ТБ 2,5',k:m.tt&&m.tt[0]===2.5?m.tt[1]:null},{p:1-m.ov,t:'Тотал меньше 2,5',s:'ТМ 2,5',k:m.tt&&m.tt[0]===2.5?m.tt[2]:null}];
 const ck=c.filter(x=>x.k);return (ck.length?ck:c).sort((a,b)=>b.p-a.p)[0]}
const pool=UP.filter(m=>JV.left(m.t)>0);
const withK=pool.filter(m=>m.k);
const picks=(withK.length>=3?withK:pool).map(m=>({m,b:best(m)})).sort((a,b)=>b.b.p-a.b.p).slice(0,4).sort((a,b)=>a.m.t<b.m.t?-1:1);
const mcard=$('mcard'),cdv=$('cdv'),boardEl=$('board'),pager=$('pager');
const lvl=p=>p>=.6?'hi':p>=.5?'mid':'lo';
const tm=(s,cls)=>{const n=nm(s);return `<div class="tm${n.length>10?' long':''}">${CI(s)}<small>${cls}</small><span>${esc(n)}</span></div>`};
const card=({m,b})=>{const A=T[m.h],B=T[m.a];
 return `<div class="face">${tm(m.h,'хозяева')}<div class="vs"><span aria-hidden="true">—</span><time>${esc(m.t.slice(11))}</time></div>${tm(m.a,'гости')}</div>
 <div class="bet lv-${lvl(b.p)}"><span class="bl">Прогноз модели</span><strong>${esc(b.t)}</strong><span class="k num" aria-label="${b.k?'коэффициент':'линии пока нет'}">${b.k?fx(b.k,2):'—'}</span>
  <span class="pm"><em><i style="--w:${Math.round(b.p*100)}%"></i></em><b class="num">${Math.round(b.p*100)} % по модели</b></span></div>
 <div class="mk3"><span>1Х2<b class="num">${m.pr.map(v=>Math.round(v*100)).join(' · ')}</b><em>П1 · Х · П2, %</em></span><span>Тотал 2,5<b class="num">${Math.round(m.ov*100)} %</b><em>больше</em></span><span>Обе забьют<b class="num">${Math.round(m.bt*100)} %</b><em>да</em></span></div>
 <p class="why"><b>Почему:</b> ожидаемые голы ${fx(m.xg[0],1)} : ${fx(m.xg[1],1)}. В таблице: ${esc(A.n)} — ${A.place}, ${esc(B.n)} — ${B.place}.</p>`};
cdv.innerHTML=['h','m','s'].map((u,i)=>`<span class="cu" data-u="${u}"><b></b><small>${['ч','мин','с'][i]}</small></span>`).join('');
const cu=[...cdv.querySelectorAll('.cu b')],cdWord=document.createElement('b');cdWord.className='cdw';cdv.appendChild(cdWord);
function cdSet(sec){const on=sec>0;cdv.classList.toggle('over',!on);
 if(!on){cdWord.textContent=sec>-7200?'идёт':'завершён';return}
 const v=[Math.floor(sec/3600),Math.floor(sec%3600/60),sec%60].map(n=>String(n).padStart(2,'0'));
 v.forEach((x,i)=>{const el=cu[i];if(el.textContent===x)return;const first=!el.textContent;el.textContent=x;
  if(!first&&!RM&&el.animate)el.animate([{opacity:0,transform:'translateY(-35%)'},{opacity:1,transform:'none'}],{duration:260,easing:'cubic-bezier(.23,1,.32,1)'})})}
function swap(p,dir){
 if(RM||!mcard.animate||!mcard.innerHTML){mcard.innerHTML=card(p);return}
 const out=mcard.animate([{opacity:1,transform:'none'},{opacity:0,transform:`translateX(${-18*dir}px)`}],{duration:180,easing:'cubic-bezier(.55,0,1,.45)',fill:'forwards'});
 out.finished.then(()=>{mcard.innerHTML=card(p);out.cancel();
  mcard.animate([{opacity:0,transform:`translateX(${22*dir}px)`},{opacity:1,transform:'none'}],{duration:420,easing:'cubic-bezier(.23,1,.32,1)'})}).catch(()=>{mcard.innerHTML=card(p)})}
let cur=0,timer=0,shown=false;
if(!picks.length){$('mstage').innerHTML='<p class="note" style="padding:24px 8px">Ближайшие матчи появятся в начале тура.</p>';cdv.parentElement.hidden=true;pager.hidden=true;$('bdate').textContent=''}
else{
 pager.innerHTML=picks.map(({m},i)=>`<button type="button" aria-pressed="${i===0}" aria-label="${esc(nm(m.h))} — ${esc(nm(m.a))}"></button>`).join('');
 const show=i=>{const dir=i>=cur?1:-1;cur=i;const p=picks[i],m=p.m;
  $('blg').innerHTML=LGP(m.lg);$('bmeta').textContent=`${D.leagues[m.lg].name} · ${m.t.slice(11)} МСК`;
  $('bhead').textContent=i===0?`Прогноз дня · 1 из ${picks.length}`:`Прогноз ${i+1} из ${picks.length}`;
  pager.querySelectorAll('button').forEach((b,j)=>b.setAttribute('aria-pressed',j===i));
  swap(p,shown?dir:1);shown=true;cdSet(JV.left(m.t));const d=day(m.t);$('bdate').textContent=`${d.d} ${d.mon}`};
 {let sx=null,sy=0;const z=$('mstage');
  z.addEventListener('touchstart',e=>{sx=e.touches[0].clientX;sy=e.touches[0].clientY},{passive:true});
  z.addEventListener('touchend',e=>{if(sx===null)return;const t=e.changedTouches[0],dx=t.clientX-sx,dy=t.clientY-sy;sx=null;
   if(Math.abs(dx)>40&&Math.abs(dx)>Math.abs(dy)){show((cur+(dx<0?1:picks.length-1))%picks.length);restart()}},{passive:true})}
 pager.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;show([...pager.children].indexOf(b));restart()});
 function restart(){clearInterval(timer);if(!RM&&picks.length>1)timer=setInterval(()=>show((cur+1)%picks.length),9000)}
 boardEl.addEventListener('mouseenter',()=>clearInterval(timer));boardEl.addEventListener('mouseleave',restart);
 const bio=new IntersectionObserver(es=>{if(es[0].isIntersecting){show(0);restart();bio.disconnect()}});bio.observe(boardEl);
 window.__cdPick=()=>shown&&cdSet(JV.left(picks[cur].m.t))}

/* ── матчи: котировки (линия) и вероятности модели; по нажатию — форма, последние матчи, личные встречи ── */
const ltabs=$('ltabs'),list=$('mlist'),moreB=$('moreM');
const cntL=l=>UP.filter(m=>m.lg===l).length;
ltabs.innerHTML=`<button class="tab" role="tab" aria-selected="true" data-l="all">Все <span class="c">${UP.length}</span></button>`+
 LGK.filter(k=>cntL(k)).map(k=>`<button class="tab" role="tab" aria-selected="false" data-l="${esc(k)}">${LGP(k)}${esc(D.leagues[k].name)} <span class="c">${cntL(k)}</span></button>`).join('');
const LIM=14;let curTab='all',shownN=LIM,sel=[];
function det(m){return m.det||(m.det={A:{s:m.h,g:gamesOf(m.h),st:stats(m.h)},B:{s:m.a,g:gamesOf(m.a),st:stats(m.a)},h:h2h(m.h,m.a)})}
function back(m){const {A,B,h}=det(m),nA=nm(m.h),nB=nm(m.a);
 const last=t=>`<div class="l3"><h5>${CI(t.s)}${esc(nm(t.s))}</h5><ul>${t.g.slice(0,3).map(g=>{const r=rOf(g);return `<li><b class="rs ${r}" title="${RESF[r]}">${RES[r]}</b><span class="op">${CI(g.o)}${esc(nm(g.o))}</span><span class="sc num">${g.gf}:${g.ga}</span><span class="d">${g.h?'дома':'в гостях'} · ${dd(g.d)}</span></li>`}).join('')||'<li class="none">Нет данных</li>'}</ul></div>`;
 const form=t=>`<div class="fm"><span>${CI(t.s)}${esc(nm(t.s))}</span>${dots(t.s)}</div>`;
 const row=(lab,a,b)=>`<tr><td>${lab}</td><td class="num">${a}</td><td class="num">${b}</td></tr>`;
 const f1=v=>fx(v,1),p0=v=>v==null?'—':Math.round(v*100)+' %';
 const TA=T[m.h],TB=T[m.a];
 const wA=h.filter(g=>(g.h===m.h?g.hs>g.as:g.as>g.hs)).length,wB=h.filter(g=>(g.h===m.h?g.as>g.hs:g.hs>g.as)).length,dr=h.length-wA-wB;
 const h2hHTML=h.length?`<p class="h2t"><span>${CI(m.h)}${esc(nA)}</span><b class="num">${wA} — ${dr} — ${wB}</b><span>${esc(nB)}${CI(m.a)}</span></p><ul class="h2l">${h.slice(0,6).map(g=>{const home=g.h,away=g.h===m.h?m.a:m.h;
   return `<li><span class="d">${dd(g.d)}<small class="smp">${esc(g.s)}</small></span><span class="pp">${CI(home)}<span class="${g.hs>g.as?'wn':''}">${esc(nm(home))}</span></span><span class="sc num"><b class="${g.hs>g.as?'wn':''}">${g.hs}</b>:<b class="${g.as>g.hs?'wn':''}">${g.as}</b></span><span class="pp aw">${CI(away)}<span class="${g.as>g.hs?'wn':''}">${esc(nm(away))}</span></span></li>`}).join('')}</ul>`
  :`<p class="none">Эти клубы ещё не встречались в лиге в сезонах 2025/26 и 2026/27.</p>`;
 return `<div class="xd">
  <section class="xb x-last"><h4>Последние 3 матча</h4><div class="two">${last(A)}${last(B)}</div></section>
  <section class="xb x-form"><h4>Форма <span class="note">последние 5: слева раньше, справа последняя; в кружке — соперник</span></h4>${form(A)}${form(B)}</section>
  <section class="xb x-stat"><h4>Статистика команды <span class="note">сезон 2026/27</span></h4><table class="st"><thead><tr><th></th><th>${CI(m.h)}<span>${esc(nA)}</span></th><th>${CI(m.a)}<span>${esc(nB)}</span></th></tr></thead><tbody>
   ${row('Место в таблице',TA.place,TB.place)}${row('Очки',TA.pts,TB.pts)}${row('Победы — ничьи — поражения',`${TA.w} — ${TA.d} — ${TA.l}`,`${TB.w} — ${TB.d} — ${TB.l}`)}
   ${row('Мячи за игру',f1(A.st.gf),f1(B.st.gf))}${row('Пропущено за игру',f1(A.st.ga),f1(B.st.ga))}${row('Удары за игру',f1(A.st.sh),f1(B.st.sh))}${row('Угловые за игру',f1(A.st.cor),f1(B.st.cor))}
   ${row('Матчей с тоталом больше 2,5',p0(A.st.ov),p0(B.st.ov))}${row('Матчей, где забили обе',p0(A.st.bt),p0(B.st.bt))}</tbody></table></section>
  <section class="xb x-h2h"><h4>Личные встречи <span class="note">лига, два сезона</span></h4>${h2hHTML}</section>
  <p class="note xn">Матчи и статистика — ESPN, сезон 2026/27. Страница клуба — по ссылке с эмблемы в разделе «Лиги и клубы».</p></div>`}
function rowHTML(m){const L=D.leagues[m.lg],mx=Math.max(...m.pr),d=day(m.t);
 const q=['П1','Х','П2'].map((k,j)=>`<span class="qc${m.pr[j]===mx?' fav':''}"><small>${k}</small><b class="num">${m.k?k2(m.k[j]):'—'}</b><em class="num">${pc(m.pr[j])}</em></span>`).join('');
 const tot=m.tt&&m.tt[0]===2.5?`Тотал 2,5 <span>Б <b class="num">${k2(m.tt[1])}</b></span><span>М <b class="num">${k2(m.tt[2])}</b></span>`:`Тотал 2,5 <span>Б <b class="num">${pc(m.ov)}</b></span><span>М <b class="num">${pc(1-m.ov)}</b></span>`;
 return `<li class="match ${esc(m.lg)}"><button class="mhead" type="button" aria-expanded="false">
  <div class="mt"><time>${esc(m.t.slice(11))}</time><span class="cd" data-t="${esc(m.t)}"></span></div>
  <div><div class="lgline">${LGP(m.lg)}${esc(L.name)}</div><div class="teams"><div class="team">${CI(m.h)}<span>${esc(nm(m.h))}</span></div><div class="team">${CI(m.a)}<span>${esc(nm(m.a))}</span></div></div></div>
  <div class="quotes"><div class="q3">${q}</div><div class="qt">${tot}</div></div>
  <span class="chev">${chev}</span></button><div class="mbody"><div></div></div></li>`}
function render(l,more){if(!more){curTab=l;shownN=LIM}
 sel=(l==='all'?UP:UP.filter(m=>m.lg===l));
 ltabs.querySelectorAll('.tab').forEach(t=>t.setAttribute('aria-selected',t.dataset.l===l));
 let html='',prev='';const vis=sel.slice(0,shownN);
 vis.forEach(m=>{const dk=m.t.slice(0,10);if(dk!==prev){prev=dk;const d=day(m.t);html+=`<li class="dayh" aria-hidden="true">${d.wd}, ${d.d} ${d.mon}${dk===today?' · сегодня':''}</li>`}html+=rowHTML(m)});
 list.innerHTML=html||'<li class="note" style="padding:18px 4px">В этой лиге ближайших матчей пока нет.</li>';
 list.querySelectorAll('.match').forEach((li,i)=>{const b=li.querySelector('.mhead'),body=li.querySelector('.mbody>div');
  b.addEventListener('click',()=>{if(!body.innerHTML)body.innerHTML=back(vis[i]);requestAnimationFrame(()=>{const o=li.classList.toggle('open');b.setAttribute('aria-expanded',o)})})});
 if(!RM&&!more)list.querySelectorAll('.match').forEach((li,i)=>li.animate([{opacity:0,transform:'translateY(14px)'},{opacity:1,transform:'none'}],{duration:500,delay:Math.min(i,10)*55,easing:'cubic-bezier(.23,1,.32,1)',fill:'backwards'}));
 requestAnimationFrame(()=>list.querySelectorAll('.match').forEach(li=>li.classList.add('in')));
 moreB.hidden=sel.length<=shownN;moreB.textContent=`Показать ещё ${Math.min(LIM,sel.length-shownN)}`;tick()}
function tick(){document.querySelectorAll('.cd[data-t]').forEach(e=>e.textContent=JV.inMin(JV.left(e.dataset.t)));if(window.__cdPick)window.__cdPick()}
ltabs.addEventListener('click',e=>{const t=e.target.closest('.tab');if(t)render(t.dataset.l)});
moreB.addEventListener('click',()=>{shownN+=LIM;render(curTab,true)});
render('all');setInterval(tick,1000);

/* ── лиги и клубы: плашки-переключатели, эмблемы клубов лиги целиком, таблица ── */
const flags=$('flags'),wallEl=$('wall'),wallH=$('wallh');let curLg='';
flags.innerHTML=LGK.map(k=>{const l=D.leagues[k],n=cntL(k);
 return `<button type="button" role="tab" class="lgtab ${esc(k)}" id="lg-${esc(k)}" data-lg="${esc(k)}" aria-selected="false" aria-controls="wallbox"><img class="lgbg" src="${LGI(k)}" alt=""><span class="lgtx"><span class="lgn">${esc(l.name)}</span><span class="lgf">${esc(l.full)}</span><span class="nt">${l.ids.length} ${plural(l.ids.length,'клуб','клуба','клубов')}</span><span class="cnt">${n?`${n} ${plural(n,'матч','матча','матчей')} в ближайший тур`:'туров нет в расписании'}</span></span></button>`}).join('');
const ZONE=lg=>({epl:[[1,4,'z1','Лига чемпионов'],[5,5,'z2','Лига Европы'],[18,20,'z4','Вылет']],laliga:[[1,4,'z1','Лига чемпионов'],[5,6,'z2','Лига Европы'],[18,20,'z4','Вылет']],
 seriea:[[1,4,'z1','Лига чемпионов'],[5,6,'z2','Лига Европы'],[18,20,'z4','Вылет']],bundesliga:[[1,4,'z1','Лига чемпионов'],[5,6,'z2','Лига Европы'],[16,16,'z3','Стыковые матчи'],[17,18,'z4','Вылет']],
 ligue1:[[1,3,'z1','Лига чемпионов'],[4,5,'z2','Лига Европы'],[16,16,'z3','Стыковые матчи'],[17,18,'z4','Вылет']],rpl:[[1,3,'z1','Еврокубки по рейтингу'],[15,16,'z4','Вылет']]})[lg]||[];
function pickLg(lg,anim=true){if(lg===curLg||!D.leagues[lg])return;curLg=lg;
 flags.querySelectorAll('.lgtab').forEach(b=>b.setAttribute('aria-selected',b.dataset.lg===lg));
 const L=D.leagues[lg],rows=L.ids.map(s=>T[s]).sort((a,b)=>a.place-b.place),z=ZONE(lg);
 const put=()=>{wallH.innerHTML=`${LGP(lg)}<span>${esc(L.name)}</span><span>${rows.length} ${plural(rows.length,'клуб','клуба','клубов')}</span>`;
  wallEl.dataset.lg=lg;wallEl.innerHTML=rows.map((t,i)=>`<a class="crest" style="--i:${i}" href="${teamHref(t.id)}" title="${esc(t.n)} · ${esc(L.name)}: страница клуба">${CI(t.id)}<span>${esc(t.n)}</span></a>`).join('');
  $('ltab').innerHTML=`<thead><tr><th>#</th><th>Клуб</th><th>И</th><th class="hm">В</th><th class="hm">Н</th><th class="hm">П</th><th>Мячи</th><th>О</th></tr></thead><tbody>${rows.map(t=>{const zc=(z.find(x=>t.place>=x[0]&&t.place<=x[1])||[])[2]||'';
   return `<tr class="${zc}"><td>${t.place}</td><td><a href="${teamHref(t.id)}">${CI(t.id)}<span>${esc(t.n)}</span></a></td><td>${t.gp}</td><td class="hm">${t.w}</td><td class="hm">${t.d}</td><td class="hm">${t.l}</td><td>${t.gf}:${t.ga}</td><td>${t.pts}</td></tr>`}).join('')}</tbody>`;
  const seen=[];z.forEach(x=>{if(!seen.find(s=>s[3]===x[3]))seen.push(x)});
  $('lkey').innerHTML=seen.map(x=>`<li><i style="background:${{z1:'#0d7a48',z2:'#1c63c4',z3:'#d9822b',z4:'#c4303b'}[x[2]]}"></i>${esc(x[3])}</li>`).join('')+`<li>И — игры, О — очки; по данным ESPN на ${esc((D.built||'').slice(8,10))}.${esc((D.built||'').slice(5,7))}</li>`;
  if(anim&&!RM)wallEl.querySelectorAll('.crest').forEach((c,i)=>c.animate([{opacity:0,transform:'translateY(12px)'},{opacity:1,transform:'none'}],{duration:420,delay:Math.min(i,32)*18,easing:'cubic-bezier(.23,1,.32,1)',fill:'backwards'}))};
 if(anim&&!RM&&wallEl.innerHTML){wallEl.animate([{opacity:1},{opacity:0,transform:'translateY(6px)'}],{duration:160,easing:'ease-in'}).finished.then(put).catch(put)}else put()}
flags.addEventListener('click',e=>{const b=e.target.closest('.lgtab');if(b)pickLg(b.dataset.lg)});
flags.addEventListener('keydown',e=>{if(!/Arrow(Left|Right)/.test(e.key))return;const t=[...flags.querySelectorAll('.lgtab')],i=t.findIndex(b=>b.dataset.lg===curLg),n=t[(i+(e.key==='ArrowRight'?1:t.length-1))%t.length];n.focus();pickLg(n.dataset.lg)});
pickLg(/^#lg-/.test(location.hash)&&D.leagues[location.hash.slice(4)]?location.hash.slice(4):LGK[0],false);
document.addEventListener('click',e=>{const a=e.target.closest('a[href^="#lg-"]');if(!a)return;pickLg(a.getAttribute('href').slice(4))});
})();
