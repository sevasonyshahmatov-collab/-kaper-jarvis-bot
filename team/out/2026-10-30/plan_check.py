# -*- coding: utf-8 -*-
"""Проверка 30.10 (форы +1,5 в роликах): план роликов на день по старым (main до PR) и новым правилам pick.py — только лог,
владельцу ничего не уходит. python team/out/2026-10-30/plan_check.py <old|new|make> <khl|nhl> <день>"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.pop('TG_BOT_TOKEN', None)
if len(sys.argv) == 1:
    for lg in ('khl', 'nhl'):
        for mode in ('old', 'new', 'make'):
            print('=== CHECK %s %s' % (mode, lg), flush=True)
            r = subprocess.run([sys.executable, os.path.abspath(__file__), mode, lg, '2026-10-31'], cwd=ROOT)
            print('=== CHECK %s %s код %d' % (mode, lg, r.returncode), flush=True)
    sys.exit(0)
mode, league, day = sys.argv[1:4]
if mode == 'make':
    sys.exit(subprocess.run([sys.executable, 'team/reels_daily/make.py', 'plan', league, day, '--max', '0', '--per', '3'],
                            cwd=ROOT, env=dict(os.environ, PYTHONPATH='render')).returncode)
sys.path.insert(0, os.path.join(ROOT, 'team', 'picks'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'daily'))
if mode == 'old':
    sys.path.insert(0, os.path.join(ROOT, 'team', 'out', '2026-10-30', 'old'))
else:
    sys.path.insert(0, os.path.join(ROOT, 'team', 'reels_daily'))
import calc  # noqa: E402
import pick  # noqa: E402
import pin  # noqa: E402
if league == 'khl':
    import khl_data
    games, nxt = khl_data.fetch(day)
    fon = {(x['h'], x['a']): x.get('bets') for x in nxt}
else:
    import nhl_data
    games, nxt = nhl_data.fetch(day)
    fon = {}
if mode == 'new':
    live = __import__('khl_live' if league == 'khl' else 'nhl_live')
    calc.NHL_NEW, calc.NHL_WN = live.prepare(day, nxt), live.WN
pins, _ = pin.fetch(league, day, [(x['h'], x['a']) for x in nxt])
backup = set()
if league == 'nhl':
    import espn
    for k, mk in espn.fetch(day, [x for x in nxt if (x['h'], x['a']) not in pins]).items():
        pins[k] = mk
        backup.add(k)
ms = pick.day_picks(games, nxt, pins, fon, league, backup=backup)
n = sum(1 for m in ms if 'Фора' in m['pick'] and '+1,5' in m['pick'])
print('SUMMARY %s %s %s: матчей %d, роликов %d, фор +1,5 %d' % (mode, league, day, len(nxt), len(ms), n), flush=True)
