# -*- coding: utf-8 -*-
"""Этап 0, проба 2: ESPN (дни, команды лиг по сезонам, кэфы в истории), ClubElo по https, Understat AJAX, fdco «extra»."""
import json
import requests

UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'}
E = 'https://site.api.espn.com/apis/site/v2/sports/soccer/'


def get(url, **kw):
    try:
        r = requests.get(url, headers=UA, timeout=25, **kw)
        return r.status_code, r.text
    except Exception as e:
        return 'ERR', repr(e)[:120]


def out(src, text):
    print('FQ %s %s' % (src, text), flush=True)


for lg, d in [('uefa.champions', '20231024'), ('uefa.europa', '20231026'), ('uefa.europa.conf', '20231026'),
              ('uefa.champions', '20220913'), ('uefa.champions', '20261021'), ('uefa.champions_qual', '20250722')]:
    st, t = get(E + lg + '/scoreboard', params={'dates': d})
    try:
        ev = json.loads(t).get('events') or []
        e = ev[0] if ev else {}
        c = (e.get('competitions') or [{}])[0]
        sc = [(x['team'].get('displayName'), x['team'].get('id'), x.get('score'), [l.get('value') for l in x.get('linescores') or []])
              for x in c.get('competitors', [])]
        out('espn_day', '%s %s st=%s ev=%d status=%s odds=%s %s' % (lg, d, st, len(ev), (e.get('status') or {}).get('type', {}).get('name'),
            bool(c.get('odds')), sc))
    except Exception as ex:
        out('espn_day', '%s %s st=%s err=%r %s' % (lg, d, st, ex, t[:100]))
st, t = get(E + 'uefa.champions/scoreboard', params={'dates': '202310'})
out('espn_month', 'st=%s %s' % (st, t[:80] if st != 200 else len(json.loads(t).get('events') or [])))
st, t = get(E + 'uefa.champions/scoreboard', params={'dates': '20231001-20231031', 'limit': 200})
out('espn_range', 'st=%s %s' % (st, t[:80] if st != 200 else len(json.loads(t).get('events') or [])))
# кэфы прошлого сезона в summary
st, t = get(E + 'uefa.europa/scoreboard', params={'dates': '20240307'})
try:
    for e in (json.loads(t).get('events') or [])[:2]:
        s2, t2 = get(E + 'uefa.europa/summary', params={'event': e['id']})
        j = json.loads(t2)
        out('espn_odds', '%s odds=%s pick=%s' % (e['name'], json.dumps(j.get('odds'), ensure_ascii=False)[:200],
            json.dumps(j.get('pickcenter'), ensure_ascii=False)[:200]))
except Exception as ex:
    out('espn_odds', 'err %r' % ex)
# команды лиги по сезонам
for lg in ['eng.1', 'ned.1', 'tur.1']:
    st, t = get(E + lg + '/teams', params={'season': 2023})
    try:
        tm = json.loads(t)['sports'][0]['leagues'][0]['teams']
        out('espn_teams', '%s 2023 st=%s n=%d %s' % (lg, st, len(tm), [x['team']['displayName'] for x in tm[:4]]))
    except Exception as ex:
        out('espn_teams', '%s st=%s err=%r' % (lg, st, ex))
# ClubElo
for u in ['https://api.clubelo.com/2025-10-01', 'http://api.clubelo.com/2024-10-01', 'http://api.clubelo.com/ManCity']:
    st, t = get(u)
    ls = t.splitlines()
    out('clubelo', '%s st=%s rows=%d %s' % (u, st, len(ls), ' | '.join(ls[:3])[:250]))
# Understat AJAX
for u, kw in [('https://understat.com/main/getLeagueData/EPL/2025', {}), ('https://understat.com/getLeagueData/EPL/2025', {'headers': dict(UA, **{'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://understat.com/league/EPL/2025'})})]:
    try:
        r = requests.get(u, timeout=25, **(kw or {'headers': UA}))
        out('understat', '%s st=%s len=%d %s' % (u, r.status_code, len(r.text), r.text[:150].replace('\n', ' ')))
    except Exception as ex:
        out('understat', 'err %r' % ex)
st, t = get('https://understat.com/league/EPL/2025')
import re
out('understat', 'scripts=%s' % re.findall(r'src="([^"]+\.js[^"]*)"', t)[:8])
out('understat', 'vars=%s' % re.findall(r'var (\w+)\s*=', t)[:10])
# fdco extra leagues (результаты всех сезонов одним файлом)
for c in ['AUT', 'SWZ', 'DNK', 'NOR', 'POL']:
    st, t = get('https://www.football-data.co.uk/new/%s.csv' % c)
    ls = t.splitlines()
    out('fdco_extra', '%s st=%s rows=%d hdr=%s last=%s' % (c, st, len(ls), ls[0][:120] if ls else '', ls[-1][:80] if ls else ''))
for c in ['N1', 'B1', 'T1', 'SC0', 'G1']:
    st, t = get('https://www.football-data.co.uk/mmz4281/2526/%s.csv' % c)
    ls = t.splitlines()
    out('fdco_more', '%s st=%s rows=%d psc=%s' % (c, st, len(ls), 'PSCH' in (ls[0] if ls else '')))
