/* JARVIS v3a — «Что дальше» в конце страницы (задание 14.11, п. 8): один понятный следующий шаг вместо голого подвала.
   Ближайший матч (того же вида спорта и лиги, если она открыта) → «Матчи дня»; и «Прогноз на сегодня».
   Подключает footer.js на страницах лиг, трендов, игроков, клубов, итогов. Данные — data/today.js (грузится сам, если его нет). */
(()=>{
const SRC=(document.currentScript&&document.currentScript.src)||new URL('assets/next.js',location.href).href;
const U=p=>new URL('../'+p,SRC).href;
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const sport=document.documentElement.dataset.sport||'';
const lgq=new URLSearchParams(location.search).get('lg')||(location.pathname.match(/\/(khl|nhl|epl|laliga|seriea|bundesliga|ligue1|rpl|ucl|uel)\//)||[])[1]||'';
const LG={khl:'КХЛ',nhl:'НХЛ',epl:'АПЛ',laliga:'Ла Лига',seriea:'Серия А',bundesliga:'Бундеслига',ligue1:'Лига 1',rpl:'РПЛ',ucl:'Лига чемпионов',uel:'Лига Европы'};
const isH=lg=>lg==='khl'||lg==='nhl';
const fc=sport==='hockey'?(lgq==='nhl'?'hockey/forecast-nhl.html':'hockey/forecast-khl.html'):sport==='football'?'football/forecast-'+(LG[lgq]&&!isH(lgq)&&lgq!=='ucl'&&lgq!=='uel'?lgq:'epl')+'.html':'forecast.html';
function draw(){
 const T=window.JV_TODAY||{},now=Date.now(),at=t=>Date.parse(String(t).replace(' ','T')+':00+03:00');
 let L=(T.matches||[]).filter(m=>at(m.t)>now-15*60e3).sort((a,b)=>a.t<b.t?-1:1);
 if(sport)L=L.filter(m=>sport==='hockey'?isH(m.lg):!isH(m.lg));
 const inLg=lgq?L.filter(m=>m.lg===lgq):[];const m=(inLg.length?inLg:L)[0];
 const MSK=new Date(now+3*36e5).toISOString().slice(0,10),tm=new Date(now+27*36e5).toISOString().slice(0,10);
 const when=m?(m.t.slice(0,10)===MSK?'сегодня':m.t.slice(0,10)===tm?'завтра':+m.t.slice(8,10)+'.'+m.t.slice(5,7))+', '+m.t.slice(11,16)+' МСК':'';
 const s=document.createElement('section');s.className='nxs';s.setAttribute('aria-labelledby','nxs-h');
 s.innerHTML=`<div class="wrap"><h2 id="nxs-h">Что дальше</h2><div class="nxs-g">
  ${m?`<a class="nxs-m" href="${esc(U('matches.html'+(sport?'?s='+(sport==='hockey'?'h':'f'):'')))}"><small>Ближайший матч · ${esc(LG[m.lg]||'')}</small><b>${esc(m.hn)} — ${esc(m.an)}</b><span>${esc(when)} · расчёт модели →</span></a>`:''}
  <a class="nxs-f" href="${esc(U(fc))}"><small>Списком</small><b>Прогноз на сегодня</b><span>все матчи дня с выводом модели →</span></a></div></div>`;
 const f=document.querySelector('footer.jvf')||document.querySelector('footer');(f&&f.parentNode?f.parentNode.insertBefore(s,f):document.body.appendChild(s))}
try{const l=document.createElement('link');l.rel='stylesheet';l.href=new URL('next.css',SRC).href;document.head.appendChild(l)}catch(e){}
const go=()=>{if(window.JV_TODAY)return draw();const sc=document.createElement('script');sc.src=U('data/today.js');sc.onload=sc.onerror=draw;document.head.appendChild(sc)};
document.readyState==='loading'?document.addEventListener('DOMContentLoaded',go):go();
})();
