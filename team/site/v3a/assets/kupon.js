/* JARVIS v3a — «Купон» (hockey/kupon.html): конструктор ставок по вероятностям модели.
   Данные: JV_TODAY (матчи), JV_MODEL (lam — ожидаемые голы, p1/x/p2, w1/w2), JV_LINES (линия: П1/Х/П2, победа с ОТ, тотал).
   Все рынки считаются по одной сетке счётов матча, поэтому комбинации внутри матча учитывают связь событий. */
(function(){
'use strict';
const T=window.JV_TODAY||{matches:[]},MODEL=window.JV_MODEL||{},LINES=window.JV_LINES||{};
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const LS_CUR='jv_kupon',LS_SAVED='jv_kupons';
const LG={khl:'КХЛ',nhl:'НХЛ'};
const MON=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];

/* ---------- числа ---------- */
const fk=x=>x>=100?String(Math.round(x)):x.toFixed(2).replace('.',',');           /* кэф */
const fl=x=>String(x).replace('.',',').replace('-','−');                             /* линия */
const fs=x=>(x>0?'+':'')+fl(x);
const fp=p=>p<=0?'0 %':p<.01?'меньше 1 %':p>.99&&p<1?'больше 99 %':Math.round(p*100)+' %';
const fm=x=>Math.round(x).toLocaleString('ru-RU');
const LEG=/^[a-z]+(:[\w.+-]+)+$/,ODD=s=>/^\d{1,3}([.,]\d{1,2})?$/.test(String(s))&&num(s)>1&&num(s)<=50;   /* событие и кэф из ссылки или памяти — только такого вида */
const num=s=>{const v=parseFloat(String(s).replace(',','.'));return isFinite(v)?v:NaN};
function oneIn(p){if(p<=0)return '';if(p>=.9)return 'по модели примерно '+Math.min(99,Math.round(p*100))+' раз из 100';const n=1/p;
  if(n<1.8){const k=Math.round(p*10);return 'примерно '+k+' раз'+(k>1&&k<5?'а':'')+' из 10'}
  return 'примерно 1 раз из '+Math.round(n)}

/* ---------- время матча (в данных — московское) ---------- */
const tms=m=>Date.parse(m.t.replace(' ','T')+':00+03:00');
const started=m=>tms(m)<=Date.now();
const mskDay=ms=>new Date(ms+3*36e5).toISOString().slice(0,10);
function dayName(d){const now=mskDay(Date.now()),tom=mskDay(Date.now()+864e5);
  const s=+d.slice(8)+' '+MON[+d.slice(5,7)-1];return d===now?'Сегодня, '+s:d===tom?'Завтра, '+s:s}
const hm=m=>esc(String(m.t).slice(11));
const dm=m=>m.t.slice(8,10)+'.'+m.t.slice(5,7);

/* ---------- сетка счётов матча ---------- */
const GRID={};
function pois(l,n){const a=[Math.exp(-l)];for(let i=1;i<n;i++)a[i]=a[i-1]*l/i;return a}
function grid(key){
  if(key in GRID)return GRID[key];
  const m=MODEL[key];if(!m||!m.lam||!(m.lam[0]>0)||!(m.lam[1]>0))return GRID[key]=null;
  const N=15,ph=pois(m.lam[0],N),pa=pois(m.lam[1],N),sum=[0,0,0],cells=[];
  for(let h=0;h<N;h++)for(let a=0;a<N;a++){const r=h>a?0:h===a?1:2,p=ph[h]*pa[a];sum[r]+=p;cells.push([h,a,r,p])}
  /* исходы основного времени приводим к цифрам модели (ничьих в хоккее больше, чем даёт простая сетка) */
  const tg=[m.p1,m.x,m.p2],ok=tg.every(v=>typeof v==='number'&&v>0)&&Math.abs(tg[0]+tg[1]+tg[2]-1)<.02;
  const all=sum[0]+sum[1]+sum[2],f=ok?tg.map((v,i)=>v/sum[i]):[1/all,1/all,1/all];
  /* доля побед хозяев в овертайме и по буллитам — из «итоговой победы» модели */
  let q=.5;if(ok&&typeof m.w1==='number')q=Math.min(.75,Math.max(.25,(m.w1-m.p1)/m.x));
  const st=[];
  for(const [h,a,r,p0] of cells){const p=p0*f[r];if(p<1e-12)continue;
    if(r===1){st.push({h,a,w:1,ot:1,p:p*q});st.push({h,a,w:2,ot:1,p:p*(1-q)})}
    else st.push({h,a,w:r===0?1:2,ot:0,p})}
  return GRID[key]=st;
}

/* ---------- события ---------- */
function pred(id){const a=id.split(':');
  switch(a[0]){
    case 'r':return a[1]==='x'?s=>!!s.ot:a[1]==='1'?s=>!s.ot&&s.w===1:s=>!s.ot&&s.w===2;
    case 'w':return a[1]==='1'?s=>s.w===1:s=>s.w===2;
    case 'dc':return a[1]==='1x'?s=>s.ot||s.w===1:a[1]==='x2'?s=>s.ot||s.w===2:s=>!s.ot;
    case 't':{const l=+a[2];return a[1]==='o'?s=>s.h+s.a>l:s=>s.h+s.a<l}
    case 'f':{const l=+a[2];return a[1]==='1'?s=>s.h+l>s.a:s=>s.a+l>s.h}
    case 'it':{const l=+a[3],g=a[1]==='1'?s=>s.h:s=>s.a;return a[2]==='o'?s=>g(s)>l:s=>g(s)<l}
    case 'b':return a[1]==='y'?s=>s.h>0&&s.a>0:s=>!(s.h>0&&s.a>0);
    case 'ot':return a[1]==='y'?s=>!!s.ot:s=>!s.ot;
    case 'eo':return a[1]==='e'?s=>(s.h+s.a)%2===0:s=>(s.h+s.a)%2===1;
  }
  return ()=>false;
}
/* события одной группы исключают друг друга: новое заменяет прежнее */
function group(id){const a=id.split(':');
  switch(a[0]){case 't':return 't:'+a[2];case 'f':return 'f:'+(a[1]==='1'?+a[2]:-a[2]);case 'it':return 'it:'+a[1]+':'+a[3];default:return a[0]}}
function prob(key,ids){const g=grid(key);if(!g)return 0;const ps=ids.map(pred);let s=0;
  for(const st of g){let ok=true;for(const f of ps)if(!f(st)){ok=false;break}if(ok)s+=st.p}return s}
/* короткая подпись на кнопке и полная — в купоне */
function short(id){const a=id.split(':');
  switch(a[0]){
    case 'r':return a[1]==='x'?'Х':'П'+a[1];
    case 'w':return 'П'+a[1];
    case 'dc':return a[1].toUpperCase().replace('X','Х');
    case 't':return (a[1]==='o'?'Б ':'М ')+fl(a[2]);
    case 'f':return 'Ф'+a[1]+' ('+fs(+a[2])+')';
    case 'it':return (a[2]==='o'?'Б ':'М ')+fl(a[3]);
    case 'b':case 'ot':return a[1]==='y'?'Да':'Нет';
    case 'eo':return a[1]==='e'?'Чёт':'Нечет';
  }return id}
function full(id,m){const a=id.split(':'),tn=a[1]==='1'?m.hn:m.an;
  switch(a[0]){
    case 'r':return a[1]==='x'?'Ничья в основное время':'П'+a[1]+' · '+tn+', основное время';
    case 'w':return 'Победа в матче: '+tn+' (с ОТ и буллитами)';
    case 'dc':return a[1]==='1x'?'1Х · '+m.hn+' не проиграет':a[1]==='x2'?'Х2 · '+m.an+' не проиграет':'12 · ничьей в основное время не будет';
    case 't':return 'Тотал '+(a[1]==='o'?'больше ':'меньше ')+fl(a[2]);
    case 'f':return 'Фора '+tn+' ('+fs(+a[2])+')';
    case 'it':return 'Инд. тотал '+(a[1]==='1'?m.hn:m.an)+' '+(a[2]==='o'?'больше ':'меньше ')+fl(a[3]);
    case 'b':return 'Обе забьют: '+(a[1]==='y'?'да':'нет');
    case 'ot':return 'Овертайм: '+(a[1]==='y'?'будет':'не будет');
    case 'eo':return 'Тотал '+(a[1]==='e'?'чётный':'нечётный');
  }return id}
/* кэф линии, если он есть в данных */
function lineOdd(key,id){const L=LINES[key];if(!L)return null;const a=id.split(':');let v=null;
  if(a[0]==='r')v=a[1]==='1'?L.p1:a[1]==='x'?L.x:L.p2;
  else if(a[0]==='w')v=a[1]==='1'?L.fin1:L.fin2;
  else if(a[0]==='t'&&L.tot!=null&&+a[2]===+L.tot&&L.tot%1!==0)v=a[1]==='o'?L.over:L.under;
  return typeof v==='number'&&v>1?v:null}

/* ---------- фон карточки: цвета клубов, как у карточек «Выбрать матч» (assets/deck.js pickPair) ---------- */
const hex2rgb=h=>{h=String(h).replace('#','');if(h.length===3)h=h.replace(/./g,'$&$&');const n=parseInt(h,16);return isNaN(n)||h.length!==6?null:[n>>16&255,n>>8&255,n&255]};
function rgb2hsl(r,g,b){r/=255;g/=255;b/=255;const mx=Math.max(r,g,b),mn=Math.min(r,g,b),l=(mx+mn)/2;let h=0,s=0;
  if(mx!==mn){const d=mx-mn;s=l>.5?d/(2-mx-mn):d/(mx+mn);h=mx===r?(g-b)/d+(g<b?6:0):mx===g?(b-r)/d+2:(r-g)/d+4;h*=60}return [h,s,l]}
/* цвета отдаём готовыми rgb(), середину перелива считаем здесь: без color-mix() и новой записи hsl() — их нет в старых браузерах телефонов */
function hsl2rgb(h,s,l){h=(((h%360)+360)%360)/360;const q=l<.5?l*(1+s):l+s-l*s,p=2*l-q,f=t=>{t=(t+1)%1;return t<1/6?p+(q-p)*6*t:t<.5?q:t<2/3?p+(q-p)*(2/3-t)*6:p};
  return [f(h+1/3),f(h),f(h-1/3)].map(v=>Math.round(v*255))}
const rgb=c=>'rgb('+c.join(',')+')';
const hueD=(a,b)=>{const d=Math.abs(a-b)%360;return d>180?360-d:d};
const cands=id=>((window.JV_CLUBS||{})[id]||[]).map(hex2rgb).filter(Boolean).map(c=>rgb2hsl(c[0],c[1],c[2]));
const cnorm=([h,s,l])=>[h,Math.min(.85,Math.max(.55,s)),Math.min(.40,Math.max(.30,l))];
const cscore=([h,s,l])=>s>=.25&&l>.1&&l<.93?s*(1-Math.abs(l-.42)):-1;
const COLS={};
function cols(m){if(COLS[m.key])return COLS[m.key];
  const A=cands(m.h).sort((x,y)=>cscore(y)-cscore(x)),B=cands(m.a).sort((x,y)=>cscore(y)-cscore(x));
  let a=A[0]&&cscore(A[0])>0?A[0]:[218,.3,.34],b=B[0]&&cscore(B[0])>0?B[0]:[222,.3,.26];
  if(hueD(a[0],b[0])<32&&Math.abs(a[2]-b[2])<.2){const alt=B.find(c=>cscore(c)>0&&hueD(a[0],c[0])>=40);b=alt||[b[0]+34,b[1],b[2]+.1]}
  a=cnorm(a);b=cnorm(b);
  if(Math.abs(a[2]-b[2])<.05&&hueD(a[0],b[0])<50){a[2]=Math.max(.28,a[2]-.04);b[2]=Math.min(.42,b[2]+.05)}
  const A1=hsl2rgb(a[0],a[1],a[2]),B1=hsl2rgb(b[0],b[1],b[2]);
  return COLS[m.key]=[rgb(A1),rgb(B1),rgb(A1.map((v,i)=>Math.round((v+B1[i])/2)))]}

/* ---------- рынки матча ---------- */
/* Правило владельца 14.11: в НХЛ минимальный тотал матча, который дают взять, — 4,5 (больше или меньше); 3,5 не бывает. В КХЛ линия идёт с 3,5. */
const totalLines=m=>m.lg==='nhl'?[4.5,5.5,6.5,7.5]:[3.5,4.5,5.5,6.5,7.5];
function markets(m){
  const L=LINES[m.key]||{},base=L.tot!=null&&L.tot%1!==0?+L.tot:5.5,tl=totalLines(m);
  const tot=l=>['t:o:'+l,'t:u:'+l];
  return {
    main:[{n:'Основное время',o:['r:1','r:x','r:2']},{n:'Победа с ОТ и буллитами',o:['w:1','w:2']},{n:'Тотал голов',o:tot(base)}],
    more:[
      {n:'Двойной шанс',o:['dc:1x','dc:12','dc:x2']},
      {n:'Тотал голов, другие линии',o:tl.filter(l=>l!==base).flatMap(tot),c:2},
      {n:'Фора: '+m.hn,o:['f:1:-2.5','f:1:-1.5','f:1:1.5','f:1:2.5'],c:2},
      {n:'Фора: '+m.an,o:['f:2:-2.5','f:2:-1.5','f:2:1.5','f:2:2.5'],c:2},
      {n:'Голы: '+m.hn,o:[1.5,2.5,3.5,4.5].flatMap(l=>['it:1:o:'+l,'it:1:u:'+l]),c:2},
      {n:'Голы: '+m.an,o:[1.5,2.5,3.5,4.5].flatMap(l=>['it:2:o:'+l,'it:2:u:'+l]),c:2},
      {n:'Обе забьют',o:['b:y','b:n'],c:2},
      {n:'Овертайм',o:['ot:y','ot:n'],c:2},
      {n:'Чёт / нечет',o:['eo:e','eo:o'],c:2}
    ]};
}

/* ---------- состояние ---------- */
/* купон хоккейный: футбольные матчи окна (они тоже в today.js) сюда не берём — иначе «undefined» вместо лиги и пустые эмблемы (19.11) */
const HM=(T.matches||[]).filter(m=>m&&LG[m.lg]);
const BY={};HM.forEach(m=>BY[m.key]=m);
const S={legs:[],odds:{},stake:'1000',mode:'x',lg:'',day:'',open:{},sheet:false,look:8,ad:'',an:0};   /* ad — день для автоподбора ('' — все), an — сколько событий (0 — сам) */
/* варианты оформления списка матчей (выбор владельца): 0 — подробные плашки, 1 — строки, 2 — плитки, 3 — спокойный */
const LOOKS=['Подробный','Строки','Плитки','Спокойный','Цвет слева','Приглушённый','Цвет при выборе','По группам','Группы + цвет при выборе'];
const EMBS=['Внахлёст','Лицом к лицу','С наклоном','Крупно, с обрезкой','Фоном','В кругах','Столкновение','По краям строки','Ступенькой','В столбик'];S.emb=3;
/* Выбор владельца 14.11: вид «Группы + цвет при выборе», эмблемы «Крупно, с обрезкой». Остальные варианты — только по адресу ?variants=1 (&look=0…8, &emb=0…9). */
const VARIANTS=/[?&]variants=1(?:&|$)/.test(location.search);
/* варианты на выбор владельцу (15.11): оформление купона и фон страницы. Временный переключатель на странице; ?slip=0…3, ?bg=0…4 */
const SLIPS=['Как сейчас','Билет','В цветах клубов','Светлый чек','Стекло','Жёлтая рамка'],SUMS=['Как сейчас','Жёлтая плашка','Табло','Итог сверху','Круг шанса'],BGS=['Как сейчас','Лёд','Свет арены','Графит','Глубокий синий'];
S.slip=3;S.bg=2;S.sum=3; /* выбор владельца 15.11: купон «Светлый чек», итог сверху, фон «Свет арены»; остальное — по ?variants=1 */
try{const q=new URLSearchParams(location.search);[['slip',5],['bg',4],['sum',4]].forEach(([k,mx])=>{const v=q.get(k);if(/^\d$/.test(v||'')&&+v<=mx)S[k]=+v})}catch(e){}
function skin(){const b=document.body;b.className=b.className.replace(/\s*\b(kb|ks|kt)\d\b/g,'')+' kb'+S.bg+' ks'+S.slip+' kt'+S.sum;
  if(!$('kp-bgfx'))b.insertAdjacentHTML('afterbegin','<div class="kp-bgfx" id="kp-bgfx" aria-hidden="true"></div>')}
/* Правило владельца 14.11: у этих клубов эмблема — лицо, которое смотрит влево. Когда они в гостях (эмблема справа), она ложится ПОВЕРХ эмблемы хозяев,
   иначе хозяева обрезают лицо. Чикаго, Миннесота, Анахайм, Флорида. */
const FACE_LEFT={nhl_chi:1,minnesota:1,nhl_ana:1,nhl_fla:1};
try{const v=new URLSearchParams(location.search).get('emb');if(/^[0-9]$/.test(v||''))S.emb=+v}catch(e){}
try{const q=new URLSearchParams(location.search).get('look'),v=q;if(/^[0-8]$/.test(v||''))S.look=+v}catch(e){}
function load(src){try{
  const d=typeof src==='string'?JSON.parse(src):src;if(!d)return;
  S.legs=(Array.isArray(d.legs)?d.legs:[]).filter(l=>l&&BY[l.k]&&grid(l.k)&&typeof l.o==='string'&&LEG.test(l.o));
  S.odds={};Object.entries(d.odds||{}).forEach(([k,v])=>{if(BY[k]&&ODD(v))S.odds[k]=String(v)});S.stake=/^\d{1,9}([.,]\d{1,2})?$/.test(String(d.stake))?String(d.stake):'1000';S.mode=d.mode==='s'?'s':'x';
}catch(e){}}
function dump(){return {legs:S.legs,odds:S.odds,stake:S.stake,mode:S.mode}}
function keep(){try{localStorage.setItem(LS_CUR,JSON.stringify(dump()))}catch(e){}}
function saved(){try{const v=JSON.parse(localStorage.getItem(LS_SAVED));return Array.isArray(v)?v.filter(s=>s&&typeof s==='object'&&typeof s.name==='string'&&typeof s.info==='string'&&s.data&&typeof s.data==='object').slice(0,12):[]}catch(e){return []}}
/* перед заменой купона по ссылке (#k=, ?want) прежний купон не теряем — кладём в «Сохранённые» (аудит 19.11) */
function stash(){if(!S.legs.length)return false;const sv=saved(),d=dump();const js=JSON.stringify(d);if(sv.some(s=>JSON.stringify(s.data)===js))return false;
  sv.unshift({name:'Прежний купон · '+S.legs.length+' '+plural(S.legs.length,'событие','события','событий'),info:'сохранён перед открытием ссылки',data:d});
  try{localStorage.setItem(LS_SAVED,JSON.stringify(sv.slice(0,12)));return true}catch(e){return false}}
/* ссылка на купон: #k=<ключ матча>~<событие>,<событие>@<кэф>;… */
function toHash(){return 'k='+encodeURIComponent(byMatch().map(g=>g.key+'~'+g.ids.join(',')+(S.odds[g.key]?'@'+S.odds[g.key]:'')).join(';'))}
function fromHash(){const h=location.hash.replace(/^#/,'');if(h.slice(0,2)!=='k=')return false;
  const legs=[],odds={};
  try{decodeURIComponent(h.slice(2)).split(';').forEach(part=>{const [key,rest]=part.split('~');if(!rest||!BY[key])return;
    const [ids,odd]=rest.split('@');ids.split(',').forEach(o=>{if(LEG.test(o))legs.push({k:key,o})});if(odd&&ODD(odd))odds[key]=odd})}catch(e){return false}
  if(!legs.length)return false;if(JSON.stringify([legs,odds,'x'])!==JSON.stringify([S.legs.map(l=>({k:l.k,o:l.o})),S.odds,S.mode]))fromHash.kept=stash();load({legs,odds,stake:S.stake,mode:'x'});S.link=true;return true}

function byMatch(){const out=[],ix={};
  S.legs.forEach(l=>{if(!(l.k in ix)){ix[l.k]=out.length;out.push({key:l.k,m:BY[l.k],ids:[]})}out[ix[l.k]].ids.push(l.o)});
  out.forEach(g=>{g.p=prob(g.key,g.ids);
    g.def=g.ids.length===1&&lineOdd(g.key,g.ids[0])||(g.p>0?Math.min(999,1/g.p):0);
    g.isLine=g.ids.length===1&&!!lineOdd(g.key,g.ids[0]);
    const u=num(S.odds[g.key]);g.user=u>1;g.k=g.user?u:g.def;g.live=started(g.m)});
  return out}
function has(key,id){return S.legs.some(l=>l.k===key&&l.o===id)}
function toggle(key,id){
  if(has(key,id))S.legs=S.legs.filter(l=>!(l.k===key&&l.o===id));
  else{const g=group(id);S.legs=S.legs.filter(l=>!(l.k===key&&group(l.o)===g));S.legs.push({k:key,o:id})}
  delete S.odds[key];keep();paint()}

/* ---------- расчёт купона ---------- */
function calc(){const G=byMatch(),n=G.length,stake=Math.max(0,num(S.stake)||0);
  const r={G,n,stake,events:S.legs.length,bad:G.some(g=>g.p<=0),live:G.some(g=>g.live),real:G.some(g=>g.user||g.isLine)};
  r.p=G.reduce((a,g)=>a*g.p,n?1:0);r.k=G.reduce((a,g)=>a*g.k,1);
  r.fair=r.p>0?1/r.p:0;r.win=stake*r.k;r.ev=r.p*r.k-1;
  r.sWin=G.reduce((a,g)=>a+stake*g.k,0);r.sAvg=G.reduce((a,g)=>a+g.p,0);r.sAny=1-G.reduce((a,g)=>a*(1-g.p),1);
  r.sEv=n?G.reduce((a,g)=>a+g.p*g.k,0)/n-1:0;
  return r}

/* ---------- отрисовка ---------- */
const emb=id=>'<img class="kp-em" src="../assets/em/'+esc(id)+'.webp" alt="" width="28" height="28" loading="lazy" onerror="this.style.visibility=\'hidden\'">';
/* на кнопке крупно кэф (владелец 15.11), мелко — шанс модели; кэф из линии — как есть, расчётный по модели — со знаком ≈ */
const KF=(p,lo)=>lo?fk(lo):p>0?'<s>≈</s>'+fk(Math.min(999,1/p)):'—';
function btn(m,id){const p=prob(m.key,[id]),lo=lineOdd(m.key,id),on=has(m.key,id),val=lo&&p*lo>=1.03;
  return '<button type="button" class="kp-o'+(on?' on':'')+(val?' val':'')+'" data-k="'+esc(m.key)+'" data-o="'+esc(id)+'" aria-pressed="'+on+'"'+(p<=0?' disabled':'')+
    ' title="'+esc(full(id,m))+'"><i>'+short(id)+'</i>'+(S.look===3?'<b>'+fp(p)+'</b>':'<b>'+KF(p,lo)+'</b><small>шанс '+fp(p)+'</small>')+'</button>'}
function mkt(m,g){return '<div class="kp-mk"><h4>'+esc(g.n)+'</h4><div class="kp-os'+(g.c?' c'+g.c:' c'+g.o.length)+'">'+g.o.map(id=>btn(m,id)).join('')+'</div></div>'}
const CHEV='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
/* компактные виды: на карточке только клубы и П1 · Х · П2, остальные события — по кнопке */
/* раскрытая линия матча — роспись плашками (владелец 15.11, по образцу росписи букмекера): у плашки заголовок, подпись «основное время» и сворачивание;
   строка тотала — «Меньше · линия · Больше»; в ячейке слева название исхода, справа шанс модели и кэф */
const FOLD={};
function cell(m,id,lab){const p=prob(m.key,[id]),lo=lineOdd(m.key,id),on=has(m.key,id),val=lo&&p*lo>=1.03;
  return '<button type="button" class="kp-o kp-c'+(on?' on':'')+(val?' val':'')+'" data-k="'+esc(m.key)+'" data-o="'+esc(id)+'" aria-pressed="'+on+'"'+(p<=0?' disabled':'')+
    ' title="'+esc(full(id,m))+'"><i>'+(Array.isArray(lab)?'<u>'+esc(lab[0])+'</u><em>'+esc(lab[1])+'</em>':esc(lab))+'</i><span><b>'+KF(p,lo)+'</b><small>'+fp(p)+'</small></span></button>'}
function panel(m){
  const sec=(id,t,sub,body)=>{const f=!!FOLD[id];return '<section class="kp-sec'+(f?' fold':'')+'"><button type="button" class="kp-sh2" data-fold="'+id+'" aria-expanded="'+!f+'"><span><b>'+esc(t)+'</b><small>'+sub+'</small></span>'+CHEV+'</button>'+(f?'':'<div class="kp-rows">'+body+'</div>')+'</section>'};
  const pair=(a,la,b,lb)=>'<div class="kp-tr n2">'+cell(m,a,la)+cell(m,b,lb)+'</div>';
  const ou=(pre,lines)=>lines.map(l=>'<div class="kp-tr ou">'+cell(m,pre+'u:'+l,'Меньше')+'<span class="kp-ln">'+fl(l)+'</span>'+cell(m,pre+'o:'+l,'Больше')+'</div>').join('');
  const RT='Основное время',il=[1.5,2.5,3.5,4.5];
  return '<div class="kp-all kp-pan"><div>'+
    sec('w','Победа в матче','С овертаймом и буллитами',pair('w:1',m.hn,'w:2',m.an))+
    sec('dc','Двойной шанс',RT,'<div class="kp-tr n3">'+cell(m,'dc:1x','1Х')+cell(m,'dc:12','12')+cell(m,'dc:x2','Х2')+'</div>')+
    sec('t','Тотал',RT,ou('t:',totalLines(m)))+
    sec('b','Обе забьют',RT,pair('b:y','Да','b:n','Нет'))+
    sec('ot','Овертайм','Ничья в основное время',pair('ot:y','Будет','ot:n','Не будет'))+
    sec('eo','Чёт / нечет',RT,pair('eo:e','Чёт','eo:o','Нечет'))+
    '</div><div>'+
    sec('f','Фора',RT,[[-2.5,2.5],[-1.5,1.5],[1.5,-1.5],[2.5,-2.5]].map(([a,b])=>pair('f:1:'+a,[m.hn,'('+fs(a)+')'],'f:2:'+b,[m.an,'('+fs(b)+')'])).join(''))+
    sec('i1','Тотал '+m.hn,RT,ou('it:1:',il))+sec('i2','Тотал '+m.an,RT,ou('it:2:',il))+
    '</div></div>'}
function card2(m){const mk=markets(m),open=!!S.open[m.key],legs=S.legs.filter(l=>l.k===m.key),hid=legs.filter(l=>l.o.slice(0,2)!=='r:').length,L=S.look;
  const c=cols(m),tm=(id,n)=>'<div class="kp-t">'+emb(id)+'<b>'+esc(n)+'</b></div>';
  const more='<button type="button" class="kp-more" data-more="'+esc(m.key)+'" aria-expanded="'+open+'" title="'+(open?'Свернуть':'Все события матча')+'"><span>'+(open?'Свернуть':'Все события')+'</span>'+(hid&&!open?'<em>'+hid+'</em>':'')+CHEV+'</button>';
  /* строки: крупные эмблемы во всю высоту строки, внахлёст, обрезаются краем плашки; у названий эмблемы не повторяем */
  const big=id=>'<img src="../assets/em/'+esc(id)+'.webp" alt="" loading="lazy" onerror="this.style.visibility=\'hidden\'">';
  if(L===1||L>=4)return '<article class="kp-m v v1'+(L>=4?' v'+L+(L===8?' v6':''):'')+(legs.length?' has':'')+(open?' open':'')+'" data-key="'+esc(m.key)+'" style="--h1:'+c[0]+';--h2:'+c[1]+';--hm:'+c[2]+'">'+
    '<div class="kp-hd"><div class="kp-logos'+(FACE_LEFT[m.a]?' aw':'')+'" aria-hidden="true">'+big(m.a)+big(m.h)+'</div><div class="kp-tms"><b>'+emb(m.h)+esc(m.hn)+'</b><b>'+emb(m.a)+esc(m.an)+'</b></div><div class="kp-when"><time>'+hm(m)+'</time><span class="kp-lg">'+LG[m.lg]+'</span></div></div>'+
    '<div class="kp-os c3 kp-x3">'+mk.main[0].o.map(id=>btn(m,id)).join('')+'</div>'+more+
    (open?panel(m):'')+'</article>';
  const head=L===2?
    '<div class="kp-hd"><div class="kp-when"><span class="kp-lg">'+LG[m.lg]+'</span><time>'+hm(m)+' <small>МСК</small></time></div><div class="kp-duo">'+tm(m.h,m.hn)+'<s>—</s>'+tm(m.a,m.an)+'</div></div>':
    '<div class="kp-hd"><div class="kp-when"><time>'+hm(m)+'</time><span class="kp-lg">'+LG[m.lg]+'</span></div><div class="kp-tms">'+tm(m.h,m.hn)+tm(m.a,m.an)+'</div></div>';
  return '<article class="kp-m v v'+L+(legs.length?' has':'')+(open?' open':'')+'" data-key="'+esc(m.key)+'" style="--h1:'+c[0]+';--h2:'+c[1]+';--hm:'+c[2]+'">'+
    head+'<div class="kp-os c3 kp-x3">'+mk.main[0].o.map(id=>btn(m,id)).join('')+'</div>'+more+
    (open?'<div class="kp-all">'+mk.main.slice(1).concat(mk.more).map(g=>mkt(m,Object.assign({c:2},g))).join('')+'</div>':'')+'</article>'}
function card(m){if(S.look)return card2(m);const mk=markets(m),open=!!S.open[m.key],cnt=S.legs.filter(l=>l.k===m.key).length,mod=MODEL[m.key];
  return '<article class="kp-m'+(cnt?' has':'')+'" data-key="'+esc(m.key)+'" style="--h1:'+cols(m)[0]+';--h2:'+cols(m)[1]+';--hm:'+cols(m)[2]+'">'+
    '<header><span class="kp-lg">'+LG[m.lg]+'</span><time>'+hm(m)+' <small>МСК</small></time>'+
      '<div class="kp-tm">'+emb(m.h)+'<b>'+esc(m.hn)+'</b><s>—</s><b>'+esc(m.an)+'</b>'+emb(m.a)+'</div>'+
      (mod?'<span class="kp-xg" title="Ожидаемые голы по модели">ожидаемые голы '+fl(mod.lam[0].toFixed(1))+' : '+fl(mod.lam[1].toFixed(1))+'</span>':'')+'</header>'+
    '<div class="kp-row">'+mk.main.map(g=>mkt(m,g)).join('')+'</div>'+
    '<button type="button" class="kp-more" data-more="'+esc(m.key)+'" aria-expanded="'+open+'">'+(open?'Свернуть линию':'Вся линия: форы, тоталы команд, обе забьют')+'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></button>'+
    (open?'<div class="kp-all">'+mk.more.map(g=>mkt(m,g)).join('')+'</div>':'')+
  '</article>'}
function visible(){return HM.filter(m=>grid(m.key)&&!started(m)&&(!S.lg||m.lg===S.lg)&&(!S.day||gameDay(m)===S.day))}
/* ночные матчи НХЛ относим к игровому дню накануне: «сегодня вечером и ночью» */
function gameDay(m){return mskDay(tms(m)-9*36e5)}
function paintList(){
  const all=HM.filter(m=>grid(m.key)&&!started(m)),days=[...new Set(all.map(gameDay))].sort();
  if(S.day&&!days.includes(S.day))S.day='';
  const lgs=[...new Set(all.map(m=>m.lg))];
  const chip=(a,v,t,cur)=>'<button type="button" data-'+a+'="'+v+'" aria-pressed="'+(cur===v)+'">'+t+'</button>';
  $('kp-filt').innerHTML=(lgs.length>1?'<div>'+chip('lg','','Все лиги',S.lg)+lgs.map(l=>chip('lg',l,LG[l],S.lg)).join('')+'</div>':'')+
    (days.length>1?'<div>'+chip('day','','Все дни',S.day)+days.map(d=>chip('day',d,dayName(d).split(',')[0],S.day)).join('')+'</div>':'');
  const vis=visible();let h='',cur='',grp='';
  vis.forEach(m=>{const d=gameDay(m);if(d!==cur){h+=(cur?'</div>':'')+'<h3 class="kp-day">'+dayName(d)+'</h3><div class="kp-set">';cur=d;grp=''}
    if(S.look>=7){const g=LG[m.lg]+' · начало в '+hm(m);if(g!==grp){grp=g;h+='<h4 class="kp-grp">'+g+' МСК</h4>'}}
    h+=card(m)});
  if(cur)h+='</div>';
  $('kp-list').className='kp-list l'+S.look+' e'+S.emb;
  if(VARIANTS&&(S.look===1||S.look>=4))$('kp-filt').insertAdjacentHTML('beforeend','<div class="kp-looks"><span>Эмблемы:</span>'+EMBS.map((n,i)=>'<button type="button" data-emb="'+i+'" aria-pressed="'+(S.emb===i)+'">'+n+'</button>').join('')+'</div>');
  if(VARIANTS)$('kp-filt').insertAdjacentHTML('beforeend','<div class="kp-looks"><span>Вид:</span>'+LOOKS.map((n,i)=>'<button type="button" data-look="'+i+'" aria-pressed="'+(S.look===i)+'">'+n+'</button>').join('')+'</div>');
  const sw=(t,k,arr)=>'<div class="kp-looks kp-sw"><span>'+t+'</span>'+arr.map((n,i)=>'<button type="button" data-skin="'+k+'" data-v="'+i+'" aria-pressed="'+(S[k]===i)+'">'+n+'</button>').join('')+'</div>';
  if(VARIANTS)$('kp-filt').insertAdjacentHTML('beforeend',sw('Купон:','slip',SLIPS)+sw('Итог купона:','sum',SUMS)+sw('Фон:','bg',BGS));
  $('kp-list').innerHTML=h||'<p class="kp-empty">'+(all.length?'По этому фильтру матчей нет.':'Ближайшие матчи уже начались. Новые появятся после обновления данных — обычно утром и днём.')+'</p>';
  $('kp-auto').hidden=!all.length;$('kp-filt').hidden=!VARIANTS;paintOpts();
}
const TG='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 3.2 2.9 10.4c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.7c.3-1.3-.5-1.9-1.4-1.5ZM8.3 13.2l9.6-6c.5-.3.9-.1.5.2l-8.2 7.4-.3 3.4-1.6-5Z"/></svg>';
function paintSlip(){
  const c=calc(),el=$('kp-slip'),sv=saved();
  let h='<div class="kp-sh"><h2>Купон'+(c.events?' <em>'+c.events+'</em>':'')+'</h2>'+(c.n?'<button type="button" data-act="clear">Очистить</button>':'')+
    '<button type="button" class="kp-x" data-act="close" aria-label="Закрыть купон">×</button></div>';
  if(!c.n){
    h+='<p class="kp-hint">Нажмите на событие в любом матче — оно появится здесь. Несколько событий одного матча складываются в комбинацию, разных матчей — в экспресс.</p>';
  }else{
    if(S.link)h+='<p class="kp-link">Купон собран пользователем по ссылке, это не прогноз JARVIS.</p>';
    if(c.n>1)h+='<div class="kp-mode" role="group" aria-label="Тип ставки"><button type="button" data-mode="x" aria-pressed="'+(S.mode==='x')+'">Экспресс</button><button type="button" data-mode="s" aria-pressed="'+(S.mode==='s')+'">Ординары</button></div>';
    h+='<ol class="kp-legs">'+c.G.map(g=>{const m=g.m;
      return '<li'+(g.p<=0?' class="bad"':'')+' style="--h1:'+cols(m)[0]+';--h2:'+cols(m)[1]+';--hm:'+cols(m)[2]+'"><div class="kp-lm"><span>'+LG[m.lg]+' · '+dm(m)+' '+hm(m)+'</span><b>'+esc(m.hn)+' — '+esc(m.an)+'</b></div>'+
        '<ul>'+g.ids.map(id=>'<li><span>'+esc(full(id,m))+'</span><button type="button" data-k="'+esc(g.key)+'" data-o="'+esc(id)+'" data-rm aria-label="Убрать событие">×</button></li>').join('')+'</ul>'+
        (g.live?'<p class="kp-warn">Матч уже начался.</p>':'')+
        (g.p<=0?'<p class="kp-warn">Эти события не могут сыграть вместе. Уберите одно из них.</p>':
        '<div class="kp-lk"><span>Шанс <b>'+fp(g.p)+'</b>'+(g.ids.length>1?' · комбинация':'')+'</span>'+
          '<label>кэф <input type="text" inputmode="decimal" data-odd="'+esc(g.key)+'" value="'+(g.user?esc(S.odds[g.key]):'')+'" placeholder="'+fk(g.def)+'" aria-label="Кэф у букмекера"></label></div>'+
          '<small class="kp-src">'+(g.user?'ваш кэф':g.isLine?'кэф из линии':'расчётный кэф по модели — впишите свой')+'</small>')+
      '</li>'}).join('')+'</ol>';
    h+='<div class="kp-sum" id="kp-sum"></div>';
    h+='<div class="kp-act"><button type="button" class="btn btn-tg" data-act="tg">'+TG+'<span>Отправить себе в Telegram</span></button>'+
      '<div><button type="button" data-act="copy">Скопировать</button><button type="button" data-act="img">Картинка</button><button type="button" data-act="save">Сохранить</button></div></div>';
  }
  if(sv.length)h+='<div class="kp-saved"><h3>Сохранённые купоны</h3><ul>'+sv.map((s,i)=>'<li><button type="button" data-load="'+i+'"><b>'+esc(s.name)+'</b><small>'+esc(s.info)+'</small></button><button type="button" data-del="'+i+'" aria-label="Удалить купон">×</button></li>').join('')+'</ul></div>';
  el.innerHTML=h;paintSum(c);
  const bar=$('kp-bar');bar.hidden=!c.n;
  if(c.n)bar.innerHTML='<span><b>Купон</b><em>'+c.events+'</em></span>'+(c.bad?'<span class="w">проверьте события</span>':S.mode==='x'?'<span>шанс <b>'+fp(c.p)+'</b></span><span>кэф <b>'+fk(c.k)+'</b></span>':'<span>ординары: <b>'+c.n+'</b></span>')+'<i>Открыть</i>';
  document.documentElement.classList.toggle('kp-open',S.sheet&&!!c.n);if(!c.n)S.sheet=false;
  modal();
}
function paintSum(c){c=c||calc();const el=$('kp-sum');if(!el)return;el.style.setProperty('--p',Math.round((S.mode==='s'&&c.n>1?c.sAny:c.p)*100));
  const stake='<label class="kp-stake"><span>Сумма'+(S.mode==='s'&&c.n>1?' на каждую':'')+'</span><input type="text" inputmode="decimal" id="kp-stake" value="'+esc(S.stake)+'" aria-label="Сумма ставки"></label>';
  if(c.bad){el.innerHTML='<p class="kp-warn">В купоне есть события, которые исключают друг друга.</p>';return}
  const evp=v=>'<p class="kp-ev '+(v>=0?'up':'dn')+'">'+(v>=0?'По расчёту модели кэф выше шанса: +':'По расчёту модели кэф ниже шанса: −')+Math.abs(Math.round(v*100))+' %</p>';
  if(S.mode==='s'&&c.n>1){
    el.innerHTML='<dl><div><dt>Ставок</dt><dd>'+c.n+'</dd></div><div><dt>В среднем зайдёт</dt><dd>'+fl(c.sAvg.toFixed(1))+' из '+c.n+'</dd></div><div><dt>Хотя бы одна</dt><dd>'+fp(c.sAny)+'</dd></div></dl>'+
      stake+'<p class="kp-win"><span>Если зайдут все</span><b>'+fm(c.sWin)+'</b></p><p class="kp-tot">Всего на кону: '+fm(c.stake*c.n)+'</p>'+(c.real?evp(c.sEv):'');
    return}
  el.innerHTML='<div class="kp-big"><div><span>Шанс купона</span><b>'+fp(c.p)+'</b><small>'+oneIn(c.p)+'</small></div><div><span>Общий кэф</span><b>'+fk(c.k)+'</b><small>'+(c.real?'по шансу модели — '+fk(c.fair):'расчётный')+'</small></div></div>'+
    '<div class="kp-meter" aria-hidden="true"><i style="width:'+Math.max(2,Math.round(c.p*100))+'%"></i></div>'+
    stake+'<p class="kp-win"><span>Возможный выигрыш</span><b>'+fm(c.win)+'</b></p>'+(c.real?evp(c.ev):'<p class="kp-ev">Кэфы расчётные. Впишите кэфы своего букмекера — увидите, выгоден ли купон по расчёту модели.</p>');
}
function paint(){paintList();paintSlip()}

/* ---------- «собрать за меня» ---------- */
/* подбор купона под желаемый кэф (владелец 15.11): чем меньше событий и чем они вероятнее, тем лучше, поэтому берём
   n ≈ ln(кэф)/ln(1,5) событий с шансом около кэф^(−1/n) — по одному на матч; последнее событие добирает кэф как можно ближе к цели */
const POOL=['r:1','r:2','w:1','w:2','dc:1x','dc:x2','dc:12','t:o:4.5','t:u:4.5','t:o:5.5','t:u:5.5','t:o:6.5','t:u:6.5','f:1:1.5','f:2:1.5','f:1:-1.5','f:2:-1.5','f:1:2.5','f:2:2.5',
  'it:1:o:1.5','it:2:o:1.5','it:1:o:2.5','it:2:o:2.5','it:1:u:2.5','it:2:u:2.5','it:1:u:3.5','it:2:u:3.5','b:y','ot:n'];
/* строка выбора под полем кэфа: дни из загруженного списка и число событий 1–8 (владелец 19.11) */
function paintOpts(){const all=HM.filter(m=>grid(m.key)&&!started(m)),days=[...new Set(all.map(gameDay))].sort();
  if(S.ad&&!days.includes(S.ad))S.ad='';
  const b=(k,v,t,on)=>'<button type="button" data-'+k+'="'+v+'" aria-pressed="'+on+'">'+t+'</button>';
  $('kp-ad').innerHTML='<span>Дни:</span>'+b('ad','','Все',!S.ad)+days.map(d=>b('ad',d,esc(dayName(d).split(',')[0]),S.ad===d)).join('');
  $('kp-ad').hidden=days.length<2;
  const mx=Math.min(8,new Set(all.filter(m=>!S.ad||gameDay(m)===S.ad).map(m=>m.key)).size);if(S.an>mx)S.an=0;
  $('kp-an').innerHTML='<span>Событий:</span>'+b('an',0,'Сам',!S.an)+Array.from({length:mx},(_,i)=>b('an',i+1,i+1,S.an===i+1)).join('');
  $('kp-opts').hidden=!all.length}
function auto(target){
  const ms=visible().filter(m=>(!S.alg||m.lg===S.alg)&&(!S.ad||gameDay(m)===S.ad));if(!ms.length){toast('Нет матчей для подбора'+(S.alg?' '+LG[S.alg]:'')+(S.ad?' — '+dayName(S.ad).split(',')[0].toLowerCase():''));return}
  const opts=m=>POOL.map(id=>{const p=prob(m.key,[id]);return p>.03&&p<.97?{k:m.key,o:id,p,odd:lineOdd(m.key,id)||1/p}:null}).filter(Boolean);
  const all=ms.map(opts).filter(a=>a.length),maxOdd=o=>Math.max(...o.map(x=>x.odd));
  let n=Math.max(1,Math.min(all.length,8,Math.round(Math.log(target)/Math.log(1.5))));
  while(n<Math.min(all.length,8)&&Math.pow(target,1/n)>3.2)n++;
  /* число событий задал посетитель: столько и берём (одно событие на матч), если матчей хватает */
  let few='';if(S.an){n=Math.min(S.an,all.length);if(n<S.an)few='Матчей хватило только на '+n+' '+plural(n,'событие','события','событий')+'. '}
  const leg=Math.pow(target,1/n),legs=[];let k=1;
  /* среди событий с подходящим кэфом берём самое вероятное по модели, а не просто ближайшее по кэфу */
  const near=(o,t,lo,hi)=>{const ok=o.filter(x=>x.odd>=t*lo&&x.odd<=t*hi);return ok.length?ok.reduce((a,b)=>b.p>a.p?b:a):o.reduce((a,b)=>Math.abs(Math.log(b.odd/t))<Math.abs(Math.log(a.odd/t))?b:a)};
  const rest=all.map(o=>({o,best:near(o,leg,.9,1.12)})).sort((a,b)=>Math.abs(Math.log(a.best.odd/leg))-Math.abs(Math.log(b.best.odd/leg)));
  for(let i=0;i<n-1;i++){const r=rest.shift();legs.push(r.best);k*=r.best.odd}
  /* последнее событие: любое из оставшихся матчей, чтобы общий кэф встал ближе всего к желаемому */
  let last=null;rest.forEach(r=>{const x=near(r.o,target/k,.96,1.1),in1=x.odd>=target/k*.96&&x.odd<=target/k*1.1,d=in1?-x.p:1+Math.abs(Math.log(k*x.odd/target));if(!last||d<last.d)last={x,d}});
  if(last){legs.push(last.x);k*=last.x.odd}
  S.legs=legs.map(l=>({k:l.k,o:l.o}));S.odds={};S.mode='x';keep();paint();
  toast(few+(k<target*.9&&!few?'Матчей мало: получился кэф '+fk(k)+' вместо '+fk(target):'Собран '+(legs.length>1?'экспресс из '+legs.length+' '+plural(legs.length,'события','событий','событий'):'ординар')+' с кэфом '+fk(k)));
  if(matchMedia('(max-width:1023px)').matches)openSheet(document.activeElement)
}
function autoGo(){const i=$('kp-want'),v=num(i.value);
  if(!(v>=1.2&&v<=500)){toast('Введите кэф от 1,2 до 500');i.focus();return}
  auto(v)}
const plural=(n,a,b,c)=>n%10===1&&n%100!==11?a:n%10>=2&&n%10<=4&&(n%100<10||n%100>=20)?b:c;

/* ---------- текст, картинка, отправка ---------- */
function link(){return location.origin+location.pathname+'#'+toHash()}
function text(){const c=calc(),x=S.mode==='x'||c.n<2,L=[];
  L.push('Купон JARVIS · '+(c.n<2?'ординар':x?'экспресс':'ординары')+' · '+c.events+' '+plural(c.events,'событие','события','событий'));L.push('');
  c.G.forEach((g,i)=>{L.push((i+1)+'. '+LG[g.m.lg]+' · '+dm(g.m)+' '+hm(g.m)+' МСК · '+g.m.hn+' — '+g.m.an);
    g.ids.forEach(id=>L.push('   • '+full(id,g.m)));L.push('   кэф '+fk(g.k)+(g.user||g.isLine?'':' (расчётный)')+' · шанс '+fp(g.p))});
  L.push('');
  if(x){L.push('Итого: кэф '+fk(c.k)+' · шанс '+fp(c.p));if(c.stake)L.push('Сумма '+fm(c.stake)+' → возможный выигрыш '+fm(c.win))}
  else{L.push('В среднем зайдёт '+fl(c.sAvg.toFixed(1))+' из '+c.n);if(c.stake)L.push('По '+fm(c.stake)+' на каждую, всего '+fm(c.stake*c.n))}
  L.push('');L.push('Шансы — расчёт модели, результат не гарантирован. 18+');return L.join('\n')}
function toast(t){const el=$('kp-toast');el.textContent=t;el.classList.add('on');clearTimeout(toast.t);toast.t=setTimeout(()=>el.classList.remove('on'),2600)}
function copy(){const t=text()+'\n'+link();
  const ok=()=>toast('Купон скопирован'),fb=()=>{const a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();try{document.execCommand('copy');ok()}catch(e){toast('Не удалось скопировать')}a.remove()};
  navigator.clipboard&&navigator.clipboard.writeText?navigator.clipboard.writeText(t).then(ok,fb):fb()}
function telegram(){window.open('https://t.me/share/url?url='+encodeURIComponent(link())+'&text='+encodeURIComponent(text()),'_blank','noopener');
  toast('В Telegram выберите «Избранное»')}
function image(){const c=calc(),x=S.mode==='x'||c.n<2,W=1080,P=64;
  const rows=[];c.G.forEach(g=>{rows.push({t:'m',g});g.ids.forEach(id=>rows.push({t:'e',s:full(id,g.m)}));rows.push({t:'k',g})});
  const H=250+rows.reduce((a,r)=>a+(r.t==='m'?92:r.t==='e'?50:74),0)+300;
  const cv=document.createElement('canvas');cv.width=W;cv.height=H;const x2=cv.getContext('2d');
  const ff=getComputedStyle(document.body).getPropertyValue('--display')||'sans-serif',F=(w,s)=>x2.font=w+' '+s+'px '+ff;
  x2.fillStyle='#071225';x2.fillRect(0,0,W,H);x2.fillStyle='#ffc21a';x2.fillRect(0,0,W,10);
  x2.textBaseline='alphabetic';F(800,34);x2.fillStyle='#eaf3ff';x2.fillText('JARVIS',P,96);
  F(800,68);x2.fillText('КУПОН',P,182);F(600,30);x2.fillStyle='#8fa6cc';x2.textAlign='right';
  x2.fillText((c.n<2?'ординар':x?'экспресс':'ординары')+' · '+c.events+' '+plural(c.events,'событие','события','событий'),W-P,182);x2.textAlign='left';
  let y=250;const fit=(s,w)=>{while(x2.measureText(s).width>w&&s.length>4)s=s.slice(0,-2);return s};
  rows.forEach(r=>{
    if(r.t==='m'){x2.fillStyle='#1e3460';x2.fillRect(P,y-8,W-2*P,2);F(600,26);x2.fillStyle='#8fa6cc';x2.fillText(LG[r.g.m.lg]+' · '+dm(r.g.m)+' '+hm(r.g.m)+' МСК',P,y+34);
      F(800,38);x2.fillStyle='#eaf3ff';x2.fillText(fit(r.g.m.hn+' — '+r.g.m.an,W-2*P),P,y+80);y+=92}
    else if(r.t==='e'){F(600,32);x2.fillStyle='#b8c9e4';x2.fillText(fit('•  '+r.s,W-2*P),P,y+38);y+=50}
    else{F(700,30);x2.fillStyle='#ffc21a';x2.fillText('кэф '+fk(r.g.k),P,y+40);x2.fillStyle='#3ee0ff';x2.fillText('шанс '+fp(r.g.p),P+250,y+40);y+=74}});
  x2.fillStyle='#0f1d38';x2.fillRect(P,y+10,W-2*P,170);
  F(600,26);x2.fillStyle='#8fa6cc';F(800,56);
  if(x){F(600,26);x2.fillText('ОБЩИЙ КЭФ',P+32,y+62);x2.fillText('ШАНС КУПОНА',P+360,y+62);if(c.stake)x2.fillText('ВЫИГРЫШ',P+700,y+62);
    F(800,60);x2.fillStyle='#ffc21a';x2.fillText(fk(c.k),P+32,y+138);x2.fillStyle='#3ee0ff';x2.fillText(fp(c.p),P+360,y+138);if(c.stake){x2.fillStyle='#eaf3ff';x2.fillText(fit(fm(c.win),250),P+700,y+138)}}
  else{F(600,26);x2.fillText('СТАВОК',P+32,y+62);x2.fillText('В СРЕДНЕМ ЗАЙДЁТ',P+360,y+62);F(800,60);x2.fillStyle='#ffc21a';x2.fillText(String(c.n),P+32,y+138);x2.fillStyle='#3ee0ff';x2.fillText(fl(c.sAvg.toFixed(1))+' из '+c.n,P+360,y+138)}
  F(500,24);x2.fillStyle='#8fa6cc';x2.fillText('Шансы — расчёт модели JARVIS, результат не гарантирован. 18+',P,y+240);x2.fillText('t.me/jarvibet',P,y+276);
  cv.toBlob(b=>{if(!b)return toast('Не удалось собрать картинку');const f=new File([b],'kupon-jarvis.png',{type:'image/png'});
    if(navigator.canShare&&navigator.canShare({files:[f]})&&matchMedia('(pointer:coarse)').matches){navigator.share({files:[f]}).catch(()=>{});return}
    const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=f.name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),4e3);toast('Картинка сохранена')},'image/png')}
