# -*- coding: utf-8 -*-
"""Прогон football_day.py с выводом только блоков (FDMATCH/FDLINE/FONMATCH/FDFON/FDPROB/FDPICK) матчей по ключевым словам.
    python3 team/picks/foot_filter.py 2026-11-01 Liverpool "Real Madrid" """
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
day, keys = sys.argv[1], [k.lower() for k in sys.argv[2:]]
out = subprocess.run([sys.executable, os.path.join(HERE, 'football_day.py'), day], capture_output=True, text=True).stdout
show = False
for ln in out.split('\n'):
    t = ln.split(' ', 1)[0]
    if t == 'FDMATCH':
        show = any(k in ln.lower() for k in keys)
    if show and t in ('FDMATCH', 'FDLINE', 'FONMATCH', 'FDFON', 'FDPROB', 'FDPICK'):
        print('EXPQ', ln, flush=True)
print('EXPQDONE', flush=True)
