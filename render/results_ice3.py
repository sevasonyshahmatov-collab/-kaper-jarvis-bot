"""«Итоги дня» в стиле «Лёд» — пять других раскладок, победитель виден без галочек.

    import results_ice3 as r3
    r3.render(items, 'itogi.jpg', layout='stack', league='KHL', date_title='понедельник, 28 сентября')

layout:
  'stack'    ДВЕ ПОЛОСЫ     — каждая команда своей полосой; у победителя полоса длиннее и в цвете. Oswald.
  'winner'   ЦВЕТ ПОБЕДЫ    — плашка окрашена только со стороны победителя, сторона проигравшего светлая. Russo One.
  'tiles'    ПЛИТКИ         — сетка 2 колонки, у каждой плитки шапка в цвете победителя. Unbounded.
  'tab'      ВКЛАДКА        — счёт на вкладке над плашкой, вкладка в цвете победителя со стрелкой. Tektur.
  'diagonal' ДИАГОНАЛЬ      — плашка разрезана наискось, у победителя большая часть. Exo 2 Italic.
"""
import numpy as np
from PIL import Image, ImageDraw

import poster
import results_styles as rs
from results_styles2 import F, fit, club, spaced, OSW, TEK, RUSSO, UNB, EXOI
from results_ice2 import _background, _logo, NAVY, RED

S, W = rs.S, rs.W
HEAD, FOOT = 270, 96
LIGHT = (242, 245, 250)
GREY = (150, 158, 172)
GOLD = (255, 194, 61)


def _header(d, league, title, date_title):
    rs._brand(d, W * S / 2, 58 * S, league, dark_text=True)
    d.text((W * S / 2, 136 * S), title, font=F(EXOI, 76 * S, 900), anchor='mm', fill=NAVY + (255,))
    if date_title:
        spaced(d, (W * S / 2, 206 * S), date_title.upper(), F(EXOI, 22 * S, 700), (60, 80, 112, 255), 3 * S)


def _footer(d, H):
    spaced(d, (W * S / 2, (H - 42) * S), '@jarvibet', F(EXOI, 24 * S, 800), RED + (255,), 2 * S)


def _dim(c):
    """Цвет проигравшего: обесцвеченный и темнее."""
    c = np.array(c, np.float32)
    return tuple(int(v) for v in (c * 0.35 + c.mean() * 0.65) * 0.8)


def _ink(c):
    """Цвет клуба, достаточно тёмный для цифр на светлом фоне."""
    c = np.array(c, np.float32)
    lum = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    return tuple(int(v) for v in (c * (110 / lum) if lum > 110 else c))


def _grad_box(w, h, radius, left, right=None, split=None, gloss=True):
    """Прямоугольник с цветом (или двумя цветами с резкой границей split — доля ширины) и бликом сверху."""
    right = right or left
    xs = np.linspace(0, 1, w, dtype=np.float32)
    k = (xs >= (split if split is not None else 1.1)).astype(np.float32)[:, None]
    a = (1 - k) * np.array(left, np.float32) + k * np.array(right, np.float32)
    a = np.repeat(a[None], h, axis=0)
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    a = a * (1 - 0.16 * ys)
    if gloss:
        a = a + (255 - a) * np.clip(0.22 - ys * 0.5, 0, 1)
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=245)
    img.putalpha(m)
    return img


def _name(d, xy, text, font, anchor, won, on_color=True):
    if on_color:
        d.text((xy[0], xy[1] + 2 * S), text, font=font, anchor=anchor, fill=(0, 0, 0, 90))
        d.text(xy, text, font=font, anchor=anchor, fill=(255, 255, 255, 255 if won else 170))
    else:
        d.text(xy, text, font=font, anchor=anchor, fill=NAVY + (255,) if won else GREY + (255,))


def _tag(d, cx, cy, mark, dark=True):
    if not mark:
        return
    t, f = rs.MARK_TEXT[mark], F(EXOI, 13 * S, 800)
    w = f.getlength(t) + 16 * S
    d.rounded_rectangle((cx - w / 2, cy - 11 * S, cx + w / 2, cy + 11 * S), radius=8 * S, fill=(16, 22, 34, 230) if dark else (255, 255, 255, 240))
    d.text((cx, cy), t, font=f, anchor='mm', fill=(255, 255, 255, 255) if dark else (16, 22, 34, 255))


