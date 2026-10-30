# -*- coding: utf-8 -*-
"""Футбол: широкая роспись матча и статистика команд (владелец 30.10: «максимально широкая линия по матчам,
индивидуальная статистика команд, рейтинги клубов»).

Рынки (за 90 минут, вероятности модели):
  • голы — счёт по Дикси-Коулсу (football_model.py): 1Х2, двойной шанс, ничья — возврат (П1/П2 без ничьей), азиатские
    и европейские форы, тоталы 0,5–5,5, инд. тоталы 0,5–3,5, обе забьют (и с исходом / тоталом), чёт/нечет,
    точный счёт, разница, «сухой» матч, победа всухую, комбинации «исход + тотал»;
  • таймы — голы 1-го и 2-го тайма отдельно (доля голов 1-го тайма лиги): 1Х2 и тоталы 1-го тайма, «тайм с бо́льшим
    числом голов», забьют в обоих таймах;
  • угловые, жёлтые карточки, удары в створ — свой рейтинг «за / против» по каждой статистике (как голы) и
    отрицательное биномиальное распределение (разброс по лиге): тоталы матча и команд, фора / «у кого больше».
Проверка на истории — `python team/picks/football_wide.py --bt` (2025/26 вслепую: обещано / зашло по видам рынков).
Только модель: кэфов на эти рынки в истории нет — «ВЫБОР» по ним не ставим, пока заходимость не подтвердится."""
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import football_hist as FH  # noqa: E402
import football_model as FM  # noqa: E402

STATS = {'co': 'угловые', 'yc': 'жёлтые', 'st': 'в створ'}
SP = dict(hl=300.0, alpha=0.0, k=6.0, new_a=1.0, new_d=1.0, rho=0.0, iters=10)     # рейтинг статистик
LINES = {'co': [x + 0.5 for x in range(5, 16)], 'yc': [x + 0.5 for x in range(1, 9)], 'st': [x + 0.5 for x in range(4, 15)]}
TLINES = {'co': [x + 0.5 for x in range(0, 10)], 'yc': [x + 0.5 for x in range(0, 6)], 'st': [x + 0.5 for x in range(0, 10)]}
MAXN = 40


def out(tag, text):
    print(tag + ' ' + text, flush=True)


# ---------- рейтинг статистик ----------
def stat_games(games, key):
    return [dict(d=g['d'], s=g['s'], h=g['h'], a=g['a'], hg=g[key][0], ag=g[key][1]) for g in games if key in g]


def stat_fit(games, key, day, known=None):
    sg = stat_games(games, key)
    return FM.fit(sg, day, SP, known)


def dispersion(games, key, day, seasons=2):
    """Размер r отрицательного биномиального: дисперсия = μ + μ²/r (по командам за последние сезоны, метод моментов)."""
    s0 = FH.season_of(day) - seasons
    xs = [g[key][i] for g in games if key in g and s0 <= g['s'] and g['d'] < day for i in (0, 1)]
    if len(xs) < 50:
        return 30.0
    m = sum(xs) / len(xs)
    v = sum((x - m) ** 2 for x in xs) / len(xs)
    # часть разброса — разная сила команд (~15 % дисперсии), остальное — случайность матча
    ex = 0.85 * v - m
    return max(4.0, min(200.0, m * m / ex)) if ex > 0 else 200.0


def nb_pmf(mu, r, n=MAXN):
    p = r / (r + mu)
    out_ = [p ** r]
    for k in range(1, n):
        out_.append(out_[-1] * (k - 1 + r) / k * (1 - p))
    s = sum(out_)
    return [x / s for x in out_]


def ht_share(games, day):
    hs = [g for g in games if 'ht' in g and g['d'] < day and FH.season_of(day) - 2 <= g['s']]
    tot = sum(g['hg'] + g['ag'] for g in hs)
    return sum(g['ht'][0] + g['ht'][1] for g in hs) / tot if tot else 0.44


# ---------- рынки ----------
def pois(l, n=11):
    return [math.exp(-l) * l ** i / math.factorial(i) for i in range(n)]


