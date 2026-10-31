/* JARVIS v3a — курсор «Swirl»: хвост за указателем (сплайн по последним 40 точкам, сужается к концу).
   Системный курсор не прячем; слой поверх страницы не ловит нажатия. Только мышь (hover + fine),
   без анимации при prefers-reduced-motion. Цвет хвоста подстраивается под фон под указателем:
   на тёмном — белый → голубой, на светлом — тёмно-синий → синий льда. */
(()=>{
  const N=40, HEAD=15, ALPHA=.8;
  const DARK=['#FFFFFF','#5B9BF6'], LIGHT=['#10161f','#1462a8'];
  const mqFine=matchMedia('(hover: hover) and (pointer: fine)');
  const mqMotion=matchMedia('(prefers-reduced-motion: reduce)');
  let off=null;

  function mount(){
    const cv=document.createElement('canvas');
    cv.setAttribute('aria-hidden','true');
    cv.style.cssText='position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:9999;opacity:'+ALPHA;
    document.body.appendChild(cv);
    const ctx=cv.getContext('2d');
    let dpr=1, w=0, h=0;
    const size=()=>{dpr=Math.min(devicePixelRatio||1,2);w=innerWidth;h=innerHeight;
      cv.width=Math.round(w*dpr);cv.height=Math.round(h*dpr);ctx.setTransform(dpr,0,0,dpr,0,0)};
    size();

    const pts=[]; let px=-1, py=-1, inside=false, raf=0, frame=0, cols=DARK, hot=false;

    // яркость фона под указателем: ищем ближайшего предка с непрозрачным фоном
    const lum=c=>{const m=c.match(/[\d.]+/g);if(!m)return null;
      if(m.length>3&&+m[3]===0)return null;
      const [r,g,b]=m.slice(0,3).map(v=>{v/=255;return v<=.03928?v/12.92:((v+.055)/1.055)**2.4});
      return .2126*r+.7152*g+.0722*b};
    const sample=()=>{
      let el=document.elementFromPoint(px,py), L=null;
      hot=!!(el&&el.closest('a, button, input'));
      while(el&&el!==document.documentElement){L=lum(getComputedStyle(el).backgroundColor);if(L!==null)break;el=el.parentElement}
      if(L===null)L=lum(getComputedStyle(document.body).backgroundColor)??0;
      cols=L>.35?LIGHT:DARK;
    };

    const onMove=e=>{px=e.clientX;py=e.clientY;inside=true};
    const onLeave=()=>{inside=false};
    addEventListener('pointermove',onMove,{passive:true});
    document.addEventListener('pointerleave',onLeave);
    addEventListener('resize',size);

    const loop=()=>{
      raf=requestAnimationFrame(loop);
      if(inside&&px>=0){pts.push([px,py]);if(++frame%8===0)sample()}
      else if(pts.length)pts.shift();          // хвост догоняет и гаснет
      while(pts.length>N)pts.shift();
      ctx.clearRect(0,0,w,h);
      const n=pts.length; if(n<3)return;
      // габариты хвоста — для градиента под 90° (слева направо)
      let x0=Infinity,x1=-Infinity;for(const p of pts){if(p[0]<x0)x0=p[0];if(p[0]>x1)x1=p[0]}
      const gr=ctx.createLinearGradient(x0-1,0,x1+1,0);gr.addColorStop(0,cols[0]);gr.addColorStop(1,cols[1]);
      ctx.strokeStyle=gr;ctx.lineCap='round';ctx.lineJoin='round';
      const head=HEAD*(hot?1.25:1);
      // отрезки сплайна по серединам: толщина растёт от 0 (хвост) до head (голова)
      for(let i=1;i<n-1;i++){
        const a=pts[i-1],b=pts[i],c=pts[i+1];
        ctx.lineWidth=Math.max(.1,head*(i/(n-1)));
        ctx.beginPath();
        ctx.moveTo((a[0]+b[0])/2,(a[1]+b[1])/2);
        ctx.quadraticCurveTo(b[0],b[1],(b[0]+c[0])/2,(b[1]+c[1])/2);
        ctx.stroke();
      }
    };
    raf=requestAnimationFrame(loop);

    return ()=>{cancelAnimationFrame(raf);removeEventListener('pointermove',onMove);
      document.removeEventListener('pointerleave',onLeave);removeEventListener('resize',size);cv.remove()};
  }

  const check=()=>{
    const want=mqFine.matches&&!mqMotion.matches;
    if(want&&!off)off=mount(); else if(!want&&off){off();off=null}
  };
  mqFine.addEventListener('change',check);mqMotion.addEventListener('change',check);
  document.readyState==='loading'?document.addEventListener('DOMContentLoaded',check):check();
})();
