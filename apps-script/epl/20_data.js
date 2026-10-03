/* ==========================================================================
 * ДАННЫЕ: календарь и результаты, xG, архив прошлых сезонов с линиями
 *  • ESPN (site.api.espn.com) — календарь сезона, счёт, статус, удары и удары в створ. Без ключа.
 *  • Understat — ожидаемые голы (xG) по матчам. Без ключа; не ответил — модель обходится ударами в створ.
 *  • football-data.co.uk — прошлые сезоны: счёт, удары, закрывающая линия Pinnacle (1X2 и тотал 2,5).
 *    Нужен для стартовой силы команд и для честной проверки модели против рынка.
 *  Всё это неофициальные открытые источники: поменяются — шаг напишет ошибку в журнал,
 *  а на листах останутся последние загруженные данные.
 * ========================================================================== */

var SHEET_MATCHES = 'Матчи';
var SHEET_ARCHIVE = 'Архив_сезонов';
var MATCH_HEAD = ['ID', 'Дата', 'Время (МСК)', 'Хозяева', 'Гости', 'Статус', 'Г Х', 'Г Г', 'xG Х', 'xG Г',
  'Удары Х', 'Удары Г', 'В створ Х', 'В створ Г', 'Владение Х, %', 'Начало (UTC)', 'Обновлено (МСК)'];
var ST_PLAYED = 'Сыгран', ST_LIVE = 'Идёт', ST_SCHED = 'Запланирован', ST_POST = 'Перенесён', ST_CANC = 'Отменён';
var ESPN_BASE = 'https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1';

/** Год начала текущего сезона: с июля — этот год, раньше — прошлый. */
function seasonStartYear_(d) {
  d = d || new Date();
  var y = Number(fmt_(d, 'yyyy')), m = Number(fmt_(d, 'M'));
  return m >= 7 ? y : y - 1;
}
function seasonLabel_(y) { return y + '-' + String(y + 1).slice(2); }

/* ---------------- ESPN ---------------- */
function espnStat_(c, names) {
  var st = c.statistics || [];
  for (var i = 0; i < st.length; i++) {
    if (names.indexOf(st[i].name) >= 0 || names.indexOf(st[i].abbreviation) >= 0) {
      var v = Number(String(st[i].displayValue !== undefined ? st[i].displayValue : st[i].value).replace('%', ''));
      return isFinite(v) ? v : null;
    }
  }
  return null;
}
function espnStatus_(ev) {
  var t = ((ev.status || {}).type) || {}, name = String(t.name || ''), state = String(t.state || '');
  if (/POSTPON/i.test(name)) return ST_POST;
  if (/CANCEL|ABANDON/i.test(name)) return ST_CANC;
  if (state === 'post' || t.completed) return ST_PLAYED;
  if (state === 'in') return ST_LIVE;
  return ST_SCHED;
}
/** Разбор ответа scoreboard → матчи. */
function espnParse_(data) {
  var out = [];
  ((data && data.events) || []).forEach(function (ev) {
    var comp = (ev.competitions || [])[0]; if (!comp) return;
    var h = null, a = null;
    (comp.competitors || []).forEach(function (c) { if (c.homeAway === 'home') h = c; else if (c.homeAway === 'away') a = c; });
    if (!h || !a) return;
    var start = new Date(ev.date || comp.date), status = espnStatus_(ev);
    var num = function (c) { var v = Number(c.score && c.score.value !== undefined ? c.score.value : c.score); return isFinite(v) ? v : null; };
    out.push({
      id: String(ev.id), start: start, status: status,
      home: teamRu_(h.team && (h.team.displayName || h.team.name)), away: teamRu_(a.team && (a.team.displayName || a.team.name)),
      hg: status === ST_PLAYED || status === ST_LIVE ? num(h) : null, ag: status === ST_PLAYED || status === ST_LIVE ? num(a) : null,
      hs: espnStat_(h, ['totalShots', 'shots', 'SHOTS']), as: espnStat_(a, ['totalShots', 'shots', 'SHOTS']),
      hst: espnStat_(h, ['shotsOnTarget', 'ST', 'SOG']), ast: espnStat_(a, ['shotsOnTarget', 'ST', 'SOG']),
      poss: espnStat_(h, ['possessionPct', 'PP'])
    });
  });
  return out;
}
function ymd_(d) { return Utilities.formatDate(d, 'UTC', 'yyyyMMdd'); }
/** Матчи за период [from, to] (Date). Запросы по месяцу, чтобы ответ не обрезался. */
function espnRange_(from, to) {
  var out = [], seen = {}, cur = new Date(from.getTime());
  while (cur <= to) {
    var end = new Date(Math.min(to.getTime(), cur.getTime() + 30 * 86400000));
    var r = fetchJson_(ESPN_BASE + '/scoreboard?limit=500&dates=' + ymd_(cur) + '-' + ymd_(end));
    if (r.code !== 200 || !r.data) throw new Error('ESPN ответил кодом ' + r.code + (r.text ? ': ' + r.text : ''));
    espnParse_(r.data).forEach(function (m) { if (!seen[m.id]) { seen[m.id] = true; out.push(m); } });
    cur = new Date(end.getTime() + 86400000);
  }
  return out;
}

