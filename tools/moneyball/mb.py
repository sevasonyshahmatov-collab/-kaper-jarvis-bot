"""«Мани-бол» для КХЛ: какие признаки букмекер недооценивает или переоценивает.

Идея фильма (Билли Бин, «Окленд»): рынок платит за заметное (средний процент отбивания, громкие имена),
а побеждает незаметное (процент выхода на базу). У нас «рынок» — линия букмекера. Если какой-то признак
команды систематически расходится с тем, что заложено в коэффициент, — это и есть недооценка.

Для каждого матча: m — вероятность по линии (маржа снята), y — исход. Остаток y − m.
Признак «переоценён рынком», если команды с ним стабильно выступают ХУЖЕ линии (остаток < 0).
Проверка честная: открываем на одной части данных, подтверждаем на другой.
    python3 tools/moneyball/mb.py
"""
import json, math, collections, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'model_backtest'))
import bt

D = bt.D


def mk(o3):
    p1, x, p2 = (1 / o for o in o3); s = p1 + x + p2
    return p1 / s, x / s, p2 / s


def features(games):
    """Признаки команд ДО матча (с начала сезона), разность хозяева − гости."""
    st = collections.defaultdict(lambda: dict(n=0, w=0, gf=0, ga=0, otw=0, otg=0, sf=0, sa=0, sn=0, res=[], last=None, away=0, home=0))
    out = []
    for g in sorted(games, key=lambda g: g['d']):
        h, a = g['h'], g['a']
        row = dict(g=g)
        f = {}
        for side, t, opp in (('h', h, a), ('a', a, h)):
            c = st[t]
            n = c['n']
            pyth = c['gf'] ** 2 / (c['gf'] ** 2 + c['ga'] ** 2) if c['gf'] + c['ga'] else .5
            wp = c['w'] / n if n else .5
            streak = 0
            for r in reversed(c['res']):
                if streak == 0: streak = 1 if r else -1
                elif (r and streak > 0): streak += 1
                elif (not r and streak < 0): streak -= 1
                else: break
            l5 = c['res'][-5:]
            rest = None
            if c['last']:
                from datetime import date
                d0 = date.fromisoformat(c['last']); d1 = date.fromisoformat(g['d'])
                rest = (d1 - d0).days
            f[side] = dict(
                n=n,
                luck=(wp - pyth) if n >= 10 else None,                    # побед больше, чем «положено» по разнице шайб
                ot=(c['otg'] / n) if n >= 10 else None,                    # доля матчей с ОТ/буллитами
                streak=streak,
                hot=(sum(l5) / len(l5) - wp) if n >= 10 else None,          # последние 5 против сезона
                gd=((c['gf'] - c['ga']) / n) if n >= 10 else None,
                shots=((c['sf'] - c['sa']) / c['sn']) if c['sn'] >= 8 else None,
                pdo=((c['gf'] / c['sf'] if c['sf'] else 0) + (1 - (c['ga'] / c['sa'] if c['sa'] else 0))) if c['sn'] >= 8 else None,
                rest=rest,
                road=c['away'],                                              # подряд в гостях
                wp=wp if n >= 10 else None,
            )
        row['f'] = f
        out.append(row)
        # ---- после матча
        hw = g['hg'] > g['ag']
        for t, gf, ga, won, home in ((h, g['hg'], g['ag'], hw, True), (a, g['ag'], g['hg'], not hw, False)):
            c = st[t]; c['n'] += 1; c['w'] += won; c['gf'] += gf; c['ga'] += ga
            if g['ot']: c['otg'] += 1
            c['res'].append(1 if won else 0); c['last'] = g['d']
            if home: c['away'] = 0
            else: c['away'] += 1
            if 'hs' in g and g.get('hs') is not None:
                sf, sa = (g['hs'], g['as']) if home else (g['as'], g['hs'])
                c['sf'] += sf; c['sa'] += sa; c['sn'] += 1
    return out


def rows_with_market(feats):
    rs = []
    for r in feats:
        g = r['g']
        if not g.get('o3'): continue
        p1, x, p2 = mk(g['o3'])
        m = p1 + x * p1 / (p1 + p2)                    # победа с учётом ОТ
        y = 1 if g['hg'] > g['ag'] else 0
        yreg = 1 if (g['hg'] > g['ag'] and not g['ot']) else 0
        ya = 1 if (g['ag'] > g['hg'] and not g['ot']) else 0
        rs.append(dict(r, m=m, y=y, p1=p1, p2=p2, yreg=yreg, yareg=ya, o3=g['o3']))
    return rs


