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
    try:                                         # новый рейтинг КХЛ (владелец 29.10) — когда включён в khl_live.ENABLED
        import khl_live
        if khl_live.ENABLED:
            calc.NHL_NEW, calc.NHL_WN = khl_live.prepare(DAY, nxt), khl_live.WN
    except Exception as e:  # noqa: BLE001 — не посчитался: прогнозы по старому расчёту
        print('NHLLIVEERR КХЛ: новый рейтинг не посчитан, считаю по-старому: %r' % e, flush=True)
        calc.NHL_NEW = {}
else:
    import nhl_data
    games, nxt = nhl_data.fetch(DAY)
    fon = {}
    try:                                         # новый рейтинг НХЛ (владелец 29.10): xG, вратарь-стартер, два дня подряд
        import nhl_live
        calc.NHL_NEW, calc.NHL_WN = nhl_live.prepare(DAY, nxt), nhl_live.WN
    except Exception as e:  # noqa: BLE001 — не посчитался: прогнозы по старому расчёту
        print('NHLLIVEERR новый рейтинг не посчитан, считаю по-старому: %r' % e, flush=True)
        calc.NHL_NEW = {}
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
