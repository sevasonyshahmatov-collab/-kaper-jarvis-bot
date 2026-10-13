# -*- coding: utf-8 -*-
"""«Ювелир» — прогноз как витрина ювелирного бутика (трек «VVS»): чёрный бархат с драпировкой, стекло витрины,
тёплый луч софита. Эмблемы клубов — полированные золотые медальоны с платиновым гильоше на подвесах (крутятся на
цепочке, блик скользит по металлу), факты — ценники ювелира на цепочках и гравированные золотые таблички на стеклянной
полке, выигрыш/поражение — изумруд «В» / рубин «П».

Сцены (u — доля трека, D — дроп; доли считаются от дропа, team / pre / hold / cta — параметры):
  интро (до D − (2·team + pre) долей) — сам матч: JARVIS | NHL, лига и время МСК, на перекладине два медальона
                 (хозяева / гости), между ними бриллиант-подвеска, под ними названия клубов; на стеклянной полке — линия
                 основного времени П1 · Х · П2 крупными плашками (оникс в золотой оправе) — по плашке на полдоли;
  команда (team долей) ×2 — медальон клуба опускается на цепочке ровно на долю, справа название, «хозяева / гости»,
                 серия (от 2 игр), результат дома / в гостях и большинство / меньшинство (если цифры есть);
                 на 1–3-й доле с нижней перекладины на цепочках спускаются ценники последних 3 игр (соперник, дата,
                 дома / в гостях, счёт, ОТ/Б, камень В/П) и качаются, на каждой доле — лёгкий толчок; на 4–6-й доле на
                 полку ложатся золотые таблички: очки за N матчей, место, разница шайб;
  интрига (pre долей) — оба медальона на перекладине крутятся всё быстрее, луч софита сужается к центру, блёстки чаще,
                 камера медленно наезжает;
  ДРОП (hold долей) — ровно на дропе вспышка граней: остаётся только медальон выбранной команды — уже «во льду»
                 (платина, паве из бриллиантов, бриллиантовая цепочка), лучи света за ним, разлёт искр; на полку падает
                 большая золотая табличка с прогнозом (form.split_pick) и кэфом; на каждую долю — блики на камнях;
  финал (cta долей) — витрина приподнимается, снизу плашка Telegram (C.tg_plate, текст ровно по центру плашки).
lag — на сколько долей настоящий удар трека позже точки дропа, которую передаёт сборка (vvs: точка 27,47 с, удар баса —
28,47 с, ровно полторы доли): видимый дроп self.drop = drop + lag·u, прогноз встаёт точно на удар.
@jarvibet — у низа безопасной зоны (y 1448), одинаково во всех сценах до плашки Telegram.
Кадр — чистая функция t; медальоны (с вариантами блика), ценники, таблички, бриллианты и бархат кешируются
на уровне модуля и в _prep (до fork — общие для процессов).
"""
import colorsys
import math
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels.core import W, H

C.FONTS.setdefault('yeseva', 'YesevaOne-Regular.ttf')        # дидона с жирным начертанием (кириллица, цифры в строку)

CHAMP = (243, 228, 194)                 # шампань — светлый текст
GOLDT = (228, 192, 118)                 # золото подписей
INK = (44, 28, 8)                       # гравировка на золоте
IVORY = (247, 240, 225)
WHITE = (255, 255, 255)
WARM = (255, 232, 186)
EMER = (16, 150, 96)
RUBY = (196, 24, 56)
TAG_Y, DATE_Y, RAIL_Y, RAIL2_Y, SHELF_Y, HY = 262, 318, 372, 758, 1322, 1448
SLOT_X = (200, 540, 880)                # ценники / таблички / плашки линии
TAGW, TAGH, CHL = 300, 262, 46          # ценник и цепочка до люверса
PLW, PLH = 300, 190                     # золотая табличка
ODW, ODH = 300, 240                     # плашка линии
G_INTRO, G_TEAM, G_PRE = 330, 290, 430  # диаметры медальонов по сценам
G_PICK, G_CTA = 470, 400
X_TEAM, NAME_X = 222, 738               # медальон команды и центр блока с названием
GOLD_STOPS = [(0.0, (46, 28, 6)), (0.2, (112, 76, 22)), (0.42, (190, 144, 58)), (0.62, (230, 192, 108)),
              (0.8, (250, 224, 156)), (0.92, (255, 243, 204)), (1.0, (255, 252, 236))]
PLAT_STOPS = [(0.0, (40, 44, 52)), (0.3, (112, 118, 130)), (0.6, (192, 198, 210)), (0.84, (234, 238, 245)),
              (1.0, (255, 255, 255))]
TEXT_GOLD = [(0.0, (255, 249, 222)), (0.38, (249, 220, 152)), (0.54, (218, 170, 82)), (0.68, (240, 204, 126)),
             (1.0, (255, 240, 190))]
LV = np.array([-0.42, -0.62, 0.66]) / np.linalg.norm([-0.42, -0.62, 0.66])
HV = (LV + np.array([0, 0, 1.0])) / np.linalg.norm(LV + np.array([0, 0, 1.0]))
_M = {}


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def pct(v):
    try:
        return ('%.1f' % float(v)).rstrip('0').rstrip('.') + '%'
    except (TypeError, ValueError):
        return None


# ─────────────────────────────── металл, камни, свет ───────────────────────────────
def ramp(v, stops):
    pos = [s[0] for s in stops]
    cols = np.array([s[1] for s in stops], np.float32)
    return np.stack([np.interp(v, pos, cols[:, i]) for i in range(3)], -1).astype(np.float32)


def to_img(rgb, a):
    arr = np.concatenate([np.clip(rgb, 0, 255), np.clip(a, 0, 255)[..., None]], -1).astype(np.uint8)
    return Image.fromarray(arr, 'RGBA')


def gold_text(s, font, size, wght=400, track=0.0, max_w=None, stroke=2, stops=TEXT_GOLD):
    """Текст золотом: вертикальный градиент полированного металла и тёмная окантовка (читается на бархате)."""
    key = ('gt', s, font, int(size), wght, track, max_w, stroke)
    if key not in _M:
        base = C.text(s, font, size, WHITE, wght, track=track, max_w=max_w, stroke=stroke, stroke_fill=(24, 14, 2))
        arr = np.asarray(base, np.float32).copy()
        g = ramp(np.linspace(0, 1, arr.shape[0]), stops)
        arr[..., :3] = arr[..., :3] / 255.0 * g[:, None, :]
        _M[key] = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
    return _M[key]


def engraved(s, font, size, wght=700, track=0.0, max_w=None, ink=INK, hi=(255, 246, 214)):
    """Гравировка на золоте: тёмная надпись и светлая кромка снизу."""
    key = ('en', s, font, int(size), wght, track, max_w, ink, hi)
    if key not in _M and font == 'yeseva' and s[:1] in '−-' and len(s) > 1:
        a = engraved('−', 'mont', size * 0.8, 800, ink=ink, hi=hi)          # в Yeseva нет знака минус
        b = engraved(s[1:], font, size, wght, track, max_w, ink, hi)
        out = Image.new('RGBA', (a.width + 4 + b.width, b.height), (0, 0, 0, 0))
        out.alpha_composite(a, (0, int(b.height * 0.5 - a.height * 0.5)))
        out.alpha_composite(b, (a.width + 4, 0))
        _M[key] = out
    if key not in _M:
        d = C.text(s, font, size, ink, wght, track=track, max_w=max_w)
        li = C.text(s, font, size, hi, wght, track=track, max_w=max_w)
        out = Image.new('RGBA', (d.width + 2, d.height + 3), (0, 0, 0, 0))
        out.alpha_composite(C.fade(li, 0.8), (1, 3))
        out.alpha_composite(d, (1, 0))
        _M[key] = out
    return _M[key]


def sdf_rr(w, h, r):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    px, py = x + 0.5 - w / 2, y + 0.5 - h / 2
    qx, qy = np.abs(px) - (w / 2 - r), np.abs(py) - (h / 2 - r)
    sd = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r
    return sd, x, y


def metal(w, h, r, stops=GOLD_STOPS, bevel=9, seed=3, gain=1.0):
    """Пластина полированного металла со скошенной кромкой (свет сверху слева) и лёгкой шлифовкой."""
    key = ('metal', w, h, r, tuple(stops[2][1]), bevel, seed, gain)
    if key in _M:
        return _M[key]
    sd, x, y = sdf_rr(w, h, r)
    a = np.clip(0.5 - sd, 0, 1)
    p = (x / w * 0.8 + y / h * 0.5) / 1.3
    v = 0.5 + 0.26 * np.exp(-((p - 0.25) / 0.15) ** 2) + 0.2 * np.exp(-((p - 0.74) / 0.09) ** 2) - 0.1 * p
    rng = np.random.default_rng(seed)
    rows = np.convolve(rng.normal(0, 1, h + 8), np.ones(5) / 5, 'same')[4:h + 4]
    v = v + 0.03 * rows[:, None] + 0.012 * rng.normal(0, 1, (h, w))
    inside = -sd
    gy, gx = np.gradient(sd)
    band = np.clip(1 - inside / bevel, 0, 1) * (inside > -1)
    v = v + 0.42 * band * (-(gx * 0.55 + gy * 0.83))
    v = v - 0.2 * np.exp(-((inside - bevel) / 1.3) ** 2) + 0.1 * np.exp(-((inside - bevel - 2.6) / 1.1) ** 2)
    out = to_img(ramp(np.clip(v * gain, 0, 1), stops), a * 255)
    _M[key] = out
    return out


