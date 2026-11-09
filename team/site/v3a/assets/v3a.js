/* JARVIS v3a — общие части: табло split-flap, бегущая строка, фон-разметка, появление, счётчики, навигация, шторка. */
(()=>{
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const doc=document.documentElement;
doc.classList.add('js');
const JV=window.JV={RM};
JV.esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
JV.f1=(v,d=1)=>v.toFixed(d).replace('.',',');
JV.pc=v=>Math.round(v*100)+'%';
JV.two=n=>String(n).padStart(2,'0');
JV.plural=(n,a,b,c)=>{const k=n%100,j=n%10;return k>10&&k<20?c:j===1?a:j>1&&j<5?b:c};
JV.atMs=t=>Date.parse(t.replace(' ','T')+':00+03:00');
JV.left=t=>{const s=Math.round((JV.atMs(t)-Date.now())/1000);return s};
JV.hms=s=>s>0?`${JV.two(Math.floor(s/3600))}:${JV.two(Math.floor(s%3600/60))}:${JV.two(s%60)}`:(s>-7200?'ИДЁТ':'ФИНАЛ');
/* статус по времени: до 2 ч после старта — «идёт», до суток — «завершён», дальше — дата матча (устаревшие примеры не выдаём за «только что завершён») */
JV.over=s=>{if(s>-7200)return 'идёт';if(s>-86400)return 'завершён';const d=new Date(Date.now()+s*1000+3*3600e3).toISOString();return 'матч '+d.slice(8,10)+'.'+d.slice(5,7)};
JV.inMin=s=>{const m=Math.floor(s/60);return s<=0?JV.over(s):m<60?`через ${m} мин`:m<2880?`через ${Math.floor(m/60)} ч ${m%60} мин`:`через ${Math.floor(m/1440)} дн ${Math.floor(m%1440/60)} ч`};

/* Крупные заголовки: самое длинное слово целиком в колонке — иначе шрифт меньше ровно настолько, чтобы влезло
   («АНАЛИТИЧЕСКАЯ», «БУНДЕСЛИГА», «ЧЕМПИОНОВ»: без разрыва посреди слова, 09.11) */
JV.fitWords=sel=>{
 const one=h=>{const W=h.clientWidth;if(!W)return;h.style.fontSize='';let mx=0;
  const masks=h.querySelectorAll('[class$="-w-mask"]');   /* слово уже разбито анимацией на буквы — меряем сами блоки (они шире текста) */
  if(masks.length){const ws=h.style.whiteSpace;h.style.whiteSpace='nowrap';masks.forEach(m=>{mx=Math.max(mx,m.getBoundingClientRect().width)});h.style.whiteSpace=ws}
  else{const sp=document.createElement('span');sp.style.cssText='position:absolute;visibility:hidden;white-space:nowrap;left:0;top:0';h.appendChild(sp);
   (h.getAttribute('aria-label')||h.textContent).split(/\s+/).filter(Boolean).forEach(w=>{sp.textContent=w;mx=Math.max(mx,sp.getBoundingClientRect().width)});sp.remove();mx*=1.13}   /* запас под разбиение на буквы */
  const fs=parseFloat(getComputedStyle(h).fontSize);if(mx>W)h.style.fontSize=Math.floor(fs*W/mx*0.98)+'px'};
 const run=()=>document.querySelectorAll(sel).forEach(one);run();(JV._fit=JV._fit||[]).push(run);
 if(document.fonts&&document.fonts.ready)document.fonts.ready.then(run);
 let t=0,lw=innerWidth;addEventListener('resize',()=>{if(innerWidth===lw)return;lw=innerWidth;clearTimeout(t);t=setTimeout(run,150)})};   /* только при смене ширины — без качелей из-за полосы прокрутки */
JV.refit=()=>(JV._fit||[]).forEach(f=>f());

/* Название клуба в шапке (владелец 09.11): строка не рвётся внутри слова — шрифт уменьшается до ширины колонки
   (не меньше min); не влезло и так — перенос только между словами. Строки — <span class="l"> (у НХЛ: город / прозвище). */
JV.fitH1=(h,min)=>{if(!h)return;min=min||30;
 const over=()=>h.scrollWidth>h.clientWidth+1,shrink=lo=>{let fs=parseFloat(getComputedStyle(h).fontSize);while(fs>lo&&over()){fs-=1;h.style.fontSize=fs+'px'}};
 const fit=()=>{h.style.fontSize='';h.style.whiteSpace='nowrap';shrink(innerWidth<=620?Math.min(min,26):min);if(!over())return;
  h.style.fontSize='';h.style.whiteSpace='normal';shrink(20)};   /* не влезло в строку — перенос только между словами, каждое слово целиком */
 fit();if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);
 let t=0,lw=innerWidth;addEventListener('resize',()=>{if(innerWidth===lw)return;lw=innerWidth;clearTimeout(t);t=setTimeout(fit,120)})};
/* НХЛ: полное название двумя строками — город и прозвище (владелец 09.11) */
JV.NHL_FULL={nhl_car:'Каролина|Харрикейнз',minnesota:'Миннесота|Уайлд',nhl_edm:'Эдмонтон|Ойлерз',nhl_bos:'Бостон|Брюинз',nhl_mtl:'Монреаль|Канадиенс',
 nhl_tbl:'Тампа-Бэй|Лайтнинг',nhl_njd:'Нью-Джерси|Девилз',nhl_vgk:'Вегас|Голден Найтс',nhl_ott:'Оттава|Сенаторз',dallas:'Даллас|Старз',nhl_col:'Колорадо|Эвеланш',
 nhl_nsh:'Нэшвилл|Предаторз',nhl_nyr:'Нью-Йорк|Рейнджерс',nhl_uta:'Юта|Мамонт',nhl_fla:'Флорида|Пантерз',nhl_buf:'Баффало|Сейбрз',nhl_sea:'Сиэтл|Кракен',
 nhl_ana:'Анахайм|Дакс',nhl_wsh:'Вашингтон|Кэпиталз',nhl_tor:'Торонто|Мейпл Лифс',nhl_nyi:'Нью-Йорк|Айлендерс',nhl_det:'Детройт|Ред Уингз',nhl_stl:'Сент-Луис|Блюз',
 nhl_cgy:'Калгари|Флэймз',nhl_wpg:'Виннипег|Джетс',nhl_sjs:'Сан-Хосе|Шаркс',nhl_cbj:'Коламбус|Блю Джекетс',nhl_pit:'Питтсбург|Пингвинз',nhl_lak:'Лос-Анджелес|Кингз',
 nhl_phi:'Филадельфия|Флайерз',nhl_chi:'Чикаго|Блэкхокс',nhl_van:'Ванкувер|Кэнакс'};

/* страница матча (как seo/build_match.py): <лига>/<дата>-<хозяева>-<гости>/index.html; НХЛ — английские названия городов (09.11) */
{const NHL_EN={"nhl_car":"carolina","nhl_edm":"edmonton","minnesota":"minnesota","nhl_bos":"boston","nhl_vgk":"vegas","nhl_mtl":"montreal","nhl_tbl":"tampa-bay","nhl_njd":"new-jersey","nhl_uta":"utah","dallas":"dallas","nhl_col":"colorado","nhl_ott":"ottawa","nhl_fla":"florida","nhl_tor":"toronto","nhl_sea":"seattle","nhl_buf":"buffalo","nhl_nsh":"nashville","nhl_nyr":"rangers","nhl_det":"detroit","nhl_wsh":"washington","nhl_nyi":"islanders","nhl_stl":"st-louis","nhl_ana":"anaheim","nhl_sjs":"san-jose","nhl_cgy":"calgary","nhl_wpg":"winnipeg","nhl_cbj":"columbus","nhl_pit":"pittsburgh","nhl_phi":"philadelphia","nhl_lak":"los-angeles","nhl_chi":"chicago","nhl_van":"vancouver"};
 JV.mslug=(lg,id)=>lg==='nhl'?(NHL_EN[id]||String(id).replace(/^nhl_/,'').replace(/_/g,'-')):String(id).replace(/_/g,'-');
 JV.matchPage=(root,lg,day,h,a)=>`${root}${lg}/${String(day).slice(0,10)}-${JV.mslug(lg,h)}-${JV.mslug(lg,a)}/index.html`;}
/* «Напомнить о матче»: событие для календаря телефона (.ics, сигнал за 15 мин); t — «ГГГГ-ММ-ДД ЧЧ:ММ» МСК (09.11) */
JV.ics=(title,t,min)=>{const st=new Date(Date.parse(String(t).slice(0,16).replace(' ','T')+':00+03:00'));if(isNaN(st))return '';
 const f=d=>d.toISOString().replace(/[-:]/g,'').slice(0,15)+'Z',en=new Date(st.getTime()+(min||150)*6e4);
 const s=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//JARVIS//match//RU','BEGIN:VEVENT','UID:'+f(st)+'-'+title.length+'@jarvis','DTSTAMP:'+f(st),'DTSTART:'+f(st),'DTEND:'+f(en),
  'SUMMARY:'+title,'DESCRIPTION:Расчёт модели — на сайте JARVIS. Прогнозы дня — в Telegram @jarvibet.','BEGIN:VALARM','TRIGGER:-PT15M','ACTION:DISPLAY','DESCRIPTION:'+title,'END:VALARM','END:VEVENT','END:VCALENDAR'].join('\r\n');
 return 'data:text/calendar;charset=utf-8,'+encodeURIComponent(s)};
