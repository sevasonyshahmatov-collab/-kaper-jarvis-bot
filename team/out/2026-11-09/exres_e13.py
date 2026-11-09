"""Итог НХЛ-экспресса 0811-e13 (владелец 09.11): номер поста — из t.me/s/jarvibet, итог — express_result.compute."""
import json, os, re, sys, html, requests
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path[:0] = [os.path.join(ROOT, p) for p in ('team/picks', 'render', 'team/daily')]
import express_result as xr
JOB = os.path.join(ROOT, 'team/out/2026-11-09/exres_e13.json')
job = json.load(open(JOB, encoding='utf-8'))
os.environ['EXPRESS_FORCE_LIVE'] = '0'
num = None; before = None
for _ in range(6):
    t = requests.get('https://t.me/s/jarvibet' + ('?before=%d' % before if before else ''), headers={'User-Agent': 'Mozilla/5.0'}, timeout=30).text
    posts = re.findall(r'data-post="jarvibet/(\d+)"(.*?)(?=data-post="jarvibet/|\Z)', t, re.S)
    if not posts: break
    for n, body in posts:
        txt = html.unescape(re.sub(r'<[^>]+>', ' ', body))
        if 'Анахайм' in txt and 'Нью-Джерси' in txt and 'Тампа' in txt and (num is None or int(n) > num):
            num = int(n)
    before = min(int(n) for n, _ in posts)
    if num: break
print('EXRES POST', num, flush=True)
c, legs, res, st = xr.compute('team/out/2026-11-08/express_owner2_coupons.json', '1', 'out/express/2026-11-08-owner2')
print('EXRES STATE', st, res, flush=True)
if st == 'pending' or not num:
    sys.exit('pending или нет поста')
job['messages'].append({'to': 'owner', 'type': 'photo', 'html': True, 'emoji': True, 'files': ['out/express/2026-11-08-owner2/e1_result.jpg'],
                        'text': xr.result_text(c, legs, st), 'buttons': 'post', 'pid': '0811-e13r%d' % num})
json.dump(job, open(JOB, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('EXRES SENT', st, flush=True)
