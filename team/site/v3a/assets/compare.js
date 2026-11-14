/* фото КХЛ без белого фона (черновик 14.11): адрес khl.ru -> hockey/data/kph/<папка>_<номер>.webp (hockey/khl_cut.py) */
window.JV_KPH=window.JV_KPH||(S=>u=>{if(!window.JV_KPH_ON)return u;const m=/khl\.ru\/img\/teamplayers_db\/(\d+)\/(\d+)\.jpg/.exec(u||'');return m&&S?new URL('../hockey/data/kph/'+m[1]+'_'+m[2]+'.webp',S).href:u})(document.currentScript&&document.currentScript.src);
/* JARVIS v3a — «Сравнение» (идеи 10 и 15): hockey/compare.html?t=clubs|players&a=<id>&b=<id>.
   Клубы — assets/data/teams-lite.js (таблица, 6 осей, игры сезона). Игроки — список из data/search.json (p),
   профиль — hockey/data/pp/<лига>/<id>.json, для НХЛ ещё hockey/data/nhl_skills.json (силовые, блоки, скорость).
   Только реальные поля; чего в данных нет (броски КХЛ) — строка не показывается. Адрес страницы — ссылка на это сравнение. */
(()=>{
const $=id=>document.getElementById(id),OUT=$('cmp-out');
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
/* футбол (football/compare.html, <html data-sport="football">): клубы из football/data/football-lite.js приводятся к тому же виду,
   что хоккейные; игр по матчам в этом файле нет — блоки «Дом и выезд», «Форма» и очные встречи заменяют оси 0–100 и ближайшая встреча */
const FB=document.documentElement.dataset.sport==='football',JF=window.JV_FOOT||{};
const TT=FB?Object.fromEntries(Object.entries(JF.teams||{}).filter(([,t])=>(JF.leagues||{})[t.lg]&&t.gp).map(([k,t])=>[k,{name:t.n,lg:t.lg,place:t.place,gp:t.gp,w:t.w,d:t.d,l:t.l,gf:t.gf,ga:t.ga,pts:t.pts,axes:t.axes,ucl:t.lg==='ucl'||(t.cups||[]).includes('ucl'),
  colors:(t.c||[]).map(c=>'#'+String(c).replace('#',''))}])):(window.JV_TEAMS||{}).teams||{};
const AX=FB?JF.axes||[]:(window.JV_TEAMS||{}).axes||[],ML=window.JV_MATCHLINKS||{};
const EMDIR=FB?'fc':'em',TEAMURL=id=>FB?'team.html?id='+id:'../team/index.html?id='+id;
const Q=new URLSearchParams(location.search);
const st={t:!FB&&Q.get('t')==='players'?'players':'clubs',a:Q.get('a')||'',b:Q.get('b')||''};
const num=(x,d)=>x==null||isNaN(x)?'—':Number(x).toFixed(d==null?0:d).replace('.',',');
const ddmm=d=>d.slice(8,10)+'.'+d.slice(5,7);
const mmss=s=>s?Math.floor(s/60)+':'+String(Math.round(s%60)).padStart(2,'0'):'—';
const em=(id,sz)=>`<img class="cmp-em" src="../assets/${EMDIR}/${encodeURIComponent(id)}.webp" alt="" width="${sz||28}" height="${sz||28}" loading="lazy" onerror="this.style.visibility='hidden'">`;
/* цвет стороны — цвет её клуба: первый насыщенный из палитры, осветлённый для тёмного фона; если у второй стороны выходит
   похожий оттенок (один клуб или близкие цвета) — берём её следующий цвет, а если и он похож — светлый нейтральный */
const hsl=h=>{const n=parseInt(h.slice(1),16),r=(n>>16&255)/255,g=(n>>8&255)/255,b=(n&255)/255,mx=Math.max(r,g,b),mn=Math.min(r,g,b),l=(mx+mn)/2,d=mx-mn;
  if(!d)return[0,0,l];const sat=d/(1-Math.abs(2*l-1));let hh=mx===r?((g-b)/d)%6:mx===g?(b-r)/d+2:(r-g)/d+4;return[(hh*60+360)%360,sat,l]};
const lit=c=>{const[h,sa,l]=hsl(c),lo=h>205&&h<290?.69:.58;   /* синие и фиолетовые на тёмном фоне темнее на вид — поднимаем сильнее */
  return `hsl(${Math.round(h)} ${Math.round(Math.max(sa,.55)*100)}% ${Math.round(Math.min(Math.max(l,lo),.76)*100)}%)`};
const cands=id=>(((TT[id]||{}).colors)||[]).filter(c=>/^#[0-9a-f]{6}$/i.test(c)&&hsl(c)[1]>.28&&hsl(c)[2]>.1&&hsl(c)[2]<.93);
const far=(x,y)=>{const d=Math.abs(hsl(x)[0]-hsl(y)[0]);return Math.min(d,360-d)>38};
function sideColors(ta,tb){const ca=cands(ta)[0]||'#5ab8ff',cb=cands(tb).find(c=>far(c,ca));return[lit(ca),cb?lit(cb):'#e9eef7']}
const paint=(ta,tb)=>{const c=sideColors(ta,tb);OUT.style.setProperty('--ca',c[0]);OUT.style.setProperty('--cb',c[1])};
const LGN=FB?Object.fromEntries(Object.entries(JF.leagues||{}).map(([k,v])=>[k,v.name||k])):{khl:'КХЛ',nhl:'НХЛ'};
let IDX=null;const index=()=>IDX||(IDX=fetch('../data/search.json').then(r=>r.json()).catch(()=>({c:[],p:[]})));
/* клубы сравниваем только внутри одной лиги (владелец 11.11); исключение — футбол: участники Лиги чемпионов между собой */
const pairOk=(a,b)=>{const A=TT[a],B=TT[b];return !!A&&!!B&&(A.lg===B.lg||(FB&&A.ucl&&B.ucl))};
const mate=a=>{const A=TT[a];return Object.keys(TT).filter(k=>k!==a&&TT[k].lg===A.lg).sort((x,y)=>TT[x].place-TT[y].place||TT[y].pts-TT[x].pts)[0]||''};
const clubs=()=>Object.keys(TT).filter(k=>LGN[TT[k].lg]).map(k=>({id:k,n:TT[k].name,lg:TT[k].lg,t:k})).sort((x,y)=>x.n.localeCompare(y.n,'ru'));
const players=()=>index().then(d=>(d.p||[]).map(p=>({id:p[1]+'-'+p[4],n:p[0],lg:p[1],t:p[2],pts:p[3]})));
const list=()=>st.t==='clubs'?Promise.resolve(clubs()):players();
const cache={};const jget=u=>cache[u]||(cache[u]=fetch(u).then(r=>r.ok?r.json():null).catch(()=>null));

/* ── кто впереди: у каждой сравнимой строки/плитки data-w="a|b|d"; по ним считаются счёт блока и общий итог ── */
const ok=x=>x!=null&&!isNaN(x);
const win=(a,b,low)=>a===b?'d':(low?a<b:a>b)?'a':'b';
const cnt=(s,w)=>(s.match(new RegExp('data-w="'+w+'"','g'))||[]).length;
/* строка: значение · подпись · значение; полосы — доля от суммы; лидер — цветная плашка, полоса отстающего приглушена */
function row(label,a,b,o){o=o||{};const f=o.f||(x=>num(x,o.d));
  if(!ok(a)&&!ok(b))return '';
  let wa=50,wb=50,w='';
  if(ok(a)&&ok(b)){const mn=Math.min(a,b,0),A=a-mn,B=b-mn,s=A+B;if(s>0){wa=Math.round(A/s*100);wb=100-wa}
    if(!o.flat)w=win(a,b,o.low)}
  return `<div class="cmp-row${w?' w-'+w:''}"${w?` data-w="${w}"`:''}><b class="v">${ok(a)?f(a):'—'}</b><span class="l">${esc(label)}</span><b class="v">${ok(b)?f(b):'—'}</b>
   ${ok(a)&&ok(b)?`<i class="bar${o.flat?' flat':''}" aria-hidden="true"><u style="width:${wa}%"></u><u style="width:${wb}%"></u></i>`:''}</div>`}
/* плитки-дуэли: главные цифры блока крупно */
function tiles(items){const t=items.map(([l,a,b,o])=>{o=o||{};if(!ok(a)||!ok(b))return '';const f=o.f||(x=>num(x,o.d)),w=win(a,b,o.low);
  return `<div class="cmp-tile w-${w}" data-w="${w}"><span>${esc(l)}</span><p><b>${f(a)}</b><b>${f(b)}</b></p></div>`}).filter(Boolean);
  return t.length?`<div class="cmp-tiles">${t.join('')}</div>`:''}
const chip=s=>{const a=cnt(s,'a'),b=cnt(s,'b');return a+b?`<span class="cmp-sc" title="В скольких показателях блока впереди каждая сторона"><b class="a">${a}</b><i>:</i><b class="b">${b}</b></span>`:''};
const group=(h,rows)=>{rows=rows.filter(Boolean);const s=rows.join('');return rows.length?`<section class="cmp-g"><h2><span>${esc(h)}</span>${chip(s)}</h2>${s}</section>`:''};
const dots=a=>`<span class="cmp-dots">${a.map(x=>`<i class="fd-${x.c}" title="${esc(x.t)}">${esc(x.s)}</i>`).join('')}</span>`;
/* общий итог под карточками сторон */
function verdict(html,na,nb){const a=cnt(html,'a'),b=cnt(html,'b'),d=cnt(html,'d');if(!(a+b))return '';
  return `<div class="cmp-ver ${a>b?'w-a':b>a?'w-b':''}"><p>${a===b?'<b>Поровну</b> — по '+a+' из '+(a+b+d):'Впереди <b>'+esc(a>b?na:nb)+'</b> — '+Math.max(a,b)+' из '+(a+b+d)} показателей сезона</p>
   <i class="vb" aria-hidden="true"><u style="flex:${a}"></u><u style="flex:${b}"></u></i><p class="vn"><span>${esc(na)} · ${a}</span>${d?`<span>равны · ${d}</span>`:''}<span>${esc(nb)} · ${b}</span></p></div>`}
/* две панели рядом: по одной на сторону */
const panels=(w,pa,pb)=>`<div class="cmp-forms w-${w}" data-w="${w}">${pa}${pb}</div>`;
const fpanel=(s,e,n,body,big,cap)=>`<div class="cmp-fp ${s}"><h3>${e}<span>${esc(n)}</span></h3>${body}<p><b>${big}</b> ${esc(cap)}</p></div>`;

/* ── фигуры силы: два многоугольника поверх друг друга (клубы — 6 осей, игроки — 5 оценок), шкала 0–100 ── */
function radar(names,va,vb,la,lb,h){
  const n=names.length;if(n<3||va.some(x=>x==null)||vb.some(x=>x==null))return '';
  const W=340,H=310,cx=W/2,cy=H/2+4,R=104,pt=(i,v)=>{const a=-Math.PI/2+i*2*Math.PI/n,r=R*v/100;return[(cx+r*Math.cos(a)).toFixed(1),(cy+r*Math.sin(a)).toFixed(1)]};
  const poly=v=>v.map((x,i)=>pt(i,Math.max(4,Math.min(100,x))).join(',')).join(' '),ring=k=>names.map((_,i)=>pt(i,k).join(',')).join(' ');
  const lab=names.map((nm,i)=>{const p=pt(i,100),a=-Math.PI/2+i*2*Math.PI/n,x=cx+(R+14)*Math.cos(a),y=cy+(R+14)*Math.sin(a),an=Math.abs(Math.cos(a))<.3?'middle':Math.cos(a)>0?'start':'end';
    return `<line x1="${cx}" y1="${cy}" x2="${p[0]}" y2="${p[1]}"/><text x="${x.toFixed(1)}" y="${(y+(Math.sin(a)>.3?10:Math.sin(a)<-.3?-2:4)).toFixed(1)}" text-anchor="${an}">${esc(nm)}</text>`}).join('');
  const desc=names.map((nm,i)=>nm+': '+va[i]+' и '+vb[i]).join('; ');
  return `<section class="cmp-g cmp-rad"><h2>${esc(h)}</h2><div class="cmp-radb"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(la+' и '+lb+'. '+desc)}">
   <g class="rd-grid">${[25,50,75,100].map(k=>`<polygon points="${ring(k)}"/>`).join('')}${lab}</g>
   <polygon class="rd-a" points="${poly(va)}"/><polygon class="rd-b" points="${poly(vb)}"/>
   ${va.map((x,i)=>`<circle class="rd-da" cx="${pt(i,Math.max(4,x))[0]}" cy="${pt(i,Math.max(4,x))[1]}" r="3.2"/>`).join('')}${vb.map((x,i)=>`<circle class="rd-db" cx="${pt(i,Math.max(4,x))[0]}" cy="${pt(i,Math.max(4,x))[1]}" r="3.2"/>`).join('')}</svg>
   <ul class="cmp-leg"><li class="a"><i></i>${la}</li><li class="b"><i></i>${lb}</li></ul></div></section>`}

/* ── клубы ── */
function clubView(a,b){
  const A=TT[a],B=TT[b],ea=em(a,22),eb=em(b,22);
  const fin=t=>(t.games||[]).filter(g=>g.gf!=null&&g.ga!=null);
  const last=t=>fin(t).slice(-5).map(g=>({c:g.gf>g.ga?'w':'l',s:g.gf>g.ga?'В':'П',t:ddmm(g.d)+' '+((TT[g.o]||{}).name||g.o)+' '+g.gf+':'+g.ga+(g.x?' '+g.x:'')}));
  const pg=(t,k)=>t.gp?t[k]/t.gp:null;
  const h2h=fin(A).filter(g=>g.o===b).map(g=>({d:g.d,h:g.h?a:b,w:g.h?b:a,sh:g.h?g.gf:g.ga,sa:g.h?g.ga:g.gf,x:g.x||''}));
  const next=(A.games||[]).find(g=>g.o===b&&g.gf==null&&Date.parse(g.d.replace(' ','T')+':00+03:00')>Date.now());
  const wa=h2h.filter(m=>(m.h===a)===(m.sh>m.sa)).length;
  const link=m=>{const k=TT[m.h].lg+'|'+m.d.slice(0,10)+'|'+m.h+'|'+m.w;return ML[k]?'../'+ML[k]:''};
  /* дом и выезд: две карточки, в каждой обе команды — победы–поражения и доля побед полосой */
  const venue=()=>{if(!A.tr||!B.tr)return '';const pc=r=>r[0]+r[1]?r[0]/(r[0]+r[1])*100:0;
    const card=(h,k)=>{const x=A.tr[k],y=B.tr[k],pa=pc(x),pb=pc(y),w=win(pa,pb);
      const ln=(s,e,n,r,p)=>`<div class="ln ${s}">${e}<span>${esc(n)}</span><b>${r[0]}–${r[1]}</b><i aria-hidden="true"><u style="width:${Math.round(p)}%"></u></i><em>${Math.round(p)} %</em></div>`;
      return `<div class="cmp-vc w-${w}" data-w="${w}"><h3>${h}<small>победы–поражения, доля побед</small></h3>${ln('a',ea,A.name,x,pa)}${ln('b',eb,B.name,y,pb)}</div>`};
    return `<div class="cmp-ven">${card('Дома','home')}${card('В гостях','away')}</div>`};
  /* футбол: ближайшая встреча из расчёта модели (JV_FOOT.up) */
  const fbNext=()=>{const u=(JF.up||[]).find(m=>(m.h===a&&m.a===b)||(m.h===b&&m.a===a));if(!u)return '';const hn=TT[u.h].name,an=TT[u.a].name;
    return `<section class="cmp-g"><h2><span>Ближайшая встреча</span></h2><ul class="cmp-h2h"><li><div><time>${ddmm(u.t)}</time><span>${esc(hn)}${em(u.h,24)}</span><b>${esc(u.t.slice(11))}</b><span>${em(u.a,24)}${esc(an)}</span></div></li></ul>
     <p class="cmp-note">Время московское. ${esc(hn)} играет дома.</p></section>`};
  const form=ok(A.l10)&&ok(B.l10)?panels(win(A.l10,B.l10),fpanel('a',ea,A.name,dots(last(A)),A.l10,'очков в 10 последних матчах'),fpanel('b',eb,B.name,dots(last(B)),B.l10,'очков в 10 последних матчах')):'';
  const body=(A.axes&&B.axes&&A.lg===B.lg?radar(AX,A.axes,B.axes,ea+esc(A.name),eb+esc(B.name),'Сильные стороны'):'')
  +group('Сезон',[tiles([['Очки за матч',pg(A,'pts'),pg(B,'pts'),{d:2}],['Забивает за матч',pg(A,'gf'),pg(B,'gf'),{d:2}],['Пропускает за матч',pg(A,'ga'),pg(B,'ga'),{d:2,low:1}]]),
    row('Победы, %',A.gp?A.w/A.gp*100:null,B.gp?B.w/B.gp*100:null),FB?row('Ничьи',A.d,B.d,{flat:1}):'',FB?row('Поражения',A.l,B.l,{low:1}):'',row('Матчей сыграно',A.gp,B.gp,{flat:1})])
  +group('Дом и выезд',[venue(),row('Голов в матче в среднем',A.tr&&A.tr.tot,B.tr&&B.tr.tot,{d:2,flat:1})])
  +group('Форма',[form])
  +(A.axes&&B.axes&&A.lg===B.lg?group('Сильные стороны по цифрам, 0–100 в своей лиге',AX.map((n,i)=>row(n,A.axes[i],B.axes[i]))):'')
  +(FB?fbNext():`<section class="cmp-g"><h2><span>Очные встречи в сезоне</span></h2>${h2h.length?`<p class="cmp-note">${esc(A.name)} — ${wa} ${wa===1?'победа':wa>=2&&wa<=4?'победы':'побед'}, ${esc(B.name)} — ${h2h.length-wa}.</p><ul class="cmp-h2h">${h2h.reverse().map(m=>{const u=link(m),inner=`<time>${ddmm(m.d)}</time><span>${esc(TT[m.h].name)}${em(m.h,24)}</span><b>${m.sh}:${m.sa}${m.x?' <small>'+esc(m.x)+'</small>':''}</b><span>${em(m.w,24)}${esc(TT[m.w].name)}</span>`;return `<li>${u?`<a href="${esc(u)}">${inner}</a>`:`<div>${inner}</div>`}</li>`}).join('')}</ul>`
     :`<p class="cmp-note">${A.lg===B.lg?'В этом сезоне ещё не играли.':'Клубы из разных лиг — между собой не играют.'}</p>`}
   ${next?`<p class="cmp-note">Следующая встреча — ${ddmm(next.d)} в ${esc(next.d.slice(11))} МСК, ${next.h?esc(A.name):esc(B.name)} дома.</p>`:''}</section>`);
  const subt=t=>`${esc(LGN[t.lg]||'')}${t.conf?' · '+esc(t.conf):''}, ${t.place}-е место`;
  return head(a,b,A.name,B.name,subt(A),subt(B),em(a,72),em(b,72),TEAMURL(a),TEAMURL(b))
   +verdict(body,A.name,B.name)+body+(A.lg!==B.lg?'<p class="cmp-note">Оба клуба играют в Лиге чемпионов. Оценки 0–100 считаются внутри своей лиги, поэтому для клубов из разных лиг их не показываем.</p>':'')}

function head(a,b,na,nb,sa,sb,ia,ib,ua,ub){
  const side=(n,s,i,u,c)=>`<a class="cmp-side" href="${esc(u)}" style="--c:var(${c})">${i}<b>${esc(n)}</b><small>${s}</small></a>`;
  return `<div class="cmp-head">${side(na,sa,ia,ua,'--ca')}<span aria-hidden="true">—</span>${side(nb,sb,ib,ub,'--cb')}</div>`}

/* ── игроки ── */
const POS={C:'центр',L:'левый нападающий',R:'правый нападающий',D:'защитник',F:'нападающий',G:'вратарь'};
function pstat(P,E){const L=P.log||[],N=L.length,sum=(i,r)=>(r||L).reduce((s,x)=>s+(x[i]||0),0);
  const G=sum(3),A=sum(4),sog=P.ssog!=null?P.ssog:sum(5),toiL=L.filter(x=>x[6]),toi=toiL.length?sum(6,toiL)/toiL.length:(P.ts||null);
  const L5=L.slice(-5),L10=L.slice(-10),H=L.filter(x=>x[2]===1),W=L.filter(x=>x[2]===0),pp=r=>r.length?(sum(3,r)+sum(4,r))/r.length:null;
  const gp=E&&E.gp||N;
  return{N,G,A,P:G+A,ppg:N?(G+A)/N:null,sog:sog||null,shp:sog>=5?G/sog*100:null,spg:sog&&N?sog/N:null,toi,pim:P.spim!=null?P.spim:sum(7),pm:P.spm,
   l5:sum(3,L5)+sum(4,L5),l10:pp(L10),hit:L.filter(x=>x[3]+x[4]>0).length,home:pp(H),away:pp(W),
   p60:toi&&N?(G+A)/(toi*N/3600):null,sk:P.sk||[],L5,
   e:E?{hit:E.hit/gp,blk:E.blk/gp,tk:E.tk,gv:E.gv,fo:E.fon>=20&&E.fo!=null?E.fo*(E.fo<=1?100:1):null,spd:E.spd?E.spd*1.609:null,shot:E.shot?E.shot*1.609:null,bur:E.bur!=null?E.bur/gp:null}:null}}
function playerView(xa,xb,PA,PB,SK){
  const E=x=>x.lg==='nhl'&&SK&&SK.p?SK.p[x.id.split('-')[1]]:null,A=pstat(PA,E(xa)),B=pstat(PB,E(xb)),ta=PA.t,tb=PB.t;
  const img=(P,t)=>`<span class="cmp-ph${P.img?'':' nop'}">${P.img?`<img src="${esc(JV_KPH(P.img))}" alt="" width="96" height="96" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentNode.classList.add('nop');this.remove()">`:''}${em(t,30)}</span>`;
  const sub=(P,t)=>`${esc((TT[t]||{}).name||t)} · ${esc(POS[P.pos]||'')}${P.no?' · №'+P.no:''}`;
  const url=x=>'player.html?lg='+x.lg+'&id='+x.id.split('-')[1];
  /* форма игрока: 5 последних матчей столбиками, высота — очки в матче */
  const mx=Math.max(1,...A.L5.concat(B.L5).map(r=>r[3]+r[4]));
  const cols=S=>`<span class="cmp-cols">${S.L5.map(r=>{const v=r[3]+r[4];return `<i class="${v?'':'z'}" style="--h:${Math.round(v/mx*100)}%" title="${esc(ddmm(r[0])+' '+((TT[r[1]]||{}).name||r[1])+': '+r[3]+'+'+r[4])}"><b>${v}</b><small>${ddmm(r[0])}</small></i>`}).join('')}</span>`;
  const e=(k)=>[A.e?A.e[k]:null,B.e?B.e[k]:null];
  const names=A.sk.map(s=>s[0]),skv=(S,n)=>{const f=S.sk.find(s=>s[0]===n);return f?f[1]:null};
  const body=(names.length&&B.sk.length?radar(names,names.map(n=>skv(A,n)),names.map(n=>skv(B,n)),em(ta,22)+esc(PA.n),em(tb,22)+esc(PB.n),'Оценки игрока'):'')
  +group('Сезон',[tiles([['Очки (гол + пас)',A.P,B.P],['Голы',A.G,B.G],['Передачи',A.A,B.A]]),row('Очков за матч',A.ppg,B.ppg,{d:2}),
    row('Матчей',A.N,B.N,{flat:1}),row('Матчей с очками',A.hit,B.hit),row('Плюс-минус',A.pm,B.pm,{f:x=>(x>0?'+':x<0?'−':'')+Math.abs(x)}),row('Штраф, мин',A.pim,B.pim,{low:1})])
  +group('Броски и время',[row('Броски в створ',A.sog,B.sog),row('Бросков за матч',A.spg,B.spg,{d:1}),row('Реализация бросков, %',A.shp,B.shp,{d:1}),
    row('Время на льду за матч',A.toi,B.toi,{f:mmss}),row('Очков за 60 минут',A.p60,B.p60,{d:2})])
  +group('Форма',[A.L5.length&&B.L5.length?panels(win(A.l5,B.l5),fpanel('a',em(ta,22),PA.n,cols(A),A.l5,'очков за 5 последних матчей'),fpanel('b',em(tb,22),PB.n,cols(B),B.l5,'очков за 5 последних матчей')):'',
    row('Очков за матч в 10 последних',A.l10,B.l10,{d:2}),row('Дома: очков за матч',A.home,B.home,{d:2}),row('В гостях: очков за матч',A.away,B.away,{d:2})])
  +(A.e||B.e?group('Игра без шайбы и скорость (НХЛ)',[row('Силовых приёмов за матч',...e('hit'),{d:1}),row('Блоков за матч',...e('blk'),{d:1}),row('Отборов за сезон',...e('tk')),
    row('Потерь за сезон',...e('gv'),{low:1}),row('Вбрасывания, %',...e('fo'),{d:1}),row('Макс. скорость, км/ч',...e('spd'),{d:1}),row('Самый сильный бросок, км/ч',...e('shot'),{d:1}),row('Рывков за матч',...e('bur'),{d:1})]):'')
  +(names.length&&B.sk.length?group('Оценки по цифрам, 0–100 в своей лиге',names.map(n=>row(n,skv(A,n),skv(B,n)))):'')
  +(xa.lg!==xb.lg?'<p class="cmp-note">Игроки из разных лиг: уровень соперников разный, оценки считаются внутри своей лиги.</p>':'');
  return head(ta,tb,PA.n,PB.n,sub(PA,ta),sub(PB,tb),img(PA,ta),img(PB,tb),url(xa),url(xb))+verdict(body,PA.n,PB.n)+body}

/* ── выбор и адрес ── */
const HINT={clubs:[FB?'Арсенал, Зенит…':'СКА, Каролина…','Клуб'],players:['McDavid, Rempal…','Игрок']};
function setUrl(){const q=new URLSearchParams();q.set('t',st.t);if(st.a)q.set('a',st.a);if(st.b)q.set('b',st.b);history.replaceState(null,'','?'+q)}
function defaults(L){
  if(st.t==='clubs'){const g=TT,k=Object.keys(g).filter(x=>g[x].lg===(FB?'epl':'khl')).sort((x,y)=>g[x].place-g[y].place||g[y].pts-g[x].pts);return[k[0]||'',k[1]||'']}
  const top=L.slice().sort((x,y)=>y.pts-x.pts);return[(top[0]||{}).id||'',(top[1]||{}).id||'']}
async function render(){
  document.querySelectorAll('.cmp-tabs button').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.t===st.t)));
  ['a','b'].forEach(s=>{$('cmp-'+s).placeholder=HINT[st.t][0];$('cmp-'+s).previousElementSibling.textContent=HINT[st.t][1]+(s==='a'?' первый':' второй')});
  const L=await list(),by=id=>L.find(x=>x.id===id);
  if(!by(st.a)||!by(st.b)||st.a===st.b){const d=defaults(L);if(!by(st.a))st.a=d[0]===st.b?d[1]:d[0];if(!by(st.b)||st.a===st.b)st.b=d[1]===st.a?d[0]:d[1]}
  if(st.t==='clubs'&&by(st.a)&&!pairOk(st.a,st.b))st.b=mate(st.a);   /* другая лига — ставим соперника из лиги первого клуба */
  const xa=by(st.a),xb=by(st.b);$('cmp-a').value=xa?xa.n:'';$('cmp-b').value=xb?xb.n:'';setUrl();
  if(!xa||!xb){OUT.innerHTML='<p class="cmp-note">Данные не загрузились. Обновите страницу.</p>';return}
  if(st.t==='clubs'){paint(xa.id,xb.id);OUT.innerHTML=clubView(xa.id,xb.id);return}
  OUT.innerHTML='<p class="cmp-note">Загружаем игроков…</p>';const tk=st.a+'|'+st.b;
  const pu=x=>'data/pp/'+x.lg+'/'+x.id.split('-')[1]+'.json';
  const[PA,PB,SK]=await Promise.all([jget(pu(xa)),jget(pu(xb)),xa.lg==='nhl'||xb.lg==='nhl'?jget('data/nhl_skills.json'):null]);
  if(tk!==st.a+'|'+st.b||st.t!=='players')return;
  if(PA&&PB)paint(PA.t,PB.t);
  OUT.innerHTML=PA&&PB?playerView(xa,xb,PA,PB,SK):'<p class="cmp-note">Профиль игрока не загрузился. Выберите другого.</p>'}