def goal_markets(lh, la, rho, share):
    M = FM.score_matrix(lh, la, rho)
    N = FM.MAXG
    r = {}
    P = lambda f: sum(M[i][j] for i in range(N) for j in range(N) if f(i, j))  # noqa: E731
    p1, px, p2 = P(lambda i, j: i > j), P(lambda i, j: i == j), P(lambda i, j: i < j)
    r.update({'П1': p1, 'Х': px, 'П2': p2, '1Х': p1 + px, '12': p1 + p2, 'Х2': px + p2,
              'П1 (ничья — возврат)': p1 / (p1 + p2), 'П2 (ничья — возврат)': p2 / (p1 + p2)})
    for hc in [x + 0.5 for x in range(-4, 4)]:
        r['Ф1 %+.1f' % hc] = P(lambda i, j: i - j + hc > 0)
        r['Ф2 %+.1f' % hc] = P(lambda i, j: j - i + hc > 0)
    for hc in (-2, -1, 1, 2):          # целые форы: без возврата — вероятность выигрыша при условии «не возврат»
        w = P(lambda i, j: i - j + hc > 0)
        push = P(lambda i, j: i - j + hc == 0)
        r['Ф1 %+d (возврат при %s)' % (hc, 'ровно')] = w / (1 - push)
        w2 = P(lambda i, j: j - i + hc > 0)
        push2 = P(lambda i, j: j - i + hc == 0)
        r['Ф2 %+d (возврат при %s)' % (hc, 'ровно')] = w2 / (1 - push2)
    for ln in (0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5):
        r['ТБ %.1f' % ln] = P(lambda i, j: i + j > ln)
        r['ТМ %.1f' % ln] = 1 - r['ТБ %.1f' % ln]
    for ln in (0.5, 1.5, 2.5, 3.5, 4.5):
        r['ИТ1Б %.1f' % ln] = P(lambda i, j: i > ln)
        r['ИТ1М %.1f' % ln] = 1 - r['ИТ1Б %.1f' % ln]
        r['ИТ2Б %.1f' % ln] = P(lambda i, j: j > ln)
        r['ИТ2М %.1f' % ln] = 1 - r['ИТ2Б %.1f' % ln]
    r['ОЗ да'] = P(lambda i, j: i > 0 and j > 0)
    r['ОЗ нет'] = 1 - r['ОЗ да']
    for ln in (1.5, 2.5, 3.5, 4.5):
        for yn, fb in (('да', lambda i, j: i > 0 and j > 0), ('нет', lambda i, j: i == 0 or j == 0)):
            r['ОЗ %s + ТБ %.1f' % (yn, ln)] = P(lambda i, j, fb=fb, ln=ln: fb(i, j) and i + j > ln)
            r['ОЗ %s + ТМ %.1f' % (yn, ln)] = P(lambda i, j, fb=fb, ln=ln: fb(i, j) and i + j < ln)
    for hc in (-3, -2, -1, 1, 2, 3):      # европейская фора (3 исхода) хозяев
        r['ЕФ1 %+d' % hc] = P(lambda i, j, hc=hc: i + hc > j)
        r['ЕФ Х %+d' % hc] = P(lambda i, j, hc=hc: i + hc == j)
        r['ЕФ2 %+d' % hc] = P(lambda i, j, hc=hc: i + hc < j)
    for nm, f in (('П1', lambda i, j: i > j), ('Х', lambda i, j: i == j), ('П2', lambda i, j: i < j),
                  ('1Х', lambda i, j: i >= j), ('Х2', lambda i, j: i <= j)):
        r['%s + ОЗ да' % nm] = P(lambda i, j, f=f: f(i, j) and i > 0 and j > 0)
        r['%s + ОЗ нет' % nm] = P(lambda i, j, f=f: f(i, j) and (i == 0 or j == 0))
        for ln in (1.5, 2.5, 3.5):
            r['%s + ТБ %.1f' % (nm, ln)] = P(lambda i, j, f=f, ln=ln: f(i, j) and i + j > ln)
            r['%s + ТМ %.1f' % (nm, ln)] = P(lambda i, j, f=f, ln=ln: f(i, j) and i + j < ln)
    r['чёт'] = P(lambda i, j: (i + j) % 2 == 0)
    r['нечет'] = 1 - r['чёт']
    r['сухой у хозяев (гости не забьют)'] = P(lambda i, j: j == 0)
    r['сухой у гостей (хозяева не забьют)'] = P(lambda i, j: i == 0)
    r['П1 всухую'] = P(lambda i, j: i > j and j == 0)
    r['П2 всухую'] = P(lambda i, j: j > i and i == 0)
    for d in (1, 2):
        r['П1 ровно в %d' % d] = P(lambda i, j, d=d: i - j == d)
        r['П2 ровно в %d' % d] = P(lambda i, j, d=d: j - i == d)
    r['П1 в 3 и больше'] = P(lambda i, j: i - j >= 3)
    r['П2 в 3 и больше'] = P(lambda i, j: j - i >= 3)
    cs = sorted(((M[i][j], '%d:%d' % (i, j)) for i in range(6) for j in range(6)), reverse=True)[:8]
    for p, sc in cs:
        r['счёт ' + sc] = p
    # таймы: голы 1-го тайма ~ Пуассон(λ·доля), 2-го — λ·(1 − доля), независимо
    h1, a1 = pois(lh * share), pois(la * share)
    h2, a2 = pois(lh * (1 - share)), pois(la * (1 - share))
    n = len(h1)
    Q = lambda h, a, f: sum(h[i] * a[j] for i in range(n) for j in range(n) if f(i, j))  # noqa: E731
    r['1-й тайм П1'] = Q(h1, a1, lambda i, j: i > j)
    r['1-й тайм Х'] = Q(h1, a1, lambda i, j: i == j)
    r['1-й тайм П2'] = Q(h1, a1, lambda i, j: i < j)
    r['1-й тайм ОЗ да'] = (1 - h1[0]) * (1 - a1[0])
    for ln in (0.5, 1.5):
        r['1-й тайм ИТ1Б %.1f' % ln] = sum(h1[i] for i in range(n) if i > ln)
        r['1-й тайм ИТ2Б %.1f' % ln] = sum(a1[i] for i in range(n) if i > ln)
    for ln in (0.5, 1.5, 2.5, 3.5):
        r['1-й тайм ТБ %.1f' % ln] = Q(h1, a1, lambda i, j, ln=ln: i + j > ln)
        r['1-й тайм ТМ %.1f' % ln] = 1 - r['1-й тайм ТБ %.1f' % ln]
    for hc in (-1.5, -0.5, 0.5, 1.5):
        r['1-й тайм Ф1 %+.1f' % hc] = Q(h1, a1, lambda i, j, hc=hc: i - j + hc > 0)
        r['1-й тайм Ф2 %+.1f' % hc] = Q(h1, a1, lambda i, j, hc=hc: j - i + hc > 0)
    for ln in (0.5, 1.5, 2.5):
        r['2-й тайм ТБ %.1f' % ln] = Q(h2, a2, lambda i, j, ln=ln: i + j > ln)
        r['2-й тайм ТМ %.1f' % ln] = 1 - r['2-й тайм ТБ %.1f' % ln]
    t1 = [sum(h1[i] * a1[k - i] for i in range(k + 1) if i < n and k - i < n) for k in range(2 * n - 1)]
    t2 = [sum(h2[i] * a2[k - i] for i in range(k + 1) if i < n and k - i < n) for k in range(2 * n - 1)]
    r['больше голов во 2-м тайме'] = sum(t1[i] * t2[j] for i in range(len(t1)) for j in range(len(t2)) if j > i)
    r['больше голов в 1-м тайме'] = sum(t1[i] * t2[j] for i in range(len(t1)) for j in range(len(t2)) if i > j)
    r['голы в обоих таймах'] = (1 - t1[0]) * (1 - t2[0])
    r['хозяева забьют в обоих таймах'] = (1 - h1[0]) * (1 - h2[0])
    r['гости забьют в обоих таймах'] = (1 - a1[0]) * (1 - a2[0])
    return r


