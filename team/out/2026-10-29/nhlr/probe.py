# -*- coding: utf-8 -*-
"""Пересборка рейтинга НХЛ (владелец 29.10), шаг 1: какие источники открыты из Actions. В лог — строки SRC."""
import json
import re
import signal
import requests


def _alarm(*a):
    raise TimeoutError('hard 30s')


signal.signal(signal.SIGALRM, _alarm)

H = {'User-Agent': 'Mozilla/5.0 (jarvibet research)'}
D = '2026-10-29'


def probe(name, url, show=None):
    signal.alarm(30)
    try:
        r = requests.get(url, headers=H, timeout=15)
        t = r.text
        extra = show(r) if (show and r.ok) else t[:160].replace('\n', ' ')
        print(f'SRC {name} {r.status_code} {len(t)}b {extra}', flush=True)
        return r
    except Exception as e:
        print(f'SRC {name} ERR {e}', flush=True)
    finally:
        signal.alarm(0)


def csvhead(r):
    lines = r.text.splitlines()
    return f'rows={len(lines)} head={lines[0][:400]} | {lines[1][:200] if len(lines) > 1 else ""}'


def keys(r):
    j = r.json()
    return 'keys=' + ','.join(list(j)[:25])


probe('nhl_standings', 'https://api-web.nhle.com/v1/standings/now', keys)
s = probe('nhl_score', f'https://api-web.nhle.com/v1/score/{D}', keys)
gid = None
try:
    gid = s.json()['games'][0]['id']
except Exception:
    pass
if gid:
    def land(r):
        j = r.json()
        m = j.get('matchup') or {}
        gc = m.get('goalieComparison') or {}
        return f'keys={",".join(j)[:300]} matchup={",".join(m)[:200]} gc={json.dumps(gc, ensure_ascii=False)[:700]}'
    probe('nhl_landing', f'https://api-web.nhle.com/v1/gamecenter/{gid}/landing', land)
    probe('nhl_rightrail', f'https://api-web.nhle.com/v1/gamecenter/{gid}/right-rail', keys)
probe('nhl_goalie_stats', 'https://api.nhle.com/stats/rest/en/goalie/summary?limit=3&cayenneExp=seasonId=20262027%20and%20gameTypeId=2',
      lambda r: json.dumps(r.json(), ensure_ascii=False)[:600])
probe('nhl_team_stats', 'https://api.nhle.com/stats/rest/en/team/summary?limit=2&cayenneExp=seasonId=20262027%20and%20gameTypeId=2',
      lambda r: json.dumps(r.json(), ensure_ascii=False)[:500])
for y in (2026, 2025):
    probe(f'mp_teams_{y}', f'https://moneypuck.com/moneypuck/playerData/seasonSummary/{y}/regular/teams.csv', csvhead)
    probe(f'mp_goalies_{y}', f'https://moneypuck.com/moneypuck/playerData/seasonSummary/{y}/regular/goalies.csv', csvhead)
probe('mp_team_gbg', 'https://moneypuck.com/moneypuck/playerData/careers/gameByGame/regular/teams/COL.csv', csvhead)
probe('mp_page', 'https://moneypuck.com/data.htm', lambda r: ' '.join(sorted(set(re.findall(r'href="([^"]+\.(?:csv|zip))"', r.text)))[:1500]))


def dfo(r):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        return 'no NEXT_DATA ' + r.text[:200].replace('\n', ' ')
    j = json.loads(m.group(1))
    pp = j.get('props', {}).get('pageProps', {})
    d = pp.get('data')
    first = d[0] if isinstance(d, list) and d else d
    return f'pageProps={",".join(pp)[:200]} n={len(d) if isinstance(d, list) else "-"} first={json.dumps(first, ensure_ascii=False)[:900]}'


probe('dfo_today', f'https://www.dailyfaceoff.com/starting-goalies/{D}', dfo)
probe('dfo_past', 'https://www.dailyfaceoff.com/starting-goalies/2026-10-20', dfo)
probe('nst', 'https://www.naturalstattrick.com/teamtable.php?fromseason=20262027&thruseason=20262027&stype=2&sit=5v5', lambda r: r.text[:120])


def espn(r):
    ev = r.json().get('events') or []
    if not ev:
        return 'no events'
    c = ev[0]['competitions'][0]
    return f'n={len(ev)} odds={json.dumps(c.get("odds"), ensure_ascii=False)[:900]}'


probe('espn_past_2026-03-10', 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates=20260310', espn)
probe('espn_past_2026-10-20', 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates=20261020', espn)
