/* ==========================================================================
 * «ПРОГНОЗЫ — КРАТКО» И ОФОРМЛЕНИЕ ТАБЛИЦЫ (как в таблицах КХЛ и НХЛ)
 * --------------------------------------------------------------------------
 * «Прогнозы — кратко» — чистая витрина: сыгранные за неделю и ближайшие матчи, строка на матч —
 * исход по модели и «лучший прогноз» с процентами, кэфы, тотал 2,5 и «обе забьют», ставка (если есть
 * перевес к линии), счёт и отметки, угадали ли. Обновляется вместе с листом «Прогнозы»
 * (каждый час с линией и утром). В паузу на сборные окно расширяется: всегда видно 10 ближайших матчей.
 * Вкладки — группами по цвету, как в хоккейных таблицах; служебные листы скрыты («🧹 Навести порядок»).
 * ========================================================================== */

var SHEET_BRIEF = 'Прогнозы — кратко';
var BRIEF_BACK_DAYS = 7, BRIEF_AHEAD_DAYS = 10, BRIEF_MIN = 10;
var LOOK = {
  title: '#0b3d2e', sub: '#5a6472', head: '#0b3d2e', group: '#e6efe9', line: '#0b3d2e',
  past: ['#ffffff', '#f4f6f8'], next: ['#eef7f1', '#e2f0e7'],
  model: '#1a4fd6', best: '#6b3fa0', pick: '#b45309', ok: '#137333', bad: '#c5221f', muted: '#80868b'
};
var BRIEF_RES_MARK = { 'выигрыш': '✅', 'проигрыш': '❌', 'возврат': '↩ возврат', 'половина выигрыша': '½ ✅', 'половина проигрыша': '½ ❌' };

/** '2026-10-17' → 'Сб, 17.10' */
function briefDay_(key) {
  var p = String(key).split('-').map(Number), wd = new Date(Date.UTC(p[0], p[1] - 1, p[2])).getUTCDay();
  return ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'][wd] + ', ' + keyRu_(key);
}
function briefPct_(p) { return Math.round(p * 100) + '%'; }
function argmax3_(p) { return p[0] >= p[1] && p[0] >= p[2] ? 0 : p[1] >= p[2] ? 1 : 2; }
/** Исход с наибольшим шансом: «Арсенал · 54%» или «Ничья · 31%». */
function briefOutcome_(p, m) { var k = argmax3_(p); return [m.home, 'Ничья', m.away][k] + ' · ' + briefPct_(p[k]); }

/** Опубликованные ставки по матчам (лист «Посты»): {id: {bet, odds, res}} — последняя по времени. */
function briefPosts_(ss) {
  var sh = ss.getSheetByName(SHEET_POSTS), out = {};
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, POST_HEAD.length).getValues().forEach(function (r) {
    if (!r[2] || !r[6]) return;
    out[String(r[2])] = { bet: String(r[6]), odds: Number(r[8]) || null, res: String(r[12] || '') };
  });
  return out;
}

