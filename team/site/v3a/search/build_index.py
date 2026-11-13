#!/usr/bin/env python3
"""Индекс поиска сайта v3a: клубы, лиги, матчи (±7 дней), хоккеисты -> ../data/search.json (<=150 КБ).
Запуск: python3 search/build_index.py  (из любой папки; без сети; читает только файлы сайта)."""
import json, os, sys, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # team/site/v3a
OUT = os.path.join(ROOT, 'data', 'search.json')
LIMIT = 150 * 1024
DAYS = 7


def js_obj(path):
    s = open(path, encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])


# --- хоккей: английские названия и синонимы (slug -> (EN, синонимы)) ---
KHL = {
    'dinamo_msk': ('Dynamo Moscow', 'динамо мск dinamo moscow'), 'avangard': ('Avangard Omsk', 'омск avangard'),
    'amur': ('Amur Khabarovsk', 'хабаровск'), 'cska': ('CSKA Moscow', 'цска цска армейцы cska конь'),
    'spartak': ('Spartak Moscow', 'спартак красно-белые'), 'torpedo': ('Torpedo Nizhny Novgorod', 'нижний новгород торпеда'),
    'sibir': ('Sibir Novosibirsk', 'новосибирск'), 'lokomotiv': ('Lokomotiv Yaroslavl', 'ярославль локо'),
    'traktor': ('Traktor Chelyabinsk', 'челябинск'), 'metallurg': ('Metallurg Magnitogorsk', 'магнитогорск'),
    'salavat': ('Salavat Yulaev Ufa', 'уфа салават'), 'neftekhimik': ('Neftekhimik Nizhnekamsk', 'нижнекамск'),
    'dinamo_minsk': ('Dinamo Minsk', 'минск динамо минск'), 'akbars': ('Ak Bars Kazan', 'казань ак барс акбарс'),
    'severstal': ('Severstal Cherepovets', 'череповец'), 'ska': ('SKA Saint Petersburg', 'ска питер санкт-петербург ska'),
    'barys': ('Barys Astana', 'астана'), 'avtomobilist': ('Avtomobilist Yekaterinburg', 'екатеринбург'),
    'admiral': ('Admiral Vladivostok', 'владивосток'), 'lada': ('Lada Togliatti', 'тольятти'),
    'sochi': ('HC Sochi', 'хк сочи'), 'shanghai': ('Shanghai Dragons', 'китай шанхай dragons'),
}
NHL = {  # code: (slug, RU сокр. город, EN полное)
    'ANA': ('nhl_ana', 'Anaheim Ducks', 'утки'), 'BOS': ('nhl_bos', 'Boston Bruins', 'брюинз'),
    'BUF': ('nhl_buf', 'Buffalo Sabres', 'сейбрз'), 'CGY': ('nhl_cgy', 'Calgary Flames', 'флеймз'),
    'CAR': ('nhl_car', 'Carolina Hurricanes', 'харрикейнз'), 'CHI': ('nhl_chi', 'Chicago Blackhawks', 'блэкхокс'),
    'COL': ('nhl_col', 'Colorado Avalanche', 'эвеланш'), 'CBJ': ('nhl_cbj', 'Columbus Blue Jackets', 'блю джекетс'),
    'DAL': ('dallas', 'Dallas Stars', 'старз'), 'DET': ('nhl_det', 'Detroit Red Wings', 'ред уингз'),
    'EDM': ('nhl_edm', 'Edmonton Oilers', 'ойлерз'), 'FLA': ('nhl_fla', 'Florida Panthers', 'пантерз'),
    'LAK': ('nhl_lak', 'Los Angeles Kings', 'кингз'), 'MIN': ('minnesota', 'Minnesota Wild', 'уайлд'),
    'MTL': ('nhl_mtl', 'Montreal Canadiens', 'канадиенс хабс'), 'NSH': ('nhl_nsh', 'Nashville Predators', 'предаторз'),
    'NJD': ('nhl_njd', 'New Jersey Devils', 'девилз'), 'NYI': ('nhl_nyi', 'New York Islanders', 'айлендерс'),
    'NYR': ('nhl_nyr', 'New York Rangers', 'рейнджерс'), 'OTT': ('nhl_ott', 'Ottawa Senators', 'сенаторз'),
    'PHI': ('nhl_phi', 'Philadelphia Flyers', 'флайерз'), 'PIT': ('nhl_pit', 'Pittsburgh Penguins', 'пингвинз'),
    'SJS': ('nhl_sjs', 'San Jose Sharks', 'шаркс'), 'SEA': ('nhl_sea', 'Seattle Kraken', 'кракен'),
    'STL': ('nhl_stl', 'St. Louis Blues', 'блюз'), 'TBL': ('nhl_tbl', 'Tampa Bay Lightning', 'лайтнинг'),
    'TOR': ('nhl_tor', 'Toronto Maple Leafs', 'мейпл лифс'), 'UTA': ('nhl_uta', 'Utah Mammoth Hockey Club', 'маммот'),
    'VAN': ('nhl_van', 'Vancouver Canucks', 'кэнакс'), 'VGK': ('nhl_vgk', 'Vegas Golden Knights', 'голден найтс'),
    'WSH': ('nhl_wsh', 'Washington Capitals', 'кэпиталз'), 'WPG': ('nhl_wpg', 'Winnipeg Jets', 'джетс'),
}
NHL_BY_SLUG = {v[0]: (k, v[1], v[2]) for k, v in NHL.items()}

