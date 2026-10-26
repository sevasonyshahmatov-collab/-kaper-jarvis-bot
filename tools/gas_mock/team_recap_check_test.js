/* Проверка сверки ставок перед утренними итогами (apps-script/project/Код.js: recapCheckSend_, recapCheckCallback_,
 * recapFixTake_, напоминание в recapAutoTick_) на макете Apps Script (владелец 26.10): в 08:30 МСК — список ставок из записей
 * PMW_ (окно 08:00 вчера – 08:00 сегодня) с кнопками; «Всё верно» → один запуск recap_ask с этими строками; «Поправить» →
 * ответ владельца списком → запуск с его строками; повторное нажатие не дублирует; без записей — «Без итогов»; без ответа
 * до 12:00 — одно напоминание. Telegram и GitHub (запуск itogi.yml) подменены записью.
 *   node tools/gas_mock/team_recap_check_test.js        → «ok», иначе первая ошибка */
const assert = require('assert');
const path = require('path');
const gm = require('./gas_mock');

const ROOT = path.join(__dirname, '..', '..');
const CHAT = 777, BOT = { id: 42, is_bot: true }, OWNER = { id: 1 };
const DAY = '2026-10-16';
const msk = s => new Date(s + ':00+03:00').getTime();
const rec = (pid, start, home, away, pick, kef, ch) => ['PMW_' + pid, JSON.stringify({ pid, league: /^НХЛ/.test(home) ? 'NHL' : 'KHL',
  home, away, start: msk(start), pick, kef, ch, st: 'sent' })];
const PMW = Object.fromEntries([
  rec('1510-3', '2026-10-16T02:00', 'Чикаго', 'Монреаль', 'тотал больше 5,5', '1.85', 503),
  rec('1510-1', '2026-10-15T16:30', 'Лада', 'СКА', 'победа СКА в основное время', '2.10', 501),
  rec('1510-2', '2026-10-15T19:30', 'Спартак', 'Шанхайские Драконы', 'индивидуальный тотал Спартака больше 2,5', '1,85', 502),
  rec('1510-9', '2026-10-15T07:30', 'Сибирь', 'Авангард', 'победа Сибири', '2,40', 509),     // до 08:00 вчера — не в окне
  rec('1610-1', '2026-10-16T12:30', 'Адмирал', 'Спартак', 'победа Спартака', '1,95', 601),    // сегодня днём — не в окне
  rec('1410-1', '2026-10-14T19:00', 'Ак Барс', 'Салават Юлаев', 'тотал меньше 4,5', '1,80', 401)
]);

let nextId = 900;                                                    // номера сообщений бота — сквозные по всем «запускам»
/** Макет таблицы на момент «ЧЧ:ММ» МСК дня DAY; props — свойства скрипта с прошлого «запуска». */
function at(hm, props, ghCode) {
  const env = gm.makeEnv({ now: new Date(msk(DAY + 'T' + hm)).toISOString(), cache: true });
  gm.load(env, [path.join(ROOT, 'apps-script/project/Код.js')]);
  Object.assign(env.props, props || {}, { GITHUB_TOKEN: 'x', TEAM_OWNER_CHAT: String(CHAT) });
  const ctx = env.ctx, w = { env, ctx, calls: [], inbox: [], gh: [], ghCode: ghCode || 204 };
  ctx.tgRaw_ = (method, payload) => { w.calls.push({ method, payload: JSON.parse(JSON.stringify(payload)) }); return { ok: true, result: { message_id: nextId++ } }; };
  ctx.teamAppend_ = (p, line) => { w.inbox.push(line); };
  ctx.teamFile_ = () => { throw new Error('сверке файлы репозитория не нужны'); };
  ctx.itogiGithub_ = (method, url, body) => {
    w.gh.push({ method, url, body: JSON.parse(JSON.stringify(body || null)) });
    return { getResponseCode: () => w.ghCode, getContentText: () => '{"message":"Resource not accessible by personal access token"}' };
  };
  ctx.tgIsChannelAdmin_ = () => true;
  ctx.botEnsureCommands_ = () => {};
  let upd = 1;
  w.of = m => w.calls.filter(c => c.method === m);
  w.toast = () => (w.calls.find(c => c.method === 'answerCallbackQuery') || { payload: {} }).payload;
  w.press = (data, mid) => { w.calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, callback_query: { id: 'q' + upd, from: OWNER, data,
    message: { message_id: mid, chat: { id: CHAT, type: 'private' }, from: BOT, text: 'Сверка перед итогами' } } }); };
  w.reply = (text, mid) => { w.calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, message: { message_id: 5000 + upd, chat: { id: CHAT, type: 'private' },
    from: OWNER, text, reply_to_message: { message_id: mid, chat: { id: CHAT, type: 'private' }, from: BOT, text: '…' } } }); };
  w.tick = () => { w.calls.length = 0; return ctx.recapAutoTick_(); };
  w.state = () => JSON.parse(env.props['RECAP_AUTO_' + DAY] || 'null');
  w.payloads = () => w.gh.map(g => JSON.parse(g.body.inputs.payload));
  w.props = () => Object.assign({}, env.props);
  return w;
}
const DONE = { morning: JSON.stringify({ day: DAY, greet: '06:00' }) };      // утро уже запущено — в тиках только сверка
const base = extra => Object.assign({ ['RECAP_AUTO_' + DAY]: DONE.morning }, PMW, extra || {});
const kbData = m => m.payload.reply_markup.inline_keyboard.map(r => r.map(b => [b.text, b.callback_data]));

