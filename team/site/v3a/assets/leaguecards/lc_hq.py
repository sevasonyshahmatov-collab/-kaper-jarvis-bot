# -*- coding: utf-8 -*-
"""Фото высокого качества для карточек лиг (черновик 14.11). Только Commons, только CC BY / CC BY-SA / CC0 / PD.
hq.json: {"discover": {ключ: {cats:[...], qs:[...], depth:1}}, "cut": {имя: {t: "File:...", box:[x0,y0,x1,y1] доли, h: 1800}}}
discover -> cand/hq-<ключ>.txt + cand/hqsheet-<ключ>-NN.jpg (только длинная сторона >= 2500 px)
cut      -> оригинал -> кадр box -> rembg (birefnet) -> cand/cut-<имя>.webp (q90) + cand/cutprev-<имя>.jpg + cand/hqmeta.json"""
import io, json, os, re, time, html
import requests
from PIL import Image, ImageDraw, ImageFilter
Image.MAX_IMAGE_PIXELS = None
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, 'cand'); os.makedirs(OUT, exist_ok=True)
S = requests.Session(); S.headers['User-Agent'] = 'JarvisSiteBot/1.0 (league cards; github.com/sevasonyshahmatov-collab)'
API = 'https://commons.wikimedia.org/w/api.php'
OK_LIC = re.compile(r'^(cc[- ]by(-sa)?[- ]\d|cc0|pd|public domain)', re.I)
cfg = json.load(open(os.path.join(H, 'hq.json'), encoding='utf-8'))


def api(**p):
    p.update(format='json')
    for k in range(5):
        try:
            r = S.get(API, params=p, timeout=60)
            if r.status_code == 429: time.sleep(10 * (k + 1)); continue
            return r.json()
        except Exception:
            time.sleep(5)
    return {}


def strip(s): return html.unescape(re.sub(r'<[^>]+>', '', s or '')).strip()


def files(cat, depth, maxc=40, deadline=None):
    out, cats, todo = [], [], [(cat, 0)]
    while todo and len(cats) < maxc:
        c, d = todo.pop(0)
        if c in cats: continue
        cats.append(c)
        if d < depth:
            j = api(action='query', list='categorymembers', cmtitle=c, cmtype='subcat', cmlimit=200)
            todo += [(m['title'], d + 1) for m in (j.get('query') or {}).get('categorymembers', [])]
    for c in cats:
        cont = {}
        while True:
            j = api(action='query', list='categorymembers', cmtitle=c, cmtype='file', cmlimit=500, **cont)
            out += [m['title'] for m in (j.get('query') or {}).get('categorymembers', [])]
            if 'continue' not in j or len(out) > 3000: break
            cont = {'cmcontinue': j['continue']['cmcontinue']}
    return out


def search(q):
    out = []
    for off in (0, 50, 100):
        j = api(action='query', list='search', srsearch=q, srnamespace=6, srlimit=50, sroffset=off)
        r = [m['title'] for m in (j.get('query') or {}).get('search', [])]
        out += r
        if len(r) < 50: break
    return out


def info(titles, w=360):
    res = []
    for k in range(0, len(titles), 40):
        j = api(action='query', prop='imageinfo', iiprop='url|size|mime|extmetadata', iiurlwidth=w, titles='|'.join(titles[k:k + 40]))
        for pg in ((j.get('query') or {}).get('pages') or {}).values():
            ii = (pg.get('imageinfo') or [None])[0]
            if ii: res.append((pg['title'], ii))
        time.sleep(.5)
    return res


def lic_of(ii):
    em = ii.get('extmetadata') or {}
    return (strip((em.get('LicenseShortName') or {}).get('value')), strip((em.get('Artist') or {}).get('value'))[:80],
            strip((em.get('DateTimeOriginal') or {}).get('value'))[:10], strip((em.get('LicenseUrl') or {}).get('value')))


