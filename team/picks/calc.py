# -*- coding: utf-8 -*-
"""«Что заходит» по паре — повтор конструктора матча из таблиц КХЛ и НХЛ (apps-script: betsCalcModel_, betsCalcMarkets_,
betsCalcFreq_, betsCalcMatch_ — код у таблиц одинаковый), плюс факты команд для доводов и кэфы к каждой ставке.

Методика как в таблице: вероятность = ½ модель счёта + ½ частота у самих команд.
  • модель: ожидаемые голы в осн. время = средний гол лиги дома/в гостях × атака команды × оборона соперника
    (сглажено к лиге на 6 матчей), счёт по Пуассону, ничьи подогнаны под реальную долю ничьих в лиге;
    итоговая победа — ничья в осн. время делится по доле побед в ОТ/Б (сглажено к 50 %);
  • частота: как часто ставка заходила у хозяев (их глазами) и у гостей (глазами соперника), домашние матчи хозяев
    и выездные гостей весят вдвое, сглажено к лиге на 6 матчей.
Удаления не считаем (нужны протоколы).

Вход — матчи сезона [{d: 'YYYY-MM-DD HH:MM' (МСК), h, a, hg, ag, e: ''|'ОТ'|'Б', p: ['1:0', '0:2', '1:1', …]}].
Печатает в лог: LEAGUE, TABLE, PAIR, CALC (все ставки пары по вероятности), TEAM / PER / LAST (факты команд), H2H,
BRIEF (ставки с кэфом: вероятность, кэф, «ВЫБОР» — самая вероятная с кэфом от 1,6, «ВАРИАНТ» — чуть менее вероятная
с кэфом заметно выше), PICKJSON (то же одной строкой для team/picks/parse_log.py).
Запускается из team/picks/day.py; отдельно: python team/picks/calc.py games.json 'Хозяева|Гости;…'"""
import json
from datetime import datetime, timezone
import math
import os
import sys

K, W, MAXG = 6, 0.5, 12
MIN_ODDS = 1.6          # владелец 15.10: самая вероятная ставка с кэфом от 1,6
MIN_P = (0.5, 0.45)     # выбор — среди ставок от 50 % (нет таких — от 45 %, «ВЫБОР?»); ниже — не «самая вероятная», решает сессия
NHL_P = (0.60, 0.65)    # владелец 29.10: НХЛ — инд. тотал и фора +1,5 от 60 %, остальное от 65 % (nhl_floor)
ALT_P, ALT_K = 0.06, 0.15   # «чуть менее вероятная, но кэф выше»: до 6 п. п. ниже по вероятности и кэф выше на 0,15+
# Владелец 22.10: «нужна модель, которая выдаёт наиболее точные вероятные прогнозы». Разбор предложений 15–21.10: модель
# обещала ~62 %, заходило ~50 % (тоталы 45 % при 62 %, фора +1,5 — 56 % при 67 %). До большой подгонки на истории —
# вероятность модели наполовину сдвигаем к вероятности из линии (кэф без маржи ~4 %): «самая вероятная» выбирается по ней.
W_MKT, MARGIN_EST = 0.5, 1.04
# Поправка вероятности модели по виду ставки и лиге (team/picks/backtest.py: 2025/26 + этот сезон, ~7000 ставок на лигу):
# logit(p') = a + b·logit(p). LEAGUE ставят day.py и шортсы ('KHL' | 'NHL'); нет — без поправки.
LEAGUE = None
# Новый рейтинг НХЛ (владелец 29.10; team/picks/nhl_live.py ставит из day.py): {(хозяева, гости): {lh, la, s, info}} —
# ожидаемые голы с формой по xG, вратарём-стартером и усталостью; вес модели против частоты NHL_WN, поправка — calib.json «NHL2».
# Пусто (не посчиталось) — всё по-старому.
NHL_NEW = {}
NHL_WN = 0.8
try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calib.json'), encoding='utf-8') as _f:
        CALIB = json.load(_f)
except (OSError, ValueError):
    CALIB = {}


