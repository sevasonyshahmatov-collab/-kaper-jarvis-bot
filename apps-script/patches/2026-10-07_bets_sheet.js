/* ЛИСТ «ЧТО ЗАХОДИТ» — ОТДЕЛЬНЫЙ ФАЙЛ, один и тот же для таблицы КХЛ и для таблицы НХЛ.
 *
 * Что делает: лист «Что заходит» — по каждой команде доля матчей сезона (с первой игры), в которых зашла бы ставка:
 * исход в основное время, итоговая победа, форы, тоталы, индивидуальные тоталы, удаления. Это сами матчи, а не наши прогнозы.
 * Обновляется сам раз в день после результатов (КХЛ — 07:00, НХЛ — 14:00 по Красноярску).
 *
 * КАК ВСТАВИТЬ (в каждой таблице: Расширения → Apps Script):
 *  1. Слева у «Файлы» нажмите «+» → «Скрипт», назовите «Ставки_команд». Файл должен стоять в списке ниже «Код».
 *  2. Удалите в новом файле всё, что там есть, вставьте этот файл целиком (вместе с этим комментарием), Ctrl+S.
 *  3. Кнопка в меню (по желанию): в «Код.gs» найдите (Ctrl+F) строку
 *        ui.createMenu('КХЛ-парсер')          — в таблице НХЛ: ui.createMenu('НХЛ-парсер')
 *     и сразу под ней вставьте строку:
 *        .addItem('📈 Что заходит у команд', 'betStatsNow_')
 *     Ctrl+S, обновите страницу таблицы.
 *  4. Первый раз лист можно построить сразу: в редакторе вверху выберите функцию betStatsNow_ и нажмите «Выполнить»
 *     (или пункт меню из шага 3). Чтобы он обновлялся сам: «КХЛ-парсер» / «НХЛ-парсер» → Настройки → «Включить всю автоматику»
 *     (или подождите утреннего обновления — оно само доставит недостающий запуск).
 *
 * В НХЛ первый запуск докачает удаления всех сыгранных матчей сезона из протоколов НХЛ (до 2 минут), дальше — только новые.
 */

/* ══════════════ 📈 ЧТО ЗАХОДИТ У КОМАНД — частота ставок за сезон ══════════════
 * Отдельный лист «Что заходит»: по каждой команде — в какой доле матчей сезона (с первой игры) зашла бы ставка
 * каждого популярного вида. Это не наши прогнозы, а сами матчи: исход, итоговая победа, форы, тоталы,
 * индивидуальные тоталы, удаления.
 *  • Всё по основному времени, как считают букмекеры, кроме «Итоговой победы» — она с овертаймом и буллитами.
 *    Матч, ушедший в ОТ или буллиты, в основное время — ничья: 3:2 ОТ → 2:2.
 *  • Цвет ячейки — сравнение с лигой: зелёный — у команды заходит заметно чаще, чем в среднем, красный — реже.
 *  • «Чаще всего заходит» — до трёх ставок, которые у команды заходят чаще, чем у лиги, с учётом числа матчей
 *    (одна ставка из каждой группы; тотал меньше — тоже ставка, а не «не зашёл тотал больше»).
 *  • Удаления: КХЛ — штрафные минуты из приложения КХЛ (лист «КХЛ_матчи_приложение»), число удалений — по числу
 *    большинства у соперника; НХЛ — протоколы матчей НХЛ (скрытый лист «Удаления_НХЛ», каждый матч качается один раз).
 *    Линии удалений подобраны по среднему лиги.
 *  • Обновляется раз в день автоматикой после результатов; вручную — betStatsNow_ (меню или «Выполнить» в редакторе).
 *
 * Один и тот же файл — в таблице КХЛ и в таблице НХЛ: лигу код узнаёт сам (VIDEO_LEAGUE, NHL_TEAMS).
 * ==========================================================================*/
var BETS_SHEET = 'Что заходит';
var BETS_PEN_SHEET = 'Удаления_НХЛ';
var BETS_PEN_HEADER = ['Дата (МСК)', 'ID матча', 'Хозяева', 'Гости', 'Штраф Х, мин', 'Штраф Г, мин', 'Удалений Х', 'Удалений Г'];
var BETS_MIN_GAMES = 5;              // меньше матчей — «Чаще всего заходит» не считаем, ячейки не красим
var BETS_COLOR_MIN = 3;              // от скольких матчей красить ячейки
var BETS_PEN_MAX_MS = 120000;        // докачка удалений НХЛ — не дольше двух минут за запуск

