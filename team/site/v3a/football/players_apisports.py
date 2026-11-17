# -*- coding: utf-8 -*-
"""Фото футболистов из API-Football (api-sports.io), владелец 17.11: «фото игроков в одном стиле и формате».
Ключ — секрет репозитория APISPORTS_KEY (в коде и логах его нет). Бесплатный тариф: 100 запросов в день, 10 в минуту —
скрипт держит паузу между запросами, читает остаток из заголовка ответа и останавливается заранее; продолжит следующий запуск.
1) клубы: наши клубы (football-lite.js, английские названия) -> id клуба в API (по лиге, иначе поиск по названию); кэш data/as_teams.json;
2) составы: /players/squads?team=<id> -> игроки с id и фото; кэш data/as_squads.json (обновляем раз в 7 дней);
3) игрок: наш игрок (players.js, имя + клуб) -> игрок состава по имени (точное, либо фамилия + первая буква имени; только если один);
4) фото media.api-sports.io/football/players/<id>.png -> обработка как у портретов из Wikimedia (players_headshots.py):
   одно лицо по центру, голова и плечи, фон убирает rembg, 256x256 WEBP -> data/ph/<espn_id>.webp; в headshots.json src='as'.
Не нашли или не обработали — остаётся прежнее фото. Учёт: data/as_done.json, data/as_skipped.json; остаток — data/as_left.txt.
Запуск — Actions (site-v3a-apisports.yml)."""
import difflib, io, json, os, re, sys, time, unicodedata
import requests
from PIL import Image

H = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(H, 'data')
OUT = os.path.join(D, 'ph')
os.makedirs(OUT, exist_ok=True)
KEY = os.environ.get('APISPORTS_KEY', '').strip()
if len(sys.argv) > 1 and sys.argv[1] == '--due':       # для ежедневной сборки: 0 — пора запускать, 1 — рано или нет ключа
    try:
        nxt = open(os.path.join(D, 'as_next.txt'), encoding='utf-8').read().strip()
    except Exception:  # noqa: BLE001
        nxt = ''
    sys.exit(0 if KEY and (not nxt or nxt <= time.strftime('%Y-%m-%d')) else 1)
if not KEY:
    print('AS: нет ключа APISPORTS_KEY — пропуск', flush=True)
    sys.exit(0)
BUDGET = float(os.environ.get('AS_BUDGET', 40 * 60))
RESERVE = int(os.environ.get('AS_RESERVE', 3))          # запросов оставляем про запас на день
T0 = time.time()
API = 'https://v3.football.api-sports.io'
S = requests.Session()
S.headers.update({'x-apisports-key': KEY, 'User-Agent': 'JarvisSiteBot/1.0'})
M = requests.Session()
M.headers['User-Agent'] = 'JarvisSiteBot/1.0'
LEAGUE = {'epl': 39, 'laliga': 140, 'seriea': 135, 'bundesliga': 78, 'ligue1': 61, 'rpl': 235, 'ucl': 2, 'uel': 3}
SEASON = int(os.environ.get('AS_SEASON', time.strftime('%Y') if time.strftime('%m') >= '07' else str(int(time.strftime('%Y')) - 1)))


def jload(name, default):
    try:
        return json.load(open(os.path.join(D, name), encoding='utf-8'))
    except Exception:  # noqa: BLE001
        return default


def jsave(name, obj, indent=None):
    json.dump(obj, open(os.path.join(D, name), 'w', encoding='utf-8'), ensure_ascii=False,
              indent=indent, separators=None if indent is not None else (',', ':'))


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(fc|cf|ac|afc|sc|ssc|as|sv|vfb|vfl|tsg|rc|ogc|losc|fk|pfc|club|de|the|1)\b', ' ', s)
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


LEFT_REQ = [None]
STOP = [False]


def api(path, **params):
    """один запрос к API с паузой (10 в минуту) и учётом дневного остатка; None — лимит/ошибка"""
    if STOP[0] or (LEFT_REQ[0] is not None and LEFT_REQ[0] <= RESERVE):
        STOP[0] = True
        return None
    time.sleep(6.5)
    for k in range(3):
        try:
            r = S.get(API + path, params=params, timeout=40)
            rem = r.headers.get('x-ratelimit-requests-remaining')
            if rem is not None and rem.lstrip('-').isdigit():
                LEFT_REQ[0] = int(rem)
            if r.status_code == 200:
                j = r.json()
                err = j.get('errors')
                if err:
                    print('AS api errors', path, json.dumps(err, ensure_ascii=False)[:200], flush=True)
                    if any(x in json.dumps(err).lower() for x in ('limit', 'requests', 'token', 'key', 'suspended')):
                        STOP[0] = True
                    return {'errors': err, 'response': j.get('response') or []}
                return j
            print('AS http', r.status_code, path, flush=True)
            if r.status_code in (401, 403):
                STOP[0] = True
                return None
            time.sleep(10 * (k + 1))
        except Exception as e:  # noqa: BLE001
            print('AS err', path, repr(e)[:120], flush=True)
            time.sleep(10 * (k + 1))
    return None


