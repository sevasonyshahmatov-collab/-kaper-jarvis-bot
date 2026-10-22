"""Сжатый вывод расчёта НХЛ на ночь на 23.10 (team/picks/day.py nhl 2026-10-22): по матчу — выбранная ставка (уточнённая
вероятность, модель, кэф) и пять ближайших вариантов; факты команд (TEAM/PER/LAST/NHLSTAND/NHLCLUB/H2H). Только чтение."""
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
r = subprocess.run([sys.executable, os.path.join(ROOT, 'team', 'picks', 'day.py'), 'nhl', '2026-10-22'], cwd=ROOT,
                   capture_output=True, text=True)
for line in r.stdout.splitlines():
    tag = line.split(' ', 1)[0]
    if tag == 'PICKJSON':
        j = json.loads(line.split(' ', 1)[1])
        pk = j.get('pick') or {}
        print('NB %s %s — %s | %s | %.1f%% (модель %.1f%%) кэф %s | 1X2 %s | итог %s' % (
            j['d'], j['h'], j['a'], pk.get('t'), 100 * (pk.get('p') or 0), 100 * (pk.get('p_model') or 0), pk.get('odds'),
            j.get('x1x2'), j.get('fin')), flush=True)
        for x in (j.get('top') or [])[:8]:
            if x.get('odds') and x['odds'] >= 1.55:
                print('NB    · %s %.1f%% кэф %.2f' % (x['t'], 100 * x['p'], x['odds']), flush=True)
    elif tag in ('TEAM', 'PER', 'LAST', 'NHLSTAND', 'NHLCLUB', 'NHLH2HPREV', 'H2H'):
        print('NF ' + line[:400], flush=True)
print('NB код %d, ошибки: %s' % (r.returncode, r.stderr[-500:]), flush=True)