# ------------------------------------------------------------------ 1. ДВЕ ПОЛОСЫ
def _stack(items, path, league, title, date_title):
    BAR, IN, GAP = 62, 8, 22
    BLOCK = BAR * 2 + IN
    H = HEAD + len(items) * (BLOCK + GAP) - GAP + FOOT
    bg = _background(H, league)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _header(d, league, title, date_title)
    for i, it in enumerate(items):
        y0 = HEAD + i * (BLOCK + GAP)
        hw = it['sh'] > it['sa']
        for k, (team, val, won) in enumerate(((it['home'], it['sh'], hw), (it['away'], it['sa'], not hw))):
            by = y0 + k * (BAR + IN)
            x1, x2 = 132, (W - 150) if won else (W - 300)            # полоса победителя длиннее
            bar = _grad_box((x2 - x1) * S, BAR * S, 16 * S, club(team) if won else _dim(club(team)))
            poster._shadowed(ov, bar, (x1 * S, by * S), blur=8 * S, off=(0, 4 * S), color=(30, 60, 110, 60))
            cy = (by + BAR / 2) * S
            e = poster._raw_emblem(team, int(70 * S), int(70 * S))
            if not won:
                g = e.convert('L').convert('RGBA'); g.putalpha(e.getchannel('A').point(lambda v: int(v * 0.6))); e = g
            from results_styles2 import _sticker
            e = _sticker(e, 4 * S)
            poster._shadowed(ov, e, (int(92 * S - e.width / 2), int(cy - e.height / 2)), blur=8 * S, off=(0, 4 * S), color=(0, 0, 0, 110))
            d = ImageDraw.Draw(ov)
            name = rs._short(team)
            _name(d, (160 * S, cy), name, fit(name, OSW, 34 * S, 360 * S, 700 if won else 500), 'lm', won)
            d.text(((W - 70) * S, cy), str(val), font=F(OSW, 60 * S if won else 42 * S, 700 if won else 500), anchor='mm',
                   fill=NAVY + (255,) if won else GREY + (255,))
        if it.get('mark'):
            _tag(d, (W - 150 - 70) * S, (y0 + (BAR + IN) * (0 if hw else 1) + BAR / 2) * S, it['mark'])
    _footer(d, H)
    return rs._finish(bg, ov, H, path, grain=0.2)


# ------------------------------------------------------------------ 2. ЦВЕТ ПОБЕДЫ
def _winner(items, path, league, title, date_title):
    ROW, GAP = 128, 16
    H = HEAD + len(items) * (ROW + GAP) - GAP + FOOT
    bg = _background(H, league)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _header(d, league, title, date_title)
    for i, it in enumerate(items):
        y0 = HEAD + i * (ROW + GAP)
        cy = (y0 + ROW / 2) * S
        hw = it['sh'] > it['sa']
        wc = club(it['home'] if hw else it['away'])
        plate = _grad_box((W - 64) * S, ROW * S, 22 * S, wc if hw else LIGHT, LIGHT if hw else wc, split=0.5)
        poster._shadowed(ov, plate, (32 * S, y0 * S), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 70))
        lx, rx = (32 + ROW * 0.6) * S, (W - 32 - ROW * 0.6) * S
        _logo(ov, it['home'], lx, cy, 10, faded=not hw)
        _logo(ov, it['away'], rx, cy, -10, faded=hw)
        d = ImageDraw.Draw(ov)
        for team, x, anchor, won in ((it['home'], 196, 'lm', hw), (it['away'], W - 196, 'rm', not hw)):
            name = rs._short(team)
            _name(d, (x * S, cy), name, fit(name, EXOI, 34 * S, 190 * S, 800), anchor, won, on_color=won)
        # счёт: цифра победителя в цвете клуба, на белой «таблетке», проигравшего — серая
        cx = W / 2 * S
        ws = -1 if hw else 1
        d.rounded_rectangle((cx - 96 * S, cy - 44 * S, cx + 96 * S, cy + 44 * S), radius=44 * S, fill=(255, 255, 255, 250),
                            outline=wc + (255,), width=4 * S)
        d.text((cx + ws * 42 * S, cy), str(it['sh'] if hw else it['sa']), font=F(RUSSO, 60 * S), anchor='mm', fill=_ink(wc) + (255,))
        d.text((cx - ws * 42 * S, cy + 3 * S), str(it['sa'] if hw else it['sh']), font=F(RUSSO, 40 * S), anchor='mm', fill=GREY + (255,))
        d.text((cx, cy - 2 * S), ':', font=F(RUSSO, 36 * S), anchor='mm', fill=(190, 196, 208, 255))
        _tag(d, cx, cy + 56 * S, it.get('mark'))
    _footer(d, H)
    return rs._finish(bg, ov, H, path, grain=0.2)


