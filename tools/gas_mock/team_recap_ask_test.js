/* Проверка утреннего опроса «На какие прогнозы вчера ставили?» (apps-script/project/Код.js: recapAsk*, recapFree*,
 * recapDispatch_) на макете Apps Script: 16.10, 05:00 МСК; Telegram, GitHub (SENT.md, INBOX, запуск itogi.yml) подменены записью.
 *   node tools/gas_mock/team_recap_ask_test.js        → «ok», иначе первая ошибка */
const assert = require('assert');
const path = require('path');
const gm = require('./gas_mock');

const ROOT = path.join(__dirname, '..', '..');
const CHAT = 777, BOT = { id: 42, is_bot: true }, OWNER = { id: 1 };
const SENT = [
  '| Номер | Лига | Матч (дата и время МСК) | Ставка | Кэф | «Что заходит» | Отправлено |',
  '|---|---|---|---|---|---|---|',
  '| 1410-1 | КХЛ | Спартак — ЦСКА, 14.10 19:30 | победа Спартака в осн. время | 1,90 | 55 % | 14.10 |',
  '| 1510-1 | КХЛ | Лада — СКА, 15.10 18:00 | победа СКА в осн. время | 1,64 | 58,8 % | 15.10 08:49 |',
  '| 1510-2 | КХЛ | Северсталь — Локомотив, 15.10 19:00 | тотал матча меньше 4,5 | 2,05 | 58,0 % | 15.10 08:49 |',
  '| 1510-3 | КХЛ | Торпедо — Динамо Москва, 16.10 19:00 | итоговая победа Торпедо | 1,67 | 66,3 % | 15.10 10:37 |',
  '| 1510-6 | НХЛ | Тампа-Бэй — Сиэтл, 16.10 02:00 | фора Сиэтла +1,5 | 1,83 | 72,1 % | 15.10 11:52 |',
  '| 1510-14 | НХЛ | Вегас — Калгари, 16.10 05:00 | тотал матча больше 5,5 | 1,66 | 66,0 % | 15.10 11:52 |',
  '| 1510-15 | КХЛ | Северсталь — Локомотив, 15.10 19:00 | тотал матча меньше 4,5 (повтор 1510-2 по просьбе владельца — для правки) | 2,02 | 58,0 % | 15.10 15:10 |',
  '| 1610-1 | КХЛ | Адмирал — Спартак, 16.10 12:30 | победа Спартака в основное время | 1,95 | 50,5 % | 16.10 04:46 |',
].join('\n');
const INBOX = [
  '- [x] 15.10 09:14 · опубликовано владельцем: 1510-2 «КХЛ · 15 октября · 19:00 МСК»',
  '- [x] 15.10 12:00 · правка владельца в боте: 1510-1 — новый текст поста; Прогноз: победа СКА с учётом ОТ; Кэф: 1,50',
  '- [x] 16.10 00:30 · опубликовано владельцем (по расписанию): 1510-6 «НХЛ · 16 октября · 02:00 МСК»',
].join('\n');