JV.BELL='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>';

/* ── split-flap ─────────────────────────────────────────────── */
const CH='АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЭЮЯ0123456789';
const cellHTML=c=>`<span class="t"><i>${c}</i></span><span class="b"><i>${c}</i></span><span class="ft"><i>${c}</i></span><span class="fb"><i>${c}</i></span>`;
function mkCell(){const s=document.createElement('span');s.className='fl';s.innerHTML=cellHTML('&nbsp;');s.dataset.c=' ';return s}
function put(el,c){el.firstChild.textContent=c===' '?' ':c}
function flipOnce(cell,ch,dur){
  const [t,b,ft,fb]=cell.children,old=cell.dataset.c;
  if(old===ch)return Promise.resolve();
  cell.dataset.c=ch;
  if(RM||!cell.animate){put(t,ch);put(b,ch);put(ft,ch);put(fb,ch);return Promise.resolve()}
  put(t,ch);put(ft,old);put(fb,ch);put(b,old);
  const half=dur/2;
  return ft.animate([{transform:'rotateX(0deg)'},{transform:'rotateX(-90deg)'}],{duration:half,easing:'cubic-bezier(.55,0,.9,.4)',fill:'forwards'}).finished
   .then(()=>fb.animate([{transform:'rotateX(90deg)'},{transform:'rotateX(0deg)'}],{duration:half,easing:'cubic-bezier(.2,.7,.3,1)',fill:'forwards'}).finished)
   .then(()=>{put(b,ch);put(ft,ch);ft.getAnimations().forEach(a=>a.cancel());fb.getAnimations().forEach(a=>a.cancel())})
   .catch(()=>{put(b,ch);put(ft,ch)});
}
async function flipTo(cell,ch,delay,spins){
  const tok=cell._tok=(cell._tok||0)+1;
  if(delay)await new Promise(r=>setTimeout(r,delay));
  const seq=[];for(let i=0;i<spins;i++)seq.push(CH[(Math.random()*CH.length)|0]);seq.push(ch);
  for(const c of seq){if(cell._tok!==tok)return;await flipOnce(cell,c,c===ch?150:96)}
  if(cell._tok===tok&&cell.dataset.c!==ch)await flipOnce(cell,ch,150);
}
JV.board=function(root,rows){
  const box=root.querySelector('.brows');box.innerHTML='';
  const R=rows.map(r=>{const row=document.createElement('div');row.className='brow '+(r.cls||'');
    row.innerHTML=`<span>${r.label}</span><div class="cells" aria-hidden="true"></div><span class="sr" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)"></span>`;
    const cells=row.querySelector('.cells');const list=[];for(let i=0;i<(r.n||14);i++){const c=mkCell();cells.appendChild(c);list.push(c)}
    box.appendChild(row);return {row,list,n:r.n||14,sr:row.querySelector('.sr')}});
  return {
    set(texts,{spin=true}={}){texts.forEach((tx,ri)=>{const r=R[ri];if(!r)return;const s=String(tx).toUpperCase().slice(0,r.n).padEnd(r.n,' ');
      r.sr.textContent=tx;[...s].forEach((ch,i)=>{const c=r.list[i];if(c.dataset.c===ch){c._tok=(c._tok||0)+1;return}
        flipTo(c,ch,spin?ri*90+i*26:0,spin&&!RM?1+((Math.random()*4)|0):0)})})},
    tick(ri,tx){const r=R[ri];const s=String(tx).toUpperCase().slice(0,r.n).padEnd(r.n,' ');r.sr.textContent=tx;
      [...s].forEach((ch,i)=>{const c=r.list[i];if(c.dataset.c!==ch||c._busy)flipTo(c,ch,0,0)})}
  };
};