# ------------------------------------------------------------------ 3. ПЛИТКИ
def _tiles(items, path, league, title, date_title):
    cols, gap, TH, BAND = 2, 20, 250, 104
    rows = (len(items) + cols - 1) // cols
    H = HEAD + rows * (TH + gap) - gap + FOOT
    TW = (W - 64 - gap) // cols
    bg = _background(H, league)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _header(d, league, title, date_title)
    for i, it in enumerate(items):
        r, c = divmod(i, cols)
        x0 = 32 + c * (TW + gap)
        if r == rows - 1 and len(items) % cols and c == 0:
            x0 = (W - TW) // 2
        y0 = HEAD + r * (TH + gap)
        hw = it['sh'] > it['sa']
        wt, lt = (it['home'], it['away']) if hw else (it['away'], it['home'])
        wv, lv = (it['sh'], it['sa']) if hw else (it['sa'], it['sh'])
        tile = Image.new('RGBA', (TW * S, TH * S), (0, 0, 0, 0))
        ImageDraw.Draw(tile).rounded_rectangle((0, 0, tile.width - 1, tile.height - 1), radius=24 * S, fill=(255, 255, 255, 235))
        band = _grad_box(TW * S, BAND * S, 24 * S, club(wt))
        bm = Image.new('L', band.size, 0)                           # у шапки скруглены только верхние углы
        ImageDraw.Draw(bm).rounded_rectangle((0, 0, band.width - 1, band.height + 40 * S), radius=24 * S, fill=245)
        band.putalpha(bm)
        tile.alpha_composite(band)
        poster._shadowed(ov, tile, (x0 * S, y0 * S), blur=12 * S, off=(0, 6 * S), color=(30, 60, 110, 70))
        _logo(ov, wt, (x0 + 62) * S, (y0 + BAND / 2) * S, 8, size=84)
        d = ImageDraw.Draw(ov)
        name = rs._short(wt)
        _name(d, ((x0 + 124) * S, (y0 + BAND / 2) * S), name, fit(name, UNB, 26 * S, (TW - 144) * S, 800), 'lm', True)
        # счёт крупно, «победитель — проигравший»
        sy = (y0 + BAND + 64) * S
        d.text(((x0 + 30) * S, sy), str(wv), font=F(UNB, 60 * S, 800), anchor='lm', fill=_ink(club(wt)) + (255,))
        wv_w = F(UNB, 60 * S, 800).getlength(str(wv))
        d.text(((x0 + 30) * S + wv_w + 14 * S, sy + 4 * S), ':  ' + str(lv), font=F(UNB, 38 * S, 600), anchor='lm', fill=GREY + (255,))
        # проигравший — мелко справа
        e = poster._raw_emblem(lt, int(52 * S), int(52 * S))
        g = e.convert('L').convert('RGBA'); g.putalpha(e.getchannel('A').point(lambda v: int(v * 0.55)))
        ov.alpha_composite(g, (int((x0 + TW - 84) * S - g.width / 2), int(sy - 14 * S - g.height / 2)))
        d = ImageDraw.Draw(ov)
        ln = rs._short(lt)
        d.text(((x0 + TW - 84) * S, sy + 32 * S), ln, font=fit(ln, UNB, 14 * S, 140 * S, 600), anchor='mm', fill=GREY + (255,))
        if it.get('mark'):
            _tag(d, (x0 + 110) * S, (y0 + TH - 26) * S, it['mark'])
    _footer(d, H)
    return rs._finish(bg, ov, H, path, grain=0.2)


