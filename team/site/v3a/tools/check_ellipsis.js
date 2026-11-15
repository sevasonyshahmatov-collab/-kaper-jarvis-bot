/* Проверка «текст обрезан троеточием» (владелец: названия команд целиком, без «Шанхайские Дра…»).
   Ищет видимые элементы с text-overflow: ellipsis, у которых текст не помещается (scrollWidth > clientWidth),
   и строки, обрезанные line-clamp. Страницы — те же, что в check_padding.js. Запуск из team/site/v3a при запущенном
   python3 -m http.server 8765: node tools/check_ellipsis.js [страница-фильтр] [ширины через запятую]. */
const {chromium}=require('playwright');
const fs=require('fs');
const ONLY=process.argv[2]||'',WS=(process.argv[3]||'360,390,430,768,1440').split(',').map(Number);
const src=fs.readFileSync(__dirname+'/check_padding.js','utf8');
const PAGES=eval(src.match(/const PAGES=(\[[\s\S]*?\]);/)[1]);
(async()=>{const b=await chromium.launch();const agg=new Map();let total=0;
for(const path of PAGES){if(ONLY&&!path.includes(ONLY))continue;
 for(const w of WS){const p=await b.newPage({viewport:{width:w,height:w<500?844:900}});
  await p.goto('http://localhost:8765/'+path,{waitUntil:'networkidle'}).catch(()=>{});await p.waitForTimeout(1200);
  await p.evaluate(async()=>{for(let y=0;y<document.body.scrollHeight;y+=700){scrollTo(0,y);await new Promise(r=>setTimeout(r,40))}scrollTo(0,1500)});   /* остаться ниже первого экрана: так видна липкая шапка с названием клуба */
  await p.evaluate(()=>document.querySelectorAll('[data-rv]').forEach(e=>e.classList.add('in')));await p.waitForTimeout(600);
  const r=await p.evaluate(()=>{const out=[];const sel=e=>{let s=e.tagName.toLowerCase();if(e.classList.length)s+='.'+[...e.classList].slice(0,2).join('.');return s};
   for(const e of document.querySelectorAll('body *')){const c=getComputedStyle(e);
    const ell=c.textOverflow==='ellipsis'&&e.scrollWidth>e.clientWidth+1;
    const clamp=c.webkitLineClamp&&c.webkitLineClamp!=='none'&&e.scrollHeight>e.clientHeight+2;
    if(!ell&&!clamp)continue;if(!e.textContent.trim())continue;
    if(e.closest('[aria-hidden="true"],.sr-only,.tick,.marquee,.tkr'))continue;
    if(e.checkVisibility&&!e.checkVisibility({opacityProperty:true,visibilityProperty:true}))continue;
    const r=e.getBoundingClientRect();if(r.width<2||r.height<2)continue;
    out.push([(e.parentElement?sel(e.parentElement)+' > ':'')+sel(e),ell?'троеточие':'обрезка строк',e.textContent.trim().slice(0,40)])}
   return out});
  for(const [s,why,t] of r){const k=path.split('?')[0]+' | '+s;const a=agg.get(k)||{n:0,w:new Set(),ex:new Set(),why};a.n++;a.w.add(w);if(a.ex.size<3)a.ex.add(t);agg.set(k,a);total++}
  await p.close()}}
for(const [k,a] of [...agg.entries()].sort((x,y)=>y[1].n-x[1].n))console.log(String(a.n).padStart(4),k,'·',a.why,'·',[...a.w].join('/'),'·',[...a.ex].join(' | '));
console.log('ИТОГО обрезок:',total,'мест:',agg.size);await b.close()})();