def key_of(k):
    """Вид ставки без стороны: ('ml',6,'draw') → 'ничья осн.', ('sp',6,'away',1.5) → 'фора +1.5' …"""
    t = k[0]
    if t == 'ml':
        return 'итоговая победа' if k[1] == 0 else ('ничья осн.' if k[2] == 'draw' else 'победа осн.')
    if t == 'sp':
        return 'не проиграет осн.' if abs(k[3]) == 0.5 else 'фора %+g' % k[3]
    if t == 'tot':
        return 'тотал %s %g' % ('больше' if k[2] == 'over' else 'меньше', k[3])
    if t == 'tt':
        return 'инд. тотал %s %g' % ('больше' if k[3] == 'over' else 'меньше', k[4])
    return str(k)


def calibrate(k, p):
    lg = str(LEAGUE or '').upper()
    ab = (CALIB.get(lg + '2' if NHL_NEW else lg) or {}).get(key_of(k))      # новый рейтинг — своя поправка (NHL2 / KHL2)
    if not ab:
        return p
    x = math.log(max(1e-6, min(1 - 1e-6, p)) / (1 - max(1e-6, min(1 - 1e-6, p))))
    return 1 / (1 + math.exp(-(ab[0] + ab[1] * x)))


def p_adj(p, odds):
    return (1 - W_MKT) * p + W_MKT / (odds * MARGIN_EST) if odds else p


def out(tag, text):
    print(tag + ' ' + text, flush=True)


def prep(raw):
    games = []
    for g in raw:
        games.append(dict(day=g['d'][:10], home=g['h'], away=g['a'], hg=g['hg'], ag=g['ag'], ot=bool(g['e']), e=g['e'],
                          p=g.get('p') or []))
    games.sort(key=lambda g: g['day'])
    return games


def team_games(games):
    T = {}
    for g in games:
        m = min(g['hg'], g['ag'])
        rh, ra = (m, m) if g['ot'] else (g['hg'], g['ag'])
        T.setdefault(g['home'], []).append(dict(gf=g['hg'], ga=g['ag'], rf=rh, ra=ra, home=True, ot=g['ot'], e=g['e'],
                                                opp=g['away'], day=g['day'], p=g['p'], side=0))
        T.setdefault(g['away'], []).append(dict(gf=g['ag'], ga=g['hg'], rf=ra, ra=rh, home=False, ot=g['ot'], e=g['e'],
                                                opp=g['home'], day=g['day'], p=g['p'], side=1))
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
    """Ставки как в конструкторе таблицы; k — где искать кэф у Pinnacle: (тип, период, сторона, линия)."""
    out_ = []

    def add(g, t, f, k, fin=None):
        out_.append(dict(g=g, t=t, f=f, k=k, fin=fin))
    add('res', 'П1 %s в осн. время' % H, lambda o: o['h'] > o['a'], ('ml', 6, 'home'))
    add('res', 'Х ничья в осн. время', lambda o: o['h'] == o['a'], ('ml', 6, 'draw'))
    add('res', 'П2 %s в осн. время' % A, lambda o: o['a'] > o['h'], ('ml', 6, 'away'))
    add('res', '1Х %s не проиграет в осн. время' % H, lambda o: o['h'] >= o['a'], ('sp', 6, 'home', 0.5))
    add('res', 'Х2 %s не проиграет в осн. время' % A, lambda o: o['a'] >= o['h'], ('sp', 6, 'away', 0.5))
    add('fin', 'итоговая победа %s (с ОТ и Б)' % H, lambda o: o['fh'] > o['fa'], ('ml', 0, 'home'), 'h')
    add('fin', 'итоговая победа %s (с ОТ и Б)' % A, lambda o: o['fa'] > o['fh'], ('ml', 0, 'away'), 'a')
    add('hc', 'Ф1(-1,5) %s' % H, lambda o: o['h'] - o['a'] >= 2, ('sp', 6, 'home', -1.5))
    add('hc', 'Ф2(+1,5) %s' % A, lambda o: o['h'] - o['a'] <= 1, ('sp', 6, 'away', 1.5))
    add('hc', 'Ф1(+1,5) %s' % H, lambda o: o['a'] - o['h'] <= 1, ('sp', 6, 'home', 1.5))
    add('hc', 'Ф2(-1,5) %s' % A, lambda o: o['a'] - o['h'] >= 2, ('sp', 6, 'away', -1.5))
    add('hc', 'Ф1(+2,5) %s' % H, lambda o: o['a'] - o['h'] <= 2, ('sp', 6, 'home', 2.5))
    add('hc', 'Ф2(+2,5) %s' % A, lambda o: o['h'] - o['a'] <= 2, ('sp', 6, 'away', 2.5))
    for x in (4.5, 5.5, 6.5):
        add('tot', 'ТБ ' + str(x).replace('.', ',') + ' в осн. время', lambda o, x=x: o['h'] + o['a'] > x, ('tot', 6, 'over', x))
        add('tot', 'ТМ ' + str(x).replace('.', ',') + ' в осн. время', lambda o, x=x: o['h'] + o['a'] < x, ('tot', 6, 'under', x))
    for nm, k, side in ((H, 'h', 'home'), (A, 'a', 'away')):
        add('it' + k, 'ИТБ 1,5 %s в осн. время' % nm, lambda o, k=k: o[k] > 1.5, ('tt', 6, side, 'over', 1.5))
        add('it' + k, 'ИТБ 2,5 %s в осн. время' % nm, lambda o, k=k: o[k] > 2.5, ('tt', 6, side, 'over', 2.5))
        add('it' + k, 'ИТМ 2,5 %s в осн. время' % nm, lambda o, k=k: o[k] < 2.5, ('tt', 6, side, 'under', 2.5))
        add('it' + k, 'ИТБ 3,5 %s в осн. время' % nm, lambda o, k=k: o[k] > 3.5, ('tt', 6, side, 'over', 3.5))
    return out_


