/* ==========================================================================
 * ПОСТЫ
 *  • Пост-прогноз на матч — за 3–4 часа до начала. Куда: свойство EPL_POSTS_TO = admin (вам в личку, по умолчанию),
 *    channel (сразу в канал АПЛ) или both. Ставка выбирается по числам (перевес к линии), текст пишет Gemini
 *    по доводам, которые считает код, — как в хоккейных таблицах: без перечня счетов и фамилий, без упоминания модели.
 *  • «Матчи дня» — в канал АПЛ в 11:00 МСК в день матчей: время и линия.
 *  • «Итоги дня» — в канал АПЛ, когда доигран последний матч дня: счёт всех матчей и, если прогнозы
 *    публикуются в канал, честный итог по ним (и зашедшие, и нет).
 *  Журнал «Посты»: что и когда ушло, ставка, кэф при публикации, итог, кэф закрытия и CLV.
 * ========================================================================== */

var SHEET_POSTS = 'Посты';
var POST_HEAD = ['День', 'Начало (МСК)', 'ID матча', 'Матч', 'Отправлено (МСК)', 'Куда', 'Ставка', 'Код ставки', 'Кэф', 'Перевес, п.п.', 'Запасная', 'Счёт', 'Итог ставки', 'Кэф закрытия', 'CLV, %', 'Текст поста'];
var POST_LEAD_MIN = 240, POST_LATE_MIN = 150;      // окно публикации: за 4 ч … 2,5 ч до начала
var POST_MAX_MS = 240000;
var MATCHDAY_HOUR = 11;

function postsTo_() { var v = String(prop_('EPL_POSTS_TO', 'admin')); return /^(admin|channel|both)$/.test(v) ? v : 'admin'; }
function postsSheet_(ss) {
  var sh = sheet_(ss, SHEET_POSTS);
  if (sh.getLastRow() === 0) { writeTable_(sh, POST_HEAD, []); ensureSize_(sh, 2001, POST_HEAD.length); sh.getRange(2, 1, 2000, 5).setNumberFormat('@'); sh.getRange(2, 12, 2000, 1).setNumberFormat('@'); }
  return sh;
}

