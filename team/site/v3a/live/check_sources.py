# -*- coding: utf-8 -*-
"""Проверка источников живого счёта «как браузер»: запрос с Origin и preflight OPTIONS; пишет sources_report.json/.md."""
import json
import re
import time
from datetime import datetime, timedelta, timezone

import requests

ORIGIN = 'https://raw.githack.com'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36'
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/'
KHL = 'https://khl.api.webcaster.pro/api/khl_mobile/'
NHL = 'https://api-web.nhle.com/v1/'
now = datetime.now(timezone.utc)
rep = {'at': now.strftime('%Y-%m-%d %H:%M UTC'), 'origin': ORIGIN, 'items': []}


def probe(league, name, url):
    it = {'league': league, 'name': name, 'url': url}
    try:
        t = time.time()
        r = requests.get(url, headers={'Origin': ORIGIN, 'User-Agent': UA, 'Accept': 'application/json'}, timeout=30)
        it.update(code=r.status_code, ms=int((time.time() - t) * 1000), bytes=len(r.content),
                  acao=r.headers.get('Access-Control-Allow-Origin'), vary=r.headers.get('Vary'),
                  cache=r.headers.get('Cache-Control'), ctype=r.headers.get('Content-Type'))
        try:
            it['json'] = r.json()
        except Exception:  # noqa: BLE001
            it['json'] = None
    except Exception as e:  # noqa: BLE001
        it['error'] = repr(e)[:200]
    try:
        o = requests.options(url, headers={'Origin': ORIGIN, 'Access-Control-Request-Method': 'GET',
                                           'Access-Control-Request-Headers': 'accept', 'User-Agent': UA}, timeout=30)
        it['preflight'] = {'code': o.status_code, 'acao': o.headers.get('Access-Control-Allow-Origin'),
                           'methods': o.headers.get('Access-Control-Allow-Methods'),
                           'headers': o.headers.get('Access-Control-Allow-Headers')}
    except Exception as e:  # noqa: BLE001
        it['preflight'] = {'error': repr(e)[:200]}
    a = it.get('acao') or ''
    it['cors_simple_get'] = a == '*' or a == ORIGIN
    rep['items'].append(it)
    return it


def sample_espn(j):
    out = []
    for ev in (j or {}).get('events', [])[:3]:
        c = (ev.get('competitions') or [{}])[0]
        st = ev.get('status') or {}
        t = st.get('type') or {}
        out.append({'id': ev.get('id'), 'date': ev.get('date'), 'teams': [(x.get('team') or {}).get('abbreviation') for x in c.get('competitors', [])],
                    'score': [x.get('score') for x in c.get('competitors', [])], 'period': st.get('period'), 'clock': st.get('displayClock'),
                    'state': t.get('state'), 'detail': t.get('shortDetail')})
    return {'events': len((j or {}).get('events', [])), 'sample': out}


def sample_nhl(j):
    gs = (j or {}).get('games') or []
    out = []
    for g in gs[:3]:
        out.append({'id': g.get('id'), 'start': g.get('startTimeUTC'), 'state': g.get('gameState'), 'home': (g.get('homeTeam') or {}).get('abbrev'),
                    'away': (g.get('awayTeam') or {}).get('abbrev'), 'score': [(g.get('homeTeam') or {}).get('score'), (g.get('awayTeam') or {}).get('score')],
                    'period': (g.get('periodDescriptor') or {}).get('number'), 'clock': g.get('clock')})
    return {'games': len(gs), 'sample': out}


def sample_land(j):
    j = j or {}
    return {'id': j.get('id'), 'state': j.get('gameState'), 'period': (j.get('periodDescriptor') or {}).get('number'), 'clock': j.get('clock'),
            'home': (j.get('homeTeam') or {}).get('score'), 'away': (j.get('awayTeam') or {}).get('score')}


# ESPN
for lg, path in [('НХЛ', 'hockey/nhl'), ('АПЛ', 'soccer/eng.1'), ('Ла Лига', 'soccer/esp.1'), ('Серия А', 'soccer/ita.1'),
                 ('Бундеслига', 'soccer/ger.1'), ('Лига 1', 'soccer/fra.1'), ('РПЛ', 'soccer/rus.1'),
                 ('Лига чемпионов', 'soccer/uefa.champions'), ('Лига Европы', 'soccer/uefa.europa')]:
    it = probe(lg, 'ESPN scoreboard', ESPN + path + '/scoreboard')
    it['fields'] = sample_espn(it.pop('json', None))

