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
out('khl_list', [dict(id=g['id'], h=g['home'], a=g['away'], s='%s:%s' % (g['hg'], g['ag'])) for g in khl])
if khl:
    gid = khl[0]['id']
    safe('khl_event_v2', lambda: data.khl_get('event_v2.json?id=%s' % gid))
    for path in ('text_events.json?id=%s', 'event_text_v2.json?id=%s', 'events/%s/text_events.json', 'event_texts.json?event_id=%s',
                 'broadcast.json?id=%s', 'event_stats.json?id=%s', 'event_protocol.json?id=%s'):
        safe('khl_' + path.split('.')[0].replace('/', '_'), lambda p=path: data.khl_get(p % gid), 4000)
nhl = [g for g in data.nhl_day('2026-10-17') if g['state'] == 'final']
out('nhl_list', [dict(id=g['id'], h=g['home'], a=g['away'], s='%s:%s' % (g['hg'], g['ag'])) for g in nhl])
if nhl:
    gid = nhl[0]['id']
    def pbp():
        j = data.nhl_get('gamecenter/%s/play-by-play' % gid)
        keep = ('goal', 'penalty', 'shot-on-goal', 'hit', 'giveaway', 'takeaway', 'blocked-shot', 'period-start', 'period-end')
        plays = [dict(t=p.get('typeDescKey'), per=(p.get('periodDescriptor') or {}).get('number'), tm=p.get('timeInPeriod'),
                      sit=p.get('situationCode'), d=p.get('details')) for p in j.get('plays') or [] if p.get('typeDescKey') in keep]
        return dict(keys=list(j), roster=(j.get('rosterSpots') or [])[:3], n=len(j.get('plays') or []), plays=plays)
    safe('nhl_pbp', pbp)
    safe('nhl_landing', lambda: data.nhl_get('gamecenter/%s/landing' % gid))
    safe('nhl_right_rail', lambda: data.nhl_get('gamecenter/%s/right-rail' % gid), 20000)
