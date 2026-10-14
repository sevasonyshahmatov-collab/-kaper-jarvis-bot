# -*- coding: utf-8 -*-
"""«Пинбол» — неоновый пинбольный стол глазами игрока (трек «Gem», первый дроп): крутая перспектива игрового поля
с глянцевым артом в цветах клуба, хромированные борта, светящиеся бамперы, мишени и рогатки над флипперами; сверху —
бэкгласс автомата с точечным (dot-matrix) табло. Стальной шарик бьёт по мишеням — и каждая мишень загорается одним
фактом на крупной плашке в стиле бэкгласса. Не гонка, не радар, не кассета — игровой автомат (без «казино» и «джекпотов»).

Сцены (u — доля трека, D — дроп; доли считаются от дропа; team / pre / hold / cta — параметры из reels_cfg):
  интро (до D − (2·team + pre) долей) — бэкгласс с обеими эмблемами, названиями и ролями, на табло лига, день и время
                 МСК; на поле — линия основного времени П1 · Х · П2 тремя крупными плашками-мишенями: шарик вылетает
                 из пускового жёлоба и на долях зажигает П1, Х, П2; на склейке флиппер отбивает шарик в следующую сцену;
  команда (team долей) ×2 — стол в цвете клуба, эмблема и название на бэкглассе («ХОЗЯЕВА» / «ГОСТИ» на табло);
                 склейка — толчок стола (наклон и тряска) ровно на доле, флиппер отбивает шарик; дальше на каждой
                 половине доли шарик бьёт очередную цель: три мишени — последние 3 игры (соперник, дата, счёт, ОТ/Б,
                 В/П цветом), три бампера — очки за N матчей, место, разница шайб, две рогатки — серия (от 2 игр)
                 и большинство / меньшинство (если есть). Зажжённое остаётся до конца сцены; затем шарик просто
                 играет по бамперам на долях (успеть прочитать);
  разгон (pre долей) — факты гаснут, шарик скатывается по дорожке к флипперу, огни бегут по бортам всё быстрее,
                 флипперы «наготове» вздрагивают на половинах доли, камера наезжает;
  ДРОП (hold долей) — ровно на дропе флиппер бьёт, шарик улетает по рампе в бэкгласс, весь стол вспыхивает в цвете
                 команды прогноза: бэкгласс вырастает, огромная эмблема только этой команды (без второй и без «VS»),
                 на табло «ПОБЕДА …» и «В ОСНОВНОЕ ВРЕМЯ», через долю — плашка с кэфом; огни пульсируют на долях;
  финал (cta долей) — снизу плашка Telegram (C.tg_plate, текст по центру плашки).
@jarvibet — на фартуке стола у низа безопасной зоны (y 1452), одинаково во всех сценах до плашки Telegram.
Кадр зависит только от t: траектория шарика — ключевые точки на долях, всё статичное (столы, бамперы, плашки,
табло) кешируется в словарях модуля.
"""
import colorsys
import math
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels.core import W, H

WHITE = (255, 255, 255)
GRAY = (176, 170, 196)
INK = (12, 8, 22)
NEUT = (196, 92, 255)             # неон интро: фиолетовый
NEUT2 = (60, 220, 255)            # второй неон интро: голубой
AMBER = (255, 142, 36)            # точечное табло
TAG_Y, HY = 260, 1452
PF_TOP, PF_BOT = 536, 1428        # игровое поле (трапеция)
PF_TX0, PF_TX1 = 118, 962         # верхняя кромка поля
PF_BX0, PF_BX1 = -16, 1096        # нижняя кромка поля
BG_X0, BG_X1, BG_Y0 = 34, 1046, 290   # бэкгласс
BGB_INTRO, BGB_TEAM, BGB_PICK = 800, 528, 1004
PITCH = 5                         # шаг точек табло
FL_PIV = {'L': (300.0, 1318.0), 'R': (780.0, 1318.0)}
FL_LEN, FL_REST, FL_UP = 200.0, 24.0, -27.0
GAME_C = ((206, 652), (540, 652), (874, 652))
GAME_WH = (318, 190)
BUMP_C = ((290, 902), (790, 902), (540, 1106))
BUMP_W, BUMP_H = 262, 226
SLING_C = ((182, 1186), (898, 1186))
SLING_WH = (308, 116)
LINE_C = ((200, 978), (540, 978), (880, 978))
LINE_WH = (318, 214)
PLUNGER = (1040.0, 1404.0)
_CACHE = {}


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def neon(c, v_min=0.92, s_min=0.6):
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    s = min(0.92, max(s, s_min)) if s > 0.12 else s
    v = max(v, v_min)
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, s, v))


def club(t, avoid=None):
    cand = [c for c in (t.c1, t.c0, t.c2) if (max(c) - min(c)) / 255 > 0.2 and 40 < 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] < 235]
    cand = [neon(c) for c in cand] or [neon(t.c1)]
    if avoid is not None:
        far = [c for c in cand if sum((a - b) ** 2 for a, b in zip(c, avoid)) ** 0.5 > 120]
        if far:
            return far[0]
    return cand[0]


def dark(col, v=0.32, s_k=1.0):
    h, s, _ = colorsys.rgb_to_hsv(*(x / 255 for x in col))
    return tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, min(1, s * s_k), v))


def pct(v):
    try:
        return ('%.1f' % float(v)).rstrip('0').rstrip('.').replace('.', ',') + '%'
    except (TypeError, ValueError):
        return None


def cached(key, fn):
    if key not in _CACHE:
        _CACHE[key] = fn()
    return _CACHE[key]


def tinted(mask, col, k=1.0):
    lay = Image.new('RGBA', mask.size, tuple(col) + (0,))
    lay.putalpha(mask if k == 1.0 else mask.point(lambda v: min(255, int(v * k))))
    return lay


# ─────────────────────────────── геометрия поля ───────────────────────────────
def pf_x(y, side):
    """x кромки поля на высоте y (side −1 — левая, +1 — правая)."""
    k = (y - PF_TOP) / (PF_BOT - PF_TOP)
    return C.lerp(PF_TX0, PF_BX0, k) if side < 0 else C.lerp(PF_TX1, PF_BX1, k)


def persp_coeffs(dst, src):
    """Коэффициенты PIL PERSPECTIVE: точка выхода dst → точка источника src (по 4 парам)."""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        B += [u, v]
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def ball_d(y):
    return 40 + 18 * C.clamp((y - PF_TOP) / (PF_BOT - PF_TOP))


# ─────────────────────────────── точечное табло ───────────────────────────────
def dot_tile(p):
    yy, xx = np.mgrid[0:p, 0:p].astype(np.float32)
    r = np.hypot(xx - (p - 1) / 2, yy - (p - 1) / 2)
    return np.clip(p * 0.44 - r + 0.5, 0, 1)


