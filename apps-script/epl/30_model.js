/* ==========================================================================
 * МОДЕЛЬ: сила атаки и обороны → вероятности исходов
 * --------------------------------------------------------------------------
 * Почему не Elo, как в хоккее: в футболе каждый четвёртый матч — ничья, а Elo ничью не прогнозирует,
 * и тотал из него не получить. Стандартная модель для футбола (Махер, Диксон — Коулз):
 *   ожидаемые голы хозяев = база × дом × атака хозяев / оборона гостей,
 *   ожидаемые голы гостей = база × атака гостей / оборона хозяев,
 * голы каждой команды — распределение Пуассона, а поправка Диксона — Коулза (rho) чуть добавляет
 * счетам 0:0 и 1:1, которых в жизни больше, чем у чистого Пуассона.
 *
 * Что учитывается:
 *  • свежие матчи весят больше: вес = ½ ^ (давность / период полураспада);
 *  • «по игре», а не только по счёту: цель для атаки — смесь забитых голов и xG (или ударов в створ,
 *    если xG нет). Так команда, которая создаёт много, но не забивает, не проваливается в рейтинге —
 *    это и есть урок «Мани-бола» из хоккейной таблицы: процесс предсказывает будущее лучше счёта;
 *  • новичок лиги (поднялся из Чемпионшипа) стартует слабее середняка, пока не наберёт своих матчей.
 * Все параметры — в MODEL_DEFAULT; подбирает их честная проверка на прошлых сезонах (лист «Проверка модели»),
 * лучший вариант сохраняется в свойстве MODEL_PARAMS.
 * ========================================================================== */

var MODEL_DEFAULT = {
  half: 180,        // период полураспада веса матча, дней
  proc: 0.5,        // доля «игры» (xG / удары в створ) в цели для атаки и обороны
  rho: -0.08,       // поправка Диксона — Коулза на 0:0, 1:0, 0:1, 1:1
  prior: 4,         // сила «приора» в матчах: сколько матчей нужно, чтобы данные перевесили стартовую оценку
  promo: 0.18,      // насколько новичок лиги слабее середняка (в логарифме: 0.18 ≈ на 16–20% меньше забивает и больше пропускает)
  iters: 40,
  maxGoals: 10
};
function modelParams_() { var p = propJson_('MODEL_PARAMS', {}); var out = {}; for (var k in MODEL_DEFAULT) out[k] = p[k] !== undefined ? p[k] : MODEL_DEFAULT[k]; return out; }

/** Коэффициент «удары в створ → ожидаемые голы» по самим данным: сколько голов приходится на удар в створ. */
function sotRate_(games) {
  var g = 0, s = 0;
  games.forEach(function (m) { if (m.hst !== null && m.hst !== undefined && m.ast !== null && m.ast !== undefined) { g += m.hg + m.ag; s += m.hst + m.ast; } });
  return s > 50 ? g / s : 0.31;
}
/** Матчи → вид для модели: время, команды, голы и «игра» (xG, иначе удары в створ × коэффициент). */
function modelGames_(list, rate) {
  rate = rate || sotRate_(list);
  return list.filter(function (m) { return m.hg !== null && m.ag !== null && isFinite(m.hg) && isFinite(m.ag); }).map(function (m) {
    var hp = m.hx !== null && m.hx !== undefined && isFinite(m.hx) ? m.hx : (m.hst !== null && m.hst !== undefined && isFinite(m.hst) ? m.hst * rate : null);
    var ap = m.ax !== null && m.ax !== undefined && isFinite(m.ax) ? m.ax : (m.ast !== null && m.ast !== undefined && isFinite(m.ast) ? m.ast * rate : null);
    return { t: m.t !== undefined ? m.t : new Date(m.date || m.start).getTime(), home: m.home, away: m.away, hg: m.hg, ag: m.ag, hp: hp, ap: ap };
  });
}

/**
 * Подгонка силы команд на матчах до момента asOf (мс). games — из modelGames_.
 * newTeams — {команда: true} для новичков лиги (стартовая оценка ниже середняка).
 * warm — прошлый результат подгонки для быстрого старта (проверка на истории).
 */
