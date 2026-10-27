const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});
for(let i=1;i<=7;i++){await p.goto('file://'+process.argv[2]+'/table_'+i+'.html');await p.waitForTimeout(500);await p.screenshot({path:process.argv[2]+'/table_'+i+'.jpg',type:'jpeg',quality:93});}await b.close();})();
