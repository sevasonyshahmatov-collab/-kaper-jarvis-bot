/* ДОВСТАВКА к 2026-10-05_video_limit.js — если таблица пишет «geminiQuota_ is not defined».
 *
 * Значит, в «Код.gs» попала только верхняя часть кода, а четыре вспомогательные функции из конца файла — нет.
 *
 * 1. В «Код.gs» нажмите Ctrl+F и найдите строку
 *      /** Английские написания клубов КХЛ
 *    Кликните в самое начало этой строки (перед «/**») и нажмите Enter — появится пустая строка.
 * 2. Встаньте на эту пустую строку и вставьте весь этот файл целиком (вместе с этим комментарием — он не мешает).
 * 3. Ctrl+S. Затем «Разобрать видео» ещё раз.
 *
 * Если какие-то из этих функций у вас уже были — ничего страшного: функции те же самые, ошибки не будет.
 */

/** Модели Flash (не lite), которые умеют generateContent; null — список не получить. */
function videoFlashModels_() {
  try {
    var resp = UrlFetchApp.fetch('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200&key=' + encodeURIComponent(agentProps_().getProperty('GEMINI_KEY')), { muteHttpExceptions: true });
    if (resp.getResponseCode() !== 200) return null;
    return (JSON.parse(resp.getContentText()).models || []).filter(function (x) {
      return (x.supportedGenerationMethods || []).indexOf('generateContent') !== -1 && /flash/i.test(x.name) && !/lite|image|tts|audio|live|exp|preview/i.test(x.name);
    }).map(function (x) { return x.name.replace(/^models\//, ''); });
  } catch (e) { return null; }
}

/** Следующая модель Flash вместо той, что без бесплатного лимита: не из tried и не отмеченная. '' — нет такой. */
function videoNextModel_(tried) {
  var nofree = videoNoFree_();
  return (videoFlashModels_() || []).filter(function (n) { return tried.indexOf(n) < 0 && !nofree[n]; })
    .sort(function (a, b) { return (b === 'gemini-flash-latest') - (a === 'gemini-flash-latest') || (a < b ? 1 : a > b ? -1 : 0); })[0] || '';
}

/** Модели, у которых Gemini ответил «limit: 0» (нет в бесплатном тарифе): videoNoFree_() — {модель: дата}, videoNoFree_(m) — отметить.
 *  Отметка живёт 7 дней: Google иногда возвращает модели бесплатный лимит. */
function videoNoFree_(model) {
  var p = agentProps_(), map = {}, now = Date.now();
  try { map = JSON.parse(p.getProperty('GEMINI_NOFREE') || '{}'); } catch (e) { map = {}; }
  Object.keys(map).forEach(function (m) { if (now - Number(map[m]) > 7 * 864e5) delete map[m]; });
  if (model) { map[model] = now; if (p.getProperty('GEMINI_VIDEO_ALT') === model) p.deleteProperty('GEMINI_VIDEO_ALT'); }
  try { p.setProperty('GEMINI_NOFREE', JSON.stringify(map)); } catch (e) {}
  return map;
}

/** Что Gemini написал в ответе 429. Дневной лимит отличаем от минутного по названию квоты (…PerDay… / …PerMinute…) — так пишет сам Google.
 *  {day, zero — «limit: 0», модель не бесплатная, wait — через сколько секунд повторить, why — коротко для сообщения} */
function geminiQuota_(txt, model) {
  var e = {}; try { e = JSON.parse(txt).error || {}; } catch (x) { e = {}; }
  var msg = String(e.message || txt || ''), vs = [], wait = 0;
  (e.details || []).forEach(function (d) {
    (d.violations || []).forEach(function (v) { vs.push({ id: String(v.quotaId || ''), metric: String(v.quotaMetric || ''), val: v.quotaValue === undefined ? '' : String(v.quotaValue) }); });
    if (d.retryDelay) wait = parseFloat(d.retryDelay) || 0;
  });
  var lim = msg.match(/limit:\s*(\d+)/);
  var zero = vs.some(function (v) { return v.val === '0'; }) || !!(lim && lim[1] === '0');
  var day = vs.length ? vs.some(function (v) { return /PerDay/i.test(v.id); }) : /per ?day|daily|YouTube/i.test(msg);
  var v = vs.filter(function (x) { return /PerDay/i.test(x.id) === day; })[0] || vs[0] || { id: '', metric: '', val: lim ? lim[1] : '' };
  var what = /token/i.test(v.id + v.metric) ? 'токенов' : /request/i.test(v.id + v.metric) ? 'запросов' : '';
  var why = model + ': ' + (zero ? 'лимит 0 — модели нет в бесплатном тарифе' :
    (v.val ? v.val + ' ' : 'лимит ') + (what ? what + ' ' : '') + (day ? 'в сутки' : 'в минуту'));   // полный ответ — в свойстве GEMINI_LAST_429
  return { day: day, zero: zero, wait: wait, why: why };
}