function save(){const c=calc(),sv=saved(),d=new Date();
  sv.unshift({name:(c.n<2?'Ординар':S.mode==='x'?'Экспресс':'Ординары')+' · '+c.events+' '+plural(c.events,'событие','события','событий'),
    info:('0'+d.getDate()).slice(-2)+'.'+('0'+(d.getMonth()+1)).slice(-2)+' · '+(S.mode==='x'||c.n<2?'кэф '+fk(c.k)+' · шанс '+fp(c.p):c.G.map(g=>g.m.hn).join(', ')),data:dump()});
  try{localStorage.setItem(LS_SAVED,JSON.stringify(sv.slice(0,12)));toast('Купон сохранён на этом устройстве')}catch(e){toast('Не удалось сохранить')}paintSlip()}

/* мобильный лист купона (аудит 19.11, круг 3): одно открытие для полоски и автоподбора — фокус внутрь, удержание (Tab выше), возврат туда, откуда открыли */
/* узкий экран: открытый лист — модальное окно для экранного диктора (role=dialog, aria-modal), всё вокруг — inert (аудит 19.11, круг 4) */
const NARROW=matchMedia('(max-width:1023px)');
function modal(){const sl=$('kp-slip');if(!sl)return;const on=document.documentElement.classList.contains('kp-open')&&NARROW.matches;
  if(on){sl.setAttribute('role','dialog');sl.setAttribute('aria-modal','true')}else{sl.removeAttribute('role');sl.removeAttribute('aria-modal')}
  if(on){for(let n=sl;n&&n!==document.body;n=n.parentElement)for(const x of n.parentElement.children)if(x!==n&&x.tagName!=='SCRIPT'&&!x.inert){x.inert=true;x.dataset.kpInert='1'}}
  else document.querySelectorAll('[data-kp-inert]').forEach(x=>{x.inert=false;delete x.dataset.kpInert})}
