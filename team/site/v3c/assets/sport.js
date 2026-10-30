/* JARVIS v3c — страницы видов спорта: собирает разделы из примерных данных страницы (__FTODAY/__FOOTBT или __TODAY/__HOCKEY). */
(()=>{
const SPORT=document.documentElement.dataset.sport,RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const $=id=>document.getElementById(id);
const esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const f1=(v,d=1)=>v.toFixed(d).replace('.',',');
const pc=v=>Math.round(v*100)+'%';
const plural=(n,a,b,c)=>{const k=n%100,j=n%10;return k>10&&k<20?c:j===1?a:j>1&&j<5?b:c};
const two=n=>String(n).padStart(2,'0');
const atMs=t=>Date.parse(t.replace(' ','T')+':00+03:00');
const LGI=id=>`../assets/lg/${id}.svg`;
const ICON={plus:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
 ok:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><circle cx="12" cy="12" r="10" stroke-width="1.6" opacity=".4"/><path d="m7.5 12.5 3 3 6-7"/></svg>',
 no:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><circle cx="12" cy="12" r="10" stroke-width="1.6" opacity=".4"/><path d="m8.5 8.5 7 7m0-7-7 7"/></svg>'};
const ringSvg=(p,cls='fg')=>`<svg viewBox="0 0 132 132" aria-hidden="true"><circle class="bg" cx="66" cy="66" r="58" pathLength="1"/><circle class="tick" cx="66" cy="66" r="50" pathLength="1"/><circle class="${cls}" cx="66" cy="66" r="58" pathLength="1" data-p="${p.toFixed(3)}"/></svg>`;
const mini=(label,p,top)=>`<div class="mini${top?' top':''}"><svg viewBox="0 0 48 48" aria-hidden="true"><circle class="bg" cx="24" cy="24" r="20" pathLength="1"/><circle class="fg" cx="24" cy="24" r="20" pathLength="1" data-p="${p.toFixed(3)}"/></svg><span class="v">${pc(p)}</span>${label}</div>`;
const form=s=>`<span class="form">${[...s].map(c=>`<i class="${c==='W'?'w':c==='D'?'d':'l'}" title="${c==='W'?'победа':c==='D'?'ничья':'поражение'}">${c==='W'?'В':c==='D'?'Н':'П'}</i>`).join('')}</span>`;

/* ── общий: табло «Прогноз дня» ── */
function board(el,m,o){const P=Math.round(m.pr*100);
 el.innerHTML=`<div class="b-top"><span class="live">Прогноз дня</span><span class="b-lg"><img src="${LGI(m.lg)}" alt="">${o.lgName} · ${m.t.slice(11)} МСК</span></div>
 <div class="b-match"><div class="tm"><img src="${o.logo(m.a)}" alt="">${esc(m.a)}</div>
  <div class="ring">${ringSvg(m.pr)}<div><b class="num" data-count="${P}" data-suf="%">${P}%</b><small>по модели</small></div></div>
  <div class="tm"><img src="${o.logo(m.b)}" alt="">${esc(m.b)}</div></div>
 <div class="b-pick"><div><span>${o.tag}</span><strong>${esc(m.p)}</strong></div><span class="k num">${m.k}</span></div>
 <div class="b-clock"><span id="cdl">${o.until}</span><b class="num" id="cd">—</b></div>
 <p class="sample">Пример данных. ${o.when}</p>`;
 el.setAttribute('data-in','');UI.observe(el.parentNode);
 const tick=()=>{const s=Math.round((atMs(m.t)-Date.now())/1000);if(s>0)$('cd').textContent=`${two(Math.floor(s/3600))}:${two(Math.floor(s%3600/60))}:${two(s%60)}`;else{$('cdl').textContent='Матч';$('cd').textContent=s>-9000?'идёт':'завершён'}
  document.querySelectorAll('.cd[data-t]').forEach(e=>{const s=Math.round((atMs(e.dataset.t)-Date.now())/1000),mm=Math.floor(s/60);e.textContent=s<=0?(s>-9000?'идёт':''):mm<60?`через ${mm} мин`:`через ${Math.floor(mm/60)} ч ${mm%60} мин`})};
 tick();setInterval(tick,1000)}

/* ── общий: вкладки и строки матчей ── */
function matches(D,L,row){const tabs=$('tabs'),list=$('mlist'),cnt=id=>D.filter(m=>m.lg===id).length;
 tabs.innerHTML=`<button class="tab" role="tab" aria-selected="true" data-l="all">Все <span class="n">${D.length}</span></button>`+
  L.filter(l=>!l.hide).map(l=>`<button class="tab" role="tab" aria-selected="false" data-l="${l.id}"><img src="${LGI(l.id)}" alt="">${l.name} <span class="n">${cnt(l.id)}</span></button>`).join('');
 const render=l=>{const sel=(l==='all'?D:D.filter(m=>m.lg===l)).slice().sort((a,b)=>a.t<b.t?-1:1);
  tabs.querySelectorAll('.tab').forEach(t=>t.setAttribute('aria-selected',t.dataset.l===l));
  list.innerHTML=sel.length?sel.map((m,i)=>`<article class="mrow glass rv" style="--d:${i*70}" data-in>${row(m)}</article>`).join(''):`<div class="mrow glass"><b>Сегодня матчей нет</b><p class="note">Расписание и прогнозы — в Telegram @jarvibet.</p></div>`;
  list.querySelectorAll('.more').forEach(b=>b.addEventListener('click',()=>{const r=b.closest('.mrow'),o=r.classList.toggle('open');b.setAttribute('aria-expanded',o)}));
  UI.observe(list)};
 tabs.addEventListener('click',e=>{const t=e.target.closest('.tab');if(t)render(t.dataset.l)});render('all')}
const timeCell=(m,L)=>`<div class="m-time"><b class="num">${m.t.slice(11)}</b><span><img src="${LGI(m.lg)}" alt="">${L.name}</span><i class="cd" data-t="${m.t}"></i></div>`;
const pairCell=(m,logo)=>`<div class="pair"><div><img src="${logo(m.a)}" alt="" loading="lazy"><span>${esc(m.a)}</span></div><div><img src="${logo(m.b)}" alt="" loading="lazy"><span>${esc(m.b)}</span></div></div>`;
const moreBtn=m=>`<button class="more" type="button" aria-expanded="false" aria-label="${esc(m.a)} — ${esc(m.b)}: подробнее">${ICON.plus}</button>`;

/* ── общий: лиги и бегущие эмблемы ── */
function leagues(L,D,clubs,logo){const cnt=id=>D.filter(m=>m.lg===id).length;
 $('lgs').innerHTML=L.map((l,i)=>{const n=cnt(l.id);return `<li><a class="lgt glass rv" style="--d:${i*60}" href="#matches" data-l="${l.id}"><img src="${LGI(l.id)}" alt=""><h3>${l.name}</h3><p>${l.full}</p>${l.note?`<span class="nb">${l.note}</span>`:''}<span class="n num">${n?n+' '+plural(n,'матч','матча','матчей')+' сегодня':'сегодня без матчей'}</span></a></li>`}).join('');
 UI.observe($('lgs'));
 $('lgs').addEventListener('click',e=>{const a=e.target.closest('[data-l]');if(!a)return;const t=document.querySelector(`.tab[data-l="${a.dataset.l}"]`);t&&t.click()});
 const half=Math.ceil(clubs.length/2),r=arr=>arr.map(([n,lg])=>`<span class="crest"><img src="${logo(n)}" alt="" loading="lazy">${esc(n)}<small>${lg}</small></span>`).join('');
 const a=clubs.slice(0,half),b=clubs.slice(half);
 $('marq').innerHTML=`<div class="marq-row">${r(a)}${r(a)}</div><div class="marq-row rev">${r(b)}${r(b)}</div>`;
 $('marq').querySelectorAll('.marq-row').forEach((row,i)=>[...row.children].slice(i?b.length:a.length).forEach(c=>c.setAttribute('aria-hidden','true')))}

/* ── общий: гистограмма розыгрышей (DOM) + фон-гистограмма ── */
function hist(bins,labels,hot,cut){const h=$('hist'),mx=Math.max(...bins);
 h.classList.remove('on');
 h.innerHTML=bins.map((v,i)=>`<div class="col${hot(i)?' hot':''}" style="--i:${i};--h:${(v/mx*78).toFixed(1)}%"><span class="pv">${pc(v)}</span><div class="colb"></div><span class="lb">${labels[i]}</span></div>`).join('')+
  (cut!=null?`<div class="cut" style="left:${(cut/bins.length*100).toFixed(2)}%"><span>${cut===3?'ТБ 2,5':''}</span></div>`:'');
 requestAnimationFrame(()=>requestAnimationFrame(()=>h.classList.add('on')));
 const sec=$('model');sec._opts={p:bins};window.Field&&Field.refresh()}
function simCounter(n){const el=$('simn');if(RM){el.textContent=UI.fmt(n,0);return}const t0=performance.now();const f=now=>{const q=Math.min(1,(now-t0)/1300);el.textContent=UI.fmt(Math.round(n*(1-Math.pow(1-q,3))),0);if(q<1)requestAnimationFrame(f)};requestAnimationFrame(f)}

/* ════════════════ ФУТБОЛ ════════════════ */
function football(){
 const D=window.__FTODAY||[],B=window.__FOOTBT;
 const L=[{id:'epl',name:'АПЛ',full:'Англия'},{id:'laliga',name:'Ла Лига',full:'Испания'},{id:'seriea',name:'Серия А',full:'Италия'},{id:'bundesliga',name:'Бундеслига',full:'Германия'},
  {id:'ligue1',name:'Лига 1',full:'Франция'},{id:'portugal',name:'Португалия',full:'Примейра',note:'разбор без «ВЫБОР»'},{id:'ucl',name:'Лига чемпионов',full:'Еврокубок'}];
 const LN=Object.fromEntries(L.map(l=>[l.id,l]));
 const FC={'Рома':'roma','ПСЖ':'psg','Ман Сити':'mancity','Челси':'chelsea','Бавария':'bayern','Барселона':'barcelona','Реал':'realmadrid','Арсенал':'arsenal','МЮ':'manutd','Атлетико':'atletico','Милан':'milan','Интер':'inter','Боруссия Д':'dortmund','Спортинг':'sporting','Бенфика':'benfica','Порту':'porto','Наполи':'napoli','Ювентус':'juventus','Ливерпуль':'liverpool','Фиорентина':'fiorentina','Байер':'leverkusen','Ланс':'lens','Марсель':'marseille','Бетис':'betis','Майнц':'mainz','Брага':'braga','Брентфорд':'brentford','Реал Сосьедад':'sociedad'};
 const logo=n=>FC[n]?`../assets/clubs/${FC[n]}.webp`:LGI('ucl');
 const PICK=m=>m.k!=='—'&&m.pr>=.6;
 $('chips').innerHTML=L.map(l=>`<li><a href="#leagues"><img src="${LGI(l.id)}" alt="" width="24" height="24">${l.name}</a></li>`).join('');
 const best=[...D].filter(PICK).sort((a,b)=>b.pr-a.pr)[0]||D[0];
 board($('board'),best,{lgName:LN[best.lg].name,logo,tag:'ВЫБОР',until:'До стартового свистка',when:'Прогноз выходит в канале за 4–5 часов до матча.'});

 matches(D,L,m=>{const mx=Math.max(...m.pp),pk=PICK(m);
  return `<div class="m-main">${timeCell(m,LN[m.lg])}${pairCell(m,logo)}
   <div class="minis">${['П1','Х','П2'].map((k,j)=>mini(k,m.pp[j],m.pp[j]===mx)).join('')}${mini('ТБ 2,5',m.tb,m.tb>=.6)}</div>
   <div class="pk-cell">${pk?'<span class="tag">ВЫБОР</span>':''}<b>${esc(m.p)}</b>${m.k!=='—'?`<span class="k">${m.k}</span>`:`<small>${m.lg==='portugal'?'Португалия — только разбор':'Пост выходит за 4–5 часов до матча'}</small>`}</div>
   ${moreBtn(m)}</div>
   <div class="m-det"><div><dl>
    <div><dt>Форма, 5 матчей</dt><dd>${esc(m.a)} ${form(m.fa)}</dd><dd>${esc(m.b)} ${form(m.fb)}</dd></div>
    <div><dt>Личные встречи, 5 последних</dt><dd>${esc(m.h2h)}</dd></div>
    <div><dt>Наносит / допускает (1 — средний уровень лиги)</dt><dd class="num">${esc(m.a)}: ${f1(m.att[0],2)} / ${f1(m.def[0],2)}</dd><dd class="num">${esc(m.b)}: ${f1(m.att[1],2)} / ${f1(m.def[1],2)}</dd></div>
   </dl></div></div>`});

 const CL=[['Ман Сити','АПЛ'],['Ливерпуль','АПЛ'],['Арсенал','АПЛ'],['Челси','АПЛ'],['МЮ','АПЛ'],['Реал','Ла Лига'],['Барселона','Ла Лига'],['Атлетико','Ла Лига'],['Бавария','Бундеслига'],['Боруссия Д','Бундеслига'],
  ['Интер','Серия А'],['Милан','Серия А'],['Ювентус','Серия А'],['Наполи','Серия А'],['Рома','Серия А'],['ПСЖ','Лига 1'],['Бенфика','Португалия'],['Порту','Португалия'],['Спортинг','Португалия']];
 leagues(L,D,CL,logo);

 // сила лиг к АПЛ
 const LGN={epl:'АПЛ',laliga:'Ла Лига',bundesliga:'Бундеслига',ligue1:'Лига 1',seriea:'Серия А',portugal:'Португалия'},mn=-1.2;
 $('pwl').innerHTML=`<h3>Сила лиг Европы к АПЛ</h3><p class="note">По матчам еврокубков: разница «атака − оборона», АПЛ — ноль.</p>`+
  Object.entries(B.power).map(([id,v],i)=>`<div class="bar" style="--i:${i}"><span>${LGN[id]}</span><em><i style="--w:${(1-v/mn).toFixed(3)}"></i></em><b class="${v<0?'dn':''}">${v?f1(v,2).replace('-','−'):'0'}</b></div>`).join('')+
  `<p class="note" style="margin-top:16px">Источник: проверка модели 30.10, предварительно.</p>`;
 const TOP=[['Ман Сити','АПЛ'],['Реал','Ла Лига'],['Бавария','Бундеслига'],['Ливерпуль','АПЛ'],['Барселона','Ла Лига'],['Арсенал','АПЛ'],['Интер','Серия А'],['ПСЖ','Лига 1']];
 $('order').innerHTML=TOP.map(([n,lg],i)=>`<li><span class="pos">${two(i+1)}</span><img src="${logo(n)}" alt="" loading="lazy"><b>${esc(n)}</b><span class="note">${lg}</span></li>`).join('');

 // модель на матче дня
 const ex=best,AVG=[1.52,1.18],lh=ex.att[0]*ex.def[1]*AVG[0],la=ex.att[1]*ex.def[0]*AVG[1];
 $('ad').innerHTML=[[ex.a+' наносит',ex.att[0]],[ex.b+' допускает',ex.def[1]],[ex.b+' наносит',ex.att[1],'color-mix(in srgb,var(--ink) 55%,transparent)'],[ex.a+' допускает',ex.def[0],'color-mix(in srgb,var(--ink) 55%,transparent)']]
  .map(([k,v,c])=>`<div class="r"><span>${esc(k)}</span><em><i style="--w:${Math.min(1,v/1.6).toFixed(3)};${c?'--c:'+c:''}"></i></em><b>${f1(v,2)}</b></div>`).join('');
 $('lam').innerHTML=`<span>Ожидаемые голы</span><b>${f1(lh,2)} : ${f1(la,2)}</b>`;
 $('simh').textContent=`${ex.a} — ${ex.b}: голы за матч`;
 const rp=l=>{let k=0,p=Math.exp(-l),s=p,u=Math.random();while(u>s&&k<12){k++;p*=l/k;s+=p}return k};
 function sim(n){const T=new Array(8).fill(0);let h=0,d=0,a=0,o=0;for(let i=0;i<n;i++){const x=rp(lh),y=rp(la);x>y?h++:x===y?d++:a++;if(x+y>2)o++;T[Math.min(7,x+y)]++}
  return {T:T.map(v=>v/n),r:[h,d,a,o].map(v=>v/n)}}
 let S=sim(10000);
 const show=()=>{hist(S.T,['0','1','2','3','4','5','6','7+'],i=>i>=3,3);simCounter(10000);
  const r=S.r,mx=Math.max(r[0],r[1],r[2]);$('simout').innerHTML=[['П1',r[0]],['Х',r[1]],['П2',r[2]],['ТБ 2,5',r[3]]].map(([k,v],i)=>`<div class="${(i<3&&v===mx)||(i===3&&v>=.6)?'hi':''}"><b class="num">${pc(v)}</b>${k}</div>`).join('')};
 $('simbox').addEventListener('seen',show,{once:true});
 $('again').addEventListener('click',()=>{S=sim(10000);window.Field&&Field.burst();show()});
 const inv=ex.x.map(k=>1/k),sum=inv.reduce((a,b)=>a+b),line=inv.map(v=>v/sum);
 const lg=p=>Math.log(p/(1-p)),ilg=x=>1/(1+Math.exp(-x));
 const mi=line.indexOf(Math.max(...line)),mM=S.r[mi],mL=line[mi],mX=ilg(.45*lg(mM)+.55*lg(mL));
 $('mix').innerHTML=`<p class="note" style="margin-bottom:8px">Исход ${['П1','Х','П2'][mi]} в матче ${esc(ex.a)} — ${esc(ex.b)}:</p>`+
  [['Модель',mM,'color-mix(in srgb,var(--ink) 55%,transparent)'],['Линия рынка',mL,'color-mix(in srgb,var(--ink) 30%,transparent)'],['Смесь',mX,'var(--acc)']].map(([k,v,c])=>`<div class="r"><span>${k}</span><em><i style="--w:${v.toFixed(3)};--c:${c}"></i></em><b>${pc(v)}</b></div>`).join('')+`<p class="note" style="margin-top:8px">Пример расчёта.</p>`;

 // порог «ВЫБОР»
 const thr=$('thr');
 const showThr=()=>{const v=+thr.value,row=B.thr.reduce((a,b)=>Math.abs(b[0]-v)<Math.abs(a[0]-v)?b:a),[p,n,pr,got,roi]=row;
  thr.style.setProperty('--p',((v-55)/10*100)+'%');
  $('throut').innerHTML=`<div><span>ставок</span><b>${n}</b></div><div><span>обещано</span><b>${f1(pr)}&nbsp;%</b></div><div class="${got>=pr-3?'got':'bad'}"><span>зашло</span><b>${f1(got)}&nbsp;%</b></div><div class="${roi>=0?'got':'bad'}"><span>ROI, закрытие</span><b>${roi>0?'+':roi<0?'−':''}${f1(Math.abs(roi))}&nbsp;%</b></div>`;
  $('thrnote').textContent=(p!==v?`Ближайший посчитанный порог — ${p} %. `:'')+(p===60?'Наш порог: «зашло» в пределах 3 п. п. от обещанного.':p<60?'Ниже 60 % обещание расходится с результатом.':'Выше 62 % ставок мало, и они хуже.')+' Проверка вслепую, 2025/26.';
  thr.setAttribute('aria-valuetext',`${v} %: ${n} ставок, зашло ${f1(got)}&nbsp;%`)};
 thr.addEventListener('input',showThr);showThr();
 $('lgtable').innerHTML=Object.entries(B.lg).filter(([k])=>k!=='portugal').map(([k,[n,pr,got]])=>`<li><span>${LGN[k]} · ${n}</span><b class="${got<pr?'dn':''}">${f1(pr)} → ${f1(got)}&nbsp;%</b></li>`).join('');
}

/* ════════════════ ХОККЕЙ ════════════════ */
function hockey(){
 const T=window.__TODAY,H=window.__HOCKEY;
 const D=[...T.khl.map(m=>({...m,lg:'khl'})),...T.nhl.map(m=>({...m,lg:'nhl'}))];
 const L=[{id:'khl',name:'КХЛ',full:'Континентальная хоккейная лига',note:'днём и вечером по Москве'},{id:'nhl',name:'НХЛ',full:'Национальная хоккейная лига',note:'ночью по Москве'}];
 const LN=Object.fromEntries(L.map(l=>[l.id,l]));
 const EM={'СКА':'ska','ЦСКА':'cska','Ак Барс':'akbars','Локомотив':'lokomotiv','Сибирь':'sibir','Трактор':'traktor','Бостон':'nhl_bos','Торонто':'nhl_tor','Колорадо':'nhl_col','Даллас':'dallas','Вегас':'nhl_vgk','Эдмонтон':'nhl_edm'};
 const logo=n=>EM[n]?`../assets/em/${EM[n]}.webp`:LGI('khl');
 $('chips').innerHTML=L.map(l=>`<li><a href="#leagues"><img src="${LGI(l.id)}" alt="" width="24" height="24">${l.name}</a></li>`).join('');
 const best=[...D].sort((a,b)=>b.pr-a.pr)[0];
 const bk=D.find(m=>m.a==='Ак Барс')||best;
 board($('board'),bk,{lgName:LN[bk.lg].name,logo,tag:'Прогноз',until:'До вбрасывания',when:'КХЛ — в канале до 08:00 МСК, НХЛ — до 14:00 МСК.'});

 matches(D,L,m=>`<div class="m-main">${timeCell(m,LN[m.lg])}${pairCell(m,logo)}
   <div class="odds" aria-label="Кэфы линии">${['П1','Х','П2'].map((k,j)=>`<div><b class="num">${f1(m.x[j],2)}</b>${k}</div>`).join('')}</div>
   <div class="pk-cell"><b>${esc(m.p)}</b><span class="k">${m.k.replace('.',',')}</span> <small>· ${pc(m.pr)} по модели</small></div>
   ${moreBtn(m)}</div>
   <div class="m-det"><div><dl>
    <div><dt>Почему</dt><dd>${esc(m.y)}</dd></div>
    <div><dt>Вероятность по модели</dt><dd>${mini('',m.pr,true)}</dd></div>
    <div><dt>Пост в канале</dt><dd>${m.lg==='khl'?'до 08:00 МСК':'до 14:00 МСК'}, с кэфом и разбором</dd></div>
   </dl></div></div>`);

 const CL=[['СКА','КХЛ'],['ЦСКА','КХЛ'],['Ак Барс','КХЛ'],['Локомотив','КХЛ'],['Сибирь','КХЛ'],['Трактор','КХЛ'],['Бостон','НХЛ'],['Торонто','НХЛ'],['Колорадо','НХЛ'],['Даллас','НХЛ'],['Вегас','НХЛ'],['Эдмонтон','НХЛ']];
 leagues(L,D,CL,logo);

 // рейтинг Эло и тренды
 const mxE=Math.max(...H.elo.map(e=>e[1])),mnE=1400;
 $('pwl').innerHTML=`<h3>Рейтинг Эло, КХЛ</h3><p class="note">Сила команды одним числом. Пересчитывается после каждого матча: победа над сильным стоит больше.</p>`+
  H.elo.map(([n,v,d],i)=>`<div class="bar" style="--i:${i}"><span>${esc(n)}</span><em><i style="--w:${((v-mnE)/(mxE-mnE)).toFixed(3)}"></i></em><b>${v}</b></div>`).join('')+
  `<p class="note" style="margin-top:16px">Пример данных.</p>`;
 $('pwr').innerHTML=`<h3>Что заходит у команд</h3><p class="note">Как часто случается событие за сезон. Пример данных.</p>
  <ol class="order tight">${H.eloOrder.map(([n,w,o,u,ot])=>`<li><img src="${logo(n)}" alt="" loading="lazy"><b>${esc(n)}</b><span class="num">Победа ${w}% · ТБ 5,5 ${o}%</span></li>`).join('')}</ol>
  <ul class="trends">${H.trends.map(([t,v])=>`<li><span>${esc(t)}</span><b class="num">${v}</b></li>`).join('')}</ul>`;

 // модель: Ак Барс — Локомотив
 const ea=H.elo.find(e=>e[0]===bk.a),eb=H.elo.find(e=>e[0]===bk.b);
 $('ad').innerHTML=[[bk.a,ea[1]],[bk.b,eb[1]]].map(([k,v],i)=>`<div class="r"><span>${esc(k)}, Эло</span><em><i style="--w:${((v-mnE)/(mxE-mnE)).toFixed(3)};${i?'':'--c:color-mix(in srgb,var(--ink) 55%,transparent)'}"></i></em><b>${v}</b></div>`).join('');
 $('lam').innerHTML=`<span>Последние игры</span><b style="font-size:15px;font-family:var(--text);white-space:normal">${esc(bk.y)}</b>`;
 $('simh').textContent=`${bk.a} — ${bk.b}`;
 const base=H.sim;
 function sim(n){const c=[0,0,0];for(let i=0;i<n;i++){const r=Math.random();c[r<base[0]?0:r<base[0]+base[1]?1:2]++}return c.map(v=>v/n)}
 let S=sim(10000);
 const show=()=>{hist(S,['П1','Х','П2'],i=>i===2,null);simCounter(10000);
  $('simout').innerHTML=[['П1',S[0]],['Х',S[1]],['П2',S[2]]].map(([k,v],i)=>`<div class="${i===2?'hi':''}"><b class="num">${pc(v)}</b>${k}</div>`).join('')+`<div><b class="num">${bk.k.replace('.',',')}</b>кэф П2</div>`};
 $('simbox').addEventListener('seen',show,{once:true});
 $('again').addEventListener('click',()=>{S=sim(10000);window.Field&&Field.burst();show()});
 const lineP=1/parseFloat(bk.k);
 $('mix').innerHTML=`<p class="note" style="margin-bottom:8px">${esc(bk.p)}:</p>`+[['Модель',bk.pr,'var(--acc)'],['Линия, ≈',lineP,'color-mix(in srgb,var(--ink) 40%,transparent)']].map(([k,v,c])=>`<div class="r"><span>${k}</span><em><i style="--w:${v.toFixed(3)};--c:${c}"></i></em><b>${pc(v)}</b></div>`).join('')+`<p class="note" style="margin-top:8px">Пример расчёта.</p>`;

 // коридор кэфов
 const k=$('thr');
 const showK=()=>{const v=+k.value;k.style.setProperty('--p',((v-1.2)/2*100)+'%');const ok=v>=1.6&&v<=2.3;
  $('throut').innerHTML=`<div><span>кэф</span><b>${f1(v,2)}</b></div><div><span>по линии ≈</span><b>${Math.round(100/v)} %</b></div><div class="${ok?'got':'bad'}" style="grid-column:span 2"><span>для модели</span><b style="font-family:var(--text);font-size:18px">${ok?'рабочий коридор':v<1.6?'слишком низкий':'слишком высокий'}</b></div>`;
  $('thrnote').textContent=ok?'Выбор — самое вероятное событие в коридоре 1,6–2,3.':v<1.6?'Слишком низкий кэф: рисковать ради такого нет смысла.':'Слишком высокий кэф: больше случайности, чем расчёта.';
  k.setAttribute('aria-valuetext',`кэф ${f1(v,2)}`)};
 k.addEventListener('input',showK);showK();
 $('recent').innerHTML=(window.__RES||[]).map(r=>`<li class="${r.ok?'ok':'no'}">${r.ok?ICON.ok:ICON.no}<span>${esc(r.t)} · ${esc(r.b)}</span></li>`).join('');
}

if(SPORT==='football')football();else if(SPORT==='hockey')hockey();
})();
