# -*- coding: utf-8 -*-
"""Фото хоккеистов — свои копии (владелец 13.11: «да, если поможет»). Раньше страницы брали фото прямо с www.khl.ru и
assets.nhle.com: сменят адреса или закроют доступ — на сайте пустые места.
Берёт адреса фото из hockey/data/khl_players.json и nhl_players.json (поле img игроков и gimg — вратари), скачивает
НОВЫЕ (уже скачанные не трогает), сохраняет в webp: hockey/data/ph/<лига>/<имя>.webp, список — hockey/data/ph/index.json
{адрес источника: файл}. В самих *_players.json адрес заменяется на свой (/hockey/data/ph/…, путь от корня сайта);
не скачалось — остаётся адрес источника (на странице при ошибке видны инициалы). Фото ушедших игроков удаляются.
Запуск — шаг hk_photos в daily/run.py после nhl_players / khl_players (сеть только в Actions):
    python team/site/v3a/hockey/photos_fetch.py [--limit N]"""
import io, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image

H = os.path.dirname(os.path.abspath(__file__))
PH = os.path.join(H, 'data', 'ph')
IDX = os.path.join(PH, 'index.json')
URL_PREFIX = '/hockey/data/ph/'            # путь от корня сайта: фото показываются на страницах из разных папок
MAX = 340                                  # самое крупное фото на сайте — страница игрока, до 340 px
BUDGET = 900                               # секунд на скачивание за один запуск; остальное — в следующий раз
S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0 (JarvisSiteBot; player photos)'


def fname(lg, url):
    """Имя файла из адреса: КХЛ …/teamplayers_db/15543/35799.jpg → 15543_35799; НХЛ …/20262027/NSH/8486189.png → 8486189_NSH_20262027."""
    p = [x for x in re.sub(r'\?.*$', '', url).split('/') if x]
    stem = os.path.splitext(p[-1])[0]
    tail = p[-3:-1] if lg == 'nhl' else p[-2:-1]
    return '%s/%s.webp' % (lg, '_'.join([stem] + tail[::-1]) if lg == 'nhl' else '_'.join(tail + [stem]))


def fetch(item):
    url, fn = item
    for k in range(3):
        try:
            r = S.get(url, timeout=20)
            if r.status_code == 404:
                return url, None
            if r.status_code == 200 and len(r.content) > 500:
                im = Image.open(io.BytesIO(r.content))
                im = im.convert('RGBA') if (im.mode in ('RGBA', 'LA', 'P')) else im.convert('RGB')
                if max(im.size) > MAX:
                    im.thumbnail((MAX, MAX), Image.LANCZOS)
                out = os.path.join(PH, fn)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                im.save(out, 'WEBP', quality=80, method=6)
                return url, fn
        except Exception:
            pass
        time.sleep(0.5 + k)
    return url, None


def main(limit=None):
    idx = {}
    if os.path.exists(IDX):
        idx = json.load(open(IDX, encoding='utf-8'))
    data, urls = {}, {}
    rev = {fn: u for u, fn in idx.items()}

    def note(u, lg):                           # свой адрес (вчерашний файл данных) — тоже «нужное» фото, не удалять
        if u.startswith(URL_PREFIX):
            u = rev.get(u[len(URL_PREFIX):], '')
        if u.startswith('http'):
            urls[u] = lg
    for lg in ('khl', 'nhl'):
        f = os.path.join(H, 'data', '%s_players.json' % lg)
        if not os.path.exists(f):
            continue
        d = json.load(open(f, encoding='utf-8'))
        data[lg] = (f, d)
        for p in d.get('players') or []:
            note(p.get('img') or '', lg)
        for m in (d.get('gimg') or {}).values():
            for u in m.values():
                note(u or '', lg)
    have = {u: fn for u, fn in idx.items() if os.path.exists(os.path.join(PH, fn))}
    todo = [(u, fname(lg, u)) for u, lg in urls.items() if u not in have]
    if limit:
        todo = todo[:limit]
    t0, got, fail = time.time(), 0, 0
    st = {'ok': 0, 'bad': 0}

    def job(it):                               # стоп по времени и если источник недоступен (40 неудач подряд без единой удачи)
        if time.time() - t0 > BUDGET or (st['bad'] >= 40 and not st['ok']):
            return it[0], None
        r = fetch(it)
        st['ok' if r[1] else 'bad'] += 1
        return r
    with ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(job, it) for it in todo]
        for fu in futs:
            u, fn = fu.result()
            if fn:
                have[u] = fn
                got += 1
            else:
                fail += 1
    # убрать фото, которых больше нет в данных (ушедшие игроки, новый сезон)
    keep = {u: fn for u, fn in have.items() if u in urls}
    used = set(keep.values())
    for lg in ('khl', 'nhl'):
        d_ = os.path.join(PH, lg)
        for fn in (os.listdir(d_) if os.path.isdir(d_) else []):
            if '%s/%s' % (lg, fn) not in used:
                os.remove(os.path.join(d_, fn))
    os.makedirs(PH, exist_ok=True)
    with open(IDX, 'w', encoding='utf-8') as f:
        json.dump(keep, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    # адреса в данных → свои файлы
    def loc(u):
        if u.startswith(URL_PREFIX):
            u = rev.get(u[len(URL_PREFIX):], u)
        return URL_PREFIX + keep[u] if u in keep else u
    for lg, (f, d) in data.items():
        for p in d.get('players') or []:
            if p.get('img'):
                p['img'] = loc(p['img'])
        for m in (d.get('gimg') or {}).values():
            for k in m:
                if m[k]:
                    m[k] = loc(m[k])
        with open(f, 'w', encoding='utf-8') as fo:
            json.dump(d, fo, ensure_ascii=False, separators=(',', ':'))
    size = sum(os.path.getsize(os.path.join(PH, fn)) for fn in used)
    print('HK_PHOTOS всего %d, свои %d (новых %d, не скачалось %d), %.1f МБ' % (len(urls), len(keep), got, fail, size / 1048576))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(int(a[a.index('--limit') + 1]) if '--limit' in a else None)
