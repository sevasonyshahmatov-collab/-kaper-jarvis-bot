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
 series.slice().reverse().forEach(s=>{o+=`<polygon class="rpoly${s.dash?' dash':''}" points="${poly(s.v)}" fill="${s.c}" stroke="${s.c}"${s.dash?' stroke-dasharray="9 6"':''}/>`;
  s.v.forEach((x,i)=>{if(x!=null){const [px,py]=pt(i,x);o+=`<circle class="rdot" cx="${px}" cy="${py}" r="5" fill="${s.c}"/>`}})});
 ax.forEach((a,i)=>{const [lx,vy]=pt(i,100),ty=[0,1,5].includes(i)?vy-26:vy+22;
  o+=`<text class="rlab" x="${lx}" y="${ty}" text-anchor="middle">${esc(a)}</text><text class="rval" x="${lx}" y="${ty+19}" text-anchor="middle">${
   series.map(s=>`<tspan fill="${s.c}">${s.v[i]??'—'}</tspan>`).join('<tspan class="rsep"> · </tspan>')}</text>`});
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
const CLUB_THEMES={nhl_fla:{css:1,bg:1}};
const CS=(window.CLUB_SET||{})[ID];
/* фон-картинка клуба (03.11): assets/club/bg/<id>.webp, сцена и «стекло» — assets/club/bg.css + bg.js; флаг bg:1 (CLUB_THEMES здесь или CLUB_SET в themes.js) */
function clubBg(){const b=document.body,v=new URLSearchParams(location.search).get('bgv'),m=v==='hero'?'hero':'bottom';b.classList.add('club-bg',m==='hero'?'club-bgh':'club-bgb');b.dataset.clubId=ID;
 const l=document.createElement('link');l.rel='stylesheet';l.href='../assets/club/bg.css';document.head.appendChild(l);
 const s=document.createElement('script');s.src='../assets/club/bg.js';document.head.appendChild(s)}
if(CLUB_THEMES[ID]){const th=CLUB_THEMES[ID];document.body.classList.add('club','club-'+ID);
 if(th.css){const l=document.createElement('link');l.rel='stylesheet';l.href=`../assets/club/${ID}.css`;document.head.appendChild(l)}
 if(th.js){const s=document.createElement('script');s.src=`../assets/club/${ID}.js`;document.head.appendChild(s)}
 if(th.bg)clubBg()}
else if(CS){/* общий движок assets/club/theme.css: переменные клуба из assets/club/themes.js */
 const b=document.body,u=p=>`url(${new URL('../assets/'+p,location.href).href})`;b.classList.add('club','club-g','club-'+ID);
 [['--k-dk',CS.dk],['--k-a1',CS.a1],['--k-a2',CS.a2],['--k-ac',CS.ac],['--k-em',u('em/'+ID+'.webp')],['--k-mA',u('club/m/'+CS.m[0]+'.svg')],['--k-mB',u('club/m/'+(CS.m[1]||CS.m[0])+'.svg')]].forEach(([k,v])=>b.style.setProperty(k,v));
 if(!CS.m[1])b.classList.add('nomB');
 if(CS.bg)clubBg()}
const played=T.games.filter(g=>g.gf!=null),future=T.games.filter(g=>g.gf==null);
/* серия: от последнего сыгранного матча назад — победа (любая) или поражение (любое, в т.ч. ОТ/буллиты); показываем от 3 */
const streak=(()=>{const a=played.slice().sort((x,y)=>String(x.d).localeCompare(String(y.d)));let n=0,w=null;
 for(let i=a.length-1;i>=0;i--){const win=a[i].gf>a[i].ga;if(w===null)w=win;if(win!==w)break;n++}
 return {n,win:w,last:a.slice(a.length-n).map(g=>g.gf>g.ga)}})();