def onyx(w, h, r, rim=7):
    """Чёрный оникс в золотой оправе: глянец сверху, тонкая золотая линия внутри."""
    key = ('onyx', w, h, r, rim)
    if key in _M:
        return _M[key]
    out = metal(w, h, r, bevel=5, seed=11).copy()
    iw, ih = w - 2 * rim, h - 2 * rim
    sd, x, y = sdf_rr(iw, ih, max(2, r - rim))
    a = np.clip(0.5 - sd, 0, 1)
    k = (y / ih)[..., None]
    rgb = np.array((38, 34, 40), np.float32) * (1 - k) + np.array((9, 8, 10), np.float32) * k
    gl = np.clip(1 - y / (ih * 0.46), 0, 1) ** 1.6 * 26 * (np.abs(x - iw * 0.5) < iw * 0.47)
    rgb = rgb + gl[..., None]
    inner = to_img(rgb, a * 255)
    out.alpha_composite(inner, (rim, rim))
    ln = C.rrect(w - 2 * rim - 16, h - 2 * rim - 16, max(2, r - rim - 8), None, outline=(180, 140, 64), width=2)
    out.alpha_composite(C.fade(ln, 0.85), (rim + 8, rim + 8))
    _M[key] = out
    return out


def sphere(d, stops=GOLD_STOPS):
    key = ('sph', d, tuple(stops[2][1]))
    if key in _M:
        return _M[key]
    ss = 3
    S = d * ss
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    nx, ny = (x + 0.5 - S / 2) / (S / 2), (y + 0.5 - S / 2) / (S / 2)
    rr = nx ** 2 + ny ** 2
    nz = np.sqrt(np.clip(1 - rr, 0, 1))
    dif = np.clip(nx * LV[0] + ny * LV[1] + nz * LV[2], 0, 1)
    spec = np.clip(nx * HV[0] + ny * HV[1] + nz * HV[2], 0, 1) ** 30
    v = 0.12 + 0.62 * dif + 0.6 * spec
    a = np.clip((1 - np.sqrt(rr)) * S / 2 + 0.5, 0, 1) * 255
    out = to_img(ramp(np.clip(v, 0, 1), stops), a).resize((d, d), Image.LANCZOS)
    _M[key] = out
    return out


def diamond(s, var=0):
    """Бриллиант круглой огранки сверху: площадка, клинья, грани короны; у части граней — «игра» (цветные отблески)."""
    s = int(s)
    key = ('dia', s, var)
    if key in _M:
        return _M[key]
    ss = 6 if s < 30 else 4
    S = s * ss
    c, R = S / 2, S / 2 - ss * 0.6
    rng = np.random.default_rng(900 + var * 37)
    off = -math.pi / 2 + math.pi / 16
    G = [(c + R * math.cos(j * math.pi / 8 + off), c + R * math.sin(j * math.pi / 8 + off)) for j in range(16)]
    T = [(c + 0.55 * R * math.cos(k * math.pi / 4 + off), c + 0.55 * R * math.sin(k * math.pi / 4 + off)) for k in range(8)]
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon(G, fill=(40, 46, 58, 255))

    def col(b):
        if rng.random() < 0.16:
            hue = rng.choice([0.0, 0.08, 0.14, 0.52, 0.6, 0.78, 0.9])
            r_, g_, b_ = colorsys.hsv_to_rgb(hue, 0.42, 0.5 + 0.5 * b)
            return (int(r_ * 255), int(g_ * 255), int(b_ * 255), 255)
        return (int(26 + 226 * b), int(30 + 225 * b), int(42 + 213 * b), 255)

    for k in range(8):
        a0, a1 = T[k], T[(k + 1) % 8]
        g0, g1, g2 = G[2 * k], G[2 * k + 1], G[(2 * k + 2) % 16]
        for tri in ((a0, g0, g1), (a0, g1, a1), (a1, g1, g2)):
            d.polygon(tri, fill=col(rng.choice([0.08, 0.25, 0.5, 0.75, 0.92, 1.0], p=[0.14, 0.18, 0.18, 0.18, 0.16, 0.16])))
    d.polygon(T, fill=col(0.62 + 0.25 * rng.random()))
    for k in range(8):                                              # «стрелы» — тёмные клинья к центру
        d.line((c, c, T[k][0], T[k][1]), fill=(30, 36, 50, 150), width=max(1, int(ss * 0.5)))
    d.line(G + [G[0]], fill=(245, 248, 255, 210), width=max(1, int(ss * 0.7)))
    d.line(T + [T[0]], fill=(255, 255, 255, 120), width=max(1, int(ss * 0.45)))
    hx, hy = c - 0.22 * R, c - 0.26 * R
    d.ellipse((hx - 0.1 * R, hy - 0.1 * R, hx + 0.1 * R, hy + 0.1 * R), fill=(255, 255, 255, 230))
    out = im.resize((s, s), Image.LANCZOS)
    _M[key] = out
    return out


def gem(res, d=56):
    """Камень ступенчатой огранки в золотой оправе: изумруд — «В», рубин — «П»."""
    key = ('gem', res, d)
    if key in _M:
        return _M[key]
    col = EMER if res == 'В' else RUBY if res == 'П' else (110, 112, 124)
    ss = 4
    D = d * ss
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.rounded_rectangle((0, 0, D - 1, D - 1), radius=int(D * 0.24), fill=(222, 178, 86, 255))
    dr.rounded_rectangle((D * 0.035, D * 0.035, D * 0.965, D * 0.965), radius=int(D * 0.22), fill=(150, 108, 34, 255))
    for ins, b in ((0.07, 0.5), (0.15, 1.05), (0.25, 0.72), (0.35, 1.2), (0.45, 0.9)):
        c = tuple(int(min(255, v * b)) for v in col) + (255,)
        dr.rounded_rectangle((D * ins, D * ins, D * (1 - ins), D * (1 - ins)), radius=int(D * 0.2 * (1 - ins)), fill=c)
    dr.polygon([(D * 0.16, D * 0.2), (D * 0.42, D * 0.12), (D * 0.3, D * 0.32)], fill=(255, 255, 255, 120))
    im = im.resize((d, d), Image.LANCZOS)
    dk = tuple(int(v * 0.35) for v in col)
    C.put(im, C.text(res or '?', 'mont', d * 0.52, WHITE, 900, stroke=2, stroke_fill=dk), d / 2, d / 2 + 1)
    _M[key] = im
    return im


def star(S, col=(255, 246, 228), diag=0.35):
    """Звёздный блик (float32, h×w×3, 0..~1.5) — складывается со светом кадра."""
    S = int(S) | 1
    key = ('star', S, col, diag)
    if key in _M:
        return _M[key]
    y, x = np.mgrid[0:S, 0:S].astype(np.float32) - S // 2
    r = np.hypot(x, y)
    tk = max(0.75, S * 0.009)
    L = S * 0.17
    I = 1.3 * np.exp(-(r / (S * 0.03 + 0.9)) ** 2) + 0.28 * np.exp(-(r / (S * 0.1)) ** 2)
    I += np.exp(-(y / tk) ** 2) * np.exp(-np.abs(x) / L) + np.exp(-(x / tk) ** 2) * np.exp(-np.abs(y) / L)
    uu, ww = (x + y) / 1.4142, (x - y) / 1.4142
    I += diag * (np.exp(-(ww / tk) ** 2) * np.exp(-np.abs(uu) / (L * 0.45)) +
                 np.exp(-(uu / tk) ** 2) * np.exp(-np.abs(ww) / (L * 0.45)))
    I *= np.clip(1 - r / (S / 2), 0, 1) ** 0.6
    out = (I[..., None] * (np.array(col, np.float32) / 255)).astype(np.float32)
    _M[key] = out
    return out


def fire(L, th, hue0, ang):
    """Цветной отблеск-радуга (дисперсия в гранях) — короткий штрих (float32)."""
    key = ('fire', L, th, round(hue0, 2), round(ang, 1))
    if key in _M:
        return _M[key]
    S = int(L + 8) | 1
    y, x = np.mgrid[0:S, 0:S].astype(np.float32) - S // 2
    ca, sa = math.cos(ang), math.sin(ang)
    p, q = x * ca + y * sa, -x * sa + y * ca
    k = np.clip(1 - np.abs(p) / (L / 2), 0, 1) ** 0.8 * np.exp(-(q / th) ** 2)
    hue = (hue0 + (p / L + 0.5) * 0.75) % 1.0
    rgb = np.stack([np.clip(np.abs(hue * 6 - 3) - 1, 0, 1), np.clip(2 - np.abs(hue * 6 - 2), 0, 1),
                    np.clip(2 - np.abs(hue * 6 - 4), 0, 1)], -1)
    out = (k[..., None] * (0.35 + 0.65 * rgb)).astype(np.float32)
    _M[key] = out
    return out


