"""Десять шаблонов постов НХЛ — у каждого своя шрифтовая пара и своя структура.

 6. board    — ЛЕД-табло, Tektur
 7. paper    — газетная полоса, Golos Text + Roboto Condensed
 8. minimal  — швейцарский минимализм, Manrope
 9. neon     — неон арены, Unbounded
10. stripe   — диагональные полосы, Oswald
11. sticker  — наклейки, Rubik
12. terminal — терминал, Roboto Condensed
13. magazine — журнальный разворот, Exo 2 Italic
14. card     — коллекционная карточка, Onest
15. app      — матч-центр в приложении, Golos Text
"""
import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from poster import TEAMS, _raw_emblem, _canvas_texture, _shadowed, _layer_draw, _spaced
from recap import _needs_plate
from nhl_variants import _save

_FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
FONTS = {
    'tektur':     (_FD + '/Tektur[wdth,wght].ttf', [110, 700]),
    'golos':      (_FD + '/GolosText[wght].ttf', [700]),
    'golos_b':    (_FD + '/GolosText[wght].ttf', [900]),
    'onest':      (_FD + '/Onest[wght].ttf', [700]),
    'onest_b':    (_FD + '/Onest[wght].ttf', [900]),
    'rubik':      (_FD + '/Rubik[wght].ttf', [700]),
    'rubik_b':    (_FD + '/Rubik[wght].ttf', [900]),
    'exo_i':      (_FD + '/Exo2-Italic[wght].ttf', [800]),
    'exo':        (_FD + '/Exo2[wght].ttf', [600]),
    'robcond':    (_FD + '/RobotoCondensed[wght].ttf', [500]),
    'robcond_b':  (_FD + '/RobotoCondensed[wght].ttf', [700]),
    'oswald':     (_FD + '/Oswald[wght].ttf', [600]),
    'oswald_b':   (_FD + '/Oswald[wght].ttf', [700]),
    'manrope':    (_FD + '/Manrope[wght].ttf', [600]),
    'manrope_b':  (_FD + '/Manrope[wght].ttf', [800]),
    'unbounded':  (_FD + '/Unbounded[wght].ttf', [800]),
    'unb_light':  (_FD + '/Unbounded[wght].ttf', [400]),
    'russo':      (_FD + '/RussoOne-Regular.ttf', None),
    'mont':       (_FD + '/Montserrat[wght].ttf', [900]),
    'mont_b':     (_FD + '/Montserrat[wght].ttf', [800]),
    'mont_m':     (_FD + '/Montserrat[wght].ttf', [600]),
}
INK = (12, 18, 28)


def _f(name, size):
    p, axes = FONTS[name]
    f = ImageFont.truetype(p, int(size))
    if axes:
        try:
            f.set_variation_by_axes(axes)
        except Exception:
            pass
    return f


def _fit(text, name, size, max_w, min_size=12):
    f = _f(name, size)
    while f.getlength(text) > max_w and size > min_size:
        size -= 1
        f = _f(name, size)
    return f


def _logo(ov, team, cx, cy, w, h, S, plate=None, blur=24, alpha=130):
    if team not in TEAMS:
        return None
    if plate is None:
        plate = _needs_plate(team)
    e = _raw_emblem(team, int(w * S), int(h * S), plate=plate)
    _shadowed(ov, e, (int(cx * S - e.width / 2), int(cy * S - e.height / 2)),
              blur=blur, off=(0, 10), color=(0, 0, 0, alpha))
    return e


def _grad(W, H, top, bottom):
    import numpy as np
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    col = np.array(top, np.float32) * (1 - y) + np.array(bottom, np.float32) * y
    return Image.fromarray(np.clip(col.repeat(W, axis=1), 0, 255).astype('uint8'), 'RGB').convert('RGBA')


# ------------------------------------------------ 6. ЛЕД-ТАБЛО · Tektur
AMBER = (255, 176, 40)