try{NARROW.addEventListener('change',modal)}catch(e){}
let sheetFrom=null;
function openSheet(from){sheetFrom=from&&from!==document.body?from:null;S.sheet=true;paintSlip();/* сначала «Закрыть»: Enter не должен попасть на «Очистить» */const sl=$('kp-slip'),f=sl.querySelector('[data-act="close"]')||sl.querySelector('button:not([data-act="clear"]),input');if(f)setTimeout(()=>{try{f.focus({preventScroll:true})}catch(x){}},0)}
function closeSheet(){S.sheet=false;paintSlip();const to=sheetFrom&&sheetFrom.isConnected?sheetFrom:$('kp-bar');sheetFrom=null;try{if(to&&!to.hidden)to.focus({preventScroll:true})}catch(x){}}
/* ---------- события интерфейса ---------- */
/* перерисовка списка заменяет кнопки — возвращаем фокус на такую же кнопку (клавиатура, аудит 19.11) */
function refocus(b){if(b.isConnected)return;try{const ar=b.closest('[data-key]'),k=ar&&ar.dataset.key;
  const at=[...b.attributes].filter(x=>/^data-/.test(x.name)).map(x=>'['+x.name+'="'+CSS.escape(x.value)+'"]').join('');if(!at)return;
  const n=document.querySelector((k?'[data-key="'+CSS.escape(k)+'"] ':'')+'button'+at);if(n)n.focus({preventScroll:true})}catch(e){}}
