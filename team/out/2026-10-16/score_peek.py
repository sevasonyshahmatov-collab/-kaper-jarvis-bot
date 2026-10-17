# -*- coding: utf-8 -*-
"""Счёт матчей КХЛ 16.10 (для пробных послематчевых баннеров): итог, периоды, ОТ/Б — печать в лог."""
import json, os, sys
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'daily'))
import data
t0 = datetime(2026, 10, 16, 8, 0, tzinfo=data.MSK)
t1 = datetime(2026, 10, 17, 8, 0, tzinfo=data.MSK)
for g in data.khl_games(t0, t1):
    line = 'SCORE %s %s — %s · %s · %s:%s' % (g['start'].strftime('%H:%M'), g['home'], g['away'], g['state'], g['hg'], g['ag'])
    if g['state'] == 'final':
        try:
            j = data.khl_get('event_v2.json?id=%s' % g['id']); d = j.get('event') or j
            line += ' · ' + json.dumps(d.get('scores') or {}, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            line += ' · err %r' % e
    print(line, flush=True)
