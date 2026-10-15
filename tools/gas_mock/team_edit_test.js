/* Проверка «правки черновика сразу» в боте таблицы КХЛ (apps-script/project/Код.js: teamEdit*, tgToHtml_) на макете Apps Script.
 * Пост — настоящий прогноз из team/out/2026-10-15/picks_owner.json; Telegram подменён записью вызовов.
 *   node tools/gas_mock/team_edit_test.js        → «ok», иначе первая ошибка */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const gm = require('./gas_mock');

const ROOT = path.join(__dirname, '..', '..');
const env = gm.makeEnv({ now: '2026-10-15T07:00:00Z', cache: true });
gm.load(env, [path.join(ROOT, 'apps-script/project/Код.js')]);
const ctx = env.ctx, calls = [], inbox = [];
let nextId = 900;
ctx.tgRaw_ = (method, payload) => { calls.push({ method, payload: JSON.parse(JSON.stringify(payload)) }); return { ok: true, result: { message_id: nextId++ } }; };
ctx.teamAppend_ = (p, line) => { inbox.push(line); };
ctx.tgIsChannelAdmin_ = () => true;
ctx.botEnsureCommands_ = () => {};
env.props.GITHUB_TOKEN = 'x';

/** Bot API HTML (b, i, s, u, blockquote, a, tg-spoiler) → текст + entities, как их прислал бы Telegram. */
function parse(html) {
  const types = { b: 'bold', i: 'italic', s: 'strikethrough', u: 'underline', blockquote: 'blockquote', a: 'text_link', 'tg-spoiler': 'spoiler' };
  let text = '', open = [], ents = [], re = /<(\/?)([a-z-]+)([^>]*)>|([^<]+)/g, m;
  const unesc = s => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
  while ((m = re.exec(html))) {
    if (m[4] !== undefined) { text += unesc(m[4]); continue; }
    if (!m[1]) { open.push({ tag: m[2], attrs: m[3], offset: text.length }); continue; }
    const o = open.pop(); assert.strictEqual(o.tag, m[2]);
    const e = { type: types[o.tag] + (o.tag === 'blockquote' && /expandable/.test(o.attrs) ? '' : ''), offset: o.offset, length: text.length - o.offset };
    if (o.tag === 'blockquote' && /expandable/.test(o.attrs)) e.type = 'expandable_blockquote';
    if (o.tag === 'a') e.url = unesc((o.attrs.match(/href="([^"]*)"/) || [])[1] || '');
    ents.push(e);
  }
  return { text, entities: ents.sort((x, y) => x.offset - y.offset || y.length - x.length) };
}

const job = JSON.parse(fs.readFileSync(path.join(ROOT, 'team/out/2026-10-15/picks_owner.json'), 'utf8'));
const post = job.messages[1], HTML0 = post.text;
const KB = { inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pub|1510-1' }],
  [{ text: 'Поправить', callback_data: 'tm|fix|1510-1' }, { text: 'Не надо', callback_data: 'tm|no|1510-1' }]] };
const CHAT = 777, BOT = { id: 42, is_bot: true }, OWNER = { id: 1 };
let upd = 1, cur = HTML0;
const postMsg = () => { const p = parse(cur); return { message_id: 500, chat: { id: CHAT, type: 'private' }, from: BOT, photo: [{}], caption: p.text, caption_entities: p.entities, reply_markup: KB }; };
const say = (text, reply, entities) => { calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, message: { message_id: 600 + upd, chat: { id: CHAT, type: 'private' }, from: OWNER, text, entities, reply_to_message: reply } }); };
const edited = () => calls.filter(c => /^editMessage/.test(c.method)).map(c => c.payload);
const replies = () => calls.filter(c => c.method === 'sendMessage').map(c => c.payload.text).join('\n');

// 1. HTML → разметка Telegram → обратно в HTML без потерь (как бот увидит пост в ответе)
const p0 = parse(HTML0);
assert.strictEqual(ctx.tgToHtml_(p0.text, p0.entities), HTML0);
// пересекающиеся выделения и кусок с середины
assert.strictEqual(ctx.tgToHtml_('abcdef', [{ type: 'bold', offset: 0, length: 4 }, { type: 'italic', offset: 2, length: 4 }]), '<b>ab<i>cd</i></b><i>ef</i>');
assert.strictEqual(ctx.tgToHtml_('x: a<b', [{ type: 'bold', offset: 3, length: 3 }], 3), '<b>a&lt;b</b>');

