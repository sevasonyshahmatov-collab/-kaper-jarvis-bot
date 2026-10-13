# -*- coding: utf-8 -*-
"""Данные НХЛ на ночь 13→14.10 из официального API (api-web.nhle.com, api.nhle.com/stats) — для роликов и описаний.
Облачная сессия до сайта НХЛ не достаёт, Actions — достаёт: скрипт печатает в лог строки «NHLDATA {json}», их читают из лога.
Ничего не рисует и никуда не шлёт; ошибка одного запроса — строка «NHLERR …», остальные данные всё равно печатаются.
Запуск: python team/out/2026-10-13/nhl_fetch.py [YYYY-MM-DD по ET, по умолчанию 2026-10-13]"""
import json
import sys

import requests

DAY = sys.argv[1] if len(sys.argv) > 1 else '2026-10-13'
SEASONS = ('20262027', '20252026')
WEB = 'https://api-web.nhle.com/v1/'
S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0'


def get(url):
    r = S.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def out(kind, obj):
    print('NHLDATA ' + json.dumps({'k': kind, 'd': obj}, ensure_ascii=False, separators=(',', ':')), flush=True)


def err(what, e):
    print('NHLERR %s: %r' % (what, e), flush=True)


def name(t):
    v = t.get('commonName') or t.get('name') or t.get('teamName') or {}
    return v.get('default') if isinstance(v, dict) else v


def main():
    games, teams = [], []
    try:
        sch = get(WEB + 'schedule/' + DAY)
        for w in sch.get('gameWeek', []):
            if w.get('date') != DAY:
                continue
            for g in w.get('games', []):
                h, a = g['homeTeam'], g['awayTeam']
                games.append(dict(id=g.get('id'), utc=g.get('startTimeUTC'), home=h['abbrev'], away=a['abbrev'],
                                  venue=(g.get('venue') or {}).get('default'), state=g.get('gameState'),
                                  home_name=name(h), away_name=name(a)))
                teams += [h['abbrev'], a['abbrev']]
        out('games', games)
    except Exception as e:                          # noqa: BLE001
        err('schedule', e)
    try:
        st = get(WEB + 'standings/now')
        rows = []
        for r in st.get('standings', []):
            ab = (r.get('teamAbbrev') or {}).get('default')
            if teams and ab not in teams:
                continue
            rows.append({k: r.get(k) for k in (
                'gamesPlayed', 'points', 'wins', 'losses', 'otLosses', 'regulationWins', 'goalFor', 'goalAgainst',
                'goalDifferential', 'leagueSequence', 'conferenceSequence', 'divisionSequence', 'conferenceName',
                'divisionName', 'streakCode', 'streakCount', 'homeWins', 'homeLosses', 'homeOtLosses', 'roadWins',
                'roadLosses', 'roadOtLosses', 'l10Wins', 'l10Losses', 'l10OtLosses', 'pointPctg')} | {'team': ab})
        out('standings', rows)
    except Exception as e:                          # noqa: BLE001
        err('standings', e)
    try:
        q = ('https://api.nhle.com/stats/rest/en/team/summary?isAggregate=false&isGame=false'
             '&cayenneExp=gameTypeId=2%20and%20seasonId=' + SEASONS[0])
        rows = [{k: r.get(k) for k in ('teamFullName', 'gamesPlayed', 'goalsForPerGame', 'goalsAgainstPerGame',
                                       'powerPlayPct', 'penaltyKillPct', 'shotsForPerGame', 'shotsAgainstPerGame',
                                       'faceoffWinPct', 'teamId')} for r in get(q).get('data', [])]
        out('summary', rows)
    except Exception as e:                          # noqa: BLE001
        err('summary', e)
    for ab in sorted(set(teams)):
        for season in SEASONS:
            try:
                gs = []
                for g in get(WEB + 'club-schedule-season/%s/%s' % (ab, season)).get('games', []):
                    if g.get('gameType') != 2 or g.get('gameState') not in ('OFF', 'FINAL'):
                        continue
                    h, a = g['homeTeam'], g['awayTeam']
                    gs.append([g.get('gameDate'), h['abbrev'], h.get('score'), a['abbrev'], a.get('score'),
                               (g.get('gameOutcome') or {}).get('lastPeriodType')])
                if season == SEASONS[0]:
                    out('games_' + ab, gs)
                else:                               # прошлый сезон — только встречи с сегодняшним соперником
                    opp = {x['away'] if x['home'] == ab else x['home'] for x in games if ab in (x['home'], x['away'])}
                    out('h2h_prev_' + ab, [x for x in gs if x[1] in opp or x[3] in opp])
            except Exception as e:                  # noqa: BLE001
                err('schedule %s %s' % (ab, season), e)
        try:
            cs = get(WEB + 'club-stats/%s/now' % ab)
            gl = [{k: (v.get('default') if isinstance(v, dict) else v) for k, v in x.items()
                   if k in ('firstName', 'lastName', 'gamesPlayed', 'gamesStarted', 'wins', 'savePercentage',
                            'goalsAgainstAverage', 'shutouts')} for x in cs.get('goalies', [])]
            sk = sorted(cs.get('skaters', []), key=lambda x: -(x.get('points') or 0))[:4]
            sk = [{k: (v.get('default') if isinstance(v, dict) else v) for k, v in x.items()
                   if k in ('firstName', 'lastName', 'gamesPlayed', 'goals', 'assists', 'points')} for x in sk]
            out('club_' + ab, {'goalies': gl, 'top': sk})
        except Exception as e:                      # noqa: BLE001
            err('club-stats %s' % ab, e)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:                          # noqa: BLE001 — задание не валим: данные читают из лога
        err('main', e)
