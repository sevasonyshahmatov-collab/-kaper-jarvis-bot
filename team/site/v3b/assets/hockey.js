/* Хоккей — ПРИМЕРНЫЕ ДАННЫЕ макета (те же, что в v2: __TODAY, __RES, __MONTHS, рейтинг Эло из тура). */
(()=>{
const {esc,f1,plural,ring,two,at,atMs,RM}=JB;
const M=(o,min)=>{o.t=at(min);return o};
const D=[
 M({lg:'khl',a:'СКА',b:'ЦСКА',p:'Тотал больше 4,5',k:'1.70',y:'Обе команды забивают в среднем больше трёх за игру',x:[2.25,4.1,2.6],pr:.56,pick:-1},90),
 M({lg:'khl',a:'Ак Барс',b:'Локомотив',p:'Победа Локомотива',k:'1.85',y:'Локомотив выиграл 2 из 3 последних',x:[2.10,4.20,1.85],pr:.58,pick:2},190),
 M({lg:'khl',a:'Сибирь',b:'Трактор',p:'Победа Трактора',k:'1.95',y:'Трактор выше в таблице и в лучшей форме',x:[2.9,4.3,1.95],pr:.55,pick:2},200),
 M({lg:'nhl',a:'Бостон',b:'Торонто',p:'Победа Бостона',k:'1.75',y:'Бостон дома, три победы подряд',x:[1.75,4.4,3.3],pr:.57,pick:0},560),
 M({lg:'nhl',a:'Колорадо',b:'Даллас',p:'Тотал больше 5,5',k:'1.90',y:'Две самые результативные команды дивизиона',x:[2.0,4.3,2.7],pr:.54,pick:-1},620),
 M({lg:'nhl',a:'Вегас',b:'Эдмонтон',p:'Победа Эдмонтона',k:'2.05',y:'Эдмонтон набрал очки в последних 3 играх',x:[2.4,4.2,2.05],pr:.52,pick:2},740)];
const RES=[{t:'Нэшвилл — Колорадо',b:'ТБ 5,5',ok:true},{t:'Рейнджерс — Лос-Анджелес',b:'ИТБ Рейнджерс 2,5',ok:true},{t:'Калгари — Торонто',b:'ТБ 5,5',ok:true},
 {t:'Каролина — Бостон',b:'Ф2 +1,5',ok:true},{t:'Чикаго — Лос-Анджелес',b:'ИТБ Лос-Анджелеса 2,5',ok:false},{t:'Сибирь — Металлург',b:'П2',ok:false},
 {t:'Нефтехимик — Адмирал',b:'ТБ 4,5',ok:true},{t:'Каролина — Коламбус',b:'П1',ok:true},{t:'Сент-Луис — Бостон',b:'ИТБ Бостона 2,5',ok:false}];
const MONTHS=[{m:'2026-09',name:'Сентябрь',n:25,w:21,l:4,p:0,kef:1.81,units:12.3,live:0},{m:'2026-10',name:'Октябрь',n:153,w:108,l:42,p:3,kef:1.78,units:39.01,live:1}];
const LEAGUES=[{id:'khl',name:'КХЛ',full:'Континентальная хоккейная лига',when:'матчи днём по Москве'},{id:'nhl',name:'НХЛ',full:'Национальная хоккейная лига',when:'матчи ночью по Москве'}];
const LN=Object.fromEntries(LEAGUES.map(l=>[l.id,l]));
const LGI=id=>`../assets/lg/${id}.svg`;
const EM={'СКА':'ska','ЦСКА':'cska','Ак Барс':'akbars','Локомотив':'lokomotiv','Сибирь':'sibir','Трактор':'traktor','Бостон':'nhl_bos','Торонто':'nhl_tor','Колорадо':'nhl_col','Даллас':'dallas','Вегас':'nhl_vgk','Эдмонтон':'nhl_edm'};
const em=n=>`../assets/em/${EM[n]}.webp`;
const cnt=id=>D.filter(m=>m.lg===id).length;
document.getElementById('nToday').textContent=D.length;

/* Прогноз дня: Ак Барс — Локомотив, как в v2 */
const best=D[1],td=document.getElementById('today');
td.innerHTML=`<div class="today-top"><span>Прогноз дня</span><span><img src="${LGI(best.lg)}" alt="">${LN[best.lg].name}, ${best.t.slice(11)} МСК</span></div>
 <div class="pair"><div class="tm"><img src="${em(best.a)}" alt="">${esc(best.a)}</div>
 <div class="pct"><span class="circ">${Math.round(best.pr*100)}%${ring()}</span><small>по модели</small></div>
 <div class="tm"><img src="${em(best.b)}" alt="">${esc(best.b)}</div></div>
 <div class="odds">${['П1','Х','П2'].map((k,i)=>`<div class="${i===best.pick?'on':''}">${k}<b>${best.x[i].toFixed(2)}</b></div>`).join('')}</div>
 <div class="pick"><div><span>Прогноз</span><strong>${esc(best.p)}</strong></div><span class="k">${best.k}</span></div>
 <div class="clock"><span id="cl">До вбрасывания</span><b id="cd">—</b></div>
 <p class="sample">Пример данных. Прогноз выйдет в канале до 08:00 МСК.</p>`;

/* Матчи дня */
const ltabs=document.getElementById('ltabs'),ml=document.getElementById('mlist');
ltabs.innerHTML=`<button class="tab" role="tab" aria-selected="true" data-l="all">Все <span class="n">${D.length}</span></button>`+
 LEAGUES.map(l=>`<button class="tab" role="tab" aria-selected="false" data-l="${l.id}"><img src="${LGI(l.id)}" alt="">${l.name} <span class="n">${cnt(l.id)}</span></button>`).join('');
function card(m){return `<li class="match"><div class="m-top"><span><img src="${LGI(m.lg)}" alt="">${LN[m.lg].name}</span><time>${m.t.slice(11)} МСК</time></div>
 <div class="m-teams"><div><img src="${em(m.a)}" alt="">${esc(m.a)}</div><div><img src="${em(m.b)}" alt="">${esc(m.b)}</div></div>
 <div class="m-cd" data-t="${m.t}"></div>
 <div class="odds">${['П1','Х','П2'].map((k,i)=>`<div class="${i===m.pick?'on':''}">${k}<b>${m.x[i].toFixed(2)}</b></div>`).join('')}</div>
 <div class="bars"><div class="bar top"><span>модель</span><em><i style="--w:${m.pr.toFixed(2)}"></i></em><b>${Math.round(m.pr*100)}%</b></div></div>
 <p class="reason">${esc(m.y)}</p>
 <div class="m-foot"><span class="m-pick">${esc(m.p)}<span class="k">${m.k}</span></span></div></li>`}
function render(l){const sel=l==='all'?D:D.filter(m=>m.lg===l);ltabs.querySelectorAll('.tab').forEach(t=>t.setAttribute('aria-selected',t.dataset.l===l));
 ml.innerHTML=sel.map(card).join('');
 if(RM||!('IntersectionObserver' in window))ml.querySelectorAll('.match').forEach(c=>c.classList.add('in'));
 else{const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{rootMargin:'0px 0px -10% 0px'});ml.querySelectorAll('.match').forEach(c=>io.observe(c))}
 tick()}
ltabs.addEventListener('click',e=>{const t=e.target.closest('.tab');if(t)render(t.dataset.l)});
function tick(){const s=Math.round((atMs(best.t)-Date.now())/1000),cd=document.getElementById('cd');
 if(s>0)cd.textContent=`${two(Math.floor(s/3600))}:${two(Math.floor(s%3600/60))}:${two(s%60)}`;else{document.getElementById('cl').textContent='Матч';cd.textContent=s>-10800?'идёт':'завершён'}
 document.querySelectorAll('.m-cd[data-t]').forEach(e=>{const s=Math.round((atMs(e.dataset.t)-Date.now())/1000),m=Math.floor(s/60);
  e.textContent=s<=0?(s>-10800?'идёт':''):m<60?`через ${m} мин`:`через ${Math.floor(m/60)} ч ${m%60} мин`})}
render('all');setInterval(tick,1000);

/* Лиги и клубы */
document.getElementById('lglist').innerHTML=LEAGUES.map(l=>`<li><a href="#matches" data-l="${l.id}"><img src="${LGI(l.id)}" alt=""><span><b>${l.name}</b><small>${l.full}, ${l.when}</small></span><span class="n">${cnt(l.id)} ${plural(cnt(l.id),'матч','матча','матчей')}</span></a></li>`).join('');
document.getElementById('lglist').addEventListener('click',e=>{const a=e.target.closest('a[data-l]');if(a)render(a.dataset.l)});
const CL=[['СКА','КХЛ'],['ЦСКА','КХЛ'],['Ак Барс','КХЛ'],['Локомотив','КХЛ'],['Сибирь','КХЛ'],['Трактор','КХЛ'],['Бостон','НХЛ'],['Торонто','НХЛ'],['Колорадо','НХЛ'],['Даллас','НХЛ'],['Вегас','НХЛ'],['Эдмонтон','НХЛ']];
document.getElementById('crests').innerHTML=CL.map(([n,l])=>`<li title="${esc(n)}, ${l}"><img src="${em(n)}" alt="" loading="lazy">${esc(n)}</li>`).join('');

/* Сила команд: Эло (пример) */
const ELO=[['Локомотив',1612,14],['СКА',1598,6],['Ак Барс',1571,-4],['ЦСКА',1560,9],['Трактор',1534,-11],['Сибирь',1488,3]];
document.getElementById('order').innerHTML=ELO.map(([n],i)=>`<li><span class="no">${i+1}</span><img src="${em(n)}" alt="">${esc(n)}</li>`).join('');
document.getElementById('power').innerHTML=`<h3>Рейтинг Эло</h3><p class="src" style="margin-top:6px">Изменение — за последний матч.</p>`+
 ELO.map(([n,v,d])=>`<div class="cb"><span>${esc(n)}</span><em><i style="--w:${((v-1440)/180).toFixed(3)}"></i></em><b>${v}</b></div><div style="text-align:right;font-size:13px;color:${d>=0?'var(--win)':'var(--red)'};margin-top:-6px">${d>0?'+':d<0?'−':''}${Math.abs(d)}</div>`).join('')+`<p class="src">Пример данных.</p>`;

/* Модель: ползунок кэфа и розыгрыши */
const k=document.getElementById('k'),ko=document.getElementById('kout'),fk=v=>v.toFixed(2).replace('.',',');
const kv=()=>{const v=+k.value;ko.innerHTML=`<b class="hand" style="font-size:30px">${fk(v)}</b> — примерно ${Math.round(100/v)} % по линии. `+(v<1.6?'Слишком низкий кэф: рисковать ради такого нет смысла.':v<=2.3?'Рабочий коридор модели.':'Слишком высокий кэф: больше случайности, чем расчёта.');k.setAttribute('aria-valuetext',fk(v))};
k.addEventListener('input',kv);kv();
const sim=document.getElementById('sim');
function run(n){const c=[0,0,0];for(let i=0;i<n;i++){const r=Math.random();c[r<.26?0:r<.42?1:2]++}return c.map(v=>v/n)}
function show(r){sim.innerHTML=[['П1 Ак Барс',r[0]],['Ничья',r[1]],['П2 Локомотив',r[2]]].map(([l,v],i)=>`<div class="r"><span>${l}</span><em><i style="--w:${v.toFixed(3)};--c:${i===2?'var(--mark)':'var(--dim)'}"></i></em><b>${Math.round(v*100)}%</b></div>`).join('')}
show(run(10000));
document.getElementById('again').addEventListener('click',e=>{const b=e.currentTarget;if(RM){show(run(10000));return}b.disabled=true;let i=0;const iv=setInterval(()=>{show(run(400));if(++i>9){clearInterval(iv);show(run(10000));b.disabled=false}},70)});

/* Итоги: месяцы и лента */
const rub=u=>(Math.round(Math.abs(u)*100)*100).toLocaleString('ru-RU').replace(/\s/g,' ');
document.getElementById('months').innerHTML=MONTHS.map((m,i)=>{const pct=Math.round(100*m.w/(m.w+m.l));
 return `<div class="panel month rv" style="--d:${i*90}ms"><div class="month-top"><h3>${m.name} ${m.m.slice(0,4)}</h3>${m.live?'<span class="live">идёт</span>':''}</div>
 <p class="pc"><span class="circ">${pct}%${ring()}</span></p><p style="color:var(--dim);font-size:15px">зашло из ${m.n} ${plural(m.n,'прогноза','прогнозов','прогнозов')}</p>
 <div class="wl" aria-hidden="true"><i class="w" style="width:${100*m.w/m.n}%"></i><i class="l" style="width:${100*m.l/m.n}%"></i>${m.p?`<i class="p" style="width:${100*m.p/m.n}%"></i>`:''}</div>
 <div class="mrow"><span>зашло <b>${m.w}</b></span><span>не зашло <b>${m.l}</b></span>${m.p?`<span>возврат <b>${m.p}</b></span>`:''}<span>средний кэф <b>${f1(m.kef,2)}</b></span></div>
 <div class="rub"><b>${m.units>=0?'+':'−'}${rub(m.units)} ₽</b><span>если ставить по 10 000 ₽ на каждый прогноз</span></div></div>`}).join('');
const R=RES.map(r=>`<span class="res ${r.ok?'win':'loss'}">${esc(r.t)}, ${esc(r.b)}<b>${r.ok?'зашёл':'не зашёл'}</b></span>`).join('');
document.getElementById('tick').innerHTML=R+R;

JB.page('hockey');JB.reveal();
})();
