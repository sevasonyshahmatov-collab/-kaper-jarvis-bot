"""Проба 30.10: где взять ИСТОРИЮ кэфов на «обе забьют», таймы, угловые, карточки (вопрос владельца).
SofaScore (кэфы прошедших матчей), BetExplorer / OddsPortal (архив линий), BetBoom (доступ из Actions). Только лог."""
import json, re, urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
      'Accept': 'application/json, text/html;q=0.9,*/*;q=0.8', 'Accept-Language': 'en-US,en;q=0.9'}


def get(url, js=False):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            b = r.read()
            return r.status, (json.loads(b) if js else b.decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return 'ERR %s' % type(e).__name__, None


def sofa():
    for host in ('https://api.sofascore.com', 'https://www.sofascore.com'):
        for day in ('2026-10-25', '2025-03-08', '2023-10-21'):
            st, d = get('%s/api/v1/sport/football/scheduled-events/%s' % (host, day), js=True)
            print('SOFA', host, day, 'events', st, flush=True)
            if not d:
                continue
            ev = [e for e in d.get('events', []) if e.get('tournament', {}).get('uniqueTournament', {}).get('id') in (17, 8, 23, 35, 34)]
            ev = ev or d.get('events', [])[:1]
            for e in ev[:2]:
                st2, o = get('%s/api/v1/event/%s/odds/1/all' % (host, e['id']), js=True)
                mk = [m.get('marketName', '') + ('' if not m.get('choiceGroup') else ' ' + str(m['choiceGroup'])) for m in (o or {}).get('markets', [])]
                print('SOFA_ODDS', day, e['homeTeam']['name'], '-', e['awayTeam']['name'], st2, 'рынков', len(mk), '|', '; '.join(mk[:40]), flush=True)
            if ev:
                st3, s = get('%s/api/v1/event/%s/statistics' % (host, ev[0]['id']), js=True)
                names = sorted({i['name'] for p in (s or {}).get('statistics', []) for g in p.get('groups', []) for i in g.get('statisticsItems', [])})
                print('SOFA_STATS', day, st3, len(names), ', '.join(names[:25]), flush=True)
        # хватит одного рабочего хоста
        if st == 200:
            break


def betexplorer():
    st, h = get('https://www.betexplorer.com/football/england/premier-league-2024-2025/results/')
    ids = re.findall(r'/football/england/premier-league-2024-2025/[a-z0-9-]+/([A-Za-z0-9]{8})/', h or '')
    print('BETEXP results', st, 'матчей', len(set(ids)), flush=True)
    if ids:
        for mk in ('1x2', 'ou', 'bts', 'ha', 'ah', 'dc'):
            st2, j = get('https://www.betexplorer.com/match-odds/%s/1/%s/' % (ids[0], mk), js=True)
            body = (j or {}).get('odds', '') if isinstance(j, dict) else ''
            print('BETEXP odds', mk, st2, 'букм.', len(re.findall(r'data-bid', body)), 'кэфов', len(re.findall(r'data-odd=', body)), flush=True)


def oddsportal():
    st, h = get('https://www.oddsportal.com/football/england/premier-league-2024-2025/results/')
    print('ODDSPORTAL results', st, 'длина', len(h or ''), 'есть данные' if h and 'event' in h else '', flush=True)


def betboom():
    for u in ('https://betboom.ru/', 'https://betboom.ru/sport/football'):
        st, h = get(u)
        print('BETBOOM', u, st, 'длина', len(h or ''), flush=True)


for f in (sofa, betexplorer, oddsportal, betboom):
    try:
        f()
    except Exception as e:
        print(f.__name__, 'ошибка', repr(e)[:200], flush=True)
