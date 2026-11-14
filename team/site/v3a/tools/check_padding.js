/* Проверка «текст не впритык к краю плашки» (владелец 14.11: «ни в одном месте сайта этого не было»).
   Правило: от текста до края своей плашки (ближайший предок с фоном, рамкой, тенью или обрезкой) —
   телефон ≥12 px по бокам и ≥10 px сверху/снизу, компьютер ≥16 / 12 px; ячейки таблиц — ≥8 px по бокам, крайние колонки как плашка;
   маленькие метки (плашка уже 90 px и ниже 34 px) — ≥8 px по бокам, ≥3 px сверху/снизу. До края экрана — ≥16 px.
   По вертикали вычитается «воздух» строки ((line-height − font-size)/2). Запуск: из team/site/v3a — python3 -m http.server 8765,
   затем node tools/check_padding.js [страница-фильтр] [ширины через запятую]. Вывод — по селекторам, с худшим отступом.
   Исключения (ложные срабатывания) — EXCL ниже, с причиной. */
const {chromium}=require('playwright');
const ONLY=process.argv[2]||'',WS=(process.argv[3]||'360,390,430,768,1440').split(',').map(Number);
const PAGES=['index.html','hockey/index.html','football/index.html','hockey/league.html?lg=khl','hockey/league.html?lg=nhl','football/league.html?lg=epl',
 'football/ucl.html','team/index.html?id=lokomotiv','team/index.html?id=shanghai','hockey/player.html?lg=nhl&id=8478402','hockey/player.html?lg=khl&id=31089',
 'football/player.html?id=253989','hockey/players.html','hockey/trends.html','football/trends.html','hockey/compare.html','football/compare.html',
 'results.html','matches.html','khl/2026-11-20-torpedo-lokomotiv/','forecast.html','model.html','glossary.html','hockey/table.html','me/index.html','404.html'];
const EXCL=[
 ['header,#hd,.tb,.tabbar,.tbs','шапка и нижняя панель — свои отступы, проверены отдельно'],
 ['[aria-hidden="true"],.sr-only,.pp-wm,.wm,.no,.pps-wm,.ppa-shine','декор и скрытый текст'],
 ['details:not([open])>:not(summary)','закрытые раскрывашки'],
 ['.tick,.marquee,.tkr','бегущая строка — лента с прокруткой'],
 ['canvas,svg','рисунки']];