def stat_markets(key, mh, ma, r_):
    """Тоталы статистики (угловые, жёлтые, удары в створ): матч, команды, «у кого больше»."""
    ph, pa = nb_pmf(mh, r_), nb_pmf(ma, r_)
    n = len(ph)
    tot = [0.0] * (2 * n)
    for i in range(n):
        for j in range(n):
            tot[i + j] += ph[i] * pa[j]
    nm = STATS[key]
    r = {}
    for ln in LINES[key]:
        o = sum(v for k, v in enumerate(tot) if k > ln)
        r['%s: ТБ %.1f' % (nm, ln)] = o
        r['%s: ТМ %.1f' % (nm, ln)] = 1 - o
    for ln in TLINES[key]:
        r['%s хозяев: Б %.1f' % (nm, ln)] = sum(v for k, v in enumerate(ph) if k > ln)
        r['%s гостей: Б %.1f' % (nm, ln)] = sum(v for k, v in enumerate(pa) if k > ln)
        r['%s хозяев: М %.1f' % (nm, ln)] = 1 - r['%s хозяев: Б %.1f' % (nm, ln)]
        r['%s гостей: М %.1f' % (nm, ln)] = 1 - r['%s гостей: Б %.1f' % (nm, ln)]
    more_h = sum(ph[i] * pa[j] for i in range(n) for j in range(n) if i > j)
    eq = sum(ph[i] * pa[i] for i in range(n))
    r['%s: больше у хозяев' % nm] = more_h
    r['%s: поровну' % nm] = eq
    r['%s: больше у гостей' % nm] = 1 - more_h - eq
    for hc in [x + 0.5 for x in range(-7, 7)]:
        r['%s: фора хозяев %+.1f' % (nm, hc)] = sum(ph[i] * pa[j] for i in range(n) for j in range(n) if i - j + hc > 0)
    return r


