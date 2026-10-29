# -*- coding: utf-8 -*-
"""Новый рейтинг НХЛ (владелец 29.10: «пересоберём НХЛ, нужно больше точности, люди на нас надеются»).

Сила команды — атака A и оборона D (1,00 = средняя команда лиги), ожидаемые голы в основное время:
    λ хозяев = голы лиги дома × A хозяев × D гостей × вратарь гостей × усталость,   гости — зеркально.
  • Форма — по каждому матчу сезона: атака = α·xG + (1−α)·голы, оборона = β·xG соперника + (1−β)·пропущенные, с поправкой
    на силу соперника и дом/выезд; свежие матчи весят больше (вес матча ½ через hl игр назад).
  • Старт сезона — сила прошлого сезона, сжатая к средней (reg: 0,33 = втрое), её вес kp/(kp + игр) тает с каждой игрой
    (kp = 6: после 6 игр — половина, к 20 играм — меньше четверти).
  • Вратарь — качество каждого в этом сезоне (и прошлый с весом gw_prev): пропущено / xG по броскам в его ворота
    (сейвы выше ожидаемого, GSAx), сжато к средней на cg xG; запасной может быть лучше основного — берём именно того,
    кто стартует. Сила вратаря в степени gamma.
  • Игры два дня подряд: у уставшей команды атака × (1 − b2b_o), её соперник забивает × (1 + b2b_d).
Данные — team/picks/nhl_hist.py; проверка на истории — team/picks/nhl_bt.py; в прогнозы — calc.py (LEAGUE='NHL')."""
import math
from collections import defaultdict

P0 = dict(hl=10.0, kp=6.0, reg=0.33, alpha=0.6, beta=0.8, cg=40.0, gw_prev=0.5, gamma=1.0, b2b_o=0.04, b2b_d=0.06,
          kmu=300.0, iters=3)


def _obs(g, P):
    """Атака и оборона матча глазами хозяев и гостей (осн. время). Без xG — только голы."""
    r = g.get('r') or [g['hg'], g['ag']]
    x = g.get('x') or r
    a, b = P['alpha'], P['beta']
    off_h, off_a = a * x[0] + (1 - a) * r[0], a * x[1] + (1 - a) * r[1]
    def_h, def_a = b * x[1] + (1 - b) * r[1], b * x[0] + (1 - b) * r[0]
    return off_h, off_a, def_h, def_a


def league(games, P, prior=None):
    """Средние лиги: голы дома / в гостях (осн. время) и средние «наблюдения» атаки и обороны (для нормировки)."""
    n = len(games)
    pr = prior or dict(gh=3.05, ga=2.75, oh=3.05, oa=2.75, dh=2.75, da=3.05)
    k = P['kmu']
    s = defaultdict(float)
    for g in games:
        r = g.get('r') or [g['hg'], g['ag']]
        oh, oa, dh, da = _obs(g, P)
        s['gh'] += r[0]
        s['ga'] += r[1]
        s['oh'] += oh
        s['oa'] += oa
        s['dh'] += dh
        s['da'] += da
    return {key: (s[key] + k * pr[key]) / (n + k) for key in pr}


def ratings(games, P, prior=None, mu_prior=None):
    """games — матчи одного сезона до дня расчёта (по времени). prior — {команда: (A, D)} прошлого сезона (уже сжатые).
    → dict(A, D, n, mu)."""
    mu = league(games, P, mu_prior)
    prior = prior or {}
    per = defaultdict(list)                 # команда → [(дом?, соперник, атака, оборона)]
    for g in games:
        oh, oa, dh, da = _obs(g, P)
        per[g['h']].append((True, g['a'], oh, dh))
        per[g['a']].append((False, g['h'], oa, da))
    teams = set(per) | set(prior)
    A = {t: prior.get(t, (1.0, 1.0))[0] for t in teams}
    D = {t: prior.get(t, (1.0, 1.0))[1] for t in teams}
    hl = P['hl']
    for _ in range(int(P['iters'])):
        nA, nD = {}, {}
        for t in teams:
            lst = per.get(t) or []
            n = len(lst)
            pa, pd = prior.get(t, (1.0, 1.0))
            if not n:
                nA[t], nD[t] = pa, pd
                continue
            sw = sa = sd = 0.0
            for i, (home, opp, o, d) in enumerate(lst):
                w = 0.5 ** ((n - 1 - i) / hl)
                # атака: сколько создала против этой обороны (дома — к домашнему среднему)
                sa += w * o / ((mu['oh'] if home else mu['oa']) * D.get(opp, 1.0))
                sd += w * d / ((mu['dh'] if home else mu['da']) * A.get(opp, 1.0))
                sw += w
            wp = P['kp'] / (P['kp'] + n)
            nA[t] = wp * pa + (1 - wp) * sa / sw
            nD[t] = wp * pd + (1 - wp) * sd / sw
        # нормировка: средняя команда = 1
        ma = sum(nA.values()) / len(nA)
        md = sum(nD.values()) / len(nD)
        A = {t: v / ma for t, v in nA.items()}
        D = {t: v / md for t, v in nD.items()}
    return dict(A=A, D=D, n={t: len(per.get(t) or []) for t in teams}, mu=mu)


