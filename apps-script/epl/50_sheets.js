/* ==========================================================================
 * ЛИСТЫ: прогнозы, сила команд, таблица, модель против рынка, точность
 * --------------------------------------------------------------------------
 * Честность прогнозов: каждый прогноз хранится в скрытом журнале «Прогнозы_журнал» и обновляется
 * только до начала матча. После стартового свистка он замораживается — по нему и считается точность.
 * Если таблицу подключили посреди сезона, прогнозы на уже сыгранные матчи считаются «задним числом»,
 * но честно: модель строится только по матчам, сыгранным ДО того дня (так и отмечено в журнале).
 * ========================================================================== */

var SHEET_PRED = 'Прогнозы';
var SHEET_PLOG = 'Прогнозы_журнал';
var SHEET_POWER = 'Сила команд';
var SHEET_TABLE = 'Таблица';
var SHEET_VS = 'Модель vs рынок';
var SHEET_ACC = 'Точность';
var PRED_DAYS_AHEAD = 14;
var PLOG_HEAD = ['ID', 'Начало (UTC)', 'Хозяева', 'Гости', 'Ож. голы Х', 'Ож. голы Г', 'П1', 'Х', 'П2', 'Б1.5', 'Б2.5', 'Б3.5', 'Обе забьют', 'Вероятный счёт', 'Обновлено (МСК)', 'Как получен'];
var PICK_EDGE = 0.05;               // ставка, только если наша оценка выше линии хотя бы на 5 п.п.
var PICK_ODDS_MIN = 1.45, PICK_ODDS_MAX = 5.5;

function plogRead_(ss) {
  var sh = ss.getSheetByName(SHEET_PLOG), out = {};
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, PLOG_HEAD.length).getValues().forEach(function (r) {
    if (!r[0]) return;
    out[String(r[0])] = { id: String(r[0]), start: String(r[1]), home: r[2], away: r[3], h: Number(r[4]), a: Number(r[5]), p1: Number(r[6]), px: Number(r[7]), p2: Number(r[8]),
      o15: Number(r[9]), o25: Number(r[10]), o35: Number(r[11]), btts: Number(r[12]), score: String(r[13]), upd: r[14], how: r[15] };
  });
  return out;
}
function plogWrite_(ss, map) {
  var rows = Object.keys(map).map(function (k) { var p = map[k];
    return [p.id, p.start, p.home, p.away, r2_(p.h), r2_(p.a), r2_(p.p1 * 1000) / 1000, r2_(p.px * 1000) / 1000, r2_(p.p2 * 1000) / 1000,
      r2_(p.o15 * 1000) / 1000, r2_(p.o25 * 1000) / 1000, r2_(p.o35 * 1000) / 1000, r2_(p.btts * 1000) / 1000, p.score, p.upd, p.how]; });
  rows.sort(function (a, b) { return a[1] < b[1] ? -1 : 1; });
  var sh = sheet_(ss, SHEET_PLOG);
  writeTable_(sh, PLOG_HEAD, rows, { textCols: [1, 2, 14, 15] });
  try { sh.hideSheet(); } catch (e) {}
}

/** Обновить журнал прогнозов: будущие — по свежей модели, сыгранные без прогноза — честно задним числом. */
function updatePredLog_(ss) {
  var matches = matchesRead_(ss), log = plogRead_(ss), now = new Date(), stamp = mskNow_('dd.MM HH:mm');
  var fit = modelFitNow_(ss), games = null, newT = null, byDay = {}, fresh = 0, retro = 0;
  matches.forEach(function (m) {
    if (m.status === ST_CANC) return;
    var key = m.id, started = m.start <= now || m.status === ST_PLAYED || m.status === ST_LIVE;
    if (!started && m.start - now <= 60 * 86400000) {
      var p = modelPredict_(fit, m.home, m.away);
      log[key] = { id: key, start: m.start.toISOString(), home: m.home, away: m.away, h: p.h, a: p.a, p1: p.p1, px: p.px, p2: p.p2, o15: p.o15, o25: p.o25, o35: p.o35, btts: p.btts, score: p.score, upd: stamp, how: 'до матча' };
      fresh++;
    } else if (started && !log[key] && m.status === ST_PLAYED) {
      if (!games) { games = modelAllGames_(ss); newT = modelNewTeams_(ss); }
      var d = dayKey_(m.start);
      if (!byDay[d]) byDay[d] = modelFit_(games, new Date(d + 'T00:00:00Z').getTime() - 3 * 3600000, modelParams_(), newT);
      var q = modelPredict_(byDay[d], m.home, m.away);
      log[key] = { id: key, start: m.start.toISOString(), home: m.home, away: m.away, h: q.h, a: q.a, p1: q.p1, px: q.px, p2: q.p2, o15: q.o15, o25: q.o25, o35: q.o35, btts: q.btts, score: q.score, upd: stamp, how: 'задним числом (по матчам до этого дня)' };
      retro++;
    }
  });
  plogWrite_(ss, log);
  return { fresh: fresh, retro: retro };
}

