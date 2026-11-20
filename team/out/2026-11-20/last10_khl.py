# -*- coding: utf-8 -*-
"""Последние 10 матчей команд КХЛ дня (просьба владельца 20.11: экспрессы по последним 10 играм) — пометками ::notice L10.
Счёт основного времени (ОТ/Б = ничья в осн. время, как calc.team_games)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'picks'))
import khl_data, calc
day = sys.argv[1]
games, nxt = khl_data.fetch(day)
T = calc.team_games(calc.prep(games))
for m in nxt:
    if m['d'][:10] != day:
        continue
    for t in (m['h'], m['a']):
        lst = [x for x in T.get(t, []) if x['day'] < day][-10:]
        rows = ['%s %s %s %d:%d%s' % (x['day'][8:10] + '.' + x['day'][5:7], 'д' if x['home'] else 'г', x['opp'], x['rf'], x['ra'],
                                      ' (итог %d:%d %s)' % (x['gf'], x['ga'], x['e']) if x['ot'] else '') for x in lst]
        tot = [x['rf'] + x['ra'] for x in lst]
        s = ('%s (%s — %s) | осн. время В-Н-П %d-%d-%d | забивает %.1f, пропускает %.1f | тотал<5,5 %d, <6,5 %d, >4,5 %d из %d | '
             'проиграл 2+ шайбы %d, выиграл 2+ %d | ' % (
                 t, m['h'], m['a'], sum(x['rf'] > x['ra'] for x in lst), sum(x['rf'] == x['ra'] for x in lst), sum(x['rf'] < x['ra'] for x in lst),
                 sum(x['rf'] for x in lst) / len(lst), sum(x['ra'] for x in lst) / len(lst), sum(v < 5.5 for v in tot), sum(v < 6.5 for v in tot),
                 sum(v > 4.5 for v in tot), len(lst), sum(x['ra'] - x['rf'] >= 2 for x in lst), sum(x['rf'] - x['ra'] >= 2 for x in lst))
             + ' · '.join(rows))
        print(s, flush=True)
        print('::notice title=L10::%s' % s, flush=True)