function picker(s){const inp=$('cmp-'+s),ul=$('cmp-r'+s);let cur=[];
  const close=()=>{ul.hidden=true;ul.innerHTML=''};
  const show=async all=>{const q=all===true?'':inp.value.trim().toLowerCase(),   /* по нажатию — весь список, по вводу — поиск */
    L=await list(),other=st[s==='a'?'b':'a'];
    cur=L.filter(x=>x.id!==other&&(st.t!=='clubs'||s==='a'||pairOk(st.a,x.id))&&(!q||x.n.toLowerCase().includes(q)||((TT[x.t]||{}).name||'').toLowerCase().includes(q)));
    if(st.t==='players')cur.sort((x,y)=>y.pts-x.pts);cur=cur.slice(0,st.t==='clubs'&&!q?60:12);
    ul.innerHTML=cur.length?cur.map((x,i)=>`<li><button type="button" data-i="${i}">${em(x.t,22)}<span>${esc(x.n)}</span><small>${st.t==='players'?esc((TT[x.t]||{}).name||'')+' · '+x.pts+' оч.':LGN[x.lg]}</small></button></li>`).join(''):'<li class="none">Не нашли</li>';ul.hidden=false};
  inp.addEventListener('focus',()=>{inp.select();show(true)});inp.addEventListener('input',show);
  inp.addEventListener('keydown',e=>{if(e.key==='Escape'){close();inp.blur()}if(e.key==='Enter'&&cur[0]){st[s]=cur[0].id;close();inp.blur();render()}});
  ul.addEventListener('mousedown',e=>e.preventDefault());
  ul.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;st[s]=cur[+b.dataset.i].id;close();inp.blur();render()});
  inp.addEventListener('blur',()=>setTimeout(()=>{close();render()},120))}
picker('a');picker('b');
if(FB)document.querySelector('.cmp-tabs').hidden=true;
document.querySelector('.cmp-tabs').addEventListener('click',e=>{const b=e.target.closest('button');if(!b||b.dataset.t===st.t)return;st.t=b.dataset.t;st.a=st.b='';render()});
render();
})();
