# Все игроки КХЛ: id, имя по-русски и по-английски (locale=en) — для перевода имён на сайте (владелец 09.11)
import json, requests, sys
sys.path.insert(0, 'team/site/v3a/hockey')
B = 'https://khl.api.webcaster.pro/api/khl_mobile/'
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
st = S.get(B + 'data.json', timeout=40).json().get('current_stage_id')
TIDS = [8,10,12,16,18,22,24,26,28,30,32,36,38,40,42,44,46,56,61,105,113,315]
out = {}
for tid in TIDS:
    for loc in ('', '&locale=en'):
        for page in range(1, 6):
            a = S.get(B + 'players_v2.json?stage_id=%s&q[team_id_eq]=%s&page=%d%s' % (st, tid, page, loc), timeout=40).json()
            if not a: break
            for x in a:
                p = x.get('player') or x
                o = out.setdefault(str(p['id']), {})
                o['en' if loc else 'ru'] = p.get('name')
print('KHLNAMES ' + json.dumps(out, ensure_ascii=False))
