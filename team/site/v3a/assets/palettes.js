/* Пробные палитры 60/30/10: ?pal=lime|coral|purple|mono включает, ?pal=off сбрасывает; без параметра сайт как раньше.
   Выбор помнится в sessionStorage до закрытия вкладки. Плашка-переключатель видна только при включённой палитре. */
(function(){
  var d=document.documentElement,K='jv-pal',L=['lime','coral','purple','mono','trend'],N={lime:'Лайм',coral:'Коралл',purple:'Фиолет',mono:'Мята',trend:'Тренд'};
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
  ['palettes.css','pal/common.css','pal/hockey.css','pal/football.css'].forEach(function(f){
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
