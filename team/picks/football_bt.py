# -*- coding: utf-8 -*-
"""Проверка футбольного рейтинга на истории (ТЗ docs/handoff/FOOTBALL_BRIEF.md, п. 5–7; как nhl_bt.py).

Каждый матч считается вслепую — по рейтингу на утро дня матча, только по прошлым играм.
  • Подбор констант (hl, alpha, k, новички, rho, xG) — на сезонах 2022/23–2024/25 (logloss 1Х2 + тотал 2,5).
  • Проверка вслепую — 2025/26 целиком и 2026/27 до сегодня.
  • Сравнение с рынком: закрытие Pinnacle без маржи (1Х2, тотал 2,5); у 2026/27 в CSV Pinnacle нет — средняя рынка.
    Остальные рынки (1Х/Х2, тоталы 1,5 и 3,5, «обе забьют») рынок оценивается из 1Х2 и тотала 2,5 закрытия
    (Пуассон под эти цены), кэф — эта вероятность с маржой 3 % (оценка, в CSV их нет).
  • Ставки как в боте: по матчу самая вероятная ставка с кэфом ≥ 1,6 и p ≥ порога; «обещано» — средняя p модели
    (после калибровки по сезонам подбора), «зашло» — доля выигрышей, ROI — по кэфу закрытия.
  • Еврокубки: сила клуба в лиге × сила лиги (из матчей еврокубков прошлых лет) — общая шкала; кэфы — ESPN.
Печатает строки FBT*; итог — team/out/2026-10-30/football_bt.md (собирается из лога).
Запуск: python team/picks/football_bt.py [--quick]"""
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import football_hist as FH  # noqa: E402
import football_model as FM  # noqa: E402

QUICK = '--quick' in sys.argv
TUNE = [2022, 2023, 2024]
TEST = [2025, 2026]
LEAGUES = list(FH.OURS)
MARGIN = 0.03
MIN_ODDS = 1.6
FLOORS = [0.55, 0.58, 0.60, 0.62, 0.65, 0.70]
GROUP = {'П1': '1Х2', 'Х': '1Х2', 'П2': '1Х2', '1Х': 'не проиграет', 'Х2': 'не проиграет',
         'ТБ 1.5': 'тотал 1,5', 'ТМ 1.5': 'тотал 1,5', 'ТБ 2.5': 'тотал 2,5', 'ТМ 2.5': 'тотал 2,5',
         'ТБ 3.5': 'тотал 3,5', 'ТМ 3.5': 'тотал 3,5', 'ОЗ да': 'обе забьют', 'ОЗ нет': 'обе забьют'}
KINDS = list(GROUP)


def out(tag, text):
    print(tag + ' ' + text, flush=True)


# ---------- xG по ударам ----------
def shot_coef(games, seasons):
    """Голы ≈ a·удары в створ + b·удары мимо (МНК без свободного члена) по сезонам подбора."""
    sxx = sxy = syy = sx = sy = 0.0
    for g in games:
        if g['s'] not in seasons or 'st' not in g:
            continue
        for i, goals in ((0, g['hg']), (1, g['ag'])):
            on, off = g['st'][i], max(0, g['sh'][i] - g['st'][i])
            sxx += on * on
            sxy += on * off
            syy += off * off
            sx += on * goals
            sy += off * goals
    det = sxx * syy - sxy * sxy
    if det <= 0:
        return 0.3, 0.03
    return (sx * syy - sy * sxy) / det, (sy * sxx - sx * sxy) / det


def prep(games, coef, src):
    """g['x'] — ожидаемые голы матча: Understat (src='us', где есть) или по ударам."""
    a, b = coef
    for g in games:
        g.pop('x', None)
        if src == 'us' and g.get('xg'):
            g['x'] = g['xg']
        elif 'st' in g and src in ('us', 'shots'):
            g['x'] = [a * g['st'][i] + b * max(0, g['sh'][i] - g['st'][i]) for i in (0, 1)]


