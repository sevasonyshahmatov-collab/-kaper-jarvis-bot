# -*- coding: utf-8 -*-
"""«Что заходит» по паре — повтор конструктора матча из таблицы (apps-script: betsCalcModel_, betsCalcMarkets_,
betsCalcFreq_, betsCalcMatch_) на матчах сезона из официального приложения КХЛ, плюс факты команд для доводов.

Методика как в таблице: вероятность = ½ модель счёта + ½ частота у самих команд.
  • модель: ожидаемые голы в осн. время = средний гол лиги дома/в гостях × атака команды × оборона соперника
    (сглажено к лиге на 6 матчей), счёт по Пуассону, ничьи подогнаны под реальную долю ничьих в лиге;
    итоговая победа — ничья в осн. время делится по доле побед в ОТ/Б (сглажено к 50 %);
  • частота: как часто ставка заходила у хозяев (их глазами) и у гостей (глазами соперника), домашние матчи хозяев
    и выездные гостей весят вдвое, сглажено к лиге на 6 матчей.
Удаления не считаем (нужны протоколы). Вход — out/1510/khl_games.json (khl_fetch.py, тем же заданием).
Печатает в лог: CALC (ставки пары по вероятности), TEAM / LAST / PER (факты команд), H2H, TABLE (очки).
Запуск: python team/out/2026-10-15/khl_picks_calc.py [хозяева-гости;хозяева-гости]"""
import json
import math
import sys

K, W, MAXG = 6, 0.5, 12
PAIRS = [tuple(p.split('-', 1)) for p in (sys.argv[1] if len(sys.argv) > 1 else 'Лада-СКА;Северсталь-Локомотив').split(';')]


def load(path='out/1510/khl_games.json'):
    games = []
    for g in json.load(open(path, encoding='utf-8')):
        games.append(dict(day=g['d'][:10], home=g['h'], away=g['a'], hg=g['hg'], ag=g['ag'], ot=bool(g['e']), e=g['e'], p=g.get('p') or []))
    games.sort(key=lambda g: g['day'])
    return games


def team_games(games):
    T = {}
    for g in games:
        m = min(g['hg'], g['ag'])
        rh, ra = (m, m) if g['ot'] else (g['hg'], g['ag'])
        T.setdefault(g['home'], []).append(dict(gf=g['hg'], ga=g['ag'], rf=rh, ra=ra, home=True, ot=g['ot'], e=g['e'], opp=g['away'], day=g['day'], p=g['p'], side=0))
        T.setdefault(g['away'], []).append(dict(gf=g['ag'], ga=g['hg'], rf=ra, ra=rh, home=False, ot=g['ot'], e=g['e'], opp=g['home'], day=g['day'], p=g['p'], side=1))
    return T


def pois(l, k):
    return math.exp(-l) * l ** k / math.factorial(k)


def lam(M, H, A):
    return (M['muH'] * M['att'].get(H, 1) * M['de'].get(A, 1), M['muA'] * M['att'].get(A, 1) * M['de'].get(H, 1))


def model(games):
    S, n, gh, ga, dr = {}, 0, 0, 0, 0
    for g in games:
        m = min(g['hg'], g['ag'])
        h, a = (m, m) if g['ot'] else (g['hg'], g['ag'])
        for t, f, ag_, won in ((g['home'], h, a, g['hg'] > g['ag']), (g['away'], a, h, g['ag'] > g['hg'])):
            s = S.setdefault(t, dict(n=0, f=0, a=0, otN=0, otW=0))
            s['n'] += 1
            s['f'] += f
            s['a'] += ag_
            if g['ot']:
                s['otN'] += 1
                s['otW'] += 1 if won else 0
        n += 1
        gh += h
        ga += a
        dr += 1 if h == a else 0
    M = dict(n=n, att={}, de={}, ot={}, rho=1.0, muH=gh / n, muA=ga / n)
    mu = (gh + ga) / (2 * n)
    for t, s in S.items():
        M['att'][t] = (s['f'] + K * mu) / (s['n'] + K) / mu
        M['de'][t] = (s['a'] + K * mu) / (s['n'] + K) / mu
        M['ot'][t] = (s['otW'] + 1.5) / (s['otN'] + 3)
    dp = sum(sum(pois(l[0], i) * pois(l[1], i) for i in range(MAXG + 1)) for l in (lam(M, g['home'], g['away']) for g in games)) / n
    de = dr / n
    if 0 < dp < 1 and 0 < de < 1:
        rho = de * (1 - dp) / (dp * (1 - de))
        M['rho'] = max(0.7, min(2, 1 + (rho - 1) * n / (n + 30)))
    M['draws'] = de
    return M


def scores(lh, la, rho):
    P = [[pois(lh, i) * pois(la, j) * (rho if i == j else 1) for j in range(MAXG + 1)] for i in range(MAXG + 1)]
    s = sum(map(sum, P))
    return [[x / s for x in r] for r in P]