/** Ставка по числам: где наша вероятность выше линии без маржи. pred — из журнала, o — строка «Коэффициенты». */
function pickFor_(pred, o) {
  if (!pred || !o) return null;
  var f = oddsFair_(o); if (!f) return null;
  var c = [];
  if (f.p1 !== undefined) {
    [['П1', pred.p1, f.p1, Number(o['П1']), '1'], ['Х', pred.px, f.px, Number(o['Х']), 'X'], ['П2', pred.p2, f.p2, Number(o['П2']), '2']].forEach(function (x) {
      var edge = x[1] - x[2];
      if (edge >= PICK_EDGE && x[3] >= PICK_ODDS_MIN && x[3] <= PICK_ODDS_MAX) c.push({ code: x[4], label: x[0], odds: x[3], edge: edge, model: x[1], market: x[2] });
    });
  }
  if (f.over !== undefined && pred.h) {
    var pm = modelOver_(pred.h, pred.a, modelParams_().rho, f.line);
    [['ТБ ' + f.line, pm, f.over, Number(o['Больше']), 'O' + f.line], ['ТМ ' + f.line, 1 - pm, 1 - f.over, Number(o['Меньше']), 'U' + f.line]].forEach(function (x) {
      var edge = x[1] - x[2];
      if (edge >= PICK_EDGE && x[3] >= PICK_ODDS_MIN && x[3] <= PICK_ODDS_MAX) c.push({ code: x[4], label: x[0], odds: x[3], edge: edge, model: x[1], market: x[2] });
    });
  }
  c.sort(function (a, b) { return b.edge - a.edge; });
  return c.length ? { main: c[0], alt: c[1] || null } : null;
}
/** Итог ставки по счёту: 1 — выигрыш, 0 — проигрыш, 0.5 — возврат (целый тотал), null — нельзя посчитать. */
function pickResult_(code, hg, ag) {
  if (hg === null || ag === null || hg === '' || ag === '') return null;
  hg = Number(hg); ag = Number(ag);
  if (code === '1') return hg > ag ? 1 : 0;
  if (code === 'X') return hg === ag ? 1 : 0;
  if (code === '2') return ag > hg ? 1 : 0;
  var m = String(code).match(/^([OU])([\d.]+)$/); if (!m) return null;
  var line = Number(m[2]), t = hg + ag;
  var one = function (L) { if (t === L) return 0.5; return (m[1] === 'O') === (t > L) ? 1 : 0; };
  if (Math.abs(line * 2 - Math.round(line * 2)) > 1e-9) return (one(line - 0.25) + one(line + 0.25)) / 2;   // азиатская четверть
  return one(line);
}

