# -*- coding: utf-8 -*-
"""Портреты футболистов «как в НХЛ»: голова и плечи, анфас, прозрачный фон, 256x256 WEBP.
Источник — фото из football/data/photos.json (Wikimedia Commons). Запуск в Actions (site-v3a-headshots.yml).
Правила: нужно ровно одно крупное лицо (иначе пропуск, чужих лиц не оставляем); лицо ~40% ширины кадра,
глаза на ~38% высоты; фон убирает rembg. Готовые файлы не пересчитываются.
Лимит игроков: первая строка headshots_run.txt вида «limit=30» (пусто или 0 — все)."""
import io, json, os, re, sys, time
import cv2, numpy as np, requests
from PIL import Image

H = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(H, 'data')
OUT = os.path.join(D, 'ph')
os.makedirs(OUT, exist_ok=True)
BUDGET = float(os.environ.get('HEADSHOTS_BUDGET', 48 * 60))  # сек: потом выходим, коммит, следующий запуск продолжит
T0 = time.time()
S = requests.Session()
S.headers['User-Agent'] = 'JarvisSiteBot/1.0 (football headshots; contact via github.com/sevasonyshahmatov-collab)'


def jload(name, default):
    try:
        return json.load(open(os.path.join(D, name), encoding='utf-8'))
    except Exception:  # noqa: BLE001
        return default


photos = jload('photos.json', {})
done = jload('headshots.json', {})
skipped = jload('headshots_skipped.json', {})
src = open(os.path.join(D, 'players.js'), encoding='utf-8').read().strip()
P = json.loads(src[src.index('=') + 1:].rstrip(';'))['players']
goals = {p['id']: p.get('G', 0) for p in P}
limit = 0
try:
    m = re.search(r'limit\s*=\s*(\d+)', open(os.path.join(H, 'headshots_run.txt'), encoding='utf-8').read())
    limit = int(m.group(1)) if m else 0
except Exception:  # noqa: BLE001
    pass
ids = sorted((i for i in photos if re.fullmatch(r'[0-9]{1,12}', str(i))), key=lambda i: -goals.get(i, 0))   # id попадает в имя файла ph/<id>.webp: только цифры (защита от ../ из внешних данных)
if limit:
    ids = ids[:limit]
print('HS players', len(ids), 'limit', limit, flush=True)

import rembg
sess = rembg.new_session(os.environ.get('HEADSHOTS_MODEL', 'u2net_human_seg'))
casc = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_alt2.xml'))


THUMB = {}   # имя файла -> адрес готовой миниатюры (MediaWiki API, по 50 файлов за запрос)
STOP = False  # Wikimedia ответила 429 подряд — прекращаем запуск и цепочку, без долбёжки


def thumbs(names):
    for k in range(0, len(names), 50):
        part = names[k:k + 50]
        try:
            r = S.get('https://commons.wikimedia.org/w/api.php', params={
                'action': 'query', 'format': 'json', 'prop': 'imageinfo', 'iiprop': 'url', 'iiurlwidth': 640,
                'titles': '|'.join('File:' + n for n in part)}, timeout=60)
            pages = (r.json().get('query') or {}).get('pages') or {}
            norm = {x['to']: x['from'] for x in (r.json().get('query') or {}).get('normalized') or []}
            for pg in pages.values():
                ii = (pg.get('imageinfo') or [{}])[0]
                t = pg.get('title', '')
                name = norm.get(t, t)[5:]
                if ii.get('thumburl'):
                    THUMB[name] = ii['thumburl']
        except Exception as e:  # noqa: BLE001
            print('HS api err', repr(e)[:150], flush=True)
        time.sleep(2)


def fetch(fn):
    global STOP
    url = THUMB.get(fn)
    if not url:
        return None
    for k in range(3):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 200 and r.content:
                return r.content
            if r.status_code == 404:
                return None
            print('HS http', r.status_code, fn, flush=True)
            if r.status_code == 429:
                time.sleep(min(120, int(r.headers.get('Retry-After') or 30)))
            else:
                time.sleep(3 * (k + 1))
        except Exception as e:  # noqa: BLE001
            print('HS err', repr(e)[:150], flush=True)
            time.sleep(3 * (k + 1))
    raise RuntimeError('download')


