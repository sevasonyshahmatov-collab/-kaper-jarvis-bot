/* ==========================================================================
 * ТРАВМЫ И СОСТАВЫ (Fantasy Premier League, без ключа)
 * --------------------------------------------------------------------------
 * Официальный фэнтези-сервис АПЛ отдаёт по каждому игроку: статус (травма, дисквалификация, под вопросом),
 * новость, шанс сыграть в ближайшем туре, минуты, голы, передачи и личные xG / xA.
 * Лист «Травмы»:
 *   • сверху — по каждой команде: кто важный выбывает и ПОДСКАЗКА поправки (сколько атаки уходит вместе
 *     с ними: их доля в xG+xA команды, наполовину возмещённая заменой; основной вратарь — минус к обороне);
 *   • ниже — все неготовые игроки с новостями.
 * Подсказку таблица сама не применяет: решаете вы — переносите в «Мои поправки» (или кнопкой).
 * Новости о составе попадают в посты-прогнозы как факты — без них ИИ игроков не упоминает.
 * ========================================================================== */

var SHEET_INJ = 'Травмы';
var INJ_REPLACE = 0.5;               // замена возмещает половину вклада выбывшего
var INJ_GK_DEF = 0.06;               // без основного вратаря — пропускает примерно на 6% больше
var INJ_OUT_CHANCE = 25;             // шанс сыграть 25% и ниже — считаем, что не сыграет
var INJ_STATUS = { i: 'травма', s: 'дисквалификация', u: 'недоступен', d: 'под вопросом', n: 'не заявлен' };
var INJ_POS = { 1: 'вратарь', 2: 'защитник', 3: 'полузащитник', 4: 'нападающий' };

/** Игроки и команды FPL: {players:[...], teams:{id: ru}} */
function fplPlayers_() {
  var r = fetchJson_(FPL_BASE + '/bootstrap-static/');
  if (!r.data) throw new Error('FPL не ответил (код ' + r.code + ')');
  var teams = {}; (r.data.teams || []).forEach(function (t) { teams[t.id] = teamRu_(t.name); });
  return { teams: teams, players: (r.data.elements || []).map(function (e) {
    var n = function (x) { var v = Number(x); return isFinite(v) ? v : 0; };
    return { name: e.web_name || ((e.first_name || '') + ' ' + (e.second_name || '')).trim(), full: ((e.first_name || '') + ' ' + (e.second_name || '')).trim(),
      team: teams[e.team] || String(e.team), pos: INJ_POS[e.element_type] || '', status: e.status || 'a', news: e.news || '',
      added: e.news_added ? fmt_(new Date(e.news_added), 'dd.MM') : '', chance: e.chance_of_playing_next_round === null || e.chance_of_playing_next_round === undefined ? null : n(e.chance_of_playing_next_round),
      min: n(e.minutes), starts: n(e.starts), g: n(e.goals_scored), a: n(e.assists), xg: n(e.expected_goals), xa: n(e.expected_assists), gk: e.element_type === 1 };
  }) };
}
function injOut_(p) { return p.status === 'i' || p.status === 's' || p.status === 'u' || p.status === 'n' || (p.chance !== null && p.chance <= INJ_OUT_CHANCE); }

