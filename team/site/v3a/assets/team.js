/* JARVIS v3a — страница команды: team/index.html?id=<slug> (slug = имя эмблемы в assets/em без .webp).
   Данные — assets/data/teams.js (собирает team/build_data.py из app/data.json и data/*.json живого сайта).
   Шестиугольник силы — функция radar() со страницы команды мини-приложения (team/site/app/index.html), цвета под v3a. */
(()=>{
'use strict';
const D=window.JV_TEAMS||{teams:{},names:{},axes:[]};
const P=new URLSearchParams(location.search),ID=(P.get('id')||'').toLowerCase(),THEME=P.get('theme');
const T=D.teams[ID];
const esc=t=>String(t??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const f=(v,d=2)=>(+v).toFixed(d).replace('.',',');
const plural=(n,a,b,c)=>{const k=n%100,j=n%10;return k>10&&k<20?c:j===1?a:j>1&&j<5?b:c};
const LG={khl:{name:'КХЛ'},nhl:{name:'НХЛ'}};
const lgp=lg=>`<span class="lgp ${lg}"><img src="../assets/lg/${lg}.webp" alt=""></span>`;
const em=(s,cls='em')=>`<img class="${cls}" src="../assets/em/${esc(s)}.webp" alt="" loading="lazy" width="64" height="64">`;
const nm=s=>D.names[s]||s;
// ссылки на страницы клубов: data-href — v3a.js при ?theme= переписывает href у «index.html», возвращаем id после него
const tq=THEME?`&theme=${encodeURIComponent(THEME)}`:'';
const tl=(s,inner,cls='')=>`<a class="${cls}" href="index.html?id=${esc(s)}${tq}" data-href="index.html?id=${esc(s)}${tq}">${inner}</a>`;
const BACK=lg=>`../hockey/index.html${THEME?'?theme='+encodeURIComponent(THEME):''}#lg-${lg}`;
const MON=['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'],WD=['вс','пн','вт','ср','чт','пт','сб'];
const day=d=>{const [y,m,dd]=d.slice(0,10).split('-').map(Number),x=new Date(Date.UTC(y,m-1,dd));return {d:dd,mon:MON[m-1],wd:WD[x.getUTCDay()],tm:d.slice(11,16)}};
const formTitle=g=>{const r=g.gf>g.ga?'W':(g.x?'OTL':'L'),o=nm(g.o),sc=`${g.gf}:${g.ga}`;return r==='W'?`Победа над ${o} ${sc}${g.x?(g.x==='Б'?' по буллитам':' в овертайме'):''}`:`Поражение от ${o} ${sc}${r==='OTL'?(g.x==='Б'?' по буллитам':' в овертайме'):''}`};
const res=g=>g.gf>g.ga?'W':(g.x?'OTL':'L');
const RL={W:['В','w','победа'],L:['П','l','поражение'],OTL:['ОТ','ot','поражение в овертайме или по буллитам']};
// плашка итога: В / П — основное время, ВО / ПО — овертайм, ВБ / ПБ — буллиты
const rlab=g=>{const r=res(g),b=g.x==='Б'?'Б':'О';return r==='W'?(g.x?['В'+b,'w','победа '+(b==='Б'?'по буллитам':'в овертайме')]:RL.W):(g.x?['П'+b,'ot','поражение '+(b==='Б'?'по буллитам':'в овертайме')]:RL.L)};
// тёмный фирменный цвет на тёмном фоне не виден — осветляем (как bright() в app/index.html)
function bright(h){const n=parseInt(String(h||'#3ee0ff').slice(1),16);let r=n>>16,g=n>>8&255,b=n&255;const l=(.2126*r+.7152*g+.0722*b)/255;
 if(l<.42){const k=(.42-l)/.42*.8+.2;r=Math.round(r+(255-r)*k);g=Math.round(g+(255-g)*k);b=Math.round(b+(255-b)*k)}return `rgb(${r},${g},${b})`}

/* ── шестиугольник силы: перенесён с лендинга-приложения (radar), сетка и подписи — от цветов темы ── */
function radar(series,ax){
 const W=366,H=420,r=142,c=W/2,cy=H/2+4,pt=(i,x)=>[c+r*x/100*Math.sin(Math.PI*i/3),cy-r*x/100*Math.cos(Math.PI*i/3)];
 const poly=vs=>vs.map((x,i)=>pt(i,x==null?0:x).map(n=>n.toFixed(1)).join(',')).join(' ');
 const one=series.length===1;
 let o=`<svg class="radar" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(series.map(s=>s.name+': '+ax.map((a,i)=>a+' '+(s.v[i]??'нет данных')).join(', ')).join('; '))}">`;
 for(const k of [100,75,50,25])o+=`<polygon class="${k===100?'rg0':'rg'}" points="${poly(Array(6).fill(k))}"/>`;
 for(let i=0;i<6;i++){const [x,y]=pt(i,100);o+=`<line class="rg" x1="${c}" y1="${cy}" x2="${x}" y2="${y}"/>`}
 if(one)o+=`<polygon class="rmid" points="${poly(Array(6).fill(55))}"/>`;
 series.slice().reverse().forEach(s=>{o+=`<polygon class="rpoly" points="${poly(s.v)}" fill="${s.c}" stroke="${s.c}"/>`;
  s.v.forEach((x,i)=>{if(x!=null){const [px,py]=pt(i,x);o+=`<circle class="rdot" cx="${px}" cy="${py}" r="5" fill="${s.c}"/>`}})});
 ax.forEach((a,i)=>{const [lx,vy]=pt(i,100),ty=[0,1,5].includes(i)?vy-26:vy+22;
  o+=`<text class="rlab" x="${lx}" y="${ty}" text-anchor="middle">${esc(a)}</text><text class="rval" x="${lx}" y="${ty+19}" text-anchor="middle">${
   series.map(s=>`<tspan fill="${s.c}">${s.v[i]??'—'}</tspan>`).join('')}</text>`});
 return o+'</svg>';
}

/* ── нет такой команды ── */
if(!T){
 document.title='Команда не найдена · JARVIS';
 document.querySelector('.tmhero').classList.add('none');
 document.getElementById('hero').innerHTML=`<header class="tmid tmnone" data-rv>
   <a class="crumb" href="${BACK('khl')}"><span aria-hidden="true">←</span> Лиги и клубы</a>
   <h1>Такой команды нет</h1>
   <p class="lead">${ID?`По адресу «${esc(ID)}» клуба не нашлось.`:'В адресе не указан клуб.'} Выберите команду на стене эмблем — там все 54 клуба КХЛ и НХЛ.</p>
   <div class="hero-cta"><a class="btn btn-tg" href="${BACK('khl')}">Клубы КХЛ</a><a class="btn btn-line" href="${BACK('nhl')}">Клубы НХЛ</a></div></header>`;
 ['table','games','players','picks'].forEach(id=>{const e=document.getElementById(id);e.hidden=true;e.removeAttribute('data-zone')}); // скрытые зоны сбивают «свет» арены
 document.documentElement.classList.add('tm-none');
 document.querySelector('.nav').hidden=true;
 return;
}

const lg=T.lg,L=LG[lg],conf=T.conf||'';
/* ── палитра клуба: градиент шапки из фирменных цветов (assets/data/clubs.js), текст светлый или тёмный по контрасту ≥ 4,5:1 ── */
const rgb=h=>{const n=parseInt(String(h).replace('#','').replace(/^(.)(.)(.)$/,'$1$1$2$2$3$3'),16);return [n>>16,n>>8&255,n&255]};
const hex=a=>'#'+a.map(v=>Math.max(0,Math.min(255,Math.round(v))).toString(16).padStart(2,'0')).join('');
const mix=(a,b,t)=>hex(rgb(a).map((v,i)=>v+(rgb(b)[i]-v)*t));
const lum=h=>{const c=rgb(h).map(v=>{v/=255;return v<=.03928?v/12.92:((v+.055)/1.055)**2.4});return .2126*c[0]+.7152*c[1]+.0722*c[2]};
const cr=(a,b)=>{const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)};
function palette(c){
 let stops=[c[0],mix(c[0],c[1],.5),c[1]],acc=c[2];
 const ok=t=>stops.every(s=>cr(t,s)>=4.5&&cr(mix(t,s,.25),s)>=4.5);   // и основной текст, и приглушённый (подписи)
 let text=null;
 for(let k=0;k<14&&!text;k++){if(ok('#ffffff'))text='#ffffff';else if(ok('#0b0f16'))text='#0b0f16';else stops=stops.map(s=>mix(s,'#000000',.1))}
 text=text||'#ffffff';
 // акцент должен читаться на фоне шапки (≥ 3:1 — крупные цифры и линии шестиугольника)
 for(let k=0;k<10&&stops.some(s=>cr(acc,s)<3);k++)acc=mix(acc,text,.18);
 // акцент на светлой «газете» ниже (полоски, обводки): затемняем до ≥ 3:1 к бумаге
 let accL=c[2];for(let k=0;k<12&&cr(accL,'#eceee8')<3;k++)accL=mix(accL,'#000000',.12);
 return {stops,text,acc,accL,base:stops[0]};
}
const CP=palette((window.JV_CLUBS||{})[ID]||[T.colors?.[0]||'#1b2a44',T.colors?.[1]||'#0b1220',bright(T.colors?.[2])]);
const acc=CP.acc;
document.title=`${T.name} — матчи сезона, место в таблице, сила команды · JARVIS`;
{const st=document.body.style;[['--c1',CP.stops[0]],['--c2',CP.stops[1]],['--c3',CP.stops[2]],['--con',CP.text],['--cacc',CP.acc],['--team',CP.accL],['--cbase',CP.base]].forEach(([k,v])=>st.setProperty(k,v));
 document.body.classList.toggle('on-light',CP.text!=='#ffffff');
 const m=document.querySelector('meta[name=theme-color]');if(m)m.content=CP.stops[0];
 const wm=document.createElement('img');wm.className='tmwm';wm.src=`../assets/em/${ID}.webp`;wm.alt='';wm.setAttribute('aria-hidden','true');document.querySelector('.tmhero').prepend(wm)}
document.body.dataset.lg=lg;
/* ── клубная тема (03.11): у клуба из списка — свой фон каждой секции, файлы assets/club/<id>.css (+ .js при нужде) ── */
const CLUB_THEMES={nhl_fla:{css:1}};
const CS=(window.CLUB_SET||{})[ID];
if(CLUB_THEMES[ID]){const th=CLUB_THEMES[ID];document.body.classList.add('club','club-'+ID);
 if(th.css){const l=document.createElement('link');l.rel='stylesheet';l.href=`../assets/club/${ID}.css`;document.head.appendChild(l)}
 if(th.js){const s=document.createElement('script');s.src=`../assets/club/${ID}.js`;document.head.appendChild(s)}}
else if(CS){/* общий движок assets/club/theme.css: переменные клуба из assets/club/themes.js */
 const b=document.body,u=p=>`url(${new URL('../assets/'+p,location.href).href})`;b.classList.add('club','club-g','club-'+ID);
 [['--k-dk',CS.dk],['--k-a1',CS.a1],['--k-a2',CS.a2],['--k-ac',CS.ac],['--k-em',u('em/'+ID+'.webp')],['--k-mA',u('club/m/'+CS.m[0]+'.svg')],['--k-mB',u('club/m/'+(CS.m[1]||CS.m[0])+'.svg')]].forEach(([k,v])=>b.style.setProperty(k,v));
 if(!CS.m[1])b.classList.add('nomB')}
const played=T.games.filter(g=>g.gf!=null),future=T.games.filter(g=>g.gf==null);
/* серия: от последнего сыгранного матча назад — победа (любая) или поражение (любое, в т.ч. ОТ/буллиты); показываем от 3 */
const streak=(()=>{const a=played.slice().sort((x,y)=>String(x.d).localeCompare(String(y.d)));let n=0,w=null;
 for(let i=a.length-1;i>=0;i--){const win=a[i].gf>a[i].ga;if(w===null)w=win;if(win!==w)break;n++}
 return {n,win:w,last:a.slice(a.length-n).map(g=>g.gf>g.ga)}})();
const streakHtml=streak.n>=3?`<p class="tmstreak ${streak.win?'w':'l'}" aria-label="${streak.win?'Серия побед':'Серия поражений'}: ${streak.n}"><span class="sk">${streak.win?'Серия побед':'Серия поражений'}:</span><b class="num">${streak.n}</b><span class="dots" aria-hidden="true">${streak.last.slice(-10).map(x=>`<i class="${x?'w':'l'}"></i>`).join('')}</span></p>`:'';
const hasSample=T.games.some(g=>g.s||g.ks);
const otl=Math.max(0,(T.pts||0)-2*(T.w||0));
const confRows=Object.entries(D.teams).filter(([,x])=>x.lg===lg&&x.conf===conf).sort((a,b)=>a[1].place-b[1].place);
const builtDay=(D.built||'').slice(0,10),bd=builtDay?day(builtDay):null;
const asOf=bd?`на ${bd.d} ${bd.mon}`:'';

/* ── 1. шапка команды на тёмной арене + шестиугольник ── */
const ax=D.axes||[];
document.getElementById('hero').innerHTML=`
 <header class="tmid" data-rv>
  <a class="crumb" href="${BACK(lg)}"><span aria-hidden="true">←</span> Лиги и клубы · ${L.name}</a>
  <div class="tmrow">
   <span class="tmcrest">${em(ID)}</span>
   <div class="tmname"><p class="tmlg">${lgp(lg)}<span>${L.name}</span><span class="dot">·</span><span>Конференция «${esc(conf)}»</span></p>
    <h1>${esc(T.name)}</h1></div>
  </div>
  <div class="tmplace"><b class="num">${T.place}</b><span>-е место<br>в конференции «${esc(conf)}»</span></div>
  <ul class="tmpills" aria-label="Коротко о сезоне">
   <li><b class="num">${T.pts}</b><span>${plural(T.pts,'очко','очка','очков')}</span></li>
   <li><b class="num">${T.gp}</b><span>${plural(T.gp,'игра','игры','игр')}</span></li>
   <li><b class="num">${T.w}–${T.l}</b><span>победы–поражения${otl?`, из них ${otl} в ОТ`:''}</span></li>
   <li><b class="num">${T.gf}:${T.ga}</b><span>шайбы</span></li>
  </ul>
  ${streakHtml}
  ${T.coach?`<p class="tmcoach">Главный тренер — ${esc(T.coach.split(' ').slice(0,2).reverse().join(' '))}</p>`:''}
 </header>
 <div class="tmpower" data-rv>
  <div class="ph"><h2 class="h3">Шестиугольник силы</h2><span>место в лиге, 0–100</span></div>
  <div class="rad">${radar([{v:T.axes||[],c:acc,name:T.name}],ax)}</div>
  <div class="legend"><span><i style="border-color:${acc}"></i>${esc(T.name)}</span><span><i class="d"></i>середина лиги</span></div>
  <p class="note">Балл — место команды в своей лиге по показателю: 100 — лучшая, 10 — худшая. ${lg==='khl'?'Большинство и меньшинство — голы в большинстве и пропущенные в меньшинстве за игру.':'Большинство и меньшинство — реализация и нейтрализация по данным НХЛ.'} Форма — очки за последние 10 игр.</p>
 </div>`;

/* ── 2. место в таблице и статистика ── */
const last5=played.slice(-5);
const raw=T.raw||[],A=T.axes||[];
const tile=(lab,val,unit,i,sub)=>`<div class="st"><span class="sl">${lab}</span><b class="num">${val}<small>${unit}</small></b>
  ${i!=null&&A[i]!=null?`<span class="bar" aria-label="${A[i]} из 100"><i style="--w:${A[i]}%"></i></span><span class="ss">${esc(ax[i])} — <b>${A[i]}</b> из 100 в ${L.name}</span>`:`<span class="ss">${sub||''}</span>`}</div>`;
const pp=lg==='nhl'?[f(raw[3]*100,1),'%','реализация большинства']:[f(raw[3]),'','голов в большинстве за игру'];
const pk=lg==='nhl'?[f(raw[4]*100,1),'%','нейтрализация меньшинства']:[f(raw[4]),'','пропускает в меньшинстве за игру'];
const hm=(T.tr||{}).home,aw=(T.tr||{}).away;
document.getElementById('tableBox').innerHTML=`
 <div class="sec-head" data-rv><h2>Место в таблице</h2><p>${lgp(lg)}${L.name}, конференция «${esc(conf)}» ${asOf}. Очки, игры и шайбы — настоящие, обновляются вместе с сайтом.</p></div>
 <div class="tmgrid">
  <div class="tmtable" data-rv><table class="table stand">
   <thead><tr><th>#</th><th>Клуб</th><th class="ra">И</th><th class="ra hide-s">В</th><th class="ra hide-s">П</th><th class="ra hide-s">Шайбы</th><th class="ra">О</th></tr></thead>
   <tbody>${confRows.map(([s,x])=>`<tr class="${s===ID?'me':''}"${s===ID?' aria-current="true"':''}><td>${x.place}</td>
    <td>${tl(s,`${em(s)}<span>${esc(x.name)}</span>`,'cl')}</td><td class="ra">${x.gp}</td><td class="ra hide-s">${x.w}</td><td class="ra hide-s">${x.l}</td>
    <td class="ra hide-s">${x.gf}:${x.ga}</td><td class="ra pts">${x.pts}</td></tr>`).join('')}</tbody></table></div>
  <div class="tmstats" id="stats" data-rv>
   <div class="stg">
    ${tile('Забивает за игру',f(T.gf/T.gp),'',0)}
    ${tile('Пропускает за игру',f(T.ga/T.gp),'',1)}
    ${tile('Большинство',pp[0],pp[1],3)}
    ${tile('Меньшинство',pk[0],pk[1],4)}
    ${tile('Вратари: отражённые',f(raw[2]*100,1),'%',2)}
    ${tile('Дома · в гостях',hm?`${hm[0]}–${hm[1]}`:'—',aw?` · ${aw[0]}–${aw[1]}`:'',null,'победы–поражения дома и на выезде')}
   </div>
   <div class="formbox"><span class="sl">Форма — последние 5 игр</span>
    <ol class="frm" aria-label="Последние 5 игр, слева раньше">${last5.map(g=>{const t=formTitle(g);return `<li class="${RL[res(g)][1]}" title="${esc(t)}" aria-label="${esc(t)}"><b><img src="../assets/em/${esc(g.o)}.webp" alt="" loading="lazy"></b><span>${g.gf}:${g.ga}${g.x?' '+g.x:''}</span></li>`}).join('')}</ol>
    <p class="ss">Слева — раньше, справа — последняя игра. В кружке — соперник: зелёный — победа, красный — поражение, серый — поражение в овертайме или по буллитам. За 10 игр — <b>${T.l10s||T.l10+' '+plural(T.l10,'очко','очка','очков')}</b>.</p></div>
  </div>
 </div>`;

/* ── 3. все матчи сезона ── */
const kf=v=>v==null?'—':f(v,2);
const row=g=>{const t=day(g.d),opp=tl(g.o,`${em(g.o)}<span>${esc(nm(g.o))}</span>`,'op');
 const when=`<span class="gd"><b>${t.d} ${t.mon}</b><small>${t.wd}${t.tm?' · '+t.tm:''}</small></span>`;
 const ha=`<span class="ha ${g.h?'h':'a'}" title="${g.h?'дома':'в гостях'}">${g.h?'Д':'В'}</span>`;
 const smp=g.s?'<span class="smp">пример</span>':'';
 if(g.gf!=null){const r=rlab(g);
  return `<li class="g ${g.h?'home':'away'}${g.s?' is-s':''}">${when}${ha}${opp}<span class="sc num">${g.gf}:${g.ga}${g.x?`<small>${g.x}</small>`:''}</span><span class="rs ${r[1]}" title="${r[2]}">${r[0]}</span>${smp}</li>`}
 return `<li class="g fut ${g.h?'home':'away'}${g.s?' is-s':''}">${when}${ha}${opp}<span class="kx num" aria-label="Линия: победа команды ${esc(T.name)} ${kf(g.k[0])}, ничья ${kf(g.k[1])}, победа соперника ${kf(g.k[2])}"><span><small>П</small>${kf(g.k[0])}</span><span><small>Х</small>${kf(g.k[1])}</span><span><small>П</small>${kf(g.k[2])}</span></span>${g.s||g.ks?'<span class="smp">пример</span>':''}</li>`};
const wins=played.filter(g=>res(g)==='W').length;
const lossReg=played.filter(g=>res(g)==='L').length,lossOt=played.length-wins-lossReg;
const gfS=played.reduce((a,g)=>a+g.gf,0),gaS=played.reduce((a,g)=>a+g.ga,0);
const gsum=`<ul class="gsum" aria-label="Итоги сыгранных матчей" data-rv>
  <li><b class="num">${played.length}</b><span>${plural(played.length,'матч','матча','матчей')} сыграно</span></li>
  <li class="w"><b class="num">${wins}</b><span>${plural(wins,'победа','победы','побед')}</span></li>
  <li class="l"><b class="num">${lossReg+lossOt}</b><span>${plural(lossReg+lossOt,'поражение','поражения','поражений')}${lossOt?`, из них ${lossOt} в ОТ/по буллитам`:''}</span></li>
  <li><b class="num">${gfS}:${gaS}</b><span>шайбы забито : пропущено</span></li></ul>`;
document.getElementById('gamesBox').innerHTML=`
 <div class="sec-head" data-rv><h2>Матчи сезона</h2><p>${played.length} ${plural(played.length,'матч сыгран','матча сыграно','матчей сыграно')}, ${wins} ${plural(wins,'победа','победы','побед')}. Плашка справа: В / П — основное время, ВО / ПО — овертайм, ВБ / ПБ — буллиты. Впереди — время по Москве и линия: первая цифра — победа команды ${esc(T.name)}, вторая — ничья в основное время, третья — победа соперника.</p></div>
 ${gsum}
 <div class="gfilter" role="group" aria-label="Какие матчи показать" data-rv><div class="seg"><button type="button" aria-pressed="true" data-f="all">Все</button><button type="button" aria-pressed="false" data-f="home">Дома</button><button type="button" aria-pressed="false" data-f="away">В гостях</button></div></div>
 <div class="glist" id="glist" data-f="all">
  <h3 class="gh">Ближайшие<span>${future.length}</span></h3>
  <ol class="gs">${future.map(row).join('')}</ol>
  <h3 class="gh">Сыгранные<span>${played.length}</span></h3>
  <ol class="gs">${played.slice().reverse().map(row).join('')}</ol>
 </div>
 ${hasSample?`<p class="note smpnote"><span class="sample">Пример данных</span> Строки с пометкой «пример» — линия на матчи, где её ещё нет, и матчи, которых нет в данных лиги, дописаны для макета. Сыгранные матчи со счётом, игроки, место и шестиугольник — настоящие.</p>`:''}`;
document.querySelectorAll('.gfilter button').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.gfilter button').forEach(x=>x.setAttribute('aria-pressed',x===b));document.getElementById('glist').dataset.f=b.dataset.f}));

/* ── 4. что заходило в наших ставках ── */
const pk2=T.picks||[],hit=pk2.filter(p=>p.r==='win').length;
document.getElementById('picksBox').innerHTML=`
 <div class="sec-head" data-rv><h2>Наши ставки на ${esc(T.name)}</h2><p>Все прогнозы JARVIS на матчи команды — и зашедшие, и нет. Новые выходят в Telegram: КХЛ до 08:00, НХЛ до 14:00 МСК.</p></div>
 ${pk2.length?`<div class="pkwrap" data-rv>
  <div class="pksum"><b class="num">${hit}<small>из ${pk2.length}</small></b><span>${plural(hit,'прогноз зашёл','прогноза зашло','прогнозов зашло')}</span>
   <span class="pkbar" aria-hidden="true">${pk2.map(p=>`<i class="${p.r==='win'?'ok':'no'}"></i>`).join('')}</span></div>
  <ol class="pks">${pk2.map(p=>{const t=day(p.d),ok=p.r==='win';return `<li class="${ok?'ok':'no'}">
   <span class="gd"><b>${t.d} ${t.mon}</b><small>${t.wd}</small></span>
   <span class="pm">${em(p.h)}<span>${esc(nm(p.h))} — ${esc(nm(p.a))}</span>${em(p.a)}</span>
   <span class="pt"><strong>${esc(String(p.pick||'').replace(/(\d)\.(\d)/g,'$1,$2'))}</strong><small>кэф ${esc(p.k)} · счёт ${esc(p.sc)}</small></span>
   <span class="pr" title="${ok?'прогноз зашёл':'прогноз не зашёл'}">${ok?'✓':'✕'}</span></li>`}).join('')}</ol></div>`
 :`<div class="pkempty" data-rv><p>На матчи ${esc(T.name)} прогнозов пока не было. Как только модель найдёт ставку — она появится здесь и в канале.</p><a class="btn btn-ink" href="https://t.me/jarvibet" target="_blank" rel="noopener">Открыть @jarvibet</a></div>`}`;

/* ── 3б. игроки: лидеры, вкладки «Полевые» / «Вратари», сортировка по клику на заголовок ── */
const PL=T.pl,mmss=v=>v?`${Math.floor(v/60)}:${String(Math.round(v%60)).padStart(2,'0')}`:'—';
const SKC=[['pos','Поз','tx'],['gp','И'],['g','Г'],['a','П'],['pts','О'],['pm','+/−'],['pim','Штр'],['sog','Бр'],['toi','Время']];
const GKC=[['gp','И'],['w','В'],['l','П'],['sv','%'],['gaa','КН'],['so','Сух']];
const SKT={pos:'амплуа',gp:'игры',g:'голы',a:'передачи',pts:'очки (голы + передачи)',pm:'плюс/минус',pim:'штрафные минуты',sog:'броски по воротам',toi:'среднее время на льду за игру'};
const GKT={gp:'игры',w:'победы',l:'поражения (в НХЛ — вместе с овертаймом)',sv:'процент отражённых бросков',gaa:'коэффициент надёжности — пропущено за 60 минут',so:'«сухие» игры'};
const pbox=document.getElementById('playersBox');
if(!PL){pbox.innerHTML=`<div class="sec-head" data-rv><h2>Игроки</h2><p>Статистика игроков ${esc(T.name)} появится здесь, как только лига отдаст данные.</p></div>`}
else{
 const sk=PL.sk||[],gk=PL.gk||[];
 const hasSog=sk.some(p=>p.sog!=null),hasToi=sk.some(p=>p.toi);
 const skc=SKC.filter(c=>(c[0]!=='sog'||hasSog)&&(c[0]!=='toi'||hasToi));
 const minG=Math.max(3,Math.round(Math.max(0,...gk.map(p=>p.gp||0))*.3));
 const best=(a,k,ok=()=>true)=>a.filter(ok).reduce((m,p)=>m==null||(p[k]??-1)>(m[k]??-1)?p:m,null);
 const lead=[['Лучший бомбардир',best(sk,'pts'),p=>[p.pts,'очк.',`${p.g}+${p.a} в ${p.gp} ${plural(p.gp,'матче','матчах','матчах')}`]],
  ['Лучший снайпер',best(sk,'g'),p=>[p.g,plural(p.g,'гол','гола','голов'),`${p.gp} ${plural(p.gp,'матч','матча','матчей')}, ${p.pts} очк.`]],
  ['Лучший вратарь',best(gk,'sv',p=>(p.gp||0)>=minG&&p.sv!=null),p=>[f(p.sv,1),'%',`${p.gp} ${plural(p.gp,'матч','матча','матчей')}, КН ${f(p.gaa)}${p.so?`, ${p.so} сух.`:''}`]]].filter(x=>x[1]);
 const st={tab:sk.length?'sk':'gk',key:{sk:'pts',gk:'sv'},dir:{sk:-1,gk:-1}};
 const cmp=(k,d)=>(a,b)=>{const x=a[k],y=b[k];if(k==='pos'||k==='n')return d*String(x||'').localeCompare(String(y||''),'ru');return d*((x??-1e9)-(y??-1e9))||(b.pts||0)-(a.pts||0)||(b.g||0)-(a.g||0)||(b.gp||0)-(a.gp||0)};
 const cell=(p,k)=>{const v=p[k];return k==='toi'?mmss(v):k==='pm'?(v>0?'+'+v:v<0?'−'+Math.abs(v):'0'):k==='sv'?(v==null?'—':f(v,1)):k==='gaa'?(v==null?'—':f(v)):k==='pos'?esc(v):(v==null?'—':v)};
 const render=()=>{const sk0=st.tab==='sk',cols=sk0?skc:GKC,arr=(sk0?sk:gk).slice().sort(cmp(st.key[st.tab],st.dir[st.tab])),TT=sk0?SKT:GKT;
  const th=(k,l,cls='')=>{const on=st.key[st.tab]===k,d=st.dir[st.tab];return `<th class="${cls}" scope="col" aria-sort="${on?(d<0?'descending':'ascending'):'none'}"><button type="button" data-k="${k}" title="${esc(TT[k]||'')}">${esc(l)}<i aria-hidden="true">${on?(d<0?'↓':'↑'):''}</i></button></th>`};
  document.getElementById('plTable').innerHTML=`<table class="table pltab"><thead><tr><th class="c1" scope="col">№</th>${th('n','Игрок','c2 tx')}${cols.map(c=>th(c[0],c[1],c[2]||'ra')).join('')}</tr></thead>
   <tbody>${arr.map(p=>`<tr><td class="c1 num">${p.no??'—'}</td><td class="c2 pn">${esc(p.n)}</td>${cols.map(c=>`<td class="${c[2]||'ra'} num${c[0]===st.key[st.tab]?' on':''}">${cell(p,c[0])}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  document.querySelectorAll('#plTabs button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.t===st.tab));
 };
 pbox.innerHTML=`<div class="sec-head" data-rv><h2>Игроки</h2><p>Статистика сезона ${lgp(lg)}${L.name}: ${sk.length} ${plural(sk.length,'полевой игрок','полевых игрока','полевых игроков')} и ${gk.length} ${plural(gk.length,'вратарь','вратаря','вратарей')}. Нажмите на заголовок столбца — таблица отсортируется.</p></div>
  <ul class="plead" data-rv>${lead.map(([lab,p,fn])=>{const v=fn(p);return `<li><span class="sl">${lab}</span><b class="pln">${esc(p.n)}${p.no!=null?`<small class="num">№${p.no}</small>`:''}</b><span class="plv"><b class="num">${v[0]}</b><small>${esc(v[1])}</small></span><span class="ss">${esc(v[2])}</span></li>`}).join('')}</ul>
  <div class="gfilter" role="group" aria-label="Кого показать" data-rv><div class="seg" id="plTabs">${sk.length?`<button type="button" aria-pressed="true" data-t="sk">Полевые<small>${sk.length}</small></button>`:''}${gk.length?`<button type="button" aria-pressed="false" data-t="gk">Вратари<small>${gk.length}</small></button>`:''}</div></div>
  <div class="plwrap" id="plTable" data-rv tabindex="0" role="region" aria-label="Таблица игроков, листается вбок"></div>
  <p class="note plnote">${lg==='khl'?'Данные приложения КХЛ':'Данные НХЛ'}, регулярный сезон. Нап — нападающий, Защ — защитник${lg==='nhl'?', Цен — центр, ЛН / ПН — левый и правый нападающий':''}; «КН» — коэффициент надёжности вратаря, «Сух» — сухие матчи.</p>`;
 document.getElementById('plTabs').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;st.tab=b.dataset.t;render()});
 document.getElementById('plTable').addEventListener('click',e=>{const b=e.target.closest('th button');if(!b)return;const k=b.dataset.k,t=st.tab;
  if(st.key[t]===k)st.dir[t]*=-1;else{st.key[t]=k;st.dir[t]=(k==='n'||k==='pos'||k==='gaa')?1:-1}render()});
 render();
}

document.getElementById('foot').textContent=`Макет v3a · данные ${asOf}${hasSample?', часть — пример':''} · © JARVIS, @jarvibet`;
// v3a.js (keepTheme) при ?theme= обрезает «?id=» у ссылок на index.html — возвращаем после него
document.addEventListener('DOMContentLoaded',()=>document.querySelectorAll('a[data-href]').forEach(a=>a.setAttribute('href',a.dataset.href)));
})();
