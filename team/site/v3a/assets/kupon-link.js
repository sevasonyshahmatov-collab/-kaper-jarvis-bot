/* JARVIS v3a — входы в «Купон» с других страниц хоккея: кнопка «В купон» у матчей в «Прогнозе на сегодня» */
(function(){
 document.querySelectorAll('.fc-m[data-lv-lg][data-lv-t]').forEach(function(li){
  var d=li.dataset,box=li.querySelector('.fc-teams');if(!box||!/^(khl|nhl)$/.test(d.lvLg)||Date.parse(d.lvT)<=Date.now())return;
  var a=document.createElement('a');a.className='fc-kup';a.textContent='В купон';
  a.href='kupon.html?m='+encodeURIComponent([d.lvLg,d.lvT.slice(0,10),d.lvH,d.lvA].join('|'));
  var ml=box.querySelector('.fc-mlink');if(ml){var w=document.createElement('span');w.className='fc-acts';ml.parentNode.insertBefore(w,ml);w.appendChild(ml);w.appendChild(a)}else box.appendChild(a)});
})();
