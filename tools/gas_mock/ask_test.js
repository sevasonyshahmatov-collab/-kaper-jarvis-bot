/* Проверка «вопрос таблице своими словами» в боте КХЛ (apps-script/project/Код.js: askBotMessage_, askData_, askLlm_) на макете
 * Apps Script: цифры в запросе к ИИ — с листов таблицы; Claude не отвечает → Gemini; оба не отвечают → честная причина;
 * не админ и обычный текст — не перехватываем. Telegram и ИИ подменены записью вызовов.
 *   node tools/gas_mock/ask_test.js        → «ok», иначе первая ошибка */
const assert = require('assert');
const path = require('path');
const gm = require('./gas_mock');

const ROOT = path.join(__dirname, '..', '..');
const env = gm.makeEnv({ now: '2026-10-30T07:00:00Z', cache: true });          // 10:00 МСК
gm.load(env, [path.join(ROOT, 'apps-script/project/Код.js')]);
const ctx = env.ctx, ss = env.ss, calls = [], llm = [];
ctx.tgRaw_ = (method, payload) => { calls.push({ method, payload: JSON.parse(JSON.stringify(payload)) }); return { ok: true, result: { message_id: 1 } }; };
let admin = true;
ctx.tgIsChannelAdmin_ = () => admin;
ctx.botEnsureCommands_ = () => {};
ctx.betsBotSend_ = (chat, text) => calls.push({ method: 'bets', payload: { text } });
ctx.khlAppStatsCached_ = () => ({ 'Ак Барс': { gp: 3, sf: 90, sa: 75, ppPct: 0.25, pkPct: 0.8, svPct: 0.915, mainGoalie: 'Вратарь А', mainGoalieGp: 3 } });
ctx.agentGeminiModel_ = () => 'gemini-flash-lite';

// листы: «Таблица», «прогнозы», «результаты матчей»
const D = s => new ctx.Date(s + 'T12:00:00Z');
const tab = ss.insertSheet('Таблица');
tab.getRange(1, 1, 4, 11).setValues([['М', 'Команда', 'И', 'О', 'В', 'П', 'ЗШ', 'ПШ', '±', 'Форма', 'Сила'],
  [1, 'Ак Барс', 3, 4, 2, 1, 9, 7, 2, 'ВВП', 71], [2, 'Амур', 3, 3, 1, 2, 6, 8, -2, 'ПВП', 55], [3, 'СКА', 2, 2, 1, 1, 5, 5, 0, 'ВП', 60]]);
const games = [['2026-10-20', 'Амур', 'Ак Барс', 2, 4], ['2026-10-24', 'СКА', 'Ак Барс', 3, 2, true], ['2026-10-28', 'Ак Барс', 'Амур', 3, 2], ['2026-10-29', 'Амур', 'СКА', 1, 2]];
const prog = ss.insertSheet('прогнозы').insertColumnsAfter(26, 40), res = ss.insertSheet('результаты матчей');
const rows = games.concat([['2026-10-31', 'СКА', 'Ак Барс']]).map(g => { const r = new Array(57).fill(''); r[0] = D(g[0]); r[1] = g[1]; r[2] = g[2]; r[3] = 0.55; return r; });
prog.getRange(2, 1, rows.length, 57).setValues(rows);
res.getRange(2, 1, games.length, 7).setValues(games.map(g => [D(g[0]), 'Сыгран', g[1], g[2], g[3], g[4], !!g[5]]));

let mode = {};
ctx.UrlFetchApp = { fetch: (u, o) => {
  const body = JSON.parse(o.payload), who = /anthropic/.test(u) ? 'claude' : 'gemini';
  llm.push({ who, u, body });
  const m = mode[who] || 'ok';
  const r = (code, j) => ({ getResponseCode: () => code, getContentText: () => JSON.stringify(j) });
  if (m === 'ok') return who === 'claude' ? r(200, { content: [{ type: 'text', text: '**Ак Барс** в гостях: 1 победа из 2.' }] })
    : r(200, { candidates: [{ content: { parts: [{ text: 'Ответ Gemini: нет данных.' }] } }] });
  if (m === 'nomodel' && body.model === 'claude-haiku-5-5') return r(404, { error: { message: 'model: claude-haiku-5-5 not found' } });
  if (m === 'nomodel') return r(200, { content: [{ type: 'text', text: 'ответ второй модели' }] });
  if (m === 'credit') return r(400, { error: { message: 'Your credit balance is too low to access the Anthropic API.' } });
  return r(429, { error: { message: 'Quota exceeded for generate_content_free_tier_requests' } });
} };

