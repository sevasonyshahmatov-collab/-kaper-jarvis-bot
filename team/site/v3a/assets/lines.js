/* JARVIS v3a — линии и расчёт модели на главных страницах «Хоккей» и «Футбол».
   Данные: data/lines.js (JV_LINES), data/model.js (JV_MODEL), data/today.js (JV_TODAY) — их обновляет ежедневный конвейер, страницы только читают.
   Всё из данных экранируем esc(). Ключ матча: «лига|дата МСК|хозяева|гости». */
(()=>{
'use strict';
const L=window.JV_LINES||{},M=window.JV_MODEL||{},TD=window.JV_TODAY||{built:'',days:[],matches:[]};
const esc=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const SRC={};
const f2=v=>v==null||isNaN(v)?'—':(+v).toFixed(2).replace('.',',');
const f1=v=>v==null||isNaN(v)?'—':(+v).toFixed(1).replace('.',',');
const p0=v=>Math.round(v*100);
const key=(lg,t,h,a)=>`${lg}|${String(t).slice(0,10)}|${h}|${a}`;
/* «2026-11-04T05:23Z» (UTC) → «08:23» по Москве */
const hhmm=t=>{const ms=Date.parse(t);return isNaN(ms)?'':new Date(ms+3*3600e3).toISOString().slice(11,16)};
const ddmm=t=>String(t).slice(8,10)+'.'+String(t).slice(5,7);
const srcLabel=ln=>!ln?'':(ln.t?'обновлена в '+hhmm(ln.t)+' МСК':'рынок');
const verName=v=>String(v||'').replace(/\s*\(.*\)$/,'');
/* доли линии без маржи: из обратных кэфов */
const fair=ln=>{if(!ln)return null;const inv=[1/ln.p1,ln.x?1/ln.x:0,1/ln.p2],s=inv[0]+inv[1]+inv[2];return inv.map(v=>v/s)};
const fairTot=ln=>{if(!ln||!ln.over||!ln.under)return null;const a=1/ln.over,b=1/ln.under;return a/(a+b)};
/* расхождения модели с линией: исходы и тотал (если линия тотала совпадает с расчётной), порог — больше 5 п.п. */
const TH=6;
function diffs(ln,md){const out=[];if(!ln||!md)return out;const fl=fair(ln),mo=[md.p1,md.x,md.p2],lab=['П1','Х','П2'];
 mo.forEach((p,i)=>{if(i===1&&!ln.x)return;out.push({k:lab[i],pm:p,pl:fl[i]})});
 const ft=fairTot(ln);if(ft!=null&&md.over!=null&&ln.tot===md.tot)out.push({k:'ТБ '+f1(md.tot),pm:md.over,pl:ft});
 out.forEach(o=>{o.d=Math.round((o.pm-o.pl)*100)});return out}
const flagged=(ln,md)=>diffs(ln,md).filter(o=>Math.abs(o.d)>=TH);
const dvHtml=(ln,md)=>{const f=flagged(ln,md);if(!f.length)return '';
 const up=f.filter(o=>o.d>0),dn=f.filter(o=>o.d<0),s=a=>a.map(o=>`${esc(o.k)} ${o.d>0?'+':'−'}${Math.abs(o.d)}&nbsp;п.п.`).join(', ');
 return `<span class="dv" title="Разница между вероятностью модели и долей линии без маржи; порог — больше 5 п.п.">${up.length?`<b class="up">модель выше линии:</b> ${s(up)}`:''}${up.length&&dn.length?' · ':''}${dn.length?`<b class="dn">модель ниже линии:</b> ${s(dn)}`:''}</span>`};
const modelLine=(md,opt={})=>{if(!md)return '';const a=[`П1 ${p0(md.p1)} %`,`Х ${p0(md.x)} %`,`П2 ${p0(md.p2)} %`];
 if(md.over!=null)a.push(`ТБ ${f1(md.tot)} ${p0(md.over)} %`);if(opt.btts&&md.btts!=null)a.push(`обе забьют ${p0(md.btts)} %`);
 return `<span class="mlab">Модель JARVIS:</span> ${a.join(' · ')}`};

/* ── блок в строке матча: кэфы линии (доля линии под кэфом), тотал, модель, источник и пометка расхождения ── */
function quotes(m,opt={}){const {ln,md}=m,fl=fair(ln),pm=md?[md.p1,md.x,md.p2]:null,base=fl||pm,mx=base?Math.max(...base):0;
 const q=['П1','Х','П2'].map((k,j)=>{const v=ln?(j===0?ln.p1:j===1?ln.x:ln.p2):null;
  return `<span class="qc${base&&base[j]===mx?' fav':''}"><small>${k}</small><b class="num">${v?f2(v):'—'}</b><em class="num">${base?p0(base[j])+'%':''}</em></span>`}).join('');
 const tot=ln&&ln.tot!=null&&ln.over?`<div class="qt">Тотал ${f1(ln.tot)} <span>Б <b class="num">${f2(ln.over)}</b></span><span>М <b class="num">${f2(ln.under)}</b></span></div>`:'';
 const src=ln?`<div class="qs">Линия: ${esc(srcLabel(ln))}</div>`
  :`<div class="qs">${esc(opt.noLine||'Линии пока нет')}</div>`;
 return `<div class="q3">${q}</div>${tot}${md?`<div class="qm">${modelLine(md,opt)}</div>`:''}${dvHtml(ln,md)?`<div class="qd">${dvHtml(ln,md)}</div>`:''}${src}`}

/* ── раскрытая строка: расчёт модели ── */
const bar=(lab,pm,pl,fav)=>`<div class="wb${fav?' fav':''}"><span>${esc(lab)}</span><em><i style="--w:${p0(pm)}%"></i>${pl!=null?`<u style="left:${p0(pl)}%" title="линия: ${p0(pl)} %"></u>`:''}</em><b class="num">${p0(pm)} %</b></div>`;
function why(m,opt={}){const {ln,md}=m;if(!md)return '<p class="none">Расчёта модели на этот матч нет.</p>';
 const fl=fair(ln),mo=[md.p1,md.x,md.p2],mx=Math.max(...mo),names=[m.hn||'хозяева',m.an||'гости'];
 const rows=['П1 · '+names[0],'Х · ничья в основное время','П2 · '+names[1]].map((l,i)=>bar(l,mo[i],fl&&(i!==1||ln.x)?fl[i]:null,mo[i]===mx)).join('');
 let totals='';
 if(md.totals){const ent=Object.entries(md.totals).sort((a,b)=>a[0]-b[0]);
  totals=`<div class="wsub"><h5>Тотал матча: вероятность «больше»</h5>${ent.map(([t,p])=>bar('Больше '+f1(t),p,ln&&ln.tot===+t?fairTot(ln):null,false)).join('')}
</div>`}
 else if(md.over!=null){totals=`<div class="wsub"><h5>Тотал ${f1(md.tot)}</h5>${bar('Больше '+f1(md.tot),md.over,ln&&ln.tot===md.tot?fairTot(ln):null,false)}${bar('Меньше '+f1(md.tot),1-md.over,null,false)}
   ${md.btts!=null?bar('Обе команды забьют',md.btts,null,false):''}</div>`}
 const fin=md.w1!=null&&md.w2!=null?`<div class="wsub"><h5>Итоговая победа, с овертаймом и буллитами</h5>${bar(names[0],md.w1,ln&&ln.fin1&&ln.fin2?(1/ln.fin1)/(1/ln.fin1+1/ln.fin2):null,md.w1>md.w2)}${bar(names[1],md.w2,null,md.w2>md.w1)}</div>`:'';
 const lam=md.lam?`<p class="xlam"><b>Ожидаемые голы:</b> ${esc(names[0])} <b class="num">${f2(md.lam[0])}</b> — ${esc(names[1])} <b class="num">${f2(md.lam[1])}</b>, вместе <b class="num">${f2(md.lam[0]+md.lam[1])}</b>.</p>`:'';
 return `<section class="xb x-model"><h4>Расчёт модели <span class="note">${esc(verName(md.ver))}, ${esc(hhmm(md.t))} МСК</span></h4>
  <div class="wgrid"><div class="wsub"><h5>Исход в основное время</h5>${rows}${ln?'':'<p class="note">Линии на матч пока нет.</p>'}</div>
  ${totals}${fin}</div>${lam}${dvHtml(ln,md)?`<p class="qd">${dvHtml(ln,md)}</p>`:''}
  </section>`}

/* ── секция «Прогноз модели» (#model): все матчи окна с вероятностями модели и линией ── */
function section(root,items,cfg){
 if(!root)return; // на странице нет блока #modelbox (например, ЛЧ)
 const nDiv=items.filter(it=>flagged(it.ln,it.md).length).length,hasModel=items.filter(it=>it.md).length;
 const ver=[...new Set(items.filter(it=>it.md).map(it=>verName(it.md.ver)))].join(', ');
 const upd=TD.built?`${ddmm(TD.built)} в ${TD.built.slice(11,16)} МСК`:'';
 let mode='all';
 root.innerHTML=`<div class="mtoolbar"><div class="tabs" role="tablist" aria-label="Какие матчи показать"><button class="tab" role="tab" aria-selected="true" data-m="all">Все матчи <span class="c">${items.length}</span></button><button class="tab" role="tab" aria-selected="false" data-m="div">Модель расходится с линией <span class="c">${nDiv}</span></button></div></div>
  <ul class="mrows" id="mrows" aria-live="polite"></ul>
  <div class="mexplain"><h3>Как считает модель</h3>${cfg.explain}
</div>
  <p class="mver note">Модель: ${esc(ver||'—')}${upd?` · данные обновлены ${upd}`:''} · с расчётом ${hasModel} из ${items.length}.</p>`;
 const ul=root.querySelector('#mrows');
 const rowHtml=it=>{const {ln,md}=it,mo=md?[md.p1,md.x,md.p2]:null,mx=mo?Math.max(...mo):0,fl=fair(ln),f=flagged(ln,md);
  const bars=mo?['П1','Х','П2'].map((k,i)=>`<div class="wb${mo[i]===mx?' fav':''}"><span>${k}</span><em><i style="--w:${p0(mo[i])}%"></i>${fl&&(i!==1||ln.x)?`<u style="left:${p0(fl[i])}%" title="линия: ${p0(fl[i])} %"></u>`:''}</em><b class="num">${p0(mo[i])} %</b></div>`).join(''):'<p class="note">Расчёта нет</p>';
  const lineTxt=ln?`<div class="ml-k num">П1 <b>${f2(ln.p1)}</b>${ln.x?` · Х <b>${f2(ln.x)}</b>`:''} · П2 <b>${f2(ln.p2)}</b></div><small>${esc(srcLabel(ln))}</small>`:`<small>${esc(cfg.noLine||'Линии пока нет')}</small>`;
  const totTxt=md&&md.over!=null?`<div>ТБ ${f1(md.tot)}: <b class="num">${p0(md.over)} %</b>${ln&&ln.tot!=null&&ln.over?` <small>линия ${f1(ln.tot)}: Б ${f2(ln.over)} / М ${f2(ln.under)}</small>`:''}</div>`:'';
  const bt=cfg.btts&&md&&md.btts!=null?`<div>Обе забьют: <b class="num">${p0(md.btts)} %</b></div>`:'';
  const lam=md&&md.lam?`<div class="ml-lam">Ожидаемые голы: <b class="num">${f1(md.lam[0])} : ${f1(md.lam[1])}</b></div>`:'';
  return `<li class="mr${f.length?' dvg':''}"><div class="mr-t"><time>${esc(it.t.slice(11))}</time><small>${esc(ddmm(it.t))}</small></div>
   <div class="mr-m"><div class="lgline">${it.lgHtml}</div><div class="teams"><div class="team">${it.home}</div><div class="team">${it.away}</div></div></div>
   <div class="mr-l"><h6>Линия</h6>${lineTxt}</div><div class="mr-p"><h6>Модель JARVIS</h6>${bars}</div>
   <div class="mr-x"><h6>Тотал${cfg.btts?' и «обе забьют»':''}</h6>${totTxt}${bt}${lam}${f.length?`<div class="qd">${dvHtml(ln,md)}</div>`:''}</div></li>`};
 function draw(){const sel=mode==='div'?items.filter(it=>flagged(it.ln,it.md).length):items;let html='',prev='';
  sel.forEach(it=>{const d=it.t.slice(0,10);if(d!==prev){prev=d;html+=`<li class="dayh" aria-hidden="true">${esc(it.dayLabel(d))}</li>`}html+=rowHtml(it)});
  ul.innerHTML=html||'<li class="note empty">Сейчас нет матчей, где модель расходится с линией больше чем на 5 п.п.</li>';
  root.querySelectorAll('.tab').forEach(t=>t.setAttribute('aria-selected',t.dataset.m===mode))}
 root.querySelector('.tabs').addEventListener('click',e=>{const t=e.target.closest('.tab');if(t){mode=t.dataset.m;draw()}});
 draw()}

window.JVL={L,M,TD,esc,SRC,f1,f2,p0,key,hhmm,ddmm,srcLabel,verName,fair,fairTot,diffs,flagged,dvHtml,modelLine,quotes,why,section,
 line:k=>L[k]||null,model:k=>M[k]||null,
 /* дата начала матча по Москве — для подписи «сегодня/завтра» */
 mskDay:ms=>new Date(ms+3*3600e3).toISOString().slice(0,10),
 /* игровой день — одно правило на весь сайт (владелец 09.11): с 06:00 МСК до 06:00 следующего дня, ночь НХЛ — к вечеру накануне.
    gday('ГГГГ-ММ-ДД ЧЧ:ММ' МСК) → 'ГГГГ-ММ-ДД'; gdayNow(+дни) — текущий игровой день; isToday(m) — матч сегодняшнего игрового дня (все, включая сыгранные: «сегодня N матчей» везде одно число) */
 gday:t=>new Date(Date.parse(String(t).slice(0,16).replace(' ','T')+':00Z')-6*3600e3).toISOString().slice(0,10),
 gdayNow:(add=0)=>new Date(Date.now()+3*3600e3-6*3600e3+add*864e5).toISOString().slice(0,10),
 isToday:m=>window.JVL.gday(m.t)===window.JVL.gdayNow()};
})();
