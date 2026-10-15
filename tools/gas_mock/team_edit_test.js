/* Проверка кнопки «Редактировать» и быстрых правок поста в боте таблицы КХЛ (apps-script/project/Код.js: teamEdit*, tgToHtml_)
 * на макете Apps Script. Пост — настоящий прогноз из team/out/2026-10-15/picks_owner.json; Telegram подменён записью вызовов.
 *   node tools/gas_mock/team_edit_test.js        → «ok», иначе первая ошибка */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const gm = require('./gas_mock');

const ROOT = path.join(__dirname, '..', '..');
const env = gm.makeEnv({ now: '2026-10-15T07:00:00Z', cache: true });          // 10:00 МСК
gm.load(env, [path.join(ROOT, 'apps-script/project/Код.js')]);
const ctx = env.ctx, calls = [], inbox = [];
let nextId = 900, fail = null;                                                  // fail(method, payload) → описание ошибки Telegram или null
ctx.tgRaw_ = (method, payload) => {
  const p = JSON.parse(JSON.stringify(payload));
  const err = fail && fail(method, p);
  calls.push({ method, payload: p, err, id: err ? null : nextId });
  return err ? { ok: false, description: err } : { ok: true, result: { message_id: nextId++ } };
};
ctx.teamAppend_ = (p, line) => { inbox.push(line); };
ctx.tgIsChannelAdmin_ = () => true;
ctx.botEnsureCommands_ = () => {};
env.props.GITHUB_TOKEN = 'x';

/** Bot API HTML (b, i, s, u, blockquote, a, tg-spoiler, tg-emoji) → текст + entities, как их прислал бы Telegram. */
function parse(html) {
  const types = { b: 'bold', i: 'italic', s: 'strikethrough', u: 'underline', blockquote: 'blockquote', a: 'text_link', 'tg-spoiler': 'spoiler', 'tg-emoji': 'custom_emoji' };
  let text = '', open = [], ents = [], re = /<(\/?)([a-z-]+)([^>]*)>|([^<]+)/g, m;
  const unesc = s => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
  while ((m = re.exec(html))) {
    if (m[4] !== undefined) { text += unesc(m[4]); continue; }
    if (!m[1]) { open.push({ tag: m[2], attrs: m[3], offset: text.length }); continue; }
    const o = open.pop(); assert.strictEqual(o.tag, m[2]);
    const e = { type: types[o.tag], offset: o.offset, length: text.length - o.offset };
    if (o.tag === 'blockquote' && /expandable/.test(o.attrs)) e.type = 'expandable_blockquote';
    if (o.tag === 'a') e.url = unesc((o.attrs.match(/href="([^"]*)"/) || [])[1] || '');
    if (o.tag === 'tg-emoji') e.custom_emoji_id = (o.attrs.match(/emoji-id="([^"]*)"/) || [])[1];
    ents.push(e);
  }
  return { text, entities: ents.sort((x, y) => x.offset - y.offset || y.length - x.length) };
}

const job = JSON.parse(fs.readFileSync(path.join(ROOT, 'team/out/2026-10-15/picks_owner.json'), 'utf8'));
const HTML0 = job.messages[1].text;
const KB = { inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pub|1510-1' }],
  [{ text: 'Редактировать', callback_data: 'tm|edit|1510-1' }, { text: 'Не надо', callback_data: 'tm|no|1510-1' }]] };
