/* Варианты фона первого блока (макет, 06.11): ?hbg=1..5. Без параметра файл ничего не делает — страница как раньше.
   0 — как сейчас (старые canvas #field и #snow), 1 — «Колода лиг», 2 — «Свет арены», 3 — «Чертёж», 4 — «Силуэт», 5 — «Фактура».
   При hbg=1..5 старые canvas не создаются (v3a.js, particles.js проверяют html[data-hbg]). Курсор и мышь не используются. */
(()=>{
'use strict';
let q=null;try{q=new URLSearchParams(location.search).get('hbg')}catch(e){}
if(q===null)return;
const N=/^[0-5]$/.test(q)?+q:0,de=document.documentElement;
if(N>0)de.dataset.hbg=N;
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const NAMES=['Как сейчас','Колода лиг','Свет арены','Чертёж','Силуэт','Фактура'];
const A='../assets/';

/* ── 1. колода лиг ── */
const DECK={
 hockey:[['lg/khl',4,24,-14,1.25,1.6,13],['lg/nhl',90,22,15,1.2,1.8,15],['em/ska',17,66,10,1,2.4,14],['em/cska',3,82,-8,.95,3,12],
   ['em/avangard',44,80,7,.9,3.2,16],['em/nhl_bos',80,74,-12,1,2.2,13],['em/nhl_tor',95,52,9,.9,3,15],['em/akbars',46,18,-6,.85,3.4,14]],
 football:[['lg/epl',4,24,-14,1.2,1.6,13],['lg/laliga',17,70,11,1,2.2,14],['lg/seriea',90,24,14,1.15,1.8,15],['lg/bundesliga',3,86,-9,.95,3,12],
   ['lg/ligue1',46,82,8,.9,3.2,16],['lg/rpl',80,76,-12,1,2.2,13],['lg/ucl',95,54,9,.9,3,15]]
};
function deck(sp){
 const cards=DECK[sp].map(([src,x,y,r,s,b,d],i)=>
  `<div class="k" style="--x:${x}%;--y:${y}%;--s:${s};--r:${r}deg;--b:${b}px;--d:${d}s;--dl:${-i*2.7}s;--dx:${(i%2?-1:1)*(1.4+i%3*.4)}vmin;--dy:${(i%3-1)*1.3}vmin"><div class="kd"><img src="${A}${src}.webp" alt="" draggable="false"><i></i></div></div>`).join('');
 return `<div class="cards">${cards}</div><div class="cones"><i></i><i></i><i></i></div>`;
}
/* ── 2. свет арены ── */
const arena=()=>`<div class="bms"><i></i><i></i><i></i></div><div class="floor"><b></b><b></b><b></b><s></s></div>`;
/* ── 3. чертёж ── */
const RINK=`<svg viewBox="-3 -3 206 91" aria-hidden="true">
<g class="ln"><path id="hbo" pathLength="100" d="M28 0H172A28 28 0 0 1 200 28V57A28 28 0 0 1 172 85H28A28 28 0 0 1 0 57V28A28 28 0 0 1 28 0Z"/>
<path d="M100 0V85M75 0V85M125 0V85M11 3V82M189 3V82"/><circle id="hbc" pathLength="100" cx="100" cy="42.5" r="15"/>
<circle cx="31" cy="20.5" r="15"/><circle cx="31" cy="64.5" r="15"/><circle cx="169" cy="20.5" r="15"/><circle cx="169" cy="64.5" r="15"/>
<path d="M11 36.5A6 6 0 0 1 11 48.5M189 48.5A6 6 0 0 1 189 36.5M-1.5 39V46H11M201.5 39V46H189"/></g>
<g class="dt"><circle cx="100" cy="42.5" r="1"/><circle cx="31" cy="20.5" r="1"/><circle cx="31" cy="64.5" r="1"/><circle cx="169" cy="20.5" r="1"/><circle cx="169" cy="64.5" r="1"/><circle cx="80" cy="20.5" r="1"/><circle cx="80" cy="64.5" r="1"/><circle cx="120" cy="20.5" r="1"/><circle cx="120" cy="64.5" r="1"/></g>
<use href="#hbo" class="run r1"/><use href="#hbc" class="run r2"/></svg>`;
const PITCH=`<svg viewBox="-5 -4 115 76" aria-hidden="true">
<g class="ln"><rect id="hbo" pathLength="100" x="0" y="0" width="105" height="68"/><path d="M52.5 0V68"/><circle id="hbc" pathLength="100" cx="52.5" cy="34" r="9.15"/>
<rect x="0" y="13.84" width="16.5" height="40.32"/><rect x="88.5" y="13.84" width="16.5" height="40.32"/><rect x="0" y="24.84" width="5.5" height="18.32"/><rect x="99.5" y="24.84" width="5.5" height="18.32"/>
<path d="M16.5 26.69A9.15 9.15 0 0 1 16.5 41.31M88.5 41.31A9.15 9.15 0 0 1 88.5 26.69M-2.4 30.3V37.7H0M107.4 30.3V37.7H105"/></g>
<g class="dt"><circle cx="52.5" cy="34" r=".6"/><circle cx="11" cy="34" r=".6"/><circle cx="94" cy="34" r=".6"/></g>
<use href="#hbo" class="run r1"/><use href="#hbc" class="run r2"/></svg>`;
const plan=sp=>`<div class="pw"><div class="pl">${sp==='football'?PITCH:RINK}</div></div>`;
/* ── 4. силуэт ── */
const DUO={hockey:['.03 .30','.07 .47','.16 .68'],football:['.03 .22','.08 .50','.13 .46']};
function sil(sp){
 const d=DUO[sp];
 return `<svg width="0" height="0" style="position:absolute" aria-hidden="true"><filter id="hb-duo" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values=".33 .33 .33 0 0 .33 .33 .33 0 0 .33 .33 .33 0 0 0 0 0 1 0"/><feComponentTransfer><feFuncR type="table" tableValues="${d[0]}"/><feFuncG type="table" tableValues="${d[1]}"/><feFuncB type="table" tableValues="${d[2]}"/></feComponentTransfer></filter></svg>`+
  `<div class="sl"><img src="${A}herobg/img/${sp}.webp" alt="" draggable="false"></div>`+
  (sp==='football'?`<p class="cr">Фото: Kylian Mbappé — Bryan Berlin, CC BY-SA 4.0, Wikimedia Commons</p>`:'');
}
/* ── 5. фактура ── */
function ice(cv){
 let s=7;const R=()=>(s=(s*16807)%2147483647)/2147483647;
 const W=cv.width=Math.min(innerWidth,1920),H=cv.height=Math.min(Math.max(innerHeight,600),1100),c=cv.getContext('2d');
 c.clearRect(0,0,W,H);c.lineCap='round';
 const n=Math.round(W*H/2600);
 for(let i=0;i<n;i++){
  const x=R()*W,y=R()*H,len=(.1+R()*.5)*W,a=(R()-.5)*.9+(R()<.5?0:Math.PI*.12),bend=(R()-.5)*len*.4,hi=R()<.12;
  c.strokeStyle=hi?`rgba(215,238,255,${.08+R()*.10})`:`rgba(150,190,235,${.05+R()*.10})`;c.lineWidth=hi?1.1:.5+R()*.7;
  c.beginPath();c.moveTo(x,y);c.quadraticCurveTo(x+Math.cos(a)*len/2-Math.sin(a)*bend,y+Math.sin(a)*len/2+Math.cos(a)*bend,x+Math.cos(a)*len,y+Math.sin(a)*len);c.stroke();
 }
}
const tex=sp=>sp==='football'?`<div class="gr"></div><div class="mow"></div><div class="cloud"></div>`:`<canvas class="ic"></canvas><div class="sheen"></div>`;

function build(){
 const sp=document.body.dataset.field==='football'?'football':'hockey';
 const el=document.createElement('div');el.className='hb';el.dataset.v=N;el.dataset.sp=sp;el.setAttribute('aria-hidden','true');
 el.innerHTML=[0,deck,arena,plan,sil,tex][N](sp);
 document.body.prepend(el);
 if(N===5&&sp==='hockey'){const cv=el.querySelector('canvas');ice(cv);let t;addEventListener('resize',()=>{clearTimeout(t);t=setTimeout(()=>ice(cv),250)})}
 if(N===1&&!RM){ /* блик — раз в 6 с на одной случайной карточке */
  const ks=[...el.querySelectorAll('.kd')];let last=-1;
  setInterval(()=>{if(document.hidden)return;let n;do{n=Math.floor(Math.random()*ks.length)}while(n===last&&ks.length>1);last=n;
   const k=ks[n];k.classList.remove('gl');void k.offsetWidth;k.classList.add('gl')},6000);
 }
}
function switcher(){
 const el=document.createElement('nav');el.className='hb-sw';el.setAttribute('aria-label','Вариант фона первого блока');
 el.innerHTML='<span>Фон</span>'+NAMES.map((t,i)=>`<a href="#" data-n="${i}" title="${i} — ${t}"${i===N?' aria-current="true"':''}>${i}</a>`).join('')+`<em>${N} — ${NAMES[N]}</em>`;
 el.addEventListener('click',e=>{const a=e.target.closest('a');if(!a)return;e.preventDefault();
  const u=new URL(location.href);u.searchParams.set('hbg',a.dataset.n);location.href=u.toString()});
 document.body.append(el);
}
document.addEventListener('DOMContentLoaded',()=>{if(N)build();switcher()});
})();