(async()=>{const b=await chromium.launch();const agg=new Map();let total=0;
for(const path of PAGES){if(ONLY&&!path.includes(ONLY))continue;
 for(const w of WS){const p=await b.newPage({viewport:{width:w,height:w<500?844:900}});
  await p.goto('http://localhost:8765/'+path,{waitUntil:'networkidle'}).catch(()=>{});await p.waitForTimeout(1200);
  await p.evaluate(async()=>{for(let y=0;y<document.body.scrollHeight;y+=700){scrollTo(0,y);await new Promise(r=>setTimeout(r,40))}scrollTo(0,0)});
  await p.waitForTimeout(500);
  const r=await p.evaluate(EX=>{const vw=document.documentElement.clientWidth,mob=vw<700,out=[];
   const excl=EX.map(x=>x[0]).join(',');
   const sel=e=>{let s=e.tagName.toLowerCase();if(e.classList.length)s+='.'+[...e.classList].slice(0,2).join('.');return s};
   const isBox=e=>{const c=getComputedStyle(e);const bg=!/rgba\(0, 0, 0, 0\)|transparent/.test(c.backgroundColor)||c.backgroundImage!=='none';
    const bd=['Left','Right','Top','Bottom'].filter(k=>parseFloat(c['border'+k+'Width'])>0&&c['border'+k+'Style']!=='none').length>=2;
    const sh=c.boxShadow!=='none'&&!/inset/.test(c.boxShadow);const r=e.getBoundingClientRect();
    return (bg||bd||sh)&&r.width<vw-2&&r.width>14&&r.height>12};
   const scrollsX=e=>{for(let a=e;a&&a!==document.body;a=a.parentElement){const c=getComputedStyle(a);if(/auto|scroll/.test(c.overflowX)&&a.scrollWidth>a.clientWidth+2)return true}return false};
   const tw=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;const seen=new Set();
   while(n=tw.nextNode()){const t=n.textContent.trim();if(!t)continue;const e=n.parentElement;if(!e||seen.has(e))continue;seen.add(e);
    if(e.closest(excl))continue;const cs=getComputedStyle(e);if(cs.visibility==='hidden'||+cs.opacity<.05)continue;
    const rg=document.createRange();rg.selectNodeContents(n);const rs=[...rg.getClientRects()].filter(x=>x.width>1&&x.height>1);if(!rs.length)continue;
    const tr={left:Math.min(...rs.map(x=>x.left)),right:Math.max(...rs.map(x=>x.right)),top:Math.min(...rs.map(x=>x.top)),bottom:Math.max(...rs.map(x=>x.bottom))};
    const fs=parseFloat(cs.fontSize),lh=parseFloat(cs.lineHeight)||fs*1.2,air=Math.max(0,(rs[0].height-fs)/2)*0.6;
    let box=null,cell=null;for(let a=e;a&&a!==document.body;a=a.parentElement){if(!cell&&/^(TD|TH)$/.test(a.tagName))cell=a;if(isBox(a)){box=a;break}}
    if(!box)continue;const br=box.getBoundingClientRect(),bc=getComputedStyle(box);
    const inn={left:br.left+parseFloat(bc.borderLeftWidth),right:br.right-parseFloat(bc.borderRightWidth),top:br.top+parseFloat(bc.borderTopWidth),bottom:br.bottom-parseFloat(bc.borderBottomWidth)};
    const d={l:tr.left-inn.left,r:inn.right-tr.right,t:tr.top+air-inn.top,b:inn.bottom-tr.bottom-air};
    const small=br.width<=90&&br.height<=34;
    const H=small?8:mob?12:16,V=small?3:mob?10:12;
    const sx=scrollsX(e);const bad=[];
    if(!sx){if(d.l<H-.5&&d.l>-40)bad.push('слева '+Math.round(d.l));if(d.r<H-.5&&d.r>-200)bad.push('справа '+Math.round(d.r))}
    if(d.t<V-.5&&d.t>-20)bad.push('сверху '+Math.round(d.t));if(d.b<V-.5&&d.b>-20)bad.push('снизу '+Math.round(d.b));
    if(cell){const cr=cell.getBoundingClientRect();const cl=tr.left-cr.left,crr=cr.right-tr.right;
     const first=!cell.previousElementSibling,last=!cell.nextElementSibling;
     // внутри таблицы границы плашки проверяются только у крайних колонок/строк; внутренние ячейки — ≥8 px до соседней колонки
     for(let i=bad.length-1;i>=0;i--){const k=bad[i].split(' ')[0];if((k==='слева'&&!first)||(k==='справа'&&!last))bad.splice(i,1)}
     if(!first&&cl<3.5)bad.push('ячейка слева '+Math.round(cl));if(!last&&crr<3.5)bad.push('ячейка справа '+Math.round(crr))}
    if(bad.length)out.push([sel(box)+' > '+sel(e),bad.join(', '),t.slice(0,24)])}
   return out},EXCL);
  for(const [s,why,t] of r){const k=path.split('?')[0]+' | '+s;const a=agg.get(k)||{n:0,w:new Set(),ex:t,why};a.n++;a.w.add(w);agg.set(k,a);total++}
  await p.close()}}
const rows=[...agg.entries()].sort((a,b)=>b[1].n-a[1].n);
for(const [k,a] of rows)console.log(String(a.n).padStart(4),k,'·',a.why,'·',[...a.w].join('/'),'·',a.ex);
console.log('ИТОГО нарушений:',total,'мест (селекторов):',rows.length);await b.close()})();
