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
  const FS = `precision mediump float;varying vec2 v;uniform sampler2D tex;uniform float t;uniform vec2 sc;uniform vec3 bg;
  void main(){
    vec2 uv=vec2(v.x,1.-v.y);
    float k=smoothstep(0.,.35,uv.x)*.75+.25;                         /* у «древка» слева слабее */
    float ph=uv.x*12.0-t*1.6+uv.y*2.0;                                /* 2 широкие складки плавно бегут по диагонали */
    float ph2=uv.x*6.0-t*1.0-uv.y*1.2+sin(t*.35);                      /* крупная медленная волна */
    float h=(.6*sin(ph)+.4*sin(ph2))*k;                               /* высота ткани */
    float d=(.6*cos(ph)*12.0+.4*cos(ph2)*6.0)*k;                      /* наклон по ширине */
    float y=uv.y+h*.022;                                              /* края полотна гуляют вверх-вниз */
    float edge=smoothstep(0.,.006,y)*smoothstep(1.,.994,y);
    vec2 tc=(vec2(uv.x+h*.010,y)-.5)*sc+.5;
    vec3 col=texture2D(tex,tc).rgb;
    float s=1.+clamp(d*.04,-.38,.26);                                  /* тень во впадине, свет на склоне */
    float spec=pow(clamp(d/9.6,0.,1.),4.)*.2;                        /* блик на гребне */
    col=col*s+spec;
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
  const uT = gl.getUniformLocation(pr, 't'), uS = gl.getUniformLocation(pr, 'sc');
  const bgc = (getComputedStyle(document.body).backgroundColor.match(/\d+/g) || [11, 18, 32]).map(Number);
  gl.uniform3f(gl.getUniformLocation(pr, 'bg'), bgc[0] / 255, bgc[1] / 255, bgc[2] / 255);

  const img = new Image();
  img.onload = () => {
    const tx = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tx);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, img);
    field.insertBefore(cv, field.firstChild);
    let vis = true, raf = 0, t0 = performance.now();
    const size = () => {
      const r = field.getBoundingClientRect(), dpr = Math.min(1.5, devicePixelRatio || 1);
      cv.width = Math.max(1, Math.round(r.width * dpr)); cv.height = Math.max(1, Math.round(r.height * dpr));
      gl.viewport(0, 0, cv.width, cv.height);
      const ca = r.width / r.height, ia = img.width / img.height;        /* cover с запасом 4 % под волну */
      gl.uniform2f(uS, (ca > ia ? 1 : ca / ia) * .97, (ca > ia ? ia / ca : 1) * .9);
    };
    const draw = now => { gl.uniform1f(uT, (now - t0) / 1000); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); raf = vis && !document.hidden ? requestAnimationFrame(draw) : 0; };
    const go = () => { if (!raf && vis && !document.hidden) raf = requestAnimationFrame(draw); };
    size(); field.classList.add('waving'); go();
    addEventListener('resize', () => { size(); go(); });
    document.addEventListener('visibilitychange', go);
    if ('IntersectionObserver' in window) new IntersectionObserver(es => { vis = es[0].isIntersecting; go(); }).observe(field);
  };
  img.src = m[1];
})();