/* ---------------- доводы для текста ---------------- */
function teamRecent_(matches, team, before, n) {
  return matches.filter(function (m) { return m.status === ST_PLAYED && m.hg !== null && m.start < before && (m.home === team || m.away === team); })
    .sort(function (a, b) { return b.start - a.start; }).slice(0, n || 6).map(function (m) {
      var home = m.home === team, gf = home ? m.hg : m.ag, ga = home ? m.ag : m.hg;
      return { gf: gf, ga: ga, res: gf > ga ? 'В' : gf === ga ? 'Н' : 'П', home: home, opp: home ? m.away : m.home };
    });
}
function streakText_(games, team) {
  if (games.length < 3) return null;
  var unbeaten = 0, winless = 0, wins = 0, losses = 0;
  for (var i = 0; i < games.length && games[i].res !== 'П'; i++) unbeaten++;
  for (i = 0; i < games.length && games[i].res !== 'В'; i++) winless++;
  for (i = 0; i < games.length && games[i].res === 'В'; i++) wins++;
  for (i = 0; i < games.length && games[i].res === 'П'; i++) losses++;
  if (wins >= 3) return team + ' выиграл ' + wins + ' ' + ruPlural_(wins, 'матч', 'матча', 'матчей') + ' подряд в лиге';
  if (losses >= 3) return team + ' проиграл ' + losses + ' ' + ruPlural_(losses, 'матч', 'матча', 'матчей') + ' подряд в лиге';
  if (unbeaten >= 4) return team + ' не проигрывает ' + unbeaten + ' ' + ruPlural_(unbeaten, 'матч', 'матча', 'матчей') + ' подряд';
  if (winless >= 4) return team + ' не может выиграть ' + winless + ' ' + ruPlural_(winless, 'матч', 'матча', 'матчей') + ' подряд';
  return null;
}
/** Доводы простыми словами: из них ИИ строит логику поста. */
function postArgs_(ss, m) {
  if (!INJ_CACHE_) { try { updateInjuries_(ss); } catch (e) {} }
  var matches = matchesRead_(ss), st = seasonStats_(ss), out = [];
  [[m.home, true], [m.away, false]].forEach(function (x) {
    var t = x[0], s = st[t] || {}, rec = teamRecent_(matches, t, m.start, 6);
    if (s.xn >= 4) {
      var xf = s.xf / s.xn, xa = s.xa / s.xn;
      if (xf >= 1.9) out.push(t + ' создаёт много моментов: в среднем почти ' + Math.round(xf * 10) / 10 + ' ожидаемых гола за матч');
      else if (xf <= 1.0) out.push(t + ' создаёт мало: впереди команда буксует');
      if (xa <= 1.0) out.push(t + ' почти ничего не позволяет соперникам у своих ворот');
      else if (xa >= 1.9) out.push(t + ' много позволяет соперникам: оборона проседает');
      var luck = s.gf - s.xf;
      if (luck >= 3) out.push(t + ' забивает заметно больше, чем создаёт: реализация выше своего уровня, обычно это выравнивается');
      else if (luck <= -3) out.push(t + ' создаёт больше, чем забивает: моменты есть, не идёт реализация — обычно это выправляется');
      var keep = s.xa - s.ga;
      if (keep >= 3) out.push(t + ' пропускает меньше, чем позволяет: выручает вратарь или везёт');
      else if (keep <= -3) out.push(t + ' пропускает больше, чем позволяет: не везёт в обороне');
      var pts = s.w * 3 + s.d, xd = pts - s.xpts;
      if (s.g >= 5 && xd >= 3) out.push(t + ' набрал больше очков, чем заслужил по игре');
      else if (s.g >= 5 && xd <= -3) out.push(t + ' набрал меньше очков, чем заслужил по игре');
    }
    var sk = streakText_(rec, t); if (sk) out.push(sk);
    try {
      var R = (INJ_CACHE_ || {})[t];
      if (R) {
        var key = R.out.filter(function (z) { return z.role && z.share >= 0.12; });
        if (key.length) out.push(t + ' без ' + key.map(function (z) { return z.name + ' (' + z.pos + ')'; }).join(' и ') + ' — это заметная часть атаки команды');
        else if (R.out.filter(function (z) { return z.role; }).length >= 3) out.push(t + ' без нескольких игроков основы');
        if (R.out.some(function (z) { return z.main_gk; })) out.push(t + ' без основного вратаря');
      }
    } catch (e) {}
    var hr = matches.filter(function (q) { return q.status === ST_PLAYED && q.hg !== null && q.start < m.start && (x[1] ? q.home === t : q.away === t); });
    if (hr.length >= 3) {
      var w = hr.filter(function (q) { return x[1] ? q.hg > q.ag : q.ag > q.hg; }).length, l = hr.filter(function (q) { return x[1] ? q.hg < q.ag : q.ag < q.hg; }).length;
      if (x[1] && w === hr.length) out.push(t + ' выиграл все домашние матчи сезона');
      if (x[1] && l >= Math.ceil(hr.length * 0.6)) out.push(t + ' плохо играет дома в этом сезоне');
      if (!x[1] && l === hr.length) out.push(t + ' проиграл все выездные матчи сезона');
      if (!x[1] && w >= Math.ceil(hr.length * 0.6)) out.push(t + ' уверенно играет в гостях в этом сезоне');
    }
  });
  return out;
}
function postSide_(ss, m, team) {
  var matches = matchesRead_(ss), st = seasonStats_(ss)[team] || {}, rec = teamRecent_(matches, team, m.start, 5);
  var table = []; try { table = readTable_(ss.getSheetByName(SHEET_TABLE), 4); } catch (e) { table = []; }
  var pos = table.filter(function (r) { return r['Команда'] === team; })[0];
  var inj = []; try { inj = injFacts_(ss, team); } catch (e) { inj = []; }
  return 'КОМАНДА: ' + team + (pos ? ' (' + pos['М'] + '-е место, ' + pos['Очки'] + ' очков)' : '') +
    '\nФорма, свежие первыми: ' + (rec.map(function (g) { return g.res; }).join(' ') || 'нет данных') +
    (st.g ? '\nСезон: ' + st.w + ' побед, ' + st.d + ' ничьих, ' + st.l + ' поражений, мячи ' + st.gf + '–' + st.ga : '') +
    '\nНовости по составу (официальные данные лиги): ' + (inj.length ? inj.join('; ') : 'важных потерь нет');
}