# ------------------------------------------------------------------ 4. ВКЛАДКА
def _tab(items, path, league, title, date_title):
    ROW, GAP, TAB = 112, 50, 40
    top = HEAD + TAB
    H = top + len(items) * (ROW + GAP) - GAP + FOOT
    bg = _background(H, league)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _header(d, league, title, date_title)
    for i, it in enumerate(items):
        y0 = top + i * (ROW + GAP)
        cy = (y0 + ROW / 2 + 6) * S
        hw = it['sh'] > it['sa']
        ch, ca = club(it['home']), club(it['away'])
        plate = _grad_box((W - 64) * S, ROW * S, 22 * S, ch if hw else _dim(ch), _dim(ca) if hw else ca, split=0.5)
        poster._shadowed(ov, plate, (32 * S, y0 * S), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 70))
        _logo(ov, it['home'], (32 + 70) * S, cy, 10)
        _logo(ov, it['away'], (W - 32 - 70) * S, cy, -10)
        d = ImageDraw.Draw(ov)
        for team, x, anchor, won in ((it['home'], 190, 'lm', hw), (it['away'], W - 190, 'rm', not hw)):
            name = rs._short(team)
            _name(d, (x * S, cy), name, fit(name, EXOI, 32 * S, 240 * S, 800), anchor, won)
        # вкладка со счётом над плашкой, в цвете победителя; уголок-стрелка смотрит на победителя
        wc = ch if hw else ca
        cx, tw, th = W / 2 * S, 184 * S, 70 * S
        ty = (y0 - TAB + 8) * S
        tab = _grad_box(int(tw), int(th), 18 * S, wc)
        poster._shadowed(ov, tab, (int(cx - tw / 2), int(ty)), blur=10 * S, off=(0, 5 * S), color=(0, 0, 0, 110))
        d = ImageDraw.Draw(ov)
        ws = -1 if hw else 1
        tip = cx + ws * (tw / 2 + 16 * S)
        d.polygon([(cx + ws * (tw / 2 - 2 * S), ty + th / 2 - 14 * S), (tip, ty + th / 2), (cx + ws * (tw / 2 - 2 * S), ty + th / 2 + 14 * S)], fill=wc + (255,))
        fb, fs = F(TEK, 58 * S, 800, 100), F(TEK, 38 * S, 600, 100)
        d.text((cx - 36 * S, ty + th / 2), str(it['sh']), font=fb if hw else fs, anchor='mm', fill=(255, 255, 255, 255 if hw else 150))
        d.text((cx, ty + th / 2 - 3 * S), ':', font=F(TEK, 40 * S, 700, 100), anchor='mm', fill=(255, 255, 255, 170))
        d.text((cx + 36 * S, ty + th / 2), str(it['sa']), font=fs if hw else fb, anchor='mm', fill=(255, 255, 255, 150 if hw else 255))
        _tag(d, cx, cy + 22 * S, it.get('mark'), dark=True)
    _footer(d, H)
    return rs._finish(bg, ov, H, path, grain=0.2)


# ------------------------------------------------------------------ 5. ДИАГОНАЛЬ
def _diagonal(items, path, league, title, date_title):
    ROW, GAP = 128, 16
    H = HEAD + len(items) * (ROW + GAP) - GAP + FOOT
    bg = _background(H, league)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _header(d, league, title, date_title)
    w, h = (W - 64) * S, ROW * S
    xx, yy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    for i, it in enumerate(items):
        y0 = HEAD + i * (ROW + GAP)
        cy = (y0 + ROW / 2) * S
        hw = it['sh'] > it['sa']
        base = w * (0.60 if hw else 0.40)                          # у победителя большая часть плашки
        edge = base + (yy - h / 2) * -0.45                          # наклон разреза
        half = 70 * S
        ch = np.array(club(it['home']) if hw else _dim(club(it['home'])), np.float32)
        ca = np.array(_dim(club(it['away'])) if hw else club(it['away']), np.float32)
        a = np.where((xx < edge - half)[..., None], ch, np.where((xx > edge + half)[..., None], ca, np.array((18, 22, 32), np.float32)))
        ys = (yy / h)[..., None]
        a = a * (1 - 0.16 * ys) + (255 - a * (1 - 0.16 * ys)) * np.clip(0.2 - ys * 0.5, 0, 1)
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=22 * S, fill=245)
        img.putalpha(m)
        poster._shadowed(ov, img, (32 * S, y0 * S), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 70))
        _logo(ov, it['home'], (32 + 76) * S, cy, 10, faded=not hw)
        _logo(ov, it['away'], (W - 32 - 76) * S, cy, -10, faded=hw)
        d = ImageDraw.Draw(ov)
        sx = 32 * S + base                                          # центр тёмной косой полосы
        for team, x, anchor, won in ((it['home'], 190, 'lm', hw), (it['away'], W - 190, 'rm', not hw)):
            name = rs._short(team)
            room = (sx / S - 190 - 90) if anchor == 'lm' else (W - 190 - sx / S - 90)
            _name(d, (x * S, cy), name, fit(name, EXOI, 34 * S, max(120, room) * S, 800), anchor, won)
        f_big, f_small = F(EXOI, 60 * S, 900), F(EXOI, 40 * S, 800)
        ws = -1 if hw else 1
        d.text((sx + ws * 30 * S, cy), str(it['sh'] if hw else it['sa']), font=f_big, anchor='mm', fill=GOLD + (255,))
        d.text((sx - ws * 30 * S, cy + 4 * S), str(it['sa'] if hw else it['sh']), font=f_small, anchor='mm', fill=(150, 158, 172, 255))
        _tag(d, sx, cy + 46 * S, it.get('mark'), dark=False)
    _footer(d, H)
    return rs._finish(bg, ov, H, path, grain=0.2)


LAYOUTS = {'stack': _stack, 'winner': _winner, 'tiles': _tiles, 'tab': _tab, 'diagonal': _diagonal}


def render(items, path, layout='stack', league='KHL', title='ИТОГИ ДНЯ', date_title=None):
    league = league.upper()
    return LAYOUTS[layout](rs._resolve(items, league), path, league, title, date_title)
