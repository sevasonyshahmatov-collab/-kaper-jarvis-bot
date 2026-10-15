# -*- coding: utf-8 -*-
"""Анимированный (видео) стикерпак канала @jarvibet — «JARVIS · хоккей стикеры» (jarvibet_stickers).

Семь разных стилей и форматов (29 стикеров):
  neon  — неоновая вывеска на кирпичной стене: трубки букв гудят и мигают, галочка перерисовывается,
          шевроны «бегут» (широкая плашка);
  led   — табло стадиона: точечная LED-матрица в корпусе, мигалка гола, бегущие шевроны, столбики, лампы буллитов;
  ice   — круглый ледяной значок с лентой: блик, искры, снег; шайба влетает и отскакивает, стрелки крутятся;
  stamp — купон-прогноз, на который с размаху падает печать (прямоугольная или круглая), брызги чернил;
  flag  — флаг на древке, колышется тканью, как анимированные баннеры канала (render/versus_anim.py);
  comic — комикс-взрыв: «кипящий» зубчатый взрыв с растром, объёмные буквы, шайба, монеты, искры;
  board — тактическая доска тренера: маркер сам пишет текст, губка стирает, стрелки и галочки дорисовываются.

Формат Telegram для видео-стикеров: WEBM VP9 с альфой (yuva420p), одна сторона ровно 512 px, другая ≤ 512,
≤ 3 с, ≤ 30 fps, без звука, ≤ 256 КБ; петля бесшовная. Первый кадр — «полная» поза (его Telegram показывает
как превью). Логотипов клубов и названий букмекеров нет; «JARVIS» латиницей — только маленькой маркой.

Запуск:  PYTHONPATH=render python team/stickers/anim.py [папка] [ключи…] [--no-build] [--no-sheet]
         → <папка>/<ключ>.webm, probe.json, sheet_dark.png, sheet_light.png
         и (если отрисованы все) team/stickers/build/<ключ>.webm + manifest.json для team/emoji/publish.py.
"""
import json
import math
import os
import random
import shutil
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FD = os.path.join(ROOT, 'render', 'fonts')
sys.path.insert(0, os.path.join(ROOT, 'team', 'emoji'))
sys.path.append(os.path.join(ROOT, 'render'))
import make as mk  # noqa: E402  — шайба и шрифты семейства эмодзи

DEFAULT_OUT = '/tmp/claude-0/-home-user--kaper-jarvis-bot/750ccff3-fed4-56c4-8b4f-e7d578ed1f4d/scratchpad/owner8_9/stickers'
BUILD = os.path.join(HERE, 'build')
SET_NAME, SET_TITLE = 'jarvibet_stickers', 'JARVIS · хоккей стикеры'
FPS = 30
SS = 2                                   # статичные слои рисуем в 2× и уменьшаем
MAX_BYTES = 256 * 1024
BUDGET = 248 * 1024

WHITE = (255, 255, 255)
NAVY = (22, 40, 92)
GOLD = (255, 194, 61)

# ───────────────────────────── тайминги ─────────────────────────────


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def smooth(x):
    return x * x * (3 - 2 * x)


def ease_out(x, p=3):
    return 1 - (1 - x) ** p


def ease_in(x, p=3):
    return x ** p


def ease_io(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back_out(x, s=1.70158):
    c = s + 1
    return 1 + c * (x - 1) ** 3 + s * (x - 1) ** 2


def bump(t, c, w):
    return math.exp(-((t - c) / w) ** 2)


def elastic(x, f=3.0, d=4.0):
    """Затухающее колебание 0 → 0 (для «отдачи» после удара), x ∈ [0, 1]."""
    if x <= 0 or x >= 1:
        return 0.0
    return math.sin(2 * math.pi * f * x) * math.exp(-d * x)


def pattern(t, t0, bits, step=1 / FPS):
    """Мигание по шаблону '1101…' с t0 (вне шаблона — 1)."""
    if t < t0:
        return 1.0
    i = int((t - t0) / step)
    return 1.0 if i >= len(bits) else float(bits[i] == '1')


# ───────────────────────────── растр: маски, градиенты, композиция ─────────────────────────────

def P(v):
    return v * SS


def font(name, px, wght=None, wdth=None):
    """Шрифт размером px (в пикселях того холста, на котором рисуем)."""
    f = ImageFont.truetype(os.path.join(FD, name), max(4, int(px)))
    try:
        if wdth is not None:
            f.set_variation_by_axes([wdth, wght])
        elif wght is not None:
            f.set_variation_by_axes([wght])
    except Exception:  # noqa: BLE001 — статичный шрифт
        pass
    return f


MONT = ('Montserrat[wght].ttf', 900, None)
MONT_I = ('Montserrat-Italic[wght].ttf', 900, None)
COMF = ('Comfortaa[wght].ttf', 700, None)
LOBSTER = ('Lobster-Regular.ttf', None, None)
RUSSO = ('RussoOne-Regular.ttf', None, None)
DELA = ('DelaGothicOne-Regular.ttf', None, None)
CAVEAT = ('Caveat[wght].ttf', 700, None)
UNB = ('Unbounded[wght].ttf', 800, None)
PIXEL = 'PressStart2P-Regular.ttf'


def F(spec, px):
    return font(spec[0], px, spec[1], spec[2])


def newL(w, h, ss=SS):
    return Image.new('L', (w * ss, h * ss), 0)


def dr(m):
    return ImageDraw.Draw(m)


def down(m, ss=SS):
    """Маска PIL L (в ss×) → float 0…1 в 1×."""
    return np.asarray(m.reduce(ss) if ss > 1 else m, np.float32) / 255


def arr(m):
    return np.asarray(m, np.float32) / 255


def _box(a, r, axis):
    n = a.shape[axis]
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad), axis=axis, dtype=np.float32)
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return (hi - lo) / (2 * r + 1)


def gblur(a, s):
    """Гауссово размытие (три прохода «коробкой») по первым двум осям; s — сигма в пикселях."""
    if s <= 0.3:
        return a
    r = max(1, int(round((math.sqrt(4 * s * s + 1) - 1) / 2)))
    for _ in range(3):
        a = _box(_box(a, r, 0), r, 1)
    return a


def shift(a, dx, dy):
    o = np.zeros_like(a)
    h, w = a.shape[:2]
    dx, dy = int(round(dx)), int(round(dy))
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    o[yd, xd] = a[ys, xs]
    return o


def col3(c):
    return np.array(c[:3], np.float32) / 255


def paint(m, c, a=1.0):
    """Маска m (H, W) + цвет (кортеж 0…255 или массив (H, W, 3) 0…1) → слой RGBA с предумноженной альфой."""
    al = m * a
    rgb = (col3(c) if isinstance(c, tuple) else c) * al[..., None]
    return np.dstack([rgb, al]).astype(np.float32)


def over(top, bot):
    return top + bot * (1 - top[..., 3:4])


def blank(w, h):
    return np.zeros((h, w, 4), np.float32)


def screen(rgb, add):
    return 1 - (1 - rgb) * (1 - np.clip(add, 0, 1))


def mixc(c, k):
    t = (255, 255, 255) if k > 0 else (0, 0, 0)
    k = abs(k)
    return tuple(int(round(a + (b - a) * k)) for a, b in zip(c[:3], t))


_GRID = {}


def grid(w, h, ss=1):
    """Координаты центров пикселей в «пикселях 1×»."""
    k = (w, h, ss)
    if k not in _GRID:
        y, x = np.mgrid[0:h * ss, 0:w * ss].astype(np.float32)
        _GRID[k] = ((x + 0.5) / ss, (y + 0.5) / ss)
    return _GRID[k]


def ramp(t, stops):
    if not isinstance(stops[0][0], (int, float)) or len(stops[0]) == 3:
        stops = [(i / (len(stops) - 1), c) for i, c in enumerate(stops)]
    out = np.empty(t.shape + (3,), np.float32)
    ts = [s[0] for s in stops]
    for ch in range(3):
        out[..., ch] = np.interp(t, ts, [s[1][ch] / 255 for s in stops])
    return out


def lin(w, h, stops, p0, p1, ss=1):
    x, y = grid(w, h, ss)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    t = np.clip(((x - p0[0]) * dx + (y - p0[1]) * dy) / (dx * dx + dy * dy), 0, 1)
    return ramp(t, stops)


def radial(w, h, stops, c, r, ss=1):
    x, y = grid(w, h, ss)
    return ramp(np.clip(np.hypot(x - c[0], y - c[1]) / r, 0, 1), stops)


def bevel(m, d=2.0, b=1.2):
    """→ (свет, тень): кромки внутри маски сверху-слева и снизу-справа."""
    hi = np.clip(m - shift(m, d * 0.6, d), 0, 1)
    lo = np.clip(m - shift(m, -d * 0.6, -d), 0, 1)
    return gblur(hi, b) * m, gblur(lo, b) * m


def rings(w, h, c, step, ss=1):
    """Узор Versus: концентрические кольца (0…1)."""
    x, y = grid(w, h, ss)
    r = np.hypot(x - c[0], y - c[1])
    return np.clip(np.sin(r / step * 2 * np.pi) * 3, 0, 1)