// 0. правка поста в боте обновляет запись PMW_ — в сверку идёт исправленная ставка (23.10: «больше» вместо «меньше»)
let w = at('08:25', base());
assert.strictEqual(w.tick(), '');                                   // 08:25 — рано
assert.strictEqual(w.calls.length + w.gh.length, 0);
let pm = JSON.parse(w.env.props['PMW_1510-3']); pm.st = 'wait'; w.env.props['PMW_1510-3'] = JSON.stringify(pm);
w.ctx.pmEditSync_(CHAT, 300, 503, null, 'НХЛ · 16 октября · 02:00 МСК\nЧикаго — Монреаль\n\nПрогноз: тотал меньше 5,5\nКэф: 1,90');
pm = JSON.parse(w.env.props['PMW_1510-3']);
assert.deepStrictEqual([pm.pick, pm.kef], ['тотал меньше 5,5', '1,90']);
const props0 = w.props();

// 1. 08:30 — сверка: список по времени, только окно 08:00 вчера – 08:00 сегодня, кнопки tm|… до 64 байт; в GitHub — ничего
w = at('08:30', props0);
assert.strictEqual(w.tick(), 'запуск: recap');
assert.strictEqual(w.gh.length, 0);
let sm = w.of('sendMessage');
assert.strictEqual(sm.length, 1);
assert.strictEqual(sm[0].payload.chat_id, String(CHAT));
assert.ok(!sm[0].payload.parse_mode);
const lines = sm[0].payload.text.split('\n');
assert.strictEqual(lines[0], 'Сверка перед итогами за 15 октября');
assert.deepStrictEqual(lines.filter(l => /^\d+\. /.test(l)), [
  '1. Лада — СКА: победа СКА в основное время · кэф 2,10',
  '2. Спартак — Шанхайские Драконы: индивидуальный тотал Спартака больше 2,5 · кэф 1,85',
  '3. Чикаго — Монреаль: тотал меньше 5,5 · кэф 1,90']);
assert.deepStrictEqual(kbData(sm[0]), [[['✅ Всё верно — собрать итоги', 'tm|rck||2026-10-16']], [['✏️ Поправить', 'tm|rfx||2026-10-16']]]);
kbData(sm[0]).flat().forEach(b => assert.ok(Buffer.byteLength(b[1]) <= 64));
const MID = 900;
assert.deepStrictEqual([w.state().recap, w.state().check, w.state().mid, w.state().greet], ['08:30', 'sent', MID, '06:00']);
assert.strictEqual(w.tick(), '');                                   // второй раз за день — нет
assert.strictEqual(w.calls.length, 0);
const props1 = w.props();
w = at('10:00', props1);
assert.strictEqual(w.tick(), '');
assert.strictEqual(w.calls.length + w.gh.length, 0);

// 2. «Всё верно» — один запуск recap_ask со строками сверки; кнопки → «Итоги собираются…»; повторное нажатие не дублирует
w = at('08:41', props1);
w.press('tm|rck||2026-10-16', MID);
assert.strictEqual(w.gh.length, 1);
assert.strictEqual(w.gh[0].url, '/repos/sevasonyshahmatov-collab/-kaper-jarvis-bot/actions/workflows/itogi.yml/dispatches');
assert.strictEqual(w.gh[0].body.ref, 'claude/project-migration-old-account-6e31vz');
assert.deepStrictEqual(w.payloads()[0], { kind: 'team', job: 'team/out/2026-10-16/recap_ask.json', day: DAY, pids: [], at: '2026-10-16 08:41',
  free: ['Прогноз: Лада — СКА: победа СКА в основное время, кэф 2,10',
    'Прогноз: Спартак — Шанхайские Драконы: индивидуальный тотал Спартака больше 2,5, кэф 1,85',
    'Прогноз: Чикаго — Монреаль: тотал меньше 5,5, кэф 1,90'] });
