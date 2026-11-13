/* Профиль футболиста (13.11, по образцу хоккейного assets/player.js): football/player.html?id=<id ESPN>.
   Данные — football/data/pp/<id>.json (режет football/players_build.py из составов ESPN), клубы — football/data/football-club.js.
   log: [дата, соперник, дома 1/0, забил клуб, пропустил, в старте 1/0, минуты, голы, передачи, удары, в створ, жёлт., красн., турнир] */
(()=>{
const Q=new URLSearchParams(location.search),ID=(Q.get('id')||'').replace(/\D/g,'').slice(0,12);
const MAIN=document.getElementById('main');
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const F=window.JV_FOOT||{},TT=F.teams||{},LGS=F.leagues||{};
const tn=s=>(TT[s]&&TT[s].n)||s||'—';
const lgn=k=>(LGS[k]&&(LGS[k].short||LGS[k].name))||k||'';
const crest=s=>`../assets/fc/${encodeURIComponent(s)}.webp`;
const ddmm=d=>d.slice(8,10)+'.'+d.slice(5,7);
const MON=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
const pl=(n,a,b,c)=>{n=Math.abs(n)%100;const k=n%10;return n>10&&n<20?c:k===1?a:k>1&&k<5?b:c};
const POS={G:'Вратарь',CD:'Центральный защитник','CD-L':'Центральный защитник','CD-R':'Центральный защитник',SW:'Защитник',LB:'Левый защитник',RB:'Правый защитник',
 DM:'Опорный полузащитник',CM:'Центральный полузащитник','CM-L':'Центральный полузащитник','CM-R':'Центральный полузащитник',LM:'Левый полузащитник',RM:'Правый полузащитник',
 AM:'Атакующий полузащитник','AM-L':'Атакующий полузащитник','AM-R':'Атакующий полузащитник',F:'Нападающий',CF:'Центральный нападающий','CF-L':'Нападающий','CF-R':'Нападающий',LF:'Левый нападающий',RF:'Правый нападающий'};
const err=m=>{MAIN.innerHTML=`<p class="pp-err">${m} <a href="players.html">К списку игроков</a></p>`};
const shade=h=>{const m=/^#?([0-9a-f]{6})$/i.exec(h||'');if(!m)return '#3a4a6a';const n=parseInt(m[1],16),r=n>>16,g=n>>8&255,b=n&255;
 const L=(.2126*r+.7152*g+.0722*b)/255;if(L<=.5)return '#'+m[1];const k=.5/L;return '#'+[r,g,b].map(v=>Math.round(v*k).toString(16).padStart(2,'0')).join('')};
/* рынки — как в списке игроков (football/players.html) */
const MK=[
 {k:'sg',n:'Забьёт',f:r=>r[7]>0,v:r=>r[7],u:'голы'},
 {k:'st',n:'1+ в створ',f:r=>r[10]>=1,v:r=>r[10],u:'удары в створ'},
 {k:'s2',n:'2+ удара',f:r=>r[9]>=2,v:r=>r[9],u:'удары'},
 {k:'ga',n:'Гол+пас',f:r=>r[7]+r[8]>0,v:r=>r[7]+r[8],u:'голы и передачи'},
 {k:'cr',n:'Карточка',f:r=>r[11]+r[12]>0,v:r=>r[11]+r[12],u:'карточки'}];
if(!ID){err('Не указан игрок.');return}
fetch(`data/pp/${ID}.json`).then(r=>{if(!r.ok)throw 0;return r.json()}).then(P=>{
 const T=TT[P.t]||{},col=shade(Array.isArray(T.c)?T.c[0]:T.c);
 const log=P.log||[],N=log.length;
 const sum=i=>log.reduce((s,r)=>s+(r[i]||0),0);
 const G=sum(7),A=sum(8),S=sum(9),SoT=sum(10),Y=sum(11),R=sum(12),ST=sum(5),MIN=sum(6);
 const parts=P.n.split(/\s+/),big=parts.length>1?parts.slice(1).join(' '):P.n,small=parts.length>1?parts[0]:'';
 const ini=parts.map(w=>w[0]).slice(0,2).join('').toUpperCase();
 document.title=`${P.n} — профиль футболиста · JARVIS`;
 const pos=POS[P.pos]||'';
 const hit=(arr,m)=>[arr.filter(m.f).length,arr.length];
 const cell=h=>h[1]?`<td><b>${h[0]}</b> из ${h[1]}<small>${Math.round(100*h[0]/h[1])}%</small><span class="mb"><i style="width:${Math.round(100*h[0]/h[1])}%"></i></span></td>`:'<td class="na">—</td>';
 const L10=log.slice(-10),HM=log.filter(r=>r[2]===1),AW=log.filter(r=>r[2]===0);
 const tile=(l,v)=>`<div class="pp-tile"><span>${l}</span><b>${v}</b></div>`;
 const tiles=[tile('Матчи',N),tile('В старте',ST),tile('Минут за матч',N?Math.round(MIN/N):'—'),tile('Голы',G),tile('Передачи',A),tile('Удары',S),tile('В створ',SoT),tile('Жёлтые',Y)];
 if(R)tiles.push(tile('Красные',R));
 const teamHref=`team.html?id=${encodeURIComponent(P.t)}`;
 const res=r=>r[3]==null||r[4]==null?'':r[3]>r[4]?'w':r[3]<r[4]?'l':'d';
 const RL={w:'В',l:'П',d:'Н'};
 const lgs=[...new Set(log.map(r=>r[13]).filter(Boolean))];
 MAIN.innerHTML=`<article class="pp-hero" aria-label="${esc(P.n)}">
  <span class="pp-wm" aria-hidden="true">${esc(tn(P.t))}</span><img class="pp-ghost" src="${crest(P.t)}" alt="" aria-hidden="true" onerror="this.remove()">
  <div class="pp-txt">
   <p class="pp-crumbs"><a href="${teamHref}" title="Страница клуба"><img src="${crest(P.t)}" alt="" onerror="this.remove()">${esc(tn(P.t))}</a>${P.lg?`<a class="lg" href="league.html?lg=${encodeURIComponent(P.lg)}" title="Страница лиги">${esc(lgn(P.lg))}</a>`:''}<a class="lg" href="players.html?lg=${encodeURIComponent(P.lg||'')}" title="Игроки лиги">Игроки</a></p>
   ${pos?`<p class="pp-pos">${esc(pos)}</p>`:''}
   <h1>${small?esc(small)+' ':''}<b${String(big).length>9?` style="--fz:${(9/String(big).length).toFixed(3)}"`:''}>${esc(big)}</b></h1>
   <p class="pp-sub">${G} ${pl(G,'гол','гола','голов')} и ${A} ${pl(A,'передача','передачи','передач')} в ${N} ${pl(N,'матче','матчах','матчах')} сезона</p>
   <p class="pp-meta">${pos?`<span>${esc(pos)}</span>`:''}<span>${esc(lgs.map(lgn).join(', ')||lgn(P.lg))}, сезон ${esc(F.season||'')}</span></p>
   <dl class="pp-hs" aria-label="Сезон: ${N} ${pl(N,'матч','матча','матчей')}, ${G} голов, ${A} передач"><div><b>${N}</b><span>${pl(N,'матч','матча','матчей')}</span></div><div><b>${G}</b><span>голы</span></div><div><b>${A}</b><span>передачи</span></div><div><b>${SoT}</b><span>в створ</span></div></dl>
  </div>
  <div class="pp-photo nop"><span class="pp-ini" aria-hidden="true">${esc(ini)}</span>${P.ph===0?'':`<img class="ph" src="data/ph/${encodeURIComponent(ID)}.webp" alt="${esc(P.n)}" onload="this.parentNode.classList.remove('nop')" onerror="this.remove()">`}</div>
 </article>
 <section class="pp-sec" id="s-season" aria-labelledby="h-s"><h2 id="h-s">Сезон</h2><div class="pp-tiles">${tiles.join('')}</div>
  <p class="pp-note">Все турниры (клуб — ${esc(tn(P.t))}): ${esc(lgs.map(lgn).join(', '))}. Данные — составы и статистика матчей ESPN.</p></section>
 <section class="pp-sec" id="s-mk" aria-labelledby="h-m"><h2 id="h-m">В скольких матчах</h2>
  <div class="pp-wrap"><table class="pp-mk"><thead><tr><th scope="col">Рынок</th><th scope="col">Сезон</th><th scope="col">Последние 10</th><th scope="col">Дома</th><th scope="col">В гостях</th></tr></thead><tbody>
  ${MK.map(m=>`<tr><th scope="row">${m.n}</th>${cell(hit(log,m))}${cell(hit(L10,m))}${cell(hit(HM,m))}${cell(hit(AW,m))}</tr>`).join('')}
  </tbody></table></div><p class="pp-note">Считаются только матчи, где игрок выходил на поле.</p></section>
 <section class="pp-sec" id="s-form" aria-labelledby="h-f"><h2 id="h-f">Форма</h2>
  <div class="pp-tabs" id="tabs" role="group" aria-label="Рынок графика">${MK.map((m,i)=>`<button type="button" data-k="${m.k}" aria-pressed="${!i}">${m.n}</button>`).join('')}</div>
  <div class="pp-chart" id="chart" role="img" aria-label="Форма по последним матчам"></div></section>
 <section class="pp-sec" id="s-next" aria-labelledby="h-n"><h2 id="h-n">Следующий матч</h2><div id="next" class="pp-nx"></div></section>
 <section class="pp-sec" id="s-games" aria-labelledby="h-g"><h2 id="h-g">Все матчи сезона</h2>
  <div class="pp-wrap"><table class="pp-gm fgm"><thead><tr><th scope="col" class="res"><span class="sr">Результат</span></th><th scope="col">Дата</th><th scope="col">Соперник</th><th scope="col" class="ct">Г+П</th><th scope="col" class="rt br">Уд/створ</th><th scope="col" class="rt tm">Мин</th><th scope="col" class="rt">Счёт</th></tr></thead><tbody>
  ${log.slice().reverse().map(r=>{const w=res(r),cards=(r[11]?'<i class="cy" title="Жёлтая карточка"></i>':'')+(r[12]?'<i class="cr" title="Красная карточка"></i>':'');
   return `<tr><td class="res">${w?`<b class="${w==='d'?'':w}">${RL[w]}</b>`:''}</td><td>${ddmm(r[0])}<small class="fl">${esc(lgn(r[13]))}</small></td><td><a class="op" style="color:inherit;text-decoration:none" href="team.html?id=${encodeURIComponent(r[1])}"><img src="${crest(r[1])}" alt="" loading="lazy" onerror="this.remove()"><span>${esc(tn(r[1]))}<small>${r[2]?'дома':'в гостях'}${r[5]?'':' · со скамейки'}</small></span></a></td><td class="ct pt"><b class="${r[7]+r[8]>0?'g':''}">${r[7]}+${r[8]}</b>${cards}</td><td class="rt br">${r[9]}/${r[10]}</td><td class="rt tm">${r[6]??'—'}′</td><td class="rt sc">${r[3]!=null?`<span class="sg"><i>${r[3]}</i><u>:</u><i>${r[4]}</i></span>`:'—'}</td></tr>`}).join('')}
  </tbody></table></div></section>
 <div class="pp-cta"><p>Разборы матчей и прогнозы по футболу — в нашем Telegram-канале.</p><a href="https://t.me/jarvibet" target="_blank" rel="noopener">Получать прогнозы — бесплатно</a></div>`;
 MAIN.style.setProperty('--c',col);
 const chart=document.getElementById('chart');
 const draw=k=>{const m=MK.find(x=>x.k===k)||MK[0],L=log.slice(-15),mx=Math.max(k==='s2'||k==='st'?4:2,...L.map(m.v));
  chart.innerHTML=L.map(r=>{const v=m.v(r),ok=m.f(r),tip=`${ddmm(r[0])}, ${r[2]?'дома':'в гостях'}, ${tn(r[1])}: ${m.u} — ${v}`;
   return `<div class="pp-col" title="${esc(tip)}"><div class="bar${ok?' g':''}" style="--h:${Math.max(.04,v/mx)}">${v>0?`<b>${v}</b>`:''}</div><img class="em" src="${crest(r[1])}" alt="${esc(tn(r[1]))}" loading="lazy" onerror="this.outerHTML='<span class=fb>${esc(tn(r[1]).slice(0,3).toUpperCase())}</span>'"><small>${r[2]?'':'@'}${r[0].slice(8,10)}<i>.${r[0].slice(5,7)}</i></small></div>`}).join('');
  chart.setAttribute('aria-label',`${m.n}: ${L.map(r=>`${ddmm(r[0])} ${tn(r[1])} — ${m.v(r)}`).join('; ')}`);
  document.querySelectorAll('#tabs button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.k===m.k))};
 document.getElementById('tabs').onclick=e=>{const b=e.target.closest('button');if(b)draw(b.dataset.k)};
 draw(MK[0].k);
 const box=document.getElementById('next'),nx=P.nx;
 if(nx&&nx.o&&new Date(nx.d.replace(' ','T')+':00+03:00')>Date.now()-3*3600e3){
  const d=nx.d;box.innerHTML=`<a class="fnx" href="team.html?id=${encodeURIComponent(nx.o)}"><img src="${crest(nx.o)}" alt="" onerror="this.remove()"><span><b>${esc(tn(nx.o))}</b><small>${nx.h?'дома':'в гостях'} · ${+d.slice(8,10)} ${MON[+d.slice(5,7)-1]}, ${d.slice(11,16)} МСК${nx.lg?' · '+esc(lgn(nx.lg)):''}</small></span></a>`;
 }else box.innerHTML='<p class="pp-note">Ближайший матч пока не назначен.</p>';
}).catch(()=>err('Игрок не найден или данные ещё не собраны.'));
})();
