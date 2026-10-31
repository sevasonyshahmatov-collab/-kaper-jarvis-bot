const gm = require(__dirname + '/../../../../tools/gas_mock/gas_mock'), fs = require('fs');
let now = Date.UTC(2026, 9, 31, 11, 0);   // 14:00 МСК — владелец жмёт «Опубликовать»
const env = gm.makeEnv({ now: new Date(now).toISOString(), cache: true });
gm.load(env, [require('path').join(__dirname, '../../../../apps-script/project/Код.js')]);
const ctx = env.ctx, disp = [];
ctx.tgRaw_ = (m, p) => ({ ok: true, result: { message_id: 1310 } }); ctx.teamAppend_ = () => {}; ctx.tgIsChannelAdmin_ = () => true; ctx.botEnsureCommands_ = () => {};
ctx.recapDispatch_ = p => { disp.push(p); return { ok: true }; };
const ESPN = { 'esp.1': JSON.parse(fs.readFileSync(__dirname + '/esp.1.json', 'utf8')) };
ctx.UrlFetchApp = { fetch: u => ({ getResponseCode: () => 200, getContentText: () => JSON.stringify(ESPN[(String(u).match(/soccer\/([^/]+)\//) || [])[1]] || { events: [] }) }) };
const msg = { message_id: 700, chat: { id: 777, type: 'private' }, from: { id: 42, is_bot: true },
  text: '<b>Ла Лига · 31 октября · 16:00 МСК</b>\nЛеванте — Атлетико\n\nПрогноз: <b>победа Атлетико</b>\nКэф: <b>1,52</b>\n\nТекст…\n\n#футбол #прогноз #jarvibet', entities: [],
  reply_markup: { inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pub|3110-13' }]] } };
ctx.gameHandleUpdate_({ update_id: 1, callback_query: { id: 'q1', from: { id: 1 }, data: 'tm|pub|3110-13', message: msg } });
console.log('TMSCHED:', Object.keys(env.props).filter(k => k.startsWith('TMSCHED')), 'txt есть:', !!JSON.parse(env.props['TMSCHED_777_700'] || '{}').txt);
const setNow = t => { env.setNow ? env.setNow(new Date(t).toISOString()) : null; };
console.log('setNow в gas_mock:', typeof env.setNow);
function envAt(t, props) {
  const e = gm.makeEnv({ now: new Date(t).toISOString(), cache: true }); gm.load(e, [require('path').join(__dirname, '../../../../apps-script/project/Код.js')]);
  Object.assign(e.props, props); const c = e.ctx;
  c.tgRaw_ = () => ({ ok: true, result: { message_id: 1310 } }); c.teamAppend_ = (p, l) => console.log('  append', p); c.tgIsChannelAdmin_ = () => true; c.botEnsureCommands_ = () => {};
  c.recapDispatch_ = p => { disp.push(p); return { ok: true }; }; c.UrlFetchApp = ctx.UrlFetchApp; return e;
}
const e2 = envAt(Date.UTC(2026, 9, 31, 11, 31), env.props);            // 14:31 МСК — выход по расписанию
e2.ctx.teamSchedTick_();
console.log('PMW после выхода:', e2.props['PMW_3110-13']);
const e3 = envAt(Date.UTC(2026, 9, 31, 15, 0), e2.props);              // 18:00 МСК — после финала
e3.ctx.pmTick_();
console.log('PMW после тика:', e3.props['PMW_3110-13']); console.log('dispatch:', disp.map(d => d.pm && d.pm.pid));
