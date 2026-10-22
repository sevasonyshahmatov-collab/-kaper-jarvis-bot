"""Диагностика: почему 4 матча НХЛ 20.10 (19:00 по Нью-Йорку) не находятся в линии Pinnacle — печатает все матчи лиги 1456
с этими командами (parentId, units, startTime, день по Нью-Йорку, сопоставление команд) и число рынков. Ничего не шлёт."""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'team', 'picks'))
import requests  # noqa: E402
import pin  # noqa: E402
import teams  # noqa: E402

KEYS = ('Montreal', 'San Jose', 'New Jersey', 'Colorado', 'Islanders', 'Anaheim', 'Columbus', 'Toronto')
for lg in (1456,):
    mu = requests.get('%s/leagues/%d/matchups' % (pin.API, lg), headers=pin.HDR, timeout=30).json()
    mk = requests.get('%s/leagues/%d/markets/straight' % (pin.API, lg), headers=pin.HDR, timeout=30).json()
    cnt = {}
    for x in mk:
        cnt[x.get('matchupId')] = cnt.get(x.get('matchupId'), 0) + 1
    print('PROBE лига', lg, 'матчей', len(mu), 'рынков', len(mk), flush=True)
    for m in mu:
        names = [p.get('name') for p in m.get('participants') or []]
        if not any(k in str(n) for n in names for k in KEYS):
            continue
        side = {p.get('alignment'): p.get('name') for p in m.get('participants') or []}
        st = m.get('startTime')
        print('PROBE', m.get('id'), '| parent', m.get('parentId'), '| units', m.get('units'), '| type', m.get('type'),
              '| live', m.get('isLive'), '| status', m.get('status'), '|', st, '→ день NY', st and pin.local_day(st, 'nhl'),
              '|', side.get('home'), '→', teams.pin_team(side.get('home'), 'nhl'), '—', side.get('away'), '→',
              teams.pin_team(side.get('away'), 'nhl'), '| рынков', cnt.get(m.get('id'), 0), flush=True)