/* ---------------- лист «Прогнозы» ---------------- */
function renderPredictions_(ss) {
  var matches = matchesRead_(ss), log = plogRead_(ss), odds = oddsRead_(ss), closing = closingOdds_(ss), now = new Date(), W = blendW_();
  var up = [], past = [];
  matches.forEach(function (m) {
    var p = log[m.id]; if (!p) return;
    var o = odds[m.id] || closing[m.id], f = oddsFair_(o) || {}, pick = m.status !== ST_PLAYED ? pickFor_(p, o) : null;
    var best = f.p1 !== undefined ? [W * f.p1 + (1 - W) * p.p1, W * f.px + (1 - W) * p.px, W * f.p2 + (1 - W) * p.p2] : null;
    var res = m.status === ST_PLAYED && m.hg !== null ? m.hg + ':' + m.ag : (m.status === ST_SCHED ? '' : m.status);
    var hit = '';
    if (m.status === ST_PLAYED && m.hg !== null) {
      var probs = [p.p1, p.px, p.p2], mx = probs.indexOf(Math.max.apply(null, probs)), act = m.hg > m.ag ? 0 : m.hg === m.ag ? 1 : 2;
      hit = mx === act ? '✅' : '❌';
    }
    var row = [dayKey_(m.start), fmt_(m.start, 'HH:mm'), m.home, m.away, pct_(p.p1), pct_(p.px), pct_(p.p2), r2_(p.h), r2_(p.a), pct_(p.o25), pct_(p.btts), p.score,
      f.p1 !== undefined ? pct_(f.p1) : '', f.p1 !== undefined ? pct_(f.px) : '', f.p1 !== undefined ? pct_(f.p2) : '',
      best ? pct_(best[0]) : '', best ? pct_(best[1]) : '', best ? pct_(best[2]) : '',
      o ? o['П1'] : '', o ? o['Х'] : '', o ? o['П2'] : '', o ? o['Тотал'] : '', o ? o['Больше'] : '', o ? o['Меньше'] : '',
      pick ? pick.main.label + ' за ' + pick.main.odds : '', res, hit];
    if (m.start > now && m.status !== ST_PLAYED) { if (m.start - now <= PRED_DAYS_AHEAD * 86400000) up.push(row); }
    else past.push(row);
  });
  past.reverse();
  var head = ['Дата', 'Время (МСК)', 'Хозяева', 'Гости', 'П1, %', 'Х, %', 'П2, %', 'Ож. голы Х', 'Ож. голы Г', 'Больше 2,5, %', 'Обе забьют, %', 'Вероятный счёт',
    'Рынок П1, %', 'Рынок Х, %', 'Рынок П2, %', 'Лучший П1, %', 'Лучший Х, %', 'Лучший П2, %', 'Кэф П1', 'Кэф Х', 'Кэф П2', 'Тотал', 'Кэф Б', 'Кэф М',
    'Ставка (перевес к линии)', 'Счёт', 'Исход угадан?'];
  var sh = sheet_(ss, SHEET_PRED);
  sh.clear();
  sh.getRange(1, 1).setValue('ПРОГНОЗЫ АПЛ · ближайшие ' + PRED_DAYS_AHEAD + ' дней и сыгранные · обновлено ' + mskNow_()).setFontWeight('bold').setFontSize(12);
  sh.getRange(2, 1).setValue('«Лучший» = ' + Math.round(W * 100) + '% линия букмекера без маржи + ' + Math.round((1 - W) * 100) + '% модель. Прогноз на сыгранный матч — тот, что был до его начала.').setFontColor('#666666');
  writeTable_(sh, head, up.concat(past), { top: 4, clear: false, textCols: [1, 2, 12, 26] });
  if (up.length) sh.getRange(5, 1, up.length, head.length).setBackground('#eef7f1');
  try { sh.setColumnWidth(3, 140); sh.setColumnWidth(4, 140); sh.setColumnWidth(25, 170); } catch (e) {}
  return { upcoming: up.length, played: past.length };
}