function betsNhl_() { return typeof NHL_TEAMS !== 'undefined' && typeof nhlGet_ === 'function'; }
function betsLeague_() { return typeof VIDEO_LEAGUE === 'string' && VIDEO_LEAGUE ? VIDEO_LEAGUE : (betsNhl_() ? 'НХЛ' : 'КХЛ'); }
function betsDayDiff_(a, b) { return Math.round((Date.parse(b + 'T12:00:00Z') - Date.parse(a + 'T12:00:00Z')) / 864e5); }
function betsDay_(v) { return v instanceof Date ? sheetDayKey_(v) : String(v === null || v === undefined ? '' : v).replace(/^'/, '').trim(); }
function betsNum_(x) { return x === '' || x === null || x === undefined || isNaN(Number(x)) ? null : Number(x); }

/* ---------------- матчи сезона ---------------- */

/** Сыгранные матчи текущего сезона с первой игры: [{day, home, away, hg, ag, ot}]. */
function betsSeasonGames_(ss) {
  var rs = ss.getSheetByName(SHEET_RESULTS), all = [];
  if (!rs || rs.getLastRow() < 2) return [];
  rs.getRange(2, 1, rs.getLastRow() - 1, 7).getValues().forEach(function (r) {
    if (!(r[0] instanceof Date) || String(r[1]).trim() !== 'Сыгран' || typeof r[4] !== 'number' || typeof r[5] !== 'number') return;
    var home = String(r[2]).trim(), away = String(r[3]).trim();
    if (!home || !away) return;
    all.push({ day: sheetDayKey_(r[0]), home: home, away: away, hg: r[4], ag: r[5], ot: r[6] === true || String(r[6]).toUpperCase() === 'TRUE' });
  });
  all.sort(function (a, b) { return a.day < b.day ? -1 : a.day > b.day ? 1 : 0; });
  var from = betsSeasonStart_(ss, all);
  return all.filter(function (g) { return g.day >= from; });
}

/** Первый день сезона: НХЛ — начало окна сезона; КХЛ — первый матч в архиве приложения (там только регулярка этого сезона);
 *  запасной путь — первый матч после самого позднего перерыва больше 45 дней (межсезонье). */
function betsSeasonStart_(ss, all) {
  if (betsNhl_() && typeof NHL_SEASON_FROM === 'string') return NHL_SEASON_FROM;
  try {
    var sh = typeof KHLAPP_GAMES_SHEET === 'string' ? ss.getSheetByName(KHLAPP_GAMES_SHEET) : null, min = '';
    if (sh && sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, 1).getValues().forEach(function (r) {
      var d = betsDay_(r[0]);
      if (/^\d{4}-\d\d-\d\d$/.test(d) && (!min || d < min)) min = d;
    });
    if (min) return min;
  } catch (e) { /* без архива — по перерыву */ }
  var from = all.length ? all[0].day : '0000-00-00';
  for (var i = 1; i < all.length; i++) if (betsDayDiff_(all[i - 1].day, all[i].day) > 45) from = all[i].day;
  return from;
}

/* ---------------- удаления ---------------- */

/** КХЛ: штраф и удаления из архива приложения КХЛ. {день|хозяева|гости: {pimH, pimA, nH, nA}} */
function betsPenKhl_(ss) {
  var sh = typeof KHLAPP_GAMES_SHEET === 'string' ? ss.getSheetByName(KHLAPP_GAMES_SHEET) : null, out = {};
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, 19).getValues().forEach(function (r) {
    var d = betsDay_(r[0]), h = String(r[2]).trim(), a = String(r[3]).trim();
    if (!d || !h || !a) return;
    // удалений у хозяев = попыток большинства у гостей (столбец O), у гостей — у хозяев (M)
    out[d + '|' + h + '|' + a] = { pimH: betsNum_(r[17]), pimA: betsNum_(r[18]), nH: betsNum_(r[14]), nA: betsNum_(r[12]) };
  });
  return out;
}

function betsPenSheet_(ss) {
  var sh = ss.getSheetByName(BETS_PEN_SHEET);
  if (!sh) {
    sh = ss.insertSheet(BETS_PEN_SHEET);
    sh.getRange(1, 1, 1, BETS_PEN_HEADER.length).setValues([BETS_PEN_HEADER]).setFontWeight('bold');
    try { sh.hideSheet(); } catch (e) { /* тесты */ }
  }
  return sh;
}

/** НХЛ: уже скачанные удаления. {день|хозяева|гости: {pimH, pimA, nH, nA}} */
function betsPenNhlRead_(ss) {
  var sh = ss.getSheetByName(BETS_PEN_SHEET), out = {};
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, BETS_PEN_HEADER.length).getValues().forEach(function (r) {
    var d = betsDay_(r[0]); if (!d) return;
    out[d + '|' + String(r[2]).trim() + '|' + String(r[3]).trim()] = { pimH: betsNum_(r[4]), pimA: betsNum_(r[5]), nH: betsNum_(r[6]), nA: betsNum_(r[7]) };
  });
  return out;
}