def shrink_prior(R, P):
    """Сила конца прошлого сезона → старт нового: сжать к средней (reg)."""
    return {t: (1 + P['reg'] * (R['A'][t] - 1), 1 + P['reg'] * (R['D'][t] - 1)) for t in R['A']}


# ---------------------------------------------------------------- вратари

def goalie_table(games_cur, games_prev, P):
    """{id вратаря: (пропущено, xG против) с весом прошлого сезона} и отношение лиги голы/xG."""
    T = defaultdict(lambda: [0.0, 0.0])
    G = X = 0.0
    for lst, w in ((games_prev or [], P['gw_prev']), (games_cur, 1.0)):
        for g in lst:
            for k, (xg, ga) in (g.get('gs') or {}).items():
                T[k][0] += w * ga
                T[k][1] += w * xg
                G += w * ga
                X += w * xg
    return dict(T=T, L=(G / X) if X else 1.0)


def goalie_factor(GT, gid, P):
    """Во сколько раз вратарь пропускает больше средней (меньше 1 — лучше среднего). Нет истории — 1,02."""
    if not gid or gid not in GT['T']:
        return 1.02
    ga, xg = GT['T'][gid]
    L = GT['L']
    f = (ga + P['cg'] * L) / (xg + P['cg']) / L
    return f ** P['gamma']


def gsax(GT, gid):
    """Сейвы выше ожидаемого (GSAx) с весом прошлого сезона — для фактов."""
    if gid not in GT['T']:
        return None
    ga, xg = GT['T'][gid]
    return xg * GT['L'] - ga


# ---------------------------------------------------------------- усталость

def tired(games_cur, team, start_msk, hours=30):
    """Играла ли команда меньше чем за hours часов до этого матча (два дня подряд)."""
    from datetime import datetime
    t0 = datetime.strptime(start_msk[:16], '%Y-%m-%d %H:%M')
    for g in reversed(games_cur):
        if team in (g['h'], g['a']) and g['d'] < start_msk:
            dt = (t0 - datetime.strptime(g['d'][:16], '%Y-%m-%d %H:%M')).total_seconds() / 3600
            return dt < hours
    return False


def lam(R, H, A, P, gk_h=1.0, gk_a=1.0, tired_h=False, tired_a=False):
    """Ожидаемые голы в основное время. gk_h — фактор вратаря хозяев (влияет на голы гостей)."""
    mu = R['mu']
    lh = mu['gh'] * R['A'].get(H, 1.0) * R['D'].get(A, 1.0) * gk_a
    la = mu['ga'] * R['A'].get(A, 1.0) * R['D'].get(H, 1.0) * gk_h
    if tired_h:
        lh *= 1 - P['b2b_o']
        la *= 1 + P['b2b_d']
    if tired_a:
        la *= 1 - P['b2b_o']
        lh *= 1 + P['b2b_d']
    return lh, la


def ot_share(lh, la):
    """Доля побед хозяев в ОТ/Б при ничьей в осн. время — от соотношения сил, в пределах 0,35–0,65."""
    return max(0.35, min(0.65, 0.5 + 0.6 * (lh - la) / (lh + la)))


def rating100(R):
    """Сила для таблицы по шкале 1–100: 50 — средняя команда, ±10 ≈ ±0,25 гола разницы за матч."""
    mu = R['mu']
    res = {}
    for t in R['A']:
        diff = (mu['gh'] + mu['ga']) / 2 * (R['A'][t] - R['D'][t])
        res[t] = max(1, min(100, round(50 + 40 * diff)))
    return res


def log_prob(p):
    return math.log(max(1e-9, min(1 - 1e-9, p)))
