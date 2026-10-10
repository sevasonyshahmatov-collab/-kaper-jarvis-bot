/* ПОСТЫ-ПРОГНОЗЫ НХЛ — ОТДЕЛЬНЫЙ ФАЙЛ, вставлять только в таблицу НХЛ.
 *
 * Что делает: бот присылает вам в личку пост-прогноз на каждый матч НХЛ — так же, как в КХЛ (фактура, текст ИИ,
 * строка «ПРОГНОЗ», запасной вариант, лист «Посты»). Матчи НХЛ идут ночью по Москве, поэтому посты на матчи
 * ближайшей ночи приходят вечером: с 18:00 МСК (22:00 по Красноярску), каждый не позже чем за 2 ч 20 мин до начала.
 * Дневные матчи — как в КХЛ, за 3–4 часа. Эмодзи клубов НХЛ — лист «Эмодзи_клубов» (можно править).
 *
 * КАК ВСТАВИТЬ (Расширения → Apps Script в таблице НХЛ):
 *  1. Слева у «Файлы» нажмите «+» → «Скрипт», назовите «Посты_НХЛ». Файл должен стоять в списке ниже «Код».
 *  2. Удалите в новом файле всё, что там есть, вставьте этот файл целиком (вместе с этим комментарием), Ctrl+S.
 *  3. Меню (по желанию): в «Код.gs» найдите (Ctrl+F) строку
 *        ui.createMenu('📩 НХЛ → мне в ТГ')
 *     и сразу под ней вставьте две строки:
 *        .addItem('✍️ Пост-прогноз на матч', 'postNowMenu_')
 *        .addItem('✍️ Посты-прогнозы: включить / выключить', 'postToggle_')
 *     Ctrl+S, обновите страницу таблицы.
 *  4. В таблице: меню «НХЛ-парсер» → Настройки → «Включить всю автоматику» — появится запуск постов раз в 15 минут
 *     (или подождите утреннего обновления — оно само доставит недостающий запуск).
 *
 * Код ниже заменяет одноимённые функции из «Код.gs» (в Apps Script работает та, что в файле ниже по списку).
 * В репозитории это уже внесено в apps-script/nhl/Код.js — при следующей полной заливке кода этот файл можно удалить.
 */

var POST_NIGHT_FROM_H = 18;         // НХЛ: с 18:00 МСК (22:00 по Красноярску) — посты на все матчи ближайшей ночи
var POST_NIGHT_AHEAD_MIN = 14 * 60; // «ближайшая ночь» — матчи, которые начнутся в ближайшие 14 часов
var POST_EMOJI_DEFAULT = [['Анахайм', '🦆'], ['Бостон', '🐻'], ['Баффало', '🦬'], ['Калгари', '🔥'], ['Каролина', '🌀'],
  ['Чикаго', '🪶'], ['Колорадо', '🏔'], ['Коламбус', '💥'], ['Даллас', '⭐'], ['Детройт', '🛞'], ['Эдмонтон', '🛢'],
  ['Флорида', '🐆'], ['Лос-Анджелес', '👑'], ['Миннесота', '🌲'], ['Монреаль', '⚜️'], ['Нэшвилл', '🐯'], ['Нью-Джерси', '😈'],
  ['Айлендерс', '🏝'], ['Рейнджерс', '🗽'], ['Оттава', '🏛'], ['Филадельфия', '🟠'], ['Питтсбург', '🐧'], ['Сан-Хосе', '🦈'],
  ['Сиэтл', '🦑'], ['Сент-Луис', '🎵'], ['Тампа-Бэй', '⚡'], ['Торонто', '🍁'], ['Юта', '🦣'], ['Ванкувер', '🐋'],
  ['Вегас', '⚔️'], ['Вашингтон', '🦅'], ['Виннипег', '✈️']];

