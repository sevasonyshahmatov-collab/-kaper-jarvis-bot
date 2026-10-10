/* ==========================================================================
 * TELEGRAM И GEMINI
 *  Свойства скрипта (меню «⚽ АПЛ» → Настройки → «Ключи и Telegram»):
 *   TG_BOT_TOKEN — токен бота (можно того же, что в хоккейных таблицах);
 *   TG_ADMIN_ID  — ваш Telegram ID: сюда приходят посты-прогнозы и служебные сообщения;
 *   EPL_CHANNEL  — канал АПЛ (@имя или -100…): «Матчи дня» и «Итоги дня». Бот — админ канала с правом публиковать;
 *   GEMINI_KEY   — ключ Gemini для текстов постов.
 * ========================================================================== */

function tgRaw_(method, payload) {
  var token = prop_('TG_BOT_TOKEN');
  if (!token) throw new Error('не указан токен бота: меню «⚽ АПЛ» → Настройки → «Ключи и Telegram»');
  var resp = UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/' + method, {
    method: 'post', contentType: 'application/json', payload: JSON.stringify(payload || {}), muteHttpExceptions: true });
  var out = {};
  try { out = JSON.parse(resp.getContentText()); } catch (e) { out = { ok: false, description: 'HTTP ' + resp.getResponseCode() }; }
  return out;
}
function escHtml_(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
/** Отправить текст (HTML), длинный — частями по абзацам. Возвращает ok. */
function tgSend_(chat, html, opt) {
  opt = opt || {};
  if (!chat) throw new Error('не указан получатель');
  var parts = [], cur = '';
  String(html).split(/\n{2,}/).forEach(function (p) {
    if ((cur + '\n\n' + p).length > 3800 && cur) { parts.push(cur); cur = p; } else cur = cur ? cur + '\n\n' + p : p;
  });
  if (cur) parts.push(cur);
  var ok = true, last = null;
  parts.forEach(function (t) {
    var r = tgRaw_('sendMessage', { chat_id: chat, text: t, parse_mode: 'HTML', disable_web_page_preview: true, disable_notification: !!opt.silent });
    if (!r.ok) { ok = false; last = r.description; }
  });
  if (!ok) throw new Error('Telegram: ' + last);
  return ok;
}
function tgAdmin_() { return prop_('TG_ADMIN_ID'); }
function tgChannel_() { return prop_('EPL_CHANNEL'); }
function notifyAdmin_(text) {
  var to = tgAdmin_(); if (!to) return false;
  try { return !!tgRaw_('sendMessage', { chat_id: to, text: String(text).slice(0, 3900), disable_web_page_preview: true }).ok; } catch (e) { return false; }
}

/* ---------------- Gemini ---------------- */
function geminiModel_() {
  var m = prop_('GEMINI_MODEL'); if (m) return m;
  var key = prop_('GEMINI_KEY'); if (!key) throw new Error('нет ключа GEMINI_KEY');
  var r = fetchJson_('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200&key=' + encodeURIComponent(key));
  if (!r.data) throw new Error('Gemini не отдал список моделей (код ' + r.code + ')');
  var models = (r.data.models || []).filter(function (x) {
    return (x.supportedGenerationMethods || []).indexOf('generateContent') !== -1 && /flash/i.test(x.name) && !/image|tts|audio|live|preview|exp/i.test(x.name);
  }).map(function (x) { return x.name.replace(/^models\//, ''); });
  var lite = models.filter(function (n) { return /lite/i.test(n); });
  var pick = (lite.length ? lite : models).sort().reverse()[0];
  if (!pick) throw new Error('не нашёл модель Gemini Flash');
  props_().setProperty('GEMINI_MODEL', pick);
  return pick;
}
/** Запрос к Gemini; json=true — ответ в JSON. Возвращает текст ответа. */
function gemini_(prompt, json) {
  var key = prop_('GEMINI_KEY'); if (!key) throw new Error('нет ключа GEMINI_KEY');
  var model = geminiModel_();
  var cfg = { temperature: 0.4 }; if (json) cfg.responseMimeType = 'application/json';
  var resp = UrlFetchApp.fetch('https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent?key=' + encodeURIComponent(key), {
    method: 'post', contentType: 'application/json', muteHttpExceptions: true,
    payload: JSON.stringify({ contents: [{ role: 'user', parts: [{ text: prompt }] }], generationConfig: cfg }) });
  if (resp.getResponseCode() !== 200) throw new Error('Gemini (' + model + ') ответил кодом ' + resp.getResponseCode() + ': ' + resp.getContentText().slice(0, 200));
  var body = JSON.parse(resp.getContentText());
  var out = ((((body.candidates || [])[0] || {}).content || {}).parts || []).map(function (p) { return p.text || ''; }).join('');
  if (!out) throw new Error('Gemini вернул пустой ответ');
  return out;
}

/** Меню: проверить бота, вашу личку и канал. */
function tgCheckNow_() {
  var lines = [];
  try { var me = tgRaw_('getMe', {}); lines.push(me.ok ? '✅ Бот: @' + me.result.username : '❌ Бот: ' + me.description); } catch (e) { lines.push('❌ Бот: ' + e.message); }
  var adm = tgAdmin_();
  if (!adm) lines.push('— Ваш ID не указан'); else { try { var r = tgRaw_('sendMessage', { chat_id: adm, text: '⚽ АПЛ: проверка связи — всё работает.' }); lines.push(r.ok ? '✅ Личка: сообщение отправлено' : '❌ Личка: ' + r.description); } catch (e) { lines.push('❌ Личка: ' + e.message); } }
  var ch = tgChannel_();
  if (!ch) lines.push('— Канал АПЛ не указан: посты в канал не отправляются');
  else { try { var c = tgRaw_('getChat', { chat_id: ch }); lines.push(c.ok ? '✅ Канал: ' + (c.result.title || ch) + ' (в канал ничего не отправлял)' : '❌ Канал: ' + c.description); } catch (e) { lines.push('❌ Канал: ' + e.message); } }
  lines.push(prop_('GEMINI_KEY') ? '✅ Ключ Gemini указан' : '— Ключа Gemini нет: тексты постов не пишутся');
  uiAlert_(lines.join('\n'));
}
