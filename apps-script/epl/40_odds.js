/* ==========================================================================
 * ЛИНИЯ БУКМЕКЕРА (Pinnacle), «ЛУЧШИЙ ПРОГНОЗ», ЗАКРЫТИЕ ЛИНИИ
 * --------------------------------------------------------------------------
 * Pinnacle — самая «острая» линия с низкой маржой; открытый интерфейс сайта без ключа (как в КХЛ и НХЛ).
 * Лист «Коэффициенты»: строка на матч. До начала матча строка обновляется, после — замораживается:
 * остаётся последняя линия до матча (закрывающая). Ещё запоминаются первая линия и линия
 * в момент нашей публикации — по ним считается закрытие линии (CLV): если кэф, по которому мы
 * рекомендовали ставку, стабильно выше закрывающего, у прогнозов есть настоящее преимущество.
 * «Лучший прогноз» = доля BLEND_W от линии (без маржи) + остальное от модели. Долю подбирает проверка
 * на прошлых сезонах; по умолчанию 75/25, как в хоккейных таблицах.
 * ========================================================================== */

var MARKET_API = 'https://guest.api.arcadia.pinnacle.com/0.1';
var MARKET_SPORT = 29;               // футбол
var MARKET_LEAGUE_ID = 1980;         // England - Premier League
var MARKET_LEAGUE_RE = /^England\s*-\s*Premier League$/i;
var SHEET_ODDS = 'Коэффициенты';
var BLEND_W_DEFAULT = 0.75;
var ODDS_HEAD = ['ID матча', 'Начало (МСК)', 'Хозяева', 'Гости', 'П1', 'Х', 'П2', 'Тотал', 'Больше', 'Меньше',
  'Фора хозяев', 'Кэф фора Х', 'Кэф фора Г', 'Статус', 'Обновлено (МСК)',
  'П1 первая', 'Х первая', 'П2 первая', 'Первая линия (МСК)',
  'П1 при публикации', 'Х при публикации', 'П2 при публикации', 'Публикация (МСК)', 'ID Pinnacle', 'Начало (UTC)'];
var ODDS_OPEN = 'линия', ODDS_CLOSED = 'закрыта';

function blendW_() { var w = Number(prop_('BLEND_W', BLEND_W_DEFAULT)); return isFinite(w) ? Math.max(0, Math.min(1, w)) : BLEND_W_DEFAULT; }
function americanToDecimal_(a) { a = Number(a); if (!isFinite(a) || a === 0) return null; return Math.round((a > 0 ? 1 + a / 100 : 1 + 100 / Math.abs(a)) * 100) / 100; }
/** Кэфы одного рынка → вероятности без маржи. */
function fairProbs_(decs) {
  if (!decs || !decs.every(function (d) { return d > 1; })) return null;
  var inv = decs.map(function (d) { return 1 / d; }), s = inv.reduce(function (x, y) { return x + y; }, 0);
  return inv.map(function (x) { return x / s; });
}

function marketFetch_(path) {
  return fetchJson_(MARKET_API + path, { headers: { 'Accept': 'application/json' } });
}
function marketLeagueId_(force) {
  var saved = Number(prop_('MARKET_LEAGUE_ID'));
  if (saved && !force) return saved;
  if (!force) return MARKET_LEAGUE_ID;
  var r = marketFetch_('/sports/' + MARKET_SPORT + '/leagues?all=false');
  if (!r.data) return null;
  var f = r.data.filter(function (l) { return MARKET_LEAGUE_RE.test(l.name || ''); })[0];
  if (!f) return null;
  props_().setProperty('MARKET_LEAGUE_ID', String(f.id));
  return f.id;
}
/** Ответы Pinnacle → линии {pid, start, home, away, x12:{h,d,a}, tot:{line,over,under}, ah:{line,h,a}}. */
function parseMarket_(matchups, markets) {
  var prim = {};
  (matchups || []).forEach(function (m) {
    if (!m || m.type !== 'matchup' || m.parentId || !m.participants || m.participants.length !== 2) return;
    if (m.units && m.units !== 'Regular') return;
    if (m.special) return;
    var h = null, a = null;
    m.participants.forEach(function (p) { if (p.alignment === 'home') h = p.name; else if (p.alignment === 'away') a = p.name; });
    if (!h || !a) return;
    prim[m.id] = { pid: String(m.id), start: new Date(m.startTime), home: teamRu_(h), away: teamRu_(a), x12: null, tot: null, ah: null };
  });
  (markets || []).forEach(function (mk) {
    var L = prim[mk.matchupId];
    if (!L || mk.period !== 0 || mk.isAlternate || (mk.status && mk.status !== 'open') || !mk.prices) return;
    var pr = {}; mk.prices.forEach(function (p) { pr[p.designation] = { dec: americanToDecimal_(p.price), pts: p.points }; });
    if (mk.type === 'moneyline' && pr.home && pr.away && pr.draw) L.x12 = { h: pr.home.dec, d: pr.draw.dec, a: pr.away.dec };
    else if (mk.type === 'total' && pr.over && pr.under) L.tot = { line: pr.over.pts, over: pr.over.dec, under: pr.under.dec };
    else if (mk.type === 'spread' && pr.home && pr.away) L.ah = { line: pr.home.pts, h: pr.home.dec, a: pr.away.dec };
  });
  var out = []; for (var k in prim) if (prim[k].x12 || prim[k].tot) out.push(prim[k]);
  return out.sort(function (x, y) { return x.start - y.start; });
}

