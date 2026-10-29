# -*- coding: utf-8 -*-
"""Сжатый расчёт дня для сессии (вывод day.py целиком — сотни строк): python team/picks/brief.py <khl|nhl> <день> [команда …]
По матчам (с фильтром по командам): выбор, все ставки с кэфом (исправленная вероятность / модель / кэф), факты команд.
Только чтение — ничего не отправляет."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
lg, day, flt = sys.argv[1], sys.argv[2], sys.argv[3:]
r = subprocess.run([sys.executable, os.path.join(ROOT, 'team', 'picks', 'day.py'), lg, day], cwd=ROOT, capture_output=True,
                   text=True)
TAGS = ('BRIEF', 'TEAM', 'PER', 'LAST', 'H2H', 'PAIR', 'KHLPAIR', 'NHLSTAND', 'NHLCLUB', 'NHLH2HPREV', 'NHLRATE', 'NHLGK', 'PINMISS')
for line in r.stdout.splitlines():
    tag = line.split(' ', 1)[0]
    if tag in TAGS and (not flt or any(t in line for t in flt)):
        print('BR ' + line[:500], flush=True)
print('BR код %d %s' % (r.returncode, r.stderr[-400:]), flush=True)
