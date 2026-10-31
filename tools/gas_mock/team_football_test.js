/* Проверка футбола в боте (apps-script/project/Код.js: foot*, pm*): футбольный прогноз вышел в канал → запись PMW_ (FOOT) и строка
 * листа «Футбол»; правка владельца меняет ставку; после матча — счёт ESPN, ✅/❌ по фактической ставке, без послематчевого поста;
 * в утреннюю хоккейную сверку футбол не попадает.
 *   node tools/gas_mock/team_football_test.js [папка для снимка]   → «ok», иначе первая ошибка */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const gm = require('./gas_mock');

const ROOT = path.join(__dirname, '..', '..');
const NOW = Date.UTC(2026, 9, 31, 19, 0);                                       // 31.10 22:00 МСК
const env = gm.makeEnv({ now: new Date(NOW).toISOString(), cache: true });
gm.load(env, [path.join(ROOT, 'apps-script/project/Код.js')]);
const ctx = env.ctx, calls = [], disp = [], appended = [], fetched = [];
let nextId = 9000;
ctx.tgRaw_ = (method, payload) => { calls.push({ method, payload: JSON.parse(JSON.stringify(payload)) }); return { ok: true, result: { message_id: nextId++ } }; };
ctx.teamAppend_ = (p, line) => appended.push([p, line]);
ctx.tgIsChannelAdmin_ = () => true;
ctx.botEnsureCommands_ = () => {};
ctx.recapDispatch_ = p => { disp.push(p); return { ok: true }; };

// ESPN: два матча АПЛ в 18:00 МСК (15:00Z), один — в 20:30; Ла Лига — через ОТ не бывает, но проверим AET на ЛЧ
const team = (n, s, sc, ls) => ({ team: { displayName: n, shortDisplayName: s, name: s, location: n }, score: String(sc), linescores: (ls || []).map(v => ({ value: v })) });
const ev = (date, h, a, done, name) => ({ date, status: { type: { completed: done, state: done ? 'post' : 'in', name: name || (done ? 'STATUS_FULL_TIME' : 'STATUS_SECOND_HALF') } },
  competitions: [{ competitors: [Object.assign(h, { homeAway: 'home' }), Object.assign(a, { homeAway: 'away' })] }] });
const ESPN = {
  'eng.1': { events: [
    ev('2026-10-31T15:00Z', team('Chelsea', 'Chelsea', 2), team('Manchester United', 'Man United', 1), true),
    ev('2026-10-31T15:00Z', team('Tottenham Hotspur', 'Tottenham', 1), team('Crystal Palace', 'Crystal Palace', 1), true),
    ev('2026-10-31T17:30Z', team('Manchester City', 'Man City', 0), team('Bournemouth', 'Bournemouth', 0), false)] },
  'ita.1': { events: [ev('2026-10-31T15:00Z', team('Udinese', 'Udinese', 0), team('AS Roma', 'Roma', 0), false, 'STATUS_POSTPONED')] },
  'uefa.champions': { events: [ev('2026-10-31T17:00Z', team('Bayern Munich', 'Bayern', 3, [1, 1, 1]), team('Internazionale', 'Inter', 2, [0, 2, 0]), true, 'STATUS_FINAL_AET')] },
};
ctx.UrlFetchApp = { fetch: u => {
  fetched.push(u);
  const code = String(u).match(/soccer\/([^/]+)\/scoreboard/)[1];
  return { getResponseCode: () => 200, getContentText: () => JSON.stringify(ESPN[code] || { events: [] }) };
} };

