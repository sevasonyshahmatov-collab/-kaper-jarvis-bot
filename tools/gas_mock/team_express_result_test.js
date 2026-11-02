/* Проверка итога экспресса и сверки итогов дня сразу после финала (apps-script/project/Код.js: expressWatchSave_, expressTick_,
 * pmReplyTo_, recapFinalTick_, recapCheckRun_ для футбола) на макете Apps Script (владелец 01.11).
 *   node tools/gas_mock/team_express_result_test.js        → «ok», иначе первая ошибка */
const assert = require('assert');
const path = require('path');
const gm = require('./gas_mock');

const ROOT = path.join(__dirname, '..', '..');
const CHAT = 777, BOT = { id: 42, is_bot: true }, OWNER = { id: 1 };
const msk = s => new Date(s + ':00+03:00').getTime();
let nextId = 900;
function at(iso, props) {
  const env = gm.makeEnv({ now: new Date(msk(iso)).toISOString(), cache: true });
  gm.load(env, [path.join(ROOT, 'apps-script/project/Код.js')]);
  Object.assign(env.props, props || {}, { GITHUB_TOKEN: 'x', TEAM_OWNER_CHAT: String(CHAT) });
  const ctx = env.ctx, w = { env, ctx, calls: [], disp: [], log: [], fin: {} };
  ctx.tgRaw_ = (method, payload) => { w.calls.push({ method, payload: JSON.parse(JSON.stringify(payload)) }); return { ok: true, result: { message_id: nextId++ } }; };
  ctx.teamAppend_ = (p, line) => { w.log.push([p, line]); };
  ctx.tgIsChannelAdmin_ = () => true;
  ctx.botEnsureCommands_ = () => {};
  ctx.recapDispatch_ = payload => { w.disp.push(JSON.parse(JSON.stringify(payload))); return { ok: true }; };
  ctx.pmFinished_ = g => w.fin[g.home] !== false;                 // по умолчанию все матчи доиграны
  w.of = m => w.calls.filter(c => c.method === m);
  w.props = () => env.props;
  let upd = 1;
  w.press = (data, mid, text) => { w.calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, callback_query: { id: 'q' + upd, from: OWNER, data,
    message: { message_id: mid, chat: { id: CHAT, type: 'private' }, from: BOT, animation: {}, caption: text || 'x', caption_entities: [] } } }); };
  return w;
}
const COUPON = 'НХЛ · 31 октября – 1 ноября · экспресс\n\n1. Лос-Анджелес — Баффало, 23:00 МСК\nфора Лос-Анджелеса +2,5 · 1,22\n' +
  '2. Монреаль — Питтсбург, 1 ноября, 02:00 МСК\nинд. тотал Питтсбурга больше 1,5 · 1,22\n3. Ванкувер — Торонто, 1 ноября, 02:00 МСК\nинд. тотал Ванкувера больше 1,5 · 1,23\n\nОбщий кэф: 1,83';

// 1. купон → запись EXW_ (номер поста в канале, ноги с датами)
let w = at('2026-10-31T12:00');
w.ctx.expressWatchSave_('3110-e1', COUPON, { message_id: 321 });
let e = JSON.parse(w.props()['EXW_3110-e1']);
assert.strictEqual(e.ch, 321);
assert.strictEqual(e.legs.length, 3);
assert.strictEqual(e.legs[0].start, msk('2026-10-31T23:00'));
assert.strictEqual(e.legs[2].start, msk('2026-11-01T02:00'));
assert.strictEqual(e.league, 'NHL');
assert.strictEqual(w.ctx.pmReplyTo_('3110-e1r'), 321, 'итог — ответом на пост купона');
assert.strictEqual(w.ctx.pmReplyTo_('3110-e1r555'), 555);
assert.strictEqual(w.ctx.expressDay_('3110-e1r'), null, 'итог — не купон: Instagram не запускаем');

// 2. тик: рано — тишина; все ноги доиграны — один запуск; повтор — нет
const props = Object.assign({}, w.props());
w = at('2026-11-01T03:00', props);                              // последняя нога 02:00 + 2 ч 20 мин = 04:20
w.ctx.expressTick_(); assert.strictEqual(w.disp.length, 0, 'рано');
w = at('2026-11-01T04:30', props);
w.fin['Ванкувер'] = false;
w.ctx.expressTick_(); assert.strictEqual(w.disp.length, 0, 'одна нога не доиграна');
w.fin['Ванкувер'] = true;
w.ctx.expressTick_();
assert.deepStrictEqual(w.disp, [{ kind: 'team', job: 'team/out/2026-10-31/express_result_auto.json', day: '2026-10-31', exres: { pid: '3110-e1', ch: 321 } }]);
w.ctx.expressTick_(); assert.strictEqual(w.disp.length, 1, 'один раз на купон');
assert.strictEqual(JSON.parse(w.props()['EXW_3110-e1']).st, 'sent');

