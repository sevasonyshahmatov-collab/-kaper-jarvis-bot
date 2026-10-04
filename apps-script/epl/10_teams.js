/* ==========================================================================
 * КЛУБЫ: русские названия и все варианты написания в источниках
 *  ESPN — «Manchester United», football-data.co.uk — «Man United», Understat — «Manchester United»,
 *  Pinnacle — «Manchester United». Ключ сравнения — латиница без пробелов и знаков (см. teamKey_).
 *  Неизвестный клуб не теряется: остаётся под английским названием, а в журнал пишется подсказка.
 * ========================================================================== */

var TEAMS_ = [
  // [русское название, коротко (для постеров и узких колонок), варианты на английском...]
  ['Арсенал', 'Арсенал', 'Arsenal'],
  ['Астон Вилла', 'Астон Вилла', 'Aston Villa'],
  ['Борнмут', 'Борнмут', 'Bournemouth', 'AFC Bournemouth'],
  ['Брентфорд', 'Брентфорд', 'Brentford'],
  ['Брайтон', 'Брайтон', 'Brighton', 'Brighton & Hove Albion', 'Brighton and Hove Albion', 'Brighton Hove'],
  ['Бернли', 'Бернли', 'Burnley'],
  ['Челси', 'Челси', 'Chelsea'],
  ['Кристал Пэлас', 'Кр. Пэлас', 'Crystal Palace'],
  ['Эвертон', 'Эвертон', 'Everton'],
  ['Фулхэм', 'Фулхэм', 'Fulham'],
  ['Лидс', 'Лидс', 'Leeds', 'Leeds United'],
  ['Ливерпуль', 'Ливерпуль', 'Liverpool'],
  ['Манчестер Сити', 'Ман Сити', 'Manchester City', 'Man City', 'Man. City'],
  ['Манчестер Юнайтед', 'Ман Юнайтед', 'Manchester United', 'Man United', 'Man Utd', 'Man. United', 'Manchester Utd'],
  ['Ньюкасл', 'Ньюкасл', 'Newcastle', 'Newcastle United', 'Newcastle Utd'],
  ['Ноттингем Форест', 'Ноттингем', 'Nottingham Forest', "Nott'm Forest", 'Nottm Forest', 'Nottingham'],
  ['Сандерленд', 'Сандерленд', 'Sunderland'],
  ['Тоттенхэм', 'Тоттенхэм', 'Tottenham', 'Tottenham Hotspur', 'Spurs'],
  ['Вест Хэм', 'Вест Хэм', 'West Ham', 'West Ham United'],
  ['Вулверхэмптон', 'Вулверхэмптон', 'Wolves', 'Wolverhampton', 'Wolverhampton Wanderers'],
  // кто может подняться из Чемпионшипа — чтобы новый сезон не ломал таблицу
  ['Ипсвич', 'Ипсвич', 'Ipswich', 'Ipswich Town'],
  ['Лестер', 'Лестер', 'Leicester', 'Leicester City'],
  ['Саутгемптон', 'Саутгемптон', 'Southampton'],
  ['Шеффилд Юнайтед', 'Шеффилд Ю', 'Sheffield United', 'Sheffield Utd', 'Sheff Utd'],
  ['Шеффилд Уэнсдей', 'Шеффилд У', 'Sheffield Wednesday', 'Sheffield Weds', 'Sheff Wed'],
  ['Лутон', 'Лутон', 'Luton', 'Luton Town'],
  ['Мидлсбро', 'Мидлсбро', 'Middlesbrough'],
  ['Ковентри', 'Ковентри', 'Coventry', 'Coventry City'],
  ['Вест Бромвич', 'Вест Бромвич', 'West Brom', 'West Bromwich Albion', 'West Bromwich'],
  ['Норвич', 'Норвич', 'Norwich', 'Norwich City'],
  ['Уотфорд', 'Уотфорд', 'Watford'],
  ['Халл Сити', 'Халл', 'Hull', 'Hull City'],
  ['Сток Сити', 'Сток', 'Stoke', 'Stoke City'],
  ['Рексем', 'Рексем', 'Wrexham'],
  ['Миллуолл', 'Миллуолл', 'Millwall'],
  ['Бристоль Сити', 'Бристоль', 'Bristol City'],
  ['КПР', 'КПР', 'QPR', 'Queens Park Rangers'],
  ['Суонси', 'Суонси', 'Swansea', 'Swansea City'],
  ['Дерби Каунти', 'Дерби', 'Derby', 'Derby County'],
  ['Портсмут', 'Портсмут', 'Portsmouth'],
  ['Блэкберн', 'Блэкберн', 'Blackburn', 'Blackburn Rovers'],
  ['Престон', 'Престон', 'Preston', 'Preston North End', 'Preston NE'],
  ['Чарльтон', 'Чарльтон', 'Charlton', 'Charlton Athletic'],
  ['Бирмингем', 'Бирмингем', 'Birmingham', 'Birmingham City'],
  ['Оксфорд Юнайтед', 'Оксфорд', 'Oxford', 'Oxford United', 'Oxford Utd'],
  ['Кардифф', 'Кардифф', 'Cardiff', 'Cardiff City'],
  ['Плимут', 'Плимут', 'Plymouth', 'Plymouth Argyle'],
  ['Хаддерсфилд', 'Хаддерсфилд', 'Huddersfield', 'Huddersfield Town']
];

/** Ключ сравнения: латиница в нижнем регистре без пробелов, точек, апострофов, «FC»/«AFC». */
function teamKey_(s) {
  return String(s || '').toLowerCase().replace(/&/g, 'and').replace(/\b(a?fc|the)\b/g, '').replace(/[^a-z0-9]/g, '');
}

var TEAM_MAP_ = null;
function teamMap_() {
  if (TEAM_MAP_) return TEAM_MAP_;
  var m = {};
  TEAMS_.forEach(function (t) { m[teamKey_(t[0])] = t[0]; for (var i = 2; i < t.length; i++) m[teamKey_(t[i])] = t[0]; });
  var extra = propJson_('TEAM_ALIASES', {});                   // свои варианты: {"Английское": "Русское"} — меню не нужно, правится в свойствах
  Object.keys(extra).forEach(function (k) { m[teamKey_(k)] = extra[k]; });
  TEAM_MAP_ = m;
  return m;
}
var UNKNOWN_TEAMS_ = {};
/** Английское название из любого источника → русское. Неизвестное — как есть (и запоминается для журнала). */
function teamRu_(name) {
  if (!name) return '';
  var s = String(name).trim(), m = teamMap_(), k = teamKey_(s);
  if (m[k]) return m[k];
  if (/[а-яё]/i.test(s)) return s;                              // уже по-русски
  // «Brighton & Hove Albion FC» → пробуем без последнего слова
  var parts = s.split(/\s+/);
  while (parts.length > 1) { parts.pop(); if (m[teamKey_(parts.join(' '))]) return m[teamKey_(parts.join(' '))]; }
  UNKNOWN_TEAMS_[s] = true;
  return s;
}
function teamShort_(ru) {
  for (var i = 0; i < TEAMS_.length; i++) if (TEAMS_[i][0] === ru) return TEAMS_[i][1];
  return ru;
}