# --- футбол: синонимы топ-клубов (slug -> строка) ---
FOOT = {
    'manchester_city': 'ман сити сити горожане man city', 'manchester_united': 'ман юнайтед юнайтед манюнайтед man utd mu красные дьяволы',
    'barcelona': 'барса barca', 'real_madrid': 'реал мадрид королевский клуб', 'bayern_munich': 'бавария байерн bayern мюнхен',
    'paris_saint_germain': 'псж psg пари сен-жермен', 'internazionale': 'интер inter интернационале', 'milan': 'милан ac milan россонери',
    'juventus': 'юве ювентус старая синьора', 'atletico_madrid': 'атлетико атлетик мадрид', 'tottenham_hotspur': 'тоттенхэм шпоры spurs',
    'newcastle_united': 'ньюкасл сороки', 'arsenal': 'арсенал канониры', 'chelsea': 'челси', 'liverpool': 'ливерпуль мерсисайд',
    'borussia_dortmund': 'боруссия дортмунд борусия bvb', 'bayer_leverkusen': 'байер леверкузен', 'leipzig': 'лейпциг rb leipzig рб',
    'cska_moscow': 'цска цска армейцы cska', 'dinamo_moscow': 'динамо мск dynamo moscow', 'lokomotiv_moscow': 'локомотив локо москва',
    'spartak_moscow': 'спартак красно-белые', 'zenit_st_petersburg': 'зенит питер санкт-петербург zenit', 'krasnodar': 'краснодар быки',
    'rubin_kazan': 'рубин казань', 'akhmat_grozny': 'ахмат грозный', 'napoli': 'наполи неаполь', 'roma': 'рома', 'lazio': 'лацио',
    'atalanta': 'аталанта', 'sevilla': 'севилья', 'villarreal': 'вильярреал', 'real_betis': 'бетис', 'athletic_club': 'атлетик бильбао',
    'real_sociedad': 'реал сосьедад сосьедад', 'olympiacos': 'олимпиакос', 'shakhtar_donetsk': 'шахтер донецк shakhtar',
    'benfica': 'бенфика', 'porto': 'порту', 'sporting_cp': 'спортинг лиссабон', 'lyon': 'лион', 'marseille': 'марсель', 'monaco': 'монако',
    'galatasaray': 'галатасарай', 'fenerbahce': 'фенербахче', 'celtic': 'селтик', 'salzburg': 'ред булл зальцбург', 'psv_eindhoven': 'псв эйндховен',
    'feyenoord_rotterdam': 'фейеноорд', 'stuttgart': 'штутгарт', 'eintracht_frankfurt': 'айнтрахт франкфурт', 'brighton_hove_albion': 'брайтон',
    'nottingham_forest': 'ноттингем форест', 'aston_villa': 'астон вилла вилла',
}
LEAGUES = [
    ('h', 'khl', 'КХЛ', 'KHL Kontinental Hockey League', 'континентальная хоккейная лига', 'hockey/league.html?lg=khl'),
    ('h', 'nhl', 'НХЛ', 'NHL National Hockey League', 'национальная хоккейная лига', 'hockey/league.html?lg=nhl'),
    ('f', 'epl', 'АПЛ', 'Premier League EPL', 'английская премьер-лига англия премьер лига', 'football/league.html?lg=epl'),
    ('f', 'laliga', 'Ла Лига', 'La Liga', 'испания примера чемпионат испании', 'football/league.html?lg=laliga'),
    ('f', 'seriea', 'Серия А', 'Serie A', 'италия чемпионат италии', 'football/league.html?lg=seriea'),
    ('f', 'bundesliga', 'Бундеслига', 'Bundesliga', 'германия чемпионат германии', 'football/league.html?lg=bundesliga'),
    ('f', 'ligue1', 'Лига 1', 'Ligue 1', 'франция чемпионат франции', 'football/league.html?lg=ligue1'),
    ('f', 'rpl', 'РПЛ', 'Russian Premier League RPL', 'российская премьер-лига россия', 'football/league.html?lg=rpl'),
    ('f', 'ucl', 'Лига чемпионов', 'Champions League UCL', 'лч уефа', 'football/league.html?lg=ucl'),
    ('f', 'uel', 'Лига Европы', 'Europa League UEL', 'ле уефа', 'football/league.html?lg=uel'),
]


