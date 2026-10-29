# -*- coding: utf-8 -*-
"""Проверка всего пути прогнозов НХЛ с новым рейтингом: day.py nhl <день>, в лог — только сводка DAYCHK."""
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
day = sys.argv[1]
r = subprocess.run([sys.executable, os.path.join(ROOT, 'team/picks/day.py'), 'nhl', day], cwd=ROOT, capture_output=True, text=True)
ls = r.stdout.splitlines()
print('DAYCHK код %d, строк %d, PAIR %d, из них новый рейтинг %d' % (
    r.returncode, len(ls), sum(l.startswith('PAIR ') for l in ls), sum(l.startswith('PAIR ') and 'новый рейтинг' in l for l in ls)))
for l in ls:
    if l.startswith(('NHLLIVEERR', 'PINERR', 'PINMISS', 'DAYJOB')) or (l.startswith('BRIEF') and ('ВЫБОР' in l or 'нет ставки' in l)):
        print('DAYCHK ' + l[:300])
print('DAYCHK stderr ' + r.stderr[-600:].replace('\n', ' | '))
