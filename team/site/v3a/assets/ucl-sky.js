/* JARVIS v3a — звёздное небо и знак турнира для data-theme="ucl" / "uel": свой SVG, пятиконечные звёзды разного размера (как на мяче турнира),
   детерминированная раскладка, без анимации у курсора. */
(()=>{
'use strict';
const th=document.documentElement.dataset.theme;
if(th!=='ucl'&&th!=='uel')return;
if(document.querySelector('.ucl-deco'))return;
let s=7;const rnd=()=>(s=(s*16807)%2147483647)/2147483647;
const star=(cx,cy,r)=>{let p='';for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,k=i%2?r*.42:r;p+=`${(cx+k*Math.cos(a)).toFixed(1)},${(cy+k*Math.sin(a)).toFixed(1)} `}return p};
let st='';
const pick=()=>{const r=rnd();return th==='ucl'?(r<.5?'#e8f0ff':r<.88?'#6fe3ff':'#ff6cbb'):(r<.6?'#fff0de':'#ffa04a')};
for(let i=0;i<70;i++){const r=3+rnd()**2.2*15,o=(.1+rnd()*.32).toFixed(2);st+=`<polygon points="${star(rnd()*1600,rnd()*1000,r)}" fill="${pick()}" opacity="${o}"/>`}
for(let i=0;i<60;i++)st+=`<circle cx="${(rnd()*1600).toFixed(0)}" cy="${(rnd()*1000).toFixed(0)}" r="${(.6+rnd()*1.2).toFixed(1)}" fill="${pick()}" opacity="${(.2+rnd()*.4).toFixed(2)}"/>`;
/* свой векторный знак турнира (всегда резкий): ЛЧ — звёздный мяч (пять звёзд вокруг центральной), ЛЕ — оранжевое кольцо с гранями */
let ball='';
if(th==='ucl'){let b2=`<circle cx="400" cy="400" r="372" fill="none" stroke="#dfe9ff" stroke-width="6" opacity=".9"/>`;
 b2+=`<polygon points="${star(400,400,118)}" fill="#dfe9ff"/>`;
 for(let i=0;i<5;i++){const a=-Math.PI/2+i*Math.PI*2/5,x=400+250*Math.cos(a),y=400+250*Math.sin(a);b2+=`<polygon points="${star(x,y,96)}" fill="#dfe9ff" opacity=".78" transform="rotate(${i*72+36} ${x} ${y})"/>`}
 for(let i=0;i<5;i++){const a=-Math.PI/2+(i+.5)*Math.PI*2/5,x=400+345*Math.cos(a),y=400+345*Math.sin(a);b2+=`<polygon points="${star(x,y,38)}" fill="#6fe3ff" opacity=".7"/>`}
 ball=`<svg class="ball" viewBox="0 0 800 800" style="opacity:.13" aria-hidden="true">${b2}</svg>`}
else{let b2='';for(let k=0;k<4;k++)b2+=`<circle cx="400" cy="400" r="${372-k*52}" fill="none" stroke="#ff8a1f" stroke-width="${k?4:14}" stroke-dasharray="${k?'420 90':'1600 0'}" opacity="${k?.55:.9}" transform="rotate(${k*37} 400 400)"/>`;
 for(let i=0;i<5;i++){const a=-Math.PI/2+i*Math.PI*2/5;b2+=`<polygon points="${star(400+120*Math.cos(a),400+120*Math.sin(a),44)}" fill="#fff0de" opacity=".6"/>`}
 ball=`<svg class="ball" viewBox="0 0 800 800" style="opacity:.14" aria-hidden="true">${b2}</svg>`}
const d=document.createElement('div');d.className='ucl-deco';d.setAttribute('aria-hidden','true');
d.innerHTML=`<svg viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">${st}</svg>${ball}`;
document.body.prepend(d);
})();