def dmd_text(s, size, col=AMBER, max_w=None, font='russo', wght=400, track=0.06):
    """Строка на точечном табло: шрифт → сетка точек шага PITCH (яркость точки = заполнение ячейки) + ореол."""
    key = ('dmd', s, int(size), col, max_w, font, track)
    if key in _CACHE:
        return _CACHE[key]
    im = C.text(s, font, size, WHITE, wght, track=track, max_w=max_w)
    a = np.asarray(im.getchannel('A'), np.float32) / 255
    p = PITCH
    gh, gw = -(-a.shape[0] // p) + 2, -(-a.shape[1] // p) + 2
    big = np.zeros((gh * p, gw * p), np.float32)
    big[p:p + a.shape[0], p:p + a.shape[1]] = a
    cells = big.reshape(gh, p, gw, p).mean((1, 3))
    lit = np.clip((cells - 0.18) / 0.42, 0, 1)
    dots = np.kron(lit, dot_tile(p))
    m = Image.fromarray((dots * 255).astype(np.uint8), 'L')
    pad = 14
    mm = Image.new('L', (m.width + 2 * pad, m.height + 2 * pad), 0)
    mm.paste(m, (pad, pad))
    out = tinted(mm.filter(ImageFilter.GaussianBlur(7)), col, 0.9)
    out.alpha_composite(tinted(mm, C.mix(col, WHITE, 0.28)))
    _CACHE[key] = (out, pad)
    return out, pad


def dmd_panel(w, h, col=AMBER):
    """Пустое табло: чёрное стекло с погасшими точками и хромированной рамкой."""
    def mk():
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        fr = C.rrect(w, h, 18, (150, 150, 165), outline=(235, 235, 245), width=3)
        im.alpha_composite(fr)
        inner = C.rrect(w - 12, h - 12, 13, (10, 6, 4))
        im.alpha_composite(inner, (6, 6))
        gy, gx = (h - 24) // PITCH, (w - 24) // PITCH
        dots = np.kron(np.ones((gy, gx), np.float32), dot_tile(PITCH)) * 0.16
        m = Image.fromarray((dots * 255).astype(np.uint8), 'L')
        im.alpha_composite(tinted(m, col), (12, 12))
        gl = C.lgrad(w - 12, (h - 12) // 2, (255, 255, 255), (255, 255, 255), 90, 22, 0)
        im.alpha_composite(gl, (6, 6))
        return im
    return cached(('dmdp', w, h, col), mk)


# ─────────────────────────────── спрайты ───────────────────────────────
def ball_sprite(d, rim=(255, 255, 255)):
    d = int(d) // 2 * 2
    key = ('ball', d, rim)
    if key in _CACHE:
        return _CACHE[key]
    ss = 3
    n = d * ss
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x, y = (xx - n / 2 + 0.5) / (n / 2), (yy - n / 2 + 0.5) / (n / 2)
    r = np.hypot(x, y)
    z = np.sqrt(np.clip(1 - r ** 2, 0, 1))
    # хром: отражение «неба» сверху, тёмный горизонт, пол снизу, блик слева сверху, цветной контровой свет
    ny = y
    env = np.where(ny < 0.05, 205 - 120 * (ny + 1) * 0.5, 70 + 90 * np.clip(ny, 0, 1))
    env = env * (0.55 + 0.45 * z)
    spec = np.exp(-(((x + 0.36) ** 2 + (y + 0.42) ** 2) / 0.035)) * 255
    rimk = np.clip((r - 0.72) / 0.28, 0, 1) ** 2 * (y > -0.2)
    rgb = np.stack([env] * 3, -1)
    rgb = rgb * (1 - rimk[..., None] * 0.6) + np.array(rim, np.float32) * rimk[..., None] * 0.6
    rgb = np.clip(rgb + spec[..., None], 0, 255)
    a = np.clip((1 - r) * n / 2, 0, 1) * 255
    arr = np.concatenate([rgb, a[..., None]], -1).astype(np.uint8)
    im = Image.fromarray(arr, 'RGBA').resize((d, d), Image.LANCZOS)
    _CACHE[key] = im
    return im


def flipper_sprite(col):
    """Флиппер: широкое основание у оси, узкий кончик; белый пластик и резинка в цвете клуба. Ось — в центре картинки."""
    def mk():
        ss = 3
        S = int(FL_LEN * 2 + 80)
        im = Image.new('RGBA', (S * ss, S * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = S * ss / 2
        r0, r1, L = 30 * ss, 15 * ss, FL_LEN * ss

        def shape(dr, e, fill):
            a = math.asin((r0 - r1) / L)
            pts = [(c + math.sin(a) * (r0 + e), c - math.cos(a) * (r0 + e)), (c + L + math.sin(a) * (r1 + e), c - math.cos(a) * (r1 + e)),
                   (c + L + math.sin(a) * (r1 + e), c + math.cos(a) * (r1 + e)), (c + math.sin(a) * (r0 + e), c + math.cos(a) * (r0 + e))]
            dr.polygon(pts, fill=fill)
            dr.ellipse((c - r0 - e, c - r0 - e, c + r0 + e, c + r0 + e), fill=fill)
            dr.ellipse((c + L - r1 - e, c - r1 - e, c + L + r1 + e, c + r1 + e), fill=fill)
        shape(d, 6 * ss, tuple(col) + (255,))
        shape(d, 0, (238, 236, 244, 255))
        d.ellipse((c - 11 * ss, c - 11 * ss, c + 11 * ss, c + 11 * ss), fill=(150, 150, 170, 255))
        d.ellipse((c - 5 * ss, c - 5 * ss, c + 5 * ss, c + 5 * ss), fill=(235, 235, 245, 255))
        im = im.resize((S, S), Image.LANCZOS)
        return C.glow(im, 9, 0.7, col)
    return cached(('flip', col), mk)


def bumper_sprite(col, lit):
    """Поп-бампер: тень, цилиндр-юбка в цвете клуба, кольцо огней, тёмная глянцевая шапка с хромом. lit — огни горят."""
    def mk():
        w, hh = BUMP_W, BUMP_H
        sk = 40
        S = (w + 120, hh + sk + 120)
        im = Image.new('RGBA', S, (0, 0, 0, 0))
        cx, cy = S[0] / 2, 60 + hh / 2
        sh = C.ellipse(w + 30, int(hh * 0.62), (0, 0, 0), 150)
        C.put(im, sh.filter(ImageFilter.GaussianBlur(10)), cx + 14, cy + sk + hh * 0.18)
        # юбка
        body = Image.new('RGBA', S, (0, 0, 0, 0))
        dk = dark(col, 0.42)
        bd = ImageDraw.Draw(body)
        bd.ellipse((cx - w / 2, cy + sk - hh / 2, cx + w / 2, cy + sk + hh / 2), fill=dk + (255,))
        bd.rectangle((cx - w / 2, cy, cx + w / 2, cy + sk), fill=dk + (255,))
        gx = np.linspace(-1, 1, S[0])
        shade = (0.55 + 0.75 * np.exp(-((gx + 0.35) / 0.32) ** 2) + 0.3 * np.exp(-((gx - 0.55) / 0.12) ** 2))
        arr = np.asarray(body, np.float32).copy()
        arr[..., :3] *= shade[None, :, None]
        body = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
        im.alpha_composite(body)
        # кольцо огней по краю шапки
        ring = Image.new('RGBA', S, (0, 0, 0, 0))
        rd = ImageDraw.Draw(ring)
        lc = C.mix(col, WHITE, 0.35) if lit else dark(col, 0.55)
        for i in range(18):
            a = 2 * math.pi * i / 18
            x, y = cx + (w / 2 + 2) * math.cos(a), cy + 12 + (hh / 2 + 2) * math.sin(a)
            rd.ellipse((x - 9, y - 9, x + 9, y + 9), fill=lc + (255,))
        if lit:
            ring = C.glow(ring, 12, 1.2, col)
            ox, oy = (ring.width - S[0]) // 2, (ring.height - S[1]) // 2
            im.alpha_composite(ring.crop((ox, oy, ox + S[0], oy + S[1])))
        else:
            im.alpha_composite(ring)
        # шапка: хромовое кольцо и тёмное стекло
        cap = C.ellipse(w, hh, (205, 205, 220))
        C.put(im, cap, cx, cy)
        inner = C.ellipse(w - 22, hh - 20, (16, 12, 28) if not lit else C.mix(dark(col, 0.2), INK, 0.3))
        C.put(im, inner, cx, cy)
        gl = C.ellipse(int(w * 0.62), int(hh * 0.3), WHITE, 34)
        C.put(im, gl, cx - w * 0.08, cy - hh * 0.27)
        return im
    return cached(('bump', col, lit), mk)


def plate(w, h, col, lit=True, r=22):
    """Плашка в стиле бэкгласса: тёмное стекло, хромированная фаска, неоновый край в цвете клуба, глянец сверху."""
    def mk():
        im = C.rrect(w, h, r, (200, 200, 214))
        im.alpha_composite(C.rrect(w - 8, h - 8, r - 4, C.mix(col, WHITE, 0.25) if lit else (70, 66, 90)), (4, 4))
        im.alpha_composite(C.rrect(w - 14, h - 14, r - 7, C.mix(INK, dark(col, 0.25), 0.55), 248), (7, 7))
        gl = C.lgrad(w - 14, int((h - 14) * 0.46), (255, 255, 255), (255, 255, 255), 90, 30, 0)
        m = C.rrect(w - 14, h - 14, r - 7).crop((0, 0, w - 14, gl.height)).getchannel('A')
        gl.putalpha(Image.fromarray((np.asarray(gl.getchannel('A'), np.float32) * np.asarray(m, np.float32) / 255).astype(np.uint8)))
        im.alpha_composite(gl, (7, 7))
        return im
    return cached(('plate', w, h, col, lit, r), mk)


def neon_edge(w, h, col, r=22):
    def mk():
        ol = C.rrect(w + 6, h + 6, r + 3, None, outline=C.mix(col, WHITE, 0.4), width=5)
        return C.glow(ol, 14, 1.3, col)
    return cached(('edge', w, h, col, r), mk)


def lamp_sprite(col, on, d=30):
    def mk():
        if on <= 0:
            im = C.ellipse(d, d, dark(col, 0.3))
            C.put(im, C.ellipse(d - 10, d - 10, dark(col, 0.42)), d / 2, d / 2)
            return im
        core = C.ellipse(d, d, C.mix(col, WHITE, 0.5 * on))
        return C.glow(core, 10, 1.1 * on, col)
    return cached(('lamp', col, round(on, 2), d), mk)


def arrow_lamp(col, on, w=56, h=46):
    def mk():
        pts = [(w / 2, 0), (w, h * 0.62), (w * 0.7, h * 0.62), (w * 0.7, h), (w * 0.3, h), (w * 0.3, h * 0.62), (0, h * 0.62)]
        pts = [(w / 2, 2), (w - 2, h - 2), (w / 2, h * 0.62), (2, h - 2)]
        im = C.polygon(pts, (w, h), C.mix(col, WHITE, 0.45 * on) if on > 0 else dark(col, 0.36))
        return C.glow(im, 10, 1.1 * on, col) if on > 0 else im
    return cached(('arrow', col, round(on, 2), w, h), mk)


# ─────────────────────────────── стол ───────────────────────────────
def table(col, emb=None, lit=False):
    """Статичный кадр стола в цвете col: шкаф, поле в перспективе с артом, борта, рогатки, дорожки, фартук."""
    key = ('table', col, emb[0] if emb else None, lit)
    if key in _CACHE:
        return _CACHE[key]
    rnd = np.random.default_rng(11)
    fr = C.vgrad(W, H, [(0, (10, 6, 18)), (0.5, (6, 4, 12)), (1, (4, 3, 8))]).convert('RGBA')
    # стенки шкафа по бокам поля: тёмный лак и неоновая полоса
    walls = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    wd = ImageDraw.Draw(walls)
    wc = dark(col, 0.2)
    wd.polygon([(0, PF_TOP - 40), (PF_TX0 - 6, PF_TOP), (PF_BX0, PF_BOT), (0, PF_BOT)], fill=wc + (255,))
    wd.polygon([(W, PF_TOP - 40), (PF_TX1 + 6, PF_TOP), (PF_BX1, PF_BOT), (W, PF_BOT)], fill=wc + (255,))
    fr.alpha_composite(walls)
    # арт поля в плоскости: FW×FH → трапеция
    FW, FH = 1000, 1240
    art = C.vgrad(FW, FH, [(0, C.mix(dark(col, 0.16), INK, 0.4)), (0.55, dark(col, 0.3 if not lit else 0.42)),
                           (1, dark(col, 0.2))]).convert('RGBA')
    ad = ImageDraw.Draw(art)
    # веер лучей от низа
    for i in range(-9, 10):
        a0 = math.radians(-90 + i * 9 - 2.6)
        a1 = math.radians(-90 + i * 9 + 2.6)
        ox, oy = FW / 2, FH * 1.05
        R = 2200
        ad.polygon([(ox, oy), (ox + R * math.cos(a0), oy + R * math.sin(a0)), (ox + R * math.cos(a1), oy + R * math.sin(a1))],
                   fill=tuple(C.mix(col, WHITE, 0.2)) + (16 if not lit else 30,))
    # концентрические дуги и звёзды
    for k, rr in enumerate((300, 420, 540)):
        ad.ellipse((FW / 2 - rr, FH * 0.52 - rr, FW / 2 + rr, FH * 0.52 + rr), outline=tuple(col) + (40 if not lit else 70,),
                   width=6 if k == 1 else 3)
    for _ in range(220):
        x, y, r = rnd.uniform(0, FW), rnd.uniform(0, FH), rnd.uniform(1.2, 3.2)
        ad.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(rnd.uniform(30, 110))))
    # шашечки по краю (как на старых столах)
    for y in range(0, FH, 40):
        for x0 in (8, FW - 32):
            if (y // 40) % 2 == 0:
                ad.rectangle((x0, y, x0 + 24, y + 20), fill=tuple(C.mix(col, WHITE, 0.3)) + (60,))
    if emb is not None:
        e = emb[1]
        ew = C.fit(e, 620, 620)
        ew = C.fade(ew, 0.12 if not lit else 0.22)
        C.put(art, ew, FW / 2, FH * 0.52)
    # варп в перспективу
    dst = [(PF_TX0, PF_TOP), (PF_TX1, PF_TOP), (PF_BX1, PF_BOT), (PF_BX0, PF_BOT)]
    src = [(0, 0), (FW, 0), (FW, FH), (0, FH)]
    warped = art.transform((W, H), Image.PERSPECTIVE, persp_coeffs(dst, src), Image.BICUBIC)
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).polygon(dst, fill=255)
    warped.putalpha(mask)
    fr.alpha_composite(warped)
    # глянец поля: диагональная полоса
    gl = Image.new('L', (W, H), 0)
    ImageDraw.Draw(gl).polygon([(PF_TX0 + 120, PF_TOP), (PF_TX0 + 300, PF_TOP), (PF_BX0 + 300, PF_BOT), (PF_BX0 + 40, PF_BOT)], fill=26)
    gl = gl.filter(ImageFilter.GaussianBlur(30))
    fr.alpha_composite(tinted(gl, WHITE))
    # хромированные борта
    rails = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rails)
    prof = [(0, 90), (3, 160), (6, 235), (9, 200), (12, 120), (15, 70), (18, 140), (21, 210), (24, 110)]
    for side in (-1, 1):
        x0, x1 = (PF_TX0, PF_BX0) if side < 0 else (PF_TX1, PF_BX1)
        for off, v in prof:
            o = -side * (off - 10)
            rd.line((x0 + o * 0.9, PF_TOP - 6, x1 + o * 1.1, PF_BOT), fill=(v, v, int(v * 1.05), 255), width=4)
    nl = Image.new('L', (W, H), 0)
    nd = ImageDraw.Draw(nl)
    for side in (-1, 1):
        x0, x1 = (PF_TX0, PF_BX0) if side < 0 else (PF_TX1, PF_BX1)
        nd.line((x0 - side * 26, PF_TOP, x1 - side * 30, PF_BOT), fill=255, width=4)
    fr.alpha_composite(tinted(nl.filter(ImageFilter.GaussianBlur(8)), col, 1.4))
    fr.alpha_composite(tinted(nl, C.mix(col, WHITE, 0.3)))
    fr.alpha_composite(rails)
    # рогатки над флипперами и направляющие дорожки
    for sg in (-1, 1):
        def X(x):
            return x if sg < 0 else W - x
        tri = [(X(78), 1128), (X(78), 1262), (X(232), 1300)]
        sl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sl)
        sd.polygon(tri, fill=(232, 230, 240, 255))
        sd.line([tri[0], tri[2]], fill=tuple(C.mix(col, WHITE, 0.2)) + (255,), width=12)
        inner = [(X(92), 1150), (X(92), 1250), (X(204), 1280)]
        sd.polygon(inner, fill=tuple(dark(col, 0.5)) + (255,))
        fr.alpha_composite(sl)
        gd = ImageDraw.Draw(fr)
        for off, v in ((0, 210), (5, 120)):
            gd.line((X(36 + off), 1080, X(36 + off), 1268, X(FL_PIV['L'][0] - 26 + off), FL_PIV['L'][1] - 8), fill=(v, v, v + 10, 255),
                    width=5, joint='curve')
    # пусковой жёлоб справа
    gd = ImageDraw.Draw(fr)
    gd.line((1006, 1420, 1004, 1000, 990, 760), fill=(170, 170, 185, 255), width=5)
    # фартук
    ap = C.vgrad(W, H - PF_BOT, [(0, (40, 38, 52)), (0.15, (22, 20, 30)), (1, (8, 6, 12))]).convert('RGBA')
    fr.alpha_composite(ap, (0, PF_BOT))
    ImageDraw.Draw(fr).line((0, PF_BOT + 1, W, PF_BOT + 1), fill=(210, 210, 225, 255), width=4)
    _CACHE[key] = fr
    return fr


