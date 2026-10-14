"""«Versus» — 7 стилей оформления (14.10.2026, пробы по просьбе владельца). Раскладка та же, что у versus.py /
versus_premium.py (смещённые панели клубов, аббревиатуры лесенкой, дата, время МСК, линия П1/Х/П2), меняется подача:

    neon    «Неон»       — чёрный фон с сеткой, тёмные панели со светящейся кромкой в цветах клубов, неоновые буквы
    carbon  «Карбон»     — карбоновое плетение, панели «шлифованный металл», хромированная рамка и цифры
    marble  «Мрамор»     — чёрный мрамор с золотыми прожилками, матовые панели, двойная золотая рамка, золотые буквы
    ice     «Лёд»        — светлый иней, панели под матовым стеклом, белая рамка, тёмно-синие цифры (светлая тема)
    sport   «Спорт»      — скошенные углы панелей, косые полосы скорости, наклонные буквы с обводкой
    holo    «Голограмма» — переливающаяся радужная плёнка на панелях, рамке, буквах и плашках
    swiss   «Швейцария»  — светлая бумага, плоские цветные блоки без колец, чёрная строгая типографика и сетка

    import versus_styles
    versus_styles.render('Северсталь', 'СКА', 'out/vs_neon.jpg', style='neon', date='13 октября', time='19:00',
                         odds=(2.60, 4.20, 2.35))
Размер: 1080×1080 × quality.S (4К — 3240×3240).
"""
import colorsys
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

import brand_kit
import nhl
import poster
from versus import S, W, H, _fit, _mix, _panel, _team, _distinct, _vertical
from versus_premium import (GOLD, GOLD_HI, GOLD_LO, _emblem_gloss, _gloss_panel, _grad_text, _glass, _hairline,
                            _round_mask, _vgrad)

P1 = (100, 26, 620, 672)
P2 = (460, 408, 980, 1054)
STYLES = ('neon', 'carbon', 'marble', 'ice', 'sport', 'holo', 'swiss')
NAMES = {'neon': 'Неон', 'carbon': 'Карбон', 'marble': 'Мрамор', 'ice': 'Лёд', 'sport': 'Спорт',
         'holo': 'Голограмма', 'swiss': 'Швейцария'}
SILVER = [(0, (255, 255, 255)), (.45, (214, 218, 226)), (.55, (150, 156, 168)), (1, (226, 230, 238))]
GOLDS = [(0, GOLD_HI), (.45, GOLD), (.55, (214, 158, 52)), (1, GOLD_LO)]


# ── фоны (базовый размер 1080, потом увеличиваем) ────────────────────────────────────────────────────────────────────
def _grid():
    return np.mgrid[0:H, 0:W].astype(np.float32)


