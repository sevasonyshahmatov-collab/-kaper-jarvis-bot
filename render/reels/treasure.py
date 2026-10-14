# -*- coding: utf-8 -*-
"""«Карта» — старинная карта сокровищ (трек «Rodeo», поздний дроп после провала): пергамент с опалёнными краями
на тёмном столе при свече, чернильная рамка-шкала, румбовые линии, роза ветров, морские чудища, корабль и волны
на полях. Путь каждой команды — пунктир чернилами (перо ведёт линию на долях) от сургучной печати с эмблемой
от острова к острову; каждый остров — один факт, подписанный от руки, но крупно. Камера ездит по карте за пером.

Мир — лист 2160×3500: сверху картуш матча, ниже две «страницы» (хозяева слева, гости справа, зеркально),
внизу между ними роза ветров — место клада. Сцены (u — доля трека, D — дроп; доли от дропа; team / pre / hold / cta):
  интро (до D − (2·team + pre) долей) — картуш: обе эмблемы, названия, «хозяева / гости», лига и время МСК;
                 под картушем — линия основного времени П1 · Х · П2 тремя крупными пергаментными плашками
                 (штампуются на 0,5 / 0,75 / 1 долю);
  команда (team долей) ×2 — на долю склейки камера перелетает к странице клуба; через полдоли — сургучная печать
                 с эмблемой и название клуба; с 1-й доли перо на каждой половине доли доводит пунктир до очередного
                 острова: последние 3 игры (соперник, счёт, ОТ/Б, печать В/П, дата, дома / в гостях), затем архипелаг
                 из трёх островов — очки за N матчей, место, разница шайб (пустые поля не показываются); у гостей
                 и хозяев под названием — серия от 2 игр, если она есть. Последний факт — на 3,5 доли, дальше 3,5 доли
                 на чтение, камера плавно отъезжает к целой странице;
  поиск (pre долей) — вся карта целиком на столе, оба пути чернилами сходятся к розе ветров, стрелка компаса
                 раскручивается; в провале трека (dip) свеча почти гаснет, на возврате звука (dip[1]) камера ныряет
                 к месту клада, на подхвате (kick) — второй толчок;
  ДРОП (hold долей) — ровно на дропе красный крест штампом на месте клада, сундук распахивается, из света
                 поднимается ТОЛЬКО эмблема команды прогноза (без второй и без «VS»), свиток разворачивается:
                 «ПОБЕДА / КЛУБ», «в основное время», кэф; искры и монеты, на каждую долю — пульс света;
  финал (cta долей) — сундук и свиток уходят выше, снизу плашка Telegram (C.tg_plate, текст по центру плашки).
Метка JARVIS | NHL сверху и @jarvibet у низа безопасной зоны (y 1448) — кожаные бирки, одинаковые во всех сценах
(поверх света и тряски); @jarvibet уступает место плашке Telegram в финале.
Кадр — чистая функция t: лист, все печати, острова, подписи и пунктиры заранее «запечены» в слои мира
(пустая карта → с картушем → со страницей хозяев → со страницей гостей → со сходящимися путями), в кадре
дорисовывается только то, что появляется в этот момент. Слои — в модульном кеше (до fork — общие для процессов).
"""
import colorsys
import math
import re

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from reels import core as C
from reels import form as F
from reels.core import W, H

C.FONTS.setdefault('yes', 'YesevaOne-Regular.ttf')        # антиква с «прямыми» цифрами (у Prata 1 похожа на l)

# ─────────────────────────────── палитра и геометрия ───────────────────────────────
PAPER = (228, 203, 154)
PAPER_L = (241, 225, 186)
LAND = (214, 197, 146)
INK = (52, 32, 17)
INK2 = (104, 70, 40)
RED = (172, 30, 22)
WIN_INK = (40, 116, 54)
LOSS_INK = (170, 42, 30)
GOLD = (255, 204, 96)
CREAM = (247, 234, 204)
LEATHER = (62, 36, 20)

PW, PH = 2160, 3500                 # лист карты (мир)
M = 560                             # стол вокруг листа в слое мира
HPAD = 520                          # ещё стол вокруг половинных слоёв обзора
PAGE_Y = 1300                       # верх окна страницы клуба в мире
CMP = (1080.0, 2990.0)              # роза ветров = место клада
CMP_R = 210
TAG_Y, HY = 262, 1448
S_PICK = 1.6                        # масштаб камеры на кладе
X_Y = 790                           # где на экране стоит клад
INTRO_C = (1080.0, 960.0)
PAGE_C = {'h': (580.0, 2260.0), 'a': (1580.0, 2260.0)}
S_OV = 1184.0 / PH                  # обзор всей карты
OV_C = (1080.0, PH / 2 + (960 - 842) / S_OV)

# страница клуба (в координатах экрана для хозяев; у гостей — зеркально)
SEAL = (182, 392)
SEAL_D = 222
NAME_X = 318
G_NODES = [(178, 612), (902, 797), (178, 982)]
K_NODES = [(192, 1190), (540, 1190), (888, 1190)]
G_ISL = (196, 132)
K_ISL = (286, 150)

_BAKE, _SPR = {}, {}


# ─────────────────────────────── мелочи ───────────────────────────────
def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def gd_str(v):
    return ('+%d' % v) if v > 0 else ('–%d' % -v) if v < 0 else '0'


def paste(dst, im, cx, cy, a=1.0, anchor='c'):
    """Наложить RGBA im на dst (центр или левый верх), прозрачность a. RGBA-цель — честное наложение (alpha_composite)."""
    if im is None or a <= 0.004:
        return
    if dst.mode == 'RGBA':
        C.put(dst, im, cx, cy, a, anchor)
        return
    if a < 0.996:
        im = C.fade(im, a)
    x = int(round(cx - im.width / 2)) if anchor == 'c' else int(round(cx))
    y = int(round(cy - im.height / 2)) if anchor == 'c' else int(round(cy))
    if x >= dst.width or y >= dst.height or x + im.width <= 0 or y + im.height <= 0:
        return
    dst.paste(im, (x, y), im)


def wax_col(team):
    cands = []
    for c in (team.c1, team.c0, team.c2):
        h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
        if s > 0.25 and v > 0.25:
            cands.append(c)
    c = cands[0] if cands else team.c1
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    v = min(0.8, max(0.44, v))
    s = min(s, 0.88)
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, s, v))


def _nz(w, h, cx, cy, rnd):
    """Гладкий шум 0..1 размера w×h с ячейкой cx×cy."""
    gw, gh = max(2, int(w / cx) + 2), max(2, int(h / cy) + 2)
    a = rnd.random((gh, gw)).astype(np.float32)
    return np.asarray(Image.fromarray(a, 'F').resize((w, h), Image.BICUBIC), np.float32)


def bez(p0, c1, c2, p3, n=None):
    if n is None:
        n = max(8, int((math.dist(p0, c1) + math.dist(c1, c2) + math.dist(c2, p3)) / 3))
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append((a * p0[0] + b * c1[0] + c * c2[0] + d * p3[0], a * p0[1] + b * c1[1] + c * c2[1] + d * p3[1]))
    return out


def capsule(x0, y0, x1, y1, w, col, al=255):
    """Чернильный штрих (капсула) со сглаживанием → (спрайт, левый верх)."""
    ss = 4
    pad = w + 3
    bx0, by0 = min(x0, x1) - pad, min(y0, y1) - pad
    bw, bh = int(abs(x1 - x0) + 2 * pad) + 1, int(abs(y1 - y0) + 2 * pad) + 1
    im = Image.new('L', (bw * ss, bh * ss), 0)
    d = ImageDraw.Draw(im)
    p = [((x0 - bx0) * ss, (y0 - by0) * ss), ((x1 - bx0) * ss, (y1 - by0) * ss)]
    d.line(p, fill=al, width=int(w * ss))
    r = w * ss / 2
    for (x, y) in p:
        d.ellipse((x - r, y - r, x + r, y + r), fill=al)
    m = im.resize((bw, bh), Image.LANCZOS)
    out = Image.new('RGBA', (bw, bh), tuple(col) + (0,))
    out.putalpha(m)
    return out, (bx0, by0)


def dashes(pts, col, w=7, dash=20, gap=14, rnd=None):
    """Пунктир по ломаной pts → [(спрайт, (x, y) левый верх, длина пути до конца штриха)], полная длина."""
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    L = cum[-1]

    def at(s):
        s = C.clamp(s, 0, L)
        for i in range(1, len(cum)):
            if cum[i] >= s:
                k = (s - cum[i - 1]) / max(1e-6, cum[i] - cum[i - 1])
                a, b = pts[i - 1], pts[i]
                return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
        return pts[-1]
    out = []
    s = 4.0
    while s + 6 < L:
        e = min(L - 2, s + dash)
        a, b = at(s), at(e)
        al = int(225 + 30 * (rnd.random() if rnd is not None else 0.5))
        im, pos = capsule(a[0], a[1], b[0], b[1], w * (0.9 + 0.2 * (rnd.random() if rnd is not None else 0.5)), col, al)
        out.append((im, pos, e))
        s += dash + gap
    return out, L, at


