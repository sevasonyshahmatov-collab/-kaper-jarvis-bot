# -*- coding: utf-8 -*-
"""Проверка нового рейтинга НХЛ на истории против старого расчёта (владелец 29.10).

Честно: прогноз на день строится только по матчам ДО этого дня; поправка вероятностей (logit по виду ставки, как
backtest.py) для сезона учится на прошлом сезоне; параметры нового рейтинга подбираются по сезонам 2024/25–2025/26,
а 2026/27 — проверка «вслепую».
  старый — calc.match (½ модель голов сезона + ½ частота) → поправка → ½ линии (W_MKT), как в прогнозах сейчас;
  новый  — nhl_model (форма по xG и голам, сжатый прошлый сезон, вратарь-стартер, два дня подряд) → частота с весом
           1 − wn → поправка → доля линии wm.
Отбор ставок как в боте: самая вероятная с кэфом от 1,6 и выше порога (calc.NHL_P), только где есть кэф закрытия ESPN
(итоговая победа, фора ±1,5, тотал 5,5). В лог: BT2VAR (варианты), BT2SUM, BT2KIND, BT2REL, BT2PICK, BT2CALIB, BT2BEST.

    python team/picks/nhl_bt.py [--quick]"""
import itertools
import json
import math
import multiprocessing
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as BT  # noqa: E402
import calc  # noqa: E402
import nhl_hist as HI  # noqa: E402
import nhl_model as MO  # noqa: E402

MIN_GP = 3
EVAL = (2024, 2025, 2026)
TUNE = (2024, 2025)
QUICK = '--quick' in sys.argv


def out(tag, text):
    print(tag + ' ' + text, flush=True)


# ---------------------------------------------------------------- рынки на сетке счёта

MK = calc.markets('H', 'A')
KEYS = [calc.key_of(m['k']) for m in MK]
G = calc.MAXG + 1
MASK = np.zeros((len(MK), G, G))
DRAWFIN = np.zeros(len(MK))           # итоговая победа: ничья в осн. время → доля s (хозяева) или 1 − s
for n, m in enumerate(MK):
    for i in range(G):
        for j in range(G):
            if m['fin']:
                if i != j and m['f'](dict(fh=i, fa=j)):
                    MASK[n, i, j] = 1
            elif m['f'](dict(h=i, a=j)):
                MASK[n, i, j] = 1
    DRAWFIN[n] = 1 if m['fin'] == 'h' else (-1 if m['fin'] == 'a' else 0)
DIAG = np.eye(G)


FACT = np.array([math.factorial(k) for k in range(G)], dtype=float)
IDX = np.arange(G)


def pm_new(lh, la, rho, s):
    ph = np.exp(-lh) * lh ** IDX / FACT
    pa = np.exp(-la) * la ** IDX / FACT
    P = np.outer(ph, pa)
    P[DIAG == 1] *= rho
    P /= P.sum()
    base = (MASK * P).sum(axis=(1, 2))
    d = np.trace(P)
    return base + np.where(DRAWFIN > 0, d * s, np.where(DRAWFIN < 0, d * (1 - s), 0))


def odds_of(k, o):
    if not o:
        return None
    try:
        if k[0] == 'ml' and k[1] == 0:
            return o['ml'][0 if k[2] == 'home' else 1]
        if k[0] == 'sp' and abs(k[3]) == 1.5:
            home_line = -1.5 if o['sp'][0] == 'h' else 1.5
            if k[2] == 'home' and k[3] == home_line:
                return o['sp'][1]
            if k[2] == 'away' and k[3] == -home_line:
                return o['sp'][2]
            return None
        if k[0] == 'tot' and o['tot'][0] is not None and float(o['tot'][0]) == k[3] and calc._same_total_with_ot(k[3]):
            return o['tot'][1 if k[2] == 'over' else 2]
    except (TypeError, IndexError, KeyError, ValueError):
        return None
    return None


