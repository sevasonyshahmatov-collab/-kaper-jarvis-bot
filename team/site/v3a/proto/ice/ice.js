/* JARVIS v3a · прототип «Белый лёд» · свой JS без библиотек.
   Данные: ../../data/today.js, model.js, lines.js, assets/club/themes.js. Нет данных — блок не рисуем. */
(()=>{
'use strict';
const D=document,H=D.documentElement;
const $=(s,r=D)=>r.querySelector(s),$$=(s,r=D)=>[...r.querySelectorAll(s)];
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const FINE=matchMedia('(hover:hover) and (pointer:fine)').matches;
H.classList.add('js');if(RM)H.classList.add('rm');

const T=window.JV_TODAY||{matches:[],days:[]},M=window.JV_MODEL||{},L=window.JV_LINES||{},C=window.CLUB_SET||{};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pc=p=>Math.round(p*100);
const f2=n=>Number(n).toFixed(2).replace('.',',');
const f1=n=>Number(n).toFixed(1).replace('.',',');
const em=id=>'../../assets/em/'+id+'.webp';
const MON=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
const tms=t=>{const m=/(\d+)-(\d+)-(\d+) (\d+):(\d+)/.exec(t);return Date.UTC(+m[1],m[2]-1,+m[3],m[4]-3,+m[5])};
const hhmm=t=>t.slice(11,16);
const col=id=>(C[id]&&C[id].ac)||'#1c5cc0';
const rgb=h=>{h=h.replace('#','');return[0,2,4].map(i=>parseInt(h.substr(i,2),16))};
const far=(a,b)=>{const x=rgb(a),y=rgb(b);return Math.hypot(x[0]-y[0],x[1]-y[1],x[2]-y[2])>130};
const colAway=(h,a)=>{const c1=col(h),c2=col(a);return far(c1,c2)?c2:((C[a]&&C[a].dk)||c2)};
const sq=p=>Math.sqrt(p).toFixed(3);

/* ── матчи ── */
const hockey=()=>(T.matches||[]).filter(m=>(m.lg==='khl'||m.lg==='nhl')&&M[m.key]).map(m=>({m,mo:M[m.key],li:L[m.key]||null,ms:tms(m.t),c1:col(m.h),c2:colAway(m.h,m.a)}));
const LGN={khl:'КХЛ',nhl:'НХЛ'};
const pageOf=x=>x.m.key==='khl|2026-11-05|avangard|cska'?'match.html':'hockey.html#'+x.m.key.replace(/\|/g,'_');
const normLine=li=>{if(!li||!li.p1||!li.p2)return null;const a=1/li.p1,b=li.x?1/li.x:0,c=1/li.p2,s=a+b+c;return{p1:a/s,x:b/s,p2:c/s}};
const pbar=x=>{const o=x.mo;return `<div class="pbar" style="--c1:${x.c1};--c2:${x.c2}" aria-hidden="true"><i style="flex:${o.p1}"></i><i style="flex:${o.x}"></i><i style="flex:${o.p2}"></i></div>`};
const pn=x=>{const o=x.mo;return `<div class="pn"><div><b>${pc(o.p1)} %</b><small>П1</small></div><div><b>${pc(o.x)} %</b><small>Х</small></div><div><b>${pc(o.p2)} %</b><small>П2</small></div></div>`};
const odds=x=>{const l=x.li;if(!l||!l.p1)return '';return `<div class="odds" title="Кэфы: справка, не рекомендация"><span><em>П1</em><b>${f2(l.p1)}</b></span><span><em>Х</em><b>${l.x?f2(l.x):'—'}</b></span><span><em>П2</em><b>${f2(l.p2)}</b></span></div>`};
const teams=x=>`<div class="mc-teams"><div class="tm"><img src="${em(x.m.h)}" alt="" loading="lazy" width="62" height="62"><b>${esc(x.m.hn)}</b></div><div class="tm"><img src="${em(x.m.a)}" alt="" loading="lazy" width="62" height="62"><b>${esc(x.m.an)}</b></div></div>`;

function miniCard(x){
  return `<div class="slab" data-r><div class="tilt-in"><a class="plate mc" href="${pageOf(x)}" style="--c1:${x.c1};--c2:${x.c2}">
    <div class="mc-top"><span>${LGN[x.m.lg]}</span><b>${hhmm(x.m.t)} МСК</b></div>${teams(x)}${pbar(x)}${pn(x)}${odds(x)}<span class="more">Расчёт матча</span></a></div></div>`;
}
const ARR='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12a8 8 0 1 1-2.6-5.9"/><path d="M20 4v5h-5"/></svg>';
function flipCard(x){
  const o=x.mo,l=x.li,n=normLine(l);
  const best=[['П1','победа '+x.m.hn,o.p1],['Х','ничья в основное время',o.x],['П2','победа '+x.m.an,o.p2]].sort((a,b)=>b[2]-a[2])[0];
  const row=(k,p,np,k2)=>`<tr><td>${k}</td><td>${pc(p)} %</td><td>${n?pc(np)+' %':'—'}</td><td>${l&&l[k2]?f2(l[k2]):'—'}</td></tr>`;
  const id=x.m.key.replace(/\|/g,'_');
  return `<div class="slab" id="${id}" data-r><div class="tilt-in"><div class="flip">
   <div class="face front" style="--c1:${x.c1};--c2:${x.c2}">
    <div class="mc-top"><span>${LGN[x.m.lg]}</span><b>${hhmm(x.m.t)} МСК</b></div>${teams(x)}${pbar(x)}${pn(x)}${odds(x)}
    <button class="flipbtn" type="button" aria-label="Почему модель так думает: ${esc(x.m.hn)} — ${esc(x.m.an)}">${ARR}Почему так считает модель</button></div>
   <div class="face back" style="--c1:${x.c1};--c2:${x.c2}">
    <h4>${esc(x.m.hn)} — ${esc(x.m.an)}</h4>
    <table class="why"><thead><tr><th>Исход</th><th>Модель</th><th>Линия без маржи</th><th>Кэф</th></tr></thead><tbody>${row('П1',o.p1,n&&n.p1,'p1')}${row('Х',o.x,n&&n.x,'x')}${row('П2',o.p2,n&&n.p2,'p2')}</tbody></table>
    <p>Модель выбирает самый вероятный исход: ${best[0]} — ${best[1]}, ${pc(best[2])} %. Ожидаемые голы ${f1(o.lam[0])} : ${f1(o.lam[1])}${o.tot?`, тотал ${f1(o.tot)}: больше — ${pc(o.over)} %`:''}.</p>
    <p class="muted">Кэфы — справка, не рекомендация. Модель, а не гарантия.</p>
    <div class="acts"><button class="flipbtn" type="button">${ARR}Назад</button><a href="${pageOf(x)}">Расчёт матча</a></div></div>
  </div></div></div>`;
}

/* ── табло матча дня ── */
const DAYKEY='khl|2026-11-05|avangard|cska';
function dayMatch(){const hs=hockey();return hs.find(x=>x.m.key===DAYKEY)||hs[0]}
function fillTablo(host){
  const x=dayMatch();if(!x||!host)return;const o=x.mo;
  const vt=host.hasAttribute('data-vt');
  host.innerHTML=`<div class="tablo-top"><span>${LGN[x.m.lg]}, матч дня</span><span>${hhmm(x.m.t)} МСК</span></div>
  <div class="tablo-teams"><div class="tm"><img ${vt?'class="vt-h" ':''}src="${em(x.m.h)}" alt="" width="88" height="88"><b>${esc(x.m.hn)}</b></div><span class="vs" aria-hidden="true">—</span><div class="tm"><img ${vt?'class="vt-a" ':''}src="${em(x.m.a)}" alt="" width="88" height="88"><b>${esc(x.m.an)}</b></div></div>
  <div class="nums" role="group" aria-label="Вероятности модели"><div><small>П1</small><output data-count="${pc(o.p1)}">${pc(o.p1)}</output></div><div><small>Х</small><output data-count="${pc(o.x)}">${pc(o.x)}</output></div><div><small>П2</small><output data-count="${pc(o.p2)}">${pc(o.p2)}</output></div></div>
  <div class="cd" data-cd="${x.ms}"><small>до начала</small><span>--:--:--</span></div>`;
  $$('[data-count]',host).forEach(countUp);tickCd();
}

/* ── счётчики ── */
function countUp(el){
  const v=parseFloat(el.dataset.count),dec=+(el.dataset.dec||0),suf=el.dataset.suf||'';
  const set=n=>{el.textContent=(dec?n.toFixed(dec).replace('.',','):Math.round(n))+suf};
  if(RM){set(v);return}
  set(0);
  const go=()=>{const t0=performance.now(),d=1100;const f=t=>{const k=Math.min(1,(t-t0)/d),e=1-Math.pow(1-k,3);set(v*e);if(k<1)requestAnimationFrame(f)};requestAnimationFrame(f)};
  if('IntersectionObserver'in window){const io=new IntersectionObserver(es=>{if(es[0].isIntersecting){io.disconnect();go()}},{threshold:.4});io.observe(el)}else go();
}
/* ── таймер ── */
function tickCd(){
  $$('[data-cd]').forEach(el=>{
    const ms=+el.dataset.cd-Date.now(),s=$('span',el),sm=$('small',el);
    if(ms<=0){s.textContent='матч начался';sm.textContent='';return}
    const t=Math.floor(ms/1000),h=Math.floor(t/3600),m=Math.floor(t%3600/60),c=t%60,p=n=>String(n).padStart(2,'0');
    s.textContent=p(h)+':'+p(m)+':'+p(c);
  });
}
setInterval(tickCd,1000);

/* ── список на главной ── */
const nx=$('#next');
if(nx){
  const hs=hockey().filter(x=>x.m.t.slice(0,10)===(T.days||[])[0]).sort((a,b)=>a.ms-b.ms);
  if(hs.length)nx.innerHTML=hs.map(miniCard).join('');
}
fillTablo($('#tablo'));

/* ── хоккей: колода, вкладки, строка, статистика, таблица ── */
const deck=$('#deck');
if(deck){
  const hs=hockey().sort((a,b)=>a.ms-b.ms),days=T.days||[];
  let day=days[0],lg='all';
  const render=()=>{
    const list=hs.filter(x=>x.m.t.slice(0,10)===day&&(lg==='all'||x.m.lg===lg));
    deck.innerHTML=list.length?list.map(flipCard).join(''):'<p class="muted">На этот день матчей нет.</p>';
    bindSlabs(deck);reveal(deck);
    const h=location.hash.slice(1);if(h&&$('#'+CSS.escape(h),deck))$('#'+CSS.escape(h),deck).classList.add('flipped');
  };
  const tabs=$('#daytabs');
  if(tabs){tabs.innerHTML=days.map((d,i)=>{const m=/\d+-(\d+)-(\d+)/.exec(d);return `<button type="button" role="tab" aria-selected="${i===0}" data-d="${d}">${i===0?'Сегодня':'Завтра'}, ${+m[2]} ${MON[m[1]-1]}</button>`}).join('')+
    ['all','khl','nhl'].map((k,i)=>`<button type="button" role="tab" aria-selected="${i===0}" data-l="${k}">${k==='all'?'Все лиги':LGN[k]}</button>`).join('');
    tabs.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
      if(b.dataset.d){day=b.dataset.d;$$('[data-d]',tabs).forEach(n=>n.setAttribute('aria-selected',n===b))}
      if(b.dataset.l){lg=b.dataset.l;$$('[data-l]',tabs).forEach(n=>n.setAttribute('aria-selected',n===b))}
      render()})}
  render();
  const tk=$('#ticker');
  if(tk){const items=hs.filter(x=>x.m.t.slice(0,10)===days[0]).map(x=>`<span><b>${esc(x.m.hn)} — ${esc(x.m.an)}</b> ${hhmm(x.m.t)} МСК  П1 ${pc(x.mo.p1)} %  Х ${pc(x.mo.x)} %  П2 ${pc(x.mo.p2)} %</span>`).join('');
    tk.innerHTML=`<div class="ticker-in">${items}${items}</div>`;}
  const st=$('#stats');
  if(st){const n=hs.length,nl=hs.filter(x=>x.li&&x.li.p1).length;
    const set=(i,v)=>{const o=$$('output',st)[i];o.dataset.count=v;o.textContent=v;countUp(o)};set(0,n);set(1,nl);set(2,2)}
  const pt=$('#ptab');
  if(pt){
    const rows=hs.filter(x=>x.m.t.slice(0,10)===days[0]||x.m.lg==='khl');
    const mk=x=>{const n=normLine(x.li),o=x.mo;
      const nm=`<div class="nm"><span><img src="${em(x.m.h)}" alt="" width="30" height="30" loading="lazy">${esc(x.m.hn)}</span><span><img src="${em(x.m.a)}" alt="" width="30" height="30" loading="lazy">${esc(x.m.an)}</span></div>`;
      const marks=n?`<i class="mk" style="left:${n.p1*100}%" title="Линия: П1 ${pc(n.p1)} %"></i><i class="mk b" style="left:${(n.p1+n.x)*100}%" title="Линия: П1+Х ${pc(n.p1+n.x)} %"></i>`:'';
      return `<a class="prow" href="${pageOf(x)}" data-r style="--c1:${x.c1};--c2:${x.c2}"><time>${hhmm(x.m.t)}</time>${nm}<div class="sc">${pbar(x)}${marks}<div class="sc-n"><span>П1 <em>${pc(o.p1)} %</em></span><span>Х <em>${pc(o.x)} %</em></span><span>П2 <em>${pc(o.p2)} %</em></span></div></div></a>`};
    pt.innerHTML=rows.slice(0,10).map(mk).join('');
  }
}

