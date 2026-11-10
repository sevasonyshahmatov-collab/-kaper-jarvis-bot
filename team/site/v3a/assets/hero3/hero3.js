/* Пробный первый экран «афиша матча» (владелец 10.11): ?hero=2 включает, ?hero=off возвращает обычный; выбор помнится в sessionStorage.
   Матч — в центре: хозяева слева, гости справа, расчёт модели между ними. Фон — мягкое свечение в цветах команд (teams-lite.js),
   меняется вместе с матчем. Только оформление: данные и карточку рисует прежний код страницы. */
(function(){
  var d=document.documentElement,K='jv-hero',q='',on=false;
  try{q=new URLSearchParams(location.search).get('hero')||''}catch(e){}
  try{if(q==='2')sessionStorage.setItem(K,'2');else if(q==='off'||q==='1')sessionStorage.removeItem(K);on=sessionStorage.getItem(K)==='2'}catch(e){on=q==='2'}
  if(q==='off'||q==='1')on=false;
  if(!on)return;
  d.dataset.hero='2';
  var s=document.currentScript,css=document.createElement('link');css.rel='stylesheet';css.href=s.src.replace(/hero3\.js.*$/,'hero3.css');document.head.appendChild(css);
  document.addEventListener('DOMContentLoaded',function(){
    var hero=document.querySelector('.hero'),card=document.getElementById('mcard');if(!hero||!card)return;
    var bg=document.createElement('div');bg.className='h3bg';bg.setAttribute('aria-hidden','true');bg.innerHTML='<i></i>';hero.prepend(bg);
    var T=(window.JV_TEAMS&&window.JV_TEAMS.teams)||{};
    function col(img,fb){var m=img&&/\/em\/([^/.]+)\./.exec(img.getAttribute('src')||''),t=m&&T[m[1]],c=t&&t.colors&&t.colors[0];return c||fb}
    function paint(){var e=card.querySelectorAll('.face .tm .em');if(e.length<2)return;hero.style.setProperty('--ha',col(e[0],'#1653d6'));hero.style.setProperty('--aa',col(e[1],'#3ee0ff'))}
    paint();new MutationObserver(paint).observe(card,{childList:true});
    var b=document.createElement('div');b.className='h3bar';b.setAttribute('role','group');b.setAttribute('aria-label','Вариант первого экрана');
    b.innerHTML='<button type="button" data-h="2" aria-pressed="true">Афиша матча</button><button type="button" data-h="off" aria-pressed="false">Как было</button>';
    b.addEventListener('click',function(e){var k=e.target.getAttribute&&e.target.getAttribute('data-h');if(!k)return;var u=new URL(location.href);u.searchParams.set('hero',k);location.href=u.toString()});
    document.body.appendChild(b);
  });
})();