function modelFit_(games, asOf, P, newTeams, warm) {
  P = P || modelParams_();
  newTeams = newTeams || {};
  var lam = Math.LN2 / P.half, ts = {}, G = [];
  games.forEach(function (g) {
    if (g.t >= asOf) return;
    var w = Math.exp(-lam * (asOf - g.t) / 86400000);
    if (w < 0.01) return;
    var yh = g.hp === null ? g.hg : (1 - P.proc) * g.hg + P.proc * g.hp;
    var ya = g.ap === null ? g.ag : (1 - P.proc) * g.ag + P.proc * g.ap;
    G.push({ h: g.home, a: g.away, w: w, yh: yh, ya: ya });
    ts[g.home] = true; ts[g.away] = true;
  });
  Object.keys(newTeams).forEach(function (t) { ts[t] = true; });
  var teams = Object.keys(ts);
  var att = {}, def = {}, mu = warm ? warm.mu : Math.log(1.35), H = warm ? warm.H : 0.25;
  teams.forEach(function (t) { att[t] = warm && warm.att[t] !== undefined ? warm.att[t] : 0; def[t] = warm && warm.def[t] !== undefined ? warm.def[t] : 0; });
  var pa = function (t) { return newTeams[t] ? -P.promo : 0; };
  var iters = warm ? Math.min(P.iters, 12) : P.iters;
  for (var it = 0; it < iters; it++) {
    var base = Math.exp(mu + H / 2);
    // атака
    var num = {}, den = {};
    teams.forEach(function (t) { num[t] = P.prior * base * Math.exp(pa(t)); den[t] = P.prior * base; });
    G.forEach(function (g) {
      num[g.h] += g.w * g.yh; den[g.h] += g.w * Math.exp(mu + H - def[g.a]);
      num[g.a] += g.w * g.ya; den[g.a] += g.w * Math.exp(mu - def[g.h]);
    });
    teams.forEach(function (t) { att[t] = Math.log(num[t] / den[t]); });
    // оборона (больше — лучше)
    teams.forEach(function (t) { num[t] = P.prior * base * Math.exp(-pa(t)); den[t] = P.prior * base; });
    G.forEach(function (g) {
      num[g.a] += g.w * g.yh; den[g.a] += g.w * Math.exp(mu + H + att[g.h]);
      num[g.h] += g.w * g.ya; den[g.h] += g.w * Math.exp(mu + att[g.a]);
    });
    teams.forEach(function (t) { def[t] = -Math.log(num[t] / den[t]); });
    // центрирование: средняя команда = 0, уровень голов уходит в базу
    var ma = 0, md = 0; teams.forEach(function (t) { ma += att[t]; md += def[t]; }); ma /= teams.length || 1; md /= teams.length || 1;
    teams.forEach(function (t) { att[t] -= ma; def[t] -= md; });
    // база и преимущество поля
    var sh = 0, eh = 0, sa = 0, ea = 0;
    G.forEach(function (g) { sh += g.w * g.yh; eh += g.w * Math.exp(att[g.h] - def[g.a]); sa += g.w * g.ya; ea += g.w * Math.exp(att[g.a] - def[g.h]); });
    if (eh > 0 && ea > 0 && sh > 0 && sa > 0) {
      var lh = Math.log(sh / eh), la = Math.log(sa / ea);
      mu = la; H = lh - la;
    }
  }
  var n = {}; G.forEach(function (g) { n[g.h] = (n[g.h] || 0) + g.w; n[g.a] = (n[g.a] || 0) + g.w; });
  return { mu: mu, H: H, att: att, def: def, n: n, P: P, asOf: asOf, teams: teams };
}

/** Ожидаемые голы в матче. Неизвестная команда — как новичок лиги. */
function modelLambdas_(fit, home, away, neutral, adj) {
  var P = fit.P, aH = fit.att[home] !== undefined ? fit.att[home] : -P.promo, dH = fit.def[home] !== undefined ? fit.def[home] : -P.promo;
  var aA = fit.att[away] !== undefined ? fit.att[away] : -P.promo, dA = fit.def[away] !== undefined ? fit.def[away] : -P.promo;
  if (adj) { aH += adj.h.a; dH += adj.h.d; aA += adj.a.a; dA += adj.a.d; }          // «Мои поправки»
  return { h: Math.exp(fit.mu + (neutral ? 0 : fit.H) + aH - dA), a: Math.exp(fit.mu + aA - dH) };
}

function poissonVec_(l, n) { var v = [Math.exp(-l)]; for (var k = 1; k <= n; k++) v.push(v[k - 1] * l / k); return v; }

