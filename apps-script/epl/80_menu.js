/* ==========================================================================
 * МЕНЮ И ПЕРВИЧНАЯ НАСТРОЙКА
 * ========================================================================== */

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('⚽ АПЛ')
    .addItem('🔄 Обновить всё', 'updateAllNow_')
    .addItem('📈 Обновить коэффициенты', 'updateOddsNow_')
    .addItem('✍️ Пост-прогноз на матч', 'postNowMenu_')
    .addSeparator()
    .addSubMenu(ui.createMenu('📣 Канал АПЛ')
      .addItem('Опубликовать «Матчи дня» сейчас', 'publishMatchdayNow_')
      .addItem('Пробный пост «Матчи дня» — мне', 'previewMatchdayNow_')
      .addItem('Пробный пост «Итоги дня» — мне', 'previewResultsNow_')
      .addItem('Куда отправлять посты-прогнозы', 'postsToMenu_')
      .addItem('Автопосты-прогнозы: включить / выключить', 'postToggle_'))
    .addSubMenu(ui.createMenu('🧮 Модель')
      .addItem('Проверить модель на прошлых сезонах', 'backtestNow_')
      .addItem('Применить лучший вариант проверки', 'btApplyBest_')
      .addItem('Загрузить архив сезонов заново', 'archiveNow_')
      .addItem('Подтянуть xG (Understat)', 'xgNow_'))
    .addSubMenu(ui.createMenu('Настройки')
      .addItem('1 · Ключи и Telegram', 'keysSetup_')
      .addItem('2 · Первичная настройка таблицы', 'setupNow_')
      .addSeparator()
      .addItem('Включить автоматику', 'installAutomationNow_')
      .addItem('Выключить автоматику', 'removeAutomationNow_')
      .addItem('Статус автоматики', 'autoStatusNow_')
      .addItem('Проверить Telegram', 'tgCheckNow_')
      .addItem('Проверить источники данных', 'sourcesCheckNow_'))
    .addToUi();
}

function keysSetup_() {
  var ui = SpreadsheetApp.getUi(), p = props_();
  var ask = function (key, title, hint) {
    var cur = p.getProperty(key);
    var r = ui.prompt(title, hint + (cur ? '\n\nСейчас задано. Оставьте поле пустым, чтобы не менять.' : ''), ui.ButtonSet.OK_CANCEL);
    if (r.getSelectedButton() !== ui.Button.OK) return false;
    var v = String(r.getResponseText() || '').trim();
    if (v) p.setProperty(key, v);
    return true;
  };
  if (!ask('TG_BOT_TOKEN', 'Токен Telegram-бота', 'Можно того же бота, что в хоккейных таблицах (свойство TG_BOT_TOKEN), или нового от @BotFather.')) return;
  if (!ask('TG_ADMIN_ID', 'Ваш Telegram ID', 'Число (то же, что TG_ADMIN_ID в таблице КХЛ). Сюда — посты-прогнозы на проверку и служебные сообщения.')) return;
  if (!ask('EPL_CHANNEL', 'Канал АПЛ', 'Отдельный канал для АПЛ: @имя или числовой ID (-100…). Бот должен быть его администратором с правом публиковать. Пусто — в канал ничего не уходит.')) return;
  if (!ask('GEMINI_KEY', 'Ключ Gemini', 'Тот же, что в таблице КХЛ (свойство GEMINI_KEY). Нужен для текстов постов. Пусто — посты будут короче, без текста от ИИ.')) return;
  uiAlert_('Сохранено. Проверить: Настройки → «Проверить Telegram». Дальше — «2 · Первичная настройка таблицы».');
}

/* ---------------- первичная настройка (по этапам, с продолжением) ---------------- */
var SETUP_STAGES = [
  ['sheets', 'листы таблицы'],
  ['archive', 'архив прошлых сезонов с линиями'],
  ['matches', 'календарь и результаты сезона'],
  ['xg', 'xG сыгранных матчей'],
  ['model', 'сила команд и прогнозы'],
  ['odds', 'линия букмекера'],
  ['backtest', 'проверка модели на прошлых сезонах'],
  ['auto', 'автоматика']
];
var SETUP_MAX_MS = 270000;

