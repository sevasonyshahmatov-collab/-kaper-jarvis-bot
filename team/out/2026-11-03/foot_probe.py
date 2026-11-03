# -*- coding: utf-8 -*-
"""Проба ESPN для футбольных страниц сайта v3a: форма ответов, в лог (FPROBE)."""
import json, requests
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
def show(tag, url, n=2500, params=None):
    try:
        r = S.get(url, params=params, timeout=30)
        s = r.text
        print('FPROBE', tag, r.status_code, len(s), flush=True)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        print('FPROBE', tag, 'ERR', repr(e), flush=True)
def p(tag, obj, n=2800):
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))[:n]
    print('FPROBE', tag, s, flush=True)
B = 'https://site.api.espn.com/apis/site/v2/sports/soccer/'
j = show('teams', B + 'eng.1/teams')
if j:
    ts = j['sports'][0]['leagues'][0]['teams']
    print('FPROBE nteams', len(ts), flush=True)
    t = ts[0]['team']; p('team0', {k: t.get(k) for k in ('id','slug','displayName','shortDisplayName','abbreviation','color','alternateColor','logos')})
    tid = t['id']
j = show('standings', 'https://site.api.espn.com/apis/v2/sports/soccer/eng.1/standings')
if j:
    ch = j['children'][0]; e = ch['standings']['entries'][0]
    p('standings0', {'t': e['team'].get('displayName'), 'id': e['team'].get('id'), 'stats': [(s['name'], s.get('value')) for s in e['stats']]})
j = show('scoreboard', B + 'eng.1/scoreboard', params={'dates': '20261031', 'limit': 100})
if j:
    ev = j['events']; print('FPROBE nev', len(ev), flush=True)
    c = ev[0]['competitions'][0]
    cc = dict(c); cc.pop('competitors', None)
    p('ev0keys', list(ev[0].keys())); p('comp0keys', list(c.keys()))
    p('details', c.get('details'), 1800)
    p('odds', c.get('odds'), 1200)
    p('comp0', [{k: v for k, v in x.items() if k not in ('team',)} for x in c['competitors']], 1800)
    p('status', c['status'], 500)
    p('teamobj', c['competitors'][0]['team'], 700)
j = show('schedule', B + 'eng.1/teams/%s/schedule' % tid)
if j:
    p('schedkeys', list(j.keys())); ev = j.get('events') or []; print('FPROBE nsched', len(ev), flush=True)
    if ev: p('sched0', ev[0], 1500)
for tag, u in (('roster', B + 'eng.1/teams/%s/roster' % tid), ('stats', B + 'eng.1/teams/%s/statistics' % tid),
               ('team', B + 'eng.1/teams/%s' % tid),
               ('leaders', 'https://site.web.api.espn.com/apis/site/v2/sports/soccer/eng.1/leaders'),
               ('cstats', 'https://site.web.api.espn.com/apis/common/v3/sports/soccer/eng.1/statistics/byathlete?limit=3'),
               ('cstatsT', 'https://site.web.api.espn.com/apis/common/v3/sports/soccer/eng.1/teams/%s/statistics' % tid),
               ('core', 'https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/seasons/2026/types/1/teams/%s/athletes?limit=3' % tid)):
    j = show(tag, u)
    if j: p(tag, j, 1500)
for lg in ('esp.1','ita.1','ger.1','fra.1','por.1','uefa.champions','rus.1','eng.2'):
    j = show('lg_'+lg, B + lg + '/teams')
    if j: print('FPROBE', lg, 'teams', len(j['sports'][0]['leagues'][0]['teams']), flush=True)
    j = show('lgs_'+lg, 'https://site.api.espn.com/apis/v2/sports/soccer/%s/standings' % lg)
    if j: print('FPROBE', lg, 'children', len(j.get('children') or []), j.get('children',[{}])[0].get('name'), flush=True)
