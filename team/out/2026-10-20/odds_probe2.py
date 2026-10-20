"""Диагностика формата запасных линий НХЛ: полный JSON коэффициентов ESPN (scoreboard и summary/pickcenter) и
api-web.nhle.com partner-game по одному матчу дня. Ничего не шлёт."""
import json

import requests

H = {'User-Agent': 'Mozilla/5.0'}
j = requests.get('https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard', params={'dates': '20261021'},
                 headers=H, timeout=30).json()
ev = (j.get('events') or [])
print('ODDS2 ESPN событий 21.10:', len(ev), flush=True)
if ev:
    c = ev[0]['competitions'][0]
    print('ODDS2 ESPNSB', ev[0].get('shortName'), json.dumps(c.get('odds'), ensure_ascii=False)[:4000], flush=True)
    s = requests.get('https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary', params={'event': ev[0]['id']},
                     headers=H, timeout=30).json()
    print('ODDS2 ESPNPC', json.dumps(s.get('pickcenter'), ensure_ascii=False)[:4000], flush=True)
    print('ODDS2 ESPNODDS', json.dumps(s.get('odds'), ensure_ascii=False)[:2000], flush=True)
for cc in ('FI', 'SE', 'US'):
    r = requests.get('https://api-web.nhle.com/v1/partner-game/%s/now' % cc, headers=H, timeout=30).json()
    gs = r.get('games') or []
    print('ODDS2 NHL', cc, 'игр', len(gs), 'дни', sorted({g.get('startTimeUTC', '')[:10] for g in gs}), 'ключи', list(r)[:10],
          flush=True)
    if gs:
        print('ODDS2 NHLGAME', cc, json.dumps(gs[-1], ensure_ascii=False)[:3000], flush=True)
