"""Проба 31.10 (владелец: «пробуем Фонбет, котировки нужны максимально точно»): отвечает ли открытая выгрузка линии
Фонбета серверам Actions, есть ли КХЛ/НХЛ (и футбол), сколько рынков на матч. Обычный GET открытого JSON, без обходов. Только лог."""
import json, urllib.request

HOSTS = ['https://line%02d.bkfon-resources.com' % i for i in (1, 2, 4, 6, 12)] + \
        ['https://line-lb51-w.bk6bba-resources.com', 'https://line-lb61-w.bk6bba-resources.com']
PATHS = ['/events/list?lang=ru&version=0&scopeMarket=1600', '/line/desktop/topEvents3?place=line&sysId=1&lang=ru']


def get(url):
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'jarvis-probe/1.0'})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return 'ERR %s' % type(e).__name__, None


data = None
for h in HOSTS:
    for p in PATHS:
        st, d = get(h + p)
        print('FON', h + p, st, (list(d.keys())[:8] if isinstance(d, dict) else ''), flush=True)
        if isinstance(d, dict) and d.get('events'):
            data = d
            break
    if data:
        break

if data:
    sports = {s['id']: s for s in data.get('sports', [])}
    leagues = [s for s in sports.values() if any(k in (s.get('name') or '') for k in ('КХЛ', 'НХЛ', 'Англия. Премьер', 'Испания. Примера', 'Италия. Серия A', 'Германия. Бундеслига', 'Франция. Лига 1', 'Лига чемпионов'))]
    for s in leagues[:12]:
        print('FONLEAGUE', s['id'], s.get('name'), flush=True)
    ids = {s['id'] for s in leagues}
    evs = [e for e in data['events'] if e.get('sportId') in ids and e.get('level', 1) == 1]
    print('FONEVENTS всего', len(data['events']), 'наших матчей', len(evs), flush=True)
    facs = {}
    for f in data.get('customFactors', []):
        facs[f.get('e')] = f.get('factors', [])
    subs = {}
    for e in data['events']:
        if e.get('parentId'):
            subs.setdefault(e['parentId'], []).append(e)
    for e in evs[:6]:
        sub = subs.get(e['id'], [])
        n = len(facs.get(e['id'], [])) + sum(len(facs.get(x['id'], [])) for x in sub)
        print('FONMATCH', sports[e['sportId']].get('name'), '|', e.get('team1'), '—', e.get('team2'), '| start', e.get('startTime'),
              '| рынков-коэффициентов', n, '| подсобытия:', ', '.join(sorted({str(x.get('name')) for x in sub}))[:200], flush=True)
        print('   основные:', json.dumps(facs.get(e['id'], [])[:30], ensure_ascii=False)[:900], flush=True)
