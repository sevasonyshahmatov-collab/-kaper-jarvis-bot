# -*- coding: utf-8 -*-
"""Фото футболистов с Transfermarkt (владелец 17.11: «фото с Transfermarkt — в одном стиле и формате»).
1) номер игрока на Transfermarkt — из Wikidata: ESPN ID (P3681) -> Transfermarkt player ID (P2446); кэш — data/tm_ids.json;
2) портрет — со страницы игрока на transfermarkt.com (картинка шапки профиля; заглушку «default» пропускаем);
3) обработка та же, что у портретов из Wikimedia (players_headshots.py): одно лицо по центру, голова и плечи,
   фон убирает rembg, 256x256 WEBP -> data/ph/<espn_id>.webp. Не нашли или не обработали — остаётся прежнее фото.
Учёт: data/tm_done.json {id: номер TM} — готово, data/tm_skipped.json {id: причина}; в headshots.json у готовых
src='tm' (сайт добавляет его к адресу картинки, чтобы браузеры не показывали старое фото из кэша).
Лимит игроков: первая строка tm_run.txt «limit=N» (0 — все). Запуск — Actions (site-v3a-tm.yml), сеть облачной сессии закрыта."""
import io, json, os, re, time
import cv2, numpy as np, requests
from PIL import Image

H = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(H, 'data')
OUT = os.path.join(D, 'ph')
os.makedirs(OUT, exist_ok=True)
BUDGET = float(os.environ.get('TM_BUDGET', 35 * 60))   # сек: потом выходим, коммит, следующий запуск продолжит
T0 = time.time()
WD = requests.Session()
WD.headers['User-Agent'] = 'JarvisSiteBot/1.0 (football player photos; contact via github.com/sevasonyshahmatov-collab)'
TM = requests.Session()
TM.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
                   'Accept-Language': 'en-US,en;q=0.8'})


def jload(name, default):
    try:
        return json.load(open(os.path.join(D, name), encoding='utf-8'))
    except Exception:  # noqa: BLE001
        return default


def jsave(name, obj, indent=None):
    json.dump(obj, open(os.path.join(D, name), 'w', encoding='utf-8'), ensure_ascii=False,
              indent=indent, separators=None if indent is not None else (',', ':'))


src = open(os.path.join(D, 'players.js'), encoding='utf-8').read().strip()
P = json.loads(src[src.index('=') + 1:].rstrip(';'))['players']
goals = {p['id']: p.get('G', 0) + p.get('A', 0) for p in P}
ids = sorted((p['id'] for p in P if re.fullmatch(r'[0-9]{1,12}', str(p['id']))), key=lambda i: -goals.get(i, 0))
limit = 0
try:
    m = re.search(r'limit\s*=\s*(\d+)', open(os.path.join(H, 'tm_run.txt'), encoding='utf-8').read())
    limit = int(m.group(1)) if m else 0
except Exception:  # noqa: BLE001
    pass
if limit:
    ids = ids[:limit]
print('TM players', len(ids), 'limit', limit, flush=True)

# ---- 1. номера Transfermarkt из Wikidata ----
tmid = jload('tm_ids.json', {})
need = [i for i in ids if i not in tmid]
for k in range(0, len(need), 250):
    vals = ' '.join('"%s"' % x for x in need[k:k + 250])
    q = 'SELECT ?espn ?tm WHERE { VALUES ?espn { %s } ?p wdt:P3681 ?espn; wdt:P2446 ?tm. }' % vals
    for a in range(4):
        try:
            r = WD.post('https://query.wikidata.org/sparql', data={'query': q, 'format': 'json'}, timeout=90)
            if r.status_code == 200:
                for row in r.json()['results']['bindings']:
                    t = row['tm']['value']
                    if re.fullmatch(r'[0-9]{1,9}', t):
                        tmid.setdefault(row['espn']['value'], t)
                break
            print('TM wikidata http', r.status_code, flush=True)
        except Exception as e:  # noqa: BLE001
            print('TM wikidata err', repr(e)[:150], flush=True)
        time.sleep(5 * (a + 1))
    for x in need[k:k + 250]:
        tmid.setdefault(x, '')          # пусто — в Wikidata номера нет
    time.sleep(2)
jsave('tm_ids.json', tmid)
print('TM ids', sum(1 for i in ids if tmid.get(i)), 'of', len(ids), flush=True)

# ---- 2. портрет со страницы игрока ----
IMG = re.compile(r'(https://img\.a\.transfermarkt\.technology/portrait/(?:header|big)/[^"\'\s?]+\.(?:jpe?g|png|webp))')
STOP = False


def get(url):
    for k in range(3):
        try:
            r = TM.get(url, timeout=45)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
            print('TM http', r.status_code, url[:90], flush=True)
            if r.status_code in (403, 429):
                time.sleep(min(120, int(r.headers.get('Retry-After') or 20)))
            else:
                time.sleep(4 * (k + 1))
        except Exception as e:  # noqa: BLE001
            print('TM err', repr(e)[:150], flush=True)
            time.sleep(4 * (k + 1))
    raise RuntimeError('download')


