/* ==========================================================================
 * АПЛ-ПАРСЕР · КАПЕР ДЖАРВИС АПЛ (футбол, английская Премьер-лига)
 * --------------------------------------------------------------------------
 * Та же логика, что в таблицах КХЛ и НХЛ: результаты и календарь → модель → прогнозы →
 * линия букмекера (Pinnacle) → «лучший прогноз» (смесь линии и модели) → точность и закрытие линии →
 * посты в Telegram. Отличие — модель под футбол: ничья здесь частый исход, поэтому вместо Elo
 * считаются сила атаки и обороны каждой команды (модель Пуассона с поправкой Диксона — Коулза),
 * а из них — П1 / Х / П2, тоталы и «обе забьют».
 *
 * Первый запуск: меню «⚽ АПЛ» → Настройки → «Ключи и Telegram», затем «Первичная настройка».
 * Ключи хранятся в свойствах скрипта и в репозиторий не попадают.
 *
 * Файлы проекта:
 *   00_core      — общие помощники (даты, окна, свойства, журнал)
 *   10_teams     — клубы: русские названия и варианты написания в источниках
 *   20_data      — календарь и результаты (ESPN), xG (Understat), архив сезонов с линиями (football-data.co.uk)
 *   30_model     — модель силы команд и вероятности исходов
 *   40_odds      — линия Pinnacle, «лучший прогноз», закрытие линии (CLV)
 *   50_sheets    — листы таблицы: прогнозы, сила команд, таблица, точность, модель против рынка
 *   55_backtest  — честная проверка модели на прошлых сезонах против закрывающей линии
 *   60_telegram  — Telegram и Gemini
 *   65_posts     — пост-прогноз на матч, «Матчи дня», «Итоги дня»
 *   70_auto      — автоматика по расписанию
 *   80_menu      — меню и первичная настройка
 * ========================================================================== */

var TZ = 'Europe/Moscow';            // всё время в таблице — московское
var LEAGUE_RU = 'АПЛ';
var QUIET_ = false, QUIET_LOG_ = [];

function props_() { return PropertiesService.getScriptProperties(); }
function prop_(k, def) { var v = props_().getProperty(k); return v === null || v === undefined || v === '' ? (def === undefined ? null : def) : v; }
function propJson_(k, def) { try { var v = props_().getProperty(k); return v ? JSON.parse(v) : def; } catch (e) { return def; } }
function propSetJson_(k, v) { props_().setProperty(k, JSON.stringify(v)); }

function mskNow_(p) { return Utilities.formatDate(new Date(), TZ, p || 'dd.MM.yyyy HH:mm'); }
function fmt_(d, p) { return Utilities.formatDate(d, TZ, p); }
function dayKey_(d) { return Utilities.formatDate(d, TZ, 'yyyy-MM-dd'); }
function addDaysKey_(key, n) {
  var p = key.split('-').map(Number), d = new Date(Date.UTC(p[0], p[1] - 1, p[2] + n));
  return d.toISOString().slice(0, 10);
}
function keyRu_(key) { var p = String(key).split('-'); return p[2] + '.' + p[1]; }

var RU_WD_ = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота'];
var RU_MON_ = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
/** 'yyyy-MM-dd' → «суббота, 3 октября» */
function dayTitle_(key) {
  var p = key.split('-').map(Number), wd = new Date(Date.UTC(p[0], p[1] - 1, p[2])).getUTCDay();
  return RU_WD_[wd] + ', ' + p[2] + ' ' + RU_MON_[p[1] - 1];
}
function ruPlural_(n, a, b, c) {
  n = Math.abs(n) % 100; var n1 = n % 10;
  if (n > 10 && n < 20) return c;
  if (n1 > 1 && n1 < 5) return b;
  if (n1 === 1) return a;
  return c;
}
function pct_(p) { return p === null || p === undefined || isNaN(p) ? '' : Math.round(p * 1000) / 10; }
function r2_(x) { return Math.round(x * 100) / 100; }

function uiAlert_(a, b, c) {
  if (QUIET_) { QUIET_LOG_.push(String(b !== undefined && typeof b === 'string' ? b : a)); return null; }
  try {
    var ui = SpreadsheetApp.getUi();
    if (c !== undefined) return ui.alert(a, b, c);
    if (b !== undefined) return ui.alert(a, b);
    return ui.alert(a);
  } catch (e) { console.log(String(b !== undefined && typeof b === 'string' ? b : a)); return null; }
}
function toast_(msg) { try { SpreadsheetApp.getActive().toast(msg, LEAGUE_RU, 5); } catch (e) {} }

