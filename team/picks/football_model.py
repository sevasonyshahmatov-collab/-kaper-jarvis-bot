# -*- coding: utf-8 -*-
"""Рейтинг футбольных клубов (ТЗ docs/handoff/FOOTBALL_BRIEF.md, этап 1; владелец 30.10: «прогнозы ещё и на футбол»).

Сила команды — атака A и оборона D (1,00 = средняя команда своей лиги), ожидаемые голы за 90 минут:
    λ хозяев = голы лиги дома × A хозяев × D гостей,   λ гостей = голы лиги в гостях × A гостей × D хозяев.
  • Наблюдение матча: атака = α·xG + (1−α)·голы, оборона — то же по сопернику. xG — «ожидаемые голы по ударам»
    (удары в створ и мимо × реализация лиги за прошлые сезоны, football_hist.py): настоящего xG для Португалии нет,
    а по ударам он есть во всех шести лигах одинаково.
  • Свежие матчи весомее: вес матча ½ через hl дней. Прошлый сезон входит сам (с весом по давности); новичок лиги
    (поднялся из низшей) стартует с атакой new_a и обороной new_d — средний новичок слабее середины.
  • Сжатие к средней — k псевдо-матчей «средней команды» у каждой: в начале сезона рейтинг осторожный.
  • Счёт — Пуассон с поправкой Дикси-Коулса rho на 0:0, 1:0, 0:1, 1:1 → 1Х2, «не проиграет», тоталы, «обе забьют», форы.
Еврокубки: сила клуба в общей шкале — Elo clubelo.com (один рейтинг для всех лиг Европы) + своя форма в лиге,
см. cup_lambdas. Данные — football_hist.py, проверка — football_bt.py, в прогнозы — football_live.py."""
import math
from collections import defaultdict

P0 = dict(hl=150.0, alpha=0.5, k=4.0, new_a=0.85, new_d=1.15, rho=-0.06, iters=12)
# еврокубки: log λ = c0 ± dElo/400·c1 (+ дом), λ сумма подправлена формой в лиге (w_dom)
C0 = dict(c0=0.20, c1=0.92, home=0.12, w_dom=0.5)
MAXG = 11


def obs(g, alpha):
    """Атака хозяев/гостей матча: смесь голов и xG по ударам."""
    x = g.get('x') or [g['hg'], g['ag']]
    return alpha * x[0] + (1 - alpha) * g['hg'], alpha * x[1] + (1 - alpha) * g['ag']


def fit(games, day, P, known=None):
    """Рейтинг на утро дня day по матчам лиги до него. games — по возрастанию даты, одна лига.
    known — команды прошлого сезона этой лиги (остальные — новички). → (ratings{team: (A, D)}, mu_h, mu_a)."""
    from datetime import date
    d0 = date.fromisoformat(day)
    ln2 = math.log(2) / P['hl']
    rows = []
    sw = sh = sa = 0.0
    for g in games:
        if g['d'] >= day:
            break
        age = (d0 - date.fromisoformat(g['d'])).days
        if age > 4 * P['hl']:
            continue
        w = math.exp(-ln2 * age)
        oh, oa = obs(g, P['alpha'])
        rows.append((g['h'], g['a'], oh, oa, w))
        sw += w
        sh += w * oh
        sa += w * oa
    if not rows:
        return {}, 1.5, 1.2
    mu_h, mu_a = sh / sw, sa / sw
    teams = {t for r in rows for t in r[:2]}
    A = {t: 1.0 for t in teams}
    D = {t: 1.0 for t in teams}
    pa, pd = {}, {}
    for t in teams:
        new = known is not None and t not in known
        pa[t], pd[t] = (P['new_a'], P['new_d']) if new else (1.0, 1.0)
    k = P['k']
    for _ in range(P['iters']):
        num = defaultdict(float)
        den = defaultdict(float)
        for h, a, oh, oa, w in rows:
            num[h] += w * oh
            den[h] += w * mu_h * D[a]
            num[a] += w * oa
            den[a] += w * mu_a * D[h]
        for t in teams:      # псевдо-матчи: k игр со средним соперником на уровне prior
            A[t] = (num[t] + k * pa[t]) / (den[t] + k)
        num = defaultdict(float)
        den = defaultdict(float)
        for h, a, oh, oa, w in rows:
            num[a] += w * oh
            den[a] += w * mu_h * A[h]
            num[h] += w * oa
            den[h] += w * mu_a * A[a]
        for t in teams:
            D[t] = (num[t] + k * pd[t]) / (den[t] + k)
        ma = sum(A.values()) / len(A)
        md = sum(D.values()) / len(D)
        for t in teams:
            A[t] /= ma
            D[t] /= md
    return {t: (A[t], D[t]) for t in teams}, mu_h, mu_a


