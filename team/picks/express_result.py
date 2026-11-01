# -*- coding: utf-8 -*-
"""Итог экспресса (владелец 01.11): счёт каждой ноги (API лиги) → расчёт → баннер «ИТОГ ЭКСПРЕССА» с отметками.
    PYTHONPATH=render python3 team/picks/express_result.py <coupons.json> <номер купона с 1> <папка> [pid]
Печатает строки EXPRRES (для Actions-аннотаций): нога, счёт, итог; EXPRTOTAL win|loss|pending. Баннер — <папка>/e<k>_result.jpg,
только если все ноги сыграны. Без процентов (EXPRESS.md)."""
import json
import os
import sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
for sub in ('render', 'team/daily', 'team/picks'):
    sys.path.insert(0, os.path.join(ROOT, sub))
import data  # noqa: E402
import settle  # noqa: E402
import express_card as ec  # noqa: E402
import express_render as er  # noqa: E402


def main(src, k, out):
    c = json.load(open(os.path.join(ROOT, src), encoding='utf-8'))['coupons'][int(k) - 1]
    picks = []
    for x in c['legs']:
        st = datetime.strptime('%s %s' % (x['date'], x['time']), '%Y-%m-%d %H:%M').replace(tzinfo=data.MSK)
        picks.append(dict(league='NHL' if x['league'] in ('НХЛ', 'NHL') else 'KHL', home=settle.canon(x['home']),
                          away=settle.canon(x['away']), start=st, bet=x['bet']))
    found, errs = data.games_for(picks)
    for e in errs:
        print('EXPRERR', e, flush=True)
    legs, res = [], []
    for x, p in zip(c['legs'], picks):
        g = data.match_game(found, p)
        if not g or g['state'] != 'final' or g.get('hg') is None:
            print('EXPRRES %s — %s: нет финала (%s)' % (x['home'], x['away'], g and g['state']), flush=True)
            res.append(None)
            continue
        r, _, _ = settle.settle(p['bet'], p['home'], p['away'], g)
        res.append(r)
        print('EXPRRES %s — %s %s:%s %s → %s (%s)' % (x['home'], x['away'], g['hg'], g['ag'], g.get('end') or '', r, x['bet']), flush=True)
        legs.append(dict(home=x['home'], away=x['away'], time=x['time'], bet=x['bet_short'], kef=x['kef'],
                         league=x['league'], mark={'win': 'win', 'loss': 'loss'}.get(r, 'push')))
    if None in res:
        print('EXPRTOTAL pending', flush=True)
        return
    ok = all(r == settle.WIN for r in res)
    print('EXPRTOTAL', 'win' if ok else 'loss', flush=True)
    os.makedirs(os.path.join(ROOT, out), exist_ok=True)
    for fmt in ('feed',):
        p = ec.render(legs, os.path.join(ROOT, out, 'e%s_result.jpg' % k), fmt=fmt, title='ИТОГ ЭКСПРЕССА',
                      date_title=er.date_title(c['legs']), total=c['kef'])
        print('EXPRFILE', p, flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:4])
