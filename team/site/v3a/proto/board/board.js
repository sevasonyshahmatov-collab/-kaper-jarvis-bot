/* JARVIS v3a, прототип «Тренерский планшет»: маркер (Rough.js), фишки, губка. Данные: ../../data/*.js */
(() => {
'use strict';
const D = document, W = window;
const $ = (s, r = D) => r.querySelector(s), $$ = (s, r = D) => [...r.querySelectorAll(s)];
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const FINE = matchMedia('(hover:hover) and (pointer:fine)').matches;
const NS = 'http://www.w3.org/2000/svg';
const G = W.rough ? rough.generator() : null;
const GS = !!W.gsap;
if (GS && W.DrawSVGPlugin) gsap.registerPlugin(DrawSVGPlugin);
const ANIM = GS && !RM;
D.documentElement.classList.add('js');

/* ---------- форматирование ---------- */
const pc = v => Math.round(v * 100);
const odd = v => (v == null ? '—' : (+v).toFixed(2).replace('.', ','));
const gl = v => (+v).toFixed(1).replace('.', ',');
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const T = W.JV_TODAY || { matches: [], days: [] }, M = W.JV_MODEL || {}, L = W.JV_LINES || {}, LK = W.JV_MATCHLINKS || {};
const CS = W.CLUB_SET || {};
const LG = { khl: 'КХЛ', nhl: 'НХЛ', epl: 'АПЛ', laliga: 'Ла Лига', seriea: 'Серия А', bundesliga: 'Бундеслига', ligue1: 'Лига 1', ucl: 'Лига чемпионов', uel: 'Лига Европы', rpl: 'РПЛ' };
const isHockey = m => m.lg === 'khl' || m.lg === 'nhl';
const clubColor = id => (CS[id] && CS[id].a1) || '#5b6572';
const clubDark = id => (CS[id] && CS[id].dk) || '#2a2f35';
const timeOf = m => m.t.slice(11, 16);
function dayLabel(m) {
  const d = m.t.slice(0, 10), days = T.days || [];
  return d === days[0] ? 'сегодня' : d === days[1] ? 'завтра' : d.slice(8, 10) + '.' + d.slice(5, 7);
}
const when = m => new Date(m.t.replace(' ', 'T') + ':00+03:00');
const featured = () => T.matches.find(m => m.key === 'khl|2026-11-05|avangard|cska') || T.matches.find(m => m.lg === 'khl');
function share(l) {
  if (!l || !l.p1 || !l.x || !l.p2) return null;
  const i = [1 / l.p1, 1 / l.x, 1 / l.p2], s = i[0] + i[1] + i[2];
  return i.map(v => v / s);
}
const emb = id => `<img src="../../assets/em/${esc(id)}.webp" alt="" width="52" height="52" loading="lazy" decoding="async">`;
const ini = n => `<span class="ini" aria-hidden="true">${esc(n.trim().charAt(0))}</span>`;
D.addEventListener('error', e => {
  const t = e.target;
  if (t && t.tagName === 'IMG' && t.closest('.tm,.mg,.mg2,.scene .mag,.form h3')) {
    const a = D.createElement('span'); a.className = 'ini'; a.textContent = (t.dataset.n || '?').charAt(0); t.replaceWith(a);
  }
}, true);

/* ---------- маркер ---------- */
function S(tag, attrs, parent) {
  const e = D.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function ink(svg, dr, cls, o) {
  const out = [];
  if (!G || !dr) return out;
  for (const p of G.toPaths(dr)) {
    if (!p.stroke || p.stroke === 'none') continue;
    const e = S('path', { d: p.d, class: 'mk ' + (cls || '') }, svg);
    if (o && o.sw) e.style.strokeWidth = o.sw;
    if (o && o.ns) e.setAttribute('vector-effect', 'non-scaling-stroke');
    if (o && o.pl) e.setAttribute('pathLength', '1');
    out.push(e);
  }
  return out;
}
const R = (seed, rg = .8, extra) => Object.assign({ roughness: rg, bowing: 1.1, seed, disableMultiStroke: true, stroke: '#000' }, extra || {});
function rline(svg, x1, y1, x2, y2, cls, seed, o) { return ink(svg, G && G.line(x1, y1, x2, y2, R(seed, .7, o && o.r)), cls, o); }
function rarrow(svg, pts, cls, seed, o) {
  const sw = (o && o.sw) || 3;
  const paths = ink(svg, G && G.curve(pts, R(seed, .6, { curveFitting: .95 })), cls, o);
  const a = pts[pts.length - 2], b = pts[pts.length - 1];
  const ang = Math.atan2(b[1] - a[1], b[0] - a[0]), hl = 10 + sw * 2.2;
  for (const d of [.5, -.5]) {
    const x = b[0] - Math.cos(ang + d) * hl, y = b[1] - Math.sin(ang + d) * hl;
    paths.push(...ink(svg, G && G.line(b[0], b[1], x, y, R(seed + 7, .5)), cls, o));
  }
  return paths;
}
function drawIn(els, o) {
  els = [].concat(els).filter(Boolean);
  if (!els.length) return null;
  if (!ANIM || !W.DrawSVGPlugin) return null;
  return gsap.fromTo(els, { drawSVG: '0%' }, Object.assign({ drawSVG: '100%', duration: .9, ease: 'power2.inOut' }, o || {}));
}
function onView(el, fn, th) {
  if (!('IntersectionObserver' in W)) { fn(); return; }
  const io = new IntersectionObserver(es => { if (es[0].isIntersecting) { io.disconnect(); fn(); } }, { threshold: th || .35 });
  io.observe(el);
}
function count(el) {
  const to = +el.dataset.count, suf = el.dataset.suf || '', dec = +el.dataset.dec || 0;
  const fmt = v => (dec ? v.toFixed(dec).replace('.', ',') : Math.round(v)) + suf;
  el.textContent = fmt(to);
  if (!ANIM) return;
  el.textContent = fmt(0);
  onView(el, () => {
    const o = { v: 0 };
    gsap.to(o, { v: to, duration: 1.1, ease: 'power2.out', onUpdate: () => (el.textContent = fmt(o.v)), onComplete: () => (el.textContent = fmt(to)) });
  }, .5);
}

/* ---------- подчёркивание заголовков ---------- */
function underlines() {
  $$('.h2').forEach((h, i) => {
    const svg = S('svg', { class: 'ul', viewBox: '0 0 300 14', preserveAspectRatio: 'none', 'aria-hidden': 'true' });
    const p = ink(svg, G && G.curve([[2, 8], [90, 5], [200, 10], [298, 6]], R(i + 3, .8)), 'mk-red', { sw: 3.2, ns: true });
    h.appendChild(svg);
    if (ANIM) { gsap.set(p, { drawSVG: '0%' }); onView(h, () => drawIn(p, { duration: .7 }), .6); }
  });
}

/* ---------- фишка матча ---------- */
function ringPath(svg) {
  ink(svg, G && G.ellipse(50, 30, 96, 54, R(11, .9, { curveFitting: .97 })), '', { pl: 1, ns: true });
}
function why(m, mod, ln) {
  const a = mod.p1, x = mod.x, b = mod.p2, mx = Math.max(a, x, b);
  const who = mx === a ? 'победа хозяев (' + m.hn + ')' : mx === b ? 'победа гостей (' + m.an + ')' : 'ничья в основное время';
  return `Самый вероятный исход: ${who}, ${pc(mx)} %.`;
}
function tileHTML(m, i) {
  const mod = M[m.key], ln = L[m.key];
  if (!mod) return '';
  const mx = Math.max(mod.p1, mod.x, mod.p2);
  const cls = mx === mod.p1 ? 'h' : mx === mod.p2 ? 'a' : 'd';
  const r = (((i * 37) % 7) - 3) * .42;
  const sh = share(ln);
  const link = m.key === 'khl|2026-11-05|avangard|cska' ? 'match.html' : (LK[m.key] ? '../../' + LK[m.key] : '');
  const cell = (c, lab, v, o) => `<div class="pc ${c}${cls === c ? ' top' : ''}"><small>${lab}</small><span class="v" data-count="${pc(v)}" data-suf=" %">${pc(v)} %</span><span class="k">кэф ${odd(o)}</span>${cls === c ? '<svg class="ring" viewBox="0 0 100 60" preserveAspectRatio="none" aria-hidden="true"></svg>' : ''}</div>`;
  return `<article class="tile" style="--r:${r.toFixed(2)}deg" tabindex="0" role="button" aria-pressed="false" aria-label="${esc(m.hn)} — ${esc(m.an)}: перевернуть фишку" data-key="${esc(m.key)}">
  <div class="tile-in">
    <div class="face front" style="--ca:${clubColor(m.h)};--cb:${clubColor(m.a)}"><i class="band"></i><i class="knob"></i>
      <div class="meta"><b>${LG[m.lg] || m.lg.toUpperCase()}</b><span>${dayLabel(m)}, ${timeOf(m)} МСК</span></div>
      <div class="vs"><div class="tm">${emb(m.h).replace('alt=""', 'alt="" data-n="' + esc(m.hn) + '"')}<span>${esc(m.hn)}</span></div><span class="dash">—</span><div class="tm">${emb(m.a).replace('alt=""', 'alt="" data-n="' + esc(m.an) + '"')}<span>${esc(m.an)}</span></div></div>
      <div class="pr">${cell('h', 'П1', mod.p1, ln && ln.p1)}${cell('d', 'Х', mod.x, ln && ln.x)}${cell('a', 'П2', mod.p2, ln && ln.p2)}</div>
      <p class="hint">Нажми, чтобы перевернуть</p>
    </div>
    <div class="face back" style="--ca:${clubColor(m.h)};--cb:${clubColor(m.a)}" inert><i class="band"></i><i class="knob"></i>
      <h3>Почему модель так думает</h3>
      <ul>
        <li><span>Ожидаемые голы</span><b>${mod.lam ? gl(mod.lam[0]) + ' : ' + gl(mod.lam[1]) : '—'}</b></li>
        <li><span>Тотал ${mod.tot ? gl(mod.tot) : ''}, больше</span><b>${mod.over != null ? pc(mod.over) + ' %' : '—'}</b></li>
        ${sh ? `<li><span>Линия без маржи</span><b>${sh.map(v => pc(v)).join(' / ')} %</b></li>` : ''}
      </ul>
      <p>${esc(why(m, mod, ln))}</p>
      ${link ? `<a class="more" href="${link}">Разбор матча</a>` : ''}
      <p class="note">Кэфы: справка, не рекомендация. Вероятность, а не гарантия исхода.</p>
    </div>
  </div>
</article>`;
}
function mountDeck(box, list, limit) {
  box.innerHTML = list.map((m, i) => tileHTML(m, i)).join('');
  $$('.tile', box).forEach(t => {
    $$('svg.ring', t).forEach(ringPath);
    const front = $('.front', t), back = $('.back', t);
    const toggle = () => {
      const f = t.classList.toggle('flip');
      t.setAttribute('aria-pressed', f);
      front.toggleAttribute('inert', f); back.toggleAttribute('inert', !f);
      if (!f) t.classList.remove('seen');
    };
    t.addEventListener('click', e => { if (e.target.closest('a')) return; toggle(); });
    t.addEventListener('keydown', e => { if (e.target === t && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); toggle(); } });
    if (!FINE) onView(t, () => t.classList.add('seen'), .7);
    $$('[data-count]', t).forEach(c => { c.removeAttribute('data-count'); });
  });
}

/* ---------- губка: переход между страницами ---------- */
let wipeEl;
function buildWipe() {
  wipeEl = D.createElement('div'); wipeEl.className = 'wipe'; wipeEl.setAttribute('aria-hidden', 'true');
  wipeEl.innerHTML = '<div class="wipe-sheet"></div><div class="sponge"><i></i><b></b></div>';
  D.body.appendChild(wipeEl);
}
function leave(href) {
  if (!ANIM) { location.href = href; return; }
  if (!wipeEl) buildWipe();
  const sheet = $('.wipe-sheet', wipeEl), sp = $('.sponge', wipeEl), Wd = innerWidth;
  wipeEl.classList.add('on');
  gsap.set(sheet, { scaleX: 0 }); gsap.set(sp, { x: -70, y: 0, rotate: -6 });
  let went = false;
  const go = () => { if (went) return; went = true; try { sessionStorage.setItem('jvboard', '1'); } catch (e) {} location.href = href; };
  const tl = gsap.timeline({ onComplete: go });
  tl.to(sheet, { scaleX: 1, duration: .4, ease: 'power1.inOut' }, 0)
    .to(sp, { x: Wd - 66, duration: .4, ease: 'power1.inOut' }, 0)
    .to(sp, { y: -16, rotate: 6, duration: .1, yoyo: true, repeat: 3, ease: 'sine.inOut' }, 0);
  setTimeout(go, 900);
}
D.addEventListener('click', e => {
  const a = e.target.closest('a[href]');
  if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || a.target || a.hasAttribute('download')) return;
  const u = new URL(a.href, location.href);
  if (u.origin !== location.origin || u.pathname === location.pathname) return;
  const dir = location.pathname.replace(/[^/]*$/, '');
  if (!u.pathname.startsWith(dir) || !/\.html?$/.test(u.pathname)) return;
  e.preventDefault(); leave(u.href);
});
addEventListener('pageshow', e => { if (e.persisted && wipeEl) wipeEl.classList.remove('on'); D.documentElement.classList.remove('arrive'); });

/* ---------- площадка (общая разметка) ---------- */
function rinkLines(svg, vw, vh, x0, y0, x1, y1, rr, seed, cls, op) {
  const g = S('g', { opacity: op || .5 }, svg);
  const w = x1 - x0, h = y1 - y0;
  const d = `M${x0 + rr},${y0} L${x1 - rr},${y0} A${rr},${rr} 0 0 1 ${x1},${y0 + rr} L${x1},${y1 - rr} A${rr},${rr} 0 0 1 ${x1 - rr},${y1} L${x0 + rr},${y1} A${rr},${rr} 0 0 1 ${x0},${y1 - rr} L${x0},${y0 + rr} A${rr},${rr} 0 0 1 ${x0 + rr},${y0}Z`;
  ink(g, G && G.path(d, R(seed, .6)), 'mk-pencil', { sw: 2.2 });
  const cx = x0 + w / 2, bl = w * .28;
  rline(g, cx, y0 + 2, cx, y1 - 2, 'mk-red', seed + 1, { sw: 2.2 });
  rline(g, x0 + w / 2 - bl, y0 + 2, x0 + w / 2 - bl, y1 - 2, 'mk-blue', seed + 2, { sw: 2.2 });
  rline(g, x0 + w / 2 + bl, y0 + 2, x0 + w / 2 + bl, y1 - 2, 'mk-blue', seed + 3, { sw: 2.2 });
  ink(g, G && G.circle(cx, y0 + h / 2, h * .3, R(seed + 4, .6)), 'mk-blue', { sw: 1.8 });
  const fx = w * .2, fy = h * .27;
  [[x0 + fx, y0 + h / 2 - fy], [x0 + fx, y0 + h / 2 + fy], [x1 - fx, y0 + h / 2 - fy], [x1 - fx, y0 + h / 2 + fy]].forEach((p, i) => ink(g, G && G.circle(p[0], p[1], h * .17, R(seed + 5 + i, .6)), 'mk-red', { sw: 1.8 }));
  return g;
}

/* ---------- главная: сцена ---------- */
function heroScene() {
  const sc = $('.scene'); if (!sc || !G) return;
  const svg = $('svg', sc);
  rinkLines(svg, 600, 400, 30, 72, 570, 328, 62, 21, '', .55);
  const ghost = S('g', { opacity: .13 }, svg);
  const marks = [[70, 40, 'x'], [540, 38, 'o'], [330, 372, 'x'], [48, 366, 'o'], [560, 360, 'x'], [310, 36, 'o']];
  marks.forEach((q, i) => {
    if (q[2] === 'x') { rline(ghost, q[0] - 9, q[1] - 9, q[0] + 9, q[1] + 9, 'mk-pencil', 40 + i, { sw: 3 }); rline(ghost, q[0] + 9, q[1] - 9, q[0] - 9, q[1] + 9, 'mk-pencil', 50 + i, { sw: 3 }); }
    else ink(ghost, G.circle(q[0], q[1], 20, R(60 + i, .8)), 'mk-pencil', { sw: 3 });
  });
  const arrow = rarrow(svg, [[205, 160], [265, 104], [340, 100], [400, 152]], '', 5, { sw: 3.6 });
  arrow.forEach(p => p.style.strokeWidth = 3.8);
  const dash = ink(svg, G.curve([[210, 252], [275, 292], [335, 292], [395, 254]], R(9, .6, { curveFitting: .95 })), 'mk-pencil', { sw: 2 });
  dash.forEach(p => p.style.strokeDasharray = '3 9');
  if (ANIM && W.DrawSVGPlugin) {
    gsap.set([...arrow, ...dash], { drawSVG: '0%' });
    gsap.set('.scene .lab', { opacity: 0 });
    const run = () => {
      const tl = gsap.timeline({ delay: .25 });
      tl.to(arrow, { drawSVG: '100%', duration: .9, ease: 'power2.inOut', stagger: 0 }, 0)
        .to(dash, { drawSVG: '100%', duration: .7, ease: 'power1.out' }, .3)
        .fromTo('.scene .lab.p2', { opacity: 0, scale: .8 }, { opacity: 1, scale: 1, duration: .35, ease: 'back.out(2)' }, .75)
        .to('.scene .lab.p1, .scene .lab.x', { opacity: 1, duration: .3, stagger: .1 }, .95)
        .from('.scene .mag', { y: -30, opacity: 0, duration: .45, ease: 'power3.out', stagger: .12 }, 0);
    };
    (D.fonts && D.fonts.ready ? D.fonts.ready : Promise.resolve()).then(run);
  }
}

/* ---------- схема «Как думает модель» ---------- */
function routes() {
  const box = $('.play'); if (!box || !G) return;
  const svg = $('svg.route', box); if (!svg) return;
  const draw = () => {
    svg.innerHTML = '';
    if (getComputedStyle(svg).display === 'none') return;
    const b = box.getBoundingClientRect(), st = $$('.step', box);
    svg.setAttribute('viewBox', `0 0 ${b.width} ${b.height}`);
    const out = [];
    for (let i = 0; i < st.length - 1; i++) {
      const a = st[i].getBoundingClientRect(), c = st[i + 1].getBoundingClientRect();
      const x1 = a.right - b.left + 6, x2 = c.left - b.left - 8, y = a.top - b.top + 34;
      out.push(...rarrow(svg, [[x1, y], [(x1 + x2) / 2, y - 20], [x2, y + 4]], i ? 'mk-red' : 'mk-blue', 30 + i, { sw: 3 }));
    }
    if (ANIM && W.DrawSVGPlugin) { gsap.set(out, { drawSVG: '0%' }); onView(box, () => drawIn(out, { stagger: .12, duration: .6 }), .3); }
  };
  draw();
  let t; addEventListener('resize', () => { clearTimeout(t); t = setTimeout(draw, 200); });
}
function corridor() {
  const ax = $('.axis'); if (!ax || !G) return;
  const svg = $('svg', ax);
  svg.setAttribute('viewBox', '0 0 1000 74'); svg.setAttribute('preserveAspectRatio', 'none');
  const p = rline(svg, 0, 40, 1000, 40, '', 77, { sw: 3, ns: true });
  const marks = [];
  $$('.tk', ax).forEach((t, i) => {
    const x = parseFloat(t.style.left) * 10;
    marks.push(...rline(svg, x, 28, x, 52, i === 1 || i === 2 ? 'mk-green' : 'mk-pencil', 80 + i, { sw: 3, ns: true }));
  });
  if (ANIM && W.DrawSVGPlugin) { gsap.set([...p, ...marks], { drawSVG: '0%' }); onView(ax, () => drawIn([...p, ...marks], { duration: .8, stagger: .08 }), .5); }
}

/* ---------- обратный отсчёт ---------- */
function countdown() {
  const el = $('[data-t]'); if (!el) return;
  const t0 = new Date(el.dataset.t.replace(' ', 'T') + ':00+03:00').getTime();
  const out = $('.num', el), lab = $('.l', el);
  const z = n => String(n).padStart(2, '0');
  const tick = () => {
    const d = t0 - Date.now();
    if (d <= 0) { out.textContent = d > -3 * 3600e3 ? 'идёт' : 'сыгран'; lab.textContent = d > -3 * 3600e3 ? 'Матч начался' : 'Матч дня'; return; }
    const s = Math.floor(d / 1e3), dd = Math.floor(s / 86400);
    out.textContent = (dd ? dd + ' д ' : '') + z(Math.floor(s % 86400 / 3600)) + ':' + z(Math.floor(s % 3600 / 60)) + ':' + z(s % 60);
  };
  tick(); setInterval(tick, 1000);
}

/* ---------- фильтры колоды ---------- */
function filtered(boxSel, source, opts) {
  const box = $(boxSel); if (!box) return;
  const limit = opts.limit;
  let f = 'all', all = false;
  const render = () => {
    let list = (f === 'all' && !all && opts.initial) ? opts.initial : source.filter(m => f === 'all' || (f === 'hockey' ? isHockey(m) : f === 'football' ? !isHockey(m) : m.lg === f));
    const total = (f === 'all' && !all && opts.initial) ? source.length : list.length;
    if (!all && limit) list = list.slice(0, limit);
    mountDeck(box, list);
    const more = $(opts.more);
    if (more) { more.hidden = all || total <= limit; more.textContent = 'Показать все матчи (' + total + ')'; }
  };
  $$(opts.chips + ' .chip').forEach(c => c.addEventListener('click', () => {
    f = c.dataset.f; all = false; $$(opts.chips + ' .chip').forEach(x => x.setAttribute('aria-pressed', x === c));
    render();
  }));
  const more = $(opts.more); if (more) more.addEventListener('click', () => { all = true; render(); });
  render();
}

/* ---------- страница хоккея ---------- */
function hockeyPage() {
  const hm = T.matches.filter(m => isHockey(m) && M[m.key]).sort((a, b) => a.t.localeCompare(b.t));
  const hl = hm.filter(m => L[m.key]);
  const set = (id, n) => { const e = $('#' + id); if (e) { e.dataset.count = n; count(e); } };
  set('st-all', hm.length); set('st-line', hl.length); set('st-lg', 2);
  const f = featured();
  const ft = $('#feat'); if (ft && f) mountDeck(ft, [f]);
  const tape = $('.tape-run');
  if (tape) {
    const one = hm.map(m => { const o = M[m.key]; return `<a href="${m.key === f.key ? 'match.html' : '#sevodnya'}">${esc(m.hn)} — ${esc(m.an)} <span>${dayLabel(m)}, ${timeOf(m)}</span> <span>${pc(o.p1)} / ${pc(o.x)} / ${pc(o.p2)}</span></a>`; }).join('');
    tape.innerHTML = one + one;
  }
  filtered('#deck', hm, { limit: 9, more: '#more', chips: '#chips' });
  // таблица: прогноз против линии
  const fc = $('#fc');
  if (fc) {
    const draw = (all) => {
      const list = all ? hm : hm.slice(0, 8);
      fc.innerHTML = list.map(m => {
        const o = M[m.key], sh = share(L[m.key]), tot = o.p1 + o.x + o.p2;
        const bar = (a, b, c, k) => `<div class="bar ${k}" role="img" aria-label="${k === 'mkt' ? 'Линия' : 'Модель'}: П1 ${pc(a)} %, Х ${pc(b)} %, П2 ${pc(c)} %"><i class="h" style="width:${a / (a + b + c) * 100}%"></i><i class="d" style="width:${b / (a + b + c) * 100}%"></i><i class="a" style="width:${c / (a + b + c) * 100}%"></i></div>`;
        const lk = m.key === f.key ? 'match.html' : (LK[m.key] ? '../../' + LK[m.key] : '#');
        return `<a class="row" href="${lk}"><div class="who">${esc(m.hn)} — ${esc(m.an)}<small>${LG[m.lg]}, ${dayLabel(m)}, ${timeOf(m)}</small></div>
        <div class="scale">${bar(o.p1, o.x, o.p2, 'mod')}<div class="nums"><span class="h">П1 ${pc(o.p1)} %</span><span class="d">Х ${pc(o.x)} %</span><span class="a">П2 ${pc(o.p2)} %</span></div></div>
        <div class="cols"><small><span>Линия без маржи</span><span>${sh ? sh.map(v => pc(v)).join(' / ') + ' %' : 'нет линии'}</span></small>${sh ? bar(sh[0], sh[1], sh[2], 'mkt') : ''}</div></a>`;
      }).join('');
    };
    draw(false);
    const mb = $('#fc-more'); if (mb) mb.addEventListener('click', () => { draw(true); mb.hidden = true; });
  }
  // лиги и клубы
  ['khl', 'nhl'].forEach(k => {
    const box = $('#mags-' + k); if (!box) return;
    const teams = new Map();
    hm.filter(m => m.lg === k).forEach(m => { teams.set(m.h, m.hn); teams.set(m.a, m.an); });
    box.innerHTML = [...teams].map(([id, n], i) => `<span class="mg" style="--c:${clubColor(id)};--r:${(((i * 29) % 7) - 3) * 1.4}deg" title="${esc(n)}"><img src="../../assets/em/${esc(id)}.webp" alt="${esc(n)}" data-n="${esc(n)}" width="32" height="32" loading="lazy"></span>`).join('');
  });
  // вкладки таблицы
  const SH = {
    elo: ['Рейтинг Эло', ['Сила каждой команды одним числом. Рейтинг пересчитывается после каждого матча: победа над сильным соперником стоит больше, чем над слабым.'], ['Все команды лиги в одном списке', 'Как менялась сила команды за сезон', 'Поправка на игру: броски в створ и шайбы сверх ожидания'], 'Рейтинг Эло появится на сайте, когда подключим его расчёт. В таблице лист уже есть.'],
    fc: ['Прогнозы', ['Все матчи ближайших дней на одном листе: время по Москве, прогноз модели, коэффициенты и вероятность. После игры рядом появляется счёт.'], ['КХЛ и НХЛ', 'Расчёт модели рядом с линией', 'Обновляется каждое утро']],
    hit: ['Что заходит', ['Как часто у каждой команды случается то или иное событие за сезон: победа, тотал больше или меньше, игра в овертайм.'], ['Видно сильные и слабые стороны каждой команды', 'Конструктор матча: выбираешь две команды и видишь, что вероятнее в их игре'], 'Цифры по сезону появятся здесь после подключения данных.'],
    sch: ['Расписание', ['Все матчи сезона с датой и временем по Москве. У сыгранных стоит счёт, отмечены овертаймы и буллиты.'], ['Сегодня, завтра и вся неделя', 'Ночные матчи НХЛ собраны в один игровой день']],
    his: ['История', ['Каждый прогноз остаётся в таблице: зашёл или нет и по какому кэфу. Видно, как часто модель угадывает и как менялся банк на дистанции.'], ['Точность модели по фаворитам и аутсайдерам', 'Ничего не удаляется'], 'История и итоги по месяцам появятся на сайте после подключения базы итогов. Пока: в канале каждое утро.'],
    more: ['И ещё', ['Мы показали 5 листов. Всего в таблице их больше 20: коэффициенты, купон дня, точность модели, карточки команд, статистика, травмы и ключевые игроки.'], ['Коэффициенты: линия на ближайшие матчи и итоги прошлых', 'Модель против рынка: чья оценка точнее', 'Купон дня и «Мой купон»: собрать свой и посчитать вероятность', 'Банкролл: симуляция на дистанции', 'Карточка команды, статистика, ключевые игроки, досье, разбор перед матчем']]
  };
  const tabs = $('#tabs'), panel = $('#panel');
  if (tabs && panel) {
    tabs.innerHTML = Object.entries(SH).map(([k, v], i) => `<button role="tab" id="tab-${k}" aria-selected="${i === 1}" aria-controls="panel" data-k="${k}">${v[0]}</button>`).join('');
    const show = k => {
      const v = SH[k];
      $$('button', tabs).forEach(b => b.setAttribute('aria-selected', b.dataset.k === k));
      panel.setAttribute('aria-labelledby', 'tab-' + k);
      panel.innerHTML = `<h3>${v[0]}</h3>${v[1].map(t => `<p>${t}</p>`).join('')}<ul>${v[2].map(t => `<li>${t}</li>`).join('')}</ul>${v[3] ? `<span class="soon-t">Скоро</span><p>${v[3]}</p>` : ''}`;
    };
    tabs.addEventListener('click', e => { const b = e.target.closest('button'); if (b) show(b.dataset.k); });
    show('fc');
  }
  countdown();
}

/* ---------- главная ---------- */
function homePage() {
  const hk = T.matches.filter(m => isHockey(m) && M[m.key]).sort((a, b) => a.t.localeCompare(b.t));
  const fb = T.matches.filter(m => !isHockey(m) && M[m.key] && L[m.key]).sort((a, b) => a.t.localeCompare(b.t));
  const list = [...hk.slice(0, 4), ...fb.slice(0, 2)].sort((a, b) => a.t.localeCompare(b.t));
  const pool = [...hk, ...fb];
  filtered('#deck', pool, { initial: list, limit: 6, more: '#more', chips: '#chips' });
  heroScene(); routes(); corridor();
}

/* ---------- страница матча ---------- */
const FORM = {
  h: [['П', '22.10', 'дома Нефтехимик', '2:3'], ['В', '26.10', 'в гостях Динамо Москва', '3:2 (ОТ)'], ['В', '28.10', 'в гостях Ак Барс', '4:0'], ['П', '30.10', 'в гостях Лада', '2:3 (ОТ)'], ['П', '01.11', 'в гостях Сочи', '1:2 (ОТ)']],
  a: [['П', '23.10', 'в гостях Автомобилист', '1:5'], ['В', '25.10', 'в гостях СКА', '3:1'], ['В', '28.10', 'дома Трактор', '5:1'], ['В', '01.11', 'в гостях Трактор', '3:2 (ОТ)'], ['В', '03.11', 'в гостях Металлург', '7:3']]
};
function ruleTables() {
  $$('.marked').forEach(w => {
    let svg = $('svg.rules', w); if (svg) svg.remove();
    if (!G) return;
    svg = S('svg', { class: 'rules', 'aria-hidden': 'true' }, w);
    const wr = w.getBoundingClientRect(), t = $('table', w), tw = t.offsetWidth;
    svg.setAttribute('viewBox', `0 0 ${Math.max(wr.width, tw)} ${t.offsetHeight}`);
    svg.style.width = Math.max(wr.width, tw) + 'px';
    const rows = $$('tr', t); let i = 0;
    const paths = [];
    rows.forEach((r, k) => {
      const y = r.getBoundingClientRect().bottom - t.getBoundingClientRect().top;
      paths.push(...rline(svg, 0, y, tw, y, k === 0 ? '' : 'mk-pencil', 90 + k + i++, { sw: k === 0 ? 3 : 1.8 }));
    });
    [0, tw].forEach((x, k) => paths.push(...rline(svg, x, 0, x, t.offsetHeight, '', 120 + k, { sw: 2.2 })));
    if (ANIM && W.DrawSVGPlugin && !w.dataset.done) { w.dataset.done = 1; gsap.set(paths, { drawSVG: '0%' }); onView(w, () => drawIn(paths, { duration: .8, stagger: .05 }), .25); }
  });
}
function matchPage() {
  const key = 'khl|2026-11-05|avangard|cska', mod = M[key], ln = L[key];
  const m = T.matches.find(x => x.key === key);
  if (!mod || !m) return;
  const tot = mod.p1 + mod.x + mod.p2, a = mod.p1 / tot, b = mod.x / tot, c = mod.p2 / tot;
  const board = $('.rink'), svg = $('svg', board);
  svg.innerHTML = '';
  const VW = 800, VH = 340, x0 = 10, x1 = 790, y0 = 10, y1 = 330;
  svg.setAttribute('viewBox', `0 0 ${VW} ${VH}`);
  const defs = S('defs', {}, svg);
  const cp = S('clipPath', { id: 'rk' }, defs);
  S('rect', { x: x0, y: y0, width: x1 - x0, height: y1 - y0, rx: 84 }, cp);
  const w = x1 - x0, xa = x0 + w * a, xb = xa + w * b;
  const clip = S('g', { 'clip-path': 'url(#rk)' }, svg);
  const zones = [[x0, xa, 'mk-blue', -45, 1], [xa, xb, 'mk-pencil', 0, 2], [xb, x1, 'mk-red', 45, 3]].map(z => {
    const g = S('g', { class: 'zone' }, clip);
    ink(g, G && G.rectangle(z[0], y0, z[1] - z[0], y1 - y0, { roughness: .8, stroke: 'none', fill: '#000', fillStyle: z[4] === 2 ? 'cross-hatch' : 'hatch', hachureGap: z[4] === 2 ? 15 : 9, hachureAngle: z[3] || -45, fillWeight: 1.6, seed: 200 + z[4] }), z[2], { sw: 1.7 });
    return g;
  });
  rinkLines(svg, VW, VH, x0, y0, x1, y1, 84, 300, '', .8);
  const sep = [...rline(svg, xa, y0, xa, y1, '', 310, { sw: 3.2 }), ...rline(svg, xb, y0, xb, y1, '', 311, { sw: 3.2 })];
  const lam = mod.lam || [2.3, 2.4];
  const ar1 = rarrow(svg, [[96, 92], [330, 70], [560, 96], [724, 84]], 'mk-blue', 320, { sw: lam[0] * 3.2 });
  const ar2 = rarrow(svg, [[704, 252], [470, 276], [250, 248], [88, 262]], 'mk-red', 330, { sw: lam[1] * 3.2 });
  ar1.forEach(p => p.style.strokeWidth = lam[0] * 3.2); ar2.forEach(p => p.style.strokeWidth = lam[1] * 3.2);
  // подписи зон
  const pos = (n, cx) => { const e = $(n); if (e) e.style.left = (cx / VW * 100) + '%'; };
  [['.z.h', (x0 + xa) / 2], ['.z.d', (xa + xb) / 2], ['.z.a', (xb + x1) / 2]].forEach(q => { const e = $(q[0], board); e.style.left = ((q[1] - (q[1] === (xa + xb) / 2 ? 0 : 0)) / VW * 100) + '%'; e.style.transform = 'translateX(-50%)'; });
  const pl = $('.rink .zone-pct'); void pl; void pos;
  // анимация
  const nums = $$('.rink .z .num');
  nums.forEach(n => { n.dataset.count = n.dataset.v; count(n); });
  if (ANIM && W.DrawSVGPlugin) {
    gsap.set(zones, { opacity: 0 }); gsap.set([...sep, ...ar1, ...ar2], { drawSVG: '0%' }); gsap.set('.rink .lam, .rink .z small', { opacity: 0 });
    const run = () => {
      const tl = gsap.timeline({ delay: .2 });
      zones.forEach((z, i) => tl.fromTo(z, { opacity: 0, scaleX: .2, transformOrigin: i === 2 ? '100% 50%' : '0% 50%' }, { opacity: 1, scaleX: 1, duration: .55, ease: 'power2.out' }, i * .28));
      tl.to(sep, { drawSVG: '100%', duration: .5 }, .45)
        .to('.rink .z small', { opacity: 1, duration: .3, stagger: .15 }, .6)
        .to(ar1, { drawSVG: '100%', duration: .8, ease: 'power2.inOut' }, 1.0)
        .to(ar2, { drawSVG: '100%', duration: .8, ease: 'power2.inOut' }, 1.2)
        .to('.rink .lam', { opacity: 1, duration: .3, stagger: .15 }, 1.6);
    };
    (D.fonts && D.fonts.ready ? D.fonts.ready : Promise.resolve()).then(run);
  }
  // плашка тотала
  const pl2 = $('.plate');
  if (pl2 && G) {
    const s2 = S('svg', { 'aria-hidden': 'true' }, pl2); s2.setAttribute('viewBox', '0 0 100 40'); s2.setAttribute('preserveAspectRatio', 'none');
    const pp = ink(s2, G.rectangle(2, 2, 96, 36, R(70, .7)), 'mk-red', { sw: 2.4, ns: true });
    if (ANIM && W.DrawSVGPlugin) { gsap.set(pp, { drawSVG: '0%' }); onView(pl2, () => drawIn(pp, { duration: .8 }), .6); }
  }
  // форма
  ['h', 'a'].forEach(k => {
    const box = $('#form-' + k); if (!box) return;
    box.innerHTML = `<div class="five">${FORM[k].map((g, i) => `<span class="fm ${g[0] === 'В' ? 'w' : 'l'}" style="--r:${(((i * 3 + (k === 'a' ? 1 : 0)) % 5) - 2) * 3}deg" title="${g[1]}, ${g[2]}, ${g[3]}">${g[0]}</span>`).join('')}</div>
    <ul class="games">${FORM[k].map(g => `<li><span class="d">${g[1]}</span><span>${g[2]}</span><span class="s">${g[3]}</span></li>`).join('')}</ul>`;
  });
  // таблицы
  (D.fonts && D.fonts.ready ? D.fonts.ready : Promise.resolve()).then(() => { ruleTables(); });
  let rt; addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(ruleTables, 200); });
  countdown();
  // другие матчи
  const oth = $('#others');
  if (oth) {
    oth.innerHTML = T.matches.filter(x => x.lg === 'khl' && x.key !== key && x.t.slice(0, 10) === m.t.slice(0, 10) && M[x.key]).map(x => `<a href="${LK[x.key] ? '../../' + LK[x.key] : '#'}">${esc(x.hn)} — ${esc(x.an)}<span>${timeOf(x)} МСК</span></a>`).join('');
  }
}

/* ---------- запуск ---------- */
const page = D.body.dataset.page;
underlines();
if (page === 'home') homePage();
if (page === 'hockey') hockeyPage();
if (page === 'match') matchPage();
$$('[data-count]').forEach(count);
})();
