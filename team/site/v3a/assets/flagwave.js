/* JARVIS v3a — фон страницы матча развевается, как флаг (владелец 09.11): WebGL-шейдер над той же картинкой (bg.webp / bg-m.webp).
   Волна сдвигает картинку и даёт объём — светлые гребни и тени в складках. Рисует только пока первый экран виден и вкладка открыта;
   плотность пикселей ≤ 1,5. Нет WebGL или «уменьшить движение» — остаётся обычная картинка (CSS). */
(() => {
  'use strict';
  const field = document.querySelector('.mx-field.has-bg');
  if (!field || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const layer = field.querySelector(matchMedia('(max-width: 620px)').matches ? '.mx-fm' : '.mx-fd');
  const m = layer && /url\(["']?([^"')]+)["']?\)/.exec(layer.style.backgroundImage || '');
  if (!m) return;
  const cv = document.createElement('canvas');
  cv.className = 'mx-wave'; cv.setAttribute('aria-hidden', 'true');
  const gl = cv.getContext('webgl', {alpha: false, antialias: false, premultipliedAlpha: false});
  if (!gl) return;

  const VS = 'attribute vec2 p;varying vec2 v;void main(){v=p*.5+.5;gl_Position=vec4(p,0.,1.);}';
  /* плавно, без видимых линий (владелец 09.11): картинка заранее размыта (её фактура не «плывёт»), только широкие медленные
     волны, тени мягкие без обрезки и бликов, зерно и дизеринг неподвижны поверх — градиент без ступенек */
  const FS = `#ifdef GL_FRAGMENT_PRECISION_HIGH
  precision highp float;
  #else
  precision mediump float;
  #endif
  varying vec2 v;uniform sampler2D tex;uniform vec3 ph;uniform vec2 sc;uniform vec3 bg;
  float hash(vec2 p){vec3 q=fract(vec3(p.xyx)*.1031);q+=dot(q,q.yzx+33.33);return fract((q.x+q.y)*q.z);}
  void main(){
    vec2 uv=vec2(v.x,1.-v.y);
    float k=smoothstep(0.,.4,uv.x)*.7+.3;                             /* у «древка» слева слабее */
    float a1=uv.x*5.0+uv.y*1.2-ph.x,a2=uv.x*2.6-uv.y*.9-ph.y+.6*sin(ph.z);
    float h=(.55*sin(a1)+.45*sin(a2))*k;                              /* высота ткани: две широкие волны */
    float d=(.55*cos(a1)*5.0+.45*cos(a2)*2.6)*k/4.0;                  /* наклон, примерно −1…1 */
    float y=uv.y+h*.016;                                              /* края полотна мягко гуляют */
    float edge=smoothstep(0.,.008,y)*smoothstep(1.,.992,y);
    vec3 col=texture2D(tex,(vec2(uv.x+h*.006,y)-.5)*sc+.5).rgb;
    col*=1.+.13*d;                                                    /* мягкий свет и тень складки */
    float n=hash(gl_FragCoord.xy);
    col+=(n-.5)*(.035+1.5/255.);                                      /* неподвижное зерно + дизеринг */
    gl_FragColor=vec4(mix(bg,col,edge),1.);
  }`;
  const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return gl.getShaderParameter(s, gl.COMPILE_STATUS) ? s : null; };
  const vs = sh(gl.VERTEX_SHADER, VS), fs = sh(gl.FRAGMENT_SHADER, FS);
  if (!vs || !fs) return;
  const pr = gl.createProgram(); gl.attachShader(pr, vs); gl.attachShader(pr, fs); gl.linkProgram(pr);
  if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) return;
  gl.useProgram(pr);
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const uT = gl.getUniformLocation(pr, 'ph'), uS = gl.getUniformLocation(pr, 'sc');
  const bgc = (getComputedStyle(document.body).backgroundColor.match(/\d+/g) || [11, 18, 32]).map(Number);
  gl.uniform3f(gl.getUniformLocation(pr, 'bg'), bgc[0] / 255, bgc[1] / 255, bgc[2] / 255);

  const img = new Image();
  img.onload = () => {
    const tx = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tx);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    /* размытие без ctx.filter (его нет в старом Safari): уменьшить в 6 раз и растянуть обратно со сглаживанием */
    const bw = Math.min(1280, img.width), bh = Math.round(bw * img.height / img.width), sm = document.createElement('canvas'), bc = document.createElement('canvas');
    sm.width = Math.round(bw / 6); sm.height = Math.round(bh / 6); bc.width = bw; bc.height = bh;
    const sx = sm.getContext('2d'), bx = bc.getContext('2d'); sx.imageSmoothingQuality = bx.imageSmoothingQuality = 'high';
    sx.drawImage(img, 0, 0, sm.width, sm.height); bx.drawImage(sm, 0, 0, bw, bh);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, bc);
    field.insertBefore(cv, field.firstChild);
    let vis = true, raf = 0, t0 = performance.now();
    const size = () => {
      const r = field.getBoundingClientRect(), dpr = Math.min(1.5, devicePixelRatio || 1);
      cv.width = Math.max(1, Math.round(r.width * dpr)); cv.height = Math.max(1, Math.round(r.height * dpr));
      gl.viewport(0, 0, cv.width, cv.height);
      const ca = r.width / r.height, ia = img.width / img.height;        /* cover с запасом 4 % под волну */
      gl.uniform2f(uS, (ca > ia ? 1 : ca / ia) * .97, (ca > ia ? ia / ca : 1) * .9);
    };
    const T = 6.283185307, draw = now => { const t = (now - t0) / 1000; gl.uniform3f(uT, t * .55 % T, t * .33 % T, t * .2 % T); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); raf = vis && !document.hidden ? requestAnimationFrame(draw) : 0; };
    const go = () => { if (!raf && vis && !document.hidden) raf = requestAnimationFrame(draw); };
    size(); field.classList.add('waving'); go();
    addEventListener('resize', () => { size(); go(); });
    document.addEventListener('visibilitychange', go);
    if ('IntersectionObserver' in window) new IntersectionObserver(es => { vis = es[0].isIntersecting; go(); }).observe(field);
  };
  img.src = m[1];
})();