/** Макет таблицы на момент iso (UTC); props — свойства скрипта с прошлого «запуска». */
function boot(iso, props) {
  const env = gm.makeEnv({ now: iso, cache: true });
  gm.load(env, [path.join(ROOT, 'apps-script/project/Код.js')]);
  Object.assign(env.props, props || {}, { GITHUB_TOKEN: 'x', TEAM_OWNER_CHAT: String(CHAT) });
  const ctx = env.ctx, w = { env, ctx, calls: [], inbox: [], gh: [], files: { 'team/picks/SENT.md': SENT, 'team/INBOX.md': INBOX }, ghCode: 204 };
  let nextId = 900;
  ctx.tgRaw_ = (method, payload) => { const p = JSON.parse(JSON.stringify(payload)); w.calls.push({ method, payload: p }); return { ok: true, result: { message_id: nextId++ } }; };
  ctx.teamAppend_ = (p, line) => { w.inbox.push(line); };
  ctx.teamFile_ = p => { if (!(p in w.files)) throw new Error('нет ' + p); return { text: w.files[p], sha: 's' }; };
  ctx.itogiGithub_ = (method, url, body) => { w.gh.push({ method, url, body: JSON.parse(JSON.stringify(body || null)) }); return { getResponseCode: () => w.ghCode, getContentText: () => '{"message":"Resource not accessible by personal access token"}' }; };
  ctx.tgIsChannelAdmin_ = () => true;
  ctx.botEnsureCommands_ = () => {};
  let upd = 1;
  w.of = m => w.calls.filter(c => c.method === m);
  w.toast = () => (w.calls.find(c => c.method === 'answerCallbackQuery') || { payload: {} }).payload;
  w.press = (data, message) => { w.calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, callback_query: { id: 'q' + upd, from: OWNER, data, message } }); };
  w.say = (text, extra) => { w.calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, message: Object.assign({ message_id: 5000 + upd, chat: { id: CHAT, type: 'private' }, from: OWNER, text }, extra || {}) }); };
  w.tick = () => { w.calls.length = 0; return ctx.recapAskTick_(); };
  w.state = () => JSON.parse(env.props['RECAP_ASK_2026-10-16'] || 'null');
  return w;
}
const askMsg = (w, kb) => ({ message_id: w.state().mid, chat: { id: CHAT, type: 'private' }, from: BOT, text: 'Доброе утро! …', reply_markup: kb });
const kbOf = c => c.payload.reply_markup.inline_keyboard;

// 0. до 05:00 МСК — тишина
let w = boot('2026-10-16T01:55:00Z');
assert.strictEqual(w.tick(), '');
assert.strictEqual(w.calls.length, 0);

// 1. 05:00 МСК — вопрос и по кнопке на каждый вчерашний прогноз; опубликованные — ☑; правка владельца — в подписи
w = boot('2026-10-16T02:00:00Z');
assert.strictEqual(w.tick(), 'опрос: 5');
let sm = w.of('sendMessage');
assert.strictEqual(sm.length, 1);
assert.strictEqual(sm[0].payload.chat_id, String(CHAT));
assert.ok(/^Доброе утро! На какие прогнозы вчера ставили\?/.test(sm[0].payload.text), sm[0].payload.text);
let kb = kbOf(sm[0]);
assert.deepStrictEqual(kb.map(r => r.map(b => b.text)), [
  ['☐ Лада — СКА · победа СКА с учётом ОТ'],
  ['☑ Северсталь — Локомотив · тотал меньше 4,5 (1510-2)'],
  ['☐ Северсталь — Локомотив · тотал меньше 4,5 (1510-15)'],
  ['☑ Тампа-Бэй — Сиэтл · фора Сиэтла +1,5'],
  ['☐ Вегас — Калгари · тотал больше 5,5'],
  ['Готово', 'Сегодня без итогов']]);
assert.deepStrictEqual(kb.flat().map(b => b.callback_data), ['tm|rat|1510-1|2026-10-16', 'tm|rat|1510-2|2026-10-16', 'tm|rat|1510-15|2026-10-16',
  'tm|rat|1510-6|2026-10-16', 'tm|rat|1510-14|2026-10-16', 'tm|rad||2026-10-16', 'tm|ran||2026-10-16']);
assert.ok(kb.flat().every(b => Buffer.byteLength(b.callback_data) <= 64));
assert.strictEqual(w.tick(), '');                                   // через 5 минут второго вопроса нет
assert.strictEqual(w.calls.length, 0);

// 2. переключение: ☐ → ☑ (editMessageReplyMarkup), повторно — обратно
w.press('tm|rat|1510-1|2026-10-16', askMsg(w, kb));
let ed = w.of('editMessageReplyMarkup');
assert.strictEqual(ed.length, 1);
assert.strictEqual(kbOf(ed[0])[0][0].text, '☑ Лада — СКА · победа СКА с учётом ОТ');
assert.strictEqual(w.toast().text, 'Отмечено');
w.press('tm|rat|1510-2|2026-10-16', askMsg(w, kbOf(ed[0])));
assert.strictEqual(kbOf(w.of('editMessageReplyMarkup')[0])[1][0].text, '☐ Северсталь — Локомотив · тотал меньше 4,5 (1510-2)');
assert.strictEqual(w.toast().text, 'Снято');
assert.deepStrictEqual(Object.keys(w.state().sel).sort(), ['1510-1', '1510-6']);