/** Влияние выбывших по командам: {team: {att, def, out:[...], doubt:[...]}} — att/def — подсказка в долях (−0.08 = −8%). */
function injImpact_(fpl) {
  var by = {};
  fpl.players.forEach(function (p) { (by[p.team] = by[p.team] || []).push(p); });
  var out = {};
  Object.keys(by).forEach(function (t) {
    var ps = by[t], tot = ps.reduce(function (s, p) { return s + p.xg + p.xa; }, 0) || 1;
    var maxMin = Math.max.apply(null, ps.map(function (p) { return p.min; }).concat([1]));
    var gk = ps.filter(function (p) { return p.gk; }).sort(function (a, b) { return b.min - a.min; })[0];
    var R = { att: 0, def: 0, out: [], doubt: [] };
    ps.forEach(function (p) {
      if (p.status === 'a' && (p.chance === null || p.chance > INJ_OUT_CHANCE)) return;
      var share = (p.xg + p.xa) / tot, role = p.min >= maxMin * 0.5;          // играл хотя бы половину минут лидера — игрок основы
      var x = { name: p.name, pos: p.pos, why: INJ_STATUS[p.status] || p.status, news: p.news, chance: p.chance, share: share, role: role, main_gk: gk && p === gk };
      if (injOut_(p)) {
        R.out.push(x);
        if (role) R.att -= share * (1 - INJ_REPLACE);
        if (x.main_gk && p.min >= maxMin * 0.5) R.def -= INJ_GK_DEF;
      } else R.doubt.push(x);
    });
    R.att = Math.max(-0.25, R.att);
    R.out.sort(function (a, b) { return b.share - a.share; });
    out[t] = R;
  });
  return out;
}
var INJ_CACHE_ = null;
function updateInjuries_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var fpl = fplPlayers_(), imp = injImpact_(fpl);
  INJ_CACHE_ = imp;
  var top = Object.keys(imp).sort(function (x, y) { return (imp[x].att + imp[x].def) - (imp[y].att + imp[y].def) || (x < y ? -1 : 1); }).map(function (t) {
    var R = imp[t], key = R.out.filter(function (x) { return x.role; }).slice(0, 4);
    return [t, key.map(function (x) { return x.name + ' (' + x.pos + (x.share >= 0.05 ? ', ' + Math.round(x.share * 100) + '% атак' : '') + ')'; }).join(', ') || '—',
      R.doubt.filter(function (x) { return x.role; }).map(function (x) { return x.name + (x.chance !== null ? ' ' + x.chance + '%' : ''); }).join(', ') || '—',
      Math.round(R.att * 100) ? Math.round(R.att * 100) + '%' : '', Math.round(R.def * 100) ? Math.round(R.def * 100) + '%' : ''];
  });
  var list = [];
  fpl.players.filter(function (p) { return p.status !== 'a' || (p.chance !== null && p.chance < 100); }).sort(function (a, b) { return a.team < b.team ? -1 : a.team > b.team ? 1 : b.min - a.min; }).forEach(function (p) {
    list.push([p.team, p.name, p.pos, INJ_STATUS[p.status] || (p.chance !== null ? 'под вопросом' : p.status), p.chance === null ? '' : p.chance + '%', p.news, p.added, p.min, p.g + '+' + p.a, r2_(p.xg) + ' / ' + r2_(p.xa)]);
  });
  var sh = sheet_(ss, SHEET_INJ);
  sh.clear();
  sh.getRange(1, 1).setValue('ТРАВМЫ И СОСТАВЫ · данные официального фэнтези АПЛ · обновлено ' + mskNow_()).setFontWeight('bold').setFontSize(12);
  sh.getRange(2, 1).setValue('Подсказка поправки: сколько атаки уходит вместе с выбывшими (их доля в xG+xA команды, половину возмещает замена), без основного вратаря — минус к обороне. Таблица её сама не применяет: меню «✍️ Мои поправки» → «Перенести подсказки по травмам».').setFontColor('#666666');
  writeTable_(sh, ['Команда', 'Не сыграют (основа)', 'Под вопросом (основа)', 'Подсказка: атака', 'Подсказка: оборона'], top, { top: 4, clear: false, textCols: [4, 5] });
  var t2 = 4 + top.length + 3;
  writeTable_(sh, ['Команда', 'Игрок', 'Позиция', 'Статус', 'Шанс сыграть', 'Новость', 'Дата новости', 'Минут', 'Голы+пасы', 'xG / xA'], list, { top: t2, clear: false, textCols: [5, 7, 9, 10] });
  try { sh.setColumnWidth(1, 150); sh.setColumnWidth(2, 340); sh.setColumnWidth(3, 260); sh.setColumnWidth(6, 330); } catch (e) {}
  return { teams: top.length, players: list.length };
}
/** Новости о составе команды для поста: только выбывшие и сомнительные игроки основы. */
function injFacts_(ss, team) {
  var imp = INJ_CACHE_;
  if (!imp) { try { updateInjuries_(ss); imp = INJ_CACHE_; } catch (e) { return []; } }
  var R = imp && imp[team]; if (!R) return [];
  var out = R.out.filter(function (x) { return x.role; }).slice(0, 3).map(function (x) { return x.name + ' (' + x.pos + ') не сыграет: ' + x.why + (x.news ? ' — ' + x.news : ''); });
  R.doubt.filter(function (x) { return x.role; }).slice(0, 2).forEach(function (x) { out.push(x.name + ' (' + x.pos + ') под вопросом' + (x.chance !== null ? ', шанс сыграть ' + x.chance + '%' : '') + (x.news ? ' — ' + x.news : '')); });
  return out;
}
/** Меню: перенести подсказки по травмам в «Мои поправки» (на ближайшие 7 дней). */
function injToTweaksNow_() {
  var ss = SpreadsheetApp.getActive(), imp = INJ_CACHE_;
  if (!imp) { updateInjuries_(ss); imp = INJ_CACHE_; }
  var rows = Object.keys(imp).filter(function (t) { return Math.round(imp[t].att * 100) || Math.round(imp[t].def * 100); }).map(function (t) {
    var R = imp[t]; return [t, Math.round(R.att * 100), Math.round(R.def * 100), dayKey_(new Date()), addDaysKey_(dayKey_(new Date()), 7),
      'травмы: ' + R.out.filter(function (x) { return x.role; }).map(function (x) { return x.name; }).join(', '), mskNow_('dd.MM HH:mm')];
  });
  if (!rows.length) { uiAlert_('Сейчас у команд нет заметных потерь в основе — переносить нечего.'); return; }
  var ui = SpreadsheetApp.getUi();
  if (ui.alert('Перенести в «Мои поправки» подсказки для ' + rows.length + ' команд на 7 дней?\n\n' + rows.map(function (r) { return r[0] + ': атака ' + r[1] + '%' + (r[2] ? ', оборона ' + r[2] + '%' : ''); }).join('\n'), ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
  var sh = tweaksSheet_(ss), start = Math.max(5, sh.getLastRow() + 1);
  ensureSize_(sh, start + rows.length, TWEAK_HEAD.length);
  sh.getRange(start, 4, rows.length, 2).setNumberFormat('@');
  sh.getRange(start, 1, rows.length, TWEAK_HEAD.length).setValues(rows);
  refreshModelSheets_(ss);
  uiAlert_('Перенесено и применено. Править или удалить — на листе «' + SHEET_TWEAKS + '».');
}
function injuriesNow_() { try { var r = updateInjuries_(); sheetOpen_(SHEET_INJ); uiAlert_('Травмы: игроков с отметкой ' + r.players + ', команд ' + r.teams + '.'); } catch (e) { uiAlert_('FPL: ' + e.message); } }
