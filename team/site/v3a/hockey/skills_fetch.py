# -*- coding: utf-8 -*-
"""Данные для пятиугольника навыков игрока (владелец 07.11): Катание, Бросок, Руки, Силовая, Оборона.
НХЛ: stats API (realtime — хиты, блоки, отборы, потери; summary — плюс-минус, реализация, штрафы, TOI; faceoffwins — вбрасывания)
+ NHL EDGE по игроку (макс. скорость, рывки 20+ миль/ч, сила броска) — только для игроков от 5 матчей, с паузой и таймаутом.
Результат — hockey/data/nhl_skills.json {id: {...}}; образцы ответов — в лог. Источник закрыт из облака: запуск в Actions.
Запуск из корня: python team/site/v3a/hockey/skills_fetch.py"""
import json, os, time
from concurrent.futures import ThreadPoolExecutor

import requests

H = os.path.dirname(os.path.abspath(__file__))
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
SEASON = '20262027'
ST = 'https://api.nhle.com/stats/rest/en/skater/'
CAY = '?limit=-1&cayenneExp=seasonId=%s%%20and%%20gameTypeId=2' % SEASON
err = []


def get(url, tries=3, tmo=30):
    for k in range(tries):
        try:
            r = S.get(url, timeout=tmo)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (404, 400):
                return None
        except Exception as e:  # noqa: BLE001
            if k == tries - 1:
                err.append('%s %r' % (url[-70:], e))
        time.sleep(1 + k)
    return None


def table(name):
    j = get(ST + name + CAY, 3, 90) or {}
    rows = j.get('data') or []
    print('SKILLS', name, 'rows', len(rows), 'sample', json.dumps(rows[0], ensure_ascii=False) if rows else None, flush=True)
    return {r['playerId']: r for r in rows if r.get('playerId')}


rt, sm, fo = table('realtime'), table('summary'), table('faceoffwins')
P = {}
for pid, c in sm.items():
    a, b = rt.get(pid, {}), fo.get(pid, {})
    P[pid] = {'gp': c.get('gamesPlayed'), 'pos': c.get('positionCode'), 'toi': c.get('timeOnIcePerGame'), 'pm': c.get('plusMinus'),
              'pim': c.get('penaltyMinutes'), 'sog': c.get('shots'), 'g': c.get('goals'), 'shp': c.get('shootingPct'),
              'hit': a.get('hits'), 'blk': a.get('blockedShots'), 'tk': a.get('takeaways'), 'gv': a.get('giveaways'),
              'fo': b.get('faceoffWinPct'), 'fon': b.get('totalFaceoffs')}


def num(v):
    """число из значения EDGE: число, либо словарь с imperial/value/..."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        for k in ('imperial', 'value', 'metric'):
            if k in v:
                x = num(v[k])
                if x is not None:
                    return x
        for x in v.values():
            y = num(x)
            if y is not None:
                return y
    return None


def find(o, *names):
    """первое значение по ключу, чьё имя (без регистра) содержит все части из names"""
    stack = [o]
    while stack:
        x = stack.pop(0)
        if isinstance(x, dict):
            for k, v in x.items():
                if all(n in k.lower() for n in names):
                    y = num(v)
                    if y is not None:
                        return y
            stack += list(x.values())
        elif isinstance(x, list):
            stack += x
    return None


shown = [0]


def paths(o, pre='', out=None):
    """пути к числовым полям ответа EDGE (без overlay / leagueAvg) — чтобы увидеть структуру в логе"""
    out = [] if out is None else out
    if isinstance(o, dict):
        for k, v in o.items():
            if k not in ('overlay', 'leagueAvg', 'player', 'team'):
                paths(v, pre + '.' + k, out)
    elif isinstance(o, (int, float)):
        out.append('%s=%s' % (pre, o))
    return out


def burst(j):
    """число рывков 20+ миль/ч за сезон: skatingSpeed.burstsOver20 (или похожее по имени)"""
    for k, v in (j.get('skatingSpeed') or {}).items():
        if 'burst' in k.lower() and '20' in k:
            return num(v)
    return find(j, 'burst', '20')


def edge(pid):
    time.sleep(0.15)
    j = None
    for path in ('%s/2' % SEASON, 'now'):
        j = get('https://api-web.nhle.com/v1/edge/skater-detail/%d/%s' % (pid, path), 2, 25)
        if j:
            break
    if not j:
        return pid, None
    if shown[0] < 2:
        shown[0] += 1
        print('SKILLS edge paths', pid, ' '.join(paths(j)), flush=True)
    return pid, {'spd': find(j, 'speedmax'), 'bur': burst(j), 'shot': find(j, 'topshotspeed')}


todo = [pid for pid, v in P.items() if (v.get('gp') or 0) >= 5]
print('SKILLS players', len(P), 'edge', len(todo), flush=True)
t0 = time.time()
with ThreadPoolExecutor(4) as ex:
    for pid, e in ex.map(edge, todo):
        if e:
            P[pid].update({k: v for k, v in e.items() if v is not None})
got = sum(1 for v in P.values() if 'spd' in v)
print('SKILLS edge got', got, 'errors', len(err), err[:5], 'sec', int(time.time() - t0), flush=True)
os.makedirs(os.path.join(H, 'data'), exist_ok=True)
with open(os.path.join(H, 'data', 'nhl_skills.json'), 'w', encoding='utf-8') as f:
    json.dump({'season': SEASON, 'p': {str(k): v for k, v in P.items()}, 'err': err[:30]}, f, ensure_ascii=False, separators=(',', ':'))
