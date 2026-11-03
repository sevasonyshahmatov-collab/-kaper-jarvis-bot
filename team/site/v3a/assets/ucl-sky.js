/* JARVIS v3a — звёздное небо и знак турнира для data-theme="ucl" / "uel": свой SVG, пятиконечные звёзды разного размера (как на мяче турнира),
   детерминированная раскладка, без анимации у курсора. */
(()=>{
'use strict';
const th=document.documentElement.dataset.theme;
if(th!=='ucl'&&th!=='uel')return;
if(document.querySelector('.ucl-deco'))return;
let s=7;const rnd=()=>(s=(s*16807)%2147483647)/2147483647;
const star=(cx,cy,r)=>{let p='';for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,k=i%2?r*.42:r;p+=`${(cx+k*Math.cos(a)).toFixed(1)},${(cy+k*Math.sin(a)).toFixed(1)} `}return p};
let st='';const col=th==='ucl'?'#dfe9ff':'#ffd9b0';
for(let i=0;i<70;i++){const r=3+rnd()**2.2*15,o=(.08+rnd()*.3).toFixed(2);st+=`<polygon points="${star(rnd()*1600,rnd()*1000,r)}" fill="${col}" opacity="${o}"/>`}
for(let i=0;i<60;i++)st+=`<circle cx="${(rnd()*1600).toFixed(0)}" cy="${(rnd()*1000).toFixed(0)}" r="${(.6+rnd()*1.2).toFixed(1)}" fill="${col}" opacity="${(.2+rnd()*.4).toFixed(2)}"/>`;
const d=document.createElement('div');d.className='ucl-deco';d.setAttribute('aria-hidden','true');
const base=document.currentScript&&document.currentScript.src?document.currentScript.src.replace(/ucl-sky\.js.*$/,''):'../assets/';
d.innerHTML=`<svg viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">${st}</svg><img class="lgbig" src="${base}lg/${th}.webp" alt="">`;
document.body.prepend(d);
})();