function sheet_(ss, name, create) {
  var sh = ss.getSheetByName(name);
  if (!sh && create !== false) sh = ss.insertSheet(name);
  return sh;
}
function sheetOpen_(name) {
  try { var ss = SpreadsheetApp.getActive(), sh = ss.getSheetByName(name); if (!sh) return; if (sh.isSheetHidden()) sh.showSheet(); ss.setActiveSheet(sh); } catch (e) {}
}
/** Записать таблицу значений с шапкой (лист очищается). */
function writeTable_(sh, head, rows, opt) {
  opt = opt || {};
  var top = opt.top || 1;
  if (opt.clear !== false) sh.clear();
  sh.getRange(top, 1, 1, head.length).setValues([head]).setFontWeight('bold').setBackground(opt.headBg || '#0b3d2e').setFontColor('#ffffff').setWrap(true).setVerticalAlignment('middle');
  if (rows.length) {
    // текстовые колонки размечаем ДО записи: иначе таблица превратит счёт «2:1» во время, а «2026-08-16» — в дату
    (opt.textCols || []).forEach(function (c) { sh.getRange(top + 1, c, rows.length, 1).setNumberFormat('@'); });
    sh.getRange(top + 1, 1, rows.length, head.length).setValues(rows);
  }
  try { sh.setFrozenRows(top); } catch (e) {}
  return rows.length;
}
/** Строки листа как объекты по шапке. */
function readTable_(sh, top) {
  top = top || 1;
  if (!sh || sh.getLastRow() <= top) return [];
  var v = sh.getRange(top, 1, sh.getLastRow() - top + 1, sh.getLastColumn()).getValues(), h = v[0].map(String);
  return v.slice(1).map(function (r) { var o = {}; h.forEach(function (k, i) { o[k] = r[i]; }); return o; });
}

function fetchText_(url, opt) {
  opt = opt || {};
  var r = UrlFetchApp.fetch(url, { muteHttpExceptions: true, followRedirects: true,
    headers: Object.assign({ 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36', 'Accept-Language': 'en-GB,en;q=0.9' }, opt.headers || {}) });
  return { code: r.getResponseCode(), text: r.getContentText(opt.charset || 'UTF-8') };
}
function fetchJson_(url, opt) {
  var r = fetchText_(url, opt);
  if (r.code !== 200) return { code: r.code, data: null, text: r.text.slice(0, 300) };
  try { return { code: 200, data: JSON.parse(r.text) }; } catch (e) { return { code: 200, data: null, text: 'не JSON: ' + r.text.slice(0, 200) }; }
}

/* ---------------- журнал автоматики ---------------- */
var JOURNAL_SHEET = 'Журнал_автоматики';
var JOURNAL_MAX = 400;
function journal_(task, ok, msg) {
  try {
    var ss = SpreadsheetApp.getActive(), sh = sheet_(ss, JOURNAL_SHEET);
    if (sh.getLastRow() === 0) { sh.getRange(1, 1, 1, 4).setValues([['Время (МСК)', 'Задача', 'Итог', 'Подробности']]).setFontWeight('bold'); sh.getRange(2, 1, JOURNAL_MAX + 60, 1).setNumberFormat('@'); }
    sh.appendRow([mskNow_('dd.MM HH:mm'), task, ok ? '✓' : '⚠', String(msg || '').slice(0, 480)]);
    var n = sh.getLastRow();
    if (n > JOURNAL_MAX + 50) sh.deleteRows(2, n - JOURNAL_MAX);
  } catch (e) { console.log('journal: ' + e.message); }
}
function autoMark_(fn, ok, msg) {
  var st = propJson_('AUTO_STATUS', {});
  st[fn] = { t: mskNow_('dd.MM HH:mm'), ok: !!ok, msg: String(msg || '').slice(0, 160) };
  propSetJson_('AUTO_STATUS', st);
  var job = (typeof AUTO_JOBS !== 'undefined' ? AUTO_JOBS : []).filter(function (j) { return j.fn === fn; })[0];
  journal_(job ? job.what : fn, ok, msg);
}
/** Обёртка для запусков по расписанию: тихо, с отметкой в журнале и защитой от ошибок. */
function runAuto_(fn, body) {
  QUIET_ = true; QUIET_LOG_ = [];
  try { var msg = body(); if (msg !== false) autoMark_(fn, true, msg || 'готово'); }
  catch (e) { autoMark_(fn, false, e.message); console.log(fn + ': ' + (e.stack || e.message)); }
  finally { QUIET_ = false; }
}
