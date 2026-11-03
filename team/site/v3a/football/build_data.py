# -*- coding: utf-8 -*-
"""Сборка данных футбольных страниц макета v3a: data/raw.json.gz (ESPN, собирает team/out/2026-11-03/foot_season.py в Actions)
→ data/football.json и data/football.js (window.JV_FOOT, для открытия с диска). Запуск: python3 build_data.py [путь/к/render/football.py].
Модель «по голам сезона»: сила атаки и обороны (сезон 2026/27 + 2025/26 с весом 0,35), распределение Пуассона. Это расчёт для сайта,
а не ставка канала (ставки канала — по смеси модели и линии, порог 60 % и кэф от 1,6)."""
import gzip, json, math, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
FB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', '..', '..', 'render', 'football.py')
raw = json.load(gzip.open(os.path.join(HERE, 'data', 'raw.json.gz'), 'rt', encoding='utf-8'))
RU = eval('{' + re.search(r'^RU = \{(.*?)^\}', open(FB, encoding='utf-8').read(), re.S | re.M).group(1) + '}')
RU.update({'Akhmat Grozny': 'Ахмат', 'Akron Tolyatti': 'Акрон', 'CSKA Moscow': 'ЦСКА', 'Dinamo Moscow': 'Динамо Москва',
           'Dynamo Makhachkala': 'Динамо Махачкала', 'FC Baltika Kaliningrad': 'Балтика', 'Fakel Voronezh': 'Факел',
           'Gazovik Orenburg': 'Оренбург', 'Krasnodar': 'Краснодар', 'Krylia Sovetov': 'Крылья Советов',
           'Lokomotiv Moscow': 'Локомотив', 'Rodina Moscow': 'Родина', 'Rostov': 'Ростов', 'Rubin Kazan': 'Рубин',
           'Spartak Moscow': 'Спартак', 'Zenit St Petersburg': 'Зенит'})
E2K = {v['espn']: k for k, v in raw['leagues'].items()}
for _g in raw['games'] + raw['prev']:
    _g['lg'] = E2K.get(_g['lg'], _g['lg'])
LG = {'epl': 'АПЛ', 'laliga': 'Ла Лига', 'seriea': 'Серия А', 'bundesliga': 'Бундеслига', 'ligue1': 'Лига 1', 'rpl': 'РПЛ', 'ucl': 'Лига чемпионов', 'uel': 'Лига Европы'}
CUPS = ('ucl', 'uel')
SHORT = {'ucl': 'ЛЧ', 'uel': 'ЛЕ'}
FULL = {'epl': 'Английская Премьер-лига', 'laliga': 'Чемпионат Испании', 'seriea': 'Чемпионат Италии', 'bundesliga': 'Чемпионат Германии',
        'ligue1': 'Чемпионат Франции', 'rpl': 'Российская Премьер-лига', 'ucl': 'Турнир УЕФА, общий этап', 'uel': 'Турнир УЕФА, общий этап'}

# slug: из slug ESPN без префикса лиги
slug, used = {}, set()
import unicodedata
DROP = {'afc', 'fc', 'fk', 'cf', 'ac', 'as', 'sc', 'sv', 'vfb', 'vfl', 'tsg', 'rb', 'aj', 'ud', 'cd', 'rc', 'us', 'ss', 'ssc', 'og', 'stade', '1'}
for i, t in raw['teams'].items():
    nm = unicodedata.normalize('NFKD', t['n']).encode('ascii', 'ignore').decode().lower()
    w = [x for x in re.split(r'[^a-z0-9]+', nm) if x and x not in DROP]
    s = '_'.join(w) or re.sub(r'[^a-z0-9]+', '_', nm).strip('_')
    if s in used:
        s = t['lg'] + '_' + s
    used.add(s); slug[i] = s
ru = lambda t: RU.get(t['n'], t['n'])


def dec(a):
    try:
        a = float(str(a).replace('+', ''))
    except (TypeError, ValueError):
        return None
    return round(1 + (a / 100 if a > 0 else 100 / -a), 2)


def odds(o):
    if not o:
        return None, None
    ml = o.get('moneyline') or {}
    g = lambda side: dec(((ml.get(side) or {}).get('close') or {}).get('odds'))
    k = [g('home'), g('draw'), g('away')]
    tt = o.get('total') or {}
    ov = dec((((tt.get('over') or {}).get('close')) or {}).get('odds')); un = dec((((tt.get('under') or {}).get('close')) or {}).get('odds'))
    t = [o.get('overUnder'), ov, un] if ov and un and o.get('overUnder') else None
    return (k if all(k) else None), t


