/* JARVIS v3a — страница «Как считает модель»: живой пример по JV_TODAY / JV_MODEL / JV_LINES (data/*.js). Без сети. */
(()=>{
const q=new URLSearchParams(location.search),sp=q.get('s')==='f'?'f':'h';
const $=s=>document.querySelector(s);
const sw=$('#sw-'+sp);if(sw)sw.setAttribute('aria-current','page');
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const f1=x=>(Math.round(x*1000)/10).toFixed(1).replace('.',',');
const f2=x=>x.toFixed(2).replace('.',','), g1=x=>String(x).replace('.',',');
const SRC={};
const MON=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
const dt=s=>{const m=/^(\d+)-(\d+)-(\d+)[ T](\d+:\d+)/.exec(s||'');return m?`${+m[3]} ${MON[+m[2]-1]}, ${m[4]}`:''};
// время из данных с Z (UTC) — в МСК
const dtz=s=>{const m=/^(\d+)-(\d+)-(\d+)[ T](\d+):(\d+)/.exec(s||'');if(!m)return'';const d=new Date(Date.UTC(+m[1],m[2]-1,+m[3],+m[4],+m[5])+3*36e5);return `${d.getUTCDate()} ${MON[d.getUTCMonth()]}, ${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}`};
const T=window.JV_TODAY||{matches:[]},M=window.JV_MODEL||{},L=window.JV_LINES||{};
const picker=$('#picker'),demo=$('#demo');
if(!picker||!demo)return;

/* сейчас по Москве */
const nowMsk=(()=>{const d=new Date(Date.now()+3*3600e3);return d.toISOString().slice(0,16).replace('T',' ')})();
const isH=m=>m.lg==='khl'||m.lg==='nhl';
const ok=m=>{const l=L[m.key],md=M[m.key];if(!l||!md||!l.p1||!l.p2||md.p1==null||md.p2==null)return false;
  const s=1/l.p1+1/l.p2+(l.x?1/l.x:0);return s>1&&s<1.25};
const start=m=>(L[m.key]&&L[m.key].start)||m.t||'';
let all=(T.matches||[]).filter(m=>(sp==='h')===isH(m)&&ok(m)).sort((a,b)=>start(a)<start(b)?-1:1);
let list=all.filter(m=>start(m)>=nowMsk);
let stale=false;
if(list.length<3){list=all.slice();stale=true}
list=list.slice(0,8);
if(!list.length){demo.innerHTML='<p class="md-empty">Сейчас в данных нет матча с расчётом модели и линией. Пример появится после ближайшего обновления (06:23 и 23:47 МСК).</p>';return}

picker.innerHTML=list.map((m,i)=>`<button type="button" role="tab" aria-selected="${i?'false':'true'}" data-i="${i}">${esc(m.hn)} — ${esc(m.an)}<small>${esc(dt(start(m)))} МСК</small></button>`).join('');
picker.addEventListener('click',e=>{const b=e.target.closest('button[data-i]');if(!b)return;
  picker.querySelectorAll('button').forEach(x=>x.setAttribute('aria-selected',x===b?'true':'false'));draw(list[+b.dataset.i])});
picker.addEventListener('keydown',e=>{if(e.key!=='ArrowRight'&&e.key!=='ArrowLeft')return;
  const bs=[...picker.querySelectorAll('button')],i=bs.indexOf(document.activeElement);if(i<0)return;
  const n=bs[(i+(e.key==='ArrowRight'?1:bs.length-1))%bs.length];n.focus();n.click()});

const pois=(l,k)=>{let r=Math.exp(-l);for(let i=1;i<=k;i++)r*=l/i;return r};

function bar(cls,p,label){return `<div class="md-bar ${cls}"><span><i style="width:${Math.max(1,p*100).toFixed(1)}%"></i></span><output>${f1(p)} %</output></div>`}

function draw(m){
  const md=M[m.key],ln=L[m.key],hk=isH(m);
  const names={p1:m.hn,p2:m.an};
  const outs=[['p1','П1','победа: '+m.hn],...(ln.x&&md.x!=null?[['x','Х','ничья'+(hk?' в основное время':'')]]:[]),['p2','П2','победа: '+m.an]];
  const raw=outs.map(o=>1/ln[o[0]]),sum=raw.reduce((a,b)=>a+b,0),margin=sum-1;
  const fair=raw.map(r=>r/sum);
  const mp=outs.map(o=>md[o[0]]);
  const diffs=outs.map((o,i)=>Math.round((mp[i]-fair[i])*1000)/10);
  let bi=0;diffs.forEach((d,i)=>{if(Math.abs(d)>Math.abs(diffs[bi]))bi=i});
  const big=Math.abs(diffs[bi])>=5;
  const lam=md.lam||null;

  /* 1. ожидаемые голы + распределение Пуассона */
  let h1='';
  if(lam){
    const K=[0,1,2,3,4,5,6],ph=K.map(k=>pois(lam[0],k)),pa=K.map(k=>pois(lam[1],k)),mx=Math.max(...ph,...pa);
    h1=`<div class="md-blk"><h4>Шаг 1. Ожидаемые голы</h4>
      <div class="md-lam"><div><b>${f2(lam[0])}</b><span>${esc(m.hn)}</span></div><div><b>${f2(lam[1])}</b><span>${esc(m.an)}</span></div></div>
      <div class="md-g" role="img" aria-label="Шанс забить 0–6 голов у каждой команды при таких ожидаемых голах">${K.map((k,i)=>`<div><i style="height:${(ph[i]/mx*100).toFixed(0)}%;animation-delay:${i*40}ms"></i><i class="b" style="height:${(pa[i]/mx*100).toFixed(0)}%;animation-delay:${i*40}ms"></i></div>`).join('')}</div>
      <div class="md-gl">${K.map(k=>`<span>${k}</span>`).join('')}</div>
      <div class="md-gh"><em>${esc(m.hn)}</em><em class="b">${esc(m.an)}</em><span>число голов в матче: 0–6</span></div>
      <p>Столбики показывают упрощённый расчёт по Пуассону: например, ${esc(m.hn)} при ${f2(lam[0])} ожидаемого гола забивает ровно два гола с шансом около ${Math.round(pois(lam[0],2)*100)} %. Из таких шансов для обеих команд складываются пары счётов, а из них победа, ничья и тотал.${hk?'':' В футболе добавляется поправка Дикси–Коулса на малые счёты, а сама вероятность смешана с линией рынка.'}</p></div>`;
  }

  /* 2. вероятности модели против линии */
  const rows=outs.map((o,i)=>`<div class="md-row"><b>${o[1]} · ${esc(o[2].replace(/^победа: /,''))}${o[0]==='x'?'':''}</b>
     <div class="md-bars">${bar('m',mp[i])}${bar('l',fair[i])}</div></div>`).join('');
  const diffTxt=outs.map((o,i)=>`${o[1]} ${diffs[i]>0?'+':''}${String(diffs[i]).replace('.',',').replace('-','−')}`).join(' · ');
  const h2=`<div class="md-blk"><h4>Шаг 2. Вероятности: модель и линия</h4>
    <div class="md-cmp">${rows}</div>
    <div class="md-key" style="margin-top:12px"><em>модель</em><em class="l">линия без маржи</em></div>
    <p>Разница модели и линии в процентных пунктах: <span class="md-diff${big?' hi':''}">${diffTxt}</span>. ${big?`Самое большое расхождение: ${outs[bi][1]}, ${String(Math.abs(diffs[bi])).replace('.',',')} п.п. Это разница оценок двух источников, а не сигнал и не совет: модель могла не учесть то, что знает рынок (например, состав в день матча).`:'Расхождения небольшие: модель и линия оценивают матч похоже.'}</p></div>`;

  /* 3. маржа */
  const trs=outs.map((o,i)=>`<tr><td>${o[1]} · ${esc(o[2].replace(/^победа: /,''))}</td><td>${f2(ln[o[0]])}</td><td>${f1(raw[i])} %</td><td>${f1(fair[i])} %</td></tr>`).join('');
  const h3=`<div class="md-blk"><h4>Шаг 3. Как из кэфа получается «вероятность букмекера»</h4>
    <table class="md-calc"><thead><tr><th>Исход</th><th>Кэф</th><th>1 / кэф</th><th>Без маржи</th></tr></thead><tbody>${trs}</tbody>
    <tfoot><tr><td>Сумма</td><td></td><td>${f1(sum)} %</td><td>100,0 %</td></tr></tfoot></table>
    <p>Сначала делим единицу на кэф: так получается «сырая» вероятность. Но сумма по всем исходам вышла <b>${f1(sum)} %</b>, больше ста. Лишние <b>${f1(margin).replace(/^(-?\d+),0$/,'$1')} %</b> и есть маржа букмекера, его заработок заложен в кэфы. Чтобы сравнивать с моделью, каждую долю делим на сумму, и три шанса снова дают 100 %. Линия снята ${esc(dtz(ln.t))} МСК.</p></div>`;

  /* 4. тотал */
  let h4='';
  if(md.totals||md.over!=null){
    const pts=md.totals?Object.keys(md.totals).map(Number).sort((a,b)=>a-b).map(k=>[k,md.totals[String(k)]!=null?md.totals[String(k)]:md.totals[k.toFixed(1)]]):[[md.tot,md.over]];
    const L0=ln.tot!=null?ln.tot:null;
    const all=pts.map(p=>p[0]).concat(L0!=null?[L0]:[]);
    const lo=Math.min(...all),hi=Math.max(...all),pos=v=>hi>lo?(v-lo)/(hi-lo)*100:50;
    const dots=pts.map(([k,p])=>`<i style="left:${pos(k)}%"></i><span style="left:${pos(k)}%">${f1(p)} %<em>больше ${g1(k)}</em></span>`).join('');
    let book='',bt='';
    if(L0!=null&&ln.over&&ln.under){
      const bo=(1/ln.over)/(1/ln.over+1/ln.under),bm=1/ln.over+1/ln.under-1;
      book=`<div class="md-tsl">Линия</div><div class="md-ts l"><i style="left:${pos(L0)}%"></i><span style="left:${pos(L0)}%">${f1(bo)} %<em>больше ${g1(L0)}</em></span></div>`;
      const mo=pts.find(p=>p[0]===L0);
      bt=`<p>У линии на тотал ${g1(L0)} кэфы ${f2(ln.over)} (больше) и ${f2(ln.under)} (меньше). Те же 1 / кэф дают сумму ${f1(1+bm)} %, то есть маржа ${f1(bm)} %, а без неё шанс «больше» ${f1(bo)} %.${mo?` Модель на этой линии даёт ${f1(mo[1])} % (разница ${(mo[1]-bo>=0?'+':'−')+String(Math.abs(Math.round((mo[1]-bo)*1000)/10)).replace('.',',')} п.п.).`:` Модель считала тотал на другой линии (${g1(md.tot)}), поэтому прямое сравнение здесь не получается.`}</p>`;
    }
    h4=`<div class="md-blk"><h4>Тотал голов</h4>
      <div class="md-tsl">Модель: шанс «больше» на разных линиях</div><div class="md-ts">${dots}</div>${book}${bt}
      <p class="note">Чем выше линия, тем меньше шанс «больше»: на шкале видно, как шанс падает при переходе от одной линии к другой.</p></div>`;
  }
  const upd=md.t?`Расчёт модели: ${esc(dtz(md.t))} МСК · версия <code>${esc(String(md.ver||'').split(' ')[0])}</code>`:'';
  demo.innerHTML=`<div class="md-hd"><h3>${esc(m.hn)} — ${esc(m.an)}</h3><span>${esc(dt(start(m)))} МСК · ${esc(({khl:'КХЛ',nhl:'НХЛ',epl:'АПЛ',rpl:'РПЛ',laliga:'Ла Лига',seriea:'Серия А',bundesliga:'Бундеслига',ligue1:'Лига 1',ucl:'Лига чемпионов',uel:'Лига Европы'})[m.lg]||m.lg.toUpperCase())}</span></div>
    ${stale?'<div class="md-warnbox">Ближайших матчей в данных мало, поэтому пример взят на последнем расчёте и матч мог уже начаться. Цифры показаны как иллюстрация расчёта.</div>':''}
    ${h1}${h2}${h3}${h4}<p class="note">${upd}. Это иллюстрация того, как читать цифры, а не рекомендация что-либо делать.</p>`;
}
draw(list[0]);
})();
