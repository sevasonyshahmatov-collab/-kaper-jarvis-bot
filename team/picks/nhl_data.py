# -*- coding: utf-8 -*-
"""НХЛ: сыгранные матчи регулярки этого сезона (со счётом по периодам) и матчи игрового дня из официального API НХЛ
(api-web.nhle.com — тот же источник, что у таблицы НХЛ). Облачная сессия до сайта НХЛ не достаёт, Actions — достаёт.
Печатает NHLNEXT (матч: время МСК, арена), NHLSTAND (официальная таблица: место в дивизионе/конференции/лиге, очки,
серия, последние 10, дома/в гостях), NHLCLUB (лучшие бомбардиры и вратари клуба), NHLH2HPREV (очные прошлого сезона).
День — игровой день НХЛ (дата по Нью-Йорку): матчи ночи на следующее число по Москве.
Отдельно: python team/picks/nhl_data.py 2026-10-15"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import requests

import teams

WEB = 'https://api-web.nhle.com/v1/'
MSK = timezone(timedelta(hours=3))
S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0'


def get(path):
    for k in range(3):
        try:
            r = S.get(WEB + path, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            if k == 2:
                raise
            print('NHLERR повтор %s: %r' % (path, e), flush=True)


def msk(iso):
    return datetime.fromisoformat(str(iso).replace('Z', '+00:00')).astimezone(MSK).strftime('%Y-%m-%d %H:%M')


def ru(ab):
    return teams.NHL_RU.get(ab, ab)


def dflt(v):
    return v.get('default') if isinstance(v, dict) else v


def season_games(start, day):
    """Сыгранные матчи регулярки с start по день до day (даты НХЛ)."""
    d0, d1 = date.fromisoformat(start), date.fromisoformat(day)
    days = [(d0 + timedelta(i)).isoformat() for i in range((d1 - d0).days)]
    with ThreadPoolExecutor(8) as ex:
        pages = list(ex.map(lambda d: get('score/' + d), days))
    games = []
    for pg in pages:
        for g in pg.get('games') or []:
            if g.get('gameType') != 2 or g.get('gameState') not in ('OFF', 'FINAL'):
                continue
            h, a = g['homeTeam'], g['awayTeam']
            per = [[0, 0] for _ in range(4)]
            for gl in g.get('goals') or []:
                pd = gl.get('periodDescriptor') or {}
                n = pd.get('number') or gl.get('period') or 0
                if pd.get('periodType') == 'SO' or n > 4 or n < 1:
                    continue
                side = 0 if dflt(gl.get('teamAbbrev')) == h['abbrev'] else 1
                per[n - 1][side] += 1
            end = {'OT': 'ОТ', 'SO': 'Б'}.get((g.get('gameOutcome') or {}).get('lastPeriodType'), '')
            games.append({'d': msk(g['startTimeUTC']), 'id': g.get('id'), 'h': ru(h['abbrev']), 'a': ru(a['abbrev']),
                          'hg': int(h.get('score') or 0), 'ag': int(a.get('score') or 0), 'e': end,
                          'p': ['%d:%d' % tuple(x) for x in per[:3]] + (['%d:%d' % tuple(per[3])] if end else [''])})
    games.sort(key=lambda x: x['d'])
    return games


def fetch(day):
    """→ (сыгранные матчи [{d, id, h, a, hg, ag, e, p}], матчи дня [{d, id, h, a, ab_h, ab_a, venue}])."""
    sch = get('schedule/' + day)
    start = sch.get('regularSeasonStartDate') or day
    print('NHL регулярка с %s, игровой день %s' % (start, day), flush=True)
    games = season_games(start, day)
    print('NHL сыграно матчей: %d' % len(games), flush=True)
    nxt = []
    for g in get('score/' + day).get('games') or []:
        if g.get('gameType') != 2 or g.get('gameState') not in ('FUT', 'PRE'):
            continue
        h, a = g['homeTeam']['abbrev'], g['awayTeam']['abbrev']
        x = {'d': msk(g['startTimeUTC']), 'id': g.get('id'), 'h': ru(h), 'a': ru(a), 'ab_h': h, 'ab_a': a,
             'venue': dflt(g.get('venue'))}
        nxt.append(x)
        print('NHLNEXT ' + json.dumps(x, ensure_ascii=False, separators=(',', ':')), flush=True)
    nxt.sort(key=lambda x: x['d'])
    abbrs = sorted({x['ab_h'] for x in nxt} | {x['ab_a'] for x in nxt})
    try:
        for r in get('standings/now').get('standings') or []:
            ab = dflt(r.get('teamAbbrev'))
            if ab not in abbrs:
                continue
            print('NHLSTAND %s | %s игр, %s очков (В %s, П %s, ПО %s; побед в осн. время %s), шайбы %s:%s | %s-е в дивизионе %s, '
                  '%s-е в конференции %s, %s-е в лиге | серия %s%s | последние 10: %s-%s-%s | дома %s-%s-%s, в гостях %s-%s-%s'
                  % (ru(ab), r.get('gamesPlayed'), r.get('points'), r.get('wins'), r.get('losses'), r.get('otLosses'),
                     r.get('regulationWins'), r.get('goalFor'), r.get('goalAgainst'), r.get('divisionSequence'),
                     dflt(r.get('divisionName')), r.get('conferenceSequence'), dflt(r.get('conferenceName')), r.get('leagueSequence'),
                     r.get('streakCode'), r.get('streakCount'), r.get('l10Wins'), r.get('l10Losses'), r.get('l10OtLosses'),
                     r.get('homeWins'), r.get('homeLosses'), r.get('homeOtLosses'), r.get('roadWins'), r.get('roadLosses'),
                     r.get('roadOtLosses')), flush=True)
    except Exception as e:  # noqa: BLE001
        print('NHLERR standings %r' % e, flush=True)

    def club(ab):
        try:
            cs = get('club-stats/%s/now' % ab)
            sk = sorted(cs.get('skaters') or [], key=lambda x: (-(x.get('points') or 0), -(x.get('goals') or 0)))[:4]
            gl = sorted(cs.get('goalies') or [], key=lambda x: -(x.get('gamesPlayed') or 0))[:2]
            return '%s | бомбардиры: %s | вратари: %s' % (
                ru(ab), ', '.join('%s %s %s (%s+%s) в %s играх' % (dflt(x.get('firstName')), dflt(x.get('lastName')), x.get('points'),
                                                                 x.get('goals'), x.get('assists'), x.get('gamesPlayed')) for x in sk),
                ', '.join('%s %s %s игр, побед %s, отражено %.1f%%, пропускает %.2f, на ноль %s' % (
                    dflt(x.get('firstName')), dflt(x.get('lastName')), x.get('gamesPlayed'), x.get('wins'),
                    100 * (x.get('savePercentage') or 0), x.get('goalsAgainstAverage') or 0, x.get('shutouts')) for x in gl))
        except Exception as e:  # noqa: BLE001
            return '%s | NHLERR %r' % (ru(ab), e)

    def prev(x):
        try:
            y = (int(day[:4]) if int(day[5:7]) >= 9 else int(day[:4]) - 1) - 1        # прошлый сезон y/y+1
            res = []
            for g in get('club-schedule-season/%s/%d%d' % (x['ab_h'], y, y + 1)).get('games') or []:
                if g.get('gameType') != 2 or g.get('gameState') not in ('OFF', 'FINAL'):
                    continue
                h, a = g['homeTeam'], g['awayTeam']
                if x['ab_a'] not in (h['abbrev'], a['abbrev']):
                    continue
                end = {'OT': ' ОТ', 'SO': ' Б'}.get((g.get('gameOutcome') or {}).get('lastPeriodType'), '')
                res.append('%s %s %s:%s %s%s' % (msk(g['startTimeUTC'])[:10], ru(h['abbrev']), h.get('score'), a.get('score'),
                                                 ru(a['abbrev']), end))
            return '%s—%s | сезон %d/%02d: %s' % (x['h'], x['a'], y, (y + 1) % 100, ' · '.join(res) or 'не играли')
        except Exception as e:  # noqa: BLE001
            return '%s—%s | NHLERR %r' % (x['h'], x['a'], e)

    with ThreadPoolExecutor(8) as ex:
        for line in ex.map(club, abbrs):
            print('NHLCLUB ' + line, flush=True)
        for line in ex.map(prev, nxt):
            print('NHLH2HPREV ' + line, flush=True)
    return games, nxt


if __name__ == '__main__':
    fetch(sys.argv[1])