/** Линии → наши матчи (по командам и дате ±1,5 дня). */
function marketAttach_(lines, matches) {
  var idx = {};
  matches.forEach(function (m) { (idx[m.home + '|' + m.away] = idx[m.home + '|' + m.away] || []).push(m); });
  lines.forEach(function (L) {
    var c = idx[L.home + '|' + L.away] || [];
    var best = null;
    c.forEach(function (m) { var d = Math.abs(m.start - L.start); if (d < 36 * 3600000 && (!best || d < Math.abs(best.start - L.start))) best = m; });
    L.match = best;
  });
  return lines;
}

function oddsRead_(ss) {
  var sh = ss.getSheetByName(SHEET_ODDS), out = {};
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, ODDS_HEAD.length).getValues().forEach(function (r) {
    if (!r[0]) return;
    var o = {}; ODDS_HEAD.forEach(function (k, i) { o[k] = r[i]; });
    out[String(r[0])] = o;
  });
  return out;
}
function oddsWrite_(ss, map) {
  var rows = Object.keys(map).map(function (k) { var o = map[k]; return ODDS_HEAD.map(function (h) { return o[h] === undefined || o[h] === null ? '' : o[h]; }); });
  rows.sort(function (a, b) { return String(a[24]) < String(b[24]) ? -1 : 1; });
  var sh = sheet_(ss, SHEET_ODDS);
  writeTable_(sh, ODDS_HEAD, rows, { textCols: [1, 2, 15, 19, 23, 24, 25] });
  return rows.length;
}

/** Загрузить линию и обновить «Коэффициенты». Матчи, которые уже начались, не трогаются (закрывающая линия). */
function updateOdds_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var lid = marketLeagueId_(false), mu = marketFetch_('/leagues/' + lid + '/matchups');
  if (mu.code === 404) { lid = marketLeagueId_(true); if (lid) mu = marketFetch_('/leagues/' + lid + '/matchups'); }
  if (!mu.data) throw new Error('линия Pinnacle не ответила: код ' + mu.code + (mu.code === 401 || mu.code === 403 ? ' (доступ из Google закрыт)' : ''));
  var mk = marketFetch_('/leagues/' + lid + '/markets/straight');
  if (!mk.data) throw new Error('рынки Pinnacle не ответили: код ' + mk.code);
  var lines = marketAttach_(parseMarket_(mu.data, mk.data), matchesRead_(ss));
  var map = oddsRead_(ss), now = new Date(), stamp = mskNow_('dd.MM HH:mm'), upd = 0, miss = [];
  lines.forEach(function (L) {
    if (!L.match) { miss.push(L.home + ' — ' + L.away); return; }
    var id = L.match.id, o = map[id] || {};
    if (o['Статус'] === ODDS_CLOSED) return;
    if (L.match.start <= now) return;                        // начался — линию не трогаем
    o['ID матча'] = id; o['Начало (МСК)'] = fmt_(L.match.start, 'dd.MM HH:mm'); o['Хозяева'] = L.match.home; o['Гости'] = L.match.away;
    o['Начало (UTC)'] = L.match.start.toISOString(); o['ID Pinnacle'] = L.pid;
    if (L.x12) { o['П1'] = L.x12.h; o['Х'] = L.x12.d; o['П2'] = L.x12.a;
      if (!o['П1 первая']) { o['П1 первая'] = L.x12.h; o['Х первая'] = L.x12.d; o['П2 первая'] = L.x12.a; o['Первая линия (МСК)'] = stamp; } }
    if (L.tot) { o['Тотал'] = L.tot.line; o['Больше'] = L.tot.over; o['Меньше'] = L.tot.under; }
    if (L.ah) { o['Фора хозяев'] = L.ah.line; o['Кэф фора Х'] = L.ah.h; o['Кэф фора Г'] = L.ah.a; }
    o['Статус'] = ODDS_OPEN; o['Обновлено (МСК)'] = stamp;
    map[id] = o; upd++;
  });
  var closed = 0;
  Object.keys(map).forEach(function (id) {
    var o = map[id], st = new Date(String(o['Начало (UTC)']));
    if (o['Статус'] !== ODDS_CLOSED && !isNaN(st.getTime()) && st <= now) { o['Статус'] = ODDS_CLOSED; closed++; }
  });
  oddsWrite_(ss, map);
  return { lines: lines.length, updated: upd, closed: closed, unmatched: miss };
}

/** Отметить линию в момент публикации нашего прогноза (для CLV). */
function oddsMarkPublished_(ss, id) {
  var map = oddsRead_(ss), o = map[id];
  if (!o || o['П1 при публикации']) return;
  o['П1 при публикации'] = o['П1']; o['Х при публикации'] = o['Х']; o['П2 при публикации'] = o['П2']; o['Публикация (МСК)'] = mskNow_('dd.MM HH:mm');
  oddsWrite_(ss, map);
}

/** Вероятности рынка без маржи для строки «Коэффициенты»: {p1, px, p2, over, line} (что есть). */
function oddsFair_(o) {
  if (!o) return null;
  var out = {};
  var x = fairProbs_([Number(o['П1']), Number(o['Х']), Number(o['П2'])]);
  if (x) { out.p1 = x[0]; out.px = x[1]; out.p2 = x[2]; }
  var t = fairProbs_([Number(o['Больше']), Number(o['Меньше'])]);
  if (t && o['Тотал'] !== '') { out.over = t[0]; out.line = Number(o['Тотал']); }
  return Object.keys(out).length ? out : null;
}