def view(x, home):
    return dict(h=x['rf'], a=x['ra'], fh=x['gf'], fa=x['ga']) if home else dict(h=x['ra'], a=x['rf'], fh=x['ga'], fa=x['gf'])


def freq(lst, home, f, lg):
    s = w = 0
    for x in lst or []:
        k = 2 if x['home'] == home else 1
        w += k
        s += k if f(view(x, home)) else 0
    return (s + K * lg) / (w + K) if w else None


def match(T, M, H, A, new=None):
    """new — {lh, la, s} нового рейтинга НХЛ (NHL_NEW): ожидаемые голы и доля ОТ оттуда, вес модели NHL_WN."""
    lh, la = (new['lh'], new['la']) if new else lam(M, H, A)
    w = NHL_WN if new else W
    P = scores(lh, la, M['rho'])
    s = new['s'] if new else max(0.3, min(0.7, (M['ot'].get(H, 0.5) + 1 - M['ot'].get(A, 0.5)) / 2))
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
        rows.append(dict(g=mk['g'], t=mk['t'], k=mk['k'], p=w * pm + (1 - w) * pe, pm=pm, pe=pe, lg=lg))
    bi = max(((i, j) for i in range(MAXG + 1) for j in range(MAXG + 1)), key=lambda ij: P[ij[0]][ij[1]])
    return dict(lam=(lh, la), s=s, rows=rows, score=(bi[0], bi[1], P[bi[0]][bi[1]]))


# ---------- кэфы к ставкам ----------

def _same_total_with_ot(x):
    """Тотал с ОТ совпадает с тоталом основного времени, если ничья в осн. время (чётный тотал 2k → 2k+1 с ОТ)
    не перескакивает линию: 5,5 и 3,5 — да, 4,5 и 6,5 — нет."""
    return int(x - 0.5) % 2 == 1


