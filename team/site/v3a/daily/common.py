# -*- coding: utf-8 -*-
"""Общее для ежедневного конвейера v3a: пути, время по Москве, журнал шагов, код команды (ветка команды)."""
import json, os, subprocess, sys, time
from datetime import datetime, timedelta, timezone

MSK = timezone(timedelta(hours=3))
HERE = os.path.dirname(os.path.abspath(__file__))
V3A = os.path.abspath(os.path.join(HERE, '..'))
DATA = os.path.join(V3A, 'data')
REPO = os.path.abspath(os.path.join(V3A, '..', '..', '..'))
TEAM_BRANCH = 'claude/project-migration-old-account-6e31vz'
TEAMCODE = os.environ.get('TEAMCODE') or '/tmp/teamcode'      # сюда распаковывается код команды (team/picks, render/football.py …)
LIVE = os.environ.get('LIVE_SITE') or '/tmp/live'               # клон живого сайта (app/data.json, data/*.json)

os.makedirs(DATA, exist_ok=True)


def now_msk():
    return datetime.now(MSK)


def jload(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def jsave(path, obj, js_var=None):
    """Запись атомарно; js_var — ещё и <имя>.js (window.<js_var>=…;) для открытия страницы с диска."""
    txt = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(txt)
    os.replace(tmp, path)
    if js_var:
        jp = path[:-2] if path.endswith('.json') else path + '.js'      # x.json → x.js
        with open(jp, 'w', encoding='utf-8') as f:
            f.write('window.%s=%s;\n' % (js_var, txt))


def msk_of_iso(s):
    """'2026-11-05T16:00:00Z' | epoch → datetime МСК"""
    if isinstance(s, (int, float)):
        return datetime.fromtimestamp(s, timezone.utc).astimezone(MSK)
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(MSK)


def match_key(lg, dt_msk, home_slug, away_slug):
    """Единый ключ матча во всех файлах: лига|дата МСК|хозяева|гости (daily/README.md)."""
    return '%s|%s|%s|%s' % (lg, dt_msk.strftime('%Y-%m-%d') if hasattr(dt_msk, 'strftime') else str(dt_msk)[:10], home_slug, away_slug)


def run(cmd, cwd=None, timeout=1500, env=None):
    """Подпроцесс с выводом в общий лог; → (код, вывод)."""
    e = dict(os.environ, PYTHONUNBUFFERED='1', **(env or {}))
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd or REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout, env=e)
    sys.stdout.write(p.stdout[-6000:] if len(p.stdout) > 6000 else p.stdout)
    print('[%s → код %d, %.0f с]' % (' '.join(str(x) for x in cmd)[:100], p.returncode, time.time() - t0), flush=True)
    return p.returncode, p.stdout
