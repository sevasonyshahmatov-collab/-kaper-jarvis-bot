"""Послематчевые баннеры — 6 шаблонов (14.10.2026, пробы для владельца). Портрет 1080×1350 × quality.S.

    import post6
    m = dict(home='ЦСКА', away='Динамо Москва', sh=1, sa=0, mark='', pick='ПОБЕДА ЦСКА', odds=1.91, hit=True,
             date='среда, 14 октября')
    post6.render(m, 'out/p.jpg', style='stamp')      # stamp | jumbo | check | medal | neon | paper

  stamp  «Купон»   — бумажный купон на столе, сверху резиновый штамп «ЗАШЁЛ» / «НЕ ЗАШЁЛ»
  jumbo  «Табло»   — светодиодное табло арены: счёт точками, прогноз бегущей строкой, вердикт зелёным/красным
  check  «Галочка» — светлый минимализм: огромная галочка (или крест) в круге, крупный счёт, сетка
  medal  «Медаль»  — тёмный мрамор, золотая медаль на ленте в цветах клуба с вердиктом и кэфом
  neon   «Неон»    — кирпичная стена и неоновые вывески: счёт, прогноз, вердикт
  paper  «Газета»  — первая полоса: шапка, заголовок, эмблемы растром, заметка о матче
mark: '' | 'ОТ' | 'Б'; hit: True | False | None (возврат).
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

import bkit as K
from bkit import S, W, H

GREEN, RED, GOLD = (46, 196, 110), (226, 56, 64), (232, 186, 82)


def _verdict(hit):
    return {True: 'ЗАШЁЛ', False: 'НЕ ЗАШЁЛ'}.get(hit, 'ВОЗВРАТ')


def _vcol(hit):
    return {True: GREEN, False: RED}.get(hit, (150, 150, 160))


def _score(m):
    return '%d:%d' % (m['sh'], m['sa'])


def _mark(m):
    return {'ОТ': 'ОВЕРТАЙМ', 'Б': 'БУЛЛИТЫ'}.get(m.get('mark') or '', 'ОСНОВНОЕ ВРЕМЯ')


def _tag(m):
    return 'NHL' if K.league_of(m['home'], m['away']) == 'NHL' else 'KXL'


def _brand(d, x, y, col=(255, 255, 255), acc=GOLD, size=30, anchor='mm'):
    f = K.font('mont', size, 900)
    a, b = 'JARVIS', ' | ' + _tag_cache[0]
    w = f.getlength(a + b) / S
    x0 = x - w / 2 if anchor == 'mm' else x
    K.text(d, (x0, y), a, f, col, 'lm')
    K.text(d, (x0 + f.getlength(a) / S, y), b, f, acc, 'lm')


_tag_cache = ['KXL']


# ── 1. Купон со штампом ─────────────────────────────────────────────────────────────────────────────────────────────
def stamp(m, img):
    d = ImageDraw.Draw(img)
    img.alpha_composite(K.vgrad(W, H, [(0, (44, 34, 28)), (1, (22, 16, 12))]))
    for i in range(0, H, 46):                                     # доски стола
        d.line((0, i * S, W * S, i * S), fill=(30, 22, 18, 255), width=max(1, S))
    sw, sh = 820, 1160
    slip = Image.new('RGBA', (sw * S, sh * S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(slip)
    sd.rectangle((0, 24 * S, sw * S, sh * S), fill=(246, 242, 230, 255))
    for x in range(0, sw, 24):                                    # рваный верх
        sd.polygon([(x * S, 24 * S), ((x + 12) * S, 6 * S), ((x + 24) * S, 24 * S)], fill=(246, 242, 230, 255))
    ink = (40, 38, 44)
    mono = lambda s, w=700: K.font('mono', s, w)
    y = 90
    K.text(sd, (sw / 2, y), 'J A R V I S', mono(54, 800), ink)
    K.text(sd, (sw / 2, y + 56), 'КУПОН · ИТОГ ПРОГНОЗА', mono(26), ink)
    K.text(sd, (sw / 2, y + 96), m['date'].upper(), mono(24, 500), ink)
    for yy in (y + 140, y + 520, y + 760):
        K.text(sd, (sw / 2, yy), '-' * 40, mono(24, 500), ink)
    for j, t in enumerate((m['home'], m['away'])):
        e = K.emblem(t, 120)
        g = ImageOps.grayscale(e.convert('RGB')).convert('RGBA')
        g.putalpha(e.getchannel('A'))
        slip.alpha_composite(g, (int((sw / 2 + (-170 if j == 0 else 170)) * S - g.width / 2), int((y + 250) * S - g.height / 2)))
    K.text(sd, (sw / 2, y + 250), _score(m), K.font('mono', 96, 800), ink)
    K.text(sd, (sw / 2, y + 380), '%s — %s' % (K.short(m['home']).upper(), K.short(m['away']).upper()),
           K.fit('%s — %s' % (K.short(m['home']).upper(), K.short(m['away']).upper()), 'mono', 38, sw - 80, 800), ink)
    K.text(sd, (sw / 2, y + 440), _mark(m), mono(26, 500), ink)
    K.text(sd, (60, y + 590), 'СТАВКА', mono(28, 500), ink, 'lm')
    K.text(sd, (sw - 60, y + 590), m['pick'], K.fit(m['pick'], 'mono', 34, sw - 300, 800), ink, 'rm')
    K.text(sd, (60, y + 660), 'КЭФ', mono(28, 500), ink, 'lm')
    K.text(sd, (sw - 60, y + 660), K.fmt_odds(m.get('odds')) or '—', mono(40, 800), ink, 'rm')
    rnd = np.random.default_rng(4)
    x = 140
    while x < sw - 140:                                           # штрихкод
        w = int(rnd.choice([3, 3, 5, 8]))
        sd.rectangle((x * S, (y + 975) * S, (x + w) * S, (y + 1030) * S), fill=ink + (255,))
        x += w + int(rnd.choice([3, 5, 6]))
    K.text(sd, (sw / 2, y + 1055), '@jarvibet', mono(28, 700), ink)
    # штамп
    col = _vcol(m.get('hit'))
    st = Image.new('RGBA', (700 * S, 260 * S), (0, 0, 0, 0))
    std = ImageDraw.Draw(st)
    std.rounded_rectangle((10 * S, 10 * S, 690 * S, 250 * S), 26 * S, outline=col + (255,), width=12 * S)
    std.rounded_rectangle((34 * S, 34 * S, 666 * S, 226 * S), 16 * S, outline=col + (255,), width=4 * S)
    K.text(std, (350, 130), _verdict(m.get('hit')), K.fit(_verdict(m.get('hit')), 'russo', 120, 580), col + (255,))
    grit = Image.fromarray((np.random.default_rng(8).random((st.height // 4, st.width // 4)) > 0.18).astype(np.uint8) * 255, 'L')
    grit = grit.resize(st.size).filter(ImageFilter.GaussianBlur(S))
    st.putalpha(Image.fromarray((np.asarray(st.getchannel('A'), np.float32) * np.asarray(grit, np.float32) / 255 * 0.9)
                                .astype(np.uint8)))
    st = st.rotate(14, expand=True, resample=Image.BICUBIC)
    slip.alpha_composite(st, (int((sw / 2 + 40) * S - st.width / 2), int((y + 870) * S - st.height / 2)))
    slip = slip.rotate(-2.2, expand=True, resample=Image.BICUBIC)
    sh_ = slip.getchannel('A').filter(ImageFilter.GaussianBlur(20 * S)).point(lambda v: v * 160 // 255)
    shl = Image.new('RGBA', slip.size, (0, 0, 0, 0))
    shl.putalpha(sh_)
    img.alpha_composite(shl, (int(W * S / 2 - slip.width / 2 + 12 * S), int(H * S / 2 - slip.height / 2 + 30 * S)))
    img.alpha_composite(slip, (int(W * S / 2 - slip.width / 2), int(H * S / 2 - slip.height / 2)))


# ── 2. Табло арены (светодиоды) ─────────────────────────────────────────────────────────────────────────────────────
def _led(s, height, col, font_name='robc', wght=800, cell=7, glow=True):
    """Текст точками светодиодов: высота строки height (базовые px), шаг точки cell."""
    rows = max(6, int(height / cell))
    f = K.font(font_name, 10, wght)                               # рисуем в сетке точек
    fs = int(rows * 1.25)
    fnt = __import__('brand_kit').font(K.FONTS[font_name], fs, wght)
    w = int(fnt.getlength(s)) + 4
    m = Image.new('L', (w, rows + 4), 0)
    ImageDraw.Draw(m).text((2, (rows + 4) / 2), s, font=fnt, fill=255, anchor='lm')
    a = np.asarray(m) > 110
    c = cell * S
    tile = Image.new('L', (c, c), 0)
    ImageDraw.Draw(tile).ellipse((c * 0.12, c * 0.12, c * 0.88, c * 0.88), fill=255)
    tl = np.asarray(tile)
    big = np.kron(a.astype(np.uint8), np.ones((1, 1), np.uint8))
    on = np.kron(big, tl // 255) * 255
    off = np.kron(np.ones_like(big), tl // 255) * 34
    al = np.maximum(on, off).astype(np.uint8)
    rgb = np.zeros(al.shape + (3,), np.uint8)
    rgb[on > 0] = col
    rgb[(on == 0) & (off > 0)] = (40, 40, 44)
    im = Image.fromarray(rgb, 'RGB').convert('RGBA')
    im.putalpha(Image.fromarray(al, 'L'))
    if glow:
        g = Image.new('RGBA', im.size, tuple(col) + (0,))
        g.putalpha(Image.fromarray(on.astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(c * 0.9)))
        g.alpha_composite(im)
        im = g
    return im


def jumbo(m, img):
    d = ImageDraw.Draw(img)
    img.alpha_composite(K.vgrad(W, H, [(0, (14, 16, 22)), (1, (4, 4, 6))]))
    K.glow_blob(img, W / 2, 500, 560, (60, 70, 110), 0.35)
    AMB = (255, 176, 40)
    for box in ((50, 120, 1030, 760), (50, 800, 1030, 1260)):
        K.shadow(img, box, 30, 30, 200)
        K.rrect(d, box, 30, fill=(8, 8, 10, 255), outline=(70, 74, 86), width=6)
    _brand(d, W / 2, 175, size=30)
    K.put(img, _led('ФИНАЛ', 44, AMB, cell=4), W / 2, 250)
    for j, t in enumerate((m['home'], m['away'])):
        x = 210 if j == 0 else W - 210
        K.put(img, K.emblem(t, 190), x, 420)
        K.put(img, _led(K.abbr(t), 60, (230, 232, 240), cell=5), x, 600)
    K.put(img, _led(_score(m), 230, AMB, cell=9), W / 2, 450)
    K.put(img, _led(_mark(m), 36, (200, 200, 210), cell=4), W / 2, 690)
    K.put(img, _led('ПРОГНОЗ', 36, (200, 200, 210), cell=4), W / 2, 870)
    pk = '%s  %s' % (m['pick'], K.fmt_k(m.get('odds')))
    K.put(img, _led(pk, 64, AMB, cell=5) if len(pk) < 22 else _led(pk, 50, AMB, cell=4), W / 2, 975)
    col = _vcol(m.get('hit'))
    K.put(img, _led(_verdict(m.get('hit')), 150, col, cell=9), W / 2, 1140)
    K.text(d, (W / 2, 1305), m['date'].upper() + ' · @JARVIBET', K.font('mont', 24, 800), (150, 154, 168))


# ── 3. Галочка (светлый минимализм) ─────────────────────────────────────────────────────────────────────────────────
def check(m, img):
    d = ImageDraw.Draw(img)
    img.alpha_composite(K.vgrad(W, H, [(0, (244, 242, 236)), (1, (232, 229, 221))]))
    for x in (60, 540, 1020):
        d.line((x * S, 0, x * S, H * S), fill=(214, 210, 200), width=max(1, S // 2))
    for y in (110, 700, 1240):
        d.line((0, y * S, W * S, y * S), fill=(214, 210, 200), width=max(1, S // 2))
    ink = (18, 18, 20)
    _brand(d, 60, 70, col=ink, acc=(200, 30, 40), anchor='lm')
    K.text(d, (1020, 70), m['date'].upper(), K.font('mont', 24, 800), (90, 88, 84), 'rm')
    col = _vcol(m.get('hit'))
    cx, cy, r = 760, 400, 250
    d.ellipse(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S), fill=col + (255,))
    if m.get('hit'):
        pts = [(cx - 120, cy + 5), (cx - 35, cy + 95), (cx + 135, cy - 95)]
        d.line([(x * S, y * S) for x, y in pts], fill=(255, 255, 255), width=44 * S, joint='curve')
    else:
        for a, b in (((cx - 100, cy - 100), (cx + 100, cy + 100)), ((cx + 100, cy - 100), (cx - 100, cy + 100))):
            d.line((a[0] * S, a[1] * S, b[0] * S, b[1] * S), fill=(255, 255, 255), width=44 * S)
    K.text(d, (60, 200), 'ИТОГ', K.font('mont', 30, 900), (90, 88, 84), 'lm')
    K.text(d, (52, 400), _score(m), K.font('alumni', 330, 900), ink, 'lm')
    for j, t in enumerate((m['home'], m['away'])):
        y = 790 + j * 120
        K.put(img, K.emblem(t, 92), 110, y)
        K.text(d, (180, y), K.short(t).upper(), K.fit(K.short(t).upper(), 'osw', 64, 600, 700), ink, 'lm')
        if (m['sh'] > m['sa']) == (j == 0):
            K.text(d, (1020, y), 'ПОБЕДА', K.font('mont', 26, 900), col if m.get('hit') else ink, 'rm')
    K.text(d, (60, 1060), 'ПРОГНОЗ', K.font('mont', 26, 900), (90, 88, 84), 'lm')
    K.text(d, (60, 1130), m['pick'], K.fit(m['pick'], 'osw', 72, 700, 700), ink, 'lm')
    K.text(d, (1020, 1130), K.fmt_odds(m.get('odds')), K.font('osw', 72, 700), (200, 30, 40), 'rm')
    K.text(d, (60, 1290), _verdict(m.get('hit')) + ' · ' + _mark(m), K.font('mont', 26, 900), col, 'lm')
    K.text(d, (1020, 1290), '@jarvibet', K.font('mont', 26, 900), ink, 'rm')


# ── 4. Медаль ───────────────────────────────────────────────────────────────────────────────────────────────────────
def _metal_disc(r, stops):
    n = int(2 * r * S)
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    dx, dy = (x - n / 2) / (n / 2), (y - n / 2) / (n / 2)
    dd = np.hypot(dx, dy)
    v = 0.55 - 0.35 * dy - 0.15 * dx + 0.12 * np.cos(np.arctan2(dy, dx) * 6) * (dd > 0.86)
    v = np.where(dd > 0.84, 1 - v * 0.8, v)                      # обод светом наоборот
    cols = np.stack([np.interp(np.clip(v, 0, 1), [p for p, _ in stops], [c[i] for _, c in stops]) for i in range(3)], -1)
    a = np.clip((1 - dd) * n / 2, 0, 1) * 255
    return Image.fromarray(np.dstack([cols, a]).astype(np.uint8), 'RGBA')


def medal(m, img):
    d = ImageDraw.Draw(img)
    base = np.full((H, W, 3), 14, np.float32)
    rnd = np.random.default_rng(7)
    n = np.asarray(Image.fromarray((rnd.random((24, 20)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
    vein = np.clip(1 - np.abs(np.sin((np.mgrid[0:H, 0:W][1] * .004 + np.mgrid[0:H, 0:W][0] * .006 + n * 7) * np.pi)) * 14, 0, 1)
    base += vein[..., None] * np.array((150, 120, 60), np.float32) * 0.45 + n[..., None] * 16
    img.alpha_composite(Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).resize((W * S, H * S), Image.BICUBIC).convert('RGBA'))
    K.glow_blob(img, W / 2, 700, 520, (120, 90, 30), 0.4)
    _brand(d, W / 2, 80)
    K.text(d, (W / 2, 125), m['date'].upper(), K.font('mont', 22, 800), (190, 180, 160))
    hit = m.get('hit')
    stops = ([(0, (110, 70, 14)), (.4, (214, 162, 64)), (.7, (250, 214, 130)), (1, (255, 246, 210))] if hit else
             [(0, (60, 62, 68)), (.5, (150, 154, 162)), (1, (230, 232, 238))])
    c1, c2 = K.color(m['home'] if m['sh'] >= m['sa'] else m['away']), K.color2(m['home'] if m['sh'] >= m['sa'] else m['away'])
    for off, col in ((-70, c1), (70, c2)):                        # лента
        rib = [(W / 2 + off - 60, 150), (W / 2 + off + 60, 150), (W / 2 + off * 0.2 + 60, 470), (W / 2 + off * 0.2 - 60, 470)]
        d.polygon([(x * S, y * S) for x, y in rib], fill=col + (255,))
    disc = _metal_disc(270, stops)
    img.alpha_composite(disc, (int((W / 2 - 270) * S), int((700 - 270) * S)))
    inner = _metal_disc(205, list(reversed([(1 - p, c) for p, c in stops])))
    img.alpha_composite(inner, (int((W / 2 - 205) * S), int((700 - 205) * S)))
    ink = (60, 40, 8) if hit else (40, 42, 48)
    K.text(d, (W / 2, 610), 'ПРОГНОЗ', K.font('mont', 26, 900), ink)
    K.text(d, (W / 2, 700), _verdict(hit), K.fit(_verdict(hit), 'osw', 110, 340, 700), ink)
    K.text(d, (W / 2, 800), 'КЭФ ' + (K.fmt_odds(m.get('odds')) or '—'), K.font('osw', 54, 700), ink)
    y = 1070
    for j, t in enumerate((m['home'], m['away'])):
        K.put(img, K.emblem(t, 150, sticker=True), W / 2 + (-330 if j == 0 else 330), y)
    K.text(d, (W / 2, y - 10), _score(m), K.font('osw', 130, 700), (250, 236, 200))
    K.text(d, (W / 2, y + 85), _mark(m), K.font('mont', 24, 800), (200, 190, 170))
    K.text(d, (W / 2, 1220), m['pick'], K.fit(m['pick'], 'osw', 60, 900, 700), (250, 236, 200))
    K.text(d, (W / 2, 1300), '@jarvibet', K.font('mont', 26, 900), (200, 170, 100))


# ── 5. Неон ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def neon(m, img):
    d = ImageDraw.Draw(img)
    img.alpha_composite(K.vgrad(W, H, [(0, (26, 16, 22)), (1, (12, 8, 12))]))
    rnd = np.random.default_rng(2)
    bw, bh = 120, 46
    for r_ in range(0, H // bh + 1):                               # кирпичи
        off = (r_ % 2) * bw / 2
        for c_ in range(-1, W // bw + 2):
            x0, y0 = c_ * bw + off, r_ * bh
            v = int(rnd.integers(30, 46))
            K.rrect(d, (x0 + 3, y0 + 3, x0 + bw - 3, y0 + bh - 3), 4, fill=(v + 8, v - 6, v - 8, 255))
    img.alpha_composite(Image.new('RGBA', img.size, (0, 0, 0, 120)))
    PINK, BLUE = (255, 70, 170), (70, 190, 255)
    col = _vcol(m.get('hit'))
    K.glow_text(img, (W / 2, 120), 'JARVIS · ИТОГ', K.font('mont', 40, 900), PINK, 10, 2.2)
    K.text(d, (W / 2, 180), m['date'].upper(), K.font('mont', 24, 800), (220, 200, 220))
    for j, t in enumerate((m['home'], m['away'])):
        x = 230 if j == 0 else W - 230
        e = K.emblem(t, 200)
        g = Image.new('RGBA', e.size, (255, 255, 255, 0))
        g.putalpha(e.getchannel('A').filter(ImageFilter.GaussianBlur(14 * S)).point(lambda v: v * 200 // 255))
        K.put(img, g, x, 380)
        K.put(img, e, x, 380)
        K.glow_text(img, (x, 540), K.short(t).upper(), K.fit(K.short(t).upper(), 'osw', 50, 380, 600), BLUE, 10, 2.0)
    K.glow_text(img, (W / 2, 380), _score(m), K.font('osw', 170, 600), PINK, 18, 2.4)
    K.text(d, (W / 2, 640), _mark(m), K.font('mont', 26, 800), (230, 220, 235))
    K.glow_text(img, (W / 2, 760), 'ПРОГНОЗ', K.font('mont', 34, 900), BLUE, 8, 2.0)
    K.glow_text(img, (W / 2, 850), m['pick'], K.fit(m['pick'], 'osw', 74, 940, 600), (255, 255, 255), 10, 1.4,
                core=(255, 250, 240))
    K.glow_text(img, (W / 2, 940), 'КЭФ ' + (K.fmt_odds(m.get('odds')) or '—'), K.font('osw', 58, 600), PINK, 10, 2.0)
    vb = (170, 1030, 910, 1220)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle([v * S for v in vb], 40 * S, outline=col + (255,), width=8 * S)
    g = lay.filter(ImageFilter.GaussianBlur(14 * S))
    g.putalpha(g.getchannel('A').point(lambda v: min(255, v * 3)))
    img.alpha_composite(g)
    img.alpha_composite(lay)
    K.glow_text(img, (W / 2, 1125), _verdict(m.get('hit')), K.fit(_verdict(m.get('hit')), 'osw', 120, 680, 600), col, 18, 2.6,
                core=K.mix(col, 0.6))
    K.text(d, (W / 2, 1295), '@jarvibet', K.font('mont', 28, 900), (230, 220, 235))


# ── 6. Газета ───────────────────────────────────────────────────────────────────────────────────────────────────────
def _halftone(e, size, cell=7):
    g = ImageOps.grayscale(e.convert('RGB'))
    a = np.asarray(e.getchannel('A'), np.float32) / 255
    v = 1 - np.asarray(g, np.float32) / 255 * a - (1 - a)       # тёмное → крупная точка
    c = cell * S
    hh, ww = g.height // c, g.width // c
    small = Image.fromarray((np.clip(v, 0, 1) * 255).astype(np.uint8)).resize((ww, hh), Image.BILINEAR)
    sv = np.asarray(small, np.float32) / 255
    out = Image.new('RGBA', (ww * c, hh * c), (0, 0, 0, 0))
    od = ImageDraw.Draw(out)
    for yy in range(hh):
        for xx in range(ww):
            r = sv[yy, xx] * c * 0.62
            if r > 0.6:
                cx, cy = xx * c + c / 2, yy * c + c / 2
                od.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(28, 26, 24, 255))
    return out


def paper(m, img):
    d = ImageDraw.Draw(img)
    img.alpha_composite(K.vgrad(W, H, [(0, (236, 228, 210)), (1, (226, 216, 196))]))
    ink = (28, 26, 24)
    K.text(d, (W / 2, 95), 'JARVIS ВЕДОМОСТИ', K.font('yeseva', 82), ink)
    d.line((50 * S, 150 * S, 1030 * S, 150 * S), fill=ink, width=3 * S)
    d.line((50 * S, 158 * S, 1030 * S, 158 * S), fill=ink, width=S)
    K.text(d, (50, 182), m['date'].upper(), K.font('mont', 20, 800), ink, 'lm')
    K.text(d, (1030, 182), 'ХОККЕЙ · %s · ВЫПУСК ДНЯ' % ('НХЛ' if _tag(m) == 'NHL' else 'КХЛ'), K.font('mont', 20, 800), ink, 'rm')
    d.line((50 * S, 204 * S, 1030 * S, 204 * S), fill=ink, width=S)
    win = m['home'] if m['sh'] > m['sa'] else m['away']
    head = 'ПРОГНОЗ %s' % _verdict(m.get('hit'))
    K.text(d, (W / 2, 290), head, K.fit(head, 'play', 104, 960, 700), ink)
    sub = '%s — %s %s. Ставка «%s» за %s' % (K.short(m['home']), K.short(m['away']), _score(m), m['pick'],
                                              K.fmt_odds(m.get('odds')) or '—')
    K.text(d, (W / 2, 380), sub, K.fit(sub, 'playi', 40, 960, 400), ink)
    # «фото» растром
    ph = (50, 430, 1030, 900)
    d.rectangle([v * S for v in ph], fill=(218, 208, 188, 255), outline=ink, width=2 * S)
    for j, t in enumerate((m['home'], m['away'])):
        ht = _halftone(K.emblem(t, 300), 300)
        K.put(img, ht, 300 if j == 0 else 780, 640)
    K.text(d, (W / 2, 640), _score(m), K.font('yeseva', 150), ink)
    K.text(d, (50, 925), 'Итог матча: %s. Время: %s.' % (_score(m), _mark(m).lower()), K.font('playi', 24, 400), ink, 'lm')
    d.line((50 * S, 950 * S, 1030 * S, 950 * S), fill=ink, width=S)
    # заметка в две колонки
    col_w = 470
    txt = ('%s взял верх над «%s» со счётом %s. Прогноз канала — «%s» с коэффициентом %s.' %
           (K.short(win), K.short(m['away'] if win == m['home'] else m['home']), _score(m), m['pick'],
            K.fmt_odds(m.get('odds')) or '—'))
    txt2 = 'Вердикт редакции: прогноз %s. Разбор следующих матчей — в Telegram-канале @jarvibet.' % _verdict(m.get('hit')).lower()
    f = K.font('play', 26, 400)
    for k, para in enumerate((txt, txt2)):
        x0 = 50 + k * (col_w + 40)
        words, line, yy = para.split(), '', 990
        for wd in words:
            test = (line + ' ' + wd).strip()
            if f.getlength(test) > col_w * S:
                K.text(d, (x0, yy), line, f, ink, 'lm')
                line, yy = wd, yy + 38
            else:
                line = test
        K.text(d, (x0, yy), line, f, ink, 'lm')
    d.line((540 * S, 970 * S, 540 * S, 1200 * S), fill=ink, width=S)
    col = _vcol(m.get('hit'))
    K.rrect(d, (50, 1230, 1030, 1310), 6, fill=col + (255,))
    K.text(d, (W / 2, 1270), '%s · КЭФ %s · @JARVIBET' % (_verdict(m.get('hit')), K.fmt_odds(m.get('odds')) or '—'),
           K.font('mont', 32, 900), (255, 255, 255))


STYLES = {'stamp': stamp, 'jumbo': jumbo, 'check': check, 'medal': medal, 'neon': neon, 'paper': paper}


def render(m, path, style='stamp'):
    K.prep(K.league_of(m['home'], m['away']))
    _tag_cache[0] = _tag(m)
    img = K.canvas()
    STYLES[style](m, img)
    return K.save(img, path, grain=3)


if __name__ == '__main__':
    import sys
    m = dict(home='ЦСКА', away='Динамо Москва', sh=1, sa=0, mark='', pick='ПОБЕДА ЦСКА', odds=1.91, hit=True,
             date='среда, 14 октября')
    for st in (sys.argv[1:] or STYLES):
        print(render(m, 'out/post6/post_%s.jpg' % st, st))
