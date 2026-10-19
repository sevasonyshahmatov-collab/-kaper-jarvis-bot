/* ══════════════ 🎁 ДЕМО-ВЕРСИЯ ТАБЛИЦЫ (владелец 19.10) ══════════════
 * Отдельная Google-таблица «Таблица прогнозов КХЛ — демо» — кусочек этой таблицы для подписчиков:
 *  • только цифры: формул, кода и скрытых листов в демо нет (копируются значения и оформление нескольких листов);
 *  • у каждого листа — только верх (DEMO_SHEETS.rows), ниже строка «🔒 остальное — в полной версии»;
 *  • в «Прогнозах — кратко» у матчей без счёта прогноз и кэфы закрыты — открыты только сыгранные (видно, что зашло, а что нет);
 *  • «Джарвис» в демо не пишем (публичный текст) — заменяется на «модель»;
 *  • доступ — всем по ссылке, только просмотр; читателям запрещено скачивать, печатать и копировать (Drive: copyRequiresWriterPermission).
 * Запуск один раз: в редакторе скриптов выберите функцию demoCreate и нажмите «Выполнить» — создаст файл, откроет доступ по ссылке,
 * поставит ежедневное обновление (DEMO_HOUR) и пришлёт ссылку владельцу в Telegram (если в свойствах есть TG_OWNER_ID).
 * Дальше demoSync обновляет демо сам каждое утро; вручную — запустить demoSync. Удалить демо — demoRemove (файл в корзину, обновление снимается).
 * ==========================================================================*/
var DEMO_NAME = 'Таблица прогнозов КХЛ — демо';
var DEMO_HOUR = 8;                              // ежедневное обновление (время таблицы)
var DEMO_CHANNEL = 'https://t.me/jarvibet';
var DEMO_SHEETS = [                             // лист основной таблицы → сколько строк сверху показать
  { name: 'Прогнозы — кратко', rows: 60, lockFuture: true },
  { name: 'Что заходит', rows: 12 },
  { name: 'Таблица', rows: 14 },
  { name: 'Модель vs рынок', rows: 16 },
  { name: 'Точность', rows: 40 }
];
var DEMO_WORDS = [[/линии букмекера/g, 'линии рынка'], [/Джарвиса/g, 'модели'], [/Джарвису/g, 'модели'], [/Джарвисом/g, 'моделью'], [/Джарвис/g, 'Модель'],
                  [/JARVIS/g, 'ДЕМО'], [/Jarvis/g, 'Модель']];

function demoProps_() { return PropertiesService.getScriptProperties(); }

function demoText_(v) {
  if (typeof v !== 'string' || !v) return v;
  DEMO_WORDS.forEach(function (w) { v = v.replace(w[0], w[1]); });
  return v;
}

/** Создать демо (один раз), открыть по ссылке без копирования, поставить ежедневное обновление, прислать ссылку. */
function demoCreate() {
  var p = demoProps_(), id = p.getProperty('DEMO_ID'), demo = null;
  if (id) { try { demo = SpreadsheetApp.openById(id); } catch (e) { demo = null; } }
  if (!demo) {
    demo = SpreadsheetApp.create(DEMO_NAME);
    p.setProperty('DEMO_ID', demo.getId());
  }
  demoSync();
  var shared = '';
  try {
    DriveApp.getFileById(demo.getId()).setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    shared = demoNoCopy_(demo.getId()) ? 'открыта по ссылке, только просмотр, копирование отключено'
                                       : 'открыта по ссылке, только просмотр; копирование отключите вручную (⚙️ в «Настройках доступа»)';
  } catch (e) {                                                      // в проекте Google Cloud выключен Drive API
    shared = 'доступ НЕ открыт: включите Google Drive API в проекте Google Cloud скрипта и запустите demoCreate ещё раз ' +
             '(или откройте доступ вручную: «Настройки доступа» → «Все, у кого есть ссылка» → «Читатель», ⚙️ → снять галочку копирования)';
    Logger.log('Демо: ' + e);
  }
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'demoSync') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('demoSync').timeBased().everyDays(1).atHour(DEMO_HOUR).create();
  var url = demo.getUrl();
  var owner = p.getProperty('TG_OWNER_ID');
  if (owner && typeof tgRaw_ === 'function') {
    tgRaw_('sendMessage', { chat_id: owner, disable_web_page_preview: true,
      text: '🎁 Демо-таблица готова — ' + shared + ':\n' + url +
            '\n\nОбновляется сама каждый день в ' + DEMO_HOUR + ':00.' });
  }
  Logger.log('Демо: ' + url + ' — ' + shared);
  try { SpreadsheetApp.getUi().alert('Демо-таблица: ' + shared + '\n' + url); } catch (e) { /* запуск из редактора — без окна */ }
  return url;
}

/** Читателям нельзя скачивать, печатать и копировать (Drive API: copyRequiresWriterPermission). */
function demoNoCopy_(id) {
  var r = UrlFetchApp.fetch('https://www.googleapis.com/drive/v3/files/' + id + '?fields=copyRequiresWriterPermission', {
    method: 'patch', contentType: 'application/json', muteHttpExceptions: true,
    headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
    payload: JSON.stringify({ copyRequiresWriterPermission: true })
  });
  if (r.getResponseCode() !== 200) Logger.log('Демо: запрет копирования не поставился — ' + r.getContentText().slice(0, 300));
  return r.getResponseCode() === 200;
}

