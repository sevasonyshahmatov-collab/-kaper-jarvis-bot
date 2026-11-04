# -*- coding: utf-8 -*-
"""Футбол, сырьё для макета v3a (ESPN site.api.espn.com): клубы, таблицы, все матчи сезона 2026/27 (счёт, голы, карточки,
удары/угловые/владение), линии ESPN на ближайшие матчи. Копия team/out/2026-11-03/foot_season.py (ветка команды) для
ежедневного конвейера: пишет football/data/raw.json.gz напрямую; матчи прошлого сезона не перекачивает (берёт из старого
файла), эмблемы и логотипы не качает. Мало данных (<500 игр) — выход с ошибкой, старый файл не трогается."""
import base64, gzip, io, json, os, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
MSK = timezone(timedelta(hours=3))
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
B = 'https://site.api.espn.com/apis/site/v2/sports/soccer/'
LEAGUES = [('eng.1', 'epl', 'АПЛ'), ('esp.1', 'laliga', 'Ла Лига'), ('ita.1', 'seriea', 'Серия А'),
           ('ger.1', 'bundesliga', 'Бундеслига'), ('fra.1', 'ligue1', 'Лига 1'), ('rus.1', 'rpl', 'РПЛ'),
           ('uefa.champions', 'ucl', 'Лига чемпионов'), ('uefa.europa', 'uel', 'Лига Европы')]
CUPS = ('ucl', 'uel')
CUR = ['202607', '202608', '202609', '202610', '202611', '202612']
PRV = ['2025%02d' % m for m in range(7, 13)] + ['2026%02d' % m for m in range(1, 7)]
res = {'leagues': {}, 'teams': {}, 'games': [], 'prev': [], 'table': {}, 'err': []}


def get(url, params=None):
    for k in range(3):
        try:
            r = S.get(url, params=params, timeout=40)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (400, 404):
                return None
        except Exception as e:  # noqa: BLE001
            if k == 2:
                res['err'].append('%s %r' % (url, e)); print('FOOTERR', url, repr(e), flush=True)
        time.sleep(1 + k)
    return None