document.addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b)return;const d=b.dataset;
  if(d.o&&d.k){toggle(d.k,d.o);refocus(b);return}
  if(d.skin){S[d.skin]=+d.v;try{localStorage.setItem('jv_kupon_'+d.skin,d.v)}catch(x){}skin();paintList();return}
  if(d.fold){FOLD[d.fold]=!FOLD[d.fold];paintList();refocus(b);return}
  if(d.more){S.open[d.more]=!S.open[d.more];paintList();refocus(b);return}
  if('look' in d){S.look=+d.look;try{localStorage.setItem('jv_kupon_look',d.look)}catch(x){}paintList();return}
  if('emb' in d){S.emb=+d.emb;try{localStorage.setItem('jv_kupon_emb',d.emb)}catch(x){}paintList();return}
  if('lg' in d){S.lg=d.lg;paintList();refocus(b);return}
  if('day' in d){S.day=d.day;paintList();refocus(b);return}
  if(d.act==='auto'){autoGo();return}
  if('ad' in d&&b.closest('#kp-ad')){S.ad=d.ad;paintOpts();refocus(b);return}
  if('an' in d&&b.closest('#kp-an')){S.an=+d.an;paintOpts();refocus(b);return}
  if(d.alg){S.alg=S.alg===d.alg?'':d.alg;document.querySelectorAll('[data-alg]').forEach(x=>x.setAttribute('aria-pressed',x.dataset.alg===S.alg));$('kp-alg-n').textContent=S.alg?'только '+LG[S.alg]:'КХЛ и НХЛ вместе';return}
  if(d.mode){S.mode=d.mode;keep();paintSlip();return}
  if(d.load){const s=saved()[+d.load];if(s){load(s.data);keep();paint();toast(S.legs.length?'Купон загружен':'Матчи этого купона уже сыграны')}return}
  if(d.del){const sv=saved();sv.splice(+d.del,1);try{localStorage.setItem(LS_SAVED,JSON.stringify(sv))}catch(x){}paintSlip();return}
  if(b.id==='kp-bar'){openSheet(b);return}
  switch(d.act){
    case 'clear':S.legs=[];S.odds={};S.link=false;keep();paint();break;
    case 'close':closeSheet();break;
    case 'tg':telegram();break;case 'copy':copy();break;case 'img':image();break;case 'save':save();break}
});
document.addEventListener('input',e=>{const t=e.target;
  if(t.id==='kp-stake'){S.stake=t.value;keep();const c=calc();refreshNumbers(c)}
  else if(t.dataset.odd){const v=t.value.trim();if(v)S.odds[t.dataset.odd]=v;else delete S.odds[t.dataset.odd];keep();refreshNumbers(calc())}});
