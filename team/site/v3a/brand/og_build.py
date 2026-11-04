# -*- coding: utf-8 -*-
"""Картинки для превью ссылок (og:image, 1200×630) → assets/og/*.png.
Фон — «шёлк» баннеров канала (render/poster.py: _fluid_bg + _canvas_texture, как в daily/deck_bg.py),
надпись «JARVIS | РАЗДЕЛ» разрядкой (Inter ExtraBold), под ней короткая строка.
    python team/site/v3a/brand/og_build.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
V3A = os.path.abspath(os.path.join(HERE, '..'))
REPO = os.path.abspath(os.path.join(V3A, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'render'))
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
import poster  # noqa: E402

W, H = 1200, 630
OUT = os.path.join(V3A, 'assets', 'og')
FONTS = [os.path.join(REPO, 'render', 'fonts', 'Inter-ExtraBold.otf'), '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf',
         os.path.join(REPO, 'render', 'fonts', 'Montserrat[wght].ttf')]
SUB = 'Прогнозы по расчёту, а не наугад'
NAVY = (10, 18, 32)
# имя файла: (раздел, акцент, цвет1, цвет2, строка)
PAGES = {
    'home':    (None,         (255, 194, 26), (30, 62, 124), (14, 26, 52), SUB),
    'hockey':  ('ХОККЕЙ',     (90, 184, 255), (24, 82, 150), (10, 22, 48), 'КХЛ и НХЛ: линия и расчёт модели у каждого матча'),
    'football':('ФУТБОЛ',     (61, 214, 140), (20, 106, 84), (8, 28, 36),  'АПЛ, Ла Лига, Серия А, Бундеслига, ЛЧ'),
    'khl':     ('КХЛ',        (255, 194, 26), (120, 84, 14), (30, 22, 20), SUB),
    'nhl':     ('НХЛ',        (90, 184, 255), (24, 82, 150), (10, 22, 48), SUB),
    'matches': ('МАТЧИ ДНЯ',  (255, 194, 26), (30, 62, 124), (14, 26, 52), 'Хоккей и футбол: линия и вывод модели по каждому матчу'),
}


def font(size):
    for p in FONTS:
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            if p.endswith('.ttf'):
                try: f.set_variation_by_axes([800])
                except Exception: pass  # noqa: E722
            return f
    raise SystemExit('нет шрифта Inter/Montserrat')


def tracked(d, x, y, text, f, fill, track):
    """Разрядка: рисуем по буквам; возвращает x после последней."""
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + track
    return x - track


def width(d, text, f, track):
    return sum(d.textlength(c, font=f) for c in text) + track * (len(text) - 1)


def build(name):
    sec, acc, c1, c2, line = PAGES[name]
    bg = poster._fluid_bg(W // 2, H // 2, c1, c2, seed=21 + len(name)).resize((W, H), Image.BICUBIC).convert('RGB')
    bg = poster._canvas_texture(bg, 1.0)
    a = np.asarray(bg).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx / W - .5) * 1.15) ** 2 + ((yy / H - .5)) ** 2)
    a *= (.80 * (1 - .45 * np.clip(r - .28, 0, 1)))[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype('uint8'), 'RGB')
    im = im.quantize(72, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).convert('RGB')
    d = ImageDraw.Draw(im)
    fs = 76 if sec and len(sec) > 6 else 88
    f, tr = font(fs), fs * .16
    parts = [('JARVIS', (255, 255, 255))] + ([('|', (255, 255, 255, 90)), (sec, acc)] if sec else [])
    gap = fs * .5
    tw = sum(width(d, t, f, tr) for t, _ in parts) + gap * (len(parts) - 1)
    x, y = (W - tw) / 2, H / 2 - fs * .85
    for t, col in parts:
        if t == '|':
            lw = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(lw).text((x, y), t, font=font(fs), fill=(255, 255, 255, 95))
            im.paste(lw, (0, 0), lw)
            d = ImageDraw.Draw(im)
            x += width(d, t, f, 0) + gap
            continue
        x = tracked(d, x, y, t, f, col, tr) + gap
    d.rectangle([W / 2 - 46, y + fs * 1.5, W / 2 + 46, y + fs * 1.5 + 6], fill=(255, 194, 26))
    fl = font(38)
    lw_ = width(d, line, fl, 0.5)
    tracked(d, (W - lw_) / 2, y + fs * 1.5 + 40, line, fl, (225, 235, 250), .5)
    q = im.quantize(160, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    p = os.path.join(OUT, 'og-%s.png' % name)
    q.save(p, optimize=True)
    return os.path.getsize(p)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for n in PAGES:
        print(n, build(n) // 1024, 'КБ')