# ---- наши клубы и игроки ----
src = open(os.path.join(D, 'football-lite.js'), encoding='utf-8').read()
FL = json.loads(src[src.index('{'):src.rindex('}') + 1])['teams']
src = open(os.path.join(D, 'players.js'), encoding='utf-8').read().strip()
P = json.loads(src[src.index('=') + 1:].rstrip(';'))['players']
score = {p['id']: p.get('G', 0) + p.get('A', 0) for p in P}

# ---- 1. клубы ----
teams = jload('as_teams.json', {})        # наш id -> id в API (0 — не нашли)
by_lg = {}
for tid, t in FL.items():
    by_lg.setdefault(t.get('lg'), []).append(tid)
for lg, tids in by_lg.items():
    if all(t in teams for t in tids) or lg not in LEAGUE:
        continue
    j = api('/teams', league=LEAGUE[lg], season=SEASON)
    if j is None:
        break
    cand = {norm(x['team']['name']): x['team']['id'] for x in j.get('response', [])}
    for t in tids:
        if t in teams:
            continue
        nm = norm(FL[t].get('en') or t.replace('_', ' '))
        best = difflib.get_close_matches(nm, list(cand), n=2, cutoff=0.72)
        if nm in cand:
            teams[t] = cand[nm]
        elif len(best) == 1 or (len(best) == 2 and difflib.SequenceMatcher(None, nm, best[0]).ratio() - difflib.SequenceMatcher(None, nm, best[1]).ratio() > 0.08):
            teams[t] = cand[best[0]]
for t in FL:                                  # кого нет в списке лиги (план без сезона, кубки) — поиск по названию
    if t in teams or STOP[0]:
        continue
    q = re.sub(r'[^A-Za-z0-9 ]+', ' ', unicodedata.normalize('NFKD', FL[t].get('en') or t).encode('ascii', 'ignore').decode()).strip()
    q = max(q.split(), key=len) if len(q) > 20 else q
    if len(q) < 3:
        teams[t] = 0
        continue
    j = api('/teams', search=q)
    if j is None:
        break
    nm = norm(FL[t].get('en') or t)
    cand = {norm(x['team']['name']): x['team']['id'] for x in j.get('response', []) if not x['team'].get('national')}
    best = difflib.get_close_matches(nm, list(cand), n=1, cutoff=0.72)
    teams[t] = cand[best[0]] if best else 0
jsave('as_teams.json', teams)
print('AS teams', sum(1 for v in teams.values() if v), 'of', len(FL), 'requests left', LEFT_REQ[0], flush=True)

# ---- 2. составы ----
squads = jload('as_squads.json', {})      # наш id клуба -> {'d': дата, 'p': [[id, имя], ...]}
today = time.strftime('%Y-%m-%d')
order = sorted((t for t in FL if teams.get(t)), key=lambda t: -sum(score.get(p['id'], 0) for p in P if p.get('t') == t))
for t in order:
    s = squads.get(t)
    if s and (time.mktime(time.strptime(today, '%Y-%m-%d')) - time.mktime(time.strptime(s['d'], '%Y-%m-%d'))) < 7 * 86400:
        continue
    j = api('/players/squads', team=teams[t])
    if j is None:
        break
    pl = []
    for x in j.get('response', []):
        for p in x.get('players', []):
            if p.get('id'):
                pl.append([p['id'], p.get('name') or ''])
    squads[t] = {'d': today, 'p': pl}
    jsave('as_squads.json', squads)
print('AS squads', len(squads), 'requests left', LEFT_REQ[0], flush=True)


# ---- 3. наш игрок -> игрок API ----
def match(name, squad):
    n = norm(name).split()
    if not n:
        return None
    full = [pid for pid, nm in squad if norm(nm) == ' '.join(n)]
    if len(full) == 1:
        return full[0]
    last, ini = n[-1], n[0][0]
    c = []
    for pid, nm in squad:
        m = norm(nm).split()
        if not m:
            continue
        if m[-1] == last and (len(m) == 1 or len(n) == 1 or m[0][0] == ini):
            c.append(pid)
    return c[0] if len(set(c)) == 1 else None


