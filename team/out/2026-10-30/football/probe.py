# -*- coding: utf-8 -*-
"""Этап 0 футбола (ТЗ docs/handoff/FOOTBALL_BRIEF.md): какие источники отвечают из Actions. Печатает строки FP <источник> …"""
import json
import re
import requests

UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'}


def get(url, **kw):
    try:
        r = requests.get(url, headers=UA, timeout=25, **kw)
        return r.status_code, r.text
    except Exception as e:
        return 'ERR', repr(e)[:120]


def out(src, text):
    print('FP %s %s' % (src, text), flush=True)


# football-data.co.uk: CSV сезона, кэфы и закрытие Pinnacle
for code in ['E0', 'SP1', 'I1', 'D1', 'F1', 'P1']:
    for s in ['2122', '2526', '2627']:
        st, t = get('https://www.football-data.co.uk/mmz4281/%s/%s.csv' % (s, code))
        lines = t.splitlines() if st == 200 else []
        hdr = lines[0].split(',') if lines else []
        keep = [c for c in hdr if c.startswith(('PS', 'PC', 'Max', 'Avg', 'B365C', 'P>', 'PC>', 'AHC', 'HS', 'HST'))]
        out('fdco', '%s %s st=%s rows=%d cols=%d %s' % (code, s, st, max(0, len(lines) - 1), len(hdr), ' '.join(keep[:40])))
st, t = get('https://www.football-data.co.uk/fixtures.csv')
lines = t.splitlines() if st == 200 else []
out('fdco_fix', 'st=%s rows=%d hdr=%s' % (st, max(0, len(lines) - 1), lines[0][:300] if lines else t[:150]))
for l in lines[1:6]:
    out('fdco_fix', l[:200])

# ESPN scoreboard: лиги и еврокубки, есть ли кэфы
for lg in ['eng.1', 'esp.1', 'ita.1', 'ger.1', 'fra.1', 'por.1', 'uefa.champions', 'uefa.europa', 'uefa.europa.conf']:
    st, t = get('https://site.api.espn.com/apis/site/v2/sports/soccer/%s/scoreboard' % lg, params={'dates': '20261021-20261102'})
    try:
        j = json.loads(t)
        ev = j.get('events') or []
        odds = [c.get('odds') for e in ev for c in e.get('competitions', []) if c.get('odds')]
        o = json.dumps(odds[0][0], ensure_ascii=False)[:300] if odds else '-'
        out('espn', '%s st=%s events=%d with_odds=%d sample=%s' % (lg, st, len(ev), len(odds), o))
    except Exception as e:
        out('espn', '%s st=%s err=%r %s' % (lg, st, e, t[:80]))
# прошлые сезоны ЛЧ на ESPN
st, t = get('https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard', params={'dates': '20231001-20231031', 'limit': 300})
try:
    j = json.loads(t)
    ev = j.get('events') or []
    out('espn_hist', 'ЛЧ 10.2023 st=%s events=%d first=%s' % (st, len(ev), ev[0]['name'] if ev else '-'))
except Exception as e:
    out('espn_hist', 'err %r' % e)
# ESPN summary: статистика матча (удары) и кэфы
st, t = get('https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard', params={'dates': '20251021'})
try:
    eid = json.loads(t)['events'][0]['id']
    st2, t2 = get('https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/summary', params={'event': eid})
    j = json.loads(t2)
    out('espn_sum', 'st=%s keys=%s pickcenter=%s odds=%s' % (st2, ','.join(sorted(j.keys()))[:200],
        json.dumps(j.get('pickcenter'), ensure_ascii=False)[:250], json.dumps(j.get('odds'), ensure_ascii=False)[:200]))
    bs = (j.get('boxscore') or {}).get('teams') or []
    if bs:
        out('espn_sum', 'stats=' + ' '.join('%s:%s' % (s.get('name'), s.get('displayValue')) for s in bs[0].get('statistics', [])[:30]))
except Exception as e:
    out('espn_sum', 'err %r' % e)

