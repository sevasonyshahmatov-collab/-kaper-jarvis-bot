# -*- coding: utf-8 -*-
"""Крупные эмблемы клубов и знаки лиг ESPN (оригиналы 500 px, без combiner) для сайта v3a: PNG в лог (FOOTPNG, base64)."""
import base64, requests
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
TEAMS = ['2991', '22271', '1963', '596', '22300', '21949', '21539', '18285', '11336', '3850', '442', '21927', '3852', '3851', '1941', '2533', '8089', '13083', '622', '2528', '370', '997', '107', '493', '115', '85', '7672', '20025', '21943', '104', '152', '268', '357', '3236', '349', '7868', '367', '2925', '21613', '170', '20024', '109', '437', '388', '1895', '4411', '3841', '1010', '936', '97', '102', '94', '3263', '113', '172', '7853', '11706', '21607', '1538', '570', '21922', '87', '433', '617', '21615', '22281', '15784', '6851', '2290', '180', '111', '105', '3699', '384', '243', '2502', '7922', '362', '174', '3751', '126', '5309', '103', '11505', '552', '393', '175', '373', '169', '2994', '147', '86', '273', '12216', '8169', '3822', '432', '494', '364', '1068', '4007', '21610', '6997', '137', '90', '3611', '88', '2990', '239', '887', '2250']
LG = {'epl': 23, 'laliga': 15, 'seriea': 12, 'bundesliga': 10, 'ligue1': 9, 'rpl': 106, 'ucl': 2, 'uel': 2310}
jobs = [('t%s' % i, 'https://a.espncdn.com/i/teamlogos/soccer/500/%s.png' % i) for i in TEAMS]
for k, i in LG.items():
    jobs.append(('l%s' % k, 'https://a.espncdn.com/i/leaguelogos/soccer/500-dark/%d.png' % i))
    jobs.append(('l%s_light' % k, 'https://a.espncdn.com/i/leaguelogos/soccer/500/%d.png' % i))
for n, u in jobs:
    try:
        r = S.get(u, timeout=60)
        ok = r.status_code == 200 and r.content[:4] == b'\x89PNG'
        w = int.from_bytes(r.content[16:20], 'big') if ok else 0
        print('FOOTIMGINFO', n, r.status_code, len(r.content), w, flush=True)
        if ok:
            print('FOOTPNG %s %s' % (n, base64.b64encode(r.content).decode()), flush=True)
    except Exception as e:
        print('FOOTIMGINFO', n, 'ERR', repr(e)[:80], flush=True)
print('FOOTEND', flush=True)