/* ---------------- «Сила команд» и «Таблица» ---------------- */
function seasonStats_(ss) {
  var st = {};
  matchesRead_(ss).forEach(function (m) {
    [m.home, m.away].forEach(function (t) { if (!st[t]) st[t] = { g: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, xf: 0, xa: 0, xn: 0, xpts: 0, form: [] }; });
    if (m.status !== ST_PLAYED || m.hg === null) return;
    var H = st[m.home], A = st[m.away];
    H.g++; A.g++; H.gf += m.hg; H.ga += m.ag; A.gf += m.ag; A.ga += m.hg;
    if (m.hg > m.ag) { H.w++; A.l++; H.form.push('В'); A.form.push('П'); }
    else if (m.hg < m.ag) { A.w++; H.l++; H.form.push('П'); A.form.push('В'); }
    else { H.d++; A.d++; H.form.push('Н'); A.form.push('Н'); }
    if (m.hx !== null && m.ax !== null) {
      H.xf += m.hx; H.xa += m.ax; A.xf += m.ax; A.xa += m.hx; H.xn++; A.xn++;
      var p = modelProbs_(Math.max(0.05, m.hx), Math.max(0.05, m.ax), 0, 10);       // очки «по игре»: шансы по xG этого матча
      H.xpts += 3 * p.p1 + p.px; A.xpts += 3 * p.p2 + p.px;
    }
  });
  return st;
}
function renderPower_(ss) {
  var fit = modelFitNow_(ss), st = seasonStats_(ss), newT = modelNewTeams_(ss);
  var teams = Object.keys(st).filter(function (t) { return fit.att[t] !== undefined || newT[t]; });
  var rows = teams.map(function (t) {
    var a = fit.att[t] !== undefined ? fit.att[t] : -fit.P.promo, d = fit.def[t] !== undefined ? fit.def[t] : -fit.P.promo, s = st[t];
    var gf = Math.exp(fit.mu + fit.H / 2 + a), ga = Math.exp(fit.mu + fit.H / 2 - d);
    return { t: t, power: gf - ga, gf: gf, ga: ga, s: s, n: newT[t] };
  }).sort(function (x, y) { return y.power - x.power; });
  var out = rows.map(function (r, i) {
    var s = r.s;
    return [i + 1, r.t, r2_(r.power), r2_(r.gf), r2_(r.ga), s.g, s.gf + '–' + s.ga, s.xn ? r2_(s.xf) + '–' + r2_(s.xa) : '',
      s.xn ? r2_(s.gf - s.xf) : '', s.xn ? r2_(s.xa - s.ga) : '', s.form.slice(-5).join(' '), r.n ? 'новичок АПЛ' : ''];
  });
  var head = ['Место', 'Команда', 'Сила (разница голов против среднего соперника)', 'Забивает за матч (ожид.)', 'Пропускает за матч (ожид.)', 'Матчей', 'Голы', 'xG за – против',
    'Голы минус xG (реализация)', 'xG против минус пропущенные (вратарь и удача)', 'Форма (последние 5)', 'Примечание'];
  var sh = sheet_(ss, SHEET_POWER);
  sh.clear();
  sh.getRange(1, 1).setValue('СИЛА КОМАНД АПЛ · по модели · обновлено ' + mskNow_()).setFontWeight('bold').setFontSize(12);
  sh.getRange(2, 1).setValue('Сила — сколько голов команда в среднем выиграет у среднего соперника на нейтральном поле. Учитываются и голы, и xG; свежие матчи весят больше. Плюс в «реализации» — забивает больше, чем создаёт (обычно выравнивается).').setFontColor('#666666').setWrap(false);
  writeTable_(sh, head, out, { top: 4, clear: false, textCols: [7, 8, 11] });
  try { sh.setColumnWidth(2, 160); sh.setColumnWidths(3, 8, 120); } catch (e) {}
  return out.length;
}
function renderTable_(ss) {
  var st = seasonStats_(ss);
  var rows = Object.keys(st).filter(function (t) { return st[t].g || true; }).map(function (t) { var s = st[t]; return { t: t, s: s, pts: s.w * 3 + s.d }; })
    .sort(function (x, y) { return y.pts - x.pts || (y.s.gf - y.s.ga) - (x.s.gf - x.s.ga) || y.s.gf - x.s.gf || (x.t < y.t ? -1 : 1); });
  var out = rows.map(function (r, i) { var s = r.s;
    return [i + 1, r.t, s.g, s.w, s.d, s.l, s.gf + '–' + s.ga, s.gf - s.ga, r.pts, s.xn ? r2_(s.xpts) : '', s.xn ? r2_(r.pts - s.xpts) : '', s.form.slice(-5).join(' ')]; });
  var head = ['М', 'Команда', 'И', 'В', 'Н', 'П', 'Мячи', 'Разница', 'Очки', 'Очки по игре (xPts)', 'Очки минус xPts', 'Форма'];
  var sh = sheet_(ss, SHEET_TABLE);
  sh.clear();
  sh.getRange(1, 1).setValue('ТАБЛИЦА АПЛ ' + seasonLabel_(seasonStartYear_()) + ' · обновлено ' + mskNow_()).setFontWeight('bold').setFontSize(12);
  sh.getRange(2, 1).setValue('xPts — сколько очков команда набрала бы, если бы каждый матч решался по созданным моментам (xG). Большой плюс в «очки минус xPts» — везло, минус — недобирает.').setFontColor('#666666');
  writeTable_(sh, head, out, { top: 4, clear: false, textCols: [7, 12] });
  try { sh.setColumnWidth(2, 160); } catch (e) {}
  return out.length;
}

