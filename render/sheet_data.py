# -*- coding: utf-8 -*-
"""Данные для трейлера таблицы (владелец 19.10): листы «прогнозы», «Что заходит», «Таблица», «Elo», «Сравнение с линией»,
«Точность» — из сыгранных матчей КХЛ сезона и матчей дня (team/picks/khl_data.fetch). Модель — team/picks/calc.py
(та же методика, что у таблицы: ½ модель счёта + ½ частота команд).

build(games, nxt) → dict для render/reels/sheet_trailer.py. Прогнозы в листах «прогнозы» и «Точность» — честные: модель
на каждый день считается только по матчам ДО этого дня («зашло / не зашло» — как было бы на самом деле)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'team', 'picks'))
import calc  # noqa: E402



def _fin(r):
    return [x for x in r['rows'] if x['g'] == 'fin']


def _res3(r):
    return [x for x in r['rows'] if x['k'][:2] == ('ml', 6)]


HOME_P = 0.55          # у команды ещё нет игр в сезоне — прогноз «хозяева» (домашнее преимущество)


def rolling(G):
    """Каждый матч сезона с первого дня (владелец 19.10: «учитывать с самого начала») глазами модели «накануне»:
    [(g, p хозяев на итоговую победу)]. Первый игровой день и матчи команд без игр — прогноз «хозяева»."""
    out, cache = [], {}
    days = sorted({g['day'] for g in G})
    for d in days:
        prev = [g for g in G if g['day'] < d]
        T = calc.team_games(prev)
        if prev and d not in cache:
            cache[d] = calc.model(prev)
        M = cache.get(d)
        for g in (x for x in G if x['day'] == d):
            if M is None or not T.get(g['home']) or not T.get(g['away']):
                out.append((g, HOME_P))
                continue
            fin = _fin(calc.match(T, M, g['home'], g['away']))
            out.append((g, fin[0]['p'] / (fin[0]['p'] + fin[1]['p'])))
    return out


def elo(G, k=20.0, home=40.0):
    R, hist = {}, []
    for g in G:
        h, a = g['home'], g['away']
        rh, ra = R.get(h, 1500.0), R.get(a, 1500.0)
        e = 1 / (1 + 10 ** ((ra - rh - home) / 400))
        s = 1.0 if g['hg'] > g['ag'] else 0.0
        if g['ot']:
            s = 0.6 if s else 0.4                       # победа в ОТ/Б — не полная
        R[h], R[a] = rh + k * (s - e), ra - k * (s - e)
        hist.append((g['day'], dict(R)))
    return R, hist


WHAT = [('ПОБЕДА', lambda o: o['fh'] > o['fa']), ('ТБ 4,5', lambda o: o['h'] + o['a'] > 4.5),
        ('ТМ 5,5', lambda o: o['h'] + o['a'] < 5.5), ('ИТБ 2,5', lambda o: o['h'] > 2.5), ('Ф +1,5', lambda o: o['a'] - o['h'] <= 1)]


def build(raw, nxt=None, n_pred=8):
    G = calc.prep(raw)
    T = calc.team_games(G)
    tb = calc.table(T)
    R, hist = elo(G)
    roll = rolling(G)
    # прогнозы: последние сыгранные матчи — прогноз модели накануне и итог
    pred = []
    for g, p in [x for x in roll if x[1] != HOME_P][-n_pred:]:
        fav_home = p >= 0.5
        won_home = g['hg'] > g['ag']
        pred.append(dict(d=g['day'][8:10] + '.' + g['day'][5:7], h=g['home'], a=g['away'],
                         pick=g['home'] if fav_home else g['away'], p=round(100 * (p if fav_home else 1 - p)),
                         score='%d:%d%s' % (g['hg'], g['ag'], (' ' + g['e']) if g['e'] else ''), hit=fav_home == won_home))
    hits = sum(1 for g, p in roll if (p >= 0.5) == (g['hg'] > g['ag']))
    sure = [(g, p) for g, p in roll if max(p, 1 - p) >= 0.6]
    sure_hits = sum(1 for g, p in sure if (p >= 0.5) == (g['hg'] > g['ag']))
    acc = dict(n=len(roll), hits=hits, pct=round(100 * hits / max(1, len(roll))),
               sure_n=len(sure), sure_hits=sure_hits, sure_pct=round(100 * sure_hits / max(1, len(sure))),
               dots=[1 if (p >= 0.5) == (g['hg'] > g['ag']) else 0 for g, p in roll])
    # «Что заходит»: доля матчей сезона, где ставка зашла бы у команды (её глазами)
    what = []
    for r in tb[:9]:
        lst = T[r['t']]
        row = [round(100 * sum(1 for x in lst if f(calc.view(x, True))) / len(lst)) for _, f in WHAT]
        what.append(dict(t=r['t'], v=row, n=len(lst)))
    # таблица
    table = [dict(t=r['t'], gp=r['gp'], w=r['w'] + r['wo'], l=r['l'] + r['lo'], pts=r['pts'], gd=r['gf'] - r['ga'])
             for r in tb[:10]]
    # Elo: топ-5 на сегодня, история по дням
    top = sorted(R, key=lambda t: -R[t])[:5]
    days, seen = [], {}
    for d, snap in hist:
        seen[d] = snap
    for d in sorted(seen):
        days.append((d, [round(seen[d].get(t, 1500)) for t in top]))
    elo_ = dict(teams=top, now=[round(R[t]) for t in top], hist=days)
    # сравнение с линией: матчи дня — модель против линии (П1/Х/П2 в осн. время, без маржи)
    cmp_ = []
    M = calc.model(G)
    for x in nxt or []:
        b = x.get('bets') or {}
        try:
            k = [float(str(b.get(key)).replace(',', '.')) for key in ('team_a_win', 'draw', 'team_b_win')]
        except (TypeError, ValueError):
            continue
        if min(k) <= 1 or x['h'] not in T or x['a'] not in T:
            continue
        inv = [1 / v for v in k]
        s = sum(inv)
        line = [v / s for v in inv]
        r3 = _res3(calc.match(T, M, x['h'], x['a']))
        mp = [r3[0]['p'], r3[1]['p'], r3[2]['p']]
        sm = sum(mp)
        mp = [v / sm for v in mp]
        i = max(range(3), key=lambda j: mp[j] - line[j])
        cmp_.append(dict(h=x['h'], a=x['a'], tm=x['d'][11:16], out=('П1', 'Х', 'П2')[i], model=round(100 * mp[i]),
                         line=round(100 * line[i]), k=k[i]))
    cmp_.sort(key=lambda c: -(c['model'] - c['line']))
    return dict(pred=pred, acc=acc, what=what, what_cols=[c for c, _ in WHAT], table=table, elo=elo_, cmp=cmp_[:5],
                n_games=len(G), last_day=G[-1]['day'] if G else '')


def fake(seed=3):
    """Пробные данные для вёрстки (локально — без API КХЛ)."""
    import random
    rnd = random.Random(seed)
    teams = ['Локомотив', 'Металлург', 'Ак Барс', 'Авангард', 'Трактор', 'ЦСКА', 'СКА', 'Динамо Москва', 'Спартак',
             'Салават Юлаев', 'Северсталь', 'Торпедо', 'Автомобилист', 'Барыс', 'Сибирь', 'Амур', 'Адмирал', 'Нефтехимик',
             'Лада', 'Динамо Минск', 'Сочи', 'Шанхайские Драконы']
    st = {t: rnd.gauss(0, 0.35) for t in teams}
    raw = []
    for day in range(45):
        d = '2026-%02d-%02d' % (9 if day < 24 else 10, (day % 24) + 6 if day < 24 else day - 23)
        sh = teams[:]
        rnd.shuffle(sh)
        for i in range(0, 8, 2):
            h, a = sh[i], sh[i + 1]
            import math
            lh, la = 3.0 * math.exp(st[h] - st[a] + 0.08), 2.7 * math.exp(st[a] - st[h])

            def po(l):
                x, p, s = 0, math.exp(-l), math.exp(-l)
                u = rnd.random()
                while u > s:
                    x += 1
                    p *= l / x
                    s += p
                return x
            hg, ag = po(lh), po(la)
            e = ''
            if hg == ag:
                e = 'ОТ' if rnd.random() < 0.6 else 'Б'
                if rnd.random() < 0.5:
                    hg += 1
                else:
                    ag += 1
            raw.append(dict(d=d + ' 19:00', h=h, a=a, hg=hg, ag=ag, e=e, p=[]))
    nxt = [dict(d='2026-10-20 19:30', h='Ак Барс', a='Сибирь', bets=dict(team_a_win='2.05', draw='4.10', team_b_win='3.20')),
           dict(d='2026-10-20 17:00', h='Локомотив', a='Спартак', bets=dict(team_a_win='2.30', draw='4.00', team_b_win='2.75')),
           dict(d='2026-10-20 19:00', h='Трактор', a='Амур', bets=dict(team_a_win='1.95', draw='4.20', team_b_win='3.40')),
           dict(d='2026-10-20 12:00', h='Адмирал', a='Металлург', bets=dict(team_a_win='3.60', draw='4.30', team_b_win='1.85'))]
    return raw, nxt


if __name__ == '__main__':
    import json
    print(json.dumps(build(*fake()), ensure_ascii=False, indent=1)[:3000])