let ed = w.of('editMessageReplyMarkup');
assert.ok(ed.length === 1 && ed[0].payload.message_id === MID && ed[0].payload.reply_markup.inline_keyboard[0][0].text === '⏳ Итоги собираются…');
assert.strictEqual(w.toast().text, 'Собираю итоги — пришлю сюда');
assert.strictEqual(w.state().check, 'ok');
w.press('tm|rck||2026-10-16', MID);                                  // второе нажатие (старые кнопки) — без запуска
assert.strictEqual(w.gh.length, 1);
assert.strictEqual(w.toast().text, 'Итоги за 15 октября уже собираются');
w.press('tm|rsk||2026-10-16', MID);
assert.strictEqual(w.gh.length, 1);
assert.strictEqual(w.state().check, 'ok');
w = at('12:30', w.props());                                          // ответил — напоминания нет
assert.strictEqual(w.tick(), '');
assert.strictEqual(w.calls.length, 0);
assert.strictEqual(w.inbox.length, 0, 'сверка ничего не пишет в INBOX');

// 3. GitHub не принял «Всё верно» — сообщение с причиной, сверка ждёт; со второй попытки ушло
w = at('08:45', props1, 403);
w.press('tm|rck||2026-10-16', MID);
assert.ok(w.toast().show_alert && /^Итоги не запустились: GitHub ответил 403/.test(w.toast().text) && w.toast().text.length <= 200);
assert.strictEqual(w.state().check, 'sent');
assert.strictEqual(w.of('editMessageReplyMarkup').length, 0);
w.ghCode = 204;
w.press('tm|rck||2026-10-16', MID);
assert.strictEqual(w.gh.length, 2);
assert.strictEqual(w.state().check, 'ok');

// 4. «Поправить» → список для копирования с force_reply → ответ владельца → запуск с его строками и «Подтверждаю»
w = at('08:50', props1);
w.press('tm|rfx||2026-10-16', MID);
assert.strictEqual(w.gh.length, 0);
sm = w.of('sendMessage');
assert.strictEqual(sm.length, 1);
assert.strictEqual(sm[0].payload.reply_to_message_id, MID);
assert.strictEqual(sm[0].payload.parse_mode, 'HTML');
assert.deepStrictEqual(sm[0].payload.reply_markup, { force_reply: true, input_field_placeholder: 'по одной ставке в строке' });
assert.ok(/^✏️ Ставки за 15 октября: пришлите полный список ответом на это сообщение, по одной ставке в строке/.test(sm[0].payload.text));
assert.ok(sm[0].payload.text.endsWith('<pre>Лада — СКА: победа СКА в основное время, кэф 2,10\n' +
  'Спартак — Шанхайские Драконы: индивидуальный тотал Спартака больше 2,5, кэф 1,85\nЧикаго — Монреаль: тотал меньше 5,5, кэф 1,90</pre>'), sm[0].payload.text);
const ASK = w.state().asks[0];
assert.ok(ASK !== MID && w.state().asks.length === 1);
assert.strictEqual(w.state().check, 'sent');
w.reply('1. Лада — СКА: победа СКА в основное время, кэф 2,10\n\nЧикаго — Монреаль: тотал больше 5,5 · кэф 1,85\n' +
  'Прогноз: Динамо Москва — ЦСКА: победа ЦСКА, кэф 2,05', ASK);
assert.deepStrictEqual(w.payloads(), [{ kind: 'team', job: 'team/out/2026-10-16/recap_ask.json', day: DAY, pids: [], at: '2026-10-16 08:50',
  free: ['Прогноз: Лада — СКА: победа СКА в основное время, кэф 2,10', 'Прогноз: Чикаго — Монреаль: тотал больше 5,5, кэф 1,85',
    'Прогноз: Динамо Москва — ЦСКА: победа ЦСКА, кэф 2,05'] }]);
sm = w.of('sendMessage');
assert.strictEqual(sm.length, 1);
assert.strictEqual(sm[0].payload.text, '✅ Подтверждаю: итоги за 15 октября по вашему списку — пришлю сюда.\n' +
  '1. Лада — СКА: победа СКА в основное время, кэф 2,10\n2. Чикаго — Монреаль: тотал больше 5,5, кэф 1,85\n3. Динамо Москва — ЦСКА: победа ЦСКА, кэф 2,05');
