# -*- coding: utf-8 -*-
"""Рейтинг Club Elo (clubelo.com, бесплатный API) на сегодня для сайта v3a: CSV Rank,Club,Country,Level,Elo,From,To → в лог (FOOTELO, gzip+base64)."""
import base64, gzip, requests
from datetime import datetime, timedelta, timezone
day = datetime.now(timezone(timedelta(hours=3))).strftime('%Y-%m-%d')
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
txt = ''
for d in (day, (datetime.now(timezone(timedelta(hours=3))) - timedelta(days=1)).strftime('%Y-%m-%d')):
    for url in ('http://api.clubelo.com/' + d, 'https://api.clubelo.com/' + d):
        try:
            r = S.get(url, timeout=60)
            print('FOOTELOINFO', url, r.status_code, len(r.text), flush=True)
            if r.status_code == 200 and r.text.count('\n') > 100:
                txt = r.text; day = d; break
        except Exception as e:
            print('FOOTELOINFO', url, 'ERR', repr(e), flush=True)
    if txt: break
b = base64.b64encode(gzip.compress(('DAY ' + day + '\n' + txt).encode(), 9)).decode()
for i in range(0, len(b), 3000):
    print('FOOTELO %d %d %s' % (i // 3000, (len(b) + 2999) // 3000, b[i:i + 3000]), flush=True)
print('FOOTELOEND', len(txt), flush=True)