/* ── бегущая строка ─────────────────────────────────────────── */
JV.ticker=function(el,items){
  const ul=`<ul>${items.map(x=>`<li>${x}</li>`).join('')}</ul>`;
  el.innerHTML=`<div class="track">${ul}${ul.replace('<ul>','<ul aria-hidden="true">')}</div>`;
  el.style.setProperty('--dur',Math.max(30,items.length*7)+'s');
};

/* ── фон: разметка поля и льда на canvas ────────────────────── */
JV.field=function(kind){
  const cv=document.createElement('canvas');cv.id='field';cv.setAttribute('aria-hidden','true');document.body.prepend(cv);
  const g=cv.getContext('2d');let W=0,H=0,D=1,raf=0,last=0;
  const size=()=>{D=Math.min(1.5,devicePixelRatio||1);W=innerWidth;H=innerHeight;cv.width=W*D;cv.height=H*D;g.setTransform(D,0,0,D,0,0);draw(performance.now())};
  /* цвета разметки — из CSS-переменных темы (--fld-*), чтобы лёд читался на любом фоне */
  const cs=getComputedStyle(doc),V=(n,d)=>cs.getPropertyValue(n).trim()||d;
  let ink=V('--fld','rgba(16,22,31,.085)'),ink2=V('--fld-2','rgba(16,22,31,.05)'),fPitch=V('--fld-pitch','rgba(22,112,74,.028)'),
    fRed=V('--fld-red','rgba(196,48,59,.16)'),fBlue=V('--fld-blue','rgba(20,98,168,.16)'),fRun=V('--fld-run','rgba(20,98,168,.14)'),fRun2=V('--fld-run2','rgba(16,22,31,.10)');
  function pitch(cx,cy,L,ang){ // L — длина поля в px
    const w=L*.64;g.save();g.translate(cx,cy);g.rotate(ang);g.lineWidth=1.4;g.strokeStyle=ink;
    for(let i=0;i<12;i++){if(i%2)continue;g.fillStyle=fPitch;g.fillRect(-L/2+i*L/12,-w/2,L/12,w)}
    g.strokeRect(-L/2,-w/2,L,w);g.beginPath();g.moveTo(0,-w/2);g.lineTo(0,w/2);g.stroke();
    g.beginPath();g.arc(0,0,L*.087,0,7);g.stroke();
    [-1,1].forEach(s=>{const bx=s*L/2;g.strokeRect(s<0?bx:bx-L*.157,-w*.31,L*.157,w*.62);g.strokeRect(s<0?bx:bx-L*.052,-w*.14,L*.052,w*.28);
      g.beginPath();g.arc(bx-s*L*.105,0,L*.087,s<0?-.93:Math.PI-.93+0,s<0?.93:Math.PI+.93);g.stroke();
      g.beginPath();g.arc(bx-s*L*.105,0,2.4,0,7);g.fillStyle=ink;g.fill()});
    g.restore()}
  function rink(cx,cy,L,ang){
    const w=L*.425,r=w*.28;g.save();g.translate(cx,cy);g.rotate(ang);g.lineWidth=1.4;g.strokeStyle=ink;
    g.beginPath();g.roundRect(-L/2,-w/2,L,w,r);g.stroke();
    g.strokeStyle=fRed;g.lineWidth=3;g.beginPath();g.moveTo(0,-w/2);g.lineTo(0,w/2);g.stroke();
    g.strokeStyle=fBlue;[-1,1].forEach(s=>{g.beginPath();g.moveTo(s*L*.125,-w/2);g.lineTo(s*L*.125,w/2);g.stroke()});
    g.lineWidth=1.3;g.strokeStyle=fRed;[-1,1].forEach(s=>{g.beginPath();g.moveTo(s*L*.445,-w/2+r*.4);g.lineTo(s*L*.445,w/2-r*.4);g.stroke();
      [-1,1].forEach(t=>{g.beginPath();g.arc(s*L*.345,t*w*.26,w*.15,0,7);g.stroke()})});
    g.strokeStyle=fBlue;g.beginPath();g.arc(0,0,w*.15,0,7);g.stroke();
    g.restore()}
  const runs=Array.from({length:4},(_,i)=>({a:Math.random()*6.28,s:.00004+Math.random()*.00005,y:.2+i*.2}));
  const AR=doc.dataset.theme==='arena',DK={ink:'rgba(150,200,255,.13)',ink2:'rgba(150,200,255,.05)',red:'rgba(255,93,108,.34)',blue:'rgba(76,194,255,.34)',run:'rgba(76,194,255,.24)',run2:'rgba(255,194,26,.18)'},
    LT={ink,ink2,red:fRed,blue:fBlue,run:fRun,run2:fRun2};
  function draw(now){
    g.clearRect(0,0,W,H);
    if(AR){const l=JV.lit,P=l<.5?DK:LT;g.globalAlpha=Math.min(1,Math.abs(l-.5)*2+.15);ink=P.ink;ink2=P.ink2;fRed=P.red;fBlue=P.blue;fRun=P.run;fRun2=P.run2}const sy=scrollY*.12,t=now*.00004;
    const L=Math.max(W,H*1.3)*1.25,dx=Math.sin(t)*W*.05,ang=-.08+Math.sin(t*.7)*.025;
    if(kind==='hockey')rink(W*.52+dx,H*.5-sy%(H*1.4)+H*.2,L,ang);
    else if(kind==='mix'){pitch(W*.7+dx,H*.55-sy*.6,L*.9,ang);rink(W*.18-dx,H*.38-sy*.4,L*.62,-ang*1.4)}
    else pitch(W*.52+dx,H*.5-sy%(H*1.4)+H*.2,L,ang);
    // «тактические» пунктиры — медленные дуги розыгрышей
    g.save();g.setLineDash([2,10]);g.lineWidth=1.6;g.lineCap='round';
    runs.forEach((r,i)=>{const p=now*r.s+r.a,x0=W*(.08+.2*i),y0=H*r.y+Math.sin(p)*30;
      g.strokeStyle=i%2?fRun2:fRun;
      g.lineDashOffset=-now*.012;g.beginPath();g.moveTo(x0,y0);g.bezierCurveTo(x0+W*.12,y0-120+Math.cos(p)*60,x0+W*.22,y0+90,x0+W*.32,y0-20+Math.sin(p*1.3)*40);g.stroke()});
    g.restore();
    g.strokeStyle=ink2;g.lineWidth=1;g.beginPath();for(let x=(-sy*.5)%96;x<W;x+=96){g.moveTo(x,0);g.lineTo(x,H)}g.stroke();
  }
  const loop=now=>{raf=requestAnimationFrame(loop);if(now-last<33)return;last=now;draw(now)};
  addEventListener('resize',()=>{clearTimeout(size.t);size.t=setTimeout(size,120)});
  size();
  if(!RM){raf=requestAnimationFrame(loop);document.addEventListener('visibilitychange',()=>{cancelAnimationFrame(raf);if(!document.hidden)raf=requestAnimationFrame(loop)})}
  else addEventListener('scroll',()=>requestAnimationFrame(()=>draw(0)),{passive:true});
};