# ---------- рейтинг на каждый день ----------
def snapshots(games, P, seasons_from):
    """Рейтинг лиги на утро каждого игрового дня: {день: (R, mu_h, mu_a, known)}."""
    days = sorted({g['d'] for g in games if g['s'] >= seasons_from})
    teams_by_s = defaultdict(set)
    for g in games:
        teams_by_s[g['s']] |= {g['h'], g['a']}
    res = {}
    for d in days:
        s = FH.season_of(d)
        known = teams_by_s.get(s - 1)
        R, mh, ma = FM.fit(games, d, P, known)
        res[d] = (R, mh, ma, known)
    return res


def nv(odds):
    inv = [1 / o for o in odds]
    t = sum(inv)
    return [x / t for x in inv]


def _m3(lh, la, rho):
    m = FM.markets(lh, la, rho)
    return m['П1'], m['П2'], m['ТБ 2.5']


def market_lams(p1, px, p2, pov, rho):
    """λ хозяев и гостей, при которых Пуассон Дикси-Коулса даёт цены рынка (1Х2 и ТБ 2,5): спуск по сетке."""
    lh, la = 1.45, 1.15

    def err(a, b):
        q1, q2, qo = _m3(a, b, rho)
        return (q1 - p1) ** 2 + (q2 - p2) ** 2 + ((qo - pov) ** 2 if pov else 0)
    e0 = err(lh, la)
    for step in (0.3, 0.1, 0.03, 0.01):
        moved = True
        while moved:
            moved = False
            for dh, da in ((step, 0), (-step, 0), (0, step), (0, -step), (step, step), (-step, -step), (step, -step), (-step, step)):
                a, b = lh + dh, la + da
                if a < 0.05 or b < 0.05:
                    continue
                e = err(a, b)
                if e < e0 - 1e-12:
                    lh, la, e0, moved = a, b, e, True
                    break
    return lh, la


_ML = {}


def market_probs(g, rho, which):
    """Вероятности рынка без маржи и кэфы по всем рынкам. which: 'pin' (закрытие Pinnacle) или 'avg' (средняя)."""
    o12 = g.get('pc') if which == 'pin' else g.get('ac')
    o25 = g.get('o25') if which == 'pin' else g.get('a25')
    if not o12:
        return None, None
    p1, px, p2 = nv(o12)
    pov = nv(o25)[0] if o25 else None
    key = (round(p1, 3), round(p2, 3), round(pov or 0, 3))
    if key not in _ML:
        _ML[key] = FM.markets(*market_lams(p1, px, p2, pov, rho), rho)
    mm = dict(_ML[key])
    mm['П1'], mm['Х'], mm['П2'] = p1, px, p2
    mm['1Х'], mm['Х2'] = p1 + px, px + p2
    if pov:
        mm['ТБ 2.5'], mm['ТМ 2.5'] = pov, 1 - pov
    odds = {k: round(1 / (mm[k] * (1 + MARGIN)), 3) for k in KINDS}
    odds['П1'], odds['Х'], odds['П2'] = o12
    if o25:
        odds['ТБ 2.5'], odds['ТМ 2.5'] = o25
    return mm, odds


def outcome(k, hg, ag):
    t = hg + ag
    return {'П1': hg > ag, 'Х': hg == ag, 'П2': hg < ag, '1Х': hg >= ag, 'Х2': hg <= ag,
            'ТБ 1.5': t > 1.5, 'ТМ 1.5': t < 1.5, 'ТБ 2.5': t > 2.5, 'ТМ 2.5': t < 2.5,
            'ТБ 3.5': t > 3.5, 'ТМ 3.5': t < 3.5, 'ОЗ да': hg > 0 and ag > 0, 'ОЗ нет': not (hg > 0 and ag > 0)}[k]


