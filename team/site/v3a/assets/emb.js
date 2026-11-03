/* Анимация эмблемы клуба в шапке: ?emb=1|2|3|4 (по умолчанию — без анимации). Только transform/opacity. */
(function(){
 var m=(location.search.match(/[?&]emb=([1-4])(?:&|$)/)||[])[1];if(!m)return;
 var crest=document.querySelector('.tmcrest'),img=crest&&crest.querySelector('img.em');if(!img)return;
 if(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 var css=document.createElement('style');
 css.textContent='.tmcrest{position:relative}.tmcrest .em{will-change:transform}'+
 '@keyframes embIn{0%{transform:translateY(46%) scale(.45);opacity:0}45%{opacity:1}100%{transform:none;opacity:1}}'+
 '.emb1 .em{animation:embIn .9s cubic-bezier(.34,1.56,.64,1) both}'+
 '.emb2{perspective:520px}.emb2 .em{transition:transform .5s cubic-bezier(.2,.8,.2,1);transform-style:preserve-3d}'+
 '@keyframes embBr{0%,100%{transform:scale(1)}50%{transform:scale(1.02)}}'+
 '.emb3 .em{animation:embBr 5.5s ease-in-out infinite}'+
 '.embsh{position:absolute;left:11%;top:11%;width:78%;height:78%;pointer-events:none;overflow:hidden;-webkit-mask-size:contain;mask-size:contain;-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;-webkit-mask-position:center;mask-position:center}'+
 '.embsh i{position:absolute;left:0;top:-25%;width:36%;height:150%;opacity:0;transform:translateX(-160%) rotate(22deg);background:linear-gradient(90deg,transparent,rgba(255,255,255,.85),transparent);animation:embSh 5.5s ease-in-out infinite}'+
 '@keyframes embSh{0%,70%{transform:translateX(-160%) rotate(22deg);opacity:0}74%{opacity:1}92%{transform:translateX(420%) rotate(22deg);opacity:1}96%,100%{transform:translateX(420%) rotate(22deg);opacity:0}}'+
 '.embcv{position:absolute;left:-55%;top:-55%;width:210%;height:210%;pointer-events:none;z-index:2}'+
 '@keyframes embFl{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}'+
 '.emb4 .em{animation:embFl 6s ease-in-out infinite}';
 document.head.appendChild(css);crest.classList.add('emb'+m);
 if(m==='2'){
  var rx=0,ry=0,raf=0,set=function(x,y){rx=x;ry=y;if(!raf)raf=requestAnimationFrame(function(){raf=0;img.style.transform='rotateX('+rx.toFixed(1)+'deg) rotateY('+ry.toFixed(1)+'deg)'})};
  var cl=function(v){return Math.max(-1,Math.min(1,v))};
  addEventListener('mousemove',function(e){var r=crest.getBoundingClientRect(),dx=cl((e.clientX-r.left-r.width/2)/(innerWidth/2)*2.2),dy=cl((e.clientY-r.top-r.height/2)/(innerHeight/2)*2.2);
   img.style.transitionDuration='.12s';set(-dy*12,dx*12)},{passive:true});
  document.addEventListener('mouseleave',function(){img.style.transitionDuration='.6s';set(0,0)});
  addEventListener('scroll',function(){if(matchMedia('(hover:hover)').matches)return;var r=crest.getBoundingClientRect(),p=cl((r.top+r.height/2-innerHeight/2)/(innerHeight/2));img.style.transitionDuration='.25s';set(p*9,p*-7)},{passive:true});
 }
 if(m==='3'){
  var sh=document.createElement('span');sh.className='embsh';sh.setAttribute('aria-hidden','true');
  var u='url("'+img.src+'")';sh.style.webkitMaskImage=u;sh.style.maskImage=u;sh.innerHTML='<i></i>';crest.appendChild(sh);
 }
 if(m==='4'){
  var cv=document.createElement('canvas');cv.className='embcv';cv.setAttribute('aria-hidden','true');crest.appendChild(cv);
  var cx=cv.getContext('2d'),W=0,H=0,dpr=Math.min(devicePixelRatio||1,2),N=32,P=[],vis=true,on=false,last=0;
  var acc=getComputedStyle(document.body).getPropertyValue('--cacc').trim()||'#bfe3ff';
  function size(){var r=cv.getBoundingClientRect();W=r.width;H=r.height;cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);cx.setTransform(dpr,0,0,dpr,0,0)}
  function mk(i,init){var a=Math.random()*6.283,r0=.26+Math.random()*.1,sp=.012+Math.random()*.018;return{a:a,r:init?r0+Math.random()*.22:r0,sp:sp,s:1.8+Math.random()*2.6,t:Math.random()*6.283,c:Math.random()<.65?'#fff':acc,k:Math.random()<.4,life:init?Math.random():0}}
  for(var i=0;i<N;i++)P.push(mk(i,true));
  function draw(ts){on=false;if(!vis||document.hidden)return;var dt=Math.min((ts-last)/1000||.016,.05);last=ts;cx.clearRect(0,0,W,H);
   for(var i=0;i<N;i++){var p=P[i];p.r+=p.sp*dt;p.a+=.04*dt;p.life+=dt/7;if(p.life>=1){P[i]=p=mk(i,false)}
    var al=Math.sin(Math.PI*p.life);al=al*(.55+.45*Math.sin(p.t+ts/400));var x=W/2+Math.cos(p.a)*p.r*W,y=H/2+Math.sin(p.a)*p.r*H;
    cx.globalAlpha=Math.max(0,al)*1;cx.fillStyle=p.c;cx.beginPath();
    if(p.k){var s=p.s*1.7;cx.moveTo(x,y-s);cx.lineTo(x+s*.6,y);cx.lineTo(x,y+s);cx.lineTo(x-s*.6,y)}else{cx.arc(x,y,p.s*.8,0,6.283)}
    cx.closePath();cx.fill()}
   cx.globalAlpha=1;loop()}
  function loop(){if(!on&&vis&&!document.hidden){on=true;requestAnimationFrame(draw)}}
  size();addEventListener('resize',size);
  if('IntersectionObserver' in window)new IntersectionObserver(function(e){vis=e[0].isIntersecting;if(vis){last=performance.now();loop()}}).observe(crest);
  document.addEventListener('visibilitychange',function(){last=performance.now();loop()});loop();
 }
})();
