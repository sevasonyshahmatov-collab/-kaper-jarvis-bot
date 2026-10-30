# -*- coding: utf-8 -*-
"""Футбольные клубы для баннеров «Versus» (31.10.2026): эмблемы и цвета — ESPN (render/emblems/football/, скачивает
tools/emblems_football_fetch.py в Actions), русские названия — как у sports.ru / «Чемпионата» и в apps-script/epl/10_teams.js.

    import football
    football.is_foot('АПЛ')                  # → True (турниры: АПЛ, Ла Лига, Серия А, Бундеслига, Лига 1, Португалия, ЛЧ, ЛЕ, ЛК, FOOT)
    football.team('Манчестер Сити')          # → (ru, цвет панели, второй цвет, аббревиатура, подпись сбоку)
    football.register()                      # клубы → poster.TEAMS (эмблема — файл football/<id>.png)
Нет клуба в таблице — круглая плашка с инициалами (poster._emblem) и серая панель; название берётся как есть.
"""
import json
import os
import re

from PIL import Image

import poster

DIR = os.path.dirname(os.path.abspath(__file__))
EMB = os.path.join(poster.EMB, 'football')

ACC = (150, 232, 120)                      # акцент футбола (КХЛ — золото, НХЛ — лёд)
LEAGUES = {                                # метка турнира в углу баннера — текстом, без логотипов турниров
    'FOOT': 'FOOTBALL', 'АПЛ': 'АПЛ', 'Ла Лига': 'ЛА ЛИГА', 'Серия А': 'СЕРИЯ А', 'Бундеслига': 'БУНДЕСЛИГА',
    'Лига 1': 'ЛИГА 1', 'Португалия': 'ПОРТУГАЛИЯ', 'Лига чемпионов': 'ЛЧ', 'ЛЧ': 'ЛЧ', 'Лига Европы': 'ЛЕ',
    'ЛЕ': 'ЛЕ', 'Лига конференций': 'ЛК', 'ЛК': 'ЛК',
}