/* ---------------- текст ---------------- */
function postPickText_(pick, m) {
  if (!pick) return null;
  var c = pick.code;
  if (c === '1') return 'ПОБЕДА ' + m.home.toUpperCase();
  if (c === '2') return 'ПОБЕДА ' + m.away.toUpperCase();
  if (c === 'X') return 'НИЧЬЯ';
  var ah = String(c).match(/^([HA])(-?[\d.]+)$/);
  if (ah) { var L = Number(ah[2]); return 'ФОРА ' + (ah[1] === 'H' ? m.home : m.away).toUpperCase() + ' (' + (L > 0 ? '+' : L < 0 ? '−' : '') + String(Math.abs(L)).replace('.', ',') + ')'; }
  var t = String(c).match(/^([OU])([\d.]+)$/);
  return t ? 'ТОТАЛ ' + (t[1] === 'O' ? 'БОЛЬШЕ ' : 'МЕНЬШЕ ') + t[2].replace('.', ',') : pick.label;
}
var POST_BANNED_ = /таблиц|модел|алгоритм|нейросет|по данным|вероятн|наш расч|расч[её]т|датасет|статистическ|xG|икс-джи/i;
function postPlain_(t) {
  return String(t || '')
    .replace(/(?:[\u{1F000}-\u{1FAFF}]|[\u{2600}-\u{27BF}]|[\u{1F1E6}-\u{1F1FF}]|\u{FE0F}|\u{200D})/gu, '')
    .replace(/[*_#`]+/g, '').replace(/^\s*[-•–—]\s+/gm, '').replace(/^\s*["'«]+|["'»]+\s*$/g, '')
    .replace(/[ \t]{2,}/g, ' ').replace(/\s+([,.!?:;])/g, '$1').trim();
}
function postParse_(raw) {
  var s = String(raw || '').trim(), j = null;
  try { j = JSON.parse(s); } catch (e) { var a = s.indexOf('{'), b = s.lastIndexOf('}'); if (a >= 0 && b > a) { try { j = JSON.parse(s.slice(a, b + 1)); } catch (e2) { j = null; } } }
  if (Array.isArray(j)) j = { paragraphs: j };
  if (!j || typeof j !== 'object') j = { paragraphs: s.split(/\n{2,}/) };
  var paras = (Array.isArray(j.paragraphs) ? j.paragraphs : [j.paragraphs || j.text || '']).map(postPlain_).filter(Boolean);
  return { headline: postPlain_(j.headline || ''), paragraphs: paras, closing: postPlain_(j.closing || '') };
}
function postPrompt_(ss, m, pickText, args) {
  return 'Ты ведёшь телеграм-канал с прогнозами на английскую Премьер-лигу и пишешь пост о матче ' + m.home + ' — ' + m.away +
    '. Пиши по-русски, от первого лица, живо и просто, как человек, который смотрит футбол, а не как сводка.\n\n' +
    'ЗАДАЧА: читатель должен за полминуты понять, что решает этот матч и почему я склоняюсь к прогнозу. Это рассуждение, а не пересказ протоколов.\n' +
    'СТРУКТУРА:\n• headline — главная история матча капслоком, 3–8 слов;\n' +
    '• paragraphs — 3 абзаца по 2–3 предложения: (1) в чём история матча; (2) ' + (pickText ? 'почему это за прогноз — два-три довода из списка ДОВОДЫ своими словами' : 'почему здесь нет явного перевеса') +
    '; (3) что может помешать — честно, коротко;\n• closing — одна короткая фраза-вывод.\n\n' +
    'ПРАВИЛА ТЕКСТА: не перечисляй счета прошлых матчей и авторов голов; игроков называй только из строк «Новости по составу», не больше двух фамилий на весь пост, фамилии пиши по-русски; ' +
    'не выдумывай травм, замен и возвращений — только то, что есть в новостях; ' +
    'не больше двух чисел на весь пост, и только понятные («три победы подряд»). Без звёздочек и другой разметки, без эмодзи, хэштегов и ссылок.\n' +
    'ЗАПРЕТЫ: никогда не упоминай таблицу, модель, алгоритм, расчёты, xG, «ожидаемые голы», «по данным», проценты вероятности и коэффициенты — говори «создаёт моменты», «позволяет соперникам». ' +
    'Не выдумывай фактов — только из списков ниже. Не обращайся к читателю, не обещай выигрыш, не зови делать ставки.\n\n' +
    (pickText ? 'К ЧЕМУ СКЛОНЯЕШЬСЯ: ' + pickText.toLowerCase() + '. Объясни это через игру команд, не через числа.\n' : 'СТАВКУ НЕ ДЕЛАЕШЬ: явного перевеса нет.\n') +
    (args.length ? 'ДОВОДЫ (бери 2–3 самых сильных):\n- ' + args.join('\n- ') + '\n' : '') +
    '\nФАКТЫ О ХОЗЯЕВАХ\n' + postSide_(ss, m, m.home) + '\n\nФАКТЫ О ГОСТЯХ\n' + postSide_(ss, m, m.away) +
    '\n\nВерни JSON: {"headline":"...","paragraphs":["...","...","..."],"closing":"..."}';
}
function postAssemble_(m, pickText, odds, p) {
  var head = '⚽️ АПЛ. ' + m.home.toUpperCase() + ' — ' + m.away.toUpperCase();
  var bet = pickText ? 'ПРОГНОЗ: ' + pickText + ' ЗА ' + odds + '✔️' : 'Здесь ставку не делаю.';
  var body = p.paragraphs.filter(function (x) { return !POST_BANNED_.test(x) && !/^ПРОГНОЗ:/i.test(x) && !/ставку не делаю/i.test(x) && !/^⚽/.test(x); });
  var parts = [head];
  if (p.headline && !POST_BANNED_.test(p.headline)) parts.push(p.headline.toUpperCase());
  parts = parts.concat(body);
  if (p.closing && !POST_BANNED_.test(p.closing)) parts.push(p.closing);
  parts.push(bet);
  return parts.join('\n\n');
}
function postBuild_(ss, m) {
  var log = plogRead_(ss), odds = oddsRead_(ss), pred = log[m.id], o = odds[m.id];
  var pick = pickFor_(pred, o), main = pick ? pick.main : null, pickText = postPickText_(main, m), args = postArgs_(ss, m);
  var text;
  if (prop_('GEMINI_KEY')) {
    var prompt = postPrompt_(ss, m, pickText, args), p = postParse_(gemini_(prompt, true));
    var dirty = [p.headline, p.closing].concat(p.paragraphs).some(function (x) { return POST_BANNED_.test(x); });
    if (dirty || p.paragraphs.length < 2) {
      var p2 = postParse_(gemini_(prompt + '\n\nВ прошлый раз ответ не подошёл (упоминание расчётов или пустые абзацы). Перепиши по правилам, верни только JSON.', true));
      if (p2.paragraphs.length >= p.paragraphs.length) p = p2;
    }
    text = postAssemble_(m, pickText, main ? main.odds : '', p);
  } else {
    text = postAssemble_(m, pickText, main ? main.odds : '', { headline: '', paragraphs: args.slice(0, 3), closing: '' });
  }
  return { text: text, pick: pick, pickText: pickText };
}
/** Собрать и отправить пост по матчу. */
function postSendOne_(ss, m) {
  var r = postBuild_(ss, m), to = postsTo_(), sent = [];
  if ((to === 'admin' || to === 'both') && tgAdmin_()) { tgSend_(tgAdmin_(), escHtml_(r.text)); sent.push('мне'); }
  if ((to === 'channel' || to === 'both') && tgChannel_()) { tgSend_(tgChannel_(), escHtml_(r.text)); sent.push('канал'); }
  if (!sent.length) throw new Error('некуда отправить: укажите ваш ID или канал АПЛ');
  if (r.pick && r.pick.alt && tgAdmin_()) tgRaw_('sendMessage', { chat_id: tgAdmin_(), text: '↔️ Запасной вариант: ' + r.pick.alt.label + ' за ' + r.pick.alt.odds + ' (перевес ' + Math.round(r.pick.alt.edge * 100) + ' п.п.)' });
  try { oddsMarkPublished_(ss, m.id); } catch (e) {}
  var sh = postsSheet_(ss), main = r.pick ? r.pick.main : null;
  sh.insertRowsBefore(2, 1);
  sh.getRange(2, 1, 1, 5).setNumberFormat('@'); sh.getRange(2, 12).setNumberFormat('@');
  sh.getRange(2, 1, 1, POST_HEAD.length).setValues([[dayKey_(m.start), fmt_(m.start, 'HH:mm'), m.id, m.home + ' — ' + m.away, mskNow_('dd.MM HH:mm'), sent.join(' + '),
    r.pickText || 'без ставки', main ? main.code : '', main ? main.odds : '', main ? Math.round(main.edge * 1000) / 10 : '',
    r.pick && r.pick.alt ? r.pick.alt.label + ' за ' + r.pick.alt.odds : '', '', '', '', '', r.text]]);
  return { sent: true, pick: main };
}
function postKey_(m) { return 'POST_' + m.id; }
function postAuto_() {
  if (prop_('POST_OFF') === '1') return;
  runAuto_('postAuto_', function () {
    var ss = SpreadsheetApp.getActive(), now = new Date(), t0 = Date.now(), done = 0, err = [], fresh = false;
    matchesRead_(ss).filter(function (m) {
      var mins = (m.start - now) / 60000;
      return m.status === ST_SCHED && mins >= POST_LATE_MIN && mins <= POST_LEAD_MIN && !prop_(postKey_(m));
    }).forEach(function (m) {
      if (Date.now() - t0 > POST_MAX_MS) return;
      props_().setProperty(postKey_(m), mskNow_('dd.MM HH:mm'));
      if (!fresh) { fresh = true; try { updateInjuries_(ss); } catch (e) { journal_('Травмы', false, e.message); } }   // свежие новости о составах перед постом
      try { if (postSendOne_(ss, m).sent) done++; } catch (e) { err.push(m.home + ' — ' + m.away + ': ' + e.message); }
    });
    if (err.length) throw new Error(err.join('; '));
    return done ? 'постов отправлено: ' + done : false;
  });
}
function postNowMenu_() {
  var ss = SpreadsheetApp.getActive(), now = new Date();
  var list = matchesRead_(ss).filter(function (m) { return m.status === ST_SCHED && m.start > now && m.start - now < 4 * 86400000; });
  if (!list.length) { uiAlert_('В ближайшие 4 дня матчей нет.'); return; }
  var ui = SpreadsheetApp.getUi();
  var r = ui.prompt('Пост-прогноз', list.map(function (m, i) { return (i + 1) + ') ' + keyRu_(dayKey_(m.start)) + ' ' + fmt_(m.start, 'HH:mm') + '  ' + m.home + ' — ' + m.away; }).join('\n') + '\n\nНомер матча:', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var m = list[Number(String(r.getResponseText()).trim()) - 1];
  if (!m) { uiAlert_('Не понял номер.'); return; }
  try { var x = postSendOne_(ss, m); props_().setProperty(postKey_(m), mskNow_('dd.MM HH:mm')); sheetOpen_(SHEET_POSTS); uiAlert_('Пост отправлен (' + postsTo_() + ')' + (x.pick ? ': ' + x.pick.label + ' за ' + x.pick.odds : ', без ставки') + '.'); }
  catch (e) { uiAlert_('Не получилось: ' + e.message); }
}
function postsToMenu_() {
  var ui = SpreadsheetApp.getUi(), cur = postsTo_();
  var r = ui.prompt('Куда отправлять посты-прогнозы', 'Сейчас: ' + ({ admin: 'вам в личку', channel: 'сразу в канал АПЛ', both: 'и вам, и в канал' })[cur] +
    '.\n\nВведите: 1 — вам в личку (проверить и опубликовать самому), 2 — сразу в канал, 3 — и туда, и туда.', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var v = ({ '1': 'admin', '2': 'channel', '3': 'both' })[String(r.getResponseText()).trim()];
  if (!v) { uiAlert_('Не понял.'); return; }
  props_().setProperty('EPL_POSTS_TO', v);
  uiAlert_('Сохранено.');
}
function postToggle_() {
  var off = prop_('POST_OFF') === '1';
  if (off) props_().deleteProperty('POST_OFF'); else props_().setProperty('POST_OFF', '1');
  uiAlert_('Автоматические посты-прогнозы ' + (off ? 'включены' : 'выключены') + '.');
}

/* ---------------- итог ставок и CLV ---------------- */
function settlePosts_(ss) {
  var sh = ss.getSheetByName(SHEET_POSTS); if (!sh || sh.getLastRow() < 2) return 0;
  var byId = {}; matchesRead_(ss).forEach(function (m) { byId[m.id] = m; });
  var odds = oddsRead_(ss), v = sh.getRange(2, 1, sh.getLastRow() - 1, POST_HEAD.length).getValues(), n = 0;
  v.forEach(function (r) {
    var m = byId[String(r[2])], code = String(r[7]);
    if (!m || m.status !== ST_PLAYED || m.hg === null || r[12] !== '') return;
    r[11] = m.hg + ':' + m.ag;
    if (code) {
      var res = pickResult_(code, m.hg, m.ag), k = Number(r[8]);
      r[12] = res === 1 ? 'выигрыш' : res === 0 ? 'проигрыш' : res === 0.5 ? 'возврат' : res === 0.75 ? 'половина выигрыша' : res === 0.25 ? 'половина проигрыша' : '';
      var o = odds[m.id], close = null;
      if (o && o['Статус'] === ODDS_CLOSED) {
        if (code === '1') close = Number(o['П1']); else if (code === 'X') close = Number(o['Х']); else if (code === '2') close = Number(o['П2']);
        else {
          var t = code.match(/^([OU])([\d.]+)$/), ah = code.match(/^([HA])(-?[\d.]+)$/);
          if (t && Number(o['Тотал']) === Number(t[2])) close = Number(t[1] === 'O' ? o['Больше'] : o['Меньше']);
          if (ah && o['Фора хозяев'] !== '' && Number(o['Фора хозяев']) === (ah[1] === 'H' ? Number(ah[2]) : -Number(ah[2]))) close = Number(ah[1] === 'H' ? o['Кэф фора Х'] : o['Кэф фора Г']);
        }
      }
      if (close) { r[13] = close; r[14] = Math.round((k / close - 1) * 1000) / 10; }
    } else r[12] = 'без ставки';
    n++;
  });
  if (n) sh.getRange(2, 1, v.length, POST_HEAD.length).setValues(v);
  return n;
}
function picksStats_(ss) {
  var sh = ss.getSheetByName(SHEET_POSTS), out = { n: 0, won: 0, units: 0, clv: 0, clvN: 0 };
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, POST_HEAD.length).getValues().forEach(function (r) {
    if (!r[7] || !r[12] || r[12] === 'без ставки') return;
    var res = pickResult_(String(r[7]), Number(String(r[11]).split(':')[0]), Number(String(r[11]).split(':')[1])), k = Number(r[8]);
    if (res === null || !k) return;
    out.n++; if (res >= 0.75) out.won++;
    out.units += res === 1 ? k - 1 : res === 0 ? -1 : res === 0.5 ? 0 : res === 0.75 ? (k - 1) / 2 : -0.5;
    if (r[14] !== '') { out.clv += Number(r[14]) / 100; out.clvN++; }
  });
  return out;
}

/* ---------------- «Матчи дня» и «Итоги дня» в канал ---------------- */
function matchdayText_(ss, key) {
  var odds = oddsRead_(ss), list = matchesRead_(ss).filter(function (m) { return dayKey_(m.start) === key && m.status !== ST_CANC && m.status !== ST_POST; });
  if (!list.length) return null;
  var lines = list.map(function (m) {
    var o = odds[m.id];
    return '<b>' + fmt_(m.start, 'HH:mm') + '</b> · ' + escHtml_(m.home) + ' — ' + escHtml_(m.away) +
      (o && o['П1'] ? '\nП1 ' + o['П1'] + ' · Х ' + o['Х'] + ' · П2 ' + o['П2'] : '');
  });
  return '<b>⚽️ АПЛ · МАТЧИ ДНЯ</b>\n<i>' + dayTitle_(key) + '</i>\n\n' + lines.join('\n\n') + '\n\n<i>Время московское, коэффициенты на момент публикации.</i>';
}
function resultsText_(ss, key) {
  var list = matchesRead_(ss).filter(function (m) { return dayKey_(m.start) === key && m.status !== ST_CANC; });
  if (!list.length) return null;
  var lines = list.map(function (m) {
    if (m.status === ST_POST) return escHtml_(m.home) + ' — ' + escHtml_(m.away) + ' · перенесён';
    var hw = m.hg > m.ag, aw = m.ag > m.hg;
    return (hw ? '<b>' + escHtml_(m.home) + '</b>' : escHtml_(m.home)) + ' <b>' + m.hg + ':' + m.ag + '</b> ' + (aw ? '<b>' + escHtml_(m.away) + '</b>' : escHtml_(m.away));
  });
  var txt = '<b>⚽️ АПЛ · ИТОГИ ДНЯ</b>\n<i>' + dayTitle_(key) + '</i>\n\n' + lines.join('\n');
  if (postsTo_() !== 'admin') {                                   // прогнозы публичные — честный итог по ним
    var sh = ss.getSheetByName(SHEET_POSTS), picks = [];
    if (sh && sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, POST_HEAD.length).getValues().forEach(function (r) {
      if (String(r[0]) === key && r[7] && /канал/.test(String(r[5]))) picks.push(r);
    });
    if (picks.length) {
      var ok = 0, marks = picks.map(function (r) { var m = String(r[11]).split(':'), res = pickResult_(String(r[7]), Number(m[0]), Number(m[1])); if (res >= 0.75) ok++; return res === null ? '…' : res >= 0.75 ? '✅' : res === 0.5 ? '↩️' : '❌'; });
      txt += '\n\nНаши прогнозы дня: ' + ok + ' из ' + picks.length + ' ' + marks.join('');
    }
  }
  return txt;
}
function matchdayAuto_() {
  runAuto_('matchdayAuto_', function () {
    var ss = SpreadsheetApp.getActive(), key = dayKey_(new Date()), ch = tgChannel_();
    if (!ch) return 'канал АПЛ не указан';
    if (prop_('MATCHDAY_' + key)) return false;
    try { updateOdds_(ss); } catch (e) {}
    var t = matchdayText_(ss, key); if (!t) return false;
    tgSend_(ch, t, { silent: true }); props_().setProperty('MATCHDAY_' + key, mskNow_('HH:mm'));
    return '«Матчи дня» опубликованы';
  });
}
/** Итоги: когда все матчи дня доиграны. Дни — сегодняшний и вчерашний (поздние матчи заканчиваются после полуночи). */
function resultsDayAuto_(ss) {
  var ch = tgChannel_(); if (!ch) return null;
  var now = new Date(), done = [];
  [dayKey_(new Date(now.getTime() - 86400000)), dayKey_(now)].forEach(function (key) {
    if (prop_('RESULTS_' + key)) return;
    var list = matchesRead_(ss).filter(function (m) { return dayKey_(m.start) === key && m.status !== ST_CANC; });
    if (!list.length || list.some(function (m) { return m.status === ST_SCHED || m.status === ST_LIVE; })) return;
    if (!list.some(function (m) { return m.status === ST_PLAYED; })) return;
    try { settlePosts_(ss); } catch (e) {}
    var t = resultsText_(ss, key); if (!t) return;
    tgSend_(ch, t, { silent: true }); props_().setProperty('RESULTS_' + key, mskNow_('HH:mm')); done.push(key);
  });
  return done;
}
function previewMatchdayNow_() {
  var ss = SpreadsheetApp.getActive(), now = new Date(), key = null;
  matchesRead_(ss).some(function (m) { if (m.start > now && m.status === ST_SCHED) { key = dayKey_(m.start); return true; } return false; });
  if (!key) { uiAlert_('Ближайших матчей нет.'); return; }
  var t = matchdayText_(ss, key); tgSend_(tgAdmin_(), t); uiAlert_('Пробный пост «Матчи дня» на ' + keyRu_(key) + ' отправлен вам.');
}
function previewResultsNow_() {
  var ss = SpreadsheetApp.getActive(), now = new Date(), key = null;
  matchesRead_(ss).filter(function (m) { return m.status === ST_PLAYED; }).forEach(function (m) { if (m.start < now) key = dayKey_(m.start); });
  if (!key) { uiAlert_('Сыгранных матчей ещё нет.'); return; }
  tgSend_(tgAdmin_(), resultsText_(ss, key)); uiAlert_('Пробный пост «Итоги дня» за ' + keyRu_(key) + ' отправлен вам.');
}
function publishMatchdayNow_() {
  var ss = SpreadsheetApp.getActive(), key = dayKey_(new Date()), t = matchdayText_(ss, key);
  if (!t) { uiAlert_('Сегодня матчей нет.'); return; }
  if (!tgChannel_()) { uiAlert_('Канал АПЛ не указан.'); return; }
  var ui = SpreadsheetApp.getUi();
  if (ui.alert('Опубликовать «Матчи дня» в канал АПЛ?', ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
  tgSend_(tgChannel_(), t, { silent: true }); props_().setProperty('MATCHDAY_' + key, mskNow_('HH:mm')); uiAlert_('Опубликовано.');
}

/* ---------------- «Сила команд» — в канал по понедельникам ---------------- */
function powerText_(ss) {
  var sh = ss.getSheetByName(SHEET_POWER); if (!sh) return null;
  var rows = readTable_(sh, 4); if (rows.length < 10) return null;
  var lines = rows.slice(0, 20).map(function (r) {
    var mv = String(r['За неделю'] || ''), arrow = /^▲/.test(mv) ? ' ↑' + mv.slice(1) : /^▼/.test(mv) ? ' ↓' + mv.slice(1) : '';
    return r['Место'] + '. ' + escHtml_(r['Команда']) + arrow;
  });
  var moved = rows.filter(function (r) { return r['Сила: изменение за неделю'] !== ''; })
    .sort(function (a, b) { return Number(b['Сила: изменение за неделю']) - Number(a['Сила: изменение за неделю']); });
  var txt = '<b>⚽️ АПЛ · СИЛА КОМАНД</b>\n<i>по игре и результатам, свежие матчи важнее · ' + dayTitle_(dayKey_(new Date())) + '</i>\n\n' + lines.join('\n');
  if (moved.length >= 2) txt += '\n\nСильнее всех прибавил: ' + escHtml_(moved[0]['Команда']) + '\nСильнее всех просел: ' + escHtml_(moved[moved.length - 1]['Команда']);
  var se = ss.getSheetByName(SHEET_SEASON);
  if (se) {
    var s = readTable_(se, 4);
    var top = s.filter(function (r) { return r['Чемпион'] && r['Чемпион'] !== '<1%' && r['Чемпион'] !== '0%'; }).slice(0, 4).map(function (r) { return escHtml_(r['Команда']) + ' ' + r['Чемпион']; });
    var rel = s.slice().sort(function (a, b) { return parseFloat(String(b['Вылет']).replace(/[<>%]/g, '')) - parseFloat(String(a['Вылет']).replace(/[<>%]/g, '')); }).slice(0, 4).map(function (r) { return escHtml_(r['Команда']) + ' ' + r['Вылет']; });
    if (top.length) txt += '\n\n<b>Шансы на титул:</b> ' + top.join(', ');
    if (rel.length) txt += '\n<b>Риск вылета:</b> ' + rel.join(', ');
  }
  return txt;
}
function powerPostAuto_() {
  if (notReady_()) return;
  runAuto_('powerPostAuto_', function () {
    var ss = SpreadsheetApp.getActive(), ch = tgChannel_(); if (!ch) return 'канал АПЛ не указан';
    var t = powerText_(ss); if (!t) return 'мало данных';
    tgSend_(ch, t, { silent: true }); return '«Сила команд» опубликована';
  });
}
function previewPowerNow_() { var t = powerText_(SpreadsheetApp.getActive()); if (!t) { uiAlert_('Мало данных.'); return; } tgSend_(tgAdmin_(), t); uiAlert_('Пробный пост «Сила команд» отправлен вам.'); }
