# -*- coding: utf-8 -*-
"""«Досье» — матч как дело детектива ночью (трек «BATS», поздний участок трека, дроп 118,36 с).

Нуар: тёмный стол с зелёным кожаным бюваром, зелёная лампа банкира сверху (тёплое пятно света, пылинки в конусе),
поперёк кадра — холодные полосы лунного света сквозь жалюзи. На столе — картонные папки-досье: на обложке
снимок-«фото из дела» с эмблемой клуба на скрепке, наклейка с названием и красный штамп «ХОЗЯЕВА / ГОСТИ».
Внутри — лист, напечатанный на машинке (шрифт с засечками Podkova, буквы чуть пляшут и пропечатаны неровно):
строки печатаются по долям трека с кареткой-курсором, итог игры В/П обводится маркером, цифры клуба закрыты
чёрными полосами цензуры — полосы срываются на доли. Сверху JARVIS | NHL, у низа безопасной зоны @jarvibet
(одинаково во всех сценах до плашки Telegram). Без заголовков-рубрик: на экране только матч, факты и прогноз.

Сцены (u — доля трека, D — дроп; доли считаются от дропа, team / pre / hold / cta — reels_cfg/dossier.json):
  интро (до b(−2·team−pre)) — полоска-ярлык дела: лига, день и время МСК (печатается); две закрытые папки
                (обе эмблемы на фото, названия, «ХОЗЯЕВА / ГОСТИ») ложатся на полдоли и долю, красная нить
                протягивается между фото; на четверти долей шлёпаются три карточки линии основного времени
                П1 · Х · П2 — кэфы крупно;
  клуб ×2 (team долей) — смахивание папок ровно на долю; на полдоли обложка раскрывается, печатается название,
                на долю — фото на скрепке и штамп роли; на полдоли 1,5 / 2 / 2,5 печатаются последние 3 игры
                (дата, соперник, счёт, ОТ/Б, В/П — В/П тут же обводится маркером); на 3 / 3,5 / 4 / 4,5 / 5 долях
                срываются полосы цензуры: очки за N матчей, место (с конференцией), разница шайб, серия от 2 игр,
                большинство и меньшинство (только непустые поля, максимум 5 строк);
  сведение (pre долей)  — обе закрытые папки съезжаются в центр под красную нить, лампа мигает, в последнюю
                долю (в треке пауза) свет почти гаснет, сверху опускается штемпель;
  ДРОП (hold долей)    — ровно на дропе штемпель бьёт по листу (тряска камеры, всплеск лампы, брызги чернил):
                оттиск «ПОБЕДА / КЛУБ», над ним фото ТОЛЬКО выбранной команды (одна эмблема, без «VS»);
                на полдоли печатается «В ОСНОВНОЕ ВРЕМЯ», на долю — «КЭФ …», на 2-ю долю кэф обводят маркером;
                на каждую долю — лёгкий толчок камеры;
  финал (cta долей)    — лист уменьшается и уходит вверх, снизу плашка Telegram (C.tg_plate, текст по центру плашки).
Кадр — чистая функция t; стол, свет, бумага, папки и строки готовятся в __init__ (до fork) и кешируются на уровне модуля.
"""
import math
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels.core import W, H

C.FONTS.setdefault('podk', 'Podkova[wght].ttf')        # машинописный шрифт с засечками (лежит в render/fonts)

TW = 'podk'
INK = (30, 28, 34)                 # лента машинки
INK2 = (96, 88, 80)                # бледная печать (подписи)
PAPER = (240, 233, 214)
MANILA = (206, 170, 112)
RED = (192, 30, 38)                # маркер и штамп
GREEN = (24, 128, 64)
CREAM = (236, 226, 204)            # экранные подписи на столе
TAG_Y, HY = 262, 1448
FBW, FBH = 1000, 1112              # раскрытая папка (задняя обложка) в сцене клуба
FBX, FBY = 40, 290                 # её левый верх в кадре
PGX, PGY, PGW, PGH = 20, 14, 960, 1084   # лист внутри папки
FACE_W, FACE_H = 1000, 1112        # обложка папки в полном размере (интро и сведение — уменьшенная)
_CACHE = {}


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def pct(v):
    try:
        return ('%.1f' % float(v)).rstrip('0').rstrip('.').replace('.', ',') + '%'
    except (TypeError, ValueError):
        return None