def odds_for(k, mks):
    """Кэф Pinnacle (десятичный) к ставке по ключу k из markets(); mks — рынки матча из pin.py. → (кэф, откуда) | (None, '')."""
    def find(typ, period, pred):
        for m in mks or []:
            if m['type'] != typ or m['period'] != period:
                continue
            for p in m['prices']:
                if pred(m, p):
                    return p['price']
        return None
    kind = k[0]
    if kind == 'ml':
        v = find('moneyline', k[1], lambda m, p: p['designation'] == k[2])
        if v is None and k[1] == 6 and k[2] != 'draw':      # П1/П2 в осн. время = фора −0,5 в осн. время
            v = find('spread', 6, lambda m, p: p['designation'] == k[2] and p.get('points') == -0.5)
        return (v, 'осн. время' if k[1] == 6 else 'с ОТ и Б') if v else (None, '')
    if kind == 'sp':
        for period in (6, 0):                                # фора ±1,5 / +2,5 с ОТ = та же, что в осн. время (в ОТ разница 1)
            if period == 0 and abs(k[3]) < 1:
                continue                                     # ±0,5 с ОТ — это уже не двойной шанс
            v = find('spread', period, lambda m, p: p['designation'] == k[2] and p.get('points') == k[3])
            if v:
                return v, 'осн. время' if period == 6 else 'с ОТ = осн. время на этой линии'
        return None, ''
    if kind == 'tot':
        v = find('total', 6, lambda m, p: p['designation'] == k[2] and p.get('points') == k[3])
        if v:
            return v, 'осн. время'
        if _same_total_with_ot(k[3]):
            v = find('total', 0, lambda m, p: p['designation'] == k[2] and p.get('points') == k[3])
            if v:
                return v, 'с ОТ = осн. время на этой линии'
        return None, ''
    if kind == 'tt':
        v = find('team_total', 6, lambda m, p: m.get('side') == k[2] and p['designation'] == k[3] and p.get('points') == k[4])
        return (v, 'осн. время') if v else (None, '')
    return None, ''


def fonbet_for(k, fon):
    """Фонбет П1/Х/П2 в осн. время из приложения КХЛ (поле bets)."""
    if not fon or k[0] != 'ml' or k[1] != 6:
        return None
    key = {'home': 'team_a_win', 'draw': 'draw', 'away': 'team_b_win'}[k[2]]
    try:
        v = float(str(fon.get(key)).replace(',', '.'))
        return v if v > 1 else None
    except (TypeError, ValueError):
        return None


LINES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.lines', 'lines.jsonl')


def log_lines(H, A, info, rows):
    """Линия и вероятности модели к каждому матчу — для подбора доли линии W_MKT (владелец 22.10). Файл живёт в кэше
    Actions (itogi.yml, .lines); итог матча подставит разбор позже по дате и командам."""
    rec = dict(t=datetime.now(timezone.utc).isoformat()[:16], league=LEAGUE, d=info.get('d'), h=H, a=A,
               rows=[dict(k=key_of(x['k']) if x.get('k') else x['t'], t=x['t'], pm=x['p_model'], pc=x['p_cal'], o=x['odds'])
                     for x in rows if x.get('odds')])
    try:
        os.makedirs(os.path.dirname(LINES), exist_ok=True)
        with open(LINES, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False, separators=(',', ':')) + '\n')
    except OSError as e:
        print('LINESERR %r' % e, flush=True)


def nhl_floor(x):
    """Порог вероятности для НХЛ (владелец 29.10, заходимость 15–29.10): инд. тоталы 16/22 и фора +1,5 12/19 — от 60 %;
    «не проиграет» 10/21, тоталы 7/18, победы 3/11 — от 65 %. Нет ставки выше порога — матч без прогноза."""
    key = key_of(x['k']) if x.get('k') else ''
    return NHL_P[0] if key.startswith('инд. тотал') or key == 'фора +1.5' else NHL_P[1]


