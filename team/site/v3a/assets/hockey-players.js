/* фото КХЛ без белого фона (черновик 14.11): адрес khl.ru -> hockey/data/kph/<папка>_<номер>.webp (hockey/khl_cut.py) */
window.JV_KPH=window.JV_KPH||(S=>u=>{const m=/khl\.ru\/img\/teamplayers_db\/(\d+)\/(\d+)\.jpg/.exec(u||'');return m&&S?new URL('../hockey/data/kph/'+m[1]+'_'+m[2]+'.webp',S).href:u})(document.currentScript&&document.currentScript.src);
/* Раздел «Игроки НХЛ» (прототип 03.11): данные — hockey/data/nhl_players.json (сборщик nhl_players_fetch.py, Actions).
   Рынки «n из N» по своим матчам игрока: очко, гол, передача, 3+ броска; форма 10, TOI, дом/выезд, следующий соперник. */
(()=>{
const LG=document.documentElement.dataset.league||'nhl';
const TMK={"dinamo_msk":["Динамо Москва","#003da5"],"avangard":["Авангард","#c8102e"],"amur":["Амур","#f26522"],"cska":["ЦСКА","#e30613"],"spartak":["Спартак","#d7141a"],"torpedo":["Торпедо","#1e3a93"],"sibir":["Сибирь","#1b325a"],"lokomotiv":["Локомотив","#e30613"],"traktor":["Трактор","#aaaaaa"],"metallurg":["Металлург","#f5a623"],"salavat":["Салават Юлаев","#d4af37"],"neftekhimik":["Нефтехимик","#1c3f6e"],"dinamo_minsk":["Динамо Минск","#4db2ec"],"akbars":["Ак Барс","#007a48"],"severstal":["Северсталь","#ffcc00"],"ska":["СКА","#e31e24"],"barys":["Барыс","#2aa7b8"],"avtomobilist":["Автомобилист","#e30613"],"admiral":["Адмирал","#c8a96a"],"lada":["Лада","#0f4c81"],"sochi":["Сочи","#f5b400"],"shanghai":["Шанхайские Драконы","#ff5a00"]};
const TMN={"CAR":["Каролина","#cc0000"],"EDM":["Эдмонтон","#ff4c00"],"BOS":["Бостон","#ffb81c"],"MTL":["Монреаль","#af1e2d"],"VGK":["Вегас","#b4975a"],"OTT":["Оттава","#c8102e"],"TBL":["Тампа-Бэй","#123e8c"],"NJD":["Нью-Джерси","#ce1126"],"FLA":["Флорида","#c8102e"],"UTA":["Юта","#71afe5"],"TOR":["Торонто","#103c8c"],"COL":["Колорадо","#822d48"],"SEA":["Сиэтл","#006080"],"BUF":["Баффало","#003087"],"WSH":["Вашингтон","#c8102e"],"NYI":["Айлендерс","#00539b"],"STL":["Сент-Луис","#002f87"],"DET":["Детройт","#ce1126"],"NSH":["Нэшвилл","#ffb81c"],"NYR":["Рейнджерс","#0038a8"],"SJS":["Сан-Хосе","#006d75"],"ANA":["Анахайм","#f47a38"],"CGY":["Калгари","#d2001c"],"PIT":["Питтсбург","#fcb514"],"PHI":["Филадельфия","#f74902"],"WPG":["Виннипег","#16386e"],"CBJ":["Коламбус","#143c82"],"LAK":["Лос-Анджелес","#828c91"],"CHI":["Чикаго","#cf0a2c"],"VAN":["Ванкувер","#003e82"],"DAL":["Даллас","#006847"],"MIN":["Миннесота","#154734"]};
const TM=LG==='khl'?TMK:TMN;let JY=window.JV_JERSEY;
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const em=ab=>(ab=String(ab??'').replace(/[^\w-]/g,''),LG==='khl'?`../assets/em/${ab}.webp`:ab==='MIN'?'../assets/em/minnesota.webp':ab==='DAL'?'../assets/em/dallas.webp':`../assets/em/nhl_${ab.toLowerCase()}.webp`);
const ini=n=>n.split(/\s+/).filter(Boolean).map(w=>w[0]).slice(0,2).join('').toUpperCase();
const tn=ab=>(TM[ab]||[ab])[0];
const MK={pt:{f:r=>r[4]+r[5]>0,v:r=>r[4]+r[5],w:'набирал очко'},g:{f:r=>r[4]>0,v:r=>r[4],w:'забивал'},a:{f:r=>r[5]>0,v:r=>r[5],w:'отдавал передачу'},s3:{f:r=>r[6]>=3,v:r=>r[6],w:'бросал 3+ раза в створ'}};
const POS={'':'Все',F:'Нападающие',D:'Защитники'};
const URLT=new URLSearchParams(location.search).get('team')||'';
const URLQ=(new URLSearchParams(location.search).get('q')||'').slice(0,60);
const st={m:'pt',pos:'',tm:URLT in TM?URLT:'',ha:'',so:'G',q:URLQ,lim:30};
const mmss=s=>`${Math.floor(s/60)}:${String(Math.round(s%60)).padStart(2,'0')}`;
const pl=(n,a,b,c)=>{n=Math.abs(n)%100;const k=n%10;return n>10&&n<20?c:k===1?a:k>1&&k<5?b:c};
fetch(`data/plite_${LG}.json`).then(r=>r.json()).then(D=>{
 $('season').textContent=D.season;
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
  $('list').innerHTML=(st.m==='pt'?'<div class="gah0" aria-hidden="true"></div><div class="gah" aria-hidden="true"><span>Г</span><i></i><span>П</span></div>':'')+L.slice(0,st.lim).map((x,i)=>{const p=x.p,h=x.h,pc=Math.round(100*h[0]/h[1]),c=(TM[p.t]||[])[1]||'#334';
   const L10=p.log.slice(-10),mx=Math.max(st.m==='s3'?4:2,...L10.map(M.v)),hit=a=>a.filter(M.f).length,L5=L10.slice(-5);
   const strip=`<div class="bars">${L10.map(r=>{const ok=M.f(r),v=M.v(r);return `<i class="${ok?'g':''}" style="--h:${Math.max(.08,v/mx)}" title="${esc(r[0].slice(8,10)+'.'+r[0].slice(5,7)+' '+(r[3]?'дома, ':'в гостях, ')+tn(r[2]))}: ${r[4]}+${r[5]}${r[6]!=null?', бросков '+r[6]:''}"><b>${v}</b></i>`}).join('')}</div><small>5 матчей: <b>${hit(L5)}/${L5.length}</b> · 10: <b>${hit(L10)}/${L10.length}</b></small>`;
   const sp=a=>{const lg=p.log.filter(r=>r[3]===a);return`${lg.filter(M.f).length}/${lg.length}`};
   const nx=D.next[p.t];
   const jk=JY?JY.key(LG,p.t):'',jv=JY&&JY.vars(jk),lt=jv&&JY.calc(jk).lt;
   return `<article class="pr${jv?' k'+(lt?' lt':'')+(i<3?' t'+(i+1):''):''}" role="listitem"${jv?` style="${jv}"`:''}>${jv?`<img class="wm" src="${em(p.t)}" alt="" aria-hidden="true" loading="lazy" onerror="this.remove()">${p.no!=null?`<span class="no" aria-hidden="true">${esc(p.no)}</span>`:''}`:''}<span class="rk">${i+1}</span>
    <div class="av" style="--c:${c}">${p.img?`<img class="ph" src="${esc(JV_KPH(p.img))}" alt="" loading="lazy" onerror="this.remove()">`:''}<img class="bd" src="${em(p.t)}" alt="" loading="lazy" onerror="this.remove()"></div>
    <div class="nm"><b>${p.id!=null?`<a href="player.html?lg=${LG}&id=${p.id}" title="Профиль игрока">${esc(p.n)}</a>`:esc(p.n)}</b><span>${esc(tn(p.t))} · ${p.pos==='D'?'защитник':'нападающий'}</span></div>
    ${st.m==='pt'?`<div class="pts pin" aria-hidden="true"><b>${p.G}+${p.A}</b></div>`:''}<div class="tot" aria-label="${st.m==='g'?'голов':st.m==='a'?'передач':'очков'}: ${tot(p)}">${tot(p)}</div>
    ${p.img?`<img class="cut" src="${esc(JV_KPH(p.img))}" alt="" aria-hidden="true" loading="lazy" onerror="this.remove()">`:''}
   </article>${st.m==='pt'?`<div class="ga${jv?' k':''}"${jv?` style="${jv}"`:''} aria-label="${p.G} голов и ${p.A} передач"><span>${p.G}</span><i>+</i><span>${p.A}</span></div>`:''}`}).join('');
  $('list').classList.toggle('two',st.m==='pt');
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