/* ---------------- «Модель vs рынок» и «Точность» ---------------- */
function brier3_(p, act) { var s = 0; for (var i = 0; i < 3; i++) s += Math.pow(p[i] - (i === act ? 1 : 0), 2); return s; }
function ll3_(p, act) { return -Math.log(Math.max(1e-6, p[act])); }

function renderVs_(ss) {
  var matches = matchesRead_(ss), log = plogRead_(ss), odds = oddsRead_(ss), now = new Date(), rows = [];
  matches.forEach(function (m) {
    if (m.start <= now || m.start - now > 8 * 86400000) return;
    var p = log[m.id], o = odds[m.id], f = oddsFair_(o); if (!p || !f || f.p1 === undefined) return;
    var d = [p.p1 - f.p1, p.px - f.px, p.p2 - f.p2], lab = ['П1', 'Х', 'П2'], k = 0;
    for (var i = 1; i < 3; i++) if (Math.abs(d[i]) > Math.abs(d[k])) k = i;
    var verdict = Math.abs(d[k]) < 0.03 ? 'согласны' : (d[k] > 0 ? 'модель выше рынка на ' : 'модель ниже рынка на ') + lab[k] + ' (' + Math.round(Math.abs(d[k]) * 100) + ' п.п.)';
    var pick = pickFor_(p, o);
    rows.push([dayKey_(m.start) + ' ' + fmt_(m.start, 'HH:mm'), m.home + ' — ' + m.away, pct_(p.p1) + ' / ' + pct_(p.px) + ' / ' + pct_(p.p2),
      pct_(f.p1) + ' / ' + pct_(f.px) + ' / ' + pct_(f.p2), verdict, pick ? pick.main.label + ' за ' + pick.main.odds + ' (+' + Math.round(pick.main.edge * 100) + ' п.п.)' : '—']);
  });
  var sh = sheet_(ss, SHEET_VS);
  sh.clear();
  sh.getRange(1, 1).setValue('МОДЕЛЬ ПРОТИВ РЫНКА · ближайшая неделя · обновлено ' + mskNow_()).setFontWeight('bold').setFontSize(12);
  sh.getRange(2, 1).setValue('Проценты рынка — линия Pinnacle без маржи. Ставка появляется, только если модель выше линии на ' + Math.round(PICK_EDGE * 100) + ' п.п. и больше. Кто точнее на дистанции — лист «Точность».').setFontColor('#666666');
  writeTable_(sh, ['Начало (МСК)', 'Матч', 'Модель П1 / Х / П2, %', 'Рынок П1 / Х / П2, %', 'Расхождение', 'Ставка'], rows, { top: 4, clear: false, textCols: [1, 3, 4] });
  try { sh.setColumnWidth(2, 260); sh.setColumnWidths(3, 2, 170); sh.setColumnWidth(5, 280); sh.setColumnWidth(6, 230); } catch (e) {}
  return rows.length;
}

/** Закрывающая линия сыгранного матча: с листа «Коэффициенты», а если матч прошёл до подключения таблицы — из архива
 *  football-data.co.uk (там закрывающие кэфы Pinnacle и текущего сезона). */
