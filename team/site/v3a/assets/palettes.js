/* Цвета сайта. Основной вид — «роли цветов» (владелец 10.11), правила в конце v3a.css, работает без параметров.
   ?col=off — прежний вид, ?col=1|2 — пробные варианты (assets/col.css), ?col=3 — вернуться к основному.
   Выбор помнится в sessionStorage. Плашка-переключатель внизу видна, только пока включён не основной вид. */
(function(){
  var d=document.documentElement,K='jv-col',V=['1','2','off'],q='',c='';
  try{q=new URLSearchParams(location.search).get('col')||''}catch(e){}
  try{if(q==='3')sessionStorage.removeItem(K);else if(V.indexOf(q)>-1)sessionStorage.setItem(K,q);c=sessionStorage.getItem(K)||''}catch(e){c=V.indexOf(q)>-1?q:''}
  if(q==='3')c='';
  if(V.indexOf(c)<0)return;
  d.dataset.col=c;
  if(c==='2'){d.dataset.themeWas=d.dataset.theme||'';d.dataset.theme='a';var m=document.querySelector('meta[name=theme-color]');if(m)m.content='#0a1220'}
  var s=document.currentScript,base=s.src.replace(/palettes\.js.*$/,'');
  var css=document.createElement('link');css.rel='stylesheet';css.href=base+'col.css';document.head.appendChild(css);
  document.addEventListener('DOMContentLoaded',function(){
    var b=document.createElement('div');b.className='col-bar';b.setAttribute('role','group');b.setAttribute('aria-label','Вариант цветов');
    b.innerHTML=[['3','Основной'],['1','1 · Текущий'],['2','2 · Как главная'],['off','Было']].map(function(x){return '<button type="button" data-c="'+x[0]+'" aria-pressed="'+(x[0]===c)+'">'+x[1]+'</button>'}).join('');
    b.addEventListener('click',function(e){var k=e.target.getAttribute&&e.target.getAttribute('data-c');if(!k)return;var u=new URL(location.href);u.searchParams.set('col',k);location.href=u.toString()});
    document.body.appendChild(b);
  });
})();
/* Пробные палитры 60/30/10: ?pal=stadium|ice|volt|royal включает, ?pal=off сбрасывает; без параметра сайт как раньше.
   Выбор помнится в sessionStorage до закрытия вкладки. Плашка-переключатель видна только при включённой палитре. */
(function(){
  if(document.documentElement.classList.contains("efir"))return; /* тема «Эфир» включена: старый переключатель палитр не нужен */
  var d=document.documentElement,K='jv-pal',L=['stadium','ice','volt','royal'],N={stadium:'Стадион',ice:'Лёд и огонь',volt:'Вольт',royal:'Королевский'};
  var p='',q='';
  try{q=new URLSearchParams(location.search).get('pal')||''}catch(e){}
  try{
    if(q==='off')sessionStorage.removeItem(K);else if(L.indexOf(q)>-1)sessionStorage.setItem(K,q);
    p=sessionStorage.getItem(K)||''
  }catch(e){p=L.indexOf(q)>-1?q:''}
  if(q==='off')p='';
  if(L.indexOf(p)<0)return;
  d.dataset.pal=p;
  var s=document.currentScript,base=s.src.replace(/palettes\.js.*$/,'');
  ['palettes.css','pal/common.css','pal/hockey.css','pal/football.css','pal/energy.css'].forEach(function(f){
    var css=document.createElement('link');css.rel='stylesheet';css.href=base+f;document.head.appendChild(css);
    if(f==='palettes.css')css.addEventListener('load',function(){try{var v=getComputedStyle(d).getPropertyValue('--paper').trim(),m=document.querySelector('meta[name=theme-color]');if(v&&m)m.content=v}catch(e){}})
  });
  document.addEventListener('DOMContentLoaded',function(){
    var b=document.createElement('div');b.className='pal-bar';b.setAttribute('role','group');b.setAttribute('aria-label','Палитра');
    var h='';
    L.concat('off').forEach(function(k){h+='<button type="button" data-p="'+k+'" aria-pressed="'+(k===p)+'">'+(k==='off'?'Было':N[k])+'</button>'});
    b.innerHTML=h;
    b.addEventListener('click',function(e){
      var k=e.target.getAttribute&&e.target.getAttribute('data-p');if(!k)return;
      var u=new URL(location.href);u.searchParams.set('pal',k);location.href=u.toString()
    });
    document.body.appendChild(b);
  });
})();