/** Вероятности по ожидаемым голам: исход, тоталы, «обе забьют», самый вероятный счёт. */
function modelProbs_(lh, la, rho, maxG) {
  maxG = maxG || 10; rho = rho === undefined ? MODEL_DEFAULT.rho : rho;
  var ph = poissonVec_(lh, maxG), pa = poissonVec_(la, maxG);
  var p1 = 0, px = 0, p2 = 0, tot = {}, btts = 0, best = null, s = 0;
  for (var i = 0; i <= maxG; i++) for (var j = 0; j <= maxG; j++) {
    var p = ph[i] * pa[j];
    if (i === 0 && j === 0) p *= 1 - lh * la * rho;
    else if (i === 0 && j === 1) p *= 1 + lh * rho;
    else if (i === 1 && j === 0) p *= 1 + la * rho;
    else if (i === 1 && j === 1) p *= 1 - rho;
    if (p < 0) p = 0;
    s += p;
    if (i > j) p1 += p; else if (i === j) px += p; else p2 += p;
    tot[i + j] = (tot[i + j] || 0) + p;
    if (i > 0 && j > 0) btts += p;
    if (!best || p > best.p) best = { p: p, s: i + ':' + j };
  }
  var over = function (line) { var u = 0; for (var k in tot) if (Number(k) < line) u += tot[k]; return 1 - u / s; };
  return { h: lh, a: la, p1: p1 / s, px: px / s, p2: p2 / s, o15: over(1.5), o25: over(2.5), o35: over(3.5), btts: btts / s, score: best.s };
}
/** Вероятность «больше» для любой линии тотала (в т.ч. азиатской 2.75 — как среднее соседних). */
function modelOver_(lh, la, rho, line) {
  if (Math.abs(line * 4 - Math.round(line * 4)) < 1e-9 && Math.abs(line * 2 - Math.round(line * 2)) > 1e-9) {
    return (modelOver_(lh, la, rho, line - 0.25) + modelOver_(lh, la, rho, line + 0.25)) / 2;
  }
  var ph = poissonVec_(lh, 10), pa = poissonVec_(la, 10), u = 0, s = 0, push = 0;
  for (var i = 0; i <= 10; i++) for (var j = 0; j <= 10; j++) {
    var p = ph[i] * pa[j];
    if (i === 0 && j === 0) p *= 1 - lh * la * rho; else if (i === 0 && j === 1) p *= 1 + lh * rho; else if (i === 1 && j === 0) p *= 1 + la * rho; else if (i === 1 && j === 1) p *= 1 - rho;
    s += p; if (i + j < line) u += p; else if (i + j === line) push += p;
  }
  return (1 - (u + push) / s) / (1 - push / s);      // целая линия: возврат при равенстве
}

/** Азиатская фора: вероятность выигрыша ставки на хозяев с форой line (без учёта возвратов: как у линии без маржи).
 *  Четвертные форы (−0,75) — среднее двух половин (−0,5 и −1). */
function modelAh_(lh, la, rho, line) {
  if (Math.abs(line * 2 - Math.round(line * 2)) > 1e-9) return (modelAh_(lh, la, rho, line - 0.25) + modelAh_(lh, la, rho, line + 0.25)) / 2;
  var ph = poissonVec_(lh, 10), pa = poissonVec_(la, 10), w = 0, l = 0;
  for (var i = 0; i <= 10; i++) for (var j = 0; j <= 10; j++) {
    var p = ph[i] * pa[j];
    if (i === 0 && j === 0) p *= 1 - lh * la * rho; else if (i === 0 && j === 1) p *= 1 + lh * rho; else if (i === 1 && j === 0) p *= 1 + la * rho; else if (i === 1 && j === 1) p *= 1 - rho;
    var x = i - j + line;
    if (x > 1e-9) w += p; else if (x < -1e-9) l += p;
  }
  return w + l > 0 ? w / (w + l) : 0.5;
}

function modelPredict_(fit, home, away, adj) {
  var l = modelLambdas_(fit, home, away, false, adj);
  return modelProbs_(l.h, l.a, fit.P.rho, fit.P.maxG);
}

/* ---------------- данные для модели «сейчас» ---------------- */
/** Все матчи для модели: архив прошлых сезонов + текущий сезон с листа «Матчи» (там есть xG). */
function modelAllGames_(ss) {
  var cur = seasonLabel_(seasonStartYear_());
  var arch = archiveRead_(ss).filter(function (m) { return m.season !== cur; });
  var rate = sotRate_(arch.length ? arch : []);
  var games = modelGames_(arch, rate);
  var curList = matchesRead_(ss).filter(function (m) { return m.status === ST_PLAYED && m.hg !== null; })
    .map(function (m) { return { t: m.start.getTime(), home: m.home, away: m.away, hg: m.hg, ag: m.ag, hx: m.hx, ax: m.ax, hst: m.hst, ast: m.ast }; });
  return games.concat(modelGames_(curList, rate));
}
/** Новички лиги в текущем сезоне: есть в календаре, но не играли в АПЛ в прошлом сезоне. */
function modelNewTeams_(ss) {
  var y = seasonStartYear_(), prev = seasonLabel_(y - 1), was = {}, out = {};
  archiveRead_(ss).forEach(function (m) { if (m.season === prev) { was[m.home] = true; was[m.away] = true; } });
  if (!Object.keys(was).length) return out;
  matchesRead_(ss).forEach(function (m) { [m.home, m.away].forEach(function (t) { if (!was[t]) out[t] = true; }); });
  return out;
}
var FIT_CACHE_ = null;
function modelFitNow_(ss) {
  if (FIT_CACHE_) return FIT_CACHE_;
  ss = ss || SpreadsheetApp.getActive();
  FIT_CACHE_ = modelFit_(modelAllGames_(ss), Date.now(), modelParams_(), modelNewTeams_(ss));
  return FIT_CACHE_;
}