def burst(col, d=220):
    """Вспышка удара: кольцо и лучики."""
    def mk():
        ss = 2
        S = d * ss
        im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        c = S / 2
        for i in range(12):
            a = 2 * math.pi * i / 12 + 0.2
            r0, r1 = S * 0.16, S * (0.46 if i % 2 else 0.36)
            dr.line((c + r0 * math.cos(a), c + r0 * math.sin(a), c + r1 * math.cos(a), c + r1 * math.sin(a)),
                    fill=tuple(C.mix(col, WHITE, 0.6)) + (255,), width=5 * ss)
        im = im.resize((d, d), Image.LANCZOS)
        return C.glow(im, 8, 1.1, col)
    return cached(('burst', col, d), mk)


def sunburst(col, R=560, n=24):
    def mk():
        S = 2 * R
        im = Image.new('L', (S, S), 0)
        d = ImageDraw.Draw(im)
        for i in range(n):
            a0 = 2 * math.pi * i / n
            a1 = a0 + math.pi / n
            d.polygon([(R, R), (R + R * math.cos(a0), R + R * math.sin(a0)), (R + R * math.cos(a1), R + R * math.sin(a1))], fill=255)
        yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
        fall = np.clip(1 - np.hypot(xx - R, yy - R) / R, 0, 1) ** 1.2
        m = Image.fromarray((np.asarray(im, np.float32) * fall * 0.42).astype(np.uint8), 'L')
        return tinted(m, col)
    return cached(('sun', col, R, n), mk)


