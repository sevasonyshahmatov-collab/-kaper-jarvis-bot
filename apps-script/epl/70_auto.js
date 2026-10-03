/* ==========================================================================
 * АВТОМАТИКА (всё время — московское)
 *  Один пункт меню ставит все запуски; лист «Автоматика» показывает, что и когда запускалось и чем кончилось.
 *  Матчи АПЛ идут днём и вечером по Москве (обычно 14:30–23:00), итоги дня — к полуночи.
 * ========================================================================== */

var AUTO_SHEET = 'Автоматика';
var TRIGGER_TZ = 'Europe/Moscow';
var AUTO_JOBS = [
  { fn: 'dailyUpdateAuto_', kind: 'day', hour: 7, what: 'Утреннее обновление: календарь и результаты, xG, сила команд, прогнозы, таблица, точность' },
  { fn: 'liveAuto_', kind: 'hours', every: 1, what: 'Каждый час: счёт свежих матчей, пересчёт прогнозов; когда день доигран — «Итоги дня» в канал' },
  { fn: 'oddsAuto_', kind: 'hours', every: 1, what: 'Каждый час: линия Pinnacle, «лучший прогноз», модель против рынка' },
  { fn: 'postAuto_', kind: 'minutes', every: 15, what: 'Пост-прогноз на матч за 2,5–4 часа до начала (куда — в настройках)' },
  { fn: 'matchdayAuto_', kind: 'day', hour: 11, what: '«Матчи дня» в канал АПЛ (в дни матчей)' },
  { fn: 'powerPostAuto_', kind: 'week', hour: 12, what: 'По понедельникам: «Сила команд» и шансы на титул и вылет — в канал АПЛ' },
  { fn: 'weeklyAuto_', kind: 'week', hour: 5, what: 'По понедельникам: архив сезонов (закрывающие линии), полная сверка календаря' },
  { fn: 'monthlyAuto_', kind: 'month', hour: 4, what: '1-го числа: проверка модели на прошлых сезонах (итог — вам, применение — кнопкой)' }
];

/** Таблица ещё не настроена — автоматика молчит. */
function notReady_() { return (propJson_('SETUP', {}) || {}).stage !== 'done'; }

/** Пересчитать модель и все листы, которые от неё зависят. */
function refreshModelSheets_(ss, opt) {
  opt = opt || {};
  FIT_CACHE_ = null;
  var r = updatePredLog_(ss);
  renderPower_(ss); renderTable_(ss); renderPredictions_(ss); renderVs_(ss);
  if (opt.season) { try { renderSeason_(ss); } catch (e) { journal_('Прогноз сезона', false, e.message); } }
  try { cardRender_(ss); } catch (e) { journal_('Карточка команды', false, e.message); }
  try { settlePosts_(ss); } catch (e) { journal_('Посты', false, 'итог ставок: ' + e.message); }
  renderAccuracy_(ss);
  return r;
}

function dailyUpdateAuto_() {
  if (notReady_()) return;
  runAuto_('dailyUpdateAuto_', function () {
    var ss = SpreadsheetApp.getActive(), msg = [];
    var m = updateMatches_(ss, { back: 10, ahead: 60 }); msg.push('матчей ' + m.total + ' (сыграно ' + m.played + ', изменилось ' + m.changed + ', новых ' + m.added + ')');
    try { var x = updateXg_(ss); msg.push('xG: ' + x.matched); } catch (e) { msg.push('xG: ' + e.message); }
    try { updateOdds_(ss); } catch (e) { msg.push('линия: ' + e.message); }
    var r = refreshModelSheets_(ss, { season: true }); msg.push('прогнозов ' + r.fresh + (r.retro ? ', задним числом ' + r.retro : ''));
    return msg.join('; ');
  });
}
function liveAuto_() {
  if (notReady_()) return;
  runAuto_('liveAuto_', function () {
    var ss = SpreadsheetApp.getActive(), now = new Date();
    var near = matchesRead_(ss).filter(function (m) { return Math.abs(m.start - now) < 30 * 3600000; });
    if (!near.length) return false;                                  // в дни без матчей — тихо
    var m = updateMatches_(ss, { back: 2, ahead: 3 });
    if (m.changed) { try { updateXg_(ss); } catch (e) {} refreshModelSheets_(ss); }
    var days = resultsDayAuto_(ss) || [];
    return 'изменилось матчей: ' + m.changed + (days.length ? '; «Итоги дня» опубликованы: ' + days.map(keyRu_).join(', ') : '');
  });
}
function oddsAuto_() {
  if (notReady_()) return;
  runAuto_('oddsAuto_', function () {
    var ss = SpreadsheetApp.getActive(), r = updateOdds_(ss);
    renderPredictions_(ss); renderVs_(ss);
    return 'линий ' + r.lines + ', обновлено ' + r.updated + (r.closed ? ', закрыто ' + r.closed : '') + (r.unmatched.length ? '; без пары в календаре: ' + r.unmatched.slice(0, 3).join(', ') : '');
  });
}
function weeklyAuto_() {
  if (notReady_()) return;
  runAuto_('weeklyAuto_', function () {
    var ss = SpreadsheetApp.getActive(), msg = [];
    try { var a = updateArchive_(ss); msg.push('архив: ' + a.rows + ' матчей'); } catch (e) { msg.push('архив: ' + e.message); }
    var m = updateMatches_(ss, { full: true }); msg.push('календарь: ' + m.total);
    try { updateXg_(ss); } catch (e) {}
    refreshModelSheets_(ss, { season: true });
    return msg.join('; ');
  });
}
function monthlyAuto_() {
  if (notReady_()) return;
  props_().deleteProperty('BT_STATE');
  runAuto_('monthlyAuto_', function () {
    var r = backtestRun_(true, false);
    if (r.done && r.best) notifyAdmin_('⚽ АПЛ: ежемесячная проверка модели.\n' + btSummary_(r.best) + '\nПрименить: меню «⚽ АПЛ» → Модель → «Применить лучший вариант проверки».');
    return r.done ? 'проверка модели готова' : 'проверка модели идёт, продолжу сам';
  });
}