// 3. свои прогнозы строками «Прогноз: …» — записаны, в ответ — что понял (кэф или «не указан»)
w.say('Прогноз: победа СКА в основное время, кэф 1,85\nпрогноз: тотал больше 5,5 в матче Вегас — Калгари 1.66\nПрогноз: ИТБ Юты 2,5');
sm = w.of('sendMessage');
assert.strictEqual(sm.length, 1);
const echo = sm[0].payload.text;
assert.ok(/Записал свои прогнозы \(3\)/.test(echo), echo);
assert.ok(echo.includes('1. победа СКА в основное время — кэф 1,85'), echo);
assert.ok(echo.includes('2. тотал больше 5,5 в матче Вегас — Калгари — кэф 1,66'), echo);
assert.ok(echo.includes('3. ИТБ Юты 2,5 — кэф не указан'), echo);
assert.deepStrictEqual(w.state().free, ['Прогноз: победа СКА в основное время, кэф 1,85', 'Прогноз: тотал больше 5,5 в матче Вегас — Калгари 1.66', 'Прогноз: ИТБ Юты 2,5']);
w.say('Прогноз: Динамо выиграет');                                  // второе сообщение дописывает
assert.strictEqual(w.state().free.length, 4);
w.say('Привет, как дела?');                                         // обычный текст — не наш
assert.strictEqual(w.state().free.length, 4);
w.say('КХЛ · 16 октября\nПрогноз: победа Торпедо\nКэф: 1,70');      // текст поста (правка) — не «свои прогнозы»
assert.strictEqual(w.state().free.length, 4);

// 4. «Готово»: строка в INBOX → запуск itogi.yml на ветке команды с выбором → «Принято — итоги будут через 2–3 минуты»
w.ghCode = 403;                                                      // у токена нет права Actions — понятная ошибка, выбор не теряется
w.press('tm|rad||2026-10-16', askMsg(w, kb));
assert.ok(w.toast().show_alert && /не запустились/.test(w.toast().text));
assert.ok(w.of('sendMessage').some(c => /GitHub ответил 403 — у токена GITHUB_TOKEN нет права Actions: Read and write/.test(c.payload.text)));
assert.strictEqual(w.inbox.length, 1);
assert.ok(!w.state().done);
w.ghCode = 204;
w.press('tm|rad||2026-10-16', askMsg(w, kb));
assert.strictEqual(w.inbox.length, 1, 'повторное «Готово» не дублирует строку INBOX');
assert.ok(/^- \[x\] 16\.10 05:00 · итоги ставок 16\.10: выбрано 1510-1, 1510-6; свои: "Прогноз: победа СКА в основное время, кэф 1,85"; "Прогноз: тотал больше 5,5 в матче Вегас — Калгари 1\.66"; "Прогноз: ИТБ Юты 2,5"; "Прогноз: Динамо выиграет"$/.test(w.inbox[0]), w.inbox[0]);
const d = w.gh[w.gh.length - 1];
assert.strictEqual(d.method, 'post');
assert.strictEqual(d.url, '/repos/sevasonyshahmatov-collab/-kaper-jarvis-bot/actions/workflows/itogi.yml/dispatches');
assert.strictEqual(d.body.ref, 'claude/project-migration-old-account-6e31vz');
const pl = JSON.parse(d.body.inputs.payload);
assert.deepStrictEqual(pl, { kind: 'team', job: 'team/out/2026-10-16/recap_ask.json', pids: ['1510-1', '1510-6'],
  free: w.state().free, day: '2026-10-16', at: '2026-10-16 05:00' });