function renderBrief_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var log = plogRead_(ss), odds = oddsRead_(ss), closing = closingOdds_(ss), posts = briefPosts_(ss), W = blendW_(), now = new Date();
  var list = matchesRead_(ss).filter(function (m) { return m.status !== ST_CANC && log[m.id]; }).sort(function (a, b) { return a.start - b.start || (a.home < b.home ? -1 : 1); });
  var isPast = function (m) { return m.status === ST_PLAYED || m.status === ST_LIVE || m.start <= now; };
  var past = list.filter(isPast), next = list.filter(function (m) { return !isPast(m); });
  var today = dayKey_(now), from = addDaysKey_(today, -BRIEF_BACK_DAYS), to = addDaysKey_(today, BRIEF_AHEAD_DAYS);
  var pastSel = past.filter(function (m) { return dayKey_(m.start) >= from; });
  if (pastSel.length < BRIEF_MIN) pastSel = past.slice(-BRIEF_MIN);
  var nextSel = next.filter(function (m) { return dayKey_(m.start) <= to; });
  if (nextSel.length < BRIEF_MIN) nextSel = next.slice(0, BRIEF_MIN);

  var sum = { n: 0, model: 0, nb: 0, best: 0, bets: 0, won: 0, units: 0 };
  var row = function (m, played) {
    var p = log[m.id], pm = [p.p1, p.px, p.p2];
    var o = played ? (closing[m.id] || odds[m.id]) : odds[m.id], f = oddsFair_(o) || {};
    var pb = f.p1 !== undefined ? [W * f.p1 + (1 - W) * p.p1, W * f.px + (1 - W) * p.px, W * f.p2 + (1 - W) * p.p2] : null;
    var done = played && m.status === ST_PLAYED && m.hg !== null, act = done ? (m.hg > m.ag ? 0 : m.hg === m.ag ? 1 : 2) : null;
    var post = posts[m.id], bet = '—', betRes = '';
    if (post) {
      bet = post.bet + (post.odds ? ' · ' + post.odds.toFixed(2) : '');
      betRes = BRIEF_RES_MARK[post.res] || '';
    } else if (!played) {
      var pk = pickFor_(p, o);
      if (pk) bet = pk.main.label + ' · ' + pk.main.odds.toFixed(2) + ' (+' + Math.round(pk.main.edge * 100) + ' п.п.)';
    }
    if (done) {
      sum.n++; if (argmax3_(pm) === act) sum.model++;
      if (pb) { sum.nb++; if (argmax3_(pb) === act) sum.best++; }
      if (post && BRIEF_RES_MARK[post.res] && post.odds) {
        var k = post.odds, u = { 'выигрыш': k - 1, 'проигрыш': -1, 'возврат': 0, 'половина выигрыша': (k - 1) / 2, 'половина проигрыша': -0.5 }[post.res];
        sum.bets++; sum.units += u; if (u > 0) sum.won++;
      }
    }
    var score = done ? m.hg + ':' + m.ag : m.status === ST_LIVE ? 'идёт' : m.status === ST_POST ? 'перенесён' : '';
    return [briefDay_(dayKey_(m.start)), fmt_(m.start, 'HH:mm'), m.home + ' — ' + m.away,
      briefOutcome_(pm, m), pb ? briefOutcome_(pb, m) : '—', (pb || pm).map(function (x) { return Math.round(x * 100); }).join(' / '),
      o && Number(o['П1']) > 1 ? [o['П1'], o['Х'], o['П2']].map(function (x) { return Number(x).toFixed(2); }).join(' / ') : '—',
      briefPct_(p.o25), briefPct_(p.btts), p.score, bet, score,
      done ? (argmax3_(pm) === act ? '✅' : '❌') : '', done && pb ? (argmax3_(pb) === act ? '✅' : '❌') : '', betRes];
  };
  var items = pastSel.map(function (m) { return { m: m, next: false, row: row(m, true) }; })
    .concat(nextSel.map(function (m) { return { m: m, next: true, row: row(m, false) }; }));

  var head = ['День', 'Начало (МСК)', 'Матч', '🤖 Модель', '⭐ Лучший прогноз', 'П1 / Х / П2, %', 'Кэфы П1 / Х / П2', 'Больше 2,5', 'Обе забьют', 'Вероятный счёт',
    '💰 Ставка', 'Счёт', 'Модель', 'Лучший', 'Ставка'];
  var sh = sheet_(ss, SHEET_BRIEF);
  sh.clear();
  ensureSize_(sh, items.length + 6, head.length);
  var note = 'Модель — сила атаки и обороны команд по голам и xG. Лучший прогноз — ' + Math.round(W * 100) + '% линии букмекера без маржи + ' + Math.round((1 - W) * 100) +
    '% модели. Шансы — на исход основного времени. Ставка — только при перевесе над линией от ' + Math.round(PICK_EDGE * 100) + ' п.п. Прогноз на сыгранный матч — тот, что был до начала.';
  var stat = sum.n ? 'Сыгранные на листе: модель угадала исход в ' + sum.model + ' из ' + sum.n + (sum.nb ? ', лучший прогноз — в ' + sum.best + ' из ' + sum.nb : '') +
    (sum.bets ? '. Ставок ' + sum.bets + ', выиграно ' + sum.won + ', итог ' + (sum.units >= 0 ? '+' : '−') + String(Math.abs(Math.round(sum.units * 100) / 100)).replace('.', ',') + ' ед.' : '.') : '';
  lookTitle_(sh, 'ПРОГНОЗЫ АПЛ · JARVIS', note + ' Обновлено ' + mskNow_() + ' МСК.', stat, head.length);
  writeTable_(sh, head, items.map(function (x) { return x.row; }), { top: 4, clear: false, textCols: [1, 2, 6, 7, 10, 12] });
  lookHead_(sh, 4, head.length);
  if (items.length) {
    var n = items.length, bg = [], fc = [], fw = [], band = 0, prev = null;
    items.forEach(function (x, i) {
      var d = dayKey_(x.m.start);
      if (prev !== null && (d !== prev.d || x.next !== prev.next)) band = 1 - band;
      if (prev && x.next !== prev.next) band = 0;
      prev = { d: d, next: x.next };
      var c = (x.next ? LOOK.next : LOOK.past)[band];
      bg.push(head.map(function () { return c; }));
      fc.push(x.row.map(function (v, j) {
        if (j === 3) return LOOK.model; if (j === 4) return LOOK.best; if (j === 10) return v === '—' ? LOOK.muted : LOOK.pick;
        if (j >= 12) return /✅/.test(v) ? LOOK.ok : /❌/.test(v) ? LOOK.bad : LOOK.muted;
        return '#202124';
      }));
      fw.push(x.row.map(function (v, j) { return j === 2 || j === 4 || j === 11 || (j === 10 && v !== '—') ? 'bold' : 'normal'; }));
    });
    var rg = sh.getRange(5, 1, n, head.length);
    rg.setBackgrounds(bg).setFontColors(fc).setFontWeights(fw).setVerticalAlignment('middle');
    sh.getRange(5, 1, n, 2).setHorizontalAlignment('center');
    sh.getRange(5, 4, n, head.length - 3).setHorizontalAlignment('center');
    for (var i = 0; i < n; i++) if (items[i].next) { sh.getRange(5 + i, 1, 1, head.length).setBorder(true, null, null, null, null, null, LOOK.line, SpreadsheetApp.BorderStyle.SOLID_THICK); break; }
  } else {
    sh.getRange(5, 1).setValue('Матчей пока нет — таблица ещё не загрузила календарь.').setFontColor(LOOK.muted);
  }
  [80, 64, 270, 190, 190, 110, 150, 82, 82, 78, 220, 62, 66, 66, 86].forEach(function (w, i) { sh.setColumnWidth(i + 1, w); });
  try { sh.setHiddenGridlines(true); } catch (e) {}
  return { rows: items.length, played: sum.n };
}

