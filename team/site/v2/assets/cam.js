/* JARVIS v2 — движок «камеры-путешествия» (docs/handoff/SITE_V2_CAMERA.md, п. 1–2).
 *
 * Разметка:
 *   <div id="stage"><div class="scene" data-seg="F2" data-video="../assets/football/F2" data-video-back="../assets/football/F2_back"
 *        data-poster="../assets/football/F2.webp" data-move="push" [data-loop data-rate="0.3"]></div> … <div class="veil"></div></div>
 *   <section data-seg="F2" data-veil=".3"> … </section>        — раздел поверх; его прокрутка = прогресс отрезка F2
 *
 * Ролики (подхватываются сами, код не трогать): <data-video>.mp4 — компьютер (scrub: кадр = прогресс секции; кодировать
 * «каждый кадр ключевой»), <data-video-back>.mp4 — обратный путь (тот же отрезок, камера развёрнута; начало = конец прямого),
 * <data-video>_m.mp4 — телефон, только петли (data-loop). Нет файла — постер с наездом/панорамой transform-ом.
 *
 * Режимы (html[data-cam]): scrub — компьютер; lite — телефон <768 px или экономия трафика (постеры, петли, наплыв, без scrub);
 * still — «уменьшить движение» (постеры, без движения, смена без наплыва).
 */
