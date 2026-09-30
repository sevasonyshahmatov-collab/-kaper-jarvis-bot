"""Пять вариантов оформления постов НХЛ — разные по структуре, а не по цвету.

1. rink     — светлый лёд с разметкой площадки, красный акцент
2. jersey   — диптих в свитерных полосах с медальоном VS
3. ticker   — тёмная инфографика со статистикой матча
4. poster   — асимметричная афиша с эмблемой навылет
5. ticket   — купон: светлая карточка с перфорацией на тёмном фоне
"""
import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from poster import TEAMS, _raw_emblem, _canvas_texture, _shadowed, _layer_draw, _spaced
from recap import _needs_plate

_FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
F = {
    'brand': (_FD + '/Unbounded[wght].ttf', 800),
    'display': (_FD + '/RussoOne-Regular.ttf', None),
    'cond': (_FD + '/Oswald[wght].ttf', 600),
    'cond_b': (_FD + '/Oswald[wght].ttf', 700),
    'text': (_FD + '/Manrope[wght].ttf', 700),
    'text_m': (_FD + '/Manrope[wght].ttf', 500),
    'tech': (_FD + '/Tektur[wdth,wght].ttf', None),
}
ICE = (122, 202, 255)
PUCK_RED = (208, 42, 46)
INK = (10, 20, 33)


def _f(kind, size):
    p, w = F[kind]
    f = ImageFont.truetype(p, int(size))
    if w:
        try:
            f.set_variation_by_axes([w])
        except Exception:
            pass
    return f


def _fit(text, kind, size, max_w, min_size=13):
    f = _f(kind, size)
    while f.getlength(text) > max_w and size > min_size:
        size -= 1
        f = _f(kind, size)
    return f


def _emb(ov, team, cx, cy, w, h, S, blur=28, alpha=140):
    if team not in TEAMS:
        return
    e = _raw_emblem(team, int(w * S), int(h * S), plate=_needs_plate(team))
    _shadowed(ov, e, (int(cx * S - e.width / 2), int(cy * S - e.height / 2)),
              blur=blur, off=(0, 14), color=(0, 0, 0, alpha))
    return e


def _brand(d, cx, y, S, size=24, tag='NHL', light=(255, 255, 255), accent=ICE):
    fb = _f('brand', size * S)
    sp = 3 * S
    bar = 20 * S
    w1 = sum(fb.getlength(c) for c in 'JARVIS') + sp * 5
    w2 = sum(fb.getlength(c) for c in tag) + sp * (len(tag) - 1)
    x0 = cx - (w1 + 2 * bar + w2) / 2
    _spaced(d, (x0, y), 'JARVIS', fb, light + (255,), sp)
    d.rounded_rectangle((x0 + w1 + bar - 1.5 * S, y - 13 * S, x0 + w1 + bar + 1.5 * S, y + 13 * S),
                        radius=S, fill=light + (140,))
    _spaced(d, (x0 + w1 + 2 * bar, y), tag, fb, accent + (255,), sp)


def _save(bg, ov, W, H, path, sharpen=True):
    if bg.size != (W, H):
        bg = bg.resize((W, H), Image.LANCZOS)
    ov = ov.resize((W, H), Image.LANCZOS)
    out = Image.alpha_composite(bg.convert('RGBA'), ov).convert('RGB')
    if sharpen:
        out = out.filter(ImageFilter.UnsharpMask(radius=1.0, percent=45, threshold=2))
    out.save(path, optimize=True) if path.lower().endswith('.png') else out.save(path, quality=96, subsampling=0)
    return path


