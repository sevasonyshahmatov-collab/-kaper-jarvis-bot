/* ==========================================================================
 * КАРТОЧКА КОМАНДЫ — выберите клуб в ячейке B2, лист соберёт всё о нём
 *  Сила и место по модели, сезон (очки, мячи, xG, очки «по игре»), шансы по «Прогнозу сезона»,
 *  последние матчи и ближайшие — с шансами на победу, ничью и поражение.
 *  Перерисовывается сразу при смене команды (onEdit) и после каждого обновления таблицы.
 * ========================================================================== */

var SHEET_CARD = 'Карточка команды';

function onEdit(e) {
  try {
    var r = e && e.range; if (!r) return;
    var sh = r.getSheet();
    if (sh.getName() === SHEET_CARD && r.getA1Notation() === 'B2') cardRender_(sh.getParent(), String(r.getValue() || '').trim());
  } catch (err) { /* простой триггер: ошибки не показываем */ }
}

function cardTeams_(ss) { var t = {}; matchesRead_(ss).forEach(function (m) { t[m.home] = true; t[m.away] = true; }); return Object.keys(t).sort(); }
function cardSheet_(ss) {
  var sh = ss.getSheetByName(SHEET_CARD) || ss.insertSheet(SHEET_CARD);
  var list = cardTeams_(ss);
  if (list.length) sh.getRange(2, 2).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(list, true).setAllowInvalid(false).build());
  return sh;
}
/** Строка листа с шапкой в строке 4 по названию команды в колонке «Команда». */
function rowOf_(ss, name, team) {
  var sh = ss.getSheetByName(name); if (!sh) return null;
  return readTable_(sh, 4).filter(function (r) { return r['Команда'] === team; })[0] || null;
}
function cardRender_(ss, team) {
  ss = ss || SpreadsheetApp.getActive();
  var sh = cardSheet_(ss);
  team = team || String(sh.getRange(2, 2).getValue() || '').trim() || cardTeams_(ss)[0];
  if (!team) return;
  sh.getRange(5, 1, Math.max(1, sh.getMaxRows() - 4), Math.min(8, sh.getMaxColumns())).clearContent();
  sh.getRange(1, 1).setValue('КАРТОЧКА КОМАНДЫ').setFontWeight('bold').setFontSize(13);
  sh.getRange(2, 1).setValue('Команда →').setFontWeight('bold');
  sh.getRange(2, 2).setValue(team).setFontWeight('bold').setBackground('#fff4d6');
  sh.getRange(3, 1).setValue('Выберите клуб в жёлтой ячейке — карточка обновится. Данные — с листов «Сила команд», «Таблица», «Прогноз сезона», «Прогнозы».').setFontColor('#666666');
  var out = [], sec = function (t) { out.push([t, '', '', '', '', '']); }, line = function (a, b, c, d, e, f) { out.push([a, b === undefined ? '' : b, c === undefined ? '' : c, d === undefined ? '' : d, e === undefined ? '' : e, f === undefined ? '' : f]); };
  var pw = rowOf_(ss, SHEET_POWER, team), tb = rowOf_(ss, SHEET_TABLE, team), se = rowOf_(ss, SHEET_SEASON, team);
  sec('СИЛА ПО МОДЕЛИ');
  if (pw) {
    line('Место по силе', pw['Место'], 'за неделю', pw['За неделю'] || '—');
    line('Сила (голов против среднего соперника)', pw['Сила (разница голов против среднего соперника)'], 'изменение за неделю', pw['Сила: изменение за неделю'] === '' ? '—' : pw['Сила: изменение за неделю']);
    line('Забивает за матч (ожид.)', pw['Забивает за матч (ожид.)'], 'пропускает', pw['Пропускает за матч (ожид.)']);
    line('Реализация: голы минус xG', pw['Голы минус xG (реализация)'], 'вратарь и удача: xGA минус пропущенные', pw['xG против минус пропущенные (вратарь и удача)']);
  } else line('нет данных');
  sec('СЕЗОН');
  if (tb) {
    line('Место в таблице', tb['М'], 'очки', tb['Очки']);
    line('Игры: В / Н / П', tb['В'] + ' / ' + tb['Н'] + ' / ' + tb['П'], 'мячи', tb['Мячи']);
    line('Очки по игре (xPts)', tb['Очки по игре (xPts)'], 'очки минус xPts', tb['Очки минус xPts']);
    line('Форма (последние 5)', tb['Форма']);
  } else line('нет данных');
  sec('ПРОГНОЗ СЕЗОНА');
  if (se) {
    line('Очки в конце (ожид.)', se['Очки в конце (ожид.)'], '80% случаев', se['Очки: 80% случаев']);
    line('Место в среднем', se['Место в среднем'], 'чемпион', se['Чемпион']);
    line('Топ-4 (Лига чемпионов)', se['Топ-4 (Лига чемпионов)'], 'топ-7 (еврокубки)', se['Топ-7 (еврокубки)']);
    line('Вылет', se['Вылет']);
  } else line('нет данных');
  var matches = matchesRead_(ss).filter(function (m) { return m.home === team || m.away === team; }), now = new Date(), log = plogRead_(ss), odds = oddsRead_(ss);
  sec('ПОСЛЕДНИЕ МАТЧИ');
  line('Дата', 'Соперник', 'Где', 'Счёт', 'xG', 'Итог');
  matches.filter(function (m) { return m.status === ST_PLAYED && m.hg !== null; }).slice(-6).reverse().forEach(function (m) {
    var home = m.home === team, gf = home ? m.hg : m.ag, ga = home ? m.ag : m.hg;
    line(keyRu_(dayKey_(m.start)), home ? m.away : m.home, home ? 'дома' : 'в гостях', gf + ':' + ga,
      m.hx !== null && m.ax !== null ? r2_(home ? m.hx : m.ax) + ' – ' + r2_(home ? m.ax : m.hx) : '', gf > ga ? 'победа' : gf === ga ? 'ничья' : 'поражение');
  });
  sec('БЛИЖАЙШИЕ МАТЧИ');
  line('Дата', 'Соперник', 'Где', 'Победа / ничья / поражение, %', 'Кэф на победу', 'Вероятный счёт');
  matches.filter(function (m) { return m.start > now && m.status !== ST_PLAYED && m.status !== ST_CANC; }).slice(0, 5).forEach(function (m) {
    var home = m.home === team, p = log[m.id], o = odds[m.id];
    line(keyRu_(dayKey_(m.start)) + ' ' + fmt_(m.start, 'HH:mm'), home ? m.away : m.home, home ? 'дома' : 'в гостях',
      p ? pct_(home ? p.p1 : p.p2) + ' / ' + pct_(p.px) + ' / ' + pct_(home ? p.p2 : p.p1) : '', o ? (home ? o['П1'] : o['П2']) : '', p ? (home ? p.score : p.score.split(':').reverse().join(':')) : '');
  });
  ensureSize_(sh, 5 + out.length, 6);
  sh.getRange(5, 1, out.length, 6).setNumberFormat('@').setValues(out.map(function (r) { return r.map(function (x) { return x === null || x === undefined ? '' : String(x); }); }));
  out.forEach(function (r, i) { if (/^[А-ЯЁ ]+$/.test(r[0]) && !r[1]) sh.getRange(5 + i, 1, 1, 6).setFontWeight('bold').setBackground('#0b3d2e').setFontColor('#ffffff'); else sh.getRange(5 + i, 1, 1, 6).setFontWeight('normal').setBackground(null).setFontColor('#000000'); });
  try { sh.setColumnWidth(1, 300); sh.setColumnWidths(2, 5, 170); } catch (e) {}
}
