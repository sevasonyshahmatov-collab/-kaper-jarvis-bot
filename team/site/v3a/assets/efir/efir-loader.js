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
  var css=['vendor/fonts.css','efir.css'];
  if(document.readyState==='loading'){
    css.forEach(function(f){document.write('<link rel="stylesheet" href="'+base+f+'">')});
    document.write('<script defer src="'+base+'efir.js"><\/script>');
  }else{
    css.forEach(function(f){var l=document.createElement('link');l.rel='stylesheet';l.href=base+f;document.head.appendChild(l)});
    var j=document.createElement('script');j.src=base+'efir.js';document.head.appendChild(j);
  }
})();
