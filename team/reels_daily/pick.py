# -*- coding: utf-8 -*-
"""Прогноз на матч для ролика — правило владельца 17.10: из «Что заходит» (team/picks/calc.py) самое вероятное событие
с кэфом 1,6–2,3. Равный матч (П1 и П2 близки) — ближе к 1,6–1,7; аутсайдер против сильного — 1,8–2,0.
Пример 17.10: Сибирь — Барыс (2.60/3.70/2.40) → ТБ 4,5 за 1,61; Сочи — Локомотив (6.80/4.70/1.41) → фора Локомотива −1,5 за 1,75."""
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'team', 'picks'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'daily'))

import calc  # noqa: E402
from settle import gen  # noqa: E402

LO, HI = 1.6, 2.3
MIN_P = 0.45            # ниже — уже не «самая вероятная», матч без ролика
NEAR = 0.04             # в пределах 4 п. п. от самой вероятной выбираем кэф, подходящий матчу
EQUAL, STRONG = 0.75, 0.5   # П-меньший / П-больший: ≥ 0,75 — равный матч; < 0,5 — аутсайдер против сильного


def band(x1x2):
    """Желательный коридор кэфа по линии П1 · Х · П2."""
    p1, _, p2 = (x1x2 or (None, None, None))[:3]
    if not p1 or not p2:
        return LO, HI
    r = min(p1, p2) / max(p1, p2)
    if r >= EQUAL:
        return 1.6, 1.7
    if r < STRONG:
        return 1.8, 2.0
    return LO, HI


def choose(rows, x1x2, avoid=()):
    """rows — ставки calc.brief (t, g, p, odds). avoid — виды ставок (g), уже взятые сегодня: берём другой вид,
    если он не дальше NEAR от лучшего. → ставка или None."""
    ok = [x for x in rows if x.get('odds') and LO <= x['odds'] <= HI and x['p'] >= MIN_P]
    if not ok:
        return None
    best = max(x['p'] for x in ok)
    near = [x for x in ok if x['p'] >= best - NEAR]
    lo, hi = band(x1x2)
    dist = lambda x: max(lo - x['odds'], 0, x['odds'] - hi)  # noqa: E731
    near.sort(key=lambda x: (round(dist(x), 3) > 0.05, x['g'] in avoid, -x['p']))
    return near[0]


def human(t, h, a, ot=False):
    """Строка «Что заходит» → прогноз по-человечески (как в постах канала). ot — дописать «в основное время» к форе
    и тоталам (НХЛ: там по умолчанию считают с овертаймом)."""
    tail = ' в основное время' if ot else ''
    num = lambda s: s.replace('-', '−')  # noqa: E731
    m = re.match(r'П([12]) (.+) в осн\. время$', t)
    if m:
        return 'Победа %s в основное время' % gen(m.group(2))
    if t.startswith('Х ничья'):
        return 'Ничья в основное время'
    m = re.match(r'(?:1Х|Х2) (.+) не проиграет в осн\. время$', t)
    if m:
        return '%s не проиграет в основное время' % m.group(1)
    m = re.match(r'итоговая победа (.+) \(с ОТ и Б\)$', t)
    if m:
        return 'Итоговая победа %s' % gen(m.group(1))
    m = re.match(r'Ф[12]\(([-+][\d,]+)\) (.+)$', t)
    if m:
        return 'Фора %s %s%s' % (gen(m.group(2)), num(m.group(1)), tail)
    m = re.match(r'Т([БМ]) ([\d,]+) в осн\. время$', t)
    if m:
        return 'Тотал матча %s %s%s' % ('больше' if m.group(1) == 'Б' else 'меньше', m.group(2), tail)
    m = re.match(r'ИТ([БМ]) ([\d,]+) (.+) в осн\. время$', t)
    if m:
        return 'Тотал %s %s %s%s' % (gen(m.group(3)), 'больше' if m.group(1) == 'Б' else 'меньше', m.group(2), tail)
    return t


