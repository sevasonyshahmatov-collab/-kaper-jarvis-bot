/* JARVIS v3a — поиск по клубам, матчам, лигам и хоккеистам. Подключается из nav.js (одна точка).
   Индекс data/search.json (search/build_index.py) грузится лениво при первом открытии. Открытие: лупа, «/», Ctrl+K. */
(()=>{
const hd=document.getElementById('hd');if(!hd||window.JV_SEARCH)return;window.JV_SEARCH=1;
const SRC=(document.currentScript&&document.currentScript.src)||new URL('assets/search.js',location.href).href;
const U=p=>new URL('../'+p,SRC).href;
const sport=document.documentElement.dataset.sport||'';
// раздел сайта: на хоккейных страницах ищем только хоккей, на футбольных — только футбол, на главной — всё (владелец 04.11)
const ZONE=sport==='hockey'?'h':sport==='football'?'f':'';
const mine=x=>!ZONE||x.s===ZONE;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);

/* ---- нормализация: латиница и кириллица сводятся к одному «скелету» ---- */
const CY={а:'a',б:'b',в:'v',г:'g',д:'d',е:'e',ё:'e',ж:'zh',з:'z',и:'i',й:'i',к:'k',л:'l',м:'m',н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',у:'u',ф:'f',х:'h',ц:'c',ч:'ch',ш:'sh',щ:'sh',ъ:'',ы:'i',ь:'',э:'e',ю:'u',я:'a'};
function fold(s){
  s=String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/ё/g,'е');
  s=s.replace(/[а-я]/g,c=>CY[c]);
  s=s.replace(/ø/g,'o').replace(/ß/g,'ss').replace(/æ/g,'ae').replace(/đ/g,'d').replace(/ł/g,'l');
  s=s.replace(/ck/g,'k').replace(/c(?!h)/g,'k').replace(/q/g,'k').replace(/x/g,'ks').replace(/[yj]/g,'i').replace(/w/g,'v').replace(/(.)\1+/g,'$1');
  return s;
}
const words=s=>fold(s).split(/[^a-z0-9]+/).filter(Boolean);
/* опечатка в 1 букву (замена, вставка, пропуск, перестановка) */
function near(a,b){
  if(a===b)return true;const d=a.length-b.length;if(d>1||d<-1)return false;
  let i=0;while(i<a.length&&i<b.length&&a[i]===b[i])i++;
  if(!d)return a.slice(i+1)===b.slice(i+1)||(a[i]===b[i+1]&&a[i+1]===b[i]&&a.slice(i+2)===b.slice(i+2));
  return d>0?a.slice(i+1)===b.slice(i):b.slice(i+1)===a.slice(i);
}
let NOTYPO=false;
/* насколько слово w подходит слову запроса q: -1 нет, иначе штраф (меньше — лучше) */
function wm(q,w){
  if(w===q)return 0;if(w.startsWith(q))return .2;
  if(q.length>=5&&!NOTYPO){for(let k=-1;k<=1;k++){const l=q.length+k;if(k<0&&q.length<6)continue;if(l>=4&&l<=w.length&&near(q,w.slice(0,l)))return 3}}
  return -1;
}

/* ---- индекс ---- */
let IDX=null,loading=null;
const SP={h:'Хоккей',f:'Футбол'};
const pg=(c)=>c.s==='h'?'team/index.html?id='+encodeURIComponent(c.id):'football/team.html?id='+encodeURIComponent(c.id);
const crest=c=>U((c.s==='h'?'assets/em/s/':'assets/fc/')+c.id+'.webp');
function load(){
  if(IDX)return Promise.resolve(IDX);
  if(loading)return loading;
  loading=fetch(U('data/search.json'),{cache:'default'}).then(r=>{if(!r.ok)throw 0;return r.json()}).then(D=>{
    const W=(ru,en,al)=>{const o=[];for(const x of words(ru))o.push([x,0]);for(const x of words(en))o.push([x,1]);for(const x of words(al))o.push([x,2]);return o};
    const C={};const clubs=D.c.map(r=>{const c={id:r[0],s:r[1],lg:r[2],ru:r[3],en:r[4],w:W(r[3],r[4],r[5])};C[r[1]+r[0]]=c;return c});
    const leagues=D.l.map(r=>({s:r[0],id:r[1],ru:r[2],en:r[3],url:r[5],w:W(r[2],r[3],r[4])}));
    const matches=D.m.map(r=>{const h=C[r[1]+r[2]],a=C[r[1]+r[3]];return h&&a?{d:r[0],s:r[1],h,a,sc:r[4]||'',cup:r[5]||'',w:h.w.concat(a.w)}:null}).filter(Boolean);
    const players=D.p.map((r,i)=>{const c=C['h'+r[2]];/* имена «Имя Фамилия» (НХЛ латиницей, КХЛ по-русски с 13.11) — ищем сначала по фамилии; у КХЛ r[5] — латиница для поиска */return{n:r[0],lg:r[1],c,i,id:r[4],w:W(r[0].split(/\s+/).reverse().join(' '),r[5]||'','')}});
    return IDX={built:D.built,clubs,leagues,matches,players};
  });
  loading.catch(()=>{loading=null});return loading;
}
/* совпадение записи с запросом: штраф или -1 */
function score(ws,qs){
  let t=0;
  for(const q of qs){let b=9;
    for(let i=0;i<ws.length;i++){const m=wm(q,ws[i][0]);if(m<0)continue;
      let v=m+Math.min(i,6)*.15-(ws[i][1]===2&&ws[i][0]===q?1:0)-(ws[i][1]===0?.5:0);if(v<b)b=v}
    if(b===9)return -99;t+=b}
  return t;
}
const NOW=()=>{const d=new Date(Date.now()+(new Date().getTimezoneOffset()+180)*6e4);const p=n=>String(n).padStart(2,'0');return d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+' '+p(d.getHours())+':'+p(d.getMinutes())};
function search(raw){
  NOTYPO=true;const r=search1(raw);if(r&&(r.clubs.length||r.matches.length||r.leagues.length||r.players.length))return r;
  NOTYPO=false;return search1(raw);
}
function search1(raw){
  const qs=words(raw);if(!qs.length||!IDX)return null;
  const pick=(arr,f,lim,cmp)=>{const o=[];for(const x of arr){const s=score(f(x),qs);if(s>-90)o.push([s,x])}o.sort(cmp||((a,b)=>a[0]-b[0]));return o.slice(0,lim).map(a=>a[1])};
  const boost=c=>c.s===sport?-.3:0;
  const clubs=pick(IDX.clubs.filter(mine),c=>c.w,6,(a,b)=>(a[0]+boost(a[1]))-(b[0]+boost(b[1])));
  const now=NOW();
  const ms=pick(IDX.matches.filter(mine),m=>m.w,40,(a,b)=>a[0]-b[0]);
  const up=ms.filter(a=>a.d>=now).sort((a,b)=>a.d<b.d?-1:1),old=ms.filter(a=>a.d<now).sort((a,b)=>a.d<b.d?1:-1);
  const matches=up.concat(old).slice(0,5);
  const leagues=pick(IDX.leagues.filter(mine),l=>l.w,4,(a,b)=>(a[0]+(a[1].s===sport?-.3:0))-(b[0]+(b[1].s===sport?-.3:0)));
  const players=ZONE==='f'?[]:pick(IDX.players,p=>p.w,6,(a,b)=>a[0]-b[0]||a[1].i-b[1].i);
  return{clubs,matches,leagues,players};
}

/* ---- интерфейс ---- */
const LUPA='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/></svg>';
const row=hd.querySelector('.hdrow');if(!row)return;
/* кнопку рисует nav.js сразу (без сдвига шапки); если её нет — создаём */
let sb=row.querySelector('.sbtn');
if(!sb){sb=document.createElement('button');sb.type='button';sb.className='sbtn';sb.setAttribute('aria-label','Поиск по сайту');sb.setAttribute('aria-haspopup','dialog');sb.setAttribute('aria-expanded','false');
sb.innerHTML=LUPA+'<kbd aria-hidden="true">/</kbd>';
const anchor=row.querySelector('.btn-tg')||row.querySelector('.mbtn');row.insertBefore(sb,anchor)}

const box=document.createElement('div');box.className='jsq';box.hidden=true;box.setAttribute('role','dialog');box.setAttribute('aria-modal','true');box.setAttribute('aria-label','Поиск');
box.innerHTML=`<div class="sp-bg" data-x></div><div class="sp-pn"><form class="sp-top" role="search" autocomplete="off">${LUPA}<input id="sp-q" type="search" inputmode="search" enterkeyhint="search" placeholder="${ZONE==='h'?'Хоккей: клуб, матч, лига или игрок':ZONE==='f'?'Футбол: клуб, матч или лига':'Клуб, матч, лига или игрок'}" aria-label="Запрос" aria-controls="sp-res" autocapitalize="off" autocorrect="off" spellcheck="false"><button type="button" class="sp-x" data-x aria-label="Закрыть поиск">Закрыть</button></form><div class="sp-res" id="sp-res" role="listbox" aria-label="Результаты"></div></div>`;
document.body.appendChild(box);
const inp=box.querySelector('#sp-q'),res=box.querySelector('#sp-res');
let items=[],cur=-1,opener=null;

const REC='jv_search_recent';
const recent=()=>{try{const a=JSON.parse(localStorage.getItem(REC)||'[]');return Array.isArray(a)?a.filter(x=>typeof x==='string').slice(0,5):[]}catch(e){return[]}};
const remember=q=>{q=q.trim();if(q.length<2)return;try{const a=[q].concat(recent().filter(x=>x.toLowerCase()!==q.toLowerCase())).slice(0,5);localStorage.setItem(REC,JSON.stringify(a))}catch(e){}};

const dt=d=>{const t=NOW().slice(0,10),y=new Date(Date.now()+(new Date().getTimezoneOffset()+180)*6e4);const dd=d.slice(8,10)+'.'+d.slice(5,7);
  const tm=d.slice(11,16);const diff=Math.round((Date.parse(d.slice(0,10))-Date.parse(t))/864e5);
  return(diff===0?'сегодня':diff===1?'завтра':diff===-1?'вчера':dd)+', '+tm};
const img=c=>`<img src="${esc(crest(c))}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">`;
const tcode=p=>!p.c?'':p.lg==='khl'?p.c.id:p.c.id==='minnesota'?'MIN':p.c.id==='dallas'?'DAL':p.c.id.replace(/^nhl_/,'').toUpperCase();
const LGN={khl:'КХЛ',nhl:'НХЛ',epl:'АПЛ',laliga:'Ла Лига',seriea:'Серия А',bundesliga:'Бундеслига',ligue1:'Лига 1',rpl:'РПЛ',ucl:'ЛЧ',uel:'ЛЕ'};
const li=(href,html,cls)=>`<a class="sp-i ${cls||''}" role="option" id="spo${items.push(href)-1}" href="${esc(href)}" tabindex="-1">${html}</a>`;
function draw(r){
  items=[];cur=-1;
  const g=(t,a,f)=>a.length?`<div class="sp-g" role="group" aria-label="${t}"><h3>${t}</h3>${a.map(f).join('')}</div>`:'';
  const out=g('Клубы',r.clubs,c=>li(U(pg(c)),`${img(c)}<span class="sp-t"><b>${esc(c.ru)}</b><small>${esc(c.en&&c.en!==c.ru?c.en+' · ':'')}${SP[c.s]} · ${esc(LGN[c.lg]||c.lg)}</small></span>`))
   +g('Матчи',r.matches,m=>li(U(pg(m.h)),`<span class="sp-vs">${img(m.h)}${img(m.a)}</span><span class="sp-t"><b>${esc(m.h.ru)} — ${esc(m.a.ru)}</b><small>${esc(dt(m.d))} МСК${m.sc?' · '+esc(m.sc):''}${m.cup?' · '+esc(LGN[m.cup]||m.cup):''} · ${SP[m.s]}</small></span>`))
   +g('Лиги',r.leagues,l=>li(U(l.url),`<span class="sp-lg">${l.s==='h'?'ХК':'ФК'}</span><span class="sp-t"><b>${esc(l.ru)}</b><small>${SP[l.s]} · таблица и матчи</small></span>`))
   +g('Игроки',r.players,p=>li(U(p.id!=null?'hockey/player.html?lg='+p.lg+'&id='+encodeURIComponent(p.id):(p.lg==='nhl'?'hockey/players.html':'hockey/players_khl.html')+'?team='+encodeURIComponent(tcode(p))+'&q='+encodeURIComponent(p.n)),`<span class="sp-lg">${esc(p.n.split(/\s+/).slice(0,2).map(w=>w[0]).join('').toUpperCase())}</span><span class="sp-t"><b>${esc(p.n)}</b><small>${esc(p.c?p.c.ru:'')} · ${p.lg==='nhl'?'НХЛ':'КХЛ'}</small></span>`));
  res.innerHTML=out||`<p class="sp-empty">Ничего не нашли по «${esc(inp.value.trim())}». Попробуйте название клуба или лиги.</p>`;
}
function idle(){
  items=[];cur=-1;const r=recent();
  res.innerHTML=(r.length?`<div class="sp-g"><h3>Недавние запросы</h3>${r.map(x=>`<button type="button" class="sp-i sp-rc" data-q="${esc(x)}"><span class="sp-lg">↺</span><span class="sp-t"><b>${esc(x)}</b></span></button>`).join('')}</div>`:'')
   +`<p class="sp-hint">Например: «Спартак», «arsenal», «Капризов», «НХЛ». Клавиши: ↑ ↓ — выбор, Enter — открыть, Esc — закрыть.</p>`;
}
function run(){
  const v=inp.value;
  if(!words(v).length){idle();return}
  if(!IDX){res.innerHTML='<p class="sp-hint">Загружаем…</p>';load().then(()=>{if(inp.value===v)run()}).catch(()=>{res.innerHTML='<p class="sp-empty">Не удалось загрузить поиск. Обновите страницу.</p>'});return}
  draw(search(v));
}
function mark(i){
  const all=res.querySelectorAll('.sp-i[role=option]');if(!all.length)return;
  cur=(i+all.length)%all.length;all.forEach((a,k)=>a.classList.toggle('on',k===cur));
  inp.setAttribute('aria-activedescendant',all[cur].id);all[cur].scrollIntoView({block:'nearest'});
}
function open(){
  if(!box.hidden)return;opener=document.activeElement;box.hidden=false;sb.setAttribute('aria-expanded','true');
  document.documentElement.classList.add('sp-lock');load().catch(()=>{});run();setTimeout(()=>{inp.focus();inp.select()},0);
}
function close(back){
  if(box.hidden)return;box.hidden=true;sb.setAttribute('aria-expanded','false');document.documentElement.classList.remove('sp-lock');
  try{if(box.contains(document.activeElement))document.activeElement.blur();if(back!==false&&opener&&opener!==document.body&&opener.focus)opener.focus()}catch(e){}
}
sb.addEventListener('click',e=>{e.stopPropagation();box.hidden?open():close()});
box.addEventListener('click',e=>{
  if(e.target.closest('[data-x]')){close();return}
  const rc=e.target.closest('.sp-rc');if(rc){inp.value=rc.dataset.q;run();inp.focus();return}
  const a=e.target.closest('a.sp-i');if(a)remember(inp.value);
});
inp.addEventListener('input',run);
box.querySelector('form').addEventListener('submit',e=>{e.preventDefault();const a=res.querySelectorAll('a.sp-i')[cur<0?0:cur];if(a){remember(inp.value);location.href=a.href}});
addEventListener('keydown',e=>{
  const t=e.target,typing=t&&(t.tagName==='INPUT'||t.tagName==='TEXTAREA'||t.tagName==='SELECT'||t.isContentEditable);
  if((e.key==='k'||e.key==='K'||e.key==='л'||e.key==='Л')&&(e.ctrlKey||e.metaKey)){e.preventDefault();box.hidden?open():close();return}
  if(box.hidden){if(e.key==='/'&&!typing&&!e.ctrlKey&&!e.metaKey&&!e.altKey){e.preventDefault();open()}return}
  if(e.key==='Escape'){e.preventDefault();close()}
  else if(e.key==='ArrowDown'){e.preventDefault();mark(cur+1)}
  else if(e.key==='ArrowUp'){e.preventDefault();mark(cur<0?-1:cur-1)}
  else if(e.key==='Tab'){const f=[...box.querySelectorAll('input,button')].filter(x=>x.offsetParent);if(f.length){const i=f.indexOf(document.activeElement);if(e.shiftKey&&i<=0){e.preventDefault();f[f.length-1].focus()}else if(!e.shiftKey&&i===f.length-1){e.preventDefault();f[0].focus()}}}
});
/* адрес вида ?q=… (SearchAction в разметке главной): открыть поиск с этим запросом */
try{const qq=new URLSearchParams(location.search).get('q');if(qq!==null){inp.value=qq.slice(0,80);open()}}catch(e){}
})();