def _noise(seed, scale, octaves=4):
    """Плавный шум: сумма увеличенных случайных сеток (0..1)."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((H, W), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = max(2, int(W / scale * 2 ** o))
        g = Image.fromarray((rng.random((n, n)) * 255).astype(np.uint8), 'L').resize((W, H), Image.BICUBIC)
        acc += np.asarray(g, np.float32) / 255 * amp
        tot += amp
        amp *= .5
    return acc / tot


def _glow_blobs(bg, cols, k=.3):
    g = _grid()
    for (cx, cy, rad), col in cols:
        m = k * np.exp(-((g[1] - cx) ** 2 + (g[0] - cy) ** 2) / (2 * rad ** 2))
        bg += (np.array(col, np.float32) - bg) * m[..., None]
    return bg


def _vignette(bg, k=.35):
    g = _grid()
    return bg * (1 - k * np.clip(np.hypot(g[1] / W - .5, g[0] / H - .5) / .72, 0, 1) ** 2)[..., None]


def bg_neon(hc, ac):
    g = _grid()
    bg = np.full((H, W, 3), (6, 6, 12), np.float32)
    bg = _glow_blobs(bg, (((330, 300, 380), hc), ((760, 780, 380), ac)), .16)
    line = ((g[1] % 40 < 1.2) | (g[0] % 40 < 1.2)).astype(np.float32)
    bg += line[..., None] * np.array((40, 44, 70), np.float32) * .35
    return _vignette(bg, .5)


def bg_carbon(hc, ac):
    g = _grid()
    c = 10
    cell = ((g[1] // c + g[0] // c) % 2).astype(np.float32)
    tx = (g[1] % c) / c
    ty = (g[0] % c) / c
    sheen = np.where(cell > 0, np.sin(tx * np.pi), np.sin(ty * np.pi))
    v = 18 + 14 * sheen
    bg = np.repeat(v[..., None], 3, -1) * np.array((1, 1.02, 1.08), np.float32)
    bg = _glow_blobs(bg, (((330, 300, 420), hc), ((760, 780, 420), ac)), .14)
    diag = np.exp(-((g[1] * .7 - g[0] * .7 + 120) ** 2) / (2 * 160 ** 2)) * 18
    return _vignette(bg + diag[..., None], .45)


def bg_marble(hc, ac):
    n = _noise(7, 180, 5)
    t = np.sin((_grid()[1] * .004 + _grid()[0] * .007 + n * 9) * np.pi)
    vein = np.clip(1 - np.abs(t) * 10, 0, 1) ** 2
    fine = np.clip(1 - np.abs(np.sin((n * 23 + _grid()[0] * .003) * np.pi)) * 16, 0, 1) ** 2
    base = 12 + 10 * n
    bg = np.repeat(base[..., None], 3, -1)
    bg += (np.array((120, 120, 126), np.float32) * .45) * fine[..., None]
    bg += (np.array(GOLD, np.float32) - bg) * (vein * .55)[..., None]
    return _vignette(bg, .4)


def bg_ice(hc, ac):
    g = _grid()
    top, bot = np.array((236, 244, 251), np.float32), np.array((196, 216, 234), np.float32)
    t = (g[0] / H)[..., None]
    bg = top + (bot - top) * t
    n = _noise(3, 90, 4)
    bg += ((n - .5) * 18)[..., None]
    rng = np.random.default_rng(11)
    sc = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(sc)
    for _ in range(160):                                    # царапины от коньков
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        a, ln = rng.uniform(-.5, .5), rng.uniform(40, 220)
        d.line((x, y, x + ln * np.cos(a), y + ln * np.sin(a)), fill=int(rng.uniform(40, 120)), width=1)
    bg += (np.asarray(sc, np.float32) / 255 * 30)[..., None]
    return _glow_blobs(bg, (((330, 300, 420), hc), ((760, 780, 420), ac)), .10)


def bg_sport(hc, ac):
    g = _grid()
    bg = np.full((H, W, 3), (14, 15, 20), np.float32)
    band = ((g[1] + g[0] * .6) % 90 < 34).astype(np.float32)
    fade = np.clip(1 - np.abs(g[1] / W - .5) * 1.4, 0, 1)
    bg += (band * fade)[..., None] * 7
    bg = _glow_blobs(bg, (((300, 280, 360), hc), ((780, 800, 360), ac)), .22)
    return _vignette(bg, .4)


def _holo_field(h, w, phase=0.0, sat=.55, val=1.0):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    hue = ((x / w * .8 + y / h * .5) + phase + .08 * np.sin(x / w * 9 + y / h * 5)) % 1
    rgb = np.stack(np.vectorize(colorsys.hsv_to_rgb, otypes=[float, float, float])(hue[::4, ::4], sat, val), -1)
    img = Image.fromarray((rgb * 255).astype(np.uint8), 'RGB').resize((w, h), Image.BICUBIC)
    return np.asarray(img, np.float32)


def bg_holo(hc, ac):
    bg = np.full((H, W, 3), (12, 10, 26), np.float32)
    field = _holo_field(H, W, .6, .7, .5)
    g = _grid()
    k = .16 * np.exp(-((g[1] - 540) ** 2 + (g[0] - 540) ** 2) / (2 * 520 ** 2))
    bg += (field - bg) * k[..., None]
    bg = _glow_blobs(bg, (((330, 300, 400), hc), ((760, 780, 400), ac)), .14)
    return _vignette(bg, .45)


def bg_swiss(hc, ac):
    bg = np.full((H, W, 3), (241, 239, 233), np.float32)
    n = _noise(5, 60, 3)
    return bg + ((n - .5) * 8)[..., None]


# ── панели ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def _chamfer_mask(w, h, c):
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).polygon([(c, 0), (w, 0), (w, h - c), (w - c, h), (0, h), (0, c)], fill=255)
    return m


def _apply(pn, mask):
    pn = pn.convert('RGBA')
    pn.putalpha(mask)
    return pn


def panel(style, col, w, h, seed, ctr, fade):
    """Плитка панели в размере ×S (RGBA) и её маска."""
    bw, bh = w // S, h // S
    base = _panel(bw, bh, col, (ctr[0] * bw, ctr[1] * bh), seed, fade, dim=.5)
    r = 26 * S
    if style == 'neon':
        dark = _panel(bw, bh, _mix(col, -.78), (ctr[0] * bw, ctr[1] * bh), seed, fade, dim=.7)
        pn = dark.resize((w, h), Image.BICUBIC)
        return _apply(pn, _round_mask(w, h, r)), _round_mask(w, h, r)
    if style == 'carbon':
        a = np.asarray(base.resize((w // 3, h // 3), Image.BICUBIC), np.float32)
        rng = np.random.default_rng(seed)
        streak = np.repeat(rng.normal(0, 1, (a.shape[0], 1)), a.shape[1], 1)
        streak = np.asarray(Image.fromarray(((streak * 18) + 128).clip(0, 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(1)), np.float32) - 128
        a = np.clip(a * (1 + streak[..., None] / 260), 0, 255)
        pn = _gloss_panel(Image.fromarray(a.astype(np.uint8)).resize((w, h), Image.BICUBIC), 10 * S)
        return pn, _round_mask(w, h, 10 * S)
    if style == 'marble':
        mat = _panel(bw, bh, _mix(col, -.18), (ctr[0] * bw, ctr[1] * bh), seed, fade, dim=.62)
        mat = mat.filter(ImageFilter.GaussianBlur(1.5)).resize((w, h), Image.BICUBIC)
        return _apply(mat, _round_mask(w, h, 4 * S)), _round_mask(w, h, 4 * S)
    if style == 'ice':
        a = np.asarray(base.filter(ImageFilter.GaussianBlur(1)).resize((w, h), Image.BICUBIC), np.float32)
        y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        a = a + (255 - a) * (.28 * np.clip(1 - y * 1.6, 0, 1) + .06)
        return _apply(Image.fromarray(a.astype(np.uint8)), _round_mask(w, h, r)), _round_mask(w, h, r)
    if style == 'sport':
        a = np.asarray(base.resize((w, h), Image.BICUBIC), np.float32)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        stripe = (((xx - yy * .55) / S) % 120 < 18).astype(np.float32) * .10
        a = a + (255 - a) * stripe[..., None]
        m = _chamfer_mask(w, h, 70 * S)
        return _apply(Image.fromarray(a.astype(np.uint8)), m), m
    if style == 'holo':
        a = np.asarray(base.resize((w, h), Image.BICUBIC), np.float32)
        field = _holo_field(h, w, seed * .07, .55, 1.0)
        a = a * .62 + field * .38
        pn = _gloss_panel(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)), r)
        return pn, _round_mask(w, h, r)
    if style == 'swiss':
        flat = Image.new('RGB', (w, h), col)
        return _apply(flat, Image.new('L', (w, h), 255)), Image.new('L', (w, h), 255)
    raise KeyError(style)


def _frame(img, style, box, mask, col):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    edge = ImageChops_edge(mask, {'neon': 3, 'carbon': 3, 'marble': 2, 'ice': 4, 'sport': 3, 'holo': 3,
                                  'swiss': 0}[style] * S)
    if style == 'swiss' or edge is None:
        return
    if style == 'neon':
        c = _mix(col, .25)
        for blur, al in ((26 * S, 200), (9 * S, 230), (0, 255)):
            t = Image.new('RGBA', (w, h), c + (0,))
            e = edge.filter(ImageFilter.GaussianBlur(blur)) if blur else edge
            t.putalpha(e.point(lambda v, al=al: min(255, v * al // 255 * (3 if blur else 1))))
            img.alpha_composite(t, (x0, y0))
        return
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = np.clip((xx / w + yy / h) / 2, 0, 1)
    if style in ('carbon',):
        st = [(0, (255, 255, 255)), (.3, (170, 176, 186)), (.6, (236, 240, 246)), (1, (110, 116, 128))]
    elif style == 'marble':
        st = [(0, GOLD_HI), (.5, GOLD), (1, GOLD_LO)]
    elif style == 'ice':
        st = [(0, (255, 255, 255)), (1, (226, 238, 248))]
    elif style == 'sport':
        st = [(0, (255, 255, 255)), (1, (255, 255, 255))]
    else:  # holo
        arr = _holo_field(h, w, .3, .55, 1.0)
        tile = Image.fromarray(arr.astype(np.uint8), 'RGB').convert('RGBA')
        tile.putalpha(edge)
        img.alpha_composite(tile, (x0, y0))
        return
    arr = np.stack([np.interp(t, [p for p, _ in st], [c[i] for _, c in st]) for i in range(3)], -1)
    tile = Image.fromarray(arr.astype(np.uint8), 'RGB').convert('RGBA')
    tile.putalpha(edge)
    img.alpha_composite(tile, (x0, y0))
    if style == 'marble':                                       # вторая тонкая золотая линия внутри
        inner = ImageChops_edge(mask.resize((w - 24 * S, h - 24 * S)), max(1, S))
        t2 = Image.new('RGBA', inner.size, GOLD + (0,))
        t2.putalpha(inner.point(lambda v: v * 200 // 255))
        img.alpha_composite(t2, (x0 + 12 * S, y0 + 12 * S))


def ImageChops_edge(mask, wpx):
    """Кромка маски толщиной wpx (внутрь)."""
    if wpx <= 0:
        return None
    pad = wpx + 2                                            # снаружи маски — пусто, иначе прямые края не «съедаются»
    big = ImageOps.expand(mask, pad, 0)
    er = big.filter(ImageFilter.MinFilter(wpx * 2 + 1)).crop((pad, pad, pad + mask.width, pad + mask.height))
    a = np.asarray(mask, np.int16) - np.asarray(er, np.int16)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'L')


# ── буквы, цифры, плашки ───────────────────────────────────────────────────────────────────────────────────────────
def _holo_stops(k=0):
    hues = [.55, .8, .02, .15, .45]
    cols = [tuple(int(v * 255) for v in colorsys.hsv_to_rgb((h + k) % 1, .42, 1)) for h in hues]
    return [(i / (len(cols) - 1), c) for i, c in enumerate(cols)]


def _flat(c):
    return [(0, c), (1, c)]


def _abbr_stops(style, col):
    return {'neon': [(0, (255, 255, 255)), (.55, _mix(col, .55)), (1, _mix(col, .2))],
            'carbon': _glass(col),
            'marble': GOLDS,
            'ice': _flat(_mix(col, -.25)),
            'sport': _glass(col),
            'holo': _holo_stops(.1),
            'swiss': _flat((18, 18, 20))}[style]


def _ink_tile(text, f, stops, stroke=0, stroke_fill=None, shear=0.0):
    l, t, r, b = f.getbbox(text)
    pad = int(f.size * .3)
    w, h = r - l + 2 * pad, b - t + 2 * pad
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).text((pad - l, pad - t), text, font=f, fill=255)
    col = np.broadcast_to(_vgrad(h, [(0, stops[0][1])] + [(pad / h + (h - 2 * pad) / h * p, c) for p, c in stops]
                                 + [(1, stops[-1][1])]), (h, w, 3)).astype(np.uint8)
    tile = Image.fromarray(np.ascontiguousarray(col), 'RGB').convert('RGBA')
    tile.putalpha(m)
    if stroke:
        sm = m.filter(ImageFilter.MaxFilter(stroke * 2 + 1))
        st = Image.new('RGBA', (w, h), stroke_fill + (0,))
        st.putalpha(sm)
        st.alpha_composite(tile)
        tile = st
    if shear:
        tile = tile.transform((w + int(h * abs(shear)), h), Image.AFFINE, (1, shear, -h * abs(shear) if shear < 0 else 0,
                                                                          0, 1, 0), Image.BICUBIC)
    return tile, pad


def _put_text(img, style, x, y, text, f, stops, anchor='l', glow=None, shadow=True, strength=1.0):
    if style == 'sport':
        tile, pad = _ink_tile(text, f, stops, stroke=max(2, f.size // 40), stroke_fill=(255, 255, 255), shear=-.18)
        ox = {'l': x - pad, 'r': x - tile.width + pad, 'm': x - tile.width / 2}[anchor]
        sh = Image.new('RGBA', tile.size, (0, 0, 0, 0))
        sh.putalpha(tile.getchannel('A').point(lambda v: v * 150 // 255).filter(ImageFilter.GaussianBlur(f.size // 16)))
        img.alpha_composite(sh, (int(ox + f.size * .04), int(y - pad + f.size * .06)))
        img.alpha_composite(tile, (int(ox), int(y - pad)))
        return
    if style == 'neon' and glow:
        tile, pad = _ink_tile(text, f, [(0, glow), (1, glow)])
        ox = {'l': x - pad, 'r': x - tile.width + pad, 'm': x - tile.width / 2}[anchor]
        for blur, mult in ((f.size // 5, 2.2 * strength), (f.size // 14, 1.4 * strength)):
            g = tile.copy()
            g.putalpha(tile.getchannel('A').filter(ImageFilter.GaussianBlur(blur)).point(lambda v, m=mult: min(255, int(v * m))))
            img.alpha_composite(g, (int(ox), int(y - pad)))
        _grad_text(img, x, y, text, f, stops, anchor, shadow=0)
        return
    sh = 0 if style in ('swiss', 'ice') else (140 if shadow else 0)
    _grad_text(img, x, y, text, f, stops, anchor, shadow=sh, glow=glow if style in ('carbon', 'holo') else None)


def _pill(img, style, box, text, f, acc):
    x0, y0, x1, y1 = (int(v) for v in box)
    w, h = x1 - x0, y1 - y0
    r = {'swiss': 0, 'sport': 0, 'marble': 4 * S}.get(style, int(h * .3))
    mask = _chamfer_mask(w, h, int(h * .32)) if style == 'sport' else _round_mask(w, h, r) if r else Image.new('L', (w, h), 255)
    if style not in ('swiss', 'ice'):
        sh = Image.new('RGBA', (w + 60 * S, h + 60 * S), (0, 0, 0, 0))
        sh.paste(Image.new('RGBA', (w, h), (0, 0, 0, 150)), (30 * S, 36 * S), mask)
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9 * S)), (x0 - 30 * S, y0 - 30 * S))
    if style == 'neon':
        fill, txt = np.zeros((h, w, 3), np.float32) + np.array((10, 10, 18), np.float32), _mix(acc, .2)
    elif style == 'carbon':
        fill, txt = np.broadcast_to(_vgrad(h, SILVER), (h, w, 3)), (20, 22, 28)
    elif style in ('marble',):
        fill, txt = np.broadcast_to(_vgrad(h, GOLDS), (h, w, 3)), (28, 20, 6)
    elif style == 'ice':
        fill, txt = np.zeros((h, w, 3), np.float32) + np.array((16, 38, 78), np.float32), (255, 255, 255)
    elif style == 'sport':
        fill, txt = np.broadcast_to(_vgrad(h, [(0, _mix(acc, .3)), (1, _mix(acc, -.15))]), (h, w, 3)), (20, 16, 8)
    elif style == 'holo':
        fill, txt = _holo_field(h, w, .2, .45, 1.0), (24, 20, 40)
    else:  # swiss
        fill, txt = np.zeros((h, w, 3), np.float32) + 18, (255, 255, 255)
    tile = Image.fromarray(np.ascontiguousarray(fill).astype(np.uint8), 'RGB').convert('RGBA')
    tile.putalpha(mask)
    img.alpha_composite(tile, (x0, y0))
    if style == 'neon':
        e = ImageChops_edge(mask, 2 * S)
        for blur in (8 * S, 0):
            t = Image.new('RGBA', (w, h), acc + (0,))
            t.putalpha(e.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, v * 3)) if blur else e)
            img.alpha_composite(t, (x0, y0))
    ImageDraw.Draw(img).text(((x0 + x1) / 2, (y0 + y1) / 2 + 1 * S), text, font=f, fill=txt, anchor='mm')


# ── сборка ─────────────────────────────────────────────────────────────────────────────────────────────────────────
BGS = {'neon': bg_neon, 'carbon': bg_carbon, 'marble': bg_marble, 'ice': bg_ice, 'sport': bg_sport, 'holo': bg_holo,
       'swiss': bg_swiss}
LIGHT = ('ice', 'swiss')


def render(home, away, path, style='neon', date='', time='', odds=None, league='KHL', tz='время московское',
           fade=('down', 'up')):
    if league == 'NHL':
        nhl.register()
    hn, hc, _, ha, hs = _team(home, league)
    an, ac, ac2, aa, as_ = _team(away, league)
    ac = _distinct(hc, ac, ac2)
    acc = poster.ACC if league == 'KHL' else nhl.ICE
    light = style in LIGHT
    ink = (16, 32, 66) if style == 'ice' else (18, 18, 20) if style == 'swiss' else (245, 245, 245)
    sub = (70, 86, 112) if style == 'ice' else (90, 88, 84) if style == 'swiss' else (196, 194, 202)

    bg = BGS[style](hc, ac)
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), 'RGB').resize((W * S, H * S), Image.BICUBIC).convert('RGBA')
    d = ImageDraw.Draw(img)

    if style == 'swiss':                                         # сетка-линейка
        for x in (100, 460, 620, 980):
            d.line((x * S, 0, x * S, H * S), fill=(205, 202, 194), width=max(1, S // 2))
        for y in (26, 408, 672, 1054):
            d.line((0, y * S, W * S, y * S), fill=(205, 202, 194), width=max(1, S // 2))

    for (x0, y0, x1, y1), col, emb, seed, ctr, fd in ((P1, hc, hn, 11, (.62, .42), fade[0]),
                                                       (P2, ac, an, 23, (.40, .55), fade[1])):
        w, h = (x1 - x0) * S, (y1 - y0) * S
        tile, mask = panel(style, col, w, h, seed, ctr, fd)
        if style not in ('swiss',):
            sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
            sh.paste(Image.new('RGBA', (w, h), (0, 0, 0, 110 if light else 175)),
                     ((x0 + 18) * S, (y0 + 30) * S), mask)
            img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(34 * S)))
        img.alpha_composite(tile, (x0 * S, y0 * S))
        _frame(img, style, (x0 * S, y0 * S, x1 * S, y1 * S), mask, col)
        em = _emblem_gloss(emb, 380 * S) if style not in ('swiss',) else poster._emblem(emb, 380 * S)
        cx, cy = (x0 + x1) / 2 * S, ((y0 + y1) / 2 + 6) * S
        if style == 'neon':
            gl = Image.new('RGBA', img.size, (0, 0, 0, 0))
            gl.paste(Image.new('RGBA', em.size, _mix(col, .3) + (210,)), (int(cx - em.width / 2), int(cy - em.height / 2)),
                     em.getchannel('A'))
            img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(40 * S)))
        elif style != 'swiss':
            es = Image.new('RGBA', img.size, (0, 0, 0, 0))
            es.paste(Image.new('RGBA', em.size, _mix(col, -.7) + (170,)),
                     (int(cx - em.width / 2 + 12 * S), int(cy - em.height / 2 + 26 * S)), em.getchannel('A'))
            img.alpha_composite(es.filter(ImageFilter.GaussianBlur(28 * S)))
        img.alpha_composite(em, (int(cx - em.width / 2), int(cy - em.height / 2)))

    # аббревиатуры
    AB = 'AlumniSans[wght].ttf'
    fa = min((_fit(t, 330 * S, 150 * S, 900, AB) for t in (ha, aa)), key=lambda f: f.size)
    if style == 'swiss':
        sw = lambda c: _flat((18, 18, 20) if _lum(c) > 150 else c)      # светлый клубный цвет на бумаге не читается
        _put_text(img, style, 684 * S, 36 * S, ha, fa, sw(hc), 'l')
        _put_text(img, style, 1030 * S, 241 * S, aa, fa, sw(ac), 'r')
    else:
        _put_text(img, style, 684 * S, 36 * S, ha, fa, _abbr_stops(style, _mix(hc, .04)), 'l', glow=hc)
        _put_text(img, style, 1030 * S, 241 * S, aa, fa, _abbr_stops(style, _mix(ac, .04)), 'r', glow=ac)
    fv = brand_kit.font('Oswald[wght].ttf', 40 * S, 600)
    vb = fv.getbbox('vs')
    vs_stops = {'neon': _flat((255, 255, 255)), 'carbon': SILVER, 'marble': GOLDS, 'ice': _flat(ink),
                'sport': _flat((255, 255, 255)), 'holo': _holo_stops(.4), 'swiss': _flat(ink)}[style]
    _put_text(img, style, 690 * S, 218 * S - (vb[3] - vb[1]) // 2, 'vs', fv, vs_stops, 'l', glow=acc)

    fs = brand_kit.font('Manrope[wght].ttf', 17 * S, 600)
    vcol = lambda c: (_mix(c, -.35) if light else _mix(c, .2)) + (255,)
    _vertical(img, '#' + hs, 50 * S, 336 * S, fs, vcol(hc), ccw=True)
    _vertical(img, '#' + as_, 1030 * S, 744 * S, fs, vcol(ac), ccw=False)

    # дата, время, линия
    X0, X1 = 130, 430
    cxm = (X0 + X1) / 2 * S
    dy = 0 if odds else 90
    date_stops = {'neon': _flat(_mix(acc, .2)), 'carbon': SILVER, 'marble': GOLDS, 'ice': _flat((40, 92, 160)),
                  'sport': _flat(acc), 'holo': _holo_stops(.25), 'swiss': _flat((200, 30, 40))}[style]
    time_stops = {'neon': _flat((255, 255, 255)), 'carbon': SILVER, 'marble': SILVER, 'ice': _flat(ink),
                  'sport': _flat((255, 255, 255)), 'holo': SILVER, 'swiss': _flat(ink)}[style]
    if date:
        fdt = _fit(date.upper(), (X1 - X0) * S, 30 * S, 600)
        _put_text(img, style, cxm, (711 + dy) * S, date.upper(), fdt, date_stops, 'm', glow=acc, shadow=False,
                  strength=.45)
    if time:
        ft = _fit(time, (X1 - X0) * S, 74 * S, 700)
        _put_text(img, style, cxm, (763 + dy) * S, time, ft, time_stops, 'm', glow=acc, strength=.4)   # цифры читаемы
    fz = brand_kit.font('Manrope[wght].ttf', 19 * S, 600)
    d = ImageDraw.Draw(img)
    d.text((cxm, (860 + dy) * S), tz, font=fz, fill=sub, anchor='mm')
    if odds:
        line_c = {'marble': GOLD, 'carbon': (200, 204, 212), 'ice': (40, 92, 160), 'swiss': (18, 18, 20)}.get(style, acc)
        _hairline(img, cxm, 884 * S, 150 * S, line_c)
        fo = brand_kit.font('Oswald[wght].ttf', 30 * S, 600)
        fl = brand_kit.font('Manrope[wght].ttf', 15 * S, 700)
        pw, gap, y0 = 88, 12, 930
        x = cxm / S - (3 * pw + 2 * gap) / 2
        for lab, v in zip(('П1', 'Х', 'П2'), odds):
            d.text(((x + pw / 2) * S, (y0 - 10) * S), lab, font=fl, fill=sub, anchor='md')
            _pill(img, style, (x * S, y0 * S, (x + pw) * S, (y0 + 46) * S), '%.2f' % v, fo, acc)
            x += pw + gap
        fn = brand_kit.font('Manrope[wght].ttf', 14 * S, 700)
        d.text((cxm, 1000 * S), 'ОСНОВНОЕ ВРЕМЯ', font=fn, fill=sub, anchor='mm')

    # марка канала
    fm = brand_kit.font('Oswald[wght].ttf', 24 * S, 700)
    tag = 'KXL' if league == 'KHL' else 'NHL'
    wj, wt = fm.getlength('JARVIS'), fm.getlength(tag)
    gx, bar = 14 * S, 3 * S
    xr = cxm + (wj + gx * 2 + bar + wt) / 2
    yb = 1056 * S
    tagc = {'swiss': (200, 30, 40), 'ice': (40, 92, 160), 'carbon': (210, 214, 222)}.get(style, GOLD if league == 'KHL' else acc)
    d.text((xr, yb), tag, font=fm, fill=tagc, anchor='rs')
    d.rectangle((xr - wt - gx - bar, yb - 22 * S, xr - wt - gx, yb), fill=tagc)
    d.text((xr - wt - 2 * gx - bar, yb), 'JARVIS', font=fm, fill=ink, anchor='rs')

    a = np.asarray(img.convert('RGB')).astype(np.int16)
    a += np.random.default_rng(5).integers(-2, 3, a.shape[:2], dtype=np.int16)[..., None]
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').save(path, quality=94, optimize=True)
    return path


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


if __name__ == '__main__':
    import sys
    for st in (sys.argv[1:] or STYLES):
        print(render('Северсталь', 'СКА', 'out/vs_styles/vs_%s.jpg' % st, style=st, date='13 октября', time='19:00',
                     odds=(2.60, 4.20, 2.35)))