/* при вводе не перерисовываем поля, чтобы не терять курсор */
function refreshNumbers(c){const st=$('kp-stake'),pos=st&&document.activeElement===st?st.selectionStart:null;
  paintSum(c);if(pos!==null){const n=$('kp-stake');n.focus();try{n.setSelectionRange(pos,pos)}catch(e){}}
  c.G.forEach(g=>{const i=document.querySelector('input[data-odd="'+CSS.escape(g.key)+'"]'),s=i&&i.closest('li').querySelector('.kp-src');
    if(s)s.textContent=g.user?'ваш кэф':g.isLine?'кэф из линии':'расчётный кэф по модели — впишите свой'})}
document.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target.id==='kp-want'){e.preventDefault();autoGo();return}if(e.key==='Escape'&&S.sheet){closeSheet();return}
  /* открытый мобильный лист: Tab и Shift+Tab ходят только внутри него */
  if(e.key==='Tab'&&S.sheet&&document.documentElement.classList.contains('kp-open')){const f=[...$('kp-slip').querySelectorAll('button,input,a[href],select,textarea')].filter(x=>!x.disabled&&x.offsetParent);if(!f.length)return;
    const i=f.indexOf(document.activeElement);if(e.shiftKey&&i<=0){e.preventDefault();f[f.length-1].focus()}else if(!e.shiftKey&&(i===-1||i===f.length-1)){e.preventDefault();f[0].focus()}}});