/* ── вкладки таблицы ── */
const sh=$('#sheets');
if(sh){
  const btns=$$('[role=tab]',sh),pan=$$('.panel',sh);let cur=0;
  const go=i=>{cur=(i+pan.length)%pan.length;btns.forEach((b,j)=>b.setAttribute('aria-selected',j===cur));pan.forEach((p,j)=>{p.hidden=j!==cur;p.classList.toggle('on',j===cur)});const pg=$('#pg');if(pg)pg.textContent=(cur+1)+' / '+pan.length};
  btns.forEach((b,i)=>b.addEventListener('click',()=>go(i)));
  $('#prev')?.addEventListener('click',()=>go(cur-1));$('#next2')?.addEventListener('click',()=>go(cur+1));go(0);
}

/* ── наклон, переворот ── */
function bindSlabs(root){
  $$('.slab',root).forEach(s=>{
    if(s.dataset.b)return;s.dataset.b=1;
    const tin=$('.tilt-in',s);
    if(FINE&&!RM){
      let raf=0,e0;
      const upd=()=>{raf=0;const r=s.getBoundingClientRect(),px=(e0.clientX-r.left)/r.width-.5,py=(e0.clientY-r.top)/r.height-.5;
        s.style.setProperty('--ry',(px*12).toFixed(2)+'deg');s.style.setProperty('--rx',(-py*12).toFixed(2)+'deg');
        s.style.setProperty('--sx',(-px*26).toFixed(1)+'px');s.style.setProperty('--sy',(-py*18).toFixed(1)+'px')};
      s.addEventListener('pointermove',e=>{if(e.pointerType==='touch')return;e0=e;s.classList.add('moving');if(!raf)raf=requestAnimationFrame(upd)});
      s.addEventListener('pointerleave',()=>{s.classList.remove('moving');['--rx','--ry','--sx','--sy'].forEach(k=>s.style.removeProperty(k))});
    }
    if($('.flip',s)){
      const toggle=()=>{s.classList.toggle('flipped');const f=s.classList.contains('flipped');
        $('.face.front .flipbtn',s)?.setAttribute('aria-expanded',f);};
      s.addEventListener('click',e=>{if(e.target.closest('a'))return;toggle()});
      $$('.flipbtn',s).forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();toggle()}));
    }
  });
}
bindSlabs(D);

