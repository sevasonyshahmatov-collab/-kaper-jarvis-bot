/* Шаблон A «Первая полоса»: матч дня — заголовок, матчи по видам спорта — газетные колонки. */
(()=>{
const H=window.HOME,$=id=>document.getElementById(id);
if(!H||!H.J)return;
const e=H.esc;
$('fp-date').textContent=H.dateStr();
$('fp-upd').textContent=H.upd();
const all=H.all();
if(!all.length)return;

const hero=H.hero(all);
function lead(m){
 const when=`${m.lgn}, ${m.day==='сегодня'||m.day==='завтра'?m.day:m.day}, ${m.hm} МСК`;
 const cells=m.pr?[['П1',m.pr[0],m.ln&&m.ln.p1],['Х',m.pr[1],m.ln&&m.ln.x],['П2',m.pr[2],m.ln&&m.ln.p2]].filter(c=>c[1]!=null&&!(c[0]==='Х'&&m.hockey&&!(m.ln&&m.ln.x))):[];
 const fav=m.bi>=0?(m.bi===1?'Ничья':e(m.who)):'';
 $('fp-lead').innerHTML=`
  <p class="fp-kick">Матч дня: ${e(when)}</p>
  <h1><span class="sr">Матч дня: </span><span class="tm"><img src="${m.hc}" alt="" width="64" height="64">${e(m.hn)}</span><span class="dash" aria-hidden="true">—</span><span class="tm"><img src="${m.ac}" alt="" width="64" height="64">${e(m.an)}</span></h1>
  ${m.md?`<p class="fp-deck">${m.bi===1?'Модель ждёт ничью':`Модель считает фаворитом <b>${fav}</b>`}: ${H.pct(m.best)}&nbsp;% на этот исход.</p>
  <dl class="fp-nums">${cells.map((c,i)=>`<div class="${(c[0]==='П1'&&m.bi===0)||(c[0]==='Х'&&m.bi===1)||(c[0]==='П2'&&m.bi===2)?'on':''}"><dt>${c[0]}</dt><dd>${H.pct(c[1])}<small>%</small></dd><dd class="k">${c[2]?'кэф '+H.f2(c[2]):'&nbsp;'}</dd></div>`).join('')}</dl>`:''}
  <a class="fp-go" href="${m.href}">Все матчи ${m.hockey?'хоккея':'футбола'}</a>`;
}
if(hero)lead(hero);

function li(m){
 const p=m.md?`<b class="p${m.best>=.6?' hi':''}">${H.pct(m.best)}<small>%</small></b>`:'';
 const k=m.ln&&m.bi>=0?[m.ln.p1,m.ln.x,m.ln.p2][m.bi]:null;
 return `<li><a href="${m.href}"><time>${m.hm}<small>${m.day==='сегодня'?m.lgn:m.day}</small></time>
  <span class="nm"><span>${e(m.hn)}</span><span>${e(m.an)}</span></span>
  <span class="pk">${p}<small>${m.md?(m.bi===1?'ничья':e(m.who))+(k?', кэф '+H.f2(k):''):'расчёт скоро'}</small></span></a></li>`;
}
const fill=(id,list)=>{$(id).innerHTML=list.length?list.slice(0,6).map(li).join(''):'<li class="fp-none">Матчей пока нет.</li>'};
const rest=all.filter(m=>m!==hero);
fill('fp-h',rest.filter(m=>m.hockey));
fill('fp-f',rest.filter(m=>!m.hockey));
})();