/** Удаления из «landing» матча НХЛ (summary.penalties по периодам). null — в ответе нет протокола удалений. */
function betsPenFromLanding_(j, hab, aab) {
  var groups = j && j.summary && j.summary.penalties;
  if (!Array.isArray(groups)) return null;
  var abbr = function (x) { return String(x && typeof x === 'object' ? (x.default || x.abbrev || '') : (x || '')).toUpperCase(); };
  hab = abbr(hab || (j.homeTeam && j.homeTeam.abbrev)); aab = abbr(aab || (j.awayTeam && j.awayTeam.abbrev));
  var o = { pimH: 0, pimA: 0, nH: 0, nA: 0 };
  groups.forEach(function (g) {
    (g && g.penalties || []).forEach(function (p) {
      var ab = abbr(p.teamAbbrev), side = ab && ab === hab ? 'H' : ab && ab === aab ? 'A' : null;
      if (!side) return;
      var dur = Number(p.duration) || 0, type = String(p.type || '').toUpperCase();
      o['pim' + side] += dur;
      // удаление — малый, двойной малый, большой и малый скамейке; дисциплинарные (10 минут) не в счёт: игрок не оставляет команду в меньшинстве
      if (type ? /^(MIN|BEN|MAJ)$/.test(type) : (dur === 2 || dur === 4 || dur === 5)) o['n' + side] += 1;
    });
  });
  return o;
}

/** НХЛ: докачать удаления сыгранных матчей сезона, которых ещё нет на скрытом листе. {added, pending} */
function betsPenNhlSync_(ss, games) {
  var t0 = Date.now(), sh = betsPenSheet_(ss), have = betsPenNhlRead_(ss);
  var need = games.filter(function (g) { return !have[g.day + '|' + g.home + '|' + g.away]; });
  if (!need.length) return { added: 0, pending: 0 };
  var want = {}, days = {};
  need.forEach(function (g) { want[g.day + '|' + g.home + '|' + g.away] = true; days[g.day] = true; days[addDaysKey_(g.day, -1)] = true; });
  // id матчей: из счёта за нужные дни (МСК-день = вечер по Нью-Йорку накануне или сам день)
  var ids = {};
  Object.keys(days).sort().reverse().forEach(function (d) {
    if (Date.now() - t0 > BETS_PEN_MAX_MS * 0.4) return;
    nhlGamesOf_(nhlGet_('score/' + d)).forEach(function (g) {
      var x = nhlGameInfo_(g); if (!x) return;
      var k = x.iso + '|' + x.home + '|' + x.away;
      if (want[k]) ids[k] = { id: x.id, hab: g.homeTeam && g.homeTeam.abbrev, aab: g.awayTeam && g.awayTeam.abbrev };
    });
  });
  var queue = need.map(function (g) { var k = g.day + '|' + g.home + '|' + g.away; return ids[k] ? { g: g, q: ids[k] } : null; }).filter(Boolean);
  var rows = [], i = 0;
  while (i < queue.length && Date.now() - t0 < BETS_PEN_MAX_MS) {
    var batch = queue.slice(i, i + 8); i += batch.length;
    var resps = [];
    try { resps = UrlFetchApp.fetchAll(batch.map(function (x) { return { url: NHL_API + 'gamecenter/' + x.q.id + '/landing', muteHttpExceptions: true }; })); } catch (e) { resps = []; }
    batch.forEach(function (x, k) {
      var j = null;
      try { if (resps[k] && resps[k].getResponseCode() === 200) j = JSON.parse(resps[k].getContentText()); } catch (e) { j = null; }
      var p = betsPenFromLanding_(j, x.q.hab, x.q.aab);
      if (p) rows.push(["'" + x.g.day, x.q.id, x.g.home, x.g.away, p.pimH, p.pimA, p.nH, p.nA]);
    });
  }
  if (rows.length) sh.getRange(sh.getLastRow() + 1, 1, rows.length, BETS_PEN_HEADER.length).setValues(rows);
  return { added: rows.length, pending: need.length - rows.length };
}