def pois(l, n=10):
    p = [math.exp(-l)]
    for i in range(1, n):
        p.append(p[-1] * l / i)
    return p


def model(lg):
    """сила атаки/обороны по лиге → функция (h, a) → вероятности"""
    cur = [g for g in raw['games'] if g['lg'] == lg and g.get('hs') is not None and g['st'] == 'post']
    prv = [g for g in raw['prev'] if g['lg'] == lg and g.get('hs') is not None and g['st'] == 'post'
           and g['h'] in raw['teams'] and g['a'] in raw['teams']]
    W = defaultdict(lambda: [0, 0, 0])   # вес, забито, пропущено
    hg = ag = n = 0
    for gs, w in ((cur, 1.0), (prv, .35)):
        for g in gs:
            for me, gf, ga in ((g['h'], g['hs'], g['as']), (g['a'], g['as'], g['hs'])):
                x = W[me]; x[0] += w; x[1] += w * gf; x[2] += w * ga
            hg += w * g['hs']; ag += w * g['as']; n += w
    if not n:
        return lambda h, a: ([.45, .27, .28], .5, .5, 1.4, 1.1)
    mh, ma = hg / n, ag / n
    avg = (mh + ma) / 2
    K = 10 if lg in CUPS else 4

    def st(i):
        w, gf, ga = W[i]
        return ((gf + K * avg) / (w + K)) / avg, ((ga + K * avg) / (w + K)) / avg

    def f(h, a):
        ah, dh = st(h); aa, da = st(a)
        lh, la = mh * ah * da, ma * aa * dh
        ph, pa = pois(lh), pois(la)
        p1 = px = p2 = ov = bt = 0
        for i in range(10):
            for j in range(10):
                p = ph[i] * pa[j]
                if i > j: p1 += p
                elif i == j: px += p
                else: p2 += p
                if i + j > 2: ov += p
                if i > 0 and j > 0: bt += p
        s = p1 + px + p2
        return [round(p1 / s, 3), round(px / s, 3), round(p2 / s, 3)], round(ov / s, 3), round(bt / s, 3), round(lh, 2), round(la, 2)
    return f


MODEL = {lg: model(lg) for lg in LG}
TEAMS = {}
for cup_pass in (0, 1):
    for lg, L in raw['leagues'].items():
        if (lg in CUPS) != bool(cup_pass):
            continue
        for i in L['ids']:
            if slug[i] in TEAMS:
                continue
            t = raw['teams'][i]
            TEAMS[slug[i]] = {'id': slug[i], 'espn': i, 'n': ru(t), 'en': t['n'], 'ab': t['ab'], 'lg': lg, 'c': [t.get('c') or '1b2a44', t.get('c2') or '0b1220'],
                              'games': [], 'goals': {}, 'cards': {}, 'cups': []}
TABLES = {}
for lg, rows in raw['table'].items():
    TABLES[lg] = []
    for r in rows:
        s_ = slug.get(r['id'])
        if s_ not in TEAMS:
            continue
        v = dict(id=s_, place=int(r['rank'] or 0), gp=int(r['gp'] or 0), w=int(r['w'] or 0), d=int(r['d'] or 0), l=int(r['l'] or 0),
                 gf=int(r['gf'] or 0), ga=int(r['ga'] or 0), pts=int(r['pts'] or 0))
        TABLES[lg].append(v)
        if lg in CUPS:
            if s_ not in [x for x in TEAMS[s_]['cups']]:
                TEAMS[s_]['cups'].append(lg)
            if TEAMS[s_]['lg'] == lg:
                TEAMS[s_].update({k: v[k] for k in ('place', 'gp', 'w', 'd', 'l', 'gf', 'ga', 'pts')}, note=r.get('note') or '')
        else:
            TEAMS[s_].update({k: v[k] for k in ('place', 'gp', 'w', 'd', 'l', 'gf', 'ga', 'pts')}, note=r.get('note') or '')
for lg in CUPS:   # клуб кубка без таблицы кубка (редко): всё равно отмечаем по составу
    for i in raw['leagues'][lg]['ids']:
        if lg not in TEAMS[slug[i]]['cups']:
            TEAMS[slug[i]]['cups'].append(lg)