const streakHtml=streak.n>=3?`<p class="tmstreak ${streak.win?'w':'l'}" aria-label="${streak.win?'Серия побед':'Серия поражений'}: ${streak.n}"><span class="sk">${streak.win?'Серия побед':'Серия поражений'}:</span><b class="num">${streak.n}</b><span class="dots" aria-hidden="true">${streak.last.slice(-10).map(x=>`<i class="${x?'w':'l'}"></i>`).join('')}</span></p>`:'';
const TGICO='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 3.2 2.9 10.4c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.8 5.6c.2.6.9.8 1.4.4l2.6-2.2 4.8 3.5c.6.4 1.4.1 1.6-.7l3.1-15.1c.2-1-.7-1.7-1.6-1.3z"/></svg>';
/* «Следить за командой»: старт бота с параметром follow_<id> (подписку на команду в боте делают отдельно) */
const followBtn=(cls='')=>`<a class="follow ${cls}" href="https://t.me/jarvibet?start=follow_${esc(ID)}" target="_blank" rel="noopener" title="Прогноз и итог матча — в Telegram">${TGICO}<span>Получать прогнозы</span></a>`;
const hasSample=T.games.some(g=>g.s||g.ks);
const otl=Math.max(0,(T.pts||0)-2*(T.w||0));
const confRows=Object.entries(D.teams).filter(([,x])=>x.lg===lg&&x.conf===conf).sort((a,b)=>a[1].place-b[1].place);
const builtDay=(D.built||'').slice(0,10),bd=builtDay?day(builtDay):null;
const asOf=bd?`на ${bd.d} ${bd.mon}`:'';

/* ── 1. шапка команды на тёмной арене + шестиугольник ── */
const ax=D.axes||[];
document.getElementById('hero').innerHTML=`
 <header class="tmid" data-rv>
  <div class="tmtop"><a class="crumb" href="${BACK(lg)}"><span aria-hidden="true">←</span> Лиги и клубы · ${L.name}</a>${followBtn('in-hero')}</div>
  <div class="tmrow">
   <span class="tmcrest">${em(ID)}</span>
   <div class="tmname"><p class="tmlg"><a class="lglnk" href="../hockey/league.html?lg=${lg}${tq}" title="Страница лиги">${lgp(lg)}<span>${L.name}</span></a><span class="dot">·</span><span>Конференция «${esc(conf)}»</span></p>
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

/* ── плашка «Игроки команды» под формой → раздел «Игроки» с фильтром по этой команде (владелец 03.11) ── */
const PLCODE=T.lg==='nhl'?(ID==='minnesota'?'MIN':ID==='dallas'?'DAL':ID.replace(/^nhl_/,'').toUpperCase()):ID;
const PLURL=T.lg==='nhl'?`../hockey/players.html?team=${PLCODE}`:`../hockey/players_khl.html?team=${encodeURIComponent(ID)}`;
const plTop=((T.pl&&T.pl.sk)||[]).slice().sort((a,b)=>(b.pts||0)-(a.pts||0)||(b.g||0)-(a.g||0)).slice(0,3);
const plIni=n=>String(n).split(/\s+/).filter(Boolean).map(w=>w[0]).slice(0,2).join('').toUpperCase();
const plCard=()=>`<a class="plcard" href="${PLURL}" aria-label="Все игроки ${esc(T.name)}: очки, голы, передачи «n из N»">
  <span class="sl">Игроки: ${esc(T.name)}</span>
  ${plTop.length?`<ol class="pltop">${plTop.map(x=>`<li><i class="pav" data-n="${esc(x.n)}">${esc(plIni(x.n))}</i><b>${esc(x.n)}</b><span>${x.g||0}+${x.a||0}=<em>${x.pts||0}</em></span></li>`).join('')}</ol>`:''}
  <span class="plgo">Все игроки, фото и «n из N» по рынкам <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></span></a>`;

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
   ${plCard()}
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
 :`<div class="pkempty" data-rv><p>На матчи ${esc(T.name)} прогнозов пока не было. Как только модель найдёт ставку — она появится здесь и в канале.</p><a class="btn btn-ink" href="https://t.me/jarvibet" target="_blank" rel="noopener">Открыть @jarvibet</a></div>`}
`;