# ---------- статистика команды ----------
def team_panel(games, team, s, day, R=None):
    gs = [g for g in games if g['s'] == s and g['d'] < day and team in (g['h'], g['a'])]
    if not gs:
        return None
    acc = defaultdict(float)
    for g in gs:
        h = g['h'] == team
        i, j = (0, 1) if h else (1, 0)
        f, a = (g['hg'], g['ag']) if h else (g['ag'], g['hg'])
        acc['n'] += 1
        acc['w'] += f > a
        acc['d'] += f == a
        acc['gf'] += f
        acc['ga'] += a
        acc['cs'] += a == 0
        acc['btts'] += f > 0 and a > 0
        acc['o25'] += f + a > 2
        acc['pts'] += 3 if f > a else (1 if f == a else 0)
        acc['hn' if h else 'an'] += 1
        acc['hp' if h else 'ap'] += 3 if f > a else (1 if f == a else 0)
        for k in ('xg', 'sh', 'st', 'co', 'yc'):
            if k in g:
                acc[k + 'f'] += g[k][i]
                acc[k + 'a'] += g[k][j]
                acc[k + 'n'] += 1
    n = acc['n']
    parts = ['%d игр: %d-%d-%d, очки %.2f/игра (дома %.2f, в гостях %.2f)' % (
        n, acc['w'], acc['d'], n - acc['w'] - acc['d'], acc['pts'] / n,
        acc['hp'] / acc['hn'] if acc['hn'] else 0, acc['ap'] / acc['an'] if acc['an'] else 0),
        'голы %.2f:%.2f' % (acc['gf'] / n, acc['ga'] / n)]
    for k, nm in (('xg', 'xG'), ('sh', 'удары'), ('st', 'в створ'), ('co', 'угловые'), ('yc', 'жёлтые')):
        if acc[k + 'n']:
            parts.append('%s %.2f:%.2f' % (nm, acc[k + 'f'] / acc[k + 'n'], acc[k + 'a'] / acc[k + 'n']))
    parts.append('сухие %d%%, обе забили %d%%, ТБ 2,5 %d%%' % (100 * acc['cs'] / n, 100 * acc['btts'] / n, 100 * acc['o25'] / n))
    if R and team in R:
        A, D = R[team]
        parts.append('рейтинг: атака %d, оборона %d (100 = средняя команда лиги; оборона — выше = лучше)' % (
            round(100 * A), round(100 / D)))
    return ' · '.join(parts)


def power_table(R, mh, ma):
    """Сила клубов лиги: ожидаемая разница голов против средней команды на нейтральном поле → место."""
    mu = (mh + ma) / 2
    pw = {t: mu * (A - D) for t, (A, D) in R.items()}
    return {t: (i + 1, pw[t]) for i, t in enumerate(sorted(pw, key=lambda t: -pw[t]))}