# название ESPN → русское (как в постах и 10_teams.js)
RU = {
    'AFC Bournemouth': 'Борнмут', 'Arsenal': 'Арсенал', 'Aston Villa': 'Астон Вилла', 'Brentford': 'Брентфорд',
    'Brighton & Hove Albion': 'Брайтон', 'Chelsea': 'Челси', 'Coventry City': 'Ковентри', 'Crystal Palace': 'Кристал Пэлас',
    'Everton': 'Эвертон', 'Fulham': 'Фулхэм', 'Hull City': 'Халл Сити', 'Ipswich Town': 'Ипсвич', 'Leeds United': 'Лидс',
    'Liverpool': 'Ливерпуль', 'Manchester City': 'Манчестер Сити', 'Manchester United': 'Манчестер Юнайтед',
    'Newcastle United': 'Ньюкасл', 'Nottingham Forest': 'Ноттингем Форест', 'Sunderland': 'Сандерленд',
    'Tottenham Hotspur': 'Тоттенхэм',
    'Alavés': 'Алавес', 'Athletic Club': 'Атлетик Бильбао', 'Atlético Madrid': 'Атлетико', 'Barcelona': 'Барселона',
    'Celta Vigo': 'Сельта', 'Deportivo': 'Депортиво', 'Elche': 'Эльче', 'Espanyol': 'Эспаньол', 'Getafe': 'Хетафе',
    'Levante': 'Леванте', 'Málaga': 'Малага', 'Osasuna': 'Осасуна', 'Racing Santander': 'Расинг Сантандер',
    'Rayo Vallecano': 'Райо Вальекано', 'Real Betis': 'Бетис', 'Real Madrid': 'Реал Мадрид', 'Real Sociedad': 'Реал Сосьедад',
    'Sevilla': 'Севилья', 'Valencia': 'Валенсия', 'Villarreal': 'Вильярреал',
    'AJ Auxerre': 'Осер', 'AS Monaco': 'Монако', 'Angers': 'Анже', 'Brest': 'Брест', 'Le Havre AC': 'Гавр',
    'Le Mans': 'Ле-Ман', 'Lens': 'Ланс', 'Lille': 'Лилль', 'Lorient': 'Лорьян', 'Lyon': 'Лион', 'Marseille': 'Марсель',
    'Nice': 'Ницца', 'Paris FC': 'Париж', 'Paris Saint-Germain': 'ПСЖ', 'Stade Rennais': 'Ренн', 'Strasbourg': 'Страсбур',
    'Toulouse': 'Тулуза', 'Troyes': 'Труа',
    '1. FC Union Berlin': 'Унион Берлин', 'Bayer Leverkusen': 'Байер', 'Bayern Munich': 'Бавария',
    'Borussia Dortmund': 'Боруссия Дортмунд', 'Borussia Mönchengladbach': 'Боруссия Мёнхенгладбах',
    'Eintracht Frankfurt': 'Айнтрахт Франкфурт', 'FC Augsburg': 'Аугсбург', 'FC Cologne': 'Кёльн', 'Hamburg SV': 'Гамбург',
    'Mainz': 'Майнц', 'RB Leipzig': 'РБ Лейпциг', 'SC Freiburg': 'Фрайбург', 'SC Paderborn 07': 'Падерборн',
    'SV Elversberg': 'Эльверсберг', 'Schalke 04': 'Шальке', 'TSG Hoffenheim': 'Хоффенхайм', 'VfB Stuttgart': 'Штутгарт',
    'Werder Bremen': 'Вердер',
    'AC Milan': 'Милан', 'AS Roma': 'Рома', 'Atalanta': 'Аталанта', 'Bologna': 'Болонья', 'Cagliari': 'Кальяри',
    'Como': 'Комо', 'Fiorentina': 'Фиорентина', 'Frosinone': 'Фрозиноне', 'Genoa': 'Дженоа', 'Internazionale': 'Интер',
    'Juventus': 'Ювентус', 'Lazio': 'Лацио', 'Lecce': 'Лечче', 'Monza': 'Монца', 'Napoli': 'Наполи', 'Parma': 'Парма',
    'Sassuolo': 'Сассуоло', 'Torino': 'Торино', 'Udinese': 'Удинезе', 'Venezia': 'Венеция',
    'Académico de Viseu': 'Академику', 'Alverca': 'Алверка', 'Arouca': 'Ароука', 'Benfica': 'Бенфика', 'Braga': 'Брага',
    'C.D. Nacional': 'Насьонал', 'Casa Pia': 'Каса Пия', 'Estoril': 'Эшторил', 'Estrela': 'Эштрела',
    'FC Famalicao': 'Фамаликан', 'FC Porto': 'Порту', 'Gil Vicente': 'Жил Висенте', 'Maritimo': 'Маритиму',
    'Moreirense': 'Морейренсе', 'Rio Ave': 'Риу Аве', 'Santa Clara': 'Санта-Клара', 'Sporting CP': 'Спортинг',
    'Vitória de Guimaraes': 'Витория Гимарайнш',
    'AEK Athens': 'АЕК', 'Bodo/Glimt': 'Будё-Глимт', 'Club Brugge': 'Брюгге', 'Fenerbahce': 'Фенербахче',
    'Feyenoord Rotterdam': 'Фейеноорд', 'Galatasaray': 'Галатасарай', 'LASK Linz': 'ЛАСК', 'PSV Eindhoven': 'ПСВ',
    'Sabah FK': 'Сабах', 'Shakhtar Donetsk': 'Шахтёр Донецк', 'Slavia Prague': 'Славия Прага', 'Slovan Bratislava': 'Слован',
    'Viking FK': 'Викинг', 'AZ Alkmaar': 'АЗ', 'Anderlecht': 'Андерлехт', 'Ararat-Armenia': 'Арарат-Армения',
    'Besiktas': 'Бешикташ', 'Celtic': 'Селтик', 'Dinamo Zagreb': 'Динамо Загреб', 'Ferencvaros': 'Ференцварош',
    "Hapoel Be'er": 'Хапоэль Беэр-Шева', 'Jagiellonia Bialystok': 'Ягеллония', 'Lech Poznan': 'Лех',
    'Levski Sofia': 'Левски', 'Lillestrom': 'Лиллестрём', 'NEC Nijmegen': 'НЕК', 'NK Celje': 'Целе', 'OFI Crete': 'ОФИ',
    'Olympiacos': 'Олимпиакос', 'Omonia Nicosia': 'Омония', 'RB Salzburg': 'Зальцбург', 'SK Sturm Graz': 'Штурм',
    'Sparta Prague': 'Спарта Прага', 'Torreense': 'Торренсе', 'Union St.-Gilloise': 'Юнион Сент-Жилуаз',
    'Viktoria Plzen': 'Виктория Пльзень', 'AGF': 'Орхус', 'Ajax Amsterdam': 'Аякс', 'Borac Banja Luka': 'Борац',
    'CSKA Sofia': 'ЦСКА София', 'CSU Craiova': 'Университатя Крайова', 'Egnatia': 'Эгнатия', 'F.C. København': 'Копенгаген',
    'FC Lugano': 'Лугано', 'FC Midtjylland': 'Мидтьюлланн', 'FC Nordsjælland': 'Нордсьелланн', 'FC Thun': 'Тун',
    'FC Twente': 'Твенте', 'Hajduk Split': 'Хайдук', 'Heart of Midlothian': 'Хартс', 'Iberia 1999': 'Иберия 1999',
    "Inter D'Escaldes": 'Интер Эскальдес', 'Jablonec': 'Яблонец', 'KAA Gent': 'Гент', 'Kairat Almaty': 'Кайрат',
    'Kauno Zalgiris': 'Жальгирис', 'KuPS Kuopio': 'КуПС', 'Lincoln Red Imps': 'Линкольн Ред Импс', 'Mjällby AIF': 'Мьельбю',
    'Pafos': 'Пафос', 'Panathinaikos': 'Панатинаикос', 'Red Star Belgrade': 'Црвена Звезда', 'Riga FC': 'Рига',
    'SK Brann': 'Брюнн', 'Sint-Truidense': 'Синт-Трёйден', 'Trabzonspor': 'Трабзонспор',
}
# запись из источников (football-data, Pinnacle, sports.ru) → русское название таблицы
ALIAS = {
    'man city': 'Манчестер Сити', 'man united': 'Манчестер Юнайтед', 'man utd': 'Манчестер Юнайтед',
    'ман сити': 'Манчестер Сити', 'ман юнайтед': 'Манчестер Юнайтед', 'манчестер': 'Манчестер Сити',
    'tottenham': 'Тоттенхэм', 'spurs': 'Тоттенхэм', 'newcastle': 'Ньюкасл', 'nott\'m forest': 'Ноттингем Форест',
    'brighton': 'Брайтон', 'bournemouth': 'Борнмут', 'leeds': 'Лидс', 'ipswich': 'Ипсвич', 'hull': 'Халл Сити',
    'crystal palace': 'Кристал Пэлас', 'кр пэлас': 'Кристал Пэлас', 'палас': 'Кристал Пэлас',
    'ath madrid': 'Атлетико', 'atletico madrid': 'Атлетико', 'атлетико мадрид': 'Атлетико', 'ath bilbao': 'Атлетик Бильбао',
    'атлетик': 'Атлетик Бильбао', 'sociedad': 'Реал Сосьедад', 'betis': 'Бетис', 'real betis': 'Бетис', 'celta': 'Сельта',
    'vallecano': 'Райо Вальекано', 'rayo': 'Райо Вальекано', 'alaves': 'Алавес', 'malaga': 'Малага',
    'inter': 'Интер', 'inter milan': 'Интер', 'milan': 'Милан', 'roma': 'Рома', 'internazionale milano': 'Интер',
    'bayern': 'Бавария', 'bayern munchen': 'Бавария', 'dortmund': 'Боруссия Дортмунд', 'боруссия д': 'Боруссия Дортмунд',
    'leverkusen': 'Байер', 'байер леверкузен': 'Байер', "m'gladbach": 'Боруссия Мёнхенгладбах', 'gladbach': 'Боруссия Мёнхенгладбах',
    'боруссия м': 'Боруссия Мёнхенгладбах', 'borussia monchengladbach': 'Боруссия Мёнхенгладбах',
    'ein frankfurt': 'Айнтрахт Франкфурт', 'eintracht': 'Айнтрахт Франкфурт', 'frankfurt': 'Айнтрахт Франкфурт',
    'айнтрахт': 'Айнтрахт Франкфурт', 'leipzig': 'РБ Лейпциг', 'лейпциг': 'РБ Лейпциг', 'rb leipzig': 'РБ Лейпциг',
    'stuttgart': 'Штутгарт', 'freiburg': 'Фрайбург', 'hoffenheim': 'Хоффенхайм', 'union berlin': 'Унион Берлин',
    'werder': 'Вердер', 'bremen': 'Вердер', 'koln': 'Кёльн', 'cologne': 'Кёльн', 'köln': 'Кёльн', 'hamburg': 'Гамбург',
    'augsburg': 'Аугсбург', 'paderborn': 'Падерборн', 'elversberg': 'Эльверсберг', 'schalke': 'Шальке',
    'paris sg': 'ПСЖ', 'paris saint germain': 'ПСЖ', 'psg': 'ПСЖ', 'пари сен-жермен': 'ПСЖ', 'пари сен жермен': 'ПСЖ',
    'auxerre': 'Осер', 'monaco': 'Монако', 'le havre': 'Гавр', 'rennes': 'Ренн', 'stade rennes': 'Ренн',
    'olympique marseille': 'Марсель', 'olympique lyon': 'Лион', 'lens': 'Ланс', 'lille': 'Лилль',
    'sporting': 'Спортинг', 'sporting lisbon': 'Спортинг', 'sp lisbon': 'Спортинг', 'porto': 'Порту', 'nacional': 'Насьонал',
    'guimaraes': 'Витория Гимарайнш', 'vitoria guimaraes': 'Витория Гимарайнш', 'famalicao': 'Фамаликан',
    'psv': 'ПСВ', 'feyenoord': 'Фейеноорд', 'ajax': 'Аякс', 'az alkmaar': 'АЗ', 'club brugge': 'Брюгге', 'brugge': 'Брюгге',
    'shakhtar': 'Шахтёр Донецк', 'шахтер донецк': 'Шахтёр Донецк', 'slavia praha': 'Славия Прага', 'sparta praha': 'Спарта Прага',
    'salzburg': 'Зальцбург', 'red bull salzburg': 'Зальцбург', 'copenhagen': 'Копенгаген', 'fc copenhagen': 'Копенгаген',
    'red star': 'Црвена Звезда', 'crvena zvezda': 'Црвена Звезда', 'црвена звезда': 'Црвена Звезда', 'бодо глимт': 'Будё-Глимт',
    'bodo glimt': 'Будё-Глимт', 'hearts': 'Хартс', 'midtjylland': 'Мидтьюлланн', 'young boys': None,
}


