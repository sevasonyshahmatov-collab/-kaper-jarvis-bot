/* «Джамботрон»: общий скрипт трёх страниц. Данные только настоящие (../../data/*.js), всё из данных экранируем.
   Анимируются только transform/opacity/clip-path; при prefers-reduced-motion цифры сразу итоговые, ленты и волны выключены. */
(() => {
'use strict';
const L = window.JV_LINES || {}, M = window.JV_MODEL || {}, TD = window.JV_TODAY || { matches: [], days: [] };
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const FINE = matchMedia('(hover: hover) and (pointer: fine)').matches;
const $ = (s, r) => (r || document).querySelector(s), $$ = (s, r) => [...(r || document).querySelectorAll(s)];
const esc = t => String(t == null ? '' : t).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const f2 = v => (+v).toFixed(2).replace('.', ','), f1 = v => (+v).toFixed(1).replace('.', ',');
const p0 = v => Math.round(v * 100);
const LG = { khl: 'КХЛ', nhl: 'НХЛ', epl: 'АПЛ', laliga: 'Ла Лига', seriea: 'Серия А', bundesliga: 'Бундеслига', ligue1: 'Лига 1', ucl: 'Лига чемпионов', uel: 'Лига Европы', rpl: 'РПЛ' };
const isH = m => m.lg === 'khl' || m.lg === 'nhl';
const emb = (m, id) => `../../assets/${isH(m) ? 'em' : 'fc'}/${encodeURIComponent(id)}.webp`;
const DEF = 'khl|2026-11-05|avangard|cska';
const href = m => m.key === DEF ? 'match.html' : 'match.html?k=' + encodeURIComponent(m.key);

/* демо-часы: данные сняты 05.11 в 04:23 МСК, поэтому «сейчас» идёт от этого момента (?t=16:45 — другое время того дня) */
const q = new URLSearchParams(location.search);
const BASE = (() => { const t = /^\d\d:\d\d$/.test(q.get('t') || '') ? q.get('t') : '04:23'; return Date.parse('2026-11-05T' + t + ':00+03:00'); })();
const T0 = performance.now();
const now = () => BASE + (performance.now() - T0);
const startMs = m => Date.parse(m.t.replace(' ', 'T') + ':00+03:00');
const live = m => { const n = now(), s = startMs(m); return n >= s && n < s + 3.5 * 36e5; };
const hhmm = m => m.t.slice(11, 16);
const dayWord = m => (TD.days || [])[0] === m.t.slice(0, 10) ? 'Сегодня' : 'Завтра';
const mdl = m => M[m.key], lin = m => L[m.key];
const all = (TD.matches || []).filter(m => M[m.key]).sort((a, b) => a.t.localeCompare(b.t) || a.key.localeCompare(b.key));
const upcoming = all.filter(m => startMs(m) + 3.5 * 36e5 > now());

/* ── карточки ── */
const probs = m => { const d = mdl(m); return d ? [['П1', d.p1], ['Х', d.x], ['П2', d.p2]] : []; };
const maxI = a => a.reduce((b, v, i) => v[1] > a[b][1] ? i : b, 0);
function card(m) {
  const pr = probs(m), mi = maxI(pr), ln = lin(m);
  const kf = ln ? `<div class="kf"><span>кэфы, справка</span><b>${f2(ln.p1)}</b><b>${f2(ln.x)}</b><b>${f2(ln.p2)}</b></div>` : '';
  return `<a class="pn mc tilt${live(m) ? ' live' : ''}" href="${href(m)}" data-k="${esc(m.key)}"><i class="wave"></i>
  <div class="hd2"><span class="lab">${esc(LG[m.lg] || m.lg)}, ${esc(dayWord(m).toLowerCase())}</span>${live(m) ? '<span class="livetag">идёт матч</span>' : `<b>${hhmm(m)}</b>`}</div>
  <div class="tm"><span class="team"><img src="${emb(m, m.h)}" alt="" loading="lazy" width="36" height="36">${esc(m.hn)}</span><span class="team"><img src="${emb(m, m.a)}" alt="" loading="lazy" width="36" height="36">${esc(m.an)}</span></div>
  <div class="pp">${pr.map((p, i) => `<div class="${i === mi ? 'mx' : ''}"><span class="lab">${p[0]}, %</span><span class="led am" aria-label="${p0(p[1])} процентов">${p0(p[1])}</span></div>`).join('')}</div>${kf}</a>`;
}
function row(m) {
  const pr = probs(m), mi = maxI(pr);
  return `<a class="pn mr tilt${live(m) ? ' live' : ''}" href="${href(m)}" data-k="${esc(m.key)}"><i class="wave"></i>
  <span class="tt">${live(m) ? '<span class="livetag">идёт</span>' : hhmm(m)}</span>
  <span class="tm2"><span><img src="${emb(m, m.h)}" alt="" width="26" height="26" loading="lazy">${esc(m.hn)}</span><span><img src="${emb(m, m.a)}" alt="" width="26" height="26" loading="lazy">${esc(m.an)}</span><span class="lab">${esc(LG[m.lg])}, ${esc(dayWord(m).toLowerCase())}</span></span>
  ${pr.map((p, i) => `<span class="p"><span class="lab">${p[0]}${i === mi ? ', вероятнее' : ''}</span><span class="led ${i === mi ? 'am' : 'hi'}" ${i === mi ? '' : 'style="--c:var(--mute)"'}>${p0(p[1])}</span></span>`).join('')}</a>`;
}

/* ── split-flap ── */
const RU = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', DG = '0123456789';
const flapHTML = (txt, words) => [...txt].map(ch => {
  const sp = ch === ' ' || ch === ':' || ch === '-' || ch === '—';
  return `<span class="fc${sp ? ' sp' : ''}" aria-hidden="true"><span>${ch === ' ' ? '&nbsp;' : esc(ch)}</span></span>`;
}).join('');
const ticking = [];
let tick = 0;
function pump() {
  if (tick) return;
  tick = setInterval(() => {
    for (let i = ticking.length - 1; i >= 0; i--) {
      const c = ticking[i];
      c.n--;
      c.el.textContent = c.n <= 0 ? c.fin : c.pool[(c.i0 + (c.steps - c.n)) % c.pool.length];
      if (!RM) c.el.animate([{ transform: 'rotateX(-80deg)', opacity: 0.3 }, { transform: 'rotateX(0)', opacity: 1 }], { duration: 40, easing: 'ease-out' });
      if (c.n <= 0) ticking.splice(i, 1);
    }
    if (!ticking.length) { clearInterval(tick); tick = 0; }
  }, 40);
}
function flapRun(el) {
  const txt = el.dataset.f; if (el.dataset.run) return; el.dataset.run = '1';
  const cells = $$('.fc > span', el);
  [...txt].forEach((ch, idx) => {
    const c = cells[idx]; if (!c) return;
    const up = ch.toUpperCase(), pool = DG.includes(ch) ? DG : (RU.includes(up) ? RU : null);
    if (!pool || RM) { c.textContent = ch; return; }
    const steps = Math.min(22, 5 + idx * 2 + (pool === DG ? 3 : 0));
    const fi = pool.indexOf(pool === DG ? ch : up);
    ticking.push({ el: c, n: steps, steps, pool, fin: pool === DG ? ch : up, i0: ((fi - steps + 1) % pool.length + pool.length) % pool.length });
    c.textContent = pool[((fi - steps) % pool.length + pool.length) % pool.length];
  });
  pump();
}
function flapInit(el) {
  el.dataset.init = '1';
  const raw = el.dataset.f || el.textContent.trim(); el.dataset.f = raw;
  const txt = el.classList.contains('words') ? raw.toUpperCase() : raw; el.dataset.f = txt;
  el.setAttribute('role', 'img'); el.setAttribute('aria-label', raw);
  el.innerHTML = flapHTML(txt);
  if (!RM) { $$('.fc > span', el).forEach(s => { s.textContent = '\u00a0'; }); }
  return el;
}
function flapSet(el, txt) { /* обновление без пересчёта: меняем только отличающиеся ячейки */
  const cells = $$('.fc > span', el), old = el.dataset.f; el.dataset.f = txt;
  if (cells.length !== txt.length) { el.innerHTML = flapHTML(txt); return; }
  [...txt].forEach((ch, i) => { if (old[i] !== ch) { cells[i].textContent = ch; if (!RM) cells[i].animate([{ transform: 'rotateX(-80deg)', opacity: 0.3 }, { transform: 'rotateX(0)', opacity: 1 }], { duration: 40, easing: 'ease-out' }); } });
}

/* ── LED-цифры «как счёт» ── */
function ledDigits(el, n) { el.innerHTML = [...String(n).padStart(2, '0')].map(d => `<span class="dg">${d}</span>`).join(''); }
function countTo(el, n) {
  el.setAttribute('aria-label', n + ' процентов');
  if (RM || n < 1) { ledDigits(el, n); return; }
  const inc = Math.max(1, Math.ceil(n / 24)); let v = 0; ledDigits(el, 0);
  const t = setInterval(() => { v = Math.min(n, v + inc); ledDigits(el, v); if (v >= n) clearInterval(t); }, 40);
}

/* ── наблюдатель: запуск при появлении ── */
const io = 'IntersectionObserver' in window ? new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return; const el = e.target; io.unobserve(el);
  if (el.classList.contains('flap')) flapRun(el);
  if (el.classList.contains('pn') && !FINE) { el.classList.add('on'); setTimeout(() => el.classList.remove('on'), 900); }
  if (el.dataset.count) countTo(el, +el.dataset.count);
  if (el.classList.contains('col')) el.style.setProperty('--h', el.dataset.h + '%');
  if (el.classList.contains('bar')) { const t = $('.tr', el); t.style.setProperty('--w', el.dataset.w + '%'); }
  if (el.classList.contains('scoreboard')) { const f = $('.sb-flash', el); if (f && !RM) f.classList.add('go'); }
}), { threshold: 0.35 }) : null;
const watch = el => { if (io) io.observe(el); else { if (el.classList.contains('flap')) flapRun(el); if (el.dataset.count) countTo(el, +el.dataset.count); if (el.dataset.h) el.style.setProperty('--h', el.dataset.h + '%'); } };

