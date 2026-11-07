# -*- coding: utf-8 -*-
"""Поиск фото для карточек лиг: категории и запросы Commons -> только свободные лицензии -> контактные листы миниатюр (без rembg).
Читает discover.json {ключ: {cats:[...], qs:[...]}}; пишет cand/disc-<ключ>.txt и cand/dsheet-<ключ>-N.jpg."""
import io, json, os, re, time, html
import requests
from PIL import Image, ImageDraw
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, 'cand'); os.makedirs(OUT, exist_ok=True)
S = requests.Session(); S.headers['User-Agent'] = 'JarvisSiteBot/1.0 (league cards mockup; github.com/sevasonyshahmatov-collab)'
API = 'https://commons.wikimedia.org/w/api.php'
OK_LIC = re.compile(r'^(cc[- ]by(-sa)?[- ]\d|cc0|pd|public domain)', re.I)


def api(**p):
    p.update(format='json')
    for k in range(4):
        r = S.get(API, params=p, timeout=60)
        if r.status_code == 429:
            time.sleep(10 * (k + 1)); continue
        try:
            return r.json()
        except Exception:
            return {}
    return {}


def files(cat, depth=3, maxc=60):
    out, seen, cats, todo = [], set(), [], [(cat, 0)]
    while todo and len(cats) < maxc:
        c, d = todo.pop(0)
        if c in cats: continue
        cats.append(c)
        if d < depth:
            j = api(action='query', list='categorymembers', cmtitle=c, cmtype='subcat', cmlimit=100)
            todo += [(m['title'], d + 1) for m in (j.get('query') or {}).get('categorymembers', [])]
    for c in cats:
        j = api(action='query', list='categorymembers', cmtitle=c, cmtype='file', cmlimit=500)
        for m in (j.get('query') or {}).get('categorymembers', []):
            if m['title'] not in seen: seen.add(m['title']); out.append(m['title'])
    return out


def search(q):
    j = api(action='query', list='search', srsearch=q, srnamespace=6, srlimit=100)
    return [m['title'] for m in (j.get('query') or {}).get('search', [])]


def strip(s): return html.unescape(re.sub(r'<[^>]+>', '', s or '')).strip()


cfg = json.load(open(os.path.join(H, 'discover.json'), encoding='utf-8'))
for key, c in cfg.items():
    t = []
    for cat in c.get('cats', []): t += files(cat)
    for q in c.get('qs', []): t += search(q)
    t = list(dict.fromkeys(t)); print(key, 'найдено', len(t), flush=True)
    ok = []
    for k in range(0, len(t), 40):
        j = api(action='query', prop='imageinfo', iiprop='url|size|mime|extmetadata', iiurlwidth=360, titles='|'.join(t[k:k + 40]))
        for pg in ((j.get('query') or {}).get('pages') or {}).values():
            ii = (pg.get('imageinfo') or [None])[0]
            if not ii: continue
            em = ii.get('extmetadata') or {}; lic = strip((em.get('LicenseShortName') or {}).get('value'))
            if ii.get('mime', '').startswith('image/jpeg') and OK_LIC.match(lic) and ii['height'] >= 700 and ii['width'] >= 500:
                ok.append((pg['title'], ii, lic, strip((em.get('Artist') or {}).get('value'))[:60], strip((em.get('DateTimeOriginal') or {}).get('value'))[:10]))
        time.sleep(1)
    ok.sort(key=lambda x: x[0]); print(key, 'свободных', len(ok), flush=True)
    open(os.path.join(OUT, 'disc-%s.txt' % key), 'w', encoding='utf-8').write('\n'.join('%03d\t%s\t%dx%d\t%s\t%s\t%s' % (i, a, b['width'], b['height'], l, au, d) for i, (a, b, l, au, d) in enumerate(ok)))
    cw, ch, per = 300, 330, 18
    for sn in range(0, len(ok), per):
        chunk = ok[sn:sn + per]; sheet = Image.new('RGB', (cw * 6, ch * 3), (30, 30, 40))
        for i, (a, b, l, au, d) in enumerate(chunk):
            try:
                r = S.get(b.get('thumburl') or b['url'], timeout=60)
                im = Image.open(io.BytesIO(r.content)).convert('RGB'); im.thumbnail((cw - 4, ch - 20))
                sheet.paste(im, ((i % 6) * cw + 2, (i // 6) * ch + 18))
            except Exception as e:  # noqa: BLE001
                print('err', a, repr(e)[:80])
            ImageDraw.Draw(sheet).text(((i % 6) * cw + 3, (i // 6) * ch + 3), '%03d %s' % (sn + i, a[5:40]), fill=(255, 255, 0))
            time.sleep(.5)
        sheet.save(os.path.join(OUT, 'dsheet-%s-%02d.jpg' % (key, sn // per)), quality=80)