# ---------------------------------------------------------------- данные и старый расчёт (один раз)

SEAS = {}
OLD = {}            # id матча → dict(p_old, pe, lg, rho, y, odds)


def old_day(args):
    s, day = args
    S = SEAS[s]
    prev = [g for g in S if g['d'][:10] < day]
    if len(prev) < 20:
        return []
    pp = calc.prep(prev)
    T = calc.team_games(pp)
    M = calc.model(pp)
    res = []
    for g in (x for x in S if x['d'][:10] == day):
        H, A = g['h'], g['a']
        if len(T.get(H) or []) < MIN_GP or len(T.get(A) or []) < MIN_GP:
            continue
        r = calc.match(T, M, H, A)
        m = min(g['hg'], g['ag'])
        o = dict(h=m if g['e'] else g['hg'], a=m if g['e'] else g['ag'], fh=g['hg'], fa=g['ag'])
        res.append((g['id'], dict(p=[x['p'] for x in r['rows']], pe=[x['pe'] for x in r['rows']], rho=M['rho'],
                                  y=[1 if mk['f'](o) else 0 for mk in MK],
                                  od=[odds_of(mk['k'], g.get('o')) for mk in MK])))
    return res


# ---------------------------------------------------------------- новый расчёт для варианта параметров

def new_variant(P):
    """→ {id матча: [λ-вариант → pm по рынкам]} для 4 вариантов (вратарь да/нет × два дня подряд да/нет)."""
    final, res = {}, {}
    for s in sorted(SEAS):
        S = SEAS[s]
        prior = MO.shrink_prior(final[s - 1], P) if s - 1 in final else None
        mu_prior = final[s - 1]['mu'] if s - 1 in final else None
        prev_season = SEAS.get(s - 1)
        if s in EVAL:
            days = sorted({g['d'][:10] for g in S})
            for day in days:
                todays = [g for g in S if g['d'][:10] == day and g['id'] in OLD]
                if not todays:
                    continue
                prev = [g for g in S if g['d'][:10] < day]
                R = MO.ratings(prev, P, prior, mu_prior)
                GT = MO.goalie_table(prev, prev_season, P)
                for g in todays:
                    H, A = g['h'], g['a']
                    gh, ga = (g.get('g') or [None, None])
                    th, ta = MO.tired(prev, H, g['d']), MO.tired(prev, A, g['d'])
                    v = []
                    for use_g, use_t in ((0, 0), (1, 0), (0, 1), (1, 1)):
                        fh = MO.goalie_factor(GT, gh, P) if use_g else 1.0
                        fa = MO.goalie_factor(GT, ga, P) if use_g else 1.0
                        lh, la = MO.lam(R, H, A, P, fh, fa, th and use_t, ta and use_t)
                        v.append(pm_new(lh, la, OLD[g['id']]['rho'], MO.ot_share(lh, la)))
                    res[g['id']] = v
        final[s] = MO.ratings(S, P, prior, mu_prior)
    return res


def _run(P):
    return P, new_variant(P)


# ---------------------------------------------------------------- оценка

def logloss(recs):
    return -sum(math.log(max(1e-9, p if y else 1 - p)) for p, y in recs) / max(1, len(recs))


def calibrated(recs_by_season):
    """recs_by_season: {s: [(kind, p, y)]} → {s: [(kind, p', y)]}: поправка для сезона — с прошлого сезона."""
    res = {}
    for s in sorted(recs_by_season):
        prev = recs_by_season.get(s - 1)
        ab = {}
        if prev:
            byk = defaultdict(list)
            for k, p, y in prev:
                byk[k].append((p, y))
            ab = {k: BT.fit(v) for k, v in byk.items() if len(v) >= 200}
        res[s] = [(k, BT.apply(ab[k], p) if k in ab else p, y) for k, p, y in recs_by_season[s]]
    return res


