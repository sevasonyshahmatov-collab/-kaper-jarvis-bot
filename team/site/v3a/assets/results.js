/* JARVIS v3a — страница «Итоги прогнозов» (results.html). Данные — data/results.js (window.__RESULTS), собирает daily/results.py
   из постов канала; здесь только показ: сводка, месяцы, модель / автор / экспрессы, график, список с фильтрами. */
(()=>{
const D=window.__RESULTS;if(!D||!D.picks)return;
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const num=(x,d)=>x==null?'—':Number(x).toFixed(d==null?2:d).replace('.',',');
const sign=x=>(x>0?'+':x<0?'−':'')+num(Math.abs(x),1);
const MG=['','января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
const day=s=>+s.slice(8,10)+' '+MG[+s.slice(5,7)];
const LG={khl:'КХЛ',nhl:'НХЛ',epl:'АПЛ',laliga:'Ла Лига',seriea:'Серия А',bundesliga:'Бундеслига',ligue1:'Лига 1',rpl:'РПЛ',ucl:'ЛЧ',uel:'ЛЕ',uecl:'ЛК',foot:'Футбол'};
const RES={w:'Зашёл',l:'Не зашёл',p:'Возврат'};
const T=D.sum.total,A=T.all;

/* ── первый экран ── */
$('#rs-lead').textContent='Все прогнозы канала @jarvibet с '+day(D.since)+' '+D.since.slice(0,4)+' года: что зашло, что нет, со счётом матча и ссылкой на пост.';
$('#rs-kpi').innerHTML=
 `<li><b>${A.n}</b><span>прогнозов с итогом</span></li>
  <li class="win"><b>${A.w}</b><span>зашло — ${num(A.rate,1)} % без учёта возвратов</span></li>
  <li class="loss"><b>${A.l}</b><span>не зашло${A.p?', ещё '+A.p+' — возврат':''}</span></li>
  <li><b>${sign(A.units)}<small>ед.</small></b><span>результат при ставке 1 на каждый прогноз</span></li>`;
const done=D.picks.filter(p=>p.r);
$('#rs-form').innerHTML=`<span>Последние ${Math.min(20,done.length)}:</span><span class="rs-dots" role="img" aria-label="${done.slice(0,20).map(p=>RES[p.r]).join(', ')}">${done.slice(0,20).reverse().map(p=>`<i class="${p.r}"></i>`).join('')}</span><span>старые слева, свежие справа</span>`;
$('#rs-upd').textContent='Обновлено '+day(D.built)+' в '+D.built.slice(11,16)+' МСК. Последний расчётный день — '+day(D.sum.last_day)+'.';

/* ── карточка сводки ── */
const bar=t=>{const n=t.w+t.l+t.p||1;return `<div class="rs-bar" role="img" aria-label="Зашло ${t.w}, не зашло ${t.l}, возврат ${t.p}"><i style="width:${100*t.w/n}%"></i><u style="width:${100*t.p/n}%"></u></div>`};
const meta=t=>`<p class="rs-meta"><span>зашло <b>${t.w}</b></span><span>не зашло <b>${t.l}</b></span>${t.p?`<span>возврат <b>${t.p}</b></span>`:''}<span>средний кэф <b>${num(t.kef)}</b></span><span>результат <b class="${t.units>=0?'pos':'neg'}">${sign(t.units)} ед.</b></span></p>`;
const big=t=>`<div class="rs-big"><b>${t.w} из ${t.w+t.l}</b><span>${num(t.rate,1)} %</span></div>`;
const short=t=>t.n?`${t.w} из ${t.w+t.l}`:'—';

/* ── месяцы ── */
$('#rs-months').innerHTML=D.sum.months.map(m=>`<article class="rs-card"><h3>${esc(m.name)}${m.live?'<em>идёт</em>':''}</h3>${big(m.all)}${bar(m.all)}${meta(m.all)}
 <ul class="rs-split">
  <li><span>Хоккей</span><b>${short(m.hockey)}</b></li>
  ${m.football.n?`<li><span>Футбол</span><b>${short(m.football)}</b></li>`:''}
  ${m.express.n?`<li><span>Экспрессы</span><b>${short(m.express)}</b></li>`:''}
  ${m.model.n?`<li><span>По модели</span><b>${short(m.model)}</b></li>`:''}
  ${m.author.n?`<li><span>Выбор автора</span><b>${short(m.author)}</b></li>`:''}
 </ul></article>`).join('');

/* ── модель / автор / экспрессы ── */
const who=(title,t,note)=>`<article class="rs-card"><h3>${title}</h3>${t.n?big(t)+bar(t)+meta(t):'<p class="rs-note">Пока нет рассчитанных прогнозов.</p>'}<p class="rs-note">${note}</p></article>`;
$('#rs-who').innerHTML=
 who('По модели',T.model,'Ставку предложила модель, автор опубликовал её без изменений.')+
 who('Выбор автора',T.author,'Модель предлагала другое — автор поставил по-своему.')+
 who('Экспрессы',T.express,'Собирает автор: два-три события в одном купоне. Зашёл, только если зашли все.');
const unl=T.single.n-T.model.n-T.author.n;
$('#rs-who-note').textContent='Метки ведём с '+(D.labels_since?day(D.labels_since):'середины октября')+': с этого дня известно, что предлагала модель. Одиночных прогнозов без метки — '+unl+', они входят в общий счёт, но не в это сравнение.';
if(D.sum.cal&&D.sum.cal.length){
 $('#rs-cal').innerHTML=`<h3 style="margin:0;font:800 22px/1.1 var(--display);text-transform:none;letter-spacing:0">Сколько обещала модель и сколько зашло</h3>
 <table class="rs-cal"><thead><tr><th>Вероятность модели</th><th>Прогнозов</th><th>Обещала</th><th>Зашло</th></tr></thead><tbody>
 ${D.sum.cal.map(c=>`<tr><td>${c.lo}–${c.hi===100?'100':c.hi} %</td><td>${c.n}</td><td>${num(c.pm,1)} %</td><td>${num(100*c.w/c.n,1)} %</td></tr>`).join('')}</tbody></table>
 <p class="rs-note">Только прогнозы «по модели». Выборка небольшая: при 30–50 прогнозах в строке разброс в 10–15 п. п. — обычное дело.</p>`;
}else $('#rs-cal').remove();

/* ── график накопленного результата (одна линия: каждый прогноз — ставка 1) ── */
(()=>{
 const rows=done.filter(p=>p.u!=null).slice().reverse();if(rows.length<5){$('#rs-chart').remove();return}
 let s=0;const pts=rows.map(p=>(s+=p.u,{d:p.d.slice(0,10),v:s}));
 const W=1000,H=260,L=44,R=64,Tp=14,B=30,min=Math.min(0,...pts.map(p=>p.v)),max=Math.max(1,...pts.map(p=>p.v));
 const x=i=>L+(W-L-R)*i/(pts.length-1),y=v=>Tp+(H-Tp-B)*(1-(v-min)/(max-min));
 const step=max-min>60?20:max-min>24?10:5;let grid='';
 for(let v=Math.ceil(min/step)*step;v<=max;v+=step)grid+=`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="#10161f" stroke-opacity="${v===0?.45:.1}"/><text x="${L-8}" y="${y(v)+4}" text-anchor="end">${v>0?'+':''}${v}</text>`;
 let ticks='',last='';pts.forEach((p,i)=>{const m=p.d.slice(0,7);if(m!==last){last=m;if(i>0)ticks+=`<line x1="${x(i)}" x2="${x(i)}" y1="${Tp}" y2="${H-B}" stroke="#10161f" stroke-opacity=".1"/>`;ticks+=`<text x="${x(i)+(i?6:0)}" y="${H-8}">${['','Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'][+m.slice(5)]}</text>`}});
 const e=pts[pts.length-1];
 $('#rs-chart').innerHTML=`<h3>Накопленный результат</h3><p>Каждый прогноз — ставка в 1 единицу: зашёл — плюс (кэф − 1), не зашёл — минус 1. Прогнозов с кэфом: ${pts.length}.</p>
 <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Накопленный результат с ${day(pts[0].d)} по ${day(e.d)}: ${sign(e.v)} единицы">${grid}${ticks}
 <polyline fill="none" stroke="#173daf" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" points="${pts.map((p,i)=>x(i).toFixed(1)+','+y(p.v).toFixed(1)).join(' ')}"/>
 <circle cx="${x(pts.length-1)}" cy="${y(e.v)}" r="5" fill="#173daf"/><text x="${x(pts.length-1)+9}" y="${y(e.v)+4}" style="font-weight:800;fill:#10161f">${sign(e.v)}</text></svg>`;
})();

/* ── список ── */
const F={sport:'all',src:'all',res:'all',m:'all'};let shown=40;
const months=[...new Set(D.picks.map(p=>p.d.slice(0,7)))];
const MN=['','Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
const groups=[
 ['sport','Вид',[['all','Все'],['hockey','Хоккей'],['football','Футбол'],['express','Экспрессы']]],
 ['src','Чья ставка',[['all','Все'],['model','По модели'],['author','Выбор автора']]],
 ['res','Итог',[['all','Все'],['w','Зашло'],['l','Не зашло']]],
 ['m','Месяц',[['all','Все месяцы'],...months.map(m=>[m,MN[+m.slice(5)]])]]
];
$('#rs-filters').innerHTML=groups.map(g=>`<div class="rs-fg" role="group" aria-label="${g[1]}">${g[2].map(o=>`<button type="button" data-f="${g[0]}" data-v="${o[0]}" aria-pressed="${o[0]==='all'}">${o[1]}</button>`).join('')}</div>`).join('');
const pass=p=>(F.sport==='all'||(F.sport==='express'?p.kind==='express':p.kind==='single'&&p.sport===F.sport))
 &&(F.src==='all'||(p.kind==='single'&&p.src===F.src))&&(F.res==='all'||p.r===F.res)&&(F.m==='all'||p.d.slice(0,7)===F.m);
const row=p=>{
 const ex=p.kind==='express',fb=p.sport==='football';
 const tag=ex?'<span class="rtag ex">Экспресс</span>':p.src==='model'?'<span class="rtag">Модель</span>':p.src==='author'?'<span class="rtag au">Автор</span>':'';
 const em=e=>e?`<img class="rs-em" src="${esc(e)}" alt="" width="22" height="22" loading="lazy">`:'';   /* эмблема у названия (владелец 11.11) */
 const tm=(e,n)=>`<span class="rs-tm">${em(e)}${esc(n)}</span>`;
 const title=ex?esc(p.bet):tm(p.he,p.h)+' — '+tm(p.ae,p.a);
 const bet=ex?'общий кэф '+(p.kef?num(p.kef):'—'):esc(p.bet);
 const pm=p.pm?` · модель ${num(p.pm*100,0)} %`:'';
 return `<li class="rs-row"><span class="rlg${fb?' fb':''}">${LG[p.lg]||''}</span>
  <span class="rmt">${title}<small>${p.d.slice(11,16)!=='00:00'?p.d.slice(11,16)+' МСК':''}${pm}</small></span>
  <span class="rbet">${tag}${bet}</span>
  <span class="rkef"><i>кэф </i>${p.kef?num(p.kef):'—'}</span><span class="rsc">${esc(p.sc||'')}</span>
  <span class="rres ${p.r||'n'}">${p.r?RES[p.r]:'Без итога'}</span>
  <a class="rpost" href="${esc(p.url)}" target="_blank" rel="noopener">Пост №${p.id}</a>
  ${ex?`<ul class="rs-legs">${p.legs.map(l=>`<li><b>${tm(l.he,l.h)} — ${tm(l.ae,l.a)}${l.sc?' '+esc(l.sc):''}</b><span>${esc(l.bet)}${l.kef?' · '+num(l.kef):''}</span>${l.r?`<span class="${l.r}">${l.r==='w'?'зашло':l.r==='l'?'не зашло':'возврат'}</span>`:''}</li>`).join('')}</ul>`:''}</li>`};
const draw=()=>{
 const rows=D.picks.filter(pass),w=rows.filter(p=>p.r==='w').length,l=rows.filter(p=>p.r==='l').length;
 $('#rs-count').textContent=rows.length?`Найдено ${rows.length}: зашло ${w}, не зашло ${l}`+(rows.filter(p=>p.r==='p').length?`, возврат ${rows.filter(p=>p.r==='p').length}`:'')+(rows.filter(p=>!p.r).length?`, без итога ${rows.filter(p=>!p.r).length}`:''):'По таким условиям прогнозов нет.';
 let html='',cur='';rows.slice(0,shown).forEach(p=>{const d=p.d.slice(0,10);if(d!==cur){if(cur)html+='</ul>';cur=d;const dr=rows.filter(x=>x.d.slice(0,10)===d&&x.r),dw=dr.filter(x=>x.r==='w').length;
  html+=`<h3 class="rs-day">${day(d)}<span>${dr.length?dw+' из '+dr.length:''}</span></h3><ul class="rs-list">`}html+=row(p)});
 $('#rs-list').innerHTML=html+(cur?'</ul>':'');
 const more=$('#rs-more');more.hidden=rows.length<=shown;more.textContent='Показать ещё '+Math.min(40,rows.length-shown);
};
$('#rs-filters').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;F[b.dataset.f]=b.dataset.v;shown=40;
 b.parentNode.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));draw()});
$('#rs-more').addEventListener('click',()=>{shown+=40;draw()});
draw();
const pend=D.picks.filter(p=>!p.r).length,bysc=D.picks.filter(p=>p.rs==='score').length;
$('#rs-pend').textContent=(pend?`Без итога сейчас ${pend}: матч ещё не сыгран или ставку нельзя проверить по счёту (броски, первый гол). `:'')+(bysc?`У ${bysc} футбольных прогнозов итога в канале не было — он поставлен по счёту матча.`:'');
})();
