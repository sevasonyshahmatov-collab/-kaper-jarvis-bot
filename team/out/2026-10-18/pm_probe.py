# -*- coding: utf-8 -*-
"""Разведка: какие подробности матча отдают приложение КХЛ (event_v2 и соседние) и API НХЛ (play-by-play, landing) —
для послематчевого разбора «по ходу матча» (владелец 18.10). Печатает в лог строки «PMPROBE {json}», ничего не шлёт."""
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'daily'))
import data  # noqa: E402


def out(k, obj, lim=60000):
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    print('PMPROBE ' + json.dumps({'k': k, 'n': len(s)}, ensure_ascii=False) + ' ' + s[:lim], flush=True)


def safe(k, f, lim=60000):
    try:
        out(k, f(), lim)
    except Exception as e:  # noqa: BLE001
        print('PMPROBE-ERR %s %r' % (k, e), flush=True)


t0 = datetime(2026, 10, 17, 0, 0, tzinfo=data.MSK)
khl = [g for g in data.khl_games(t0, t0 + timedelta(days=1)) if g['state'] == 'final']
if khl:
    j = data.khl_get('event_v2.json?id=%s' % khl[0]['id'])
    e = j.get('event') or j
    out('khl_keys', {k: (type(v).__name__, len(json.dumps(v, ensure_ascii=False))) for k, v in e.items()})
    for side in ('team_a', 'team_b'):
        t = dict(e.get(side) or {})
        t.pop('top_players', None)
        out('khl_' + side, {k: v for k, v in t.items() if k not in ('players',)}, 8000)
    for k, v in e.items():
        if k in ('team_a', 'team_b', 'arena', 'players'):
            continue
        if isinstance(v, (list, dict)):
            out('khl_f_' + k, v, 12000)