let upd = 1;
const say = text => { calls.length = 0; llm.length = 0;
  ctx.gameHandleUpdate_({ update_id: upd++, message: { message_id: upd, chat: { id: 7, type: 'private' }, from: { id: 1 }, text } }); };
const sent = () => calls.filter(c => c.method === 'sendMessage').map(c => c.payload.text).join('\n');

// 1) Claude отвечает; в запросе — настоящие цифры таблицы
env.props.ANTHROPIC_API_KEY = 'k'; env.props.GEMINI_KEY = 'g';
say('/вопрос как Ак Барс играет в гостях с топ-8');
assert.strictEqual(llm.length, 1); assert.strictEqual(llm[0].who, 'claude');
const pr = llm[0].body.messages[0].content;
assert(/ВОПРОС: как Ак Барс играет в гостях с топ-8/.test(pr), 'вопрос в запросе');
assert(/10-20 Амур \(2\) — Ак Барс \(1\) 2:4/.test(pr), 'сыгранный матч с местами: ' + pr.slice(pr.indexOf('СЫГРАННЫЕ'), pr.indexOf('СЫГРАННЫЕ') + 300));
assert(/10-24 СКА \(3\) — Ак Барс \(1\) 3:2 \(ОТ\/Б\)/.test(pr), 'ОТ/Б');
assert(/1\. Ак Барс: 3 и, 4 о/.test(pr), 'турнирная таблица');
assert(/Ак Барс: 30 \/ 25, ПП 25%/.test(pr), 'статистика команды');
assert(/10-31 СКА \(3\) — Ак Барс \(1\): шанс Джарвиса на победу хозяев 55 %; СКА: прошлый матч 10-29, дней отдыха 1/.test(pr), 'ближайший матч и отдых');
assert(/Ак Барс: прошлый матч 10-28, дней отдыха 2, матчей за 7 дней 2/.test(pr), 'отдых гостей');
assert(/Ак Барс в гостях: 1 победа из 2\./.test(sent()) && !/\*\*/.test(sent()), 'ответ без разметки: ' + sent());
assert(/Claude claude-haiku-5-5/.test(sent()));

// 2) первая модель Claude не найдена — вторая
mode = { claude: 'nomodel' };
say('/ask кому выгодна завтрашняя усталость');
assert.deepStrictEqual(llm.map(x => x.body.model), ['claude-haiku-5-5', 'claude-haiku-4-5-20251001']);
assert(/ответ второй модели/.test(sent()));

// 3) у Claude нет денег — Gemini
mode = { claude: 'credit' };
say('кому выгодна завтрашняя усталость в КХЛ?');
assert.deepStrictEqual(llm.map(x => x.who), ['claude', 'gemini']);
assert(/Ответ Gemini/.test(sent()) && /Gemini gemini-flash-lite/.test(sent()), sent());

// 4) оба не отвечают — честно, какой и почему
mode = { claude: 'credit', gemini: 'quota' };
say('/вопрос кто лучше в большинстве');
assert(/ИИ не отвечает/.test(sent()), sent());
assert(/Claude: на счёте ключа нет денег — нужно пополнить \(код 400/.test(sent()), sent());
assert(/Gemini: исчерпан лимит или квота ключа \(код 429/.test(sent()), sent());

// 5) ключей нет вовсе
delete env.props.ANTHROPIC_API_KEY; delete env.props.GEMINI_KEY;
say('/вопрос кто лучше в большинстве');
assert.strictEqual(llm.length, 0);
assert(/ключа ANTHROPIC_API_KEY нет/.test(sent()) && /ключа GEMINI_KEY нет/.test(sent()), sent());

// 6) обычный текст без «?» и не админ — как раньше (шансы на матч), ИИ не зовём
env.props.ANTHROPIC_API_KEY = 'k'; mode = {};
say('Ак Барс Северсталь');
assert.strictEqual(llm.length, 0); assert(calls.some(c => c.method === 'bets'));
admin = false;
say('как Ак Барс играет в гостях?');
assert.strictEqual(llm.length, 0); assert(calls.some(c => c.method === 'bets'), 'не админ — шансы на матч');
say('/вопрос как Ак Барс играет');
assert.strictEqual(llm.length, 0);
console.log('ok');
