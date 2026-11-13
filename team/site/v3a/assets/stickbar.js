/* Полоса при прокрутке (владелец 12.11, по образцу nhl.com) — чтобы не терять, чья это страница.
   Матч (любая лига): под шапкой сайта остаются эмблемы, названия, время или счёт и переходы к разделам — когда баннер ушёл вверх.
   Клуб (team/index.html): во вторую полосу шапки (якоря страницы) слева добавляется эмблема, название, место и очки.
   Подключает assets/nav.js; стили — конец assets/nav.css. */
(()=>{
const hd=document.getElementById('hd');if(!hd)return;
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const watch=(el,cb)=>{if(!('IntersectionObserver'in window))return;
 new IntersectionObserver(([e])=>cb(!e.isIntersecting&&e.boundingClientRect.top<0),{rootMargin:`-${hd.offsetHeight+6}px 0px 0px 0px`}).observe(el)};

/* ── матч ── */
const mh=document.querySelector('main>.mx-hero');
if(mh){
 const field=mh.querySelector('.mx-field')||mh,tm=[...mh.querySelectorAll('.mx-team')];if(tm.length<2)return;
 const side=(a,c)=>{const im=a.querySelector('img'),n=(a.querySelector('b')||{}).textContent||'';
  return `<a class="mb-t ${c}" href="${esc(a.getAttribute('href')||'#')}" tabindex="-1">${im?`<img src="${esc(im.getAttribute('src'))}" alt="">`:''}<b>${esc(n)}</b></a>`};
 const bar=document.createElement('div');bar.className='mbar';bar.setAttribute('aria-hidden','true');
 ['--hc','--ac'].forEach(k=>{const v=mh.style.getPropertyValue(k);if(v)bar.style.setProperty(k,v)});
 const links=[['mt-md','Расчёт'],['mt-form','Форма'],['mt-cmp','Сравнение'],['mt-h2h','Личные встречи'],['mt-tbl','Таблица']];
 bar.innerHTML=`<div class="wrap">${side(tm[0],'h')}<span class="mb-mid"><b></b><small></small></span>${side(tm[1],'a')}<nav></nav></div>`;
 document.body.appendChild(bar);
 const mid=bar.querySelector('.mb-mid b'),sm=bar.querySelector('.mb-mid small'),nav=bar.querySelector('nav');
 const fill=()=>{
  /* идёт или сыгран — счёт из живого блока или баннера, иначе время начала */
  const sc=mh.querySelector('.lv-sc,.mx-score'),t=mh.querySelector('.mx-time'),w=mh.querySelector('.mx-when');
  mid.textContent=((sc&&sc.textContent.trim())||(t&&t.textContent.trim())||'—').replace(/\s+/g,' ').slice(0,12);
  sm.textContent=w?w.textContent.split('·')[0].split(',')[0].trim():'';
  nav.innerHTML=links.filter(([id])=>document.getElementById(id)).map(([id,n])=>`<a href="#${id}" tabindex="-1">${n}</a>`).join('');
  bar.style.setProperty('--hdh',hd.offsetHeight+'px')};
 watch(field,on=>{if(on)fill();bar.classList.toggle('on',on)});
 return;
}

/* ── клуб ── */
if(!/\/team\/(index\.html)?$/.test(location.pathname))return;
let n=0;const wait=setInterval(()=>{
 const hero=document.querySelector('#hero .tmid'),sub=hd.querySelector('.subbar .wrap');
 if(++n>60)clearInterval(wait);if(!hero||!sub)return;clearInterval(wait);
 const im=hero.querySelector('.tmcrest img'),h1=hero.querySelector('.tmh1'),pl=hero.querySelector('.tmplace b'),pts=hero.querySelector('.tmpills li b');
 const id=document.createElement('a');id.className='sb-id';id.href='#main';id.setAttribute('aria-hidden','true');id.tabIndex=-1;
 id.innerHTML=`${im?`<img src="${esc(im.getAttribute('src'))}" alt="">`:''}<b>${esc(h1?h1.textContent.replace(/\s+/g,' ').trim():'')}</b>${pl?`<small>${esc(pl.textContent)}-е место${pts?' · '+esc(pts.textContent)+' очк.':''}</small>`:''}`;
 id.addEventListener('click',e=>{e.preventDefault();scrollTo({top:0,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})});
 sub.prepend(id);sub.classList.add('has-id');
 watch(hero,on=>hd.classList.toggle('sb-on',on));
},150);
})();
