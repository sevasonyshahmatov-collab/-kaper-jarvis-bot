/* Профиль хоккеиста: hockey/player.html?lg=nhl|khl&id=<id>.
   Данные — один маленький файл hockey/data/pp/<лига>/<id>.json (его режет daily/split.py), клубы — assets/data/teams-lite.js,
   следующий матч: data/today.js (+ lines.js, model.js только если этот матч в окне «сегодня–завтра»). */
(()=>{
const Q=new URLSearchParams(location.search),LG=Q.get('lg')==='khl'?'khl':'nhl',ID=(Q.get('id')||'').replace(/\D/g,'').slice(0,9);
const MAIN=document.getElementById('main');
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const TT=(window.JV_TEAMS&&JV_TEAMS.teams)||{};
const tn=s=>(TT[s]&&TT[s].name)||s;
const em=s=>`../assets/em/${encodeURIComponent(s)}.webp`;
const mmss=s=>s?`${Math.floor(s/60)}:${String(Math.round(s%60)).padStart(2,'0')}`:'—';
const ddmm=d=>d.slice(8,10)+'.'+d.slice(5,7);
const MON=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
const POS={C:'Центр',L:'Левый нападающий',R:'Правый нападающий',D:'Защитник',F:'Нападающий',G:'Вратарь'};
const pl=(n,a,b,c)=>{n=Math.abs(n)%100;const k=n%10;return n>10&&n<20?c:k===1?a:k>1&&k<5?b:c};
const err=m=>{MAIN.innerHTML=`<p class="pp-err">${m} <a href="${LG==='khl'?'players_khl.html':'players.html'}">К списку игроков</a></p>`};
/* цвет клуба: слишком светлый (жёлтый Бостона) притемняем, чтобы белый текст читался */
const shade=h=>{const m=/^#([0-9a-f]{6})$/i.exec(h||'');if(!m)return '#3a4a6a';const n=parseInt(m[1],16),r=n>>16,g=n>>8&255,b=n&255;
 const L=(.2126*r+.7152*g+.0722*b)/255;if(L<=.5)return h;const k=.5/L;return '#'+[r,g,b].map(v=>Math.round(v*k).toString(16).padStart(2,'0')).join('')};
const MK=[
 {k:'pt',n:'Гол+пас',w:'очко',f:r=>r[3]+r[4]>0,v:r=>r[3]+r[4]},
 {k:'g',n:'Гол',w:'гол',f:r=>r[3]>0,v:r=>r[3]},
 {k:'a',n:'Пас',w:'передачи',f:r=>r[4]>0,v:r=>r[4]},
 {k:'s3',n:'Броски',w:'броски в створ',f:r=>(r[5]||0)>0,v:r=>r[5]||0,nhl:1}];
/* Шестиугольник (НХЛ) / пятиугольник (КХЛ) навыков: P.sk = [[ось, 0–100]] — процентиль среди игроков лиги той же группы (split.py) */
const radar=sk=>{if(!sk||sk.length<3)return'';const n=sk.length,R=120,C=170,pt=(i,r)=>{const a=-Math.PI/2+i*2*Math.PI/n;return[C+r*Math.cos(a),C+r*Math.sin(a)]},
 poly=r=>sk.map((_,i)=>pt(i,r).map(v=>v.toFixed(1)).join(',')).join(' ');
 const grid=[.25,.5,.75,1].map(f=>`<polygon class="gr" points="${poly(R*f)}"/>`).join('')+sk.map((_,i)=>{const[x,y]=pt(i,R);return`<line class="gr" x1="${C}" y1="${C}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}"/>`}).join('');
 const val=sk.map(([,v],i)=>pt(i,R*Math.max(.04,Math.min(1,(v-45)/55))).map(x=>x.toFixed(1)).join(',')).join(' ');
 const lab=sk.map(([nm,v],i)=>{const[x,y]=pt(i,R+30),an=Math.abs(x-C)<8?'middle':x>C?'start':'end';return`<text x="${x.toFixed(1)}" y="${(y-6).toFixed(1)}" text-anchor="${an}" class="ax">${esc(nm)}</text><text x="${x.toFixed(1)}" y="${(y+14).toFixed(1)}" text-anchor="${an}" class="vl">${v}</text>`}).join('');
 return `<section class="pp-sec" aria-labelledby="h-k"><h2 id="h-k">Навыки</h2><div class="pp-sk"><svg viewBox="-120 0 580 345" role="img" aria-label="${esc(sk.map(([a,v])=>a+' '+v).join(', '))}">${grid}<polygon class="vv" points="${val}"/>${sk.map(([,v],i)=>{const[x,y]=pt(i,R*Math.max(.04,Math.min(1,(v-45)/55)));return`<circle class="dt" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4.5"/>`}).join('')}${lab}</svg></div></section>`};
if(!ID){err('Не указан игрок.');return}
fetch(`data/pp/${LG}/${ID}.json`).then(r=>{if(!r.ok)throw 0;return r.json()}).then(P=>{
 const T=TT[P.t]||{},col=shade((T.colors||[])[0]);
 const log=P.log||[],nhl=LG==='nhl',N=log.length;
 const G=log.reduce((s,r)=>s+r[3],0),A=log.reduce((s,r)=>s+r[4],0);
 const sog=P.ssog!=null?P.ssog:log.reduce((s,r)=>s+(r[5]||0),0),pim=P.spim!=null?P.spim:log.reduce((s,r)=>s+(r[7]||0),0);
 const gp=nhl?(P.sgp||N):(P.sgp||P.gp||N);
 /* имена НХЛ и КХЛ — латиницей «Имя [И.] Фамилия» (09.11): крупно фамилия */
 const parts=P.n.split(/\s+/),k=parts.length>2&&/\.$/.test(parts[1])?2:1,big=parts.slice(k).join(' ')||P.n,small=parts.length>1?parts.slice(0,k).join(' '):'';
 const ini=parts.map(w=>w[0]).slice(0,2).join('').toUpperCase();
 document.title=`${P.n} — профиль хоккеиста · JARVIS`;
 const mkList=MK.filter(m=>!m.nhl||nhl);
 /* «n из N»: КХЛ-приложение не отдаёт, кто играл в матче, — лог содержит все матчи клуба, N в сезоне берём по играм игрока */
 const hit=(arr,m,season)=>{const k=arr.filter(m.f).length;return[k,(season&&!nhl)?Math.max(gp,k):arr.length]};
 const cell=(h)=>h[1]?`<td><b>${h[0]}</b> из ${h[1]}<small>${Math.round(100*h[0]/h[1])}%</small><span class="mb"><i style="width:${Math.round(100*h[0]/h[1])}%"></i></span></td>`:'<td class="na">—</td>';
 const L10=log.slice(-10),HM=log.filter(r=>r[2]===1),AW=log.filter(r=>r[2]===0);
 const tile=(l,v)=>`<div class="pp-tile"><span>${l}</span><b>${v}</b></div>`;
 const tiles=[tile('Игры',gp),tile('Голы',G),tile('Передачи',A),tile('Очки',G+A)];
 if(nhl||P.ssog!=null)tiles.push(tile('Броски',sog));
 if(P.ts)tiles.push(tile('Время на льду',mmss(P.ts)));
 if(P.spm!=null)tiles.push(tile('Плюс/минус',P.spm>0?'+'+P.spm:P.spm<0?'−'+Math.abs(P.spm):'0'));
 tiles.push(tile('Штраф, мин',pim));
 const lgName=nhl?'НХЛ':'КХЛ';
 const teamHref=`../team/index.html?id=${encodeURIComponent(P.t)}`;
 const photo=P.img?`<img class="ph" src="${esc(P.img)}" alt="${esc(P.n)}" onerror="this.parentNode.classList.add('nop');this.remove()">`:'';
 let html=`<article class="pp-hero" aria-label="${esc(P.n)}">
  ${P.no!=null?`<span class="pp-no" aria-hidden="true">${esc(P.no)}</span>`:''}
  <span class="pp-wm" aria-hidden="true">${esc(tn(P.t))}</span><img class="pp-ghost" src="${em(P.t)}" alt="" aria-hidden="true" onerror="this.remove()">
  <div class="pp-txt">
   <p class="pp-crumbs"><a href="${teamHref}" title="Страница клуба"><img src="${em(P.t)}" alt="" onerror="this.remove()">${esc(tn(P.t))}</a><a class="lg" href="league.html?lg=${LG}" title="Страница лиги">${lgName}</a><a class="lg" href="compare.html?t=players&a=${LG}-${ID}" title="Сравнить с другим игроком">Сравнить</a></p>
   <p class="pp-pos">${esc(POS[P.pos]||P.pos||'')}${P.no!=null?' · №'+esc(P.no):''}</p>
   <h1>${small?esc(small)+' ':''}<b${String(big).length>9?` style="--fz:${(9/String(big).length).toFixed(3)}"`:''}>${esc(big)}</b></h1>
   <p class="pp-sub">${G}+${A}=${G+A} в ${gp} ${pl(gp,'матче','матчах','матчах')} сезона</p>
   <p class="pp-meta">${P.no!=null?`<span><b>#${esc(P.no)}</b></span>`:''}<span>${esc(POS[P.pos]||P.pos||'')}</span><span>${lgName}, сезон 2026/27</span></p>
   <dl class="pp-hs" aria-label="Сезон: ${gp} ${pl(gp,'игра','игры','игр')}, ${G}+${A}"><div><b>${gp}</b><span>${pl(gp,'игра','игры','игр')}</span></div><div><b>${G}</b><span>голы</span></div><div><b>${A}</b><span>передачи</span></div><div><b>${G+A}</b><span>очки</span></div></dl>
  </div>
  <div class="pp-photo${P.img?'':' nop'}"><span class="pp-ini" aria-hidden="true">${esc(ini)}</span>${photo}</div>
 </article>
 <section class="pp-sec" id="s-season" aria-labelledby="h-s"><h2 id="h-s">Сезон</h2><div class="pp-tiles">${tiles.join('')}</div></section>${radar(P.sk)}
 <section class="pp-sec" id="s-mk" aria-labelledby="h-m"><h2 id="h-m">В скольких матчах</h2>
  <table class="pp-mk"><thead><tr><th scope="col">Рынок</th><th scope="col">Сезон</th><th scope="col">Последние 10</th><th scope="col">Дома</th><th scope="col">В гостях</th></tr></thead><tbody>
  ${mkList.map(m=>`<tr><th scope="row">${m.n}</th>${cell(hit(log,m,1))}${cell(hit(L10,m))}${cell(HM.length?hit(HM,m):[0,0])}${cell(AW.length?hit(AW,m):[0,0])}</tr>`).join('')}
  </tbody></table></section>
 <section class="pp-sec" id="s-form" aria-labelledby="h-f"><h2 id="h-f">Форма</h2>
  <div class="pp-tabs" id="tabs" role="group" aria-label="Рынок графика">${mkList.map((m,i)=>`<button type="button" data-k="${m.k}" aria-pressed="${!i}">${m.n}</button>`).join('')}</div>
  <div class="pp-chart" id="chart" role="img" aria-label="Форма по последним матчам"></div></section>
 <section class="pp-sec" id="s-next" aria-labelledby="h-n"><h2 id="h-n">Следующий матч</h2><div id="next" class="pp-nx"></div></section>
 <section class="pp-sec" id="s-games" aria-labelledby="h-g"><h2 id="h-g">Все матчи сезона</h2>
  <div class="pp-wrap"><table class="pp-gm"><thead><tr><th scope="col" class="res"><span class="sr">Результат</span></th><th scope="col">Дата</th><th scope="col">Соперник</th><th scope="col" class="ct">Г+П</th>${nhl?'<th scope="col" class="rt br">Бр</th><th scope="col" class="rt tm">Время</th>':''}<th scope="col" class="rt">Счёт</th></tr></thead><tbody>
  ${log.slice().reverse().map(r=>{const sc=r[8],w=sc&&sc[0]>sc[1];return `<tr><td class="res">${sc?`<b class="${w?'w':'l'}">${w?'В':'П'}</b>`:''}</td><td>${ddmm(r[0])}</td><td><a class="op" style="color:inherit;text-decoration:none" href="../team/index.html?id=${encodeURIComponent(r[1])}"><img src="${em(r[1])}" alt="" loading="lazy" onerror="this.remove()"><span>${esc(tn(r[1]))}<small>${r[2]?'дома':'в гостях'}</small></span></a></td><td class="ct pt"><b class="${r[3]+r[4]>0?'g':''}">${r[3]}+${r[4]}</b></td>${nhl?`<td class="rt br">${r[5]??'—'}</td><td class="rt tm">${mmss(r[6])}</td>`:''}<td class="rt sc">${sc?`<span class="sg"><small>${sc[2]?esc(sc[2]):''}</small><i>${sc[0]}</i><u>:</u><i>${sc[1]}</i></span>`:'—'}</td></tr>`}).join('')}
  </tbody></table></div></section>
 <div class="pp-cta"><p>Разборы матчей и прогнозы по хоккею — в нашем Telegram-канале.</p><a href="https://t.me/jarvibet" target="_blank" rel="noopener">Получать прогнозы — бесплатно</a></div>`;
 MAIN.innerHTML=html;
 MAIN.style.setProperty('--c',col);
 /* клубные цвета профиля (06.11): переменные --kb… из club/jersey.js; --kg — акцент для графиков на фоне страницы */
 const JY=window.JV_JERSEY,jc=JY&&JY.calc(P.t);
 if(jc){
  JY.vars(P.t).split(';').forEach(d=>{const i=d.indexOf(':');MAIN.style.setProperty(d.slice(0,i),d.slice(i+1))});
  let bg='#0b1626';try{const m=/(\d+)\D+(\d+)\D+(\d+)/.exec(getComputedStyle(document.body).backgroundColor);if(m)bg='#'+[1,2,3].map(i=>(+m[i]).toString(16).padStart(2,'0')).join('')}catch(e){}
  const a=JY.pick(P.t,bg);MAIN.style.setProperty('--kg',a.g);MAIN.style.setProperty('--kgo',a.go);
  MAIN.classList.add('k');if(jc.lt)MAIN.classList.add('lt');
  if(Q.get('hero')!=='old')MAIN.classList.add('x');
 }
 /* полоса игрока под шапкой сайта: появляется, когда шапка профиля ушла вверх (12.11, по образцу nhl.com) */
 {const hero=MAIN.querySelector('.pp-hero'),hd=document.getElementById('hd'),bar=document.createElement('div');
  bar.className='pp-stick';bar.setAttribute('aria-hidden','true');
  ['--kb','--ko','--ko2','--ks','--kt'].forEach(v=>{const x=MAIN.style.getPropertyValue(v);if(x)bar.style.setProperty(v,x)});
  bar.innerHTML=`<div class="wrap"><span class="pps-wm">${esc(tn(P.t))}</span>${P.img?`<img class="pps-ph" src="${esc(P.img)}" alt="" onerror="this.remove()">`:''}
   <div class="pps-who"><b>${esc(P.n)}</b><span>${P.no!=null?'#'+esc(P.no)+' · ':''}${esc(POS[P.pos]||P.pos||'')} · ${esc(tn(P.t))}</span></div>
   <div class="pps-st"><div><b>${gp}</b><span>игр</span></div><div><b>${G}</b><span>голы</span></div><div><b>${A}</b><span>пас</span></div><div><b>${G+A}</b><span>очки</span></div></div>
   <nav><a href="#s-season" tabindex="-1">Сезон</a><a href="#s-mk" tabindex="-1">Рынки</a><a href="#s-form" tabindex="-1">Форма</a><a href="#s-next" tabindex="-1">Следующий матч</a><a href="#s-games" tabindex="-1">Матчи</a></nav>
   <img class="pps-em" src="${em(P.t)}" alt="" onerror="this.remove()"></div>`;
  document.body.appendChild(bar);
  const fit=()=>bar.style.setProperty('--hdh',(hd?hd.offsetHeight:64)+'px');fit();addEventListener('resize',fit);
  if(hero&&'IntersectionObserver'in window)new IntersectionObserver(([e])=>{fit();bar.classList.toggle('on',!e.isIntersecting&&e.boundingClientRect.top<0)},{rootMargin:'-70px 0px 0px 0px'}).observe(hero);
 }
 /* график */
 const chart=document.getElementById('chart');
 const draw=k=>{const m=mkList.find(x=>x.k===k)||mkList[0],R=log.slice(-15),mx=Math.max(k==='s3'?4:2,...R.map(m.v));
  chart.innerHTML=R.map(r=>{const v=m.v(r),ok=m.f(r),tip=`${ddmm(r[0])}, ${r[2]?'дома':'в гостях'}, ${tn(r[1])}: ${r[3]}+${r[4]}${nhl?', бросков '+(r[5]||0):''}`;
   return `<div class="pp-col" title="${esc(tip)}"><div class="bar${ok?' g':''}" style="--h:${Math.max(.04,v/mx)}">${v>0?`<b>${v}</b>`:''}</div><img class="em" src="${em(r[1])}" alt="${esc(tn(r[1]))}" loading="lazy" onerror="this.outerHTML='<span class=fb>${esc(tn(r[1]).slice(0,3).toUpperCase())}</span>'"><small>${r[2]?'':'@'}${r[0].slice(8,10)}<i>.${r[0].slice(5,7)}</i></small></div>`}).join('');
  chart.setAttribute('aria-label',`${m.n}: ${R.map(r=>`${ddmm(r[0])} ${tn(r[1])} — ${m.v(r)}`).join('; ')}`);
  document.querySelectorAll('#tabs button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.k===m.k))};
 document.getElementById('tabs').onclick=e=>{const b=e.target.closest('button');if(b)draw(b.dataset.k)};
 draw(mkList[0].k);
 nextMatch(P);
}).catch(()=>err('Игрок не найден или данные ещё не собраны.'));

function nextMatch(P){
 const box=document.getElementById('next');let nx=P.nx;
 /* матч из данных уже прошёл (данные от утра) — ищем следующий в today.js, иначе «не объявлен» (аудит 08.11) */
 const past=n=>n&&Date.parse(n.d.slice(0,16).replace(' ','T')+':00+03:00')<Date.now()-3*3600e3;
 if(past(nx)){
  const T=((window.JV_TODAY||{}).matches||[]).filter(m=>(m.h===P.t||m.a===P.t)&&Date.parse(m.t.replace(' ','T')+':00+03:00')>Date.now()-3*3600e3).sort((a,b)=>a.t<b.t?-1:1)[0];
  if(T){nextMatch(Object.assign({},P,{nx:{d:T.t,h:T.h===P.t,o:T.h===P.t?T.a:T.h}}));return}
  if(!window.JV_TODAY&&!P._lt){const s=document.createElement('script');s.src='../data/today.js';s.onload=s.onerror=()=>nextMatch(Object.assign({},P,{_lt:1}));document.head.appendChild(s);return}
  nx=null;
 }
 if(!nx){box.innerHTML='<p class="hint" style="margin:0">Ближайший матч клуба пока не объявлен.</p>';return}
 const d=nx.d,when=`${+d.slice(8,10)} ${MON[+d.slice(5,7)-1]}, ${d.slice(11,16)} МСК`;
 const hs=nx.h?P.t:nx.o,as=nx.h?nx.o:P.t,key=`${LG}|${d.slice(0,10)}|${hs}|${as}`;
 box.innerHTML=`<div class="vs"><a class="cl" href="../team/index.html?id=${encodeURIComponent(nx.o)}"><img src="${em(nx.o)}" alt="" onerror="this.remove()"></a>
  <a class="cl" href="../team/index.html?id=${encodeURIComponent(nx.o)}"><b>${nx.h?'Дома':'В гостях'} — ${esc(tn(nx.o))}</b><span>${when}</span></a></div><div id="nxl"></div>`;
 const load=src=>new Promise(ok=>{const s=document.createElement('script');s.src=src;s.onload=s.onerror=()=>ok();document.head.appendChild(s)});
 load('../data/today.js').then(()=>{
  const m=((window.JV_TODAY||{}).matches||[]).find(x=>x.key===key);if(!m)return;
  return Promise.all([load('../data/lines.js'),load('../data/model.js')]).then(()=>{
   const ln=(window.JV_LINES||{})[key],md=(window.JV_MODEL||{})[key];if(!ln&&!md)return;
   const f2=v=>v==null?'—':(+v).toFixed(2),pc=v=>v==null?'—':Math.round(v*100)+'%';
   const hn=tn(hs),an=tn(as);let h='';
   if(ln)h+=`<div><h3>Линия</h3><div class="row"><span>${esc(hn)}</span><b>${f2(ln.p1)}</b></div>${ln.x!=null?`<div class="row"><span>Ничья</span><b>${f2(ln.x)}</b></div>`:''}<div class="row"><span>${esc(an)}</span><b>${f2(ln.p2)}</b></div>${ln.tot!=null?`<div class="row"><span>Тотал ${ln.tot}: больше / меньше</span><b>${f2(ln.over)} / ${f2(ln.under)}</b></div>`:''}</div>`;
   if(md)h+=`<div><h3>Модель JARVIS · основное время</h3><div class="row"><span>${esc(hn)}</span><b>${pc(md.p1)}</b></div>${md.x!=null?`<div class="row"><span>Ничья</span><b>${pc(md.x)}</b></div>`:''}<div class="row"><span>${esc(an)}</span><b>${pc(md.p2)}</b></div>${md.w1!=null?`<div class="row"><span>С учётом ОТ и буллитов</span><b>${pc(md.w1)} / ${pc(md.w2)}</b></div>`:''}${md.over!=null&&md.tot!=null?`<div class="row"><span>Тотал ${md.tot} больше</span><b>${pc(md.over)}</b></div>`:''}</div>`;
   document.getElementById('nxl').innerHTML=`<div class="pp-ln">${h}</div><p class="pp-note">Справочные данные матча, не рекомендация.</p>`})});
}
})();
