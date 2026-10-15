# -*- coding: utf-8 -*-
"""Кастомные эмодзи Telegram для постов @jarvibet: статичные PNG 100×100 с прозрачным фоном.

Рисуем в 8× (800×800) в «единицах» 0…100 и уменьшаем LANCZOS. Единый язык семейства:
  • свет сверху-слева: градиент светлее к верху, блик по верхне-левой кромке, тень по нижне-правой;
  • тёмный контур (KEY) одинаковой толщины вокруг силуэта и мягкая падающая тень вниз;
  • белые знаки на «шайбах»-жетонах — штрих 12 ед., скруглённые концы, своя тень;
  • палитра бренда: тёмный BG, золото (КХЛ), лёд (НХЛ), зелёный (заход), красный (минус), белый;
  • узор Versus — концентрические кольца тон-в-тон на плоскостях; шрифты Montserrat 900 (крупные знаки)
    и Tektur 900 узкий (подписи КХЛ / LIVE / МСК — самые высокие буквы на ширину 100 px).
Логотипов лиг/клубов, букмекеров, «100%»/«гарант» нет.

Запуск:  python team/emoji/make.py [папка] [ключи…]          → <папка>/<ключ>.png
         python team/emoji/make.py [папка] --preview          → ещё sheet.png и inline.png
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, '..', '..', 'render', 'fonts')
DEFAULT_OUT = '/tmp/claude-0/-home-user--kaper-jarvis-bot/750ccff3-fed4-56c4-8b4f-e7d578ed1f4d/scratchpad/emoji'

S = 8                       # пикселей на единицу (100 ед. = 800 px)
N = 100 * S
SIZE = 100                  # итоговый размер эмодзи Telegram

BG = (22, 20, 24)
GOLD = (255, 194, 61)
ICE = (122, 202, 255)
GREEN = (46, 214, 120)
RED = (240, 82, 70)
WHITE = (250, 250, 252)
KEY = (14, 12, 17)          # контур силуэта
STEEL = (196, 210, 224)     # «металл» в ледяном оттенке

GLYPH_W = 12                # толщина штриха знаков на жетонах, ед.


# ───────────────────────────── базовые помощники ─────────────────────────────

def u(v):
    return v * S


def mix(c, k):
    """k > 0 — к белому, k < 0 — к чёрному."""
    t = (255, 255, 255) if k > 0 else (0, 0, 0)
    k = abs(k)
    return tuple(int(round(a + (b - a) * k)) for a, b in zip(c[:3], t))


def font(name, size, wght=None, wdth=None):
    f = ImageFont.truetype(os.path.join(FD, name), int(size))
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
TEK = ('Tektur[wdth,wght].ttf', 900, 75)


def new():
    return Image.new('RGBA', (N, N), (0, 0, 0, 0))


def M():
    return Image.new('L', (N, N), 0)


def md(m):
    return ImageDraw.Draw(m)


def ell(m, cx, cy, rx, ry=None, fill=255):
    ry = rx if ry is None else ry
    md(m).ellipse((u(cx - rx), u(cy - ry), u(cx + rx), u(cy + ry)), fill=fill)
    return m


def poly(m, pts, fill=255):
    md(m).polygon([(u(x), u(y)) for x, y in pts], fill=fill)
    return m


def rrect(m, box, r, fill=255):
    x0, y0, x1, y1 = box
    md(m).rounded_rectangle((u(x0), u(y0), u(x1), u(y1)), radius=u(r), fill=fill)
    return m


def stroke(m, pts, w, fill=255, caps=True):
    d = md(m)
    d.line([(u(x), u(y)) for x, y in pts], fill=fill, width=int(u(w)), joint='curve')
    if caps:
        for x, y in (pts[0], pts[-1]):
            d.ellipse((u(x - w / 2), u(y - w / 2), u(x + w / 2), u(y + w / 2)), fill=fill)
    return m


def arc_pts(cx, cy, r, a0, a1, n=48):
    """Точки дуги, углы в градусах (0 — вправо, 90 — вниз)."""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def ring_mask(cx, cy, r_out, r_in, ry_k=1.0):
    m = ell(M(), cx, cy, r_out, r_out * ry_k)
    ell(m, cx, cy, r_in, r_in * ry_k, fill=0)
    return m


def shift(m, dx, dy):
    o = Image.new(m.mode, m.size, 0)
    o.paste(m, (int(dx), int(dy)))
    return o


def mul(a, b):
    return ImageChops.multiply(a, b)


def sub(a, b):
    return ImageChops.subtract(a, b)


def union(*ms):
    o = ms[0]
    for m in ms[1:]:
        o = ImageChops.lighter(o, m)
    return o


def scale(m, k):
    return m.point(lambda v: int(v * k))


def blur(m, r):
    return m.filter(ImageFilter.GaussianBlur(u(r)))


def soften(m, r):
    """Скруглить острые углы маски (размыть и снова сделать край чётким)."""
    return blur(m, r).point(lambda v: 0 if v < 100 else 255 if v > 156 else (v - 100) * 255 // 56)


def erode(m, r):
    """Сузить маску на ~r ед. (размытие + высокий порог)."""
    return blur(m, r * 0.75).point(lambda v: 0 if v < 235 else (v - 235) * 255 // 20)


def put(base, paint, mask, alpha=1.0):
    """Залить mask краской (цвет или RGB-картинка) поверх base."""
    if isinstance(paint, tuple):
        paint = Image.new('RGB', (N, N), paint[:3])
    a = mask if alpha >= 1 else scale(mask, alpha)
    lay = paint.convert('RGB')
    lay.putalpha(a)
    base.alpha_composite(lay)


_Y, _X = np.mgrid[0:N, 0:N].astype(np.float32) / S       # координаты в единицах


def lin(stops, mask=None, direction=(0.32, 1.0), box=None):
    """Линейный градиент по направлению света (сверху-слева → вниз-вправо), растянутый на bbox маски.
    stops — список цветов (равномерно) или пар (t, цвет)."""
    if box is None:
        bb = mask.getbbox() if mask is not None else None
        box = (0, 0, 100, 100) if bb is None else tuple(v / S for v in bb)
    x0, y0, x1, y1 = box
    dx, dy = direction
    n = math.hypot(dx, dy)
    dx, dy = dx / n, dy / n
    corners = [x * dx + y * dy for x in (x0, x1) for y in (y0, y1)]
    lo, hi = min(corners), max(corners)
    t = np.clip((_X * dx + _Y * dy - lo) / max(hi - lo, 1e-6), 0, 1)
    return _ramp(t, stops)


def rad(stops, cx, cy, r):
    t = np.clip(np.hypot(_X - cx, _Y - cy) / r, 0, 1)
    return _ramp(t, stops)


def _ramp(t, stops):
    if not isinstance(stops[0][0], (int, float)) or len(stops[0]) == 3:
        stops = [(i / (len(stops) - 1), c) for i, c in enumerate(stops)]
    out = np.zeros(t.shape + (3,), np.float32)
    ts = [s[0] for s in stops]
    for ch in range(3):
        out[..., ch] = np.interp(t, ts, [s[1][ch] for s in stops])
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')


def bevel(base, mask, hi=0.55, lo=0.45, d=2.4, b=1.5):
    """Объём: светлая кромка сверху-слева, тёмная снизу-справа (внутри маски)."""
    dx, dy = u(d) * 0.55, u(d)
    h = mul(blur(sub(mask, shift(mask, dx, dy)), b), mask)
    s = mul(blur(sub(mask, shift(mask, -dx, -dy)), b), mask)
    put(base, (255, 255, 255), h, hi)
    put(base, (0, 0, 0), s, lo)


def gloss(base, mask, box, alpha=0.22, b=4):
    """Мягкий блик-эллипс в верхней части формы."""
    g = M()
    md(g).ellipse(tuple(u(v) for v in box), fill=255)
    put(base, (255, 255, 255), mul(blur(g, b), mask), alpha)


def rings(base, mask, cx, cy, step=6.0, alpha=0.08, color=(255, 255, 255)):
    """Узор Versus: концентрические кольца тон-в-тон, обрезанные маской."""
    r = np.hypot(_X - cx, _Y - cy)
    band = np.clip(np.sin(r / step * 2 * np.pi) * 3, 0, 1) * 255
    m = Image.fromarray(band.astype(np.uint8), 'L')
    put(base, color, mul(m, mask), alpha)


def cast(base, glyph, surface, alpha=0.42, d=2.2, b=1.4):
    """Тень знака на поверхности (вниз-вправо), обрезанная поверхностью."""
    sh = blur(shift(glyph, u(d) * 0.35, u(d)), b)
    put(base, (0, 0, 0), mul(sh, surface) if surface is not None else sh, alpha)


def glyph(base, gm, surface, color=WHITE, shade=None, alpha=0.42):
    """Знак на жетоне: тень + заливка с лёгким градиентом + фаска."""
    cast(base, gm, surface, alpha)
    shade = shade or mix(color, -0.13)
    put(base, lin([mix(color, 0.3), color, shade], gm), gm)
    bevel(base, gm, hi=0.45, lo=0.22, d=1.6, b=1.0)


def text_mask(text, spec, cx, cy, w, h, squeeze=1.0):
    """Маска текста максимального кегля, чьи «чернила» влезают в w×h ед.; центр чернил в (cx, cy).
    squeeze < 1 — сжать по ширине (выше буквы при той же ширине)."""
    name, wght, wdth = spec
    size = int(u(h) * 1.8)
    while size > 8:
        f = font(name, size, wght, wdth)
        l, t, r, b = f.getbbox(text)
        if (r - l) * squeeze <= u(w) and b - t <= u(h):
            break
        size -= max(1, size // 60)
    m = M()
    md(m).text((u(50) - (l + r) / 2, u(cy) - (t + b) / 2), text, font=f, fill=255)
    if squeeze != 1.0:
        sq = m.resize((int(N * squeeze), N), Image.LANCZOS)
        m = M()
        m.paste(sq, ((N - sq.width) // 2, 0))
    return shift(m, u(cx - 50), 0)


def outline(a, key=1.7):
    """Маска тёмного контура вокруг альфы a."""
    return blur(a, key * 0.55).point(lambda v: 0 if v < 6 else min(255, v * 4))


def fade(im, k):
    """RGBA-слой с прозрачностью × k."""
    if k >= 1:
        return im
    o = im.copy()
    o.putalpha(scale(im.getchannel('A'), max(0.0, k)))
    return o


def finish(art, key=1.7, drop=0.42, lift=0.0, fx=()):
    """Контур + падающая тень, уменьшение 800 → 100 LANCZOS.
    Для анимации (по умолчанию ничего не меняют):
      lift — рисунок поднят на lift ед. над «столом»: тень остаётся внизу, мягче и слабее;
      fx — [(слой RGBA, прозрачность, с_контуром)]: элементы, которые плавно гаснут/появляются.
           С контуром — получают свою обводку и ложатся под основной рисунок; без — свет поверх всего."""
    a = art.getchannel('A')
    k = outline(a, key)
    out = new()
    under = [(lay, op, outline(lay.getchannel('A'), key)) for lay, op, ol in fx if ol and op > 0]
    sh = k
    for _, op, kk in under:
        sh = union(sh, scale(kk, op))
    put(out, (0, 0, 0), blur(shift(sh, 0, u(2.0 + lift)), 2.0 + lift * 0.5), drop / (1 + lift * 0.15))
    put(out, KEY, k, 0.92)
    for lay, op, kk in under:
        e = new()
        put(e, KEY, kk, 0.92)
        e.alpha_composite(lay)
        out.alpha_composite(fade(e, op))
    out.alpha_composite(art)
    for lay, op, ol in fx:
        if not ol and op > 0:
            out.alpha_composite(fade(lay, op))
    return out.resize((SIZE, SIZE), Image.LANCZOS)


# ───────────────────────────── помощники анимации ─────────────────────────────

def xform(m, ang=0.0, k=1.0, dx=0.0, dy=0.0, cx=50, cy=50, kx=None, ky=None):
    """Маска или слой: поворот на ang° (по часовой), масштаб k (или kx/ky) вокруг (cx, cy) ед., сдвиг (dx, dy) ед.
    Без параметров возвращает тот же объект (статика не меняется)."""
    kx = k if kx is None else kx
    ky = k if ky is None else ky
    if not ang and kx == 1 and ky == 1 and not dx and not dy:
        return m
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    a, b, d, e = c / kx, s / kx, -s / ky, c / ky          # обратная к R(ang)·diag(kx, ky)
    X, Y = u(cx + dx), u(cy + dy)
    data = (a, b, u(cx) - a * X - b * Y, d, e, u(cy) - d * X - e * Y)
    return m.transform(m.size, Image.AFFINE, data, resample=Image.BICUBIC)


def rotp(pts, ang, cx, cy):
    """Повернуть точки на ang° по часовой вокруг (cx, cy)."""
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def part(pts, f):
    """Начальная доля f (0…1) ломаной по длине — «знак рисуется пером»."""
    if f >= 1:
        return pts
    lens = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    left = sum(lens) * max(0.0, f)
    out = [pts[0]]
    for (a, b), L in zip(zip(pts, pts[1:]), lens):
        if left >= L:
            out.append(b)
            left -= L
            continue
        k = left / L if L else 0.0
        out.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
        break
    return out


def sheen(base, mask, pos, width=5.0, alpha=0.6, slant=0.6):
    """Блик-полоса «/», пробегающая по маске слева направо: pos 0…1 (на краях — за пределами формы)."""
    bb = mask.getbbox()
    if bb is None:
        return
    x0, y0, x1, y1 = (v / S for v in bb)
    lo, hi = x0 + y0 * slant - width * 2.5, x1 + y1 * slant + width * 4
    c = lo + (hi - lo) * pos
    d = _X + _Y * slant - c
    band = np.exp(-(d / width) ** 2) + 0.6 * np.exp(-((d + width * 2.4) / (width * 0.3)) ** 2)
    m = Image.fromarray(np.clip(band * 255, 0, 255).astype(np.uint8), 'L')
    put(base, (255, 255, 255), mul(m, mask), alpha)


def sparkle_pts(sx, sy, r, ri):
    """Четырёхлучевая искра."""
    return [(sx, sy - r), (sx + ri, sy - ri), (sx + r, sy), (sx + ri, sy + ri), (sx, sy + r), (sx - ri, sy + ri),
            (sx - r, sy), (sx - ri, sy - ri)]


def sparkle(base, sx, sy, r, ang=0.0):
    """Искра как у кубика льда: мягкое свечение + белая звёздочка (r — радиус луча, ед.; ang — поворот, °)."""
    if r <= 0.3:
        return
    pts = sparkle_pts(sx, sy, r, r * 0.23)
    sp = poly(M(), rotp(pts, ang, sx, sy) if ang else pts)
    put(base, (255, 255, 255), blur(sp, 2.5 * r / 14), 0.6)
    put(base, (255, 255, 255), sp)


# ───────────────────────────── общие детали ─────────────────────────────

TK = dict(cx=50, cy=46, r=41, th=6)       # геометрия жетона-шайбы (вид сверху с толщиной)


def token(art, col, rim=None, dark=False):
    """Жетон-шайба: торец (толщина снизу), лицевая плоскость с градиентом, кольца Versus, фаска.
    rim — цвет кромки (золотой ободок). → маска лицевой плоскости (для теней знака)."""
    cx, cy, r, th = TK['cx'], TK['cy'], TK['r'], TK['th']
    side = ell(M(), cx, cy + th, r)
    md(side).rectangle((u(cx - r), u(cy), u(cx + r), u(cy + th)), fill=255)
    side = soften(side, 0.6)
    face = ell(M(), cx, cy, r)
    if dark:
        put(art, lin([(34, 32, 38), (8, 8, 10)], side), side)
        put(art, lin([(64, 61, 70), (34, 32, 38), (16, 15, 19)], face), face)
    else:
        put(art, lin([mix(col, -0.38), mix(col, -0.62)], side), side)
        put(art, lin([mix(col, 0.32), col, mix(col, -0.16)], face), face)
    inner = face
    if rim:
        rm = ring_mask(cx, cy, r, r - 5.5)
        put(art, lin([mix(rim, 0.55), rim, mix(rim, -0.4)], rm), rm)
        bevel(art, rm, hi=0.5, lo=0.45, d=1.6, b=0.8)
        inner = ell(M(), cx, cy, r - 5.5)
        # внутренняя тень от ободка
        put(art, (0, 0, 0), mul(blur(sub(inner, shift(inner, u(0.6), u(1.6))), 1.2), inner), 0.5)
        # ободок виден и на торце: тонкая золотая линия снизу
        edge = sub(side, shift(face, 0, -u(0.2)))
        put(art, mix(rim, -0.35), mul(edge, ring_mask(cx, cy + th, r, r - 2.2)), 0.9)
    rings(art, inner, cx - 20, cy - 24, step=6.5, alpha=0.07 if not dark else 0.05)
    if not rim:
        bevel(art, face, hi=0.5, lo=0.35)
        # тонкое внутреннее кольцо — как у фишки/шайбы
        put(art, (255, 255, 255), ring_mask(cx, cy, r - 6, r - 7.6), 0.18)
    gloss(art, inner, (cx - 30, cy - 38, cx + 18, cy - 4), alpha=0.16 if not dark else 0.08)
    return inner


def puck3d(art, cx, cy, rx, ry, h, rim=GOLD, rim_w=2.6):
    """Шайба в 3/4: чёрный торец с насечкой, верхняя плоскость, золотая кромка-блик."""
    side = ell(M(), cx, cy + h, rx, ry)
    md(side).rectangle((u(cx - rx), u(cy), u(cx + rx), u(cy + h)), fill=255)
    side = soften(side, 0.4)
    # цилиндр: светлее у левой трети, темнее к краям
    put(art, lin([(10, 10, 12), (46, 44, 52), (26, 25, 30), (6, 6, 8)], side, direction=(1, 0)), side)
    # насечка на торце
    kn = M()
    d = md(kn)
    for i in range(-14, 15):
        x = cx + rx * math.sin(i / 14 * 1.35)
        d.line((u(x), u(cy + ry * 0.2), u(x), u(cy + h + ry * 0.75)), fill=255, width=max(2, int(u(0.7))))
    put(art, (0, 0, 0), mul(kn, sub(side, ell(M(), cx, cy, rx, ry))), 0.35)
    top = ell(M(), cx, cy, rx, ry)
    put(art, lin([(70, 67, 76), (34, 32, 38), (14, 13, 16)], top), top)
    rings(art, top, cx - rx * 0.45, cy - ry * 0.8, step=max(3.0, rx / 5), alpha=0.05)
    if rim:
        rm = ring_mask(cx, cy, rx, rx - rim_w, ry_k=ry / rx)
        put(art, lin([mix(rim, 0.6), rim, mix(rim, -0.45)], rm, direction=(0.6, 1)), rm)
        bottom = sub(ring_mask(cx, cy + h, rx, rx - rim_w * 0.7, ry_k=ry / rx), shift(top, 0, u(h * 0.5)))
        put(art, mix(rim, -0.45), mul(bottom, side), 0.85)
    gloss(art, top, (cx - rx * 0.8, cy - ry * 0.9, cx + rx * 0.1, cy + ry * 0.2), alpha=0.2, b=max(1.0, ry / 4))
    return union(side, top)


def plate(art, box, r, col, dark_text=True):
    """Плашка в стиле Versus (как плашки линии П1/Х/П2): градиент, кольца, фаска."""
    m = rrect(M(), box, r)
    put(art, lin([mix(col, 0.35), col, mix(col, -0.22)], m), m)
    rings(art, m, box[0] + 4, box[1] - 4, step=5.5, alpha=0.08 if dark_text else 0.06,
          color=(255, 255, 255))
    bevel(art, m, hi=0.55, lo=0.4, d=2.0, b=1.2)
    return m


def star_pts(cx, cy, ro, ri, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        a = math.radians(rot + i * 180 / n)
        rr = ro if i % 2 == 0 else ri
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def faceted_star(art, cx, cy, ro, ri, col, surface=None):
    """Золотая звезда с гранями: у каждого луча светлая и тёмная половины (свет сверху-слева)."""
    pts = star_pts(cx, cy, ro, ri)
    sm = poly(M(), pts)
    cast(art, sm, surface, 0.5, d=2.4, b=1.6)
    put(art, lin([mix(col, 0.3), col, mix(col, -0.1)], sm), sm)
    for i in range(0, 10, 2):
        tip = pts[i]
        for j in (i - 1, i + 1):
            inner = pts[j % 10]
            # нормаль грани: насколько смотрит на свет (вверх-влево)
            mx, my = (tip[0] + inner[0] + cx) / 3 - cx, (tip[1] + inner[1] + cy) / 3 - cy
            lit = -(mx * -0.55 + my * -0.83) / (math.hypot(mx, my) + 1e-6)
            fm = poly(M(), [(cx, cy), tip, inner])
            if lit < 0:
                put(art, (255, 255, 255), fm, min(0.4, -lit * 0.4))
            else:
                put(art, mix(col, -0.5), fm, min(0.45, lit * 0.45))
    bevel(art, sm, hi=0.35, lo=0.2, d=1.2, b=0.8)
    return sm


def smooth_closed(pts, k=10):
    """Catmull-Rom по замкнутому контуру."""
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        for s in range(k):
            t = s / k
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    return out


# ───────────────────────────── итоги ─────────────────────────────

CHECK = [(30.5, 47), (44, 60.5), (69.5, 33.5)]


def e_zahod(draw=1.0, alpha=1.0, shine=None):
    """Галочка на зелёном жетоне.
    Анимация: draw — доля галочки, прорисованной пером (0…1); alpha — её непрозрачность; shine — блик 0…1."""
    art = new()
    face = token(art, GREEN)
    if draw > 0 and alpha > 0:
        g = stroke(M(), part(CHECK, draw), GLYPH_W)
        glyph(art, g if alpha >= 1 else scale(g, alpha), face)
    if shine is not None:
        sheen(art, face, shine)
    return art


def e_minus(k=1.0, ang=0.0):
    """Крест на красном жетоне. Анимация: k — масштаб креста (0 — нет), ang — его поворот, °."""
    art = new()
    face = token(art, RED)
    if k > 0:
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))

        def p(dx, dy):
            return 50 + (dx * c - dy * s) * k, 46 + (dx * s + dy * c) * k

        g = union(stroke(M(), [p(-15, -15), p(15, 15)], GLYPH_W * k), stroke(M(), [p(15, -15), p(-15, 15)], GLYPH_W * k))
        glyph(art, g, face)
    return art


def e_vozvrat(ang=0.0):
    """Стрелка возврата на ледяном жетоне. Анимация: ang — поворот стрелки вокруг центра жетона, ° (по часовой)."""
    art = new()
    face = token(art, ICE)
    ox, oy = 3, 0
    path = [(38 + ox, 36 + oy), (54 + ox, 36 + oy)] + arc_pts(54 + ox, 50 + oy, 14, -90, 90, 32)[1:] + [(40 + ox, 64 + oy)]
    tip = [(21 + ox, 36 + oy), (40 + ox, 22.5 + oy), (40 + ox, 49.5 + oy)]
    if ang:
        path, tip = rotp(path, ang, TK['cx'], TK['cy']), rotp(tip, ang, TK['cx'], TK['cy'])
    g = stroke(M(), path, 11)
    g = union(g, poly(M(), tip))
    g = soften(g, 0.5)
    glyph(art, g, face)
    return art


HG_TOP, HG_BOT, HG_NECK = 18, 82, 50                 # песочные часы: верх/низ колб и горлышко, ед.
PILE_DX = [0, 6, 16, 28, 60]                          # профиль горки: |x − 50| → насколько ниже вершины
PILE_DY = [0, 1.5, 7, 17, 44]


def _hg_bulb(y0, y1):
    pts_l, pts_r = [], []
    for i in range(25):
        t = i / 24
        y = y0 + (y1 - y0) * t
        tt = abs(y - HG_NECK) / abs(y0 - HG_NECK)     # 1 у крышки, 0 у горлышка
        hw = 3.2 + 21 * math.sqrt(max(0.0, 1 - (1 - tt) ** 2)) ** 1.0 * (0.25 + 0.75 * tt ** 0.35)
        pts_l.append((50 - hw, y))
        pts_r.append((50 + hw, y))
    return pts_l + pts_r[::-1]


def _hg_glass():
    return soften(union(poly(M(), _hg_bulb(HG_TOP, HG_NECK)), poly(M(), _hg_bulb(HG_BOT, HG_NECK))), 0.6)


def _hg_static_sand(glass):
    top_sand = mul(glass, poly(M(), [(0, 37), (100, 37), (100, 51), (0, 51)]))
    pile = mul(glass, soften(poly(M(), [(22, 82), (34, 72), (44, 66.5), (50, 65), (56, 66.5), (66, 72), (78, 82)]), 2))
    return top_sand, pile


_HG_VOL = []


def _hg_volume():
    """Весь песок статичной картинки (сверху + горка), в «пикселях» маски 8×."""
    if not _HG_VOL:
        _HG_VOL.append(sum(float(np.asarray(m, np.float32).sum()) / 255 for m in _hg_static_sand(_hg_glass())))
    return _HG_VOL[0]


def _sand_fill(bulb, vol, mound):
    """Песок объёмом vol в колбе bulb (маска в осях холста): лежит внизу, поверхность — ровный уровень
    плюс горка высотой mound (1 — как на статичной картинке, 0 — ровно)."""
    if vol <= 0:
        return M()
    b = np.asarray(bulb, np.float32) / 255
    g = _Y - mound * np.interp(np.abs(_X - 50), PILE_DX, PILE_DY)
    sel = b > 0.004
    gv, bv = g[sel], b[sel]
    order = np.argsort(-gv)
    cum = np.cumsum(bv[order])
    lvl = gv[order][min(int(np.searchsorted(cum, vol)), len(cum) - 1)]
    reg = Image.fromarray(((g > lvl) * 255).astype(np.uint8), 'L')
    return mul(bulb, soften(reg, 2))


def e_zhdem(sand=None, ang=0.0, k=1.0, mound=1.0, stream=(0.0, 1.0), grain=None):
    """Песочные часы: золотые крышки и стойки, стеклянные колбы, золотой песок.
    Анимация: sand — доля песка, пересыпавшаяся в нижнюю колбу (None — как на статичной картинке);
    ang, k — поворот (переворот часов) и масштаб вокруг центра, свет остаётся сверху-слева;
    mound — высота горки внизу (1…0); stream — струйка: доли пути от горлышка до горки (от, до) или None;
    grain — фаза бегущих по струйке песчинок (0…1)."""
    art = new()
    # часы симметричны: после 90° рисуем поворот на ang − 180 с переставленными колбами —
    # к концу переворота геометрия ровно совпадает со стоячими часами (бесшовная петля)
    swap = ang > 90
    ra = ang - 180 if swap else ang

    def T(m):
        return xform(m, ra, k)

    glass = T(_hg_glass())
    # стойки сзади
    posts = T(union(rrect(M(), (17, 14, 23, 86), 2), rrect(M(), (77, 14, 83, 86), 2)))
    put(art, lin([mix(GOLD, -0.15), mix(GOLD, -0.55)], posts, direction=(1, 0.2)), posts)
    bevel(art, posts, hi=0.4, lo=0.3, d=1.2, b=0.6)
    # стекло
    put(art, lin([(235, 246, 255), (150, 190, 220)], glass), glass, 0.38)
    # песок: остаток сверху и горка снизу, струйка
    seg = None
    if sand is None:
        top_sand, pile = _hg_static_sand(glass)
        st = stroke(M(), [(50, 50), (50, 66)], 2.6)
        sm = union(top_sand, pile, st)
    else:
        vol = _hg_volume()
        up = mul(glass, T(poly(M(), [(0, 0), (100, 0), (100, HG_NECK), (0, HG_NECK)])))
        dn = mul(glass, T(poly(M(), [(0, HG_NECK), (100, HG_NECK), (100, 100), (0, 100)])))
        if swap:
            up, dn = dn, up
        sm = union(_sand_fill(up, (1 - sand) * vol, 0.0), _sand_fill(dn, sand * vol, mound))
        if stream is not None and not ra and k == 1:
            col = np.nonzero(np.asarray(sm)[int(u(HG_NECK + 2)):, int(u(50))] > 127)[0]
            peak = HG_NECK + 2 + (col[0] / S if len(col) else HG_BOT - 2)
            y0, y1 = (HG_NECK + (peak - HG_NECK) * f for f in stream)
            if y1 - y0 > 0.2:
                sm = union(sm, stroke(M(), [(50, y0), (50, y1)], 2.6))
                seg = (y0, y1)
    put(art, lin([mix(GOLD, 0.25), GOLD, mix(GOLD, -0.3)], sm), sm)
    bevel(art, sm, hi=0.35, lo=0.25, d=1.2, b=0.8)
    if seg and grain is not None:
        for j in range(3):
            y = seg[0] + (seg[1] - seg[0]) * ((grain + j / 3) % 1)
            put(art, (255, 246, 214), ell(M(), 50, y, 0.75, 1.3), 0.9)
    # контур стекла и блики (блики — отражение света: не вращаются, гаснут на ребре)
    edge = sub(glass, erode(glass, 2.6))
    put(art, (245, 250, 255), edge, 0.95)
    hl = union(stroke(M(), [(31, 22), (33, 30), (38, 37)], 2.6), stroke(M(), [(30, 78), (31.5, 72)], 2.6))
    if ra or k != 1:
        put(art, (255, 255, 255), mul(xform(hl, 0, k), glass), 0.9 * abs(math.cos(math.radians(ra))))
    else:
        put(art, (255, 255, 255), hl, 0.9)
    # крышки
    for y in (8, 82):
        cap = T(rrect(M(), (13, y, 87, y + 10), 4))
        put(art, lin([mix(GOLD, 0.45), GOLD, mix(GOLD, -0.38)], cap), cap)
        bevel(art, cap, hi=0.55, lo=0.45, d=1.8, b=0.9)
    return art


FLAME_OUT = [(26, 72), (17, 54), (21, 36), (29, 42), (32, 24), (41, 31), (50, 6), (59, 22), (67, 13), (72, 32), (82, 45),
             (80, 62), (74, 72)]
FLAME_IN = [(36, 72), (31, 58), (37, 45), (43, 51), (49, 28), (57, 44), (63, 39), (67, 56), (64, 72)]
FLAME_CORE = [(43, 72), (41, 62), (47, 54), (50, 46), (55, 56), (58, 64), (57, 72)]


def flicker(pts, ph):
    """Колыхание пламени: гладкое поле смещений, растёт к кончикам (основание у шайбы неподвижно).
    ph — фаза 0…1; только целые гармоники, поэтому ph = 1 совпадает с ph = 0 (бесшовная петля)."""
    tau = 2 * math.pi
    out = []
    for x, y in pts:
        h = min(1.0, max(0.0, (70 - y) / 58)) ** 1.25
        dx = h * (2.0 * math.sin(tau * 2 * ph - y / 8.5 + 0.6) + 0.8 * math.sin(tau * 3 * ph + x / 6.5 + 1.3))
        dy = h * (1.6 * math.sin(tau * 2 * ph + x / 9 - y / 14) + 0.7 * math.sin(tau * 3 * ph + x / 5 + 2.1))
        out.append((x + dx, y + dy))
    return out


def e_seriya(ph=None):
    """Пламя над шайбой. Анимация: ph — фаза колыхания языков 0…1 (None — статичная форма)."""
    art = new()
    po, pi, pc = FLAME_OUT, FLAME_IN, FLAME_CORE
    if ph is not None:
        po, pi, pc = flicker(po, ph), flicker(pi, ph), flicker(pc, ph)
    outer = smooth_closed(po)
    inner = smooth_closed(pi)
    om = poly(M(), outer)
    im = poly(M(), inner)
    glow = blur(om, 5)
    put(art, (255, 120, 50), glow, 0.35 if ph is None else 0.35 + 0.06 * math.sin(2 * math.pi * 3 * ph))
    put(art, lin([(255, 70, 58), (250, 110, 50), (255, 160, 60)], om, direction=(0.1, 1)), om)
    bevel(art, om, hi=0.3, lo=0.25, d=2, b=1.4)
    put(art, lin([(255, 214, 90), GOLD, (255, 238, 170)], im, direction=(0, 1)), im)
    core = poly(M(), smooth_closed(pc))
    put(art, (255, 248, 215), blur(core, 1.2), 0.9)
    puck3d(art, 50, 71, 35, 12, 10)
    return art


# ───────────────────────────── типы прогнозов ─────────────────────────────

def e_stavka_dnya(k=1.0, shine=None, sparkles=()):
    """Золотая звезда в тёмном жетоне.
    Анимация: k — масштаб звезды; shine — блик 0…1 по звезде и ободку; sparkles — [(x, y, r, поворот°)] искорки."""
    art = new()
    inner = token(art, None, rim=GOLD, dark=True)
    sm = faceted_star(art, 50, 47.5, 31 * k, 13.5 * k, GOLD, inner)
    if shine is not None:
        sheen(art, union(sm, ring_mask(TK['cx'], TK['cy'], TK['r'], TK['r'] - 5.5)), shine)
    for x, y, r, a in sparkles:
        sparkle(art, x, y, r, a)
    return art


def e_express():
    """Три шайбы на золотой цепи (по диагонали вверх)."""
    art = new()
    centers = [(20, 74), (50, 50), (80, 26)]
    # звенья цепи между шайбами
    for (x0, y0), (x1, y1) in zip(centers, centers[1:]):
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        link = M()
        L, R = 15, 8
        pts = [(mx + L * math.cos(math.radians(ang)) * s + R * math.cos(math.radians(ang + 90)) * t,
                my + L * math.sin(math.radians(ang)) * s + R * math.sin(math.radians(ang + 90)) * t)
               for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        poly(link, pts)
        link = soften(link, 2.2)
        hole = soften(poly(M(), [(mx + (L - 6.5) * math.cos(math.radians(ang)) * s
                                  + (R - 4.2) * math.cos(math.radians(ang + 90)) * t,
                                  my + (L - 6.5) * math.sin(math.radians(ang)) * s
                                  + (R - 4.2) * math.sin(math.radians(ang + 90)) * t)
                                 for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))]), 1)
        lk = sub(link, hole)
        put(art, lin([mix(GOLD, 0.4), GOLD, mix(GOLD, -0.4)], lk), lk)
        bevel(art, lk, hi=0.5, lo=0.4, d=1.4, b=0.7)
    for cx, cy in centers:
        face = ell(M(), cx, cy, 15.5)
        side = ell(M(), cx, cy + 3.5, 15.5)
        put(art, (8, 8, 10), side)
        put(art, mix(GOLD, -0.4), mul(sub(side, shift(face, 0, -u(0.2))), ring_mask(cx, cy + 3.5, 15.5, 14)), 0.9)
        rm = ring_mask(cx, cy, 15.5, 11.8)
        inner = ell(M(), cx, cy, 11.8)
        put(art, lin([(66, 63, 72), (30, 28, 34), (14, 13, 16)], inner), inner)
        put(art, lin([mix(GOLD, 0.55), GOLD, mix(GOLD, -0.4)], rm), rm)
        bevel(art, rm, hi=0.5, lo=0.4, d=1.2, b=0.6)
        gloss(art, inner, (cx - 10, cy - 11, cx + 3, cy - 1), alpha=0.18, b=1.5)
    return art


def e_ordinar():
    art = new()
    inner = token(art, None, rim=GOLD, dark=True)
    g = text_mask('1', MONT, 49, 47, 40, 46)
    glyph(art, g, inner, color=GOLD, shade=mix(GOLD, -0.25), alpha=0.55)
    return art


def e_live(pulse=0.0, waves=((19, 1.0), (27.5, 1.0)), fx=None):
    """Красная точка с волнами эфира + плашка LIVE.
    Анимация: pulse 0…1 — точка «вздыхает» (растёт и светится); waves — [(радиус, непрозрачность)] дуг эфира;
    fx — список для finish(): гаснущие волны и свечение уходят туда отдельными слоями."""
    art = new()
    cx, cy = 50, 21
    # волны (( ● ))
    solid = M()
    for r, op in waves:
        w = solid if op >= 1 or fx is None else M()
        stroke(w, arc_pts(cx, cy, r, 150, 210, 16), 4.6)
        stroke(w, arc_pts(cx, cy, r, -30, 30, 16), 4.6)
        if w is not solid and op > 0:
            lay = new()
            put(lay, lin([mix(RED, 0.25), mix(RED, -0.1)], w), w)
            fx.append((lay, op, True))
    put(art, lin([mix(RED, 0.25), mix(RED, -0.1)], solid), solid)
    k = 1 + 0.14 * pulse
    halo = ell(M(), cx, cy, 13)
    put(art, RED, blur(halo, 3), 0.45)
    if pulse > 0 and fx is not None:                    # свечение вокруг точки (поверх, без контура)
        lay = new()
        put(lay, (255, 90, 70), sub(blur(ell(M(), cx, cy, 15), 4), ell(M(), cx, cy, 10.5 * k)))
        fx.append((lay, 0.55 * pulse, False))
    dot = ell(M(), cx, cy, 10.5 * k)
    put(art, rad([(255, 200, 190), mix(RED, 0.15), mix(RED, -0.2)], cx - 3.5 * k, cy - 4 * k, 14 * k), dot)
    bevel(art, dot, hi=0.5, lo=0.35, d=1.4, b=0.8)
    # плашка
    pm = plate(art, (4, 40, 96, 92), 12, RED)
    g = text_mask('LIVE', TEK, 50, 66.5, 82, 34)
    glyph(art, g, pm, color=WHITE, alpha=0.5)
    return art


def e_topkef():
    """Толстая золотая стрелка вверх с вырезанной «К»."""
    art = new()
    arrow = poly(M(), [(50, 4), (93, 46), (72, 46), (72, 94), (28, 94), (28, 46), (7, 46)])
    arrow = soften(arrow, 1.6)
    put(art, lin([mix(GOLD, 0.4), GOLD, mix(GOLD, -0.3)], arrow), arrow)
    rings(art, arrow, 30, 10, step=5.5, alpha=0.07)
    bevel(art, arrow, hi=0.6, lo=0.45, d=2.2, b=1.3)
    g = text_mask('К', MONT, 50, 66, 40, 37)
    # гравировка: знак тёмный, со светлой кромкой снизу
    put(art, (255, 240, 200), shift(g, u(0.4), u(1.3)), 0.75)
    put(art, lin([(44, 34, 20), (20, 16, 12)], g), g)
    return art


# ───────────────────────────── хоккей ─────────────────────────────

PUCK_STREAKS = (  # «следы скорости»: (y, начало относительно центра шайбы или None — из-за края силуэта, толщина, доля длины)
    (9.5, -6, 3.0, 0.75), (16.5, -19, 3.6, 1.0), (48, None, 4.4, 0.9), (69, None, 3.4, 0.6))


def e_puck(dx=0.0, kx=1.0, ky=1.0, streak=0.0):
    """Шайба в 3/4. Анимация: dx — сдвиг по горизонтали, ед.; kx, ky — сплющивание (низ на месте);
    streak — длина «следов скорости» за шайбой (слева), ед."""
    art = new()
    cx, cy, rx, ry, h = 50 + dx, 38, 44 * kx, 21 * ky, 22 * ky
    if ky != 1:
        cy = 81 - h - ry
    if streak > 1.5:
        sk = M()
        for y, hx, w, f in PUCK_STREAKS:
            if streak * f < 4:
                continue
            w *= min(1.0, streak * f / 14)              # короткий след — тоньше (не остаётся «точек»)
            if hx is None:                               # растёт из-за левого края силуэта
                yy = abs(y - cy) / ry if y < cy + h * 0.5 else max(0.0, y - cy - h) / ry
                xh = cx - rx * math.sqrt(1 - min(1.0, yy) ** 2) + 8
                xt = xh - 8 - streak * f
            else:                                        # летит над шайбой
                xh = cx + hx * kx
                xt = xh - streak * f
                ell(sk, xh, y, w / 2)
            poly(sk, [(xh, y - w / 2), (xt, y - w * 0.12), (xt, y + w * 0.12), (xh, y + w / 2)])
        sk = soften(sk, 0.4)
        put(art, lin([mix(ICE, 0.2), mix(ICE, 0.75), (255, 255, 255)], sk, direction=(1, 0)), sk)
        bevel(art, sk, hi=0.3, lo=0.3, d=0.8, b=0.5)
    puck3d(art, cx, cy, rx, ry, h, rim_w=3.4)
    return art


def _stick(art, top, heel, toe, shaft_col, flip=False):
    """Клюшка: древко от top к heel, крюк heel→toe с белой обмоткой."""
    sm = stroke(M(), [top, heel], 9.5)
    put(art, lin([mix(shaft_col, 0.35), shaft_col, mix(shaft_col, -0.35)], sm, direction=(1, 0.4) if not flip else (-1, 0.4)), sm)
    bevel(art, sm, hi=0.5, lo=0.4, d=1.6, b=0.8)
    # торец-набалдашник (обмотка)
    knob = stroke(M(), [top, (top[0] + (heel[0] - top[0]) * 0.1, top[1] + (heel[1] - top[1]) * 0.1)], 11)
    put(art, lin([(60, 58, 66), (16, 15, 19)], knob), knob)
    bevel(art, knob, hi=0.35, lo=0.3, d=1.2, b=0.6)
    # крюк
    hx, hy = heel
    tx, ty = toe
    blade = soften(union(stroke(M(), [(hx, hy - 1.5), (tx, ty)], 10.5),
                         ell(M(), tx, ty - 0.5, 6.5, 5.8)), 1)
    put(art, lin([(240, 244, 250), (176, 188, 202)], blade), blade)
    tape = M()
    for i in range(1, 5):
        k = i / 5
        x = hx + (tx - hx) * k
        y = hy + (ty - hy) * k - 1
        md(tape).line((u(x - 1.5), u(y - 6), u(x + 1.5), u(y + 6)), fill=255, width=int(u(1.6)))
    put(art, (120, 132, 148), mul(tape, blade), 0.8)
    bevel(art, blade, hi=0.45, lo=0.4, d=1.6, b=0.8)
    return union(sm, blade, knob)


def e_sticks():
    """Две скрещённые клюшки: золотая (КХЛ) и ледяная (НХЛ), шайба между крюками."""
    art = new()
    _stick(art, (84, 9), (31, 79), (10, 84), ICE, flip=True)
    _stick(art, (16, 9), (69, 79), (90, 84), GOLD)
    puck3d(art, 50, 82, 11, 4.6, 5, rim_w=1.6)
    return art


def e_goal():
    """Ворота анфас: красная рама, сетка, шайба внутри."""
    art = new()
    outer = rrect(M(), (8, 18, 92, 92), 12)
    md(outer).rectangle((u(8), u(60), u(92), u(92)), fill=255)
    inner = rrect(M(), (17.5, 27.5, 82.5, 98), 5)
    frame = sub(outer, inner)
    net_area = mul(outer, inner)
    # сетка: светлая дымка + ромбическая сетка, глубже к центру темнее
    put(art, rad([(70, 76, 88), (40, 44, 54)], 50, 62, 40), net_area, 0.9)
    mesh = M()
    d = md(mesh)
    for i in range(-14, 16):
        x = i * 6.2
        d.line((u(x), u(20), u(x + 80), u(100)), fill=255, width=int(u(1.7)))
        d.line((u(x + 80), u(20), u(x), u(100)), fill=255, width=int(u(1.7)))
    put(art, (240, 244, 250), mul(mesh, net_area), 0.85)
    # глубина: внутренняя тень от рамы
    put(art, (0, 0, 0), mul(blur(sub(net_area, shift(net_area, u(1), u(3))), 2.5), net_area), 0.6)
    # линия ворот
    gl = rrect(M(), (4, 88.5, 96, 93.5), 2.5)
    put(art, lin([mix(RED, 0.2), mix(RED, -0.2)], gl), gl)
    puck3d(art, 50, 71, 17, 6.8, 7.5, rim_w=2)
    put(art, lin([mix(RED, 0.35), RED, mix(RED, -0.3)], frame), frame)
    bevel(art, frame, hi=0.55, lo=0.45, d=1.8, b=1)
    return art


LAMP_RAYS = (-162, -126, -90, -54, -18)               # углы лучей мигалки, ° (−90 — вверх)
LAMP_C = (50, 54)                                     # центр лампы (откуда идут лучи)


def _angdiff(a, b):
    return (a - b + 180) % 360 - 180


def _lamp_ray(m, a):
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    x, y = LAMP_C
    return stroke(m, [(x + ca * 33, y + sa * 33), (x + ca * 44, y + sa * 44)], 6)


def e_goal_lamp(beam=None, flash=0.0, fx=None):
    """Красная мигалка гола: купол со светом, лучи, тёмное основание с золотой кромкой.
    Анимация: beam — направление вращающегося луча (или кортеж направлений), ° (−90 — вверх, по часовой);
    flash 0…1 — вспышка (купол и ореол ярче); fx — список для finish(): свет луча и ореола поверх рисунка."""
    art = new()
    cx = 50
    beams = () if beam is None else (beam,) if isinstance(beam, (int, float)) else tuple(beam)
    rays = M()
    for a in LAMP_RAYS:
        _lamp_ray(rays, a)
    halo = ell(M(), cx, 50, 30, 28)
    put(art, RED, blur(halo, 7), 0.55)
    put(art, lin([(255, 220, 200), mix(RED, 0.2)], rays, direction=(0, 1)), rays)
    if beams:                                           # луч проходит по лучам — они вспыхивают по очереди
        for a in LAMP_RAYS:
            lit = max(math.exp(-(_angdiff(a, b) / 24) ** 2) for b in beams)
            if lit > 0.02:
                put(art, (255, 246, 238), _lamp_ray(M(), a), 0.85 * lit)
    bevel(art, rays, hi=0.3, lo=0.25, d=1, b=0.6)
    dome = union(ell(M(), cx, 52, 25, 27), rrect(M(), (25, 52, 75, 76), 2))
    md(dome).rectangle((u(25), u(52), u(75), u(76)), fill=255)
    put(art, rad([(255, 236, 220), (255, 130, 110), RED, mix(RED, -0.35)], cx - 4, 48, 34), dome)
    for b in beams:                                     # отражатель внутри купола: светлая полоса бежит за лучом
        front = 0.5 - 0.5 * math.sin(math.radians(b))
        bx = cx + 19 * math.cos(math.radians(b))
        band = np.exp(-((_X - bx) / 7) ** 2) * np.clip((80 - _Y) / 12, 0, 1)
        bm = Image.fromarray((band * 255).astype(np.uint8), 'L')
        put(art, (255, 240, 228), mul(bm, dome), 0.6 * front ** 1.5)
    if flash > 0:
        put(art, (255, 228, 214), mul(blur(ell(M(), cx - 2, 50, 16, 18), 6), dome), 0.6 * flash)
    # полосы «линзы» (френель)
    fr = M()
    for y in (60, 67):
        md(fr).line((u(25), u(y), u(75), u(y)), fill=255, width=int(u(1.4)))
    put(art, mix(RED, -0.45), mul(fr, dome), 0.45)
    bevel(art, dome, hi=0.45, lo=0.45, d=2, b=1.2)
    hl = stroke(M(), arc_pts(cx, 52, 18, 196, 248, 16), 4)
    put(art, (255, 255, 255), hl, 0.85)
    base = rrect(M(), (16, 74, 84, 92), 4)
    put(art, lin([(70, 66, 76), (30, 28, 34), (12, 11, 14)], base), base)
    trim = rrect(M(), (16, 74, 84, 78.5), 2)
    put(art, lin([mix(GOLD, 0.4), GOLD, mix(GOLD, -0.3)], trim, direction=(1, 0.2)), trim)
    bevel(art, base, hi=0.35, lo=0.35, d=1.4, b=0.8)
    if fx is not None and (beams or flash > 0):
        lx, ly = LAMP_C
        r = np.hypot(_X - lx, _Y - ly)
        above = np.clip((76 - _Y) / 12, 0, 1)                 # за основанием света не видно
        not_dome = 1 - np.asarray(blur(dome, 1), np.float32) / 255
        paint = rad([(255, 236, 222), (255, 120, 92), (240, 70, 56)], lx, ly, 50)
        if beams:                                       # конусы вращающихся лучей
            ang = np.degrees(np.arctan2(_Y - ly, _X - lx))
            cone = 0
            for b in beams:
                d = (ang - b + 180) % 360 - 180
                cone = cone + np.exp(-(d / 14) ** 2) + 0.5 * np.exp(-(d / 5) ** 2)
            cone = cone * np.clip((r - 19) / 5, 0, 1) * np.clip(1 - (r - 22) / 27, 0, 1) ** 1.2
            lay = rad([(255, 248, 240), (255, 178, 150), (255, 96, 74)], lx, ly, 52).convert('RGBA')
            lay.putalpha(Image.fromarray((np.clip(cone * above * not_dome, 0, 1) * 225).astype(np.uint8), 'L'))
            fx.append((lay, 1.0, False))
        if flash > 0:                                   # ореол вспышки вокруг купола
            glow = np.clip(1 - (r - 22) / 22, 0, 1) ** 1.6 * np.clip((r - 18) / 6, 0, 1)
            lay = paint.convert('RGBA')
            lay.putalpha(Image.fromarray((np.clip(glow * above * not_dome, 0, 1) * 160).astype(np.uint8), 'L'))
            fx.append((lay, flash, False))
    return art


def e_mask():
    """Вратарская маска анфас: белая скорлупа с золотой полосой, тёмный вырез, решётка."""
    art = new()
    pts = []
    for i in range(73):
        t = i / 72 * 2 * math.pi
        x = math.sin(t)
        y = -math.cos(t)
        k = 1 - 0.28 * max(0.0, y) ** 1.4                  # сужение к подбородку
        pts.append((50 + 34 * x * k, 50 + 45 * y * (1 if y < 0 else 0.98)))
    shell = poly(M(), pts)
    put(art, lin([(255, 255, 255), (232, 238, 246), (172, 184, 200)], shell), shell)
    rings(art, shell, 30, 8, step=6, alpha=0.05, color=(120, 140, 170))
    # золотая полоса по центру лба и ледяные «крылья»
    stripe = mul(shell, poly(M(), [(44, 0), (56, 0), (54, 33), (46, 33)]))
    put(art, lin([mix(GOLD, 0.3), GOLD, mix(GOLD, -0.3)], stripe), stripe)
    wings = mul(shell, union(poly(M(), [(16, 30), (34, 22), (38, 33), (20, 46)]),
                             poly(M(), [(84, 30), (66, 22), (62, 33), (80, 46)])))
    put(art, ICE, wings, 0.75)
    bevel(art, shell, hi=0.5, lo=0.55, d=2.4, b=1.5)
    # вырез лица
    hole = soften(poly(M(), [(28, 38), (72, 38), (70, 66), (60, 84), (40, 84), (30, 66)]), 3.5)
    put(art, lin([(10, 10, 12), (36, 34, 40)], hole), hole)
    put(art, (0, 0, 0), mul(blur(sub(hole, shift(hole, u(0.8), u(2.4))), 1.6), hole), 0.7)
    # решётка
    cage = M()
    for x in (41.5, 58.5):
        stroke(cage, [(x, 37), (x, 85)], 4.4)
    for y in (49, 63):
        stroke(cage, [(26, y), (74, y)], 4.4)
    cage = mul(cage, soften(union(hole, shift(hole, 0, 0)), 0.1).filter(ImageFilter.MaxFilter(9)))
    cast(art, cage, hole, 0.6, d=2, b=1)
    put(art, lin([(255, 255, 255), STEEL, (130, 145, 165)], cage), cage)
    bevel(art, cage, hi=0.4, lo=0.3, d=0.9, b=0.5)
    return art


def e_ot():
    """Секундомер «ОТ» (овертайм): ледяной обод, тёмный циферблат, кнопки."""
    art = new()
    cx, cy, r = 50, 54, 39
    crown = union(rrect(M(), (41, 3, 59, 11), 3), rrect(M(), (46, 9, 54, 17), 1))
    side_btn = poly(M(), [(78, 17), (86, 25), (80, 31), (72, 23)])
    side_btn = soften(side_btn, 1)
    for m in (crown, side_btn):
        put(art, lin([mix(ICE, 0.5), ICE, mix(ICE, -0.4)], m), m)
        bevel(art, m, hi=0.5, lo=0.4, d=1.4, b=0.7)
    rm = ring_mask(cx, cy, r, r - 6.5)
    face = ell(M(), cx, cy, r - 6.5)
    put(art, lin([(64, 61, 70), (30, 28, 34), (14, 13, 16)], face), face)
    rings(art, face, cx - 18, cy - 22, step=6, alpha=0.05)
    # деления
    ticks = M()
    for k in range(12):
        a = math.radians(k * 30)
        r0, r1 = (r - 9.5, r - 13.5) if k % 3 else (r - 9, r - 15)
        stroke(ticks, [(cx + r0 * math.sin(a), cy - r0 * math.cos(a)), (cx + r1 * math.sin(a), cy - r1 * math.cos(a))],
               1.8 if k % 3 else 2.6)
    put(art, (150, 200, 235), ticks, 0.55)
    put(art, (0, 0, 0), mul(blur(sub(face, shift(face, u(0.6), u(1.8))), 1.2), face), 0.55)
    put(art, lin([mix(ICE, 0.55), ICE, mix(ICE, -0.4)], rm), rm)
    bevel(art, rm, hi=0.55, lo=0.45, d=1.6, b=0.8)
    g = text_mask('ОТ', MONT, cx, cy + 0.5, 50, 28)
    glyph(art, g, face, alpha=0.5)
    gloss(art, face, (cx - 30, cy - 34, cx + 14, cy - 8), alpha=0.1)
    return art


def e_so():
    """Буллиты: плашка с «Б» и шайба, летящая в угол."""
    art = new()
    pm = rrect(M(), (6, 5, 94, 93), 20)
    put(art, lin([(64, 61, 70), (30, 28, 34), (14, 13, 16)], pm), pm)
    rings(art, pm, 18, 12, step=6, alpha=0.06)
    rm = sub(pm, rrect(M(), (11.5, 10.5, 88.5, 87.5), 15))
    put(art, lin([mix(GOLD, 0.5), GOLD, mix(GOLD, -0.4)], rm), rm)
    bevel(art, rm, hi=0.5, lo=0.45, d=1.4, b=0.7)
    inner = rrect(M(), (11.5, 10.5, 88.5, 87.5), 15)
    put(art, (0, 0, 0), mul(blur(sub(inner, shift(inner, u(0.6), u(1.8))), 1.2), inner), 0.5)
    g = text_mask('Б', MONT, 41, 46, 44, 52)
    glyph(art, g, inner, alpha=0.5)
    # след шайбы
    trail = M()
    for i, (y, w) in enumerate(((73, 2.6), (79, 2.6))):
        stroke(trail, [(52 + i * 3, y), (66, y)], w)
    put(art, GOLD, trail, 0.85)
    puck3d(art, 76, 74, 11.5, 5, 5.5, rim_w=1.8)
    return art


def rot(m, a):
    """Повернуть маску вокруг центра холста (a > 0 — против часовой)."""
    return m.rotate(a, resample=Image.BICUBIC, center=(N / 2, N / 2))


def e_whistle(metal=None):
    """Свисток судьи (иконный силуэт): круглая камера с внутренним кольцом, мундштук с прорезью, петля."""
    art = new()
    metal = metal or [(255, 255, 255), (234, 240, 249), (190, 203, 220), (122, 139, 163)]
    A = -9                                             # лёгкий наклон: мундштук приподнят
    loop = rot(ring_mask(86, 34, 8.5, 4.6), A)
    put(art, lin([(250, 252, 255), STEEL, (100, 114, 132)], loop), loop)
    bevel(art, loop, hi=0.45, lo=0.4, d=1.1, b=0.5)
    cx, cy, r = 63, 57, 29
    barrel = ell(M(), cx, cy, r)
    mouth = soften(poly(M(), [(3, 30.5), (63, 28), (63, 52), (3, 49.5)]), 2.6)
    notch = soften(poly(M(), [(40, 22), (56, 22), (56, 38.5), (47, 38.5)]), 0.8)
    whole = union(barrel, mouth)
    body = rot(sub(whole, notch), A)
    put(art, lin(metal, body), body)
    # прорезь: тёмная глубина под «лезвием»
    slot = rot(mul(poly(M(), [(46.5, 34), (56, 34), (56, 42), (49, 42)]), whole), A)
    put(art, lin([(10, 10, 12), (50, 52, 60)], slot), slot)
    # торец камеры: внутреннее кольцо — узнаваемая деталь свистка
    face_ring = rot(ring_mask(cx, cy, 17, 13.2), A)
    put(art, (0, 0, 0), blur(shift(face_ring, u(0.5), u(1.2)), 0.6), 0.25)
    put(art, mix(metal[-1], -0.25), face_ring, 0.8)
    put(art, (255, 255, 255), rot(ring_mask(cx - 0.6, cy - 1.2, 13.4, 12.2), A), 0.6)
    rings(art, body, cx, cy, step=4.5, alpha=0.05, color=(90, 110, 140))
    # шов мундштука
    seam = rot(stroke(M(), [(22, 30), (22, 50)], 1.6, caps=False), A)
    put(art, mix(metal[-1], -0.2), mul(seam, body), 0.6)
    bevel(art, body, hi=0.7, lo=0.55, d=2.4, b=1.3)
    streak = rot(stroke(M(), [(8, 34.5), (37, 33)], 2.8), A)
    put(art, (255, 255, 255), blur(streak, 0.5), 0.95)
    gloss(art, body, (42, 32, 68, 52), alpha=0.35, b=3)
    return art


def e_ice():
    """Кубик льда (изометрия) с искрой."""
    art = new()
    cx = 46
    top = [(cx, 18), (cx + 34, 35), (cx, 52), (cx - 34, 35)]
    left = [(cx - 34, 35), (cx, 52), (cx, 92), (cx - 34, 75)]
    right = [(cx, 52), (cx + 34, 35), (cx + 34, 75), (cx, 92)]
    cube = soften(union(poly(M(), top), poly(M(), left), poly(M(), right)), 2.2)
    tm, lm, rm = (mul(poly(M(), p), cube) for p in (top, left, right))
    put(art, lin([(240, 250, 255), mix(ICE, 0.55)], tm), tm)
    put(art, lin([mix(ICE, 0.3), ICE, mix(ICE, -0.15)], lm), lm)
    put(art, lin([mix(ICE, -0.05), mix(ICE, -0.32)], rm), rm)
    # внутренние трещинки и «изморозь»
    cr = M()
    stroke(cr, [(cx - 24, 52), (cx - 14, 60), (cx - 18, 70)], 1.4)
    stroke(cr, [(cx + 12, 62), (cx + 22, 56), (cx + 26, 66)], 1.4)
    put(art, (255, 255, 255), mul(cr, cube), 0.55)
    # рёбра-блики
    edges = M()
    stroke(edges, [(cx - 34, 35), (cx, 52), (cx + 34, 35)], 2.4)
    stroke(edges, [(cx, 52), (cx, 92)], 2.4)
    put(art, (255, 255, 255), mul(blur(edges, 0.3), cube), 0.85)
    bevel(art, cube, hi=0.55, lo=0.4, d=1.8, b=1)
    # искра
    sp = M()
    sx, sy, r = 81, 19, 14
    poly(sp, sparkle_pts(sx, sy, r, 3.2))
    sx2, sy2, r2 = 18, 86, 8
    poly(sp, sparkle_pts(sx2, sy2, r2, 2))
    put(art, (255, 255, 255), blur(sp, 2.5), 0.6)
    put(art, (255, 255, 255), sp)
    return art


# ───────────────────────────── лиги / бренд ─────────────────────────────

def _tag(text, col):
    art = new()
    pm = plate(art, (4, 21, 96, 79), 13, col)
    g = text_mask(text, TEK, 50, 50.5, 84, 38, squeeze=0.86)
    put(art, mix(col, 0.6), shift(g, u(0.3), u(1.2)), 0.7)        # светлая кромка гравировки
    put(art, lin([(40, 30, 22) if col == GOLD else (14, 30, 48), (12, 11, 14)], g), g)
    return art


def e_khl_tag():
    return _tag('КХЛ', GOLD)


def e_nhl_tag():
    return _tag('НХЛ', ICE)


def e_jarvis():
    """Монограмма «J» в тёмном щите с золотой кромкой."""
    art = new()

    def shield(k):
        cx = 50
        w, top, mid, bot = 36 * k, 49 - 42 * k, 49 + 4 * k, 49 + 44 * k
        pts = [(cx - w, top + 6 * k), (cx - w * 0.5, top), (cx, top + 4 * k), (cx + w * 0.5, top), (cx + w, top + 6 * k),
               (cx + w, mid)]
        pts += [(cx + w * math.cos(t * math.pi / 2) ** 0.9, mid + (bot - mid) * math.sin(t * math.pi / 2) ** 1.4)
                for t in [i / 16 for i in range(1, 17)]]
        pts += [(cx - w * math.cos(t * math.pi / 2) ** 0.9, mid + (bot - mid) * math.sin(t * math.pi / 2) ** 1.4)
                for t in [i / 16 for i in range(16, 0, -1)]]
        pts += [(cx - w, mid)]
        return soften(poly(M(), pts), 1.2)

    outer = shield(1.0)
    inner = shield(0.84)
    rim = sub(outer, inner)
    put(art, lin([(64, 61, 70), (30, 28, 34), (12, 11, 14)], inner), inner)
    rings(art, inner, 70, 82, step=6, alpha=0.06, color=GOLD)
    put(art, lin([mix(GOLD, 0.55), GOLD, mix(GOLD, -0.45)], rim), rim)
    bevel(art, rim, hi=0.55, lo=0.45, d=1.6, b=0.8)
    put(art, (0, 0, 0), mul(blur(sub(inner, shift(inner, u(0.6), u(1.8))), 1.2), inner), 0.5)
    g = text_mask('J', MONT, 49, 47, 36, 50)
    glyph(art, g, inner, color=GOLD, shade=mix(GOLD, -0.25), alpha=0.55)
    return art


def e_kef():
    """Золотая монета-шайба с выбитой «К»."""
    art = new()
    face = token(art, GOLD)
    put(art, mix(GOLD, -0.35), ring_mask(50, 46, 33, 31), 0.6)
    g = text_mask('К', MONT, 50, 46.5, 38, 36)
    put(art, (255, 238, 190), shift(g, u(0.4), u(1.4)), 0.8)
    put(art, lin([(70, 46, 10), (34, 24, 10)], g), g)
    return art


# ───────────────────────────── сервис ─────────────────────────────

def e_clock_msk():
    """Часы 19:00 (стрелки на 7) с плашкой «МСК»."""
    art = new()
    cx, cy, r = 50, 34, 30
    body = ell(M(), cx, cy, r)
    face = ell(M(), cx, cy, r - 5)
    rm = sub(body, face)
    put(art, lin([(255, 255, 255), (230, 238, 246), (180, 192, 208)], face), face)
    ticks = M()
    for k in range(12):
        a = math.radians(k * 30)
        r0, r1 = (r - 8, r - 10.5) if k % 3 else (r - 7.5, r - 12)
        stroke(ticks, [(cx + r0 * math.sin(a), cy - r0 * math.cos(a)), (cx + r1 * math.sin(a), cy - r1 * math.cos(a))],
               1.6 if k % 3 else 2.4)
    put(art, (60, 64, 76), ticks, 0.8)
    hands = M()
    a7 = math.radians(210)
    stroke(hands, [(cx, cy), (cx + 14 * math.sin(a7), cy - 14 * math.cos(a7))], 4.6)
    stroke(hands, [(cx, cy), (cx, cy - 20)], 3.6)
    cast(art, hands, face, 0.3, d=1.4, b=0.8)
    put(art, (20, 19, 24), hands)
    put(art, (0, 0, 0), mul(blur(sub(face, shift(face, u(0.6), u(1.8))), 1.2), face), 0.4)
    put(art, lin([mix(GOLD, 0.55), GOLD, mix(GOLD, -0.4)], rm), rm)
    bevel(art, rm, hi=0.5, lo=0.4, d=1.4, b=0.7)
    pin = ell(M(), cx, cy, 3.4)
    put(art, GOLD, pin)
    # плашка МСК
    pm = rrect(M(), (5, 57, 95, 94), 11)
    put(art, lin([(70, 66, 78), (34, 32, 38), (14, 13, 16)], pm), pm)
    rings(art, pm, 10, 50, step=5, alpha=0.05)
    bevel(art, pm, hi=0.4, lo=0.35, d=1.6, b=0.8)
    g = text_mask('МСК', TEK, 50, 76.5, 84, 28, squeeze=0.9)
    glyph(art, g, pm, color=WHITE, alpha=0.5)
    return art


def e_calendar_today():
    """Листок календаря «СЕГОДНЯ» с шайбой."""
    art = new()
    page = rrect(M(), (10, 13, 90, 93), 11)
    put(art, lin([(255, 255, 255), (234, 240, 248), (190, 200, 214)], page), page)
    head = mul(page, rrect(M(), (10, 13, 90, 39), 0))
    put(art, lin([mix(GOLD, 0.35), GOLD, mix(GOLD, -0.25)], head), head)
    rings(art, head, 14, 6, step=5, alpha=0.07)
    g = text_mask('СЕГОДНЯ', TEK, 50, 28, 62, 9.5)
    put(art, (40, 30, 18), g)
    put(art, (0, 0, 0), mul(blur(shift(rrect(M(), (0, 37, 100, 40), 0), 0, u(1)), 1), page), 0.25)
    bevel(art, page, hi=0.5, lo=0.45, d=2, b=1.2)
    for x in (31, 69):
        hole = ell(M(), x, 18.5, 3.6)
        put(art, (40, 32, 20), hole, 0.8)
        hook = rrect(M(), (x - 3, 5, x + 3, 21), 3)
        put(art, lin([(90, 88, 98), (40, 38, 46), (14, 13, 16)], hook, direction=(1, 0)), hook)
        bevel(art, hook, hi=0.4, lo=0.3, d=1, b=0.5)
    puck3d(art, 50, 61, 25, 10, 10, rim_w=2.2)
    return art


def e_stats():
    """Мини-гистограмма: столбики лёд / золото по очереди, растут вправо."""
    art = new()
    base_y = 86
    bars = ((7, 26, 34, ICE), (29, 48, 54, GOLD), (51, 70, 42, ICE), (73, 92, 76, GOLD))
    for x0, x1, h, col in bars:
        m = rrect(M(), (x0, base_y - h, x1, base_y + 2), 4.5)
        put(art, lin([mix(col, 0.4), col, mix(col, -0.3)], m), m)
        rings(art, m, x0, base_y - h, step=5, alpha=0.06)
        bevel(art, m, hi=0.55, lo=0.45, d=1.8, b=1)
    axis = rrect(M(), (3, base_y, 97, base_y + 6.5), 3.2)
    put(art, lin([(250, 252, 255), (180, 190, 206)], axis), axis)
    bevel(art, axis, hi=0.3, lo=0.35, d=1.2, b=0.6)
    return art


def e_news():
    """Молния в круге."""
    art = new()
    inner = token(art, None, rim=GOLD, dark=True)
    bolt = poly(M(), [(58, 12), (27, 53), (46, 53), (38, 82), (72, 38), (53, 38), (63, 12)])
    bolt = soften(bolt, 0.8)
    bolt = mul(bolt, inner)
    glyph(art, bolt, inner, color=GOLD, shade=mix(GOLD, -0.3), alpha=0.6)
    return art


def e_vs():
    """«VS» в стиле Versus: две смещённые панели клубов с кольцами, белые буквы."""
    art = new()
    A = rrect(M(), (6, 6, 61, 67), 8)
    B = rrect(M(), (38, 29, 93, 90), 8)
    for m, col, c in ((A, (214, 52, 58), (26, 14)), (B, (36, 98, 196), (72, 84))):
        cast(art, m, None, 0.55, d=2.5, b=2)
        put(art, lin([mix(col, 0.2), col, mix(col, -0.35)], m), m)
        rings(art, m, c[0], c[1], step=5, alpha=0.12)
        bevel(art, m, hi=0.4, lo=0.4, d=1.6, b=0.9)
    g = text_mask('VS', MONT_I, 50, 50, 70, 44)
    cast(art, g, None, 0.7, d=2.6, b=1.6)
    edge = blur(g, 1.2).point(lambda v: 0 if v < 10 else min(255, v * 3))
    put(art, KEY, edge, 0.9)
    put(art, lin([(255, 255, 255), (236, 238, 244), (200, 206, 216)], g), g)
    bevel(art, g, hi=0.3, lo=0.25, d=1.2, b=0.7)
    return art


# ───────────────────────────── реестр ─────────────────────────────

EMOJI = {
    # итоги
    'zahod': (e_zahod, '✅'),
    'minus': (e_minus, '❌'),
    'vozvrat': (e_vozvrat, '↩️'),
    'zhdem': (e_zhdem, '⏳'),
    'seriya': (e_seriya, '🔥'),
    # типы прогнозов
    'stavka_dnya': (e_stavka_dnya, '⭐'),
    'express': (e_express, '🔗'),
    'ordinar': (e_ordinar, '1️⃣'),
    'live': (e_live, '🔴'),
    'topkef': (e_topkef, '📈'),
    # хоккей
    'puck': (e_puck, '⚫'),
    'sticks': (e_sticks, '🏒'),
    'goal': (e_goal, '🥅'),
    'goal_lamp': (e_goal_lamp, '🚨'),
    'mask': (e_mask, '🥶'),
    'ot': (e_ot, '⏱'),
    'so': (e_so, '🎯'),
    'whistle': (e_whistle, '📣'),
    'ice': (e_ice, '🧊'),
    # лиги / бренд
    'khl_tag': (e_khl_tag, '🇷🇺'),
    'nhl_tag': (e_nhl_tag, '🌐'),
    'jarvis': (e_jarvis, '🤖'),
    'kef': (e_kef, '💰'),
    # сервис
    'clock_msk': (e_clock_msk, '🕖'),
    'calendar_today': (e_calendar_today, '📅'),
    'stats': (e_stats, '📊'),
    'news': (e_news, '⚡'),
    'vs': (e_vs, '🆚'),
}


def render(key):
    """→ PIL RGBA 100×100."""
    return finish(EMOJI[key][0]())


def render_all(out_dir, keys=None):
    os.makedirs(out_dir, exist_ok=True)
    res = {}
    for k in keys or EMOJI:
        im = render(k)
        assert im.size == (SIZE, SIZE) and im.mode == 'RGBA'
        p = os.path.join(out_dir, k + '.png')
        im.save(p, optimize=True)
        res[k] = im
    return res


# ───────────────────────────── превью ─────────────────────────────

TG_DARK = (24, 26, 32)
NOTO = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'


def std_emoji(ch, size=18):
    """Стандартный эмодзи (запасной) картинкой — через Noto Color Emoji, если шрифт есть."""
    try:
        f = ImageFont.truetype(NOTO, 109)
    except OSError:
        return None
    im = Image.new('RGBA', (200, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((100, 80), ch, font=f, embedded_color=True, anchor='mm')
    im = im.crop(im.getbbox())
    k = size / max(im.size)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def sheet(ims, path, cols=7):
    keys = list(ims)
    cw, ch, pad = 132, 150, 24
    rows = (len(keys) + cols - 1) // cols
    W = cols * cw + pad * 2
    strip_h = 120
    H = rows * ch + pad * 2 + 30 + strip_h
    img = Image.new('RGB', (W, H), TG_DARK)
    d = ImageDraw.Draw(img)
    ft = font('Onest[wght].ttf', 20, 700)
    fl = font('JetBrainsMono[wght].ttf', 12, 500)
    fs = font('Onest[wght].ttf', 13, 500)
    d.text((pad, pad - 6), '@jarvibet · custom emoji · 100×100', font=ft, fill=(235, 236, 240))
    d.text((W - pad, pad - 2), 'под ключом — запасной стандартный эмодзи', font=fs, fill=(120, 124, 136), anchor='ra')
    for i, k in enumerate(keys):
        x = pad + (i % cols) * cw + (cw - 100) // 2
        y = pad + 30 + (i // cols) * ch
        img.paste(ims[k], (x, y), ims[k])
        d.text((x + 50, y + 108), k, font=fl, fill=(170, 174, 186), anchor='mt')
        fb = std_emoji(EMOJI[k][1])
        if fb is not None:
            img.paste(fb, (x + 50 - fb.width // 2, y + 126), fb)
        else:
            d.text((x + 50, y + 126), EMOJI[k][1], font=fs, fill=(110, 114, 126), anchor='mt')
    # полосы 22 px: тёмная и светлая тема
    y0 = H - strip_h
    d.text((pad, y0 + 4), 'at 22 px', font=fs, fill=(140, 144, 156))
    img.paste((255, 255, 255), (0, y0 + 64, W, H))
    for row, (yy, _) in enumerate(((y0 + 28, TG_DARK), (y0 + 80, (255, 255, 255)))):
        for i, k in enumerate(keys):
            sm = ims[k].resize((22, 22), Image.LANCZOS)
            img.paste(sm, (pad + i * 30, yy), sm)
    img.save(path)
    return path


INLINE = [
    '{zahod} Зашёл! Торпедо — Динамо 3:1 {vs}',
    '{stavka_dnya} Ставка дня · КХЛ {khl_tag} {clock_msk} 19:00',
    '{live} {goal_lamp} ГОООЛ!',
    '{minus} Не зашёл · {vozvrat} Возврат',
    '{nhl_tag} Ночь НХЛ {puck} {stats} 3 из 4',
    '{seriya} Серия 5 заходов {zahod}{zahod}{zahod} · {zhdem} ждём',
    '{express} Экспресс дня {topkef} кэф 4.85 · {ordinar} ординар {kef} 1.95',
    '{sticks} Сегодня {calendar_today} {goal} гол {mask} сухарь вратаря',
    '{ot} Овертайм · {so} буллиты · {whistle} удаление {ice}',
    '{jarvis} JARVIS · {news} Новости дня',
]


def _line(img, d, x, y, tpl, ims, f, color, es=22):
    parts = []
    i = 0
    while i < len(tpl):
        j = tpl.find('{', i)
        if j < 0:
            parts.append(('t', tpl[i:]))
            break
        if j > i:
            parts.append(('t', tpl[i:j]))
        k = tpl.index('}', j)
        parts.append(('e', tpl[j + 1:k]))
        i = k + 1
    asc, _ = f.getmetrics()
    base = y + asc
    for kind, v in parts:
        if kind == 't':
            d.text((x, base), v, font=f, fill=color, anchor='ls')
            x += d.textlength(v, font=f)
        else:
            sm = ims[v].resize((es, es), Image.LANCZOS)
            # центр эмодзи — на середине строчных (как в Telegram)
            img.paste(sm, (int(round(x)) + 1, int(round(base - f.size * 0.36 - es / 2))), sm)
            x += es + 3


def inline(ims, path):
    W, lh, pad = 600, 34, 22
    H1 = pad * 2 + lh * len(INLINE) + 10
    img = Image.new('RGB', (W, H1 * 2), TG_DARK)
    d = ImageDraw.Draw(img)
    f = font('Onest[wght].ttf', 16, 500)
    fs = font('Onest[wght].ttf', 11, 500)
    for p, (bg, bub, fg) in enumerate(((TG_DARK, (43, 47, 56), (236, 238, 242)),
                                        ((222, 230, 238), (255, 255, 255), (18, 20, 24)))):
        y0 = p * H1
        img.paste(bg, (0, y0, W, y0 + H1))
        d.rounded_rectangle((12, y0 + 12, W - 12, y0 + H1 - 12), 14, fill=bub)
        d.text((W - 26, y0 + H1 - 20), 'dark theme' if p == 0 else 'light theme', font=fs,
               fill=(120, 124, 136), anchor='rs')
        for i, tpl in enumerate(INLINE):
            _line(img, d, pad + 10, y0 + pad + 4 + i * lh, tpl, ims, f, fg)
    img.save(path)
    return path


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0] if args else DEFAULT_OUT
    keys = args[1:] or None
    ims = render_all(out, keys)
    for k in ims:
        print(os.path.join(out, k + '.png'))
    if '--preview' in sys.argv or not keys:
        if keys:
            ims = {k: Image.open(os.path.join(out, k + '.png')).convert('RGBA') for k in EMOJI}
        print(sheet(ims, os.path.join(out, 'sheet.png')))
        print(inline(ims, os.path.join(out, 'inline.png')))