def addl(arr, spr, cx, cy, k):
    """Сложить свет спрайта spr (float) в кадр arr (float32 0..255) центром в (cx, cy)."""
    if k <= 0.01:
        return
    h, w = spr.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya:
        return
    arr[ya:yb, xa:xb] += spr[ya - y0:yb - y0, xa - x0:xb - x0] * (255.0 * k)


def chain_strip(L=1600, w=16, pitch=15, iced=False):
    """Цепочка сверху вниз (кеш): золотые звенья «якорь» или бриллиантовая теннисная нить."""
    key = ('chain', L, w, pitch, iced)
    if key in _M:
        return _M[key]
    if iced:
        im = Image.new('RGBA', (w, L), (0, 0, 0, 0))
        bar = C.rrect(4, L, 2, (200, 206, 218))
        C.put(im, bar, w / 2, L / 2)
        for i, y in enumerate(range(w // 2, L + w, w)):
            C.put(im, diamond(w, i % 6), w / 2, y)
        _M[key] = im
        return im
    ss = 3
    im = Image.new('RGBA', (w * ss, L * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dark, mid, light = (112, 76, 20, 255), (196, 150, 62, 255), (255, 232, 160, 255)
    for i, y in enumerate(range(-pitch, L + pitch, pitch)):
        if i % 2 == 0:
            box = (w * ss * 0.1, y * ss, w * ss * 0.9, (y + pitch * 1.5) * ss)
            d.ellipse(box, outline=dark, width=int(3.6 * ss))
            d.ellipse((box[0] + ss * 0.6, box[1] + ss * 0.3, box[2] - ss * 0.9, box[3] - ss * 0.6), outline=mid, width=int(2.2 * ss))
            d.arc((box[0] + ss, box[1] + ss * 0.8, box[2] - ss, box[3] - ss), 160, 250, fill=light, width=int(1.4 * ss))
        else:
            d.rounded_rectangle((w * ss * 0.38, (y - 3) * ss, w * ss * 0.62, (y + pitch * 1.5 + 3) * ss), radius=int(w * ss * 0.12),
                                fill=mid, outline=dark, width=ss)
            d.line((w * ss * 0.45, y * ss, w * ss * 0.45, (y + pitch * 1.5) * ss), fill=light, width=ss)
    out = im.resize((w, L), Image.LANCZOS)
    _M[key] = out
    return out


def rail(w, th=12):
    """Перекладина витрины: золотой пруток с шарами на концах."""
    key = ('rail', w, th)
    if key in _M:
        return _M[key]
    fd = int(th * 2.6)
    out = Image.new('RGBA', (w + fd, fd + 4), (0, 0, 0, 0))
    yy = np.linspace(0, 1, th)
    v = 0.3 + 0.62 * np.exp(-((yy - 0.3) / 0.2) ** 2) - 0.18 * yy
    rgb = ramp(np.clip(v, 0, 1), GOLD_STOPS)[:, None, :].repeat(w, 1)
    a = np.full((th, w), 255.0)
    a[0, :] = a[-1, :] = 150
    rod = to_img(rgb, a)
    out.alpha_composite(rod, (fd // 2, (fd + 4 - th) // 2))
    sp = sphere(fd)
    out.alpha_composite(sp, (0, 2))
    out.alpha_composite(sp, (w, 2))
    _M[key] = out
    return out


def hook(d=18):
    key = ('hook', d)
    if key not in _M:
        ss = 4
        im = Image.new('RGBA', (d * ss, d * ss), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        dr.ellipse((ss * 2, ss * 2, d * ss - ss * 2, d * ss - ss * 2), outline=(118, 80, 22, 255), width=int(4 * ss))
        dr.ellipse((ss * 2.6, ss * 2.2, d * ss - ss * 2.8, d * ss - ss * 2.8), outline=(244, 214, 140, 255), width=int(2 * ss))
        _M[key] = im.resize((d, d), Image.LANCZOS)
    return _M[key]


def shelf(w=1010):
    """Стеклянная полка: верхняя плоскость, светлая передняя кромка, зеленоватый торец."""
    key = ('shelf', w)
    if key in _M:
        return _M[key]
    h = 30
    arr = np.zeros((h, w, 4), np.float32)
    xs = np.linspace(0, 1, w)
    fade_x = np.clip(np.minimum(xs, 1 - xs) / 0.06, 0, 1)
    arr[0:10, :, :3] = (190, 214, 210)
    arr[0:10, :, 3] = np.linspace(22, 60, 10)[:, None] * fade_x[None, :]
    arr[10:12, :, :3] = (240, 252, 248)
    arr[10:12, :, 3] = 210 * fade_x
    arr[12:26, :, :3] = (96, 146, 136)
    arr[12:26, :, 3] = np.linspace(120, 50, 14)[:, None] * fade_x[None, :]
    arr[26:28, :, :3] = (170, 210, 200)
    arr[26:28, :, 3] = 70 * fade_x
    out = Image.fromarray(arr.astype(np.uint8), 'RGBA')
    _M[key] = out
    return out


def reflection(im, hgt=70, a0=0.24):
    """Отражение предмета в стекле полки: перевёрнутый низ, гаснет вниз."""
    key = ('refl', id(im), hgt, a0)
    if key in _M:
        return _M[key][1]
    hgt = min(hgt, im.height)
    part = im.crop((0, im.height - hgt, im.width, im.height)).transpose(Image.FLIP_TOP_BOTTOM)
    al = np.asarray(part.getchannel('A'), np.float32) * (np.linspace(a0, 0, hgt) ** 1.3)[:, None]
    part.putalpha(Image.fromarray(al.astype(np.uint8)))
    _M[key] = (im, part)                       # держим im — id не переиспользуется
    return part


# ─────────────────────────────── медальоны ───────────────────────────────
K_SWEEP = 10


def _polar(d, m, ss):
    Wd, Hd = d * ss, (d + m) * ss
    R = d * ss / 2
    cx, cy = Wd / 2, m * ss + R
    y, x = np.mgrid[0:Hd, 0:Wd].astype(np.float32)
    dx, dy = x + 0.5 - cx, y + 0.5 - cy
    r = np.hypot(dx, dy)
    return dict(R=R, dx=dx, dy=dy, r=r, rn=r / R, th=np.arctan2(dy, dx), ux=dx / np.maximum(r, 1e-3), uy=dy / np.maximum(r, 1e-3))


def _lit(P, nr):
    nz = np.sqrt(np.clip(1 - nr ** 2, 0, 1))
    nx, ny = nr * P['ux'], nr * P['uy']
    dif = np.clip(nx * LV[0] + ny * LV[1] + nz * LV[2], 0, 1)
    spec = np.clip(nx * HV[0] + ny * HV[1] + nz * HV[2], 0, 1) ** 36
    return dif, spec


def _bail(im, d, m, iced):
    """Ушко подвеса над медальоном (рисуется до диска — низ ушка уходит за медальон)."""
    ss = 4
    w, h = int(d * 0.15), int(m + d * 0.05)
    lay = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    th = max(3, d * 0.03) * ss
    dk, lt = ((70, 74, 86, 255), (236, 240, 248, 255)) if iced else ((104, 70, 18, 255), (250, 222, 150, 255))
    dr.ellipse((ss, ss, w * ss - ss, h * ss - ss), outline=dk, width=int(th))
    dr.ellipse((ss * 2.2, ss * 1.6, w * ss - ss * 3, h * ss - ss * 3), outline=lt, width=int(th * 0.45))
    lay = lay.resize((w, h), Image.LANCZOS)
    im.alpha_composite(lay, (int(d / 2 - w / 2), 1))
    if iced:
        for k in range(2):
            C.put(im, diamond(int(d * 0.045), k + 3), d / 2, 1 + h * (0.28 + 0.4 * k))


def _sweeps(base, d, m):
    """K вариантов: диагональный блик проходит по металлу (выбирается по повороту медальона)."""
    arr = np.asarray(base, np.float32)
    a = arr[..., 3:4] / 255
    y, x = np.mgrid[0:d + m, 0:d].astype(np.float32)
    proj = ((x - d / 2) * 0.6 + (y - m - d / 2) * 0.8) / d + 0.5
    out = []
    for k in range(K_SWEEP):
        p = -0.25 + 1.5 * k / (K_SWEEP - 1)
        band = (np.exp(-((proj - p) / 0.07) ** 2) * 0.55 + np.exp(-((proj - p - 0.13) / 0.025) ** 2) * 0.35)[..., None]
        rgb = arr[..., :3] + band * 255 * a * (1 - arr[..., :3] / 400)
        out.append(to_img(rgb, arr[..., 3]))
    return out


def medal(team, d, iced=False):
    """Медальон клуба диаметра d с ушком (холст d × (d + m), центр диска — (d/2, m + d/2), точка подвеса — (d/2, 0)).
    Золото: полированный выпуклый обод, бусины, платиновое гильоше, эмблема с эмалевым глянцем.
    «Во льду»: платина, ряд крупных бриллиантов по ободу, паве по полю, эмблема в платиновой рамке.
    → dict(var=[K вариантов блика], edge=торец для поворота, m, d, stones=[(x, y, размер)] для бликов)."""
    key = ('medal', team.name, d, iced)
    if key in _M:
        return _M[key]
    m = int(round(d * 0.11))
    ss = 2
    P = _polar(d, m, ss)
    rn, R = P['rn'], P['R']
    stones = []
    if not iced:
        nr = np.clip((rn - 0.93) / 0.075, -1, 1)
        dif, spec = _lit(P, nr)
        v_rim = 0.16 + 0.62 * dif + 0.7 * spec + 0.05 * np.cos(2 * P['th'] + 0.8)
        dif2, spec2 = _lit(P, np.clip((rn - 0.81) / 0.05, -1, 1) * -0.45)
        v_seat = 0.14 + 0.45 * dif2 + 0.2 * spec2
        lf = np.clip(0.55 - (P['dx'] * 0.42 + P['dy'] * 0.62) / (R * 1.5), 0, 1)
        guil = 0.5 + 0.5 * np.sin(P['th'] * 64)
        v_face = 0.5 + 0.3 * lf + 0.08 * (guil - 0.5) * np.clip(rn / 0.76, 0, 1) + 0.025 * np.sin(rn * R / ss * 0.9)
        v_face = v_face - 0.32 * np.exp(-np.clip(0.76 - rn, 0, None) / 0.02)
        gold = ramp(np.clip(np.where(rn >= 0.86, v_rim, v_seat), 0, 1), GOLD_STOPS)
        plat = ramp(np.clip(v_face, 0, 1), PLAT_STOPS)
        rgb = np.where((rn < 0.76)[..., None], plat, gold)
        rgb *= (1 - 0.55 * np.exp(-((rn - 0.86) * R / (1.3 * ss)) ** 2))[..., None]
        rgb += (60 * np.exp(-((rn - 0.765) * R / (1.0 * ss)) ** 2))[..., None]
        edge_rgb = ramp(np.clip(0.2 + 0.25 * lf + 0.0 * rn, 0, 1), GOLD_STOPS)
    else:
        nr = np.clip((rn - 0.965) / 0.035, -1, 1)
        dif, spec = _lit(P, nr)
        v_rim = 0.18 + 0.6 * dif + 0.7 * spec
        dif3, spec3 = _lit(P, np.clip((rn - 0.76) / 0.016, -1, 1))
        v_ring = 0.2 + 0.6 * dif3 + 0.6 * spec3
        v = np.where(rn >= 0.93, v_rim, np.where(np.abs(rn - 0.76) < 0.016, v_ring, 0.2))
        rgb = ramp(np.clip(v, 0, 1), PLAT_STOPS)
        lf = np.clip(0.55 - (P['dx'] * 0.42 + P['dy'] * 0.62) / (R * 1.5), 0, 1)
        edge_rgb = ramp(np.clip(0.2 + 0.3 * lf, 0, 1), PLAT_STOPS)
    a = np.clip((R - P['r']) / ss + 0.5, 0, 1) * 255
    disc = to_img(rgb, a).resize((d, d + m), Image.LANCZOS)
    edge = to_img(edge_rgb, a).resize((d, d + m), Image.LANCZOS)
    im = Image.new('RGBA', (d, d + m), (0, 0, 0, 0))
    _bail(im, d, m, iced)
    im.alpha_composite(disc)
    R1 = d / 2
    cx, cy = d / 2, m + d / 2
    if not iced:
        n = int(2 * math.pi * 0.81 / 0.1)
        bd = max(6, int(R1 * 0.085))
        sp = sphere(bd)
        for k in range(n):
            a_ = 2 * math.pi * k / n
            C.put(im, sp, cx + 0.81 * R1 * math.cos(a_), cy + 0.81 * R1 * math.sin(a_))
        e = team.emb(int(d * 0.6))
    else:
        n1 = int(2 * math.pi * 0.85 / 0.135)
        s1 = int(2 * math.pi * 0.85 * R1 / n1 * 0.97)
        for k in range(n1):
            a_ = 2 * math.pi * k / n1 - math.pi / 2
            x_, y_ = cx + 0.85 * R1 * math.cos(a_), cy + 0.85 * R1 * math.sin(a_)
            C.put(im, diamond(s1, k % 8), x_, y_)
            stones.append((x_, y_, s1))
        sp_ = 0.088 * R1
        s2 = max(8, int(sp_ * 0.98))
        rng = np.random.default_rng(5)
        j = 0
        for row in range(-12, 13):
            yy = row * sp_ * 0.866
            for col in range(-12, 13):
                xx = (col + (0.5 if row % 2 else 0)) * sp_
                if math.hypot(xx, yy) + sp_ * 0.5 < 0.74 * R1:
                    C.put(im, diamond(s2, 8 + j % 6), cx + xx, cy + yy)
                    if rng.random() < 0.3:
                        stones.append((cx + xx, cy + yy, s2))
                    j += 1
        e = team.emb(int(d * 0.56))
        ring = C.tint(e, (232, 236, 244))
        ring.putalpha(e.getchannel('A').filter(ImageFilter.MaxFilter(9)))
        C.put(im, C.shadow(ring, 10, 0.9, (6, 6, 10), spread=4), cx, cy + 4)
        C.put(im, ring, cx, cy)
    if not iced:
        C.put(im, C.shadow(e, 5, 0.55), cx + 3, cy + 6)
    C.put(im, e, cx, cy)
    gl = np.zeros((e.height, e.width, 4), np.uint8)                       # эмалевый глянец по эмблеме
    gl[..., :3] = 255
    yk = np.clip(1 - np.linspace(0, 1, e.height) / 0.5, 0, 1) ** 1.5 * 60
    gl[..., 3] = np.minimum(np.asarray(e.getchannel('A'), np.float32), yk[:, None]).astype(np.uint8)
    C.put(im, Image.fromarray(gl, 'RGBA'), cx, cy)
    out = dict(var=_sweeps(im, d, m), edge=edge, m=m, d=d, stones=stones)
    _M[key] = out
    return out


# ─────────────────────────────── бархат витрины ───────────────────────────────
def velvet():
    key = ('velvet',)
    if key in _M:
        return _M[key]
    rng = np.random.default_rng(5)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    xs = x + 34 * np.sin(y / 430 + 0.7) + 14 * np.sin(y / 170 + 2.0)
    fold = 0.5 * np.sin(xs / 97 + 0.3) + 0.3 * np.sin(xs / 53 + 1.9) + 0.2 * np.sin(xs / 31 + 0.4)
    fold = (fold + 1) / 2
    v = 0.74 + 0.36 * fold ** 1.6
    top = np.exp(-(((x - W / 2) / 760) ** 2 + ((y + 140) / 1250) ** 2))          # свет софита сверху
    v = v * (0.55 + 1.15 * top)
    n = Image.fromarray((rng.normal(128, 40, (H, W))).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    v = v * (1 + (np.asarray(n, np.float32) - 128) / 128 * 0.07)
    base = np.array((25, 18, 23), np.float32)
    rgb = v[..., None] * base
    for c0, wd, k in ((420, 70, 7.0), (560, 22, 6.0), (1500, 120, 4.0)):            # блики стекла витрины
        dd = np.abs(x * 0.5 + y - c0) / 1.118
        rgb += (k * np.exp(-(dd / wd) ** 2))[..., None]
    for gx in (30, W - 30):                                                          # рёбра стеклянного короба
        g = np.exp(-((x - gx) / 1.6) ** 2) * (0.3 + 0.7 * np.clip(1 - y / H, 0, 1)) * 22
        rgb += g[..., None] * np.array((0.8, 1.0, 0.95), np.float32)
    out = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    _M[key] = out
    return out


def vignette_f():
    key = ('vig',)
    if key not in _M:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 * 0.8 + ((y - H * 0.48) / (H / 2)) ** 2)
        _M[key] = (1 - 0.5 * np.clip(d / 1.25, 0, 1) ** 2.3)[..., None].astype(np.float32)
    return _M[key]


def grain_f(i):
    key = ('grain',)
    if key not in _M:
        rng = np.random.default_rng(3)
        _M[key] = [(rng.normal(0, 3.2, (H // 2 + 1, W // 2 + 1))).astype(np.float32).repeat(2, 0).repeat(2, 1)[:H, :W]
                   for _ in range(6)]
    return _M[key][i % 6]


def flash_f(cx, cy):
    key = ('flash', int(cx), int(cy))
    if key not in _M:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.hypot(x - cx, (y - cy) * 0.9)
        _M[key] = (np.exp(-(r / 260) ** 2) * 0.55 + np.exp(-(r / 820) ** 2) * 0.4).astype(np.float32)
    return _M[key]


# ─────────────────────────────── ролик ───────────────────────────────
class Jewel(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 90, drop=24 * 60 / 90, line=None, team=9, pre=2,
                 hold=6, cta=3.5, lag=0.0, seed=41, **kw):
        """Сцены: интро → команда (team долей) ×2 → интрига (pre) → дроп-прогноз (hold) → Telegram (cta); доли — от дропа."""
        super().__init__(u, drop + lag * u, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.line = league, when, coef, line
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.other = 'a' if self.side == 'h' else 'h'
        self.T = {'h': self.h, 'a': self.a}
        self.raw = {'h': sh or {}, 'a': sa or {}}
        self.st = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.team_n, self.pre = team, pre
        self.t1 = self.b(-(2 * team + pre))
        self.t2 = self.b(-(team + pre))
        self.tp = self.b(-pre)
        if self.t1 < 1.5:
            raise ValueError('мало времени до дропа')
        self.t_cta = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = max(1.4, self.t1 - 0.6)
        self.i_d = G_INTRO if line else 400
        self.i_cy = max(590, RAIL_Y + 10 + 0.61 * self.i_d) if line else 680
        self._prep()

    # ── заготовки ──
    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        self.bg = velvet()
        vignette_f()
        grain_f(0)
        for t_ in (self.h, self.a):
            medal(t_, G_PRE)
        self.fav = self.T[self.side]
        self.ice = medal(self.fav, G_PICK, iced=True)
        self.tag = C.text(F.tag(self.league), 'mont', 28, GOLDT, 700, track=0.32)
        self.date = C.text('%s · %s' % (F.lg_ru(self.league), self.when), 'mont', 40, CHAMP, 700, track=0.03, max_w=980)
        self.handle = C.text(C.HANDLE, 'mont', 40, CHAMP, 700)
        self.rail1 = rail(980, 14)
        self.rail2 = rail(980, 10)
        self.shelf = shelf()
        self.chain = chain_strip()
        self.ichain = chain_strip(700, 16, iced=True)
        self.hookim = hook(20)
        # интро
        self.i_role = {s: C.text('ХОЗЯЕВА' if s == 'h' else 'ГОСТИ', 'mont', 26, GOLDT, 700, track=0.32) for s in 'ha'}
        self.i_name = {s: gold_text(self.T[s].up, 'yeseva', 66, max_w=470) for s in 'ha'}
        self.orn = diamond(84, 2)
        self.odds = []
        if self.line:
            for lab, v in zip(('П1', 'Х', 'П2'), self.line):
                pl = onyx(ODW, ODH, 30).copy()
                C.put(pl, C.text(lab, 'mont', 38, GOLDT, 800, track=0.16), ODW / 2, 64)
                C.put(pl, gold_text(C.fmt_k(v), 'yeseva', 104, stroke=0, max_w=ODW - 50), ODW / 2, 154)
                self.odds.append((pl, reflection(pl)))
        self.odds_lab = C.text('ОСНОВНОЕ ВРЕМЯ', 'mont', 30, GOLDT, 700, track=0.3)
        # команды
        self.TD = {s: self._team_data(s) for s in 'ha'}
        # интрига
        self.p_name = {s: gold_text(self.T[s].up, 'yeseva', 68, max_w=480) for s in 'ha'}
        # прогноз
        self.pick_pl = self._pick_plate()
        self.pick_refl = reflection(self.pick_pl, 80)
        self.tg = C.tg_plate(960, 170)
        # свет: блёстки на бархате, искры дропа, цветные отблески
        self.twk = [(rnd.uniform(40, W - 40), rnd.uniform(240, 1460), rnd.uniform(1.3, 2.8), rnd.uniform(0, 1),
                     int(rnd.choice([25, 31, 37, 45]))) for _ in range(120)]
        self.sparks = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(500, 1500), int(rnd.choice([31, 41, 55, 71]))) for _ in range(64)]
        self.fires = []
        for _ in range(26):
            ang = rnd.uniform(0, 2 * math.pi)
            rr = rnd.uniform(G_PICK * 0.56, G_PICK * 0.95)
            self.fires.append((ang, rr, int(rnd.uniform(46, 120)), rnd.uniform(2.5, 5), rnd.uniform(0, 1),
                               round(rnd.uniform(-0.6, 0.6) + ang + math.pi / 2, 1), rnd.uniform(0, 1)))
        y, x = np.mgrid[0:300, 0:300].astype(np.float32)
        self.ray_th = np.arctan2(y - 150, x - 150)
        self.ray_r = np.hypot(y - 150, x - 150) * 4
        yq, xq = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
        self.cone_x, self.cone_y = xq * 4 + 2, yq * 4 + 2

    def _facts(self, s):
        """Строки под названием клуба: серия (от 2), результат дома / в гостях, большинство · меньшинство."""
        rec = self.raw[s]
        out = []
        m = re.match(r'\s*(ОТ|В|П)\s*(\d+)', str(rec.get('streak') or ''))
        if m and int(m.group(2)) >= 2:
            n = int(m.group(2))
            word = {'В': plural(n, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'), 'П': plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ'),
                    'ОТ': plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ') + ' В ОТ'}[m.group(1)]
            out.append(('%d %s ПОДРЯД' % (n, word), True))
        home_today = rec.get('home_today')
        if home_today is None:
            home_today = s == 'h'
        vr = rec.get('home_rec' if home_today else 'road_rec')
        mm = re.match(r'\s*(\d+)\D+(\d+)(?:\D+(\d+))?', str(vr or ''))
        if mm:
            wn = int(mm.group(1))
            tot = wn + int(mm.group(2)) + int(mm.group(3) or 0)
            if tot:
                out.append(('%s: %d %s В %d %s' % ('ДОМА' if home_today else 'В ГОСТЯХ', wn, plural(wn, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'),
                                                   tot, 'МАТЧЕ' if tot % 10 == 1 and tot % 100 != 11 else 'МАТЧАХ'), False))
        pp, pk = pct(rec.get('pp')) if rec.get('pp') is not None else None, pct(rec.get('pk')) if rec.get('pk') is not None else None
        sp = ' · '.join(x for x in (('БОЛЬШИНСТВО ' + pp) if pp else '', ('МЕНЬШИНСТВО ' + pk) if pk else '') if x)
        if sp:
            out.append((sp, False))
        return out[:3]

    def _tag_img(self, g):
        """Ценник ювелира на цепочке: холст с точкой подвеса (TAGW/2, 0)."""
        w, h = TAGW, TAGH
        ss = 2
        c = 34
        sh = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(sh)
        pts = [(c, 0), (w - c, 0), (w, c), (w, h - 14), (w - 14, h), (14, h), (0, h - 14), (0, c)]
        d.polygon([(x * ss, y * ss) for x, y in pts], fill=IVORY + (255,))
        ins = 9
        pts2 = [(c + 4, ins), (w - c - 4, ins), (w - ins, c + 4), (w - ins, h - 18), (w - 18, h - ins), (18, h - ins),
                (ins, h - 18), (ins, c + 4)]
        d.line([(x * ss, y * ss) for x, y in pts2 + [pts2[0]]], fill=(196, 152, 70, 255), width=int(2.2 * ss))
        tag = sh.resize((w, h), Image.LANCZOS)
        arr = np.asarray(tag, np.float32).copy()                          # плотная бумага: лёгкий тон сверху вниз
        arr[..., :3] *= np.linspace(1.0, 0.9, h)[:, None, None]
        tag = Image.fromarray(arr.astype(np.uint8), 'RGBA')
        dr = ImageDraw.Draw(tag)
        dr.ellipse((w / 2 - 15, 15, w / 2 + 15, 45), fill=(206, 164, 76, 255))
        dr.ellipse((w / 2 - 10, 20, w / 2 + 10, 40), fill=(244, 216, 146, 255))
        dr.ellipse((w / 2 - 6, 24, w / 2 + 6, 36), fill=(22, 16, 18, 255))
        C.put(tag, C.text(g['opp'].upper(), 'mont', 34, INK, 800, max_w=w - 44), w / 2, 84)
        sub = ' · '.join(x for x in (g['date'], {True: 'ДОМА', False: 'В ГОСТЯХ'}.get(g['home'], '')) if x)
        if sub:
            C.put(tag, C.text(sub, 'mont', 24, (128, 100, 58), 700, track=0.06, max_w=w - 44), w / 2, 121)
        sc = C.text(g['score'], 'yeseva', 94, INK, 400)
        gm = gem(g['res'], 58)
        nt = C.text(g['note'], 'mont', 28, (150, 108, 34), 800) if g['note'] else None
        tw = sc.width + 18 + gm.width + ((nt.width + 8) if nt else 0)
        x0 = (w - tw) / 2
        yc = 192
        C.put(tag, sc, x0, yc - sc.height / 2, anchor='tl')
        x = x0 + sc.width + 8
        if nt:
            C.put(tag, nt, x, yc + sc.height / 2 - nt.height - 4, anchor='tl')
            x += nt.width + 10
        else:
            x += 10
        C.put(tag, gm, x + gm.width / 2, yc)
        out = Image.new('RGBA', (w, CHL - 30 + h), (0, 0, 0, 0))
        out.alpha_composite(tag, (0, CHL - 30))
        ch = self.chain.crop((0, 0, self.chain.width, CHL + 4))
        out.alpha_composite(ch, (int(w / 2 - ch.width / 2), 0))
        Lmax = int(math.hypot(w / 2, out.height)) + 4                     # квадратный холст для качания вокруг подвеса
        sq = Image.new('RGBA', (2 * Lmax, 2 * Lmax), (0, 0, 0, 0))
        sq.alpha_composite(out, (Lmax - w // 2, Lmax))
        return out, sq

    def _plate_img(self, lab, val, sub, vcol):
        pl = metal(PLW, PLH, 18, seed=sum(map(ord, lab)) % 97).copy()
        for x in (26, PLW - 26):                                          # заклёпки
            C.put(pl, sphere(12), x, 22)
        C.put(pl, engraved(lab, 'mont', 24, 800, track=0.14, max_w=PLW - 92), PLW / 2, 32)
        C.put(pl, engraved(val, 'yeseva', 90, 400, max_w=PLW - 40, ink=vcol), PLW / 2, 104)
        if sub:
            C.put(pl, engraved(sub, 'mont', 25, 700, max_w=PLW - 40, ink=(86, 60, 20)), PLW / 2, 162)
        return pl

    def _team_data(self, s):
        tm = self.T[s]
        st = self.st[s]
        tags = [self._tag_img(g) for g in st['games'][:3]]
        plates = []
        if st['points'] is not None:
            sub = ('за %d %s' % (st['gp'], plural(st['gp'], 'матч', 'матча', 'матчей'))) if st['gp'] is not None else ''
            plates.append(self._plate_img('ОЧКИ', '%d' % st['points'], sub, INK))
        if st['place'] is not None:
            plates.append(self._plate_img('МЕСТО', '%d' % st['place'], st['place_scope'], INK))
        if st['gd'] is not None:
            vc = (14, 96, 52) if st['gd'] > 0 else (140, 18, 30) if st['gd'] < 0 else INK
            plates.append(self._plate_img('РАЗНИЦА ШАЙБ', F.gd_txt(st['gd']), '', vc))
        plates = [(p, reflection(p)) for p in plates[:3]]
        facts = []
        for txt, hot in self._facts(s):
            facts.append(C.text(txt, 'mont', 30 if hot else 27, (255, 214, 200) if hot else CHAMP, 700, max_w=610))
        name = gold_text(tm.up, 'yeseva', 100, max_w=620)
        role = C.text('ХОЗЯЕВА' if s == 'h' else 'ГОСТИ', 'mont', 28, GOLDT, 700, track=0.34)
        return dict(tags=tags, plates=plates, facts=facts, name=name, role=role)

    def _pick_plate(self):
        w, h = 960, 382
        pl = metal(w, h, 26, bevel=11, seed=21).copy()
        for x in (34, w - 34):
            C.put(pl, sphere(16), x, 30)
        m = re.match(r'(ПОБЕДА)\s+(.+)$', self.pick1)
        top, main = (m.group(1), m.group(2)) if m else ('', self.pick1)
        y = 50
        if top:
            C.put(pl, engraved(top, 'mont', 42, 800, track=0.34), w / 2, 54)
        mi = engraved(main, 'yeseva', 124, 400, max_w=880)
        C.put(pl, mi, w / 2, 140)
        if self.pick2:
            C.put(pl, engraved(self.pick2, 'mont', 34, 800, track=0.2, max_w=860, ink=(86, 58, 16)), w / 2, 228)
        if self.coef:
            kt = gold_text('КЭФ ' + C.fmt_k(self.coef), 'yeseva', 70, stroke=0)
            kp = onyx(kt.width + 120, 104, 52, rim=6).copy()
            C.put(kp, kt, kp.width / 2, 54)
            C.put(pl, kp, w / 2, 310)
        return pl

    # ── время ──
    def phase(self, t):
        """Фаза вращения подвесов: спокойно до интриги, на интриге всё быстрее (непрерывно)."""
        u, f0, f1 = self.u, 1 / (4 * self.u), 1 / self.u
        if t < self.tp:
            return 2 * math.pi * f0 * t
        Tp = self.pre * u
        x = min(t, self.drop) - self.tp
        return 2 * math.pi * (f0 * self.tp + f0 * x + (f1 - f0) * x * x / (2 * Tp))

    def yaw(self, t, k=0.0):
        ph = self.phase(t) + k
        if self.tp <= t < self.drop:
            amp = C.lerp(24, 72, C.in_cubic(C.seg(t, self.tp, self.drop)))
        else:
            amp = 24
        return math.radians(amp) * math.sin(ph)

    def pendants(self, t):
        """[(сторона, x, центр y, диаметр, поворот, видимость 0..1 «опущен с перекладины», лёд)] на момент t."""
        u, D = self.u, self.drop
        T1, T2, TP = self.t1, self.t2, self.tp
        out = []
        idd, icy = self.i_d, self.i_cy
        tcy = RAIL_Y + 10 + 0.61 * G_TEAM
        pcy = max(700, RAIL_Y + 10 + 0.61 * G_PRE)
        if t >= D:
            k = C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.5))
            dd = C.lerp(G_PICK, G_CTA, k)
            cy = C.lerp(RAIL_Y + 14 + 0.61 * G_PICK, RAIL_Y + 14 + 0.61 * G_CTA, k)
            pop = C.lerp(1.2, 1.0, C.out_back(C.seg(t, D, D + 0.42), 2.2))
            ywa = math.radians(14) * math.sin(2 * math.pi * (t - D) / (6 * u) - 0.6)
            out.append((self.side, W / 2, cy + (pop - 1) * 0.3 * dd, dd * pop, ywa, 1.0, True))
            return out
        land0 = u / 2
        low = lambda tl, dl=0.32: C.out_back(C.seg(t, tl - dl, tl + 0.08), 1.5)       # опускание с перекладины
        rise = lambda a, b: 1 - C.in_cubic(C.seg(t, a, b))
        # хозяева
        if t < T2:
            k = C.in_out(C.seg(t, T1 - 0.3, T1 + 0.06))
            x, cy, dd = C.lerp(270, X_TEAM, k), C.lerp(icy, tcy, k), C.lerp(idd, G_TEAM, k)
            vis = low(land0, land0) * rise(T2 - 0.52, T2 - 0.26)
            out.append(('h', x, cy, dd, self.yaw(t), vis, False))
        elif t >= TP - 0.26:
            out.append(('h', 270, pcy, G_PRE, self.yaw(t, 1.3), low(TP), False))
        # гости
        if t < T1:
            out.append(('a', 810, icy, idd, self.yaw(t, 2.1), low(land0, land0) * rise(T1 - 0.46, T1 - 0.18), False))
        elif t >= T2 - 0.26:
            k = C.in_out(C.seg(t, TP - 0.52, TP - 0.2))
            x, cy, dd = C.lerp(X_TEAM, 810, k), C.lerp(tcy, pcy, k), C.lerp(G_TEAM, G_PRE, k)
            out.append(('a', x, cy, dd, self.yaw(t, 2.1), low(T2), False))
        return out

    # ── рисование ──
    def draw_pendant(self, fr, s, x, cy, dd, yw, vis, iced):
        md = self.ice if iced else medal(self.T[s], G_PRE)
        d0, m = md['d'], md['m']
        sc = dd / d0
        cs = max(0.08, abs(math.cos(yw)))
        piv = cy - (m + d0 / 2) * sc                                     # точка подвеса (верх ушка)
        full_h = (d0 + m) * sc
        py = piv - (1 - vis) * (full_h + piv - RAIL_Y + 12)              # поднят — спрятан за перекладиной
        L = int(py - RAIL_Y)
        if L > 0:
            ch = (self.ichain if iced else self.chain)
            ch = ch.crop((0, 0, ch.width, min(ch.height, L + 4)))
            C.put(fr, ch, x - ch.width / 2, RAIL_Y, anchor='tl')
        if py + full_h <= RAIL_Y + 6:
            return
        ph = 0.5 - 0.62 * math.sin(yw) + 0.06 * math.sin(self._t * 0.9)
        kk = int(round(C.clamp((ph + 0.25) / 1.5) * (K_SWEEP - 1)))
        ww, hh = max(2, int(round(d0 * sc * cs))), max(2, int(round(full_h)))
        face = md['var'][kk].resize((ww, hh), Image.BILINEAR)
        top = int(round(py))
        if abs(math.sin(yw)) > 0.05:                                     # торец медальона при повороте
            eg = md['edge'].resize((ww, hh), Image.BILINEAR)
            th = 0.05 * dd * math.sin(yw)
            for f in (1.0, 0.66, 0.33):
                self._put_clip(fr, eg, x - ww / 2 + th * f, top)
        self._put_clip(fr, face, x - ww / 2, top)

    def _put_clip(self, fr, im, x0, y0, a=1.0, clip=RAIL_Y + 3):
        """Положить im левым верхним углом в (x0, y0), срезав всё выше линии clip (за перекладиной)."""
        y0 = int(round(y0))
        if y0 < clip:
            cut = clip - y0
            if cut >= im.height:
                return
            im = im.crop((0, cut, im.width, im.height))
            y0 = clip
        C.put(fr, im, x0, y0, a, anchor='tl')

    def draw_rail2(self, fr, t):
        T1, TP = self.t1, self.tp
        if t < T1 - 0.16 or t >= TP - 0.1:
            return 0.0
        k = C.out_expo(C.seg(t, T1 - 0.16, T1 + 0.24)) * (1 - C.in_cubic(C.seg(t, TP - 0.42, TP - 0.1)))
        if k <= 0.01:
            return k
        w = max(2, int(self.rail2.width * k))
        im = self.rail2.crop(((self.rail2.width - w) // 2, 0, (self.rail2.width + w) // 2, self.rail2.height))
        C.put(fr, im, W / 2, RAIL2_Y, k ** 0.5)
        return k

    def swing(self, t, tl, j):
        """Угол ценника (град.): качание после спуска + толчок на каждой следующей доле."""
        sg = 1 if j % 2 == 0 else -1
        x = t - tl
        if x < 0:
            return 0.0
        a = 7.5 * sg * math.exp(-x / 0.75) * math.sin(2 * math.pi * x / 0.9)
        n = math.floor((t - self.drop) / self.u + 1e-6)
        for q in (n, n - 1):
            tb = self.b(q)
            if tb > tl + 0.05 and t >= tb:
                y = t - tb
                a += 1.8 * (1 if q % 2 else -1) * sg * math.exp(-y / 0.4) * math.sin(2 * math.pi * y / 0.9)
        return a

    def team_items(self, fr, t, s, ts, te, lights):
        u = self.u
        td = self.TD[s]
        # название и факты
        qa = C.out_cubic(C.seg(t, ts - 0.06, ts + 0.3)) * (1 - C.seg(t, te - 0.56, te - 0.32))
        if qa > 0.01:
            dx = 70 * (1 - C.out_cubic(C.seg(t, ts - 0.06, ts + 0.3))) - 50 * C.in_cubic(C.seg(t, te - 0.56, te - 0.32))
            nf = len(td['facts'])
            y_name = 520 - 14 * (3 - nf)
            C.put(fr, td['role'], NAME_X + dx, y_name - 74, qa)
            C.put(fr, td['name'], NAME_X + dx, y_name, qa)
            qf = C.out_cubic(C.seg(t, ts + 0.5 * u - 0.08, ts + 0.5 * u + 0.28)) * qa
            for i, im in enumerate(td['facts']):
                C.put(fr, im, NAME_X + dx * 0.6, y_name + 82 + 46 * i + 12 * (1 - qf), qf)
        # ценники на цепочках
        for j, (hang, sq) in enumerate(td['tags']):
            tl = ts + (j + 1) * u
            if t < tl - 0.3:
                continue
            ax = SLOT_X[j]
            down = C.seg(t, tl - 0.26, tl) ** 2
            up = C.in_cubic(C.seg(t, te - 0.42 + 0.04 * j, te - 0.12 + 0.04 * j))
            off = -(hang.height + 6) * ((1 - down) + up)
            if t >= tl and up <= 0:
                ang = self.swing(t, tl, j)
                bounce = -7 * math.exp(-(t - tl) / 0.09) * math.sin(2 * math.pi * (t - tl) / 0.28)
                if abs(ang) > 0.08:
                    im = sq.rotate(ang, Image.BICUBIC)
                    C.put(fr, im, ax, RAIL2_Y + bounce)
                else:
                    C.put(fr, hang, ax - TAGW / 2, RAIL2_Y + bounce, anchor='tl')
                if t - tl < 0.35:
                    lights.append(('star', 150, ax + 104, RAIL2_Y + 72, 0.9 * math.exp(-(t - tl) / 0.12)))
            else:
                self._put_clip(fr, hang, ax - TAGW / 2, RAIL2_Y + off, clip=RAIL2_Y + 2)
            C.put(fr, self.hookim, ax, RAIL2_Y + 4)
        # таблички на полке
        for j, (pl, rf) in enumerate(td['plates']):
            tl = ts + (4 + j) * u
            if t < tl - 0.2:
                continue
            fall = C.seg(t, tl - 0.2, tl) ** 2
            ex = C.in_cubic(C.seg(t, te - 0.42, te - 0.14))
            a = C.seg(t, tl - 0.2, tl - 0.1) * (1 - ex)
            y = SHELF_Y - 4 - PLH / 2 - 150 * (1 - fall) + 50 * ex
            if t >= tl:
                y -= 9 * abs(math.sin(2 * math.pi * (t - tl) / 0.36)) * math.exp(-(t - tl) / 0.12)
            C.put(fr, pl, SLOT_X[j], y, a)
            if t >= tl - 0.02:
                C.put(fr, rf, SLOT_X[j], SHELF_Y + 12 + rf.height / 2, a * (1 - ex))
            if 0 <= t - tl < 0.4:
                lights.append(('star', 170, SLOT_X[j] + PLW / 2 - 24, y - PLH / 2 + 10, 1.0 * math.exp(-(t - tl) / 0.13)))

    def intro_items(self, fr, t, lights):
        u, T1 = self.u, self.t1
        ex = C.in_cubic(C.seg(t, T1 - 0.46, T1 - 0.16))
        q = C.out_cubic(C.seg(t, 0.22, 0.56)) * (1 - ex)
        if q > 0.01:
            yb = self.i_cy + self.i_d / 2
            for s, x in (('h', 270), ('a', 810)):
                C.put(fr, self.i_role[s], x, yb + 54 + 16 * (1 - q), q)
                C.put(fr, self.i_name[s], x, yb + 110 + 16 * (1 - q), q)
        # бриллиант-подвеска между медальонами
        k = C.out_back(C.seg(t, 0.12, 0.5), 1.4) * (1 - ex)
        if k > 0.01:
            y = self.i_cy - 30 - 260 * (1 - k)
            L = int(y - 42 - RAIL_Y)
            if L > 0:
                ch = self.chain.crop((0, 0, self.chain.width, L))
                C.put(fr, ch, W / 2 - ch.width / 2, RAIL_Y, anchor='tl')
            if y - 42 > RAIL_Y:
                C.put(fr, self.orn, W / 2, y)
        # линия П1 · Х · П2 на полке — по плашке на полдоли
        if self.odds:
            qa = C.seg(t, 0.4, 0.7) * (1 - ex)
            C.put(fr, self.odds_lab, W / 2, SHELF_Y - ODH - 52, qa)
            for j, (pl, rf) in enumerate(self.odds):
                tl = u * (1 + 0.5 * j)
                if t < tl - 0.2:
                    continue
                fall = C.seg(t, tl - 0.2, tl) ** 2
                a = C.seg(t, tl - 0.2, tl - 0.1) * (1 - ex)
                y = SHELF_Y - 4 - ODH / 2 - 150 * (1 - fall) + 50 * ex
                if t >= tl:
                    y -= 9 * abs(math.sin(2 * math.pi * (t - tl) / 0.36)) * math.exp(-(t - tl) / 0.12)
                C.put(fr, pl, SLOT_X[j], y, a)
                if t >= tl - 0.02:
                    C.put(fr, rf, SLOT_X[j], SHELF_Y + 12 + rf.height / 2, a)
                if 0 <= t - tl < 0.4:
                    lights.append(('star', 170, SLOT_X[j] + ODW / 2 - 22, y - ODH / 2 + 12, 1.0 * math.exp(-(t - tl) / 0.13)))

    def cone(self, fr, t):
        """Луч софита (интрига — сужается к центру, прогноз — узкий на медальоне) + затемнение вокруг."""
        D, TP = self.drop, self.tp
        if t < TP:
            return
        if t < D:
            k = C.in_out(C.seg(t, TP, D))
            hw_top, hw_bot, veil, lite, cx = C.lerp(330, 90, k), C.lerp(620, 170, k), C.lerp(0.0, 0.55, k), C.lerp(0.10, 0.2, k), W / 2
        else:
            kc = C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.5))
            hw_top, hw_bot, veil, lite, cx = 150, C.lerp(560, 600, kc), 0.32 * (1 - kc), 0.14, W / 2
        x, y = self.cone_x, self.cone_y
        hw = hw_top + (hw_bot - hw_top) * (y / H)
        c = np.clip(1.25 - np.abs(x - cx) / hw, 0, 1) ** 1.6 * (0.55 + 0.45 * np.exp(-y / 900))
        a_l = lite * c
        a_v = veil * (1 - c)
        a = a_l + a_v * (1 - a_l)
        col = np.zeros(c.shape + (4,), np.float32)
        col[..., :3] = np.array(WARM, np.float32) * (a_l / np.maximum(a, 1e-4))[..., None]
        col[..., 3] = a * 255
        lay = Image.fromarray(col.astype(np.uint8), 'RGBA').resize((W, H), Image.BILINEAR)
        fr.alpha_composite(lay)

    def rays(self, fr, t, cx, cy, k):
        """Лучи света из-за медальона «во льду» (медленно вращаются)."""
        if k <= 0.01:
            return
        th = self.ray_th - (t - self.drop) * 0.16
        I = (0.6 * (0.5 + 0.5 * np.cos(14 * th)) ** 7 + 0.45 * (0.5 + 0.5 * np.cos(9 * th + 1.3)) ** 11
             + 0.3 * (0.5 + 0.5 * np.cos(23 * th + 0.4)) ** 15)
        r = self.ray_r
        I = I * np.exp(-r / 420) * np.clip((r - 150) / 90, 0, 1) * k
        col = np.zeros(I.shape + (4,), np.float32)
        col[..., :3] = WARM
        col[..., 3] = np.clip(I * 255, 0, 255)
        lay = Image.fromarray(col.astype(np.uint8), 'RGBA').resize((1200, 1200), Image.BILINEAR)
        C.put(fr, lay, cx, cy)

    def frame(self, t):
        self._t = t
        u, D = self.u, self.drop
        T1, T2, TP, TC = self.t1, self.t2, self.tp, self.t_cta
        fr = self.bg.copy()
        lights = []
        # свет под предметами
        pend = self.pendants(t)
        if t >= D:
            s, x, cy, dd, yw, vis, iced = pend[0]
            rk = C.seg(t, D, D + 0.18) * (0.85 + 0.15 * math.sin(t * 3.1))
            n = math.floor((t - D) / u + 1e-6)
            rk += 0.35 * math.exp(-(t - self.b(n)) / 0.25)
            self.rays(fr, t, x, cy, rk)
        self.cone(fr, t)
        # перекладина, подвесы
        for s, x, cy, dd, yw, vis, iced in pend:
            self.draw_pendant(fr, s, x, cy, dd, yw, vis, iced)
        C.put(fr, self.rail1, W / 2, RAIL_Y)
        # полка
        kc = C.in_out(C.seg(t, TC, TC + 0.5))
        shy = SHELF_Y - 120 * kc
        C.put(fr, self.shelf, W / 2, shy - 10 + self.shelf.height / 2, C.seg(t, 0.0, 0.3))
        # сцены
        if t < T1:
            self.intro_items(fr, t, lights)
        if T1 - 0.2 <= t < TP:
            self.draw_rail2(fr, t)
            if t < T2:
                self.team_items(fr, t, 'h', T1, T2, lights)
            else:
                self.team_items(fr, t, 'a', T2, TP, lights)
        if TP - 0.26 <= t < D:
            q = C.out_cubic(C.seg(t, TP, TP + 0.3))
            for s, x in (('h', 270), ('a', 810)):
                C.put(fr, self.p_name[s], x, 700 + G_PRE / 2 + 80 + 14 * (1 - q), q)
        if t >= D:
            ts = t - D
            k = C.seg(t, D, D + 0.16)
            sc = C.lerp(1.0, 0.86, kc)
            pl = self.pick_pl if sc > 0.995 else C.scale(self.pick_pl, sc)
            rf = self.pick_refl if sc > 0.995 else C.scale(self.pick_refl, sc)
            y = shy - 4 - pl.height / 2 - 170 * (1 - k * k)
            if ts > 0.16:
                y -= 12 * abs(math.sin(2 * math.pi * (ts - 0.16) / 0.4)) * math.exp(-(ts - 0.16) / 0.14)
            C.put(fr, pl, W / 2, y, C.seg(t, D, D + 0.07))
            if ts > 0.14:
                C.put(fr, rf, W / 2, shy + 12 + rf.height / 2)
        # шапка и подпись
        a0 = C.seg(t, 0, 0.3)
        C.put(fr, self.tag, W / 2, TAG_Y, a0)
        C.put(fr, self.date, W / 2, DATE_Y, a0)
        ha = C.seg(t, 0.15, 0.45) * (1 - C.seg(t, TC, TC + 0.2))
        C.put(fr, self.handle, W / 2, HY, ha)
        if t >= TC:
            q = C.out_expo(C.seg(t, TC + 0.05, TC + 0.5))
            C.put(fr, self.tg, W / 2, 1372 + 60 * (1 - q), q)
        # ── свет: блики на долях, блёстки, вспышка ──
        arr = np.asarray(fr.convert('RGB'), np.float32)
        nb = math.floor((t - D) / u + 1e-6)
        for q in (nb, nb - 1):
            tb = self.b(q)
            e = math.exp(-(t - tb) / 0.2) * C.seg(t, tb - 0.03, tb + 0.02)
            if e < 0.02 or tb < 0.3:
                continue
            rr = np.random.default_rng(int(q) + 500)
            for s, x, cy, dd, yw, vis, iced in pend:
                if vis < 0.9:
                    continue
                if iced:
                    st = self.ice['stones']
                    sc_ = dd / G_PICK
                    for i in rr.choice(len(st), 6, replace=False):
                        sx, sy, sz = st[i]
                        addl(arr, star(int(150 + 120 * rr.random())), x + (sx - G_PICK / 2) * sc_ * abs(math.cos(yw)),
                             cy + (sy - self.ice['m'] - G_PICK / 2) * sc_, 1.2 * e)
                else:
                    for _ in range(2):
                        ang = rr.uniform(math.pi * 1.05, math.pi * 1.95)
                        addl(arr, star(int(dd * 0.55)), x + 0.93 * dd / 2 * math.cos(ang) * abs(math.cos(yw)),
                             cy + 0.93 * dd / 2 * math.sin(ang), 0.95 * e)
        if TP <= t < D:                                                  # интрига: блики на полудолях всё чаще
            kq = C.seg(t, TP, D)
            step = u / 2 if kq < 0.5 else u / 4
            tb = D - math.ceil((D - t) / step - 1e-6) * step
            tb = tb if tb <= t else tb - step
            e = math.exp(-(t - tb) / 0.12)
            rr = np.random.default_rng(int(tb * 1000) % 100000)
            for s, x, cy, dd, yw, vis, iced in pend:
                ang = rr.uniform(math.pi * 1.0, math.pi * 2.0)
                addl(arr, star(int(dd * 0.5)), x + 0.9 * dd / 2 * math.cos(ang) * abs(math.cos(yw)), cy + 0.9 * dd / 2 * math.sin(ang),
                     (0.6 + 0.6 * kq) * e)
        # блёстки на бархате
        n_act = 40 if t < TP else int(C.lerp(40, 120, C.seg(t, TP, D))) if t < D else 70
        speed = 1.0 + (2.2 * C.seg(t, TP, D) if TP <= t < D else 0.0)
        for i, (x, y, p, ph, S) in enumerate(self.twk[:n_act]):
            bb = math.sin(2 * math.pi * (t * speed / p + ph))
            if bb > 0.9:
                addl(arr, star(S), x, y, 0.55 * ((bb - 0.9) / 0.1) ** 2)
        for kind, S, x, y, kk in lights:
            addl(arr, star(S), x, y, kk)
        if t >= D:
            ts = t - D
            s, x, cy, dd, yw, vis, iced = pend[0]
            if ts < 1.0:                                                 # разлёт алмазной пыли
                for ang, sp, S in self.sparks:
                    r = sp * ts * (1 - 0.38 * ts)
                    addl(arr, star(S), x + r * math.cos(ang), cy + r * math.sin(ang) + 240 * ts * ts, 1.1 * (1 - ts) ** 1.5)
            fk = C.seg(t, D + 0.2, D + 0.6) * (1 - C.seg(t, TC, TC + 0.3) * 0.6)
            if fk > 0.01:                                                # «игра» бриллиантов — цветные отблески вокруг
                for ang, rr_, L, th, ph, a2, sp in self.fires:
                    fl = 0.5 + 0.5 * math.sin(2 * math.pi * (t * (0.5 + sp) + ph))
                    sc_ = dd / G_PICK
                    addl(arr, fire(L, th, round(ph, 2), a2), x + rr_ * sc_ * math.cos(ang), cy + rr_ * sc_ * math.sin(ang),
                         0.5 * fk * fl ** 2)
            if ts < 0.34:                                                # вспышка граней
                fk = (1 - ts / 0.34) ** 2 * 1.15
                arr += flash_f(W / 2, RAIL_Y + 14 + 0.61 * G_PICK)[..., None] * (np.array((255, 246, 226), np.float32) * fk)
        arr *= vignette_f()
        arr += grain_f(int(t * 24))[..., None]
        out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
        # камера: наезд на интриге, удар на дропе, лёгкие толчки на склейках
        z, dx, dy = 1.0, 0.0, 0.0
        if TP <= t < D:
            z += 0.035 * C.in_cubic(C.seg(t, TP, D))
        if t >= D:
            z += 0.07 * (1 - C.seg(t, D, D + 0.4)) ** 2
            sx, sy = C.shake(t, D, 16, 0.38)
            dx, dy = dx + sx, dy + sy
        for th in (T1, T2):
            if th <= t < th + 0.3:
                z += 0.014 * (1 - C.seg(t, th, th + 0.3)) ** 2
        if z > 1.0005 or dx or dy:
            out = C.zoom(out, z, W / 2, 700, dx, dy)
        return out
