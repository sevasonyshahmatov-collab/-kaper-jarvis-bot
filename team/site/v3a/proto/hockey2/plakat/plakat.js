/* «Плакат»: данные настоящие (../../../data/*.js), всё из данных экранируем. Анимация одна: блоки вырастают до ширины-вероятности. */
(() => {
'use strict';
const L = window.JV_LINES || {}, M = window.JV_MODEL || {}, TD = window.JV_TODAY || { matches: [] }, J = window.JV_JERSEY;
const $ = s => document.querySelector(s);
const esc = t => String(t == null ? '' : t).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const f2 = v => (+v).toFixed(2).replace('.', ',');
const A = '../../../';
const NHL = { nhl_wsh: 'washington', nhl_nyi: 'islanders', nhl_njd: 'new-jersey', nhl_uta: 'utah', nhl_ott: 'ottawa', nhl_fla: 'florida', nhl_col: 'colorado', nhl_sea: 'seattle', nhl_buf: 'buffalo', nhl_nsh: 'nashville', nhl_nyr: 'rangers', nhl_ana: 'anaheim', nhl_tor: 'toronto', nhl_det: 'detroit', nhl_stl: 'st-louis', nhl_cgy: 'calgary', nhl_wpg: 'winnipeg', nhl_sjs: 'san-jose', nhl_cbj: 'columbus', nhl_lak: 'los-angeles', nhl_pit: 'pittsburgh', nhl_phi: 'philadelphia', nhl_chi: 'chicago', nhl_van: 'vancouver', nhl_car: 'carolina', nhl_bos: 'boston', nhl_edm: 'edmonton', nhl_vgk: 'vegas', nhl_mtl: 'montreal', nhl_tbl: 'tampa-bay' };
const slug = c => NHL[c] || c;
const href = m => `${A}${m.lg}/${m.key.split('|')[1]}-${slug(m.h)}-${slug(m.a)}/index.html`;
const LGN = { khl: 'КХЛ', nhl: 'НХЛ' };
const startMs = m => Date.parse(m.t.replace(' ', 'T') + ':00+03:00');
const dayKey = m => new Date(Date.parse(m.t.replace(' ', 'T') + ':00Z') - 6 * 36e5).toISOString().slice(0, 10); /* игровой день по МСК: ночь относится ко вчера */

const all = (TD.matches || []).filter(m => (m.lg === 'khl' || m.lg === 'nhl') && M[m.key]).sort((a, b) => a.t.localeCompare(b.t) || a.key.localeCompare(b.key));
let pool = all.filter(m => startMs(m) + 3.5 * 36e5 > Date.now());
if (!pool.length) pool = all;
const g0 = pool.length ? dayKey(pool[0]) : '';
const day = pool.filter(m => dayKey(m) === g0);

/* цвета клубов: основной цвет формы; если у пары почти одинаковые — гостям второй цвет */
const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const dist = (a, b) => { const x = hex(a), y = hex(b); return Math.hypot(x[0] - y[0], x[1] - y[1], x[2] - y[2]); };
const ink = bg => (J && J.cr('#ffffff', bg) >= J.cr('#0a0a0a', bg)) ? '#fff' : '#0a0a0a';
function cols(m) {
  const h = (J && J.J[m.h]) || ['#222', '#888'], a = (J && J.J[m.a]) || ['#444', '#888'];
  let ac = a[0];
  const lt = c => hex(c).reduce((x, y) => x + y, 0) > 640;
  if (dist(h[0], a[0]) < 110) ac = dist(h[0], a[1]) >= 110 && !lt(a[1]) ? a[1] : (J ? J.mix(a[0], '#ffffff', .45) : '#999');
  return [h[0], ac];
}

const emb = c => `${A}assets/em/${encodeURIComponent(c)}.webp`;
const pc = v => Math.round(v * 100);
function blocks(m, hero) {
  const d = M[m.key], c = cols(m);
  const P = [d.p1, d.x, d.p2], fi = P[0] >= P[2] ? 0 : 2;
  const tot = P[0] + P[1] + P[2];
  return [0, 1, 2].map(i => {
    const p = P[i] / tot * 100, n = pc(P[i]), x = i === 1;
    const bg = x ? '' : `--bg:${c[i === 0 ? 0 : 1]};--fg:${ink(c[i === 0 ? 0 : 1])};`;
    const cls = ['b', x ? 'x' : '', i === fi ? 'fav' : '', hero && i !== fi && p < 27 ? 'rot' : '', !hero && p < 11 ? 'small' : ''].join(' ');
    const top = hero ? (x ? '<span></span>' : `<img class="em" src="${emb(i === 0 ? m.h : m.a)}" alt="${esc(i === 0 ? m.hn : m.an)}" width="64" height="64">`) : '';
    return `<div class="${cls}" style="${bg}--p:${p.toFixed(2)}"><div class="bi">${top}<span class="n">${n}<i>%</i></span></div></div>`;
  }).join('');
}

/* первый экран: матч с самым уверенным фаворитом среди ближайших матчей игрового дня */
const feat = day.slice().sort((a, b) => Math.max(M[b.key].p1, M[b.key].p2) - Math.max(M[a.key].p1, M[a.key].p2))[0];
const grow = el => { const go = () => requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add('in'))); go(); };
if (feat) {
  const d = M[feat.key], ln = L[feat.key], tot = d.p1 + d.x + d.p2;
  const MO = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
  $('#hLg').textContent = `${LGN[feat.lg]} · ${+feat.t.slice(8, 10)} ${MO[+feat.t.slice(5, 7) - 1]}`;
  $('#hTm').innerHTML = `${feat.t.slice(11, 16)}<small>МСК</small>`;
  $('#h1').textContent = `${feat.hn} —\u00a0${feat.an}`;
  const cells = ln ? `<div class="cells" aria-hidden="false">${['p1', 'x', 'p2'].map((k, i) => `<span style="--p:${([d.p1, d.x, d.p2][i] / tot * 100).toFixed(2)}">${i === 0 ? '<em>кэф</em>' : ''}${f2(ln[k])}</span>`).join('')}</div>` : '';
  $('#poster').innerHTML = `<a class="bar" href="${href(feat)}" aria-label="${esc(feat.hn)} — ${esc(feat.an)}: подробности">${blocks(feat, true)}</a>${cells}`;
  grow($('#poster .bar'));
  { const p1 = d.p1 / tot * 100, ht = $('.hero-txt'); if (ht && p1 >= 55) { ht.style.setProperty('--p1', p1.toFixed(2) + '%'); ht.classList.add('al'); } }
  /* a.bar — контейнер, кэфы вне него */
}