/* ---------------- что считаем ---------------- */

/** Матч глазами каждой команды: забила / пропустила (итог и основное время), удаления свои и соперника. */
function betsTeamGames_(games, pen) {
  var T = {};
  games.forEach(function (g) {
    var m = Math.min(g.hg, g.ag), rh = g.ot ? m : g.hg, ra = g.ot ? m : g.ag;
    var p = pen[g.day + '|' + g.home + '|' + g.away] || pen[addDaysKey_(g.day, -1) + '|' + g.home + '|' + g.away] || pen[addDaysKey_(g.day, 1) + '|' + g.home + '|' + g.away] || {};
    var add = function (team, gf, ga, rf, rA, pim, pimO, n, nO, home) {
      (T[team] = T[team] || []).push({ gf: gf, ga: ga, rf: rf, ra: rA, pim: pim, pimO: pimO, pen: n, penO: nO, home: home, ot: g.ot });
    };
    add(g.home, g.hg, g.ag, rh, ra, betsNum_(p.pimH), betsNum_(p.pimA), betsNum_(p.nH), betsNum_(p.nA), true);
    add(g.away, g.ag, g.hg, ra, rh, betsNum_(p.pimA), betsNum_(p.pimH), betsNum_(p.nA), betsNum_(p.nH), false);
  });
  return T;
}

/** Столбцы листа. kind 'p' — доля матчей, где ставка зашла (f → true/false/null — нет данных); 'avg' — среднее за игру.
 *  yes / no — как назвать ставку и обратную ей в «Чаще всего заходит»; grp — одна ставка на группу. */