# openfootball
for u in ['https://raw.githubusercontent.com/openfootball/football.json/master/2024-25/en.1.json',
          'https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/en.1.json',
          'https://raw.githubusercontent.com/openfootball/champions-league/master/2024-25/cl.txt']:
    st, t = get(u)
    out('openfb', '%s st=%s len=%d' % (u.split('master/')[1], st, len(t)))

# Understat: xG
for u in ['https://understat.com/league/EPL/2025', 'https://understat.com/getLeagueData/EPL/2025']:
    st, t = get(u, )
    has = 'datesData' in t or '"xG"' in t or 'xG' in t[:5000]
    out('understat', '%s st=%s len=%d xg=%s head=%s' % (u, st, len(t), has, re.sub(r'\s+', ' ', t[:120])))
st, t = get('https://understat.com/getLeagueData/EPL/2025', )
try:
    j = json.loads(t)
    out('understat', 'json keys=%s dates=%d' % (','.join(j.keys()), len(j.get('dates') or [])))
    d = (j.get('dates') or [{}])[0]
    out('understat', 'match=%s' % json.dumps(d, ensure_ascii=False)[:300])
except Exception as e:
    out('understat', 'getLeagueData not json: %r' % e)

# FBref
st, t = get('https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures')
out('fbref', 'st=%s len=%d xg=%s' % (st, len(t), 'xg' in t.lower()))

# ClubElo: общая шкала силы клубов Европы
st, t = get('http://api.clubelo.com/2025-10-01')
lines = t.splitlines() if st == 200 else []
out('clubelo', 'st=%s rows=%d hdr=%s top=%s' % (st, len(lines), lines[0] if lines else t[:100], ' | '.join(lines[1:4])))
st, t = get('http://api.clubelo.com/Fixtures')
lines = t.splitlines() if st == 200 else []
out('clubelo_fix', 'st=%s rows=%d hdr=%s' % (st, len(lines), lines[0][:200] if lines else t[:100]))
for l in lines[1:3]:
    out('clubelo_fix', l[:200])

# Линия на день без ключа
st, t = get('https://api.the-odds-api.com/v4/sports/')
out('oddsapi', 'без ключа st=%s %s' % (st, t[:120]))
st, t = get('https://v3.football.api-sports.io/status')
out('apifootball', 'без ключа st=%s %s' % (st, t[:120]))
HDR = dict(UA, Accept='application/json')
try:
    r = requests.get('https://guest.api.arcadia.pinnacle.com/0.1/sports/29/leagues?all=false', headers=HDR, timeout=25)
    out('pinnacle', 'leagues st=%s' % r.status_code)
    want = ('England - Premier League', 'Spain - La Liga', 'Italy - Serie A', 'Germany - Bundesliga', 'France - Ligue 1',
            'Portugal - Primeira Liga', 'Portugal - Liga Portugal', 'UEFA - Champions League', 'UEFA - Europa League',
            'UEFA - Conference League', 'UEFA - Europa Conference League')
    ids = {}
    for L in r.json():
        if L.get('name') in want or ('UEFA' in str(L.get('name')) and 'Women' not in str(L.get('name'))):
            ids[L['name']] = L['id']
            out('pinnacle', 'league %s = %s matchups=%s' % (L['id'], L['name'], L.get('matchupCount')))
    lid = ids.get('England - Premier League')
    if lid:
        mu = requests.get('https://guest.api.arcadia.pinnacle.com/0.1/leagues/%d/matchups' % lid, headers=HDR, timeout=25).json()
        mk = requests.get('https://guest.api.arcadia.pinnacle.com/0.1/leagues/%d/markets/straight' % lid, headers=HDR, timeout=25).json()
        main = [m for m in mu if not m.get('parentId')]
        out('pinnacle', 'EPL matchups=%d markets=%d types=%s' % (len(main), len(mk), sorted({(m.get('type'), m.get('period')) for m in mk})[:20]))
        if main:
            m = main[0]
            out('pinnacle', 'EPL first %s %s' % (m.get('startTime'), [p.get('name') for p in m.get('participants') or []]))
        tot = [m for m in mk if m.get('type') == 'total' and m.get('period') == 0][:1]
        out('pinnacle', 'EPL total sample %s' % json.dumps(tot, ensure_ascii=False)[:300])
except Exception as e:
    out('pinnacle', 'err %r' % e)
