(()=>{
const ROOT='../../../';
const TD=window.JV_TODAY||{matches:[]},MD=window.JV_MODEL||{},LN=window.JV_LINES||{};
const RM=matchMedia('(prefers-reduced-motion:reduce)').matches;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const atMs=t=>Date.parse(t.replace(' ','T').slice(0,16)+':00+03:00');
const q=new URLSearchParams(location.search).get('now');
const NOW=q?atMs(q.replace('T',' ')):Date.now();
const H=3600e3;
const COL={khl:'#d8232a',nhl:'#1e5bc6'},NAME={khl:'КХЛ',nhl:'НХЛ'};
const mskDay=ms=>new Date(ms+3*H).toISOString().slice(0,10);
const gameDay=t=>mskDay(atMs(t)-6*H-60e3);   // игровой день: от 06:00 до 06:00 МСК
const hhmm=ms=>new Date(ms+3*H).toISOString().slice(11,16);
const plural=(n,a,b,c)=>{const m=n%10,k=n%100;return m==1&&k!=11?a:m>=2&&m<=4&&(k<10||k>=20)?b:c};

/* данные дня */
const all=(TD.matches||[]).filter(m=>m.lg==='khl'||m.lg==='nhl').sort((a,b)=>a.t<b.t?-1:a.t>b.t?1:a.lg<b.lg?-1:1);
const fresh=all.filter(m=>atMs(m.t)>NOW-3*H);
const day=(fresh[0]||all[all.length-1]||{t:''}).t&&gameDay((fresh[0]||all[all.length-1]).t);
const S=all.filter(m=>gameDay(m.t)===day);
if(!S.length){document.getElementById('sch').innerHTML='<p style="margin:0">В последнем обновлении данных матчей КХЛ и НХЛ нет.</p>';return}
const dayStart=atMs(day+' 12:00');
S.forEach(m=>{
  m.ms=atMs(m.t);m.min=Math.round((m.ms-dayStart)/6e4);m.md=MD[m.key]||null;m.ln=LN[m.key]||null;
  const p=m.md;m.fav=p?(p.p1>=p.p2?1:2):0;m.pct=p?Math.round(Math.max(p.p1,p.p2)*100):0;
  m.live=NOW>=m.ms&&NOW<m.ms+2.7*H;m.done=NOW>=m.ms+2.7*H;
});
const pool=S.filter(m=>m.md&&!m.done).length?S.filter(m=>m.md&&!m.done):S.filter(m=>m.md);
const star=pool.reduce((a,m)=>!a||m.pct>a.pct?m:a,null);
if(star)star.star=true;
const nowMin=Math.round((NOW-dayStart)/6e4);
const minM=Math.min(...S.map(m=>m.min)),maxM=Math.max(...S.map(m=>m.min));
const axS=Math.floor(Math.min(0,minM)/60)*60,axE=Math.max(Math.ceil(maxM/60)*60,axS+360);
const lines=['khl','nhl'].filter(l=>S.some(m=>m.lg===l));
lines.forEach(l=>{S.filter(m=>m.lg===l).forEach((m,i)=>m.idx=i)});
const href=m=>ROOT+'hockey/index.html#m-'+m.key.replace(/\|/g,'-');
const em=c=>`${ROOT}assets/em/${c}.webp`;

/* размещение станций вдоль оси времени: жадно, с минимальными зазорами */
function place(o){
  const last={khl:[-1e9,-1e9],nhl:[-1e9,-1e9]};
  let cm=o.start,gm=-1e9,cur=null,barrier=-1e9,nowPos=null,nowDone=!o.nowRow;
  const items=S.slice();
  const out=[];
  const doNow=()=>{
    const p=Math.max(o.base(Math.max(nowMin,axS)),cm,barrier,last.khl[1]+o.nowGap,last.nhl[1]+o.nowGap);
    nowPos=p;barrier=p+o.nowRow;nowDone=true;
  };
  for(const m of items){
    if(m.min!==cur){cm=Math.max(cm,gm);cur=m.min}
    if(!nowDone&&nowMin<=m.min){ if(m.min!==cur){} doNow() }
    const L=last[m.lg];
    const p=Math.max(o.base(m.min),cm,barrier,L[1]+o.g1,L[0]+o.g2);
    L[0]=L[1];L[1]=p;gm=Math.max(gm,p);m.p=p;
    if(m.key===o.open)barrier=Math.max(barrier,p+o.openExt);
  }
  if(!nowDone&&o.nowRow){cm=Math.max(cm,gm);const prev=barrier;barrier=Math.max(barrier,cm);doNow()}
  return {nowPos,end:Math.max(gm,nowPos==null?-1e9:nowPos+(o.nowRow||0),barrier)};
}

const sch=document.getElementById('sch'),svg=document.getElementById('lines'),stl=document.getElementById('stl'),card=document.getElementById('card');
let open=null,first=true,lastW=0;
const SV=(t,a)=>{const e=document.createElementNS('http://www.w3.org/2000/svg',t);for(const k in a)e.setAttribute(k,a[k]);return e};

function cardHtml(m){
  const p=m.md,l=m.ln;
  const bar=p?(()=>{const v=[p.p1,p.x||0,p.p2],s=v[0]+v[1]+v[2];return `<div class="bar" style="--c:${COL[m.lg]}">${v.map((x,i)=>`<span style="flex:${x/s}">${['П1','Х','П2'][i]} ${Math.round(x/s*100)}%</span>`).join('')}</div><div class="cap"><span>${esc(m.hn)}</span><span>${esc(m.an)}</span></div>`})():'<p class="none">Расчёта модели на этот матч пока нет.</p>';
  const od=l?`<div class="od">${[['П1',l.p1],['Х',l.x],['П2',l.p2]].filter(r=>r[1]).map(r=>`<div><small>${r[0]}</small>${(+r[1]).toFixed(2)}</div>`).join('')}</div>`:'<p class="none">Линии пока нет.</p>';
  return `<h3>${esc(m.hn)} — ${esc(m.an)}, ${m.t.slice(11,16)} МСК</h3><div class="cg"><div>${bar}</div><div>${od}</div></div><a class="go" href="${href(m)}">Страница матча</a>`;
}

function render(animate){
  const W=sch.clientWidth,V=matchMedia('(max-width:900px)').matches;
  const nodes=[];stl.innerHTML='';svg.innerHTML='';
  sch.classList.toggle('pre',animate&&!RM);
  const ST=S.map(m=>({m}));
  let cardH=0,openM=S.find(m=>m.key===open);
  card.hidden=!openM;
  if(openM){card.innerHTML=cardHtml(openM);card.style.width=W+'px';card.style.left='0';cardH=card.offsetHeight}
  let H_,pos={};
  if(!V){
    /* горизонтальная схема */
    const start=118,endPad=70;
    const g=[[76,140],[72,124],[70,112]],fs=[1,.8,.6,.45,.3,.15,0];let res,gi=0,done=false;
    for(gi=0;gi<g.length&&!done;gi++)for(const f of fs){
      const k=f*(W-start-endPad)/(axE-axS);
      res=place({start,base:m=>start+(m-axS)*k,g1:g[gi][0],g2:g[gi][1],nowRow:0,nowGap:0,open:null,openExt:0});
      if(res.end<=W-endPad-10){done=true;break}
    }
    if(done)gi--;
    gi=Math.min(gi,g.length-1);
    sch.style.setProperty('--lw',(g[gi][1]-8)+'px');
    const lbH=70,dy=16;
    const Yc={};let y=lbH+40;
    lines.forEach(l=>{Yc[l]=y;y+=2*(lbH+34)+8});
    const axY=Yc[lines[lines.length-1]]+lbH+34+22;
    H_=axY+52;
    /* линии */
    lines.forEach(l=>{
      const L=S.filter(m=>m.lg===l);
      let d=`M 74 ${Yc[l]}`;let px=78,py=Yc[l];
      const pts=L.map(m=>({x:m.p,y:Yc[l]+(m.idx%2?dy/2:-dy/2)}));
      pts.forEach((pt,i)=>{
        const pad=i?29:4;
        if(pt.y===py){d+=` L ${pt.x} ${pt.y}`}
        else{const dd=Math.abs(pt.y-py),sx=px+pad;d+=` L ${sx} ${py} L ${sx+dd} ${pt.y} L ${pt.x} ${pt.y}`}
        px=pt.x;py=pt.y;
      });
      d+=` L ${px+40} ${py}`;
      const p=SV('path',{d,class:'ln',stroke:COL[l]});svg.appendChild(p);nodes.push(p);
      const t=document.createElement('div');t.className='term '+l;t.style.left='0';t.style.top=Yc[l]+'px';
      t.innerHTML=`<img src="${ROOT}assets/lg/${l}.webp" alt="">${NAME[l]}`;stl.appendChild(t);
    });
    /* шкала времени */
    const anc=[[axS,start]];
    [...new Set(S.map(m=>m.min))].forEach(mn=>anc.push([mn,Math.min(...S.filter(m=>m.min===mn).map(m=>m.p))]));
    anc.push([axE,Math.max(W-endPad+10,res.end+30)]);
    anc.sort((a,b)=>a[0]-b[0]);for(let i=1;i<anc.length;i++)anc[i][1]=Math.max(anc[i][1],anc[i-1][1]);
    const fx=mn=>{if(mn<=anc[0][0])return anc[0][1];for(let i=1;i<anc.length;i++)if(mn<=anc[i][0]){const a=anc[i-1],b=anc[i];return b[0]===a[0]?b[1]:a[1]+(b[1]-a[1])*(mn-a[0])/(b[0]-a[0])}return anc[anc.length-1][1]};
    svg.appendChild(SV('line',{class:'axis',x1:start-30,x2:fx(axE),y1:axY,y2:axY}));
    let lx=-99;
    for(let mn=axS;mn<=axE;mn+=60){const x=fx(mn),hr=(12+mn/60)%24;
      svg.appendChild(SV('line',{class:'axis',x1:x,x2:x,y1:axY,y2:axY+6}));
      if(x-lx>=40&&hr%2===0){const t=SV('text',{x,y:axY+22,'text-anchor':'middle'});t.textContent=String(hr).padStart(2,'0')+':00';svg.appendChild(t);lx=x}}
    if(nowMin>=axS&&nowMin<=axE){const x=fx(nowMin);
      svg.appendChild(SV('circle',{class:'nowd',cx:x,cy:axY,r:7}));
      const t=SV('text',{class:'nowt',x,y:axY+42,'text-anchor':'middle'});t.textContent='сейчас '+hhmm(NOW);svg.appendChild(t)}
    S.forEach(m=>{m.x=m.p;m.y=Yc[m.lg]+(m.idx%2?dy/2:-dy/2);m.dir=m.idx%2?'dn':'up'});
    if(openM){card.style.top=(H_+8)+'px';card.style.setProperty('--nx',Math.min(Math.max(openM.x,24),W-24)+'px');H_+=8+cardH+16}
    sch.style.height=H_+'px';svg.setAttribute('width',W);svg.setAttribute('height',H_);
  }else{
    /* вертикальная схема */
    const cx={khl:23,nhl:W-W*0+202-0};
    cx.khl=28;cx.nhl=Math.round(W/2)+28;
    const lw=cx.nhl-cx.khl-34-28-4;
    sch.style.setProperty('--lw',lw+'px');
    const start=70,k=.5;
    const res=place({start,base:m=>start+(m-axS)*k,g1:68,g2:120,nowRow:50,nowGap:62,open:open,openExt:openM?46+cardH+14:0});
    S.forEach(m=>{m.x=cx[m.lg];m.y=m.p;m.dir='r'});
    H_=res.end+40;
    lines.forEach(l=>{
      const L=S.filter(m=>m.lg===l),lastY=L[L.length-1].y;
      const d=`M ${cx[l]} 34 L ${cx[l]} ${lastY} L ${cx[l]} ${lastY+22} L ${cx[l]+14} ${lastY+36}`;
      const p=SV('path',{d,class:'ln',stroke:COL[l]});svg.appendChild(p);nodes.push(p);
      const t=document.createElement('div');t.className='term '+l;t.style.left=(cx[l]-23)+'px';t.style.top='17px';
      t.innerHTML=`<img src="${ROOT}assets/lg/${l}.webp" alt="">${NAME[l]}`;stl.appendChild(t);
    });
    if(res.nowPos!=null){const y=res.nowPos;
      svg.appendChild(SV('line',{class:'nowl',x1:0,x2:W,y1:y,y2:y}));
      const tg=SV('rect',{x:W/2-52,y:y-13,width:104,height:26,rx:13,fill:'#14181f'});svg.appendChild(tg);
      const t=SV('text',{x:W/2,y:y+4.5,'text-anchor':'middle',fill:'#fff'});t.setAttribute('style','fill:#fff;font-weight:700');t.textContent='сейчас '+hhmm(NOW);svg.appendChild(t)}
    if(openM){card.style.top=(openM.y+46)+'px';card.style.setProperty('--nx',(openM.x)+'px')}
    sch.style.height=H_+'px';svg.setAttribute('width',W);svg.setAttribute('height',H_);
  }
  /* станции */
  S.forEach((m,i)=>{
    const b=document.createElement('button');b.type='button';
    b.className=`st ${m.dir==='r'?'':m.dir} ${m.star?'big':''} ${m.live?'live':''} ${m.done?'done':''}`;
    b.style.cssText=`left:${m.x}px;top:${m.y}px;--c:${COL[m.lg]};transition-delay:${animate?1000+i*35:0}ms`;
    b.dataset.k=m.key;b.setAttribute('aria-expanded',m.key===open);b.setAttribute('aria-controls','card');
    b.setAttribute('aria-label',`${m.t.slice(11,16)} ${m.hn} — ${m.an}${m.pct?', фаворит '+m.pct+'%':''}`);
    const nm=`<span class="${m.fav===1?'f':''}">${esc(m.hn)}</span> — <span class="${m.fav===2?'f':''}">${esc(m.an)}</span>`;
    const fl=[m.star?'Матч дня':'',m.live?'идёт':''].filter(Boolean).join(' · ');
    b.innerHTML=`<span class="pill"><img src="${em(m.h)}" alt="" width="20" height="20"><img src="${em(m.a)}" alt="" width="20" height="20"></span><span class="lb"><b class="tm">${m.t.slice(11,16)}${m.pct?`<em>${m.pct}%</em>`:''}</b>${nm}${fl?`<span class="fl">${fl}</span>`:''}</span>`;
    b.addEventListener('click',()=>{open=open===m.key?null:m.key;render(false);if(open)b.focus({preventScroll:true})});
    stl.appendChild(b);
  });
  card.style.left='0';
  /* прорисовка линий */
  if(animate&&!RM){
    nodes.forEach(p=>{const n=p.getTotalLength();p.style.strokeDasharray=n;p.style.strokeDashoffset=n});
    sch.classList.add('anim');
    requestAnimationFrame(()=>requestAnimationFrame(()=>{nodes.forEach(p=>p.style.strokeDashoffset=0);sch.classList.remove('pre')}));
  }
  sch.classList.toggle('anim',animate&&!RM);
  lastW=W;
}

/* список и лиги */
const f1=m=>m.fav===1?'f':'',f2=m=>m.fav===2?'f':'';
document.getElementById('list').innerHTML=S.map(m=>`<li><time>${m.t.slice(11,16)}</time><span class="lgd ${m.lg}">${NAME[m.lg]}</span><a href="${href(m)}"><span class="nm"><span class="${f1(m)}">${esc(m.hn)}</span> — <span class="${f2(m)}">${esc(m.an)}</span></span></a><span class="pc">${m.pct?m.pct+'%':'без расчёта'}</span></li>`).join('');
document.getElementById('lgs').innerHTML=['khl','nhl'].map(l=>{const n=S.filter(m=>m.lg===l).length;return `<a href="${ROOT}hockey/league.html?lg=${l}" style="--c:${COL[l]}"><img src="${ROOT}assets/lg/${l}.webp" alt=""><div><b>${NAME[l]}</b><span>${n} ${plural(n,'станция','станции','станций')} сегодня</span></div></a>`}).join('');

document.addEventListener('keydown',e=>{if(e.key==='Escape'&&open){open=null;render(false)}});
let rt;new ResizeObserver(()=>{if(Math.abs(sch.clientWidth-lastW)>1){clearTimeout(rt);rt=setTimeout(()=>render(false),80)}}).observe(sch);
(document.fonts&&document.fonts.ready||Promise.resolve()).then(()=>render(true));
})();
