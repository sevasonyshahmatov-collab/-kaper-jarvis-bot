/* Проверка утренних запусков без опроса (apps-script/project/Код.js: recapAutoTick_, recapDispatch_, recapAskCallback_)
 * на макете Apps Script: 06:00 МСК — «Начало игрового дня» (morning_greet), 08:30 — итоги из канала (recap_auto), каждое — раз
 * в день; GitHub не принял (403) — одно сообщение владельцу за день; старые кнопки опроса — «Опрос больше не используется».
 * Telegram и GitHub (запуск itogi.yml) подменены записью.
 *   node tools/gas_mock/team_recap_auto_test.js        → «ok», иначе первая ошибка */
const assert = require('assert');
const path = require('path');
const gm = require('./gas_mock');

const ROOT = path.join(__dirname, '..', '..');
const CHAT = 777, BOT = { id: 42, is_bot: true }, OWNER = { id: 1 };
const DAY = '2026-10-16';

/** Макет таблицы на момент iso (UTC); props — свойства скрипта с прошлого «запуска». */
function boot(iso, props, ghCode) {
  const env = gm.makeEnv({ now: iso, cache: true });
  gm.load(env, [path.join(ROOT, 'apps-script/project/Код.js')]);
  Object.assign(env.props, props || {}, { GITHUB_TOKEN: 'x', TEAM_OWNER_CHAT: String(CHAT) });
  const ctx = env.ctx, w = { env, ctx, calls: [], inbox: [], gh: [], ghCode: ghCode || 204 };
  let nextId = 900;
  ctx.tgRaw_ = (method, payload) => { w.calls.push({ method, payload: JSON.parse(JSON.stringify(payload)) }); return { ok: true, result: { message_id: nextId++ } }; };
  ctx.teamAppend_ = (p, line) => { w.inbox.push(line); };
  ctx.teamFile_ = () => { throw new Error('утренним запускам файлы репозитория не нужны'); };
  ctx.itogiGithub_ = (method, url, body) => {
    w.gh.push({ method, url, body: JSON.parse(JSON.stringify(body || null)) });
    return { getResponseCode: () => w.ghCode, getContentText: () => '{"message":"Resource not accessible by personal access token"}' };
  };
  ctx.tgIsChannelAdmin_ = () => true;
  ctx.botEnsureCommands_ = () => {};
  let upd = 1;
  w.of = m => w.calls.filter(c => c.method === m);
  w.toast = () => (w.calls.find(c => c.method === 'answerCallbackQuery') || { payload: {} }).payload;
  w.press = (data, message) => { w.calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, callback_query: { id: 'q' + upd, from: OWNER, data, message } }); };
  w.say = text => { w.calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, message: { message_id: 5000 + upd, chat: { id: CHAT, type: 'private' }, from: OWNER, text } }); };
  w.tick = () => { w.calls.length = 0; return ctx.recapAutoTick_(); };
  w.state = (d) => JSON.parse(env.props['RECAP_AUTO_' + (d || DAY)] || 'null');
  w.payloads = () => w.gh.map(g => JSON.parse(g.body.inputs.payload));
  return w;
}
const at = (hm, props, code) => boot(DAY + 'T' + String(Number(hm.slice(0, 2)) - 3).padStart(2, '0') + ':' + hm.slice(3) + ':00Z', props, code);   // МСК → UTC

// 0. часы — константами; тик подключён к проверке раз в 5 минут (задания — заготовки team/daily/jobs/*.json ветки команды)
let w = at('05:55');
assert.deepStrictEqual([w.ctx.DAILY_GREET_HOUR, w.ctx.DAILY_GREET_MIN, w.ctx.DAILY_RECAP_HOUR, w.ctx.DAILY_RECAP_MIN, w.ctx.DAILY_LAST_HOUR], [6, 0, 8, 30, 12]);
assert.ok(/recapAutoTick_\(\)/.test(w.ctx.liveUpdateAuto_.toString()) && !/recapAskTick_\(\)/.test(w.ctx.liveUpdateAuto_.toString()));