def test(rs, name, sig, thr):
    """sig(row) → число «за хозяев» (>0 — признак говорит, что хозяева сильнее, чем по линии).
    Возвращает: матчей, средний остаток на стороне сигнала, t, доходность ставки «на победу в основное время» стороны сигнала."""
    pts = []
    for r in rs:
        s = sig(r)
        if s is None or abs(s) < thr: continue
        side = 1 if s > 0 else -1
        resid = (r['y'] - r['m']) * side
        odds = r['o3'][0] if side > 0 else r['o3'][2]
        win = r['yreg'] if side > 0 else r['yareg']
        pts.append((resid, win * odds - 1))
    n = len(pts)
    if n < 15: return dict(name=name, n=n)
    mr = sum(p[0] for p in pts) / n
    sd = math.sqrt(sum((p[0] - mr) ** 2 for p in pts) / (n - 1))
    roi = sum(p[1] for p in pts) / n
    return dict(name=name, n=n, resid=round(mr * 100, 1), t=round(mr / (sd / math.sqrt(n)), 2), roi=round(roi * 100, 1))


def d(k, inv=False):
    def f(r):
        a, b = r['f']['h'][k], r['f']['a'][k]
        if a is None or b is None: return None
        return (b - a) if inv else (a - b)
    return f


SIGNALS = [
    # имя, функция «за хозяев», порог. inv=True — ставим ПРОТИВ команды, у которой признак выше.
    ('Против «везучих»: побед больше, чем по разнице шайб', d('luck', inv=True), 0.08),
    ('Против серии побед (ставим на соперника)', d('streak', inv=True), 3),
    ('Против «горячих»: последние 5 лучше сезона', d('hot', inv=True), 0.25),
    ('За команду с лучшей разницей шайб', d('gd'), 0.6),
    ('За команду с лучшим соотношением бросков', d('shots'), 4),
    ('Против высокого PDO (реализация + сейвы)', d('pdo', inv=True), 0.03),
    ('За отдохнувшую (разница отдыха ≥ 2 дня)', d('rest'), 2),
    ('Против долгого выезда (3+ матча подряд в гостях)', lambda r: (1 if r['f']['a']['road'] >= 3 else 0) - (1 if r['f']['h']['road'] >= 3 else 0), 1),
    ('Против частых ОТ (очки «в лотерею»)', d('ot', inv=True), 0.12),
]


def fav_longshot(rs):
    """Перекос «фаворит — андердог»: как часто сбываются исходы по ценовым корзинам."""
    b = collections.defaultdict(lambda: [0, 0.0, 0.0])
    for r in rs:
        for p, y, o in ((r['p1'], r['yreg'], r['o3'][0]), (r['p2'], r['yareg'], r['o3'][2])):
            k = min(int(p * 10), 7)
            b[k][0] += 1; b[k][1] += y - p; b[k][2] += y * o - 1
    return {'%d0–%d0%%' % (k, k + 1): (v[0], round(v[1] / v[0] * 100, 1), round(v[2] / v[0] * 100, 1)) for k, v in sorted(b.items())}


if __name__ == '__main__':
    prev = rows_with_market(features(D['prev']))
    cur = rows_with_market(features(D['cur']))
    half = len(prev) // 2
    parts = [('2025-26, 1-я половина (открытие)', prev[:half]), ('2025-26, 2-я половина (проверка)', prev[half:]),
             ('2026-27 (проверка)', cur), ('всё вместе', prev + cur)]
    for title, rs in parts:
        print('\n==', title, len(rs), 'матчей с линией')
        for name, sig, thr in SIGNALS:
            r = test(rs, name, sig, thr)
            if r['n'] < 15: print('  %-55s мало матчей (%d)' % (name, r['n'])); continue
            print('  %-55s n=%3d  остаток %+5.1f п.п.  t=%+5.2f  доходность %+6.1f%%' % (name, r['n'], r['resid'], r['t'], r['roi']))
    print('\nПерекос по цене (вероятность по линии → матчей, сбылось минус ожидалось п.п., доходность ставки):')
    for k, v in fav_longshot(prev + cur).items(): print('  ', k, v)
    hr = [r['y'] - r['m'] for r in prev + cur]
    print('\nХозяева против линии: %+.1f п.п. (%d матчей)' % (sum(hr) / len(hr) * 100, len(hr)))
