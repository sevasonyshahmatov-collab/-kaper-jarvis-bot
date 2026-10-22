# -*- coding: utf-8 -*-
"""Проверка модели на истории и поправка вероятностей (владелец 22.10: «нужна модель, которая выдаёт наиболее точные
вероятные прогнозы»). Разбор предложений 15–21.10: модель обещала ~62 %, заходило ~50 %.

1) Матчи регулярки КХЛ и НХЛ прошлого (2025/26) и этого сезона. Каждый игровой день модель (calc.model / calc.match)
   строится только по матчам ДО этого дня — как было бы на самом деле. По каждой ставке из calc.markets — обещанная
   вероятность и исход.
2) Поправка по виду ставки (key: «тотал больше 5,5», «фора +1,5», «победа с ОТ» …) и лиге: logit(p') = a + b·logit(p),
   подбор по максимуму правдоподобия. Сначала честно: учим на прошлом сезоне, проверяем на этом (ошибка Брайера до/после,
   «обещали / зашло» по корзинам). Потом — на обоих сезонах, это идёт в работу.
3) В лог: BTREL (надёжность по корзинам), BTKEY (по видам ставок), BTSUM, и CALIBJSON — коэффициенты для calc.py
   (team/picks/calib.json). Сессия переносит CALIBJSON в репозиторий.

    python team/picks/backtest.py
"""
import json
import math
import multiprocessing
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calc  # noqa: E402

MIN_GP = 3          # у обеих команд меньше игр в сезоне — матч не считаем (модель ещё ничего не знает)
BINS = [0.0, 0.35, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9, 1.01]


# ---------------------------------------------------------------- данные

def khl_season(label):
    """Регулярка КХЛ сезона label ('2025/26' или 'current') из приложения КХЛ."""
    import khl_data as K
    boot = K.get('data.json')
    stages = boot.get('stages_v2') or []
    for s in stages:
        print('BTSTAGE', json.dumps({k: s.get(k) for k in ('id', 'season', 'title', 'name', 'type', 'start_at', 'end_at')},
                                    ensure_ascii=False), flush=True)
    if label == 'current':
        st = next((x for x in stages if x.get('id') == boot.get('current_stage_id')), {})
    else:
        y = label[:4]
        cand = [x for x in stages if str(x.get('season') or '').startswith(y)
                and 'егуляр' in str(x.get('title') or x.get('name') or '').lower() + str(x.get('type') or '')]
        cand = cand or [x for x in stages if str(x.get('season') or '').startswith(y)]
        st = cand[0] if cand else {}
    if not st:
        print('BTERR КХЛ: этап сезона %s не найден' % label, flush=True)
        return []
    year = int(str(st.get('season') or label)[:4])
    frm = int(datetime(year, 8, 1, tzinfo=timezone.utc).timestamp())
    to = int(min(datetime(year + 1, 5, 1, tzinfo=timezone.utc), datetime.now(timezone.utc)).timestamp())
    events = []
    for page in range(1, 120):
        q = ('events_v2.json?order_direction=asc&page=%d&q%%5Bstart_at_gt_time_from_unixtime%%5D=%d'
             '&q%%5Bstart_at_lt_time_from_unixtime%%5D=%d&stage_id=%s' % (page, frm, to, st['id']))
        arr = K.get(q)
        if not isinstance(arr, list) or not arr:
            break
        events += [w.get('event') or w for w in arr if (w.get('event') or w).get('type_id') in (18, 24)]
        if len(arr) < 16:
            break
    done = [e for e in events if e.get('game_state_key') == 'finished']
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:
        details = list(ex.map(K.detail, done))
    games = []
    for e, d in zip(done, details):
        src = d or e
        sc = str(src.get('score') or e.get('score') or '').split(':')
        if len(sc) != 2:
            continue
        s = src.get('scores') or {}
        end = 'Б' if s.get('bullitt') else 'ОТ' if s.get('overtime') else ''
        games.append({'d': K.msk(src.get('start_at') or e.get('start_at')), 'h': K.team(src.get('team_a') or e.get('team_a')),
                      'a': K.team(src.get('team_b') or e.get('team_b')), 'hg': int(sc[0]), 'ag': int(sc[1]), 'e': end, 'p': []})
    print('BTDATA КХЛ %s: этап %s, матчей %d' % (label, st.get('id'), len(games)), flush=True)
    return games


def nhl_season(start, end):
    import nhl_data as N
    g = N.season_games(start, end)
    print('BTDATA НХЛ %s…%s: матчей %d' % (start, end, len(g)), flush=True)
    return g


# ---------------------------------------------------------------- проверка

key_of = calc.key_of


_G = None


def _day(d):
    prev = [g for g in _G if g['day'] < d]
    T = calc.team_games(prev)
    if len(prev) < 20:
        return []
    M = calc.model(prev)
    out = []
    for g in (x for x in _G if x['day'] == d):
        H, A = g['home'], g['away']
        if len(T.get(H) or []) < MIN_GP or len(T.get(A) or []) < MIN_GP:
            continue
        r = calc.match(T, M, H, A)
        m = min(g['hg'], g['ag'])
        o = dict(h=m if g['ot'] else g['hg'], a=m if g['ot'] else g['ag'], fh=g['hg'], fa=g['ag'])
        for row, mk in zip(r['rows'], calc.markets(H, A)):
            out.append((key_of(mk['k']), round(row['p'], 5), 1 if mk['f'](o) else 0))
    return out