# ─────────────────────────────── спрайты ───────────────────────────────
def island(w, h, seed, land=LAND):
    key = ('isl', w, h, seed, land)
    if key in _SPR:
        return _SPR[key]
    rnd = np.random.default_rng(seed)
    ss = 3
    S = (int(w * 1.4) + 20, int(h * 1.5) + 20)
    cx, cy = S[0] * ss / 2, S[1] * ss / 2
    ph = rnd.uniform(0, 6.3, 5)
    th = np.linspace(0, 2 * np.pi, 140, endpoint=False)
    r = (1 + 0.09 * np.sin(2 * th + ph[0]) + 0.07 * np.sin(3 * th + ph[1]) + 0.05 * np.sin(5 * th + ph[2])
         + 0.03 * np.sin(8 * th + ph[3]) + 0.02 * np.sin(13 * th + ph[4]))

    def poly(k):
        return [(cx + w / 2 * ss * k * rr * math.cos(a), cy + h / 2 * ss * k * rr * math.sin(a)) for rr, a in zip(r, th)]
    big = Image.new('RGBA', (S[0] * ss, S[1] * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    for k, al, wd in ((1.30, 70, 2), (1.15, 120, 2)):                  # береговые «волны»
        pts = poly(k)
        for i in range(0, len(pts), 2):
            d.line([pts[i], pts[(i + 1) % len(pts)]], fill=INK2 + (al,), width=wd * ss)
    mask = Image.new('L', big.size, 0)
    ImageDraw.Draw(mask).polygon(poly(1.0), fill=255)
    fill = Image.new('RGBA', big.size, land + (0,))
    fill.putalpha(mask.point(lambda v: int(v * 0.86)))
    big.alpha_composite(fill)
    # штриховка тени у берега (снизу-справа)
    sh = ImageChops.subtract(mask, ImageChops.offset(mask, -int(16 * ss / 3 * 2), -int(16 * ss / 3 * 2)))
    hat = Image.new('L', big.size, 0)
    dh = ImageDraw.Draw(hat)
    for x in range(-big.height, big.width, 9 * ss // 2 * 2):
        dh.line((x, big.height, x + big.height, 0), fill=150, width=ss + 1)
    hat = ImageChops.multiply(hat, sh)
    lay = Image.new('RGBA', big.size, INK2 + (0,))
    lay.putalpha(hat)
    big.alpha_composite(lay)
    d = ImageDraw.Draw(big)
    pts = poly(1.0)
    d.line(pts + [pts[0]], fill=INK + (255,), width=4 * ss, joint='curve')
    out = big.resize(S, Image.LANCZOS)
    _SPR[key] = out
    return out


def wax_seal(team, d, col):
    key = ('seal', team.name, d, col)
    if key in _SPR:
        return _SPR[key]
    ss = 3
    S = int(d * 1.2)
    N = S * ss
    c = N / 2
    R = d / 2 * ss
    rnd = np.random.default_rng(sum(map(ord, team.name)) % 1000)
    th = np.linspace(0, 2 * np.pi, 220, endpoint=False)
    ph = rnd.uniform(0, 6.3, 3)
    r = 1 + 0.03 * np.sin(5 * th + ph[0]) + 0.022 * np.sin(9 * th + ph[1]) + 0.015 * np.sin(14 * th + ph[2])
    for k in range(4):                                            # подтёки сургуча
        a0 = rnd.uniform(0, 2 * np.pi)
        dd = np.angle(np.exp(1j * (th - a0)))
        r = r + rnd.uniform(0.04, 0.08) * np.exp(-(dd / rnd.uniform(0.12, 0.22)) ** 2)
    mask = Image.new('L', (N, N), 0)
    ImageDraw.Draw(mask).polygon([(c + R * rr * math.cos(a), c + R * rr * math.sin(a)) for rr, a in zip(r, th)], fill=255)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    rr = np.hypot(xx - c, yy - c) / R
    lit = np.clip(1 - (((xx - c + 0.35 * R) ** 2 + (yy - c + 0.4 * R) ** 2) / (R * R * 2.2)), 0, 1)
    colf = np.array(col, np.float32)
    arr = colf * (0.6 + 0.6 * lit)[..., None]
    groove = np.exp(-((rr - 0.80) / 0.035) ** 2)
    ridge = np.exp(-((rr - 0.87) / 0.03) ** 2) * (0.5 + lit)
    arr = arr * (1 - 0.45 * groove)[..., None] + 70 * ridge[..., None]
    inner = np.array(C.mix(CREAM, col, 0.16), np.float32) * (0.9 + 0.12 * lit)[..., None]
    k = np.clip((0.775 - rr) / 0.012, 0, 1)[..., None]
    arr = arr * (1 - k) + inner * k
    out = np.concatenate([np.clip(arr, 0, 255), np.asarray(mask, np.float32)[..., None]], -1).astype(np.uint8)
    im = Image.fromarray(out, 'RGBA').resize((S, S), Image.LANCZOS)
    e = team.emb(int(d * 0.6))
    paste(im, e, S / 2, S / 2)
    sh = C.shadow(im, 10, 0.5)
    o = Image.new('RGBA', sh.size, (0, 0, 0, 0))
    o.alpha_composite(sh, (6, 10))
    o.alpha_composite(im, (30, 30))
    _SPR[key] = o
    return o


def stamp_chip(r, d=84):
    key = ('chip', r, d)
    if key in _SPR:
        return _SPR[key]
    col = WIN_INK if r == 'В' else LOSS_INK if r == 'П' else INK2
    ss = 3
    N = d * ss
    im = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    rnd = np.random.default_rng(ord(r[:1] or 'x'))
    th = np.linspace(0, 2 * np.pi, 90, endpoint=False)
    rr = N / 2 * (0.96 + 0.035 * np.sin(6 * th + rnd.uniform(0, 6)))
    dr.polygon([(N / 2 + a * math.cos(t), N / 2 + a * math.sin(t)) for a, t in zip(rr, th)], fill=col + (245,))
    dr.ellipse((N * 0.12, N * 0.12, N * 0.88, N * 0.88), outline=CREAM + (200,), width=2 * ss)
    im = im.resize((d, d), Image.LANCZOS)
    paste(im, C.text(r or '?', 'yes', int(d * 0.52), CREAM), d / 2, d / 2 + 1)
    im = im.rotate(-9, Image.BICUBIC, expand=True)
    _SPR[key] = im
    return im


def leather(s):
    key = ('leather', s)
    if key in _SPR:
        return _SPR[key]
    tx = C.text(s, 'yes', 34, CREAM, track=0.06)
    w, h = tx.width + 64, 60
    pl = C.rrect(w, h, 14, LEATHER, 238)
    ss = 3
    st = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(st)
    x0, y0, x1, y1 = 8 * ss, 8 * ss, (w - 8) * ss, (h - 8) * ss
    seg = 9 * ss
    for x in range(x0, x1, seg * 2):
        d.line((x, y0, min(x + seg, x1), y0), fill=(214, 182, 132, 200), width=2 * ss)
        d.line((x, y1, min(x + seg, x1), y1), fill=(214, 182, 132, 200), width=2 * ss)
    pl.alpha_composite(st.resize((w, h), Image.LANCZOS))
    paste(pl, tx, w / 2, h / 2)
    sh = C.shadow(pl, 8, 0.55)
    o = Image.new('RGBA', sh.size, (0, 0, 0, 0))
    o.alpha_composite(sh, (0, 6))
    o.alpha_composite(pl, (24, 24))
    _SPR[key] = o
    return o


def quill():
    if 'quill' in _SPR:
        return _SPR['quill']
    ss = 3
    w, h = 70, 250
    im = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = w * ss / 2
    # перо: лист вдоль стержня, кончик (нижний край) — пишущий
    left, right = [], []
    for i in range(41):
        t = i / 40
        y = (h - 30) * ss * (1 - t)
        wd = (math.sin(min(1.0, t * 1.15) * math.pi) ** 0.8) * w * ss * 0.46 * (0.25 + 0.75 * t ** 0.3) if t > 0.12 else 0
        left.append((cx - wd * 0.95, y))
        right.append((cx + wd * 0.7, y))
    d.polygon(left + right[::-1], fill=(238, 230, 214, 255))
    for i in range(6, 40, 2):                                       # бородки
        y = (h - 30) * ss * (1 - i / 40)
        d.line((cx, y, left[i][0] + 4, y - 14 * ss), fill=(180, 168, 150, 255), width=ss)
        d.line((cx, y, right[i][0] - 3, y - 12 * ss), fill=(190, 178, 160, 255), width=ss)
    d.line((cx, 0, cx, (h - 8) * ss), fill=(150, 130, 105, 255), width=2 * ss)
    d.polygon([(cx - 5 * ss, (h - 34) * ss), (cx + 5 * ss, (h - 34) * ss), (cx, h * ss)], fill=INK + (255,))
    im = im.resize((w, h), Image.LANCZOS)
    ang = -32
    rot = im.rotate(ang, Image.BICUBIC, expand=True)
    # где оказался кончик (w/2, h) после поворота вокруг центра
    vx, vy = 0, h / 2
    a = math.radians(-ang)
    tx, ty = vx * math.cos(a) - vy * math.sin(a), vx * math.sin(a) + vy * math.cos(a)
    tip = (rot.width / 2 + tx, rot.height / 2 + ty)
    sh = C.shadow(rot, 8, 0.35)
    o = Image.new('RGBA', sh.size, (0, 0, 0, 0))
    o.alpha_composite(sh, (18, 22))
    o.alpha_composite(rot, (24, 24))
    _SPR['quill'] = (o, (tip[0] + 24, tip[1] + 24))
    return _SPR['quill']


def needle(L):
    key = ('needle', L)
    if key in _SPR:
        return _SPR[key]
    ss = 3
    S = L + 20
    im = Image.new('RGBA', (S * ss, S * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S * ss / 2
    hl, hw = L / 2 * ss, L * 0.075 * ss
    d.polygon([(c, c - hl), (c + hw, c), (c - hw, c)], fill=RED + (255,))
    d.polygon([(c, c - hl), (c, c), (c - hw, c)], fill=C.mix(RED, (0, 0, 0), 0.3) + (255,))
    d.polygon([(c, c + hl), (c + hw, c), (c - hw, c)], fill=(60, 44, 30, 255))
    d.polygon([(c, c + hl), (c, c), (c + hw, c)], fill=(30, 20, 12, 255))
    r = L * 0.06 * ss
    d.ellipse((c - r, c - r, c + r, c + r), fill=(200, 160, 80, 255), outline=INK + (255,), width=ss)
    im = im.resize((S, S), Image.LANCZOS)
    _SPR[key] = im
    return im


def plate_odds(lab, val, w=292, h=222, seed=0):
    rnd = np.random.default_rng(40 + seed)
    ss = 2
    pts = []
    n = 18
    for i in range(n):
        pts.append((i / n * w, rnd.uniform(0, 7)))
    for i in range(n // 2):
        pts.append((w - rnd.uniform(0, 6), i / (n // 2) * h))
    for i in range(n):
        pts.append((w - i / n * w, h - rnd.uniform(0, 7)))
    for i in range(n // 2):
        pts.append((rnd.uniform(0, 6), h - i / (n // 2) * h))
    pad = 10
    big = Image.new('RGBA', ((w + 2 * pad) * ss, (h + 2 * pad) * ss), (0, 0, 0, 0))
    ImageDraw.Draw(big).polygon([((x + pad) * ss, (y + pad) * ss) for x, y in pts], fill=PAPER_L + (255,))
    im = big.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS)
    arr = np.asarray(im, np.float32).copy()
    yy, xx = np.mgrid[0:im.height, 0:im.width].astype(np.float32)
    nz = _nz(im.width, im.height, 30, 30, rnd)
    edge = np.minimum(np.minimum(xx - pad, w + pad - xx), np.minimum(yy - pad, h + pad - yy))
    k = (0.9 + 0.12 * nz) * (1 - 0.22 * np.clip(1 - edge / 26, 0, 1))
    arr[..., :3] *= k[..., None]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
    d = ImageDraw.Draw(im)
    d.rectangle((pad + 12, pad + 12, pad + w - 12, pad + h - 12), outline=INK2 + (200,), width=2)
    d.rectangle((pad + 18, pad + 18, pad + w - 18, pad + h - 18), outline=INK2 + (110,), width=1)
    paste(im, C.text(lab, 'yes', 50, INK2), im.width / 2, pad + 64)
    paste(im, C.text(val, 'yes', 104, INK, max_w=w - 40), im.width / 2, pad + 152)
    # гвоздик сверху
    pin = C.radial(26, 26, (150, 32, 24), 255, 0.6)
    paste(im, pin, im.width / 2, pad + 12)
    sh = C.shadow(im, 12, 0.45)
    o = Image.new('RGBA', sh.size, (0, 0, 0, 0))
    o.alpha_composite(sh, (6, 14))
    o.alpha_composite(im, (36, 36))
    return o


def star8(r, col=INK):
    ss = 3
    S = int(2 * r + 6)
    im = Image.new('RGBA', (S * ss, S * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S * ss / 2
    for k in range(8):
        a = k * math.pi / 4
        L = r * ss * (1 if k % 2 == 0 else 0.55)
        wd = r * ss * 0.2
        tip = (c + L * math.sin(a), c - L * math.cos(a))
        l1 = (c + wd * math.sin(a - math.pi / 2), c - wd * math.cos(a - math.pi / 2))
        l2 = (c + wd * math.sin(a + math.pi / 2), c - wd * math.cos(a + math.pi / 2))
        d.polygon([tip, l1, (c, c)], fill=tuple(col) + (255,))
        d.polygon([tip, l2, (c, c)], outline=tuple(col) + (255,), fill=PAPER_L + (255,), width=ss)
    return im.resize((S, S), Image.LANCZOS)


# ─────────────────────────────── лист карты ───────────────────────────────
def _serpent(d, x0, y0, L, Hh, flip=False, f=230, k=2):
    """Морской змей рисунком чернилами (координаты ×k)."""
    sg = -1 if flip else 1

    def P(x, y):
        return ((x0 + sg * x) * k, (y0 + y) * k)
    th = Hh * 0.30
    humps = [(0.32 * L, 0.12 * L, Hh * 0.95), (0.58 * L, 0.11 * L, Hh * 0.8), (0.82 * L, 0.09 * L, Hh * 0.62)]
    for xc, hw, hh in humps:
        outer = [P(xc - hw * math.cos(a), -hh * math.sin(a)) for a in np.linspace(0, math.pi, 22)]
        inner = [P(xc - (hw - th) * math.cos(a), -(hh - th) * math.sin(a)) for a in np.linspace(math.pi, 0, 22)]
        d.polygon(outer + inner, fill=30)
        d.line(outer, fill=f, width=3 * k)
        d.line(inner, fill=f, width=2 * k)
        for i in range(2, 21, 3):
            d.line([outer[i], inner[20 - i]], fill=140, width=k + 1)
        for j in (-1, 1):                                          # волны у воды
            xw = xc + j * (hw + 10)
            xa, xb = sorted((P(xw - 18, 0)[0], P(xw + 18, 0)[0]))
            d.arc((xa, (y0 - 8) * k, xb, (y0 + 8) * k), 0, 180, fill=f, width=2 * k)
    # шея и голова
    neck = bez((0.24 * L, 0), (0.17 * L, -Hh * 0.9), (0.06 * L, -Hh * 1.5), (0.0, -Hh * 1.25), 24)
    left = [P(x - th * 0.45, y) for x, y in neck]
    right = [P(x + th * 0.45, y + th * 0.1) for x, y in neck]
    d.polygon(left + right[::-1], fill=30)
    d.line(left, fill=f, width=3 * k)
    d.line(right, fill=f, width=2 * k)
    for i in range(3, 20, 4):                                      # гребень
        x, y = neck[i]
        d.polygon([P(x - th * 0.45, y), P(x - th * 1.0, y - 6), P(x - th * 0.45, y - 14)], fill=f)
    hx, hy = 0.0, -Hh * 1.25
    head = [P(hx + 0.02 * L, hy - Hh * 0.22), P(hx - 0.13 * L, hy - Hh * 0.12), P(hx - 0.15 * L, hy + Hh * 0.02),
            P(hx - 0.04 * L, hy + Hh * 0.06), P(hx - 0.13 * L, hy + Hh * 0.2), P(hx + 0.03 * L, hy + Hh * 0.18)]
    d.polygon(head, fill=30)
    d.line(head + [head[0]], fill=f, width=3 * k)
    ex, ey = P(hx - 0.02 * L, hy - Hh * 0.08)
    d.ellipse((ex - 4 * k, ey - 4 * k, ex + 4 * k, ey + 4 * k), fill=f)
    # хвост
    tx = 0.97 * L
    tail = [P(tx - 10, 0), P(tx + 18, -Hh * 0.55), P(tx + 46, -Hh * 0.8), P(tx + 24, -Hh * 0.35), P(tx + 6, 0)]
    d.polygon(tail, fill=60)
    d.line(tail + [tail[0]], fill=f, width=2 * k)


def _ship(d, x0, y0, s=1.0, f=220, k=2):
    def P(x, y):
        return ((x0 + x * s) * k, (y0 + y * s) * k)
    hull = [P(-120, -10), P(120, -10), P(95, 34), P(-90, 34)]
    d.polygon(hull, fill=40)
    d.line(hull + [hull[0]], fill=f, width=3 * k)
    for x in (-80, -40, 0, 40, 80):
        d.line([P(x, 0), P(x + 4, 24)], fill=150, width=k)
    for mx, top in ((-40, -190), (40, -165)):
        d.line([P(mx, -10), P(mx, top)], fill=f, width=3 * k)
        for y0_, y1_, wd in ((top + 20, top + 80, 52), (top + 90, -26, 66)):
            sail = [P(mx - wd, y0_), P(mx + wd, y0_), P(mx + wd * 0.92, y1_), P(mx, y1_ + 12), P(mx - wd * 0.92, y1_)]
            d.polygon(sail, fill=25)
            d.line(sail + [sail[0]], fill=f, width=2 * k)
        d.polygon([P(mx, top), P(mx + 34, top + 8), P(mx, top + 16)], fill=f)
    for i in range(-3, 4):
        xw = i * 46
        a, b = P(xw - 20, 30), P(xw + 20, 50)
        d.arc((a[0], a[1], b[0], b[1]), 200, 340, fill=f, width=2 * k)


def _tentacles(d, x0, y0, s=1.0, f=220, k=2):
    for j, (dx, hgt, curl) in enumerate(((-90, 210, 1), (0, 260, -1), (95, 190, 1))):
        pts = bez((dx, 0), (dx + curl * 30, -hgt * 0.5), (dx - curl * 60, -hgt * 0.95), (dx - curl * 10, -hgt), 30)
        n = len(pts)
        left, right = [], []
        for i, (x, y) in enumerate(pts):
            w = 22 * (1 - i / n) + 3
            left.append(((x0 + (x - w) * s) * k, (y0 + y * s) * k))
            right.append(((x0 + (x + w) * s) * k, (y0 + y * s) * k))
        d.polygon(left + right[::-1], fill=35)
        d.line(left, fill=f, width=3 * k)
        d.line(right, fill=f, width=2 * k)
        for i in range(2, n - 6, 4):
            x, y = right[i]
            r = (7 * (1 - i / n) + 2) * k * s
            d.ellipse((x - r * 2.2, y - r, x - r * 0.2, y + r), outline=f, width=k)
    for i in range(-4, 5):
        a = ((x0 + (i * 44 - 20) * s) * k, (y0 - 6) * k)
        b = ((x0 + (i * 44 + 20) * s) * k, (y0 + 12) * k)
        d.arc((a[0], a[1], b[0], b[1]), 200, 340, fill=f, width=2 * k)


def _rose(d, cx, cy, r, f=230, k=2, letters=True, red=None):
    """Роза ветров: 16 лучей (тёмная и светлая половины), кольца с рисками, буквы С В Ю З; север — красным."""
    X, Y = cx * k, cy * k
    for rad, wd in ((r * 1.08, 3), (r * 1.16, 2)):
        d.ellipse((X - rad * k, Y - rad * k, X + rad * k, Y + rad * k), outline=f, width=wd * k)
    for deg in range(0, 360, 5):
        a = math.radians(deg)
        L = 14 if deg % 45 == 0 else 8 if deg % 15 == 0 else 5
        r0 = r * 1.08
        d.line((X + r0 * k * math.sin(a), Y - r0 * k * math.cos(a), X + (r0 + L) * k * math.sin(a),
                Y - (r0 + L) * k * math.cos(a)), fill=f, width=k)
    tiers = [(22.5 + 45 * i, 0.42, 0.07) for i in range(8)] + [(45 + 90 * i, 0.68, 0.11) for i in range(4)] + \
            [(90 * i, 1.0, 0.15) for i in range(4)]
    for deg, Lk, wk in tiers:
        a = math.radians(deg)
        L, wd = r * Lk * k, r * wk * k
        tip = (X + L * math.sin(a), Y - L * math.cos(a))
        l1 = (X + wd * math.sin(a - math.pi / 2), Y - wd * math.cos(a - math.pi / 2))
        l2 = (X + wd * math.sin(a + math.pi / 2), Y - wd * math.cos(a + math.pi / 2))
        d.polygon([tip, l2, (X, Y)], fill=16)
        d.line([tip, l2, (X, Y)], fill=f, width=k)
        d.polygon([tip, l1, (X, Y)], fill=f)
    if red is not None:
        L, wd = r * k, r * 0.15 * k
        red.polygon([(X, Y - L), (X - wd, Y), (X, Y)], fill=230)
    d.ellipse((X - r * 0.08 * k, Y - r * 0.08 * k, X + r * 0.08 * k, Y + r * 0.08 * k), fill=16, outline=f, width=2 * k)
    if letters:
        fnt = C.font('yes', int(r * 0.24 * k))
        for s, deg in (('С', 0), ('В', 90), ('Ю', 180), ('З', 270)):
            a = math.radians(deg)
            rr = r * 1.36 * k
            d.text((X + rr * math.sin(a), Y - rr * math.cos(a)), s, fill=f, font=fnt, anchor='mm')


def canvas(seed=11):
    """Лист карты на столе (RGB, PW+2M × PH+2M), с декором: рамка-шкала, румбы, розы ветров, чудища, корабль, волны."""
    key = ('canvas', seed)
    if key in _BAKE:
        return _BAKE[key]
    rnd = np.random.default_rng(seed)
    CW_, CH_ = PW + 2 * M, PH + 2 * M
    n1 = _nz(CW_, CH_, 520, 520, rnd)
    n2 = _nz(CW_, CH_, 150, 150, rnd)
    n3 = _nz(CW_, CH_, 34, 34, rnd)
    fb = 0.5 * n1 + 0.32 * n2 + 0.18 * n3
    paper = np.empty((CH_, CW_, 3), np.float32)
    pk = 0.86 + 0.28 * fb
    for i in range(3):
        paper[..., i] = PAPER[i] * pk
    fine = rnd.normal(0, 1, (CH_ // 2 + 1, CW_ // 2 + 1)).astype(np.float32).repeat(2, 0).repeat(2, 1)[:CH_, :CW_]
    paper += (fine * 3.2)[..., None]
    st = _nz(CW_, CH_, 760, 760, rnd)
    stain = np.clip((st - 0.6) / 0.22, 0, 1) ** 1.6 * 0.13
    paper *= (1 - stain)[..., None]
    paper[..., 2] *= (1 - stain * 0.6)
    xs = np.arange(CW_, dtype=np.float32) - M
    ys = np.arange(CH_, dtype=np.float32) - M
    dx = np.minimum(xs, PW - 1 - xs)
    dy = np.minimum(ys, PH - 1 - ys)
    dist = np.minimum(dx[None, :], dy[:, None]) + (n2 - 0.5) * 64 + (n3 - 0.5) * 22
    alpha = np.clip(dist / 2.0, 0, 1)
    ke = np.clip(1 - dist / 190, 0, 1) ** 2 * 0.5
    kb = np.clip(1 - dist / 34, 0, 1) ** 1.3
    for i, (ce, cb) in enumerate(zip((150, 98, 48), (38, 18, 8))):
        paper[..., i] = paper[..., i] * (1 - ke) + ce * ke
        paper[..., i] = paper[..., i] * (1 - kb) + cb * kb
    tg = _nz(CW_, CH_, 12, 900, rnd)
    tk = (0.7 + 0.55 * tg + 0.25 * (n1 - 0.5))
    shd = np.clip(1 + dist / 110, 0, 1) * (dist < 0)
    tk *= (1 - 0.6 * shd)
    out = np.empty_like(paper)
    for i, c in enumerate((44, 27, 16)):
        out[..., i] = c * tk * (1 - alpha) + paper[..., i] * alpha
    del paper, n1, n2, n3, fb, fine, st, stain, tg, tk, shd
    # декор чернилами (×2 со сглаживанием)
    k = 2
    ink = Image.new('L', (PW * k, PH * k), 0)
    red = Image.new('L', (PW * k, PH * k), 0)
    d, dr = ImageDraw.Draw(ink), ImageDraw.Draw(red)
    roses = [(CMP, CMP_R), ((330.0, 520.0), 92), ((1830.0, 520.0), 92)]
    for (cx, cy), r in roses:                                         # румбовые линии
        n = 32 if r > 100 else 16
        for i in range(n):
            a = 2 * math.pi * i / n
            L = 5000
            d.line((cx * k, cy * k, (cx + L * math.sin(a)) * k, (cy - L * math.cos(a)) * k), fill=34 if r > 100 else 26, width=2 * k)
    # рамка-шкала
    for ins, wd in ((56, 4), (88, 2)):
        d.rectangle((ins * k, ins * k, (PW - ins) * k, (PH - ins) * k), outline=225, width=wd * k)
    step = 110
    for side in range(4):
        L = PW if side % 2 == 0 else PH
        for i, s in enumerate(range(100, L - 100, step)):
            if i % 2:
                continue
            if side == 0:
                box = (s, 64, s + step, 80)
            elif side == 2:
                box = (s, PH - 80, s + step, PH - 64)
            elif side == 1:
                box = (PW - 80, s, PW - 64, s + step)
            else:
                box = (64, s, 80, s + step)
            d.rectangle(tuple(v * k for v in box), fill=150)
    _rose(d, CMP[0], CMP[1], CMP_R, red=dr)
    _rose(d, 330, 520, 92, red=dr)
    _rose(d, 1830, 520, 92, red=dr)
    _serpent(d, 1080 - 250, 1388, 500, 92)
    _ship(d, 400, 1040, 1.05)
    _serpent(d, 1990, 1000, 380, 80, flip=True)
    _tentacles(d, 420, 3260, 1.0)
    _serpent(d, 1520, 3260, 420, 84)
    # волны «~» по свободному морю
    busy = [(520, 230, 1640, 1440), (90, 1520, 2070, 2700), (820, 2740, 1340, 3250), (240, 330, 430, 640),
            (1730, 330, 1930, 640), (250, 820, 560, 1110), (1560, 860, 2020, 1030), (300, 3020, 560, 3290),
            (1500, 3150, 1990, 3290)]
    wr = np.random.default_rng(seed + 5)
    placed = 0
    for _ in range(900):
        x, y = wr.uniform(130, PW - 130), wr.uniform(130, PH - 130)
        if any(a - 30 < x < c + 30 and b - 30 < y < e + 30 for a, b, c, e in busy):
            continue
        for j in range(3):
            xx = x + j * 30
            d.arc(((xx - 16) * k, (y - 8) * k, (xx + 16) * k, (y + 8) * k), 200, 340, fill=150, width=2 * k)
        placed += 1
        if placed > 70:
            break
    ink = ink.reduce(k)
    red = red.reduce(k)
    ia = np.asarray(ink, np.float32) / 255 * 0.9
    ra = np.asarray(red, np.float32) / 255 * 0.85
    reg = out[M:M + PH, M:M + PW]
    pa = alpha[M:M + PH, M:M + PW]
    ia *= pa
    ra *= pa
    for i in range(3):
        reg[..., i] = reg[..., i] * (1 - ia) + INK[i] * ia
        reg[..., i] = reg[..., i] * (1 - ra) + RED[i] * ra
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')
    _BAKE[key] = im
    return im


# ─────────────────────────────── ролик ───────────────────────────────
class Treasure(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 67, drop=19 * 60 / 67, line=None, team=7, pre=2,
                 hold=5, cta=2.5, dip=(-1.47, -0.69), kick=-0.45, seed=11, **kw):
        """Сцены: интро → страница хозяев (team долей) → страница гостей → вся карта (pre) → клад на дропе (hold) →
        Telegram (cta). dip — провал трека (с от дропа: тишина, возврат звука), kick — подхват перед дропом."""
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
        if self.t1 < 1.5:
            raise ValueError('мало времени до дропа')
        self.t_cta = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = min(2.0, self.t1 - 0.4)
        D = self.drop
        self.dip0, self.dip1 = D + dip[0], D + dip[1]
        self.kick = D + kick
        self.dive0 = max(self.tp + 0.6, self.dip1)
        self.conv0, self.conv1 = self.tp + 0.32 * u, self.dive0 - 0.06
        self.key = (home, away, league, when, pick, coef, tuple(line or ()), seed, round(u, 5),
                    tuple(sorted((k, str(v)) for k, v in self.raw['h'].items())),
                    tuple(sorted((k, str(v)) for k, v in self.raw['a'].items())))
        self._prep()

    # ── заготовки ──
    def _prep(self):
        u = self.u
        self.tag_im = leather(F.tag(self.league))
        self.handle_im = leather(C.HANDLE)
        self.tg = C.tg_plate(960, 172, font='mont')
        self.wax = {'h': wax_col(self.h), 'a': wax_col(self.a)}
        self.intro_items = self._intro_items()
        self.pages = {s: self._page(s, t0) for s, t0 in (('h', self.t1), ('a', self.t2))}
        self.conv = {s: self._conv(s) for s in ('h', 'a')}
        self.qu = quill()
        if self.key in _BAKE:
            self.B = _BAKE[self.key]
        else:
            self.B = self._bake()
            _BAKE[self.key] = self.B
        self._pick_prep()
        # свет свечи: тёплая виньетка (H, W, 3)
        if 'light' not in _SPR:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            dd = np.sqrt(((xx - 540) / 760) ** 2 + ((yy - 860) / 1150) ** 2)
            L = 1 - 0.5 * np.clip(dd, 0, 1.25) ** 2.1
            L = np.clip(L, 0.2, 1)
            _SPR['light'] = np.stack([L ** 0.75 * 1.04, L ** 0.95, L ** 1.3 * 0.94], -1).astype(np.float32)
        self.light = _SPR['light']
        C.grain(Image.new('RGB', (W, H)), 0, 5)                 # зерно — до fork

    def _intro_items(self):
        """Картуш и линия — элементы в координатах мира (экран интро + 540 по x) с временем появления."""
        u = self.u
        ox = 540
        it = []
        cart = self._cartouche()
        it.append(dict(im=cart, pos=(ox + 540, 604), t=0.0, kind='unroll'))
        for s, x, t0 in (('h', 296, 0.12), ('a', 784, 0.24)):
            tm = self.h if s == 'h' else self.a
            e = tm.emb(212)
            it.append(dict(im=C.with_shadow(e, 10, 0.35, 8), pos=(ox + x, 498), t=t0, kind='pop'))
            it.append(dict(im=C.text(tm.up, 'yes', 54, INK, max_w=350), pos=(ox + x, 658), t=t0 + 0.12, kind='wipe'))
            it.append(dict(im=C.text('хозяева' if s == 'h' else 'гости', 'hand', 48, INK2, 700), pos=(ox + x, 712),
                           t=t0 + 0.2, kind='wipe'))
        it.append(dict(im=star8(40), pos=(ox + 540, 498), t=0.3, kind='pop'))
        it.append(dict(im=C.text('%s · %s' % (F.lg_ru(self.league), self.when), 'yes', 50, INK, max_w=820),
                       pos=(ox + 540, 806), t=0.36, kind='wipe'))
        if self.line:
            it.append(dict(im=C.text('основное время', 'hand', 54, INK2, 700), pos=(ox + 540, 968), t=0.4, kind='wipe'))
            for i, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), self.line)):
                pl = plate_odds(lab, C.fmt_k(v), seed=i)
                pl = pl.rotate((-2.2, 1.2, 2.4)[i], Image.BICUBIC, expand=True)
                it.append(dict(im=pl, pos=(ox + 215 + 325 * i, 1130), t=(0.5 + 0.25 * i) * u, kind='stamp'))
        return it

    def _cartouche(self):
        w, h = 948, 610
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        rnd = np.random.default_rng(3)
        body = np.zeros((h - 70, w - 40, 4), np.float32)
        nz = _nz(w - 40, h - 70, 60, 60, rnd)
        for i in range(3):
            body[..., i] = PAPER_L[i] * (0.93 + 0.1 * nz)
        body[..., 3] = 250
        b = Image.fromarray(body.astype(np.uint8), 'RGBA')
        d = ImageDraw.Draw(b)
        bw, bh = b.size
        for ins, wd, al in ((14, 3, 230), (24, 1, 170)):
            d.rectangle((ins, ins, bw - ins, bh - ins), outline=INK + (al,), width=wd)
        for (x, y) in ((24, 24), (bw - 24, 24), (24, bh - 24), (bw - 24, bh - 24)):
            d.ellipse((x - 9, y - 9, x + 9, y + 9), outline=INK + (220,), width=2)
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=RED + (230,))
        # завиток-разделитель над строкой даты
        yy = bh - 150
        d.line((150, yy, bw / 2 - 30, yy), fill=INK2 + (190,), width=2)
        d.line((bw / 2 + 30, yy, bw - 150, yy), fill=INK2 + (190,), width=2)
        d.polygon([(bw / 2 - 18, yy), (bw / 2, yy - 9), (bw / 2 + 18, yy), (bw / 2, yy + 9)], fill=RED + (230,))
        im.alpha_composite(b, (20, 35))
        # свёрнутые края свитка сверху и снизу
        for y0 in (8, h - 58):
            ry = np.linspace(0, 1, 50)[:, None]
            shade = 0.62 + 0.5 * np.sin(ry * math.pi) ** 0.7
            roll = np.zeros((50, w, 4), np.float32)
            for i in range(3):
                roll[..., i] = PAPER[i] * shade * np.ones((1, w))
            roll[..., 3] = 255
            r = Image.fromarray(np.clip(roll, 0, 255).astype(np.uint8), 'RGBA')
            m = C.rrect(w, 50, 25, (255, 255, 255)).getchannel('A')
            r.putalpha(m)
            dd = ImageDraw.Draw(r)
            dd.rounded_rectangle((0, 0, w - 1, 49), radius=25, outline=INK + (200,), width=2)
            for x in (26, w - 26):
                dd.ellipse((x - 14, 11, x + 14, 39), outline=INK2 + (200,), width=2)
                dd.ellipse((x - 6, 19, x + 6, 31), outline=INK2 + (160,), width=2)
            im.alpha_composite(r, (0, y0))
        sh = C.shadow(im, 16, 0.4)
        o = Image.new('RGBA', sh.size, (0, 0, 0, 0))
        o.alpha_composite(sh, (6, 16))
        o.alpha_composite(im, (48, 48))
        return o

    # страница клуба
    def _w(self, side, x, y):
        return (x + 40.0, y + PAGE_Y) if side == 'h' else (2120.0 - x, y + PAGE_Y)

    def _tl(self, side, im, x, y, align):
        """Левый верх текста в мире: якорь (x, y) — левый (align='l') или правый край строки, y — центр."""
        wx, wy = self._w(side, x, y)
        al = align if side == 'h' else ('r' if align == 'l' else 'l')
        left = wx if al == 'l' else wx - im.width
        return (left, wy - im.height / 2)

    def _page(self, side, t0):
        u = self.u
        tm = self.h if side == 'h' else self.a
        s = self.st[side]
        rec = self.raw[side]
        rnd = np.random.default_rng(77 if side == 'h' else 91)
        items = []
        # печать и название
        seal = wax_seal(tm, SEAL_D, self.wax[side])
        ts = t0 + 0.5 * u
        items.append(dict(im=seal, c=self._w(side, *SEAL), t=ts, kind='seal'))
        nm = C.text(tm.up, 'yes', 80, INK, max_w=1020 - NAME_X)
        items.append(dict(im=nm, tl=self._tl(side, nm, NAME_X, 362, 'l'), t=ts + 0.06, kind='wipe'))
        sub = 'хозяева' if side == 'h' else 'гости'
        m = re.match(r'\s*(ОТ|В|П)\s*(\d+)', str(rec.get('streak') or ''))
        if m and int(m.group(2)) >= 2:
            n = int(m.group(2))
            word = {'В': plural(n, 'победа', 'победы', 'побед'), 'П': plural(n, 'поражение', 'поражения', 'поражений'),
                    'ОТ': plural(n, 'поражение', 'поражения', 'поражений') + ' в ОТ'}[m.group(1)]
            sub += ' · %d %s подряд' % (n, word)
        sb = C.text(sub, 'hand', 54, INK2, 700, max_w=1020 - NAME_X)
        items.append(dict(im=sb, tl=self._tl(side, sb, NAME_X + 4, 440, 'l'), t=ts + 0.2, kind='wipe'))
        facts = []
        for i, g in enumerate(s['games'][:3]):
            facts.append(('g', g, G_NODES[i]))
        stats = []
        if s['points'] is not None:
            cap2 = ('за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей'))) if s['gp'] is not None else ''
            stats.append(('%d' % s['points'], plural(s['points'], 'очко', 'очка', 'очков'), cap2, INK))
        if s['place'] is not None:
            stats.append(('%d' % s['place'], 'место', s['place_scope'] or '', INK))
        if s['gd'] is not None:
            stats.append((gd_str(s['gd']), 'разница', 'шайб', WIN_INK if s['gd'] > 0 else LOSS_INK if s['gd'] < 0 else INK))
        # архипелаг показателей центрируем, если их меньше трёх
        kx = {3: [0, 1, 2], 2: [0, 2], 1: [1]}.get(len(stats), [])
        for j, st in enumerate(stats):
            facts.append(('k', st, K_NODES[kx[j]]))
        # маршрут: от печати — по островам
        prev = (SEAL[0], SEAL[1] + SEAL_D / 2 + 4)
        prev_kind = 'seal'
        segs = []
        for j, (kind, data, node) in enumerate(facts):
            ta = t0 + (1.0 + 0.5 * j) * u
            pts = self._route(prev, prev_kind, node, kind)
            wpts = [self._w(side, x, y) for x, y in pts]
            ds, L, at = dashes(wpts, INK, rnd=rnd)
            segs.append(dict(ds=ds, L=L, at=at, t0=ta - 0.42 * u, t1=ta - 0.02))
            items += self._fact(side, kind, data, node, ta, j)
            prev, prev_kind = node, kind
        return dict(items=items, segs=segs, t0=t0, last=(prev, prev_kind))

    def _route(self, a, ak, b, bk):
        """Кривая между островами (в координатах страницы хозяев)."""
        ax, ay = a
        bx, by = b
        if ak == 'seal':
            return bez((ax, ay), (ax - 30, ay + 20), (bx + 30, by - 80), (bx, by - G_ISL[1] / 2 - 8))
        if ak == 'g' and bk == 'g':
            if bx > ax:
                p0, p3 = (ax + 84, ay + 36), (bx - 84, by - 34)
                return bez(p0, (p0[0] + 200, p0[1] + 92), (p3[0] - 200, p3[1] - 70), p3)
            p0, p3 = (ax - 84, ay + 36), (bx + 84, by - 34)
            return bez(p0, (p0[0] - 200, p0[1] + 92), (p3[0] + 200, p3[1] - 70), p3)
        if ak == 'g' and bk == 'k':
            p0, p3 = (ax + (10 if ax < 540 else -10), ay + G_ISL[1] / 2 + 6), (bx, by - K_ISL[1] / 2 - 10)
            if abs(p0[0] - p3[0]) < 60:
                return bez(p0, (p0[0] - 40, p0[1] + 30), (p3[0] + 40, p3[1] - 30), p3)
            return bez(p0, (p0[0], p0[1] + 90), (p3[0], p3[1] - 90), p3)
        # k → k: дуга над проливом
        sg = 1 if bx > ax else -1
        p0, p3 = (ax + sg * (K_ISL[0] / 2 - 18), ay - 40), (bx - sg * (K_ISL[0] / 2 - 18), by - 40)
        return bez(p0, (p0[0] + sg * 30, p0[1] - 60), (p3[0] - sg * 30, p3[1] - 60), p3)

    def _fact(self, side, kind, data, node, ta, j):
        out = []
        wc = self._w(side, *node)
        if kind == 'g':
            g = data
            isl = island(G_ISL[0], G_ISL[1], 300 + j * 7 + (0 if side == 'h' else 50))
            out.append(dict(im=isl, c=wc, t=ta, kind='island'))
            out.append(dict(im=stamp_chip(g['res'] or '?'), c=wc, t=ta + 0.07, kind='stamp'))
            # строка: соперник, счёт, ОТ/Б
            col = WIN_INK if g['res'] == 'В' else LOSS_INK if g['res'] == 'П' else INK
            sc = C.text(g['score'], 'yes', 76, col)
            nt = C.text(g['note'], 'hand', 54, INK2, 700) if g['note'] else None
            room = 700 - sc.width - 26 - (nt.width + 14 if nt else 0)
            op = C.text(g['opp'].upper(), 'yes', 56, INK, max_w=max(200, room))
            wd = op.width + 26 + sc.width + (14 + nt.width if nt else 0)
            hh = max(op.height, sc.height)
            row = Image.new('RGBA', (wd, hh + 10), (0, 0, 0, 0))
            base = hh + 4
            row.alpha_composite(op, (0, base - op.height))
            row.alpha_composite(sc, (op.width + 26, base - sc.height))
            if nt:
                row.alpha_composite(nt, (op.width + 26 + sc.width + 14, base - nt.height - 2))
            left = node[0] < 540
            ax = node[0] + (G_ISL[0] / 2 + 22 if left else -(G_ISL[0] / 2 + 22))
            out.append(dict(im=row, tl=self._tl(side, row, ax, node[1] - 22, 'l' if left else 'r'), t=ta + 0.04, kind='wipe'))
            where = 'дома' if g['home'] is True else 'в гостях' if g['home'] is False else ''
            l2 = ' · '.join(x for x in (g['date'], where) if x)
            if l2:
                tx = C.text(l2, 'hand', 48, INK2, 700)
                out.append(dict(im=tx, tl=self._tl(side, tx, ax + (4 if left else -4), node[1] + 42, 'l' if left else 'r'),
                                t=ta + 0.12, kind='wipe'))
        else:
            val, c1, c2, vcol = data
            isl = island(K_ISL[0], K_ISL[1], 500 + j * 11 + (0 if side == 'h' else 60), land=(220, 205, 156))
            out.append(dict(im=isl, c=wc, t=ta, kind='island'))
            out.append(dict(im=C.text(val, 'yes', 100, vcol, max_w=K_ISL[0] - 40), c=(wc[0], wc[1] + 2), t=ta + 0.05, kind='stamp'))
            cap = Image.new('RGBA', (340, 104), (0, 0, 0, 0))
            t1 = C.text(c1, 'hand', 52, INK, 700, max_w=330)
            paste(cap, t1, 170, 26)
            if c2:
                paste(cap, C.text(c2, 'hand', 46, INK2, 700, max_w=330), 170, 76)
            out.append(dict(im=cap, c=(wc[0], wc[1] + K_ISL[1] / 2 + 62), t=ta + 0.1, kind='wipe_c'))
        return out

    def _conv(self, side):
        prev, _ = self.pages[side]['last']
        x, y = prev
        cx = CMP[0] - 40.0                                   # центр розы в координатах страницы хозяев
        cy = CMP[1] - PAGE_Y
        if x > 540:
            p0 = (x + K_ISL[0] / 2 - 30, y + 20)
            pts = bez(p0, (p0[0] + 60, p0[1] + 160), (cx + 30, cy - 330), (cx, cy - 26))
        else:
            p0 = (x, y + K_ISL[1] / 2 + 110)
            pts = bez(p0, (p0[0] + 40, p0[1] + 220), (cx - 220, cy - 120), (cx - 18, cy - 18))
        wpts = [self._w(side, a, b) for a, b in pts]
        ds, L, at = dashes(wpts, RED, w=8, dash=22, gap=13, rnd=np.random.default_rng(5))
        return dict(ds=ds, L=L, at=at, pts=wpts)

    # ── запекание слоёв мира ──
    def _bake(self):
        base = canvas(self.seed)
        B = {'base': base}
        im = base.copy()
        for it in self.intro_items:
            paste(im, it['im'], it['pos'][0] + M, it['pos'][1] + M)
        B['intro'] = im
        for side, key in (('h', 'p1'), ('a', 'full')):
            im = im.copy()
            self._draw_page(im, side, 1e9, -M, -M)
            B[key] = im
        im = im.copy()
        for side in ('h', 'a'):
            for sp, (x, y), e in self.conv[side]['ds']:
                paste(im, sp, x + M, y + M, anchor='tl')
        B['conv'] = im
        # обзор целиком — из уменьшенных вдвое слоёв с запасом стола по краям (окно обзора шире листа)
        B['half_full'] = ImageOps.expand(B['full'].reduce(2), border=HPAD, fill=(30, 18, 10))
        B['half_conv'] = ImageOps.expand(B['conv'].reduce(2), border=HPAD, fill=(30, 18, 10))
        return B

    # ── камера ──
    def cam_page(self, side, t, t0):
        u = self.u
        cx, cy = PAGE_C[side]
        p = C.in_out(C.seg(t, t0 + 0.5 * u, t0 + 4.2 * u))
        return (cx, cy - 64 * (1 - p), 1.05 - 0.05 * p)

    def cam(self, t):
        u = self.u
        if t < self.t1:
            return (INTRO_C[0], INTRO_C[1] - 6, 1.0 + 0.018 * C.seg(t, 0.9, self.t1))
        if t < self.t2:
            a = (INTRO_C[0], INTRO_C[1] - 6, 1.018)
            b = self.cam_page('h', t, self.t1)
            k = C.out_cubic(C.seg(t, self.t1, self.t1 + 0.44))
            return self._lerp_cam(a, b, k)
        if t < self.tp:
            a = self.cam_page('h', t, self.t1)
            b = self.cam_page('a', t, self.t2)
            k = C.out_cubic(C.seg(t, self.t2, self.t2 + 0.44))
            return self._lerp_cam(a, b, k)
        ov = (OV_C[0], OV_C[1], S_OV)
        if t < self.dive0:
            a = self.cam_page('a', t, self.t2)
            k = C.in_out(C.seg(t, self.tp, self.tp + 0.55 * u))
            z = 1 + 0.03 * C.seg(t, self.tp + 0.55 * u, self.dive0)               # медленный наезд в провале
            return self._lerp_cam(a, (ov[0], ov[1], ov[2] * z), k)
        # нырок к кладу: X идёт в (540, X_Y), масштаб растёт до S_PICK
        z0 = S_OV * (1 + 0.03 * C.seg(self.dive0, self.tp + 0.55 * u, self.dive0))
        q1 = C.out_cubic(C.seg(t, self.dive0, self.kick))
        q2 = C.in_cubic(C.seg(t, self.kick, self.drop))
        k = 0.35 * q1 + 0.65 * q2
        s = math.exp(C.lerp(math.log(z0), math.log(S_PICK), k))
        py0 = 960 + (CMP[1] - ov[1]) * z0
        py = C.lerp(py0, X_Y, k)
        return (CMP[0], CMP[1] - (py - 960) / s, s)

    @staticmethod
    def _lerp_cam(a, b, k):
        s = math.exp(C.lerp(math.log(a[2]), math.log(b[2]), k))
        return (C.lerp(a[0], b[0], k), C.lerp(a[1], b[1], k), s)

    def layer(self, t):
        """Какой запечённый слой мира под кадром (всё, что на нём, уже появилось)."""
        if t < 1.25 * self.u + 0.45:
            return 'base'
        if t < self.t2:
            return 'intro'
        if t < self.tp:
            return 'p1'
        if t < self.conv1:
            return 'full'
        return 'conv'

    # ── отрисовка элементов мира ──
    def _draw_intro(self, im, t, ox, oy):
        for it in self.intro_items:
            q = t - it['t']
            if q < 0:
                continue
            x, y = it['pos'][0] - ox, it['pos'][1] - oy
            img = it['im']
            kd = it['kind']
            if kd == 'unroll':
                k = C.out_cubic(C.seg(q, 0, 0.34))
                hh = max(2, int(img.height * (0.12 + 0.88 * k)))
                crop = img.crop((0, (img.height - hh) // 2, img.width, (img.height - hh) // 2 + hh))
                paste(im, crop, x, y, min(1.0, k * 3))
            elif kd == 'pop':
                k = C.out_back(C.seg(q, 0, 0.32), 1.7)
                if k > 0.02:
                    paste(im, C.scale(img, max(0.05, k)), x, y, min(1.0, k * 2))
            elif kd == 'stamp':
                k = C.seg(q, 0, 0.12)
                if k > 0:
                    sc = 1 + 0.35 * (1 - C.out_cubic(k)) ** 1.5 - 0.03 * math.exp(-max(0.0, q - 0.12) / 0.06) * (q > 0.12)
                    paste(im, C.scale(img, sc), x, y, min(1.0, k * 2.5))
            else:
                self._wipe(im, img, x - img.width / 2, y - img.height / 2, q, 0.26)

    def _wipe(self, im, img, left, top, q, d=0.28):
        k = C.out_cubic(C.seg(q, 0, d))
        if k <= 0.01:
            return
        if k >= 0.999:
            paste(im, img, left, top, anchor='tl')
            return
        w = max(1, int(img.width * k))
        part = img.crop((0, 0, w, img.height))
        # мягкий край «чернила ещё сохнут»
        fe = min(40, w)
        if fe > 2:
            a = np.asarray(part.getchannel('A'), np.float32)
            a[:, -fe:] *= np.linspace(1, 0.15, fe)[None, :]
            part.putalpha(Image.fromarray(a.astype(np.uint8), 'L'))
        paste(im, part, left, top, anchor='tl')

    def _draw_page(self, im, side, t, ox, oy):
        P = self.pages[side]
        for sg in P['segs']:
            if t < sg['t0']:
                continue
            L = sg['L'] * C.seg(t, sg['t0'], sg['t1'])
            for sp, (x, y), e in sg['ds']:
                if e <= L + 0.5:
                    paste(im, sp, x - ox, y - oy, anchor='tl')
        for it in P['items']:
            q = t - it['t']
            if q < 0:
                continue
            img = it['im']
            kd = it['kind']
            if kd in ('wipe', 'wipe_c'):
                if 'tl' in it:
                    l, tp = it['tl']
                else:
                    l, tp = it['c'][0] - img.width / 2, it['c'][1] - img.height / 2
                self._wipe(im, img, l - ox, tp - oy, q, 0.28)
                continue
            x, y = it['c'][0] - ox, it['c'][1] - oy
            if kd == 'seal':
                k = C.seg(q, 0, 0.14)
                sc = 1 + 0.55 * (1 - C.out_cubic(k)) ** 1.4
                if q > 0.14:
                    sc = 1 - 0.04 * math.exp(-(q - 0.14) / 0.07)
                paste(im, C.scale(img, sc) if abs(sc - 1) > 0.003 else img, x, y, min(1.0, k * 3))
            elif kd == 'island':
                k = C.out_back(C.seg(q, 0, 0.3), 1.5)
                if k > 0.02:
                    paste(im, C.scale(img, 0.55 + 0.45 * k) if k < 0.999 else img, x, y, min(1.0, k * 2.2))
            elif kd == 'stamp':
                k = C.seg(q, 0, 0.1)
                if k > 0:
                    sc = 1 + 0.6 * (1 - C.out_cubic(k)) ** 1.5
                    paste(im, C.scale(img, sc) if sc > 1.003 else img, x, y, min(1.0, k * 2.5))

    def _quill(self, im, t, side, ox, oy):
        P = self.pages[side]
        segs = P['segs']
        if not segs or t < segs[0]['t0'] - 0.15 or t > segs[-1]['t1'] + 0.35:
            return
        head = None
        for sg in segs:
            if t >= sg['t0']:
                head = sg['at'](sg['L'] * C.seg(t, sg['t0'], sg['t1']))
        if head is None:
            head = segs[0]['at'](0)
        a = min(C.seg(t, segs[0]['t0'] - 0.15, segs[0]['t0']), 1 - C.seg(t, segs[-1]['t1'] + 0.1, segs[-1]['t1'] + 0.35))
        img, tip = self.qu
        paste(im, img, head[0] - ox - tip[0], head[1] - oy - tip[1], a, anchor='tl')

    def _draw_conv_screen(self, fr, t, cam):
        """Сходящиеся пути на обзоре (экранные координаты, кружки-штрихи)."""
        cx, cy, s = cam
        d = ImageDraw.Draw(fr)
        wd = max(2.0, 8 * s)
        for side in ('h', 'a'):
            cv = self.conv[side]
            L = cv['L'] * C.seg(t, self.conv0, self.conv1)
            for sp, (x, y), e in cv['ds']:
                if e > L + 0.5:
                    break
                bx, by = x + sp.width / 2, y + sp.height / 2
                X, Y = 540 + (bx - cx) * s, 960 + (by - cy) * s
                d.ellipse((X - wd * 1.1, Y - wd * 0.7, X + wd * 1.1, Y + wd * 0.7), fill=RED)

    def needle_angle(self, t):
        if t < self.tp:
            return 8 * math.sin(t * 1.3)
        q = t - self.tp
        # разгон: угол = ∫ω, ω растёт от 120°/с до ~1500°/с к дропу
        T = self.drop - self.tp
        return 120 * q + 690 * q * q / T

    def _draw_needle(self, fr, t, cam):
        cx, cy, s = cam
        X, Y = 540 + (CMP[0] - cx) * s, 960 + (CMP[1] - cy) * s
        L = int(CMP_R * 1.7 * s)
        if L < 20 or Y - L > H or Y + L < 0:
            return
        nd = C.scale(needle(int(CMP_R * 1.7)), s, Image.BILINEAR) if abs(s - 1) > 0.01 else needle(int(CMP_R * 1.7))
        paste(fr, C.rotate(nd, -self.needle_angle(t)), X, Y)

    # ── вид карты ──
    def view(self, t, cam=None, dyn=True):
        cx, cy, s = cam or self.cam(t)
        key = self.layer(t)
        if s < 0.74:
            src = self.B['half_conv' if key == 'conv' else 'half_full']
            k = 0.5
        else:
            src = self.B[key]
            k = 1.0
        w, h = W / s, H / s
        x0, y0 = cx - w / 2, cy - h / 2
        if k < 1:
            box = ((x0 + M) * k + HPAD, (y0 + M) * k + HPAD, (x0 + w + M) * k + HPAD, (y0 + h + M) * k + HPAD)
            return src.resize((W, H), Image.BILINEAR, box=box)
        if not dyn:
            box = (x0 + M, y0 + M, x0 + w + M, y0 + h + M)
            return src.resize((W, H), Image.BILINEAR, box=box)
        ix0, iy0 = int(math.floor(x0)), int(math.floor(y0))
        ix1, iy1 = int(math.ceil(x0 + w)), int(math.ceil(y0 + h))
        reg = src.crop((ix0 + M, iy0 + M, ix1 + M, iy1 + M))
        self.draw_world(reg, t, ix0, iy0)
        if abs(s - 1) < 1e-4 and abs(x0 - ix0) < 1e-3 and abs(y0 - iy0) < 1e-3:
            return reg.crop((0, 0, W, H)) if reg.size != (W, H) else reg
        return reg.resize((W, H), Image.BILINEAR, box=(x0 - ix0, y0 - iy0, x0 - ix0 + w, y0 - iy0 + h))

    def draw_world(self, reg, t, ox, oy):
        """Дорисовать в участке мира то, что сейчас появляется (участок — от (ox, oy) мира)."""
        if t < 1.25 * self.u + 0.45:
            self._draw_intro(reg, t, ox, oy)
        if self.t1 <= t < self.tp:
            side = 'h' if t < self.t2 else 'a'
            self._draw_page(reg, side, t, ox, oy)
            self._quill(reg, t, side, ox, oy)

    def map_frame(self, t):
        cam = self.cam(t)
        # скорость камеры (пикс. экрана за кадр) → смаз движения при перелётах
        c2 = self.cam(t - 1 / 30)
        sp = math.hypot(cam[0] - c2[0], cam[1] - c2[1]) * cam[2] + abs(math.log(cam[2] / c2[2])) * 900
        if sp > 30:
            n = min(6, 2 + int(sp / 45))
            acc = None
            for i in range(n):
                tt = t - (i / (n - 1)) * 0.5 / 30
                im = self.view(tt, self.cam(tt), dyn=False)
                a = np.asarray(im, np.float32)
                acc = a if acc is None else acc + a
            fr = Image.fromarray((acc / n).astype(np.uint8), 'RGB')
        else:
            fr = self.view(t, cam)
        if self.tp <= t < self.drop:
            if t < self.conv1:
                self._draw_conv_screen(fr, t, cam)
            self._draw_needle(fr, t, cam)
        return fr

    # ── клад ──
    def _pick_prep(self):
        key = ('pick',) + self.key
        if key in _BAKE:
            self.PK = _BAKE[key]
            return
        PK = {}
        cam = (CMP[0], CMP[1] - (X_Y - 960) / S_PICK, S_PICK)
        PK['bg'] = self._pick_bg(cam)
        PK['x'] = self._x_stamp(820, 700)
        PK['lid'], PK['box'], PK['mound'] = self._chest(440)
        PK['emb'] = C.glow(self.fav.emb(300), 26, 1.0, (255, 214, 120))
        PK['scroll'], PK['roll'] = self._scroll()
        rays = self._rays(1000)
        PK['rays'] = [rays.rotate(-i * 22.5 / 12, Image.BILINEAR) for i in range(12)]
        PK['glow'] = C.radial(1000, 1000, (255, 196, 90), 230, 1.6)
        PK['spark'] = C.glow(C.ellipse(12, 12, (255, 246, 210)), 7, 1.4, (255, 200, 80))
        PK['coin'] = self._coin(34)
        _BAKE[key] = PK
        self.PK = PK

    def _pick_bg(self, cam):
        cx, cy, s = cam
        w, h = W / s, H / s
        x0, y0 = cx - w / 2 + M, cy - h / 2 + M
        src = self.B['base'].crop((int(x0) - 4, int(y0) - 4, int(x0 + w) + 6, int(y0 + h) + 6))
        for side in ('h', 'a'):                                   # чистая карта + только сходящиеся пути к кладу
            for sp, (x, y), e in self.conv[side]['ds']:
                paste(src, sp, x + M - int(x0) + 4, y + M - int(y0) + 4, anchor='tl')
        fx, fy = x0 - int(x0) + 4, y0 - int(y0) + 4
        im = src.resize((W, H), Image.BILINEAR, box=(fx, fy, fx + w, fy + h))
        im = im.filter(ImageFilter.GaussianBlur(3.2))
        arr = np.asarray(im, np.float32) * 0.6
        return Image.fromarray(arr.astype(np.uint8), 'RGB')

    def _x_stamp(self, w, h):
        rnd = np.random.default_rng(9)
        ss = 2
        im = Image.new('L', (w * ss, h * ss), 0)
        d = ImageDraw.Draw(im)
        for (x0, y0, x1, y1) in ((0.08, 0.06, 0.92, 0.94), (0.9, 0.08, 0.1, 0.92)):
            ax, ay, bx, by = x0 * w * ss, y0 * h * ss, x1 * w * ss, y1 * h * ss
            L = math.hypot(bx - ax, by - ay)
            nx, ny = -(by - ay) / L, (bx - ax) / L
            left, right = [], []
            for i in range(31):
                t = i / 30
                wd = (34 + 26 * math.sin(math.pi * t) ** 0.5) * ss * (0.92 + 0.16 * rnd.random())
                px, py = ax + (bx - ax) * t, ay + (by - ay) * t
                left.append((px + nx * wd, py + ny * wd))
                right.append((px - nx * wd, py - ny * wd))
            d.polygon(left + right[::-1], fill=255)
        for _ in range(26):                                             # брызги
            x, y = rnd.uniform(0.05, 0.95) * w * ss, rnd.uniform(0.05, 0.95) * h * ss
            r = rnd.uniform(3, 11) * ss
            d.ellipse((x - r, y - r, x + r, y + r), fill=255)
        m = im.resize((w, h), Image.LANCZOS)
        streak = _nz(w, h, 4, 90, rnd)
        a = np.asarray(m, np.float32) * (0.78 + 0.22 * streak)
        out = Image.new('RGBA', (w, h), RED + (0,))
        out.putalpha(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'L'))
        return out

    def _chest(self, w):
        """Сундук: крышка (откинута назад, видна изнутри), горка золота, передняя стенка."""
        ss = 2
        bw, bh = w, int(w * 0.44)
        WOOD = (124, 72, 36)
        WOOD_D = (78, 44, 22)
        IRON = (58, 56, 54)
        # передняя стенка
        im = Image.new('RGBA', (bw * ss, bh * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, bw * ss - 1, bh * ss - 1), radius=10 * ss, fill=WOOD + (255,))
        for i in range(1, 3):
            y = bh * ss * i / 3
            d.line((6 * ss, y, (bw - 6) * ss, y), fill=WOOD_D + (255,), width=3 * ss)
        for x in (0.1, 0.9):
            d.rectangle(((x * bw - 18) * ss, 0, (x * bw + 18) * ss, bh * ss), fill=IRON + (255,))
            for yy in (0.18, 0.5, 0.82):
                cx, cy = x * bw * ss, yy * bh * ss
                d.ellipse((cx - 5 * ss, cy - 5 * ss, cx + 5 * ss, cy + 5 * ss), fill=(150, 146, 140, 255))
        d.rectangle((0, 0, bw * ss, 16 * ss), fill=IRON + (255,))
        lx, ly = bw * ss / 2, 18 * ss
        d.rounded_rectangle((lx - 34 * ss, ly, lx + 34 * ss, ly + 70 * ss), radius=8 * ss, fill=(214, 168, 60, 255),
                            outline=(120, 84, 20, 255), width=2 * ss)
        d.ellipse((lx - 9 * ss, ly + 18 * ss, lx + 9 * ss, ly + 36 * ss), fill=(40, 24, 10, 255))
        d.polygon([(lx - 5 * ss, ly + 30 * ss), (lx + 5 * ss, ly + 30 * ss), (lx + 3 * ss, ly + 54 * ss), (lx - 3 * ss, ly + 54 * ss)],
                  fill=(40, 24, 10, 255))
        box = im.resize((bw, bh), Image.LANCZOS)
        arr = np.asarray(box, np.float32).copy()
        yy = np.linspace(0, 1, bh)[:, None]
        arr[..., :3] *= (1.08 - 0.35 * yy)[..., None]
        box = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
        # крышка изнутри (трапеция над стенкой)
        lh = int(w * 0.40)
        lid = Image.new('RGBA', (bw * ss, lh * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(lid)
        poly = [(0, lh * ss), (bw * ss, lh * ss), ((bw - 24) * ss, 30 * ss), (bw * ss / 2, 0), (24 * ss, 30 * ss)]
        d.polygon(poly, fill=(70, 38, 18, 255))
        for x in (0.1, 0.9):
            d.line(((x * bw) * ss, lh * ss, (x * bw + (12 if x < 0.5 else -12)) * ss, 22 * ss), fill=IRON + (255,), width=26 * ss)
        d.line(poly + [poly[0]], fill=(40, 22, 10, 255), width=4 * ss)
        lid = lid.resize((bw, lh), Image.LANCZOS)
        # горка золота
        mh = 70
        mound = Image.new('RGBA', (bw * ss, mh * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(mound)
        d.chord((10 * ss, 0, (bw - 10) * ss, mh * 2 * ss), 180, 360, fill=(226, 172, 52, 255))
        rnd = np.random.default_rng(4)
        for _ in range(60):
            x = rnd.uniform(30, bw - 30) * ss
            y = rnd.uniform(0.25, 1.0) * mh * ss
            r = rnd.uniform(9, 15) * ss
            c = (int(rnd.uniform(220, 255)), int(rnd.uniform(170, 210)), int(rnd.uniform(50, 90)), 255)
            d.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), fill=c, outline=(150, 100, 20, 255), width=ss)
        mound = mound.resize((bw, mh), Image.LANCZOS)
        return C.with_shadow(lid, 10, 0.4, 6), box, mound

    def _rays(self, S):
        im = Image.new('L', (S, S), 0)
        d = ImageDraw.Draw(im)
        c = S / 2
        for i in range(16):
            a = i * 2 * math.pi / 16
            wa = 0.07 if i % 2 == 0 else 0.04
            d.polygon([(c, c), (c + c * math.sin(a - wa), c - c * math.cos(a - wa)), (c + c * math.sin(a + wa), c - c * math.cos(a + wa))],
                      fill=150 if i % 2 == 0 else 90)
        yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
        fall = np.clip(1 - np.hypot(xx - c, yy - c) / c, 0, 1) ** 1.2
        a = np.asarray(im, np.float32) * fall
        out = Image.new('RGBA', (S, S), (255, 214, 120, 0))
        out.putalpha(Image.fromarray(a.astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(3)))
        return out

    def _coin(self, d):
        im = C.ellipse(d, d, (176, 122, 26))
        paste(im, C.ellipse(d - 6, d - 6, (246, 196, 72)), d / 2, d / 2)
        paste(im, C.ellipse(d - 16, d - 16, (226, 170, 50)), d / 2, d / 2)
        return im

    def _scroll(self):
        w, h = 900, 424
        rw = 56
        rnd = np.random.default_rng(12)
        body = np.zeros((h - 24, w - 2 * rw + 20, 4), np.float32)
        nz = _nz(body.shape[1], body.shape[0], 70, 70, rnd)
        yy = np.linspace(-1, 1, body.shape[0])[:, None]
        for i in range(3):
            body[..., i] = PAPER_L[i] * (0.92 + 0.1 * nz) * (1 - 0.08 * yy ** 2)
        body[..., 3] = 255
        b = Image.fromarray(np.clip(body, 0, 255).astype(np.uint8), 'RGBA')
        d = ImageDraw.Draw(b)
        bw, bh = b.size
        d.rectangle((26, 18, bw - 26, bh - 18), outline=INK2 + (170,), width=2)
        m = re.match(r'(ПОБЕДА)\s+(.+)$', self.pick1)
        y = 60
        if m:
            paste(b, C.text('ПОБЕДА', 'yes', 56, INK, track=0.1), bw / 2, y)
            nm = m.group(2)
            y += 84
        else:
            nm = self.pick1
            y += 30
        paste(b, C.text(nm, 'yes', 108, (138, 26, 18), max_w=bw - 70), bw / 2, y)
        y += 82
        if self.pick2:
            paste(b, C.text(self.pick2.lower(), 'hand', 60, INK2, 700, max_w=bw - 80), bw / 2, y)
        y += 74
        if self.coef:
            kt = C.text('КЭФ', 'hand', 54, INK2, 700)
            kv = C.text(C.fmt_k(self.coef), 'yes', 84, INK)
            wbox = kt.width + kv.width + 70
            bx = C.rrect(wbox, 104, 14, CREAM, 255, outline=INK, width=3)
            paste(bx, kt, 24 + kt.width / 2, 54)
            paste(bx, kv, wbox - 24 - kv.width / 2, 52)
            paste(b, bx, bw / 2, y + 22)
        out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        out.alpha_composite(b, (rw - 10, 12))
        roll = np.zeros((h, rw, 4), np.float32)
        xx = np.linspace(0, 1, rw)[None, :]
        shade = 0.55 + 0.6 * np.sin(xx * math.pi) ** 0.7
        for i in range(3):
            roll[..., i] = PAPER[i] * shade
        roll[..., 3] = 255
        r = Image.fromarray(np.clip(roll * np.ones((h, 1, 1)), 0, 255).astype(np.uint8), 'RGBA')
        r.putalpha(C.rrect(rw, h, rw / 2, (255, 255, 255)).getchannel('A'))
        dd = ImageDraw.Draw(r)
        dd.rounded_rectangle((0, 0, rw - 1, h - 1), radius=rw / 2, outline=INK + (200,), width=2)
        return out, r

    def beat_pulse(self, t):
        if t < self.drop:
            return 0.0
        return math.exp(-(((t - self.drop) / self.u) % 1.0) * 6)

    def pick(self, fr, t):
        D, u = self.drop, self.u
        PK = self.PK
        q = t - D
        kc = C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.5))
        gA = 1 - 0.24 * kc
        dyA = -62 * kc

        def A(x, y):
            return (540 + (x - 540) * gA, 640 + (y - 640) * gA + dyA)
        bp = self.beat_pulse(t)
        # свет из сундука
        gk = min(1.0, q / 0.12) * (0.7 + 0.3 * bp) * (1 + 0.6 * math.exp(-q / 0.25))
        gx, gy = A(540, 640)
        fr = C.add_light(fr, C.scale(PK['glow'], gA * (1 + 0.1 * bp)), gx, gy, 0.75 * gk)
        rays = PK['rays'][int((t * 30) / 2.5) % 12]
        # крест на месте клада
        kx = C.seg(q, 0, 0.09)
        if kx > 0:
            sc = (1 + 0.9 * (1 - C.out_cubic(kx)) ** 2) * gA
            x, y = A(540, 818)
            paste(fr, C.scale(PK['x'], sc), x, y, min(1.0, kx * 3))
        ra = min(1.0, q / 0.2) * (0.55 + 0.25 * bp)
        x, y = A(540, 600)
        paste(fr, C.scale(rays, gA * (0.8 + 0.25 * C.out_cubic(min(1.0, q / 0.4)))), x, y, ra)
        # сундук выпрыгивает
        kb = C.out_back(C.seg(q, 0.0, 0.2), 1.8)
        if kb > 0.01:
            lid_open = C.out_back(C.seg(q, 0.03, 0.2), 1.6)
            lid = PK['lid']
            lh = max(2, int(lid.height * max(0.12, lid_open)))
            lid_s = lid.resize((lid.width, lh), Image.BILINEAR)
            x, y = A(540, 706)
            ss = gA * max(0.3, kb)
            lid_s = C.scale(lid_s, ss)
            paste(fr, lid_s, x, y - lid_s.height / 2 + 30 * ss, min(1.0, kb * 2))
        # эмблема поднимается из сундука
        ke = C.out_back(C.seg(q, 0.02, 0.38), 1.3)
        ey = C.lerp(760, 462, ke)
        es = (0.45 + 0.55 * C.out_cubic(C.seg(q, 0.02, 0.3))) * (1 + 0.04 * bp)
        x, y = A(540, ey)
        paste(fr, C.scale(PK['emb'], es * gA), x, y, min(1.0, C.seg(q, 0.02, 0.1) * 2))
        if kb > 0.01:
            ss = gA * max(0.3, kb)
            x, y = A(540, 712)
            paste(fr, C.scale(PK['mound'], ss), x, y, min(1.0, kb * 2))
            x, y = A(540, 802)
            paste(fr, C.scale(PK['box'], ss), x, y, min(1.0, kb * 2))
        # искры и монеты
        self._sparks(fr, t, A, gA)
        # свиток
        ks = C.out_cubic(C.seg(q, 0.0, 0.3))
        sc = 1 - 0.16 * kc
        cy = C.lerp(1146, 1006, kc)
        scr = PK['scroll']
        if abs(sc - 1) > 0.003:
            scr = C.scale(scr, sc)
            roll = C.scale(PK['roll'], sc)
        else:
            roll = PK['roll']
        vis = max(int(roll.width * 1.2), int(scr.width * (0.05 + 0.95 * ks)))
        part = scr.crop(((scr.width - vis) // 2, 0, (scr.width - vis) // 2 + vis, scr.height))
        paste(fr, part, 540, cy)
        for sgn in (-1, 1):
            paste(fr, roll, 540 + sgn * (vis / 2 - roll.width / 2), cy)
        return fr

    def _sparks(self, fr, t, A, gA):
        PK = self.PK
        D, u = self.drop, self.u
        bursts = [(D, 46, 1.0)] + [(D + k * u, 12, 0.6) for k in range(1, 8) if D + k * u < self.dur]
        for b0, n, power in bursts:
            q = t - b0
            if not 0 <= q < 1.4:
                continue
            rnd = np.random.default_rng(int(b0 * 1000) % 100000)
            for i in range(n):
                ang = rnd.uniform(-math.pi * 0.92, -math.pi * 0.08)
                v = rnd.uniform(500, 1300) * power
                life = rnd.uniform(0.7, 1.3)
                if q > life:
                    continue
                x = 540 + math.cos(ang) * v * q
                y = 700 + math.sin(ang) * v * q + 900 * q * q
                X, Y = A(x, y)
                a = (1 - q / life) ** 1.2
                if i % 4 == 0 and n > 20:
                    spin = abs(math.cos(q * rnd.uniform(8, 16) + i))
                    cimg = PK['coin']
                    cimg = cimg.resize((max(2, int(cimg.width * spin * gA)), max(2, int(cimg.height * gA))), Image.BILINEAR)
                    paste(fr, cimg, X, Y, a)
                else:
                    paste(fr, PK['spark'], X, Y, a)

    # ── кадр ──
    def light_k(self, t):
        f = 1 + 0.022 * math.sin(t * 11.3) + 0.014 * math.sin(t * 23.7 + 1.3) + 0.01 * math.sin(t * 41 + 0.4)
        if t < 0.35:
            f *= 0.25 + 0.75 * C.out_cubic(C.seg(t, 0, 0.35))
        if self.dip0 <= t < self.dip1:
            f *= 1 - 0.34 * C.seg(t, self.dip0, self.dip0 + 0.15)
        if t >= self.dip1:
            f *= 1 + 0.16 * math.exp(-(t - self.dip1) / 0.14)
        if t >= self.kick and t < self.drop:
            f *= 1 + 0.1 * math.exp(-(t - self.kick) / 0.12)
        if t >= self.drop:
            f *= 1 + 0.07 * self.beat_pulse(t)
        return f

    def frame(self, t):
        u, D = self.u, self.drop
        if t < D:
            fr = self.map_frame(t)
        else:
            fr = self.PK['bg'].copy()
            fr = self.pick(fr, t)
        # камера: толчки на склейках, удар на дропе, пульс на долях
        z, dx, dy, rot = 1.0, 0.0, 0.0, 0.0
        for side in ('h', 'a'):
            ts = self.pages[side]['t0'] + 0.5 * u
            sx, sy = C.shake(t, ts, 6, 0.22)
            dx, dy = dx + sx, dy + sy
        if t >= D:
            kk = 1 - C.seg(t, D, D + 0.45)
            z += 0.07 * kk ** 2 + (0.012 * self.beat_pulse(t) if t < self.t_cta else 0)
            sx, sy = C.shake(t, D, 26, 0.45)
            dx, dy = dx + sx, dy + sy
            rot = 1.2 * kk ** 2 * math.sin((t - D) * 36)
        if z != 1.0 or dx or dy or rot:
            fr = C.zoom(fr.convert('RGB'), z, dx=dx, dy=dy, rot=rot)
        # свет свечи
        arr = np.asarray(fr.convert('RGB'), np.float32)
        arr *= self.light
        arr *= self.light_k(t)
        if D <= t < D + 0.32:
            fa = (1 - C.seg(t, D, D + 0.32)) ** 1.6
            arr = arr * (1 - 0.55 * fa) + np.array((255, 236, 190), np.float32) * 0.55 * fa
        fr = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
        fr = C.grain(fr, t, 5)
        # бирки поверх
        paste(fr, self.tag_im, W / 2, TAG_Y, C.seg(t, 0.05, 0.35))
        ha = C.seg(t, 0.15, 0.45) * (1 - C.seg(t, self.t_cta, self.t_cta + 0.2))
        paste(fr, self.handle_im, W / 2, HY, ha)
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.05, self.t_cta + 0.5))
            paste(fr, self.tg, W / 2, 1372 + 50 * (1 - q), q)
        return fr
