const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1350}});
for(let i=1;i<=7;i++){await p.goto('file://'+process.argv[2]+'/car_'+i+'.html');await p.waitForTimeout(400);
await p.evaluate(()=>{const st=document.querySelector('.stage');const cap=document.querySelector('.cap');const card=st.querySelector('.card');
 const hasCap=cap&&cap.textContent.trim();const top=document.querySelector('.t').getBoundingClientRect().bottom+45;const bottom=hasCap?1235:1285;
 st.style.top=top+'px';
 st.style.top=top+'px';card.style.height=(bottom-card.getBoundingClientRect().top)+'px';card.style.display='flex';card.style.flexDirection='column';card.style.justifyContent='space-evenly';
 const g=card.querySelector(':scope>div[style*="grid"]');if(g){g.style.flex='1';g.style.gridAutoRows='1fr';g.querySelectorAll('.row').forEach(r=>r.style.height='auto');}
 card.querySelectorAll(':scope>.row').forEach(r=>{r.style.flex='1';r.style.height='auto';r.style.maxHeight='200px';});
 card.style.fontSize='';document.body.classList.add('big');
 if(hasCap)cap.style.top=(bottom+30)+'px';});
await p.waitForTimeout(200);await p.screenshot({path:process.argv[2]+'/car_'+i+'.jpg',type:'jpeg',quality:93});}await b.close();})();