(()=>{
 const stage=document.getElementById('stage');if(!stage)return;
 const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
 const conn=navigator.connection||{};
 // телефон тоже получает полёт по прокрутке (владелец 31.10); облегчённый режим — только экономия трафика / медленная сеть
 const MODE=RM?'still':(conn.saveData||/(^|-)2g|3g/.test(conn.effectiveType||''))?'lite':'scrub';
 document.documentElement.dataset.cam=MODE;
 const scenes=[...stage.querySelectorAll('.scene[data-seg]')];
 const veil=stage.querySelector('.veil');
 const secs=[...document.querySelectorAll('main [data-seg]')];
 const cap=document.getElementById('camcap');
 const clamp=(v,a,b)=>v<a?a:v>b?b:v;

 // постеры: прямой и «обратный» (зеркальный, пока нет ролика обратного пути)
 const S=scenes.map((el,i)=>{
  const rig=document.createElement('div');rig.className='rig';
  const f=document.createElement('div');f.className='pic fwd';
  const b=document.createElement('div');b.className='pic back mirror';
  const poster=el.dataset.poster;if(poster){f.style.backgroundImage=b.style.backgroundImage=`url("${poster}")`}
  rig.append(f,b);el.append(rig);
  return {el,i,id:el.dataset.seg,rig,f,b,loop:el.hasAttribute('data-loop'),rate:+el.dataset.rate||1,move:el.dataset.move||'push',
   v:null,vb:null,tried:false,sp:0,t:0,tb:0,
   journey:el.hasAttribute('data-journey'),table:el.dataset.table?JSON.parse(el.dataset.table):null};
 });
 const byId=Object.fromEntries(S.map(s=>[s.id,s]));

 function mkVideo(src,loop,onok){
  const v=document.createElement('video');
  v.muted=true;v.defaultMuted=true;v.playsInline=true;v.setAttribute('playsinline','');v.setAttribute('muted','');
  v.preload='auto';v.loop=!!loop;v.disablePictureInPicture=true;v.setAttribute('aria-hidden','true');
  v.addEventListener('loadeddata',()=>onok(v),{once:true});
  // запасной адрес: если просмотрщик (raw.githack) не отдал ролик — берём его прямо с GitHub
  let alt=null;if(/^https:\/\/raw\.githack\.com\//.test(location.href))
   alt=new URL(src,location.href).href.replace('https://raw.githack.com/','https://raw.githubusercontent.com/');
  if(loop){
   v.addEventListener('error',()=>{if(alt&&v.src!==alt){v.src=alt;v.load()}else v.remove()});
   v.src=src;return v;
  }
  // ролик прокрутки грузим целиком в память: перемотка (currentTime) работает и там, где сервер не отдаёт файл
  // кусками (Range) — иначе браузер не может прыгать по кадрам и стоит первый кадр (так было на raw.githack)
  const get=u=>fetch(u).then(r=>{if(!r.ok)throw new Error(r.status);return r.blob()});
  get(src).catch(e=>{if(alt)return get(alt);throw e})
   .then(bl=>{v.src=URL.createObjectURL(bl)}).catch(()=>v.remove());
  return v;
 }
 // ролики грузим только для текущего отрезка и соседей
 function want(s){
  if(!s||s.tried||MODE==='still')return;s.tried=true;
  const base=s.el.dataset.video;if(!base)return;
  if(s.journey){
   // весь путь — один ролик: сначала лёгкий (быстро стартует), потом полное качество 1080p подменяет его без скачка
   s.f.append(mkVideo(base+'_lo.mp4',false,v=>{if(s.v)return;s.v=v;v.pause();s.f.classList.add('vid');
    const hi=mkVideo(base+'.mp4',false,h=>{h.pause();h.currentTime=v.currentTime;
     h.addEventListener('seeked',()=>{s.f.append(h);s.v=h;h.style.opacity=1;setTimeout(()=>v.remove(),500)},{once:true})});
    hi.style.opacity=0}));
   return;
  }
  if(MODE==='lite'){
   if(!s.loop)return;
   s.f.append(mkVideo(base+'_m.mp4',true,v=>{s.v=v;s.f.classList.add('vid');v.playbackRate=s.rate;sync()}));
   return;
  }
  s.f.append(mkVideo(base+'.mp4',s.loop,v=>{s.v=v;s.f.classList.add('vid');if(s.loop)v.playbackRate=s.rate;else v.pause();sync()}));
  const back=s.el.dataset.videoBack;
  if(back&&!s.loop)s.b.append(mkVideo(back+'.mp4',false,v=>{s.vb=v;v.pause();s.b.classList.add('vid');s.b.classList.remove('mirror')}));
 }

 // направление прокрутки — со сглаживанием и порогом, чтобы мелкие рывки не дёргали камеру
 let lastY=scrollY,vel=0,back=false,cur=null,curSec=null,veilV=-1,hidden=false;
 function sync(){S.forEach(s=>{if(!s.v||!s.loop)return;if(s===cur&&!hidden){s.v.playbackRate=s.rate;s.v.play().catch(()=>{})}else s.v.pause()})}
 document.addEventListener('visibilitychange',()=>{hidden=document.hidden;sync()});

 function activeSection(){
  const mid=innerHeight*.5;let best=null;
  for(const sec of secs){const r=sec.getBoundingClientRect();if(r.top<=mid&&r.bottom>mid){best=[sec,r];break}}
  if(!best){const sec=scrollY<10?secs[0]:secs[secs.length-1];if(!sec)return null;best=[sec,sec.getBoundingClientRect()]}
  const [sec,r]=best;const p=clamp((mid-r.top)/r.height,0,1);
  // разделы F1–F5 — части одного ролика: data-j="начало,конец" в долях пути
  const j=sec.dataset.j?sec.dataset.j.split(',').map(Number):null;
  return {sec,id:sec.dataset.seg,scene:sec.dataset.scene||sec.dataset.seg,p:j?j[0]+p*(j[1]-j[0]):p,veil:sec.dataset.veil};
 }

 // наезд/панорама постера: прогресс 0…1 → transform камеры; на обратном пути — зеркально
 const MOVES={
  orbit:(p,t)=>[Math.sin(t*.06)*1.6,Math.cos(t*.05)*.8,1.06+p*.06,Math.sin(t*.04)*.6],
  descend:p=>[0,-4+p*8,1.04+p*.16,0],
  push:p=>[0,p*-2,1.04+p*.18,0],
  pan:p=>[3-p*6,0,1.1,0],
  dolly:p=>[0,1-p*2,1.02+p*.26,0],
  rise:p=>[-p*4,4-p*8,1.1+p*.04,0],
  sway:(p,t)=>[Math.sin(t*.05)*1.2,0,1.06+p*.04,0]
 };
 let T0=performance.now();
 function frame(now){
  requestAnimationFrame(frame);
  const t=(now-T0)/1000;
  const y=scrollY,dy=y-lastY;lastY=y;
  vel=vel*.86+dy*.14;
  if(vel<-1.2)back=true;else if(vel>1.2)back=false;
  const a=activeSection();if(!a)return;
  const s=byId[a.scene];if(!s)return;
  if(a.id!==curSec){const prevSec=curSec;curSec=a.id;
   document.dispatchEvent(new CustomEvent('cam:seg',{detail:{id:a.id,prev:prevSec}}));}
  if(s!==cur){
   const prev=cur;cur=s;s.sp=a.p;
   S.forEach(x=>x.el.classList.toggle('on',x===s));
   want(s);want(S[s.i+1]);want(S[s.i-1]);sync();
   if(cap)cap.textContent=s.id+(s.v?'':' · постер-заглушка');
  }
  const v=a.veil!=null?+a.veil:.25;if(v!==veilV){veilV=v;veil&&veil.style.setProperty('--veil',v)}
  if(MODE==='still'){s.rig.style.transform='scale(1.04)';return}
  s.sp+=(a.p-s.sp)*(MODE==='scrub'?.12:.2);
  const p=s.sp;
  // обратный путь: есть ролик назад — наплыв на него; нет роликов совсем — зеркальный постер (видно, что механизм работает)
  const useBack=back&&!s.loop&&MODE==='scrub'&&(s.vb||!s.v);
  s.el.classList.toggle('rev',useBack);
  if(s.v&&!s.loop&&MODE==='scrub'){
   const vv=useBack&&s.vb?s.vb:s.v,d=vv.duration||0;
   if(d){let target=(useBack&&s.vb?1-p:p)*(d-.05);
    // путь по таблице «доля пути → секунда»: камера движется ровно, без замедлений на стыках роликов
    if(s.table){const n=s.table.length-1,x=clamp(p,0,1)*n,i=Math.min(n-1,x|0);target=Math.min(d-.05,s.table[i]+(s.table[i+1]-s.table[i])*(x-i))}if(!vv.seeking&&Math.abs(vv.currentTime-target)>1/48)vv.currentTime=target}
   s.rig.style.transform='scale(1.04)';
  }else{
   const m=MOVES[s.move]||MOVES.push,amp=MODE==='lite'?.5:1;
   const pp=useBack?1-p:p;let [tx,ty,sc,rot]=m(pp,t);
   if(useBack){tx=-tx;rot=-rot}
   s.rig.style.transform=`translate3d(${(tx*amp).toFixed(2)}%,${(ty*amp).toFixed(2)}%,0) scale(${(1+(sc-1)*amp).toFixed(4)}) rotate(${(rot*amp).toFixed(2)}deg)`;
  }
  // ролик пути, когда камера выше или ниже его: держим на крайнем кадре, чтобы наплыв на стадион/угол был без скачка
  S.forEach(x=>{if(x===s||!x.journey||!x.v)return;const vv=x.v,d=vv.duration||0;if(!d)return;
   const end=x.i<s.i?d-.05:0;x.sp=x.i<s.i?1:0;if(!vv.seeking&&Math.abs(vv.currentTime-end)>1/48)vv.currentTime=end});
  window.__cam={mode:MODE,seg:a.id,p:+p.toFixed(3),back:useBack,video:!!s.v};
 }
 requestAnimationFrame(frame);
})();