def noise(w, h, cell, seed, ss=1):
    """Плавный шум 0…1 с размером ячейки cell px."""
    rng = np.random.default_rng(seed)
    lo = rng.random((max(2, h // cell + 2), max(2, w // cell + 2)))
    im = Image.fromarray((lo * 255).astype(np.uint8), 'L').resize((w * ss + cell * 2 * ss, h * ss + cell * 2 * ss),
                                                                    Image.BICUBIC)
    return np.asarray(im, np.float32)[cell * ss // 2:cell * ss // 2 + h * ss, cell * ss // 2:cell * ss // 2 + w * ss] / 255


def text_fit(text, spec, maxw, maxh, stroke=0):
    """Кегль (в 2×), при котором «чернила» текста влезают в maxw×maxh (px 1×)."""
    lo, hi = 4, int(P(maxh) * 2.2)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        f = F(spec, mid)
        l, t, r, b = f.getbbox(text, stroke_width=P(stroke), anchor='ls')
        if r - l <= P(maxw) and b - t <= P(maxh):
            lo = mid
        else:
            hi = mid
    return lo


def text_L(w, h, text, spec, cx, cy, size=None, maxw=None, maxh=None, stroke=0, fill=255, cap=False):
    """Маска текста в 2× (PIL L): центр «чернил» в (cx, cy) px 1×. size — кегль в 2× (иначе — по maxw×maxh).
    cap=True — центр по высоте заглавной «Н» (а не по чернилам; строки с Й/Ё и хвостами встают ровно)."""
    size = size or text_fit(text, spec, maxw, maxh, stroke)
    f = F(spec, size)
    m = newL(w, h)
    d = dr(m)
    l, t, r, b = d.textbbox((0, 0), text, font=f, anchor='ls', stroke_width=P(stroke))
    if cap:
        _, t, _, b = d.textbbox((0, 0), 'Н', font=f, anchor='ls')
    d.text((P(cx) - (l + r) / 2, P(cy) - (t + b) / 2), text, font=f, anchor='ls', fill=fill,
           stroke_width=P(stroke), stroke_fill=fill)
    return m


def letters_L(w, h, text, spec, cx, cy, size):
    """Маски отдельных букв строки (в 2×) — для неона, где буквы мигают по одной."""
    f = F(spec, size)
    tmp = dr(newL(1, 1))
    l, t, r, b = tmp.textbbox((0, 0), text, font=f, anchor='ls')
    x0, y0 = P(cx) - (l + r) / 2, P(cy) - (t + b) / 2
    out = []
    for i, ch in enumerate(text):
        if ch == ' ':
            continue
        m = newL(w, h)
        dr(m).text((x0 + f.getlength(text[:i]), y0), ch, font=f, anchor='ls', fill=255)
        out.append(m)
    return out


def poly_L(w, h, pts, width, closed=False, frac=1.0, fill=255, m=None):
    """Ломаная толщиной width px с круглыми концами и стыками (в 2×); frac — доля длины (дорисовка)."""
    m = m or newL(w, h)
    pts = list(pts) + ([pts[0]] if closed else [])
    if frac < 1:
        pts = part(pts, frac)
    if len(pts) < 2:
        return m
    d = dr(m)
    q = [(P(x), P(y)) for x, y in pts]
    d.line(q, fill=fill, width=int(P(width)), joint='curve')
    rr = P(width) / 2
    for x, y in (q[0], q[-1]):
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=fill)
    return m


def part(pts, f):
    """Начальная доля f ломаной по длине."""
    L = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    tot, goal, out = sum(L), sum(L) * clamp(f), [pts[0]]
    for (a, b), l in zip(zip(pts, pts[1:]), L):
        if goal <= 0:
            break
        if l <= goal:
            out.append(b)
            goal -= l
        else:
            k = goal / l
            out.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
            goal = 0
    return out if tot > 0 else pts[:1]


def ellipse_L(w, h, cx, cy, rx, ry=None, m=None, fill=255):
    m = m or newL(w, h)
    ry = rx if ry is None else ry
    dr(m).ellipse((P(cx - rx), P(cy - ry), P(cx + rx), P(cy + ry)), fill=fill)
    return m


def rrect_L(w, h, box, r, m=None, fill=255):
    m = m or newL(w, h)
    dr(m).rounded_rectangle(tuple(P(v) for v in box), radius=P(r), fill=fill)
    return m


def polygon_L(w, h, pts, m=None, fill=255):
    m = m or newL(w, h)
    dr(m).polygon([(P(x), P(y)) for x, y in pts], fill=fill)
    return m


def star_pts(cx, cy, ro, ri, n=5, rot=-90):
    return [(cx + (ro if i % 2 == 0 else ri) * math.cos(math.radians(rot + i * 180 / n)),
             cy + (ro if i % 2 == 0 else ri) * math.sin(math.radians(rot + i * 180 / n))) for i in range(2 * n)]


def heart_pts(cx, cy, s, n=72):
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        out.append((cx + x * s, cy - y * s))
    return out


def to_rgba_img(a):
    """Слой с предумноженной альфой (2×) → PIL 'RGBa' для поворотов/масштаба без тёмной каймы."""
    return Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8), 'RGBa')


def xf(img, w, h, ang=0.0, k=1.0, cx=256, cy=256, dx=0.0, dy=0.0, kx=None, ky=None, ss=SS):
    """PIL 'RGBa'/'L' в ss× → слой 1× (w×h): поворот ang° по часовой, масштаб вокруг (cx, cy) px, сдвиг."""
    kx = k if kx is None else kx
    ky = k if ky is None else ky
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    a, b, d, e = c / kx, s / kx, -s / ky, c / ky
    X, Y = (cx + dx) * ss, (cy + dy) * ss
    data = (a, b, cx * ss - a * X - b * Y, d, e, cy * ss - d * X - e * Y)
    o = img.transform((w * ss, h * ss), Image.AFFINE, data, resample=Image.BICUBIC)
    if ss > 1:
        o = o.reduce(ss)
    return np.asarray(o, np.float32) / 255


def half(a):
    """Слой 2× → 1× (среднее 2×2, для предумноженной альфы — корректно)."""
    h, w = a.shape[0] // 2, a.shape[1] // 2
    return a.reshape(h, 2, w, 2, -1).mean(axis=(1, 3)) if a.ndim == 3 else a.reshape(h, 2, w, 2).mean(axis=(1, 3))


def diecut(a, width=7, shadow=0.34):
    """Вырубка стикера: белая обводка ~width px по силуэту (без слабых свечений) и мягкая тень вниз."""
    al = a[..., 3]
    core = np.clip((al - 0.3) / 0.4, 0, 1)
    d = gblur(core, width / 1.645)
    o = np.maximum(np.clip((d - 0.035) / 0.07, 0, 1), core)
    sh = shift(gblur(o, 6), 0, 5)
    base = over(paint(o, (255, 255, 255)), paint(sh, (8, 10, 20), shadow))
    return over(a, base)


PUCK_C = (200, 96)            # центр верхней плоскости шайбы в спрайте (px 1×; спрайт 800×400 — это 2×)
PUCK_RX = 160                 # полуширина шайбы в спрайте (px 1×)


def puck_sprite(rim=GOLD):
    """Шайба семейства эмодзи (make.puck3d) → PIL 'RGBa' 800×400 (2×)."""
    art = mk.new()
    mk.puck3d(art, 50, 44, 40, 15, 12, rim=rim)
    return art.crop((0, 160, 800, 560)).convert('RGBa')


def puck_at(sprite, w, h, x, y, rx, ang=0.0):
    """Шайба с центром верхней плоскости в (x, y), полуширина rx px, поворот ang°."""
    return xf(sprite, w, h, ang=ang, k=rx / PUCK_RX, cx=PUCK_C[0], cy=PUCK_C[1], dx=x - PUCK_C[0], dy=y - PUCK_C[1])


# ───────────────────────────── 1. НЕОН ─────────────────────────────

class Neon:
    """Неоновая вывеска на тёмной кирпичной стене (широкая плашка). Трубки — буквы Comfortaa (моно-линия, как
    гнутое стекло), белая сердцевина, двойное свечение и отсвет на стене. Буквы мигают по одной."""

    def __init__(self, sp):
        self.sp = sp
        W, H = self.W, self.H = 512, sp.get('h', 300)
        box = (20, 20, W - 20, H - 24)
        self.bm = down(rrect_L(W, H, box, 30))
        inner = down(rrect_L(W, H, (box[0] + 7, box[1] + 7, box[2] - 7, box[3] - 7), 24))
        wall = lin(W, H, [(40, 34, 52), (22, 20, 32), (12, 11, 18)], (0, box[1]), (0, box[3]))
        # кирпич: швы через 26 px, вертикальные — со сдвигом через ряд
        x, y = grid(W, H)
        row = np.floor((y - box[1]) / 26)
        hor = np.exp(-(((y - box[1]) % 26) - 0.5) ** 2 / 2.0)
        ver = np.exp(-(((x + (row % 2) * 30) % 60) - 0.5) ** 2 / 2.0)
        mortar = np.clip(hor + ver, 0, 1)
        wall = wall * (1 - 0.45 * mortar[..., None])
        wall = wall * (0.92 + 0.12 * noise(W, H, 40, 7)[..., None])
        frame_m = np.clip(self.bm - inner, 0, 1)
        fr = lin(W, H, [(150, 152, 170), (70, 70, 84), (36, 36, 44)], (0, box[1]), (0, box[3]))
        hi, lo = bevel(frame_m, 1.5, 0.8)
        rgb = wall * (1 - frame_m[..., None]) + fr * frame_m[..., None]
        rgb = screen(rgb, hi[..., None] * 0.6)
        rgb = rgb * (1 - lo[..., None] * 0.5)
        sh = gblur(np.clip(inner - shift(inner, 0, 6), 0, 1), 3) * inner
        rgb = rgb * (1 - sh[..., None] * 0.6)
        for sx, sy in ((box[0] + 22, box[1] + 22), (box[2] - 22, box[1] + 22), (box[0] + 22, box[3] - 22),
                       (box[2] - 22, box[3] - 22)):
            sm = down(ellipse_L(W, H, sx, sy, 6))
            sl = down(poly_L(W, H, [(sx - 4, sy + 2), (sx + 4, sy - 2)], 1.6))
            rgb = rgb * (1 - sm[..., None]) + (lin(W, H, [(190, 190, 200), (80, 80, 92)], (sx - 6, sy - 6), (sx + 6, sy + 6))
                                              * sm[..., None])
            rgb = rgb * (1 - sl[..., None] * 0.7)
        jm = down(text_L(W, H, 'JARVIS', UNB, box[2] - 50, box[3] - 18, maxw=50, maxh=8))
        rgb = rgb * (1 - jm[..., None]) + col3((120, 110, 150)) * jm[..., None]
        self.wall = rgb
        self.inner = inner
        self.els = []                                    # (маска, цвет, группа)
        for line in sp['lines']:
            text, spec, cx, cy, mw, mh, col = line
            size = text_fit(text, spec, mw, mh)
            for m in letters_L(W, H, text, spec, cx, cy, size):
                self.add(down(m), col)
        self.n_text = len(self.els)
        self.anim = sp['anim']
        self.dyn = {}

    def add(self, m, col):
        self.els.append(self._prep(m, col))

    @staticmethod
    def _prep(m, col):
        core = np.clip((gblur(m, 1.6) - 0.62) / 0.3, 0, 1) * m
        g1, g2 = gblur(m, 4.5), gblur(m, 16)
        return dict(m=m, core=core, g1=g1, g2=g2, col=col3(col), c=col)

    def compose(self, items):
        """items: [(элемент, яркость 0…1)] → кадр."""
        rgb = self.wall.copy()
        spill = np.zeros_like(rgb)
        for e, I in items:
            if I <= 0.01:
                continue
            spill += (e['g2'] * 0.75 + e['g1'] * 0.9)[..., None] * e['col'] * I
        rgb = screen(rgb, spill * 0.85)
        for e, I in items:
            on = 0.55 * e['col'] + 0.45
            off = 0.2 * e['col'] + 0.1
            tube = off * (1 - I) + on * I
            m = e['m'][..., None]
            rgb = rgb * (1 - m) + tube * m
            rgb = screen(rgb, (e['core'] * I * 0.9)[..., None] * np.ones(3, np.float32))
            hi = np.clip(e['m'] - shift(e['m'], 1, 2), 0, 1) * (1 - I) * 0.35       # блик на холодном стекле
            rgb = screen(rgb, hi[..., None])
        rgb = screen(rgb, spill * 0.18)
        return np.dstack([rgb * self.bm[..., None], self.bm])

    def frame(self, t):
        return getattr(self, 'a_' + self.anim)(t)

    def hum(self, t, k=0):
        d = self.sp['dur']
        return 0.93 + 0.05 * math.sin(2 * math.pi * (4 * t / d + k * 0.37)) + 0.02 * math.sin(2 * math.pi * (11 * t / d + k))

    def text_items(self, t, over_=None):
        over_ = over_ or {}
        return [(e, self.hum(t, i) * over_.get(i, 1.0)) for i, e in enumerate(self.els[:self.n_text])]

    def icon(self, key, pts, width, col, frac=1.0, closed=False):
        k = (key, round(frac, 3))
        if k not in self.dyn:
            self.dyn[k] = self._prep(down(poly_L(self.W, self.H, pts, width, closed=closed, frac=frac)), col)
        return self.dyn[k]

    # — сценарии —
    def a_check(self, t):
        sp = self.sp
        off = 1 - smooth(seg(t, 0.85, 0.95))
        draw = ease_io(seg(t, 1.05, 1.5))
        fl = {sp['flick']: pattern(t, 2.05, '1101100111011110001110')}
        items = self.text_items(t, fl)
        I = self.hum(t, 9)
        if t < 1.0:
            items.append((self.icon('i', sp['icon'], 15, sp['icol']), I * off))
        elif draw > 0:
            items.append((self.icon('i', sp['icon'], 15, sp['icol'], frac=draw), I))
        return self.compose(items)

    def a_cross(self, t):
        sp = self.sp
        dying = pattern(t % 1.5, 0.3, '1110110111111001011101111111011010111')
        items = self.text_items(t, {sp['flick']: dying})
        I = self.hum(t, 5) * pattern(t, 1.6, '10010011')
        a, b = sp['icon']
        items.append((self.icon('a', a, 15, sp['icol']), I))
        items.append((self.icon('b', b, 15, sp['icol']), I * pattern(t, 1.62, '1001101')))
        return self.compose(items)

    def a_chevrons(self, t):
        sp = self.sp
        items = self.text_items(t, {sp['flick']: pattern(t, 2.2, '110100111')})
        n = len(sp['chev'])
        for k, pts in enumerate(sp['chev']):
            ph = (t / sp['dur'] * 3 - k / n) % 1.0
            I = 0.18 + 0.82 * (math.exp(-(ph / 0.16) ** 2) + math.exp(-((ph - 1) / 0.16) ** 2))
            items.append((self.icon('c%d' % k, pts, 13, sp['icol']), min(1.0, I)))
        return self.compose(items)

    def a_heart(self, t):
        sp = self.sp
        items = self.text_items(t, {sp['flick']: pattern(t, 1.3, '1011001111')})
        b = bump(t % 1.0, 0.12, 0.05) + 0.6 * bump(t % 1.0, 0.3, 0.05)
        cx, cy, s = sp['heart']
        k = round(1 + 0.16 * b, 2)
        items.append((self.icon(('h', k), heart_pts(cx, cy, s * k), 11, sp['icol'], closed=True), 0.75 + 0.25 * b))
        return self.compose(items)


NEON_GREEN, NEON_RED, NEON_CYAN, NEON_PINK, NEON_ORANGE = (60, 255, 140), (255, 52, 72), (70, 220, 255), \
    (255, 80, 190), (255, 150, 40)


def _chev(cx, cy, w, h, up=True):
    s = -1 if up else 1
    return [(cx - w, cy - s * h / 2), (cx, cy + s * h / 2), (cx + w, cy - s * h / 2)]


# ───────────────────────────── 2. LED-ТАБЛО ─────────────────────────────

def px_text(text, scale=1):
    """Текст пиксельным шрифтом Press Start 2P: bool-массив (7·scale строк)."""
    f = ImageFont.truetype(os.path.join(FD, PIXEL), 8)
    im = Image.new('1', (8 * len(text) + 8, 12))
    d = ImageDraw.Draw(im)
    d.fontmode = '1'
    d.text((0, 0), text, font=f, fill=1)
    a = np.asarray(im)[0:7]
    cols = np.where(a.any(axis=0))[0]
    a = a[:, :cols.max() + 1] if len(cols) else a[:, :1]
    if scale > 1:
        a = a.repeat(scale, 0).repeat(scale, 1)
    return a


CHEV_BITS = np.array([[1, 1, 0, 0, 0], [0, 1, 1, 0, 0], [0, 0, 1, 1, 0], [0, 0, 0, 1, 1],
                      [0, 0, 1, 1, 0], [0, 1, 1, 0, 0], [1, 1, 0, 0, 0]], bool)
PLUS_BITS = np.array([[0, 0, 1, 0, 0], [0, 0, 1, 0, 0], [1, 1, 1, 1, 1], [0, 0, 1, 0, 0], [0, 0, 1, 0, 0]], bool)


def disc_bits(d):
    y, x = np.mgrid[0:d, 0:d]
    c = (d - 1) / 2
    return np.hypot(x - c, y - c) <= d / 2 - 0.2


class Led:
    """Табло: корпус-«коробка» с болтами, чёрная панель с LED-точками (горят цветом, в центре — белая сердцевина,
    свечение). Содержимое — сетка rows×cols на кадр."""

    def __init__(self, sp):
        self.sp = sp
        self.cols, self.rows, self.p = sp['cols'], sp['rows'], sp['pitch']
        pw, ph = self.cols * self.p, self.rows * self.p
        top = sp.get('top', 0)
        self.W = 512
        H = top + ph + 18 + 36 + 2 * 22
        self.H = H = H + H % 2                       # yuva420p — чётные стороны
        W = self.W
        hx0 = (W - pw) // 2 - 12
        hy0 = 22 + top
        box = (hx0, hy0, W - hx0, hy0 + ph + 18 + 36)
        self.px0, self.py0 = (W - pw) // 2, hy0 + 18
        self.box = box
        hm = down(rrect_L(W, H, box, 20))
        body = lin(W, H, [(74, 78, 90), (44, 46, 54), (24, 25, 30)], (0, box[1]), (0, box[3]))
        body = body * (0.95 + 0.07 * noise(W, H, 6, 11)[..., None])
        hi, lo = bevel(hm, 2.2, 1.2)
        rgb = screen(body, hi[..., None] * 0.55) * (1 - lo[..., None] * 0.55)
        pm = down(rrect_L(W, H, (self.px0 - 6, self.py0 - 6, self.px0 + pw + 6, self.py0 + ph + 6), 8))
        rgb = rgb * (1 - pm[..., None]) + col3((6, 6, 8)) * pm[..., None]
        lip = np.clip(pm - shift(pm, 0, 3), 0, 1)
        rgb = rgb * (1 - gblur(lip, 1.5)[..., None] * 0.8)
        for bx, by in ((box[0] + 22, box[3] - 16), (box[2] - 22, box[3] - 16)):
            bm = down(ellipse_L(W, H, bx, by, 4.5))
            rgb = rgb * (1 - bm[..., None]) + lin(W, H, [(200, 200, 210), (70, 70, 80)], (bx - 4, by - 4),
                                                  (bx + 4, by + 4)) * bm[..., None]
        jm = down(text_L(W, H, 'JARVIS', UNB, W / 2, box[3] - 18, maxw=86, maxh=12))
        jsh = shift(jm, 0, 1)
        rgb = rgb * (1 - jsh[..., None] * 0.7)
        rgb = rgb * (1 - jm[..., None]) + lin(W, H, [(255, 226, 140), (200, 150, 50)], (0, box[3] - 26),
                                              (0, box[3] - 10)) * jm[..., None]
        self.base = np.dstack([rgb * hm[..., None], hm])
        self.hm = hm
        self.pm = pm
        p = self.p
        y, x = np.mgrid[0:p, 0:p].astype(np.float32)
        d = np.hypot(x + 0.5 - p / 2, y + 0.5 - p / 2)
        self.k_core = np.clip((0.43 * p - d) / 0.9 + 0.5, 0, 1)
        self.k_hot = np.exp(-(d / (0.2 * p)) ** 2)
        self.init_extra()

    def grid_img(self, G):
        """G (rows, cols, 3) 0…1 → панель (ph, pw, 3) + свечение (на весь кадр)."""
        r, c, p = self.rows, self.cols, self.p
        lit = G.repeat(p, 0).repeat(p, 1)
        core = np.tile(self.k_core, (r, c))[..., None]
        hot = np.tile(self.k_hot, (r, c))[..., None]
        mx = G.max(axis=2).repeat(p, 0).repeat(p, 1)[..., None]
        img = lit * core + hot * mx * 0.55 + (1 - mx) * core * col3((34, 34, 40))
        return img, lit * core

    def compose(self, G, overlay=None):
        img, light = self.grid_img(np.clip(G, 0, 1))
        a = self.base.copy()
        y0, x0 = self.py0, self.px0
        h, w = img.shape[:2]
        rgb = a[..., :3]
        rgb[y0:y0 + h, x0:x0 + w] = img
        glow = np.zeros_like(rgb)
        glow[y0:y0 + h, x0:x0 + w] = light
        g = gblur(glow, 2.4) * 0.8 + gblur(glow, 7) * 0.55
        rgb[:] = screen(rgb, g * self.hm[..., None])
        a[..., :3] = rgb * self.hm[..., None]
        return a if overlay is None else (a, overlay)

    def put(self, G, bits, x, y, color, k=1.0):
        h, w = bits.shape
        r0, c0 = max(0, y), max(0, x)
        r1, c1 = min(self.rows, y + h), min(self.cols, x + w)
        if r1 <= r0 or c1 <= c0:
            return
        sub = bits[r0 - y:r1 - y, c0 - x:c1 - x]
        G[r0:r1, c0:c1][sub] = col3(color) * k

    def center_x(self, bits):
        return (self.cols - bits.shape[1]) // 2

    def frame(self, t):
        G = np.zeros((self.rows, self.cols, 3), np.float32)
        return getattr(self, 'a_' + self.sp['anim'])(t, G)

    # — сценарии —
    def a_gol(self, t, G):
        bits = px_text('ГОЛ!', 2)
        x, y = self.center_x(bits), (self.rows - bits.shape[0]) // 2
        flash = t < 1.0 and int(t * 8) % 2 == 1
        col = (255, 214, 40) if flash else (255, 40, 40)
        self.put(G, bits, x, y, col)
        if t >= 1.0:                                     # блик-диагональ по буквам
            yy, xx = np.mgrid[0:self.rows, 0:self.cols]
            band = np.exp(-(((xx + yy * 0.8) - (-10 + 110 * seg(t, 1.05, 1.75))) / 4.0) ** 2)
            on = G.max(axis=2) > 0
            G[on] = G[on] * (1 - band[on, None]) + band[on, None]
        # бегущая рамка
        per = []
        r, c = self.rows, self.cols
        per += [(0, j) for j in range(c)] + [(i, c - 1) for i in range(1, r)]
        per += [(r - 1, j) for j in range(c - 2, -1, -1)] + [(i, 0) for i in range(r - 2, 0, -1)]
        sh = int(t * FPS * 0.5)
        for n, (i, j) in enumerate(per):
            if (n + sh) % 4 == 0:
                G[i, j] = col3((255, 214, 40))
        body, halo = self.lamp(t)
        a = self.compose(G)
        return over(body, a), halo

    def init_extra(self):
        if self.sp['anim'] != 'gol':
            return
        W, H = self.W, self.H
        cx, top = W / 2, self.box[1]
        self.lamp_c = (cx, top - 30)
        base = down(rrect_L(W, H, (cx - 34, top - 14, cx + 34, top + 4), 4))
        dome = down(ellipse_L(W, H, cx, top - 14, 28, 30))
        dome = dome * (grid(W, H)[1] <= top - 14)
        self.lamp_base = paint(base, lin(W, H, [(170, 170, 180), (60, 60, 70)], (0, top - 14), (0, top + 4)))
        self.dome = dome

    def lamp(self, t):
        """Мигалка гола над табло: красный купол, внутри бегает отражатель; когда он смотрит на нас — вспышка."""
        W, H = self.W, self.H
        x, y = grid(W, H)
        cx, cy = self.lamp_c
        th = 2 * math.pi * t / self.sp['dur'] * 2
        bx = cx + 22 * math.sin(th)
        face = max(0.0, math.cos(th)) ** 2
        beam = np.exp(-((x - bx) / (10 + 8 * face)) ** 2)
        base = lin(W, H, [(255, 110, 100), (200, 20, 30), (110, 0, 10)], (cx - 20, cy - 20), (cx + 20, cy + 16))
        rgb = screen(base, (beam * (0.6 + 0.4 * face))[..., None] * col3((255, 220, 200)))
        hi = np.exp(-(((x - cx + 12) / 7) ** 2 + ((y - cy + 10) / 9) ** 2)) * 0.6
        rgb = screen(rgb, hi[..., None])
        dome = paint(self.dome, rgb)
        halo = gblur(self.dome, 18) * (0.25 + 0.75 * face) * (1 - self.dome)
        return over(dome, self.lamp_base), paint(np.clip(halo * 1.4, 0, 0.7), (255, 40, 40))

    def a_ticker(self, t, G):
        top = px_text(self.sp['text'])
        self.put(G, top, self.center_x(top), 2, self.sp['col'])
        sh = int(round(t / self.sp['dur'] * 24))
        for k in range(-2, self.cols // 8 + 2):
            x = k * 8 + sh
            ph = (k % 3)
            self.put(G, CHEV_BITS, x, 11, self.sp['col2'], 0.45 + 0.55 * (ph == 0) + 0.25 * (ph == 1))
        return self.compose(G)

    def a_bars(self, t, G):
        top = px_text(self.sp['text'])
        self.put(G, top, self.center_x(top), 1, self.sp['col'])
        heights = (2, 3, 3, 4, 5, 5, 6, 7, 8)
        n = len(heights)
        x0 = (self.cols - (n * 7 - 1)) // 2
        drop = ease_in(seg(t, 2.55, 2.85), 2)
        for i, hgt in enumerate(heights):
            g = back_out(seg(t, 0.1 + 0.12 * i, 0.45 + 0.12 * i), 2.2) * (1 - drop)
            hh = int(round(hgt * g))
            if hh <= 0:
                continue
            bits = np.ones((hh, 6), bool)
            k = 0.6 + 0.4 * (i == n - 1) * (0.5 + 0.5 * math.cos(2 * math.pi * t * 3))
            self.put(G, bits, x0 + i * 7, self.rows - 1 - hh, self.sp['col2'], k)
        return self.compose(G)

    def a_lamps(self, t, G):
        top = px_text(self.sp['text'])
        self.put(G, top, self.center_x(top), 1, self.sp['col'])
        res = self.sp['res']
        n = len(res)
        d = disc_bits(7)
        gap = (self.cols - n * 7) // (n + 1)
        x0 = (self.cols - (n * 7 + (n - 1) * gap)) // 2
        off = ease_in(seg(t, 2.6, 2.85), 1)
        for i, r in enumerate(res):
            on = seg(t, 0.15 + 0.32 * i, 0.2 + 0.32 * i)
            col = (60, 255, 110) if r == 'g' else (255, 50, 50)
            blink = 1.0
            if r == 'g' and 1.9 < t < 2.5:
                blink = 0.35 + 0.65 * (int((t - 1.9) * 10) % 2 == 0)
            k = on * (1 - off) * blink
            self.put(G, d, x0 + i * (7 + gap), 10, (50, 50, 60), 0.6)
            if k > 0:
                self.put(G, d, x0 + i * (7 + gap), 10, col, k)
        return self.compose(G)

    def a_plus(self, t, G):
        bits = px_text(self.sp['text'], 2)
        x, y = self.center_x(bits), (self.rows - bits.shape[0]) // 2
        self.put(G, bits, x, y, self.sp['col'])
        yy, xx = np.mgrid[0:self.rows, 0:self.cols]
        band = np.exp(-(((xx - yy * 0.7) - (-14 + 100 * seg(t, 0.3, 1.2))) / 4.5) ** 2)
        on = G.max(axis=2) > 0
        G[on] = G[on] * (1 - 0.8 * band[on, None]) + 0.8 * band[on, None]
        small = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)
        rng = random.Random(3)
        for i in range(10):
            xv, yv = rng.randrange(1, self.cols - 4), rng.choice((0, self.rows - 3))
            k = math.sin(math.pi * ((t / self.sp['dur'] * 2 + i / 10) % 1.0)) ** 2
            if k > 0.05:
                self.put(G, small, xv, yv, (255, 255, 255) if i % 3 == 0 else self.sp['col'], k)
        return self.compose(G)


# ───────────────────────────── 3. ЛЁД: круглый значок с лентой ─────────────────────────────

class Ice:
    W = H = 512
    C, R = (256, 228), 190

    def __init__(self, sp):
        self.sp = sp
        W, H, (cx, cy), R = self.W, self.H, self.C, self.R
        rng = random.Random(sp.get('seed', 3))
        S2 = SS
        disc = down(ellipse_L(W, H, cx, cy, R))
        face = down(ellipse_L(W, H, cx, cy, R - 15))
        self.face = face
        rim = np.clip(disc - face, 0, 1)
        fc = radial(W, H, [(0, (242, 251, 255)), (0.5, (176, 220, 247)), (1.0, (88, 152, 214))],
                    (cx - 60, cy - 70), R * 1.45)
        n1 = noise(W, H, 34, rng.randrange(999))
        n2 = noise(W, H, 9, rng.randrange(999))
        fc = screen(fc, (np.clip(n1 - 0.45, 0, 1) * 0.5 + np.clip(n2 - 0.6, 0, 1) * 0.4)[..., None])
        fc = fc * (1 - 0.035 * rings(W, H, (cx - 120, cy - 150), 9)[..., None])
        # трещины
        cr = newL(W, H)
        d = dr(cr)
        for _ in range(9):
            a = rng.uniform(0, 2 * math.pi)
            rr = rng.uniform(0.2, 0.85) * R
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
            pts = [(x, y)]
            ang = rng.uniform(0, 2 * math.pi)
            for _ in range(rng.randint(3, 6)):
                ang += rng.uniform(-0.7, 0.7)
                x += math.cos(ang) * rng.uniform(14, 34)
                y += math.sin(ang) * rng.uniform(14, 34)
                pts.append((x, y))
            d.line([(P(px), P(py)) for px, py in pts], fill=255, width=P(1) + 1)
        crack = down(cr) * face
        fc = screen(fc, crack[..., None] * 0.75)
        fc = fc * (1 - shift(crack, 1, 1.5)[..., None] * 0.25)
        # иней по кромке
        fr = newL(W, H)
        d = dr(fr)
        for i in range(84):
            a = 2 * math.pi * i / 84 + rng.uniform(-0.02, 0.02)
            ln = rng.uniform(8, 26)
            r0 = R - 15
            x0, y0 = cx + r0 * math.cos(a), cy + r0 * math.sin(a)
            x1, y1 = cx + (r0 - ln) * math.cos(a), cy + (r0 - ln) * math.sin(a)
            d.line((P(x0), P(y0), P(x1), P(y1)), fill=190, width=int(P(1.4)))
            for s in (-1, 1):
                k = rng.uniform(0.35, 0.6)
                xm, ym = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
                b = a + math.pi + s * 0.7
                d.line((P(xm), P(ym), P(xm + 7 * math.cos(b)), P(ym + 7 * math.sin(b))), fill=150, width=P(1))
        fc = screen(fc, (down(fr) * face)[..., None] * 0.8)
        ins = gblur(np.clip(face - shift(face, 2, 5), 0, 1), 4) * face
        fc = fc * (1 - ins[..., None] * 0.35)
        rc = lin(W, H, [(250, 254, 255), (196, 222, 242), (120, 160, 200), (64, 100, 150)], (cx - R, cy - R),
                 (cx + R, cy + R))
        hi, lo = bevel(rim, 2.0, 1.0)
        rc = screen(rc, hi[..., None] * 0.7) * (1 - lo[..., None] * 0.45)
        rgb = fc * face[..., None] + rc * rim[..., None]
        self.disc = np.dstack([rgb, disc])
        # лента с надписью
        y0, y1 = 336, 404
        tail_l = [(18, y0 + 18), (74, y0 + 18), (74, y1 + 16), (18, y1 + 16), (36, (y0 + y1) / 2 + 17)]
        tail_r = [(W - x, y) for x, y in tail_l]
        tails = down(polygon_L(W, H, tail_r, m=polygon_L(W, H, tail_l)))
        fold = down(polygon_L(W, H, [(74, y1), (74, y1 + 16), (56, y1)],
                              m=polygon_L(W, H, [(W - 74, y1), (W - 74, y1 + 16), (W - 56, y1)])))
        band = down(polygon_L(W, H, [(56, y0), (W - 56, y0), (W - 56, y1), (56, y1)]))
        rc = sp.get('ribbon', NAVY)
        lay = paint(tails, lin(W, H, [mixc(rc, -0.2), mixc(rc, -0.5)], (0, y0), (0, y1 + 16)))
        lay = over(paint(fold, mixc(rc, -0.65)), lay)
        bc = lin(W, H, [mixc(rc, 0.28), rc, mixc(rc, -0.3)], (0, y0), (0, y1))
        hi, lo = bevel(band, 1.6, 0.8)
        bc = screen(bc, hi[..., None] * 0.5) * (1 - lo[..., None] * 0.4)
        x, y = grid(W, H)
        st = ((np.abs(y - (y0 + 7)) < 0.9) | (np.abs(y - (y1 - 7)) < 0.9)) & ((x % 12) < 7)
        bc = screen(bc, (st * band * 0.45)[..., None])
        lay = over(paint(band, bc), lay)
        tm = down(text_L(W, H, sp['text'], MONT, W / 2, (y0 + y1) / 2 + 1, maxw=356, maxh=40, cap=True))
        lay = over(paint(gblur(shift(tm, 1, 3), 1.2), (0, 0, 0), 0.5), lay)
        lay = over(paint(tm, lin(W, H, [(255, 255, 255), (214, 232, 250)], (0, y0 + 10), (0, y1 - 10))), lay)
        self.ribbon = lay
        self.flakes = [(rng.uniform(cx - R, cx + R), rng.uniform(0, 1), rng.uniform(1.4, 3.0), rng.uniform(0, 6.28))
                       for _ in range(18)]
        self.sparks = [(cx + rng.uniform(-0.75, 0.75) * R, cy + rng.uniform(-0.8, 0.45) * R, rng.uniform(7, 13),
                        rng.uniform(0, 1)) for _ in range(5)]
        getattr(self, 'i_' + sp['icon'])()

    # — общие эффекты —
    def fx(self, t, lay):
        W, H = self.W, self.H
        dur = self.sp['dur']
        x, y = grid(W, H)
        pos = -260 + 620 * seg(t, self.sp.get('shine', 0.25), self.sp.get('shine', 0.25) + 0.75)
        band = np.exp(-(((x - self.C[0]) * 0.8 + (y - self.C[1]) * 0.6 - pos) / 26) ** 2) * self.face
        rgb = screen(lay[..., :3], (band * 0.55)[..., None] * lay[..., 3:4])
        lay = np.dstack([rgb, lay[..., 3]])
        m = newL(W, H)
        d = dr(m)
        for fx_, fy, r, ph in self.flakes:
            yy = (fy + t / dur) % 1.0
            py = self.C[1] - self.R + yy * 2 * self.R
            px = fx_ + 6 * math.sin(2 * math.pi * (t / dur) + ph)
            d.ellipse((P(px - r), P(py - r), P(px + r), P(py + r)), fill=200)
        sp = newL(W, H)
        ds = dr(sp)
        for sx, sy, r, ph in self.sparks:
            k = math.sin(math.pi * ((t / dur * 2 + ph) % 1.0)) ** 4
            if k > 0.02:
                ds.polygon([(P(px), P(py)) for px, py in star_pts(sx, sy, r * k, r * k * 0.18, 4, -90)], fill=255)
        snow = down(m) * self.face
        spk = down(sp)
        a = over(paint(snow, (255, 255, 255), 0.8), lay)
        return over(paint(spk, (255, 255, 255)), a), spk

    def frame(self, t):
        icon = getattr(self, 'f_' + self.sp['icon'])(t)
        lay = over(icon[0], self.disc) if icon[0] is not None else self.disc
        lay, spk = self.fx(t, lay)
        lay = over(self.ribbon, lay)
        if icon[1] is not None:
            lay = over(icon[1], lay)
        glow = gblur(spk, 4)
        return over(paint(np.clip(glow * 2, 0, 0.8), (230, 245, 255)), lay)

    # — значки —
    def i_zero(self):
        W, H = self.W, self.H
        cx, cy = self.C[0], self.C[1] - 30
        self.zc = (cx, cy)
        st = arr(text_L(W, H, '0', MONT, cx, cy, maxw=230, maxh=176, stroke=10))
        fi = arr(text_L(W, H, '0', MONT, cx, cy, size=text_fit('0', MONT, 230, 176, 10)))
        lay = paint(st, NAVY)
        g = lin(W, H, [(255, 255, 255), (200, 232, 252), (128, 190, 236)], (0, cy - 80), (0, cy + 80), ss=SS)
        lay = over(paint(fi, g), lay)
        hl = np.clip(fi - shift(fi, 4, 7), 0, 1)
        lay = over(paint(gblur(hl, 2), (255, 255, 255), 0.7), lay)
        self.zero = to_rgba_img(lay)
        self.puck = puck_sprite(rim=(150, 200, 240))

    def f_zero(self, t):
        W, H = self.W, self.H
        cx, cy = self.zc
        hit = 1.25
        e = elastic(seg(t, hit, hit + 0.6), 2.5, 4.5)
        z = xf(self.zero, W, H, ang=7 * e, cx=cx, cy=cy, dx=5 * e)
        out = None
        if 0.85 < t < 1.75:                          # шайба: влёт слева-снизу → удар в «0» → отскок вверх-влево
            if t < hit:
                q = ease_in(seg(t, 0.85, hit), 1.6)
                px, py = 40 + (cx - 84 - 40) * q, 330 + (cy + 10 - 330) * q
                ang = -30 + 200 * q
                vx, vy = (cx - 8) / 0.4, (cy + 10 - 330) / 0.4
            else:
                q = ease_out(seg(t, hit, 1.75), 1.4)
                px, py = cx - 84 - 150 * q, cy + 10 - 150 * q + 120 * q * q
                ang = 170 + 260 * q
                vx, vy = -260 / 0.5, -170 / 0.5
            pl = puck_at(self.puck, W, H, px, py, 36, ang * 0.15)
            pl = pl * (smooth(seg(t, 0.85, 0.95)) * (1 - smooth(seg(t, 1.6, 1.75))))
            sp_v = math.hypot(vx, vy)
            m = newL(W, H)
            d = dr(m)
            ux, uy = -vx / sp_v, -vy / sp_v
            for off in (-9, 0, 9):
                ox, oy = -uy * off, ux * off
                d.line((P(px + ox + ux * 22), P(py + oy + uy * 22), P(px + ox + ux * 90), P(py + oy + uy * 90)),
                       fill=180, width=P(3))
            streak = paint(down(m), (255, 255, 255), 0.7 * smooth(seg(t, 0.85, 0.95)) * (1 - smooth(seg(t, 1.5, 1.7))))
            out = over(pl, streak)
        if hit <= t < hit + 0.7:                     # осколки льда
            q = seg(t, hit, hit + 0.7)
            m = newL(W, H)
            d = dr(m)
            rng = random.Random(5)
            for i in range(10):
                a = math.radians(rng.uniform(110, 250))
                v = rng.uniform(90, 200)
                x = cx - 70 + math.cos(a) * v * q
                y = cy + 10 + math.sin(a) * v * q + 160 * q * q
                s = rng.uniform(4, 9) * (1 - q)
                d.polygon([(P(x), P(y - s)), (P(x + s * 0.7), P(y + s * 0.6)), (P(x - s * 0.8), P(y + s * 0.4))],
                          fill=255)
            sh = paint(down(m), (240, 250, 255))
            out = sh if out is None else over(out, sh)
        return z, out

    def _clock_face(self, r, ticks=12):
        W, H = self.W, self.H
        cx, cy = self.C[0], self.C[1] - 36
        self.cc = (cx, cy)
        ring = arr(ellipse_L(W, H, cx, cy, r + 10))
        face = arr(ellipse_L(W, H, cx, cy, r))
        lay = paint(ring, lin(W, H, [(80, 110, 170), NAVY], (cx - r, cy - r), (cx + r, cy + r), ss=SS))
        lay = over(paint(face, radial(W, H, [(255, 255, 255), (220, 236, 250)], (cx - 20, cy - 20), r * 1.3, ss=SS)),
                   lay)
        m = newL(W, H)
        d = dr(m)
        for i in range(ticks):
            a = 2 * math.pi * i / ticks
            r0 = r - (16 if i % 3 == 0 else 10)
            d.line((P(cx + r0 * math.sin(a)), P(cy - r0 * math.cos(a)), P(cx + (r - 4) * math.sin(a)),
                    P(cy - (r - 4) * math.cos(a))), fill=255, width=P(5 if i % 3 == 0 else 3))
        lay = over(paint(arr(m), NAVY), lay)
        return lay

    def i_clock(self):
        lay = self._clock_face(70)
        cx, cy = self.cc
        h = poly_L(self.W, self.H, [(cx, cy), (cx - 30, cy - 18)], 9)
        lay = over(paint(arr(h), NAVY), lay)
        self.clock = half(lay)

    def _hand(self, ang, ln, w, col, tail=12):
        cx, cy = self.cc
        a = math.radians(ang)
        m = poly_L(self.W, self.H, [(cx - tail * math.sin(a), cy + tail * math.cos(a)),
                                    (cx + ln * math.sin(a), cy - ln * math.cos(a))], w)
        return paint(down(m), col)

    def _cap(self, col=(230, 50, 60)):
        cx, cy = self.cc
        return paint(down(ellipse_L(self.W, self.H, cx, cy, 8)), col)

    def f_clock(self, t):
        ang = 360 * t / self.sp['dur']
        sh = shift(self._hand(ang, 58, 6, NAVY), 2, 3)
        sh[..., :3] = 0
        lay = over(self._hand(ang, 58, 6, NAVY), over(sh * 0.3, self.clock))
        return over(self._cap(), lay), None

    def i_arrow(self):
        W, H = self.W, self.H
        cx, cy = self.C[0], self.C[1] - 36
        self.cc = (cx, cy)
        r = 62
        pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(-60, 215, 5)]
        a1 = math.radians(-60)
        tip = (cx + r * math.cos(a1), cy + r * math.sin(a1))
        tx, ty = -math.sin(a1), math.cos(a1)                 # касательная по ходу (против часовой — к концу)
        nx, ny = math.cos(a1), math.sin(a1)
        head = [(tip[0] + nx * 26 + tx * 4, tip[1] + ny * 26 + ty * 4), (tip[0] - nx * 26 + tx * 4, tip[1] - ny * 26 + ty * 4),
                (tip[0] - tx * 30, tip[1] - ty * 30)]
        body = poly_L(W, H, pts[::-1][:-1], 26)
        polygon_L(W, H, head, m=body)
        b = arr(body)
        ob = np.clip(gblur(b, 9) * 3, 0, 1)
        lay = paint(ob, NAVY)
        lay = over(paint(b, lin(W, H, [(255, 255, 255), (190, 225, 250)], (cx - r, cy - r), (cx + r, cy + r), ss=SS)),
                   lay)
        hi = np.clip(b - shift(b, 3, 5), 0, 1)
        lay = over(paint(gblur(hi, 2), (255, 255, 255), 0.8), lay)
        self.arrow = to_rgba_img(lay)

    def f_arrow(self, t):
        x = seg(t, 0.35, 1.55)
        ang = -360 * ease_io(x)
        ang += -10 * elastic(seg(t, 1.55, 2.2), 2, 5)
        cx, cy = self.cc
        return xf(self.arrow, self.W, self.H, ang=ang, cx=cx, cy=cy), None

    def i_watch(self):
        W, H = self.W, self.H
        lay = self._clock_face(66, ticks=60 // 5)
        cx, cy = self.cc
        crown = arr(rrect_L(W, H, (cx - 12, cy - 98, cx + 12, cy - 80), 3))
        stem = arr(rrect_L(W, H, (cx - 6, cy - 84, cx + 6, cy - 72), 2))
        btn = arr(poly_L(W, H, [(cx + 52, cy - 52), (cx + 64, cy - 64)], 12))
        metal = lin(W, H, [(230, 236, 246), (120, 140, 170)], (cx - 20, cy - 100), (cx + 60, cy - 50), ss=SS)
        lay = over(lay, paint(np.maximum(np.maximum(crown, stem), btn), metal))
        self.watch = half(lay)
        x, y = grid(W, H)
        self.wa = (np.degrees(np.arctan2(x - cx, -(y - cy))) % 360, np.hypot(x - cx, y - cy))

    def f_watch(self, t):
        ang = 360 * t / self.sp['dur']
        a, r = self.wa
        d = (ang - a) % 360
        wedge = (d < 80) * np.clip((80 - d) / 80, 0, 1) * np.clip((62 - r) / 2, 0, 1)
        lay = over(paint(wedge, (240, 60, 70), 0.55), self.watch)
        lay = over(self._hand(ang, 56, 5, (220, 40, 50), tail=14), lay)
        return over(self._cap(NAVY), lay), None


# ───────────────────────────── 4. ПЕЧАТЬ на купоне ─────────────────────────────

class Stamp:
    W, H = 512, 448

    def __init__(self, sp):
        self.sp = sp
        W, H = self.W, self.H
        rng = random.Random(sp.get('seed', 1))
        # купон 2× (без поворота) → поворот один раз
        w2, h2 = W * SS, H * SS
        x0, y0, x1, y1 = 72, 40, 440, 400
        self.slip_box = (x0, y0, x1, y1)
        m = Image.new('L', (w2, h2), 0)
        d = dr(m)
        teeth = 14
        pts = [(P(x0), P(y0)), (P(x1), P(y0))]
        n = int((x1 - x0) / teeth)
        for i in range(n, -1, -1):
            x = x0 + i * (x1 - x0) / n
            pts.append((P(x), P(y1 - (6 if i % 2 else 0))))
        d.polygon(pts, fill=255)
        for i in range(12):                                   # перфорация по верху
            cxh = x0 + 20 + i * (x1 - x0 - 40) / 11
            d.ellipse((P(cxh - 3), P(y0 + 50), P(cxh + 3), P(y0 + 56)), fill=0)
        sm = arr(m)
        paper = lin(W, H, [(252, 250, 243), (240, 236, 224)], (0, y0), (0, y1), ss=SS)
        paper = paper * (0.97 + 0.04 * noise(W, H, 3, 4, ss=SS)[..., None])
        lay = paint(sm, paper)
        head = arr(rrect_L(W, H, (x0 + 12, y0 + 12, x1 - 12, y0 + 44), 6))
        lay = over(paint(head, lin(W, H, [(40, 52, 92), (24, 32, 62)], (0, y0), (0, y0 + 44), ss=SS)), lay)
        lay = over(paint(arr(text_L(W, H, 'JARVIS', UNB, x0 + 62, y0 + 28, maxw=80, maxh=12)), (255, 255, 255)), lay)
        lay = over(paint(arr(text_L(W, H, 'ПРОГНОЗ', MONT, x1 - 64, y0 + 28, maxw=90, maxh=12, cap=True)), GOLD), lay)
        g = newL(W, H)
        d = dr(g)
        for i in range(5):
            yy = y0 + 84 + i * 50
            d.ellipse((P(x0 + 24), P(yy - 6), P(x0 + 36), P(yy + 6)), fill=150)
            d.rounded_rectangle((P(x0 + 48), P(yy - 6), P(x0 + 48 + rng.randint(140, 220)), P(yy + 6)), P(4), fill=110)
            d.rounded_rectangle((P(x1 - 74), P(yy - 6), P(x1 - 26), P(yy + 6)), P(4), fill=150)
            if i < 4:
                for k in range(int((x1 - x0 - 48) / 12)):
                    d.line((P(x0 + 24 + k * 12), P(yy + 25), P(x0 + 30 + k * 12), P(yy + 25)), fill=70, width=P(1))
        lay = over(paint(arr(g), (120, 116, 108)), lay)
        self.slip = Image.fromarray(np.clip(lay * 255 + 0.5, 0, 255).astype(np.uint8), 'RGBa').rotate(
            sp.get('slip_rot', 3), resample=Image.BICUBIC, center=(W, H))
        sl = np.asarray(self.slip.reduce(SS), np.float32) / 255
        self.slip1 = sl
        # оттиск: маска 2× с «грязью» краски
        cx, cy = self.sc = (W / 2 + sp.get('dx', 0), (y0 + y1) / 2 + 22 + sp.get('dy', 0))
        im = self.round_seal(cx, cy) if sp['shape'] == 'round' else self.rect_seal(cx, cy)
        base = arr(im)
        rough = gblur(base, 1.6) + (noise(W, H, 5, rng.randrange(999), ss=SS) - 0.5) * 0.55
        ink = np.clip((rough - 0.45) / 0.12, 0, 1) * base.clip(0, 1)
        holes = noise(W, H, 3, rng.randrange(999), ss=SS)
        ink = ink * np.clip(1 - (holes - 0.72) / 0.08, 0, 1)
        ink = ink * (0.86 + 0.14 * noise(W, H, 22, rng.randrange(999), ss=SS))
        self.ink = Image.fromarray((np.clip(ink, 0, 1) * 255).astype(np.uint8), 'L')
        self.foot = Image.fromarray((np.clip(gblur(base, 22) * 2.2, 0, 1) * 255).astype(np.uint8), 'L')
        self.icol = col3(sp['col'])
        self.drops = [(rng.uniform(0, 2 * math.pi), rng.uniform(120, 190), rng.uniform(2.5, 5.5)) for _ in range(9)]

    def rect_seal(self, cx, cy):
        W, H = self.W, self.H
        w, h = self.sp.get('size', (330, 150))
        m = newL(W, H)
        d = dr(m)
        box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        d.rounded_rectangle(tuple(P(v) for v in box), P(16), outline=255, width=P(8))
        d.rounded_rectangle(tuple(P(v) for v in (box[0] + 14, box[1] + 14, box[2] - 14, box[3] - 14)), P(8),
                            outline=255, width=P(3))
        t = text_L(W, H, self.sp['text'], RUSSO, cx, cy + 2, maxw=w - 64, maxh=h - 76, cap=True)
        m.paste(255, (0, 0), t)
        for k in (-1, 0, 1):
            star = star_pts(cx + k * 26, box[1] + 26, 8, 3.4)
            dr(m).polygon([(P(x), P(y)) for x, y in star], fill=255)
        j = text_L(W, H, 'JARVIS', UNB, cx, box[3] - 25, maxw=70, maxh=9)
        m.paste(255, (0, 0), j)
        m = m.rotate(-self.sp.get('rot', -10), resample=Image.BICUBIC, center=(P(cx), P(cy)))
        return m

    def round_seal(self, cx, cy):
        W, H = self.W, self.H
        R = self.sp.get('r', 140)
        m = newL(W, H)
        d = dr(m)
        for r, wd in ((R, 7), (R - 36, 3)):
            d.ellipse((P(cx - r), P(cy - r), P(cx + r), P(cy + r)), outline=255, width=P(wd))
        # текст по кругу
        txt = self.sp['arc']
        f = F(RUSSO, P(19))
        tot = sum(f.getlength(ch) for ch in txt)
        rr = R - 19
        circ = 2 * math.pi * P(rr)
        k = circ / tot
        a = -90.0 - 360 * f.getlength(txt[0]) / 2 / tot
        for ch in txt:
            wch = f.getlength(ch) * k
            mid = a + 360 * (wch / 2) / circ
            if ch != ' ':
                g = Image.new('L', (P(40), P(40)), 0)
                dr(g).text((P(20), P(20)), ch, font=f, fill=255, anchor='mm')
                g = g.rotate(-(mid + 90), resample=Image.BICUBIC)
                px = P(cx) + P(rr) * math.cos(math.radians(mid))
                py = P(cy) + P(rr) * math.sin(math.radians(mid))
                m.paste(255, (int(px - P(20)), int(py - P(20))), g)
            a += 360 * wch / circ
        bw, bh = R - 30, 34
        d.rectangle((P(cx - bw - 6), P(cy - bh), P(cx + bw + 6), P(cy + bh)), fill=0)
        d.line((P(cx - bw - 4), P(cy - bh), P(cx + bw + 4), P(cy - bh)), fill=255, width=P(4))
        d.line((P(cx - bw - 4), P(cy + bh), P(cx + bw + 4), P(cy + bh)), fill=255, width=P(4))
        t = text_L(W, H, self.sp['text'], RUSSO, cx, cy + 1, maxw=2 * bw - 16, maxh=40, cap=True)
        m.paste(255, (0, 0), t)
        for sy in (cy - bh - 24, cy + bh + 24):
            dr(m).polygon([(P(x), P(y)) for x, y in star_pts(cx, sy, 11, 4.6)], fill=255)
            for s in (-1, 1):
                dr(m).polygon([(P(x), P(y)) for x, y in star_pts(cx + s * 30, sy + (4 if sy > cy else -4) * 0, 7, 3)],
                              fill=255)
        m = m.rotate(-self.sp.get('rot', -10), resample=Image.BICUBIC, center=(P(cx), P(cy)))
        return m

    def frame(self, t):
        W, H = self.W, self.H
        cx, cy = self.sc
        hit = 0.45
        sq = elastic(seg(t, hit, hit + 0.5), 2.0, 5.0)
        slip = self.slip1 if abs(sq) < 1e-3 else xf(self.slip, W, H, kx=1 + 0.02 * sq, ky=1 - 0.035 * sq,
                                                     cx=W / 2, cy=self.slip_box[3])
        rgb, al = slip[..., :3].copy(), slip[..., 3:4]
        if t < hit:                                     # тень подлетающей печати
            q = seg(t, 0.12, hit)
            if q > 0:
                k = 1.0 + 0.35 * (1 - ease_in(q, 2))
                fm = xf(self.foot, W, H, k=k, cx=cx, cy=cy, dx=10 * (1 - q), dy=14 * (1 - q))
                fm = gblur(fm, 10 * (1 - q) + 3)
                rgb = rgb * (1 - (fm * 0.17 * ease_in(q, 1.5))[..., None])
        else:
            fade = 1 - smooth(seg(t, 2.55, 2.88))
            k = 1 + 0.05 * ease_out(1 - seg(t, hit, hit + 0.12), 2)
            ink = xf(self.ink, W, H, k=k, cx=cx, cy=cy) * fade
            m = ink[..., None]
            rgb = rgb * (1 - m) + rgb * self.icol * m       # «умножение» краски на бумагу
            q = seg(t, hit, hit + 0.35)
            if 0 < q < 1:
                dm = newL(W, H)
                d = dr(dm)
                for a, v, r in self.drops:
                    x = cx + math.cos(a) * (v + 60 * ease_out(q))
                    y = cy + math.sin(a) * (v * 0.6 + 40 * ease_out(q))
                    rr = r * (1 - q * 0.4)
                    d.ellipse((P(x - rr), P(y - rr), P(x + rr), P(y + rr)), fill=255)
                dmm = down(dm)[..., None] * (1 - q) * al
                rgb = rgb * (1 - dmm) + rgb * self.icol * dmm
        return np.dstack([rgb, al[..., 0]])


# ───────────────────────────── 5. ФЛАГ на древке ─────────────────────────────

FLAG_WAVES = ((8.5, 300, 10, 1, 0.0, 1.0), (3.0, 170, -14, 2, 1.7, 0.5), (1.1, 105, 24, 3, 4.1, 0.25))


class Flag:
    W, H = 512, 400

    def __init__(self, sp):
        self.sp = sp
        W, H = self.W, self.H
        self.fx0, self.fy0, self.fw, self.fh = 54, 46, 436, 250
        fw, fh = self.fw, self.fh
        PADF = 24
        tw, th = fw + 2 * PADF, fh + 2 * PADF
        self.PADF = PADF
        c1, c2, tc = sp['col'], sp['col2'], sp.get('tcol', (255, 255, 255))
        # плоская ткань в 2× (с запасом PADF по краям — цвет края продолжается)
        x, y = grid(tw, th, SS)
        u, v = x - PADF, y - PADF
        base = lin(tw, th, [mixc(c1, 0.18), c1, mixc(c1, -0.35)], (PADF, PADF), (PADF + fw * 0.6, PADF + fh), ss=SS)
        stripe = np.abs((u * 0.55 + v) - (fh * 0.95)) < 26
        stripe2 = np.abs((u * 0.55 + v) - (fh * 0.95 + 46)) < 7
        s = (stripe | stripe2)[..., None]
        base = base * (1 - s) + lin(tw, th, [mixc(c2, 0.3), c2, mixc(c2, -0.3)], (0, PADF), (0, PADF + fh), ss=SS) * s
        rg = rings(tw, th, (PADF + fw * 0.95, PADF - 20), 9, ss=SS)
        base = screen(base, (rg * 0.06)[..., None])
        sleeve = (u < 16)[..., None]
        base = base * (1 - sleeve * 0.35)
        lay = paint(np.ones(base.shape[:2], np.float32), base)
        lines = sp['lines']
        for text, cy, mh, spec in lines:
            tm = arr(text_L(tw, th, text, spec, PADF + 16 + (fw - 16) / 2, PADF + cy, maxw=fw - 90, maxh=mh, cap=True))
            ol = np.clip(gblur(tm, 3.5) * 4, 0, 1)
            lay = over(paint(gblur(shift(ol, 5, 8), 3), (0, 0, 0), 0.45), lay)
            lay = over(paint(ol, mixc(c1, -0.7)), lay)
            lay = over(paint(tm, lin(tw, th, [mixc(tc, 0.4), tc, mixc(tc, -0.12)], (0, PADF + cy - mh / 2),
                                     (0, PADF + cy + mh / 2), ss=SS)), lay)
        if sp.get('star'):
            sx, sy = PADF + fw - 46, PADF + 40
            st = arr(polygon_L(tw, th, star_pts(sx, sy, 22, 9)))
            lay = over(paint(st, lin(tw, th, [(255, 240, 170), GOLD, (200, 130, 20)], (sx - 20, sy - 20),
                                     (sx + 20, sy + 20), ss=SS)), over(paint(gblur(shift(st, 2, 3), 2), (0, 0, 0), 0.4), lay))
        jm = arr(text_L(tw, th, 'JARVIS', UNB, PADF + fw - 46, PADF + fh - 18, maxw=54, maxh=8))
        lay = over(paint(jm, (255, 255, 255), 0.55), lay)
        self.tex = lay                                    # 2×, предумноженная
        # поле выборки в 1× (для каждого пикселя кадра): u, v относительно левого-верхнего угла ткани
        X, Y = grid(W, H, SS)
        self.U, self.V = X - self.fx0, Y - self.fy0
        q = np.clip(self.U / fw, 0, 1)
        self.env = (0.06 + 0.94 * q ** 1.15).astype(np.float32)
        # древко и навершие
        px = self.fx0 - 8
        pole = down(rrect_L(W, H, (px - 7, 30, px + 7, 370), 6))
        knob = down(ellipse_L(W, H, px, 28, 14))
        pc = lin(W, H, [(110, 80, 30), (255, 226, 140), (210, 160, 60), (110, 80, 30)], (px - 7, 0), (px + 7, 0))
        kc = radial(W, H, [(255, 246, 200), GOLD, (150, 100, 20)], (px - 5, 22), 18)
        self.pole = over(paint(knob, kc), paint(pole, pc))

    def frame(self, t):
        W, H = self.W, self.H
        tau = t / self.sp['dur']
        U, V, env = self.U, self.V, self.env
        z = np.zeros_like(U)
        zq = np.zeros_like(U)
        slope = np.zeros_like(U)
        smax = 0.0
        for amp, lam, ang, n, ph, wl in FLAG_WAVES:
            kx = math.cos(math.radians(ang)) / lam
            ky = math.sin(math.radians(ang)) / lam
            p = (np.float32(2 * math.pi * kx) * U + np.float32(2 * math.pi * ky) * V
                 + np.float32((ph - 2 * math.pi * n * tau) % (2 * math.pi)))
            s, c = np.sin(p), np.cos(p)
            z += amp * s
            zq += amp * c
            g = wl * amp * 2 * math.pi * (0.85 * kx + 0.5 * ky)
            slope += np.float32(g) * c
            smax += abs(g)
        us = U - 0.16 * env * zq
        vs = V - env * z
        tex = self.tex
        th, tw = tex.shape[:2]
        sx = (us + self.PADF) * SS - 0.5
        sy = (vs + self.PADF) * SS - 0.5
        x0 = np.clip(np.floor(sx).astype(np.int32), 0, tw - 2)
        y0 = np.clip(np.floor(sy).astype(np.int32), 0, th - 2)
        fx = np.clip(sx - x0, 0, 1)[..., None]
        fy = np.clip(sy - y0, 0, 1)[..., None]
        a = tex[y0, x0]
        b = tex[y0, x0 + 1]
        c = tex[y0 + 1, x0]
        d = tex[y0 + 1, x0 + 1]
        smp = (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy
        sl = env * slope / smax
        shade = (1 + 0.2 * (sl + 0.3 * np.maximum(sl, 0) ** 2))[..., None]
        spec = (0.18 * np.clip(sl, 0, None) ** 3)[..., None]
        dist = np.minimum(np.minimum(us, self.fw - us), np.minimum(vs, self.fh - vs)) * SS
        al = np.clip(dist + 0.5, 0, 1)[..., None]
        rgb = smp[..., :3] * shade + spec
        out = np.concatenate([rgb * al, al], axis=2)
        out = half(out)
        return over(self.pole, out)


# ───────────────────────────── 6. КОМИКС-ВЗРЫВ ─────────────────────────────

class Comic:
    W = H = 512

    def __init__(self, sp):
        self.sp = sp
        W, H = self.W, self.H
        cx, cy = self.c = (256, 252)
        rng = random.Random(sp.get('seed', 2))
        sx, sy = sp.get('stretch', (1.0, 1.0))
        n = sp.get('spikes', 15)
        ro = [rng.uniform(196, 226) for _ in range(n)]
        ri = [rng.uniform(140, 162) for _ in range(n)]
        self.bursts = []
        c1, c2 = sp['col'], sp['col2']
        for v in range(3):
            j = random.Random(100 + v)
            pts, inner = [], []
            for i in range(n):
                a0 = 2 * math.pi * i / n + j.uniform(-0.04, 0.04)
                a1 = 2 * math.pi * (i + 0.5) / n + j.uniform(-0.04, 0.04)
                r0, r1 = ro[i] + j.uniform(-9, 9), ri[i] + j.uniform(-6, 6)
                pts += [(cx + r1 * math.cos(a0) * sx, cy + r1 * math.sin(a0) * sy),
                        (cx + r0 * math.cos(a1) * sx, cy + r0 * math.sin(a1) * sy)]
                inner += [(cx + r1 * 0.66 * math.cos(a0) * sx, cy + r1 * 0.66 * math.sin(a0) * sy),
                          (cx + r0 * 0.7 * math.cos(a1 + 0.1) * sx, cy + r0 * 0.7 * math.sin(a1 + 0.1) * sy)]
            bm = arr(polygon_L(W, H, pts))
            ol = np.clip(gblur(bm, 8) * 3.2, 0, 1)
            x, y = grid(W, H, SS)
            dist = np.hypot((x - cx) / sx, (y - cy) / sy) / 220
            gx, gy = (x * 0.7 - y * 0.7), (x * 0.7 + y * 0.7)
            cell = 13
            dx, dy = (gx % cell) - cell / 2, (gy % cell) - cell / 2
            rdot = cell * 0.5 * np.clip(dist * 1.15 - 0.3, 0, 1)
            dots = np.clip((rdot - np.hypot(dx, dy)) * 2, 0, 1)
            fill = radial(W, H, [mixc(c1, 0.35), c1, mixc(c1, -0.1)], (cx - 60, cy - 80), 260, ss=SS)
            fill = fill * (1 - dots[..., None]) + col3(c2) * dots[..., None] * 0.95 + fill * dots[..., None] * 0.05
            lay = paint(ol, (16, 14, 20))
            lay = over(paint(bm, fill), lay)
            im = arr(polygon_L(W, H, inner))
            lay = over(paint(im, (255, 255, 255), 0.22), lay)
            self.bursts.append(to_rgba_img(lay))
        # слова: объём (выдавливание), чёрная обводка, заливка
        tl = []
        for text, cyo, mh in sp['lines']:
            tm = text_L(W, H, text, DELA, cx, cy + cyo, maxw=sp.get('tw', 370), maxh=mh, cap=True)
            tl.append(arr(tm))
        tm = np.maximum.reduce(tl)
        ol = np.clip(gblur(tm, 5) * 3.5, 0, 1)
        lay = blank(W * SS, H * SS)
        for k in range(12, 0, -1):
            lay = over(paint(shift(ol, P(k * 0.6), P(k)), (16, 14, 20)), lay)
        for k in range(10, 0, -1):
            lay = over(paint(shift(tm, P(k * 0.6), P(k)), mixc(sp['tex'], -0.35 - 0.02 * k)), lay)
        lay = over(paint(ol, (16, 14, 20)), lay)
        tc = sp.get('tcol', (255, 255, 255))
        lay = over(paint(tm, lin(W, H, [mixc(tc, 0.5), tc, mixc(tc, -0.15)], (0, cy - 60), (0, cy + 60), ss=SS)), lay)
        hl = np.clip(tm - shift(tm, P(2), P(4)), 0, 1)
        lay = over(paint(gblur(hl, 1.5), (255, 255, 255), 0.85), lay)
        self.text = to_rgba_img(lay)
        self.rot = sp.get('rot', -7)
        self.puck = puck_sprite() if sp.get('puck') else None
        self.rng = rng

    def frame(self, t):
        W, H = self.W, self.H
        cx, cy = self.c
        dur = self.sp['dur']
        v = int(t * FPS / 4) % 3
        kick = self.sp.get('kick', 0.0)
        imp = 0.0
        if kick:
            imp = elastic(seg(t, kick, kick + 0.7), 2.2, 4.5)
        beat = bump(t % (dur / 2), 0.0, 0.07) + bump(t % (dur / 2), dur / 2, 0.07)
        shake = self.sp.get('shake', 0.0)
        jx = shake * math.sin(t * 97.0) * math.sin(t * 13.0) if shake else 0.0
        jy = shake * math.sin(t * 71.0 + 1) * math.sin(t * 11.0) if shake else 0.0
        if kick and kick <= t < kick + 0.4:
            q = 1 - seg(t, kick, kick + 0.4)
            jx += 8 * q * math.sin(t * 120)
            jy += 6 * q * math.sin(t * 90)
        bk = 1 + 0.12 * imp + 0.025 * beat
        burst = xf(self.bursts[v], W, H, k=bk, cx=cx, cy=cy, dx=jx * 0.5, dy=jy * 0.5)
        tk = 1 + 0.16 * imp + 0.05 * beat
        text = xf(self.text, W, H, k=tk, ang=self.rot + 2 * imp, cx=cx, cy=cy, dx=jx, dy=jy)
        extra = getattr(self, 'x_' + self.sp.get('extra', 'none'))(t)
        mid = None
        if extra is not None and len(extra) == 3:
            back, mid, front = extra
        elif extra is not None:
            back, front = extra
        lay = over(text, burst if mid is None else over(mid, burst))
        if extra is not None:
            if back is not None:
                lay = over(lay, back)
            if front is not None:
                lay = over(front, lay)
        return lay

    def x_none(self, t):
        return None

    def x_puck(self, t):
        """Шайба влетает из левого нижнего угла в центр и «пробивает» взрыв (удар — kick)."""
        W, H = self.W, self.H
        kick = self.sp['kick']
        t0 = kick - 0.32
        if not (t0 <= t < kick + 0.6):
            return None
        front = None
        if t < kick:
            q = ease_in(seg(t, t0, kick), 1.5)
            px, py = -40 + (self.c[0] - 30 + 40) * q, 470 - (470 - self.c[1] - 20) * q
            pl = puck_at(self.puck, W, H, px, py, 62 - 26 * q, -20 + 40 * q)
            m = newL(W, H)
            d = dr(m)
            ux, uy = -(self.c[0] + 40), (470 - self.c[1])
            nn = math.hypot(ux, uy)
            ux, uy = ux / nn, uy / nn
            for off in (-14, 0, 14):
                ox, oy = -uy * off, ux * off
                d.line((P(px + ox + ux * 40), P(py + oy + uy * 40), P(px + ox + ux * 150), P(py + oy + uy * 150)),
                       fill=255, width=P(5))
            front = over(pl, paint(down(m), (16, 14, 20), 0.85))
        q = seg(t, kick, kick + 0.6)
        if q > 0:
            m = newL(W, H)
            d = dr(m)
            rng = random.Random(9)
            for i in range(12):
                a = 2 * math.pi * i / 12 + rng.uniform(-0.2, 0.2)
                r = 120 + 200 * ease_out(q, 2)
                x, y = self.c[0] + r * math.cos(a), self.c[1] + r * math.sin(a)
                s = (16 + rng.uniform(0, 8)) * (1 - q)
                d.polygon([(P(px_), P(py_)) for px_, py_ in star_pts(x, y, s, s * 0.45, 4, rng.uniform(0, 90))],
                          fill=255)
            st = down(m)
            sp = over(paint(st, (255, 236, 90)), paint(np.clip(gblur(st, 2) * 3, 0, 1), (16, 14, 20)))
            front = sp if front is None else over(front, sp)
        return None, front

    def particles(self, t, n, life, spawn, draw, seed=4):
        """Частицы с периодом жизни life (петля: dur кратно life/n)."""
        W, H = self.W, self.H
        m = newL(W, H)
        d = dr(m)
        rng = random.Random(seed)
        for i in range(n):
            ph = (t / life + i / n) % 1.0
            draw(d, i, ph, rng)
        return m

    def x_debris(self, t):
        W, H = self.W, self.H
        cx, cy = self.c

        def draw(d, i, q, rng):
            a = rng.uniform(0, 2 * math.pi)
            spin = rng.uniform(-6, 6)
            r = 170 + 140 * q
            x, y = cx + r * math.cos(a) * 1.1, cy + r * math.sin(a) * 0.9 + 60 * q * q
            s = rng.uniform(7, 13) * (1 - q ** 2)
            pts = [(x + s * math.cos(spin * q + k * 2.1), y + s * math.sin(spin * q + k * 2.1)) for k in range(3)]
            d.polygon([(P(px), P(py)) for px, py in pts], fill=255)
        m = down(self.particles(t, 14, 1.0, None, draw))
        ol = np.clip(gblur(m, 1.2) * 3, 0, 1)
        return over(paint(m, (255, 150, 40)), paint(ol, (16, 14, 20))), None

    def x_coins(self, t):
        """Золотые монеты вылетают из-за слова веером вверх и падают, вращаясь (ширина ∝ |cos|)."""
        W, H = self.W, self.H
        cx, cy = self.c
        im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        rng = random.Random(7)
        for i in range(7):
            q = (t / 1.0 + i / 7) % 1.0
            a = math.radians(rng.uniform(205, 335))
            v = rng.uniform(150, 220)
            x = cx + math.cos(a) * (90 + v * q)
            y = cy - 30 + math.sin(a) * (60 + v * q) + 280 * q * q
            r = 26 * (0.7 + 0.3 * smooth(seg(q, 0, 0.3)))
            sx = abs(math.cos(2 * math.pi * (q * 1.5 + i * 0.3))) * 0.85 + 0.15
            al = int(255 * smooth(seg(q, 0.0, 0.1)) * (1 - smooth(seg(q, 0.8, 1.0))))
            if al <= 0:
                continue
            for rr, c in ((r + 4, (16, 14, 20)), (r, (230, 160, 30)), (r * 0.78, (255, 212, 70)),
                          (r * 0.5, (255, 236, 140))):
                d.ellipse((P(x - rr * sx), P(y - rr), P(x + rr * sx), P(y + rr)), fill=c + (al,))
        a = np.asarray(im.reduce(SS), np.float32) / 255
        a[..., :3] *= a[..., 3:4]
        return None, a, None

    def x_embers(self, t):
        W, H = self.W, self.H
        cx, cy = self.c

        def draw(d, i, q, rng):
            x0 = cx + rng.uniform(-200, 200)
            x = x0 + 18 * math.sin(2 * math.pi * (q + rng.random()))
            y = cy + 150 - 340 * q
            s = rng.uniform(5, 10) * (1 - q)
            d.ellipse((P(x - s), P(y - s * 1.4), P(x + s), P(y + s)), fill=255)
        m = down(self.particles(t, 16, 1.0, None, draw, seed=6))
        lay = paint(np.clip(gblur(m, 4) * 1.5, 0, 0.7), (255, 80, 20))
        return None, over(paint(m, (255, 220, 80)), lay)


# ───────────────────────────── 7. ТАКТИЧЕСКАЯ ДОСКА: текст пишется сам ─────────────────────────────

class Board:
    W, H = 512, 384

    def __init__(self, sp):
        self.sp = sp
        W, H = self.W, self.H
        box = (18, 18, W - 18, H - 40)
        self.box = box
        fm = down(rrect_L(W, H, box, 18))
        inner = down(rrect_L(W, H, (box[0] + 11, box[1] + 11, box[2] - 11, box[3] - 11), 8))
        alu = lin(W, H, [(236, 238, 244), (170, 176, 188), (120, 126, 140), (200, 204, 214)], (0, box[1]), (0, box[3]))
        hi, lo = bevel(fm, 1.6, 0.8)
        alu = screen(alu, hi[..., None] * 0.6) * (1 - lo[..., None] * 0.4)
        wb = lin(W, H, [(255, 255, 255), (238, 242, 248)], (box[0], box[1]), (box[2], box[3]))
        x, y = grid(W, H)
        cxm = (box[0] + box[2]) / 2
        cym = (box[1] + box[3]) / 2
        mk_ = np.zeros_like(x)
        red = (np.abs(x - cxm) < 2.5).astype(np.float32)
        blue = ((np.abs(x - (cxm - 120)) < 3) | (np.abs(x - (cxm + 120)) < 3)).astype(np.float32)
        circ = (np.abs(np.hypot(x - cxm, y - cym) - 56) < 1.6).astype(np.float32)
        dots = sum(np.hypot(x - (cxm + s * 60), y - (cym + v * 60)) < 4 for s in (-1, 1) for v in (-1, 1)).astype(np.float32)
        wb = wb * (1 - (red * 0.16 + circ * 0.14 + dots * 0.16)[..., None] * (1 - col3((230, 60, 60))))
        wb = wb * (1 - (blue * 0.14)[..., None] * (1 - col3((60, 110, 230))))
        wb = wb * (1 - 0.05 * noise(W, H, 60, 3)[..., None])
        sh = gblur(np.clip(inner - shift(inner, 0, 4), 0, 1), 2) * inner
        wb = wb * (1 - sh[..., None] * 0.25)
        rgb = alu * (1 - inner[..., None]) + wb * inner[..., None]
        tray = down(rrect_L(W, H, (box[0] + 30, box[3] - 4, box[2] - 30, box[3] + 14), 5))
        tc = lin(W, H, [(210, 214, 222), (110, 116, 130)], (0, box[3] - 4), (0, box[3] + 14))
        a = np.dstack([rgb * fm[..., None], fm])
        a = over(a, paint(tray, tc))
        jm = down(text_L(W, H, 'JARVIS', UNB, box[2] - 48, box[1] + 30, maxw=50, maxh=8))
        a = over(paint(jm * inner, (150, 156, 170)), a)
        self.base = a
        self.inner = inner
        # строки текста маркером
        self.ink = []
        for text, cx, cy, mh, mw, colr in sp['lines']:
            m = arr(text_L(W, H, text, CAVEAT, cx, cy, maxw=mw, maxh=mh))
            m = half(m[..., None])[..., 0]
            cols = np.where(m.max(axis=0) > 0.1)[0]
            ys = (m * np.arange(H, dtype=np.float32)[:, None]).sum(0) / np.maximum(m.sum(0), 1e-6)
            self.ink.append(dict(m=m, x0=cols.min(), x1=cols.max(), ys=ys, col=colr))
        self.doodles = sp.get('doodles', [])
        self.marker_col = sp['lines'][0][5]

    def marker(self, x, y, col, k=1.0):
        """Маркер: колпачок цвета чернил, тело белое; кончик в (x, y), корпус уходит вправо-вниз."""
        W, H = self.W, self.H
        a = math.radians(-35)
        ux, uy = math.cos(a), -math.sin(a)
        body = poly_L(W, H, [(x + ux * 16, y + uy * 16), (x + ux * 110, y + uy * 110)], 22)
        tip = poly_L(W, H, [(x + ux * 3, y + uy * 3), (x + ux * 18, y + uy * 18)], 9)
        cap = poly_L(W, H, [(x + ux * 90, y + uy * 90), (x + ux * 116, y + uy * 116)], 24)
        bm, tm, cm = down(body), down(tip), down(cap)
        lay = paint(np.clip(gblur(bm, 5) * 1.0, 0, 1), (0, 0, 0), 0.18 * k)
        lay = over(paint(bm, lin(W, H, [(255, 255, 255), (200, 204, 214)], (x, y), (x + 20, y + 30))), lay)
        lay = over(paint(cm, col), lay)
        lay = over(paint(tm, (40, 40, 48)), lay)
        if k < 1:
            lay = lay * k
        return lay

    def frame(self, t):
        sp = self.sp
        W, H = self.W, self.H
        lay = self.base.copy()
        ew = 0.0
        erase = seg(t, 0.0, 0.32)
        if 0 < erase < 1:
            ew = self.box[0] - 80 + (self.box[2] - self.box[0] + 90) * ease_io(erase)
        x, y = grid(W, H)
        tw0, tw1 = sp.get('write', (0.42, 1.85))
        total = sum(e['x1'] - e['x0'] for e in self.ink)
        prog = ease_io(seg(t, tw0, tw1)) * total if t >= tw0 else (total if t < 0.32 else 0)
        pen = None
        for e in self.ink:
            span = e['x1'] - e['x0']
            p = clamp(prog / span) if span else 1
            prog -= span
            front = e['x0'] + p * (span + 4)
            vis = np.clip((front - x) / 4, 0, 1)
            if 0.32 > t > 0:
                vis = vis * np.clip((x - ew) / 70, 0, 1)
            m = e['m'] * vis
            lay = over(paint(m, e['col']), lay)
            if 0 < p < 1 and t >= tw0:
                fx = int(clamp(front, 0, W - 1))
                pen = (front, e['ys'][fx] + 2 * math.sin(t * 40), e['col'])
        for dd in self.doodles:
            pts, w, colr, (d0, d1) = dd
            f = ease_io(seg(t, d0, d1)) if t >= d0 else (1.0 if t < 0.32 else 0.0)
            if f <= 0:
                continue
            m = down(poly_L(W, H, pts, w, frac=f))
            if 0.32 > t > 0:
                m = m * np.clip((x - ew) / 70, 0, 1)
            lay = over(paint(m, colr), lay)
            if 0 < f < 1 and t >= d0:
                q = part(pts, f)[-1]
                pen = (q[0], q[1], colr)
        if pen is not None:
            lay = over(self.marker(pen[0], pen[1], pen[2]), lay)
        return lay


# ───────────────────────────── реестр стикеров ─────────────────────────────
# ключ → (стиль, параметры). dur — длительность петли, off — сдвиг старта (первый кадр — полная поза),
# emoji — эмодзи стикера (Telegram подсказывает стикер по нему), kw — слова поиска.

NAVY_INK, RED_INK, GREEN_INK, BLUE_INK, VIOLET_INK = (40, 60, 160), (214, 36, 46), (20, 150, 70), (30, 90, 200), \
    (96, 36, 160)

STICKERS = {
    'neon_zahod': ('neon', dict(
        dur=3.0, off=0.0, emoji='✅', kw=['заход', 'зашло', 'плюс', 'победа'], anim='check', flick=2,
        lines=[('ЗАХОД', COMF, 310, 152, 280, 92, NEON_GREEN)], icon=[(54, 150), (88, 186), (146, 112)],
        icol=NEON_GREEN)),
    'stamp_zahod': ('stamp', dict(
        dur=3.0, off=1.2, emoji='✅', kw=['заход', 'зашло', 'печать', 'купон'], shape='rect', text='ЗАХОД',
        col=GREEN_INK, rot=-9, seed=11)),
    'neon_minus': ('neon', dict(
        dur=3.0, off=0.0, emoji='❌', kw=['минус', 'не зашло', 'проигрыш'], anim='cross', flick=3,
        lines=[('МИНУС', COMF, 310, 152, 280, 92, NEON_RED)],
        icon=([(64, 116), (138, 190)], [(138, 116), (64, 190)]), icol=NEON_RED)),
    'stamp_minus': ('stamp', dict(
        dur=3.0, off=1.2, emoji='❌', kw=['минус', 'не зашло', 'печать'], shape='rect', text='МИНУС', col=RED_INK,
        rot=8, seed=12)),
    'ice_vozvrat': ('ice', dict(
        dur=3.0, off=2.3, emoji='🔁', kw=['возврат', 'ставка вернулась'], text='ВОЗВРАТ', icon='arrow', seed=4)),
    'stamp_vozvrat': ('stamp', dict(
        dur=3.0, off=1.2, emoji='🔁', kw=['возврат', 'печать'], shape='round', text='ВОЗВРАТ',
        arc='СТАВКА ВЕРНУЛАСЬ • JARVIS • ', col=BLUE_INK, rot=-12, r=138, seed=13)),
    'flag_stavka': ('flag', dict(
        dur=2.0, off=0.0, emoji='⭐', kw=['ставка дня', 'главный прогноз'], col=(28, 34, 66), col2=GOLD,
        tcol=(255, 214, 110), star=True, lines=[('СТАВКА', 90, 70, MONT_I), ('ДНЯ', 168, 70, MONT_I)])),
    'led_kef': ('led', dict(
        dur=3.0, off=2.0, emoji='💰', kw=['кэф дня', 'коэффициент'], anim='bars', cols=65, rows=19, pitch=7,
        text='КЭФ ДНЯ', col=(255, 176, 40), col2=(60, 255, 120))),
    'led_express': ('led', dict(
        dur=3.0, off=0.0, emoji='🔗', kw=['экспресс', 'экспресс дня'], anim='ticker', cols=65, rows=19, pitch=7,
        text='ЭКСПРЕСС', col=(255, 214, 60), col2=(70, 200, 255))),
    'comic_zanos': ('comic', dict(
        dur=2.0, off=0.0, emoji='🤑', kw=['занос', 'выигрыш', 'деньги'], col=(255, 214, 40), col2=(255, 140, 20),
        tex=(20, 150, 70), tcol=(130, 255, 150), lines=[('ЗАНОС!', 8, 96)], tw=330, extra='coins', rot=-6)),
    'flag_zanos': ('flag', dict(
        dur=2.0, off=0.0, emoji='💰', kw=['занос', 'выигрыш'], col=(18, 120, 64), col2=(255, 214, 80),
        lines=[('ЗАНОС', 128, 104, MONT_I)])),
    'ice_ot': ('ice', dict(
        dur=3.0, off=0.0, emoji='⏱', kw=['овертайм', 'ОТ', 'дополнительное время'], text='ОВЕРТАЙМ', icon='watch',
        seed=6, ribbon=(150, 24, 40))),
    'led_bullity': ('led', dict(
        dur=3.0, off=2.3, emoji='🎯', kw=['буллиты', 'серия буллитов'], anim='lamps', cols=65, rows=19, pitch=7,
        text='БУЛЛИТЫ', col=(235, 240, 255), res='grggg')),
    'comic_gol': ('comic', dict(
        dur=3.0, off=0.0, emoji='🥅', kw=['гол', 'шайба', 'забили'], col=(255, 220, 40), col2=(240, 60, 40),
        tex=(200, 30, 30), lines=[('ГОЛ!', 8, 150)], tw=330, puck=True, extra='puck', kick=1.6, rot=-8)),
    'led_gol': ('led', dict(
        dur=2.0, off=0.0, emoji='🚨', kw=['гол', 'табло', 'забили'], anim='gol', cols=65, rows=19, pitch=7, top=50)),
    'ice_suhar': ('ice', dict(
        dur=3.0, off=0.0, emoji='🥶', kw=['сухарь', 'на ноль', 'вратарь'], text='СУХАРЬ', icon='zero', seed=8)),
    'comic_razgrom': ('comic', dict(
        dur=2.0, off=0.0, emoji='💥', kw=['разгром', 'крупная победа'], col=(255, 90, 40), col2=(160, 20, 30),
        tex=(30, 30, 40), tcol=(255, 240, 120), lines=[('РАЗГРОМ', 6, 84)], tw=396, stretch=(1.12, 0.86),
        shake=3.0, extra='debris', rot=-5, spikes=17)),
    'neon_verim': ('neon', dict(
        dur=2.0, off=0.0, emoji='🙏', kw=['верим', 'верю', 'вера'], anim='heart', flick=1,
        lines=[('Верим', LOBSTER, 204, 150, 270, 120, NEON_PINK)], heart=(410, 152, 3.0), icol=(255, 60, 90))),
    'flag_verim': ('flag', dict(
        dur=2.0, off=0.0, emoji='💪', kw=['верим', 'поддержка'], col=(30, 80, 200), col2=(255, 255, 255),
        lines=[('ВЕРИМ', 128, 104, MONT_I)])),
    'ice_zhdem': ('ice', dict(
        dur=3.0, off=0.0, emoji='⏳', kw=['ждём', 'ждем', 'ожидание'], text='ЖДЁМ', icon='clock', seed=9)),
    'board_zhdem': ('board', dict(
        dur=3.0, off=2.4, emoji='⏳', kw=['ждём', 'ждем', 'терпение'],
        lines=[('Ждём', 196, 160, 116, 250, NAVY_INK)],
        doodles=[([(330, 196), (331, 197)], 13, NAVY_INK, (1.95, 2.0)),
                 ([(362, 196), (363, 197)], 13, NAVY_INK, (2.05, 2.1)),
                 ([(394, 196), (395, 197)], 13, NAVY_INK, (2.15, 2.2)),
                 ([(96, 236), (180, 246), (300, 240), (420, 230)], 6, RED_INK, (2.25, 2.4))])),
    'led_plus': ('led', dict(
        dur=2.0, off=0.0, emoji='➕', kw=['плюс', 'в плюсе', 'профит'], anim='plus', cols=65, rows=21, pitch=7,
        text='ПЛЮС', col=(60, 255, 120))),
    'neon_tb': ('neon', dict(
        dur=3.0, off=0.0, emoji='⬆️', kw=['тотал больше', 'ТБ', 'больше'], anim='chevrons', flick=4, h=340,
        lines=[('ТОТАЛ', COMF, 214, 112, 210, 50, NEON_PINK), ('БОЛЬШЕ', COMF, 214, 208, 330, 76, NEON_CYAN)],
        chev=[_chev(430, 252, 34, 26), _chev(430, 194, 34, 26), _chev(430, 136, 34, 26)], icol=(80, 255, 140))),
    'neon_tm': ('neon', dict(
        dur=3.0, off=0.0, emoji='⬇️', kw=['тотал меньше', 'ТМ', 'меньше'], anim='chevrons', flick=2, h=340,
        lines=[('ТОТАЛ', COMF, 214, 112, 210, 50, NEON_PINK), ('МЕНЬШЕ', COMF, 214, 208, 330, 76, NEON_ORANGE)],
        chev=[_chev(430, 136, 34, 26, up=False), _chev(430, 194, 34, 26, up=False), _chev(430, 252, 34, 26, up=False)],
        icol=(255, 70, 60))),
    'flag_pognali': ('flag', dict(
        dur=2.0, off=0.0, emoji='🚀', kw=['погнали', 'поехали', 'старт'], col=(200, 30, 44), col2=(255, 255, 255),
        lines=[('ПОГНАЛИ', 128, 92, MONT_I)])),
    'comic_ogon': ('comic', dict(
        dur=2.0, off=0.0, emoji='🔥', kw=['огонь', 'жара', 'топ'], col=(255, 150, 30), col2=(220, 40, 20),
        tex=(170, 20, 10), tcol=(255, 240, 120), lines=[('ОГОНЬ!', 8, 104)], extra='embers', rot=-6, seed=5)),
    'stamp_proveren': ('stamp', dict(
        dur=3.0, off=1.2, emoji='👌', kw=['проверено', 'одобрено', 'разбор'], shape='round', text='ПРОВЕРЕНО',
        arc='РАЗБОР МАТЧА • JARVIS • РАЗБОР МАТЧА • JARVIS • ', col=VIOLET_INK, rot=9, r=138, seed=14)),
    'board_plan': ('board', dict(
        dur=3.0, off=2.4, emoji='📋', kw=['план', 'план есть', 'тактика'],
        lines=[('План есть!', 236, 150, 100, 340, NAVY_INK)],
        doodles=[([(410, 120), (466, 120), (466, 176), (410, 176), (410, 120)], 6, NAVY_INK, (1.9, 2.15)),
                 ([(420, 146), (436, 164), (476, 106)], 9, RED_INK, (2.15, 2.35)),
                 ([(70, 230), (200, 246), (330, 232)], 6, RED_INK, (2.35, 2.5))])),
    'board_itogi': ('board', dict(
        dur=3.0, off=2.4, emoji='📊', kw=['итоги', 'итоги дня', 'статистика'],
        lines=[('Итоги дня', 218, 128, 96, 320, NAVY_INK)],
        doodles=[([(70, 290), (150, 250), (210, 268), (300, 214), (380, 222), (456, 160)], 7, GREEN_INK, (1.9, 2.3)),
                 ([(430, 158), (458, 158), (458, 186)], 7, GREEN_INK, (2.3, 2.42))])),
}
STYLES = {'neon': Neon, 'led': Led, 'ice': Ice, 'stamp': Stamp, 'flag': Flag, 'comic': Comic, 'board': Board}
STYLE_TITLE = {'neon': 'неон', 'led': 'табло', 'ice': 'лёд', 'stamp': 'печать', 'flag': 'флаг', 'comic': 'комикс',
               'board': 'доска'}


def spec(key):
    style, sp = STICKERS[key]
    return style, sp


def n_frames(key):
    return int(round(spec(key)[1]['dur'] * FPS))


_OBJ = {}


def obj(key):
    if key not in _OBJ:
        style, sp = spec(key)
        _OBJ[key] = STYLES[style](sp)
    return _OBJ[key]


def frame(key, i):
    """Кадр i стикера → uint8 RGBA (H, W, 4)."""
    sp = spec(key)[1]
    t = round((i / FPS + sp['off']) % sp['dur'], 6)
    r = obj(key).frame(t)
    ov = None
    if isinstance(r, tuple):
        r, ov = r
    a = diecut(r)
    if ov is not None:
        a = over(ov, a)
    al = np.clip(a[..., 3:4], 0, 1)
    rgb = np.clip(a[..., :3] / np.maximum(al, 1e-6), 0, 1)
    return (np.dstack([rgb, al]) * 255 + 0.5).astype(np.uint8)


# ───────────────────────────── кодирование и проверка ─────────────────────────────

def encode(frames, dst, crf):
    h, w = frames[0].shape[:2]
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba',
                          '-s', '%dx%d' % (w, h), '-framerate', str(FPS), '-i', '-',
                          '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-auto-alt-ref', '0', '-b:v', '0',
                          '-crf', str(crf), '-deadline', 'good', '-cpu-used', '1', '-row-mt', '1', '-g', '300', '-an',
                          '-metadata:s:v:0', 'alpha_mode=1', dst], stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError('ffmpeg ' + dst)
    return os.path.getsize(dst)


def encode_fit(frames, dst, crfs=(14, 18, 22, 26, 30, 34, 38, 42, 46, 50, 55, 60)):
    """Наименьший crf (лучшее качество), который влезает в бюджет (бинарный поиск по списку)."""
    lo, hi, best = 0, len(crfs) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if encode(frames, dst[:-5] + '.part.webm', crfs[mid]) <= BUDGET:
            best = mid
            os.replace(dst[:-5] + '.part.webm', dst)
            hi = mid - 1
        else:
            lo = mid + 1
    if best is None:
        encode(frames, dst, crfs[-1])
        best = len(crfs) - 1
    if os.path.exists(dst[:-5] + '.part.webm'):
        os.remove(dst[:-5] + '.part.webm')
    return crfs[best]


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', path],
                       capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = [s for s in j['streams'] if s['codec_type'] == 'video'][0]
    tags = {k.lower(): val for k, val in v.get('tags', {}).items()}
    return dict(codec=v['codec_name'], w=v['width'], h=v['height'], fps=v['r_frame_rate'], pix_fmt=v.get('pix_fmt'),
                frames=int(v.get('nb_read_frames', 0)), dur=float(j['format']['duration']),
                alpha=tags.get('alpha_mode', '-'), audio=sum(s['codec_type'] == 'audio' for s in j['streams']),
                size=os.path.getsize(path), fmt=j['format']['format_name'])


def decode(path):
    """Все кадры webm (декодер libvpx-vp9 — только он отдаёт альфу) → список uint8 RGBA."""
    info = probe(path)
    w, h = info['w'], info['h']
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-c:v', 'libvpx-vp9', '-i', path, '-f', 'rawvideo',
                        '-pix_fmt', 'rgba', '-'], capture_output=True, check=True)
    a = np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w, 4)
    return list(a)