/* ---------------- общее оформление листов ---------------- */
/** Строки 1–3: заголовок, пояснение (серым) и итог (жирным) — над шапкой в строке 4. */
function lookTitle_(sh, title, note, stat, cols) {
  sh.getRange(1, 1).setValue(title).setFontWeight('bold').setFontSize(14).setFontColor(LOOK.title);
  if (note) sh.getRange(2, 1).setValue(note).setFontColor(LOOK.sub).setFontSize(9).setWrap(false);
  if (stat) sh.getRange(3, 1).setValue(stat).setFontWeight('bold').setFontSize(10).setFontColor('#202124');
  try { sh.setRowHeight(1, 30); } catch (e) {}
}
/** Шапка таблицы: по центру, перенос слов, повыше. */
function lookHead_(sh, row, cols) {
  sh.getRange(row, 1, 1, cols).setHorizontalAlignment('center').setVerticalAlignment('middle').setWrap(true).setFontSize(9);
  try { sh.setRowHeight(row, 40); } catch (e) {}
}
/** Строка над шапкой с подписями групп колонок: [[подпись, с какой колонки, сколько колонок, цвет]]. */
function lookGroups_(sh, row, groups) {
  var last = groups.reduce(function (m, g) { return Math.max(m, g[1] + g[2] - 1); }, 1);
  try { sh.getRange(row, 1, 1, last).breakApart(); } catch (e) {}
  groups.forEach(function (g) {
    var r = sh.getRange(row, g[1], 1, g[2]);
    try { if (g[2] > 1) r.merge(); } catch (e) {}
    r.setValue(g[0]).setBackground(g[3] || LOOK.group).setFontWeight('bold').setFontSize(9).setHorizontalAlignment('center').setFontColor('#202124');
  });
}
/** Цвет полосы по дням: соседние дни чередуются, чтобы глаз не терялся в длинном списке. */
function lookDayBands_(sh, top, keys, cols, colors) {
  if (!keys.length) return;
  var band = 0, bg = keys.map(function (k, i) { if (i && k !== keys[i - 1]) band = 1 - band; var c = colors[band]; return Array.apply(null, Array(cols)).map(function () { return c; }); });
  sh.getRange(top, 1, keys.length, cols).setBackgrounds(bg);
}