# ─────────────────────────────── ролик ───────────────────────────────
class Pinball(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 70, drop=19 * 60 / 70, line=None, team=7, pre=1,
                 hold=5, cta=3, seed=31, **kw):
        """Сцены: интро → команда (team долей) ×2 → разгон (pre) → дроп-прогноз (hold) → Telegram (cta); доли — от дропа."""
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
        self.cover_t = max(1.3, self.t1 - 0.3)
        self.hb = u / 2
        self._prep()

    # ── заготовки ──
    def _prep(self):
        self.col = {'h': club(self.h)}
        self.col['a'] = club(self.a, avoid=self.col['h'])
        self.col['n'] = NEUT
        self.cf = self.col[self.side]
        self.col['f'] = self.cf
        self.tm = {'h': self.h, 'a': self.a, 'f': self.fav}
        # столы (до fork — общие для процессов)
        self.tab = {'n': table(NEUT)}
        for k in ('h', 'a'):
            self.tab[k] = table(self.col[k], (self.tm[k].name, self.tm[k].emb(600)))
        self.tab['f'] = table(self.cf, (self.fav.name, self.fav.emb(600)), lit=True)
        self.tag = C.text(F.tag(self.league), 'rubik', 30, (214, 206, 236), 700, track=0.16)
        self.tag_pl = C.rrect(self.tag.width + 56, 48, 24, (24, 18, 40), 230, outline=(120, 110, 150), width=2)
        C.put(self.tag_pl, self.tag, self.tag_pl.width / 2, 24)
        self.handle_im = C.text(C.HANDLE, 'russo', 40, (236, 232, 248), 400, track=0.04)
        # бэкгласс: высокая заготовка (обрезаем по нужной высоте) и нижняя хромированная кромка
        for k in ('n', 'h', 'a', 'f'):
            self._bg_panel(k)
        self.bg_edge = {k: self._bg_edge(self.col[k]) for k in ('n', 'h', 'a', 'f')}
        # интро
        self.i_emb = {s: C.glow(t.emb(224), 18, 0.8, self.col[s]) for s, t in (('h', self.h), ('a', self.a))}
        self.i_name = {s: C.text(t.up, 'russo', 60, WHITE, 400, max_w=430) for s, t in (('h', self.h), ('a', self.a))}
        self.i_role = {s: C.text(r, 'rubik', 28, GRAY, 700, track=0.2) for s, r in (('h', 'ХОЗЯЕВА'), ('a', 'ГОСТИ'))}
        self.i_date = dmd_text('%s · %s' % (F.lg_ru(self.league), self.when), 54, max_w=880)
        self.i_ball = C.glow(ball_sprite(92, NEUT2), 16, 0.7, NEUT2)
        self.line_lab = C.text('ОСНОВНОЕ ВРЕМЯ', 'rubik', 30, C.mix(NEUT2, WHITE, 0.4), 700, track=0.24)
        self.line_pl = []
        if self.line:
            for lab, v in zip(('П1', 'Х', 'П2'), self.line):
                self.line_pl.append(self._line_plate(lab, v))
        # команды
        self.T = {k: self._team(k) for k in ('h', 'a')}
        # прогноз
        self.p_emb = C.glow(self.fav.emb(430), 26, 0.9, self.cf)
        m = re.match(r'(ПОБЕДА)\s+(.+)$', self.pick1)
        self.p_row1 = dmd_text(self.pick1, 92, max_w=900)
        self.p_row2 = dmd_text(self.pick2, 56, max_w=880) if self.pick2 else None
        self.kef = None
        if self.coef:
            kt = C.text('КЭФ', 'rubik', 46, C.mix(self.cf, WHITE, 0.55), 800, track=0.16)
            kv = C.text(C.fmt_k(self.coef), 'russo', 96, WHITE, 400)
            w = kt.width + kv.width + 120
            pl = plate(w, 136, self.cf).copy()
            x = (w - kt.width - 26 - kv.width) / 2
            C.put(pl, kt, x, 68 - kt.height / 2 + 6, anchor='tl')
            C.put(pl, kv, x + kt.width + 26, 68 - kv.height / 2, anchor='tl')
            self.kef = pl
            self.kef_edge = neon_edge(w, 136, self.cf)
        self.tg = C.tg_plate(960, 172, font='russo')
        # ключевые точки шарика и удары
        self._path()
        # огни: колонки по бортам и стрелки по центру
        self.lamps = []
        for side in (-1, 1):
            for i in range(9):
                y = PF_TOP + 70 + i * 92
                self.lamps.append(('o', pf_x(y, side) - side * 58, y, i))
        self.arrows = [(540, 1272 + i * 0), (540, 1314)]
        self.arrows = [(540, 1282 - 0), (540, 1330)]
        warm = [ball_sprite(int(ball_d(y)), self.col[k]) for y in range(PF_TOP - 200, PF_BOT + 2, 2) for k in ('n', 'h', 'a', 'f')]
        del warm

    def _bg_panel(self, k):
        key = ('bgp', k, id(self))
        col = self.col[k]

        def mk():
            hh = BGB_PICK - BG_Y0 + 10
            w = BG_X1 - BG_X0
            im = C.rrect(w, hh, 30, (196, 196, 212))
            im.alpha_composite(C.rrect(w - 10, hh - 10, 25, C.mix(col, WHITE, 0.2)), (5, 5))
            inner = C.vgrad(w - 18, hh - 18, [(0, C.mix(dark(col, 0.22), INK, 0.3)), (0.5, C.mix(dark(col, 0.12), INK, 0.5)),
                                               (1, INK)]).convert('RGBA')
            inner.putalpha(C.rrect(w - 18, hh - 18, 21).getchannel('A'))
            # арт: дуги и звёзды
            d = ImageDraw.Draw(inner)
            rnd = np.random.default_rng(5)
            for _ in range(90):
                x, y, r = rnd.uniform(0, w), rnd.uniform(0, hh), rnd.uniform(1, 2.6)
                d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(rnd.uniform(40, 120))))
            im.alpha_composite(inner, (9, 9))
            return im
        self.__dict__.setdefault('bgp', {})[k] = cached(key, mk)

    def _bg_edge(self, col):
        w = BG_X1 - BG_X0
        im = Image.new('RGBA', (w + 60, 70), (0, 0, 0, 0))
        bar = C.rrect(w, 14, 7, (205, 205, 222))
        bar.alpha_composite(C.rrect(w - 6, 4, 2, (255, 255, 255)), (3, 3))
        g = C.glow(C.rrect(w - 40, 6, 3, col), 12, 1.2, col)
        C.put(im, g, im.width / 2, 40)
        C.put(im, bar, im.width / 2, 30)
        return im

    def _line_plate(self, lab, v):
        w, h = LINE_WH
        out = {}
        for lit in (False, True):
            col = NEUT if lit else (110, 90, 140)
            pl = plate(w, h, NEUT, lit).copy()
            C.put(pl, C.text(lab, 'rubik', 40, C.mix(NEUT2, WHITE, 0.3) if lit else (150, 140, 176), 800, track=0.12), w / 2, 52)
            C.put(pl, C.text(C.fmt_k(v), 'russo', 96, WHITE if lit else (196, 190, 214), 400, max_w=w - 36), w / 2, 136)
            out[lit] = pl
        out['edge'] = neon_edge(w, h, NEUT)
        return out

    # ── плашки фактов ──
    def _game_plate(self, g, col):
        w, h = GAME_WH
        pl = plate(w, h, col).copy()
        x0 = 24
        dt = C.text(g['date'], 'rubik', 26, GRAY, 600) if g['date'] else None
        room = w - x0 - 20 - (dt.width + 12 if dt else 0)
        nm = C.text(g['opp'].upper(), 'russo', 36, WHITE, 400, max_w=room)
        C.put(pl, nm, x0, 46 - nm.height / 2, anchor='tl')
        if dt:
            C.put(pl, dt, w - 20 - dt.width, 46 - dt.height / 2, anchor='tl')
        yc = 124
        sc = C.text(g['score'], 'russo', 76, WHITE, 400)
        C.put(pl, sc, x0, yc - sc.height / 2, anchor='tl')
        ch = F.chip(g['res'], 62)
        C.put(pl, ch, w - 22 - 31, yc)
        if g['note']:
            nt = C.text(g['note'], 'rubik', 32, (226, 214, 160), 800, max_w=w - x0 - sc.width - 100)
            C.put(pl, nt, x0 + sc.width + 12, yc + sc.height / 2 - nt.height, anchor='tl')
        return pl

    def _bump_face(self, lab, val, sub, vcol):
        """Надписи на шапке бампера (отдельный слой поверх спрайта)."""
        w, hh = BUMP_W - 30, BUMP_H - 26
        im = Image.new('RGBA', (w, hh), (0, 0, 0, 0))
        C.put(im, C.text(lab, 'rubik', 28, GRAY, 800, track=0.14, max_w=w * 0.72), w / 2, 40)
        C.put(im, C.text(val, 'russo', 92, vcol, 400, max_w=w * 0.8), w / 2, hh / 2 + 6)
        if sub:
            C.put(im, C.text(sub, 'rubik', 28, (226, 222, 238), 600, max_w=w * 0.74), w / 2, hh - 40)
        return im

    def _sling_plate(self, lab, val, col):
        w, h = SLING_WH
        pl = plate(w, h, col).copy()
        C.put(pl, C.text(lab, 'rubik', 26, GRAY, 800, track=0.12, max_w=w - 40), w / 2, 34)
        C.put(pl, C.text(val, 'russo', 50, WHITE, 400, max_w=w - 40), w / 2, 78)
        return pl

    def _stats(self, s):
        out = []
        if s['points'] is not None:
            sub = ('за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей'))) if s['gp'] is not None else ''
            out.append(('ОЧКИ', '%d' % s['points'], sub, WHITE))
        if s['place'] is not None:
            out.append(('МЕСТО', '%d' % s['place'], s['place_scope'], WHITE))
        if s['gd'] is not None:
            gcol = F.WIN if s['gd'] > 0 else F.LOSS if s['gd'] < 0 else WHITE
            out.append(('РАЗНИЦА', F.gd_txt(s['gd']), 'шайб', gcol))
        return out

    def _extras(self, rec):
        out = []
        m = re.match(r'\s*(ОТ|В|П)\s*(\d+)', str(rec.get('streak') or ''))
        if m and int(m.group(2)) >= 2:
            n = int(m.group(2))
            word = {'В': plural(n, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'), 'П': plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ'),
                    'ОТ': plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ') + ' В ОТ'}[m.group(1)]
            out.append(('СЕРИЯ', '%d %s' % (n, word)))
        for key, lab in (('pp', 'БОЛЬШИНСТВО'), ('pk', 'МЕНЬШИНСТВО')):
            v = pct(rec.get(key)) if rec.get(key) is not None else None
            if v:
                out.append((lab, v))
        return out[:2]

    def _team(self, key):
        tm = self.h if key == 'h' else self.a
        col = self.col[key]
        s = self.st[key]
        facts = []                                             # (id, картинка, центр)
        for i, g in enumerate(s['games'][:3]):
            facts.append(('g%d' % i, self._game_plate(g, col), GAME_C[i]))
        for i, (lab, v, sub, vc) in enumerate(self._stats(s)[:3]):
            facts.append(('b%d' % i, self._bump_face(lab, v, sub, vc), BUMP_C[i]))
        for i, (lab, v) in enumerate(self._extras(self.raw[key])):
            facts.append(('s%d' % i, self._sling_plate(lab, v, col), SLING_C[i]))
        emb = C.glow(tm.emb(186), 16, 0.8, col)
        ring = C.ellipse(212, 212, C.mix(col, WHITE, 0.2))
        ring.alpha_composite(C.ellipse(200, 200, dark(col, 0.18)), (6, 6))
        name = dmd_text(tm.up, 100, max_w=690)
        role = dmd_text('ХОЗЯЕВА' if key == 'h' else 'ГОСТИ', 44, max_w=690, font='rubik', wght=800, track=0.24)
        return dict(col=col, facts=facts, emb=emb, ring=C.glow(ring, 14, 0.9, col), name=name, role=role,
                    edge_g=neon_edge(GAME_WH[0], GAME_WH[1], col), edge_s=neon_edge(SLING_WH[0], SLING_WH[1], col),
                    bump=bumper_sprite(col, False), bump_lit=bumper_sprite(col, True), flip=flipper_sprite(col),
                    burst=burst(col))

    # ── шарик ──
    def fl_point(self, side):
        px, py = FL_PIV[side]
        sg = 1 if side == 'L' else -1
        a = math.radians(FL_REST)
        L = FL_LEN * 0.66
        return (px + sg * L * math.cos(a) + sg * 10, py + L * math.sin(a) - 40)

    def _hit_point(self, tid, prev, scene):
        if tid.startswith('i'):
            cx, cy = LINE_C[int(tid[1])]
            return (cx + (prev[0] - cx) * 0.12, cy + LINE_WH[1] / 2 + 24)
        if tid.startswith('g'):
            cx, cy = GAME_C[int(tid[1])]
            return (cx + (prev[0] - cx) * 0.1, cy + GAME_WH[1] / 2 + 26)
        if tid.startswith('b'):
            cx, cy = BUMP_C[int(tid[1])]
            cy += 18
            dx, dy = prev[0] - cx, (prev[1] - cy) / 0.86
            n = math.hypot(dx, dy) or 1.0
            rx, ry = BUMP_W / 2 + 22, (BUMP_H / 2 + 22) * 0.86
            return (cx + dx / n * rx, cy + dy / n * ry)
        if tid.startswith('s'):
            i = int(tid[1])
            cx, cy = SLING_C[i]
            return (cx + (1 if i == 0 else -1) * (SLING_WH[0] / 2 + 22), cy + 10)
        return prev

    def _path(self):
        """Ключевые точки шарика: (t, (x, y), событие). Удары и выстрелы флипперов — ровно на долях / половинах долей."""
        b, hb = self.b, self.hb
        K = [(0.0, PLUNGER, None), (b(-18.5), (996.0, 880.0), None)]
        self.hits = []                                         # (t, сцена, id)
        self.fires = {'L': [], 'R': []}

        def add_hit(t, scene, tid):
            p = self._hit_point(tid, K[-1][1], scene)
            K.append((t, p, ('hit', scene, tid)))
            self.hits.append((t, scene, tid))

        def add_fire(t, side):
            K.append((t, self.fl_point(side), ('fire', side)))
            self.fires[side].append(t)

        if self.line:
            for i in range(3):
                add_hit(b(-18 + i), 'n', 'i%d' % i)
        add_fire(self.t1, 'L')
        for key, ts, nxt in (('h', self.t1, 'R'), ('a', self.t2, None)):
            ids = [f[0] for f in self.T[key]['facts']]
            for i, tid in enumerate(ids):
                add_hit(ts + (i + 1) * hb, key, tid)
            k = len(ids) + 2
            cyc = ['b0', 'b1', 'b2', 'b1']
            j = 0
            while k <= 12:
                tid = cyc[j % 4]
                if K[-1][2] and K[-1][2][0] == 'hit' and K[-1][2][2] == tid:
                    j += 1
                    tid = cyc[j % 4]
                add_hit(ts + k * hb, key, tid)
                k += 2
                j += 1
            if nxt:
                add_fire(ts + 14 * hb, nxt)
        # разгон: шарик выходит на правую дорожку и скатывается к правому флипперу ровно к дропу
        K.append((self.tp + 0.5 * hb, (930.0, 1150.0), None))
        add_fire(self.drop, 'R')
        self.K = K
        self.Kt = [k[0] for k in K]
        # изгиб сегментов
        self.bend = []
        for i in range(len(K) - 1):
            (t0, p0, _), (t1, p1, _) = K[i], K[i + 1]
            straight = i == 0 or i == len(K) - 2
            self.bend.append(0.0 if straight else (0.2 if i % 2 else -0.2))

    def ball_pos(self, t):
        K = self.K
        if t <= K[0][0]:
            return K[0][1]
        if t >= self.drop:
            # выстрел по центральной рампе в бэкгласс
            p0 = K[-1][1]
            q = C.seg(t, self.drop, self.drop + 0.16)
            p1 = (548.0, 560.0)
            return (C.lerp(p0[0], p1[0], q ** 0.8), C.lerp(p0[1], p1[1], q ** 0.8))
        i = max(0, np.searchsorted(self.Kt, t, side='right') - 1)
        i = min(i, len(K) - 2)
        (t0, p0, _), (t1, p1, _) = K[i], K[i + 1]
        q = C.seg(t, t0, t1)
        if i == 0:
            q = C.out_cubic(q)
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        bk = self.bend[i]
        cx, cy = mx - dy * bk, my + dx * bk
        x = (1 - q) ** 2 * p0[0] + 2 * (1 - q) * q * cx + q ** 2 * p1[0]
        y = (1 - q) ** 2 * p0[1] + 2 * (1 - q) * q * cy + q ** 2 * p1[1]
        return (x, y)

    def fl_angle(self, t, side):
        a = 0.0
        for tf in self.fires[side]:
            dt = t - tf
            if -0.001 <= dt < 0.4:
                k = C.seg(dt, 0, 0.05) if dt < 0.05 else (1.0 if dt < 0.16 else 1 - C.in_out(C.seg(dt, 0.16, 0.36)))
                a = max(a, k)
        if self.tp <= t < self.drop:                            # «наготове»: вздрагивают на половинах доли
            for k in range(2):
                dt = t - (self.tp + k * self.hb)
                if 0 <= dt < 0.3:
                    a = max(a, 0.35 * math.sin(math.pi * dt / 0.3))
        sg = 1 if side == 'L' else -1
        return sg * (FL_REST + (FL_UP - FL_REST) * a)

    # ── сцена и цвета ──
    def scene(self, t):
        if t < self.t1:
            return 'n'
        if t < self.t2:
            return 'h'
        if t < self.drop:
            return 'a'
        return 'f'

    def bgb(self, t):
        """Нижняя кромка бэкгласса."""
        D = self.drop
        if t < self.t1:
            return BGB_INTRO
        if t < D:
            return C.lerp(BGB_INTRO, BGB_TEAM, C.out_expo(C.seg(t, self.t1, self.t1 + 0.42)))
        return C.lerp(BGB_TEAM, BGB_PICK, C.out_expo(C.seg(t, D, D + 0.34)))

    def hit_info(self, t, scene, tid):
        """(первый удар, последний удар ≤ t) по цели в сцене."""
        first = last = None
        for th, sc, i in self.hits:
            if sc == scene and i == tid:
                if first is None:
                    first = th
                if th <= t:
                    last = th
        return first, last

    # ── отрисовка ──
    def draw_lamps(self, fr, t, key):
        col = self.col[key]
        D, u = self.drop, self.u
        for kind, x, y, i in self.lamps:
            if key == 'f':
                ph = ((t - D) / u) % 1.0
                on = 0.65 + 0.35 * math.exp(-ph * 5) if (i + int((t - D) / u)) % 2 == 0 else 0.45 + 0.4 * math.exp(-ph * 5)
            elif self.tp <= t < D:
                sp = 6 + 14 * C.seg(t, self.tp, D)
                ph = (t - self.tp) * sp
                on = 1.0 if (int(ph) - (8 - i)) % 3 == 0 else 0.18
            else:
                ph = (t / u) * 2
                on = 0.85 if (int(ph) + (8 - i)) % 4 == 0 else 0.0
            on = round(on * 4) / 4
            C.put(fr, lamp_sprite(col, on, 28), x, y)
        for j, (x, y) in enumerate(self.arrows):
            if key == 'f':
                on = 1.0
            else:
                on = 1.0 if (int(t / self.hb) + j) % 2 == 0 else 0.25
            C.put(fr, arrow_lamp(col, on), x, y)

    def draw_backglass(self, fr, t, key, yb):
        hh = int(yb - BG_Y0)
        pan = self.bgp[key].crop((0, 0, BG_X1 - BG_X0, hh))
        C.put(fr, pan, BG_X0, BG_Y0, anchor='tl')
        C.put(fr, self.bg_edge[key], W / 2, yb - 4)

    def put_dmd(self, fr, im_pad, cx, cy, ox, oy, reveal=1.0, a=1.0):
        """Положить строку табло так, чтобы точки легли на сетку табло (ox, oy — начало сетки)."""
        im, pad = im_pad
        x = cx - im.width / 2
        y = cy - im.height / 2
        x = ox + round((x + pad - ox) / PITCH) * PITCH - pad
        y = oy + round((y + pad - oy) / PITCH) * PITCH - pad
        if reveal < 0.999:
            wv = int(im.width * reveal)
            if wv <= 0:
                return
            im = im.crop((0, 0, wv, im.height))
        C.put(fr, im, x, y, a, anchor='tl')

    def intro(self, fr, t, yb, a=1.0):
        # бэкгласс: эмблемы, названия, роли, табло с датой
        for s, x, d0 in (('h', 262, 0.05), ('a', 818, 0.18)):
            q = C.out_back(C.seg(t, d0, d0 + 0.4), 1.5)
            if q > 0.01:
                C.put(fr, C.scale(self.i_emb[s], 0.6 + 0.4 * q), x, 452, a * min(1, q * 1.6))
            qn = C.out_expo(C.seg(t, d0 + 0.12, d0 + 0.45))
            C.put(fr, self.i_name[s], x, 612 + 16 * (1 - qn), a * qn)
            C.put(fr, self.i_role[s], x, 664, a * qn)
        C.put(fr, self.i_ball, 540, 452, a * C.seg(t, 0.25, 0.5))
        dp = dmd_panel(900, 96)
        C.put(fr, dp, 540, 744, a)
        self.put_dmd(fr, self.i_date, 540, 744, 540 - 450 + 12, 744 - 48 + 12, reveal=C.seg(t, 0.15, 0.75), a=a)
        # линия: плашки-мишени
        if self.line_pl:
            C.put(fr, self.line_lab, 540, 846, a * C.seg(t, 0.3, 0.6))
            for i, pl in enumerate(self.line_pl):
                cx, cy = LINE_C[i]
                q = C.out_back(C.seg(t, 0.25 + 0.08 * i, 0.6 + 0.08 * i), 1.4)
                first, last = self.hit_info(t, 'n', 'i%d' % i)
                lit = first is not None and t >= first
                fl = math.exp(-(t - last) / 0.2) if last is not None else 0.0
                im = pl[lit]
                s = (0.8 + 0.2 * q) * (1 + 0.05 * fl)
                C.put(fr, C.scale(im, s) if abs(s - 1) > 0.003 else im, cx, cy, a * min(1, q * 1.5))
                if lit:
                    C.put(fr, pl['edge'], cx, cy, a * (0.55 + 0.45 * fl))

    def team(self, fr, t, key, ts, te, yb):
        T = self.T[key]
        col = T['col']
        out_k = C.seg(t, te - 0.24, te) if t < self.drop else 1.0       # факты «падают» перед склейкой
        if key == 'a':
            out_k = C.seg(t, self.tp - 0.0, self.tp + 0.26)
        # бамперы (статичные спрайты) и факты
        for i in range(3):
            cx, cy = BUMP_C[i]
            tid = 'b%d' % i
            first, last = self.hit_info(t, key, tid)
            fl = math.exp(-(t - last) / 0.22) if last is not None and t - last < 1.2 else 0.0
            sp = T['bump_lit'] if (fl > 0.25 or (first is not None and t >= first and out_k < 1)) else T['bump']
            s = 1 + 0.045 * fl
            C.put(fr, C.scale(sp, s) if s > 1.003 else sp, cx, cy + 32)
        for tid, im, (cx, cy) in T['facts']:
            first, last = self.hit_info(t, key, tid)
            if first is None or t < first or out_k >= 1:
                continue
            q = C.out_back(C.seg(t, first, first + 0.26), 1.7)
            fl = math.exp(-(t - last) / 0.2) if last is not None else 0.0
            s = (0.62 + 0.38 * q) * (1 + 0.05 * fl) * (1 - 0.25 * out_k)
            a = min(1.0, q * 1.8) * (1 - out_k)
            dy = 60 * C.in_cubic(out_k)
            if tid[0] == 'b':
                C.put(fr, C.scale(im, s), cx, cy + dy, a)
            else:
                C.put(fr, C.scale(im, s), cx, cy + dy, a)
                edge = T['edge_g'] if tid[0] == 'g' else T['edge_s']
                C.put(fr, C.scale(edge, s), cx, cy + dy, a * (0.45 + 0.55 * fl))

    def dmd_chase(self, fr, t, px0, px1, cy):
        """Табло на разгоне: бегущие полосы точек (огни табло)."""
        w = px1 - px0 - 24
        hh = 206 - 24
        key = ('chase', w, hh)
        if key not in _CACHE:
            gy, gx = hh // PITCH, w // PITCH
            _CACHE[key] = (gy, gx, dot_tile(PITCH))
        gy, gx, tile = _CACHE[key]
        xs = np.arange(gx)[None, :]
        ys = np.arange(gy)[:, None]
        ph = (t - self.tp) * (24 + 40 * C.seg(t, self.tp, self.drop))
        v = (np.sin((xs * 0.55 + np.abs(ys - gy / 2) * 0.9 - ph)) > 0.55).astype(np.float32)
        v *= 0.6 + 0.4 * (np.abs(ys - gy / 2) < gy * 0.36)
        dots = np.kron(v, tile)
        m = Image.fromarray((dots * 230).astype(np.uint8), 'L')
        C.put(fr, tinted(m, C.mix(AMBER, WHITE, 0.15)), px0 + 12, cy - 103 + 12, anchor='tl')

    def pick(self, fr, t, yb):
        D, u = self.drop, self.u
        tc = self.t_cta
        # солнце лучей и огромная эмблема на бэкглассе
        ey = BG_Y0 + (yb - BG_Y0 - 230) / 2 + 6
        sb = sunburst(self.cf)
        rot = (t - D) * 9
        sbr = sb.rotate(rot, Image.BILINEAR)
        k = C.out_expo(C.seg(t, D, D + 0.3))
        C.put(fr, sbr, 540, ey, 0.9 * k)
        pulse = math.exp(-(((t - D) / u) % 1.0) * 6) if t >= D else 0.0
        s = (1.35 - 0.35 * k) * (1 + 0.025 * pulse)
        C.put(fr, C.scale(self.p_emb, s), 540, ey)
        # табло: «ПОБЕДА …» и «В ОСНОВНОЕ ВРЕМЯ»
        pw, ph = 980, 206
        py = yb - 18 - ph / 2
        C.put(fr, dmd_panel(pw, ph, AMBER), 540, py)
        ox, oy = 540 - pw / 2 + 12, py - ph / 2 + 12
        if self.p_row2 is not None:
            self.put_dmd(fr, self.p_row1, 540, py - 36, ox, oy, reveal=C.seg(t, D, D + 0.22))
            self.put_dmd(fr, self.p_row2, 540, py + 58, ox, oy, reveal=C.seg(t, D + 0.5 * u, D + 0.5 * u + 0.25))
        else:
            self.put_dmd(fr, self.p_row1, 540, py, ox, oy, reveal=C.seg(t, D, D + 0.22))
        if self.kef is not None:
            q = C.out_back(C.seg(t, D + u, D + u + 0.32), 1.8)
            if q > 0.01:
                kp = 1 + 0.03 * math.exp(-(((t - D) / u) % 1.0) * 6) * (t >= D + 2 * u)
                C.put(fr, C.scale(self.kef_edge, (0.5 + 0.5 * q) * kp), 540, 1150, min(1, q * 1.5))
                C.put(fr, C.scale(self.kef, (0.5 + 0.5 * q) * kp), 540, 1150, min(1, q * 1.5))

    def effects(self, fr, t, key):
        """Вспышки ударов по целям."""
        for th, sc, tid in self.hits:
            dt = t - th
            if 0 <= dt < 0.32:
                p = self.ball_pos(th)
                q = dt / 0.32
                b = burst(self.col[sc])
                C.put(fr, C.scale(b, 0.5 + 0.9 * C.out_cubic(q)), p[0], p[1], (1 - q) ** 1.5)

    def draw_ball(self, fr, t, key):
        if t >= self.drop + 0.16:
            return
        rim = self.col[key] if key != 'n' else NEUT2
        for k in (4, 3, 2, 1):
            tt = t - k * 0.018
            if tt < 0:
                continue
            x, y = self.ball_pos(tt)
            d = ball_d(y)
            C.put(fr, ball_sprite(int(d * (1 - 0.06 * k)), rim), x, y, 0.16 * (5 - k) / 4)
        x, y = self.ball_pos(t)
        d = ball_d(y)
        sh = cached(('bsh', int(d) // 2 * 2), lambda: C.ellipse(int(d) // 2 * 2, int(d * 0.5), (0, 0, 0), 120).filter(ImageFilter.GaussianBlur(4)))
        C.put(fr, sh, x + d * 0.22, y + d * 0.42)
        C.put(fr, ball_sprite(int(d), rim), x, y)

    def draw_flippers(self, fr, t, key):
        if key == 'n':
            fl = flipper_sprite(NEUT)
        else:
            fl = self.T[key]['flip'] if key in self.T else flipper_sprite(self.cf)
        for side in ('L', 'R'):
            ang = self.fl_angle(t, side)
            im = fl if side == 'L' else cached(('flipR', id(fl)), lambda: fl.transpose(Image.FLIP_LEFT_RIGHT))
            im = im.rotate(-ang, Image.BICUBIC)
            C.put(fr, im, *FL_PIV[side])

    def frame(self, t):
        u, D = self.u, self.drop
        key = self.scene(t)
        tab = self.tab[key]
        # склейки: стол меняет цвет за 0,24 с (светлая волна сверху вниз)
        prev = {'h': 'n', 'a': 'h', 'f': 'a'}.get(key)
        t0 = {'h': self.t1, 'a': self.t2, 'f': D}.get(key)
        fr = tab.copy()
        if prev and t - t0 < 0.24:
            k = C.seg(t, t0, t0 + 0.24)
            yy = int(PF_TOP - 200 + (H - PF_TOP + 200) * k)
            old = self.tab[prev].crop((0, yy, W, H))
            fr.paste(old, (0, yy))
        self.draw_lamps(fr, t, key)
        yb = self.bgb(t)
        if key in ('n',):
            # бамперы интро (нижний виден под плашками линии)
            sp = bumper_sprite(NEUT, False)
            C.put(fr, sp, BUMP_C[2][0], BUMP_C[2][1] + 32)
        elif key == 'f':
            pass
        self.draw_flippers(fr, t, key)
        if key in ('h', 'a'):
            self.draw_ball(fr, t, key)
            self.team(fr, t, key, self.t1 if key == 'h' else self.t2, self.t2 if key == 'h' else self.tp, yb)
        elif key == 'n':
            self.draw_ball(fr, t, key)
        else:
            self.draw_ball(fr, t, 'f')
        self.effects(fr, t, key)
        self.draw_backglass(fr, t, key if key != 'n' or t < self.t1 else 'n', yb)
        if key == 'n':
            self.intro(fr, t, yb)
            # линия поверх поля (плашки ниже бэкгласса)
        elif key in ('h', 'a'):
            T = self.T[key]
            ts = self.t1 if key == 'h' else self.t2
            ey = BG_Y0 + (yb - BG_Y0) / 2 + 2
            q = C.out_back(C.seg(t, ts, ts + 0.35), 1.6)
            C.put(fr, T['ring'], 162, ey, min(1, q * 1.5))
            C.put(fr, C.scale(T['emb'], 0.6 + 0.4 * q), 162, ey, min(1, q * 1.5))
            self.backglass_team(fr, t, key, ts, yb)
        else:
            self.pick(fr, t, yb)
        # метка лиги и @jarvibet
        C.put(fr, self.tag_pl, W / 2, TAG_Y, C.seg(t, 0, 0.3))
        ha = C.seg(t, 0.15, 0.45) * (1 - C.seg(t, self.t_cta, self.t_cta + 0.2))
        C.put(fr, self.handle_im, W / 2, HY, ha)
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.04, self.t_cta + 0.5))
            C.put(fr, self.tg, W / 2, 1360 + 50 * (1 - q), q)
        # выстрел по рампе: световой след
        if D <= t < D + 0.4:
            self.shot(fr, t)
        # камера: толчок стола на склейках, наезд на разгоне, удар на дропе
        z, dx, dy, rot = 1.0, 0.0, 0.0, 0.0
        for th in (self.t1, self.t2):
            if t >= th:
                kk = 1 - C.seg(t, th, th + 0.45)
                z += 0.035 * kk ** 2
                rot += 2.4 * kk ** 2 * math.sin((t - th) * 22) * (1 if th == self.t1 else -1)
            sx, sy = C.shake(t, th, 12, 0.3)
            dx, dy = dx + sx, dy + sy
        for th, sc, tid in self.hits:
            if 0 <= t - th < 0.2:
                z += 0.008 * (1 - (t - th) / 0.2)
        if self.tp <= t < D:
            q = C.seg(t, self.tp, D)
            z += 0.045 * C.in_cubic(q)
            dx += 4 * q * math.sin(t * 71)
            dy += 4 * q * math.cos(t * 53)
        if t >= D:
            kk = 1 - C.seg(t, D, D + 0.5)
            pulse = math.exp(-(((t - D) / u) % 1.0) * 7) if t < self.t_cta else 0.0
            z += 0.08 * kk ** 2 + 0.008 * pulse
            sx, sy = C.shake(t, D, 26, 0.5)
            dx, dy = dx + sx, dy + sy
            rot = 1.2 * kk ** 2 * math.sin((t - D) * 36)
        fr = C.zoom(fr.convert('RGB'), z, dx=dx, dy=dy, rot=rot)
        if D <= t < D + 0.2:
            fr = C.rgb_split(fr, 14 * (1 - C.seg(t, D, D + 0.2)))
        if D <= t < D + 0.36:
            fa = 1.0 if t < D + 1 / 30 else (1 - C.seg(t, D + 1 / 30, D + 0.36)) ** 1.5
            fr = Image.blend(fr, Image.new('RGB', fr.size, C.mix(WHITE, self.cf, 0.25)), 0.7 * fa)
        fr = C.vignette(fr, 0.36)
        return C.grain(fr, t, 4)

    def backglass_team(self, fr, t, key, ts, yb):
        T = self.T[key]
        px0, px1 = 280, 1028
        dpy = BG_Y0 + (yb - BG_Y0) / 2 + 2
        dp = dmd_panel(px1 - px0, 206)
        C.put(fr, dp, (px0 + px1) / 2, dpy)
        ox, oy = px0 + 12, dpy - 103 + 12
        if t >= self.tp:
            self.dmd_chase(fr, t, px0, px1, dpy)
            return
        self.put_dmd(fr, T['name'], (px0 + px1) / 2, dpy - 24, ox, oy, reveal=C.seg(t, ts + 0.02, ts + 0.32))
        self.put_dmd(fr, T['role'], (px0 + px1) / 2, dpy + 62, ox, oy, reveal=C.seg(t, ts + 0.2, ts + 0.45))

    def shot(self, fr, t):
        """След шарика по рампе на дропе."""
        D = self.drop
        p0 = self.K[-1][1]
        q = C.seg(t, D, D + 0.16)
        fade_k = 1 - C.seg(t, D + 0.16, D + 0.4)
        p1 = self.ball_pos(t)
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.line((p0[0], p0[1], p1[0], p1[1]), fill=tuple(C.mix(self.cf, WHITE, 0.6)) + (int(230 * fade_k),), width=18)
        d.line((p0[0], p0[1], p1[0], p1[1]), fill=(255, 255, 255, int(255 * fade_k)), width=6)
        fr.alpha_composite(lay)