def portrait(t):
    r = get('https://www.transfermarkt.com/x/profil/spieler/%s' % t)
    if r is None:
        return None, 'нет страницы'
    html = r.text
    i = html.find('data-header__profile-image')
    cand = IMG.findall(html[max(0, i - 600):i + 600]) if i >= 0 else []
    cand = cand or IMG.findall(html)
    cand = [u for u in cand if '/default' not in u]
    if not cand:
        return None, 'нет фото'
    url = cand[0].replace('/portrait/big/', '/portrait/header/')
    time.sleep(1.5)
    im = get(url)
    return (im.content if im is not None and im.content else None), (None if im is not None else 'нет файла')


# ---- 3. обработка (как players_headshots.py) ----
import rembg  # noqa: E402
sess = rembg.new_session(os.environ.get('HEADSHOTS_MODEL', 'u2net_human_seg'))
casc = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_alt2.xml'))


def make(raw):
    img = Image.open(io.BytesIO(raw)).convert('RGB')
    if img.width < 640:                              # у Transfermarkt портреты небольшие: увеличиваем до поиска лица
        k = 640 / img.width
        img = img.resize((640, int(round(img.height * k))), Image.LANCZOS)
    img.thumbnail((800, 800))
    g = cv2.equalizeHist(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY))
    fs = sorted([tuple(int(v) for v in f) for f in casc.detectMultiScale(g, 1.1, 6, minSize=(max(40, img.width // 14),) * 2)],
                key=lambda f: -f[2])
    if not fs:
        return None, 'нет лица'
    x, y, w, h = fs[0]
    if sum(1 for f in fs if f[2] >= 0.45 * w) > 1:
        return None, 'несколько лиц'
    side = w / 0.40
    ex, ey = x + w / 2, y + 0.40 * h
    left, top = ex - side / 2, ey - 0.38 * side
    box = (int(round(left)), int(round(top)), int(round(left + side)), int(round(top + side)))
    cv = Image.new('RGB', (box[2] - box[0], box[3] - box[1]), (128, 128, 128))
    cv.paste(img, (-box[0], -box[1]))
    mk = Image.new('L', cv.size, 0)
    mk.paste(Image.new('L', img.size, 255), (-box[0], -box[1]))
    if np.array(mk).mean() < 255 * 0.60:            # портрет TM обрезан по плечам — допускаем чуть больше пустоты снизу/по бокам
        return None, 'лицо у края кадра'
    cv = cv.resize((512, 512), Image.LANCZOS)
    mk = mk.resize((512, 512), Image.LANCZOS)
    cut = rembg.remove(cv, session=sess).convert('RGBA')
    a = np.minimum(np.array(cut.getchannel('A')), np.array(mk))
    # без светлой каймы от фона студии: край маски внутрь на 2 px и мягко, цвет края — от соседних пикселей силуэта
    a = cv2.GaussianBlur(cv2.erode(a, np.ones((3, 3), np.uint8), iterations=2), (3, 3), 0)
    rgb = np.array(cut.convert('RGB'))
    inner = cv2.erode((a > 200).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1)
    fill = cv2.inpaint(rgb, (1 - inner).astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
    edge = (a > 0) & (inner == 0)
    rgb[edge] = fill[edge]
    cut = Image.fromarray(rgb).convert('RGBA')
    cut.putalpha(Image.fromarray(a))
    if (a > 128).mean() < 0.12:
        return None, 'фон не отделился'
    return cut.resize((256, 256), Image.LANCZOS), None


done = jload('tm_done.json', {})
skipped = jload('tm_skipped.json', {})
hs = jload('headshots.json', {})
fails = n_new = n_skip = 0
for i in ids:
    t = tmid.get(i)
    if not t or done.get(i) == t or (i in skipped and skipped[i].get('tm') == t and skipped[i].get('why') != 'ошибка загрузки'):
        continue
    if time.time() - T0 > BUDGET:
        print('TM budget out', flush=True)
        break
    try:
        raw, why = portrait(t)
        im = None
        if raw is not None:
            im, why = make(raw)
    except Exception as e:  # noqa: BLE001
        im, why = None, 'ошибка загрузки' if 'download' in str(e) else 'ошибка: ' + repr(e)[:80]
    fails = fails + 1 if why == 'ошибка загрузки' else 0
    if fails >= 3:
        print('TM отказ подряд (403/429) — стоп, цепочку не продолжаем', flush=True)
        STOP = True
        break
    if im is not None:
        im.save(os.path.join(OUT, i + '.webp'), 'WEBP', quality=88, method=6)
        done[i] = t
        skipped.pop(i, None)
        hs[i] = {'f': 'tm:' + t, 'ok': 1, 'src': 'tm'}
        n_new += 1
    else:
        skipped[i] = {'tm': t, 'why': why}
        n_skip += 1
        print('TM skip', i, t, why, flush=True)
    time.sleep(2.5)
    if (n_new + n_skip) % 5 == 0:
        jsave('tm_done.json', done); jsave('tm_skipped.json', skipped, 0); jsave('headshots.json', hs)

jsave('tm_done.json', done); jsave('tm_skipped.json', skipped, 0); jsave('headshots.json', hs)
left = sum(1 for i in ids if tmid.get(i) and done.get(i) != tmid[i] and not (i in skipped and skipped[i].get('why') != 'ошибка загрузки'))
print('TM done new', n_new, 'skipped', n_skip, 'left', left, flush=True)
open(os.path.join(D, 'tm_left.txt'), 'w').write(str(0 if STOP else left))