# ---------- проверка на истории ----------
def bt():
    import football_bt as BT
    import football_live as FL
    P, C = FL.conf()
    data = FH.load(rebuild='--rebuild' in sys.argv)
    groups = defaultdict(lambda: defaultdict(lambda: [0, 0.0, 0]))
    for lg in FH.OURS:
        games = sorted(data['dom'][lg], key=lambda g: g['d'])
        for g in games:
            if C.get('xg') == 'us' and g.get('xg'):
                g['x'] = g['xg']
        days = sorted({g['d'] for g in games if g['s'] == 2025})
        cache = {}
        for d in days:
            known = {g['h'] for g in games if g['s'] == 2024}
            R, mh, ma = FM.fit(games, d, P, known)
            sh = ht_share(games, d)
            st = {k: (stat_fit(games, k, d, known), dispersion(games, k, d)) for k in STATS}
            cache[d] = (R, mh, ma, sh, st)
        for g in games:
            if g['s'] != 2025:
                continue
            R, mh, ma, sh, st = cache[g['d']]
            lh, la = FM.lambdas(R, mh, ma, g['h'], g['a'], P)
            rows = []
            if 'ht' in g:
                m = goal_markets(lh, la, P['rho'], sh)
                rows += [(k, p, settle(k, g)) for k, p in m.items()]
            for k in STATS:
                if k not in g:
                    continue
                (Rs, smh, sma), r_ = st[k]
                a, b = FM.lambdas(Rs, smh, sma, g['h'], g['a'], SP)
                rows += [(kk, p, settle(kk, g)) for kk, p in stat_markets(k, a, b, r_).items()]
            for k, p, y in rows:
                if y is None or p < 0.5:
                    continue
                grp = group_of(k)
                b = groups[grp][min(19, int(p * 20)) / 20]
                b[0] += 1
                b[1] += p
                b[2] += y
        out('FWBT', '%s готово' % lg)
    for grp in sorted(groups):
        bins = groups[grp]
        n = sum(v[0] for v in bins.values())
        pr = sum(v[1] for v in bins.values()) / n
        hit = sum(v[2] for v in bins.values()) / n
        hi = [v for k, v in bins.items() if k >= 0.6]
        nh = sum(v[0] for v in hi)
        line = '%s | ставок от 50%%: %d, обещано %.1f%%, зашло %.1f%%' % (grp, n, 100 * pr, 100 * hit)
        if nh:
            line += ' | от 60%%: %d, обещано %.1f%%, зашло %.1f%%' % (
                nh, 100 * sum(v[1] for v in hi) / nh, 100 * sum(v[2] for v in hi) / nh)
        out('FWBTG', line)


def group_of(k):
    for pre, grp in (('угловые', 'угловые'), ('жёлтые', 'жёлтые'), ('в створ', 'удары в створ'), ('1-й тайм', '1-й тайм'),
                     ('2-й тайм', '2-й тайм'), ('ИТ', 'инд. тоталы'), ('счёт', 'точный счёт'), ('Ф', 'форы'),
                     ('ТБ', 'тоталы'), ('ТМ', 'тоталы'), ('ОЗ', 'обе забьют'), ('чёт', 'чёт/нечет'), ('нечет', 'чёт/нечет')):
        if k.startswith(pre):
            return grp
    if ' + ' in k:
        return 'комбинации'
    if 'тайм' in k:
        return 'таймы прочее'
    return 'исход и прочее'


def settle(k, g):
    """Итог ставки по матчу (True/False; None — возврат или нет данных)."""
    i, j = g['hg'], g['ag']
    m = goal_outcomes(i, j, g.get('ht'))
    if k in m:
        return m[k]
    for key, nm in STATS.items():
        if k.startswith(nm) and key in g:
            a, b = g[key]
            rest = k[len(nm):]
            if rest.startswith(': ТБ '):
                return a + b > float(rest[5:])
            if rest.startswith(': ТМ '):
                return a + b < float(rest[5:])
            if rest.startswith(' хозяев: Б '):
                return a > float(rest[11:])
            if rest.startswith(' хозяев: М '):
                return a < float(rest[11:])
            if rest.startswith(' гостей: Б '):
                return b > float(rest[11:])
            if rest.startswith(' гостей: М '):
                return b < float(rest[11:])
            if rest == ': больше у хозяев':
                return a > b
            if rest == ': поровну':
                return a == b
            if rest == ': больше у гостей':
                return a < b
            if rest.startswith(': фора хозяев '):
                return a - b + float(rest[14:]) > 0
    return None


