/* JARVIS v3a — картинка клуба, два варианта по ?bgv= (hero или bottom, иначе bottom; mode ставит team.js классом club-bgh / club-bgb):
   hero — размытый слой .hbg внутри .tmhero; bottom — блок .clubend перед подвалом. Стили — bg.css. Лёгкий параллакс только внутри
   блока, только transform и только без prefers-reduced-motion. Подключает team.js по флагу bg:1. */
(()=>{const b=document.body,id=b.dataset.clubId,hero=document.querySelector('.tmhero'),ft=document.querySelector('footer');if(!id)return;
const bottom=b.classList.contains('club-bgb');let el;
b.style.setProperty('--club-bg',`url(${new URL('../assets/club/bg/'+id+'.webp',document.baseURI).href})`);
if(bottom){if(!ft)return;el=document.createElement('div');el.className='clubend';el.innerHTML='<i class="ce-img"></i><i class="ce-top"></i><i class="ce-bot"></i>';
 const pk=document.querySelector('#picks');if(pk){const c=getComputedStyle(pk).backgroundColor;if(c&&c!=='rgba(0, 0, 0, 0)')el.style.setProperty('--ce-page',c)}
 ft.parentNode.insertBefore(el,ft)}
else{if(!hero)return;el=document.createElement('div');el.className='hbg';el.innerHTML='<i class="hb-img"></i><i class="hb-shade"></i>';hero.prepend(el)}
el.setAttribute('aria-hidden','true');
if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
let q=0;const upd=()=>{q=0;if(bottom){const r=el.getBoundingClientRect(),p=Math.min(1,Math.max(0,(innerHeight-r.top)/(r.height+innerHeight)));el.style.setProperty('--py',((p-.5)*r.height*.1).toFixed(1)+'px')}
 else{const h=hero.offsetHeight||1,p=Math.min(1,Math.max(0,scrollY/h));el.style.setProperty('--py',(p*h*.07).toFixed(1)+'px')}};
addEventListener('scroll',()=>{if(!q)q=requestAnimationFrame(upd)},{passive:true});addEventListener('resize',upd);upd()})();