link = jload('as_players.json', {})        # espn id -> id в API
for p in P:
    sq = squads.get(p.get('t'))
    if sq and p['id'] not in link:
        a = match(p.get('n', ''), sq['p'])
        if a:
            link[p['id']] = a
jsave('as_players.json', link)
print('AS players linked', len(link), 'of', len(P), flush=True)

# ---- 4. фото ----
done = jload('as_done.json', {})
skipped = jload('as_skipped.json', {})
todo = sorted((i for i in link if done.get(i) != link[i] and not (skipped.get(i, {}).get('a') == link[i] and skipped[i].get('why') != 'ошибка загрузки')),
              key=lambda i: -score.get(i, 0))
print('AS photos to do', len(todo), flush=True)
if todo:
    import cv2, numpy as np, rembg   # noqa: E401
    sess = rembg.new_session(os.environ.get('HEADSHOTS_MODEL', 'u2net_human_seg'))
    casc = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_alt2.xml'))

    def make(raw):
        img = Image.open(io.BytesIO(raw))
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGBA')
            bg = Image.new('RGB', img.size, (236, 238, 242))
            bg.paste(img, (0, 0), img)
            img = bg
        img = img.convert('RGB')
        if img.width < 640:                      # фото API небольшие (150-250 px): увеличиваем до поиска лица
            k = 640 / img.width
            img = img.resize((640, int(round(img.height * k))), Image.LANCZOS)
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
        if np.array(mk).mean() < 255 * 0.55:       # портрет обрезан по плечам — допускаем пустоту снизу и по бокам
            return None, 'лицо у края кадра'
        cv = cv.resize((512, 512), Image.LANCZOS)
        mk = mk.resize((512, 512), Image.LANCZOS)
        cut = rembg.remove(cv, session=sess).convert('RGBA')
        a = np.minimum(np.array(cut.getchannel('A')), np.array(mk))
        # без светлой каймы от фона: край маски внутрь на 2 px и мягко, цвет края — от соседних пикселей силуэта
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

    hs = jload('headshots.json', {})
    fails = n_new = n_skip = 0
    for i in todo:
        if time.time() - T0 > BUDGET:
            print('AS budget out', flush=True)
            break
        a = link[i]
        why, im, st = None, None, ''
        try:
            r = M.get('https://media.api-sports.io/football/players/%s.png' % a, timeout=40)
            st = str(r.status_code)
            if r.status_code == 200 and len(r.content) > 3000:
                im, why = make(r.content)
            elif r.status_code in (403, 429):
                why = 'ошибка загрузки'
            else:
                why = 'нет фото'
        except Exception as e:  # noqa: BLE001
            why, st = 'ошибка загрузки', type(e).__name__
        fails = fails + 1 if why == 'ошибка загрузки' else 0
        if fails >= 5:
            print('AS media: отказ подряд', st, '— стоп', flush=True)
            STOP[0] = True
            break
        if im is not None:
            im.save(os.path.join(OUT, i + '.webp'), 'WEBP', quality=88, method=6)
            done[i] = a
            skipped.pop(i, None)
            hs[i] = {'f': 'as:%s' % a, 'ok': 1, 'src': 'as'}
            n_new += 1
        else:
            skipped[i] = {'a': a, 'why': why, 'st': st}
            n_skip += 1
            print('AS skip', i, a, why, st, flush=True)
        time.sleep(1.2)
        if (n_new + n_skip) % 10 == 0:
            jsave('as_done.json', done); jsave('as_skipped.json', skipped, 0); jsave('headshots.json', hs)
    jsave('as_done.json', done); jsave('as_skipped.json', skipped, 0); jsave('headshots.json', hs)
    print('AS photos new', n_new, 'skipped', n_skip, flush=True)

left = sum(1 for i in link if done.get(i) != link[i] and not (skipped.get(i, {}).get('a') == link[i] and skipped[i].get('why') != 'ошибка загрузки'))
open(os.path.join(D, 'as_left.txt'), 'w').write(str(0 if STOP[0] else left))
# когда запускать снова (ежедневная сборка смотрит этот файл): упёрлись в дневной лимит — завтра; иначе — через 7 дней (новички в составах)
nxt = time.strftime('%Y-%m-%d', time.localtime(time.time() + (86400 if STOP[0] or left else 7 * 86400)))
open(os.path.join(D, 'as_next.txt'), 'w').write(nxt)
print('AS left', left, 'stop', STOP[0], 'requests left', LEFT_REQ[0], flush=True)