/* ── появление и счётчики ───────────────────────────────────── */
JV.reveal=function(scope=document){
  const els=scope.querySelectorAll('[data-rv]:not(.in)');
  els.forEach(el=>[...el.children].forEach((c,i)=>c.style.setProperty('--i',i)));
  if(!('IntersectionObserver' in window)){doc.classList.add('no-io');els.forEach(e=>e.classList.add('in'));return}
  const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);count(e.target)}}),{rootMargin:'0px 0px -12% 0px',threshold:.05});
  els.forEach(e=>io.observe(e));
};
function count(scope){scope.querySelectorAll('[data-count]').forEach(el=>{if(el.dataset.done)return;el.dataset.done=1;
  const to=+el.dataset.count,dec=+(el.dataset.dec||0),suf=el.dataset.suf||'';
  const fmt=v=>v.toLocaleString('ru-RU',{minimumFractionDigits:dec,maximumFractionDigits:dec})+suf;
  if(RM){el.textContent=fmt(to);return}
  const t0=performance.now(),D=1400;const st=now=>{const q=Math.min(1,(now-t0)/D),e=1-Math.pow(1-q,4);el.textContent=fmt(to*e);if(q<1)requestAnimationFrame(st)};requestAnimationFrame(st)})}
JV.count=count;

