"""Проба 30.10, круг 2: BetExplorer — архив кэфов по рынкам («обе забьют», таймы, тоталы) с заголовками AJAX. Только лог."""
import json, re, urllib.request

B = 'https://www.betexplorer.com'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'


def get(url, ref=None, ajax=False):
    h = {'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'}
    if ref:
        h['Referer'] = ref
    if ajax:
        h['X-Requested-With'] = 'XMLHttpRequest'
        h['Accept'] = 'application/json, text/javascript, */*; q=0.01'
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=25) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:
        return 'ERR', ''


for season in ('premier-league-2024-2025', 'premier-league-2019-2020'):
    st, h = get('%s/football/england/%s/results/' % (B, season))
    links = re.findall(r'href="(/football/england/%s/[a-z0-9-]+/([A-Za-z0-9]{8})/)"' % season, h)
    print('BETEXP', season, st, 'матчей', len(set(links)), flush=True)
    if not links:
        continue
    path, mid = links[0]
    page = B + path
    st, mh = get(page)
    print('MATCH', path, st, 'длина', len(mh), flush=True)
    for s in sorted(set(re.findall(r'["\'](/[a-z-]*odds[a-z-]*/[^"\']{0,60})["\']', mh)))[:10]:
        print('  ссылка в странице:', s, flush=True)
    for s in sorted(set(re.findall(r'data-(?:bettype|bt|mk|market)[a-z-]*="([^"]+)"', mh)))[:20]:
        print('  рынок в странице:', s, flush=True)
    tabs = sorted(set(re.findall(r'#(1x2|ou|ah|ha|dnb|dc|bts|cs|ht-ft|oe)\b', mh)))
    print('  вкладки:', tabs, flush=True)
    for pat in ('/match-odds/%s/1/%s/', '/match-odds-old/%s/1/%s/', '/match-odds/%s/1/%s/?t=1'):
        for mk in ('1x2', 'ou', 'bts', 'ht-ft'):
            st, j = get(B + pat % (mid, mk), ref=page, ajax=True)
            body = ''
            try:
                body = json.loads(j).get('odds', '') if j else ''
            except Exception:
                body = j
            n = len(re.findall(r'data-odd=', body))
            per = sorted(set(re.findall(r'(\d,\d\d|\d\.\d\d)', body)))[:3]
            print('  ', pat.split('/')[1], mk, st, 'кэфов', n, 'букм.', len(re.findall(r'in-bookmaker-logo-link|bookmaker', body)), per, flush=True)
