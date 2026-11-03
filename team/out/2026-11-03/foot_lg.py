# -*- coding: utf-8 -*-
"""Логотипы футбольных лиг ESPN для сайта v3a: PNG 256 px в лог (FOOTPNG, base64)."""
import base64, requests
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
IDS = {'epl': 23, 'laliga': 15, 'seriea': 12, 'bundesliga': 10, 'ligue1': 9, 'rpl': 106}
for k, i in IDS.items():
    for v in ('500', '500-dark'):
        path = '/i/leaguelogos/soccer/%s/%d.png' % (v, i)
        r = S.get('https://a.espncdn.com/combiner/i', params={'img': path, 'w': 256, 'h': 256}, timeout=40)
        ok = r.status_code == 200 and r.content[:4] == b'\x89PNG'
        print('FOOTLGINFO', k, v, r.status_code, len(r.content), flush=True)
        if ok:
            print('FOOTPNG l%s%s %s' % (k, '' if v == '500' else '_dark', base64.b64encode(r.content).decode()), flush=True)
print('FOOTEND', flush=True)
