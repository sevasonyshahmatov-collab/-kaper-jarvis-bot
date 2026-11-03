/* JARVIS v3a — футбол: общие части страницы «Футбол» и страницы клуба (football/team.html).
   Данные — football/data/football.js (window.JV_FOOT, собирает football/build_data.py из ESPN). Всё из данных экранируем esc(). */
(()=>{
'use strict';
const D=window.JV_FOOT||{teams:{},leagues:{},up:[],h2h:{},axes:[]};
const esc=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const fx=(v,d=2)=>v==null||isNaN(v)?'—':(+v).toFixed(d).replace('.',',');
const pc=v=>Math.round(v*100)+'%';
const plural=(n,a,b,c)=>{const k=n%100,j=n%10;return k>10&&k<20?c:j===1?a:j>1&&j<5?b:c};
const T=D.teams;
const nm=s=>(T[s]||{}).n||s;
const crest=s=>`../assets/fc/${encodeURIComponent(s)}.webp`;
const CI=(s,cls='')=>`<img class="em${cls?' '+cls:''}" src="${crest(s)}" alt="" loading="lazy" width="64" height="64">`;
const LGI=k=>`../assets/lg/${encodeURIComponent(k)}.webp`;
const LGP=k=>`<span class="lgp ${esc(k)}"><img src="${LGI(k)}" alt=""></span>`;
const teamHref=s=>`team.html?id=${encodeURIComponent(s)}`;
const MON=['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'],WD=['вс','пн','вт','ср','чт','пт','сб'];
const day=d=>{const [y,m,dd]=d.slice(0,10).split('-').map(Number),x=new Date(Date.UTC(y,m-1,dd));return {d:dd,mon:MON[m-1],wd:WD[x.getUTCDay()],tm:d.slice(11,16)}};
const dd=t=>`${t.slice(8,10)}.${t.slice(5,7)}`;
const played=g=>g.gf!=null&&g.ga!=null;
const rOf=g=>g.gf>g.ga?'w':g.gf===g.ga?'d':'l';
const RES={w:'В',d:'Н',l:'П'},RESF={w:'победа',d:'ничья',l:'поражение'};
const gamesOf=s=>(T[s]?T[s].games:[]).filter(played).sort((x,y)=>x.d<y.d?1:-1);   // сыгранные, новые первыми
const avg=(a,k)=>{const v=a.map(g=>k(g)).filter(x=>x!=null&&!isNaN(x));return v.length?v.reduce((p,q)=>p+q,0)/v.length:null};
/* показатели клуба по сыгранным матчам сезона */
function stats(s){const P=gamesOf(s),n=P.length;
 const pts=P.reduce((a,g)=>a+(g.gf>g.ga?3:g.gf===g.ga?1:0),0);
 return {n,pts,ppg:n?pts/n:null,gf:avg(P,g=>g.gf),ga:avg(P,g=>g.ga),sh:avg(P,g=>g.x&&g.x.sh),sot:avg(P,g=>g.x&&g.x.sot),cor:avg(P,g=>g.x&&g.x.cor),pos:avg(P,g=>g.x&&g.x.pos),
  shA:avg(P,g=>g.y&&g.y.sh),sotA:avg(P,g=>g.y&&g.y.sot),corA:avg(P,g=>g.y&&g.y.cor),
  ov:n?P.filter(g=>g.gf+g.ga>2).length/n:null,bt:n?P.filter(g=>g.gf>0&&g.ga>0).length/n:null,cs:n?P.filter(g=>g.ga===0).length/n:null}}
/* личные встречи двух клубов: текущий и прошлый сезон, новые первыми */
const h2h=(a,b)=>(D.h2h[[a,b].sort().join('|')]||[]).slice().sort((x,y)=>x.d<y.d?1:-1);
/* форма «В Н П» в виде кружков с эмблемой соперника */
const dots=(s,n=5)=>{const g=gamesOf(s).slice(0,n).reverse();
 return `<span class="dots" aria-label="форма: ${esc(g.map(x=>RESF[rOf(x)]+' '+nm(x.o)+' '+x.gf+':'+x.ga).join(', '))}">${g.map(x=>{const r=rOf(x),o=nm(x.o),sc=`${x.gf}:${x.ga}`;
  return `<i class="${r}" title="${esc((r==='w'?'Победа над ':r==='d'?'Ничья с ':'Поражение от ')+o+' '+sc)}"><img src="${crest(x.o)}" alt="" loading="lazy"></i>`}).join('')}</span>`};
/* шестиугольник силы: перенесён с хоккейной страницы команды, подписи осей — футбольные */
function radar(series,ax){
 const W=366,H=420,r=142,c=W/2,cy=H/2+4,pt=(i,x)=>[c+r*x/100*Math.sin(Math.PI*i/3),cy-r*x/100*Math.cos(Math.PI*i/3)];
 const poly=vs=>vs.map((x,i)=>pt(i,x==null?0:x).map(n=>n.toFixed(1)).join(',')).join(' ');
 const one=series.length===1;
 let o=`<svg class="radar" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(series.map(s=>s.name+': '+ax.map((a,i)=>a+' '+(s.v[i]??'нет данных')).join(', ')).join('; '))}">`;
 for(const k of [100,75,50,25])o+=`<polygon class="${k===100?'rg0':'rg'}" points="${poly(Array(6).fill(k))}"/>`;
 for(let i=0;i<6;i++){const [x,y]=pt(i,100);o+=`<line class="rg" x1="${c}" y1="${cy}" x2="${x}" y2="${y}"/>`}
 if(one)o+=`<polygon class="rmid" points="${poly(Array(6).fill(55))}"/>`;
 series.slice().reverse().forEach(s=>{o+=`<polygon class="rpoly${s.dash?' dash':''}" points="${poly(s.v)}" fill="${esc(s.c)}" stroke="${esc(s.c)}"${s.dash?' stroke-dasharray="9 6"':''}/>`;
  s.v.forEach((x,i)=>{if(x!=null){const [px,py]=pt(i,x);o+=`<circle class="rdot" cx="${px}" cy="${py}" r="5" fill="${esc(s.c)}"/>`}})});
 ax.forEach((a,i)=>{const [lx,vy]=pt(i,100),ty=[0,1,5].includes(i)?vy-26:vy+22;
  o+=`<text class="rlab" x="${lx}" y="${ty}" text-anchor="middle">${esc(a)}</text><text class="rval" x="${lx}" y="${ty+19}" text-anchor="middle">${
   series.map(s=>`<tspan fill="${esc(s.c)}">${s.v[i]??'—'}</tspan>`).join('<tspan class="rsep"> · </tspan>')}</text>`});
 return o+'</svg>';
}
/* цвет клуба: светлеем тёмный, чтобы читался на тёмной шапке */
function bright(h){const n=parseInt(String(h||'3ee08a').replace('#',''),16);let r=n>>16,g=n>>8&255,b=n&255;const l=(.2126*r+.7152*g+.0722*b)/255;
 if(l<.42){const k=(.42-l)/.42*.8+.2;r=Math.round(r+(255-r)*k);g=Math.round(g+(255-g)*k);b=Math.round(b+(255-b)*k)}return `rgb(${r},${g},${b})`}
window.JVF={D,esc,fx,pc,plural,T,nm,crest,CI,LGI,LGP,teamHref,MON,WD,day,dd,played,rOf,RES,RESF,gamesOf,stats,h2h,dots,radar,bright};
})();
/* палитра клуба для шапки страницы клуба: градиент из цветов ESPN, текст — светлый или тёмный по контрасту ≥ 4,5:1 */
(()=>{
const rgb=h=>{const n=parseInt(String(h).replace('#','').replace(/^(.)(.)(.)$/,'$1$1$2$2$3$3'),16);return [n>>16,n>>8&255,n&255]};
const hex=a=>'#'+a.map(v=>Math.max(0,Math.min(255,Math.round(v))).toString(16).padStart(2,'0')).join('');
const mix=(a,b,t)=>hex(rgb(a).map((v,i)=>v+(rgb(b)[i]-v)*t));
const lum=h=>{const c=rgb(h).map(v=>{v/=255;return v<=.03928?v/12.92:((v+.055)/1.055)**2.4});return .2126*c[0]+.7152*c[1]+.0722*c[2]};
const cr=(a,b)=>{const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)};
const sat=h=>{const [r,g,b]=rgb(h),mx=Math.max(r,g,b),mn=Math.min(r,g,b);return mx?(mx-mn)/mx:0};
function palette(c){
 let stops=[c[0],mix(c[0],c[1],.5),c[1]],acc=c[2];
 const ok=t=>stops.every(s=>cr(t,s)>=4.5&&cr(mix(t,s,.25),s)>=4.5);
 let text=null;
 for(let k=0;k<14&&!text;k++){if(ok('#ffffff'))text='#ffffff';else if(ok('#0b0f16'))text='#0b0f16';else stops=stops.map(s=>mix(s,'#000000',.1))}
 text=text||'#ffffff';
 for(let k=0;k<10&&stops.some(s=>cr(acc,s)<3);k++)acc=mix(acc,text,.18);
 let accL=c[2];for(let k=0;k<12&&cr(accL,'#eceee8')<3;k++)accL=mix(accL,'#000000',.12);
 return {stops,text,acc,accL,base:stops[0]};
}
/* ESPN отдаёт два цвета клуба (основной и запасной): шапка — основной, затемнённый; акцент — более насыщенный из двух */
function clubColors(t){const cc=t.c||[],a='#'+(cc[0]||'1b2a44'),b='#'+(cc[1]||'0b1220');
 const dark=x=>lum(x)<.55?x:mix(x,'#000000',.45);
 const c0=dark(a),c1=mix(c0,'#000000',.5);
 const okc=x=>lum(x)<.85&&lum(x)>.02&&sat(x)>.25,acc=okc(a)||!okc(b)?a:b;
 return [c0,c1,acc==='#ffffff'||lum(acc)>.92?'#e8edf4':acc]}
Object.assign(window.JVF,{rgb,hex,mix,lum,cr,palette,clubColors});
})();