/* ---------------- лист «Матчи» ---------------- */
function matchesRead_(ss) {
  var sh = ss.getSheetByName(SHEET_MATCHES);
  if (!sh || sh.getLastRow() < 2) return [];
  return sh.getRange(2, 1, sh.getLastRow() - 1, MATCH_HEAD.length).getValues().filter(function (r) { return r[0] !== ''; }).map(function (r) {
    var n = function (x) { return x === '' || x === null ? null : Number(x); };
    return { id: String(r[0]), start: new Date(String(r[15])), status: String(r[5]), home: String(r[3]), away: String(r[4]),
      hg: n(r[6]), ag: n(r[7]), hx: n(r[8]), ax: n(r[9]), hs: n(r[10]), as: n(r[11]), hst: n(r[12]), ast: n(r[13]), poss: n(r[14]) };
  });
}
function matchesWrite_(ss, list) {
  list.sort(function (a, b) { return a.start - b.start || (a.home < b.home ? -1 : 1); });
  var sh = sheet_(ss, SHEET_MATCHES), now = mskNow_('dd.MM HH:mm');
  var e = function (x) { return x === null || x === undefined || (typeof x === 'number' && isNaN(x)) ? '' : x; };
  var rows = list.map(function (m) {
    return [m.id, dayKey_(m.start), fmt_(m.start, 'HH:mm'), m.home, m.away, m.status, e(m.hg), e(m.ag), e(m.hx), e(m.ax),
      e(m.hs), e(m.as), e(m.hst), e(m.ast), e(m.poss), m.start.toISOString(), m.updated || now];
  });
  writeTable_(sh, MATCH_HEAD, rows, { textCols: [1, 2, 3, 16, 17] });
  try { sh.setColumnWidth(4, 150); sh.setColumnWidth(5, 150); } catch (e2) {}
  return rows.length;
}

/** Обновить календарь и результаты сезона с ESPN. xG и уже записанные данные сохраняются. */
function updateMatches_(ss, opt) {
  opt = opt || {};
  ss = ss || SpreadsheetApp.getActive();
  var y = seasonStartYear_(), old = matchesRead_(ss), byId = {};
  old.forEach(function (m) { byId[m.id] = m; });
  var from, to;
  if (opt.full || !old.length) { from = new Date(Date.UTC(y, 6, 20)); to = new Date(Date.UTC(y + 1, 5, 10)); }
  else { from = new Date(Date.now() - (opt.back || 10) * 86400000); to = new Date(Date.now() + (opt.ahead || 45) * 86400000); }
  var fresh = espnRange_(from, to), changed = 0, added = 0;
  fresh.forEach(function (m) {
    var o = byId[m.id];
    if (!o) { byId[m.id] = m; added++; return; }
    ['hx', 'ax'].forEach(function (k) { if (m[k] === undefined || m[k] === null) m[k] = o[k]; });
    ['hs', 'as', 'hst', 'ast', 'poss'].forEach(function (k) { if (m[k] === null && o[k] !== null) m[k] = o[k]; });
    if (o.status !== m.status || o.hg !== m.hg || o.ag !== m.ag || o.start.getTime() !== m.start.getTime()) changed++;
    byId[m.id] = m;
  });
  var list = Object.keys(byId).map(function (k) { return byId[k]; });
  matchesWrite_(ss, list);
  var unk = Object.keys(UNKNOWN_TEAMS_);
  if (unk.length) journal_('Клубы', false, 'не знаю русского названия: ' + unk.join(', ') + ' — пишу по-английски (можно добавить в TEAM_ALIASES)');
  return { total: list.length, added: added, changed: changed, played: list.filter(function (m) { return m.status === ST_PLAYED; }).length };
}

