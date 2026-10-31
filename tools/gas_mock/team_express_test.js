/* Проверка купона «Экспресс» (apps-script/project/Код.js: expressDay_, expressAfterPub_): «Опубликовать» под купоном
 * ДДММ-eN — сразу в канал (шапка без времени), затем запуск itogi.yml с express.pid (Instagram); обычный прогноз — без запуска;
 * запуск не удался — предупреждение владельцу под купоном.
 *   node tools/gas_mock/team_express_test.js        → «ok», иначе первая ошибка */
const assert = require('assert');
const path = require('path');
const gm = require('./gas_mock');

const ROOT = path.join(__dirname, '..', '..');
const NOW = Date.UTC(2026, 9, 31, 9, 0);                                        // 31.10 12:00 МСК
const env = gm.makeEnv({ now: new Date(NOW).toISOString(), cache: true });
gm.load(env, [path.join(ROOT, 'apps-script/project/Код.js')]);
const ctx = env.ctx, calls = [], disp = [];
let nextId = 9000, dispOk = true;
ctx.tgRaw_ = (method, payload) => {
  calls.push({ method, payload: JSON.parse(JSON.stringify(payload)) });
  return { ok: true, result: { message_id: nextId++ } };
};
ctx.teamAppend_ = () => {};
ctx.tgIsChannelAdmin_ = () => true;
ctx.botEnsureCommands_ = () => {};
ctx.recapDispatch_ = (payload) => { disp.push(JSON.parse(JSON.stringify(payload))); return dispOk ? { ok: true } : { ok: false, why: 'GitHub ответил 403' }; };

const CHAT = 777, BOT = { id: 42, is_bot: true }, OWNER = { id: 1 };
const kb = pid => ({ inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pub|' + pid }]] });
let upd = 1;
const press = (data, message) => { calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, callback_query: { id: 'q' + upd, from: OWNER, data, message } }); };
const of = m => calls.filter(c => c.method === m);
const coupon = (mid, pid) => ({ message_id: mid, chat: { id: CHAT, type: 'private' }, from: BOT, animation: {},
  caption: 'НХЛ · 31 октября – 1 ноября · экспресс\n\n1. Лос-Анджелес — Баффало, 23:00 МСК\nфора Лос-Анджелеса +2,5 · 1,22\n\n' +
    'Общий кэф: 1,83\n\n#нхл #экспресс #jarvibet', caption_entities: [], reply_markup: kb(pid) });

// 1. день купона
assert.strictEqual(ctx.expressDay_('3110-e1'), '2026-10-31');
assert.strictEqual(ctx.expressDay_('0111-e3'), '2026-11-01');
assert.strictEqual(ctx.expressDay_('3110-1'), null);
assert.strictEqual(ctx.expressDay_('3110-1r'), null);

// 2. «Опубликовать» под купоном — сразу в канал (без расписания) и запуск Instagram
press('tm|pub|3110-e1', coupon(700, '3110-e1'));
assert.strictEqual(of('copyMessage').length, 1, 'купон — сразу в канал');
assert.ok(!Object.keys(env.props).some(k => k.indexOf('TMSCHED_') === 0), 'купон не ставится на расписание');
assert.strictEqual(disp.length, 1);
assert.deepStrictEqual(disp[0], { kind: 'team', job: 'team/out/2026-10-31/express_ig.json', day: '2026-10-31', express: { pid: '3110-e1' } });
assert.ok(!env.props['PMW_3110-e1'], 'купон — не прогноз: послематчевого поста нет');

// 3. запуск не удался — предупреждение под купоном, канал не откатываем
dispOk = false;
press('tm|pub|3110-e2', coupon(701, '3110-e2'));
assert.strictEqual(of('copyMessage').length, 1);
const warn = of('sendMessage').find(c => /Instagram не отправлен/.test(c.payload.text));
assert.ok(warn && warn.payload.reply_to_message_id === 701, 'предупреждение владельцу');
assert.ok(!of('deleteMessage').length, 'канал не откатываем');

// 4. обычный прогноз — без запуска Instagram
dispOk = true;
const n = disp.length;
const pick = { message_id: 702, chat: { id: CHAT, type: 'private' }, from: BOT, animation: {},
  caption: 'КХЛ · 31 октября · 12:30 МСК\nАдмирал — Спартак\n\nПрогноз: победа Спартака в основное время\nКэф: 1,95\n\nТекст…',
  caption_entities: [], reply_markup: kb('3110-1') };
press('tm|pub|3110-1', pick);
assert.strictEqual(disp.length, n, 'прогноз — без express');
console.log('ok');