// 1. разбор ставок
const S = (bet, hg, ag, home, away) => { const b = ctx.footBet_(bet, home || 'Челси', away || 'Манчестер Юнайтед'); return b ? [b.m, b.f(hg, ag)] : null; };
assert.deepStrictEqual(S('победа Челси', 2, 1), ['1Х2', 1]);
assert.deepStrictEqual(S('победа Манчестер Юнайтед', 2, 1), ['1Х2', -1]);
assert.deepStrictEqual(S('П2', 0, 1), ['1Х2', 1]);
assert.deepStrictEqual(S('ничья', 1, 1), ['1Х2', 1]);
assert.deepStrictEqual(S('Х', 1, 0), ['1Х2', -1]);
assert.deepStrictEqual(S('тотал больше 2,5', 2, 1), ['Тотал 2,5', 1]);
assert.deepStrictEqual(S('ТМ 2,5', 2, 1), ['Тотал 2,5', -1]);
assert.deepStrictEqual(S('тотал меньше 3', 2, 1), ['Другое', 0]);
assert.deepStrictEqual(S('ТБ 2,25', 1, 1), ['Другое', -0.5]);
assert.deepStrictEqual(S('обе забьют', 2, 1), ['Другое', 1]);
assert.deepStrictEqual(S('обе забьют — нет', 2, 0), ['Другое', 1]);
assert.deepStrictEqual(S('Челси не проиграет', 1, 1), ['Другое', 1]);
assert.deepStrictEqual(S('фора Челси (-1)', 2, 1), ['Другое', 0]);
assert.deepStrictEqual(S('Ф2 (+1,5)', 2, 1), ['Другое', 1]);
assert.strictEqual(S('победа Челси и тотал больше 2,5', 3, 1), null);           // экспресс — руками
assert.strictEqual(S('угловые больше 9,5', 3, 1), null);
assert.strictEqual(ctx.footTourOf_('<b>Лига 1 · 31 октября · 21:00 МСК</b>')[1], 'fra.1');
assert.strictEqual(ctx.footTourOf_('Лига чемпионов · 4 ноября · 23:00 МСК')[1], 'uefa.champions');
assert.strictEqual(ctx.footTourOf_('КХЛ · 31 октября · 19:00 МСК'), null);

// 2. «Опубликовать» под футбольным черновиком: выход за полтора часа (матч 1.11 18:00)
const CHAT = 777, BOT = { id: 42, is_bot: true }, OWNER = { id: 1 };
const kb = pid => ({ inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pub|' + pid }]] });
const post = (pid, head, teams, bet, kef, mid) => ({ message_id: mid, chat: { id: CHAT, type: 'private' }, from: BOT,
  text: '<b>' + head + '</b>\n' + teams + '\n\nПрогноз: <b>' + bet + '</b>\nКэф: <b>' + kef + '</b>\n\nТекст…\n\n#футбол #прогноз #jarvibet', entities: [], reply_markup: kb(pid) });
let upd = 1;
const press = (data, message) => { calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, callback_query: { id: 'q' + upd, from: OWNER, data, message } }); };
press('tm|pub|0111-1', post('0111-1', 'АПЛ · 1 ноября · 18:00 МСК', 'Арсенал — Ливерпуль', 'победа Арсенала', '2,10', 700));
const sch = JSON.parse(env.props['TMSCHED_' + CHAT + '_700']);
assert.strictEqual(sch.at, Date.UTC(2026, 10, 1, 13, 30), 'выход за 1,5 ч: ' + new Date(sch.at).toISOString());

// 3. вышли в канал (как из teamSchedTick_ / «опубликовать сейчас»)
const pubs = [
  ['3110-2', 'АПЛ · 31 октября · 18:00 МСК', '«Челси» — «Манчестер Юнайтед»', 'тотал больше 2,5', '1,85', 501],
  ['3110-3', 'АПЛ · 31 октября · 18:00 МСК', 'Тоттенхэм — Кристал Пэлас', 'победа Тоттенхэма', '1,72', 502],
  ['3110-4', 'Серия А · 31 октября · 18:00 МСК', 'Удинезе — Рома', 'тотал больше 2,5', '2,05', 503],
  ['3110-5', 'Лига чемпионов · 31 октября · 20:00 МСК', 'Бавария — Интер', 'ничья', '4,10', 504],
  ['3110-6', 'АПЛ · 31 октября · 20:30 МСК', 'Манчестер Сити — Борнмут', 'победа Манчестер Сити', '1,40', 505],
];
pubs.forEach(([pid, head, teams, bet, kef, ch]) => ctx.pmWatchSave_(pid, post(pid, head, teams, bet, kef, 0).text, { message_id: ch }));
const w2 = JSON.parse(env.props['PMW_3110-2']);
assert.deepStrictEqual([w2.league, w2.tour, w2.espn, w2.home, w2.away, w2.pick], ['FOOT', 'АПЛ', 'eng.1', 'Челси', 'Манчестер Юнайтед', 'тотал больше 2,5']);
let sh = env.ss.getSheetByName('Футбол');
assert.ok(sh, 'нет листа «Футбол»');
assert.strictEqual(sh.getRange(5, 9).getValue(), '⏳');