def goal_outcomes(i, j, ht):
    r = {'П1': i > j, 'Х': i == j, 'П2': i < j, '1Х': i >= j, '12': i != j, 'Х2': i <= j,
         'П1 (ничья — возврат)': None if i == j else i > j, 'П2 (ничья — возврат)': None if i == j else i < j}
    for hc in [x + 0.5 for x in range(-4, 4)]:
        r['Ф1 %+.1f' % hc] = i - j + hc > 0
        r['Ф2 %+.1f' % hc] = j - i + hc > 0
    for hc in (-2, -1, 1, 2):
        r['Ф1 %+d (возврат при ровно)' % hc] = None if i - j + hc == 0 else i - j + hc > 0
        r['Ф2 %+d (возврат при ровно)' % hc] = None if j - i + hc == 0 else j - i + hc > 0
    for ln in (0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5):
        r['ТБ %.1f' % ln], r['ТМ %.1f' % ln] = i + j > ln, i + j < ln
    for ln in (0.5, 1.5, 2.5, 3.5, 4.5):
        r['ИТ1Б %.1f' % ln], r['ИТ1М %.1f' % ln] = i > ln, i < ln
        r['ИТ2Б %.1f' % ln], r['ИТ2М %.1f' % ln] = j > ln, j < ln
    bt_ = i > 0 and j > 0
    r.update({'ОЗ да': bt_, 'ОЗ нет': not bt_})
    for ln in (1.5, 2.5, 3.5, 4.5):
        for yn, fb in (('да', bt_), ('нет', not bt_)):
            r['ОЗ %s + ТБ %.1f' % (yn, ln)], r['ОЗ %s + ТМ %.1f' % (yn, ln)] = fb and i + j > ln, fb and i + j < ln
    for hc in (-3, -2, -1, 1, 2, 3):
        r['ЕФ1 %+d' % hc], r['ЕФ Х %+d' % hc], r['ЕФ2 %+d' % hc] = i + hc > j, i + hc == j, i + hc < j
    for nm, f in (('П1', i > j), ('Х', i == j), ('П2', i < j), ('1Х', i >= j), ('Х2', i <= j)):
        r['%s + ОЗ да' % nm], r['%s + ОЗ нет' % nm] = f and bt_, f and not bt_
        for ln in (1.5, 2.5, 3.5):
            r['%s + ТБ %.1f' % (nm, ln)], r['%s + ТМ %.1f' % (nm, ln)] = f and i + j > ln, f and i + j < ln
    r['чёт'], r['нечет'] = (i + j) % 2 == 0, (i + j) % 2 == 1
    r['сухой у хозяев (гости не забьют)'], r['сухой у гостей (хозяева не забьют)'] = j == 0, i == 0
    r['П1 всухую'], r['П2 всухую'] = i > j and j == 0, j > i and i == 0
    for d in (1, 2):
        r['П1 ровно в %d' % d], r['П2 ровно в %d' % d] = i - j == d, j - i == d
    r['П1 в 3 и больше'], r['П2 в 3 и больше'] = i - j >= 3, j - i >= 3
    for a in range(6):
        for b in range(6):
            r['счёт %d:%d' % (a, b)] = (i, j) == (a, b)
    if ht:
        x, y = ht
        u, v = i - x, j - y
        r.update({'1-й тайм П1': x > y, '1-й тайм Х': x == y, '1-й тайм П2': x < y,
                  'больше голов во 2-м тайме': u + v > x + y, 'больше голов в 1-м тайме': x + y > u + v,
                  'голы в обоих таймах': x + y > 0 and u + v > 0, 'хозяева забьют в обоих таймах': x > 0 and u > 0,
                  'гости забьют в обоих таймах': y > 0 and v > 0})
        r['1-й тайм ОЗ да'] = x > 0 and y > 0
        for ln in (0.5, 1.5):
            r['1-й тайм ИТ1Б %.1f' % ln], r['1-й тайм ИТ2Б %.1f' % ln] = x > ln, y > ln
        for hc in (-1.5, -0.5, 0.5, 1.5):
            r['1-й тайм Ф1 %+.1f' % hc], r['1-й тайм Ф2 %+.1f' % hc] = x - y + hc > 0, y - x + hc > 0
        for ln in (0.5, 1.5, 2.5, 3.5):
            r['1-й тайм ТБ %.1f' % ln], r['1-й тайм ТМ %.1f' % ln] = x + y > ln, x + y < ln
        for ln in (0.5, 1.5, 2.5):
            r['2-й тайм ТБ %.1f' % ln], r['2-й тайм ТМ %.1f' % ln] = u + v > ln, u + v < ln
    return r