/* ── шапка, навигация по разделам, плашка Telegram ──────────── */
function chrome(){
  const hd=document.getElementById('hd'),bar=document.getElementById('tgbar');
  /* нижняя панель Telegram на телефоне: прячется, пока на экране табло, список матчей или блок подписки */
  const hide=new Set(),watch=['board','matches','subscribe'].map(id=>document.getElementById(id)).filter(Boolean);
  const onS=()=>{const y=scrollY;hd&&hd.classList.toggle('stuck',y>8);bar&&bar.classList.toggle('on',y>innerHeight*.6&&!hide.size&&y<document.body.scrollHeight-innerHeight*1.4)};
  if(bar&&'IntersectionObserver' in window){const bio=new IntersectionObserver(es=>{es.forEach(e=>e.isIntersecting?hide.add(e.target):hide.delete(e.target));onS()});watch.forEach(el=>bio.observe(el))}
  addEventListener('scroll',onS,{passive:true});onS();
  const nav=document.querySelector('.nav');if(!nav||!('IntersectionObserver' in window))return;
  const ind=document.createElement('i');ind.className='bar';nav.appendChild(ind);
  const links=[...nav.querySelectorAll('a[href^="#"]')],map=new Map(links.map(a=>[a.getAttribute('href').slice(1),a]));
  const mark=a=>{links.forEach(l=>l.classList.toggle('on',l===a));if(!a){ind.style.width='0';return}
    ind.style.width=(a.offsetWidth-20)+'px';ind.style.transform=`translateX(${a.offsetLeft+10}px)`};
  const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)mark(map.get(e.target.id))}),{rootMargin:'-45% 0px -50% 0px'});
  map.forEach((a,id)=>{const s=document.getElementById(id);s&&io.observe(s)});
}