def markets(H, A):
    out = []

    def add(g, t, f, fin=None):
        out.append(dict(g=g, t=t, f=f, fin=fin))
    add('res', 'П1 %s в осн. время' % H, lambda o: o['h'] > o['a'])
    add('res', 'Х ничья в осн. время', lambda o: o['h'] == o['a'])
    add('res', 'П2 %s в осн. время' % A, lambda o: o['a'] > o['h'])
    add('res', '1Х %s не проиграет' % H, lambda o: o['h'] >= o['a'])
    add('res', 'Х2 %s не проиграет' % A, lambda o: o['a'] >= o['h'])
    add('fin', 'итоговая победа %s' % H, lambda o: o['fh'] > o['fa'], 'h')
    add('fin', 'итоговая победа %s' % A, lambda o: o['fa'] > o['fh'], 'a')
    add('hc', 'Ф1(-1,5) %s' % H, lambda o: o['h'] - o['a'] >= 2)
    add('hc', 'Ф2(+1,5) %s' % A, lambda o: o['h'] - o['a'] <= 1)
    add('hc', 'Ф1(+1,5) %s' % H, lambda o: o['a'] - o['h'] <= 1)
    add('hc', 'Ф2(-1,5) %s' % A, lambda o: o['a'] - o['h'] >= 2)
    add('hc', 'Ф1(+2,5) %s' % H, lambda o: o['a'] - o['h'] <= 2)
    add('hc', 'Ф2(+2,5) %s' % A, lambda o: o['h'] - o['a'] <= 2)
    for x in (4.5, 5.5, 6.5):
        add('tot', 'ТБ ' + str(x).replace('.', ','), lambda o, x=x: o['h'] + o['a'] > x)
        add('tot', 'ТМ ' + str(x).replace('.', ','), lambda o, x=x: o['h'] + o['a'] < x)
    for nm, k in ((H, 'h'), (A, 'a')):
        add('it' + k, 'ИТБ 1,5 %s' % nm, lambda o, k=k: o[k] > 1.5)
        add('it' + k, 'ИТБ 2,5 %s' % nm, lambda o, k=k: o[k] > 2.5)
        add('it' + k, 'ИТМ 2,5 %s' % nm, lambda o, k=k: o[k] < 2.5)
        add('it' + k, 'ИТБ 3,5 %s' % nm, lambda o, k=k: o[k] > 3.5)
    return out


def view(x, home):
    return dict(h=x['rf'], a=x['ra'], fh=x['gf'], fa=x['ga']) if home else dict(h=x['ra'], a=x['rf'], fh=x['ga'], fa=x['gf'])


def freq(lst, home, f, lg):
    s = w = 0
    for x in lst or []:
        k = 2 if x['home'] == home else 1
        w += k
        s += k if f(view(x, home)) else 0
    return (s + K * lg) / (w + K) if w else None


def match(games, T, M, H, A):
    lh, la = lam(M, H, A)
    P = scores(lh, la, M['rho'])
    s = max(0.3, min(0.7, (M['ot'].get(H, 0.5) + 1 - M['ot'].get(A, 0.5)) / 2))
    home_recs = [view(x, True) for t in T for x in T[t] if x['home']]
    rows = []
    for mk in markets(H, A):
        lg = sum(1 for o in home_recs if mk['f'](o)) / len(home_recs)
        pm = 0.0
        for i in range(MAXG + 1):
            for j in range(MAXG + 1):
                if mk['fin']:
                    if i != j:
                        pm += P[i][j] if mk['f'](dict(fh=i, fa=j)) else 0
                    else:
                        pm += P[i][j] * (s if mk['fin'] == 'h' else 1 - s)
                elif mk['f'](dict(h=i, a=j)):
                    pm += P[i][j]
        eh, ea = freq(T.get(H), True, mk['f'], lg), freq(T.get(A), False, mk['f'], lg)
        pe = ea if eh is None else eh if ea is None else (eh + ea) / 2
        rows.append(dict(g=mk['g'], t=mk['t'], p=W * pm + (1 - W) * pe, pm=pm, pe=pe, lg=lg))
    bi = max(((i, j) for i in range(MAXG + 1) for j in range(MAXG + 1)), key=lambda ij: P[ij[0]][ij[1]])
    return dict(lam=(lh, la), s=s, rows=rows, score=(bi[0], bi[1], P[bi[0]][bi[1]]))


def res(x):
    if x['gf'] > x['ga']:
        return 'В' + (x['e'] or '')
    return 'П' + (x['e'] or '')


def table(T):
    rows = []
    for t, lst in T.items():
        w = sum(1 for x in lst if x['gf'] > x['ga'] and not x['ot'])
        wo = sum(1 for x in lst if x['gf'] > x['ga'] and x['ot'])
        lo = sum(1 for x in lst if x['gf'] < x['ga'] and x['ot'])
        l_ = sum(1 for x in lst if x['gf'] < x['ga'] and not x['ot'])
        rows.append(dict(t=t, gp=len(lst), w=w, wo=wo, lo=lo, l=l_, pts=2 * (w + wo) + lo,
                         gf=sum(x['gf'] for x in lst), ga=sum(x['ga'] for x in lst)))
    rows.sort(key=lambda r: (-r['pts'], r['gp'], -(r['w'] + r['wo'])))
    return rows