def brief(H, A, r, mks, fon):
    """Ставки с кэфом по убыванию вероятности + выбор по правилу владельца."""
    rows = []
    for x in r['rows']:
        v, src = odds_for(x['k'], mks)
        fb = fonbet_for(x['k'], fon)
        k = v or fb
        rows.append(dict(t=x['t'], g=x['g'], k=x['k'], p=round(p_adj(calibrate(x['k'], x['p']), k), 4), p_model=round(x['p'], 4),
                         p_cal=round(calibrate(x['k'], x['p']), 4), pm=round(x['pm'], 4),
                         pe=round(x['pe'], 4), lg=round(x['lg'], 4), pin=v, fon=fb, odds=k,
                         src=src if v else ('Фонбет, осн. время' if fb else '')))
    rows.sort(key=lambda x: -x['p'])
    pick = None
    floors = MIN_P
    if str(LEAGUE or '').upper() == 'NHL':      # владелец 29.10: НХЛ — только уверенные ставки (разбор 15–29.10)
        floors = (None,)
    for floor, mark in zip(floors, ('ВЫБОР', 'ВЫБОР?')):
        ok = [x for x in rows if x['odds'] and x['odds'] >= MIN_ODDS and x['p'] >= (floor or nhl_floor(x))]
        if ok:
            pick = ok[0]
            pick['mark'] = mark
            break
    if pick:
        for x in ok[1:]:
            if x['p'] >= pick['p'] - ALT_P and x['odds'] >= pick['odds'] + ALT_K:
                x['mark'] = 'ВАРИАНТ'
    return rows, pick


# ---------- факты ----------

def res(x):
    return ('В' if x['gf'] > x['ga'] else 'П') + (x['e'] or '')


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
    lst = T.get(t) or []
    if not lst:
        out('TEAM', '%s | в этом сезоне матчей нет' % t)
        return
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
    out('TEAM', '%s | место %d из %d по очкам (2 за победу, 1 за поражение в ОТ/Б) | %d игр, очки %d (В %d, ВО %d, ПО %d, П %d), '
        'шайбы %d:%d (%.2f:%.2f) | серия %s%d | матчей с ОТ/Б %d'
        % (t, place, len(tb), r['gp'], r['pts'], r['w'], r['wo'], r['lo'], r['l'], r['gf'], r['ga'], r['gf'] / r['gp'], r['ga'] / r['gp'],
           streak, k, sum(1 for x in lst if x['ot'])))
    out('TEAM', '%s | дома: %s | в гостях: %s' % (t, split(hm), split(aw)))
    rf = sum(x['rf'] for x in lst) / len(lst)
    ra = sum(x['ra'] for x in lst) / len(lst)
    tot = [x['rf'] + x['ra'] for x in lst]
    out('TEAM', '%s | осн. время: забивает %.2f, пропускает %.2f, тотал матча %.2f; ТМ 5,5 в %d из %d, ТБ 4,5 в %d из %d, '
        'сухих побед %d, всухую проиграл %d'
        % (t, rf, ra, sum(tot) / len(tot), sum(1 for v in tot if v < 5.5), len(tot), sum(1 for v in tot if v > 4.5), len(tot),
           sum(1 for x in lst if x['ga'] == 0), sum(1 for x in lst if x['gf'] == 0)))
    per = [[0, 0], [0, 0], [0, 0]]
    for x in lst:
        for i, sc in enumerate((x['p'] or [])[:3]):
            if not sc or ':' not in sc:
                continue
            a, b = (int(v) for v in sc.split(':'))
            f, g_ = (a, b) if x['side'] == 0 else (b, a)
            per[i][0] += f
            per[i][1] += g_
    out('PER', '%s | по периодам (забито:пропущено): 1-й %d:%d, 2-й %d:%d, 3-й %d:%d' % (t, *per[0], *per[1], *per[2]))
    out('LAST', '%s | %s' % (t, ' · '.join('%s %s %s %d:%d %s' % (x['day'][8:10] + '.' + x['day'][5:7], 'дома' if x['home'] else 'в гостях',
                                                              x['opp'], x['gf'], x['ga'], res(x)) for x in lst[-6:])))


