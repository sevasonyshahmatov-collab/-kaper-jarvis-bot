# Ответы ESPN scoreboard за 31.10 (eng.1, esp.1, ger.1) — только поля, которые читает бот (footEspnGames_), в лог.
import json, requests
for lg in ('eng.1', 'esp.1', 'ger.1'):
    for d in ('20261031',):
        j = requests.get('https://site.api.espn.com/apis/site/v2/sports/soccer/%s/scoreboard' % lg, params={'dates': d},
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=30).json()
        evs = [dict(id=e.get('id'), date=e.get('date'), competitions=[dict(status=dict(type={k: (c.get('status') or {}).get('type', {}).get(k) for k in ('state', 'name', 'completed')}),
               competitors=[dict(homeAway=t.get('homeAway'), score=t.get('score'), linescores=[dict(value=x.get('value')) for x in t.get('linescores') or []],
                                 team={k: (t.get('team') or {}).get(k) for k in ('displayName', 'shortDisplayName', 'name', 'location')}) for t in c.get('competitors') or []])
               for c in (e.get('competitions') or [])[:1]]) for e in j.get('events') or []]
        s = json.dumps(dict(events=evs), ensure_ascii=False, separators=(',', ':'))
        for i in range(0, len(s), 3000):
            print('ESPNDUMP %s %s %d %s' % (lg, d, i // 3000, s[i:i + 3000]), flush=True)
