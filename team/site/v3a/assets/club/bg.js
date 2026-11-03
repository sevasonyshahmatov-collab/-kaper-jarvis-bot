/* JARVIS v3a — картинка в шапке клуба: слой .hbg внутри .tmhero (стили — bg.css). Лёгкий параллакс только внутри шапки,
   только transform и только без prefers-reduced-motion. Подключает team.js по флагу bg:1. */
(()=>{const id=document.body.dataset.clubId,hero=document.querySelector('.tmhero');if(!id||!hero)return;
const l=document.createElement('div');l.className='hbg';l.setAttribute('aria-hidden','true');
l.innerHTML='<i class="hb-img"></i><i class="hb-shade"></i>';hero.prepend(l);
document.body.style.setProperty('--club-bg',`url(${new URL('../assets/club/bg/'+id+'.webp',location.href).href})`);
if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
let q=0;const upd=()=>{q=0;const h=hero.offsetHeight||1,p=Math.min(1,Math.max(0,scrollY/h));l.style.setProperty('--py',(p*h*.07).toFixed(1)+'px')};
addEventListener('scroll',()=>{if(!q)q=requestAnimationFrame(upd)},{passive:true});addEventListener('resize',upd);upd()})();
