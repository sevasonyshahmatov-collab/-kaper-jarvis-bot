# -*- coding: utf-8 -*-
"""Фото для карточек лиг (КХЛ - Локомотив, НХЛ - Каролина): Commons (только CC BY / CC BY-SA / CC0 / PD) -> rembg -> cand/*.webp + meta.json.
Список всех найденных файлов пишется в cand/titles-<ключ>.txt; если рядом есть want.json {ключ: [заголовки файлов]} - берутся именно они."""
import io, json, os, re, time, html
import requests
from PIL import Image, ImageDraw

H = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(H, 'cand')
os.makedirs(OUT, exist_ok=True)
S = requests.Session()
S.headers['User-Agent'] = 'JarvisSiteBot/1.0 (league cards mockup; github.com/sevasonyshahmatov-collab)'
API = 'https://commons.wikimedia.org/w/api.php'
# ключ: (категории, поисковые запросы)
TARGETS = {
    'car-aho': (['Category:Sebastian Aho (ice hockey, born 1997)'], ['Sebastian Aho Hurricanes']),
    'car-svechnikov': (['Category:Andrei Svechnikov'], ['Andrei Svechnikov Hurricanes']),
    'car-jarvis': (['Category:Seth Jarvis'], ['Seth Jarvis Hurricanes']),
    'car-slavin': (['Category:Jaccob Slavin'], ['Jaccob Slavin Hurricanes']),
    'car-team': (['Category:Carolina Hurricanes players', 'Category:Carolina Hurricanes'], ['Carolina Hurricanes player']),
    'lok': (['Category:Lokomotiv Yaroslavl players', 'Category:HC Lokomotiv Yaroslavl', 'Category:Lokomotiv Yaroslavl'],
            ['Lokomotiv Yaroslavl hockey player', 'Локомотив Ярославль хоккей', 'Lokomotiv KHL game']),
}
OK_LIC = re.compile(r'^(cc[- ]by(-sa)?[- ]\d|cc0|pd|public domain)', re.I)
PER = 24
want = {}
if os.path.exists(os.path.join(H, 'want.json')):
    want = json.load(open(os.path.join(H, 'want.json'), encoding='utf-8'))


def api(**p):
    p.update(format='json')
    for k in range(4):
        r = S.get(API, params=p, timeout=60)
        if r.status_code == 429:
            time.sleep(10 * (k + 1)); continue
        return r.json()
    return {}


def files(cat, depth=2):
    out, seen, cats, todo = [], set(), [], [(cat, 0)]
    while todo and len(cats) < 30:
        c, d = todo.pop(0); cats.append(c)
        if d < depth:
            j = api(action='query', list='categorymembers', cmtitle=c, cmtype='subcat', cmlimit=40)
            todo += [(m['title'], d + 1) for m in (j.get('query') or {}).get('categorymembers', [])][:15]
    for c in cats:
        j = api(action='query', list='categorymembers', cmtitle=c, cmtype='file', cmlimit=300)
        for m in (j.get('query') or {}).get('categorymembers', []):
            if m['title'] not in seen:
                seen.add(m['title']); out.append(m['title'])
    return out


def search(q):
    j = api(action='query', list='search', srsearch=q, srnamespace=6, srlimit=50)
    return [m['title'] for m in (j.get('query') or {}).get('search', [])]


def info(titles):
    res = []
    for k in range(0, len(titles), 40):
        j = api(action='query', prop='imageinfo', iiprop='url|size|mime|extmetadata', iiurlwidth=1600, titles='|'.join(titles[k:k + 40]))
        for pg in ((j.get('query') or {}).get('pages') or {}).values():
            ii = (pg.get('imageinfo') or [None])[0]
            if ii: res.append((pg['title'], ii))
        time.sleep(1)
    return res


def strip(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s or '')).strip()


import rembg
sess = rembg.new_session('isnet-general-use')
mp = os.path.join(OUT, 'meta.json')
meta = json.load(open(mp, encoding='utf-8')) if os.path.exists(mp) else {}
for key, (cats, qs) in TARGETS.items():
    if want and key not in want: continue
    titles = []
    if key in want:
        titles = want[key]
    else:
        for c in cats: titles += files(c)
        for q in qs: titles += search(q)
        titles = list(dict.fromkeys(titles))
    print(key, 'файлов найдено', len(titles), flush=True)
    cand, lines = [], []
    for t, ii in info(titles):
        em = ii.get('extmetadata') or {}
        lic = strip((em.get('LicenseShortName') or {}).get('value'))
        w, h = ii['width'], ii['height']
        okk = ii.get('mime', '').startswith('image/jpeg') and OK_LIC.match(lic) and h >= 900 and w >= 600
        lines.append('%s\t%s\t%dx%d\t%s' % ('OK ' if okk else 'no ', t, w, h, lic))
        if okk: cand.append((t, ii, lic))
    open(os.path.join(OUT, 'titles-%s.txt' % key), 'w', encoding='utf-8').write('\n'.join(lines))
    if key not in want:
        cand = cand[:PER * 3]
    n = 0
    for t, ii, lic in cand:
        if n >= PER: break
        url = ii.get('thumburl') or ii['url']
        try:
            r = S.get(url, timeout=90)
            if r.status_code != 200:
                print('skip', t, r.status_code, flush=True); time.sleep(5); continue
            src = Image.open(io.BytesIO(r.content)).convert('RGB')
            cut = rembg.remove(src, session=sess)
            bb = cut.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox()
            if not bb: continue
            cut = cut.crop(bb)
            hh = 1000
            cut = cut.resize((max(1, round(cut.width * hh / cut.height)), hh), Image.LANCZOS)
            name = '%s-%02d.webp' % (key, n + 1)
            cut.save(os.path.join(OUT, name), 'WEBP', quality=88, method=6)
            em = ii['extmetadata']
            meta[name] = {'key': key, 'title': t, 'page': ii.get('descriptionurl'),
                          'author': strip((em.get('Artist') or {}).get('value')), 'license': lic,
                          'license_url': strip((em.get('LicenseUrl') or {}).get('value')),
                          'desc': strip((em.get('ImageDescription') or {}).get('value'))[:240],
                          'date': strip((em.get('DateTimeOriginal') or {}).get('value'))[:40], 'w': cut.width, 'h': cut.height}
            n += 1
            print('ok', name, t, lic, flush=True)
        except Exception as e:  # noqa: BLE001
            print('err', t, repr(e)[:120], flush=True)
        time.sleep(2)
    json.dump(meta, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# контактные листы с подписью номера
for key in TARGETS:
    names = sorted(n for n in meta if n.startswith(key + '-'))
    if not names: continue
    cw, ch = 300, 450
    sheet = Image.new('RGB', (cw * 6, ch * ((len(names) + 5) // 6)), (200, 200, 210))
    for i, n in enumerate(names):
        im = Image.open(os.path.join(OUT, n)).convert('RGBA'); im.thumbnail((cw - 10, ch - 30))
        bg = Image.new('RGBA', (cw, ch), (60, 70, 100, 255)); bg.alpha_composite(im, ((cw - im.width) // 2, ch - im.height - 4))
        ImageDraw.Draw(bg).text((6, 4), n[:-5], fill=(255, 255, 255, 255))
        sheet.paste(bg.convert('RGB'), ((i % 6) * cw, (i // 6) * ch))
    sheet.save(os.path.join(OUT, 'sheet-%s.png' % key))
