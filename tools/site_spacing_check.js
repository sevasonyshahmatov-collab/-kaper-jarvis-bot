/* Проверка отступов сайта v3a (черновик 14.11, задание аудита п. 9).
   Запуск: в team/site/v3a — python3 -m http.server 8765; из корня репозитория — node tools/site_spacing_check.js [порт] [только-страница].
   Ищет: (1) видимый текст ближе 12 px к краю своей плашки (ближайший предок с фоном / рамкой / тенью, уже экрана);
         (2) текст ближе 16 px к краю экрана на телефоне (кроме полос с прокруткой вбок);
         (3) горизонтальную прокрутку страницы; (4) последний блок впритык к подвалу (меньше 32 px).
   Скрипт даёт и ложные срабатывания (значки, «таблетки» кнопок, бегущие строки) — смотреть снимки глазами. */
const {chromium}=require('playwright');
const PORT=process.argv[2]||8765,ONLY=process.argv[3];
const PAGES=[['Главная','index.html'],['Хоккей','hockey/index.html'],['Футбол','football/index.html'],['Лига КХЛ','hockey/league.html?lg=khl'],
 ['Лига АПЛ','football/league.html?lg=epl'],['ЛЧ','football/ucl.html'],['Клуб','team/index.html?id=lokomotiv'],
 ['Профиль хоккеиста','hockey/player.html?lg=nhl&id=8478402'],['Профиль футболиста','football/player.html?id=253989'],
 ['Игроки','hockey/players.html'],['Тренды','hockey/trends.html'],['Сравнение','hockey/compare.html'],['Итоги','results.html'],
 ['Матчи дня','matches.html'],['Матч','khl/2026-11-19-metallurg-traktor/'],['Прогноз','forecast.html'],['Модель','model.html'],
 ['Словарь','glossary.html'],['Таблица','hockey/table.html'],['Мой JARVIS','me/index.html'],['404','404.html']];
const WIDTHS=[360,390,430,768,1440];
(async()=>{
 const b=await chromium.launch();let total=0;const rows=[];
 for(const [name,path] of PAGES){ if(ONLY&&!path.includes(ONLY))continue;
  for(const w of WIDTHS){
   const p=await b.newPage({viewport:{width:w,height:w<500?844:900}});
   await p.goto(`http://localhost:${PORT}/${path}`,{waitUntil:'networkidle'}).catch(()=>{});await p.waitForTimeout(900);
   const r=await p.evaluate(()=>{
    const vw=document.documentElement.clientWidth,out=[];
    const isBox=e=>{const cs=getComputedStyle(e);if(e===document.body||e===document.documentElement)return false;
     const bg=cs.backgroundColor!=='rgba(0, 0, 0, 0)'&&cs.backgroundColor!=='transparent'||cs.backgroundImage!=='none';
     const bd=parseFloat(cs.borderLeftWidth)>0&&cs.borderLeftStyle!=='none'||parseFloat(cs.borderTopWidth)>0&&cs.borderTopStyle!=='none'&&parseFloat(cs.borderBottomWidth)>0;
     const r=e.getBoundingClientRect();return (bg||bd||cs.boxShadow!=='none')&&r.width<vw-2&&r.width>60&&r.height>40};
    const scrollsX=e=>{for(let a=e;a&&a!==document.body;a=a.parentElement){const cs=getComputedStyle(a);if(/auto|scroll/.test(cs.overflowX)&&a.scrollWidth>a.clientWidth+2)return true}return false};
    const skip=e=>e.closest('header,#hd,.tb,.tabbar,nav[aria-label],.jvf-mini,button,.btn,svg,[aria-hidden="true"],.sr,.visually-hidden,select,input,.chip,.pill,.tag,.pp-rk,.open,.tot,.no,.pp-wm,.wm,.marquee,.tick');
    const tw=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;const seen=new Set();
    while(n=tw.nextNode()){const t=n.textContent.trim();if(t.length<2)continue;const e=n.parentElement;if(!e||seen.has(e))continue;seen.add(e);
     if(skip(e))continue;const cs=getComputedStyle(e);if(cs.visibility==='hidden'||!e.offsetParent&&cs.position!=='fixed')continue;
     const rg=document.createRange();rg.selectNodeContents(n);const tr=rg.getBoundingClientRect();if(tr.width<2||tr.height<2)continue;
     if(tr.bottom<0||tr.top>document.documentElement.scrollHeight)continue;
     let box=null;for(let a=e;a&&a!==document.body;a=a.parentElement){if(isBox(a)){box=a;break}}
     const sx=scrollsX(e);
     if(box&&!sx){const br=box.getBoundingClientRect();const csb=getComputedStyle(box);const bl=parseFloat(csb.borderLeftWidth)||0,brr=parseFloat(csb.borderRightWidth)||0;
      const dl=tr.left-br.left-bl,dr=br.right-brr-tr.right;
      // проверяем только левый / правый край: верх и низ у заголовков плашек бывает уже по замыслу
      if(Math.min(dl,dr)<11.5&&tr.width<br.width-4)out.push(['плашка',Math.round(Math.min(dl,dr)),(box.className||box.tagName).toString().slice(0,40),t.slice(0,30)])}
     if(vw<500&&!sx){const d=Math.min(tr.left,vw-tr.right);if(d<15.5&&d>-200)out.push(['экран',Math.round(d),(e.className||e.tagName).toString().slice(0,40),t.slice(0,30)])}
    }
    const hs=document.documentElement.scrollWidth>vw+1;
    const f=document.querySelector('footer');let gap=null;if(f){let prev=f.previousElementSibling;while(prev&&(!prev.offsetHeight||/script|style/i.test(prev.tagName)))prev=prev.previousElementSibling;
     if(prev)gap=Math.round(f.getBoundingClientRect().top-prev.getBoundingClientRect().bottom)}
    return {out,hs,gap}});
   const uniq=[...new Map(r.out.map(x=>[x[0]+x[2]+x[3],x])).values()];
   total+=uniq.length+(r.hs?1:0)+(r.gap!=null&&r.gap<32?1:0);
   rows.push(`${name} ${w}: ${uniq.length} мест${r.hs?', ГОРИЗ. ПРОКРУТКА':''}${r.gap!=null&&r.gap<32?`, до подвала ${r.gap} px`:''}`);
   uniq.slice(0,12).forEach(x=>rows.push(`   ${x[0]} ${x[1]}px  [${x[2]}]  «${x[3]}»`));
   await p.close()}}
 console.log(rows.join('\n'));console.log('ИТОГО мест:',total);await b.close()})();