def msk(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(MSK).strftime('%Y-%m-%d %H:%M')


STAT = {'totalShots': 'sh', 'shotsOnTarget': 'sot', 'wonCorners': 'cor', 'possessionPct': 'pos', 'foulsCommitted': 'fl'}


def ev_row(lg, e, full):
    c = (e.get('competitions') or [{}])[0]
    cs = c.get('competitors') or []
    if len(cs) != 2:
        return None
    h = next((x for x in cs if x.get('homeAway') == 'home'), cs[0])
    a = next((x for x in cs if x is not h), cs[1])
    st = (c.get('status') or {}).get('type') or {}
    row = {'id': e.get('id'), 'lg': lg, 'd': msk(e['date']), 'h': h['team']['id'], 'a': a['team']['id'], 'st': st.get('state'),
           'sn': st.get('name')}
    if st.get('state') in ('post', 'in'):
        try:
            row['hs'], row['as'] = int(h.get('score')), int(a.get('score'))
        except (TypeError, ValueError):
            pass
    if not full:
        return row
    if st.get('state') == 'post':
        for side, x in (('hx', h), ('ax', a)):
            d = {}
            for s in x.get('statistics') or []:
                if s.get('name') in STAT:
                    try:
                        d[STAT[s['name']]] = float(s.get('displayValue'))
                    except (TypeError, ValueError):
                        pass
            row[side] = d
        gl, cd = [], []
        for x in c.get('details') or []:
            ath = (x.get('athletesInvolved') or [{}])[0]
            mn = (x.get('clock') or {}).get('displayValue')
            if x.get('scoringPlay') and not x.get('shootout'):
                gl.append([mn, (x.get('team') or {}).get('id'), ath.get('id'), ath.get('displayName'),
                           'og' if x.get('ownGoal') else 'pen' if x.get('penaltyKick') else ''])
            elif x.get('redCard') or x.get('yellowCard'):
                cd.append([mn, (x.get('team') or {}).get('id'), ath.get('id'), ath.get('displayName'), 'r' if x.get('redCard') else 'y'])
        row['g'] = gl; row['c'] = cd
    elif st.get('state') == 'pre':
        od = (c.get('odds') or [None])[0]
        if od:
            row['odds'] = od
    return row


def month(args):
    lg, m, full = args
    j = get(B + lg + '/scoreboard', {'dates': m, 'limit': 1000})
    rows = []
    for e in (j or {}).get('events') or []:
        try:
            r = ev_row(lg, e, full)
        except Exception as ex:  # noqa: BLE001
            res['err'].append('ev %s %r' % (e.get('id'), ex)); r = None
        if r:
            rows.append(r)
    print('FOOTMONTH', lg, m, len(rows), flush=True)
    return rows


for lg, key, ru in LEAGUES:
    j = get(B + lg + '/teams')
    lgj = j['sports'][0]['leagues'][0]
    lgl = (lgj.get('logos') or [{}])[0].get('href')
    res['leagues'][key] = {'espn': lg, 'ru': ru, 'logo': lgl, 'name': lgj.get('name'), 'ids': []}
    for t in lgj['teams']:
        t = t['team']
        lgo = [x['href'] for x in t.get('logos') or [] if 'default' in (x.get('rel') or [])]
        if key in CUPS and t['id'] in res['teams']:
            res['leagues'][key]['ids'].append(t['id']); continue
        res['teams'][t['id']] = {'id': t['id'], 'slug': t.get('slug'), 'n': t.get('displayName'), 's': t.get('shortDisplayName'),
                                 'ab': t.get('abbreviation'), 'c': t.get('color'), 'c2': t.get('alternateColor'), 'lg': key,
                                 'logo': lgo[0] if lgo else t.get('logo')}
        res['leagues'][key]['ids'].append(t['id'])
    j = get('https://site.api.espn.com/apis/v2/sports/soccer/%s/standings' % lg)
    rows = []
    for ch in (j or {}).get('children') or []:
        for e in ch['standings']['entries']:
            st = {s['name']: s.get('value') for s in e['stats']}
            rows.append({'id': e['team']['id'], 'rank': st.get('rank'), 'gp': st.get('gamesPlayed'), 'w': st.get('wins'),
                         'd': st.get('ties'), 'l': st.get('losses'), 'gf': st.get('pointsFor'), 'ga': st.get('pointsAgainst'),
                         'pts': st.get('points'), 'note': (e.get('note') or {}).get('description')})
    res['table'][key] = rows
    print('FOOTLG', lg, len(res['leagues'][key]['ids']), 'клубов,', len(rows), 'в таблице', flush=True)

PRV_OLD = None
_old = os.path.join(HERE, '..', 'football', 'data', 'raw.json.gz')
try:
    PRV_OLD = json.load(gzip.open(_old, 'rt', encoding='utf-8')).get('prev')   # прошлый сезон не меняется — не качаем заново
except Exception:  # noqa: BLE001
    PRV_OLD = None
jobs = [(lg, m, True) for lg, k, _ in LEAGUES for m in CUR + (['202701'] if k in CUPS else [])]
if not PRV_OLD:
    jobs += [(lg, m, False) for lg, k, _ in LEAGUES if k not in CUPS for m in PRV]
with ThreadPoolExecutor(6) as ex:
    out = list(ex.map(month, jobs))
for (lg, m, full), rows in zip(jobs, out):
    (res['games'] if full else res['prev']).extend(rows)
if PRV_OLD:
    res['prev'] = PRV_OLD
seen = set(); g2 = []
for r in res['games']:
    if r['id'] not in seen:
        seen.add(r['id']); g2.append(r)
res['games'] = g2
res['built'] = datetime.now(MSK).strftime('%Y-%m-%d %H:%M')
n_games = len(res['games'])
if n_games < 500 or len(res['teams']) < 100:
    raise SystemExit('FOOTFAIL мало данных: игр %d, клубов %d, ошибок %d' % (n_games, len(res['teams']), len(res['err'])))
OUT = os.path.join(HERE, '..', 'football', 'data', 'raw.json.gz')
tmp = OUT + '.tmp'
with gzip.open(tmp, 'wt', encoding='utf-8', compresslevel=9) as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
os.replace(tmp, OUT)
print('FOOTDONE игр', n_games, 'прошлый сезон', len(res['prev']), 'клубов', len(res['teams']), 'ошибок', len(res['err']), flush=True)
