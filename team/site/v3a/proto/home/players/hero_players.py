# -*- coding: utf-8 -*-
"""Фото игроков для главной (шаблон 1): Commons -> кандидаты -> rembg -> WEBP с прозрачностью (высота ~900) + JSON авторов."""
import io, json, os, re, time, html
import requests
from PIL import Image

H = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(H, 'cand')
os.makedirs(OUT, exist_ok=True)
S = requests.Session()
S.headers['User-Agent'] = 'JarvisSiteBot/1.0 (hero players mockup; github.com/sevasonyshahmatov-collab)'
API = 'https://commons.wikimedia.org/w/api.php'
PLAYERS = {'mcdavid': ['Category:Connor McDavid'], 'mbappe': ['Category:Kylian Mbappé']}
OK_LIC = re.compile(r'^(cc[- ]by(-sa)?[- ]\d|cc0|pd|public domain)', re.I)
PER = 10


def api(**p):
    p.update(format='json')
    for k in range(4):
        r = S.get(API, params=p, timeout=60)
        if r.status_code == 429:
            time.sleep(10 * (k + 1)); continue
        return r.json()
    return {}


def files(cat):
    out, seen = [], set()
    cats = [cat]
    j = api(action='query', list='categorymembers', cmtitle=cat, cmtype='subcat', cmlimit=30)
    cats += [m['title'] for m in (j.get('query') or {}).get('categorymembers', [])][:12]
    for c in cats:
        j = api(action='query', list='categorymembers', cmtitle=c, cmtype='file', cmlimit=200)
        for m in (j.get('query') or {}).get('categorymembers', []):
            if m['title'] not in seen:
                seen.add(m['title']); out.append(m['title'])
    return out


def info(titles):
    res = []
    for k in range(0, len(titles), 40):
        j = api(action='query', prop='imageinfo', iiprop='url|size|mime|extmetadata', iiurlwidth=1600,
                titles='|'.join(titles[k:k + 40]))
        for pg in ((j.get('query') or {}).get('pages') or {}).values():
            ii = (pg.get('imageinfo') or [None])[0]
            if ii: res.append((pg['title'], ii))
        time.sleep(1)
    return res


def strip(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s or '')).strip()


import rembg
sess = rembg.new_session('isnet-general-use')
meta = {}
for key, cats in PLAYERS.items():
    titles = []
    for c in cats:
        titles += files(c)
    print(key, 'файлов в категориях', len(titles), flush=True)
    cand = []
    for t, ii in info(titles):
        em = ii.get('extmetadata') or {}
        lic = strip((em.get('LicenseShortName') or {}).get('value'))
        if not ii.get('mime', '').startswith('image/jpeg') or not OK_LIC.match(lic):
            continue
        w, h = ii['width'], ii['height']
        if h < 1100 or w < 700:
            continue
        cand.append((t, ii, lic, w / h))
    print(key, 'годных по лицензии/размеру', len(cand), flush=True)
    cand.sort(key=lambda x: -x[1]['height'])
    n = 0
    for t, ii, lic, ar in cand:
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
            hh = 900
            cut = cut.resize((max(1, round(cut.width * hh / cut.height)), hh), Image.LANCZOS)
            name = '%s-%02d.webp' % (key, n + 1)
            cut.save(os.path.join(OUT, name), 'WEBP', quality=88, method=6)
            em = ii['extmetadata']
            meta[name] = {'player': key, 'title': t, 'page': ii.get('descriptionurl'),
                          'author': strip((em.get('Artist') or {}).get('value')), 'license': lic,
                          'license_url': strip((em.get('LicenseUrl') or {}).get('value')),
                          'desc': strip((em.get('ImageDescription') or {}).get('value'))[:200],
                          'w': cut.width, 'h': cut.height}
            n += 1
            print('ok', name, t, lic, flush=True)
        except Exception as e:  # noqa: BLE001
            print('err', t, repr(e)[:120], flush=True)
        time.sleep(3)
json.dump(meta, open(os.path.join(H, 'cand', 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# контактный лист на тёмном фоне, чтобы смотреть вырезки
for key in PLAYERS:
    names = sorted(n for n in meta if n.startswith(key))
    if not names: continue
    cw, ch = 360, 540
    sheet = Image.new('RGB', (cw * 5, ch * ((len(names) + 4) // 5)), (200, 200, 210))
    for i, n in enumerate(names):
        im = Image.open(os.path.join(OUT, n)).convert('RGBA'); im.thumbnail((cw - 10, ch - 10))
        bg = Image.new('RGBA', (cw, ch), (60, 70, 100, 255)); bg.alpha_composite(im, ((cw - im.width) // 2, ch - im.height - 4))
        sheet.paste(bg.convert('RGB'), ((i % 5) * cw, (i // 5) * ch))
    sheet.save(os.path.join(OUT, 'sheet-%s.png' % key))