for T_ in TEAMS.values():
    for k in ('place', 'gp', 'w', 'd', 'l', 'gf', 'ga', 'pts'):
        T_.setdefault(k, 0)
    T_.setdefault('note', '')

CTXK = lambda g: g['lg'] if g['lg'] in CUPS else 'l'
# матчи сезона и ближайшие
UP = []
for g in sorted(raw['games'], key=lambda x: x['d']):
    if g['sn'] == 'STATUS_ABANDONED' or g['h'] not in slug or g['a'] not in slug:
        continue
    h, a = slug[g['h']], slug[g['a']]
    if h not in TEAMS or a not in TEAMS:
        continue
    played = g['st'] == 'post' and g.get('hs') is not None
    for me, op, home, gf, ga, mx, ox in ((h, a, 1, g.get('hs'), g.get('as'), g.get('hx'), g.get('ax')), (a, h, 0, g.get('as'), g.get('hs'), g.get('ax'), g.get('hx'))):
        row = {'d': g['d'], 'o': op, 'h': home}
        if g['lg'] in CUPS:
            row['c'] = g['lg']
        if played:
            row['gf'], row['ga'] = gf, ga
            if mx: row['x'] = {k: v for k, v in mx.items() if k in ('sh', 'sot', 'cor', 'pos')}
            if ox: row['y'] = {k: v for k, v in ox.items() if k in ('sh', 'sot', 'cor', 'pos')}
        if played:
            TEAMS[me]['games'].append(row)
    if played:
        for mn, tid, pid, nm, kind in g.get('g') or []:
            s = slug.get(tid)
            if not pid or not nm or kind == 'og' or s not in (h, a):
                continue
            e = TEAMS[s]['goals'].setdefault(CTXK(g), {}).setdefault(pid, {'n': nm, 'g': 0, 'p': 0}); e['g'] += 1; e['p'] += 1 if kind == 'pen' else 0
        for mn, tid, pid, nm, kind in g.get('c') or []:
            s = slug.get(tid)
            if not pid or not nm or s not in (h, a):
                continue
            e = TEAMS[s]['cards'].setdefault(CTXK(g), {}).setdefault(pid, {'n': nm, 'y': 0, 'r': 0}); e[kind] += 1
    elif g['st'] == 'pre':
        mk = g['lg'] if g['lg'] in CUPS else TEAMS[h]['lg']
        pr, ov, bt, lh, la = MODEL[mk](g['h'], g['a'])
        k, t = odds(g.get('odds'))
        m = {'lg': mk, 't': g['d'], 'h': h, 'a': a, 'pr': pr, 'ov': ov, 'bt': bt, 'xg': [lh, la]}
        if k: m['k'] = k
        if t: m['tt'] = t
        UP.append(m)
        TEAMS[h]['games'].append({'d': g['d'], 'o': a, 'h': 1, **({'c': mk} if mk in CUPS else {}), 'pr': pr, 'ov': ov, 'bt': bt, **({'k': k} if k else {}), **({'tt': t} if t else {})})
        TEAMS[a]['games'].append({'d': g['d'], 'o': h, 'h': 0, **({'c': mk} if mk in CUPS else {}), 'pr': [pr[2], pr[1], pr[0]], 'ov': ov, 'bt': bt, **({'k': [k[2], k[1], k[0]]} if k else {}), **({'tt': t} if t else {})})

# оси «силы»: место среди клубов лиги, 0–100 (100 — лучший)
def pct(vals):
    out = {}
    s = sorted(vals.items(), key=lambda kv: kv[1])
    n = len(s)
    for key, v in vals.items():
        lo = sum(1 for _, x in s if x < v); eq = sum(1 for _, x in s if x == v)
        out[key] = round(100 * (lo + (eq - 1) / 2) / max(1, n - 1))
    return out


