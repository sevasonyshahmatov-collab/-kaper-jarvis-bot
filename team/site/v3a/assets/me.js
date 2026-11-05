/* JARVIS v3a — «Мой JARVIS» (этап B: без сервера). Избранные клубы — assets/fav.js (localStorage).
   Данные: data/search.json — клубы (c) и матчи (m: время МСК, спорт, хозяева, гости, счёт, кубок). Кэфов на странице нет. */
(()=>{
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const F=window.JVFav;
const LG={khl:'КХЛ',nhl:'НХЛ',epl:'АПЛ',laliga:'Ла Лига',seriea:'Серия А',bundesliga:'Бундеслига',ligue1:'Лига 1',rpl:'РПЛ',ucl:'Лига чемпионов',uel:'Лига Европы'};
const POP=['h:ska','h:cska','h:nhl_edm','h:nhl_tor','f:arsenal','f:real_madrid'];
const VK='jv_visit_v1',VS='jv_visit_prev';
let C={},M=[],ready=false;
const ms=t=>Date.parse(t.replace(' ','T')+':00+03:00');           /* время в данных — московское */
const page=c=>c.s==='h'?'../team/index.html?id='+encodeURIComponent(c.id):'../football/team.html?id='+encodeURIComponent(c.id);
const crest=c=>'../assets/'+(c.s==='h'?'em/':'fc/')+encodeURIComponent(c.id)+'.webp';
const img=c=>`<span class="me-cr"><img src="${esc(crest(c))}" alt="" loading="lazy" width="48" height="48"></span>`;
const fmtTime=t=>new Date(t).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'});
const dayKey=t=>{const d=new Date(t);return d.getFullYear()*1e4+d.getMonth()*100+d.getDate()};
const dayLabel=t=>{const n=Date.now(),k=dayKey(t);
  if(k===dayKey(n))return 'Сегодня';if(k===dayKey(n+864e5))return 'Завтра';if(k===dayKey(n-864e5))return 'Вчера';
  const s=new Date(t).toLocaleDateString('ru-RU',{weekday:'short',day:'numeric',month:'long'});return s.charAt(0).toUpperCase()+s.slice(1)};
const key=c=>c.s+':'+c.id;

/* прошлый визит: пока открыта вкладка, держим его в sessionStorage, чтобы перезагрузка не стирала «что изменилось» */
function lastVisit(){
  let prev=0;
  try{const p=sessionStorage.getItem(VS);if(p!==null)prev=+p||0;else{prev=+localStorage.getItem(VK)||0;sessionStorage.setItem(VS,String(prev))}}catch(e){}
  try{localStorage.setItem(VK,String(Date.now()))}catch(e){}
  return prev;
}
const PREV=lastVisit();

/* ── поиск и добавление ── */
const fold=s=>String(s).toLowerCase().replace(/ё/g,'е');
function find(q){
  q=fold(q).trim();if(!q)return[];
  const out=[];
  for(const k in C){const c=C[k];
    const hay=fold(c.ru+' '+c.en+' '+c.al),ws=hay.split(/[^a-zа-я0-9]+/);
    const st=ws.some(w=>w.startsWith(q))||fold(c.ru).startsWith(q);
    if(st||hay.includes(q))out.push([st?0:1,c.ru.length,c])}
  return out.sort((a,b)=>a[0]-b[0]||a[1]-b[1]).slice(0,8).map(x=>x[2]);
}
const qEl=$('q'),qRes=$('qres');
function drawRes(){
  const v=qEl.value;if(!ready||!v.trim()){qRes.hidden=true;qRes.innerHTML='';return}
  const r=find(v);
  qRes.innerHTML=r.length?r.map(c=>{const on=F.has(c.s,c.id);
    return `<li><button type="button" class="me-r" data-k="${esc(key(c))}"${on?' disabled':''}>${img(c)}<span class="me-rt"><b>${esc(c.ru)}</b><small>${c.s==='h'?'Хоккей':'Футбол'} · ${esc(LG[c.lg]||c.lg)}</small></span><span class="me-ra">${on?'Уже в списке':'Добавить'}</span></button></li>`}).join('')
   :`<li class="me-none">Такого клуба не нашли. Попробуйте название по-русски или по-английски.</li>`;
  qRes.hidden=false;
}
qEl.addEventListener('input',drawRes);
qEl.addEventListener('keydown',e=>{if(e.key==='Escape'){qEl.value='';drawRes()}
  if(e.key==='Enter'){e.preventDefault();const b=qRes.querySelector('.me-r:not([disabled])');if(b)b.click()}});
qRes.addEventListener('click',e=>{const b=e.target.closest('.me-r');if(!b||b.disabled)return;const k=b.dataset.k;F.add(k[0],k.slice(2));qEl.value='';drawRes();qEl.focus()});

/* ── клубы ── */
function nextOf(c,now){return M.find(m=>m.ms>now-3*36e5&&!m.sc&&(m.h===c||m.a===c))}
function drawClubs(){
  const fav=F.list().map(x=>C[x.s+':'+x.id]).filter(Boolean),box=$('clubsBox'),cnt=$('cnt');
  cnt.hidden=!fav.length;cnt.textContent=fav.length?fav.length+' '+(fav.length%10===1&&fav.length%100!==11?'клуб':fav.length%10>=2&&fav.length%10<=4&&(fav.length%100<10||fav.length%100>=20)?'клуба':'клубов'):'';
  if(!fav.length){
    const pop=POP.map(k=>C[k]).filter(Boolean);
    box.innerHTML=`<div class="me-empty"><div class="me-star" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 2.8l2.7 5.9 6.4.7-4.8 4.3 1.4 6.3L12 16.7l-5.7 3.3 1.4-6.3L2.9 9.4l6.4-.7z"/></svg></div>
      <h3>Здесь пока пусто</h3>
      <p>Выберите клубы, за которыми следите, — мы соберём их ближайшие матчи и результаты. Звёздочка «В избранное» есть и на странице каждого клуба.</p>
      <ul class="me-pop" aria-label="Популярные клубы">${pop.map(c=>`<li><button type="button" class="me-pb" data-k="${esc(key(c))}">${img(c)}<span><b>${esc(c.ru)}</b><small>${esc(LG[c.lg]||c.lg)}</small></span><i aria-hidden="true">+</i></button></li>`).join('')}</ul></div>`;
    return;
  }
  const now=Date.now();
  box.innerHTML=`<ul class="me-grid">${fav.map(c=>{const n=nextOf(c,now),opp=n?(n.h===c?n.a:n.h):null;
    return `<li class="me-card"><a class="me-cl" href="${esc(page(c))}">${img(c)}<span class="me-ct"><b>${esc(c.ru)}</b><small>${c.s==='h'?'Хоккей':'Футбол'} · ${esc(LG[c.lg]||c.lg)}</small></span></a>
      <p class="me-cn">${n?`Ближайший матч: <b>${n.h===c?'дома с':'в гостях у'} ${esc(opp.ru)}</b><br><span>${esc(dayLabel(n.ms).toLowerCase())}, ${esc(fmtTime(n.ms))}</span>`:'Ближайшего матча в данных пока нет'}</p>
      ${F.btn(c.s,c.id,'favbtn-ico').replace('class="favbtn','data-name="'+esc(c.ru)+'" class="favbtn')}</li>`}).join('')}</ul>`;
}
$('clubsBox').addEventListener('click',e=>{const b=e.target.closest('.me-pb');if(b){const k=b.dataset.k;F.add(k[0],k.slice(2))}});

/* ── строка матча ── */
function row(m,fav){
  const sc=m.sc?m.sc.split(' '):null,res=sc?sc[0].split(':').map(Number):null;
  let badge='';
  if(res&&fav){const mine=fav.has(m.h)&&!fav.has(m.a)?0:fav.has(m.a)&&!fav.has(m.h)?1:-1;
    if(mine>=0){const a=res[mine],b=res[1-mine];badge=a>b?'<i class="me-b w" title="Победа">В</i>':a<b?'<i class="me-b l" title="Поражение">П</i>':'<i class="me-b d" title="Ничья">Н</i>'}}
  const ex=sc&&sc[1]?` <small>${esc(sc.slice(1).join(' '))}</small>`:'';
  return `<li class="me-m"><div class="me-mt">
    <a class="me-tm" href="${esc(page(m.h))}" title="Страница клуба: ${esc(m.h.ru)}">${img(m.h)}<b>${esc(m.h.ru)}</b></a>
    <span class="me-mc">${sc?`<strong class="num">${esc(sc[0].replace(':',' : '))}</strong>${ex}`:`<strong class="num">${esc(fmtTime(m.ms))}</strong>`}</span>
    <a class="me-tm r" href="${esc(page(m.a))}" title="Страница клуба: ${esc(m.a.ru)}"><b>${esc(m.a.ru)}</b>${img(m.a)}</a></div>
    <span class="me-ml">${badge}${esc(LG[m.cup||m.h.lg]||'')}</span></li>`;
}
function group(list,fav){
  let out='',last='';
  for(const m of list){const d=dayLabel(m.ms);if(d!==last){out+=(last?'</ul>':'')+`<h3 class="me-day">${esc(d)}</h3><ul class="me-ms">`;last=d}out+=row(m,fav)}
  return out+(last?'</ul>':'');
}
function drawMatches(){
  const fav=new Set(F.list().map(x=>C[x.s+':'+x.id]).filter(Boolean)),now=Date.now();
  const nx=$('next'),sn=$('since');
  if(!fav.size){nx.hidden=sn.hidden=true;return}
  const mine=M.filter(m=>fav.has(m.h)||fav.has(m.a));
  const up=mine.filter(m=>!m.sc&&m.ms>now-3*36e5).sort((a,b)=>a.ms-b.ms).slice(0,12);
  nx.hidden=false;
  let tz='';try{tz=Intl.DateTimeFormat().resolvedOptions().timeZone||''}catch(e){}
  $('tzNote').textContent=tz?'Время — по вашему часовому поясу ('+tz.replace(/_/g,' ')+')':'Время — по вашему часовому поясу';
  $('nextBox').innerHTML=up.length?group(up,fav):'<p class="me-load">Ближайших матчей ваших клубов в данных пока нет. Данные обновляются дважды в день.</p>';
  /* что изменилось с прошлого визита; в первый раз — результаты за последние 5 дней */
  const from=PREV||now-5*864e5,first=!PREV;
  const done=mine.filter(m=>m.sc&&m.ms<=now&&m.ms>from).sort((a,b)=>b.ms-a.ms).slice(0,12);
  sn.hidden=false;
  const d=new Date(from).toLocaleDateString('ru-RU',{day:'numeric',month:'long'});
  $('sinceNote').textContent=first?'Это ваш первый визит — показываем последние 5 дней':'Прошлый визит — '+d;
  $('sinceBox').innerHTML=done.length?group(done,fav):`<p class="me-load">${first?'За последние дни ваши клубы не играли или счёта ещё нет в данных.':'С прошлого визита ваши клубы не сыграли ни одного матча или счёта ещё нет в данных.'}</p>`;
}

function draw(){drawClubs();drawMatches();drawRes();F.sync()}
F.onchange(()=>{if(ready)draw()});

/* ── очистка ── */
const cl=$('clear');let ct=0;
cl.addEventListener('click',()=>{
  if(!cl.dataset.arm){cl.dataset.arm='1';cl.textContent='Точно стереть? Нажмите ещё раз';clearTimeout(ct);ct=setTimeout(()=>{delete cl.dataset.arm;cl.textContent='Очистить мои данные'},4000);return}
  clearTimeout(ct);delete cl.dataset.arm;F.clear();cl.textContent='Готово: данные стёрты';setTimeout(()=>{cl.textContent='Очистить мои данные'},2500);
});

/* ── загрузка данных ── */
fetch('../data/search.json',{cache:'default'}).then(r=>{if(!r.ok)throw 0;return r.json()}).then(D=>{
  D.c.forEach(r=>{C[r[1]+':'+r[0]]={id:r[0],s:r[1],lg:r[2],ru:r[3],en:r[4],al:r[5]||''}});
  M=D.m.map(r=>{const h=C[r[1]+':'+r[2]],a=C[r[1]+':'+r[3]];return h&&a?{ms:ms(r[0]),h,a,sc:r[4]||'',cup:r[5]||''}:null}).filter(Boolean);
  ready=true;draw();
}).catch(()=>{$('clubsBox').innerHTML='<p class="me-load">Не удалось загрузить список клубов. Обновите страницу.</p>'});
})();