function enhance(root) {
  $$('.flap', root).forEach(el => { if (!el.dataset.run && !el.dataset.init) { el.dataset.init = '1'; flapInit(el); watch(el); } });
  $$('[data-count]', root).forEach(el => { ledDigits(el, 0); watch(el); });
  $$('.col', root).forEach(watch);
  $$('.bar', root).forEach(watch);
  if (!FINE) $$('.pn.mc, .pn.mr', root).forEach(el => { if (io) io.observe(el); });
  if (FINE && !RM) $$('.tilt', root).forEach(el => {
    el.addEventListener('pointermove', e => { const r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5; el.style.setProperty('--ry', (x * 5).toFixed(2) + 'deg'); el.style.setProperty('--rx', (-y * 4).toFixed(2) + 'deg'); });
    el.addEventListener('pointerleave', () => { el.style.setProperty('--ry', '0deg'); el.style.setProperty('--rx', '0deg'); });
  });
}

/* ── общий переход: эмблема перелетает в шапку матча ── */
document.addEventListener('click', e => {
  const a = e.target.closest && e.target.closest('a[href*="match.html"]'); if (!a) return;
  $$('.vtn').forEach(x => x.classList.remove('vtn'));
  const im = $('.team img, .tm2 img', a); if (im) im.classList.add('vtn');
});

