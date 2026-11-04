# -*- coding: utf-8 -*-
"""Хоккей, сезон: матчи и игроки каждого клуба КХЛ и НХЛ → team/season.json (его читает team/build_data.py).
1) team_season.py из ветки команды (приложение КХЛ + api-web.nhle.com): сыгранные матчи, расписание НХЛ, игроки;
2) расписание КХЛ на ближайшие 3 недели (приложение КХЛ, khl_data.py команды) — несыгранные матчи с настоящим временем МСК."""
import json, os, sys, time
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def khl_schedule(days=21):
    sys.path.insert(0, os.path.join(C.TEAMCODE, 'team', 'picks'))
    import khl_data as K  # noqa: E402
    boot = K.get('data.json')
    stage = boot.get('current_stage_id')
    t0 = int(C.now_msk().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    t1 = t0 + days * 86400
    rows = []
    for page in range(1, 40):
        q = ('events_v2.json?order_direction=asc&page=%d&q%%5Bstart_at_gt_time_from_unixtime%%5D=%d'
             '&q%%5Bstart_at_lt_time_from_unixtime%%5D=%d&stage_id=%s' % (page, t0, t1, stage))
        arr = K.get(q)
        if not isinstance(arr, list) or not arr:
            break
        for w in arr:
            e = w.get('event') or w
            if e and e.get('type_id') in (18, 24) and e.get('game_state_key') != 'finished':
                rows.append(e)
        if len(arr) < 16:
            break
        time.sleep(0.2)
    out = []
    for e in rows:
        h, a = K.team(e.get('team_a')), K.team(e.get('team_b'))
        d = K.msk(e.get('start_at'))
        out.append((d, h, a))
    return out


def main():
    code_py = os.path.join(C.TEAMCODE, 'team', 'out', '2026-11-03', 'team_season.py')
    rc, _ = C.run([sys.executable, code_py], cwd=C.TEAMCODE, timeout=1500)
    res_path = os.path.join(C.TEAMCODE, 'team', 'out', '2026-11-03', 'season', 'season.mp4')
    s = C.jload(res_path)
    if not s or len(s.get('khl') or {}) < 20 or len(s.get('nhl') or {}) < 30:
        raise RuntimeError('team_season.py не дал полных данных (код %s, КХЛ %d, НХЛ %d) — season.json не меняю'
                           % (rc, len((s or {}).get('khl') or {}), len((s or {}).get('nhl') or {})))
    note = 'ошибок источника %d' % len(s.get('err') or [])
    try:
        sched = khl_schedule()
        for d, h, a in sched:
            if h in s['khl'] and a in s['khl']:
                s['khl'][h]['games'].append({'d': d, 'o': a, 'h': 1, 'gf': None, 'ga': None})
                s['khl'][a]['games'].append({'d': d, 'o': h, 'h': 0, 'gf': None, 'ga': None})
        note += '; расписание КХЛ: %d матчей' % len(sched)
        if not sched:
            note += ' (пусто)'
    except Exception as e:  # noqa: BLE001
        note += '; расписание КХЛ НЕ получено: %r' % e
    for lg in ('khl', 'nhl'):
        for d in s[lg].values():
            d['games'].sort(key=lambda g: g['d'])
    out = os.path.join(C.V3A, 'team', 'season.json')
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(s, f, ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, out)
    return note


if __name__ == '__main__':
    print(main())
