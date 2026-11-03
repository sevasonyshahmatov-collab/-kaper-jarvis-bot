/* JARVIS v3a — сцена-фон клуба: один fixed-слой с картинкой assets/club/bg/<id>.webp, зерно и затемнение (стили — bg.css).
   Лёгкий параллакс/масштаб при прокрутке — только transform и только без prefers-reduced-motion. Подключает team.js по флагу bg:1. */
(()=>{const id=document.body.dataset.clubId;if(!id)return;
const sc=document.createElement('div');sc.className='clubscene';sc.setAttribute('aria-hidden','true');
sc.innerHTML='<i class="cs-img"></i><i class="cs-shade"></i><i class="cs-grain"></i>';
document.body.prepend(sc);
document.body.style.setProperty('--club-bg',`url(${new URL('../assets/club/bg/'+id+'.webp',location.href).href})`);
if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
let q=0;const upd=()=>{q=0;const d=document.documentElement,m=Math.max(1,d.scrollHeight-innerHeight),p=Math.min(1,Math.max(0,scrollY/m));
 sc.style.setProperty('--py',(-p*3.2+1.6).toFixed(2)+'%');sc.style.setProperty('--sc',(1.03+p*.05).toFixed(4))};
addEventListener('scroll',()=>{if(!q)q=requestAnimationFrame(upd)},{passive:true});addEventListener('resize',upd);upd()})();
