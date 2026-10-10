/* Прогон таблицы АПЛ на макете: тестовый сезон (3 сыгранных тура, пауза на сборные, 2 будущих), прогнозы модели,
 * линия, опубликованные ставки → листы рисуются настоящим кодом из apps-script/epl, снимки — в out_dir.
 *
 *   node tools/gas_mock/epl_preview.js <out_dir> [время UTC, по умолчанию 2026-10-04T14:30:00Z]
 */
const fs = require('fs'), path = require('path');
const gm = require('./gas_mock');

const OUT = process.argv[2] || 'epl_preview';
const NOW = process.argv[3] || '2026-10-04T14:30:00Z';
const ROOT = path.resolve(__dirname, '../../apps-script/epl');
fs.mkdirSync(OUT, { recursive: true });

const env = gm.makeEnv({ now: NOW });
gm.load(env, fs.readdirSync(ROOT).filter(f => f.endsWith('.js')).sort().map(f => path.join(ROOT, f)));
const C = env.ctx, ss = env.ss;
env.props.SETUP = JSON.stringify({ stage: 'done' });

// ---- тестовые данные (не настоящие результаты) ----
const R = { 'Арсенал': 1.1, 'Манчестер Сити': 1.0, 'Ливерпуль': 0.95, 'Челси': 0.7, 'Ньюкасл': 0.45, 'Астон Вилла': 0.4, 'Тоттенхэм': 0.35, 'Брайтон': 0.25,
  'Кристал Пэлас': 0.15, 'Манчестер Юнайтед': 0.15, 'Борнмут': 0.1, 'Ноттингем Форест': 0.05, 'Брентфорд': 0, 'Фулхэм': 0, 'Эвертон': -0.15, 'Вест Хэм': -0.2,
  'Вулверхэмптон': -0.3, 'Лидс': -0.4, 'Сандерленд': -0.5, 'Бернли': -0.6 };
const T = Object.keys(R);
let seed = 7; const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
const pois = l => { let L = Math.exp(-l), k = 0, p = 1; do { k++; p *= rnd(); } while (p > L); return k - 1; };
const lam = (h, a) => [1.45 * Math.exp((R[h] - R[a]) / 2.4), 1.15 * Math.exp((R[a] - R[h]) / 2.4)];