def render_board(m, path, W=1280, H=640, handle='@jarvibet'):
    S = 2
    WW, HH = W * S, H * S
    bg = Image.new('RGBA', (WW, HH), (6, 8, 11, 255))
    L, ld = _layer_draw(bg)
    for gy in range(0, HH, 9 * S):                     # точечная матрица
        for gx in range(0, WW, 9 * S):
            ld.ellipse((gx, gy, gx + 2 * S, gy + 2 * S), fill=(255, 255, 255, 12))
    ld.rectangle((0, 0, WW, 6 * S), fill=AMBER + (255,))
    ld.rectangle((0, HH - 6 * S, WW, HH), fill=AMBER + (255,))
    bg.alpha_composite(L)

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _spaced(d, (WW / 2, 56 * S), 'JARVIS  NHL', _f('tektur', 22 * S), AMBER + (255,), 6 * S, anchor='m')
    _spaced(d, (WW / 2, 92 * S), m['league'], _f('tektur', 13 * S), (150, 156, 166, 255), 4 * S, anchor='m')

    for side, cx in ((m['home'], 300), (m['away'], 980)):
        _logo(ov, side.get('team'), cx, 200, 150, 108, S, blur=14)
    d = ImageDraw.Draw(ov)
    for side, cx in ((m['home'], 300), (m['away'], 980)):
        code = side.get('code', side['name'][:3])
        d.text((cx * S, 320 * S), code, font=_f('tektur', 86 * S), fill=AMBER + (255,), anchor='mm')
        _spaced(d, (cx * S, 378 * S), side['name'], _f('tektur', 15 * S), (222, 228, 238, 255), 3 * S, anchor='m')
    d.text((WW / 2, 320 * S), ':', font=_f('tektur', 74 * S), fill=(120, 128, 140, 255), anchor='mm')
    _spaced(d, (WW / 2, 200 * S), m['when'], _f('tektur', 15 * S), (206, 214, 226, 255), 3 * S, anchor='m')

    L, ld = _layer_draw(ov)                            # бегущая строка
    ld.rectangle((40 * S, 448 * S, (W - 40) * S, 540 * S), fill=(13, 16, 21, 250),
                 outline=AMBER + (170,), width=2 * S)
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    line = 'ПРОГНОЗ:  ' + m['pred']
    fp = _fit(line, 'tektur', 24 * S, 760 * S, min_size=14 * S)
    d.text((72 * S, 494 * S), line, font=fp, fill=(255, 255, 255, 255), anchor='lm')
    d.text(((W - 72) * S, 494 * S), 'КЭФ  %.2f' % m['coef'], font=_f('tektur', 26 * S),
           fill=AMBER + (255,), anchor='rm')
    _spaced(d, (WW / 2, 584 * S), handle, _f('tektur', 13 * S), (140, 148, 160, 255), 4 * S, anchor='m')
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 7. ГАЗЕТА · Golos Text
def render_paper(m, path, W=1280, H=640, handle='@jarvibet'):
    S = 2
    WW, HH = W * S, H * S
    bg = _grad(WW, HH, (244, 241, 233), (231, 227, 216))
    bg = _canvas_texture(bg.convert('RGB'), 1.1).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    ink = (22, 26, 32)
    d.line((60 * S, 62 * S, (W - 60) * S, 62 * S), fill=ink + (255,), width=4 * S)
    d.line((60 * S, 72 * S, (W - 60) * S, 72 * S), fill=ink + (255,), width=S)
    _spaced(d, (WW / 2, 104 * S), 'JARVIS · NHL', _f('golos_b', 26 * S), ink + (255,), 5 * S, anchor='m')
    d.line((60 * S, 134 * S, (W - 60) * S, 134 * S), fill=ink + (255,), width=S)
    _spaced(d, (WW / 2, 158 * S), m['league'] + '  ·  ' + m['when'], _f('robcond', 15 * S),
            (92, 96, 104, 255), 3 * S, anchor='m')

    head = m['pred']
    fh = _fit(head, 'golos_b', 52 * S, 1060 * S, min_size=26 * S)
    d.text((WW / 2, 224 * S), head, font=fh, fill=ink + (255,), anchor='mm')
    d.line((300 * S, 266 * S, (W - 300) * S, 266 * S), fill=(150, 146, 138, 255), width=2 * S)

    d.line((WW / 2, 300 * S, WW / 2, 520 * S), fill=(168, 164, 154, 255), width=2 * S)
    for side, cx, al in ((m['home'], 330, 'left'), (m['away'], 950, 'right')):
        _logo(ov, side.get('team'), cx, 356, 168, 116, S, plate=False, blur=12, alpha=70)
    d = ImageDraw.Draw(ov)
    for side, cx in ((m['home'], 330), (m['away'], 950)):
        fn = _fit(side['name'], 'golos_b', 30 * S, 460 * S, min_size=20 * S)
        d.text((cx * S, 442 * S), side['name'], font=fn, fill=ink + (255,), anchor='mm')
        _spaced(d, (cx * S, 474 * S), side['sub'], _f('robcond', 14 * S), (110, 112, 118, 255), 3 * S, anchor='m')
    if m.get('note'):
        _spaced(d, (WW / 2, 546 * S), m['note'], _f('robcond', 14 * S), (104, 106, 112, 255), 2 * S, anchor='m')

    L, ld = _layer_draw(ov)
    ld.rectangle((60 * S, 572 * S, 300 * S, 614 * S), fill=ink + (255,))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    d.text((180 * S, 593 * S), 'КЭФ %.2f' % m['coef'], font=_f('golos_b', 21 * S),
           fill=(244, 241, 233, 255), anchor='mm')
    _spaced(d, ((W - 60) * S, 593 * S), handle, _f('robcond_b', 15 * S), ink + (255,), 3 * S, anchor='r')
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 8. МИНИМАЛ · Manrope
def render_minimal(m, path, W=1280, H=640, handle='@jarvibet'):
    S = 2
    WW, HH = W * S, H * S
    bg = _grad(WW, HH, (248, 248, 246), (238, 239, 236))
    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    ink = (16, 18, 22)
    d.rectangle((44 * S, 44 * S, (W - 44) * S, (H - 44) * S), outline=(200, 202, 200, 255), width=2 * S)

    _spaced(d, (96 * S, 108 * S), 'JARVIS — NHL', _f('manrope_b', 14 * S), ink + (255,), 4 * S)
    _spaced(d, (96 * S, 140 * S), m['league'], _f('manrope', 13 * S), (132, 136, 140, 255), 3 * S)

    d.text((96 * S, 216 * S), m['home']['name'], font=_fit(m['home']['name'], 'manrope_b', 54 * S, 620 * S),
           fill=ink + (255,), anchor='lm')
    d.line((96 * S, 252 * S, 700 * S, 252 * S), fill=(206, 208, 206, 255), width=2 * S)
    d.text((96 * S, 292 * S), m['away']['name'], font=_fit(m['away']['name'], 'manrope', 54 * S, 620 * S),
           fill=(120, 124, 128, 255), anchor='lm')

    for side, cy in ((m['home'], 208), (m['away'], 316)):
        _logo(ov, side.get('team'), 1088, cy, 132, 92, S, plate=False, blur=10, alpha=60)
    d = ImageDraw.Draw(ov)

    _spaced(d, (96 * S, 388 * S), 'ПРОГНОЗ', _f('manrope_b', 12 * S), (140, 144, 148, 255), 4 * S)
    fp = _fit(m['pred'], 'manrope_b', 24 * S, 700 * S, min_size=15 * S)
    d.text((96 * S, 420 * S), m['pred'], font=fp, fill=ink + (255,), anchor='lm')

    _spaced(d, (96 * S, 476 * S), 'КОЭФФИЦИЕНТ', _f('manrope_b', 12 * S), (140, 144, 148, 255), 4 * S)
    d.text((92 * S, 544 * S), '%.2f' % m['coef'], font=_f('manrope_b', 92 * S), fill=ink + (255,), anchor='lm')
    _spaced(d, ((W - 96) * S, 532 * S), m['when'], _f('manrope_b', 15 * S), ink + (255,), 3 * S, anchor='r')
    _spaced(d, ((W - 96) * S, 560 * S), handle, _f('manrope', 13 * S), (140, 144, 148, 255), 3 * S, anchor='r')
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 9. НЕОН · Unbounded
CYAN = (84, 230, 255)
MAG = (255, 86, 186)


