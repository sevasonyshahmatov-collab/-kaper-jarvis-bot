# -*- coding: utf-8 -*-
"""Матчи НХЛ на ночь 14→15.10 (ET 14.10) из официального API — для баннеров «Versus».
Облачная сессия до api-web.nhle.com не достаёт, Actions — достаёт: печатает «NHLDATA {json}», читаем из лога."""
import json

import requests

DAY = '2026-10-14'
r = requests.get('https://api-web.nhle.com/v1/schedule/' + DAY, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
r.raise_for_status()
games = []
for w in r.json().get('gameWeek', []):
    if w.get('date') != DAY:
        continue
    for g in w.get('games', []):
        h, a = g['homeTeam'], g['awayTeam']
        games.append(dict(utc=g.get('startTimeUTC'), home=h['abbrev'], away=a['abbrev'], type=g.get('gameType'),
                          venue=(g.get('venue') or {}).get('default')))
print('NHLDATA ' + json.dumps(games, ensure_ascii=False), flush=True)