/* ---------- запуск ---------- */
try{load(localStorage.getItem(LS_CUR))}catch(e){}
if(fromHash()){keep();history.replaceState(null,'',location.pathname+location.search);if(fromHash.kept)setTimeout(()=>toast('Прежний купон — в «Сохранённых»'),400)}
if(T.built)$('kp-upd').textContent='Данные обновлены '+T.built.slice(8,10)+'.'+T.built.slice(5,7)+' в '+T.built.slice(11)+' МСК.';
/* в поле кэфа — случайный пример, новый при каждом открытии страницы (владелец 15.11) */
try{$('kp-want').placeholder=fk([1.6,1.8,2,2.2,2.4,2.7,3,3.5,4,4.5,5,6,7.5][Math.floor(Math.random()*13)]).replace(/,00$/,'').replace(/(,\d)0$/,'$1')}catch(e){}
skin();
/* вход с других страниц: kupon.html?m=<лига|день|хозяева|гости> — матч сразу раскрыт и на экране */
let FOCUS='';try{const k=new URLSearchParams(location.search).get('m');if(k&&BY[k]&&!started(BY[k])){S.open[k]=true;FOCUS=k}}catch(e){}
paint();
/* вход с баннера «Не знаете, на что поставить?»: kupon.html?want=3 — купон на этот кэф собирается сразу (владелец 18.11) */
try{const w=num(new URLSearchParams(location.search).get('want')||'');if(w>=1.2&&w<=500){$('kp-want').value=fk(w).replace(/,00$/,'');const kept=stash();auto(w);if(kept)setTimeout(()=>toast('Прежний купон — в «Сохранённых»'),2700);history.replaceState(null,'',location.pathname+location.hash)}}catch(e){}
if(FOCUS){const el=document.querySelector('.kp-m[data-key="'+CSS.escape(FOCUS)+'"]');if(el)setTimeout(()=>el.scrollIntoView({block:'start'}),60)}
setInterval(()=>{if(!document.hidden&&!document.activeElement.matches('input'))paint()},6e4);
})();
