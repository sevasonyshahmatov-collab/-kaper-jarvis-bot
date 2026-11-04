/* JARVIS v3a — общая шапка для всех страниц. Подключается ПЕРЕД v3a.js.
   Рисует: логотип, переключатель Хоккей/Футбол, разделы вида спорта, Telegram, кнопку «Меню» (телефон).
   Меню-якоря страницы (.nav внутри <header id="hd">) переносит во вторую полосу под шапкой.
   Вид спорта и раздел берёт из <html data-sport> и адреса страницы. */
(()=>{
const hd=document.getElementById('hd');if(!hd)return;
const SRC=(document.currentScript&&document.currentScript.src)||new URL('assets/nav.js',location.href).href;
const U=p=>new URL('../'+p,SRC).href;
const path=location.pathname.replace(/\/+$/,''),file=path.split('/').pop()||'index.html';
const dir=path.split('/').slice(-2,-1)[0]||'';
const q=new URLSearchParams(location.search);
const sport=document.documentElement.dataset.sport||'';

const SECTIONS={
 hockey:[['m','Матчи','hockey/index.html'],['khl','КХЛ','hockey/league.html?lg=khl'],['nhl','НХЛ','hockey/league.html?lg=nhl'],
         ['pl','Игроки','hockey/players.html'],['tr','Тренды','hockey/trends.html'],['mod','Модель','hockey/index.html#model']],
 football:[['m','Матчи','football/index.html'],['lg','Лиги','football/league.html?lg=epl'],['ucl','Лига чемпионов','football/ucl.html'],
         /* ['pl','Игроки','football/players.html'], — скрыто до готовности портретов (владелец 04.11) */['tr','Тренды','football/trends.html'],['mod','Модель','index.html#model']]
};
/* какой пункт активен */
function active(){
  if(!sport)return '';
  if(dir==='team'){const id=q.get('id')||'',T=window.JV_TEAMS&&JV_TEAMS.teams&&JV_TEAMS.teams[id];
    return T&&T.lg==='nhl'||/^nhl_/.test(id)?'nhl':'khl'}
  if(file==='team.html')return 'lg';
  if(file==='index.html')return 'm';
  if(file==='ucl.html')return 'ucl';
  if(file==='league.html'){const l=q.get('lg')||'';return sport==='hockey'?(l==='nhl'?'nhl':'khl'):(l==='ucl'?'ucl':'lg')}
  if(/^players/.test(file)||file==='photo-credits.html')return 'pl';
  if(file==='trends.html')return 'tr';
  return '';
}
const act=active();
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const home=(file==='index.html'&&!sport&&dir!=='hockey'&&dir!=='football');
const link=(s,cur)=>`<a href="${esc(U(s[2]))}"${cur===s[0]?' aria-current="page"':''}>${esc(s[1])}</a>`;
const TG='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 3.2 2.9 10.4c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.7c.3-1.3-.5-1.9-1.4-1.5ZM8.3 13.2l9.6-6c.5-.3.9-.1.5.2l-8.2 7.4-.3 3.4-1.6-5Z"/></svg>';

/* page-local меню-якоря: забираем до перерисовки */
const local=hd.querySelector('.nav');
if(local)local.remove();

const sec=SECTIONS[sport]||null;
const panel=(sec?[sec]:[SECTIONS.hockey,SECTIONS.football]).map((list,i)=>{
  const name=sec?'':(i?'Футбол':'Хоккей');
  return `<div class="mgrp">${name?`<b>${name}</b>`:''}${list.map(s=>link(s,sec?act:'')).join('')}</div>`}).join('');

hd.innerHTML=`<div class="wrap hdrow">
  <a class="logo" href="${esc(U('index.html'))}" aria-label="JARVIS, на главную">JAR<i>V</i>IS</a>
  <nav class="seg" aria-label="Вид спорта">
    <a href="${esc(U('hockey/index.html'))}"${sport==='hockey'?' aria-current="true"':''}>Хоккей</a>
    <a href="${esc(U('football/index.html'))}"${sport==='football'?' aria-current="true"':''}>Футбол</a>
  </nav>
  ${sec?`<nav class="gnav" aria-label="Разделы сайта">${sec.map(s=>link(s,act)).join('')}</nav>`:'<span class="gnav-sp"></span>'}
  <a class="btn btn-tg" href="https://t.me/jarvibet" target="_blank" rel="noopener" aria-label="Telegram @jarvibet">${TG}<span>Telegram</span></a>
  <button type="button" class="mbtn" id="mbtn" aria-expanded="false" aria-controls="mpanel"><span class="mi" aria-hidden="true"></span><span class="mt">Меню</span></button>
</div>
<div class="mpanel" id="mpanel" hidden>${panel}<a class="mtg" href="https://t.me/jarvibet" target="_blank" rel="noopener">${TG}<span>Telegram @jarvibet</span></a></div>`;

/* вторая полоса — якоря страницы */
let sub=null;
if(local){
  sub=document.createElement('div');sub.className='subbar';
  const w=document.createElement('div');w.className='wrap';
  local.setAttribute('aria-label','Разделы страницы');w.appendChild(local);sub.appendChild(w);hd.appendChild(sub);
  /* ссылки на скрытые/отсутствующие блоки не показываем */
  const refresh=()=>{let n=0;local.querySelectorAll('a[href^="#"]').forEach(a=>{const t=document.getElementById(a.getAttribute('href').slice(1));
    const ok=!!t&&!t.hidden;a.hidden=!ok;if(ok)n++});sub.hidden=!n};
  let tm=0;const sched=()=>{clearTimeout(tm);tm=setTimeout(refresh,60)};
  /* подсвеченный при прокрутке пункт держим в видимой части полосы (на телефоне она листается вбок) */
  if('MutationObserver' in window)new MutationObserver(ms=>{for(const m of ms){const a=m.target;if(a.classList&&a.classList.contains('on')&&local.scrollWidth>local.clientWidth){
    local.scrollTo({left:Math.max(0,a.offsetLeft-(local.clientWidth-a.offsetWidth)/2),behavior:'auto'});break}}}).observe(local,{subtree:true,attributes:true,attributeFilter:['class']});
  refresh();document.addEventListener('DOMContentLoaded',refresh);addEventListener('load',refresh);
  if('MutationObserver' in window)new MutationObserver(sched).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['hidden']});
}

/* меню на телефоне */
const btn=document.getElementById('mbtn'),pn=document.getElementById('mpanel');
const setOpen=o=>{pn.hidden=!o;btn.setAttribute('aria-expanded',o?'true':'false');hd.classList.toggle('menu-open',o);btn.querySelector('.mt').textContent=o?'Закрыть':'Меню'};
btn.addEventListener('click',e=>{e.stopPropagation();setOpen(pn.hidden)});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!pn.hidden){setOpen(false);btn.focus()}});
document.addEventListener('click',e=>{if(!pn.hidden&&!pn.contains(e.target))setOpen(false)});
addEventListener('resize',()=>{if(innerWidth>1100&&!pn.hidden)setOpen(false)});

/* страницы без v3a.js: тень шапки при прокрутке */
if(!window.JV){const on=()=>hd.classList.toggle('stuck',scrollY>8);addEventListener('scroll',on,{passive:true});on()}
/* активная вкладка подменю — в видимую часть */
addEventListener('load',()=>{const a=hd.querySelector('.subbar a.on');if(a&&a.scrollIntoView)try{a.scrollIntoView({block:'nearest',inline:'center'})}catch(e){}});
})();