// 2. «Поправить» → вопрос с подсказкой, пост запомнен
calls.length = 0;
ctx.gameHandleUpdate_({ update_id: upd++, callback_query: { id: 'q1', from: OWNER, data: 'tm|fix|1510-1', message: postMsg() } });
const ask = calls.find(c => c.method === 'sendMessage');
assert.ok(ask && /заменить прогноз на/.test(ask.payload.text), 'вопрос с подсказкой');
const askId = 900 + calls.indexOf(ask);
const askMsg = { message_id: askId, chat: { id: CHAT }, from: BOT, text: ask.payload.text };
assert.ok(env.props['TMFIX_' + CHAT + '_' + askId], 'пост запомнен');

// 3. ответ на вопрос: заменить прогноз — правка сразу, кнопки на месте, остальное оформление не тронуто
say('заменить прогноз на: победа СКА с учётом ОТ', askMsg);
let e = edited();
assert.strictEqual(e.length, 1);
assert.strictEqual(e[0].message_id, 500);
assert.deepStrictEqual(e[0].reply_markup, KB);
assert.ok(e[0].caption.includes('Прогноз: <b>победа СКА с учётом ОТ</b>'));
assert.strictEqual(e[0].caption, HTML0.replace('Прогноз: <b>победа СКА в основное время</b>', 'Прогноз: <b>победа СКА с учётом ОТ</b>'));
assert.ok(/Поправил: прогноз/.test(replies()));
assert.ok(inbox.some(l => /правка владельца в боте: 1510-1 — прогноз/.test(l)));
cur = e[0].caption;

// 4. кэф без двоеточия, ответом на тот же вопрос — берётся уже новый вариант поста
say('заменить кэф на 1,70', askMsg);
e = edited();
assert.ok(e[0].caption.includes('Кэф: <b>1,70</b>') && e[0].caption.includes('с учётом ОТ'));
cur = e[0].caption;

// 5. прямой ответ на пост: новый текст прогноза, выделение из команды переходит в пост
const t5 = 'заменить текст прогноза: Коротко: СКА сильнее и <злее>.';
say(t5, postMsg(), [{ type: 'bold', offset: t5.indexOf('СКА'), length: 3 }]);
e = edited();
assert.ok(e[0].caption.includes('<blockquote>Коротко: <b>СКА</b> сильнее и &lt;злее&gt;.</blockquote>'), e[0].caption);
cur = e[0].caption;