/* ---------------- Understat: xG ---------------- */
function understatDecode_(s) {
  return s.replace(/\\x([0-9a-fA-F]{2})/g, function (_, h) { return String.fromCharCode(parseInt(h, 16)); }).replace(/\\u([0-9a-fA-F]{4})/g, function (_, h) { return String.fromCharCode(parseInt(h, 16)); }).replace(/\\'/g, "'");
}
/** Матчи сезона с xG: [{home, away, date:'yyyy-MM-dd', hx, ax, done}] или исключение. */
function understatSeason_(y) {
  var dates = null;
  var api = fetchJson_('https://understat.com/getLeagueData/EPL/' + y, { headers: { 'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://understat.com/league/EPL/' + y } });
  if (api.data && api.data.dates) dates = api.data.dates;
  if (!dates) {
    var page = fetchText_('https://understat.com/league/EPL/' + y);
    var m = page.code === 200 && page.text.match(/datesData\s*=\s*JSON\.parse\('([^']+)'\)/);
    if (m) { try { dates = JSON.parse(understatDecode_(m[1])); } catch (e) { dates = null; } }
    if (!dates) throw new Error('Understat не отдал данные (коды ' + api.code + ' / ' + page.code + ')');
  }
  return dates.map(function (d) {
    return { home: teamRu_(d.h && d.h.title), away: teamRu_(d.a && d.a.title), date: String(d.datetime || '').slice(0, 10),
      hx: d.xG && d.xG.h !== null && d.xG.h !== undefined ? Number(d.xG.h) : null, ax: d.xG && d.xG.a !== null && d.xG.a !== undefined ? Number(d.xG.a) : null,
      done: d.isResult === true || d.isResult === 'true' };
  });
}
/** Вписать xG в лист «Матчи». Матч ищется по хозяевам, гостям и дате (±1 день: Understat даёт время по Лондону). */
function updateXg_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var list = matchesRead_(ss), y = seasonStartYear_(), xs = understatSeason_(y).filter(function (x) { return x.done && x.hx !== null; });
  var idx = {};
  xs.forEach(function (x) { (idx[x.home + '|' + x.away] = idx[x.home + '|' + x.away] || []).push(x); });
  var n = 0;
  list.forEach(function (m) {
    var c = idx[m.home + '|' + m.away]; if (!c) return;
    var key = dayKey_(m.start);
    var hit = c.filter(function (x) { return Math.abs((new Date(x.date) - new Date(key)) / 86400000) <= 1.5; })[0];
    if (hit && (m.hx !== hit.hx || m.ax !== hit.ax)) { m.hx = hit.hx; m.ax = hit.ax; n++; }
  });
  if (n) matchesWrite_(ss, list);
  return { matched: n, available: xs.length };
}

/* ---------------- football-data.co.uk: архив сезонов ---------------- */
var ARCH_HEAD = ['Сезон', 'Дата', 'Хозяева', 'Гости', 'Г Х', 'Г Г', 'Удары Х', 'Удары Г', 'В створ Х', 'В створ Г',
  'Кэф П1 закр.', 'Кэф Х закр.', 'Кэф П2 закр.', 'Кэф Б2.5 закр.', 'Кэф М2.5 закр.', 'Чья линия'];
var ARCH_SEASONS = 5;                 // сколько прошлых сезонов держать

