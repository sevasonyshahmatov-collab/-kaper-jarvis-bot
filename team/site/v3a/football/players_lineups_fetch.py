# -*- coding: utf-8 -*-
"""Составы и статистика игроков по сыгранным матчам 8 лиг: ESPN summary (rosters[].roster[]).
Вход: data/raw.json.gz (games: id, lg, st='post'). Выход: data/lineups.json.gz
  {event_id: {team_espn_id: [[athlete_id, starter, minutes|None, shots, sot, assists, fouls, yc, rc], ...]}}
  плюс '_n' {athlete_id: [имя, позиция]} и '_err' (список ошибок). Уже собранные матчи не перекачиваются. Разведка структуры — data/espn_summary_probe.json.
Минуты: если в stats есть minutes — они; иначе по замене (plays/keyEvents: время замены), иначе None.
Запуск в Actions (site-v3a-players.yml): python team/site/v3a/football/players_lineups_fetch.py"""
import gzip, json, os, re, time
from concurrent.futures import ThreadPoolExecutor
import requests

H = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(H, 'data/lineups.json.gz')
URL = 'https://site.api.espn.com/apis/site/v2/sports/soccer/%s/summary?event=%s'
raw = json.load(gzip.open(os.path.join(H, 'data/raw.json.gz')))
games = [g for g in raw['games'] if g['st'] == 'post']
old = {}
if os.path.exists(OUT):
    try: old = json.load(gzip.open(OUT))
    except Exception: old = {}
    if '_n' not in old: old = {}   # старый формат без имён — качаем заново
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'

def num(v):
    try: return float(v)
    except Exception: return 0.0

def clock_min(c):
    """'67\'' / '45\'+2' / dict -> минута (int)"""
    if isinstance(c, dict): c = c.get('displayValue') or c.get('value')
    if c is None: return None
    m = re.match(r"\s*(\d+)(?:'?\s*\+\s*(\d+))?", str(c))
    if not m: return None
    return int(m.group(1)) + int(m.group(2) or 0)

def get(url):
    for i in range(4):
        try:
            r = S.get(url, timeout=40)
            if r.status_code == 200: return r.json()
            if r.status_code == 404: raise RuntimeError('404')
        except RuntimeError: raise
        except Exception: pass
        time.sleep(2 + 3 * i)
    raise RuntimeError('fail')

def parse(j):
    subs = {}   # athlete_id -> {'in': min, 'out': min}
    for src in (j.get('keyEvents') or []) + (j.get('plays') or []):
        t = ((src.get('type') or {}).get('type') or (src.get('type') or {}).get('text') or '').lower()
        if 'substitution' not in t: continue
        m = clock_min(src.get('clock'))
        ps = src.get('participants') or []
        if m is None or len(ps) < 2: continue
        a_on = str((ps[0].get('athlete') or {}).get('id', '')); a_off = str((ps[1].get('athlete') or {}).get('id', ''))
        if a_on: subs.setdefault(a_on, {})['in'] = m
        if a_off: subs.setdefault(a_off, {})['out'] = m
    end = 90
    for src in (j.get('keyEvents') or []):
        m = clock_min(src.get('clock'))
        if m and m > end and m < 130: end = m
    res = {}; names = {}
    for ros in j.get('rosters') or []:
        tid = str((ros.get('team') or {}).get('id', ''))
        rows = []
        for e in ros.get('roster') or []:
            a = e.get('athlete') or {}; aid = str(a.get('id', ''))
            if not aid: continue
            st = {s.get('name'): s.get('value', s.get('displayValue')) for s in (e.get('stats') or [])}
            starter = 1 if e.get('starter') else 0
            sb_in = bool(e.get('subbedIn')) if not isinstance(e.get('subbedIn'), dict) else True
            played = starter or sb_in or num(st.get('appearances')) > 0
            if not played: continue
            names[aid] = [a.get('displayName') or a.get('fullName') or '', ((e.get('position') or a.get('position') or {}).get('abbreviation') or '')]
            mins = None
            if st.get('minutes') is not None: mins = int(num(st['minutes']))
            else:
                s = subs.get(aid, {})
                if starter: mins = min(s.get('out', end), end) if s else end
                elif 'in' in s: mins = max(0, (s.get('out', end)) - s['in'])
            rows.append([aid, starter, mins, int(num(st.get('totalShots'))), int(num(st.get('shotsOnTarget'))),
                         int(num(st.get('goalAssists'))), int(num(st.get('foulsCommitted'))),
                         int(num(st.get('yellowCards'))), int(num(st.get('redCards')))])
        res[tid] = rows
    return res, names

def work(g):
    try:
        j = get(URL % (g['lg'], g['id']))
        r, nm = parse(j)
        return g['id'], (r, nm), j, None
    except Exception as ex:
        return g['id'], None, None, '%s %s: %s' % (g['lg'], g['id'], ex)

todo = [g for g in games if g['id'] not in old]
print('матчей', len(games), 'к загрузке', len(todo), flush=True)
out = {k: v for k, v in old.items() if k != '_err'}; names = out.pop('_n', {}); errs = []; probed = False
with ThreadPoolExecutor(6) as ex:
    for n, (eid, r, j, er) in enumerate(ex.map(work, todo), 1):
        if er: errs.append(er)
        else:
            out[eid] = r[0]; names.update(r[1])
            if not probed and j.get('rosters'):
                probed = True
                ros = j['rosters'][0]
                pr = {'event': eid, 'top_keys': sorted(j), 'roster_keys': sorted(ros),
                      'roster0': (ros.get('roster') or [None])[0],
                      'roster_sub': next((e for e in ros.get('roster') or [] if not e.get('starter')), None),
                      'keyEvent_sub': next((k for k in j.get('keyEvents') or [] if 'sub' in json.dumps(k.get('type', '')).lower()), None),
                      'parsed': r[0]}
                json.dump(pr, open(os.path.join(H, 'data/espn_summary_probe.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        if n % 50 == 0: print(n, '/', len(todo), 'ошибок', len(errs), flush=True)
out['_n'] = names; out['_err'] = errs
with gzip.open(OUT, 'wt', encoding='utf-8') as f: json.dump(out, f, separators=(',', ':'))
rows = [x for k, v in out.items() if k not in ('_err', '_n') for t in v.values() for x in t]
print('матчей в файле', len(out) - 2, 'строк игроков', len(rows), 'с минутами', sum(1 for x in rows if x[2] is not None), 'ошибок', len(errs))
for e in errs[:10]: print(e)
