"""Бэктест модели КХЛ: точная копия Elo из таблицы (computeAndWriteElo_ + формула «Шансы хозяев») с параметрами."""
import json, math, collections
D = json.load(open(__file__.rsplit('/',1)[0] + '/data.json'))

BASE = dict(K=20, ot=0.75, mov=True, boost=0, bgames=15, fw=8, fscale=20, fcap=8, fon=1.0,
            S=90, H=6, shrink=1.0, clip=(0.08, 0.92),
            # процесс (броски): proc — вес силы по броскам, luck — вес поправки за везение (PDO), n0 — усадка по числу игр
            proc=0.0, luck=0.0, n0=8, gpp=33.0, procwin=0, carry=None)

def market_p(o3):
    p1, x, p2 = (1/o for o in o3); s = p1 + x + p2
    p1, x, p2 = p1/s, x/s, p2/s
    return p1 + x * (p1 / (p1 + p2))          # победа с учётом ОТ: ничью делим пропорционально силе

def run(games, start, P, eval_from=0, collect=False):
    P = dict(BASE, **P)
    elo = {t: 1500 + (P['shrink'] * (r - 50)) * 6 for t, r in start.items()}
    gp = collections.Counter(); form = collections.defaultdict(list)
    st = collections.defaultdict(lambda: collections.Counter())     # броски/голы по ходу сезона
    lg = collections.Counter()
    out = []
    for i, g in enumerate(games):
        h, a = g['h'], g['a']
        if h not in elo: elo[h] = 1500
        if a not in elo: elo[a] = 1500
        # ---- прогноз ДО матча
        Th, Ta = 50 + (elo[h] - 1500) / 6, 50 + (elo[a] - 1500) / 6
        def fadj(t):
            d = form[t]
            if not d: return 0
            w = sum(range(1, len(d) + 1)); x = sum((k + 1) * v for k, v in enumerate(d)) / w
            return max(-P['fcap'], min(P['fcap'], x * P['fscale']))
        def padj(t):
            c = st[t]; n = c['n']
            if not n or not lg['sf']: return 0
            lsh = lg['g'] / lg['sf']
            xgd = (c['sf'] - c['sa']) / n * lsh                     # ожидаемая разница шайб за игру по броскам
            gd = (c['gf'] - c['ga']) / n
            shr = n / (n + P['n0'])
            return shr * P['gpp'] * (P['proc'] * xgd - P['luck'] * (gd - xgd))
        diff = Th + P['H'] + P['fon'] * (fadj(h) - fadj(a)) + padj(h) - padj(a) - Ta
        p = 1 / (1 + 10 ** (-diff / P['S']))
        p = max(P['clip'][0], min(P['clip'][1], p))
        y = 1 if g['hg'] > g['ag'] else 0
        if i >= eval_from:
            rec = dict(p=p, y=y, g=g)
            if 'o3' in g: rec['m'] = market_p(g['o3'])
            out.append(rec)
        # ---- обновление после матча
        eh, ea = elo[h], elo[a]
        exp = 1 / (1 + 10 ** ((ea - eh) / 400))
        won = g['hg'] > g['ag']
        act = (P['ot'] if won else 1 - P['ot']) if g['ot'] else (1 if won else 0)
        f = 1
        if P['mov'] and not g['ot']:
            gd = abs(g['hg'] - g['ag']); ed = (eh - ea) if won else (ea - eh)
            f = (math.log(gd) + 1) * 2.2 / (ed * 0.001 + 2.2)
        kh = P['K'] * (1 + P['boost'] * max(0, 1 - gp[h] / P['bgames'])) * f
        ka = P['K'] * (1 + P['boost'] * max(0, 1 - gp[a] / P['bgames'])) * f
        elo[h] = eh + kh * (act - exp); elo[a] = ea + ka * ((1 - act) - (1 - exp))
        gp[h] += 1; gp[a] += 1
        dlt = act - exp
        form[h].append(dlt); form[a].append(-dlt)
        form[h] = form[h][-P['fw']:]; form[a] = form[a][-P['fw']:]
        if 'hs' in g:
            for t, sf, sa, gf, ga in ((h, g['hs'], g['as'], g['hg'], g['ag']), (a, g['as'], g['hs'], g['ag'], g['hg'])):
                c = st[t]; c['n'] += 1; c['sf'] += sf; c['sa'] += sa; c['gf'] += gf; c['ga'] += ga
            lg['sf'] += g['hs'] + g['as']; lg['g'] += g['hg'] + g['ag']
    return (out, elo) if collect else out

def score(out, key='p'):
    rs = [r for r in out if key in r]
    if not rs: return None
    n = len(rs)
    br = sum((r[key] - r['y']) ** 2 for r in rs) / n
    ll = -sum(math.log(r[key] if r['y'] else 1 - r[key]) for r in rs) / n
    acc = sum((r[key] > .5) == (r['y'] == 1) for r in rs) / n
    return dict(n=n, brier=round(br, 4), logloss=round(ll, 4), acc=round(acc, 3))

def cal(out, key='p'):
    b = collections.defaultdict(lambda: [0, 0, 0.0])
    for r in out:
        q = max(r[key], 1 - r[key]); won = (r[key] > .5) == (r['y'] == 1)
        k = min(9, int(q * 10)); b[k][0] += 1; b[k][1] += won; b[k][2] += q
    return {'%d0-%d0%%' % (k, k + 1): (v[0], round(v[1] / v[0], 3), round(v[2] / v[0], 3)) for k, v in sorted(b.items())}