for key, c in (cfg.get('discover') or {}).items():
    t = []
    for cat in c.get('cats', []): t += files(cat, c.get('depth', 1))
    for q in c.get('qs', []): t += search(q)
    t = list(dict.fromkeys(x for x in t if re.search(r'\.jpe?g$', x, re.I)))
    if c.get('filter'): t = [x for x in t if re.search(c['filter'], x, re.I)]
    t = t[:c.get('maxt', 900)]   # не больше maxt файлов на ключ — иначе поиск не укладывается в 40 мин (14.11)
    print(key, 'найдено', len(t), flush=True)
    ok = []
    for title, ii in info(t):
        lic, au, d, _ = lic_of(ii)
        if OK_LIC.match(lic) and max(ii['width'], ii['height']) >= c.get('min', 2500):
            ok.append((title, ii, lic, au, d))
    ok.sort(key=lambda x: (x[4], x[0]), reverse=True); ok = ok[:c.get('max', 144)]
    print(key, 'свободных и крупных', len(ok), flush=True)
    open(os.path.join(OUT, 'hq-%s.txt' % key), 'w', encoding='utf-8').write(
        '\n'.join('%03d\t%s\t%dx%d\t%s\t%s\t%s' % (i, a, b['width'], b['height'], l, au, d) for i, (a, b, l, au, d) in enumerate(ok)))
    cw, ch, per = 320, 340, 24
    for sn in range(0, len(ok), per):
        chunk = ok[sn:sn + per]; sheet = Image.new('RGB', (cw * 6, ch * 4), (30, 30, 40))
        for i, (a, b, l, au, d) in enumerate(chunk):
            try:
                r = S.get(b.get('thumburl') or b['url'], timeout=60)
                im = Image.open(io.BytesIO(r.content)).convert('RGB'); im.thumbnail((cw - 4, ch - 22))
                sheet.paste(im, ((i % 6) * cw + 2, (i // 6) * ch + 20))
            except Exception as e:  # noqa: BLE001
                print('err', a, repr(e)[:80])
            ImageDraw.Draw(sheet).text(((i % 6) * cw + 3, (i // 6) * ch + 3), '%03d %dx%d %s' % (sn + i, b['width'], b['height'], a[5:30]), fill=(255, 255, 0))
            time.sleep(.1)
        sheet.save(os.path.join(OUT, 'hqsheet-%s-%02d.jpg' % (key, sn // per)), quality=82)

cut = cfg.get('cut') or {}
if cut:
    import rembg
    sess = None
    for m in ('birefnet-general', 'isnet-general-use'):
        try:
            sess = rembg.new_session(m); print('модель', m, flush=True); break
        except Exception as e:  # noqa: BLE001
            print('нет модели', m, repr(e)[:100])
    mp = os.path.join(OUT, 'hqmeta.json')
    meta = json.load(open(mp, encoding='utf-8')) if os.path.exists(mp) else {}
    for name, c in cut.items():
        try:
            (title, ii), = info([c['t']], 2000)
            lic, au, d, lu = lic_of(ii)
            if not OK_LIC.match(lic): print('лицензия не подходит', title, lic); continue
            r = S.get(ii['url'], timeout=180); src = Image.open(io.BytesIO(r.content))
            from PIL import ImageOps
            src = ImageOps.exif_transpose(src).convert('RGB')
            b = c.get('box') or [0, 0, 1, 1]
            src = src.crop((round(b[0] * src.width), round(b[1] * src.height), round(b[2] * src.width), round(b[3] * src.height)))
            src.save(os.path.join(OUT, 'crop-%s.jpg' % name), quality=85) if c.get('savecrop') else None
            out = rembg.remove(src, session=sess, post_process_mask=True)
            a = out.getchannel('A')
            bb = a.point(lambda v: 255 if v > 40 else 0).getbbox()
            out = out.crop(bb)
            # убрать ореол: альфу чуть сжать и смягчить
            a = out.getchannel('A').filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(.6))
            out.putalpha(a)
            hh = c.get('h', 1800)
            if out.height > hh: out = out.resize((round(out.width * hh / out.height), hh), Image.LANCZOS)
            out.save(os.path.join(OUT, 'cut-%s.webp' % name), 'WEBP', quality=90, method=6)
            pv = Image.new('RGBA', out.size, (40, 60, 110, 255)); pv.alpha_composite(out); pv.thumbnail((900, 1200))
            pv.convert('RGB').save(os.path.join(OUT, 'cutprev-%s.jpg' % name), quality=85)
            meta[name] = {'title': title, 'page': ii.get('descriptionurl'), 'author': au, 'license': lic, 'license_url': lu,
                          'date': d, 'src': '%dx%d' % (ii['width'], ii['height']), 'cut': '%dx%d' % out.size}
            print('ok', name, out.size, lic, au, flush=True)
        except Exception as e:  # noqa: BLE001
            print('err', name, repr(e)[:200], flush=True)
    json.dump(meta, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
