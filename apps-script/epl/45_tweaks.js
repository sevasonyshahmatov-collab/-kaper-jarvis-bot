/* ==========================================================================
 * МОИ ПОПРАВКИ — как в хоккейных таблицах
 * --------------------------------------------------------------------------
 * Лист «Мои поправки»: команда, поправка атаки и обороны в процентах, срок действия, причина.
 *   Атака +10%  — команда забивает на 10% больше, чем считает модель (вернулся лучший бомбардир);
 *   Оборона −15% — пропускает на 15% больше (травмирован основной вратарь, два центральных защитника).
 * Поправка действует только на матчи, которые начнутся в срок «с … по …», и только пока матч не начался.
 * Прогноз без поправок тоже сохраняется — на листе «Точность» видно, помогают ли поправки на деле.
 * ========================================================================== */

var SHEET_TWEAKS = 'Мои поправки';
var TWEAK_HEAD = ['Команда', 'Атака, % (+ лучше)', 'Оборона, % (+ лучше)', 'С какого дня (ГГГГ-ММ-ДД)', 'По какой день', 'Причина', 'Добавлено'];
var TWEAK_MAX = 0.4;                         // больше ±40% не принимаем — это уже опечатка

function tweaksSheet_(ss) {
  var sh = ss.getSheetByName(SHEET_TWEAKS);
  if (sh) return sh;
  sh = ss.insertSheet(SHEET_TWEAKS);
  sh.getRange(1, 1).setValue('МОИ ПОПРАВКИ К СИЛЕ КОМАНД').setFontWeight('bold').setFontSize(12);
  sh.getRange(2, 1).setValue('Атака +10% — забивает на 10% больше, чем считает модель; Оборона −15% — пропускает на 15% больше. Действует на матчи в указанные даты (пусто — с сегодня / бессрочно), только до их начала. Удалите строку — поправка снята.').setFontColor('#666666');
  writeTable_(sh, TWEAK_HEAD, [], { top: 4, clear: false });
  ensureSize_(sh, 200, TWEAK_HEAD.length);
  sh.getRange(5, 4, 195, 2).setNumberFormat('@');
  try { sh.setColumnWidth(1, 160); sh.setColumnWidth(6, 320); } catch (e) {}
  tweaksValidation_(ss, sh);
  return sh;
}
/** Выпадающий список команд в колонке «Команда». */
function tweaksValidation_(ss, sh) {
  var teams = {}; matchesRead_(ss).forEach(function (m) { teams[m.home] = true; teams[m.away] = true; });
  var list = Object.keys(teams).sort();
  if (!list.length) return;
  var rule = SpreadsheetApp.newDataValidation().requireValueInList(list, true).setAllowInvalid(false).build();
  sh.getRange(5, 1, 195, 1).setDataValidation(rule);
}
function pctNum_(v) {
  if (v === '' || v === null || v === undefined) return 0;
  var n = typeof v === 'number' ? (Math.abs(v) <= 1 && String(v).indexOf('.') >= 0 ? v * 100 : v) : Number(String(v).replace('%', '').replace(',', '.').replace('−', '-'));
  return isFinite(n) ? n / 100 : 0;
}
/** Действующие поправки: [{team, a, d, from, to, why}] (a, d — доли: 0.1 = +10%). */
function tweaksRead_(ss) {
  var sh = ss.getSheetByName(SHEET_TWEAKS);
  if (!sh || sh.getLastRow() < 5) return [];
  return sh.getRange(5, 1, sh.getLastRow() - 4, TWEAK_HEAD.length).getValues().filter(function (r) { return r[0]; }).map(function (r) {
    var d = function (x) { if (!x) return ''; if (x instanceof Date) return dayKey_(x); return String(x).trim(); };
    return { team: String(r[0]).trim(), a: Math.max(-TWEAK_MAX, Math.min(TWEAK_MAX, pctNum_(r[1]))), d: Math.max(-TWEAK_MAX, Math.min(TWEAK_MAX, pctNum_(r[2]))),
      from: d(r[3]), to: d(r[4]), why: String(r[5] || '') };
  }).filter(function (t) { return t.a || t.d; });
}
/** Поправка команды на день матча (в логарифме, складывается с силой). */
function tweakFor_(list, team, key) {
  var out = { a: 0, d: 0, why: [] };
  list.forEach(function (t) {
    if (t.team !== team) return;
    if (t.from && key < t.from) return;
    if (t.to && key > t.to) return;
    out.a += Math.log(1 + t.a); out.d += -Math.log(1 - t.d);      // оборона +10% = пропускает в 0,9 раза
    out.why.push(team + (t.a ? ' атака ' + (t.a > 0 ? '+' : '') + Math.round(t.a * 100) + '%' : '') + (t.d ? ' оборона ' + (t.d > 0 ? '+' : '') + Math.round(t.d * 100) + '%' : '') + (t.why ? ' (' + t.why + ')' : ''));
  });
  return out;
}
function tweaksOpen_() { tweaksSheet_(SpreadsheetApp.getActive()); sheetOpen_(SHEET_TWEAKS); }
function tweaksApplyNow_() {
  var ss = SpreadsheetApp.getActive(), n = tweaksRead_(ss).length;
  refreshModelSheets_(ss);
  uiAlert_('Поправок действует: ' + n + '. Прогнозы на ещё не начавшиеся матчи пересчитаны.');
}