def predict_league(games, P, seasons):
    snaps = snapshots(games, P, min(seasons))
    recs = []
    for g in games:
        if g['s'] not in seasons:
            continue
        R, mh, ma, known = snaps[g['d']]
        lh, la = FM.lambdas(R, mh, ma, g['h'], g['a'], P)
        recs.append((g, lh, la))
    return recs, snaps


def ll3(p, y):
    return -math.log(max(1e-9, p[y]))


def score_1x2(recs, rho):
    """logloss 1Х2 + logloss тотала 2,5 (по модели)."""
    s = n = 0.0
    for g, lh, la in recs:
        m = FM.markets(lh, la, rho)
        y = 0 if g['hg'] > g['ag'] else (1 if g['hg'] == g['ag'] else 2)
        s += ll3([m['П1'], m['Х'], m['П2']], y)
        ov = g['hg'] + g['ag'] > 2.5
        s += -math.log(max(1e-9, m['ТБ 2.5'] if ov else m['ТМ 2.5']))
        n += 1
    return s / max(1, n)


def logit(p):
    p = min(1 - 1e-6, max(1e-6, p))
    return math.log(p / (1 - p))


def fit_calib(rows):
    """logit(p') = a + b·logit(p) по виду ставки (как calib.json хоккея): Ньютон, 25 шагов."""
    res = {}
    by = defaultdict(list)
    for k, p, y in rows:
        by[k].append((logit(p), y))
    for k, xs in by.items():
        a, b = 0.0, 1.0
        for _ in range(25):
            ga = gb = haa = hab = hbb = 0.0
            for x, y in xs:
                q = 1 / (1 + math.exp(-(a + b * x)))
                ga += y - q
                gb += (y - q) * x
                w = q * (1 - q)
                haa += w
                hab += w * x
                hbb += w * x * x
            det = haa * hbb - hab * hab + 1e-9
            a += (hbb * ga - hab * gb) / det
            b += (haa * gb - hab * ga) / det
        res[k] = (round(a, 4), round(b, 4))
    return res


def cal(c, k, p):
    a, b = c.get(k, (0.0, 1.0))
    return 1 / (1 + math.exp(-(a + b * logit(p))))


def pick_table(rows, floor, kinds=None):
    """rows: [(матч, вид, p, y, кэф)] → самая вероятная ставка по матчу с кэфом ≥ 1,6 и p ≥ порога."""
    best = {}
    for gid, k, p, y, od in rows:
        if kinds and k not in kinds:
            continue
        if not od or od < MIN_ODDS or p < floor:
            continue
        if gid not in best or p > best[gid][1]:
            best[gid] = (k, p, y, od)
    v = list(best.values())
    if not v:
        return 0, 0, 0, 0
    n = len(v)
    return n, sum(x[1] for x in v) / n, sum(x[2] for x in v) / n, sum((x[3] - 1) if x[2] else -1 for x in v) / n


def fmt(n, prom, hit, roi):
    if not n:
        return 'ставок 0'
    return 'ставок %d · обещано %.1f%% · зашло %.1f%% · ROI %+.1f%%' % (n, 100 * prom, 100 * hit, 100 * roi)


# ---------- еврокубки: общая шкала ----------
def team_rating(snaps_all, lg, team, d):
    """(A, D) клуба в своей лиге на утро дня d (последний снимок не позже d), None — нет данных."""
    sn = snaps_all.get(lg)
    if not sn:
        return None
    days = sn['days']
    import bisect
    i = bisect.bisect_left(days, d) - 1
    if i < 0:
        return None
    R = sn['snap'][days[i]][0]
    return R.get(team)


