/* JARVIS · «Эфир»: загрузчик темы. Подключается в <head> ПЕРЕД assets/palettes.js (одной строкой).
   ?theme=efir включает тему (помнится до закрытия вкладки), ?theme=off сбрасывает. Без параметра сайт как раньше. */
(function(){
  var K='jv-theme',q='',on=false,d=document.documentElement;
  try{q=new URLSearchParams(location.search).get('theme')||''}catch(e){}
  try{
    if(q==='efir')sessionStorage.setItem(K,'efir');else if(q==='off')sessionStorage.removeItem(K);
    on=sessionStorage.getItem(K)==='efir'
  }catch(e){on=q==='efir'}
  if(q==='off')on=false;
  if(!on)return;
  d.classList.add('efir');d.setAttribute('data-efir','1');
  var s=document.currentScript,base=s.src.replace(/efir-loader\.js.*$/,'');
  try{var m=document.querySelector('meta[name=theme-color]');if(m)m.content='#2c374d'}catch(e){}
  var css=['vendor/fonts.css','efir.css','pages-common.css'],extra=['pages-common.js'];
  /* разделы по спорту: футбол — pages-football.css/js + цвета клубов; хоккей — pages-hockey.css/js; общие страницы — pages-common */
  if(d.getAttribute('data-sport')==='football'){css.push('pages-football.css');extra.push('fc-colors.js','pages-football.js')}
  if(d.getAttribute('data-sport')==='hockey'){css.push('pages-hockey.css');extra.push('pages-hockey.js')}
  if(document.readyState==='loading'){
    css.forEach(function(f){document.write('<link rel="stylesheet" href="'+base+f+'">')});
    document.write('<script defer src="'+base+'efir.js"><\/script>');
    extra.forEach(function(f){document.write('<script defer src="'+base+f+'"><\/script>')});
  }else{
    css.forEach(function(f){var l=document.createElement('link');l.rel='stylesheet';l.href=base+f;document.head.appendChild(l)});
    var j=document.createElement('script');j.src=base+'efir.js';document.head.appendChild(j);
    extra.forEach(function(f){var x=document.createElement('script');x.src=base+f;x.async=false;document.head.appendChild(x)});
  }
})();