function betsColumns_(lines) {
  var L = lines || {};
  var dec = function (x) { return String(x).replace('.', ','); };
  var cols = [
    { g: 'ИСХОД · осн. время', h: 'Победа', kind: 'p', f: function (x) { return x.rf > x.ra; }, yes: 'Победа в осн. время', grp: 'res' },
    { g: 'ИСХОД · осн. время', h: 'Ничья', kind: 'p', f: function (x) { return x.rf === x.ra; }, yes: 'Ничья в осн. время', grp: 'res' },
    { g: 'ИСХОД · осн. время', h: 'Поражение', kind: 'p', f: function (x) { return x.rf < x.ra; }, yes: 'Победа соперника в осн. время', grp: 'res' },
    { g: 'ИСХОД · осн. время', h: 'Не проиграет', kind: 'p', f: function (x) { return x.rf >= x.ra; }, yes: 'Не проиграет в осн. время', grp: 'res' },
    { g: 'ИТОГОВАЯ ПОБЕДА', h: 'с ОТ и Б', kind: 'p', f: function (x) { return x.gf > x.ga; }, yes: 'Итоговая победа', no: 'Итоговая победа соперника', grp: 'fin' },
    { g: 'ФОРА · осн. время', h: 'Ф(−1,5)', kind: 'p', f: function (x) { return x.rf - x.ra >= 2; }, yes: 'Ф(−1,5)', no: 'Ф(+1,5) соперника', grp: 'hc' },
    { g: 'ФОРА · осн. время', h: 'Ф(+1,5)', kind: 'p', f: function (x) { return x.rf - x.ra >= -1; }, yes: 'Ф(+1,5)', no: 'Ф(−1,5) соперника', grp: 'hc' },
    { g: 'ФОРА · осн. время', h: 'Ф(+2,5)', kind: 'p', f: function (x) { return x.rf - x.ra >= -2; }, yes: 'Ф(+2,5)', no: 'Ф(−2,5) соперника', grp: 'hc' },
    { g: 'ТОТАЛ МАТЧА · осн. время', h: 'ТБ 4,5', kind: 'p', f: function (x) { return x.rf + x.ra > 4.5; }, yes: 'ТБ 4,5', no: 'ТМ 4,5', grp: 'tot' },
    { g: 'ТОТАЛ МАТЧА · осн. время', h: 'ТБ 5,5', kind: 'p', f: function (x) { return x.rf + x.ra > 5.5; }, yes: 'ТБ 5,5', no: 'ТМ 5,5', grp: 'tot' },
    { g: 'ТОТАЛ МАТЧА · осн. время', h: 'ТБ 6,5', kind: 'p', f: function (x) { return x.rf + x.ra > 6.5; }, yes: 'ТБ 6,5', no: 'ТМ 6,5', grp: 'tot' },
    { g: 'ТОТАЛ МАТЧА · осн. время', h: 'Голов за игру', kind: 'avg', v: function (x) { return x.rf + x.ra; } },
    { g: 'ИНД. ТОТАЛ · осн. время', h: 'ИТБ 1,5', kind: 'p', f: function (x) { return x.rf > 1.5; }, yes: 'ИТБ 1,5', no: 'ИТМ 1,5', grp: 'it' },
    { g: 'ИНД. ТОТАЛ · осн. время', h: 'ИТБ 2,5', kind: 'p', f: function (x) { return x.rf > 2.5; }, yes: 'ИТБ 2,5', no: 'ИТМ 2,5', grp: 'it' },
    { g: 'ИНД. ТОТАЛ · осн. время', h: 'ИТБ 3,5', kind: 'p', f: function (x) { return x.rf > 3.5; }, yes: 'ИТБ 3,5', no: 'ИТМ 3,5', grp: 'it' },
    { g: 'ИНД. ТОТАЛ · осн. время', h: 'Соперник ИТБ 2,5', kind: 'p', f: function (x) { return x.ra > 2.5; }, yes: 'ИТБ 2,5 соперника', no: 'ИТМ 2,5 соперника', grp: 'ito' },
    { g: 'ИНД. ТОТАЛ · осн. время', h: 'Забивает за игру', kind: 'avg', v: function (x) { return x.rf; } },
    { g: 'ИНД. ТОТАЛ · осн. время', h: 'Пропускает за игру', kind: 'avg', v: function (x) { return x.ra; } },
    { g: 'УДАЛЕНИЯ', h: 'Удалений за игру', kind: 'avg', v: function (x) { return x.pen; } },
    { g: 'УДАЛЕНИЯ', h: 'Удалений соперника', kind: 'avg', v: function (x) { return x.penO; } }
  ];
  if (L.pen !== undefined) cols.push({ g: 'УДАЛЕНИЯ', h: 'ИТБ удалений ' + dec(L.pen), kind: 'p',
    f: function (x) { return x.pen === null ? null : x.pen > L.pen; }, yes: 'ИТБ удалений ' + dec(L.pen), no: 'ИТМ удалений ' + dec(L.pen), grp: 'pen' });
  if (L.penM !== undefined) cols.push({ g: 'УДАЛЕНИЯ', h: 'ТБ удалений матча ' + dec(L.penM), kind: 'p',
    f: function (x) { return x.pen === null || x.penO === null ? null : x.pen + x.penO > L.penM; }, yes: 'ТБ удалений матча ' + dec(L.penM), no: 'ТМ удалений матча ' + dec(L.penM), grp: 'penm' });
  cols.push({ g: 'УДАЛЕНИЯ', h: 'Штраф, мин за игру', kind: 'avg', v: function (x) { return x.pim; } });
  if (L.pim !== undefined) cols.push({ g: 'УДАЛЕНИЯ', h: 'ТБ штрафа матча ' + dec(L.pim) + ' мин', kind: 'p',
    f: function (x) { return x.pim === null || x.pimO === null ? null : x.pim + x.pimO > L.pim; }, yes: 'ТБ штрафного времени матча ' + dec(L.pim), no: 'ТМ штрафного времени матча ' + dec(L.pim), grp: 'pim' });
  return cols;
}

