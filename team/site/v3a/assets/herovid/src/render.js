// Сборка роликов-эскизов: node render.js  (нужен локальный сервер на 8765 из корня репозитория, Playwright и ffmpeg)
const {chromium}=require('playwright');const {spawn}=require('child_process');const path=require('path');
const OUT=path.join(__dirname,'..'),N=192,FPS=24;
(async()=>{const br=await chromium.launch();const p=await br.newPage({viewport:{width:1300,height:740}});
await p.goto('http://localhost:8765/team/site/v3a/assets/herovid/src/render.html');await p.evaluate(()=>window.ready);
const ONLY=process.argv.slice(2);   // например: node render.js football-1 hockey-4
for(const sp of ['hockey','football'])for(const v of [1,2,3,4]){if(ONLY.length&&!ONLY.includes(sp+'-'+v))continue;
 const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(FPS),'-c:v','mjpeg','-i','-','-c:v','libx264','-pix_fmt','yuv420p','-crf','27','-preset','slow','-movflags','+faststart','-an',path.join(OUT,`${sp}-${v}.mp4`)]);
 const done=new Promise(ok=>ff.on('close',ok));ff.stderr.on('data',d=>process.stderr.write(d));
 for(let i=0;i<N;i++){const d=await p.evaluate(([v,sp,t])=>window.draw(v,sp,t),[v,sp,i/N]);const b=Buffer.from(d.split(',')[1],'base64');
  if(i===Math.round(N*({1:.42,2:.62,3:.72,4:.3})[v]))require('fs').writeFileSync(path.join(OUT,`${sp}-${v}.jpg`),b);
  if(!ff.stdin.write(b))await new Promise(ok=>ff.stdin.once('drain',ok))}
 ff.stdin.end();await done;console.log(sp,v,'ok')}
await br.close()})();
