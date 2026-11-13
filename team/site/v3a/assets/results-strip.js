/* JARVIS v3a — полоса «Честные итоги» на главной и в разделах: последний расчётный день, счёт месяца и общий счёт.
   Данные — data/results-lite.js (window.__RESLITE, daily/results.py). Разметка: <div class="rsx" id="rsx" data-root=""></div>;
   нет данных — блок остаётся как был (запасной текст внутри). */
(()=>{
const D=window.__RESLITE,box=document.getElementById('rsx');if(!D||!D.sum)return;
const hr=document.getElementById('hm-res');if(hr){const a=D.sum.total.all;hr.textContent='Итоги: зашло '+a.w+' из '+(a.w+a.l)}
/* компактная полоса «Честные итоги» в разделах Хоккей / Футбол (задание 14.11, п. 4): три цифры — те же данные */
{const pf=document.getElementById('pf');if(pf){const A=D.sum.total.all,S=D.sum.total[pf.dataset.sport],$=id=>document.getElementById(id);
 const n1=x=>Number(x).toFixed(1).replace('.',','),sg=x=>(x>0?'+':x<0?'−':'')+n1(Math.abs(x));
 const MG=['','января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
 $('pfW').innerHTML=`${A.w}<small> из ${A.w+A.l}</small>`;$('pfR').textContent=Math.round(A.w/(A.w+A.l)*100)+' %';
 $('pfU').innerHTML=`${sg(A.units)}<small> ед.</small>`;$('pfU').parentNode.classList.add(A.units>=0?'pos':'neg');
 $('pfS').textContent=`Все прогнозы канала с ${+D.since.slice(8,10)} ${MG[+D.since.slice(5,7)]}`+(S&&S.w+S.l?`, из них ${pf.dataset.sport==='hockey'?'хоккей':'футбол'} — ${S.w} из ${S.w+S.l}`:'')+'. Со счётом матча и ссылкой на пост, минусы — в том же списке.'}}
if(!box)return;
const root=box.dataset.root||'';
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const num=(x,d)=>Number(x).toFixed(d==null?2:d).replace('.',',');
const sign=x=>(x>0?'+':x<0?'−':'')+num(Math.abs(x),1);
const MG=['','января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
const day=s=>+s.slice(8,10)+' '+MG[+s.slice(5,7)];
const now=new Date(Date.now()+3*36e5),iso=d=>d.toISOString().slice(0,10),yd=iso(new Date(now-864e5));
const when=D.last_day===iso(now)?'Сегодня':D.last_day===yd?'Вчера':day(D.last_day);
const rows=D.last||[],w=rows.filter(p=>p.r==='w').length,l=rows.filter(p=>p.r==='l').length;
const mark={w:'✓',l:'✕',p:'↩'},word={w:'зашёл',l:'не зашёл',p:'возврат'};
const A=D.sum.total.all,M=(D.sum.months||[])[0];
box.innerHTML=`<div class="rsx-box"><h3>${when}: ${w} из ${w+l}<span>${when===day(D.last_day)?'последний расчётный день':day(D.last_day)}</span></h3>
 <ul class="rsx-rows">${rows.slice(0,7).map(p=>`<li class="${p.r}"><i aria-label="${word[p.r]}">${mark[p.r]}</i><span>${p.kind==='express'?esc(p.bet):esc(p.h)+' — '+esc(p.a)+(p.sc?' '+esc(p.sc):'')}<small>${p.kind==='express'?p.legs.map(x=>esc(x.h)+' — '+esc(x.a)).join(' · '):esc(p.bet)}</small></span><em>${p.kef?num(p.kef):''}</em></li>`).join('')}</ul>
 ${rows.length>7?`<p class="rs-note">И ещё ${rows.length-7} — на странице итогов.</p>`:''}</div>
<div class="rsx-box"><h3>${M?esc(M.name.split(' ')[0]):'Всего'}${M&&M.live?'<span>месяц идёт</span>':''}</h3>
 <dl class="rsx-nums">
  ${M?`<div><dt>зашло за месяц</dt><dd>${M.all.w} из ${M.all.w+M.all.l}</dd></div><div class="${M.all.units>=0?'pos':'neg'}"><dt>результат месяца при ставке 1</dt><dd>${sign(M.all.units)}<small>ед.</small></dd></div>`:''}
  <div><dt>зашло всего, с ${day(D.since)}</dt><dd>${A.w} из ${A.w+A.l}</dd></div><div class="${A.units>=0?'pos':'neg'}"><dt>результат за всё время</dt><dd>${sign(A.units)}<small>ед.</small></dd></div>
 </dl>
 <div class="rsx-foot"><a class="btn btn-ink" href="${esc(root)}results.html">Все прогнозы и итоги</a><p>Со счётом матча и ссылкой на пост. Минусы в том же списке.</p></div></div>`;
})();
