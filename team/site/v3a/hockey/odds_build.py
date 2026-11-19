# -*- coding: utf-8 -*-
"""«Где закончат сезон» (владелец 19.11, по образцу раздела Final table odds у markstats.club): шансы каждого клуба КХЛ и НХЛ
на плей-офф, на 1-е место в конференции и на каждое место — по 10 000 розыгрышей оставшихся матчей регулярного чемпионата.

Вход (без сети): assets/data/teams.json (очки, игры, шайбы — официальная таблица), team/season.json (сыгранные матчи и
расписание), team/khl_rest.json (полное расписание КХЛ до конца регулярки — пишет daily/hockey_season.py в Actions; если
файла нет, недостающие матчи клуба КХЛ разыгрываются против случайного соперника лиги).
Выход: hockey/data/odds_khl.json, hockey/data/odds_nhl.json (страница лиги hockey/league.html, блок «Где закончат сезон»).

Модель: сила атаки и обороны клуба — шайбы за игру в сезоне, подтянутые к среднему по лиге (как будто ещё 12 средних матчей);
преимущество своей площадки — по сыгранным матчам лиги; в каждом розыгрыше сила клубов чуть «дрожит» (мы не знаем её точно),
голы — по Пуассону; ничья → овертайм/буллиты: победителю 2 очка, проигравшему 1. Это расчёт, а не прогноз канала и не ставка.
Запуск: python3 hockey/odds_build.py [число_розыгрышей]"""
import json, os, sys
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
V3A = os.path.dirname(HERE)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
SHRINK = 12        # «виртуальные» средние матчи, к которым подтягиваем силу клуба
NOISE = 0.09       # разброс силы клуба между розыгрышами (лог-шкала)
GAMES = {'khl': 68}  # матчей у клуба в регулярке КХЛ (НХЛ — по полному расписанию)
NHL_DIV = {
    'Атлантический': ['nhl_bos', 'nhl_buf', 'nhl_det', 'nhl_fla', 'nhl_mtl', 'nhl_ott', 'nhl_tbl', 'nhl_tor'],
    'Столичный': ['nhl_car', 'nhl_cbj', 'nhl_njd', 'nhl_nyi', 'nhl_nyr', 'nhl_phi', 'nhl_pit', 'nhl_wsh'],
    'Центральный': ['nhl_chi', 'nhl_col', 'dallas', 'minnesota', 'nhl_nsh', 'nhl_stl', 'nhl_uta', 'nhl_wpg'],
    'Тихоокеанский': ['nhl_ana', 'nhl_cgy', 'nhl_edm', 'nhl_lak', 'nhl_sjs', 'nhl_sea', 'nhl_van', 'nhl_vgk'],
}
DIV_OF = {t: d for d, ts in NHL_DIV.items() for t in ts}


def jload(p, d=None):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return d


