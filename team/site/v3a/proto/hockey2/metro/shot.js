const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();
for(const [w,h] of [[390,844],[768,1000],[1440,900]]){
 const p=await b.newPage({viewport:{width:w,height:h}});const errs=[];
 p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});p.on('pageerror',e=>errs.push(String(e)));
 await p.goto('http://localhost:8765/proto/hockey2/metro/index.html?now='+(process.env.NOW||'2026-11-07T15:03'));
 await p.waitForTimeout(2600);
 await p.screenshot({path:`shots/first-${w}.png`});
 await p.screenshot({path:`shots/full-${w}.png`,fullPage:true});
 const m=await p.evaluate(()=>{const r=e=>{const b=e.getBoundingClientRect();return [Math.round(b.left),Math.round(b.right)]};
  return {sw:document.documentElement.scrollWidth,iw:innerWidth,h1:r(document.querySelector('h1')),sch:r(document.getElementById('sch')),list:r(document.getElementById('list')),lgs:r(document.getElementById('lgs')),ft:r(document.querySelector('.ft .wrap')),logo:r(document.querySelector('.hd .logo')),
  stations:[...document.querySelectorAll('.st')].map(e=>{const b=e.querySelector('.pill').getBoundingClientRect();return Math.round(b.left)+'-'+Math.round(b.right)}).join(' ')}});
 console.log(w,JSON.stringify(m),errs);
 if(w!==768){await p.click('.st.big .pill');await p.waitForTimeout(500);await p.screenshot({path:`shots/open-${w}.png`,fullPage:true})}
 await p.close()}
await b.close()})();