/* ── кольцевая лента ── */
function ring() {
  const list = upcoming.slice(0, 18); if (!list.length) return;
  const item = m => { const d = mdl(m); return `<a class="ri" href="${href(m)}"><span class="mono">${hhmm(m)}</span><span>${esc(m.hn)} — ${esc(m.an)}</span><b>${p0(d.p1)}</b><i>${p0(d.x)}</i><b>${p0(d.p2)}</b></a>`; };
  const tr = `<div class="rtrack">${list.map(item).join('')}${list.map(item).join('')}</div>`;
  const d = document.createElement('div'); d.className = 'ring'; d.setAttribute('role', 'region'); d.setAttribute('aria-label', 'Лента матчей дня: время, команды, вероятности П1, Х, П2 в процентах. Наведите курсор, чтобы остановить');
  d.innerHTML = ['t', 'r', 'b', 'l'].map(s => `<div class="rs rs-${s}">${tr}</div>`).join('');
  document.body.appendChild(d); document.body.classList.add('has-ring');
  /* на телефоне лента нажатием останавливается и запускается */
  $$('.rs-t,.rs-b', d).forEach(s => s.addEventListener('pointerdown', () => { if (!FINE) s.classList.toggle('stop'); }));
}
function marquee(el, list) {
  const item = m => { const d = mdl(m); return `<a class="ri" href="${href(m)}"><span class="mono">${hhmm(m)}</span><span>${esc(m.hn)} — ${esc(m.an)}</span><b>${p0(d.p1)}</b><i>${p0(d.x)}</i><b>${p0(d.p2)}</b></a>`; };
  el.innerHTML = `<div class="rtrack">${list.map(item).join('')}${list.map(item).join('')}</div>`;
}