AX = ['Атака', 'Защита', 'Форма', 'Дома', 'В гостях', 'Очки']
for lg in LG:
    ts = [T for T in TEAMS.values() if T['lg'] == lg]
    base = {}
    for T in ts:
        P = [g for g in T['games'] if 'gf' in g and ('c' not in g or T['lg'] in CUPS)]
        n = max(1, len(P))
        ppg = lambda gs: sum(3 if g['gf'] > g['ga'] else 1 if g['gf'] == g['ga'] else 0 for g in gs) / max(1, len(gs))
        H = [g for g in P if g['h']]; A = [g for g in P if not g['h']]
        base[T['id']] = (sum(g['gf'] for g in P) / n, -sum(g['ga'] for g in P) / n, ppg(P[-5:]), ppg(H), ppg(A), ppg(P))
        T['raw'] = [round(base[T['id']][0], 2), round(-base[T['id']][1], 2), round(ppg(P[-5:]), 2), round(ppg(H), 2), round(ppg(A), 2), round(ppg(P), 2)]
    for j in range(6):
        p = pct({k: v[j] for k, v in base.items()})
        for T in ts:
            T.setdefault('axes', [0] * 6)[j] = p[T['id']]
for T in TEAMS.values():
    T['games'].sort(key=lambda g: g['d'])
    G, C_ = T.pop('goals'), T.pop('cards')
    fs = lambda d: sorted(({'n': v['n'], 'g': v['g'], 'p': v['p']} for v in d.values()), key=lambda x: (-x['g'], x['n']))[:12]
    fc = lambda d: sorted(({'n': v['n'], 'y': v['y'], 'r': v['r']} for v in d.values()), key=lambda x: (-x['r'], -x['y'], x['n']))[:8]
    T['sc'] = fs(G.get(T['lg'] if T['lg'] in CUPS else 'l', {})); T['cd'] = fc(C_.get(T['lg'] if T['lg'] in CUPS else 'l', {}))
    T['scx'] = {k: fs(G.get(k, {})) for k in CUPS if k in T['cups']}; T['cdx'] = {k: fc(C_.get(k, {})) for k in CUPS if k in T['cups']}

# личные встречи прошлого сезона
H2H = defaultdict(list)
for g in sorted(raw['prev'], key=lambda x: x['d']):
    if g['st'] != 'post' or g.get('hs') is None or g['h'] not in slug or g['a'] not in slug:
        continue
    h, a = slug[g['h']], slug[g['a']]
    if h in TEAMS and a in TEAMS:
        H2H['|'.join(sorted((h, a)))].append({'s': '2025/26', 'd': g['d'][:10], 'h': h, 'hs': g['hs'], 'as': g['as']})
for g in raw['games']:
    if g['st'] == 'post' and g.get('hs') is not None and g['h'] in slug and g['a'] in slug and slug[g['h']] in TEAMS and slug[g['a']] in TEAMS:
        h, a = slug[g['h']], slug[g['a']]
        H2H['|'.join(sorted((h, a)))].append({'s': '2026/27', 'd': g['d'][:10], 'h': h, 'hs': g['hs'], 'as': g['as']})
for v in H2H.values():
    v.sort(key=lambda x: x['d'])


