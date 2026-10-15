/* Проверка выхода постов команды за полтора часа до матча (apps-script/project/Код.js: teamSched*, «Опубликовать»)
 * на макете Apps Script: сейчас по макету 15.10 10:00 МСК; Telegram подменён записью вызовов.
 *   node tools/gas_mock/team_sched_test.js        → «ok», иначе первая ошибка */
const assert = require('assert');
const path = require('path');
const gm = require('./gas_mock');

const ROOT = path.join(__dirname, '..', '..');
const NOW = Date.UTC(2026, 9, 15, 7, 0);                                        // 10:00 МСК
const env = gm.makeEnv({ now: new Date(NOW).toISOString(), cache: true });
gm.load(env, [path.join(ROOT, 'apps-script/project/Код.js')]);
const ctx = env.ctx, calls = [], inbox = [];
let nextId = 5000, fail = null;
ctx.tgRaw_ = (method, payload) => {
  const p = JSON.parse(JSON.stringify(payload)), err = fail && fail(method, p);
  calls.push({ method, payload: p, err, id: err ? null : nextId });
  return err ? { ok: false, description: err } : { ok: true, result: method === 'copyMessages' ? p.message_ids.map(() => ({ message_id: nextId++ })) : { message_id: nextId++ } };
};
ctx.teamAppend_ = (p, line) => { inbox.push(line); };
ctx.tgIsChannelAdmin_ = () => true;
ctx.botEnsureCommands_ = () => {};

const CHAT = 777, BOT = { id: 42, is_bot: true }, OWNER = { id: 1 };
const kb = pid => ({ inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pub|' + pid }],
  [{ text: 'Редактировать', callback_data: 'tm|edit|' + pid }, { text: 'Не надо', callback_data: 'tm|no|' + pid }]] });
const post = (id, head, pid, markup) => ({ message_id: id, chat: { id: CHAT, type: 'private' }, from: BOT, photo: [{}],
  caption: head + '\nТорпедо — Динамо Москва\n\nПрогноз: итоговая победа Торпедо\nКэф: 1,67', caption_entities: [], reply_markup: markup || kb(pid) });
let upd = 1;
const press = (data, message) => { calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, callback_query: { id: 'q' + upd, from: OWNER, data, message } }); };
const of = m => calls.filter(c => c.method === m && !c.err);
const toast = () => (calls.find(c => c.method === 'answerCallbackQuery') || { payload: {} }).payload;
const sched = id => JSON.parse(env.props['TMSCHED_' + CHAT + '_' + id] || 'null');
const tick = () => { calls.length = 0; ctx.teamSchedTick_(); };
const due = id => { const s = sched(id); s.at = NOW - 60000; env.props['TMSCHED_' + CHAT + '_' + id] = JSON.stringify(s); };
const TOMORROW = 'КХЛ · 16 октября · 19:00 МСК';

// 1. «Опубликовать» под постом на завтра — на выход 16.10 в 17:30 МСК, в канал пока ничего
press('tm|pub|1510-3', post(600, TOMORROW, '1510-3'));
assert.strictEqual(of('copyMessage').length, 0);
assert.ok(/Выйдет 16\.10 в 17:30 МСК — за полтора часа до матча/.test(toast().text), toast().text);
let s = sched(600);
assert.ok(s && s.at === Date.UTC(2026, 9, 16, 14, 30) && s.start === Date.UTC(2026, 9, 16, 16, 0) && s.pid === '1510-3');
const skb = of('editMessageReplyMarkup')[0].payload.reply_markup;
assert.strictEqual(skb.inline_keyboard[0][0].text, '⏰ Выйдет 16.10 в 17:30 · опубликовать сейчас');
assert.deepStrictEqual(skb.inline_keyboard.flat().map(b => b.callback_data), ['tm|pub|1510-3|now', 'tm|edit|1510-3', 'tm|unsched|1510-3']);
assert.ok(inbox.some(l => /запланировано владельцем: 1510-3 «КХЛ · 16 октября · 19:00 МСК» — выход 16\.10 17:30 МСК/.test(l)));

// 2. время не пришло — проверка раз в 5 минут ничего не публикует
tick();
assert.strictEqual(of('copyMessage').length, 0);

// 3. правка, пока пост стоит на выходе: кнопки расписания остаются, подсказка о выходе
press('tm|edit|1510-3', post(600, TOMORROW, '1510-3', skb));
assert.ok(of('sendMessage').some(c => /стоит на выходе/.test(c.payload.text)));
const copy = of('sendMessage')[1];
calls.length = 0;
ctx.gameHandleUpdate_({ update_id: upd++, message: { message_id: 7000, chat: { id: CHAT, type: 'private' }, from: OWNER,
  text: copy.payload.text.replace('1,67', '1,70'), reply_to_message: { message_id: copy.id, chat: { id: CHAT }, from: BOT, text: copy.payload.text } } });
const ed = of('editMessageCaption')[0];
assert.ok(ed && ed.payload.caption.includes('1,70'));
assert.deepStrictEqual(ed.payload.reply_markup, skb);