/* ── 2а. следующий матч: крупная карточка сразу под шапкой ── */
const real=played.filter(g=>!g.s).slice().sort((a,b)=>String(a.d).localeCompare(String(b.d)));
const startMs=d=>Date.parse(d.slice(0,10)+'T'+(d.slice(11,16)||'00:00')+':00+03:00');
const fsort=future.slice().sort((a,b)=>String(a.d).localeCompare(String(b.d)));
const nextG=fsort.find(g=>startMs(g.d)>Date.now()-3*36e5)||fsort[0];   // матч, начавшийся больше 3 часов назад, но ещё без счёта в данных — пропускаем
if(nextG){
 const t=day(nextG.d),oh=nextG.h,k=nextG.k,sm=nextG.s||nextG.ks;
 const pick=(T.picks||[]).find(p=>p.d.slice(0,10)===nextG.d.slice(0,10)&&(p.h===nextG.o||p.a===nextG.o));
 const kl=['П1','Х','П2'];
 const crest=(sl,cls)=>`<span class="nmc ${cls}">${tl(sl,`<span class="nmcr">${em(sl)}</span><b>${esc(nm(sl))}</b>`)}</span>`;
 document.getElementById('nextBox').innerHTML=`
  <div class="sec-head" data-rv><h2>Следующий матч</h2><p>${lgp(lg)}${L.name} · ${oh?'дома':'в гостях'}, время московское.</p></div>
  <article class="nmatch" data-rv aria-label="${esc(T.name)} — ${esc(nm(nextG.o))}, ${t.d} ${t.mon}, ${t.tm} МСК">
   <div class="nmteams">${crest(oh?ID:nextG.o,'a')}<span class="nmmid"><span class="nmdt"><b>${t.d} ${t.mon}</b><small>${t.wd}${t.tm?' · '+t.tm+' МСК':''}</small></span><span class="nmha ${oh?'h':'a'}">${oh?'Дома':'В гостях'}</span></span>${crest(oh?nextG.o:ID,'b')}</div>
   <div class="nmside">
    ${k?`<div class="nmline"><span class="sl">Линия на матч${sm?' · <em class="smp">пример</em>':''}</span>
      <ol class="kx" aria-label="Линия: ${esc(T.name)} ${kf(k[0])}, ничья ${kf(k[1])}, ${esc(nm(nextG.o))} ${kf(k[2])}">${k.map((v,i)=>`<li><b class="num">${kf(v)}</b><small>${kl[i]}</small></li>`).join('')}</ol></div>`
     :`<div class="nmline"><span class="sl">Линия появится ближе к матчу</span></div>`}
    <div class="nmcd" id="nmcd"><span class="sl">До начала</span><b class="num" id="nmcdv">—</b></div>
    ${pick?`<div class="nmpick"><span class="sl">Наш прогноз</span><b>${esc(String(pick.pick||'').replace(/(\d)\.(\d)/g,'$1,$2'))}</b><small>кэф ${esc(pick.k)}</small></div>`:''}
    <a class="btn btn-line nmgo" href="../hockey/index.html${THEME?'?theme='+encodeURIComponent(THEME):''}#matches">Разбор матча</a>
   </div>
  </article>
  <details class="nmh2h" id="nmh2h" hidden></details>`;
 document.getElementById('next').hidden=false;
 const cdv=document.getElementById('nmcdv'),st0=startMs(nextG.d);
 const tick=()=>{const df=st0-Date.now();
  if(isNaN(st0)||df<=0){cdv.textContent=isNaN(st0)?'—':'матч начался';return}
  const m=Math.floor(df/6e4),dd=Math.floor(m/1440),hh=Math.floor(m%1440/60),mm=m%60;
  cdv.innerHTML=(dd?`${dd}<small>${plural(dd,'день','дня','дней')}</small> `:'')+`${hh}<small>ч</small> ${mm}<small>мин</small>`};
 tick();setInterval(tick,30000);
}