/** Линии удалений по среднему лиге: число удалений команды и матча — ближайшее «,5» ниже среднего; штраф матча — чётное «,5» ниже. */
function betsPenLines_(T) {
  var n = 0, pen = 0, nm = 0, penM = 0, pm = 0, pim = 0;
  Object.keys(T).forEach(function (t) {
    T[t].forEach(function (x) {
      if (x.pen !== null) { n++; pen += x.pen; }
      if (x.pen !== null && x.penO !== null) { nm++; penM += x.pen + x.penO; }
      if (x.pim !== null && x.pimO !== null) { pm++; pim += x.pim + x.pimO; }
    });
  });
  var out = {};
  if (n) out.pen = Math.floor(pen / n) + 0.5;
  if (nm) out.penM = Math.floor(penM / nm) + 0.5;
  if (pm) out.pim = 2 * Math.floor(pim / pm / 2) + 0.5;
  return out;
}

/** Строка команды: {n, vals[], cnt[]} — по столбцам доля (0…1) или среднее; cnt — по скольким матчам посчитано. */
function betsStats_(list, cols) {
  var vals = [], cnt = [];
  cols.forEach(function (c) {
    var s = 0, k = 0;
    list.forEach(function (x) {
      if (c.kind === 'p') { var r = c.f(x); if (r === null || r === undefined) return; k++; if (r) s++; }
      else { var v = c.v(x); if (v === null || v === undefined || isNaN(v)) return; k++; s += v; }
    });
    vals.push(k ? s / k : null); cnt.push(k);
  });
  return { n: list.length, vals: vals, cnt: cnt };
}

/** «Чаще всего заходит»: ставки, у которых доля у команды выше, чем у лиги, с учётом числа матчей (z ≥ 1,2, не меньше 60%).
 *  Одна ставка на группу, до трёх. */
function betsTop_(st, lg, cols) {
  if (st.n < BETS_MIN_GAMES) return 'мало матчей (' + st.n + ')';
  var cand = [];
  cols.forEach(function (c, i) {
    if (c.kind !== 'p' || st.vals[i] === null || lg.vals[i] === null || st.cnt[i] < BETS_MIN_GAMES) return;
    var p = st.vals[i], p0 = Math.min(0.97, Math.max(0.03, lg.vals[i])), se = Math.sqrt(p0 * (1 - p0) / st.cnt[i]);
    var z = (p - p0) / se;
    if (c.yes) cand.push({ t: c.yes, p: p, p0: lg.vals[i], z: z, grp: c.grp });
    if (c.no) cand.push({ t: c.no, p: 1 - p, p0: 1 - lg.vals[i], z: -z, grp: c.grp });
  });
  var used = {}, out = [];
  cand.filter(function (x) { return x.z >= 1.2 && x.p >= 0.6; }).sort(function (a, b) { return b.z - a.z; }).forEach(function (x) {
    if (out.length >= 3 || used[x.grp]) return;
    used[x.grp] = true;
    out.push(x.t + ' — ' + Math.round(x.p * 100) + '% (лига ' + Math.round(x.p0 * 100) + '%)');
  });
  return out.length ? out.join(' · ') : 'как у лиги — заметно чаще ничего не заходит';
}

/* ---------------- лист ---------------- */