function closingOdds_(ss) {
  var odds = oddsRead_(ss), cur = seasonLabel_(seasonStartYear_()), arch = {};
  archiveRead_(ss).forEach(function (a) { if (a.season === cur && a.o1) arch[a.home + '|' + a.away] = a; });
  var out = {};
  matchesRead_(ss).forEach(function (m) {
    var o = odds[m.id];
    if (o && o['Статус'] === ODDS_CLOSED && o['П1']) { out[m.id] = o; return; }
    var a = arch[m.home + '|' + m.away];
    if (a && Math.abs(new Date(a.date) - new Date(dayKey_(m.start))) <= 2 * 86400000)
      out[m.id] = { 'П1': a.o1, 'Х': a.ox, 'П2': a.o2, 'Тотал': a.oOver ? 2.5 : '', 'Больше': a.oOver || '', 'Меньше': a.oUnder || '', 'Статус': ODDS_CLOSED, src: 'архив' };
  });
  return out;
}
function accuracyData_(ss) {
  var matches = matchesRead_(ss), log = plogRead_(ss), odds = closingOdds_(ss), W = blendW_();
  var A = { n: 0, model: { b: 0, l: 0, hit: 0 }, nm: 0, market: { b: 0, l: 0, hit: 0 }, mModel: { b: 0, l: 0 }, blend: { b: 0, l: 0 }, tot: { n: 0, model: 0, market: 0 } };
  matches.forEach(function (m) {
    if (m.status !== ST_PLAYED || m.hg === null) return;
    var p = log[m.id]; if (!p) return;
    var act = m.hg > m.ag ? 0 : m.hg === m.ag ? 1 : 2, pm = [p.p1, p.px, p.p2];
    A.n++; A.model.b += brier3_(pm, act); A.model.l += ll3_(pm, act); if (pm.indexOf(Math.max.apply(null, pm)) === act) A.model.hit++;
    var f = oddsFair_(odds[m.id]);
    if (f && f.p1 !== undefined) {
      var pk = [f.p1, f.px, f.p2], pb = [0, 1, 2].map(function (i) { return W * pk[i] + (1 - W) * pm[i]; });
      A.nm++; A.market.b += brier3_(pk, act); A.market.l += ll3_(pk, act); if (pk.indexOf(Math.max.apply(null, pk)) === act) A.market.hit++;
      A.mModel.b += brier3_(pm, act); A.mModel.l += ll3_(pm, act); A.blend.b += brier3_(pb, act); A.blend.l += ll3_(pb, act);
      if (f.over !== undefined && f.line === 2.5) { var o = m.hg + m.ag > 2.5 ? 1 : 0; A.tot.n++; A.tot.model += Math.pow(p.o25 - o, 2); A.tot.market += Math.pow(f.over - o, 2); }
    }
  });
  return A;
}
function renderAccuracy_(ss) {
  var A = accuracyData_(ss), rows = [];
  var f = function (x, n) { return n ? Math.round(x / n * 10000) / 10000 : ''; };
  rows.push(['Сыгранных матчей с прогнозом', A.n, '', '']);
  rows.push(['Модель: Brier (П1/Х/П2, меньше — лучше)', f(A.model.b, A.n), 'логлосс', f(A.model.l, A.n)]);
  rows.push(['Модель: угадан самый вероятный исход', A.n ? Math.round(A.model.hit / A.n * 1000) / 10 + '%' : '', '', '']);
  rows.push(['', '', '', '']);
  rows.push(['Матчей с закрывающей линией', A.nm, '', '']);
  rows.push(['Модель на этих матчах: Brier', f(A.mModel.b, A.nm), 'логлосс', f(A.mModel.l, A.nm)]);
  rows.push(['Букмекер (Pinnacle, без маржи): Brier', f(A.market.b, A.nm), 'логлосс', f(A.market.l, A.nm)]);
  rows.push(['«Лучший прогноз» (' + Math.round(blendW_() * 100) + '% линия + модель): Brier', f(A.blend.b, A.nm), 'логлосс', f(A.blend.l, A.nm)]);
  rows.push(['Тотал 2,5: Brier модели / букмекера', f(A.tot.model, A.tot.n), 'матчей', A.tot.n]);
  var pk = picksStats_(ss);
  rows.push(['', '', '', '']);
  rows.push(['Наших ставок (посты) рассчитано', pk.n, 'выиграно', pk.won]);
  rows.push(['Итог в единицах ставки (по кэфу публикации)', r2_(pk.units), 'доходность', pk.n ? Math.round(pk.units / pk.n * 1000) / 10 + '%' : '']);
  rows.push(['Закрытие линии (CLV): кэф публикации против закрывающего', pk.clvN ? Math.round(pk.clv / pk.clvN * 1000) / 10 + '%' : '', 'ставок с CLV', pk.clvN]);
  var sh = sheet_(ss, SHEET_ACC);
  sh.clear();
  sh.getRange(1, 1).setValue('ТОЧНОСТЬ · кто точнее: модель или букмекер · обновлено ' + mskNow_()).setFontWeight('bold').setFontSize(12);
  sh.getRange(2, 1).setValue('Считается только по прогнозам, сделанным до начала матча. CLV больше нуля на дистанции — главный признак, что у прогнозов есть преимущество (раньше, чем это покажет плюс по деньгам).').setFontColor('#666666');
  writeTable_(sh, ['Показатель', 'Значение', '', ''], rows, { top: 4, clear: false });
  try { sh.setColumnWidth(1, 460); } catch (e) {}
  return A;
}