/* ── шторка при переходе между страницами ───────────────────── */
function wipe(){
  if(RM)return;
  const w=document.createElement('div');w.className='wipe';w.setAttribute('aria-hidden','true');w.innerHTML=Array.from({length:6},(_,i)=>`<i style="--i:${i}"></i>`).join('');document.body.appendChild(w);
  let came=false;try{came=sessionStorage.getItem('jv-wipe')==='1';sessionStorage.removeItem('jv-wipe')}catch(e){}
  if(came){w.querySelectorAll('i').forEach(i=>i.style.transform='scaleY(1)');requestAnimationFrame(()=>requestAnimationFrame(()=>{w.querySelectorAll('i').forEach(i=>i.style.transform='');w.classList.add('reveal')}))}
  addEventListener('pageshow',e=>{if(e.persisted){w.classList.remove('cover');w.classList.add('reveal')}});
  document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a||a.target||e.metaKey||e.ctrlKey||e.shiftKey)return;
    const h=a.getAttribute('href');if(!/index\.html(\?[^#]*)?(#.*)?$/.test(h)||h.startsWith('#'))return;
    e.preventDefault();try{sessionStorage.setItem('jv-wipe','1')}catch(err){}
    w.classList.remove('reveal');w.classList.add('cover');setTimeout(()=>location.href=a.href,560)});
}

