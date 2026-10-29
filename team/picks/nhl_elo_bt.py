# -*- coding: utf-8 -*-
"""Elo таблицы НХЛ (apps-script/nhl/Код.js, recalcElo) на матчах этого сезона: как сейчас и с поправками
(владелец 29.10: стартовый рейтинг весит больше формы — Колорадо 97 против Сиэтла 23 даёт ~93 % на победу).

Повтор формулы таблицы: Elo = 1500 + (старт − 50) × ELO_SCALE, ожидание 1/(1+10^(−Δ/400)) без преимущества льда,
победа в ОТ/Б = 0,75, множитель разницы шайб как у FiveThirtyEight, скорость ELO_K × (1 + boost × (1 − игр/15)).
Каждый матч оценивается по Elo ДО него. Сравнение: logloss и Брайер «итоговой победы хозяев», «обещали / зашло».
Стартовый рейтинг — из NHL_TEAMS таблицы (15.09) или из нового рейтинга (nhl_model, конец прошлого сезона, сжатый).
В лог: ELOBT (варианты), ELOBTREL, ELOSTART.
    python team/picks/nhl_elo_bt.py"""
import itertools
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nhl_hist as HI  # noqa: E402
import nhl_model as MO  # noqa: E402
import nhl_live as LV  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def out(tag, text):
    print(tag + ' ' + text, flush=True)


def sheet_start():
    src = open(os.path.join(ROOT, 'apps-script', 'nhl', 'Код.js'), encoding='utf-8').read()
    return {m.group(1): int(m.group(2)) for m in re.finditer(r"\['[A-Z]{3}', '([^']+)',[^\]]*?, (\d+)\]", src)}


def run(games, start, scale, k, boost, home=0.0, early=15):
    elo = {t: 1500 + (v - 50) * scale for t, v in start.items()}
    gp = {}
    res = []
    for g in games:
        h, a = g['h'], g['a']
        eh, ea = elo.get(h, 1500), elo.get(a, 1500)
        exp = 1 / (1 + 10 ** ((ea - eh - home) / 400))
        won = g['hg'] > g['ag']
        res.append((exp, 1 if won else 0))
        act = (0.75 if won else 0.25) if g['e'] else (1.0 if won else 0.0)
        mov = 1.0
        if not g['e']:
            diff = abs(g['hg'] - g['ag'])
            ew = (eh - ea) if won else (ea - eh)
            mov = (math.log(diff) + 1) * 2.2 / (ew * 0.001 + 2.2)
        kh = k * (1 + boost * max(0, 1 - gp.get(h, 0) / early)) * mov
        ka = k * (1 + boost * max(0, 1 - gp.get(a, 0) / early)) * mov
        elo[h] = eh + kh * (act - exp)
        elo[a] = ea + ka * ((1 - act) - (1 - exp))
        gp[h] = gp.get(h, 0) + 1
        gp[a] = gp.get(a, 0) + 1
    return res, elo


def ll(rs):
    return -sum(math.log(max(1e-9, p if y else 1 - p)) for p, y in rs) / len(rs)


def br(rs):
    return sum((p - y) ** 2 for p, y in rs) / len(rs)


def main():
    cur = HI.season_of(HI.datetime.now(HI.timezone(HI.timedelta(hours=-5))).date().isoformat())
    G = HI.load(seasons=[cur - 2, cur - 1, cur])
    S = {}
    for g in G:
        S.setdefault(g['s'], []).append(g)
    games = sorted(S[cur], key=lambda g: g['d'])
    sheet = sheet_start()
    # новый старт: сила конца прошлого сезона (nhl_model, лучшие параметры), сжатая, по шкале 1–100
    P = LV.BEST
    final = {}
    for s in sorted(S):
        if s == cur:
            break
        prior = MO.shrink_prior(final[s - 1], P) if s - 1 in final else None
        final[s] = MO.ratings(S[s], P, prior, final[s - 1]['mu'] if s - 1 in final else None)
    R = dict(final[cur - 1])
    pr = MO.shrink_prior(R, P)
    R = dict(R, A={t: v[0] for t, v in pr.items()}, D={t: v[1] for t, v in pr.items()})
    model_start = MO.rating100(R)
    out('ELOSTART', 'таблица (15.09): ' + ' · '.join('%s %d' % (t, sheet[t]) for t in sorted(sheet, key=lambda t: -sheet[t])))
    out('ELOSTART', 'новый рейтинг (конец прошлого сезона, сжат): ' + ' · '.join(
        '%s %d' % (t, model_start[t]) for t in sorted(model_start, key=lambda t: -model_start[t])))
    flat = {t: 50 for t in sheet}
    rows = []
    for (nm, st), scale, k, boost, home in itertools.product(
            (('таблица', sheet), ('новый', model_start), ('все 50', flat)), (6, 4, 3, 2), (20, 30, 40), (0, 1, 2), (0, 30)):
        rs, elo = run(games, st, scale, k, boost, home)
        rows.append((ll(rs), nm, scale, k, boost, home, br(rs), rs, elo))
    rows.sort(key=lambda r: r[0])
    base = next(r for r in rows if r[1] == 'таблица' and r[2] == 6 and r[3] == 20 and r[4] == 0 and r[5] == 0)
    out('ELOBT', 'сейчас в таблице: старт таблица, ELO_SCALE 6, ELO_K 20, boost 0, лёд 0 | матчей %d | logloss %.4f | Брайер %.4f'
        % (len(games), base[0], base[6]))
    for r in rows[:12]:
        out('ELOBT', 'старт %-7s ELO_SCALE %d ELO_K %d boost %d лёд %2d | logloss %.4f | Брайер %.4f' % (
            r[1], r[2], r[3], r[4], r[5], r[0], r[6]))
    for nm in ('таблица', 'новый', 'все 50'):
        r = next(x for x in rows if x[1] == nm)
        out('ELOBT', 'лучший со стартом «%s»: ELO_SCALE %d ELO_K %d boost %d лёд %d | logloss %.4f' % (nm, r[2], r[3], r[4], r[5], r[0]))
    for tag, r in (('сейчас', base), ('лучший', rows[0])):
        for lo, hi in ((0, .35), (.35, .45), (.45, .55), (.55, .65), (.65, .75), (.75, 1.01)):
            xs = [(p, y) for p, y in r[7] if lo <= p < hi]
            if len(xs) >= 10:
                out('ELOBTREL', '%s | %2d–%2d %% | матчей %3d | обещано %4.1f %% | зашло %4.1f %%' % (
                    tag, 100 * lo, min(100, 100 * hi), len(xs), 100 * sum(p for p, _ in xs) / len(xs),
                    100 * sum(y for _, y in xs) / len(xs)))
    e0, e1 = base[8], rows[0][8]
    out('ELONOW', 'сейчас: ' + ' · '.join('%s %d' % (t, round(50 + (e0[t] - 1500) / 6)) for t in sorted(e0, key=lambda t: -e0[t])))
    out('ELONOW', 'лучший: ' + ' · '.join('%s %d' % (t, round(50 + (e1[t] - 1500) / rows[0][2])) for t in sorted(e1, key=lambda t: -e1[t])))


if __name__ == '__main__':
    main()
