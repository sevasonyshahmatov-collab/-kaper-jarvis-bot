# -*- coding: utf-8 -*-
"""Данные к ежедневным прогнозам одним заданием Actions: матчи сезона и матчи дня (приложение КХЛ / API НХЛ),
линия Pinnacle, «Что заходит» по каждой паре с кэфами (calc.py). Всё — в лог; читать его team/picks/parse_log.py.
Задание: {"day": "<сегодня>", "make": ["team/picks/day.py khl 2026-10-16"], "messages": []}
  khl <дата> — матчи КХЛ этой даты по Москве; nhl <дата> — игровой день НХЛ (ночь на следующее число по Москве)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import calc  # noqa: E402
import pin  # noqa: E402

LEAGUE, DAY = sys.argv[1].lower(), sys.argv[2]
print('DAYJOB %s %s' % (LEAGUE, DAY), flush=True)
calc.LEAGUE = LEAGUE.upper()                     # поправка вероятностей по лиге (calc.calibrate, team/picks/calib.json)
if LEAGUE == 'khl':
    import khl_data
    games, nxt = khl_data.fetch(DAY)
    fon = {(x['h'], x['a']): x.get('bets') for x in nxt}
else:
    import nhl_data
    games, nxt = nhl_data.fetch(DAY)
    fon = {}
pairs = [(x['h'], x['a']) for x in nxt]
try:
    pins, starts = pin.fetch(LEAGUE, DAY, pairs)
except Exception as e:  # noqa: BLE001 — без линии расчёт всё равно нужен
    print('PINERR %r' % e, flush=True)
    pins = {}
missing = [p for p in pairs if p not in pins]
if missing:
    print('PINMISS нет линии Pinnacle: %s' % ', '.join('%s—%s' % p for p in missing), flush=True)
calc.run(games, pairs, pins, fon, {(x['h'], x['a']): dict(x, league=LEAGUE) for x in nxt})
print('DAYJOB готово: матчей %d' % len(pairs), flush=True)
