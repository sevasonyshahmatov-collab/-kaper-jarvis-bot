# -*- coding: utf-8 -*-
"""Сверка линии Фонбета с Pinnacle (31.10, поручение «котировки Фонбета»): правильно ли разобраны коды и сопоставлены
матчи. На день: КХЛ, НХЛ (calc.markets → calc.odds_for по обеим линиям) и топ-лиги футбола (1Х2, тотал 2,5).
Хоккей: тоталы 4,5 / 6,5 сравниваются с Pinnacle «осн. время» (period 6) и «с ОТ» (period 0) — чья ближе, то и у Фонбета.
Вывод — пометками ::notice FCK_* (логи Actions из облака закрыты): по лиге — матчей, сопоставлено, медиана кэф Ф / кэф P,
доля рынков, где у Фонбета ниже, маржа 1Х2, худшие расхождения. Запуск: python team/picks/fon_check.py 2026-10-31"""
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calc  # noqa: E402
import fonbet as FON  # noqa: E402
import pin  # noqa: E402

DAY = sys.argv[1]
notes = []


def note(t, m):
    notes.append((t, str(m).replace('\n', ' ')[:3900]))


def summary(lg, pairs_ratio, worst, extra=''):
    rs = [r for r in pairs_ratio if r]
    if not rs:
        note('FCK_' + lg, 'нет общих рынков. ' + extra)
        return
    worst.sort(key=lambda x: -abs(x[0] - 1))
    note('FCK_' + lg, 'общих рынков %d | медиана Ф/P %.3f | у Фонбета ниже %d%% | |Ф/P−1|>10%%: %d | %s | худшие: %s'
         % (len(rs), statistics.median(rs), 100 * sum(1 for r in rs if r < 1) / len(rs), sum(1 for r in rs if abs(r - 1) > 0.10),
            extra, '; '.join('%s %s Ф%.2f P%.2f' % (w[1], w[2], w[3], w[4]) for w in worst[:6])))


for lg in ('khl', 'nhl'):
    try:
        pins, _ = pin.fetch(lg, DAY)
        fon = FON.hockey_day(lg, DAY, list(pins))
    except Exception as e:  # noqa: BLE001
        note('FCK_' + lg, 'ошибка %r' % e)
        continue
    rat, worst, regs, ots, marg = [], [], [], [], []
    for pair, v in fon.items():
        mks = pins.get(pair)
        marg.append(FON.overround(v['flat']).get('1Х2'))
        if not mks:
            continue
        for mk in calc.markets(*pair):
            f, _ = calc.odds_for(mk['k'], v['mks'])
            p, _ = calc.odds_for(mk['k'], mks)
            if f and p:
                rat.append(f / p)
                worst.append((f / p, '%s—%s' % pair, mk['t'][:28], f, p))
        for x in (4.5, 6.5):                      # осн. время или с ОТ? сравнить с period 6 и 0
            f = v['flat'].get('ТБ %.1f' % x)
            p6 = next((q['price'] for m in mks if m['type'] == 'total' and m['period'] == 6 for q in m['prices']
                       if q['designation'] == 'over' and q['points'] == x), None)
            p0 = next((q['price'] for m in mks if m['type'] == 'total' and m['period'] == 0 for q in m['prices']
                       if q['designation'] == 'over' and q['points'] == x), None)
            if f and p6 and p0:
                regs.append(abs(1 / f - 1 / p6))
                ots.append(abs(1 / f - 1 / p0))
    extra = 'матчей Фонбет %d / Pinnacle %d / общих %d | маржа 1Х2 %s | ТБ 4,5/6,5: |Δp| к осн. времени %.3f, к «с ОТ» %.3f (n=%d)' % (
        len(fon), len(pins), len(set(fon) & set(pins)), ', '.join('%.3f' % m for m in marg if m)[:120],
        statistics.mean(regs) if regs else -1, statistics.mean(ots) if ots else -1, len(regs))
    summary(lg.upper(), rat, worst, extra)

import football_live as FL  # noqa: E402
rat, worst, cnt = [], [], []
for code in ('E0', 'SP1', 'I1', 'D1', 'F1', 'UCL', 'UEL'):
    try:
        line = FL.pin_day(code, DAY)
        fevs = FON.foot_day(code, DAY)
    except Exception as e:  # noqa: BLE001
        cnt.append('%s ошибка %r' % (code, e))
        continue
    ok = 0
    for (ph, pa, t), od in line.items():
        fe = FON.match_foot(fevs, ph, pa, t, None, code)
        if not fe:
            continue
        ok += 1
        for k in ('П1', 'Х', 'П2', '1Х', 'Х2', 'ТБ 2.5', 'ТМ 2.5'):
            if k in od and k in fe['flat']:
                rat.append(fe['flat'][k] / od[k])
                worst.append((fe['flat'][k] / od[k], '%s—%s' % (fe['h'], fe['a']), k, fe['flat'][k], od[k]))
    cnt.append('%s: Pinnacle %d, Фонбет %d, сопоставлено %d' % (code, len(line), len(fevs), ok))
summary('FOOT', rat, worst, ' · '.join(cnt))
for t, m in notes:
    print('::notice title=%s::%s' % (t, m), flush=True)
