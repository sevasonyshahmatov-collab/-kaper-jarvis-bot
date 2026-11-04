import json, urllib.request
def get(u): return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30))
b = 'https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/'
for e in get(b + 'scoreboard?dates=20261103')['events']:
    n = e['name']
    if not any(t in n for t in ('Villa', 'Paris', 'Bodo', 'Atl')):
        continue
    try:
        s = get(b + 'summary?event=' + e['id'])
        for t in s['boxscore']['teams']:
            st = {x.get('name'): x.get('displayValue') for x in t.get('statistics', [])}
            print('UCLSHOTS', n, t['team']['displayName'], 'всего', st.get('totalShots'), 'в створ', st.get('shotsOnTarget'), flush=True)
    except Exception as ex:
        print('UCLSHOTSERR', n, ex, flush=True)