def team_report(T, tb, t):
    lst = T[t]
    r = next(x for x in tb if x['t'] == t)
    place = tb.index(r) + 1
    hm = [x for x in lst if x['home']]
    aw = [x for x in lst if not x['home']]

    def split(z):
        if not z:
            return '0'
        return '%d игр %d-%d (В-П), голы %d:%d, %.2f:%.2f за игру' % (
            len(z), sum(1 for x in z if x['gf'] > x['ga']), sum(1 for x in z if x['gf'] < x['ga']),
            sum(x['gf'] for x in z), sum(x['ga'] for x in z), sum(x['gf'] for x in z) / len(z), sum(x['ga'] for x in z) / len(z))
    streak, k = None, 0
    for x in reversed(lst):
        v = 'В' if x['gf'] > x['ga'] else 'П'
        if streak in (None, v):
            streak, k = v, k + 1
        else:
            break
    print('TEAM %s | место %d из %d по очкам | %d игр, очки %d (В %d, ВО %d, ПО %d, П %d), шайбы %d:%d (%.2f:%.2f) | серия %s%d | ОТ/Б матчей %d'
          % (t, place, len(tb), r['gp'], r['pts'], r['w'], r['wo'], r['lo'], r['l'], r['gf'], r['ga'], r['gf'] / r['gp'], r['ga'] / r['gp'],
             streak, k, sum(1 for x in lst if x['ot'])), flush=True)
    print('TEAM %s | дома: %s | в гостях: %s' % (t, split(hm), split(aw)), flush=True)
    rf = sum(x['rf'] for x in lst) / len(lst)
    ra = sum(x['ra'] for x in lst) / len(lst)
    tot = [x['rf'] + x['ra'] for x in lst]
    print('TEAM %s | осн. время: забивает %.2f, пропускает %.2f, тотал матча %.2f; ТМ 5,5 в %d из %d, ТБ 4,5 в %d из %d, сухих побед %d, всухую проиграл %d'
          % (t, rf, ra, sum(tot) / len(tot), sum(1 for v in tot if v < 5.5), len(tot), sum(1 for v in tot if v > 4.5), len(tot),
             sum(1 for x in lst if x['ga'] == 0), sum(1 for x in lst if x['gf'] == 0)), flush=True)
    per = [[0, 0], [0, 0], [0, 0]]
    for x in lst:
        for i, sc in enumerate((x['p'] or [])[:3]):
            if not sc or ':' not in sc:
                continue
            a, b = (int(v) for v in sc.split(':'))
            f, g_ = (a, b) if x['side'] == 0 else (b, a)
            per[i][0] += f
            per[i][1] += g_
    print('PER %s | по периодам (забито:пропущено): 1-й %d:%d, 2-й %d:%d, 3-й %d:%d' % (t, *per[0], *per[1], *per[2]), flush=True)
    print('LAST %s | %s' % (t, ' · '.join('%s %s %s %d:%d %s' % (x['day'][8:10] + '.' + x['day'][5:7], 'дома' if x['home'] else 'в гостях',
                                                                   x['opp'], x['gf'], x['ga'], res(x)) for x in lst[-6:])), flush=True)


if __name__ == '__main__':
    games = load()
    T = team_games(games)
    M = model(games)
    tb = table(T)
    print('LEAGUE матчей %d (%s … %s), голов в осн. время дома %.2f / в гостях %.2f, ничьих в осн. время %.1f%%, rho %.2f'
          % (M['n'], games[0]['day'], games[-1]['day'], M['muH'], M['muA'], 100 * M['draws'], M['rho']), flush=True)
    print('TABLE ' + ' · '.join('%d.%s %d (%d)' % (i + 1, r['t'], r['pts'], r['gp']) for i, r in enumerate(tb)), flush=True)
    for H, A in PAIRS:
        r = match(games, T, M, H, A)
        print('PAIR %s — %s | λ %.2f : %.2f | самый вероятный счёт осн. времени %d:%d (%.1f%%) | доля ОТ хозяев s=%.2f'
              % (H, A, r['lam'][0], r['lam'][1], r['score'][0], r['score'][1], 100 * r['score'][2], r['s']), flush=True)
        for x in sorted(r['rows'], key=lambda x: -x['p']):
            best = ' *' if 0.55 <= x['p'] <= 0.85 and x['p'] - x['lg'] >= 0.05 else ''
            print('CALC %s—%s | %-30s %5.1f%% | честный %5.2f | модель %5.1f%% | частота %5.1f%% | лига %5.1f%%%s'
                  % (H, A, x['t'], 100 * x['p'], 1 / x['p'], 100 * x['pm'], 100 * x['pe'], 100 * x['lg'], best), flush=True)
        for t in (H, A):
            team_report(T, tb, t)
        h2h = [g for g in games if {g['home'], g['away']} == {H, A}]
        print('H2H %s — %s | %s' % (H, A, ' · '.join('%s %s %d:%d %s%s' % (g['day'][8:10] + '.' + g['day'][5:7], g['home'], g['hg'], g['ag'],
                                                                             g['away'], ' ' + g['e'] if g['e'] else '') for g in h2h) or 'в этом сезоне не играли'),
              flush=True)