def _noise(w, h, seed, blur=0.0, scale=1):
    rnd = np.random.default_rng(seed)
    a = rnd.normal(0, 1, (h // scale + 1, w // scale + 1)).astype(np.float32)
    im = Image.fromarray(np.clip(a * 40 + 128, 0, 255).astype(np.uint8), 'L')
    if scale > 1:
        im = im.resize((w, h), Image.BICUBIC)
    else:
        im = im.crop((0, 0, w, h))
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return (np.asarray(im, np.float32) - 128) / 40


# ─────────────────────────────── машинопись ───────────────────────────────
def typed(s, size, col=INK, wght=760, seed=0, max_w=None):
    """Строка «с машинки» → (RGBA, правые края символов). Буквы чуть пляшут по высоте и пропечатаны неровно."""
    key = ('typed', s, int(size), tuple(col), wght, seed, max_w)
    if key in _CACHE:
        return _CACHE[key]
    size = int(size)
    while True:
        f = C.font(TW, size, wght)
        tw = f.getlength(s)
        if not max_w or tw <= max_w or size <= 18:
            break
        size = max(18, int(size * max_w / tw * 0.99))
    asc, desc = f.getmetrics()
    pad = int(size * 0.2) + 3
    im = Image.new('RGBA', (int(math.ceil(tw)) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rnd = np.random.default_rng(abs(hash((s, size, seed))) % (2 ** 31))
    xs = []
    for i, ch in enumerate(s):
        x = pad + f.getlength(s[:i])
        dy = rnd.uniform(-0.035, 0.035) * size
        al = int(rnd.uniform(205, 255))
        d.text((x, pad + dy), ch, font=f, fill=tuple(col) + (al,))
        xs.append(pad + f.getlength(s[:i + 1]))
    a = np.asarray(im.getchannel('A'), np.float32)
    nz = _noise(im.width, im.height, 11 + seed, 0.6)
    a = a * np.clip(0.9 + 0.12 * nz, 0.55, 1.0)
    im.putalpha(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'L'))
    bb = im.getchannel('A').getbbox()
    top = pad + max(0, int(asc - size * 0.8))
    bot = pad + asc + 2
    x0 = bb[0] if bb else 0
    im = im.crop((x0, max(0, min(top, bb[1] if bb else top)), bb[2] if bb else im.width, max(bot, bb[3] if bb else bot)))
    xs = [x - x0 for x in xs]
    _CACHE[key] = (im, xs)
    return im, xs


class Line:
    """Строка из кусков [(картинка, x, y_центр)] в координатах листа; печать слева направо по символам."""

    def __init__(self, parts):
        self.parts = parts            # [(im, xs, x, yc)]
        self.n = sum(len(xs) for _, xs, _, _ in parts)

    def draw(self, dst, k, ox=0, oy=0, cursor=True):
        """k — доля напечатанного (0..1); cursor — каретка у последней буквы, пока строка печатается."""
        if k <= 0:
            return
        m = int(math.ceil(self.n * min(1.0, k)))
        last = None
        for im, xs, x, yc in self.parts:
            if m <= 0:
                break
            c = min(m, len(xs))
            cw = int(math.ceil(xs[c - 1])) + 2 if c < len(xs) else im.width
            cw = min(cw, im.width)
            piece = im.crop((0, 0, cw, im.height)) if cw < im.width else im
            C.put(dst, piece, ox + x, oy + yc - im.height / 2, anchor='tl')
            last = (ox + x + cw, oy + yc, im.height)
            m -= c
        if cursor and k < 1 and last:
            x, yc, h = last
            C.put(dst, _rect(10, int(h * 0.9), INK, 200), x + 8, yc)


def _rect(w, h, col, a=255):
    key = ('rect', w, h, tuple(col), a)
    if key not in _CACHE:
        _CACHE[key] = Image.new('RGBA', (int(w), int(h)), tuple(col) + (a,))
    return _CACHE[key]


# ─────────────────────────────── предметы ───────────────────────────────
def paper(w, h, seed=3, col=PAPER):
    key = ('paper', w, h, seed, col)
    if key in _CACHE:
        return _CACHE[key]
    n1 = _noise(w, h, seed, 0, 1)
    n2 = _noise(w, h, seed + 1, 0, 24)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    age = np.clip(1 - edge / 70, 0, 1) ** 2
    base = np.array(col, np.float32)[None, None, :]
    arr = base * (1 + 0.012 * n1[..., None] + 0.03 * n2[..., None])
    arr = arr * (1 - 0.1 * age[..., None]) + np.array((-4, -6, -16), np.float32) * age[..., None]
    out = np.concatenate([np.clip(arr, 0, 255), np.full((h, w, 1), 255, np.float32)], -1).astype(np.uint8)
    im = Image.fromarray(out, 'RGBA')
    _CACHE[key] = im
    return im


def manila(w, h, seed=5, col=MANILA, spine=False):
    key = ('manila', w, h, seed, col, spine)
    if key in _CACHE:
        return _CACHE[key]
    n1 = _noise(w, h, seed, 0, 1)
    n2 = _noise(w, h, seed + 1, 0, 30)
    fib = _noise(w, h, seed + 2, 0, 1)
    fib = np.asarray(Image.fromarray(np.clip(fib * 40 + 128, 0, 255).astype(np.uint8), 'L').filter(ImageFilter.BoxBlur(0)).resize(
        (w, h)), np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    age = np.clip(1 - edge / 40, 0, 1) ** 1.6
    arr = np.array(col, np.float32)[None, None, :] * (1 + 0.025 * n1[..., None] + 0.05 * n2[..., None])
    arr = arr * (1 - 0.22 * age[..., None])
    if spine:                                                   # сгиб у левого края обложки
        sp = np.exp(-((xx - 26) / 6) ** 2)
        arr = arr * (1 - 0.18 * sp[..., None])
    arr += (fib[..., None] - 128) * 0.03
    rr = max(6, int(min(w, h) * 0.018))
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), rr, fill=255)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    out.putalpha(mask)
    _CACHE[key] = out
    return out


def clip_sprite(s=1.0):
    """Скрепка (вид сверху), высота ~150·s."""
    key = ('clip', round(s, 3))
    if key in _CACHE:
        return _CACHE[key]
    ss = 3
    w, h = int(64 * s), int(170 * s)
    im = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = max(2, int(7 * s * ss))
    steel, hi = (150, 156, 164, 255), (232, 236, 240, 255)

    def loop(x0, y0, x1, y1, col, wd):
        r = (x1 - x0) / 2
        d.rounded_rectangle((x0, y0, x1, y1), radius=r, outline=col, width=wd)

    m = 6 * s * ss
    loop(m, m, w * ss - m, h * ss - m, steel, lw)
    loop(m + 14 * s * ss, m + 34 * s * ss, w * ss - m - 14 * s * ss, h * ss - m - 8 * s * ss, steel, lw)
    loop(m + 2 * s * ss, m + 2 * s * ss, w * ss - m - 2 * s * ss, h * ss - m - 2 * s * ss, hi, max(1, lw // 3))
    im = im.resize((w, h), Image.LANCZOS)
    out = C.with_shadow(im, 4, 0.55, 5)
    _CACHE[key] = out
    return out


def photo(team, w, h, seed=1):
    """«Фото из дела»: белая кромка, серый фон с ростовой линейкой, эмблема клуба; лёгкий блик и старение."""
    key = ('photo', team.name, w, h, seed)
    if key in _CACHE:
        return _CACHE[key]
    b = max(10, int(w * 0.05))
    iw, ih = w - 2 * b, h - 2 * b - int(b * 0.6)
    inner = C.vgrad(iw, ih, [(0, (126, 130, 134)), (1, (70, 73, 78))]).convert('RGBA')
    d = ImageDraw.Draw(inner)
    step = max(18, ih // 11)
    for i, y in enumerate(range(step // 2, ih, step)):
        d.line((0, y, iw, y), fill=(196, 198, 200, 120 if i % 2 else 70), width=2 if i % 2 else 1)
    e = team.emb(int(min(iw, ih) * 0.78))
    C.put(inner, C.shadow(e, 10, 0.6), iw / 2 + 4, ih / 2 + 12)
    C.put(inner, e, iw / 2, ih / 2 + 4)
    arr = np.asarray(inner, np.float32)
    yy, xx = np.mgrid[0:ih, 0:iw].astype(np.float32)
    vg = 1 - 0.32 * np.clip(np.hypot((xx - iw / 2) / (iw / 2), (yy - ih / 2) / (ih / 2)) / 1.3, 0, 1) ** 2
    arr[..., :3] = arr[..., :3] * vg[..., None]
    arr[..., :3] = arr[..., :3] * 0.9 + np.array((255, 236, 200), np.float32) * 0.1 * (arr[..., :3] / 255)  # тёплый отпечаток
    inner = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
    gl = C.lgrad(iw, ih, (255, 255, 255), (255, 255, 255), 35, 0, 0)
    ga = np.asarray(gl, np.float32)
    band = np.clip(1 - np.abs((xx + yy * 0.6) / (iw + ih * 0.6) - 0.33) * 9, 0, 1) * 34
    ga[..., 3] = band
    inner.alpha_composite(Image.fromarray(ga.astype(np.uint8), 'RGBA'))
    out = paper(w, h, seed + 40, (246, 243, 236)).copy()
    out.paste(inner.convert('RGB'), (b, b))
    _CACHE[key] = out
    return out


def stamp_box(lines_, h_line, col=RED, pad=(36, 18), border=7, seed=2, font='dela', rot=0.0, gap=10):
    """Оттиск резинового штампа: двойная рамка, текст строками, неровная пропечатка."""
    key = ('stamp', tuple(lines_), tuple(h_line), col, pad, border, seed, font, rot, gap)
    if key in _CACHE:
        return _CACHE[key]
    ims = [C.text(s, font, hh, col, 800, max_w=mw) for s, (hh, mw) in zip(lines_, h_line)]
    tw = max(i.width for i in ims)
    th = sum(i.height for i in ims) + gap * (len(ims) - 1)
    w, h = int(tw + 2 * pad[0] + 4 * border), int(th + 2 * pad[1] + 4 * border)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = int(min(w, h) * 0.08)
    d.rounded_rectangle((0, 0, w - 1, h - 1), r, outline=tuple(col) + (255,), width=border)
    o = int(border * 1.9)
    d.rounded_rectangle((o, o, w - 1 - o, h - 1 - o), max(2, r - o), outline=tuple(col) + (255,), width=max(2, border // 2))
    y = (h - th) / 2
    for i in ims:
        C.put(im, i, w / 2, y + i.height / 2)
        y += i.height + gap
    a = np.asarray(im.getchannel('A'), np.float32)
    n1 = _noise(w, h, seed, 0.8, 1)
    n2 = _noise(w, h, seed + 7, 0, 9)
    k = np.clip(0.86 + 0.1 * n1 + 0.16 * n2, 0, 1)
    k[(n1 > 1.9)] *= 0.25                                       # непропечатанные точки
    im.putalpha(Image.fromarray(np.clip(a * k * 0.93, 0, 255).astype(np.uint8), 'L'))
    if rot:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    _CACHE[key] = im
    return im


def marker_ring(w, h, col=RED, wd=7, seed=4, turns=1.12, steps=26):
    """Обводка маркером: список картинок по мере рисования (0..steps)."""
    key = ('ring', w, h, col, wd, seed, turns, steps)
    if key in _CACHE:
        return _CACHE[key]
    rnd = np.random.default_rng(seed)
    S = 3
    pw, ph = int(w + 4 * wd), int(h + 4 * wd)
    a0 = math.radians(rnd.uniform(190, 230))
    n = 120
    pts = []
    for i in range(n + 1):
        q = i / n
        ang = a0 - turns * 2 * math.pi * q
        rr = 1 + 0.05 * math.sin(q * 7 + seed) + 0.04 * q
        pts.append(((pw / 2 + math.cos(ang) * w / 2 * rr) * S, (ph / 2 + math.sin(ang) * h / 2 * rr * (1 - 0.06 * q)) * S))
    out = []
    for k in range(steps + 1):
        m = int(round(n * k / steps))
        im = Image.new('RGBA', (pw * S, ph * S), (0, 0, 0, 0))
        if m >= 1:
            ImageDraw.Draw(im).line(pts[:m + 1], fill=tuple(col) + (225,), width=wd * S, joint='curve')
        out.append(im.resize((pw, ph), Image.LANCZOS))
    _CACHE[key] = out
    return out


def redact_bar(w, h, seed=0):
    key = ('bar', w, h, seed)
    if key in _CACHE:
        return _CACHE[key]
    rnd = np.random.default_rng(seed)
    S = 2
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = []
    n = 14
    for i in range(n + 1):
        pts.append((i / n * w * S, rnd.uniform(0, 5) * S))
    for i in range(n, -1, -1):
        pts.append((i / n * w * S, (h - rnd.uniform(0, 5)) * S))
    d.polygon(pts, fill=(14, 13, 16, 248))
    im = im.resize((w, h), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    nz = _noise(w, h, seed + 3, 0, 1)
    a[..., :3] += (nz * 5)[..., None]                    # фактура маркера
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    _CACHE[key] = out
    return out


def stamper(w, h):
    """Сам штемпель сверху: резина, деревянная колодка, ручка-шар."""
    key = ('stamper', w, h)
    if key in _CACHE:
        return _CACHE[key]
    im = Image.new('RGBA', (w + 120, h + 120), (0, 0, 0, 0))
    C.put(im, C.rrect(w, h, 26, (70, 20, 22)), im.width / 2, im.height / 2)
    wood = C.lgrad(w - 40, h - 40, (122, 78, 44), (74, 44, 24), 90)
    m = C.rrect(w - 40, h - 40, 22, (255, 255, 255))
    wood.putalpha(m.getchannel('A'))
    C.put(im, wood, im.width / 2, im.height / 2)
    kn = int(h * 0.62)
    knob = C.radial(kn, kn, (60, 34, 18), 255, 0.25)
    C.put(im, C.ellipse(kn, kn, (52, 30, 16)), im.width / 2, im.height / 2)
    hl = C.radial(kn // 2, kn // 2, (210, 160, 110), 200, 1.4)
    C.put(im, knob, im.width / 2, im.height / 2)
    C.put(im, hl, im.width / 2 - kn * 0.16, im.height / 2 - kn * 0.18)
    _CACHE[key] = im
    return im


def ink_splat(w, h, seed=9, col=RED):
    key = ('splat', w, h, seed, col)
    if key in _CACHE:
        return _CACHE[key]
    rnd = np.random.default_rng(seed)
    S = 2
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(46):
        ang = rnd.uniform(0, 2 * math.pi)
        rx = w / 2 * rnd.uniform(0.86, 1.05)
        ry = h / 2 * rnd.uniform(0.8, 1.1)
        x, y = w / 2 + math.cos(ang) * rx, h / 2 + math.sin(ang) * ry
        r = rnd.uniform(1.5, 7) if rnd.uniform() < 0.85 else rnd.uniform(8, 13)
        d.ellipse(((x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S), fill=tuple(col) + (int(rnd.uniform(150, 230)),))
    out = im.resize((w, h), Image.LANCZOS)
    _CACHE[key] = out
    return out


# ─────────────────────────────── стол и свет ───────────────────────────────
def desk():
    if 'desk' in _CACHE:
        return _CACHE['desk']
    h, w = H, W
    n1 = _noise(w, h, 21, 0, 1)
    n2 = _noise(w, h, 22, 0, 40)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # тёмное дерево по краям, зелёная кожа бювара в середине
    wood = np.array((40, 26, 18), np.float32) * (1 + 0.18 * np.sin(yy / 23 + 3 * n2) [..., None] * 0.5 + 0.04 * n1[..., None])
    leather = np.array((24, 44, 36), np.float32) * (1 + 0.05 * n1[..., None] + 0.12 * n2[..., None])
    bx0, bx1, by0, by1 = 22, w - 22, 214, 1536
    inb = ((xx >= bx0) & (xx <= bx1) & (yy >= by0) & (yy <= by1)).astype(np.float32)
    arr = wood * (1 - inb[..., None]) + leather * inb[..., None]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    d = ImageDraw.Draw(im)
    d.rectangle((bx0 + 12, by0 + 12, bx1 - 12, by1 - 12), outline=(150, 118, 58, 150), width=2)   # тиснение по краю
    d.rectangle((bx0, by0, bx1, by1), outline=(10, 14, 12, 255), width=3)
    # кофейный след на столе
    ring = Image.new('RGBA', (300, 300), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((20, 20, 280, 280), outline=(70, 44, 24, 120), width=10)
    ring = ring.filter(ImageFilter.GaussianBlur(2.5))
    C.put(im, ring, 900, 1600)
    # лампа банкира сверху (вне безопасной зоны — только декор)
    sh = Image.new('RGBA', (560, 230), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    ds.pieslice((0, -200, 560, 230), 0, 180, fill=(18, 70, 46, 255))
    ds.arc((0, -200, 560, 230), 0, 180, fill=(196, 168, 88, 255), width=6)
    sh = C.with_shadow(sh, 14, 0.7, 10)
    C.put(im, sh, 760, 34)
    _CACHE['desk'] = im
    return im


def lights():
    """(лампа RGB-множитель, жалюзи RGB-множитель, добавка конуса света) — float32 (H, W, 3)."""
    if 'lights' in _CACHE:
        return _CACHE['lights']
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d2 = ((xx - 560) / 820) ** 2 + ((yy - 820) / 1120) ** 2
    pool = np.exp(-1.15 * d2)
    vig = 1 - 0.55 * np.clip(np.sqrt(((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2) / 1.25, 0, 1) ** 2.2
    lamp = (0.22 + 0.86 * pool) * vig
    lampc = np.stack([lamp * 1.06, lamp * 0.99, lamp * 0.86], -1)
    # полосы лунного света сквозь жалюзи (косые, холодные)
    p = (xx * 0.42 + yy) / 1.0
    band = 0.5 + 0.5 * np.sin(p / 96 * 2 * math.pi)
    band = np.clip((band - 0.35) * 3.2, 0, 1)
    fall = np.clip(1 - ((xx - 160) / 1400) ** 2 - ((yy - 500) / 2300) ** 2, 0, 1)
    blind = band * fall * 0.17 * vig
    blindc = np.stack([blind * 0.62, blind * 0.84, blind * 1.18], -1)
    # объёмный конус от лампы
    cx, cy = 760, 140
    ang = np.arctan2(xx - cx, yy - cy)
    dist = np.hypot(xx - cx, yy - cy)
    cone = np.exp(-((ang + 0.12) / 0.42) ** 2) * np.clip(dist / 260, 0, 1) * np.exp(-dist / 1500) * (yy > cy)
    conec = np.stack([cone * 30, cone * 25, cone * 16], -1).astype(np.float32)
    out = (lampc.astype(np.float32), blindc.astype(np.float32), conec)
    _CACHE['lights'] = out
    _CACHE['lsum'] = out[0] + out[1]
    return out


# ─────────────────────────────── ролик ───────────────────────────────
class Dossier(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 73, drop=20 * 60 / 73, line=None, team=7, pre=2,
                 hold=5, cta=3, seed=41, **kw):
        """Сцены: интро → клуб (team долей) ×2 → сведение (pre) → дроп-прогноз (hold) → Telegram (cta); доли — от дропа."""
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.line = league, when, coef, line
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
        self.raw = {'h': sh or {}, 'a': sa or {}}
        self.st = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.t1 = self.b(-(2 * team + pre))
        self.t2 = self.b(-(team + pre))
        self.tp = self.b(-pre)
        if self.t1 < 2.0:
            raise ValueError('мало времени до дропа')
        self.t_cta = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = round(self.t1 - 0.45, 2)
        self._prep()

    # ── заготовки ──
    def _prep(self):
        desk()
        lights()
        self.tag = C.text(F.tag(self.league), 'unb', 32, (214, 200, 172), 700, track=0.12)
        self.handle_im = C.text(C.HANDLE, 'unb', 40, CREAM, 600)
        self.dot = C.radial(14, 14, (255, 236, 196), 255, 1.5)
        rnd = np.random.default_rng(self.seed)
        self.dust = [(rnd.uniform(300, 1060), rnd.uniform(240, 1500), rnd.uniform(6, 22), rnd.uniform(0.2, 1.0), rnd.uniform(0, 6.3),
                      rnd.uniform(0.4, 1.3)) for _ in range(70)]
        # папки (обложки) и сцены клубов
        self.face = {s: self._face(tm, s) for s, tm in (('h', self.h), ('a', self.a))}
        self.small = {}
        for s in ('h', 'a'):
            for sc, rot in ((0.5, -3.0 if s == 'h' else 2.5), (0.54, -4.0 if s == 'h' else 3.5)):
                im = C.rotate(self.face[s].resize((int(FACE_W * sc), int(FACE_H * sc)), Image.LANCZOS), rot)
                self.small[(s, sc)] = C.with_shadow(im, 18, 0.6, 16)
        self.back = self._back()
        self.T = {k: self._team(k) for k in ('h', 'a')}
        # интро
        self.strip = self._strip('%s · %s' % (F.lg_ru(self.league), self.when), 820)
        self.strip2 = self._strip('%s — %s' % (self.h.up, self.a.up), 900)
        self.strip3 = self._strip('%s · %s' % (F.lg_ru(self.league), self.when), 820)
        self.cards = self._cards() if self.line else []
        # прогноз
        self._pick_prep()
        self.tg = C.tg_plate(960, 172, font='unb')

    def _strip(self, s, w):
        """Полоска-ярлык дела: бумага на скотче, строка печатается."""
        im, xs = typed(s, 54, INK, 800, seed=len(s), max_w=w - 70)
        h = 104
        pl = paper(w, h, 77, (238, 230, 210)).copy()
        x0 = (w - im.width) / 2
        tape = Image.new('RGBA', (120, 46), (230, 222, 190, 150))
        out = Image.new('RGBA', (w + 60, h + 40), (0, 0, 0, 0))
        C.put(out, C.with_shadow(pl, 8, 0.6, 6), out.width / 2, out.height / 2 + 4)
        for tx in (0.06, 0.94):
            C.put(out, C.rotate(tape, 8 if tx < 0.5 else -8), 30 + w * tx, 26)
        line = Line([(im, xs, 30 + x0, out.height / 2 + 2)])
        return dict(im=out, line=line)

    def _face(self, tm, side):
        """Обложка папки: фото на скрепке, наклейка с названием, штамп роли."""
        fc = manila(FACE_W, FACE_H, 5 if side == 'h' else 8, spine=True).copy()
        ph = photo(tm, 560, 600, 1 if side == 'h' else 2)
        ph = C.rotate(ph, -3 if side == 'h' else 2.5)
        C.put(fc, C.with_shadow(ph, 10, 0.5, 8), FACE_W / 2, 360)
        C.put(fc, clip_sprite(1.6), FACE_W / 2 - 150, 140)
        lab = paper(820, 180, 33, (246, 242, 232)).copy()
        d = ImageDraw.Draw(lab)
        d.line((30, 150, 790, 150), fill=(170, 60, 60, 160), width=3)
        im, _ = typed(tm.up, 130, INK, 800, seed=3, max_w=740)
        C.put(lab, im, 410, 86)
        C.put(fc, C.with_shadow(C.rotate(lab, 1.2), 8, 0.45, 6), FACE_W / 2, 790)
        st = stamp_box(['ХОЗЯЕВА' if side == 'h' else 'ГОСТИ'], [(84, 600)], RED, (40, 16), 8, seed=5 + (side == 'a'), rot=-7)
        C.put(fc, st, FACE_W / 2 + 120, 990)
        return fc

    def _back(self):
        """Раскрытая папка: задняя обложка и чистый лист."""
        bk = manila(FBW, FBH, 12).copy()
        pg = paper(PGW, PGH, 14).copy()
        d = ImageDraw.Draw(pg)
        for y in (226, 860):                                     # дырки дырокола
            d.ellipse((22, y - 15, 52, y + 15), fill=(52, 40, 30, 255))
        d.line((78, 0, 78, PGH), fill=(196, 96, 96, 110), width=2)  # поле
        C.put(bk, C.shadow(pg, 8, 0.45), PGX + PGW / 2 + 3, PGY + PGH / 2 + 6)
        C.put(bk, pg, PGX, PGY, anchor='tl')
        return bk

    def _team(self, key):
        tm = self.h if key == 'h' else self.a
        s = self.st[key]
        page = Image.new('RGBA', (FBW, FBH), (0, 0, 0, 0))     # статичная печать листа (подписи, линейки)
        ox, oy = PGX, PGY
        d = ImageDraw.Draw(page)
        X0 = ox + 100
        XR = ox + PGW - 40
        # шапка: фото слева, название и роль
        ph = C.with_shadow(C.rotate(photo(tm, 290, 316, 5 + (key == 'a')), -4 if key == 'h' else 3), 9, 0.5, 8)
        name, nxs = typed(tm.up, 112, INK, 800, seed=1, max_w=XR - (ox + 400))
        role = stamp_box(['ХОЗЯЕВА' if key == 'h' else 'ГОСТИ'], [(58, 400)], RED, (30, 12), 6, seed=8 + (key == 'a'), rot=-5)
        nx = ox + 400 + (XR - ox - 400 - name.width) / 2
        name_line = Line([(name, nxs, nx, oy + 128)])
        d.line((X0 - 20, oy + 338, XR, oy + 338), fill=INK2 + (150,), width=3)
        d.line((X0 - 20, oy + 662, XR, oy + 662), fill=INK2 + (150,), width=3)
        # последние игры
        games = []
        for i, g in enumerate(s['games'][:3]):
            yc = oy + 392 + 107 * i
            parts = []
            dt, dxs = typed(g['date'], 40, INK2, 650, seed=i)
            parts.append((dt, dxs, X0, yc + 6))
            sc_im, sxs = typed(g['score'], 76, INK, 800, seed=10 + i)
            xs_score = ox + 690 - sc_im.width
            opp, oxs = typed(g['opp'].upper(), 62, INK, 780, seed=20 + i, max_w=xs_score - (X0 + 140) - 24)
            parts.append((opp, oxs, X0 + 140, yc))
            parts.append((sc_im, sxs, xs_score, yc))
            if g['note']:
                nt, ntx = typed(g['note'], 40, INK2, 700, seed=30 + i)
                parts.append((nt, ntx, ox + 702, yc + 10))
            res = g['res'] or '?'
            col = GREEN if res == 'В' else RED if res == 'П' else INK2
            rs, rxs = typed(res, 76, col, 800, seed=40 + i)
            rx = ox + 850
            parts.append((rs, rxs, rx - rs.width / 2, yc))
            ring = marker_ring(118, 104, col, 7, seed=i + (key == 'a') * 3)
            games.append(dict(line=Line(parts), ring=ring, ring_pos=(rx, yc)))
            if i < 2:
                for x in range(int(X0 - 20), int(XR), 14):                # пунктир между строками
                    d.line((x, yc + 54, x + 6, yc + 54), fill=INK2 + (70,), width=2)
        # цифры под цензурой
        rows = self._stat_rows(key)
        stats = []
        for i, (lab, val, sub, vcol) in enumerate(rows[:5]):
            yc = oy + 722 + 79 * i
            lb, _ = typed(lab, 40, INK2, 700, seed=50 + i)
            C.put(page, lb, X0, yc - lb.height / 2 + 4, anchor='tl')
            v, _ = typed(val, 64, vcol, 800, seed=60 + i)
            sb = typed(sub, 38, INK2, 650, seed=70 + i)[0] if sub else None
            wtot = v.width + (14 + sb.width if sb is not None else 0)
            vx = XR - wtot
            for x in range(int(X0 + lb.width + 18), int(vx - 18), 16):      # отточие
                d.ellipse((x, yc + 14, x + 4, yc + 18), fill=INK2 + (150,))
            grp = Image.new('RGBA', (int(wtot) + 4, max(v.height, sb.height if sb else 0) + 4), (0, 0, 0, 0))
            C.put(grp, v, 0, grp.height - v.height - 2, anchor='tl')
            if sb is not None:
                C.put(grp, sb, v.width + 14, grp.height - sb.height - 4, anchor='tl')
            bw, bh = int(wtot + 36), 70
            stats.append(dict(img=grp, pos=(vx, yc - grp.height / 2 + 2), bar=redact_bar(bw, bh, seed=i + 10 * (key == 'a')),
                              bar_pos=(vx - 18, yc - bh / 2)))
        return dict(page=page, photo=ph, photo_pos=(ox + 196, oy + 172), clip=clip_sprite(1.0), clip_pos=(ox + 128, oy + 22),
                    name=name_line, role=role, role_pos=(ox + 400 + (XR - ox - 400) / 2, oy + 262), games=games, stats=stats)

    def _stat_rows(self, key):
        s, rec = self.st[key], self.raw[key]
        out = []
        if s['points'] is not None:
            sub = ('за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей'))) if s['gp'] is not None else ''
            out.append(('ОЧКИ', '%d' % s['points'], sub, INK))
        if s['place'] is not None:
            out.append(('МЕСТО', '%d' % s['place'], s['place_scope'], INK))
        if s['gd'] is not None:
            out.append(('РАЗНИЦА ШАЙБ', F.gd_txt(s['gd']), '', GREEN if s['gd'] > 0 else RED if s['gd'] < 0 else INK))
        m = re.match(r'\s*(ОТ|В|П)\s*(\d+)', str(rec.get('streak') or ''))
        if m and int(m.group(2)) >= 2:
            n = int(m.group(2))
            word = {'В': plural(n, 'победа', 'победы', 'побед'), 'П': plural(n, 'поражение', 'поражения', 'поражений'),
                    'ОТ': plural(n, 'поражение', 'поражения', 'поражений') + ' в ОТ'}[m.group(1)]
            out.append(('СЕРИЯ', '%d' % n, word, GREEN if m.group(1) == 'В' else RED))
        for k, lab in (('pp', 'БОЛЬШИНСТВО'), ('pk', 'МЕНЬШИНСТВО')):
            v = pct(rec.get(k)) if rec.get(k) is not None else None
            if v:
                out.append((lab, v, '', INK))
        return out

    def _cards(self):
        out = []
        for i, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), self.line)):
            w, h = 300, 262
            cd = paper(w, h, 90 + i, (247, 244, 236)).copy()
            d = ImageDraw.Draw(cd)
            d.line((0, 66, w, 66), fill=(200, 70, 70, 200), width=3)
            for y in range(110, h, 40):
                d.line((0, y, w, y), fill=(120, 150, 200, 70), width=2)
            lb, _ = typed(lab, 52, RED, 800, seed=80 + i)
            C.put(cd, lb, 26, 36 - lb.height / 2, anchor='tl')
            vv, _ = typed(C.fmt_k(v), 116, INK, 800, seed=85 + i, max_w=w - 40)
            C.put(cd, vv, w / 2, 168)
            out.append(C.with_shadow(C.rotate(cd, (-2.5, 1.5, -1.0)[i]), 10, 0.6, 9))
        return out

    def _pick_prep(self):
        tm = self.fav
        pg = Image.new('RGBA', (FBW, FBH), (0, 0, 0, 0))
        self.p_page = pg
        ph = C.with_shadow(C.rotate(photo(tm, 390, 430, 9), -3), 10, 0.55, 9)
        self.p_photo = ph
        m = re.match(r'(ПОБЕДА)\s+(.+)$', self.pick1)
        if m:
            ls, hs = [m.group(1), m.group(2)], [(86, 700), (150, 800)]
        else:
            ls, hs = [self.pick1], [(110, 820)]
        self.p_stamp = stamp_box(ls, hs, RED, (46, 22), 11, seed=17, rot=-5, gap=14)
        self.p_splat = ink_splat(self.p_stamp.width + 60, self.p_stamp.height + 50, 9)
        self.p_l3 = None
        if self.pick2:
            im, xs = typed(self.pick2, 60, INK, 800, seed=91, max_w=820)
            self.p_l3 = Line([(im, xs, (FBW - im.width) / 2, 0)])
        self.p_kef = None
        if self.coef:
            im, xs = typed('КЭФ ' + C.fmt_k(self.coef), 124, INK, 800, seed=92)
            self.p_kef = Line([(im, xs, (FBW - im.width) / 2, 0)])
            self.p_ring = marker_ring(im.width + 110, im.height + 70, RED, 9, seed=13)
        self.stamper_im = stamper(self.p_stamp.width - 30, int(self.p_stamp.height * 0.92))

    # ── сцены ──
    def team_page(self, t, key, t0):
        """Раскрытая папка клуба в момент t (слой FBW×FBH)."""
        u = self.u
        T = self.T[key]
        im = self.back.copy()
        im.alpha_composite(T['page'])
        tb = (t - t0) / u                                        # доли от начала сцены
        # фото на скрепке и штамп роли — на 1-ю долю
        q = C.seg(t, t0 + u, t0 + u + 0.16)
        if q > 0:
            s = 1 + 0.35 * (1 - C.out_cubic(q))
            C.put(im, C.scale(T['photo'], s), T['photo_pos'][0], T['photo_pos'][1], min(1.0, q * 2))
            if q >= 1:
                C.put(im, T['clip'], T['clip_pos'][0], T['clip_pos'][1])
            C.put(im, C.scale(T['role'], 1 + 0.6 * (1 - C.out_cubic(q))), T['role_pos'][0], T['role_pos'][1], min(1.0, q * 1.5))
        T['name'].draw(im, C.seg(tb, 0.6, 1.0))
        for i, g in enumerate(T['games']):
            b0 = 1.5 + 0.5 * i
            g['line'].draw(im, C.seg(tb, b0, b0 + 0.36))
            kr = C.seg(tb, b0 + 0.38, b0 + 0.62)
            if kr > 0:
                rg = g['ring']
                C.put(im, rg[int(round(kr * (len(rg) - 1)))], g['ring_pos'][0], g['ring_pos'][1])
        for i, st in enumerate(T['stats']):
            b0 = 3.0 + 0.5 * i
            kv = C.seg(tb, b0, b0 + 0.08)
            if kv > 0:
                C.put(im, st['img'], st['pos'][0], st['pos'][1], kv, anchor='tl')
            kb = C.seg(tb, b0, b0 + 0.34)
            if kb < 1:
                e = C.in_cubic(kb) if kb > 0 else 0.0
                bar = st['bar'] if e < 0.01 else C.rotate(st['bar'], -7 * e)
                C.put(im, bar, st['bar_pos'][0] + 520 * e, st['bar_pos'][1] - 60 * e - (bar.height - st['bar'].height) / 2, 1 - e,
                      anchor='tl')
        return im

    def cover_over(self, page, key, k):
        """Обложка поверх раскрытой папки: k = 1 — закрыта, 0 — раскрыта (переворот вокруг левого корешка)."""
        if k <= 0.001:
            return page
        fc = self.face[key]
        w = max(2, int(FACE_W * abs(math.cos(math.pi / 2 * (1 - k)))))
        im = fc.resize((w, FACE_H), Image.BILINEAR) if w < FACE_W else fc
        dk = 1 - k
        if dk > 0.01:
            arr = np.asarray(im, np.float32).copy()
            arr[..., :3] *= (1 - 0.5 * dk)
            im = Image.fromarray(arr.astype(np.uint8), 'RGBA')
            sh = C.shadow(im, 16, 0.5 * (1 - dk * 0.5))
            C.put(page, sh, w / 2 + 14, FACE_H / 2 + 12)
        C.put(page, im, 0, 0, anchor='tl')
        return page

    def scene_team(self, fr, t, key, t0, t_end, dx=0.0):
        k_open = 1 - C.in_out(C.seg(t, t0 + 0.5 * self.u, t0 + 0.5 * self.u + 0.3))
        pg = self.team_page(t, key, t0)
        pg = self.cover_over(pg, key, k_open)
        C.put(fr, C.shadow(pg, 22, 0.7), FBX + FBW / 2 + dx + 6, FBY + FBH / 2 + 22)
        C.put(fr, pg, FBX + dx, FBY, anchor='tl')

    def scene_intro(self, fr, t, dx=0.0):
        u = self.u
        q = C.out_expo(C.seg(t, 0.05, 0.4))
        st = self.strip
        C.put(fr, st['im'], W / 2 + dx, 350 - 30 * (1 - q), q)
        st['line'].draw(fr, C.seg(t, 0.25, 0.8), W / 2 - st['im'].width / 2 + dx, 350 - st['im'].height / 2 - 30 * (1 - q))
        for s, x, y, tl in (('h', 285, 752, 0.5 * u), ('a', 795, 762, u)):
            k = C.seg(t, tl - 0.22, tl)
            if k <= 0:
                continue
            e = C.in_cubic(k)
            sc = 1.35 - 0.35 * e
            im = self.small[(s, 0.5)]
            C.put(fr, C.scale(im, sc), x + dx + (1 - e) * (-120 if s == 'h' else 120), y - 40 * (1 - e), min(1.0, k * 2.5))
        self.thread(fr, t, (285 + dx - 70, 752 - 190), (795 + dx - 70, 762 - 190), C.seg(t, u + 0.1, 1.5 * u + 0.1))
        for i, cd in enumerate(self.cards):
            tl = 1.5 * u + 0.25 * u * i
            k = C.seg(t, tl - 0.16, tl)
            if k <= 0:
                continue
            e = C.in_cubic(k)
            C.put(fr, C.scale(cd, 1.3 - 0.3 * e), 190 + 350 * i + dx, 1222 - 30 * (1 - e), min(1.0, k * 2.5))

    def thread(self, fr, t, p0, p1, k, sag=60):
        """Красная нить между булавками (k — сколько протянуто)."""
        if k <= 0:
            return
        pts = []
        n = 30
        for i in range(n + 1):
            q = i / n * k
            x = C.lerp(p0[0], p1[0], q)
            y = C.lerp(p0[1], p1[1], q) + sag * 4 * q * (1 - q) * (k ** 0.5)
            pts.append((x, y))
        d = ImageDraw.Draw(fr)
        d.line([(x + 3, y + 5) for x, y in pts], fill=(0, 0, 0, 90), width=6, joint='curve')
        d.line(pts, fill=(176, 22, 30, 255), width=5, joint='curve')
        for p in (p0, pts[-1]):
            C.put(fr, self._pin(), p[0], p[1])

    def _pin(self):
        if 'pin' not in _CACHE:
            pn = C.radial(30, 30, (210, 40, 40), 255, 0.3)
            C.put(pn, C.ellipse(26, 26, (186, 26, 32)), 15, 15)
            C.put(pn, C.ellipse(9, 9, (255, 190, 190)), 11, 10)
            _CACHE['pin'] = C.with_shadow(pn, 4, 0.6, 4)
        return _CACHE['pin']

    def scene_pre(self, fr, t):
        u, D, tp = self.u, self.drop, self.tp
        q = C.out_expo(C.seg(t, tp, tp + 0.35))
        st = self.strip2
        C.put(fr, st['im'], W / 2, 350 - 30 * (1 - q), q)
        st['line'].draw(fr, C.seg(t, tp + 0.05, tp + 0.5), W / 2 - st['im'].width / 2, 350 - st['im'].height / 2 - 30 * (1 - q),
                        cursor=False)
        st3 = self.strip3
        C.put(fr, st3['im'], W / 2, 1270 + 30 * (1 - q), q)
        st3['line'].draw(fr, 1.0, W / 2 - st3['im'].width / 2, 1270 - st3['im'].height / 2 + 30 * (1 - q), cursor=False)
        k = C.in_out(C.seg(t, tp, tp + 0.5 * u))                # заходят с краёв
        k2 = C.in_out(C.seg(t, tp + 0.5 * u, D - u))           # съезжаются
        jit = C.seg(t, D - u, D)
        for s, xs, xm, xe in (('h', -420, 300, 410), ('a', 1500, 780, 670)):
            x = C.lerp(xs, xm, k) + (xe - xm) * k2
            y = 800 + 6 * jit * math.sin(t * 61 + (s == 'a'))
            C.put(fr, self.small[(s, 0.54)], x, y)
        self.thread(fr, t, (410 - 150, 800 - 210), (670 - 140, 800 - 205), 1.0 if k2 > 0 else 0.0, sag=30)
        # штемпель опускается сверху за 0,16 с до дропа
        ks = C.seg(t, D - 0.16, D)
        if ks > 0:
            e = C.in_cubic(ks)
            sc = 1.9 - 0.9 * e
            im = C.scale(self.stamper_im, sc)
            C.put(fr, C.shadow(im, 30, 0.5 + 0.3 * e), 540 + 40 * (1 - e) + 6, 900 + 30 * (1 - e) + 40)
            C.put(fr, im, 540, 900 - 200 * (1 - e))

    def pick_page(self, t):
        u, D = self.u, self.drop
        im = self.back.copy()
        C.put(im, self.p_photo, FBW / 2, 268)
        C.put(im, clip_sprite(1.2), FBW / 2 - 110, 54)
        sy = 640
        C.put(im, self.p_splat, FBW / 2, sy)
        C.put(im, self.p_stamp, FBW / 2, sy)
        y3 = 850
        if self.p_l3 is not None:
            self.p_l3.draw(im, C.seg(t, D + 0.5 * u, D + 0.85 * u), 0, y3)
        if self.p_kef is not None:
            yk = 990 if self.p_l3 is not None else 900
            self.p_kef.draw(im, C.seg(t, D + u, D + 1.3 * u), 0, yk)
            kr = C.seg(t, D + 2 * u, D + 2.4 * u)
            if kr > 0:
                rg = self.p_ring
                C.put(im, rg[int(round(kr * (len(rg) - 1)))], FBW / 2, yk)
        return im

    def scene_pick(self, fr, t):
        u, D, tc = self.u, self.drop, self.t_cta
        pg = self.pick_page(t)
        kc = C.in_out(C.seg(t, tc, tc + 0.45))
        s = 1 - 0.22 * kc
        x = W / 2
        y = FBY + FBH / 2 - (FBY + FBH / 2 - (238 + FBH * s / 2)) * kc
        pgs = C.scale(pg, s) if s < 0.999 else pg
        C.put(fr, C.shadow(pgs, 22, 0.7), x + 6, y + 22)
        C.put(fr, pgs, x, y)
        # штемпель уходит вверх после удара
        kl = C.seg(t, D, D + 0.32)
        if kl < 1:
            e = C.out_cubic(kl)
            im = C.scale(self.stamper_im, 1 + 0.9 * e)
            C.put(fr, im, 540 + 60 * e, FBY + 640 - 420 * e, 1 - e)

    # ── свет ──
    def lamp_k(self, t):
        u, D, tp = self.u, self.drop, self.tp
        k = 1.0
        if t < 0.35:
            k = 0.25 + 0.75 * C.out_cubic(C.seg(t, 0, 0.35))
        if tp <= t < D - u:                                      # мигает
            i = int(t * 30)
            r = ((i * 7919) % 97) / 97
            k = 0.72 if r < 0.22 else 1.0
        elif D - u <= t < D:                                     # в треке пауза — свет почти гаснет
            k = 0.2
            for tf in (D - 0.72 * u, D - 0.4 * u):
                if tf <= t < tf + 0.07:
                    k = 0.75
        elif t >= D:
            k = 1 + 0.75 * math.exp(-(t - D) / 0.12)
        return k

    def frame(self, t):
        u, D = self.u, self.drop
        fr = desk().copy()
        tr = 0.22                                                # смахивание папок перед долей
        if t < self.t1:
            dx = -W * C.in_cubic(C.seg(t, self.t1 - tr, self.t1))
            self.scene_intro(fr, t, dx)
        if self.t1 - tr <= t < self.t2:
            dx = W * (1 - C.out_cubic(C.seg(t, self.t1 - tr, self.t1))) - W * C.in_cubic(C.seg(t, self.t2 - tr, self.t2))
            self.scene_team(fr, t, 'h', self.t1, self.t2, dx)
        if self.t2 - tr <= t < self.tp:
            dx = W * (1 - C.out_cubic(C.seg(t, self.t2 - tr, self.t2))) - W * C.in_cubic(C.seg(t, self.tp - tr, self.tp))
            self.scene_team(fr, t, 'a', self.t2, self.tp, dx)
        if self.tp <= t < D:
            self.scene_pre(fr, t)
        if t >= D:
            self.scene_pick(fr, t)
        # пылинки в конусе лампы
        for x0, y0, sp, br, ph, sz in self.dust:
            y = 240 + (y0 - 240 - sp * t) % 1260
            x = x0 + 26 * math.sin(t * 0.7 * sz + ph)
            C.put(fr, C.scale(self.dot, sz), x, y, 0.55 * br)
        C.put(fr, self.tag, W / 2, TAG_Y, C.seg(t, 0, 0.3) * 0.95)
        ha = C.seg(t, 0.2, 0.5) * (1 - C.seg(t, self.t_cta, self.t_cta + 0.2))
        C.put(fr, self.handle_im, W / 2, HY, 0.92 * ha)
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.05, self.t_cta + 0.5))
            C.put(fr, self.tg, W / 2, 1318 + 60 * (1 - q), q)
        # свет: лампа (мигание/всплеск) + полосы жалюзи + конус
        lamp, blind, cone = lights()
        k = self.lamp_k(t)
        arr = np.asarray(fr.convert('RGB'), np.float32)
        if abs(k - 1) < 1e-3:
            arr *= _CACHE['lsum']
            arr += cone
        else:
            arr *= lamp * k + blind
            arr += cone * min(k, 1.6)
        fr = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
        # камера: толчки на склейках, удар на дропе, пульс на долях
        z, dx, dy, rot = 1.0, 0.0, 0.0, 0.0
        for th in (self.t1, self.t2):
            sx, sy = C.shake(t, th, 9, 0.25)
            dx, dy = dx + sx, dy + sy
        for th in (0.5 * u, u, 1.5 * u + 0.5 * u):                # папки и карточки ложатся
            sx, sy = C.shake(t, th, 4, 0.18)
            dx, dy = dx + sx, dy + sy
        if t >= D:
            kk = 1 - C.seg(t, D, D + 0.45)
            sx, sy = C.shake(t, D, 30, 0.5)
            dx, dy = dx + sx, dy + sy
            rot = 1.2 * kk ** 2 * math.sin((t - D) * 40)
            z += 0.07 * kk ** 2
            if t < self.t_cta:
                z += 0.012 * math.exp(-(((t - D) / u) % 1.0) * 7)
        fr = C.zoom(fr, z, dx=dx, dy=dy, rot=rot)
        return C.grain(fr, t, 5)
