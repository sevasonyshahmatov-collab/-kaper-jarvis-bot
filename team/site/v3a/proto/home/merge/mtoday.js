/* «Ближайшие матчи» — три вида на выбор владельца: ?m=1 «Лицом к лицу», ?m=2 «Билеты», ?m=3 «Табло по времени».
   Данные — window.HOME (proto/home/common.js): тот же список, что на главной. Подписей минимум, без эффектов при наведении. */
(()=>{
'use strict';
const H=window.HOME,box=document.getElementById('mt');
if(!box)return;
const q=new URLSearchParams(location.search),V=['1','2','3'].includes(q.get('m'))?+q.get('m'):1;
document.documentElement.dataset.m=V;
document.querySelectorAll('.mt-sw a').forEach(a=>{if(+a.dataset.m===V)a.setAttribute('aria-current','true')});
if(!H||!H.J){box.innerHTML='<p class="mt-none">Матчи появятся после обновления данных.</p>';return}
const e=H.esc,f2=H.f2,pc=v=>H.pct(v);
const upd=document.getElementById('mt-upd');if(upd)upd.textContent=H.upd();

/* 8 ближайших: по 4 хоккея и футбола, по времени */
const all=H.all(),now=Date.now();
const by=(a,b)=>a.t<b.t?-1:a.t>b.t?1:0;
let L=all.filter(m=>m.hockey).slice(0,4).concat(all.filter(m=>!m.hockey).slice(0,4));
if(L.length<8){const s=new Set(L.map(m=>m.key));L=L.concat(all.filter(m=>!s.has(m.key)).slice(0,8-L.length))}
L.sort(by);
if(!L.length){box.innerHTML='<p class="mt-none">Сегодня матчей нет.</p>';return}

const crest=(src,cls)=>`<img class="${cls}" src="${src}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">`;
const kef=(m,i)=>{const ln=m.ln;if(!ln)return '';const v=[ln.p1,ln.x,ln.p2][i];return v?f2(v):''};
const OUT=['П1','Х','П2'];
const pick=m=>m.pr?{o:OUT[m.bi],p:pc(m.best),k:kef(m,m.bi),who:m.bi===1?'ничья':m.bi===0?m.hn:m.an}:null;
const when=m=>m.day==='сегодня'?m.hm:`${m.hm}<small>${e(m.day)}</small>`;

/* 1 — лицом к лицу: эмблемы крупно, полоса шансов модели П1 / Х / П2, кэф под своим исходом.
   Наведение (владелец 08.11): матч расширяется в своём ряду, соседи сужаются; справа — подробности. Касание на телефоне — раскрыть, второе — перейти. */
const f1=v=>(Math.round(v*100)/100).toFixed(2).replace(/0$/,'').replace('.',',');
function left(m){const ms=Date.parse(m.t.replace(' ','T')+':00+03:00')-now;if(ms<=0)return ms>-(m.hockey?3:2.2)*36e5?'идёт сейчас':'сыгран';
 const h=Math.floor(ms/36e5),mi=Math.floor(ms%36e5/6e4);return h>=24?`через ${Math.floor(h/24)} ${H.pl(Math.floor(h/24),'день','дня','дней')}`:h?`через ${h} ч ${mi} мин`:`через ${mi} мин`}
function more(m){
 const md=m.md,ln=m.ln,rows=[];
 if(md&&md.lam)rows.push([m.hockey?'Ожидаемые шайбы':'Ожидаемые голы',`${f1(md.lam[0])} : ${f1(md.lam[1])}`]);
 if(md&&md.tot!=null&&md.over!=null){const k=ln&&ln.tot===md.tot&&ln.over?` · ${f2(ln.over)}`:'';rows.push([`Тотал больше ${String(md.tot).replace('.',',')}`,`${pc(md.over)}%${k}`])}
 if(md&&md.btts!=null)rows.push(['Обе забьют',`${pc(md.btts)}%`]);
 if(md&&md.w1!=null)rows.push(['Победа с ОТ и буллитами',`${pc(md.w1)}% / ${pc(md.w2)}%`]);
 const ar=m.arena?(typeof m.arena==='string'?m.arena:[m.arena.name,m.arena.city].filter(Boolean).join(', ')):'';
 return `<div class="more"><dl>${rows.map(r=>`<div><dt>${e(r[0])}</dt><dd>${r[1]}</dd></div>`).join('')}</dl>
  <p class="meta">${e(left(m))}${ar?' · '+e(ar):''}</p><span class="go">Разбор матча →</span></div>`;
}
/* живой счёт (assets/live.js): атрибуты как в seo/build_seo.py lv_attrs */
const lv=m=>`data-lv data-lv-lg="${e(m.lg)}" data-lv-t="${e(m.t.replace(' ','T'))}:00+03:00" data-lv-h="${e(m.h)}" data-lv-a="${e(m.a)}" data-lv-hn="${e(m.hn)}" data-lv-an="${e(m.an)}"`;
function card1(m){
 const pr=m.pr;
 const bar=pr?`<div class="bar">${pr.map((p,i)=>p==null?'':`<i class="${i===m.bi?'on':''}" style="flex:${Math.max(p,.06)}"><b>${pc(p)}%</b><small>${OUT[i]}${kef(m,i)?' · '+kef(m,i):''}</small></i>`).join('')}</div>`:'<div class="bar none">расчёт скоро</div>';
 return `<li class="${m.hockey?'hk':'fb'}"><a href="${m.page}" data-fb="${m.href}"><div class="main">
   <div class="fo">
    <span class="tm">${crest(m.hc,'cr')}<b>${e(m.hn)}</b></span>
    <span class="mid" ${lv(m)}><time>${when(m)}</time><em>${e(m.lgn)}</em></span>
    <span class="tm aw">${crest(m.ac,'cr')}<b>${e(m.an)}</b></span>
   </div>${bar}</div>${more(m)}</a></li>`;
}
function v1(){
 const n=innerWidth>=981?3:innerWidth>=640?2:1,rows=[];
 for(let i=0;i<L.length;i+=n)rows.push(L.slice(i,i+n));
 return `<div class="mt1" data-n="${n}">${rows.map(r=>`<ul class="row">${r.map(card1).join('')}</ul>`).join('')}</div>`;
}
function wire1(){
 const root=box.querySelector('.mt1');if(!root)return;
 /* высота карточки = высоте с раскрытыми подробностями: ряд не прыгает при наведении */
 if(root.dataset.n!=='1'){let mh=0;root.querySelectorAll('li').forEach(li=>{li.classList.add('on','probe');mh=Math.max(mh,li.querySelector('a').getBoundingClientRect().height);li.classList.remove('on','probe')});root.style.setProperty('--mh',Math.ceil(mh)+'px')}
 const set=li=>{root.querySelectorAll('li.on').forEach(x=>{if(x!==li)x.classList.remove('on')});root.querySelectorAll('.row').forEach(r=>r.classList.toggle('act',!!li&&r.contains(li)));if(li)li.classList.add('on')};
 root.querySelectorAll('li').forEach(li=>{
  li.addEventListener('pointerenter',ev=>{if(ev.pointerType==='mouse')set(li)});
  li.addEventListener('pointerleave',ev=>{if(ev.pointerType==='mouse')set(null)});
  li.addEventListener('focusin',()=>{if(li.querySelector('a:focus-visible'))set(li)});
  li.addEventListener('pointerdown',ev=>{li.dataset.pt=ev.pointerType});
  li.querySelector('a').addEventListener('click',ev=>{if((ev.pointerType||li.dataset.pt)&&(ev.pointerType||li.dataset.pt)!=='mouse'&&!li.classList.contains('on')){ev.preventDefault();ev.stopPropagation();set(li)}});
 });
 root.addEventListener('focusout',ev=>{if(!root.contains(ev.relatedTarget))set(null)});
}

/* 2 — билеты: корешок со временем, команды, справа исход модели крупно */
function v2(){
 return `<ul class="mt2">${L.map(m=>{const p=pick(m);
  return `<li class="${m.hockey?'hk':'fb'}"><a href="${m.href}">
   <div class="stub"><time>${when(m)}</time><em>${e(m.lgn)}</em></div>
   <div class="body">
    <span class="tm">${crest(m.hc,'cr')}<b>${e(m.hn)}</b></span>
    <span class="tm">${crest(m.ac,'cr')}<b>${e(m.an)}</b></span>
   </div>
   <div class="pk">${p?`<b>${p.p}<small>%</small></b><span>${p.o} · ${e(p.who)}</span>${p.k?`<em>${p.k}</em>`:''}`:'<span>расчёт скоро</span>'}</div>
  </a></li>`}).join('')}</ul>`;
}

/* 3 — табло по времени: слева час, справа матчи этого часа плитками */
function v3(){
 const g=[];L.forEach(m=>{const k=m.day+' '+m.hm;let x=g.find(y=>y.k===k);if(!x)g.push(x={k,m,list:[]});x.list.push(m)});
 return `<ol class="mt3">${g.map(x=>`<li><time>${x.m.hm}${x.m.day!=='сегодня'?`<small>${e(x.m.day)}</small>`:''}</time><div class="slot">${x.list.map(m=>{const p=pick(m);
  return `<a class="ch ${m.hockey?'hk':'fb'}" href="${m.href}">
   <span class="crs">${crest(m.hc,'cr')}${crest(m.ac,'cr')}</span>
   <span class="nm"><b>${e(m.hn)}</b><b>${e(m.an)}</b></span>
   ${p?`<span class="pk"><b>${p.p}%</b><small>${p.o}${p.k?' · '+p.k:''}</small></span>`:''}
  </a>`}).join('')}</div></li>`).join('')}</ol>`;
}
box.innerHTML=[v1,v2,v3][V-1]();
/* страница матча есть не у всех (окно сборки): нет — ведём в раздел */
const seen={};function fixLinks(){box.querySelectorAll('a[data-fb]').forEach(a=>{const u=a.getAttribute('href');
 (seen[u]||(seen[u]=fetch(u,{method:'HEAD'}).then(r=>r.ok).catch(()=>false))).then(ok=>{if(!ok)a.setAttribute('href',a.dataset.fb)})})}
fixLinks();
document.dispatchEvent(new Event('jv:rows'));
if(V===1){wire1();let n0=box.querySelector('.mt1').dataset.n;
 addEventListener('resize',()=>{const n=innerWidth>=981?3:innerWidth>=640?2:1;if(String(n)!==n0){n0=String(n);box.innerHTML=v1();wire1();fixLinks();document.dispatchEvent(new Event('jv:rows'))}})}
})();
