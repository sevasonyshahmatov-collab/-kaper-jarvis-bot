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
JV.inMin=s=>{const m=Math.floor(s/60);return s<=0?(s>-7200?'идёт':'завершён'):m<60?`через ${m} мин`:`через ${Math.floor(m/60)} ч ${m%60} мин`};

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
  const ink=V('--fld','rgba(16,22,31,.085)'),ink2=V('--fld-2','rgba(16,22,31,.05)'),fPitch=V('--fld-pitch','rgba(22,112,74,.028)'),
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
  function draw(now){
    g.clearRect(0,0,W,H);const sy=scrollY*.12,t=now*.00004;
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
  const onS=()=>{const y=scrollY;hd&&hd.classList.toggle('stuck',y>8);bar&&bar.classList.toggle('on',y>innerHeight*.8&&y<document.body.scrollHeight-innerHeight*1.6)};
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

/* ── тема из адреса (?theme=a|b|c) — переносим на ссылки между страницами макета ── */
function keepTheme(){
  const t=new URLSearchParams(location.search).get('theme');if(!/^[abc]$/.test(t||''))return;
  document.querySelectorAll('a[href*="index.html"]').forEach(a=>{const h=a.getAttribute('href');if(/^https?:/.test(h))return;
    const [p,hash]=h.split('#');a.setAttribute('href',p.split('?')[0]+'?theme='+t+(hash?'#'+hash:''))});
}

document.addEventListener('DOMContentLoaded',()=>{keepTheme();chrome();wipe();
  requestAnimationFrame(()=>document.querySelector('.hero,.mast')?.classList.add('ready'));
  JV.reveal();
  const k=document.body.dataset.field;if(k)JV.field(k);
});
})();