// 4. владелец в боте поменял ставку 3110-2 после выхода → ставка в записи и на листе новая
ctx.pmEditSync_(CHAT, 0, 501, null, post('3110-2', 'АПЛ · 31 октября · 18:00 МСК', 'Челси — Манчестер Юнайтед', 'тотал меньше 2,5', '2,00', 0).text);
assert.strictEqual(JSON.parse(env.props['PMW_3110-2']).pick, 'тотал меньше 2,5');

// 5. в утреннюю хоккейную сверку футбол не идёт
ctx.pmWatchSave_('3110-1', 'КХЛ · 31 октября · 19:00 МСК\nАдмирал — Спартак\n\nПрогноз: победа Спартака\nКэф: 1,95', { message_id: 499 });
assert.strictEqual(JSON.stringify(ctx.recapCheckItems_('2026-11-01').map(x => x.t)), JSON.stringify(['Адмирал — Спартак']));
delete env.props['PMW_3110-1'];

// 6. тик после матчей: счёт ESPN, итог по фактической ставке, без послематчевого задания
ctx.pmTick_();
assert.strictEqual(disp.length, 0, 'для футбола не должно быть postmatch_auto');
assert.ok(fetched.length && fetched.every(u => /scoreboard\?dates=\d{8}$/.test(u)), 'ESPN — только один день в запросе: ' + fetched[0]);
const st = pid => JSON.parse(env.props['PMW_' + pid]);
assert.deepStrictEqual([st('3110-2').score, st('3110-2').mark], ['2:1', '❌'], 'ТМ 2,5 при 2:1');   // по правке владельца, не по черновику (ТБ — был бы ✅)
assert.deepStrictEqual([st('3110-3').score, st('3110-3').mark], ['1:1', '❌']);
assert.deepStrictEqual([st('3110-4').score, st('3110-4').mark], ['перенесён', '↩️']);
assert.deepStrictEqual([st('3110-5').score, st('3110-5').mark], ['2:2', '✅'], 'ЛЧ после ОТ — счёт за 90 минут');
assert.strictEqual(st('3110-6').st, 'wait', 'матч ещё идёт');
assert.strictEqual(appended.filter(a => a[0] === 'team/picks/FOOT_RESULTS.md').length, 4);
assert.ok(appended.some(a => /3110-2 · АПЛ · Челси — Манчестер Юнайтед · тотал меньше 2,5 · 2,00 · 2:1 · ❌$/.test(a[1])), appended.map(a => a[1]).join('\n'));

// 7. лист: строки и сводка
sh = env.ss.getSheetByName('Футбол');
const rows = sh.getRange(5, 1, 5, 10).getValues();
assert.deepStrictEqual(rows.map(r => r[0]), ['3110-6', '3110-5', '3110-4', '3110-3', '3110-2']);
assert.deepStrictEqual(rows.find(r => r[0] === '3110-2').slice(4, 10), ['тотал меньше 2,5', 'Тотал 2,5', '2,00', '2:1', '❌', -1]);
assert.strictEqual(rows.find(r => r[0] === '3110-5')[9], 3.1);
const sum = sh.getRange(4, 12, 6, 8).getValues();
assert.deepStrictEqual(sum[0].slice(0, 2), ['По турнирам', 'Ставок']);
const total = sum.find(r => r[0] === 'Всего');
assert.deepStrictEqual(total.slice(1, 5), [4, 1, 2, 1]);                         // рассчитано 4 (с возвратом), ✅1 ❌2, ждём 1

// 8. ручной итог в листе не затирается и учитывается при пересчёте
sh.getRange(5 + rows.findIndex(r => r[0] === '3110-3'), 9).setValue('✅');
ctx.footSheetNow_();
const total2 = env.ss.getSheetByName('Футбол').getRange(4, 12, 8, 8).getValues().find(r => r[0] === 'Всего');
assert.deepStrictEqual(total2.slice(2, 4), [2, 1]);

if (process.argv[2]) {
  fs.mkdirSync(process.argv[2], { recursive: true });
  fs.writeFileSync(path.join(process.argv[2], '1.html'), gm.renderHtml(env.ss, ['Футбол']));
}
console.log('ok');
