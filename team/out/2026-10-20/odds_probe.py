"""Диагностика запасных источников линии НХЛ на 20.10 (по Нью-Йорку): ESPN scoreboard (коэффициенты партнёра) и
NHL api-web partner-game (коэффициенты букмекеров-партнёров лиги). Печатает, что есть по каждому матчу. Ничего не шлёт."""
import json

import requests

H = {'User-Agent': 'Mozilla/5.0'}
try:
    j = requests.get('https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard', params={'dates': '20261020'},
                     headers=H, timeout=30).json()
    for e in j.get('events') or []:
        c = (e.get('competitions') or [{}])[0]
        print('ESPN', e.get('shortName'), e.get('date'), '|', json.dumps(c.get('odds'), ensure_ascii=False)[:700], flush=True)
except Exception as ex:  # noqa: BLE001
    print('ESPNERR', repr(ex), flush=True)
for cc in ('US', 'CA', 'SE', 'FI'):
    try:
        r = requests.get('https://api-web.nhle.com/v1/partner-game/%s/now' % cc, headers=H, timeout=30)
        j = r.json()
        print('NHLODDS', cc, r.status_code, 'партнёр', json.dumps(j.get('bookmaker') or j.get('partner'), ensure_ascii=False)[:200], flush=True)
        for g in j.get('games') or []:
            print('NHLODDS', cc, g.get('gameId'), (g.get('homeTeam') or {}).get('abbrev'), (g.get('awayTeam') or {}).get('abbrev'),
                  g.get('startTimeUTC'), '| home', json.dumps((g.get('homeTeam') or {}).get('odds'))[:300],
                  '| away', json.dumps((g.get('awayTeam') or {}).get('odds'))[:300], flush=True)
    except Exception as ex:  # noqa: BLE001
        print('NHLODDSERR', cc, repr(ex), flush=True)