// 4. время пришло — пост уходит в канал (последний вариант черновика), «✅ Опубликовано в 10:00», номер в канале запомнен
due(600);
tick();
const cp = of('copyMessage');
assert.ok(cp.length === 1 && cp[0].payload.chat_id === '@jarvibet' && cp[0].payload.message_id === 600);
assert.ok(of('editMessageReplyMarkup').some(c => c.payload.reply_markup.inline_keyboard[0][0].text === '✅ Опубликовано в 10:00'));
assert.ok(!sched(600) && JSON.parse(env.props['TMPUB_' + CHAT + '_600']).ch === cp[0].id);
assert.ok(inbox.some(l => /опубликовано владельцем \(по расписанию\): 1510-3/.test(l)));

// 5. «Отменить выход» — обычные кнопки обратно, расписание снято
press('tm|pub|1510-4', post(601, TOMORROW, '1510-4'));
press('tm|unsched|1510-4', post(601, TOMORROW, '1510-4', ctx.teamSchedKb_(sched(601))));
assert.ok(!sched(601) && /Выход отменён/.test(toast().text));
assert.deepStrictEqual(of('editMessageReplyMarkup')[0].payload.reply_markup, kb('1510-4'));

// 6. «опубликовать сейчас» на стоящем посте — сразу и расписание снято
press('tm|pub|1510-5', post(602, TOMORROW, '1510-5'));
press('tm|pub|1510-5|now', post(602, TOMORROW, '1510-5', ctx.teamSchedKb_(sched(602))));
assert.ok(of('copyMessage').length === 1 && !sched(602) && /Опубликовано в канал/.test(toast().text));

// 7. до матча меньше полутора часов — сразу; в шапке нет времени — сразу; матч начался — отказ
press('tm|pub|1510-6', post(603, 'КХЛ · 15 октября · 11:00 МСК', '1510-6'));
assert.ok(of('copyMessage').length === 1 && !sched(603));
press('tm|pub|1510-7', post(604, 'КХЛ · итоги дня · среда, 14 октября', '1510-7'));
assert.ok(of('copyMessage').length === 1);
press('tm|pub|1510-8', post(605, 'КХЛ · 15 октября · 09:30 МСК', '1510-8'));
assert.ok(of('copyMessage').length === 0 && toast().show_alert && /Матч уже начался/.test(toast().text));

// 8. «Не надо» снимает выход
press('tm|pub|1510-9', post(606, TOMORROW, '1510-9'));
press('tm|no|1510-9', post(606, TOMORROW, '1510-9', ctx.teamSchedKb_(sched(606))));
assert.ok(!sched(606));

// 9. не успели до начала матча (например, таблица не работала) — не публикуем, пост остаётся черновиком
press('tm|pub|1510-10', post(607, TOMORROW, '1510-10'));
s = sched(607); s.at = NOW - 3 * 3600000; s.start = NOW - 3600000; env.props['TMSCHED_' + CHAT + '_607'] = JSON.stringify(s);
tick();
assert.ok(of('copyMessage').length === 0 && !sched(607) && of('sendMessage').some(c => /Не успел опубликовать до начала матча/.test(c.payload.text)));

// 10. Telegram не принял три раза — пост остаётся черновиком с объяснением
press('tm|pub|1510-11', post(608, TOMORROW, '1510-11'));
due(608);
fail = m => (m === 'copyMessage' ? 'Bad Request: chat not found' : null);
tick(); tick();
assert.ok(sched(608) && sched(608).fails === 2);
tick();
fail = null;
assert.ok(!sched(608) && of('sendMessage').some(c => /Не получилось опубликовать по расписанию: Bad Request: chat not found/.test(c.payload.text)));

// 11. альбом: кнопки отдельным сообщением, при выходе — весь альбом
const albumKb = { inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pubm|1510-12|300|3' }]] };
press('tm|pubm|1510-12|300|3', { message_id: 609, chat: { id: CHAT }, from: BOT, text: '1510-12 — альбом выше: ' + TOMORROW, reply_markup: albumKb });
assert.strictEqual(sched(609).album.first, 300);
due(609);
tick();
const cps = of('copyMessages');
assert.ok(cps.length === 1 && JSON.stringify(cps[0].payload.message_ids) === '[300,301,302]');

// 12. ночью (23:00–08:00 МСК) пост выходит без звука, днём — со звуком (по макету сейчас 10:00 МСК)
assert.strictEqual(cps[0].payload.disable_notification, false);
const night = gm.makeEnv({ now: new Date(Date.UTC(2026, 9, 15, 23, 30)).toISOString(), cache: true });   // 02:30 МСК
gm.load(night, [path.join(ROOT, 'apps-script/project/Код.js')]);
const nc = [];
night.ctx.tgRaw_ = (method, payload) => { nc.push({ method, payload }); return { ok: true, result: { message_id: 1 } }; };
night.ctx.teamPublishNow_(CHAT, 700, null);
assert.ok(nc[0].method === 'copyMessage' && nc[0].payload.disable_notification === true);
console.log('ok');