def render_neon(m, path, W=1280, H=640, handle='@jarvibet'):
    S = 2
    WW, HH = W * S, H * S
    bg = Image.new('RGBA', (WW, HH), (6, 7, 14, 255))
    glow = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-200 * S, 60 * S, 620 * S, 560 * S), fill=CYAN + (46,))
    gd.ellipse((660 * S, 60 * S, 1480 * S, 560 * S), fill=MAG + (40,))
    bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(90 * S // 2)))
    L, ld = _layer_draw(bg)
    for gy in range(0, HH, 6 * S):
        ld.line((0, gy, WW, gy), fill=(255, 255, 255, 7), width=S)
    bg.alpha_composite(L)

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    halo = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse((190 * S, 110 * S, 470 * S, 330 * S), fill=CYAN + (120,))
    hd.ellipse((810 * S, 110 * S, 1090 * S, 330 * S), fill=MAG + (110,))
    ov.alpha_composite(halo.filter(ImageFilter.GaussianBlur(40 * S)))
    for side, cx in ((m['home'], 330), (m['away'], 950)):
        _logo(ov, side.get('team'), cx, 220, 210, 150, S, blur=20)
    d = ImageDraw.Draw(ov)
    _spaced(d, (WW / 2, 54 * S), 'JARVIS | NHL', _f('unbounded', 22 * S), (255, 255, 255, 255), 4 * S, anchor='m')
    _spaced(d, (WW / 2, 92 * S), m['league'], _f('unb_light', 13 * S), CYAN + (255,), 4 * S, anchor='m')
    for side, cx, col in ((m['home'], 330, CYAN), (m['away'], 950, MAG)):
        fn = _fit(side['name'], 'unbounded', 27 * S, 480 * S, min_size=16 * S)
        d.text((cx * S, 348 * S), side['name'], font=fn, fill=(255, 255, 255, 255), anchor='mm')
        _spaced(d, (cx * S, 382 * S), side['sub'], _f('unb_light', 13 * S), col + (255,), 3 * S, anchor='m')
    d.text((WW / 2, 220 * S), 'VS', font=_f('unbounded', 30 * S), fill=(255, 255, 255, 220), anchor='mm')

    tube = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    td = ImageDraw.Draw(tube)
    td.rounded_rectangle((70 * S, 438 * S, (W - 70) * S, 528 * S), radius=45 * S, outline=CYAN + (235,), width=3 * S)
    ov.alpha_composite(tube.filter(ImageFilter.GaussianBlur(9 * S)))
    ov.alpha_composite(tube)
    d = ImageDraw.Draw(ov)
    fp = _fit(m['pred'], 'unbounded', 22 * S, 620 * S, min_size=13 * S)
    d.text((136 * S, 483 * S), m['pred'], font=fp, fill=(255, 255, 255, 255), anchor='lm')
    d.text(((W - 136) * S, 483 * S), '%.2f' % m['coef'], font=_f('unbounded', 28 * S), fill=MAG + (255,), anchor='rm')
    _spaced(d, (WW / 2, 570 * S), m['when'], _f('unb_light', 14 * S), (214, 222, 236, 255), 3 * S, anchor='m')
    _spaced(d, (WW / 2, 604 * S), handle, _f('unb_light', 13 * S), CYAN + (255,), 3 * S, anchor='m')
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 10. ПОЛОСЫ · Oswald
def render_stripe(m, path, W=1280, H=640, handle='@jarvibet'):
    S = 2
    WW, HH = W * S, H * S
    bg = Image.new('RGBA', (WW, HH), (14, 16, 20, 255))
    L, ld = _layer_draw(bg)
    ld.polygon([(0, 0), (520 * S, 0), (300 * S, HH), (0, HH)], fill=tuple(m['home']['color']) + (255,))
    ld.polygon([(760 * S, 0), (WW, 0), (WW, HH), (980 * S, HH)], fill=tuple(m['away']['color']) + (255,))
    ld.polygon([(520 * S, 0), (560 * S, 0), (340 * S, HH), (300 * S, HH)], fill=(255, 255, 255, 40))
    ld.polygon([(720 * S, 0), (760 * S, 0), (980 * S, HH), (940 * S, HH)], fill=(255, 255, 255, 40))
    bg.alpha_composite(L)
    bg = _canvas_texture(bg.convert('RGB'), 0.7).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    for side, cx in ((m['home'], 190), (m['away'], 1096)):
        _logo(ov, side.get('team'), cx, 190, 200, 140, S)
    d = ImageDraw.Draw(ov)
    _spaced(d, (WW / 2, 56 * S), 'JARVIS | NHL', _f('oswald_b', 22 * S), (255, 255, 255, 255), 5 * S, anchor='m')
    _spaced(d, (WW / 2, 92 * S), m['league'], _f('oswald', 15 * S), (226, 232, 240, 235), 4 * S, anchor='m')

    fn = _fit(m['home']['name'], 'oswald_b', 76 * S, 560 * S, min_size=34 * S)
    d.text((WW / 2, 262 * S), m['home']['name'], font=fn, fill=(255, 255, 255, 255), anchor='mm')
    _spaced(d, (WW / 2, 312 * S), 'ПРОТИВ', _f('oswald', 17 * S), (226, 232, 240, 230), 8 * S, anchor='m')
    fn = _fit(m['away']['name'], 'oswald_b', 76 * S, 560 * S, min_size=34 * S)
    d.text((WW / 2, 364 * S), m['away']['name'], font=fn, fill=(255, 255, 255, 255), anchor='mm')

    L, ld = _layer_draw(ov)
    ld.rectangle((0, 452 * S, WW, 552 * S), fill=(10, 12, 16, 240))
    ld.rectangle((0, 452 * S, WW, 456 * S), fill=(255, 255, 255, 130))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    _spaced(d, (64 * S, 482 * S), 'ПРОГНОЗ', _f('oswald', 13 * S), (150, 158, 170, 255), 3 * S)
    fp = _fit(m['pred'], 'oswald_b', 30 * S, 720 * S, min_size=18 * S)
    d.text((64 * S, 518 * S), m['pred'], font=fp, fill=(255, 255, 255, 255), anchor='lm')
    d.text(((W - 64) * S, 506 * S), '%.2f' % m['coef'], font=_f('oswald_b', 44 * S), fill=(255, 255, 255, 255), anchor='rm')
    _spaced(d, ((W - 64) * S, 470 * S), 'КЭФ', _f('oswald', 13 * S), (150, 158, 170, 255), 3 * S, anchor='r')
    _spaced(d, (64 * S, 596 * S), m['when'], _f('oswald_b', 16 * S), (236, 240, 246, 255), 3 * S)
    _spaced(d, ((W - 64) * S, 596 * S), handle, _f('oswald', 14 * S), (226, 232, 240, 235), 3 * S, anchor='r')
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 11. НАКЛЕЙКИ · Rubik
def render_sticker(m, path, W=1280, H=640, handle='@jarvibet'):
    S = 2
    WW, HH = W * S, H * S
    base = tuple(int(a * 0.5 + b * 0.5) for a, b in zip(m['home']['color'], m['away']['color']))
    bg = _grad(WW, HH, tuple(min(255, int(c * 1.5 + 26)) for c in base), tuple(int(c * 0.8) for c in base))
    L, ld = _layer_draw(bg)
    rnd = random.Random(12)
    for _ in range(18):
        cx, cy = rnd.uniform(0, WW), rnd.uniform(0, HH)
        r = rnd.uniform(18 * S, 60 * S)
        ld.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, 26), width=3 * S)
    bg.alpha_composite(L)

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))

    def badge(team, cx, cy, angle):
        d_ = int(216 * S)
        tile = Image.new('RGBA', (d_, d_), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        td.rounded_rectangle((0, 0, d_ - 1, d_ - 1), radius=int(d_ * 0.26), fill=(255, 255, 255, 255))
        e = _raw_emblem(team, int(150 * S), int(112 * S), plate=False)
        tile.alpha_composite(e, ((d_ - e.width) // 2, (d_ - e.height) // 2))
        tile = tile.rotate(angle, expand=True, resample=Image.BICUBIC)
        _shadowed(ov, tile, (int(cx * S - tile.width / 2), int(cy * S - tile.height / 2)),
                  blur=22, off=(0, 14), color=(0, 0, 0, 120))

    badge(m['home'].get('team'), 322, 238, 6)
    badge(m['away'].get('team'), 958, 238, -6)
    d = ImageDraw.Draw(ov)
    _spaced(d, (WW / 2, 56 * S), 'JARVIS | NHL', _f('rubik_b', 22 * S), (255, 255, 255, 255), 4 * S, anchor='m')
    _spaced(d, (WW / 2, 92 * S), m['league'], _f('rubik', 13 * S), (240, 244, 250, 230), 3 * S, anchor='m')

    for side, cx in ((m['home'], 322), (m['away'], 958)):
        name = side['name']
        fn = _fit(name, 'rubik_b', 26 * S, 380 * S, min_size=16 * S)
        tw = fn.getlength(name)
        L, ld = _layer_draw(ov)
        ld.rounded_rectangle((cx * S - tw / 2 - 26 * S, 376 * S, cx * S + tw / 2 + 26 * S, 428 * S),
                             radius=26 * S, fill=(16, 20, 28, 240))
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)
        d.text((cx * S, 402 * S), name, font=fn, fill=(255, 255, 255, 255), anchor='mm')
    d.text((WW / 2, 238 * S), 'VS', font=_f('rubik_b', 34 * S), fill=(255, 255, 255, 245), anchor='mm')

    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((70 * S, 466 * S, 940 * S, 560 * S), radius=30 * S, fill=(255, 255, 255, 250))
    ld.ellipse((972 * S, 456 * S, 1140 * S, 570 * S), fill=(16, 20, 28, 250))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    _spaced(d, (108 * S, 494 * S), 'ПРОГНОЗ', _f('rubik', 12 * S), (120, 126, 136, 255), 3 * S)
    fp = _fit(m['pred'], 'rubik_b', 25 * S, 780 * S, min_size=15 * S)
    d.text((108 * S, 528 * S), m['pred'], font=fp, fill=(18, 22, 30, 255), anchor='lm')
    _spaced(d, (1056 * S, 490 * S), 'КЭФ', _f('rubik', 12 * S), (176, 184, 196, 255), 2.4 * S, anchor='m')
    d.text((1056 * S, 526 * S), '%.2f' % m['coef'], font=_f('rubik_b', 28 * S), fill=(255, 255, 255, 255), anchor='mm')
    _spaced(d, (WW / 2, 600 * S), m['when'] + '   ·   ' + handle, _f('rubik', 13 * S),
            (246, 248, 252, 240), 3 * S, anchor='m')
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 12. ТЕРМИНАЛ · Roboto Condensed
TERM = (64, 255, 160)


def render_terminal(m, path, W=1280, H=640, handle='@jarvibet'):
    S = 2
    WW, HH = W * S, H * S
    bg = Image.new('RGBA', (WW, HH), (5, 9, 8, 255))
    L, ld = _layer_draw(bg)
    for gy in range(0, HH, 4 * S):
        ld.line((0, gy, WW, gy), fill=(64, 255, 160, 10), width=S)
    ld.ellipse((-400 * S, 120 * S, 1680 * S, 1200 * S), fill=(64, 255, 160, 14))
    bg.alpha_composite(L.filter(ImageFilter.GaussianBlur(2 * S)))

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle((44 * S, 44 * S, (W - 44) * S, (H - 44) * S), outline=TERM + (120,), width=2 * S)
    for cx, cy in ((44, 44), (W - 44, 44), (44, H - 44), (W - 44, H - 44)):
        d.rectangle((cx * S - 7 * S, cy * S - 7 * S, cx * S + 7 * S, cy * S + 7 * S), fill=TERM + (220,))
    _spaced(d, (80 * S, 92 * S), 'JARVIS://NHL', _f('robcond_b', 21 * S), TERM + (255,), 3 * S)
    _spaced(d, ((W - 80) * S, 92 * S), m['league'], _f('robcond', 15 * S), (120, 190, 158, 255), 3 * S, anchor='r')
    d.line((80 * S, 116 * S, (W - 80) * S, 116 * S), fill=TERM + (90,), width=2 * S)

    for side, cx in ((m['home'], 1012), (m['away'], 1140)):
        _logo(ov, side.get('team'), cx, 200, 112, 86, S, blur=10, alpha=90)
    d = ImageDraw.Draw(ov)

    rows = [('МАТЧ', '%s — %s' % (m['home']['name'], m['away']['name'])),
            ('НАЧАЛО', m['when']),
            ('РЫНОК', m['pred']),
            ('ЛИГА', m['league'])]
    y = 172
    for lab, val in rows:
        d.text((80 * S, y * S), '>', font=_f('robcond_b', 22 * S), fill=TERM + (200,), anchor='lm')
        _spaced(d, (112 * S, y * S), lab, _f('robcond', 17 * S), (126, 196, 162, 255), 2.6 * S)
        fv = _fit(val, 'robcond_b', 25 * S, 600 * S, min_size=15 * S)
        d.text((330 * S, y * S), val, font=fv, fill=(224, 255, 240, 255), anchor='lm')
        y += 62
    d.line((80 * S, 428 * S, (W - 80) * S, 428 * S), fill=TERM + (90,), width=2 * S)

    L, ld = _layer_draw(ov)
    ld.rectangle((80 * S, 460 * S, 420 * S, 536 * S), fill=TERM + (235,))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    _spaced(d, (104 * S, 484 * S), 'СТАВКА', _f('robcond_b', 13 * S), (6, 26, 18, 255), 3 * S)
    d.text((104 * S, 516 * S), '%.2f' % m['coef'], font=_f('robcond_b', 32 * S), fill=(5, 22, 15, 255), anchor='lm')
    for i, ln in enumerate((m.get('note', ''), 'СТАТУС: ОПУБЛИКОВАНО')):
        if ln:
            _spaced(d, (460 * S, (482 + i * 34) * S), ln, _f('robcond', 15 * S), (140, 210, 176, 255), 2 * S)
    _spaced(d, ((W - 80) * S, 568 * S), handle, _f('robcond_b', 15 * S), TERM + (255,), 3 * S, anchor='r')
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 13. ЖУРНАЛ · Exo 2 Italic
def render_magazine(m, path, W=1280, H=640, handle='@jarvibet'):
    import numpy as np
    S = 2
    WW, HH = W * S, H * S
    x = np.linspace(0, 1, WW, dtype=np.float32)[None, :, None]
    a = np.array(m['home']['color'], np.float32) * 1.15
    b = np.array((18, 20, 26), np.float32)
    col = a * (1 - x) + b * x
    y = np.linspace(0, 1, HH, dtype=np.float32)[:, None, None]
    col = col * (1.10 - 0.30 * y)
    bg = Image.fromarray(np.clip(col, 0, 255).astype('uint8'), 'RGB').convert('RGBA')
    ghost = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    if m['home'].get('team') in TEAMS:
        e = _raw_emblem(m['home']['team'], 760 * S, 560 * S, plate=False)
        e.putalpha(e.getchannel('A').point(lambda v: int(v * 0.16)))
        ghost.alpha_composite(e, (int(-120 * S), int(HH / 2 - e.height / 2)))
    bg = Image.alpha_composite(bg, ghost.filter(ImageFilter.GaussianBlur(3 * S)))
    bg = _canvas_texture(bg.convert('RGB'), 0.9).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    _logo(ov, m['home'].get('team'), 300, 320, 330, 240, S, blur=34, alpha=160)
    _logo(ov, m['away'].get('team'), 1130, 118, 128, 96, S, blur=14)
    d = ImageDraw.Draw(ov)
    _spaced(d, (620 * S, 90 * S), 'JARVIS | NHL', _f('exo', 17 * S), (255, 255, 255, 255), 5 * S)
    d.line((620 * S, 116 * S, (W - 64) * S, 116 * S), fill=(255, 255, 255, 80), width=2 * S)
    d.text((620 * S, 176 * S), '01', font=_f('exo_i', 58 * S), fill=(255, 255, 255, 70), anchor='lm')
    _spaced(d, (700 * S, 176 * S), 'ПРОГНОЗ ДНЯ', _f('exo', 16 * S), (232, 238, 248, 255), 5 * S)

    fn = _fit(m['home']['name'], 'exo_i', 62 * S, 600 * S, min_size=32 * S)
    d.text((620 * S, 254 * S), m['home']['name'], font=fn, fill=(255, 255, 255, 255), anchor='lm')
    fn = _fit('/ ' + m['away']['name'], 'exo_i', 40 * S, 600 * S, min_size=22 * S)
    d.text((620 * S, 310 * S), '/ ' + m['away']['name'], font=fn, fill=(226, 232, 244, 235), anchor='lm')
    _spaced(d, (620 * S, 360 * S), m['when'], _f('exo', 15 * S), (206, 216, 232, 255), 3 * S)

    d.line((620 * S, 396 * S, (W - 64) * S, 396 * S), fill=(255, 255, 255, 70), width=2 * S)
    fp = _fit(m['pred'], 'exo_i', 30 * S, 580 * S, min_size=17 * S)
    d.text((620 * S, 444 * S), m['pred'], font=fp, fill=(255, 255, 255, 255), anchor='lm')
    L, ld = _layer_draw(ov)
    ld.ellipse((620 * S, 486 * S, 736 * S, 594 * S), fill=(255, 255, 255, 250))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    d.text((678 * S, 528 * S), '%.2f' % m['coef'], font=_f('exo_i', 27 * S), fill=(20, 22, 30, 255), anchor='mm')
    _spaced(d, (678 * S, 562 * S), 'КЭФ', _f('exo', 12 * S), (90, 96, 108, 255), 2.4 * S, anchor='m')
    if m.get('note'):
        _spaced(d, (768 * S, 524 * S), m['note'], _f('exo', 14 * S), (214, 222, 236, 255), 2 * S)
    _spaced(d, ((W - 64) * S, 562 * S), handle, _f('exo', 14 * S), (226, 232, 244, 255), 3 * S, anchor='r')
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 14. КАРТОЧКА · Onest
def render_card(m, path, W=1280, H=640, handle='@jarvibet'):
    S = 2
    WW, HH = W * S, H * S
    bg = _grad(WW, HH, tuple(int(c * 0.9 + 16) for c in m['away']['color']), (10, 12, 18))
    bg = _canvas_texture(bg.convert('RGB'), 0.8).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    card = (330, 46, 950, 594)
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((card[0] * S, card[1] * S, card[2] * S, card[3] * S), radius=26 * S,
                         fill=(247, 249, 252, 252), outline=(255, 255, 255, 255), width=3 * S)
    ld.rounded_rectangle((card[0] * S, card[1] * S, card[2] * S, (card[1] + 96) * S), radius=26 * S,
                         fill=tuple(m['home']['color']) + (255,))
    ld.rectangle((card[0] * S, (card[1] + 60) * S, card[2] * S, (card[1] + 96) * S),
                 fill=tuple(m['home']['color']) + (255,))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    _spaced(d, (640 * S, 78 * S), 'JARVIS | NHL', _f('onest_b', 19 * S), (255, 255, 255, 255), 4 * S, anchor='m')
    _spaced(d, (640 * S, 108 * S), m['league'], _f('onest', 12 * S), (236, 242, 250, 230), 3 * S, anchor='m')

    _logo(ov, m['home'].get('team'), 640, 216, 300, 190, S, plate=False, blur=20, alpha=80)
    d = ImageDraw.Draw(ov)
    fn = _fit(m['home']['name'], 'onest_b', 38 * S, 540 * S, min_size=22 * S)
    d.text((640 * S, 336 * S), m['home']['name'], font=fn, fill=INK + (255,), anchor='mm')
    _spaced(d, (640 * S, 370 * S), 'ПРОТИВ  ' + m['away']['name'], _f('onest', 14 * S),
            (118, 126, 140, 255), 3 * S, anchor='m')
    _logo(ov, m['away'].get('team'), 884, 366, 86, 66, S, plate=False, blur=8, alpha=50)
    d = ImageDraw.Draw(ov)
    d.line((372 * S, 400 * S, 908 * S, 400 * S), fill=(216, 222, 232, 255), width=2 * S)

    for i, (lab, val) in enumerate((('НАЧАЛО', m['when']), ('ПРОГНОЗ', m['pred']))):
        yy = 424 + i * 58
        _spaced(d, (372 * S, yy * S), lab, _f('onest', 11 * S), (140, 148, 162, 255), 3 * S)
        fv = _fit(val, 'onest_b', 20 * S, 540 * S, min_size=13 * S)
        d.text((372 * S, (yy + 26) * S), val, font=fv, fill=INK + (255,), anchor='lm')

    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((372 * S, 528 * S, 908 * S, 578 * S), radius=14 * S, fill=INK + (250,))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    _spaced(d, (398 * S, 553 * S), 'КОЭФФИЦИЕНТ', _f('onest', 12 * S), (158, 168, 184, 255), 2.6 * S)
    d.text((882 * S, 553 * S), '%.2f' % m['coef'], font=_f('onest_b', 26 * S), fill=(255, 255, 255, 255), anchor='rm')
    _spaced(d, (168 * S, 320 * S), handle, _f('onest', 14 * S), (230, 238, 250, 220), 3 * S, anchor='m')
    _spaced(d, (1112 * S, 320 * S), m['league'], _f('onest', 14 * S), (230, 238, 250, 220), 3 * S, anchor='m')
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 15. МАТЧ-ЦЕНТР · Golos Text
def render_app(m, path, W=1280, H=640, handle='@jarvibet'):
    S = 2
    WW, HH = W * S, H * S
    bg = _grad(WW, HH, (16, 21, 32), (9, 12, 19))
    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((60 * S, 44 * S, (W - 60) * S, 112 * S), radius=20 * S, fill=(255, 255, 255, 16))
    ld.rounded_rectangle((60 * S, 128 * S, (W - 60) * S, 380 * S), radius=24 * S,
                         fill=(255, 255, 255, 20), outline=(255, 255, 255, 34), width=2 * S)
    ld.rounded_rectangle((60 * S, 396 * S, (W - 60) * S, 544 * S), radius=24 * S,
                         fill=(255, 255, 255, 20), outline=(255, 255, 255, 34), width=2 * S)
    ld.rounded_rectangle((880 * S, 424 * S, (W - 92) * S, 516 * S), radius=18 * S, fill=(88, 205, 140, 255))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)

    _spaced(d, (92 * S, 78 * S), 'МАТЧ-ЦЕНТР', _f('mont_b', 17 * S), (236, 242, 250, 255), 3 * S)
    _spaced(d, ((W - 92) * S, 78 * S), 'JARVIS | NHL', _f('mont_m', 15 * S), (150, 208, 255, 255), 3 * S, anchor='r')

    _spaced(d, (WW / 2, 168 * S), m['league'] + '  ·  ' + m['when'], _f('mont_m', 13 * S),
            (156, 168, 188, 255), 3 * S, anchor='m')
    for side, cx in ((m['home'], 320), (m['away'], 960)):
        _logo(ov, side.get('team'), cx, 258, 168, 118, S, blur=16)
    d = ImageDraw.Draw(ov)
    for side, cx in ((m['home'], 320), (m['away'], 960)):
        fn = _fit(side['name'], 'golos_b', 26 * S, 400 * S, min_size=16 * S)
        d.text((cx * S, 336 * S), side['name'], font=fn, fill=(255, 255, 255, 255), anchor='mm')
    d.text((WW / 2, 258 * S), 'VS', font=_f('mont_b', 24 * S), fill=(210, 220, 236, 235), anchor='mm')

    _spaced(d, (92 * S, 432 * S), 'СТАВКА', _f('mont_m', 12 * S), (150, 162, 182, 255), 3 * S)
    fp = _fit(m['pred'], 'golos_b', 24 * S, 720 * S, min_size=15 * S)
    d.text((92 * S, 470 * S), m['pred'], font=fp, fill=(255, 255, 255, 255), anchor='lm')
    if m.get('note'):
        _spaced(d, (92 * S, 506 * S), m['note'], _f('mont_m', 13 * S), (146, 158, 178, 255), 2 * S)
    _spaced(d, (1034 * S, 452 * S), 'КЭФ', _f('mont_m', 12 * S), (8, 42, 24, 255), 2.4 * S, anchor='m')
    d.text((1034 * S, 486 * S), '%.2f' % m['coef'], font=_f('mont_b', 28 * S), fill=(6, 34, 20, 255), anchor='mm')

    for i, lab in enumerate(('ПРОГНОЗЫ', 'ИТОГИ', 'ТАБЛИЦА')):
        cx = 300 + i * 340
        col = (150, 208, 255) if i == 0 else (120, 132, 152)
        _spaced(d, (cx * S, 592 * S), lab, _f('mont_m', 13 * S), col + (255,), 3 * S, anchor='m')
    d.line((214 * S, 612 * S, 386 * S, 612 * S), fill=(150, 208, 255, 255), width=3 * S)
    return _save(bg, ov, W, H, path)
