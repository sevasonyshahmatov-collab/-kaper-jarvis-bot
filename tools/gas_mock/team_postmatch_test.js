/* Проверка послематчевых постов (apps-script/project/Код.js: pm*): прогноз вышел в канал → запись PMW_, после финала —
 * запуск задания postmatch_auto, «Опубликовать» под итогом (ММДД-Nr) — ответом на пост прогноза.
 *   node tools/gas_mock/team_postmatch_test.js        → «ok», иначе первая ошибка */
const assert = require('assert');
const path = require('path');
const gm = require('./gas_mock');

const ROOT = path.join(__dirname, '..', '..');
const NOW = Date.UTC(2026, 9, 16, 9, 0);                                        // 16.10 12:00 МСК
const env = gm.makeEnv({ now: new Date(NOW).toISOString(), cache: true });
gm.load(env, [path.join(ROOT, 'apps-script/project/Код.js')]);
const ctx = env.ctx, calls = [], disp = [];
let nextId = 9000;
ctx.tgRaw_ = (method, payload) => {
  const p = JSON.parse(JSON.stringify(payload));
  calls.push({ method, payload: p });
  return { ok: true, result: { message_id: nextId++ } };
};
ctx.teamAppend_ = () => {};
ctx.tgIsChannelAdmin_ = () => true;
ctx.botEnsureCommands_ = () => {};
ctx.recapDispatch_ = (payload) => { disp.push(JSON.parse(JSON.stringify(payload))); return { ok: true }; };
let finished = false;
ctx.pmFinished_ = () => finished;

const CHAT = 777, BOT = { id: 42, is_bot: true }, OWNER = { id: 1 };
const kb = pid => ({ inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pub|' + pid }]] });
let upd = 1;
const press = (data, message) => { calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, callback_query: { id: 'q' + upd, from: OWNER, data, message } }); };
const of = m => calls.filter(c => c.method === m);
const pick = { message_id: 600, chat: { id: CHAT, type: 'private' }, from: BOT, animation: {},
  caption: 'КХЛ · 16 октября · 12:30 МСК\nАдмирал — Спартак\n\nПрогноз: победа Спартака в основное время\nКэф: 1,95\n\nТекст поста…',
  caption_entities: [], reply_markup: kb('1610-1') };

// 1. разбор поста прогноза
const w0 = ctx.pmParse_(pick.caption);
assert.deepStrictEqual([w0.league, w0.home, w0.away, w0.pick, w0.kef, w0.start],
  ['KHL', 'Адмирал', 'Спартак', 'победа Спартака в основное время', '1,95', Date.UTC(2026, 9, 16, 9, 30)]);
assert.strictEqual(ctx.pmParse_('Прогнозы КХЛ на 16 октября — 4 матча'), null);

// 2. «Опубликовать» за 30 минут до матча — сразу в канал, запись PMW_ с номером поста в канале
press('tm|pub|1610-1', pick);
const cp = of('copyMessage')[0];
assert.ok(cp && !cp.payload.reply_parameters, 'прогноз — без ответа');
let w = JSON.parse(env.props['PMW_1610-1']);
assert.strictEqual(w.ch, 9000);
assert.strictEqual(w.st, 'wait');

// 3. рано — ничего; финала нет — ничего; финал — запуск задания
ctx.pmTick_();
assert.strictEqual(disp.length, 0);
w.start = NOW - 130 * 60000;                                                    // «прошло 2 ч 10 мин с начала»
env.props['PMW_1610-1'] = JSON.stringify(w);
ctx.pmTick_();
assert.strictEqual(disp.length, 0);
finished = true;
ctx.pmTick_();
assert.strictEqual(disp.length, 1);
assert.strictEqual(disp[0].job, 'team/out/2026-10-16/postmatch_auto.json');
assert.deepStrictEqual(disp[0].pm, { pid: '1610-1', league: 'KHL', home: 'Адмирал', away: 'Спартак', start: '2026-10-16 09:50',
  pick: 'победа Спартака в основное время', kef: '1,95', ch: 9000 });
ctx.pmTick_();
assert.strictEqual(disp.length, 1, 'второй раз не запускаем');

// 4. «Опубликовать» под итогом — копия в канал ответом на пост прогноза, сама итог не отслеживается
const res = { message_id: 700, chat: { id: CHAT, type: 'private' }, from: BOT, animation: {},
  caption: '✅ Адмирал — Спартак 1:5\n\n🎯 Ставка: победа Спартака в основное время', caption_entities: [], reply_markup: kb('1610-1r') };
press('tm|pub|1610-1r', res);
const cp2 = of('copyMessage')[0];
assert.ok(cp2, 'итог опубликован сразу');
assert.deepStrictEqual(cp2.payload.reply_parameters, { message_id: 9000, allow_sending_without_reply: true });
assert.ok(!env.props['PMW_1610-1r']);

// 5. НХЛ, пост по расписанию: запись появляется при выходе
const nhl = { message_id: 610, chat: { id: CHAT, type: 'private' }, from: BOT, animation: {},
  caption: 'НХЛ · 17 октября · 04:00 МСК\nКолорадо — Питтсбург\n\nПрогноз: фора Питтсбурга +1,5\nКэф: 1,75', caption_entities: [], reply_markup: kb('1610-5') };
press('tm|pub|1610-5', nhl);
assert.strictEqual(of('copyMessage').length, 0, 'НХЛ за 4 часа — пока на выходе');
const sk = Object.keys(env.props).find(k => /^TMSCHED_/.test(k));
const s = JSON.parse(env.props[sk]); s.at = NOW - 1000; env.props[sk] = JSON.stringify(s);
calls.length = 0;
ctx.teamSchedTick_();
assert.strictEqual(of('copyMessage').length, 1);
w = JSON.parse(env.props['PMW_1610-5']);
assert.deepStrictEqual([w.league, w.home, w.away, w.pick], ['NHL', 'Колорадо', 'Питтсбург', 'фора Питтсбурга +1,5']);
console.log('ok');