const PUBKB = { inline_keyboard: [[{ text: '✅ Опубликовано', callback_data: 'tm|done' }]] };
const CHAT = 777, BOT = { id: 42, is_bot: true }, OWNER = { id: 1 };
let upd = 1, lastOwnerMsg = 0;
const photo = (html, kb, id) => { const p = parse(html); return { message_id: id || 500, chat: { id: CHAT, type: 'private' }, from: BOT, photo: [{}], caption: p.text, caption_entities: p.entities, reply_markup: kb }; };
const press = (data, message) => { calls.length = 0; ctx.gameHandleUpdate_({ update_id: upd++, callback_query: { id: 'q' + upd, from: OWNER, data, message } }); };
const say = (text, reply, entities) => {
  calls.length = 0; lastOwnerMsg = 6000 + upd;
  ctx.gameHandleUpdate_({ update_id: upd++, message: { message_id: lastOwnerMsg, chat: { id: CHAT, type: 'private' }, from: OWNER, text, entities, reply_to_message: reply } });
};
const sayHtml = (html, reply) => { const p = parse(html); say(p.text, reply, p.entities); };
const of = m => calls.filter(c => c.method === m && !c.err);
const toast = () => (calls.find(c => c.method === 'answerCallbackQuery') || { payload: {} }).payload;
const replies = () => of('sendMessage').map(c => c.payload.text).join('\n');
const asMsg = c => ({ message_id: c.id, chat: { id: CHAT }, from: BOT, text: parse(c.payload.text).text });

// 1. разметка Telegram ↔ HTML без потерь; пересекающиеся выделения и кусок с середины
const p0 = parse(HTML0);
assert.strictEqual(ctx.tgToHtml_(p0.text, p0.entities), HTML0);
assert.strictEqual(ctx.tgToHtml_('abcdef', [{ type: 'bold', offset: 0, length: 4 }, { type: 'italic', offset: 2, length: 4 }]), '<b>ab<i>cd</i></b><i>ef</i>');
assert.strictEqual(ctx.tgToHtml_('x: a<b', [{ type: 'bold', offset: 3, length: 3 }], 3), '<b>a&lt;b</b>');

// 2. «Редактировать» → подсказка ответом на пост + текст поста с тем же оформлением и включённым ответом
press('tm|edit|1510-1', photo(HTML0, KB));
assert.ok(/Скопируйте/.test(toast().text));
let sent = of('sendMessage');
assert.strictEqual(sent.length, 2);
const hint = sent[0], copy = sent[1];
assert.ok(hint.payload.reply_to_message_id === 500 && /Редактирование 1510-1/.test(hint.payload.text));
assert.ok(copy.payload.text === HTML0 && copy.payload.parse_mode === 'HTML' && copy.payload.reply_markup.force_reply);
assert.ok(env.props['TMEDIT_' + CHAT + '_' + copy.id] && env.props['TMEDIT_' + CHAT + '_' + hint.id]);

// 3. владелец вставил текст, поменял прогноз, кэф и выделил слово в цитате → пост заменён целиком, оформление вставки сохранено
const HTML1 = HTML0.replace('победа СКА в основное время', 'победа СКА с учётом ОТ').replace('<b>1,64</b>', '<b>1,40</b>').replace('сплошной провал', '<b>сплошной</b> провал');
sayHtml(HTML1, asMsg(copy));
let ed = of('editMessageCaption');
assert.strictEqual(ed.length, 1);
assert.ok(ed[0].payload.message_id === 500 && ed[0].payload.caption === HTML1);
assert.deepStrictEqual(ed[0].payload.reply_markup, KB);
assert.deepStrictEqual(of('deleteMessage').map(c => c.payload.message_id).sort(), [hint.id, copy.id, lastOwnerMsg].sort());   // служебные и вставка убраны
const done = of('sendMessage').find(c => /Пост обновлён/.test(c.payload.text));
assert.ok(done && /tm\|undo/.test(JSON.stringify(done.payload.reply_markup)));
assert.ok(inbox.some(l => /правка владельца в боте: 1510-1 — новый текст поста; Прогноз: победа СКА с учётом ОТ; Кэф: 1,40/.test(l)), inbox.join('\n'));
assert.ok(!env.props['TMEDIT_' + CHAT + '_' + copy.id], 'сеанс закрыт');
const doneMsg = asMsg(done);

// 4. «↩️ Вернуть как было» — прежний текст обратно, второй раз — нельзя
press('tm|undo', doneMsg);
ed = of('editMessageCaption');
assert.ok(ed.length === 1 && ed[0].payload.caption === HTML0 && ed[0].payload.message_id === 500);
assert.ok(of('editMessageText').some(c => /Вернул как было/.test(c.payload.text)));
press('tm|undo', doneMsg);
assert.ok(/уже нельзя/.test(toast().text) && of('editMessageCaption').length === 0);

