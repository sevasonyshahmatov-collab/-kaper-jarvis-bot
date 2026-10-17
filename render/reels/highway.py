# -*- coding: utf-8 -*-
"""«Трасса» — ночное шоссе из кабины грузовика (трек «TRUCK»): дорога уходит к горизонту, пунктир разметки
летит навстречу, натриевые фонари проплывают по краям (по одному на долю трека), вдали — зарево города.
Факты приходят большими зелёными дорожными знаками (белый узкий шрифт, светоотражающая кайма): знак вырастает
из точки схода и встаёт на место на долю трека, в конце сцены вся группа знаков пролетает над камерой.

Сцены (u — доля трека, D — дроп; доли считаются от дропа, team / run / hold / cta — параметры из reels_cfg/highway.json):
  интро (до D − (2·team + run) долей) — портал над дорогой: обе эмблемы, названия, «хозяева / гости», время МСК,
                 на табличке-«съезде» сверху — JARVIS | NHL; на 1-ю долю вырастают три полосных знака со стрелками вниз —
                 линия основного времени П1 · Х · П2 крупно (каждый исход — своя полоса);
  команда (team долей) ×2 — небо и зарево в цвете клуба; на долю 0 подлетает большой указатель: эмблема в белом
                 круге, название клуба, на табличке сверху «ХОЗЯЕВА» / «ГОСТИ»; на доли 1, 1½, 2 на нём загораются
                 строки последних 3 игр (В/П, соперник, счёт, ОТ/Б) — как пункты и расстояния; на доли 3, 3½, 4
                 у обочины встают знаки: «ограничение скорости» — очки за N матчей, щит трассы — место
                 (на табличке — конференция), ромб — разница шайб (на табличке — забито и пропущено);
                 за долю до конца сцены вся группа знаков пролетает над кабиной (наезд-смаз);
  разгон (run долей) — скорость растёт, фонари тянутся в полосы, издалека надвигается тёмный портал;
  ДРОП (hold долей) — ровно на дропе (удар трека) грузовик проходит под порталом: вспышка, прожекторы портала
                 загораются, камера встаёт; через bass с (вход баса «TRUCK», 0,42 с) — второй удар прожекторов и камеры; на знаке — только команда прогноза (одна эмблема, без «VS»), «ПОБЕДА …»,
                 «В ОСНОВНОЕ ВРЕМЯ» и жёлтая полоса снизу с кэфом; на каждую долю — пульс прожекторов;
  финал (cta долей) — портал уходит вверх и уменьшается, снизу — плашка Telegram (C.tg_plate, текст по центру).
@jarvibet — зелёная табличка у низа безопасной зоны (y 1447), одинаково во всех сценах до плашки Telegram.
Пустые (None) поля статистики не показываются; никаких шансов и процентов победы.
Кадр зависит только от t (путь грузовика — заранее посчитанный интеграл скорости); знаки, фон и свечения кешируются.
"""
import math
import re

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels.core import W, H

VX, VY = 540, 1000                 # точка схода
FPX = 700.0                        # фокус: экранная «глубина» d = FPX / z, y земли = VY + d
GREEN = (0, 118, 72)
GREEN_D = (0, 84, 52)
WHITE = (246, 248, 244)
YEL = (255, 204, 18)
BLACK = (18, 18, 18)
SODIUM = (255, 150, 58)
WIN = (34, 190, 96)
LOSS = (226, 54, 50)
STEEL = (62, 68, 78)
FN = 'robc'                        # узкий гротеск в духе дорожного шрифта

DASH_P, DASH_L, POLE_P = 4.8, 1.5, 9.6
HANDLE_Y = 1447
BEAM_Y = 286
ZMIN = FPX / (H - VY + 20)

_CACHE = {}
_SPR = {}


