/* ВСТАВИТЬ ВРУЧНУЮ — одинаково в таблицу КХЛ и в таблицу НХЛ (Расширения → Apps Script → файл «Код»).
 *
 * Что чинит: разбор видео писал «дневной лимит Gemini на видео исчерпан», даже когда дневной лимит ни при чём —
 * например, если модель, которую таблица берёт для видео, Google убрал из бесплатного тарифа (он отвечает «limit: 0»,
 * старый код принимал это за исчерпанный дневной лимит). Теперь таблица читает ответ Google целиком:
 *   • «limit: 0» → сама переходит на другую модель Flash и запоминает её;
 *   • минутный лимит → повторяет через 2 минуты, а не ждёт до утра;
 *   • дневной лимит → пишет, какой именно (например, «20 запросов в сутки») и у какой модели;
 *   • последний ответ Google с ошибкой 429 сохраняется в свойство скрипта GEMINI_LAST_429 (Настройки проекта → Свойства скрипта).
 *
 * ШАГ 1. Нажмите Ctrl+F, найдите строку
 *          /** Один запрос к Gemini с роликом
 *        Выделите всё от этой строки и вниз до строки (её не выделять)
 *          /** Английские написания клубов КХЛ
 *        и вставьте вместо выделенного весь текст ниже, начиная со строки «/** Один запрос к Gemini с роликом».
 *
 * ШАГ 2. Нажмите Ctrl+H (найти и заменить). Найти:
 *          Дневной бесплатный лимит Gemini на видео исчерпан (около 8 часов роликов в сутки). Лимит сбрасывается
 *        Заменить на:
 *          Дневной бесплатный лимит Gemini исчерпан — какой именно, написано ниже во «Внимание». Лимит считается на проект Google, где создан ключ, и общий для всех таблиц с этим ключом. Сбрасывается
 *        Нажмите «Заменить» (одно совпадение).
 *
 * ШАГ 3. Ctrl+S (сохранить). После этого в меню «🎬 … · Видео» снова нажмите «Разобрать видео».
 */

/** Один запрос к Gemini с роликом (или его куском). {author, teams:[...], model} */
function videoGeminiClip_(url, from, to, deadline, memory) {
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
      payload: JSON.stringify({ contents: [{ role: 'user', parts: [part, { text: videoPrompt_(from, to, memory) }] }], generationConfig: gc })
    });
  };
  // Перегрузка Google (500/502/503/504) — временная: повторяем с паузой, затем пробуем запасную модель Flash.
  var busy = function (c) { return c === 500 || c === 502 || c === 503 || c === 504; };
  var models = [model], alt = videoAltModel_(model), resp = null, q429 = [];
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
    if (resp.getResponseCode() === 429) {
      var q = geminiQuota_(resp.getContentText(), models[mi]);
      q429.push(q);
      try { p.setProperty('GEMINI_LAST_429', mskNow_() + ' · ' + models[mi] + ' · ' + resp.getContentText().slice(0, 4000)); } catch (e) {}
      if (q.zero) {                                                          // лимит 0: модель не входит в бесплатный тариф — берём следующую
        videoNoFree_(models[mi]);
        var nx = models.length < 4 ? videoNextModel_(models) : '';
        if (nx) models.push(nx);
      }
      if (mi < models.length - 1) continue;                                  // лимит у этой модели — у запасной он свой
    }
    if (!busy(resp.getResponseCode())) { model = models[mi]; break; }
  }
  var code = resp.getResponseCode(), txt = resp.getContentText();
  if (busy(code)) throw new Error('Gemini перегружен (' + code + ', ' + models.join(' и ') + ') — продолжу позже');
  if (code === 429) {
    var live = q429.filter(function (x) { return !x.zero; }), why = q429.map(function (x) { return x.why; }).join('; ');
    if (!live.length) throw new Error('дневной лимит: у ключа Gemini нет бесплатного лимита на модели для видео (' + why + ') — продолжу после сброса');
    if (live.some(function (x) { return !x.day; })) throw new Error('лимит Gemini в минуту (429: ' + why + ') — продолжу позже');
    throw new Error('дневной лимит Gemini исчерпан (429: ' + why + ') — продолжу после сброса');
  }
  if (code === 200 && q429.length && q429[0].zero && model !== models[0]) {  // основная модель стала платной — дальше сразу работающая
    p.setProperty('GEMINI_VIDEO_MODEL', model);
    p.deleteProperty('GEMINI_VIDEO_ALT');
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
  var all = videoFlashModels_();
  if (!all) return '';
  var nofree = videoNoFree_();
  var pick = all.filter(function (n) { return n !== current && /^gemini-\d/.test(n) && !nofree[n]; }).sort().reverse()[0] || '';
  p.setProperty('GEMINI_VIDEO_ALT', pick || '-');
  return pick;
}

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