function setupNow_() {
  var st = propJson_('SETUP', {});
  if (st.stage === 'done') {
    var ui = SpreadsheetApp.getUi();
    if (ui.alert('Таблица уже настроена. Пройти настройку заново? Данные перезагрузятся, журнал постов сохранится.', ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
  }
  propSetJson_('SETUP', { stage: SETUP_STAGES[0][0], started: mskNow_(), log: [] });
  props_().deleteProperty('BT_STATE');
  var r = setupRun_();
  uiAlert_(r.done ? 'Готово! ' + r.text : 'Настройка идёт: ' + r.text + '\n\nДальше таблица продолжит сама (Google даёт скрипту 6 минут за раз). Как закончит — пришлю сообщение в Telegram, а этапы видно на листе «' + JOURNAL_SHEET + '».');
}
function setupContinue_() {
  try { ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'setupContinue_') ScriptApp.deleteTrigger(t); }); } catch (e) {}
  QUIET_ = true;
  try { setupRun_(); } finally { QUIET_ = false; }
}
function setupRun_() {
  var ss = SpreadsheetApp.getActive(), t0 = Date.now(), st = propJson_('SETUP', {});
  var idx = function (s) { for (var i = 0; i < SETUP_STAGES.length; i++) if (SETUP_STAGES[i][0] === s) return i; return -1; };
  while (st.stage !== 'done') {
    var i = idx(st.stage), name = SETUP_STAGES[i][1], msg = '';
    try {
      if (st.stage === 'sheets') msg = setupSheets_(ss);
      else if (st.stage === 'archive') { var a = updateArchive_(ss); msg = a.rows + ' матчей' + (a.errors.length ? ' (не загрузились: ' + a.errors.join('; ') + ')' : ''); }
      else if (st.stage === 'matches') { var m = updateMatches_(ss, { full: true }); msg = m.total + ' матчей, сыграно ' + m.played; }
      else if (st.stage === 'xg') { try { var x = updateXg_(ss); msg = 'xG у ' + x.matched + ' матчей'; } catch (e) { msg = 'xG пока нет (' + e.message + ') — модель возьмёт удары в створ'; } }
      else if (st.stage === 'model') { props_().setProperty('SETUP_MODEL', '1'); var r = refreshModelSheets_(ss); msg = 'прогнозов ' + r.fresh + ', задним числом ' + r.retro; }
      else if (st.stage === 'odds') { try { var o = updateOdds_(ss); renderPredictions_(ss); renderVs_(ss); msg = 'линий ' + o.lines; } catch (e) { msg = 'линия не загрузилась: ' + e.message; } }
      else if (st.stage === 'backtest') {
        var b = backtestRun_(true, true);
        if (!b.done) { journal_('Настройка', true, 'проверка модели: готово вариантов ' + b.runs + ', продолжаю'); propSetJson_('SETUP', st); setupSchedule_(); return { done: false, text: 'идёт проверка модели' }; }
        refreshModelSheets_(ss);
        msg = b.best ? btParamsText_(b.best.P) : 'без результата';
      }
      else if (st.stage === 'auto') { ensureAutomation_(true); autoRender_(ss); setupOrder_(ss); msg = AUTO_JOBS.length + ' запусков'; }
      st.log = (st.log || []).concat([name + ': ' + msg]);
      journal_('Настройка', true, name + ': ' + msg);
    } catch (e) {
      st.log = (st.log || []).concat([name + ': ОШИБКА ' + e.message]);
      journal_('Настройка', false, name + ': ' + e.message);
      if (st.stage === 'archive' || st.stage === 'matches' || st.stage === 'model') {      // без них дальше нельзя
        propSetJson_('SETUP', st);
        notifyAdmin_('⚠ АПЛ: настройка остановилась на этапе «' + name + '»: ' + e.message);
        return { done: false, text: 'ошибка на этапе «' + name + '»: ' + e.message };
      }
    }
    st.stage = i + 1 < SETUP_STAGES.length ? SETUP_STAGES[i + 1][0] : 'done';
    propSetJson_('SETUP', st);
    if (st.stage !== 'done' && Date.now() - t0 > SETUP_MAX_MS) { setupSchedule_(); return { done: false, text: st.log.join('\n') }; }
  }
  st.finished = mskNow_(); propSetJson_('SETUP', st);
  notifyAdmin_('✅ Таблица АПЛ настроена.\n\n' + st.log.join('\n'));
  return { done: true, text: st.log.join('\n') };
}
function setupSchedule_() {
  try { ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'setupContinue_') ScriptApp.deleteTrigger(t); });
    ScriptApp.newTrigger('setupContinue_').timeBased().after(60 * 1000).create(); } catch (e) {}
}