// 3б. текст отправлен БЕЗ ответа (так вышло у владельца 15.10 в Telegram Desktop) — тоже правка, если похож на пост
press('tm|edit|1510-1', photo(HTML1, KB));
const HTML2 = HTML1.replace('победа СКА с учётом ОТ', 'победа СКА').replace('<b>1,40</b>', '<b>2,01</b>');
assert.strictEqual(ctx.teamBotMessage_({ message_id: 7001, chat: { id: CHAT, type: 'private' }, from: OWNER, text: 'акб сев' }, 'акб'), false);
sayHtml(HTML2, undefined);
ed = of('editMessageCaption');
assert.ok(ed.length === 1 && ed[0].payload.message_id === 500 && ed[0].payload.caption === HTML2, JSON.stringify(ed));
assert.ok(!env.props['TMEDIT_LAST_' + CHAT], 'сеанс закрыт и без ответа');
// ответ прямо на сам пост во время правки — тоже правка; быстрая команда ответом на пост — быстрая правка, не замена
press('tm|edit|1510-1', photo(HTML2, KB));
say('заменить кэф на 1,95', photo(HTML2, KB));
ed = of('editMessageCaption');
assert.ok(ed.length === 1 && ed[0].payload.caption === HTML2.replace('<b>2,01</b>', '<b>1,95</b>'), JSON.stringify(ed));
sayHtml(HTML1, photo(HTML2, KB));
ed = of('editMessageCaption');
assert.ok(ed.length === 1 && ed[0].payload.caption === HTML1, JSON.stringify(ed));
// через полчаса без ответа уже не принимаем
press('tm|edit|1510-1', photo(HTML1, KB));
const sess = JSON.parse(env.props['TMEDIT_LAST_' + CHAT]);
sess.t -= 31 * 60000;
env.props['TMEDIT_LAST_' + CHAT] = JSON.stringify(sess);
assert.strictEqual(ctx.teamBotMessage_({ message_id: 7002, chat: { id: CHAT, type: 'private' }, from: OWNER, text: parse(HTML2).text, entities: parse(HTML2).entities }, 'кхл'), false);
delete env.props['TMEDIT_LAST_' + CHAT];

// 5. ошибки Telegram — понятный ответ, служебные сообщения на месте; премиум-смайлик — вторая попытка без него
press('tm|edit|1510-1', photo(HTML0, KB));
const copy2 = of('sendMessage')[1];
fail = (m) => (m === 'editMessageCaption' ? 'Bad Request: message caption is too long' : null);
sayHtml(HTML0 + ' ещё', asMsg(copy2));
fail = null;
assert.ok(/не больше 1024 знаков/.test(replies()) && of('deleteMessage').length === 0);
fail = (m, p) => (m === 'editMessageCaption' && /<tg-emoji/.test(p.caption || '') ? 'Bad Request: ENTITY_TEXT_INVALID' : null);
sayHtml(HTML0.replace('Лада — СКА</b>', 'Лада — СКА</b> <tg-emoji emoji-id="5">🏒</tg-emoji>'), asMsg(copy2));
fail = null;
ed = of('editMessageCaption');
assert.ok(ed.length === 1 && ed[0].payload.caption.includes('Лада — СКА</b> 🏒'), JSON.stringify(ed));