assert.ok(w.of('sendMessage').some(c => c.payload.text === 'Принято — итоги будут через 2–3 минуты'));
assert.strictEqual(kbOf(w.of('editMessageReplyMarkup')[0])[0][0].text, '✅ Итоги заказаны: 6');
assert.strictEqual(w.state().done, 'ok');
w.press('tm|rat|1510-14|2026-10-16', askMsg(w, kb));               // после «Готово» опрос закрыт
assert.strictEqual(w.toast().text, 'Итоги уже заказаны');
assert.strictEqual(w.gh.length, 2);

// 5. напоминание в 08:00 — только если ответа нет, и одно
let props = Object.assign({}, w.env.props);
w = boot('2026-10-16T05:05:00Z', props);                             // 08:05 МСК, уже ответил — тишина
assert.strictEqual(w.tick(), '');
assert.strictEqual(w.calls.length, 0);
const fresh = boot('2026-10-16T02:00:00Z');
fresh.tick();
props = Object.assign({}, fresh.env.props);
w = boot('2026-10-16T04:30:00Z', props);                             // 07:30 — ещё рано
assert.strictEqual(w.tick(), '');
w = boot('2026-10-16T05:00:00Z', props);                             // 08:00 — одно напоминание ответом на вопрос
assert.strictEqual(w.tick(), 'напоминание');
sm = w.of('sendMessage');
assert.ok(sm.length === 1 && sm[0].payload.reply_to_message_id === w.state().mid && /Напоминаю: на какие прогнозы вчера ставили/.test(sm[0].payload.text));
assert.strictEqual(w.tick(), '');
assert.strictEqual(w.calls.length, 0);
assert.strictEqual(w.gh.length, 0, 'без ответа ничего не запускается и не публикуется');

// 6. «Сегодня без итогов» — опрос закрыт, строка в INBOX, без запуска; свои строки после этого не принимаются
w.press('tm|ran||2026-10-16', askMsg(w, kb));
assert.strictEqual(w.state().done, 'none');
assert.strictEqual(kbOf(w.of('editMessageReplyMarkup')[0])[0][0].text, 'Сегодня без итогов');
assert.ok(/итоги ставок 16\.10: сегодня без итогов$/.test(w.inbox[0]), w.inbox[0]);
assert.strictEqual(w.gh.length, 0);
w.say('Прогноз: победа СКА');
assert.ok(/без итогов/.test(w.of('sendMessage')[0].payload.text));
assert.strictEqual(w.state().free.length, 0);
w.press('tm|rad||2026-10-16', askMsg(w, kb));
assert.strictEqual(w.gh.length, 0);

// 7. «Готово» без единой отметки — подсказка, ничего не запускается
w = boot('2026-10-16T02:00:00Z');
w.files['team/INBOX.md'] = '';                                       // ничего не опубликовано — всё ☐
w.tick();
w.press('tm|rad||2026-10-16', askMsg(w, kbOf(w.of('sendMessage')[0] || { payload: { reply_markup: { inline_keyboard: [] } } })));
assert.ok(w.toast().show_alert && /Ничего не отмечено/.test(w.toast().text));
assert.strictEqual(w.gh.length + w.inbox.length, 0);

// 8. отправленных на вчера прогнозов нет — не спрашиваем (и не проверяем GitHub каждые 5 минут)
w = boot('2026-10-17T02:00:00Z');
w.files['team/picks/SENT.md'] = SENT.split('\n').slice(0, 3).join('\n');
assert.strictEqual(w.tick(), 'нет прогнозов');
assert.strictEqual(w.of('sendMessage').length, 0);
w.ctx.teamFile_ = () => { throw new Error('не должен ходить в GitHub'); };
assert.strictEqual(w.tick(), '');

// 9. «Прогноз: …» без открытого опроса — не перехватываем
w = boot('2026-10-16T02:00:00Z');
w.say('Прогноз: победа СКА');
assert.strictEqual(w.state(), null);
assert.ok(!w.of('sendMessage').some(c => /Записал/.test(c.payload.text || '')));
console.log('ok');
