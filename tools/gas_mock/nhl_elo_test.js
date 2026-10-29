/* Проверка Elo таблицы НХЛ (apps-script/nhl/Код.js) после пересборки рейтинга (владелец 29.10): стартовый рейтинг
 * сжат втрое (ELO_START_SHRINK), свой лёд в ожидании Elo (ELO_HOME).
 *   node tools/gas_mock/nhl_elo_test.js        → «ok», иначе первая ошибка */
const assert = require('assert');
const path = require('path');
const gm = require('./gas_mock');

const ROOT = path.join(__dirname, '..', '..');
const env = gm.makeEnv({ now: '2026-10-29T12:00:00Z', cache: true });
gm.load(env, [path.join(ROOT, 'apps-script/nhl/Код.js')]);
const ctx = env.ctx;
assert.ok(Math.abs(ctx.ELO_START_SHRINK - 1 / 3) < 1e-9);
assert.strictEqual(ctx.ELO_HOME, 30);

// Колорадо 97 против Сиэтла 23: разница в рейтинге до первого матча — 74 / 3 ≈ 24,7, а не 74
const d1 = new Date(Date.UTC(2026, 9, 10)), d2 = new Date(Date.UTC(2026, 9, 12));
const season = { name: '2026/27', start: { 'Колорадо': 97, 'Сиэтл': 23 }, schedule: [
  { home: 'Колорадо', away: 'Сиэтл', date: d1, played: true, hg: 3, ag: 2, ot: false },
  { home: 'Сиэтл', away: 'Колорадо', date: d2, played: true, hg: 4, ag: 1, ot: false }] };
const rec = ctx.scWalkForward_([season], 0, 0, {});
assert.strictEqual(rec.length, 2);
assert.ok(Math.abs(rec[0].base - 74 / 3) < 0.01, 'разница до матча ' + rec[0].base);
// дома ожидается больше: победа хозяев-фаворитов двигает рейтинг меньше, чем без ELO_HOME
const e0 = 1500 + 47 * 6 / 3, e1 = 1500 - 27 * 6 / 3;
const exp = 1 / (1 + Math.pow(10, (e1 - e0 - 30) / 400));
const k = ctx.eloTeamK_(0, ctx.ELO_K, ctx.ELO_EARLY_BOOST, ctx.ELO_EARLY_GAMES);
const after = e0 + k * 1 * (1 - exp);                               // разница шайб 1 → множитель 1 × dampen
const dampen = 2.2 / ((e0 - e1) * 0.001 + 2.2);
const want = 50 + (e0 + k * dampen * (1 - exp) - 1500) / 6 - (50 + (e1 - k * dampen * (1 - exp) - 1500) / 6);
assert.ok(Math.abs(rec[1].base - (-want)) < 0.01, 'после первого матча ' + rec[1].base + ' ≠ ' + (-want) + ' (' + after + ')');
console.log('ok');