def lambdas(R, mu_h, mu_a, h, a, P, known=None):
    def get(t):
        if t in R:
            return R[t]
        return (P['new_a'], P['new_d'])
    Ah, Dh = get(h)
    Aa, Da = get(a)
    return mu_h * Ah * Da, mu_a * Aa * Dh


def score_matrix(lh, la, rho):
    ph = [math.exp(-lh) * lh ** i / math.factorial(i) for i in range(MAXG)]
    pa = [math.exp(-la) * la ** i / math.factorial(i) for i in range(MAXG)]
    M = [[ph[i] * pa[j] for j in range(MAXG)] for i in range(MAXG)]
    M[0][0] *= max(1e-6, 1 - lh * la * rho)
    M[0][1] *= max(1e-6, 1 + lh * rho)
    M[1][0] *= max(1e-6, 1 + la * rho)
    M[1][1] *= max(1e-6, 1 - rho)
    s = sum(map(sum, M))
    return [[v / s for v in r] for r in M]


def markets(lh, la, rho):
    """Вероятности рынков за 90 минут: ключ → p."""
    M = score_matrix(lh, la, rho)
    p1 = sum(M[i][j] for i in range(MAXG) for j in range(MAXG) if i > j)
    px = sum(M[i][i] for i in range(MAXG))
    p2 = 1 - p1 - px
    tot = defaultdict(float)
    for i in range(MAXG):
        for j in range(MAXG):
            tot[i + j] += M[i][j]
    r = {'П1': p1, 'Х': px, 'П2': p2, '1Х': p1 + px, 'Х2': px + p2}
    for line in (1.5, 2.5, 3.5):
        under = sum(v for n, v in tot.items() if n < line)
        r['ТБ %.1f' % line] = 1 - under
        r['ТМ %.1f' % line] = under
    nb = sum(M[i][0] for i in range(MAXG)) + sum(M[0][j] for j in range(MAXG)) - M[0][0]
    r['ОЗ да'] = 1 - nb
    r['ОЗ нет'] = nb
    for hc in (-1.5, 1.5):     # фора хозяев
        r['Ф1 %+.1f' % hc] = sum(M[i][j] for i in range(MAXG) for j in range(MAXG) if i - j + hc > 0)
        r['Ф2 %+.1f' % (-hc)] = 1 - r['Ф1 %+.1f' % hc]
    return r


def cup_lambdas(elo_h, elo_a, C, dom_h=None, dom_a=None, neutral=False):
    """Еврокубок: ожидаемые голы из разницы Elo (общая шкала Европы). dom_* — (A, D, mu) клуба в своей лиге, если она
    из шести наших: поправляет «голевитость» (атака × оборона), не силу — силу между лигами меряет Elo."""
    d = (elo_h - elo_a) / 400.0
    hm = 0 if neutral else C['home']
    lh = math.exp(C['c0'] + hm / 2 + C['c1'] * d / 2)
    la = math.exp(C['c0'] - hm / 2 - C['c1'] * d / 2)
    w = C['w_dom']
    if w and dom_h and dom_a:
        # отношение атаки к обороне соперника внутри своих лиг против нейтрального (1,1)
        fh = (dom_h[0] * dom_a[1]) ** 0.5
        fa = (dom_a[0] * dom_h[1]) ** 0.5
        lh *= fh ** w
        la *= fa ** w
    return lh, la