def check(info):
    """Требования Telegram к видео-стикеру → список нарушений."""
    bad = []
    if info['codec'] != 'vp9':
        bad.append('codec')
    if max(info['w'], info['h']) != 512 or min(info['w'], info['h']) > 512:
        bad.append('size %dx%d' % (info['w'], info['h']))
    if info['dur'] > 3.0:
        bad.append('dur %.2f' % info['dur'])
    if info['size'] > MAX_BYTES:
        bad.append('bytes %d' % info['size'])
    if info['audio']:
        bad.append('audio')
    if info['pix_fmt'] != 'yuv420p' or info['alpha'] != '1':     # VP9: альфа — отдельный поток, alpha_mode=1
        bad.append('pix_fmt %s alpha %s' % (info['pix_fmt'], info['alpha']))
    if eval(info['fps']) > 30:
        bad.append('fps')
    return bad


def _work(job):
    key, out = job
    frames = [frame(key, i) for i in range(n_frames(key))]
    dst = os.path.join(out, key + '.webm')
    crf = encode_fit(frames, dst)
    info = dict(probe(dst), crf=crf)
    dec = decode(dst)
    a = [f.astype(np.float32) for f in dec]
    steps = [np.abs(a[i + 1] - a[i]).mean() for i in range(len(a) - 1)]
    info['seam'] = (float(np.abs(a[0] - a[-1]).mean()), float(np.median(steps)), float(np.max(steps)))
    info['bad'] = check(info)
    pick = [0, len(dec) // 4, len(dec) // 2, 3 * len(dec) // 4]
    np.save(os.path.join(out, key + '.pick.npy'), np.stack([dec[i] for i in pick]))
    return key, info


# ───────────────────────────── контактные листы ─────────────────────────────

def sheet(keys, out, bg, name, n=4, cell=180):
    fl = mk.font('JetBrainsMono[wght].ttf', 13, 600)
    fh = mk.font('Onest[wght].ttf', 20, 700)
    cols = 2
    cw = n * (cell + 6) + 16
    ch = cell + 26
    rows = (len(keys) + cols - 1) // cols
    img = Image.new('RGB', (cols * cw + 20, rows * ch + 50), bg)
    d = ImageDraw.Draw(img)
    fg = (230, 232, 238) if sum(bg) < 300 else (30, 32, 40)
    d.text((14, 12), '%s · %s · %d шт. · кадры 0, ¼, ½, ¾ петли' % (SET_TITLE, 'тёмный фон' if sum(bg) < 300 else
                                                                     'светлый фон', len(keys)), font=fh, fill=fg)
    for j, k in enumerate(keys):
        x0 = 10 + (j % cols) * cw
        y0 = 46 + (j // cols) * ch
        pk = np.load(os.path.join(out, k + '.pick.npy'))
        for c in range(n):
            im = Image.fromarray(pk[c], 'RGBA')
            s = cell / 512
            im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
            img.paste(im, (x0 + c * (cell + 6) + (cell - im.width) // 2, y0 + (cell - im.height) // 2), im)
        lab = '%s  [%s]' % (k, STYLE_TITLE[STICKERS[k][0]])
        d.text((x0 + 4, y0 + cell + 4), lab, font=fl, fill=fg)
        em = mk.std_emoji(STICKERS[k][1]['emoji'], 16)
        if em is not None:
            img.paste(em, (int(x0 + 12 + d.textlength(lab, font=fl)), y0 + cell + 3), em)
    p = os.path.join(out, name)
    img.save(p)
    return p


# ───────────────────────────── сборка набора ─────────────────────────────

def build(out):
    """WEBM из out → team/stickers/build/ + manifest.json (формат как у team/emoji/build/manifest.json)."""
    missing = [k for k in STICKERS if not os.path.exists(os.path.join(out, k + '.webm'))]
    if missing:
        raise SystemExit('нет файлов: ' + ', '.join(missing))
    shutil.rmtree(BUILD, ignore_errors=True)
    os.makedirs(BUILD)
    items = []
    for k, (style, sp) in STICKERS.items():
        shutil.copy(os.path.join(out, k + '.webm'), os.path.join(BUILD, k + '.webm'))
        items.append({'key': k, 'file': k + '.webm', 'format': 'video', 'emoji': sp['emoji'], 'keywords': sp['kw'],
                      'style': style})
    man = {'sets': [{'name': SET_NAME, 'title': SET_TITLE, 'sticker_type': 'regular', 'items': items}]}
    with open(os.path.join(BUILD, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    return os.path.join(BUILD, 'manifest.json')


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0] if args else DEFAULT_OUT
    keys = args[1:] or list(STICKERS)
    os.makedirs(out, exist_ok=True)
    # тяжёлые (флаги, комиксы) — первыми, чтобы процессы закончили одновременно
    order = sorted(keys, key=lambda k: -{'flag': 3, 'comic': 3, 'stamp': 2, 'ice': 2}.get(STICKERS[k][0], 1) * n_frames(k))
    res = {}
    with Pool(os.cpu_count() or 2) as p:
        for k, info in p.imap_unordered(_work, [(k, out) for k in order]):
            res[k] = info
            print('%-15s %dx%d %4.2fs %2d fr %6.1f KB crf %2d %s' % (
                k, info['w'], info['h'], info['dur'], info['frames'], info['size'] / 1024, info['crf'],
                'OK' if not info['bad'] else 'FAIL ' + '; '.join(info['bad'])), flush=True)
    old = {}
    pj = os.path.join(out, 'probe.json')
    if os.path.exists(pj):
        with open(pj) as f:
            old = json.load(f)
    old.update(res)
    with open(pj, 'w') as f:
        json.dump(old, f, indent=1, ensure_ascii=False)
    if '--no-sheet' not in sys.argv:
        ks = [k for k in STICKERS if os.path.exists(os.path.join(out, k + '.pick.npy'))]
        print(sheet(ks, out, (24, 26, 32), 'sheet_dark.png'))
        print(sheet(ks, out, (236, 238, 242), 'sheet_light.png'))
    if '--no-build' not in sys.argv and set(keys) == set(STICKERS):
        print(build(out))