def run(raw_games, pairs, pins=None, fonbet=None, meta=None):
    """pairs — [(хозяева, гости)]; pins — {(хозяева, гости): рынки Pinnacle}; fonbet — {(хозяева, гости): bets}; meta — {(х, г): {...}}."""
    games = prep(raw_games)
    if not games:
        out('LEAGUE', 'нет сыгранных матчей — расчёт невозможен')
        return
    T = team_games(games)
    M = model(games)
    tb = table(T)
    out('LEAGUE', 'матчей %d (%s … %s), голов в осн. время дома %.2f / в гостях %.2f, ничьих в осн. время %.1f%%, rho %.2f'
        % (M['n'], games[0]['day'], games[-1]['day'], M['muH'], M['muA'], 100 * M['draws'], M['rho']))
    out('TABLE', ' · '.join('%d.%s %d (%d)' % (i + 1, r['t'], r['pts'], r['gp']) for i, r in enumerate(tb)))
    for H, A in pairs:
        if H not in T or A not in T:
            out('PAIR', '%s — %s | у одной из команд нет матчей в сезоне — расчёта нет' % (H, A))
            continue
        new = NHL_NEW.get((H, A))
        r = match(T, M, H, A, new)
        mks = (pins or {}).get((H, A))
        fon = (fonbet or {}).get((H, A))
        out('PAIR', '%s — %s | λ %.2f : %.2f | самый вероятный счёт осн. времени %d:%d (%.1f%%) | доля ОТ хозяев s=%.2f | линия Pinnacle: %s%s'
            % (H, A, r['lam'][0], r['lam'][1], r['score'][0], r['score'][1], 100 * r['score'][2], r['s'], 'есть' if mks else 'НЕТ',
               ' | новый рейтинг' if new else ''))
        for x in sorted(r['rows'], key=lambda x: -x['p']):
            out('CALC', '%s—%s | %-40s %5.1f%% | честный %5.2f | модель %5.1f%% | частота %5.1f%% | лига %5.1f%%'
                % (H, A, x['t'], 100 * x['p'], 1 / x['p'], 100 * x['pm'], 100 * x['pe'], 100 * x['lg']))
        rows, pick = brief(H, A, r, mks, fon)
        log_lines(H, A, (meta or {}).get((H, A)) or {}, rows)
        for x in rows:
            if not x['odds']:
                continue
            out('BRIEF', '%s—%s | %5.1f%% (модель %4.1f%%) %-40s | кэф %.2f (%s)%s | p×k %.2f%s'
                % (H, A, 100 * x['p'], 100 * x['p_model'], x['t'], x['odds'], x['src'],
                   ', Фонбет %.2f' % x['fon'] if x['fon'] and x['pin'] else '', x['p'] * x['odds'],
                   ' | ' + x['mark'] if x.get('mark') else ''))
        if not pick:
            out('BRIEF', '%s—%s | нет ставки от 45 %% с кэфом от %.1f — выбрать самому (самая вероятная с кэфом) или честно пропустить матч'
                % (H, A, MIN_ODDS))
        for t in (H, A):
            team_report(T, tb, t)
        h2h = [g for g in games if {g['home'], g['away']} == {H, A}]
        out('H2H', '%s — %s | %s' % (H, A, ' · '.join('%s %s %d:%d %s%s' % (g['day'][8:10] + '.' + g['day'][5:7], g['home'], g['hg'], g['ag'],
                                                                           g['away'], ' ' + g['e'] if g['e'] else '') for g in h2h)
                                     or 'в этом сезоне не играли'))
        x1x2 = [odds_for(('ml', 6, s), mks)[0] or fonbet_for(('ml', 6, s), fon) for s in ('home', 'draw', 'away')]
        fin = [odds_for(('ml', 0, s), mks)[0] for s in ('home', 'away')]
        info = dict((meta or {}).get((H, A)) or {})
        if new:
            info['rate'] = new.get('info')
        info.update(h=H, a=A, x1x2=x1x2, fin=fin, pick=pick,
                    top=[{k: x[k] for k in ('t', 'p', 'odds', 'src', 'mark') if k in x} for x in rows if x['odds']][:12])
        out('PICKJSON', json.dumps(info, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    run(json.load(open(sys.argv[1], encoding='utf-8')), [tuple(p.split('|', 1)) for p in sys.argv[2].split(';')])
