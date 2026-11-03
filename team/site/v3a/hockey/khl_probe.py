# -*- coding: utf-8 -*-
"""Разведка приложения КХЛ для раздела «Игроки КХЛ»: что есть по игроку (players_v2: фото, статистика) и по матчу
(event_v2: есть ли статистика игроков по матчу). Результат — hockey/data/khl_probe.json (коммит в ветку)."""
import json, os, time
from datetime import datetime, timezone

import requests

B = 'https://khl.api.webcaster.pro/api/khl_mobile/'
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
H = os.path.dirname(os.path.abspath(__file__))
out = {}


def get(p):
    r = S.get(B + p, timeout=40); r.raise_for_status(); return r.json()


def cut(v, n=1500):
    s = json.dumps(v, ensure_ascii=False); return s[:n]


try:
    boot = get('data.json'); stage = boot.get('current_stage_id'); out['stage'] = stage
    arr = get('players_v2.json?stage_id=%s&q[team_id_eq]=44&page=1' % stage)
    out['player_full'] = arr[0] if arr else None
    out['players_n'] = len(arr)
except Exception as e:  # noqa: BLE001
    out['err_players'] = repr(e)
try:
    now = int(time.time())
    ev = get('events_v2.json?order_direction=desc&page=1&q%%5Bstart_at_lt_time_from_unixtime%%5D=%d' % now)
    ev = [x.get('event') or x for x in ev]
    out['events_list_keys'] = sorted(ev[0].keys()) if ev else None
    done = [x for x in ev if str(x.get('game_state_key') or x.get('state') or '').lower() in ('finished', 'over', 'ended')] or ev
    e = get('event_v2.json?id=%s' % done[0]['id']); e = e.get('event') or e
    out['event_id'] = done[0]['id']
    out['event_keys'] = sorted(e.keys())
    out['event_fields'] = {k: cut(v) for k, v in e.items() if isinstance(v, (dict, list))}
    for path in ('event_v2/players.json?id=%s', 'events/%s/players.json', 'event_v2/protocol.json?id=%s', 'protocol_v2.json?event_id=%s'):
        try:
            out['try ' + path] = cut(get(path % done[0]['id']), 2500)
        except Exception as x:  # noqa: BLE001
            out['try ' + path] = repr(x)[:200]
except Exception as e:  # noqa: BLE001
    out['err_event'] = repr(e)
os.makedirs(os.path.join(H, 'data'), exist_ok=True)
json.dump(out, open(os.path.join(H, 'data', 'khl_probe.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('KHLPROBE ok', list(out), flush=True)