def build(lg, TM, SE, rest, rng):
    ids = [k for k, t in TM.items() if t.get('lg') == lg]
    ids.sort(key=lambda k: TM[k]['name'])
    ix = {k: i for i, k in enumerate(ids)}
    by_name = {TM[k]['name']: k for k in ids}
    n = len(ids)
    gi = lambda k, f: int(float(TM[k].get(f) or 0))
    pts0 = np.array([gi(k, 'pts') for k in ids], float)
    gp = np.array([gi(k, 'gp') for k in ids], float)
    w0 = np.array([gi(k, 'w') for k in ids], float)
    gf = np.array([gi(k, 'gf') for k in ids], float)
    ga = np.array([gi(k, 'ga') for k in ids], float)

    # сыгранные (для преимущества площадки) и оставшиеся матчи (со стороны хозяев)
    hg = ag = cnt = 0
    fut = []
    for name, t in (SE.get(lg) or {}).items():
        h = by_name.get(name)
        if h is None:
            continue
        for g in t.get('games') or []:
            if g.get('h') != 1:
                continue
            a = by_name.get(g.get('o'))
            if a is None:
                continue
            if g.get('gf') is None:
                fut.append((g.get('d') or '', ix[h], ix[a]))
            else:
                hg += g['gf']; ag += g['ga']; cnt += 1
    full = True
    if lg == 'khl' and rest:
        known = {(d[:10], h, a) for d, h, a in fut}
        for d, hn, an in rest:
            h, a = by_name.get(hn), by_name.get(an)
            if h is not None and a is not None and (d[:10], ix[h], ix[a]) not in known:
                fut.append((d, ix[h], ix[a])); known.add((d[:10], ix[h], ix[a]))
    sched = np.zeros(n)
    for _, h, a in fut:
        sched[h] += 1; sched[a] += 1
    extra = np.zeros(n, int)
    if lg in GAMES:
        extra = np.maximum(0, GAMES[lg] - gp - sched).astype(int)
        full = not extra.any()
    total_games = int(round(float(np.max(gp + sched + extra)))) if n else 0

    mu = (gf.sum() + ga.sum()) / max(1.0, 2 * gp.sum())          # шайб за игру у одной команды
    att = (gf + SHRINK * mu) / (gp + SHRINK) / mu
    dfn = (ga + SHRINK * mu) / (gp + SHRINK) / mu
    home = np.sqrt(hg / ag) if cnt and ag else 1.05               # множитель хозяевам и делитель гостям
    H = np.array([f[1] for f in fut], int)
    A = np.array([f[2] for f in fut], int)

    places = np.zeros((n, n))            # место в конференции (индекс 0 = 1-е)
    lgfirst = np.zeros(n)
    po = np.zeros(n)
    finals = np.zeros((N, n))
    conf = [TM[k].get('conf') or '' for k in ids]
    confs = sorted(set(conf), key=lambda c: (c != ('Запад' if lg == 'khl' else 'Восток'), c))
    cmask = {c: np.array([x == c for x in conf]) for c in confs}
    div = [DIV_OF.get(k, '') for k in ids]

    for s in range(N):
        a_s = att * np.exp(rng.normal(0, NOISE, n))
        d_s = dfn * np.exp(rng.normal(0, NOISE, n))
        pts = pts0.copy(); wins = w0.copy()
        if len(H):
            lh = mu * a_s[H] * d_s[A] * home
            la = mu * a_s[A] * d_s[H] / home
            xh = rng.poisson(lh); xa = rng.poisson(la)
            tie = xh == xa
            p_ot = 0.5 + (lh / (lh + la) - 0.5) * 0.5
            hw = np.where(tie, rng.random(len(H)) < p_ot, xh > xa)
            np.add.at(pts, H, np.where(hw, 2, np.where(tie, 1, 0)))
            np.add.at(pts, A, np.where(~hw, 2, np.where(tie, 1, 0)))
            np.add.at(wins, H, hw.astype(float))
            np.add.at(wins, A, (~hw).astype(float))
        if extra.any():                                         # КХЛ без полного расписания: соперник — случайный клуб лиги
            for i in np.nonzero(extra)[0]:
                k = extra[i]
                opp = rng.integers(0, n - 1, k); opp[opp >= i] += 1
                isH = rng.random(k) < 0.5
                lt = mu * a_s[i] * d_s[opp] * np.where(isH, home, 1 / home)
                lo = mu * a_s[opp] * d_s[i] * np.where(isH, 1 / home, home)
                xt = rng.poisson(lt); xo = rng.poisson(lo)
                tie = xt == xo
                win = np.where(tie, rng.random(k) < 0.5 + (lt / (lt + lo) - 0.5) * 0.5, xt > xo)
                pts[i] += np.sum(np.where(win, 2, np.where(tie, 1, 0))); wins[i] += win.sum()
        finals[s] = pts
        key = pts * 1000 + wins + rng.random(n) * 0.5            # очки, затем победы, затем жребий
        lgfirst[int(np.argmax(key))] += 1
        for c in confs:
            idx = np.nonzero(cmask[c])[0]
            order = idx[np.argsort(-key[idx])]
            for p, i in enumerate(order):
                places[i, p] += 1
            if lg == 'khl':
                po[order[:8]] += 1
            else:
                inn = []
                for dv in sorted({div[i] for i in idx}):
                    inn += [i for i in order if div[i] == dv][:3]
                inn += [i for i in order if i not in inn][:2]
                po[inn] += 1

    pc = lambda v: round(float(v) / N * 100, 1)
    rows = []
    for k, i in ix.items():
        sz = int(cmask[conf[i]].sum())
        rows.append({'id': k, 'name': TM[k]['name'], 'conf': conf[i], 'div': div[i] or None, 'gp': int(gp[i]), 'pts': int(pts0[i]),
                     'left': int(sched[i] + extra[i]),
                     'xp': round(float(finals[:, i].mean()), 1),
                     'lo': int(np.percentile(finals[:, i], 10)), 'hi': int(np.percentile(finals[:, i], 90)),
                     'po': pc(po[i]), 'c1': pc(places[i, 0]), 'l1': pc(lgfirst[i]),
                     'pl': [pc(v) for v in places[i, :sz]]})
    rows.sort(key=lambda r: (-r['xp'], -r['pts']))
    now = datetime.now(timezone(timedelta(hours=3))).strftime('%Y-%m-%d %H:%M')
    return {'lg': lg, 'built': now, 'src_built': TM_BUILT, 'sims': N, 'games': total_games, 'confs': confs,
            'po_rule': 'по 8 лучших в каждой конференции' if lg == 'khl' else 'по 3 лучших в каждом дивизионе и ещё по 2 в конференции (уайлд-кард)',
            'full_schedule': bool(full), 'left_games': len(fut) + int(extra.sum()) // 2,
            'home': round(float(home * home), 3), 'teams': rows}


if __name__ == '__main__':
    T = jload(os.path.join(V3A, 'assets', 'data', 'teams.json'), {})
    TM, TM_BUILT = T.get('teams') or {}, T.get('built')
    SE = jload(os.path.join(V3A, 'team', 'season.json'), {})
    rest = jload(os.path.join(V3A, 'team', 'khl_rest.json'))
    rng = np.random.default_rng(20261119)
    out = []
    for lg in ('khl', 'nhl'):
        r = build(lg, TM, SE, rest if lg == 'khl' else None, rng)
        if len(r['teams']) < (20 if lg == 'khl' else 30):
            raise SystemExit('мало клубов %s: %d — файл не меняю' % (lg, len(r['teams'])))
        p = os.path.join(HERE, 'data', 'odds_%s.json' % lg)
        with open(p + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(r, f, ensure_ascii=False, separators=(',', ':'))
        os.replace(p + '.tmp', p)
        out.append('%s: %d клубов, осталось матчей %d, расписание %s' % (lg, len(r['teams']), r['left_games'], 'полное' if r['full_schedule'] else 'частично'))
    print('; '.join(out))