# ── Рейтинг Club Elo (clubelo.com: страницы стран, топ-25 каждой) и «сила» в контексте еврокубка ──
import unicodedata as _u
ELO = json.load(open(os.path.join(HERE, 'data', 'elo_raw.json'), encoding='utf-8'))
EBN = {r['n']: r for r in ELO}
ALIAS = {'Brighton & Hove Albion': 'Brighton', 'Leeds United': 'Leeds', 'Nottingham Forest': 'Forest', 'Borussia Mönchengladbach': 'Gladbach',
         'FC Cologne': 'Köln', 'Paris Saint-Germain': 'Paris SG', 'Stade Rennais': 'Rennes', 'Dinamo Moscow': 'Dynamo Moskva',
         'FC Baltika Kaliningrad': 'Baltika', 'Lokomotiv Moscow': 'Lok Moskva', 'Zenit St Petersburg': 'Zenit', 'AEK Athens': 'AEK',
         'Club Brugge': 'Brugge', 'PSV Eindhoven': 'PSV', 'Slovan Bratislava': 'Slovan', 'AZ Alkmaar': 'AZ', 'Lech Poznan': 'Lech',
         'Levski Sofia': 'Levski', 'OFI Crete': 'OFI', 'Omonia Nicosia': 'Omonia', 'Akhmat Grozny': 'Terek Grozny', 'Internazionale': 'Internazionale',
         'Bayern Munich': 'Bayern München', 'Manchester City': 'Man City', 'Manchester United': 'Man United', 'Atlético Madrid': 'Atlético',
         'Real Betis': 'Betis', 'AC Milan': 'Milan', 'AS Roma': 'Roma', 'Sporting CP': 'Sporting', 'FC Porto': 'Porto', 'Shakhtar Donetsk': 'Shakhtar',
         'Olympiacos': 'Olympiakos', 'Fenerbahce': 'Fenerbahçe', 'Slavia Prague': 'Slavia Praha', 'Sparta Prague': 'Sparta Praha', 'CSKA Moscow': 'CSKA Moskva',
         'Spartak Moscow': 'Spartak Moskva', 'Krasnodar': 'FC Krasnodar', 'Krylia Sovetov': 'Kryliya Sovetov', 'Rodina Moscow': 'Rodina Moskva',
         'Gazovik Orenburg': 'Orenburg', 'Dynamo Makhachkala': 'Makhachkala', 'Feyenoord Rotterdam': 'Feyenoord', 'Bodo/Glimt': 'Bodø/Glimt',
         'Viktoria Plzen': 'Viktoria Plzeň', 'Lillestrom': 'Lillestrøm', 'Jagiellonia Bialystok': 'Jagiellonia', 'NEC Nijmegen': 'Nijmegen',
         'NK Celje': 'Celje', 'LASK Linz': 'LASK', 'Hull City': 'Hull', 'Coventry City': 'Coventry', 'Ipswich Town': 'Ipswich', 'Newcastle United': 'Newcastle',
         'Tottenham Hotspur': 'Tottenham', 'AFC Bournemouth': 'Bournemouth', 'Alavés': 'Alaves', 'Celta Vigo': 'Celta', 'Deportivo': 'Depor',
         'Racing Santander': 'Santander', 'Bayer Leverkusen': 'Leverkusen', 'Eintracht Frankfurt': 'Frankfurt', 'FC Augsburg': 'Augsburg',
         'Hamburg SV': 'Hamburg', 'SC Freiburg': 'Freiburg', 'SC Paderborn 07': 'Paderborn', 'SV Elversberg': 'Elversberg', 'TSG Hoffenheim': 'Hoffenheim',
         'VfB Stuttgart': 'Stuttgart', 'Werder Bremen': 'Werder', 'Borussia Dortmund': 'Dortmund', '1. FC Union Berlin': 'Union Berlin', 'AJ Auxerre': 'Auxerre',
         'AS Monaco': 'Monaco', 'SK Sturm Graz': 'Sturm Graz', 'Viking FK': 'Viking', 'Schalke 04': 'Schalke', 'Le Havre AC': 'Le Havre', 'Borussia Dortmund ': 'Dortmund'}
def _norm(x):
    return _u.normalize('NFKD', x).encode('ascii', 'ignore').decode().lower()
EBNORM = {_norm(r['n']): r for r in ELO}
elo_of, ELO_EST = {}, set()
for sl, T_ in TEAMS.items():
    en = T_['en']
    r = EBN.get(ALIAS.get(en, en)) or EBNORM.get(_norm(ALIAS.get(en, en)))
    if r:
        elo_of[sl] = r
# среднее по странам (клубы высшего дивизиона из топ-25 страницы страны)
CMEAN = {}
for r in ELO:
    if r.get('l') == 1:
        CMEAN.setdefault(r['c'], []).append(r['e'])
CMEAN = {k: sum(v) / len(v) for k, v in CMEAN.items() if len(v) >= 3}
LGC = {'epl': 'ENG', 'laliga': 'ESP', 'seriea': 'ITA', 'bundesliga': 'GER', 'ligue1': 'FRA', 'rpl': 'RUS'}
def country(sl):
    r = elo_of.get(sl)
    return r['c'] if r else LGC.get(TEAMS[sl]['lg'])
# оценка для клубов, которых нет в рейтинге: среднее Elo их лиги + поправка по месту (+150 лидеру … −150 последнему)
for sl, T_ in TEAMS.items():
    if sl in elo_of:
        continue
    same = [elo_of[x]['e'] for x, t in TEAMS.items() if t['lg'] == T_['lg'] and x in elo_of]
    base = sum(same) / len(same) if same else 1650
    n = max(2, len([1 for t in TEAMS.values() if t['lg'] == T_['lg']]))
    pl = T_['place'] or n // 2
    elo_of[sl] = {'n': T_['en'], 'c': country(sl), 'l': 1, 'e': round(base + 150 * (1 - 2 * (pl - 1) / (n - 1)), 1)}
    ELO_EST.add(sl)
