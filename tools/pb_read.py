# -*- coding: utf-8 -*-
"""Собрать пометки ::notice PB_i/n запуска Actions (gzip+base64 текст) — логи из облака закрыты.
    python3 tools/pb_read.py <run_id> [PB|BZ] [> файл]   (PB — football_day / day.py, BZ — betzona.py)"""
import base64, gzip, json, re, subprocess, sys
R = 'https://api.github.com/repos/sevasonyshahmatov-collab/-kaper-jarvis-bot'
def j(u):
    return json.loads(subprocess.run(['curl', '-sS', '-m', '30', u], capture_output=True, text=True).stdout)
pre = sys.argv[2] if len(sys.argv) > 2 else 'PB'
parts = {}
for job in j('%s/actions/runs/%s/jobs' % (R, sys.argv[1])).get('jobs', []):
    for a in j('%s/check-runs/%s/annotations?per_page=100' % (R, job['id'])):
        m = re.match(pre + r'_(\d+)/(\d+)', a.get('title') or '')
        if m:
            parts[int(m.group(1))] = a['message']
b = ''.join(parts[k] for k in sorted(parts))
sys.stdout.write(gzip.decompress(base64.b64decode(b)).decode('utf-8') if b else 'нет пометок %s_\n' % pre)
