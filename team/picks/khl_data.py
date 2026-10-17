# -*- coding: utf-8 -*-
"""КХЛ: сыгранные матчи регулярки этого сезона и матчи дня из официального приложения КХЛ (khl.api.webcaster.pro —
тот же источник, что у таблицы КХЛ, лист «КХЛ_матчи_приложение»). Облачная сессия до API не достаёт, Actions — достаёт.
Печатает KHLSTAGE, KHLNEXT (матч дня: время МСК, арена, линия Фонбета П1/Х/П2 в осн. время — поле bets) и KHLPAIR
(история пары за все сезоны — поле this_pair_stat). Отдельно: python team/picks/khl_data.py 2026-10-16"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

import teams

BASE = 'https://khl.api.webcaster.pro/api/khl_mobile/'
MSK = timezone(timedelta(hours=3))
S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0'


def get(path):
    r = S.get(BASE + path, timeout=40)
    r.raise_for_status()
    return r.json()


def out(tag, obj):
    print(tag + ' ' + json.dumps(obj, ensure_ascii=False, separators=(',', ':')), flush=True)


def team(t):
    t = t or {}
    return teams.KHL_IDS.get(t.get('id')) or str(t.get('name') or '').strip()


def msk(ts):
    if isinstance(ts, str) and not ts.isdigit():
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(MSK).strftime('%Y-%m-%d %H:%M')
    v = float(ts or 0)
    return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, MSK).strftime('%Y-%m-%d %H:%M')


def detail(e):
    for k in range(3):
        try:
            j = get('event_v2.json?id=%s' % e['id'])
            return j.get('event') or j
        except Exception as err:  # noqa: BLE001
            if k == 2:
                print('KHLERR', e.get('id'), err, flush=True)
                return None
            time.sleep(1 + k)


def fetch(day):
    """→ (сыгранные матчи [{d, id, h, a, hg, ag, e, p}], матчи дня [{d, id, h, a, bets, arena}])."""
    boot = get('data.json')
    stage = boot.get('current_stage_id')
    st = next((x for x in boot.get('stages_v2') or [] if x.get('id') == stage), {})
    out('KHLSTAGE', {'stage': stage, 'season': st.get('season'), 'title': st.get('title') or st.get('name')})
    year = int(str(st.get('season') or day)[:4])
    frm = int(datetime(year, 8, 1, tzinfo=timezone.utc).timestamp())
    to = int(datetime.fromisoformat(day).replace(tzinfo=MSK).timestamp()) + 2 * 86400
    events = []
    for page in range(1, 81):
        q = ('events_v2.json?order_direction=asc&page=%d&q%%5Bstart_at_gt_time_from_unixtime%%5D=%d'
             '&q%%5Bstart_at_lt_time_from_unixtime%%5D=%d&stage_id=%s' % (page, frm, to, stage))
        arr = get(q)
        if not isinstance(arr, list) or not arr:
            break
        for w in arr:
            e = w.get('event') or w
            if e and e.get('type_id') in (18, 24):
                events.append(e)
        if len(arr) < 16:
            break
    done = [e for e in events if e.get('game_state_key') == 'finished']
    with ThreadPoolExecutor(8) as ex:
        details = list(ex.map(detail, done))
    games = []
    for e, d in zip(done, details):
        src = d or e
        sc = str(src.get('score') or e.get('score') or '').split(':')
        if len(sc) != 2:
            continue
        s = src.get('scores') or {}
        end = 'Б' if s.get('bullitt') else 'ОТ' if s.get('overtime') else ''
        games.append({'d': msk(src.get('start_at') or e.get('start_at')), 'id': e.get('id'), 'h': team(src.get('team_a') or e.get('team_a')),
                      'a': team(src.get('team_b') or e.get('team_b')), 'hg': int(sc[0]), 'ag': int(sc[1]), 'e': end,
                      'p': [s.get(k) or '' for k in ('first_period', 'second_period', 'third_period', 'overtime')]})
    print('KHL сыграно матчей: %d (всего событий %d)' % (len(games), len(events)), flush=True)
    nxt = []
    for e in events:
        if e.get('game_state_key') == 'finished' or not msk(e.get('start_at') or 0).startswith(day):
            continue
        d = detail(e) or e
        b = dict(d.get('bets') or e.get('bets') or {})
        b.pop('url', None)
        x = {'d': msk(e.get('start_at')), 'id': e.get('id'), 'h': team(e.get('team_a')), 'a': team(e.get('team_b')), 'bets': b,
             'arena': d.get('arena') or d.get('location')}
        nxt.append(x)
        out('KHLNEXT', x)
        print('KHLPAIR %s—%s %s' % (x['h'], x['a'], json.dumps(d.get('this_pair_stat'), ensure_ascii=False)[:2500]), flush=True)
    nxt.sort(key=lambda x: x['d'])
    return games, nxt


if __name__ == '__main__':
    fetch(sys.argv[1])