/* ── 2б. тренды: «n из N» по сыгранным матчам сезона (без примера), последние 10 / весь сезон, все / дома / в гостях ── */
{const box=document.getElementById('trendsBox'),st={per:'l10',ven:'all'};
 const prevLoss=new Map();real.forEach((g,i)=>prevLoss.set(g,i>0&&real[i-1].gf<real[i-1].ga));
 const DEF=[
  {id:'t45',t:'Тотал больше 4,5',ok:g=>g.gf+g.ga>4.5},
  {id:'t55',t:'Тотал больше 5,5',ok:g=>g.gf+g.ga>5.5,keep:1},
  {id:'t65',t:'Тотал больше 6,5',ok:g=>g.gf+g.ga>6.5},
  {id:'win',t:'Победа в основное время',ok:g=>g.gf>g.ga&&!g.x},
  {id:'ot',t:'Матч дошёл до ОТ или буллитов',ok:g=>!!g.x},
  {id:'btts',t:'Обе команды забили',ok:g=>g.gf>0&&g.ga>0},
  {id:'sc3',t:'Забила 3 и больше',ok:g=>g.gf>=3},
  {id:'ga3',t:'Пропустила 3 и больше',ok:g=>g.ga>=3},
  {id:'bounce',t:'Победа после поражения',ok:g=>g.gf>g.ga,pre:g=>prevLoss.get(g)}];
 const calc=()=>{let a=real.filter(g=>st.ven==='all'||(st.ven==='home'?g.h:!g.h));if(st.per==='l10')a=a.slice(-10);
  let r=DEF.map(d=>{const s=d.pre?a.filter(d.pre):a;return {...d,N:s.length,n:s.filter(d.ok).length,seq:s.map(d.ok)}}).filter(x=>x.N>=5);
  // из линий тотала оставляем 5,5 и ту из двух других, что дальше от 50 %
  const tot=r.filter(x=>/^t[46]5$/.test(x.id)).sort((x,y)=>Math.abs(y.n/y.N-.5)-Math.abs(x.n/x.N-.5));
  const drop=new Set(tot.slice(1).map(x=>x.id));r=r.filter(x=>!drop.has(x.id)||x.keep);
  return {a,r:r.sort((x,y)=>Math.abs(y.n/y.N-.5)-Math.abs(x.n/x.N-.5)).slice(0,8)}};
 const unit={all:'',home:' домашних',away:' гостевых'};
 const draw=()=>{const {a,r}=calc(),scope=st.per==='l10'?`последних${unit[st.ven]}`:`${unit[st.ven]?unit[st.ven].trim()+' ':''}матчей сезона`;
  document.getElementById('trList').innerHTML=r.length?r.map(x=>{const txt=`${x.t} — ${x.n} из ${x.N} ${scope}`;
   return `<li class="tr" aria-label="${esc(txt)}"><span class="trt">${esc(x.t)}</span>
   <span class="trd" aria-hidden="true">${x.seq.map(v=>`<i class="${v?'y':'n'}"></i>`).join('')}</span>
   <span class="trn"><b class="num">${x.n} из ${x.N}</b><small>${esc(scope)}</small></span></li>`}).join('')
   :`<li class="tr none">Для такого среза мало сыгранных матчей — нужно хотя бы 5.</li>`};
 if(real.length>=5){
  box.innerHTML=`<div class="sec-head" data-rv><h2>Тренды</h2><p>Что чаще всего случается в матчах ${esc(T.name)} в этом сезоне. Кружок — один матч: заполнен, если тренд сошёлся; справа — свежие.</p></div>
   <div class="trctl" data-rv><div class="gfilter"><div class="seg" id="trPer" role="group" aria-label="Период"><button type="button" aria-pressed="true" data-v="l10">Последние 10</button><button type="button" aria-pressed="false" data-v="all">Весь сезон</button></div></div>
    <div class="gfilter"><div class="seg" id="trVen" role="group" aria-label="Где играли"><button type="button" aria-pressed="true" data-v="all">Все</button><button type="button" aria-pressed="false" data-v="home">Дома</button><button type="button" aria-pressed="false" data-v="away">В гостях</button></div></div></div>
   <ol class="trs" id="trList" data-rv></ol>`;
  document.getElementById('trends').hidden=false;
  for(const [id,key] of [['trPer','per'],['trVen','ven']])document.getElementById(id).addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
   st[key]=b.dataset.v;document.querySelectorAll('#'+id+' button').forEach(x=>x.setAttribute('aria-pressed',x===b));draw()});
  draw();
 }}