// 1. до 06:00 МСК — ничего
assert.strictEqual(w.tick(), '');
assert.strictEqual(w.calls.length + w.gh.length, 0);
assert.strictEqual(w.state(), null);

// 2. 06:00 — один запуск «Начало игрового дня», в Telegram ничего (посты пришлёт Actions)
w = at('06:00');
assert.strictEqual(w.tick(), 'запуск: greet');
assert.strictEqual(w.gh.length, 1);
assert.strictEqual(w.gh[0].method, 'post');
assert.strictEqual(w.gh[0].url, '/repos/sevasonyshahmatov-collab/-kaper-jarvis-bot/actions/workflows/itogi.yml/dispatches');
assert.strictEqual(w.gh[0].body.ref, 'claude/project-migration-old-account-6e31vz');
assert.deepStrictEqual(w.payloads()[0], { kind: 'team', job: 'team/out/2026-10-16/morning_greet.json', day: DAY });
assert.strictEqual(w.calls.length, 0);
assert.strictEqual(w.tick(), '');                                    // следующий тик — второго запуска нет
assert.strictEqual(w.gh.length, 1);
let props = Object.assign({}, w.env.props);
w = at('08:25', props);                                              // 08:25 — итогам ещё рано, утро уже запущено
assert.strictEqual(w.tick(), '');
assert.strictEqual(w.gh.length, 0);

// 3. 08:30 — один запуск итогов из канала
w = at('08:30', props);
assert.strictEqual(w.tick(), 'запуск: recap');
assert.deepStrictEqual(w.payloads(), [{ kind: 'team', job: 'team/out/2026-10-16/recap_auto.json', day: DAY }]);
assert.strictEqual(w.calls.length, 0);
assert.strictEqual(w.tick(), '');
assert.deepStrictEqual([w.state().greet, w.state().recap], ['06:00', '08:30']);
props = Object.assign({}, w.env.props);
w = at('10:40', props);                                              // позже в тот же день — ничего
assert.strictEqual(w.tick(), '');
assert.strictEqual(w.gh.length, 0);
w = boot('2026-10-17T03:00:00Z', props);                             // назавтра в 06:00 — снова утро (новый день)
assert.strictEqual(w.tick(), 'запуск: greet');
assert.deepStrictEqual(w.payloads(), [{ kind: 'team', job: 'team/out/2026-10-17/morning_greet.json', day: '2026-10-17' }]);

// 4. таблица «проснулась» в 09:10 — оба запуска по порядку, каждый по разу
w = at('09:10');
assert.strictEqual(w.tick(), 'запуск: greet, recap');
assert.deepStrictEqual(w.payloads().map(p => p.job), ['team/out/2026-10-16/morning_greet.json', 'team/out/2026-10-16/recap_auto.json']);
assert.strictEqual(w.tick(), '');
// после полудня пропущенное не догоняем
w = at('12:00');
assert.strictEqual(w.tick(), '');
assert.strictEqual(w.gh.length, 0);