function postEmoji_(ss) {
  var sh = ss.getSheetByName(POST_EMOJI_SHEET);
  if (!sh) {
    sh = ss.insertSheet(POST_EMOJI_SHEET);
    sh.getRange(1, 1, 1, 2).setValues([['Команда', 'Эмодзи']]).setFontWeight('bold');
    sh.getRange(2, 1, POST_EMOJI_DEFAULT.length, 2).setValues(POST_EMOJI_DEFAULT);
    sh.setFrozenRows(1);
    sh.getRange(1, 4).setValue('Это подставляется в заголовок поста. Меняйте на свои — пост возьмёт новые со следующего раза.');
  }
  var out = {};
  if (sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues().forEach(function (r) { if (r[0]) out[String(r[0]).trim()] = String(r[1] || ''); });
  // лист достался от таблицы КХЛ (клубов НХЛ на нём нет) — дописываем клубы НХЛ, ваши правки не трогаем
  var miss = POST_EMOJI_DEFAULT.filter(function (x) { return !(x[0] in out); });
  if (miss.length === POST_EMOJI_DEFAULT.length) {
    sh.getRange(sh.getLastRow() + 1, 1, miss.length, 2).setValues(miss);
    miss.forEach(function (x) { out[x[0]] = x[1]; });
  }
  return out;
}

/** Какие матчи пора описывать: начало через POST_LATE_MIN…POST_LEAD_MIN минут, а с POST_NIGHT_FROM_H по МСК —
 *  все матчи ближайшей ночи (начало в пределах POST_NIGHT_AHEAD_MIN). Пост по матчу уходит один раз (postSentKey_). */
function postDue_(ss, now) {
  var sh = ss.getSheetByName(SHEET_ODDS_LOG), out = [];
  if (!sh || sh.getLastRow() < 2) return out;
  var evening = Number(Utilities.formatDate(now, 'Europe/Moscow', 'H')) >= POST_NIGHT_FROM_H;
  sh.getRange(2, 1, sh.getLastRow() - 1, ODDS_HEADER.length).getValues().forEach(function (r) {
    var start = new Date(String(r[15]));
    if (isNaN(start.getTime())) return;
    var mins = (start - now) / 60000;
    if (mins < POST_LATE_MIN || mins > (evening ? Math.max(POST_LEAD_MIN, POST_NIGHT_AHEAD_MIN) : POST_LEAD_MIN)) return;
    out.push({ day: String(r[2]), time: String(r[1]).slice(11), home: String(r[3]).trim(), away: String(r[4]).trim() });
  });
  out.sort(function (a, b) { return a.time < b.time ? -1 : 1; });
  return out;
}

function postNowMenu_() {
  var ss = SpreadsheetApp.getActive(), now = new Date();
  var day = nhlBriefDay_(now), list = agentMatchesOfDay_(ss, day);
  if (!list.length) { uiAlert_('В ближайшую ночь матчей нет.'); return; }
  var ui = SpreadsheetApp.getUi();
  var r = ui.prompt('Пост-прогноз', 'Матчи ближайшей ночи:\n' + list.map(function (m, i) { return (i + 1) + ') ' + m.time + '  ' + m.home + ' — ' + m.away; }).join('\n') +
    '\n\nНомер матча (или «все»):', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var a = String(r.getResponseText() || '').trim().toLowerCase();
  var pick = a === 'все' ? list : [list[Number(a) - 1]].filter(Boolean);
  if (!pick.length) { uiAlert_('Не понял номер матча.'); return; }
  var ok = 0, err = [];
  pick.forEach(function (m) {
    m.day = day;
    try { if (postSendOne_(ss, m, now).sent) ok++; } catch (e) { err.push(m.home + ' — ' + m.away + ': ' + e.message); }
  });
  sheetOpen_(POST_SHEET);
  uiAlert_('Готово: постов отправлено вам в Telegram — ' + ok + '.' + (err.length ? '\n\nНе получилось:\n' + err.join('\n') : ''));
}

// запуск раз в 15 минут — в список автоматики (без дубля, если он уже есть в «Код.gs»)
if (!AUTO_JOBS.some(function (j) { return j.fn === 'postAuto_'; })) AUTO_JOBS.push({ fn: 'postAuto_', kind: 'minutes', every: 15, what: 'Пост-прогноз на каждый матч вам в личку: на матчи ночи — с 18:00 МСК (22:00 по Красноярску), не позже чем за 2 ч 20 мин до начала' });
