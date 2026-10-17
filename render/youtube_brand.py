# -*- coding: utf-8 -*-
"""Оформление YouTube-канала (17.10): баннер 2560×1440 и аватар 800×800 — три варианта стиля, плюс примерка
на компьютере, телефоне и телевизоре. Всё важное на баннере — в безопасной зоне 1546×423 по центру (её видно везде:
телефон показывает только её, компьютер — полосу 2560×423, телевизор — весь баннер).

    PYTHONPATH=render python render/youtube_brand.py <папка> [night ice storm] [--lang ru|en]
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reels import core as C  # noqa: E402

BW, BH = 2560, 1440
SAFE = (BW - 1546) // 2, (BH - 423) // 2, (BW + 1546) // 2, (BH + 423) // 2      # x0, y0, x1, y1
DESK = (0, (BH - 423) // 2, BW, (BH + 423) // 2)
GOLD = (222, 186, 110)
NAVY = (14, 26, 52)

TXT = {
    'ru': dict(sub='ПРОГНОЗЫ НА ХОККЕЙ · КХЛ · НХЛ', line='Каждый день · Telegram @jarvibet'),
    'en': dict(sub='NHL PICKS & PREVIEWS', line='Every game, every day'),
}


def noise(w, h, scale, seed, octaves=3):
    rng = np.random.default_rng(seed)
    n = np.zeros((h, w), np.float32)
    for k in range(octaves):
        s = max(2, int(scale / (2 ** k)))
        g = rng.random((h // s + 2, w // s + 2)).astype(np.float32)
        n += np.asarray(Image.fromarray(g).resize((w, h), Image.BICUBIC)) / (2 ** k)
    return (n - n.min()) / (n.max() - n.min() + 1e-6)


def scratches(w, h, seed, n=260, a=26, col=(255, 255, 255)):
    """Царапины коньков на льду: тонкие длинные дуги."""
    rng = np.random.default_rng(seed)
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for _ in range(n):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        L = rng.uniform(80, 520)
        ang = rng.uniform(-0.5, 0.5) + (math.pi if rng.random() < 0.5 else 0)
        bend = rng.uniform(-0.002, 0.002)
        pts = []
        for i in range(12):
            t = i / 11 * L
            pts.append((x + math.cos(ang + bend * t) * t, y + math.sin(ang + bend * t) * t))
        d.line(pts, fill=col + (int(rng.uniform(0.3, 1) * a),), width=1)
    return lay


def wordmark(txt, size, fill, track=0.08, glow=None):
    im = C.text(txt, 'unb', size, fill, 800, track=track)
    if glow:
        im = C.glow(im, int(size * 0.12), 0.5, glow)
    return im


def gold_text(txt, size, font='mont', wght=800, track=0.3):
    im = C.text(txt, font, size, (255, 255, 255), wght, track=track)
    g = C.lgrad(im.width, im.height, (246, 222, 160), (188, 146, 72), angle=90)
    g.putalpha(im.getchannel('A'))
    return g


def rink_lines(w, h, cx, cy, s=1.0, a=40, light=False):
    """Разметка центра площадки: красная линия, синие, круг вбрасывания — едва видно."""
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    red, blue = (200, 50, 60), (50, 90, 200)
    d.line((cx, 0, cx, h), fill=red + (a,), width=int(14 * s))
    for dx in (-620, 620):
        d.line((cx + dx * s, 0, cx + dx * s, h), fill=blue + (a,), width=int(18 * s))
    r = 300 * s
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=blue + (a,), width=int(8 * s))
    d.ellipse((cx - 14 * s, cy - 14 * s, cx + 14 * s, cy + 14 * s), fill=blue + (a,))
    return lay.filter(ImageFilter.GaussianBlur(1.2))


# ─────────────────────────── 1. «Ночь» — тёмная арена, золото ───────────────────────────
def banner_night(lang):
    t = TXT[lang]
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    cx, cy = BW / 2, BH / 2
    base = np.array((7, 11, 20), np.float32)[None, None, :] * np.ones((BH, BW, 1), np.float32)
    glow = np.exp(-(((xx - cx) / 1100) ** 2 + ((yy - cy) / 520) ** 2))
    base += (glow * 30)[..., None] * np.array((0.6, 0.75, 1.0))
    n = noise(BW, BH, 260, 3)
    base += ((n - 0.5) * 8)[..., None]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    img.alpha_composite(rink_lines(BW, BH, cx, cy, 1.0, 34))
    img.alpha_composite(scratches(BW, BH, 5, 300, 18))
    # лучи прожекторов сверху
    beams = Image.new('RGBA', (BW, BH), (0, 0, 0, 0))
    bd = ImageDraw.Draw(beams)
    for x0, ang in ((560, 18), (1280, 0), (2000, -18)):
        a = math.radians(90 + ang)
        L = 1700
        for sp, al in ((0.10, 16), (0.05, 22)):
            pts = [(x0, -60), (x0 + L * math.cos(a - sp), -60 + L * math.sin(a - sp)),
                   (x0 + L * math.cos(a + sp), -60 + L * math.sin(a + sp))]
            bd.polygon(pts, fill=(170, 196, 255, al))
    img.alpha_composite(beams.filter(ImageFilter.GaussianBlur(40)))
    img = C.vignette(img, 0.55, 2.0).convert('RGBA')
    # текст — по центру безопасной зоны
    wm = wordmark('JARVIS', 190, (246, 246, 250), 0.1, glow=(140, 170, 255))
    C.put(img, wm, cx, cy - 70)
    C.put(img, gold_text(t['sub'], 50), cx, cy + 82)
    ln = Image.new('RGBA', (900, 4), GOLD + (150,))
    C.put(img, ln, cx, cy + 130)
    C.put(img, C.text(t['line'], 'mont', 40, (196, 204, 222), 600, track=0.04), cx, cy + 172)
    return img


def avatar_night():
    S = 800
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    bg = C.radial(S, S, (24, 36, 66), 255, 0.8)
    disc = Image.new('RGBA', (S, S), (8, 12, 22, 255))
    disc.alpha_composite(bg)
    m = Image.new('L', (S, S), 0)
    ImageDraw.Draw(m).ellipse((0, 0, S - 1, S - 1), fill=255)
    disc.putalpha(m)
    im.alpha_composite(disc)
    ring = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((40, 40, S - 40, S - 40), outline=GOLD + (255,), width=10)
    im.alpha_composite(ring)
    j = gold_text('J', 470, 'unb', 800, 0)
    C.put(im, C.glow(j, 26, 0.35, (255, 210, 130)), S / 2, S / 2 + 10)
    return im


# ─────────────────────────── 2. «Лёд» — светлый, как обложка канала ───────────────────────────
def banner_ice(lang):
    t = TXT[lang]
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    cx, cy = BW / 2, BH / 2
    n = noise(BW, BH, 300, 7)
    base = np.array((226, 236, 246), np.float32)[None, None, :] + ((n - 0.5) * 18)[..., None]
    base -= (np.clip((np.abs(yy - cy) / 900) ** 2, 0, 1) * 30)[..., None]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    img.alpha_composite(rink_lines(BW, BH, cx, cy, 1.0, 60))
    img.alpha_composite(scratches(BW, BH, 9, 420, 70, (150, 170, 196)))
    frost = Image.fromarray((np.clip((n - 0.45) * 3, 0, 1) * 90).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
    fl = Image.new('RGBA', (BW, BH), (255, 255, 255, 0))
    fl.putalpha(frost)
    img.alpha_composite(fl)
    wm = wordmark('JARVIS', 190, NAVY, 0.1)
    C.put(img, C.shadow(wm, r=14, a=0.25), cx + 6, cy - 70 + 10)
    C.put(img, wm, cx, cy - 70)
    sub = C.text(t['sub'], 'mont', 50, (176, 128, 40), 800, track=0.3)
    C.put(img, sub, cx, cy + 82)
    C.put(img, Image.new('RGBA', (900, 4), NAVY + (90,)), cx, cy + 130)
    C.put(img, C.text(t['line'], 'mont', 40, (60, 76, 104), 600, track=0.04), cx, cy + 172)
    return img


def avatar_ice():
    S = 800
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    n = noise(S, S, 120, 4)
    arr = np.array((232, 240, 248), np.float32)[None, None, :] + ((n - 0.5) * 20)[..., None]
    disc = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    disc.alpha_composite(scratches(S, S, 2, 70, 80, (150, 170, 196)))
    m = Image.new('L', (S, S), 0)
    ImageDraw.Draw(m).ellipse((0, 0, S - 1, S - 1), fill=255)
    disc.putalpha(m)
    im.alpha_composite(disc)
    puck = C.ellipse(560, 560, NAVY)
    C.put(im, C.shadow(puck, r=18, a=0.35), S / 2 + 8, S / 2 + 16)
    C.put(im, puck, S / 2, S / 2)
    ring = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((140, 140, S - 140, S - 140), outline=GOLD + (255,), width=8)
    im.alpha_composite(ring)
    C.put(im, gold_text('J', 330, 'unb', 800, 0), S / 2, S / 2 + 8)
    return im


# ─────────────────────────── 3. «Гроза» — ч/б ночное небо, молния ───────────────────────────
def _bolt_light(w, h, seed, x0, y0, x1, y1):
    from reels.premium import _tree
    rng = np.random.default_rng(seed)
    segs = []
    _tree(rng, None, x0, y0, x1, y1, 0, segs)
    core = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(core)
    for pts, width, val in sorted(segs, key=lambda s: s[2]):
        d.line(pts, fill=val, width=width + 1, joint='curve')
    acc = np.zeros((h, w), np.float32)
    for r, g in ((0, 1.0), (2, 1.5), (9, 1.3), (40, 1.5)):
        lay = core.filter(ImageFilter.GaussianBlur(r)) if r else core
        acc += np.asarray(lay, np.float32) * g
    return np.clip(acc, 0, 255)


def banner_storm(lang):
    t = TXT[lang]
    cx, cy = BW / 2, BH / 2
    n = noise(BW, BH, 420, 11, 4)
    cl = n ** 1.5
    yy = np.mgrid[0:BH, 0:BW][0].astype(np.float32)
    lum = 6 + cl * 70 * (0.55 + 0.45 * np.exp(-((yy - cy) / 700) ** 2))
    bolt = _bolt_light(BW, BH, 99, 2330, -40, 2180, BH * 0.95)
    bolt2 = _bolt_light(BW, BH, 55, 230, -40, 400, BH * 0.75) * 0.6
    halo = np.asarray(Image.fromarray(np.clip(bolt, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(120)), np.float32)
    lum = lum + cl * halo * 1.2 + bolt * 0.9 + bolt2 * 0.9
    arr = np.clip(np.stack([lum, lum, lum * 1.03], -1), 0, 255)
    img = Image.fromarray(arr.astype(np.uint8), 'RGB').convert('RGBA')
    img = C.vignette(img, 0.5, 2.0).convert('RGBA')
    # тёмная подложка под текстом, чтобы молния не спорила с надписью
    pad = C.radial(1700, 700, (0, 0, 0), 170, 1.2)
    C.put(img, pad, cx, cy)
    wm = wordmark('JARVIS', 190, (244, 244, 248), 0.1, glow=(210, 214, 226))
    C.put(img, wm, cx, cy - 70)
    C.put(img, C.text(t['sub'], 'mont', 50, (210, 212, 220), 800, track=0.3), cx, cy + 82)
    C.put(img, Image.new('RGBA', (900, 3), (230, 230, 236, 120)), cx, cy + 130)
    C.put(img, C.text(t['line'], 'mont', 40, (170, 172, 180), 600, track=0.04), cx, cy + 172)
    return img


def avatar_storm():
    S = 800
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    n = noise(S, S, 200, 21, 4) ** 1.5
    bolt = _bolt_light(S, S, 7, 560, -20, 470, S + 20) * 0.5
    lum = 8 + n * 70 + bolt * 0.6
    arr = np.clip(np.stack([lum, lum, lum * 1.03], -1), 0, 255)
    disc = Image.fromarray(arr.astype(np.uint8), 'RGB').convert('RGBA')
    m = Image.new('L', (S, S), 0)
    ImageDraw.Draw(m).ellipse((0, 0, S - 1, S - 1), fill=255)
    disc.putalpha(m)
    im.alpha_composite(disc)
    ring = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((40, 40, S - 40, S - 40), outline=(220, 222, 230, 255), width=8)
    im.alpha_composite(ring)
    C.put(im, C.glow(C.text('J', 'unb', 470, (246, 246, 250), 800), 24, 0.5, (210, 214, 226)), S / 2, S / 2 + 10)
    return im


STYLES = {'night': (banner_night, avatar_night, 'Ночь'), 'ice': (banner_ice, avatar_ice, 'Лёд'),
          'storm': (banner_storm, avatar_storm, 'Гроза')}


# ─────────────────────────── примерка ───────────────────────────
def _circle(av, d):
    a = av.resize((d, d), Image.LANCZOS)
    m = Image.new('L', (d * 3, d * 3), 0)
    ImageDraw.Draw(m).ellipse((0, 0, d * 3 - 1, d * 3 - 1), fill=255)
    a.putalpha(Image.fromarray(np.minimum(np.asarray(a.getchannel('A')), np.asarray(m.resize((d, d), Image.LANCZOS)))))
    return a


def _ui(img, x, y, av, d, name, handle, dark, big=True):
    """Блок канала под баннером как в YouTube: аватар, название, @имя и подписчики."""
    C.put(img, _circle(av, d), x + d / 2, y + d / 2)
    ink = (241, 241, 241) if dark else (15, 15, 15)
    sub = (170, 170, 170) if dark else (96, 96, 96)
    tx = x + d + (36 if big else 22)
    C.put(img, C.text(name, 'rubik', 56 if big else 34, ink, 700), tx, y + d * 0.22, anchor='tl')
    C.put(img, C.text(handle + ' · 0 подписчиков · 0 видео', 'rubik', 30 if big else 22, sub, 400), tx,
          y + d * 0.22 + (80 if big else 50), anchor='tl')


def preview(banner, av, title, lang):
    """Лист примерки: компьютер (полоса 2560×423), телефон (зона 1546×423), телевизор (весь баннер), аватар крупно и мелко."""
    dark = True
    bg = (15, 15, 15)
    W, H = 2400, 2200
    sheet = Image.new('RGBA', (W, H), bg + (255,))
    lab = lambda s: C.text(s, 'mont', 34, (200, 200, 200), 700, track=0.06)
    name = 'JARVIS'
    handle = '@jarvibet'
    # компьютер
    C.put(sheet, lab('КОМПЬЮТЕР / НОУТБУК — полоса 2560×423'), 60, 56, anchor='tl')
    desk = banner.crop(DESK).resize((2280, int(2280 * 423 / 2560)), Image.LANCZOS)
    m = C.rrect(desk.width, desk.height, 24).getchannel('A')
    desk.putalpha(m)
    sheet.alpha_composite(desk, (60, 110))
    _ui(sheet, 60, 110 + desk.height + 40, av, 180, name, handle, dark)
    # телефон
    py = 110 + desk.height + 300
    C.put(sheet, lab('ТЕЛЕФОН — видна только зона 1546×423'), 60, py, anchor='tl')
    phone = Image.new('RGBA', (760, 1000), (0, 0, 0, 255))
    ph = banner.crop(SAFE).resize((700, int(700 * 423 / 1546)), Image.LANCZOS)
    ph.putalpha(C.rrect(ph.width, ph.height, 18).getchannel('A'))
    phone.alpha_composite(ph, (30, 120))
    _ui(phone, 30, 120 + ph.height + 30, av, 120, name, handle, dark, big=False)
    frame = C.rrect(780, 1020, 70, None, outline=(80, 80, 86), width=10)
    sheet.alpha_composite(C.rrect(780, 1020, 70, (0, 0, 0)), (60, py + 60))
    sheet.alpha_composite(phone.crop((0, 0, 760, 1000)), (70, py + 70))
    sheet.alpha_composite(frame, (60, py + 60))
    # телевизор
    C.put(sheet, lab('ТЕЛЕВИЗОР — весь баннер 2560×1440'), 920, py, anchor='tl')
    tv = banner.resize((1400, 788), Image.LANCZOS)
    sheet.alpha_composite(C.rrect(1440, 828, 20, (40, 40, 44)), (920, py + 60))
    sheet.alpha_composite(tv, (940, py + 80))
    # аватар: как в комментариях и ленте (мелко)
    ay = py + 940
    C.put(sheet, lab('АВАТАР в ленте и комментариях'), 920, ay, anchor='tl')
    x = 920
    for d in (176, 88, 48, 32):
        C.put(sheet, _circle(av, d), x + d / 2, ay + 80 + 88)
        x += d + 50
    tl = C.text('Вариант «%s»' % title, 'unb', 50, (255, 255, 255), 800)
    C.put(sheet, tl, W - 60 - tl.width, 40, anchor='tl')
    return sheet.convert('RGB')


def main():
    out = sys.argv[1]
    lang = sys.argv[sys.argv.index('--lang') + 1] if '--lang' in sys.argv else 'ru'
    names = [a for a in sys.argv[2:] if a in STYLES] or list(STYLES)
    os.makedirs(out, exist_ok=True)
    for nm in names:
        bf, af, title = STYLES[nm]
        b, a = bf(lang), af()
        b.convert('RGB').save(os.path.join(out, 'banner_%s_%s.jpg' % (nm, lang)), quality=94)
        a.save(os.path.join(out, 'avatar_%s.png' % nm))
        preview(b, a, title, lang).save(os.path.join(out, 'preview_%s_%s.jpg' % (nm, lang)), quality=88)
        print(nm, 'ok', flush=True)


if __name__ == '__main__':
    main()
