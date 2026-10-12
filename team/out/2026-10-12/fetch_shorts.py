"""Готовые шортсы 12.10 (собраны с треками владельца в сессии руководителя) — из временной ветки claude/team-dev-shorts-1210
в team/out/2026-10-12/shorts/ для отправки владельцу. Ветка удаляется после отправки."""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, 'team', 'out', '2026-10-12', 'shorts')
os.makedirs(OUT, exist_ok=True)
subprocess.run(['git', 'fetch', '-q', '--depth', '1', 'origin', 'claude/team-dev-shorts-1210'], cwd=ROOT, check=True)
for name in ('coupon', 'top3', 'notify'):
    data = subprocess.run(['git', 'show', 'FETCH_HEAD:shorts/%s.mp4' % name], cwd=ROOT, check=True, capture_output=True).stdout
    with open(os.path.join(OUT, name + '.mp4'), 'wb') as f:
        f.write(data)
    print(name, len(data))
