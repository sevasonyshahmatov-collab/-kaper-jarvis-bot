/* ==========================================================================
 * ПРОГНОЗ СЕЗОНА и ИСТОРИЯ СИЛЫ КОМАНД
 * --------------------------------------------------------------------------
 * Прогноз сезона: оставшиеся матчи разыгрываются SEASON_SIMS раз по модели (голы — Пуассон от силы
 * атаки и обороны). Сила каждой команды в каждом прогоне чуть «шевелится» (SEASON_NOISE), потому что
 * мы её знаем не точно — без этого шансы выходят слишком уверенными. Итог: ожидаемые очки и место,
 * шансы на титул, топ-4, еврокубки и вылет.
 * История силы: раз в день снимок рейтинга (скрытый лист «Сила_история») — на листе «Сила команд»
 * видно, кто за неделю вырос, а кто просел.
 * ========================================================================== */

var SHEET_SEASON = 'Прогноз сезона';
var SHEET_PHIST = 'Сила_история';
var SEASON_SIMS = 3000;
var SEASON_NOISE = 0.08;

function rng_(seed) {                                   // mulberry32: одинаковый день — одинаковые цифры
  var a = seed >>> 0;
  return function () { a = (a + 0x6D2B79F5) >>> 0; var t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
function poissonDraw_(l, rnd) { var L = Math.exp(-l), k = 0, p = 1; do { k++; p *= rnd(); } while (p > L && k < 15); return k - 1; }
function gauss_(rnd) { var u = 0, v = 0; while (u === 0) u = rnd(); while (v === 0) v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }

/** Симуляция остатка сезона → {team: {pts, g, exp, pos, p1, top4, top5, top7, rel, lo, hi}} */
function seasonSim_(ss, sims) {
  sims = sims || SEASON_SIMS;
  var fit = modelFitNow_(ss), matches = matchesRead_(ss), base = {}, rest = [];
  matches.forEach(function (m) {
    [m.home, m.away].forEach(function (t) { if (!base[t]) base[t] = { pts: 0, gd: 0, gf: 0, g: 0 }; });
    if (m.status === ST_CANC) return;
    if (m.status === ST_PLAYED && m.hg !== null) {
      var H = base[m.home], A = base[m.away];
      H.g++; A.g++; H.gf += m.hg; A.gf += m.ag; H.gd += m.hg - m.ag; A.gd += m.ag - m.hg;
      if (m.hg > m.ag) H.pts += 3; else if (m.hg < m.ag) A.pts += 3; else { H.pts++; A.pts++; }
    } else rest.push(m);
  });
  var teams = Object.keys(base), n = teams.length, idx = {};
  teams.forEach(function (t, i) { idx[t] = i; });
  var att = teams.map(function (t) { return fit.att[t] !== undefined ? fit.att[t] : -fit.P.promo; });
  var def = teams.map(function (t) { return fit.def[t] !== undefined ? fit.def[t] : -fit.P.promo; });
  var R = rest.map(function (m) { return [idx[m.home], idx[m.away]]; });
  var acc = teams.map(function () { return { pts: 0, pos: 0, p1: 0, top4: 0, top5: 0, top7: 0, rel: 0, all: [] }; });
  var rnd = rng_(Number(dayKey_(new Date()).replace(/-/g, '')));
  var pts = new Array(n), gd = new Array(n), gf = new Array(n), a2 = new Array(n), d2 = new Array(n), order = new Array(n);
  for (var s = 0; s < sims; s++) {
    for (var i = 0; i < n; i++) { var b = base[teams[i]]; pts[i] = b.pts; gd[i] = b.gd; gf[i] = b.gf; a2[i] = att[i] + SEASON_NOISE * gauss_(rnd); d2[i] = def[i] + SEASON_NOISE * gauss_(rnd); order[i] = i; }
    for (var r = 0; r < R.length; r++) {
      var h = R[r][0], a = R[r][1];
      var hg = poissonDraw_(Math.exp(fit.mu + fit.H + a2[h] - d2[a]), rnd), ag = poissonDraw_(Math.exp(fit.mu + a2[a] - d2[h]), rnd);
      gf[h] += hg; gf[a] += ag; gd[h] += hg - ag; gd[a] += ag - hg;
      if (hg > ag) pts[h] += 3; else if (hg < ag) pts[a] += 3; else { pts[h]++; pts[a]++; }
    }
    order.sort(function (x, y) { return pts[y] - pts[x] || gd[y] - gd[x] || gf[y] - gf[x] || (rnd() - 0.5); });
    for (var p = 0; p < n; p++) {
      var t = order[p], A2 = acc[t];
      A2.pts += pts[t]; A2.pos += p + 1; A2.all.push(pts[t]);
      if (p === 0) A2.p1++; if (p < 4) A2.top4++; if (p < 5) A2.top5++; if (p < 7) A2.top7++; if (p >= n - 3) A2.rel++;
    }
  }
  var out = {};
  teams.forEach(function (t, i) {
    var A3 = acc[i]; A3.all.sort(function (x, y) { return x - y; });
    out[t] = { pts: base[t].pts, g: base[t].g, exp: A3.pts / sims, pos: A3.pos / sims, p1: A3.p1 / sims, top4: A3.top4 / sims, top5: A3.top5 / sims, top7: A3.top7 / sims, rel: A3.rel / sims,
      lo: A3.all[Math.floor(sims * 0.1)], hi: A3.all[Math.floor(sims * 0.9)] };
  });
  return { teams: out, rest: rest.length, sims: sims };
}
function renderSeason_(ss) {
  var r = seasonSim_(ss), t = r.teams;
  var rows = Object.keys(t).sort(function (a, b) { return t[b].exp - t[a].exp; }).map(function (k, i) {
    var x = t[k], p = function (v) { return v >= 0.995 ? '>99%' : v > 0 && v < 0.005 ? '<1%' : Math.round(v * 100) + '%'; };
    return [i + 1, k, x.pts, x.g, Math.round(x.exp), x.lo + '–' + x.hi, Math.round(x.pos * 10) / 10, p(x.p1), p(x.top4), p(x.top5), p(x.top7), p(x.rel)];
  });
  var sh = sheet_(ss, SHEET_SEASON);
  sh.clear();
  sh.getRange(1, 1).setValue('ПРОГНОЗ СЕЗОНА АПЛ ' + seasonLabel_(seasonStartYear_()) + ' · ' + r.sims + ' розыгрышей оставшихся ' + r.rest + ' матчей · обновлено ' + mskNow_()).setFontWeight('bold').setFontSize(12);
  sh.getRange(2, 1).setValue('Каждый оставшийся матч разыгрывается по силе команд, сама сила в каждом розыгрыше чуть меняется (мы её знаем не точно). «Очки: 80% случаев» — коридор, куда команда попадает в 8 розыгрышах из 10.').setFontColor('#666666');
  writeTable_(sh, ['Место (ожид.)', 'Команда', 'Очки сейчас', 'Игр', 'Очки в конце (ожид.)', 'Очки: 80% случаев', 'Место в среднем', 'Чемпион', 'Топ-4 (Лига чемпионов)', 'Топ-5', 'Топ-7 (еврокубки)', 'Вылет'],
    rows, { top: 4, clear: false, textCols: [6, 8, 9, 10, 11, 12] });
  try { sh.setColumnWidth(2, 160); } catch (e) {}
  propSetJson_('SEASON_LAST', { t: mskNow_('dd.MM'), top: rows.slice(0, 6).map(function (x) { return [x[1], x[7], x[8]]; }), rel: rows.slice(-6).map(function (x) { return [x[1], x[11]]; }) });
  return rows.length;
}

/* ---------------- история силы ---------------- */
function powerSnapshot_(ss, list) {
  var sh = sheet_(ss, SHEET_PHIST), key = dayKey_(new Date());
  var old = sh.getLastRow() > 1 ? sh.getRange(2, 1, sh.getLastRow() - 1, 4).getValues().filter(function (r) { return String(r[0]) !== key && r[0] !== ''; }) : [];
  var cut = addDaysKey_(key, -120);
  old = old.filter(function (r) { return String(r[0]) >= cut; });
  var rows = old.concat(list.map(function (x, i) { return [key, x.t, r2_(x.power), i + 1]; }));
  writeTable_(sh, ['Дата', 'Команда', 'Сила', 'Место'], rows, { textCols: [1] });
  try { sh.hideSheet(); } catch (e) {}
}
/** Сила и место команд на дату не позже чем days дней назад: {team: {power, pos, day}} */
function powerAgo_(ss, days) {
  var sh = ss.getSheetByName(SHEET_PHIST), out = {};
  if (!sh || sh.getLastRow() < 2) return out;
  var lim = addDaysKey_(dayKey_(new Date()), -days), best = null;
  var v = sh.getRange(2, 1, sh.getLastRow() - 1, 4).getValues();
  v.forEach(function (r) { var d = String(r[0]); if (d <= lim && (!best || d > best)) best = d; });
  if (!best) return out;
  v.forEach(function (r) { if (String(r[0]) === best) out[r[1]] = { power: Number(r[2]), pos: Number(r[3]), day: best }; });
  return out;
}