def find_face(img):
    g = cv2.equalizeHist(cv2.cvtColor(np.array(img.convert('RGB')), cv2.COLOR_RGB2GRAY))
    w = img.width
    fs = casc.detectMultiScale(g, 1.1, 6, minSize=(max(40, w // 14),) * 2)
    return sorted([tuple(int(v) for v in f) for f in fs], key=lambda f: -f[2])


def make(raw):
    img = Image.open(io.BytesIO(raw)).convert('RGB')
    img.thumbnail((800, 800))
    fs = find_face(img)
    if not fs:
        return None, 'нет лица'
    x, y, w, h = fs[0]
    if sum(1 for f in fs if f[2] >= 0.45 * w) > 1:
        return None, 'несколько лиц'
    if w < 60:
        return None, 'лицо мелкое'
    side = w / 0.40
    ex, ey = x + w / 2, y + 0.40 * h  # линия глаз ~ 40% высоты рамки Хаара
    left, top = ex - side / 2, ey - 0.38 * side
    box = (int(round(left)), int(round(top)), int(round(left + side)), int(round(top + side)))
    # квадрат с полями: за кадром — прозрачность
    cv = Image.new('RGB', (box[2] - box[0], box[3] - box[1]), (128, 128, 128))
    cv.paste(img, (-box[0], -box[1]))
    mask = Image.new('L', img.size, 255)
    mk = Image.new('L', cv.size, 0)
    mk.paste(mask, (-box[0], -box[1]))
    # сторона кадра меньше трети видимого — слишком большая пустота
    if np.array(mk).mean() < 255 * 0.72:
        return None, 'лицо у края кадра'
    cv = cv.resize((512, 512), Image.LANCZOS)
    mk = mk.resize((512, 512), Image.LANCZOS)
    cut = rembg.remove(cv, session=sess).convert('RGBA')
    a = np.minimum(np.array(cut.getchannel('A')), np.array(mk))
    cut.putalpha(Image.fromarray(a))
    # проверка: человек должен занимать центр
    if (a > 128).mean() < 0.12:
        return None, 'фон не отделился'
    return cut.resize((256, 256), Image.LANCZOS), None


for i in ids:
    if i not in done and os.path.exists(os.path.join(OUT, i + '.webp')):
        done[i] = {'f': photos[i], 'ok': 1}
thumbs([photos[i] for i in ids if i not in done])
print('HS thumbs', len(THUMB), flush=True)
fails = 0
n_ok = n_new = n_skip = 0
for i in ids:
    fn = photos[i]
    path = os.path.join(OUT, i + '.webp')
    if os.path.exists(path) and done.get(i, {}).get('f') == fn:
        n_ok += 1
        continue
    if skipped.get(i, {}).get('f') == fn and skipped[i].get('why') != 'ошибка загрузки':
        n_skip += 1
        continue
    if time.time() - T0 > BUDGET:
        print('HS budget out', flush=True)
        break
    try:
        raw = fetch(fn)
        time.sleep(1.0)
        if raw is None:
            im, why = None, 'файл не найден'
        else:
            im, why = make(raw)
    except Exception as e:  # noqa: BLE001
        im, why = None, 'ошибка загрузки' if 'download' in str(e) else 'ошибка: ' + repr(e)[:80]
    fails = fails + 1 if why == 'ошибка загрузки' else 0
    if fails >= 3:
        print('HS 429 подряд — стоп, цепочку не продолжаем', flush=True)
        STOP = True
        break
    time.sleep(2.0)
    if im is not None:
        im.save(path, 'WEBP', quality=88, method=6)
        done[i] = {'f': fn, 'ok': 1}
        skipped.pop(i, None)
        n_ok += 1
        n_new += 1
    else:
        skipped[i] = {'f': fn, 'why': why}
        n_skip += 1
        print('HS skip', i, fn, why, flush=True)
    if (n_new + n_skip) % 5 == 0:  # сохранять часто: запуск может оборваться по лимиту времени
        json.dump(done, open(os.path.join(D, 'headshots.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        json.dump(skipped, open(os.path.join(D, 'headshots_skipped.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

json.dump(done, open(os.path.join(D, 'headshots.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(skipped, open(os.path.join(D, 'headshots_skipped.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('HS done ok', n_ok, 'new', n_new, 'skipped', n_skip, flush=True)
if STOP:
    open(os.path.join(D, 'headshots_stop.txt'), 'w').write(time.strftime('%Y-%m-%d %H:%M'))
elif os.path.exists(os.path.join(D, 'headshots_stop.txt')):
    os.remove(os.path.join(D, 'headshots_stop.txt'))
