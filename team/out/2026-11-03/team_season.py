# -*- coding: utf-8 -*-
"""Сборщик для страниц команд макета сайта v3a (владелец 03.11): все матчи сезона и игроки каждого клуба КХЛ и НХЛ.
Кладёт JSON в team/out/2026-11-03/season/season.mp4 (имя .mp4 — потому что itogi.yml сохраняет артефактом только mp4;
это обычный JSON). Запуск из корня репозитория, в задании: "make": ["team/out/2026-11-03/team_season.py"]."""
import gzip, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'picks'))
import requests  # noqa: E402
import teams  # noqa: E402
import khl_data  # noqa: E402

MSK = timezone(timedelta(hours=3))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'season')
os.makedirs(OUT, exist_ok=True)
res = {'khl': {}, 'nhl': {}, 'err': []}
S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0'
WEB = 'https://api-web.nhle.com/v1/'


def web(path):
    for k in range(3):
        try:
            r = S.get(WEB + path, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            if k == 2:
                res['err'].append('NHL %s: %r' % (path, e)); print('SEASONERR', path, repr(e), flush=True)
                return None
            time.sleep(1 + k)


def dflt(v):
    return v.get('default') if isinstance(v, dict) else v


# ── КХЛ: матчи (khl_data.fetch) и игроки (players_v2 по клубам)
try:
    day = datetime.now(MSK).strftime('%Y-%m-%d')
    games, _ = khl_data.fetch(day)
    for g in games:
        for me, op, home, gf, ga in ((g['h'], g['a'], 1, g['hg'], g['ag']), (g['a'], g['h'], 0, g['ag'], g['hg'])):
            res['khl'].setdefault(me, {'games': [], 'sk': [], 'gk': []})['games'].append(
                {'d': g['d'], 'o': op, 'h': home, 'gf': gf, 'ga': ga, 'x': g['e']})
    stage = khl_data.get('data.json').get('current_stage_id')
    for tid, name in teams.KHL_IDS.items():
        allp = []
        for page in range(1, 9):
            try:
                arr = khl_data.get('players_v2.json?stage_id=%s&q[team_id_eq]=%s&page=%d' % (stage, tid, page))
            except Exception as e:  # noqa: BLE001
                res['err'].append('KHLP %s %d: %r' % (tid, page, e)); break
            if not isinstance(arr, list) or not arr:
                break
            allp += [x.get('player') or x for x in arr]
            if len(arr) < 16:
                break
            time.sleep(0.2)
        d = res['khl'].setdefault(name, {'games': [], 'sk': [], 'gk': []})
        for p in allp:
            if ((p.get('team') or {}).get('id')) not in (tid, None):
                continue
            st = {s.get('id'): s.get('val') for s in p.get('stats') or []}
            if not st.get('gp'):
                continue
            role = str(p.get('role_key') or '')
            row = {'n': p.get('name'), 'no': p.get('shirt_number'), 'st': st}
            if 'goal' in role:
                d['gk'].append(row)
            else:
                row['pos'] = 'З' if 'def' in role else 'Н'
                d['sk'].append(row)
        print('SEASON КХЛ %s: матчей %d, полевых %d, вратарей %d' % (name, len(d['games']), len(d['sk']), len(d['gk'])), flush=True)
except Exception as e:  # noqa: BLE001
    res['err'].append('KHL: %r' % e); print('SEASONERR KHL', repr(e), flush=True)


# ── НХЛ: расписание клуба на сезон + статистика клуба + номера (roster)
def nhl_club(ab):
    name = teams.NHL_RU[ab]
    d = {'games': [], 'sk': [], 'gk': []}
    sch = web('club-schedule-season/%s/now' % ab) or {}
    for g in sch.get('games') or []:
        if g.get('gameType') != 2:
            continue
        h, a = g['homeTeam'], g['awayTeam']
        home = h.get('abbrev') == ab
        opp = a if home else h
        row = {'d': datetime.fromisoformat(g['startTimeUTC'].replace('Z', '+00:00')).astimezone(MSK).strftime('%Y-%m-%d %H:%M'),
               'o': teams.NHL_RU.get(opp.get('abbrev'), opp.get('abbrev')), 'h': 1 if home else 0}
        if g.get('gameState') in ('OFF', 'FINAL') and h.get('score') is not None:
            row['gf'], row['ga'] = (h['score'], a['score']) if home else (a['score'], h['score'])
            lp = (g.get('gameOutcome') or {}).get('lastPeriodType')
            row['x'] = 'ОТ' if lp == 'OT' else 'Б' if lp == 'SO' else ''
        d['games'].append(row)
    nums = {}
    ro = web('roster/%s/current' % ab) or {}
    for k in ('forwards', 'defensemen', 'goalies'):
        for p in ro.get(k) or []:
            nums[p.get('id')] = p.get('sweaterNumber')
    cs = web('club-stats/%s/now' % ab) or {}
    for p in cs.get('skaters') or []:
        d['sk'].append({'n': '%s %s' % (dflt(p.get('firstName')), dflt(p.get('lastName'))), 'no': nums.get(p.get('playerId')),
                        'pos': {'C': 'Ц', 'L': 'ЛН', 'R': 'ПН', 'D': 'З'}.get(p.get('positionCode'), p.get('positionCode')),
                        'gp': p.get('gamesPlayed'), 'g': p.get('goals'), 'a': p.get('assists'), 'pts': p.get('points'),
                        'pm': p.get('plusMinus'), 'pim': p.get('penaltyMinutes'), 'sog': p.get('shots'),
                        'toi': round(p.get('avgTimeOnIcePerGame') or 0)})
    for p in cs.get('goalies') or []:
        d['gk'].append({'n': '%s %s' % (dflt(p.get('firstName')), dflt(p.get('lastName'))), 'no': nums.get(p.get('playerId')),
                        'gp': p.get('gamesPlayed'), 'w': p.get('wins'), 'l': p.get('losses') , 'otl': p.get('overtimeLosses'),
                        'svp': p.get('savePercentage'), 'gaa': p.get('goalsAgainstAverage'), 'so': p.get('shutouts')})
    print('SEASON НХЛ %s: матчей %d, полевых %d, вратарей %d' % (name, len(d['games']), len(d['sk']), len(d['gk'])), flush=True)
    return name, d


with ThreadPoolExecutor(4) as ex:
    for name, d in ex.map(nhl_club, list(teams.NHL_RU)):
        res['nhl'][name] = d
res['built'] = datetime.now(MSK).strftime('%Y-%m-%d %H:%M')
with open(os.path.join(OUT, 'season.mp4'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
print('SEASONDONE', os.path.getsize(os.path.join(OUT, 'season.mp4')), 'байт; ошибок', len(res['err']), flush=True)