def _norm(s):
    s = re.sub(r'[^\wа-яё ]+', ' ', (s or '').lower().replace('ё', 'е').replace('&', ' and '))
    return re.sub(r'\s+', ' ', s).strip()


def _load():
    p = os.path.join(EMB, 'teams.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


_T = _load()                               # id → {name, abbr, color, alt, leagues…}
_BY_RU = {}                                # ru → id
_INDEX = {}                                # нормализованное имя → ru
for _id, _v in _T.items():
    _ru = RU.get(_v['name'])
    if not _ru:
        continue
    _BY_RU[_ru] = _id
    for _k in (_ru, _v['name'], _v.get('short') or '', _v.get('location') or ''):
        _INDEX.setdefault(_norm(_k), _ru)
for _k, _ru in ALIAS.items():
    if _ru:
        _INDEX[_norm(_k)] = _ru


def is_foot(league):
    return league in LEAGUES


def label(league):
    return LEAGUES.get(league, 'FOOTBALL')


def resolve(name):
    """Имя клуба из поста / Pinnacle / football-data → русское название таблицы (нет в таблице — как есть)."""
    n = _norm(name)
    if n in _INDEX:
        return _INDEX[n]
    for k, ru in _INDEX.items():                # «Манчестер Сити (жен.)», «Man City FC» и т. п. — по началу слов
        if len(k) >= 5 and (n.startswith(k + ' ') or k.startswith(n + ' ')):
            return ru
    return name


def _hex(h, default=(110, 115, 125)):
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return default


def _sat(c):
    return (max(c) - min(c)) / max(1, max(c))


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _logo_color(tid):
    """Самый заметный насыщенный цвет эмблемы (если у ESPN цвет белый/чёрный/блёклый)."""
    p = os.path.join(EMB, tid + '.png')
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert('RGBA')
    im.thumbnail((64, 64))
    best, score = None, 0
    bins = {}
    for r, g, b, a in im.getdata():
        if a < 200:
            continue
        c = (r, g, b)
        if _sat(c) < .45 or not 55 < _lum(c) < 215:
            continue
        k = (r // 32, g // 32, b // 32)
        bins.setdefault(k, []).append(c)
    total = sum(len(cs) for cs in bins.values())
    for k, cs in bins.items():
        if len(cs) > score and len(cs) >= 0.12 * max(1, im.width * im.height * 0.35):
            best, score = tuple(sum(x[i] for x in cs) // len(cs) for i in range(3)), len(cs)
    return best


def _good(c):
    return _sat(c) >= .3 and 55 < _lum(c) < 215


# цвет панели руками, где ESPN отдаёт белый/чёрный или цвет, которого нет на самой эмблеме
COLOR = {'Манчестер Сити': (108, 171, 221), 'Ювентус': (140, 140, 146), 'Удинезе': (150, 150, 156),
         'Ньюкасл': (120, 124, 132), 'Тоттенхэм': (28, 52, 110), 'Реал Мадрид': (86, 110, 176)}


# аббревиатуры ESPN, которые путаются (MAN, MUN у Баварии…) — как их пишут на табло
ABBR = {'Манчестер Юнайтед': 'MUN', 'Манчестер Сити': 'MCI', 'Бавария': 'BAY', 'Байер': 'LEV', 'Лилль': 'LIL',
        'Ланс': 'LEN', 'Монако': 'MON', 'Рома': 'ROM', 'Ренн': 'REN', 'Марсель': 'MAR', 'Лион': 'LYO', 'ПСЖ': 'PSG',
        'Интер': 'INT', 'Милан': 'MIL', 'Тоттенхэм': 'TOT', 'Ньюкасл': 'NEW', 'Эвертон': 'EVE', 'Фрайбург': 'FRE',
        'Майнц': 'MAI', 'Айнтрахт Франкфурт': 'SGE', 'Боруссия Мёнхенгладбах': 'BMG', 'Боруссия Дортмунд': 'BVB',
        'РБ Лейпциг': 'RBL', 'Брюгге': 'BRU', 'Копенгаген': 'COP'}


def banner_color(tid):
    v = _T.get(tid) or {}
    ru = RU.get(v.get('name'))
    if ru in COLOR:
        return COLOR[ru]
    c1, c2 = _hex(v.get('color') or ''), _hex(v.get('alt') or '')
    for c in (c1, c2):
        if _good(c):
            return c
    return _logo_color(tid) or (110, 115, 125)


def second_color(tid):
    v = _T.get(tid) or {}
    return _hex(v.get('alt') or '', (235, 235, 235))


def team(name):
    """→ (ru-название, цвет панели, второй цвет, аббревиатура, подпись сбоку) — как versus._team."""
    ru = resolve(name)
    tid = _BY_RU.get(ru)
    if not tid:
        return ru, (110, 115, 125), (235, 235, 235), ''.join(w[0] for w in ru.split()[:3]).upper().ljust(3, 'X')[:3], ru.upper()
    v = _T[tid]
    en = v['name']
    side = ru if _norm(ru) == _norm(en) else '%s · %s' % (ru, en)
    return ru, banner_color(tid), second_color(tid), (ABBR.get(ru) or v.get('abbr') or ru[:3]).upper(), side.upper()


def register():
    """Вписывает клубы в poster.TEAMS: эмблема — render/emblems/football/<id>.png; цвета — как в team()."""
    for ru, tid in _BY_RU.items():
        poster.TEAMS[ru] = ('football/' + tid, banner_color(tid), second_color(tid))
