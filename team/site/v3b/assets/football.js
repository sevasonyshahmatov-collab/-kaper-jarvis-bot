/* Футбол — ПРИМЕРНЫЕ ДАННЫЕ макета (те же, что в v2: __FTODAY, __FOOTBT; на сайте их подставит build.py).
   Время матчей — от «сейчас», чтобы отсчёт был живым. */
(()=>{
const {esc,f1,plural,ring,two,at,atMs,RM}=JB;
const M=(o,min)=>{o.t=at(min);return o};
const D=[
 M({lg:'laliga',a:'Реал Сосьедад',b:'Бетис',p:'Тотал больше 2,5',k:'1.75',pr:.62,x:[2.45,3.4,2.95],pp:[.40,.27,.33],tb:.62,fa:'WWDLW',fb:'DWLWW',h2h:'2 победы · 2 ничьи · 1 поражение',att:[1.28,1.14],def:[.96,1.12]},280),
 M({lg:'epl',a:'Арсенал',b:'Брентфорд',p:'Победа Арсенала',k:'1.62',pr:.61,x:[1.62,4.0,5.2],pp:[.61,.22,.17],tb:.55,fa:'WWWDW',fb:'LDWLL',h2h:'4 победы · 1 ничья',att:[1.42,.98],def:[.78,1.18]},200),
 M({lg:'seriea',a:'Интер',b:'Фиорентина',p:'Тотал больше 2,5',k:'1.80',pr:.60,x:[1.7,3.9,4.6],pp:[.56,.24,.20],tb:.60,fa:'WDWWL',fb:'WLDDW',h2h:'3 победы · 1 ничья · 1 поражение',att:[1.36,1.08],def:[.84,1.04]},250),
 M({lg:'bundesliga',a:'Байер',b:'Майнц',p:'Победа Байера',k:'1.66',pr:.61,x:[1.66,4.1,4.9],pp:[.61,.21,.18],tb:.58,fa:'WWLWD',fb:'LLDWL',h2h:'3 победы · 2 ничьи',att:[1.38,.92],def:[.86,1.2]},260),
 M({lg:'ligue1',a:'Марсель',b:'Ланс',p:'Прогноз выйдет в канале',k:'—',pr:.54,x:[2.0,3.5,3.8],pp:[.47,.27,.26],tb:.52,fa:'WLWDW',fb:'DWWLD',h2h:'2 победы · 1 ничья · 2 поражения',att:[1.2,1.06],def:[.98,.94]},290),
 M({lg:'portugal',a:'Бенфика',b:'Брага',p:'Разбор без «ВЫБОР»',k:'—',pr:.58,x:[1.55,4.2,5.6],pp:[.58,.24,.18],tb:.57,fa:'WWDWW',fb:'WDLWD',h2h:'4 победы · 1 поражение',att:[1.4,1.1],def:[.8,1.0]},230)].sort((a,b)=>a.t<b.t?-1:1);
const B={n:284,promised:62.5,got:60.9,
 thr:[[55,824,59.3,56.8,-3.4],[57,512,61.0,58.2,-2.7],[60,284,62.5,60.9,.9],[62,136,64.3,58.8,-2.9],[65,36,67.5,58.3,-3.2]],
 lg:{laliga:[45,62.7,71.1],seriea:[38,62.6,68.4],bundesliga:[66,63.2,60.6],epl:[53,61.8,58.5],ligue1:[48,62.3,56.2],portugal:[34,62.5,50.0]},
 power:{epl:0,laliga:-.38,bundesliga:-.48,ligue1:-.56,seriea:-.60,portugal:-.97}};
const LEAGUES=[{id:'epl',name:'АПЛ',full:'Англия'},{id:'laliga',name:'Ла Лига',full:'Испания'},{id:'seriea',name:'Серия А',full:'Италия'},
 {id:'bundesliga',name:'Бундеслига',full:'Германия'},{id:'ligue1',name:'Лига 1',full:'Франция'},{id:'portugal',name:'Португалия',full:'Примейра · разбор без «ВЫБОР»'},
 {id:'ucl',name:'Лига чемпионов',full:'Еврокубок'}];
const LN=Object.fromEntries(LEAGUES.map(l=>[l.id,l]));
const LGI=id=>`../assets/lg/${id}.svg`;
const FC={'Рома':'roma','ПСЖ':'psg','Ман Сити':'mancity','Челси':'chelsea','Бавария':'bayern','Барселона':'barcelona','Реал':'realmadrid','Арсенал':'arsenal','МЮ':'manutd',
 'Атлетико':'atletico','Милан':'milan','Интер':'inter','Боруссия Д':'dortmund','Спортинг':'sporting','Бенфика':'benfica','Порту':'porto','Наполи':'napoli','Ювентус':'juventus','Ливерпуль':'liverpool',
 'Фиорентина':'fiorentina','Байер':'leverkusen','Ланс':'lens','Марсель':'marseille','Бетис':'betis','Майнц':'mainz','Брага':'braga','Брентфорд':'brentford','Реал Сосьедад':'sociedad'};
const crest=n=>FC[n]?`../assets/clubs/${FC[n]}.webp`:LGI('ucl');
const PICK=m=>m.k!=='—'&&m.pr>=.6;
const pc=v=>Math.round(v*100)+'%';
const cnt=id=>D.filter(m=>m.lg===id).length;

/* Прогноз дня */
const best=[...D].filter(PICK).sort((a,b)=>b.pr-a.pr)[0];
const td=document.getElementById('today');
td.innerHTML=`<div class="today-top"><span>Прогноз дня</span><span><img src="${LGI(best.lg)}" alt="">${LN[best.lg].name}, ${best.t.slice(11)} МСК</span></div>
 <div class="pair"><div class="tm"><img src="${crest(best.a)}" alt="">${esc(best.a)}</div>
 <div class="pct"><span class="circ">${Math.round(best.pr*100)}%${ring()}</span><small>по модели</small></div>
 <div class="tm"><img src="${crest(best.b)}" alt="">${esc(best.b)}</div></div>
 <div class="pick"><div><span>ВЫБОР</span><strong>${esc(best.p)}</strong></div><span class="k">${best.k}</span></div>
 <div class="clock"><span id="cl">До стартового свистка</span><b id="cd">—</b></div>
 <p class="sample">Пример данных. Прогноз выходит в канале за 4–5 часов до матча.</p>`;

/* Матчи дня */
const form=s=>`<span class="form">${[...s].map(c=>`<i class="${c==='W'?'w':c==='D'?'d':'l'}" aria-label="${c==='W'?'победа':c==='D'?'ничья':'поражение'}">${c==='W'?'В':c==='D'?'Н':'П'}</i>`).join('')}</span>`;
const ltabs=document.getElementById('ltabs'),ml=document.getElementById('mlist');
ltabs.innerHTML=`<button class="tab" role="tab" aria-selected="true" data-l="all">Все <span class="n">${D.length}</span></button>`+
 LEAGUES.filter(l=>cnt(l.id)).map(l=>`<button class="tab" role="tab" aria-selected="false" data-l="${l.id}"><img src="${LGI(l.id)}" alt="">${l.name} <span class="n">${cnt(l.id)}</span></button>`).join('');
function card(m){const mx=Math.max(...m.pp),pk=PICK(m);
 const rows=[['П1',m.pp[0]],['Х',m.pp[1]],['П2',m.pp[2]],['ТБ 2,5',m.tb]];
 return `<li class="match"><div class="m-top"><span><img src="${LGI(m.lg)}" alt="">${LN[m.lg].name}</span><time>${m.t.slice(11)} МСК</time></div>
 <div class="m-teams"><div><img src="${crest(m.a)}" alt="">${esc(m.a)}</div><div><img src="${crest(m.b)}" alt="">${esc(m.b)}</div></div>
 <div class="m-cd" data-t="${m.t}"></div>
 <div class="bars">${rows.map(([k,v],j)=>`<div class="bar${(j<3&&v===mx)||(j===3&&v>=.6)?' top':''}"><span>${k}</span><em><i style="--w:${v.toFixed(2)}"></i></em><b>${pc(v)}</b></div>`).join('')}</div>
 <div class="m-foot"><span class="m-pick">${esc(m.p)}${m.k!=='—'?`<span class="k">${m.k}</span>`:''}</span>${pk?'<span class="stamp">ВЫБОР</span>':''}</div>
 <button class="more" type="button" aria-expanded="false">Разбор <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="m6 9 6 6 6-6"/></svg></button>
 <div class="m-back"><div><dl>
  <div><dt>Форма, 5 матчей</dt><dd>${esc(m.a)} ${form(m.fa)}</dd><dd>${esc(m.b)} ${form(m.fb)}</dd></div>
  <div><dt>Личные встречи, 5 последних</dt><dd>${esc(m.h2h)}</dd></div>
  <div><dt>Наносит / допускает (1 — средний уровень лиги)</dt><dd>${f1(m.att[0],2)} / ${f1(m.def[0],2)} и ${f1(m.att[1],2)} / ${f1(m.def[1],2)}</dd></div>
  ${m.lg==='portugal'?'<div><dt>Португалия</dt><dd>Только разбор: на проверке модель здесь не прошла.</dd></div>':''}
 </dl></div></div></li>`}
function render(l){const sel=l==='all'?D:D.filter(m=>m.lg===l);ltabs.querySelectorAll('.tab').forEach(t=>t.setAttribute('aria-selected',t.dataset.l===l));
 ml.innerHTML=sel.map(card).join('');ml.querySelectorAll('.more').forEach(b=>b.addEventListener('click',()=>{const c=b.closest('.match'),o=c.classList.toggle('open');b.setAttribute('aria-expanded',o)}));
 if(RM||!('IntersectionObserver' in window))ml.querySelectorAll('.match').forEach(c=>c.classList.add('in'));
 else{const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{rootMargin:'0px 0px -10% 0px'});
  ml.querySelectorAll('.match').forEach((c,i)=>{c.style.transitionDelay='';io.observe(c)})}
 tick()}
ltabs.addEventListener('click',e=>{const t=e.target.closest('.tab');if(t)render(t.dataset.l)});

function tick(){const s=Math.round((atMs(best.t)-Date.now())/1000),cd=document.getElementById('cd');
 if(s>0)cd.textContent=`${two(Math.floor(s/3600))}:${two(Math.floor(s%3600/60))}:${two(s%60)}`;else{document.getElementById('cl').textContent='Матч';cd.textContent=s>-7200?'идёт':'завершён'}
 document.querySelectorAll('.m-cd[data-t]').forEach(e=>{const s=Math.round((atMs(e.dataset.t)-Date.now())/1000),m=Math.floor(s/60);
  e.textContent=s<=0?(s>-7200?'идёт':''):m<60?`через ${m} мин`:`через ${Math.floor(m/60)} ч ${m%60} мин`})}
render('all');setInterval(tick,1000);

/* Лиги и клубы */
document.getElementById('lglist').innerHTML=LEAGUES.map(l=>{const n=cnt(l.id);
 return `<li><a href="#matches" data-l="${l.id}"><img src="${LGI(l.id)}" alt=""><span><b>${l.name}</b><small>${l.full}</small></span>${n?`<span class="n">${n} ${plural(n,'матч','матча','матчей')}</span>`:`<span class="n off">${l.id==='ucl'?'тур — 3 ноября':'сегодня без матчей'}</span>`}</a></li>`}).join('');
document.getElementById('lglist').addEventListener('click',e=>{const a=e.target.closest('a[data-l]');if(a&&cnt(a.dataset.l))render(a.dataset.l)});
const CL=[['Ман Сити','АПЛ'],['Ливерпуль','АПЛ'],['Арсенал','АПЛ'],['Челси','АПЛ'],['МЮ','АПЛ'],['Реал','Ла Лига'],['Барселона','Ла Лига'],['Атлетико','Ла Лига'],
 ['Бавария','Бундеслига'],['Боруссия Д','Бундеслига'],['Интер','Серия А'],['Милан','Серия А'],['Ювентус','Серия А'],['Наполи','Серия А'],['Рома','Серия А'],
 ['ПСЖ','Лига 1'],['Бенфика','Португалия'],['Порту','Португалия'],['Спортинг','Португалия']];
document.getElementById('crests').innerHTML=CL.map(([n,l])=>`<li title="${esc(n)}, ${l}"><img src="${crest(n)}" alt="" loading="lazy">${esc(n)}</li>`).join('');

/* Сила команд */
const TOP=['Ман Сити','Реал','Бавария','Ливерпуль','Барселона','Арсенал','Интер','ПСЖ'];
document.getElementById('order').innerHTML=TOP.map((n,i)=>`<li><span class="no">${i+1}</span><img src="${crest(n)}" alt="">${esc(n)}</li>`).join('');
const LGN={epl:'АПЛ',laliga:'Ла Лига',bundesliga:'Бундеслига',ligue1:'Лига 1',seriea:'Серия А',portugal:'Португалия'};
document.getElementById('power').innerHTML=`<h3>Сила лиг Европы к АПЛ</h3><p class="src" style="margin-top:6px">По матчам еврокубков: разница «атака − оборона», АПЛ — ноль.</p>`+
 Object.entries(B.power).map(([id,v])=>`<div class="cb"><span>${LGN[id]}</span><em><i style="--w:${(1+v/1.2).toFixed(3)}"></i></em><b>${v?f1(v,2).replace('-','−'):'0'}</b></div>`).join('')+`<p class="src">Источник: проверка модели 30.10, предварительно.</p>`;

/* Модель на матче-примере */
const ex=best,AVG=[1.52,1.18],lh=ex.att[0]*ex.def[1]*AVG[0],la=ex.att[1]*ex.def[0]*AVG[1];
document.getElementById('ad').innerHTML=[[ex.a+' наносит',ex.att[0]],[ex.b+' допускает',ex.def[1]],[ex.b+' наносит',ex.att[1],'var(--dim)'],[ex.a+' допускает',ex.def[0],'var(--dim)']]
 .map(([k,v,c])=>`<div class="r"><span>${esc(k)}</span><em><i style="--w:${Math.min(1,v/1.6).toFixed(2)};${c?'--c:'+c:''}"></i></em><b>${f1(v,2)}</b></div>`).join('');
document.getElementById('lam').innerHTML=`<span>Ожидаемые голы</span><b>${f1(lh,2)} : ${f1(la,2)}</b>`;
const fact=n=>n<2?1:n*fact(n-1),pois=(l,k)=>Math.exp(-l)*Math.pow(l,k)/fact(k);
const G=[];for(let i=0;i<5;i++){G[i]=[];for(let j=0;j<5;j++)G[i][j]=pois(lh,i)*pois(la,j)}
const gm=Math.max(...G.flat());
document.getElementById('grid5').innerHTML='<span></span>'+[0,1,2,3,4].map(j=>`<span>${j}</span>`).join('')+
 G.map((r,i)=>`<span>${i}</span>`+r.map((v,j)=>{const h=v/gm*.85+.06;return `<i class="${h>.55?'hot':''}" style="--h:${h.toFixed(2)}" title="${i}:${j}">${Math.round(v*100)}</i>`}).join('')).join('');
const so=document.getElementById('simout');
function sim(n){let h=0,d=0,a=0,o=0;const rp=l=>{let k=0,p=Math.exp(-l),s=p,u=Math.random();while(u>s&&k<12){k++;p*=l/k;s+=p}return k};
 for(let i=0;i<n;i++){const x=rp(lh),y=rp(la);x>y?h++:x===y?d++:a++;if(x+y>2)o++}return [h,d,a,o].map(v=>v/n)}
function show(r){const mx=Math.max(r[0],r[1],r[2]);so.innerHTML=[['П1',r[0]],['Х',r[1]],['П2',r[2]],['ТБ 2,5',r[3]]].map(([k,v],i)=>`<div class="${(i<3&&v===mx)||(i===3&&v>=.55)?'hi':''}"><b>${pc(v)}</b>${k}</div>`).join('')}
let R=sim(10000);show(R);
document.getElementById('again').addEventListener('click',e=>{const b=e.currentTarget;if(RM){R=sim(10000);show(R);return}b.disabled=true;let k=0;const iv=setInterval(()=>{show(sim(700));if(++k>9){clearInterval(iv);R=sim(10000);show(R);b.disabled=false}},70)});
const inv=ex.x.map(k=>1/k),sum=inv.reduce((a,b)=>a+b),line=inv.map(v=>v/sum);
const lg=p=>Math.log(p/(1-p)),ilg=x=>1/(1+Math.exp(-x));
const mi=line.indexOf(Math.max(...line)),mM=R[mi],mL=line[mi],mX=ilg(.45*lg(mM)+.55*lg(mL));
document.getElementById('mix').innerHTML=`<p style="font-size:14px;color:var(--dim)">Исход ${['П1','Х','П2'][mi]} в матче ${esc(ex.a)} — ${esc(ex.b)}:</p>`+
 [['Модель',mM,'var(--dim)'],['Линия рынка',mL,'var(--chalk)'],['Смесь',mX,'var(--mark)']].map(([k,v,c])=>`<div class="r"><span>${k}</span><em><i style="--w:${v.toFixed(2)};--c:${c}"></i></em><b>${pc(v)}</b></div>`).join('')+`<p class="src" style="margin-top:4px">Пример расчёта.</p>`;

/* Порог «ВЫБОР» */
const thr=document.getElementById('thr'),to=document.getElementById('throut'),tn=document.getElementById('thrnote');
function showThr(){const v=+thr.value,row=B.thr.reduce((a,b)=>Math.abs(b[0]-v)<Math.abs(a[0]-v)?b:a),[p,n,pr,got,roi]=row;
 to.innerHTML=`<div><span>ставок</span><b>${n}</b></div><div><span>обещано</span><b>${f1(pr)} %</b></div><div class="${got>=pr-3?'got':'bad'}"><span>зашло</span><b>${f1(got)} %</b></div><div class="${roi>=0?'got':'bad'}"><span>ROI, закрытие</span><b>${roi>0?'+':roi<0?'−':''}${f1(Math.abs(roi))} %</b></div>`;
 tn.textContent=(p!==v?`Ближайший посчитанный порог — ${p} %. `:'')+(p===60?'Наш порог: «зашло» в пределах 3 п. п. от обещанного.':p<60?'Ниже 60 % обещание расходится с результатом.':'Выше 62 % ставок мало, и они хуже.')+' Проверка вслепую, 2025/26.';
 thr.setAttribute('aria-valuetext',`${v} %: ${n} ставок, зашло ${f1(got)} %`)}
thr.addEventListener('input',showThr);showThr();

/* Итоги по лигам */
document.getElementById('lgtab').innerHTML=Object.entries(B.lg).filter(([k])=>k!=='portugal').map(([k,[n,pr,got]])=>`<li><span>${LGN[k]}, ${n}</span><b class="${got<pr?'dn':''}">${f1(pr)} → ${f1(got)} %</b></li>`).join('');

JB.page('football');JB.reveal();
})();
