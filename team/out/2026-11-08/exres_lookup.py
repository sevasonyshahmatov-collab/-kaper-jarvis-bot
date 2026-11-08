"""Разово (08.11): номера постов экспрессов 07.11 в канале (t.me/s/jarvibet) и счета ног. Только печатает LOOKUP-строки."""
import re, html, requests
H = {'User-Agent': 'Mozilla/5.0'}
seen = {}
before = None
for _ in range(6):
    url = 'https://t.me/s/jarvibet' + ('?before=%d' % before if before else '')
    try:
        t = requests.get(url, headers=H, timeout=30).text
    except Exception as e:
        print('LOOKUP ERR', e, flush=True); break
    posts = re.findall(r'data-post="jarvibet/(\d+)"(.*?)(?=data-post="jarvibet/|\Z)', t, re.S)
    if not posts: print('LOOKUP пусто', url, flush=True); break
    for n, body in posts:
        m = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', body, re.S)
        txt = html.unescape(re.sub(r'<br\s*/?>', ' / ', re.sub(r'<(?!br)[^>]+>', '', m.group(1)))) if m else ''
        seen[int(n)] = txt
    before = min(int(n) for n, _ in posts)
    if before < 1440: break
for n in sorted(seen):
    if n >= 1455:
        print('LOOKUP POST %d | %s' % (n, seen[n][:300]), flush=True)
for lg in ('ger.1', 'ita.1', 'esp.1'):
    try:
        r = requests.get('https://site.api.espn.com/apis/site/v2/sports/soccer/%s/scoreboard?dates=20261107' % lg, headers=H, timeout=30).json()
        for e in r.get('events', []):
            c = e['competitions'][0]['competitors']
            h = [x for x in c if x['homeAway'] == 'home'][0]; a = [x for x in c if x['homeAway'] == 'away'][0]
            print('LOOKUP FOOT', lg, h['team']['displayName'], h['score'], ':', a['score'], a['team']['displayName'], e['status']['type']['name'], flush=True)
    except Exception as ex:
        print('LOOKUP FOOT ERR', lg, ex, flush=True)
try:
    for g in requests.get('https://api-web.nhle.com/v1/score/2026-11-07', headers=H, timeout=30).json().get('games', []):
        print('LOOKUP NHL', g['homeTeam']['abbrev'], g['homeTeam'].get('score'), ':', g['awayTeam'].get('score'), g['awayTeam']['abbrev'],
              g.get('gameState'), (g.get('gameOutcome') or {}).get('lastPeriodType'), flush=True)
except Exception as ex:
    print('LOOKUP NHL ERR', ex, flush=True)