EVAL = sorted([r['e'] for r in ELO] + [elo_of[x]['e'] for x in ELO_EST], reverse=True)
def erank(e):
    return 1 + sum(1 for v in EVAL if v > e + 1e-9)
def played_all(T_):
    return [g for g in T_['games'] if 'gf' in g]
AXC = ['Сила', 'Атака', 'Защита', 'Форма', 'Дома', 'В гостях']
for cup in CUPS:
    ids = [slug[i] for i in raw['leagues'][cup]['ids']]
    ctry = {x: country(x) for x in ids}
    cm = {x: CMEAN.get(ctry[x]) for x in ids}
    known = [v for v in cm.values() if v]
    avg_c = sum(known) / len(known) if known else 1700
    coef = {x: (cm[x] / avg_c if cm[x] else 1.0) for x in ids}
    # средние по лигам и в кубке — для усадки
    cupg = [g for x in ids for g in TEAMS[x]['games'] if g.get('c') == cup and 'gf' in g]
    cup_avg = sum(g['gf'] for g in cupg) / len(cupg) if cupg else 1.4
    def lg_avg(lgk):
        gs = [g for t in TEAMS.values() if t['lg'] == lgk for g in t['games'] if 'gf' in g and 'c' not in g]
        return sum(g['gf'] for g in gs) / len(gs) if gs else 1.4
    LA = {k: lg_avg(k) for k in LG if k not in CUPS}
    raw_v = {}
    for x in ids:
        T_ = TEAMS[x]
        dom = [g for g in T_['games'] if 'gf' in g and 'c' not in g]
        cp = [g for g in T_['games'] if 'gf' in g and g.get('c') == cup]
        la = LA.get(T_['lg'], cup_avg)
        cgf = (sum(g['gf'] for g in cp) + 3 * cup_avg) / (len(cp) + 3)
        cga = (sum(g['ga'] for g in cp) + 3 * cup_avg) / (len(cp) + 3)
        if dom:
            dgf = (sum(g['gf'] for g in dom) + 4 * la) / (len(dom) + 4) * coef[x]
            dga = (sum(g['ga'] for g in dom) + 4 * la) / (len(dom) + 4) / coef[x]
            att, dfn = .6 * dgf + .4 * cgf, .6 * dga + .4 * cga
        else:
            att, dfn = cgf, cga
        allp = sorted(played_all(T_), key=lambda g: g['d'])
        def wp(gs):
            return sum((3 if g['gf'] > g['ga'] else 1 if g['gf'] == g['ga'] else 0) * (elo_of[g['o']]['e'] / 1800) for g in gs) / len(gs) if gs else 0
        raw_v[x] = (elo_of[x]['e'], att, -dfn, wp(allp[-8:]), wp([g for g in allp if g['h']]), wp([g for g in allp if not g['h']]))
    for j in range(6):
        p = pct({x: raw_v[x][j] for x in ids})
        for x in ids:
            TEAMS[x].setdefault('cx', {}).setdefault(cup, {'axes': [0] * 6, 'e': round(elo_of[x]['e']), 'r': erank(elo_of[x]['e']), 'est': x in ELO_EST})['axes'][j] = p[x]
    for x in ids:
        TEAMS[x]['cx'][cup]['raw'] = [round(v, 2) for v in raw_v[x][1:3]]
out = {'built': raw['built'], 'axes': AX, 'season': '2026/27',
       'leagues': {k: {'name': LG[k], 'full': FULL[k], 'ids': [slug[i] for i in raw['leagues'][k]['ids']], 'short': SHORT.get(k, LG[k]), 'cup': k in CUPS} for k in LG},
       'tables': TABLES, 'axesCup': AXC, 'elo': {'date': raw['built'][:10], 'src': 'Club Elo (clubelo.com)', 'estimated': sorted(ELO_EST)}, 'teams': TEAMS, 'up': UP, 'h2h': H2H}
js = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
open(os.path.join(HERE, 'data', 'football.json'), 'w', encoding='utf-8').write(js)
open(os.path.join(HERE, 'data', 'football.js'), 'w', encoding='utf-8').write('window.JV_FOOT=' + js + ';')
print('клубов', len(TEAMS), 'ближайших матчей', len(UP), 'байт', len(js))
json.dump({v: k for k, v in slug.items() if k in raw['teams']}, open(os.path.join(HERE, 'data', 'slugs.json'), 'w'), ensure_ascii=False)