/* ── табло дня и таймер ── */
function board(m) {
  const pr = probs(m), mi = maxI(pr), s = startMs(m);
  const root = $('#board'); if (!root) return;
  $('.bd-lg', root).textContent = LG[m.lg] + ', ' + dayWord(m).toLowerCase();
  $('.bd-tm', root).textContent = live(m) ? 'идёт матч' : hhmm(m) + ' МСК';
  $$('.bd-h', root).forEach(e => { e.dataset.f = m.hn; e.setAttribute('aria-label', m.hn); }); $$('.bd-a', root).forEach(e => { e.dataset.f = m.an; });
  $$('.bd-hi,.bd-hi2').forEach(e => { e.src = emb(m, m.h); }); $$('.bd-ai,.bd-ai2').forEach(e => { e.src = emb(m, m.a); });
  $$('.pc', root).forEach((c, i) => { c.classList.toggle('max', i === mi); $('.flap', c).dataset.f = String(p0(pr[i][1])); });
  const a = $('a.btn', root); if (a) a.href = href(m);
  root.classList.toggle('live', live(m));
}
function countdown(el, m) {
  const s = startMs(m);
  const fmt = () => { let d = Math.max(0, Math.floor((s - now()) / 1000)); const h = Math.floor(d / 3600), mi = Math.floor(d % 3600 / 60), sc = d % 60; return [h, mi, sc].map(v => String(v).padStart(2, '0')).join(':'); };
  el.dataset.f = fmt(); flapInit(el); watch(el);
  setInterval(() => { if (document.hidden || !el.dataset.run) return; flapSet(el, fmt()); }, 1000);
}

