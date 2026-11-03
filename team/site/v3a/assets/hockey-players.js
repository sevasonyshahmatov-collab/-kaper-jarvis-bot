/* Раздел «Игроки НХЛ» (прототип 03.11): данные — hockey/data/nhl_players.json (сборщик nhl_players_fetch.py, Actions).
   Рынки «n из N» по своим матчам игрока: очко, гол, передача, 3+ броска; форма 10, TOI, дом/выезд, следующий соперник. */
(()=>{
const TM={"CAR":["Каролина","#cc0000"],"EDM":["Эдмонтон","#ff4c00"],"BOS":["Бостон","#ffb81c"],"MTL":["Монреаль","#af1e2d"],"VGK":["Вегас","#b4975a"],"OTT":["Оттава","#c8102e"],"TBL":["Тампа-Бэй","#123e8c"],"NJD":["Нью-Джерси","#ce1126"],"FLA":["Флорида","#c8102e"],"UTA":["Юта","#71afe5"],"TOR":["Торонто","#103c8c"],"COL":["Колорадо","#822d48"],"SEA":["Сиэтл","#006080"],"BUF":["Баффало","#003087"],"WSH":["Вашингтон","#c8102e"],"NYI":["Айлендерс","#00539b"],"STL":["Сент-Луис","#002f87"],"DET":["Детройт","#ce1126"],"NSH":["Нэшвилл","#ffb81c"],"NYR":["Рейнджерс","#0038a8"],"SJS":["Сан-Хосе","#006d75"],"ANA":["Анахайм","#f47a38"],"CGY":["Калгари","#d2001c"],"PIT":["Питтсбург","#fcb514"],"PHI":["Филадельфия","#f74902"],"WPG":["Виннипег","#16386e"],"CBJ":["Коламбус","#143c82"],"LAK":["Лос-Анджелес","#828c91"],"CHI":["Чикаго","#cf0a2c"],"VAN":["Ванкувер","#003e82"],"DAL":["Даллас","#006847"],"MIN":["Миннесота","#154734"]};
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const em=ab=>`../assets/em/nhl_${ab.toLowerCase()}.webp`;
const ini=n=>n.split(/\s+/).filter(Boolean).map(w=>w[0]).slice(0,2).join('').toUpperCase();
const tn=ab=>(TM[ab]||[ab])[0];
const MK={pt:{f:r=>r[4]+r[5]>0,v:r=>r[4]+r[5],w:'набирал очко'},g:{f:r=>r[4]>0,v:r=>r[4],w:'забивал'},a:{f:r=>r[5]>0,v:r=>r[5],w:'отдавал передачу'},s3:{f:r=>r[6]>=3,v:r=>r[6],w:'бросал 3+ раза в створ'}};
const POS={'':'Все',F:'Нападающие',D:'Защитники'};
const st={m:'pt',pos:'',tm:'',ha:'',so:'rate',q:'',lim:30};
const mmss=s=>`${Math.floor(s/60)}:${String(Math.round(s%60)).padStart(2,'0')}`;
const pl=(n,a,b,c)=>{n=Math.abs(n)%100;const k=n%10;return n>10&&n<20?c:k===1?a:k>1&&k<5?b:c};
fetch('data/nhl_players.json').then(r=>r.json()).then(D=>{
 $('season').textContent=D.season;
 $('lg').innerHTML=Object.entries(POS).map(([k,v])=>`<button type="button" data-l="${k}" aria-pressed="${!k}">${v}</button>`).join('');
 $('tm').innerHTML='<option value="">Все</option>'+Object.keys(TM).sort((a,b)=>tn(a).localeCompare(tn(b),'ru')).map(a=>`<option value="${a}">${esc(tn(a))}</option>`).join('');
 const P=D.players.map(p=>{const L=p.log,n=L.length;return{...p,gp:n,G:L.reduce((s,r)=>s+r[4],0),A:L.reduce((s,r)=>s+r[5],0),S:L.reduce((s,r)=>s+r[6],0),toi:n?L.reduce((s,r)=>s+r[7],0)/n:0}});
 function render(){
  const M=MK[st.m],q=st.q.trim().toLowerCase();
  let L=P.filter(p=>(!st.pos||(st.pos==='D'?p.pos==='D':p.pos!=='D'))&&(!st.tm||p.t===st.tm)&&(!q||p.n.toLowerCase().includes(q)));
  L=L.map(p=>{const lg=st.ha?p.log.filter(r=>r[3]===(st.ha==='home'?1:0)):p.log;return{p,h:[lg.filter(M.f).length,lg.length]}}).filter(x=>x.h[0]>0&&x.h[1]>=(st.ha?3:5));
  const tot=p=>st.m==='g'?p.G:st.m==='a'?p.A:st.m==='s3'?p.S:p.G+p.A;
  const val=x=>st.so==='n'?x.h[0]:st.so==='G'?tot(x.p):st.so==='toi'?x.p.toi:x.h[0]/x.h[1];
  L.sort((a,b)=>val(b)-val(a)||b.h[0]-a.h[0]||a.p.n.localeCompare(b.p.n));
  $('meta').textContent=`${L.length} ${pl(L.length,'игрок','игрока','игроков')} · ${M.w} хотя бы в одном матче${st.ha==='home'?' дома':st.ha==='away'?' в гостях':''} · данные на ${D.built}`;
  $('list').innerHTML=L.slice(0,st.lim).map((x,i)=>{const p=x.p,h=x.h,pc=Math.round(100*h[0]/h[1]),c=(TM[p.t]||[])[1]||'#334';
   const strip=p.log.slice(-10).map(r=>{const ok=M.f(r);return `<i class="${ok?'g':''}" title="${esc(r[0].slice(8,10)+'.'+r[0].slice(5,7)+' '+(r[3]?'— ':'@ ')+tn(r[2]))}: ${r[4]}+${r[5]}, бросков ${r[6]}">${M.v(r)}</i>`}).join('');
   const sp=a=>{const lg=p.log.filter(r=>r[3]===a);return`${lg.filter(M.f).length}/${lg.length}`};
   const nx=D.next[p.t];
   return `<article class="pr" role="listitem"><span class="rk">${i+1}</span>
    <div class="av" style="--c:${c}"><span>${esc(ini(p.n))}</span>${p.img?`<img class="ph" src="${esc(p.img)}" alt="" loading="lazy" onerror="this.remove()">`:''}<img class="bd" src="${em(p.t)}" alt="" loading="lazy" onerror="this.remove()"></div>
    <div class="nm"><b>${esc(p.n)}</b><span>${esc(tn(p.t))} · ${p.pos==='D'?'защ.':'нап.'}${p.no?' · №'+p.no:''} · ${p.G}+${p.A}=${p.G+p.A}, бросков ${p.S} · ${mmss(p.toi)} за игру</span></div>
    <div class="hit" aria-label="${h[0]} из ${h[1]} матчей"><b>${h[0]}<small>из ${h[1]}</small></b><div class="bar"><i style="width:${pc}%"></i></div></div>
    <div class="strip" aria-label="Последние 10 матчей">${strip}</div>
    <div class="ha">Дома <b>${sp(1)}</b> · В гостях <b>${sp(0)}</b></div>
    <div class="nx">${nx?`<img src="${em(nx.o)}" alt="" loading="lazy" onerror="this.remove()"><span>Далее: <b>${esc(tn(nx.o))}</b><br>${nx.h?'дома':'в гостях'}, ${nx.d.slice(8,10)}.${nx.d.slice(5,7)}</span>`:''}</div>
   </article>`}).join('');
  $('more').hidden=L.length<=st.lim}
 $('mk').onclick=e=>{const b=e.target.closest('button');if(!b)return;st.m=b.dataset.m;st.lim=30;$('mk').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));render()};
 $('lg').onclick=e=>{const b=e.target.closest('button');if(!b)return;st.pos=b.dataset.l;st.lim=30;$('lg').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));render()};
 $('tm').onchange=e=>{st.tm=e.target.value;st.lim=30;render()};
 $('ha').onchange=e=>{st.ha=e.target.value;render()};
 $('so').onchange=e=>{st.so=e.target.value;render()};
 $('q').oninput=e=>{st.q=e.target.value;st.lim=30;render()};
 $('more').onclick=()=>{st.lim+=30;render()};
 render();
}).catch(()=>{$('meta').textContent='Данные игроков ещё не собраны.'});
})();