function betStatsBuild_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var nhl = betsNhl_(), league = betsLeague_();
  var games = betsSeasonGames_(ss), sync = null;
  if (nhl) { try { sync = betsPenNhlSync_(ss, games); } catch (e) { sync = { error: e.message }; } }
  var pen = nhl ? betsPenNhlRead_(ss) : betsPenKhl_(ss);
  var T = betsTeamGames_(games, pen), teams = Object.keys(T).sort(function (a, b) { return a.localeCompare(b, 'ru'); });
  var lines = betsPenLines_(T), cols = betsColumns_(lines);
  var all = []; teams.forEach(function (t) { all = all.concat(T[t]); });
  var lg = betsStats_(all, cols);
  var penGames = all.filter(function (x) { return x.pen !== null || x.pim !== null; }).length / 2;

  var sh = resetSheet_(ss, BETS_SHEET);
  try { sh.setTabColor('#34a853'); } catch (e) {}
  var W = 3 + cols.length, from = games.length ? games[0].day : '';
  if (sh.getMaxColumns() < W) sh.insertColumnsAfter(sh.getMaxColumns(), W - sh.getMaxColumns());   // у нового листа всего 26 столбцов
  sh.getRange(1, 1).setValue('ЧТО ЗАХОДИТ У КОМАНД · ' + league + (typeof VIDEO_SEASON === 'string' ? ' · СЕЗОН ' + VIDEO_SEASON : ''))
    .setFontWeight('bold').setFontSize(14).setFontColor('#1a4fd6');
  sh.getRange(2, 1).setValue('Доля матчей сезона, в которых зашла бы ставка: с первой игры' + (from ? ' (' + from.split('-').reverse().join('.') + ')' : '') +
    ', матчей — ' + games.length + '. Это сами матчи, а не наши прогнозы. Всё по основному времени, кроме «Итоговой победы» (с ОТ и буллитами); ' +
    'матч с ОТ или буллитами в основное время — ничья. Тотал меньше = 100% − тотал больше. Обновлено ' + mskNow_() + ' МСК.').setFontColor('#5a6472').setFontSize(9);
  sh.getRange(3, 1).setValue('Цвет — сравнение с лигой (строка «Лига в среднем» внизу): зелёный — у команды заходит заметно чаще (у средних за игру — больше), красный — заметно реже (меньше). ' +
    'Удаления: ' + (nhl ? 'протоколы матчей НХЛ' : 'число — по большинству у соперника, штраф — минуты из приложения КХЛ') +
    (penGames ? ' (есть по ' + Math.round(penGames) + ' из ' + games.length + ' матчей)' : ' — пока нет данных') + '; линии удалений — по среднему лиги.')
    .setFontColor('#5a6472').setFontSize(9);

  // шапка: группы и столбцы
  var head1 = ['', '', ''], head2 = ['Команда', 'Игр', 'Чаще всего заходит'];
  cols.forEach(function (c) { head1.push(c.g); head2.push(c.h); });
  sh.getRange(5, 1, 1, W).setValues([head1]).setFontWeight('bold').setFontSize(9).setFontColor('#1f3a68').setBackground('#dfe7f3').setHorizontalAlignment('center')
    .setVerticalAlignment('middle').setWrap(true);                                     // «ИТОГОВАЯ ПОБЕДА» над одним столбцом — в две строки
  sh.getRange(6, 1, 1, W).setValues([head2]).setFontWeight('bold').setFontSize(9).setBackground('#eef2f7').setHorizontalAlignment('center').setVerticalAlignment('middle').setWrap(true);
  for (var c0 = 3; c0 < W; ) {
    var c1 = c0; while (c1 + 1 < W && head1[c1 + 1] === head1[c0]) c1++;
    if (c1 > c0) sh.getRange(5, c0 + 1, 1, c1 - c0 + 1).merge();
    sh.getRange(5, c0 + 1, 2, c1 - c0 + 1).setBorder(null, true, null, true, null, null, '#9aa7b8', SpreadsheetApp.BorderStyle.SOLID);
    c0 = c1 + 1;
  }

  // команды и строка лиги
  var rows = [], bgs = [], fmts = [], stats = [];
  teams.forEach(function (t) {
    var st = betsStats_(T[t], cols); stats.push(st);
    var row = [t, st.n, betsTop_(st, lg, cols)], bg = ['#ffffff', '#ffffff', '#f7fbf8'], fm = ['@', '0', '@'];
    cols.forEach(function (c, i) {
      var v = st.vals[i], v0 = lg.vals[i];
      row.push(v === null ? '' : v);
      fm.push(c.kind === 'p' ? '0%' : '0.0');
      var col = '#ffffff';
      if (v !== null && v0 !== null && st.cnt[i] >= BETS_COLOR_MIN) {
        var d = c.kind === 'p' ? (v - v0) * 100 : (v0 ? (v - v0) / v0 * 100 : 0);
        col = d >= 20 ? '#a8dab5' : d >= 10 ? '#d4efdc' : d <= -20 ? '#f5b7b1' : d <= -10 ? '#fbe0dd' : '#ffffff';
      }
      bg.push(col);
    });
    rows.push(row); bgs.push(bg); fmts.push(fm);
  });
  var lgRow = ['Лига в среднем', Math.round(games.length * 2 / Math.max(1, teams.length) * 10) / 10, 'для сравнения'];
  cols.forEach(function (c, i) { lgRow.push(lg.vals[i] === null ? '' : lg.vals[i]); });
  rows.push(lgRow);
  bgs.push(lgRow.map(function () { return '#eef2f7'; }));
  fmts.push(['@', '0.0', '@'].concat(cols.map(function (c) { return c.kind === 'p' ? '0%' : '0.0'; })));

  if (rows.length > 1) {
    var rg = sh.getRange(7, 1, rows.length, W);
    rg.setNumberFormats(fmts).setValues(rows).setBackgrounds(bgs).setFontSize(10).setVerticalAlignment('middle');
    sh.getRange(7, 2, rows.length, W - 1).setHorizontalAlignment('center');
    sh.getRange(7, 3, rows.length, 1).setHorizontalAlignment('left').setWrap(true).setFontSize(9).setFontColor('#137333');
    sh.getRange(7, 1, rows.length, 1).setFontWeight('bold');
    sh.getRange(6 + rows.length, 1, 1, W).setFontWeight('bold').setBorder(true, null, null, null, null, null, '#1f3a68', SpreadsheetApp.BorderStyle.SOLID);
    for (var g0 = 3; g0 < W; ) {
      var g1 = g0; while (g1 + 1 < W && head1[g1 + 1] === head1[g0]) g1++;
      sh.getRange(7, g0 + 1, rows.length, g1 - g0 + 1).setBorder(null, true, null, true, null, null, '#9aa7b8', SpreadsheetApp.BorderStyle.SOLID);
      g0 = g1 + 1;
    }
  } else {
    sh.getRange(7, 1).setValue('Сыгранных матчей сезона пока нет.');
  }
  sh.setColumnWidth(1, 150); sh.setColumnWidth(2, 44); sh.setColumnWidth(3, 330);
  for (var k = 4; k <= W; k++) sh.setColumnWidth(k, 74);
  sh.setRowHeight(5, 34); sh.setRowHeight(6, 44);
  sh.setFrozenRows(6);
  try { sh.setFrozenColumns(2); } catch (e) {}
  return { games: games.length, teams: teams.length, penGames: Math.round(penGames), sync: sync, lines: lines };
}