# ─────────────────────────────── мелочи ───────────────────────────────
def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _fnum(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(str(v).replace(',', '.').replace('%', '').replace('−', '-').strip())
    except ValueError:
        return None


def _vivid(c, lo=70, hi=230):
    """Цвет клуба для зарева: не слишком тёмный."""
    m = max(c)
    if m < lo:
        k = lo / max(1, m)
        c = tuple(min(255, int(x * k)) for x in c)
    return c


def persp(s, x, y):
    """Точка группы знаков (координаты при s = 1) при масштабе s относительно точки схода."""
    return VX + (x - VX) * s, VY + (y - VY) * s


def put_persp(fr, im, cx, cy, s, a=1.0):
    """Наложить im (центр (cx, cy) при s = 1) в перспективе: масштаб s от точки схода; крупное — только видимый кусок."""
    if im is None or a <= 0.003 or s <= 0.004:
        return
    if abs(s - 1) < 0.002:
        C.put(fr, im, cx, cy, a)
        return
    px, py = persp(s, cx, cy)
    w, h = im.width * s, im.height * s
    x0, y0 = px - w / 2, py - h / 2
    dx0, dy0, dx1, dy1 = max(0.0, x0), max(0.0, y0), min(float(W), x0 + w), min(float(H), y0 + h)
    dw, dh = int(round(dx1 - dx0)), int(round(dy1 - dy0))
    if dw < 1 or dh < 1:
        return
    box = ((dx0 - x0) / s, (dy0 - y0) / s, (dx1 - x0) / s, (dy1 - y0) / s)
    piece = im.resize((dw, dh), Image.BILINEAR, box=box)
    if a < 0.997:
        piece = C.fade(piece, a)
    fr.alpha_composite(piece, (int(round(dx0)), int(round(dy0))))


def _approach(q, far=12.0):
    """Масштаб знака на подлёте (q 0→1): из точки схода, мягкая посадка."""
    return 1.0 / (1.0 + far * (1 - C.out_cubic(q)))


def _flyby(q):
    """Масштаб при пролёте над камерой (q 0→1): растёт всё быстрее."""
    return 1.0 / max(0.06, 1 - 0.93 * C.in_cubic(q) ** 0.8)


# ─────────────────────────────── знаки ───────────────────────────────
def panel(w, h, r=24, col=GREEN, border=WHITE, inset=11, bw=6, sheen=True):
    """Щит знака: светоотражающая плёнка (лёгкий градиент и зерно), белая кайма внутри, тёмная кромка."""
    w, h = int(w), int(h)
    g = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    top = np.array(C.mix(col, (255, 255, 255), 0.10), np.float32)
    bot = np.array(C.mix(col, (0, 0, 0), 0.16), np.float32)
    arr = np.repeat(top * (1 - g) + bot * g, w, 1)
    if sheen:
        rnd = np.random.default_rng(w * 7 + h)
        arr = arr * (1 + rnd.normal(0, 0.018, (h, w, 1)).astype(np.float32))
        xx = np.arange(w, dtype=np.float32)[None, :, None]
        arr = arr * (1 + 0.05 * np.exp(-((xx / w - 0.3) / 0.35) ** 2))
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    im.putalpha(C.rrect(w, h, r, (255, 255, 255)).getchannel('A'))
    rim = C.rrect(w, h, r, None, outline=C.mix(col, (0, 0, 0), 0.5), width=3)
    im.alpha_composite(rim)
    if border:
        bd = C.rrect(w - 2 * inset, h - 2 * inset, max(4, r - inset * 0.7), None, outline=border, width=bw)
        im.alpha_composite(bd, (inset, inset))
    return im


def tab(txt, h=74, col=GREEN, size=44, pad=34, fg=WHITE):
    """Табличка «съезда» над знаком: зелёная, белая кайма, текст по центру."""
    t = C.text(txt, FN, size, fg, 700, track=0.06)
    w = t.width + 2 * pad
    im = panel(w, h, 16, col, WHITE, 8, 5)
    C.put(im, t, w / 2, h / 2 + 1)
    return im


def circle_badge(team, d, ring=None):
    """Белый круглый «маркер трассы» с эмблемой клуба."""
    S = 3
    im = Image.new('RGBA', (d * S, d * S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse((0, 0, d * S - 1, d * S - 1), fill=(250, 250, 248, 255))
    if ring:
        k = int(d * S * 0.045)
        dr.ellipse((k, k, d * S - 1 - k, d * S - 1 - k), outline=tuple(ring) + (255,), width=int(d * S * 0.035))
    im = im.resize((d, d), Image.LANCZOS)
    e = team.emb(int(d * 0.66))
    C.put(im, e, d / 2, d / 2)
    return im


def chip(r, d=86):
    im = C.rrect(d, d, d * 0.2, F.res_col(r) if r else (150, 150, 160))
    col = WIN if r == 'В' else LOSS if r == 'П' else (150, 150, 160)
    im = C.rrect(d, d, d * 0.2, col, outline=WHITE, width=4)
    C.put(im, C.text(r or '?', FN, d * 0.62, WHITE, 800), d / 2, d / 2 + 1)
    return im


def note_tag(s, h=56):
    t = C.text(s, FN, h * 0.66, GREEN, 800)
    w = max(h, t.width + 22)
    im = C.rrect(w, h, 10, WHITE)
    C.put(im, t, w / 2, h / 2 + 1)
    return im


def arrow_down(w, h, col=WHITE):
    """Стрелка полосы вниз (как на знаках над полосами)."""
    sw = w * 0.3
    hh = h * 0.48
    pts = [(w / 2 - sw / 2, 0), (w / 2 + sw / 2, 0), (w / 2 + sw / 2, h - hh), (w, h - hh), (w / 2, h), (0, h - hh),
           (w / 2 - sw / 2, h - hh)]
    return C.polygon(pts, (w, h), col)


def speed_sign(top, num, sub, w=290, h=356):
    """Белый знак в духе «ограничения скорости»: подпись, крупное число, мелкая строка."""
    im = panel(w, h, 20, (238, 238, 232), BLACK, 12, 6, sheen=True)
    C.put(im, C.text(top, FN, 56, BLACK, 700, track=0.04, max_w=w - 60), w / 2, 74)
    C.put(im, C.text(num, FN, 168, BLACK, 800, max_w=w - 50), w / 2, h * 0.52 + 6)
    if sub:
        C.put(im, C.text(sub, FN, 38, BLACK, 600, max_w=w - 56), w / 2, h - 58)
    return im


def _shield_mask(w, h, S=3):
    """Щит трассы: верх со «скулами», низ сходится плавной дугой."""
    W2, H2 = w * S, h * S
    xs = np.linspace(0, 1, 160)
    topy = 0.07 - 0.07 * np.sin(np.pi * xs) ** 0.5 + 0.035 * np.sin(np.pi * xs) ** 6
    boty = 0.46 + 0.54 * (1 - np.abs(2 * xs - 1) ** 1.9) ** 0.62
    pts = [(x * W2, y * H2) for x, y in zip(xs, topy)] + [(x * W2, y * H2) for x, y in zip(xs[::-1], boty[::-1])]
    m = Image.new('L', (W2, H2), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def shield_sign(top, num, w=272, h=300):
    m = _shield_mask(w, h)
    im = Image.new('RGBA', (w, h), (20, 20, 22, 255))
    im.putalpha(m)
    wm = m.filter(ImageFilter.MinFilter(5))
    lay = Image.new('RGBA', (w, h), WHITE + (255,))
    lay.putalpha(wm)
    im.alpha_composite(lay)
    im2 = m.filter(ImageFilter.MinFilter(15))
    body = np.zeros((h, w, 4), np.uint8)
    yy = np.arange(h)[:, None]
    body[..., 0] = np.where(yy < h * 0.30, 196, 0)
    body[..., 1] = np.where(yy < h * 0.30, 30, 62)
    body[..., 2] = np.where(yy < h * 0.30, 44, 150)
    body[..., 3] = 255
    bim = Image.fromarray(body, 'RGBA')
    bim.putalpha(im2)
    im.alpha_composite(bim)
    ImageDraw.Draw(im).line((14, int(h * 0.30) + 2, w - 14, int(h * 0.30) + 2), fill=WHITE + (255,), width=5)
    C.put(im, C.text(top, FN, 46, WHITE, 700, track=0.08, max_w=w - 80), w / 2, h * 0.165)
    C.put(im, C.text(num, FN, 150, WHITE, 800, max_w=w - 70), w / 2, h * 0.57)
    return im


def diamond_sign(num, w=290):
    S = 3
    D = w * S
    m = Image.new('L', (D, D), 0)
    dr = ImageDraw.Draw(m)
    dr.polygon([(D / 2, 0), (D, D / 2), (D / 2, D), (0, D / 2)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(S * 5)).point(lambda v: 255 if v > 128 else 0)    # скруглённые углы
    m = m.resize((w, w), Image.LANCZOS)
    im = Image.new('RGBA', (w, w), YEL + (255,))
    im.putalpha(m)
    inner = m.filter(ImageFilter.MinFilter(17))
    ring = ImageChops.subtract(inner, inner.filter(ImageFilter.MinFilter(11)))
    blk = Image.new('RGBA', (w, w), BLACK + (255,))
    blk.putalpha(ring)
    im.alpha_composite(blk)
    edge = ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(3)))
    e2 = Image.new('RGBA', (w, w), (120, 90, 0, 255))
    e2.putalpha(edge)
    im.alpha_composite(e2)
    C.put(im, C.text(num, FN, 132, BLACK, 800, max_w=w * 0.56), w / 2, w / 2 + 2)
    return im


def plaque(txt, w, h=62, col=GREEN, fg=WHITE, border=WHITE, size=36):
    im = panel(w, h, 12, col, border, 7, 4)
    C.put(im, C.text(txt, FN, size, fg, 700, track=0.04, max_w=w - 36), w / 2, h / 2 + 1)
    return im


def on_post(sign, plq=None, gap=8, post_to=None):
    """Знак (и табличка) на стойке: стойка уходит вниз до земли; центр — центр щита знака."""
    sh = (sign.height + (plq.height + gap if plq is not None else 0))
    post_h = (post_to or 0)
    w = max(sign.width, plq.width if plq is not None else 0)
    hh = sh + post_h
    im = Image.new('RGBA', (w, hh), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    if post_h:
        dr.rectangle((w / 2 - 9, sign.height // 2, w / 2 + 9, hh), fill=(92, 98, 108, 255))
        dr.rectangle((w / 2 - 9, sign.height // 2, w / 2 - 4, hh), fill=(140, 146, 156, 255))
    im.alpha_composite(sign, ((w - sign.width) // 2, 0))
    if plq is not None:
        im.alpha_composite(plq, ((w - plq.width) // 2, sign.height + gap))
    return im


def with_sh(im, r=16, a=0.6, dy=10):
    return C.with_shadow(im, r, a, dy)


# ─────────────────────────────── свечения ───────────────────────────────
def _q(v):
    """Квантование размера спрайта (≈ 8 шагов на октаву)."""
    v = max(2.0, float(v))
    return max(2, int(round(2 ** (round(math.log2(v) * 8) / 8))))


def _blob(rx, ry, power=2.0):
    key = (rx, ry, power)
    if key not in _SPR:
        y, x = np.mgrid[0:2 * ry, 0:2 * rx].astype(np.float32)
        d = np.sqrt(((x + 0.5 - rx) / rx) ** 2 + ((y + 0.5 - ry) / ry) ** 2)
        _SPR[key] = (np.clip(1 - d, 0, 1) ** power).astype(np.float32)
    return _SPR[key]


def add_blob(acc, cx, cy, rx, ry, col, k=1.0, power=2.0):
    """Сложить пятно света в полуразмерный буфер acc (координаты — полного кадра)."""
    rx, ry = _q(rx * 0.5), _q(ry * 0.5)
    cx, cy = cx * 0.5, cy * 0.5
    h, w = acc.shape[:2]
    x0, y0 = int(round(cx - rx)), int(round(cy - ry))
    x1, y1 = x0 + 2 * rx, y0 + 2 * ry
    if x1 <= 0 or y1 <= 0 or x0 >= w or y0 >= h:
        return
    sp = _blob(rx, ry, power)
    sx0, sy0 = max(0, -x0), max(0, -y0)
    sx1, sy1 = 2 * rx - max(0, x1 - w), 2 * ry - max(0, y1 - h)
    acc[max(0, y0):min(h, y1), max(0, x0):min(w, x1)] += sp[sy0:sy1, sx0:sx1, None] * (np.array(col, np.float32) * k)


def radial_streak(img, amt, n=4):
    """Смаз «на скорости» от точки схода (для слоя света в полразмера)."""
    if amt < 0.004:
        return img
    w, h = img.size
    cx, cy = VX * w / W, VY * h / H
    acc = np.asarray(img, np.float32).copy()
    for k in range(1, n + 1):
        z = 1 + amt * k / n
        cw, ch = w / z, h / z
        x0, y0 = cx - cw * cx / w, cy - ch * cy / h
        acc += np.asarray(img.resize((w, h), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)), np.float32)
    return Image.fromarray(np.clip(acc / (n + 1) * 1.6, 0, 255).astype(np.uint8), 'RGB')


def zoom_blur(fr, amt):
    """Смаз-наезд на всём кадре (пролёт знаков, разгон)."""
    if amt < 0.003:
        return fr
    z1 = C.zoom(fr, 1 + amt, VX, VY)
    z2 = C.zoom(fr, 1 + amt * 2, VX, VY)
    return Image.blend(Image.blend(fr, z1, 0.5), z2, 0.33)


# ─────────────────────────────── фон ───────────────────────────────
def _background(tint, seed=3):
    """Небо с заревом города в цвете tint, силуэты домов на горизонте, асфальт, обочины, отбойники, свет фар."""
    rnd = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sky_t = np.array((5, 8, 20), np.float32)
    sky_h = np.array(C.mix(C.mix(tint, SODIUM, 0.35), (10, 10, 20), 0.35), np.float32)
    g = np.clip(yy / VY, 0, 1)[..., None] ** 2.2
    arr = sky_t * (1 - g) + sky_h * g
    # зарево над горизонтом
    dd = np.sqrt(((xx - VX) / 760) ** 2 + ((yy - VY) / 330) ** 2)
    glow = np.clip(1 - dd, 0, 1) ** 1.6
    arr += glow[..., None] * np.array(C.mix(tint, SODIUM, 0.25), np.float32) * 0.55
    # земля
    gy = np.clip((yy - VY) / (H - VY), 0, 1)
    d = np.maximum(yy - VY, 0.01)
    X = (xx - VX) / d                                                # мировой X точки земли
    asph = np.array((22, 22, 26), np.float32) * (1 - gy[..., None]) + np.array((44, 42, 44), np.float32) * gy[..., None]
    shoulder = np.array((10, 12, 12), np.float32) * (1 - gy[..., None]) + np.array((22, 24, 22), np.float32) * gy[..., None]
    on_road = (np.abs(X) <= 2.25).astype(np.float32)[..., None]
    ground = asph * on_road + shoulder * (1 - on_road)
    ground = ground * (1 + rnd.normal(0, 0.05, (H, W, 1)).astype(np.float32))
    # свет фар: тёплый клин на асфальте перед кабиной
    hl = np.exp(-(X / 1.6) ** 2) * np.clip((yy - VY - 60) / 700, 0, 1) ** 1.2
    ground += hl[..., None] * np.array((60, 54, 44), np.float32)
    # отражение зарева у горизонта
    ground += (np.clip(1 - (yy - VY) / 90, 0, 1) ** 2)[..., None] * sky_h * 0.5
    below = (yy >= VY)[..., None]
    arr = np.where(below, ground, arr)
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
    dr = ImageDraw.Draw(im)
    # силуэт города
    x = 150
    while x < 930:
        bw = int(rnd.integers(14, 46))
        far = 1 - abs(x - VX) / 420
        bh = int(rnd.integers(8, 26) + 46 * max(0, far) * rnd.random())
        dr.rectangle((x, VY - bh, x + bw, VY), fill=(12, 12, 22))
        for wy in range(VY - bh + 4, VY - 3, 6):
            for wx in range(x + 3, x + bw - 3, 6):
                if rnd.random() < 0.22:
                    c = C.mix((255, 196, 120), tint, 0.25)
                    dr.point((wx, wy), fill=tuple(int(v * 0.7) for v in c))
        x += bw + int(rnd.integers(0, 6))
    # сплошные линии края (X = ±2.1) и отбойники (X = ±2.75, высота 0.35)
    for sg in (-1, 1):
        for X0, X1, col in ((2.04, 2.16, (196, 190, 170)),):
            pts = [(VX + sg * X0 * 2, VY + 2), (VX + sg * X1 * 2, VY + 2), (VX + sg * X1 * 1000, VY + 1000), (VX + sg * X0 * 1000, VY + 1000)]
            dr.polygon(pts, fill=col)
        top = [(VX + sg * 2.75 * dd_, VY + 0.62 * dd_) for dd_ in (3, 1000)]
        bot = [(VX + sg * 2.75 * dd_, VY + dd_) for dd_ in (3, 1000)]
        dr.polygon([top[0], top[1], bot[1], bot[0]], fill=(52, 52, 58))
        dr.line([top[0], top[1]], fill=(118, 116, 120), width=3)
    # дымка у горизонта поверх линий
    im = im.convert('RGBA')
    haze = Image.new('RGBA', (W, 120), C.mix(tint, SODIUM, 0.3) + (0,))
    ha = np.clip(1 - np.abs(np.arange(120) - 60) / 60, 0, 1) ** 1.5 * 70
    haze.putalpha(Image.fromarray(np.repeat(ha[:, None], W, 1).astype(np.uint8)))
    im.alpha_composite(haze, (0, VY - 60))
    return im.convert('RGB')


# ─────────────────────────────── ролик ───────────────────────────────
class Highway(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 65, drop=16 * 60 / 65, line=None, team=5.5,
                 run=1, hold=5, cta=2.5, bass=0.42, seed=11, **kw):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.T = {'h': self.h, 'a': self.a}
        self.league, self.when, self.coef, self.line = league, when, coef, line
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.raw = {'h': sh or {}, 'a': sa or {}}
        self.st = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.team_b = team
        self.bass = float(bass)                    # через сколько секунд после дропа (удар трека) входит бас
        self.t1 = self.b(-(2 * team + run))
        self.t2 = self.b(-(team + run))
        self.t_run = self.b(-run)
        if self.t1 < 2.0:
            raise ValueError('мало времени до дропа: %.2f с на интро' % self.t1)
        self.t_cta = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = round(self.t1 - 1.15, 2)
        self.t0 = {'h': self.t1, 'a': self.t2}
        self.t_end = {'h': self.t2, 'a': self.t_run}
        key = (home, away, league, when, pick, coef, tuple(line or ()), repr(sorted((sh or {}).items()))[:4000],
               repr(sorted((sa or {}).items()))[:4000], round(u, 5), round(drop, 4), team, run, hold, cta, seed)
        if key not in _CACHE:
            _CACHE[key] = self._prep()
        self.L = _CACHE[key]

    # ── скорость и путь ──
    def speed(self, t):
        u, D = self.u, self.drop
        v0 = 2 * DASH_P / u                                            # пунктир — на восьмые, фонарь — на долю
        k = 1.0
        for tb in (self.t1, self.t2, self.t_run):
            k += 0.9 * math.exp(-((t - tb) / 0.22) ** 2)                # рывок на пролёте знаков
        if t >= self.t_run - 0.3:
            k += 2.6 * C.in_cubic(C.seg(t, self.t_run - 0.3, D))
        if t >= D:
            k *= 1 - C.out_cubic(C.seg(t, D, D + 0.4))                  # под порталом — встали
        return v0 * k

    def _path(self):
        dt = 1 / 600
        n = int((self.dur + 1) / dt) + 2
        ts = np.arange(n) * dt
        v = np.array([self.speed(x) for x in ts], np.float64)
        return np.concatenate([[0.0], np.cumsum((v[1:] + v[:-1]) * 0.5 * dt)])

    def pos(self, t):
        p = self.L['path']
        i = t * 600
        i0 = int(clamp_i(i, 0, len(p) - 2))
        f = i - i0
        return p[i0] * (1 - f) + p[i0 + 1] * f

    # ── заготовки ──
    def _prep(self):
        L = {}
        self.L = L
        L['path'] = self._path()
        cols = {'i': (70, 110, 190), 'h': _vivid(self.h.c1), 'a': _vivid(self.a.c1)}
        cols['p'] = cols[self.side]
        L['bg'] = {k: _background(c) for k, c in cols.items()}
        L['tint'] = cols
        # @jarvibet
        hp = panel(344, 64, 14, GREEN, WHITE, 6, 4)
        C.put(hp, C.text(C.HANDLE, FN, 44, WHITE, 700, track=0.03), 172, 33)
        L['handle'] = with_sh(hp, 10, 0.55, 4)
        self._prep_intro(L)
        for k in ('h', 'a'):
            self._prep_team(L, k)
        self._prep_pick(L)
        L['tg'] = C.tg_plate(900, 170)
        L['tg_sh'] = C.shadow(L['tg'], 18, 0.6)
        return L

    def _prep_intro(self, L):
        w, h = 960, 526
        pl = panel(w, h, 28)
        for k, cx in (('h', w * 0.25), ('a', w * 0.75)):
            t = self.T[k]
            C.put(pl, circle_badge(t, 214, t.c1), cx, 148)
            C.put(pl, C.text(t.up, FN, 80, WHITE, 700, max_w=w / 2 - 60), cx, 316)
            C.put(pl, C.text('ХОЗЯЕВА' if k == 'h' else 'ГОСТИ', FN, 38, (190, 230, 206), 600, track=0.12), cx, 380)
        dr = ImageDraw.Draw(pl)
        dr.line((w / 2, 46, w / 2, 392), fill=WHITE + (255,), width=4)
        dr.line((40, 418, w - 40, 418), fill=WHITE + (255,), width=4)
        C.put(pl, C.text(self.when.upper(), FN, 60, WHITE, 700, track=0.02, max_w=w - 100), w / 2, 470)
        tb = tab(F.tag(self.league), 72, size=40)
        grp = Image.new('RGBA', (w, h + 54), (0, 0, 0, 0))
        grp.alpha_composite(pl, (0, 54))
        grp.alpha_composite(tb, (60, 0))
        L['i_sign'] = with_sh(grp, 18, 0.65, 10)
        L['i_sign_cy'] = 312 + grp.height / 2                       # верх таблички — y 312
        # полосные знаки П1 · Х · П2
        L['lanes'] = []
        if self.line:
            for lab, v in zip(('П1', 'Х', 'П2'), self.line):
                lw, lh = 312, 392
                s = panel(lw, lh, 22)
                lt = C.text(lab, FN, 60, GREEN, 800)
                lp = C.rrect(max(108, lt.width + 48), 80, 12, WHITE)
                C.put(lp, lt, lp.width / 2, 41)
                C.put(s, lp, lw / 2, 74)
                C.put(s, C.text(C.fmt_k(v), FN, 140, WHITE, 800, max_w=lw - 46), lw / 2, 198)
                C.put(s, arrow_down(78, 90), lw / 2, 318)
                L['lanes'].append(with_sh(s, 14, 0.6, 8))

    def _rows(self, key):
        games = self.st[key]['games']
        out = []
        rw = 840
        for g in games:
            row = Image.new('RGBA', (rw, 104), (0, 0, 0, 0))
            C.put(row, chip(g['res'], 84), 42, 52)
            sc = C.text(g['score'], FN, 84, WHITE, 800)
            nt = note_tag(g['note'], 54) if g['note'] else None
            bw = sc.width + (nt.width + 14 if nt is not None else 0)
            x = rw - bw
            C.put(row, sc, x, 52 - sc.height / 2, anchor='tl')
            if nt is not None:
                C.put(row, nt, x + sc.width + 14, 52 - nt.height / 2 + 2, anchor='tl')
            name = C.text(str(g['opp']).upper(), FN, 70, WHITE, 700, max_w=rw - 118 - bw - 40)
            C.put(row, name, 116, 52 - name.height / 2, anchor='tl')
            out.append(row)
        return out

    def _prep_team(self, L, key):
        t, s, r = self.T[key], self.st[key], self.raw[key]
        w = 920
        rows = self._rows(key)
        top_h = 222
        h = top_h + 26 + max(1, len(rows)) * 116 + 20 if rows else top_h
        base = panel(w, h, 28)
        C.put(base, circle_badge(t, 170, t.c1), 40 + 85, 30 + 85 + 4)
        nm = C.text(t.up, FN, 118, WHITE, 700, max_w=w - 260)
        C.put(base, nm, 246, 122 - nm.height / 2, anchor='tl')
        if rows:
            ImageDraw.Draw(base).line((36, top_h, w - 36, top_h), fill=WHITE + (255,), width=4)
        full = base.copy()
        row_pos = []
        for i, rw in enumerate(rows):
            x, y = 40, top_h + 26 + i * 116
            full.alpha_composite(rw, (x, y))
            row_pos.append((x, y))
        tb = tab('ХОЗЯЕВА' if key == 'h' else 'ГОСТИ', 72, size=42)
        def grp(p):
            g = Image.new('RGBA', (w, h + 54), (0, 0, 0, 0))
            g.alpha_composite(p, (0, 54))
            g.alpha_composite(tb, (w - tb.width - 50, 0))
            return g
        pad = 18 * 3
        L['t_base_' + key] = with_sh(grp(base), 18, 0.65, 10)
        L['t_full_' + key] = with_sh(grp(full), 18, 0.65, 10)
        L['t_rows_' + key] = rows
        top = 300
        gh = h + 54
        L['t_cy_' + key] = top + gh / 2
        L['t_rowxy_' + key] = [(VX - w / 2 + x, top + 54 + y) for x, y in row_pos]
        L['t_bottom_' + key] = top + gh
        # знаки у обочины: очки, место, разница шайб
        signs = []
        if s['points'] is not None:
            sub = ('за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей'))) if s['gp'] is not None else ''
            signs.append(on_post(speed_sign('ОЧКИ', '%d' % s['points'], sub), post_to=230))
        if s['place'] is not None:
            sc = s['place_scope'].upper()
            signs.append(on_post(shield_sign('МЕСТО', '%d' % s['place']), plaque(sc, 280) if sc else None, post_to=230))
        if s['gd'] is not None:
            pq = plaque('РАЗНИЦА ШАЙБ', 290, 62, YEL, BLACK, BLACK, 36)
            signs.append(on_post(diamond_sign(F.gd_txt(s['gd'])), pq, post_to=230))
        n = len(signs)
        xs = {1: [540], 2: [300, 780], 3: [190, 540, 890]}.get(n, [])
        bot = 1382                                                    # низ знаков (без стойки)
        L['b_signs_' + key] = []
        for sg, x in zip(signs, xs):
            vis_h = sg.height - 230
            cy = bot - vis_h + sg.height / 2
            L['b_signs_' + key].append((sg, x, cy))

    def _prep_pick(self, L):
        t = self.T[self.side]
        w, h = 1000, 956
        pl = panel(w, h, 30)
        C.put(pl, circle_badge(t, 356, t.c1), w / 2, 44 + 178)
        C.put(pl, C.text(self.pick1, FN, 116, WHITE, 800, max_w=w - 90), w / 2, 516)
        if self.pick2:
            C.put(pl, C.text(self.pick2, FN, 62, (214, 240, 222), 700, track=0.06, max_w=w - 120), w / 2, 612)
        yb = 694
        # жёлтая полоса снизу с кэфом
        ybar = Image.new('RGBA', (w - 24, h - 12 - yb), YEL + (255,))
        m = C.rrect(w - 24, h - 12 - yb + 40, 20, (255, 255, 255)).getchannel('A').crop((0, 40, w - 24, h - 12 - yb + 40))
        ybar.putalpha(m)
        pl.alpha_composite(ybar, (12, yb))
        ImageDraw.Draw(pl).line((12, yb, w - 12, yb), fill=WHITE + (255,), width=6)
        kl = C.text('КЭФ', FN, 74, BLACK, 700, track=0.06)
        kv = C.text(C.fmt_k(self.coef), FN, 164, BLACK, 800)
        gap = 34
        tw = kl.width + gap + kv.width
        x0 = w / 2 - tw / 2
        cyb = yb + (h - 12 - yb) / 2 + 4
        C.put(pl, kl, x0, cyb - kl.height / 2 + 14, anchor='tl')
        C.put(pl, kv, x0 + kl.width + gap, cyb - kv.height / 2, anchor='tl')
        L['p_sign'] = with_sh(pl, 20, 0.7, 12)
        dark = panel(w, h, 30, (8, 30, 22), (40, 58, 50), sheen=False)
        L['p_dark'] = with_sh(dark, 20, 0.6, 12)
        L['p_cy'] = 344 + h / 2
        L['p_kef_box'] = (VX - w / 2 + 12, 344 + yb, VX + w / 2 - 12, 344 + h - 12)
        L['lamp'] = C.rrect(96, 34, 10, (40, 44, 50), outline=(90, 96, 104), width=3)
        lens = C.rrect(70, 14, 6, (255, 246, 220))
        C.put(L['lamp'], lens, 48, 22)
        L['streak'] = C.radial(1500, 40, (255, 236, 200), 255, 1.2)
        L['flare'] = C.radial(520, 520, (255, 226, 170), 255, 2.2)
        cone = np.zeros((560, 420), np.float32)
        yy, xx = np.mgrid[0:560, 0:420].astype(np.float32)
        spread = 40 + yy * 0.32
        cone = np.clip(1 - np.abs(xx - 210) / spread, 0, 1) ** 1.5 * np.clip(1 - yy / 560, 0, 1) ** 1.2
        arr = np.zeros((560, 420, 4), np.uint8)
        arr[..., :3] = (255, 236, 196)
        arr[..., 3] = (cone * 120).astype(np.uint8)
        L['cone'] = Image.fromarray(arr, 'RGBA')

    # ─────────────────────────────── дорога ───────────────────────────────
    def road(self, key, t, streak=0.0, lit=None):
        """Фон сцены + разметка, отражатели, опоры фонарей и свет (в полразмера, со смазом на скорости)."""
        fr = self.L['bg'][key].copy()
        pos = self.pos(t)
        v = self.speed(t)
        v0 = 2 * DASH_P / self.u
        # разметка: пунктир X = ±0.7
        mk = Image.new('L', (W, H - VY), 0)
        dm = ImageDraw.Draw(mk)
        ext = min(3.0, max(0.0, (v / v0 - 1.0)) * 0.6)
        ph = pos % DASH_P
        for X in (-0.7, 0.7):
            for k in range(0, 36):
                za = k * DASH_P - ph
                zb = za + DASH_L + ext
                if zb < ZMIN:
                    continue
                za = max(za, ZMIN)
                d1, d2 = FPX / za, FPX / zb
                if d1 < 2:
                    break
                fog = C.clamp((d2 - 2) / 40) * 0.75 + 0.25
                hw = 0.055
                pts = [(VX + (X - hw) * d1, d1), (VX + (X + hw) * d1, d1), (VX + (X + hw) * d2, d2), (VX + (X - hw) * d2, d2)]
                dm.polygon(pts, fill=int(225 * fog))
        mk = mk.filter(ImageFilter.GaussianBlur(0.8))
        fr.paste((232, 230, 214), (0, VY), mk)
        dr = ImageDraw.Draw(fr)
        # отражатели на отбойниках
        rp = 3.2
        ph2 = pos % rp
        for k in range(0, 40):
            z = k * rp - ph2 + 1.0
            if z < ZMIN:
                continue
            d = FPX / z
            if d < 3:
                break
            r_ = max(1.0, 0.03 * d)
            for sg in (-1, 1):
                x, y = VX + sg * 2.73 * d, VY + 0.6 * d
                if -20 < x < W + 20:
                    dr.ellipse((x - r_, y - r_ * 0.7, x + r_, y + r_ * 0.7), fill=(255, 168, 60))
        # опоры и фонари
        acc = np.zeros((H // 2, W // 2, 3), np.float32)
        spill = np.zeros((H // 2, W // 2, 3), np.float32)
        ph3 = pos % POLE_P
        lamps = []
        for k in range(0, 18):
            z = k * POLE_P - ph3 + 0.5 * POLE_P
            if z < 0.45:
                continue
            d = FPX / z
            if d < 4:
                break
            for sg in (-1, 1):
                xb, yb = VX + sg * 3.3 * d, VY + d
                xt, yt = xb, VY - 3.15 * d
                xl, yl = VX + sg * 2.45 * d, VY - 3.0 * d
                wd = max(1, int(0.075 * d))
                if -200 < xb < W + 200:
                    dr.line((xb, yb, xt, yt), fill=(26, 28, 34), width=wd)
                    dr.line((xt, yt, xl, yl), fill=(26, 28, 34), width=max(1, int(wd * 0.7)))
                    lw_ = max(1.5, 0.16 * d)
                    dr.ellipse((xl - lw_, yl - lw_ * 0.35, xl + lw_, yl + lw_ * 0.45), fill=(255, 226, 180))
                lamps.append((sg, d, xl, yl))
        for sg, d, xl, yl in lamps:
            add_blob(acc, xl, yl, min(330, 0.9 * d + 10), min(330, 0.9 * d + 10), SODIUM, 0.9, 2.2)
            add_blob(acc, xl, yl, min(120, 0.25 * d + 4), min(120, 0.25 * d + 4), (255, 230, 190), 1.4, 1.6)
            # пятно света на асфальте
            rx = 2.0 * d
            ry = 2.0 * d * d / FPX
            if ry > 1:
                add_blob(acc, VX + sg * 2.3 * d, VY + d, min(900, rx), min(900, ry), SODIUM, 0.42, 1.6)
            if d > 110:                                              # тёплый свет проходящего фонаря на знаках
                add_blob(spill, xl, yl, min(900, 1.7 * d), min(900, 1.7 * d), SODIUM, 0.30 * C.clamp((d - 110) / 120), 1.8)
        if lit is not None:
            lit(acc)
        lay = Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8), 'RGB')
        if streak > 0:
            lay = radial_streak(lay, streak)
        lay = lay.resize((W, H), Image.BILINEAR)
        sp = Image.fromarray(np.clip(spill, 0, 255).astype(np.uint8), 'RGB').resize((W, H), Image.BILINEAR) if spill.max() > 2 else None
        return ImageChops.add(fr, lay), sp

    # ─────────────────────────────── сцены ───────────────────────────────
    def gantry(self, fr, s, a=1.0, y=BEAM_Y, span=(-260, 1340), hang=(-300, 300), hang_to=None):
        """Портал: ферма поперёк дороги (две полки и раскосы), подвесы к знаку. Рисуется в перспективе."""
        if a <= 0.01 or s <= 0.01:
            return
        dr = ImageDraw.Draw(fr)
        col = C.mix((14, 16, 20), STEEL, a)
        hi = C.mix((14, 16, 20), (120, 128, 140), a)
        t_, b_ = y - 20, y + 16
        x0, x1 = span
        p = lambda x, yy: persp(s, x, yy)
        lw = max(1, int(7 * s))
        for yy in (t_, b_):
            dr.line((*p(x0, yy), *p(x1, yy)), fill=col, width=lw)
        dr.line((*p(x0, t_ - 3), *p(x1, t_ - 3)), fill=hi, width=max(1, int(2 * s)))
        x = x0
        k = 0
        while x < x1:
            xa, xb = x, x + 64
            dr.line((*p(xa, t_ if k % 2 == 0 else b_), *p(xb, b_ if k % 2 == 0 else t_)), fill=col, width=max(1, int(4 * s)))
            x = xb
            k += 1
        # стойки портала (видны, пока портал далеко)
        for xx in (x0 + 40, x1 - 40):
            dr.line((*p(xx, t_), *p(xx, VY + 560)), fill=col, width=max(1, int(16 * s)))
        if hang_to is not None:
            for hx in hang:
                dr.line((*p(VX + hx, b_), *p(VX + hx, hang_to)), fill=col, width=max(1, int(8 * s)))

    @staticmethod
    def spill(fr, sp):
        if sp is None:
            return fr
        return ImageChops.add(fr.convert('RGB'), sp).convert('RGBA')

    def handle(self, fr, t):
        a = C.seg(t, 0.15, 0.5)
        if t >= self.t_cta:
            a *= 1 - C.seg(t, self.t_cta, self.t_cta + 0.18)
        if a > 0:
            C.put(fr, self.L['handle'], W / 2, HANDLE_Y, a)

    def intro(self, t):
        L, u = self.L, self.u
        fly = C.seg(t, self.t1 - 0.3, self.t1)
        fr, sp = self.road('i', t)
        fr = fr.convert('RGBA')
        # портал с обеими командами: подлёт 0 → 0.55 с
        s = _approach(C.seg(t, 0.0, 0.55), 10) if fly <= 0 else _flyby(fly)
        fa = 1 - C.seg(fly, 0.7, 1.0)
        self.gantry(fr, s, fa, hang_to=L['i_sign_cy'] - L['i_sign'].height / 2 + 60)
        put_persp(fr, L['i_sign'], VX, L['i_sign_cy'], s, fa)
        # полосные знаки встают на 1-ю долю (по очереди через 0.12 с)
        tb = self.b(-16) + u if self.drop >= 16 * u - 1e-6 else u    # 1-я доля ролика
        tb = max(u, tb)
        xs = (192, 540, 888)
        for i, im in enumerate(L['lanes']):
            ta = tb + 0.12 * i
            q = C.seg(t, ta - 0.42, ta)
            if q <= 0:
                continue
            sl = _approach(q, 9) if fly <= 0 else _flyby(fly)
            put_persp(fr, im, xs[i], 1104, sl, fa * min(1.0, q * 3))
            if fly <= 0:
                self.glint(fr, im, xs[i], 1104, t - ta)
        return self.spill(fr, sp)

    def glint(self, fr, im, cx, cy, dt, dur=0.42):
        """Блик фар по светоотражающей плёнке после посадки знака."""
        if dt < 0 or dt > dur:
            return
        key = ('gl', id(im))
        if key not in _SPR:
            _SPR[key] = np.asarray(im.getchannel('A'), np.float32) / 255
        al = _SPR[key]
        h, w = al.shape
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
        xx = np.arange(w, dtype=np.float32)[None, :]
        yy = np.arange(h, dtype=np.float32)[:, None]
        p = -0.3 * w + (w * 1.6) * (dt / dur)
        band = np.exp(-((xx + yy * 0.45 - p) / (w * 0.07)) ** 2) * al * 70 * (1 - dt / dur * 0.5)
        X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
        if X1 <= X0 or Y1 <= Y0:
            return
        reg = fr.crop((X0, Y0, X1, Y1))
        arr = np.asarray(reg, np.float32)
        b = band[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0, None]
        arr = arr.copy()
        arr[..., :3] = np.clip(arr[..., :3] + b, 0, 255)
        fr.paste(Image.fromarray(arr.astype(np.uint8), 'RGBA'), (X0, Y0))

    def team(self, key, t):
        L, u = self.L, self.u
        t0, te = self.t0[key], self.t_end[key]
        fly = C.seg(t, te - 0.3, te)
        fr, sp = self.road(key, t)
        fr = fr.convert('RGBA')
        fa = 1 - C.seg(fly, 0.7, 1.0)
        sign_top = L['t_cy_' + key] - L['t_base_' + key].height / 2 + 54
        # большой указатель: подлёт за половину доли
        q = C.seg(t, t0, t0 + 0.5 * u)
        s = _approach(q, 12) if fly <= 0 else _flyby(fly)
        self.gantry(fr, s, fa, hang_to=sign_top + 60)
        rows = L['t_rows_' + key]
        row_t = [t0 + u * (1 + 0.5 * i) for i in range(len(rows))]
        if fly > 0 or q < 1:
            img = L['t_full_' + key] if fly > 0 else L['t_base_' + key]
            put_persp(fr, img, VX, L['t_cy_' + key], s, fa * min(1.0, q * 4 + (fly > 0)))
        else:
            C.put(fr, L['t_base_' + key], VX, L['t_cy_' + key])
            self.glint(fr, L['t_base_' + key], VX, L['t_cy_' + key], t - (t0 + 0.5 * u), 0.5)
            for (x, y), rw, tr in zip(L['t_rowxy_' + key], rows, row_t):
                qr = C.out_cubic(C.seg(t, tr, tr + 0.28))
                if qr <= 0:
                    continue
                C.put(fr, rw, x - 40 * (1 - qr), y, qr, anchor='tl')
                fl = 1 - C.seg(t, tr, tr + 0.4)
                if fl > 0:                                               # строка «загорается» в свете фар
                    C.put(fr, C.tint(rw, (255, 255, 240)), x - 40 * (1 - qr), y, 0.75 * fl * qr, anchor='tl')
        # знаки у обочины: на доли 3, 3½, 4
        for i, (im, x, cy) in enumerate(L['b_signs_' + key]):
            tb = t0 + u * (3 + 0.5 * i)
            qb = C.seg(t, tb - 0.42, tb)
            if qb <= 0:
                continue
            sb = _approach(qb, 9) if fly <= 0 else _flyby(fly)
            put_persp(fr, im, x, cy, sb, fa * min(1.0, qb * 3))
            if fly <= 0:
                self.glint(fr, im, x, cy, t - tb, 0.4)
        return self.spill(fr, sp)

    def run(self, t):
        """Разгон: фонари в полосы, тёмный портал надвигается."""
        L, D = self.L, self.drop
        q = C.seg(t, self.t_run, D)
        streak = 0.05 + 0.22 * C.in_cubic(q)
        fr, sp = self.road('p', t, streak=streak)
        fr = fr.convert('RGBA')
        s = 1.0 / (1.0 + 13 * (1 - q))
        self.gantry(fr, s, 0.6 + 0.4 * q, hang_to=L['p_cy'] - 478 + 4)
        put_persp(fr, L['p_dark'], VX, L['p_cy'], s, min(1.0, q * 4))
        return self.spill(fr, sp)

    def pick(self, t):
        L, u, D = self.L, self.u, self.drop
        ck = C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.6))
        pulse = math.exp(-(((t - D) / u) % 1.0) * 6) if t >= D else 0.0
        fl0 = math.exp(-(t - D) / 0.35) if t >= D else 0.0             # вспышка прожекторов на дропе
        tb2 = D + self.bass
        fl0 += 0.75 * math.exp(-(t - tb2) / 0.3) if t >= tb2 else 0.0   # второй удар — вход баса

        def lit(acc):
            for lx in (250, 540, 830):
                add_blob(acc, lx, BEAM_Y + 30, 260, 200, (255, 228, 180), 0.35 + 0.25 * pulse + 1.2 * fl0, 2.0)

        fr, sp = self.road('p', t, lit=lit)
        fr = fr.convert('RGBA')
        # камера встаёт с лёгким «клевком», на финале портал уменьшается и уходит вверх
        settle = 0.018 * math.sin(min(1.0, (t - D) / 0.45) * math.pi) * (1 - C.seg(t, D, D + 0.45))
        s = 1.0 + settle
        sc = 1 - 0.18 * ck
        ay = 300

        def pt(y):
            return ay + (y - ay) * sc
        top_y = 344
        self.gantry(fr, s * sc, 1.0, y=pt(BEAM_Y), hang_to=pt(top_y + 4)) if sc == 1 else self._gantry_c(fr, sc, ay)
        img = L['p_sign'] if sc > 0.999 else C.scale(L['p_sign'], sc)
        cy = pt(L['p_cy'])
        put_persp(fr, img, VX, cy, s)
        # конусы света прожекторов поверх знака
        k_cone = 0.55 + 0.25 * pulse + 0.6 * fl0
        for lx in (250, 540, 830):
            x = VX + (lx - VX) * sc
            C.put(fr, L['cone'], x, pt(BEAM_Y + 30) + 280 * sc, min(1.0, k_cone * (1 - 0.4 * ck)))
            C.put(fr, L['lamp'] if sc > 0.999 else C.scale(L['lamp'], sc), x, pt(BEAM_Y + 30))
        # блик по кэфу на следующую долю
        if t >= D + u - 0.02 and sc > 0.999:
            x0, y0, x1, y1 = L['p_kef_box']
            self._sweep(fr, (x0, y0, x1, y1), t - (D + u), 0.5)
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.3, self.t_cta + 0.75))
            if q > 0:
                C.put(fr, L['tg_sh'], W / 2, 1300 + 18 + 170 * (1 - q), 0.6 * q)
                C.put(fr, L['tg'], W / 2, 1300 + 170 * (1 - q), q)
        # блики прожекторов (поверх всего)
        if fl0 > 0.01 or pulse > 0.05:
            rgb = fr.convert('RGB')
            for lx in (250, 540, 830):
                x = VX + (lx - VX) * sc
                rgb = C.add_light(rgb, L['flare'], x, pt(BEAM_Y + 36), 0.25 * pulse + 1.1 * fl0)
            rgb = C.add_light(rgb, L['streak'], W / 2, pt(BEAM_Y + 36), 0.2 * pulse + 1.0 * fl0)
            fr = rgb.convert('RGBA')
        return fr

    def _gantry_c(self, fr, sc, ay):
        self.gantry(fr, 1.0, 1.0, y=ay + (BEAM_Y - ay) * sc, hang_to=ay + (344 + 4 - ay) * sc,
                    hang=(-300 * sc, 300 * sc))

    def _sweep(self, fr, box, dt, dur):
        if dt < 0 or dt > dur:
            return
        x0, y0, x1, y1 = [int(v) for v in box]
        reg = fr.crop((x0, y0, x1, y1))
        arr = np.asarray(reg, np.float32).copy()
        w, h = x1 - x0, y1 - y0
        xx = np.arange(w, dtype=np.float32)[None, :]
        yy = np.arange(h, dtype=np.float32)[:, None]
        p = -0.2 * w + 1.4 * w * dt / dur
        band = np.exp(-((xx + yy * 0.5 - p) / (w * 0.06)) ** 2) * 110
        arr[..., :3] = np.clip(arr[..., :3] + band[..., None], 0, 255)
        fr.paste(Image.fromarray(arr.astype(np.uint8), 'RGBA'), (x0, y0))

    # ─────────────────────────────── кадр ───────────────────────────────
    def scene(self, t):
        if t < self.t1:
            return self.intro(t)
        if t < self.t2:
            return self.team('h', t)
        if t < self.t_run:
            return self.team('a', t)
        if t < self.drop:
            return self.run(t)
        return self.pick(t)

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.scene(t).convert('RGB')
        # смаз-наезд на пролётах знаков и на разгоне
        zb = 0.0
        for tb in (self.t1, self.t2, self.t_run):
            if tb - 0.3 <= t < tb + 0.18:
                zb = max(zb, 0.035 * (C.seg(t, tb - 0.3, tb) if t < tb else 1 - C.seg(t, tb, tb + 0.18)))
        if self.t_run <= t < D:
            zb = max(zb, 0.012 + 0.03 * C.in_cubic(C.seg(t, self.t_run, D)))
        fr = zoom_blur(fr, zb)
        # камера: лёгкий толчок на каждую долю, дрожь на разгоне, удар на дроп
        z, dx, dy = 1.0, 0.0, 0.0
        n = math.floor((t - D) / u + 1e-6)
        tb = D + n * u
        if t < self.t_cta and t - tb < 0.25:
            z += 0.008 * (1 - (t - tb) / 0.25) ** 2
        if self.t_run - 0.3 <= t < D:
            q = C.seg(t, self.t_run - 0.3, D)
            dx += (2 + 7 * q) * math.sin(t * 71)
            dy += (2 + 7 * q) * math.cos(t * 57)
        if t >= D:
            sx, sy = C.shake(t, D, 22, 0.45)
            sx2, sy2 = C.shake(t, D + self.bass, 14, 0.35)
            dx, dy = dx + sx + sx2, dy + sy + sy2
            if t >= D + self.bass:
                z += 0.025 * (1 - C.seg(t, D + self.bass, D + self.bass + 0.35)) ** 2
            z += 0.05 * (1 - C.seg(t, D, D + 0.45)) ** 2
        if z > 1.0005 or abs(dx) > 0.3 or abs(dy) > 0.3:
            fr = C.zoom(fr, z, VX, VY * 0.7, dx=dx, dy=dy)
        if D - 0.12 <= t < D:
            fr = Image.blend(fr, Image.new('RGB', fr.size, (255, 246, 228)), 0.45 * C.seg(t, D - 0.12, D))
        elif D <= t < D + 0.1:
            fr = Image.blend(fr, Image.new('RGB', fr.size, (255, 250, 240)), 0.85 * (1 - C.seg(t, D, D + 0.1)))
        fr = C.vignette(fr, 0.42)
        fr = fr.convert('RGBA')
        self.handle(fr, t)
        return C.grain(fr, t, 4)


def clamp_i(v, a, b):
    return a if v < a else b if v > b else v
