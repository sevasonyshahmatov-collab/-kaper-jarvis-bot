/* ==========================================================================
 * НХЛ-ПАРСЕР · КАПЕР ДЖАРВИС НХЛ
 * Та же модель и те же листы, что в таблице КХЛ; источники — API НХЛ, Pinnacle (NHL), sports.ru, Telegram.
 * Первый запуск: меню «НХЛ-парсер» → Настройки → «Первичная настройка таблицы под НХЛ».
 * Собрано из KHL_Parser.gs: не правьте вручную — обе таблицы обновляются вместе.
 * ==========================================================================*/
/**
 * КХЛ — автозагрузка результатов матчей со Sports.ru по кнопке одной строкой меню.
 *
 * УСТАНОВКА:
 * 1. Откройте вашу таблицу → Расширения → Apps Script.
 * 2. Удалите содержимое файла Code.gs и вставьте вместо него весь этот файл.
 * 3. Сохраните (значок дискеты), закройте редактор, обновите страницу таблицы.
 * 4. В таблице появится меню «НХЛ-парсер» → «Обновить всё после игрового дня».
 *    При первом запуске Google попросит авторизовать скрипт — это нормально.
 *
 * ВАЖНО, ПРОЧТИТЕ ПЕРЕД ЗАПУСКОМ:
 * - Ниже указаны названия листа и столбцов ТОЧНО как в вашей таблице на момент
 *   анализа. Если вы переименуете лист «Результаты» или заголовки столбцов —
 *   поправьте константы SHEET_RESULTS / SHEET_TEAMS и объект col ниже.
 * - Скрипт читает внешнюю страницу sports.ru. Она не находится под вашим
 *   контролем и может в любой момент немного поменять вёрстку — тогда
 *   регулярное выражение в parseMatches_() перестанет находить матчи.
 *   Проверить это просто: если после нажатия кнопки выходит «0 матчей
 *   обновлено», откройте Apps Script → Выполнения (Executions) и посмотрите
 *   журнал — там будет видно, что вернул сайт.
 * - Скрипт точно определяет исход в овертайме/буллитах — sports.ru помечает такие
 *   матчи буквой «б» (буллиты) или «от» (овертайм) прямо в счёте, и парсер это
 *   учитывает. Раньше это определялось только эвристикой (разница в 1 шайбу) —
 *   теперь не нужно ничего перепроверять вручную.
 */

var SHEET_RESULTS = 'результаты матчей';   // <-- проверено по вашей таблице
var SHEET_TEAMS   = 'Справочник команд';   // <-- проверено по вашей таблице
var SHEET_ELO     = 'Elo';                 // <-- создаётся скриптом автоматически

// Параметры Elo-рейтинга
var ELO_K = 20;          // насколько сильно один матч двигает рейтинг
var ELO_BASE = 1500;     // Elo, соответствующий стартовому рейтингу 50 (середина шкалы)
var ELO_SCALE = 6;       // 1 пункт стартового рейтинга (1-100) = 6 очков Elo
var ELO_OT_CREDIT = 0.75; // "неполная" победа в ОТ/буллитах (не 1.0, а 0.75 против 0.25)
// «Быстрый старт» рейтинга: в первых ELO_EARLY_GAMES играх сезона каждой команды
// рейтинг двигается сильнее (в 1 + ELO_EARLY_BOOST раз в первой игре, плавно до обычного).
// 0 = выключено. Значение выбирается только по результату «Самопроверки» (тест 3).
var ELO_EARLY_BOOST = 0;
var ELO_EARLY_GAMES = 15;

/** Скорость рейтинга для команды, сыгравшей n матчей в текущем сезоне. */
function eloTeamK_(n, baseK, boost, games) {
  if (baseK === undefined) baseK = ELO_K;
  if (boost === undefined) boost = ELO_EARLY_BOOST;
  if (games === undefined) games = ELO_EARLY_GAMES;
  if (!(boost > 0) || !(games > 0)) return baseK;
  return baseK * (1 + boost * Math.max(0, 1 - (n || 0) / games));
}
var FORM_WINDOW = 8;      // сколько последних игр ТЕКУЩЕГО сезона учитывать во взвешенной форме
var FORM_SCALE = 20;      // множитель перевода "перфоманс минус ожидание" в шкалу рейтинга —
                            // подобран заново под новую (более узкую) дельта-шкалу, чтобы сохранить
                            // прежнюю значимость фактора формы, как приоритетного по просьбе пользователя

var SOURCE_URLS = [
  'https://www.sports.ru/hockey/tournament/khl/calendar/2026-2027/',
  'https://www.sports.ru/hockey/tournament/khl/calendar/'
];

// Написания команд на sports.ru, которых может не быть в вашей колонке
// "Старые / альтернативные названия". Дополняйте по мере необходимости.
var EXTRA_ALIASES = {
  'Металлург Мг': 'Металлург',
  'Шанхай Дрэгонс': 'Шанхайские Драконы',
  'Локомотив Я': 'Локомотив',
  'Спартак Москва': 'Спартак',
  'ЦСКА Москва': 'ЦСКА',
  'Амур Хабаровск': 'Амур',
  'Динамо Мск': 'Динамо Москва',
  'Динамо Мн': 'Динамо Минск'
};

/**
 * Показывает окошко с сообщением, если скрипт запущен вручную (через меню).
 * Если скрипт запущен автоматически по расписанию — окна показать нельзя,
 * тогда сообщение просто пишется в журнал (Apps Script → Выполнения).
 */
function notify_(message) {
  uiAlert_(message);
}

/*
 * «Тихий режим» для общей кнопки: пока он включён, окна с сообщениями не
 * показываются, а текст копится в QUIET_LOG_ — в конце выводится одна сводка.
 * Окна-подтверждения (Да/Нет) в тихом режиме возвращают «нет», поэтому в
 * общую кнопку такие функции не включены.
 */
var QUIET_ = false;
var QUIET_LOG_ = [];
function uiAlert_(a, b, c) {
  if (QUIET_) {
    QUIET_LOG_.push(String(c !== undefined || b !== undefined && typeof b === 'string' ? b : a));
    return null;
  }
  try {
    var ui = SpreadsheetApp.getUi();
    if (c !== undefined) return ui.alert(a, b, c);
    if (b !== undefined) return ui.alert(a, b);
    return ui.alert(a);
  } catch (e) {
    Logger.log(String(b !== undefined && typeof b === 'string' ? b : a)); // запуск по расписанию — окон нет
    return null;
  }
}


/** Отдельное меню для роликов экспертов (общее для КХЛ и НХЛ). */
function videoMenu_(ui, title) {
  ui.createMenu(title)
    .addItem('🎬 Вставить видео (ссылка → сразу разбор в Gemini)', 'videoInsert_')
    .addItem('➕ Добавить ролик (открыть список ссылок)', 'videoOpenList_')
    .addItem('▶️ Разобрать новые ролики (Gemini)', 'videoAnalyzeNow_')
    .addItem('🔁 Разобрать все ролики заново', 'videoReanalyzeNow_')
    .addSeparator()
    .addItem('📊 Точность экспертов из роликов', 'expertPicksReportNow_')
    .addItem('📋 Что вытащили из роликов (сводка по командам)', 'videoOpenSummary_')
    .addSeparator()
    .addItem('🔄 Учесть видео в прогнозах сейчас', 'videoApplyNow_')
    .addItem('✅ Применить расклад к стартовому рейтингу', 'preseasonApply_')
    .addItem('↩️ Вернуть прежний стартовый рейтинг', 'preseasonRevert_')
    .addToUi();
}

/** Строит словарь "любое написание команды" → "каноничное название" из листа Команды */
function buildNameMap_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(SHEET_TEAMS);
  var map = {};

  if (sh) {
    var data = sh.getDataRange().getValues();
    for (var i = 0; i < data.length; i++) {
      var canon = String(data[i][0]).trim();
      var alt = String(data[i][1]).trim();
      if (!canon || canon === 'Команда (каноничное название)') continue;
      map[canon] = canon;
      if (alt) {
        alt.split(/[,/]/).forEach(function (a) {
          a = a.trim();
          if (a) map[a] = canon;
        });
      }
    }
  }
  for (var k in EXTRA_ALIASES) map[k] = EXTRA_ALIASES[k];
  return map;
}

/** Приводит дату (Date, текст "дд.мм.гггг", что угодно) к строке "гггг-мм-дд" для надёжного сравнения между листами. */
function dateOnlyKey_(v) {
  if (v instanceof Date) return Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  var s = String(v).trim();
  var m = s.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
  if (m) return m[3] + '-' + m[2] + '-' + m[1];
  return s;
}

function normalizeTeam_(name, map) {
  name = String(name).trim();
  return map[name] || name;
}

/** Строит адрес календаря конкретного месяца сезона, напр. ?m=9 для сентября */
function monthUrl_(monthNumber) {
  return 'https://www.sports.ru/hockey/tournament/khl/calendar/2026-2027/?m=' + monthNumber;
}


/** Убирает повторяющиеся матчи (могли встретиться на нескольких страницах) */
function dedupeMatches_(matches) {
  var seen = {};
  var result = [];
  for (var i = 0; i < matches.length; i++) {
    var m = matches[i];
    var key = m.date + '|' + m.home + '|' + m.away;
    if (!seen[key]) {
      seen[key] = true;
      result.push(m);
    }
  }
  return result;
}

/**
 * Подстраховка: если по какой-то причине разметка sports.ru для только что
 * завершившихся матчей отличается от архивной, и метка «от»/«б» приклеилась
 * к названию команды вместо того, чтобы отделиться в счёт — отрезаем её здесь.
 * Ни одна команда КХЛ не заканчивается словом «от» или «б», так что это безопасно.
 */
function stripTrailingOTMarker_(name) {
  var m = name.match(/^(.*?)\s*(б|от)$/);
  if (m && m[1].trim().length > 0) {
    return { name: m[1].trim(), ot: true };
  }
  return { name: name, ot: false };
}

/**
 * Извлекает из текста страницы записи вида:
 *   05.09.2026 16:30 Локомотив 2 - 1 Трактор                  (обычная победа)
 *   05.09.2026 16:30 Локомотив б2 - 1 Трактор                 (по буллитам)
 *   05.09.2026 16:30 Локомотив от2 - 1 Трактор                (в овертайме)
 * sports.ru ставит букву «б» (буллиты) или «от» (овертайм) прямо перед одним из
 * чисел счёта — неважно, перед каким. Без учёта этой буквы такие матчи вообще
 * не распознавались регулярным выражением и тихо пропускались.
 * Ещё не сыгранные матчи (со счётом "- - -") в результат не попадают.
 */
function parseMatches_(pageText) {
  var text = pageText.replace(/<[^>]+>/g, ' ');
  var re = /(\d{2}\.\d{2}\.\d{4})\s*(?:\d{2}:\d{2})?\s*([А-ЯЁа-яё][А-ЯЁа-яё \-]*?)\s*(б|от)?(\d+)\s*[-–]\s*(б|от)?(\d+)\s*([А-ЯЁа-яё][А-ЯЁа-яё \-]*?)(?=\s*\d{2}\.\d{2}\.\d{4}|$)/g;
  var matches = [];
  var m;
  while ((m = re.exec(text)) !== null) {
    var homeClean = stripTrailingOTMarker_(m[2].trim());
    var awayClean = stripTrailingOTMarker_(m[7].trim());
    matches.push({
      date: m[1],
      home: homeClean.name,
      homeGoals: parseInt(m[4], 10),
      awayGoals: parseInt(m[6], 10),
      away: awayClean.name,
      ot: !!(m[3] || m[5]) || homeClean.ot || awayClean.ot
    });
  }
  return matches;
}

function dateFromRu_(d) {
  var p = d.split('.');
  return new Date(Number(p[2]), Number(p[1]) - 1, Number(p[0]));
}

function sameDate_(cellValue, ruDateStr) {
  var wmDate = dateFromRu_(ruDateStr);
  if (cellValue instanceof Date) {
    return cellValue.getFullYear() === wmDate.getFullYear() &&
           cellValue.getMonth() === wmDate.getMonth() &&
           cellValue.getDate() === wmDate.getDate();
  }
  // на случай, если дата в ячейке хранится как текст "10.09.2026"
  return String(cellValue).indexOf(ruDateStr) !== -1;
}

function updateResultsFromWeb() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(SHEET_RESULTS);

  if (!sh) {
    notify_('Не найден лист "' + SHEET_RESULTS + '". Поправьте константу SHEET_RESULTS в коде.');
    return;
  }

  var nameMap;
  var webMatches = [];
  var loadErr = '';
  try {
    nameMap = buildNameMap_();
  } catch (e) {
    notify_('Ошибка загрузки данных: ' + e.message);
    return;
  }
  try {
    var texts = fetchAllCalendarTexts_();
    var allMatches = [];
    for (var t = 0; t < texts.length; t++) {
      allMatches = allMatches.concat(parseMatches_(texts[t]));
    }
    webMatches = dedupeMatches_(allMatches);
  } catch (e) { loadErr = e.message; }

  // новая разметка sports.ru: счёт со страниц матчей — только для матчей, которых ещё нет в таблице
  var mpInfo = null;
  try {
    var pre = sh.getDataRange().getValues(), h0 = pre[0];
    var cD = h0.indexOf('Дата'), cS = h0.indexOf('Статус'), cH = h0.indexOf('Хозяева'), cA = h0.indexOf('Гости');
    var planned = [];
    for (var q = 1; q < pre.length; q++) {
      if (String(pre[q][cS]).trim() !== 'Запланирован' || !(pre[q][cD] instanceof Date)) continue;
      planned.push({ date: pre[q][cD], home: normalizeTeam_(pre[q][cH], nameMap), away: normalizeTeam_(pre[q][cA], nameMap) });
    }
    if (planned.length) {
      mpInfo = mpFetchPlayed_(planned, nameMap, new Date());
      webMatches = dedupeMatches_(webMatches.concat(mpInfo.matches));
    }
  } catch (e) { loadErr = (loadErr ? loadErr + '; ' : '') + 'страницы матчей: ' + e.message; }

  if (webMatches.length === 0) {
    if (mpInfo && mpInfo.checked === 0 && !loadErr) { return; }   // новых сыгранных матчей просто нет
    notify_(
      'На странице sports.ru не найдено ни одного сыгранного матча по текущему ' +
      'регулярному выражению. Откройте Apps Script → Выполнения, чтобы посмотреть ' +
      'фактический текст страницы, и поправьте parseMatches_().'
    );
    return;
  }

  var data = sh.getDataRange().getValues();
  var header = data[0];
  var col = {
    date: header.indexOf('Дата'),
    status: header.indexOf('Статус'),
    home: header.indexOf('Хозяева'),
    away: header.indexOf('Гости'),
    homeGoals: header.indexOf('Г Хозяев'),
    awayGoals: header.indexOf('Г Гостей'),
    ot: header.indexOf('ОТ/буллиты?'),
    winner: header.indexOf('Победитель'),
    homePts: header.indexOf('Очки Х'),
    awayPts: header.indexOf('Очки Г')
  };

  for (var key in col) {
    if (col[key] === -1) {
      notify_('Не найден столбец "' + key + '" в листе "' + SHEET_RESULTS + '". Проверьте заголовки.');
      return;
    }
  }

  // результаты, вписанные вручную, — заморозить их прогнозы до пересчёта Elo
  var manualFrozen = 0;
  try { manualFrozen = freezeManualResults_(); } catch (eM) { /* не критично */ }

  var updated = 0;
  var plannedRowsSample = [];
  var webMatchesSample = [];

  // индекс строк листа "прогнозы" по ключу "дата|хозяева|гости" — нужен, чтобы
  // заморозить прогноз именно этой строки в момент, когда матч сыгран (см. ниже,
  // почему это критично для честности трекера точности)
  var progSh = ss.getSheetByName('прогнозы');
  var progIndex = {};
  if (progSh) {
    var progLastRow = progSh.getLastRow();
    if (progLastRow >= 2) {
      var progData = progSh.getRange(2, 1, progLastRow - 1, 3).getValues(); // A,B,C = Дата,Хозяева,Гости
      for (var pr = 0; pr < progData.length; pr++) {
        var pDate = progData[pr][0], pHome = String(progData[pr][1]).trim(), pAway = String(progData[pr][2]).trim();
        if (!pHome || !pAway) continue;
        var pKey = dateOnlyKey_(pDate) + '|' + pHome + '|' + pAway;
        progIndex[pKey] = pr + 2; // реальный номер строки на листе
      }
    }
  }

  for (var r = 1; r < data.length; r++) {
    if (String(data[r][col.status]).trim() !== 'Запланирован') continue;

    var rowHome = normalizeTeam_(data[r][col.home], nameMap);
    var rowAway = normalizeTeam_(data[r][col.away], nameMap);

    if (plannedRowsSample.length < 5) {
      var rawDate = data[r][col.date];
      var dateStr = (rawDate instanceof Date)
        ? Utilities.formatDate(rawDate, Session.getScriptTimeZone(), 'dd.MM.yyyy')
        : String(rawDate);
      plannedRowsSample.push(dateStr + ' | ' + rowHome + ' — ' + rowAway);
    }

    for (var i = 0; i < webMatches.length; i++) {
      var wm = webMatches[i];
      var wmHome = normalizeTeam_(wm.home, nameMap);
      var wmAway = normalizeTeam_(wm.away, nameMap);

      if (wmHome === rowHome && wmAway === rowAway && sameDate_(data[r][col.date], wm.date)) {
        var sheetRow = r + 1;
        var hg = wm.homeGoals, ag = wm.awayGoals;

        sh.getRange(sheetRow, col.homeGoals + 1).setValue(hg);
        sh.getRange(sheetRow, col.awayGoals + 1).setValue(ag);
        sh.getRange(sheetRow, col.status + 1).setValue('Сыгран');

        var homeWon = hg > ag;
        var winnerName = homeWon ? rowHome : rowAway;
        var isOT = !!wm.ot; // теперь это реальный флаг с сайта, а не догадка

        sh.getRange(sheetRow, col.winner + 1).setValue(isOT ? winnerName + ' (в ОТ/буллитах)' : winnerName);
        sh.getRange(sheetRow, col.homePts + 1).setValue(homeWon ? 2 : (isOT ? 1 : 0));
        sh.getRange(sheetRow, col.awayPts + 1).setValue(!homeWon ? 2 : (isOT ? 1 : 0));
        sh.getRange(sheetRow, col.ot + 1).setValue(isOT);

        // ЗАМОРОЗКА ПРОГНОЗА: как только матч сыгран, фиксируем текущие (ещё
        // не тронутые пересчётом Elo этого матча) значения шансов и ожидаемых
        // голов как обычные числа вместо живой формулы. Без этого шага
        // строка задним числом "узнавала" бы результат через обновлённый
        // рейтинг команд при следующем пересчёте Elo — прогноз бы незаметно
        // подгонялся под факт, и трекер точности врал бы.
        var progRow = progIndex[dateOnlyKey_(data[r][col.date]) + '|' + rowHome + '|' + rowAway];
        if (progRow) {
          freezePredictionRow_(progSh, progRow); // до пересчёта Elo по этому матчу — прогноз честный
        }

        updated++;
        break;
      }
    }
  }

  var msg = updated + ' матч(ей) обновлено.' + (manualFrozen ? ' Вписанных вручную: ' + manualFrozen + '.' : '') +
    (mpInfo && mpInfo.checked ? ' Со страниц матчей: проверено ' + mpInfo.checked + ', получен счёт ' + mpInfo.matches.length +
      (mpInfo.checked > mpInfo.matches.length ? ' (остальные sports.ru ещё не закрыл — добавятся при следующем обновлении)' : '') + '.' : '');

  if (updated > 0 || manualFrozen > 0) {
    try {
      computeAndWriteElo_(true); // true = не показывать отдельное окно, добавим строку в это же сообщение
      msg += '\nElo-рейтинг пересчитан.';
      try { updateLeagueRates_(true); } catch (e2) { /* не критично: доли по лиге обновятся в следующий раз */ }
    } catch (e) {
      msg += '\n\nМатчи обновились, но пересчитать Elo не получилось: ' + e.message;
    }
  }

  if (updated === 0) {
    var sortedForDiag = webMatches.slice().sort(function (a, b) {
      return dateFromRu_(b.date) - dateFromRu_(a.date);
    });
    for (var j = 0; j < Math.min(5, sortedForDiag.length); j++) {
      var wm2 = sortedForDiag[j];
      webMatchesSample.push(
        wm2.date + ' | ' + normalizeTeam_(wm2.home, nameMap) + ' ' + wm2.homeGoals +
        ':' + wm2.awayGoals + ' ' + normalizeTeam_(wm2.away, nameMap) +
        (wm2.ot ? ' [ОТ/буллиты]' : '')
      );
    }
    msg += '\n\nДИАГНОСТИКА (0 совпадений):' +
      '\n\nВсего найдено сыгранных матчей: ' + webMatches.length +
      '\nСамые свежие из них (первые 5):\n' + webMatchesSample.join('\n') +
      '\n\nЖдут результата в вашей таблице (первые 5 строк со статусом "Запланирован"):\n' +
      plannedRowsSample.join('\n');
  }

  notify_(msg);
}

/**
 * Пересчитывает Elo-рейтинг всех команд С НУЛЯ по всем сыгранным матчам сезона
 * (не накопительно — безопаснее, чем инкрементально обновлять, не задвоится
 * при повторном нажатии). Стартовая точка для каждой команды берётся из
 * столбца «Стартовый рейтинг» листа Справочник команд:
 *   Elo_старт = 1500 + (Стартовый_рейтинг - 50) * 6
 * Победа в овертайме/буллитах засчитывается как "неполная" (0.75 против 0.25
 * очка), а не как чистая победа — это стандартная практика в спортивных
 * Elo-моделях и честнее отражает, что игра была равной.
 *
 * Результат пишется в отдельный лист "Elo" (создаётся сам, если его нет).
 * silent=true — не показывать всплывающее окно (используется при автовызове
 * из updateResultsFromWeb); без аргумента — показывает окно (для отдельного
 * пункта меню «Пересчитать Elo-рейтинг»).
 */
function computeAndWriteElo_(silent) {
  var ss = SpreadsheetApp.getActive();
  var teamsSh = ss.getSheetByName(SHEET_TEAMS);
  var resultsSh = ss.getSheetByName(SHEET_RESULTS);

  if (!teamsSh) throw new Error('Не найден лист "' + SHEET_TEAMS + '"');
  if (!resultsSh) throw new Error('Не найден лист "' + SHEET_RESULTS + '"');

  // стартовые Elo из "Стартовый рейтинг" (1-100)
  var teamsData = teamsSh.getDataRange().getValues();
  var elo = {};
  var teamOrder = [];
  for (var i = 1; i < teamsData.length; i++) {
    var name = String(teamsData[i][0]).trim();
    var rawRating = teamsData[i][2];
    if (typeof rawRating === 'string' && /^\s*\d+([.,]\d+)?\s*$/.test(rawRating)) rawRating = Number(rawRating.replace(',', '.'));   // число, сохранённое как текст
    // строго требуем настоящее число в ячейке — пустая ячейка/текст (например,
    // случайно попавшая в этот столбец заметка) не должны считаться командой
    if (!name || typeof rawRating !== 'number') continue;
    var startRating = rawRating;
    elo[name] = ELO_BASE + (startRating - 50) * ELO_SCALE;
    teamOrder.push(name);
  }

  // все сыгранные матчи, по порядку дат
  var resData = resultsSh.getDataRange().getValues();
  var header = resData[0];
  var col = {
    date: header.indexOf('Дата'),
    status: header.indexOf('Статус'),
    home: header.indexOf('Хозяева'),
    away: header.indexOf('Гости'),
    homeGoals: header.indexOf('Г Хозяев'),
    awayGoals: header.indexOf('Г Гостей'),
    ot: header.indexOf('ОТ/буллиты?')
  };

  var games = [];
  for (var r = 1; r < resData.length; r++) {
    if (String(resData[r][col.status]).trim() !== 'Сыгран') continue;
    games.push({
      date: resData[r][col.date],
      home: String(resData[r][col.home]).trim(),
      away: String(resData[r][col.away]).trim(),
      hg: Number(resData[r][col.homeGoals]),
      ag: Number(resData[r][col.awayGoals]),
      ot: !!resData[r][col.ot]
    });
  }
  games.sort(function (a, b) {
    var da = (a.date instanceof Date) ? a.date.getTime() : 0;
    var db = (b.date instanceof Date) ? b.date.getTime() : 0;
    return da - db;
  });

  var gamesPlayed = {};
  var recentForm = {}; // команда -> массив "перфоманс минус ожидание" за последние (до FORM_WINDOW) игр
  for (var g = 0; g < games.length; g++) {
    var game = games[g];
    if (!(game.home in elo) || !(game.away in elo)) continue; // неизвестная команда — пропускаем

    var eloHome = elo[game.home];
    var eloAway = elo[game.away];
    var expectedHome = 1 / (1 + Math.pow(10, (eloAway - eloHome) / 400));

    var homeWon = game.hg > game.ag;
    var actualHome;
    if (game.ot) {
      actualHome = homeWon ? ELO_OT_CREDIT : (1 - ELO_OT_CREDIT);
    } else {
      actualHome = homeWon ? 1 : 0;
    }

    // Margin of victory: крупная победа над сильным соперником двигает рейтинг больше,
    // чем такая же победа над аутсайдером — как в модели Elo у FiveThirtyEight для NHL.
    // Применяем только к победам в основное время (в ОТ/буллитах разница всегда 1 шайба,
    // там уже своя логика через ELO_OT_CREDIT).
    var movFactor = 1;
    if (!game.ot) {
      var goalDiff = Math.abs(game.hg - game.ag);
      var eloDiffWinner = homeWon ? (eloHome - eloAway) : (eloAway - eloHome);
      var movMultiplier = Math.log(goalDiff) + 1; // 1 шайба разницы -> множитель 1 (как раньше)
      var dampen = 2.2 / (eloDiffWinner * 0.001 + 2.2); // крупная победа фаворита весит меньше, крупный апсет — больше
      movFactor = movMultiplier * dampen;
    }
    // скорость у каждой команды своя: в начале сезона рейтинг догоняет реальный уровень быстрее
    var kHome = eloTeamK_(gamesPlayed[game.home]) * movFactor;
    var kAway = eloTeamK_(gamesPlayed[game.away]) * movFactor;

    elo[game.home] = eloHome + kHome * (actualHome - expectedHome);
    elo[game.away] = eloAway + kAway * ((1 - actualHome) - (1 - expectedHome));

    gamesPlayed[game.home] = (gamesPlayed[game.home] || 0) + 1;
    gamesPlayed[game.away] = (gamesPlayed[game.away] || 0) + 1;

    // форма: не сырые очки, а "перфоманс минус ожидание" (то же delta, что и в Elo) —
    // так 8 побед подряд над аутсайдерами и 8 побед подряд над лидерами не выглядят одинаково
    var deltaHome = actualHome - expectedHome;
    if (!recentForm[game.home]) recentForm[game.home] = [];
    if (!recentForm[game.away]) recentForm[game.away] = [];
    recentForm[game.home].push(deltaHome);
    recentForm[game.away].push(-deltaHome);
    if (recentForm[game.home].length > FORM_WINDOW) recentForm[game.home].shift();
    if (recentForm[game.away].length > FORM_WINDOW) recentForm[game.away].shift();
  }

  // взвешенная форма: более свежая игра из окна весит больше (вес растёт к концу массива)
  var formAdj = {};
  teamOrder.forEach(function (name) {
    var deltas = recentForm[name] || [];
    if (deltas.length === 0) { formAdj[name] = 0; return; }
    var weightSum = 0, weighted = 0;
    for (var k = 0; k < deltas.length; k++) {
      var w = k + 1; // самая старая игра в окне весит 1, самая свежая — deltas.length
      weightSum += w;
      weighted += w * deltas[k];
    }
    var weightedDelta = weighted / weightSum; // примерно -1..+1, обычно куда уже (-0.4..+0.4)
    var adj = weightedDelta * FORM_SCALE;
    formAdj[name] = Math.max(-8, Math.min(8, Math.round(adj * 100) / 100));
  });

  // пишем результат в лист Elo (создаём при необходимости)
  var eloSh = ss.getSheetByName(SHEET_ELO);
  if (!eloSh) {
    eloSh = ss.insertSheet(SHEET_ELO);
  } else {
    eloSh.clearContents();
  }
  eloSh.getRange(1, 1, 1, 4).setValues([['Команда', 'Elo', 'Игр учтено', 'Поправка формы (посл. ' + FORM_WINDOW + ')']]);
  var rows = teamOrder.map(function (name) {
    return [name, Math.round(elo[name] * 10) / 10, gamesPlayed[name] || 0, formAdj[name] || 0];
  });
  eloSh.getRange(2, 1, rows.length, 4).setValues(rows);

  // Рейтинг силы (Data!T) — тот самый, по которому считаются все прогнозы, —
  // записываем напрямую числом из только что посчитанного Elo.
  // Раньше там стояла формула INDEX/MATCH по листу Elo с запасным вариантом
  // IFERROR(...; стартовый рейтинг), и она возвращала именно запасной вариант:
  // на момент аудита рейтинг силы у ВСЕХ 22 команд был в точности равен
  // предсезонному, то есть пересчитанный Elo до прогнозов не доходил вообще и
  // модель не училась на результатах сезона. Прямая запись убирает эту связку.
  var ratingsWritten = writeStrengthRatingToData_(teamOrder, elo);

  // сохраняем "снимок" Elo на сегодня в историю — для графика по ходу сезона
  appendEloHistorySnapshot_(teamOrder, elo);

  if (!silent) {
    uiAlert_('Elo-рейтинг пересчитан для ' + rows.length + ' команд по ' + games.length + ' матчам.\n' +
      'Рейтинг силы (Data!T) обновлён для ' + ratingsWritten + ' команд — теперь прогнозы считаются по фактическим ' +
      'результатам сезона, а не по предсезонным оценкам.');
  }
}

/**
 * Дописывает одну строку в лист "Elo_история" (создаёт при необходимости):
 * дата + текущий Elo каждой команды, по одной колонке на команду. Если на
 * сегодняшнюю дату снимок уже есть — перезаписывает его, а не плодит дубли
 * (так можно спокойно жать "Обновить результаты" несколько раз за день).
 */
function appendEloHistorySnapshot_(teamOrder, elo) {
  var ss = SpreadsheetApp.getActive();
  var histSh = ss.getSheetByName('Elo_история');
  if (!histSh) {
    histSh = ss.insertSheet('Elo_история');
    histSh.getRange(1, 1, 1, teamOrder.length + 1).setValues([['Дата'].concat(teamOrder)]);
  }

  var header = histSh.getRange(1, 1, 1, Math.max(1, histSh.getLastColumn())).getValues()[0];
  // заголовок от другой лиги (копия таблицы) — начать историю заново; новые команды — дописать столбцами
  var known = header.slice(1).filter(function (t) { return elo.hasOwnProperty(String(t)); }).length;
  if (known === 0) {
    histSh.clearContents();
    header = ['Дата'].concat(teamOrder);
    histSh.getRange(1, 1, 1, header.length).setValues([header]);
  } else {
    var missing = teamOrder.filter(function (t) { return header.indexOf(t) === -1; });
    if (missing.length) { histSh.getRange(1, header.length + 1, 1, missing.length).setValues([missing]); header = header.concat(missing); }
  }
  // на случай, если состав команд когда-нибудь изменится — сверяем по заголовку, а не по teamOrder напрямую
  var todayStr = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');

  var lastRow = histSh.getLastRow();
  var todayRowIndex = -1;
  if (lastRow > 1) {
    var dates = histSh.getRange(2, 1, lastRow - 1, 1).getValues();
    for (var i = 0; i < dates.length; i++) {
      var d = dates[i][0];
      var dStr = (d instanceof Date) ? Utilities.formatDate(d, Session.getScriptTimeZone(), 'yyyy-MM-dd') : '';
      if (dStr === todayStr) { todayRowIndex = i + 2; break; }
    }
  }

  var rowValues = [new Date()];
  for (var c = 1; c < header.length; c++) {
    var teamName = header[c];
    rowValues.push(Math.round((elo[teamName] || 0) * 10) / 10);
  }

  var targetRow = (todayRowIndex !== -1) ? todayRowIndex : histSh.getLastRow() + 1;
  histSh.getRange(targetRow, 1, 1, rowValues.length).setValues([rowValues]);
}

/**
 * Строит линейный график Elo-рейтинга всех команд по ходу сезона на основе
 * листа "Elo_история" (заполняется автоматически при каждом пересчёте Elo).
 * Если истории накопилось меньше 2 дат — график будет плоским, это нормально,
 * просто пока рано смотреть на тренд, наберите больше снимков.
 */
function createEloChart_() {
  var ss = SpreadsheetApp.getActive();
  var histSh = ss.getSheetByName('Elo_история');
  if (!histSh || histSh.getLastRow() < 2) {
    uiAlert_(
      'Пока нет истории Elo для графика. Нажмите "Обновить результаты" или "Пересчитать Elo-рейтинг" ' +
      'хотя бы один раз (а лучше — в разные дни, чтобы накопился тренд), потом повторите.'
    );
    return;
  }

  // удаляем старый график с этим же именем, если уже строили раньше — чтобы не плодить дубли
  var charts = histSh.getCharts();
  for (var i = 0; i < charts.length; i++) {
    histSh.removeChart(charts[i]);
  }

  var range = histSh.getRange(1, 1, histSh.getLastRow(), histSh.getLastColumn());
  var chart = histSh.newChart()
    .setChartType(Charts.ChartType.LINE)
    .addRange(range)
    .setTransposeRowsAndColumns(false)
    .setNumHeaders(1)
    .setOption('title', 'Elo-рейтинг команд по ходу сезона 2026/27')
    .setOption('width', 1000)
    .setOption('height', 600)
    .setOption('legend', { position: 'right' })
    .setPosition(2, histSh.getLastColumn() + 2, 0, 0)
    .build();

  histSh.insertChart(chart);
  uiAlert_('Готово: график добавлен на лист "Elo_история", справа от таблицы.');
}

/**
 * Полностью пересчитывает историю очков команд по датам ТЕКУЩЕГО сезона —
 * в отличие от Elo (где снимок копится по одному при каждом нажатии кнопки),
 * здесь можно сразу восстановить всю историю за уже сыгранные дни, потому
 * что даты и результаты всех игр у нас уже есть. Пишет в лист
 * "Таблица_история" (одна строка на игровой день, одна колонка на команду,
 * значение — очки нарастающим итогом) и сразу строит график.
 * Можно запускать повторно — лист каждый раз перестраивается с нуля.
 */
function computeStandingsHistory_() {
  var ss = SpreadsheetApp.getActive();
  var teamsSh = ss.getSheetByName(SHEET_TEAMS);
  var resultsSh = ss.getSheetByName(SHEET_RESULTS);
  if (!teamsSh || !resultsSh) {
    uiAlert_('Не найден лист "' + SHEET_TEAMS + '" или "' + SHEET_RESULTS + '".');
    return;
  }

  var teamsData = teamsSh.getDataRange().getValues();
  var teamOrder = [];
  for (var i = 1; i < teamsData.length; i++) {
    var name = String(teamsData[i][0]).trim();
    if (name && typeof teamsData[i][2] === 'number') teamOrder.push(name);
  }

  var resData = resultsSh.getDataRange().getValues();
  var header = resData[0];
  var col = {
    date: header.indexOf('Дата'), status: header.indexOf('Статус'),
    home: header.indexOf('Хозяева'), away: header.indexOf('Гости'),
    homeGoals: header.indexOf('Г Хозяев'), awayGoals: header.indexOf('Г Гостей'),
    ot: header.indexOf('ОТ/буллиты?')
  };

  var games = [];
  for (var r = 1; r < resData.length; r++) {
    if (String(resData[r][col.status]).trim() !== 'Сыгран') continue;
    var d = resData[r][col.date];
    if (!(d instanceof Date)) continue;
    games.push({
      date: d, home: String(resData[r][col.home]).trim(), away: String(resData[r][col.away]).trim(),
      hg: Number(resData[r][col.homeGoals]), ag: Number(resData[r][col.awayGoals]), ot: !!resData[r][col.ot]
    });
  }
  if (games.length === 0) {
    uiAlert_('Сыгранных матчей пока нет — история таблицы появится после первого тура.');
    return;
  }
  games.sort(function (a, b) { return a.date.getTime() - b.date.getTime(); });

  var points = {};
  teamOrder.forEach(function (t) { points[t] = 0; });

  var snapshots = []; // {dateStr, points: {...}}
  var currentDateKey = null;
  var tz = Session.getScriptTimeZone();

  for (var g = 0; g < games.length; g++) {
    var game = games[g];
    if (!(game.home in points) || !(game.away in points)) continue;
    var dateKey = Utilities.formatDate(game.date, tz, 'yyyy-MM-dd');

    if (currentDateKey !== null && dateKey !== currentDateKey) {
      snapshots.push({ dateKey: currentDateKey, points: Object.assign({}, points) });
    }
    currentDateKey = dateKey;

    var homeWon = game.hg > game.ag;
    points[game.home] += homeWon ? 2 : (game.ot ? 1 : 0);
    points[game.away] += !homeWon ? 2 : (game.ot ? 1 : 0);
  }
  if (currentDateKey !== null) {
    snapshots.push({ dateKey: currentDateKey, points: Object.assign({}, points) });
  }

  var histSh = ss.getSheetByName('Таблица_история');
  if (!histSh) {
    histSh = ss.insertSheet('Таблица_история');
  } else {
    histSh.clearContents();
    var oldCharts = histSh.getCharts();
    for (var ci = 0; ci < oldCharts.length; ci++) histSh.removeChart(oldCharts[ci]);
  }

  var headerRow = ['Дата'].concat(teamOrder);
  var outRows = [headerRow];
  snapshots.forEach(function (snap) {
    var row = [snap.dateKey];
    teamOrder.forEach(function (t) { row.push(snap.points[t]); });
    outRows.push(row);
  });
  histSh.getRange(1, 1, outRows.length, headerRow.length).setValues(outRows);
  histSh.getRange(2, 1, outRows.length - 1, 1).setNumberFormat('yyyy-mm-dd');

  var range = histSh.getRange(1, 1, outRows.length, headerRow.length);
  var chart = histSh.newChart()
    .setChartType(Charts.ChartType.LINE)
    .addRange(range)
    .setNumHeaders(1)
    .setOption('title', 'Очки команд по ходу сезона 2026/27 (чем выше линия — тем выше место в таблице)')
    .setOption('width', 1000)
    .setOption('height', 600)
    .setOption('legend', { position: 'right' })
    .setPosition(2, headerRow.length + 2, 0, 0)
    .build();
  histSh.insertChart(chart);

  uiAlert_(
    'Готово: история турнирной таблицы (' + (outRows.length - 1) + ' игровых дней) и график ' +
    'на листе "Таблица_история". Чем выше линия команды на графике — тем выше её место в таблице на ту дату.'
  );
}

/**
 * Одноразовая настройка: добавляет в лист "прогнозы" три новых столбца
 * (N: всего личных встреч, O: побед сегодняшних хозяев в них, P: сама
 * поправка к рейтингу) и вписывает поправку в формулу шансов хозяев (D).
 * Можно запускать повторно — просто перезапишет те же формулы, ничего не
 * задвоится. Учитывает встречи из ТЕКУЩЕГО сезона и листа "Результаты 2025-26".
 * Пишет через Apps Script, поэтому синтаксис формул (запятые/точки) всегда
 * стандартный — Google Таблицы сами покажут его в формате вашей локали.
 */
function setupH2HFormulas_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }

  // сколько строк матчей реально заполнено (по столбцу B — Хозяева)
  var colB = sh.getRange(2, 2, sh.getMaxRows() - 1, 1).getValues();
  var lastRow = 1;
  for (var i = 0; i < colB.length; i++) {
    if (String(colB[i][0]).trim() !== '') lastRow = i + 2;
  }
  if (lastRow < 2) {
    uiAlert_('На листе "прогнозы" не найдено ни одной строки с матчем в столбце B.');
    return;
  }
  var numRows = lastRow - 1;

  // заголовки
  sh.getRange('N1').setValue('Личных встреч, взвеш.');
  sh.getRange('O1').setValue('Побед Хозяев, взвеш.');
  sh.getRange('P1').setValue('H2H поправка');

  // формулы в строке 2 (эта таблица требует точку с запятой как разделитель
  // аргументов даже при записи через Apps Script — проверено эмпирически)
  // Затухание по времени: каждая встреча взвешена EXP(-ln2/365*(сегодня-дата)) —
  // встреча "сегодня" весит 1, встреча год назад — примерно 0.5, две — 0.25 и т.д.
  // Так более свежая игра значит больше, чем игра из прошлого сезона.
  var decayRM = 'EXP(-LN(2)/365*(TODAY()-\'результаты матчей\'!$A$2:$A$1600))';
  var decayH25 = 'EXP(-LN(2)/365*(TODAY()-\'Результаты 2025-26\'!$A$2:$A$1400))';

  var formulaN =
    '=SUMPRODUCT((\'результаты матчей\'!$B$2:$B$1600="Сыгран")*(' +
      '((\'результаты матчей\'!$C$2:$C$1600=$B2)*(\'результаты матчей\'!$D$2:$D$1600=$C2))' +
      '+((\'результаты матчей\'!$C$2:$C$1600=$C2)*(\'результаты матчей\'!$D$2:$D$1600=$B2))' +
    ')*' + decayRM + ')' +
    '+SUMPRODUCT((' +
      '((\'Результаты 2025-26\'!$C$2:$C$1400=$B2)*(\'Результаты 2025-26\'!$D$2:$D$1400=$C2))' +
      '+((\'Результаты 2025-26\'!$C$2:$C$1400=$C2)*(\'Результаты 2025-26\'!$D$2:$D$1400=$B2))' +
    ')*' + decayH25 + ')';

  var formulaO =
    '=SUMPRODUCT((\'результаты матчей\'!$B$2:$B$1600="Сыгран")*(\'результаты матчей\'!$C$2:$C$1600=$B2)*(\'результаты матчей\'!$D$2:$D$1600=$C2)*(\'результаты матчей\'!$E$2:$E$1600>\'результаты матчей\'!$F$2:$F$1600)*' + decayRM + ')' +
    '+SUMPRODUCT((\'результаты матчей\'!$B$2:$B$1600="Сыгран")*(\'результаты матчей\'!$C$2:$C$1600=$C2)*(\'результаты матчей\'!$D$2:$D$1600=$B2)*(\'результаты матчей\'!$F$2:$F$1600>\'результаты матчей\'!$E$2:$E$1600)*' + decayRM + ')' +
    '+SUMPRODUCT((\'Результаты 2025-26\'!$C$2:$C$1400=$B2)*(\'Результаты 2025-26\'!$D$2:$D$1400=$C2)*(\'Результаты 2025-26\'!$E$2:$E$1400>\'Результаты 2025-26\'!$F$2:$F$1400)*' + decayH25 + ')' +
    '+SUMPRODUCT((\'Результаты 2025-26\'!$C$2:$C$1400=$C2)*(\'Результаты 2025-26\'!$D$2:$D$1400=$B2)*(\'Результаты 2025-26\'!$F$2:$F$1400>\'Результаты 2025-26\'!$E$2:$E$1400)*' + decayH25 + ')';

  var formulaP = '=IF(N2=0;0;(2*O2-N2)/N2*16*MIN(1;N2/6))';

  sh.getRange('N2').setFormula(formulaN);
  sh.getRange('O2').setFormula(formulaO);
  sh.getRange('P2').setFormula(formulaP);

  // формула шансов хозяев (столбец D) целиком — известна заранее, поэтому просто
  // задаём её напрямую, а не пытаемся текстово подменить кусок старой формулы
  // (так надёжнее и безопасно при повторном запуске). Точка с запятой — по той
  // же причине, что и выше.
  var formulaD =
    '=IF(OR(B2="";C2="");"";ROUND(1/(1+10^(-((INDEX(Data!$T$2:$T$33;MATCH(B2;Data!$A$2:$A$33;0)))+$M$2+P2-(INDEX(Data!$T$2:$T$33;MATCH(C2;Data!$A$2:$A$33;0))))/$M$3));4))';
  // формула шансов ставится централизованно, только в несыгранные строки

  // копируем строку 2 (N,O,P и D) вниз до последней заполненной строки матчей
  if (numRows > 1) {
    sh.getRange('N2:P2').copyTo(sh.getRange(3, 14, numRows - 1, 3));
    applyProbabilityFormula_(sh);
  }

  uiAlert_('Готово: формулы H2H расставлены для ' + numRows + ' строк (со 2 по ' + lastRow + ').');
}

/**
 * Одноразовая настройка: добавляет в лист "прогнозы" четыре служебных столбца
 * (Q: игр дома, R: очков дома, S: игр в гостях, T: очков в гостях — по обеим
 * сезонам) и итоговый столбец U — персональный бонус команды за своё поле
 * вместо единого $M$2 для всех. Формула U даёт (среднее очков за домашнюю
 * игру минус среднее очков за гостевую игру) * 6, в шкале рейтинга силы, с
 * лёгким ограничением диапазона на случай нетипичных выбросов; если данных
 * по какой-то причине нет — подстраховкой остаётся старое значение $M$2.
 * Затем подключает U вместо $M$2 в формулу шансов хозяев (столбец D).
 * Можно запускать повторно.
 */
function setupHomeAwayFormulas_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }

  var colB = sh.getRange(2, 2, sh.getMaxRows() - 1, 1).getValues();
  var lastRow = 1;
  for (var i = 0; i < colB.length; i++) {
    if (String(colB[i][0]).trim() !== '') lastRow = i + 2;
  }
  if (lastRow < 2) {
    uiAlert_('На листе "прогнозы" не найдено ни одной строки с матчем в столбце B.');
    return;
  }
  var numRows = lastRow - 1;

  sh.getRange('Q1').setValue('Игр дома (оба сезона)');
  sh.getRange('R1').setValue('Очков дома, всего');
  sh.getRange('S1').setValue('Игр в гостях (оба сезона)');
  sh.getRange('T1').setValue('Очков в гостях, всего');
  sh.getRange('U1').setValue('Дом. бонус (персональный)');

  var formulaQ =
    '=SUMPRODUCT((\'результаты матчей\'!$B$2:$B$1600="Сыгран")*(\'результаты матчей\'!$C$2:$C$1600=$B2))' +
    '+SUMPRODUCT((\'Результаты 2025-26\'!$C$2:$C$1400=$B2)*1)';

  var formulaR =
    '=SUMPRODUCT((\'результаты матчей\'!$B$2:$B$1600="Сыгран")*(\'результаты матчей\'!$C$2:$C$1600=$B2)*(\'результаты матчей\'!$I$2:$I$1600))' +
    '+SUMPRODUCT((\'Результаты 2025-26\'!$C$2:$C$1400=$B2)*(\'Результаты 2025-26\'!$I$2:$I$1400))';

  var formulaS =
    '=SUMPRODUCT((\'результаты матчей\'!$B$2:$B$1600="Сыгран")*(\'результаты матчей\'!$D$2:$D$1600=$B2))' +
    '+SUMPRODUCT((\'Результаты 2025-26\'!$D$2:$D$1400=$B2)*1)';

  var formulaT =
    '=SUMPRODUCT((\'результаты матчей\'!$B$2:$B$1600="Сыгран")*(\'результаты матчей\'!$D$2:$D$1600=$B2)*(\'результаты матчей\'!$J$2:$J$1600))' +
    '+SUMPRODUCT((\'Результаты 2025-26\'!$D$2:$D$1400=$B2)*(\'Результаты 2025-26\'!$J$2:$J$1400))';

  var formulaU = '=IF(OR(Q2=0;S2=0);$M$2;MAX(-3;MIN(9;(R2/Q2-T2/S2)*6)))';

  sh.getRange('Q2').setFormula(formulaQ);
  sh.getRange('R2').setFormula(formulaR);
  sh.getRange('S2').setFormula(formulaS);
  sh.getRange('T2').setFormula(formulaT);
  sh.getRange('U2').setFormula(formulaU);

  // формула шансов хозяев (столбец D) целиком — теперь с персональным U2 вместо $M$2
  var formulaD =
    '=IF(OR(B2="";C2="");"";ROUND(1/(1+10^(-((INDEX(Data!$T$2:$T$33;MATCH(B2;Data!$A$2:$A$33;0)))+U2+P2-(INDEX(Data!$T$2:$T$33;MATCH(C2;Data!$A$2:$A$33;0))))/$M$3));4))';
  // формула шансов хозяев ставится централизованно, только в несыгранные строки
  // (см. applyProbabilityFormula_ в пакете исправлений — это защищает заморозку)

  if (numRows > 1) {
    sh.getRange('Q2:U2').copyTo(sh.getRange(3, 17, numRows - 1, 5));
    applyProbabilityFormula_(sh);
  }

  uiAlert_('Готово: персональный дом/гостевой бонус расставлен для ' + numRows + ' строк (со 2 по ' + lastRow + ').');
}

/**
 * Одноразовая настройка: добавляет в лист "прогнозы" столбцы усталости по
 * календарю (V-AB) и подключает итоговую поправку к формуле шансов хозяев.
 * Дата предыдущей игры команды берётся из полного расписания (результаты
 * матчей), независимо от статуса "Сыгран"/"Запланирован" — само расписание
 * фиксировано заранее, так что календарная плотность известна вперёд.
 * 0 дней отдыха (игра на следующий день) — минус 6 очков рейтинга,
 * 1 день — минус 3, 2 и больше — поправка обнуляется (команда отдохнула).
 * Можно запускать повторно.
 */
function setupFatigueFormulas_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }

  var colB = sh.getRange(2, 2, sh.getMaxRows() - 1, 1).getValues();
  var lastRow = 1;
  for (var i = 0; i < colB.length; i++) {
    if (String(colB[i][0]).trim() !== '') lastRow = i + 2;
  }
  if (lastRow < 2) {
    uiAlert_('На листе "прогнозы" не найдено ни одной строки с матчем в столбце B.');
    return;
  }
  var numRows = lastRow - 1;

  sh.getRange('V1').setValue('Пред. игра Хозяев');
  sh.getRange('W1').setValue('Отдых Хозяев, дней');
  sh.getRange('X1').setValue('Устал. поправка Хозяев');
  sh.getRange('Y1').setValue('Пред. игра Гостей');
  sh.getRange('Z1').setValue('Отдых Гостей, дней');
  sh.getRange('AA1').setValue('Устал. поправка Гостей');
  sh.getRange('AB1').setValue('Итог. поправка усталости (Х-Г)');

  var formulaV =
    '=MAX(' +
      'MAXIFS(\'результаты матчей\'!$A$2:$A$1600;\'результаты матчей\'!$C$2:$C$1600;$B2;\'результаты матчей\'!$A$2:$A$1600;"<"&$A2);' +
      'MAXIFS(\'результаты матчей\'!$A$2:$A$1600;\'результаты матчей\'!$D$2:$D$1600;$B2;\'результаты матчей\'!$A$2:$A$1600;"<"&$A2)' +
    ')';
  var formulaW = '=IF(V2=0;7;$A2-V2)';
  var formulaX = '=MIN(0;MAX(-6;(W2-2)*3))';

  var formulaY =
    '=MAX(' +
      'MAXIFS(\'результаты матчей\'!$A$2:$A$1600;\'результаты матчей\'!$C$2:$C$1600;$C2;\'результаты матчей\'!$A$2:$A$1600;"<"&$A2);' +
      'MAXIFS(\'результаты матчей\'!$A$2:$A$1600;\'результаты матчей\'!$D$2:$D$1600;$C2;\'результаты матчей\'!$A$2:$A$1600;"<"&$A2)' +
    ')';
  var formulaZ = '=IF(Y2=0;7;$A2-Y2)';
  var formulaAA = '=MIN(0;MAX(-6;(Z2-2)*3))';
  var formulaAB = '=X2-AA2';

  sh.getRange('V2').setFormula(formulaV);
  sh.getRange('W2').setFormula(formulaW);
  sh.getRange('X2').setFormula(formulaX);
  sh.getRange('Y2').setFormula(formulaY);
  sh.getRange('Z2').setFormula(formulaZ);
  sh.getRange('AA2').setFormula(formulaAA);
  sh.getRange('AB2').setFormula(formulaAB);

  // явный формат ячеек: V/Y — как дата, остальное — как обычное число.
  // Без этого Таблицы иногда наследуют формат "дата" от соседних ячеек и
  // показывают, например, "3 дня отдыха" как "03.01.1900" — значение при
  // этом верное, просто отображается некорректно.
  sh.getRange(2, 22, 1, 1).setNumberFormat('dd.mm.yyyy');       // V
  sh.getRange(2, 23, 1, 2).setNumberFormat('0.##');             // W, X
  sh.getRange(2, 25, 1, 1).setNumberFormat('dd.mm.yyyy');       // Y
  sh.getRange(2, 26, 1, 3).setNumberFormat('0.##');             // Z, AA, AB

  // формула шансов хозяев (столбец D) целиком — теперь ещё и с поправкой на усталость (AB2)
  var formulaD =
    '=IF(OR(B2="";C2="");"";ROUND(1/(1+10^(-((INDEX(Data!$T$2:$T$33;MATCH(B2;Data!$A$2:$A$33;0)))+U2+P2+AB2-(INDEX(Data!$T$2:$T$33;MATCH(C2;Data!$A$2:$A$33;0))))/$M$3));4))';
  // формула шансов хозяев ставится централизованно, только в несыгранные строки
  // (см. applyProbabilityFormula_ в пакете исправлений — это защищает заморозку)

  if (numRows > 1) {
    sh.getRange('V2:AB2').copyTo(sh.getRange(3, 22, numRows - 1, 7));
    applyProbabilityFormula_(sh);
  }

  uiAlert_('Готово: поправка на усталость расставлена для ' + numRows + ' строк (со 2 по ' + lastRow + ').');
}

/**
 * Одноразовая настройка: добавляет в лист "прогнозы" столбец AC — поправку
 * за текущую форму (последние 8 игр ТЕКУЩЕГО сезона, свежие игры весят
 * больше) — и подключает её к формуле шансов хозяев. Сама поправка на
 * команду считается в computeAndWriteElo_ и лежит в листе Elo, здесь только
 * подтягивается разница между хозяевами и гостями.
 * Нажмите "Пересчитать Elo-рейтинг" один раз перед этим, если ещё не делали
 * этого в текущей сессии — иначе столбец формы в листе Elo может быть пуст.
 * Можно запускать повторно.
 */
function setupFormFormulas_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }
  if (!ss.getSheetByName(SHEET_ELO)) {
    uiAlert_('Не найден лист "' + SHEET_ELO + '". Сначала нажмите "Пересчитать Elo-рейтинг".');
    return;
  }

  var colB = sh.getRange(2, 2, sh.getMaxRows() - 1, 1).getValues();
  var lastRow = 1;
  for (var i = 0; i < colB.length; i++) {
    if (String(colB[i][0]).trim() !== '') lastRow = i + 2;
  }
  if (lastRow < 2) {
    uiAlert_('На листе "прогнозы" не найдено ни одной строки с матчем в столбце B.');
    return;
  }
  var numRows = lastRow - 1;

  sh.getRange('AC1').setValue('Поправка формы (Х-Г)');
  var formulaAC =
    '=IFERROR(INDEX(Elo!$D$2:$D$33;MATCH($B2;Elo!$A$2:$A$33;0));0)' +
    '-IFERROR(INDEX(Elo!$D$2:$D$33;MATCH($C2;Elo!$A$2:$A$33;0));0)';
  sh.getRange('AC2').setFormula(formulaAC);
  sh.getRange(2, 29, 1, 1).setNumberFormat('0.##'); // AC

  // формула шансов хозяев (столбец D) целиком — теперь ещё и с поправкой на форму (AC2),
  // плюс жёсткий пол/потолок 8%/92% как подстраховка от переуверенности модели
  var formulaD =
    '=IF(OR(B2="";C2="");"";ROUND(MAX(8/100;MIN(92/100;1/(1+10^(-((INDEX(Data!$T$2:$T$33;MATCH(B2;Data!$A$2:$A$33;0)))+U2+P2+AB2+AC2-(INDEX(Data!$T$2:$T$33;MATCH(C2;Data!$A$2:$A$33;0))))/$M$3))));4))';
  // формула шансов хозяев ставится централизованно, только в несыгранные строки
  // (см. applyProbabilityFormula_ в пакете исправлений — это защищает заморозку)

  if (numRows > 1) {
    sh.getRange('AC2').copyTo(sh.getRange(3, 29, numRows - 1, 1));
    applyProbabilityFormula_(sh);
  }

  uiAlert_('Готово: поправка формы расставлена для ' + numRows + ' строк (со 2 по ' + lastRow + '). Теперь формула шансов хозяев учитывает все пять факторов: Elo, очные встречи, дом/гости, усталость и текущую форму.');
}

/**
 * Одноразовая настройка: добавляет столбец AD "Прогноз сбылся?" на лист
 * "прогнозы" — для уже сыгранных матчей сравнивает предсказанного победителя
 * (кто из B2/C2 имел больший % шансов) с реальным победителем из листа
 * "результаты матчей" и ставит ✅ или ❌. Для ещё не сыгранных матчей ячейка
 * остаётся пустой. Столбец добавлен в конец (после всех служебных столбцов
 * H2H/дом-гостей/усталости/формы), а не физически между F и G — так и
 * безопаснее (не сдвигает буквы столбцов, на которые ссылаются остальные
 * формулы), и его всё равно можно потом перетащить куда угодно вручную.
 * Можно запускать повторно.
 */
function setupResultCheckFormulas_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }

  var colB = sh.getRange(2, 2, sh.getMaxRows() - 1, 1).getValues();
  var lastRow = 1;
  for (var i = 0; i < colB.length; i++) {
    if (String(colB[i][0]).trim() !== '') lastRow = i + 2;
  }
  if (lastRow < 2) {
    uiAlert_('На листе "прогнозы" не найдено ни одной строки с матчем в столбце B.');
    return;
  }
  var numRows = lastRow - 1;

  // если раньше запускали эту функцию и она писала в AD — очищаем, чтобы не было дублей
  sh.getRange(1, 30, lastRow, 1).clearContent();

  sh.getRange('K1').setValue('Прогноз сбылся?');

  var formulaAD =
    '=IF(OR($B2="";$C2="");"";' +
      'IF(' +
        'IFERROR(INDEX(\'результаты матчей\'!$B$2:$B$1600;MATCH(1;(\'результаты матчей\'!$A$2:$A$1600=$A2)*(\'результаты матчей\'!$C$2:$C$1600=$B2)*(\'результаты матчей\'!$D$2:$D$1600=$C2);0));"")<>"Сыгран";' +
        '"";' +
        'IF(' +
          'LEFT(' +
            'IFERROR(INDEX(\'результаты матчей\'!$H$2:$H$1600;MATCH(1;(\'результаты матчей\'!$A$2:$A$1600=$A2)*(\'результаты матчей\'!$C$2:$C$1600=$B2)*(\'результаты матчей\'!$D$2:$D$1600=$C2);0));"");' +
            'LEN(IF($D2>$E2;$B2;$C2))' +
          ')=IF($D2>$E2;$B2;$C2);' +
          '"\u2705";"\u274c"' +
        ')' +
      ')' +
    ')';

  sh.getRange('K2').setFormula(formulaAD);

  if (numRows > 1) {
    sh.getRange('K2').copyTo(sh.getRange(3, 11, numRows - 1, 1));
  }

  uiAlert_(
    'Готово: столбец "Прогноз сбылся?" в K для ' + numRows + ' строк. ' +
    'Для уже сыгранных матчей появится ✅ или ❌, для ещё не сыгранных — пусто.'
  );
}

/**
 * Считает точность прогнозов по столбцу K листа "прогнозы" (✅/❌) и пишет
 * сводку в отдельный лист "Точность" — отдельно общую точность и отдельно
 * точность только на явных фаворитах (>60% по нашей модели), чтобы видеть,
 * не завышена ли уверенность модели именно там, где она увереннее всего.
 */
function showAccuracySummary_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }

  var data = sh.getRange(2, 1, sh.getLastRow() - 1, 11).getValues(); // A..K
  // столбец AD — метка честности прогноза (ставит fixDataLeak_). Матчи, помеченные
  // «нет», были испорчены утечкой: их прогноз пересчитался уже после результата,
  // поэтому в статистику они не идут — иначе точность выходит завышенной.
  var integrity = sh.getRange(2, COL_INTEGRITY, sh.getLastRow() - 1, 1).getValues();
  var resolved = []; // все сыгранные матчи с ЧЕСТНЫМ прогнозом, в хронологическом порядке
  var excludedContaminated = 0;

  for (var i = 0; i < data.length; i++) {
    var row = data[i];
    var date = row[0], home = row[1], away = row[2], d = row[3], e = row[4], predTotal = row[8], mark = row[10]; // A,B,C,D,E,I,K
    if (mark !== '✅' && mark !== '❌') continue; // ещё не сыграно или пусто
    if (String(integrity[i][0]).trim() === 'нет') { excludedContaminated++; continue; }
    var dNum = Number(d) || 0, eNum = Number(e) || 0;
    var isCorrect = (mark === '✅');
    var favProb = Math.max(dNum, eNum);
    var homeWasFavorite = dNum >= eNum;
    var homeActuallyWon = isCorrect ? homeWasFavorite : !homeWasFavorite;
    var actualHome = homeActuallyWon ? 1 : 0;
    resolved.push({
      date: date, dateKey: dateOnlyKey_(date), correct: isCorrect,
      favProb: favProb, brierTerm: Math.pow(dNum - actualHome, 2),
      home: String(home).trim(), away: String(away).trim(), homeWon: homeActuallyWon,
      predTotal: Number(predTotal) || null
    });
  }
  resolved.sort(function (a, b) { return a.dateKey < b.dateKey ? -1 : (a.dateKey > b.dateKey ? 1 : 0); });

  // подтягиваем фактический тотал (Г Хозяев + Г Гостей) для каждого сыгранного матча —
  // строим индекс по результаты матчей один раз, а не ищем построчно
  var resultsSh = ss.getSheetByName(SHEET_RESULTS);
  var actualTotalByKey = {};
  if (resultsSh) {
    var resData2 = resultsSh.getDataRange().getValues();
    var resHeader = resData2[0];
    var rCol = {
      date: resHeader.indexOf('Дата'), home: resHeader.indexOf('Хозяева'), away: resHeader.indexOf('Гости'),
      hg: resHeader.indexOf('Г Хозяев'), ag: resHeader.indexOf('Г Гостей')
    };
    for (var rr = 1; rr < resData2.length; rr++) {
      var rHome = String(resData2[rr][rCol.home]).trim(), rAway = String(resData2[rr][rCol.away]).trim();
      if (!rHome || !rAway) continue;
      var rKey = dateOnlyKey_(resData2[rr][rCol.date]) + '|' + rHome + '|' + rAway;
      var hg2 = Number(resData2[rr][rCol.hg]), ag2 = Number(resData2[rr][rCol.ag]);
      if (!isNaN(hg2) && !isNaN(ag2)) actualTotalByKey[rKey] = hg2 + ag2;
    }
  }
  resolved.forEach(function (r) {
    var key = r.dateKey + '|' + r.home + '|' + r.away;
    r.actualTotal = actualTotalByKey.hasOwnProperty(key) ? actualTotalByKey[key] : null;
  });

  var total = resolved.length;
  var correct = resolved.filter(function (r) { return r.correct; }).length;
  var brierSum = resolved.reduce(function (s, r) { return s + r.brierTerm; }, 0);
  var brier = total === 0 ? null : Math.round((brierSum / total) * 1000) / 1000;

  var pct = function (n, d) { return d === 0 ? '' : Math.round(1000 * n / d) / 10 + '%'; };

  // --- скользящий Brier score за последние 10 и 20 матчей ---
  var rollingBrier = function (n) {
    if (total === 0) return null;
    var slice = resolved.slice(Math.max(0, total - n));
    var sum = slice.reduce(function (s, r) { return s + r.brierTerm; }, 0);
    return Math.round((sum / slice.length) * 1000) / 1000;
  };
  var brier10 = rollingBrier(10), brier20 = rollingBrier(20);

  // --- разбивка фаворит (>=60%) / андердог (<60%) ---
  var favBucket = resolved.filter(function (r) { return r.favProb >= 0.6; });
  var dogBucket = resolved.filter(function (r) { return r.favProb < 0.6; });
  var favCorrect = favBucket.filter(function (r) { return r.correct; }).length;
  var dogCorrect = dogBucket.filter(function (r) { return r.correct; }).length;

  // --- калибровочная таблица по узким бакетам уверенности ---
  var buckets = [
    { label: '50-60%', min: 0.5, max: 0.6 },
    { label: '60-70%', min: 0.6, max: 0.7 },
    { label: '70-80%', min: 0.7, max: 0.8 },
    { label: '80-90%', min: 0.8, max: 0.9 },
    { label: '90%+', min: 0.9, max: 1.01 }
  ];
  var calibRows = buckets.map(function (b) {
    var inBucket = resolved.filter(function (r) { return r.favProb >= b.min && r.favProb < b.max; });
    var bucketCorrect = inBucket.filter(function (r) { return r.correct; }).length;
    var avgConfidence = inBucket.length > 0
      ? Math.round(inBucket.reduce(function (s, r) { return s + r.favProb; }, 0) / inBucket.length * 1000) / 10
      : null;
    return [
      b.label, inBucket.length, bucketCorrect,
      inBucket.length > 0 ? pct(bucketCorrect, inBucket.length) : '',
      avgConfidence !== null ? avgConfidence + '%' : ''
    ];
  });

  // --- калибровка тоталов: только матчи, где нашёлся и прогноз, и факт ---
  var totalsResolved = resolved.filter(function (r) { return r.predTotal !== null && r.actualTotal !== null; });
  var totalsCount = totalsResolved.length;
  var avgAbsError = totalsCount > 0
    ? Math.round(totalsResolved.reduce(function (s, r) { return s + Math.abs(r.predTotal - r.actualTotal); }, 0) / totalsCount * 100) / 100
    : null;
  var totalsLineHits = totalsResolved.filter(function (r) {
    var predSide = r.predTotal >= COUPON_TOTAL_LINE ? 'over' : 'under';
    var actualSide = r.actualTotal >= COUPON_TOTAL_LINE ? 'over' : 'under';
    return predSide === actualSide;
  }).length;

  // бакеты по прогнозируемому тоталу (не по вероятности, а по самому числу голов)
  var totalBuckets = [
    { label: '< 4.5', min: -Infinity, max: 4.5 },
    { label: '4.5 - 5.5', min: 4.5, max: 5.5 },
    { label: '5.5 - 6.5', min: 5.5, max: 6.5 },
    { label: '> 6.5', min: 6.5, max: Infinity }
  ];
  var totalCalibRows = totalBuckets.map(function (b) {
    var inBucket = totalsResolved.filter(function (r) { return r.predTotal >= b.min && r.predTotal < b.max; });
    if (inBucket.length === 0) return [b.label, 0, '', ''];
    var bucketAvgError = Math.round(inBucket.reduce(function (s, r) { return s + Math.abs(r.predTotal - r.actualTotal); }, 0) / inBucket.length * 100) / 100;
    var bucketAvgActual = Math.round(inBucket.reduce(function (s, r) { return s + r.actualTotal; }, 0) / inBucket.length * 100) / 100;
    return [b.label, inBucket.length, bucketAvgActual, bucketAvgError];
  });

  // --- точность по каждой команде отдельно (и как хозяева, и как гости — вместе) ---
  var teamStats = {};
  resolved.forEach(function (r) {
    [r.home, r.away].forEach(function (team) {
      if (!teamStats[team]) teamStats[team] = { total: 0, correct: 0 };
      teamStats[team].total++;
      if (r.correct) teamStats[team].correct++;
    });
  });
  var teamRows = Object.keys(teamStats)
    .map(function (t) { return [t, teamStats[t].total, teamStats[t].correct, pct(teamStats[t].correct, teamStats[t].total)]; })
    .sort(function (a, b) { return b[1] - a[1]; }); // по числу матчей, по убыванию

  var accSh = ss.getSheetByName('Точность');
  if (!accSh) {
    accSh = ss.insertSheet('Точность');
  } else {
    accSh.clearContents();
  }

  var brierLabel = brier === null ? '—' :
    brier + (brier < 0.20 ? '  (хорошо откалибровано)' : brier < 0.25 ? '  (нормально)' : '  (модель переуверена или недоуверена — стоит присмотреться)');

  accSh.getRange(1, 1, 9, 2).setValues([
    ['Точность прогнозов', ''],
    ['Обновлено', new Date()],
    ['', ''],
    ['Всего сыгранных матчей с ЧЕСТНЫМ прогнозом', total],
    ['Исключено (прогноз испорчен утечкой, см. столбец AD)', excludedContaminated],
    ['Угадано верно', correct + ' (' + pct(correct, total) + ')'],
    ['Из них явные фавориты (>60%): всего / угадано', favBucket.length + ' / ' + favCorrect + ' (' + pct(favCorrect, favBucket.length) + ')'],
    ['', ''],
    ['Brier score, весь сезон (0 = идеально, 0.25 = как монетка, 1 = наоборот)', brierLabel]
  ]);
  accSh.getRange('A1').setFontWeight('bold').setFontSize(14);
  accSh.getRange('A4:A7').setFontWeight('bold');
  accSh.getRange('A9').setFontWeight('bold');
  accSh.getRange('A5:B5').setFontColor(excludedContaminated > 0 ? '#b00020' : '#666666');

  // --- блок: скользящий Brier score ---
  var row = 11;
  accSh.getRange(row, 1).setValue('Скользящий Brier score (тренд)').setFontWeight('bold').setFontSize(12);
  row++;
  accSh.getRange(row, 1, 1, 2).setValues([['За последние 10 матчей', brier10 === null ? '—' : brier10]]);
  row++;
  accSh.getRange(row, 1, 1, 2).setValues([['За последние 20 матчей', brier20 === null ? '—' : brier20]]);
  row++;
  accSh.getRange(row, 1, 1, 2).setValues([['Сравнение с общим сезонным', brier10 !== null && brier !== null ? (brier10 < brier ? 'улучшается ↓' : brier10 > brier ? 'ухудшается ↑' : 'без изменений') : '—']]);
  row += 2;

  // --- блок: фаворит / андердог ---
  accSh.getRange(row, 1).setValue('Разбивка: фаворит (≥60%) / андердог (<60%)').setFontWeight('bold').setFontSize(12);
  row++;
  accSh.getRange(row, 1, 1, 4).setValues([['Категория', 'Матчей', 'Угадано', '% точности']]).setFontWeight('bold');
  row++;
  accSh.getRange(row, 1, 2, 4).setValues([
    ['Фаворит (≥60%)', favBucket.length, favCorrect, pct(favCorrect, favBucket.length)],
    ['Андердог (<60%)', dogBucket.length, dogCorrect, pct(dogCorrect, dogBucket.length)]
  ]);
  row += 3;

  // --- блок: калибровочная таблица ---
  accSh.getRange(row, 1).setValue('Калибровочная таблица (по узким интервалам уверенности)').setFontWeight('bold').setFontSize(12);
  row++;
  accSh.getRange(row, 1, 1, 5).setValues([['Бакет', 'Матчей', 'Угадано', '% точности', 'Средняя увер. модели']]).setFontWeight('bold');
  row++;
  accSh.getRange(row, 1, calibRows.length, 5).setValues(calibRows);
  accSh.getRange(row, 1, calibRows.length, 5).setBorder(true, true, true, true, true, true, '#b7b7b7', SpreadsheetApp.BorderStyle.SOLID);
  row += calibRows.length + 2;

  accSh.getRange(row, 1, 1, 5).merge()
    .setValue('Как читать калибровочную таблицу: если "% точности" бакета заметно ВЫШЕ его диапазона — модель ' +
      'недооценивает свою уверенность в этих матчах; если заметно НИЖЕ — переоценивает. В идеале % точности ' +
      'бакета должен примерно совпадать с его диапазоном (например, у бакета 70-80% и угадывать надо ~70-80% раз).')
    .setFontStyle('italic').setFontColor('#666666').setWrap(true);
  row += 2;

  // --- блок: калибровка тоталов ---
  accSh.getRange(row, 1).setValue('Калибровка тоталов').setFontWeight('bold').setFontSize(12);
  row++;
  accSh.getRange(row, 1, 1, 2).setValues([['Матчей с прогнозом тотала', totalsCount]]);
  row++;
  accSh.getRange(row, 1, 1, 2).setValues([['Средняя ошибка (|прогноз - факт|), шайб', avgAbsError === null ? '—' : avgAbsError]]);
  row++;
  accSh.getRange(row, 1, 1, 2).setValues([['Угадано Больше/Меньше линии ' + COUPON_TOTAL_LINE, totalsCount > 0 ? totalsLineHits + ' / ' + totalsCount + ' (' + pct(totalsLineHits, totalsCount) + ')' : '—']]);
  row += 2;
  accSh.getRange(row, 1, 1, 4).setValues([['Прогноз тотала', 'Матчей', 'Средний факт. тотал', 'Средняя ошибка']]).setFontWeight('bold');
  row++;
  accSh.getRange(row, 1, totalCalibRows.length, 4).setValues(totalCalibRows);
  accSh.getRange(row, 1, totalCalibRows.length, 4).setBorder(true, true, true, true, true, true, '#b7b7b7', SpreadsheetApp.BorderStyle.SOLID);
  row += totalCalibRows.length + 2;

  // --- блок: точность по командам ---
  accSh.getRange(row, 1).setValue('Точность прогнозов по командам').setFontWeight('bold').setFontSize(12);
  row++;
  accSh.getRange(row, 1, 1, 4).setValues([['Команда', 'Матчей', 'Угадано', '% точности']]).setFontWeight('bold');
  row++;
  if (teamRows.length > 0) {
    accSh.getRange(row, 1, teamRows.length, 4).setValues(teamRows);
    accSh.getRange(row, 1, teamRows.length, 4).setBorder(true, true, true, true, true, true, '#b7b7b7', SpreadsheetApp.BorderStyle.SOLID);
  }
  row += teamRows.length + 2;

  accSh.getRange(row, 1, 1, 5).merge()
    .setValue('Команда с числом матчей поменьше — цифра по ней менее надёжна статистически, не спешите с выводами ' +
      'по 2-3 играм. Системное отклонение (постоянно ниже среднего) заметнее на командах с 10+ матчами.')
    .setFontStyle('italic').setFontColor('#666666').setWrap(true);

  accSh.autoResizeColumns(1, 5);

  uiAlert_(
    'Точность на данный момент: ' + correct + ' из ' + total + ' (' + pct(correct, total) + ').\n' +
    'Brier score за весь сезон: ' + (brier === null ? '—' : brier) + '.\n' +
    'Скользящий Brier (последние 10 / 20): ' + (brier10 === null ? '—' : brier10) + ' / ' + (brier20 === null ? '—' : brier20) + '.\n\n' +
    'Добавлены калибровочная таблица по бакетам, разбивка фаворит/андердог, калибровка тоталов и точность по командам — подробности на листе "Точность".'
  );
}

/**
 * Создаёт лист "Ставки" (если его ещё нет) для ручного учёта реальных ставок
 * и банкролла. Заполнять руками: дату, матч, на кого ставка, коэффициент,
 * сумму и статус. Прибыль/убыток и текущий банкролл считаются сами.
 * Если лист уже существует — ничего не трогает (безопасно запускать повторно).
 */
function setupBetsSheet_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('Ставки');
  if (sh) {
    uiAlert_('Лист "Ставки" уже существует — не стал его трогать, чтобы не потерять ваши данные.');
    return;
  }

  sh = ss.insertSheet('Ставки');
  sh.getRange('A1').setValue('Начальный банкролл').setFontWeight('bold');
  sh.getRange('B1').setValue(10000).setBackground('#fff2cc');

  var headers = ['Дата', 'Матч', 'Ставка на', 'Коэффициент', 'Сумма ставки',
    'Статус (В ожидании/Выиграла/Проиграла)', 'Прибыль/убыток', 'Банкролл после'];
  sh.getRange(3, 1, 1, headers.length).setValues([headers]).setFontWeight('bold').setBackground('#d9e1f2');

  // формулы для строки 4 (первая строка ввода) — Прибыль/убыток и Банкролл после
  var formulaProfit = '=IF(F4="Выиграла";E4*(D4-1);IF(F4="Проиграла";-E4;0))';
  var formulaBankroll = '=IF(A4="";"";$B$1+SUM($G$4:G4))';
  sh.getRange('G4').setFormula(formulaProfit);
  sh.getRange('H4').setFormula(formulaBankroll);
  // размножим формулы на 100 строк вперёд про запас
  sh.getRange('G4:H4').copyTo(sh.getRange(5, 7, 96, 2));

  sh.setColumnWidths(1, 1, 90);
  sh.setColumnWidth(2, 220);
  sh.autoResizeColumns(3, 6);

  uiAlert_(
    'Лист "Ставки" создан. Впишите начальный банкролл в B1 (сейчас там 10000 для примера), ' +
    'дальше заполняйте строки вручную по мере того, как делаете ставки — статус "Выиграла"/"Проиграла" ' +
    'сам посчитает прибыль и обновит банкролл построчно.'
  );
}

/**
 * Устанавливает ежедневный триггер, который сам запускает
 * updateResultsFromWeb() (обновление результатов + Elo) каждый день в
 * заданный час — без необходимости нажимать кнопку руками. Проверяет, нет
 * ли уже такого триггера, чтобы не наставить дублей при повторном запуске.
 * При первом запуске Google попросит заново авторизовать скрипт — это
 * нормально, триггерам нужно отдельное разрешение.
 */
function installDailyTrigger_() { return installAllAutomation_(); }

/** Прежний вариант установки (оставлен для истории, не вызывается). */
function installDailyTriggerOld_() {
  var HOUR = 6; // утром по часовому поясу таблицы: к этому времени все вечерние матчи уже есть на sports.ru

  // снимаем прежние триггеры — и старый (только результаты), и новый, чтобы не было двойных запусков
  var removed = 0;
  ScriptApp.getProjectTriggers().forEach(function (t) {
    var h = t.getHandlerFunction();
    if (h === 'updateResultsFromWeb' || h === 'runAfterGameDay_') { ScriptApp.deleteTrigger(t); removed++; }
    if (h === 'updateMarketOddsAuto_' || h === 'gamePostMatchesAuto_' || h === 'liveUpdateAuto_' || h === 'agentDailyBriefAuto_') ScriptApp.deleteTrigger(t);
  });
  // игра: пост «матчи дня» (если бот и канал не подключены — просто ничего не делает)
  // часы — по Красноярску явно: у таблицы и проекта скрипта может стоять чужой пояс
  // (у этой таблицы — Лос-Анджелес, из-за этого «6 утра» наступало в 20:00 по Красноярску)
  ScriptApp.newTrigger('gamePostMatchesAuto_').timeBased().everyDays(1).atHour(GAME_POST_HOUR).inTimezone(TRIGGER_TZ).create();
  ScriptApp.newTrigger('runAfterGameDay_').timeBased().everyDays(1).atHour(HOUR).inTimezone(TRIGGER_TZ).create();
  // коэффициенты меняются в течение дня — обновляем их отдельно каждые 2 часа
  ScriptApp.newTrigger('updateMarketOddsAuto_').timeBased().everyHours(2).create();
  // агент: утренняя сводка по матчам (без ключей ничего не делает)
  ScriptApp.newTrigger('agentDailyBriefAuto_').timeBased().everyDays(1).atHour(AGENT_HOUR).inTimezone(TRIGGER_TZ).create();
  // живые шансы: раз в 5 минут; без идущих матчей ничего не скачивает
  ScriptApp.newTrigger('liveUpdateAuto_').timeBased().everyMinutes(5).create();

  uiAlert_(
    'Готово: каждое утро около ' + HOUR + ':00 по Красноярску (' + (HOUR - 4) + ':00 МСК) будет автоматически выполняться ' +
    '«Обновить всё после игрового дня» — результаты, Elo, новые матчи в прогнозах, точность, банкролл.' +
    (removed ? '\n\nПрежнее автообновление (только результаты) заменено этим.' : '') +
    '\n\nКоэффициенты рынка будут обновляться отдельно каждые 2 часа.' +
    '\nЕсли игра «Обыграй Джарвиса» подключена, пост «матчи дня» будет выходить каждый день в ' + GAME_POST_HOUR + ':00 по Красноярску (' + (GAME_POST_HOUR - 4) + ':00 МСК), ' +
    'а во время матчей — пост «🔴 LIVE» со счётом и периодами (проверка каждые 5 минут, пост обновляется после каждого периода).' +
    '\nАгент (если заданы ключи) — сводка по матчам в ' + AGENT_HOUR + ':00 по Красноярску (' + (AGENT_HOUR - 4) + ':00 МСК).' +
    '\n\nКнопкой в меню можно пользоваться и вручную в любой момент.'
  );
}

/**
 * Убирает ежедневный триггер, если вдруг разонравится автообновление.
 */
function removeDailyTrigger_() {
  var removed = 0;
  ScriptApp.getProjectTriggers().forEach(function (t) {
    var h = t.getHandlerFunction();
    if (h === 'updateResultsFromWeb' || AUTO_JOBS.some(function (j) { return j.fn === h; })) { ScriptApp.deleteTrigger(t); removed++; }
  });
  uiAlert_(removed > 0 ? 'Автообновление выключено.' : 'Автообновление и не было включено.');
}

/* ── Порядок в таблице: группы листов, цвета вкладок, служебные листы скрыты ──
 * Цвет вкладки = группа. Служебные листы (сырые данные, журналы, диагностика) скрываются — формулам и скриптам это
 * не мешает. Ничего не удаляется: скрытый лист возвращается через ПКМ по вкладке → «Показать скрытые листы».
 * Кнопки проверок сами открывают свой лист. Цвета новым листам проставляются при каждом «Обновить всё». */
function sheetGroups_() {
  var g = sheetGroupsBase_(), extra = SHEETS_HIDE_EXTRA;
  g.forEach(function (x) { if (!x.hide) x.sheets = x.sheets.filter(function (n) { return extra.indexOf(n) < 0; }); else x.sheets = x.sheets.concat(extra); });
  return g.filter(function (x) { return x.sheets.length; });
}
function sheetGroupsBase_() {
  return [
    { icon: '🟩', name: 'прогнозы и ставки', color: '#34a853', sheets: [SHEET_BRIEF, 'прогнозы', POST_SHEET, SHEET_VS, SHEET_ODDS, 'Точность', 'Сравнение_NeurHL', 'Купон дня', 'Мой купон', 'Банкролл', 'Ставки'] },
    { icon: '🟦', name: 'лига и команды', color: '#4285f4', sheets: ['Таблица', SHEET_RESULTS, 'Карточка команды', 'Elo_история', KEY_SHEET, 'Статистика_КХЛ', 'Статистика_НХЛ', 'Вратари_сегодня'] },
    { icon: '🟪', name: 'агент и досье', color: '#9334e6', sheets: [AGENT_SHEET, SCOUT_SHEET, DOSSIER_SHEET, SIGNAL_BOARD] },
    { icon: '🟧', name: 'видео экспертов', color: '#ff6d01', sheets: [VIDEO_SHEET, PRESEASON_SHEET, PICKS_SHEET] },
    { icon: '🟨', name: 'канал и игра', color: '#fbbc04', sheets: [GAME_VIEW, GAME_VIEW_OLD, NEWS_QUEUE_SHEET] },
    { icon: '⬛', name: 'ваши настройки', color: '#5f6368', sheets: [SHEET_TWEAKS, SHEET_TEAMS, POST_EMOJI_SHEET, 'Стартовый_рейтинг', EXPERT_SHEET, AUTO_SHEET] },
    { icon: '⬜', name: 'служебные (скрыты)', color: '#cccccc', hide: true, sheets: ['Data', SHEET_ELO, 'Parser_Data', 'Форма_расчет', 'Результаты 2025-26', 'Таблица 2025-26',
      'Броски_кэш', 'Броски_debug', 'Выездные_серии', 'Статистика_debug', SHEET_ODDS_LOG, HIST_ODDS_SHEET, GAME_PLAYERS, GAME_PICKS, LIVE_LOG, DOSSIER_LOG,
      SIGNAL_SHEET, LINEUP_SHEET, LINEUP_WATCH_SHEET, VIDEO_RAW_SHEET, SCOUT_SEEN_SHEET, NEWS_LIVE_SHEET, 'Таблица_история', 'Самопроверка', SHEET_CONTEXT,
      DIAG_SHEET, NEWS_DIAG_SHEET, LINEUP_DIAG_SHEET, 'Диагностика_НХЛ', 'КХЛ_матчи_приложение', 'Диагностика_КХЛ_приложение', 'Статистика_НХЛ_история'] }
  ];
}

/** Цвета вкладок по группам; hide — ещё и скрыть служебные. {colored, hidden[], other[]} */
function sheetsDecorate_(ss, hide) {
  ss = ss || SpreadsheetApp.getActive();
  var known = {}, hidden = [], colored = 0;
  sheetGroups_().forEach(function (g) {
    g.sheets.forEach(function (n) {
      if (!n || known[n]) return;
      known[n] = g;
      var sh = ss.getSheetByName(n);
      if (!sh) return;
      try { if (String(sh.getTabColor() || '').toLowerCase() !== g.color) { sh.setTabColor(g.color); colored++; } } catch (e) {}
      if (hide && g.hide && !sh.isSheetHidden()) { try { sh.hideSheet(); hidden.push(n); } catch (e) {} }
    });
  });
  var other = ss.getSheets().map(function (sh) { return sh.getName(); }).filter(function (n) { return !known[n]; });
  return { colored: colored, hidden: hidden, other: other };
}

/** Кнопка «Навести порядок»: вкладки по группам и цветам, служебные листы скрыты. */
function tidyUpSheets_() {
  var ss = SpreadsheetApp.getActive(), pos = 1;
  // порядок вкладок: группы слева направо (скрытые листы не трогаем — их нельзя сделать активными, не показав)
  sheetGroups_().forEach(function (g) {
    if (g.hide) return;
    g.sheets.forEach(function (n) {
      var sh = n && ss.getSheetByName(n);
      if (!sh || sh.isSheetHidden()) return;
      try { ss.setActiveSheet(sh); ss.moveActiveSheet(pos++); } catch (e) {}
    });
  });
  var r = sheetsDecorate_(ss, true);
  try { var first = ss.getSheetByName(SHEET_BRIEF) || ss.getSheetByName('прогнозы'); if (first) ss.setActiveSheet(first); } catch (e) {}
  uiAlert_('Готово. Цвет вкладки — это группа:\n\n' +
    sheetGroups_().filter(function (g) { return !g.hide; }).map(function (g) {
      var have = g.sheets.filter(function (n) { var sh = n && ss.getSheetByName(n); return sh && !sh.isSheetHidden(); });
      return g.icon + ' ' + g.name + (have.length ? ': ' + have.join(', ') : '');
    }).join('\n') +
    '\n\nСкрыто служебных листов: ' + (r.hidden.length ? r.hidden.length : 'уже были скрыты') + ' — это сырые данные, журналы и диагностика для формул и скриптов. ' +
    'Кнопки проверок сами откроют свой лист. Вернуть любой: ПКМ по вкладке внизу → «Показать скрытые листы».' +
    (r.other.length ? '\n\nБез группы (ваши или новые листы — не трогал): ' + r.other.join(', ') + '.' : ''));
  return r;
}

/** Показать (если скрыт) и открыть лист — для кнопок проверок. */
function sheetOpen_(name) {
  try {
    var ss = SpreadsheetApp.getActive(), sh = ss.getSheetByName(name);
    if (!sh) return;
    if (sh.isSheetHidden()) sh.showSheet();
    ss.setActiveSheet(sh);
  } catch (e) {}
}
function checkNewsNow_() { dossierCheckNews_(); sheetOpen_(NEWS_DIAG_SHEET); }
function checkLineupsNow_() { lineupDiag_(); sheetOpen_(LINEUP_DIAG_SHEET); }
function checkResultsNow_() { diagResultsSources_(); sheetOpen_(DIAG_SHEET); }
function selfCheckNow_() { selfCheckFactors_(); sheetOpen_('Самопроверка'); }

/**
 * Создаёт (или обновляет) лист "Карточка команды" — выбираете команду
 * (и, по желанию, соперника) из выпадающего списка в B3/B4, и ниже сама
 * подтягивается: текущий Elo, место в таблице, стартовый рейтинг, форма,
 * последние 8 игр, ближайшие 5 игр и очные встречи с выбранным соперником.
 * Можно запускать повторно — старое содержимое (кроме выбора в B3/B4, если
 * лист уже был) пересоздаётся заново.
 */
function setupTeamCard_() {
  var ss = SpreadsheetApp.getActive();
  var teamsSh = ss.getSheetByName(SHEET_TEAMS);
  if (!teamsSh) {
    uiAlert_('Не найден лист "' + SHEET_TEAMS + '".');
    return;
  }

  var existing = ss.getSheetByName('Карточка команды');
  var prevTeam1 = '', prevTeam2 = '';
  if (existing) {
    prevTeam1 = existing.getRange('B3').getValue();
    prevTeam2 = existing.getRange('B4').getValue();
    ss.deleteSheet(existing);
  }
  var sh = ss.insertSheet('Карточка команды', 1);
  sh.setHiddenGridlines(true);

  var TITLE_BG = '#1c4587', SECTION_BG = '#d9e1f2', INPUT_BG = '#fff2cc', BORDER = '#b7b7b7';
  var wideRange = function (row, numCols, numRows) { return sh.getRange(row, 1, numRows || 1, numCols); };

  // ---------- шапка ----------
  sh.getRange('A1:F1').merge().setValue('🏒  Карточка команды')
    .setFontWeight('bold').setFontSize(18).setFontColor('white').setBackground(TITLE_BG)
    .setVerticalAlignment('middle');
  sh.setRowHeight(1, 40);

  sh.getRange('A3').setValue('Команда:').setFontWeight('bold');
  sh.getRange('A4').setValue('Соперник (для очных встреч):').setFontWeight('bold');

  var lastTeamRow = teamsSh.getLastRow();
  var teamRange = teamsSh.getRange(2, 1, lastTeamRow - 1, 1);
  var rule = SpreadsheetApp.newDataValidation().requireValueInRange(teamRange, true).setAllowInvalid(false).build();
  sh.getRange('B3').setDataValidation(rule).setBackground(INPUT_BG).setFontWeight('bold').setBorder(true, true, true, true, false, false);
  sh.getRange('B4').setDataValidation(rule).setBackground(INPUT_BG).setFontWeight('bold').setBorder(true, true, true, true, false, false);
  var known = teamRange.getValues().map(function (r) { return String(r[0]).trim(); });
  if (known.indexOf(String(prevTeam1 || '').trim()) === -1) prevTeam1 = '';     // команды из старого справочника (напр. после смены лиги) не подставляем
  if (known.indexOf(String(prevTeam2 || '').trim()) === -1) prevTeam2 = '';
  sh.getRange('B3').setValue(prevTeam1 || teamsSh.getRange(2, 1).getValue());
  sh.getRange('B4').setValue(prevTeam2 || teamsSh.getRange(3, 1).getValue());

  // ---------- сравнение команд B3 vs B4 по всем ключевым метрикам ----------
  var factsRow = 6;
  sh.getRange(factsRow, 1, 1, 3).merge().setValue('Сравнение команд').setFontWeight('bold').setBackground(SECTION_BG);
  var compHeaderRow = factsRow + 1;
  sh.getRange(compHeaderRow, 1).setValue('Показатель').setFontWeight('bold');
  sh.getRange(compHeaderRow, 2).setFormula('=$B$3').setFontWeight('bold').setHorizontalAlignment('center');
  sh.getRange(compHeaderRow, 3).setFormula('=$B$4').setFontWeight('bold').setHorizontalAlignment('center');
  sh.getRange(compHeaderRow, 1, 1, 3).setBackground('#eef2fa');

  // шаблон формулы с {CELL} — подставляем $B$3 или $B$4 при сборке строки
  var facts = [
    ['Место в таблице', '=IFERROR(RANK(INDEX(Data!$C$2:$C$33;MATCH({CELL};Data!$A$2:$A$33;0));Data!$C$2:$C$33);"—")'],
    ['Очки', '=IFERROR(INDEX(Data!$C$2:$C$33;MATCH({CELL};Data!$A$2:$A$33;0));"—")'],
    ['Игры', '=IFERROR(INDEX(Data!$B$2:$B$33;MATCH({CELL};Data!$A$2:$A$33;0));"—")'],
    ['Победы', '=IFERROR(INDEX(Data!$D$2:$D$33;MATCH({CELL};Data!$A$2:$A$33;0));"—")'],
    ['Поражения', '=IFERROR(INDEX(Data!$E$2:$E$33;MATCH({CELL};Data!$A$2:$A$33;0));"—")'],
    ['Рейтинг силы (1-100)', '=IFERROR(ROUND(INDEX(Data!$T$2:$T$33;MATCH({CELL};Data!$A$2:$A$33;0));1);"—")'],
    ['Elo-рейтинг', '=IFERROR(ROUND(INDEX(Elo!$B$2:$B$33;MATCH({CELL};Elo!$A$2:$A$33;0));0);"—")'],
    ['Поправка формы (взвеш., посл. ' + FORM_WINDOW + ')', '=IFERROR(INDEX(Elo!$D$2:$D$33;MATCH({CELL};Elo!$A$2:$A$33;0));"—")'],
    ['Забито за игру (с учётом бросков)', '=IFERROR(ROUND(INDEX(Data!$U$2:$U$33;MATCH({CELL};Data!$A$2:$A$33;0));2);"—")'],
    ['Пропущено за игру', '=IFERROR(ROUND(INDEX(Data!$J$2:$J$33;MATCH({CELL};Data!$A$2:$A$33;0));2);"—")'],
    ['Забито дома, итог', '=IFERROR(ROUND(INDEX(Data!$Z$2:$Z$33;MATCH({CELL};Data!$A$2:$A$33;0));2);"—")'],
    ['Забито в гостях, итог', '=IFERROR(ROUND(INDEX(Data!$AA$2:$AA$33;MATCH({CELL};Data!$A$2:$A$33;0));2);"—")'],
    ['Пропущено дома, итог', '=IFERROR(ROUND(INDEX(Data!$AB$2:$AB$33;MATCH({CELL};Data!$A$2:$A$33;0));2);"—")'],
    ['Пропущено в гостях, итог', '=IFERROR(ROUND(INDEX(Data!$AC$2:$AC$33;MATCH({CELL};Data!$A$2:$A$33;0));2);"—")'],
    ['Стартовый рейтинг (на старте сезона)', '=IFERROR(INDEX(\'' + SHEET_TEAMS + '\'!$C$2:$C$33;MATCH({CELL};\'' + SHEET_TEAMS + '\'!$A$2:$A$33;0));"—")']
  ];
  facts.forEach(function (f, idx) {
    var r = compHeaderRow + 1 + idx;
    sh.getRange(r, 1).setValue(f[0]);
    sh.getRange(r, 2).setFormula(f[1].replace('{CELL}', '$B$3')).setHorizontalAlignment('center');
    sh.getRange(r, 3).setFormula(f[1].replace('{CELL}', '$B$4')).setHorizontalAlignment('center');
  });
  sh.getRange(compHeaderRow, 1, facts.length + 1, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  var row = compHeaderRow + facts.length + 2;

  // ---------- последние 8 игр ----------
  sh.getRange(row, 1, 1, 5).merge().setValue('Последние 8 игр команды из B3').setFontWeight('bold').setBackground(SECTION_BG);
  row++;
  sh.getRange(row, 1, 1, 5).setValues([['Дата', 'Хозяева', 'Гости', 'Г Хозяев', 'Г Гостей']]).setFontWeight('bold').setBackground('#eef2fa');
  var last8Row = row + 1;
  sh.getRange(last8Row, 1).setFormula(
    '=IFERROR(QUERY(\'' + SHEET_RESULTS + '\'!A2:J1600;' +
    '"select A, C, D, E, F where (C = \'"&$B$3&"\' or D = \'"&$B$3&"\') and B = \'Сыгран\' order by A desc limit 8";0);"нет данных")'
  );
  sh.getRange(last8Row, 1, 8, 1).setNumberFormat('dd.mm.yyyy');
  sh.getRange(row, 1, 9, 5).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  row = last8Row + 9;

  // ---------- ближайшие 5 игр ----------
  sh.getRange(row, 1, 1, 3).merge().setValue('Ближайшие 5 игр команды из B3').setFontWeight('bold').setBackground(SECTION_BG);
  row++;
  sh.getRange(row, 1, 1, 3).setValues([['Дата', 'Хозяева', 'Гости']]).setFontWeight('bold').setBackground('#eef2fa');
  var next5Row = row + 1;
  sh.getRange(next5Row, 1).setFormula(
    '=IFERROR(QUERY(\'' + SHEET_RESULTS + '\'!A2:J1600;' +
    '"select A, C, D where (C = \'"&$B$3&"\' or D = \'"&$B$3&"\') and B = \'Запланирован\' order by A asc limit 5";0);"нет данных")'
  );
  sh.getRange(next5Row, 1, 5, 1).setNumberFormat('dd.mm.yyyy');
  sh.getRange(row, 1, 6, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  row = next5Row + 6;

  // ---------- прогноз на следующую очную встречу B3 vs B4 ----------
  sh.getRange(row, 1, 1, 6).merge().setValue('Прогноз на ближайшую встречу B3 vs B4 (если запланирована)')
    .setFontWeight('bold').setBackground(SECTION_BG);
  row++;
  sh.getRange(row, 1, 1, 6).setValues([['Дата', 'Хозяева', 'Гости', 'Шансы Хозяев', 'Шансы Гостей', 'Наиболее вероятный победитель']])
    .setFontWeight('bold').setBackground('#eef2fa');
  var predRow = row + 1;
  sh.getRange(predRow, 1).setFormula(
    '=IFERROR(QUERY(прогнозы!A2:F1600;' +
    '"select A, B, C, D, E, F where ((B = \'"&$B$3&"\' and C = \'"&$B$4&"\') or (B = \'"&$B$4&"\' and C = \'"&$B$3&"\')) order by A asc limit 1";0);' +
    '"нет запланированной встречи между этими командами")'
  );
  sh.getRange(predRow, 1, 1, 1).setNumberFormat('dd.mm.yyyy');
  sh.getRange(predRow, 4, 1, 2).setNumberFormat('0.0%');
  sh.getRange(row, 1, 2, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  row = predRow + 2;

  // ---------- очные встречи: сводка ----------
  sh.getRange(row, 1, 1, 2).merge().setValue('Очные встречи B3 vs B4 — сводка (оба сезона)').setFontWeight('bold').setBackground(SECTION_BG);
  row++;
  var sumRow = row;
  sh.getRange(row, 1).setValue('Всего встреч:');
  sh.getRange(row, 2).setFormula(
    '=IFERROR(' +
      'SUMPRODUCT((\'' + SHEET_RESULTS + '\'!$B$2:$B$1600="Сыгран")*(' +
        '((\'' + SHEET_RESULTS + '\'!$C$2:$C$1600=$B$3)*(\'' + SHEET_RESULTS + '\'!$D$2:$D$1600=$B$4))' +
        '+((\'' + SHEET_RESULTS + '\'!$C$2:$C$1600=$B$4)*(\'' + SHEET_RESULTS + '\'!$D$2:$D$1600=$B$3))' +
      '))' +
      '+SUMPRODUCT(' +
        '((\'Результаты 2025-26\'!$C$2:$C$1400=$B$3)*(\'Результаты 2025-26\'!$D$2:$D$1400=$B$4))' +
        '+((\'Результаты 2025-26\'!$C$2:$C$1400=$B$4)*(\'Результаты 2025-26\'!$D$2:$D$1400=$B$3))' +
      ');"—")'
  ).setHorizontalAlignment('right');
  row++;
  sh.getRange(row, 1).setValue('Побед команды из B3:');
  sh.getRange(row, 2).setFormula(
    '=IFERROR(' +
      'SUMPRODUCT((\'' + SHEET_RESULTS + '\'!$B$2:$B$1600="Сыгран")*(\'' + SHEET_RESULTS + '\'!$C$2:$C$1600=$B$3)*(\'' + SHEET_RESULTS + '\'!$D$2:$D$1600=$B$4)*(\'' + SHEET_RESULTS + '\'!$E$2:$E$1600>\'' + SHEET_RESULTS + '\'!$F$2:$F$1600))' +
      '+SUMPRODUCT((\'' + SHEET_RESULTS + '\'!$B$2:$B$1600="Сыгран")*(\'' + SHEET_RESULTS + '\'!$C$2:$C$1600=$B$4)*(\'' + SHEET_RESULTS + '\'!$D$2:$D$1600=$B$3)*(\'' + SHEET_RESULTS + '\'!$F$2:$F$1600>\'' + SHEET_RESULTS + '\'!$E$2:$E$1600))' +
      '+SUMPRODUCT((\'Результаты 2025-26\'!$C$2:$C$1400=$B$3)*(\'Результаты 2025-26\'!$D$2:$D$1400=$B$4)*(\'Результаты 2025-26\'!$E$2:$E$1400>\'Результаты 2025-26\'!$F$2:$F$1400))' +
      '+SUMPRODUCT((\'Результаты 2025-26\'!$C$2:$C$1400=$B$4)*(\'Результаты 2025-26\'!$D$2:$D$1400=$B$3)*(\'Результаты 2025-26\'!$F$2:$F$1400>\'Результаты 2025-26\'!$E$2:$E$1400));"—")'
  ).setHorizontalAlignment('right');
  row++;
  sh.getRange(row, 1).setValue('Побед команды из B4:');
  sh.getRange(row, 2).setFormula('=IFERROR($' + colLetter_(2) + '$' + sumRow + '-$' + colLetter_(2) + '$' + (sumRow + 1) + ';"—")').setHorizontalAlignment('right');
  sh.getRange(sumRow, 1, 3, 2).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  row += 2;

  // ---------- очные встречи: список за текущий сезон ----------
  sh.getRange(row, 1, 1, 5).merge().setValue('История встреч — текущий сезон 2026/27').setFontWeight('bold').setBackground(SECTION_BG);
  row++;
  sh.getRange(row, 1, 1, 5).setValues([['Дата', 'Хозяева', 'Гости', 'Г Хозяев', 'Г Гостей']]).setFontWeight('bold').setBackground('#eef2fa');
  var h2hCurRow = row + 1;
  sh.getRange(h2hCurRow, 1).setFormula(
    '=IFERROR(QUERY(\'' + SHEET_RESULTS + '\'!A2:J1600;' +
    '"select A, C, D, E, F where ((C = \'"&$B$3&"\' and D = \'"&$B$4&"\') or (C = \'"&$B$4&"\' and D = \'"&$B$3&"\')) and B = \'Сыгран\' order by A desc";0);' +
    '"личных встреч в этом сезоне пока не было")'
  );
  sh.getRange(h2hCurRow, 1, 10, 1).setNumberFormat('dd.mm.yyyy');
  sh.getRange(row, 1, 11, 5).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  row = h2hCurRow + 11;

  // ---------- очные встречи: список за прошлый сезон 2025/26 ----------
  sh.getRange(row, 1, 1, 5).merge().setValue('История встреч — сезон 2025/26').setFontWeight('bold').setBackground(SECTION_BG);
  row++;
  sh.getRange(row, 1, 1, 5).setValues([['Дата', 'Хозяева', 'Гости', 'Г Хозяев', 'Г Гостей']]).setFontWeight('bold').setBackground('#eef2fa');
  var h2hPrevRow = row + 1;
  sh.getRange(h2hPrevRow, 1).setFormula(
    '=IFERROR(QUERY(\'Результаты 2025-26\'!A2:J1400;' +
    '"select A, C, D, E, F where (C = \'"&$B$3&"\' and D = \'"&$B$4&"\') or (C = \'"&$B$4&"\' and D = \'"&$B$3&"\') order by A desc";0);' +
    '"личных встреч в прошлом сезоне не было")'
  );
  sh.getRange(h2hPrevRow, 1, 10, 1).setNumberFormat('dd.mm.yyyy');
  sh.getRange(row, 1, 11, 5).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  // ---------- общее оформление ----------
  sh.setColumnWidth(1, 230);
  sh.setColumnWidth(2, 140);
  sh.setColumnWidths(3, 4, 110);
  sh.setFrozenRows(1);
  sh.getRange('A1:F1').setHorizontalAlignment('left');

  uiAlert_(
    'Готово: лист "Карточка команды" обновлён. Выберите команду в B3 и соперника в B4 — ' +
    'таблица сравнения (15 метрик по обеим командам), последние/ближайшие игры, прогноз на очную ' +
    'встречу и вся история личных встреч за оба сезона переключатся сами, как только измените выбор.'
  );
}

/** Слаги клубов на sports.ru для страниц новостей вида /hockey/club/<slug>/news/ */

/**
 * Создаёт лист "Купон дня" — по выбранной дате показывает все матчи этого
 * дня, отсортированные по уверенности модели (по убыванию), и сразу
 * предлагает три готовых купона (из 2, 3 и 4 самых уверенных исходов) с
 * посчитанной совместной вероятностью (произведение вероятностей — считаем
 * исходы независимыми, это упрощение, реальная совместная вероятность может
 * немного отличаться, если результаты матчей коррелируют).
 * Добавляет на "прогнозы" один вспомогательный столбец AI — уверенность
 * (максимум из шансов хозяев/гостей) — если он там уже есть, просто оставит
 * как есть, если добавляли раньше.
 * Можно запускать повторно — лист пересоздаётся заново, дата в B1 сохранится.
 */
var COUPON_TOTAL_LINE = 5.5;        // условная линия тотала — для текстовых подписей
var COUPON_TOTAL_LINE_FORMULA = '11/2'; // та же линия, но как дробь без точки — для арифметики в формулах
                                          // (эта таблица не принимает десятичную точку как разделитель)

function setupCouponSheet_() {
  var ss = SpreadsheetApp.getActive();
  var progSh = ss.getSheetByName('прогнозы');
  if (!progSh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }

  var colB = progSh.getRange(2, 2, progSh.getMaxRows() - 1, 1).getValues();
  var lastRow = 1;
  for (var i = 0; i < colB.length; i++) {
    if (String(colB[i][0]).trim() !== '') lastRow = i + 2;
  }

  var RM = SHEET_RESULTS;
  // общий "строительный блок" для поиска нужной строки в результаты матчей по дате+хозяева+гости
  var matchKey = '(\'' + RM + '\'!$A$2:$A$1600=$A2)*(\'' + RM + '\'!$C$2:$C$1600=$B2)*(\'' + RM + '\'!$D$2:$D$1600=$C2)';

  if (lastRow >= 2) {
    progSh.getRange('AI1').setValue('Увер. модели (макс. Х/Г)');
    progSh.getRange('AI2').setFormula('=IF(OR($D2="";$E2="");"";MAX($D2;$E2))');

    progSh.getRange('AJ1:AR1').setValues([[
      'Тотал (Б/М ' + COUPON_TOTAL_LINE + ')', 'Откл. от тотала',
      'Оценка увер. Победа', 'Оценка увер. Тотал',
      'Лучший тип', 'Лучшая оценка', 'Лучший исход (текст)',
      'Тотал сбылся?', 'Комбо сбылся?'
    ]]);
    progSh.getRange('AJ2').setFormula('=IF($I2="";"";IF($I2>=' + COUPON_TOTAL_LINE_FORMULA + ';"Больше ' + COUPON_TOTAL_LINE + '";"Меньше ' + COUPON_TOTAL_LINE + '"))');
    progSh.getRange('AK2').setFormula('=IF($I2="";"";ABS($I2-(' + COUPON_TOTAL_LINE_FORMULA + ')))');
    progSh.getRange('AL2').setFormula('=IF($AI2="";"";$AI2*100)');
    progSh.getRange('AM2').setFormula('=IF($AK2="";"";MIN(95;50+$AK2*15))');
    progSh.getRange('AN2').setFormula('=IF(OR($AL2="";$AM2="");"";IF($AL2>=$AM2;"Победа";"Тотал"))');
    progSh.getRange('AO2').setFormula('=IF(OR($AL2="";$AM2="");"";MAX($AL2;$AM2))');
    progSh.getRange('AP2').setFormula('=IF($AN2="";"";IF($AN2="Победа";$F2;$AJ2))');

    // AQ: сбылся ли тотал (сравниваем реальную сумму шайб с линией и с тем, что предсказали в AJ)
    progSh.getRange('AQ2').setFormula(
      '=IF(OR($B2="";$C2="");"";' +
        'IF(IFERROR(INDEX(\'' + RM + '\'!$B$2:$B$1600;MATCH(1;' + matchKey + ';0));"")<>"Сыгран";"";' +
          'IF(' +
            '(IFERROR(INDEX(\'' + RM + '\'!$E$2:$E$1600;MATCH(1;' + matchKey + ';0));0)' +
            '+IFERROR(INDEX(\'' + RM + '\'!$F$2:$F$1600;MATCH(1;' + matchKey + ';0));0))>=' + COUPON_TOTAL_LINE_FORMULA + ';' +
            'IF($AJ2="Больше ' + COUPON_TOTAL_LINE + '";"✅";"❌");' +
            'IF($AJ2="Меньше ' + COUPON_TOTAL_LINE + '";"✅";"❌")' +
          ')' +
        ')' +
      ')'
    );
    // AR: сбылось ли "лучшее" комбо-событие — берём готовый статус победы (K) либо тотала (AQ), смотря какой тип
    progSh.getRange('AR2').setFormula('=IF($AN2="";"";IF($AN2="Победа";$K2;$AQ2))');

    if (lastRow > 2) {
      progSh.getRange('AI2').copyTo(progSh.getRange(3, 35, lastRow - 2, 1));
      progSh.getRange('AJ2:AR2').copyTo(progSh.getRange(3, 36, lastRow - 2, 9));
    }
    progSh.getRange(2, 35, lastRow - 1, 1).setNumberFormat('0.0%');
  }

  var existing = ss.getSheetByName('Купон дня');
  var prevDate = null;
  if (existing) {
    var v = existing.getRange('B3').getValue();
    if (v instanceof Date) prevDate = v;
    ss.deleteSheet(existing);
  }
  var sh = ss.insertSheet('Купон дня', 1);
  sh.setHiddenGridlines(true);

  var TITLE_BG = '#1c4587', INPUT_BG = '#fff2cc', BORDER = '#b7b7b7';
  var WIN_BG = '#c9daf8', WIN_BG_LIGHT = '#eaf1fc', WIN_BG_DARK = '#3c78d8';
  var TOT_BG = '#d9ead3', TOT_BG_LIGHT = '#eef7ec', TOT_BG_DARK = '#38761d';
  var COMBO_BG = '#e6d6f2', COMBO_BG_LIGHT = '#f4ecf9', COMBO_BG_DARK = '#8e44ad';

  sh.getRange('A1:R1').merge().setValue('🎟️  Конструктор купона дня')
    .setFontWeight('bold').setFontSize(18).setFontColor('white').setBackground(TITLE_BG).setVerticalAlignment('middle');
  sh.setRowHeight(1, 40);

  sh.getRange('A3').setValue('Дата:').setFontWeight('bold');
  var defaultDate = prevDate || new Date();
  if (!prevDate) {
    sh.getRange('B3').setFormula('=MINIFS(прогнозы!$A$2:$A$1600;прогнозы!$B$2:$B$1600;"<>")');
    SpreadsheetApp.flush();
    var computed = sh.getRange('B3').getValue();
    sh.getRange('B3').setValue(computed);
  } else {
    sh.getRange('B3').setValue(defaultDate);
  }
  sh.getRange('B3').setNumberFormat('dd.mm.yyyy').setBackground(INPUT_BG).setFontWeight('bold')
    .setBorder(true, true, true, true, false, false);
  sh.getRange('C3').setValue('← можно поменять на любую другую дату из календаря').setFontStyle('italic').setFontColor('#666666');

  // ===================== три блока рядом: Победы (A-E), Тоталы (G-K), Комбо (M-R) =====================
  // столбец F и L — узкие разделители между блоками

  var WIN_COL = 1, TOT_COL = 7, COMBO_COL = 13;

  var HEADER_ROW = 5;
  sh.getRange(HEADER_ROW, WIN_COL, 1, 5).merge().setValue('🏆 Победы').setFontWeight('bold').setFontSize(13).setFontColor('white').setBackground(WIN_BG_DARK);
  sh.getRange(HEADER_ROW, TOT_COL, 1, 5).merge().setValue('⚽ Тоталы').setFontWeight('bold').setFontSize(13).setFontColor('white').setBackground(TOT_BG_DARK);
  sh.getRange(HEADER_ROW, COMBO_COL, 1, 6).merge().setValue('🎯 Комбо').setFontWeight('bold').setFontSize(13).setFontColor('white').setBackground(COMBO_BG_DARK);

  var SUBHEAD_ROW = HEADER_ROW + 1;
  sh.getRange(SUBHEAD_ROW, WIN_COL, 1, 5).setValues([['Хозяева', 'Гости', 'Прогноз', 'Увер.', 'Статус']]).setFontWeight('bold').setBackground(WIN_BG_LIGHT);
  sh.getRange(SUBHEAD_ROW, TOT_COL, 1, 5).setValues([['Хозяева', 'Гости', 'Прогноз тотала', 'Ожид.', 'Статус']]).setFontWeight('bold').setBackground(TOT_BG_LIGHT);
  sh.getRange(SUBHEAD_ROW, COMBO_COL, 1, 6).setValues([['Хозяева', 'Гости', 'Тип', 'Исход', 'Оценка', 'Статус']]).setFontWeight('bold').setBackground(COMBO_BG_LIGHT);

  var LIST_ROW = SUBHEAD_ROW + 1;
  var LIST_HEIGHT = 8;

  sh.getRange(LIST_ROW, WIN_COL).setFormula(
    '=IFERROR(QUERY(прогнозы!A2:AI1600;' +
    '"select B, C, F, AI, K where A = date \'"&TEXT($B$3;"yyyy-MM-dd")&"\' and AI is not null order by AI desc";0);' +
    '"нет матчей")'
  );
  sh.getRange(LIST_ROW, WIN_COL + 3, LIST_HEIGHT, 1).setNumberFormat('0.0%');

  sh.getRange(LIST_ROW, TOT_COL).setFormula(
    '=IFERROR(QUERY(прогнозы!A2:AR1600;' +
    '"select B, C, AJ, I, AQ where A = date \'"&TEXT($B$3;"yyyy-MM-dd")&"\' and AK is not null order by AK desc";0);' +
    '"нет матчей")'
  );

  sh.getRange(LIST_ROW, COMBO_COL).setFormula(
    '=IFERROR(QUERY(прогнозы!A2:AR1600;' +
    '"select B, C, AN, AP, AO, AR where A = date \'"&TEXT($B$3;"yyyy-MM-dd")&"\' and AO is not null order by AO desc";0);' +
    '"нет матчей")'
  );

  sh.getRange(HEADER_ROW, WIN_COL, LIST_HEIGHT + 2, 5).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(HEADER_ROW, TOT_COL, LIST_HEIGHT + 2, 5).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(HEADER_ROW, COMBO_COL, LIST_HEIGHT + 2, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  var row = LIST_ROW + LIST_HEIGHT + 1;

  // общая функция статуса купона: ✅ если все ноги ✅, ❌ если хоть одна ❌, иначе пусто (есть ещё не сыгранные)
  var couponStatusFormula = function (statusRange) {
    return '=IF(COUNTIF(' + statusRange + ';"❌")>0;"❌ Не зашёл";IF(COUNTIF(' + statusRange + ';"✅")=' +
      'COUNTA(' + statusRange + ');"✅ Зашёл";"⏳ Ждём"))';
  };

  // ---------- купоны по победам ----------
  var buildWinCoupon = function (n, startRow) {
    sh.getRange(startRow, WIN_COL, 1, 3).merge().setValue('Купон из ' + n).setFontWeight('bold').setBackground(WIN_BG);
    var r = startRow + 1;
    var firstLegRow = r;
    for (var k = 0; k < n; k++) {
      var srcRow = LIST_ROW + k;
      sh.getRange(r, WIN_COL).setFormula('=IFERROR(INDEX($A' + srcRow + ':$B' + srcRow + ';1;1)&" — "&INDEX($A' + srcRow + ':$B' + srcRow + ';1;2);"")');
      sh.getRange(r, WIN_COL + 1).setFormula('=IFERROR(INDEX($C' + srcRow + ':$C' + srcRow + ';1;1);"")');
      sh.getRange(r, WIN_COL + 2).setFormula('=IFERROR(INDEX($D' + srcRow + ':$D' + srcRow + ';1;1);"")').setNumberFormat('0.0%');
      sh.getRange(r, WIN_COL + 3).setFormula('=IFERROR(INDEX($E' + srcRow + ':$E' + srcRow + ';1;1);"")').setHorizontalAlignment('center');
      r++;
    }
    var lastLegRow = r - 1;
    sh.getRange(r, WIN_COL).setValue('Совместная вероятность:').setFontWeight('bold');
    var parts = [];
    for (var k2 = 0; k2 < n; k2++) parts.push('$C' + (firstLegRow + k2));
    sh.getRange(r, WIN_COL + 2).setFormula('=IFERROR(' + parts.join('*') + ';"")').setNumberFormat('0.0%').setFontWeight('bold');
    sh.getRange(r, WIN_COL + 3).setFormula(couponStatusFormula('$D' + firstLegRow + ':$D' + lastLegRow)).setFontWeight('bold').setHorizontalAlignment('center');
    sh.getRange(startRow + 1, WIN_COL, n + 1, 5).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
    return r + 2;
  };
  var winRow = row;
  winRow = buildWinCoupon(2, winRow);
  winRow = buildWinCoupon(3, winRow);
  winRow = buildWinCoupon(4, winRow);
  sh.getRange(winRow, WIN_COL, 1, 5).merge().setValue('Произведение отдельных вероятностей (исходы считаю независимыми).')
    .setFontStyle('italic').setFontColor('#666666').setWrap(true);

  // ---------- купоны по тоталам ----------
  var buildTotalsCoupon = function (n, startRow) {
    sh.getRange(startRow, TOT_COL, 1, 3).merge().setValue('Купон из ' + n).setFontWeight('bold').setBackground(TOT_BG);
    var r = startRow + 1;
    var firstLegRow = r;
    for (var k = 0; k < n; k++) {
      var srcRow = LIST_ROW + k;
      sh.getRange(r, TOT_COL).setFormula('=IFERROR(INDEX($G' + srcRow + ':$H' + srcRow + ';1;1)&" — "&INDEX($G' + srcRow + ':$H' + srcRow + ';1;2);"")');
      sh.getRange(r, TOT_COL + 1).setFormula('=IFERROR(INDEX($I' + srcRow + ':$I' + srcRow + ';1;1);"")');
      sh.getRange(r, TOT_COL + 2).setFormula('=IFERROR("ожид. "&INDEX($J' + srcRow + ':$J' + srcRow + ';1;1);"")');
      sh.getRange(r, TOT_COL + 3).setFormula('=IFERROR(INDEX($K' + srcRow + ':$K' + srcRow + ';1;1);"")').setHorizontalAlignment('center');
      r++;
    }
    var lastLegRow = r - 1;
    sh.getRange(r, TOT_COL).setValue('Статус купона:').setFontWeight('bold');
    sh.getRange(r, TOT_COL + 3).setFormula(couponStatusFormula('$K' + firstLegRow + ':$K' + lastLegRow)).setFontWeight('bold').setHorizontalAlignment('center');
    sh.getRange(startRow + 1, TOT_COL, n + 1, 5).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
    return r + 2;
  };
  var totRow = row;
  totRow = buildTotalsCoupon(2, totRow);
  totRow = buildTotalsCoupon(3, totRow);
  totRow = buildTotalsCoupon(4, totRow);
  sh.getRange(totRow, TOT_COL, 1, 5).merge().setValue('Тотал — не вероятность, а ожидаемое число голов; совместную "вероятность" намеренно не считаю.')
    .setFontStyle('italic').setFontColor('#666666').setWrap(true);

  // ---------- комбинированный купон ----------
  var buildComboCoupon = function (n, startRow) {
    sh.getRange(startRow, COMBO_COL, 1, 4).merge().setValue('Купон из ' + n).setFontWeight('bold').setBackground(COMBO_BG);
    var r = startRow + 1;
    var firstLegRow = r;
    for (var k = 0; k < n; k++) {
      var srcRow = LIST_ROW + k;
      sh.getRange(r, COMBO_COL).setFormula('=IFERROR(INDEX($M' + srcRow + ':$N' + srcRow + ';1;1)&" — "&INDEX($M' + srcRow + ':$N' + srcRow + ';1;2);"")');
      sh.getRange(r, COMBO_COL + 1).setFormula('=IFERROR(INDEX($O' + srcRow + ':$O' + srcRow + ';1;1);"")');
      sh.getRange(r, COMBO_COL + 2).setFormula('=IFERROR(INDEX($P' + srcRow + ':$P' + srcRow + ';1;1);"")');
      sh.getRange(r, COMBO_COL + 3).setFormula('=IFERROR(ROUND(INDEX($Q' + srcRow + ':$Q' + srcRow + ';1;1);1)&"/100";"")');
      sh.getRange(r, COMBO_COL + 4).setFormula('=IFERROR(INDEX($R' + srcRow + ':$R' + srcRow + ';1;1);"")').setHorizontalAlignment('center');
      r++;
    }
    var lastLegRow = r - 1;
    sh.getRange(r, COMBO_COL).setValue('Статус купона:').setFontWeight('bold');
    sh.getRange(r, COMBO_COL + 4).setFormula(couponStatusFormula('$' + colLetter_(COMBO_COL + 4) + firstLegRow + ':$' + colLetter_(COMBO_COL + 4) + lastLegRow)).setFontWeight('bold').setHorizontalAlignment('center');
    sh.getRange(startRow + 1, COMBO_COL, n + 1, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
    return r + 2;
  };
  var comboRow = row;
  comboRow = buildComboCoupon(2, comboRow);
  comboRow = buildComboCoupon(3, comboRow);
  comboRow = buildComboCoupon(4, comboRow);
  sh.getRange(comboRow, COMBO_COL, 1, 6).merge().setValue('Оценка 0-100: для побед — реальная вероятность×100, для тоталов — эвристика. Сравнивайте как ранг.')
    .setFontStyle('italic').setFontColor('#666666').setWrap(true);

  sh.setColumnWidth(1, 150); sh.setColumnWidth(2, 150); sh.setColumnWidth(3, 120);
  sh.setColumnWidth(4, 70); sh.setColumnWidth(5, 70); sh.setColumnWidth(6, 20);
  sh.setColumnWidth(7, 150); sh.setColumnWidth(8, 150); sh.setColumnWidth(9, 120);
  sh.setColumnWidth(10, 80); sh.setColumnWidth(11, 70); sh.setColumnWidth(12, 20);
  sh.setColumnWidth(13, 150); sh.setColumnWidth(14, 150); sh.setColumnWidth(15, 80);
  sh.setColumnWidth(16, 120); sh.setColumnWidth(17, 80); sh.setColumnWidth(18, 70);
  sh.setFrozenRows(1);

  uiAlert_(
    'Готово: лист "Купон дня" пересобран с тремя цветными блоками (синий — победы, зелёный — тоталы, ' +
    'фиолетовый — комбо) и статусом ✅/❌ по каждой ноге и по купону целиком. Статус появится, как только ' +
    'соответствующий матч будет отмечен как сыгранный через "Обновить результаты".'
  );
}

function colLetter_(col) {
  var letter = '';
  while (col > 0) {
    var rem = (col - 1) % 26;
    letter = String.fromCharCode(65 + rem) + letter;
    col = Math.floor((col - 1) / 26);
  }
  return letter;
}

/**
 * Заменяет столбцы G-J на листе "прогнозы" (раньше — "Ожидаемые броски"/
 * "Ожидаемый штраф", которые тянулись из замороженного Parser_Data — те же
 * самые фиктивные цифры, что мы отключили от рейтинга силы) на честные
 * прогнозы, посчитанные из настоящей текущей результативности команд
 * (Data!"Забито за игру" / "Пропущено за игру" — эти данные живые и
 * обновляются с каждым сыгранным матчем):
 *   Ожид. голы Хозяев = (ЗабитоХ + ПропущеноГ соперника) / 2
 *   Ожид. голы Гостей  = (ЗабитоГ + ПропущеноХ соперника) / 2
 *   Ожид. тотал        = сумма двух предыдущих
 *   Ожид. разница (Х-Г)= разница двух предыдущих
 * Реальных данных по броскам и штрафному времени за игру, увы, по-прежнему
 * взять неоткуда (см. более раннее обсуждение) — эти столбцы удаляются, а не
 * чинятся, потому что источника для них нет.
 * Можно запускать повторно.
 */
function setupExpectedGoalsFormulas_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }

  var colB = sh.getRange(2, 2, sh.getMaxRows() - 1, 1).getValues();
  var lastRow = 1;
  for (var i = 0; i < colB.length; i++) {
    if (String(colB[i][0]).trim() !== '') lastRow = i + 2;
  }
  if (lastRow < 2) {
    uiAlert_('На листе "прогнозы" не найдено ни одной строки с матчем в столбце B.');
    return;
  }
  var numRows = lastRow - 1;

  // Названия намеренно НЕ "Ожидаемые голы Хозяев/Гостей" — это самостоятельная статистика
  // результативности каждой команды (для тоталов), не связанная с моделью победителя (D/E/F).
  // Более сильная по общей игре команда вполне может быть менее результативной сама по себе —
  // это не ошибка данных, а две разные вещи, которые эти столбцы намеренно не путают местами.
  sh.getRange(1, 7, 1, 4).setValues([['Ср. голы Хозяев за игру', 'Ср. голы Гостей за игру', 'Ожид. тотал (Х+Г)', 'Ожид. разница (Х-Г)']]);

  var formulaG = '=IFERROR(ROUND((INDEX(Data!$I$2:$I$33;MATCH(B2;Data!$A$2:$A$33;0))+INDEX(Data!$J$2:$J$33;MATCH(C2;Data!$A$2:$A$33;0)))/2;2);"")';
  var formulaH = '=IFERROR(ROUND((INDEX(Data!$I$2:$I$33;MATCH(C2;Data!$A$2:$A$33;0))+INDEX(Data!$J$2:$J$33;MATCH(B2;Data!$A$2:$A$33;0)))/2;2);"")';
  var formulaI = '=IFERROR(ROUND(G2+H2;2);"")';
  var formulaJ = '=IFERROR(ROUND(G2-H2;2);"")';

  // G,H,I,J ставятся только в несыгранные строки — строка 2 может быть уже сыгранной и замороженной

  if (numRows > 1) {
    applyGoalsFormulas_(sh);
  }

  uiAlert_(
    'Готово: столбцы G-J теперь считают ожидаемые голы, тотал и разницу по настоящей текущей ' +
    'результативности команд вместо старых замороженных бросков/штрафа. Реального источника по ' +
    'броскам и штрафному времени за игру по-прежнему нет — эти столбцы просто убраны, а не заменены заглушкой.'
  );
}

var ROAD_TRIP_STEP = 1.5;   // очков рейтинга за каждую доп. игру серии подряд на выезде
var ROAD_TRIP_CAP = 6;      // максимальный бонус хозяевам за длинную выездную серию гостей

/**
 * Считает для каждой команды глубину текущей выездной серии на каждую игру
 * сезона (по всему расписанию — и сыгранному, и ещё запланированному, ведь
 * календарь известен заранее): 1 — первая игра на выезде после домашней,
 * 2 — вторая подряд без возврата домой, и так далее; при игре дома счётчик
 * сбрасывается в 0. Результат пишется в лист "Выездные_серии"
 * (Дата, Команда, НомерВСерии) — оттуда его подтягивает поправка к прогнозу.
 * Можно запускать повторно — лист каждый раз перестраивается с нуля.
 */
function computeRoadTrips_() {
  var ss = SpreadsheetApp.getActive();
  var resultsSh = ss.getSheetByName(SHEET_RESULTS);
  if (!resultsSh) {
    uiAlert_('Не найден лист "' + SHEET_RESULTS + '".');
    return;
  }

  var resData = resultsSh.getDataRange().getValues();
  var header = resData[0];
  var col = { date: header.indexOf('Дата'), home: header.indexOf('Хозяева'), away: header.indexOf('Гости') };

  var appearances = {}; // команда -> [{date, isHome}]
  for (var r = 1; r < resData.length; r++) {
    var d = resData[r][col.date];
    if (!(d instanceof Date)) continue;
    var home = String(resData[r][col.home]).trim();
    var away = String(resData[r][col.away]).trim();
    if (!home || !away) continue;
    if (!appearances[home]) appearances[home] = [];
    if (!appearances[away]) appearances[away] = [];
    appearances[home].push({ date: d, isHome: true });
    appearances[away].push({ date: d, isHome: false });
  }

  var outRows = [];
  for (var team in appearances) {
    var games = appearances[team];
    games.sort(function (a, b) { return a.date.getTime() - b.date.getTime(); });
    var streak = 0;
    for (var i = 0; i < games.length; i++) {
      if (games[i].isHome) {
        streak = 0;
      } else {
        streak++;
        outRows.push([games[i].date, team, streak]);
      }
    }
  }

  var sh = ss.getSheetByName('Выездные_серии');
  if (!sh) {
    sh = ss.insertSheet('Выездные_серии');
  } else {
    sh.clearContents();
  }
  sh.getRange(1, 1, 1, 3).setValues([['Дата', 'Команда', 'Номер игры в выездной серии']]);
  if (outRows.length > 0) {
    sh.getRange(2, 1, outRows.length, 3).setValues(outRows);
    sh.getRange(2, 1, outRows.length, 1).setNumberFormat('dd.mm.yyyy');
  }

  uiAlert_('Готово: посчитаны выездные серии для ' + Object.keys(appearances).length + ' команд, ' + outRows.length + ' игр на выезде всего.');
}

/**
 * Добавляет на лист "прогнозы" столбец AS — бонус хозяевам за то, что гости
 * сейчас в затяжной выездной серии (каждая следующая игра подряд на выезде
 * без возврата домой добавляет ' + ROAD_TRIP_STEP + ' очка, максимум ' + ROAD_TRIP_CAP + ') —
 * и подключает его к формуле шансов хозяев. Перед этим нужно один раз
 * запустить "Пересчитать выездные серии". Можно запускать повторно.
 */
function setupRoadTripFormulas_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }
  if (!ss.getSheetByName('Выездные_серии')) {
    uiAlert_('Сначала нажмите "Пересчитать выездные серии" — лист с данными ещё не создан.');
    return;
  }

  var colB = sh.getRange(2, 2, sh.getMaxRows() - 1, 1).getValues();
  var lastRow = 1;
  for (var i = 0; i < colB.length; i++) {
    if (String(colB[i][0]).trim() !== '') lastRow = i + 2;
  }
  if (lastRow < 2) {
    uiAlert_('На листе "прогнозы" не найдено ни одной строки с матчем в столбце B.');
    return;
  }
  var numRows = lastRow - 1;

  sh.getRange('AS1').setValue('Бонус Х за выездную серию Г');
  var formulaAS =
    '=MIN(' + ROAD_TRIP_CAP + ';MAX(0;(SUMPRODUCT((Выездные_серии!$A$2:$A$100000=$A2)*(Выездные_серии!$B$2:$B$100000=$C2)*(Выездные_серии!$C$2:$C$100000))-1)*' +
    (ROAD_TRIP_STEP * 2) + '/2))';
  sh.getRange('AS2').setFormula(formulaAS);
  if (numRows > 1) sh.getRange('AS2').copyTo(sh.getRange(3, 45, numRows - 1, 1));

  // формула шансов хозяев (столбец D) целиком — теперь ещё и с бонусом за выездную серию гостей (AS2)
  var formulaD =
    '=IF(OR(B2="";C2="");"";ROUND(MAX(8/100;MIN(92/100;1/(1+10^(-((INDEX(Data!$T$2:$T$33;MATCH(B2;Data!$A$2:$A$33;0)))+U2+P2+AB2+AC2+AS2-(INDEX(Data!$T$2:$T$33;MATCH(C2;Data!$A$2:$A$33;0))))/$M$3))));4))';
  // формула шансов хозяев ставится централизованно, только в несыгранные строки
  // (см. applyProbabilityFormula_ в пакете исправлений — это защищает заморозку)

  if (numRows > 1) applyProbabilityFormula_(sh);

  uiAlert_(
    'Готово: поправка за выездные серии подключена для ' + numRows + ' строк. Команда на 3-4-й игре ' +
    'подряд на выезде без возврата домой теперь даёт небольшой бонус сегодняшним хозяевам.'
  );
}

var DENSITY_WINDOW_DAYS = 5; // окно в днях для подсчёта "плотности" календаря

/**
 * Добавляет на лист "прогнозы" поправку за плотность календаря — в отличие
 * от уже существующей усталости (которая смотрит только на разрыв до
 * ПРЕДЫДУЩЕЙ игры), здесь считается, сколько игр команда провела за
 * последние 5 дней. 3+ игры за 5 дней — это устаёт заметно сильнее, чем
 * просто "1 день отдыха", даже если формальный разрыв перед сегодняшней
 * игрой одинаковый. Столбцы AT/AU — счётчик игр за окно у хозяев/гостей,
 * AV — итоговая поправка (в пользу того, у кого календарь легче).
 * Можно запускать повторно.
 */
function setupCalendarDensityFormulas_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }

  var colB = sh.getRange(2, 2, sh.getMaxRows() - 1, 1).getValues();
  var lastRow = 1;
  for (var i = 0; i < colB.length; i++) {
    if (String(colB[i][0]).trim() !== '') lastRow = i + 2;
  }
  if (lastRow < 2) {
    uiAlert_('На листе "прогнозы" не найдено ни одной строки с матчем в столбце B.');
    return;
  }
  var numRows = lastRow - 1;

  sh.getRange('AT1').setValue('Игр Хозяев за посл. ' + DENSITY_WINDOW_DAYS + ' дн.');
  sh.getRange('AU1').setValue('Игр Гостей за посл. ' + DENSITY_WINDOW_DAYS + ' дн.');
  sh.getRange('AV1').setValue('Поправка плотности (Х-Г)');

  var formulaAT =
    '=SUMPRODUCT((\'' + SHEET_RESULTS + '\'!$A$2:$A$1600>=$A2-' + DENSITY_WINDOW_DAYS + ')*(\'' + SHEET_RESULTS + '\'!$A$2:$A$1600<$A2)*' +
    '((\'' + SHEET_RESULTS + '\'!$C$2:$C$1600=$B2)+(\'' + SHEET_RESULTS + '\'!$D$2:$D$1600=$B2)))';
  var formulaAU =
    '=SUMPRODUCT((\'' + SHEET_RESULTS + '\'!$A$2:$A$1600>=$A2-' + DENSITY_WINDOW_DAYS + ')*(\'' + SHEET_RESULTS + '\'!$A$2:$A$1600<$A2)*' +
    '((\'' + SHEET_RESULTS + '\'!$C$2:$C$1600=$C2)+(\'' + SHEET_RESULTS + '\'!$D$2:$D$1600=$C2)))';
  var formulaAV = '=(IF(AT2>=3;-3;IF(AT2>=2;-1;0)))-(IF(AU2>=3;-3;IF(AU2>=2;-1;0)))';

  sh.getRange('AT2').setFormula(formulaAT);
  sh.getRange('AU2').setFormula(formulaAU);
  sh.getRange('AV2').setFormula(formulaAV);
  if (numRows > 1) sh.getRange('AT2:AV2').copyTo(sh.getRange(3, 46, numRows - 1, 3));

  // формула шансов хозяев (столбец D) целиком — теперь ещё и с поправкой на плотность календаря (AV2)
  var formulaD =
    '=IF(OR(B2="";C2="");"";ROUND(MAX(8/100;MIN(92/100;1/(1+10^(-((INDEX(Data!$T$2:$T$33;MATCH(B2;Data!$A$2:$A$33;0)))+U2+P2+AB2+AC2+AS2+AV2-(INDEX(Data!$T$2:$T$33;MATCH(C2;Data!$A$2:$A$33;0))))/$M$3))));4))';
  // формула шансов хозяев ставится централизованно, только в несыгранные строки
  // (см. applyProbabilityFormula_ в пакете исправлений — это защищает заморозку)

  if (numRows > 1) applyProbabilityFormula_(sh);

  uiAlert_(
    'Готово: поправка за плотность календаря подключена для ' + numRows + ' строк. Команда, которая ' +
    'играет 3+ раз за последние ' + DENSITY_WINDOW_DAYS + ' дней, теперь получает дополнительный штраф ' +
    'сверх обычной поправки на отдых.'
  );
}

/**
 * Строит на листе "Купон дня" сводную таблицу ВСЕХ событий выбранной даты —
 * и по победам, и по тоталам вместе, одним списком, отсортированным по
 * убыванию уверенности модели (не только топ-2/3/4, как в готовых купонах
 * выше, а вообще все матчи этого дня по обоим типам событий). Читает уже
 * готовые столбцы AI/AJ/AL/AM/K/AQ на листе "прогнозы" (их ставит
 * "Создать конструктор купона дня" — если этот пункт ещё не запускали,
 * сначала нужно его). Пишет как значения, не формулы, поэтому таблица
 * актуальна на момент нажатия кнопки — при смене даты в B3 нажмите ещё раз.
 * Можно запускать повторно, старая таблица каждый раз перестраивается.
 */
function updateAllEventsForDay_() {
  try {
    var ss = SpreadsheetApp.getActive();
    var sh = ss.getSheetByName('Купон дня');
    var progSh = ss.getSheetByName('прогнозы');
    if (!sh) {
      uiAlert_('Не найден лист "Купон дня". Сначала запустите "Создать конструктор купона дня".');
      return;
    }
    if (!progSh) {
      uiAlert_('Не найден лист "прогнозы".');
      return;
    }

    var targetDate = sh.getRange('B3').getValue();
    if (!(targetDate instanceof Date)) {
      uiAlert_('В ячейке B3 листа "Купон дня" нет даты — выберите дату и повторите.');
      return;
    }
    var targetKey = Utilities.formatDate(targetDate, Session.getScriptTimeZone(), 'yyyy-MM-dd');

    var lastRow = progSh.getLastRow();
    if (lastRow < 2) {
      uiAlert_('На листе "прогнозы" нет строк с матчами.');
      return;
    }
    var lastCol = Math.max(43, progSh.getLastColumn());
    var data = progSh.getRange(2, 1, lastRow - 1, lastCol).getValues();

    var events = [];
    for (var i = 0; i < data.length; i++) {
      var row = data[i];
      var date = row[0], home = row[1], away = row[2], winText = row[5];
      if (!(date instanceof Date) || !home || !away) continue;
      var dateKey = Utilities.formatDate(date, Session.getScriptTimeZone(), 'yyyy-MM-dd');
      if (dateKey !== targetKey) continue;

      var winStatus = row[10];     // K
      var winConf = row[37];       // AL (0-100)
      var totalText = row[35];     // AJ
      var totalConf = row[38];     // AM (0-100)
      var totalStatus = row[42];   // AQ

      if (winText !== '' && winConf !== '') {
        events.push({ type: 'Победа', match: home + ' — ' + away, pick: winText, conf: Number(winConf), status: winStatus });
      }
      if (totalText !== '' && totalConf !== '') {
        events.push({ type: 'Тотал', match: home + ' — ' + away, pick: totalText, conf: Number(totalConf), status: totalStatus });
      }
    }

    events.sort(function (a, b) { return b.conf - a.conf; });

    // область под таблицу — справа от блока "Комбо" (он занимает столбцы M-R, 13-18),
    // с отступом в один пустой столбец, начиная с той же строки, что и остальные блоки.
    // Если на листе физически ещё нет столбца ANCHOR_COL+5 — досоздаём столбцы, иначе
    // getRange может не сработать так, как ожидается.
    var ANCHOR_ROW = 5;
    var ANCHOR_COL = 20; // T
    var neededCols = ANCHOR_COL + 5; // до Y включительно
    if (sh.getMaxColumns() < neededCols) {
      sh.insertColumnsAfter(sh.getMaxColumns(), neededCols - sh.getMaxColumns());
    }

    sh.getRange(ANCHOR_ROW, ANCHOR_COL, 200, 6).breakApart().clearContent();

    sh.getRange(ANCHOR_ROW, ANCHOR_COL, 1, 6).merge().setValue('Все события ' + Utilities.formatDate(targetDate, Session.getScriptTimeZone(), 'dd.MM.yyyy') + ' — по убыванию уверенности')
      .setFontWeight('bold').setFontSize(13).setFontColor('white').setBackground('#1c4587');
    sh.getRange(ANCHOR_ROW + 1, ANCHOR_COL, 1, 6).setValues([['№', 'Тип', 'Матч', 'Прогноз', 'Увер., %', 'Статус']])
      .setFontWeight('bold').setBackground('#eef2fa');

    if (events.length === 0) {
      sh.getRange(ANCHOR_ROW + 2, ANCHOR_COL).setValue('На эту дату нет событий с прогнозом.');
    } else {
      var outRows = events.map(function (e, idx) {
        return [idx + 1, e.type, e.match, e.pick, e.conf, e.status || ''];
      });
      sh.getRange(ANCHOR_ROW + 2, ANCHOR_COL, outRows.length, 6).setValues(outRows);
      sh.getRange(ANCHOR_ROW, ANCHOR_COL, outRows.length + 2, 6).setBorder(true, true, true, true, true, true, '#b7b7b7', SpreadsheetApp.BorderStyle.SOLID);
    }

    sh.setColumnWidth(ANCHOR_COL + 2, 160); // Матч
    sh.setColumnWidth(ANCHOR_COL + 3, 130); // Прогноз

    uiAlert_(
      'Готово: список всех событий на ' + Utilities.formatDate(targetDate, Session.getScriptTimeZone(), 'dd.MM.yyyy') +
      ' (' + events.length + ' событий, победы и тоталы вместе) — смотрите таблицу справа от блока "Комбо" (столбец T).'
    );
  } catch (err) {
    uiAlert_('Ошибка в updateAllEventsForDay_: ' + err.message + '\n\n' + (err.stack || ''));
  }
}

/**
 * Список типов событий, которые понимает конструктор своего купона, и как
 * каждый из них считается:
 * - Победа Хозяев/Гостей — берём готовый % из листа "прогнозы".
 * - Тотал (матча / только хозяев / только гостей) Больше/Меньше линии —
 *   считаем через нормальное распределение вокруг уже посчитанного
 *   ожидаемого количества шайб (тот же принцип, что и обычный тотал в
 *   таблице, только тут можно указать ЛЮБУЮ линию, а не только 5.5).
 *   Стандартное отклонение — 2 шайбы для тотала матча, 1.4 для тотала
 *   одной команды: это оценка на глаз (типичный разброс числа шайб за
 *   игру в хоккее), не откалиброванная на наших данных отдельно.
 */
var MY_COUPON_EVENT_TYPES = [
  { label: 'Победа Хозяев', kind: 'winH' },
  { label: 'Победа Гостей', kind: 'winA' },
  { label: 'Тотал матча Больше', kind: 'over', col: 'total', std: 2 },
  { label: 'Тотал матча Меньше', kind: 'under', col: 'total', std: 2 },
  { label: 'Тотал Хозяев Больше', kind: 'over', col: 'goalsH', std: 1.4 },
  { label: 'Тотал Хозяев Меньше', kind: 'under', col: 'goalsH', std: 1.4 },
  { label: 'Тотал Гостей Больше', kind: 'over', col: 'goalsA', std: 1.4 },
  { label: 'Тотал Гостей Меньше', kind: 'under', col: 'goalsA', std: 1.4 },
  { label: 'Победа Хозяев + Тотал Больше', kind: 'winOver', win: 'H', col: 'total', std: 2 },
  { label: 'Победа Хозяев + Тотал Меньше', kind: 'winUnder', win: 'H', col: 'total', std: 2 },
  { label: 'Победа Гостей + Тотал Больше', kind: 'winOver', win: 'A', col: 'total', std: 2 },
  { label: 'Победа Гостей + Тотал Меньше', kind: 'winUnder', win: 'A', col: 'total', std: 2 }
];

/**
 * Создаёт лист "Мой купон" — конструктор, где вы сами выбираете из
 * выпадающих списков матч и тип события (победа команды, тотал с
 * произвольной линией — общий или отдельно по каждой команде, либо связка
 * победа+тотал). Саму вероятность здесь НЕ считают формулы ячеек — это
 * специально, после нескольких особенностей именно этой таблицы с
 * математическими функциями. Вероятность считает скрипт (кнопка
 * "Пересчитать мой купон") и просто вписывает готовое число.
 * Можно запускать повторно — лист пересоздаётся, введённый выбор теряется.
 */
function setupMyCouponBuilder_() {
  var ss = SpreadsheetApp.getActive();
  var progSh = ss.getSheetByName('прогнозы');
  if (!progSh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }

  // AW: метка матча "дата | хозяева — гости" для выпадающего списка —
  // показываем только ещё не сыгранные матчи (столбец K пока пуст)
  var lastRow = progSh.getLastRow();
  if (lastRow >= 2) {
    progSh.getRange('AW1').setValue('Метка матча (для купона)');
    progSh.getRange('AW2').setFormula('=IF(OR($A2="";$B2="");"";IF($K2<>"";"";TEXT($A2;"dd.mm.yyyy")&" | "&$B2&" — "&$C2))');
    if (lastRow > 2) progSh.getRange('AW2').copyTo(progSh.getRange(3, 49, lastRow - 2, 1));
  }

  var existing = ss.getSheetByName('Мой купон');
  if (existing) ss.deleteSheet(existing);
  var sh = ss.insertSheet('Мой купон', 1);
  sh.setHiddenGridlines(true);

  var TITLE_BG = '#1c4587', SECTION_BG = '#d9e1f2', BORDER = '#b7b7b7';

  sh.getRange('A1:D1').merge().setValue('🛠️  Конструктор своего купона')
    .setFontWeight('bold').setFontSize(18).setFontColor('white').setBackground(TITLE_BG).setVerticalAlignment('middle');
  sh.setRowHeight(1, 40);

  sh.getRange('A3:D3').merge()
    .setValue('Выбирайте матч, тип события и (для тоталов) линию из выпадающих списков (от 1.5 до 6.5). ' +
      'Затем нажмите в меню «Пересчитать мой купон», чтобы посчитать вероятность.')
    .setFontStyle('italic').setFontColor('#666666').setWrap(true);

  var HEADER_ROW = 5;
  sh.getRange(HEADER_ROW, 1, 1, 4).setValues([['Матч', 'Тип события', 'Линия (для тоталов)', 'Вероятность, %']])
    .setFontWeight('bold').setBackground(SECTION_BG);

  var matchRange = progSh.getRange('AW2:AW1600');
  var matchRule = SpreadsheetApp.newDataValidation().requireValueInRange(matchRange, true).setAllowInvalid(true).build();
  var typeLabels = MY_COUPON_EVENT_TYPES.map(function (e) { return e.label; });
  var typeRule = SpreadsheetApp.newDataValidation().requireValueInList(typeLabels, true).setAllowInvalid(true).build();

  var NUM_ROWS = 20;
  var firstDataRow = HEADER_ROW + 1;
  var lastDataRow = firstDataRow + NUM_ROWS - 1;

  sh.getRange(firstDataRow, 1, NUM_ROWS, 1).setDataValidation(matchRule).setBackground('#fff2cc');
  sh.getRange(firstDataRow, 2, NUM_ROWS, 1).setDataValidation(typeRule).setBackground('#fff2cc');
  // столбец C принудительно текстовый — иначе эта таблица воспринимает "3.5" как дату (3 мая),
  // а не как число 3.5; выпадающий список со строковыми значениями это полностью обходит
  sh.getRange(firstDataRow, 3, NUM_ROWS, 1).setNumberFormat('@');
  var lineValues = ['1.5', '2.5', '3.5', '4.5', '5.5', '6.5'];
  var lineRule = SpreadsheetApp.newDataValidation().requireValueInList(lineValues, true).setAllowInvalid(true).build();
  sh.getRange(firstDataRow, 3, NUM_ROWS, 1).setDataValidation(lineRule).setBackground('#fff2cc');
  sh.getRange(firstDataRow, 1, NUM_ROWS, 4).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  var summaryRow = lastDataRow + 2;
  sh.getRange(summaryRow, 1).setValue('Совместная вероятность купона:').setFontWeight('bold');
  sh.getRange(summaryRow + 1, 1).setValue('Эквивалентный коэффициент (справедливый):').setFontWeight('bold');

  sh.getRange(summaryRow + 3, 1, 1, 4).merge()
    .setValue('После выбора событий нажмите в меню «НХЛ-парсер» → «Пересчитать мой купон». ' +
      'Тоталы считаются по ожидаемому числу шайб с разумным разбросом (не откалибровано отдельно на данных).')
    .setFontStyle('italic').setFontColor('#666666').setWrap(true);

  sh.setColumnWidth(1, 260); sh.setColumnWidth(2, 220); sh.setColumnWidth(3, 150); sh.setColumnWidth(4, 120);
  sh.setFrozenRows(HEADER_ROW);

  uiAlert_(
    'Готово: лист "Мой купон" создан, ' + NUM_ROWS + ' строк для выбора событий. После выбора нажмите ' +
    '«Пересчитать мой купон» в меню, чтобы посчитать вероятность.'
  );
}

/**
 * Считает вероятность для каждой заполненной строки на листе "Мой купон" и
 * вписывает готовое число (не формулу) — вся математика делается в самом
 * скрипте, а не в ячейках, чтобы не зависеть от того, как именно эта
 * таблица трактует функции вроде NORMDIST. Плюс совместная вероятность и
 * справедливый коэффициент внизу.
 */
function recalcMyCoupon_() {
  try {
    var ss = SpreadsheetApp.getActive();
    var sh = ss.getSheetByName('Мой купон');
    var progSh = ss.getSheetByName('прогнозы');
    if (!sh) {
      uiAlert_('Не найден лист "Мой купон". Сначала запустите "Создать конструктор своего купона".');
      return;
    }
    if (!progSh) {
      uiAlert_('Не найден лист "прогнозы".');
      return;
    }

    var progLastRow = progSh.getLastRow();
    if (progLastRow < 2) {
      uiAlert_('На листе "прогнозы" нет строк с матчами.');
      return;
    }
    // A..C (дата/хозяева/гости), D/E (шансы %), G/H/I (ожид. голы Х/Г/тотал),
    // N (H2H встреч), P (H2H поправка), AC (поправка формы)
    var progData = progSh.getRange(2, 1, progLastRow - 1, 29).getValues();
    var tz = Session.getScriptTimeZone();

    var byLabel = {};
    for (var i = 0; i < progData.length; i++) {
      var row = progData[i];
      var date = row[0], home = row[1], away = row[2];
      if (!(date instanceof Date) || !home || !away) continue;
      var label = Utilities.formatDate(date, tz, 'dd.MM.yyyy') + ' | ' + home + ' — ' + away;
      byLabel[label] = {
        home: home, away: away,
        winHome: Number(row[3]), winAway: Number(row[4]),
        goalsH: Number(row[6]), goalsA: Number(row[7]), total: Number(row[8]),
        h2hGames: Number(row[13]), h2hAdj: Number(row[15]), formAdj: Number(row[28])
      };
    }

    var typeByLabel = {};
    MY_COUPON_EVENT_TYPES.forEach(function (et) { typeByLabel[et.label] = et; });

    var couponData = sh.getRange(6, 1, 20, 3).getValues(); // A-C, строки 6-25 (жёстко, как создаёт setup)
    var probs = [];
    var skipped = []; // диагностика: почему строка не посчиталась

    for (var r = 0; r < couponData.length; r++) {
      var rowNum = 6 + r;
      var matchLabel = couponData[r][0], typeLabel = couponData[r][1];
      var lineRaw = couponData[r][2];
      var line = (lineRaw === '' || lineRaw === null) ? '' : Number(String(lineRaw).replace(',', '.'));
      if (!matchLabel && !typeLabel) {
        sh.getRange(rowNum, 4).setValue('');
        continue; // строка просто не заполнена — не диагностика, а норма
      }
      if (!matchLabel || !typeLabel) {
        sh.getRange(rowNum, 4).setValue('');
        skipped.push('строка ' + rowNum + ': не выбраны и матч, и тип события вместе');
        continue;
      }
      var m = byLabel[matchLabel];
      var et = typeByLabel[typeLabel];
      if (!m) {
        sh.getRange(rowNum, 4).setValue('');
        skipped.push('строка ' + rowNum + ': матч "' + matchLabel + '" не найден на листе "прогнозы" (сыгран или расхождение в тексте)');
        continue;
      }
      if (!et) {
        sh.getRange(rowNum, 4).setValue('');
        skipped.push('строка ' + rowNum + ': тип события "' + typeLabel + '" не распознан');
        continue;
      }

      var needsLine = (et.kind !== 'winH' && et.kind !== 'winA');
      if (needsLine && (line === '' || line === null || isNaN(line))) {
        sh.getRange(rowNum, 4).setValue('');
        skipped.push('строка ' + rowNum + ': для этого типа события нужна линия в столбце C, а она пуста');
        continue;
      }

      var expVal = et.col === 'total' ? m.total : (et.col === 'goalsH' ? m.goalsH : m.goalsA);
      var logistic = function (x) { return 1 / (1 + Math.exp(-1.702 * x)); };
      var pOver = function (lineVal, mean, std) { return 1 - logistic((lineVal - mean) / std); };
      var pUnder = function (lineVal, mean, std) { return logistic((lineVal - mean) / std); };

      var p;
      if (et.kind === 'winH') p = m.winHome;
      else if (et.kind === 'winA') p = m.winAway;
      else if (et.kind === 'over') p = pOver(Number(line), expVal, et.std);
      else if (et.kind === 'under') p = pUnder(Number(line), expVal, et.std);
      else if (et.kind === 'winOver') p = (et.win === 'H' ? m.winHome : m.winAway) * pOver(Number(line), expVal, et.std);
      else p = (et.win === 'H' ? m.winHome : m.winAway) * pUnder(Number(line), expVal, et.std); // winUnder

      if (isNaN(p)) {
        sh.getRange(rowNum, 4).setValue('');
        skipped.push('строка ' + rowNum + ': расчёт дал не число (проверьте, что в "прогнозы" для этого матча заполнены нужные столбцы)');
        continue;
      }
      var pct = Math.round(p * 1000) / 10;
      sh.getRange(rowNum, 4).setValue(pct);
      probs.push(p);
    }

    var summaryRow = 27;
    var combined = probs.length > 0 ? probs.reduce(function (a, b) { return a * b; }, 1) : 0;
    sh.getRange(summaryRow, 4).setValue(probs.length > 0 ? Math.round(combined * 10000) / 100 : '').setFontWeight('bold');
    sh.getRange(summaryRow + 1, 4).setValue(combined > 0 ? Math.round((1 / combined) * 100) / 100 : '').setFontWeight('bold');

    var msg = 'Готово: пересчитано ' + probs.length + ' событий. Совместная вероятность — внизу листа.';
    if (skipped.length > 0) {
      msg += '\n\nНе получилось для:\n' + skipped.join('\n');
    }
    uiAlert_(msg);
  } catch (err) {
    uiAlert_('Ошибка в recalcMyCoupon_: ' + err.message + '\n\n' + (err.stack || ''));
  }
}

var SHOTS_STATS_URL = 'https://www.sports.ru/hockey/tournament/khl/stat/';


/**
 * Подключает поправку по эффективности реализации бросков к статистике
 * каждой команды. ВАЖНО: поправка вносится на уровне листа Data (столбец U,
 * "Забито за игру, с учётом бросков") — по каждой команде отдельно, а НЕ на
 * уровне прогнозы!G/H, потому что те столбцы уже смешивают показатели ОБЕИХ
 * команд конкретного матча и не являются "своей" статистикой одной команды.
 * Использует лист "Броски_кэш" (собирается отдельной кнопкой) — для команд
 * без данных поправка не применяется (используется исходное значение
 * Data!I как есть). После установки переключает прогнозы!G/H на новый
 * столбец Data!U вместо исходного Data!I.
 * Можно запускать повторно.
 */
function setupShotsAdjustmentFormulas_() {
  var ss = SpreadsheetApp.getActive();
  var dataSh = ss.getSheetByName('Data');
  var progSh = ss.getSheetByName('прогнозы');
  var shotsSh = ss.getSheetByName('Броски_кэш');
  if (!dataSh || !progSh) {
    uiAlert_('Не найден лист "Data" или "прогнозы".');
    return;
  }
  if (!shotsSh) {
    uiAlert_('Сначала нажмите "Обновить статистику бросков" — лист "Броски_кэш" ещё не создан.');
    return;
  }

  var lastShotsRow = shotsSh.getLastRow();
  shotsSh.getRange('D1').setValue('Средний Б/Г по лиге:');
  shotsSh.getRange('E1').setFormula('=IFERROR(AVERAGE(B2:B' + lastShotsRow + ');"")');

  var SHOTS_WEIGHT = '3/10'; // вес поправки по броскам в смеси с фактическими голами (30%)

  // Data занимает строки 2-23 (22 команды) — тот же диапазон, что используют
  // остальные формулы, ссылающиеся на Data!$A$2:$A$33
  dataSh.getRange('U1').setValue('Забито за игру (с учётом бросков)');
  var formulaU =
    '=IFERROR(' +
      'IF(ISNA(MATCH($A2;\'Броски_кэш\'!$A$2:$A$' + lastShotsRow + ';0));' +
        'I2;' + // нет данных по броскам для этой команды — используем фактическую ЗГ как есть
        'I2*(1-' + SHOTS_WEIGHT + ')+I2*(INDEX(\'Броски_кэш\'!$B$2:$B$' + lastShotsRow + ';MATCH($A2;\'Броски_кэш\'!$A$2:$A$' + lastShotsRow + ';0))/\'Броски_кэш\'!$E$1)*' + SHOTS_WEIGHT +
      ');' +
    'I2)';
  dataSh.getRange('U2').setFormula(formulaU);
  dataSh.getRange('U2').copyTo(dataSh.getRange(3, 21, 21, 1)); // строки 3-23

  // переключаем прогнозы!G (Ожид. голы Хозяев) на Data!U вместо Data!I —
  // H (Ожид. голы Гостей) по-прежнему использует Data!J (пропущено за игру
  // соперника) без изменений, поправка по броскам это только про свою реализацию
  var progLastRow = progSh.getLastRow();
  if (progLastRow >= 2) {
    var formulaG = '=IFERROR(ROUND((INDEX(Data!$U$2:$U$33;MATCH(B2;Data!$A$2:$A$33;0))+INDEX(Data!$J$2:$J$33;MATCH(C2;Data!$A$2:$A$33;0)))/2;2);"")';
    var formulaH = '=IFERROR(ROUND((INDEX(Data!$U$2:$U$33;MATCH(C2;Data!$A$2:$A$33;0))+INDEX(Data!$J$2:$J$33;MATCH(B2;Data!$A$2:$A$33;0)))/2;2);"")';
    setFormulaOnOpenRows_(progSh, 7, formulaG.replace(/([(;+\-\s])([BCGHIJ])2(?![0-9])/g, '$1$2{R}'), openPredictionRows_(progSh));
    setFormulaOnOpenRows_(progSh, 8, formulaH.replace(/([(;+\-\s])([BCGHIJ])2(?![0-9])/g, '$1$2{R}'), openPredictionRows_(progSh));
  }

  uiAlert_(
    'Готово: столбец Data!U ("Забито за игру, с учётом бросков") добавлен для каждой команды, ' +
    'и столбцы G/H на листе "прогнозы" (Ожид. голы) теперь используют его вместо исходного Data!I. ' +
    'Вес поправки — 30%, для команд без данных по броскам используется фактическая ЗГ как есть.'
  );
}

/**
 * Приводит столбец "Дата" на листе "прогнозы" к единому виду (дд.мм.гггг —
 * иначе строки, где дата хранится по-разному, отображаются то коротко, то
 * полной датой со временем), и добавляет условное форматирование: строка
 * сегодняшнего дня подсвечивается автоматически (обновляется само по себе
 * день за днём, ничего не нужно трогать руками).
 * Можно запускать повторно — старое условное форматирование этого правила
 * каждый раз убирается и ставится заново, остальные не трогаются.
 */
function formatPredictionsDatesAndHighlight_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }
  var lastRow = sh.getLastRow();
  var lastCol = sh.getLastColumn();
  if (lastRow < 2) {
    uiAlert_('На листе "прогнозы" нет строк с матчами.');
    return;
  }

  // единый формат отображения даты
  sh.getRange(2, 1, lastRow - 1, 1).setNumberFormat('dd.mm.yyyy');

  // условное форматирование — своё правило для этого листа, не трогаем чужие
  var range = sh.getRange(2, 1, lastRow - 1, lastCol);
  var rules = sh.getConditionalFormatRules();
  // убираем прежнее правило этой же функции, если уже было (узнаём по тому же диапазону старта A2)
  rules = rules.filter(function (r) {
    var ranges = r.getRanges();
    return !(ranges.length === 1 && ranges[0].getColumn() === 1 && ranges[0].getRow() === 2);
  });
  var todayRule = SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=$A2=TODAY()')
    .setBackground('#fff2cc')
    .setRanges([range])
    .build();
  rules.push(todayRule);
  sh.setConditionalFormatRules(rules);

  uiAlert_(
    'Готово: даты приведены к единому виду (дд.мм.гггг), сегодняшние матчи подсвечены. ' +
    'Подсветка автоматически переходит на новый день сам по себе — ничего обновлять руками не нужно.'
  );
}


/**
 * Считает результативность каждой команды ОТДЕЛЬНО дома и в гостях (не общую
 * смесь, как было раньше) — команда может забивать заметно больше в одной
 * из ситуаций. Пишет в Data столбцы V-Y (сырые значения) и, если уже
 * подключена поправка по броскам (лист "Броски_кэш" существует), ещё и
 * Z/AA — те же значения, но с той же 30%-й поправкой на эффективность
 * реализации, что и в общей версии. Затем переключает прогнозы!G/H на эти
 * раздельные (и, если есть, смешанные с бросками) столбцы.
 * Можно запускать повторно — полностью пересчитывает всё заново.
 */
function setupHomeAwayScoringSplit_() {
  var ss = SpreadsheetApp.getActive();
  var dataSh = ss.getSheetByName('Data');
  var progSh = ss.getSheetByName('прогнозы');
  var resultsSh = ss.getSheetByName(SHEET_RESULTS);
  if (!dataSh || !progSh || !resultsSh) {
    uiAlert_('Не найден лист "Data", "прогнозы" или "' + SHEET_RESULTS + '".');
    return;
  }

  // на случай, если где-то в этой области случайно есть объединённые ячейки —
  // разъединяем сразу весь широкий диапазон одним вызовом
  dataSh.getRange(1, 1, 200, 40).breakApart();
  progSh.getRange(1, 1, 400, 40).breakApart();

  var resData = resultsSh.getDataRange().getValues();
  var header = resData[0];
  var col = {
    status: header.indexOf('Статус'), home: header.indexOf('Хозяева'), away: header.indexOf('Гости'),
    hg: header.indexOf('Г Хозяев'), ag: header.indexOf('Г Гостей')
  };

  var stats = {}; // команда -> {homeGF,homeGA,homeGames,awayGF,awayGA,awayGames}
  for (var r = 1; r < resData.length; r++) {
    if (String(resData[r][col.status]).trim() !== 'Сыгран') continue;
    var home = String(resData[r][col.home]).trim(), away = String(resData[r][col.away]).trim();
    var hg = Number(resData[r][col.hg]), ag = Number(resData[r][col.ag]);
    if (!home || !away || isNaN(hg) || isNaN(ag)) continue;
    if (!stats[home]) stats[home] = { homeGF: 0, homeGA: 0, homeGames: 0, awayGF: 0, awayGA: 0, awayGames: 0 };
    if (!stats[away]) stats[away] = { homeGF: 0, homeGA: 0, homeGames: 0, awayGF: 0, awayGA: 0, awayGames: 0 };
    stats[home].homeGF += hg; stats[home].homeGA += ag; stats[home].homeGames++;
    stats[away].awayGF += ag; stats[away].awayGA += hg; stats[away].awayGames++;
  }

  // читаем текущее состояние Data целиком — нужны столбцы I (ЗГ за игру, общее),
  // J (ПГ за игру, общее) и, если уже посчитан, U (ЗГ с учётом бросков, общее)
  var dataData = dataSh.getDataRange().getValues();
  var teamOrder = [];
  var overallGF = {}, overallGA = {};
  for (var i = 1; i < dataData.length; i++) {
    var n = String(dataData[i][0]).trim();
    if (!n) continue;
    teamOrder.push(n);
    var uVal = dataData[i][20]; // столбец U (индекс 20, т.к. массив с нуля) — ЗГ с учётом бросков, если есть
    var iVal = dataData[i][8];  // столбец I — ЗГ за игру, общее (сырое)
    var jVal = dataData[i][9];  // столбец J — ПГ за игру, общее
    overallGF[n] = (typeof uVal === 'number' && uVal !== '') ? uVal : (typeof iVal === 'number' ? iVal : 0);
    overallGA[n] = (typeof jVal === 'number') ? jVal : 0;
  }

  // статистика бросков (если уже собрана) — читаем прямо сейчас, а не формулой в ячейке
  var shotsSh = ss.getSheetByName('Броски_кэш');
  var shotsByTeam = {}, leagueAvgBG = null;
  if (shotsSh) {
    var shotsData = shotsSh.getDataRange().getValues();
    var bgValues = [];
    for (var sIdx = 1; sIdx < shotsData.length; sIdx++) {
      var sTeam = String(shotsData[sIdx][0]).trim();
      var sVal = Number(shotsData[sIdx][1]);
      if (sTeam && !isNaN(sVal)) { shotsByTeam[sTeam] = sVal; bgValues.push(sVal); }
    }
    if (bgValues.length > 0) leagueAvgBG = bgValues.reduce(function (a, b) { return a + b; }, 0) / bgValues.length;
  }

  var CONFIDENCE_CAP = 6 / 10;   // раздельная статистика никогда не весит больше 60% даже при большой выборке
  var CONFIDENCE_GAMES = 8;      // столько игр каждого типа (дома/в гостях) нужно для выхода на потолок уверенности
  var SHOTS_WEIGHT = 3 / 10;

  dataSh.getRange('V1:AC1').setValues([[
    'ЗГ дома, сырое', 'ПГ дома, сырое', 'ЗГ в гостях, сырое', 'ПГ в гостях, сырое',
    'ЗГ дома, итог', 'ЗГ в гостях, итог', 'ПГ дома, итог', 'ПГ в гостях, итог'
  ]]);

  var rows = teamOrder.map(function (t) {
    var s = stats[t] || { homeGF: 0, homeGA: 0, homeGames: 0, awayGF: 0, awayGA: 0, awayGames: 0 };
    var homeGFraw = s.homeGames > 0 ? s.homeGF / s.homeGames : null;
    var homeGAraw = s.homeGames > 0 ? s.homeGA / s.homeGames : null;
    var awayGFraw = s.awayGames > 0 ? s.awayGF / s.awayGames : null;
    var awayGAraw = s.awayGames > 0 ? s.awayGA / s.awayGames : null;

    var homeConf = Math.min(CONFIDENCE_CAP, s.homeGames / CONFIDENCE_GAMES);
    var awayConf = Math.min(CONFIDENCE_CAP, s.awayGames / CONFIDENCE_GAMES);

    // поправка по броскам применяется только к своей результативности (не к пропускаемости)
    var applyShotsAdj = function (val) {
      if (val === null || !shotsByTeam.hasOwnProperty(t) || !leagueAvgBG) return val;
      return val * (1 - SHOTS_WEIGHT) + val * (shotsByTeam[t] / leagueAvgBG) * SHOTS_WEIGHT;
    };

    var homeGFshots = applyShotsAdj(homeGFraw);
    var awayGFshots = applyShotsAdj(awayGFraw);

    var finalHomeGF = homeGFraw === null ? overallGF[t] : (homeGFshots * homeConf + overallGF[t] * (1 - homeConf));
    var finalAwayGF = awayGFraw === null ? overallGF[t] : (awayGFshots * awayConf + overallGF[t] * (1 - awayConf));
    var finalHomeGA = homeGAraw === null ? overallGA[t] : (homeGAraw * homeConf + overallGA[t] * (1 - homeConf));
    var finalAwayGA = awayGAraw === null ? overallGA[t] : (awayGAraw * awayConf + overallGA[t] * (1 - awayConf));

    var r2 = function (x) { return Math.round(x * 100) / 100; };
    return [
      homeGFraw === null ? '' : r2(homeGFraw), homeGAraw === null ? '' : r2(homeGAraw),
      awayGFraw === null ? '' : r2(awayGFraw), awayGAraw === null ? '' : r2(awayGAraw),
      r2(finalHomeGF), r2(finalAwayGF), r2(finalHomeGA), r2(finalAwayGA)
    ];
  });
  dataSh.getRange(2, 22, rows.length, 8).setValues(rows); // V=22..AC=29

  var progLastRow = progSh.getLastRow();
  if (progLastRow >= 2) {
    // G2 (Ожид. голы Хозяев) = ЗГ дома хозяев, итог (Z) + ПГ в гостях гостей, итог (AC), пополам
    // H2 (Ожид. голы Гостей) = ЗГ в гостях гостей, итог (AA) + ПГ дома хозяев, итог (AB), пополам
    var formulaG = '=IFERROR(ROUND((INDEX(Data!$Z$2:$Z$33;MATCH(B2;Data!$A$2:$A$33;0))+INDEX(Data!$AC$2:$AC$33;MATCH(C2;Data!$A$2:$A$33;0)))/2;2);"")';
    var formulaH = '=IFERROR(ROUND((INDEX(Data!$AA$2:$AA$33;MATCH(C2;Data!$A$2:$A$33;0))+INDEX(Data!$AB$2:$AB$33;MATCH(B2;Data!$A$2:$A$33;0)))/2;2);"")';
    setFormulaOnOpenRows_(progSh, 7, formulaG.replace(/([(;+\-\s])([BCGHIJ])2(?![0-9])/g, '$1$2{R}'), openPredictionRows_(progSh));
    setFormulaOnOpenRows_(progSh, 8, formulaH.replace(/([(;+\-\s])([BCGHIJ])2(?![0-9])/g, '$1$2{R}'), openPredictionRows_(progSh));
  }

  uiAlert_(
    'Готово: результативность дома/в гостях посчитана раздельно для ' + teamOrder.length + ' команд, ' +
    'с поправкой на уверенность (вес раздельной статистики растёт по мере накопления игр каждого типа, ' +
    'максимум 60%, минимум 8 игр для выхода на потолок)' + (shotsSh ? ' и поправкой по броскам' : '') + '. ' +
    'Пока игр мало, "Ожидаемые голы" будут близки к общей (несмешанной) статистике — так и задумано, ' +
    'это устраняет как раз ту нестыковку с шансами победы, которую вы заметили.'
  );
}

/**
 * Симулирует, как менялся бы условный банк, если бы вы ставили на самый
 * вероятный исход КАЖДОГО сыгранного матча, каждый раз определённым
 * процентом от ТЕКУЩЕГО банка (не фиксированной суммой — банк растёт/падает,
 * а размер ставки пересчитывается от нового баланса).
 *
 * Коэффициент: если в столбцах AE/AF (Кэф. букмекера) вписан реальный
 * коэффициент вручную — используется он. Если пусто — считается УСЛОВНЫЙ
 * коэффициент из вероятности самой модели с обычной букмекерской маржой (7%)
 * — это оценка, а не реальная рыночная цена, помечается отдельным столбцом.
 *
 * Ставка процентом от банка математически никогда не обнуляет его полностью
 * (после серии проигрышей банк просто становится очень маленьким, но не
 * ровно нулём) — это свойство именно такой схемы ставок, а не баг.
 *
 * Настройки — ячейки B1 (стартовый банк) и B2 (% ставки от банка) на самом
 * листе "Банкролл": можно менять и запускать функцию заново.
 * Можно запускать повторно — лист каждый раз пересчитывается с нуля.
 */
function updateBankrollSimulation_() {
  var ss = SpreadsheetApp.getActive();
  var progSh = ss.getSheetByName('прогнозы');
  if (!progSh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }

  var BOOKMAKER_MARGIN = 7 / 100; // условная маржа букмекера для расчётного коэффициента, если реального нет
  var headerRow = 4;

  var sh = ss.getSheetByName('Банкролл');
  var startBankroll = 2000, betPercent = 2 / 100;
  var stakeLowered = false;
  var manualOverrides = {}; // "ключ матча" -> вручную вписанный коэффициент (сохраняем при пересборке)
  var debugInfo = 'Диагностика сохранения правок:\n';
  if (sh) {
    var b1 = sh.getRange('B1').getValue();
    var b2 = sh.getRange('B2').getValue();
    if (typeof b1 === 'number' && b1 > 0) startBankroll = b1;
    if (typeof b2 === 'number' && b2 > 0 && b2 <= 1) betPercent = b2;
    else if (typeof b2 === 'number' && b2 > 1) betPercent = b2 / 100; // на случай, если ввели 25 вместо 0.25
    // Прежнее значение по умолчанию — 25% банка на одну ставку. При такой доле пара неудачных дней
    // обнуляет счёт, а любая удачная серия раздувает итог в разы, поэтому один раз меняем его на 2%.
    // Если вы осознанно поставите другое число, оно сохранится.
    if (Math.abs(betPercent - 0.25) < 1e-9) { betPercent = 0.02; stakeLowered = true; }

    // читаем существующие строки ДО пересборки — если коэффициент отличается от того,
    // что скрипт сам вычислил бы, или уже помечен как "ручной" — считаем его правкой
    // пользователя и сохраняем, чтобы не затереть при пересчёте
    var lastRow = sh.getLastRow();
    debugInfo += '- lastRow на листе: ' + lastRow + ' (headerRow=' + headerRow + ')\n';
    if (lastRow > headerRow) {
      var oldRows = sh.getRange(headerRow + 1, 1, lastRow - headerRow, 11).getValues();
      var nonEmptyOld = 0;
      oldRows.forEach(function (row) {
        if (!row[1]) return; // пустая строка (в пределах старого диапазона форматирования, но без данных)
        nonEmptyOld++;
        var key = dateOnlyKey_(row[0]) + '|' + row[1];
        var oldOdds = Number(row[6]), oldSource = row[7];
        if (!isNaN(oldOdds) && oldOdds > 0) {
          manualOverrides[key] = { odds: oldOdds, wasManual: (oldSource === 'ручной') };
        }
      });
      debugInfo += '- Прочитано непустых старых строк: ' + nonEmptyOld + ', из них с числом в G: ' + Object.keys(manualOverrides).length + '\n';
      var sampleKeys = Object.keys(manualOverrides).slice(0, 2);
      debugInfo += '- Пример ключей: ' + JSON.stringify(sampleKeys) + '\n';
    }
  }

  var data = progSh.getDataRange().getValues();
  var header = data[0];
  var col = {
    date: header.indexOf('Дата'), home: header.indexOf('Хозяева'), away: header.indexOf('Гости'),
    chH: header.indexOf('Шансы Хозяев, %'), chA: header.indexOf('Шансы Гостей, %'),
    result: header.indexOf('Прогноз сбылся?'),
    oddsH: header.indexOf('Кэф. букмекера (Хозяева) — вводить вручную'),
    oddsA: header.indexOf('Кэф. букмекера (Гости) — вводить вручную'),
    integrity: header.indexOf('Честный прогноз?')
  };

  var rows = [];
  var excluded = 0;
  for (var r = 1; r < data.length; r++) {
    var mark = data[r][col.result];
    if (mark !== '✅' && mark !== '❌') continue; // берём только уже разрешённые (сыгранные) матчи
    // Прогнозы, испорченные утечкой (пересчитаны уже после результата), в симуляцию не берём:
    // сторона ставки в них выбрана «с подсказкой», и на них набегала почти вся прежняя прибыль.
    if (col.integrity !== -1 && String(data[r][col.integrity]).trim() === 'нет') { excluded++; continue; }
    var chH = Number(data[r][col.chH]), chA = Number(data[r][col.chA]);
    if (isNaN(chH) || isNaN(chA)) continue;
    rows.push({
      date: data[r][col.date], home: data[r][col.home], away: data[r][col.away],
      chH: chH, chA: chA, won: (mark === '✅'),
      oddsH: Number(data[r][col.oddsH]) || null, oddsA: Number(data[r][col.oddsA]) || null
    });
  }
  rows.sort(function (a, b) {
    return dateOnlyKey_(a.date) < dateOnlyKey_(b.date) ? -1 : (dateOnlyKey_(a.date) > dateOnlyKey_(b.date) ? 1 : 0);
  });

  var bankroll = startBankroll;
  var outRows = [];
  var wins = 0, losses = 0;
  var firstMatchDebugCaptured = false;

  rows.forEach(function (m) {
    var favoredHome = m.chH >= m.chA;
    var probability = favoredHome ? m.chH : m.chA;
    var favoredTeam = favoredHome ? m.home : m.away;
    var realOdds = favoredHome ? m.oddsH : m.oddsA;
    var usedFallback = !realOdds;
    var computedOdds = realOdds || (1 / probability) * (1 - BOOKMAKER_MARGIN);
    var computedSource = usedFallback ? 'расчётный' : 'реальный';

    var matchKey = dateOnlyKey_(m.date) + '|' + m.home + ' — ' + m.away;
    var prev = manualOverrides[matchKey];
    var odds = computedOdds, source = computedSource;
    if (prev) {
      var differsFromComputed = Math.abs(prev.odds - computedOdds) > 0.005;
      if (prev.wasManual || differsFromComputed) {
        odds = prev.odds;
        source = 'ручной';
      }
    }

    if (!firstMatchDebugCaptured) {
      firstMatchDebugCaptured = true;
      debugInfo += '- Ключ 1-го матча сейчас: "' + matchKey + '"\n';
      debugInfo += '- Найдено совпадение в старых данных? ' + (prev ? 'да, старое G=' + prev.odds : 'нет') + '\n';
      debugInfo += '- Свежерассчитанный коэф.: ' + Math.round(computedOdds * 100) / 100 + ', итоговый источник: ' + source + '\n';
    }

    var bankBefore = bankroll;
    var bet = Math.round(bankBefore * betPercent * 100) / 100;
    var profit;
    if (m.won) {
      profit = Math.round(bet * (odds - 1) * 100) / 100;
      bankroll += profit;
      wins++;
    } else {
      profit = -bet;
      bankroll -= bet;
      losses++;
    }
    bankroll = Math.round(bankroll * 100) / 100;

    outRows.push([
      m.date, m.home + ' — ' + m.away, favoredTeam,
      Math.round(probability * 1000) / 10, bankBefore, bet,
      Math.round(odds * 100) / 100, source,
      m.won ? '✅' : '❌', profit, bankroll
    ]);
  });

  if (!sh) sh = ss.insertSheet('Банкролл'); else sh.clearContents();
  sh.getRange(1, 1, 200, 20).breakApart();

  sh.getRange('A1').setValue('Стартовый банк, ₽:');
  sh.getRange('B1').setValue(startBankroll);
  sh.getRange('A2').setValue('Ставка, доля от банка (0-1):');
  sh.getRange('B2').setValue(betPercent);
  sh.getRange('D1').setValue('Итоговый банк, ₽:');
  sh.getRange('E1').setValue(bankroll).setFontWeight('bold');
  sh.getRange('D2').setValue('Изменение банка:');
  sh.getRange('E2').setValue((bankroll >= startBankroll ? '+' : '') + Math.round((bankroll / startBankroll - 1) * 1000) / 10 + '%').setFontWeight('bold');
  sh.getRange('G1').setValue('Ставок всего / угадано:');
  sh.getRange('H1').setValue(outRows.length + ' / ' + wins + ' (' + (outRows.length ? Math.round(wins / outRows.length * 1000) / 10 : 0) + '%)');
  sh.getRange('G2').setValue('Исключено (прогноз испорчен утечкой):');
  sh.getRange('H2').setValue(excluded);
  var computedCount = outRows.filter(function (r) { return r[7] === 'расчётный'; }).length;
  sh.getRange('A3:K3').merge().setWrap(true).setFontStyle('italic').setFontColor('#b00020').setValue(
    computedCount > 0
      ? 'Важно: у ' + computedCount + ' из ' + outRows.length + ' ставок коэффициент расчётный — выведен из вероятности самой модели ' +
        'за вычетом маржи букмекера. У такой ставки ожидаемый результат заранее минус 7%, поэтому итог этого листа ' +
        'показывает только, как часто модель угадывает, а не выгодна ли она на деле. Проверить выгодность можно ' +
        'только по настоящим коэффициентам букмекера — впишите их в столбец G.'
      : 'Все коэффициенты вписаны вручную — итог отражает реальный результат ставок по ним.');
  sh.setRowHeight(3, 48);

  sh.getRange(headerRow, 1, 1, 11).setValues([[
    'Дата', 'Матч', 'Ставили на', 'Вероятность, %', 'Банк до', 'Размер ставки',
    'Коэффициент (можно вписать своё)', 'Коэф. — источник', 'Исход', 'Прибыль/убыток', 'Банк после'
  ]]).setFontWeight('bold');

  if (outRows.length > 0) {
    sh.getRange(headerRow + 1, 1, outRows.length, 11).setValues(outRows);
    sh.getRange(headerRow, 1, outRows.length + 1, 11).setBorder(true, true, true, true, true, true, '#b7b7b7', SpreadsheetApp.BorderStyle.SOLID);
    sh.getRange(headerRow + 1, 7, outRows.length, 1).setBackground('#fff2cc'); // подсвечиваем столбец G как редактируемый
  }

  sh.setColumnWidth(2, 220); sh.setColumnWidth(3, 150); sh.setColumnWidth(7, 190); sh.setColumnWidth(8, 130);
  sh.setFrozenRows(headerRow);

  uiAlert_(
    'Готово: симуляция по ' + outRows.length + ' сыгранным матчам с честным прогнозом' +
    (excluded ? ' (ещё ' + excluded + ' исключены: их прогноз испорчен утечкой)' : '') + '.\n\n' +
    'Стартовый банк: ' + startBankroll + ' ₽ → итоговый: ' + bankroll + ' ₽ (' +
    (bankroll >= startBankroll ? '+' : '') + Math.round((bankroll / startBankroll - 1) * 1000) / 10 + '%), ставка ' +
    Math.round(betPercent * 1000) / 10 + '% банка.\n\n' +
    (stakeLowered ? 'Доля ставки снижена с 25% до 2%: при 25% пара неудачных дней обнуляет банк, а удачная серия раздувает итог в разы. ' +
                    'Своё значение можно вписать в B2.\n\n' : '') +
    'Помните: пока коэффициенты расчётные, этот лист проверяет угадываемость, а не выгодность — подробности в строке 3.'
  );
}

/**
 * Добавляет на лист "прогнозы" условное форматирование, подсвечивающее ещё
 * не сыгранные ("горячие") матчи по трём независимым критериям — каждый
 * своим цветом, применяется только к строкам без вердикта (столбец K пуст):
 *   - золотой: найден Value 8 п.п.+ хотя бы на одной стороне (если вписан
 *     коэффициент букмекера в AE/AF)
 *   - голубой: модель очень уверена в фаворите (80%+)
 *   - оранжевый: почти монетка (45-55%) — самый непредсказуемый матч тура
 * Не трогает уже существующее правило подсветки "сегодняшнего дня" —
 * добавляет свои правила рядом с ним, не заменяя.
 * Можно запускать повторно — свои три правила каждый раз переставляются
 * заново (по диапазону старта совпадающему с этой функцией), чужие не трогает.
 */
function highlightHotMatches_() {
  try {
    var ss = SpreadsheetApp.getActive();
    var sh = ss.getSheetByName('прогнозы');
    if (!sh) {
      uiAlert_('Не найден лист "прогнозы".');
      return;
    }
    var lastRow = sh.getLastRow();
    var lastCol = sh.getLastColumn();
    if (lastRow < 2) {
      uiAlert_('На листе "прогнозы" нет строк с матчами.');
      return;
    }

    var range = sh.getRange(2, 1, lastRow - 1, lastCol);
    var existingRules = sh.getConditionalFormatRules();
    var existingCount = existingRules.length;

    var isOwnRule = function (r) {
      try {
        var cond = r.getBooleanCondition();
        if (!cond) return false;
        var values = cond.getCriteriaValues();
        if (!values || values.length === 0) return false;
        var f = String(values[0]);
        return f.indexOf('$D2-1/$AE2>=0.08') !== -1 || f.indexOf('$D2>=0.8;$E2>=0.8') !== -1 || f.indexOf('$D2>=0.45;$D2<=0.55') !== -1;
      } catch (innerErr) {
        return false; // если конкретное правило не удалось прочитать — просто не считаем его своим, не роняем всю функцию
      }
    };
    var rules = existingRules.filter(function (r) { return !isOwnRule(r); });
    var removedCount = existingCount - rules.length;

    var valueRule = SpreadsheetApp.newConditionalFormatRule()
      .whenFormulaSatisfied(
        '=AND(LEN($K2)=0;OR(' +
          'AND(LEN($AE2)>0;ISNUMBER($AE2);$D2-1/$AE2>=0.08);' +
          'AND(LEN($AF2)>0;ISNUMBER($AF2);$E2-1/$AF2>=0.08)' +
        '))'
      )
      .setBackground('#ffd966')
      .setRanges([range])
      .build();

    var highConfRule = SpreadsheetApp.newConditionalFormatRule()
      .whenFormulaSatisfied('=AND(LEN($K2)=0;OR($D2>=0.8;$E2>=0.8))')
      .setBackground('#c9daf8')
      .setRanges([range])
      .build();

    var coinFlipRule = SpreadsheetApp.newConditionalFormatRule()
      .whenFormulaSatisfied('=AND(LEN($K2)=0;$D2>=0.45;$D2<=0.55)')
      .setBackground('#f9cb9c')
      .setRanges([range])
      .build();

    rules.unshift(valueRule, highConfRule, coinFlipRule); // в начало списка — чтобы наши правила имели приоритет над остальными
    sh.setConditionalFormatRules(rules);

    // перечитываем правила с самого листа, чтобы подтвердить, что запись реально прошла,
    // а не просто не упала с ошибкой
    var verifyRules = sh.getConditionalFormatRules();

    // список формул "чужих" правил (не наших трёх) — если подсветка всё равно не видна,
    // это покажет, что именно может её перекрывать
    var foreignFormulas = [];
    existingRules.forEach(function (r) {
      if (isOwnRule(r)) return;
      try {
        var c = r.getBooleanCondition();
        if (c) {
          var v = c.getCriteriaValues();
          foreignFormulas.push(v && v[0] ? String(v[0]) : '(правило без формулы, другой тип условия)');
        } else {
          foreignFormulas.push('(не формула — вероятно, градиентная заливка по цвету)');
        }
      } catch (e2) {
        foreignFormulas.push('(не удалось прочитать это правило)');
      }
    });

    uiAlert_(
      'Готово. Свои правила переставлены В НАЧАЛО списка — теперь у них приоритет над остальными.\n\n' +
      'ДИАГНОСТИКА:\n' +
      '- Правил было до запуска: ' + existingCount + '\n' +
      '- Из них своих (убрано перед повторной вставкой): ' + removedCount + '\n' +
      '- Правил после сборки для записи: ' + rules.length + '\n' +
      '- Правил реально на листе после записи (перечитано): ' + verifyRules.length + '\n' +
      '- Диапазон применения: строки 2-' + lastRow + ', столбцы 1-' + lastCol + '\n\n' +
      'Формулы "чужих" правил (' + foreignFormulas.length + ' шт.), которые могли мешать раньше:\n' +
      foreignFormulas.join('\n') + '\n\n' +
      'Проверьте теперь строку с матчем Сочи — Ак Барс (85.5% за Ак Барс) — должна стать голубой.'
    );
  } catch (err) {
    uiAlert_('Ошибка в highlightHotMatches_: ' + err.message + '\n\n' + (err.stack || ''));
  }
}

/**
 * Полностью убирает из листа "прогнозы" всё, что было связано с ручным
 * вводом коэффициентов букмекера (решили отказаться от идеи — ручной ввод
 * оказался неинтересен):
 *   - столбец J возвращается к исходному смыслу "Ожид. разница (Х-Г)"
 *   - столбцы AE-AH (коэффициенты итоговой победы + Value) очищаются
 *   - столбцы AX-BB (доп. рынки П1/Х/П2, 1Х/2Х) очищаются
 *   - все столбцы показываются обратно, закрепление снимается
 * Симуляция банкролла и подсветка горячих матчей продолжат работать —
 * они уже устроены так, чтобы без реальных коэффициентов просто переходить
 * на расчётный (из вероятности модели) вариант вместо реального.
 * Можно запускать повторно — безопасно, если уже почищено.
 */
function removeCoefficientColumns_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) {
    uiAlert_('Не найден лист "прогнозы".');
    return;
  }

  var colB = sh.getRange(2, 2, sh.getMaxRows() - 1, 1).getValues();
  var lastRow = 1;
  for (var i = 0; i < colB.length; i++) {
    if (String(colB[i][0]).trim() !== '') lastRow = i + 2;
  }
  var numRows = Math.max(lastRow - 1, 1);

  // J — возвращаем исходный смысл (Ожид. разница Х-Г)
  sh.getRange('J1').setValue('Ожид. разница (Х-Г)');
  applyGoalsFormulas_(sh);

  // AE-AH и AX-BB — полностью очищаем (содержимое + фон)
  var maxRows = sh.getMaxRows();
  sh.getRange(1, 33, maxRows, 2).clearContent().setBackground(null); // AG:AH (AD/AE/AF заняты метками честности и флагами ОТ)
  sh.getRange(1, 50, maxRows, 5).clearContent().setBackground(null); // AX:BB

  // показываем всё обратно и снимаем закрепление
  var lastColForShow = Math.max(sh.getLastColumn(), 100);
  sh.showColumns(12, lastColForShow - 12 + 1);
  sh.setFrozenColumns(0);

  uiAlert_(
    'Готово: столбец J вернулся к «Ожид. разница (Х-Г)», столбцы AE-AH и AX-BB с коэффициентами ' +
    'полностью очищены, все столбцы снова видны, закрепление снято. Симуляция банкролла и подсветка ' +
    'горячих матчей продолжат работать — там, где раньше мог быть реальный коэффициент, теперь всегда ' +
    'будет использоваться расчётный (из вероятности модели).'
  );
}

/* ============================================================================
 * ДЖАРВИС-АНАЛИТИК: качественный контекст по матчу через Claude (Anthropic API)
 * ----------------------------------------------------------------------------
 * ВАЖНО (правило проекта, не менять):
 *   - Эта функция НИКОГДА не пишет в листы "Data", "Elo", "прогнозы" и не
 *     меняет ни одной цифры модели. Она только читает готовый прогноз из
 *     "прогнозы" и добавляет СВОЮ, отдельную качественную заметку на лист
 *     "Контекст и новости" — второй, независимый "голос", который вы читаете
 *     и учитываете сами, вручную. Модель как считала, так и продолжает считать.
 *   - Использует настоящий Anthropic API (с реальным веб-поиском), а не
 *     встроенный в таблицу Gemini — у Gemini нет доступа в интернет, он умеет
 *     работать только с уже готовыми данными в самой таблице.
 *   - Каждый вызов этой функции тратит реальные деньги (API оплачивается
 *     Вадимом). Функция вызывается вручную, по одному матчу за раз — по
 *     выбранной строке на листе "прогнозы" — а не по всем матчам сразу.
 *
 * НАСТРОЙКА (один раз):
 *   1. Меню "НХЛ-парсер" → "Разовая настройка" → "Указать API-ключ Anthropic".
 *   2. Вставьте ключ (начинается на "sk-ant-...") в появившееся окошко.
 *      Ключ сохраняется в свойствах СКРИПТА (Script Properties) — это
 *      хранилище Google, привязанное к конкретной таблице, а не к файлу кода,
 *      и не видно никому, кто не имеет доступа на редактирование скрипта.
 *
 * ИСПОЛЬЗОВАНИЕ:
 *   1. На листе "прогнозы" встаньте на любую ячейку в строке нужного матча.
 *   2. Меню "НХЛ-парсер" → "Спросить Джарвиса про матч".
 *   3. Через 15-30 секунд (идёт настоящий веб-поиск) выйдет подтверждение,
 *      а сама заметка появится новой строкой на листе "Контекст и новости".
 * ==========================================================================*/

var SHEET_CONTEXT = 'Контекст и новости';
var ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001'; // экономичная модель — этого достаточно для веб-поиска и краткой сводки
var ANTHROPIC_MAX_TOKENS = 1600;   // ответ теперь структурный (вратари/составы/свежесть/игра/вывод)

/**
 * Разовая настройка: спрашивает у пользователя ключ Anthropic API и
 * сохраняет его в Script Properties (PropertiesService) — оттуда его
 * читает askJarvisAboutMatch_(). Можно перезапускать, если ключ поменялся.
 */
function setAnthropicApiKey_() {
  var ui = SpreadsheetApp.getUi();
  var resp = ui.prompt(
    'Ключ Anthropic API',
    'Вставьте ваш ключ (обычно начинается на "sk-ant-..."). ' +
    'Он будет сохранён в свойствах скрипта этой таблицы и использоваться ' +
    'только функцией "Спросить Джарвиса про матч".',
    ui.ButtonSet.OK_CANCEL
  );
  if (resp.getSelectedButton() !== ui.Button.OK) return;

  var key = String(resp.getResponseText() || '').trim();
  if (!key) {
    ui.alert('Ключ пустой, ничего не сохранено.');
    return;
  }
  PropertiesService.getScriptProperties().setProperty('ANTHROPIC_API_KEY', key);
  ui.alert('Готово: ключ сохранён. Теперь можно пользоваться пунктом "Спросить Джарвиса про матч".');
}

/** Находит на листе "прогнозы" строку матча, на которой сейчас стоит курсор. */
function getSelectedMatchRow_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) return null;

  var active = SpreadsheetApp.getActiveSheet();
  if (active.getName() !== 'прогнозы') return { error: 'Встаньте курсором на строку матча на листе "прогнозы", затем повторите.' };

  var row = sh.getActiveCell().getRow();
  if (row < 2) return { error: 'Встаньте курсором на строку с матчем (не на заголовок), затем повторите.' };

  var vals = sh.getRange(row, 1, 1, 11).getValues()[0]; // A..K
  var home = String(vals[1] || '').trim();
  var away = String(vals[2] || '').trim();
  if (!home || !away) return { error: 'В выбранной строке не заполнены хозяева/гости — выберите строку с матчем.' };

  return {
    row: row,
    date: vals[0],
    home: home,
    away: away,
    probHome: vals[3],
    probAway: vals[4],
    favorite: vals[5]
  };
}

function formatDateRu_(d) {
  if (!(d instanceof Date)) return String(d || '');
  return Utilities.formatDate(d, Session.getScriptTimeZone() || 'Europe/Moscow', 'dd.MM.yyyy');
}

/** Собирает на листе "Контекст и новости" заголовки, если листа ещё нет. */
function ensureContextSheet_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(SHEET_CONTEXT);
  var header = ['Когда спросили', 'Дата матча', 'Матч', 'Прогноз модели (на момент запроса)', 'Заметка Джарвиса', 'Проверено?'];

  if (!sh) {
    sh = ss.insertSheet(SHEET_CONTEXT);
    sh.getRange(1, 1, 1, header.length).setValues([header]);
  } else {
    // Лист мог остаться от прежнего агента-скаута — у него было всего четыре
    // столбца ("Дата обновления / Дата матча / Матч / Сводка"). Если дописывать
    // в него шесть значений как есть, данные лягут под чужие заголовки, поэтому
    // шапку приводим к нужному виду, а старые записи оставляем на месте.
    var width = Math.max(sh.getLastColumn(), header.length);
    var current = sh.getRange(1, 1, 1, width).getValues()[0];
    var needsHeaderFix = false;
    for (var i = 0; i < header.length; i++) {
      if (String(current[i] || '').trim() !== header[i]) { needsHeaderFix = true; break; }
    }
    if (needsHeaderFix) {
      sh.getRange(1, 1, 1, header.length).setValues([header]);
    }
  }

  sh.setFrozenRows(1);
  sh.getRange(1, 1, 1, header.length).setFontWeight('bold');
  sh.setColumnWidths(1, 2, 130);
  sh.setColumnWidth(3, 220);
  sh.setColumnWidth(4, 220);
  sh.setColumnWidth(5, 600);
  sh.setColumnWidth(6, 90);
  if (sh.isSheetHidden()) sh.showSheet();
  return sh;
}

/**
 * Строит текст запроса к Claude для конкретного матча — специально просит
 * искать именно то, чего не видит числовая модель: насколько тяжёлой была
 * последняя игра фаворита (физическая нагрузка, овертайм/буллиты, разгромный
 * счёт), травмы, кадровые новости, форма и настрой команд — и явно спросить,
 * есть ли основания ждать неожиданного результата, даже если по цифрам
 * фаворит один.
 */
function buildJarvisPrompt_(match) {
  var dateStr = formatDateRu_(match.date);
  var probHomeStr = (typeof match.probHome === 'number') ? Math.round(match.probHome * (match.probHome <= 1 ? 100 : 1)) + '%' : String(match.probHome);
  var probAwayStr = (typeof match.probAway === 'number') ? Math.round(match.probAway * (match.probAway <= 1 ? 100 : 1)) + '%' : String(match.probAway);

  return (
    'Ты аналитик НХЛ (Национальная хоккейная лига). Матч: ' + match.home + ' — ' + match.away +
    ', дата: ' + dateStr + '. ' +
    'Наша статистическая модель (Elo-рейтинг + форма) сейчас считает фаворитом: ' + match.favorite +
    ' (' + match.home + ' ' + probHomeStr + ' / ' + match.away + ' ' + probAwayStr + ').\n\n' +
    'Модель считает только по счёту прошлых матчей. Она НЕ видит вратарей, составы и травмы — ' +
    'а в хоккее это решает больше, чем любая другая деталь. Найди в интернете (обязательно используй ' +
    'веб-поиск) свежие факты и ответь строго по этим пунктам, по-русски, без markdown-разметки:\n\n' +
    'ВРАТАРИ: кто, скорее всего, выйдет в воротах у каждой команды на этот матч. Если состав ещё не ' +
    'объявлен — кто играл последние 2-3 матча и в какой форме. Укажи процент отражённых бросков за сезон, ' +
    'если найдёшь. Отдельно отметь, если у команды травмирован или не играет основной вратарь — это ' +
    'самое важное, что модель не учитывает.\n\n' +
    'СОСТАВЫ И ТРАВМЫ: кто из ключевых игроков не сыграет (травма, дисквалификация, отъезд). ' +
    'Важны именно лидеры — первое звено, первая пара защитников, бомбардиры.\n\n' +
    'СВЕЖЕСТЬ: насколько тяжёлой физически была последняя игра каждой команды — овертайм или буллиты, ' +
    'разгромный счёт, дальний перелёт, игра через день, затяжная выездная серия. Команда после ' +
    'изматывающего матча может физически провалить следующий, даже будучи сильнее по составу.\n\n' +
    'ИГРА И НАСТРОЙ: как команды выглядят в последних матчах по содержанию игры, а не только по очкам. ' +
    'Смена тренера, конфликт, серия поражений, давление на клуб — если есть.\n\n' +
    'ВЫВОД: одна-две фразы — есть ли качественные основания ожидать, что фаворит по цифрам (' +
    match.favorite + ') неожиданно проиграет. Если таких оснований нет, так и скажи прямо.\n\n' +
    'Если по какому-то пункту ничего конкретного не нашлось — напиши "нет данных" и не выдумывай. ' +
    'Пиши сухо, фактами, без общих рассуждений. Каждый пункт начинай с его названия заглавными буквами.'
  );
}

/**
 * Собственно вызов Anthropic API с включённым веб-поиском. Возвращает
 * текст ответа (склеенные текстовые блоки) или бросает исключение с
 * понятным сообщением, если что-то пошло не так (нет ключа, ошибка API и т.п.).
 */
function callAnthropicWithWebSearch_(promptText, apiKey) {
  var payload = {
    model: ANTHROPIC_MODEL,
    max_tokens: ANTHROPIC_MAX_TOKENS,
    tools: [{ type: 'web_search_20260209', name: 'web_search', max_uses: 6 }],
    messages: [{ role: 'user', content: promptText }]
  };

  var options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01'
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  var resp = UrlFetchApp.fetch('https://api.anthropic.com/v1/messages', options);
  var code = resp.getResponseCode();
  var bodyText = resp.getContentText();

  if (code !== 200) {
    var errMsg = bodyText;
    try {
      var errJson = JSON.parse(bodyText);
      if (errJson.error && errJson.error.message) errMsg = errJson.error.message;
    } catch (e) { /* оставляем сырой текст */ }
    throw new Error('Anthropic API вернул ошибку (код ' + code + '): ' + errMsg);
  }

  var json = JSON.parse(bodyText);
  return extractTextFromAnthropicResponse_(json);
}

/** Склеивает все текстовые блоки ответа Claude (пропуская блоки веб-поиска) в одну строку. */
function extractTextFromAnthropicResponse_(json) {
  if (!json || !json.content || !json.content.length) return '';
  var parts = [];
  for (var i = 0; i < json.content.length; i++) {
    var block = json.content[i];
    if (block && block.type === 'text' && block.text) parts.push(block.text.trim());
  }
  return parts.join('\n').trim();
}

/**
 * Главная функция меню: берёт выбранную строку матча на листе "прогнозы",
 * зовёт Claude с веб-поиском по ней, и дописывает новую строку на лист
 * "Контекст и новости". Ничего в листах Data/Elo/прогнозы не меняет.
 */
function askJarvisAboutMatch_() {
  var ui = SpreadsheetApp.getUi();

  var apiKey = PropertiesService.getScriptProperties().getProperty('ANTHROPIC_API_KEY');
  if (!apiKey) {
    ui.alert(
      'Сначала укажите API-ключ: меню "НХЛ-парсер" → "Разовая настройка" → ' +
      '"Указать API-ключ Anthropic".'
    );
    return;
  }

  var match = getSelectedMatchRow_();
  if (!match) {
    ui.alert('Не найден лист "прогнозы".');
    return;
  }
  if (match.error) {
    ui.alert(match.error);
    return;
  }

  var promptText = buildJarvisPrompt_(match);

  var answerText;
  try {
    answerText = callAnthropicWithWebSearch_(promptText, apiKey);
  } catch (e) {
    ui.alert('Не получилось получить ответ от Джарвиса: ' + e.message);
    return;
  }

  if (!answerText) {
    ui.alert('Джарвис ответил пусто — попробуйте ещё раз чуть позже.');
    return;
  }

  var contextSh = ensureContextSheet_();
  var predictionSnapshot = match.home + ' ' + match.probHome + ' / ' + match.away + ' ' + match.probAway +
    ' (фаворит: ' + match.favorite + ')';

  contextSh.appendRow([
    new Date(),
    match.date,
    match.home + ' — ' + match.away,
    predictionSnapshot,
    answerText,
    ''
  ]);
  var newRow = contextSh.getLastRow();
  contextSh.getRange(newRow, 1).setNumberFormat('dd.mm.yyyy hh:mm');
  contextSh.getRange(newRow, 2).setNumberFormat('dd.mm.yyyy');
  contextSh.getRange(newRow, 1, 1, 6).setVerticalAlignment('top').setWrap(true);

  ui.alert('Готово: заметка Джарвиса по матчу "' + match.home + ' — ' + match.away + '" добавлена на лист "' + SHEET_CONTEXT + '".');
}

/* ============================================================================
 * ПАКЕТ ИСПРАВЛЕНИЙ (аудит таблицы, сентябрь 2026)
 * ----------------------------------------------------------------------------
 * Исправляет четыре найденные при разборе таблицы проблемы:
 *
 * 1. УТЕЧКА ДАННЫХ. Все функции «Разовой настройки» ставили формулу в строку 2
 *    и копировали её вниз через copyTo на ВЕСЬ столбец — включая уже сыгранные
 *    матчи, у которых прогноз должен быть заморожен. Любой такой запуск снимал
 *    заморозку, и прогноз задним числом «узнавал» результат через обновлённый
 *    рейтинг. На момент аудита так было испорчено 18 из 39 сыгранных матчей:
 *    на них точность выходила 83.3% против 66.7% на честных.
 *    Лечится двумя частями: (а) формулы теперь ставятся ТОЛЬКО в строки без
 *    результата (setFormulaOnOpenRows_), (б) появился столбец AD «Честный
 *    прогноз?», и статистика считается только по строкам с «да».
 *
 * 2. УСТАЛОСТЬ НЕ РАБОТАЛА. Формула =MIN(0;MAX(-6;(W-2)*3)) задумывалась под
 *    шкалу «0 дней отдыха = -6, 1 день = -3, 2+ = 0». Но в КХЛ команды играют
 *    минимум через день, то есть W всегда >= 2, и поправка всегда выходила
 *    ровно 0 — проверено на всех 84 строках. Порог сдвинут на реальную для КХЛ
 *    шкалу (полное восстановление — 4 дня) и добавлен учёт того, что прошлая
 *    игра была тяжёлой (овертайм/буллиты).
 *
 * 3. ДОМАШНЕЕ ПРЕИМУЩЕСТВО БЫЛО ЗАНИЖЕНО. Столбец U считал только персональную
 *    разницу «очки дома минус очки в гостях», а базовое преимущество лиги
 *    ($M$2) подставлялось лишь как запасной вариант при отсутствии данных.
 *    В итоге модель давала хозяевам в среднем 42.3% там, где они выигрывают
 *    52.4%. Теперь база применяется всегда, и она откалибрована по факту:
 *    за два сезона (810 матчей) хозяева берут 54.3%, что при масштабе $M$3=90
 *    даёт ровно +6.74 пункта; с учётом средней персональной добавки (+0.64)
 *    базовое значение = 6.0.
 *
 * 4. H2H ПЕРЕВЕШИВАЛ. Поправка за личные встречи доходила до ±13.3 пункта —
 *    больше, чем разница в силе между 4-й и 8-й командой лиги — уже при пяти
 *    очных матчах, половина которых из прошлого сезона с другими составами.
 *    Вес снижен вдвое, насыщение сдвинуто с 6 встреч на 10.
 *
 * ВАЖНО: сама архитектура модели не трогается — меняются только коэффициенты
 * и то, в какие строки разрешено писать формулы.
 * ==========================================================================*/

// --- откалиброванные коэффициенты (менять здесь, а не в формулах) ---
var HOME_BASE_ADVANTAGE = 6.0;   // базовое домашнее преимущество лиги, пунктов рейтинга
var HOME_PERSONAL_MULT  = 4;     // множитель персональной добавки (было 6)
var HOME_PERSONAL_MIN   = -3;    // нижняя граница персональной добавки
var HOME_PERSONAL_MAX   = 6;     // верхняя граница (было 9)

var FATIGUE_FULL_REST   = 4;     // дней отдыха для полного восстановления (было 2)
var FATIGUE_STEP        = 2;     // пунктов штрафа за каждый недостающий день
var FATIGUE_CAP         = 6;     // максимальный штраф за усталость
var FATIGUE_OT_PENALTY  = '3/2'; // доп. штраф, если прошлая игра шла в ОТ/буллиты
                                  // (записан дробью, а не как 1.5 — чтобы не зависеть
                                  //  от того, точка или запятая служит в таблице
                                  //  десятичным разделителем)

var H2H_WEIGHT     = 8;          // вес поправки за личные встречи (было 16)
var H2H_FULL_GAMES = 10;         // сколько очных встреч даёт полный вес (было 6)

var COL_INTEGRITY = 30;          // AD — «Честный прогноз?»
var COL_OT_HOME   = 31;          // AE — прошлая игра хозяев шла в ОТ/буллиты
var COL_OT_AWAY   = 32;          // AF — то же для гостей

/** Номер последней строки с матчем на листе "прогнозы". */
function lastMatchRow_(sh) {
  var colB = sh.getRange(2, 2, sh.getMaxRows() - 1, 1).getValues();
  var lastRow = 1;
  for (var i = 0; i < colB.length; i++) {
    if (String(colB[i][0]).trim() !== '') lastRow = i + 2;
  }
  return lastRow;
}

/**
 * Возвращает номера строк, в которые МОЖНО писать формулы — то есть матчи,
 * которые ещё не сыграны (столбец K пуст). Строки с ✅/❌ в список не попадают:
 * их прогноз заморожен и трогать его нельзя, иначе вернётся утечка.
 */
function openPredictionRows_(sh) {
  var lastRow = lastMatchRow_(sh);
  if (lastRow < 2) return [];
  var vals = sh.getRange(2, 1, lastRow - 1, 11).getValues(); // A..K
  var out = [];
  for (var i = 0; i < vals.length; i++) {
    var home = String(vals[i][1]).trim(), away = String(vals[i][2]).trim();
    if (!home || !away) continue;
    var mark = String(vals[i][10]).trim();
    if (mark === '✅' || mark === '❌') continue; // сыгран — не трогаем
    out.push(i + 2);
  }
  return out;
}

/**
 * Ставит формулу в указанные строки одного столбца. Шаблон формулы должен
 * содержать {R} вместо номера строки. Идущие подряд строки объединяются в
 * блоки, чтобы не дёргать таблицу на каждую ячейку по отдельности.
 */
function setFormulaOnOpenRows_(sh, col, template, rows) {
  if (!rows || !rows.length) return 0;
  var i = 0, written = 0;
  while (i < rows.length) {
    var start = i;
    while (i + 1 < rows.length && rows[i + 1] === rows[i] + 1) i++;
    var block = rows.slice(start, i + 1);
    var formulas = block.map(function (r) {
      return [template.replace(/\{R\}/g, r)];
    });
    sh.getRange(block[0], col, block.length, 1).setFormulas(formulas);
    written += block.length;
    i++;
  }
  return written;
}

/*
 * СОСТАВ МОДЕЛИ. Какие поправки входят в формулу шансов — решено по
 * самопроверке на 614 матчах двух сезонов (21.09.2026), где каждый матч
 * оценивался только по тому, что было известно до него:
 *
 *   вариант                                      Brier   точность
 *   все поправки (как было)                      0.2288  60.3%
 *   рейтинг + дом + усталость + плотность        0.2252  62.5%   <- выбран
 *
 * Форма ухудшала прогноз (единственный эффект больше погрешности): она
 * повторно учитывала те же последние матчи, которые уже сдвинули Elo, и
 * модель перереагировала на короткие серии. H2H, выездная серия и
 * персональный домашний бонус не дали никакого эффекта — их столбцы остаются
 * на листе для справки, но в шансы не входят. Домашний бонус остаётся
 * базовым ($M$2 = 6), который самопроверка подтвердила как оптимальный.
 *
 * Если со временем самопроверка покажет другое — меняются только эти флаги,
 * затем пункт меню «Применить самую точную модель».
 */
var MODEL_USE_PERSONAL_HOME = false; // U: персональный домашний бонус (иначе — только база $M$2)
var MODEL_USE_H2H           = false; // P
var MODEL_USE_FATIGUE       = true;  // AB
var MODEL_USE_FORM          = false; // AC
var MODEL_USE_ROAD          = false; // AS
var MODEL_USE_DENSITY       = true;  // AV

/** Единая формула шансов хозяев — собирается в одном месте из флагов выше. */
function probabilityFormulaTemplate_(withoutTweak) {
  var terms = [MODEL_USE_PERSONAL_HOME ? 'U{R}' : '$M$2'];
  if (!withoutTweak && typeof tweaksOn_ === 'function' && tweaksOn_()) terms.push('BC{R}');   // моя ручная поправка
  if (MODEL_USE_H2H) terms.push('P{R}');
  if (MODEL_USE_FATIGUE) terms.push('AB{R}');
  if (modelUseForm_()) terms.push('AC{R}');
  if (MODEL_USE_ROAD) terms.push('AS{R}');
  if (MODEL_USE_DENSITY) terms.push('AV{R}');
  return '=IF(OR(B{R}="";C{R}="");"";ROUND(MAX(8/100;MIN(92/100;1/(1+10^(-(' +
         '(INDEX(Data!$T$2:$T$33;MATCH(B{R};Data!$A$2:$A$33;0)))' +
         '+' + terms.join('+') +
         '-(INDEX(Data!$T$2:$T$33;MATCH(C{R};Data!$A$2:$A$33;0)))' +
         ')/$M$3))));4))';
}

/** Пункт меню: ставит выбранную по самопроверке формулу в несыгранные матчи. */
function applyBestModel_() {
  var sh = SpreadsheetApp.getActive().getSheetByName('прогнозы');
  if (!sh) { uiAlert_('Не найден лист "прогнозы".'); return; }
  var n = applyProbabilityFormula_(sh);
  var used = ['рейтинг силы', 'домашний бонус'];
  if (MODEL_USE_H2H) used.push('личные встречи');
  if (MODEL_USE_FATIGUE) used.push('усталость');
  if (modelUseForm_()) used.push('форма');
  if (MODEL_USE_ROAD) used.push('выездная серия');
  if (MODEL_USE_DENSITY) used.push('плотность календаря');
  uiAlert_(
    'Формула шансов обновлена в ' + n + ' несыгранных матчах.\n\n' +
    'Теперь в расчёте: ' + used.join(', ') + '.\n\n' +
    'Так модель показала себя точнее всего на 614 матчах двух сезонов: 62.5% угаданных и Brier 0.2252 ' +
    'против 60.3% и 0.2288 у прежнего состава. Уже сыгранные прогнозы не тронуты. Столбцы формы, ' +
    'личных встреч и выездных серий остаются на листе для справки.'
  );
}

/**
 * Ставит формулу шансов хозяев (D) и зеркальную формулу гостей (E) только в
 * несыгранные строки. Заменяет прежнюю связку «setFormula в D2 + copyTo вниз»,
 * которая и ломала заморозку.
 */
function applyProbabilityFormula_(sh) {
  var rows = openPredictionRows_(sh);
  setFormulaOnOpenRows_(sh, 4, probabilityFormulaTemplate_(), rows);
  setFormulaOnOpenRows_(sh, 5, '=IF(OR(B{R}="";C{R}="");"";1-D{R})', rows);
  return rows.length;
}

/** Ставит формулы ожидаемых голов/тотала/разницы (G,H,I,J) только в несыгранные строки. */
function applyGoalsFormulas_(sh) {
  var rows = openPredictionRows_(sh);
  setFormulaOnOpenRows_(sh, 7,
    '=IFERROR(ROUND((INDEX(Data!$Z$2:$Z$33;MATCH(B{R};Data!$A$2:$A$33;0))+INDEX(Data!$AC$2:$AC$33;MATCH(C{R};Data!$A$2:$A$33;0)))/2;2);"")', rows);
  setFormulaOnOpenRows_(sh, 8,
    '=IFERROR(ROUND((INDEX(Data!$AA$2:$AA$33;MATCH(C{R};Data!$A$2:$A$33;0))+INDEX(Data!$AB$2:$AB$33;MATCH(B{R};Data!$A$2:$A$33;0)))/2;2);"")', rows);
  setFormulaOnOpenRows_(sh, 9,  '=IFERROR(ROUND(G{R}+H{R};2);"")', rows);
  setFormulaOnOpenRows_(sh, 10, '=IFERROR(ROUND(G{R}-H{R};2);"")', rows);
  return rows.length;
}

/* ---------------------------------------------------------------------------
 * ИСПРАВЛЕНИЕ 1: заморозка сыгранных матчей + отметка честности прогноза
 * -------------------------------------------------------------------------*/
function fixDataLeak_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) { uiAlert_('Не найден лист "прогнозы".'); return; }

  var lastRow = lastMatchRow_(sh);
  if (lastRow < 2) { uiAlert_('На листе "прогнозы" нет матчей.'); return; }

  sh.getRange(1, COL_INTEGRITY).setValue('Честный прогноз?');

  var predCols = [4, 5, 7, 8, 9, 10]; // D,E,G,H,I,J
  var marks = sh.getRange(2, 11, lastRow - 1, 1).getValues();       // K
  var existingFlags = sh.getRange(2, COL_INTEGRITY, lastRow - 1, 1).getValues();

  var frozen = 0, contaminated = 0, alreadyClean = 0;
  var flagsOut = [];

  for (var i = 0; i < lastRow - 1; i++) {
    var row = i + 2;
    var mark = String(marks[i][0]).trim();
    var prevFlag = String(existingFlags[i][0]).trim();

    if (mark !== '✅' && mark !== '❌') {  // матч не сыгран — метка пустая
      flagsOut.push(['']);
      continue;
    }

    // Матч сыгран. Смотрим, осталась ли в столбцах прогноза живая формула.
    var hadLiveFormula = false;
    for (var c = 0; c < predCols.length; c++) {
      if (sh.getRange(row, predCols[c]).getFormula() !== '') { hadLiveFormula = true; break; }
    }

    // Замораживаем в любом случае — чтобы дальше ничего не менялось.
    if (hadLiveFormula) {
      for (var c2 = 0; c2 < predCols.length; c2++) {
        var cell = sh.getRange(row, predCols[c2]);
        if (cell.getFormula() !== '') cell.setValue(cell.getValue());
      }
      frozen++;
    }

    // Определяем честность. Если строка уже была помечена раньше — метку не
    // переписываем: однажды испорченный прогноз честным больше не станет.
    if (prevFlag === 'нет') {
      flagsOut.push(['нет']);
      contaminated++;
    } else if (hadLiveFormula) {
      flagsOut.push(['нет']);
      contaminated++;
    } else {
      flagsOut.push(['да']);
      alreadyClean++;
    }
  }

  sh.getRange(2, COL_INTEGRITY, flagsOut.length, 1).setValues(flagsOut);

  uiAlert_(
    'Заморозка восстановлена.\n\n' +
    'Честных прогнозов (можно верить): ' + alreadyClean + '\n' +
    'Испорченных утечкой (помечены «нет»): ' + contaminated + '\n' +
    'Заморожено сейчас (было живой формулой): ' + frozen + '\n\n' +
    'Испорченные прогнозы восстановить нельзя — их исходные значения не сохранились. ' +
    'Поэтому они помечены в столбце AD и дальше исключаются из подсчёта точности, ' +
    'чтобы не завышать статистику. Новые матчи будут замораживаться корректно.'
  );
}

/* ---------------------------------------------------------------------------
 * ИСПРАВЛЕНИЕ 2: рабочая поправка на усталость
 * -------------------------------------------------------------------------*/
function fixFatigueFormulas_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) { uiAlert_('Не найден лист "прогнозы".'); return; }

  var lastRow = lastMatchRow_(sh);
  if (lastRow < 2) { uiAlert_('На листе "прогнозы" нет матчей.'); return; }
  var allRows = [];
  for (var r = 2; r <= lastRow; r++) allRows.push(r);

  sh.getRange(1, COL_OT_HOME).setValue('Пред. игра Хозяев в ОТ?');
  sh.getRange(1, COL_OT_AWAY).setValue('Пред. игра Гостей в ОТ?');
  sh.getRange('X1').setValue('Устал. поправка Хозяев');
  sh.getRange('AA1').setValue('Устал. поправка Гостей');

  // Была ли предыдущая игра команды в овертайме/по буллитам: ищем в расписании
  // матч с датой = дате предыдущей игры (V/Y) и участием этой команды, и
  // смотрим флаг в столбце G листа результатов.
  var otTemplate = function (dateCol, teamCol) {
    return '=IF(' + dateCol + '{R}=0;0;IF(SUMPRODUCT(' +
      '(\'результаты матчей\'!$A$2:$A$998=' + dateCol + '{R})*' +
      '((\'результаты матчей\'!$C$2:$C$998=$' + teamCol + '{R})+(\'результаты матчей\'!$D$2:$D$998=$' + teamCol + '{R}))*' +
      '(\'результаты матчей\'!$G$2:$G$998=TRUE))>0;1;0))';
  };
  setFormulaOnOpenRows_(sh, COL_OT_HOME, otTemplate('V', 'B'), allRows);
  setFormulaOnOpenRows_(sh, COL_OT_AWAY, otTemplate('Y', 'C'), allRows);

  // Новая шкала усталости: полное восстановление за FATIGUE_FULL_REST дней,
  // каждый недостающий день — минус FATIGUE_STEP пунктов, плюс отдельный штраф
  // за тяжёлую (овертаймовую) прошлую игру. Всё вместе ограничено FATIGUE_CAP.
  var fatigueTemplate = function (restCol, otCol) {
    return '=MAX(-' + FATIGUE_CAP + ';MIN(0;(' + restCol + '{R}-' + FATIGUE_FULL_REST + ')*' + FATIGUE_STEP + ')' +
           '-IF(' + otCol + '{R}=1;' + FATIGUE_OT_PENALTY + ';0))';
  };
  setFormulaOnOpenRows_(sh, 24, fatigueTemplate('W', 'AE'), allRows);  // X
  setFormulaOnOpenRows_(sh, 27, fatigueTemplate('Z', 'AF'), allRows);  // AA
  setFormulaOnOpenRows_(sh, 28, '=X{R}-AA{R}', allRows);               // AB

  sh.getRange(2, 24, lastRow - 1, 1).setNumberFormat('0.##');
  sh.getRange(2, 27, lastRow - 1, 2).setNumberFormat('0.##');
  sh.getRange(2, COL_OT_HOME, lastRow - 1, 2).setNumberFormat('0');

  var applied = applyProbabilityFormula_(sh);

  uiAlert_(
    'Поправка на усталость теперь работает.\n\n' +
    'Было: полное восстановление засчитывалось уже за 2 дня отдыха, а в КХЛ меньше двух дней ' +
    'между играми почти не бывает — поэтому поправка всегда выходила ровно 0 и ни на что не влияла.\n\n' +
    'Стало: полное восстановление за ' + FATIGUE_FULL_REST + ' дня, каждый недостающий день — минус ' +
    FATIGUE_STEP + ' пункта рейтинга (максимум -' + FATIGUE_CAP + '). Отдельно учитывается, что прошлая игра ' +
    'была тяжёлой — если она шла в овертайме или до буллитов, добавляется ещё полтора пункта штрафа.\n\n' +
    'Формула шансов обновлена в ' + applied + ' несыгранных матчах. Сыгранные не тронуты.'
  );
}

/* ---------------------------------------------------------------------------
 * ИСПРАВЛЕНИЕ 3: домашнее преимущество по факту лиги
 * -------------------------------------------------------------------------*/
function fixHomeAdvantage_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) { uiAlert_('Не найден лист "прогнозы".'); return; }

  var lastRow = lastMatchRow_(sh);
  if (lastRow < 2) { uiAlert_('На листе "прогнозы" нет матчей.'); return; }
  var allRows = [];
  for (var r = 2; r <= lastRow; r++) allRows.push(r);

  sh.getRange('L2').setValue('Домашнее преимущество (доб. к рейтингу хозяев)');
  sh.getRange('M2').setValue(HOME_BASE_ADVANTAGE);

  // Базовое преимущество лиги теперь добавляется ВСЕГДА, а персональная разница
  // «очки дома минус очки в гостях» идёт сверху как отклонение конкретной
  // команды от средней — с уменьшенным весом, чтобы не перекрывать базу.
  var formulaU = '=$M$2+IF(OR(Q{R}=0;S{R}=0);0;MAX(' + HOME_PERSONAL_MIN + ';MIN(' + HOME_PERSONAL_MAX +
                 ';(R{R}/Q{R}-T{R}/S{R})*' + HOME_PERSONAL_MULT + ')))';
  setFormulaOnOpenRows_(sh, 21, formulaU, allRows);
  sh.getRange(2, 21, lastRow - 1, 1).setNumberFormat('0.##');

  var applied = applyProbabilityFormula_(sh);

  uiAlert_(
    'Домашнее преимущество откалибровано по факту.\n\n' +
    'Было: модель давала хозяевам в среднем 42.3% там, где они реально выигрывают 52.4% — ' +
    'базовое преимущество лиги применялось только когда по команде вообще нет данных.\n\n' +
    'Стало: база +' + HOME_BASE_ADVANTAGE + ' пункта добавляется всегда. Значение не выдумано: за два сезона ' +
    '(810 матчей) хозяева берут 54.3% побед, что при масштабе $M$3 = 90 даёт ровно +6.74 пункта; ' +
    'с учётом средней персональной добавки (+0.64) база выходит 6.0. Для двух равных по силе команд ' +
    'хозяин теперь получает 54.2% — то есть ровно столько, сколько показывает статистика.\n\n' +
    'Формула шансов обновлена в ' + applied + ' несыгранных матчах.'
  );
}

/* ---------------------------------------------------------------------------
 * ИСПРАВЛЕНИЕ 4: вес личных встреч
 * -------------------------------------------------------------------------*/
function fixH2HWeight_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) { uiAlert_('Не найден лист "прогнозы".'); return; }

  var lastRow = lastMatchRow_(sh);
  if (lastRow < 2) { uiAlert_('На листе "прогнозы" нет матчей.'); return; }
  var allRows = [];
  for (var r = 2; r <= lastRow; r++) allRows.push(r);

  var formulaP = '=IF(N{R}=0;0;(2*O{R}-N{R})/N{R}*' + H2H_WEIGHT + '*MIN(1;N{R}/' + H2H_FULL_GAMES + '))';
  setFormulaOnOpenRows_(sh, 16, formulaP, allRows);
  sh.getRange(2, 16, lastRow - 1, 1).setNumberFormat('0.##');

  var applied = applyProbabilityFormula_(sh);

  uiAlert_(
    'Вес личных встреч снижен.\n\n' +
    'Было: до ±13.3 пункта уже при пяти очных матчах — это больше, чем разница в силе между 4-й и 8-й ' +
    'командой лиги, причём половина этих встреч из прошлого сезона, когда составы были другими.\n\n' +
    'Стало: максимум ±' + H2H_WEIGHT + ' пунктов, и полный вес набирается только к ' + H2H_FULL_GAMES +
    ' очным встречам вместо ' + 6 + '. При пяти встречах поправка теперь не превысит ±4 пункта.\n\n' +
    'Формула шансов обновлена в ' + applied + ' несыгранных матчах.'
  );
}

/* ---------------------------------------------------------------------------
 * ВСЁ СРАЗУ
 * -------------------------------------------------------------------------*/
function fixEverything_() {
  var ui = SpreadsheetApp.getUi();
  var confirm = ui.alert(
    'Исправить всё найденное при аудите',
    'Сейчас будут применены четыре исправления:\n\n' +
    '1. Восстановлена заморозка сыгранных прогнозов, испорченные утечкой матчи помечены и исключены из статистики\n' +
    '2. Починена поправка на усталость (сейчас она всегда равна нулю)\n' +
    '3. Домашнее преимущество поднято до откалиброванного по факту значения\n' +
    '4. Снижен вес личных встреч\n\n' +
    'Сыгранные матчи не пересчитываются — меняются только прогнозы на будущие игры. Продолжить?',
    ui.ButtonSet.YES_NO
  );
  if (confirm !== ui.Button.YES) return;

  fixDataLeak_();
  fixFatigueFormulas_();
  fixHomeAdvantage_();
  fixH2HWeight_();
  computeAndWriteElo_(true);   // заодно записывает рейтинг силы в Data!T реальными числами

  ui.alert('Все исправления применены, Elo пересчитан.\n\n' +
           'Главное: рейтинг силы (Data!T) теперь берётся из реального Elo, а не из предсезонной оценки. ' +
           'До этого он был в точности равен стартовому у всех 22 команд — то есть модель за три недели ' +
           'сезона ни разу не учла, кто как играет на самом деле.\n\n' +
           'Дальше стоит нажать «Показать точность прогнозов» — она теперь считается только по честным матчам.');
}


/**
 * Пишет рейтинг силы (Data!T) прямо числом, пересчитанным из Elo:
 *     рейтинг = 50 + (Elo - 1500) / ELO_SCALE,  ограничен диапазоном 1..100
 *
 * Зачем понадобилось. В столбце T стояла формула
 *     =MIN(100;MAX(1;IFERROR(50+(INDEX(Elo!$B$2:$B$33;MATCH(A2;Elo!$A$2:$A$33;0))-1500)/6;Q2)))
 * то есть «возьми Elo, а если не вышло — возьми стартовый рейтинг Q». При
 * разборе таблицы выяснилось, что она всегда возвращала именно Q: рейтинг силы
 * у всех 22 команд был ровно равен предсезонной оценке, хотя лист Elo к тому
 * моменту уже показывал совсем другие цифры (Сибирь -14.6, Авангард -9.8,
 * Барыс +10.9 пункта). Прогнозы при этом считались по Q — модель три недели
 * не замечала, кто как на самом деле играет.
 *
 * Прямая запись числом надёжнее: она не зависит от того, сработает ли поиск
 * по соседнему листу, и обновляется ровно тогда, когда пересчитывается Elo.
 * Команда, которой почему-либо нет в листе Elo, сохраняет свой стартовый
 * рейтинг из столбца Q — как и было задумано изначально.
 */
function writeStrengthRatingToData_(teamOrder, elo) {
  var ss = SpreadsheetApp.getActive();
  var dataSh = ss.getSheetByName('Data');
  if (!dataSh) return 0;

  // сколько строк с командами на листе Data
  var colA = dataSh.getRange(2, 1, Math.min(dataSh.getMaxRows() - 1, 200), 1).getValues();
  var lastTeamRow = 1;
  for (var i = 0; i < colA.length; i++) {
    if (String(colA[i][0]).trim() !== '') lastTeamRow = i + 2;
  }
  if (lastTeamRow < 2) return 0;

  var count = lastTeamRow - 1;
  var names = dataSh.getRange(2, 1, count, 1).getValues();
  var startRatings = dataSh.getRange(2, 17, count, 1).getValues(); // Q — стартовый рейтинг
  var out = [];
  var updated = 0;

  for (var r = 0; r < count; r++) {
    var name = String(names[r][0]).trim();
    if (name && elo.hasOwnProperty(name)) {
      var value = 50 + (elo[name] - ELO_BASE) / ELO_SCALE;
      value = Math.min(100, Math.max(1, Math.round(value * 10) / 10));
      out.push([value]);
      updated++;
    } else {
      // команды нет в Elo (например, ещё не сыграла ни одного матча) — оставляем стартовый
      var fallback = Number(startRatings[r][0]);
      out.push([isNaN(fallback) ? 50 : fallback]);
    }
  }

  dataSh.getRange(2, 20, count, 1).setValues(out); // T
  dataSh.getRange(2, 20, count, 1).setNumberFormat('0.#');
  return updated;
}

/* ============================================================================
 * РЕАЛЬНАЯ КОМАНДНАЯ СТАТИСТИКА: броски, большинство, меньшинство
 * ----------------------------------------------------------------------------
 * Зачем. В таблице уже были столбцы Data!K «Броски за игру», Data!M
 * «Большинство, %» и Data!N «Меньшинство, %», но данные в них фиктивные: они
 * тянулись из листа Parser_Data, где у команд стоит 19-53 броска ЗА ВЕСЬ СЕЗОН
 * при реальных 25-35 за один матч, а у трёх команд реализация большинства
 * значилась как 0%. Проверено при разборе таблицы: ни на один прогноз эти
 * столбцы не влияли (ссылок на них в формулах нет), то есть вреда не было, но
 * и пользы тоже — а в «Карточке команды» они показывались как настоящие цифры.
 *
 * Эта функция забирает статистику с сайта и кладёт её на отдельный лист
 * «Статистика_команд», откуда её уже можно подключать к модели. Источники
 * пробуются по очереди: сайты периодически меняют вёрстку и закрываются от
 * автоматических запросов, поэтому один источник — это гарантированная
 * поломка через пару месяцев.
 *
 * Если не отозвался ни один источник, функция не молчит и не пишет нули, а
 * сохраняет кусок ответа на лист «Статистика_debug» — по нему видно, что
 * именно вернул сайт, и парсер можно поправить под новую вёрстку.
 * ==========================================================================*/

var SHEET_TEAM_STATS = 'Статистика_команд';



/** Приводит "58,3" / "58.3%" / " 58 " к числу 58.3; возвращает null, если не число. */
function parseStatNumber_(raw) {
  if (raw === null || raw === undefined) return null;
  var s = String(raw).replace(/\s|&nbsp;|%/g, '').replace(',', '.');
  if (!s || !/^-?\d+(\.\d+)?$/.test(s)) return null;
  return parseFloat(s);
}

/** Убирает html-теги из куска разметки и схлопывает пробелы. */
function stripTags_(html) {
  return String(html).replace(/<[^>]*>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
}



/**
 * Убирает фиктивные данные из листа Parser_Data и связанных с ним столбцов
 * Data!K/L/M/N, чтобы они не выглядели как настоящая статистика.
 *
 * Почему именно убрать, а не оставить как есть: в этих столбцах стояли
 * «19 бросков за сезон» и «0% реализации большинства» у команд, которые
 * большинство реализовывали. На прогнозы это не влияло (ни одна формула
 * модели на них не ссылается — проверено), но в «Карточке команды» эти числа
 * показывались наравне с настоящими, и по ним можно было сделать неверный
 * вывод о сопернике.
 */
function clearFakeParserStats_() {
  var ss = SpreadsheetApp.getActive();
  var ui = SpreadsheetApp.getUi();

  var answer = ui.alert(
    'Убрать фиктивную статистику',
    'В листе Parser_Data лежат недостоверные данные: броски за сезон (19-53 при реальных ' +
    '25-35 за ОДИН матч), штрафное время и проценты спецбригад, где у части команд стоит 0%.\n\n' +
    'На прогнозы они не влияют, но показываются в «Карточке команды» как настоящие цифры.\n\n' +
    'Очистить их? Реальные броски будет раз в день записывать скрипт на GitHub.',
    ui.ButtonSet.YES_NO
  );
  if (answer !== ui.Button.YES) return;

  var cleared = [];

  var parserSh = ss.getSheetByName('Parser_Data');
  if (parserSh) {
    var lastRow = parserSh.getLastRow();
    if (lastRow >= 2) {
      parserSh.getRange(2, 2, lastRow - 1, 4).clearContent(); // B..E, названия команд в A оставляем
      cleared.push('Parser_Data (столбцы с числами)');
    }
  }

  var dataSh = ss.getSheetByName('Data');
  if (dataSh) {
    // заголовки честно переименовываем — столбцы остаются, но видно, что данных нет
    dataSh.getRange('K1').setValue('Броски за игру (нет данных)');
    dataSh.getRange('L1').setValue('Штраф за игру (нет данных)');
    dataSh.getRange('M1').setValue('Большинство, % (нет данных)');
    dataSh.getRange('N1').setValue('Меньшинство, % (нет данных)');
    cleared.push('заголовки Data!K/L/M/N помечены');
  }

  ui.alert(
    'Готово: ' + cleared.join('; ') + '.\n\n' +
    'Столбец «Броски за игру» заполнит настоящими числами ежедневный скрипт на GitHub. ' +
    'Штраф и спецбригады останутся пустыми: надёжного источника для них не нашлось.'
  );
}



/* ============================================================================
 * САМОПРОВЕРКА ФАКТОРОВ
 * ----------------------------------------------------------------------------
 * Отвечает на вопрос: какие поправки модели реально улучшают прогноз, а какие
 * только добавляют шум.
 *
 * Как устроено. Скрипт проходит по всем сыгранным матчам обоих сезонов в
 * хронологическом порядке и перед каждым матчем заново считает рейтинг и все
 * поправки ТОЛЬКО по тому, что было известно на тот день (результаты раньше
 * этого матча, расписание). Потом сравнивает прогноз с фактом. Утечки здесь
 * нет по построению — в отличие от сохранённых прогнозов, где её пришлось
 * вычищать вручную. И выборка сразу большая: ~600 матчей вместо пары десятков
 * честных сохранённых прогнозов.
 *
 * Первые 200 матчей прошлого сезона в оценку не идут: рейтинги там стартуют
 * с одинаковых 1500 и ещё не успели разойтись. Текущий сезон стартует с
 * экспертных оценок, как и настоящая модель.
 *
 * Для каждой поправки считается два теста:
 *  1. «убрать из полной модели» — насколько хуже или лучше станет без неё;
 *  2. «добавить к простой модели» (рейтинг + базовый домашний бонус) — в
 *     полную силу и вполсилы.
 * Разница считается попарно по каждому матчу, и рядом стоит её погрешность
 * (две стандартные ошибки). Если эффект меньше погрешности — честный ответ
 * «не различимо», даже если цифра чуть лучше: на таком объёме это может быть
 * случайностью.
 *
 * Функция ничего не меняет в модели — только пишет лист «Самопроверка».
 * ==========================================================================*/

var SELFCHECK_WARMUP = 200;
// Тест 3 самопроверки: насколько быстро рейтинг должен реагировать на свежие матчи.
var SELFCHECK_SPEED_VARIANTS = [
  { name: 'Обычная скорость (K=20)', k: 20, boost: 0, games: 15 },
  { name: 'Медленнее (K=15)', k: 15, boost: 0, games: 15 },
  { name: 'Быстрее (K=25)', k: 25, boost: 0, games: 15 },
  { name: 'Сильно быстрее (K=30)', k: 30, boost: 0, games: 15 },
  { name: 'Быстрый старт ×1.5 первые 15 игр', k: 20, boost: 0.5, games: 15 },
  { name: 'Быстрый старт ×2 первые 15 игр', k: 20, boost: 1, games: 15 },
  { name: 'Быстрый старт ×3 первые 15 игр', k: 20, boost: 2, games: 15 }
];
var SELFCHECK_FACTORS = [
  { key: 'home',    name: 'Домашний бонус (база + персональный)' },
  { key: 'h2h',     name: 'Личные встречи (H2H)' },
  { key: 'fatigue', name: 'Усталость (отдых + овертайм)' },
  { key: 'form',    name: 'Форма (последние матчи)' },
  { key: 'road',    name: 'Выездная серия соперника' },
  { key: 'density', name: 'Плотность календаря' }
];

function scParseDate_(v) {
  if (v instanceof Date) return new Date(v.getFullYear(), v.getMonth(), v.getDate());
  var m = String(v || '').trim().match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/);
  return m ? new Date(+m[3], +m[2] - 1, +m[1]) : null;
}

function scDays_(a, b) { return Math.round((a.getTime() - b.getTime()) / 86400000); }

/** Читает лист результатов: сыгранные матчи (и, если нужно, запланированные — для расписания). */
function scLoadGames_(sh, withPlanned) {
  var out = [];
  if (!sh) return out;
  var v = sh.getDataRange().getValues();
  for (var r = 1; r < v.length; r++) {
    var d = scParseDate_(v[r][0]);
    var home = String(v[r][2] || '').trim(), away = String(v[r][3] || '').trim();
    if (!d || !home || !away) continue;
    var played = String(v[r][1]).trim() === 'Сыгран' && typeof v[r][4] === 'number' && typeof v[r][5] === 'number';
    if (!played && !withPlanned) continue;
    out.push({ date: d, home: home, away: away, played: played,
               hg: played ? v[r][4] : null, ag: played ? v[r][5] : null, ot: played ? !!v[r][6] : false });
  }
  out.sort(function (a, b) { return a.date - b.date; });
  return out;
}

/**
 * Пошаговый проход по сезонам. Возвращает для каждого сыгранного матча
 * разницу рейтингов, все поправки на момент ДО матча и исход.
 */
function scWalkForward_(seasons, homeBase, otPenalty, eloOpts) {
  eloOpts = eloOpts || {};
  var baseK = eloOpts.k !== undefined ? eloOpts.k : ELO_K;
  var boost = eloOpts.boost !== undefined ? eloOpts.boost : ELO_EARLY_BOOST;
  var boostGames = eloOpts.games !== undefined ? eloOpts.games : ELO_EARLY_GAMES;
  var records = [];
  // история, общая для обоих сезонов (домашний бонус и H2H в модели считаются по двум сезонам)
  var homeG = {}, homeP = {}, awayG = {}, awayP = {}, meetings = {};

  seasons.forEach(function (season) {
    var elo = {};
    if (season.start) for (var t in season.start) elo[t] = ELO_BASE + (season.start[t] - 50) * ELO_SCALE;
    var form = {}, lastGame = {}, played = {};

    // выездные серии и даты игр по расписанию сезона
    var streak = {}, streakAt = {}, datesByTeam = {};
    season.schedule.forEach(function (g) {
      streak[g.home] = 0;
      streak[g.away] = (streak[g.away] || 0) + 1;
      streakAt[g.date.getTime() + '|' + g.away] = streak[g.away];
      (datesByTeam[g.home] = datesByTeam[g.home] || []).push(g.date);
      (datesByTeam[g.away] = datesByTeam[g.away] || []).push(g.date);
    });

    var idx = 0;
    season.schedule.forEach(function (g) {
      if (!g.played) return;
      var h = g.home, a = g.away, d = g.date;
      if (!(h in elo)) elo[h] = ELO_BASE;
      if (!(a in elo)) elo[a] = ELO_BASE;
      var rating = function (t) { return Math.min(100, Math.max(1, 50 + (elo[t] - ELO_BASE) / ELO_SCALE)); };

      // --- поправки ДО матча ---
      var Q = homeG[h] || 0, R = homeP[h] || 0, S = awayG[h] || 0, T = awayP[h] || 0;
      var U = homeBase + ((Q && S) ? Math.max(HOME_PERSONAL_MIN, Math.min(HOME_PERSONAL_MAX, (R / Q - T / S) * HOME_PERSONAL_MULT)) : 0);

      var pairKey = [h, a].sort().join('|');
      var meet = meetings[pairKey] || [];
      var N = meet.length, O = 0;
      meet.forEach(function (m) { if ((m.home === h && m.hg > m.ag) || (m.away === h && m.ag > m.hg)) O++; });
      var P = N === 0 ? 0 : (2 * O - N) / N * H2H_WEIGHT * Math.min(1, N / H2H_FULL_GAMES);

      var fat = function (t) {
        var lg = lastGame[t];
        var rest = lg ? scDays_(d, lg.date) : 7;
        return Math.max(-FATIGUE_CAP, Math.min(0, (rest - FATIGUE_FULL_REST) * FATIGUE_STEP) - ((lg && lg.ot) ? otPenalty : 0));
      };
      var AB = fat(h) - fat(a);

      var fadj = function (t) {
        var arr = form[t] || [];
        if (!arr.length) return 0;
        var ws = 0, acc = 0;
        for (var k = 0; k < arr.length; k++) { ws += k + 1; acc += (k + 1) * arr[k]; }
        return Math.max(-8, Math.min(8, Math.round((acc / ws) * FORM_SCALE * 100) / 100));
      };
      var AC = fadj(h) - fadj(a);

      var st = streakAt[d.getTime() + '|' + a] || 0;
      var AS = Math.min(ROAD_TRIP_CAP, Math.max(0, (st - 1) * ROAD_TRIP_STEP));

      var dens = function (t) {
        var n = 0;
        (datesByTeam[t] || []).forEach(function (x) { var dd = scDays_(d, x); if (dd > 0 && dd <= DENSITY_WINDOW_DAYS) n++; });
        return n;
      };
      var pen = function (n) { return n >= 3 ? -3 : (n >= 2 ? -1 : 0); };
      var AV = pen(dens(h)) - pen(dens(a));

      var homeWon = g.hg > g.ag;
      idx++;
      records.push({
        season: season.name, idx: idx, base: rating(h) - rating(a), homeWon: homeWon, ot: !!g.ot,
        gp: Math.min(played[h] || 0, played[a] || 0),
        fac: { home: U, h2h: P, fatigue: AB, form: AC, road: AS, density: AV }
      });

      // --- обновление истории ПОСЛЕ матча ---
      var hp = homeWon ? 2 : (g.ot ? 1 : 0), ap = !homeWon ? 2 : (g.ot ? 1 : 0);
      homeG[h] = Q + 1; homeP[h] = R + hp;
      awayG[a] = (awayG[a] || 0) + 1; awayP[a] = (awayP[a] || 0) + ap;
      (meetings[pairKey] = meetings[pairKey] || []).push({ home: h, away: a, hg: g.hg, ag: g.ag });

      // Elo — ровно как в computeAndWriteElo_
      var eh = elo[h], ea = elo[a];
      var exp = 1 / (1 + Math.pow(10, (ea - eh) / 400));
      var act = g.ot ? (homeWon ? ELO_OT_CREDIT : 1 - ELO_OT_CREDIT) : (homeWon ? 1 : 0);
      var mov = 1;
      if (!g.ot) {
        var gd = Math.abs(g.hg - g.ag);
        var ed = homeWon ? (eh - ea) : (ea - eh);
        mov = (Math.log(gd) + 1) * (2.2 / (ed * 0.001 + 2.2));
      }
      elo[h] = eh + eloTeamK_(played[h], baseK, boost, boostGames) * mov * (act - exp);
      elo[a] = ea + eloTeamK_(played[a], baseK, boost, boostGames) * mov * ((1 - act) - (1 - exp));
      played[h] = (played[h] || 0) + 1; played[a] = (played[a] || 0) + 1;
      var dl = act - exp;
      (form[h] = form[h] || []).push(dl); (form[a] = form[a] || []).push(-dl);
      if (form[h].length > FORM_WINDOW) form[h].shift();
      if (form[a].length > FORM_WINDOW) form[a].shift();
      lastGame[h] = { date: d, ot: g.ot }; lastGame[a] = { date: d, ot: g.ot };
    });
  });
  return records;
}

/** Brier каждого матча при заданных весах поправок. weights: {factorKey: вес}, 'homeBaseOnly' — только база. */
function scBriers_(recs, weights, scale, homeBase) {
  return recs.map(function (r) {
    var x = r.base;
    for (var k in weights) {
      if (k === 'homeBaseOnly') x += weights[k] * homeBase;
      else x += weights[k] * r.fac[k];
    }
    var p = Math.max(0.08, Math.min(0.92, 1 / (1 + Math.pow(10, -x / scale))));
    return Math.pow(p - (r.homeWon ? 1 : 0), 2);
  });
}
function scMean_(a) { var s = 0; a.forEach(function (x) { s += x; }); return a.length ? s / a.length : 0; }
function scSe_(a) {
  if (a.length < 2) return 0;
  var m = scMean_(a), s = 0;
  a.forEach(function (x) { s += (x - m) * (x - m); });
  return Math.sqrt(s / (a.length - 1)) / Math.sqrt(a.length);
}
function scAccuracy_(recs, weights, scale, homeBase) {
  var ok = 0;
  recs.forEach(function (r) {
    var x = r.base;
    for (var k in weights) x += weights[k] * (k === 'homeBaseOnly' ? homeBase : r.fac[k]);
    if ((x >= 0) === r.homeWon) ok++;
  });
  return recs.length ? ok / recs.length : 0;
}
/** Сравнивает два набора Brier попарно: эффект (<0 — вариант лучше) и вердикт. */
function scCompare_(variant, reference) {
  var d = variant.map(function (x, i) { return x - reference[i]; });
  var m = scMean_(d), se2 = 2 * scSe_(d);
  var verdict = m < -se2 ? 'улучшает' : (m > se2 ? 'ухудшает' : 'не различимо');
  return { effect: m, err: se2, verdict: verdict };
}

/** Собирает все цифры самопроверки (без записи в таблицу — удобно для проверки). */
function computeSelfCheck_(seasons, homeBase, scale, otPenalty) {
  var recs = scWalkForward_(seasons, homeBase, otPenalty);
  var scored = recs.filter(function (r) { return !(r.season === seasons[0].name && r.idx <= SELFCHECK_WARMUP); });
  var allKeys = {}; SELFCHECK_FACTORS.forEach(function (f) { allKeys[f.key] = 1; });
  var full = scBriers_(scored, allKeys, scale, homeBase);
  var simpleW = { homeBaseOnly: 1 };
  var simple = scBriers_(scored, simpleW, scale, homeBase);

  var dropRows = SELFCHECK_FACTORS.map(function (f) {
    var w = {}; for (var k in allKeys) if (k !== f.key) w[k] = 1;
    var c = scCompare_(scBriers_(scored, w, scale, homeBase), full);
    // effect = (ошибка без поправки) − (ошибка полной модели): плюс — без неё хуже, то есть поправка полезна
    var v = c.verdict === 'улучшает' ? 'мешает (без него лучше)' : (c.verdict === 'ухудшает' ? 'помогает' : 'не различимо');
    return { name: f.name, brier: scMean_(scBriers_(scored, w, scale, homeBase)), effect: c.effect, err: c.err, verdict: v };
  });

  var addRows = [];
  SELFCHECK_FACTORS.forEach(function (f) {
    [1, 0.5].forEach(function (wt) {
      var w = { homeBaseOnly: 1 };
      if (f.key === 'home') { w.homeBaseOnly = 1 - wt; w.home = wt; } // персональная часть поверх базы
      else w[f.key] = wt;
      var b = scBriers_(scored, w, scale, homeBase);
      var c = scCompare_(b, simple);
      addRows.push({ name: f.key === 'home' ? 'Персональный домашний бонус' : f.name, weight: wt,
                     brier: scMean_(b), effect: c.effect, err: c.err,
                     verdict: c.verdict === 'улучшает' ? 'помогает' : (c.verdict === 'ухудшает' ? 'мешает' : 'не различимо') });
    });
  });

  var curW = {};
  if (MODEL_USE_PERSONAL_HOME) curW.home = 1; else curW.homeBaseOnly = 1;
  if (MODEL_USE_H2H) curW.h2h = 1;
  if (MODEL_USE_FATIGUE) curW.fatigue = 1;
  if (MODEL_USE_FORM) curW.form = 1;
  if (MODEL_USE_ROAD) curW.road = 1;
  if (MODEL_USE_DENSITY) curW.density = 1;
  var current = { brier: scMean_(scBriers_(scored, curW, scale, homeBase)), acc: scAccuracy_(scored, curW, scale, homeBase) };

  // Тест 3: скорость рейтинга. Каждый вариант — свой полный пошаговый проход, модель та же, что в прогнозах.
  var curBriers = scBriers_(scored, curW, scale, homeBase);
  var lastSeason = seasons[seasons.length - 1].name;
  var inLast = [];
  scored.forEach(function (r, i) { if (r.season === lastSeason) inLast.push(i); });
  var pickIdx = function (arr) { return inLast.map(function (i) { return arr[i]; }); };
  var speed = SELFCHECK_SPEED_VARIANTS.map(function (v) {
    var vr = scWalkForward_(seasons, homeBase, otPenalty, { k: v.k, boost: v.boost, games: v.games })
      .filter(function (r) { return !(r.season === seasons[0].name && r.idx <= SELFCHECK_WARMUP); });
    var b = scBriers_(vr, curW, scale, homeBase);
    var c = scCompare_(b, curBriers);
    var cl = scCompare_(pickIdx(b), pickIdx(curBriers));
    var isCur = v.k === ELO_K && (v.boost || 0) === (ELO_EARLY_BOOST || 0) && (!(v.boost > 0) || v.games === ELO_EARLY_GAMES);
    var verd = function (x) { return x.verdict === 'улучшает' ? 'точнее' : (x.verdict === 'ухудшает' ? 'хуже' : 'не различимо'); };
    return { name: v.name + (isCur ? ' (сейчас)' : ''), current: isCur, brier: scMean_(b), acc: scAccuracy_(vr, curW, scale, homeBase),
             effect: c.effect, err: c.err, verdict: isCur ? '—' : verd(c),
             lastN: inLast.length, lastEffect: cl.effect, lastErr: cl.err, lastVerdict: isCur ? '—' : verd(cl) };
  });

  var homeRate = scored.filter(function (r) { return r.homeWon; }).length / (scored.length || 1);
  var always = scored.map(function (r) { return Math.pow(homeRate - (r.homeWon ? 1 : 0), 2); });

  return {
    n: scored.length, nTotal: recs.length,
    perSeason: seasons.map(function (s) { return { name: s.name, n: scored.filter(function (r) { return r.season === s.name; }).length }; }),
    full: { brier: scMean_(full), acc: scAccuracy_(scored, allKeys, scale, homeBase) },
    current: current,
    simple: { brier: scMean_(simple), acc: scAccuracy_(scored, simpleW, scale, homeBase) },
    ratingOnly: { brier: scMean_(scBriers_(scored, {}, scale, homeBase)), acc: scAccuracy_(scored, {}, scale, homeBase) },
    always: { brier: scMean_(always), acc: homeRate },
    drop: dropRows, add: addRows, speed: speed
  };
}

/** Пункт меню: считает самопроверку и пишет лист «Самопроверка». */
function selfCheckFactors_() {
  var ss = SpreadsheetApp.getActive();
  var ui = SpreadsheetApp.getUi();

  var teamsSh = ss.getSheetByName(SHEET_TEAMS);
  var start = {};
  if (teamsSh) {
    teamsSh.getDataRange().getValues().slice(1).forEach(function (r) {
      var n = String(r[0] || '').trim();
      if (n && typeof r[2] === 'number') start[n] = r[2];
    });
  }
  var progSh = ss.getSheetByName('прогнозы');
  var homeBase = progSh ? Number(progSh.getRange('M2').getValue()) : HOME_BASE_ADVANTAGE;
  var scale = progSh ? Number(progSh.getRange('M3').getValue()) : 90;
  if (!(homeBase > 0)) homeBase = HOME_BASE_ADVANTAGE;
  if (!(scale > 0)) scale = 90;
  var otParts = String(FATIGUE_OT_PENALTY).split('/');
  var otPenalty = otParts.length === 2 ? Number(otParts[0]) / Number(otParts[1]) : Number(FATIGUE_OT_PENALTY);

  var seasons = [
    { name: '2025-26', schedule: scLoadGames_(ss.getSheetByName('Результаты 2025-26'), false), start: null },
    { name: '2026-27', schedule: scLoadGames_(ss.getSheetByName(SHEET_RESULTS), true), start: start }
  ];
  var res = computeSelfCheck_(seasons, homeBase, scale, otPenalty);
  if (res.n < 50) { ui.alert('Слишком мало сыгранных матчей для самопроверки (' + res.n + ').'); return; }

  var sh = ss.getSheetByName('Самопроверка');
  if (!sh) sh = ss.insertSheet('Самопроверка'); else sh.clear();
  var rows = [];
  var r4 = function (x) { return Math.round(x * 10000) / 10000; };
  var sign = function (x) { return (x > 0 ? '+' : '') + r4(x); };
  rows.push(['Самопроверка факторов модели', '', '', '', '', '']);
  rows.push(['Обновлено', Utilities.formatDate(new Date(), Session.getScriptTimeZone() || 'Europe/Moscow', 'dd.MM.yyyy HH:mm'), '', '', '', '']);
  rows.push(['Матчей в оценке', res.n + ' (' + res.perSeason.map(function (s) { return s.name + ': ' + s.n; }).join(', ') + ')', '', '', '', '']);
  rows.push(['', '', '', '', '', '']);
  var boldRows = [rows.length + 1];
  rows.push(['Модель', 'Brier (меньше — лучше)', 'Точность', '', '', '']);
  var modelsRow = rows.length + 1;
  rows.push(['Текущая модель (как в прогнозах)', r4(res.current.brier), res.current.acc, '', '', '']);
  rows.push(['Полная модель (все поправки)', r4(res.full.brier), res.full.acc, '', '', '']);
  rows.push(['Простая: рейтинг + домашний бонус ' + homeBase, r4(res.simple.brier), res.simple.acc, '', '', '']);
  rows.push(['Только рейтинг, без поправок', r4(res.ratingOnly.brier), res.ratingOnly.acc, '', '', '']);
  rows.push(['Для сравнения: «всегда хозяева»', r4(res.always.brier), res.always.acc, '', '', '']);
  rows.push(['', '', '', '', '', '']);
  boldRows.push(rows.length + 1, rows.length + 2);
  rows.push(['Тест 1. Что будет, если убрать поправку из полной модели', '', '', '', '', '']);
  rows.push(['Поправка', 'Brier без неё', 'Польза поправки', '± погрешность', 'Вывод', '']);
  var dropRow = rows.length + 1;
  res.drop.forEach(function (d) { rows.push([d.name, r4(d.brier), sign(d.effect), r4(d.err), d.verdict, '']); });
  rows.push(['', '', '', '', '', '']);
  boldRows.push(rows.length + 1, rows.length + 2);
  rows.push(['Тест 2. Что будет, если добавить поправку к простой модели', '', '', '', '', '']);
  rows.push(['Поправка', 'Вес', 'Brier', 'Изменение', '± погрешность', 'Вывод']);
  var addRow = rows.length + 1;
  res.add.forEach(function (a) { rows.push([a.name, a.weight === 1 ? 'полный' : 'половина', r4(a.brier), sign(a.effect), r4(a.err), a.verdict]); });
  rows.push(['', '', '', '', '', '']);
  boldRows.push(rows.length + 1, rows.length + 2);
  rows.push(['Тест 3. Как быстро рейтинг должен реагировать на свежие матчи (форма через рейтинг)', '', '', '', '', '']);
  rows.push(['Вариант', 'Brier', 'Изменение ± погрешность', 'Вывод (все матчи)', 'Текущий сезон: изменение', 'Вывод (сезон)']);
  var speedRow = rows.length + 1;
  (res.speed || []).forEach(function (v) {
    rows.push([v.name, r4(v.brier), v.current ? '—' : sign(v.effect) + ' ± ' + r4(v.err), v.verdict,
               v.current ? '— (' + v.lastN + ' матчей)' : sign(v.lastEffect) + ' ± ' + r4(v.lastErr), v.lastVerdict]);
  });
  rows.push(['', '', '', '', '', '']);
  rows.push(['Как читать. Brier — средняя ошибка вероятности: 0.25 — уровень монетки, чем меньше, тем лучше. ' +
             '«Польза поправки» в тесте 1 — насколько вырастет ошибка, если поправку убрать: плюс — поправка полезна, минус — без неё лучше. ' +
             '«Изменение» в тесте 2 — насколько изменится ошибка, если поправку добавить: минус — стало лучше. ' +
             'Вывод «не различимо» значит, что эффект меньше погрешности и на таком числе матчей может быть случайностью. ' +
             'Каждый матч оценивается по тому, что было известно ДО него, поэтому подглядывания в результат здесь нет.', '', '', '', '', '']);

  sh.getRange(1, 1, rows.length, 6).setValues(rows);
  sh.getRange('A1').setFontWeight('bold').setFontSize(14);
  boldRows.forEach(function (r) { sh.getRange(r, 1, 1, 6).setFontWeight('bold'); });
  sh.getRange(modelsRow, 3, 5, 1).setNumberFormat('0.0%');
  sh.getRange(rows.length, 1, 1, 6).merge().setWrap(true).setFontStyle('italic').setFontColor('#666666');
  sh.setRowHeight(rows.length, 90);
  var paint = function (rowFrom, count, col) {
    for (var i = 0; i < count; i++) {
      var cell = sh.getRange(rowFrom + i, col);
      var v = String(cell.getValue());
      if (/^помогает/.test(v)) cell.setBackground('#d9ead3');
      else if (/^мешает/.test(v)) cell.setBackground('#f4cccc');
    }
  };
  paint(dropRow, res.drop.length, 5);
  paint(addRow, res.add.length, 6);
  for (var si = 0; si < (res.speed || []).length; si++) {
    [4, 6].forEach(function (c) {
      var cell = sh.getRange(speedRow + si, c), v = String(cell.getValue());
      if (v === 'точнее') cell.setBackground('#d9ead3'); else if (v === 'хуже') cell.setBackground('#f4cccc');
    });
  }
  sh.setColumnWidth(1, 330);
  sh.autoResizeColumns(2, 5);

  var helps = res.drop.filter(function (d) { return d.verdict === 'помогает'; }).map(function (d) { return d.name; });
  var hurts = res.drop.filter(function (d) { return /^мешает/.test(d.verdict); }).map(function (d) { return d.name; });
  ui.alert(
    'Самопроверка по ' + res.n + ' матчам готова (лист «Самопроверка»).\n\n' +
    'Текущая модель: Brier ' + r4(res.current.brier) + ', точность ' + Math.round(res.current.acc * 1000) / 10 + '%.\n' +
    'Все поправки сразу: Brier ' + r4(res.full.brier) + ', точность ' + Math.round(res.full.acc * 1000) / 10 + '%.\n' +
    'Простая (рейтинг + дом): Brier ' + r4(res.simple.brier) + ', точность ' + Math.round(res.simple.acc * 1000) / 10 + '%.\n\n' +
    'Достоверно помогают: ' + (helps.length ? helps.join(', ') : 'ни одна поправка') + '.\n' +
    'Достоверно мешают: ' + (hurts.length ? hurts.join(', ') : 'ни одна поправка') + '.\n' +
    'Скорость рейтинга: ' + (function () {
      var better = (res.speed || []).filter(function (v) { return v.verdict === 'точнее'; }).map(function (v) { return v.name; });
      return better.length ? 'достоверно точнее — ' + better.join(', ') + ' (можно включить)' : 'текущая не хуже ни одного варианта';
    })() + '.\n\n' +
    'Модель при этом не изменена — это только проверка.'
  );
}

/* ============================================================================
 * П1 / Х / П2 В ОСНОВНОЕ ВРЕМЯ И ЧЕСТНАЯ ОЦЕНКА ТОТАЛОВ
 * ----------------------------------------------------------------------------
 * Обе вещи проверены пошаговым бэктестом на матчах двух сезонов (21.09.2026),
 * где каждый матч оценивался только по тому, что было известно до него.
 *
 * П1/Х/П2. Модель предсказывает итогового победителя (с овертаймом и
 * буллитами), а букмекеры считают основное время. Проверка показала:
 *  - в овертайм уходит около 22% матчей, и эта доля НЕ зависит от того,
 *    насколько равны команды (почти равные — 18.6%, средний перевес — 24.4%,
 *    явный фаворит — 20.3%). Поэтому Х = доля овертаймов по лиге;
 *  - в овертайме и буллитах перевес фаворита заметно меньше, чем в основное
 *    время (фаворит модели выигрывает 63% матчей в основное время и 59%
 *    овертаймов). Лучше всего подошло правило «в овертайме шансы фаворита
 *    сжимаются наполовину к 50/50». Отрицательных вероятностей оно не даёт:
 *      П1 = D − Х·(1/4 + D/2),   П2 = (1 − D) − Х·(3/4 − D/2).
 *
 * Тоталы. Прогноз тотала (столбец I, средние забитые и пропущенные команд)
 * ошибается ровно так же, как одно число «среднее по лиге»: 1.895 шайбы против
 * 1.897 на 743 матчах. Вероятность «больше 5.5», посчитанная из него, тоже не
 * лучше простой доли таких матчей в лиге. При этом прежняя «оценка
 * уверенности» в тотале (столбец AM) считалась по придуманному правилу — 50 +
 * 15 за каждую шайбу отклонения от 5.5 — и выдавала 60-70% там, где реальная
 * вероятность около 56-59%. Из-за этого «Купон дня» часто выбирал тотал
 * вместо победы. Теперь AM — честная вероятность того исхода, который указан
 * в столбце AJ, по доле таких матчей в лиге.
 *
 * Доли по лиге (ячейки M4 и M5) пересчитываются после каждого «Обновить
 * результаты»: текущий сезон, смешанный с прошлым как с «весом» в 150 матчей,
 * — чтобы в начале сезона пара случайных туров не раскачивала оценку.
 * ==========================================================================*/

var LEAGUE_RATE_PRIOR = 150;  // вес прошлого сезона в долях по лиге, в матчах
var OVER_LINE = 5.5;

/** Считает доли «больше 5.5» и овертаймов по лиге и пишет их в прогнозы!M4 и M5. */
function updateLeagueRates_(silent) {
  var ss = SpreadsheetApp.getActive();
  var progSh = ss.getSheetByName('прогнозы');
  if (!progSh) return null;
  var count = function (sh) {
    var n = 0, over = 0, ot = 0;
    if (!sh) return { n: 0, over: 0, ot: 0 };
    var v = sh.getDataRange().getValues();
    for (var r = 1; r < v.length; r++) {
      if (String(v[r][1]).trim() !== 'Сыгран') continue;
      var hg = v[r][4], ag = v[r][5];
      if (typeof hg !== 'number' || typeof ag !== 'number') continue;
      n++;
      if (hg + ag > OVER_LINE) over++;
      if (v[r][6] === true || String(v[r][6]).toUpperCase() === 'TRUE') ot++;
    }
    return { n: n, over: over, ot: ot };
  };
  var prev = count(ss.getSheetByName('Результаты 2025-26'));
  var cur = count(ss.getSheetByName(SHEET_RESULTS));
  var prevOver = prev.n ? prev.over / prev.n : 0.44, prevOt = prev.n ? prev.ot / prev.n : 0.22;
  var overRate = (cur.over + LEAGUE_RATE_PRIOR * prevOver) / (cur.n + LEAGUE_RATE_PRIOR);
  var otRate = (cur.ot + LEAGUE_RATE_PRIOR * prevOt) / (cur.n + LEAGUE_RATE_PRIOR);

  progSh.getRange('L4:M5').setValues([
    ['Доля матчей «больше 5.5» (лига)', Math.round(overRate * 10000) / 10000],
    ['Доля овертаймов (лига)', Math.round(otRate * 10000) / 10000]
  ]);
  progSh.getRange('M4:M5').setNumberFormat('0.0%');
  if (!silent) {
    uiAlert_('Доли по лиге обновлены: «больше 5.5» — ' + Math.round(overRate * 1000) / 10 +
      '%, овертаймы — ' + Math.round(otRate * 1000) / 10 + '% (текущий сезон: ' + cur.n + ' матчей).');
  }
  return { over: overRate, ot: otRate, curN: cur.n, curOver: cur.n ? cur.over / cur.n : null };
}

/** Пункт меню: ставит П1/Х/П2 в основное время и честную оценку тотала в несыгранные матчи. */
function setupRegulationAndTotals_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) { uiAlert_('Не найден лист "прогнозы".'); return; }

  var rates = updateLeagueRates_(true);
  var rows = openPredictionRows_(sh);

  sh.getRange(1, 50, 1, 3).setValues([['П1 в осн. время', 'Х (ничья в осн. время)', 'П2 в осн. время']]).setFontWeight('bold');
  setFormulaOnOpenRows_(sh, 50, '=IF($D{R}="";"";ROUND($D{R}-$M$5*(1/4+$D{R}/2);4))', rows);
  setFormulaOnOpenRows_(sh, 51, '=IF($D{R}="";"";$M$5)', rows);
  setFormulaOnOpenRows_(sh, 52, '=IF($D{R}="";"";ROUND((1-$D{R})-$M$5*(3/4-$D{R}/2);4))', rows);
  var lastRow = lastMatchRow_(sh);
  if (lastRow >= 2) sh.getRange(2, 50, lastRow - 1, 3).setNumberFormat('0.0%');

  // AM — вероятность того исхода тотала, что указан в AJ, по доле таких матчей в лиге
  sh.getRange('AM1').setValue('Оценка увер. Тотал (доля по лиге)');
  setFormulaOnOpenRows_(sh, 39, '=IF($AJ{R}="";"";ROUND(100*IF($AJ{R}="Больше 5.5";$M$4;1-$M$4);2))', rows);

  var under = Math.round((1 - rates.over) * 1000) / 10;
  uiAlert_(
    'Готово для ' + rows.length + ' несыгранных матчей.\n\n' +
    'П1 / Х / П2 в основное время — столбцы AX, AY, AZ. Ничья в основное время — ' + Math.round(rates.ot * 1000) / 10 +
    '% (доля овертаймов по лиге; от расклада сил она не зависит, это проверено на архиве).\n\n' +
    'Тоталы. Проверка на 743 матчах двух сезонов показала, что прогноз тотала не точнее простого среднего ' +
    'по лиге. Поэтому уверенность в тотале теперь честная: «Меньше 5.5» — ' + under + '%, «Больше 5.5» — ' +
    Math.round(rates.over * 1000) / 10 + '% (сейчас в этом сезоне больше 5.5 забивают в ' +
    (rates.curOver === null ? '—' : Math.round(rates.curOver * 1000) / 10 + '%') + ' матчей).\n\n' +
    'Раньше здесь стояли 60-70%, придуманные по отклонению от линии, и «Купон дня» из-за этого часто ' +
    'выбирал тотал вместо победы. Теперь тотал попадёт в купон, только если модель увереннее в нём, чем в победителе. ' +
    'Уже сыгранные матчи не тронуты.'
  );
}

/* ============================================================================
 * ОБЩАЯ КНОПКА «ОБНОВИТЬ ВСЁ ПОСЛЕ ИГРОВОГО ДНЯ»
 * ----------------------------------------------------------------------------
 * Одна кнопка вместо десятка: по порядку делает всё, что нужно для прогнозов
 * на следующие дни. Каждый шаг выполняется отдельно — если один сломается
 * (например, сайт с результатами не ответил), остальные всё равно пройдут, а
 * в итоговой сводке будет видно, какой шаг и почему не удался.
 *
 *  1. Результаты вчерашних матчей с sports.ru; прогнозы по ним замораживаются
 *     и помечаются честными; пересчитываются Elo, рейтинг силы и доли по лиге.
 *  1б. Календарь сезона: будущие матчи с sports.ru, которых ещё нет на листе
 *     «результаты матчей» (раньше календарь заканчивался на 30.09).
 *  2. Новые матчи из расписания на две недели вперёд добавляются в «прогнозы»
 *     со всеми формулами. Раньше этого не делал ни один пункт меню, и
 *     прогнозы заканчивались на последней вручную добавленной строке.
 *  3. Результативность дома / в гостях (Data!V:AC) — ожидаемые голы.
 *  4. Формула шансов, П1/Х/П2 и оценка тотала — в каждый несыгранный матч.
 *  5-8. Точность, банкролл, история турнирной таблицы, события дня в купоне.
 *
 * Эту же функцию запускает автообновление каждое утро (Настройки → Включить
 * автообновление).
 * ==========================================================================*/

var SYNC_HORIZON_DAYS = 14;

/**
 * Добавляет в «прогнозы» запланированные матчи из расписания на
 * SYNC_HORIZON_DAYS дней вперёд, которых там ещё нет. Формулы берутся из
 * последней несыгранной строки (copyTo сам сдвигает ссылки на нужную строку).
 * Уже сыгранные матчи не добавляются никогда: их «прогноз» считался бы по
 * рейтингу, который уже знает результат.
 */
function syncPredictionRows_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  var res = ss.getSheetByName(SHEET_RESULTS);
  if (!sh || !res) throw new Error('не найден лист «прогнозы» или «' + SHEET_RESULTS + '»');

  var lastRow = lastMatchRow_(sh);
  var existing = {};
  if (lastRow >= 2) {
    sh.getRange(2, 1, lastRow - 1, 3).getValues().forEach(function (r) {
      if (r[1] && r[2] && r[0] instanceof Date) existing[sheetDayKey_(r[0]) + '|' + String(r[1]).trim() + '|' + String(r[2]).trim()] = true;
    });
  }

  var today = todayKey_();
  var until = addDaysKey_(today, SYNC_HORIZON_DAYS);

  var v = res.getDataRange().getValues();
  var h = v[0];
  var cD = h.indexOf('Дата'), cS = h.indexOf('Статус'), cH = h.indexOf('Хозяева'), cA = h.indexOf('Гости');
  var toAdd = [];
  for (var r = 1; r < v.length; r++) {
    var d = v[r][cD];
    if (!(d instanceof Date)) continue;
    var key = sheetDayKey_(d);
    if (key < today || key > until) continue;
    if (String(v[r][cS]).trim() !== 'Запланирован') continue;
    var home = String(v[r][cH]).trim(), away = String(v[r][cA]).trim();
    if (!home || !away) continue;
    var full = key + '|' + home + '|' + away;
    if (existing[full]) continue;
    existing[full] = true;
    toAdd.push({ key: key, row: [d, home, away] }); // дата переносится как есть — без пересчёта часовых поясов
  }
  if (!toAdd.length) return 0;
  toAdd.sort(function (a, b) { return a.key < b.key ? -1 : a.key > b.key ? 1 : 0; });

  var open = openPredictionRows_(sh);
  if (!open.length) throw new Error('в «прогнозах» нет ни одной несыгранной строки, с которой можно взять формулы');
  var template = open[open.length - 1];
  var lastCol = Math.max(sh.getLastColumn(), 52);
  var start = lastRow + 1;
  if (sh.getMaxRows() < start + toAdd.length) sh.insertRowsAfter(sh.getMaxRows(), start + toAdd.length - sh.getMaxRows());

  sh.getRange(template, 1, 1, 11).copyTo(sh.getRange(start, 1, toAdd.length, 11));                     // A:K
  sh.getRange(template, 14, 1, lastCol - 13).copyTo(sh.getRange(start, 14, toAdd.length, lastCol - 13)); // N:… (L:M — параметры модели)
  sh.getRange(start, 1, toAdd.length, 3).setValues(toAdd.map(function (x) { return x.row; }));
  sh.getRange(start, COL_INTEGRITY, toAdd.length, 1).clearContent();
  return toAdd.length;
}

/** Пункт меню и утреннее автообновление: всё, что нужно после игрового дня. */
function runAfterGameDay_(e) {
  var ss = SpreadsheetApp.getActive();
  var steps = [];
  var auto = !!(e && e.triggerUid);            // запуск по расписанию (у кнопки меню аргументов нет)
  if (nhlNotReady_(auto)) return;
  var problem = /ошибк|не найден|не получилось|не удалось|не нашлось/i;

  var step = function (name, fn) {
    var before = QUIET_LOG_.length;
    try {
      var out = fn();
      var msgs = QUIET_LOG_.slice(before);
      var warn = msgs.filter(function (m) { return problem.test(m); });
      steps.push({ name: name, ok: warn.length === 0, out: out, msgs: msgs, err: warn.length ? warn[0] : null });
    } catch (e) {
      steps.push({ name: name, ok: false, msgs: QUIET_LOG_.slice(before), err: e.message });
    }
  };

  QUIET_ = true;
  QUIET_LOG_ = [];
  try {
    step('Границы диапазонов в формулах', function () { return repairFormulaBounds_(ss); });
    step('Даты и известные ошибки расписания', function () {
      return { fixedDates: repairShiftedDates_(), corrections: applyKnownCorrections_(), moved: mergeRescheduled_(ss) };
    });
    step('Результаты и рейтинг Elo', function () {
      updateResultsFromWeb();
      computeAndWriteElo_(true);   // всегда: матч мог попасть в таблицу и без sports.ru (исправления, ручной ввод)
      updateLeagueRates_(true);
    });
    step('Календарь сезона (API НХЛ)', function () { return syncScheduleFromWeb_(); });
    step('Новые матчи в прогнозах (на ' + SYNC_HORIZON_DAYS + ' дней)', function () { return syncPredictionRows_(); });
    step('Результативность дома / в гостях', function () { setupHomeAwayScoringSplit_(); });
    step('Формулы модели, П1/Х/П2, тоталы', function () {
      applyProbabilityFormula_(ss.getSheetByName('прогнозы'));
      setupRegulationAndTotals_();
    });
    step('Точность прогнозов', function () { showAccuracySummary_(); });
    step('Проверка выводов агента', function () { return agentSignalsReview_(ss); });
    step('Прогнозы экспертов из роликов', function () { return expertPicksSettle_(ss); });
    step('Составы сыгранных матчей', function () { var r = lineupsCollect_(ss, 150000); lineupKeyRender_(ss); return r; });
    if (PIPELINE_EXTRA_NAME) step(PIPELINE_EXTRA_NAME, function () { return pipelineExtra_(ss); });
    step('Банкролл', function () { updateBankrollSimulation_(); });
    step('История турнирной таблицы', function () { computeStandingsHistory_(); });
    step('События дня в купоне', function () { updateAllEventsForDay_(); });
    step('Архив линий прошлого сезона', function () { return loadHistOddsIfNeeded_(); });
    step('Мои поправки к рейтингу', function () { tweaksApply_(true); tweaksRankingRender_(); return tweaksRender_(); });
    step('Коэффициенты рынка', function () { return updateMarketOdds_(true); });
    if (publicPageOn_()) step('Публичная страница точности', function () { return publicPageUpdate_(ss, false); });
    if (PIPELINE_GAME) step('Игра «Угадай победителей»', function () { return gameAfterResults_(); });
  } finally {
    QUIET_ = false;
  }
  try { sheetsDecorate_(ss, false); } catch (e) { /* цвета вкладок — не критично */ }

  // --- сводка ---
  var lines = [];
  var firstLine = function (m) { return String(m || '').split('\n')[0].trim(); };
  steps.forEach(function (s) {
    var detail = '';
    if (!s.ok) detail = ' — ' + firstLine(s.err);
    else if (s.name.indexOf('Результаты') === 0 && s.msgs.length) {
      var rm = s.msgs.filter(function (m) { return /матч\(ей\) обновлено/.test(m); });
      detail = ' — ' + firstLine(rm.length ? rm[rm.length - 1] : s.msgs[s.msgs.length - 1]);
    }
    else if (s.name.indexOf('Новые матчи') === 0) detail = ' — добавлено: ' + (s.out || 0);
    else if (s.name.indexOf('Составы') === 0 && s.out) detail = ' — добавлено матчей: ' + s.out.added + (s.out.pending ? ', осталось ' + s.out.pending + ' (догрузятся завтра или кнопкой в меню «Агент»)' : '');
    else if (s.name.indexOf('Проверка выводов') === 0 && s.out) detail = ' — проверено новых выводов: ' + s.out.checked + (s.out.checked ? ', подтвердилось: ' + s.out.hits : '');
    else if (s.name.indexOf('Прогнозы экспертов') === 0 && s.out) detail = s.out.settled ? ' — проверено новых: ' + s.out.checked + '; ' + s.out.lines.slice(0, 3).join('; ') : ' — пока нечего проверять';
    else if (s.name.indexOf('Игра') === 0 && s.out) detail = s.out.skipped ? ' — не подключена' : ' — подсчитано прогнозов: ' + s.out.settled + (s.out.sent.length ? ', в канал: ' + s.out.sent.join(', ') : '');
    else if (s.name.indexOf('Коэффициенты') === 0 && s.out) detail = ' — линий: ' + s.out.lines + ', ближайших матчей с линией: ' + s.out.withOdds + ' из ' + s.out.upcoming;
    else if (s.name.indexOf('Даты') === 0 && s.out) {
      var parts = [];
      if (s.out.fixedDates) parts.push('исправлено дат: ' + s.out.fixedDates);
      if (s.out.corrections.length) parts.push(s.out.corrections.join('; '));
      if (s.out.moved && s.out.moved.length) parts.push('перенесённые матчи: ' + s.out.moved.join('; '));
      detail = parts.length ? ' — ' + parts.join('; ') : ' — всё в порядке';
    }
    else if (s.name.indexOf('Календарь') === 0 && s.out) {
      detail = ' — новых матчей: ' + s.out.added;
      if (s.out.unknown.length) detail += '\n     не распознаны команды: ' + s.out.unknown.slice(0, 5).join('; ');
      if (s.out.notOnWeb.length) detail += '\n     есть в таблице, но нет в календаре сайта (перенос?): ' + s.out.notOnWeb.slice(0, 5).join('; ') +
        (s.out.notOnWeb.length > 5 ? ' и ещё ' + (s.out.notOnWeb.length - 5) : '');
    }
    lines.push((s.ok ? '✓ ' : '⚠ ') + s.name + detail);
  });

  var extra = [];
  try {
    var acc = ss.getSheetByName('Точность');
    if (acc) {
      var a = acc.getRange('A4:B6').getValues();
      extra.push(Number(a[0][1]) > 0 ? 'Точность по честным прогнозам: ' + a[2][1] + ' из ' + a[0][1] + ' матчей.' : 'Точность по честным прогнозам: сыгранных матчей с честным прогнозом пока нет.');
    }
  } catch (e) { /* сводка без точности */ }
  try {
    var sh = ss.getSheetByName('прогнозы');
    var open = openPredictionRows_(sh);
    if (open.length) {
      var dates = sh.getRange(open[0], 1, open[open.length - 1] - open[0] + 1, 1).getValues()
        .map(function (r) { return r[0]; }).filter(function (d) { return d instanceof Date; });
      var last = new Date(Math.max.apply(null, dates));
      extra.push('Несыгранных матчей с прогнозом: ' + open.length + ', последний — ' +
        Utilities.formatDate(last, Session.getScriptTimeZone() || 'Europe/Moscow', 'dd.MM.yyyy') + '.');
    }
  } catch (e) { /* сводка без горизонта */ }

  var failed = steps.filter(function (s) { return !s.ok; }).length;
  var text = (failed ? 'Готово, но ' + failed + ' шаг(а) с проблемой — подробности ниже.' : 'Всё обновлено.') + '\n\n' +
    lines.join('\n') + (extra.length ? '\n\n' + extra.join('\n') : '');
  if (auto) {
    autoMark_('runAfterGameDay_', !failed, failed ? failed + ' шаг(а) с проблемой' : 'всё обновлено');
    try { ensureAutomation_(false); } catch (e2) { /* триггеры проверим в следующий раз */ }
    try { autoRender_(ss); } catch (e3) { /* лист статуса не обязателен */ }
    if (failed) autoNotifyAdmin_('⚠ Утреннее обновление таблицы: ' + failed + ' шаг(а) с проблемой\n\n' +
      lines.filter(function (l) { return l.indexOf('⚠') === 0; }).join('\n'));
  } else uiAlert_(text);
  return { steps: steps, text: text };
}

/* ============================================================================
 * КАЛЕНДАРЬ СЕЗОНА С SPORTS.RU
 * ----------------------------------------------------------------------------
 * На листе «результаты матчей» календарь был загружен только до 30.09.2026,
 * дальше шли пустые строки-заготовки. «Обновить результаты» лишь вписывает
 * счёт в уже существующие строки, поэтому новые матчи ниоткуда не появлялись —
 * и прогнозы бы закончились вместе с сентябрём.
 *
 * Страница календаря sports.ru содержит весь регулярный чемпионат. Сыгранные
 * матчи на ней записаны со счётом, будущие — с тремя прочерками вместо счёта:
 *     20.09.2026 14:00 Трактор - - - Авангард
 * Функция берёт оттуда БУДУЩИЕ матчи, которых ещё нет на листе, и вписывает их
 * в пустые строки-заготовки (дата, хозяева, гости; статус и очки считаются
 * формулами листа, как у остальных строк). Уже сыгранные и прошедшие матчи она
 * не добавляет: их результаты вносит «Обновить результаты».
 *
 * Команды проверяются по «Справочнику команд»: матч с неизвестным названием не
 * добавляется, а попадает в сводку — чтобы опечатка сайта не породила
 * «новую команду» в таблице. Будущие матчи, которые есть на листе, но пропали
 * из календаря сайта (перенос или ошибочная строка), не удаляются — только
 * перечисляются в сводке для проверки.
 * ==========================================================================*/

/** Разбирает со страницы календаря все матчи — и сыгранные, и будущие: {date, home, away}. */
function parseScheduleEntries_(pageText) {
  var text = pageText.replace(/<[^>]+>/g, ' ');
  // имя гостей заканчивается перед датой следующего матча, переводом строки, концом текста
  // или любым символом, которого не бывает в названиях команд (так не теряется последний
  // матч страницы, после которого идёт подвал сайта)
  var re = /(\d{2}\.\d{2}\.\d{4})\s*(?:\d{2}:\d{2})?\s*([А-ЯЁа-яё][А-ЯЁа-яё \-]*?)\s*(?:(?:б|от)?\d+\s*[-–]\s*(?:б|от)?\d+|[-–—]\s*[-–—:]\s*[-–—])\s*([А-ЯЁа-яё][А-ЯЁа-яё \-]*?)(?=\s*\d{2}\.\d{2}\.\d{4}|\s*\n|\s*$|\s*[^А-ЯЁа-яё \-])/g;
  var out = [], m;
  while ((m = re.exec(text)) !== null) {
    out.push({ date: m[1], home: stripTrailingOTMarker_(m[2].trim()).name, away: stripTrailingOTMarker_(m[3].trim()).name });
  }
  return out;
}


/* ============================================================================
 * ДАТЫ И ЧАСОВЫЕ ПОЯСА, ИСПРАВЛЕНИЕ ИЗВЕСТНЫХ ОШИБОК РАСПИСАНИЯ
 * ----------------------------------------------------------------------------
 * Таблица и скрипт живут в разных часовых поясах (таблица — Лос-Анджелес,
 * скрипт — Красноярск, разница 14-15 часов). Дата, созданная как «полночь по
 * времени скрипта», в таблице выглядит как 09:00-10:00 ПРЕДЫДУЩЕГО дня. Так
 * 21.09.2026 календарь с sports.ru записался со сдвигом на день назад у всех
 * 661 добавленной строки. Поэтому новые даты теперь создаются как полночь
 * в часовом поясе ТАБЛИЦЫ, а сравнение дней идёт по тому, что видно в таблице.
 * ==========================================================================*/

function sheetTz_() {
  try { return SpreadsheetApp.getActive().getSpreadsheetTimeZone(); } catch (e) { return Session.getScriptTimeZone(); }
}
/** Полночь заданного дня в часовом поясе таблицы (m — 1..12). */
function sheetDate_(y, m, d) {
  return Utilities.parseDate(y + '-' + ('0' + m).slice(-2) + '-' + ('0' + d).slice(-2), sheetTz_(), 'yyyy-MM-dd');
}
/** День так, как его показывает таблица: 'yyyy-MM-dd'. */
function sheetDayKey_(v) {
  return Utilities.formatDate(v, sheetTz_(), 'yyyy-MM-dd');
}
/** Сегодняшний день пользователя (часовой пояс скрипта): 'yyyy-MM-dd'. */
function todayKey_() {
  return Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
}
function keyToSheetDate_(key) {
  var p = key.split('-');
  return sheetDate_(+p[0], +p[1], +p[2]);
}
function addDaysKey_(key, n) {
  var p = key.split('-').map(Number);
  var d = new Date(Date.UTC(p[0], p[1] - 1, p[2] + n));
  return d.getUTCFullYear() + '-' + ('0' + (d.getUTCMonth() + 1)).slice(-2) + '-' + ('0' + d.getUTCDate()).slice(-2);
}



/**
 * Замораживает прогноз одной строки «прогнозов»: D,E (шансы), G..J
 * (ожидаемые голы и тотал), AM (оценка тотала), AX:AZ (П1/Х/П2) становятся
 * числами, а строка помечается честной. Вызывается ДО пересчёта Elo по этому
 * матчу — поэтому прогноз ещё не знает результата.
 */
function freezePredictionRow_(progSh, row) {
  [4, 5, 7, 8, 9, 10, 39, 50, 51, 52].forEach(function (c) {
    var cell = progSh.getRange(row, c);
    if (cell.getFormula() === '') return;
    cell.setValue(cell.getValue());
  });
  progSh.getRange(row, COL_INTEGRITY).setValue('да');
}

/**
 * Результат матча можно вписать и вручную. Тогда «Обновить результаты» его
 * не трогает, и прогноз по нему не замораживался бы — а после пересчёта Elo
 * задним числом «узнал» бы исход. Эта функция находит такие матчи и
 * замораживает их прогноз до пересчёта Elo.
 */
function freezeManualResults_() {
  var ss = SpreadsheetApp.getActive();
  var res = ss.getSheetByName(SHEET_RESULTS), prog = ss.getSheetByName('прогнозы');
  if (!res || !prog || prog.getLastRow() < 2) return 0;
  var idx = {};
  prog.getRange(2, 1, prog.getLastRow() - 1, 3).getValues().forEach(function (r, i) {
    if (r[1] && r[2] && r[0] instanceof Date) idx[sheetDayKey_(r[0]) + '|' + String(r[1]).trim() + '|' + String(r[2]).trim()] = i + 2;
  });
  var v = res.getDataRange().getValues();
  var h = v[0];
  var cD = h.indexOf('Дата'), cH = h.indexOf('Хозяева'), cA = h.indexOf('Гости'), cHG = h.indexOf('Г Хозяев'), cAG = h.indexOf('Г Гостей');
  var n = 0;
  for (var r = 1; r < v.length; r++) {
    if (typeof v[r][cHG] !== 'number' || typeof v[r][cAG] !== 'number' || !(v[r][cD] instanceof Date)) continue;
    var row = idx[sheetDayKey_(v[r][cD]) + '|' + String(v[r][cH]).trim() + '|' + String(v[r][cA]).trim()];
    if (!row) continue;
    if (prog.getRange(row, 4).getFormula() === '') continue; // уже заморожен
    freezePredictionRow_(prog, row);
    n++;
  }
  return n;
}

/* ============================================================================
 * КОЭФФИЦИЕНТЫ РЫНКА И СРАВНЕНИЕ «МОДЕЛЬ ПРОТИВ РЫНКА»
 * ----------------------------------------------------------------------------
 * Источник — открытая линия Pinnacle (guest.api.arcadia.pinnacle.com): без
 * ключа и регистрации, КХЛ есть. Pinnacle — самый «острый» букмекер с самой
 * низкой маржой, поэтому его линия лучше всего отражает мнение рынка.
 * Это неофициальный интерфейс сайта: он может поменяться, тогда шаг покажет
 * ошибку, а на листах останутся последние загруженные данные.
 *
 * Лист «Коэффициенты» — журнал линий: одна строка на матч. Пока матч не
 * начался, строка обновляется; после начала замораживается — остаётся
 * последняя линия до матча. По этим строкам потом честно сравнивается,
 * кто точнее: модель или рынок.
 *
 * Лист «Модель vs рынок» — для людей: по каждому ближайшему матчу шансы
 * модели и рынка рядом (маржа букмекера убрана), разница и вывод словами,
 * а сверху — счёт «кто точнее» на уже сыгранных матчах.
 * Вероятности рынка = обратные коэффициенты, нормированные на 100%.
 * ==========================================================================*/

var MARKET_API = 'https://guest.api.arcadia.pinnacle.com/0.1';
var SHEET_ODDS = 'Коэффициенты';
var SHEET_VS = 'Модель vs рынок';
var MARKET_DAYS_AHEAD = 3;
var MARKET_BLEND_W = 0.75;     // доля букмекера в «смеси» = лучший прогноз (проверено на 614 матчах)            // сколько дней вперёд показывать (линии открываются за 2-3 дня)
var MARKET_AGREE_PP = 0.05;           // до 5 п.п. разницы считаем, что модель и рынок согласны

var ODDS_HEADER = ['Обновлено (МСК)', 'Начало (МСК)', 'День матча', 'Хозяева', 'Гости',
  'Кэф П1 (с ОТ)', 'Кэф П2 (с ОТ)', 'Кэф П1 осн.', 'Кэф Х осн.', 'Кэф П2 осн.',
  'Тотал осн. (линия)', 'Кэф больше', 'Кэф меньше', 'Статус', 'ID матча', 'Начало (UTC)',
  'Кэф П1 при публикации', 'Кэф П2 при публикации', 'Линия при публикации (МСК)'];
/* Закрытие линии (CLV): кэф, по которому прогноз увидели подписчики, против последнего кэфа до начала.
 * «При публикации» = первая линия не раньше чем за CLV_PUB_HOURS до начала: утренние посты КХЛ и вечерний пост НХЛ. */
var CLV_PUB_HOURS = 18;
var CLV_MIN_EDGE = 0.02;          // таблица «видит перевес», если расходится с линией хотя бы на 2 п.п.
var ODDS_OPEN = 'линия';
var ODDS_CLOSED = 'закрыта (последняя линия до матча)';

/** Американский коэффициент (-341, +250) -> десятичный (1.29, 3.50). */
function americanToDecimal_(a) {
  a = Number(a);
  if (!isFinite(a) || a === 0) return null;
  return a > 0 ? 1 + a / 100 : 1 + 100 / Math.abs(a);
}

/** Десятичные коэффициенты одного рынка -> вероятности без маржи (сумма = 1). */
function fairProbs_(decimals) {
  if (!decimals.every(function (d) { return d > 1; })) return null;
  var inv = decimals.map(function (d) { return 1 / d; });
  var s = inv.reduce(function (x, y) { return x + y; }, 0);
  return inv.map(function (x) { return x / s; });
}


/** GET к линии Pinnacle. Возвращает {code, data}. */
function marketFetch_(path) {
  var resp = UrlFetchApp.fetch(MARKET_API + path, {
    muteHttpExceptions: true,
    headers: { 'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36' }
  });
  var code = resp.getResponseCode(), data = null;
  if (code === 200) { try { data = JSON.parse(resp.getContentText()); } catch (e) { data = null; } }
  return { code: code, data: data };
}

/** ID лиги КХЛ: сохранённый или найденный заново по названию (если Pinnacle его сменит). */
function marketLeagueId_(forceLookup) {
  var props = PropertiesService.getScriptProperties();
  var saved = Number(props.getProperty('MARKET_LEAGUE_ID'));
  if (saved && !forceLookup) return saved;
  if (!forceLookup) return MARKET_LEAGUE_ID;
  var r = marketFetch_('/sports/19/leagues?all=false');
  if (r.code !== 200 || !r.data) return null;
  var found = r.data.filter(function (l) { return MARKET_LEAGUE_RE.test(l.name || ''); })[0];
  if (!found) return null;
  props.setProperty('MARKET_LEAGUE_ID', String(found.id));
  return found.id;
}

/**
 * Разбирает ответы Pinnacle в строки линий.
 * matchups — /leagues/{id}/matchups, markets — /leagues/{id}/markets/straight.
 */
function parseMarketLines_(matchups, markets) {
  var primary = {}, unknown = {};
  (matchups || []).forEach(function (m) {
    if (!m || m.type !== 'matchup' || m.parentId || !m.participants || m.participants.length !== 2) return;
    if (m.units && m.units !== 'Regular') return;
    var home = null, away = null;
    m.participants.forEach(function (p) {
      if (p.alignment === 'home') home = p.name;
      else if (p.alignment === 'away') away = p.name;
    });
    if (!home || !away) return;
    var h = pinnacleTeamRu_(home), a = pinnacleTeamRu_(away);
    if (!h) unknown[home] = true;
    if (!a) unknown[away] = true;
    if (!h || !a) return;
    primary[m.id] = { id: String(m.id), start: new Date(m.startTime), home: h, away: a, ml: null, reg: null, tot: null };
  });

  (markets || []).forEach(function (mk) {
    var line = primary[mk.matchupId];
    if (!line || mk.isAlternate || (mk.status && mk.status !== 'open') || !mk.prices) return;
    var price = {};
    mk.prices.forEach(function (p) { price[p.designation] = { dec: americanToDecimal_(p.price), points: p.points }; });
    if (mk.type === 'moneyline' && mk.period === 0 && price.home && price.away && !price.draw) {
      line.ml = { h: price.home.dec, a: price.away.dec };
    } else if (mk.type === 'moneyline' && mk.period === 6 && price.home && price.away && price.draw) {
      line.reg = { h: price.home.dec, d: price.draw.dec, a: price.away.dec };
    } else if (mk.type === 'total' && mk.period === 6 && price.over && price.under) {
      line.tot = { line: price.over.points, over: price.over.dec, under: price.under.dec };
    }
  });

  var lines = [];
  for (var id in primary) if (primary[id].ml || primary[id].reg) lines.push(primary[id]);
  lines.sort(function (x, y) { return x.start - y.start; });
  return { lines: lines, unknown: Object.keys(unknown) };
}

/** Загружает линии, обновляет журнал «Коэффициенты» и лист «Модель vs рынок». */
function updateMarketOdds_(silent) {
  var ss = SpreadsheetApp.getActive();
  var leagueId = marketLeagueId_(false);
  var mu = marketFetch_('/leagues/' + leagueId + '/matchups');
  if (mu.code === 404) {                         // лигу переименовали/перенумеровали — ищем заново
    leagueId = marketLeagueId_(true);
    if (leagueId) mu = marketFetch_('/leagues/' + leagueId + '/matchups');
  }
  if (mu.code !== 200 || !mu.data) {
    throw new Error('не удалось получить коэффициенты: сайт линии ответил кодом ' + mu.code +
      (mu.code === 403 || mu.code === 401 ? ' (доступ из Google закрыт)' : ''));
  }
  var mk = marketFetch_('/leagues/' + leagueId + '/markets/straight');
  if (mk.code !== 200 || !mk.data) throw new Error('не удалось получить коэффициенты: рынки ответили кодом ' + mk.code);

  var parsed = parseMarketLines_(mu.data, mk.data);
  try { nhlFixStartTimes_(parsed.lines); } catch (e) { /* без расписания — время как у линии, с поправкой ниже */ }
  var written = writeOddsLog_(ss, parsed.lines, new Date());
  try { writeBestForecast_(ss); } catch (e) { /* лучший прогноз не мешает коэффициентам */ }
  try { renderBriefSheet_(ss); } catch (e) { /* витрина не мешает коэффициентам */ }
  var vs = renderMarketSheets_();
  try {   // Джарвис в игре обновляет выбор вместе с моделью (до начала матча)
    if (ss.getSheetByName(GAME_PICKS)) gameSyncJarvis_(ss);
  } catch (e) { /* игра не мешает коэффициентам */ }

  var msg = 'Коэффициенты рынка: линий загружено ' + parsed.lines.length + ', обновлено ' + written.updated +
    ', закрыто начавшихся матчей ' + written.closed + '. Ближайших матчей (' + MARKET_DAYS_AHEAD + ' дня): ' + vs.upcoming +
    ', из них с линией ' + vs.withOdds + '. Табло «чья логика точнее»: ' +
    (vs.score.n ? 'таблица ' + vs.score.win.model + ', букмекер ' + vs.score.win.market + ' из ' + vs.score.n : 'начнётся после первых сыгранных матчей') + '.';
  if (parsed.unknown.length) msg += '\nНе распознаны команды (не ошибка, но их матчи пропущены): ' + parsed.unknown.join(', ');
  if (!silent) uiAlert_(msg);
  return { lines: parsed.lines.length, updated: written.updated, closed: written.closed, unknown: parsed.unknown,
           upcoming: vs.upcoming, withOdds: vs.withOdds, message: msg };
}

/**
 * Время начала — по официальному расписанию НХЛ, а не по линии: Pinnacle ставит матчам НХЛ «время вбрасывания»
 * с запасом в 7–8 минут (02:37 вместо 02:30, 05:07 вместо 05:00), и оно попадало в таблицу, посты и постеры.
 * Матч ищем в расписании НХЛ (любой тип: предсезонка, чемпионат, плей-офф) по хозяевам, гостям и близкому времени;
 * не нашёлся — срезаем запас линии: минуты :05–:09 и :35–:39 округляем вниз до :00 / :30.
 */
function nhlFixStartTimes_(lines) {
  var official = {}, days = {};
  lines.forEach(function (L) { days[Utilities.formatDate(L.start, 'America/New_York', 'yyyy-MM-dd')] = true; });
  Object.keys(days).sort().forEach(function (d) {
    if (official[d + '|seen']) return;
    var data = null; try { data = nhlGet_('schedule/' + d); } catch (e) { data = null; }
    nhlGamesOf_(data).forEach(function (g) {
      var st = g.startTimeUTC ? new Date(g.startTimeUTC) : null, h = nhlTeamOf_(g.homeTeam), a = nhlTeamOf_(g.awayTeam);
      if (!st || isNaN(st.getTime()) || !h || !a) return;
      (official[h + '|' + a] = official[h + '|' + a] || []).push(st);
      official[Utilities.formatDate(st, 'America/New_York', 'yyyy-MM-dd') + '|seen'] = true;   // неделя расписания уже есть — дни внутри не запрашиваем
    });
    official[d + '|seen'] = true;
  });
  var fixed = 0;
  lines.forEach(function (L) {
    var best = null;
    (official[L.home + '|' + L.away] || []).forEach(function (st) {
      var diff = Math.abs(st.getTime() - L.start.getTime());
      if (diff <= 3 * 3600000 && (!best || diff < Math.abs(best.getTime() - L.start.getTime()))) best = st;
    });
    if (!best) {
      var m = L.start.getUTCMinutes() % 30;
      if (m >= 5 && m <= 9) best = new Date(L.start.getTime() - m * 60000 - L.start.getUTCSeconds() * 1000);
    }
    if (best && best.getTime() !== L.start.getTime()) { L.start = best; fixed++; }
  });
  return fixed;
}

/** Для триггера раз в 2 часа: тихо, без окон. */
function updateMarketOddsAuto_() {
  if (nhlNotReady_(true)) return;
  QUIET_ = true;
  try { var r = updateMarketOdds_(true) || {}; autoMark_('updateMarketOddsAuto_', !r.error, r.error ? r.error : 'линий: ' + (r.lines || 0) + ', матчей с линией: ' + (r.withOdds || 0)); }
  catch (e) { autoMark_('updateMarketOddsAuto_', false, e.message); }
  finally { QUIET_ = false; }
}

/* ---------------------------------------------------------------------------
 * Журнал линий (скрытый лист «Коэффициенты_журнал») — одна строка на матч.
 * Пока матч не начался, строка обновляется; после начала замораживается.
 * Видимые листы «Коэффициенты» и «Модель vs рынок» каждый раз строятся
 * заново из журнала, прогнозов и результатов — через один общий сбор данных
 * collectMarketData_, поэтому цифры на них всегда согласованы.
 * -------------------------------------------------------------------------*/

var SHEET_ODDS_LOG = 'Коэффициенты_журнал';
var MARKET_DAYS_BACK = 7;             // сколько дней назад показывать результаты на листе «Коэффициенты»

// оформление (цвета канала: тёмный фон, неоновый зелёный)
var MV_ = {
  dark: '#0a0e17', neon: '#39ff88', day: '#1f2937', head: '#e8eaf0', alt: '#f7f8fa', line: '#d0d4dc',
  favBg: '#c6f1d6', favText: '#0b6b33',           // зелёный — самый вероятный исход по букмекеру
  modelBg: '#dce8ff', modelText: '#1a4fd6',       // синий — самый вероятный исход по таблице
  okBg: '#e3f6e9', badBg: '#fde2e4', warnBg: '#fff4d6', muted: '#8a8f98', font: 'Inter'
};
var RU_WEEKDAYS_ = ['ВОСКРЕСЕНЬЕ', 'ПОНЕДЕЛЬНИК', 'ВТОРНИК', 'СРЕДА', 'ЧЕТВЕРГ', 'ПЯТНИЦА', 'СУББОТА'];
var RU_MONTHS_ = ['ЯНВАРЯ', 'ФЕВРАЛЯ', 'МАРТА', 'АПРЕЛЯ', 'МАЯ', 'ИЮНЯ', 'ИЮЛЯ', 'АВГУСТА', 'СЕНТЯБРЯ', 'ОКТЯБРЯ', 'НОЯБРЯ', 'ДЕКАБРЯ'];

/** 'yyyy-MM-dd' -> «ПОНЕДЕЛЬНИК, 21 СЕНТЯБРЯ» */
function ruDayTitle_(key) {
  var p = key.split('-').map(Number);
  var wd = new Date(Date.UTC(p[0], p[1] - 1, p[2])).getUTCDay();
  return RU_WEEKDAYS_[wd] + ', ' + p[2] + ' ' + RU_MONTHS_[p[1] - 1];
}

/** Лист журнала; при первом запуске переносит туда старый лист «Коэффициенты» (он был журналом). */
function oddsLogSheet_(ss) {
  var log = ss.getSheetByName(SHEET_ODDS_LOG);
  if (log) return log;
  log = ss.insertSheet(SHEET_ODDS_LOG);
  var old = ss.getSheetByName(SHEET_ODDS);
  if (old && String(old.getRange(1, 1).getValue()) === ODDS_HEADER[0] && old.getLastRow() >= 2) {
    var vals = old.getRange(1, 1, old.getLastRow(), ODDS_HEADER.length).getValues();
    log.getRange(1, 1, vals.length, 3).setNumberFormat('@');
    log.getRange(1, 15, vals.length, 2).setNumberFormat('@');
    log.getRange(1, 1, vals.length, ODDS_HEADER.length).setValues(vals);
  }
  try { log.hideSheet(); } catch (e) { /* в тестах */ }
  return log;
}

/** Пишет/обновляет журнал. Строки начавшихся матчей не перезаписываются. */
function writeOddsLog_(ss, lines, now) {
  var sh = oddsLogSheet_(ss);
  var NC = ODDS_HEADER.length;
  var existing = [];
  if (sh.getLastRow() >= 2) existing = sh.getRange(2, 1, sh.getLastRow() - 1, NC).getValues();
  var byId = {};
  existing.forEach(function (r) { if (String(r[14])) byId[String(r[14])] = r; });

  var fmt = function (d, p) { return Utilities.formatDate(d, 'Europe/Moscow', p); };
  var r2 = function (x) { return x ? Math.round(x * 100) / 100 : ''; };
  var updated = 0, closed = 0;

  lines.forEach(function (L) {
    var old = byId[L.id];
    if (old && old[13] === ODDS_CLOSED) return;          // матч уже начался — линию не трогаем
    if (L.start.getTime() <= now.getTime()) return;       // начавшийся матч заново не пишем
    var pub = old && old[16] ? [old[16], old[17], old[18]] : ['', '', ''];
    if (!pub[0] && L.ml && L.start.getTime() - now.getTime() <= CLV_PUB_HOURS * 3600000) pub = [r2(L.ml.h), r2(L.ml.a), fmt(now, 'dd.MM.yyyy HH:mm')];
    byId[L.id] = [fmt(now, 'dd.MM.yyyy HH:mm'), fmt(L.start, 'dd.MM.yyyy HH:mm'), fmt(L.start, 'yyyy-MM-dd'),
      L.home, L.away,
      L.ml ? r2(L.ml.h) : '', L.ml ? r2(L.ml.a) : '',
      L.reg ? r2(L.reg.h) : '', L.reg ? r2(L.reg.d) : '', L.reg ? r2(L.reg.a) : '',
      L.tot ? L.tot.line : '', L.tot ? r2(L.tot.over) : '', L.tot ? r2(L.tot.under) : '',
      ODDS_OPEN, L.id, L.start.toISOString(), pub[0], pub[1], pub[2]];
    updated++;
  });
  for (var id in byId) {
    var row = byId[id];
    if (row[13] === ODDS_OPEN && new Date(row[15]).getTime() <= now.getTime()) { row[13] = ODDS_CLOSED; closed++; }
  }

  var rows = Object.keys(byId).map(function (k) { return byId[k]; });
  rows.sort(function (a, b) { return String(a[15]) < String(b[15]) ? -1 : String(a[15]) > String(b[15]) ? 1 : 0; });

  sh.clearContents();
  sh.getRange(1, 1, 1, NC).setValues([ODDS_HEADER]).setFontWeight('bold');
  sh.getRange(1, 1, Math.max(rows.length, 1) + 1, 3).setNumberFormat('@');   // даты — текстом, чтобы таблица их не «переводила»
  sh.getRange(1, 15, Math.max(rows.length, 1) + 1, 2).setNumberFormat('@');
  sh.getRange(1, 19, Math.max(rows.length, 1) + 1, 1).setNumberFormat('@');
  rows = rows.map(function (x) { x = x.slice(0, NC); while (x.length < NC) x.push(''); return x; });   // старые строки — без колонок публикации
  if (rows.length) sh.getRange(2, 1, rows.length, NC).setValues(rows);
  sh.setFrozenRows(1);
  return { updated: updated, closed: closed, total: rows.length };
}

/** Журнал -> {'yyyy-MM-dd|Хозяева|Гости' -> линия с коэффициентами и вероятностями без маржи}. */
function readOddsLog_(ss) {
  var sh = ss.getSheetByName(SHEET_ODDS_LOG);
  var out = {};
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, ODDS_HEADER.length).getValues().forEach(function (r) {
    var num = function (x) { return typeof x === 'number' ? x : (x === '' ? null : Number(String(x).replace(',', '.'))); };
    var ml = [num(r[5]), num(r[6])], reg = [num(r[7]), num(r[8]), num(r[9])];
    var okMl = ml.every(function (x) { return x > 1; }), okReg = reg.every(function (x) { return x > 1; });
    var pml = okMl ? fairProbs_(ml) : null;
    var preg = okReg ? fairProbs_(reg) : null;
    if (!pml && preg) pml = [preg[0] + preg[1] / 2, preg[2] + preg[1] / 2];   // нет линии с ОТ — ничью делим пополам
    var tot = null;
    if (num(r[11]) > 1 && num(r[12]) > 1) tot = { line: num(r[10]), overOdds: num(r[11]), underOdds: num(r[12]), over: fairProbs_([num(r[11]), num(r[12])])[0] };
    var pubMl = [num(r[16]), num(r[17])], okPub = pubMl.every(function (x) { return x > 1; });
    out[String(r[2]) + '|' + r[3] + '|' + r[4]] = {
      pubOdds: okPub ? pubMl : null, pPubHome: okPub ? fairProbs_(pubMl)[0] : null, pubText: String(r[18] || ''),
      startText: String(r[1]), time: String(r[1]).slice(11), closed: r[13] === ODDS_CLOSED,
      mlOdds: okMl ? ml : null, pHome: pml ? pml[0] : null,
      regOdds: okReg ? reg : null, reg: preg, tot: tot
    };
  });
  return out;
}

/** Индекс максимума (для вероятностей) или минимума (для коэффициентов); null, если чисел нет. */
function argBest_(arr, wantMin) {
  var best = null;
  for (var i = 0; i < arr.length; i++) {
    if (typeof arr[i] !== 'number' || !isFinite(arr[i])) return null;
    if (best === null || (wantMin ? arr[i] < arr[best] : arr[i] > arr[best])) best = i;
  }
  return best;
}

/**
 * Общий сбор данных для обоих листов: матчи в окне [сегодня − MARKET_DAYS_BACK; сегодня + MARKET_DAYS_AHEAD]
 * и счёт «чья логика точнее» по ВСЕМ сыгранным матчам сезона, где есть честный прогноз таблицы
 * (замороженный до матча) и последняя линия букмекера до начала.
 *   Победитель матча: фаворит = сторона с вероятностью ≥ 50% (букмекер — по коэффициентам без маржи).
 *   Исход основного времени: самый вероятный из П1 / Х / П2; ничья = матч ушёл в ОТ или буллиты.
 */
function collectMarketData_(ss) {
  var odds = readOddsLog_(ss);
  var prog = ss.getSheetByName('прогнозы');
  if (!prog) throw new Error('не найден лист «прогнозы»');
  var lastRow = lastMatchRow_(prog);
  var pv = lastRow >= 2 ? prog.getRange(2, 1, lastRow - 1, 52).getValues() : [];

  var results = {};
  var rs = ss.getSheetByName(SHEET_RESULTS);
  if (rs && rs.getLastRow() >= 2) {
    rs.getRange(2, 1, rs.getLastRow() - 1, 7).getValues().forEach(function (r) {
      if (!(r[0] instanceof Date) || String(r[1]).trim() !== 'Сыгран' || typeof r[4] !== 'number' || typeof r[5] !== 'number') return;
      results[sheetDayKey_(r[0]) + '|' + String(r[2]).trim() + '|' + String(r[3]).trim()] =
        { hg: r[4], ag: r[5], ot: r[6] === true || String(r[6]).toUpperCase() === 'TRUE' };
    });
  }
  var findOdds = function (key, home, away) {
    var ks = [key, addDaysKey_(key, -1), addDaysKey_(key, 1)];   // соседняя дата — из-за часовых поясов
    for (var i = 0; i < ks.length; i++) if (odds[ks[i] + '|' + home + '|' + away]) return odds[ks[i] + '|' + home + '|' + away];
    return null;
  };

  var today = todayKey_();
  var from = addDaysKey_(today, -MARKET_DAYS_BACK), to = addDaysKey_(today, MARKET_DAYS_AHEAD);
  var score = { n: 0, win: { market: 0, model: 0, blend: 0 }, regN: 0, reg: { market: 0, model: 0 },
                brier: { market: 0, model: 0, blend: 0 }, disagree: 0, disagreeModel: 0, disagreeMarket: 0,
                clv: { n: 0, toward: 0, against: 0, flat: 0, sum: 0, since: '' },
                all: { n: 0, hit: 0, brier: 0, hist: [] } };
  var matches = [];

  pv.forEach(function (r) {
    if (!(r[0] instanceof Date) || !r[1] || !r[2] || typeof r[3] !== 'number') return;
    var key = sheetDayKey_(r[0]), home = String(r[1]).trim(), away = String(r[2]).trim();
    var o = findOdds(key, home, away);
    var res = results[key + '|' + home + '|' + away] || null;
    var honest = String(r[29]).trim() === 'да';
    var regModel = [r[49], r[50], r[51]].map(function (x) { return typeof x === 'number' ? x : null; });
    var m = {
      key: key, home: home, away: away, o: o, res: res, honest: honest,
      model: { pHome: r[3], winPick: r[3] >= 0.5 ? 0 : 1, reg: regModel, regPick: argBest_(regModel, false) },
      market: o ? { pHome: o.pHome, winPick: o.pHome === null ? null : (o.pHome >= 0.5 ? 0 : 1),
                    reg: o.reg, regPick: o.regOdds ? argBest_(o.regOdds, true) : null } : null
    };
    // закрытие линии: куда пошла линия от публикации до начала, если таблица видела перевес
    if (honest && o && o.closed && o.pubOdds && o.mlOdds && o.pHome !== null && typeof r[3] === 'number') {
      var edge = r[3] - o.pPubHome;
      if (Math.abs(edge) >= CLV_MIN_EDGE) {
        var side = edge > 0 ? 0 : 1, move = (o.pHome - o.pPubHome) * (side === 0 ? 1 : -1);
        var clv = o.pubOdds[side] / o.mlOdds[side] - 1;
        m.clv = { side: side, pub: o.pubOdds[side], close: o.mlOdds[side], clv: clv, dir: Math.abs(move) < 0.005 ? 0 : (move > 0 ? 1 : -1) };
        score.clv.n++; score.clv.sum += clv;
        if (m.clv.dir > 0) score.clv.toward++; else if (m.clv.dir < 0) score.clv.against++; else score.clv.flat++;
        if (!score.clv.since || key < score.clv.since) score.clv.since = key;
      }
    }
    if (res && honest && typeof r[3] === 'number') {
      var won = res.hg > res.ag ? 0 : 1;
      score.all.n++; if ((r[3] >= 0.5 ? 0 : 1) === won) score.all.hit++;
      score.all.brier += Math.pow(r[3] - (won === 0 ? 1 : 0), 2);
      score.all.hist.push({ key: key, home: home, away: away, p: r[3], pm: o && o.closed ? o.pHome : null, won: won, hg: res.hg, ag: res.ag, ot: res.ot, clv: m.clv || null });
    }
    if (res) {
      m.actualWin = res.hg > res.ag ? 0 : 1;
      m.actualReg = res.ot ? 1 : (res.hg > res.ag ? 0 : 2);
      m.hitMarket = (m.market && m.market.winPick !== null && o.closed) ? m.market.winPick === m.actualWin : null;
      m.hitModel = honest ? m.model.winPick === m.actualWin : null;
      // счёт: только когда есть оба честных мнения
      if (honest && o && o.closed && m.market.winPick !== null) {
        score.n++;
        if (m.market.winPick === m.actualWin) score.win.market++;
        if (m.model.winPick === m.actualWin) score.win.model++;
        score.brier.market += Math.pow(o.pHome - (m.actualWin === 0 ? 1 : 0), 2);
        score.brier.model += Math.pow(r[3] - (m.actualWin === 0 ? 1 : 0), 2);
        // смесь «таблица + букмекер» пополам — проверяем, не точнее ли она каждого по отдельности
        var pBlend = MARKET_BLEND_W * o.pHome + (1 - MARKET_BLEND_W) * r[3];
        score.brier.blend += Math.pow(pBlend - (m.actualWin === 0 ? 1 : 0), 2);
        if ((pBlend >= 0.5 ? 0 : 1) === m.actualWin) score.win.blend++;
        if (m.market.winPick !== m.model.winPick) {
          score.disagree++;
          if (m.model.winPick === m.actualWin) score.disagreeModel++; else score.disagreeMarket++;
        }
        if (m.market.regPick !== null && m.model.regPick !== null) {
          score.regN++;
          if (m.market.regPick === m.actualReg) score.reg.market++;
          if (m.model.regPick === m.actualReg) score.reg.model++;
        }
      }
    }
    if (key >= from && key <= to) matches.push(m);
  });

  var startOf = function (m) { return m.o && m.o.time ? m.o.time : '99:99'; };
  var upcoming = matches.filter(function (m) { return !m.res && m.key >= today; })
    .sort(function (a, b) { return a.key !== b.key ? (a.key < b.key ? -1 : 1) : (startOf(a) < startOf(b) ? -1 : 1); });
  var recent = matches.filter(function (m) { return m.res || m.key < today; })
    .sort(function (a, b) { return a.key !== b.key ? (a.key > b.key ? -1 : 1) : (startOf(a) < startOf(b) ? -1 : 1); });
  return { upcoming: upcoming, recent: recent, score: score, today: today };
}

/** «12 из 18 · 67%» */
/** Закрытие линии — одной строкой. */
function clvText_(s) {
  var c = s.clv || { n: 0 };
  if (!c.n) return '📈 Закрытие линии: счёт начнётся с матчей, у которых записана линия при публикации (за ' + CLV_PUB_HOURS + ' ч до начала) и линия перед стартом.';
  var pct = function (x) { return Math.round(x / c.n * 100) + '%'; }, avg = c.sum / c.n * 100;
  return '📈 Закрытие линии: когда таблица видела перевес, линия к старту шла в её сторону в ' + c.toward + ' из ' + c.n + ' матчей (' + pct(c.toward) + '), против — ' + c.against +
    ', без движения — ' + c.flat + '. Средний CLV ' + (avg >= 0 ? '+' : '') + (Math.round(avg * 10) / 10) + '% (кэф при публикации к кэфу закрытия). ' +
    'Больше половины и CLV выше нуля — таблица находит то, что рынок учитывает позже.';
}

function scoreText_(hit, n) { return n ? hit + ' из ' + n + ' · ' + Math.round(hit / n * 100) + '%' : '—'; }

/** Кто впереди — одной строкой. */
function leaderText_(s) {
  if (!s.n) return 'Счёт начнётся с первых сыгранных матчей, у которых сохранилась линия до начала.';
  var a = s.win.model, b = s.win.market;
  var who = a > b ? '🤖 Пока точнее таблица' : (b > a ? '📊 Пока точнее букмекер' : '🤝 Пока ничья');
  return who + ' (победитель матча: ' + a + ' против ' + b + ' из ' + s.n + ')' +
    (s.n < 50 ? '. Матчей пока мало — разница в пару угаданных может быть случайной, надёжно — от 100–150 матчей.' : '.');
}

/** Строка про смесь «таблица + букмекер»: точнее ли она, чем каждый по отдельности. */
function blendText_(s) {
  if (!s.n) return '🤝 Смесь таблицы и букмекера (' + Math.round(MARKET_BLEND_W * 100) + '/' + Math.round((1 - MARKET_BLEND_W) * 100) + ') — счёт начнётся с первых сыгранных матчей.';
  var bB = Math.round(s.brier.blend / s.n * 1000) / 1000, bM = Math.round(s.brier.model / s.n * 1000) / 1000, bK = Math.round(s.brier.market / s.n * 1000) / 1000;
  var best = Math.min(bB, bM, bK);
  return '🤝 Лучший прогноз (' + Math.round(MARKET_BLEND_W * 100) + '% букмекер + ' + Math.round((1 - MARKET_BLEND_W) * 100) + '% таблица): победитель ' + s.win.blend + ' из ' + s.n + ', ошибка ' + bB +
    ' (таблица ' + bM + ', букмекер ' + bK + '). ' +
    'На архиве прошлого сезона (614 матчей) смесь точнее таблицы, букмекер — точнее обоих лишь чуть-чуть.';
}

/** Готовит лист к перерисовке: чистит значения, форматы и объединения. */
function resetSheet_(ss, name, index) {
  var sh = ss.getSheetByName(name);
  if (!sh) sh = index === undefined ? ss.insertSheet(name) : ss.insertSheet(name, index);
  var mr = Math.max(sh.getMaxRows(), 1), mc = Math.max(sh.getMaxColumns ? sh.getMaxColumns() : 26, 1);
  sh.getRange(1, 1, mr, mc).breakApart();
  sh.clear();
  sh.setHiddenGridlines(true);
  sh.setFrozenRows(0);
  return sh;
}

/** Пишет блок строк с общими стилями одной операцией на свойство. */
function paintBlock_(sh, row, values, style) {
  if (!values.length) return;
  var nr = values.length, nc = values[0].length;
  var rng = sh.getRange(row, 1, nr, nc);
  rng.setValues(values);
  if (style.bg) rng.setBackgrounds(style.bg);
  if (style.color) rng.setFontColors(style.color);
  if (style.weight) rng.setFontWeights(style.weight);
  if (style.fmt) rng.setNumberFormats(style.fmt);
}

function grid_(nr, nc, v) { var g = []; for (var i = 0; i < nr; i++) { var r = []; for (var j = 0; j < nc; j++) r.push(v); g.push(r); } return g; }

/** Строит оба видимых листа. */
function renderMarketSheets_() {
  var ss = SpreadsheetApp.getActive();
  var data = collectMarketData_(ss);
  renderOddsSheet_(ss, data);
  renderVsSheet_(ss, data);
  return { upcoming: data.upcoming.length,
           withOdds: data.upcoming.filter(function (m) { return m.o && m.o.pHome !== null; }).length,
           score: data.score };
}

/* ---------------------------- лист «Коэффициенты» ---------------------------- */
function renderOddsSheet_(ss, data) {
  var sh = resetSheet_(ss, SHEET_ODDS);
  var NC = 14;
  var s = data.score;
  var row = 1;
  var put = function (vals) { var a = []; for (var i = 0; i < NC; i++) a.push(vals[i] !== undefined ? vals[i] : ''); return a; };

  // шапка
  sh.getRange(1, 1, 1, NC).merge().setValue('КОЭФФИЦИЕНТЫ  ·  НХЛ')
    .setBackground(MV_.dark).setFontColor(MV_.neon).setFontSize(18).setFontWeight('bold').setVerticalAlignment('middle');
  sh.setRowHeight(1, 44);
  sh.getRange(2, 1, 1, NC).merge().setValue('Обновлено ' + Utilities.formatDate(new Date(), 'Europe/Moscow', 'dd.MM.yyyy HH:mm') +
    ' МСК  ·  время матчей — московское  ·  «осн.» — основное время, Х — ничья в основное время')
    .setBackground(MV_.dark).setFontColor('#c9ced6').setFontSize(9);
  sh.getRange(3, 1, 1, NC).merge().setValue(leaderText_(s))
    .setBackground('#111827').setFontColor('#ffffff').setFontSize(10).setFontWeight('bold').setWrap(true);
  sh.setRowHeight(3, 30);
  // легенда
  sh.getRange(4, 1, 1, 3).merge().setValue('  самый вероятный исход по букмекеру').setBackground(MV_.favBg).setFontColor(MV_.favText).setFontWeight('bold').setFontSize(9);
  sh.getRange(4, 4, 1, 4).merge().setValue('  самый вероятный исход по таблице (синие цифры)').setBackground(MV_.modelBg).setFontColor(MV_.modelText).setFontWeight('bold').setFontSize(9);
  sh.getRange(4, 8, 1, 7).merge().setValue('  ✅ / ❌ — сбылся ли этот исход (победитель матча, с учётом ОТ)').setFontColor(MV_.muted).setFontSize(9);
  row = 6;

  var header1 = put(['Начало', 'Хозяева', 'Гости', 'Победа в матче (с ОТ)', '', 'Основное время', '', '', 'Тотал осн.', '', '', 'Счёт', 'Букмекер', 'Таблица']);
  var header2 = put(['', '', '', 'П1', 'П2', 'П1', 'Х', 'П2', 'линия', 'больше', 'меньше', '', 'угадал?', 'угадала?']);

  var titleRows = [];
  var section = function (title, list, withResult) {
    titleRows.push(row);
    sh.getRange(row, 1, 1, NC).merge().setValue(title).setFontSize(13).setFontWeight('bold').setFontColor(MV_.dark);
    sh.setRowHeight(row, 30);
    row++;
    paintBlock_(sh, row, [header1, header2], { bg: grid_(2, NC, MV_.head), weight: grid_(2, NC, 'bold') });
    sh.getRange(row, 4, 1, 2).merge(); sh.getRange(row, 6, 1, 3).merge(); sh.getRange(row, 9, 1, 3).merge();
    [1, 2, 3, 12, 13, 14].forEach(function (c) { sh.getRange(row, c, 2, 1).merge(); });
    sh.getRange(row, 1, 2, NC).setHorizontalAlignment('center').setVerticalAlignment('middle').setFontSize(9);
    row += 2;
    if (!list.length) {
      sh.getRange(row, 1, 1, NC).merge().setValue('нет матчей').setFontColor(MV_.muted).setHorizontalAlignment('center');
      row += 2; return;
    }
    var lastDay = null, idx = 0;
    list.forEach(function (m) {
      if (m.key !== lastDay) {
        sh.getRange(row, 1, 1, NC).merge().setValue(ruDayTitle_(m.key))
          .setBackground(MV_.day).setFontColor('#ffffff').setFontWeight('bold').setFontSize(9);
        row++; lastDay = m.key; idx = 0;
      }
      var o = m.o || {};
      var ml = o.mlOdds || ['', ''], reg = o.regOdds || ['', '', ''], t = o.tot || {};
      var scoreTxt = m.res ? m.res.hg + ' : ' + m.res.ag + (m.res.ot ? ' ОТ' : '') : '';
      var mark = function (hit) { return hit === null || hit === undefined ? (m.res ? '—' : '') : (hit ? '✅' : '❌'); };
      var vals = put([o.time || '—', m.home, m.away, ml[0], ml[1], reg[0], reg[1], reg[2],
                      t.line !== undefined ? t.line : '', t.overOdds || '', t.underOdds || '',
                      scoreTxt, withResult ? mark(m.hitMarket) : '', withResult ? mark(m.hitModel) : '']);
      var base = idx % 2 ? MV_.alt : '#ffffff';
      var bg = [grid_(1, NC, base)[0]], color = [grid_(1, NC, '#1f2328')[0]], weight = [grid_(1, NC, 'normal')[0]];
      // фаворит букмекера — зелёная клетка (минимальный коэффициент)
      var wm = argBest_(ml, true); if (wm !== null) { bg[0][3 + wm] = MV_.favBg; }
      var rm = argBest_(reg, true); if (rm !== null) { bg[0][5 + rm] = MV_.favBg; }
      // выбор таблицы — синие жирные цифры (на зелёном, если мнения совпали)
      [[3 + m.model.winPick, ml[m.model.winPick]], [m.model.regPick === null ? -1 : 5 + m.model.regPick, m.model.regPick === null ? '' : reg[m.model.regPick]]].forEach(function (x) {
        if (x[0] < 0 || x[1] === '' || x[1] === undefined) return;
        color[0][x[0]] = MV_.modelText; weight[0][x[0]] = 'bold';
        if (bg[0][x[0]] === base) bg[0][x[0]] = MV_.modelBg;
      });
      if (!o.mlOdds && !o.regOdds) { color[0][0] = MV_.muted; }
      weight[0][1] = 'bold'; weight[0][2] = 'bold';
      if (m.res) { weight[0][11] = 'bold'; }
      if (withResult) {
        if (m.hitMarket === true) bg[0][12] = MV_.okBg; else if (m.hitMarket === false) bg[0][12] = MV_.badBg;
        if (m.hitModel === true) bg[0][13] = MV_.okBg; else if (m.hitModel === false) bg[0][13] = MV_.badBg;
      }
      paintBlock_(sh, row, [vals], { bg: bg, color: color, weight: weight,
        fmt: [put(['@', '@', '@', '0.00', '0.00', '0.00', '0.00', '0.00', '0.0', '0.00', '0.00', '@', '@', '@'])] });
      row++; idx++;
    });
    row++;
  };

  var noOdds = data.upcoming.filter(function (m) { return !m.o; }).length;
  section('🔜  Ближайшие матчи (' + MARKET_DAYS_AHEAD + ' дня)' + (noOdds ? '  ·  без линии пока: ' + noOdds : ''), data.upcoming, false);
  section('🏁  Сыгранные за ' + MARKET_DAYS_BACK + ' дней', data.recent, true);
  sh.getRange(row, 1, 1, NC).merge().setWrap(true).setFontSize(9).setFontColor(MV_.muted).setValue(
    'Источник — линия букмекера с минимальной маржой. После начала матча его линия замораживается: так сравнение честное. ' +
    '«Таблица угадала?» считается только по честным прогнозам, сделанным до матча; «—» — прогноз не заморожен или линии не было. ' +
    'Полный журнал всех линий — на скрытом листе «' + SHEET_ODDS_LOG + '».');
  sh.setRowHeight(row, 44);

  var last = row;
  sh.getRange(5, 1, last - 4, NC).setFontFamily(MV_.font).setVerticalAlignment('middle');
  sh.getRange(6, 1, last - 6, 1).setHorizontalAlignment('center');
  sh.getRange(6, 4, last - 6, NC - 3).setHorizontalAlignment('center');
  titleRows.forEach(function (tr) { sh.getRange(tr, 1).setHorizontalAlignment('left'); });
  sh.getRange(last, 1).setHorizontalAlignment('left');
  sh.getRange(1, 1, 4, NC).setFontFamily(MV_.font);
  [58, 128, 128, 56, 56, 56, 56, 56, 52, 56, 56, 66, 72, 72].forEach(function (w, i) { sh.setColumnWidth(i + 1, w); });
  sh.setFrozenRows(3);
}

/* --------------------------- лист «Модель vs рынок» --------------------------- */
function renderVsSheet_(ss, data) {
  var sh = resetSheet_(ss, SHEET_VS);
  var NC = 13;
  var s = data.score;
  var put = function (vals) { var a = []; for (var i = 0; i < NC; i++) a.push(vals[i] !== undefined ? vals[i] : ''); return a; };

  sh.getRange(1, 1, 1, NC).merge().setValue('ЧЬЯ ЛОГИКА ТОЧНЕЕ  ·  ТАБЛИЦА ПРОТИВ БУКМЕКЕРА')
    .setBackground(MV_.dark).setFontColor(MV_.neon).setFontSize(18).setFontWeight('bold').setVerticalAlignment('middle');
  sh.setRowHeight(1, 44);
  sh.getRange(2, 1, 1, NC).merge().setValue('Обновлено ' + Utilities.formatDate(new Date(), 'Europe/Moscow', 'dd.MM.yyyy HH:mm') +
    ' МСК  ·  у букмекера убрана маржа, поэтому его проценты — чистое мнение рынка')
    .setBackground(MV_.dark).setFontColor('#c9ced6').setFontSize(9);

  // ---- табло ----
  var r = 4;
  sh.getRange(r, 1, 1, NC).merge().setValue('🏆  Табло сезона').setFontSize(13).setFontWeight('bold');
  r++;
  var board = [
    put(['', '', '', '', '🤖  ТАБЛИЦА', '', '', '📊  БУКМЕКЕР', '', '', 'Как считается']),
    put(['Победитель матча (с ОТ)', '', '', '', scoreText_(s.win.model, s.n), '', '', scoreText_(s.win.market, s.n), '', '', 'фаворит — у кого ≥ 50%']),
    put(['Исход основного времени (П1 / Х / П2)', '', '', '', scoreText_(s.reg.model, s.regN), '', '', scoreText_(s.reg.market, s.regN), '', '', 'самый вероятный из трёх']),
    put(['Средняя ошибка вероятности (Brier)', '', '', '', s.n ? Math.round(s.brier.model / s.n * 1000) / 1000 : '—', '', '',
         s.n ? Math.round(s.brier.market / s.n * 1000) / 1000 : '—', '', '', 'меньше — точнее; 0.25 — монетка']),
    put(['Когда фавориты разные — кто оказался прав', '', '', '', s.disagree ? s.disagreeModel + ' из ' + s.disagree : '—', '', '',
         s.disagree ? s.disagreeMarket + ' из ' + s.disagree : '—', '', '', 'самое интересное: кто прав в спорных'])
  ];
  sh.getRange(r, 1, board.length, NC).setValues(board);
  for (var i = 0; i < board.length; i++) {
    sh.getRange(r + i, 1, 1, 4).merge(); sh.getRange(r + i, 5, 1, 3).merge();
    sh.getRange(r + i, 8, 1, 3).merge(); sh.getRange(r + i, 11, 1, 3).merge();
  }
  sh.getRange(r, 1, 1, NC).setBackground(MV_.head).setFontWeight('bold');
  sh.getRange(r, 5).setBackground(MV_.modelBg).setFontColor(MV_.modelText);
  sh.getRange(r, 8).setBackground(MV_.favBg).setFontColor(MV_.favText);
  sh.getRange(r + 1, 5, board.length - 1, 1).setFontColor(MV_.modelText).setFontWeight('bold').setFontSize(12);
  sh.getRange(r + 1, 8, board.length - 1, 1).setFontColor(MV_.favText).setFontWeight('bold').setFontSize(12);
  sh.getRange(r + 1, 1, board.length - 1, 4).setFontWeight('bold');
  sh.getRange(r + 1, 11, board.length - 1, 3).setFontColor(MV_.muted).setFontSize(9);
  sh.getRange(r, 5, board.length, 6).setHorizontalAlignment('center');
  // победитель строки — подсветка лидера
  var lead = [[s.win.model, s.win.market, s.n], [s.reg.model, s.reg.market, s.regN]];
  lead.forEach(function (x, k) {
    if (!x[2] || x[0] === x[1]) return;
    sh.getRange(r + 1 + k, x[0] > x[1] ? 5 : 8).setBackground(x[0] > x[1] ? MV_.modelBg : MV_.favBg);
  });
  sh.getRange(r, 1, board.length, NC).setBorder(true, true, true, true, false, true, MV_.line, SpreadsheetApp.BorderStyle.SOLID);
  r += board.length;
  sh.getRange(r, 1, 1, NC).merge().setValue(blendText_(s)).setFontSize(10).setFontWeight('bold').setFontColor('#6b3fa0').setWrap(true);
  sh.setRowHeight(r, 30);
  r += 1;
  sh.getRange(r, 1, 1, NC).merge().setValue(clvText_(s)).setFontSize(10).setFontWeight('bold').setFontColor(MV_.modelText).setWrap(true);
  sh.setRowHeight(r, 30);
  r += 1;
  sh.getRange(r, 1, 1, NC).merge().setValue(leaderText_(s)).setFontSize(9).setFontColor(MV_.muted).setWrap(true);
  sh.setRowHeight(r, 30);
  r += 2;

  // ---- ближайшие матчи ----
  sh.getRange(r, 1, 1, NC).merge().setValue('🔜  Ближайшие матчи: кто кого считает фаворитом').setFontSize(13).setFontWeight('bold');
  r++;
  var h1 = put(['Начало', 'Хозяева', 'Гости', 'Победа хозяев (с ОТ)', '', '', 'Основное время: таблица', '', '', 'Основное время: букмекер', '', '', 'Вывод']);
  var h2 = put(['', '', '', 'таблица', 'букмекер', 'разница', 'П1', 'Х', 'П2', 'П1', 'Х', 'П2', '']);
  paintBlock_(sh, r, [h1, h2], { bg: grid_(2, NC, MV_.head), weight: grid_(2, NC, 'bold') });
  sh.getRange(r, 4, 1, 3).merge(); sh.getRange(r, 7, 1, 3).merge(); sh.getRange(r, 10, 1, 3).merge();
  [1, 2, 3, 13].forEach(function (c) { sh.getRange(r, c, 2, 1).merge(); });
  sh.getRange(r, 7).setBackground(MV_.modelBg).setFontColor(MV_.modelText);
  sh.getRange(r, 10).setBackground(MV_.favBg).setFontColor(MV_.favText);
  sh.getRange(r + 1, 4).setFontColor(MV_.modelText); sh.getRange(r + 1, 5).setFontColor(MV_.favText);
  sh.getRange(r, 1, 2, NC).setHorizontalAlignment('center').setVerticalAlignment('middle').setFontSize(9);
  var tableTop = r;
  r += 2;

  var verdict = function (m) {
    if (!m.market || m.market.pHome === null) return 'линии пока нет';
    var mFav = m.model.pHome >= 0.5 ? m.home : m.away, kFav = m.market.pHome >= 0.5 ? m.home : m.away;
    var mP = Math.max(m.model.pHome, 1 - m.model.pHome), kP = Math.max(m.market.pHome, 1 - m.market.pHome);
    if (mFav !== kFav) return '⚔️ Расходятся: таблица за ' + mFav + ' (' + Math.round(mP * 100) + '%), букмекер за ' + kFav + ' (' + Math.round(kP * 100) + '%)';
    var d = Math.round((mP - kP) * 100);
    if (Math.abs(mP - kP) <= MARKET_AGREE_PP) return '🤝 Согласны: фаворит ' + mFav;
    return d > 0 ? '📈 Таблица увереннее в ' + mFav + ' на ' + d + ' п.п.' : '📉 Букмекер увереннее в ' + mFav + ' на ' + (-d) + ' п.п.';
  };

  var lastDay = null, idx = 0, firstData = r;
  if (!data.upcoming.length) {
    sh.getRange(r, 1, 1, NC).merge().setValue('нет матчей в ближайшие ' + MARKET_DAYS_AHEAD + ' дня').setFontColor(MV_.muted).setHorizontalAlignment('center');
    r++;
  }
  data.upcoming.forEach(function (m) {
    if (m.key !== lastDay) {
      sh.getRange(r, 1, 1, NC).merge().setValue(ruDayTitle_(m.key))
        .setBackground(MV_.day).setFontColor('#ffffff').setFontWeight('bold').setFontSize(9);
      r++; lastDay = m.key; idx = 0;
    }
    var k = m.market, has = k && k.pHome !== null;
    var reg = m.model.reg, kreg = (k && k.reg) || [null, null, null];
    var v = verdict(m);
    var vals = put([(m.o && m.o.time) || '—', m.home, m.away,
      m.model.pHome, has ? k.pHome : '', has ? m.model.pHome - k.pHome : '',
      reg[0] === null ? '' : reg[0], reg[1] === null ? '' : reg[1], reg[2] === null ? '' : reg[2],
      kreg[0] === null ? '' : kreg[0], kreg[1] === null ? '' : kreg[1], kreg[2] === null ? '' : kreg[2], v]);
    var base = idx % 2 ? MV_.alt : '#ffffff';
    var bg = [grid_(1, NC, base)[0]], color = [grid_(1, NC, '#1f2328')[0]], weight = [grid_(1, NC, 'normal')[0]];
    color[0][3] = MV_.modelText; color[0][4] = MV_.favText;
    if (m.model.regPick !== null) { bg[0][6 + m.model.regPick] = MV_.modelBg; color[0][6 + m.model.regPick] = MV_.modelText; weight[0][6 + m.model.regPick] = 'bold'; }
    if (k && k.regPick !== null) { bg[0][9 + k.regPick] = MV_.favBg; color[0][9 + k.regPick] = MV_.favText; weight[0][9 + k.regPick] = 'bold'; }
    if (has && Math.abs(m.model.pHome - k.pHome) > 0.10) { bg[0][5] = MV_.warnBg; weight[0][5] = 'bold'; }
    if (/^⚔️/.test(v)) bg[0][12] = MV_.badBg;
    if (!has) color[0][12] = MV_.muted;
    weight[0][1] = 'bold'; weight[0][2] = 'bold';
    paintBlock_(sh, r, [vals], { bg: bg, color: color, weight: weight,
      fmt: [put(['@', '@', '@', '0%', '0%', '+0%;-0%;0%', '0%', '0%', '0%', '0%', '0%', '0%', '@'])] });
    r++; idx++;
  });
  r++;
  sh.getRange(r, 1, 1, NC).merge().setWrap(true).setFontSize(9).setFontColor(MV_.muted).setValue(
    'Синее — самый вероятный исход по таблице, зелёное — по букмекеру. «Разница» — на сколько п.п. таблица выше (+) или ниже (−) ' +
    'букмекера в победе хозяев; жёлтым — расхождение больше 10 п.п. Табло считается по всем сыгранным матчам сезона, где был честный ' +
    'прогноз таблицы (сделан до матча) и последняя линия букмекера перед началом. Коэффициенты — на листе «' + SHEET_ODDS + '».');
  sh.setRowHeight(r, 44);

  sh.getRange(3, 1, r - 2, NC).setFontFamily(MV_.font).setVerticalAlignment('middle');
  sh.getRange(1, 1, 2, NC).setFontFamily(MV_.font);
  if (r - 1 > tableTop + 1) {
    sh.getRange(tableTop + 2, 1, r - tableTop - 2, 1).setHorizontalAlignment('center');
    sh.getRange(tableTop + 2, 4, r - tableTop - 2, 9).setHorizontalAlignment('center');
  }
  [58, 128, 128, 66, 72, 62, 48, 48, 48, 48, 48, 48, 330].forEach(function (w, i) { sh.setColumnWidth(i + 1, w); });
  sh.setFrozenRows(2);
  return firstData;
}

/** Совместимость: старое имя — теперь строит оба листа. */
function buildModelVsMarket_() { return renderMarketSheets_(); }

/* ============================================================================
 * ИГРА «ОБЫГРАЙ ДЖАРВИСА» + ВИРТУАЛЬНЫЙ БАНК
 * ----------------------------------------------------------------------------
 * Бот живёт прямо в этом скрипте (веб-приложение Apps Script принимает
 * сообщения Telegram через webhook), данные — на листах таблицы.
 *
 *  • Каждый день в канал выходит пост «матчи дня» с кнопками: кто победит
 *    (с учётом ОТ и буллитов). Нажать можно прямо в канале, бот не нужен.
 *    На кнопках — коэффициент и доля голосов подписчиков.
 *  • Выбор = виртуальная ставка GAME_STAKE по коэффициенту на момент выбора.
 *    Стартовый банк GAME_START_BANK. Передумать можно до начала матча.
 *  • Игра называется «Угадай победителей игрового дня!»: текстовый пост с кнопками (логотипы клубов — премиум-эмодзи,
 *    если Telegram разрешает их боту в этом чате). Прогноз модели в игре не участвует публично (он пишется только для внутренней статистики).
 *  • Под постами — «📊 Мой счёт» (окно в канале) и «📈 История ставок» (бот присылает личную динамику и банк). Общего рейтинга нет.
 *  • После результатов: подсчёт и пост итогов дня (пост «Победитель недели» выключен: GAME_WEEKLY_POST).
 *  • Лист «Угадай победителей» — таблица игроков недели и сезона (только для вас).
 * ==========================================================================*/

var GAME_PLAYERS = 'Игра_игроки';
var GAME_PICKS = 'Игра_прогнозы';
var GAME_VIEW = 'Угадай победителей';
var GAME_VIEW_OLD = 'Обыграй Джарвиса';       // прежнее название листа — переименуем сами
var GAME_TITLE = 'Угадай победителей игрового дня!';
var GAME_STAKE = 500;
var GAME_START_BANK = 10000;
var GAME_PRIZE = 'приз от канала';
var GAME_WEEKLY_POST = false;   // пост «Победитель недели» в канал по понедельникам (выключен по вашему решению; true — включить)
var TRIGGER_TZ = 'Asia/Krasnoyarsk';   // пояс, в котором считаются часы автозапусков
var GAME_POST_HOUR = 12;          // час публикации «матчей дня» по времени скрипта (12:00 Красноярск = 08:00 МСК)
var GAME_JARVIS_ID = 'jarvis';
var GAME_JARVIS_NAME = '🎯 Мой прогноз';
var PICKS_HEADER = ['Время выбора (МСК)', 'ID игрока', 'Имя', 'ID матча', 'День матча', 'Хозяева', 'Гости',
  'Начало (UTC)', 'Выбор', 'Сторона', 'Кэф', 'Ставка', 'Статус', 'Выигрыш', 'Итог (МСК)'];
var PLAYERS_HEADER = ['ID игрока', 'Имя', 'Username', 'Первый визит (МСК)', 'Последний выбор (МСК)', 'Пишет боту'];
var PICK_WAIT = 'ждёт', PICK_WIN = 'угадал', PICK_LOSS = 'мимо';

function mskNow_(p) { return Utilities.formatDate(new Date(), 'Europe/Moscow', p || 'dd.MM.yyyy HH:mm'); }
function escHtml_(s) { return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

/* ------------------------------ Telegram API ------------------------------ */
function tgRaw_(method, payload) {
  var token = PropertiesService.getScriptProperties().getProperty('TG_BOT_TOKEN');
  if (!token) throw new Error('не указан токен бота (меню «📣 НХЛ · ТГ группа» → «Игра: подключить бота и канал»)');
  var resp = UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/' + method, {
    method: 'post', contentType: 'application/json', payload: JSON.stringify(payload || {}), muteHttpExceptions: true
  });
  var out = {};
  try { out = JSON.parse(resp.getContentText()); } catch (e) { out = { ok: false, description: 'HTTP ' + resp.getResponseCode() }; }
  return out;
}

/**
 * Отправка в Telegram. В постах с разметкой HTML обычные смайлики заменяются на премиум
 * (если они заданы командой боту, см. tgEmojiLearn_). Если Telegram премиум-смайлики
 * не принял — пост уходит ещё раз с обычными, чтобы ничего не потерялось.
 */
/* Где премиум-смайлики отвергают (по правилам Telegram — в каналах), туда не шлём их повторно:
 * помним отказ по чату неделю, иначе каждый пост уходил бы дважды. */
function tgEmojiBlocked_(chat) {
  if (!chat) return false;
  try {
    var j = JSON.parse(PropertiesService.getScriptProperties().getProperty('TG_EMOJI_BLOCK') || '{}');
    return !!j[String(chat)] && (Date.now() - j[String(chat)]) < 7 * 86400000;
  } catch (e) { return false; }
}
function tgEmojiBlockSet_(chat, on) {
  if (!chat) return;
  var pr = PropertiesService.getScriptProperties(), j = {};
  try { j = JSON.parse(pr.getProperty('TG_EMOJI_BLOCK') || '{}'); } catch (e) { j = {}; }
  if (on) j[String(chat)] = Date.now(); else delete j[String(chat)];
  pr.setProperty('TG_EMOJI_BLOCK', JSON.stringify(j));
}

function tg_(method, payload) {
  payload = payload || {};
  var field = payload.text !== undefined ? 'text' : (payload.caption !== undefined ? 'caption' : null);
  if (field && payload.parse_mode === 'HTML' && !tgEmojiBlocked_(payload.chat_id)) {
    var fancy = tgEmojify_(payload[field]);
    if (fancy !== payload[field]) {
      var p2 = JSON.parse(JSON.stringify(payload)); p2[field] = fancy;
      var r = tgRaw_(method, p2);
      if (r.ok || /not modified/i.test(r.description || '')) { tgEmojiBlockSet_(payload.chat_id, false); return r; }
      console.log('премиум-смайлики не приняты: ' + (r.description || '') + ' — отправляем с обычными');
      PropertiesService.getScriptProperties().setProperty('TG_EMOJI_LAST_ERROR', mskNow_() + ' · ' + (payload.chat_id || '') + ' · ' + (r.description || ''));
      var plain = tgRaw_(method, payload);
      if (plain.ok) tgEmojiBlockSet_(payload.chat_id, true);      // текст в порядке, дело именно в смайликах
      return plain;
    }
  }
  return tgRaw_(method, payload);
}

/* ------------------------- премиум-смайлики в постах ------------------------- */
function tgEmojiMap_() {
  try { return JSON.parse(PropertiesService.getScriptProperties().getProperty('TG_EMOJI_MAP') || '{}'); } catch (e) { return {}; }
}
function tgStripVs_(e) { return String(e).replace(/\uFE0F/g, ''); }

function tgTeamEmojiMap_() {
  try { return JSON.parse(PropertiesService.getScriptProperties().getProperty('TG_TEAM_EMOJI') || '{}'); } catch (e) { return {}; }
}

/**
 * Заменяет обычные смайлики на <tg-emoji> по сохранённой таблице и ставит логотип клуба
 * (премиум-смайлик из набора) перед названием команды. Теги и уже заменённое не трогаем.
 */
function tgEmojify_(html) {
  var map = tgEmojiMap_(), keys = Object.keys(map);
  var teams = tgTeamEmojiMap_(), names = Object.keys(teams);
  if ((!keys.length && !names.length) || !html) return html;
  keys.sort(function (a, b) { return b.length - a.length; });   // сначала длинные (составные смайлики)
  // клубы без логотипа тоже в списке: их кружок цвета не должен подмениться общим смайликом (например 🔴 → LIVE)
  var all = names.concat(Object.keys(TEAM_COLORS).filter(function (n) { return !teams[n]; }));
  all.sort(function (a, b) { return b.length - a.length; });    // «Динамо Москва» раньше «Динамо»
  var parts = String(html).split(/(<tg-emoji[^>]*>[\s\S]*?<\/tg-emoji>|<[^>]+>)/);
  return parts.map(function (chunk, i) {
    if (i % 2 === 1) return chunk;
    var saved = [];
    all.forEach(function (n) {
      var re = new RegExp('(^|[^А-ЯЁа-яёA-Za-z])((?:' + TEAM_CIRCLES_.join('|') + ')\uFE0F? )?(' + n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')(?![А-ЯЁа-яёA-Za-z])', 'g');
      var afterLogo = i > 0 && /^<tg-emoji/.test(parts[i - 1]);
      chunk = chunk.replace(re, function (m, pre, circle, name, off) {
        if (!teams[n]) {                                                         // логотипа нет — кружок как есть
          if (!circle) return m;
          saved.push(circle + name);
          return pre + '\u0001' + (saved.length - 1) + '\u0001';
        }
        if (afterLogo && !circle && !chunk.slice(0, off + pre.length).trim()) return m;   // логотип уже стоит
        // кружок перед названием заменяется логотипом; где Telegram логотип не покажет (канал) — останется этот же кружок
        var alt = circle ? circle.replace(/\uFE0F?\s$/, '') : (teamCircle_(n) || '🏒');
        saved.push('<tg-emoji emoji-id="' + teams[n] + '">' + alt + '</tg-emoji> ' + name);
        return pre + '\u0001' + (saved.length - 1) + '\u0001';
      });
    });
    keys.forEach(function (k) {
      var bare = tgStripVs_(k);
      [k, bare].filter(function (v, j, arr) { return v && arr.indexOf(v) === j; }).forEach(function (v) {
        chunk = chunk.split(v).join('\u0000' + k + '\u0000');
      });
    });
    chunk = chunk.replace(/\u0000([^\u0000]+)\u0000(\uFE0F)?/g, function (m, k) {
      return '<tg-emoji emoji-id="' + map[k] + '">' + k + '</tg-emoji>';
    });
    return chunk.replace(/\u0001(\d+)\u0001/g, function (m, n) { return saved[Number(n)]; });
  }).join('');
}

/** Админ канала пишет боту в личку премиум-смайлики — запоминаем, какой обычный смайлик на какой менять. */
function tgEmojiLearn_(msg) {
  var text = String(msg.text || '');
  var ents = (msg.entities || []).filter(function (e) { return e.type === 'custom_emoji' && e.custom_emoji_id; });
  if (!ents.length) return null;
  var covered = ents.map(function (e) { return [e.offset, e.offset + e.length]; });
  var inCustom = function (pos) { return covered.some(function (c) { return pos >= c[0] && pos < c[1]; }); };
  var map = tgEmojiMap_(), teams = tgTeamEmojiMap_(), added = [], addedTeams = [];
  ents.forEach(function (e) {
    var lineStart = text.lastIndexOf('\n', e.offset - 1) + 1;
    var before = text.slice(lineStart, e.offset).replace(/[\s=\-–—>→:]+$/, '');
    // «Торпедо [логотип]» — логотип клуба перед названием команды
    var word = before.replace(/^[\s\d.)]+/, '');
    if (word && /[А-ЯЁа-яё]/.test(word) && !/\p{Extended_Pictographic}/u.test(word)) {
      teams[word] = String(e.custom_emoji_id);
      addedTeams.push(word);
      return;
    }
    // «🏒 [премиум]» — явная пара: заменять именно этот обычный смайлик
    var m = before.match(/(\p{Extended_Pictographic}(?:\uFE0F|\u200D\p{Extended_Pictographic})*\uFE0F?)$/u);
    var base = m && !inCustom(lineStart + before.length - m[1].length) ? m[1] : text.substr(e.offset, e.length);
    if (!base) return;
    map[base] = String(e.custom_emoji_id);
    added.push({ base: base, id: String(e.custom_emoji_id) });
  });
  var props = PropertiesService.getScriptProperties();
  props.setProperty('TG_EMOJI_MAP', JSON.stringify(map));
  props.setProperty('TG_TEAM_EMOJI', JSON.stringify(teams));
  return { added: added, addedTeams: addedTeams, map: map, teams: teams };
}

/* ── Перенос премиум-смайликов между таблицами ──
 * Бот отвечает только в таблице КХЛ, поэтому привязка логотипов сохраняется там.
 * Эти два пункта переносят её в НХЛ (и обратно) копированием одной строки. */
function tgEmojiExportNow_() {
  var p = PropertiesService.getScriptProperties();
  var data = { map: tgEmojiMap_(), teams: tgTeamEmojiMap_() };
  var n = Object.keys(data.map).length + Object.keys(data.teams).length;
  if (!n) { uiAlert_('Премиум-смайлики ещё не заданы. Как задать: напишите боту /emoji.'); return; }
  var ui = SpreadsheetApp.getUi();
  ui.prompt('Смайлики для переноса (' + n + ' шт.)',
    'Скопируйте строку ниже целиком и вставьте её в другой таблице: Настройки → «Смайлики: взять из другой таблицы».\n\n' +
    JSON.stringify(data), ui.ButtonSet.OK);
}
function tgEmojiImportNow_() {
  var ui = SpreadsheetApp.getUi();
  var r = ui.prompt('Смайлики из другой таблицы', 'Вставьте строку, которую показала другая таблица (Настройки → «Смайлики: отдать в другую таблицу»):', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var data;
  try { data = JSON.parse(String(r.getResponseText() || '').trim()); } catch (e) { uiAlert_('Это не та строка — она должна начинаться с {"map":'); return; }
  if (!data || typeof data !== 'object' || (!data.map && !data.teams)) { uiAlert_('Это не та строка — она должна начинаться с {"map":'); return; }
  var p = PropertiesService.getScriptProperties();
  var map = tgEmojiMap_(), teams = tgTeamEmojiMap_(), n = 0;
  Object.keys(data.map || {}).forEach(function (k) { map[k] = String(data.map[k]); n++; });
  Object.keys(data.teams || {}).forEach(function (k) { teams[k] = String(data.teams[k]); n++; });
  p.setProperty('TG_EMOJI_MAP', JSON.stringify(map));
  p.setProperty('TG_TEAM_EMOJI', JSON.stringify(teams));
  p.deleteProperty('TG_EMOJI_BLOCK');                       // новые смайлики — пробуем везде заново
  uiAlert_('Перенесено: ' + n + '. Логотипы клубов: ' + Object.keys(teams).length + '.\n\nПроверить: 🔧 Проверки → «Телеграм: бот, канал, личка».');
}

/** Набор премиум-смайликов по ссылке t.me/addemoji/<имя>: показать все смайлики с номерами. */
function tgPackShow_(chat, arg) {
  var name = String(arg || '').replace(/^.*addemoji\//, '').replace(/[?#].*$/, '').trim();
  if (!name) { tgRaw_('sendMessage', { chat_id: chat, text: 'Пришлите так: /pack https://t.me/addemoji/khl_hd' }); return; }
  var r = tgRaw_('getStickerSet', { name: name });
  if (!r.ok) { tgRaw_('sendMessage', { chat_id: chat, text: 'Не нашёл набор «' + name + '»: ' + (r.description || '') }); return; }
  var st = (r.result.stickers || []).filter(function (x) { return x.custom_emoji_id; });
  if (!st.length) { tgRaw_('sendMessage', { chat_id: chat, text: 'В наборе «' + name + '» нет эмодзи (это стикеры, а не эмодзи).' }); return; }
  var lines = st.map(function (x, i) {
    return (i + 1) + '. <tg-emoji emoji-id="' + x.custom_emoji_id + '">' + (x.emoji || '⭐') + '</tg-emoji>  запасной: ' + (x.emoji || '—');
  });
  tgRaw_('sendMessage', { chat_id: chat, parse_mode: 'HTML', text: '📦 <b>' + escHtml_(r.result.title || name) + '</b> — ' + st.length + ' шт.' });
  for (var i = 0; i < lines.length; i += 50) {
    var res = tgRaw_('sendMessage', { chat_id: chat, parse_mode: 'HTML', text: lines.slice(i, i + 50).join('\n') });
    if (!res.ok) { tgRaw_('sendMessage', { chat_id: chat, text: 'Telegram не дал показать премиум-смайлики: ' + (res.description || '') }); return; }
  }
}

function tgIsChannelAdmin_(userId) {
  var p = PropertiesService.getScriptProperties();
  if (p.getProperty('TG_OWNER_ID') && String(p.getProperty('TG_OWNER_ID')) === String(userId)) return true;   // владелец, заданный вручную
  var channel = p.getProperty('TG_CHANNEL');
  if (!channel) { TG_ADMIN_CHECK_WHY_ = 'в настройках не указан канал'; return false; }
  var r = tgRaw_('getChatMember', { chat_id: channel, user_id: userId });
  if (!r.ok) { TG_ADMIN_CHECK_WHY_ = 'Telegram не дал проверить: ' + (r.description || 'нет ответа'); return false; }
  var st = r.result && r.result.status;
  if (st === 'creator' || st === 'administrator') return true;
  TG_ADMIN_CHECK_WHY_ = 'в канале ' + channel + ' у вас статус «' + st + '»';
  return false;
}
var TG_ADMIN_CHECK_WHY_ = '';

/** Ответ «только для админов» — с причиной и способом открыть доступ владельцу. */
function tgAdminDenied_(chat, userId) {
  tgRaw_('sendMessage', { chat_id: chat, text: 'Эта команда — только для админов канала.\n\n' +
    'Почему не пустило: ' + (TG_ADMIN_CHECK_WHY_ || 'неизвестно') + '.\n' +
    'Ваш Telegram ID: ' + userId + '\n\n' +
    'Если это ваш канал: в Apps Script → ⚙️ Настройки проекта → Свойства скрипта добавьте свойство TG_OWNER_ID со значением ' + userId + ' — и команда заработает.' });
}

function tgEmojiListText_(map, title) {
  var keys = Object.keys(map), teams = tgTeamEmojiMap_(), names = Object.keys(teams);
  if (!keys.length && !names.length) return (title ? title + '\n\n' : '') + 'Премиум-смайлики не заданы — в постах обычные.';
  return (title ? title + '\n\n' : '') + keys.map(function (k) {
    return k + ' → <tg-emoji emoji-id="' + map[k] + '">' + k + '</tg-emoji>';
  }).concat(names.length ? ['', '<b>Логотипы клубов:</b>'].concat(names.map(function (n) {
    return '<tg-emoji emoji-id="' + teams[n] + '">' + (teamCircle_(n) || '🏒') + '</tg-emoji> ' + escHtml_(n);
  })) : []).join('\n');
}

/* ------------------------------- листы игры ------------------------------- */
function gameSheet_(ss, name, header) {
  var sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.getRange(1, 1, 1, header.length).setValues([header]).setFontWeight('bold');
    sh.getRange(1, 1, 1000, header.length).setNumberFormat('@');   // всё текстом: id, даты
    sh.setFrozenRows(1);
    try { sh.hideSheet(); } catch (e) { /* тесты */ }
  }
  return sh;
}
function gameReadPicks_(ss) {
  var sh = gameSheet_(ss, GAME_PICKS, PICKS_HEADER);
  var n = sh.getLastRow() - 1;
  return n > 0 ? sh.getRange(2, 1, n, PICKS_HEADER.length).getValues() : [];
}
function gameWritePicks_(ss, rows) {
  var sh = gameSheet_(ss, GAME_PICKS, PICKS_HEADER);
  var old = sh.getLastRow() - 1;
  if (old > 0) sh.getRange(2, 1, old, PICKS_HEADER.length).clearContent();
  if (rows.length) {
    sh.getRange(2, 1, rows.length, PICKS_HEADER.length).setNumberFormat('@');
    sh.getRange(2, 11, rows.length, 2).setNumberFormat('0.00');
    sh.getRange(2, 14, rows.length, 1).setNumberFormat('0');
    sh.getRange(2, 1, rows.length, PICKS_HEADER.length).setValues(rows);
  }
}
function gameUpsertPlayer_(ss, user, startedBot) {
  var sh = gameSheet_(ss, GAME_PLAYERS, PLAYERS_HEADER);
  if (sh.getRange(1, 6).getValue() !== PLAYERS_HEADER[5]) sh.getRange(1, 6).setValue(PLAYERS_HEADER[5]).setFontWeight('bold');
  var n = sh.getLastRow() - 1;
  var ids = n > 0 ? sh.getRange(2, 1, n, 1).getValues().map(function (r) { return String(r[0]); }) : [];
  var name = gamePlayerName_(user);
  var i = ids.indexOf(String(user.id));
  var uname = user.username ? '@' + user.username : '';
  if (i === -1) {
    sh.getRange(sh.getLastRow() + 1, 1, 1, 6).setValues([[String(user.id), name, uname, mskNow_(), mskNow_(), startedBot ? 'да' : '']]);
  } else {
    var row = sh.getRange(i + 2, 1, 1, 6).getValues()[0];
    sh.getRange(i + 2, 2, 1, 5).setValues([[name, uname, row[3], mskNow_(), startedBot ? 'да' : row[5]]]);
  }
  return name;
}
/** id игроков, которые запускали бота (им можно писать в личку). */
function gameBotUsers_(ss) {
  var sh = ss.getSheetByName(GAME_PLAYERS);
  if (!sh || sh.getLastRow() < 2) return {};
  var out = {};
  sh.getRange(2, 1, sh.getLastRow() - 1, 6).getValues().forEach(function (r) { if (r[5] === 'да') out[String(r[0])] = true; });
  return out;
}
/** username бота (для ссылок t.me/…), запоминается. */
function gameBotUsername_() {
  var props = PropertiesService.getScriptProperties();
  var u = props.getProperty('TG_BOT_USERNAME');
  if (u) return u;
  var me = tg_('getMe', {});
  if (me.ok && me.result && me.result.username) { props.setProperty('TG_BOT_USERNAME', me.result.username); return me.result.username; }
  return null;
}
/** Нижний ряд кнопок: «Мой счёт» (всплывающее окно прямо в канале) и «История ставок» (бот пришлёт личную динамику и банк). */
function gameStatsRow_() {
  var row = [{ text: '📊 Мой счёт', callback_data: 'me' }];
  var bot = gameBotUsername_();
  if (bot) row.push({ text: '📈 История ставок', url: 'https://t.me/' + bot + '?start=history' });
  return row;
}
/** Короткая сводка игрока для всплывающего окна (Telegram — до 200 символов). */
function gameMeShort_(ss, id) {
  var rows = gameReadPicks_(ss), wk = weekStartKey_(todayKey_());
  var season = gameStats_(rows), week = gameStats_(rows, wk, addDaysKey_(wk, 6));
  var me = season.filter(function (s) { return s.id === id; })[0];
  if (!me) return 'Ты ещё не сделал ни одного прогноза — жми на команду в посте 👆';
  var mw = week.filter(function (s) { return s.id === id; })[0];
  var waiting = rows.filter(function (r) { return String(r[1]) === id && r[12] === PICK_WAIT; }).length;
  var fmt = function (x) { return String(x).replace(/\B(?=(\d{3})+(?!\d))/g, ' '); };
  var t = '📊 Неделя: ' + (mw && mw.settled ? mw.wins + ' из ' + mw.settled : '—') +
    '\nСезон: ' + me.wins + ' из ' + me.settled +
    '\n💰 Банк: ' + fmt(me.bank) + ' ₽ (' + (me.profit >= 0 ? '+' : '−') + fmt(Math.abs(me.profit)) + ')' +
    (waiting ? '\n⏳ Ждут результата: ' + waiting : '') + '\n📈 Динамика — кнопка «История ставок»';
  return t.slice(0, 200);
}
function gamePlayerName_(user) {
  var n = [user.first_name, user.last_name].filter(function (x) { return x; }).join(' ').trim();
  return n || (user.username ? '@' + user.username : 'Игрок ' + String(user.id).slice(-4));
}

/** Матчи, на которые сейчас принимаются прогнозы: линия есть, матч не начался. */
function gameOpenMatches_(ss, now) {
  now = now || new Date();
  var sh = ss.getSheetByName(SHEET_ODDS_LOG);
  var out = [];
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, ODDS_HEADER.length).getValues().forEach(function (r) {
    var start = new Date(String(r[15]));
    var h = Number(r[5]), a = Number(r[6]);
    if (r[13] !== ODDS_OPEN || !(start.getTime() > now.getTime())) return;
    if (!(h > 1 && a > 1)) {                          // нет линии «с ОТ» — берём честные кэфы из основного времени
      var reg = [Number(r[7]), Number(r[8]), Number(r[9])];
      if (!reg.every(function (x) { return x > 1; })) return;
      var p = fairProbs_(reg); var ph = p[0] + p[1] / 2;
      h = Math.round(100 / ph) / 100; a = Math.round(100 / (1 - ph)) / 100;
    }
    out.push({ id: String(r[14]), key: String(r[2]), time: String(r[1]).slice(11), start: start, home: r[3], away: r[4], oddsH: h, oddsA: a });
  });
  out.sort(function (x, y) { return x.start - y.start; });
  return out;
}

/** Записать/изменить выбор. Возвращает {ok, text}. */
function gamePick_(ss, user, matchId, side, now) {
  now = now || new Date();
  var match = gameOpenMatches_(ss, now).filter(function (m) { return m.id === String(matchId); })[0];
  if (!match) return { ok: false, text: '⛔ Матч уже начался — приём прогнозов закрыт.' };
  var isJarvis = user.id === GAME_JARVIS_ID;
  var name = isJarvis ? GAME_JARVIS_NAME : gameUpsertPlayer_(ss, user);
  var team = side === 'h' ? match.home : match.away, odds = side === 'h' ? match.oddsH : match.oddsA;
  var rows = gameReadPicks_(ss);
  var row = [mskNow_(), String(user.id), name, match.id, match.key, match.home, match.away, match.start.toISOString(),
             team, side, odds, GAME_STAKE, PICK_WAIT, '', ''];
  var idx = -1;
  for (var i = 0; i < rows.length; i++) if (String(rows[i][1]) === String(user.id) && String(rows[i][3]) === match.id) { idx = i; break; }
  var changed = idx !== -1 && rows[idx][9] !== side;
  if (idx !== -1 && !changed) return { ok: true, text: '✅ Уже принято: ' + team + ' (кэф ' + Number(rows[idx][10]).toFixed(2) + ' на победу с учётом ОТ и буллитов). Изменить можно до начала матча.', match: match };
  if (idx === -1) rows.push(row); else rows[idx] = row;
  gameWritePicks_(ss, rows);
  return { ok: true, match: match,
    text: (changed ? '🔄 Выбор изменён: ' : '✅ Принято: ') + team + ' · кэф ' + odds.toFixed(2) + ' (победа с учётом ОТ и буллитов) · ставка ' + GAME_STAKE +
          ' ₽. Передумать можно до начала матча.' };
}

/** Голоса подписчиков (без Джарвиса) по матчу. */
function gameCounts_(rows, matchId) {
  var c = { h: 0, a: 0 };
  rows.forEach(function (r) { if (String(r[3]) === String(matchId) && String(r[1]) !== GAME_JARVIS_ID) c[r[9]] = (c[r[9]] || 0) + 1; });
  return c;
}

/** Короткие названия для кнопок: длинные обрезаются Telegram посередине. */
var GAME_SHORT = { 'Шанхайские Драконы': 'Шанхай', 'Салават Юлаев': 'Салават', 'Динамо Москва': 'Динамо М',
  'Динамо Минск': 'Динамо Мн' };
function gameShort_(team) { return GAME_SHORT[team] || team; }

/** Клавиатура: по строке на матч, две кнопки «Команда · кэф · % голосов». */
function gameKeyboard_(matches, rows) {
  return { inline_keyboard: gameMatchRows_(matches, rows).concat([gameStatsRow_()]) };
}
function gameMatchRows_(matches, rows) {
  return (function () { return matches.map(function (m) {
    var c = gameCounts_(rows, m.id), tot = c.h + c.a;
    var pct = function (x) { return tot ? ' · ' + Math.round(x / tot * 100) + '%' : ''; };
    return [
      { text: gameShort_(m.home) + ' · ' + m.oddsH.toFixed(2) + ' с ОТ' + pct(c.h), callback_data: 'p|' + m.id + '|h' },
      { text: gameShort_(m.away) + ' · ' + m.oddsA.toFixed(2) + ' с ОТ' + pct(c.a), callback_data: 'p|' + m.id + '|a' }
    ];
  }); })();
}

/** Матчи ближайшего игрового дня (по МСК): в пост «матчи дня» не попадают матчи следующего дня. */
function gameMatchesForPost_(ss, now) {
  now = now || new Date();
  var soon = gameOpenMatches_(ss, now).filter(function (m) { return m.start.getTime() - now.getTime() <= 24 * 3600 * 1000; });
  if (!soon.length) return soon;
  var day = soon[0].key;
  return soon.filter(function (m) { return m.key === day; });
}

function gamePostText_(matches) {
  // матчи одного дня — дата в шапке; нескольких дней (команда /matches) — дата над каждым днём
  var days = [];
  matches.forEach(function (m) { if (days.indexOf(m.key) === -1) days.push(m.key); });
  var line = function (m) { return m.time + '  ' + teamMark_(m.home) + ' — ' + teamMark_(m.away); };
  var body;
  if (days.length <= 1) {
    body = (days.length ? ruDayTitle_(days[0]).toLowerCase() : '') + '\n\n' + matches.map(line).join('\n');
  } else {
    body = '\n' + days.map(function (d) {
      return '📅 <b>' + escHtml_(ruDayTitle_(d).toLowerCase()) + '</b>\n' +
        matches.filter(function (m) { return m.key === d; }).map(line).join('\n');
    }).join('\n\n');
  }
  return '🎯 <b>' + GAME_TITLE + '</b>\n' + body +
    '\n\nЖми, кто победит (с учётом ОТ и буллитов) 👇\n' +
    'ℹ️ Кэфы на кнопках — на победу с учётом овертайма и буллитов (ничьей нет), поэтому они ниже, ' +
    'чем П1/П2 в основное время у букмекеров.\nКаждый выбор — виртуальная ставка ' + GAME_STAKE +
    ' ₽ по коэффициенту на кнопке. Стартовый банк у всех — ' + GAME_START_BANK.toLocaleString('ru-RU') +
    ' ₽. Передумать можно до начала матча.';
}

/** Пост «матчи дня» в канал. */
function gamePostMatches_(silent) {
  var ss = SpreadsheetApp.getActive();
  var props = PropertiesService.getScriptProperties();
  var channel = props.getProperty('TG_CHANNEL');
  if (!channel) throw new Error('не указан канал (меню «📣 НХЛ · ТГ группа» → «Игра: подключить бота и канал»)');
  gameSyncJarvis_(ss);
  var matches = gameMatchesForPost_(ss);
  if (!matches.length) { if (!silent) uiAlert_('Сейчас нет матчей с открытой линией на ближайшие сутки — публиковать нечего.'); return { posted: false, matches: 0 }; }
  var res = tg_('sendMessage', { chat_id: channel, text: gamePostText_(matches), parse_mode: 'HTML',
                                 reply_markup: gameKeyboard_(matches, gameReadPicks_(ss)) });
  if (!res.ok) throw new Error('Telegram не принял пост: ' + (res.description || 'нет ответа'));
  props.setProperty('GAME_LAST_POST', JSON.stringify({ chat: res.result.chat.id, msg: res.result.message_id, ids: matches.map(function (m) { return m.id; }) }));
  dailyMark_('game');
  if (!silent) uiAlert_('Опубликовано в канал: ' + matches.length + ' матч(ей) с кнопками.');
  return { posted: true, matches: matches.length };
}
function gamePostMatchesAuto_() {
  var p = PropertiesService.getScriptProperties();
  if (!p.getProperty('TG_BOT_TOKEN') || !p.getProperty('TG_CHANNEL')) return;   // игра не подключена
  QUIET_ = true;
  try { gamePostMatches_(true); autoMark_('gamePostMatchesAuto_', true, 'пост «матчи дня»'); } catch (e) { Logger.log('Игра: ' + e.message); autoMark_('gamePostMatchesAuto_', false, e.message); } finally { QUIET_ = false; }
}

/** Выбор Джарвиса = фаворит модели; обновляется до начала матча вместе с моделью. */
function gameSyncJarvis_(ss, now) {
  now = now || new Date();
  var open = gameOpenMatches_(ss, now);
  if (!open.length) return 0;
  var prog = ss.getSheetByName('прогнозы');
  if (!prog) return 0;
  var last = lastMatchRow_(prog);
  var pv = last >= 2 ? prog.getRange(2, 1, last - 1, 4).getValues() : [];
  var model = {};
  pv.forEach(function (r) {
    if (!(r[0] instanceof Date) || typeof r[3] !== 'number') return;
    model[sheetDayKey_(r[0]) + '|' + String(r[1]).trim() + '|' + String(r[2]).trim()] = r[3];
  });
  var n = 0;
  open.forEach(function (m) {
    var p = [m.key, addDaysKey_(m.key, -1), addDaysKey_(m.key, 1)].map(function (k) { return model[k + '|' + m.home + '|' + m.away]; })
      .filter(function (x) { return typeof x === 'number'; })[0];
    if (p === undefined) return;
    var r = gamePick_(ss, { id: GAME_JARVIS_ID }, m.id, p >= 0.5 ? 'h' : 'a', now);
    if (r.ok) n++;
  });
  return n;
}

/* ------------------------------ webhook бота ------------------------------ */
function doPost(e) {
  try {
    var props = PropertiesService.getScriptProperties();
    if (!e || !e.parameter || e.parameter.s !== props.getProperty('TG_WEBHOOK_SECRET')) return HtmlService.createHtmlOutput('forbidden');
    var update = JSON.parse(e.postData.contents);
    var cache = CacheService.getScriptCache();
    if (cache.get('u' + update.update_id)) return HtmlService.createHtmlOutput('dup');   // Telegram иногда присылает повторно
    cache.put('u' + update.update_id, '1', 21600);
    var lock = LockService.getScriptLock();
    lock.waitLock(25000);
    try { gameHandleUpdate_(update); } finally { lock.releaseLock(); }
  } catch (err) {
    try {
      Logger.log('doPost: ' + err.message);
      PropertiesService.getScriptProperties().setProperty('GAME_LAST_ERROR', mskNow_() + ' — ' + String(err && err.message || err).slice(0, 300));
    } catch (e2) { /* */ }
  }
  return HtmlService.createHtmlOutput('OK');   // именно HtmlService: ContentService даёт Telegram редирект 302
}
function doGet() { return HtmlService.createHtmlOutput('Бот на связи.'); }

function gameHandleUpdate_(update) {
  var ss = SpreadsheetApp.getActive();
  if (update.callback_query) {
    var q = update.callback_query, parts = String(q.data || '').split('|');
    if (parts[0] === 'me') {
      tg_('answerCallbackQuery', { callback_query_id: q.id, text: gameMeShort_(ss, String(q.from.id)), show_alert: true });
      return;
    }
    if (parts[0] !== 'p') { tg_('answerCallbackQuery', { callback_query_id: q.id }); return; }
    var res = gamePick_(ss, q.from, parts[1], parts[2] === 'a' ? 'a' : 'h');
    tg_('answerCallbackQuery', { callback_query_id: q.id, text: res.text, show_alert: false });
    if (res.ok && q.message && q.message.reply_markup) gameRefreshKeyboard_(ss, q.message);
    return;
  }
  var msg = update.message;
  if (!msg || !msg.text || !msg.chat || msg.chat.type !== 'private') return;
  var words = String(msg.text).trim().split(/\s+/);
  var cmd = words[0].toLowerCase().replace(/@.*/, '');
  var arg = (words[1] || '').toLowerCase();
  var chat = msg.chat.id;
  if (cmd === '/scout') {
    if (!tgIsChannelAdmin_(msg.from.id)) { tgAdminDenied_(chat, msg.from.id); return; }
    tg_('sendMessage', { chat_id: chat, text: '🔎 Смотрю, что нового…' });
    try { scoutNowTo_(chat); } catch (e) { tg_('sendMessage', { chat_id: chat, text: '⚠️ Разведчик: ' + e.message }); }
    return;
  }
  if (cmd === '/agent') {
    if (!tgIsChannelAdmin_(msg.from.id)) { tgAdminDenied_(chat, msg.from.id); return; }
    PropertiesService.getScriptProperties().setProperty('TG_ADMIN_ID', String(chat));
    var pa = PropertiesService.getScriptProperties();
    if (!pa.getProperty('TAVILY_KEY') || !pa.getProperty('GEMINI_KEY')) {
      tg_('sendMessage', { chat_id: chat, text: '🧠 Запомнил: сводки агента буду присылать сюда. Но ключей TAVILY_KEY / GEMINI_KEY ещё нет в свойствах скрипта.' });
      return;
    }
    tg_('sendMessage', { chat_id: chat, text: '🧠 Запомнил: сводки буду присылать сюда каждый день в 09:00 МСК. Собираю сводку на сегодня…' });
    try {
      var ar = agentDailyBrief_(null, chat);
      if (!ar.matches) tg_('sendMessage', { chat_id: chat, text: 'Сегодня матчей нет.' });
    } catch (e) { tg_('sendMessage', { chat_id: chat, text: '⚠️ Агент: ' + e.message }); }
    return;
  }
  var hasCustom = (msg.entities || []).some(function (e) { return e.type === 'custom_emoji'; });
  if (hasCustom || cmd === '/emoji' || cmd === '/emoji_reset' || cmd === '/pack') {
    if (!tgIsChannelAdmin_(msg.from.id)) {
      if (cmd.charAt(0) === '/') tgAdminDenied_(chat, msg.from.id);
      return;
    }
    if (cmd === '/emoji_reset') {
      PropertiesService.getScriptProperties().setProperty('TG_EMOJI_MAP', '{}');
      PropertiesService.getScriptProperties().setProperty('TG_TEAM_EMOJI', '{}');
      tgRaw_('sendMessage', { chat_id: chat, text: 'Готово: премиум-смайлики сброшены, в постах снова обычные.' });
      return;
    }
    if (cmd === '/pack') { tgPackShow_(chat, words[1]); return; }
    if (hasCustom) {
      var learned = tgEmojiLearn_(msg);
      tgRaw_('sendMessage', { chat_id: chat, parse_mode: 'HTML', text: tgEmojiListText_(learned.map,
        '✅ Запомнил: смайликов ' + learned.added.length + ', логотипов ' + learned.addedTeams.length + '. Теперь в автопостах так:') +
        '\n\nЧтобы премиум-смайлик заменял конкретный обычный, пишите их парой: <b>🏒 [премиум]</b> — по паре в строке. ' +
        'Посмотреть список — /emoji, сбросить всё — /emoji_reset' });
      return;
    }
    var err = PropertiesService.getScriptProperties().getProperty('TG_EMOJI_LAST_ERROR');
    tgRaw_('sendMessage', { chat_id: chat, parse_mode: 'HTML', text: tgEmojiListText_(tgEmojiMap_(), '✨ <b>Премиум-смайлики в постах</b>') +
      '\n\nКак задать: пришлите мне сообщение, где каждая строка — пара «обычный смайлик, пробел, премиум-смайлик», например:\n' +
      '🏒 [ваша шайба]\n🔴 [ваш LIVE]\n🤖 [ваш робот]\n\n' +
      'Логотипы клубов — так же, название и логотип в строке (название как в постах):\nТорпедо [логотип]\nДинамо Москва [логотип]\n\n' +
      'Посмотреть все смайлики набора — /pack ссылка_на_набор\n' +
      'Смайлики, которые есть в постах: 🎮 🏒 🔴 🤖 🏁 ⏳ ✅ ❌ 📊 🏆 💰 👇 🥇 🥈 🥉 📈 🎯\n' +
      'Премиум-смайлик без пары заменит тот обычный, к которому его привязал автор набора. Сбросить — /emoji_reset' + (err ? '\n\n⚠️ Последний отказ Telegram: ' + escHtml_(err) : '') });
    return;
  }
  if (cmd === '/start') gameUpsertPlayer_(ss, msg.from, true);     // запустил бота — можно присылать личные итоги
  if (cmd === '/start' && (arg === 'me' || arg === 'top' || arg === 'history')) cmd = '/' + arg;   // ссылки t.me/бот?start=history
  if (cmd === '/top') cmd = '/history';          // общего рейтинга больше нет — показываем свою историю
  if (cmd === '/start' || cmd === '/help') {
    tg_('sendMessage', { chat_id: chat, parse_mode: 'HTML', text:
      '🎯 <b>' + GAME_TITLE + '</b>\n\nУгадывай, кто победит в матчах КХЛ (с учётом ОТ и буллитов), и следи за своим банком.\n\n' +
      '• Каждый выбор — виртуальная ставка ' + GAME_STAKE + ' ₽ по коэффициенту на кнопке. Стартовый банк у всех — ' + GAME_START_BANK.toLocaleString('ru-RU') + ' ₽.\n' +
      '• Передумать можно до начала матча.' + (GAME_WEEKLY_POST ? '\n• Победитель недели — у кого больше угаданных исходов. Приз — ' + escHtml_(GAME_PRIZE) + '.' : '') + '\n\n' +
      'Команды:\n/matches — матчи с кнопками\n/me — мой счёт и банк\n/history — история ставок и банк по дням\n\nПосле каждого игрового дня я буду присылать тебе личные итоги.' });
    gameSendMatches_(ss, chat);
  } else if (cmd === '/matches') {
    gameSendMatches_(ss, chat);
  } else if (cmd === '/me') {
    tg_('sendMessage', { chat_id: chat, parse_mode: 'HTML', text: gameMeText_(ss, String(msg.from.id)) });
  } else if (cmd === '/history') {
    tg_('sendMessage', { chat_id: chat, parse_mode: 'HTML', text: gameHistoryText_(ss, String(msg.from.id)) });
  }
}

function gameSendMatches_(ss, chat) {
  gameSyncJarvis_(ss);
  var matches = gameOpenMatches_(ss).slice(0, 15);
  if (!matches.length) { tg_('sendMessage', { chat_id: chat, text: 'Сейчас нет матчей с открытой линией. Линии появляются за 2–3 дня до игры.' }); return; }
  tg_('sendMessage', { chat_id: chat, parse_mode: 'HTML', text: gamePostText_(matches), reply_markup: gameKeyboard_(matches, gameReadPicks_(ss)) });
}

/** Обновляет проценты на кнопках поста (не чаще раза в 10 секунд на пост). */
function gameRefreshKeyboard_(ss, message) {
  var cache = CacheService.getScriptCache(), key = 'kb' + message.chat.id + '_' + message.message_id;
  if (cache.get(key)) return;
  cache.put(key, '1', 10);
  var ids = [];
  (message.reply_markup.inline_keyboard || []).forEach(function (row) {
    var p = String((row[0] || {}).callback_data || '').split('|'); if (p[0] === 'p') ids.push(p[1]);
  });
  var open = gameOpenMatches_(ss), byId = {};
  open.forEach(function (m) { byId[m.id] = m; });
  var list = ids.map(function (id) { return byId[id]; }).filter(function (m) { return m; });
  if (!list.length) return;
  tg_('editMessageReplyMarkup', { chat_id: message.chat.id, message_id: message.message_id, reply_markup: gameKeyboard_(list, gameReadPicks_(ss)) });
}

/* --------------------------- подсчёт и рейтинги --------------------------- */
/** Подводит итоги по сыгранным матчам. Возвращает только что подсчитанные выборы. */
function gameSettle_(ss) {
  var results = {};
  var rs = ss.getSheetByName(SHEET_RESULTS);
  if (rs && rs.getLastRow() >= 2) {
    rs.getRange(2, 1, rs.getLastRow() - 1, 6).getValues().forEach(function (r) {
      if (!(r[0] instanceof Date) || String(r[1]).trim() !== 'Сыгран' || typeof r[4] !== 'number' || typeof r[5] !== 'number') return;
      results[sheetDayKey_(r[0]) + '|' + String(r[2]).trim() + '|' + String(r[3]).trim()] = { hg: r[4], ag: r[5] };
    });
  }
  var rows = gameReadPicks_(ss), fresh = [];
  rows.forEach(function (r) {
    if (r[12] !== PICK_WAIT) return;
    var key = String(r[4]);
    var res = [key, addDaysKey_(key, -1), addDaysKey_(key, 1)].map(function (k) { return results[k + '|' + r[5] + '|' + r[6]]; })
      .filter(function (x) { return x; })[0];
    if (!res) return;
    var winSide = res.hg > res.ag ? 'h' : 'a';
    var won = r[9] === winSide;
    r[12] = won ? PICK_WIN : PICK_LOSS;
    r[13] = won ? Math.round(Number(r[11]) * (Number(r[10]) - 1)) : -Number(r[11]);
    r[14] = mskNow_();
    r.score = res.hg + ':' + res.ag;
    fresh.push(r);
  });
  if (fresh.length) gameWritePicks_(ss, rows.map(function (r) { return r.slice(0, PICKS_HEADER.length); }));
  return fresh;
}

/** Понедельник недели для 'yyyy-MM-dd'. */
function weekStartKey_(key) {
  var p = key.split('-').map(Number);
  var wd = new Date(Date.UTC(p[0], p[1] - 1, p[2])).getUTCDay();
  return addDaysKey_(key, -((wd + 6) % 7));
}

/** Статистика игроков по выборам (фильтр по дню матча). */
function gameStats_(rows, fromKey, toKey) {
  var by = {};
  rows.forEach(function (r) {
    var key = String(r[4]);
    if ((fromKey && key < fromKey) || (toKey && key > toKey)) return;
    var id = String(r[1]);
    var s = by[id] || (by[id] = { id: id, name: r[2], picks: 0, settled: 0, wins: 0, profit: 0 });
    s.name = id === GAME_JARVIS_ID ? GAME_JARVIS_NAME : r[2]; s.picks++;
    if (r[12] === PICK_WIN || r[12] === PICK_LOSS) { s.settled++; s.profit += Number(r[13]) || 0; if (r[12] === PICK_WIN) s.wins++; }
  });
  var list = Object.keys(by).map(function (k) { var s = by[k]; s.bank = GAME_START_BANK + s.profit; return s; });
  // при полном равенстве человек выше Джарвиса — чтобы «обыграть машину» было реально
  list.sort(function (a, b) { return b.wins - a.wins || b.bank - a.bank || a.settled - b.settled ||
    (a.id === GAME_JARVIS_ID ? 1 : 0) - (b.id === GAME_JARVIS_ID ? 1 : 0); });
  list.forEach(function (s, i) { s.place = i + 1; });
  return list;
}

function gameTopText_(ss) {
  var rows = gameReadPicks_(ss), wk = weekStartKey_(todayKey_());
  var week = gameStats_(rows, wk, addDaysKey_(wk, 6)).filter(function (s) { return s.settled; });
  var season = gameStats_(rows);
  var line = function (s) {
    return (s.id === GAME_JARVIS_ID ? '<b>' : '') + s.place + '. ' + escHtml_(s.name) + ' — ' + s.wins + ' из ' + s.settled +
      ' · банк ' + s.bank.toLocaleString('ru-RU') + ' ₽' + (s.id === GAME_JARVIS_ID ? '</b>' : '');
  };
  var j = week.filter(function (s) { return s.id === GAME_JARVIS_ID; })[0];
  var top = week.slice(0, 10).map(line);
  if (j && j.place > 10) top.push('…', line(j));
  var beat = j ? week.filter(function (s) { return s.id !== GAME_JARVIS_ID && s.wins > j.wins; }).length : 0;
  var richest = season.filter(function (s) { return s.settled; }).sort(function (a, b) { return b.bank - a.bank; })[0];
  return '🏆 <b>Рейтинг недели</b> (с ' + wk.slice(8, 10) + '.' + wk.slice(5, 7) + ')\n\n' +
    (top.length ? top.join('\n') : 'Пока нет подсчитанных матчей на этой неделе.') +
    (j ? '\n\nМой прогноз обгоняют: ' + beat + ' чел.' : '') +
    (richest ? '\n💰 Самый большой банк сезона: ' + escHtml_(richest.name) + ' — ' + richest.bank.toLocaleString('ru-RU') + ' ₽' : '');
}

function gameMeText_(ss, id) {
  var rows = gameReadPicks_(ss), wk = weekStartKey_(todayKey_());
  var season = gameStats_(rows), week = gameStats_(rows, wk, addDaysKey_(wk, 6));
  var me = season.filter(function (s) { return s.id === id; })[0];
  if (!me) return 'Ты ещё не сделал ни одного прогноза. Жми /matches 👇';
  var mw = week.filter(function (s) { return s.id === id; })[0];
  var waiting = rows.filter(function (r) { return String(r[1]) === id && r[12] === PICK_WAIT; })
    .map(function (r) { return '• ' + escHtml_(r[5]) + ' — ' + escHtml_(r[6]) + ': ' + escHtml_(r[8]) + ' (' + Number(r[10]).toFixed(2) + ')'; });
  return '👤 <b>' + escHtml_(me.name) + '</b>\n\n' +
    'Сезон: угадано ' + me.wins + ' из ' + me.settled + (me.settled ? ' (' + Math.round(me.wins / me.settled * 100) + '%)' : '') + '\n' +
    'Неделя: ' + (mw ? mw.wins + ' из ' + mw.settled : '—') + '\n' +
    '💰 Банк: ' + me.bank.toLocaleString('ru-RU') + ' ₽ (' + (me.profit >= 0 ? '+' : '') + me.profit.toLocaleString('ru-RU') + ')\n' +
    (waiting.length ? '\n⏳ Ждут результата:\n' + waiting.join('\n') : '') + '\n\nИстория ставок и банк по дням — /history';
}

/** Итоги: пост дня в канал и по понедельникам — победитель прошлой недели. */
var GAME_RESULTS_POST = false;   // пост «Итоги игрового дня» в канал выключен по вашему решению; личные итоги игрокам приходят как раньше
function gameResultsPost_(ss, fresh) {
  if (!GAME_RESULTS_POST) return [];
  var props = PropertiesService.getScriptProperties();
  var channel = props.getProperty('TG_CHANNEL');
  var sent = [];
  if (!channel || !props.getProperty('TG_BOT_TOKEN')) return sent;
  if (fresh.length) {
    var byMatch = {}, byUser = {};
    fresh.forEach(function (r) {
      var mk = r[3];
      var m = byMatch[mk] || (byMatch[mk] = { home: r[5], away: r[6], score: r.score, jarvis: null, n: 0, ok: 0 });
      if (String(r[1]) === GAME_JARVIS_ID) m.jarvis = r;
      else { m.n++; if (r[12] === PICK_WIN) m.ok++; var u = byUser[r[1]] || (byUser[r[1]] = { name: r[2], n: 0, ok: 0 }); u.n++; if (r[12] === PICK_WIN) u.ok++; }
    });
    var lines = Object.keys(byMatch).map(function (k) {
      var m = byMatch[k];
      return teamMark_(m.home) + ' ' + m.score + ' ' + teamMark_(m.away) +
        (m.n ? '  ·  угадали ' + Math.round(m.ok / m.n * 100) + '% из ' + m.n : '');
    });
    var perfect = Object.keys(byUser).filter(function (k) { return byUser[k].n >= 2 && byUser[k].ok === byUser[k].n; })
      .map(function (k) { return escHtml_(byUser[k].name); });
    var text = '🏁 <b>ИТОГИ ИГРОВОГО ДНЯ</b>\n\n' + lines.join('\n') +
      (perfect.length ? '\n\n🎯 Угадали всё: ' + perfect.slice(0, 10).join(', ') + (perfect.length > 10 ? ' и ещё ' + (perfect.length - 10) : '') : '') +
      '\n\nСвой счёт и историю ставок — кнопками ниже 👇';
    var r1 = tg_('sendMessage', { chat_id: channel, text: text, parse_mode: 'HTML', reply_markup: { inline_keyboard: [gameStatsRow_()] } });
    if (r1.ok) sent.push('итоги дня');
  }
  // понедельник: победитель прошлой недели (один раз)
  var today = todayKey_(), wk = weekStartKey_(today);
  if (GAME_WEEKLY_POST && today === wk && props.getProperty('GAME_WEEK_POSTED') !== wk) {
    var prev = addDaysKey_(wk, -7);
    var st = gameStats_(gameReadPicks_(ss), prev, addDaysKey_(prev, 6)).filter(function (s) { return s.settled; });
    var humans = st.filter(function (s) { return s.id !== GAME_JARVIS_ID; });
    var j = st.filter(function (s) { return s.id === GAME_JARVIS_ID; })[0];
    if (humans.length) {
      var w = humans[0];
      var txt = '🏆 <b>ПОБЕДИТЕЛЬ НЕДЕЛИ</b>\n\n🥇 ' + escHtml_(w.name) + ' — ' + w.wins + ' из ' + w.settled + ', банк ' + w.bank.toLocaleString('ru-RU') + ' ₽' +
        (humans[1] ? '\n🥈 ' + escHtml_(humans[1].name) + ' — ' + humans[1].wins + ' из ' + humans[1].settled : '') +
        (humans[2] ? '\n🥉 ' + escHtml_(humans[2].name) + ' — ' + humans[2].wins + ' из ' + humans[2].settled : '') +
        '\n\nПриз — ' + escHtml_(GAME_PRIZE) + '. Новая неделя уже началась 👇';
      var r2 = tg_('sendMessage', { chat_id: channel, text: txt, parse_mode: 'HTML' });
      if (r2.ok) { sent.push('победитель недели'); props.setProperty('GAME_WEEK_POSTED', wk); }
    }
  }
  return sent;
}

/** Личные итоги в бот тем, кто его запускал. Возвращает число отправленных сообщений. */
function gameNotifyPlayers_(ss, fresh) {
  if (!fresh.length || !PropertiesService.getScriptProperties().getProperty('TG_BOT_TOKEN')) return 0;
  var allowed = gameBotUsers_(ss), byUser = {};
  fresh.forEach(function (r) {
    var id = String(r[1]);
    if (id === GAME_JARVIS_ID || !allowed[id]) return;
    (byUser[id] = byUser[id] || []).push(r);
  });
  var rows = gameReadPicks_(ss), wk = weekStartKey_(todayKey_());
  var season = gameStats_(rows), week = gameStats_(rows, wk, addDaysKey_(wk, 6));
  var fmt = function (x) { return String(x).replace(/\B(?=(\d{3})+(?!\d))/g, ' '); };
  var n = 0;
  Object.keys(byUser).forEach(function (id) {
    var lines = byUser[id].map(function (r) {
      var win = r[12] === PICK_WIN;
      return (win ? '✅ ' : '❌ ') + escHtml_(r[5]) + ' ' + (r.score || '') + ' ' + escHtml_(r[6]) + ' — твой выбор ' + escHtml_(r[8]) +
        ' (' + Number(r[10]).toFixed(2) + ') ' + (win ? '+' : '−') + fmt(Math.abs(Number(r[13]))) + ' ₽';
    });
    var me = season.filter(function (s) { return s.id === id; })[0];
    var mw = week.filter(function (s) { return s.id === id; })[0];
    var text = '🏁 <b>Твои итоги</b>\n\n' + lines.join('\n') +
      (me ? '\n\n💰 Банк: ' + fmt(me.bank) + ' ₽' : '') +
      (mw ? '\n🗓 Неделя: ' + mw.wins + ' из ' + mw.settled : '') +
      '\n\nИстория ставок — /history · новые матчи — /matches';
    var res = tg_('sendMessage', { chat_id: Number(id), text: text, parse_mode: 'HTML' });
    if (res.ok) n++;
  });
  return n;
}

/** Лист «Угадай победителей»: таблица игроков недели и сезона (только для вас, в канал не публикуется). */
function gameRender_(ss) {
  var rows = gameReadPicks_(ss), today = todayKey_(), wk = weekStartKey_(today);
  var week = gameStats_(rows, wk, addDaysKey_(wk, 6)).filter(function (s) { return s.settled || s.picks; });
  var season = gameStats_(rows);
  var old = ss.getSheetByName(GAME_VIEW_OLD);
  if (old && !ss.getSheetByName(GAME_VIEW)) try { old.setName(GAME_VIEW); } catch (e) {}
  week = week.filter(function (s) { return s.id !== GAME_JARVIS_ID; });
  season = season.filter(function (s) { return s.id !== GAME_JARVIS_ID; });
  var sh = resetSheet_(ss, GAME_VIEW);
  var NC = 7;
  sh.getRange(1, 1, 1, NC).merge().setValue(GAME_TITLE.toUpperCase())
    .setBackground(MV_.dark).setFontColor(MV_.neon).setFontSize(18).setFontWeight('bold');
  sh.setRowHeight(1, 44);
  var players = season.filter(function (s) { return s.id !== GAME_JARVIS_ID; }).length;
  sh.getRange(2, 1, 1, NC).merge().setValue('Игроков: ' + players + '  ·  выбор = виртуальная ставка ' + GAME_STAKE + ' ₽  ·  старт ' +
    GAME_START_BANK.toLocaleString('ru-RU') + ' ₽  ·  обновлено ' + mskNow_() + ' МСК').setBackground(MV_.dark).setFontColor('#c9ced6').setFontSize(9);
  var r = 4;
  var table = function (title, list) {
    sh.getRange(r, 1, 1, NC).merge().setValue(title).setFontSize(13).setFontWeight('bold'); r++;
    var head = ['Место', 'Игрок', 'Угадано', 'Сыграно', 'Точность', 'Банк, ₽', 'Итог, ₽'];
    sh.getRange(r, 1, 1, NC).setValues([head]).setBackground(MV_.head).setFontWeight('bold').setHorizontalAlignment('center'); r++;
    if (!list.length) { sh.getRange(r, 1, 1, NC).merge().setValue('пока нет прогнозов').setFontColor(MV_.muted); r += 2; return; }
    var shown = list.slice(0, 30);
    var j = list.filter(function (s) { return s.id === GAME_JARVIS_ID; })[0];
    if (j && shown.indexOf(j) === -1) shown.push(j);
    var vals = shown.map(function (s) {
      var medal = s.place === 1 ? '🥇' : s.place === 2 ? '🥈' : s.place === 3 ? '🥉' : String(s.place);
      return [medal, s.name, s.wins, s.settled, s.settled ? s.wins / s.settled : '', s.bank, s.profit];
    });
    var bg = shown.map(function (s, i) { return grid_(1, NC, s.id === GAME_JARVIS_ID ? MV_.modelBg : (i % 2 ? MV_.alt : '#ffffff'))[0]; });
    var color = shown.map(function (s) { return [null, s.id === GAME_JARVIS_ID ? MV_.modelText : '#1f2328', null, null, null, null, s.profit >= 0 ? MV_.favText : '#c62828']; });
    var weight = shown.map(function (s) { return [s.place <= 3 ? 'bold' : 'normal', 'bold', 'bold', 'normal', 'normal', 'normal', 'bold']; });
    paintBlock_(sh, r, vals, { bg: bg, color: color.map(function (row) { return row.map(function (c) { return c || '#1f2328'; }); }), weight: weight,
      fmt: vals.map(function () { return ['@', '@', '0', '0', '0%', '#,##0', '+#,##0;-#,##0;0']; }) });
    sh.getRange(r, 1, vals.length, 1).setHorizontalAlignment('center');
    sh.getRange(r, 3, vals.length, 5).setHorizontalAlignment('center');
    r += vals.length + 1;
    if (j) {
      var beat = list.filter(function (s) { return s.id !== GAME_JARVIS_ID && s.wins > j.wins; }).length;
      sh.getRange(r - 1, 1, 1, NC).merge().setValue('Мой прогноз обгоняют: ' + beat + ' чел.').setFontColor(MV_.modelText).setFontSize(9);
      r++;
    }
  };
  table('🗓  Неделя с ' + wk.slice(8, 10) + '.' + wk.slice(5, 7), week);
  table('🏆  Сезон', season.filter(function (s) { return s.picks; }));
  sh.getRange(r, 1, 1, NC).merge().setWrap(true).setFontSize(9).setFontColor(MV_.muted).setValue(
    'Прогнозы принимаются кнопками в канале или в боте до начала матча. Место — по числу угаданных исходов (с учётом ОТ и буллитов), при равенстве — по банку. ' +
    'Банк — результат виртуальных ставок по ' + GAME_STAKE + ' ₽ по коэффициенту на момент выбора. Деньги ненастоящие.');
  sh.setRowHeight(r, 44);
  sh.getRange(3, 1, r - 2, NC).setFontFamily(MV_.font).setVerticalAlignment('middle');
  [60, 220, 80, 80, 80, 100, 90].forEach(function (w, i) { sh.setColumnWidth(i + 1, w); });
  sh.setFrozenRows(2);
  return { week: week.length, season: season.length };
}

/** Шаг общей кнопки: подсчёт, пост итогов, лист рейтинга. */
function gameAfterResults_() {
  var ss = SpreadsheetApp.getActive();
  if (!ss.getSheetByName(GAME_PICKS) && !PropertiesService.getScriptProperties().getProperty('TG_BOT_TOKEN')) return { skipped: true, settled: 0, sent: [] };
  var fresh = gameSettle_(ss);
  var sent = [];
  try { sent = gameResultsPost_(ss, fresh); } catch (e) { sent = ['ошибка поста: ' + e.message]; }
  try { var dm = gameNotifyPlayers_(ss, fresh); if (dm) sent.push('личные итоги: ' + dm); } catch (e) { sent.push('ошибка личных итогов: ' + e.message); }
  gameRender_(ss);
  return { settled: fresh.length, sent: sent };
}

/* --------------------------------- меню --------------------------------- */
function gameConnect_() {
  var ui = SpreadsheetApp.getUi();
  var props = PropertiesService.getScriptProperties();
  var t = ui.prompt('Бот игры', 'Токен бота от @BotFather' + (props.getProperty('TG_BOT_TOKEN') ? ' (оставьте пустым, чтобы не менять)' : '') + ':', ui.ButtonSet.OK_CANCEL);
  if (t.getSelectedButton() !== ui.Button.OK) return;
  if (t.getResponseText().trim()) props.setProperty('TG_BOT_TOKEN', t.getResponseText().trim());
  var c = ui.prompt('Канал', 'Username канала, например @jarvis_khl' + (props.getProperty('TG_CHANNEL') ? ' (сейчас ' + props.getProperty('TG_CHANNEL') + '; пусто — не менять)' : '') + ':', ui.ButtonSet.OK_CANCEL);
  if (c.getSelectedButton() !== ui.Button.OK) return;
  var ch = c.getResponseText().trim();
  if (ch) props.setProperty('TG_CHANNEL', /^-?\d+$/.test(ch) || ch.charAt(0) === '@' ? ch : '@' + ch);

  // рабочий адрес веб-приложения: Google иногда подставляет тестовый (/dev), по которому Telegram не пускают
  var url = props.getProperty('TG_WEBAPP_URL') || '';
  var auto = '';
  try { auto = ScriptApp.getService().getUrl() || ''; } catch (e) { auto = ''; }
  if (!/\/exec$/.test(url) && /\/exec$/.test(auto)) url = auto;
  var u = ui.prompt('Адрес веб-приложения',
    'Откройте в редакторе скрипта «Развернуть» → «Управление развертываниями», скопируйте «URL веб-приложения» (заканчивается на /exec) и вставьте сюда.' +
    (url ? '\n\nСейчас: ' + url + '\n(оставьте пустым, чтобы не менять)' : ''), ui.ButtonSet.OK_CANCEL);
  if (u.getSelectedButton() !== ui.Button.OK) return;
  if (u.getResponseText().trim()) url = u.getResponseText().trim();
  if (!/^https:\/\/script\.google\.com\/.+\/exec$/.test(url)) {
    uiAlert_('Нужен адрес вида https://script.google.com/macros/s/…/exec\n\nЕсли его нет: «Развернуть» → «Новое развертывание» → тип «Веб-приложение», «Выполнять от имени: я», «У кого есть доступ: Все» → «Развернуть» и скопируйте URL.');
    return;
  }
  props.setProperty('TG_WEBAPP_URL', url);
  var secret = props.getProperty('TG_WEBHOOK_SECRET');
  if (!secret) { secret = Utilities.getUuid().replace(/-/g, ''); props.setProperty('TG_WEBHOOK_SECRET', secret); }
  var me = tg_('getMe', {});
  if (!me.ok) { uiAlert_('Telegram не принял токен: ' + (me.description || '')); return; }
  props.setProperty('TG_BOT_USERNAME', me.result.username);
  var wh = tg_('setWebhook', { url: url + '?s=' + secret, allowed_updates: ['message', 'callback_query'], drop_pending_updates: true });
  var adm = tg_('getChatMember', { chat_id: props.getProperty('TG_CHANNEL'), user_id: me.result.id });
  var isAdmin = adm.ok && (adm.result.status === 'administrator' || adm.result.status === 'creator');
  uiAlert_('Бот @' + me.result.username + ' подключён: ' + (wh.ok ? 'приём нажатий включён ✓' : 'webhook не установлен — ' + wh.description) + '\n' +
    'Канал ' + props.getProperty('TG_CHANNEL') + ': ' + (isAdmin ? 'бот — администратор ✓' : 'бот НЕ администратор — добавьте его в админы канала с правом публиковать сообщения') + '\n\n' +
    'Дальше: «Игра» → «Опубликовать матчи дня сейчас» для проверки. При включённом автообновлении пост будет выходить каждый день в ' + GAME_POST_HOUR + ':00 (по Красноярску).');
}
function gamePostNow_() { gamePostMatches_(false); }

/** Пункт меню: почему не работают кнопки — спрашивает у Telegram состояние приёма нажатий. */
function gameDiagnose_() {
  var props = PropertiesService.getScriptProperties();
  var info = tg_('getWebhookInfo', {});
  if (!info.ok) { uiAlert_('Telegram не ответил: ' + (info.description || '') + '\nПроверьте токен: «Игра» → «Подключить бота и канал».'); return; }
  var w = info.result || {};
  var url = String(w.url || '');
  var lines = [];
  lines.push('Адрес приёма: ' + (url ? url.replace(/\?s=.*/, '?s=…') : 'НЕ УСТАНОВЛЕН'));
  lines.push('Ожидают обработки: ' + (w.pending_update_count || 0));
  if (w.last_error_message) {
    lines.push('Последняя ошибка Telegram: ' + w.last_error_message + (w.last_error_date ? ' (' + Utilities.formatDate(new Date(w.last_error_date * 1000), 'Europe/Moscow', 'dd.MM HH:mm') + ' МСК)' : ''));
  }
  var le = props.getProperty('GAME_LAST_ERROR');
  if (le) lines.push('Последняя ошибка скрипта: ' + le);
  var advice = [];
  if (!url) advice.push('Приём не включён — нажмите «Подключить бота и канал».');
  else if (/\/dev\?/.test(url)) advice.push('Установлен тестовый адрес (/dev) — Telegram по нему не пускают. Нажмите «Подключить бота и канал» и вставьте URL, который заканчивается на /exec.');
  if (/401|403|Unauthorized|Forbidden/i.test(w.last_error_message || '')) advice.push('Google не пускает Telegram: в «Управление развертываниями» у веб-приложения должно быть «У кого есть доступ: Все» (не «все, у кого есть аккаунт Google»).');
  if (/302|Moved/i.test(w.last_error_message || '')) advice.push('Скрипт отвечает старой версией кода: «Развернуть» → «Управление развертываниями» → карандаш → «Версия: новая» → «Развернуть».');
  if (/404|Not Found/i.test(w.last_error_message || '')) advice.push('Адрес не найден: развертывание удалено или URL скопирован не целиком. Вставьте URL заново.');
  if (!advice.length && !w.last_error_message && !le) advice.push('Ошибок нет. Если кнопки всё равно молчат — выпустите новую версию развертывания (карандаш → «Версия: новая»).');
  uiAlert_(lines.join('\n') + '\n\n' + advice.join('\n'));
}
function gameSettleNow_() {
  var r = gameAfterResults_();
  uiAlert_('Подсчитано прогнозов: ' + r.settled + (r.sent.length ? '. В канал: ' + r.sent.join(', ') : '') + '. Лист «' + GAME_VIEW + '» обновлён.');
}

/* ==========================================================================
 * «МАТЧИ ДНЯ · РЕЗУЛЬТАТЫ» — один пост на игровой день
 *
 *  • Когда начинается первый матч дня, в канал (без звука) выходит пост: все матчи дня столбиком,
 *    время начала и прогноз Джарвиса.
 *  • Через ~2 часа после начала каждого матча скрипт раз в 5 минут смотрит страницу матча на sports.ru;
 *    как только там «Завершен» — в пост дописывается счёт и ✅/❌ прогноза. Итог дня — внизу поста.
 *  • Живого счёта по ходу матча нет: у линии Pinnacle по КХЛ живых данных нет (проверено по журналу 23–26.09),
 *    поэтому пост ничего не обещает «по периодам».
 *  • Ничего не выдумываем: не нашли счёт за 4 часа — пишем «счёт уточняется».
 * ==========================================================================*/

var LIVE_LOG = 'Live_журнал';
var LIVE_LOG_HEADER = ['Время (МСК)', 'ID матча', 'Хозяева', 'Гости', 'isLive', 'status', 'state (как есть)', 'periods (как есть)',
  'Счёт хозяев', 'Счёт гостей', 'Стадия', 'Кэф П1 (с ОТ)', 'Кэф П2 (с ОТ)', 'Шанс хозяев', 'Шанс гостей'];
var LIVE_LOG_KEEP = 600;
var LIVE_WINDOW_MIN = 240;        // сколько минут после начала матча следим за ним
var LIVE_FINISH_MIN = 75;         // пропал из линии позже, чем через столько минут после начала — завершён

/** Матчи из журнала коэффициентов, которые идут сейчас (или начнутся в ближайшие 2 минуты) — и все матчи тех же дней. */
function liveCandidates_(ss, now) {
  var sh = ss.getSheetByName(SHEET_ODDS_LOG);
  if (!sh || sh.getLastRow() < 2) return [];
  var all = [], activeDays = {};
  sh.getRange(2, 1, sh.getLastRow() - 1, ODDS_HEADER.length).getValues().forEach(function (r) {
    var start = new Date(String(r[15]));
    var mins = (now.getTime() - start.getTime()) / 60000;
    var m = { id: String(r[14]), day: String(r[2]), time: String(r[1]).slice(11), start: start, home: r[3], away: r[4], mins: mins };
    all.push(m);
    if (mins > -2 && mins < LIVE_WINDOW_MIN) activeDays[m.day] = true;
  });
  var out = all.filter(function (m) { return activeDays[m.day] && m.mins < LIVE_WINDOW_MIN + 60; });
  out.sort(function (a, b) { return a.start - b.start || (a.home < b.home ? -1 : 1); });
  return out;
}

function livePct_(p) { return Math.round(p * 100) + '%'; }
function liveHas_(x) { return x !== null && x !== undefined && x !== ''; }

/** Текст поста «Матчи дня»: счёт появляется сразу после финальной сирены. */
function liveText_(day, items, now) {
  var lines = ['🏒 <b>МАТЧИ ДНЯ · РЕЗУЛЬТАТЫ</b>', ruDayTitle_(day).toLowerCase(), ''];
  var hit = 0, miss = 0;
  items.forEach(function (it) {
    var m = it.m, s = it.s;
    if (s.phase === 'done' && liveHas_(s.sh) && liveHas_(s.sa)) {
      lines.push('🏁 <b>' + escHtml_(m.home) + ' ' + s.sh + ':' + s.sa + ' ' + escHtml_(m.away) + '</b>' + (s.ot ? ' (ОТ/Б)' : ''));
      if (s.pick) {
        var ok = (s.sh > s.sa) === (s.pick === m.home); if (ok) hit++; else miss++;
        lines.push('<i>мой прогноз: ' + escHtml_(s.pick) + ' ' + (ok ? '✅' : '❌') + '</i>');
      }
    } else if (s.phase === 'done') {
      lines.push('🏁 ' + escHtml_(m.home) + ' — ' + escHtml_(m.away));
      lines.push('<i>завершён · счёт уточняется</i>');
    } else if (s.phase === 'live') {
      lines.push('▶️ ' + escHtml_(m.home) + ' — ' + escHtml_(m.away));
      lines.push('<i>идёт матч · начало в ' + m.time + ' МСК' + (s.pick ? ' · мой прогноз: ' + escHtml_(s.pick) : '') + '</i>');
    } else {
      lines.push('⏳ ' + escHtml_(m.home) + ' — ' + escHtml_(m.away));
      lines.push('<i>начало в ' + m.time + ' МСК' + (s.pick ? ' · мой прогноз: ' + escHtml_(s.pick) : '') + '</i>');
    }
    lines.push('');
  });
  if (hit + miss) lines.push('Прогнозы дня: <b>' + hit + ' из ' + (hit + miss) + '</b> ✅');
  lines.push('<i>Счёт появляется здесь сразу после финальной сирены (по данным sports.ru). Обновлено в ' + Utilities.formatDate(now, 'Europe/Moscow', 'HH:mm') + ' МСК.</i>');
  return lines.join('\n');
}

/** Ссылки на страницы матчей дня (календарь sports.ru), с кэшем на час: {'Хозяева|Гости': item} */
function liveCalendar_(day) {
  var cache = null, key = 'LIVE_CAL_' + day;
  try { cache = CacheService.getScriptCache(); var hit = cache.get(key); if (hit) return JSON.parse(hit); } catch (e) { cache = null; }
  var m = Number(day.slice(5, 7)), out = {}, map = {};
  try { map = buildNameMap_(); } catch (e) { map = {}; }
  try {
    var r = UrlFetchApp.fetch('https://www.sports.ru/hockey/tournament/khl/calendar/2026-2027/?m=' + m, { muteHttpExceptions: true, headers: SPORTS_UA });
    if (r.getResponseCode() === 200) mpCalendarItems_(r.getContentText()).forEach(function (it) {
      if (it.iso !== day) return;
      out[normalizeTeam_(it.home, map) + '|' + normalizeTeam_(it.away, map)] = { name: it.name, iso: it.iso, url: it.url };
    });
  } catch (e) { /* нет календаря — попробуем в следующий раз */ }
  try { if (cache && Object.keys(out).length) cache.put(key, JSON.stringify(out), 3600); } catch (e) {}
  return out;
}

/** Прогноз модели на матч (кто победит) с листа «прогнозы». */
function livePicks_(ss, day) {
  var pr = ss.getSheetByName('прогнозы'), out = {};
  if (!pr || pr.getLastRow() < 2) return out;
  pr.getRange(2, 1, pr.getLastRow() - 1, 4).getValues().forEach(function (r) {
    if (!(r[0] instanceof Date) || sheetDayKey_(r[0]) !== day) return;
    var d = Number(r[3]); if (!(d > 0 && d < 1)) return;
    out[String(r[1]).trim() + '|' + String(r[2]).trim()] = d >= 0.5 ? String(r[1]).trim() : String(r[2]).trim();
  });
  return out;
}

/** Один шаг (раз в 5 минут): отметить начавшиеся матчи, подтянуть финальный счёт с sports.ru, при изменениях — переписать пост. */
var LIVE_SCORE_FROM_MIN = 115;     // раньше чем через столько минут после начала финального счёта не бывает — страницу не трогаем

/** Для триггера раз в 5 минут. */
function liveUpdateAuto_() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {
    var lv = null, lw = null;
    try { lv = liveUpdate_(new Date()); } catch (e) { console.log('live: ' + e.message); autoMark_('liveUpdateAuto_', false, 'LIVE: ' + e.message); }
    try { lw = lineupWatch_(new Date()); } catch (e) { console.log('lineups: ' + e.message); autoMark_('liveUpdateAuto_', false, 'заявки: ' + e.message); }
    if (lv && lv.doneDays && lv.doneDays.length && PIPELINE_GAME) { try { gameEarlySettle_(lv.doneDays); } catch (e) { console.log('game early: ' + e.message); } }
    if ((lv && (lv.posted || lv.edited)) || (lw && lw.checked)) autoMark_('liveUpdateAuto_', true, (lv && lv.matches ? 'LIVE: матчей ' + lv.matches + '. ' : '') + (lw && lw.checked ? 'заявки: проверено ' + lw.checked + ', отправлено ' + lw.sent : ''));
    // раз в сутки: доставить недостающие запуски (после вставки нового кода нажимать ничего не нужно)
    var pp = PropertiesService.getScriptProperties(), today = mskNow_('yyyy-MM-dd');
    if (pp.getProperty('AUTO_ENSURED_DAY') !== today) {
      pp.setProperty('AUTO_ENSURED_DAY', today);
      try { ensureAutomation_(false); } catch (e) { console.log('auto: ' + e.message); }
    }
  } finally { lock.releaseLock(); }
}

/** Из меню. */
function liveUpdateNow_() {
  var r;
  try { r = liveUpdate_(new Date()); } catch (e) { uiAlert_('LIVE: ошибка — ' + e.message); return; }
  if (!r.matches) { uiAlert_('Сейчас нет идущих матчей. Пост «Матчи дня» выйдет сам, когда начнётся первый матч дня.'); return; }
  if (r.error) { uiAlert_('Идущих матчей: ' + r.matches + ', но ' + r.error + ' (меню «📣 НХЛ · ТГ группа» → «Игра: подключить бота и канал»).'); return; }
  uiAlert_('Идущих матчей: ' + r.matches + '. ' + (r.posted ? 'Пост опубликован.' : r.edited ? 'Пост обновлён.' : 'Новых результатов нет — пост не трогали.'));
}

/* ==========================================================================
 * МОИ ПОПРАВКИ К РЕЙТИНГУ
 *
 *  Лист «Мои поправки»: команда, поправка в очках рейтинга, срок действия, причина.
 *  Поправка прибавляется к рейтингу команды ТОЛЬКО в ещё не сыгранных матчах
 *  (история и прошлые прогнозы не меняются — иначе нельзя честно себя проверять).
 *
 *  Рядом с прогнозом хранится «шанс без моей поправки» (столбец BD), поэтому после
 *  матчей видно, помогла поправка или помешала: по неделям, по последним 5 оценкам
 *  и по каждой команде.
 * ==========================================================================*/

var SHEET_TWEAKS = 'Мои поправки';
var COL_TWEAK = 55;            // BC — моя поправка (Х-Г), очки рейтинга
var COL_PROB_BASE = 56;        // BD — шанс хозяев БЕЗ моей поправки
var TWEAK_LIMIT = 75;          // предел одной поправки, очков рейтинга
var TWEAK_DEFAULT_DAYS = 7;    // на сколько дней ставится поправка по умолчанию
var TWEAK_ROWS = 200;          // сколько строк отведено под поправки
var TWEAKS_HEADER = ['Команда', 'Поправка (очки рейтинга)', 'Действует до', 'Причина', 'Поставлено (МСК)'];
var TWEAK_REASONS = ['запасной вратарь', 'вернулся основной вратарь', 'травмы / нет лидеров', 'вернулись лидеры',
  'смена тренера', 'усталость / перелёты', 'мотивация / настрой', 'видео экспертов', 'другое'];

/** Включены ли поправки (можно выключить, если окажется, что они мешают). */
function tweaksOn_() {
  return PropertiesService.getScriptProperties().getProperty('TWEAKS_OFF') !== 'да';
}
function tweaksTurnOff_() { PropertiesService.getScriptProperties().setProperty('TWEAKS_OFF', 'да'); tweaksApply_(true); uiAlert_('Поправки выключены: прогнозы считаются без них. Включить — соседним пунктом меню.'); }
function tweaksTurnOn_() { PropertiesService.getScriptProperties().setProperty('TWEAKS_OFF', 'нет'); tweaksApply_(true); uiAlert_('Поправки включены: несыгранные матчи пересчитаны с ними.'); }

/** Создаёт лист «Мои поправки», если его нет. */
function ensureTweaksSheet_(ss) {
  var sh = ss.getSheetByName(SHEET_TWEAKS);
  if (sh) return sh;
  sh = ss.insertSheet(SHEET_TWEAKS);
  sh.getRange(1, 1, 1, TWEAKS_HEADER.length).setValues([TWEAKS_HEADER]).setFontWeight('bold');
  sh.getRange(1, 1, 1, TWEAKS_HEADER.length).setBackground('#1a4fd6').setFontColor('#ffffff');
  sh.setFrozenRows(1);
  sh.setColumnWidth(1, 180); sh.setColumnWidth(2, 190); sh.setColumnWidth(3, 130); sh.setColumnWidth(4, 320); sh.setColumnWidth(5, 150);
  sh.getRange(2, 3, TWEAK_ROWS, 1).setNumberFormat('dd.MM.yyyy');
  sh.getRange(2, 2, TWEAK_ROWS, 1).setNumberFormat('+0;-0;0');
  sh.getRange(1, 7).setValue('Как пользоваться').setFontWeight('bold');
  [
    'Пишите по строке на команду: название (как в таблице), поправку и до какой даты она действует.',
    'Поправка — в очках рейтинга. +25 ≈ +3,5% к шансам, +50 ≈ +7%, +100 ≈ +14%. Домашнее преимущество ≈ 60–70.',
    'Предел одной поправки ±' + TWEAK_LIMIT + ': больше — это уже не поправка, а замена модели мнением.',
    'Пустая дата = поправка действует ' + TWEAK_DEFAULT_DAYS + ' дней с момента, как её поставили.',
    'Поправка меняет только БУДУЩИЕ матчи. Прошлые прогнозы остаются как были.',
    'Ниже таблицы — счёт: помогают ваши поправки или мешают. Он обновляется после каждого игрового дня.',
    'Вратари: запасной в воротах — поставьте команде поправку на этот день (например −30) и причину «запасной вратарь». По причинам потом видно, насколько это важно.'
  ].forEach(function (t, i) { sh.getRange(2 + i, 7).setValue('• ' + t).setFontColor('#5a6472'); });
  try { sh.getRange(2, 1, TWEAK_ROWS, 1).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInRange(ss.getRange(SHEET_ELO + '!A2:A33'), true).setAllowInvalid(true).build()); } catch (e) { /* нет листа Elo или тесты */ }
  return sh;
}

/** Выпадающий список причин (можно вписать и свою) — по причинам потом видно, какие поправки работают. */
function tweaksReasonsValidation_(sh) {
  try {
    sh.getRange(2, 4, TWEAK_ROWS, 1).setDataValidation(
      SpreadsheetApp.newDataValidation().requireValueInList(TWEAK_REASONS, true).setAllowInvalid(true).build());
  } catch (e) { /* тесты */ }
}

/** Заполняет пустые сроки и время постановки, обрезает поправки по пределу. Возвращает список активных. */
function tweaksNormalize_(ss, now) {
  now = now || new Date();
  var sh = ensureTweaksSheet_(ss);
  var last = Math.max(sh.getLastRow(), 1);
  if (last < 2) return [];
  var rng = sh.getRange(2, 1, last - 1, TWEAKS_HEADER.length);
  var vals = rng.getValues(), changed = false, active = [];
  for (var i = 0; i < vals.length; i++) {
    var team = String(vals[i][0]).trim();
    var delta = Number(vals[i][1]);
    if (!team || !isFinite(delta) || delta === 0) continue;
    var capped = Math.max(-TWEAK_LIMIT, Math.min(TWEAK_LIMIT, Math.round(delta)));
    if (capped !== delta) { vals[i][1] = capped; changed = true; }
    if (!(vals[i][4] instanceof Date) && !String(vals[i][4]).trim()) { vals[i][4] = mskNow_(); changed = true; }
    if (!(vals[i][2] instanceof Date)) {
      var until = new Date(now.getTime() + TWEAK_DEFAULT_DAYS * 86400000);
      vals[i][2] = new Date(until.getFullYear(), until.getMonth(), until.getDate());
      changed = true;
    }
    active.push({ row: i + 2, team: team, delta: capped, until: vals[i][2] });
  }
  if (changed) rng.setValues(vals);
  return active;
}

/** Формула столбца BC: сумма активных поправок хозяев минус гостей (с пределом). */
function tweakFormulaTemplate_() {
  if (!tweaksOn_()) return '=IF(OR(B{R}="";C{R}="");"";0)';
  var col = function (c) { return "'" + SHEET_TWEAKS + "'!$" + c + "$2:$" + c + "$" + (TWEAK_ROWS + 1); };
  var side = function (teamCell) {
    return 'MAX(-' + TWEAK_LIMIT + ';MIN(' + TWEAK_LIMIT + ';SUMIFS(' + col('B') + ';' + col('A') + ';' + teamCell + ';' + col('C') + ';">="&$A{R})))';
  };
  return '=IF(OR(B{R}="";C{R}="");"";' + side('$B{R}') + '-' + side('$C{R}') + ')';
}

/** Ставит поправки и «шанс без поправки» в несыгранные строки листа «прогнозы». */
function tweaksApply_(silent) {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) { if (!silent) uiAlert_('Не найден лист «прогнозы».'); return { rows: 0 }; }
  tweaksReasonsValidation_(ensureTweaksSheet_(ss));
  tweaksNormalize_(ss, new Date());
  sh.getRange(1, COL_TWEAK).setValue('Моя поправка (Х-Г)');
  sh.getRange(1, COL_PROB_BASE).setValue('Шансы Хозяев без моей поправки');
  var rows = openPredictionRows_(sh);
  setFormulaOnOpenRows_(sh, COL_TWEAK, tweakFormulaTemplate_(), rows);
  setFormulaOnOpenRows_(sh, COL_PROB_BASE, probabilityFormulaTemplate_(true), rows);
  applyProbabilityFormula_(sh);
  if (!silent) uiAlert_('Готово: поправки учтены в ' + rows.length + ' несыгранных матчах. Рядом сохраняется шанс без поправки — по нему потом считается, помогли они или нет.');
  return { rows: rows.length };
}

/* ------------------------- помогают ли поправки ------------------------- */
/** Сыгранные матчи, где поправка была не нулевой: сравниваем шанс с поправкой и без. */
function tweaksCollect_(ss) {
  var sh = ss.getSheetByName('прогнозы');
  var out = [];
  if (!sh) return out;
  var last = lastMatchRow_(sh);
  if (last < 2) return out;
  var vals = sh.getRange(2, 1, last - 1, COL_PROB_BASE).getValues();
  // фактические победители (победа с учётом ОТ — как считает столбец D)
  var res = {};
  var rs = ss.getSheetByName(SHEET_RESULTS);
  if (rs && rs.getLastRow() >= 2) {
    rs.getRange(2, 1, rs.getLastRow() - 1, 6).getValues().forEach(function (r) {
      if (!(r[0] instanceof Date) || String(r[1]).trim() !== 'Сыгран') return;
      if (typeof r[4] !== 'number' || typeof r[5] !== 'number') return;
      res[sheetDayKey_(r[0]) + '|' + String(r[2]).trim() + '|' + String(r[3]).trim()] = r[4] > r[5] ? 1 : 0;
    });
  }
  // какие поправки (и с какой причиной) действовали на матч
  var tw = ss.getSheetByName(SHEET_TWEAKS), twRows = [];
  if (tw && tw.getLastRow() >= 2) twRows = tw.getRange(2, 1, tw.getLastRow() - 1, TWEAKS_HEADER.length).getValues()
    .filter(function (r) { return String(r[0]).trim() && Number(r[1]) && r[2] instanceof Date; });
  var reasonsFor = function (date, home, away) {
    var out = [];
    twRows.forEach(function (r) {
      var t = String(r[0]).trim();
      if ((t === home || t === away) && r[2].getTime() + 86400000 > date.getTime()) {
        var why = String(r[3]).trim() || 'без причины';
        if (out.indexOf(why) === -1) out.push(why);
      }
    });
    return out.length ? out : ['без причины'];
  };
  vals.forEach(function (v) {
    var date = v[0], home = String(v[1]).trim(), away = String(v[2]).trim();
    if (!(date instanceof Date) || !home || !away) return;
    if (String(v[COL_INTEGRITY - 1]).trim() !== 'да') return;          // нечестный прогноз в счёт не идёт
    var tweak = Number(v[COL_TWEAK - 1]), pWith = Number(v[3]), pBase = Number(v[COL_PROB_BASE - 1]);
    if (!isFinite(tweak) || tweak === 0 || !(pWith > 0) || !(pBase > 0)) return;
    var y = res[sheetDayKey_(date) + '|' + home + '|' + away];
    if (y === undefined) return;
    out.push({ date: date, home: home, away: away, tweak: tweak, pWith: pWith, pBase: pBase, y: y, reasons: reasonsFor(date, home, away),
               toward: (pWith - pBase) * (y - pBase) > 0,            // сдвинули в сторону правды?
               bWith: Math.pow(pWith - y, 2), bBase: Math.pow(pBase - y, 2) });
  });
  out.sort(function (a, b) { return a.date - b.date; });
  return out;
}

/** Дата как есть в таблице, без пересчёта часовых поясов (иначе день «съезжает»). */
function tweakDM_(d) {
  var p = function (n) { return (n < 10 ? '0' : '') + n; };
  return p(d.getDate()) + '.' + p(d.getMonth() + 1);
}
function tweakWeekKey_(d) {
  var x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7));                     // понедельник
  return tweakDM_(x);
}
function tweakAvg_(arr, f) { return arr.length ? arr.reduce(function (s, x) { return s + f(x); }, 0) / arr.length : null; }
function tweakR3_(x) { return x === null ? '—' : Math.round(x * 1000) / 1000; }

/** Рисует табло «помогают ли поправки» на листе «Мои поправки» (столбцы I..N). */
function tweaksRender_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var sh = ensureTweaksSheet_(ss);
  var rows = tweaksCollect_(ss);
  var area = sh.getRange(1, 9, Math.max(sh.getMaxRows(), 60), 6);
  area.clearContent(); area.setFontWeight('normal').setFontColor('#000000').setFontSize(10);
  var out = [], fmt = [];
  var put = function (arr, bold) { out.push(arr.concat(['', '', '', '', '', ''].slice(arr.length))); fmt.push(bold ? 'bold' : 'normal'); };

  put(['ПОМОГАЮТ ЛИ МОИ ПОПРАВКИ'], true);
  if (!rows.length) {
    put(['Пока нечего оценивать: ни один матч с поправкой ещё не сыгран.']);
    put(['Поставьте поправку слева — после игрового дня здесь появится счёт.']);
  } else {
    var toward = rows.filter(function (r) { return r.toward; }).length;
    var bW = tweakAvg_(rows, function (r) { return r.bWith; }), bB = tweakAvg_(rows, function (r) { return r.bBase; });
    put(['Оценено матчей с поправкой', rows.length, 'направление угадано', toward + ' из ' + rows.length +
      ' (' + Math.round(toward / rows.length * 100) + '%)']);
    put(['Средняя ошибка (Brier)', 'с поправками ' + tweakR3_(bW), 'без поправок ' + tweakR3_(bB), 'меньше — точнее']);
    var diff = bB - bW;
    put([rows.length < 20
      ? 'Матчей пока мало — выводы делать рано, нужно хотя бы 20–30.'
      : (diff > 0.01 ? 'Поправки помогают: ошибка ниже, чем без них.'
        : (diff < -0.01 ? 'Поправки мешают: без них ошибка ниже. Стоит ставить их реже или меньше по размеру.'
          : 'Разницы почти нет: поправки ничего не меняют.'))], true);

    put(['']);
    put(['По неделям'], true);
    put(['Неделя с', 'Матчей', 'Направление', 'Brier с', 'Brier без'], true);
    var weeks = {}, order = [];
    rows.forEach(function (r) { var k = tweakWeekKey_(r.date); if (!weeks[k]) { weeks[k] = []; order.push(k); } weeks[k].push(r); });
    order.forEach(function (k) {
      var w = weeks[k], t = w.filter(function (r) { return r.toward; }).length;
      put([k, w.length, t + ' из ' + w.length, tweakR3_(tweakAvg_(w, function (r) { return r.bWith; })), tweakR3_(tweakAvg_(w, function (r) { return r.bBase; }))]);
    });

    put(['']);
    put(['Последние 5 оценок'], true);
    put(['Дата', 'Матч', 'Поправка', 'Шанс Х: с / без', 'Итог'], true);
    rows.slice(-5).reverse().forEach(function (r) {
      put([tweakDM_(r.date), r.home + ' — ' + r.away,
        (r.tweak > 0 ? '+' : '') + r.tweak,
        Math.round(r.pWith * 100) + '% / ' + Math.round(r.pBase * 100) + '%',
        (r.y ? 'победа хозяев' : 'победа гостей') + (r.toward ? '  ✅ в плюс' : '  ❌ в минус')]);
    });

    put(['']);
    put(['По причинам (например, «запасной вратарь»)'], true);
    put(['Причина', 'Матчей', 'Направление', 'Brier с', 'Brier без'], true);
    var byWhy = {}, wOrder = [];
    rows.forEach(function (r) { (r.reasons || ['без причины']).forEach(function (w) { if (!byWhy[w]) { byWhy[w] = []; wOrder.push(w); } byWhy[w].push(r); }); });
    wOrder.sort(function (a, b) { return byWhy[b].length - byWhy[a].length; }).forEach(function (w) {
      var g = byWhy[w], k = g.filter(function (r) { return r.toward; }).length;
      put([w, g.length, k + ' из ' + g.length, tweakR3_(tweakAvg_(g, function (r) { return r.bWith; })), tweakR3_(tweakAvg_(g, function (r) { return r.bBase; }))]);
    });

    put(['']);
    put(['По командам'], true);
    put(['Команда', 'Матчей', 'Направление', 'Brier с', 'Brier без'], true);
    var byTeam = {}, tOrder = [];
    rows.forEach(function (r) {
      [r.home, r.away].forEach(function (t) {
        if (!byTeam[t]) { byTeam[t] = []; tOrder.push(t); }
        byTeam[t].push(r);
      });
    });
    tOrder.sort(function (a, b) { return byTeam[b].length - byTeam[a].length; }).slice(0, 12).forEach(function (t) {
      var w = byTeam[t], k = w.filter(function (r) { return r.toward; }).length;
      put([t, w.length, k + ' из ' + w.length, tweakR3_(tweakAvg_(w, function (r) { return r.bWith; })), tweakR3_(tweakAvg_(w, function (r) { return r.bBase; }))]);
    });
  }
  put(['']);
  put(['Обновлено ' + mskNow_() + ' МСК' + (tweaksOn_() ? '' : '  ·  ПОПРАВКИ СЕЙЧАС ВЫКЛЮЧЕНЫ')]);

  sh.getRange(1, 9, out.length, 6).setValues(out);
  out.forEach(function (r, i) { if (fmt[i] === 'bold') sh.getRange(i + 1, 9, 1, 6).setFontWeight('bold'); });
  sh.getRange(1, 9, 1, 6).setFontSize(12).setFontColor('#1a4fd6');
  [9, 10, 11, 12, 13, 14].forEach(function (c, i) { sh.setColumnWidth(c, i === 1 ? 220 : 150); });
  return { evaluated: rows.length };
}

/** Пункт меню: поправки в силу + пересчёт табло. */
function tweaksUpdateNow_() {
  var r = tweaksApply_(true);
  var s = tweaksRender_();
  tweaksRankingRender_();
  uiAlert_('Мои поправки: учтены в ' + r.rows + ' несыгранных матчах. Оценено сыгранных матчей с поправкой: ' + s.evaluated + '.' +
    (tweaksOn_() ? '' : '\n\nСейчас поправки ВЫКЛЮЧЕНЫ — прогнозы считаются без них.'));
}

/* ----------------------- общий рейтинг команд по местам ----------------------- */
var RANK_COL = 16;              // P — начало блока рейтинга на листе «Мои поправки»
var RANK_DAYS = 7;              // с какой давностью сравниваем (движение за неделю)

/** Снимок рейтингов из «Elo_история» примерно RANK_DAYS назад. {команда: рейтинг} или null. */
function rankPrevSnapshot_(ss, now) {
  var sh = ss.getSheetByName('Elo_история');
  if (!sh || sh.getLastRow() < 2) return null;
  var vals = sh.getRange(1, 1, sh.getLastRow(), sh.getLastColumn()).getValues();
  var head = vals[0];
  var target = now.getTime() - RANK_DAYS * 86400000;
  var best = null, bestDiff = null;
  for (var i = 1; i < vals.length; i++) {
    var d = vals[i][0];
    if (!(d instanceof Date)) continue;
    var diff = Math.abs(d.getTime() - target);
    if (bestDiff === null || diff < bestDiff) { bestDiff = diff; best = vals[i]; }
  }
  if (!best) return null;
  var out = {};
  for (var c = 1; c < head.length; c++) {
    var name = String(head[c]).trim();
    if (name && typeof best[c] === 'number') out[name] = best[c];
  }
  return { date: best[0], elo: out };
}

/** Таблица команд по рейтингу со стрелками движения. */
function tweaksRankingRows_(ss, now) {
  now = now || new Date();
  var eloSh = ss.getSheetByName(SHEET_ELO);
  if (!eloSh || eloSh.getLastRow() < 2) return null;
  var elo = eloSh.getRange(2, 1, eloSh.getLastRow() - 1, 2).getValues()
    .filter(function (r) { return String(r[0]).trim() && typeof r[1] === 'number'; })
    .map(function (r) { return { team: String(r[0]).trim(), elo: r[1] }; });
  if (!elo.length) return null;

  var tweaks = {};
  tweaksNormalize_(ss, now).forEach(function (t) {
    var until = t.until instanceof Date ? t.until : null;
    if (until && until.getTime() + 86400000 < now.getTime()) return;    // срок вышел
    tweaks[t.team] = (tweaks[t.team] || 0) + t.delta;
  });

  var prev = rankPrevSnapshot_(ss, now);
  var prevRank = {};
  if (prev) {
    Object.keys(prev.elo).map(function (t) { return { team: t, elo: prev.elo[t] }; })
      .sort(function (a, b) { return b.elo - a.elo; })
      .forEach(function (x, i) { prevRank[x.team] = i + 1; });
  }
  elo.forEach(function (x) { x.tweak = tweaks[x.team] || 0; x.total = x.elo + x.tweak; });
  elo.sort(function (a, b) { return b.total - a.total; });
  return elo.map(function (x, i) {
    var p = prev ? prev.elo[x.team] : undefined;
    var dElo = (typeof p === 'number') ? Math.round((x.elo - p) * 10) / 10 : null;
    var dPlace = prevRank[x.team] ? prevRank[x.team] - (i + 1) : null;
    return { place: i + 1, team: x.team, elo: Math.round(x.elo * 10) / 10, dElo: dElo, dPlace: dPlace,
             tweak: x.tweak, total: Math.round(x.total * 10) / 10, prevDate: prev ? prev.date : null };
  });
}

/** Рисует таблицу рейтинга (столбцы P..U) на листе «Мои поправки». */
function tweaksRankingRender_(ss, now) {
  ss = ss || SpreadsheetApp.getActive();
  now = now || new Date();
  var sh = ensureTweaksSheet_(ss);
  var area = sh.getRange(1, RANK_COL, Math.max(sh.getMaxRows(), 40), 7);
  area.clearContent(); area.setFontWeight('normal').setFontColor('#000000');
  var rows = tweaksRankingRows_(ss, now);
  if (!rows) {
    sh.getRange(1, RANK_COL).setValue('Рейтинг команд появится после пересчёта Elo.');
    return { teams: 0 };
  }
  var out = [['РЕЙТИНГ КОМАНД  ·  все ' + rows.length, '', '', '', '', '', ''],
             ['стрелки — движение за неделю по сравнению с ' + (rows[0].prevDate ? tweakDM_(rows[0].prevDate) : '—') +
              '; место считается по рейтингу с вашей поправкой', '', '', '', '', '', ''],
             ['Место', 'Команда', 'Рейтинг', 'За неделю', 'Моя поправка', 'Итог с поправкой', 'Места']];
  var colors = [['#1a4fd6', '', '', '', '', '', ''], ['#5a6472', '', '', '', '', '', ''], ['', '', '', '', '', '', '']];
  rows.forEach(function (r) {
    var arrow = function (v) { return v === null ? '—' : (v > 0 ? '▲ ' : (v < 0 ? '▼ ' : '— ')) + (v ? Math.abs(v) : ''); };
    out.push([r.place, r.team, r.elo, arrow(r.dElo), r.tweak ? (r.tweak > 0 ? '+' : '') + r.tweak : '', r.total, arrow(r.dPlace)]);
    var col = function (v) { return v === null || v === 0 ? '#5a6472' : (v > 0 ? '#137333' : '#c5221f'); };
    colors.push(['#000000', '#000000', '#000000', col(r.dElo), r.tweak ? col(r.tweak) : '#000000', '#000000', col(r.dPlace)]);
  });
  sh.getRange(1, RANK_COL, out.length, 7).setValues(out);
  sh.getRange(1, RANK_COL, out.length, 7).setFontColors(colors);
  sh.getRange(1, RANK_COL, 1, 7).setFontWeight('bold').setFontSize(12);
  sh.getRange(3, RANK_COL, 1, 7).setFontWeight('bold');
  [70, 190, 90, 110, 130, 140, 90].forEach(function (w, i) { sh.setColumnWidth(RANK_COL + i, w); });
  return { teams: rows.length };
}

/* ==========================================================================
 * АРХИВ ЛИНИЙ ПРОШЛОГО СЕЗОНА (betexplorer.com)
 *
 *  Нужен, чтобы честно проверить: точнее ли смесь «таблица + букмекер», чем
 *  таблица сама по себе, — на сотнях матчей прошлого сезона, а не ждать 50 новых.
 *  Коэффициенты — средние по букмекерам на исход основного времени (1 / X / 2).
 *  Лист «Архив_линий» скрытый; если разобрать страницу не удалось — в нём
 *  остаётся кусок страницы, чтобы можно было поправить разбор.
 * ==========================================================================*/

var HIST_ODDS_SHEET = 'Архив_линий';
var HIST_ODDS_BASE = 'https://www.betexplorer.com/hockey/russia/';
var HIST_ODDS_URLS = {            // регулярный чемпионат по месяцам (страница без месяца показывает только часть)
  '2025-26': ['2025-09', '2025-10', '2025-11', '2025-12', '2026-01', '2026-02', '2026-03'].map(function (m) {
    return HIST_ODDS_BASE + 'khl-2025-2026/results/?stage=rNiLspwC&month=' + m; }),
  '2026-27': [HIST_ODDS_BASE + 'khl/results/']      // текущий сезон — сыгранные матчи до начала нашего журнала линий
};
var HIST_HEADER = ['Сезон', 'Дата', 'Хозяева', 'Гости', 'Г Хозяев', 'Г Гостей', 'ОТ/буллиты?', 'Кэф П1 осн.', 'Кэф Х осн.', 'Кэф П2 осн.', 'Хозяева (как на сайте)', 'Гости (как на сайте)'];

function histStrip_(h) { return String(h || '').replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim(); }

/** Разбор страницы результатов betexplorer: строки таблицы → матчи с коэффициентами. */
function histParseBetexplorer_(html, season) {
  var out = [], unknown = {};
  var y1 = Number(season.slice(0, 4)), y2 = y1 + 1;
  var rows = String(html).split(/<tr[\s>]/i).slice(1);
  rows.forEach(function (tr) {
    tr = tr.split(/<\/tr>/i)[0];
    var teams = tr.match(/<a[^>]*in-match[^>]*>([\s\S]*?)<\/a>/i) || tr.match(/<td[^>]*h-text-left[^>]*>([\s\S]*?)<\/td>/i);
    if (!teams) return;
    var spans = teams[1].match(/<span[^>]*>([\s\S]*?)<\/span>/gi);
    var names = spans && spans.length >= 2 ? spans.slice(0, 2).map(histStrip_) : histStrip_(teams[1]).split(/\s+-\s+/);
    if (!names || names.length < 2) return;
    var text = histStrip_(tr);
    var sc = text.match(/(\d{1,2})\s*:\s*(\d{1,2})\s*(AET|OT|pen\.?|SO|ET)?/i);
    if (!sc) return;
    // по ячейкам: из каждой <td> берём первое data-odd (оно бывает и у ячейки, и во вложенных span)
    var odds = [];
    tr.split(/<td/i).slice(1).forEach(function (td) {
      var mm = td.match(/data-odd="([\d.]+)"/i);
      if (mm) odds.push(Number(mm[1]));
    });
    if (odds.length < 3) {                                   // запасной вариант: числа в тексте ячеек
      var cells = tr.match(/<td[^>]*odds[^>]*>([\s\S]*?)<\/td>/gi) || [];
      odds = cells.map(function (c) { return Number(histStrip_(c)); }).filter(function (x) { return x > 1; });
    }
    var dm = text.match(/(\d{2})\.(\d{2})\.(\d{4})?/g);
    if (!dm) return;
    var last = dm[dm.length - 1].split('.');
    var mon = Number(last[1]), year = last[2] ? Number(last[2]) : (mon >= 7 ? y1 : y2);
    var home = pinnacleTeamRu_(names[0]), away = pinnacleTeamRu_(names[1]);
    if (!home) unknown[names[0]] = true;
    if (!away) unknown[names[1]] = true;
    if (!home || !away) return;
    out.push([season, Utilities.formatDate(new Date(year, mon - 1, Number(last[0]), 12), 'Europe/Moscow', 'yyyy-MM-dd'),
      home, away, Number(sc[1]), Number(sc[2]), sc[3] ? 'да' : 'нет',
      odds[0] || '', odds[1] || '', odds[2] || '', names[0], names[1]]);
  });
  return { rows: out, unknown: Object.keys(unknown) };
}



/* ==========================================================================
 * ЛУЧШИЙ ПРОГНОЗ = 75% линия букмекера + 25% таблица
 *
 *  Проверка на 614 матчах (прошлый сезон с архивом линий + текущий): букмекер точнее
 *  таблицы, а смесь с большой долей букмекера лучше таблицы с запасом больше погрешности.
 *  Джарвис (столбец D) остаётся НЕЗАВИСИМЫМ — на нём игра и табло «против букмекера».
 *  «Лучший прогноз» — отдельные столбцы BE/BF рядом, для ставок и платного контента.
 *  Сыгранные матчи не перезаписываются (последнее значение до матча остаётся).
 * ==========================================================================*/

var COL_BEST_P = 57;           // BE — лучший прогноз: шанс хозяев
var COL_BEST_PICK = 58;        // BF — лучший прогноз: кто победит (и откуда цифра)
var BEST_MARKET_W = 0.75;      // доля букмекера в лучшем прогнозе

function writeBestForecast_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var sh = ss.getSheetByName('прогнозы');
  if (!sh) return { rows: 0 };
  var last = lastMatchRow_(sh);
  sh.getRange(1, COL_BEST_P).setValue('Лучший прогноз: шансы хозяев (' + Math.round(BEST_MARKET_W * 100) + '% букмекер + ' + Math.round((1 - BEST_MARKET_W) * 100) + '% таблица)');
  sh.getRange(1, COL_BEST_PICK).setValue('Лучший прогноз: кто победит');
  if (last < 2) return { rows: 0 };
  var odds = readOddsLog_(ss);
  var vals = sh.getRange(2, 1, last - 1, 11).getValues();               // A..K
  var cur = sh.getRange(2, COL_BEST_P, last - 1, 2).getValues();
  var out = [], withLine = 0, n = 0;
  for (var i = 0; i < vals.length; i++) {
    var v = vals[i], mark = String(v[10]).trim();
    if (mark === '✅' || mark === '❌' || !(v[0] instanceof Date) || !v[1] || !v[2] || typeof v[3] !== 'number') { out.push(cur[i]); continue; }
    var key = sheetDayKey_(v[0]), home = String(v[1]).trim(), away = String(v[2]).trim();
    var o = null, ks = [key, addDaysKey_(key, -1), addDaysKey_(key, 1)];
    for (var k = 0; k < ks.length && !o; k++) o = odds[ks[k] + '|' + home + '|' + away] || null;
    var pm = v[3], p, src;
    if (o && o.pHome !== null) { p = BEST_MARKET_W * o.pHome + (1 - BEST_MARKET_W) * pm; src = ''; withLine++; }
    else { p = pm; src = ' (линии пока нет — только таблица)'; }
    p = Math.round(p * 10000) / 10000;
    out.push([p, (p >= 0.5 ? home : away) + ' · ' + Math.round(Math.max(p, 1 - p) * 100) + '%' + src]);
    n++;
  }
  sh.getRange(2, COL_BEST_P, out.length, 2).setValues(out);
  sh.getRange(2, COL_BEST_P, out.length, 1).setNumberFormat('0.0%');
  return { rows: n, withLine: withLine };
}

/* ==========================================================================
 * ЛИСТ «ПРОГНОЗЫ — КРАТКО» — чистая витрина для подписчиков
 *  Ближайшие 3 дня и последние 7: матч, Джарвис, лучший прогноз, коэффициенты, итог.
 *  Обновляется вместе с коэффициентами (каждые 2 часа) и утренним обновлением.
 * ==========================================================================*/

var SHEET_BRIEF = 'Прогнозы — кратко';

/** '2026-09-23' → 'Ср, 23.09' */
function briefDay_(key) {
  var p = String(key).split('-'), d = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]), 12);
  return ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'][d.getDay()] + ', ' + p[2] + '.' + p[1];
}

function renderBriefSheet_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var prog = ss.getSheetByName('прогнозы');
  if (!prog) return { rows: 0 };
  var last = lastMatchRow_(prog);
  var vals = last >= 2 ? prog.getRange(2, 1, last - 1, COL_BEST_PICK).getValues() : [];
  var odds = readOddsLog_(ss);
  var res = {};
  var rs = ss.getSheetByName(SHEET_RESULTS);
  if (rs && rs.getLastRow() >= 2) {
    rs.getRange(2, 1, rs.getLastRow() - 1, 7).getValues().forEach(function (r) {
      if (!(r[0] instanceof Date) || String(r[1]).trim() !== 'Сыгран' || typeof r[4] !== 'number') return;
      res[sheetDayKey_(r[0]) + '|' + String(r[2]).trim() + '|' + String(r[3]).trim()] =
        { hg: r[4], ag: r[5], ot: r[6] === true || String(r[6]).toUpperCase() === 'TRUE' };
    });
  }
  var today = todayKey_(), from = addDaysKey_(today, -7), to = addDaysKey_(today, 3);
  var pct = function (p) { return Math.round(p * 100) + '%'; };
  var items = [];
  vals.forEach(function (v) {
    if (!(v[0] instanceof Date) || !v[1] || !v[2] || typeof v[3] !== 'number') return;
    var key = sheetDayKey_(v[0]);
    if (key < from || key > to) return;
    var home = String(v[1]).trim(), away = String(v[2]).trim();
    var o = null, ks = [key, addDaysKey_(key, -1), addDaysKey_(key, 1)];
    for (var k = 0; k < ks.length && !o; k++) o = odds[ks[k] + '|' + home + '|' + away] || null;
    var r = res[key + '|' + home + '|' + away] || null;
    var pJ = v[3], pB = typeof v[COL_BEST_P - 1] === 'number' ? v[COL_BEST_P - 1] : null;
    var winner = r ? (r.hg > r.ag ? 0 : 1) : null;
    var hit = function (p) { return p === null || winner === null ? '' : (((p >= 0.5 ? 0 : 1) === winner) ? '✅' : '❌'); };
    items.push({ key: key, time: o && o.time ? o.time : '', row: [
      briefDay_(key),
      o && o.time ? o.time : '',
      home + ' — ' + away,
      (pJ >= 0.5 ? home : away) + ' · ' + pct(Math.max(pJ, 1 - pJ)),
      pB === null ? '—' : (pB >= 0.5 ? home : away) + ' · ' + pct(Math.max(pB, 1 - pB)),
      o && o.regOdds ? o.regOdds.map(function (x) { return x.toFixed(2); }).join(' / ') : '—',
      r ? r.hg + ':' + r.ag + (r.ot ? ' ОТ/Б' : '') : '',
      hit(pJ), hit(pB)] });
  });
  items.sort(function (a, b) { return a.key !== b.key ? (a.key < b.key ? -1 : 1) : (a.time < b.time ? -1 : 1); });

  var sh = resetSheet_(ss, SHEET_BRIEF);
  var head = ['День', 'Начало (МСК)', 'Матч', '🤖 Джарвис', '⭐ Лучший прогноз', 'Кэфы П1 / Х / П2 (осн. время)', 'Счёт', 'Джарвис', 'Лучший'];
  sh.getRange(1, 1).setValue('ПРОГНОЗЫ НХЛ · JARVIS').setFontWeight('bold').setFontSize(14).setFontColor('#1a4fd6');
  sh.getRange(2, 1).setValue('Джарвис — собственная модель. Лучший прогноз — 75% линии букмекера + 25% Джарвиса (точнее на архиве прошлого сезона). ' +
    'Шансы — на победу с учётом ОТ и буллитов. Обновлено ' + mskNow_() + ' МСК.').setFontColor('#5a6472').setFontSize(9);
  sh.getRange(4, 1, 1, head.length).setValues([head]).setFontWeight('bold').setBackground('#eef2f7');
  if (items.length) {
    var rows = items.map(function (x) { return x.row; });
    sh.getRange(5, 1, rows.length, head.length).setValues(rows);
    var colors = rows.map(function (r) {
      return r.map(function (c, j) { return j >= 7 ? (c === '✅' ? '#137333' : (c === '❌' ? '#c5221f' : '#000000')) : (j === 4 ? '#6b3fa0' : (j === 3 ? '#1a4fd6' : '#000000')); });
    });
    sh.getRange(5, 1, rows.length, head.length).setFontColors(colors);
    // граница между прошедшими и будущими
    for (var i = 0; i < items.length; i++) if (items[i].key >= today) { sh.getRange(5 + i, 1, 1, head.length).setBorder(true, null, null, null, null, null, '#1a4fd6', SpreadsheetApp.BorderStyle.SOLID); break; }
  } else {
    sh.getRange(5, 1).setValue('Матчей в ближайшие дни нет.');
  }
  [90, 95, 260, 190, 200, 190, 80, 75, 75].forEach(function (w, i) { sh.setColumnWidth(i + 1, w); });
  sh.setFrozenRows(4);
  return { rows: items.length };
}

/* ==========================================================================
 * ДИАГНОСТИКА ИСТОЧНИКА РЕЗУЛЬТАТОВ
 *  sports.ru поменял календарь: по умолчанию показывает только будущие матчи,
 *  поэтому результаты с 23.09 перестали записываться. Эта функция проверяет
 *  несколько вариантов страниц и сохраняет образцы в скрытый лист, чтобы
 *  настроить разбор под новую разметку.
 * ==========================================================================*/

var DIAG_SHEET = 'Диагностика_результатов';

function diagResultsSources_() {
  var probe = addDaysKey_(todayKey_(), -2);                       // позавчера — точно сыгранные матчи
  var p = probe.split('-'), needle = p[2] + '.' + p[1] + '.' + p[0];
  var base = 'https://www.sports.ru/hockey/tournament/khl/calendar/';
  var urls = [base, base + '2026-2027/', base + '2026-2027/?m=' + Number(p[1]), base + '?m=' + Number(p[1]),
    base + '?type=past', base + '?filter=past', base + '?view=past', base + '?s=past',
    'https://www.sports.ru/hockey/club/torpedo-nn/calendar/', 'https://www.sports.ru/hockey/club/lokomotiv/calendar/',
    'https://www.khl.ru/calendar/', 'https://www.sport-express.ru/hockey/khl/calendar/',
    'https://m.sports.ru/hockey/tournament/khl/calendar/2026-2027/?m=' + Number(p[1]) + '&is_bot=1',
    'https://m.sports.ru/hockey/tournament/khl/calendar/2026-2027/?m=' + Number(p[1]),
    'https://www.sports.ru/hockey/tournament/khl/calendar/2026-2027/?m=' + Number(p[1]) + '&is_bot=1'];
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(DIAG_SHEET) || ss.insertSheet(DIAG_SHEET);
  sh.clearContents();
  var out = [['Адрес', 'Код', 'Длина', 'Есть ' + needle + '?', 'Разобрано матчей старым разбором', 'Текст вокруг даты', 'HTML вокруг даты', 'Ссылки на календарь']];
  urls.forEach(function (u) {
    var code = 0, html = '';
    try {
      var r = UrlFetchApp.fetch(u, { muteHttpExceptions: true, followRedirects: true,
        headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36' } });
      code = r.getResponseCode(); html = r.getContentText();
    } catch (e) { html = 'ошибка: ' + e.message; }
    var text = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    var ti = text.indexOf(needle), hi = html.indexOf(needle);
    var parsed = 0;
    try { parsed = parseMatches_(html).length; } catch (e) { parsed = -1; }
    var links = (html.match(/href="[^"]*calendar[^"]*"/gi) || []).filter(function (x, i, a) { return a.indexOf(x) === i; }).slice(0, 60).join(' ');
    out.push([u, code, html.length, ti >= 0 ? 'да' : 'нет', parsed,
      ti >= 0 ? text.slice(Math.max(0, ti - 200), ti + 1500) : '',
      hi >= 0 ? html.slice(Math.max(0, hi - 1500), hi + 3500) : '', links.slice(0, 45000)]);
    Utilities.sleep(500);
  });
  sh.getRange(1, 1, out.length, out[0].length).setValues(out);
  // целиком одна страница (сентябрь), по кускам — чтобы разобрать новую разметку полностью
  try {
    var full = UrlFetchApp.fetch(base + '2026-2027/?m=' + Number(p[1]), { muteHttpExceptions: true,
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36' } }).getContentText();
    var parts = [];
    for (var k = 0; k < full.length; k += 45000) parts.push([full.slice(k, k + 45000)]);
    sh.getRange(1, 10).setValue('Страница целиком (' + full.length + ' знаков), по кускам ниже');
    sh.getRange(2, 10, parts.length, 1).setValues(parts);
  } catch (e) { sh.getRange(1, 10).setValue('не удалось сохранить страницу: ' + e.message); }
  // страницы сыгранных матчей: обычный (Торпедо 2:3 ЦСКА, 18.09) и в ОТ (Динамо Мн 3:4 Торпедо, 07.09)
  [['https://www.sports.ru/hockey/match/1947795/', 11], ['https://www.sports.ru/hockey/match/1947843/', 12],
   ['https://m.sports.ru/hockey/match/1947843/', 13]].forEach(function (x) {
    try {
      var t = UrlFetchApp.fetch(x[0], { muteHttpExceptions: true,
        headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36' } }).getContentText();
      var ch = [];
      for (var k = 0; k < Math.min(t.length, 45000 * 25); k += 45000) ch.push([t.slice(k, k + 45000)]);
      sh.getRange(1, x[1]).setValue(x[0] + ' (' + t.length + ' знаков)');
      sh.getRange(2, x[1], ch.length, 1).setValues(ch);
    } catch (e) { sh.getRange(1, x[1]).setValue(x[0] + ' — ошибка: ' + e.message); }
  });
  try { sh.hideSheet(); } catch (e) { /* тесты */ }
  uiAlert_('Проверил ' + urls.length + ' страниц, образцы сохранены в скрытый лист «' + DIAG_SHEET + '». ' +
    'Напишите в чат «диагностика готова».');
}

/* ==========================================================================
 * РЕЗУЛЬТАТЫ СО СТРАНИЦ МАТЧЕЙ (sports.ru с 23.09.2026)
 *  Календарь sports.ru теперь рисуется скриптом: счёта в нём нет, но есть список
 *  матчей (дата, команды, ссылка). Счёт и отметка ОТ/Б берутся со страницы матча,
 *  где табло ещё приходит обычным HTML. Страница проверяется: те же команды, та же
 *  дата и статус «Завершен» — иначе матч пропускается (ничего не угадываем).
 * ==========================================================================*/

var MP_LOOKBACK_DAYS = 12;          // за сколько дней назад добираем несыгранные в таблице матчи

/** Список матчей из календаря: [{iso:'2026-09-23', date:'23.09.2026', home, away, url}] */
function mpCalendarItems_(html) {
  var out = [], seen = {};
  var re = /"item":\{"@type":"SportsEvent","name":"([^"]+)","description":"[^"]*","startDate":"(\d{4})-(\d{2})-(\d{2})T([^"]*)","endDate":"[^"]*","url":"([^"]+)"/g, m;
  while ((m = re.exec(html)) !== null) {
    var name = m[1].replace(/^Матч\s+/, ''), parts = name.split(' - ');
    if (parts.length !== 2) continue;
    var key = m[2] + m[3] + m[4] + '|' + name;
    if (seen[key]) continue;
    seen[key] = true;
    var st = new Date(m[2] + '-' + m[3] + '-' + m[4] + 'T' + m[5]);
    out.push({ iso: m[2] + '-' + m[3] + '-' + m[4], date: m[4] + '.' + m[3] + '.' + m[2],
               home: parts[0].trim(), away: parts[1].trim(), name: name, url: m[6], start: isNaN(st.getTime()) ? null : st });
  }
  return out;
}

/** Счёт со страницы матча: {homeGoals, awayGoals, ot} или null (не тот матч / не завершён / не разобрали). */
function mpParseMatchPage_(html, item) {
  if (!html) return null;
  var esc = function (s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); };
  if (!new RegExp('"name":"' + esc(item.name) + '","startDate":"' + item.iso).test(html)) return null;   // другой матч этих команд
  var st = html.match(/data-testid="match-status"[^>]*>\s*<span[^>]*>([^<]+)</);
  if (!st || !/Завершен/i.test(st[1])) return null;
  var at = html.indexOf('match-summary__teams');
  if (at < 0) return null;
  var text = html.slice(at, at + 15000).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  var sc = text.match(/\s(\d{1,2})\s+(\d{1,2})\s+(ОТ|Б|OT|SO)?\s*\d{1,2}-\d{1,2}/);
  if (!sc) return null;
  return { homeGoals: Number(sc[1]), awayGoals: Number(sc[2]), ot: !!sc[3] };
}


/* ==========================================================================
 * 🧠 АГЕНТ ДЖАРВИСА — этап 1: утренняя сводка по матчам дня
 *
 *  Поиск: Tavily (бесплатно 1000 кредитов/мес; глубокий поиск = 2 кредита).
 *  Модель: Gemini (бесплатный тариф). Ключи — в свойствах скрипта:
 *    TAVILY_KEY, GEMINI_KEY  (необязательно: GEMINI_MODEL — какую модель брать).
 *  Правила для модели: только факты из найденных статей, у каждого — ссылка,
 *  нет данных — так и пишем. Модель выбирается один раз и записывается в
 *  свойства; сама она не меняется — если перестанет работать, агент сообщит.
 *  Результат: лист «Агент_сводки» + сообщение админу в личку от бота.
 * ==========================================================================*/

var AGENT_SHEET = 'Агент_сводки';
var AGENT_HEADER = ['Дата', 'Матч', 'Хозяева: состав и травмы', 'Гости: состав и травмы', 'Вратари', 'Форма и настрой', 'Важное', 'Источники', 'Создано (МСК)'];

function agentProps_() { return PropertiesService.getScriptProperties(); }
function agentMskDay_(d) { return Utilities.formatDate(d || new Date(), 'Europe/Moscow', 'yyyy-MM-dd'); }

/** Матчи дня (по МСК) из листа результатов: [{home, away, time}] */
function agentMatchesOfDay_(ss, dayKey) {
  var sh = ss.getSheetByName(SHEET_RESULTS);
  if (!sh || sh.getLastRow() < 2) return [];
  var odds = {};
  try { odds = readOddsLog_(ss); } catch (e) { odds = {}; }
  var out = [];
  sh.getRange(2, 1, sh.getLastRow() - 1, 4).getValues().forEach(function (r) {
    if (!(r[0] instanceof Date) || sheetDayKey_(r[0]) !== dayKey) return;
    var home = String(r[2]).trim(), away = String(r[3]).trim();
    if (!home || !away) return;
    var o = odds[dayKey + '|' + home + '|' + away];
    out.push({ home: home, away: away, time: o && o.time ? o.time : '', day: dayKey });
  });
  out.sort(function (a, b) { return a.time < b.time ? -1 : 1; });
  return out;
}

/** Tavily: учёт кредитов за месяц, чтобы не выйти за бесплатный лимит. */
function agentTavilyBudget_(cost) {
  var p = agentProps_(), month = Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM');
  var st = {};
  try { st = JSON.parse(p.getProperty('AGENT_TAVILY_USAGE') || '{}'); } catch (e) { st = {}; }
  if (st.month !== month) st = { month: month, used: 0 };
  if (cost === undefined) return st;
  if (st.used + cost > AGENT_TAVILY_MONTHLY_CAP) return null;
  st.used += cost;
  p.setProperty('AGENT_TAVILY_USAGE', JSON.stringify(st));
  return st;
}

/** Как команду называют в текстах (корень слова, чтобы ловить падежи: «Автомобилиста», «Ак Барсу»). */

/** Сколько раз команда упомянута в тексте (с падежами; ЦСКА не считается за СКА). */
function agentMentionCount_(text, team) {
  var t = ' ' + String(text || '').toLowerCase().replace(/ё/g, 'е').replace(/[«»"“”„'`]/g, '') + ' ';
  var stems = AGENT_TEAM_STEMS[team] || String(team).toLowerCase().slice(0, Math.max(4, String(team).length - 1));
  if (team === 'СКА') t = t.replace(/цска/g, ' ');
  var m = t.match(new RegExp('(^|[^а-яa-z])(' + stems + ')', 'g'));
  return m ? m.length : 0;
}
function agentMentions_(text, team) { return agentMentionCount_(text, team) > 0; }

/** Почему статья не годится ('' — годится): служебные страницы, спам, другой спорт, другие лиги. */
function agentDocReject_(d) {
  var u = String(d.url || '').toLowerCase(), t = (String(d.title || '') + ' ' + String(d.text || '')).toLowerCase().replace(/ё/g, 'е');
  if (/kunghac|amsiga|hacked|earn money|make money|casino|казино|snapchat|facebook/.test(u + ' ' + t)) return 'спам';
  if (/\/search|[?&](searchstr|q|query|s)=|\/tags?\/|\/stat\/|\/lenta\/|\/(club|clubs|team|teams)\/[a-z0-9_-]+\/?$/.test(u)) return 'служебная страница';
  if (/\/game\/|\/tv(\?|\/|$)|\/betting\/|\/player\/|\/video(\/|$)|raspisanie|translyaci|gde-igrayut/.test(u)) return 'расписание/протокол/ставки';
  var age = agentDocAgeDays_(d);
  if (age !== null && age > 21) return 'старше 3 недель';
  if (/football|futbol|soccer|\/figure|figur|basket|tennis|volley|boxing|\/mma|biathlon|\/ski|formula|chess|bandy|\/cyber/.test(u)) return 'другой вид спорта';
  if (/(^|[\/.])(mhl|vhl|khl|mkhl|whl|ahl|ncaa)([\/.]|$)|\/junior|\/tournament\/khl/.test(u)) return 'другая лига (КХЛ/АХЛ/МХЛ)';
  var hockeyUrl = /hockey|nhl|allhockey/.test(u), hockeyText = /хокке|нхл|шайб|вратар|буллит|овертайм/.test(t);
  if (!hockeyUrl && !hockeyText) return 'не про хоккей';
  if (!hockeyText && /футбол|рпл|футболист/.test(t)) return 'другой вид спорта';
  return '';
}

/** Возраст статьи в днях (по дате из поиска или из адреса); null — дата неизвестна. */
function agentDocAgeDays_(d) {
  var t = NaN;
  if (d.date) t = new Date(d.date).getTime();
  if (isNaN(t)) { var m = String(d.url || '').match(/\/(20\d\d)\/(\d\d)\/(\d\d)\//); if (m) t = new Date(+m[1], +m[2] - 1, +m[3]).getTime(); }
  return isNaN(t) ? null : Math.floor((Date.now() - t) / 86400000);
}

/** Поиск + отбор статей про команду(ы).
 *  Сначала отсеиваем мусор; затем «сильные» статьи — команда в заголовке или ≥2 упоминаний в тексте.
 *  Сильных меньше двух — один поиск шире (новости за месяц); всё ещё мало — добавляем статьи с одним упоминанием. */
function agentSearchAbout_(query, teams, broadQuery) {
  var rejected = {}, seen = {};
  var score = function (d) {
    return Math.max.apply(null, teams.map(function (t) { return 3 * agentMentionCount_(d.title, t) + agentMentionCount_(d.text, t); }));
  };
  var take = function (docs) {
    return docs.filter(function (d) {
      if (seen[d.url]) return false; seen[d.url] = true;
      var why = agentDocReject_(d);
      if (why) { rejected[why] = (rejected[why] || 0) + 1; return false; }
      d.score = score(d);
      if (!d.score) { rejected['не про эту команду'] = (rejected['не про эту команду'] || 0) + 1; return false; }
      return true;
    });
  };
  var docs = take(agentTavilySearch_(query));
  var strong = function () { return docs.filter(function (d) { return d.score >= 2; }); };
  if (strong().length < 2 && broadQuery) docs = docs.concat(take(agentTavilySearch_(broadQuery)));
  docs.sort(function (a, b) { return b.score - a.score; });
  var out = strong();
  if (out.length < 2) out = out.concat(docs.filter(function (d) { return d.score < 2; })).slice(0, 4);
  out = out.slice(0, 8);
  out.rejected = rejected;
  return out;
}

/** Коротко, что отсеяли: «отсеяно: спам 3, другой вид спорта 2» */
function agentRejectedNote_(docs) {
  var r = (docs && docs.rejected) || {}, k = Object.keys(r);
  return k.length ? 'отсеяно: ' + k.map(function (x) { return x + ' ' + r[x]; }).join(', ') : '';
}

function agentTavilySearch_(query, opt) {
  opt = opt || {};
  var key = agentProps_().getProperty('TAVILY_KEY');
  if (!key) throw new Error('нет ключа TAVILY_KEY в свойствах скрипта');
  if (!agentTavilyBudget_(2)) throw new Error('исчерпан месячный лимит поиска (' + AGENT_TAVILY_MONTHLY_CAP + ' кредитов)');
  var resp = UrlFetchApp.fetch('https://api.tavily.com/search', {
    method: 'post', contentType: 'application/json', muteHttpExceptions: true,
    headers: { Authorization: 'Bearer ' + key },
    payload: JSON.stringify({ query: query, topic: opt.topic || 'news', search_depth: 'advanced', time_range: opt.time_range || 'week',
      max_results: 10, include_domains: AGENT_DOMAINS, include_answer: false, include_raw_content: false })
  });
  var code = resp.getResponseCode(), body = {};
  try { body = JSON.parse(resp.getContentText()); } catch (e) { body = {}; }
  if (code !== 200) throw new Error('поиск ответил кодом ' + code + (body.detail ? ': ' + JSON.stringify(body.detail).slice(0, 200) : ''));
  return (body.results || []).map(function (r) {
    return { title: String(r.title || ''), url: String(r.url || ''), text: String(r.content || '').slice(0, 1800), date: r.published_date || '' };
  });
}

/** Модель Gemini: из свойства GEMINI_MODEL; если не задана — один раз находим flash-lite и записываем. */
function agentGeminiModel_() {
  var p = agentProps_(), m = p.getProperty('GEMINI_MODEL');
  if (m) return m;
  var key = p.getProperty('GEMINI_KEY');
  if (!key) throw new Error('нет ключа GEMINI_KEY в свойствах скрипта');
  var resp = UrlFetchApp.fetch('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200&key=' + encodeURIComponent(key), { muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) throw new Error('Gemini не отдал список моделей (код ' + resp.getResponseCode() + '): ' + resp.getContentText().slice(0, 300));
  var models = (JSON.parse(resp.getContentText()).models || []).filter(function (x) {
    return (x.supportedGenerationMethods || []).indexOf('generateContent') !== -1 && /flash/i.test(x.name) && !/image|tts|audio|live|preview|exp/i.test(x.name);
  }).map(function (x) { return x.name.replace(/^models\//, ''); });
  var lite = models.filter(function (n) { return /lite/i.test(n); });
  var pick = (lite.length ? lite : models).sort().reverse()[0];
  if (!pick) throw new Error('не нашёл подходящую модель Gemini Flash');
  p.setProperty('GEMINI_MODEL', pick);
  return pick;
}

/** JSON из ответа модели: без ```-обёртки, с переносами строк внутри текста, с лишним текстом вокруг. null — не разобрать. */
function agentJsonSafe_(text) {
  var t = String(text || '').trim().replace(/^```(json)?\s*|\s*```$/g, '');
  var tries = [t];
  var a = t.indexOf('{'), b = t.lastIndexOf('}');
  if (a >= 0 && b > a) tries.push(t.slice(a, b + 1));
  var fixCtl = function (x) {                                                   // переносы и табы внутри строк → \n, \t
    var out = '', inStr = false, esc = false;
    for (var i = 0; i < x.length; i++) {
      var c = x.charAt(i);
      if (inStr && !esc && (c === '\n' || c === '\r' || c === '\t')) { out += c === '\t' ? '\\t' : c === '\n' ? '\\n' : ''; continue; }
      if (c === '"' && !esc) inStr = !inStr;
      esc = inStr && c === '\\' && !esc;
      out += c;
    }
    return out;
  };
  tries.push(fixCtl(tries[tries.length - 1]));
  for (var k = 0; k < tries.length; k++) { try { var j = JSON.parse(tries[k]); if (j && typeof j === 'object') return j; } catch (e) {} }
  return null;
}

function agentGemini_(prompt) {
  var key = agentProps_().getProperty('GEMINI_KEY');
  if (!key) throw new Error('нет ключа GEMINI_KEY в свойствах скрипта');
  var model = agentGeminiModel_();
  var resp = UrlFetchApp.fetch('https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent?key=' + encodeURIComponent(key), {
    method: 'post', contentType: 'application/json', muteHttpExceptions: true,
    payload: JSON.stringify({ contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.2, responseMimeType: 'application/json' } })
  });
  var code = resp.getResponseCode(), txt = resp.getContentText();
  if (code !== 200) throw new Error('Gemini (' + model + ') ответил кодом ' + code + ': ' + txt.slice(0, 300));
  var body = JSON.parse(txt);
  var out = ((((body.candidates || [])[0] || {}).content || {}).parts || []).map(function (p) { return p.text || ''; }).join('');
  if (!out) throw new Error('Gemini вернул пустой ответ');
  return { model: model, text: out };
}

function agentPrompt_(m, docs, dosH, dosA, today) {
  var src = docs.map(function (d, i) {
    return '[' + (i + 1) + '] ' + d.title + (d.date ? ' (' + d.date + ')' : '') + (/\/blogs\//.test(d.url) ? ' [блог болельщика]' : '') + '\n' + d.url + '\n' + d.text;
  }).join('\n\n');
  var dos = function (team, d) {
    return team + ':\n' + DOSSIER_FIELDS.map(function (f) { return '  ' + f[1] + ': ' + (d && d[f[0]] ? d[f[0]] : 'пусто'); }).join('\n') +
      (d && d.updated ? '\n  (досье обновлено ' + d.updated + ')' : '');
  };
  return 'Ты — аналитик хоккейного канала. Сегодня ' + today + '. Матч НХЛ: ' + m.home + ' (хозяева) — ' + m.away + ' (гости).\n\n' +
    'ПРАВИЛА:\n' +
    '1. Факты бери ТОЛЬКО из статей ниже и из досье. Ничего не придумывай и не достраивай по памяти.\n' +
    '2. К каждому факту из статей ставь номер источника, например [2]. Факты из досье помечай [досье].\n' +
    '3. Про каждого игрока пиши, за какую команду он играет. Если из статьи неясно, чей он, — не упоминай.\n' +
    '4. Цифры (голы, очки, серии) приводи только если в статье прямо сказано, к какой команде они относятся.\n' +
    '5. Нет данных по пункту — пиши ровно «нет данных». Статьи о других матчах и прошлых сезонах игнорируй. Прогнозы капперов не пересказывай.\n' +
    '6. Блоги болельщиков — менее надёжны: составы из них помечай «ориентировочно».\n' +
    '7. Только НХЛ: факты о клубах-тёзках из других видов спорта, фарм-клубах (АХЛ), КХЛ и сборных игнорируй.\n' +
    '8. Не пиши «2 weeks ago», «вчера» и т.п. — переводи в дату по дате статьи или не указывай дату.\n' +
    '9. Источники «Telegram …» — посты инсайдеров и журналистов: слухи помечай «по данным <канал>».\n\n' +
    'ДОСЬЕ (что агент знал до сегодняшних статей):\n' + dos(m.home, dosH) + '\n' + dos(m.away, dosA) + '\n\n' +
    'Верни JSON строго такого вида (на русском):\n' +
    '{"home_lineup":"состав/травмы/дисквалификации хозяев (до 250 знаков)","away_lineup":"то же для гостей",' +
    '"goalies":"кто в воротах у обеих команд, если известно","form":"форма и серии обеих команд","key":"главное для исхода матча одной-двумя фразами",' +
    '"sources":[номера использованных статей],' +
    '"dossier_home":{' + DOSSIER_FIELDS.map(function (f) { return '"' + f[0] + '":"..."'; }).join(',') + '},' +
    '"dossier_away":{то же для гостей},' +
    '"signals":[{"team":"home или away","factor":"одно из: ' + SIGNAL_FACTORS.join(', ') + '","effect":"+ если помогает этой команде, - если мешает",' +
    '"strength":"1-3","text":"вывод одной фразой со ссылкой [n]"}],' +
    '"lean":"home, away или none — в чью пользу новости в целом (none, если явного перевеса нет)"}\n\n' +
    'signals — это твои проверяемые выводы: только факторы из статей и досье, которые реально могут повлиять на исход (до 5 штук). ' +
    'Не выдумывай факторов ради количества: нет — пустой список. Прогнозов на счёт не давай.\n\n' +
    'Как обновлять досье: это ПОЛНЫЙ новый текст каждого пункта (до 300 знаков). Сохрани из старого досье то, что по-прежнему верно, ' +
    'добавь новое из статей, убери то, что статьи опровергают или что старше трёх недель. У травм и замен вратарей ставь дату в формате (с ДД.ММ). ' +
    'Если по пункту нет ни старых, ни новых данных — «нет данных».\n\n' +
    'СТАТЬИ:\n' + src;
}

/** Сводка по одному матчу: {home_lineup, away_lineup, goalies, form, key, links[]} */
function agentBriefMatch_(m, ss) {
  ss = ss || SpreadsheetApp.getActive();
  // сначала бесплатные источники: новости клубов на sports.ru и Telegram-каналы
  var docs = [], toDoc = function (n) { return { title: n.title, url: n.url, text: '', date: n.date ? Utilities.formatDate(n.date, 'Europe/Moscow', 'dd.MM') : '' }; };
  var tgPosts = []; try { tgPosts = expertPostsAll_(ss); } catch (e) { tgPosts = []; }
  [m.home, m.away].forEach(function (t) {
    var own = []; try { own = sportsClubNews_(t); } catch (e) { own = []; }
    var near = own.filter(function (n) { return !n.date || (Date.now() - n.date.getTime()) / 86400000 <= 7; }).slice(0, 8);
    docs = docs.concat(near.map(toDoc), expertPostsAbout_(tgPosts, t, 4).map(toDoc));
  });
  var seenU = {}; docs = docs.filter(function (d) { if (seenU[d.url]) return false; seenU[d.url] = true; return true; });
  var lineup = {}; try { var kp = lineupKeyPlayers_(ss); lineup.home = lineupStatus_(kp[m.home], m.home); lineup.away = lineupStatus_(kp[m.away], m.away);
    ['home', 'away'].forEach(function (sd) { var x = kp[sd === 'home' ? m.home : m.away]; if (lineup[sd] && x && x.lastUrl) docs.unshift({ title: 'Заявки прошлых матчей (sports.ru): ' + lineup[sd].text.replace(/^\S+ /, ''), url: x.lastUrl, text: '', date: '' }); });
  } catch (e) { lineup = {}; }
  if (docs.length < 4) {
    try {
      docs = docs.concat(agentSearchAbout_(m.home + ' ' + m.away + ' НХЛ матч состав травмы вратарь', [m.home, m.away], m.home + ' ' + m.away + ' хоккей НХЛ')
        .filter(function (d) { return !seenU[d.url]; }));
    } catch (e) { if (!docs.length) throw e; }
  }
  var extra = null; try { extra = agentExtraContext_(m, ss); } catch (e) { extra = null; }
  if (extra && extra.docs && extra.docs.length) docs = extra.docs.concat(docs);
  try { docs = scoutFactsDocs_(ss, [m.home, m.away]).concat(docs); } catch (e) { /* Разведчик не настроен */ }
  if (!docs.length) return { empty: true, home_lineup: 'нет данных', away_lineup: 'нет данных', goalies: 'нет данных',
    form: 'нет данных', key: 'Свежих статей о матче не нашлось.', links: [] };
  var dossier = dossierRead_(ss);
  var prompt = agentPrompt_(m, docs, dossier[m.home], dossier[m.away], mskNow_('dd.MM.yyyy'));
  var g = agentGemini_(prompt), j = agentJsonSafe_(g.text);
  if (!j) { g = agentGemini_(prompt); j = agentJsonSafe_(g.text); }                  // оборванный или кривой ответ — ещё одна попытка
  if (!j) throw new Error('модель вернула не JSON: ' + g.text.slice(0, 200));
  var used = (j.sources || []).map(Number).filter(function (n) { return n >= 1 && n <= docs.length; });
  if (!used.length) used = docs.map(function (_, i) { return i + 1; }).slice(0, 3);
  var clean = function (s, n) { return String(s || 'нет данных').replace(/\s+/g, ' ').trim().slice(0, n || 400); };
  var links = used.map(function (n) { return { n: n, url: docs[n - 1].url, title: docs[n - 1].title, blog: /\/blogs\//.test(docs[n - 1].url), tg: /^https:\/\/t\.me\//.test(docs[n - 1].url) }; });
  var srcText = links.map(function (l) { return '[' + l.n + '] ' + l.url; }).join(' ');
  [[m.home, j.dossier_home], [m.away, j.dossier_away]].forEach(function (x) {
    if (!x[1] || typeof x[1] !== 'object') return;
    try { var f = dossierFormText_(ss, x[0]); if (f) x[1].form = f; } catch (e) {}
    dossierWrite_(ss, x[0], x[1], srcText);
  });
  j.signals = (Array.isArray(j.signals) ? j.signals.slice(0, 5) : []);
  ['home', 'away'].forEach(function (sd) { if (lineup[sd]) lineup[sd].signals.forEach(function (x) { x.team = sd; j.signals.push(x); }); });
  var sig = null; try { sig = agentSignalsSave_(ss, m, m.day || agentMskDay_(), j); } catch (e) { sig = null; }
  return { model: g.model, signals: sig ? sig.n : 0, lean: sig ? sig.lean : '', leanText: sig ? sig.leanText : '',
    lineups: [lineup.home, lineup.away].filter(Boolean).map(function (x) { return x.text; }),
    home_lineup: clean(j.home_lineup), away_lineup: clean(j.away_lineup), goalies: clean(j.goalies),
    form: clean(j.form), key: clean(j.key), links: links, extra: extra && extra.lines ? extra.lines : [] };
}

/* ── Диагностика источников составов (бесплатно: ни поиска, ни ИИ). Сохраняет, что отдают страницы, чтобы написать разбор. ── */
var LINEUP_DIAG_SHEET = 'Диагностика_составов';

/** Таблицы игроков со страницы составов sports.ru: [{caption, heading, players:[{num,name,toi}]}] */
function lineupTables_(html) {
  var out = [], re = /<caption class="stat-table__caption"[^>]*>([\s\S]*?)<\/caption>/g, m;
  while ((m = re.exec(html))) {
    var start = m.index, end = html.indexOf('</table>', start); if (end < 0) end = start + 200000;
    var body = html.slice(start, end), before = html.slice(Math.max(0, start - 6000), start);
    var heads = before.match(/<(h[1-4]|button|a)[^>]*>([^<]{2,60})<\/\1>/g) || [];
    var players = [], rr = /<tr class="table-row table-row--td"[\s\S]*?<\/tr>/g, row;
    while ((row = rr.exec(body))) {
      var r = row[0], nm = r.match(/data-col="player"[\s\S]*?title="([^"]+)"/), num = r.match(/stat-table-position-cell__position[^>]*>([^<]*)</), toi = r.match(/data-col="timeOnIce"[^>]*>(?:<!--\[-->)*\s*([^<]*)/);
      if (nm) players.push({ num: num ? num[1].trim() : '', name: sportsText_(nm[1]), toi: toi ? sportsText_(toi[1]) : '' });
    }
    out.push({ caption: sportsText_(m[1]), heading: heads.slice(-3).map(function (h) { return sportsText_(h); }).join(' | '), players: players });
  }
  return out;
}

/** Минифицированный объект вида {a:b,"c":"d",e:[x]} → JSON-текст; идентификаторы-значения берутся из vars. */
function jsObjToJson_(src, vars) {
  var out = '', i = 0, n = src.length;
  while (i < n) {
    var ch = src[i];
    if (ch === '"' || ch === "'") {
      var q = ch, j = i + 1, buf = '';
      while (j < n && src[j] !== q) { if (src[j] === '\\') { buf += src[j] + src[j + 1]; j += 2; continue; } buf += src[j]; j++; }
      if (q === "'") buf = buf.replace(/\\'/g, "'").replace(/"/g, '\\"');
      out += '"' + buf + '"'; i = j + 1; continue;
    }
    if (/[A-Za-z_$]/.test(ch)) {
      var k = i; while (k < n && /[\w$]/.test(src[k])) k++;
      var id = src.slice(i, k), rest = src.slice(k).match(/^\s*(:)?/);
      if (rest[1] && /[{,]\s*$/.test(out)) out += '"' + id + '"';                      // ключ
      else if (id === 'void') { out += 'null'; k = src.indexOf('0', k) + 1; }
      else if (id === 'true' || id === 'false' || id === 'null') out += id;
      else if (id === 'undefined' || id === 'NaN' || id === 'Infinity') out += 'null';
      else out += JSON.stringify(vars && Object.prototype.hasOwnProperty.call(vars, id) ? vars[id] : null);
      i = k; continue;
    }
    out += ch; i++;
  }
  return out;
}

/** Конец сбалансированного блока, начинающегося с открывающей скобки в позиции p (строки учитываются). */
function jsBlockEnd_(src, p) {
  var open = src[p], close = open === '{' ? '}' : open === '[' ? ']' : ')', depth = 0;
  for (var i = p; i < src.length; i++) {
    var ch = src[i];
    if (ch === '"' || ch === "'") { var q = ch; i++; while (i < src.length && src[i] !== q) { if (src[i] === '\\') i++; i++; } continue; }
    if (ch === '{' || ch === '[' || ch === '(') depth++;
    else if (ch === '}' || ch === ']' || ch === ')') { depth--; if (depth === 0) return i; }
  }
  return -1;
}

/** Составы со страницы «составы» матча sports.ru: {home:{players}, away:{players}, found:bool}.
 *  players: [{id, name, num, pos:'G'|'D'|'F'|'', toi:'мм:сс'|'', goals, assists, shotsAgainst, saves}] */
function sportsLineupsFromHtml_(html) {
  var res = { home: { players: [] }, away: { players: [] }, found: false, vars: 0 };
  var at = html.indexOf('"hockey-online-lineups":');
  if (at < 0) return res;
  var ob = html.indexOf('{', at), oe = jsBlockEnd_(html, ob);
  if (ob < 0 || oe < 0) return res;
  // переменные: ищем ближайшую выше функцию-обёртку (function(a,b,...){...}(аргументы))
  var vars = {}, fnRe = /function\s*\(([\w$,\s]*)\)\s*\{/g, fm, fn = null;
  var scStart = html.lastIndexOf('<script', at);
  fnRe.lastIndex = scStart < 0 ? 0 : scStart;
  while ((fm = fnRe.exec(html)) && fm.index < at) fn = { params: fm[1], bodyStart: fm.index + fm[0].length - 1 };
  if (fn && fn.params.trim()) {
    var bodyEnd = jsBlockEnd_(html, fn.bodyStart);
    if (bodyEnd > oe) {
      var k = bodyEnd + 1; while (k < html.length && /[\s)]/.test(html[k])) k++;
      if (html[k] === '(') {
        var ae = jsBlockEnd_(html, k);
        try {
          var args = JSON.parse(jsObjToJson_('[' + html.slice(k + 1, ae) + ']', {}));
          fn.params.split(',').forEach(function (nm, idx) { vars[nm.trim()] = args[idx]; });
          res.vars = args.length;
        } catch (e) { res.varsError = e.message; }
      }
    }
  }
  var data;
  try { data = JSON.parse(jsObjToJson_(html.slice(ob, oe + 1), vars)); } catch (e) { res.error = e.message; return res; }
  var posOf = function (p, st) {
    var f = String(p.fieldPosition || p.convertedFieldPosition || '').toLowerCase();
    if (/вратар|goal|^g/.test(f)) return 'G';
    if (/защит|defen|^d/.test(f)) return 'D';
    if (/напад|forw|^f|center|wing/.test(f)) return 'F';
    if (st && typeof st.gkSavePercentage === 'string') return 'G';                       // вратарь, который играл
    if (st && res.vars && st.goals === null && st.timeOnIce === null) return 'G';           // запасной вратарь: у полевых голы = 0, у него пусто
    return '';
  };
  ['home', 'away'].forEach(function (side) {
    var t = data[side] || {}, st = t.stat || {};
    (t.players || []).forEach(function (p) {
      var s0 = st[p.id] || {};
      res[side].players.push({ id: p.id, name: p.name, num: p.jerseyNumber || '', pos: posOf(p, s0), toi: typeof s0.timeOnIce === 'string' ? s0.timeOnIce : '',
        goals: s0.goals, assists: s0.assists, shotsAgainst: s0.shotsAgainst, saves: s0.saves, rawPos: p.fieldPosition });
    });
  });
  res.found = res.home.players.length + res.away.players.length > 0;
  return res;
}


/* ─────────────── СОСТАВЫ: кто реально играет (бесплатно, со страниц «составы» матчей sports.ru) ───────────────
 * После каждого игрового дня скрипт сохраняет заявки обеих команд: кто играл, сколько минут, очки, кто стоял в воротах.
 * По ним считаются ключевые игроки (основной вратарь по числу стартов, лидеры по игровому времени и очкам)
 * и кто из них не попал в заявку прошлого матча — это обычно травма или болезнь, часто раньше, чем в новостях. */
var LINEUP_SHEET = 'Составы_матчей';
var KEY_SHEET = 'Ключевые_игроки';
var LINEUP_HEADER = ['Дата', 'Хозяева', 'Гости', 'Команда', 'Поз.', '№', 'Игрок', 'Время (мин)', 'Голы', 'Передачи', 'Броски по воротам', 'Отражено', 'Страница'];
var LINEUP_RECENT = 15;       // по скольким последним матчам команды считаем ключевых
var LINEUP_POS = { GOALKEEPER: 'G', DEFENDER: 'D', FORWARD: 'F', G: 'G', D: 'D', F: 'F' };

function lineupSheet_(ss) {
  var sh = ss.getSheetByName(LINEUP_SHEET);
  if (sh) return sh;
  sh = ss.insertSheet(LINEUP_SHEET);
  sh.getRange(1, 1, 1, LINEUP_HEADER.length).setValues([LINEUP_HEADER]).setFontWeight('bold');
  sh.setFrozenRows(1);
  return sh;
}
function lineupToi_(s) { var m = String(s || '').match(/^(\d+):(\d\d)$/); return m ? Math.round((+m[1] + m[2] / 60) * 100) / 100 : 0; }

/** Месяцы сезона от сентября до текущего (для календаря sports.ru ?m=). */
function lineupSeasonMonths_(now) {
  var cur = (now || new Date()).getMonth() + 1, out = [];
  if (cur >= 9) { for (var m = 9; m <= cur; m++) out.push(m); }
  else { for (var a = 9; a <= 12; a++) out.push(a); for (var b = 1; b <= cur; b++) out.push(b); }
  return out;
}


/** Ключевые игроки и состояние заявки каждой команды по последним матчам. {team: info} */
function lineupKeyPlayers_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(LINEUP_SHEET), by = {};
  if (!sh || sh.getLastRow() < 2) return {};
  sh.getRange(2, 1, sh.getLastRow() - 1, LINEUP_HEADER.length).getValues().forEach(function (r) {
    var team = String(r[3]).trim(); if (!team || !r[6]) return;
    var day = signalDay_(r[0]), mk = day + '|' + r[1] + '|' + r[2];
    var t = by[team] || (by[team] = {}), m = t[mk] || (t[mk] = { day: day, opp: r[1] === team ? r[2] : r[1], url: r[12], players: {} });
    m.players[r[6]] = { pos: r[4], toi: Number(r[7]) || 0, pts: (Number(r[8]) || 0) + (Number(r[9]) || 0) };
  });
  var out = {};
  Object.keys(by).forEach(function (team) {
    var games = Object.keys(by[team]).map(function (k) { return by[team][k]; }).sort(function (a, b) { return a.day < b.day ? 1 : -1; }).slice(0, LINEUP_RECENT);
    var n = games.length, last = games[0];
    // вратари: стартовый в матче — вратарь с наибольшим временем
    var starts = {}, lastStarter = '';
    games.slice(0, 10).forEach(function (g, gi) {
      var best = '', bt = 0;
      Object.keys(g.players).forEach(function (nm) { var p = g.players[nm]; if (p.pos === 'G' && p.toi > bt) { bt = p.toi; best = nm; } });
      if (best) { starts[best] = (starts[best] || 0) + 1; if (gi === 0) lastStarter = best; }
    });
    var gk = Object.keys(starts).sort(function (a, b) { return starts[b] - starts[a]; });
    var main = gk[0] || '', of = Math.min(10, n);
    // полевые
    var st = {};
    games.forEach(function (g) {
      Object.keys(g.players).forEach(function (nm) {
        var p = g.players[nm]; if (p.pos === 'G') return;
        var s = st[nm] || (st[nm] = { name: nm, pos: p.pos, gp: 0, toi: 0, pts: 0 });
        if (p.toi > 0) { s.gp++; s.toi += p.toi; } s.pts += p.pts;
      });
    });
    var minGp = Math.max(2, Math.ceil(n * 0.4));
    var pool = Object.keys(st).map(function (k) { var s = st[k]; s.avg = s.gp ? s.toi / s.gp : 0; return s; }).filter(function (s) { return s.gp >= minGp; });
    var pick = function (arr, k, role) { return arr.slice(0, k).map(function (s) { return { name: s.name, pos: s.pos, role: role, avg: s.avg, pts: s.pts, gp: s.gp }; }); };
    var keys = pick(pool.filter(function (s) { return s.pos === 'F'; }).sort(function (a, b) { return b.avg - a.avg; }), 3, 'лидер нападения по времени')
      .concat(pick(pool.filter(function (s) { return s.pos === 'D'; }).sort(function (a, b) { return b.avg - a.avg; }), 2, 'первая пара защиты'));
    pool.slice().sort(function (a, b) { return b.pts - a.pts || b.avg - a.avg; }).forEach(function (s) {
      if (keys.length < 7 && s.pts >= 3 && !keys.some(function (k) { return k.name === s.name; })) keys.push({ name: s.name, pos: s.pos, role: 'лидер по очкам', avg: s.avg, pts: s.pts, gp: s.gp });
    });
    var missed = function (nm) { var c = 0; for (var i = 0; i < games.length; i++) { if (games[i].players[nm]) break; c++; } return c; };
    keys.forEach(function (k) { k.missed = missed(k.name); });
    out[team] = { games: n, lastDay: last ? last.day : '', lastOpp: last ? last.opp : '', lastUrl: last ? last.url : '', main: main, mainStarts: main ? starts[main] : 0, of: of,
      mainMissed: main ? missed(main) : 0, lastStarter: lastStarter, keys: keys };
  });
  return out;
}

function lineupSurname_(nm) { var p = String(nm).trim().split(/\s+/); return p[p.length - 1]; }

/** Строка статуса команды для сводки: {level:0|1|2, emoji, text, signals:[]} */
function lineupStatus_(info, team) {
  if (!info || !info.games) return null;
  var level = 0, parts = [], signals = [];
  if (info.main && info.mainMissed >= 1) {
    level = 2;
    parts.push('нет основного вратаря ' + lineupSurname_(info.main) + ' (не в заявке ' + info.mainMissed + ' ' + (info.mainMissed === 1 ? 'матч' : 'матча') + ')' + (info.lastStarter ? ', играл ' + lineupSurname_(info.lastStarter) : ''));
    signals.push({ factor: 'вратарь', effect: '-', strength: 3, text: '[составы] Основной вратарь ' + info.main + ' не попал в заявку последнего матча' });
  } else if (info.main && info.lastStarter && info.lastStarter !== info.main) {
    level = 1;
    parts.push('в прошлом матче в воротах ' + lineupSurname_(info.lastStarter) + ', основной ' + lineupSurname_(info.main) + ' отдыхал');
  }
  var gone = info.keys.filter(function (k) { return k.missed >= 1; });
  if (gone.length) {
    level = Math.max(level, gone.length >= 2 ? 2 : 1);
    parts.push('не играли в прошлом матче: ' + gone.map(function (k) { return lineupSurname_(k.name) + ' (' + k.role + (k.missed > 1 ? ', пропустил ' + k.missed : '') + ')'; }).join(', '));
    signals.push({ factor: 'травмы', effect: '-', strength: gone.length >= 2 ? 2 : 1, text: '[составы] Не играли в прошлом матче: ' + gone.map(function (k) { return k.name; }).join(', ') });
  }
  var gtxt = info.main ? 'вратарь ' + lineupSurname_(info.main) + ' (' + info.mainStarts + ' из ' + info.of + ' стартов)' : '';
  var emoji = level === 2 ? '🔴' : level === 1 ? '🟡' : '🟢';
  return { level: level, emoji: emoji, text: emoji + ' ' + team + ' — ' + (parts.length ? parts.join('; ') : 'основа на месте') + (gtxt ? '; ' + gtxt : ''), signals: signals };
}

/** Лист «Ключевые игроки» — чтобы было видно, на чём основаны отметки. */
function lineupKeyRender_(ss, info) {
  ss = ss || SpreadsheetApp.getActive(); info = info || lineupKeyPlayers_(ss);
  var teams = Object.keys(info).sort(), rows = teams.map(function (t) {
    var x = info[t], st = lineupStatus_(x, t) || { emoji: '', text: '' };
    return [t, st.emoji, x.main ? x.main + ' — ' + x.mainStarts + ' из ' + x.of + (x.mainMissed ? ' (не в заявке ' + x.mainMissed + ')' : '') : '—',
      x.keys.map(function (k) { return k.name + ' (' + k.pos + ', ' + k.role + ': ' + Math.round(k.avg * 10) / 10 + ' мин за игру, ' + k.pts + ' очк. в ' + k.gp + ' играх)' + (k.missed ? ' — НЕ ИГРАЛ ' + k.missed : ''); }).join('\n'),
      x.lastDay ? x.lastDay.split('-').reverse().slice(0, 2).join('.') + ' с ' + x.lastOpp : '', x.games];
  });
  var sh = ss.getSheetByName(KEY_SHEET) || ss.insertSheet(KEY_SHEET);
  sh.clear();
  var head = ['Команда', 'Статус', 'Основной вратарь (стартов из последних)', 'Ключевые игроки (по последним ' + LINEUP_RECENT + ' матчам)', 'Последний матч', 'Матчей в базе'];
  sh.getRange(1, 1, 1, head.length).setValues([head]).setFontWeight('bold').setBackground('#1a4fd6').setFontColor('#ffffff');
  if (rows.length) sh.getRange(2, 1, rows.length, head.length).setValues(rows).setWrap(true).setVerticalAlignment('top');
  try { sh.setFrozenRows(1); sh.setColumnWidth(3, 230); sh.setColumnWidth(4, 520); } catch (e) {}
  return rows.length;
}

/** Меню: собрать составы и обновить ключевых игроков. Не успели — продолжит сам через минуту. */
function lineupsUpdateNow_(auto) {
  var ss = SpreadsheetApp.getActive(), r = lineupsCollect_(ss, 240000), n = lineupKeyRender_(ss);
  if (r.pending) { try { ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'lineupsContinue_') ScriptApp.deleteTrigger(t); });
    ScriptApp.newTrigger('lineupsContinue_').timeBased().after(60 * 1000).create(); } catch (e) {} }
  var msg = 'Составы: добавлено матчей ' + r.added + (r.pending ? ', осталось ' + r.pending + ' — продолжу сам через минуту' : ', все сыгранные матчи собраны') +
    (r.failed.length ? '\nНе разобраны: ' + r.failed.slice(0, 5).join('; ') : '') + '\nКлючевые игроки обновлены для ' + n + ' команд — лист «' + KEY_SHEET + '».';
  if (auto !== true) uiAlert_(msg);
  return r;
}
function lineupsContinue_() {
  try { ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'lineupsContinue_') ScriptApp.deleteTrigger(t); }); } catch (e) {}
  try { lineupsUpdateNow_(true); } catch (e) { console.log('lineups: ' + e.message); }
}

/* ─────────────── ЗАЯВКИ ЗА ЧАС ДО МАТЧА ───────────────
 * Каждые 5 минут (вместе с LIVE) смотрим матчи, до начала которых 5–95 минут. Если на странице «составы»
 * sports.ru появилась заявка — сравниваем её с ключевыми игроками и основным вратарём и шлём админу
 * 🟢🟡🔴 уже по сегодняшнему составу. Один раз на матч. Журнал «Заявки_наблюдение» показывает,
 * за сколько минут до начала заявка появляется (так поймём, насколько рано можно полагаться на неё). */
var LINEUP_WATCH_SHEET = 'Заявки_наблюдение';
var LINEUP_WATCH_FROM = 95, LINEUP_WATCH_TO = 5;          // окно: за сколько минут до начала смотрим
var LINEUP_MIN_PLAYERS = 15;                               // меньше — считаем, что заявки ещё нет

/** Адреса страниц «составы» на сегодня: {'Хозяева|Гости': url}. Календарь sports.ru грузим не чаще раза в 30 минут. */
function lineupWatchUrls_(day, force) {
  var p = PropertiesService.getScriptProperties(), c = {};
  try { c = JSON.parse(p.getProperty('LINEUP_URLS') || '{}'); } catch (e) { c = {}; }
  if (!force && c.day === day && c.map && (Object.keys(c.map).length || Date.now() - (c.ts || 0) < 30 * 60000)) return c.map;
  var map = {}, nameMap = buildNameMap_(), mon = Number(day.split('-')[1]);
  try {
    var r = UrlFetchApp.fetch('https://www.sports.ru/hockey/tournament/khl/calendar/2026-2027/?m=' + mon, { muteHttpExceptions: true, headers: SPORTS_UA });
    if (r.getResponseCode() === 200) mpCalendarItems_(r.getContentText()).forEach(function (it) {
      if (it.iso === day) map[normalizeTeam_(it.home, nameMap) + '|' + normalizeTeam_(it.away, nameMap)] = it.url.replace(/\/?$/, '/') + 'lineups/';
    });
  } catch (e) { /* попробуем позже */ }
  p.setProperty('LINEUP_URLS', JSON.stringify({ day: day, ts: Date.now(), map: map }));
  return map;
}

/** Есть ли игрок в заявке: полное имя или та же фамилия + первая буква имени («Д. Кин» = «Джоуи Кин»). */
function lineupHas_(decl, name) {
  if (decl.names[name]) return true;
  var p = String(name).trim().split(/\s+/), sur = p[p.length - 1], ini = (p[0] || '').charAt(0);
  return decl.list.some(function (n) { var q = String(n).trim().split(/\s+/); return q[q.length - 1] === sur && (q[0] || '').charAt(0) === ini; });
}

/** Отметка по заявке на сегодняшний матч. */
function lineupPreStatus_(info, team, decl) {
  var level = 0, parts = [];
  if (info && info.main && !lineupHas_(decl, info.main)) { level = 2; parts.push('нет основного вратаря ' + lineupSurname_(info.main)); }
  var keys = info ? info.keys : [];
  var gone = keys.filter(function (k) { return !lineupHas_(decl, k.name); });
  if (gone.length) { level = Math.max(level, gone.length >= 2 ? 2 : 1); parts.push('нет в заявке: ' + gone.map(function (k) { return lineupSurname_(k.name) + ' (' + k.role + ')'; }).join(', ')); }
  var back = keys.filter(function (k) { return k.missed >= 1 && lineupHas_(decl, k.name); });
  if (back.length) parts.push('вернулись: ' + back.map(function (k) { return lineupSurname_(k.name); }).join(', '));
  var gk = decl.goalies.map(lineupSurname_).join(', ');
  var emoji = level === 2 ? '🔴' : level === 1 ? '🟡' : '🟢';
  return { level: level, text: emoji + ' ' + team + ' — ' + (parts.length ? parts.join('; ') : 'основа на месте') + (gk ? '; вратари в заявке: ' + gk : '') };
}

function lineupDecl_(players) {
  var d = { names: {}, list: [], goalies: [] };
  players.forEach(function (p) { d.names[p.name] = true; d.list.push(p.name); if (p.pos === 'G' || /GOAL/i.test(String(p.rawPos || ''))) d.goalies.push(p.name); });
  return d;
}



/* ─────────────── АВТОМАТИКА: всё, что было по кнопкам ───────────────
 * Один пункт меню ставит все запуски. Утреннее обновление само доставит недостающие триггеры
 * (ensureAutomation_), так что после вставки нового кода ничего нажимать не обязательно.
 * Статус каждого запуска — на листе «Автоматика»; при проблемах утреннего обновления — сообщение админу. */
var AUTO_SHEET = 'Автоматика';

function autoMark_(fn, ok, msg) {
  var p = PropertiesService.getScriptProperties(), st = {};
  try { st = JSON.parse(p.getProperty('AUTO_STATUS') || '{}'); } catch (e) { st = {}; }
  st[fn] = { t: mskNow_('dd.MM HH:mm'), ok: !!ok, msg: String(msg || '').slice(0, 160) };
  p.setProperty('AUTO_STATUS', JSON.stringify(st));
}

function autoNotifyAdmin_(text) {
  var to = PropertiesService.getScriptProperties().getProperty('TG_ADMIN_ID');
  if (!to) return false;
  try { var r = tg_('sendMessage', { chat_id: to, text: String(text).slice(0, 3900), disable_web_page_preview: true }); return !!(r && r.ok); } catch (e) { return false; }
}

function autoCreate_(j) {
  var b = ScriptApp.newTrigger(j.fn).timeBased();
  if (j.kind === 'day') b.everyDays(1).atHour(j.hour).inTimezone(TRIGGER_TZ).create();
  else if (j.kind === 'hours') b.everyHours(j.every).create();
  else if (j.kind === 'minutes') b.everyMinutes(j.every).create();
  else if (j.kind === 'week') b.onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(j.hour).inTimezone(TRIGGER_TZ).create();
  else if (j.kind === 'month') b.onMonthDay(1).atHour(j.hour).inTimezone(TRIGGER_TZ).create();
}

/** Поставить недостающие запуски (reset — снять все наши и поставить заново). Возвращает {added, total}. */
/* Запуски, которые нужны не всегда: лайв новостного канала держим включённым, только пока он подключён,
 * иначе минутный триггер зря жёг бы дневной лимит времени скриптов. */
var AUTO_WHEN_ = { newsLiveOn_: function () { return newsLiveOn_(); }, newsFeedOn_: function () { return newsFeedOn_(); } };
function autoJobOn_(j) {
  if (!j.when) return true;
  try { return !!(AUTO_WHEN_[j.when] && AUTO_WHEN_[j.when]()); } catch (e) { return false; }
}
function ensureAutomation_(reset) {
  var have = {}, mine = {}, off = {};
  AUTO_JOBS.forEach(function (j) { mine[j.fn] = true; if (!autoJobOn_(j)) off[j.fn] = true; });
  ScriptApp.getProjectTriggers().forEach(function (t) {
    var h = t.getHandlerFunction();
    if (h === 'updateResultsFromWeb' || off[h] || (reset && mine[h])) { ScriptApp.deleteTrigger(t); return; }
    if (have[h]) { ScriptApp.deleteTrigger(t); return; }                 // дубль
    have[h] = true;
  });
  var added = 0, jobs = AUTO_JOBS.filter(autoJobOn_);
  jobs.forEach(function (j) { if (!have[j.fn]) { autoCreate_(j); added++; } });
  return { added: added, total: jobs.length };
}

function autoSchedText_(j) {
  var msk = function (h) { return ((h - 4 + 24) % 24) + ':00 МСК'; };
  if (j.kind === 'day') return 'каждый день в ' + j.hour + ':00 по Красноярску (' + msk(j.hour) + ')';
  if (j.kind === 'hours') return 'каждые ' + j.every + ' ч';
  if (j.kind === 'minutes') return 'каждые ' + j.every + ' мин';
  if (j.kind === 'week') return 'по понедельникам в ' + j.hour + ':00 по Красноярску';
  return '1-го числа в ' + j.hour + ':00 по Красноярску';
}

/** Лист «Автоматика»: что и когда запускается, когда был последний запуск и чем закончился. */
function autoRender_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var st = {}; try { st = JSON.parse(PropertiesService.getScriptProperties().getProperty('AUTO_STATUS') || '{}'); } catch (e) { st = {}; }
  var have = {}; try { ScriptApp.getProjectTriggers().forEach(function (t) { have[t.getHandlerFunction()] = true; }); } catch (e) { have = null; }
  var rows = AUTO_JOBS.map(function (j) {
    var s = st[j.fn];
    var state = !autoJobOn_(j) ? '— не подключено' : have === null ? '?' : have[j.fn] ? '✅ включено' : '❌ нет';
    return [j.what, autoSchedText_(j), state, s ? s.t : '—', s ? (s.ok ? '✓ ' : '⚠ ') + s.msg : ''];
  });
  var sh = ss.getSheetByName(AUTO_SHEET) || ss.insertSheet(AUTO_SHEET);
  sh.clear();
  sh.getRange(1, 1).setValue('Автоматика: что таблица делает сама').setFontWeight('bold').setFontSize(13);
  sh.getRange(2, 1).setValue('Время последнего запуска — по МСК. Если в «Статус» стоит ❌ — меню «НХЛ-парсер» → Настройки → «Включить всю автоматику».');
  var head = ['Что делает', 'Когда', 'Статус', 'Последний запуск', 'Результат'];
  sh.getRange(4, 1, 1, head.length).setValues([head]).setFontWeight('bold').setBackground('#1a4fd6').setFontColor('#ffffff');
  sh.getRange(5, 1, rows.length, head.length).setValues(rows).setWrap(true).setVerticalAlignment('top');
  try { sh.setColumnWidth(1, 420); sh.setColumnWidth(2, 230); sh.setColumnWidth(5, 260); } catch (e) {}
  return rows.length;
}

/** Меню: включить всю автоматику (снимает старые запуски и ставит все заново). */
function installAllAutomation_() {
  if (nhlNotReady_(false)) return;
  var r = ensureAutomation_(true);
  autoRender_();
  uiAlert_('Автоматика включена: ' + r.total + ' запусков.\n\n' + AUTO_JOBS.map(function (j) { return '• ' + autoSchedText_(j) + ' — ' + j.what; }).join('\n') +
    '\n\nСтатус и время последних запусков — на листе «' + AUTO_SHEET + '». Кнопками меню можно пользоваться и вручную.');
}


function autoStatusNow_() { var ss = SpreadsheetApp.getActive(); autoRender_(ss); try { ss.setActiveSheet(ss.getSheetByName(AUTO_SHEET)); } catch (e) {} }

/** Раз в месяц: самопроверка факторов модели (результат — на листе «Самопроверка»). */
function monthlyAuto_() {
  if (nhlNotReady_(true)) return;
  QUIET_ = true;
  try { selfCheckFactors_(); autoMark_('monthlyAuto_', true, 'самопроверка факторов выполнена'); }
  catch (e) { autoMark_('monthlyAuto_', false, e.message); }
  finally { QUIET_ = false; }
}

/* ─────────────── ЭТАП 4: выводы агента и их проверка по результатам ───────────────
 * Перед матчем агент записывает проверяемые выводы («у хозяев травмирован основной вратарь — минус»).
 * После матча скрипт сверяет их с исходом и сравнивает с моделью: если модель и так давала этой стороне 70%,
 * то «угадал в 70% случаев» — не заслуга новостей. Модель скрипт НЕ меняет: только показывает цифры. */
var SIGNAL_SHEET = 'Агент_выводы';
var SIGNAL_BOARD = 'Агент_проверка';
var SIGNAL_FACTORS = ['вратарь', 'травмы', 'возвращение', 'форма', 'усталость', 'тренер', 'мотивация', 'прочее'];
var SIGNAL_LEAN = 'итог по новостям';
var SIGNAL_HEADER = ['Дата матча', 'Хозяева', 'Гости', 'Команда', 'Фактор', 'Влияние', 'Сила', 'Вывод агента',
  'Шанс команды по модели (до матча)', 'Итог для команды', 'Вывод подтвердился?', 'Проверено (МСК)'];
var SIGNAL_MIN_N = 15;

function agentModelProb_(ss, dayKey, home, away) {
  var sh = ss.getSheetByName('прогнозы');
  if (!sh || sh.getLastRow() < 2) return null;
  var v = sh.getRange(2, 1, sh.getLastRow() - 1, 5).getValues();
  for (var i = 0; i < v.length; i++) {
    if (!(v[i][0] instanceof Date) || sheetDayKey_(v[i][0]) !== dayKey) continue;
    if (String(v[i][1]).trim() !== home || String(v[i][2]).trim() !== away) continue;
    var ph = Number(v[i][3]);
    if (isNaN(ph) || v[i][3] === '') return null;
    if (ph > 1) ph = ph / 100;
    return { home: ph, away: 1 - ph };
  }
  return null;
}

function signalSheet_(ss) {
  var sh = ss.getSheetByName(SIGNAL_SHEET);
  if (sh) return sh;
  sh = ss.insertSheet(SIGNAL_SHEET);
  sh.getRange(1, 1, 1, SIGNAL_HEADER.length).setValues([SIGNAL_HEADER]).setFontWeight('bold').setBackground('#1a4fd6').setFontColor('#ffffff');
  sh.setFrozenRows(1);
  try { [95, 120, 120, 120, 100, 70, 55, 380, 110, 95, 110, 120].forEach(function (w, i) { sh.setColumnWidth(i + 1, w); }); } catch (e) {}
  return sh;
}

function signalDay_(v) { return v instanceof Date ? sheetDayKey_(v) : String(v || ''); }
function signalDate_(dayKey) { var p = String(dayKey).split('-'); return sheetDate_(+p[0], +p[1], +p[2]); }
var SIGNAL_PLUS = 'в плюс', SIGNAL_MINUS = 'в минус';

function signalRows_(sh) {
  return sh.getLastRow() >= 2 ? sh.getRange(2, 1, sh.getLastRow() - 1, SIGNAL_HEADER.length).getValues() : [];
}
function signalWriteAll_(sh, rows) {
  if (sh.getLastRow() >= 2) sh.getRange(2, 1, sh.getLastRow() - 1, SIGNAL_HEADER.length).clearContent();
  if (rows.length) sh.getRange(2, 1, rows.length, SIGNAL_HEADER.length).setValues(rows).setWrap(true).setVerticalAlignment('top');
}

/** Записать выводы по матчу. Повторная сводка в тот же день заменяет непроверенные выводы по этому матчу. */
function agentSignalsSave_(ss, m, dayKey, j) {
  var pm = agentModelProb_(ss, dayKey, m.home, m.away);
  var side = function (x) { x = String(x || '').toLowerCase(); return x === 'home' || x === m.home.toLowerCase() ? 'home' : x === 'away' || x === m.away.toLowerCase() ? 'away' : ''; };
  var rows = [];
  (Array.isArray(j.signals) ? j.signals : []).slice(0, 9).forEach(function (sg) {
    if (!sg || typeof sg !== 'object') return;
    var sd = side(sg.team), eff = String(sg.effect || '').replace('−', '-').trim();
    if (!sd || (eff !== '+' && eff !== '-') || !String(sg.text || '').trim()) return;
    var f = String(sg.factor || '').toLowerCase().trim(); if (SIGNAL_FACTORS.indexOf(f) === -1) f = 'прочее';
    var st = Math.max(1, Math.min(3, Math.round(Number(sg.strength) || 1)));
    var team = sd === 'home' ? m.home : m.away;
    rows.push([signalDate_(dayKey), m.home, m.away, team, f, eff === '+' ? SIGNAL_PLUS : SIGNAL_MINUS, st, String(sg.text).replace(/\s+/g, ' ').trim().slice(0, 300), pm ? Math.round(pm[sd] * 1000) / 1000 : '', '', '', '']);
  });
  var lean = side(j.lean), leanText = '';
  if (lean) {
    var lt = lean === 'home' ? m.home : m.away;
    rows.push([signalDate_(dayKey), m.home, m.away, lt, SIGNAL_LEAN, SIGNAL_PLUS, 2, 'По новостям перевес у «' + lt + '»', pm ? Math.round(pm[lean] * 1000) / 1000 : '', '', '', '']);
    leanText = 'По новостям перевес у «' + lt + '»' + (pm ? ' · модель даёт ей ' + Math.round(pm[lean] * 100) + '%' : '');
  }
  var sh = signalSheet_(ss);
  var keep = signalRows_(sh).filter(function (r) { return !(signalDay_(r[0]) === dayKey && r[1] === m.home && r[2] === m.away && !r[11]); });
  signalWriteAll_(sh, keep.concat(rows));
  return { n: rows.length, lean: lean, leanText: leanText };
}

/** Сверка непроверенных выводов с результатами + табло. {checked, hits} */
function agentSignalsReview_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(SIGNAL_SHEET);
  if (!sh || sh.getLastRow() < 2) return { checked: 0, hits: 0 };
  var res = {}, rs = ss.getSheetByName(SHEET_RESULTS);
  if (rs && rs.getLastRow() >= 2) rs.getRange(2, 1, rs.getLastRow() - 1, 8).getValues().forEach(function (r) {
    if (!(r[0] instanceof Date) || String(r[1]).trim() !== 'Сыгран' || r[4] === '' || r[5] === '') return;
    var gh = Number(r[4]), ga = Number(r[5]); if (isNaN(gh) || isNaN(ga) || gh === ga) return;
    res[sheetDayKey_(r[0]) + '|' + String(r[2]).trim() + '|' + String(r[3]).trim()] = gh > ga ? String(r[2]).trim() : String(r[3]).trim();
  });
  var rows = signalRows_(sh), checked = 0, hits = 0, now = mskNow_();
  rows.forEach(function (r) {
    if (r[11]) return;
    var day = signalDay_(r[0]);
    var w = res[day + '|' + r[1] + '|' + r[2]];
    if (!w) return;
    var won = w === r[3], hit = (r[5] === SIGNAL_PLUS) === won;
    r[9] = won ? 'победа' : 'поражение'; r[10] = hit ? 'да' : 'нет'; r[11] = now;
    checked++; if (hit) hits++;
  });
  if (checked) signalWriteAll_(sh, rows);
  agentSignalsBoard_(ss, rows);
  return { checked: checked, hits: hits };
}

/** Табло: какие виды выводов реально добавляют точности сверх модели. */
function agentSignalsBoard_(ss, rows) {
  var groups = {}, order = SIGNAL_FACTORS.concat([SIGNAL_LEAN]);
  var add = function (k, r) {
    var g = groups[k] || (groups[k] = { n: 0, hits: 0, pn: 0, psum: 0 });
    g.n++; if (r[10] === 'да') g.hits++;
    var p = Number(r[8]);
    if (r[8] !== '' && !isNaN(p)) { g.pn++; g.psum += r[5] === SIGNAL_PLUS ? p : 1 - p; }   // шанс по модели того исхода, который «предсказал» вывод
  };
  rows.filter(function (r) { return r[10] === 'да' || r[10] === 'нет'; }).forEach(function (r) {
    add(r[4], r); if (r[4] !== SIGNAL_LEAN) add('все выводы', r);
  });
  var line = function (name, g) {
    if (!g) return [name, 0, '', '', '', '', 'пока нет проверенных'];
    var rate = g.hits / g.n, pm = g.pn ? g.psum / g.pn : null, diff = pm === null ? null : rate - pm;
    var verdict = g.n < SIGNAL_MIN_N ? 'мало данных (нужно от ' + SIGNAL_MIN_N + ')' : diff === null ? 'нет шанса модели' :
      diff >= 0.05 ? '✅ добавляет точности к модели' : diff <= -0.05 ? '❌ сбивает с толку' : '➖ модель это уже учитывает';
    return [name, g.n, g.hits, Math.round(rate * 100) + '%', pm === null ? '—' : Math.round(pm * 100) + '%',
      diff === null ? '—' : Math.round(Math.abs(diff) * 100) === 0 ? 'как модель' : 'на ' + Math.round(Math.abs(diff) * 100) + ' п.п. ' + (diff > 0 ? 'выше' : 'ниже'), verdict];
  };
  var body = [line('все выводы', groups['все выводы'])].concat(order.map(function (k) { return line(k, groups[k]); }));
  var sh = ss.getSheetByName(SIGNAL_BOARD) || ss.insertSheet(SIGNAL_BOARD);
  sh.clear();
  sh.getRange(1, 1).setValue('Проверка выводов агента').setFontWeight('bold').setFontSize(14);
  sh.getRange(2, 1).setValue('Выводы агента перед матчами сверяются с результатами. «Модель ждала» — сколько в среднем давала модель тому исходу, на который указывал вывод. ' +
    'Если выводы сбываются чаще, чем ждала модель, — новости добавляют точности. Модель скрипт сам не меняет.');
  var head = ['Вид вывода', 'Проверено', 'Сбылось', 'Точность', 'Модель ждала', 'Разница', 'Вердикт'];
  sh.getRange(4, 1, 1, head.length).setValues([head]).setFontWeight('bold').setBackground('#1a4fd6').setFontColor('#ffffff');
  sh.getRange(5, 1, body.length, head.length).setValues(body);
  sh.getRange(5, 1, 1, head.length).setFontWeight('bold');
  try { sh.setColumnWidth(1, 170); sh.setColumnWidth(7, 280); } catch (e) {}
  return body;
}

function agentSignalsReviewNow_() {
  var r = agentSignalsReview_(SpreadsheetApp.getActive());
  uiAlert_('Проверено новых выводов: ' + r.checked + (r.checked ? ', подтвердилось: ' + r.hits : '') + '.\nИтоги по видам выводов — на листе «' + SIGNAL_BOARD + '».');
}

/* ---------------------------- досье на команды ---------------------------- */
var DOSSIER_SHEET = 'Досье_команд';
var DOSSIER_LOG = 'Досье_история';
var DOSSIER_FIELDS = [['injuries', 'Травмы и отсутствия'], ['goalies', 'Вратари'], ['coach_roster', 'Тренер и состав'],
  ['form', 'Форма и серии'], ['other', 'Прочее важное']];
var DOSSIER_HEADER = ['Команда'].concat(DOSSIER_FIELDS.map(function (f) { return f[1]; }), ['Обновлено (МСК)', 'Источники последнего обновления']);

function dossierSheet_(ss) {
  var sh = ss.getSheetByName(DOSSIER_SHEET);
  if (sh) {
    dossierFillTeamNames_(ss, sh);                                        // лист есть: дописать команды, которых на нём нет
    return sh;
  }
  sh = ss.insertSheet(DOSSIER_SHEET);
  sh.getRange(1, 1, 1, DOSSIER_HEADER.length).setValues([DOSSIER_HEADER]).setFontWeight('bold').setBackground('#1a4fd6').setFontColor('#ffffff');
  sh.setFrozenRows(1); sh.setFrozenColumns(1);
  [170, 300, 240, 260, 260, 260, 130, 300].forEach(function (w, i) { sh.setColumnWidth(i + 1, w); });
  dossierFillTeamNames_(ss, sh);
  return sh;
}

/** Команды на лист досье: из справочника (а если его нет — из Elo). Уже записанные не трогает, недостающие дописывает. */
function dossierFillTeamNames_(ss, sh) {
  var teams = [], src = [ss.getSheetByName(SHEET_TEAMS), ss.getSheetByName(SHEET_ELO)];
  for (var k = 0; k < src.length && !teams.length; k++) {
    var x = src[k];
    if (x && x.getLastRow() >= 2) teams = x.getRange(2, 1, x.getLastRow() - 1, 1).getValues().map(function (r) { return String(r[0]).trim(); })
      .filter(function (t) { return t && !/^Команда/.test(t); });
  }
  if (sh.getLastRow() < 1) sh.getRange(1, 1, 1, DOSSIER_HEADER.length).setValues([DOSSIER_HEADER]).setFontWeight('bold');
  var have = {};
  if (sh.getLastRow() >= 2) sh.getRange(2, 1, sh.getLastRow() - 1, 1).getValues().forEach(function (r) { have[String(r[0]).trim()] = true; });
  var add = teams.filter(function (t) { return !have[t]; }).sort();
  if (add.length) sh.getRange(sh.getLastRow() + 1, 1, add.length, 1).setValues(add.map(function (t) { return [t]; }));
  return add.length;
}

/** {команда: {injuries, goalies, coach_roster, form, other, updated}} */
function dossierRead_(ss) {
  var sh = dossierSheet_(ss), out = {};
  if (sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, DOSSIER_HEADER.length).getValues().forEach(function (r) {
    var t = String(r[0]).trim(); if (!t) return;
    var d = {}; DOSSIER_FIELDS.forEach(function (f, i) { d[f[0]] = String(r[i + 1] || ''); });
    d.updated = r[DOSSIER_FIELDS.length + 1] instanceof Date ? Utilities.formatDate(r[DOSSIER_FIELDS.length + 1], 'Europe/Moscow', 'dd.MM.yyyy') : String(r[DOSSIER_FIELDS.length + 1] || '');
    out[t] = d;
  });
  return out;
}

function dossierWrite_(ss, team, upd, srcText) {
  var sh = dossierSheet_(ss);
  var names = sh.getLastRow() >= 2 ? sh.getRange(2, 1, sh.getLastRow() - 1, 1).getValues().map(function (r) { return String(r[0]).trim(); }) : [];
  var idx = names.indexOf(team), row = idx === -1 ? sh.getLastRow() + 1 : idx + 2;
  var prev = dossierRead_(ss)[team] || {};
  var vals = [team].concat(DOSSIER_FIELDS.map(function (f) {
      var v = String(upd[f[0]] || '').replace(/\s+/g, ' ').trim();
      if (!v || /^нет данных\.?$/i.test(v)) v = prev[f[0]] && !/^нет данных/i.test(prev[f[0]]) ? prev[f[0]] : 'нет данных';   // не стираем известное пустотой
      return v.slice(0, 450);
    }),
    [mskNow_(), srcText || '']);
  sh.getRange(row, 1, 1, vals.length).setValues([vals]).setWrap(true).setVerticalAlignment('top');
  // история: что знал агент и когда — пригодится, чтобы потом проверять его выводы
  var lg = ss.getSheetByName(DOSSIER_LOG);
  if (!lg) {
    lg = ss.insertSheet(DOSSIER_LOG);
    lg.getRange(1, 1, 1, DOSSIER_HEADER.length).setValues([DOSSIER_HEADER]).setFontWeight('bold');
    try { lg.hideSheet(); } catch (e) { /* тесты */ }
  }
  lg.getRange(lg.getLastRow() + 1, 1, 1, vals.length).setValues([vals]);
}

/** Из меню: заполнить досье всех команд разом (один поиск на команду, ~2 кредита). */
/** Очистить досье (история остаётся на скрытом листе) и собрать заново — после смены правил отбора статей. */
function dossierRebuild_() {
  var ui = null; try { ui = SpreadsheetApp.getUi(); } catch (e) { ui = null; }
  if (ui) {
    var r = ui.alert('Пересобрать досье с нуля?', 'Все ячейки досье очистятся и соберутся заново по новым правилам отбора статей. ' +
      'История сохранится на скрытом листе «' + DOSSIER_LOG + '». Новости берутся бесплатно с sports.ru; платный поиск — только для команд, где там мало новостей.', ui.ButtonSet.YES_NO);
    if (r !== ui.Button.YES) return;
  }
  var ss = SpreadsheetApp.getActive(), sh = dossierSheet_(ss);
  if (sh.getLastRow() >= 2) sh.getRange(2, 2, sh.getLastRow() - 1, DOSSIER_HEADER.length - 1).clearContent();
  agentProps_().deleteProperty('DOSSIER_PASS');
  dossierFillAll_();
}

/** Сколько полей досье пустые или «нет данных» — такие команды обновляем первыми. */
function dossierGaps_(d) {
  return DOSSIER_FIELDS.filter(function (f) { var v = String(d[f[0]] || '').trim(); return !v || /^нет данных/i.test(v); }).length;
}

/* ── Бесплатный источник: страницы новостей клубов на sports.ru (кредиты поиска не тратятся) ── */
var SPORTS_UA = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36' };
var RU_MONTHS_GEN = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
var DOSSIER_FRESH_DAYS = 21;

function sportsText_(s) {
  return String(s || '').replace(/<[^>]+>/g, ' ').replace(/&nbsp;|&#160;/g, ' ').replace(/&quot;|&#34;/g, '"').replace(/&laquo;/g, '«')
    .replace(/&raquo;/g, '»').replace(/&mdash;/g, '—').replace(/&ndash;/g, '–').replace(/&#(\d+);/g, function (_, n) { return String.fromCharCode(+n); })
    .replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
}

/** Ссылки на клубы со страницы таблицы: [{slug, name}] */
function sportsParseClubLinks_(html) {
  var re = /href=["'](?:https?:\/\/www\.sports\.ru)?\/hockey\/club\/([a-z0-9-]+)\/?["'][^>]*>([\s\S]{0,400}?)<\/a>/g, m, out = [], seen = {};
  while ((m = re.exec(html))) {
    var name = sportsText_(m[2]);
    if (!name || seen[m[1]]) continue;
    seen[m[1]] = true; out.push({ slug: m[1], name: name });
  }
  return out;
}

/** Адреса клубов на sports.ru: берём со страницы таблицы КХЛ (раз в неделю), недостающие — из запасного списка. */
function sportsClubSlugs_(force) {
  var p = agentProps_(), c = null;
  try { c = JSON.parse(p.getProperty('SPORTS_CLUB_SLUGS_V2') || 'null'); } catch (e) { c = null; }
  if (!force && c && c.map && Date.now() - c.ts < 7 * 86400000) return c.map;
  var map = {}; Object.keys(SPORTS_CLUB_SLUGS).forEach(function (t) { map[t] = SPORTS_CLUB_SLUGS[t]; });
  try {
    var r = UrlFetchApp.fetch('https://www.sports.ru/hockey/tournament/nhl/table/', { muteHttpExceptions: true, headers: SPORTS_UA });
    if (r.getResponseCode() === 200) {
      var found = sportsParseClubLinks_(r.getContentText());
      Object.keys(map).forEach(function (team) {
        for (var i = 0; i < found.length; i++) if (agentMentions_(found[i].name, team)) { map[team] = found[i].slug; break; }
      });
    }
  } catch (e) { /* остаётся запасной список */ }
  p.setProperty('SPORTS_CLUB_SLUGS_V2', JSON.stringify({ ts: Date.now(), map: map }));
  return map;
}

/** Новости со страницы клуба: [{id, url, title, date|null}] в порядке страницы (сверху — свежие).
 *  Дата — последняя встреченная выше по странице («24 сентября» или datetime="2026-09-24"). */
function sportsParseNews_(html, now) {
  now = now || new Date();
  var mk = Utilities.formatDate(now, 'Europe/Moscow', 'yyyy-MM-dd').split('-');   // «Сегодня» на sports.ru — по Москве
  var today = new Date(+mk[0], +mk[1] - 1, +mk[2], 12);                          // полдень: дата не съезжает при показе по Москве
  var re = new RegExp(
    '(?:datetime="|"(?:published|publishedAt|published_at|datePublished|pubDate)"\\s*:\\s*")(\\d{4})-(\\d\\d)-(\\d\\d)' +        // 1-3: ISO-дата
    '|(\\d{1,2})\\s+(' + RU_MONTHS_GEN.join('|') + ')(?:\\s+(20\\d\\d))?' +                                                      // 4-6: «24 сентября»
    '|>\\s*(Сегодня|Вчера)\\s*[<,]' +                                                                                             // 7
    '|href="((?:https?://www\\.sports\\.ru)?/hockey/(\\d{9,11})-[a-z0-9-]+\\.html)"([^>]*)>([\\s\\S]{0,800}?)</a>' +             // 8-11: новость
    '|"(?:url|link|href)"\\s*:\\s*"((?:https?:)?(?:\\\\?/\\\\?/www\\.sports\\.ru)?\\\\?/hockey\\\\?/(\\d{9,11})-[a-z0-9-]+\\.html)"[^{}]{0,400}?"title"\\s*:\\s*"((?:[^"\\\\]|\\\\.){15,300})"', // 12-14: JSON
    'g');
  var m, cur = null, out = [], byId = {};
  var add = function (id, url, title) {
    title = sportsText_(title);
    if (title.length < 15) return;
    url = url.replace(/\\\//g, '/'); if (url.indexOf('//') === 0) url = 'https:' + url; if (url.indexOf('http') !== 0) url = 'https://www.sports.ru' + url;
    if (byId[id]) { if (title.length > byId[id].title.length) byId[id].title = title; if (!byId[id].date && cur) byId[id].date = cur; return; }
    byId[id] = { id: id, url: url, title: title, date: cur }; out.push(byId[id]);
  };
  while ((m = re.exec(html))) {
    if (m[1]) { cur = new Date(+m[1], +m[2] - 1, +m[3], 12); continue; }
    if (m[4]) {
      var y = m[6] ? +m[6] : now.getFullYear(), d = new Date(y, RU_MONTHS_GEN.indexOf(m[5]), +m[4], 12);
      if (!m[6] && d.getTime() - now.getTime() > 2 * 86400000) d.setFullYear(y - 1);
      cur = d; continue;
    }
    if (m[7]) { cur = m[7] === 'Сегодня' ? today : new Date(today.getTime() - 86400000); continue; }
    if (m[8]) {
      var text = m[11], ta = String(m[10] || '').match(/title="([^"]{15,})"/);
      if (sportsText_(text).length < 15 && ta) text = ta[1];
      add(m[9], m[8], text); continue;
    }
    if (m[12]) {
      var t = m[14]; try { t = JSON.parse('"' + t + '"'); } catch (e) {}
      var a0 = html.lastIndexOf('{', m.index), b0 = html.indexOf('}', re.lastIndex);        // дата публикации — внутри того же объекта
      var dm = html.slice(a0 < 0 ? m.index : a0, b0 < 0 ? re.lastIndex : b0).match(/"(?:published|publishedAt|published_at|datePublished|pubDate|date)"\s*:\s*"(\d{4})-(\d\d)-(\d\d)/);
      if (dm) cur = new Date(+dm[1], +dm[2] - 1, +dm[3], 12);
      add(m[13], m[12], t);
    }
  }
  return out;
}

/** Отбор: свежие (≤ 3 недель), сначала где упомянута команда, потом остальные новости страницы клуба; всего до 20. */
function sportsNewsFromHtml_(html, team, now) {
  now = now || new Date();
  var fresh = sportsParseNews_(html, now).filter(function (n) { return !n.date || (now.getTime() - n.date.getTime()) / 86400000 <= DOSSIER_FRESH_DAYS; });
  var mine = fresh.filter(function (n) { return agentMentions_(n.title, team); });
  var other = fresh.filter(function (n) { return !agentMentions_(n.title, team); });
  // на странице клуба почти всё — про клуб, даже без названия в заголовке («Динамо» без «Москвы»); сначала — где команда названа
  var out = mine.concat(other).slice(0, 20);
  out.mine = Math.min(mine.length, 20);
  return out;
}

function sportsClubNewsUrl_(slug) { return 'https://www.sports.ru/hockey/club/' + slug + '/news/'; }

/** Страница не найдена (404) — запасные адреса: короткий адрес клуба; в НХЛ — ещё адрес без /hockey/club/ (sports.ru/utah-mammoth/). */
function sportsClubNewsRetry_(slug, r) {
  var alt = [];
  if (slug.indexOf('-') > 0) alt.push(sportsClubNewsUrl_(slug.split('-')[0]));
  if (SPORTS_TOPLEVEL_FALLBACK) alt.push('https://www.sports.ru/' + slug + '/news/');
  for (var i = 0; i < alt.length && r.getResponseCode() === 404; i++) { r = UrlFetchApp.fetch(alt[i], { muteHttpExceptions: true, headers: SPORTS_UA }); r.url_ = alt[i]; }
  return r;
}

function sportsClubNews_(team, slugs) {
  var slug = (slugs || sportsClubSlugs_())[team];
  if (!slug) throw new Error('нет адреса клуба на sports.ru');
  var r = sportsClubNewsRetry_(slug, UrlFetchApp.fetch(sportsClubNewsUrl_(slug), { muteHttpExceptions: true, headers: SPORTS_UA }));
  if (r.getResponseCode() !== 200) throw new Error('sports.ru ответил кодом ' + r.getResponseCode());
  return sportsNewsFromHtml_(r.getContentText(), team);
}

function sportsNewsLine_(n, i) {
  return '[S' + (i + 1) + '] ' + (n.date ? Utilities.formatDate(n.date, 'Europe/Moscow', 'dd.MM') + ' — ' : '') + String(n.title).slice(0, 700);
}

/* ── Каналы экспертов и инсайдеров в Telegram: читаем открытую веб-версию t.me/s/<канал> (бесплатно) ── */
var EXPERT_SHEET = 'Каналы_экспертов';
var EXPERT_FRESH_DAYS = 7;
/* Официальные Telegram-каналы клубов: перед игрой там состав и вратарь. Пост клубного канала относится к его команде,
 * даже если название в тексте не упомянуто. Дописываются в лист один раз; удалённые вами не возвращаются. */
function expertClubTeam_(channel) {
  var c = String(channel || '').toLowerCase();
  for (var i = 0; i < EXPERT_CLUBS.length; i++) if (EXPERT_CLUBS[i][0].toLowerCase() === c) return EXPERT_CLUBS[i][1];
  return '';
}
/** Один раз: дописать каналы клубов, которых ещё нет на листе. */
function expertClubsAdd_(sh) {
  var p = PropertiesService.getScriptProperties();
  if (!EXPERT_CLUBS.length || p.getProperty('EXPERT_CLUBS_ADDED')) return 0;
  var have = {};
  if (sh.getLastRow() >= 2) sh.getRange(2, 1, sh.getLastRow() - 1, 1).getValues().forEach(function (r) {
    have[String(r[0]).trim().replace(/^@|^(https?:\/\/)?(www\.)?(t|telegram)\.me\/(s\/)?/ig, '').replace(/[\/?].*$/, '').toLowerCase()] = true; });
  var add = EXPERT_CLUBS.filter(function (c) { return !have[c[0].toLowerCase()]; }).map(function (c) { return [c[0], 'ХК «' + c[1] + '» — официальный канал']; });
  if (add.length) sh.getRange(sh.getLastRow() + 1, 1, add.length, 2).setValues(add);
  p.setProperty('EXPERT_CLUBS_ADDED', mskNow_('dd.MM.yyyy'));
  return add.length;
}

/** Список каналов с листа (можно дописывать свои: в колонку A — имя канала без @). */
function expertChannels_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(EXPERT_SHEET);
  if (!sh) {
    sh = ss.insertSheet(EXPERT_SHEET);
    sh.getRange(1, 1, 1, 4).setValues([['Канал (без @)', 'Кто это', 'Постов за неделю', 'Последняя проверка']]).setFontWeight('bold');
    sh.getRange(2, 1, EXPERT_DEFAULT.length, 2).setValues(EXPERT_DEFAULT);
    try { sh.setColumnWidth(1, 170); sh.setColumnWidth(2, 260); } catch (e) {}
  }
  try { expertClubsAdd_(sh); } catch (e) { /* не критично */ }
  if (sh.getLastRow() < 2) return [];
  return sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues().map(function (r, i) {
    return { name: String(r[0]).trim().replace(/^@|^(https?:\/\/)?(www\.)?(t|telegram)\.me\/(s\/)?/ig, '').replace(/[\/?].*$/, ''), who: String(r[1] || '').trim(), row: i + 2 };
  }).filter(function (c) { return /^[A-Za-z0-9_]{4,}$/.test(c.name); });
}

/** Посты со страницы t.me/s/<канал>: [{url, text, date}] */
function tgParseChannel_(html, channel) {
  var out = [], parts = String(html || '').split('data-post="');
  for (var i = 1; i < parts.length; i++) {
    var ch = parts[i], id = ch.slice(0, ch.indexOf('"'));
    var text = '', a = -1;
    while ((a = ch.indexOf('tgme_widget_message_text', a + 1)) !== -1) {      // бывает цитата ответа — берём самый длинный текст поста
      var st = ch.indexOf('>', a) + 1, b = ch.indexOf('</div>', st);
      var t = sportsText_(ch.slice(st, b === -1 ? st + 4000 : b).replace(/<br\s*\/?>/gi, ' \n '));
      if (t.length > text.length) text = t;
    }
    if (text.length < 20) continue;
    var dm = ch.match(/<time[^>]*datetime="([^"]+)"/);
    var d = dm ? new Date(dm[1]) : null;
    out.push({ url: 'https://t.me/' + id, channel: channel, text: text.slice(0, 1200), date: d && !isNaN(d.getTime()) ? d : null });
  }
  return out;
}

/** Свежие посты всех каналов (одна загрузка на канал, параллельно). Лист каналов отмечает, сколько постов нашлось. */
var EXPERT_POSTS_RUN_ = null;                         // один запуск — одна загрузка каналов (сводка читает их для каждого матча)
function expertPostsAll_(ss) {
  if (EXPERT_POSTS_RUN_ && Date.now() - EXPERT_POSTS_RUN_.t < 10 * 60 * 1000) return EXPERT_POSTS_RUN_.posts.slice();
  var res = expertPostsLoad_(ss);
  EXPERT_POSTS_RUN_ = { t: Date.now(), posts: res };
  return res.slice();
}
function expertPostsLoad_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var chans = expertChannels_(ss), now = Date.now(), all = [];
  if (!chans.length) return all;
  var resps = [];
  try { resps = UrlFetchApp.fetchAll(chans.map(function (c) { return { url: 'https://t.me/s/' + c.name, muteHttpExceptions: true, headers: SPORTS_UA }; })); } catch (e) { resps = []; }
  var sh = ss.getSheetByName(EXPERT_SHEET);
  chans.forEach(function (c, i) {
    var posts = [];
    try { if (resps[i] && resps[i].getResponseCode() === 200) posts = tgParseChannel_(resps[i].getContentText(), c.name); } catch (e) { posts = []; }
    posts = posts.filter(function (p) { return !p.date || (now - p.date.getTime()) / 86400000 <= EXPERT_FRESH_DAYS; });
    posts.forEach(function (p) { p.who = c.who || c.name; });
    all = all.concat(posts);
    try { sh.getRange(c.row, 3, 1, 2).setValues([[resps[i] ? (resps[i].getResponseCode() === 200 ? posts.length : 'ошибка ' + resps[i].getResponseCode()) : 'нет ответа', mskNow_()]]); } catch (e) {}
  });
  all.sort(function (x, y) { return (y.date ? y.date.getTime() : 0) - (x.date ? x.date.getTime() : 0); });
  return all;
}

/** Посты, где упомянута команда (свежие сверху), в виде «новостей» для ИИ. */
function expertPostsAbout_(posts, team, limit) {
  return (posts || []).filter(function (p) { return agentMentions_(p.text, team) || expertClubTeam_(p.channel) === team; }).slice(0, limit || 6).map(function (p) {
    return { url: p.url, title: 'Telegram «' + p.who + '»: ' + p.text, date: p.date, tg: true };
  });
}

/** Бесплатная проверка: откуда и сколько новостей найдётся по каждой команде. Кредиты поиска и ИИ не тратятся. */
var NEWS_DIAG_SHEET = 'Диагностика_новостей';
function dossierCheckNews_() {
  var ss = SpreadsheetApp.getActive(), slugs = sportsClubSlugs_(true), teams = Object.keys(SPORTS_CLUB_SLUGS), rows = [], okN = 0, now = new Date();
  var resps = UrlFetchApp.fetchAll(teams.map(function (t) { return { url: sportsClubNewsUrl_(slugs[t]), muteHttpExceptions: true, headers: SPORTS_UA }; }));
  teams.forEach(function (t, i) {
    var r = resps[i];
    if (r.getResponseCode() === 404) r = sportsClubNewsRetry_(slugs[t], r);          // те же запасные адреса, что при сборе досье
    var code = r.getResponseCode(), news = code === 200 ? sportsNewsFromHtml_(r.getContentText(), t, now) : [];
    if (news.length) okN++;
    rows.push([t, r.url_ || sportsClubNewsUrl_(slugs[t]), code, news.mine || 0, news.length,
      news.slice(0, 4).map(sportsNewsLine_).join('\n') || '—']);
  });
  var sh = ss.getSheetByName(NEWS_DIAG_SHEET) || ss.insertSheet(NEWS_DIAG_SHEET);
  sh.clear();
  var head = ['Команда', 'Страница новостей', 'Ответ', 'Новостей про команду', 'Всего взято', 'Первые новости'];
  sh.getRange(1, 1, 1, head.length).setValues([head]).setFontWeight('bold');
  sh.getRange(2, 1, rows.length, head.length).setValues(rows).setWrap(true).setVerticalAlignment('top');
  try { sh.setColumnWidth(2, 260); sh.setColumnWidth(6, 520); } catch (e) {}
  var posts = [], chans = [];
  try { chans = expertChannels_(ss); posts = expertPostsAll_(ss); } catch (e) { posts = []; }
  var byCh = {}; posts.forEach(function (p) { byCh[p.channel] = (byCh[p.channel] || 0) + 1; });
  var tgLine = chans.length ? '\nTelegram-каналы: ' + chans.map(function (c) { return '@' + c.name + ' — ' + (byCh[c.name] || 0); }).join(', ') + ' постов за неделю.' : '';
  uiAlert_('Новости sports.ru найдены у ' + okN + ' из ' + teams.length + ' команд.' + tgLine +
    (okN < teams.length ? '\nБез новостей: ' + rows.filter(function (r) { return !r[4]; }).map(function (r) { return r[0] + ' (код ' + r[2] + ')'; }).join(', ') : '') +
    '\n\nПодробно — лист «' + NEWS_DIAG_SHEET + '». Кредиты поиска и ИИ не тратились.');
  return { ok: okN, total: teams.length };
}

/** Форма из наших же результатов — всегда есть и всегда точная. */
function dossierFormText_(ss, team) {
  var sh = ss.getSheetByName(SHEET_RESULTS);
  if (!sh || sh.getLastRow() < 2) return '';
  var rows = sh.getRange(2, 1, sh.getLastRow() - 1, 7).getValues().filter(function (r) {
    return String(r[1]).trim() === 'Сыгран' && r[0] instanceof Date && (String(r[2]).trim() === team || String(r[3]).trim() === team) &&
      r[4] !== '' && r[5] !== '' && !isNaN(Number(r[4])) && !isNaN(Number(r[5]));
  });
  if (!rows.length) return '';
  rows.sort(function (a, b) { return b[0].getTime() - a[0].getTime(); });
  var res = rows.map(function (r) {
    var home = String(r[2]).trim() === team, gf = Number(home ? r[4] : r[5]), ga = Number(home ? r[5] : r[4]);
    var ot = r[6] === true || /^(да|true|от|б|ot|so)/i.test(String(r[6]).trim());
    var k = sheetDayKey_(r[0]).split('-');
    return { w: gf > ga, s: (gf > ga ? 'В' : 'П') + (ot ? ' ОТ' : '') + ' ' + gf + ':' + ga + (home ? ' дома с ' : ' в гостях у ') + String(home ? r[3] : r[2]).trim() + ' (' + k[2] + '.' + k[1] + ')' };
  });
  var streak = 1; while (streak < res.length && res[streak].w === res[0].w) streak++;
  var place = '';
  var tb = ss.getSheetByName('Таблица');
  if (tb && tb.getLastRow() >= 2) tb.getRange(2, 1, tb.getLastRow() - 1, 4).getValues().forEach(function (r) {
    if (String(r[1]).trim() === team && r[0] !== '') place = Number(r[0]) + '-е место в общей таблице, ' + r[2] + ' матчей, ' + r[3] + ' очков. ';
  });
  return place + 'Последние ' + Math.min(5, res.length) + ': ' + res.slice(0, 5).map(function (x) { return x.s; }).join('; ') +
    '. ' + (streak === 1 ? 'Последний матч — ' + (res[0].w ? 'победа' : 'поражение') :
      'Серия: ' + streak + ' ' + (res[0].w ? (streak < 5 ? 'победы' : 'побед') : (streak < 5 ? 'поражения' : 'поражений')) + ' подряд') + ' [таблица]';
}

function dossierPrompt_(team, old, news, docs, today) {
  return 'Ты — аналитик хоккейного канала. Сегодня ' + today + '. Составь досье на команду НХЛ «' + team + '» по новостям ниже и старому досье.\n\n' +
    'ПРАВИЛА:\n' +
    '1. Только то, что прямо сказано в новостях или старом досье. Ничего не придумывай и не добавляй по памяти.\n' +
    '2. Игрок относится к «' + team + '», только если это прямо сказано («вратарь «' + team + '» …», «у «' + team + '» травмирован …»). ' +
    'Фраза «X не сыграет с «' + team + '»» или «против «' + team + '»» значит, что X — игрок СОПЕРНИКА: в досье его не пиши.\n' +
    '3. Только НХЛ. Фарм-клубы (АХЛ), КХЛ, сборные и другие виды спорта игнорируй (отправка игрока в АХЛ или вызов из АХЛ — одной фразой в «Прочее»).\n' +
    '4. У травм и замен вратарей ставь дату новости в формате (с ДД.ММ). Убери то, что старше трёх недель или опровергнуто.\n' +
    '5. Если по пункту ничего нет — ровно «нет данных».\n' +
    '6. Пиши только то, что может повлиять на результат матчей: травмы, дисквалификации, кто в воротах, приходы и уходы, смена тренера, конфликты, переезды. ' +
    'Личную жизнь, интервью о жизни в городе, рекламу, статистику без выводов — не пиши.\n' +
    '7. «Вратари» — только кто стартует, кто травмирован или заменён, новые вратари. «Прочее» — одна-две важные вещи или «нет данных».\n' +
    '8. Посты из Telegram — это инсайдеры и журналисты: слухи помечай «по данным <канал>», факты — как есть.\n\n' +
    'СТАРОЕ ДОСЬЕ:\n' + DOSSIER_FIELDS.map(function (f) { return f[1] + ': ' + ((old && old[f[0]]) || 'пусто'); }).join('\n') + '\n\n' +
    (news.length ? 'НОВОСТИ (дата — заголовок; sports.ru и Telegram-каналы):\n' + news.map(sportsNewsLine_).join('\n') + '\n\n' : '') +
    (docs.length ? 'СТАТЬИ:\n' + docs.map(function (d, k) { return '[' + (k + 1) + '] ' + d.title + (d.date ? ' (' + d.date + ')' : '') + (/\/blogs\//.test(d.url) ? ' [блог болельщика]' : '') + '\n' + d.text; }).join('\n\n') + '\n\n' : '') +
    'Верни только JSON: {' + DOSSIER_FIELDS.map(function (f) { return '"' + f[0] + '":"' + f[1] + ', до 300 знаков или «нет данных»"'; }).join(',') + '}';
}

function agentJson_(text) {
  var t = String(text || ''), a = t.indexOf('{'), b = t.lastIndexOf('}');
  if (a === -1 || b <= a) throw new Error('ИИ вернул не JSON');
  return JSON.parse(t.slice(a, b + 1));
}

/** Проход по всем командам. Новости — бесплатно со страниц клубов sports.ru; платный поиск — только если там мало.
 *  Форма — из наших результатов, поэтому у каждой команды досье не пустое.
 *  Не успели за 4,5 мин — скрипт сам продолжит через минуту (ничего нажимать не надо), итог пришлёт в Telegram. */
function dossierFillAll_(auto, fresh) {
  auto = auto === true;
  var ss = SpreadsheetApp.getActive(), p = agentProps_();
  if (!p.getProperty('GEMINI_KEY')) { if (!auto) uiAlert_('Нужен ключ GEMINI_KEY.'); return; }
  dossierSheet_(ss);                                                     // сначала лист (и список команд), потом чтение
  var dossier = dossierRead_(ss), t0 = Date.now(), done = 0, errs = [], budgetOut = false;
  var all = Object.keys(dossier);
  var pass = null;
  try { pass = JSON.parse(p.getProperty('DOSSIER_PASS') || 'null'); } catch (e) { pass = null; }
  var complete = !pass || !pass.done || pass.done.length >= all.length || (Date.now() - (pass.started || 0)) > 12 * 3600000;
  if (complete) { if (auto && fresh !== true) return; pass = { started: Date.now(), done: [] }; }
  var teams = all.filter(function (t) { return pass.done.indexOf(t) === -1; }).sort(function (a, b) {
    var g = dossierGaps_(dossier[b]) - dossierGaps_(dossier[a]);
    return g || (String(dossier[a].updated) < String(dossier[b].updated) ? -1 : 1);
  });
  var slugs = {}; try { slugs = sportsClubSlugs_(); } catch (e) { slugs = SPORTS_CLUB_SLUGS; }
  var tgPosts = []; try { tgPosts = expertPostsAll_(ss); } catch (e) { tgPosts = []; }
  var today = mskNow_('dd.MM.yyyy');
  for (var i = 0; i < teams.length; i++) {
    if (Date.now() - t0 > 4.5 * 60000) break;                              // лимит Google — продолжим следующим запуском
    var team = teams[i], news = [], docs = [], notes = [], j = {};
    try { news = sportsClubNews_(team, slugs); } catch (e) { notes.push('sports.ru: ' + e.message); }
    var sportsN = news.length, tgAbout = expertPostsAbout_(tgPosts, team, 6);
    news = news.concat(tgAbout);
    try { news = news.concat(dossierExtraNews_(team) || []); } catch (e) { notes.push('доп. данные: ' + e.message); }
    if (news.length < 3 && !budgetOut && p.getProperty('TAVILY_KEY')) {
      try {
        docs = agentSearchAbout_(team + ' НХЛ хоккей травмы вратарь тренер новости', [team], team + ' НХЛ ' + (AGENT_TEAM_CITY[team] || '') + ' хоккей');
        var rn = agentRejectedNote_(docs); if (rn) notes.push(rn);
      } catch (e) { notes.push('поиск: ' + e.message); if (/лимит поиска/.test(e.message)) budgetOut = true; }
    }
    if (news.length || docs.length) {
      try { j = agentJson_(agentGemini_(dossierPrompt_(team, dossier[team], news, docs, today)).text); Utilities.sleep(1000); }
      catch (e) { errs.push(team + ': ' + e.message); j = {}; }
    }
    var form = ''; try { form = dossierFormText_(ss, team); } catch (e) { form = ''; }
    if (form) j.form = form;
    var src = [];
    if (sportsN) src.push(sportsClubNewsUrl_(slugs[team]) + ' — ' + sportsN + ' новостей');
    if (tgAbout.length) src.push('Telegram: ' + tgAbout.map(function (x) { return x.url; }).join(' '));
    docs.slice(0, 4).forEach(function (d, k) { src.push('[' + (k + 1) + '] ' + d.url); });
    if (!news.length && !docs.length) src.push('свежих новостей не нашлось');
    dossierWrite_(ss, team, j, src.join(' ') + (notes.length ? ' (' + notes.join('; ') + ')' : ''));
    done++; pass.done.push(team);
    p.setProperty('DOSSIER_PASS', JSON.stringify(pass));                  // прогресс сохраняется после каждой команды
  }
  var left = all.length - pass.done.length;
  var gaps = 0, after = dossierRead_(ss); all.forEach(function (t) { gaps += dossierGaps_(after[t] || {}); });
  var usage = {}; try { usage = agentTavilyBudget_(); } catch (e) { usage = {}; }
  var msg = 'Досье: обновлено ' + done + ' команд.' +
    (left ? ' Осталось ' + left + ' — продолжу сам через минуту, нажимать ничего не нужно.' : ' Готово по всем ' + all.length + ' командам.') +
    '\nЗаполнено ячеек: ' + (all.length * DOSSIER_FIELDS.length - gaps) + ' из ' + all.length * DOSSIER_FIELDS.length + ' (пусто = в свежих новостях этого нет).' +
    (errs.length ? '\nОшибки ИИ (форма всё равно записана): ' + errs.slice(0, 5).join('; ') : '') +
    '\nПоиск в этом месяце: ' + (usage.used || 0) + ' из ' + AGENT_TAVILY_MONTHLY_CAP + '.';
  if (left && done) dossierScheduleContinue_();
  if (!auto) uiAlert_(msg);
  else if (!left) { var to = p.getProperty('TG_ADMIN_ID'); if (to) try { tg_('sendMessage', { chat_id: to, text: '🧠 ' + msg }); } catch (e) {} }
  return { done: done, left: left, gaps: gaps };
}

function dossierScheduleContinue_() {
  try {
    ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'dossierFillContinue_') ScriptApp.deleteTrigger(t); });
    ScriptApp.newTrigger('dossierFillContinue_').timeBased().after(60 * 1000).create();
  } catch (e) { /* нет прав на триггеры — тогда нажать кнопку ещё раз */ }
}

/** Для одноразового триггера: продолжить проход по досье. */
function dossierFillContinue_() {
  try { ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'dossierFillContinue_') ScriptApp.deleteTrigger(t); }); } catch (e) {}
  try { dossierFillAll_(true); } catch (e) { console.log('dossier: ' + e.message); }
}

function agentSheet_(ss) {
  var sh = ss.getSheetByName(AGENT_SHEET);
  if (!sh) {
    sh = ss.insertSheet(AGENT_SHEET);
    sh.getRange(1, 1, 1, AGENT_HEADER.length).setValues([AGENT_HEADER]).setFontWeight('bold').setBackground('#1a4fd6').setFontColor('#ffffff');
    sh.setFrozenRows(1);
    [95, 230, 300, 300, 260, 260, 320, 320, 130].forEach(function (w, i) { sh.setColumnWidth(i + 1, w); });
  }
  return sh;
}

function agentMessageText_(dayKey, items, model, usage) {
  var lines = ['🧠 <b>СВОДКА АГЕНТА</b> · ' + escHtml_(ruDayTitle_(dayKey).toLowerCase()), ''];
  items.forEach(function (it) {
    var b = it.brief;
    lines.push('🏒 <b>' + escHtml_(it.m.home + ' — ' + it.m.away) + '</b>' + (it.m.time ? ' · ' + it.m.time + ' МСК' : ''));
    if (it.error) { lines.push('⚠️ не получилось: ' + escHtml_(it.error)); lines.push(''); return; }
    (b.extra || []).forEach(function (t) { lines.push(escHtml_(t)); });
    lines.push('🧤 ' + escHtml_(b.goalies));
    lines.push('🏥 ' + escHtml_(it.m.home) + ': ' + escHtml_(b.home_lineup));
    lines.push('🏥 ' + escHtml_(it.m.away) + ': ' + escHtml_(b.away_lineup));
    lines.push('📈 ' + escHtml_(b.form));
    lines.push('❗ ' + escHtml_(b.key));
    if (b.leanText) lines.push('🧭 ' + escHtml_(b.leanText));
    if (b.lineups && b.lineups.length) { lines.push('🧾 <i>заявки прошлых матчей:</i>'); b.lineups.forEach(function (t) { lines.push(escHtml_(t)); }); }
    if (it.keyNote) lines.push('🧍 ' + escHtml_(it.keyNote));
    if (b.links.length) lines.push(b.links.map(function (l) { return '<a href="' + escHtml_(l.url) + '">[' + l.n + ']' + (l.blog ? ' блог' : l.tg ? ' tg' : '') + '</a>'; }).join(' '));
    lines.push('');
  });
  lines.push('<i>Только факты из найденных статей и досье команд; [n] — источник, «блог» — статья болельщика (менее надёжно). Модель: ' + escHtml_(model || '—') +
    '. Поиск в этом месяце: ' + usage.used + ' из ' + AGENT_TAVILY_MONTHLY_CAP + ' кредитов.</i>');
  return lines.join('\n');
}

/** Сводка по матчам дня: пишет на лист и шлёт админу. dayKey — 'yyyy-MM-dd' по МСК (по умолчанию сегодня).
 * Google обрывает запуск через 6 минут, а один матч агент разбирает около минуты. Поэтому:
 *  • каждый готовый матч сразу пишется на лист, готовые части сразу уходят в Telegram (до 4096 знаков в сообщении);
 *  • после AGENT_BRIEF_MAX_MS новых матчей не начинаем — остальные доделает отдельный запуск через минуту;
 *  • на случай обрыва заранее стоит страховочный запуск: он продолжит с первого неразобранного матча. */
var AGENT_BRIEF_MAX_MS = 3 * 60 * 1000;
var AGENT_BRIEF_FLUSH_MS = 2 * 60 * 1000;
var AGENT_BRIEF_PART = 'AGENT_BRIEF_PART';
function agentDailyBrief_(dayKey, chatId, cont) {
  var ss = SpreadsheetApp.getActive(), p = agentProps_(), t0 = Date.now();
  if (!p.getProperty('GEMINI_KEY')) return { skipped: 'нет ключей' };   // поиск Tavily теперь запасной — без него работают sports.ru, Telegram и составы
  dayKey = dayKey || agentMskDay_();
  var matches = agentMatchesOfDay_(ss, dayKey);
  if (!matches.length) return { matches: 0 };
  var key = function (m) { return m.home + '|' + m.away; };
  var st = { day: dayKey, chat: chatId || (cont && cont.chat) || p.getProperty('TG_ADMIN_ID') || '', part: cont && cont.part ? cont.part : 0,
    rows: cont && cont.rows ? cont.rows : 0, done: cont && cont.done ? cont.done.slice() : [], sent: cont && cont.sent ? cont.sent.slice() : [] };
  var sh = agentSheet_(ss), unsent = [];
  if (cont) {                                                               // после обрыва верим листу: что уже записано сверху — сделано
    var dd = dayKey.split('-').reverse().join('.'), n = 0, top = sh.getLastRow() > 1 ? sh.getRange(2, 1, Math.min(40, sh.getLastRow() - 1), AGENT_HEADER.length).getValues() : [];
    var byKey = {}; matches.forEach(function (m) { byKey[key(m)] = m; });
    while (n < top.length && (top[n][0] instanceof Date ? sheetDayKey_(top[n][0]).split('-').reverse().join('.') : String(top[n][0])) === dd) {
      var r0 = top[n], mk = String(r0[1]).split(' — ').join('|');
      if (st.done.indexOf(mk) < 0) st.done.push(mk);
      if (st.sent.indexOf(mk) < 0 && byKey[mk]) {                             // разобран, но до Telegram не дошёл — берём с листа
        var err = /^⚠️ /.test(String(r0[2])) ? String(r0[2]).slice(3) : '';
        unsent.push(err ? { m: byKey[mk], error: err } : { m: byKey[mk], brief: { home_lineup: r0[2], away_lineup: r0[3], goalies: r0[4], form: r0[5], key: r0[6],
          links: String(r0[7] || '').split('\n').map(function (l) { var x = l.match(/^\[(\d+)\]\s+(\S+)/); return x ? { n: +x[1], url: x[2], blog: /\(блог\)/.test(l) } : null; }).filter(Boolean) } });
      }
      n++;
    }
    st.rows = n;
  }
  var todo = matches.filter(function (m) { return st.done.indexOf(key(m)) < 0; });
  if (!todo.length && !unsent.length) { p.deleteProperty(AGENT_BRIEF_PART); return { matches: matches.length, done: st.done.length, rest: 0, errors: 0, sent: false, sendError: '', parts: 0, model: '' }; }
  var save = function () { p.setProperty(AGENT_BRIEF_PART, JSON.stringify(st)); };
  var schedule = function (ms) {
    try {
      ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'agentBriefContinue_') ScriptApp.deleteTrigger(t); });
      if (ms) ScriptApp.newTrigger('agentBriefContinue_').timeBased().after(ms).create();
    } catch (e) {}
  };
  save(); schedule(7 * 60 * 1000);                                           // страховка: если Google оборвёт запуск
  var now = mskNow_(), items = [], pending = unsent.slice(), model = '', rest = [], sentAll = { ok: true, parts: 0, error: '' };
  var flush = function (last) {
    if (!pending.length && !(last && st.part === 0)) return;
    st.part++;
    var text = agentMessageText_(dayKey, pending, model, agentTavilyBudget_());
    var multi = st.part > 1 || !last || rest.length > 0;
    if (multi) text = text.replace('</b> · ', '</b> · часть ' + st.part + ' · ');
    if (last && rest.length) text += '\n\n⏳ Ещё ' + rest.length + ' ' + ruPlural_(rest.length, 'матч', 'матча', 'матчей') + ' — следующим сообщением через пару минут.';
    if (st.chat) {
      var r = tgSendLong_(st.chat, text);
      sentAll.parts += r.parts || 0;
      if (!r.ok) { sentAll.ok = false; sentAll.error = r.error; }
    }
    if (st.chat) pending.forEach(function (x) { st.sent.push(key(x.m)); });
    pending = [];
    save();
  };
  var lastFlush = Date.now();
  todo.forEach(function (m) {
    if (items.length && Date.now() - t0 > AGENT_BRIEF_MAX_MS) { rest.push(m); return; }   // не успеваем — доделает следующий запуск
    var it = { m: m };
    try { it.brief = agentBriefMatch_(m, ss); model = it.brief.model || model; }
    catch (e) { it.error = e.message; }
    items.push(it); pending.push(it);
    var b = it.brief || {};
    var row = [dayKey.split('-').reverse().join('.'), m.home + ' — ' + m.away,
      it.error ? '⚠️ ' + it.error : b.home_lineup, b.away_lineup || '', b.goalies || '', b.form || '', b.key || '',
      (b.links || []).map(function (l) { return '[' + l.n + '] ' + l.url + (l.blog ? ' (блог)' : ''); }).join('\n'), now];
    sh.insertRowsAfter(1 + st.rows, 1);                                        // матчи дня — по порядку, сразу на лист
    sh.getRange(2 + st.rows, 1, 1, AGENT_HEADER.length).setValues([row]).setWrap(true).setVerticalAlignment('top');
    try { SpreadsheetApp.flush(); } catch (e) {}
    st.rows++; st.done.push(key(m)); save();
    if (Date.now() - lastFlush > AGENT_BRIEF_FLUSH_MS && todo.length > items.length) { flush(false); lastFlush = Date.now(); }   // готовое — не держим до конца
  });
  flush(true);
  if (rest.length) schedule(60 * 1000);
  else { schedule(0); p.deleteProperty(AGENT_BRIEF_PART); }
  return { matches: matches.length, done: st.done.length, rest: rest.length, errors: items.filter(function (x) { return x.error; }).length,
    sent: !!(st.chat && sentAll.ok), sendError: !st.chat ? '' : sentAll.ok ? '' : sentAll.error, parts: sentAll.parts, model: model };
}

/** Строка для листа «Автоматика». */
function agentBriefStatus_(r) {
  if (r.skipped) return 'пропущено: ' + r.skipped;
  return 'матчей: ' + (r.done !== undefined ? r.done : r.matches || 0) + (r.rest ? ' из ' + r.matches + ' (остальные — следующим запуском)' : '') +
    (r.errors ? ', с ошибкой: ' + r.errors : '') + (r.sendError ? ' · в Telegram не ушло: ' + r.sendError : '');
}

/** Продолжение сводки: не успели все матчи за один запуск или Google оборвал запуск. */
function agentBriefContinue_() {
  try { ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'agentBriefContinue_') ScriptApp.deleteTrigger(t); }); } catch (e) {}
  var p = agentProps_(), st = null;
  try { st = JSON.parse(p.getProperty(AGENT_BRIEF_PART) || 'null'); } catch (e) { st = null; }
  if (!st || !st.day || st.day < agentMskDay_(new Date(Date.now() - 86400000))) { p.deleteProperty(AGENT_BRIEF_PART); return; }   // старое — не доделываем
  try { agentDailyBrief_(st.day, st.chat || null, st); }
  catch (e) { p.deleteProperty(AGENT_BRIEF_PART); autoNotifyAdmin_('⚠ Сводка агента (продолжение) не собралась: ' + e.message); }
}

/** Длинный HTML-текст — несколькими сообщениями по границам абзацев. Если Telegram не принял разметку — та же часть без неё. */
var TG_PART_MAX = 3800;
function tgSendLong_(chat, html) {
  var blocks = String(html).split('\n\n'), parts = [], cur = '';
  var push = function (b) {
    if (b.length > TG_PART_MAX) {                                             // один огромный блок — режем по строкам
      b.split('\n').forEach(function (ln) { while (ln.length > TG_PART_MAX) { push(ln.slice(0, TG_PART_MAX)); ln = ln.slice(TG_PART_MAX); } push(ln); });
      return;
    }
    if (cur && (cur + '\n\n' + b).length > TG_PART_MAX) { parts.push(cur); cur = b; } else cur = cur ? cur + '\n\n' + b : b;
  };
  blocks.forEach(push);
  if (cur) parts.push(cur);
  var ok = true, err = '';
  parts.forEach(function (t) {
    var r = tg_('sendMessage', { chat_id: chat, text: t, parse_mode: 'HTML', disable_web_page_preview: true });
    if (!r || !r.ok) {
      var plain = t.replace(/<[^>]+>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
      r = tgRaw_('sendMessage', { chat_id: chat, text: plain, disable_web_page_preview: true });
    }
    if (!r || !r.ok) { ok = false; err = (r && r.description) || 'Telegram не ответил'; }
  });
  return { ok: ok, parts: parts.length, error: err };
}



/** Из меню: проверить ключи и модель, не тратя поиск. */
function agentCheckKeys_() {
  var p = agentProps_(), out = [];
  out.push('TAVILY_KEY: ' + (p.getProperty('TAVILY_KEY') ? 'есть' : 'НЕТ'));
  out.push('GEMINI_KEY: ' + (p.getProperty('GEMINI_KEY') ? 'есть' : 'НЕТ'));
  if (p.getProperty('GEMINI_KEY')) {
    try {
      var g = agentGemini_('Ответь JSON {"ok":true}');
      out.push('Gemini работает, модель: ' + g.model);
    } catch (e) { out.push('Gemini: ошибка — ' + e.message); }
  }
  var u = agentTavilyBudget_();
  out.push('Поиск в этом месяце: ' + u.used + ' из ' + AGENT_TAVILY_MONTHLY_CAP + ' кредитов');
  out.push('Сводка в Telegram: ' + (p.getProperty('TG_ADMIN_ID') ? 'подключена' : 'напишите боту /agent'));
  uiAlert_(out.join('\n'));
}

/* ── Границы диапазонов в формулах листов ──
 * Формулы Data и Форма_расчет считали только строки 2–442 листа «результаты матчей», а в сезоне 748 матчей:
 * с середины ноября очки, победы и форма перестали бы обновляться. Расширяем до строки FORMULA_RESULTS_ROWS.
 * Повторный запуск ничего не меняет. Значения (рейтинг силы, голы дома/в гостях) не трогаются. */
var FORMULA_BOUND_SHEETS = ['Data', 'Форма_расчет'];
function repairFormulaBounds_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var fixed = 0, re = /('результаты матчей'!R2C\d+:R)(442|749|997|999)(C\d+)/g;
  FORMULA_BOUND_SHEETS.forEach(function (name) {
    var sh = ss.getSheetByName(name); if (!sh || sh.getLastRow() < 2) return;
    var nr = sh.getLastRow() - 1, nc = sh.getLastColumn();
    var f = sh.getRange(2, 1, nr, nc).getFormulasR1C1();
    for (var c = 0; c < nc; c++) {
      var col = f.map(function (row) { return row[c]; });
      var out = col.map(function (x) { return x ? x.replace(re, '$1' + FORMULA_RESULTS_ROWS + '$3') : x; });
      var changed = out.filter(function (x, i) { return x !== col[i]; }).length;
      if (!changed) continue;
      if (col.every(function (x) { return !!x; })) sh.getRange(2, c + 1, nr, 1).setFormulasR1C1(out.map(function (x) { return [x]; }));
      else out.forEach(function (x, i) { if (x !== col[i]) sh.getRange(2 + i, c + 1).setFormulaR1C1(x); });
      fixed += changed;
    }
  });
  return { fixed: fixed };
}

/* ── Точки расширения для другой лиги (в КХЛ ничего не делают; таблица НХЛ подставляет свои данные) ── */

/* ==========================================================================
 * 🖼 КАРТОЧКИ МАТЧЕЙ ДНЯ (картинки 1280×720 в фирменном стиле JARVIS)
 *  Скрипт рисует слайд в служебной презентации Google Slides, выгружает PNG и присылает вам ботом.
 *  Данные: очки и игры — лист Data, форма (5 матчей) — «результаты матчей», время и П1/Х/П2 в основное время — журнал линий Pinnacle.
 *  Логотипы: папка «JARVIS логотипы» на вашем Google Диске, файл = название клуба (СКА.png, Вашингтон.png или WSH.png).
 *  Нет логотипа — рисуется кружок цвета клуба с сокращением.
 * ==========================================================================*/
/* Левая половина шапки — имя канала (без «собаки»), чтобы карточку можно было репостить и было видно, чьё это.
 * Своё слово можно задать свойством BANNER_BRAND; пустое значение — только лига. */
function bannerBrand_() {
  var own = PropertiesService.getScriptProperties().getProperty('BANNER_BRAND');
  if (own !== null && own !== undefined) return String(own).trim();
  var ch = String(bannerChannel_() || '').replace(/^@/, '').trim();
  return ch ? ch.toUpperCase() : '';
}
var BANNER_HANDLE = '@jarvibet';
var BANNER_LOGO_FOLDER = 'JARVIS логотипы';
var BANNER_PRES_NAME = 'JARVIS — карточки матчей (служебная, не удалять)';
var BANNER_GOLD = '#ffc23d';
var BANNER_FONT = 'Montserrat';
var TEAM_COLORS = {
  'Авангард': '#c8102e', 'Автомобилист': '#b3202a', 'Адмирал': '#1b3f8b', 'Ак Барс': '#0f7b3e', 'Амур': '#d6222a', 'Барыс': '#00a3e0',
  'Динамо Минск': '#1e5aa8', 'Динамо Москва': '#0b4da2', 'Лада': '#1c5aa6', 'Локомотив': '#c8102e', 'Металлург': '#f0a202', 'Нефтехимик': '#2a6fb4',
  'Салават Юлаев': '#0a8f4f', 'Северсталь': '#f2c500', 'Сибирь': '#0b3d91', 'СКА': '#1e3f99', 'Сочи': '#0d6fb8', 'Спартак': '#d2001f',
  'Торпедо': '#0e3b85', 'Трактор': '#5a6270', 'Шанхайские Драконы': '#e4572e', 'ЦСКА': '#b0122a',
  'Анахайм': '#f47a38', 'Бостон': '#ffb81c', 'Баффало': '#003087', 'Калгари': '#c8102e', 'Каролина': '#ce1126', 'Чикаго': '#cf0a2c', 'Колорадо': '#6f263d',
  'Коламбус': '#002654', 'Даллас': '#006847', 'Детройт': '#ce1126', 'Эдмонтон': '#ff4c00', 'Флорида': '#c8102e', 'Лос-Анджелес': '#a2aaad', 'Миннесота': '#154734',
  'Монреаль': '#af1e2d', 'Нэшвилл': '#ffb81c', 'Нью-Джерси': '#ce1126', 'Айлендерс': '#00539b', 'Рейнджерс': '#0038a8', 'Оттава': '#da1a32', 'Филадельфия': '#f74902',
  'Питтсбург': '#fcb514', 'Сан-Хосе': '#006d75', 'Сиэтл': '#68a2b9', 'Сент-Луис': '#002f87', 'Тампа-Бэй': '#002868', 'Торонто': '#00205b', 'Юта': '#6cace4',
  'Ванкувер': '#00843d', 'Вегас': '#b4975a', 'Вашингтон': '#c8102e', 'Виннипег': '#004c97'
};
var RU_WD_SHORT_ = ['ВС', 'ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ'];

/* ── Кружок цвета клуба перед названием в постах ──
 * В канале бот не может показать премиум-смайлик с логотипом (правило Telegram), поэтому в тексте стоит
 * кружок цвета клуба. Если логотипы клубов заданы боту (/emoji), кружок подменяется логотипом там,
 * где Telegram это разрешает (личка с ботом у владельца с Premium), а в канале остаётся кружок. */
var TEAM_CIRCLES_ = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤', '⚫', '⚪'];
var TEAM_CIRCLE_OVERRIDE = { 'Металлург': '🟠', 'Колорадо': '🔴', 'Лос-Анджелес': '⚫', 'Трактор': '⚫', 'Вегас': '🟡' };
function teamCircle_(team) {
  team = String(team || '').trim();
  if (TEAM_CIRCLE_OVERRIDE[team]) return TEAM_CIRCLE_OVERRIDE[team];
  var hex = TEAM_COLORS[team];
  if (!hex || !/^#[0-9a-f]{6}$/i.test(hex)) return '';
  var r = parseInt(hex.substr(1, 2), 16) / 255, g = parseInt(hex.substr(3, 2), 16) / 255, b = parseInt(hex.substr(5, 2), 16) / 255;
  var mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, sat = mx ? d / mx : 0;
  if (sat < 0.25 || mx < 0.15) return mx > 0.6 ? '⚪' : '⚫';
  var h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  h = (h * 60 + 360) % 360;
  return h < 10 || h >= 345 ? '🔴' : h < 40 ? '🟠' : h < 65 ? '🟡' : h < 170 ? '🟢' : h < 260 ? '🔵' : '🟣';
}
/** «🔵 Торпедо» (HTML-безопасно); у неизвестной команды — просто название. */
function teamMark_(team) { var c = teamCircle_(team); return (c ? c + ' ' : '') + escHtml_(team); }

/**
 * Бесплатная проверка Telegram: принимает ли Telegram токен этой таблицы, видит ли бот канал
 * и вашу личку. Сам токен нигде не показывается — только длина и последние 4 символа,
 * чтобы можно было сверить его с другой таблицей, не раскрывая.
 */
function tgCheckNow_() {
  var p = PropertiesService.getScriptProperties(), tok = String(p.getProperty('TG_BOT_TOKEN') || '');
  var tail = tok ? 'В этой таблице TG_BOT_TOKEN: ' + tok.length + ' символов, оканчивается на «…' + tok.slice(-4) + '».' : '';
  var how = '\n\nГде поменять: редактор скрипта → ⚙️ Настройки проекта → Свойства скрипта → TG_BOT_TOKEN. ' +
    'Значение должно совпадать с таблицей КХЛ (без пробелов в начале и конце).';
  if (!tok) { uiAlert_('❌ Токен бота не задан в этой таблице.' + how); return; }
  if (/\s/.test(tok)) { uiAlert_('❌ В токене есть пробел или перенос строки — Telegram такой не примет.\n\n' + tail + how); return; }
  var me = tg_('getMe', {});
  if (!me.ok) {
    uiAlert_('❌ Telegram не принял токен: ' + (me.description || '') +
      (/not found/i.test(me.description || '') ? '\n(«Not Found» — значит такого бота нет: токен чужой, старый или обрезанный.)' : '') +
      '\n\n' + tail + how);
    return;
  }
  var nhl = typeof nhlChannelId_ === 'function';                       // в таблице НХЛ свои свойства и своя настройка
  var fix = nhl ? 'меню «НХЛ-парсер» → Настройки → «Ключи и Telegram для НХЛ»' : '⚙️ Настройки проекта → Свойства скрипта';
  var out = ['✅ Бот @' + me.result.username + ' — токен рабочий.'];
  var ch = bannerChannel_();
  if (!ch) out.push('⚠️ Канал не указан (свойство ' + (nhl ? 'NHL_CHANNEL' : 'TG_CHANNEL') + ') — посты в канал не уходят. Где вписать: ' + fix + '.');
  else {
    var c = tg_('getChat', { chat_id: ch });
    if (!c.ok) out.push('❌ Канал ' + ch + ': ' + (c.description || '') + ' — проверьте имя канала.');
    else {
      var adm = tg_('getChatMember', { chat_id: ch, user_id: me.result.id });
      var isAdmin = adm.ok && (adm.result.status === 'administrator' || adm.result.status === 'creator');
      out.push((isAdmin ? '✅' : '❌') + ' Канал ' + ch + ' («' + (c.result.title || '') + '»): ' +
        (isAdmin ? 'бот — администратор.' : 'бот НЕ администратор — добавьте его в админы с правом публиковать.'));
    }
  }
  var adminId = p.getProperty('TG_ADMIN_ID');
  var howAdmin = nhl ? 'возьмите число из свойства TG_ADMIN_ID таблицы КХЛ (бот отвечает только там) и впишите: ' + fix
    : 'напишите боту /agent — он запомнит вас сам';
  if (!adminId) out.push('⚠️ Личка не подключена — ' + howAdmin + '.');
  else {
    var a = tg_('getChat', { chat_id: adminId });
    out.push((a.ok ? '✅ Личка подключена' + (a.result.first_name ? ' (' + a.result.first_name + ')' : '') + '.' :
      '❌ Личка: ' + (a.description || '') + ' — в свойстве TG_ADMIN_ID неверное число. Что делать: ' + howAdmin + '.'));
  }
  var map = tgEmojiMap_(), teamMap = tgTeamEmojiMap_(), nMap = Object.keys(map).length + Object.keys(teamMap).length;
  if (!nMap) out.push('ℹ️ Премиум-смайлики не заданы. Как задать: напишите боту /emoji.');
  else {
    out.push('✨ Премиум-смайликов задано: ' + nMap + ' (логотипов клубов: ' + Object.keys(teamMap).length + ').');
    if (ch && tgEmojiBlocked_(ch)) out.push('   В канал они не уходят — Telegram разрешает их боту только в личке, группах и супергруппах. В канале остаются обычные смайлики и кружки.');
    var le = p.getProperty('TG_EMOJI_LAST_ERROR');
    if (le) out.push('   Последний отказ Telegram: ' + le);
  }
  out.push('', tail);
  uiAlert_(out.join('\n'));
}


function ruPlural_(n, one, few, many) { var a = Math.abs(n) % 100, b = a % 10; return a > 10 && a < 20 ? many : b > 1 && b < 5 ? few : b === 1 ? one : many; }

/** Данные карточек на день: [{home, away, day, time, pts, gp, form, odds:[p1,x,p2]}] */
function bannerData_(ss, dayKey) {
  var matches = agentMatchesOfDay_(ss, dayKey), odds = {};
  try { odds = readOddsLog_(ss); } catch (e) { odds = {}; }
  var data = {}, dsh = ss.getSheetByName('Data');
  if (dsh && dsh.getLastRow() >= 2) dsh.getRange(2, 1, dsh.getLastRow() - 1, 3).getValues().forEach(function (r) { if (r[0]) data[String(r[0]).trim()] = { gp: Number(r[1]) || 0, pts: Number(r[2]) || 0 }; });
  var games = [], rs = ss.getSheetByName(SHEET_RESULTS);
  if (rs && rs.getLastRow() >= 2) rs.getRange(2, 1, rs.getLastRow() - 1, 7).getValues().forEach(function (r) {
    if (!(r[0] instanceof Date) || String(r[1]).trim() !== 'Сыгран') return;
    games.push({ key: sheetDayKey_(r[0]), home: String(r[2]).trim(), away: String(r[3]).trim(), hg: Number(r[4]), ag: Number(r[5]), ot: r[6] === true || String(r[6]).toUpperCase() === 'TRUE' });
  });
  games.sort(function (a, b) { return a.key < b.key ? -1 : a.key > b.key ? 1 : 0; });
  var form = function (team) {
    var out = [];
    games.forEach(function (g) {
      if (g.key >= dayKey || (g.home !== team && g.away !== team)) return;
      var won = g.home === team ? g.hg > g.ag : g.ag > g.hg;
      out.push(g.ot ? (won ? 'ОТВ' : 'ОТП') : (won ? 'В' : 'П'));
    });
    return out.slice(-5);                                                     // свежие — справа
  };
  matches.sort(function (a, b) { var x = a.time || '99', y = b.time || '99'; return x < y ? -1 : x > y ? 1 : 0; });   // без времени — в конец
  return matches.map(function (m) {
    var o = odds[dayKey + '|' + m.home + '|' + m.away] || {};
    return { home: m.home, away: m.away, day: dayKey, time: m.time || o.time || '',
      h: { name: m.home, pts: (data[m.home] || {}).pts || 0, gp: (data[m.home] || {}).gp || 0, form: form(m.home) },
      a: { name: m.away, pts: (data[m.away] || {}).pts || 0, gp: (data[m.away] || {}).gp || 0, form: form(m.away) },
      odds: o.regOdds || null };
  });
}

/** Логотипы из папки на Диске: {название без расширения: Blob} (один раз за запуск). */
var BANNER_LOGOS_ = null;
function bannerLogos_() {
  if (BANNER_LOGOS_) return BANNER_LOGOS_;
  BANNER_LOGOS_ = {};
  try {
    var it = DriveApp.getFoldersByName(BANNER_LOGO_FOLDER);
    if (!it.hasNext()) return BANNER_LOGOS_;
    var files = it.next().getFiles();
    while (files.hasNext()) { var f = files.next(); if (/^image\//.test(f.getMimeType())) BANNER_LOGOS_[f.getName().replace(/\.[^.]+$/, '').trim().toLowerCase()] = f; }
  } catch (e) { /* нет доступа к Диску — будут кружки */ }
  return BANNER_LOGOS_;
}
function bannerLogoFor_(team) {
  var L = bannerLogos_(), keys = [team.toLowerCase()];
  try { if (typeof NHL_TEAMS !== 'undefined') NHL_TEAMS.forEach(function (t) { if (t[1] === team) keys.push(t[0].toLowerCase()); }); } catch (e) {}
  for (var i = 0; i < keys.length; i++) if (L[keys[i]]) return L[keys[i]].getBlob();
  return null;
}

/** Служебная презентация (создаётся один раз). */
function bannerPres_() {
  var p = PropertiesService.getScriptProperties(), id = p.getProperty('BANNER_PRES_ID'), pres = null;
  if (id) { try { pres = SlidesApp.openById(id); } catch (e) { pres = null; } }
  if (!pres) { pres = SlidesApp.create(BANNER_PRES_NAME); p.setProperty('BANNER_PRES_ID', pres.getId()); }
  return pres;
}

/* ---- рисование (координаты в пунктах, слайд 720×405 = 1280×720 px) ---- */
function bnText_(slide, text, x, y, w, h, size, color, weight, align) {
  var tb = slide.insertTextBox(text, x, y, w, h);
  var st = tb.getText().getTextStyle();
  st.setFontFamilyAndWeight(BANNER_FONT, weight || 700).setFontSize(size).setForegroundColor(color || '#ffffff');
  tb.getText().getParagraphStyle().setParagraphAlignment(align || SlidesApp.ParagraphAlignment.CENTER);
  tb.setContentAlignment(SlidesApp.ContentAlignment.MIDDLE);
  return tb;
}
function bnShape_(slide, type, x, y, w, h, fill, alpha, line, lineAlpha, lineW) {
  var s = slide.insertShape(type, x, y, w, h);
  if (fill) s.getFill().setSolidFill(fill, alpha === undefined ? 1 : alpha); else s.getFill().setTransparent();
  if (line) { s.getBorder().getLineFill().setSolidFill(line, lineAlpha === undefined ? 1 : lineAlpha); s.getBorder().setWeight(lineW || 1); } else s.getBorder().setTransparent();
  return s;
}
function bnShort_(team) {
  var w = team.split(/[\s-]+/);
  return (w.length > 1 ? w.map(function (x) { return x.charAt(0); }).join('') : team.slice(0, 3)).toUpperCase();
}

function bannerDrawTeam_(slide, t, x, y) {
  var W = 294, H = 205, col = TEAM_COLORS[t.name] || '#2a3b5c';
  bnShape_(slide, SlidesApp.ShapeType.ROUND_RECTANGLE, x, y, W, H, '#0b111c', 0.78, '#ffffff', 0.16, 1);
  var logo = null; try { logo = bannerLogoFor_(t.name); } catch (e) { logo = null; }
  var box = 92, lx = x + (W - box) / 2, ly = y + 12;
  if (logo) {
    var img = slide.insertImage(logo), iw = img.getWidth(), ih = img.getHeight(), k = Math.min(box / iw, box / ih);
    img.setWidth(iw * k).setHeight(ih * k).setLeft(lx + (box - iw * k) / 2).setTop(ly + (box - ih * k) / 2);
  } else {
    var c = bnShape_(slide, SlidesApp.ShapeType.ELLIPSE, lx + 6, ly + 6, box - 12, box - 12, col, 1, '#ffffff', 0.9, 2);
    c.getText().setText(bnShort_(t.name));
    c.getText().getTextStyle().setFontFamilyAndWeight(BANNER_FONT, 800).setFontSize(18).setForegroundColor('#ffffff');
    c.getText().getParagraphStyle().setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
    c.setContentAlignment(SlidesApp.ContentAlignment.MIDDLE);
  }
  var nm = t.name.toUpperCase(), fs = nm.length <= 8 ? 28 : nm.length <= 11 ? 23 : nm.length <= 14 ? 19 : 16;
  bnText_(slide, nm, x + 8, y + 108, W - 16, 38, fs, '#ffffff', 900);
  var sub = t.gp ? t.pts + ' ' + ruPlural_(t.pts, 'ОЧКО', 'ОЧКА', 'ОЧКОВ') + ' · ' + t.gp + ' ' + ruPlural_(t.gp, 'ИГРА', 'ИГРЫ', 'ИГР') : 'ПЕРВЫЙ МАТЧ СЕЗОНА';
  bnText_(slide, sub, x + 8, y + 146, W - 16, 18, 10.5, '#c9d2e0', 500);
  var ln = slide.insertLine(SlidesApp.LineCategory.STRAIGHT, x + 62, y + 170, x + W - 62, y + 170);
  ln.getLineFill().setSolidFill('#ffffff', 0.18); ln.setWeight(0.75);
  var n = t.form.length, d = 16, gap = 5, fx = x + (W - (n * d + (n - 1) * gap)) / 2;
  t.form.forEach(function (r, i) {
    var ot = r.indexOf('ОТ') === 0, win = r === 'В' || r === 'ОТВ', colr = win ? '#22c55e' : '#ef4444';
    var s = bnShape_(slide, SlidesApp.ShapeType.ELLIPSE, fx + i * (d + gap), y + 177, d, d, ot ? '#ffffff' : colr, 1, ot ? colr : null, 1, 2);
    s.getText().setText(ot ? 'ОТ' : r);
    s.getText().getTextStyle().setFontFamilyAndWeight(BANNER_FONT, 800).setFontSize(ot ? 5.5 : 7).setForegroundColor(ot ? '#111827' : '#ffffff');
    s.getText().getParagraphStyle().setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
    s.setContentAlignment(SlidesApp.ContentAlignment.MIDDLE);
  });
}

/** Одна карточка на новом слайде. Возвращает слайд. */
function bannerDraw_(pres, m) {
  var slide = pres.appendSlide(SlidesApp.PredefinedLayout.BLANK);
  slide.getBackground().setSolidFill('#0a1020');
  var ch = TEAM_COLORS[m.home] || '#2a3b5c', ca = TEAM_COLORS[m.away] || '#2a3b5c';
  // свечение цветов клубов: слои полупрозрачных кругов дают плавный переход (размытия в Slides нет)
  [[700, 0.07], [600, 0.07], [500, 0.07], [400, 0.08], [300, 0.08]].forEach(function (l) {
    bnShape_(slide, SlidesApp.ShapeType.ELLIPSE, 100 - l[0] / 2, 180 - l[0] / 2, l[0], l[0], ch, l[1]);
    bnShape_(slide, SlidesApp.ShapeType.ELLIPSE, 620 - l[0] / 2, 180 - l[0] / 2, l[0], l[0], ca, l[1]);
  });
  [[520, 0.03], [380, 0.03]].forEach(function (l) { bnShape_(slide, SlidesApp.ShapeType.ELLIPSE, 360 - l[0] / 2, -l[0] / 2, l[0], l[0] * 0.7, '#ffffff', l[1]); });
  var brand = bannerBrand_();
  var hd = bnText_(slide, (brand ? brand + '  |  ' : '') + BANNER_LEAGUE, 200, 14, 320, 26, 15, '#ffffff', 900);
  var ht = hd.getText(), cut = ht.asString().indexOf('|');
  if (cut >= 0) {
    ht.getRange(cut, cut + 1).getTextStyle().setForegroundColor('#8a93a3');
    ht.getRange(cut + 1, ht.asString().replace(/\n$/, '').length).getTextStyle().setForegroundColor(BANNER_GOLD);
  } else ht.getTextStyle().setForegroundColor(BANNER_GOLD);
  bannerDrawTeam_(slide, m.h, 32, 54);
  bannerDrawTeam_(slide, m.a, 394, 54);
  bnText_(slide, 'VS', 330, 140, 60, 30, 15, '#aab4c5', 900);
  var p = m.day.split('-'), wd = RU_WD_SHORT_[new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])).getUTCDay()];
  var pill = bnShape_(slide, SlidesApp.ShapeType.ROUND_RECTANGLE, 262, 272, 196, 30, '#0b111c', 0.92, BANNER_GOLD, 1, 1.5);
  pill.getText().setText(wd + ' ' + p[2] + '.' + p[1] + (m.time ? ' · ' + m.time + ' МСК' : ''));
  pill.getText().getTextStyle().setFontFamilyAndWeight(BANNER_FONT, 800).setFontSize(12.5).setForegroundColor('#ffffff');
  pill.getText().getParagraphStyle().setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
  pill.setContentAlignment(SlidesApp.ContentAlignment.MIDDLE);
  if (m.odds) {
    var fav = m.odds[0] <= m.odds[2] ? 0 : 2, labels = ['П1', 'Х', 'П2'], w = 74, g = 10, x0 = 360 - (3 * w + 2 * g) / 2;
    m.odds.forEach(function (o, i) {
      var hot = i === fav;
      var b = bnShape_(slide, SlidesApp.ShapeType.ROUND_RECTANGLE, x0 + i * (w + g), 312, w, 26, '#0b111c', 0.92, hot ? BANNER_GOLD : '#ffffff', hot ? 1 : 0.22, hot ? 1.5 : 1);
      b.getText().setText(labels[i] + '   ' + Number(o).toFixed(2));
      var tx = b.getText();
      tx.getTextStyle().setFontFamilyAndWeight(BANNER_FONT, 800).setFontSize(11).setForegroundColor(hot ? BANNER_GOLD : '#ffffff');
      tx.getRange(0, labels[i].length).getTextStyle().setFontFamilyAndWeight(BANNER_FONT, 600).setFontSize(9).setForegroundColor('#aab4c5');
      tx.getParagraphStyle().setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
      b.setContentAlignment(SlidesApp.ContentAlignment.MIDDLE);
    });
    bnText_(slide, 'КОЭФФИЦИЕНТЫ НА ОСНОВНОЕ ВРЕМЯ', 120, 344, 480, 14, 6.5, '#8a93a3', 600);
  }
  bnText_(slide, BANNER_HANDLE, 260, 364, 200, 18, 9.5, BANNER_GOLD, 700);
  return slide;
}

/** PNG слайда. */
function bannerPng_(presId, slideId, name) {
  var r = UrlFetchApp.fetch('https://docs.google.com/presentation/d/' + presId + '/export/png?pageid=' + slideId,
    { headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() }, muteHttpExceptions: true });
  if (r.getResponseCode() !== 200) throw new Error('выгрузка картинки: код ' + r.getResponseCode());
  return r.getBlob().setName(name + '.png');
}

/** Фото в Telegram (альбомами по 10). */
function tgSendPhotos_(chat, blobs, caption) {
  var token = PropertiesService.getScriptProperties().getProperty('TG_BOT_TOKEN');
  if (!token) throw new Error('не указан токен бота');
  for (var i = 0; i < blobs.length; i += 10) {
    var part = blobs.slice(i, i + 10), payload = { chat_id: String(chat) }, media = [];
    part.forEach(function (b, k) { payload['p' + k] = b; media.push({ type: 'photo', media: 'attach://p' + k }); });
    if (i === 0 && caption) { media[0].caption = caption; media[0].parse_mode = 'HTML'; }
    var method = part.length === 1 ? 'sendPhoto' : 'sendMediaGroup';
    if (part.length === 1) { payload = { chat_id: String(chat), photo: part[0] }; if (i === 0 && caption) { payload.caption = caption; payload.parse_mode = 'HTML'; } }
    else payload.media = JSON.stringify(media);
    var r = UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/' + method, { method: 'post', payload: payload, muteHttpExceptions: true });
    var j = {}; try { j = JSON.parse(r.getContentText()); } catch (e) { j = {}; }
    if (!j.ok) throw new Error('Telegram: ' + (j.description || ('код ' + r.getResponseCode())));
  }
  return blobs.length;
}

/** Собрать карточки дня. limit — сколько матчей (для пробы — 1). Возвращает {blobs, matches}. */
function bannersBuild_(dayKey, limit, only) {
  var ss = SpreadsheetApp.getActive(), list = bannerData_(ss, dayKey);
  if (only && only.length) list = list.filter(function (m) {         // карточка к посту-прогнозу — по одному матчу
    return only.some(function (x) { return x.home === m.home && x.away === m.away; });
  });
  if (limit) list = list.slice(0, limit);
  if (!list.length) return { blobs: [], matches: [] };
  BANNER_LOGOS_ = null;
  var pres = bannerPres_();
  pres.getSlides().forEach(function (s) { s.remove(); });
  var slides = list.map(function (m) { return bannerDraw_(pres, m); });
  var ids = slides.map(function (s) { return s.getObjectId(); });
  pres.saveAndClose();
  var blobs = ids.map(function (id, i) { return bannerPng_(pres.getId(), id, 'card_' + list[i].home + '_' + list[i].away); });
  return { blobs: blobs, matches: list };
}

function bannersSend_(target, dayKey, limit) {
  dayKey = dayKey || bannersDay_();
  var r = bannersBuild_(dayKey, limit);
  if (!r.blobs.length) return { sent: 0 };
  var chat = target === 'channel' ? bannerChannel_() : PropertiesService.getScriptProperties().getProperty('TG_ADMIN_ID');
  if (!chat) throw new Error(target === 'channel' ? 'не указан канал' : 'не указан ваш Telegram ID (TG_ADMIN_ID)');
  var d = dayKey.split('-').reverse().slice(0, 2).join('.');
  var noLogo = r.matches.reduce(function (a, m) { [m.home, m.away].forEach(function (t) { if (!bannerLogoFor_(t) && a.indexOf(t) === -1) a.push(t); }); return a; }, []);
  var cap = target === 'channel' ? '' : '🖼 Карточки матчей на ' + d + ': ' + r.blobs.length + '.' + (noLogo.length ? '\nНет логотипа в папке «' + BANNER_LOGO_FOLDER + '»: ' + escHtml_(noLogo.join(', ')) : '') +
    (limit ? '' : '\nОпубликовать в группу: меню «📣 НХЛ · ТГ группа» → «Карточки матчей ночи → группа».');
  tgSendPhotos_(chat, r.blobs, cap);
  if (target === 'channel') dailyMark_('cards');
  return { sent: r.blobs.length, noLogo: noLogo };
}

/* ---- расписание и меню ---- */
var BANNER_DAYS_AHEAD = 2;        // карточки готовим на сегодня и ещё на столько дней вперёд
function bannersAuto_() {
  if (nhlNotReady_(true)) return;
  matchiAuto_(bannersDay_());
  var sent = 0, err = '';
  for (var i = 0; i <= BANNER_DAYS_AHEAD; i++) {
    var day = addDaysKey_(bannersDay_(), i);
    try { sent += (bannersSend_('admin', day).sent || 0); }
    catch (e) { err = e.message; }
  }
  if (sent || !err) autoMark_('bannersAuto_', true, sent ? 'карточек: ' + sent + ' (на ' + (BANNER_DAYS_AHEAD + 1) + ' дня)' : 'матчей нет');
  else { autoMark_('bannersAuto_', false, err); autoNotifyAdmin_('⚠ Карточки матчей не собрались: ' + err); }
}
function bannersTestNow_() {
  try {
    var ss = SpreadsheetApp.getActive(), day = bannersDay_();
    for (var i = 0; i < 10 && !agentMatchesOfDay_(ss, day).length; i++) day = addDaysKey_(day, 1);
    var r = bannersSend_('admin', day, 1);
    uiAlert_(r.sent ? 'Пробная карточка на ' + day.split('-').reverse().join('.') + ' отправлена вам в Telegram.' + (r.noLogo.length ? '\n\nНет логотипов (нарисованы кружки): ' + r.noLogo.join(', ') + '. Положите файлы в папку «' + BANNER_LOGO_FOLDER + '» на Google Диске.' : '') : 'В ближайшие 10 дней матчей нет.');
  } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}
function bannersAllNow_() { try { var r = bannersSend_('admin'); uiAlert_(r.sent ? 'Карточки отправлены вам: ' + r.sent + '.' : 'Сегодня матчей нет.'); } catch (e) { uiAlert_('Не получилось: ' + e.message); } }
function bannersToChannelNow_() {
  var ui = null; try { ui = SpreadsheetApp.getUi(); } catch (e) { ui = null; }
  if (ui && ui.alert('Опубликовать карточки матчей дня в ' + (bannerChannel_() || 'канал') + '?', ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
  try { var r = bannersSend_('channel'); uiAlert_(r.sent ? 'Опубликовано: ' + r.sent + ' карточек.' : 'Сегодня матчей нет.'); } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}

/* ── Перенесённые матчи ──
 * Календарь добавляет перенесённый матч новой строкой (новая дата), а старая остаётся «Запланирован» навсегда —
 * вместе с прогнозом, который так и не будет проверен. Если у той же пары есть строка через 1–10 дней после
 * прошедшей даты, это перенос: старой строке ставим новую дату (и счёт, если он уже пришёл в новую строку),
 * новую строку очищаем; в «прогнозах» дату переносим так же. Прогноз остаётся тем, что был сделан до матча. */
function mergeRescheduled_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(SHEET_RESULTS); if (!sh || sh.getLastRow() < 3) return [];
  var v = sh.getRange(2, 1, sh.getLastRow() - 1, 7).getValues(), today = todayKey_(), moved = [];
  var rows = v.map(function (r, i) { return { i: i, d: r[0] instanceof Date ? sheetDayKey_(r[0]) : '', date: r[0], st: String(r[1]).trim(), h: String(r[2]).trim(), a: String(r[3]).trim(), hg: r[4], ag: r[5], ot: r[6] }; })
    .filter(function (x) { return x.d && x.h && x.a; });
  var used = {};
  rows.forEach(function (old) {
    if (old.st !== 'Запланирован' || old.d >= today || used[old.i]) return;
    var nw = rows.filter(function (x) {
      return x.i !== old.i && !used[x.i] && x.h === old.h && x.a === old.a && x.d > old.d && x.d <= addDaysKey_(old.d, 10);
    })[0];
    if (!nw) return;
    used[old.i] = used[nw.i] = true;
    var r1 = old.i + 2, r2 = nw.i + 2;
    sh.getRange(r1, 1).setValue(nw.date);
    if (nw.st === 'Сыгран' && nw.hg !== '' && nw.ag !== '') sh.getRange(r1, 5, 1, 3).setValues([[nw.hg, nw.ag, nw.ot === true || String(nw.ot).toUpperCase() === 'TRUE']]);
    sh.getRange(r2, 1, 1, 7).clearContent();                                  // формулы статуса/очков (B, H:J) в пустой строке дают ""
    // «прогнозы»: старой строке — новая дата; дубль на новую дату (если успел появиться) — очистить
    var pr = ss.getSheetByName('прогнозы');
    if (pr && pr.getLastRow() >= 2) {
      var pv = pr.getRange(2, 1, pr.getLastRow() - 1, 3).getValues(), pOld = -1, pNew = -1;
      pv.forEach(function (r, i) {
        if (!(r[0] instanceof Date) || String(r[1]).trim() !== old.h || String(r[2]).trim() !== old.a) return;
        var k = sheetDayKey_(r[0]); if (k === old.d) pOld = i + 2; else if (k === nw.d) pNew = i + 2;
      });
      if (pOld > 0) {
        pr.getRange(pOld, 1).setValue(nw.date);
        if (pNew > 0) pr.getRange(pNew, 1, 1, 3).clearContent();
      }
    }
    moved.push(old.h + ' — ' + old.a + ': ' + old.d.slice(8, 10) + '.' + old.d.slice(5, 7) + ' → ' + nw.d.slice(8, 10) + '.' + nw.d.slice(5, 7));
  });
  return moved;
}

/* ── Поправка формы в прогнозе: включается вручную (решает владелец таблицы) ──
 * По 614 матчам двух прошлых сезонов форма ухудшала прогноз и была выключена (MODEL_USE_FORM = false).
 * В начале сезона 2026/27 по 37 честным прогнозам КХЛ (18–26.09) с формой: угадано 70% против 57%, Brier 0.232 против 0.245
 * (выигрыш есть во всех 5000 бутстреп-выборках). Вероятная причина — стартовые рейтинги разведены шире реального,
 * и форма быстрее исправляет перекос, чем Elo. Проверять заново каждые 2–3 недели: к середине сезона эффект может исчезнуть. */
function modelUseForm_() {
  var v = PropertiesService.getScriptProperties().getProperty('MODEL_USE_FORM');
  return v === null || v === undefined ? MODEL_USE_FORM : v === '1';
}
function modelFormSet_(on) {
  var pp = PropertiesService.getScriptProperties(), log = [];
  try { log = JSON.parse(pp.getProperty('MODEL_FORM_LOG') || '[]'); } catch (e) { log = []; }
  log.push([todayKey_(), on ? 1 : 0]);                                        // с какого дня прогнозы считаются с формой (для честной проверки)
  pp.setProperty('MODEL_FORM_LOG', JSON.stringify(log.slice(-50)));
  pp.setProperty('MODEL_USE_FORM', on ? '1' : '0');
  var sh = SpreadsheetApp.getActive().getSheetByName('прогнозы');
  var n = sh ? applyProbabilityFormula_(sh) : 0;
  uiAlert_('Поправка формы ' + (on ? 'ВКЛЮЧЕНА' : 'выключена') + ' в прогнозе. Формула шансов обновлена в ' + n + ' несыгранных матчах; сыгранные прогнозы не тронуты.' +
    '\n\nПроверка точности с формой и без неё — меню «НХЛ-парсер» → 🔧 Проверки → «Поправка формы: проверить на сыгранных матчах».');
}
function modelFormOn_() { modelFormSet_(true); }
function modelFormOff_() { modelFormSet_(false); }

/** Бесплатная проверка: как угадывали бы честные прогнозы этого сезона с поправкой формы и без неё. */
function modelFormCheck_() {
  var ss = SpreadsheetApp.getActive(), pr = ss.getSheetByName('прогнозы'), rs = ss.getSheetByName(SHEET_RESULTS);
  if (!pr || !rs || pr.getLastRow() < 2) { uiAlert_('Нет листов «прогнозы» / «результаты матчей».'); return; }
  var M3 = Number(pr.getRange('M3').getValue()) || 90, formOn = modelUseForm_(), res = {}, log = [];
  try { log = JSON.parse(PropertiesService.getScriptProperties().getProperty('MODEL_FORM_LOG') || '[]'); } catch (e) { log = []; }
  var inclForm = function (k) { var v = MODEL_USE_FORM; log.forEach(function (x) { if (x[0] <= k) v = !!x[1]; }); return v; };   // была ли форма в формуле на дату матча
  rs.getRange(2, 1, rs.getLastRow() - 1, 6).getValues().forEach(function (r) {
    if (r[0] instanceof Date && String(r[1]).trim() === 'Сыгран') res[sheetDayKey_(r[0]) + '|' + String(r[2]).trim() + '|' + String(r[3]).trim()] = Number(r[4]) > Number(r[5]) ? 1 : 0;
  });
  var cl = function (q) { return Math.min(0.92, Math.max(0.08, q)); }, a = { n: 0, b0: 0, b1: 0, c0: 0, c1: 0 };
  pr.getRange(2, 1, pr.getLastRow() - 1, Math.max(COL_INTEGRITY, 29)).getValues().forEach(function (r) {
    var mark = String(r[10] || ''), d = Number(r[3]), ac = Number(r[28]) || 0;
    if ((mark !== '✅' && mark !== '❌') || String(r[COL_INTEGRITY - 1]).trim() === 'нет' || !(d > 0 && d < 1) || !(r[0] instanceof Date)) return;
    var y = res[sheetDayKey_(r[0]) + '|' + String(r[1]).trim() + '|' + String(r[2]).trim()]; if (y === undefined) return;
    var x = M3 * Math.log(d / (1 - d)) / Math.LN10;
    var had = inclForm(sheetDayKey_(r[0]));
    var p0 = had ? cl(1 / (1 + Math.pow(10, -(x - ac) / M3))) : d, p1 = had ? d : cl(1 / (1 + Math.pow(10, -(x + ac) / M3)));   // без формы / с формой
    a.n++; a.b0 += (p0 - y) * (p0 - y); a.b1 += (p1 - y) * (p1 - y); a.c0 += (p0 >= 0.5) === (y === 1) ? 1 : 0; a.c1 += (p1 >= 0.5) === (y === 1) ? 1 : 0;
  });
  if (!a.n) { uiAlert_('Пока нет сыгранных матчей с честным прогнозом.'); return; }
  var f = function (x) { return Math.round(x * 10000) / 10000; }, pc = function (x) { return Math.round(x / a.n * 1000) / 10 + '%'; };
  uiAlert_('Честных прогнозов этого сезона: ' + a.n + '. Сейчас поправка формы ' + (formOn ? 'ВКЛЮЧЕНА' : 'выключена') + '.\n\n' +
    'Без формы: угадано ' + pc(a.c0) + ', Brier ' + f(a.b0 / a.n) + '\nС формой: угадано ' + pc(a.c1) + ', Brier ' + f(a.b1 / a.n) +
    '\n\nBrier — средняя ошибка вероятности, меньше — лучше (0.25 — монетка). Включить или выключить: меню «НХЛ-парсер» → Настройки → «Поправка формы: …».');
}

/* ==========================================================================
 * 🎬 ВИДЕО ЭКСПЕРТОВ (YouTube) → РАСКЛАД СИЛ → СТАРТОВЫЙ РЕЙТИНГ
 *
 *  • Лист «Видео_эксперты»: ссылки на открытые ролики YouTube — вставляйте в колонку A на свободную строку.
 *    Проще — кнопка «🎬 Вставить видео»: спросит ссылку, впишет её сюда и сразу отдаст ролик Gemini.
 *    Ролик про другую лигу (НХЛ в таблице КХЛ и наоборот) узнаётся по первым двум кускам — дальше лимит не тратится.
 *    Разбираются только новые ролики; чтобы разобрать ролик заново — очистите его ячейку «Статус».
 *  • Gemini (тот же ключ GEMINI_KEY) «смотрит» ролик по ссылке — скачивать ничего не нужно. Длинный ролик режется на
 *    куски по 15 минут; прогресс сохраняется; перегрузка или лимит Google — продолжение само через 10/30 минут.
 *    Бесплатный лимит Google — до 8 часов роликов YouTube в сутки.
 *  • Лист «Видео_разбор» — что сказано о каждой команде (место в списке эксперта, оценка 1–10, плюсы, минусы, вратари, минута).
 *  • Лист со сводкой (PRESEASON_SHEET) — по командам и ПРЕДЛАГАЕМЫЙ стартовый рейтинг:
 *      внутри каждого списка, который выстраивает эксперт (дивизион, конференция или вся лига), команды встают
 *      по его местам (мест нет — по оценке 1–10) и получают их же нынешние стартовые рейтинги в этом порядке:
 *      средний уровень и разброс не меняются — меняется только порядок. Несколько роликов — среднее.
 *      Итог = 2/3 нынешнего стартового рейтинга + 1/3 «по экспертам». Цифру можно поправить руками.
 *  • В модель это попадает САМО через минуту после разбора (см. «Видео в расчётах» ниже): расклад — в стартовый рейтинг,
 *    новости о травмах, вратарях и форме — в поправки на неделю. «Вернуть прежний стартовый рейтинг» выключает автоучёт.
 *    Прогнозы сыгранных матчей заморожены и не меняются; Elo пересчитывается с начала сезона и дальше
 *    считается только по результатам.
 *  • Любой ролик (расклад, подкаст, обзор, пресс-конференция): по каждой команде — травмы, переходы, вратари, тренер
 *    и тактика, форма, ожидания эксперта. Это идёт в досье команд и агенту к матчу (VIDEO_CONTEXT_DAYS дней).
 *  • Прогнозы эксперта на конкретные матчи — лист «Прогнозы_экспертов»: после матча отмечается, угадал ли он,
 *    и рядом — угадала ли модель на том же матче. Так видно, кому из экспертов стоит доверять.
 * ==========================================================================*/
var VIDEO_SHEET = 'Видео_эксперты';
var VIDEO_RAW_SHEET = 'Видео_разбор';
var VIDEO_SEASON = '2026/27';
var VIDEO_CLIP_SEC = 900;                 // кусок ролика на один запрос, сек
var VIDEO_FPS = 0.2;                      // кадр раз в 5 секунд: важна речь, картинка почти не нужна (меньше токенов)
var VIDEO_WEIGHT = 1 / 3;                 // доля мнения экспертов в стартовом рейтинге
var VIDEO_TIME_BUDGET_MS = 270000;        // сколько работать за один запуск (у Apps Script лимит 6 минут)
var VIDEO_CONTEXT_DAYS = 45;              // сколько дней после разбора мнение экспертов показывать агенту
var PRESEASON_BACKUP_PROP = 'PRESEASON_BACKUP';
var RAW_COLS = 21;                        // «Видео_разбор»: …, Минута, Место (число), Список эксперта, Травмы, Переходы, Тренер, Форма, Ожидания, Тип ролика
var PRE_PROP_COL = 12;                    // сводка: колонка «С учётом видео»
var PRE_COLS = 21;
var VIDEO_BLIND_MAX_SEC = 4 * 3600;       // длина ролика неизвестна — идём кусками, но не дальше 4 часов
var PICKS_SHEET = 'Прогнозы_экспертов';
var PICKS_COLS = 15;
var PICKS_WAIT_DAYS = 21;                 // матч без даты ищем в течение 3 недель после разбора

var VIDEO_START_MS = 150000;              // новый кусок ролика — только в первые 2,5 минуты запуска (кусок идёт до 2 минут)
var VIDEO_DEADLINE_MS = 290000;           // к этой минуте запуска — никаких повторов запроса (лимит Apps Script — 6 минут)
var VIDEO_TWEAK_MAX = 15;                 // предел поправки из роликов, очков рейтинга (+25 ≈ +3,5% к шансам)
var VIDEO_TWEAK_DAYS = 7;                 // сколько дней после ролика действует поправка из него
var VIDEO_TWEAK_REASON = 'видео экспертов';   // причина на листе «Мои поправки»: по ней табло покажет, помогают ли
var PRESEASON_APPLIED_PROP = 'PRESEASON_APPLIED'; // какой стартовый рейтинг расклад поставил в прошлый раз
var VIDEO_AUTO_OFF_PROP = 'VIDEO_AUTO_OFF';   // «да» — видео в расчёты само не идёт (после «Вернуть прежний стартовый рейтинг»)
var VIDEO_OTHER_MAX = 2;                  // столько кусков подряд «ролик про другую лигу» — и хватит тратить лимит

/** Ссылка, которую Gemini понимает надёжнее всего: youtube.com/watch?v=ID (без youtu.be и хвостов ?si=…). */
function videoCanon_(id) { return 'https://www.youtube.com/watch?v=' + id; }

/** Другая лига: Gemini назвал лигу ролика, и это не лига этой таблицы. */
function videoOtherLeague_(s) {
  var l = String(s || '').toUpperCase().replace(/NHL/g, 'НХЛ').replace(/KHL/g, 'КХЛ');
  return !!l && l.indexOf(VIDEO_LEAGUE) < 0 && /НХЛ|КХЛ|ВХЛ|МХЛ|AHL|АХЛ|ДРУГ|OTHER/.test(l);
}
function videoImpact_(x) {
  var n = x === null || x === undefined || x === '' ? NaN : Number(x);
  return isFinite(n) && Math.round(n) ? Math.max(-VIDEO_TWEAK_MAX, Math.min(VIDEO_TWEAK_MAX, Math.round(n))) : '';
}
function videoOtherName_() { return VIDEO_LEAGUE === 'КХЛ' ? 'НХЛ' : 'КХЛ'; }

/** Счётчики «пустых» кусков подряд живут между запусками (раньше обнулялись, и ролик без команд шёл до 4 часов). */
function videoRunState_(id, st) {
  var p = PropertiesService.getScriptProperties(), k = 'VIDEO_RUN_' + id;
  if (st === undefined) { try { return JSON.parse(p.getProperty(k) || 'null') || { empty: 0, other: 0, league: '' }; } catch (e) { return { empty: 0, other: 0, league: '' }; } }
  if (st === null) p.deleteProperty(k); else p.setProperty(k, JSON.stringify(st));
}

function videoIdOf_(url) { var m = String(url || '').match(/(?:[?&]v=|youtu\.be\/|shorts\/|live\/|embed\/)([A-Za-z0-9_-]{11})/); return m ? m[1] : null; }
function videoMmss_(s) { s = Math.max(0, Math.round(Number(s) || 0)); var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60; return (h ? h + ':' + ('0' + m).slice(-2) : m) + ':' + ('0' + x).slice(-2); }

/** Лист со ссылками: [{row, url, id, who, status, done, len}] */
function videoList_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(VIDEO_SHEET);
  if (!sh) {
    sh = ss.insertSheet(VIDEO_SHEET);
    sh.getRange(1, 1, 1, 9).setValues([['Ссылка на ролик YouTube (открытый)', 'Эксперт / канал', 'Статус', 'Разобрано, сек', 'Длина, сек', 'Команд найдено', 'Разобрано (МСК)', 'Ответ Gemini (для проверки)', 'Дата ролика']]).setFontWeight('bold');
    sh.getRange(2, 1, VIDEO_DEFAULT.length, 1).setValues(VIDEO_DEFAULT.map(function (u) { return [u]; }));
    try { sh.setColumnWidth(1, 330); sh.setColumnWidth(2, 220); sh.setColumnWidth(3, 200); } catch (e) {}
  }
  var n = sh.getLastRow() - 1;
  if (n < 1) return { sh: sh, list: [] };
  // Таблицы умеют прятать адрес под подписью («Лидеры и аутсайдеры НХЛ…») — тогда в тексте ячейки ролика нет,
  // и адрес надо доставать из самой ссылки. Иначе строка молча выпадает из разбора.
  var rich = [];
  try { rich = sh.getRange(2, 1, n, 1).getRichTextValues(); } catch (e) { rich = []; }
  var linkOf = function (i) {
    var v = rich[i] && rich[i][0];
    if (!v) return '';
    var u = '';
    try { u = v.getLinkUrl() || ''; } catch (e) { u = ''; }
    if (u) return u;
    try { (v.getRuns() || []).forEach(function (run) { if (!u) { try { u = run.getLinkUrl() || ''; } catch (e2) {} } }); } catch (e3) {}
    return u;
  };
  var list = sh.getRange(2, 1, n, 6).getValues().map(function (r, i) {
    var text = String(r[0]).trim(), id = videoIdOf_(text), url = text;
    if (!id) { var u = linkOf(i); if (u) { id = videoIdOf_(u); url = u; } }
    return { row: i + 2, url: url, id: id, who: String(r[1] || '').trim(), status: String(r[2] || ''), done: Number(r[3]) || 0, len: Number(r[4]) || 0, found: Number(r[5]) || 0 };
  }).filter(function (v) { return v.id; });
  return { sh: sh, list: list };
}

/** Длина, название и автор ролика со страницы YouTube (бесплатно). Не вышло — {len: 0}. */
function videoInfo_(id) {
  var out = { len: 0, title: '', author: '', pub: '' };
  try {
    // cookie согласия: без него YouTube может отдать страницу «примите условия» без данных о ролике
    var r = UrlFetchApp.fetch('https://www.youtube.com/watch?v=' + id + '&hl=ru&bpctr=9999999999&has_verified=1', { muteHttpExceptions: true,
      headers: { 'User-Agent': SPORTS_UA['User-Agent'], 'Accept-Language': 'ru', 'Cookie': 'CONSENT=YES+cb.20240101-00-p0.ru+FX+000; SOCS=CAI' } });
    if (r.getResponseCode() !== 200) return out;
    var t = r.getContentText(), m = t.match(/"lengthSeconds":"(\d+)"/), ms = t.match(/"approxDurationMs":"(\d+)"/);
    var iso = t.match(/itemprop="duration"\s+content="PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"/);
    out.len = m ? Number(m[1]) : ms ? Math.round(Number(ms[1]) / 1000) : iso ? (Number(iso[1] || 0) * 3600 + Number(iso[2] || 0) * 60 + Number(iso[3] || 0)) : 0;
    var un = function (s) { try { return JSON.parse('"' + s + '"'); } catch (e) { return s; } };
    var vd = t.indexOf('"videoDetails"'), part = vd >= 0 ? t.slice(vd, vd + 20000) : '';
    var tm = part.match(/"title":"((?:[^"\\]|\\.)*)"/), am = part.match(/"author":"((?:[^"\\]|\\.)*)"/);
    if (tm) out.title = un(tm[1]);
    if (am) out.author = un(am[1]);
    var pd = t.match(/"publishDate":"(\d{4}-\d\d-\d\d)/) || t.match(/"uploadDate":"(\d{4}-\d\d-\d\d)/) || t.match(/itemprop="datePublished"\s+content="(\d{4}-\d\d-\d\d)/);
    if (pd) out.pub = pd[1];
  } catch (e) {}
  return out;
}

function videoPrompt_(from, to) {
  var names = [];
  try { names = Object.keys(preseasonStartRatings_(SpreadsheetApp.getActive())); } catch (e) { names = []; }
  var frag = to ? 'фрагмент ролика с ' + videoMmss_(from) + ' по ' + videoMmss_(to) : 'ролик';
  return 'Это ' + frag + ' о хоккее (' + VIDEO_LEAGUE + ', сезон ' + VIDEO_SEASON + '). Это может быть что угодно: расклад сил по местам, подкаст с новостями, ' +
    'обзор матча, превью тура, прогнозы на матчи, пресс-конференция, интервью.\n' +
    'Задача — вытащить всё, что поможет прогнозировать матчи ' + VIDEO_LEAGUE + '.\n' +
    'ПРАВИЛА: только то, что прозвучало или показано в ролике; ничего не добавляй от себя и по памяти. Нет данных — пустая строка "" или null. ' +
    'Команды из других лиг (сборные, НХЛ/КХЛ — если это не ' + VIDEO_LEAGUE + ', молодёжные лиги) не включай.\n' +
    (names.length ? 'Названия команд — СТРОГО из этого списка: ' + names.join(', ') + '.\n' : '') +
    'teams — КАЖДАЯ команда ' + VIDEO_LEAGUE + ', о которой в ' + (to ? 'этом фрагменте' : 'ролике') + ' сказано что-то существенное:\n' +
    '  injuries — кто травмирован, дисквалифицирован или не играет и на сколько; roster — приходы, уходы, обмены, аренды, вызовы из фарма; ' +
    'goalie — кто в воротах, конкуренция вратарей; coach — тренер, тактика, звенья, большинство; form — как команда играет сейчас (по словам автора); ' +
    'outlook — чего автор ждёт от команды; plus / minus — сильные и слабые стороны.\n' +
    '  impact — целое число от -' + VIDEO_TWEAK_MAX + ' до ' + VIDEO_TWEAK_MAX + ': насколько сказанное в ролике (травмы и возвращения, вратари, переходы, форма, тренер) ' +
    'меняет силу команды в БЛИЖАЙШИХ матчах по сравнению с её обычным уровнем. -' + VIDEO_TWEAK_MAX + ' — нет основного вратаря и нескольких лидеров; ' +
    '-5 — выбыл один важный игрок; +5 — вернулся лидер; 0 — не меняет или неясно. Оценка общей силы на сезон сюда НЕ входит (она — в score). ' +
    'impact_why — коротко, почему (до 100 знаков).\n' +
    '  Если автор расставляет команды по местам: group — какой список (дивизион, конференция или «вся лига»), place_num — место целым числом (1 — первое); ' +
    'если идёт по порядку мест (например, с последнего к первому) — место следует из порядка; у разных команд одного списка места разные. Иначе place_num = null.\n' +
    '  score — оценка силы команды по словам автора от 1 до 10 (10 — главный претендент на титул, 5 — борьба за плей-офф, 1 — худшая команда лиги); ' +
    'согласуется с местом. Если автор силу не оценивает — null.\n' +
    'match_picks — ТОЛЬКО когда автор прямо говорит, кто победит в конкретном предстоящем матче: хозяева, гости, дата (если названа), за кого он, ' +
    'уверенность и почему. Победа — с учётом овертайма и буллитов.\n' +
    'Верни JSON строго такого вида (тексты на русском, каждое поле до 200 знаков):\n' +
    '{"author":"кто ведёт ролик, если назван","league":"о какой лиге в основном ' + (to ? 'этот фрагмент' : 'ролик') + ': КХЛ, НХЛ, другая или \"\"",' +
    '"video_type":"расклад / подкаст-новости / обзор матча / превью / прогнозы на матчи / пресс-конференция / другое",' +
    '"clip_empty":' + (to ? 'true, если этого фрагмента в ролике нет (он за концом ролика), иначе false' : 'false') + ',' +
    '"teams":[{"team":"' + (names.length ? 'название из списка' : 'полное название клуба') + '","group":"","place_num":null,"score":null,"place":"как автор сказал о месте, или \"\"",' +
    '"playoff":"да, нет, на грани или \"\"","injuries":"","roster":"","goalie":"","coach":"","form":"","outlook":"","plus":"","minus":"","impact":0,"impact_why":"",' +
    '"time":"мм:сс от начала всего ролика, где начинается разговор о команде"}],' +
    '"match_picks":[{"home":"хозяева","away":"гости","date":"дд.мм или \"\"","pick":"название команды, за которую автор","confidence":"низкая / средняя / высокая","reason":"почему","time":"мм:сс"}]}';
}

/** Один запрос к Gemini с роликом (или его куском). {author, teams:[...], model} */
function videoGeminiClip_(url, from, to, deadline) {
  var p = agentProps_(), key = p.getProperty('GEMINI_KEY');
  if (!key) throw new Error('нет ключа GEMINI_KEY');
  var model = videoModel_();
  var send = function (simple, m) {
    var part = { fileData: { fileUri: url } };
    if (to) part.videoMetadata = simple ? { startOffset: from + 's', endOffset: to + 's' } : { startOffset: from + 's', endOffset: to + 's', fps: VIDEO_FPS };
    else if (!simple) part.videoMetadata = { fps: VIDEO_FPS };
    var gc = { temperature: 0.1, responseMimeType: 'application/json' };
    if (!simple) gc.mediaResolution = 'MEDIA_RESOLUTION_LOW';
    return UrlFetchApp.fetch('https://generativelanguage.googleapis.com/v1beta/models/' + m + ':generateContent?key=' + encodeURIComponent(key), {
      method: 'post', contentType: 'application/json', muteHttpExceptions: true,
      payload: JSON.stringify({ contents: [{ role: 'user', parts: [part, { text: videoPrompt_(from, to) }] }], generationConfig: gc })
    });
  };
  // Перегрузка Google (500/502/503/504) — временная: повторяем с паузой, затем пробуем запасную модель Flash.
  var busy = function (c) { return c === 500 || c === 502 || c === 503 || c === 504; };
  var models = [model], alt = videoAltModel_(model), resp = null;
  if (alt) models.push(alt);
  for (var mi = 0; mi < models.length; mi++) {
    if (mi && deadline && Date.now() > deadline) break;                     // на запасную модель времени уже нет
    for (var attempt = 0; attempt < 3; attempt++) {
      if (attempt && deadline && Date.now() + 10000 * attempt > deadline) break;   // повтор не успеет до лимита 6 минут
      if (attempt) Utilities.sleep(10000 * attempt);
      resp = send(false, models[mi]);
      if (resp.getResponseCode() === 400) resp = send(true, models[mi]);  // модель не понимает fps/разрешение — без них
      if (!busy(resp.getResponseCode())) break;
    }
    if (resp.getResponseCode() === 429 && mi < models.length - 1) continue;   // лимит у этой модели — у запасной он свой
    if (!busy(resp.getResponseCode())) { model = models[mi]; break; }
  }
  var code = resp.getResponseCode(), txt = resp.getContentText();
  if (busy(code)) throw new Error('Gemini перегружен (' + code + ', ' + models.join(' и ') + ') — продолжу позже');
  if (code === 429) {
    if (/PerDay|per day|daily|YouTube/i.test(txt)) throw new Error('дневной лимит Gemini на видео исчерпан (429) — продолжу после сброса');
    throw new Error('лимит Gemini в минуту (429) — продолжу позже');
  }
  if (code !== 200) throw new Error('Gemini (' + model + ') ответил кодом ' + code + ': ' + txt.slice(0, 300));
  var body = JSON.parse(txt), cand = (body.candidates || [])[0] || {};
  var out = ((cand.content || {}).parts || []).map(function (x) { return x.text || ''; }).join('');
  if (!out) throw new Error('Gemini вернул пустой ответ' + (cand.finishReason ? ' (' + cand.finishReason + ')' : '') + (body.promptFeedback ? ': ' + JSON.stringify(body.promptFeedback).slice(0, 200) : ''));
  var obj;
  try { obj = JSON.parse(out); } catch (e) { var j = out.match(/\{[\s\S]*\}/); obj = j ? JSON.parse(j[0]) : {}; }
  if (Array.isArray(obj)) obj = { teams: obj };
  var teams = videoTeams_(obj.teams || obj.команды), picks = videoPicks_(obj.match_picks);
  return { author: String(obj.author || ''), league: String(obj.league || '').slice(0, 40), type: String(obj.video_type || '').slice(0, 40), clipEmpty: obj.clip_empty === true,
    teams: teams, picks: picks, unknown: (teams.unknown || []).concat(picks.unknown || []), total: Array.isArray(obj.teams) ? obj.teams.length : 0, model: model, raw: out };
}

/** Модель для видео: свойство GEMINI_VIDEO_MODEL; иначе полноценная Flash (lite путает места и оценки) — ищем один раз и запоминаем. */
function videoModel_() {
  var p = agentProps_(), m = p.getProperty('GEMINI_VIDEO_MODEL');
  if (m) return m;
  var pick = null;
  try {
    var resp = UrlFetchApp.fetch('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200&key=' + encodeURIComponent(p.getProperty('GEMINI_KEY')), { muteHttpExceptions: true });
    if (resp.getResponseCode() === 200) {
      var names = (JSON.parse(resp.getContentText()).models || []).filter(function (x) {
        return (x.supportedGenerationMethods || []).indexOf('generateContent') !== -1 && /flash/i.test(x.name) && !/lite|image|tts|audio|live|exp|preview/i.test(x.name);
      }).map(function (x) { return x.name.replace(/^models\//, ''); });
      pick = names.indexOf('gemini-flash-latest') >= 0 ? 'gemini-flash-latest' : names.sort().reverse()[0] || null;
    }
  } catch (e) { pick = null; }
  if (!pick) return agentGeminiModel_();
  p.setProperty('GEMINI_VIDEO_MODEL', pick);
  return pick;
}

/** Запасная модель Flash (не lite) на случай перегрузки основной: другая версия — другие серверы. '' — нет такой. */
function videoAltModel_(current) {
  var p = agentProps_(), a = p.getProperty('GEMINI_VIDEO_ALT');
  if (a !== null) return a === '-' || a === current ? '' : a;
  var pick = '';
  try {
    var resp = UrlFetchApp.fetch('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200&key=' + encodeURIComponent(p.getProperty('GEMINI_KEY')), { muteHttpExceptions: true });
    if (resp.getResponseCode() !== 200) return '';
    pick = (JSON.parse(resp.getContentText()).models || []).filter(function (x) {
      return (x.supportedGenerationMethods || []).indexOf('generateContent') !== -1 && /flash/i.test(x.name) && !/lite|image|tts|audio|live|exp|preview/i.test(x.name);
    }).map(function (x) { return x.name.replace(/^models\//, ''); }).filter(function (n) { return n !== current && /^gemini-\d/.test(n); }).sort().reverse()[0] || '';
  } catch (e) { return ''; }
  p.setProperty('GEMINI_VIDEO_ALT', pick || '-');
  return pick;
}

/** Английские написания клубов КХЛ → русские (если Gemini ответит по-английски). */
var VIDEO_EN_NAMES_ = { 'lokomotiv': 'Локомотив', 'lokomotiv yaroslavl': 'Локомотив', 'ska': 'СКА', 'ska saint petersburg': 'СКА', 'ska st. petersburg': 'СКА', 'cska': 'ЦСКА', 'cska moscow': 'ЦСКА',
  'metallurg': 'Металлург', 'metallurg magnitogorsk': 'Металлург', 'avangard': 'Авангард', 'avangard omsk': 'Авангард', 'ak bars': 'Ак Барс', 'ak bars kazan': 'Ак Барс',
  'dynamo moscow': 'Динамо Москва', 'dinamo moscow': 'Динамо Москва', 'dinamo minsk': 'Динамо Минск', 'dynamo minsk': 'Динамо Минск', 'spartak': 'Спартак', 'spartak moscow': 'Спартак',
  'traktor': 'Трактор', 'traktor chelyabinsk': 'Трактор', 'avtomobilist': 'Автомобилист', 'avtomobilist yekaterinburg': 'Автомобилист', 'torpedo': 'Торпедо', 'torpedo nizhny novgorod': 'Торпедо',
  'severstal': 'Северсталь', 'severstal cherepovets': 'Северсталь', 'salavat yulaev': 'Салават Юлаев', 'salavat yulaev ufa': 'Салават Юлаев', 'sibir': 'Сибирь', 'sibir novosibirsk': 'Сибирь',
  'neftekhimik': 'Нефтехимик', 'neftekhimik nizhnekamsk': 'Нефтехимик', 'amur': 'Амур', 'amur khabarovsk': 'Амур', 'admiral': 'Адмирал', 'admiral vladivostok': 'Адмирал',
  'lada': 'Лада', 'lada togliatti': 'Лада', 'sochi': 'Сочи', 'barys': 'Барыс', 'barys astana': 'Барыс', 'shanghai dragons': 'Шанхайские Драконы', 'kunlun red star': 'Шанхайские Драконы' };


function videoTeams_(arr) {
  var clip = function (x, n) { return String(x === null || x === undefined ? '' : x).replace(/\s+/g, ' ').trim().slice(0, n); };
  var unknown = [];
  var out = (Array.isArray(arr) ? arr : []).map(function (t) {
    var ru = videoTeamRu_(t && t.team), sc = t && t.score !== null && t.score !== '' ? Number(t.score) : NaN;
    if (!ru && t && t.team) unknown.push(clip(t.team, 40));
    var pn = t && t.place_num !== null && t.place_num !== '' ? Number(t.place_num) : NaN;
    return ru ? { team: ru, score: isFinite(sc) && sc >= 1 && sc <= 10 ? Math.round(sc * 10) / 10 : '', pn: isFinite(pn) && pn >= 1 && pn <= 40 ? Math.round(pn) : '',
      group: clip(t.group, 60), place: clip(t.place, 80), playoff: clip(t.playoff, 20), plus: clip(t.plus, 250), minus: clip(t.minus, 250), goalie: clip(t.goalie, 200),
      injuries: clip(t.injuries, 250), roster: clip(t.roster, 250), coach: clip(t.coach, 250), form: clip(t.form, 250), outlook: clip(t.outlook, 250), time: clip(t.time, 10),
      impact: videoImpact_(t.impact), why: clip(t.impact_why, 120) } : null;
  }).filter(Boolean);
  out.unknown = unknown;                                   // названия, которые не нашлись в справочнике — покажем в статусе
  return out;
}

/** Прогнозы эксперта на матчи: [{home, away, pick, date, conf, reason, time}] (только с узнанными командами). */
function videoPicks_(arr) {
  var clip = function (x, n) { return String(x === null || x === undefined ? '' : x).replace(/\s+/g, ' ').trim().slice(0, n); };
  var unknown = [];
  var out = (Array.isArray(arr) ? arr : []).map(function (p) {
    if (!p) return null;
    var h = videoTeamRu_(p.home), a = videoTeamRu_(p.away);
    if (!h && p.home) unknown.push(clip(p.home, 40));
    if (!a && p.away) unknown.push(clip(p.away, 40));
    if (!h || !a || h === a) return null;
    var w = clip(p.pick, 60), team = /^(home|хозя)/i.test(w) ? h : /^(away|гост)/i.test(w) ? a : videoTeamRu_(w);
    if (team !== h && team !== a) return null;
    return { home: h, away: a, pick: team, date: clip(p.date, 20), conf: clip(p.confidence, 20), reason: clip(p.reason, 250), time: clip(p.time, 10) };
  }).filter(Boolean);
  out.unknown = unknown;
  return out;
}

function videoRawSheet_(ss) {
  var sh = ss.getSheetByName(VIDEO_RAW_SHEET) || ss.insertSheet(VIDEO_RAW_SHEET);
  sh.getRange(1, 1, 1, RAW_COLS).setValues([['Ролик', 'Эксперт', 'Фрагмент', 'Команда', 'Оценка 1–10', 'Место', 'Плей-офф', 'Плюсы', 'Минусы', 'Вратари', 'Минута', 'Место (число)', 'Список эксперта',
    'Травмы / кто не играет', 'Переходы и состав', 'Тренер и тактика', 'Форма', 'Ожидания эксперта', 'Тип ролика',
    'Влияние на ближайшие матчи (очки рейтинга)', 'Почему (влияние)']]).setFontWeight('bold');
  return sh;
}

function videoPicksSheet_(ss) {
  var sh = ss.getSheetByName(PICKS_SHEET);
  if (!sh) {
    sh = ss.insertSheet(PICKS_SHEET);
    sh.getRange(1, 1, 1, PICKS_COLS).setValues([['Ролик', 'Эксперт', 'Разобрано (МСК)', 'Когда матч (со слов)', 'Хозяева', 'Гости', 'Эксперт за', 'Уверенность', 'Почему', 'Минута',
      'Матч в таблице', 'Счёт', 'Эксперт угадал?', 'Модель угадала?', 'Примечание']]).setFontWeight('bold');
    try { sh.setFrozenRows(1); sh.setColumnWidth(1, 200); sh.setColumnWidth(9, 280); } catch (e) {}
  }
  return sh;
}

/** Убрать прогнозы ролика (при разборе с начала заново). */
function videoPicksClear_(ss, url) {
  var sh = ss.getSheetByName(PICKS_SHEET);
  if (!sh || sh.getLastRow() < 2) return;
  var n = sh.getLastRow() - 1, rows = sh.getRange(2, 1, n, PICKS_COLS).getValues(), keep = rows.filter(function (r) { return String(r[0]).trim() !== url; });
  if (keep.length === rows.length) return;
  sh.getRange(2, 1, n, PICKS_COLS).clearContent();
  if (keep.length) sh.getRange(2, 1, keep.length, PICKS_COLS).setValues(keep.map(function (r) { r[9] = r[9] ? "'" + r[9] : ''; return r; }));
}

/** Убрать из разбора строки ролика (при разборе с начала заново). */
function videoRawClear_(sh, url) {
  var n = sh.getLastRow() - 1;
  if (n < 1) return;
  var rows = sh.getRange(2, 1, n, RAW_COLS).getValues(), keep = rows.filter(function (r) { return String(r[0]).trim() !== url; });
  if (keep.length === rows.length) return;
  sh.getRange(2, 1, n, RAW_COLS).clearContent();
  if (keep.length) sh.getRange(2, 1, keep.length, RAW_COLS).setValues(keep.map(function (r) { r[10] = r[10] ? "'" + r[10] : ''; return r; }));
}

/** Кнопка и продолжение: разобрать все неразобранные ролики. */
function videoAnalyzeAll_(auto) {
  auto = auto === true;
  var ss = SpreadsheetApp.getActive(), p = agentProps_();
  if (!p.getProperty('GEMINI_KEY')) { if (!auto) uiAlert_('Нужен ключ Gemini: свойство GEMINI_KEY в настройках проекта Apps Script (как для агента).'); return { error: 'нет ключа' }; }
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) { if (!auto) uiAlert_('Разбор видео уже идёт — подождите пару минут.'); return { busy: true }; }
  var t0 = Date.now(), L = videoList_(ss), raw = videoRawSheet_(ss), errs = [], clips = 0, stop = false, stopWait = 30, model = '', picksN = 0;
  // страховка: если запуск оборвётся на лимите 6 минут (тогда код ниже не выполнится), разбор продолжится сам через 8 минут
  if (L.list.some(function (v) { return !/^готово/.test(v.status); })) videoScheduleContinue_(8);
  L.list.forEach(function (v) {
    if (/^ошибка/.test(v.status)) { v.status = ''; v.resume = true; L.sh.getRange(v.row, 3).setValue(''); }   // прошлые ошибки — продолжаем с того же места
    else if (!v.status && v.done) v.done = 0;          // статус очистили руками — разбираем ролик с начала
  });
  try {
    for (var i = 0; i < L.list.length && !stop; i++) {
      var v = L.list[i];
      if (/^готово/.test(v.status)) continue;
      if (Date.now() - t0 > VIDEO_START_MS) break;
      if (!v.len) {
        var info = videoInfo_(v.id);
        v.len = info.len;
        if (!v.who && (info.author || info.title)) { v.who = info.author + (info.title ? ' — ' + info.title : ''); L.sh.getRange(v.row, 2).setValue(v.who.slice(0, 200)); }
        if (v.len) L.sh.getRange(v.row, 5).setValue(v.len);
        if (info.pub) try { L.sh.getRange(1, 9).setValue('Дата ролика'); L.sh.getRange(v.row, 9).setValue(info.pub); } catch (e) {}
      }
      if (!v.done) { videoRawClear_(raw, v.url); videoPicksClear_(ss, v.url); v.found = 0; videoRunState_(v.id, null); }
      var rs = videoRunState_(v.id), emptyRun = rs.empty || 0;
      while (Date.now() - t0 < VIDEO_START_MS) {
        // длина неизвестна — всё равно кусками по 15 минут, пока ролик не кончится (кусок за концом — пустой или ошибка 4xx)
        var from = v.done, to = v.len ? Math.min(v.len, from + VIDEO_CLIP_SEC) : from + VIDEO_CLIP_SEC, res, ended = false;
        try { res = videoGeminiClip_(videoCanon_(v.id), from, to, t0 + VIDEO_DEADLINE_MS); }
        catch (e) {
          if (!v.len && from > 0 && /кодом 4\d\d/.test(e.message) && !/429/.test(e.message)) ended = true;
          else {
          errs.push(videoMmss_(from) + ' в ролике ' + (i + 1) + ': ' + e.message);
          if (/429|лимит|перегружен/.test(e.message)) {
            stop = true;
            var streak = /минуту/.test(e.message) ? Number(p.getProperty('VIDEO_429_STREAK') || 0) + 1 : 0;
            p.setProperty('VIDEO_429_STREAK', String(streak));
            // «минутный» лимит три раза подряд — на деле дневной: ждём сброса, а не стучимся каждые 2 минуты
            stopWait = /перегружен/.test(e.message) ? 10 : /дневной/.test(e.message) || streak >= 3 ? videoMinutesToQuotaReset_() : 2;
          }
          else L.sh.getRange(v.row, 3).setValue('ошибка: ' + e.message.slice(0, 150));
          break;
          }
        }
        if (ended) {                                         // ролик кончился раньше, чем мы думали
          L.sh.getRange(v.row, 3).setValue('готово' + (v.found ? '' : rs.other ? ' — ролик про ' + (rs.league || videoOtherName_()) + ', а не про ' + VIDEO_LEAGUE : ' — Gemini не нашёл в ролике команд'));
          v.status = 'готово'; videoRunState_(v.id, null); break;
        }
        clips++; model = res.model;
        if (clips === 1) try { p.deleteProperty('VIDEO_429_STREAK'); } catch (e) {}
        if (!v.who && res.author) { v.who = res.author; L.sh.getRange(v.row, 2).setValue(v.who.slice(0, 200)); }
        var label = videoMmss_(from) + '–' + videoMmss_(to);
        if (res.teams.length) {
          // минута — текстом (иначе таблица превращает «27:22» в «1 день 3:22»)
          var rows = res.teams.map(function (t) { return [v.url, v.who, label, t.team, t.score, t.place, t.playoff, t.plus, t.minus, t.goalie, t.time ? "'" + t.time : '', t.pn, t.group,
            t.injuries, t.roster, t.coach, t.form, t.outlook, res.type, t.impact, t.why]; });
          raw.getRange(raw.getLastRow() + 1, 1, rows.length, RAW_COLS).setValues(rows);
        }
        if (res.picks.length) {
          var ps = videoPicksSheet_(ss), now = mskNow_();
          var prow = res.picks.map(function (q) { return [v.url, v.who, now, q.date ? "'" + q.date : '', q.home, q.away, q.pick, q.conf, q.reason, q.time ? "'" + q.time : '', '', '', '', '', '']; });
          ps.getRange(ps.getLastRow() + 1, 1, prow.length, PICKS_COLS).setValues(prow);
          picksN += res.picks.length;
        }
        v.found += res.teams.length;
        v.unknown = (v.unknown || []).concat(res.unknown.filter(function (n) { return (v.unknown || []).indexOf(n) < 0; }));
        v.total = (v.total || 0) + res.total;
        try { L.sh.getRange(1, 8).setValue('Ответ Gemini (для проверки)'); L.sh.getRange(v.row, 8).setValue(String(res.raw).slice(0, 20000)); } catch (e) {}
        v.done = to;
        emptyRun = res.teams.length || res.picks.length ? 0 : emptyRun + 1;
        // ролик про другую лигу (НХЛ в таблице КХЛ и наоборот): команды этой лиги в нём не ищутся — не тратим лимит до конца ролика
        var other = !res.teams.length && !res.picks.length && videoOtherLeague_(res.league);
        rs = { empty: emptyRun, other: other ? (rs.other || 0) + 1 : 0, league: other ? res.league : rs.league };
        var wrong = !v.found && rs.other >= VIDEO_OTHER_MAX;
        // конец ролика неизвестной длины: Gemini говорит «фрагмента нет» (или ошибка 4xx выше); запасной предел — час без единой команды
        var fin = wrong || (v.len ? v.done >= v.len : (res.clipEmpty || emptyRun >= 4 || v.done >= VIDEO_BLIND_MAX_SEC));
        if (fin) videoRunState_(v.id, null); else videoRunState_(v.id, rs);
        var note = (fin && !v.found ? (wrong ? ' — ролик про ' + res.league + ', а не про ' + VIDEO_LEAGUE + ': вставьте его в таблицу ' + videoOtherName_() :
          v.total ? ' — команды не узнал' : ' — Gemini не нашёл в ролике команд') : '') + (v.unknown.length ? ' (не узнал: ' + v.unknown.slice(0, 8).join(', ') + ')' : '');
        L.sh.getRange(v.row, 3, 1, 5).setValues([[(fin ? 'готово' : 'разобрано ' + videoMmss_(v.done) + (v.len ? ' из ' + videoMmss_(v.len) : ' (длина неизвестна, идём дальше)')) + note, v.done, v.len || '', v.found, mskNow_()]]);
        if (fin && wrong) errs.push('ролик ' + (i + 1) + ' — про ' + res.league + ', а это таблица ' + VIDEO_LEAGUE + ': вставьте его в таблицу ' + videoOtherName_() +
          ' (меню «🎬 ' + videoOtherName_() + ' · Видео» → «Вставить видео»)');
        else if (fin && (!v.found || v.unknown.length)) errs.push('ролик ' + (i + 1) + ': найдено команд ' + v.found + (v.unknown.length ? ', не узнал: ' + v.unknown.slice(0, 8).join(', ') : v.total ? '' : ' — Gemini вернул пустой список (ответ — в колонке H листа «' + VIDEO_SHEET + '»)'));
        if (fin) { v.status = 'готово'; break; }
      }
    }
  } finally { lock.releaseLock(); }
  var left = L.list.filter(function (v) { return !/^готово/.test(v.status); });
  var errLeft = left.filter(function (v) { return /^ошибка/.test(String(L.sh.getRange(v.row, 3).getValue())); }).length;
  var more = left.length - errLeft > 0 && (clips > 0 || stop || Date.now() - t0 > VIDEO_START_MS);
  if (more) videoScheduleContinue_(stop ? stopWait : 1);
  var toModel = !more && clips > 0 && agentProps_().getProperty(VIDEO_AUTO_OFF_PROP) !== 'да';
  if (toModel) videoScheduleApply_();
  else try { ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'videoContinue_') ScriptApp.deleteTrigger(t); }); } catch (e) {}
  var sum = preseasonBuild_(ss);
  var msg = '🎬 Видео экспертов: разобрано кусков ' + clips + (model ? ' (' + model + ')' : '') + '. Готово роликов: ' + (L.list.length - left.length) + ' из ' + L.list.length + '.' +
    (more ? (stop ? (stopWait === 10 ? '\nGemini сейчас перегружен (это временно, на стороне Google) — продолжу сам через 10 минут, нажимать ничего не нужно.' :
      stopWait > 10 ? '\nДневной бесплатный лимит Gemini на видео исчерпан (около 8 часов роликов в сутки). Лимит сбрасывается в полночь по Калифорнии — продолжу сам около ' +
        Utilities.formatDate(new Date(Date.now() + stopWait * 60000), 'Asia/Krasnoyarsk', 'HH:mm') + ' по Красноярску, нажимать ничего не нужно. Сводки агента это не задевает — у них своя модель.' :
      '\nGemini упёрся в минутный лимит — продолжу сам через 2 минуты.') : '\nОсталось ' + (left.length - errLeft) + ' — продолжу сам через минуту, нажимать ничего не нужно.') : '') +
    (errs.length ? '\nВнимание: ' + errs.slice(0, 4).join('; ') : '') +
    '\n\nСводка (лист «' + PRESEASON_SHEET + '»): команд с местом или оценкой экспертов — ' + sum.scored + ' из ' + Object.keys(preseasonStartRatings_(ss)).length +
    '; команд, о которых есть что-то в роликах, — ' + sum.teams + ' (эти факты идут в досье команд и агенту к матчам ' + VIDEO_CONTEXT_DAYS + ' дней).' +
    (picksN ? '\nПрогнозов эксперта на матчи: ' + picksN + ' — лист «' + PICKS_SHEET + '», после матчей отмечу, угадал ли он.' : '') +
    (sum.teams && !sum.scored ? '\nМест и оценок в роликах нет (похоже, это обсуждение новостей, а не расклад по местам) — стартовый рейтинг не меняется.' : '') +
    (sum.dup && sum.dup.length ? '\n⚠ Повторяются места в дивизионе (проверьте лист «' + PRESEASON_SHEET + '», можно поправить цифры руками): ' + sum.dup.slice(0, 4).join('; ') + '.' : '') +
    (sum.changes.length ? '\nСильнее всего изменится стартовый рейтинг: ' + sum.changes.slice(0, 5).map(function (c) { return c.team + ' ' + c.cur + '→' + c.prop; }).join(', ') + '.' : '') +
    (toModel ? '\nЧерез минуту это само попадёт в расчёты: расклад мест — в стартовый рейтинг (доля видео ' + Math.round(VIDEO_WEIGHT * 100) + '%), ' +
      'новости о травмах, вратарях и форме — в поправки на ' + VIDEO_TWEAK_DAYS + ' дней (до ±' + VIDEO_TWEAK_MAX + ' очков). Итог пришлю в Telegram.' :
      more ? '' : '\nАвтоучёт видео выключен — включится кнопкой «Применить расклад к стартовому рейтингу».');
  if (!auto) uiAlert_(msg);
  else if (!more) { var to2 = p.getProperty('TG_ADMIN_ID'); if (to2) try { tg_('sendMessage', { chat_id: to2, text: msg }); } catch (e) {} }
  return { clips: clips, left: left.length, errors: errs, summary: sum, more: more };
}
function videoAnalyzeNow_() { videoAnalyzeAll_(false); }

/** Кнопка: забыть прежний разбор и разобрать все ролики заново (например, после смены модели). Применённый рейтинг не трогает. */
function videoReanalyzeNow_() {
  var ui = null; try { ui = SpreadsheetApp.getUi(); } catch (e) { ui = null; }
  if (ui && ui.alert('Разобрать все ролики заново? Прежний разбор на листе «' + VIDEO_RAW_SHEET + '» будет удалён. Стартовый рейтинг это не меняет.', ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
  var ss = SpreadsheetApp.getActive(), L = videoList_(ss), raw = videoRawSheet_(ss);
  L.list.forEach(function (v) { L.sh.getRange(v.row, 3, 1, 5).setValues([['', '', v.len || '', '', '']]); });
  if (raw.getLastRow() > 1) raw.getRange(2, 1, raw.getLastRow() - 1, RAW_COLS).clearContent();
  L.list.forEach(function (v) { videoPicksClear_(ss, v.url); });
  videoAnalyzeAll_(false);
}

/** Минут до сброса дневных лимитов Gemini (полночь по Калифорнии) + 10 минут запаса. */
function videoMinutesToQuotaReset_() {
  var hm = Utilities.formatDate(new Date(), 'America/Los_Angeles', 'HH:mm').split(':');
  return Math.max(15, 24 * 60 - (Number(hm[0]) * 60 + Number(hm[1])) + 10);
}

function videoScheduleContinue_(minutes) {
  try {
    ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'videoContinue_') ScriptApp.deleteTrigger(t); });
    ScriptApp.newTrigger('videoContinue_').timeBased().after((minutes || 1) * 60 * 1000).create();
  } catch (e) { /* нет прав на триггеры — нажать кнопку ещё раз */ }
}
function videoContinue_() {
  try { ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'videoContinue_') ScriptApp.deleteTrigger(t); }); } catch (e) {}
  try { videoAnalyzeAll_(true); } catch (e) { console.log('video: ' + e.message); }
}

/** Стартовые рейтинги из справочника: {команда: {row, val}} */
function preseasonStartRatings_(ss) {
  var sh = ss.getSheetByName(SHEET_TEAMS), out = {};
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, 3).getValues().forEach(function (r, i) {
    var t = String(r[0]).trim(), v = typeof r[2] === 'string' && /^\s*\d+([.,]\d+)?\s*$/.test(r[2]) ? Number(r[2].replace(',', '.')) : r[2];
    if (t && typeof v === 'number') out[t] = { row: i + 2, val: v };
  });
  return out;
}

function preseasonBackup_() { try { return JSON.parse(agentProps_().getProperty(PRESEASON_BACKUP_PROP) || 'null'); } catch (e) { return null; } }

/** Сводка по командам и предлагаемый стартовый рейтинг → лист сводки. {scored, teams, changes[], dup[]} */
function preseasonBuild_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var raw = ss.getSheetByName(VIDEO_RAW_SHEET), by = {}, order = [], lists = {}, listOrder = [];
  var avg = function (a) { return a.length ? a.reduce(function (x, y) { return x + y; }, 0) / a.length : null; };
  var when = {};                                            // ролик → когда разобран
  try { var L = videoList_(ss); if (L.sh.getLastRow() > 1) L.sh.getRange(2, 1, L.sh.getLastRow() - 1, 9).getValues().forEach(function (r) { when[String(r[0]).trim()] = r[8] || r[6]; }); } catch (e) {}   // дата ролика, иначе — дата разбора
  var rawRows = raw && raw.getLastRow() > 1 ? raw.getRange(2, 1, raw.getLastRow() - 1, RAW_COLS).getValues() : [];
  // кусок без названия списка: берём список этой команды в том же ролике, а если в ролике список один — его
  var gTeam = {}, gUrl = {};
  rawRows.forEach(function (r) { var g = String(r[12] || '').trim(), u = String(r[0]).trim(); if (!g) return; gTeam[u + '|' + String(r[3]).trim()] = g; (gUrl[u] = gUrl[u] || {})[g.toLowerCase()] = g; });
  rawRows.forEach(function (r) {
    var t = String(r[3]).trim(); if (!t) return;
    var url = String(r[0]).trim(), who = String(r[1] || '').split(' — ')[0] || 'ролик', grp = String(r[12] || '').trim();
    if (!grp) { var gs = gUrl[url] ? Object.keys(gUrl[url]) : []; grp = gTeam[url + '|' + t] || (gs.length === 1 ? gUrl[url][gs[0]] : ''); }
    if (!by[t]) { by[t] = { scores: [], place: [], playoff: [], plus: [], minus: [], goalie: [], injuries: [], roster: [], coach: [], form: [], outlook: [], type: [], where: [], lists: [], when: '' }; order.push(t); }
    var b = by[t];
    if (r[4] !== '' && isFinite(Number(r[4]))) b.scores.push(Number(r[4]));
    [['place', 5], ['playoff', 6], ['plus', 7], ['minus', 8], ['goalie', 9], ['injuries', 13], ['roster', 14], ['coach', 15], ['form', 16], ['outlook', 17], ['type', 18]].forEach(function (f) { var x = String(r[f[1]] || '').trim(); if (x && b[f[0]].indexOf(x) < 0) b[f[0]].push(x); });
    b.where.push(who + (r[10] ? ' ' + String(r[10]).replace(/^'/, '') : '') + ' ' + url);
    if (when[url]) b.when = when[url];
    // список эксперта = ролик + то, что он ранжирует (дивизион / конференция / вся лига)
    var key = url + '|' + grp.toLowerCase();
    if (!lists[key]) { lists[key] = { label: grp || who, members: {} }; listOrder.push(key); }
    var mem = lists[key].members[t] = lists[key].members[t] || { pns: [], scores: [] };
    if (r[11] !== '' && r[11] !== undefined && isFinite(Number(r[11]))) mem.pns.push(Number(r[11]));
    if (r[4] !== '' && isFinite(Number(r[4]))) mem.scores.push(Number(r[4]));
    if (b.lists.indexOf(key) < 0) b.lists.push(key);
  });
  var start = preseasonStartRatings_(ss), bak = preseasonBackup_() || {};
  var base = function (t) { return bak[t] !== undefined ? Number(bak[t]) : start[t] ? start[t].val : null; };   // от исходного рейтинга, без двойного учёта
  // В каждом списке: места эксперта (меньше — лучше); если мест меньше двух — оценка 1–10 (больше — лучше).
  // Нынешние рейтинги этих команд раздаются в этом порядке; одинаковые места/оценки делят рейтинги поровну.
  var mapped = {}, pnShow = {}, dup = [];
  listOrder.forEach(function (key) {
    var li = lists[key], all = Object.keys(li.members).filter(function (t) { return base(t) !== null; }).map(function (t) {
      return { team: t, pn: avg(li.members[t].pns), score: avg(li.members[t].scores), cur: base(t) };
    });
    var byPlace = all.filter(function (x) { return x.pn !== null; }), seen = {};
    byPlace.forEach(function (x) {
      pnShow[x.team] = (pnShow[x.team] || []).concat([x.pn]);
      var k = String(x.pn); if (seen[k]) dup.push(li.label + ': ' + seen[k] + ' и ' + x.team + ' — ' + k + '-е'); else seen[k] = x.team;
    });
    var list = byPlace.length >= 2 ? byPlace : all.filter(function (x) { return x.score !== null; });
    if (list.length < 2) return;
    var keyf = byPlace.length >= 2 ? function (x) { return x.pn; } : function (x) { return -x.score; };
    var vals = list.map(function (x) { return x.cur; }).sort(function (a, b) { return b - a; });
    list.sort(function (a, b) { return keyf(a) - keyf(b); });
    for (var i = 0; i < list.length;) {
      var j = i; while (j + 1 < list.length && Math.abs(keyf(list[j + 1]) - keyf(list[i])) < 1e-9) j++;
      var s = 0; for (var k = i; k <= j; k++) s += vals[k]; s /= (j - i + 1);
      for (k = i; k <= j; k++) (mapped[list[k].team] = mapped[list[k].team] || []).push(s);
      i = j + 1;
    }
  });
  var info = {}, ranked = [];
  order.forEach(function (t) {
    var x = info[t] = { team: t, cur: base(t), score: avg(by[t].scores), firstList: listOrder.indexOf(by[t].lists[0]), pnFirst: null };
    var l0 = lists[by[t].lists[0]]; if (l0 && l0.members[t].pns.length) x.pnFirst = avg(l0.members[t].pns);
    if (mapped[t] && x.cur !== null) { x.prop = Math.round((1 - VIDEO_WEIGHT) * x.cur + VIDEO_WEIGHT * avg(mapped[t])); ranked.push(x); }
  });
  var sh = ss.getSheetByName(PRESEASON_SHEET) || ss.insertSheet(PRESEASON_SHEET);
  sh.clear();
  var head = ['Команда', 'Список эксперта', 'Место в списке (эксперт)', 'Оценка силы (1–10)', 'Как сказано о месте', 'Плей-офф', 'Плюсы', 'Минусы', 'Вратари', 'Где в роликах',
    'Стартовый рейтинг (исходный)', 'С учётом видео (ставится само)', 'Изменение', 'Применено', 'Дата ролика / разбора',
    'Травмы / кто не играет', 'Переходы и состав', 'Тренер и тактика', 'Форма', 'Ожидания эксперта', 'Тип роликов'];
  sh.getRange(1, 1, 1, head.length).setValues([head]).setFontWeight('bold');
  var applied = preseasonBackup_() !== null;
  var rows = order.slice().sort(function (a, b) {
    var x = info[a], y = info[b];
    if (x.firstList !== y.firstList) return x.firstList - y.firstList;
    if (x.pnFirst !== null && y.pnFirst !== null && x.pnFirst !== y.pnFirst) return x.pnFirst - y.pnFirst;
    return (y.score || 0) - (x.score || 0);
  }).map(function (t) {
    var b = by[t], x = info[t], j2 = function (a) { return a.join(' | ').slice(0, 700); }, has = x.prop !== undefined;
    var lab = b.lists.map(function (k) { return lists[k].label; }).filter(function (v, i, a) { return a.indexOf(v) === i; }).join(' | ');
    var pn = pnShow[t] ? (pnShow[t].length === 1 ? pnShow[t][0] : pnShow[t].join(' | ')) : '';
    return [t, lab, pn, x.score === null ? '' : Math.round(x.score * 10) / 10,
      j2(b.place), j2(b.playoff), j2(b.plus), j2(b.minus), j2(b.goalie), b.where.slice(0, 4).join('\n'), x.cur === null ? '' : x.cur,
      has ? x.prop : '', has ? (x.prop - x.cur > 0 ? '+' : '') + (x.prop - x.cur) : '', applied && has && start[t] && start[t].val === x.prop ? 'да' : '', b.when || '',
      j2(b.injuries), j2(b.roster), j2(b.coach), j2(b.form), j2(b.outlook), j2(b.type)];
  });
  if (rows.length) sh.getRange(2, 1, rows.length, head.length).setValues(rows).setWrap(true).setVerticalAlignment('top');
  try { sh.setFrozenRows(1); sh.setColumnWidth(1, 120); [7, 8].forEach(function (c) { sh.setColumnWidth(c, 280); }); sh.setColumnWidth(10, 260); } catch (e) {}
  var changes = ranked.filter(function (x) { return x.prop !== x.cur; }).sort(function (a, b) { return Math.abs(b.prop - b.cur) - Math.abs(a.prop - a.cur); });
  return { scored: ranked.length, teams: order.length, changes: changes, dup: dup };
}

/** Кнопка: записать «С учётом видео» в стартовый рейтинг справочника и пересчитать Elo. Исходные значения сохраняются. */
function preseasonApply_() {
  var ss = SpreadsheetApp.getActive(), sh = ss.getSheetByName(PRESEASON_SHEET), teams = ss.getSheetByName(SHEET_TEAMS);
  if (!sh || sh.getLastRow() < 2 || !teams) { uiAlert_('Сначала: меню «🎬 НХЛ · Видео» → «Разобрать новые ролики».'); return { applied: 0 }; }
  var start = preseasonStartRatings_(ss), bak = preseasonBackup_() || {}, ch = [];
  sh.getRange(2, 1, sh.getLastRow() - 1, PRE_PROP_COL).getValues().forEach(function (r) {
    var t = String(r[0]).trim(), pv = r[PRE_PROP_COL - 1], v = Number(pv);
    if (!t || pv === '' || !isFinite(v) || !start[t]) return;
    v = Math.max(1, Math.min(100, Math.round(v)));
    if (bak[t] === undefined) bak[t] = start[t].val;
    if (v !== start[t].val) ch.push({ team: t, row: start[t].row, from: start[t].val, to: v });
  });
  if (!ch.length) { uiAlert_('Изменений нет: стартовый рейтинг уже совпадает с колонкой «С учётом видео».'); return { applied: 0 }; }
  var ui = null; try { ui = SpreadsheetApp.getUi(); } catch (e3) { ui = null; }
  var text = 'Изменить стартовый рейтинг у ' + ch.length + ' команд по раскладу экспертов (доля видео — ' + Math.round(VIDEO_WEIGHT * 100) + '%)?\n\n' +
    ch.slice().sort(function (a, b) { return Math.abs(b.to - b.from) - Math.abs(a.to - a.from); }).slice(0, 12).map(function (c) { return c.team + ': ' + c.from + ' → ' + c.to; }).join('\n') +
    (ch.length > 12 ? '\n…' : '') + '\n\nElo будет пересчитан с начала сезона и поменяет прогнозы будущих матчей; прогнозы уже сыгранных матчей заморожены и не изменятся. ' +
    'Вернуть как было — кнопкой «Вернуть прежний стартовый рейтинг».';
  if (ui && ui.alert(text, ui.ButtonSet.YES_NO) !== ui.Button.YES) return { applied: 0, canceled: true };
  agentProps_().setProperty(PRESEASON_BACKUP_PROP, JSON.stringify(bak));
  ch.forEach(function (c) { teams.getRange(c.row, 3).setValue(c.to); });
  var lastSet = {}; try { lastSet = JSON.parse(agentProps_().getProperty(PRESEASON_APPLIED_PROP) || '{}') || {}; } catch (e6) { lastSet = {}; }
  ch.forEach(function (c) { lastSet[c.team] = c.to; });
  agentProps_().setProperty(PRESEASON_APPLIED_PROP, JSON.stringify(lastSet));
  agentProps_().deleteProperty(VIDEO_AUTO_OFF_PROP);
  var eloMsg = ''; try { computeAndWriteElo_(true); eloMsg = ' Elo пересчитан.'; } catch (e4) { eloMsg = ' Elo не пересчитался: ' + e4.message + ' — нажмите «Обновить всё».'; }
  try { preseasonBuild_(ss); } catch (e5) {}
  uiAlert_('Готово: стартовый рейтинг изменён у ' + ch.length + ' команд.' + eloMsg);
  return { applied: ch.length, changes: ch };
}

/** Кнопка: вернуть стартовый рейтинг, который был до применения видео. */
function preseasonRevert_() {
  var ss = SpreadsheetApp.getActive(), bak = preseasonBackup_(), teams = ss.getSheetByName(SHEET_TEAMS);
  if (!bak || !teams) { uiAlert_('Возвращать нечего: расклад экспертов к стартовому рейтингу не применялся.'); return { reverted: 0 }; }
  var start = preseasonStartRatings_(ss), n = 0;
  Object.keys(bak).forEach(function (t) { if (start[t] && start[t].val !== Number(bak[t])) { teams.getRange(start[t].row, 3).setValue(Number(bak[t])); n++; } });
  agentProps_().deleteProperty(PRESEASON_BACKUP_PROP);
  agentProps_().deleteProperty(PRESEASON_APPLIED_PROP);
  agentProps_().setProperty(VIDEO_AUTO_OFF_PROP, 'да');
  try { computeAndWriteElo_(true); } catch (e) {}
  try { preseasonBuild_(ss); } catch (e2) {}
  uiAlert_('Стартовый рейтинг возвращён к прежнему у ' + n + ' команд, Elo пересчитан.\n\nАвтоучёт видео выключен: новые ролики в расчёты сами не пойдут ' +
    '(поправки из роликов, которые уже стоят, доживут до своей даты — их можно удалить на листе «' + SHEET_TWEAKS + '»). Включить — кнопкой «Применить расклад к стартовому рейтингу».');
  return { reverted: n };
}

/* ── 🎬 → 📈 Видео в расчётах: после разбора роликов (через минуту, отдельным запуском — Elo считается долго) ──
 *  1) расклад экспертов по местам сам идёт в стартовый рейтинг (доля VIDEO_WEIGHT), Elo пересчитывается с начала сезона;
 *     если стартовый рейтинг команды с прошлого раза поменяли руками или другой кнопкой — новое значение и есть исходное;
 *  2) новости из роликов (травмы, вратари, форма) — поправки на листе «Мои поправки» с причиной VIDEO_TWEAK_REASON:
 *     до ±VIDEO_TWEAK_MAX очков, на VIDEO_TWEAK_DAYS дней после ролика, только для несыгранных матчей.
 *     Табло на том же листе покажет, помогают ли они; выключить все поправки — меню «Мои поправки».
 *  Прошлые прогнозы заморожены и не меняются. «Вернуть прежний стартовый рейтинг» выключает автоучёт. */
function preseasonAutoApply_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var p = agentProps_(), teams = ss.getSheetByName(SHEET_TEAMS);
  if (p.getProperty(VIDEO_AUTO_OFF_PROP) === 'да' || !teams) return { applied: 0 };
  var start = preseasonStartRatings_(ss), bak = preseasonBackup_(), last = {};
  try { last = JSON.parse(p.getProperty(PRESEASON_APPLIED_PROP) || '{}') || {}; } catch (e) { last = {}; }
  if (bak) {
    Object.keys(last).forEach(function (t) { if (start[t] && start[t].val !== Number(last[t])) bak[t] = start[t].val; });
    p.setProperty(PRESEASON_BACKUP_PROP, JSON.stringify(bak));
  }
  preseasonBuild_(ss);
  var sh = ss.getSheetByName(PRESEASON_SHEET);
  if (!sh || sh.getLastRow() < 2) return { applied: 0 };
  bak = bak || {};
  var ch = [];
  sh.getRange(2, 1, sh.getLastRow() - 1, PRE_PROP_COL).getValues().forEach(function (r) {
    var t = String(r[0]).trim(), pv = r[PRE_PROP_COL - 1], v = Number(pv);
    if (!t || pv === '' || !isFinite(v) || !start[t]) return;
    v = Math.max(1, Math.min(100, Math.round(v)));
    if (bak[t] === undefined) bak[t] = start[t].val;
    last[t] = v;
    if (v !== start[t].val) ch.push({ team: t, row: start[t].row, from: start[t].val, to: v });
  });
  if (!Object.keys(bak).length) return { applied: 0 };
  p.setProperty(PRESEASON_BACKUP_PROP, JSON.stringify(bak));
  p.setProperty(PRESEASON_APPLIED_PROP, JSON.stringify(last));
  if (!ch.length) return { applied: 0 };
  ch.forEach(function (c) { teams.getRange(c.row, 3).setValue(c.to); });
  var eloErr = ''; try { computeAndWriteElo_(true); } catch (e2) { eloErr = e2.message; }
  try { preseasonBuild_(ss); } catch (e3) {}
  return { applied: ch.length, changes: ch, eloErr: eloErr };
}

/** Новости из свежих роликов → поправки на листе «Мои поправки». {set: ['Команда +5 (почему)', …]} */
function videoTweaksSync_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  if (agentProps_().getProperty(VIDEO_AUTO_OFF_PROP) === 'да') return { set: [] };
  var raw = ss.getSheetByName(VIDEO_RAW_SHEET);
  if (!raw || raw.getLastRow() < 2) return { set: [] };
  var when = {}, L = videoList_(ss);
  if (L.sh.getLastRow() > 1) {
    var lv = L.sh.getRange(2, 1, L.sh.getLastRow() - 1, 9).getValues();
    L.list.forEach(function (v) { var r = lv[v.row - 2] || []; when[v.url] = videoDate_(r[8]) || videoDate_(r[6]); });   // дата ролика, иначе — дата разбора
  }
  var now = new Date(), by = {};
  raw.getRange(2, 1, raw.getLastRow() - 1, RAW_COLS).getValues().forEach(function (r) {
    var t = String(r[3]).trim(), imp = r[19] === '' ? NaN : Number(r[19]), d = when[String(r[0]).trim()];
    if (!t || !isFinite(imp) || !imp || !d || now - d > VIDEO_TWEAK_DAYS * 86400000) return;
    var b = by[t] = by[t] || { sum: 0, n: 0, why: [], d: d };
    b.sum += imp; b.n++;
    if (r[20] && b.why.indexOf(String(r[20])) < 0) b.why.push(String(r[20]));
    if (d > b.d) b.d = d;
  });
  var teams = Object.keys(by);
  if (!teams.length) return { set: [] };
  var sh = ensureTweaksSheet_(ss), n = Math.min(TWEAK_ROWS, Math.max(sh.getLastRow() - 1, 0));
  var vals = n ? sh.getRange(2, 1, n, TWEAKS_HEADER.length).getValues() : [];
  var today = new Date(now.getFullYear(), now.getMonth(), now.getDate()), set = [];
  teams.forEach(function (t) {
    var b = by[t], delta = Math.max(-VIDEO_TWEAK_MAX, Math.min(VIDEO_TWEAK_MAX, Math.round(b.sum / b.n)));
    if (!delta) return;
    var u = new Date(b.d.getTime() + VIDEO_TWEAK_DAYS * 86400000), until = new Date(u.getFullYear(), u.getMonth(), u.getDate());
    if (until < today) return;
    var row = -1, i;
    // та же команда, та же причина и поправка ещё действует — обновляем её; иначе — новая строка (старые остаются для табло)
    for (i = 0; i < vals.length && row < 0; i++) if (String(vals[i][0]).trim() === t && String(vals[i][3]).trim() === VIDEO_TWEAK_REASON && vals[i][2] instanceof Date && vals[i][2] >= today) row = i;
    for (i = 0; i < vals.length && row < 0; i++) if (!String(vals[i][0]).trim() && String(vals[i][1]).trim() === '') row = i;
    if (row < 0) { if (vals.length >= TWEAK_ROWS) return; vals.push(TWEAKS_HEADER.map(function () { return ''; })); row = vals.length - 1; }
    var old = vals[row];
    if (String(old[0]).trim() === t && Number(old[1]) === delta && old[2] instanceof Date && old[2].getTime() === until.getTime()) return;   // уже стоит такая же
    vals[row] = [t, delta, until, VIDEO_TWEAK_REASON, mskNow_()].concat(old.slice(5));
    set.push(t + ' ' + (delta > 0 ? '+' : '') + delta + (b.why.length ? ' (' + b.why[0].slice(0, 70) + ')' : ''));
  });
  if (set.length) { sh.getRange(2, 1, vals.length, TWEAKS_HEADER.length).setValues(vals); tweaksApply_(true); }
  return { set: set };
}

/** Текст итога: что из видео попало в расчёты. verbose — отвечать и когда ничего не изменилось (кнопка). */
function videoApply_(verbose) {
  if (agentProps_().getProperty(VIDEO_AUTO_OFF_PROP) === 'да')
    return verbose ? 'Автоучёт видео выключен (после «Вернуть прежний стартовый рейтинг»). Включить — кнопкой «Применить расклад к стартовому рейтингу».' : '';
  var ss = SpreadsheetApp.getActive(), a = {}, tw = {}, lines = [];
  try { a = preseasonAutoApply_(ss); } catch (e) { lines.push('Расклад экспертов: не получилось — ' + e.message); }
  try { tw = videoTweaksSync_(ss); } catch (e2) { lines.push('Поправки из роликов: не получилось — ' + e2.message); }
  if (a.applied) lines.push('Стартовый рейтинг по раскладу экспертов изменён у ' + a.applied + ' команд: ' +
    a.changes.slice().sort(function (x, y) { return Math.abs(y.to - y.from) - Math.abs(x.to - x.from); }).slice(0, 6).map(function (c) { return c.team + ' ' + c.from + '→' + c.to; }).join(', ') +
    (a.changes.length > 6 ? '…' : '') + '.' + (a.eloErr ? ' Elo не пересчитался: ' + a.eloErr : ' Elo пересчитан.'));
  if (tw.set && tw.set.length) lines.push('Поправки из роликов на ' + VIDEO_TWEAK_DAYS + ' дней (лист «' + SHEET_TWEAKS + '»): ' + tw.set.slice(0, 8).join('; ') + (tw.set.length > 8 ? '…' : '') + '.');
  if (!lines.length) return verbose ? '🎬 Видео → прогнозы: новых изменений нет — расклад уже учтён, а свежих новостей о силе команд в роликах нет.' : '';
  return '🎬 ' + VIDEO_LEAGUE + ' · видео учтено в прогнозах\n' + lines.join('\n') +
    '\nПрошлые прогнозы не меняются. Помогают ли поправки из роликов — табло на листе «' + SHEET_TWEAKS + '» (причина «' + VIDEO_TWEAK_REASON + '»).';
}
function videoScheduleApply_() {
  try {
    ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'videoApplyRun_') ScriptApp.deleteTrigger(t); });
    ScriptApp.newTrigger('videoApplyRun_').timeBased().after(60 * 1000).create();
  } catch (e) { /* нет прав на триггеры — кнопка «Учесть видео в прогнозах сейчас» */ }
}
function videoApplyRun_() {
  try { ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'videoApplyRun_') ScriptApp.deleteTrigger(t); }); } catch (e) {}
  var msg = '';
  try { msg = videoApply_(false); } catch (e2) { msg = '🎬 Видео → прогнозы: ошибка — ' + e2.message; }
  var to = agentProps_().getProperty('TG_ADMIN_ID');
  if (msg && to) try { tg_('sendMessage', { chat_id: to, text: msg }); } catch (e3) {}
}
function videoApplyNow_() { uiAlert_(videoApply_(true)); }

/** Для агента: что эксперты говорили о командах (VIDEO_CONTEXT_DAYS дней после разбора). */
var PRESEASON_CTX_ = null;
function preseasonContext_(ss, teams, day) {
  if (!PRESEASON_CTX_) {
    PRESEASON_CTX_ = {};
    var sh = ss.getSheetByName(PRESEASON_SHEET), now = day ? new Date(day + 'T12:00:00Z') : new Date();
    if (sh && sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, PRE_COLS).getValues().forEach(function (r) {
      var t = String(r[0]).trim(); if (!t) return;
      var w = r[14], wd = w instanceof Date ? w : w ? new Date(String(w).replace(/^(\d\d)\.(\d\d)\.(\d{4})/, '$3-$2-$1').replace(' ', 'T')) : null;
      if (wd && !isNaN(wd.getTime()) && (now - wd) / 86400000 > VIDEO_CONTEXT_DAYS) return;      // мнение устарело
      var bits = [];
      if (r[2] !== '') bits.push('место в списке «' + r[1] + '»: ' + r[2]);
      if (r[3] !== '') bits.push('оценка ' + r[3] + '/10');
      if (r[4]) bits.push('как сказано: ' + r[4]);
      if (r[5]) bits.push('плей-офф: ' + r[5]);
      if (r[6]) bits.push('плюсы: ' + r[6]);
      if (r[7]) bits.push('минусы: ' + r[7]);
      if (r[8]) bits.push('вратари: ' + r[8]);
      if (r[15]) bits.push('травмы / не играют: ' + r[15]);
      if (r[16]) bits.push('переходы и состав: ' + r[16]);
      if (r[17]) bits.push('тренер и тактика: ' + r[17]);
      if (r[18]) bits.push('форма: ' + r[18]);
      if (r[19]) bits.push('ожидания эксперта: ' + r[19]);
      if (bits.length) PRESEASON_CTX_[t] = t + ' — ' + bits.join('; ') + (wd && !isNaN(wd.getTime()) ? ' (разбор от ' + Utilities.formatDate(wd, 'Europe/Moscow', 'dd.MM') + ')' : '');
    });
  }
  var lines = teams.map(function (t) { return PRESEASON_CTX_[t]; }).filter(Boolean);
  return lines.length ? lines.join('\n') : null;
}

/** Для досье команды: факты из разобранных роликов одной «новостью» (свежие — VIDEO_CONTEXT_DAYS дней). */
function videoDossierNews_(team) {
  var ss = SpreadsheetApp.getActive(), txt = preseasonContext_(ss, [team], agentMskDay_());
  if (!txt) return [];
  var sh = ss.getSheetByName(PRESEASON_SHEET), when = new Date();
  try {
    sh.getRange(2, 1, sh.getLastRow() - 1, 15).getValues().forEach(function (r) {
      if (String(r[0]).trim() !== team || !r[14]) return;
      var d = r[14] instanceof Date ? r[14] : new Date(String(r[14]).replace(/^(\d\d)\.(\d\d)\.(\d{4})/, '$3-$2-$1').replace(' ', 'T'));
      if (!isNaN(d.getTime())) when = d;
    });
  } catch (e) {}
  return [{ id: 'video-' + team, url: 'https://www.youtube.com/', title: 'Разбор роликов YouTube (эксперты): ' + txt.replace(new RegExp('^' + team + ' — '), '').slice(0, 1500), date: when }];
}

/** Дата из ячейки: Date, «дд.мм.гггг[ чч:мм]» или «гггг-мм-дд». */
function videoDate_(x) {
  if (x instanceof Date) return isNaN(x.getTime()) ? null : x;
  var s = String(x || '').trim(), m = s.match(/^(\d\d)\.(\d\d)\.(\d{4})/);
  var d = m ? new Date(m[3] + '-' + m[2] + '-' + m[1] + 'T12:00:00') : /^\d{4}-\d\d-\d\d/.test(s) ? new Date(s.slice(0, 10) + 'T12:00:00') : null;
  return d && !isNaN(d.getTime()) ? d : null;
}

/** Название победителя без приписки: «Локомотив (в ОТ/буллитах)» → «Локомотив». */
function winnerName_(x) { return String(x || '').split(' (')[0].trim(); }

/** Прогнозы экспертов из роликов: найти матч, отметить, угадал ли эксперт и модель. {checked, settled, lines[]} */
function expertPicksSettle_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(PICKS_SHEET);
  if (!sh || sh.getLastRow() < 2) return { checked: 0, settled: 0, lines: [] };
  var res = ss.getSheetByName(SHEET_RESULTS), R = res ? res.getDataRange().getValues() : [], hdr = R[0] || [];
  var ci = function (n) { return hdr.indexOf(n); };
  var cD = ci('Дата'), cS = ci('Статус'), cH = ci('Хозяева'), cA = ci('Гости'), cHG = ci('Г Хозяев'), cAG = ci('Г Гостей'), cW = ci('Победитель'), cOT = ci('ОТ/буллиты?');
  var prog = ss.getSheetByName('прогнозы'), P = prog && prog.getLastRow() > 1 ? prog.getRange(2, 1, prog.getLastRow() - 1, 11).getValues() : [];
  var key = function (d) { return d ? Utilities.formatDate(d, 'Europe/Moscow', 'yyyy-MM-dd') : ''; };
  var n = sh.getLastRow() - 1, rows = sh.getRange(2, 1, n, PICKS_COLS).getValues(), checked = 0, today = new Date();
  rows.forEach(function (r) {
    if (r[12] === '✅' || r[12] === '❌' || /после матча/.test(String(r[14]))) return;
    var said = videoDate_(r[2]); if (!said) return;
    var saidKey = key(said), want = null, wm = String(r[3]).match(/(\d{1,2})\.(\d{1,2})/);
    if (wm) { var y = said.getFullYear(), mo = Number(wm[2]); if (mo < said.getMonth() + 1 - 6) y++; want = new Date(y + '-' + ('0' + mo).slice(-2) + '-' + ('0' + wm[1]).slice(-2) + 'T12:00:00'); }
    var best = null;
    for (var j = 1; j < R.length; j++) {
      var h = String(R[j][cH]).trim(), a = String(R[j][cA]).trim();
      if (!((h === r[4] && a === r[5]) || (h === r[5] && a === r[4]))) continue;
      var d = videoDate_(R[j][cD]); if (!d) continue;
      var days = (d - (want || said)) / 86400000;
      if (want ? Math.abs(days) > 1.5 : (days < -1 || days > PICKS_WAIT_DAYS)) continue;
      if (!best || Math.abs(days) < Math.abs(best.days)) best = { j: j, d: d, days: days };
    }
    if (!best) { if ((today - said) / 86400000 > PICKS_WAIT_DAYS) r[14] = 'матч не найден в календаре'; return; }
    var row = R[best.j];
    r[10] = key(best.d).split('-').reverse().join('.');
    if (key(best.d) < saidKey) { r[14] = 'ролик разобран после матча — не считаем'; return; }
    if (String(row[cS]).trim() !== 'Сыгран' || !String(row[cW]).trim()) { r[14] = 'ждём матч'; return; }
    r[11] = row[cHG] + ':' + row[cAG] + (row[cOT] === true || /^(да|true|от|б)/i.test(String(row[cOT])) ? ' ОТ/Б' : '');
    r[12] = winnerName_(row[cW]) === r[6] ? '✅' : '❌';
    r[14] = '';
    for (var k = 0; k < P.length; k++) {
      if (key(videoDate_(P[k][0])) === key(best.d) && String(P[k][1]).trim() === String(row[cH]).trim() && String(P[k][2]).trim() === String(row[cA]).trim()) { r[13] = P[k][10] === '✅' || P[k][10] === '❌' ? P[k][10] : ''; break; }
    }
    checked++;
  });
  sh.getRange(2, 1, n, PICKS_COLS).setValues(rows.map(function (r) { r[3] = r[3] ? "'" + r[3] : ''; r[9] = r[9] ? "'" + r[9] : ''; return r; }));
  var by = {}, settled = 0;
  rows.forEach(function (r) {
    if (r[12] !== '✅' && r[12] !== '❌') return;
    settled++;
    var e = String(r[1] || 'ролик').split(' — ')[0], b = by[e] = by[e] || { n: 0, h: 0, mn: 0, mh: 0 };
    b.n++; if (r[12] === '✅') b.h++;
    if (r[13] === '✅' || r[13] === '❌') { b.mn++; if (r[13] === '✅') b.mh++; }
  });
  var lines = Object.keys(by).sort(function (a, b) { return by[b].n - by[a].n; }).map(function (e) {
    var b = by[e];
    return e + ': ' + b.h + ' из ' + b.n + ' (' + Math.round(100 * b.h / b.n) + '%)' + (b.mn ? '; модель на тех же матчах: ' + b.mh + ' из ' + b.mn : '');
  });
  return { checked: checked, settled: settled, lines: lines };
}

/** Кнопка: точность экспертов из роликов. */
function expertPicksReportNow_() {
  var r = expertPicksSettle_(SpreadsheetApp.getActive());
  uiAlert_(r.settled ? '🎬 Прогнозы экспертов из роликов (проверено матчей: ' + r.settled + '):\n\n' + r.lines.join('\n') +
    '\n\nПодробно — лист «' + PICKS_SHEET + '». Выводы делайте после 20–30 матчей на эксперта: на меньшем числе это ещё случайность.'
    : 'Проверенных прогнозов экспертов пока нет. Они появятся, когда в разобранных роликах эксперт назовёт победителя конкретного матча и этот матч будет сыгран.');
}

/** Для сводки агента: прогноз эксперта из ролика на этот матч (строки для Telegram). */
function expertPicksFor_(ss, m) {
  var sh = ss.getSheetByName(PICKS_SHEET);
  if (!sh || sh.getLastRow() < 2) return [];
  var day = videoDate_(m.day || agentMskDay_()), out = [];
  sh.getRange(2, 1, sh.getLastRow() - 1, PICKS_COLS).getValues().forEach(function (r) {
    if (r[12] === '✅' || r[12] === '❌') return;
    if (!((r[4] === m.home && r[5] === m.away) || (r[4] === m.away && r[5] === m.home))) return;
    var said = videoDate_(r[2]); if (!said || !day || (day - said) / 86400000 > PICKS_WAIT_DAYS || (day - said) / 86400000 < -1) return;
    var md = r[10] ? videoDate_(String(r[10]).split('.').reverse().join('-')) : null;
    if (md && Math.abs(md - day) / 86400000 > 1.5) return;
    out.push('🎬 ' + (String(r[1] || 'эксперт').split(' — ')[0]) + ': за «' + r[6] + '»' + (r[7] ? ' (' + r[7] + ')' : '') + (r[8] ? ' — ' + String(r[8]).slice(0, 120) : ''));
  });
  return out.slice(0, 3);
}

/** Кнопка «🎬 Вставить видео»: спросить ссылку, вписать её в список и сразу отдать ролик Gemini на разбор. */
function videoInsert_() {
  var ui = SpreadsheetApp.getUi();
  var r = ui.prompt('🎬 Вставить видео · ' + VIDEO_LEAGUE, 'Ссылка на открытый ролик YouTube (youtube.com/watch?v=… или youtu.be/…).\n' +
    'После «ОК» ролик сразу уйдёт в Gemini: команды, травмы, составы, форма и прогнозы эксперта попадут в досье команд и агенту к матчам.', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var text = String(r.getResponseText() || '').trim(), id = videoIdOf_(text);
  if (!id) { ui.alert('Не похоже на ссылку на ролик YouTube: «' + text.slice(0, 120) + '».\nНужна ссылка вида youtube.com/watch?v=… или youtu.be/…'); return; }
  var ss = SpreadsheetApp.getActive(), L = videoList_(ss);
  var same = L.list.filter(function (v) { return v.id === id; })[0];
  if (same && /^готово/.test(same.status)) {
    if (ui.alert('Этот ролик уже разобран (строка ' + same.row + ': «' + same.status.slice(0, 120) + '»). Разобрать заново?', ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
    L.sh.getRange(same.row, 3, 1, 5).setValues([['', '', same.len || '', '', '']]);
    videoRunState_(id, null);
  } else if (!same) {
    L.sh.getRange(Math.max(2, L.sh.getLastRow() + 1), 1).setValue(videoCanon_(id));
  }
  try { ss.toast('Ролик отправлен в Gemini. Итог появится здесь через 1–4 минуты; длинный ролик разберётся частями сам.', '🎬 Видео', 15); } catch (e) {}
  videoAnalyzeAll_(false);
}

/** Кнопка «Добавить ролик»: открыть список ссылок на первой свободной строке. */
function videoOpenList_() {
  var ss = SpreadsheetApp.getActive(), L = videoList_(ss);
  try { if (L.sh.isSheetHidden()) L.sh.showSheet(); ss.setActiveSheet(L.sh); L.sh.getRange(Math.max(2, L.sh.getLastRow() + 1), 1).activate(); } catch (e) {}
  uiAlert_('Вставьте ссылку на ролик YouTube (открытый) в выделенную ячейку колонки A — по одной ссылке на строку, можно несколько. ' +
    'Затем меню «🎬 … · Видео» → «Разобрать новые ролики». Уже разобранные ролики повторно лимит не тратят.\n\n' +
    'Разобрать ролик заново — очистите его ячейку «Статус». Бесплатный лимит Google — около 8 часов роликов в сутки.');
}
function videoOpenSummary_() { preseasonBuild_(SpreadsheetApp.getActive()); sheetOpen_(PRESEASON_SHEET); }

/* ── 📅 Меню «Ежедневно»: пункты по порядку дня, у каждого — во сколько это делает автоматика ──
 * С включённой автоматикой нажимать ничего не обязательно: пункт 0 покажет, что уже сделано сегодня.
 * Кнопки публикации в канал спрашивают подтверждение, если сегодня уже публиковали (сами или автоматика) — без дублей. */
var DAILY_KHL_ = [
  ['0 · Что автоматика уже сделала сегодня', 'autoStatusNow_'],
  null,
  ['1 · Обновить всё после игрового дня', 'runAfterGameDay_'],
  ['2 · Обновить коэффициенты', 'updateMarketOdds_'],
  ['3 · Учесть мои поправки', 'tweaksUpdateNow_', 'runAfterGameDay_'],
  null,
  ['❓ Как пользоваться меню', 'dailyHelp_']
];
/* 📣 «ТГ группа»: всё, что публикуется в группу (канал), по порядку дня. */
var TG_GROUP_KHL_ = [
  ['1 · Карточки матчей дня → группа', 'dailyCardsChannel_', '-'],
  ['2 · Игра «матчи дня» → группа', 'dailyGamePost_', 'gamePostMatchesAuto_'],
  ['3 · Счёт после матчей в пост «Матчи дня» → группа', 'liveUpdateNow_', 'liveUpdateAuto_'],
  ['4 · Игра: подвести итоги (личные итоги игрокам)', 'gameSettleNow_', '-'],
  ['5 · «Сила команд» → группа (пн)', 'powerPostNow_', '-'],
  null,
  ['Игра: подключить бота и канал (настройка)', 'gameConnect_'],
  ['Игра: проверить связь с ботом', 'gameDiagnose_'],
  null,
  ['🌐 Публичная страница точности (создать / обновить)', 'publicPageNow_'],
  null,
  ['❓ Что куда публикуется', 'dailyHelp_']
];

/** Подпись «(авто 06:00)» / «(авто каждые 2 ч)» по расписанию автоматики; '-' — только вручную. */
function dailyAutoLabel_(fn, autoFn) {
  if (autoFn === '-') return ' (только вручную)';
  var j = AUTO_JOBS.filter(function (x) { return x.fn === (autoFn || fn) || x.fn === fn.replace(/_$/, 'Auto_'); })[0];
  if (!j) return '';
  if (j.kind === 'day') return ' (авто ' + ('0' + j.hour).slice(-2) + ':00)';
  if (j.kind === 'hours') return ' (авто каждые ' + j.every + ' ч)';
  if (j.kind === 'minutes') return ' (авто)';
  return '';
}

function dailyMenu_(ui, title, items) {
  var m = ui.createMenu(title);
  items.forEach(function (it) {
    if (!it) { m.addSeparator(); return; }
    m.addItem(it[0] + (/^\d/.test(it[0]) && it[1] !== 'autoStatusNow_' ? dailyAutoLabel_(it[1], it[2]) : ''), it[1]);
  });
  m.addToUi();
}

/** Отметка «сегодня уже опубликовано» (по МСК); старые отметки чистятся. */
function dailyKey_(what) { return 'DAILY_' + what + '_' + Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM-dd'); }
function dailyMark_(what) {
  try {
    var p = PropertiesService.getScriptProperties(), key = dailyKey_(what), today = key.slice(-10);
    Object.keys(p.getProperties()).forEach(function (k) { if (/^DAILY_/.test(k) && k.slice(-10) !== today) p.deleteProperty(k); });
    p.setProperty(key, mskNow_('HH:mm'));
  } catch (e) {}
}
/** true — остановиться: сегодня уже публиковали, а повтор не подтвердили. */
function dailyAlready_(what, label) {
  var t = PropertiesService.getScriptProperties().getProperty(dailyKey_(what));
  if (!t) return false;
  var ui = null; try { ui = SpreadsheetApp.getUi(); } catch (e) { return true; }
  return ui.alert(label + ' сегодня уже опубликовано в канал (в ' + t + ' МСК). Опубликовать ещё раз?', ui.ButtonSet.YES_NO) !== ui.Button.YES;
}
function dailyCardsChannel_() { if (dailyAlready_('cards', 'Карточки матчей')) return; bannersToChannelNow_(); }
function dailyGamePost_() { if (dailyAlready_('game', 'Игра «матчи дня»')) return; gamePostNow_(); }

function dailyHelp_() {
  var auto = [];
  try { ScriptApp.getProjectTriggers().forEach(function (t) { auto.push(t.getHandlerFunction()); }); } catch (e) {}
  var on = AUTO_JOBS.some(function (j) { return auto.indexOf(j.fn) >= 0; }), L = VIDEO_LEAGUE;
  uiAlert_('Время в пунктах — по Красноярску.\n\n' +
    '📅 «' + L + ' · Ежедневно» — только то, что нужно для работы таблицы: результаты, Elo, календарь, прогнозы, точность, коэффициенты, ваши поправки.\n' +
    '📣 «' + L + ' · ТГ группа» — всё, что публикуется в группу (канал). Вручную всегда — карточки матчей: сначала посмотрите их у себя («📩 ' + L + ' → мне в ТГ»). ' +
    'Если сегодня уже публиковали (вы или автоматика), кнопка спросит «Опубликовать ещё раз?» — дублей не будет.\n' +
    '📩 «' + L + ' → мне в ТГ» — приходит только вам: сводка агента, карточки для проверки, пробные посты.\n\n' +
    (on ? '✅ Автоматика включена: всё с пометкой «авто» делается само — нажимать нужно, только если хотите раньше или пункт 0 в «Ежедневно» показал сбой.'
        : '⚠ Автоматика выключена — пункты нужно нажимать самим по порядку. Включить: «НХЛ-парсер» → Настройки → «Включить всю автоматику».'));
}

/* ==========================================================================
 * 📊 СТАТИСТИКА КХЛ ИЗ ОФИЦИАЛЬНОГО ПРИЛОЖЕНИЯ КХЛ (бесплатно, без ключей)
 *  Сам khl.ru закрыт для программ (гео-блок и защита от ботов), а у мобильного приложения КХЛ открытый API
 *  (khl.api.webcaster.pro — им же пользуется сайт khl.ru; описание: github.com/icebergvibe/OpenScore).
 *  По каждому сыгранному матчу: броски в створ и все броски, большинство (голы/попытки), вбрасывания, штраф,
 *  блоки, силовые, время в атаке, кто из вратарей сколько стоял, счёт по периодам (ОТ/буллиты), коэффициенты Фонбета.
 *  • Лист «КХЛ_матчи_приложение» (скрыт): каждый матч скачивается ОДИН раз и хранится сжато.
 *  • Лист «Статистика_КХЛ»: по командам — броски за/против, доля бросков, реализация большинства и меньшинства,
 *    вбрасывания, % отражённых, PDO, основной вратарь и кто стоял в последнем матче.
 *  • Это идёт агенту к матчу и в досье команд. Модель прогнозов НЕ меняется.
 * ==========================================================================*/
var KHLAPP_BASE = 'https://khl.api.webcaster.pro/api/khl_mobile/';
var KHLAPP_GAMES_SHEET = 'КХЛ_матчи_приложение';
var KHL_STATS_SHEET = 'Статистика_КХЛ';
var KHLAPP_DIAG_SHEET = 'Диагностика_КХЛ_приложение';
var KHLAPP_MAX_NEW = 40;                  // сколько новых матчей скачивать за один запуск «Обновить всё»
var KHLAPP_TIME_MS = 90000;               // и не дольше полутора минут
/* id команды в приложении → название в справочнике (запасной путь, если названия разойдутся) */
var KHLAPP_TEAM_IDS = { 8: 'Динамо Москва', 10: 'Авангард', 12: 'Амур', 16: 'ЦСКА', 18: 'Спартак', 22: 'Торпедо', 24: 'Сибирь', 26: 'Локомотив',
  28: 'Трактор', 30: 'Металлург', 32: 'Салават Юлаев', 36: 'Нефтехимик', 38: 'Динамо Минск', 40: 'Ак Барс', 42: 'Северсталь', 44: 'СКА',
  46: 'Барыс', 56: 'Автомобилист', 61: 'Адмирал', 105: 'Лада', 113: 'Сочи', 315: 'Шанхайские Драконы' };
var KHLAPP_COLS = ['Дата (МСК)', 'ID матча', 'Хозяева', 'Гости', 'Г Х', 'Г Г', 'Концовка', 'Броски в створ Х', 'Броски в створ Г', 'Все броски Х', 'Все броски Г',
  'Голы в бол. Х', 'Попыток бол. Х', 'Голы в бол. Г', 'Попыток бол. Г', 'Вбрасывания Х', 'Вбрасывания Г', 'Штраф Х', 'Штраф Г', 'Блоки Х', 'Блоки Г',
  'Силовые Х', 'Силовые Г', 'Атака Х, сек', 'Атака Г, сек', 'Вратарь Х', 'Вратарь Г', 'В пустые ворота Х', 'В пустые ворота Г', 'Кэф П1', 'Кэф Х', 'Кэф П2'];

function khlAppGet_(path) {
  var r = UrlFetchApp.fetch(KHLAPP_BASE + path, { muteHttpExceptions: true, headers: { 'User-Agent': SPORTS_UA['User-Agent'] } });
  if (r.getResponseCode() !== 200) throw new Error('приложение КХЛ ответило кодом ' + r.getResponseCode() + ' (' + path.split('?')[0] + ')');
  var j = JSON.parse(r.getContentText());
  if (j && j.error) throw new Error('приложение КХЛ: ' + (j.error.message || j.error.code));
  return j;
}

function khlAppTeam_(t) {
  if (!t) return null;
  var byId = KHLAPP_TEAM_IDS[t.id];
  var map = buildNameMap_(), n = String(t.name || '').trim();
  if (map[n]) return map[n];
  if (byId && map[byId]) return map[byId];
  var v = null; try { v = videoTeamRu_(n); } catch (e) { v = null; }
  return v || byId || null;
}

/** Матчи за период: [{id, day, home, away, state}] (по МСК). */
function khlAppEvents_(fromSec, toSec, stageId) {
  var out = [], page = 1;
  while (page <= 40) {
    var q = 'events_v2.json?order_direction=asc&page=' + page + '&q%5Bstart_at_gt_time_from_unixtime%5D=' + fromSec + '&q%5Bstart_at_lt_time_from_unixtime%5D=' + toSec + (stageId ? '&stage_id=' + stageId : '');
    var arr = khlAppGet_(q);
    if (!Array.isArray(arr) || !arr.length) break;
    arr.forEach(function (w) {
      var e = w.event || w; if (!e || (e.type_id !== 18 && e.type_id !== 24)) return;
      out.push({ id: e.id, day: Utilities.formatDate(new Date(e.start_at), 'Europe/Moscow', 'yyyy-MM-dd'), home: khlAppTeam_(e.team_a), away: khlAppTeam_(e.team_b), state: e.game_state_key, score: e.score });
    });
    if (arr.length < 16) break;
    page++;
  }
  return out;
}

/** «Броски: 55-48 ; Броски в створ: 33-22 ; …» → {'Броски': [55, 48], …}; время «11:26-11:04» → секунды. */
function khlAppInfo_(ev) {
  var line = ((ev.text_events || []).filter(function (x) { return x.type === 'info' && /^Статистика матча/.test(String(x.text)); })[0] || {}).text || '', out = {};
  line.replace(/^Статистика матча:\s*/, '').split(';').forEach(function (part) {
    var m = part.match(/^\s*([^:]+):\s*([\d:]+)\s*-\s*([\d:]+)/); if (!m) return;
    var v = function (s) { var t = s.split(':'); return t.length === 2 ? Number(t[0]) * 60 + Number(t[1]) : Number(s); };
    out[m[1].trim()] = [v(m[2]), v(m[3])];
  });
  return out;
}

/** Сжатая строка матча для архива (см. KHLAPP_COLS) или null, если матч не завершён. */
function khlAppGameRow_(ev) {
  if (!ev || ev.game_state_key !== 'finished') return null;
  var a = ev.team_a || {}, b = ev.team_b || {}, sc = String(ev.score || '').split(':');
  if (sc.length !== 2) return null;
  var s = ev.scores || {}, end = s.bullitt ? 'Б' : s.overtime ? 'ОТ' : '';
  var info = khlAppInfo_(ev), pair = function (k, i) { return info[k] ? info[k][i] : ''; };
  var goalie = function (t) {
    var best = null;
    (t.players || []).forEach(function (p) {
      if (p.role_key !== 'goaltender') return;
      var toi = Number(((p.match_stats || []).filter(function (x) { return x.id === 'toi'; })[0] || {}).val) || 0;
      if (!best || toi > best.toi) best = { name: p.name, toi: toi };
    });
    return best && best.toi > 0 ? best.name : '';
  };
  var en = function (teamId) { return (ev.goals || []).filter(function (g) { return g.status_abbr === 'EN' && g.author && g.author.team_id === teamId; }).length; };
  var bets = ev.bets || {};
  return [Utilities.formatDate(new Date(ev.start_at), 'Europe/Moscow', 'yyyy-MM-dd'), ev.id, khlAppTeam_(a), khlAppTeam_(b), Number(sc[0]), Number(sc[1]), end,
    a.shots === undefined ? pair('Броски в створ', 0) : a.shots, b.shots === undefined ? pair('Броски в створ', 1) : b.shots, pair('Броски', 0), pair('Броски', 1),
    a.ppg, a.ppc, b.ppg, b.ppc, a.vbr === undefined ? pair('Вбрасывания', 0) : a.vbr, b.vbr === undefined ? pair('Вбрасывания', 1) : b.vbr,
    a.pim === undefined ? pair('Штраф', 0) : a.pim, b.pim === undefined ? pair('Штраф', 1) : b.pim, pair('Блокированные броски', 0), pair('Блокированные броски', 1),
    pair('Силовые приемы', 0), pair('Силовые приемы', 1), pair('Время в атаке', 0), pair('Время в атаке', 1), goalie(a), goalie(b), en(a.id), en(b.id),
    bets.team_a_win || '', bets.draw || '', bets.team_b_win || ''].map(function (x) { return x === undefined || x === null ? '' : x; });
}

function khlAppGamesSheet_(ss) {
  var sh = ss.getSheetByName(KHLAPP_GAMES_SHEET);
  if (!sh) { sh = ss.insertSheet(KHLAPP_GAMES_SHEET); sh.getRange(1, 1, 1, KHLAPP_COLS.length).setValues([KHLAPP_COLS]).setFontWeight('bold'); try { sh.hideSheet(); } catch (e) {} }
  return sh;
}

/** Докачать новые сыгранные матчи текущего сезона в архив. {added, pending, stage} */
function khlAppSync_(ss, maxNew, timeMs) {
  var t0 = Date.now(), sh = khlAppGamesSheet_(ss), boot = khlAppGet_('data.json'), stage = boot.current_stage_id;
  var st = (boot.stages_v2 || []).filter(function (x) { return x.id === stage; })[0] || {};
  var have = {}, lastDay = '';
  if (sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues().forEach(function (r) { have[String(r[1])] = 1; var d = String(r[0]).replace(/^'/, ''); if (d > lastDay) lastDay = d; });
  // первый раз — с 1 августа сезона (предсезонка отсекается по stage_id); дальше — с последнего сохранённого матча минус 3 дня
  var y = Number(String(st.season || '').slice(0, 4)) || new Date().getFullYear(), from = Math.floor(new Date(y + '-08-01T00:00:00Z').getTime() / 1000);
  if (/^\d{4}-\d\d-\d\d$/.test(lastDay)) from = Math.max(from, Math.floor(new Date(lastDay + 'T00:00:00Z').getTime() / 1000) - 3 * 86400);
  var evs = khlAppEvents_(from, Math.floor(Date.now() / 1000), stage).filter(function (e) { return e.state === 'finished' && !have[String(e.id)]; });
  var todo = evs.slice(0, maxNew || KHLAPP_MAX_NEW), rows = [];
  for (var i = 0; i < todo.length && Date.now() - t0 < (timeMs || KHLAPP_TIME_MS); i += 10) {
    var batch = todo.slice(i, i + 10), resps = UrlFetchApp.fetchAll(batch.map(function (e) { return { url: KHLAPP_BASE + 'event_v2.json?id=' + e.id, muteHttpExceptions: true, headers: { 'User-Agent': SPORTS_UA['User-Agent'] } }; }));
    resps.forEach(function (r) {
      try { if (r.getResponseCode() !== 200) return; var j = JSON.parse(r.getContentText()); var row = khlAppGameRow_(j.event); if (row && row[2] && row[3]) rows.push(row); } catch (e) {}
    });
  }
  if (rows.length) sh.getRange(sh.getLastRow() + 1, 1, rows.length, KHLAPP_COLS.length).setValues(rows.map(function (r) { r[0] = "'" + r[0]; return r; }));
  return { added: rows.length, pending: evs.length - rows.length, stage: stage, season: st.season || '' };
}

/** Сводка по командам из архива: {команда: {...}} */
function khlAppTeamStats_(ss) {
  var sh = ss.getSheetByName(KHLAPP_GAMES_SHEET), T = {};
  if (!sh || sh.getLastRow() < 2) return T;
  var rows = sh.getRange(2, 1, sh.getLastRow() - 1, KHLAPP_COLS.length).getValues().sort(function (a, b) { return String(a[0]) < String(b[0]) ? -1 : 1; });
  var num = function (x) { var n = Number(x); return x === '' || x === null || !isFinite(n) ? null : n; };
  rows.forEach(function (r) {
    [[2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 23, 24, 25, 27, 28], [3, 2, 5, 4, 8, 7, 10, 9, 13, 14, 11, 12, 16, 15, 18, 17, 24, 23, 26, 28, 27]].forEach(function (ix, side) {
      var team = String(r[ix[0]]).trim(); if (!team) return;
      var t = T[team] = T[team] || { gp: 0, gf: 0, ga: 0, sf: 0, sa: 0, cf: 0, ca: 0, cN: 0, ppg: 0, ppc: 0, ppgA: 0, ppcA: 0, fow: 0, fol: 0, pim: 0, atk: 0, atkA: 0, atkN: 0, enA: 0, goalies: {}, last: [], lastGoalie: '' };
      var gf = num(r[ix[2]]), ga = num(r[ix[3]]);
      // буллиты: победный буллит даёт +1 в счёт — для бросков/реализации считаем только голы по ходу игры
      if (r[6] === 'Б') { if (gf > ga) gf--; else ga--; }
      t.gp++; t.gf += gf; t.ga += ga;
      var sf = num(r[ix[4]]), sa = num(r[ix[5]]); if (sf !== null && sa !== null) { t.sf += sf; t.sa += sa; }
      var cf = num(r[ix[6]]), ca = num(r[ix[7]]); if (cf !== null && ca !== null) { t.cf += cf; t.ca += ca; t.cN++; }
      t.ppg += num(r[ix[8]]) || 0; t.ppc += num(r[ix[9]]) || 0; t.ppgA += num(r[ix[10]]) || 0; t.ppcA += num(r[ix[11]]) || 0;
      t.fow += num(r[ix[12]]) || 0; t.fol += num(r[ix[13]]) || 0; t.pim += num(r[ix[14]]) || 0;
      var at = num(r[ix[16]]), atA = num(r[ix[17]]); if (at !== null && atA !== null) { t.atk += at; t.atkA += atA; t.atkN++; }
      var g = String(r[ix[18]] || '').trim(); if (g) { t.goalies[g] = (t.goalies[g] || 0) + 1; t.lastGoalie = g; }
      t.enA += num(r[ix[20]]) || 0;
      t.last.push({ sf: sf, sa: sa, win: gf > ga || (r[6] === 'Б' && num(r[ix[2]]) > num(r[ix[3]])) });
    });
  });
  Object.keys(T).forEach(function (k) {
    var t = T[k], sv = t.sa ? 1 - (t.ga - t.enA) / t.sa : null, sh5 = t.sf ? t.gf / t.sf : null;
    t.svPct = sv; t.shPct = sh5; t.pdo = sv !== null && sh5 !== null ? (sv + sh5) * 100 : null;
    t.ppPct = t.ppc ? t.ppg / t.ppc : null; t.pkPct = t.ppcA ? 1 - t.ppgA / t.ppcA : null;
    t.foPct = t.fow + t.fol ? t.fow / (t.fow + t.fol) : null; t.cfPct = t.cf + t.ca ? t.cf / (t.cf + t.ca) : null;
    t.atkPct = t.atk + t.atkA ? t.atk / (t.atk + t.atkA) : null;
    var gl = Object.keys(t.goalies).sort(function (a, b) { return t.goalies[b] - t.goalies[a]; });
    t.mainGoalie = gl[0] || ''; t.mainGoalieGp = gl[0] ? t.goalies[gl[0]] : 0;
    var l5 = t.last.slice(-5), s5 = 0, a5 = 0; l5.forEach(function (x) { s5 += x.sf || 0; a5 += x.sa || 0; });
    t.sf5 = l5.length ? s5 / l5.length : null; t.sa5 = l5.length ? a5 / l5.length : null;
  });
  return T;
}

var KHL_APP_STATS_ = null;
function khlAppStatsCached_(ss) { if (!KHL_APP_STATS_) { try { KHL_APP_STATS_ = khlAppTeamStats_(ss || SpreadsheetApp.getActive()); } catch (e) { KHL_APP_STATS_ = {}; } } return KHL_APP_STATS_; }

function khlPct_(x) { return x === null || x === undefined ? '—' : Math.round(x * 1000) / 10 + '%'; }
function khlNum_(x, d) { return x === null || x === undefined ? '—' : Math.round(x * Math.pow(10, d || 1)) / Math.pow(10, d || 1); }

/** Строка о команде для агента/досье. */
function khlAppTeamLine_(team, T) {
  var t = (T || {})[team]; if (!t || !t.gp) return '';
  return team + ' (матчей: ' + t.gp + '): броски в створ за игру ' + khlNum_(t.sf / t.gp) + ' — пропускает ' + khlNum_(t.sa / t.gp) +
    (t.sf5 !== null ? ' (последние 5: ' + khlNum_(t.sf5) + ' — ' + khlNum_(t.sa5) + ')' : '') +
    '; доля всех бросков ' + khlPct_(t.cfPct) + '; реализация большинства ' + khlPct_(t.ppPct) + ', меньшинство ' + khlPct_(t.pkPct) +
    '; вбрасывания ' + khlPct_(t.foPct) + '; % отражённых ' + khlPct_(t.svPct) + ', PDO ' + khlNum_(t.pdo) +
    (t.mainGoalie ? '; основной вратарь ' + t.mainGoalie + ' (' + t.mainGoalieGp + ' из ' + t.gp + ')' + (t.lastGoalie && t.lastGoalie !== t.mainGoalie ? ', в последнем матче — ' + t.lastGoalie : '') : '');
}

/** Лист «Статистика_КХЛ». */
function khlAppRender_(ss, T) {
  var sh = ss.getSheetByName(KHL_STATS_SHEET) || ss.insertSheet(KHL_STATS_SHEET);
  sh.clear();
  var head = ['Команда', 'Матчей', 'Броски в створ за игру', 'Пропускает бросков за игру', 'Последние 5: броски за / против', 'Доля всех бросков', 'Реализация большинства',
    'Меньшинство (% без гола)', 'Вбрасывания', '% отражённых', 'Реализация бросков', 'PDO', 'Время в атаке, доля', 'Штраф за игру, мин', 'Основной вратарь', 'Вратарь в последнем матче', 'Обновлено (МСК)'];
  sh.getRange(1, 1, 1, head.length).setValues([head]).setFontWeight('bold');
  var now = mskNow_(), rows = Object.keys(T).sort(function (a, b) { return (T[b].cfPct || 0) - (T[a].cfPct || 0); }).map(function (k) {
    var t = T[k];
    return [k, t.gp, khlNum_(t.sf / t.gp), khlNum_(t.sa / t.gp), t.sf5 === null ? '—' : khlNum_(t.sf5) + ' / ' + khlNum_(t.sa5), khlPct_(t.cfPct), khlPct_(t.ppPct), khlPct_(t.pkPct),
      khlPct_(t.foPct), khlPct_(t.svPct), khlPct_(t.shPct), khlNum_(t.pdo), khlPct_(t.atkPct), khlNum_(t.pim / t.gp), t.mainGoalie ? t.mainGoalie + ' (' + t.mainGoalieGp + ')' : '—', t.lastGoalie || '—', now];
  });
  if (rows.length) sh.getRange(2, 1, rows.length, head.length).setValues(rows);
  sh.getRange(rows.length + 3, 1).setValue('Источник: официальное приложение КХЛ (khl.api.webcaster.pro). Доля всех бросков > 50% — команда чаще бросает, чем соперник. ' +
    'PDO = % отражённых + реализация бросков; сильно выше 100 — вероятно, везение, которое обычно проходит.').setFontColor('#666666');
  try { sh.setFrozenRows(1); } catch (e) {}
}

/** Шаг «Обновить всё» и кнопка. */
function khlAppUpdate_(ss, maxNew) {
  ss = ss || SpreadsheetApp.getActive();
  var s = khlAppSync_(ss, maxNew);
  KHL_APP_STATS_ = null;
  var T = khlAppStatsCached_(ss);
  khlAppRender_(ss, T);
  return 'приложение КХЛ: новых матчей ' + s.added + (s.pending ? ', догрузятся позже ' + s.pending : '') + ', команд в статистике ' + Object.keys(T).length;
}
function khlStatsNow_() {
  try { var r = khlAppUpdate_(SpreadsheetApp.getActive(), 200); sheetOpen_(KHL_STATS_SHEET); uiAlert_('📊 Статистика КХЛ обновлена (бесплатно, лимиты не тратятся):\n' + r + '.'); }
  catch (e) { uiAlert_('Не получилось: ' + e.message + '\n\nПроверьте источник: «НХЛ-парсер» → 🔧 Проверки → «Источник статистики: приложение КХЛ».'); }
}

/** Бесплатная проверка источника: что отвечает приложение КХЛ из Google. */
function khlAppDiag_() {
  var ss = SpreadsheetApp.getActive(), rows = [], add = function (what, ok, detail) { rows.push([what, ok ? '✓' : '✗', String(detail).slice(0, 900)]); };
  var boot = null;
  try { boot = khlAppGet_('data.json'); add('Приложение КХЛ отвечает', true, 'сезон: ' + (((boot.stages_v2 || []).filter(function (x) { return x.id === boot.current_stage_id; })[0] || {}).title || '?') + ' (stage ' + boot.current_stage_id + '), команд: ' + (boot.teams || []).length + ', страна запроса: ' + (boot.country || '?') + (boot.geo_error ? ', гео-ошибка: ' + boot.geo_error : '')); }
  catch (e) { add('Приложение КХЛ отвечает', false, e.message); }
  if (boot) {
    var unk = (boot.teams || []).filter(function (t) { return !khlAppTeam_(t); }).map(function (t) { return t.name; });
    add('Названия команд совпадают со справочником', !unk.length, unk.length ? 'не узнал: ' + unk.join(', ') : 'все ' + (boot.teams || []).length);
    try {
      var now = Math.floor(Date.now() / 1000), evs = khlAppEvents_(now - 3 * 86400, now, boot.current_stage_id), fin = evs.filter(function (e) { return e.state === 'finished'; });
      add('Матчи за последние 3 дня', evs.length > 0, 'всего ' + evs.length + ', сыграно ' + fin.length + (evs.length ? ': ' + evs.slice(-4).map(function (e) { return e.home + ' — ' + e.away + ' ' + (e.score || ''); }).join('; ') : ''));
      if (fin.length) {
        var ev = khlAppGet_('event_v2.json?id=' + fin[fin.length - 1].id).event, row = khlAppGameRow_(ev);
        add('Протокол матча', !!row, row ? row[2] + ' — ' + row[3] + ' ' + row[4] + ':' + row[5] + (row[6] ? ' ' + row[6] : '') + '; броски в створ ' + row[7] + '–' + row[8] + ', все броски ' + row[9] + '–' + row[10] +
          ', большинство ' + row[11] + '/' + row[12] + ' и ' + row[13] + '/' + row[14] + ', вбрасывания ' + row[15] + '–' + row[16] + ', вратари: ' + (row[25] || '?') + ' и ' + (row[26] || '?') + ', кэфы ' + [row[29], row[30], row[31]].join(' / ') : 'нет данных');
      }
    } catch (e) { add('Матчи и протокол', false, e.message); }
  }
  var sh = ss.getSheetByName(KHLAPP_DIAG_SHEET) || ss.insertSheet(KHLAPP_DIAG_SHEET);
  sh.clear(); sh.getRange(1, 1, 1, 3).setValues([['Проверка', 'Итог', 'Подробности']]).setFontWeight('bold');
  sh.getRange(2, 1, rows.length, 3).setValues(rows).setWrap(true).setVerticalAlignment('top');
  try { sh.setColumnWidth(1, 260); sh.setColumnWidth(3, 700); } catch (e) {}
  sheetOpen_(KHLAPP_DIAG_SHEET);
  var ok = rows.every(function (r) { return r[1] === '✓'; });
  uiAlert_((ok ? '✅ Приложение КХЛ доступно — статистику можно забирать.' : '⚠ Есть проблемы — подробности на листе «' + KHLAPP_DIAG_SHEET + '».') + '\n\n' +
    rows.map(function (r) { return r[1] + ' ' + r[0] + ': ' + r[2].slice(0, 200); }).join('\n') + '\n\nКредиты и лимиты не тратились.');
  return rows;
}

/* ── Игра «Угадай победителей»: история ставок игрока ── */

/** Личная история: итог, банк по дням, последние ставки (для бота, HTML). */
function gameHistoryText_(ss, id) {
  var rows = gameReadPicks_(ss).filter(function (r) { return String(r[1]) === String(id); });
  if (!rows.length) return 'Ты ещё не сделал ни одного прогноза. Жми /matches 👇';
  var fmt = function (x) { return String(Math.round(x)).replace(/\B(?=(\d{3})+(?!\d))/g, ' '); };
  var ddmm = function (k) { return String(k).slice(8, 10) + '.' + String(k).slice(5, 7); };
  var settled = rows.filter(function (r) { return r[12] === PICK_WIN || r[12] === PICK_LOSS; })
    .sort(function (a, b) { return String(a[4]) < String(b[4]) ? -1 : String(a[4]) > String(b[4]) ? 1 : 0; });
  var wins = settled.filter(function (r) { return r[12] === PICK_WIN; }).length, bank = GAME_START_BANK, byDay = [], last = null;
  settled.forEach(function (r) {
    bank += Number(r[13]) || 0;
    if (last && last.day === String(r[4])) last.bank = bank; else { last = { day: String(r[4]), bank: bank }; byDay.push(last); }
  });
  var profit = bank - GAME_START_BANK, best = null, worst = null;
  byDay.forEach(function (d, i) {
    var prev = i ? byDay[i - 1].bank : GAME_START_BANK, ch = d.bank - prev;
    if (!best || ch > best.ch) best = { day: d.day, ch: ch };
    if (!worst || ch < worst.ch) worst = { day: d.day, ch: ch };
  });
  var name = rows[rows.length - 1][2];
  var lines = settled.slice(-12).reverse().map(function (r) {
    var win = r[12] === PICK_WIN, x = Number(r[13]) || 0;
    return (win ? '✅ ' : '❌ ') + ddmm(r[4]) + ' ' + escHtml_(r[5]) + ' — ' + escHtml_(r[6]) + ': ' + escHtml_(r[8]) + ' (' + Number(r[10]).toFixed(2) + ') ' +
      (x >= 0 ? '+' : '−') + fmt(Math.abs(x)) + ' ₽';
  });
  var waiting = rows.filter(function (r) { return r[12] === PICK_WAIT; }).map(function (r) {
    return '⏳ ' + ddmm(r[4]) + ' ' + escHtml_(r[5]) + ' — ' + escHtml_(r[6]) + ': ' + escHtml_(r[8]) + ' (' + Number(r[10]).toFixed(2) + ')';
  });
  var trail = [fmt(GAME_START_BANK)].concat(byDay.slice(-10).map(function (d) { return ddmm(d.day) + ': ' + fmt(d.bank); }));
  return '📈 <b>История ставок</b> — ' + escHtml_(name) + '\n\n' +
    'Ставок подсчитано: ' + settled.length + ', угадано ' + wins + (settled.length ? ' (' + Math.round(wins / settled.length * 100) + '%)' : '') + '\n' +
    '💰 Банк: ' + fmt(bank) + ' ₽ (' + (profit >= 0 ? '+' : '−') + fmt(Math.abs(profit)) + ' от старта ' + fmt(GAME_START_BANK) + ' ₽)' +
    (settled.length ? '\n📊 Банк по дням: ' + trail.join(' → ') : '') +
    (best && byDay.length > 1 ? '\nЛучший день: ' + ddmm(best.day) + ' (' + (best.ch >= 0 ? '+' : '−') + fmt(Math.abs(best.ch)) + ' ₽), худший: ' + ddmm(worst.day) + ' (' + (worst.ch >= 0 ? '+' : '−') + fmt(Math.abs(worst.ch)) + ' ₽)' : '') +
    (lines.length ? '\n\n<b>Последние ставки:</b>\n' + lines.join('\n') : '') +
    (waiting.length ? '\n\n<b>Ждут результата:</b>\n' + waiting.join('\n') : '') +
    '\n\nМатчи с кнопками — /matches';
}

/* ══════════ 🌐 Публичная страница точности (telegra.ph) ══════════
 * Страница открывается прямо в Telegram (мгновенный просмотр), её можно закрепить в канале.
 * Создаётся по кнопке один раз, дальше обновляется сама после каждого «Обновить всё».
 * Ключ доступа telegra.ph — в свойствах скрипта (PUBLIC_PAGE_TOKEN), это не ваш аккаунт и не токен бота. */
var PUBLIC_PAGE_LAST = 20;
function tph_(method, params) {
  var r = UrlFetchApp.fetch('https://api.telegra.ph/' + method, { method: 'post', payload: params, muteHttpExceptions: true });
  var j = {}; try { j = JSON.parse(r.getContentText()); } catch (e) { throw new Error('telegra.ph ответил кодом ' + r.getResponseCode()); }
  if (!j.ok) throw new Error('telegra.ph: ' + (j.error || 'ошибка'));
  return j.result;
}
function publicPageOn_() { try { return !!PropertiesService.getScriptProperties().getProperty('PUBLIC_PAGE_PATH'); } catch (e) { return false; } }
function publicPageChannelUrl_() {
  var ch = String(bannerChannel_() || '');
  return /^@\w{4,}$/.test(ch) ? 'https://t.me/' + ch.slice(1) : '';
}
function publicPageAuthor_() { var ch = String(bannerChannel_() || ''); return /^@\w{4,}$/.test(ch) ? ch : 'Прогнозы на хоккей'; }
function publicPageTitle_() { return 'Честная статистика моих прогнозов на ' + VIDEO_LEAGUE; }

/** Узлы страницы telegra.ph из того же счёта, что и лист «Модель vs рынок». */
function publicPageContent_(data) {
  var s = data.score, a = s.all, c = s.clv, out = [];
  var pct = function (x, n) { return n ? Math.round(x / n * 100) + '%' : '—'; };
  var li = function (t) { return { tag: 'li', children: [t] }; };
  var r3 = function (x) { return String(Math.round(x * 1000) / 1000).replace('.', ','); };
  out.push({ tag: 'p', children: ['Обновлено ' + mskNow_('dd.MM.yyyy HH:mm') + ' МСК. Каждый мой прогноз фиксируется до начала матча и не удаляется — здесь все, и удачные, и нет.'] });
  out.push({ tag: 'h3', children: ['Итог сезона'] });
  var sum = [li('Моих прогнозов с результатом: ' + a.n),
             li('Угадан победитель (с учётом ОТ и буллитов): ' + a.hit + ' из ' + a.n + ' (' + pct(a.hit, a.n) + ')')];
  if (a.n) sum.push(li('Средняя ошибка вероятности (Brier): ' + r3(a.brier / a.n) + ' — меньше лучше, 0,25 = подбросить монетку'));
  if (s.n) {
    sum.push(li('На тех же ' + s.n + ' матчах фаворит букмекеров угадал ' + s.win.market + ' (' + pct(s.win.market, s.n) + '), я — ' + s.win.model + ' (' + pct(s.win.model, s.n) + ')'));
    sum.push(li('Brier на этих матчах: мой ' + r3(s.brier.model / s.n) + ', букмекеры ' + r3(s.brier.market / s.n)));
  }
  out.push({ tag: 'ul', children: sum });
  out.push({ tag: 'h3', children: ['Закрытие линии'] });
  out.push({ tag: 'p', children: [c.n
    ? 'Когда я расходился с линией, к началу матча она двигалась в мою сторону в ' + c.toward + ' из ' + c.n + ' матчей (' + pct(c.toward, c.n) + '), против — ' + c.against +
      '. Средний CLV: ' + (c.sum >= 0 ? '+' : '') + String(Math.round(c.sum / c.n * 1000) / 10).replace('.', ',') + '%. Это главный признак, что я вижу то, что рынок учитывает позже.'
    : 'Считаем с конца сентября 2026 года: кэф в момент публикации прогноза против кэфа перед стартом. Цифры появятся после первых матчей.'] });
  // по уверенности
  var buckets = [[0.5, 0.6], [0.6, 0.7], [0.7, 0.8], [0.8, 1.01]], rows = [];
  buckets.forEach(function (b) {
    var xs = a.hist.filter(function (h) { var q = Math.max(h.p, 1 - h.p); return q >= b[0] && q < b[1]; });
    if (!xs.length) return;
    var hit = xs.filter(function (h) { return (h.p >= 0.5 ? 0 : 1) === h.won; }).length;
    rows.push(li(Math.round(b[0] * 100) + '–' + Math.min(100, Math.round(b[1] * 100)) + '%: угадано ' + hit + ' из ' + xs.length + ' (' + pct(hit, xs.length) + ')'));
  });
  if (rows.length) { out.push({ tag: 'h3', children: ['Точность по уверенности'] }); out.push({ tag: 'ul', children: rows }); }
  // последние прогнозы
  var last = a.hist.slice().sort(function (x, y) { return x.key < y.key ? 1 : x.key > y.key ? -1 : 0; }).slice(0, PUBLIC_PAGE_LAST);
  if (last.length) {
    out.push({ tag: 'h3', children: ['Последние прогнозы'] });
    out.push({ tag: 'ul', children: last.map(function (h) {
      var pick = h.p >= 0.5 ? h.home : h.away, pp = Math.round(Math.max(h.p, 1 - h.p) * 100), ok = (h.p >= 0.5 ? 0 : 1) === h.won;
      var bk = h.pm === null ? '' : ', букмекеры ' + Math.round((h.p >= 0.5 ? h.pm : 1 - h.pm) * 100) + '%';
      return li(h.key.slice(8, 10) + '.' + h.key.slice(5, 7) + ' ' + h.home + ' — ' + h.away + ': за ' + pick + ' (' + pp + '%' + bk + ') → ' + h.hg + ':' + h.ag + (h.ot ? ' ОТ/Б' : '') + ' ' + (ok ? '✅' : '❌'));
    }) });
  }
  out.push({ tag: 'h3', children: ['Как я считаю'] });
  out.push({ tag: 'p', children: ['Мои прогнозы строятся на модели: рейтинг Эло, форма, домашняя площадка, усталость, плотность календаря, очные встречи. Прогноз записывается до начала матча и больше не меняется. ' +
    'Brier — средняя ошибка вероятности: он наказывает за уверенные промахи. CLV — насколько кэф при публикации был лучше кэфа перед стартом.'] });
  var ch = publicPageChannelUrl_();
  out.push({ tag: 'p', children: ch ? ['18+. Статистика — не призыв к ставкам. Канал: ', { tag: 'a', attrs: { href: ch }, children: [ch.replace('https://', '')] }] : ['18+. Статистика — не призыв к ставкам.'] });
  return out;
}

/** Создаёт (create=true) или обновляет страницу. {url, created} или null, если страницы нет и create=false. */
function publicPageUpdate_(ss, create) {
  ss = ss || SpreadsheetApp.getActive();
  var p = PropertiesService.getScriptProperties(), token = p.getProperty('PUBLIC_PAGE_TOKEN'), path = p.getProperty('PUBLIC_PAGE_PATH');
  if (!path && !create) return null;
  var ch = publicPageChannelUrl_();
  if (!token) {
    var acc = tph_('createAccount', { short_name: 'hockey', author_name: publicPageAuthor_(), author_url: ch });
    token = acc.access_token; p.setProperty('PUBLIC_PAGE_TOKEN', token);
  }
  var content = JSON.stringify(publicPageContent_(collectMarketData_(ss)));
  var params = { access_token: token, title: publicPageTitle_(), author_name: publicPageAuthor_(), author_url: ch, content: content };
  var res = path ? tph_('editPage/' + path, params) : tph_('createPage', params);
  if (!path) { p.setProperty('PUBLIC_PAGE_PATH', res.path); p.setProperty('PUBLIC_PAGE_URL', res.url); }
  return { url: res.url || p.getProperty('PUBLIC_PAGE_URL'), created: !path };
}

function publicPageNow_() {
  var p = PropertiesService.getScriptProperties();
  if (!p.getProperty('PUBLIC_PAGE_PATH')) {
    var ui = null; try { ui = SpreadsheetApp.getUi(); } catch (e) { ui = null; }
    if (ui && ui.alert('Создать публичную страницу точности на telegra.ph?\n\nЕё увидит любой, у кого есть ссылка: итог сезона, сравнение с букмекерами, закрытие линии и последние ' + PUBLIC_PAGE_LAST +
        ' прогнозов с результатами. Дальше она будет обновляться сама после каждого «Обновить всё».', ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
  }
  try {
    var r = publicPageUpdate_(SpreadsheetApp.getActive(), true);
    uiAlert_((r.created ? '🌐 Страница создана: ' : '🌐 Страница обновлена: ') + r.url +
      '\n\nЗакрепите ссылку в канале (или добавьте в закреплённый пост) — страница открывается прямо в Telegram и обновляется сама.');
  } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}

/* ══════════ 🔎 Разведчик: факты о командах раз в час, итог вам за ~1,5 ч до матча ══════════
 * Раз в час: новые посты Telegram-каналов (лист «Каналы_экспертов») и новости клубов — только про команды,
 * у которых матч в ближайшие SCOUT_LOOKAHEAD_H часов. Всё новое за час — ОДНИМ запросом к Gemini → лист «Факты».
 * Уже прочитанные ссылки помнит скрытый лист «Разведчик_просмотрено», поэтому одно и то же дважды не разбирается.
 * Каждые 15 минут (без интернета и ИИ, только чтение таблицы): у кого матч через ~1,5 часа — свежий сбор и итог вам в личку.
 * По запросу: меню «📩 → мне в ТГ» → «🔎 Разведчик: что нового сейчас» или команда боту /scout.
 * В шансы модели факты сами НЕ попадают: сначала проверим их пользу на сыгранных матчах, включать будете вы. */
var SCOUT_SHEET = 'Факты';
var SCOUT_SEEN_SHEET = 'Разведчик_просмотрено';
var SCOUT_HEADER = ['Найдено (МСК)', 'Команда', 'Игрок', 'Что', 'Что известно', 'До', 'Уверенность', 'Источник', 'Откуда', 'Опубликовано'];
var SCOUT_LOOKAHEAD_H = 36;        // про какие команды собирать: матч в ближайшие N часов
var SCOUT_REPORT_MIN = 90;         // за сколько минут до начала присылать итог
var SCOUT_FACT_DAYS = 3;           // сколько дней факт показывается в отчётах
var SCOUT_MAX_ITEMS = 60;          // не больше N новых постов в одном запросе к ИИ
var SCOUT_SEEN_KEEP = 3000;
var SCOUT_READ_ROWS = 800;          // сколько верхних (свежих) строк «Фактов» читать для отчётов
var SCOUT_TYPES = ['травма', 'возвращение', 'вратарь', 'состав', 'дисквалификация', 'тренер', 'переход', 'другое'];
var SCOUT_ICON = { 'травма': '🩹', 'возвращение': '🔙', 'вратарь': '🧤', 'состав': '📋', 'дисквалификация': '🟥', 'тренер': '🧑‍💼', 'переход': '🔁', 'другое': '•' };

function scoutSheet_(ss) {
  var sh = ss.getSheetByName(SCOUT_SHEET);
  if (!sh) {
    sh = ss.insertSheet(SCOUT_SHEET);
    sh.getRange(1, 1, 1, SCOUT_HEADER.length).setValues([SCOUT_HEADER]).setFontWeight('bold');
    sh.setFrozenRows(1);
    try { sh.setColumnWidth(5, 380); sh.setColumnWidth(8, 220); } catch (e) {}
  }
  return sh;
}
function scoutSeenSheet_(ss) {
  var sh = ss.getSheetByName(SCOUT_SEEN_SHEET);
  if (!sh) { sh = ss.insertSheet(SCOUT_SEEN_SHEET); sh.getRange(1, 1, 1, 2).setValues([['Ссылка', 'Прочитано (МСК)']]); try { sh.hideSheet(); } catch (e) {} }
  return sh;
}

/** Матчи, которые начнутся в (from, to] мс: [{home, away, start: Date, key}]. Время — из журнала коэффициентов. */
function scoutUpcoming_(ss, fromMs, toMs) {
  var out = [], seen = {};
  var sh = ss.getSheetByName(SHEET_ODDS_LOG);
  if (sh && sh.getLastRow() >= 2) sh.getRange(2, 1, sh.getLastRow() - 1, 16).getValues().forEach(function (r) {
    var st = new Date(String(r[15] || '')), home = String(r[3] || '').trim(), away = String(r[4] || '').trim();
    if (!home || !away || isNaN(st.getTime()) || st.getTime() <= fromMs || st.getTime() > toMs) return;
    var k = home + '|' + away; if (seen[k]) return; seen[k] = true;
    out.push({ home: home, away: away, start: st, key: String(r[2] || '') });
  });
  out.sort(function (a, b) { return a.start - b.start; });
  return out;
}

/** Новости клуба (для НХЛ адресов нет — будут только Telegram-каналы). */
function scoutNewsFor_(team) { try { return sportsClubNews_(team) || []; } catch (e) { return []; } }

/** Сбор: новые посты и новости → факты. {items, facts, skipped?, model} */
function scoutCollect_(ss, opts) {
  ss = ss || SpreadsheetApp.getActive(); opts = opts || {};
  var p = agentProps_(), now = Date.now();
  if (!p.getProperty('GEMINI_KEY')) return { skipped: 'нет ключа GEMINI_KEY' };
  var matches = scoutUpcoming_(ss, now, now + SCOUT_LOOKAHEAD_H * 3600000);
  if (!matches.length) { p.setProperty('SCOUT_LAST', String(now)); return { skipped: 'в ближайшие ' + SCOUT_LOOKAHEAD_H + ' ч матчей нет', items: 0, facts: 0 }; }
  var teams = [];
  matches.forEach(function (m) { [m.home, m.away].forEach(function (t) { if (teams.indexOf(t) < 0) teams.push(t); }); });
  if (opts.teams) teams = teams.filter(function (t) { return opts.teams.indexOf(t) >= 0; });
  // что уже читали
  var seenSh = scoutSeenSheet_(ss), seen = {};
  if (seenSh.getLastRow() > 1) seenSh.getRange(2, 1, seenSh.getLastRow() - 1, 1).getValues().forEach(function (r) { seen[String(r[0])] = true; });
  var items = [], add = function (it) { if (!it.url || seen[it.url]) return; seen[it.url] = true; items.push(it); };
  var posts = []; try { posts = expertPostsAll_(ss); } catch (e) { posts = []; }
  posts.forEach(function (x) {
    if (x.date && now - x.date.getTime() > 48 * 3600000) return;
    var club = expertClubTeam_(x.channel);
    var tt = teams.filter(function (t) { return agentMentions_(x.text, t) || club === t; });
    if (tt.length) add({ url: x.url, who: 'Telegram «' + (x.who || x.channel) + '»', text: x.text, date: x.date, teams: tt });
  });
  teams.forEach(function (t) {
    scoutNewsFor_(t).forEach(function (n) {
      if (n.date && now - n.date.getTime() > 48 * 3600000) return;
      add({ url: n.url, who: 'sports.ru', text: String(n.title || '') + (n.text ? '. ' + n.text : ''), date: n.date || null, teams: [t] });
    });
  });
  if (!items.length) { p.setProperty('SCOUT_LAST', String(now)); return { items: 0, facts: 0 }; }
  items.sort(function (a, b) { return (b.date ? b.date.getTime() : 0) - (a.date ? a.date.getTime() : 0); });
  var batch = items.slice(0, SCOUT_MAX_ITEMS);
  var prompt = 'Ты — разведчик хоккейного аналитика. Лига: ' + VIDEO_LEAGUE + '. Сегодня ' + mskNow_('dd.MM.yyyy HH:mm') + ' МСК.\n' +
    'Ниже посты и новости. Вытащи ТОЛЬКО факты, важные для ближайших матчей этих команд: ' + teams.join(', ') + '.\n' +
    'Правила: только то, что прямо написано; ничего не додумывай. Мнения, прогнозы, счёт прошедших матчей, статистику — не бери. ' +
    'Команда — строго из списка выше. Тип — одно из: ' + SCOUT_TYPES.join(', ') + '. Если в тексте нет фактов — не добавляй ничего.\n' +
    'Уверенность: «высокая» — официально (клуб, тренер, заявка) или известный журналист с конкретикой; «средняя» — СМИ без ссылки на клуб; «низкая» — слух.\n' +
    'Верни JSON: {"facts":[{"i":номер поста,"team":"","player":"имя или пусто","type":"","status":"что известно, до 160 знаков","until":"до когда, если сказано, иначе пусто","confidence":""}]}\n\n' +
    batch.map(function (it, k) { return '[' + (k + 1) + '] ' + it.who + (it.date ? ' (' + Utilities.formatDate(it.date, 'Europe/Moscow', 'dd.MM HH:mm') + ')' : '') + ': ' + String(it.text).slice(0, 700); }).join('\n\n');
  var g = agentGemini_(prompt), j = agentJsonSafe_(g.text);
  if (!j) { g = agentGemini_(prompt); j = agentJsonSafe_(g.text); }
  if (!j) throw new Error('модель вернула не JSON');
  // уже известные факты — не дублируем
  var sh = scoutSheet_(ss), known = {}, cut = now - SCOUT_FACT_DAYS * 86400000;
  var norm = function (x) { return String(x || '').toLowerCase().replace(/ё/g, 'е').replace(/[^а-яa-z0-9]+/g, ' ').trim(); };
  scoutFactsRead_(ss).forEach(function (f) { if (f.found.getTime() >= cut) known[norm(f.team) + '|' + norm(f.player) + '|' + f.type + '|' + norm(f.status).slice(0, 40)] = true; });
  var rows = [], stamp = mskNow_('dd.MM.yyyy HH:mm');
  (j.facts || []).forEach(function (f) {
    var it = batch[Number(f.i) - 1], team = String(f.team || '').trim(), type = String(f.type || '').trim().toLowerCase();
    if (!it || teams.indexOf(team) < 0 || !f.status) return;
    if (SCOUT_TYPES.indexOf(type) < 0) type = 'другое';
    var conf = /высок/.test(f.confidence) ? 'высокая' : /низк/.test(f.confidence) ? 'низкая' : 'средняя';
    var key = norm(team) + '|' + norm(f.player) + '|' + type + '|' + norm(f.status).slice(0, 40);
    if (known[key]) return; known[key] = true;
    rows.push([stamp, team, String(f.player || '').trim(), type, String(f.status).slice(0, 200), String(f.until || '').slice(0, 60), conf, it.url, it.who,
      it.date ? Utilities.formatDate(it.date, 'Europe/Moscow', 'dd.MM.yyyy HH:mm') : '']);
  });
  if (rows.length) {
    sh.insertRowsAfter(1, rows.length);
    sh.getRange(2, 1, rows.length, SCOUT_HEADER.length).setNumberFormat('@').setValues(rows);
  }
  // отметить прочитанное (всё из запроса, в том числе без фактов); хвост журнала обрезаем
  var seenRows = batch.map(function (it) { return [it.url, stamp]; });
  seenSh.insertRowsAfter(1, seenRows.length);
  seenSh.getRange(2, 1, seenRows.length, 2).setNumberFormat('@').setValues(seenRows);
  var extra = seenSh.getLastRow() - 1 - SCOUT_SEEN_KEEP;
  if (extra > 0) try { seenSh.deleteRows(SCOUT_SEEN_KEEP + 2, extra); } catch (e) {}
  p.setProperty('SCOUT_LAST', String(now));
  return { items: batch.length, rest: items.length - batch.length, facts: rows.length, model: g.model };
}

/** Факты с листа: [{found: Date, team, player, type, status, until, conf, url, who}] (свежие сверху). */
function scoutFactsRead_(ss) {
  var sh = ss.getSheetByName(SCOUT_SHEET);
  if (!sh || sh.getLastRow() < 2) return [];
  // свежие — сверху: для отчётов и защиты от повторов хватает верхних строк, весь архив не читаем
  return sh.getRange(2, 1, Math.min(sh.getLastRow() - 1, SCOUT_READ_ROWS), SCOUT_HEADER.length).getValues().map(function (r) {
    var m = String(r[0]).match(/(\d\d)\.(\d\d)\.(\d{4}) (\d\d):(\d\d)/);
    var d = r[0] instanceof Date ? r[0] : m ? new Date(Date.UTC(+m[3], +m[2] - 1, +m[1], +m[4] - 3, +m[5])) : null;   // МСК = UTC+3
    return { found: d, team: String(r[1]), player: String(r[2]), type: String(r[3]), status: String(r[4]), until: String(r[5]), conf: String(r[6]), url: String(r[7]), who: String(r[8]) };
  }).filter(function (f) { return f.found && f.team; });
}

/** Факты про команду за последние SCOUT_FACT_DAYS дней. */
function scoutFactsFor_(facts, team) {
  var cut = Date.now() - SCOUT_FACT_DAYS * 86400000;
  return facts.filter(function (f) { return f.team === team && f.found.getTime() >= cut; });
}

/** Для сводки агента: факты Разведчика как «статьи» с источником. */
function scoutFactsDocs_(ss, teams) {
  var all = scoutFactsRead_(ss), out = [];
  teams.forEach(function (t) {
    scoutFactsFor_(all, t).slice(0, 8).forEach(function (f) {
      out.push({ title: 'Разведчик · ' + t + ' · ' + f.type + (f.player ? ' · ' + f.player : '') + ': ' + f.status + (f.conf === 'низкая' ? ' (слух)' : ''), url: f.url, text: '',
        date: Utilities.formatDate(f.found, 'Europe/Moscow', 'dd.MM') });
    });
  });
  return out;
}

/** Текст отчёта по матчам (HTML). */
function scoutReportText_(ss, matches, title) {
  var all = scoutFactsRead_(ss), fresh = Date.now() - 3 * 3600000, lines = ['🔎 <b>РАЗВЕДЧИК</b> · ' + escHtml_(title), ''];
  var prog = {}; try { collectMarketData_(ss).upcoming.forEach(function (m) { prog[m.home + '|' + m.away] = m; }); } catch (e) { prog = {}; }
  matches.forEach(function (m) {
    lines.push('🏒 <b>' + escHtml_(m.home + ' — ' + m.away) + '</b> · ' + Utilities.formatDate(m.start, 'Europe/Moscow', 'HH:mm') + ' МСК');
    var pm = prog[m.home + '|' + m.away];
    if (pm && typeof pm.model.pHome === 'number') lines.push('<i>Модель: ' + escHtml_(m.home) + ' ' + Math.round(pm.model.pHome * 100) + '%' +
      (pm.market && pm.market.pHome !== null ? ' · линия ' + Math.round(pm.market.pHome * 100) + '%' : '') + '</i>');
    var any = false;
    [m.home, m.away].forEach(function (t) {
      var fs = scoutFactsFor_(all, t);
      if (!fs.length) return;
      any = true;
      lines.push('<b>' + escHtml_(t) + '</b>');
      fs.slice(0, 8).forEach(function (f) {
        lines.push((f.found.getTime() >= fresh ? '🆕 ' : '') + (SCOUT_ICON[f.type] || '•') + ' ' + (f.player ? escHtml_(f.player) + ' — ' : '') + escHtml_(f.status) +
          (f.until ? ' (до ' + escHtml_(f.until) + ')' : '') + (f.conf === 'низкая' ? ' <i>(слух)</i>' : '') + ' <a href="' + escHtml_(f.url) + '">источник</a>');
      });
    });
    if (!any) lines.push('Новых фактов за ' + SCOUT_FACT_DAYS + ' дня в открытых источниках нет.');
    lines.push('');
  });
  lines.push('<i>🆕 — найдено за последние 3 часа. Факты — из постов и новостей со ссылками; в шансы модели они сами не попадают.</i>');
  return lines.join('\n');
}

/** Каждый час: сбор (ночью по МСК для КХЛ спит). */
function scoutAuto_() {
  var h = Number(Utilities.formatDate(new Date(), 'Europe/Moscow', 'H'));
  if (SCOUT_QUIET_HOURS.indexOf(h) >= 0) return;
  try { var r = scoutCollect_(SpreadsheetApp.getActive()); autoMark_('scoutAuto_', true, r.skipped ? r.skipped : 'новых постов: ' + r.items + ', фактов: ' + r.facts); }
  catch (e) { autoMark_('scoutAuto_', false, e.message); }
}

/** Каждые 15 минут: у кого матч через ~1,5 часа — свежий сбор и итог вам (матчи одного времени — одним сообщением). */
function scoutReportAuto_() {
  var ss = SpreadsheetApp.getActive(), p = agentProps_(), now = Date.now(), to = p.getProperty('TG_ADMIN_ID');
  if (!to) return;
  var sent = {}; try { sent = JSON.parse(p.getProperty('SCOUT_SENT') || '{}'); } catch (e) { sent = {}; }
  var due = scoutUpcoming_(ss, now, now + SCOUT_REPORT_MIN * 60000).filter(function (m) { return !sent[m.key + '|' + m.home + '|' + m.away]; });
  if (!due.length) return;
  try {
    if (now - Number(p.getProperty('SCOUT_LAST') || 0) > 30 * 60000) {
      var teams = []; due.forEach(function (m) { teams.push(m.home, m.away); });
      scoutCollect_(ss, { teams: teams });
    }
  } catch (e) { /* сбор не удался — пришлём то, что уже известно */ }
  var groups = {};
  due.forEach(function (m) { var k = Utilities.formatDate(m.start, 'Europe/Moscow', 'HH:mm'); (groups[k] = groups[k] || []).push(m); });
  Object.keys(groups).sort().forEach(function (k) {
    var r = tgSendLong_(to, scoutReportText_(ss, groups[k], 'перед матчами в ' + k + ' МСК'));
    if (r.ok) groups[k].forEach(function (m) { sent[m.key + '|' + m.home + '|' + m.away] = mskNow_('dd.MM HH:mm'); });
  });
  var keep = {}, cut = Utilities.formatDate(new Date(now - 3 * 86400000), 'Europe/Moscow', 'yyyy-MM-dd');
  Object.keys(sent).forEach(function (k) { if (k.slice(0, 10) >= cut) keep[k] = sent[k]; });
  p.setProperty('SCOUT_SENT', JSON.stringify(keep));
  autoMark_('scoutReportAuto_', true, 'итог отправлен: ' + due.length + ' ' + ruPlural_(due.length, 'матч', 'матча', 'матчей'));
}

/** По запросу: свежий сбор + картина по матчам ближайших суток. chat — куда (по умолчанию вам). */
function scoutNowTo_(chat) {
  var ss = SpreadsheetApp.getActive(), now = Date.now(), r = {};
  try { r = scoutCollect_(ss); } catch (e) { r = { error: e.message }; }
  var ms = scoutUpcoming_(ss, now, now + 24 * 3600000);
  var head = r.error ? 'сбор не удался (' + r.error + '), показываю известное' : r.skipped ? r.skipped : 'новых постов ' + (r.items || 0) + ', новых фактов ' + (r.facts || 0);
  if (!ms.length) { if (chat) tg_('sendMessage', { chat_id: chat, text: '🔎 Разведчик: в ближайшие сутки матчей нет. (' + head + ')' }); return { matches: 0, head: head }; }
  var sent = chat ? tgSendLong_(chat, scoutReportText_(ss, ms, 'сейчас · ' + head)) : { ok: false };
  return { matches: ms.length, head: head, sent: sent.ok };
}
function scoutNow_() {
  var to = agentProps_().getProperty('TG_ADMIN_ID');
  var r = scoutNowTo_(to);
  sheetOpen_(SCOUT_SHEET);
  uiAlert_('🔎 Разведчик: ' + r.head + '.\nМатчей в ближайшие сутки: ' + r.matches + '.' +
    (to ? (r.sent ? '\nКартина по ним — у вас в Telegram.' : '') : '\nЧтобы получать в Telegram, напишите боту /agent.') + '\nВсе факты со ссылками — на листе «' + SCOUT_SHEET + '».');
}

/* ── Итоги игры — сразу после последнего матча дня, а не в 02:00 МСК ──
 * Когда пост «Матчи дня» видит финальный счёт у всех матчей дня: результаты с sports.ru → расчёт игры → личные итоги игрокам.
 * Ночное «Обновить всё» потом ничего не повторит: рассчитанные выборы второй раз не считаются. */
function gameEarlySettle_(days) {
  var p = PropertiesService.getScriptProperties(), todo = days.filter(function (d) { return !p.getProperty('GAME_EARLY_' + d); });
  if (!todo.length) return null;
  todo.forEach(function (d) { p.setProperty('GAME_EARLY_' + d, mskNow_('HH:mm')); });   // один раз, даже если что-то пойдёт не так
  try { Object.keys(p.getProperties()).forEach(function (k) { if (/^GAME_EARLY_/.test(k) && k.slice(11) < addDaysKey_(todo[0], -3)) p.deleteProperty(k); }); } catch (e) {}
  QUIET_ = true;
  try { updateResultsFromWeb(); } catch (e) { console.log('early results: ' + e.message); }
  finally { QUIET_ = false; }
  var r = gameAfterResults_();
  autoMark_('liveUpdateAuto_', true, 'игра: итоги дня ' + todo.join(', ') + ' — рассчитано ' + (r.settled || 0) + ', ' + (r.sent || []).join('; '));
  return r;
}

/* ══════════════ ✍️ ПОСТ-ПРОГНОЗ НА МАТЧ — готовый текст вам в личку ══════════════
 * За 3–4 часа до каждого матча собираем фактуру и просим ИИ написать пост в вашем стиле:
 * последние игры обеих команд с деталями, кто забивал, что с большинством, кто выбыл и вернулся,
 * график и отдых — и в конце строка «ПРОГНОЗ» с основной ставкой и запасным вариантом.
 *
 * Ставку выбирает не ИИ, а числа: расхождение модели с линией по победителю и по тоталу.
 * ИИ только пишет текст вокруг неё и НЕ знает слов «модель», «таблица», «вероятность» —
 * в тексте их быть не должно, это проверяется отдельно (postClean_).
 *
 * Лист «Посты» — что и когда ушло. Эмодзи клубов — лист «Эмодзи_клубов», правьте как хотите.
 * ==========================================================================*/
var POST_SHEET = 'Посты';
var POST_HEADER = ['День', 'Начало (МСК)', 'Матч', 'Отправлено (МСК)', 'Ставка', 'Кэф', 'Запасная', 'Текст поста'];
var POST_EMOJI_SHEET = 'Эмодзи_клубов';
var POST_LEAD_MIN = 245;            // начинаем готовить за столько минут до начала
var POST_LATE_MIN = 140;            // и не позже, чем за столько
var POST_EDGE_WIN = 0.05;           // перевес по победителю: 5 п.п. к линии
var POST_EDGE_TOT = 0.4;            // расхождение по тоталу: 0,4 шайбы
var POST_LAST_GAMES = 5;            // сколько последних матчей показываем ИИ
var POST_MAX_MS = 260000;           // за один запуск работаем не дольше (лимит Apps Script — 6 минут)
var POST_EMOJI_DEFAULT = [['Авангард', '🦅'], ['Автомобилист', '🏎'], ['Адмирал', '⚓'], ['Ак Барс', '🐆'], ['Амур', '🐅'],
  ['Барыс', '🐆'], ['Динамо Минск', '🦬'], ['Динамо Москва', '⚡'], ['Лада', '🚗'], ['Локомотив', '🚂'], ['Металлург', '🦊'],
  ['Нефтехимик', '🐺'], ['Салават Юлаев', '🏹'], ['Северсталь', '🐗'], ['Сибирь', '❄️'], ['СКА', '⭐'], ['Сочи', '🌴'],
  ['Спартак', '🔴'], ['Торпедо', '🛡'], ['Трактор', '⚙️'], ['Шанхайские Драконы', '🐉'], ['ЦСКА', '🐎']];

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
  return out;
}
function postSheet_(ss) {
  var sh = ss.getSheetByName(POST_SHEET);
  if (!sh) {
    sh = ss.insertSheet(POST_SHEET);
    sh.getRange(1, 1, 1, POST_HEADER.length).setValues([POST_HEADER]).setFontWeight('bold');
    sh.setFrozenRows(1); sh.setColumnWidth(8, 700);
  }
  return sh;
}

/** Последние сыгранные матчи команды: [{date, opp, home, gf, ga, ot}] — свежие первыми. */
function postTeamGames_(ss, team, n) {
  var sh = ss.getSheetByName(SHEET_RESULTS);
  if (!sh || sh.getLastRow() < 2) return [];
  var v = sh.getRange(2, 1, sh.getLastRow() - 1, 8).getValues(), out = [];
  v.forEach(function (r) {
    if (!(r[0] instanceof Date) || String(r[1]).indexOf('Сыгран') < 0) return;
    var h = String(r[2]).trim(), a = String(r[3]).trim();
    if (h !== team && a !== team) return;
    var gh = Number(r[4]), ga = Number(r[5]);
    if (!(gh >= 0 && ga >= 0)) return;
    out.push({ date: r[0], opp: h === team ? a : h, home: h === team, gf: h === team ? gh : ga, ga: h === team ? ga : gh, ot: !!r[6] });
  });
  out.sort(function (x, y) { return y.date - x.date; });
  return out.slice(0, n || POST_LAST_GAMES);
}
/** График: игр за 7 дней и дней отдыха — по календарю, а не по часам (в таблице у матчей только дата). */
function postDayDiff_(a, b) {
  var f = function (d) { return Date.parse(Utilities.formatDate(d, 'Europe/Moscow', 'yyyy-MM-dd')); };
  return Math.round((f(a) - f(b)) / 86400000);
}
function postSchedule_(games, now) {
  if (!games.length) return { week: 0, rest: null };
  var week = games.filter(function (g) { return postDayDiff_(now, g.date) <= 7; }).length;
  return { week: week, rest: postDayDiff_(now, games[0].date) };
}
/** Детали последнего матча команды из приложения КХЛ: счёт по периодам, броски, большинство, авторы голов. */
function postLastProtocol_(ss, team) {
  var sh = ss.getSheetByName(KHLAPP_GAMES_SHEET);
  if (!sh || sh.getLastRow() < 2) return null;
  var v = sh.getRange(2, 1, sh.getLastRow() - 1, 7).getValues(), row = null;
  v.forEach(function (r) {
    if (String(r[2]).trim() !== team && String(r[3]).trim() !== team) return;
    if (!row || String(r[0]) > String(row[0])) row = r;
  });
  if (!row) return null;
  var raw, ev;
  try { raw = khlAppGet_('event_v2.json?id=' + row[1]); } catch (e) { return null; }
  ev = raw && raw.event ? raw.event : raw;
  if (!ev) return null;
  var aId = (ev.team_a || {}).id, home = khlAppTeam_(ev.team_a), away = khlAppTeam_(ev.team_b);
  var s = ev.scores || {}, per = ['first_period', 'second_period', 'third_period', 'overtime', 'bullitt']
    .map(function (k) { return s[k]; }).filter(function (x) { return x && /\d+:\d+/.test(String(x)); });
  var info = khlAppInfo_(ev), shots = info['Броски в створ'] || null;
  var goals = (ev.goals || []).slice().sort(function (x, y) { return (Number(x.time) || 0) - (Number(y.time) || 0); })
    .map(function (g) {
      var forHome = !!(g.author && g.author.team_id === aId);
      return { team: forHome ? home : away, period: Number(g.period) || 0, time: newsClock_(g.time, g.period),
        author: (g.author && g.author.name) || '', assists: (g.assistants || []).map(function (a) { return a.name; }).filter(Boolean),
        kind: String(g.status_abbr || '') };
    });
  return { home: home, away: away, score: String(ev.score || ''), periods: per, shots: shots,
    ppHome: [(ev.team_a || {}).ppg, (ev.team_a || {}).ppc], ppAway: [(ev.team_b || {}).ppg, (ev.team_b || {}).ppc], goals: goals };
}

/** Вся фактура по матчу — то, из чего ИИ пишет пост. */
function postFacts_(ss, m, now) {
  now = now || new Date();
  var odds = {}; try { odds = readOddsLog_(ss); } catch (e) { odds = {}; }
  var o = odds[m.day + '|' + m.home + '|' + m.away] || {};
  var pr = ss.getSheetByName('прогнозы'), model = {};
  if (pr && pr.getLastRow() > 1) {
    pr.getRange(2, 1, pr.getLastRow() - 1, 58).getValues().forEach(function (r) {
      if (!(r[0] instanceof Date) || sheetDayKey_(r[0]) !== m.day) return;
      if (String(r[1]).trim() !== m.home || String(r[2]).trim() !== m.away) return;
      model = { pHome: Number(r[3]) || null, goalsHome: Number(r[6]) || null, goalsAway: Number(r[7]) || null,
        total: Number(r[8]) || null, best: String(r[57] || '') };
    });
  }
  var facts = []; try { facts = scoutFactsRead_(ss); } catch (e) { facts = []; }
  var kp = {}; try { kp = lineupKeyPlayers_(ss); } catch (e) { kp = {}; }
  var dos = {}; try { dos = dossierRead_(ss); } catch (e) { dos = {}; }
  var side = function (team) {
    var games = postTeamGames_(ss, team);
    var st = postSchedule_(games, now);
    var f = [];
    try { f = scoutFactsFor_(facts, team).map(function (x) { return x.type + ': ' + (x.player ? x.player + ' — ' : '') + x.status; }); } catch (e) { f = []; }
    var d = dos[team] || {};
    return { team: team, games: games, week: st.week, rest: st.rest, facts: f.slice(0, 8),
      lineup: kp[team] && kp[team].text ? kp[team].text : '', dossier: [d.form, d.style, d.key].filter(Boolean).join(' · '),
      proto: postLastProtocol_(ss, team) };
  };
  return { m: m, odds: o, model: model, home: side(m.home), away: side(m.away) };
}

/** Вероятность «меньше линии»: шайбы за матч ложатся на распределение Пуассона со средним lam. */
function postUnderProb_(lam, line) {
  if (!(lam > 0) || !(line > 0)) return null;
  var k = Math.floor(line), term = Math.exp(-lam), sum = term;
  for (var i = 1; i <= k; i++) { term *= lam / i; sum += term; }
  return Math.min(0.999, Math.max(0.001, sum));
}
/**
 * Ставка считается по числам, а не по вкусу ИИ: и победа, и тотал приводятся к одному —
 * насколько наша вероятность выше той, что заложена в линию. Сравнивать проценты с шайбами нельзя.
 */
function postPick_(f) {
  var out = [], o = f.odds || {}, mo = f.model || {};
  if (o.pHome !== null && o.pHome !== undefined && mo.pHome) {
    var edge = mo.pHome - o.pHome, team = edge > 0 ? f.m.home : f.m.away;
    var odd = o.mlOdds ? (edge > 0 ? o.mlOdds[0] : o.mlOdds[1]) : null;
    if (Math.abs(edge) >= POST_EDGE_WIN && odd)
      out.push({ kind: 'победа', text: 'ПОБЕДА ' + team.toUpperCase() + ' (С ОТ)', odds: odd, edge: Math.abs(edge), why: 'перевес к линии ' + Math.round(Math.abs(edge) * 100) + ' п.п.' });
  }
  if (o.tot && mo.total && o.tot.over !== null && o.tot.over !== undefined) {
    var pUnder = postUnderProb_(mo.total, o.tot.line), mUnder = 1 - o.tot.over;
    if (pUnder !== null) {
      var eU = pUnder - mUnder, under = eU > 0;                      // перевес там, где наша вероятность выше
      var odd2 = under ? o.tot.underOdds : o.tot.overOdds;
      if (Math.abs(eU) >= POST_EDGE_WIN && Math.abs(mo.total - o.tot.line) >= POST_EDGE_TOT && odd2)
        out.push({ kind: 'тотал', text: 'ОБЩИЙ ТОТАЛ ' + o.tot.line + (under ? ' МЕНЬШЕ' : ' БОЛЬШЕ'), odds: odd2, edge: Math.abs(eU),
          why: 'ожидаемая результативность ' + mo.total.toFixed(1) + ' против линии ' + o.tot.line + ', перевес ' + Math.round(Math.abs(eU) * 100) + ' п.п.' });
    }
  }
  out.sort(function (a, b) { return b.edge - a.edge; });
  return { main: out[0] || null, alt: out[1] || null };
}

/* ---------------- запрос к ИИ ---------------- */
function postSideText_(s) {
  var g = s.games.map(function (x) {
    return Utilities.formatDate(x.date, 'Europe/Moscow', 'dd.MM') + ' ' + (x.home ? 'дома' : 'в гостях') + ' с «' + x.opp + '» ' + x.gf + ':' + x.ga + (x.ot ? ' (ОТ/Б)' : '');
  }).join('; ');
  var p = s.proto, lines = ['КОМАНДА: ' + s.team, 'Последние матчи: ' + (g || 'нет данных'),
    'Игр за 7 дней: ' + s.week + (s.rest === null ? '' : ', дней отдыха после последнего: ' + s.rest)];
  if (p) {
    lines.push('Протокол последнего матча: ' + p.home + ' ' + p.score + ' ' + p.away +
      (p.periods.length ? ' (по периодам ' + p.periods.join(', ') + ')' : '') +
      (p.shots ? ', броски в створ ' + p.shots[0] + ':' + p.shots[1] : ''));
    var pp = s.team === p.home ? p.ppHome : p.ppAway;
    if (pp && pp[1]) lines.push('Большинство в том матче: ' + (pp[0] || 0) + ' из ' + pp[1]);
    if (p.goals.length) lines.push('Голы того матча: ' + p.goals.map(function (x) {
      return x.team + ', ' + x.period + '-й период ' + x.time + ' — ' + x.author + (x.assists.length ? ' (' + x.assists.join(', ') + ')' : '') + (x.kind ? ' [' + x.kind + ']' : '');
    }).join('; '));
  }
  if (s.lineup) lines.push('Заявка прошлого матча: ' + s.lineup);
  if (s.facts.length) lines.push('Новости по составу: ' + s.facts.join('; '));
  if (s.dossier) lines.push('Про команду: ' + s.dossier);
  return lines.join('\n');
}
function postPrompt_(f, pick, emo) {
  var m = f.m, head = '🏒КХЛ. ' + (emo[m.home] || '') + m.home.toUpperCase() + ' - ' + m.away.toUpperCase() + (emo[m.away] || '');
  var bet = pick.main ? 'ПРОГНОЗ: ' + (emo[m.home] || '') + (emo[m.away] || '') + pick.main.text + ' ЗА ' + pick.main.odds : '';
  return 'Ты ведёшь телеграм-канал с прогнозами на хоккей и пишешь пост о матче КХЛ. Пиши по-русски, от первого лица, спокойно.\n\n' +
    'СТРОГИЕ ЗАПРЕТЫ. Никогда не упоминай таблицу, модель, алгоритм, расчёты, статистику «по данным», проценты вероятности и коэффициенты в тексте (кроме последней строки). ' +
    'Не выдумывай ни одной фамилии, даты и счёта — бери только из фактов ниже. Чего нет в фактах — того не пиши. ' +
    'Не обращайся к читателю («друзья», «подписывайтесь»), не обещай выигрыш, не зови делать ставки.\n\n' +
    'СТРУКТУРА (6–7 абзацев, пустая строка между ними):\n' +
    '1. Заголовок ровно такой строкой: ' + head + '\n' +
    '2–3. Про хозяев: последний матч — как он шёл, кто забивал, что с большинством, кто вернулся или выбыл.\n' +
    '4–5. Про гостей: то же самое.\n' +
    '6. Своё рассуждение: график, отдых, что смущает, к чему склоняешься. Здесь можно сомневаться вслух.\n' +
    (bet ? '7. Последняя строка ровно такая: ' + bet + '\n' : '7. Последняя строка: «Ставку не делаю».\n') +
    '\nФАКТЫ О ХОЗЯЕВАХ\n' + postSideText_(f.home) +
    '\n\nФАКТЫ О ГОСТЯХ\n' + postSideText_(f.away) +
    '\n\nМАТЧ: ' + m.home + ' — ' + m.away + ', начало ' + (f.odds.startText || m.time || '') + ' МСК.' +
    (pick.main ? '\nК чему склоняешься: ' + pick.main.text.toLowerCase() + ' (' + pick.main.why + '). Объясни это своими словами, через игру команд, а не через числа.' : '');
}
/** Подчищаем то, чего в посте быть не должно: упоминания таблицы и служебных слов. */
var POST_BANNED_ = /таблиц|модел|алгоритм|нейросет|по данным|вероятн|наш расч|расч[её]т|датасет|статистическ/i;
function postClean_(text) {
  return String(text || '').split(/\n{2,}/).filter(function (p) { return !POST_BANNED_.test(p) || /ПРОГНОЗ:/.test(p); })
    .join('\n\n').replace(/\n{3,}/g, '\n\n').trim();
}

function postBuild_(ss, m, now) {
  var emo = postEmoji_(ss), f = postFacts_(ss, m, now), pick = postPick_(f);
  var raw = agentGemini_(postPrompt_(f, pick, emo));
  var text = postClean_(typeof raw === 'string' ? raw : (raw && raw.text) || '');
  if (POST_BANNED_.test(text)) {                       // одна попытка переписать, если проскочило
    raw = agentGemini_(postPrompt_(f, pick, emo) + '\n\nВ прошлый раз ты упомянул расчёты и таблицу — так нельзя. Перепиши без этого.');
    text = postClean_(typeof raw === 'string' ? raw : (raw && raw.text) || '');
  }
  return { text: text, pick: pick, facts: f };
}

/** Собрать и отправить пост по одному матчу: карточка, текст, запасной вариант. */
function postSendOne_(ss, m, now) {
  var to = PropertiesService.getScriptProperties().getProperty('TG_ADMIN_ID');
  if (!to) throw new Error('не указан ваш Telegram — напишите боту /agent');
  var r = postBuild_(ss, m, now);
  if (!r.text) return { sent: false };
  try { var b = bannersBuild_(m.day, 0, [m]); if (b.blobs.length) tgSendPhotos_(to, b.blobs, ''); } catch (e) { console.log('карточка: ' + e.message); }
  tgSendLong_(to, escHtml_(r.text));
  if (r.pick.alt) tgRaw_('sendMessage', { chat_id: to, text: '↔️ Запасной вариант: ' + r.pick.alt.text + ' за ' + r.pick.alt.odds + ' (' + r.pick.alt.why + ')' });
  var sh = postSheet_(ss);
  sh.insertRowsBefore(2, 1);
  sh.getRange(2, 1, 1, POST_HEADER.length).setValues([[m.day, m.time || '', m.home + ' — ' + m.away, mskNow_('dd.MM HH:mm'),
    r.pick.main ? r.pick.main.text : 'без ставки', r.pick.main ? r.pick.main.odds : '', r.pick.alt ? r.pick.alt.text + ' за ' + r.pick.alt.odds : '', r.text]]);
  return { sent: true, pick: r.pick.main };
}

/** Какие матчи пора описывать: начало через POST_LATE_MIN…POST_LEAD_MIN минут, пост ещё не уходил. */
function postDue_(ss, now) {
  var sh = ss.getSheetByName(SHEET_ODDS_LOG), out = [];
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, ODDS_HEADER.length).getValues().forEach(function (r) {
    var start = new Date(String(r[15]));
    if (isNaN(start.getTime())) return;
    var mins = (start - now) / 60000;
    if (mins < POST_LATE_MIN || mins > POST_LEAD_MIN) return;
    out.push({ day: String(r[2]), time: String(r[1]).slice(11), home: String(r[3]).trim(), away: String(r[4]).trim() });
  });
  out.sort(function (a, b) { return a.time < b.time ? -1 : 1; });
  return out;
}
function postSentKey_(m) { return 'POST_' + m.day + '_' + m.home + '_' + m.away; }

function postAuto_() {
  var p = PropertiesService.getScriptProperties();
  if (p.getProperty('POST_OFF') === '1' || !p.getProperty('GEMINI_KEY')) return;
  var ss = SpreadsheetApp.getActive(), now = new Date(), t0 = Date.now(), done = 0;
  var due = postDue_(ss, now).filter(function (m) { return !p.getProperty(postSentKey_(m)); });
  due.forEach(function (m) {
    if (Date.now() - t0 > POST_MAX_MS) return;
    p.setProperty(postSentKey_(m), mskNow_('dd.MM HH:mm'));      // один раз на матч, даже если что-то упадёт
    try { if (postSendOne_(ss, m, now).sent) done++; }
    catch (e) { autoMark_('postAuto_', false, m.home + ' — ' + m.away + ': ' + e.message); }
  });
  if (done) autoMark_('postAuto_', true, 'постов отправлено: ' + done);
}

/* ---------------- кнопки ---------------- */
function postNowMenu_() {
  var ss = SpreadsheetApp.getActive(), now = new Date();
  var day = agentMskDay_(), list = agentMatchesOfDay_(ss, day);
  if (!list.length) { uiAlert_('Сегодня матчей нет.'); return; }
  var ui = SpreadsheetApp.getUi();
  var r = ui.prompt('Пост-прогноз', 'Матчи сегодня:\n' + list.map(function (m, i) { return (i + 1) + ') ' + m.time + '  ' + m.home + ' — ' + m.away; }).join('\n') +
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
function postToggle_() {
  var p = PropertiesService.getScriptProperties(), off = p.getProperty('POST_OFF') === '1';
  if (off) p.deleteProperty('POST_OFF'); else p.setProperty('POST_OFF', '1');
  uiAlert_('Автоматические посты-прогнозы ' + (off ? 'включены' : 'выключены') + '.');
}

/* ══════════════ 📰 НОВОСТНОЙ КАНАЛ: лайв матчей и лента новостей ══════════════
 * Отдельный канал (свойство NEWS_CHANNEL) — без ставок: счёт по ходу матча, голы, новости клубов.
 *  • Лайв: раз в минуту, пока идут матчи, читаем протокол матча у лиги и публикуем новые события.
 *    Каждое событие уходит ровно один раз — его ключ пишется в скрытый лист «Лайв_лог».
 *  • Лента: раз в час берём свежие факты Разведчика и публикуем короткие заметки,
 *    не больше NEWS_MAX_DAY за сутки. Видео мы не перезаливаем — только ссылка на официальный ролик.
 *  • Источник событий свой у каждой лиги: КХЛ — приложение КХЛ, НХЛ — api-web (см. nhlLiveEvents_).
 * ==========================================================================*/
var NEWS_LIVE_SHEET = 'Лайв_лог';
var NEWS_QUEUE_SHEET = 'Новости';
var NEWS_LIVE_HEADER = ['Время (МСК)', 'Матч', 'Событие', 'Ключ', 'Текст поста'];
var NEWS_QUEUE_HEADER = ['Время (МСК)', 'Команда', 'Что', 'Текст поста', 'Источник', 'Статус'];
var NEWS_MAX_DAY = 12;              // сколько заметок ленты публикуем автоматом за сутки
var NEWS_FEED_HOURS = 4;            // насколько свежие факты берём в ленту
var NEWS_FEED_MAX = 3;              // сколько заметок за один запуск
var NEWS_LIVE_KEEP = 4000;          // строк лайв-лога держим
var NEWS_LIVE_BACK_H = 5;           // матч считается «идущим» столько часов после начала

function newsChannel_() { return PropertiesService.getScriptProperties().getProperty('NEWS_CHANNEL') || ''; }
function newsLiveOn_() { return !!newsChannel_() && PropertiesService.getScriptProperties().getProperty('NEWS_LIVE_OFF') !== '1'; }
function newsFeedOn_() { return !!newsChannel_() && PropertiesService.getScriptProperties().getProperty('NEWS_FEED_OFF') !== '1'; }

function newsLiveSheet_(ss) {
  var sh = ss.getSheetByName(NEWS_LIVE_SHEET);
  if (!sh) {
    sh = ss.insertSheet(NEWS_LIVE_SHEET);
    sh.getRange(1, 1, 1, NEWS_LIVE_HEADER.length).setValues([NEWS_LIVE_HEADER]).setFontWeight('bold');
    try { sh.hideSheet(); } catch (e) {}
  }
  return sh;
}
/** Ключи уже опубликованных событий (свежие сверху). */
function newsSeen_(ss) {
  var sh = newsLiveSheet_(ss), out = {};
  if (sh.getLastRow() < 2) return out;
  sh.getRange(2, 4, Math.min(sh.getLastRow() - 1, NEWS_LIVE_KEEP), 1).getValues().forEach(function (r) { if (r[0]) out[String(r[0])] = 1; });
  return out;
}
function newsRemember_(ss, rows) {
  var sh = newsLiveSheet_(ss);
  sh.insertRowsBefore(2, rows.length);
  sh.getRange(2, 1, rows.length, NEWS_LIVE_HEADER.length).setValues(rows);
  if (sh.getLastRow() > NEWS_LIVE_KEEP + 1) sh.deleteRows(NEWS_LIVE_KEEP + 2, sh.getLastRow() - NEWS_LIVE_KEEP - 1);
}

/** Отправка в новостной канал; при отказе — одна повторная попытка. */
function newsSend_(text, withLink) {
  var chat = newsChannel_();
  if (!chat) return { ok: false, description: 'канал не указан' };
  var p = { chat_id: chat, text: text, parse_mode: 'HTML', disable_web_page_preview: !withLink };
  var r = tg_('sendMessage', p);
  if (!r || !r.ok) r = tg_('sendMessage', p);
  return r || { ok: false };
}

/* ---------------- тексты лайва ---------------- */
var NEWS_PERIOD_ORD_ = ['', 'ПЕРВОМ', 'ВТОРОМ', 'ТРЕТЬЕМ'];
var NEWS_PERIOD_NOM_ = ['', 'ПЕРВЫЙ', 'ВТОРОЙ', 'ТРЕТИЙ'];
function newsPeriodIn_(p) { return NEWS_PERIOD_ORD_[p] ? NEWS_PERIOD_ORD_[p] + ' ПЕРИОДЕ' : (p >= 4 ? 'ОВЕРТАЙМЕ' : ''); }
function newsPeriodNom_(p) { return NEWS_PERIOD_NOM_[p] || (p >= 4 ? 'ОВЕРТАЙМ' : ''); }
/** Секунды от начала матча → «12:34» внутри своего периода. */
function newsClock_(sec, period) {
  var s = Math.max(0, Math.round(Number(sec) || 0) - (Math.max(1, Number(period) || 1) - 1) * 1200);
  return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2);
}
/** Заголовок гола: кто забил и что это дало по счёту. */
function newsGoalHead_(g) {
  var my = g.forHome ? g.hs : g.as, their = g.forHome ? g.as : g.hs, who = g.forHome ? 'ХОЗЯЕВА' : 'ГОСТИ';
  var team = String(g.team || '').toUpperCase();
  if (my === 1 && their === 0) return 'ЗАБИВАЕТ ' + team + '! ОТКРЫТ СЧЁТ';
  if (my === their) return 'ЗАБИВАЕТ ' + team + '! СЧЁТ СРАВНЯЛСЯ';
  if (my - their === 1) return 'ЗАБИВАЕТ ' + team + '! ' + who + ' ВПЕРЕДИ';
  if (my > their) return 'ЗАБИВАЕТ ' + team + '! ОТРЫВ В ' + (my - their) + ' ШАЙБЫ';
  return 'ЗАБИВАЕТ ' + team + '! ОТСТАВАНИЕ СОКРАЩЕНО';
}
/**
 * Пост о голе. g: {home, away, team, forHome, hs, as, period, sec, author, assists, kind, video}
 * kind — 'PP' (большинство), 'SH' (меньшинство), 'EN' (в пустые), 'PS'/'GWS' (буллит).
 */
function newsGoalText_(g) {
  var extra = { PP: 'в большинстве', SH: 'в меньшинстве', EN: 'в пустые ворота', PS: 'буллит', GWS: 'победный буллит' }[String(g.kind || '').toUpperCase()] || '';
  var when = newsPeriodIn_(g.period);
  var line2 = (g.author ? '🏒 ' + escHtml_(g.author) : '');
  if (g.author && g.assists && g.assists.length) line2 += ' (' + g.assists.map(escHtml_).join(', ') + ')';
  if (extra) line2 += (line2 ? ' · ' : '🏒 ') + extra;
  return '🚨 <b>' + escHtml_(newsGoalHead_(g)) + (when ? ' В ' + when + '!' : '!') + '</b>\n' +
    teamMark_(g.home) + ' <b>' + g.hs + ':' + g.as + '</b> ' + teamMark_(g.away) +
    (g.period ? '  ·  ' + newsClock_(g.sec, g.period) : '') +
    (line2 ? '\n' + line2 : '') +
    (g.video ? '\n\n▶️ <a href="' + escHtml_(g.video) + '">Момент на сайте лиги</a>' : '');
}
function newsStartText_(home, away) { return '🏒 <b>МАТЧ НАЧАЛСЯ</b>\n' + teamMark_(home) + ' — ' + teamMark_(away); }
function newsPeriodText_(home, away, period, score) {
  return '⏸ <b>' + newsPeriodNom_(period) + ' ПЕРИОД ПОЗАДИ</b>\n' + teamMark_(home) + ' <b>' + score + '</b> ' + teamMark_(away);
}
function newsFinalText_(home, away, score, end, byPeriods) {
  return '🏁 <b>ФИНАЛЬНАЯ СИРЕНА</b>\n' + teamMark_(home) + ' <b>' + score + '</b> ' + teamMark_(away) + (end ? ' (' + end + ')' : '') +
    (byPeriods && byPeriods.length ? '\n<i>По периодам: ' + byPeriods.join(', ') + '</i>' : '');
}

/* ---------------- источник событий: КХЛ (приложение лиги) ---------------- */
/** Матчи, которые идут прямо сейчас (или только что закончились). */
function khlLiveMatches_() {
  var now = Math.floor(Date.now() / 1000);
  return khlAppEvents_(now - NEWS_LIVE_BACK_H * 3600, now + 300).filter(function (e) { return e.state !== 'not_yet_started'; });
}
/** Новые события матча КХЛ: [{kind, key, text, video}] в порядке появления. */
function khlLiveEvents_(m) {
  var raw = khlAppGet_('event_v2.json?id=' + m.id), ev = raw && raw.event ? raw.event : raw;
  if (!ev) return [];
  var home = m.home || khlAppTeam_(ev.team_a), away = m.away || khlAppTeam_(ev.team_b), aId = (ev.team_a || {}).id;
  var goals = (ev.goals || []).slice().sort(function (x, y) { return (Number(x.time) || 0) - (Number(y.time) || 0); });
  var out = [];
  if (Number(ev.period) >= 1 || goals.length || ev.game_state_key === 'finished')
    out.push({ kind: 'старт', key: 's:' + m.id, text: newsStartText_(home, away) });
  goals.forEach(function (g) {
    var sc = String(g.score || '').split(':');
    if (sc.length !== 2) return;
    var forHome = !!(g.author && g.author.team_id === aId);
    var vid = g.quote && g.quote.video ? String(g.quote.video) : '';
    out.push({
      kind: 'гол', key: 'g:' + m.id + ':' + g.period + ':' + g.time + ':' + g.score, video: vid,
      text: newsGoalText_({ home: home, away: away, team: forHome ? home : away, forHome: forHome, hs: Number(sc[0]), as: Number(sc[1]),
        period: Number(g.period) || 0, sec: Number(g.time) || 0, author: g.author && g.author.name, kind: g.status_abbr,
        assists: (g.assistants || []).map(function (a) { return a.name; }).filter(Boolean), video: /^https?:\/\//.test(vid) ? vid : '' })
    });
  });
  (ev.text_events || []).forEach(function (t) {
    if (String(t.type) !== 'state') return;
    var mm = String(t.text || '').match(/(?:конец|окончание)\s+(\d)[-\s]*го\s+период/i);
    if (!mm || Number(mm[1]) > 3) return;
    out.push({ kind: 'период', key: 'p:' + m.id + ':' + mm[1], text: newsPeriodText_(home, away, Number(mm[1]), String(t.score || ev.score || '')) });
  });
  if (ev.game_state_key === 'finished') {
    var s = ev.scores || {}, by = ['first_period', 'second_period', 'third_period', 'overtime', 'bullitt']
      .map(function (k) { return s[k]; }).filter(function (x) { return x && /\d+:\d+/.test(String(x)); });
    out.push({ kind: 'финал', key: 'f:' + m.id, text: newsFinalText_(home, away, String(ev.score || ''), s.bullitt ? 'буллиты' : s.overtime ? 'овертайм' : '', by) });
  }
  return out;
}

/* ---------------- общий цикл лайва ---------------- */
function newsLiveMatches_() { return typeof nhlLiveMatches_ === 'function' ? nhlLiveMatches_() : khlLiveMatches_(); }
function newsLiveEventsOf_(m) { return typeof nhlLiveEvents_ === 'function' ? nhlLiveEvents_(m) : khlLiveEvents_(m); }

function newsLiveTick_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  if (!newsLiveOn_()) return { matches: 0, posted: 0, off: true };
  var ms = [];
  try { ms = newsLiveMatches_() || []; } catch (e) { return { matches: 0, posted: 0, error: e.message }; }
  if (!ms.length) return { matches: 0, posted: 0 };
  var seen = newsSeen_(ss), rows = [], posted = 0, failed = 0;
  ms.forEach(function (m) {
    if (seen['f:' + m.id]) return;                       // матч уже отсалютовал финалом — больше не дёргаем
    var evs = [];
    try { evs = newsLiveEventsOf_(m) || []; } catch (e) { console.log('лайв ' + m.id + ': ' + e.message); return; }
    evs.forEach(function (e) {
      if (!e || !e.key || seen[e.key]) return;
      seen[e.key] = 1;
      var r = newsSend_(e.text, !!e.video);
      if (r && r.ok) posted++; else failed++;
      rows.push([mskNow_('dd.MM HH:mm:ss'), (m.home || '') + ' — ' + (m.away || ''), e.kind + (r && r.ok ? '' : ' (не ушло)'), e.key,
        String(e.text).replace(/<[^>]+>/g, '').slice(0, 300)]);
    });
  });
  if (rows.length) newsRemember_(ss, rows);
  return { matches: ms.length, posted: posted, failed: failed };
}
function newsLiveAuto_() {
  if (!newsLiveOn_()) return;
  try {
    var r = newsLiveTick_();
    if (r.posted || r.failed) autoMark_('newsLiveAuto_', !r.failed, 'опубликовано событий: ' + r.posted + (r.failed ? ', не ушло ' + r.failed : ''));
  } catch (e) { autoMark_('newsLiveAuto_', false, e.message); }
}

/* ---------------- лента новостей из фактов Разведчика ---------------- */
function newsQueueSheet_(ss) {
  var sh = ss.getSheetByName(NEWS_QUEUE_SHEET);
  if (!sh) {
    sh = ss.insertSheet(NEWS_QUEUE_SHEET);
    sh.getRange(1, 1, 1, NEWS_QUEUE_HEADER.length).setValues([NEWS_QUEUE_HEADER]).setFontWeight('bold');
    sh.setFrozenRows(1); sh.setColumnWidth(4, 520);
  }
  return sh;
}
function newsDayCount_() {
  var p = PropertiesService.getScriptProperties(), k = 'NEWS_DAY_' + todayKey_();
  return { key: k, n: Number(p.getProperty(k) || 0) };
}
/** Факты, из которых ещё не делали заметку: свежие, с командой и внятным текстом. */
function newsFeedPick_(ss, hours) {
  var lim = Date.now() - (hours || NEWS_FEED_HOURS) * 3600000, seen = {};
  newsQueueSheet_(ss);
  var q = ss.getSheetByName(NEWS_QUEUE_SHEET);
  if (q.getLastRow() > 1) q.getRange(2, 1, Math.min(q.getLastRow() - 1, 500), NEWS_QUEUE_HEADER.length).getValues()
    .forEach(function (r) { seen[String(r[1]) + '|' + String(r[4])] = 1; });
  return scoutFactsRead_(ss).filter(function (f) {
    return f.found && f.found.getTime() >= lim && f.team && f.status && String(f.conf).indexOf('низк') < 0 && !seen[f.team + '|' + f.url];
  }).slice(0, 12);
}
/** Просит ИИ превратить факты в короткие новостные заметки. Возвращает [{i, text}]. */
function newsFeedWrite_(facts) {
  if (!facts.length) return [];
  var list = facts.map(function (f, i) {
    return i + ') ' + f.team + (f.player ? ' · ' + f.player : '') + ' · ' + f.type + ': ' + f.status + (f.who ? ' (' + f.who + ')' : '');
  }).join('\n');
  var prompt = 'Ты ведёшь новостной хоккейный телеграм-канал про ' + VIDEO_LEAGUE + '. ' +
    'Ниже сырые факты. Сделай из подходящих короткие новостные заметки на русском.\n' +
    'Правила: 1–2 предложения, спокойный новостной тон, без ставок, коэффициентов, прогнозов и обращений к читателю. ' +
    'Не выдумывай ничего сверх факта. Не пиши «источник сообщает». Если факт пустой, слухи или не новость — пропусти его.\n' +
    'Ответь ТОЛЬКО JSON-массивом: [{"i": номер факта, "text": "текст заметки"}]\n\n' + list;
  var raw = agentGemini_(prompt), arr = agentJsonSafe_(raw);
  if (!Array.isArray(arr)) return [];
  return arr.filter(function (x) { return x && facts[Number(x.i)] && String(x.text || '').trim().length > 20; })
    .map(function (x) { return { i: Number(x.i), text: String(x.text).trim() }; });
}
function newsFeedTick_(ss, max) {
  ss = ss || SpreadsheetApp.getActive();
  if (!newsFeedOn_()) return { posted: 0, off: true };
  var day = newsDayCount_();
  var room = Math.min(max || NEWS_FEED_MAX, NEWS_MAX_DAY - day.n);
  if (room <= 0) return { posted: 0, limit: true };
  var facts = newsFeedPick_(ss);
  if (!facts.length) return { posted: 0 };
  var notes = newsFeedWrite_(facts).slice(0, room), q = newsQueueSheet_(ss), rows = [], posted = 0;
  notes.forEach(function (n) {
    var f = facts[n.i];
    var text = '📰 <b>' + escHtml_(f.team) + '</b>\n' + escHtml_(n.text) + (f.url ? '\n\n<a href="' + escHtml_(f.url) + '">Источник</a>' : '');
    var r = newsSend_(text, !!f.url);
    if (r && r.ok) posted++;
    rows.push([mskNow_('dd.MM HH:mm'), f.team, f.type, n.text, f.url, r && r.ok ? 'опубликовано' : 'не ушло: ' + ((r && r.description) || '')]);
  });
  if (rows.length) {
    q.insertRowsBefore(2, rows.length);
    q.getRange(2, 1, rows.length, NEWS_QUEUE_HEADER.length).setValues(rows);
  }
  if (posted) PropertiesService.getScriptProperties().setProperty(day.key, String(day.n + posted));
  return { posted: posted, facts: facts.length };
}
function newsFeedAuto_() {
  if (!newsFeedOn_()) return;
  try { var r = newsFeedTick_(); if (r.posted) autoMark_('newsFeedAuto_', true, 'заметок опубликовано: ' + r.posted); }
  catch (e) { autoMark_('newsFeedAuto_', false, e.message); }
}

/* ---------------- пункты меню ---------------- */
function newsSetupNow_() {
  var ui = SpreadsheetApp.getUi(), p = PropertiesService.getScriptProperties(), cur = newsChannel_();
  var r = ui.prompt('Новостной канал', 'Username канала для новостей, например @hockey_live' + (cur ? ' (сейчас ' + cur + ')' : '') +
    '.\nБот должен быть его администратором с правом публиковать. Пустое поле — отключить.', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var v = String(r.getResponseText() || '').trim();
  if (!v) { p.deleteProperty('NEWS_CHANNEL'); uiAlert_('Новостной канал отключён.'); return; }
  p.setProperty('NEWS_CHANNEL', /^-?\d+$/.test(v) || v.charAt(0) === '@' ? v : '@' + v);
  var c = tg_('getChat', { chat_id: newsChannel_() });
  uiAlert_(c && c.ok ? 'Канал ' + newsChannel_() + ' («' + ((c.result && c.result.title) || '') + '») подключён.\n\nДальше: «Включить всю автоматику» — появятся лайв и лента.'
    : 'Сохранил ' + newsChannel_() + ', но Telegram его не видит: ' + ((c && c.description) || '') + '. Проверьте имя канала и права бота.');
}
function newsLiveToggle_() {
  var p = PropertiesService.getScriptProperties(), off = p.getProperty('NEWS_LIVE_OFF') === '1';
  if (off) p.deleteProperty('NEWS_LIVE_OFF'); else p.setProperty('NEWS_LIVE_OFF', '1');
  uiAlert_('Лайв-трансляция ' + (off ? 'включена' : 'выключена') + '.\n\nЧтобы изменение вступило в силу, запустите «Включить всю автоматику».');
}
function newsFeedToggle_() {
  var p = PropertiesService.getScriptProperties(), off = p.getProperty('NEWS_FEED_OFF') === '1';
  if (off) p.deleteProperty('NEWS_FEED_OFF'); else p.setProperty('NEWS_FEED_OFF', '1');
  uiAlert_('Лента новостей ' + (off ? 'включена' : 'выключена') + '.');
}
function newsLiveNow_() {
  try {
    var r = newsLiveTick_();
    uiAlert_(r.off ? 'Лайв выключен или канал не подключён.' :
      'Матчей сейчас: ' + r.matches + '.\nОпубликовано событий: ' + r.posted + (r.failed ? '\nНе ушло: ' + r.failed : '') +
      (r.error ? '\nИсточник не ответил: ' + r.error : '') + '\n\nЧто уходило — на листе «' + NEWS_LIVE_SHEET + '».');
  } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}
function newsFeedNow_() {
  try {
    var r = newsFeedTick_();
    uiAlert_(r.off ? 'Лента выключена или канал не подключён.' : r.limit ? 'На сегодня лимит заметок (' + NEWS_MAX_DAY + ') уже выбран.' :
      'Свежих фактов: ' + (r.facts || 0) + '.\nЗаметок опубликовано: ' + r.posted + '.\n\nВсё, что ушло, — на листе «' + NEWS_QUEUE_SHEET + '».');
    sheetOpen_(NEWS_QUEUE_SHEET);
  } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}
/** Бесплатная проверка: что источник лиги отдаёт по идущим матчам прямо сейчас. */
function newsLiveDiag_() {
  try {
    var ms = newsLiveMatches_() || [];
    if (!ms.length) { uiAlert_('Сейчас идущих матчей нет — проверять нечего. Запустите во время игры.'); return; }
    var lines = ms.slice(0, 5).map(function (m) {
      var evs = [];
      try { evs = newsLiveEventsOf_(m) || []; } catch (e) { return '❌ ' + m.home + ' — ' + m.away + ': ' + e.message; }
      var by = {}; evs.forEach(function (e) { by[e.kind] = (by[e.kind] || 0) + 1; });
      return '✅ ' + m.home + ' — ' + m.away + ': ' + (Object.keys(by).map(function (k) { return k + ' ' + by[k]; }).join(', ') || 'событий пока нет');
    });
    uiAlert_('Источник лайва (' + VIDEO_LEAGUE + '):\n\n' + lines.join('\n') + '\n\nЭто только чтение, в канал ничего не ушло.');
  } catch (e) { uiAlert_('Источник не ответил: ' + e.message); }
}
function newsMenu_(ui, title) {
  ui.createMenu(title)
    .addItem('Подключить канал новостей', 'newsSetupNow_')
    .addItem('Проверить источник лайва (бесплатно)', 'newsLiveDiag_')
    .addSeparator()
    .addItem('Лайв: проверить и опубликовать сейчас', 'newsLiveNow_')
    .addItem('Лента: собрать заметки и опубликовать', 'newsFeedNow_')
    .addSeparator()
    .addItem('Лайв: включить / выключить', 'newsLiveToggle_')
    .addItem('Ленту: включить / выключить', 'newsFeedToggle_')
    .addToUi();
}

/* ══════════ 📊 «Сила команд» — по понедельникам в канал ══════════
 * Рейтинг Elo после всех матчей с изменением мест за неделю (↑↓). Текстом, с кружками цветов клубов. */
function powerText_(ss) {
  var sh = ss.getSheetByName('Elo_история');
  if (!sh || sh.getLastRow() < 3) return null;
  var v = sh.getDataRange().getValues(), head = v[0], rows = v.slice(1).filter(function (r) { return r[0] instanceof Date; });
  if (!rows.length) return null;
  var last = rows[rows.length - 1], weekAgo = last[0].getTime() - 7 * 86400000, prev = rows[0];
  rows.forEach(function (r) { if (r[0].getTime() <= weekAgo + 6 * 3600000) prev = r; });
  var rank = function (row) {
    var list = [];
    for (var c = 1; c < head.length; c++) if (String(head[c]).trim() && typeof row[c] === 'number') list.push({ team: String(head[c]).trim(), elo: row[c] });
    list.sort(function (a, b) { return b.elo - a.elo; });
    var pos = {}; list.forEach(function (x, i) { pos[x.team] = i + 1; }); return { list: list, pos: pos };
  };
  var now = rank(last), was = rank(prev);
  var lines = now.list.map(function (x, i) {
    var d = was.pos[x.team] ? was.pos[x.team] - (i + 1) : 0;
    var arrow = prev === last || !d ? '' : (d > 0 ? ' ⬆️' + d : ' 🔻' + (-d));
    return (i + 1) + '. ' + teamMark_(x.team) + ' — ' + Math.round(x.elo) + arrow;
  });
  var up = now.list.map(function (x, i) { return { t: x.team, d: (was.pos[x.team] || i + 1) - (i + 1) }; }).sort(function (a, b) { return b.d - a.d; });
  var from = Utilities.formatDate(prev[0], 'Europe/Moscow', 'dd.MM'), to = Utilities.formatDate(last[0], 'Europe/Moscow', 'dd.MM');
  return '📊 <b>СИЛА КОМАНД ' + escHtml_(VIDEO_LEAGUE) + '</b> · после матчей по ' + to + '\n\n' + lines.join('\n') +
    (prev !== last && up[0] && up[0].d > 0 ? '\n\nГлавный рывок недели — ' + escHtml_(up[0].t) + ' (+' + up[0].d + ' ' + ruPlural_(up[0].d, 'место', 'места', 'мест') + ')' +
      (up[up.length - 1].d < 0 ? ', сильнее всех просел ' + escHtml_(up[up.length - 1].t) + ' (' + up[up.length - 1].d + ')' : '') + '.' : '') +
    '\n\n<i>Мой рейтинг силы: учитывает результат и силу соперника. Стрелки — изменение места с ' + from + '.</i>';
}
function powerPost_(target) {
  var ss = SpreadsheetApp.getActive(), p = PropertiesService.getScriptProperties(), text = powerText_(ss);
  if (!text) throw new Error('нет истории рейтинга (лист «Elo_история»)');
  var chat = target === 'channel' ? bannerChannel_() : p.getProperty('TG_ADMIN_ID');
  if (!chat) throw new Error(target === 'channel' ? 'не указан канал' : 'не указан ваш Telegram — напишите боту /agent');
  var r = tg_('sendMessage', { chat_id: chat, text: target === 'channel' ? text : '👀 ПРОБНЫЙ ПОСТ (в канал не ушёл)\n\n' + text, parse_mode: 'HTML', disable_web_page_preview: true });
  if (!r || !r.ok) throw new Error('Telegram: ' + ((r && r.description) || 'нет ответа'));
  if (target === 'channel') dailyMark_('power');
  return true;
}
function powerAuto_() {
  if (PropertiesService.getScriptProperties().getProperty(dailyKey_('power'))) return;
  try { powerPost_('channel'); autoMark_('powerAuto_', true, '«Сила команд» опубликована'); }
  catch (e) { autoMark_('powerAuto_', false, e.message); autoNotifyAdmin_('⚠ «Сила команд» не ушла: ' + e.message); }
}
function powerPreviewNow_() { try { powerPost_('admin'); uiAlert_('Пробный пост «Сила команд» — у вас в Telegram.'); } catch (e) { uiAlert_('Не получилось: ' + e.message); } }
function powerPostNow_() {
  if (dailyAlready_('power', '«Сила команд»')) return;
  try { powerPost_('channel'); uiAlert_('«Сила команд» опубликована в канале.'); } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}

/* ==========================================================================
 * 🏒 НХЛ — источники данных и первичная настройка таблицы
 *
 *  Этот блок заменяет источники КХЛ на НХЛ, всё остальное (модель, прогнозы,
 *  точность, рынок, агент, досье, составы, автоматика) — тот же код, что в КХЛ.
 *   • расписание, счёт, составы — официальный API НХЛ (api-web.nhle.com), бесплатно, без ключей;
 *   • статистика команд (броски, большинство) — api.nhle.com/stats;
 *   • линии — Pinnacle, лига NHL;
 *   • новости — страницы клубов НХЛ на sports.ru и ваши Telegram-каналы.
 *  Даты в таблице — по Москве (как в КХЛ и на sports.ru): матч в 19:00 по Нью-Йорку = 02:00 МСК следующего дня.
 * ==========================================================================*/

var NHL_API = 'https://api-web.nhle.com/v1/';
var NHL_STATS_API = 'https://api.nhle.com/stats/rest/en/';
var NHL_SEASON = '20262027';
var NHL_PREV_SEASON = '20252026';
var NHL_PREV_FROM = '2025-10-01', NHL_PREV_TO = '2026-04-25';          // регулярка прошлого сезона
var NHL_SEASON_FROM = '2026-09-28', NHL_SEASON_TO = '2027-04-25';      // окно поиска матчей текущего сезона
var NHL_TEAM_ROWS = 32;
var FORMULA_RESULTS_ROWS = 1600;              // границы «результатов матчей» в формулах Data/Форма_расчет

/* 32 клуба: аббревиатура API, русское название (как на sports.ru), полное английское, конференция, дивизион,
 * адрес клуба на sports.ru, корни слов для поиска в новостях, город для поиска,
 * стартовый рейтинг 1–100 (из вашей таблицы «НХЛ КАПЕР ДЖАРВИС» от 15.09: 50% предсезонный рейтинг Pucky.com + 50% очки 2025/26). */
var NHL_TEAMS = [
  ['ANA', 'Анахайм', 'Anaheim Ducks', 'Запад', 'Тихоокеанский', 'anaheim-ducks', 'анахайм|дакс', 'Анахайм', 54],
  ['BOS', 'Бостон', 'Boston Bruins', 'Восток', 'Атлантический', 'boston-bruins', 'бостон|брюинз', 'Бостон', 74],
  ['BUF', 'Баффало', 'Buffalo Sabres', 'Восток', 'Атлантический', 'buffalo-sabres', 'баффало|сейбрз', 'Баффало', 76],
  ['CGY', 'Калгари', 'Calgary Flames', 'Запад', 'Тихоокеанский', 'calgary-flames', 'калгари|флэймз', 'Калгари', 18],
  ['CAR', 'Каролина', 'Carolina Hurricanes', 'Восток', 'Метрополитен', 'carolina-hurricanes', 'каролин|харрикейнз', 'Роли', 94],
  ['CHI', 'Чикаго', 'Chicago Blackhawks', 'Запад', 'Центральный', 'chicago-blackhawks', 'чикаго|блэкхокс', 'Чикаго', 16],
  ['COL', 'Колорадо', 'Colorado Avalanche', 'Запад', 'Центральный', 'colorado-avalanche', 'колорадо|эвеланш', 'Денвер', 97],
  ['CBJ', 'Коламбус', 'Columbus Blue Jackets', 'Восток', 'Метрополитен', 'columbus-blue-jackets', 'коламбус|блю джекетс', 'Коламбус', 46],
  ['DAL', 'Даллас', 'Dallas Stars', 'Запад', 'Центральный', 'dallas-stars', 'даллас|старз', 'Даллас', 87],
  ['DET', 'Детройт', 'Detroit Red Wings', 'Восток', 'Атлантический', 'detroit-red-wings', 'детройт|ред уингз', 'Детройт', 47],
  ['EDM', 'Эдмонтон', 'Edmonton Oilers', 'Запад', 'Тихоокеанский', 'edmonton-oilers', 'эдмонтон|ойлерз', 'Эдмонтон', 70],
  ['FLA', 'Флорида', 'Florida Panthers', 'Восток', 'Атлантический', 'florida-panthers', 'флорид|пантерз', 'Санрайз', 69],
  ['LAK', 'Лос-Анджелес', 'Los Angeles Kings', 'Запад', 'Тихоокеанский', 'los-angeles-kings', 'лос-анджелес|кингз', 'Лос-Анджелес', 43],
  ['MIN', 'Миннесота', 'Minnesota Wild', 'Запад', 'Центральный', 'minnesota-wild', 'миннесот|уайлд', 'Сент-Пол', 74],
  ['MTL', 'Монреаль', 'Montreal Canadiens', 'Восток', 'Атлантический', 'montreal-canadiens', 'монреал|канадиенс', 'Монреаль', 72],
  ['NSH', 'Нэшвилл', 'Nashville Predators', 'Запад', 'Центральный', 'nashville-predators', 'нэшвилл|предаторз', 'Нэшвилл', 35],
  ['NJD', 'Нью-Джерси', 'New Jersey Devils', 'Восток', 'Метрополитен', 'new-jersey-devils', 'нью-джерси|дэвилз', 'Ньюарк', 62],
  ['NYI', 'Айлендерс', 'New York Islanders', 'Восток', 'Метрополитен', 'new-york-islanders', 'айлендерс', 'Нью-Йорк', 42],
  ['NYR', 'Рейнджерс', 'New York Rangers', 'Восток', 'Метрополитен', 'new-york-rangers', 'рейнджерс', 'Нью-Йорк', 23],
  ['OTT', 'Оттава', 'Ottawa Senators', 'Восток', 'Атлантический', 'ottawa-senators', 'оттав|сенаторз', 'Оттава', 64],
  ['PHI', 'Филадельфия', 'Philadelphia Flyers', 'Восток', 'Метрополитен', 'philadelphia-flyers', 'филадельфи|флайерз', 'Филадельфия', 60],
  ['PIT', 'Питтсбург', 'Pittsburgh Penguins', 'Восток', 'Метрополитен', 'pittsburgh-penguins', 'питтсбург|пингвинз', 'Питтсбург', 55],
  ['SJS', 'Сан-Хосе', 'San Jose Sharks', 'Запад', 'Тихоокеанский', 'san-jose-sharks', 'сан-хосе|шаркс', 'Сан-Хосе', 52],
  ['SEA', 'Сиэтл', 'Seattle Kraken', 'Запад', 'Тихоокеанский', 'seattle-kraken', 'сиэтл|кракен', 'Сиэтл', 23],
  ['STL', 'Сент-Луис', 'St. Louis Blues', 'Запад', 'Центральный', 'st-louis-blues', 'сент-луис|блюз', 'Сент-Луис', 36],
  ['TBL', 'Тампа-Бэй', 'Tampa Bay Lightning', 'Восток', 'Атлантический', 'tampa-bay-lightning', 'тамп|лайтнинг', 'Тампа', 71],
  ['TOR', 'Торонто', 'Toronto Maple Leafs', 'Восток', 'Атлантический', 'toronto-maple-leafs', 'торонто|мейпл лифс|мэйпл лифс', 'Торонто', 25],
  ['UTA', 'Юта', 'Utah Mammoth', 'Запад', 'Центральный', 'utah-mammoth', 'юта|юты|юте|мамонт|маммот', 'Солт-Лейк-Сити', 49],
  ['VAN', 'Ванкувер', 'Vancouver Canucks', 'Запад', 'Тихоокеанский', 'vancouver-canucks', 'ванкувер|кэнакс', 'Ванкувер', 30],
  ['VGK', 'Вегас', 'Vegas Golden Knights', 'Запад', 'Тихоокеанский', 'vegas-golden-knights', 'вегас|голден найтс', 'Лас-Вегас', 70],
  ['WSH', 'Вашингтон', 'Washington Capitals', 'Восток', 'Метрополитен', 'washington-capitals', 'вашингтон|кэпиталз|кэпиталс', 'Вашингтон', 54],
  ['WPG', 'Виннипег', 'Winnipeg Jets', 'Запад', 'Центральный', 'winnipeg-jets', 'виннипег|джетс', 'Виннипег', 30]
];
/* ---------------- настройки, которые в КХЛ были свои ---------------- */
var MARKET_LEAGUE_ID = 1456;                  // «NHL» у Pinnacle
var MARKET_LEAGUE_RE = /^(nhl|national hockey league)$/i;   // ровно «NHL» (не предсезонка и не спецставки)
var AGENT_TAVILY_MONTHLY_CAP = 300;           // КХЛ — 650, вместе 950 из бесплатных 1000 в месяц
var AGENT_HOUR = 22;                          // 22:00 по Красноярску = 18:00 МСК: после утренних раскаток, до ночных матчей
var AGENT_DOMAINS = ['sports.ru', 'championat.com', 'sport-express.ru', 'allhockey.ru', 'matchtv.ru', 'sovsport.ru', 'rsport.ria.ru', 'sportbox.ru', 'hockey.ru', 'metaratings.ru'];
var AGENT_TEAM_STEMS = {}, AGENT_TEAM_CITY = {}, SPORTS_CLUB_SLUGS = {};
NHL_TEAMS.forEach(function (t) { AGENT_TEAM_STEMS[t[1]] = t[6]; AGENT_TEAM_CITY[t[1]] = t[7]; SPORTS_CLUB_SLUGS[t[1]] = t[5]; });
var SPORTS_TOPLEVEL_FALLBACK = true;       // у «Юты» страница sports.ru/utah-mammoth/, без /hockey/club/
var EXPERT_DEFAULT = [['Righthanded78', 'Михаил Зислис («Спорт-Экспресс», НХЛ)']];

// предыдущие аббревиатуры и названия (на всякий случай — API и линия иногда отдают старые)
var NHL_ABBR_ALIAS = { 'ARI': 'UTA', 'UTAH': 'UTA', 'PHX': 'UTA', 'LA': 'LAK', 'SJ': 'SJS', 'TB': 'TBL', 'NJ': 'NJD', 'MON': 'MTL', 'WAS': 'WSH', 'VEG': 'VGK', 'CLB': 'CBJ' };

function nhlTeamByAbbr_(abbr) {
  abbr = String(abbr || '').toUpperCase().trim(); abbr = NHL_ABBR_ALIAS[abbr] || abbr;
  for (var i = 0; i < NHL_TEAMS.length; i++) if (NHL_TEAMS[i][0] === abbr) return NHL_TEAMS[i];
  return null;
}
function nhlRu_(abbr) { var t = nhlTeamByAbbr_(abbr); return t ? t[1] : null; }

/** Любое английское написание («Toronto Maple Leafs», «Maple Leafs», «Toronto») → русское название. */
function nhlRuFromEnglish_(name) {
  var n = ' ' + String(name || '').toLowerCase().replace(/[^a-z .]/g, ' ').replace(/\s+/g, ' ') + ' ';
  var rules = [[/blue jackets|columbus/, 'CBJ'], [/golden knights|vegas/, 'VGK'], [/maple leafs|toronto/, 'TOR'], [/red wings|detroit/, 'DET'],
    [/ islanders/, 'NYI'], [/ rangers/, 'NYR'], [/lightning|tampa/, 'TBL'], [/ blues|st\.? louis|saint louis/, 'STL'], [/mammoth|utah|arizona|coyotes/, 'UTA'],
    [/ ducks|anaheim/, 'ANA'], [/bruins|boston/, 'BOS'], [/sabres|buffalo/, 'BUF'], [/flames|calgary/, 'CGY'], [/hurricanes|carolina/, 'CAR'],
    [/blackhawks|chicago/, 'CHI'], [/avalanche|colorado/, 'COL'], [/ stars|dallas/, 'DAL'], [/oilers|edmonton/, 'EDM'], [/panthers|florida/, 'FLA'],
    [/ kings|los angeles/, 'LAK'], [/ wild|minnesota/, 'MIN'], [/canadiens|montreal|montréal/, 'MTL'], [/predators|nashville/, 'NSH'],
    [/devils|new jersey/, 'NJD'], [/senators|ottawa/, 'OTT'], [/flyers|philadelphia/, 'PHI'], [/penguins|pittsburgh/, 'PIT'], [/sharks|san jose/, 'SJS'],
    [/kraken|seattle/, 'SEA'], [/canucks|vancouver/, 'VAN'], [/capitals|washington/, 'WSH'], [/ jets|winnipeg/, 'WPG']];
  for (var i = 0; i < rules.length; i++) if (rules[i][0].test(n)) return nhlRu_(rules[i][1]);
  return null;
}

/** Команда из объекта API (homeTeam/awayTeam): по аббревиатуре, иначе по названию. */
function nhlTeamOf_(t) {
  if (!t) return null;
  var ru = nhlRu_(t.abbrev || t.triCode || t.teamAbbrev && (t.teamAbbrev.default || t.teamAbbrev));
  if (ru) return ru;
  var nm = [t.placeName, t.commonName, t.name, t.teamName].map(function (x) { return x && (x.default || x); }).filter(Boolean).join(' ');
  return nhlRuFromEnglish_(nm);
}

/** GET к API НХЛ → JSON или null. Ответы кэшируются на 10 минут (одна и та же неделя в одном запуске не качается дважды). */
function nhlGet_(path, base) {
  var url = (base || NHL_API) + path, cache = null, key = 'nhl:' + Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, url));
  try { cache = CacheService.getScriptCache(); var hit = cache.get(key); if (hit) return JSON.parse(hit); } catch (e) { cache = null; }
  for (var attempt = 0; attempt < 2; attempt++) {
    try {
      var r = UrlFetchApp.fetch(url, { muteHttpExceptions: true, headers: { 'Accept': 'application/json', 'User-Agent': SPORTS_UA['User-Agent'] } });
      var code = r.getResponseCode();
      if (code === 200) {
        var txt = r.getContentText();
        try { if (cache && txt.length < 90000) cache.put(key, txt, 600); } catch (e) { /* большой ответ — без кэша */ }
        return JSON.parse(txt);
      }
      if (code === 404) return null;
    } catch (e) { /* повтор */ }
    Utilities.sleep(800);
  }
  return null;
}

/** Все матчи из объекта расписания/счёта (разные ответы API кладут их в разные места). */
function nhlGamesOf_(data) {
  if (!data) return [];
  if (Array.isArray(data.games)) return data.games;
  var out = [];
  (data.gameWeek || []).forEach(function (d) { (d.games || []).forEach(function (g) { if (!g.gameDate) g.gameDate = d.date; out.push(g); }); });
  return out;
}

var NHL_FINAL = { FINAL: true, OFF: true };

/** Матч API → {id, iso, date('dd.MM.yyyy' по МСК), time, home, away, hg, ag, ot, final, start} или null. */
function nhlGameInfo_(g) {
  if (!g || Number(g.gameType) !== 2) return null;                     // только регулярный чемпионат
  var home = nhlTeamOf_(g.homeTeam), away = nhlTeamOf_(g.awayTeam);
  if (!home || !away) return null;
  var start = g.startTimeUTC ? new Date(g.startTimeUTC) : null;
  if (!start || isNaN(start.getTime())) return null;
  var st = String(g.gameState || '').toUpperCase();
  var hg = g.homeTeam && g.homeTeam.score, ag = g.awayTeam && g.awayTeam.score;
  var last = String((g.gameOutcome && g.gameOutcome.lastPeriodType) || (g.periodDescriptor && g.periodDescriptor.periodType) || '').toUpperCase();
  return { id: String(g.id), iso: Utilities.formatDate(start, 'Europe/Moscow', 'yyyy-MM-dd'), date: Utilities.formatDate(start, 'Europe/Moscow', 'dd.MM.yyyy'),
    time: Utilities.formatDate(start, 'Europe/Moscow', 'HH:mm'), start: start, home: home, away: away,
    hg: typeof hg === 'number' ? hg : null, ag: typeof ag === 'number' ? ag : null,
    ot: last === 'OT' || last === 'SO', final: !!NHL_FINAL[st] && typeof hg === 'number' && typeof ag === 'number' };
}

/** Матчи за период (по неделям расписания). Если у сыгранного матча в расписании нет счёта — добираем по дню. */
function nhlGamesBetween_(fromIso, toIso, maxMs) {
  var t0 = Date.now(), out = {}, d = fromIso, guard = 0;
  while (d <= toIso && guard++ < 60 && (!maxMs || Date.now() - t0 < maxMs)) {
    var data = nhlGet_('schedule/' + d), games = nhlGamesOf_(data);
    var needScore = {};
    games.forEach(function (g) {
      var x = nhlGameInfo_(g); if (!x) return;
      if (NHL_FINAL[String(g.gameState || '').toUpperCase()] && !x.final && g.gameDate) needScore[g.gameDate] = true;
      out[x.id] = x;
    });
    Object.keys(needScore).forEach(function (day) {
      nhlGamesOf_(nhlGet_('score/' + day)).forEach(function (g) { var x = nhlGameInfo_(g); if (x) out[x.id] = x; });
    });
    var next = data && data.nextStartDate;
    if (next && next > d) d = next;
    else d = addDaysKey_(d, 7);
  }
  return Object.keys(out).map(function (k) { return out[k]; }).sort(function (a, b) { return a.start - b.start; });
}

/* ---------------- замены источников КХЛ ---------------- */

/** Календарные страницы sports.ru для НХЛ не нужны — счёт берём из API. */
function fetchAllCalendarTexts_() { return []; }

/** Счёт сыгранных матчей для «Обновить результаты»: те же поля, что давал разбор sports.ru. */
function mpFetchPlayed_(planned, nameMap, now) {
  now = now || new Date();
  var today = Utilities.formatDate(now, 'Europe/Moscow', 'yyyy-MM-dd'), from = addDaysKey_(today, -MP_LOOKBACK_DAYS);
  var want = {};
  planned.forEach(function (p) {
    var k = p.date instanceof Date ? sheetDayKey_(p.date) : '';
    if (k && k >= from && k <= today) want[k + '|' + p.home + '|' + p.away] = true;
  });
  var keys = Object.keys(want);
  if (!keys.length) return { matches: [], checked: 0, calendar: 0 };
  var days = {};
  keys.forEach(function (k) { var d = k.split('|')[0]; days[addDaysKey_(d, -1)] = true; days[d] = true; });   // МСК-день = вечер по Нью-Йорку накануне или сам день
  var out = [], seen = {};
  Object.keys(days).sort().forEach(function (d) {
    nhlGamesOf_(nhlGet_('score/' + d)).forEach(function (g) {
      var x = nhlGameInfo_(g); if (!x || !x.final || seen[x.id]) return;
      seen[x.id] = true;
      if (want[x.iso + '|' + x.home + '|' + x.away]) out.push({ date: x.date, home: x.home, away: x.away, homeGoals: x.hg, awayGoals: x.ag, ot: x.ot });
    });
  });
  return { matches: out, checked: keys.length, calendar: Object.keys(days).length };
}

/** Будущие матчи сезона → «результаты матчей» (та же логика добавления, что в КХЛ). */
function syncScheduleFromWeb_() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(SHEET_RESULTS);
  if (!sh) throw new Error('не найден лист «' + SHEET_RESULTS + '»');
  var today = todayKey_(), from = today > NHL_SEASON_FROM ? addDaysKey_(today, -3) : NHL_SEASON_FROM, to = addDaysKey_(from, 42);
  if (to > NHL_SEASON_TO) to = NHL_SEASON_TO;
  var games = from > NHL_SEASON_TO ? [] : nhlGamesBetween_(from, to, 150000);   // весь сезон загружен при настройке; здесь — переносы на 6 недель вперёд
  if (!games.length && from > NHL_SEASON_TO) return { added: 0, notOnWeb: [], unknown: [], last: null };
  if (!games.length) throw new Error('API НХЛ не вернул матчей регулярного чемпионата (сезон ещё не опубликован или API недоступен)');
  var web = {}, coveredTo = '';
  games.forEach(function (x) { web[x.iso + '|' + x.home + '|' + x.away] = { key: x.iso, home: x.home, away: x.away }; if (x.iso > coveredTo) coveredTo = x.iso; });
  var v = sh.getDataRange().getValues(), hdr = v[0];
  var cD = hdr.indexOf('Дата'), cH = hdr.indexOf('Хозяева'), cA = hdr.indexOf('Гости');
  var existing = {}, lastTeamRow = 1, notOnWeb = [];
  for (var r = 1; r < v.length; r++) {
    var home = String(v[r][cH] || '').trim(), away = String(v[r][cA] || '').trim();
    if (!home || !away) continue;
    lastTeamRow = r + 1;
    if (!(v[r][cD] instanceof Date)) continue;
    var key2 = sheetDayKey_(v[r][cD]), full = key2 + '|' + home + '|' + away;
    existing[full] = true;
    if (key2 >= today && key2 <= coveredTo && !web[full]) notOnWeb.push(key2.slice(8, 10) + '.' + key2.slice(5, 7) + ' ' + home + ' — ' + away);
  }
  var toAdd = [];
  for (var wk in web) if (!existing[wk] && web[wk].key >= today) toAdd.push(web[wk]);
  toAdd.sort(function (x, y) { return x.key < y.key ? -1 : x.key > y.key ? 1 : (x.home < y.home ? -1 : 1); });
  if (toAdd.length) nhlAppendResultRows_(sh, lastTeamRow, toAdd);
  return { added: toAdd.length, notOnWeb: notOnWeb, unknown: [], last: toAdd.length ? toAdd[toAdd.length - 1].key : null };
}

/** Дописать матчи в «результаты матчей» после lastTeamRow; формулы статуса/победителя/очков — как у строки-образца. */
function nhlAppendResultRows_(sh, lastTeamRow, list) {
  var tpl = -1;
  for (var t = lastTeamRow; t >= 2; t--) { if (sh.getRange(t, 2).getFormula() !== '') { tpl = t; break; } }
  var start = lastTeamRow + 1;
  if (sh.getMaxRows() < start + list.length) sh.insertRowsAfter(sh.getMaxRows(), start + list.length - sh.getMaxRows() + 10);
  sh.getRange(start, 1, list.length, 1).setValues(list.map(function (m) { return [keyToSheetDate_(m.key)]; })).setNumberFormat('dd.mm.yyyy');
  sh.getRange(start, 3, list.length, 2).setValues(list.map(function (m) { return [m.home, m.away]; }));
  if (tpl !== -1) {
    var b = sh.getRange(tpl, 2).getFormulaR1C1(), gj = sh.getRange(tpl, 7, 1, 4).getFormulasR1C1()[0];
    sh.getRange(start, 2, list.length, 1).setFormulasR1C1(list.map(function () { return [b]; }));
    sh.getRange(start, 7, list.length, 4).setFormulasR1C1(list.map(function () { return gj.map(function (f) { return f || '=FALSE()'; }); }));
  } else nhlWriteResultFormulas_(sh, start, list.length);
}

/** Формулы строки «результатов матчей» (как в КХЛ) — если строки-образца нет. */
function nhlWriteResultFormulas_(sh, start, n) {
  var f = function (tpl) { var out = []; for (var i = 0; i < n; i++) out.push([tpl.replace(/\{R\}/g, start + i)]); return out; };
  sh.getRange(start, 2, n, 1).setFormulas(f('=IF(AND(E{R}<>"";F{R}<>"");"Сыгран";"Запланирован")'));
  sh.getRange(start, 7, n, 1).setFormulas(f('=FALSE()'));
  sh.getRange(start, 8, n, 1).setFormulas(f('=IF(OR(C{R}="";D{R}="");"";IF(B{R}="Запланирован";"";IF(E{R}>F{R};C{R}&IF(G{R};" (в ОТ/буллитах)";"");IF(F{R}>E{R};D{R}&IF(G{R};" (в ОТ/буллитах)";"");"Ничья"))))'));
  sh.getRange(start, 9, n, 1).setFormulas(f('=IF(OR(C{R}="";D{R}="");"";IF(B{R}="Запланирован";"";IF(E{R}>F{R};2;IF(F{R}>E{R};IF(G{R};1;0);1))))'));
  sh.getRange(start, 10, n, 1).setFormulas(f('=IF(OR(C{R}="";D{R}="");"";IF(B{R}="Запланирован";"";IF(F{R}>E{R};2;IF(E{R}>F{R};IF(G{R};1;0);1))))'));
}

/** Исправления расписания КХЛ к НХЛ не относятся. */
function repairShiftedDates_() { return 0; }
function applyKnownCorrections_() { return []; }

/** «Броски на гол» по всем командам — из статистики НХЛ (раньше — топ-5 со страницы sports.ru). */
function updateShotsStats_() {
  var ss = SpreadsheetApp.getActive();
  var data = nhlGet_('team/summary?isAggregate=false&isGame=false&start=0&limit=50&cayenneExp=' + encodeURIComponent('gameTypeId=2 and seasonId=' + NHL_SEASON), NHL_STATS_API);
  var rows = [], sumS = 0, sumG = 0;
  ((data && data.data) || []).forEach(function (t) {
    var ru = nhlRuFromEnglish_(t.teamFullName || t.teamName || ''); if (!ru) return;
    var gp = Number(t.gamesPlayed) || 0, spg = Number(t.shotsForPerGame) || 0, gf = Number(t.goalsFor) || 0;
    if (!gp || !gf) return;
    var shots = spg * gp; sumS += shots; sumG += gf;
    rows.push([ru, Math.round(shots / gf * 100) / 100]);
  });
  var sh = ss.getSheetByName('Броски_кэш') || ss.insertSheet('Броски_кэш');
  sh.clearContents();
  sh.getRange(1, 1, 1, 2).setValues([['Команда', 'Б/Г (бросков на гол)']]);
  if (rows.length) sh.getRange(2, 1, rows.length, 2).setValues(rows);
  if (sumG) sh.getRange('E1').setValue(Math.round(sumS / sumG * 100) / 100);
  uiAlert_(rows.length ? 'Готово: «бросков на гол» для ' + rows.length + ' из 32 команд (статистика НХЛ).' : 'Статистика НХЛ пока пуста — сезон ещё не начался. Кнопку можно нажать позже.');
  return rows.length;
}

/** Линия Pinnacle: английское название → русское. */
function pinnacleTeamRu_(name) { return nhlRuFromEnglish_(name); }

/** Архив линий прошлого сезона — только для КХЛ (для НХЛ «Лучший прогноз» считается по живой линии). */
function loadHistOddsIfNeeded_() { return { skipped: true, rows: 0 }; }
function loadHistOdds_(silent) { if (!silent) uiAlert_('Для НХЛ архив линий не загружается: «Лучший прогноз» считается по текущей линии Pinnacle.'); return { skipped: true, rows: 0 }; }

/** LIVE-пост и проверка заявок за час до матча — пока только в таблице КХЛ. */
function liveUpdate_(now) { return { matches: 0, posted: false, edited: false, text: '' }; }
function lineupWatch_(now, force) { return { checked: 0, sent: 0, lines: [] }; }
function lineupWatchNow_() { uiAlert_('В НХЛ заявка публикуется перед самым матчем; отметки 🟢🟡🔴 в сводке строятся по составам прошлых матчей (протоколы НХЛ).'); }

/* ---------------- составы из протоколов НХЛ ---------------- */

function nhlToiMin_(s) { var m = String(s || '').match(/^(\d+):(\d\d)$/); return m ? Math.round((+m[1] + m[2] / 60) * 100) / 100 : 0; }
function nhlName_(p) { var n = p && p.name; n = n && (n.default || n); if (!n && p && p.firstName) n = (p.firstName.default || p.firstName) + ' ' + (p.lastName && (p.lastName.default || p.lastName) || ''); return String(n || '').trim(); }

/** Протокол матча → строки для листа «Составы_матчей». */
function nhlBoxscoreRows_(box, q) {
  var st = box && (box.playerByGameStats || (box.boxscore && box.boxscore.playerByGameStats));
  if (!st) return [];
  var rows = [], date = signalDate_(q.iso), url = 'https://www.nhl.com/gamecenter/' + q.id;
  [['homeTeam', q.home], ['awayTeam', q.away]].forEach(function (s) {
    var t = st[s[0]] || {};
    [['forwards', 'F'], ['defense', 'D'], ['goalies', 'G']].forEach(function (grp) {
      (t[grp[0]] || []).forEach(function (p) {
        var name = nhlName_(p); if (!name) return;
        var sa = p.shotsAgainst, sv = p.saves;
        if ((sa === undefined || sv === undefined) && typeof p.saveShotsAgainst === 'string') { var m = p.saveShotsAgainst.split('/'); sv = Number(m[0]); sa = Number(m[1]); }
        rows.push([date, q.home, q.away, s[1], grp[1], String(p.sweaterNumber || ''), name, nhlToiMin_(p.toi),
          typeof p.goals === 'number' ? p.goals : (grp[1] === 'G' ? '' : 0), typeof p.assists === 'number' ? p.assists : (grp[1] === 'G' ? '' : 0),
          grp[1] === 'G' && isFinite(Number(sa)) ? Number(sa) : '', grp[1] === 'G' && isFinite(Number(sv)) ? Number(sv) : '', url]);
      });
    });
  });
  return rows;
}

/** Составы всех сыгранных матчей сезона, которых ещё нет на листе. {added, pending, failed} */
function lineupsCollect_(ss, maxMs) {
  ss = ss || SpreadsheetApp.getActive(); maxMs = maxMs || 240000;
  var t0 = Date.now(), sh = lineupSheet_(ss), done = {};
  if (sh.getLastRow() >= 2) sh.getRange(2, 1, sh.getLastRow() - 1, 3).getValues().forEach(function (r) { done[signalDay_(r[0]) + '|' + r[1] + '|' + r[2]] = true; });
  var played = [], rs = ss.getSheetByName(SHEET_RESULTS);
  if (rs && rs.getLastRow() >= 2) rs.getRange(2, 1, rs.getLastRow() - 1, 4).getValues().forEach(function (r) {
    if (!(r[0] instanceof Date) || String(r[1]).trim() !== 'Сыгран') return;
    var k = sheetDayKey_(r[0]) + '|' + String(r[2]).trim() + '|' + String(r[3]).trim();
    if (!done[k]) played.push(k);
  });
  if (!played.length) return { added: 0, pending: 0, failed: [] };
  played.sort().reverse();                                                  // сначала свежие
  var need = {}; played.forEach(function (k) { need[k] = true; });
  // id матчей: из счёта за нужные дни (МСК-день = вечер по Нью-Йорку накануне или сам день)
  var ids = {}, days = {};
  played.forEach(function (k) { var d = k.split('|')[0]; days[addDaysKey_(d, -1)] = true; days[d] = true; });
  Object.keys(days).sort().reverse().forEach(function (d) {
    if (Date.now() - t0 > maxMs * 0.4) return;
    nhlGamesOf_(nhlGet_('score/' + d)).forEach(function (g) { var x = nhlGameInfo_(g); if (x && need[x.iso + '|' + x.home + '|' + x.away]) ids[x.iso + '|' + x.home + '|' + x.away] = x; });
  });
  var queue = played.filter(function (k) { return ids[k]; }).map(function (k) { return ids[k]; });
  var added = 0, failed = [], i = 0;
  while (i < queue.length && Date.now() - t0 < maxMs) {
    var batch = queue.slice(i, i + 8); i += batch.length;
    var resps = [];
    try { resps = UrlFetchApp.fetchAll(batch.map(function (q) { return { url: NHL_API + 'gamecenter/' + q.id + '/boxscore', muteHttpExceptions: true }; })); } catch (e) { resps = []; }
    var rows = [];
    batch.forEach(function (q, k) {
      var box = null;
      try { if (resps[k] && resps[k].getResponseCode() === 200) box = JSON.parse(resps[k].getContentText()); } catch (e) { box = null; }
      var rr = nhlBoxscoreRows_(box, q);
      if (!rr.length) { failed.push(q.home + ' — ' + q.away + ' ' + q.iso); return; }
      rows = rows.concat(rr); added++;
    });
    if (rows.length) sh.getRange(sh.getLastRow() + 1, 1, rows.length, LINEUP_HEADER.length).setValues(rows);
  }
  return { added: added, pending: played.length - added - failed.length, failed: failed };
}

/* ---------------- диагностика источников (бесплатно) ---------------- */
var NHL_DIAG_SHEET = 'Диагностика_НХЛ';
function lineupDiag_() { return nhlDiag_(); }
function nhlDiag_() {
  var ss = SpreadsheetApp.getActive(), rows = [], t0 = Date.now();
  var add = function (what, ok, res) { rows.push([what, ok ? '✓' : '✗', String(res).slice(0, 45000)]); };
  var raw = function (path, base) {
    try { var r = UrlFetchApp.fetch((base || NHL_API) + path, { muteHttpExceptions: true }); return { code: r.getResponseCode(), text: r.getContentText() }; }
    catch (e) { return { code: 'ошибка: ' + e.message, text: '' }; }
  };
  var today = todayKey_();
  // 1. расписание: ближайшая неделя и начало регулярки
  var s = raw('schedule/' + (today < NHL_SEASON_FROM ? NHL_SEASON_FROM : today)), sd = null;
  try { sd = JSON.parse(s.text); } catch (e) { sd = null; }
  var games = nhlGamesOf_(sd), reg = games.map(nhlGameInfo_).filter(Boolean);
  add('Расписание (неделя)', reg.length > 0, 'ответ ' + s.code + '; матчей в ответе: ' + games.length + ', регулярки: ' + reg.length +
    (sd ? '; начало регулярки: ' + (sd.regularSeasonStartDate || '?') + ', конец: ' + (sd.regularSeasonEndDate || '?') : '') +
    '\n' + reg.slice(0, 5).map(function (x) { return x.date + ' ' + x.time + ' МСК ' + x.home + ' — ' + x.away; }).join('\n') + '\n\nНАЧАЛО ОТВЕТА:\n' + s.text.slice(0, 6000));
  // 2. счёт: вчерашние матчи (сейчас это предсезонка — проверяем формат)
  var y = raw('score/' + addDaysKey_(today, -1)), yd = null;
  try { yd = JSON.parse(y.text); } catch (e) { yd = null; }
  var yg = nhlGamesOf_(yd), fin = yg.filter(function (g) { return NHL_FINAL[String(g.gameState || '').toUpperCase()]; });
  add('Счёт за вчера', y.code === 200, 'ответ ' + y.code + '; матчей: ' + yg.length + ', завершено: ' + fin.length + '\n' +
    yg.slice(0, 4).map(function (g) { return (g.gameType === 2 ? 'регулярка ' : 'тип ' + g.gameType + ' ') + (nhlTeamOf_(g.homeTeam) || '?') + ' ' + (g.homeTeam && g.homeTeam.score) + ':' + (g.awayTeam && g.awayTeam.score) + ' ' + (nhlTeamOf_(g.awayTeam) || '?') + ' ' + g.gameState + ' ' + JSON.stringify(g.gameOutcome || {}); }).join('\n') +
    '\n\nНАЧАЛО ОТВЕТА:\n' + y.text.slice(0, 5000));
  // 3. протокол завершённого матча — составы
  var g0 = fin[0] || yg[0];
  if (g0) {
    var b = raw('gamecenter/' + g0.id + '/boxscore'), bd = null;
    try { bd = JSON.parse(b.text); } catch (e) { bd = null; }
    var rr = nhlBoxscoreRows_(bd, { id: g0.id, iso: today, home: nhlTeamOf_(g0.homeTeam) || 'H', away: nhlTeamOf_(g0.awayTeam) || 'A' });
    var gk = rr.filter(function (r) { return r[4] === 'G'; });
    add('Протокол матча (составы)', rr.length >= 30, 'ответ ' + b.code + '; игроков разобрано: ' + rr.length + ', вратари: ' + gk.map(function (r) { return r[3] + ' ' + r[6] + ' ' + r[7] + ' мин, ' + r[11] + '/' + r[10]; }).join('; ') +
      '\nпример полевого: ' + (rr[0] ? rr[0].slice(3, 10).join(' | ') : '—') + '\n\nНАЧАЛО ОТВЕТА:\n' + b.text.slice(0, 6000));
  } else add('Протокол матча (составы)', false, 'вчера матчей не было — проверю в следующий раз');
  // 4. статистика команд
  var st = raw('team/summary?isAggregate=false&isGame=false&start=0&limit=50&cayenneExp=' + encodeURIComponent('gameTypeId=2 and seasonId=' + NHL_PREV_SEASON), NHL_STATS_API), sdat = null;
  try { sdat = JSON.parse(st.text); } catch (e) { sdat = null; }
  var list = (sdat && sdat.data) || [], mapped = list.filter(function (t) { return nhlRuFromEnglish_(t.teamFullName); }).length;
  add('Статистика команд (прошлый сезон)', mapped >= 30, 'ответ ' + st.code + '; команд: ' + list.length + ', распознано: ' + mapped + '\n' + (list[0] ? JSON.stringify(list[0]).slice(0, 1500) : ''));
  // 5. линия Pinnacle
  try {
    var mu = marketFetch_('/leagues/' + marketLeagueId_(false) + '/matchups'), names = {};
    ((mu && mu.data) || []).forEach(function (m) { (m.participants || []).forEach(function (p) { names[p.name] = pinnacleTeamRu_(p.name) || '❓'; }); });
    var nn = Object.keys(names);
    add('Линия Pinnacle (NHL)', mu.code === 200, 'ответ ' + mu.code + '; матчей: ' + ((mu.data || []).length) + '; команды: ' + nn.slice(0, 40).map(function (k) { return k + ' → ' + names[k]; }).join(', '));
  } catch (e) { add('Линия Pinnacle (NHL)', false, e.message); }
  // 6. новости клуба на sports.ru
  try {
    var slugs = sportsClubSlugs_(true), news = sportsClubNews_('Вашингтон', slugs);
    add('Новости клуба на sports.ru (Вашингтон)', news.length > 0, 'новостей: ' + news.length + '\n' + news.slice(0, 5).map(sportsNewsLine_).join('\n') +
      '\nадреса клубов: ' + NHL_TEAMS.map(function (t) { return t[1] + '=' + slugs[t[1]]; }).join(', '));
  } catch (e) { add('Новости клуба на sports.ru', false, e.message); }
  // 7–12. дополнительные источники
  try { var sd2 = nhlStandings_(), k2 = Object.keys(sd2); add('Таблица НХЛ (форма, серии)', k2.length >= 30, 'команд: ' + k2.length + (k2[0] ? '; пример: ' + k2[0] + ' ' + JSON.stringify(sd2[k2[0]]) : '')); } catch (e) { add('Таблица НХЛ', false, e.message); }
  try { var ts = nhlTeamStats_(), kt = Object.keys(ts).filter(function (k) { return k !== 'season'; }); add('Спецбригады и броски (НХЛ)', kt.length >= 30 && !!ts[kt[0]].pp, 'сезон ' + ts.season + ', команд: ' + kt.length + (kt[0] ? '; пример: ' + kt[0] + ' ' + JSON.stringify(ts[kt[0]]) : '')); } catch (e) { add('Спецбригады (НХЛ)', false, e.message); }
  try { var gsx = nhlGoalieStats_(), kg = Object.keys(gsx).filter(function (k) { return k !== 'season'; }); add('Вратари (НХЛ)', kg.length >= 30, 'сезон ' + gsx.season + ', команд: ' + kg.length + (kg[0] ? '; пример: ' + kg[0] + ' ' + JSON.stringify(gsx[kg[0]].slice(0, 2)) : '')); } catch (e) { add('Вратари (НХЛ)', false, e.message); }
  try { var mp = moneyPuckData_(), km = Object.keys(mp.teams); add('MoneyPuck (xG, GSAx)', km.length >= 30, 'ответы: ' + mp.codes.join(', ') + '; сезон ' + (mp.season || '—') + ', команд: ' + km.length + ', вратарей у команд: ' + Object.keys(mp.goalies).length + (km[0] ? '; пример: ' + km[0] + ' ' + JSON.stringify(mp.teams[km[0]]) : '')); } catch (e) { add('MoneyPuck', false, e.message); }
  try {
    var inj = espnInjuries_(), ki = Object.keys(inj).filter(function (k) { return k !== 'code'; }), raw2 = raw('', ESPN_INJURIES_URL);
    add('Травмы (ESPN)', inj.code === 200 && ki.length > 0, 'ответ ' + inj.code + '; команд с травмами: ' + ki.length + ', игроков: ' + ki.reduce(function (a, k) { return a + inj[k].length; }, 0) +
      (ki[0] ? '; пример: ' + nhlInjuryLine_({ injuries: inj }, ki[0]) : '') + '\n\nНАЧАЛО ОТВЕТА:\n' + raw2.text.slice(0, 3000));
  } catch (e) { add('Травмы (ESPN)', false, e.message); }
  try {
    var etd = Utilities.formatDate(new Date(), 'America/New_York', 'yyyy-MM-dd'), df = dailyFaceoffGoalies_(etd);
    add('Стартовые вратари (Daily Faceoff)', df.length > 0, 'ответ ' + df.code + ', данные страницы ' + (df.found ? 'найдены' : 'НЕ найдены') + '; матчей с вратарями на ' + etd + ': ' + df.length +
      (df[0] ? '; пример: ' + df[0].home + ' ' + df[0].hg + ' (' + df[0].hs + ') — ' + df[0].away + ' ' + df[0].ag + ' (' + df[0].as + ')' : ' (до старта сезона матчей может не быть)') + '\n\nНАЧАЛО СТРАНИЦЫ:\n' + df.snippet);
  } catch (e) { add('Стартовые вратари (Daily Faceoff)', false, e.message); }
  var sh = ss.getSheetByName(NHL_DIAG_SHEET) || ss.insertSheet(NHL_DIAG_SHEET);
  sh.clear();
  sh.getRange(1, 1, 1, 3).setValues([['Что проверяли', 'Итог', 'Подробности']]).setFontWeight('bold');
  sh.getRange(2, 1, rows.length, 3).setValues(rows.map(function (r) { return r.map(function (v) { return typeof v === 'string' && /^[=+\-@]/.test(v) ? "'" + v : v; }); })).setWrap(true).setVerticalAlignment('top');
  try { sh.setColumnWidth(1, 240); sh.setColumnWidth(3, 900); } catch (e) {}
  uiAlert_('Проверка источников НХЛ (' + Math.round((Date.now() - t0) / 1000) + ' с), кредиты не тратились:\n\n' + rows.map(function (r) { return r[1] + ' ' + r[0] + ' — ' + String(r[2]).split('\n')[0]; }).join('\n') +
    '\n\nПодробно — лист «' + NHL_DIAG_SHEET + '». Напишите Claude «готово», если что-то с ✗.');
  return rows;
}

/* ---------------- прошлый сезон ---------------- */

/** «Результаты 2025-26» и «Таблица 2025-26» из API (нужны модели: личные встречи, домашний бонус, самопроверка). */
function nhlLoadPrevSeason_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var games = nhlGamesBetween_(NHL_PREV_FROM, NHL_PREV_TO, 200000).filter(function (x) { return x.final; });
  if (games.length < 500) throw new Error('прошлый сезон загрузился не полностью: ' + games.length + ' матчей (ожидалось ~1312) — запустите настройку ещё раз');
  var rows = games.map(function (x) {
    var hw = x.hg > x.ag;
    return [x.date, 'Сыгран', x.home, x.away, x.hg, x.ag, x.ot, (hw ? x.home : x.away) + (x.ot ? ' (в ОТ/буллитах)' : ''), hw ? 2 : (x.ot ? 1 : 0), hw ? (x.ot ? 1 : 0) : 2];
  });
  var sh = ss.getSheetByName('Результаты 2025-26') || ss.insertSheet('Результаты 2025-26');
  if (sh.getMaxRows() < rows.length + 20) sh.insertRowsAfter(sh.getMaxRows(), rows.length + 20 - sh.getMaxRows());
  if (sh.getLastRow() >= 2) sh.getRange(2, 1, sh.getLastRow() - 1, Math.max(10, sh.getLastColumn())).clearContent();
  sh.getRange(1, 1, 1, 10).setValues([['Дата', 'Статус', 'Хозяева', 'Гости', 'Г Хозяев', 'Г Гостей', 'ОТ/буллиты?', 'Победитель', 'Очки Х', 'Очки Г']]);
  sh.getRange(2, 1, rows.length, 1).setNumberFormat('@');
  sh.getRange(2, 1, rows.length, 10).setValues(rows);
  // итоговая таблица прошлого сезона
  var t = {};
  NHL_TEAMS.forEach(function (x) { t[x[1]] = { n: x[1], i: 0, o: 0, w: 0, wo: 0, lo: 0, l: 0, gf: 0, ga: 0 }; });
  games.forEach(function (x) {
    [[x.home, x.hg, x.ag], [x.away, x.ag, x.hg]].forEach(function (s) {
      var r = t[s[0]]; if (!r) return;
      r.i++; r.gf += s[1]; r.ga += s[2];
      if (s[1] > s[2]) { if (x.ot) r.wo++; else r.w++; r.o += 2; } else { if (x.ot) { r.lo++; r.o += 1; } else r.l++; }
    });
  });
  var list = Object.keys(t).map(function (k) { return t[k]; }).sort(function (a, b) { return b.o - a.o || (b.gf - b.ga) - (a.gf - a.ga); });
  var tb = ss.getSheetByName('Таблица 2025-26') || ss.insertSheet('Таблица 2025-26');
  tb.clearContents();
  tb.getRange(1, 1, 1, 11).setValues([['Место', 'Команда', 'И', 'О', 'В', 'ВО', 'ПО', 'П', 'ЗШ', 'ПШ', 'Разница']]);
  tb.getRange(2, 1, list.length, 11).setValues(list.map(function (r, i) { return [i + 1, r.n, r.i, r.o, r.w, r.wo, r.lo, r.l, r.gf, r.ga, r.gf - r.ga]; }));
  return { games: games.length };
}

/* ---------------- первичная настройка копии таблицы под НХЛ ---------------- */

var NHL_SETUP_STAGES = ['teams', 'sheets', 'prev', 'schedule', 'compute', 'finish'];
var NHL_KEEP_PROPS = ['NHL_CHANNEL', 'GEMINI_KEY', 'GEMINI_MODEL', 'TAVILY_KEY', 'ANTHROPIC_API_KEY', 'TG_BOT_TOKEN', 'TG_ADMIN_ID', 'TG_OWNER_ID', 'TG_BOT_USERNAME', 'TG_EMOJI_MAP', 'NHL_SETUP'];
// листы, где лежат данные КХЛ: очищаем всё, кроме строки заголовков (оформление остаётся)
var NHL_CLEAR_SHEETS = ['Elo', 'Elo_история', 'Таблица_история', 'Точность', 'Самопроверка', 'Банкролл', 'Выездные_серии', 'Броски_кэш',
  'Составы_матчей', 'Ключевые_игроки', 'Досье_команд', 'Досье_история', 'Агент_сводки', 'Агент_выводы', 'Агент_проверка', 'Коэффициенты',
  'Коэффициенты_журнал', 'Модель vs рынок', 'Прогнозы — кратко', 'Архив_линий', 'Live_журнал', 'Игра_игроки', 'Игра_прогнозы', 'Обыграй Джарвиса',
  'Каналы_экспертов', 'Диагностика_результатов', 'Диагностика_новостей', 'Диагностика_составов', 'Заявки_наблюдение', 'Статистика_debug',
  'Контекст и новости', 'Автоматика', 'Броски_debug'];

/** Меню: запустить (или продолжить) настройку. Работает частями — если Google остановит по времени, продолжит сам через минуту. */
function nhlSetupNow_() {
  var ui = null; try { ui = SpreadsheetApp.getUi(); } catch (e) { ui = null; }
  var st = nhlSetupState_();
  var miss = nhlMissingSheets_(SpreadsheetApp.getActive());
  if (miss.length) { uiAlert_(nhlWrongTableText_(miss)); return; }
  if (ui && st.stage === 'done') {
    var again = ui.alert('Таблица уже настроена под НХЛ', 'Запустить настройку заново? Прогнозы, журналы и рейтинги будут пересобраны с нуля.', ui.ButtonSet.YES_NO);
    if (again !== ui.Button.YES) return;
    PropertiesService.getScriptProperties().deleteProperty('NHL_SETUP'); st = {};
  }
  if (ui && !st.stage) {
    var r = ui.alert('Настроить эту таблицу под НХЛ?', 'Данные КХЛ в этой копии будут удалены: команды, результаты, прогнозы, рейтинги, журналы. ' +
      'Загрузятся 32 клуба НХЛ, прошлый сезон 2025/26 и календарь 2026/27. Займёт 5–15 минут (частями). ' +
      'Оригинальную таблицу КХЛ это не трогает. Продолжить?', ui.ButtonSet.YES_NO);
    if (r !== ui.Button.YES) return;
  }
  var res = nhlSetupRun_();
  if (res.wrong) { uiAlert_(res.log.join('\n')); return; }
  var bad = res.log.filter(function (l) { return l.indexOf('⚠') === 0; }).length;
  if (ui && res.done && bad) { uiAlert_('⚠ Настройка закончилась с ошибками (' + bad + '):\n\n' + res.log.join('\n') + '\n\nПришлите этот текст Claude.'); return; }
  if (ui) uiAlert_(res.done ? '✅ Таблица НХЛ готова.\n\n' + res.log.join('\n') + '\n\nДальше: меню «НХЛ-парсер» → Настройки → «Ключи и Telegram для НХЛ», затем «Включить всю автоматику».'
    : 'Настройка идёт: ' + res.log.join('\n') + '\n\nОсталось: ' + res.left.join(', ') + '. Продолжу сам через минуту — итог придёт в Telegram (если указан ID) и появится на листе «Автоматика».');
}

function nhlSetupState_() { try { return JSON.parse(PropertiesService.getScriptProperties().getProperty('NHL_SETUP') || '{}'); } catch (e) { return {}; } }

function nhlSetupContinue_() {
  var res = nhlSetupRun_();
  if (res.done) autoNotifyAdmin_('🏒 Таблица НХЛ настроена.\n' + res.log.join('\n'));
}

/** Выполнить этапы по порядку, пока хватает времени. */
function nhlSetupSafety_(ms) {
  try {
    ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'nhlSetupContinue_') ScriptApp.deleteTrigger(t); });
    if (ms) ScriptApp.newTrigger('nhlSetupContinue_').timeBased().after(ms).create();
  } catch (e) { /* нет прав на триггеры — продолжит кнопкой */ }
}

function nhlSetupRun_() {
  var p = PropertiesService.getScriptProperties(), st = nhlSetupState_(), t0 = Date.now();
  if (!st.stage) st = { stage: NHL_SETUP_STAGES[0], log: [] };
  var miss0 = nhlMissingSheets_(SpreadsheetApp.getActive());
  if (miss0.length) { nhlSetupSafety_(0); return { done: false, log: ['⚠ ' + nhlWrongTableText_(miss0)], left: [], wrong: true }; }
  if (st.stage === 'done') return { done: true, log: st.log || [], left: [] };
  st.log = st.log || [];
  var ss = SpreadsheetApp.getActive();
  nhlSetupSafety_(8 * 60 * 1000);          // страховка: если Google оборвёт запуск по 6-минутному лимиту, продолжим через 8 минут
  // новый этап начинаем, только если прошло меньше 100 с: самый долгий этап (прошлый сезон) укладывается в 4 минуты
  while (st.stage && st.stage !== 'done' && Date.now() - t0 < 100000) {
    var name = st.stage, msg = '';
    QUIET_ = true;
    try { msg = nhlSetupStage_(ss, name) || 'готово'; st.log.push((/⚠/.test(msg) ? '⚠ ' : '✓ ') + nhlStageTitle_(name) + ': ' + msg); }
    catch (e) { st.log.push('⚠ ' + nhlStageTitle_(name) + ': ' + e.message); }
    finally { QUIET_ = false; }
    var i = NHL_SETUP_STAGES.indexOf(name);
    st.stage = i + 1 < NHL_SETUP_STAGES.length ? NHL_SETUP_STAGES[i + 1] : 'done';
    p.setProperty('NHL_SETUP', JSON.stringify(st));
  }
  var done = st.stage === 'done';
  nhlSetupSafety_(done ? 0 : 60 * 1000);
  var left = done ? [] : NHL_SETUP_STAGES.slice(NHL_SETUP_STAGES.indexOf(st.stage)).map(nhlStageTitle_);
  return { done: done, log: st.log, left: left };
}

function nhlStageTitle_(s) {
  return { teams: 'клубы и ключи', sheets: 'листы и формулы на 32 команды', prev: 'прошлый сезон 2025/26', schedule: 'календарь 2026/27',
    compute: 'рейтинги, прогнозы, карточка, купон', finish: 'автоматика и проверка' }[s] || s;
}

function nhlSetupStage_(ss, stage) {
  var p = PropertiesService.getScriptProperties();
  if (stage === 'teams') {
    // свойства КХЛ (канал, игра, журналы, кэши) — удалить; ключи — оставить
    var all = p.getProperties(), removed = 0;
    Object.keys(all).forEach(function (k) { if (NHL_KEEP_PROPS.indexOf(k) === -1) { p.deleteProperty(k); removed++; } });
    var sh = ss.getSheetByName(SHEET_TEAMS) || ss.insertSheet(SHEET_TEAMS);
    nhlUnmerge_(ss);                                                         // в таблице КХЛ были объединённые ячейки-заметки (напр. A25:F30) — они «съедали» клубы
    if (sh.getLastRow() >= 2) sh.getRange(2, 1, sh.getLastRow() - 1, Math.max(6, sh.getLastColumn())).clearContent();
    sh.getRange(1, 1, 1, 6).setValues([['Команда (каноничное название)', 'Старые / альтернативные названия', 'Стартовый рейтинг (1-100)', 'Аббревиатура', 'Конференция', 'Дивизион']]);
    sh.getRange(2, 3, NHL_TEAMS.length + 10, 1).setNumberFormat('0');        // в таблице КХЛ ниже 23-й строки мог стоять текстовый формат — рейтинг должен быть числом
    sh.getRange(2, 1, NHL_TEAMS.length, 6).setValues(NHL_TEAMS.map(function (t) {
      var nick = t[2].split(' ').slice(-1)[0];
      return [t[1], [t[2], t[0], nick].join(', '), t[8], t[0], t[3], t[4]];
    }));
    var back = sh.getRange(2, 1, NHL_TEAMS.length, 3).getValues();
    var bad = NHL_TEAMS.filter(function (t, i) { return back[i][0] !== t[1] || typeof back[i][2] !== 'number'; }).map(function (t) { return t[1]; });
    if (bad.length) throw new Error('справочник записался не полностью (' + bad.join(', ') + ') — пришлите это Claude');
    var nv = 0; try { nv = nhlFixValidations_(ss); } catch (e) { nv = 'ошибка: ' + e.message; }   // до записи календаря: правила «только из справочника» → на 32 клуба и без запрета
    return 'клубов: ' + NHL_TEAMS.length + ', удалено служебных свойств КХЛ: ' + removed + (nv ? ', правил проверки ввода исправлено: ' + nv : '');
  }
  if (stage === 'sheets') return nhlConvertSheets_(ss);
  if (stage === 'prev') { var r = nhlLoadPrevSeason_(ss); return 'матчей: ' + r.games; }
  if (stage === 'schedule') return nhlLoadSchedule_(ss);
  if (stage === 'compute') {
    var out = [];
    var tryStep = function (label, fn) { try { fn(); out.push(label); } catch (e) { out.push(label + ' ⚠ ' + e.message); } };
    tryStep('проверка ввода на 32 клуба', function () { nhlFixValidations_(ss); });
    tryStep('Elo и рейтинг силы', function () { computeAndWriteElo_(true); });   // рейтинг силы пишется внутри Elo
    tryStep('доли по лиге', function () { updateLeagueRates_(true); });
    tryStep('дом/выезд', function () { setupHomeAwayScoringSplit_(); });
    tryStep('прогнозы на 2 недели', function () { syncPredictionRows_(); });
    tryStep('формулы шансов', function () { applyProbabilityFormula_(ss.getSheetByName('прогнозы')); setupRegulationAndTotals_(); });
    tryStep('карточка команды', function () { setupTeamCard_(); });
    tryStep('купон дня', function () { setupCouponSheet_(); });
    tryStep('мой купон', function () { setupMyCouponBuilder_(); });
    tryStep('поправки', function () { ensureTweaksSheet_(ss); tweaksRankingRender_(); });
    tryStep('краткие прогнозы', function () { renderBriefSheet_(ss); });
    return out.join(', ');
  }
  if (stage === 'finish') {
    var r2 = ensureAutomation_(true);
    try { autoRender_(ss); } catch (e) {}
    try { var ex = ss.getSheetByName(EXPERT_SHEET); if (ex) ss.deleteSheet(ex); expertChannels_(ss); } catch (e) {}   // каналы КХЛ → канал Зислиса (свои можно дописать)
    return 'запусков по расписанию: ' + r2.total;
  }
  return '';
}

/** Формулы с 22 команд КХЛ → 32 команды НХЛ; границы диапазонов матчей — с запасом на сезон НХЛ. */
function nhlBounds_(f) {
  return String(f)
    .replace(/R23C/g, 'R33C')                                  // Data!$A$2:$A$23 и т.п.
    .replace(/R(442|997|999|1000|1002)C/g, 'R1600C')           // «результаты матчей», «прогнозы»
    .replace(/R749C/g, 'R1400C')                               // «Результаты 2025-26»
    .replace(/'Броски_кэш'!R2C(\d+):R10C/g, "'Броски_кэш'!R2C$1:R40C")
    .replace(/\(22-1\)/g, '(32-1)');
}

/** Строка формул листа по образцу (R1C1) для строк from..to; col A — формула поиска команды по имени. */
function nhlTeamRows_(sh, tplRow, from, to, names, opts) {
  opts = opts || {};
  var lastCol = Math.max(sh.getLastColumn(), opts.minCols || 1);
  var tpl = sh.getRange(tplRow, 1, 1, lastCol).getFormulasR1C1()[0].map(nhlBounds_);
  if (opts.patch) tpl = tpl.map(opts.patch);
  var vals = sh.getRange(tplRow, 1, 1, lastCol).getValues()[0];
  if (sh.getMaxRows() < to + 5) sh.insertRowsAfter(sh.getMaxRows(), to + 5 - sh.getMaxRows());
  var rows = [];
  for (var r = from; r <= to; r++) {
    rows.push(tpl.map(function (f, c) {
      if (c === 0 && names) return "=INDEX('" + SHEET_TEAMS + "'!R2C1:R33C1;MATCH(\"" + names[r - from] + "\";'" + SHEET_TEAMS + "'!R2C1:R33C1;0))";
      if (f) return f;
      return opts.keepValues && vals[c] !== '' ? vals[c] : '';
    }));
  }
  // формулы — через R1C1, значения — отдельно
  var block = sh.getRange(from, 1, to - from + 1, lastCol);
  block.clearContent();
  var fr = rows.map(function (row) { return row.map(function (x) { return typeof x === 'string' && x.charAt(0) === '=' ? x : ''; }); });
  block.setFormulasR1C1(fr);
  if (opts.keepValues) {
    rows.forEach(function (row, i) { row.forEach(function (x, c) { if (!(typeof x === 'string' && x.charAt(0) === '=') && x !== '') sh.getRange(from + i, c + 1).setValue(x); }); });
  }
  // строки ниже 33 (если были) — очистить
  if (sh.getMaxRows() > to) sh.getRange(to + 1, 1, Math.min(sh.getMaxRows() - to, 40), lastCol).clearContent();
  return to - from + 1;
}

function nhlConvertSheets_(ss) {
  var names = NHL_TEAMS.map(function (t) { return t[1]; }), out = [];
  // 1. листы «по командам»: 32 строки по образцу строки 2
  [['Data', 30], ['Parser_Data', 5], ['Форма_расчет', 15]].forEach(function (x) {
    var sh = ss.getSheetByName(x[0]); if (!sh) return;
    nhlTeamRows_(sh, 2, 2, 1 + NHL_TEAM_ROWS, names, { minCols: x[1] });
    out.push(x[0]);
  });
  var pd = ss.getSheetByName('Parser_Data');
  if (pd) pd.getRange(2, 2, NHL_TEAM_ROWS, 4).clearContent();                 // старые (фиктивные) числа КХЛ
  // 2. «Таблица»: место k = номер строки − 1
  var tb = ss.getSheetByName('Таблица');
  if (tb) {
    nhlTeamRows_(tb, 2, 2, 1 + NHL_TEAM_ROWS, null, { minCols: 13, patch: function (f) { return f.replace(/LARGE\((R2C13:R33C13);\s*\d+\)/g, 'LARGE($1;ROW()-1)').replace(/LARGE\((R2C13:R33C13),\s*\d+\)/g, 'LARGE($1,ROW()-1)'); } });
    tb.getRange(2, 1, NHL_TEAM_ROWS, 1).setValues(names.map(function (_, i) { return [i + 1]; }));
    out.push('Таблица');
  }
  // 3. «прогнозы»: строка-образец (последняя несыгранная с формулами) → строка 2, остальное очистить; параметры модели L1:M5 не трогаем
  var pr = ss.getSheetByName('прогнозы');
  if (pr) {
    var lastCol = Math.max(pr.getLastColumn(), 58), lr = lastMatchRow_(pr), tplRow = -1;
    var dcol = pr.getRange(2, 4, Math.max(1, lr - 1), 1).getFormulas();
    for (var i = dcol.length - 1; i >= 0; i--) if (dcol[i][0]) { tplRow = i + 2; break; }
    if (tplRow < 0) throw new Error('на листе «прогнозы» нет строки с формулами, которую можно взять за образец');
    var tpl = pr.getRange(tplRow, 1, 1, lastCol).getFormulasR1C1()[0].map(nhlBounds_);
    if (pr.getMaxRows() < 1650) pr.insertRowsAfter(pr.getMaxRows(), 1650 - pr.getMaxRows());
    var maxR = pr.getMaxRows();
    [[1, 11], [14, lastCol - 13]].forEach(function (blk) { pr.getRange(2, blk[0], maxR - 1, blk[1]).clearContent(); });   // A:K и N:… ; L:M — параметры
    tpl[0] = ''; tpl[1] = ''; tpl[2] = ''; tpl[11] = ''; tpl[12] = '';   // A:C — дата и команды (данные), L:M — параметры модели
    pr.getRange(2, 1, 1, lastCol).setFormulasR1C1([tpl.map(function (f, c) { return c === 11 || c === 12 ? '' : f; })]);
    pr.getRange('M2:M5').setValues([[6], [90], [0.5], [0.23]]);            // дом. преимущество, K, доля «больше 5.5», доля ОТ (уточнятся по данным)
    out.push('прогнозы (образец из строки ' + tplRow + ')');
  }
  // 4. «результаты матчей»: место на сезон НХЛ (1312 матчей)
  var rs = ss.getSheetByName(SHEET_RESULTS);
  if (rs && rs.getMaxRows() < 1650) rs.insertRowsAfter(rs.getMaxRows(), 1650 - rs.getMaxRows());
  // 5. «Мои поправки»: записи КХЛ убрать (табло пересчитается)
  var tw = ss.getSheetByName(SHEET_TWEAKS);
  if (tw && tw.getLastRow() >= 2) tw.getRange(2, 1, tw.getLastRow() - 1, 5).clearContent();
  // 5б. карточка команды: выбранные команды КХЛ убрать (иначе проверка ввода не даст пересоздать лист)
  var card = ss.getSheetByName('Карточка команды');
  if (card) { try { card.getRange('B3:B4').clearDataValidations(); } catch (e) {} card.getRange('B3:B4').clearContent(); }
  // 6. листы с данными КХЛ — очистить (заголовки и оформление остаются)
  var cleared = 0;
  NHL_CLEAR_SHEETS.forEach(function (n) {
    var sh = ss.getSheetByName(n); if (!sh || sh.getMaxRows() < 2) return;
    sh.getRange(2, 1, sh.getMaxRows() - 1, Math.max(1, sh.getMaxColumns())).clearContent(); cleared++;
  });
  out.push('очищено листов с данными КХЛ: ' + cleared);
  return out.join('; ');
}

/** Календарь 2026/27 → «результаты матчей» (с нуля), первый матч — в строку-образец «прогнозов». */
function nhlLoadSchedule_(ss) {
  var sh = ss.getSheetByName(SHEET_RESULTS);
  var games = nhlGamesBetween_(NHL_SEASON_FROM, NHL_SEASON_TO, 200000);
  if (games.length < 100) throw new Error('календарь сезона пока не получен (' + games.length + ' матчей) — API НХЛ не ответил, настройка продолжится завтра утром сама');
  var b = '', gj = null;
  try { b = sh.getRange(2, 2).getFormulaR1C1(); gj = sh.getRange(2, 7, 1, 4).getFormulasR1C1()[0]; } catch (e) { b = ''; }
  if (sh.getLastRow() >= 2) sh.getRange(2, 1, sh.getLastRow() - 1, Math.max(10, sh.getLastColumn())).clearContent();
  var list = games.map(function (x) { return { key: x.iso, home: x.home, away: x.away, x: x }; });
  sh.getRange(2, 1, list.length, 1).setValues(list.map(function (m) { return [keyToSheetDate_(m.key)]; })).setNumberFormat('dd.mm.yyyy');
  sh.getRange(2, 3, list.length, 2).setValues(list.map(function (m) { return [m.home, m.away]; }));
  if (b && gj && gj.join('')) {
    sh.getRange(2, 2, list.length, 1).setFormulasR1C1(list.map(function () { return [b]; }));
    sh.getRange(2, 7, list.length, 4).setFormulasR1C1(list.map(function () { return gj.map(function (f) { return f || '=FALSE()'; }); }));
  } else nhlWriteResultFormulas_(sh, 2, list.length);
  var chk = sh.getRange(2, 2, list.length, 3).getValues(), fb = sh.getRange(2, 2).getFormula();
  var miss = chk.filter(function (r, i) { return r[1] !== list[i].home || r[2] !== list[i].away; }).length;
  if (miss || !fb) throw new Error('календарь записался не полностью (строк без команд: ' + miss + (fb ? '' : ', нет формулы статуса') + ') — пришлите это Claude');
  // уже сыгранные (если настройка запущена после старта сезона) — счёт сразу
  var played = 0;
  list.forEach(function (m, i) {
    if (!m.x.final) return;
    sh.getRange(2 + i, 5, 1, 3).setValues([[m.x.hg, m.x.ag, m.x.ot]]); played++;
  });
  // первый несыгранный матч — в строку-образец «прогнозов» (от неё скрипт размножит формулы)
  var pr = ss.getSheetByName('прогнозы'), first = list.filter(function (m) { return !m.x.final && m.key >= todayKey_(); })[0];
  if (pr && first) pr.getRange(2, 1, 1, 3).setValues([[keyToSheetDate_(first.key), first.home, first.away]]);
  return 'матчей: ' + list.length + (played ? ', уже сыграно: ' + played : '') + ', первый: ' + (first ? first.key + ' ' + first.home + ' — ' + first.away : '—');
}

/** Меню: ключи и Telegram для таблицы НХЛ (вводятся здесь, в таблице, — не в чате). */
function nhlKeysSetup_() {
  var ui = SpreadsheetApp.getUi(), p = PropertiesService.getScriptProperties();
  var ask = function (key, title, hint) {
    var cur = p.getProperty(key);
    var r = ui.prompt(title, hint + (cur ? '\n\nСейчас задано. Оставьте поле пустым, чтобы не менять.' : ''), ui.ButtonSet.OK_CANCEL);
    if (r.getSelectedButton() !== ui.Button.OK) return false;
    var v = String(r.getResponseText() || '').trim();
    if (v) p.setProperty(key, v);
    return true;
  };
  if (!ask('GEMINI_KEY', 'Ключ Gemini', 'Тот же, что в таблице КХЛ (Apps Script КХЛ → ⚙️ Настройки проекта → Свойства скрипта → GEMINI_KEY).')) return;
  if (!ask('TAVILY_KEY', 'Ключ Tavily (необязательно)', 'Запасной поиск. Можно оставить пустым: новости берутся со sports.ru и из Telegram-каналов.')) return;
  if (!ask('TG_BOT_TOKEN', 'Токен Telegram-бота', 'Тот же бот, что в КХЛ (свойство TG_BOT_TOKEN). Бот будет только присылать вам сводки — кнопки игры остаются в КХЛ.')) return;
  if (!ask('TG_ADMIN_ID', 'Ваш Telegram ID', 'Число из свойства TG_ADMIN_ID таблицы КХЛ. Сюда будут приходить сводки агента по НХЛ.')) return;
  if (!ask('NHL_CHANNEL', 'Канал для публикаций', 'Например @jarvibet. Бот должен быть администратором канала с правом публиковать. Пусто — посты в канал не отправляются.')) return;
  uiAlert_('Сохранено. Проверить можно: меню «НХЛ-парсер» → 🔧 Проверки → «Ключи агента» и «Телеграм: бот, канал, личка».');
}

/* ---------------- меню и автоматика НХЛ ---------------- */

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  dailyMenu_(ui, '📅 НХЛ · Ежедневно', DAILY_NHL_);
  // Три отдельных меню в строке меню таблицы — по тому, куда уходит результат:
  //   «НХЛ-парсер» — только таблица; «📩 НХЛ → мне в ТГ» — личка от бота; «📣 НХЛ · ТГ группа» — всё, что публикуется в группу (канал).
  ui.createMenu('НХЛ-парсер')
    .addItem('🏒 Обновить всё после игрового дня', 'runAfterGameDay_')
    .addItem('📈 Обновить коэффициенты', 'updateMarketOdds_')
    .addItem('✍️ Учесть мои поправки', 'tweaksUpdateNow_')
    .addItem('📊 Статистика НХЛ, xG, травмы, вратари', 'nhlStatsNow_')
    .addItem('🆚 Сравнение нашей модели с NeurHL', 'neurhlNow_')
    .addSubMenu(ui.createMenu('🎯 Стартовый рейтинг')
      .addItem('1 · Посчитать варианты и сравнить с букмекерами', 'nhlStartBuildNow_')
      .addItem('2 · Применить вариант A (с NeurHL)', 'nhlStartApplyA_')
      .addItem('2 · Применить вариант B (без NeurHL)', 'nhlStartApplyB_')
      .addItem('Вернуть прежний стартовый рейтинг', 'nhlStartRevert_'))
    .addSeparator()
    .addItem('Спросить Джарвиса про матч', 'askJarvisAboutMatch_')
    .addItem('Пересчитать мой купон', 'recalcMyCoupon_')
    .addItem('Список всех событий на выбранную дату', 'updateAllEventsForDay_')
    .addSeparator()
    .addSubMenu(ui.createMenu('🧠 Агент')
      .addItem('Заполнить досье всех команд', 'dossierFillAll_')
      .addItem('Пересобрать досье с нуля', 'dossierRebuild_')
      .addItem('Составы: собрать и обновить ключевых игроков', 'lineupsUpdateNow_')
      .addItem('Проверить выводы агента по результатам', 'agentSignalsReviewNow_'))
    .addSubMenu(ui.createMenu('✍️ Мои поправки')
      .addItem('Выключить поправки', 'tweaksTurnOff_')
      .addItem('Включить поправки', 'tweaksTurnOn_'))
    .addSubMenu(ui.createMenu('🔧 Проверки (бесплатно)')
      .addItem('Источники НХЛ', 'nhlDiagNow_')
      .addItem('Источник новостей', 'checkNewsNow_')
      .addItem('Ключи агента', 'agentCheckKeys_')
      .addItem('Телеграм: бот, канал, личка', 'tgCheckNow_')
      .addItem('Поправка формы: проверить на сыгранных матчах', 'modelFormCheck_')
      .addItem('Обновить «броски на гол»', 'updateShotsStats_')
      .addItem('Самопроверка факторов модели', 'selfCheckNow_'))
    .addSubMenu(ui.createMenu('Настройки')
      .addItem('Первичная настройка таблицы под НХЛ', 'nhlSetupNow_')
      .addItem('Ключи и Telegram для НХЛ', 'nhlKeysSetup_')
      .addItem('Смайлики: взять из другой таблицы', 'tgEmojiImportNow_')
      .addItem('Смайлики: отдать в другую таблицу', 'tgEmojiExportNow_')
      .addItem('Включить всю автоматику', 'installAllAutomation_')
      .addItem('Статус автоматики', 'autoStatusNow_')
      .addItem('Выключить автоматику', 'removeDailyTrigger_')
      .addItem('Поправка формы: включить в прогноз', 'modelFormOn_')
      .addItem('Поправка формы: выключить', 'modelFormOff_')
      .addItem('Применить самую точную модель', 'applyBestModel_')
      .addItem('Указать API-ключ Anthropic', 'setAnthropicApiKey_')
      .addItem('Навести порядок: цвета вкладок, скрыть служебные листы', 'tidyUpSheets_')
      .addSubMenu(ui.createMenu('Пересоздать лист, если удалили')
        .addItem('Карточка команды', 'setupTeamCard_')
        .addItem('Купон дня', 'setupCouponSheet_')
        .addItem('Мой купон', 'setupMyCouponBuilder_')))
    .addToUi();
  ui.createMenu('📩 НХЛ → мне в ТГ')
    .addItem('🧠 Сводка агента на ближайшую ночь (+ лист в таблице)', 'agentBriefNow_')
    .addItem('🔎 Разведчик: что нового сейчас', 'scoutNow_')
    .addItem('📊 «Сила команд» — пробный пост', 'powerPreviewNow_')
    .addItem('🖼 Карточки матчей ночи', 'bannersAllNow_')
    .addItem('Пробный пост «прогнозы на ночь»', 'nhlPreviewEvening_')
    .addItem('Пробный пост «итоги ночи»', 'nhlPreviewMorning_')
    .addItem('Пробная карточка (бесплатно)', 'bannersTestNow_')
    .addToUi();
  dailyMenu_(ui, '📣 НХЛ · ТГ группа', TG_GROUP_NHL_);
  videoMenu_(ui, '🎬 НХЛ · Видео');
}
function nhlDiagNow_() { nhlDiag_(); sheetOpen_(NHL_DIAG_SHEET); }
var SHEETS_HIDE_EXTRA = ['Обыграй Джарвиса', 'Угадай победителей', 'Игра_игроки', 'Игра_прогнозы', 'Live_журнал'];   // игра и LIVE — только в КХЛ

/* Матчи НХЛ идут ночью по Москве (02:00–07:00), поэтому:
 *  • обновление после игрового дня — в 13:00 по Красноярску (09:00 МСК), когда доиграны и матчи Западного побережья;
 *  • сводка агента — в 22:00 по Красноярску (18:00 МСК) на матчи ближайшей ночи, после утренних раскаток. */
var AUTO_JOBS = [
  { fn: 'runAfterGameDay_', kind: 'day', hour: 13, what: 'Обновить всё после игрового дня: результаты, Elo, календарь, прогнозы, точность, составы, ключевые игроки, проверка выводов агента, банкролл' },
  { fn: 'agentDailyBriefAuto_', kind: 'day', hour: AGENT_HOUR, what: 'Агент: сводка по матчам ближайшей ночи в личку (новости, досье, составы прошлых матчей)' },
  { fn: 'updateMarketOddsAuto_', kind: 'hours', every: 2, what: 'Коэффициенты рынка (Pinnacle, NHL) и «Лучший прогноз»' },
  { fn: 'nhlEveningAuto_', kind: 'day', hour: 23, what: 'Канал: «прогнозы на ночь» (шансы, лучший прогноз, вратари, вывод агента) + вам расхождения модели и рынка' },
  { fn: 'nhlGoaliesAuto_', kind: 'hours', every: 1, what: 'До начала матчей (19:00–07:00 МСК): сменились вратари — правка поста в канале и сообщение вам' },
  { fn: 'nhlMorningAuto_', kind: 'day', hour: 14, what: 'Канал: «итоги ночи» (счёт матчей и «Наши»)' },
  { fn: 'scoutAuto_', kind: 'hours', every: 1, what: 'Разведчик: новые посты и новости по командам ближайших матчей → лист «Факты»' },
  { fn: 'scoutReportAuto_', kind: 'minutes', every: 15, what: 'Разведчик: итог вам за ~1,5 ч до каждого матча' },
  { fn: 'powerAuto_', kind: 'week', hour: 21, what: 'Канал: «Сила команд» по понедельникам (рейтинг и изменения мест за неделю)' },
  { fn: 'bannersAuto_', kind: 'day', hour: 21, what: 'Карточки матчей ближайшей ночи (картинки) — вам в Telegram' },
  { fn: 'weeklyAuto_', kind: 'week', hour: 5, what: 'Раз в неделю (пн): досье всех команд заново + «броски на гол» по статистике НХЛ' },
  { fn: 'monthlyAuto_', kind: 'month', hour: 4, what: 'Раз в месяц (1-го числа): самопроверка факторов модели' }
];

/** День (по МСК), на который делать сводку: до 08:00 МСК — матчи идут сейчас, позже — матчи следующей ночи. */
function nhlBriefDay_(now) {
  now = now || new Date();
  var h = Number(Utilities.formatDate(now, 'Europe/Moscow', 'HH')), today = Utilities.formatDate(now, 'Europe/Moscow', 'yyyy-MM-dd');
  return h < 8 ? today : addDaysKey_(today, 1);
}

function agentDailyBriefAuto_() {
  if (nhlNotReady_(true)) return;
  try { var r = agentDailyBrief_(nhlBriefDay_()) || {}; autoMark_('agentDailyBriefAuto_', !r.errors && !r.sendError, agentBriefStatus_(r)); }
  catch (e) { console.log('agent: ' + e.message); autoMark_('agentDailyBriefAuto_', false, e.message); autoNotifyAdmin_('⚠ Сводка агента НХЛ не собралась: ' + e.message); }
}

function agentBriefNow_() {
  if (!agentProps_().getProperty('GEMINI_KEY')) { uiAlert_('Нужен ключ Gemini: меню «НХЛ-парсер» → Настройки → «Ключи и Telegram для НХЛ».'); return; }
  var day = nhlBriefDay_(), r = agentDailyBrief_(day) || {};
  var d = day.split('-').reverse().join('.');
  if (!r.matches) { uiAlert_('На ' + d + ' (по МСК) матчей НХЛ нет — сводку делать не по чему.'); return; }
  uiAlert_('Сводка на ' + d + ' готова: матчей ' + r.done + (r.rest ? ' из ' + r.matches : '') + (r.errors ? ', с ошибкой ' + r.errors : '') + '. Модель: ' + r.model + '.\n' +
    'Лист «' + AGENT_SHEET + '»' + (r.sent ? ' + сообщение вам от бота' + (r.parts > 1 ? ' (' + r.parts + ' части)' : '') + '.'
      : r.sendError ? '.\n⚠ В Telegram не ушло: ' + r.sendError + '.' : '. Чтобы получать сводку в Telegram, укажите свой ID: Настройки → «Ключи и Telegram для НХЛ».') +
    (r.rest ? '\n⏳ Ещё ' + r.rest + ' — таблица доделает сама через пару минут и пришлёт следующим сообщением.' : ''));
}

function weeklyAuto_() {
  if (nhlNotReady_(true)) return;
  var msg = [], ok = true;
  QUIET_ = true;
  try { var n = updateShotsStats_(); msg.push('броски на гол: ' + n + ' команд'); } catch (e) { msg.push('броски: ' + e.message); }
  try { var ru = nhlRussiansRefresh_(SpreadsheetApp.getActive()); msg.push('россиян в составах: ' + ru.count); } catch (e) { msg.push('россияне: ' + e.message); }
  finally { QUIET_ = false; }
  try { PropertiesService.getScriptProperties().deleteProperty('DOSSIER_PASS'); var r = dossierFillAll_(true, true) || {}; msg.push('досье: обновлено ' + (r.done || 0) + (r.left ? ', остальные — следующими запусками' : '')); }
  catch (e) { ok = false; msg.push('досье: ' + e.message); }
  autoMark_('weeklyAuto_', ok, msg.join('; '));
}

/** Защита от запуска до настройки или не в той таблице. true — остановиться (сообщение уже показано). */
function nhlNotReady_(auto) {
  var ss = SpreadsheetApp.getActive(), st = nhlSetupState_();
  var need = nhlMissingSheets_(ss);
  var msg = '';
  if (need.length) msg = nhlWrongTableText_(need);
  else if (st.stage !== 'done') msg = 'Таблица ещё не настроена под НХЛ' + (st.stage ? ' (настройка идёт: ' + nhlStageTitle_(st.stage) + ')' : '') +
    '.\n\nМеню «НХЛ-парсер» → Настройки → «Первичная настройка таблицы под НХЛ».';
  if (!msg) return false;
  if (auto && need.length) {
    try { var mine = {}; AUTO_JOBS.forEach(function (j) { mine[j.fn] = true; });
      ScriptApp.getProjectTriggers().forEach(function (t) { if (mine[t.getHandlerFunction()]) ScriptApp.deleteTrigger(t); }); } catch (e) {}
    autoNotifyAdmin_('⚠ НХЛ: автоматика была включена не в той таблице — выключил её там. ' + msg);
    return true;
  }
  if (auto) autoNotifyAdmin_('⚠ НХЛ: ' + msg); else uiAlert_(msg);
  return true;
}

/** Листы копии таблицы КХЛ, без которых скрипт НХЛ работать не может. */
var NHL_REQUIRED_SHEETS = ['результаты матчей', 'прогнозы', 'Data', 'Форма_расчет', 'Parser_Data', 'Таблица', 'Справочник команд'];
function nhlMissingSheets_(ss) { return NHL_REQUIRED_SHEETS.filter(function (n) { return !ss.getSheetByName(n); }); }
function nhlWrongTableText_(miss) {
  return 'Это не та таблица: в ней нет листов ' + miss.join(', ') + '.\n\nСкрипт НХЛ работает только в таблице «КАПЕР ДЖАРВИС НХЛ» — копии таблицы КХЛ, где все эти листы есть. ' +
    'Откройте её, вставьте код туда и запустите настройку там. Здесь ничего не изменено.';
}

/** Правила проверки ввода «значение из диапазона 'Справочник команд'!…» (их ставили руками в таблице КХЛ на 22 строки)
 *  → на 32 клуба; списки с названиями клубов КХЛ → диапазон справочника. Возвращает число исправленных правил. */
function nhlFixValidations_(ss) {
  var teams = ss.getSheetByName(SHEET_TEAMS); if (!teams) return 0;
  var full = teams.getRange(2, 1, NHL_TEAM_ROWS, 1), fixed = 0;
  var khl = ['СКА', 'ЦСКА', 'Ак Барс', 'Авангард', 'Локомотив', 'Металлург', 'Трактор', 'Салават Юлаев', 'Динамо Москва', 'Спартак'];
  ss.getSheets().forEach(function (sh) {
    var nr = Math.min(sh.getMaxRows(), 60), nc = Math.min(sh.getMaxColumns(), 40), dv;
    try { dv = sh.getRange(1, 1, nr, nc).getDataValidations(); } catch (e) { return; }
    var cols = {};
    for (var r = 0; r < nr; r++) for (var c = 0; c < nc; c++) {
      var rule = dv[r][c]; if (!rule || cols[c]) continue;
      var type = String(rule.getCriteriaType()), vals = rule.getCriteriaValues() || [];
      var onTeams = /VALUE_IN_RANGE/.test(type) && vals[0] && vals[0].getSheet && vals[0].getSheet().getName() === SHEET_TEAMS;
      var khlList = /VALUE_IN_LIST/.test(type) && (vals[0] || []).some(function (x) { return khl.indexOf(String(x)) >= 0; });
      if (onTeams || khlList) cols[c] = { row: r + 1, rule: rule, drop: vals[1] !== false };
    }
    Object.keys(cols).forEach(function (c) {
      var x = cols[c], col = +c + 1;
      var nb = x.rule.copy().requireValueInRange(full, x.drop).setAllowInvalid(true).build();   // предупреждение вместо запрета: скрипт пишет названия сам
      var rows = sh.getMaxRows() - x.row + 1;
      // только те клетки столбца, где правило уже стояло
      var cur = sh.getRange(x.row, col, rows, 1).getDataValidations();
      var out = cur.map(function (row) { return [row[0] ? nb : null]; });
      sh.getRange(x.row, col, rows, 1).setDataValidations(out);
      fixed++;
    });
  });
  var elo = ss.getSheetByName(SHEET_ELO);
  if (elo) { try { elo.getRange(1, 1, elo.getMaxRows(), 1).clearDataValidations(); } catch (e) {} }   // лист Elo пишет только скрипт
  return fixed;
}

/** Разъединить объединённые ячейки в верхней части листов, куда пишутся 32 клуба и календарь. */
function nhlUnmerge_(ss) {
  [SHEET_TEAMS, 'Data', 'Parser_Data', 'Форма_расчет', 'Таблица', SHEET_ELO, 'прогнозы', SHEET_RESULTS, 'Досье_команд'].forEach(function (n) {
    var sh = ss.getSheetByName(n); if (!sh) return;
    try { sh.getRange(1, 1, Math.min(sh.getMaxRows(), 60), Math.min(sh.getMaxColumns(), 30)).breakApart(); } catch (e) { /* не критично */ }
  });
}

/* ==========================================================================
 * 📊 ДОПОЛНИТЕЛЬНЫЕ ДАННЫЕ НХЛ (бесплатно, без ключей)
 *  • НХЛ: таблица (форма за 10 игр, серия, дома/в гостях), большинство/меньшинство, броски, вратари (Sv%);
 *  • MoneyPuck.com: ожидаемые голы (xG) команд 5×5 и вратарей (GSAx). Данные бесплатны для некоммерческого использования, ссылка на MoneyPuck обязательна;
 *  • ESPN: список травмированных;
 *  • Daily Faceoff: стартовые вратари на игровой день (подтверждён / вероятно).
 *  Всё это идёт в сводку агента, досье и на листы «Статистика_НХЛ», «Вратари_сегодня». Модель прогнозов НЕ меняется.
 * ==========================================================================*/
var NHL_STATS_SHEET = 'Статистика_НХЛ';
var NHL_GOALIES_SHEET = 'Вратари_сегодня';
var MONEYPUCK_BASE = 'https://moneypuck.com/moneypuck/playerData/seasonSummary/';
var ESPN_INJURIES_URL = 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/injuries';
var DAILYFACEOFF_URL = 'https://www.dailyfaceoff.com/starting-goalies/';
var PIPELINE_EXTRA_NAME = 'Статистика НХЛ, xG, травмы, сравнение с NeurHL';
var PIPELINE_GAME = false;                           // игра «Обыграй Джарвиса» — только в КХЛ
var NHL_BUNDLE_ = null;                                   // кэш на один запуск

/** Любая аббревиатура (в т.ч. MoneyPuck: «T.B», «N.J», «L.A», «S.J») → русское название. */
function nhlRuAny_(x) {
  var a = String(x || '').toUpperCase().replace(/\./g, '').trim();
  return nhlRu_(a) || nhlRuFromEnglish_(x);
}

function nhlFetchText_(url) {
  try {
    var r = UrlFetchApp.fetch(url, { muteHttpExceptions: true, followRedirects: true, headers: { 'User-Agent': SPORTS_UA['User-Agent'], 'Accept': '*/*' } });
    return { code: r.getResponseCode(), text: r.getResponseCode() === 200 ? r.getContentText() : '' };
  } catch (e) { return { code: 'ошибка: ' + e.message, text: '' }; }
}

/** Таблица НХЛ: {команда: {gp, pts, l10, streak, home, road}} */
function nhlStandings_() {
  var d = nhlGet_('standings/now'), out = {};
  ((d && d.standings) || []).forEach(function (t) {
    var ru = nhlRuAny_(t.teamAbbrev && (t.teamAbbrev.default || t.teamAbbrev)) || nhlRuFromEnglish_(t.teamName && (t.teamName.default || t.teamName));
    if (!ru) return;
    out[ru] = { prev: !!(t.seasonId && String(t.seasonId) !== NHL_SEASON), gp: t.gamesPlayed, pts: t.points, l10: [t.l10Wins, t.l10Losses, t.l10OtLosses].join('-'),
      streak: t.streakCode ? t.streakCode + (t.streakCount || '') : '', home: [t.homeWins, t.homeLosses, t.homeOtLosses].join('-'),
      road: [t.roadWins, t.roadLosses, t.roadOtLosses].join('-') };
  });
  return out;
}

/** Командная статистика НХЛ за сезон (если сезон пуст — прошлый): {команда: {pp, pk, sf, sa, gf, ga}} + .season */
function nhlTeamStats_() {
  var get = function (season) {
    var d = nhlGet_('team/summary?isAggregate=false&isGame=false&start=0&limit=50&cayenneExp=' + encodeURIComponent('gameTypeId=2 and seasonId=' + season), NHL_STATS_API);
    return (d && d.data) || [];
  };
  var list = get(NHL_SEASON), season = NHL_SEASON;
  if (!list.length) { list = get(NHL_PREV_SEASON); season = NHL_PREV_SEASON; }
  var out = {};
  list.forEach(function (t) {
    var ru = nhlRuFromEnglish_(t.teamFullName || ''); if (!ru) return;
    var pct = function (v) { v = Number(v); return isFinite(v) && v !== 0 ? Math.round(v * 1000) / 10 : ''; };
    var r1 = function (v) { v = Number(v); return isFinite(v) ? Math.round(v * 10) / 10 : ''; };
    out[ru] = { gp: t.gamesPlayed, pp: pct(t.powerPlayPct), pk: pct(t.penaltyKillPct), sf: r1(t.shotsForPerGame), sa: r1(t.shotsAgainstPerGame),
      gf: r1(t.goalsForPerGame), ga: r1(t.goalsAgainstPerGame) };
  });
  out.season = season;
  return out;
}

/** Вратари НХЛ: {команда: [{name, gs, sv, gaa}] по числу стартов} */
function nhlGoalieStats_() {
  var get = function (season) {
    var d = nhlGet_('goalie/summary?isAggregate=false&isGame=false&start=0&limit=200&sort=' + encodeURIComponent('[{"property":"gamesStarted","direction":"DESC"}]') +
      '&cayenneExp=' + encodeURIComponent('gameTypeId=2 and seasonId=' + season), NHL_STATS_API);
    return (d && d.data) || [];
  };
  var list = get(NHL_SEASON), season = NHL_SEASON;
  if (!list.length) { list = get(NHL_PREV_SEASON); season = NHL_PREV_SEASON; }
  var out = {};
  list.forEach(function (g) {
    var abbr = String(g.teamAbbrevs || '').split(/[,\s]+/).filter(Boolean).pop();     // сменил команду — берём последнюю
    var ru = nhlRuAny_(abbr); if (!ru) return;
    (out[ru] = out[ru] || []).push({ name: g.goalieFullName || '', gs: Number(g.gamesStarted) || 0, sv: Number(g.savePct) || 0, gaa: Number(g.goalsAgainstAverage) || 0 });
  });
  Object.keys(out).forEach(function (k) { out[k].sort(function (a, b) { return b.gs - a.gs; }); });
  out.season = season;
  return out;
}

/** CSV MoneyPuck → массив объектов по заголовку. */
function mpCsv_(text) {
  var rows = []; try { rows = Utilities.parseCsv(text); } catch (e) { rows = []; }
  if (rows.length < 2) return [];
  var h = rows[0];
  return rows.slice(1).map(function (r) { var o = {}; h.forEach(function (k, i) { if (!(k in o)) o[k] = r[i]; }); return o; });
}

/** MoneyPuck: xG команд (5×5 и все ситуации) и GSAx вратарей. Текущий сезон, а если данных ещё нет — прошлый. */
function moneyPuckData_() {
  var y = +NHL_SEASON.slice(0, 4), out = { teams: {}, goalies: {}, season: '', codes: [] };
  for (var k = 0; k < 2 && !Object.keys(out.teams).length; k++) {
    var yr = y - k, tr = nhlFetchText_(MONEYPUCK_BASE + yr + '/regular/teams.csv');
    out.codes.push(yr + ' teams: ' + tr.code);
    var rows = mpCsv_(tr.text);
    rows.forEach(function (r) {
      var ru = nhlRuAny_(r.team || r.name); if (!ru) return;
      var t = out.teams[ru] = out.teams[ru] || {};
      var gp = Number(r.games_played) || 0;
      if (r.situation === '5on5') { t.xg5 = Math.round(Number(r.xGoalsPercentage) * 1000) / 10; t.cf5 = Math.round(Number(r.corsiPercentage) * 1000) / 10; }
      if (r.situation === 'all' && gp) { t.xgf = Math.round(Number(r.xGoalsFor) / gp * 100) / 100; t.xga = Math.round(Number(r.xGoalsAgainst) / gp * 100) / 100; t.gp = gp; }
    });
    if (Object.keys(out.teams).length) {
      out.season = yr + '/' + String(yr + 1).slice(2);
      var gr = nhlFetchText_(MONEYPUCK_BASE + yr + '/regular/goalies.csv');
      out.codes.push(yr + ' goalies: ' + gr.code);
      mpCsv_(gr.text).forEach(function (r) {
        if (r.situation !== 'all') return;
        var ru = nhlRuAny_(r.team); if (!ru) return;
        (out.goalies[ru] = out.goalies[ru] || []).push({ name: r.name, gp: Number(r.games_played) || 0, gsax: Math.round((Number(r.xGoals) - Number(r.goals)) * 10) / 10 });
      });
      Object.keys(out.goalies).forEach(function (t) { out.goalies[t].sort(function (a, b) { return b.gp - a.gp; }); });
    }
  }
  return out;
}

/** ESPN: травмы по командам {команда: [{name, pos, status, note, date}]} */
function espnInjuries_() {
  var r = nhlFetchText_(ESPN_INJURIES_URL), out = {}, d = null;
  try { d = JSON.parse(r.text); } catch (e) { d = null; }
  var teams = (d && (d.injuries || d.teams)) || [];
  teams.forEach(function (t) {
    var ru = nhlRuFromEnglish_(t.displayName || (t.team && (t.team.displayName || t.team.name)) || '');
    if (!ru) return;
    (t.injuries || []).forEach(function (i) {
      var a = i.athlete || {};
      (out[ru] = out[ru] || []).push({ name: a.displayName || a.fullName || '', pos: (a.position && (a.position.abbreviation || a.position.name)) || '',
        status: i.status || (i.type && i.type.description) || '', note: i.shortComment || (i.details && i.details.type) || '', date: String(i.date || '').slice(0, 10) });
    });
  });
  out.code = r.code;
  return out;
}

/** Daily Faceoff: стартовые вратари на день по Нью-Йорку ('yyyy-MM-dd'). [{home, away, hg, hs, ag, as}] */
function dailyFaceoffGoalies_(etDay) {
  var r = nhlFetchText_(DAILYFACEOFF_URL + (etDay || '')), out = [];
  out.code = r.code;
  var m = r.text.match(/<script[^>]*id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/);
  var data = null; try { data = m ? JSON.parse(m[1]) : null; } catch (e) { data = null; }
  out.found = !!data;
  var seen = {};
  var walk = function (o, depth) {
    if (!o || typeof o !== 'object' || depth > 12) return;
    if (Array.isArray(o)) { o.forEach(function (x) { walk(x, depth + 1); }); return; }
    if (('homeGoalieName' in o) || ('awayGoalieName' in o)) {
      var h = nhlRuFromEnglish_(o.homeTeamName || o.homeTeamSlug || ''), a = nhlRuFromEnglish_(o.awayTeamName || o.awayTeamSlug || '');
      if (h && a && !seen[h + a]) {
        seen[h + a] = true;
        out.push({ home: h, away: a, hg: o.homeGoalieName || '', hs: o.homeNewsStrengthName || o.homeGoalieStatus || '', ag: o.awayGoalieName || '', as: o.awayNewsStrengthName || o.awayGoalieStatus || '' });
      }
    }
    Object.keys(o).forEach(function (k) { walk(o[k], depth + 1); });
  };
  walk(data, 0);
  out.snippet = r.text ? r.text.slice(0, 3000) : '';
  return out;
}

function nhlGoalieStatusRu_(s) {
  s = String(s || '').toLowerCase();
  if (/confirm/.test(s)) return 'подтверждён';
  if (/likely|expected|probable/.test(s)) return 'вероятно';
  if (/unconfirm|projected/.test(s)) return 'не подтверждён';
  return s || 'нет данных';
}

/** Все дополнительные данные (один раз за запуск). withGoalies — ещё и стартовые вратари на дни dayKeys (по МСК). */
function nhlBundle_(withGoalies, dayKeys) {
  if (!NHL_BUNDLE_) {
    var b = { errors: [] };
    var safe = function (name, fn, def) { try { return fn(); } catch (e) { b.errors.push(name + ': ' + e.message); return def; } };
    b.standings = safe('таблица НХЛ', nhlStandings_, {});
    b.stats = safe('статистика НХЛ', nhlTeamStats_, {});
    b.goalies = safe('вратари НХЛ', nhlGoalieStats_, {});
    b.mp = safe('MoneyPuck', moneyPuckData_, { teams: {}, goalies: {}, season: '' });
    b.injuries = safe('ESPN', espnInjuries_, {});
    b.starters = null;
    NHL_BUNDLE_ = b;
  }
  if (withGoalies && !NHL_BUNDLE_.starters) {
    var st = {}, days = {};
    (dayKeys || [agentMskDay_()]).forEach(function (d) { days[addDaysKey_(d, -1)] = true; days[d] = true; });   // МСК-день = вечер по Нью-Йорку накануне
    Object.keys(days).forEach(function (et) {
      try { dailyFaceoffGoalies_(et).forEach(function (g) { st[g.home + '|' + g.away] = g; }); } catch (e) { NHL_BUNDLE_.errors.push('Daily Faceoff: ' + e.message); }
    });
    NHL_BUNDLE_.starters = st;
  }
  return NHL_BUNDLE_;
}

/** Строка о команде для агента (только факты с явной командой). */
function nhlTeamLine_(b, team) {
  var p = [], s = b.standings[team], t = b.stats[team], x = b.mp.teams[team], g = (b.goalies[team] || [])[0], mg = (b.mp.goalies[team] || [])[0];
  var seasonNote = b.stats.season && b.stats.season !== NHL_SEASON ? ' (прошлый сезон)' : '';
  if (s && s.gp) p.push((s.prev ? '(итог прошлого сезона) ' : '') + 'очки: ' + s.pts + ' в ' + s.gp + ' играх; последние 10: ' + s.l10 + (s.streak ? '; серия ' + s.streak : '') + '; дома ' + s.home + ', в гостях ' + s.road);
  if (t && (t.pp || t.pk)) p.push('большинство ' + t.pp + '%, меньшинство ' + t.pk + '%, броски за игру ' + t.sf + ' / против ' + t.sa + seasonNote);
  if (x && x.xg5) p.push('доля ожидаемых голов 5×5 (xG%, MoneyPuck, ' + b.mp.season + '): ' + x.xg5 + '%' + (x.xgf ? ', xG за игру ' + x.xgf + ' / против ' + x.xga : ''));
  if (g) p.push('основной вратарь по стартам — ' + g.name + ' (' + g.gs + ' стартов, Sv% ' + g.sv.toFixed(3).replace(/^0/, '') + ')' + (mg && mg.name === g.name ? ', GSAx ' + (mg.gsax > 0 ? '+' : '') + mg.gsax : '') + seasonNote);
  return p.length ? team + ': ' + p.join('; ') + '.' : '';
}

function nhlInjuryLine_(b, team) {
  var list = (b.injuries[team] || []).slice(0, 8);
  return list.length ? team + ': ' + list.map(function (i) { return i.name + (i.pos ? ' (' + i.pos + ')' : '') + ' — ' + (i.status || '?') + (i.note ? ', ' + i.note : '') + (i.date ? ', с ' + i.date.split('-').reverse().slice(0, 2).join('.') : ''); }).join('; ') : '';
}

/** Для сводки агента: документы-источники и короткие строки в Telegram. */
function agentExtraContext_(m, ss) {
  var b = nhlBundle_(true, [m.day || agentMskDay_()]), docs = [], lines = [];
  var st = [nhlTeamLine_(b, m.home), nhlTeamLine_(b, m.away)].filter(Boolean);
  if (st.length) docs.push({ title: 'Статистика НХЛ и MoneyPuck.com (таблица, спецбригады, xG, вратари)', url: 'https://www.nhl.com/stats/teams', text: st.join('\n'), date: '' });
  var inj = [nhlInjuryLine_(b, m.home), nhlInjuryLine_(b, m.away)].filter(Boolean);
  if (inj.length) docs.push({ title: 'ESPN — список травмированных', url: 'https://www.espn.com/nhl/injuries', text: inj.join('\n'), date: mskNow_('dd.MM') });
  var pre = null; try { pre = preseasonContext_(ss || SpreadsheetApp.getActive(), [m.home, m.away], m.day || agentMskDay_()); } catch (e) { pre = null; }
  if (pre) docs.push({ title: 'Разбор роликов YouTube (эксперты): расклад, травмы, составы, форма, ожидания', url: 'https://www.youtube.com/', text: pre, date: '' });
  try { lines = lines.concat(expertPicksFor_(ss || SpreadsheetApp.getActive(), m)); } catch (e) {}
  var g = b.starters && b.starters[m.home + '|' + m.away];
  if (g && (g.hg || g.ag)) {
    docs.push({ title: 'Daily Faceoff — стартовые вратари', url: DAILYFACEOFF_URL, date: mskNow_('dd.MM'),
      text: m.home + ': ' + (g.hg || 'нет данных') + ' (' + nhlGoalieStatusRu_(g.hs) + '); ' + m.away + ': ' + (g.ag || 'нет данных') + ' (' + nhlGoalieStatusRu_(g.as) + ').' });
    lines.push('🥅 Daily Faceoff: ' + (g.hg || '?') + ' (' + nhlGoalieStatusRu_(g.hs) + ') — ' + (g.ag || '?') + ' (' + nhlGoalieStatusRu_(g.as) + ')');
  }
  var xh = b.mp.teams[m.home], xa = b.mp.teams[m.away], th = b.stats[m.home], ta = b.stats[m.away];
  var parts = [];
  if (xh && xa && xh.xg5 && xa.xg5) parts.push('xG 5×5: ' + xh.xg5 + '% — ' + xa.xg5 + '%');
  if (th && ta && th.pp && ta.pp) parts.push('бол./мен.: ' + th.pp + '/' + th.pk + ' — ' + ta.pp + '/' + ta.pk);
  if (parts.length) lines.push('📊 ' + parts.join(' · '));
  var ni = (b.injuries[m.home] || []).length, na = (b.injuries[m.away] || []).length;
  if (ni || na) lines.push('🚑 ESPN: травмированных ' + ni + ' — ' + na);
  return { docs: docs, lines: lines };
}

/** Для досье: травмы из ESPN как одна «новость». */
function dossierExtraNews_(team) {
  var b = nhlBundle_(false), line = nhlInjuryLine_(b, team), out = [];
  if (line) out.push({ id: 'espn-' + team, url: 'https://www.espn.com/nhl/injuries', title: 'ESPN, список травмированных — ' + line, date: new Date() });
  var tl = nhlTeamLine_(b, team);
  if (tl) out.push({ id: 'nhlstats-' + team, url: 'https://www.nhl.com/stats/teams', title: 'Статистика НХЛ и MoneyPuck.com — ' + tl, date: new Date() });
  try { out = out.concat(videoDossierNews_(team)); } catch (e) {}
  return out;
}

/** Листы «Статистика_НХЛ» и (если есть) «Вратари_сегодня». Возвращает текст для отчёта. */
function nhlStatsUpdate_(ss, withGoalies) {
  ss = ss || SpreadsheetApp.getActive();
  NHL_BUNDLE_ = null;
  var b = nhlBundle_(!!withGoalies, [agentMskDay_(), addDaysKey_(agentMskDay_(), 1)]);
  var head = ['Команда', 'Игры', 'Очки', 'Посл. 10 (В-П-ОТ)', 'Серия', 'Дома', 'В гостях', 'Большинство, %', 'Меньшинство, %', 'Броски за игру', 'Броски против',
    'xG% 5×5 (MoneyPuck)', 'Corsi% 5×5', 'xG за игру', 'xG против', 'Основной вратарь', 'Стартов', 'Sv%', 'GSAx (MoneyPuck)', 'Травмы (ESPN)', 'Обновлено (МСК)'];
  var now = mskNow_();
  var rows = NHL_TEAMS.map(function (t) {
    var n = t[1], s = b.standings[n] || {}, st = b.stats[n] || {}, x = b.mp.teams[n] || {}, g = (b.goalies[n] || [])[0] || {}, mg = ((b.mp.goalies[n] || []).filter(function (q) { return q.name === g.name; })[0]) || {};
    return [n, s.gp || '', s.pts === undefined ? '' : s.pts, s.l10 || '', s.streak || '', s.home || '', s.road || '', st.pp || '', st.pk || '', st.sf || '', st.sa || '',
      x.xg5 || '', x.cf5 || '', x.xgf || '', x.xga || '', g.name || '', g.gs || '', g.sv ? Math.round(g.sv * 1000) / 1000 : '', mg.gsax === undefined ? '' : mg.gsax,
      (b.injuries[n] || []).map(function (i) { return i.name + ' — ' + i.status; }).join('; '), now];
  });
  var sh = ss.getSheetByName(NHL_STATS_SHEET) || ss.insertSheet(NHL_STATS_SHEET);
  sh.clearContents();
  sh.getRange(1, 1, 1, head.length).setValues([head]).setFontWeight('bold');
  sh.getRange(2, 1, rows.length, head.length).setValues(rows);
  sh.getRange(rows.length + 3, 1).setValue('Источники: NHL.com (таблица, статистика, вратари' + (b.stats.season && b.stats.season !== NHL_SEASON ? ' — пока прошлый сезон' : '') + '); ' +
    'xG, Corsi и GSAx — MoneyPuck.com' + (b.mp.season ? ' (сезон ' + b.mp.season + ')' : '') + '; травмы — ESPN. Модель прогнозов эти столбцы не использует — они для анализа и сводки агента.');
  try { sh.setFrozenRows(1); sh.setFrozenColumns(1); } catch (e) {}
  var gl = 0;
  if (withGoalies && b.starters) {
    var gs = ss.getSheetByName(NHL_GOALIES_SHEET) || ss.insertSheet(NHL_GOALIES_SHEET);
    gs.clearContents();
    var gh = ['Хозяева', 'Гости', 'Вратарь хозяев', 'Статус', 'Вратарь гостей', 'Статус', 'Обновлено (МСК)'];
    var grows = Object.keys(b.starters).map(function (k) { var g = b.starters[k]; return [g.home, g.away, g.hg, nhlGoalieStatusRu_(g.hs), g.ag, nhlGoalieStatusRu_(g.as), now]; });
    gs.getRange(1, 1, 1, gh.length).setValues([gh]).setFontWeight('bold');
    if (grows.length) gs.getRange(2, 1, grows.length, gh.length).setValues(grows);
    gl = grows.length;
  }
  try { nhlStatsLog_(ss, rows, b.mp.season); } catch (e) { /* история — не критично */ }
  var cnt = function (o) { return Object.keys(o || {}).filter(function (k) { return k !== 'season' && k !== 'code'; }).length; };
  return 'таблица ' + cnt(b.standings) + ', статистика ' + cnt(b.stats) + ', вратари ' + cnt(b.goalies) + ', xG ' + cnt(b.mp.teams) + ' (MoneyPuck ' + (b.mp.season || '—') + '), травмы ' + cnt(b.injuries) + ' команд' +
    (withGoalies ? ', стартовые вратари: матчей ' + gl : '') + (b.errors.length ? '; ⚠ ' + b.errors.join('; ') : '');
}

function pipelineExtra_(ss) {
  var out = nhlStatsUpdate_(ss, false);
  try { out += '; ' + neurhlUpdate_(ss).text; } catch (e) { out += '; сравнение с NeurHL не обновилось: ' + e.message; }   // не критично для остального
  return out;
}

/** Меню: обновить листы статистики сейчас (бесплатно). */
function nhlStatsNow_() {
  var r = nhlStatsUpdate_(SpreadsheetApp.getActive(), true);
  uiAlert_('Статистика НХЛ обновлена (кредиты не тратились):\n' + r + '\n\nЛисты «' + NHL_STATS_SHEET + '» и «' + NHL_GOALIES_SHEET + '».');
}

/* ==========================================================================
 * 📣 ПУБЛИКАЦИИ В КАНАЛ (НХЛ) и личные уведомления
 *  В канал (свойство NHL_CHANNEL, напр. @jarvibet):
 *   • 23:00 по Красноярску (19:00 МСК) — «прогнозы на ночь»: шансы модели, лучший прогноз, стартовые вратари, короткий вывод агента;
 *     до начала матчей раз в час проверяются вратари — если сменились, пост правится, а вам приходит уведомление;
 *   • 14:00 по Красноярску (10:00 МСК) — «итоги ночи»: счёт, что угадали, точность с начала сезона.
 *  Только вам: сводка агента целиком, расхождения модели и рынка > 10 п.п., смены вратарей, ошибки автоматики.
 * ==========================================================================*/
var NHL_POST_MAX = 3800;                 // запас до лимита Telegram (4096)
var NHL_DIVERGENCE_PP = 0.10;            // «модель и рынок разошлись» — от 10 п.п.

function nhlChannelId_() { return PropertiesService.getScriptProperties().getProperty('NHL_CHANNEL') || ''; }

/** Прогнозы по матчам дня (МСК): [{home, away, time, pH, bestH, mark, honest, hg, ag, ot, played}] */
function nhlDayForecasts_(ss, dayKey) {
  var list = agentMatchesOfDay_(ss, dayKey), out = [];
  if (!list.length) return out;
  var pr = ss.getSheetByName('прогнозы'), rs = ss.getSheetByName(SHEET_RESULTS), idx = {}, res = {};
  if (pr && pr.getLastRow() >= 2) {
    var lc = pr.getLastColumn(), h = pr.getRange(1, 1, 1, lc).getValues()[0];
    var cBest = -1; h.forEach(function (x, i) { if (/^Лучший прогноз: шансы/.test(String(x))) cBest = i; });
    pr.getRange(2, 1, pr.getLastRow() - 1, lc).getValues().forEach(function (r) {
      if (!(r[0] instanceof Date) || !r[1]) return;
      idx[sheetDayKey_(r[0]) + '|' + String(r[1]).trim() + '|' + String(r[2]).trim()] = { pH: Number(r[3]), bestH: cBest >= 0 && r[cBest] !== '' ? Number(r[cBest]) : null,
        mark: String(r[10] || ''), honest: String(r[COL_INTEGRITY - 1] || '').trim() !== 'нет' };
    });
  }
  if (rs && rs.getLastRow() >= 2) rs.getRange(2, 1, rs.getLastRow() - 1, 7).getValues().forEach(function (r) {
    if (!(r[0] instanceof Date) || String(r[1]).trim() !== 'Сыгран') return;
    res[sheetDayKey_(r[0]) + '|' + String(r[2]).trim() + '|' + String(r[3]).trim()] = { hg: Number(r[4]), ag: Number(r[5]), ot: r[6] === true || r[6] === 'TRUE' };
  });
  list.forEach(function (m) {
    var k = dayKey + '|' + m.home + '|' + m.away, f = idx[k] || {}, g = res[k];
    out.push({ home: m.home, away: m.away, time: m.time, pH: isFinite(f.pH) && f.pH > 0 ? f.pH : null, bestH: isFinite(f.bestH) && f.bestH > 0 ? f.bestH : null,
      mark: f.mark || '', honest: f.honest !== false, played: !!g, hg: g ? g.hg : null, ag: g ? g.ag : null, ot: g ? g.ot : false });
  });
  return out;
}

/** Короткий вывод агента по матчу (поле «Важное» с листа сводок), без номеров источников. */
function nhlAgentKey_(ss, dayKey, m) {
  var sh = ss.getSheetByName(AGENT_SHEET); if (!sh || sh.getLastRow() < 2) return '';
  var d = dayKey.split('-').reverse().join('.'), name = m.home + ' — ' + m.away;
  var rows = sh.getRange(2, 1, Math.min(sh.getLastRow() - 1, 300), AGENT_HEADER.length).getValues();
  for (var i = 0; i < rows.length; i++) {                                   // свежие сводки — сверху
    if (String(rows[i][0]) !== d || String(rows[i][1]) !== name) continue;
    var t = String(rows[i][6] || '').replace(/\s*\[(\d+|досье|S\d+)\]/g, '').replace(/\s+([,.;:!?])/g, '$1').replace(/\s+/g, ' ').trim();
    if (!t || /^нет данных/i.test(t) || /^⚠/.test(String(rows[i][2]))) return '';
    return t.length > 220 ? t.slice(0, 217).replace(/\s+\S*$/, '') + '…' : t;
  }
  return '';
}

function nhlPct_(x) { return Math.round(x * 100) + '%'; }
function nhlGoalieSig_(g) { return g ? [g.hg, g.hs, g.ag, g.as].join('|') : ''; }

/** Блоки поста «прогнозы на ночь» (по одному на матч) + подпись. */
function nhlEveningBlocks_(ss, dayKey, starters) {
  var f = nhlDayForecasts_(ss, dayKey).filter(function (x) { return !x.played; });
  return f.map(function (x) {
    var b = ['🏒 <b>' + escHtml_(x.home + ' — ' + x.away) + '</b>' + (x.time ? ' · ' + x.time + ' МСК' : '')];
    if (x.pH) b.push('📊 Модель: ' + nhlPct_(x.pH) + ' — ' + nhlPct_(1 - x.pH));
    if (x.bestH) { var hs = x.bestH >= 0.5; b.push('🎯 Лучший прогноз: <b>' + escHtml_(hs ? x.home : x.away) + '</b> (' + nhlPct_(hs ? x.bestH : 1 - x.bestH) + ')'); }
    var g = starters && starters[x.home + '|' + x.away];
    if (g && (g.hg || g.ag)) b.push('🥅 ' + escHtml_((g.hg || '?') + ' (' + nhlGoalieStatusRu_(g.hs) + ') — ' + (g.ag || '?') + ' (' + nhlGoalieStatusRu_(g.as) + ')'));
    var k = nhlAgentKey_(ss, dayKey, x);
    if (k) b.push('🧠 ' + escHtml_(k));
    return { match: x, text: b.join('\n'), sig: nhlGoalieSig_(g) };
  });
}

/** Склеить блоки в сообщения ≤ NHL_POST_MAX. */
function nhlPack_(head, blocks, foot) {
  var msgs = [], cur = head;
  blocks.forEach(function (b) {
    if ((cur + '\n\n' + b).length > NHL_POST_MAX) { msgs.push(cur); cur = b; } else cur += '\n\n' + b;
  });
  cur += '\n\n' + foot;
  msgs.push(cur);
  return msgs;
}

var NHL_EVENING_FOOT = '<i>Как я считаю: рейтинг Elo, форма, дом, отдых. Лучший прогноз: 75% линия Pinnacle + 25% моя модель. Вратари — Daily Faceoff. 🧠 — вывод по новостям, может ошибаться. Не является призывом к ставкам.</i>';

/** Прогнозы на ночь. target: 'channel' — в канал, 'admin' — пробный пост вам. */
function nhlEveningPost_(target, dayKey) {
  var ss = SpreadsheetApp.getActive(), p = PropertiesService.getScriptProperties();
  dayKey = dayKey || nhlBriefDay_();
  NHL_BUNDLE_ = null;
  var b = nhlBundle_(true, [dayKey]), blocks = nhlEveningBlocks_(ss, dayKey, b.starters);
  if (!blocks.length) return { sent: 0, matches: 0 };
  var head = '🇺🇸 <b>НХЛ · прогнозы на ночь</b> · ' + escHtml_(ruDayTitle_(dayKey).toLowerCase()) + ' (МСК)';
  var msgs = nhlPack_(head, blocks.map(function (x) { return x.text; }), NHL_EVENING_FOOT);
  var chat = target === 'channel' ? nhlChannelId_() : p.getProperty('TG_ADMIN_ID');
  if (!chat) throw new Error(target === 'channel' ? 'не указан канал: Настройки → «Ключи и Telegram для НХЛ»' : 'не указан ваш Telegram ID');
  var ids = [];
  msgs.forEach(function (t, i) {
    var r = tg_('sendMessage', { chat_id: chat, text: target === 'channel' ? t : '👀 ПРОБНЫЙ ПОСТ (в канал не ушёл)\n\n' + t, parse_mode: 'HTML', disable_web_page_preview: true });
    if (!r || !r.ok) throw new Error('Telegram: ' + ((r && r.description) || 'нет ответа'));
    ids.push(r.result.message_id);
  });
  if (target === 'channel') {
    var sig = {}; blocks.forEach(function (x) { sig[x.match.home + '|' + x.match.away] = x.sig; });
    p.setProperty('NHL_POST_' + dayKey, JSON.stringify({ chat: chat, ids: ids, sig: sig }));
    dailyMark_('evening');
    try { nhlDivergenceNote_(ss, dayKey); } catch (e) { /* не критично */ }
  }
  return { sent: ids.length, matches: blocks.length };
}

/** Вам в личку: где модель и рынок расходятся сильнее 10 п.п. */
function nhlDivergenceNote_(ss, dayKey) {
  var rows = nhlDayForecasts_(ss, dayKey).filter(function (x) { return x.pH && x.bestH; }).map(function (x) {
    var mkt = (x.bestH - 0.25 * x.pH) / 0.75; return { x: x, mkt: mkt, d: x.pH - mkt };
  }).filter(function (r) { return Math.abs(r.d) >= NHL_DIVERGENCE_PP; });
  if (!rows.length) return 0;
  autoNotifyAdmin_('⚖️ НХЛ, ' + dayKey.split('-').reverse().slice(0, 2).join('.') + ': модель и рынок расходятся ≥ ' + Math.round(NHL_DIVERGENCE_PP * 100) + ' п.п.\n' +
    rows.map(function (r) { return r.x.home + ' — ' + r.x.away + ': модель ' + nhlPct_(r.x.pH) + ', рынок ' + nhlPct_(r.mkt) + ' на хозяев'; }).join('\n') +
    '\n(в канал это не публикуется)');
  return rows.length;
}

/** Раз в час, 19:00–07:00 МСК: вратари сменились — поправить пост в канале и сообщить вам. */
function nhlGoalieRefresh_() {
  var h = Number(Utilities.formatDate(new Date(), 'Europe/Moscow', 'HH'));
  if (h >= 8 && h < 19) return { skipped: 'вне окна' };
  var ss = SpreadsheetApp.getActive(), p = PropertiesService.getScriptProperties(), dayKey = nhlBriefDay_();
  var st = null; try { st = JSON.parse(p.getProperty('NHL_POST_' + dayKey) || 'null'); } catch (e) { st = null; }
  if (!st || !st.ids || !st.ids.length) return { skipped: 'поста нет' };
  NHL_BUNDLE_ = null;
  var b = nhlBundle_(true, [dayKey]), blocks = nhlEveningBlocks_(ss, dayKey, b.starters), changed = [], before = JSON.stringify(st.sig || {});
  st.sig = st.sig || {};
  blocks.forEach(function (x) {
    var k = x.match.home + '|' + x.match.away, old = st.sig[k] || '';
    if (x.sig && x.sig !== old) {
      var o = old.split('|'), n = x.sig.split('|');
      if (old) changed.push(x.match.home + ' — ' + x.match.away + ': ' + (o[0] !== n[0] ? o[0] + ' → ' + n[0] : n[0] + ' ' + nhlGoalieStatusRu_(n[1])) + ' / ' + (o[2] !== n[2] ? o[2] + ' → ' + n[2] : n[2] + ' ' + nhlGoalieStatusRu_(n[3])));
      st.sig[k] = x.sig;
    }
  });
  if (JSON.stringify(st.sig) === before) return { edited: 0 };                 // вратари те же — пост не трогаем
  var head = '🇺🇸 <b>НХЛ · прогнозы на ночь</b> · ' + escHtml_(ruDayTitle_(dayKey).toLowerCase()) + ' (МСК)';
  var msgs = nhlPack_(head, blocks.map(function (x) { return x.text; }), NHL_EVENING_FOOT), edited = 0;
  if (msgs.length === st.ids.length) {
    msgs.forEach(function (t, i) { var r = tg_('editMessageText', { chat_id: st.chat, message_id: st.ids[i], text: t, parse_mode: 'HTML', disable_web_page_preview: true }); if (r && r.ok) edited++; });
  }
  p.setProperty('NHL_POST_' + dayKey, JSON.stringify(st));
  if (changed.length) autoNotifyAdmin_('🥅 НХЛ: изменились вратари (пост в канале ' + (edited ? 'обновлён' : 'НЕ обновлён — проверьте') + '):\n' + changed.join('\n'));
  return { edited: edited, changed: changed.length };
}

/** Итоги ночи. target: 'channel' | 'admin'. */
function nhlMorningPost_(target, dayKey) {
  var ss = SpreadsheetApp.getActive(), p = PropertiesService.getScriptProperties();
  dayKey = dayKey || Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM-dd');
  var f = nhlDayForecasts_(ss, dayKey).filter(function (x) { return x.played; });
  if (!f.length) return { sent: 0, matches: 0 };
  // только счёт матчей ночи и «Наши» — без отметок прогнозов и точности (по вашему решению от 30.09)
  var lines = f.map(function (x) {
    return escHtml_(x.home + ' — ' + x.away) + ' <b>' + x.hg + ':' + x.ag + '</b>' + (x.ot ? ' ОТ/Б' : '');
  });
  var ours = '';
  try { ours = nhlOursText_(ss, dayKey, f); } catch (e) { ours = ''; }
  var text = '🇺🇸 <b>НХЛ · итоги ночи</b> · ' + escHtml_(ruDayTitle_(dayKey).toLowerCase()) + '\n\n' + lines.join('\n') + (ours ? '\n\n' + ours : '');
  var chat = target === 'channel' ? nhlChannelId_() : p.getProperty('TG_ADMIN_ID');
  if (!chat) throw new Error(target === 'channel' ? 'не указан канал: Настройки → «Ключи и Telegram для НХЛ»' : 'не указан ваш Telegram ID');
  var r = tg_('sendMessage', { chat_id: chat, text: target === 'channel' ? text : '👀 ПРОБНЫЙ ПОСТ (в канал не ушёл)\n\n' + text, parse_mode: 'HTML', disable_web_page_preview: true });
  if (!r || !r.ok) throw new Error('Telegram: ' + ((r && r.description) || 'нет ответа'));
  if (target === 'channel') { p.setProperty('NHL_MORNING_' + dayKey, '1'); dailyMark_('morning'); }   // и автоматика не опубликует второй раз
  return { sent: 1, matches: f.length };
}

/** Точность с начала сезона: модель (✅/❌ по честным прогнозам) и лучший прогноз. */
function nhlSeasonAccuracy_(ss) {
  var pr = ss.getSheetByName('прогнозы'), rs = ss.getSheetByName(SHEET_RESULTS), out = { ok: 0, n: 0, bok: 0, bn: 0 };
  if (!pr || pr.getLastRow() < 2) return out;
  var res = {};
  if (rs && rs.getLastRow() >= 2) rs.getRange(2, 1, rs.getLastRow() - 1, 6).getValues().forEach(function (r) {
    if (r[0] instanceof Date && String(r[1]).trim() === 'Сыгран') res[sheetDayKey_(r[0]) + '|' + String(r[2]).trim() + '|' + String(r[3]).trim()] = Number(r[4]) > Number(r[5]);
  });
  var lc = pr.getLastColumn(), h = pr.getRange(1, 1, 1, lc).getValues()[0], cBest = -1;
  h.forEach(function (x, i) { if (/^Лучший прогноз: шансы/.test(String(x))) cBest = i; });
  pr.getRange(2, 1, pr.getLastRow() - 1, lc).getValues().forEach(function (r) {
    var mark = String(r[10] || ''); if (mark !== '✅' && mark !== '❌') return;
    if (String(r[COL_INTEGRITY - 1] || '').trim() === 'нет') return;
    out.n++; if (mark === '✅') out.ok++;
    var k = r[0] instanceof Date ? sheetDayKey_(r[0]) + '|' + String(r[1]).trim() + '|' + String(r[2]).trim() : '';
    if (cBest >= 0 && r[cBest] !== '' && k in res) { out.bn++; if ((Number(r[cBest]) >= 0.5) === res[k]) out.bok++; }
  });
  return out;
}

/* ---- запуски по расписанию и кнопки меню ---- */
function nhlEveningAuto_() {
  if (nhlNotReady_(true)) return;
  if (!nhlChannelId_()) { autoMark_('nhlEveningAuto_', true, 'канал не указан — пост не публикуется'); return; }
  try { var r = nhlEveningPost_('channel'); autoMark_('nhlEveningAuto_', true, r.matches ? 'опубликовано: матчей ' + r.matches + ', сообщений ' + r.sent : 'матчей нет'); }
  catch (e) { autoMark_('nhlEveningAuto_', false, e.message); autoNotifyAdmin_('⚠ НХЛ: пост «прогнозы на ночь» не ушёл: ' + e.message); }
}
function nhlGoaliesAuto_() {
  try { var r = nhlGoalieRefresh_(); if (!r.skipped) autoMark_('nhlGoaliesAuto_', true, 'правок поста: ' + (r.edited || 0) + ', смен вратарей: ' + (r.changed || 0)); }
  catch (e) { autoMark_('nhlGoaliesAuto_', false, e.message); }
}
function nhlMorningAuto_() {
  if (nhlNotReady_(true)) return;
  var p = PropertiesService.getScriptProperties(), day = Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM-dd');
  itogiAutoNhl_(day);
  if (!nhlChannelId_() || p.getProperty('NHL_MORNING_' + day)) return;
  try { var r = nhlMorningPost_('channel', day); if (r.sent) p.setProperty('NHL_MORNING_' + day, '1'); autoMark_('nhlMorningAuto_', true, r.matches ? 'итоги: матчей ' + r.matches : 'сыгранных матчей нет'); }
  catch (e) { autoMark_('nhlMorningAuto_', false, e.message); autoNotifyAdmin_('⚠ НХЛ: пост «итоги ночи» не ушёл: ' + e.message); }
}
function nhlPreviewEvening_() {
  try {
    var ss = SpreadsheetApp.getActive(), day = nhlBriefDay_();
    for (var i = 0; i < 10 && !agentMatchesOfDay_(ss, day).length; i++) day = addDaysKey_(day, 1);   // пробный пост — на ближайший игровой день
    var r = nhlEveningPost_('admin', day);
    uiAlert_(r.matches ? 'Пробный пост на ' + day.split('-').reverse().join('.') + ' отправлен вам в Telegram: матчей ' + r.matches + '.' : 'В ближайшие 10 дней матчей нет.');
  } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}
function nhlPublishEveningNow_() { try { var r = nhlEveningPost_('channel'); uiAlert_(r.matches ? 'Опубликовано в ' + nhlChannelId_() + ': матчей ' + r.matches + '.' : 'Матчей нет — публиковать нечего.'); } catch (e) { uiAlert_('Не получилось: ' + e.message); } }
function nhlPreviewMorning_() { try { var r = nhlMorningPost_('admin'); uiAlert_(r.matches ? 'Пробные итоги отправлены вам в Telegram.' : 'Сыгранных сегодня (по МСК) матчей нет.'); } catch (e) { uiAlert_('Не получилось: ' + e.message); } }
function nhlPublishMorningNow_() { try { var r = nhlMorningPost_('channel'); uiAlert_(r.matches ? 'Итоги опубликованы в ' + nhlChannelId_() + '.' : 'Сыгранных сегодня (по МСК) матчей нет.'); } catch (e) { uiAlert_('Не получилось: ' + e.message); } }

/* карточки матчей: лига, день и канал НХЛ */
var BANNER_LEAGUE = 'NHL';
function bannersDay_() { return nhlBriefDay_(); }
/* ---------------- 📰 Новостной канал: источник лайва для НХЛ ----------------
 * api-web.nhle.com отдаёт протокол матча событие за событием (play-by-play).
 * Живой счёт нельзя брать из кэша, поэтому здесь свой запрос, без кэша nhlGet_. */
function nhlLiveGet_(path) {
  var r = UrlFetchApp.fetch(NHL_API + path, { muteHttpExceptions: true, headers: { 'Accept': 'application/json', 'User-Agent': SPORTS_UA['User-Agent'] } });
  if (r.getResponseCode() !== 200) throw new Error('НХЛ ответила кодом ' + r.getResponseCode() + ' (' + path.split('?')[0] + ')');
  return JSON.parse(r.getContentText());
}
var NHL_LIVE_STATES_ = { LIVE: 1, CRIT: 1, OVER: 1, FINAL: 1, OFF: 1 };
/** Матчи, которые идут сейчас (или только что закончились): [{id, home, away, state}] */
function nhlLiveMatches_() {
  var j = nhlLiveGet_('score/now'), games = (j && j.games) || [], lim = Date.now() - NEWS_LIVE_BACK_H * 3600000, out = [];
  games.forEach(function (g) {
    if (!NHL_LIVE_STATES_[String(g.gameState || '').toUpperCase()]) return;
    var st = g.startTimeUTC ? Date.parse(g.startTimeUTC) : 0;
    if (st && st < lim) return;
    var home = nhlTeamOf_(g.homeTeam), away = nhlTeamOf_(g.awayTeam);
    if (home && away) out.push({ id: g.id, home: home, away: away, state: g.gameState });
  });
  return out;
}
/* Фамилия в пост: русские игроки — по-русски с листа «Россияне_НХЛ» (его можно править руками),
 * остальные — латиницей. Машинная транслитерация чужих фамилий даёт «Тхомпсон», поэтому её здесь нет. */
var NHL_RU_BY_ID_ = null;
function nhlRuById_(id) {
  if (NHL_RU_BY_ID_ === null) {
    NHL_RU_BY_ID_ = {};
    try {
      var sh = SpreadsheetApp.getActive().getSheetByName(NHL_RU_SHEET);
      if (sh && sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, 3).getValues()
        .forEach(function (r) { if (r[0] && r[2]) NHL_RU_BY_ID_[String(r[0])] = String(r[2]); });
    } catch (e) { NHL_RU_BY_ID_ = {}; }
  }
  return NHL_RU_BY_ID_[String(id)] || '';
}
function nhlLiveName_(spots, id) {
  var ru = nhlRuById_(id);
  if (ru) return ru;
  for (var i = 0; i < spots.length; i++) if (spots[i].playerId === id) {
    var l = spots[i].lastName, en = (l && (l.default || l)) || '';
    if (en) {
      // в новостной таблице незнакомые фамилии копятся на листе, чтобы вписать русские один раз
      if (typeof newsRuNote_ === 'function') { try { newsRuNote_(id, en); } catch (e) {} }
      return en;
    }
    var f = spots[i].firstName;
    return (f && (f.default || f)) || '';
  }
  return '';
}
function nhlLiveSec_(mmss) {
  var m = String(mmss || '').match(/^(\d+):(\d+)$/);
  return m ? Number(m[1]) * 60 + Number(m[2]) : 0;
}
/** Новые события матча НХЛ: [{kind, key, text, video}] */
function nhlLiveEvents_(m) {
  var j = nhlLiveGet_('gamecenter/' + m.id + '/play-by-play');
  if (!j) return [];
  var spots = j.rosterSpots || [], plays = j.plays || [], homeId = (j.homeTeam || {}).id, out = [];
  var state = String(j.gameState || m.state || '').toUpperCase();
  if (plays.length || state) out.push({ kind: 'старт', key: 's:' + m.id, text: newsStartText_(m.home, m.away) });
  plays.forEach(function (pl) {
    var t = String(pl.typeDescKey || '');
    var per = Number((pl.periodDescriptor || {}).number) || 0, d = pl.details || {};
    if (t === 'goal') {
      var forHome = d.eventOwnerTeamId === homeId;
      var assists = [d.assist1PlayerId, d.assist2PlayerId].filter(Boolean).map(function (id) { return nhlLiveName_(spots, id); }).filter(Boolean);
      out.push({
        kind: 'гол', key: 'g:' + m.id + ':' + (pl.eventId || (per + ':' + pl.timeInPeriod)),
        text: newsGoalText_({ home: m.home, away: m.away, team: forHome ? m.home : m.away, forHome: forHome,
          hs: Number(d.homeScore) || 0, as: Number(d.awayScore) || 0, period: per,
          sec: (Math.max(1, per) - 1) * 1200 + nhlLiveSec_(pl.timeInPeriod),
          author: nhlLiveName_(spots, d.scoringPlayerId), assists: assists })
      });
    } else if (t === 'period-end' && per >= 1 && per <= 3) {
      var sc = nhlLiveScoreAt_(plays, pl);
      out.push({ kind: 'период', key: 'p:' + m.id + ':' + per, text: newsPeriodText_(m.home, m.away, per, sc) });
    }
  });
  if (state === 'OVER' || state === 'FINAL' || state === 'OFF') {
    var last = nhlLiveScoreAt_(plays, null), end = nhlLiveEnd_(plays);
    out.push({ kind: 'финал', key: 'f:' + m.id, text: newsFinalText_(m.home, m.away, last, end, []) });
  }
  return out;
}
/** Счёт на момент события (или итоговый, если before не задан): «2:1». */
function nhlLiveScoreAt_(plays, before) {
  var hs = 0, as = 0;
  for (var i = 0; i < plays.length; i++) {
    if (before && plays[i] === before) break;
    var d = plays[i].details || {};
    if (d.homeScore !== undefined) { hs = Number(d.homeScore) || 0; as = Number(d.awayScore) || 0; }
  }
  return hs + ':' + as;
}
/** «овертайм» / «буллиты» — по номеру последнего периода. */
function nhlLiveEnd_(plays) {
  var max = 0;
  plays.forEach(function (pl) { max = Math.max(max, Number((pl.periodDescriptor || {}).number) || 0); });
  return max >= 5 ? 'буллиты' : max === 4 ? 'овертайм' : '';
}

function bannerChannel_() { return nhlChannelId_(); }

/* ---------------- 🎬 Видео экспертов: отличия НХЛ (сам модуль — общий, в коде КХЛ) ---------------- */
var VIDEO_LEAGUE = 'НХЛ';
var PRESEASON_SHEET = 'Предсезон_видео';
var VIDEO_DEFAULT = ['https://www.youtube.com/watch?v=Pk_R5VtodFA', 'https://www.youtube.com/watch?v=BESul9siT4E',
  'https://www.youtube.com/watch?v=wAeeNvv6hN0', 'https://www.youtube.com/watch?v=uwTVqWqrHAQ'];

/** Русское название из английского или русского написания. */
function videoTeamRu_(name) {
  var s = String(name || '').trim();
  if (!s) return null;
  var en = nhlRuFromEnglish_(s);
  if (en) return en;
  var low = s.toLowerCase();
  for (var i = 0; i < NHL_TEAMS.length; i++) if (low === NHL_TEAMS[i][1].toLowerCase() || new RegExp(NHL_TEAMS[i][6], 'i').test(low)) return NHL_TEAMS[i][1];
  return null;
}

/* 📅 «Ежедневно» в НХЛ: матчи ночью по МСК — утро/день у вас это итоги, вечер — прогнозы на ночь (время — по Красноярску). */
var DAILY_NHL_ = [
  ['0 · Что автоматика уже сделала сегодня', 'autoStatusNow_'],
  null,
  ['1 · Обновить всё после ночи матчей', 'runAfterGameDay_'],
  ['2 · Обновить коэффициенты', 'updateMarketOdds_'],
  ['3 · Учесть мои поправки', 'tweaksUpdateNow_', 'runAfterGameDay_'],
  null,
  ['❓ Как пользоваться меню', 'dailyHelp_']
];
var TG_GROUP_NHL_ = [
  ['1 · Итоги ночи → группа', 'dailyMorning_', 'nhlMorningAuto_'],
  ['2 · Прогнозы на ночь → группа', 'dailyEvening_', 'nhlEveningAuto_'],
  ['3 · Карточки матчей ночи → группа', 'dailyCardsChannel_', '-'],
  ['4 · «Сила команд» → группа (пн)', 'powerPostNow_', '-'],
  null,
  ['🖼 Постер «Матчи дня» → мне (ближайший игровой день)', 'matchiPosterNow_', '-'],
  ['🖼 Постер «Итоги дня» → мне (последний игровой день)', 'itogiPosterNow_', '-'],
  ['🔑 Подключить GitHub для постеров', 'itogiSetToken_', '-'],
  ['🖼 Готовый постер → мне в личку', 'posterToMe_', '-'],
  ['🖼 Готовый постер → группа', 'posterToChannel_', '-'],
  null,
  ['🌐 Публичная страница точности (создать / обновить)', 'publicPageNow_'],
  null,
  ['❓ Что куда публикуется', 'dailyHelp_']
];
/* 🖼 ГОТОВЫЙ ПОСТЕР: картинку и подпись к ней кладу на Google Диск, файл POSTER_QUEUE_FILE = {file: id картинки, caption, title}.
 * Кнопки меню «📣 НХЛ · ТГ группа»: сначала вам в личку, потом — с подтверждением — в канал NHL_CHANNEL.
 * Новый постер — новый файл на Диске, код менять не нужно; повторная публикация того же постера — только после второго «Да». */
var POSTER_QUEUE_FILE = 'jarvis_poster_nhl.json';
function posterQueue_() {
  var it = DriveApp.getFilesByName(POSTER_QUEUE_FILE), f = null, x;
  while (it.hasNext()) { x = it.next(); if (!x.isTrashed() && (!f || x.getLastUpdated() > f.getLastUpdated())) f = x; }
  if (!f) throw new Error('на Google Диске нет файла ' + POSTER_QUEUE_FILE + ' — готового постера пока нет');
  var q = JSON.parse(f.getBlob().getDataAsString());
  if (!q || !q.file) throw new Error('в файле ' + POSTER_QUEUE_FILE + ' не указана картинка');
  return q;
}
function posterToMe_() {
  try {
    var q = posterQueue_(), to = PropertiesService.getScriptProperties().getProperty('TG_ADMIN_ID');
    if (!to) throw new Error('не указан TG_ADMIN_ID');
    tgSendPhotos_(to, [DriveApp.getFileById(q.file).getBlob()], q.caption || '');
    uiAlert_('Отправлено вам в личку: «' + (q.title || 'постер') + '». Если всё хорошо — «🖼 Готовый постер → группа».');
  } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}
function posterToChannel_() {
  var ch = nhlChannelId_();
  if (!ch) { uiAlert_('Канал не указан (свойство NHL_CHANNEL).'); return; }
  try {
    var q = posterQueue_(), ui = SpreadsheetApp.getUi(), p = PropertiesService.getScriptProperties(), key = 'POSTER_SENT_' + q.file;
    if (ui.alert('Опубликовать в ' + ch + ' «' + (q.title || 'постер') + '» с подписью:\n\n' + String(q.caption || '').replace(/<[^>]+>/g, ''), ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
    if (p.getProperty(key) && ui.alert('Этот постер уже публиковали (' + p.getProperty(key) + ' МСК). Опубликовать ещё раз?', ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
    tgSendPhotos_(ch, [DriveApp.getFileById(q.file).getBlob()], q.caption || '');
    p.setProperty(key, mskNow_());
    uiAlert_('Опубликовано в ' + ch + ': «' + (q.title || 'постер') + '».');
  } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}

function dailyEvening_() { if (dailyAlready_('evening', 'Пост «прогнозы на ночь»')) return; nhlPublishEveningNow_(); }
function dailyMorning_() {
  var day = Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM-dd');
  if (PropertiesService.getScriptProperties().getProperty('NHL_MORNING_' + day) && !PropertiesService.getScriptProperties().getProperty(dailyKey_('morning'))) dailyMark_('morning');
  if (dailyAlready_('morning', 'Пост «итоги ночи»')) return;
  nhlPublishMorningNow_();
}

/* ==========================================================================
 * 🆚 СРАВНЕНИЕ С NeurHL — независимый эталон для нашей модели НХЛ
 *  NeurHL (github.com/ph05/neurhl, MIT; данные — для некоммерческого использования) до начала сезона 2026/27 выложил
 *  и «заморозил» вероятности на все 1344 матча: нейросеть (p_home_win) и их Elo (p_home_win_elo).
 *  Лист «Сравнение_NeurHL»: по каждому сыгранному матчу — наш ЧЕСТНЫЙ прогноз (сделан до матча), их два прогноза,
 *  результат; сверху — Brier (меньше — лучше, 0.25 = монетка), доля угаданных и logloss по всем трём на одних и тех же матчах.
 *  Ничего в модели не меняет; в канал не публикуется (лицензия данных — только некоммерческая).
 * ==========================================================================*/
var NEURHL_URL = 'https://raw.githubusercontent.com/ph05/neurhl/main/neurhl/output/games_2027.csv';
var NEURHL_SHEET = 'Сравнение_NeurHL';

/** Прогнозы NeurHL: {'Хозяева|Гости': [{day:'yyyy-MM-dd' (дата по Северной Америке), p, pElo}]} */
function neurhlLoad_() {
  var r = UrlFetchApp.fetch(NEURHL_URL, { muteHttpExceptions: true });
  if (r.getResponseCode() !== 200) throw new Error('NeurHL: GitHub ответил кодом ' + r.getResponseCode());
  var rows = Utilities.parseCsv(r.getContentText()), head = rows[0] || [], out = {}, n = 0;
  var c = function (name) { return head.indexOf(name); };
  var cD = c('date'), cH = c('home'), cA = c('away'), cP = c('p_home_win'), cE = c('p_home_win_elo');
  if (cD < 0 || cH < 0 || cA < 0 || cP < 0) throw new Error('NeurHL: изменился формат файла (' + head.join(',') + ')');
  for (var i = 1; i < rows.length; i++) {
    var h = nhlRuAny_(rows[i][cH]), a = nhlRuAny_(rows[i][cA]), p = Number(rows[i][cP]), pe = cE >= 0 ? Number(rows[i][cE]) : NaN;
    if (!h || !a || !isFinite(p)) continue;
    (out[h + '|' + a] = out[h + '|' + a] || []).push({ day: String(rows[i][cD]).slice(0, 10), p: p, pElo: isFinite(pe) ? pe : null });
    n++;
  }
  out.__n = n;
  return out;
}

/** Обновить лист сравнения. Возвращает {compared, text}. */
function neurhlUpdate_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var nr = neurhlLoad_(), res = ss.getSheetByName(SHEET_RESULTS), prog = ss.getSheetByName('прогнозы');
  if (!res || !prog) throw new Error('нет листов «' + SHEET_RESULTS + '» / «прогнозы»');
  var key = function (d) { return d instanceof Date ? Utilities.formatDate(d, 'Europe/Moscow', 'yyyy-MM-dd') : String(d).slice(0, 10); };
  var dayDiff = function (a, b) { return Math.round((new Date(a + 'T12:00:00Z') - new Date(b + 'T12:00:00Z')) / 86400000); };
  // наши честные прогнозы: дата|хозяева|гости → вероятность хозяев
  var ours = {};
  if (prog.getLastRow() > 1) prog.getRange(2, 1, prog.getLastRow() - 1, COL_INTEGRITY).getValues().forEach(function (r) {
    if (String(r[COL_INTEGRITY - 1]).trim() !== 'да' || !r[0]) return;
    var p = Number(r[3]); if (!isFinite(p)) return;
    if (p > 1) p = p / 100;
    ours[key(r[0]) + '|' + String(r[1]).trim() + '|' + String(r[2]).trim()] = p;
  });
  var R = res.getDataRange().getValues(), hd = R[0], ci = function (n) { return hd.indexOf(n); };
  var cD = ci('Дата'), cS = ci('Статус'), cH = ci('Хозяева'), cA = ci('Гости'), cHG = ci('Г Хозяев'), cAG = ci('Г Гостей'), cW = ci('Победитель'), cOT = ci('ОТ/буллиты?');
  var rows = [], acc = { our: [], nn: [], elo: [] };
  for (var j = 1; j < R.length; j++) {
    var row = R[j];
    if (String(row[cS]).trim() !== 'Сыгран' || !String(row[cW]).trim()) continue;
    var h = String(row[cH]).trim(), a = String(row[cA]).trim(), d = key(row[cD]);
    var cand = (nr[h + '|' + a] || []).filter(function (x) { var k = dayDiff(d, x.day); return k === 0 || k === 1; })[0];   // МСК = та же дата или следующая
    if (!cand) continue;
    var y = winnerName_(row[cW]) === h ? 1 : 0, po = ours[d + '|' + h + '|' + a];   // «Каролина (в ОТ/буллитах)» — тоже победа хозяев
    var br = function (p) { return p === null || p === undefined ? '' : Math.round(Math.pow(p - y, 2) * 10000) / 10000; };
    rows.push([d.split('-').reverse().join('.'), h, a, row[cHG] + ':' + row[cAG] + (row[cOT] === true || /^(да|true)/i.test(String(row[cOT])) ? ' ОТ/Б' : ''),
      po === undefined ? 'нет (не честный)' : Math.round(po * 1000) / 10, Math.round(cand.p * 1000) / 10, cand.pElo === null ? '' : Math.round(cand.pElo * 1000) / 10,
      y ? 'хозяева' : 'гости', po === undefined ? '' : br(po), br(cand.p), br(cand.pElo)]);
    if (po !== undefined) { acc.our.push([po, y]); acc.nn.push([cand.p, y]); if (cand.pElo !== null) acc.elo.push([cand.pElo, y]); }
  }
  var stat = function (arr) {
    if (!arr.length) return { n: 0 };
    var b = 0, ll = 0, hit = 0;
    arr.forEach(function (x) { var p = Math.min(0.99, Math.max(0.01, x[0])); b += Math.pow(x[0] - x[1], 2); ll -= x[1] ? Math.log(p) : Math.log(1 - p); if ((x[0] >= 0.5) === (x[1] === 1)) hit++; });
    return { n: arr.length, brier: b / arr.length, ll: ll / arr.length, hit: hit / arr.length };
  };
  var S = { our: stat(acc.our), nn: stat(acc.nn), elo: stat(acc.elo) };
  var sh = ss.getSheetByName(NEURHL_SHEET) || ss.insertSheet(NEURHL_SHEET);
  sh.clear();
  var f = function (s, k, pct) { return s.n ? (pct ? Math.round(s[k] * 1000) / 10 + '%' : Math.round(s[k] * 10000) / 10000) : '—'; };
  sh.getRange(1, 1, 6, 5).setValues([
    ['Сравнение с NeurHL — на одних и тех же матчах, только наши честные прогнозы (сделаны до матча)', '', '', '', ''],
    ['Модель', 'Матчей', 'Brier (меньше — лучше; 0,25 = монетка)', 'Угадано', 'Logloss (меньше — лучше)'],
    ['Наша модель', S.our.n, f(S.our, 'brier'), f(S.our, 'hit', true), f(S.our, 'll')],
    ['NeurHL (нейросеть)', S.nn.n, f(S.nn, 'brier'), f(S.nn, 'hit', true), f(S.nn, 'll')],
    ['NeurHL — их Elo', S.elo.n, f(S.elo, 'brier'), f(S.elo, 'hit', true), f(S.elo, 'll')],
    ['Прогнозы NeurHL заморожены 25.09.2026, до начала сезона: это честная планка. Источник: github.com/ph05/neurhl (данные — только для некоммерческого использования, в канал не публикуем). ' +
     'Выводы — после 100+ матчей: на меньшем числе разница может быть случайной.', '', '', '', '']]);
  sh.getRange(1, 1).setFontWeight('bold'); sh.getRange(2, 1, 1, 5).setFontWeight('bold'); sh.getRange(6, 1).setFontColor('#666666');
  var head = ['Дата (МСК)', 'Хозяева', 'Гости', 'Счёт', 'Наш прогноз: хозяева, %', 'NeurHL: хозяева, %', 'NeurHL Elo: хозяева, %', 'Победили', 'Brier наш', 'Brier NeurHL', 'Brier NeurHL Elo'];
  sh.getRange(8, 1, 1, head.length).setValues([head]).setFontWeight('bold');
  if (rows.length) sh.getRange(9, 1, rows.length, head.length).setValues(rows.reverse());
  try { sh.setFrozenRows(8); sh.setColumnWidth(1, 200); } catch (e) {}
  var text = S.our.n ? 'сравнение с NeurHL: матчей ' + S.our.n + ', Brier наш ' + f(S.our, 'brier') + ' / NeurHL ' + f(S.nn, 'brier') + ' / их Elo ' + f(S.elo, 'brier')
    : 'сравнение с NeurHL: сыгранных матчей с честным прогнозом пока нет (прогнозов NeurHL загружено: ' + nr.__n + ')';
  return { compared: S.our.n, text: text, stats: S, loaded: nr.__n };
}

/** Кнопка: обновить сравнение и открыть лист. */
function neurhlNow_() {
  try {
    var r = neurhlUpdate_(SpreadsheetApp.getActive());
    sheetOpen_(NEURHL_SHEET);
    uiAlert_('🆚 ' + r.text.charAt(0).toUpperCase() + r.text.slice(1) + '.\n\nBrier — средняя ошибка вероятности: меньше — лучше, 0,25 — как подбрасывать монетку. ' +
      'Сравниваются только наши честные прогнозы (сделаны до матча) на тех же матчах. Выводы — после 100+ матчей.');
  } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}

/* История статистики НХЛ: раз в день снимок по каждой команде (скрытый лист).
 * Нужна для ЧЕСТНОЙ проверки «улучшает ли xG% / вратарь прогноз»: берём то, что было известно накануне матча. */
var NHL_STATS_LOG_SHEET = 'Статистика_НХЛ_история';
function nhlStatsLog_(ss, rows, mpSeason) {
  var sh = ss.getSheetByName(NHL_STATS_LOG_SHEET);
  if (!sh) {
    sh = ss.insertSheet(NHL_STATS_LOG_SHEET);
    sh.getRange(1, 1, 1, 14).setValues([['Дата (МСК)', 'Команда', 'Игры', 'Очки', 'Большинство, %', 'Меньшинство, %', 'xG% 5×5', 'Corsi% 5×5', 'xG за игру', 'xG против',
      'Основной вратарь', 'Sv%', 'GSAx', 'Сезон MoneyPuck']]).setFontWeight('bold');
    try { sh.hideSheet(); } catch (e) {}
  }
  var day = Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM-dd'), last = sh.getLastRow();
  if (last > 1 && String(sh.getRange(last, 1).getValue()).replace(/^'/, '') === day) return 0;    // сегодня уже записано
  var out = rows.map(function (r) { return ["'" + day, r[0], r[1], r[2], r[7], r[8], r[11], r[12], r[13], r[14], r[15], r[17], r[18], mpSeason || '']; });
  sh.getRange(last + 1, 1, out.length, 14).setValues(out);
  return out.length;
}

/* ═══════════════ 🎯 Стартовый рейтинг НХЛ: пересчёт перед сезоном ═══════════════
 * Сейчас стартовый рейтинг (лист «Справочник команд», колонка C) взят из прошлого сезона как есть: разброс
 * слишком большой (18…97), а смены составов не учтены. На первых матчах наши шансы расходятся с букмекерами
 * в среднем на ~18 п.п. (Торонто — Монреаль: у нас 26% у хозяев, у букмекеров 51%).
 * Лист «Стартовый_рейтинг» считает два варианта и сравнивает каждый с линией букмекеров на ближайшие матчи:
 *   A — 1/3 наш рейтинг + 2/3 NeurHL (их прогнозы на весь сезон переведены в нашу шкалу 1–100);
 *   B — без NeurHL: наш рейтинг, наполовину подтянутый к среднему 50 (так делают Elo-модели между сезонами).
 * Применяет только кнопка (с подтверждением), «Вернуть прежний» — откат. Elo пересчитывается сразу. */
var NHL_START_SHEET = 'Стартовый_рейтинг';
var NHL_START_BACKUP = 'NHL_START_BACKUP';
var NHL_START_NN_SHARE = 2 / 3;       // вариант A: доля NeurHL
var NHL_START_REGRESS = 0.5;          // вариант B: насколько подтянуть к среднему

/** Прогнозы NeurHL на весь сезон списком: [{h, a, p}] */
function nhlStartNeurhlGames_() {
  var r = UrlFetchApp.fetch(NEURHL_URL, { muteHttpExceptions: true });
  if (r.getResponseCode() !== 200) throw new Error('NeurHL: GitHub ответил кодом ' + r.getResponseCode());
  var rows = Utilities.parseCsv(r.getContentText()), head = rows[0] || [], out = [];
  var cH = head.indexOf('home'), cA = head.indexOf('away'), cP = head.indexOf('p_home_win');
  if (cH < 0 || cA < 0 || cP < 0) throw new Error('NeurHL: изменился формат файла');
  for (var i = 1; i < rows.length; i++) {
    var h = nhlRuAny_(rows[i][cH]), a = nhlRuAny_(rows[i][cA]), p = Number(rows[i][cP]);
    if (h && a && isFinite(p) && p > 0 && p < 1) out.push({ h: h, a: a, p: p });
  }
  return out;
}

/** Рейтинги в нашей шкале, при которых наша формула шансов (рейтинг + дом. бонус, шкала scale) ближе всего к прогнозам games. */
function nhlStartFit_(games, teams, scale) {
  var r = {}, k = Math.LN10 / scale, home = 6;
  teams.forEach(function (t) { r[t] = 50; });
  for (var it = 0; it < 300; it++) {
    var g = {}, hs = {}, gH = 0, hH = 0;
    teams.forEach(function (t) { g[t] = 0; hs[t] = 1e-9; });
    games.forEach(function (x) {
      if (!(x.h in r) || !(x.a in r)) return;
      var q = 1 / (1 + Math.exp(-k * (r[x.h] - r[x.a] + home))), d = (q - x.p) * k, w = q * (1 - q) * k * k;
      g[x.h] += d; g[x.a] -= d; hs[x.h] += w; hs[x.a] += w; gH += d; hH += w;
    });
    var mv = 0;
    teams.forEach(function (t) { var s = g[t] / hs[t] * 0.8; r[t] -= s; mv = Math.max(mv, Math.abs(s)); });
    home -= gH / (hH + 1e-9) * 0.8;
    var mean = teams.reduce(function (s, t) { return s + r[t]; }, 0) / teams.length;
    teams.forEach(function (t) { r[t] += 50 - mean; });
    if (mv < 1e-4) break;
  }
  return { r: r, home: home };
}

/** Линия букмекеров на ближайшие матчи (победа с ОТ, без маржи): [{h, a, p, day}] */
function nhlStartMarket_(ss) {
  var sh = ss.getSheetByName(SHEET_ODDS_LOG);
  if (!sh || sh.getLastRow() < 2) return [];
  var v = sh.getDataRange().getValues(), hd = v[0], c = function (n) { return hd.indexOf(n); };
  var cH = c('Хозяева'), cA = c('Гости'), c1 = c('Кэф П1 (с ОТ)'), c2 = c('Кэф П2 (с ОТ)'), cS = c('Статус'), cD = c('День матча');
  if (cH < 0 || cA < 0 || c1 < 0 || c2 < 0) return [];
  var today = agentMskDay_(), last = {};
  for (var i = 1; i < v.length; i++) {
    var o1 = Number(v[i][c1]), o2 = Number(v[i][c2]), d = v[i][cD] instanceof Date ? agentMskDay_(v[i][cD]) : String(v[i][cD] || '').slice(0, 10);
    if (!(o1 > 1 && o2 > 1) || (cS >= 0 && String(v[i][cS]).trim() !== 'линия') || (d && d < today)) continue;
    last[d + '|' + v[i][cH] + '|' + v[i][cA]] = { h: String(v[i][cH]).trim(), a: String(v[i][cA]).trim(), day: d, p: (1 / o1) / (1 / o1 + 1 / o2) };   // последняя запись — свежая
  }
  return Object.keys(last).map(function (k) { return last[k]; });
}

/** Считает варианты и пишет лист. {teams, cur, nn, A, B, gap:{cur,A,B}, n} */
function nhlStartBuild_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var start = preseasonStartRatings_(ss), teams = Object.keys(start);
  if (teams.length < 20) throw new Error('в «' + SHEET_TEAMS + '» не найден стартовый рейтинг команд');
  var prog = ss.getSheetByName('прогнозы');
  var homeBase = prog ? Number(prog.getRange('M2').getValue()) : HOME_BASE_ADVANTAGE, scale = prog ? Number(prog.getRange('M3').getValue()) : 90;
  if (!(homeBase > 0)) homeBase = HOME_BASE_ADVANTAGE;
  if (!(scale > 0)) scale = 90;
  var bak = null; try { bak = JSON.parse(agentProps_().getProperty(NHL_START_BACKUP) || 'null'); } catch (e) { bak = null; }
  var base = {};                                                  // от чего считаем: прежний рейтинг, если уже применяли
  teams.forEach(function (t) { base[t] = bak && bak[t] !== undefined ? Number(bak[t]) : start[t].val; });
  var fit = nhlStartFit_(nhlStartNeurhlGames_(), teams, scale), nn = fit.r;
  var cl = function (x) { return Math.max(1, Math.min(100, Math.round(x))); };
  var A = {}, B = {};
  teams.forEach(function (t) {
    A[t] = cl((1 - NHL_START_NN_SHARE) * base[t] + NHL_START_NN_SHARE * nn[t]);
    B[t] = cl(50 + (1 - NHL_START_REGRESS) * (base[t] - 50));
  });
  var cur = {}; teams.forEach(function (t) { cur[t] = start[t].val; });
  var mk = nhlStartMarket_(ss).filter(function (m) { return m.h in cur && m.a in cur; });
  var prob = function (R, m) { return 1 / (1 + Math.pow(10, -(R[m.h] - R[m.a] + homeBase) / scale)); };
  var gap = function (R) { return mk.length ? mk.reduce(function (s, m) { return s + Math.abs(prob(R, m) - m.p); }, 0) / mk.length * 100 : null; };
  var res = { teams: teams, base: base, cur: cur, nn: nn, A: A, B: B, n: mk.length, gap: { cur: gap(cur), A: gap(A), B: gap(B), base: gap(base) }, market: mk, prob: prob };

  var sh = ss.getSheetByName(NHL_START_SHEET) || ss.insertSheet(NHL_START_SHEET);
  sh.clear();
  var f1 = function (x) { return x === null ? '—' : Math.round(x * 10) / 10; };
  var sg = function (x) { return x > 0 ? '+' + x : String(x); };
  var rows = [
    ['🎯 Стартовый рейтинг НХЛ — варианты перед сезоном', '', '', '', '', '', ''],
    ['Обновлено ' + Utilities.formatDate(new Date(), 'Europe/Moscow', 'dd.MM.yyyy HH:mm') + ' МСК. Применить — меню «НХЛ-парсер» → «🎯 Стартовый рейтинг». Elo пересчитается сразу, откат — «Вернуть прежний».', '', '', '', '', '', ''],
    ['A — 1/3 наш + 2/3 NeurHL.  B — без NeurHL: наш, наполовину к среднему 50.', '', '', '', '', '', ''],
    ['', '', '', '', '', '', ''],
    ['Расхождение с букмекерами (п.п., в среднем по ' + mk.length + ' ближайшим матчам)', 'Сейчас', 'Вариант A', 'Вариант B', '', '', ''],
    ['', f1(res.gap.cur), f1(res.gap.A), f1(res.gap.B), '', '', ''],
    ['', '', '', '', '', '', ''],
    ['Команда', 'Сейчас', 'NeurHL в нашей шкале', 'Вариант A', 'Изменение A', 'Вариант B', 'Изменение B']
  ];
  var head = rows.length;
  teams.slice().sort(function (x, y) { return A[y] - A[x]; }).forEach(function (t) {
    rows.push([t, cur[t], Math.round(nn[t] * 10) / 10, A[t], sg(A[t] - cur[t]), B[t], sg(B[t] - cur[t])]);
  });
  if (mk.length) {
    rows.push(['', '', '', '', '', '', ''], ['Ближайшие матчи: шансы хозяев, %', 'Сейчас', 'Вариант A', 'Вариант B', 'Букмекеры', '', '']);
    mk.forEach(function (m) { rows.push([m.day.split('-').reverse().join('.') + '  ' + m.h + ' — ' + m.a, Math.round(prob(cur, m) * 100), Math.round(prob(A, m) * 100), Math.round(prob(B, m) * 100), Math.round(m.p * 100), '', '']); });
  }
  sh.getRange(1, 1, rows.length, 7).setValues(rows);
  sh.getRange(1, 1).setFontWeight('bold').setFontSize(13);
  [5, head].forEach(function (r) { sh.getRange(r, 1, 1, 7).setFontWeight('bold').setBackground('#e8eaed'); });
  if (mk.length) sh.getRange(head + teams.length + 2, 1, 1, 7).setFontWeight('bold').setBackground('#e8eaed');
  try { sh.setColumnWidth(1, 330); sh.setFrozenRows(0); } catch (e2) {}
  return res;
}

function nhlStartBuildNow_() {
  try {
    var r = nhlStartBuild_(SpreadsheetApp.getActive());
    sheetOpen_(NHL_START_SHEET);
    var f = function (x) { return x === null ? '—' : Math.round(x) + ' п.п.'; };
    uiAlert_('🎯 Варианты стартового рейтинга посчитаны — лист «' + NHL_START_SHEET + '».\n\n' +
      (r.n ? 'Расхождение с букмекерами по ' + r.n + ' ближайшим матчам:\n• сейчас — ' + f(r.gap.cur) + '\n• вариант A (с NeurHL) — ' + f(r.gap.A) + '\n• вариант B (без NeurHL) — ' + f(r.gap.B) + '\n\n'
             : 'Линии букмекеров на ближайшие матчи пока нет — сравнить не с чем.\n\n') +
      'Применить: «НХЛ-парсер» → «🎯 Стартовый рейтинг» → «Применить вариант A» или «B».');
  } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}

function nhlStartApply_(which) {
  var ss = SpreadsheetApp.getActive(), r = nhlStartBuild_(ss), target = r[which], teamsSh = ss.getSheetByName(SHEET_TEAMS);
  var start = preseasonStartRatings_(ss), ch = [];
  r.teams.forEach(function (t) { if (start[t] && target[t] !== start[t].val) ch.push({ team: t, row: start[t].row, from: start[t].val, to: target[t] }); });
  if (!ch.length) { uiAlert_('Изменений нет: стартовый рейтинг уже совпадает с вариантом ' + which + '.'); return { applied: 0 }; }
  var ui = null; try { ui = SpreadsheetApp.getUi(); } catch (e) { ui = null; }
  var name = which === 'A' ? 'A (1/3 наш + 2/3 NeurHL)' : 'B (без NeurHL, наш наполовину к среднему)';
  var text = 'Применить вариант ' + name + '? Изменится стартовый рейтинг у ' + ch.length + ' команд:\n\n' +
    ch.slice().sort(function (x, y) { return Math.abs(y.to - y.from) - Math.abs(x.to - x.from); }).slice(0, 12).map(function (c) { return c.team + ': ' + c.from + ' → ' + c.to; }).join('\n') +
    (ch.length > 12 ? '\n…' : '') +
    (r.n ? '\n\nРасхождение с букмекерами: было ' + Math.round(r.gap.cur) + ' п.п., станет ' + Math.round(r.gap[which]) + ' п.п.' : '') +
    '\n\nElo пересчитается с начала сезона. Вернуть — «Вернуть прежний стартовый рейтинг».';
  if (ui && ui.alert(text, ui.ButtonSet.YES_NO) !== ui.Button.YES) return { applied: 0, canceled: true };
  var bak = null; try { bak = JSON.parse(agentProps_().getProperty(NHL_START_BACKUP) || 'null'); } catch (e2) { bak = null; }
  if (!bak) { bak = {}; r.teams.forEach(function (t) { bak[t] = start[t].val; }); agentProps_().setProperty(NHL_START_BACKUP, JSON.stringify(bak)); }
  ch.forEach(function (c) { teamsSh.getRange(c.row, 3).setValue(c.to); });
  var msg = ''; try { computeAndWriteElo_(true); msg = ' Elo пересчитан, шансы в «прогнозах» обновились.'; } catch (e3) { msg = ' Elo не пересчитался: ' + e3.message + ' — нажмите «Обновить всё».'; }
  try { nhlStartBuild_(ss); } catch (e4) {}
  uiAlert_('Готово: вариант ' + which + ' применён, изменено ' + ch.length + ' команд.' + msg);
  return { applied: ch.length, changes: ch };
}
function nhlStartApplyA_() { try { nhlStartApply_('A'); } catch (e) { uiAlert_('Не получилось: ' + e.message); } }
function nhlStartApplyB_() { try { nhlStartApply_('B'); } catch (e) { uiAlert_('Не получилось: ' + e.message); } }

function nhlStartRevert_() {
  var ss = SpreadsheetApp.getActive(), bak = null, teamsSh = ss.getSheetByName(SHEET_TEAMS);
  try { bak = JSON.parse(agentProps_().getProperty(NHL_START_BACKUP) || 'null'); } catch (e) { bak = null; }
  if (!bak || !teamsSh) { uiAlert_('Возвращать нечего: стартовый рейтинг не менялся.'); return { reverted: 0 }; }
  var start = preseasonStartRatings_(ss), n = 0;
  Object.keys(bak).forEach(function (t) { if (start[t] && start[t].val !== Number(bak[t])) { teamsSh.getRange(start[t].row, 3).setValue(Number(bak[t])); n++; } });
  agentProps_().deleteProperty(NHL_START_BACKUP);
  try { computeAndWriteElo_(true); } catch (e2) {}
  uiAlert_('Стартовый рейтинг возвращён к прежнему у ' + n + ' команд, Elo пересчитан.');
  return { reverted: n };
}

/* 🔎 Разведчик в НХЛ: матчи ночью по МСК, новости выходят днём и вечером — сбор без «тихих часов». */
var SCOUT_QUIET_HOURS = [];

/* 📊 «Сила команд» в НХЛ — в понедельник вечером (17:00 МСК), перед ночью матчей. Каналов клубов КХЛ здесь нет. */
var EXPERT_CLUBS = [];

/* ══════════ 🇷🇺 «Наши в НХЛ» — в пост «Итоги ночи» ══════════
 * Кто россиянин — по составам команд НХЛ (страна рождения RUS), раз в неделю в скрытый лист «Россияне_НХЛ».
 * Фамилию по-русски можно поправить на этом листе — при обновлении ваша правка сохранится.
 * Очки и сейвы — из протоколов ночи (лист «Составы_матчей»). */
var NHL_RU_SHEET = 'Россияне_НХЛ';
var NHL_RU_HEADER = ['ID', 'Игрок (англ.)', 'Фамилия по-русски (можно поправить)', 'Команда', 'Позиция', 'Обновлено'];
var NHL_RU_FIX = { 'Shesterkin': 'Шестёркин', 'Sergachev': 'Сергачёв', 'Kuzmenko': 'Кузьменко', 'Fedotov': 'Федотов', 'Semyonov': 'Семёнов',
  'Yegorov': 'Егоров', 'Kovalyov': 'Ковалёв', 'Korolyov': 'Королёв', 'Zhukov': 'Жуков' };

/** Английская фамилия → русская (правила для русских фамилий + исключения). */
function nhlRuSurname_(en) {
  en = String(en || '').trim();
  if (NHL_RU_FIX[en]) return NHL_RU_FIX[en];
  var s = en.toLowerCase(), out = '';
  var rules = [['shch', 'щ'], ['sky', 'ский'], ['kh', 'х'], ['zh', 'ж'], ['ch', 'ч'], ['sh', 'ш'], ['ts', 'ц'], ['yu', 'ю'], ['ya', 'я'], ['yo', 'ё'], ['ye', 'е'],
    ['iy', 'ий'], ['yy', 'ый'], ['ai', 'ай'], ['ei', 'ей'], ['oi', 'ой'], ['ui', 'уй']];
  var one = { a: 'а', b: 'б', v: 'в', g: 'г', d: 'д', e: 'е', z: 'з', i: 'и', k: 'к', l: 'л', m: 'м', n: 'н', o: 'о', p: 'п', r: 'р', s: 'с', t: 'т', u: 'у', f: 'ф', h: 'х', c: 'к', w: 'в', x: 'кс', q: 'к', j: 'дж' };
  for (var i = 0; i < s.length;) {
    var hit = null;
    for (var k = 0; k < rules.length; k++) if (s.substr(i, rules[k][0].length) === rules[k][0]) { hit = rules[k]; break; }
    // «ai/ei/oi» перед гласной — не дифтонг
    if (hit && /^(ai|ei|oi|ui)$/.test(hit[0]) && /[aeiouy]/.test(s.charAt(i + 2))) hit = null;
    if (hit) { out += hit[1]; i += hit[0].length; continue; }
    var ch = s.charAt(i);
    if (ch === 'y') out += /[aeiou]/.test(s.charAt(i - 1)) ? 'й' : 'ы';
    else out += one[ch] !== undefined ? one[ch] : ch;
    i++;
  }
  return out.charAt(0).toUpperCase() + out.slice(1);
}

function nhlRuKey_(first, last) { return String(first || '').trim().charAt(0).toLowerCase() + '|' + String(last || '').trim().toLowerCase(); }
/** «K. Kaprizov» / «Kirill Kaprizov» → 'k|kaprizov' */
function nhlRuKeyFromName_(name) {
  var parts = String(name || '').replace(/\s+/g, ' ').trim().split(' ');
  if (parts.length < 2) return '';
  return nhlRuKey_(parts[0], parts.slice(1).join(' '));
}

/** Составы всех команд → лист россиян. {count} */
function nhlRussiansRefresh_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(NHL_RU_SHEET);
  if (!sh) { sh = ss.insertSheet(NHL_RU_SHEET); sh.getRange(1, 1, 1, NHL_RU_HEADER.length).setValues([NHL_RU_HEADER]).setFontWeight('bold'); try { sh.hideSheet(); } catch (e) {} }
  var mine = {};   // ваши правки фамилий
  if (sh.getLastRow() >= 2) sh.getRange(2, 1, sh.getLastRow() - 1, 3).getValues().forEach(function (r) { if (r[0]) mine[String(r[0])] = { ru: String(r[2] || ''), auto: nhlRuSurname_(String(r[1]).split(' ').slice(1).join(' ')) }; });
  var teams = NHL_TEAMS.map(function (t) { return t[0]; });
  var resps = UrlFetchApp.fetchAll(teams.map(function (a) { return { url: NHL_API + 'roster/' + a + '/current', muteHttpExceptions: true }; }));
  var rows = [], stamp = mskNow_('dd.MM.yyyy'), ok = 0;
  teams.forEach(function (a, i) {
    var j = null; try { if (resps[i].getResponseCode() === 200) j = JSON.parse(resps[i].getContentText()); } catch (e) { j = null; }
    if (!j) return; ok++;
    [['forwards', 'F'], ['defensemen', 'D'], ['goalies', 'G']].forEach(function (g) {
      (j[g[0]] || []).forEach(function (pl) {
        if (String(pl.birthCountry || '').toUpperCase() !== 'RUS') return;
        var first = pl.firstName && (pl.firstName.default || pl.firstName), last = pl.lastName && (pl.lastName.default || pl.lastName), id = String(pl.id || '');
        var auto = nhlRuSurname_(last), was = mine[id];
        var ru = was && was.ru && was.ru !== was.auto ? was.ru : auto;   // ручная правка сильнее
        rows.push([id, first + ' ' + last, ru, nhlRu_(a) || a, g[1], stamp]);
      });
    });
  });
  if (ok < 20) throw new Error('составы НХЛ не загрузились (' + ok + ' из ' + teams.length + ')');
  if (sh.getLastRow() >= 2) sh.getRange(2, 1, sh.getLastRow() - 1, NHL_RU_HEADER.length).clearContent();
  if (rows.length) sh.getRange(2, 1, rows.length, NHL_RU_HEADER.length).setValues(rows);
  return { count: rows.length };
}

/** Блок «Наши» для итогов ночи ('' — если данных нет). */
function nhlOursText_(ss, dayKey, matches) {
  var ru = ss.getSheetByName(NHL_RU_SHEET);
  if (!ru || ru.getLastRow() < 2) { try { nhlRussiansRefresh_(ss); ru = ss.getSheetByName(NHL_RU_SHEET); } catch (e) { return ''; } }
  if (!ru || ru.getLastRow() < 2) return '';
  var who = {};
  ru.getRange(2, 1, ru.getLastRow() - 1, 4).getValues().forEach(function (r) {
    var nm = String(r[1] || '').split(' '); if (nm.length < 2) return;
    who[String(r[3]) + '#' + nhlRuKey_(nm[0], nm.slice(1).join(' '))] = String(r[2] || '').trim();
  });
  var lu = ss.getSheetByName(LINEUP_SHEET);
  if (!lu || lu.getLastRow() < 2) return '';
  var games = {}; matches.forEach(function (m) { games[m.home + '|' + m.away] = true; });
  var days = [dayKey, addDaysKey_(dayKey, -1)], sk = [], gk = [], zero = [];
  lu.getRange(2, 1, lu.getLastRow() - 1, 12).getValues().forEach(function (r) {
    var d = signalDay_(r[0]);
    if (days.indexOf(d) < 0 || !games[String(r[1]).trim() + '|' + String(r[2]).trim()]) return;
    var team = String(r[3]).trim(), name = who[team + '#' + nhlRuKeyFromName_(r[6])];
    if (!name) return;
    if (String(r[4]) === 'G') {
      var sa = Number(r[10]), sv = Number(r[11]);
      if (sa > 0) gk.push({ t: name + ' (' + team + ') — ' + sv + ' ' + ruPlural_(sv, 'сейв', 'сейва', 'сейвов') + ' из ' + sa, v: sv / sa });
    } else {
      var g = Number(r[8]) || 0, a = Number(r[9]) || 0;
      if (g + a > 0) sk.push({ t: name + ' (' + team + ') — ' + g + '+' + a, v: g + a + g / 10 });
      else zero.push(name);
    }
  });
  if (!sk.length && !gk.length) return '';
  sk.sort(function (x, y) { return y.v - x.v; });
  var lines = sk.slice(0, 12).map(function (x) { return x.t; }).concat(gk.map(function (x) { return '🧤 ' + x.t; }));
  return '🇷🇺 <b>Наши</b>\n' + escHtml_(lines.join('\n')) + (zero.length ? '\n<i>Без очков: ' + escHtml_(zero.slice(0, 10).join(', ')) + '</i>' : '');
}

/* ==========================================================================
 * 🖼 ПОСТЕР «ИТОГИ ДНЯ» → ВАМ В TELEGRAM
 *  Картинку рисует GitHub Actions (render/itogi_job.py, формат «Ячейки»: логотипы во всю ячейку, проигравший — серым),
 *  таблица только передаёт счёт: событие repository_dispatch «itogi» в репозиторий ITOGI_REPO.
 *  Нужно один раз: свойство GITHUB_TOKEN (меню → «🔑 Подключить GitHub для постеров») и секрет TG_BOT_TOKEN
 *  в настройках репозитория. Без токена ничего не отправляется и ничего не ломается.
 *  КХЛ — сразу после последнего матча дня (LIVE видит финальный счёт у всех); НХЛ — в 10:00 МСК, когда ночь доиграна.
 *  Постер приходит только вам (TG_ADMIN_ID); в канал — сами, когда посмотрите.
 * ==========================================================================*/
var ITOGI_REPO = 'sevasonyshahmatov-collab/-kaper-jarvis-bot';
var ITOGI_LEAGUE = 'NHL';
var ITOGI_PROP = 'ITOGI_POSTER_';            // + день (yyyy-MM-dd): постер за этот день уже заказан

function itogiGithub_(method, path, body) {
  var tok = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!tok) return null;
  var o = { method: method, muteHttpExceptions: true, contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + tok, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' } };
  if (body) o.payload = JSON.stringify(body);
  return UrlFetchApp.fetch('https://api.github.com' + path, o);
}

/** Заказать постер: {sent} или {skipped: причина}. kind: 'itogi' (items: [{home, away, sh, sa, mark}]) или 'matchi'. */
function itogiDispatch_(league, dayKey, items, kind, caption) {
  kind = kind || 'itogi';
  var p = PropertiesService.getScriptProperties(), chat = p.getProperty('TG_ADMIN_ID');
  if (!p.getProperty('GITHUB_TOKEN')) return { skipped: 'GitHub не подключён' };
  if (!chat) return { skipped: 'не указан ваш Telegram ID (TG_ADMIN_ID)' };
  if (!items || !items.length) return { skipped: 'нет сыгранных матчей' };
  var cp = { kind: kind, league: league, day: dayKey, date_title: ruDayTitle_(dayKey).toLowerCase(), chat: String(chat), items: items };
  if (caption) cp.caption = caption;
  var r = itogiGithub_('post', '/repos/' + ITOGI_REPO + '/dispatches', { event_type: kind, client_payload: cp });
  if (r.getResponseCode() !== 204) throw new Error('GitHub ответил ' + r.getResponseCode() + ': ' + r.getContentText().slice(0, 200));
  var pref = kind === 'matchi' ? MATCHI_PROP : ITOGI_PROP, old = addDaysKey_(dayKey, -10);
  p.setProperty(pref + dayKey, mskNow_());
  p.getKeys().forEach(function (k) { if (k.indexOf(pref) === 0 && k.slice(pref.length) < old) p.deleteProperty(k); });
  return { sent: items.length };
}

/** Сыгранные матчи дня с листа результатов: [{home, away, sh, sa, mark}] */
function itogiItemsFromResults_(ss, dayKey) {
  var sh = ss.getSheetByName(SHEET_RESULTS), out = [];
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, 7).getValues().forEach(function (r) {
    if (!(r[0] instanceof Date) || sheetDayKey_(r[0]) !== dayKey || String(r[1]).trim() !== 'Сыгран') return;
    if (r[4] === '' || r[5] === '' || !isFinite(Number(r[4])) || !isFinite(Number(r[5]))) return;
    var ot = r[6] === true || /^(да|true|от|б)/i.test(String(r[6]).trim());
    out.push({ home: String(r[2]).trim(), away: String(r[3]).trim(), sh: Number(r[4]), sa: Number(r[5]), mark: ot ? 'ОТ/Б' : '' });
  });
  return out;
}

/** Последний день (не позже сегодняшнего по МСК), где есть сыгранные матчи. */
function itogiLastDay_(ss) {
  var sh = ss.getSheetByName(SHEET_RESULTS), today = mskNow_('yyyy-MM-dd'), best = '';
  if (!sh || sh.getLastRow() < 2) return '';
  sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues().forEach(function (r) {
    if (!(r[0] instanceof Date) || String(r[1]).trim() !== 'Сыгран') return;
    var k = sheetDayKey_(r[0]); if (k <= today && k > best) best = k;
  });
  return best;
}

/** Кнопка: постер за последний игровой день — вам в Telegram (через 1–2 минуты). */
function itogiPosterNow_() {
  var ss = SpreadsheetApp.getActive(), day = itogiLastDay_(ss);
  if (!day) { uiAlert_('На листе «' + SHEET_RESULTS + '» нет сыгранных матчей.'); return; }
  var items = itogiItemsFromResults_(ss, day);
  try {
    var r = itogiDispatch_(ITOGI_LEAGUE, day, items);
    if (r.skipped) { uiAlert_('Постер не заказан: ' + r.skipped + '.' + (/GitHub/.test(r.skipped) ? ' Подключите: «🔑 Подключить GitHub для постеров».' : '')); return; }
    uiAlert_('Постер «Итоги дня» за ' + day.split('-').reverse().join('.') + ' (матчей: ' + r.sent + ') рисуется — придёт вам в Telegram через 1–2 минуты.');
  } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}

/** Кнопка: сохранить токен GitHub и проверить доступ к репозиторию. */
function itogiSetToken_() {
  var ui = SpreadsheetApp.getUi();
  var r = ui.prompt('🔑 GitHub для постеров', 'Токен GitHub (fine-grained, только репозиторий ' + ITOGI_REPO + ', права Contents: Read and write).\n' +
    'Он нужен, чтобы таблица могла попросить GitHub нарисовать постер. Пусто — отключить.', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var p = PropertiesService.getScriptProperties(), tok = String(r.getResponseText() || '').trim();
  if (!tok) { p.deleteProperty('GITHUB_TOKEN'); uiAlert_('GitHub отключён: постеры «Итоги дня» не заказываются.'); return; }
  p.setProperty('GITHUB_TOKEN', tok);
  var t = itogiGithub_('get', '/repos/' + ITOGI_REPO);
  var ok = t && t.getResponseCode() === 200, push = false;
  try { push = ok && JSON.parse(t.getContentText()).permissions.push === true; } catch (e) { push = false; }
  if (!ok) { p.deleteProperty('GITHUB_TOKEN'); uiAlert_('Токен не подошёл: GitHub ответил ' + (t ? t.getResponseCode() : '—') + '. Проверьте, что выбран репозиторий ' + ITOGI_REPO + '.'); return; }
  uiAlert_('GitHub подключён' + (push ? '.' : ', но у токена нет права записи (Contents: Read and write) — без него GitHub не примет заказ постера.') +
    '\nПроверьте: «🖼 Постер «Итоги дня» → мне» — картинка придёт через 1–2 минуты.');
}

/** НХЛ: ночь доиграна — заказать постер (один раз за день; в канал пост «итоги ночи» идёт отдельно). */
function itogiAutoNhl_(day) {
  var p = PropertiesService.getScriptProperties();
  if (p.getProperty(ITOGI_PROP + day)) return;
  try {
    var f = nhlDayForecasts_(SpreadsheetApp.getActive(), day), played = f.filter(function (x) { return x.played; });
    if (!played.length) return;
    var r = itogiDispatch_('NHL', day, played.map(function (x) { return { home: x.home, away: x.away, sh: Number(x.hg), sa: Number(x.ag), mark: x.ot ? 'ОТ/Б' : '' }; }));
    if (r.sent) autoMark_('nhlMorningAuto_', true, 'постер «Итоги ночи» заказан (матчей ' + r.sent + (played.length < f.length ? ' из ' + f.length : '') + ')');
  } catch (e) {
    p.setProperty(ITOGI_PROP + day, 'ошибка');
    autoNotifyAdmin_('⚠ НХЛ: постер «Итоги ночи» не заказан: ' + e.message + '. Можно вручную: меню «📣 НХЛ · ТГ группа» → «🖼 Постер «Итоги дня» → мне».');
  }
}

/* ==========================================================================
 * 🖼 ПОСТЕР «МАТЧИ ДНЯ» → ВАМ В TELEGRAM
 *  Так же, как «Итоги дня»: рисует GitHub Actions (формат «Колонки»), таблица передаёт матчи, время и линию П1/Х/П2.
 *  Приходит вместе с карточками матчей (bannersAuto_): КХЛ — утром в день матчей, НХЛ — вечером перед ночью.
 *  Подпись — готовая для канала: «02:30 | 🛩️Филадельфия — Питтсбург🐧» по строке на матч и «Время московское.»;
 *  эмодзи клубов — лист «Эмодзи_клубов» (правьте как хотите; недостающие клубы допишутся сами).
 * ==========================================================================*/
var MATCHI_PROP = 'MATCHI_POSTER_';          // + день: постер «Матчи дня» за этот день уже заказан
var MATCHI_EMOJI_NHL_ = [['Анахайм', '🦆'], ['Бостон', '🐻'], ['Баффало', '🦬'], ['Калгари', '🔥'], ['Каролина', '🌀'],
  ['Чикаго', '🪶'], ['Колорадо', '⛰️'], ['Коламбус', '💣'], ['Даллас', '⭐'], ['Детройт', '🐙'], ['Эдмонтон', '🛢️'],
  ['Флорида', '🐆'], ['Лос-Анджелес', '👑'], ['Миннесота', '🌲'], ['Монреаль', '⚜️'], ['Нэшвилл', '🎸'], ['Нью-Джерси', '😈'],
  ['Айлендерс', '🟠'], ['Рейнджерс', '🗽'], ['Оттава', '🏛️'], ['Филадельфия', '🛩️'], ['Питтсбург', '🐧'], ['Сан-Хосе', '🦈'],
  ['Сиэтл', '🦑'], ['Сент-Луис', '🎵'], ['Тампа-Бэй', '⚡'], ['Торонто', '🍁'], ['Юта', '🦣'], ['Ванкувер', '🐋'],
  ['Вегас', '⚔️'], ['Вашингтон', '🦅'], ['Виннипег', '✈️']];

/** Эмодзи клубов с листа «Эмодзи_клубов»; клубы своей лиги, которых там нет, дописываются значениями по умолчанию. */
function matchiEmoji_(ss) {
  var def = ITOGI_LEAGUE === 'NHL' ? MATCHI_EMOJI_NHL_ : POST_EMOJI_DEFAULT, sh = ss.getSheetByName(POST_EMOJI_SHEET), out = {};
  if (!sh) {
    sh = ss.insertSheet(POST_EMOJI_SHEET);
    sh.getRange(1, 1, 1, 2).setValues([['Команда', 'Эмодзи']]).setFontWeight('bold');
    sh.setFrozenRows(1);
    sh.getRange(1, 4).setValue('Эмодзи клубов для подписей к постам. Меняйте на свои — следующий пост возьмёт новые.');
  }
  if (sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues().forEach(function (r) { if (r[0]) out[String(r[0]).trim()] = String(r[1] || '').trim(); });
  var miss = def.filter(function (d) { return !(d[0] in out); });
  if (miss.length) {
    sh.getRange(Math.max(sh.getLastRow(), 1) + 1, 1, miss.length, 2).setValues(miss);
    miss.forEach(function (d) { out[d[0]] = d[1]; });
  }
  return out;
}

/** Матчи дня для постера: [{home, away, time, odds: [П1, Х, П2] | null}] — по времени начала. */
function matchiItems_(ss, day) {
  return bannerData_(ss, day).map(function (b) { return { home: b.home, away: b.away, time: String(b.time || '').slice(0, 5), odds: b.odds || null }; });
}

/** Подпись для канала: «02:30 | 🛩️Филадельфия — Питтсбург🐧», … «Время московское.» */
function matchiCaption_(ss, items) {
  var emo = matchiEmoji_(ss);
  return items.map(function (it) {
    return (it.time ? it.time + ' | ' : '') + escHtml_((emo[it.home] || '') + it.home + ' — ' + it.away + (emo[it.away] || ''));
  }).join('\n') + '\n\nВремя московское.';
}

function matchiDispatch_(ss, day) {
  var items = matchiItems_(ss, day);
  if (!items.length) return { skipped: 'матчей нет' };
  return itogiDispatch_(ITOGI_LEAGUE, day, items, 'matchi', matchiCaption_(ss, items));
}

/** Вместе с карточками матчей: заказать постер «Матчи дня» (один раз за день). */
function matchiAuto_(day) {
  var p = PropertiesService.getScriptProperties();
  if (p.getProperty(MATCHI_PROP + day)) return;
  try {
    var r = matchiDispatch_(SpreadsheetApp.getActive(), day);
    if (r.sent) autoMark_('bannersAuto_', true, 'постер «Матчи дня» за ' + day + ' заказан (матчей ' + r.sent + ')');
  } catch (e) {
    p.setProperty(MATCHI_PROP + day, 'ошибка');
    autoNotifyAdmin_('⚠ ' + VIDEO_LEAGUE + ': постер «Матчи дня» не заказан: ' + e.message + '. Можно вручную: меню «📣 … · ТГ группа» → «🖼 Постер «Матчи дня» → мне».');
  }
}

/** Кнопка: постер на ближайший игровой день — вам в Telegram (через 1–2 минуты). */
function matchiPosterNow_() {
  var ss = SpreadsheetApp.getActive(), day = bannersDay_();
  for (var i = 0; i < 7 && !agentMatchesOfDay_(ss, day).length; i++) day = addDaysKey_(day, 1);
  try {
    var r = matchiDispatch_(ss, day);
    if (r.skipped) { uiAlert_('Постер не заказан: ' + r.skipped + '.' + (/GitHub/.test(r.skipped) ? ' Подключите: «🔑 Подключить GitHub для постеров».' : '')); return; }
    uiAlert_('Постер «Матчи дня» на ' + day.split('-').reverse().join('.') + ' (матчей: ' + r.sent + ') рисуется — придёт вам в Telegram через 1–2 минуты.');
  } catch (e) { uiAlert_('Не получилось: ' + e.message); }
}
