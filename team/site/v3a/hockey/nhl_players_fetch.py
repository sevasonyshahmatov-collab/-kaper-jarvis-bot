# -*- coding: utf-8 -*-
"""Игроки НХЛ для раздела «Игроки» (макет v3a, владелец 03.11): по каждому матчу регулярного сезона — голы, передачи,
броски, время на льду, штраф каждого полевого игрока; фото (headshot) и позиция из состава; следующий матч команды.
Источник — api-web.nhle.com (из облака закрыт, запуск в Actions: workflow site-v3a-players.yml).
Результат — hockey/data/nhl_players.json (коммит в ту же ветку). Запуск из корня: python team/site/v3a/hockey/nhl_players_fetch.py"""
import json, os, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

MSK = timezone(timedelta(hours=3))
H = os.path.dirname(os.path.abspath(__file__))
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
W = 'https://api-web.nhle.com/v1/'
err = []


def get(path):
    for k in range(4):
        try:
            r = S.get(W + path, timeout=45)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
        except Exception as e:  # noqa: BLE001
            if k == 3:
                err.append('%s %r' % (path, e))
        time.sleep(1 + k)
    return None


def msk(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(MSK).strftime('%Y-%m-%d %H:%M')


def toi(s):
    try:
        m, c = str(s).split(':'); return int(m) * 60 + int(c)
    except Exception:  # noqa: BLE001
        return 0


st = get('standings/now') or {}
TEAMS = sorted({r['teamAbbrev']['default'] for r in st.get('standings') or []})
print('NHLP teams', len(TEAMS), flush=True)


def club(ab):
    sch = get('club-schedule-season/%s/now' % ab) or {}
    ro = get('roster/%s/current' % ab) or {}
    return ab, sch.get('games') or [], ro


games, nxt, roster = {}, {}, {}
with ThreadPoolExecutor(6) as ex:
    for ab, gs, ro in ex.map(club, TEAMS):
        for g in gs:
            if g.get('gameType') != 2:
                continue
            if g.get('gameState') in ('OFF', 'FINAL'):
                games[g['id']] = g
            elif ab not in nxt or g['startTimeUTC'] < nxt[ab]['t']:
                h, a = g['homeTeam']['abbrev'], g['awayTeam']['abbrev']
                nxt[ab] = {'t': g['startTimeUTC'], 'd': msk(g['startTimeUTC']), 'o': a if h == ab else h, 'h': int(h == ab)}
        for k in ('forwards', 'defensemen', 'goalies'):
            for p in ro.get(k) or []:
                roster[p['id']] = {'n': '%s %s' % ((p.get('firstName') or {}).get('default', ''), (p.get('lastName') or {}).get('default', '')), 't': ab, 'img': p.get('headshot'), 'no': p.get('sweaterNumber'), 'pos': p.get('positionCode')}
print('NHLP games', len(games), 'roster', len(roster), flush=True)


def box(gid):
    return gid, get('gamecenter/%d/boxscore' % gid)


# статистика сыгранных матчей — с 11.11 (владелец: «старые можно не заполнять»). Сначала сводка лиги (gamecenter/<id>/right-rail,
# teamGameStats), чего там нет — суммой по игрокам из протокола. Ключ — nhl|дата МСК|HOME|AWAY (сокращения лиги; в slug переводит сборщик страниц).
MS_FROM = '2026-11-10'    # 10.11 — для проверки на уже сыгранных матчах
MST = {}
RR = {'sog': 'sog', 'pim': 'pim', 'hits': 'hit', 'blockedShots': 'blk', 'giveaways': 'gv', 'takeaways': 'tk', 'faceoffWinningPctg': 'fo', 'powerPlay': 'pp'}
BX = {'sog': 'sog', 'pim': 'pim', 'hits': 'hit', 'blockedShots': 'blk', 'giveaways': 'gv', 'takeaways': 'tk', 'powerPlayGoals': 'ppg'}


def mstat(gid, b, pg):
    out = {'h': {}, 'a': {}}
    for side, k in (('homeTeam', 'h'), ('awayTeam', 'a')):
        for grp in ('forwards', 'defense', 'goalies'):
            for p in (pg.get(side) or {}).get(grp) or []:
                for src, dst in BX.items():
                    if isinstance(p.get(src), (int, float)) and not (grp == 'goalies' and src != 'pim'):
                        out[k][dst] = out[k].get(dst, 0) + p[src]
        if isinstance((b.get(side) or {}).get('sog'), int):
            out[k]['sog'] = b[side]['sog']
    rr = get('gamecenter/%d/right-rail' % gid) or {}
    for x in rr.get('teamGameStats') or []:
        dst = RR.get(x.get('category'))
        if dst:
            for k, v in (('h', x.get('homeValue')), ('a', x.get('awayValue'))):
                if v is not None:
                    out[k][dst] = v
    return out


P = {}
with ThreadPoolExecutor(8) as ex:
    for gid, b in ex.map(box, sorted(games)):
        if not b:
            continue
        g = games[gid]
        d = msk(g['startTimeUTC'])
        pg = b.get('playerByGameStats') or {}
        if d[:10] >= MS_FROM:                            # статистика матча для страницы сыгранного матча (владелец 11.11)
            try:
                MST['nhl|%s|%s|%s' % (d[:10], b['homeTeam']['abbrev'], b['awayTeam']['abbrev'])] = mstat(gid, b, pg)
            except Exception as x:  # noqa: BLE001
                err.append('mstats %s %r' % (gid, x))
        for side, home in (('homeTeam', 1), ('awayTeam', 0)):
            me = b[side]['abbrev']; op = b['awayTeam' if home else 'homeTeam']['abbrev']
            for grp in ('forwards', 'defense'):
                for p in (pg.get(side) or {}).get(grp) or []:
                    pid = p['playerId']
                    r = P.setdefault(pid, {'id': pid, 'n': (p.get('name') or {}).get('default', ''), 'pos': p.get('position'), 'log': []})
                    r['log'].append([d, me, op, home, p.get('goals', 0), p.get('assists', 0), p.get('sog', 0), toi(p.get('toi')),
                                     p.get('pim', 0)])

out = []
for pid, r in P.items():
    r['log'].sort()
    ro = roster.get(pid, {})
    r['t'] = ro.get('t') or r['log'][-1][1]
    r['img'] = ro.get('img'); r['n'] = ro.get('n') or r['n']; r['no'] = ro.get('no'); r['pos'] = ro.get('pos') or r['pos']
    out.append(r)
GIMG = {}  # фото вратарей {клуб: {имя: фото}} — для карточки «Лучший вратарь» на странице клуба
for r_ in roster.values():
    if r_.get('pos') == 'G' and r_.get('img'):
        GIMG.setdefault(r_['t'], {})[r_['n'].strip()] = r_['img']
res = {'built': datetime.now(MSK).strftime('%Y-%m-%d %H:%M'), 'season': '2026/27', 'next': nxt, 'players': out, 'gimg': GIMG, 'err': err[:30],
       'cols': ['d', 'team', 'opp', 'home', 'g', 'a', 'sog', 'toi_sec', 'pim']}
os.makedirs(os.path.join(H, 'data'), exist_ok=True)
with open(os.path.join(H, 'data', 'nhl_players.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
print('NHLP players', len(out), 'errors', len(err), flush=True)
try:                                                     # hockey/data/nhl_mstats.json: прежние матчи остаются, новые добавляются
    f_ms = os.path.join(H, 'data', 'nhl_mstats.json')
    old = json.load(open(f_ms, encoding='utf-8')) if os.path.exists(f_ms) else {}
    old.update(MST)
    with open(f_ms, 'w', encoding='utf-8') as f:
        json.dump(old, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    print('NHLP mstats', len(MST), 'всего', len(old), flush=True)
except Exception as x:  # noqa: BLE001
    print('NHLP mstats ошибка %r' % x, flush=True)