var GUIDE_SHEET = 'Как пользоваться';
function setupSheets_(ss) {
  try { ss.setSpreadsheetTimeZone(TZ); } catch (e) {}
  var sh = sheet_(ss, GUIDE_SHEET);
  sh.clear();
  var lines = [
    ['КАПЕР ДЖАРВИС · АПЛ'],
    ['Та же логика, что в таблицах КХЛ и НХЛ, но модель — футбольная: сила атаки и обороны каждой команды по голам и xG, свежие матчи весят больше.'],
    [''],
    ['ЛИСТЫ'],
    ['Прогнозы — П1/Х/П2, ожидаемые голы, тотал 2,5, «обе забьют», линия Pinnacle и «лучший прогноз» (смесь линии и модели) на 2 недели вперёд и по сыгранным.'],
    ['Модель vs рынок — где модель расходится с линией на ближайшую неделю и есть ли ставка.'],
    ['Сила команд — рейтинг по модели: на сколько голов команда лучше среднего соперника; реализация и «удача» по xG.'],
    ['Таблица — турнирная таблица и очки «по игре» (xPts): кто набрал больше, чем заслужил, и наоборот.'],
    ['Точность — кто точнее: модель, букмекер или их смесь; итог наших ставок и закрытие линии (CLV).'],
    ['Коэффициенты — линия по каждому матчу: первая, при публикации и закрывающая.'],
    ['Посты — что ушло в Telegram, ставка, кэф, итог.'],
    ['Матчи — календарь и результаты сезона (ESPN), xG (Understat).'],
    ['Проверка модели — как модель угадывала два прошлых сезона «вслепую» против закрывающей линии.'],
    ['Автоматика и Журнал_автоматики — что и когда таблица делает сама.'],
    [''],
    ['TELEGRAM'],
    ['Посты-прогнозы — за 2,5–4 часа до матча, по умолчанию вам в личку (меню «📣 Канал АПЛ» → «Куда отправлять посты-прогнозы»).'],
    ['В канал АПЛ: «Матчи дня» в 11:00 МСК в дни матчей и «Итоги дня», когда доигран последний матч.'],
    [''],
    ['ЧЕСТНОСТЬ'],
    ['Прогноз на матч фиксируется до начала и потом не меняется. Точность считается только по таким прогнозам. Ставка предлагается, только если модель выше линии на 5 п.п. и больше.']
  ];
  sh.getRange(1, 1, lines.length, 1).setValues(lines).setWrap(true);
  sh.getRange(1, 1).setFontSize(14).setFontWeight('bold');
  [4, 16, 20].forEach(function (r) { sh.getRange(r, 1).setFontWeight('bold'); });
  try { sh.setColumnWidth(1, 900); } catch (e) {}
  [SHEET_PRED, SHEET_VS, SHEET_POWER, SHEET_TABLE, SHEET_ACC, SHEET_ODDS, SHEET_POSTS, SHEET_MATCHES, SHEET_BT, AUTO_SHEET, JOURNAL_SHEET].forEach(function (n) { sheet_(ss, n); });
  postsSheet_(ss);
  var def = ss.getSheetByName('Лист1') || ss.getSheetByName('Sheet1');
  if (def && ss.getSheets().length > 1 && def.getLastRow() === 0) ss.deleteSheet(def);
  return 'созданы';
}
function setupOrder_(ss) {
  var order = [GUIDE_SHEET, SHEET_PRED, SHEET_VS, SHEET_POWER, SHEET_TABLE, SHEET_ACC, SHEET_ODDS, SHEET_POSTS, SHEET_MATCHES, SHEET_BT, AUTO_SHEET, JOURNAL_SHEET, SHEET_ARCHIVE, SHEET_PLOG];
  order.forEach(function (n, i) { var sh = ss.getSheetByName(n); if (!sh) return; try { ss.setActiveSheet(sh); ss.moveActiveSheet(i + 1); } catch (e) {} });
  var colors = { 'Прогнозы': '#0b3d2e', 'Модель vs рынок': '#0b3d2e', 'Сила команд': '#1a4fd6', 'Таблица': '#1a4fd6', 'Точность': '#b8860b' };
  Object.keys(colors).forEach(function (n) { var sh = ss.getSheetByName(n); if (sh) try { sh.setTabColor(colors[n]); } catch (e) {} });
  try { ss.getSheetByName(SHEET_ARCHIVE).hideSheet(); } catch (e) {}
  try { ss.setActiveSheet(ss.getSheetByName(SHEET_PRED)); } catch (e) {}
}

