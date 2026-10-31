# -*- coding: utf-8 -*-
"""Ролики v3: данные сезона для форматов 2–4 (ТЗ docs/handoff/REELS_V3_BRIEF.md).

Из истории лиг (team/picks/khl_hist.py — приложение КХЛ, nhl_hist.py — API НХЛ; кэш .lines/*_hist, сеть — только в Actions):
- bets(games, team)     — формат 2 «весь сезон ставим X на команду»: по каждому виду ставки — матчи по порядку
                          (счёт, зашло/нет), N из M, баланс в ставках, если у ВСЕХ учтённых матчей есть кэф (НХЛ — кэфы
                          закрытия DraftKings/ESPN из nhl_hist `o`, КХЛ кэфов в истории нет → только «зашло N из M»);
- patterns(games)       — формат 3: закономерности (случаи N из M, не меньше MIN_CASES случаев у команды);
- club(games, team)     — формат 4: цифры клуба (серии, дом/выезд, тоталы, форма).
Проверка: число учтённых матчей = числу игр команды в сезоне; N пересчитан вторым способом (по счёту заново).
Запуск в Actions: python team/reels_v3/season.py → team/reels_v3/data/season.json + строки V3SEASON в лог.
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'team', 'picks'))
MIN_CASES = 5
OUT = os.path.join(ROOT, 'team', 'reels_v3', 'data', 'season.json')


def _per(p):
    try:
        a, _, b = str(p).replace(' ', '').partition(':')
        return int(a), int(b)
    except ValueError:
        return None


def view(g, team):
    """Матч глазами команды: gf, ga (итог), rf, ra (осн. время), периоды [(f, a)], дома, окончание, кэф победы, тотал."""
    home = g['h'] == team
    hg, ag = g['hg'], g['ag']
    r = g.get('r') or [hg, ag]
    per = [_per(p) for p in (g.get('p') or [])[:3]]
    per = [(x[0], x[1]) if home else (x[1], x[0]) for x in per if x]
    o = g.get('o') or {}
    ml = (o.get('ml') or [None, None])
    return dict(d=g['d'][:10], opp=g['a'] if home else g['h'], home=home, gf=hg if home else ag, ga=ag if home else hg,
                rf=r[0] if home else r[1], ra=r[1] if home else r[0], per=per, e=g.get('e') or '',
                kwin=ml[0] if home else ml[1], tot=o.get('tot'))


BETS = [  # (ключ, как в ролике, функция зашло(v))
    ('win', 'победу', lambda v: v['gf'] > v['ga']),
    ('regwin', 'победу в основное время', lambda v: v['rf'] > v['ra']),
    ('noloss', '«не проиграет в основное время»', lambda v: v['rf'] >= v['ra']),
    ('o45', 'тотал больше 4,5', lambda v: v['rf'] + v['ra'] > 4.5),
    ('o55', 'тотал больше 5,5', lambda v: v['rf'] + v['ra'] > 5.5),
    ('u45', 'тотал меньше 4,5', lambda v: v['rf'] + v['ra'] < 4.5),
    ('it25', 'забьёт 3+ в основное время', lambda v: v['rf'] >= 3),
    ('loss', 'поражение', lambda v: v['gf'] < v['ga']),
]


def team_games(games, team):
    return [view(g, team) for g in games if team in (g['h'], g['a'])]


def bets(games, team):
    vs = team_games(games, team)
    res = []
    for key, name, fn in BETS:
        seq = [1 if fn(v) else 0 for v in vs]
        n = sum(seq)
        # проверка вторым способом: заново по строке счёта
        n2 = sum(1 for v in vs if fn(dict(v)))
        assert n == n2 and len(seq) == len(vs)
        bal = None
        if key == 'win' and vs and all(v['kwin'] for v in vs):
            bal = round(sum((v['kwin'] - 1) if s else -1 for v, s in zip(vs, seq)), 2)
        res.append(dict(key=key, bet=name, n=n, m=len(vs), bal=bal,
                        seq=''.join(map(str, seq)),
                        games=[[v['d'][5:], v['opp'], '%d:%d%s' % (v['gf'], v['ga'], (' ' + v['e']) if v['e'] else ''),
                                v['kwin']] for v in vs]))
    return res


def streaks(vs, fn):
    best = cur = 0
    for v in vs:
        cur = cur + 1 if fn(v) else 0
        best = max(best, cur)
    tail = 0
    for v in reversed(vs):
        if not fn(v):
            break
        tail += 1
    return best, tail


def club(games, team):
    vs = team_games(games, team)
    if not vs:
        return None
    W = lambda v: v['gf'] > v['ga']
    L = lambda v: v['gf'] < v['ga']
    NL = lambda v: v['rf'] >= v['ra']
    hw = [v for v in vs if v['home']]
    aw = [v for v in vs if not v['home']]
    p3 = [sum(v['per'][i][0] for v in vs if len(v['per']) > i) for i in range(3)]
    p3a = [sum(v['per'][i][1] for v in vs if len(v['per']) > i) for i in range(3)]
    return dict(team=team, gp=len(vs), w=sum(map(W, vs)), l=sum(map(L, vs)),
                gf=sum(v['gf'] for v in vs), ga=sum(v['ga'] for v in vs),
                home=[sum(map(W, hw)), len(hw)], away=[sum(map(W, aw)), len(aw)],
                win_streak=streaks(vs, W), loss_streak=streaks(vs, L), noloss_streak=streaks(vs, NL),
                o55=sum(1 for v in vs if v['rf'] + v['ra'] > 5.5), periods_for=p3, periods_against=p3a,
                last5=['%s %s %d:%d%s' % (v['d'][5:], v['opp'], v['gf'], v['ga'], (' ' + v['e']) if v['e'] else '')
                       for v in vs[-5:]],
                ot=sum(1 for v in vs if v['e']))


def patterns(games, teams):
    """Закономерности: по каждой теме — список (команда, N, M) с M ≥ MIN_CASES, по убыванию доли."""
    P = defaultdict(list)
    for t in teams:
        vs = team_games(games, t)
        # 1) проигрывали после двух периодов → не проиграли в основное время (отыгрались в 3-м)
        c = [v for v in vs if len(v['per']) >= 3 and sum(p[0] for p in v['per'][:2]) < sum(p[1] for p in v['per'][:2])]
        P['comeback3'].append((t, sum(1 for v in c if v['rf'] >= v['ra']), len(c)))
        # 2) проиграли первый период → выиграли матч
        c = [v for v in vs if v['per'] and v['per'][0][0] < v['per'][0][1]]
        P['lost1_won'].append((t, sum(1 for v in c if v['gf'] > v['ga']), len(c)))
        # 3) вели после двух периодов → не удержали (не выиграли в основное время)
        c = [v for v in vs if len(v['per']) >= 3 and sum(p[0] for p in v['per'][:2]) > sum(p[1] for p in v['per'][:2])]
        P['blown_lead'].append((t, sum(1 for v in c if v['rf'] <= v['ra']), len(c)))
        # 4) матчи с овертаймом / буллитами
        P['ot'].append((t, sum(1 for v in vs if v['e']), len(vs)))
        # 5) забивают в первом периоде
        c = [v for v in vs if v['per']]
        P['score_p1'].append((t, sum(1 for v in c if v['per'][0][0] > 0), len(c)))
        # 6) выигранные третьи периоды
        c = [v for v in vs if len(v['per']) >= 3]
        P['win_p3'].append((t, sum(1 for v in c if v['per'][2][0] > v['per'][2][1]), len(c)))
    out = {}
    for k, rows in P.items():
        rows = [r for r in rows if r[2] >= MIN_CASES]
        rows.sort(key=lambda r: (-r[1] / r[2], -r[2]))
        out[k] = rows
    return out


def league(name, games):
    cur = max(g['s'] for g in games)
    games = [g for g in games if g['s'] == cur]
    teams = sorted({g['h'] for g in games} | {g['a'] for g in games})
    return dict(league=name, season=cur, n_games=len(games), last=max(g['d'] for g in games),
                teams={t: dict(club=club(games, t), bets=bets(games, t)) for t in teams},
                patterns=patterns(games, teams))


def main():
    res = {}
    try:
        import khl_hist
        today = datetime.now(timezone(timedelta(hours=3))).date().isoformat()
        g = khl_hist.load(seasons=[khl_hist.season_of(today)], today=today)
        res['khl'] = league('КХЛ', g)
    except Exception as e:  # noqa: BLE001
        print('V3SEASON KHL ошибка %r' % e, flush=True)
    try:
        import nhl_hist
        today = datetime.now(timezone(timedelta(hours=-5))).date().isoformat()
        g = nhl_hist.load(seasons=[nhl_hist.season_of(today)], today=today)
        res['nhl'] = league('НХЛ', g)
    except Exception as e:  # noqa: BLE001
        print('V3SEASON NHL ошибка %r' % e, flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    for k, L in res.items():
        print('V3SEASON %s сезон %d матчей %d по %s, команд %d' % (L['league'], L['season'], L['n_games'], L['last'],
                                                                  len(L['teams'])), flush=True)
        for pk, rows in L['patterns'].items():
            print('V3PAT %s %s top %s | bottom %s' % (k, pk, rows[:3], rows[-2:]), flush=True)
        ext = []
        for t, d in L['teams'].items():
            for b in d['bets']:
                if b['m']:
                    ext.append((abs(b['n'] / b['m'] - 0.5), t, b['key'], b['n'], b['m'], b['bal']))
        ext.sort(reverse=True)
        for e in ext[:25]:
            print('V3BET %s %s %s %d/%d bal=%s' % (k, e[1], e[2], e[3], e[4], e[5]), flush=True)
        for t, d in L['teams'].items():
            c = d['club']
            print('V3CLUB %s %s' % (k, json.dumps(c, ensure_ascii=False, separators=(',', ':'))), flush=True)


if __name__ == '__main__':
    main()