def fit_league_factors(cups, d, rat, Cp):
    """Сила лиг по еврокубкам до дня d: λ = mu × A·a_L × D·d_L соперника × дом. → ({L: (a, d)}, mu, дом)."""
    from datetime import date as _d
    d0 = _d.fromisoformat(d)
    rows = []
    for g in cups:
        if g['d'] >= d:
            break
        age = (d0 - _d.fromisoformat(g['d'])).days
        if age > 4 * Cp['hl']:
            continue
        w = 0.5 ** (age / Cp['hl'])
        rh, ra = rat[id(g)]
        rows.append((g['hl'] if g['hl'] in rat['lgs'] else '?', g['al'] if g['al'] in rat['lgs'] else '?',
                     rh, ra, g['hg'], g['ag'], w, g['n']))
    if len(rows) < 30:
        return {}, 1.35, 1.25
    L = {r[0] for r in rows} | {r[1] for r in rows}
    fa = {x: 1.0 for x in L}
    fd = {x: 1.0 for x in L}
    sw = sum(r[6] for r in rows)
    mu = sum(r[6] * (r[4] + r[5]) for r in rows) / (2 * sw)
    hm = 1.15
    k = Cp['k']
    for _ in range(10):
        num, den = defaultdict(float), defaultdict(float)
        for lh_, la_, rh, ra, hg, ag, w, ne in rows:
            hf = 1.0 if ne else hm
            eh = mu * rh[0] * fa[lh_] * ra[1] * fd[la_] * hf
            ea = mu * ra[0] * fa[la_] * rh[1] * fd[lh_] / hf
            num[lh_] += w * hg
            den[lh_] += w * eh / fa[lh_]
            num[la_] += w * ag
            den[la_] += w * ea / fa[la_]
        for x in L:
            fa[x] = (num[x] + k) / (den[x] + k)
        num, den = defaultdict(float), defaultdict(float)
        for lh_, la_, rh, ra, hg, ag, w, ne in rows:
            hf = 1.0 if ne else hm
            eh = mu * rh[0] * fa[lh_] * ra[1] * fd[la_] * hf
            ea = mu * ra[0] * fa[la_] * rh[1] * fd[lh_] / hf
            num[la_] += w * hg
            den[la_] += w * eh / fd[la_]
            num[lh_] += w * ag
            den[lh_] += w * ea / fd[lh_]
        for x in L:
            fd[x] = (num[x] + k) / (den[x] + k)
        # дом: отношение голов хозяев к ожидаемым без дома, корень (дом делится поровну на атаку хозяев и гостей)
        nh = dh = na = da = 0.0
        for lh_, la_, rh, ra, hg, ag, w, ne in rows:
            if ne:
                continue
            nh += w * hg
            dh += w * mu * rh[0] * fa[lh_] * ra[1] * fd[la_]
            na += w * ag
            da += w * mu * ra[0] * fa[la_] * rh[1] * fd[lh_]
        hm = math.sqrt((nh / dh) / (na / da)) if dh and da and na else hm
        gm = math.exp(sum(math.log(fa[x]) for x in L) / len(L))
        gd = math.exp(sum(math.log(fd[x]) for x in L) / len(L))
        for x in L:
            fa[x] /= gm
            fd[x] /= gd
        tot_o = sum(r[6] * (r[4] + r[5]) for r in rows)
        tot_e = 0.0
        for lh_, la_, rh, ra, hg, ag, w, ne in rows:
            hf = 1.0 if ne else hm
            tot_e += w * (mu * rh[0] * fa[lh_] * ra[1] * fd[la_] * hf + mu * ra[0] * fa[la_] * rh[1] * fd[lh_] / hf)
        mu *= tot_o / tot_e
    return {x: (fa[x], fd[x]) for x in L}, mu, hm


