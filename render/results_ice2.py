"""«Итоги дня» в формате «Лёд» с логотипами поверх плашек — шесть способов сразу показать победителя.

    import results_ice2 as ri
    ri.render(items, 'itogi.jpg', variant=1, league='KHL', date_title='понедельник, 28 сентября')

Общее для всех шести:
  • центр плашки нейтральный — цвета клубов не смешиваются, счёт стоит на своём фоне;
  • половина проигравшего приглушена, половина победителя — в полном цвете;
  • иней только сверху, под заголовком (края картинки чистые);
  • свой шрифт цифр счёта в каждом варианте.
variant:
  1 КАПСУЛА   — тёмная капсула, цифра победителя крупная золотая, проигравшего мелкая серая. Russo One.
  2 ПОБЕДА    — светлый центр, крупная цифра победителя с полосой его цвета, подпись «ПОБЕДА». Oswald.
  3 СТРЕЛКА   — тёмный центр, между цифрами золотая стрелка в сторону победителя, логотип проигравшего серый. Unbounded.
  4 КОРОНА    — тёмная панель табло, светящаяся цифра победителя, золотая корона над его логотипом. Tektur.
  5 ШАЙБА     — светлый центр, у победителя большая чёрная шайба, у проигравшего маленькая. Exo 2 Italic.
  6 ГАЛОЧКА   — светло-серый центр, цифра победителя подчёркнута его цветом, зелёная галочка на логотипе. Montserrat.
  7 БОКА      — базовый: табло 4 без короны, логотип победителя стикером, проигравшего — силуэтом в плашке; шрифты «Боков».
  8 / 9       — логотип во всю цветную колонку (срезан краями), название поверх с контуром; проигравший — силуэт / тёмный.
Только логотипы, без названий (как в сетке плей-офф):
  10 ЯЧЕЙКИ   — светлые ячейки, логотип во всю ячейку, проигравший серым; тёмное табло 7, полоска цвета клуба у табло.
  11 СЕТКА    — скошенные ячейки как в сетке КХЛ: белая ячейка с логотипом + плашка счёта в цвете клуба.
  12 КОЛОНКИ  — ячейки в цвете клуба, логотип во всю колонку, проигравший — силуэт; табло 7.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import poster
import results_styles as rs
from results_styles2 import F, fit, club, spaced, _sticker, _layered, _noise, OSW, TEK, RUSSO, UNB, EXOI

S, W = rs.S, rs.W
ROW, GAP, HEAD, FOOT = 128, 16, 270, 96
NAVY, RED = (16, 34, 70), (214, 40, 57)
MONT = 'Montserrat[wght].ttf'
GREEN = (34, 176, 86)


# ------------------------------------------------------------------ фон и иней сверху
def _background(H, league):
    bg = rs._gradient(W, H, (236, 244, 251), (205, 224, 240), glow=(255, 255, 255, 120), glow_xy=(0.3, 0.1), glow_r=0.6)

    def rink(g):
        g.line(((0, H * 0.55), (W, H * 0.55)), fill=(214, 40, 57, 60), width=10)
        for y in (H * 0.36, H * 0.76):
            g.line(((0, y), (W, y)), fill=(40, 90, 200, 45), width=10)
    bg = _layered(bg, rink)
    bg = rs._watermark(bg, league, NAVY, 0.06)
    return _frost_top(bg)


def _frost_top(img, reach=235, seed=5):
    """Иней только по верхней кромке — под заголовком: неровный край, узоры вниз, блёстки."""
    W_, H_ = img.size
    rng = np.random.default_rng(seed)
    yy = np.mgrid[0:H_, 0:W_][0].astype(np.float32)
    n = _noise(W_, H_, rng)
    m = np.clip(1 - yy / (reach * (0.55 + 0.8 * n)), 0, 1) ** 1.35
    hf = np.asarray(Image.fromarray((rng.random((H_, W_)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255
    alpha = np.clip(m * (0.60 + 0.55 * hf), 0, 1) * 0.92
    frost = np.dstack([230 + 25 * n, 240 + 15 * n, 250 + 5 * n, alpha * 255]).clip(0, 255).astype(np.uint8)
    layer = Image.fromarray(frost, 'RGBA').filter(ImageFilter.GaussianBlur(1.2))
    deep = np.dstack([np.full((H_, W_), 120), np.full((H_, W_), 172), np.full((H_, W_), 226),
                      np.clip(m * 1.25, 0, 1) ** 1.2 * 140]).astype(np.uint8)
    under = Image.fromarray(deep, 'RGBA').filter(ImageFilter.GaussianBlur(6))

    lines = Image.new('RGBA', (W_, H_), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)

    def fern(x, y, ang, length, depth):
        if depth < 0 or length < 6:
            return
        x2, y2 = x + math.cos(ang) * length, y + math.sin(ang) * length
        ld.line(((x, y), (x2, y2)), fill=(255, 255, 255, 170 - (2 - depth) * 40), width=max(1, depth + 1))
        steps = int(rng.integers(2, 5))
        for j in range(1, steps + 1):
            t = j / (steps + 1)
            for sgn in (-1, 1):
                fern(x + (x2 - x) * t, y + (y2 - y) * t, ang + sgn * rng.uniform(0.6, 1.0), length * rng.uniform(0.28, 0.45), depth - 1)

    for _ in range(W_ // 14):
        fern(rng.uniform(0, W_), 0, math.pi / 2 + rng.uniform(-0.7, 0.7), rng.uniform(40, 120), 2)
    la = np.asarray(lines, np.float32)
    la[..., 3] *= np.clip(m * 1.6, 0, 1)
    lines = Image.fromarray(la.astype(np.uint8), 'RGBA')
    halo = Image.fromarray(np.dstack([np.full((H_, W_), 90, np.uint8), np.full((H_, W_), 150, np.uint8),
                                      np.full((H_, W_), 215, np.uint8), np.asarray(lines.getchannel('A'))]), 'RGBA').filter(ImageFilter.GaussianBlur(1.6))
    sp = Image.new('RGBA', (W_, H_), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sp)
    for _ in range(W_ * H_ // 900):
        x, y = int(rng.integers(W_)), int(rng.integers(H_))
        if m[y, x] > 0.25:
            r = rng.uniform(0.6, 1.8)
            sd.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(160 + 90 * m[y, x])))
    out = img.convert('RGBA')
    for L in (under, layer, halo, lines, sp):
        out = Image.alpha_composite(out, L)
    return out


# ------------------------------------------------------------------ плашка
def _plate(home, away, w, h, radius, home_win, center, cw=0.27, loser='desat'):
    """Слева цвет хозяев, справа гостей, в центре — нейтральная вставка под счёт.
    loser: 'desat' — половина проигравшего обесцвечена и чуть темнее, 'dark' — затемнена."""
    xs = np.linspace(0, 1, w, dtype=np.float32)
    a0, b0 = 0.5 - cw / 2, 0.5 + cw / 2
    soft = 0.003
    kc = np.clip((xs - a0) / soft, 0, 1) * np.clip((b0 - xs) / soft, 0, 1)          # центр
    kr = np.clip((xs - b0) / soft, 0, 1)                                            # гости
    kl = 1 - kc - kr
    ch, ca = np.array(club(home), np.float32), np.array(club(away), np.float32)

    def lose(c):
        if loser == 'none':                        # до матча: обе половины в полном цвете
            return c
        g = c.mean()
        return (c * 0.35 + g * 0.65) * 0.82 if loser == 'desat' else c * 0.5

    if home_win:
        ca = lose(ca)
    else:
        ch = lose(ch)
    a = kl[:, None] * ch + kr[:, None] * ca + kc[:, None] * np.array(center, np.float32)
    a = np.repeat(a[None], h, axis=0)
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    side = (1 - kc)[None, :, None]
    a = a * (1 - side * 0.18 * ys)                                                   # клубные половины чуть темнее книзу
    a = a + (255 - a) * np.clip(0.20 - ys * 0.5, 0, 1) * side                        # блик сверху
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=245)
    img.putalpha(m)
    ImageDraw.Draw(img).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, outline=(255, 255, 255, 160), width=max(2, h // 60))
    return img


def _logo(ov, team, cx, cy, ang, faded=False, size=None):
    e = poster._raw_emblem(team, int((size or ROW) * S), int((size or ROW) * S))
    if faded:                                     # логотип проигравшего: серый и полупрозрачный
        g = e.convert('L').convert('RGBA')
        g.putalpha(e.getchannel('A').point(lambda v: int(v * 0.62)))
        e = g
    e = _sticker(e, 5 * S).rotate(ang, Image.BICUBIC, expand=True)
    poster._shadowed(ov, e, (int(cx - e.width / 2), int(cy - e.height / 2)), blur=10 * S, off=(0, 6 * S), color=(0, 0, 0, 90 if faded else 120))


def _embed(card, team, side, ang=None):
    """Эмблема «вплавлена» в свою половину плашки тон-в-тон, как в ice_logo: крупно, наклонно, срезана краем."""
    w, h = card.size
    a = np.asarray(card, np.float32).copy()
    e = poster._raw_emblem(team, int(h * 1.55), int(h * 1.55))
    ang = ang if ang is not None else (10 if side == 'left' else -10)
    e = e.rotate(ang, Image.BICUBIC, expand=True)
    gray = np.asarray(e.convert('L'), np.float32) / 255
    al = np.asarray(e.getchannel('A'), np.float32) / 255 * 0.72
    cx = h * 0.66 if side == 'left' else w - h * 0.66
    x0, y0 = int(cx - e.width / 2), int(h * 0.52 - e.height / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(w, x0 + e.width), min(h, y0 + e.height)
    lim = int(w * 0.36) if side == 'left' else int(w * 0.64)       # не заходить на тёмный центр со счётом
    if side == 'left':
        xb = min(xb, lim)
    else:
        xa = max(xa, lim)
    g = gray[ya - y0:yb - y0, xa - x0:xb - x0, None]
    k = al[ya - y0:yb - y0, xa - x0:xb - x0, None]
    rgb = a[ya:yb, xa:xb, :3]
    a[ya:yb, xa:xb, :3] = rgb * (1 - k) + rgb * (0.55 + 0.85 * g) * k
    card.paste(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA'))


def _fill(card, team, side, mode):
    """Эмблема во всю цветную колонку: крупно, срезана краями плашки и центром.
    mode: 'color' — в полном цвете (чуть притемнена, чтобы читалось название), 'dim' — обесцвечена,
    'ghost' — силуэт тон-в-тон с плашкой."""
    w, h = card.size
    half = int(w * (1 - 0.27) / 2)                           # ширина цветной колонки
    e = poster._raw_emblem(team, int(half * 1.05), int(h * 1.9))
    x0 = (0 if side == 'left' else w - half) + (half - e.width) // 2
    y0 = (h - e.height) // 2
    a = np.asarray(card, np.float32).copy()
    em = np.zeros((h, w, 4), np.float32)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(w, x0 + e.width), min(h, y0 + e.height)
    em[ya:yb, xa:xb] = np.asarray(e, np.float32)[ya - y0:yb - y0, xa - x0:xb - x0]
    col = np.zeros(w, bool)
    col[:half] = side == 'left'
    col[w - half:] = side == 'right'
    k = em[..., 3:] / 255 * col[None, :, None]
    rgb, erg = a[..., :3], em[..., :3]
    if mode == 'ghost':
        g = erg.mean(axis=2, keepdims=True) / 255
        out = rgb * (0.55 + 0.85 * g)
        k = k * 0.72
    elif mode == 'dim':
        out = (erg * 0.3 + erg.mean(axis=2, keepdims=True) * 0.7) * 0.55
        k = k * 0.85
    else:
        out = erg * 0.82                                    # чуть темнее — белое название на логотипе читается
        k = k * 0.95
    a[..., :3] = rgb * (1 - k) + out * k
    card.paste(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA'))


def _paint(a, team, x0, x1, mask, mode, grow=1.1):
    """Эмблема во всю ячейку [x0, x1): крупно, по центру, срезана маской ячейки (mask — доля 0..1, h×w).
    mode: 'full' — в полном цвете, 'fade' — серый полупрозрачный силуэт проигравшего."""
    h, w = mask.shape
    e = poster._raw_emblem(team, int((x1 - x0) * grow), int(h * 1.85))
    ex, ey = int((x0 + x1 - e.width) / 2), (h - e.height) // 2
    em = np.zeros((h, w, 4), np.float32)
    xa, ya, xb, yb = max(0, ex), max(0, ey), min(w, ex + e.width), min(h, ey + e.height)
    em[ya:yb, xa:xb] = np.asarray(e, np.float32)[ya - ey:yb - ey, xa - ex:xb - ex]
    k = em[..., 3:] / 255 * mask[..., None]
    erg = em[..., :3]
    if mode == 'fade':
        out, k = erg.mean(axis=2, keepdims=True) * 0.6 + 70, k * 0.42
    else:
        out = erg
    a[..., :3] = a[..., :3] * (1 - k) + out * k


def _light(h, w):
    """Светлая ледяная заливка ячейки: белая сверху, чуть голубее книзу."""
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    top, bot = np.array((252, 253, 255), np.float32), np.array((222, 230, 241), np.float32)
    return np.repeat(top * (1 - ys) + bot * ys, w, axis=1)


def _poly_mask(w, h, pts):
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return np.asarray(m, np.float32) / 255


def _cells(it, hw, variant, center, pre=False, row=None):
    """Ячейки «как в сетке плей-офф»: команда показана только логотипом во всю ячейку, без названия.
    10 — светлые ячейки и тёмное табло по центру, у края табло полоска цвета клуба;
    11 — скошенные ячейки как в сетке КХЛ: белая ячейка с логотипом + плашка счёта в цвете клуба;
    12 — как 8, но без названий: ячейки в цвете клуба, логотип во всю колонку.
    pre=True — до матча: обе команды в полном цвете, проигравшего нет. row — высота ячейки (по умолчанию ROW)."""
    w, h, r = (W - 64) * S, int((row or ROW) * S), 22 * S
    home, away = it['home'], it['away']
    if variant == 12:
        card = _plate(home, away, w, h, r, hw, center, loser='none' if pre else 'dark')
        _fill(card, home, 'left', 'color' if hw or pre else 'ghost')
        _fill(card, away, 'right', 'color' if not hw or pre else 'ghost')
        return card
    lose = lambda c: tuple(int(v) for v in (np.array(c, np.float32) * 0.3 + np.mean(c) * 0.7) * 0.75)
    ch, ca = club(home), club(away)
    if pre:
        hw = None                                           # обе стороны «победители»: логотипы в цвете
    else:
        ch, ca = (ch, lose(ca)) if hw else (lose(ch), ca)
    a = np.zeros((h, w, 4), np.float32)
    if variant == 10:
        half = int(w * (1 - 0.27) / 2)
        band = 10 * S
        a[..., :3] = _light(h, w)
        a[:, half:w - half, :3] = center
        a[:, half - band:half, :3] = ch                     # полоска цвета клуба у табло
        a[:, w - half:w - half + band, :3] = ca
        for team, x0, x1, won in ((home, 0, half - band, hw), (away, w - half + band, w, not hw)):
            m = np.zeros((h, w), np.float32)
            m[:, x0:x1] = 1
            _paint(a, team, x0, x1, m, 'full' if won or pre else 'fade')
        m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=250)
        a[..., 3] = np.asarray(m, np.float32)
        card = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
        ImageDraw.Draw(card).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, outline=(255, 255, 255, 170), width=max(2, h // 60))
        return card
    # 11 — скошенные ячейки: [логотип][счёт] [счёт][логотип]
    sk = 30 * S
    we = w - sk
    cut = [0, 0.372, 0.378, 0.494, 0.506, 0.622, 0.628, 1.0]
    X = [int(v * we) for v in cut]
    seg = lambda x0, x1: [(x0 + sk, 0), (x1 + sk, 0), (x1, h), (x0, h)]
    a[..., :3] = _light(h, w)
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    alpha = np.zeros((h, w), np.float32)
    for (x0, x1), fill, team, won in (((X[0], X[1]), None, home, hw), ((X[2], X[3]), ch, None, hw),
                                      ((X[4], X[5]), ca, None, not hw), ((X[6], X[7]), None, away, not hw)):
        m = _poly_mask(w, h, seg(x0, x1))
        if fill is not None:
            col = np.array(fill, np.float32) * (1.08 - 0.2 * ys)
            col = np.broadcast_to(col, (h, w, 3))
            a[..., :3] = a[..., :3] * (1 - m[..., None]) + col * m[..., None]
        else:
            _paint(a, team, x0 + sk // 2, x1 + sk // 2, m, 'full' if won or pre else 'fade')
        alpha = np.maximum(alpha, m)
    a[..., 3] = alpha * 250
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA'), X, sk


def _crown(d, cx, cy, s, color):
    w, h = 34 * s, 24 * s
    pts = [(cx - w / 2, cy + h / 2), (cx - w / 2, cy - h / 4), (cx - w / 4, cy + h / 12), (cx, cy - h / 2),
           (cx + w / 4, cy + h / 12), (cx + w / 2, cy - h / 4), (cx + w / 2, cy + h / 2)]
    d.polygon(pts, fill=color, outline=(120, 80, 10, 255))
    for px in (cx - w / 2, cx, cx + w / 2):
        py = cy - h / 4 if px != cx else cy - h / 2
        d.ellipse((px - 3.5 * s, py - 3.5 * s, px + 3.5 * s, py + 3.5 * s), fill=color)


def _check(d, cx, cy, r):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GREEN + (255,), outline=(255, 255, 255, 255), width=int(r / 5))
    d.line(((cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), (cx + r * 0.5, cy - r * 0.35)),
           fill=(255, 255, 255, 255), width=int(r / 3.2), joint='curve')


MANROPE = 'Manrope[wght].ttf'


def _mark(d, cx, cy, mark, dark_bg, side=False):
    if not mark:
        return
    t, f = rs.MARK_TEXT[mark], (F(MANROPE, 13 * S, 800) if side else F(EXOI, 14 * S, 800))
    w = f.getlength(t) + 16 * S
    d.rounded_rectangle((cx - w / 2, cy - 11 * S, cx + w / 2, cy + 11 * S), radius=8 * S,
                        fill=(255, 255, 255, 235) if dark_bg else (16, 22, 34, 230))
    d.text((cx, cy), t, font=f, anchor='mm', fill=(16, 22, 34, 255) if dark_bg else (255, 255, 255, 255))


def _score7(ov, cx, cy, wv, lv, ws, mark, gold):
    """Табло варианта 7: светящаяся золотая цифра победителя (Unbounded), серая — проигравшего."""
    glow = Image.new('RGBA', ov.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((cx + ws * 44 * S, cy), str(wv), font=F(UNB, 58 * S, 700), anchor='mm', fill=gold + (230,))
    ov.alpha_composite(glow.filter(ImageFilter.GaussianBlur(12 * S)))
    d = ImageDraw.Draw(ov)
    d.text((cx + ws * 44 * S, cy), str(wv), font=F(UNB, 58 * S, 700), anchor='mm', fill=(255, 236, 170, 255))
    d.text((cx - ws * 44 * S, cy), str(lv), font=F(UNB, 44 * S, 500), anchor='mm', fill=(96, 104, 118, 255))
    d.text((cx, cy - 4 * S), ':', font=F(UNB, 36 * S, 500), anchor='mm', fill=(96, 104, 118, 255))
    _mark(d, cx, cy + 46 * S, mark, True, True)


# ------------------------------------------------------------------ сборка
CENTERS = {1: (20, 24, 34), 2: (242, 245, 250), 3: (20, 24, 34), 4: (12, 14, 20), 5: (242, 245, 250), 6: (226, 231, 238), 7: (12, 14, 20), 8: (12, 14, 20), 9: (12, 14, 20),
           10: (12, 14, 20), 11: (12, 14, 20), 12: (12, 14, 20)}
LOSER = {1: 'desat', 2: 'dark', 3: 'desat', 4: 'dark', 5: 'desat', 6: 'desat', 7: 'dark', 8: 'dark', 9: 'dark', 10: 'dark', 11: 'dark', 12: 'dark'}


def render(items, path, variant=1, league='KHL', title='ИТОГИ ДНЯ', date_title=None):
    league = league.upper()
    items = rs._resolve(items, league)
    acc = rs.ACCENT[league]
    gold = (255, 194, 61)
    H = HEAD + len(items) * (ROW + GAP) - GAP + FOOT
    bg = _background(H, league)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    rs._brand(d, W * S / 2, 58 * S, league, dark_text=True)
    side = variant >= 7                    # шрифты «Боков»: Oswald — названия, Unbounded — цифры, Manrope — подписи
    if side:
        spaced(d, (W * S / 2, 138 * S), title, F(OSW, 84 * S, 700), NAVY + (255,), 3 * S)
    else:
        d.text((W * S / 2, 136 * S), title, font=F(EXOI, 76 * S, 900), anchor='mm', fill=NAVY + (255,))
    if date_title:
        spaced(d, (W * S / 2, 206 * S), date_title.upper(), F(MANROPE, 21 * S, 800) if side else F(EXOI, 22 * S, 700), (40, 58, 92, 255), 3 * S)
    center = CENTERS[variant]
    dark_center = sum(center) < 300
    cx = W / 2 * S
    for i, it in enumerate(items):
        y0 = HEAD + i * (ROW + GAP)
        cy = (y0 + ROW / 2) * S
        hw = it['sh'] > it['sa']
        wv, lv = (it['sh'], it['sa']) if hw else (it['sa'], it['sh'])
        ws = -1 if hw else 1                       # сторона победителя: -1 слева, 1 справа
        if variant >= 10:                          # только логотипы, без названий
            card = _cells(it, hw, variant, center)
            if variant == 11:
                card, X, sk = card
            poster._shadowed(ov, card, (32 * S, y0 * S), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 70))
            if variant == 11:                      # цифры в плашках цвета клуба
                for (x0, x1), v, won in (((X[2], X[3]), it['sh'], hw), ((X[4], X[5]), it['sa'], not hw)):
                    x = 32 * S + (x0 + x1 + sk) / 2
                    d.text((x, cy + 2 * S), str(v), font=F(UNB, 58 * S if won else 48 * S, 800 if won else 600), anchor='mm',
                           fill=(255, 255, 255, 255 if won else 150), stroke_width=(2 * S if won else 0), stroke_fill=(0, 0, 0, 60))
                _mark(d, cx + sk / 2 - 6 * S, cy + 50 * S, it.get('mark'), True, side)
                continue
            _score7(ov, cx, cy, wv, lv, ws, it.get('mark'), gold)
            d = ImageDraw.Draw(ov)
            continue
        card = _plate(it['home'], it['away'], (W - 64) * S, ROW * S, 22 * S, hw, center, loser=LOSER[variant])
        if variant == 7:                           # логотип проигравшего «уходит» в плашку силуэтом
            _embed(card, it['away'] if hw else it['home'], 'right' if hw else 'left')
        if variant in (8, 9):                      # логотипы во всю колонку, срезаны краями плашки
            _fill(card, it['home'], 'left', 'color' if hw else ('ghost' if variant == 8 else 'dim'))
            _fill(card, it['away'], 'right', 'color' if not hw else ('ghost' if variant == 8 else 'dim'))
        poster._shadowed(ov, card, (32 * S, y0 * S), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 70))
        lx, rx = (32 + ROW * 0.60) * S, (W - 32 - ROW * 0.60) * S
        fade = variant in (3, 5)
        if variant not in (8, 9) and not (variant == 7 and not hw):
            _logo(ov, it['home'], lx, cy, 10, faded=fade and not hw)
        if variant not in (8, 9) and not (variant == 7 and hw):
            _logo(ov, it['away'], rx, cy, -10, faded=fade and hw)
        d = ImageDraw.Draw(ov)
        for team, x, anchor, won in ((it['home'], 196, 'lm', hw), (it['away'], W - 196, 'rm', not hw)):
            name = rs._short(team)
            f = fit(name, OSW, 40 * S, 196 * S, 700) if side else fit(name, EXOI, 34 * S, 196 * S, 800 if won else 700)
            d.text((x * S, cy + 2 * S), name, font=f, anchor=anchor, fill=(0, 0, 0, 90))
            if variant in (8, 9):                  # название лежит на логотипе — с тёмным контуром
                d.text((x * S, cy), name, font=f, anchor=anchor, fill=(255, 255, 255, 255 if won else 180),
                       stroke_width=3 * S, stroke_fill=(10, 14, 24, 220))
                continue
            d.text((x * S, cy), name, font=f, anchor=anchor, fill=(255, 255, 255, 255 if won else 150))
            if won and variant == 2:
                spaced(d, (x * S, cy + 32 * S), 'ПОБЕДА', F(EXOI, 14 * S, 800), gold + (255,), 2 * S, anchor='l' if anchor == 'lm' else 'r')
        if variant == 1:                           # КАПСУЛА
            fb, fs = F(RUSSO, 66 * S), F(RUSSO, 44 * S)
            d.text((cx + ws * 38 * S, cy), str(wv), font=fb, anchor='mm', fill=gold + (255,))
            d.text((cx - ws * 38 * S, cy + 4 * S), str(lv), font=fs, anchor='mm', fill=(130, 138, 152, 255))
            d.text((cx, cy - 4 * S), ':', font=F(RUSSO, 40 * S), anchor='mm', fill=(90, 98, 112, 255))
            _mark(d, cx, cy + 46 * S, it.get('mark'), True)
        elif variant == 2:                         # ПОБЕДА
            fb, fs = F(OSW, 84 * S, 700), F(OSW, 50 * S, 600)
            wx = cx + ws * 42 * S
            d.text((wx, cy - 4 * S), str(wv), font=fb, anchor='mm', fill=NAVY + (255,))
            d.rounded_rectangle((wx - 22 * S, cy + 38 * S, wx + 22 * S, cy + 45 * S), radius=3 * S, fill=club(it['home'] if hw else it['away']) + (255,))
            d.text((cx - ws * 42 * S, cy + 2 * S), str(lv), font=fs, anchor='mm', fill=(150, 158, 172, 255))
            d.text((cx, cy - 2 * S), '–', font=F(OSW, 44 * S, 500), anchor='mm', fill=(170, 176, 188, 255))
            if it.get('mark'):
                d.text((cx - ws * 42 * S, cy + 40 * S), rs.MARK_TEXT[it['mark']], font=F(EXOI, 12 * S, 800), anchor='mm', fill=RED + (255,))
        elif variant == 3:                         # СТРЕЛКА
            fn = F(UNB, 54 * S, 800)
            d.text((cx + ws * 60 * S, cy), str(wv), font=fn, anchor='mm', fill=(255, 255, 255, 255))
            d.text((cx - ws * 60 * S, cy), str(lv), font=F(UNB, 42 * S, 600), anchor='mm', fill=(110, 118, 132, 255))
            t = 16 * S                              # стрелка в сторону победителя
            d.polygon([(cx + ws * t, cy), (cx - ws * t * 0.7, cy - t), (cx - ws * t * 0.7, cy + t)], fill=gold + (255,))
            _mark(d, cx, cy + 46 * S, it.get('mark'), True)
        elif variant in (4, 7, 8, 9):              # КОРОНА (7–9 — без короны)
            glow = Image.new('RGBA', ov.size, (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            if side:
                fn, fl, fc = F(UNB, 58 * S, 700), F(UNB, 44 * S, 500), F(UNB, 36 * S, 500)
            else:
                fn, fl, fc = F(TEK, 72 * S, 800, 100), F(TEK, 56 * S, 600, 100), F(TEK, 44 * S, 700, 100)
            gd.text((cx + ws * 44 * S, cy), str(wv), font=fn, anchor='mm', fill=gold + (230,))
            ov.alpha_composite(glow.filter(ImageFilter.GaussianBlur(12 * S)))
            d = ImageDraw.Draw(ov)
            d.text((cx + ws * 44 * S, cy), str(wv), font=fn, anchor='mm', fill=(255, 236, 170, 255))
            d.text((cx - ws * 44 * S, cy), str(lv), font=fl, anchor='mm', fill=(96, 104, 118, 255))
            d.text((cx, cy - 4 * S), ':', font=fc, anchor='mm', fill=(96, 104, 118, 255))
            if variant == 4:
                _crown(d, (lx if hw else rx), cy - 62 * S, S, gold + (255,))
            _mark(d, cx, cy + 46 * S, it.get('mark'), True, side)
        elif variant == 5:                         # ШАЙБА
            wx, lxs = cx + ws * 46 * S, cx - ws * 54 * S
            r1, r2 = 50 * S, 32 * S
            d.ellipse((wx - r1, cy - r1, wx + r1, cy + r1), fill=(18, 20, 26, 255))
            d.ellipse((wx - r1 + 5 * S, cy - r1 + 5 * S, wx + r1 - 5 * S, cy + r1 - 5 * S), outline=(70, 76, 90, 255), width=2 * S)
            d.text((wx, cy - 2 * S), str(wv), font=F(EXOI, 60 * S, 900), anchor='mm', fill=(255, 255, 255, 255))
            d.ellipse((lxs - r2, cy - r2, lxs + r2, cy + r2), fill=(214, 220, 230, 255))
            d.text((lxs, cy - 1 * S), str(lv), font=F(EXOI, 36 * S, 800), anchor='mm', fill=(120, 130, 148, 255))
            if it.get('mark'):
                d.text((lxs, cy + 46 * S), rs.MARK_TEXT[it['mark']], font=F(EXOI, 12 * S, 800), anchor='mm', fill=RED + (255,))
        else:                                      # 6 ГАЛОЧКА
            fn = F(MONT, 62 * S, 900)
            wx, lx2 = cx + ws * 46 * S, cx - ws * 46 * S
            d.text((wx, cy - 4 * S), str(wv), font=fn, anchor='mm', fill=NAVY + (255,))
            d.rounded_rectangle((wx - 24 * S, cy + 30 * S, wx + 24 * S, cy + 38 * S), radius=4 * S, fill=club(it['home'] if hw else it['away']) + (255,))
            d.text((lx2, cy - 4 * S), str(lv), font=F(MONT, 46 * S, 700), anchor='mm', fill=(150, 158, 172, 255))
            d.text((cx, cy - 8 * S), ':', font=F(MONT, 40 * S, 800), anchor='mm', fill=(150, 158, 172, 255))
            _check(d, (lx + 46 * S) if hw else (rx - 46 * S), cy - 42 * S, 17 * S)
            if it.get('mark'):
                d.text((lx2, cy + 34 * S), rs.MARK_TEXT[it['mark']], font=F(EXOI, 12 * S, 800), anchor='mm', fill=RED + (255,))
    spaced(d, (W * S / 2, (H - 42) * S), '@jarvibet', F(UNB, 20 * S, 700) if side else F(EXOI, 24 * S, 800), RED + (255,), 2 * S)
    return rs._finish(bg, ov, H, path, grain=0.2)