ed = w.of('editMessageReplyMarkup');
assert.ok(ed.length === 1 && ed[0].payload.message_id === MID && ed[0].payload.reply_markup.inline_keyboard[0][0].text === '⏳ Итоги собираются…');
assert.strictEqual(w.state().check, 'fixed');
w.press('tm|rck||2026-10-16', MID);                                  // после исправления «Всё верно» не запускает
assert.strictEqual(w.gh.length, 1);
assert.strictEqual(w.inbox.length, 0, 'ответ на сверку не уходит в INBOX как «поправить»');
w.reply('случайное сообщение без ответа', 12345);                   // ответ на другое сообщение — не сверка
assert.strictEqual(w.gh.length, 1);

// 4б. ответ прямо на саму сверку (не на «✏️ Ставки…») — тоже исправленный список; пустые строки не шлём
w = at('09:00', props1);
w.reply(' \n ', MID);
assert.strictEqual(w.gh.length, 0);
w.reply('Чикаго — Монреаль: тотал меньше 5,5, кэф 1,90', MID);
assert.deepStrictEqual(w.payloads()[0].free, ['Прогноз: Чикаго — Монреаль: тотал меньше 5,5, кэф 1,90']);
assert.strictEqual(w.state().check, 'fixed');

// 5. записей нет — «Вчера прогнозов в канале не нашёл»: «Прислать свои ставки» / «Без итогов»
w = at('08:30', { ['RECAP_AUTO_' + DAY]: DONE.morning, 'PMW_1610-1': PMW['PMW_1610-1'] });
assert.strictEqual(w.tick(), 'запуск: recap');
sm = w.of('sendMessage');
assert.ok(/^Сверка перед итогами за 15 октября\nВчера прогнозов в канале не нашёл/.test(sm[0].payload.text), sm[0].payload.text);
assert.deepStrictEqual(kbData(sm[0]), [[['✏️ Прислать свои ставки', 'tm|rfx||2026-10-16']], [['Без итогов', 'tm|rsk||2026-10-16']]]);
const props5 = w.props();
w.press('tm|rfx||2026-10-16', MID);                                  // пример строки вместо списка
assert.ok(/Например:\n<pre>Спартак — Шанхайские Драконы: индивидуальный тотал Спартака больше 2,5, кэф 1,85<\/pre>$/.test(w.of('sendMessage')[0].payload.text));
w = at('08:35', props5);
w.press('tm|rsk||2026-10-16', MID);
assert.strictEqual(w.gh.length, 0);
assert.strictEqual(w.state().check, 'skip');
assert.strictEqual(w.of('editMessageReplyMarkup')[0].payload.reply_markup.inline_keyboard[0][0].text, 'Без итогов за 15 октября');
assert.strictEqual(w.toast().text, 'Ок, итогов за 15 октября не будет');
w.press('tm|rck||2026-10-16', MID);
w.press('tm|rsk||2026-10-16', MID);
assert.strictEqual(w.gh.length, 0);
assert.strictEqual(w.toast().text, 'Уже отмечено: без итогов за 15 октября');
w = at('12:30', w.props());
assert.strictEqual(w.tick(), '');

// 6. не ответил до 12:00 — одно напоминание ответом на сверку, итоги сами не запускаются
w = at('11:55', props1);
assert.strictEqual(w.tick(), '');
w = at('12:00', props1);
assert.strictEqual(w.tick(), 'напоминание');
sm = w.of('sendMessage');
assert.strictEqual(sm.length, 1);
assert.deepStrictEqual(sm[0].payload.reply_parameters, { message_id: MID, allow_sending_without_reply: true });
assert.ok(/^⏰ Итоги за 15 октября ещё не собраны: сверка ждёт ответа/.test(sm[0].payload.text));
assert.strictEqual(w.gh.length, 0);
assert.strictEqual(w.tick(), '');
w = at('15:00', w.props());
assert.strictEqual(w.tick(), '');
assert.strictEqual(w.calls.length + w.gh.length, 0);
const late = Object.assign(base(), { ['RECAP_AUTO_' + DAY]: JSON.stringify(Object.assign(JSON.parse(props1['RECAP_AUTO_' + DAY]),
  { at: msk(DAY + 'T11:50') })) });
w = at('12:00', late);                                               // сверка ушла в 11:50 — напоминание не раньше 12:20
assert.strictEqual(w.tick(), '');
w = at('12:20', late);
assert.strictEqual(w.tick(), 'напоминание');

// 7. кнопка устаревшей сверки (состояния дня нет) — ничего не запускает
w = at('09:00', {});
w.press('tm|rck||2026-10-08', MID);
assert.ok(w.toast().show_alert && /^Сверка устарела/.test(w.toast().text));
assert.strictEqual(w.gh.length, 0);
console.log('ok');