def day_picks(games, nxt, pins, fon, league='khl', backup=()):
    """→ [{h, a, d, arena, x1x2, t, g, p, odds, pick}] — по матчу дня, у кого нашёлся прогноз по правилу."""
    G = calc.prep(games)
    T = calc.team_games(G)
    M = calc.model(G)
    out, kinds = [], []
    for x in nxt:
        H, A = x['h'], x['a']
        if H not in T or A not in T:
            print('PICK %s — %s: у команды нет матчей в сезоне' % (H, A), flush=True)
            continue
        r = calc.match(T, M, H, A)
        mks, fb = (pins or {}).get((H, A)), (fon or {}).get((H, A))
        rows, _ = calc.brief(H, A, r, mks, fb)
        x1x2 = [calc.odds_for(('ml', 6, s), mks)[0] or calc.fonbet_for(('ml', 6, s), fb) for s in ('home', 'draw', 'away')]
        if not all(x1x2):
            if (H, A) not in backup:
                print('PICK %s — %s: нет линии П1/Х/П2 — без ролика' % (H, A), flush=True)
                continue
            x1x2 = None                     # запасная линия ESPN: только рынки с ОТ, коридор кэфа — общий 1,6–2,3
        c = choose(rows, x1x2, avoid=kinds)
        if not c:
            print('PICK %s — %s: нет ставки от %d %% с кэфом %.1f–%.1f — без ролика' % (H, A, MIN_P * 100, LO, HI), flush=True)
            continue
        kinds.append(c['g'])
        mk = next((k for k in calc.markets(H, A) if k['t'] == c['t']), None)
        out.append(dict(h=H, a=A, d=x['d'], arena=x.get('arena') or '', x1x2=x1x2, t=c['t'], g=c['g'], p=c['p'],
                        odds=round(c['odds'], 2), sim=simulate(r, M, mk, H + A), fact=fact(T, H, A, mk),
                        pick=human(c['t'], H, A, ot=league == 'nhl' and not str(c.get('src')).startswith('с ОТ ='))))
        out[-1]['line_src'] = 'DraftKings (ESPN)' if (H, A) in backup else 'Pinnacle'
        print('PICK %s — %s | %s | %.1f%% | кэф %.2f | линия %s' % (H, A, out[-1]['pick'], 100 * c['p'], c['odds'],
                                                               ' / '.join('%.2f' % v for v in x1x2) if x1x2 else
                                                               'DraftKings (ESPN), без П1/Х/П2'), flush=True)
    return out


N_SIM = 10000


def simulate(r, M, mk, key):
    """Шаблон «10 000 симуляций»: матч разыгрывается N_SIM раз по модели счёта (Пуассон, ничьи подогнаны под лигу —
    calc.scores; итоговая победа — ничья в осн. время делится по доле побед в ОТ/Б). → dict(n, hits, curve — доля заходов
    после каждой сотни, top — 3 самых частых счёта [(хозяева, гости, раз)]) или None."""
    if not mk:
        return None
    P = calc.scores(r['lam'][0], r['lam'][1], M['rho'])
    cells = [(i, j) for i in range(calc.MAXG + 1) for j in range(calc.MAXG + 1)]
    rnd = random.Random(key)
    draw = rnd.choices(cells, weights=[P[i][j] for i, j in cells], k=N_SIM)
    hits, curve, cnt = 0, [], {}
    for n, (i, j) in enumerate(draw, 1):
        if mk['fin']:
            ok = mk['f'](dict(fh=i, fa=j)) if i != j else rnd.random() < (r['s'] if mk['fin'] == 'h' else 1 - r['s'])
        else:
            ok = mk['f'](dict(h=i, a=j))
        hits += bool(ok)
        cnt[(i, j)] = cnt.get((i, j), 0) + 1
        if n % 100 == 0:
            curve.append(round(hits / n, 4))
    top = sorted(cnt.items(), key=lambda kv: -kv[1])[:3]
    return dict(n=N_SIM, hits=hits, curve=curve, top=[(i, j, c) for (i, j), c in top])


def fact(T, H, A, mk):
    """Шаблон «Цифра дня»: как часто ставка прогноза заходила в матчах сезона у каждой из команд (хозяева — их глазами,
    гости — глазами соперника, как в «Что заходит»). → dict(team, side, k, n, games — [(заход, счёт, дома)] по порядку)
    у команды с большей долей (от 4 матчей) или None."""
    if not mk:
        return None
    best = None
    for side, t in (('h', H), ('a', A)):
        rows = []
        for x in T.get(t) or []:
            o = calc.view(x, side == 'h')
            rows.append((bool(mk['f'](o)), '%d:%d%s' % (x['gf'], x['ga'], ' ' + x['e'] if x['e'] else ''), x['home']))
        if len(rows) < 4:
            continue
        k = sum(1 for ok, *_ in rows if ok)
        cand = dict(team=t, side=side, k=k, n=len(rows), games=rows[-12:])
        if best is None or k / len(rows) > best['k'] / best['n']:
            best = cand
    return best
