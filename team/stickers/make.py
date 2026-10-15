# -*- coding: utf-8 -*-
"""Стикеры-плашки для Telegram в стиле постов канала (Versus): тёмная плашка с кольцами, цвет статуса, Montserrat 900.
512×512 PNG с прозрачным фоном — формат статичных стикеров Telegram.
Запуск: PYTHONPATH=render python team/stickers/make.py <папка> [ключи…]"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'render', 'fonts')
S = 4                                   # рисуем крупно и уменьшаем — ровные края
W = 512 * S


def font(name, wght, size):
    f = ImageFont.truetype(os.path.join(FD, name), size * S)
    try:
        f.set_variation_by_axes([wght])
    except Exception:  # noqa: BLE001
        pass
    return f


# ключ: (главное слово, подпись, цвет плашки, цвет текста, значок, наклон)
STICKERS = {
    'zahod': ('ЗАХОД', 'прогноз зашёл', (46, 214, 120), None, 'check', -6),
    'stavka_dnya': ('СТАВКА ДНЯ', 'главный прогноз', (255, 194, 61), None, 'star', 4),
    'minus': ('МИНУС', 'бывает и так', (240, 82, 70), None, 'cross', 5),
    'vozvrat': ('ВОЗВРАТ', 'деньги вернулись', (122, 202, 255), None, 'back', -4),
}


def icon(d, kind, cx, cy, r, col):
    w = int(r * 0.32)
    if kind == 'check':
        d.line([(cx - r * .55, cy + r * .02), (cx - r * .12, cy + r * .45), (cx + r * .62, cy - r * .45)], fill=col, width=w, joint='curve')
    elif kind == 'cross':
        d.line([(cx - r * .5, cy - r * .5), (cx + r * .5, cy + r * .5)], fill=col, width=w)
        d.line([(cx - r * .5, cy + r * .5), (cx + r * .5, cy - r * .5)], fill=col, width=w)
    elif kind == 'star':
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = r * (0.75 if i % 2 == 0 else 0.32)
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=col)
    elif kind == 'back':
        d.arc([cx - r * .6, cy - r * .6, cx + r * .6, cy + r * .6], 200, 520, fill=col, width=w)
        d.polygon([(cx - r * .85, cy - r * .1), (cx - r * .35, cy - r * .1), (cx - r * .6, cy + r * .35)], fill=col)


BG = (22, 20, 24)                      # фон баннеров Versus


def sticker(word, sub, acc, _fg, ico, tilt):
    """Плашка в стиле постов: тёмная, с кольцами в цвете статуса, кружок со значком, белое слово, подпись акцентом."""
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    lay = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cr = 34 * S
    size = 84
    while True:
        big = font('Montserrat[wght].ttf', 900, size)
        tw = d.textlength(word, font=big)
        pw = 22 * S + 2 * cr + 20 * S + tw + 34 * S
        if pw <= 430 * S or size <= 40:
            break
        size -= 2
    small = font('Unbounded[wght].ttf', 600, 16)
    ph = 150 * S
    x0, y0 = (W - pw) / 2, (W - ph) / 2
    rad = 30 * S
    box = [x0, y0, x0 + pw, y0 + ph]
    mask = Image.new('L', (W, W), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, rad, fill=255)
    panel = Image.new('RGBA', (W, W), BG + (255,))
    rings = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    pd = ImageDraw.Draw(rings)
    # концентрические кольца из угла — как узор панелей Versus (отдельным слоем, чтобы смешались с фоном)
    ox, oy = x0 + pw * 0.92, y0 + ph * 0.1
    for i in range(1, 40):
        r = i * 16 * S
        pd.ellipse([ox - r, oy - r, ox + r, oy + r], outline=acc + (30,), width=3 * S)
    panel = Image.alpha_composite(panel, rings)
    # мягкое свечение цвета статуса слева
    glow = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([x0 - 60 * S, y0 - 40 * S, x0 + 220 * S, y0 + ph + 40 * S], fill=acc + (70,))
    panel = Image.alpha_composite(panel, glow.filter(ImageFilter.GaussianBlur(40 * S)))
    lay.paste(panel, (0, 0), mask)
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle(box, rad, outline=acc + (255,), width=5 * S)          # рамка цвета статуса
    cx, cy = x0 + 22 * S + cr, y0 + ph * .44
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=acc + (255,))
    icon(d, ico, cx, cy, cr, BG)
    tx = cx + cr + 20 * S
    d.text((tx, y0 + ph * .40), word, font=big, fill=(255, 255, 255), anchor='lm')
    d.text((tx + 3 * S, y0 + ph * .78), sub.upper(), font=small, fill=acc, anchor='lm')
    d.text((x0 + pw - 20 * S, y0 + 16 * S), 'JARVIS', font=font('Unbounded[wght].ttf', 800, 11), fill=(255, 255, 255, 110), anchor='rt')
    lay = lay.rotate(tilt, resample=Image.BICUBIC, center=(W / 2, W / 2))
    a = lay.split()[3]
    outline = a.filter(ImageFilter.MaxFilter(1 + 2 * (9 * S // 2)))
    shadow = outline.filter(ImageFilter.GaussianBlur(10 * S)).point(lambda v: v * 0.5)
    img.paste((0, 0, 0, 255), (0, 6 * S), shadow)
    img.paste((255, 255, 255, 255), (0, 0), outline)
    img = Image.alpha_composite(img, lay)
    img = img.crop(img.getbbox())                       # стикер Telegram: одна сторона ровно 512, вторая — до 512
    k = 512 / max(img.size)
    return img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/stickers'
    keys = sys.argv[2:] or list(STICKERS)
    os.makedirs(out, exist_ok=True)
    for k in keys:
        sticker(*STICKERS[k]).save(os.path.join(out, k + '.png'))
        print(os.path.join(out, k + '.png'))
