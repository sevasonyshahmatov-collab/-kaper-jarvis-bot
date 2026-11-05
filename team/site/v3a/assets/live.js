/* JARVIS v3a — живой счёт (вариант 1: браузер сам берёт счёт из открытых API; при запуске переносится на Cloudflare Worker, см. live/README.md).
   Элементы с атрибутом data-lv (data-lv-lg, data-lv-t = начало ISO, data-lv-h/-a = id клубов, -hn/-an = названия). Страницы матчей, «Прогноз на сегодня»,
   «Мои матчи». Опрос раз в 30 с только пока вкладка видна и только в окне матча (от начала по расписанию до ~3,5 ч после, пока не «финал»).
   Лиги: НХЛ и футбол — ESPN scoreboard (CORS *), КХЛ — приложение КХЛ events_v2 (CORS для нашего origin). Кэфов в лайве нет. Вывод — только textContent.
   Любая ошибка (сеть, CORS, формат) — тихо ничего не показываем. */
(() => {
'use strict';
if (window.JV_LIVE_OFF) return;
const POLL = 30000, WIN = 3.5 * 36e5, WIN_LIVE = 6 * 36e5, FAILS = 3;
const ESPN = 'https://site.api.espn.com/apis/site/v2/sports/';
const ESPN_LG = {nhl: 'hockey/nhl', epl: 'soccer/eng.1', laliga: 'soccer/esp.1', seriea: 'soccer/ita.1', bundesliga: 'soccer/ger.1', ligue1: 'soccer/fra.1',
  rpl: 'soccer/rus.1', ucl: 'soccer/uefa.champions', uel: 'soccer/uefa.europa'};
const KHL_BASE = 'https://khl.api.webcaster.pro/api/khl_mobile/';
const KHL_STAGE = 407;                       /* current_stage_id регулярки 2026/27; data.json с браузера отдаёт 403, поэтому номер зашит (обновить к плей-офф) */
const KHL_TID = {8: 'dinamo_msk', 10: 'avangard', 12: 'amur', 16: 'cska', 18: 'spartak', 22: 'torpedo', 24: 'sibir', 26: 'lokomotiv', 28: 'traktor', 30: 'metallurg',
  32: 'salavat', 36: 'neftekhimik', 38: 'dinamo_minsk', 40: 'akbars', 42: 'severstal', 44: 'ska', 46: 'barys', 56: 'avtomobilist', 61: 'admiral', 105: 'lada',
  113: 'sochi', 315: 'shanghai'};
const HOCKEY = {khl: 1, nhl: 1};
const me = document.currentScript;
const BASE = me && me.src ? me.src.replace(/[^/]*$/, '') : '';
const reduce = () => matchMedia('(prefers-reduced-motion:reduce)').matches;

try {                                            /* стили рядом со скриптом */
  const l = document.createElement('link');
  l.rel = 'stylesheet'; l.href = BASE + 'live.css';
  document.head.appendChild(l);
} catch (e) {}

/* ── сопоставление клубов ── */
const norm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const STOP = new Set(['fc', 'cf', 'afc', 'ac', 'as', 'sc', 'ud', 'sv', 'vfl', 'vfb', 'rc', 'rcd', 'ss', 'us', 'the', 'de', 'la', 'club', 'hockey', 'and', 'bk']);
const toks = s => norm(s).split(/[^a-z0-9]+/).filter(w => w && !STOP.has(w));
let SEARCH = null, searchP = null;
function loadSearch() {
  if (searchP) return searchP;
  searchP = fetch(BASE + '../data/search.json').then(r => r.ok ? r.json() : Promise.reject()).then(D => {
    SEARCH = {}; D.c.forEach(r => { SEARCH[r[1] + ':' + r[0]] = {en: r[4] || '', al: r[5] || ''}; });
  }).catch(() => { SEARCH = {}; });
  return searchP;
}
function siteToks(rec, side) {                   /* английское название + латиница из алиасов + id клуба */
  const id = rec[side], en = rec['en' + side] || '';
  let al = '', e2 = en;
  if (!e2 && SEARCH) { const r = SEARCH[(HOCKEY[rec.lg] ? 'h:' : 'f:') + id] || {}; e2 = r.en || ''; al = r.al || ''; }
  return new Set([...toks(e2), ...toks(al), ...toks(String(id).replace(/^nhl_/, '').replace(/_/g, ' '))]);
}
function espnToks(t) {
  t = t || {};
  return new Set([...toks(t.displayName), ...toks(t.shortDisplayName), ...toks(t.location), ...toks(t.name), ...toks(t.abbreviation)]);
}
const ALIAS = {la: 'lak', sj: 'sjs', tb: 'tbl', nj: 'njd', utah: 'uta'};
const overlap = (a, b) => { let n = 0; a.forEach(w => { if (b.has(w) || b.has(ALIAS[w]) ) n++; }); return n; };

/* ── состояние ── */
let items = [], timer = 0, busy = false;
const parseT = s => { const v = Date.parse(s); return isNaN(v) ? 0 : v; };
function collect() {
  document.querySelectorAll('[data-lv]').forEach(el => {
    if (el.__lv) return;
    const d = el.dataset, start = parseT(d.lvT);
    if (!start || !(d.lvLg in ESPN_LG || d.lvLg === 'khl')) return;
    el.__lv = {el, lg: d.lvLg, start, h: d.lvH, a: d.lvA, enh: d.lvEnH || '', ena: d.lvEnA || '', done: false, live: false, fails: 0, last: ''};
    items.push(el.__lv);
  });
  items = items.filter(x => x.el.isConnected);
}
const active = (x, now) => !x.done && now >= x.start && now <= x.start + (x.live ? WIN_LIVE : WIN);

/* ── запросы ── */
function getJSON(url) {
  const c = new AbortController(), t = setTimeout(() => c.abort(), 10000);
  return fetch(url, {signal: c.signal, cache: 'no-store', credentials: 'omit', referrerPolicy: 'no-referrer'})
    .then(r => r.ok ? r.json() : Promise.reject(r.status)).finally(() => clearTimeout(t));
}
const ymd = (ms, tz) => {
  const p = new Intl.DateTimeFormat('en-CA', {timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date(ms));
  return p.replace(/-/g, '');
};
function espnUrl(x) {                            /* НХЛ: дата по востоку США, футбол: по UTC */
  return ESPN + ESPN_LG[x.lg] + '/scoreboard?dates=' + ymd(x.start, x.lg === 'nhl' ? 'America/New_York' : 'UTC');
}
function khlUrl(list) {
  const from = Math.floor((Math.min(...list.map(x => x.start)) - 36e5) / 1000), to = Math.floor((Math.max(...list.map(x => x.start)) + 4 * 36e5) / 1000);
  return KHL_BASE + 'events_v2.json?order_direction=asc&page=1&q%5Bstart_at_gt_time_from_unixtime%5D=' + from +
    '&q%5Bstart_at_lt_time_from_unixtime%5D=' + to + '&stage_id=' + KHL_STAGE;
}

/* ── разбор ── */
const num = v => { const n = parseInt(v, 10); return isNaN(n) ? null : n; };
const clk = s => String(s || '').replace(/[^0-9+':\s]/g, '').trim();
function hockeyPeriod(p, detail, clock) {
  if (/intermission|end of/i.test(detail || '')) return 'Перерыв';
  if (p === 4) return 'Овертайм' + (clock ? ', ' + clock : '');
  if (p >= 5) return 'Буллиты';
  return p ? p + '-й период' + (clock ? ', ' + clock : '') : '';
}
function footStatus(p, detail, clock) {
  if (/^ht$|half/i.test(detail || '')) return 'Перерыв';
  if (/penalt|shootout/i.test(detail || '')) return 'Пенальти';
  if (p >= 3) return 'Доп. время' + (clock ? ', ' + clock : '');
  return clock ? clock : '';
}
function fromEspn(x, j) {
  const evs = (j && j.events) || [], hs = siteToks(x, 'h'), as = siteToks(x, 'a');
  let best = null, bs = 0;
  for (const ev of evs) {
    const dt = Math.abs(parseT(ev.date) - x.start);
    if (dt > 4 * 36e5) continue;
    const c = (ev.competitions && ev.competitions[0] && ev.competitions[0].competitors) || [];
    const H = c.find(q => q.homeAway === 'home'), A = c.find(q => q.homeAway === 'away');
    if (!H || !A) continue;
    const a = overlap(espnToks(H.team), hs), b = overlap(espnToks(A.team), as);
    if (a && b && a + b > bs) { bs = a + b; best = {ev, H, A}; }
  }
  if (!best) return null;
  const st = best.ev.status || {}, ty = st.type || {}, hh = HOCKEY[x.lg];
  const hg = num(best.H.score), ag = num(best.A.score);
  if (hg === null || ag === null) return null;
  if (ty.state === 'post') return ty.completed === false ? null : {k: 'final', hg, ag, st: ''};
  if (ty.state !== 'in') return null;
  const text = hh ? hockeyPeriod(num(st.period), ty.detail || ty.shortDetail, clk(st.displayClock)) : footStatus(num(st.period), ty.shortDetail || ty.detail, clk(st.displayClock));
  return {k: 'live', hg, ag, st: text};
}
function fromKhl(x, arr) {
  for (const w of (Array.isArray(arr) ? arr : [])) {
    const e = w.event || w;
    if (KHL_TID[e.team_a && e.team_a.id] !== x.h || KHL_TID[e.team_b && e.team_b.id] !== x.a) continue;
    if (Math.abs((+e.start_at || 0) - x.start) > 12 * 36e5) continue;
    const m = /^\s*(\d+)\s*:\s*(\d+)/.exec(String(e.score || ''));
    const key = String(e.game_state_key || '');
    if (key === 'finished') return m ? {k: 'final', hg: +m[1], ag: +m[2], st: ''} : null;
    if (/not|wait|announce|future|schedul|cancel|postpon|prepar/i.test(key)) return null;
    const p = num(e.period);
    const txt = p === 4 ? 'Овертайм' : p >= 5 ? 'Буллиты' : p > 0 ? p + '-й период' : '';
    return {k: 'live', hg: m ? +m[1] : 0, ag: m ? +m[2] : 0, st: txt};
  }
  return null;
}

/* ── вывод (только textContent) ── */
function badge(x) {
  let b = x.el.__lvb;
  if (b && b.isConnected) return b;
  b = document.createElement('div');
  b.className = 'lv'; b.hidden = true;
  const mk = (tag, cls) => { const n = document.createElement(tag); n.className = cls; b.appendChild(n); return n; };
  const tag = mk('span', 'lv-tag');
  const sc = mk('b', 'lv-sc');
  const sh = document.createElement('span'); sh.className = 'lv-h';
  const sep = document.createElement('span'); sep.className = 'lv-sep'; sep.textContent = ':';
  const sa = document.createElement('span'); sa.className = 'lv-a';
  sc.append(sh, sep, sa);
  mk('span', 'lv-st');
  if (x.el.classList.contains('lv-box')) { b.setAttribute('role', 'status'); b.setAttribute('aria-live', 'polite'); }
  x.el.appendChild(b); x.el.__lvb = b;
  return b;
}
function paint(x, r) {
  const b = badge(x);
  if (x.el.classList.contains('lv-box')) document.querySelectorAll('.mt-odds-wrap').forEach(n => { n.hidden = !!r; });   /* в лайве кэфов не показываем */
  if (!r) { b.hidden = true; return; }
  const key = r.k + r.hg + ':' + r.ag;
  const goal = x.last && x.last !== key && r.k === 'live' && x.lastK === 'live';
  b.classList.toggle('lv-final', r.k === 'final');
  b.querySelector('.lv-tag').textContent = r.k === 'final' ? 'Финал' : 'LIVE';
  b.querySelector('.lv-h').textContent = String(r.hg);
  b.querySelector('.lv-a').textContent = String(r.ag);
  b.querySelector('.lv-st').textContent = r.st || '';
  b.hidden = false;
  if (goal) {
    b.classList.remove('lv-goal'); void b.offsetWidth; b.classList.add('lv-goal');
    clearTimeout(x.gt); x.gt = setTimeout(() => b.classList.remove('lv-goal'), reduce() ? 3000 : 2600);
  }
  x.last = key; x.lastK = r.k;
}
function apply(x, r) {
  x.fails = 0;
  if (r) { x.live = r.k === 'live'; if (r.k === 'final') x.done = true; }
  paint(x, r);
}
function fail(list) {
  list.forEach(x => { if (++x.fails >= FAILS) paint(x, null); });
}

/* ── цикл ── */
async function tick() {
  if (busy || document.hidden) return;
  collect();
  const now = Date.now(), act = items.filter(x => active(x, now));
  if (!act.length) return;
  busy = true;
  try {
    const needSearch = act.some(x => x.lg !== 'khl' && !(x.enh && x.ena));
    if (needSearch) await loadSearch();
    const groups = {};
    act.forEach(x => { const k = x.lg === 'khl' ? 'khl' : espnUrl(x); (groups[k] = groups[k] || []).push(x); });
    await Promise.all(Object.keys(groups).map(async k => {
      const list = groups[k];
      try {
        const j = await getJSON(k === 'khl' ? khlUrl(list) : k);
        list.forEach(x => { let r = null; try { r = k === 'khl' ? fromKhl(x, j) : fromEspn(x, j); } catch (e) {} apply(x, r); });
      } catch (e) { fail(list); }
    }));
  } finally { busy = false; }
}
function start() {
  collect();
  tick();
  clearInterval(timer); timer = setInterval(tick, POLL);
}
document.addEventListener('visibilitychange', () => { if (!document.hidden) tick(); });
document.addEventListener('jv:rows', () => { collect(); tick(); });
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
window.JVLive = {tick, _fromEspn: fromEspn, _fromKhl: fromKhl};
})();
