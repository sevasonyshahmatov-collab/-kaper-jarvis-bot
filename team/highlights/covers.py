# -*- coding: utf-8 -*-
"""Обложки актуального Instagram «Экспресс» (итоги экспрессов, владелец 15.11) — 4 варианта + превью кружков.
Кадр 1080×1920; Instagram берёт квадрат по центру и режет в круг — рисунок держим в круге R≈380 от центра.
    PYTHONPATH=render python3 team/highlights/covers.py out/highlights/covers"""
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'render'))
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
import matchday_vs as mv  # noqa: E402

W, H = 1080, 1920
CX, CY = W // 2, H // 2
ICE = (122, 202, 255)
WIN = (46, 190, 105)
LOSS = (225, 70, 70)
DARK = (20, 22, 28)
WHITE = (245, 245, 245)
FONTS = os.path.join(ROOT, 'render', 'fonts')


def font(name, size, wght):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    try:
        f.set_variation_by_axes([wght])
    except Exception:
        pass
    return f


def base(glow=ICE):
    import numpy as np
    img = mv._background(H).convert('RGB').resize((W, H))
    g = Image.new('RGB', (W, H), (0, 0, 0))                 # мягкое свечение акцентом за рисунком
    ImageDraw.Draw(g).ellipse((CX - 420, CY - 420, CX + 420, CY + 420), fill=tuple(int(c * .28) for c in glow))
    g = g.filter(ImageFilter.GaussianBlur(160))
    img = Image.fromarray(np.clip(np.asarray(img, 'int16') + np.asarray(g, 'int16'), 0, 255).astype('uint8'))
    return img, ImageDraw.Draw(img)


def check(d, cx, cy, s, col, w):
    d.line([(cx - s * .5, cy), (cx - s * .12, cy + s * .38), (cx + s * .55, cy - s * .4)], fill=col, width=w, joint='curve')
    for x, y in ((cx - s * .5, cy), (cx + s * .55, cy - s * .4)):
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=col)


def ring(d, col=ICE, r=400, w=14):
    d.ellipse((CX - r, CY - r, CX + r, CY + r), outline=col, width=w)


def v_coupon(out):
    """Купон-чек с зубчатым краем: три строки-ноги с галочками, внизу большая галочка."""
    img, d = base()
    x0, x1, y0, y1 = CX - 210, CX + 210, CY - 300, CY + 280
    pts = [(x0, y0), (x1, y0), (x1, y1)]
    n = 10
    for i in range(n + 1):
        x = x1 - (x1 - x0) * i / n
        pts.append((x, y1 if i % 2 == 0 else y1 - 34))
    pts.append((x0, y0))
    d.polygon(pts, fill=WHITE)
    for i in range(3):
        y = y0 + 70 + i * 92
        d.rounded_rectangle((x0 + 50, y - 13, x0 + 250, y + 13), radius=13, fill=(200, 204, 212))
        d.ellipse((x1 - 100, y - 30, x1 - 40, y + 30), fill=WIN)
        check(d, x1 - 70, y + 2, 34, WHITE, 8)
    d.line((x0 + 40, y0 + 330, x1 - 40, y0 + 330), fill=(200, 204, 212), width=5)
    check(d, CX, y0 + 435, 150, DARK, 30)
    img.save(out, quality=95)


def v_text(out):
    """Слово «ЭКСПРЕСС» крупно, под ним «ИТОГИ» и три галочки."""
    img, d = base()
    ring(d)
    f = font('AlumniSans[wght].ttf', 230, 900)
    mv._txt(d, CX, CY - 70, 'ЭКСПРЕСС', mv._fit_w('ЭКСПРЕСС', 'AlumniSans[wght].ttf', 900, 230, 640), WHITE)
    f2 = font('Oswald[wght].ttf', 64, 600)
    t = 'И Т О Г И'
    d.text((CX, CY + 70), t, font=f2, fill=ICE, anchor='mm')
    for i, x in enumerate((CX - 120, CX, CX + 120)):
        d.ellipse((x - 42, CY + 150, x + 42, CY + 234), fill=WIN)
        check(d, x, CY + 194, 44, WHITE, 10)
    img.save(out, quality=95)