if __name__ == '__main__':
    if '--bt' in sys.argv:
        bt()


# ---------- вся линия Pinnacle на матч ----------
def _dec(a):
    a = float(a)
    return round(1 + a / 100, 3) if a > 0 else round(1 + 100 / abs(a), 3)


def _hc(v):
    return '%+.1f' % v if abs(v * 2 - round(v * 2)) < 1e-9 and abs(v - round(v)) > 1e-9 else None


def pin_full(code, day):
    """Все рынки Pinnacle на матчи дня (по Москве), в именах football_wide: {(хозяева, гости, время): {рынок: кэф}}."""
    import requests
    import football_live as FL
    A, H = FL.API, FL.HDR
    lg = FL.PIN[code]
    mu = requests.get('%s/leagues/%d/matchups' % (A, lg), headers=H, timeout=30).json()
    mk = requests.get('%s/leagues/%d/markets/straight' % (A, lg), headers=H, timeout=30).json()
    by = {m['id']: m for m in mu}
    main = {}
    for m in mu:
        if m.get('type') != 'matchup' or m.get('parentId') or m.get('units') != 'Regular' or not m.get('startTime'):
            continue
        st = FL.datetime.fromisoformat(m['startTime'].replace('Z', '+00:00')).astimezone(FL.MSK)
        if st.strftime('%Y-%m-%d') != day:
            continue
        side = {p.get('alignment'): p.get('name') for p in m.get('participants') or []}
        if side.get('home') and side.get('away'):
            main[m['id']] = (side['home'], side['away'], st.strftime('%H:%M'))
    root = {}                                       # любой matchup → основной матч и его вид (Regular / Corners / Bookings / special)
    for m in mu:
        pid = m.get('parentId') or m['id']
        if pid in main:
            root[m['id']] = (pid, m.get('units'), m)
    odds = {k: {} for k in main}
    for x in mk:
        if x.get('matchupId') not in root or x.get('status') not in (None, 'open'):
            continue
        pid, units, m = root[x['matchupId']]
        o = odds[pid]
        h, a, _ = main[pid]
        per = x.get('period')
        pre = {'Corners': 'угловые', 'Bookings': 'карточки'}.get(units)
        prices = [p for p in x.get('prices') or [] if p.get('price') is not None]
        if m.get('type') == 'special':
            special(o, m, prices, h, a)
            continue
        des = {p.get('designation'): p for p in prices}
        t = x.get('type')
        if units == 'Regular':
            tag = '' if per == 0 else ('1-й тайм ' if per == 1 else None)
            if tag is None:
                continue
            if t == 'moneyline' and len(des) == 3:
                o[tag + 'П1'], o[tag + 'Х'], o[tag + 'П2'] = (_dec(des[k]['price']) for k in ('home', 'draw', 'away'))
            elif t == 'spread' and 'home' in des:
                v = des['home'].get('points')
                hc = _hc(v)
                if hc:
                    o[tag + 'Ф1 ' + hc] = _dec(des['home']['price'])
                    o[tag + 'Ф2 ' + _hc(-v)] = _dec(des['away']['price'])
                elif not tag and v is not None and abs(v - round(v)) < 1e-9 and v != 0:
                    o['Ф1 %+d (возврат при ровно)' % v] = _dec(des['home']['price'])
                    o['Ф2 %+d (возврат при ровно)' % -v] = _dec(des['away']['price'])
            elif t == 'total' and 'over' in des:
                ln = des['over'].get('points')
                if _hc(ln):
                    o[tag + 'ТБ %.1f' % ln] = _dec(des['over']['price'])
                    o[tag + 'ТМ %.1f' % ln] = _dec(des['under']['price'])
            elif t == 'team_total' and 'over' in des and not tag:
                ln = des['over'].get('points')
                k = 'ИТ1' if x.get('side') == 'home' else 'ИТ2'
                if _hc(ln):
                    o['%sБ %.1f' % (k, ln)] = _dec(des['over']['price'])
                    o['%sМ %.1f' % (k, ln)] = _dec(des['under']['price'])
        elif pre and per == 0:
            if t == 'total' and 'over' in des and _hc(des['over'].get('points')):
                ln = des['over']['points']
                o['%s: ТБ %.1f' % (pre, ln)] = _dec(des['over']['price'])
                o['%s: ТМ %.1f' % (pre, ln)] = _dec(des['under']['price'])
            elif t == 'team_total' and 'over' in des and _hc(des['over'].get('points')):
                ln = des['over']['points']
                sd = 'хозяев' if x.get('side') == 'home' else 'гостей'
                o['%s %s: Б %.1f' % (pre, sd, ln)] = _dec(des['over']['price'])
                o['%s %s: М %.1f' % (pre, sd, ln)] = _dec(des['under']['price'])
            elif t == 'spread' and 'home' in des and _hc(des['home'].get('points')):
                o['%s: фора хозяев %s' % (pre, _hc(des['home']['points']))] = _dec(des['home']['price'])
                o['%s: фора хозяев %s' % (pre, _hc(-des['away']['points']))] = None
            elif t == 'moneyline' and len(des) >= 2:
                if 'home' in des:
                    o['%s: больше у хозяев' % pre] = _dec(des['home']['price'])
                if 'away' in des:
                    o['%s: больше у гостей' % pre] = _dec(des['away']['price'])
                if 'draw' in des:
                    o['%s: поровну' % pre] = _dec(des['draw']['price'])
    for o in odds.values():
        for k in [k for k, v in o.items() if v is None]:
            del o[k]
    return {main[k]: odds[k] for k in main}


