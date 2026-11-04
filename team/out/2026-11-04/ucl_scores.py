import json, urllib.request
for d in ('20261103','20261104'):
    u='https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard?dates='+d
    try:
        j=json.load(urllib.request.urlopen(u,timeout=30))
    except Exception as e:
        print('UCLERR',d,e); continue
    for e in j.get('events',[]):
        c=e['competitions'][0]['competitors']
        print('UCLSCORE',d,e['date'],' | '.join('%s %s'%(x['team']['displayName'],x['score']) for x in c),e['status']['type']['description'],flush=True)
