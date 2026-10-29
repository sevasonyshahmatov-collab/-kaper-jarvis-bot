# -*- coding: utf-8 -*-
"""Пересборка рейтинга НХЛ, проба 2: история кэфов ESPN, размеры файлов MoneyPuck, поля стартеров DailyFaceoff и протокола НХЛ."""
import json
import re
import signal
import requests

H = {'User-Agent': 'Mozilla/5.0 (jarvibet research)'}


def _alarm(*a):
    raise TimeoutError('hard')


signal.signal(signal.SIGALRM, _alarm)


def get(url, t=60, stream=False):
    signal.alarm(t + 10)
    try:
        return requests.get(url, headers=H, timeout=t, stream=stream)
    finally:
        signal.alarm(0)


def out(*a):
    print('SRC2', *a, flush=True)


# 1) ESPN: история кэфов по матчу
for d in ('20260310', '20251105'):
    try:
        ev = get(f'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates={d}').json()['events']
        eid = ev[0]['id']
        s = get(f'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary?event={eid}').json()
        out('espn_summary', d, 'keys=' + ','.join(s), 'pickcenter=' + json.dumps(s.get('pickcenter'), ensure_ascii=False)[:900],
            'odds=' + json.dumps(s.get('odds'), ensure_ascii=False)[:300])
        o = get(f'https://sports.core.api.espn.com/v2/sports/hockey/leagues/nhl/events/{eid}/competitions/{eid}/odds').json()
        out('espn_core_odds', d, json.dumps(o, ensure_ascii=False)[:900])
    except Exception as e:
        out('espn', d, 'ERR', e)

# 2) MoneyPuck: размеры и доступность
for u in ('https://moneypuck.com/moneypuck/playerData/seasonSummary/2026/regular/teams.csv',
          'https://moneypuck.com/moneypuck/playerData/seasonSummary/2026/regular/goalies.csv',
          'https://moneypuck.com/moneypuck/playerData/careers/gameByGame/all_teams.csv',
          'https://peter-tanner.com/moneypuck/downloads/shots_2025.zip',
          'https://peter-tanner.com/moneypuck/downloads/shots_2026.zip',
          'https://moneypuck.com/moneypuck/playerData/careers/gameByGame/regular/teams/COL.csv'):
    try:
        r = get(u, 90, stream=True)
        n, first = 0, b''
        for ch in r.iter_content(1 << 20):
            if not first:
                first = ch[:300]
            n += len(ch)
        tail = ''
        if u.endswith('COL.csv') or u.endswith('goalies.csv'):
            pass
        out('mp', r.status_code, u.split('/')[-1], f'{n / 1e6:.1f}MB', r.headers.get('last-modified'), first[:200])
    except Exception as e:
        out('mp', 'ERR', u.split('/')[-1], e)
try:
    t = get('https://moneypuck.com/moneypuck/playerData/careers/gameByGame/regular/teams/COL.csv', 90).text.splitlines()
    last = [x for x in t if ',2026,' in x[:20]]
    out('mp_col_2026', len(last), last[-1][:300] if last else '-')
    hdr = t[0].split(',')
    out('mp_cols', len(hdr), ','.join(hdr[:12]), '…', 'situations=' + ','.join(sorted({x.split(',')[9] for x in t[1:200]})))
except Exception as e:
    out('mp_col', 'ERR', e)

# 3) DailyFaceoff: поля стартера
try:
    r = get('https://www.dailyfaceoff.com/starting-goalies/2026-10-20')
    j = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S).group(1))
    g = j['props']['pageProps']['data'][0]
    out('dfo_keys', ','.join(k for k in g if 'Logo' not in k and 'Url' not in k and 'Color' not in k))
    out('dfo_vals', json.dumps({k: v for k, v in g.items() if re.search(r'Goalie(Name|Rating)|Strength|status|Status|news|date|Date|time', k)}, ensure_ascii=False)[:900])
except Exception as e:
    out('dfo', 'ERR', e)

# 4) Протокол НХЛ: вратари матча
try:
    sc = get('https://api-web.nhle.com/v1/score/2026-10-20').json()['games'][0]
    b = get(f'https://api-web.nhle.com/v1/gamecenter/{sc["id"]}/boxscore').json()
    gl = b['playerByGameStats']['homeTeam']['goalies']
    out('box_goalies', json.dumps(gl, ensure_ascii=False)[:800])
except Exception as e:
    out('box', 'ERR', e)