/* ── появление при прокрутке, луч, рисование ── */
function reveal(root){
  const els=$$('[data-r],.steps,.pucks,.total,.tracks,.forms',root||D);
  if(!('IntersectionObserver'in window)||RM){els.forEach(n=>n.classList.add('in'));return}
  const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{threshold:.14,rootMargin:'0px 0px -6% 0px'});
  els.forEach(n=>{if(!n.classList.contains('in'))io.observe(n)});
}
reveal();
if(!RM){
  $$('[data-beam]').forEach(sec=>{
    const b=D.createElement('i');b.className='beam';b.setAttribute('aria-hidden','true');sec.prepend(b);
    if(sec.hasAttribute('data-beam-scroll')){const f=()=>{if(scrollY>30){b.classList.add('go');removeEventListener('scroll',f)}};addEventListener('scroll',f,{passive:true});return}
    const io=new IntersectionObserver(es=>{if(es[0].isIntersecting){b.classList.add('go');io.disconnect()}},{threshold:.25});io.observe(sec);
  });
  const sc=$('.scratch');
  if(sc){let tk=0;addEventListener('scroll',()=>{if(tk)return;tk=requestAnimationFrame(()=>{tk=0;sc.style.transform='translate3d(0,'+(-scrollY*.05).toFixed(1)+'px,0)'})},{passive:true})}
}
/* страница матча: числа от нуля */
$$('[data-count]').forEach(el=>{if(!el.closest('#tablo')&&!el.closest('#stats'))countUp(el)});
})();
