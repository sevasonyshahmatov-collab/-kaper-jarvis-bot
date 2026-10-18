# -*- coding: utf-8 -*-
"""Проверка хроники матча (team/postmatch/chronicle.py) на матчах 17.10 — печатает в лог, ничего не шлёт."""
import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
sys.path[:0] = [os.path.join(ROOT, 'team', 'postmatch'), os.path.join(ROOT, 'team', 'daily')]
import chronicle  # noqa: E402
import data  # noqa: E402

t0 = datetime(2026, 10, 17, 0, 0, tzinfo=data.MSK)
k = next(g for g in data.khl_games(t0, t0 + timedelta(days=1)) if g['home'] == 'Амур')
n = next(g for g in data.nhl_day('2026-10-17') if g['state'] == 'final' and g['home'] == 'Виннипег')
for g in (k, n):
    p = dict(league=g['league'], home=g['home'], away=g['away'])
    print('PMCHRON =====', g['home'], g['away'])
    for line in chronicle.facts(p, g).split('\n'):
        print('PMCHRON', line)