/* ---------------- вкладки: группы и цвета, как в хоккейных таблицах ---------------- */
function sheetGroups_() {
  return [
    { icon: '🟩', name: 'прогнозы и ставки', color: '#34a853', sheets: [SHEET_BRIEF, SHEET_PRED, SHEET_POSTS, SHEET_VS, SHEET_ODDS, SHEET_ACC, SHEET_BT] },
    { icon: '🟦', name: 'лига и команды', color: '#4285f4', sheets: [SHEET_TABLE, SHEET_POWER, SHEET_SEASON, SHEET_CARD, SHEET_INJ, SHEET_MATCHES] },
    { icon: '⬛', name: 'ваши настройки', color: '#5f6368', sheets: [SHEET_TWEAKS, AUTO_SHEET, JOURNAL_SHEET, GUIDE_SHEET] },
    { icon: '⬜', name: 'служебные (скрыты)', color: '#cccccc', hide: true, sheets: [SHEET_ARCHIVE, SHEET_PLOG, SHEET_PHIST] }
  ];
}
/** Порядок вкладок по группам, цвета, служебные — скрыть. Ничего не удаляется. */
function sheetsArrange_(ss) {
  var pos = 1, known = {};
  sheetGroups_().forEach(function (g) {
    g.sheets.forEach(function (n) {
      var sh = n && ss.getSheetByName(n);
      if (!sh || known[n]) return;
      known[n] = true;
      try { sh.setTabColor(g.color); } catch (e) {}
      if (g.hide) { try { if (!sh.isSheetHidden()) sh.hideSheet(); } catch (e) {} return; }
      try { if (sh.isSheetHidden()) sh.showSheet(); ss.setActiveSheet(sh); ss.moveActiveSheet(pos++); } catch (e) {}
    });
  });
  try { ss.setActiveSheet(ss.getSheetByName(SHEET_BRIEF) || ss.getSheetByName(SHEET_PRED)); } catch (e) {}
  return ss.getSheets().map(function (sh) { return sh.getName(); }).filter(function (n) { return !known[n]; });
}
/** Кнопка «🧹 Навести порядок»: справка и недостающие листы, листы-витрины в новом оформлении, вкладки — по группам. Данные не трогает. */
function tidyUpNow_() {
  var ss = SpreadsheetApp.getActive();
  try { setupSheets_(ss); } catch (e) { journal_('Оформление', false, 'справка: ' + e.message); }
  if (!notReady_()) {
    try { renderPredictions_(ss); renderVs_(ss); renderPower_(ss); renderTable_(ss); renderAccuracy_(ss); } catch (e) { journal_('Оформление', false, e.message); }
  }
  var other = sheetsArrange_(ss);
  uiAlert_('Готово. Цвет вкладки — это группа:\n\n' + sheetGroups_().filter(function (g) { return !g.hide; }).map(function (g) {
    return g.icon + ' ' + g.name + ': ' + g.sheets.filter(function (n) { return ss.getSheetByName(n); }).join(', ');
  }).join('\n') + '\n⬜ служебные — скрыты (ПКМ по вкладке → «Показать скрытые листы»).' + (other.length ? '\n\nБез группы: ' + other.join(', ') : ''));
}