// 6. без свайпа — последний «Поправить»; кусок в кавычках; концовка; хэштеги; время
say('заменить «1,70» на «1,72»');
cur = edited()[0].caption; assert.ok(cur.includes('Кэф: <b>1,72</b>'));
say('заменить концовку: Кто победит? Пишите.', askMsg);
cur = edited()[0].caption; assert.ok(/<\/blockquote>\n\n<i>Кто победит\? Пишите\.<\/i>\n\n#прогнозКХЛ/.test(cur), cur);
say('заменить время на: 18:30 МСК', askMsg);
cur = edited()[0].caption; assert.ok(cur.startsWith('КХЛ · 15 октября · 18:30 МСК\n'), cur);
say('убрать концовку', askMsg);
cur = edited()[0].caption; assert.ok(!/<i>/.test(cur) && /<\/blockquote>\n\n#прогнозКХЛ/.test(cur), cur);

// 7. не найдено / ничего не изменилось — понятный ответ, пост не трогаем
say('заменить «нет такого» на «x»', askMsg);
assert.strictEqual(edited().length, 0); assert.ok(/не нашёл «нет такого»/.test(replies()));

// 8. свободный ответ — команде, как раньше; прямой ответ на пост свободным текстом — тоже команде
inbox.length = 0;
say('сделай текст короче', askMsg);
assert.strictEqual(edited().length, 0); assert.ok(/Передал команде/.test(replies()) && /поправить 1510-1 .*: сделай текст короче/.test(inbox[0]));
inbox.length = 0;
say('а можно про вратарей?', postMsg());
assert.ok(/поправить 1510-1 «КХЛ · 15 октября · 18:30 МСК»: а можно про вратарей\?/.test(inbox[0]), inbox[0]);

// 9. после «Опубликовать» (до начала матча) правка идёт и в пост канала, у черновика остаётся «✅ Опубликовано»
calls.length = 0;
ctx.gameHandleUpdate_({ update_id: upd++, callback_query: { id: 'q2', from: OWNER, data: 'tm|pub|1510-1', message: postMsg() } });
const cp = calls.findIndex(c => c.method === 'copyMessage');
assert.ok(cp >= 0);
const chId = 900 + (nextId - 900) - calls.length + cp;                  // message_id, который макет вернул на copyMessage
say('заменить кэф на: 1,80', askMsg);
e = edited();
assert.strictEqual(e.length, 2, JSON.stringify(e));
assert.ok(e[0].chat_id === '@jarvibet' && e[0].message_id === chId && !e[0].reply_markup && e[0].caption.includes('Кэф: <b>1,80</b>'));
assert.ok(e[1].chat_id === CHAT && e[1].message_id === 500 && /Опубликовано/.test(JSON.stringify(e[1].reply_markup)));
assert.ok(/в канале уже исправлен/.test(replies()) && inbox.some(l => /правка владельца в боте \(и в канале\): 1510-1 — кэф → 1,80/.test(l)));
cur = e[1].caption;
// прямой ответ на опубликованный черновик (кнопка «✅ Опубликовано») — тоже правит канал
const pubKb = { inline_keyboard: [[{ text: '✅ Опубликовано', callback_data: 'tm|done' }]] };
say('заменить «1,80» на «1,85»', Object.assign(postMsg(), { reply_markup: pubKb }));
e = edited();
assert.ok(e.length === 2 && e[0].chat_id === '@jarvibet' && e[0].caption.includes('Кэф: <b>1,85</b>'));
// опубликован до обновления бота (номера в канале нет) — отказ с подсказкой
say('заменить кэф на: 1,90', Object.assign(postMsg(), { message_id: 501, reply_markup: pubKb }));
assert.strictEqual(edited().length, 0); assert.ok(/номер там я не знаю/.test(replies()));
// матч уже начался — опубликованный прогноз не меняем (сейчас по макету 10:00 МСК)
const early = { message_id: 800, chat: { id: CHAT, type: 'private' }, from: BOT, photo: [{}], caption: 'КХЛ · 15 октября · 09:00 МСК\nПрогноз: тест',
  caption_entities: [], reply_markup: { inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pub|1510-8' }]] } };
ctx.gameHandleUpdate_({ update_id: upd++, callback_query: { id: 'q3', from: OWNER, data: 'tm|pub|1510-8', message: early } });
say('заменить прогноз на: другое', Object.assign({}, early, { reply_markup: pubKb }));
assert.strictEqual(edited().length, 0); assert.ok(/Матч уже начался/.test(replies()));
assert.strictEqual(ctx.teamEditStart_('НХЛ · 16 октября · 02:30 МСК'), Date.UTC(2026, 9, 15, 23, 30));

// 10. текстовый пост (не фото) правится через editMessageText, превью выключено; разбор команд
const txt = { message_id: 700, chat: { id: CHAT }, from: BOT, text: 'Прогноз: тест\nКэф: 1,5', entities: [{ type: 'bold', offset: 9, length: 4 }],
  reply_markup: { inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pub|1510-9' }]] } };
say('поменять кэф: 1,55', txt);
e = calls.find(c => c.method === 'editMessageText');
assert.ok(e && e.payload.text === 'Прогноз: <b>тест</b>\nКэф: <b>1,55</b>' && e.payload.link_preview_options.is_disabled);
assert.strictEqual(ctx.teamEditParse_('задача: заменить всё'), null);
assert.deepStrictEqual(JSON.parse(JSON.stringify(ctx.teamEditParse_('заменить прогноз на - победа СКА'))), { what: 'pick', from: 22, plain: 'победа СКА' });
assert.deepStrictEqual(JSON.parse(JSON.stringify(ctx.teamEditParse_('Заменить текст прогноза:\nСтрока 1\nСтрока 2'))).what, 'quote');
assert.strictEqual(ctx.teamEditParse_('сделай короче'), null);
assert.deepStrictEqual(JSON.parse(JSON.stringify(ctx.teamEditParse_('заменить победа СКА на победа ЦСКА'))), { what: 'swap', a: 'победа СКА', b: 'победа ЦСКА' });
console.log('ok');