/** Обновить демо: листы из DEMO_SHEETS — значения и оформление, без формул; лист «О демо» первым. */
function demoSync() {
  var id = demoProps_().getProperty('DEMO_ID');
  if (!id) return;
  var src = SpreadsheetApp.getActive(), demo = SpreadsheetApp.openById(id);
  var keep = demo.insertSheet('_tmp_' + Date.now());               // в таблице всегда должен оставаться хотя бы один лист
  demo.getSheets().forEach(function (s) { if (s.getSheetId() !== keep.getSheetId()) demo.deleteSheet(s); });
  demoAbout_(demo);
  DEMO_SHEETS.forEach(function (c) {
    var s = src.getSheetByName(c.name);
    if (!s) return;
    try { demoCopySheet_(s, demo, c); } catch (e) { Logger.log('Демо: лист «' + c.name + '» не скопировался — ' + e); }
  });
  demo.deleteSheet(keep);
  demo.setActiveSheet(demo.getSheets()[0]);
  demoProps_().setProperty('DEMO_SYNCED', new Date().toISOString());
}

function demoCopySheet_(s, demo, c) {
  var t = s.copyTo(demo);
  t.setName(c.name);
  t.showSheet();
  var h = Math.min(s.getLastRow(), c.rows), w = s.getLastColumn();
  if (h < 1 || w < 1) return;
  var vals = s.getRange(1, 1, h, w).getValues().map(function (row) { return row.map(demoText_); });
  if (c.lockFuture) demoLockFuture_(vals);
  t.getRange(1, 1, t.getMaxRows(), t.getMaxColumns()).clearContent();   // формулы копии ссылались бы на чужие листы
  t.clearNotes();
  t.getRange(1, 1, h, w).setValues(vals);
  var fc = t.getFrozenColumns(), fr = t.getFrozenRows();
  if (fc) t.setFrozenColumns(0);                                     // объединения ниже (конструктор матча) иначе не дают резать лист
  if (t.getMaxRows() > h) {
    t.getRange(h + 1, 1, t.getMaxRows() - h, t.getMaxColumns()).breakApart();
    if (t.getMaxRows() > h + 1) t.deleteRows(h + 2, t.getMaxRows() - h - 1);
  }
  var lock = t.getRange(h + 1, 1, 1, w);
  try { lock.breakApart(); if (w > 1) lock.merge(); } catch (e) { lock = t.getRange(h + 1, 1); }
  lock.setValue('🔒 Остальное — в полной версии таблицы · прогнозы каждый день: ' + DEMO_CHANNEL)
      .setFontStyle('italic').setFontColor('#80868b').setBackground('#f1f3f4').setFontWeight('normal');
  if (fc) { try { t.setFrozenColumns(fc); } catch (e) { /* закреплять не обязательно */ } }
  if (fr > h) t.setFrozenRows(Math.min(fr, h));
  t.getProtections(SpreadsheetApp.ProtectionType.SHEET).forEach(function (p) { p.remove(); });
  t.getProtections(SpreadsheetApp.ProtectionType.RANGE).forEach(function (p) { p.remove(); });
}

/** «Прогнозы — кратко»: у матчей без счёта (ещё не сыграны) прогнозы и кэфы закрыты. Столбцы — как в renderBriefSheet_. */
function demoLockFuture_(vals) {
  var head = -1;
  for (var i = 0; i < vals.length; i++) if (String(vals[i][2]) === 'Матч') { head = i; break; }
  if (head < 0) return;
  for (var r = head + 1; r < vals.length; r++) {
    if (!vals[r][2] || String(vals[r][6]).trim()) continue;          // нет матча или уже есть счёт
    [3, 4, 5].forEach(function (j) { if (j < vals[r].length) vals[r][j] = '🔒 в полной версии'; });
  }
}

function demoAbout_(demo) {
  var a = demo.insertSheet('О демо', 0);
  var lines = [
    ['Таблица прогнозов КХЛ — демо-версия'],
    ['Кусочек настоящей таблицы: только цифры, без формул. Обновляется каждый день, последнее обновление — ' +
      Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'dd.MM.yyyy HH:mm') + '.'],
    [''],
    ['Что есть в демо'],
    ['• Прогнозы — кратко: сыгранные матчи с прогнозом модели и итогом — что зашло, а что нет'],
    ['• Что заходит: как часто ставки заходят у команд за сезон (первые команды)'],
    ['• Таблица лиги, модель против рынка, точность за сезон (верх листов)'],
    [''],
    ['Что в полной версии'],
    ['• Прогнозы на матчи сегодня и ближайших дней, все команды и все виды ставок'],
    ['• Рейтинг силы Elo, досье команд, LIVE, конструктор матча, купон дня'],
    [''],
    ['Прогнозы каждый день — в Telegram: ' + DEMO_CHANNEL],
    ['Это аналитика и статистика, а не гарантия результата.']
  ];
  a.getRange(1, 1, lines.length, 1).setValues(lines).setFontFamily('Arial').setFontSize(11).setFontColor('#202124');
  a.getRange(1, 1).setFontSize(16).setFontWeight('bold').setFontColor('#193c78');
  [4, 9, 13].forEach(function (r) { a.getRange(r, 1).setFontWeight('bold').setFontSize(12); });
  a.setColumnWidth(1, 820);
  a.setHiddenGridlines(true);
}

/** Удалить демо: файл — в корзину, ежедневное обновление — снять. */
function demoRemove() {
  var p = demoProps_(), id = p.getProperty('DEMO_ID');
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'demoSync') ScriptApp.deleteTrigger(t); });
  if (id) { try { DriveApp.getFileById(id).setTrashed(true); } catch (e) { /* уже удалён */ } }
  p.deleteProperty('DEMO_ID');
}