/* ── 2б². тоталы и дом/выезд: гистограммы по сыгранным матчам (без примеров), карточки «Дома | В гостях» ── */
{const box=document.getElementById('totalsBox'),sec=document.getElementById('totals'),st={per:'all',ven:'all'};
 if(box&&sec&&real.length>=5){
 const f1=v=>(Math.round(v*100)/100).toFixed(2).replace('.',','),pc=(n,N)=>N?Math.round(n/N*100)+'%':'—';
 const hist=(title,sub,vals,labels,lines,N,off=0)=>{
  const n=labels.length,cnt=labels.map((_,i)=>vals.filter(v=>Math.min(Math.max(v-off,0),n-1)===i).length),mx=Math.max(1,...cnt);
  const ln=lines.map(l=>{const k=vals.filter(v=>v>l.t).length;return {...l,k,txt:`больше ${String(l.t).replace('.',',')} — ${k} из ${N}`}});
  return `<figure class="hg" role="img" aria-label="${esc(title)}: ${esc(labels.map((l,i)=>l+' — '+cnt[i]).join(', '))}">
   <figcaption><b>${esc(title)}</b><small>${esc(sub)}</small></figcaption>
   <div class="hp" style="--n:${n}">${cnt.map((c,i)=>`<span class="hc"><i class="hb" style="height:${(c/mx*76).toFixed(1)}%"></i><b class="hn num" style="bottom:calc(${(c/mx*76).toFixed(1)}% + 3px)">${c}</b></span>`).join('')}
    ${ln.map(l=>`<span class="hl" style="left:${(l.pos/n*100).toFixed(2)}%"><em>${esc(String(l.t).replace('.',','))}</em></span>`).join('')}</div>
   <div class="hx" style="--n:${n}">${labels.map(l=>`<span>${esc(l)}</span>`).join('')}</div>
   <ul class="hlg">${ln.map(l=>`<li><i></i>${esc(l.txt)}</li>`).join('')}</ul></figure>`};
 const draw=()=>{
  let a=real.filter(g=>st.ven==='all'||(st.ven==='home'?g.h:!g.h));if(st.per==='l10')a=a.slice(-10);
  const N=a.length,scope=st.per==='l10'?`последних ${N}`:`${N}`,unit={all:'матчей',home:'домашних матчей',away:'гостевых матчей'}[st.ven];
  const tot=a.map(g=>g.gf+g.ga),avgT=N?tot.reduce((x,y)=>x+y,0)/N:0,avgF=N?a.reduce((x,g)=>x+g.gf,0)/N:0,avgA=N?a.reduce((x,g)=>x+g.ga,0)/N:0;
  const short=N<3;
  const sub=`${scope} ${unit}`;
  document.getElementById('tsOut').innerHTML=short?`<p class="tsnone">Для такого среза мало сыгранных матчей.</p>`:`
   <div class="tsbig"><div><b class="num">${f1(avgT)}</b><span>средний тотал матча</span></div><div><b class="num">${f1(avgF)}</b><span>забивает ${esc(T.name)} за игру</span></div><div><b class="num">${f1(avgA)}</b><span>пропускает за игру</span></div></div>
   <div class="hgs">
    ${hist('Сколько шайб в матчах',sub,tot,['2 и меньше','3','4','5','6','7','8 и больше'],[{t:4.5,pos:3},{t:5.5,pos:4},{t:6.5,pos:5}],N,2)}
    ${hist(`Сколько забивает ${T.name}`,sub,a.map(g=>g.gf),['0','1','2','3','4','5+'],[{t:2.5,pos:3},{t:3.5,pos:4}],N)}
    ${hist('Сколько пропускает',sub,a.map(g=>g.ga),['0','1','2','3','4','5+'],[],N)}
   </div>`};
 box.innerHTML=`<div class="sec-head" data-rv><h2>Тоталы и дом/выезд</h2><p>Сколько шайб падает в матчах ${esc(T.name)} и чем отличается игра дома и в гостях. Только сыгранные матчи сезона.</p></div>
  <div class="trctl" data-rv><div class="gfilter"><div class="seg" id="tsPer" role="group" aria-label="Период"><button type="button" aria-pressed="true" data-v="all">Весь сезон</button><button type="button" aria-pressed="false" data-v="l10">Последние 10</button></div></div>
   <div class="gfilter"><div class="seg" id="tsVen" role="group" aria-label="Где играли"><button type="button" aria-pressed="true" data-v="all">Все</button><button type="button" aria-pressed="false" data-v="home">Дома</button><button type="button" aria-pressed="false" data-v="away">В гостях</button></div></div></div>
  <div id="tsOut" data-rv></div>
  <h3 class="dvh" data-rv>Дома и в гостях</h3><div class="dvg" id="haBox" data-rv></div>`;
 sec.hidden=false;
 for(const [id,key] of [['tsPer','per'],['tsVen','ven']])document.getElementById(id).addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
  st[key]=b.dataset.v;document.querySelectorAll('#'+id+' button').forEach(x=>x.setAttribute('aria-pressed',x===b));draw()});
 // карточки дом/выезд — по всему сезону
 const side=h=>{const a=real.filter(g=>!!g.h===h),N=a.length,w=a.filter(g=>g.gf>g.ga),l=a.filter(g=>g.gf<g.ga),wo=w.filter(g=>g.x).length,lo=l.filter(g=>g.x).length;
  const gf=N?a.reduce((x,g)=>x+g.gf,0)/N:0,ga=N?a.reduce((x,g)=>x+g.ga,0)/N:0,tt=N?a.reduce((x,g)=>x+g.gf+g.ga,0)/N:0,o55=a.filter(g=>g.gf+g.ga>5.5).length;
  return {N,w:w.length,l:l.length,wo,lo,wp:N?w.length/N:0,gf,ga,tt,o55p:N?o55/N:0,o55,form:a.slice(-5)}};
 const H=side(true),A=side(false);
 const best=(k,hi)=>H.N&&A.N&&H[k]!==A[k]?((H[k]>A[k])===hi?'h':'a'):'';
 const rows=[['Матчей',s=>s.N,null],['Победы–поражения',s=>`${s.w}–${s.l}`,null,s=>`в том числе ОТ/Б: ${s.wo} поб., ${s.lo} пор.`],['Побед, %',s=>pc(s.w,s.N),'wp',null,1],['Забито за игру',s=>f1(s.gf),'gf',null,1],['Пропущено за игру',s=>f1(s.ga),'ga',null,0],['Средний тотал',s=>f1(s.tt),null],['Тотал больше 5,5, % матчей',s=>pc(s.o55,s.N),null,s=>`${s.o55} из ${s.N}`]];
 const card=(s,nm,cls)=>`<article class="dvc ${cls}" aria-label="${nm}"><h4>${nm}</h4><dl>${rows.map(([t,fn,k,sm,hi])=>{const bst=k&&best(k,!!hi)===(cls==='h'?'h':'a');
  return `<div class="${bst?'bst':''}"><dt>${esc(t)}</dt><dd><b class="num">${esc(fn(s))}</b>${sm?`<small>${esc(sm(s))}</small>`:''}</dd></div>`}).join('')}</dl>
  <div class="dvf"><span>Форма, последние 5</span><span class="dvd">${s.form.map(g=>`<i class="${g.gf>g.ga?'y':'n'}" title="${esc(g.gf+':'+g.ga+(g.x?' ОТ/Б':''))}" aria-label="${g.gf>g.ga?'победа':'поражение'} ${esc(g.gf+':'+g.ga)}"></i>`).join('')||'—'}</span></div></article>`;
 document.getElementById('haBox').innerHTML=card(H,'Дома','h')+card(A,'В гостях','a');
 draw();
 }else if(sec)sec.hidden=true}