/* ---------------- триггеры ---------------- */
function autoCreate_(j) {
  var b = ScriptApp.newTrigger(j.fn).timeBased();
  if (j.kind === 'day') b.everyDays(1).atHour(j.hour).inTimezone(TRIGGER_TZ).create();
  else if (j.kind === 'hours') b.everyHours(j.every).create();
  else if (j.kind === 'minutes') b.everyMinutes(j.every).create();
  else if (j.kind === 'week') b.onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(j.hour).inTimezone(TRIGGER_TZ).create();
  else if (j.kind === 'month') b.onMonthDay(1).atHour(j.hour).inTimezone(TRIGGER_TZ).create();
}
function ensureAutomation_(reset) {
  var have = {}, mine = {};
  AUTO_JOBS.forEach(function (j) { mine[j.fn] = true; });
  ScriptApp.getProjectTriggers().forEach(function (t) {
    var h = t.getHandlerFunction();
    if ((reset && mine[h]) || have[h]) { ScriptApp.deleteTrigger(t); return; }
    have[h] = true;
  });
  var added = 0;
  AUTO_JOBS.forEach(function (j) { if (!have[j.fn] || reset) { autoCreate_(j); added++; } });
  return { added: added, total: AUTO_JOBS.length };
}
function autoSchedText_(j) {
  if (j.kind === 'day') return 'каждый день в ' + j.hour + ':00 МСК';
  if (j.kind === 'hours') return 'каждые ' + j.every + ' ч';
  if (j.kind === 'minutes') return 'каждые ' + j.every + ' мин';
  if (j.kind === 'week') return 'по понедельникам в ' + j.hour + ':00 МСК';
  return '1-го числа в ' + j.hour + ':00 МСК';
}
function autoRender_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var st = propJson_('AUTO_STATUS', {}), have = {};
  try { ScriptApp.getProjectTriggers().forEach(function (t) { have[t.getHandlerFunction()] = true; }); } catch (e) { have = null; }
  var rows = AUTO_JOBS.map(function (j) {
    var s = st[j.fn];
    return [j.what, autoSchedText_(j), have === null ? '?' : have[j.fn] ? '✅ включено' : '❌ нет', s ? s.t : '—', s ? (s.ok ? '✓ ' : '⚠ ') + s.msg : ''];
  });
  var sh = sheet_(ss, AUTO_SHEET);
  sh.clear();
  sh.getRange(1, 1).setValue('Автоматика: что таблица делает сама').setFontWeight('bold').setFontSize(12);
  sh.getRange(2, 1).setValue('Если в «Статус» стоит ❌ — меню «⚽ АПЛ» → Настройки → «Включить автоматику». Подробный журнал — лист «' + JOURNAL_SHEET + '».').setFontColor('#666666');
  writeTable_(sh, ['Что делает', 'Когда', 'Статус', 'Последний запуск', 'Результат'], rows, { top: 4, clear: false, textCols: [4] });
  try { sh.setColumnWidth(1, 430); sh.setColumnWidth(2, 200); sh.setColumnWidth(5, 330); } catch (e) {}
}
function installAutomationNow_() {
  if (notReady_()) { uiAlert_('Сначала «Первичная настройка».'); return; }
  var r = ensureAutomation_(true); autoRender_();
  uiAlert_('Автоматика включена: ' + r.total + ' запусков.\n\n' + AUTO_JOBS.map(function (j) { return '• ' + autoSchedText_(j) + ' — ' + j.what; }).join('\n'));
}
function removeAutomationNow_() {
  var mine = {}; AUTO_JOBS.forEach(function (j) { mine[j.fn] = true; });
  var n = 0; ScriptApp.getProjectTriggers().forEach(function (t) { if (mine[t.getHandlerFunction()]) { ScriptApp.deleteTrigger(t); n++; } });
  autoRender_(); uiAlert_('Автоматика выключена (снято запусков: ' + n + '). Кнопки меню работают.');
}
function autoStatusNow_() { autoRender_(); sheetOpen_(AUTO_SHEET); }