// 6. старая «Поправить» под постом открывает то же редактирование; под предложением работы — вопрос команде, как раньше
press('tm|fix|1510-1', photo(HTML0, { inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pub|1510-1' }], [{ text: 'Поправить', callback_data: 'tm|fix|1510-1' }]] }));
assert.ok(of('sendMessage').some(c => c.payload.text === HTML0));
press('tm|fix|1510-5', { message_id: 650, chat: { id: CHAT }, from: BOT, text: 'Предложение 1510-5: …',
  reply_markup: { inline_keyboard: [[{ text: 'Да', callback_data: 'tm|ok|1510-5' }, { text: 'Поправить', callback_data: 'tm|fix|1510-5' }]] } });
assert.ok(/Ответьте на это сообщение — передам команде/.test(replies()));

// 7. быстрые правки ответом прямо на пост; не найдено — понятный ответ; свободный текст — команде
say('заменить кэф на 1,70', photo(HTML0, KB));
ed = of('editMessageCaption');
assert.ok(ed.length === 1 && ed[0].payload.caption.includes('Кэф: <b>1,70</b>') && /Поправил: кэф/.test(replies()));
say('заменить «нет такого» на «x»', photo(HTML0, KB));
assert.ok(of('editMessageCaption').length === 0 && /не нашёл «нет такого»/.test(replies()));
inbox.length = 0;
say('а можно про вратарей?', photo(HTML0, KB));
assert.ok(/поправить 1510-1 «КХЛ · 15 октября · 18:00 МСК»: а можно про вратарей\?/.test(inbox[0]), inbox[0]);

// 8. опубликован (после обновления), матч не начался — «Редактировать» правит и пост в канале
press('tm|pub|1510-1', photo(HTML0, KB));
const chId = calls.find(c => c.method === 'copyMessage').id;
press('tm|edit|1510-1', photo(HTML0, PUBKB));
assert.ok(/уже в канале — поправлю и там/.test(replies()));
sayHtml(HTML1, asMsg(of('sendMessage')[1]));
ed = of('editMessageCaption');
assert.strictEqual(ed.length, 2, JSON.stringify(ed));
assert.ok(ed[0].payload.chat_id === '@jarvibet' && ed[0].payload.message_id === chId && !ed[0].payload.reply_markup && ed[0].payload.caption === HTML1);
assert.ok(ed[1].payload.chat_id === CHAT && ed[1].payload.message_id === 500 && /Опубликовано/.test(JSON.stringify(ed[1].payload.reply_markup)));
assert.ok(/и в канале/.test(replies()) && inbox.some(l => /правка владельца в боте \(и в канале\)/.test(l)));

// 9. опубликован до обновления (номер в канале неизвестен) и матч уже начался — отказ с подсказкой
press('tm|edit|1510-1', photo(HTML0, PUBKB, 501));
assert.ok(toast().show_alert && /до обновления бота/.test(toast().text) && of('sendMessage').length === 0);
const EARLY = 'КХЛ · 15 октября · 09:00 МСК\nПрогноз: <b>тест</b>';
press('tm|pub|1510-8', photo(EARLY, { inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pub|1510-8' }]] }, 800));
press('tm|edit|1510-8', photo(EARLY, PUBKB, 800));
assert.ok(/Матч уже начался/.test(toast().text) && of('sendMessage').length === 0);
assert.strictEqual(ctx.teamEditStart_('НХЛ · 16 октября · 02:30 МСК'), Date.UTC(2026, 9, 15, 23, 30));

// 10. текстовый пост правится через editMessageText, превью выключено; разбор быстрых команд
const txt = { message_id: 700, chat: { id: CHAT }, from: BOT, text: 'Прогноз: тест\nКэф: 1,5', entities: [{ type: 'bold', offset: 9, length: 4 }],
  reply_markup: { inline_keyboard: [[{ text: 'Опубликовать', callback_data: 'tm|pub|1510-9' }]] } };
say('поменять кэф: 1,55', txt);
const et = of('editMessageText')[0];
assert.ok(et && et.payload.text === 'Прогноз: <b>тест</b>\nКэф: <b>1,55</b>' && et.payload.link_preview_options.is_disabled);
assert.strictEqual(ctx.teamEditParse_('задача: заменить всё'), null);
assert.strictEqual(ctx.teamEditParse_('сделай короче'), null);
assert.deepStrictEqual(JSON.parse(JSON.stringify(ctx.teamEditParse_('заменить прогноз на - победа СКА'))), { what: 'pick', from: 22, plain: 'победа СКА' });
assert.deepStrictEqual(JSON.parse(JSON.stringify(ctx.teamEditParse_('заменить победа СКА на победа ЦСКА'))), { what: 'swap', a: 'победа СКА', b: 'победа ЦСКА' });
console.log('ok');