# НХЛ API
it = probe('НХЛ', 'api-web score/now', NHL + 'score/now')
j = it.pop('json', None)
it['fields'] = sample_nhl(j)
gid = next((g['id'] for g in (j or {}).get('games', [])), None)
if gid:
    it = probe('НХЛ', 'api-web gamecenter landing', NHL + 'gamecenter/%s/landing' % gid)
    it['fields'] = sample_land(it.pop('json', None))
it = probe('НХЛ', 'api-web schedule/now', NHL + 'schedule/now')
it['fields'] = {'keys': list((it.pop('json', None) or {}).keys())[:8]}
it = probe('НХЛ', 'api.nhle.com stats team summary', 'https://api.nhle.com/stats/rest/en/team/summary?limit=2&cayenneExp=seasonId=20262027%20and%20gameTypeId=2')
it['fields'] = {'keys': list((it.pop('json', None) or {}).keys())[:8]}

# КХЛ
it = probe('КХЛ', 'khl.api.webcaster.pro data.json', KHL + 'data.json')
boot = it.pop('json', None) or {}
stage = boot.get('current_stage_id')
it['fields'] = {'stage': stage}
frm = int((now - timedelta(days=1)).timestamp())
to = int((now + timedelta(days=2)).timestamp())
q = ('events_v2.json?order_direction=asc&page=1&q%%5Bstart_at_gt_time_from_unixtime%%5D=%d&q%%5Bstart_at_lt_time_from_unixtime%%5D=%d&stage_id=%s' % (frm, to, stage))
it = probe('КХЛ', 'khl.api.webcaster.pro events_v2', KHL + q)
arr = it.pop('json', None) or []
evs = [w.get('event') or w for w in arr] if isinstance(arr, list) else []
it['fields'] = {'events': len(evs), 'sample': [{'id': e.get('id'), 'start_at': e.get('start_at'), 'state': e.get('game_state_key'), 'score': e.get('score'),
                                                  'a': (e.get('team_a') or {}).get('name'), 'b': (e.get('team_b') or {}).get('name')} for e in evs[:3]]}
pick = next((e for e in evs if e.get('game_state_key') not in ('finished', None) and e.get('game_state_key') != 'not_started'), None) or (evs[0] if evs else None)
if pick:
    it = probe('КХЛ', 'khl.api.webcaster.pro event_v2', KHL + 'event_v2.json?id=%s' % pick['id'])
    d = it.pop('json', None) or {}
    d = d.get('event') or d
    it['fields'] = {'id': d.get('id'), 'state': d.get('game_state_key'), 'score': d.get('score'), 'scores': d.get('scores'),
                    'period_keys': [k for k in d.keys() if re.search('period|time|minute|clock|state', k)]}
it = probe('КХЛ', 'khl.ru (сайт)', 'https://www.khl.ru/calendar/')
it.pop('json', None)
it['fields'] = {}

json.dump(rep, open('sources_report.json', 'w'), ensure_ascii=False, indent=1)
L = ['# Проверка источников живого счёта', '', 'Запуск: %s, Origin: `%s`' % (rep['at'], ORIGIN), '',
     '| Лига | Источник | HTTP | ACAO | Preflight (код / ACAO / methods) | Cache-Control | Размер | Задержка | CORS для GET |', '|---|---|---|---|---|---|---|---|---|']
for i in rep['items']:
    p = i.get('preflight') or {}
    L.append('| %s | %s | %s | %s | %s / %s / %s | %s | %s | %s мс | %s |' % (
        i['league'], i['name'], i.get('code', i.get('error')), i.get('acao'), p.get('code', p.get('error')), p.get('acao'), p.get('methods'),
        i.get('cache'), i.get('bytes'), i.get('ms'), 'да' if i.get('cors_simple_get') else 'нет'))
L += ['', '## Поля счёта (пример)', '']
for i in rep['items']:
    L.append('- **%s / %s**: `%s`' % (i['league'], i['name'], json.dumps(i.get('fields'), ensure_ascii=False)[:600]))
open('sources_report.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