def backtest(raw):
    global _G
    _G = calc.prep(raw)
    days = sorted({g['day'] for g in _G})
    with multiprocessing.get_context('fork').Pool(os.cpu_count() or 2) as pool:
        parts = pool.map(_day, days)
    return [x for p in parts for x in p]


# ---------------------------------------------------------------- поправка

def logit(p):
    p = min(1 - 1e-6, max(1e-6, p))
    return math.log(p / (1 - p))


def fit(recs, reg=1.0):
    """logit(p') = a + b·logit(p): Ньютон с небольшой регуляризацией к (0, 1)."""
    a, b = 0.0, 1.0
    for _ in range(50):
        ga = reg * a
        gb = reg * (b - 1)
        haa = hbb = reg
        hab = 0.0
        for p, y in recs:
            x = logit(p)
            q = 1 / (1 + math.exp(-(a + b * x)))
            ga += q - y
            gb += (q - y) * x
            w = q * (1 - q)
            haa += w
            hab += w * x
            hbb += w * x * x
        det = haa * hbb - hab * hab
        if det <= 0:
            break
        da = (hbb * ga - hab * gb) / det
        db = (haa * gb - hab * ga) / det
        a, b = a - da, b - db
        if abs(da) + abs(db) < 1e-7:
            break
    return round(a, 4), round(b, 4)


def apply(ab, p):
    a, b = ab
    return 1 / (1 + math.exp(-(a + b * logit(p))))


def brier(recs, f=lambda p: p):
    return sum((f(p) - y) ** 2 for p, y in recs) / max(1, len(recs))


def rel(tag, recs, f=lambda p: p):
    for lo, hi in zip(BINS, BINS[1:]):
        xs = [(f(p), y) for p, y in recs if lo <= f(p) < hi]
        if len(xs) >= 30:
            print('BTREL %s | %2d–%2d %% | ставок %5d | обещано %4.1f %% | зашло %4.1f %%' % (
                tag, 100 * lo, min(100, 100 * hi), len(xs), 100 * sum(p for p, _ in xs) / len(xs),
                100 * sum(y for _, y in xs) / len(xs)), flush=True)


def main():
    today = datetime.now(timezone(timedelta(hours=3))).date().isoformat()
    data = {
        ('KHL', 'past'): khl_season('2025/26'),
        ('KHL', 'now'): khl_season('current'),
        ('NHL', 'past'): nhl_season('2025-10-07', '2026-04-18'),
        ('NHL', 'now'): nhl_season('2026-09-29', today),
    }
    res = {k: backtest(v) for k, v in data.items() if v}
    calib = {}
    for lg in ('KHL', 'NHL'):
        past, now = res.get((lg, 'past'), []), res.get((lg, 'now'), [])
        by_p, by_n = defaultdict(list), defaultdict(list)
        for k, p, y in past:
            by_p[k].append((p, y))
        for k, p, y in now:
            by_n[k].append((p, y))
        # 1) честно: поправка с прошлого сезона на этот
        tot_b0 = tot_b1 = 0.0
        cal_now = []
        for k in sorted(set(by_p) | set(by_n)):
            ab = fit(by_p[k]) if len(by_p[k]) >= 200 else (0.0, 1.0)
            xs = by_n[k]
            if xs:
                b0, b1 = brier(xs), brier(xs, lambda p: apply(ab, p))
                tot_b0 += b0 * len(xs)
                tot_b1 += b1 * len(xs)
                cal_now += [(apply(ab, p), y) for p, y in xs]
                print('BTKEY %s | %-24s | прошлый сезон %5d, этот %4d | обещано %4.1f %% → зашло %4.1f %% | Брайер %.4f → %.4f | a=%+.3f b=%.3f'
                      % (lg, k, len(by_p[k]), len(xs), 100 * sum(p for p, _ in xs) / len(xs),
                         100 * sum(y for _, y in xs) / len(xs), b0, b1, ab[0], ab[1]), flush=True)
        n_now = max(1, sum(len(v) for v in by_n.values()))
        print('BTSUM %s | этот сезон, ставок %d | Брайер модели %.4f → с поправкой прошлого сезона %.4f' % (
            lg, n_now, tot_b0 / n_now, tot_b1 / n_now), flush=True)
        rel(lg + ' модель', [(p, y) for v in by_n.values() for p, y in v])
        rel(lg + ' поправка', cal_now)
        # 2) в работу: оба сезона
        calib[lg] = {}
        for k in sorted(set(by_p) | set(by_n)):
            recs = by_p[k] + by_n[k]
            if len(recs) >= 200:
                calib[lg][k] = fit(recs)
    print('CALIBJSON ' + json.dumps(dict(made=today, note='backtest.py: logit(p\') = a + b·logit(p) по виду ставки и лиге',
                                         **calib), ensure_ascii=False, separators=(',', ':')), flush=True)


if __name__ == '__main__':
    main()