def now_msk():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=3)


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'daily'))
from split import en_name, ru_name  # noqa: E402


def main():
    now = now_msk()
    lo = (now - datetime.timedelta(days=DAYS)).strftime('%Y-%m-%d')
    hi = (now + datetime.timedelta(days=DAYS + 1)).strftime('%Y-%m-%d')
    clubs, matches, seen = [], [], set()

    # хоккей
    H = js_obj(os.path.join(ROOT, 'assets/data/teams.js'))
    for slug, t in H['teams'].items():
        lg = t['lg']
        if lg == 'khl':
            en, al = KHL.get(slug, ('', ''))
        else:
            code, en, al = NHL_BY_SLUG.get(slug, ('', '', ''))
            al = (al + ' ' + code.lower()).strip()
        clubs.append([slug, 'h', lg, t['name'], en, al])
        for g in t.get('games', []):
            d = g['d']
            if not (lo <= d[:10] <= hi) or g.get('h') != 1:
                continue
            key = (d, slug, g['o'])
            if key in seen:
                continue
            seen.add(key)
            sc = '%s:%s%s' % (g['gf'], g['ga'], (' ' + g['x']) if g.get('x') else '') if 'gf' in g else ''
            matches.append([d[:16], 'h', slug, g['o'], sc])

    # футбол
    F = js_obj(os.path.join(ROOT, 'football/data/football.js'))
    for slug, t in F['teams'].items():
        clubs.append([slug, 'f', t['lg'], t['n'], t.get('en', ''), FOOT.get(slug, '')])
        for g in t.get('games', []):
            d = g['d']
            if not (lo <= d[:10] <= hi) or g.get('h') != 1 or g['o'] not in F['teams']:
                continue
            key = (d, slug, g['o'])
            if key in seen:
                continue
            seen.add(key)
            sc = '%s:%s' % (g['gf'], g['ga']) if 'gf' in g else ''
            matches.append([d[:16], 'f', slug, g['o'], sc, g.get('c', '')])
    matches.sort(key=lambda m: m[0])
    for m in matches:
        while m and m[-1] == '':
            m.pop()

    leagues = [[s, lg, ru, en, al, url] for s, lg, ru, en, al, url in LEAGUES]

    # хоккеисты: [имя, хоккейная лига, slug клуба, очки за сезон, id игрока (профиль hockey/player.html)]; лучшие по очкам первыми
    players = []
    for lg, fn in (('nhl', 'nhl_players.json'), ('khl', 'khl_players.json')):
        p = os.path.join(ROOT, 'hockey/data', fn)
        if not os.path.exists(p):
            continue
        for pl in json.load(open(p, encoding='utf-8')).get('players', []):
            ru = ''
            if lg == 'khl':                      # на сайте имена КХЛ по-русски (13.11); латиница — для поиска
                ru, pl['n'] = en_name(pl['n']), ru_name(pl['n'])
            t = pl.get('t', '')
            slug = NHL[t][0] if lg == 'nhl' and t in NHL else t
            pts = sum((r[4] or 0) + (r[5] or 0) for r in pl.get('log', []))
            players.append([pl['n'], lg, slug, pts, pl.get('id')] + ([ru] if ru else []))
    players.sort(key=lambda x: -x[3])

    out = {'built': now.strftime('%Y-%m-%d %H:%M'), 'c': clubs, 'l': leagues, 'm': matches, 'p': players}
    s = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(s)
    n = len(s.encode('utf-8'))
    print('search.json: %d КБ, клубов %d, матчей %d, лиг %d, игроков %d' % (n // 1024, len(clubs), len(matches), len(leagues), len(players)))
    if n > LIMIT:
        print('ВНИМАНИЕ: индекс больше 150 КБ', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
