# -*- coding: utf-8 -*-
"""football_day.py в Actions + строки FD* и FON* пометками запуска ::notice PB_i/n (логи Actions из облака закрыты).
    python team/picks/foot_notice.py 2026-11-01
Сборка: gh api .../check-runs/<job>/annotations → склеить PB_* по номеру → base64 -d | gunzip.
Пометок на шаг не больше 10 и до ~4 000 знаков в каждой — при нехватке места выпадают FDVS, FDSOT, FDWIDE."""
import base64, gzip, os, subprocess, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
day = sys.argv[1]
r = subprocess.run([sys.executable, os.path.join(ROOT, 'team/picks/football_day.py'), day], cwd=ROOT,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
sys.stdout.write(r.stdout)
fd = '\n'.join(l for l in r.stdout.split('\n') if l.startswith(('FD', 'FONMATCH', 'FONMISS', 'FONHTTP')) or 'Traceback' in l or 'Error' in l)
step = 3900
b = base64.b64encode(gzip.compress(fd.encode('utf-8'), 9)).decode()
for drop in ('FDVS', 'FDSOT', 'FDTEAM', 'FDWIDE'):
    if len(b) <= 9 * step:
        break
    fd = '\n'.join(l for l in fd.split('\n') if not l.startswith(drop))
    b = base64.b64encode(gzip.compress(fd.encode('utf-8'), 9)).decode()
parts = [b[i:i + step] for i in range(0, len(b), step)] or ['']
for i, s in enumerate(parts):
    print('::notice title=PB_%d/%d::%s' % (i + 1, len(parts), s), flush=True)
sys.exit(r.returncode)
