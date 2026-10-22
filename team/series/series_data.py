# -*- coding: utf-8 -*-
"""Данные для роликов серии «Как работает JARVIS» — матчи следующего игрового дня (владелец 22.10: «примеры — на матчи
следующего дня»). Источники и правило прогноза — как у конвейера шортсов (team/reels_daily/make.py plan), но без
сообщений в Telegram. → D для render/reels/explainer_viz.py.

    python team/series/series_data.py 2026-10-23 [khl|nhl]      # печатает D (облачной сессии API КХЛ недоступен — только Actions)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (os.path.join(ROOT, 'team', 'picks'), os.path.join(ROOT, 'team', 'reels_daily')):
    sys.path.insert(0, p)

LG = {'khl': 'КХЛ', 'nhl': 'НХЛ'}


def k2(v):
    return '%.2f' % v if v else '—'


def build(day, league='khl'):
    import form
    import pick
    import pin
    if league == 'khl':
        import khl_data
        games, nxt = khl_data.fetch(day)
        fon = {(x['h'], x['a']): x.get('bets') for x in nxt}
    else:
        import nhl_data
        games, nxt = nhl_data.fetch(day)
        fon = {}
    try:
        pins, _ = pin.fetch(league, day, [(x['h'], x['a']) for x in nxt])
    except Exception as e:  # noqa: BLE001
        print('PINERR %r' % e, flush=True)
        pins = {}
    ms = sorted(pick.day_picks(games, nxt, pins, fon, league), key=lambda m: m['d'])
    if not ms:
        return None
    rows = []
    for m in ms:
        x = m.get('x1x2') or [None] * 3
        rows.append((m['d'][11:16], m['h'], m['a'], k2(x[0]), k2(x[1]), k2(x[2]), m['pick'], k2(m['odds'])))
    top = max(ms, key=lambda m: m['p'])                 # разбор — самый уверенный прогноз дня
    st = (form.khl if league == 'khl' else form.nhl)(games, day, [top['h'], top['a']])
    last = lambda t: [(g['score'], g['res'][:1]) for g in (st.get(t) or {}).get('last3', [])]  # noqa: E731
    return dict(day='%s.%s' % (day[8:10], day[5:7]), lg=LG[league], rows=rows,
                case=dict(h=top['h'], a=top['a'], time=top['d'][11:16], last_h=last(top['h']), last_a=last(top['a'])))


if __name__ == '__main__':
    print(json.dumps(build(sys.argv[1], (sys.argv[2:] or ['khl'])[0]), ensure_ascii=False, indent=1))