/* ряд малых плакатов */
const rest = day.filter(m => m !== feat);
$('#gN').textContent = rest.length;
$('#grid').innerHTML = rest.map(m => {
  const d = M[m.key], ln = L[m.key], fi = d.p1 >= d.p2 ? 'p1' : 'p2';
  const dd = m.t.slice(0, 10) !== g0 ? `<small>${m.t.slice(8, 10)}.${m.t.slice(5, 7)}</small>` : '';
  return `<a class="card" href="${href(m)}"><div class="c-hd"><b>${m.t.slice(11, 16)}${dd}</b><span>${LGN[m.lg]}${ln ? ` &nbsp;<em>кэф</em>${f2(ln[fi])}` : ''}</span></div>
  <div class="nmz"><span><img src="${emb(m.h)}" alt="" width="28" height="28" loading="lazy">${esc(m.hn)}</span><span><img src="${emb(m.a)}" alt="" width="28" height="28" loading="lazy">${esc(m.an)}</span></div>
  <div class="bar">${blocks(m, false)}</div></a>`;
}).join('');

const io = 'IntersectionObserver' in window ? new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { io.unobserve(e.target); e.target.classList.add('in'); } }), { threshold: .2 }) : null;
document.querySelectorAll('#grid .bar').forEach(b => io ? io.observe(b) : b.classList.add('in'));

/* лиги */
const cnt = lg => all.filter(m => m.lg === lg).length;
$('#lgs').innerHTML = ['khl', 'nhl'].map(lg => `<a class="lgc ${lg}" href="${A}hockey/league.html?lg=${lg}"><div><img src="${A}assets/lg/${lg}.webp" alt="" width="56" height="56"></div><div class="t">${LGN[lg]}</div><div class="f"><span>${cnt(lg)} матчей в ближайшие дни</span><span>Лига →</span></div></a>`).join('');
$('#built').textContent = TD.built ? `Данные от ${TD.built.slice(8, 10)}.${TD.built.slice(5, 7)} ${TD.built.slice(11)} МСК` : '';
})();
