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
    float a=uv.x*6.2+uv.y*2.2-t*1.5, b=uv.x*10.5-uv.y*3.4-t*2.2, c=uv.x*3.1+uv.y*5.0-t*0.9;
    float w=sin(a)*.55+sin(b)*.22+sin(c)*.23;                       /* высота ткани */
    float dx=cos(a)*6.2*.55+cos(b)*10.5*.22+cos(c)*3.1*.23;          /* наклон вдоль флага */
    float dy=cos(a)*2.2*.55-cos(b)*3.4*.22+cos(c)*5.0*.23;
    float k=.3+.7*uv.x;                                              /* у «древка» (слева) волна слабее */
    vec2 d=vec2(w*.014, w*.024+dx*.0022)*k;
    vec2 tc=(uv+d-.5)*sc+.5;                                         /* cover: картинка заполняет поле */
    vec3 col=texture2D(tex,tc).rgb;
    vec3 n=normalize(vec3(-dx*.11*k,-dy*.11*k,1.));
    float dif=dot(n,normalize(vec3(-.45,-.55,.7)));
    float spec=pow(max(dot(reflect(-normalize(vec3(-.4,-.5,.75)),n),vec3(0.,0.,1.)),0.),18.);
    col*=.70+.45*dif;                                                /* тени в складках */
    col+=spec*.22*k;                                                 /* блики на гребнях */
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