# ------------------------------------------------ 1. ЛЁД
def render_rink(m, path, W=1280, H=640, handle='@jarvibet'):
    import numpy as np
    S = 2
    WW, HH = W * S, H * S
    y = np.linspace(0, 1, HH, dtype=np.float32)[:, None, None]
    base = np.array((243, 247, 251), np.float32) * (1 - y * 0.10) + np.array((214, 228, 242), np.float32) * (y * 0.10)
    bg = Image.fromarray(np.clip(base.repeat(WW, axis=1), 0, 255).astype('uint8'), 'RGB').convert('RGBA')

    L, ld = _layer_draw(bg)
    ld.rectangle((0, 0, WW, 8 * S), fill=PUCK_RED + (255,))
    for x in (400, 880):                                   # синие линии
        ld.rectangle((x * S - 7 * S, 8 * S, x * S + 7 * S, HH), fill=(30, 84, 178, 92))
    ld.rectangle((640 * S - 5 * S, 8 * S, 640 * S + 5 * S, HH), fill=PUCK_RED + (105,))
    for x in (120, 1160):                                  # линии ворот
        ld.rectangle((x * S - 2 * S, 8 * S, x * S + 2 * S, HH), fill=PUCK_RED + (70,))
    ld.ellipse((640 * S - 168 * S, 286 * S - 168 * S, 640 * S + 168 * S, 286 * S + 168 * S),
               outline=PUCK_RED + (95,), width=5 * S)
    for cx, cy in ((400, 150), (400, 424), (880, 150), (880, 424)):
        ld.ellipse((cx * S - 9 * S, cy * S - 9 * S, cx * S + 9 * S, cy * S + 9 * S), fill=PUCK_RED + (110,))
    rnd = random.Random(4)                                  # следы коньков
    for _ in range(26):
        x0, y0 = rnd.uniform(0, WW), rnd.uniform(40 * S, HH)
        ln = rnd.uniform(40 * S, 150 * S)
        ld.line((x0, y0, x0 + ln * rnd.choice((1, -1)), y0 + rnd.uniform(-12 * S, 12 * S)),
                fill=(255, 255, 255, rnd.randint(70, 130)), width=rnd.choice((1, 2)) * S)
    bg.alpha_composite(L)
    bg = _canvas_texture(bg.convert('RGB'), 0.5).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _brand(d, WW / 2, int(54 * S), S, size=24, tag=m.get('league_tag', 'NHL'), light=INK, accent=PUCK_RED)
    _spaced(d, (WW / 2, 94 * S), m['league'], _f('cond_b', 16 * S), (74, 94, 118, 255), 3 * S, anchor='m')

    for side, cx in ((m['home'], 250), (m['away'], 1030)):
        _emb(ov, side.get('team'), cx, 246, 236, 168, S, alpha=90)
    d = ImageDraw.Draw(ov)
    for side, cx in ((m['home'], 250), (m['away'], 1030)):
        fn = _fit(side['name'], 'display', 38 * S, 420 * S, min_size=24 * S)
        d.text((cx * S, 372 * S), side['name'], font=fn, fill=INK + (255,), anchor='mm')
        _spaced(d, (cx * S, 404 * S), side['sub'], _f('cond', 15 * S), (92, 112, 136, 255), 3 * S, anchor='m')
    d.text((WW / 2, 246 * S), 'VS', font=_f('display', 34 * S), fill=(40, 60, 86, 235), anchor='mm')
    if m.get('note'):
        _spaced(d, (WW / 2, 438 * S), m['note'], _f('cond', 14 * S), (96, 116, 140, 255), 2 * S, anchor='m')

    L, ld = _layer_draw(ov)                                 # тёмная лента снизу
    ld.rounded_rectangle((40 * S, 470 * S, (W - 40) * S, 560 * S), radius=20 * S, fill=INK + (240,))
    ld.rounded_rectangle(((W - 246) * S, 484 * S, (W - 54) * S, 546 * S), radius=14 * S, fill=PUCK_RED + (255,))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    _spaced(d, (74 * S, 497 * S), 'ПРОГНОЗ', _f('cond', 13 * S), (140, 162, 186, 255), 2.4 * S)
    fp = _fit(m['pred'], 'display', 25 * S, 700 * S, min_size=16 * S)
    d.text((74 * S, 527 * S), m['pred'], font=fp, fill=(255, 255, 255, 255), anchor='lm')
    _spaced(d, ((W - 150) * S, 501 * S), 'КЭФ', _f('cond_b', 12 * S), (255, 230, 230, 255), 2 * S, anchor='m')
    d.text(((W - 150) * S, 528 * S), '%.2f' % m['coef'], font=_f('display', 28 * S),
           fill=(255, 255, 255, 255), anchor='mm')
    _spaced(d, (WW / 2, 592 * S), m['when'], _f('cond_b', 15 * S), (58, 78, 104, 255), 2.4 * S, anchor='m')
    _spaced(d, (WW / 2, 620 * S), handle, _f('cond', 13 * S), PUCK_RED + (255,), 2.4 * S, anchor='m')
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 2. ДИПТИХ В ПОЛОСАХ
def render_jersey(m, path, W=1280, H=640, handle='@jarvibet'):
    S = 2
    WW, HH = W * S, H * S
    bg = Image.new('RGBA', (WW, HH), (12, 16, 24, 255))
    for half, side in enumerate((m['home'], m['away'])):
        x0, x1 = (0, WW // 2) if half == 0 else (WW // 2, WW)
        panel = Image.new('RGBA', (x1 - x0, HH), tuple(side['color']) + (255,))
        pd = ImageDraw.Draw(panel)
        stripe = side.get('stripe', (255, 255, 255))
        for k, (off, wdt, al) in enumerate(((-120, 46, 44), (10, 26, 30), (150, 64, 26), (330, 22, 34))):
            pd.polygon([(off, HH), (off + wdt, HH), (off + wdt + 260, 0), (off + 260, 0)],
                       fill=stripe + (al,))
        sh = Image.new('RGBA', panel.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle((0, HH * 0.62, panel.width, HH), fill=(0, 0, 0, 110))
        panel.alpha_composite(sh.filter(ImageFilter.GaussianBlur(70)))
        bg.alpha_composite(panel, (x0, 0))
    L, ld = _layer_draw(bg)
    ld.rectangle((WW // 2 - 2 * S, 0, WW // 2 + 2 * S, HH), fill=(255, 255, 255, 60))
    bg.alpha_composite(L)
    bg = _canvas_texture(bg.convert('RGB'), 0.8).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _brand(d, WW / 2, int(50 * S), S, size=23, tag=m.get('league_tag', 'NHL'))
    for side, cx in ((m['home'], 320), (m['away'], 960)):
        _emb(ov, side.get('team'), cx, 226, 224, 160, S)
    d = ImageDraw.Draw(ov)
    for side, cx in ((m['home'], 320), (m['away'], 960)):
        fn = _fit(side['name'], 'cond_b', 46 * S, 480 * S, min_size=26 * S)
        d.text((cx * S, 356 * S), side['name'], font=fn, fill=(255, 255, 255, 255), anchor='mm')
        _spaced(d, (cx * S, 392 * S), side['sub'], _f('cond', 15 * S), (226, 234, 244, 235), 3 * S, anchor='m')

    md = int(84 * S)                                        # медальон VS по стыку
    L, ld = _layer_draw(ov)
    ld.ellipse((WW / 2 - md, 226 * S - md, WW / 2 + md, 226 * S + md), fill=(10, 14, 22, 240),
               outline=ICE + (235,), width=3 * S)
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    d.text((WW / 2, 226 * S), 'VS', font=_f('display', 36 * S), fill=(255, 255, 255, 255), anchor='mm')

    L, ld = _layer_draw(ov)                                 # вымпел с прогнозом
    ld.polygon([(36 * S, 446 * S), ((W - 36) * S, 446 * S), ((W - 62) * S, 508 * S),
                ((W - 36) * S, 570 * S), (36 * S, 570 * S), (62 * S, 508 * S)],
               fill=(8, 12, 20, 232), outline=ICE + (150,), width=2 * S)
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    fp = _fit(m['pred'], 'display', 27 * S, 700 * S, min_size=17 * S)
    d.text((WW / 2 - 92 * S, 490 * S), m['pred'], font=fp, fill=(255, 255, 255, 255), anchor='mm')
    _spaced(d, (WW / 2 - 92 * S, 532 * S), m['when'], _f('cond', 15 * S), (188, 206, 228, 255), 2.4 * S, anchor='m')
    L, ld = _layer_draw(ov)
    ld.ellipse((980 * S, 456 * S, 1092 * S, 560 * S), fill=ICE + (255,))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    _spaced(d, (1036 * S, 486 * S), 'КЭФ', _f('cond_b', 12 * S), (10, 28, 42, 255), 2 * S, anchor='m')
    d.text((1036 * S, 520 * S), '%.2f' % m['coef'], font=_f('display', 27 * S), fill=(6, 20, 32, 255), anchor='mm')
    _spaced(d, (WW / 2, 608 * S), handle, _f('cond', 13 * S), (226, 236, 248, 255), 2.4 * S, anchor='m')
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 3. ТИКЕР СО СТАТИСТИКОЙ
def render_ticker(m, path, W=1280, H=640, handle='@jarvibet'):
    import numpy as np
    S = 2
    WW, HH = W * S, H * S
    y = np.linspace(0, 1, HH, dtype=np.float32)[:, None, None]
    base = np.array((13, 22, 38), np.float32) * (1 - y) + np.array((8, 13, 22), np.float32) * y
    bg = Image.fromarray(np.clip(base.repeat(WW, axis=1), 0, 255).astype('uint8'), 'RGB').convert('RGBA')
    L, ld = _layer_draw(bg)
    for gx in range(0, WW, 40 * S):
        ld.line((gx, 0, gx, HH), fill=(255, 255, 255, 8), width=S)
    for gy in range(0, HH, 40 * S):
        ld.line((0, gy, WW, gy), fill=(255, 255, 255, 8), width=S)
    ld.ellipse((-300 * S, -260 * S, 520 * S, 260 * S), fill=(m['home']['color']) + (60,))
    ld.ellipse((760 * S, -260 * S, 1580 * S, 260 * S), fill=(m['away']['color']) + (60,))
    bg.alpha_composite(L.filter(ImageFilter.GaussianBlur(60 * S // 2)))
    bg = _canvas_texture(bg.convert('RGB'), 0.7).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _brand(d, WW / 2, int(48 * S), S, size=23, tag=m.get('league_tag', 'NHL'))
    _spaced(d, (WW / 2, 86 * S), m['league'], _f('cond_b', 15 * S), (168, 188, 212, 255), 3 * S, anchor='m')

    for side, cx in ((m['home'], 128), (m['away'], 1152)):
        _emb(ov, side.get('team'), cx, 156, 150, 108, S, blur=18)
    d = ImageDraw.Draw(ov)
    fn = _fit(m['home']['name'], 'display', 30 * S, 340 * S, min_size=20 * S)
    d.text((232 * S, 150 * S), m['home']['name'], font=fn, fill=(255, 255, 255, 255), anchor='lm')
    fn = _fit(m['away']['name'], 'display', 30 * S, 340 * S, min_size=20 * S)
    d.text((1048 * S, 150 * S), m['away']['name'], font=fn, fill=(255, 255, 255, 255), anchor='rm')
    _spaced(d, (WW / 2, 130 * S), m['when'], _f('cond_b', 16 * S), ICE + (255,), 2.4 * S, anchor='m')
    _spaced(d, (WW / 2, 162 * S), 'НАЧАЛО', _f('cond', 12 * S), (150, 170, 196, 255), 2.4 * S, anchor='m')

    rows = m.get('stats', [])
    top = 240
    for i, (lab, val) in enumerate(rows):
        yy = top + i * 70
        L, ld = _layer_draw(ov)
        ld.rounded_rectangle((60 * S, yy * S, (W - 60) * S, (yy + 56) * S), radius=14 * S,
                             fill=(255, 255, 255, 14), outline=(255, 255, 255, 30), width=S)
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)
        _spaced(d, (88 * S, (yy + 28) * S), lab, _f('cond', 15 * S), (178, 196, 218, 255), 2 * S)
        d.text(((W - 88) * S, (yy + 28) * S), val, font=_f('display', 20 * S),
               fill=(255, 255, 255, 255), anchor='rm')

    ybar = top + len(rows) * 70 + 14
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((60 * S, ybar * S, (W - 60) * S, (ybar + 84) * S), radius=16 * S,
                         fill=(10, 16, 26, 235), outline=ICE + (200,), width=2 * S)
    ld.rounded_rectangle((60 * S, ybar * S, 70 * S, (ybar + 84) * S), radius=4 * S, fill=ICE + (255,))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    _spaced(d, (96 * S, (ybar + 28) * S), 'ПРОГНОЗ', _f('cond', 12 * S), (150, 176, 204, 255), 2.4 * S)
    fp = _fit(m['pred'], 'display', 24 * S, 700 * S, min_size=16 * S)
    d.text((96 * S, (ybar + 58) * S), m['pred'], font=fp, fill=(255, 255, 255, 255), anchor='lm')
    d.text(((W - 92) * S, (ybar + 50) * S), '%.2f' % m['coef'], font=_f('display', 34 * S),
           fill=ICE + (255,), anchor='rm')
    _spaced(d, ((W - 92) * S, (ybar + 20) * S), 'КЭФ', _f('cond', 12 * S), (150, 176, 204, 255), 2.4 * S, anchor='r')
    _spaced(d, (WW / 2, 616 * S), handle, _f('cond', 13 * S), (196, 212, 232, 255), 2.4 * S, anchor='m')
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 4. АФИША
def render_poster(m, path, W=1280, H=640, handle='@jarvibet'):
    import numpy as np
    S = 2
    WW, HH = W * S, H * S
    x = np.linspace(0, 1, WW, dtype=np.float32)[None, :, None]
    left = np.array(m['home']['color'], np.float32)
    right = np.array((16, 20, 27), np.float32)
    t = np.clip((x - 0.40) / 0.06, 0, 1)
    col = left * (1 - t) + right * t
    yv = np.linspace(0, 1, HH, dtype=np.float32)[:, None, None]
    col = col * (1.16 - 0.34 * yv)
    bg = Image.fromarray(np.clip(col, 0, 255).astype('uint8'), 'RGB').convert('RGBA')
    bg = _canvas_texture(bg.convert('RGB'), 0.85).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    # эмблема хозяев — крупно, с уходом за край
    if m['home'].get('team') in TEAMS:
        e = _raw_emblem(m['home']['team'], 620 * S, 470 * S, plate=False)
        _shadowed(ov, e, (int(-70 * S), int(HH / 2 - e.height / 2)), blur=40, off=(0, 20), color=(0, 0, 0, 160))
    d = ImageDraw.Draw(ov)
    L, ld = _layer_draw(ov)
    ld.rectangle((545 * S, 96 * S, 548 * S, 552 * S), fill=ICE + (190,))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)

    xs = 592
    _brand(d, (xs + 250) * S, int(70 * S), S, size=22, tag=m.get('league_tag', 'NHL'))
    _spaced(d, (xs * S, 128 * S), m['league'], _f('cond_b', 15 * S), (176, 196, 220, 255), 3 * S)
    fn = _fit(m['home']['name'], 'display', 52 * S, 620 * S, min_size=30 * S)
    d.text((xs * S, 196 * S), m['home']['name'], font=fn, fill=(255, 255, 255, 255), anchor='lm')
    _spaced(d, (xs * S, 238 * S), 'ПРОТИВ', _f('cond', 15 * S), ICE + (255,), 4 * S)
    fn = _fit(m['away']['name'], 'display', 40 * S, 520 * S, min_size=24 * S)
    d.text((xs * S, 282 * S), m['away']['name'], font=fn, fill=(236, 242, 250, 255), anchor='lm')
    _emb(ov, m['away'].get('team'), 1160, 250, 150, 130, S, blur=18)
    d = ImageDraw.Draw(ov)

    L, ld = _layer_draw(ov)
    ld.line((xs * S, 324 * S, (W - 56) * S, 324 * S), fill=(255, 255, 255, 46), width=2 * S)
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    _spaced(d, (xs * S, 360 * S), m['when'], _f('cond_b', 16 * S), (222, 232, 246, 255), 2.4 * S)
    if m.get('note'):
        _spaced(d, (xs * S, 392 * S), m['note'], _f('cond', 13 * S), (170, 190, 214, 255), 2 * S)

    _spaced(d, (xs * S, 442 * S), 'ПРОГНОЗ', _f('cond', 13 * S), ICE + (255,), 2.8 * S)
    fp = _fit(m['pred'], 'display', 30 * S, 560 * S, min_size=18 * S)
    d.text((xs * S, 486 * S), m['pred'], font=fp, fill=(255, 255, 255, 255), anchor='lm')
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((xs * S, 524 * S, (xs + 196) * S, 586 * S), radius=14 * S, fill=ICE + (255,))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    _spaced(d, ((xs + 40) * S, 555 * S), 'КЭФ', _f('cond_b', 13 * S), (8, 24, 38, 255), 2 * S, anchor='m')
    d.text(((xs + 130) * S, 555 * S), '%.2f' % m['coef'], font=_f('display', 27 * S), fill=(6, 20, 32, 255), anchor='mm')
    _spaced(d, ((W - 64) * S, 604 * S), handle, _f('cond', 13 * S), (196, 212, 232, 255), 2.4 * S, anchor='r')
    _spaced(d, (xs * S, 604 * S), 'КОЭФФИЦИЕНТ НА МОМЕНТ ПУБЛИКАЦИИ', _f('cond', 12 * S), (150, 170, 196, 255), 2 * S)
    return _save(bg, ov, W, H, path)


# ------------------------------------------------ 5. КУПОН
def render_ticket(m, path, W=1280, H=640, handle='@jarvibet'):
    import numpy as np
    S = 2
    WW, HH = W * S, H * S
    yv = np.linspace(0, 1, HH, dtype=np.float32)[:, None, None]
    a = np.array(m['home']['color'], np.float32) * 0.55 + np.array((10, 14, 22), np.float32) * 0.45
    b = np.array(m['away']['color'], np.float32) * 0.55 + np.array((10, 14, 22), np.float32) * 0.45
    x = np.linspace(0, 1, WW, dtype=np.float32)[None, :, None]
    col = a * (1 - x) + b * x
    col = col * (1.05 - 0.42 * yv)
    bg = Image.fromarray(np.clip(col, 0, 255).astype('uint8'), 'RGB').convert('RGBA')
    bg = _canvas_texture(bg.convert('RGB'), 0.8).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    card = (150, 74, 1130, 566)
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((card[0] * S, card[1] * S, card[2] * S, card[3] * S), radius=26 * S,
                         fill=(244, 247, 251, 252))
    ov.alpha_composite(L)
    # вырезы и перфорация
    notch_y = 430
    cut = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cut)
    for cx in (card[0], card[2]):
        cd.ellipse((cx * S - 22 * S, notch_y * S - 22 * S, cx * S + 22 * S, notch_y * S + 22 * S),
                   fill=(0, 0, 0, 255))
    ov = Image.alpha_composite(ov, Image.new('RGBA', (WW, HH), (0, 0, 0, 0)))
    arr = np.array(ov)
    cut_a = np.array(cut)[..., 3] > 0
    arr[cut_a] = 0
    ov = Image.fromarray(arr, 'RGBA')
    d = ImageDraw.Draw(ov)
    for xd in range(int((card[0] + 34) * S), int((card[2] - 34) * S), int(16 * S)):
        d.line((xd, notch_y * S, xd + 8 * S, notch_y * S), fill=(24, 34, 48, 90), width=2 * S)

    _brand(d, WW / 2, int(122 * S), S, size=22, tag=m.get('league_tag', 'NHL'), light=INK, accent=PUCK_RED)
    _spaced(d, (WW / 2, 158 * S), 'КУПОН ПРОГНОЗА · ' + m['league'], _f('cond', 13 * S),
            (104, 122, 146, 255), 2.6 * S, anchor='m')
    d.line((186 * S, 184 * S, 1094 * S, 184 * S), fill=(24, 34, 48, 40), width=2 * S)

    rows = [('СОБЫТИЕ', '%s — %s' % (m['home']['name'], m['away']['name'])),
            ('РЫНОК', m['pred']),
            ('НАЧАЛО', m['when'])]
    for i, (lab, val) in enumerate(rows):
        yy = 214 + i * 66
        _spaced(d, (186 * S, yy * S), lab, _f('cond', 12 * S), (132, 148, 170, 255), 2.4 * S)
        fv = _fit(val, 'display', 25 * S, 900 * S, min_size=15 * S)
        d.text((186 * S, (yy + 28) * S), val, font=fv, fill=INK + (255,), anchor='lm')

    for side, cx in ((m['home'], 980), (m['away'], 1064)):
        _emb(ov, side.get('team'), cx, 232, 74, 62, S, blur=10, alpha=70)
    d = ImageDraw.Draw(ov)

    _spaced(d, (186 * S, 466 * S), 'КОЭФФИЦИЕНТ', _f('cond', 12 * S), (132, 148, 170, 255), 2.4 * S)
    d.text((186 * S, 512 * S), '%.2f' % m['coef'], font=_f('display', 46 * S), fill=PUCK_RED + (255,), anchor='lm')
    rnd = random.Random(9)                                   # штрих-код
    bx = 700
    for _ in range(46):
        w_ = rnd.choice((2, 2, 3, 5))
        d.rectangle((bx * S, 470 * S, (bx + w_) * S, 520 * S), fill=(24, 34, 48, 205))
        bx += w_ + rnd.choice((2, 3, 4))
    _spaced(d, (1094 * S, 540 * S), handle, _f('cond', 13 * S), (104, 122, 146, 255), 2.4 * S, anchor='r')
    _spaced(d, (WW / 2, 600 * S), 'КОЭФФИЦИЕНТ НА МОМЕНТ ПУБЛИКАЦИИ', _f('cond', 12 * S),
            (226, 234, 246, 220), 2.4 * S, anchor='m')
    return _save(bg, ov, W, H, path)
