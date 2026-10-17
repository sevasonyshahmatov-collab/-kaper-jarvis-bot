# -*- coding: utf-8 -*-
"""Структура карточки матча КХЛ (event_v2) и голов НХЛ (score/<день>) — для послематчевого текста."""
import json, os, sys
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'daily'))
import data
t0 = datetime(2026, 10, 16, 12, 0, tzinfo=data.MSK)
t1 = datetime(2026, 10, 16, 13, 0, tzinfo=data.MSK)
for g in data.khl_games(t0, t1):
    j = data.khl_get('event_v2.json?id=%s' % g['id'])
    d = j.get('event') or j
    print('KHLKEYS', sorted(d.keys()))
    for k, v in d.items():
        s = json.dumps(v, ensure_ascii=False)
        if any(w in k for w in ('goal', 'score', 'protocol', 'stat', 'shot', 'penalt', 'team_a', 'events')) or len(s) > 300:
            print('KHLFIELD', k, s[:1500])
    break
raw = data.nhl_get('score/2026-10-15')
g = (raw.get('games') or [{}])[0]
print('NHLKEYS', sorted(g.keys()))
print('NHLGOAL', json.dumps((g.get('goals') or [{}])[0], ensure_ascii=False)[:800])
