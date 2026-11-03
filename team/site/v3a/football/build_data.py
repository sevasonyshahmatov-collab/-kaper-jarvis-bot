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
LG = {'epl': 'АПЛ', 'laliga': 'Ла Лига', 'seriea': 'Серия А', 'bundesliga': 'Бундеслига', 'ligue1': 'Лига 1', 'rpl': 'РПЛ'}
FULL = {'epl': 'Английская Премьер-лига', 'laliga': 'Чемпионат Испании', 'seriea': 'Чемпионат Италии', 'bundesliga': 'Чемпионат Германии',
        'ligue1': 'Чемпионат Франции', 'rpl': 'Российская Премьер-лига'}

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
    mh, ma = hg / n, ag / n
    avg = (mh + ma) / 2
    K = 4

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
for lg, L in raw['leagues'].items():
    for i in L['ids']:
        t = raw['teams'][i]
        TEAMS[slug[i]] = {'id': slug[i], 'espn': i, 'n': ru(t), 'en': t['n'], 'ab': t['ab'], 'lg': lg, 'c': [t.get('c') or '1b2a44', t.get('c2') or '0b1220'],
                          'games': [], 'goals': {}, 'cards': {}}
for r in raw['table']:
    pass
tab = {}
for lg, rows in raw['table'].items():
    for r in rows:
        s = slug.get(r['id'])
        if s in TEAMS:
            T = TEAMS[s]
            T.update(place=int(r['rank'] or 0), gp=int(r['gp'] or 0), w=int(r['w'] or 0), d=int(r['d'] or 0), l=int(r['l'] or 0),
                     gf=int(r['gf'] or 0), ga=int(r['ga'] or 0), pts=int(r['pts'] or 0), note=r.get('note') or '')

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
            e = TEAMS[s]['goals'].setdefault(pid, {'n': nm, 'g': 0, 'p': 0}); e['g'] += 1; e['p'] += 1 if kind == 'pen' else 0
        for mn, tid, pid, nm, kind in g.get('c') or []:
            s = slug.get(tid)
            if not pid or not nm or s not in (h, a):
                continue
            e = TEAMS[s]['cards'].setdefault(pid, {'n': nm, 'y': 0, 'r': 0}); e[kind] += 1
    elif g['st'] == 'pre':
        pr, ov, bt, lh, la = MODEL[TEAMS[h]['lg']](g['h'], g['a'])
        k, t = odds(g.get('odds'))
        m = {'lg': TEAMS[h]['lg'], 't': g['d'], 'h': h, 'a': a, 'pr': pr, 'ov': ov, 'bt': bt, 'xg': [lh, la]}
        if k: m['k'] = k
        if t: m['tt'] = t
        UP.append(m)
        TEAMS[h]['games'].append({'d': g['d'], 'o': a, 'h': 1, 'pr': pr, 'ov': ov, 'bt': bt, **({'k': k} if k else {}), **({'tt': t} if t else {})})
        TEAMS[a]['games'].append({'d': g['d'], 'o': h, 'h': 0, 'pr': [pr[2], pr[1], pr[0]], 'ov': ov, 'bt': bt, **({'k': [k[2], k[1], k[0]]} if k else {}), **({'tt': t} if t else {})})

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
        P = [g for g in T['games'] if 'gf' in g]
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
    T['sc'] = sorted(({'n': v['n'], 'g': v['g'], 'p': v['p']} for v in T.pop('goals').values()), key=lambda x: (-x['g'], x['n']))[:12]
    T['cd'] = sorted(({'n': v['n'], 'y': v['y'], 'r': v['r']} for v in T.pop('cards').values()), key=lambda x: (-x['r'], -x['y'], x['n']))[:8]

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

out = {'built': raw['built'], 'axes': AX, 'season': '2026/27',
       'leagues': {k: {'name': LG[k], 'full': FULL[k], 'ids': [slug[i] for i in raw['leagues'][k]['ids']]} for k in LG},
       'teams': TEAMS, 'up': UP, 'h2h': H2H}
js = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
open(os.path.join(HERE, 'data', 'football.json'), 'w', encoding='utf-8').write(js)
open(os.path.join(HERE, 'data', 'football.js'), 'w', encoding='utf-8').write('window.JV_FOOT=' + js + ';')
print('клубов', len(TEAMS), 'ближайших матчей', len(UP), 'байт', len(js))
json.dump({v: k for k, v in slug.items() if k in raw['teams']}, open(os.path.join(HERE, 'data', 'slugs.json'), 'w'), ensure_ascii=False)
