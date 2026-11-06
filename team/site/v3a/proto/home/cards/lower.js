/* Нижние блоки главной «Карточки»: карточка дня, колода матчей, лиги, призыв. Данные те же (HOME из ../common.js, JVL из assets/lines.js).
   Наклон и блик — общий движок (rAF только пока карточка двигается), переворот — CSS-переход, появление — IntersectionObserver.
   prefers-reduced-motion: без наклона и анимаций. ?demo: ссылки не уводят со страницы. */
(()=>{
'use strict';
const H=window.HOME;if(!H||!H.J)return;
const J=H.J,e=H.esc,R=H.R;
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const DEMO=/[?&]demo/.test(location.search);
const $=s=>document.querySelector(s);
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const all=H.all();
const f1=v=>J.f1(v),f2=v=>J.f2(v),p0=v=>J.p0(v);

/* ── движок наклона: держит в цикле только карточки, которые ещё движутся ── */
const live=new Set();let loop=0;
function tick(){
 loop=0;
 live.forEach(s=>{
  const k=s.ptr?.2:.1;
  s.rx+=(s.tx-s.rx)*k;s.ry+=(s.ty-s.ry)*k;s.mx+=(s.tmx-s.mx)*k;s.my+=(s.tmy-s.my)*k;s.s+=(s.ts-s.s)*.16;
  const st=s.el.style,hi=.2+.8*Math.min(1,Math.hypot(s.rx,s.ry)/s.max);
  st.setProperty('--rx',s.rx.toFixed(2));st.setProperty('--ry',s.ry.toFixed(2));st.setProperty('--mx',s.mx.toFixed(1));st.setProperty('--my',s.my.toFixed(1));
  st.setProperty('--hi',hi.toFixed(2));st.setProperty('--s',s.s.toFixed(3));
  if(!s.ptr&&Math.abs(s.rx)+Math.abs(s.ry)<.05&&Math.abs(s.s-1)<.002)live.delete(s);
 });
 if(live.size)loop=requestAnimationFrame(tick);
}
function tilt(el,max,scale){
 const s={el,max,rx:0,ry:0,tx:0,ty:0,mx:50,my:50,tmx:50,tmy:50,s:1,ts:1,ptr:false,rect:null};
 if(RM){el.style.setProperty('--mx',38);el.style.setProperty('--my',30);el.style.setProperty('--hi',.5);return s}
 const wake=()=>{live.add(s);if(!loop)loop=requestAnimationFrame(tick)};
 const mv=ev=>{
  if(ev.pointerType==='touch')return;
  const r=s.rect||(s.rect=el.getBoundingClientRect());
  const px=clamp((ev.clientX-r.left)/r.width,0,1),py=clamp((ev.clientY-r.top)/r.height,0,1);
  s.ptr=true;s.ty=(px-.5)*2*max;s.tx=-(py-.5)*2*max;s.tmx=px*100;s.tmy=py*100;s.ts=scale;wake();
 };
 el.addEventListener('pointerenter',ev=>{s.rect=el.getBoundingClientRect();mv(ev)});
 el.addEventListener('pointermove',mv);
 el.addEventListener('pointerleave',()=>{s.ptr=false;s.tx=s.ty=0;s.tmx=s.tmy=50;s.ts=1;s.rect=null;wake()});
 return s;
}
addEventListener('scroll',()=>{live.forEach(s=>{s.rect=null})},{passive:true});

/* ── общее: ссылки, эмблемы, время ── */
const slug=t=>String(t).replace(/_/g,'-');
function href(m){
 const k=String(m.key).split('|');
 if(m.lg==='nhl'||k.length<4)return m.href;
 return `${R}${m.lg}/${k[1]}-${slug(k[2])}-${slug(k[3])}/index.html`;
}
const crest=(src,cls='')=>`<span class="cr ${cls}"><img src="${src}" alt="" draggable="false" loading="lazy" onerror="this.style.display='none'"></span>`;
const lgLogo=lg=>`${R}assets/lg/${lg}.webp`;
const when=m=>`${m.day==='сегодня'?'сегодня':m.day}, ${m.hm} МСК`;
const kf=m=>m.ln&&m.bi>=0?[m.ln.p1,m.ln.x,m.ln.p2][m.bi]:null;
const side=m=>m.bi===1?'Ничья':m.who;
function flip(card){
 const on=!card.classList.contains('is-flip');
 card.classList.toggle('is-flip',on);card.setAttribute('aria-pressed',on);
 card.querySelectorAll('.back a').forEach(a=>a.tabIndex=on?0:-1);
}
function wireFlip(card){
 card.addEventListener('click',ev=>{
  const a=ev.target.closest('a');
  if(a){ev.stopPropagation();if(DEMO)ev.preventDefault();return}
  if(card.dataset.drag==='1'){card.dataset.drag='0';return}
  flip(card);
 });
 card.addEventListener('keydown',ev=>{if((ev.key==='Enter'||ev.key===' ')&&ev.target===card){ev.preventDefault();flip(card)}});
}

/* ── а) Карточка дня ── */
(()=>{
 const st=$('#dc-stage'),m=H.hero(all);
 if(!m||!m.md){st.innerHTML='<p class="xnone">Сегодня расчёта модели ещё нет. Загляни позже.</p>';return}
 const md=m.md,hk=m.hockey,ln=m.ln,fl=ln&&J.fair?J.fair(ln):null;
 const pr=[md.p1,md.x,md.p2],lab=['П1','Х','П2'],mx=Math.max(...pr);
 const rows=[];
 if(md.lam)rows.push(`Ожидаемые голы: <b>${e(m.hn)} ${f2(md.lam[0])}</b> — <b>${e(m.an)} ${f2(md.lam[1])}</b>, вместе ${f2(md.lam[0]+md.lam[1])}.`);
 if(md.over!=null)rows.push(`Тотал ${f1(md.tot)}: «больше» — <b>${p0(md.over)} %</b>${!hk&&md.btts!=null?`, обе забьют — <b>${p0(md.btts)} %</b>`:''}.`);
 if(fl&&fl[m.bi]!=null){const d=p0(m.best)-p0(fl[m.bi]);rows.push(`Рынок без маржи даёт на этот исход <b>${p0(fl[m.bi])} %</b>, модель — <b>${p0(m.best)} %</b>${d?` (${d>0?'выше':'ниже'} на ${Math.abs(d)} п.п.)`:' (совпадают)'}.`)}
 else if(hk&&md.w1!=null&&md.w2!=null)rows.push(`С овертаймом и буллитами: ${e(m.hn)} <b>${p0(md.w1)} %</b>, ${e(m.an)} <b>${p0(md.w2)} %</b>.`);
 if(rows.length<3&&md.x!=null)rows.push(`Ничья в основное время — <b>${p0(md.x)} %</b>.`);
 const kv=kf(m);
 st.innerHTML=`<div class="xtc dc ${hk?'ice':'pitch'}" id="dc" role="button" tabindex="0" aria-pressed="false" aria-label="Карточка дня: ${e(m.hn)} — ${e(m.an)}. Нажми, чтобы узнать почему">
 <div class="shd"></div><div class="tilt"><div class="flip">
  <div class="face front"><div class="art"><i class="holo"></i><i class="holo2"></i></div><div class="frame rare"></div>
   <div class="dc-top"><span class="chip">Редкая · карточка дня</span><span class="when"><img src="${lgLogo(m.lg)}" alt="" onerror="this.style.display='none'"> ${e(m.lgn)} · ${e(when(m))}</span></div>
   <div class="dc-mid">
    <div class="xtm">${crest(m.hc)}<b>${e(m.hn)}</b></div>
    <div class="xpb"><strong class="num">${p0(m.best)}<small>%</small></strong><span>${m.bi===1?'ничья':'победа: '+e(side(m))}</span></div>
    <div class="xtm">${crest(m.ac)}<b>${e(m.an)}</b></div>
   </div>
   <div class="dc-bot"><div class="strip" role="img" aria-label="Вероятности: ${lab.map((l,i)=>l+' '+p0(pr[i])+' %').join(', ')}">${pr.map((p,i)=>`<i class="${p===mx?'on':''}" style="--w:${p0(p)}"><em>${lab[i]}</em> <b class="num">${p0(p)} %</b></i>`).join('')}</div>
    ${kv?`<span class="odd">кэф <b class="num">${f2(kv)}</b></span>`:''}<span class="hnt">Нажми — почему так</span></div>
  </div>
  <div class="face back"><div class="art"><i class="holo"></i><i class="holo2"></i></div><div class="frame rare"></div>
   <div class="bk2"><p class="kick">Почему так · модель JARVIS</p><ol>${rows.slice(0,3).map(r=>`<li>${r}</li>`).join('')}</ol>
    <a class="xgo" href="${href(m)}" tabindex="-1">К матчу <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.6" aria-hidden="true"><path d="M3 10h13M11 4l6 6-6 6"/></svg></a></div>
  </div>
 </div></div></div>`;
 const c=$('#dc');tilt(c,9,1.02);wireFlip(c);
})();

/* ── б) Матчи дня: колода ── */
(()=>{
 const row=$('#md-row'),chips=$('#md-chips'),sub=$('#md-sub');
 const td=all.filter(m=>m.day==='сегодня');
 const base=(td.length>=6?td:all).slice(0,40);
 const isTd=td.length>=6;
 sub.textContent=isTd?`${td.length} ${H.pl(td.length,'матч','матча','матчей')} сегодня. Листай, перетаскивай мышью, нажми на карточку.`:`Сегодня матчей мало, показываем ближайшие. Листай, нажми на карточку.`;
 const cnt={all:base.length,hk:base.filter(m=>m.hockey).length,fb:base.filter(m=>!m.hockey).length};
 const FL=[['all','Все'],['hk','Хоккей'],['fb','Футбол']].filter(([k])=>k==='all'||cnt[k]);
 let cur='all';
 chips.innerHTML=FL.map(([k,t])=>`<button type="button" class="chipb${k===cur?' on':''}" data-f="${k}" aria-pressed="${k===cur}">${t} <small>${cnt[k]}</small></button>`).join('');
 const mini=(m,i)=>{
  const md=m.md,kv=kf(m),pr=md?[md.p1,md.x,md.p2]:null,mx=pr?Math.max(...pr):0;
  return `<div class="xtc mc ${m.hockey?'ice':'pitch'}" role="button" tabindex="0" aria-pressed="false" style="--i:${Math.min(i,8)}" aria-label="${e(m.hn)} — ${e(m.an)}, ${e(when(m))}">
  <div class="shd"></div><div class="tilt"><div class="flip">
   <div class="face front"><div class="art"><i class="holo"></i><i class="holo2"></i></div><div class="frame"></div>
    <div class="mc-top"><span class="lgn"><img src="${lgLogo(m.lg)}" alt="" onerror="this.style.display='none'">${e(m.lgn)}</span><time>${m.hm}</time></div>
    <div class="mc-cr">${crest(m.hc)}${crest(m.ac)}</div>
    <p class="mc-nm"><span>${e(m.hn)}</span><span>${e(m.an)}</span></p>
    <div class="mc-bot">${md?`<strong class="num">${p0(m.best)}<small>%</small></strong><span>${m.bi===1?'ничья':e(side(m))}</span>${kv?`<em class="odd">кэф <b class="num">${f2(kv)}</b></em>`:''}`:'<span class="soon">расчёт скоро</span>'}</div>
   </div>
   <div class="face back"><div class="art"><i class="holo"></i><i class="holo2"></i></div><div class="frame"></div>
    <div class="mc-bk"><p class="kick">${e(m.day==='сегодня'?m.lgn:m.day+' · '+m.lgn)}</p>
     ${md?['П1','Х','П2'].map((l,j)=>`<div class="r${pr[j]===mx?' on':''}"><span>${l}</span><i style="--w:${p0(pr[j])}"></i><b class="num">${p0(pr[j])}</b></div>`).join(''):'<p class="soon">Расчёта модели пока нет.</p>'}
     <a class="xgo" href="${href(m)}" tabindex="-1">К матчу <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.6" aria-hidden="true"><path d="M3 10h13M11 4l6 6-6 6"/></svg></a></div>
   </div>
  </div></div></div>`;
 };
 const draw=()=>{
  const list=base.filter(m=>cur==='all'||(cur==='hk')===m.hockey);
  row.innerHTML=list.map(mini).join('')||'<p class="xnone">Матчей нет.</p>';row.scrollLeft=0;
  row.querySelectorAll('.mc').forEach(c=>{tilt(c,8,1.03);wireFlip(c)});
 };
 chips.addEventListener('click',ev=>{
  const b=ev.target.closest('button');if(!b||b.dataset.f===cur)return;
  cur=b.dataset.f;chips.querySelectorAll('button').forEach(x=>{const on=x.dataset.f===cur;x.classList.toggle('on',on);x.setAttribute('aria-pressed',on)});draw();
 });
 /* перетаскивание мышью; на телефоне — обычный свайп */
 let down=false,sx=0,sl=0,moved=0;
 row.addEventListener('pointerdown',ev=>{if(ev.pointerType!=='mouse'||ev.button)return;down=true;sx=ev.clientX;sl=row.scrollLeft;moved=0;row.classList.add('grab')});
 addEventListener('pointermove',ev=>{if(!down)return;const d=ev.clientX-sx;moved=Math.max(moved,Math.abs(d));row.scrollLeft=sl-d});
 addEventListener('pointerup',()=>{
  if(!down)return;down=false;row.classList.remove('grab');
  if(moved>5){row.querySelectorAll('.mc').forEach(c=>{c.dataset.drag='1'});setTimeout(()=>row.querySelectorAll('.mc').forEach(c=>{c.dataset.drag='0'}),60)}
 });
 draw();
})();

/* ── в) Лиги ── */
(()=>{
 const L=[['khl','КХЛ','hockey/league.html?lg=khl','Хоккей'],['nhl','НХЛ','hockey/league.html?lg=nhl','Хоккей'],['epl','АПЛ','football/league.html?lg=epl','Англия'],['laliga','Ла Лига','football/league.html?lg=laliga','Испания'],
  ['seriea','Серия А','football/league.html?lg=seriea','Италия'],['bundesliga','Бундеслига','football/league.html?lg=bundesliga','Германия'],['ligue1','Лига 1','football/league.html?lg=ligue1','Франция'],['ucl','Лига чемпионов','football/ucl.html','Европа']];
 $('#lg-row').innerHTML=L.map(([k,n,u,sb],i)=>{
  const c=all.filter(m=>m.lg===k&&m.day==='сегодня').length;
  return `<li><a class="xtc lc ${k==='khl'||k==='nhl'?'ice':'pitch'}" href="${R}${u}" style="--i:${i}"><div class="shd"></div><div class="tilt"><div class="face front"><div class="art"><i class="holo"></i><i class="holo2"></i></div><div class="frame"></div>
   <span class="lc-sb">${sb}</span><img src="${lgLogo(k)}" alt="" draggable="false"><b>${n}</b><span class="lc-n">${c?`${c} ${H.pl(c,'матч','матча','матчей')} сегодня`:'сегодня матчей нет'}</span></div></div></a></li>`;
 }).join('');
 document.querySelectorAll('.lc').forEach(c=>tilt(c,9,1.03));
 if(DEMO)document.querySelectorAll('.lc').forEach(c=>c.addEventListener('click',ev=>ev.preventDefault()));
})();

/* ── г) призыв ── */
tilt($('#cta'),3,1);

/* ── появление блоков ── */
(()=>{
 const els=[...document.querySelectorAll('.xsec .sh,.dc-stage,.xchips,.md-row,.lg-row,.xcta')];
 els.forEach(el=>el.classList.add('rv'));
 if(RM||!('IntersectionObserver'in window)){els.forEach(el=>el.classList.add('in'));return}
 const io=new IntersectionObserver(es=>es.forEach(x=>{if(x.isIntersecting){x.target.classList.add('in');io.unobserve(x.target)}}),{threshold:.12,rootMargin:'0px 0px -6% 0px'});
 els.forEach(el=>io.observe(el));
})();
})();
