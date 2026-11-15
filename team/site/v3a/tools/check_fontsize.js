/* Проверка «текст не мельче 11 px» (подписи; правило сайта). Видимый текст с font-size < 11 px, по страницам из check_padding.js.
   Запуск из team/site/v3a при запущенном python3 -m http.server 8765: node tools/check_fontsize.js [страница-фильтр] [ширины]. */
const {chromium}=require('playwright');const fs=require('fs');
const ONLY=process.argv[2]||'',WS=(process.argv[3]||'390,1440').split(',').map(Number);
const PAGES=eval(fs.readFileSync(__dirname+'/check_padding.js','utf8').match(/const PAGES=(\[[\s\S]*?\]);/)[1]);
(async()=>{const b=await chromium.launch();const agg=new Map();let total=0;
for(const path of PAGES){if(ONLY&&!path.includes(ONLY))continue;
 for(const w of WS){const p=await b.newPage({viewport:{width:w,height:w<500?844:900}});
  await p.goto('http://localhost:8765/'+path,{waitUntil:'networkidle'}).catch(()=>{});await p.waitForTimeout(1200);
  await p.evaluate(async()=>{for(let y=0;y<document.body.scrollHeight;y+=700){scrollTo(0,y);await new Promise(r=>setTimeout(r,40))}scrollTo(0,0)});
  const r=await p.evaluate(()=>{const out=[];const seen=new Set();const sel=e=>{let s=e.tagName.toLowerCase();if(e.classList.length)s+='.'+[...e.classList].slice(0,2).join('.');return s};
   const tw=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;
   while(n=tw.nextNode()){const t=n.textContent.trim();if(!t)continue;const e=n.parentElement;if(!e||seen.has(e))continue;seen.add(e);
    if(e.closest('[aria-hidden="true"],.sr-only,.sr,svg,canvas'))continue;
    if(e.checkVisibility&&!e.checkVisibility({opacityProperty:true,visibilityProperty:true}))continue;
    const fs=parseFloat(getComputedStyle(e).fontSize);const r=e.getBoundingClientRect();if(r.width<2||r.height<2)continue;
    if(fs<10.95)out.push([(e.parentElement?sel(e.parentElement)+' > ':'')+sel(e),fs,t.slice(0,30)])}
   return out});
  for(const [s,fs,t] of r){const k=path.split('?')[0]+' | '+s;const a=agg.get(k)||{n:0,w:new Set(),fs,ex:t};a.n++;a.w.add(w);a.fs=Math.min(a.fs,fs);agg.set(k,a);total++}
  await p.close()}}
for(const [k,a] of [...agg.entries()].sort((x,y)=>y[1].n-x[1].n))console.log(String(a.n).padStart(4),k,'·',a.fs+'px','·',[...a.w].join('/'),'·',a.ex);
console.log('ИТОГО мелкого текста:',total,'мест:',agg.size);await b.close()})();