/* ---------------- кнопки ---------------- */
function updateAllNow_() {
  if (notReady_()) { uiAlert_('Сначала «Первичная настройка таблицы».'); return; }
  var ss = SpreadsheetApp.getActive(), msg = [];
  var m = updateMatches_(ss, { back: 14, ahead: 60 }); msg.push('Матчей в календаре: ' + m.total + ', сыграно ' + m.played + ', изменилось ' + m.changed + '.');
  try { var x = updateXg_(ss); msg.push('xG: обновлено ' + x.matched + '.'); } catch (e) { msg.push('xG: ' + e.message); }
  try { var o = updateOdds_(ss); msg.push('Линия: ' + o.lines + ' матчей.'); } catch (e) { msg.push('Линия: ' + e.message); }
  var r = refreshModelSheets_(ss); msg.push('Прогнозов обновлено: ' + r.fresh + '.');
  sheetOpen_(SHEET_PRED); uiAlert_(msg.join('\n'));
}
function updateOddsNow_() {
  var ss = SpreadsheetApp.getActive();
  try { var r = updateOdds_(ss); renderPredictions_(ss); renderVs_(ss); uiAlert_('Линия: ' + r.lines + ' матчей, обновлено ' + r.updated + (r.unmatched.length ? '\nНе нашёл в календаре: ' + r.unmatched.join(', ') : '')); }
  catch (e) { uiAlert_('Не получилось: ' + e.message); }
}
function archiveNow_() { var r = updateArchive_(); uiAlert_('Архив: ' + r.rows + ' матчей' + (r.errors.length ? '\nНе загрузились: ' + r.errors.join('; ') : '')); }
function xgNow_() { try { var r = updateXg_(); refreshModelSheets_(SpreadsheetApp.getActive()); uiAlert_('xG вписан в ' + r.matched + ' матчей (у Understat есть ' + r.available + ').'); } catch (e) { uiAlert_('Understat: ' + e.message); } }

function sourcesCheckNow_() {
  var y = seasonStartYear_(), out = [];
  var t = function (name, fn) { try { out.push('✅ ' + name + ': ' + fn()); } catch (e) { out.push('❌ ' + name + ': ' + e.message); } };
  t('ESPN (календарь, счёт, удары)', function () { var d = espnRange_(new Date(Date.now() - 7 * 86400000), new Date(Date.now() + 7 * 86400000)); return d.length + ' матчей за ±7 дней'; });
  t('Understat (xG)', function () { var d = understatSeason_(y); return d.filter(function (x) { return x.done; }).length + ' сыгранных матчей с xG'; });
  t('football-data.co.uk (архив и закрывающие линии)', function () { return fdSeason_(y - 1).length + ' матчей прошлого сезона'; });
  t('Pinnacle (линия)', function () { var r = marketFetch_('/leagues/' + marketLeagueId_(false) + '/matchups'); if (!r.data) throw new Error('код ' + r.code); return r.data.length + ' событий'; });
  var unk = Object.keys(UNKNOWN_TEAMS_); if (unk.length) out.push('Не знаю русского названия: ' + unk.join(', '));
  uiAlert_(out.join('\n'));
}