/* ── 2в. сравнение с соперником следующего матча: наложенный шестиугольник силы, статистика бок о бок, матчи этого сезона ── */
if(nextG){
 const o=nextG.o,O=D.teams[o];
 const old=((T.h2h||{})[o]||[]).map(r=>({gf:r[2],ga:r[3]}));
 const cur=real.filter(g=>g.o===o);                       // текущий сезон, сыгранные (без примеров)
 const hasOld=!!T.h2h;
 const rec=a=>{const w=a.filter(g=>g.gf>g.ga).length;return [w,a.length-w]};
 const [cw,cl]=rec(cur),[tw,tl_]=rec(old.concat(cur));
 const tot=old.length+cur.length;
 const clubCol=id=>palette((window.JV_CLUBS||{})[id]||(D.teams[id].colors||['#1b2a44','#0b1220','#3ee0ff'])).accL;
 const c1=clubCol(ID),c2=clubCol(o);
 const near=Math.hypot(...rgb(c1).map((v,i)=>v-rgb(c2)[i]))<110;
 const nT=esc(T.name),nO=esc(nm(o));
 // — сводка в шапке: «В–П» этого сезона и за 3 сезона —
 const sumCur=cur.length?`в этом сезоне ${cw}–${cl}`:'в этом сезоне ещё не встречались';
 const sumAll=hasOld&&tot?` · за 3 сезона ${tw}–${tl_}`:(hasOld?' · за 3 сезона не встречались':'');
 // — 1. наложенный шестиугольник —
 const A2=O.axes||[];
 const rad=`<div class="cmpad"><div class="rad">${radar([{v:T.axes||[],c:c1,name:T.name},{v:A2,c:c2,name:nm(o),dash:near}],ax)}</div>
  <div class="legend cmpleg"><span>${em(ID)}<b style="color:${c1}">${nT}</b></span><span>${em(o)}<b style="color:${c2}">${nO}</b></span><span><i class="d"></i>середина лиги</span></div></div>`;
 // — 2. статистика бок о бок —
 const nn=v=>v!=null&&!Number.isNaN(+v);
 const sgn=v=>v>0?'+'+v:v<0?'−'+Math.abs(v):'0';
 const stk=t=>{const a=t.games.filter(g=>g.gf!=null).sort((x,y)=>String(x.d).localeCompare(String(y.d)));let n=0,w=null;
  for(let i=a.length-1;i>=0;i--){const win=a[i].gf>a[i].ga;if(w===null)w=win;if(win!==w)break;n++}return {n,win:w}};
 const sT=stk(T),sO=stk(O);
 const rT=T.raw||[],rO=O.raw||[];
 const fm=t=>nn(t.l10s)||t.l10s?esc(t.l10s):(nn(t.l10)?`${t.l10} ${plural(t.l10,'очко','очка','очков')}`:null);
 const pc=r=>lg==='nhl'?f(r*100,1)+'%':f(r);
 // [подпись, значение клуба, значение соперника, число клуба, число соперника, лучше (1 — больше, -1 — меньше, 0 — не сравниваем)]
 const rows=[];
 const add=(lab,a,b,x,y,dir)=>{if(a!=null&&b!=null)rows.push([lab,a,b,x,y,dir])};
 const confNote=O.conf!==conf?t=>`<small>${esc(t.conf)}</small>`:()=>'';
 add('Место в конференции',`${T.place}-е${confNote(T)}`,`${O.place}-е${confNote(O)}`,T.place,O.place,-1);
 add('Очки',T.pts,O.pts,T.pts,O.pts,1);
 add('Игры',T.gp,O.gp,0,0,0);
 add('Победы–поражения',`${T.w}–${T.l}`,`${O.w}–${O.l}`,T.w/T.gp,O.w/O.gp,1);
 add('Очки за игру',f(T.pts/T.gp),f(O.pts/O.gp),T.pts/T.gp,O.pts/O.gp,1);
 add('Забито за игру',f(T.gf/T.gp),f(O.gf/O.gp),T.gf/T.gp,O.gf/O.gp,1);
 add('Пропущено за игру',f(T.ga/T.gp),f(O.ga/O.gp),T.ga/T.gp,O.ga/O.gp,-1);
 add('Разница шайб',sgn(T.gf-T.ga),sgn(O.gf-O.ga),T.gf-T.ga,O.gf-O.ga,1);
 if(fm(T)&&fm(O))add('Форма: последние 10',fm(T),fm(O),nn(T.l10)?T.l10:0,nn(O.l10)?O.l10:0,nn(T.l10)&&nn(O.l10)?1:0);
 if(nn(rT[3])&&nn(rO[3]))add(lg==='nhl'?'Большинство, реализация':'Большинство, голов за игру',pc(rT[3]),pc(rO[3]),rT[3],rO[3],1);
 if(nn(rT[4])&&nn(rO[4]))add(lg==='nhl'?'Меньшинство, нейтрализация':'Меньшинство, пропущено за игру',pc(rT[4]),pc(rO[4]),rT[4],rO[4],lg==='nhl'?1:-1);
 if(sT.n>=3||sO.n>=3){const sf=s=>s.n>=3?`${s.n} ${s.win?plural(s.n,'победа','победы','побед'):plural(s.n,'поражение','поражения','поражений')}`:'—';
  add('Серия',sf(sT),sf(sO),0,0,0)}
 const cell=(v,x,y,dir,c,side)=>{const mine=side?y:x,his=side?x:y,w=dir&&Math.abs(mine-his)>1e-9&&(dir>0?mine>his:mine<his);
  return `<td class="${w?'lead':''}"${w?` style="--c:${c}"`:''}><span class="num">${v}</span></td>`};
 const tbl=`<table class="cmpt"><caption class="sr">Статистика сезона: ${nT} и ${nO}</caption>
  <thead><tr><th scope="col" class="cl">Показатель</th><th scope="col" style="--c:${c1}">${em(ID)}<span>${nT}</span></th><th scope="col" style="--c:${c2}">${em(o)}<span>${nO}</span></th></tr></thead>
  <tbody>${rows.map(r=>`<tr><th scope="row" class="cl">${esc(r[0])}</th>${cell(r[1],r[3],r[4],r[5],c1,0)}${cell(r[2],r[3],r[4],r[5],c2,1)}</tr>`).join('')}</tbody></table>`;
 // — 3. матчи этого сезона между командами —
 const item=(g,nx)=>{const t=day(g.d),h=g.h,r=nx?null:rlab(g);return `<li class="g h2g ${nx?'nx ':''}${h?'home':'away'}"><span class="gd"><b>${t.d} ${t.mon}</b><small>${t.wd}${nx&&t.tm?' · '+t.tm+' МСК':''}</small></span>
  <span class="ha ${h?'h':'a'}" title="${h?'дома':'в гостях'}">${h?'Д':'В'}</span><span class="hv">${h?'Дома':'В гостях'}</span>
  ${nx?`<span class="rs nxt">следующий</span>`:`<span class="sc num">${g.gf}:${g.ga}${g.x?`<small>${esc(g.x)}</small>`:''}</span><span class="rs ${r[1]}" title="${r[2]}">${r[0]}</span>`}</li>`};
 const mt=cur.length?`<ol class="gs h2l">${cur.map(g=>item(g,0)).join('')}${item(nextG,1)}</ol>`
  :`<p class="cmpno">В этом сезоне ещё не встречались.</p><ol class="gs h2l">${item(nextG,1)}</ol>`;
 const allSum=hasOld&&tot?`<p class="note cmpall">За 3 сезона: ${tw}–${tl_} в ${tot} ${plural(tot,'матче','матчах','матчах')}. Счёт — с точки зрения ${nT}.</p>`:(hasOld?`<p class="note cmpall">За 3 сезона команды не встречались.</p>`:'');
 const dt=document.getElementById('nmh2h');
 dt.innerHTML=`<summary><span class="h2cr">${em(ID)}${em(o)}</span><span class="h2st"><b>Сравнение: ${nT} — ${nO}</b>
   <small>${sumCur}${sumAll}</small></span><span class="h2ar" aria-hidden="true">▾</span></summary>
  <div class="h2in cmp">
   <section class="cmps"><h3>Сила команд</h3><p class="note">Те же шесть показателей, что в шестиугольнике выше: балл — место в лиге, 100 — лучшая команда.${near?' Цвета клубов близки, поэтому '+nO+' — пунктиром.':''}</p>${rad}</section>
   <section class="cmps"><h3>Статистика сезона</h3><div class="cmpw" tabindex="0" role="region" aria-label="Статистика команд, листается вбок">${tbl}</div><p class="note">Выделено более сильное значение.</p></section>
   <section class="cmps"><h3>Матчи этого сезона</h3>${mt}${allSum}</section>
  </div>`;
 dt.hidden=false;
}

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
/* фото лидеров в плашке «Игроки» — из данных раздела «Игроки» (подгружаются после страницы) */
fetch(T.lg==='nhl'?'../hockey/data/nhl_players.json':'../hockey/data/khl_players.json').then(r=>r.ok?r.json():null).then(j=>{if(!j)return;
 const by={};j.players.forEach(p=>{by[p.n]=p});
 document.querySelectorAll('.plcard .pav').forEach(el=>{const p=by[el.dataset.n];if(p&&p.img){const im=new Image();im.alt='';im.onload=()=>{el.textContent='';el.appendChild(im)};im.src=p.img}})}).catch(()=>{});
})();
