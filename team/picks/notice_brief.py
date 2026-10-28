# -*- coding: utf-8 -*-
"""day.py в Actions + сводка пометками запуска (хранилище логов Actions из облачной сессии закрыто, 28.10).
Запускает team/picks/day.py <лига> <день>, сохраняет вывод, делает parse_log.py → brief.md и matches.json, и печатает их
сжатыми (gzip + base64) кусками ::notice title=PB_<n>/<всего>:: — сессия читает через check-runs annotations.
    python team/picks/notice_brief.py nhl 2026-10-28
Сборка в сессии: gh api .../check-runs/<job>/annotations --paginate → склеить PB_* по номеру → base64 -d | tar xz."""
import base64
import io
import os
import subprocess
import sys
import tarfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
lg, day = sys.argv[1], sys.argv[2]
out = os.path.join(ROOT, 'out', 'picks', '%s-%s' % (lg, day))
os.makedirs(out, exist_ok=True)
log = os.path.join(out, 'day.log')
r = subprocess.run([sys.executable, os.path.join(ROOT, 'team/picks/day.py'), lg, day], cwd=ROOT,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
sys.stdout.write(r.stdout)
open(log, 'w', encoding='utf-8').write(r.stdout)
subprocess.run([sys.executable, os.path.join(ROOT, 'team/picks/parse_log.py'), log, out], cwd=ROOT)
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode='w:gz') as t:
    for n in ('brief.md', 'matches.json'):
        p = os.path.join(out, n)
        if os.path.exists(p):
            t.add(p, arcname=n)
b = base64.b64encode(buf.getvalue()).decode()
step = 3500
parts = [b[i:i + step] for i in range(0, len(b), step)] or ['']
for i, s in enumerate(parts):
    print('::notice title=PB_%d/%d::%s' % (i + 1, len(parts), s), flush=True)
sys.exit(r.returncode)