function betStatsStatus_(r) {
  return 'матчей ' + r.games + ', команд ' + r.teams + ', удаления — по ' + r.penGames + ' матчам' +
    (r.sync && r.sync.error ? '; докачка удалений НХЛ: ' + r.sync.error : r.sync && r.sync.pending ? '; ещё не скачано удалений: ' + r.sync.pending : '');
}

/** Кнопка (или «Выполнить» в редакторе): пересчитать и открыть лист. */
function betStatsNow_() {
  var r = betStatsBuild_(SpreadsheetApp.getActive());
  sheetOpen_(BETS_SHEET);
  uiAlert_('Лист «' + BETS_SHEET + '» обновлён: ' + betStatsStatus_(r) + '.\n\nВсё по основному времени, кроме «Итоговой победы». ' +
    'Зелёным — ставки, которые у команды заходят заметно чаще, чем в среднем по лиге; столбец «Чаще всего заходит» — самые заметные из них.');
}

/** Автоматика: раз в день после результатов. */
function betStatsAuto_() {
  try { var r = betStatsBuild_(SpreadsheetApp.getActive()); autoMark_('betStatsAuto_', true, betStatsStatus_(r)); }
  catch (e) { autoMark_('betStatsAuto_', false, e.message); }
}

// раз в день — в список автоматики (без дубля, если он уже есть в «Код.gs»); КХЛ — после «Обновить всё» в 06:00, НХЛ — в 13:00 (по Красноярску)
if (typeof AUTO_JOBS !== 'undefined' && !AUTO_JOBS.some(function (j) { return j.fn === 'betStatsAuto_'; }))
  AUTO_JOBS.push({ fn: 'betStatsAuto_', kind: 'day', hour: betsNhl_() ? 14 : 7,
    what: 'Лист «Что заходит»: какие ставки чаще заходят у команд за сезон (исход, форы, тоталы, инд. тоталы, удаления)' });
