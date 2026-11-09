/* JARVIS v3a — флаг страницы матча теперь только на CSS (assets/matchx.css, «ФЛАГ без WebGL»), владелец 09.11.
   Здесь осталась лишь метка на образцах proto/ — убрать вместе с подключением файла при раскатке (seo/build_match.py). */
(() => {
  const f = document.querySelector('.mx-field.has-bg');
  if (!f || !/\/proto\//.test(location.pathname)) return;
  const b = document.createElement('small'); b.className = 'mx-diag';
  b.textContent = matchMedia('(prefers-reduced-motion: reduce)').matches ? 'анимация выкл.: в системе «уменьшить движение»' : 'флаг на CSS · версия 8';
  f.appendChild(b);
})();
