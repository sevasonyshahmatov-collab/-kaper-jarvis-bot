/* фото КХЛ без белого фона (черновик 14.11): адрес khl.ru -> hockey/data/kph/<папка>_<номер>.webp (hockey/khl_cut.py) */
window.JV_KPH=window.JV_KPH||(S=>u=>{if(!window.JV_KPH_ON)return u;const m=/khl\.ru\/img\/teamplayers_db\/(\d+)\/(\d+)\.jpg/.exec(u||'');return m&&S?new URL('../hockey/data/kph/'+m[1]+'_'+m[2]+'.webp',S).href:u})(document.currentScript&&document.currentScript.src);
/* Раздел «Игроки НХЛ» (прототип 03.11): данные — hockey/data/nhl_players.json (сборщик nhl_players_fetch.py, Actions).
   Рынки «n из N» по своим матчам игрока: очко, гол, передача, 3+ броска; форма 10, TOI, дом/выезд, следующий соперник. */
(()=>{
const LG=document.documentElement.dataset.league||'nhl';
const TMK={"dinamo_msk":["Динамо Москва","#003da5"],"avangard":["Авангард","#c8102e"],"amur":["Амур","#f26522"],"cska":["ЦСКА","#e30613"],"spartak":["Спартак","#d7141a"],"torpedo":["Торпедо","#1e3a93"],"sibir":["Сибирь","#1b325a"],"lokomotiv":["Локомотив","#e30613"],"traktor":["Трактор","#aaaaaa"],"metallurg":["Металлург","#f5a623"],"salavat":["Салават Юлаев","#d4af37"],"neftekhimik":["Нефтехимик","#1c3f6e"],"dinamo_minsk":["Динамо Минск","#4db2ec"],"akbars":["Ак Барс","#007a48"],"severstal":["Северсталь","#ffcc00"],"ska":["СКА","#e31e24"],"barys":["Барыс","#2aa7b8"],"avtomobilist":["Автомобилист","#e30613"],"admiral":["Адмирал","#c8a96a"],"lada":["Лада","#0f4c81"],"sochi":["Сочи","#f5b400"],"shanghai":["Шанхайские Драконы","#ff5a00"]};
const TMN={"CAR":["Каролина","#cc0000"],"EDM":["Эдмонтон","#ff4c00"],"BOS":["Бостон","#ffb81c"],"MTL":["Монреаль","#af1e2d"],"VGK":["Вегас","#b4975a"],"OTT":["Оттава","#c8102e"],"TBL":["Тампа-Бэй","#123e8c"],"NJD":["Нью-Джерси","#ce1126"],"FLA":["Флорида","#c8102e"],"UTA":["Юта","#71afe5"],"TOR":["Торонто","#103c8c"],"COL":["Колорадо","#822d48"],"SEA":["Сиэтл","#006080"],"BUF":["Баффало","#003087"],"WSH":["Вашингтон","#c8102e"],"NYI":["Айлендерс","#00539b"],"STL":["Сент-Луис","#002f87"],"DET":["Детройт","#ce1126"],"NSH":["Нэшвилл","#ffb81c"],"NYR":["Рейнджерс","#0038a8"],"SJS":["Сан-Хосе","#006d75"],"ANA":["Анахайм","#f47a38"],"CGY":["Калгари","#d2001c"],"PIT":["Питтсбург","#fcb514"],"PHI":["Филадельфия","#f74902"],"WPG":["Виннипег","#16386e"],"CBJ":["Коламбус","#143c82"],"LAK":["Лос-Анджелес","#828c91"],"CHI":["Чикаго","#cf0a2c"],"VAN":["Ванкувер","#003e82"],"DAL":["Даллас","#006847"],"MIN":["Миннесота","#154734"]};
const TM=LG==='khl'?TMK:TMN;let JY=window.JV_JERSEY;
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const em=ab=>(ab=String(ab??'').replace(/[^\w-]/g,''),LG==='khl'?`../assets/em/${ab}.webp`:ab==='MIN'?'../assets/em/l/minnesota.webp':ab==='DAL'?'../assets/em/l/dallas.webp':`../assets/em/l/nhl_${ab.toLowerCase()}.webp`);
const ini=n=>n.split(/\s+/).filter(Boolean).map(w=>w[0]).slice(0,2).join('').toUpperCase();
const tn=ab=>(TM[ab]||[ab])[0];
const MK={pt:{f:r=>r[4]+r[5]>0,v:r=>r[4]+r[5],w:'набирал очко'},g:{f:r=>r[4]>0,v:r=>r[4],w:'забивал'},a:{f:r=>r[5]>0,v:r=>r[5],w:'отдавал передачу'},s3:{f:r=>r[6]>=3,v:r=>r[6],w:'бросал 3+ раза в створ'}};
const POS={'':'Все',F:'Нападающие',D:'Защитники'};
const URLT=new URLSearchParams(location.search).get('team')||'';
const URLQ=(new URLSearchParams(location.search).get('q')||'').slice(0,60);
const st={m:'pt',pos:'',tm:URLT in TM?URLT:'',ha:'',so:'G',q:URLQ,lim:30};
const mmss=s=>`${Math.floor(s/60)}:${String(Math.round(s%60)).padStart(2,'0')}`;
const pl=(n,a,b,c)=>{n=Math.abs(n)%100;const k=n%10;return n>10&&n<20?c:k===1?a:k>1&&k<5?b:c};
fetch((window.JVD||(u=>u))(`data/plite_${LG}.json`)).then(r=>r.json()).then(D=>{
 $('season').textContent=D.season;
 /* 17.11: переключатель лиг рядом с заголовком (раньше со страницы игроков НХЛ нельзя было перейти к игрокам КХЛ) */
 {const h=document.querySelector('.pl-hero');if(h&&!h.querySelector('.pl-lgsw')){const n=document.createElement('nav');n.className='pl-lgsw';n.setAttribute('aria-label','Лига');
  n.innerHTML=[['nhl','НХЛ','players.html'],['khl','КХЛ','players_khl.html']].map(([k,t,u])=>`<a href="${u}"${k===LG?' aria-current="page"':''}><i><img src="../assets/lg/${k}.webp" alt=""></i>${t}</a>`).join('');h.appendChild(n)}}
 $('lg').innerHTML=Object.entries(POS).map(([k,v])=>`<button type="button" data-l="${k}" aria-pressed="${!k}">${v}</button>`).join('');
 $('tm').innerHTML='<option value="">Все</option>'+Object.keys(TM).sort((a,b)=>tn(a).localeCompare(tn(b),'ru')).map(a=>`<option value="${a}"${a===st.tm?' selected':''}>${esc(tn(a))}</option>`).join('');
 const P=D.players.map(p=>{const L=p.log=p.log.map(r=>[r[0],'',r[1],r[2],r[3],r[4],r[5],r[6]]),n=L.length;return{...p,gp:n,G:L.reduce((s,r)=>s+r[4],0),A:L.reduce((s,r)=>s+r[5],0),S:L.reduce((s,r)=>s+r[6],0),toi:p.ts!=null?p.ts:(n?L.reduce((s,r)=>s+(r[7]||0),0)/n:0)}});
 function render(){
  /* цвета клубов (club/jersey.js): если файл не успел/не смог загрузиться — догружаем и перерисовываем (владелец 07.11: плашки были без цветов) */
  JY=window.JV_JERSEY;if(!JY&&!render.j){render.j=1;const sc=document.createElement('script');sc.src='../assets/club/jersey.js?r=2';sc.onload=()=>render();document.head.appendChild(sc)}
  const M=MK[st.m],q=st.q.trim().toLowerCase();
  let L=P.filter(p=>(!st.pos||(st.pos==='D'?p.pos==='D':p.pos!=='D'))&&(!st.tm||p.t===st.tm)&&(!q||p.n.toLowerCase().includes(q)));
  L=L.map(p=>{const lg=st.ha?p.log.filter(r=>r[3]===(st.ha==='home'?1:0)):p.log;const k=lg.filter(M.f).length;return{p,h:[k,(!st.ha&&p.gp)?Math.max(p.gp,k):lg.length]}}).filter(x=>x.h[0]>0&&x.h[1]>=(st.ha?3:5));
  const tot=p=>st.m==='g'?p.G:st.m==='a'?p.A:st.m==='s3'?p.S:p.G+p.A;
  const val=x=>st.so==='n'?x.h[0]:st.so==='G'?tot(x.p):st.so==='toi'?x.p.toi:x.h[0]/x.h[1];
  L.sort((a,b)=>val(b)-val(a)||b.h[0]-a.h[0]||a.p.n.localeCompare(b.p.n));
  $('meta').textContent=`${L.length} ${pl(L.length,'игрок','игрока','игроков')} · данные на ${(b=>{const m=/(\d{4})-(\d\d)-(\d\d)[ T](\d\d:\d\d)/.exec(String(b||''));return m?+m[3]+' '+['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'][+m[2]-1]+', '+m[4]+' МСК':String(b||'')})(D.built)}`;
  /* 17.11 — новый вид: тройка лидеров крупными карточками в цветах клуба, остальные — плотной таблицей (форма за 10 матчей, И/Г/П/О) */
  const key=st.m==='g'?'g':st.m==='a'?'a':st.m==='s3'?'s':'p',SH=LG==='nhl';
  const kv=p=>{const jk=JY?JY.key(LG,p.t):'',jv=JY&&JY.vars(jk),c=(TM[p.t]||[])[1]||'#334';return jv||`--kb:${c};--kbm:${c};--ks:#fff;--kt:#fff;--kx:#fff;--ko:#fff;--ko2:rgba(255,255,255,.78);--kp:${c}`};
  const ph=p=>p.img?esc(JV_KPH(p.img)):'';
  const nmB=p=>p.id!=null?`<a href="player.html?lg=${LG}&id=${p.id}" title="Профиль игрока">${esc(p.n)}</a>`:esc(p.n);
  const team=p=>`<img class="te" src="${em(p.t)}" alt="" loading="lazy" onerror="this.remove()">${esc(tn(p.t))} · ${p.pos==='D'?'защитник':'нападающий'}`;
  const form=p=>{const L10=p.log.slice(-10),mx=Math.max(st.m==='s3'?4:2,...L10.map(M.v));
   return `<div class="frm" aria-hidden="true">${L10.map(r=>{const ok=M.f(r),v=M.v(r);return `<i class="${ok?'g':''}" style="--h:${Math.max(.1,v/mx)}" title="${esc(r[0].slice(8,10)+'.'+r[0].slice(5,7)+' '+(r[3]?'дома, ':'в гостях, ')+tn(r[2]))}: ${r[4]}+${r[5]}"></i>`}).join('')}</div>`};
  const view=L.slice(0,st.lim),podN=view.length>=3?3:0;
  const pod=view.slice(0,podN).map((x,i)=>{const p=x.p;
   return `<article class="pod pod${i+1}" role="listitem" style="${kv(p)}"><img class="wm" src="${em(p.t)}" alt="" aria-hidden="true" loading="lazy" onerror="this.remove()"><i class="wms" aria-hidden="true" style="--em:url('${em(p.t)}')"></i>${p.no!=null?`<span class="no" aria-hidden="true">${esc(p.no)}</span>`:''}
    ${ph(p)?`<img class="cut" src="${ph(p)}" referrerpolicy="no-referrer" alt="" loading="lazy" onerror="this.remove()">`:''}
    <span class="prk"><b>${i+1}</b><small>место</small></span>
    <div class="pnm"><b>${nmB(p)}</b><span>${team(p)}</span></div>
    <dl class="pst"><div class="${key==='p'?'on':''}"><dt>Очки</dt><dd>${p.G+p.A}</dd></div><div class="${key==='g'?'on':''}"><dt>Голы</dt><dd>${p.G}</dd></div><div class="${key==='a'?'on':''}"><dt>Передачи</dt><dd>${p.A}</dd></div>${SH&&key==='s'?`<div class="on"><dt>Броски</dt><dd>${p.S}</dd></div>`:`<div><dt>Игры</dt><dd>${p.gp}</dd></div>`}</dl>
   </article>`}).join('');
  const th=(k,t,ti)=>`<span class="c${k===key?' on':''}${k==='gp'?' hm':''}" title="${ti}">${t}</span>`;
  const rows=view.slice(podN).map((x,i)=>{const p=x.p;
   return `<article class="lr" role="listitem" style="${kv(p)}"><span class="rk">${i+podN+1}</span>
    <span class="lav">${ph(p)?`<img class="ph" src="${ph(p)}" referrerpolicy="no-referrer" alt="" loading="lazy" onerror="this.remove()">`:''}<img class="bd" src="${em(p.t)}" alt="" loading="lazy" onerror="this.remove()"></span>
    <div class="nm"><b>${nmB(p)}</b><span>${team(p)}</span></div>${form(p)}
    <span class="c hm">${p.gp}</span><span class="c${key==='g'?' on':''}">${p.G}</span><span class="c${key==='a'?' on':''}">${p.A}</span>${SH?`<span class="c hm${key==='s'?' on':''}">${p.S}</span>`:''}<span class="c pt${key==='p'?' on':''}">${p.G+p.A}</span></article>`}).join('');
  $('list').innerHTML=(podN?`<div class="podium">${pod}</div>`:'')+(rows?`<div class="lb${SH?' sh':''}"><div class="lrh" aria-hidden="true"><span>#</span><span></span><span>Игрок</span><span class="fh">Последние 10 матчей</span>${th('gp','И','Игры')}${th('g','Г','Голы')}${th('a','П','Передачи')}${SH?th('s','Бр','Броски в створ').replace('class="c','class="c hm'):''}${th('p','О','Очки')}</div>${rows}</div>`:'');
  $('list').classList.remove('two');
  /* появление карточек анимируем только при первом показе, а не на каждый ввод в поиске или смену фильтра (ревью анимаций 17.11) */
  $('list').classList.toggle('first',!render.shown);render.shown=1;
  $('more').hidden=L.length<=st.lim}
 $('mk').onclick=e=>{const b=e.target.closest('button');if(!b)return;st.m=b.dataset.m;st.lim=30;$('mk').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));render()};
 $('lg').onclick=e=>{const b=e.target.closest('button');if(!b)return;st.pos=b.dataset.l;st.lim=30;$('lg').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));render()};
 $('tm').onchange=e=>{st.tm=e.target.value;st.lim=30;render()};
 $('ha').onchange=e=>{st.ha=e.target.value;render()};
 $('so').onchange=e=>{st.so=e.target.value;render()};
 $('q').oninput=e=>{st.q=e.target.value;st.lim=30;render()};
 $('more').onclick=()=>{st.lim+=30;render()};
 $('q').value=st.q;
 if(LG==='khl'){const b=document.querySelector('[data-m=s3]');if(b)b.remove()}
 render();
}).catch(()=>{$('meta').textContent='Данные игроков ещё не собраны.'});
})();