/* ── сборка страниц ── */
const page = document.body.dataset.page;
if (page === 'home') {
  ring();
  const hockey = upcoming.filter(isH).slice(0, 6), foot = upcoming.filter(m => !isH(m)).slice(0, 3);
  const box = $('#mgrid'); let cur = 'all';
  const draw = () => { const l = cur === 'h' ? upcoming.filter(isH).slice(0, 6) : cur === 'f' ? upcoming.filter(m => !isH(m)).slice(0, 6) : hockey.concat(foot); box.innerHTML = l.map(card).join(''); enhance(box); };
  $$('.tab').forEach(t => t.addEventListener('click', () => { cur = t.dataset.t; $$('.tab').forEach(x => x.setAttribute('aria-selected', x === t ? 'true' : 'false')); draw(); }));
  draw();
}
if (page === 'hockey') {
  const hk = upcoming.filter(isH);
  marquee($('#mq'), hk.slice(0, 14));
  const box = $('#mlist'); let cur = 'all';
  const draw = () => {
    const l = hk.filter(m => cur === 'all' || m.lg === cur); let day = '', out = '';
    l.forEach(m => { const dw = dayWord(m); if (dw !== day) { day = dw; out += `<p class="lab" style="margin-top:10px">${dw}</p>`; } out += row(m); });
    box.innerHTML = out; enhance(box);
  };
  $$('.tab').forEach(t => t.addEventListener('click', () => { cur = t.dataset.t; $$('.tab').forEach(x => x.setAttribute('aria-selected', x === t ? 'true' : 'false')); draw(); }));
  draw();
  const n1 = $('#fN'), n2 = $('#fP'); if (n1) { n1.dataset.count = hk.length; n2.dataset.count = hk.filter(m => lin(m)).length; }
  /* лиги и клубы */
  ['khl', 'nhl'].forEach(lg => {
    const seen = {}, out = []; hk.filter(m => m.lg === lg).forEach(m => [[m.h, m.hn], [m.a, m.an]].forEach(([id, n]) => { if (!seen[id]) { seen[id] = 1; out.push(`<a href="../../team/index.html?id=${encodeURIComponent(id)}"><img src="../../assets/em/${encodeURIComponent(id)}.webp" alt="" width="40" height="40" loading="lazy">${esc(n)}</a>`); } }));
    const e = $('#logos-' + lg); if (e) e.innerHTML = out.join('');
  });
  /* прогноз модели против линии */
  const cm = $('#cmp');
  if (cm) {
    cm.innerHTML = hk.slice(0, 8).map(m => {
      const d = mdl(m), ln = lin(m); let fair = null;
      if (ln) { const inv = [1 / ln.p1, 1 / ln.x, 1 / ln.p2], s = inv[0] + inv[1] + inv[2]; fair = inv.map(v => v / s); }
      const v = [d.p1, d.x, d.p2], lab = ['П1', 'Х', 'П2'];
      return `<a class="pn cmpr tilt" href="${href(m)}"><i class="wave"></i><b>${esc(m.hn)} — ${esc(m.an)}<span class="lab" style="display:block;font-weight:400">${esc(LG[m.lg])}, ${hhmm(m)} МСК</span></b><span class="bars3">${v.map((p, i) => `<span class="bar" data-w="${p0(p) }"><span>${lab[i]}</span><span class="tr"><i></i>${fair ? `<em style="--m:${(fair[i] * 100).toFixed(0)}%" title="доля линии без маржи"></em>` : ''}</span><b>${p0(p)}%</b></span>`).join('')}</span></a>`;
    }).join(''); enhance(cm);
  }
}
if (page === 'match') {
  const k = q.get('k'), m = k && all.find(x => x.key === k);
  if (m && m.key !== DEF) {
    const d = mdl(m), ln = lin(m), pr = probs(m), mi = maxI(pr);
    $$('[data-hn]').forEach(e => { e.textContent = m.hn; }); $$('[data-an]').forEach(e => { e.textContent = m.an; });
    $$('[data-ht]').forEach(e => { e.textContent = hhmm(m) + ' МСК'; }); $$('[data-lg]').forEach(e => { e.textContent = LG[m.lg]; });
    $('#hi').src = emb(m, m.h); $('#ai').src = emb(m, m.a); document.title = m.hn + ' — ' + m.an + ': прогноз на матч, ' + LG[m.lg];
    $$('.sb-col').forEach((c, i) => { c.classList.toggle('max', i === mi); $('.led', c).dataset.count = p0(pr[i][1]); $('.col', c).dataset.h = Math.round(pr[i][1] * 100 / 0.6 > 100 ? 100 : pr[i][1] * 100 / 0.6); });
    if (ln) { const o = $$('.od b'); [ln.p1, ln.x, ln.p2, ln.over, ln.under].forEach((v, i) => { if (o[i]) o[i].textContent = v ? f2(v) : '—'; }); }
    const lam = d.lam; $('#lam').textContent = lam ? f1(lam[0]) + ' : ' + f1(lam[1]) : '—';
    $('#totv').dataset.count = p0(d.over); $('#totl').textContent = 'Тотал ' + f1(d.tot).replace(',', ',') + ': больше';
    $$('.only-def').forEach(e => { e.hidden = true; }); $$('.only-oth').forEach(e => { e.hidden = false; });
    const mm = $('#mmeta'); if (mm) mm.textContent = 'Данные обновлены ' + (TD.built || '').slice(8, 10) + '.' + (TD.built || '').slice(5, 7) + ' в ' + (TD.built || '').slice(11, 16) + ' МСК.';
    if (live(m)) $('.scoreboard').classList.add('live');
    countdown($('#cdm'), m);
  } else {
    const dm = all.find(x => x.key === DEF); if (dm) { countdown($('#cdm'), dm); if (live(dm)) $('.scoreboard').classList.add('live'); }
  }
  /* прочие матчи дня */
  const oth = $('#oth'); if (oth) { const cur = (m && m.key) || DEF; oth.innerHTML = all.filter(x => x.lg === (m ? m.lg : 'khl') && x.t.slice(0, 10) === (m ? m.t : '2026-11-05').slice(0, 10) && x.key !== cur && isH(x)).slice(0, 6).map(x => `<a class="pn" href="${href(x)}"><i class="wave"></i><span>${esc(x.hn)} — ${esc(x.an)}</span><span class="tt">${hhmm(x)} МСК</span></a>`).join(''); }
}
if (page === 'home' || page === 'hockey') { const m = all.find(x => x.key === DEF); if (m) { board(m); const c = $('#cd'); if (c) countdown(c, m); } }
enhance(document);
/* волна при загрузке на «Матче дня»: сразу один раз, чтобы табло выглядело включённым */
$$('.pn.mc, .pn.mr').forEach(() => 0);
})();