function csvParse_(text) {
  var rows = [], lines = String(text).replace(/^﻿/, '').split(/\r?\n/);
  lines.forEach(function (ln) {
    if (!ln.trim()) return;
    var out = [], cur = '', q = false;
    for (var i = 0; i < ln.length; i++) {
      var c = ln.charAt(i);
      if (c === '"') { q = !q; continue; }
      if (c === ',' && !q) { out.push(cur); cur = ''; continue; }
      cur += c;
    }
    out.push(cur);
    rows.push(out);
  });
  return rows;
}
function fdDate_(s) {
  var p = String(s).split('/'); if (p.length !== 3) return null;
  var y = Number(p[2]); if (y < 100) y += 2000;
  return y + '-' + ('0' + p[1]).slice(-2) + '-' + ('0' + p[0]).slice(-2);
}
/** Один сезон football-data.co.uk → строки архива. y — год начала сезона. */
function fdSeason_(y) {
  var code = String(y).slice(2) + String(y + 1).slice(2);
  var r = fetchText_('https://www.football-data.co.uk/mmz4281/' + code + '/E0.csv', { charset: 'ISO-8859-1' });
  if (r.code !== 200) throw new Error('football-data.co.uk: сезон ' + seasonLabel_(y) + ' — код ' + r.code);
  var rows = csvParse_(r.text); if (rows.length < 2) return [];
  var h = rows[0], ix = {}; h.forEach(function (k, i) { ix[k.trim()] = i; });
  var g = function (r_, keys) { for (var i = 0; i < keys.length; i++) { var j = ix[keys[i]]; if (j !== undefined && r_[j] !== undefined && r_[j] !== '') { var v = Number(r_[j]); if (isFinite(v) && v > 0) return v; } } return null; };
  var gs = function (r_, k) { var j = ix[k]; return j === undefined ? '' : r_[j]; };
  var out = [];
  rows.slice(1).forEach(function (r_) {
    var d = fdDate_(gs(r_, 'Date'));
    if (!d || !gs(r_, 'HomeTeam')) return;
    var hg = gs(r_, 'FTHG') === '' ? null : Number(gs(r_, 'FTHG')), ag = gs(r_, 'FTAG') === '' ? null : Number(gs(r_, 'FTAG'));
    if (hg === null || ag === null || !isFinite(hg) || !isFinite(ag)) return;
    var src = g(r_, ['PSCH']) ? 'Pinnacle' : g(r_, ['AvgCH']) ? 'средняя' : g(r_, ['B365CH']) ? 'Bet365' : g(r_, ['PSH']) ? 'Pinnacle (не закр.)' : '';
    var ch = src === 'Pinnacle' ? ['PSCH', 'PSCD', 'PSCA'] : src === 'средняя' ? ['AvgCH', 'AvgCD', 'AvgCA'] : src === 'Bet365' ? ['B365CH', 'B365CD', 'B365CA'] : ['PSH', 'PSD', 'PSA'];
    var n0 = function (k) { var v = gs(r_, k); return v === '' ? '' : Number(v); };
    out.push([seasonLabel_(y), d, teamRu_(gs(r_, 'HomeTeam')), teamRu_(gs(r_, 'AwayTeam')), hg, ag, n0('HS'), n0('AS'), n0('HST'), n0('AST'),
      g(r_, [ch[0]]) || '', g(r_, [ch[1]]) || '', g(r_, [ch[2]]) || '',
      g(r_, ['PC>2.5', 'AvgC>2.5', 'B365C>2.5', 'P>2.5']) || '', g(r_, ['PC<2.5', 'AvgC<2.5', 'B365C<2.5', 'P<2.5']) || '', src]);
  });
  return out;
}
/** Загрузить архив: ARCH_SEASONS прошлых сезонов + текущий (для сверки линий). */
function updateArchive_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var y0 = seasonStartYear_(), rows = [], err = [];
  for (var y = y0 - ARCH_SEASONS; y <= y0; y++) {
    try { rows = rows.concat(fdSeason_(y)); } catch (e) { err.push(e.message); }
  }
  if (!rows.length) throw new Error('архив не загрузился: ' + err.join('; '));
  var sh = sheet_(ss, SHEET_ARCHIVE);
  writeTable_(sh, ARCH_HEAD, rows, { textCols: [1, 2] });
  props_().setProperty('ARCHIVE_TS', mskNow_());
  return { rows: rows.length, errors: err };
}
function archiveRead_(ss) {
  var sh = ss.getSheetByName(SHEET_ARCHIVE);
  if (!sh || sh.getLastRow() < 2) return [];
  return sh.getRange(2, 1, sh.getLastRow() - 1, ARCH_HEAD.length).getValues().map(function (r) {
    var n = function (x) { return x === '' || x === null ? null : Number(x); };
    return { season: String(r[0]), date: String(r[1]), home: String(r[2]), away: String(r[3]), hg: n(r[4]), ag: n(r[5]),
      hs: n(r[6]), as: n(r[7]), hst: n(r[8]), ast: n(r[9]), o1: n(r[10]), ox: n(r[11]), o2: n(r[12]), oOver: n(r[13]), oUnder: n(r[14]), src: String(r[15]) };
  }).filter(function (m) { return m.hg !== null && m.ag !== null; });
}
