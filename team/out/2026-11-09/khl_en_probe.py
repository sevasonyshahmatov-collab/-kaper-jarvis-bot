# Проба: отдаёт ли приложение КХЛ имена игроков латиницей (сайт v3a, владелец 09.11: «все имена английскими»)
import json, requests
B = 'https://khl.api.webcaster.pro/api/khl_mobile/'
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
boot = S.get(B + 'data.json', timeout=40).json(); st = boot.get('current_stage_id')
print('PROBE stage', st)
for suf, hdr in [('', {}), ('&locale=en', {}), ('&lang=en', {}), ('', {'Accept-Language': 'en'}), ('&locale=en', {'Accept-Language': 'en-US'})]:
    try:
        r = S.get(B + 'players_v2.json?stage_id=%s&q[team_id_eq]=46&page=1%s' % (st, suf), headers=hdr, timeout=40)
        a = r.json(); p = [x.get('player') or x for x in a][:4]
        print('PROBE', repr(suf), hdr, r.status_code, [x.get('name') for x in p])
        if suf == '' and not hdr: print('PROBE keys', sorted(p[0].keys()))
    except Exception as e:
        print('PROBE err', suf, hdr, e)
for u in ['https://en.khl.ru/', 'https://www.khl.ru/players/']:
    try: r = S.get(u, timeout=30); print('PROBE', u, r.status_code, len(r.text))
    except Exception as e: print('PROBE', u, e)