// 5. GitHub ответил 403 — владельцу одно сообщение за день с причиной; бот пробует снова каждые 5 минут
w = at('06:00', {}, 403);
assert.strictEqual(w.tick(), 'ошибка');
let sm = w.of('sendMessage');
assert.strictEqual(sm.length, 1);
assert.strictEqual(sm[0].payload.chat_id, String(CHAT));
assert.ok(/^⚠️ Утренние посты не запустились \(«Начало игрового дня», итоги вчерашних ставок\): GitHub ответил 403 — у токена GITHUB_TOKEN нет права Actions: Read and write/.test(sm[0].payload.text), sm[0].payload.text);
assert.ok(/до 12:00 МСК\. Это сообщение — одно за день\.$/.test(sm[0].payload.text), sm[0].payload.text);
assert.ok(!w.state().greet && w.state().errSent === '06:00');
assert.strictEqual(w.tick(), 'ошибка');                              // тот же запуск таблицы — повтор без сообщения
assert.strictEqual(w.of('sendMessage').length, 0);
props = Object.assign({}, w.env.props);
w = at('08:30', props, 403);                                         // и в 08:30 — два запуска не приняты, сообщения нет
assert.strictEqual(w.tick(), 'ошибка');
assert.strictEqual(w.gh.length, 2);
assert.strictEqual(w.calls.length, 0);
props = Object.assign({}, w.env.props);
w = at('08:35', props, 204);                                         // владелец дал токену право Actions — оба ушли
assert.strictEqual(w.tick(), 'запуск: greet, recap');
assert.strictEqual(w.calls.length, 0);
assert.strictEqual(w.tick(), '');
w = at('06:00', {}, 500);                                            // другой ответ GitHub — текст ошибки в сообщении
w.tick();
assert.ok(/GitHub ответил 500: \{"message"/.test(w.of('sendMessage')[0].payload.text));
w = at('06:00');                                                     // GitHub не подключён — тоже одно сообщение с причиной
w.ctx.itogiGithub_ = () => null;
assert.strictEqual(w.tick(), 'ошибка');
assert.ok(/GitHub не подключён/.test(w.of('sendMessage')[0].payload.text));
assert.strictEqual(w.tick(), 'ошибка');
assert.strictEqual(w.calls.length, 0);

// 6. опрос выключен: в 05:00 вопросов нет; старые кнопки — «Опрос больше не используется»; «Прогноз: …» не перехватываем
w = at('05:00', { 'RECAP_ASK_2026-10-16': JSON.stringify({ day: DAY, items: [{ pid: '1510-1', label: 'Лада — СКА' }], sel: {}, free: [], mid: 950, chat: String(CHAT) }) });
assert.strictEqual(w.ctx.recapAskTick_(), '');
assert.strictEqual(w.tick(), '');
assert.strictEqual(w.calls.length + w.gh.length, 0);
const oldMsg = { message_id: 950, chat: { id: CHAT, type: 'private' }, from: BOT, text: 'Доброе утро! На какие прогнозы вчера ставили?' };
for (const data of ['tm|rat|1510-1|2026-10-16', 'tm|rad||2026-10-16', 'tm|ran||2026-10-16', 'tm|rat|1410-1|2026-10-15']) {
  w.press(data, oldMsg);
  assert.ok(w.toast().show_alert && /^Опрос больше не используется: итоги бот собирает сам из постов канала и присылает около 8:30 МСК$/.test(w.toast().text), data + ' ' + w.toast().text);
  const ed = w.of('editMessageReplyMarkup');
  assert.ok(ed.length === 1 && ed[0].payload.reply_markup.inline_keyboard[0][0].text === 'Опрос больше не используется', data);
}
assert.strictEqual(w.gh.length + w.inbox.length, 0, 'старые кнопки ничего не запускают и не пишут в INBOX');
w.say('Прогноз: победа СКА в основное время, кэф 1,85');
assert.ok(!w.calls.some(c => /Записал/.test(c.payload.text || '')));
assert.deepStrictEqual(JSON.parse(w.env.props['RECAP_ASK_2026-10-16']).free, []);

// 7. старые состояния (опроса и запусков) чистятся через неделю
w = at('06:00', { 'RECAP_ASK_2026-10-01': '{}', 'RECAP_AUTO_2026-10-02': '{}', 'RECAP_AUTO_2026-10-12': '{"day":"2026-10-12"}' });
w.tick();
assert.ok(!('RECAP_ASK_2026-10-01' in w.env.props) && !('RECAP_AUTO_2026-10-02' in w.env.props) && 'RECAP_AUTO_2026-10-12' in w.env.props);
console.log('ok');