// круговой календарь: туры 5–9, даты туров (сб/вс), время UTC
const rounds = [], rot = T.slice(1);
for (let r = 0; r < 9; r++) {
  const all = [T[0]].concat(rot), pairs = [];
  for (let i = 0; i < 10; i++) pairs.push(r % 2 ? [all[19 - i], all[i]] : [all[i], all[19 - i]]);
  rounds.push(pairs); rot.unshift(rot.pop());
}
const days = { 5: ['2026-09-19', '2026-09-20'], 6: ['2026-09-26', '2026-09-27'], 7: ['2026-10-03', '2026-10-04'], 8: ['2026-10-17', '2026-10-18'], 9: ['2026-10-24', '2026-10-25'] };
const slots = [['0', '11:30'], ['0', '14:00'], ['0', '14:00'], ['0', '14:00'], ['0', '16:30'], ['1', '11:00'], ['1', '13:00'], ['1', '13:00'], ['1', '13:00'], ['1', '15:30']];
const now = new Date(NOW), matches = [], plog = {}, odds = {};
for (let rr = 5; rr <= 9; rr++) rounds[rr - 1].forEach((p, i) => {
  const start = new Date(days[rr][+slots[i][0]] + 'T' + slots[i][1] + ':00Z'), [lh, la] = lam(p[0], p[1]);
  const m = { id: 'E' + rr + String(i).padStart(2, '0'), start, home: p[0], away: p[1], status: 'Запланирован', hg: null, ag: null, hx: null, ax: null };
  if (start.getTime() + 2 * 3600000 < now.getTime()) {
    Object.assign(m, { status: 'Сыгран', hg: pois(lh), ag: pois(la), hx: Math.round((lh * (0.7 + rnd() * 0.6)) * 100) / 100, ax: Math.round((la * (0.7 + rnd() * 0.6)) * 100) / 100 });
  } else if (start <= now) m.status = 'Идёт';
  matches.push(m);
  const q = C.modelProbs_(lh, la, -0.08, 10);
  plog[m.id] = Object.assign({ id: m.id, start: start.toISOString(), home: m.home, away: m.away, upd: '01.10 07:00', how: 'до матча' }, q);
  if (rr <= 8 || i < 6) {
    const nz = [q.p1 + (rnd() - 0.5) * 0.08, q.px + (rnd() - 0.5) * 0.04, q.p2 + (rnd() - 0.5) * 0.08], s = nz.reduce((a, b) => a + b, 0);
    const ov = Math.min(0.85, Math.max(0.2, q.o25 + (rnd() - 0.5) * 0.1)), k = x => Math.round(100 / (x * 1.025)) / 100;
    odds[m.id] = { 'ID матча': m.id, 'Начало (МСК)': C.fmt_(start, 'dd.MM HH:mm'), 'Хозяева': m.home, 'Гости': m.away, 'П1': k(nz[0] / s), 'Х': k(nz[1] / s), 'П2': k(nz[2] / s),
      'Тотал': 2.5, 'Больше': k(ov), 'Меньше': k(1 - ov), 'Статус': start <= now ? 'закрыта' : 'линия', 'Начало (UTC)': start.toISOString() };
  }
});
C.setupSheets_(ss);
C.matchesWrite_(ss, matches);
C.plogWrite_(ss, plog);
C.oddsWrite_(ss, odds);
// опубликованные ставки на сыгранные матчи — итог считает сам код (settlePosts_)
const posts = C.postsSheet_(ss), byId = Object.fromEntries(matches.map(m => [m.id, m]));
[['E600', 'ТБ 2.5', 'O2.5', 1.92], ['E605', 'П1', '1', 2.10], ['E702', 'Х', 'X', 3.60], ['E707', 'ТМ 2.5', 'U2.5', 2.02]].forEach((b, i) => {
  const m = byId[b[0]];
  posts.getRange(2 + i, 1, 1, 11).setValues([[C.dayKey_(m.start), C.fmt_(m.start, 'HH:mm'), m.id, m.home + ' — ' + m.away, '01.10 10:00', 'вам', b[1], b[2], b[3], 6, '']]);
});
C.settlePosts_(ss);

// ---- листы ----
const run = (name, fn) => { try { fn(); console.log('✓ ' + name); } catch (e) { console.log('✗ ' + name + ': ' + (e.stack || e.message).split('\n').slice(0, 3).join(' | ')); } };
run('Таблица', () => C.renderTable_(ss));
run('Сила команд', () => C.renderPower_(ss));
run('Прогнозы + Прогнозы — кратко', () => C.renderPredictions_(ss));
run('Модель vs рынок', () => C.renderVs_(ss));
run('Точность', () => C.renderAccuracy_(ss));
run('Порядок вкладок', () => C.sheetsArrange_(ss));
if (env.log.length) console.log('журнал:\n  ' + env.log.slice(-8).join('\n  '));
const j = ss.getSheetByName('Журнал_автоматики');
if (j && j.getLastRow() > 1) console.log('Журнал_автоматики:\n  ' + j.getRange(2, 1, j.getLastRow() - 1, 4).getValues().map(r => r.join(' · ')).join('\n  '));

const names = ['Прогнозы — кратко', 'Прогнозы', 'Таблица', 'Сила команд', 'Модель vs рынок', 'Точность'];
fs.writeFileSync(path.join(OUT, 'book.html'), gm.renderHtml(ss));
names.forEach((n, i) => fs.writeFileSync(path.join(OUT, String(i + 1).padStart(2, '0') + '.html'), gm.renderHtml(ss, [n])));
console.log('вкладки: ' + ss.getSheets().map(s => (s.hidden ? '(' + s.name + ')' : s.name) + (s.tab ? ' ' + s.tab : '')).join(' | '));
