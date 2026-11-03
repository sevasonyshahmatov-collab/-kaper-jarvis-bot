# -*- coding: utf-8 -*-
"""Club Elo: страницы стран clubelo.com/<код> (рейтинг клубов страны) — все клубы с Elo; в лог (FOOTELO, gzip+base64 JSON)."""
import base64, gzip, json, re, time, requests
from concurrent.futures import ThreadPoolExecutor
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
CODES = ['ENG', 'ESP', 'ITA', 'GER', 'FRA', 'RUS', 'POR', 'NED', 'BEL', 'TUR', 'SCO', 'GRE', 'CZE', 'DEN', 'NOR', 'AUT', 'SUI', 'UKR', 'CRO', 'SRB', 'CYP', 'ISR', 'SWE', 'POL', 'KAZ', 'AZE', 'ARM', 'BUL', 'ROU', 'HUN', 'SVK', 'SVN', 'FIN', 'LTU', 'LVA', 'ALB', 'KOS', 'BIH', 'AND', 'GIB', 'FRO', 'WAL', 'IRL', 'NIR', 'ISL', 'LUX', 'MKD', 'MNE', 'MLT', 'GEO', 'MDA', 'EST', 'BLR']
out = {}
def get(c):
    for k in range(3):
        try:
            r = S.get('http://clubelo.com/' + c, timeout=60)
            if r.status_code == 200:
                t = r.text
                rows = []
                for m in re.finditer(r'\{[^{}]*"Elo"[^{}]*\}', t):
                    try:
                        o = json.loads(m.group(0))
                        if 'Name' in o: rows.append({'n': o['Name'], 'c': o.get('FedURL'), 'l': o.get('Level'), 'e': round(o['Elo'], 1)})
                    except Exception: pass
                # строки таблицы рейтинга: ссылка на клуб и число Elo рядом
                tab = re.findall(r'<a href="/([^"/]+)"[^>]*>[^<]*(?:<[^>]+>)*?</a></td><td[^>]*>(\d{3,4})</td>', t)
                print('FOOTELOINFO', c, len(t), 'json', len(rows), 'tab', len(tab), flush=True)
                return c, rows, tab[:3], len(t)
        except Exception as e:
            print('FOOTELOINFO', c, 'ERR', repr(e)[:80], flush=True)
        time.sleep(2)
    return c, [], [], 0
with ThreadPoolExecutor(5) as ex:
    res = list(ex.map(get, CODES))
allr = {}
for c, rows, tab, n in res:
    for r in rows: allr[(r['n'], r['c'])] = r
b = base64.b64encode(gzip.compress(json.dumps(list(allr.values()), ensure_ascii=False).encode(), 9)).decode()
for i in range(0, len(b), 3000):
    print('FOOTELO %d %d %s' % (i // 3000, (len(b) + 2999) // 3000, b[i:i + 3000]), flush=True)
# образец страницы: ENG, фрагмент рядом с названием клуба
r = S.get('http://clubelo.com/ENG', timeout=60); t = r.text
i = t.find('Arsenal'); print('FOOTELOSAMPLE', len(t), t.count('<tr'), t[i-200:i+500].replace('\n', ' '), flush=True)
print('FOOTELOEND', len(allr), flush=True)