def v_chain(out):
    """Звенья цепи (экспресс) и бейдж с галочкой."""
    img, d = base()
    ring(d)
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    w, h, t = 300, 150, 40
    for dx in (-110, 110):
        ld.rounded_rectangle((CX + dx - w / 2, CY - h / 2, CX + dx + w / 2, CY + h / 2), radius=h / 2,
                             outline=WHITE if dx < 0 else ICE, width=t)
    layer = layer.rotate(32, center=(CX, CY - 20), resample=Image.BICUBIC)
    img.paste(layer, (0, 0), layer)
    bx, by, br = CX + 170, CY + 170, 95
    d.ellipse((bx - br - 12, by - br - 12, bx + br + 12, by + br + 12), fill=DARK)
    d.ellipse((bx - br, by - br, bx + br, by + br), fill=WIN)
    check(d, bx, by + 4, 100, WHITE, 22)
    img.save(out, quality=95)


def v_legs(out):
    """Три полосы-ноги купона с отметками (две ✅, одна ❌ → честно) — «итоги»; сверху маленькое «ЭКСПРЕСС»."""
    img, d = base()
    ring(d)
    f = font('Oswald[wght].ttf', 52, 700)
    d.text((CX, CY - 245), 'Э К С П Р Е С С', font=f, fill=ICE, anchor='mm')
    for i, ok in enumerate((True, True, True)):
        y = CY - 130 + i * 140
        d.rounded_rectangle((CX - 280, y - 50, CX + 280, y + 50), radius=50, fill=(36, 39, 48), outline=(70, 75, 90), width=4)
        d.rounded_rectangle((CX - 230, y - 12, CX + 80, y + 12), radius=12, fill=(120, 126, 140))
        d.ellipse((CX + 160, y - 38, CX + 236, y + 38), fill=WIN if ok else LOSS)
        check(d, CX + 198, y + 3, 42, WHITE, 10)
    img.save(out, quality=95)


def preview(files, out):
    """Как выглядит в профиле: кружки 260 px на светлом и тёмном фоне, с подписью."""
    n = len(files)
    cell = 330
    sheet = Image.new('RGB', (cell * n, 2 * cell + 40), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    sheet.paste((0, 0, 0), (0, cell + 20, cell * n, 2 * cell + 40))
    f = font('Manrope[wght].ttf', 26, 600)
    for i, p in enumerate(files):
        im = Image.open(p)
        sq = im.crop((0, (H - W) // 2, W, (H + W) // 2)).resize((240, 240), Image.LANCZOS)
        m = Image.new('L', (240, 240), 0)
        ImageDraw.Draw(m).ellipse((0, 0, 239, 239), fill=255)
        for row, (bg, fg) in enumerate((((255, 255, 255), (20, 20, 20)), ((0, 0, 0), (240, 240, 240)))):
            ox, oy = i * cell + 45, row * (cell + 20) + 20
            d.ellipse((ox - 6, oy - 6, ox + 246, oy + 246), outline=(200, 200, 200), width=3)
            sheet.paste(sq, (ox, oy), m)
            d.text((ox + 120, oy + 272), '%d · Экспресс' % (i + 1), font=f, fill=fg, anchor='mm')
    sheet.save(out, quality=92)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/highlights/covers'
    os.makedirs(out, exist_ok=True)
    fs = []
    for name, fn in (('1_kupon', v_coupon), ('2_tekst', v_text), ('3_cep', v_chain), ('4_nogi', v_legs)):
        p = os.path.join(out, 'cover_%s.jpg' % name)
        fn(p)
        fs.append(p)
    preview(fs, os.path.join(out, 'preview.jpg'))
    print('\n'.join(fs + [os.path.join(out, 'preview.jpg')]))
