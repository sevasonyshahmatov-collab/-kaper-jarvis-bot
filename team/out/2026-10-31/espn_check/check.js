// footSettleWatch_ на реальных ответах ESPN 31.10: три опубликованных матча
const path = require('path'), fs = require('fs');
const gm = require(__dirname + '/../../../../tools/gas_mock/gas_mock');
const env = gm.makeEnv({ now: new Date(Date.UTC(2026, 9, 31, 17, 30)).toISOString(), cache: true });
gm.load(env, [process.argv[2] || require('path').join(__dirname, '../../../../apps-script/project/Код.js')]);
const ctx = env.ctx, disp = [], app = [];
ctx.tgRaw_ = () => ({ ok: true, result: { message_id: 1 } }); ctx.teamAppend_ = (p, l) => app.push(l); ctx.recapDispatch_ = p => { disp.push(p); return { ok: true }; };
const ESPN = {}; for (const lg of ['eng.1', 'esp.1', 'ger.1']) ESPN[lg] = JSON.parse(fs.readFileSync(__dirname + '/' + lg + '.json', 'utf8'));
ctx.UrlFetchApp = { fetch: u => { const c = String(u).match(/soccer\/([^/]+)\/scoreboard/)[1]; return { getResponseCode: () => 200, getContentText: () => JSON.stringify(ESPN[c] || { events: [] }) }; } };
const post = (h, t, b, k) => '<b>' + h + '</b>\n' + t + '\n\nПрогноз: <b>' + b + '</b>\nКэф: <b>' + k + '</b>\n\nТекст';
[['3110-13', 'Ла Лига · 31 октября · 16:00 МСК', 'Леванте — Атлетико', 'победа Атлетико', '1,52'],
 ['3110-14', 'Бундеслига · 31 октября · 17:30 МСК', 'Шальке — РБ Лейпциг', 'победа РБ Лейпцига', '1,83'],
 ['3110-15', 'АПЛ · 31 октября · 18:00 МСК', 'Манчестер Сити — Брайтон', 'победа Манчестер Сити', '1,70'],
 ['3110-16', 'Ла Лига · 31 октября · 18:15 МСК', 'Райо Вальекано — Сельта', 'Сельта не проиграет (Х2)', '1,53']].forEach(([pid, h, t, b, k], i) => {
  ctx.pmWatchSave_(pid, post(h, t, b, k), { message_id: 100 + i });
  const w = JSON.parse(env.props['PMW_' + pid]);
  const games = ctx.footEspnGames_(w.espn, w.start), g = ctx.footPick_(w, games);
  console.log(pid, t, '→', g ? g.home.split(' | ')[0] + ' — ' + g.away.split(' | ')[0] + ' ' + g.hg + ':' + g.ag + ' done=' + g.done : 'НЕ НАЙДЕН', '| рядом по времени:', games.filter(x => Math.abs(x.start - w.start) <= 15 * 60000).length);
});
ctx.pmTick_();
['3110-13', '3110-14', '3110-15', '3110-16'].forEach(p => { const w = JSON.parse(env.props['PMW_' + p]); console.log(p, w.st, w.score, w.mark, w.why || '', w.pmsent ? 'итог запущен' : ''); });
console.log('postmatch_auto:', disp.map(d => d.pm.pid + ' ' + d.pm.espn));