// 3. «Опубликовать» под итогом — ответом на пост купона, запись в учёт; Instagram не запускается
w = at('2026-11-01T05:00', w.props());
w.press('tm|pub|3110-e1r321', 800, 'Итог экспресса ✅ Зашёл!\n\nНХЛ · 31 октября – 1 ноября\n\n1. Лос-Анджелес — Баффало 2:3 · фора ✅\n\nОбщий кэф: 1,83');
const cp = w.of('copyMessage');
assert.strictEqual(cp.length, 1);
assert.deepStrictEqual(cp[0].payload.reply_parameters, { message_id: 321, allow_sending_without_reply: true });
assert.ok(w.log.some(l => /EXPRESS_RESULTS\.md/.test(l[0]) && /3110-e1 · ✅ зашёл · кэф 1,83/.test(l[1])), 'учёт');
assert.strictEqual(w.disp.length, 0);

// 4. итоги дня сразу после финала: хоккей (КХЛ + НХЛ) и футбол — отдельно
const rec = (pid, start, lg, home, away, pick, extra) => ['PMW_' + pid, JSON.stringify(Object.assign({ pid, league: lg, home, away, start: msk(start), pick, kef: '1.85', ch: 1, st: 'sent' }, extra || {}))];
const PM = Object.fromEntries([
  rec('3110-1', '2026-10-31T16:30', 'KHL', 'Лада', 'СКА', 'победа СКА'),
  rec('3110-4', '2026-11-01T02:00', 'NHL', 'Детройт', 'Сент-Луис', 'тотал больше 5,5'),
  rec('3110-9', '2026-10-31T18:00', 'FOOT', 'Челси', 'Ливерпуль', 'тотал больше 2,5', { tour: 'АПЛ', st: 'done' }),
  rec('3110-10', '2026-10-31T20:30', 'FOOT', 'Бавария', 'Лейпциг', 'победа Баварии', { tour: 'Бундеслига', st: 'wait' })
]);
w = at('2026-11-01T04:35', PM);
w.ctx.recapFinalTick_();
let sent = w.of('sendMessage');
assert.strictEqual(sent.length, 1, 'хоккей доигран — сверка сразу; футбол ещё не весь — ждёт');
assert.ok(/Сверка перед итогами за 31 октября/.test(sent[0].payload.text) && /Лада — СКА/.test(sent[0].payload.text) && !/Челси/.test(sent[0].payload.text));
assert.strictEqual(sent[0].payload.reply_markup.inline_keyboard[0][0].callback_data, 'tm|rck||2026-11-01');
w.ctx.recapFinalTick_(); assert.strictEqual(w.of('sendMessage').length, 1, 'второй раз не шлёт');
// футбол доигран → своя сверка с ключом …f; «Всё верно» → foot_recap_auto со ставками
const p2 = Object.assign({}, w.props());
p2['PMW_3110-10'] = JSON.stringify(Object.assign(JSON.parse(p2['PMW_3110-10']), { st: 'done' }));
w = at('2026-11-01T05:10', p2);
w.ctx.recapFinalTick_();
sent = w.of('sendMessage');
assert.strictEqual(sent.length, 1);
assert.ok(/Сверка перед итогами футбола/.test(sent[0].payload.text) && /Челси — Ливерпуль/.test(sent[0].payload.text) && !/Лада/.test(sent[0].payload.text));
assert.strictEqual(sent[0].payload.reply_markup.inline_keyboard[0][0].callback_data, 'tm|rck||2026-11-01f');
const mid = JSON.parse(w.props()['RECAP_AUTO_2026-11-01f']).mid;
w.press('tm|rck||2026-11-01f', mid, 'Сверка');
assert.strictEqual(w.disp.length, 1);
assert.strictEqual(w.disp[0].job, 'team/out/2026-11-01/foot_recap_auto.json');
assert.deepStrictEqual(w.disp[0].foot.map(x => [x.tour, x.home, x.start]), [['АПЛ', 'Челси', '2026-10-31 18:00'], ['Бундеслига', 'Бавария', '2026-10-31 20:30']]);
// 08:30 запасной: хоккей и футбол уже сверены — ничего не шлёт
w = at('2026-11-01T08:31', w.props());
w.calls.length = 0; w.ctx.recapAutoTick_();
assert.ok(!w.of('sendMessage').some(c => /Сверка перед итогами/.test(c.payload.text || '')), 'без дублей в 08:30');
// не весь день сыгран / пост ждёт выхода — рано
w = at('2026-10-31T19:00', Object.assign({}, PM, { 'PMW_3110-4': JSON.stringify({ pid: '3110-4', league: 'NHL', home: 'Детройт', away: 'Сент-Луис', start: msk('2026-11-01T02:00'), pick: 'x', st: 'wait' }) }));
w.ctx.recapFinalTick_(); assert.strictEqual(w.of('sendMessage').length, 0, 'НХЛ ещё не сыграна');
console.log('ok');
