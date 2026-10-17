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


# ─────────────────────────── яркие: 4. «Неон», 5. «Гол», 6. «Скорость» ───────────────────────────
def _disc(S, arr_or_img):
    im = arr_or_img if isinstance(arr_or_img, Image.Image) else Image.fromarray(np.clip(arr_or_img, 0, 255).astype(np.uint8), 'RGB')
    im = im.convert('RGBA')
    m = Image.new('L', (S, S), 0)
    ImageDraw.Draw(m).ellipse((0, 0, S - 1, S - 1), fill=255)
    im.putalpha(m)
    return im


def neon_text(txt, size, col, font='unb', wght=800, track=0.1, core=(255, 255, 255)):
    """Неоновая трубка: белое ядро, цветной ореол в два слоя."""
    t = C.text(txt, font, size, core, wght, track=track)
    pad = int(size * 0.6)
    big = Image.new('RGBA', (t.width + 2 * pad, t.height + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(t, (pad, pad))
    a = big.getchannel('A')
    out = Image.new('RGBA', big.size, (0, 0, 0, 0))
    for r, k in ((size * 0.45, 0.9), (size * 0.16, 1.0), (size * 0.05, 1.0)):
        g = Image.new('RGBA', big.size, col + (0,))
        g.putalpha(a.filter(ImageFilter.GaussianBlur(r)).point(lambda v: min(255, int(v * k * 1.6))))
        out.alpha_composite(g)
    tint = Image.new('RGBA', big.size, C.mix(core, col, 0.25) + (0,))
    tint.putalpha(a)
    out.alpha_composite(tint)
    return out


CYAN, MAGENTA = (40, 220, 255), (255, 50, 170)


def banner_neon(lang):
    t = TXT[lang]
    cx, cy = BW / 2, BH / 2
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    base = np.array((8, 6, 20), np.float32)[None, None, :] + ((noise(BW, BH, 300, 13) - 0.5) * 10)[..., None]
    for (gx, gy, col, r) in ((cx - 900, cy, CYAN, 900), (cx + 900, cy, MAGENTA, 900)):
        g = np.exp(-(((xx - gx) / r) ** 2 + ((yy - gy) / (r * 0.7)) ** 2))
        base += g[..., None] * np.array(col, np.float32) * 0.28
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    # отражающий пол и неоновые линии площадки
    lay = Image.new('RGBA', (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k, col in ((-1, CYAN), (1, MAGENTA)):
        x = cx + k * 1000
        d.line((x, 0, x, BH), fill=col + (200,), width=10)
    d.ellipse((cx - 560, cy - 560, cx + 560, cy + 560), outline=CYAN + (120,), width=8)
    glow = lay.filter(ImageFilter.GaussianBlur(26))
    img.alpha_composite(glow)
    img.alpha_composite(glow)
    img.alpha_composite(lay)
    C.put(img, C.radial(1800, 640, (0, 0, 0), 150, 1.3), cx, cy)
    C.put(img, neon_text('JARVIS', 190, CYAN), cx, cy - 66)
    C.put(img, neon_text(t['sub'], 48, MAGENTA, 'mont', 800, 0.3), cx, cy + 86)
    C.put(img, C.text(t['line'], 'mont', 40, (230, 226, 255), 600, track=0.04), cx, cy + 178)
    return C.vignette(img, 0.45, 2.2).convert('RGBA')


def avatar_neon():
    S = 800
    im = _disc(S, Image.new('RGB', (S, S), (10, 8, 24)))
    ring = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((70, 70, S - 70, S - 70), outline=MAGENTA + (255,), width=14)
    im.alpha_composite(ring.filter(ImageFilter.GaussianBlur(18)))
    im.alpha_composite(ring)
    C.put(im, neon_text('J', 430, CYAN, track=0), S / 2, S / 2 + 10)
    return im


RED, ORANGE = (255, 40, 30), (255, 150, 40)


def banner_goal(lang):
    t = TXT[lang]
    cx, cy = BW / 2, BH / 2
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    g = np.exp(-(((xx - cx) / 1300) ** 2 + ((yy - cy) / 620) ** 2))
    base = np.array((30, 4, 6), np.float32)[None, None, :] + g[..., None] * np.array((235, 40, 24), np.float32)
    base += (np.exp(-(((xx - cx) / 700) ** 2 + ((yy - cy) / 260) ** 2)) * 70)[..., None] * np.array((1, 0.6, 0.2))
    base += ((noise(BW, BH, 200, 17) - 0.5) * 22)[..., None]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    # лучи от центра и искры
    rng = np.random.default_rng(3)
    lay = Image.new('RGBA', (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(28):
        a = k / 28 * 2 * math.pi + 0.05
        d.polygon([(cx, cy), (cx + 3000 * math.cos(a - 0.025), cy + 3000 * math.sin(a - 0.025)),
                   (cx + 3000 * math.cos(a + 0.025), cy + 3000 * math.sin(a + 0.025))], fill=(255, 180, 120, 26))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(10)))
    sp = Image.new('RGBA', (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    for _ in range(420):
        x, y = rng.uniform(0, BW), rng.uniform(0, BH)
        if abs(x - cx) < 760 and abs(y - cy) < 240:
            continue
        L = rng.uniform(8, 50)
        a = math.atan2(y - cy, x - cx)
        d.line((x, y, x + L * math.cos(a), y + L * math.sin(a)), fill=(255, int(rng.uniform(170, 240)), 120, int(rng.uniform(120, 255))), width=3)
    img.alpha_composite(C.glow(sp, 6, 1.0).crop((18, 18, 18 + BW, 18 + BH)))
    wm = wordmark('JARVIS', 196, (255, 255, 255), 0.1)
    C.put(img, C.shadow(wm, r=20, a=0.55, col=(60, 0, 0)), cx + 8, cy - 60)
    C.put(img, wm, cx, cy - 70)
    sub = C.text(t['sub'], 'mont', 50, (255, 236, 196), 800, track=0.3)
    C.put(img, C.shadow(sub, r=8, a=0.7, col=(50, 0, 0)), cx + 3, cy + 88)
    C.put(img, sub, cx, cy + 84)
    C.put(img, C.text(t['line'], 'mont', 40, (255, 226, 214), 600, track=0.04), cx, cy + 172)
    return C.vignette(img, 0.4, 2.2).convert('RGBA')


def avatar_goal():
    S = 800
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    g = np.exp(-(((xx - S / 2) / 420) ** 2 + ((yy - S / 2) / 420) ** 2))
    arr = np.array((40, 4, 6), np.float32)[None, None, :] + g[..., None] * np.array((230, 50, 26), np.float32)
    im = _disc(S, arr)
    j = C.text('J', 'unb', 470, (255, 255, 255), 800)
    C.put(im, C.shadow(j, r=20, a=0.6, col=(60, 0, 0)), S / 2 + 8, S / 2 + 22)
    C.put(im, j, S / 2, S / 2 + 10)
    ring = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((36, 36, S - 36, S - 36), outline=(255, 214, 140, 255), width=10)
    im.alpha_composite(ring)
    return im


def banner_speed(lang):
    t = TXT[lang]
    cx, cy = BW / 2, BH / 2
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    k = np.clip((xx + yy * 0.6) / (BW + BH * 0.6), 0, 1)
    c0, c1, c2 = np.array((20, 40, 160.)), np.array((0, 170, 230.)), np.array((120, 50, 220.))
    base = np.where(k[..., None] < 0.5, c0 + (c1 - c0) * (k[..., None] / 0.5), c1 + (c2 - c1) * ((k[..., None] - 0.5) / 0.5))
    base *= (0.75 + 0.25 * noise(BW, BH, 400, 19))[..., None]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    rng = np.random.default_rng(8)
    lay = Image.new('RGBA', (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for _ in range(90):
        y0 = rng.uniform(-200, BH + 200)
        x0 = rng.uniform(-400, BW)
        L = rng.uniform(300, 1400)
        w = int(rng.uniform(2, 16))
        a = int(rng.uniform(30, 120))
        d.line((x0, y0, x0 + L, y0 - L * 0.32), fill=(255, 255, 255, a), width=w)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2)))
    # крупный срез-полоса за текстом
    band = Image.new('RGBA', (BW, BH), (0, 0, 0, 0))
    ImageDraw.Draw(band).polygon([(0, cy - 150), (BW, cy - 420), (BW, cy + 160), (0, cy + 430)], fill=(6, 14, 46, 150))
    img.alpha_composite(band.filter(ImageFilter.GaussianBlur(8)))
    wm = wordmark('JARVIS', 196, (255, 255, 255), 0.1)
    C.put(img, C.shadow(wm, r=16, a=0.5, col=(0, 0, 40)), cx + 8, cy - 60)
    C.put(img, wm, cx, cy - 70)
    C.put(img, gold_text(t['sub'], 50), cx, cy + 84)
    C.put(img, C.text(t['line'], 'mont', 40, (226, 240, 255), 600, track=0.04), cx, cy + 172)
    return img


def avatar_speed():
    S = 800
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    k = np.clip((xx + yy) / (2 * S), 0, 1)[..., None]
    arr = np.array((20, 40, 160.)) + (np.array((120, 50, 220.)) - np.array((20, 40, 160.))) * k
    im = _disc(S, arr)
    lay = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(10):
        y = 120 + i * 62
        d.line((-50, y + 160, S + 50, y - 100), fill=(255, 255, 255, 40), width=6)
    m = Image.new('L', (S, S), 0)
    ImageDraw.Draw(m).ellipse((0, 0, S - 1, S - 1), fill=255)
    lay.putalpha(Image.fromarray(np.minimum(np.asarray(lay.getchannel('A')), np.asarray(m))))
    im.alpha_composite(lay)
    j = C.text('J', 'unb', 470, (255, 255, 255), 800)
    C.put(im, C.shadow(j, r=18, a=0.5, col=(0, 0, 40)), S / 2 + 8, S / 2 + 20)
    C.put(im, j, S / 2, S / 2 + 10)
    ring = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((36, 36, S - 36, S - 36), outline=GOLD + (255,), width=10)
    im.alpha_composite(ring)
    return im


STYLES.update({'neon': (banner_neon, avatar_neon, 'Неон'), 'goal': (banner_goal, avatar_goal, 'Гол'),
               'speed': (banner_speed, avatar_speed, 'Скорость')})


# ─────────────────────────── клубные эмблемы на фоне: «Лёд» и «Гроза» ───────────────────────────
CLUBS = ['ЦСКА', 'Оттава', 'Локомотив', 'Флорида', 'Северсталь', 'Миннесота', 'СКА', 'Бостон', 'Ак Барс', 'Торонто',
         'Авангард', 'Эдмонтон', 'Металлург', 'Колорадо', 'Спартак', 'Вегас', 'Динамо Москва', 'Монреаль', 'Трактор',
         'Питтсбург', 'Салават Юлаев', 'Нью-Йорк Рейнджерс', 'Автомобилист', 'Тампа-Бэй', 'Сибирь', 'Даллас', 'Торпедо',
         'Чикаго', 'Шанхайские Драконы', 'Детройт', 'Нефтехимик', 'Вашингтон']


def emblem_wall(size=150, gap=70, gray=False, seed=4):
    """Шахматная сетка эмблем КХЛ и НХЛ на весь баннер → (RGBA-слой, список центров)."""
    import nhl
    nhl.register()
    rng = np.random.default_rng(seed)
    order = list(CLUBS)
    rng.shuffle(order)
    lay = Image.new('RGBA', (BW, BH), (0, 0, 0, 0))
    step = size + gap
    k = 0
    centers = []
    for j, y in enumerate(range(-size // 2, BH + size, step)):
        off = (step / 2) if j % 2 else 0
        for x in np.arange(-size / 2 + off, BW + size, step):
            em = C.fit(C.Team(order[k % len(order)]).emb(size * 2), size, size)
            k += 1
            if gray:
                g = em.convert('LA').convert('RGBA')
                g.putalpha(em.getchannel('A'))
                em = g
            C.put(lay, em, x, y)
            centers.append((x, y))
    return lay, centers


def _fade_center(lay, rx=820, ry=300, soft=1.6, floor=0.0):
    """Оставить эмблемы по краям: в центре (под текстом) — прозрачно."""
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    d = np.sqrt(((xx - BW / 2) / rx) ** 2 + ((yy - BH / 2) / ry) ** 2)
    k = np.clip((d - 1) / soft, 0, 1) * (1 - floor) + floor
    a = np.asarray(lay.getchannel('A'), np.float32) * k
    lay.putalpha(Image.fromarray(a.astype(np.uint8)))
    return lay


def banner_ice_clubs(lang):
    t = TXT[lang]
    cx, cy = BW / 2, BH / 2
    n = noise(BW, BH, 300, 7)
    yy = np.mgrid[0:BH, 0:BW][0].astype(np.float32)
    base = np.array((226, 236, 246), np.float32)[None, None, :] + ((n - 0.5) * 18)[..., None]
    base -= (np.clip((np.abs(yy - cy) / 900) ** 2, 0, 1) * 30)[..., None]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    wall, _ = emblem_wall(170, 80)
    wall = wall.filter(ImageFilter.GaussianBlur(1.2))
    wall.putalpha(wall.getchannel('A').point(lambda v: int(v * 0.42)))
    img.alpha_composite(_fade_center(wall, 760, 270, 0.9))
    img.alpha_composite(rink_lines(BW, BH, cx, cy, 1.0, 50))
    img.alpha_composite(scratches(BW, BH, 9, 520, 80, (150, 170, 196)))
    frost = Image.fromarray((np.clip((n - 0.4) * 3, 0, 1) * 120).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
    fl = Image.new('RGBA', (BW, BH), (240, 246, 252, 0))
    fl.putalpha(frost)
    img.alpha_composite(fl)
    C.put(img, C.radial(1900, 760, (236, 242, 250), 235, 1.0), cx, cy)
    wm = wordmark('JARVIS', 190, NAVY, 0.1)
    C.put(img, C.shadow(wm, r=14, a=0.25), cx + 6, cy - 60)
    C.put(img, wm, cx, cy - 70)
    C.put(img, C.text(t['sub'], 'mont', 50, (176, 128, 40), 800, track=0.3), cx, cy + 82)
    C.put(img, Image.new('RGBA', (900, 4), NAVY + (90,)), cx, cy + 130)
    C.put(img, C.text(t['line'], 'mont', 40, (60, 76, 104), 600, track=0.04), cx, cy + 172)
    return img


def banner_storm_clubs(lang):
    t = TXT[lang]
    cx, cy = BW / 2, BH / 2
    n = noise(BW, BH, 420, 11, 4)
    cl = n ** 1.5
    yy = np.mgrid[0:BH, 0:BW][0].astype(np.float32)
    lum = 6 + cl * 64 * (0.55 + 0.45 * np.exp(-((yy - cy) / 700) ** 2))
    bolt = _bolt_light(BW, BH, 99, 2330, -40, 2180, BH * 0.95)
    bolt2 = _bolt_light(BW, BH, 55, 230, -40, 400, BH * 0.75) * 0.6
    halo = np.asarray(Image.fromarray(np.clip(bolt + bolt2, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(160)), np.float32)
    lum = lum + cl * halo * 1.2
    arr = np.clip(np.stack([lum, lum, lum * 1.03], -1), 0, 255)
    img = Image.fromarray(arr.astype(np.uint8), 'RGB').convert('RGBA')
    # эмблемы в темноте: высвечены там, куда достаёт свет молний
    wall, _ = emblem_wall(170, 80, gray=True)
    light = np.clip(0.3 + halo / 60, 0.3, 1.0)
    w = np.asarray(wall, np.float32)
    w[..., :3] *= light[..., None] * 0.95
    w[..., 3] *= np.clip(0.55 + halo / 90, 0.55, 0.95)
    wall = Image.fromarray(np.clip(w, 0, 255).astype(np.uint8), 'RGBA')
    img.alpha_composite(_fade_center(wall, 760, 270, 0.9))
    lit = np.clip(np.stack([bolt + bolt2] * 3, -1) * 0.9, 0, 255).astype(np.uint8)
    img = Image.fromarray(np.clip(np.asarray(img.convert('RGB'), np.float32) + lit, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    img = C.vignette(img, 0.5, 2.0).convert('RGBA')
    C.put(img, C.radial(1800, 700, (0, 0, 0), 200, 1.2), cx, cy)
    wm = wordmark('JARVIS', 190, (244, 244, 248), 0.1, glow=(210, 214, 226))
    C.put(img, wm, cx, cy - 70)
    C.put(img, C.text(t['sub'], 'mont', 50, (210, 212, 220), 800, track=0.3), cx, cy + 82)
    C.put(img, Image.new('RGBA', (900, 3), (230, 230, 236, 120)), cx, cy + 130)
    C.put(img, C.text(t['line'], 'mont', 40, (170, 172, 180), 600, track=0.04), cx, cy + 172)
    return img


STYLES.update({'ice_clubs': (banner_ice_clubs, avatar_ice, 'Лёд + клубы'),
               'storm_clubs': (banner_storm_clubs, avatar_storm, 'Гроза + клубы')})


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
