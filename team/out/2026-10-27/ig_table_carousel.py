# Карусель «Аналитическая таблица» в Instagram (владелец 27.10): 7 слайдов 1080×1350, подпись ниже.
import os, sys, time, requests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path[:0] = [os.path.join(ROOT, 'team', 'mirror'), os.path.join(ROOT, 'team', 'reels_daily')]
import ig_mirror, instagram  # noqa: E402
API = 'https://graph.facebook.com/v21.0/'
CAP = """Как устроена моя аналитическая таблица по КХЛ и НХЛ 👇

Листай слайды: шансы на каждый матч, что чаще заходит у команд, все прогнозы со счётом после игры и сравнение с линией букмекера.

Прогнозы не удаляю, ни зашедшие, ни нет.

Хочешь доступ к таблице? Напиши в директ слово «ТАБЛИЦА».

#хоккей #кхл #нхл #прогнозынахоккей #аналитика"""
tok, uid = instagram._env()
kids = []
for i in range(1, 8):
    p = os.path.join(ROOT, 'docs/channel/pins/carousel_table/car_%d.jpg' % i)
    r = requests.post(API + uid + '/media', timeout=60, data=dict(image_url=ig_mirror.host(p), is_carousel_item='true', access_token=tok)).json()
    if 'id' not in r:
        sys.exit('::error::слайд %d: %s' % (i, r.get('error') or r))
    kids.append(r['id'])
r = requests.post(API + uid + '/media', timeout=60, data=dict(media_type='CAROUSEL', children=','.join(kids), caption=CAP, access_token=tok)).json()
if 'id' not in r:
    sys.exit('::error::карусель: %s' % (r.get('error') or r))
cid = r['id']
for _ in range(60):
    st = requests.get(API + cid, params=dict(fields='status_code', access_token=tok), timeout=30).json().get('status_code')
    if st in ('FINISHED', None):
        break
    if st in ('ERROR', 'EXPIRED'):
        sys.exit('::error::обработка: %s' % st)
    time.sleep(5)
for _ in range(6):
    p = requests.post(API + uid + '/media_publish', data=dict(creation_id=cid, access_token=tok), timeout=60).json()
    if 'id' in p or (p.get('error') or {}).get('code') != 9007:
        break
    time.sleep(15)
if 'id' not in p:
    sys.exit('::error::публикация: %s' % (p.get('error') or p))
link = requests.get(API + p['id'], params=dict(fields='permalink', access_token=tok), timeout=30).json().get('permalink', '')
print('::notice title=IGCAROUSEL::%s %s' % (p['id'], link))