def cups_bt(data, snaps_all, P, rho):
    """Проверка еврокубков: обычная (своя лига × сила лиги) против «без поправки на лигу»."""
    cups = [g for g in data['cup']]
    lgs = set(snaps_all)
    rat = {'lgs': lgs}
    unknown = (P['new_a'], P['new_d'])
    for g in cups:
        r = []
        for side in ('h', 'a'):
            t, lg = g[side], g[side + 'l']
            v = team_rating(snaps_all, lg, t, g['d']) if lg in lgs and not t.startswith('espn:') else None
            r.append(v or (1.0, 1.0))
        rat[id(g)] = tuple(r)
    Cp = dict(hl=365.0, k=3.0)
    by_season = defaultdict(list)
    cache = {}
    for g in cups:
        if g['s'] < 2023:
            continue
        wk = g['d'][:8] + ('0' if int(g['d'][8:]) < 16 else '1')     # пересчёт силы лиг раз в полмесяца
        if wk not in cache:
            cache[wk] = fit_league_factors(cups, g['d'], rat, Cp)
        F, mu, hm = cache[wk]
        rh, ra = rat[id(g)]
        hf = 1.0 if g['n'] else hm
        fh = F.get(g['hl'] if g['hl'] in lgs else '?', (1.0, 1.0))
        fa = F.get(g['al'] if g['al'] in lgs else '?', (1.0, 1.0))
        lh = mu * rh[0] * fh[0] * ra[1] * fa[1] * hf
        la = mu * ra[0] * fa[0] * rh[1] * fh[1] / hf
        lh0 = mu * rh[0] * ra[1] * hf          # без поправки на силу лиги
        la0 = mu * ra[0] * rh[1] / hf
        by_season[g['s']].append((g, lh, la, lh0, la0))
    last = None
    for wk in sorted(cache):
        last = cache[wk]
    if last and last[0]:
        F = last[0]
        base = F.get('E0', (1, 1))
        rows = sorted(F.items(), key=lambda kv: -(math.log(kv[1][0]) - math.log(kv[1][1])))
        out('FBTLG', ' · '.join('%s %+.2f' % (x, (math.log(f[0] / base[0]) - math.log(f[1] / base[1])))
                                for x, f in rows))
    return by_season


