/* Первый экран «афиша матча» (владелец 10.11) — основной вид; ?hero=off возвращает прежний (две колонки), ?hero=2 — обратно. Выбор помнится в sessionStorage.
   Матч в центре: хозяева слева, гости справа, расчёт модели между ними; под карточкой — два следующих матча и строка «что это за сайт».
   Работает на хоккее и футболе. Фон — мягкое свечение в цветах команд (teams-lite.js / football-lite.js), меняется вместе с матчем. Только оформление: карточку и данные рисует код страницы,
   список матчей табло страница отдаёт в window.__heroPicks. Стили — hero3.css (подключён в <head>, работает только при data-hero="2"). */
(function(){
  var d=document.documentElement,K='jv-hero',q='',off=false;
  try{q=new URLSearchParams(location.search).get('hero')||''}catch(e){}
  try{if(q==='off')sessionStorage.setItem(K,'off');else if(q==='2')sessionStorage.removeItem(K);off=sessionStorage.getItem(K)==='off'}catch(e){off=q==='off'}
  if(q==='2')off=false;
  function bar(){var b=document.createElement('div');b.className='h3bar';b.setAttribute('role','group');b.setAttribute('aria-label','Вариант первого экрана');
    b.innerHTML='<button type="button" data-h="2" aria-pressed="false">Афиша матча</button><button type="button" data-h="off" aria-pressed="true">Как было</button>';
    b.addEventListener('click',function(e){var k=e.target.getAttribute&&e.target.getAttribute('data-h');if(!k)return;var u=new URL(location.href);u.searchParams.set('hero',k);location.href=u.toString()});
    document.body.appendChild(b)}
  if(off){document.addEventListener('DOMContentLoaded',bar);return}
  d.dataset.hero='2';
  var esc=function(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})};
  /* цвет свечения: основной цвет клуба; если он серый или почти чёрный — самый насыщенный из остальных, иначе спокойный запасной */
    function vivid(cs,fb){var best=null,bs=0;(cs||[]).forEach(function(h,idx){var m=/^#?([0-9a-f]{6})$/i.exec(h||'');if(!m)return;var n=parseInt(m[1],16),r=n>>16&255,g=n>>8&255,b=n&255,mx=Math.max(r,g,b),mn=Math.min(r,g,b),s=mx?(mx-mn)/mx:0,sc=s*(mx/255);if(idx===0&&sc>.22){best='#'+m[1];bs=9}else if(sc>bs){bs=sc;best='#'+m[1]}});return bs>.22?best:fb}
  document.addEventListener('DOMContentLoaded',function(){
    var hero=document.querySelector('.hero'),card=document.getElementById('mcard'),pager=document.getElementById('pager'),bcol=hero&&hero.querySelector('.bcol'),board=document.getElementById('board');
    if(!hero||!card||!bcol||!board)return;
    var bg=document.createElement('div');bg.className='h3bg';bg.setAttribute('aria-hidden','true');bg.innerHTML='<i></i><img class="h3g h" alt=""><img class="h3g a" alt="">';hero.prepend(bg);
    /* эмблемы-«голограммы» по краям (владелец 12.11): хозяева слева, гости справа, уходят за край экрана; меняются вместе с матчем */
    var G=bg.querySelectorAll('.h3g');
    function ghost(g,img){var src=img&&img.getAttribute('src');if(!src){g.classList.remove('on');return}if(g.getAttribute('src')===src){g.classList.add('on');return}
      g.classList.remove('on');var t=new Image();t.onload=function(){setTimeout(function(){g.src=src;g.classList.add('on')},g.getAttribute('src')?260:0)};t.onerror=function(){g.removeAttribute('src')};t.src=src}
    var FB=d.dataset.sport==='football',T=FB?((window.JV_FOOT&&window.JV_FOOT.teams)||{}):((window.JV_TEAMS&&window.JV_TEAMS.teams)||{});
    var DIR=FB?'fc':'em',RE=FB?/\/fc\/([^/]+)\.webp/:/\/em\/([^/.]+)\./,FALL=FB?['#1f9d5b','#2aa3a3']:['#3b6fd8','#36b8d6'];
    function col(img,fb){var m=img&&RE.exec(img.getAttribute('src')||''),id=m&&m[1],t;try{id=id&&decodeURIComponent(id)}catch(e){}t=id&&T[id];return vivid(t&&(FB?t.c:t.colors),fb)}
    /* два следующих матча */
    var P=window.__heroPicks||[],next=document.createElement('div');next.className='h3next';board.after(next);
    var k2=function(v){return (Math.round(v*100)/100).toFixed(2).replace('.',',')};
    function plate(m,i){var md=m.md,ln=m.ln,pick='';
      if(m.pick)pick='<span class="h3k"><small>Расчёт модели</small><b>'+esc(m.pick)+(m.k?' · '+k2(m.k):'')+'</b></span>';
      else if(md){var mo=[md.p1,md.x,md.p2],j=mo.indexOf(Math.max.apply(null,mo)),w=j===0?m.hn+' — победа':j===2?m.an+' — победа':'Ничья',kk=ln?[ln.p1,ln.x,ln.p2][j]:null;pick='<span class="h3k"><small>Расчёт модели</small><b>'+esc(w)+(kk?' · '+k2(kk):'')+'</b></span>'}
      var em=function(s){return '<img src="../assets/'+DIR+'/'+encodeURIComponent(s)+'.webp" alt="" width="28" height="28" loading="lazy">'};
      return '<button type="button" class="h3p" data-i="'+i+'"><time>'+esc(m.t.slice(11))+'</time><span class="h3t">'+em(m.h)+esc(m.hn)+'</span><span class="h3t">'+em(m.a)+esc(m.an)+'</span>'+pick+'</button>'}
    function cur(){var bs=pager?[].slice.call(pager.children):[];for(var i=0;i<bs.length;i++)if(bs[i].getAttribute('aria-pressed')==='true')return i;return 0}
    function nextUp(){if(P.length<2){next.hidden=true;return}var c=cur(),n=Math.min(2,P.length-1),h='';for(var s=1;s<=n;s++){var i=(c+s)%P.length;h+=plate(P[i],i)}next.innerHTML=h}
    next.addEventListener('click',function(e){var b=e.target.closest('.h3p');if(!b||!pager)return;var t=pager.children[+b.dataset.i];if(t)t.click()});
    function paint(){var e=card.querySelectorAll('.face .tm .em');if(e.length>1){hero.style.setProperty('--ha',col(e[0],FALL[0]));hero.style.setProperty('--aa',col(e[1],FALL[1]));ghost(G[0],e[0]);ghost(G[1],e[1])}nextUp()}
    paint();new MutationObserver(paint).observe(card,{childList:true});
    /* строка «что это за сайт» под кнопкой */
    var n=(document.getElementById('fN')||{}).textContent||'',nl=(document.getElementById('fNl')||{}).textContent||'';
    var st=document.createElement('p');st.className='h3strip';
    st.innerHTML=FB?'<span>Топ-лиги Европы, РПЛ и еврокубки</span><span>расчёт модели на каждый матч</span><a href="#matches">Ближайшие матчи ↓</a>'
      :(n&&nl?'<span><b>'+esc(n)+'</b> '+esc(nl)+'</span>':'')+'<span>КХЛ и НХЛ</span><span>расчёт модели на каждый матч</span><a href="#matches">Все матчи дня ↓</a>';
    bcol.appendChild(st);
  });
})();
