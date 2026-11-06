/* Шаблон C «Стена эмблем»: матч дня и 8 ближайших — плитки из двух эмблем. */
(()=>{
const H=window.HOME,$=id=>document.getElementById(id);
if(!H||!H.J)return;
const e=H.esc;
$('cw-date').textContent=H.dateStr();
$('cw-upd').textContent=H.upd()?H.upd()+'.':'';
const all=H.all();
if(!all.length)return;
const cnt=(l,el,fb)=>{const n=l.filter(m=>m.day==='сегодня').length;el.textContent=n?`${n} ${H.pl(n,'матч','матча','матчей')} сегодня`:l.length?`${l.length} ${H.pl(l.length,'матч','матча','матчей')} скоро`:fb};
cnt(all.filter(m=>m.hockey),$('cw-ch'),'КХЛ и НХЛ');cnt(all.filter(m=>!m.hockey),$('cw-cf'),'топ-лиги Европы');

const hero=H.hero(all);
const rest=all.filter(m=>m!==hero&&m.md);
/* поровну хоккея и футбола, дальше по времени */
const hk=rest.filter(m=>m.hockey).slice(0,4),fb=rest.filter(m=>!m.hockey).slice(0,4);
const tiles=hk.concat(fb).sort((a,b)=>a.t.localeCompare(b.t)).slice(0,8);

function pair(m,big){
 return `<span class="cw-pair"><span class="cr"><img src="${m.hc}" alt="" width="${big?120:56}" height="${big?120:56}"></span><span class="cr"><img src="${m.ac}" alt="" width="${big?120:56}" height="${big?120:56}"></span></span>`;
}
function tile(m,i){
 const k=m.ln&&m.bi>=0?[m.ln.p1,m.ln.x,m.ln.p2][m.bi]:null;
 return `<a class="cw-t" style="--i:${i}" href="${m.href}" aria-label="${e(m.hn)} — ${e(m.an)}, ${m.hm} МСК">
  ${pair(m)}
  <span class="nm">${e(m.hn)}<i>—</i>${e(m.an)}</span>
  <span class="meta">${m.hm}, ${m.day==='сегодня'?m.lgn:m.day}</span>
  <span class="pk"><b>${H.pct(m.best)}<small>%</small></b><span>${m.bi===1?'ничья':e(m.who)}${k?`<br>кэф ${H.f2(k)}`:''}</span></span></a>`;
}
function big(m){
 const cells=[['П1',m.pr[0]],['Х',m.pr[1]],['П2',m.pr[2]]].filter(c=>c[1]!=null&&!(c[0]==='Х'&&m.hockey&&!(m.ln&&m.ln.x)));
 return `<a class="cw-t cw-hero" style="--i:0" href="${m.href}" aria-label="Матч дня: ${e(m.hn)} — ${e(m.an)}">
  <span class="tag">Матч дня</span>
  ${pair(m,true)}
  <span class="nm">${e(m.hn)}<i>—</i>${e(m.an)}</span>
  <span class="meta">${m.hm}, ${m.day==='сегодня'?m.lgn:m.day+', '+m.lgn}</span>
  <span class="nums">${cells.map((c,j)=>`<span class="${(c[0]==='П1'&&m.bi===0)||(c[0]==='Х'&&m.bi===1)||(c[0]==='П2'&&m.bi===2)?'on':''}"><small>${c[0]}</small><b>${H.pct(c[1])}<em>%</em></b></span>`).join('')}</span></a>`;
}
$('wall').innerHTML=(hero&&hero.md?big(hero):'')+tiles.map((m,i)=>tile(m,i+1)).join('');
})();
