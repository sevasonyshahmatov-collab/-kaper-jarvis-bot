/* «Газета» — первая полоса хоккея. Данные: data/today.js, lines.js, model.js (как на hockey/index.html). */
(()=>{
'use strict';
const TD=window.JV_TODAY||{matches:[]},LN=window.JV_LINES||{},MD=window.JV_MODEL||{};
const esc=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const $=s=>document.querySelector(s);
const MON=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
const WD=['воскресенье','понедельник','вторник','среда','четверг','пятница','суббота'];
const WDS=['вс','пн','вт','ср','чт','пт','сб'];
const dparts=t=>{const [y,m,d]=t.slice(0,10).split('-').map(Number);return {y,m,d,w:new Date(Date.UTC(y,m-1,d)).getUTCDay()}};
const f2=v=>(+v).toFixed(2).replace('.',',');
const em=s=>`../../../assets/em/${esc(s)}.webp`;
const link=m=>`../../../hockey/index.html#m-${m.key.replace(/[|_]/g,'-')}`;
const left=t=>Date.parse(t.replace(' ','T')+':00+03:00')-Date.now();

const ALL=(TD.matches||[]).filter(m=>m.lg==='khl'||m.lg==='nhl')
  .map(m=>({...m,ln:LN[m.key]||null,md:MD[m.key]||null})).sort((a,b)=>a.t<b.t?-1:1);
const FRESH=ALL.filter(m=>left(m.t)>-3*3600e3);   // начавшиеся больше 3 часов назад считаем сыгранными
const D=FRESH.length?FRESH:ALL;
if(!D.length){$('#lead').innerHTML='<p class="empty">Матчей КХЛ и НХЛ в последнем обновлении данных нет. Расписание появится после следующего обновления.</p>';return}
if(!FRESH.length){const n=$('#daynote');n.hidden=false;n.textContent='Все матчи из последнего обновления уже сыграны. Новые появятся после обновления данных.'}

/* выпуск: игровой день = дата первого матча окна */
{const p=dparts(D[0].t);$('#issue').textContent=`${WD[p.w][0].toUpperCase()+WD[p.w].slice(1)}, ${p.d} ${MON[p.m-1]} ${p.y}`}

/* фаворит: исход с наибольшей вероятностью модели среди П1/П2 */
const fav=m=>{const o=m.md;if(!o)return null;const k=o.p1>=o.p2?1:2;return {k,p:Math.round(o[k===1?'p1':'p2']*100),team:k===1?m.hn:m.an,slug:k===1?m.h:m.a,odd:m.ln?m.ln[k===1?'p1':'p2']:null}};
const withFav=D.map(m=>({m,f:fav(m)})).filter(x=>x.f);

/* передовица: самый уверенный фаворит модели среди матчей окна */
if(withFav.length){
 const {m,f}=withFav.reduce((a,b)=>b.f.p>a.f.p?b:a);
 const pr=[['П1',m.md.p1,m.ln&&m.ln.p1],['Х',m.md.x,m.ln&&m.ln.x],['П2',m.md.p2,m.ln&&m.ln.p2]];
 const mx=Math.max(...pr.map(r=>r[1]));
 const dp=dparts(m.t),lgn=m.lg==='khl'?'КХЛ':'НХЛ';
 $('#lead').innerHTML=`
  <p class="kick"><span class="red">Матч дня</span><span>${lgn}</span><span>${dp.d} ${MON[dp.m-1]}, ${esc(m.t.slice(11))} МСК</span></p>
  <h1 class="hl" id="hl">${esc(f.team)} — фаворит: <span class="nw">${f.p} %</span></h1>
  <div class="duel">
    <div class="side"><img src="${em(m.h)}" alt="" width="96" height="96"><b>${esc(m.hn)}</b></div>
    <div class="bars" role="img" aria-label="Вероятности модели: ${pr.map(r=>r[0]+' '+Math.round(r[1]*100)+' %').join(', ')}">
      ${pr.map(([k,p,c])=>`<div class="bar${p===mx?' fav':''}"><span class="pc">${Math.round(p*100)} %</span><span class="col"><i style="--h:${(p*100/Math.max(.6,mx)).toFixed(1)}%"></i></span><span class="lab">${k}</span><span class="od">${c?f2(c):'—'}</span></div>`).join('')}
    </div>
    <div class="side"><img src="${em(m.a)}" alt="" width="96" height="96"><b>${esc(m.an)}</b></div>
  </div>
  <a class="more" href="${link(m)}">Расчёт матча →</a>`;
}else{
 $('#lead').innerHTML='<p class="empty">Расчёт модели на ближайшие матчи ещё не готов.</p>';
}

/* таблица дня: пять самых уверенных фаворитов */
{const top=[...withFav].sort((a,b)=>b.f.p-a.f.p).slice(0,6);
 $('#tod').innerHTML=top.length?`<thead><tr><th class="l">Фаворит</th><th>%</th><th>Кэф</th></tr></thead><tbody>${top.map(({m,f})=>`<tr><td class="l"><a href="${link(m)}"><img src="${em(f.slug)}" alt="" width="20" height="20">${esc(f.team)}</a></td><td>${f.p}</td><td>${f.odd?f2(f.odd):'—'}</td></tr>`).join('')}</tbody>`:'';
 if(!top.length)$('.tod').hidden=true}

/* хроника: две рубрики, дата — подзаголовком при смене дня */
for(const lg of ['khl','nhl']){
 const list=D.filter(m=>m.lg===lg),ol=$('#rub-'+lg+' ol');let day='';
 ol.innerHTML=list.length?list.map(m=>{
  const f=fav(m),d=m.t.slice(0,10);let h='';
  if(d!==day){day=d;const p=dparts(m.t);h=`<li class="dh">${WDS[p.w]}, ${p.d} ${MON[p.m-1]}</li>`}
  return h+`<li class="row"><a href="${link(m)}"><time>${esc(m.t.slice(11))}</time>
   <span class="pair"><span class="tm${f&&f.k===1?' w':''}"><img src="${em(m.h)}" alt="" width="20" height="20"><span>${esc(m.hn)}</span></span><span class="tm${f&&f.k===2?' w':''}"><img src="${em(m.a)}" alt="" width="20" height="20"><span>${esc(m.an)}</span></span></span>
   <span class="n p">${f?f.p+' %':'—'}</span><span class="n o">${f&&f.odd?f2(f.odd):'—'}</span></a></li>`}).join(''):'<li class="dh">Матчей нет</li>';
}
})();