def main():
    data = FH.load()
    dom = {lg: sorted(data['dom'][lg], key=lambda g: g['d']) for lg in data['dom']}
    coef = {lg: shot_coef(dom[lg], set(TUNE) | {2021}) for lg in dom}
    out('FBTXG', ' · '.join('%s %.3f/%.3f' % (lg, *coef[lg]) for lg in LEAGUES))

    # ---- подбор констант на сезонах подбора ----
    P = dict(FM.P0)
    src = 'us'
    for lg in dom:
        prep(dom[lg], coef[lg], src)

    def tune_score(P_):
        tot = 0.0
        for lg in LEAGUES:
            recs, _ = predict_league(dom[lg], P_, TUNE)
            tot += score_1x2(recs, P_['rho'])
        return tot / len(LEAGUES)

    best = tune_score(P)
    out('FBTTUNE', 'старт %s → %.4f' % (P, best))
    grid = [('hl', [90.0, 120.0, 200.0, 300.0]), ('alpha', [0.0, 0.3, 0.7, 0.85]), ('k', [2.0, 8.0]),
            ('new_a', [0.8, 0.9]), ('new_d', [1.1, 1.2]), ('rho', [-0.12, -0.03, 0.0])]
    if QUICK:
        grid = grid[:2]
    for name, vals in grid:
        for v in vals:
            Q = dict(P, **{name: v})
            sc = tune_score(Q)
            if sc < best - 1e-5:
                best, P = sc, Q
        out('FBTTUNE', '%s → %s (%.4f)' % (name, P[name], best))
    for s_ in ('shots', 'none'):
        for lg in dom:
            prep(dom[lg], coef[lg], s_)
        sc = tune_score(P)
        out('FBTTUNE', 'xG=%s → %.4f (Understat+удары %.4f)' % (s_, sc, best))
        if sc < best - 1e-5:
            best, src = sc, s_
    for lg in dom:
        prep(dom[lg], coef[lg], src)
    out('FBTBEST', json.dumps(dict(P=P, xg=src, score=round(best, 4)), ensure_ascii=False))

    # ---- калибровка на сезонах подбора, проверка вслепую ----
    allrecs = {}
    snaps_all = {}
    for lg in dom:
        recs, snaps = predict_league(dom[lg], P, {2021} | set(TUNE) | set(TEST))
        allrecs[lg] = [r for r in recs if r[0]['s'] != 2021]
        snaps_all[lg] = dict(days=sorted(snaps), snap=snaps)
    crow = []
    for lg in LEAGUES:
        for g, lh, la in allrecs[lg]:
            if g['s'] in TUNE:
                m = FM.markets(lh, la, P['rho'])
                crow += [(k, m[k], outcome(k, g['hg'], g['ag'])) for k in KINDS]
    C = fit_calib(crow)
    out('FBTCALIB', json.dumps(C, ensure_ascii=False, separators=(',', ':')))

    # ---- метрики и ставки по сезонам проверки ----
    for s in TEST:
        which = 'pin' if s < 2026 else 'avg'
        agg = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0])   # Брайер модель, рынок; logloss модель, рынок; n
        tag = '%d/%02d' % (s, (s + 1) % 100)
        allrows = []
        for lg in LEAGUES:
            rows = []
            for g, lh, la in allrecs[lg]:
                if g['s'] != s:
                    continue
                m = FM.markets(lh, la, P['rho'])
                mm, odds = market_probs(g, P['rho'], which)
                gid = '%s|%s|%s' % (g['d'], g['h'], g['a'])
                y = 0 if g['hg'] > g['ag'] else (1 if g['hg'] == g['ag'] else 2)
                pm = [cal(C, k, m[k]) for k in ('П1', 'Х', 'П2')]
                t = sum(pm)
                pm = [x / t for x in pm]
                if mm:
                    pk = [mm['П1'], mm['Х'], mm['П2']]
                    a = agg[lg]
                    a[0] += sum((pm[i] - (i == y)) ** 2 for i in range(3))
                    a[1] += sum((pk[i] - (i == y)) ** 2 for i in range(3))
                    a[2] += ll3(pm, y)
                    a[3] += ll3(pk, y)
                    a[4] += 1
                    ov = g['hg'] + g['ag'] > 2.5
                    b = agg[lg + ' ТБ2,5']
                    q = cal(C, 'ТБ 2.5', m['ТБ 2.5'])
                    b[0] += (q - ov) ** 2
                    b[1] += (mm['ТБ 2.5'] - ov) ** 2
                    b[2] += -math.log(q if ov else 1 - q)
                    b[3] += -math.log(mm['ТБ 2.5'] if ov else 1 - mm['ТБ 2.5'])
                    b[4] += 1
                for k in KINDS:
                    rows.append((gid, k, cal(C, k, m[k]), outcome(k, g['hg'], g['ag']), odds[k] if odds else None))
            allrows += rows
            for fl in (0.58, 0.60, 0.62, 0.65):
                out('FBTPICK', '%s | %s | все рынки | от %d%% | %s' % (tag, FH.OURS[lg], fl * 100, fmt(*pick_table(rows, fl))))
            for grp in ('1Х2', 'не проиграет', 'тотал 1,5', 'тотал 2,5', 'тотал 3,5', 'обе забьют'):
                ks = [k for k in KINDS if GROUP[k] == grp]
                out('FBTPICK', '%s | %s | %s | от 60%% | %s' % (tag, FH.OURS[lg], grp, fmt(*pick_table(rows, 0.60, ks))))
        for lg in sorted(agg):
            a = agg[lg]
            n = a[4]
            out('FBTMET', '%s | %s | матчей %d | Брайер модель %.4f рынок %.4f | logloss модель %.4f рынок %.4f'
                % (tag, FH.OURS.get(lg.split(' ')[0], lg), n, a[0] / n, a[1] / n, a[2] / n, a[3] / n)
                + (' (ТБ 2,5)' if ' ' in lg else ' (1Х2)'))
        for fl in FLOORS:
            out('FBTALL', '%s | все лиги | все рынки | от %d%% | %s' % (tag, fl * 100, fmt(*pick_table(allrows, fl))))
        for grp in ('1Х2', 'не проиграет', 'тотал 1,5', 'тотал 2,5', 'тотал 3,5', 'обе забьют'):
            ks = [k for k in KINDS if GROUP[k] == grp]
            for fl in (0.55, 0.60, 0.65, 0.70):
                out('FBTMKT', '%s | %s | от %d%% | %s' % (tag, grp, fl * 100, fmt(*pick_table(allrows, fl, ks))))
        # калибровка по корзинам, все рынки и матчи (без фильтра кэфа)
        bins = defaultdict(lambda: [0, 0.0, 0])
        for gid, k, p, y, od in allrows:
            if p >= 0.5:
                b = bins[min(19, int(p * 20)) / 20]
                b[0] += 1
                b[1] += p
                b[2] += y
        out('FBTBIN', '%s | ' % tag + ' · '.join('%.0f–%.0f%%: %d, обещ %.1f, зашло %.1f' % (
            100 * k, 100 * k + 5, v[0], 100 * v[1] / v[0], 100 * v[2] / v[0]) for k, v in sorted(bins.items()) if v[0]))

    # ---- еврокубки ----
    cb = cups_bt(data, snaps_all, P, P['rho'])
    for s in sorted(cb):
        tag = '%d/%02d' % (s, (s + 1) % 100)
        for comp in ('UCL', 'UEL', 'UECL', 'все'):
            recs = [r for r in cb[s] if comp == 'все' or r[0]['lg'] == comp]
            if not recs:
                continue
            res = defaultdict(float)
            rows = []
            for g, lh, la, lh0, la0 in recs:
                y = 0 if g['hg'] > g['ag'] else (1 if g['hg'] == g['ag'] else 2)
                m = FM.markets(lh, la, P['rho'])
                m0 = FM.markets(lh0, la0, P['rho'])
                res['ll'] += ll3([m['П1'], m['Х'], m['П2']], y)
                res['ll0'] += ll3([m0['П1'], m0['Х'], m0['П2']], y)
                if g.get('bo'):
                    pk = nv(g['bo'])
                    res['llb'] += ll3(pk, y)
                    res['llm'] += ll3([m['П1'], m['Х'], m['П2']], y)
                    res['nb'] += 1
                gid = '%s|%s|%s' % (g['d'], g['h'], g['a'])
                od = {}
                if g.get('bo'):
                    od.update({'П1': g['bo'][0], 'Х': g['bo'][1], 'П2': g['bo'][2]})
                    pk = nv(g['bo'])
                    od['1Х'] = round(1 / ((pk[0] + pk[1]) * (1 + MARGIN)), 3)
                    od['Х2'] = round(1 / ((pk[1] + pk[2]) * (1 + MARGIN)), 3)
                if g.get('bt') and abs(g['bt'][0] - 2.5) < 0.01:
                    od['ТБ 2.5'], od['ТМ 2.5'] = g['bt'][1], g['bt'][2]
                for k in KINDS:
                    rows.append((gid, k, cal(C, k, m[k]), outcome(k, g['hg'], g['ag']), od.get(k)))
            n = len(recs)
            line = '%s | %s | матчей %d | logloss 1Х2: с поправкой на лигу %.4f, без %.4f' % (
                tag, comp, n, res['ll'] / n, res['ll0'] / n)
            if res['nb']:
                line += ' | с кэфами ESPN %d: модель %.4f, букмекер %.4f' % (res['nb'], res['llm'] / res['nb'], res['llb'] / res['nb'])
            out('FBTCUP', line)
            if comp == 'все':
                for fl in (0.55, 0.60, 0.65):
                    out('FBTCUPPICK', '%s | 1Х2 / 1Х-Х2 / тотал 2,5 с кэфами ESPN | от %d%% | %s' % (
                        tag, fl * 100, fmt(*pick_table(rows, fl))))
    out('FBTDONE', 'ok')


if __name__ == '__main__':
    main()
