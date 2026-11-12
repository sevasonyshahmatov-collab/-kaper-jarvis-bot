/* Шаблон B «Рейтинг уверенности»: список матчей как турнирная таблица, строка — полоса вероятностей. */
(()=>{
const H=window.HOME,$=id=>document.getElementById(id);
if(!H||!H.J)return;
const e=H.esc;
$('rk-date').textContent=H.dateStr();
$('rk-upd').textContent=H.upd();
const all=H.all();
let f='all',s='p';

const seg=(cls,v,lab)=>{const w=Math.round(v*100);return `<i class="${cls}" style="flex:${Math.max(v,.02)}"><span>${w>=11?w:''}</span></i>`};
function row(m,i){
 const pr=m.pr;
 const bar=pr?`<div class="rk-pb" role="img" aria-label="Победа хозяев ${H.pct(pr[0])} %, ничья ${H.pct(pr[1])} %, победа гостей ${H.pct(pr[2])} %">${seg('c1',pr[0])}${seg('c0',pr[1])}${seg('c2',pr[2])}</div>`:'<div class="rk-pb none">Расчёт скоро</div>';
 const k=m.ln&&m.bi>=0?[m.ln.p1,m.ln.x,m.ln.p2][m.bi]:null;
 const rank=s==='p'&&pr?`<b class="rk-n">${i+1}</b>`:'<b class="rk-n"></b>';
 return `<li class="${m.best>=.6?'top':''}"><a href="${m.href}">
  ${rank}
  <time>${m.hm}<small>${m.day==='сегодня'?m.lgn:m.day+', '+m.lgn}</small></time>
  <span class="rk-tm"><span><img src="${m.hc}" alt="" width="26" height="26" loading="lazy">${e(m.hn)}</span><span><img src="${m.ac}" alt="" width="26" height="26" loading="lazy">${e(m.an)}</span></span>
  ${bar}
  <span class="rk-pk">${pr?`<b>${H.pct(m.best)}<small>%</small></b><small>${m.bi===1?'ничья':e(m.who)}${k?`, кэф ${H.f2(k)}`:''}</small>`:''}</span>
 </a></li>`;
}
function render(){
 let a=all.filter(m=>f==='all'||(f==='h')===m.hockey);
 a=a.slice().sort(s==='p'?(x,y)=>y.best-x.best||x.t.localeCompare(y.t):(x,y)=>x.t.localeCompare(y.t));
 const n=a.length;a=a.slice(0,14);
 $('rk-list').innerHTML=a.length?a.map(row).join(''):'<li class="rk-none">Матчей пока нет.</li>';
}
document.querySelectorAll('.rk-tabs button').forEach(b=>b.addEventListener('click',()=>{
 const g=b.parentElement;g.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));
 if(b.dataset.f)f=b.dataset.f;if(b.dataset.s)s=b.dataset.s;render();
}));
if(all.length)render();
})();
