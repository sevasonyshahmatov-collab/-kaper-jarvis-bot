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
  const FS = `precision mediump float;varying vec2 v;uniform sampler2D tex;uniform float t;uniform vec2 sc;
  void main(){
    vec2 uv=vec2(v.x,1.-v.y);
    float k=pow(uv.x,.6)*.85+.15;                                    /* от «древка» слева амплитуда растёт */
    float ph=uv.x*7.0-t*2.3+sin(uv.y*2.6+t*.7)*1.1;                  /* волна бежит по флагу, складки слегка наклонены */
    float ph2=uv.x*13.0-t*3.4+uv.y*2.0;
    float h=(sin(ph)+.35*sin(ph2))*k;                                 /* высота ткани */
    float sl=(cos(ph)*7.0+.35*cos(ph2)*13.0)*k;                       /* наклон */
    vec2 tc=(uv+vec2(h*.012,h*.035)-.5)*sc+.5;
    vec3 col=texture2D(tex,tc).rgb;
    float sh=clamp(.80+sl*.045,.42,1.25);                             /* впадины темнее, склоны к свету светлее */
    float spec=pow(clamp(sl*.09,0.,1.),5.)*.35;                       /* блик на гребне */
    col=col*sh+spec;
    col*=.92+.08*h;
    gl_FragColor=vec4(col,1.);
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
      gl.uniform2f(uS, (ca > ia ? 1 : ca / ia) * .96, (ca > ia ? ia / ca : 1) * .96);
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