def picks(rows, floor_fn, min_odds=calc.MIN_ODDS):
    """rows: [(id, kind, k, p, y, odds)] → отбор как в боте: по матчу самая вероятная с кэфом ≥ min_odds и p ≥ порога."""
    best = {}
    for gid, kind, k, p, y, od in rows:
        if not od or od < min_odds or p < floor_fn(kind):
            continue
        if gid not in best or p > best[gid][1]:
            best[gid] = (kind, p, y, od)
    return list(best.values())


def nhl_floor_kind(kind):
    return calc.NHL_P[0] if kind.startswith('инд. тотал') or kind == 'фора +1.5' else calc.NHL_P[1]


def pick_line(tag, lst):
    if not lst:
        out('BT2PICK', '%s | ставок 0' % tag)
        return
    n = len(lst)
    hit = sum(y for _, _, y, _ in lst)
    roi = sum((od - 1) if y else -1 for _, _, y, od in lst) / n
    out('BT2PICK', '%s | ставок %4d | обещано %4.1f %% | зашло %4.1f %% | ROI %+5.1f %% | средний кэф %.2f' % (
        tag, n, 100 * sum(p for _, p, _, _ in lst) / n, 100 * hit / n, 100 * roi, sum(od for *_, od in lst) / n))


def main():
    global SEAS, OLD
    allg = HI.load()
    for g in allg:
        SEAS.setdefault(g['s'], []).append(g)
    for s in SEAS:
        SEAS[s].sort(key=lambda g: g['d'])
    out('BT2DATA', ' · '.join('%d/%02d: %d матчей, xG %d, вратарь %d, кэфы %d' % (
        s, (s + 1) % 100, len(v), sum(1 for g in v if g.get('x')), sum(1 for g in v if g.get('g') and all(g['g'])),
        sum(1 for g in v if g.get('o'))) for s, v in sorted(SEAS.items())))
    tasks = [(s, d) for s in EVAL if s in SEAS for d in sorted({g['d'][:10] for g in SEAS[s]})]
    ctx = multiprocessing.get_context('fork')
    with ctx.Pool(os.cpu_count() or 2) as pool:
        for part in pool.map(old_day, tasks):
            OLD.update(dict(part))
    sid = {g['id']: g['s'] for g in allg}
    out('BT2DATA', 'матчей в проверке: %s' % ', '.join('%d: %d' % (s, sum(1 for i in OLD if sid[i] == s)) for s in EVAL))

    # сетка параметров рейтинга
    grid = dict(hl=[8.0, 16.0], kp=[4.0, 8.0], reg=[0.33, 0.6], alpha=[0.5, 0.8], beta=[0.8])
    for a in sys.argv[1:]:
        if a.startswith('{'):
            grid = {k: [float(x) for x in v] for k, v in json.loads(a).items()}
    if QUICK:
        grid = dict(hl=[10.0], kp=[6.0], reg=[0.33], alpha=[0.6], beta=[0.8])
    variants = [dict(MO.P0, **dict(zip(grid, vals))) for vals in itertools.product(*grid.values())]
    with ctx.Pool(os.cpu_count() or 2) as pool:
        runs = pool.map(_run, variants)

    WN = (0.6, 0.8, 1.0)              # вес модели против частоты
    LAMV = ('без вратаря и усталости', 'вратарь', 'усталость', 'вратарь + усталость')

    def new_recs(nv, li, wn):
        res = defaultdict(list)
        for gid, v in nv.items():
            o = OLD[gid]
            pm = v[li]
            for n in range(len(MK)):
                res[sid[gid]].append((KEYS[n], wn * pm[n] + (1 - wn) * o['pe'][n], o['y'][n]))
        return res

    old_recs = defaultdict(list)
    for gid, o in OLD.items():
        for n in range(len(MK)):
            old_recs[sid[gid]].append((KEYS[n], o['p'][n], o['y'][n]))
    ll_old = {s: logloss([(p, y) for _, p, y in old_recs[s]]) for s in EVAL}
    out('BT2VAR', 'старый расчёт | logloss ' + ' · '.join('%d: %.4f' % (s, ll_old[s]) for s in EVAL))

    def tune_ll(nv, li, wn):
        rr = new_recs(nv, li, wn)
        return sum(logloss([(p, y) for _, p, y in rr[s]]) * len(rr[s]) for s in TUNE) / max(1, sum(len(rr[s]) for s in TUNE))
    if len(runs) > 12:                 # грубый отбор: усталость + вратарь, модель 0,8 — потом полный перебор лучших 12
        runs = sorted(runs, key=lambda r: min(tune_ll(r[1], li, 0.8) for li in (2, 3)))[:12]
    scored = []
    for P, nv in runs:
        for li in range(4):
            for wn in WN:
                rr = new_recs(nv, li, wn)
                ll = {s: logloss([(p, y) for _, p, y in rr[s]]) for s in EVAL}
                tune = sum(ll[s] * len(rr[s]) for s in TUNE) / max(1, sum(len(rr[s]) for s in TUNE))
                scored.append((tune, P, li, wn, ll))
    scored.sort(key=lambda x: x[0])
    for tune, P, li, wn, ll in scored[:8]:
        out('BT2VAR', 'новый %s | %s | модель %.1f | подбор %.4f | %s' % (
            ' '.join('%s=%g' % (k, P[k]) for k in grid), LAMV[li], wn, tune, ' · '.join('%d: %.4f' % (s, ll[s]) for s in EVAL)))
    # вклад вратаря и усталости при лучших параметрах рейтинга
    bestP = scored[0][1]
    for tune, P, li, wn, ll in scored:
        if P is bestP and wn == scored[0][3]:
            out('BT2VAR', 'вклад | %-26s | подбор %.4f | 2026: %.4f' % (LAMV[li], tune, ll[2026]))

    tune, P, li, wn, ll = scored[0]
    nv = next(v for p, v in runs if p is P)
    new = new_recs(nv, li, wn)
    cal_old, cal_new = calibrated(old_recs), calibrated(new)
    for s in (2025, 2026):
        for tag, rr, cc in (('старый', old_recs, cal_old), ('новый', new, cal_new)):
            b0 = BT.brier([(p, y) for _, p, y in rr[s]])
            b1 = BT.brier([(p, y) for _, p, y in cc[s]])
            out('BT2SUM', '%d/%02d | %-6s | ставок %6d | Брайер %.4f, с поправкой %.4f | logloss %.4f → %.4f' % (
                s, (s + 1) % 100, tag, len(rr[s]), b0, b1, logloss([(p, y) for _, p, y in rr[s]]),
                logloss([(p, y) for _, p, y in cc[s]])))
        for kind in sorted(set(KEYS)):
            xo = [(p, y) for k, p, y in cal_old[s] if k == kind]
            xn = [(p, y) for k, p, y in cal_new[s] if k == kind]
            out('BT2KIND', '%d/%02d | %-22s | Брайер старый %.4f / новый %.4f | обещано %4.1f / %4.1f %% → зашло %4.1f %%' % (
                s, (s + 1) % 100, kind, BT.brier(xo), BT.brier(xn), 100 * sum(p for p, _ in xo) / len(xo),
                100 * sum(p for p, _ in xn) / len(xn), 100 * sum(y for _, y in xo) / len(xo)))
        BT.rel('%d старый' % s, [(p, y) for _, p, y in cal_old[s]])
        BT.rel('%d новый' % s, [(p, y) for _, p, y in cal_new[s]])

    # отбор ставок с кэфами: доля линии
    def rows_for(cal, s, wm, which):
        res = []
        idx = 0
        ids = [gid for gid in OLD if sid[gid] == s] if which == 'old' else [gid for gid in nv if sid[gid] == s]
        # порядок записей cal[s] совпадает с порядком формирования (OLD / nv по сезону)
        flat = cal[s]
        for gid in ids:
            o = OLD[gid]
            for n in range(len(MK)):
                k_, p, y = flat[idx]
                idx += 1
                od = o['od'][n]
                if od:
                    p = (1 - wm) * p + wm / (od * calc.MARGIN_EST)
                res.append((gid, KEYS[n], MK[n]['k'], p, y, od))
        return res

    for s in (2025, 2026):
        for wm in (0.0, 0.25, 0.5, 0.75):
            ro, rn = rows_for(cal_old, s, wm, 'old'), rows_for(cal_new, s, wm, 'new')
            lo = logloss([(p, y) for _, _, _, p, y, od in ro if od])
            ln = logloss([(p, y) for _, _, _, p, y, od in rn if od])
            out('BT2MKT', '%d/%02d | доля линии %.2f | logloss на ставках с кэфом: старый %.4f, новый %.4f' % (s, (s + 1) % 100, wm, lo, ln))
        for wm in (0.25, 0.5):
            ro, rn = rows_for(cal_old, s, wm, 'old'), rows_for(cal_new, s, wm, 'new')
            for tag, rows in (('старый', ro), ('новый', rn)):
                pick_line('%d/%02d | %-6s | линия %.2f | порог бота' % (s, (s + 1) % 100, tag, wm), picks(rows, nhl_floor_kind))
                pick_line('%d/%02d | %-6s | линия %.2f | от 55 %%   ' % (s, (s + 1) % 100, tag, wm), picks(rows, lambda k: 0.55))
                by = defaultdict(list)
                for x in picks(rows, lambda k: 0.55):
                    by[x[0]].append(x)
                for kind, lst in sorted(by.items()):
                    pick_line('%d/%02d | %-6s | линия %.2f | от 55 %% | %s' % (s, (s + 1) % 100, tag, wm, kind), lst)

    # поправка для работы: новый расчёт, оба сезона
    calib = {}
    byk = defaultdict(list)
    for s in (2025, 2026):
        for k, p, y in new[s]:
            byk[k].append((p, y))
    for k, v in byk.items():
        if len(v) >= 200:
            calib[k] = BT.fit(v)
    # рейтинг команд сейчас (лучшие параметры) — для таблицы и для сверки владельцем
    final = {}
    for s in sorted(SEAS):
        prior = MO.shrink_prior(final[s - 1], P) if s - 1 in final else None
        final[s] = MO.ratings(SEAS[s], P, prior, final[s - 1]['mu'] if s - 1 in final else None)
    cur = max(SEAS)
    R = final[cur]
    r100 = MO.rating100(R)
    out('BT2RATE', ' · '.join('%s %d (атака %.2f, оборона %.2f, игр %d)' % (t, r100[t], R['A'][t], R['D'][t], R['n'].get(t, 0))
                             for t in sorted(r100, key=lambda t: -r100[t])))
    GT = MO.goalie_table(SEAS[cur], SEAS.get(cur - 1), P)
    names = {}
    for g in SEAS[cur]:
        for side, gid in zip((g['h'], g['a']), g.get('g') or []):
            names.setdefault(gid, side)
    top = sorted(((MO.gsax(GT, k), k) for k in names if MO.gsax(GT, k) is not None), reverse=True)
    for _, k in top[:6] + top[-6:]:
        try:
            pl = HI.N.get('player/%s/landing' % k)
            names[k] = '%s %s, %s' % (HI.N.dflt(pl.get('firstName')), HI.N.dflt(pl.get('lastName')), names[k])
        except Exception:  # noqa: BLE001
            pass
    out('BT2GK', 'лучшие: ' + ', '.join('%s (%s) %+.1f' % (k, names[k], v) for v, k in top[:6]) + ' | худшие: '
        + ', '.join('%s (%s) %+.1f' % (k, names[k], v) for v, k in top[-6:]))
    out('BT2BEST', json.dumps(dict(P={k: P[k] for k in P}, lam=LAMV[li], wn=wn), ensure_ascii=False))
    out('BT2CALIB', json.dumps(calib, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
