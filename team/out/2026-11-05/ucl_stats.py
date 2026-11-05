"""Счета и удары ЛЧ 04.11 (ESPN) для итогов опубликованных ставок."""
import json, urllib.request
def get(u): return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30))
b = 'https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/'
for e in get(b + 'scoreboard?dates=20261103')['events'] + get(b + 'scoreboard?dates=20261104')['events']:
    c = e['competitions'][0]['competitors']
    print('UCLSCORE', e['name'], '|', ' | '.join('%s %s %s' % (x['homeAway'], x['team']['displayName'], x['score']) for x in c),
          '|', e['status']['type']['description'], flush=True)
    try:
        s = get(b + 'summary?event=' + e['id'])
        for t in s['boxscore']['teams']:
            st = {x.get('name'): x.get('displayValue') for x in t.get('statistics', [])}
            print('UCLSHOTS', e['name'], '|', t['team']['displayName'], 'всего', st.get('totalShots'), 'в створ', st.get('shotsOnTarget'), flush=True)
    except Exception as ex:
        print('UCLSHOTSERR', e['name'], ex, flush=True)