def special(o, m, prices, h, a):
    """Спецрынки Pinnacle (Team Props) → имена football_wide."""
    sp = m.get('special') or {}
    d = str(sp.get('description') or '')
    names = {p.get('id'): str(p.get('name') or '') for p in m.get('participants') or []}
    pr = {names.get(p.get('participantId'), ''): _dec(p['price']) for p in prices}
    who = lambda s: 'П1' if s.startswith(h) else ('П2' if s.startswith(a) else ('Х' if s.startswith('Draw') else None))  # noqa: E731
    if d == 'Both Teams To Score?':
        o['ОЗ да'], o['ОЗ нет'] = pr.get('Yes'), pr.get('No')
    elif d == 'Both Teams To Score? 1st Half':
        o['1-й тайм ОЗ да'] = pr.get('Yes')
    elif d == 'Total Goals Odd/Even':
        o['нечет'], o['чёт'] = pr.get('Odd'), pr.get('Even')
    elif d == 'Draw No Bet':
        for nm, v in pr.items():
            w = who(nm)
            if w in ('П1', 'П2'):
                o['%s (ничья — возврат)' % w] = v
    elif d == 'Moneyline and Total Goals':
        for nm, v in pr.items():
            w = who(nm)
            ou = 'ТБ' if '& Over' in nm else ('ТМ' if '& Under' in nm else None)
            if w and ou:
                o['%s + %s %s' % (w, ou, nm.rsplit(' ', 1)[-1])] = v
    elif d == 'Both Teams To Score and Total Goals':
        for nm, v in pr.items():
            yn = 'да' if nm.startswith('Yes') else 'нет'
            ou = 'ТБ' if '& Over' in nm else 'ТМ'
            o['ОЗ %s + %s %s' % (yn, ou, nm.rsplit(' ', 1)[-1])] = v
    elif d.endswith(' To Win To Nil') and 'Half' not in d:
        w = who(d)
        if w in ('П1', 'П2'):
            o['%s всухую' % w] = pr.get('Yes')
    elif d.endswith(' To Score?') and 'Half' not in d and 'Either' not in d:
        w = who(d)
        if w in ('П1', 'П2'):
            o['ИТ%sБ 0.5' % w[1]] = pr.get('Yes')
    elif d.startswith('3-Way Handicap '):
        try:
            v = int(d.rsplit(' ', 1)[-1])
        except ValueError:
            return
        hc = v if d[len('3-Way Handicap '):].startswith(h) else (-v if d[len('3-Way Handicap '):].startswith(a) else None)
        if hc is None or hc == 0:
            return
        for nm, val in pr.items():
            if nm.startswith('Draw'):
                o['ЕФ Х %+d' % hc] = val
            elif nm.startswith(h):
                o['ЕФ1 %+d' % hc] = val
            elif nm.startswith(a):
                o['ЕФ2 %+d' % hc] = val
    for k in [k for k, v in o.items() if v is None]:
        del o[k]