/* ── тема «arena»: тёмная арена на первом экране, при прокрутке «включают свет» ──
   Цвет фона (--bgc) идёт по зонам data-zone: арена → полусвет (лёд) → газета → тёплая бумага.
   --lit 0…1 — насколько включён свет (гаснут прожекторы, герой уходит, разметка льда меняет цвет). */
JV.lit=1;
function arena(){
  if(doc.dataset.theme!=='arena'){JV.lit=1;return}
  const hero=document.querySelector('.hero'),hd=document.getElementById('hd');if(!hero)return;
  const Z={arena:[7,18,37],p1:[214,226,238],p2:[236,238,232],p2b:[221,232,242],p3:[239,233,219]};
  if(doc.dataset.col==='1'){Z.p1=Z.p2b=Z.p3=Z.p2}   /* вариант 1: после первого экрана один светлый фон */
  const zones=()=>[{el:hero,c:Z.arena},...[...document.querySelectorAll('[data-zone]')].map(el=>({el,c:Z[el.dataset.zone]||Z.p2}))];
  let zs=zones(),tops=[];
  const measure=()=>{zs=zones();tops=zs.map((z,i)=>i?z.el.getBoundingClientRect().top+scrollY:0)};
  const mix=(a,b,t)=>a.map((v,i)=>Math.round(v+(b[i]-v)*t));
  let lastLit=-1,lastC='';
  const upd=()=>{
    const vh=innerHeight,c=scrollY+vh*.5;let i=0;while(i<tops.length-1&&tops[i+1]<=c)i++;
    let col=zs[i].c,lit;
    const dn=i<tops.length-1?tops[i+1]-c:1e9,up=i>0?c-tops[i]:1e9,k=innerWidth<=620?.4:1,Wn=(i===0?vh*.36:vh*.3)*k,Wu=(i===1?vh*.36:vh*.3)*k;  /* телефон: переход короче, без блёклого экрана (аудит 08.11 п.8) */
    if(up<Wu)col=mix(zs[i-1].c,zs[i].c,.5+up/Wu*.5);else if(dn<Wn)col=mix(zs[i].c,zs[i+1].c,.5-dn/Wn*.5);
    if(i===0)lit=dn<Wn?.5-dn/Wn*.5:0;else if(i===1&&up<Wu)lit=.5+up/Wu*.5;else lit=1;
    if(RM)lit=lit<.5?0:1,col=lit?col:Z.arena;
    lit=Math.round(lit*100)/100;JV.lit=lit;
    const cs=`rgb(${col.join(',')})`;if(cs!==lastC){doc.style.setProperty('--bgc',cs);lastC=cs}
    if(lit!==lastLit){doc.style.setProperty('--lit',lit);doc.classList.toggle('lit',lit>=.5);lastLit=lit}
  };
  measure();upd();
  addEventListener('scroll',()=>requestAnimationFrame(upd),{passive:true});
  addEventListener('resize',()=>{measure();upd()});addEventListener('load',()=>{measure();upd()});
  if('ResizeObserver' in window)new ResizeObserver(()=>{measure();upd()}).observe(document.body);
}

/* ── тема из адреса (?theme=a|b|c) — переносим на ссылки между страницами макета ── */
function keepTheme(){
  const t=new URLSearchParams(location.search).get('theme');if(!/^(arena|a|b|c)$/.test(t||''))return;
  document.querySelectorAll('a[href*="index.html"]').forEach(a=>{const h=a.getAttribute('href');if(/^https?:/.test(h))return;
    const [p,hash]=h.split('#'),[path,q]=p.split('?'),sp=new URLSearchParams(q||'');sp.set('theme',t);a.setAttribute('href',path+'?'+sp.toString()+(hash?'#'+hash:''))});
}

document.addEventListener('DOMContentLoaded',()=>{keepTheme();JV.fitWords('.hero h1,.sec-head h2,.lgtab .lgn,.dk-h1');arena();chrome();wipe();
  requestAnimationFrame(()=>document.querySelector('.hero,.mast')?.classList.add('ready'));
  JV.reveal();
  const k=document.body.dataset.field;if(k&&!document.documentElement.dataset.hbg)JV.field(k);
});
})();

/* (08.11) старая подгонка заголовков заменена на JV.fitWords / JV.fitH1 (09.11): две подгонки перебивали друг друга */
