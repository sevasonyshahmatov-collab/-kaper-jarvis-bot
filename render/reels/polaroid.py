# -*- coding: utf-8 -*-
"""«Полароиды» — прогноз как снимки моментальной камеры на тёмном столе под тёплой лампой.

Стол — тёмный орех (доски, волокна), тёплое пятно лампы (лампа чуть покачивается), мягкая виньетка, плёночное зерно.
На доли трека на стол падают полароиды (лёгкий отскок и доворот, тень от высоты) и ПРОЯВЛЯЮТСЯ: из буро-серого
через блёклую холодную картинку к полному цвету примерно за долю. «Снимок» — эмблемы и счёт в цветах клубов,
оранжевая дата-впечатка как у плёночной камеры; на белом поле снизу — подпись от руки (core 'hand' = Caveat).
Камера медленно плывёт (стол чуть медленнее снимков — параллакс), между участками стола — быстрая панорама.
Сверху JARVIS | NHL, внизу безопасной зоны @jarvibet — экранные подписи, одинаковые во всех сценах до плашки Telegram.

Сцены (u — доля трека; все склейки и акценты — на долях от дропа, числа долей — reels_cfg/polaroid.json):
  интро (до b(−2·team−clear)) — большой снимок с обеими эмблемами и названиями клубов падает на стол и проявляется,
                на поле от руки — день и время МСК; на доли под ним приклеиваются скотчем три бумажные бирки
                линии основного времени П1 · Х · П2 (кэфы крупно);
  клуб ×2 (team долей)  — панорама вдоль стола ровно на долю: снимок клуба (эмблема, имя от руки, «ХОЗЯЕВА/ГОСТИ»
                впечаткой), на полдоли — карточка в линейку на скотче; на доли 1, 2, 3 — три снимка последних игр
                (эмблема соперника, счёт, ОТ/Б, дата-впечатка, наклейка В/П, соперник от руки), между ними на карточке
                от руки появляются строки: очки за игры, место, разница шайб, серия, большинство (только непустые);
  стол пустеет (clear долей) — снимки сметает со стола, свет лампы сужается в пятно (туда ляжет снимок прогноза),
                лампа подмигивает, камера чуть наезжает;
  ДРОП (hold долей)     — вспышка фотокамеры ровно на дроп: большой снимок ТОЛЬКО выбранной команды (одна эмблема)
                проявляется быстро, тиснёная лента-наклейка «ПОБЕДА …» (form.split_pick), на полдоли — вторая
                лента «В ОСНОВНОЕ ВРЕМЯ», на долю — стикер с кэфом от руки, на 2-ю долю его обводят маркером;
                на доли — лёгкий пульс камеры;
  финал (cta долей)     — всё собирается выше, снизу ложится плашка Telegram (C.tg_plate, текст по центру плашки).
Кадр — чистая функция t; стол, свет, бумага и снимки готовятся в __init__ (до fork) и кешируются на уровне модуля.
"""
import math
import re

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels import fresh
from reels.core import W, H

PAPER = (247, 244, 236)
CARD = (248, 243, 229)
INK = (28, 44, 104)                # синяя ручка
MARK = (30, 28, 32)                # чёрный маркер
RED = (196, 34, 40)
WIN_C = (30, 156, 78)
LOSS_C = (214, 52, 46)
CREAM = (244, 232, 210)            # экранные подписи
AMBER = (255, 146, 40)             # дата-впечатка
TAG_Y, HANDLE_Y = 268, 1440
SX = 1350                          # шаг камеры между участками стола
PX, PY = 80, 60                    # запас текстуры стола под дрейф камеры
LP = 100                           # запас карты света под качание лампы

_CACHE = {}


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
        return float(str(v).replace(',', '.').replace('%', '').strip())
    except ValueError:
        return None


def _streak(v):
    """«В2» → ('2', 'победы подряд'); серия из одной игры и ОТ — не показываем."""
    m = re.match(r'\s*(ОТ|OT|В|W|П|L)\s*(\d+)', str(v or '').upper())
    if not m:
        return None
    k, n = m.group(1), int(m.group(2))
    if n < 2:
        return None
    if k in ('В', 'W'):
        return '%d' % n, ' ' + plural(n, 'победа', 'победы', 'побед') + ' подряд'
    if k in ('П', 'L'):
        return '%d' % n, ' ' + plural(n, 'поражение', 'поражения', 'поражений') + ' подряд'
    return None


def _ease_fall(p):
    return p * p


def _noise2(h, w, sy, sx, rng):
    """Гладкий периодический шум N(0,1) с масштабами sy, sx (пикс.) — через FFT."""
    a = rng.normal(0, 1, (h, w)).astype(np.float32)
    f = np.fft.rfft2(a)
    ky = np.fft.fftfreq(h)[:, None].astype(np.float32)
    kx = np.fft.rfftfreq(w)[None, :].astype(np.float32)
    f *= np.exp(-((ky * sy * 2 * np.pi) ** 2 + (kx * sx * 2 * np.pi) ** 2) / 2)
    y = np.fft.irfft2(f, s=(h, w)).astype(np.float32)
    return (y - y.mean()) / (y.std() + 1e-6)


def _small_noise(h, w, cell, rng):
    """Гладкий шум через увеличение мелкой сетки (дёшево)."""
    a = rng.normal(0, 1, (h // cell + 3, w // cell + 3)).astype(np.float32)
    im = Image.fromarray(a, 'F').resize((w + 2 * cell, h + 2 * cell), Image.BICUBIC)
    return np.asarray(im, np.float32)[cell:cell + h, cell:cell + w]


# ─────────────────────────────── стол и свет ───────────────────────────────
def _wood(w, h, seed=11):
    """Тёмный орех: вертикальные доски, волокна, пятна тона, швы. → uint8 (h, w, 3)."""
    rng = np.random.default_rng(seed)
    h2 = (h + 1) // 2                                       # волокна гладкие по вертикали — считаем через строку
    fine = np.repeat(_noise2(h2, w, 35, 1.1, rng), 2, 0)[:h]
    mid = np.repeat(_noise2(h2, w, 120, 6.0, rng), 2, 0)[:h]
    big = _small_noise(h, w, 300, rng) / 0.6
    warp = _small_noise(h, w, 640, rng) * 34
    g = 0.06 * fine + 0.14 * mid                            # волокна периодичны по вертикали — доски сдвигаем без шва
    # доски: сдвиг рисунка по вертикали, свой тон, швы
    x = -int(rng.integers(40, 200))
    seams = []
    tone = np.zeros(w, np.float32)
    while x < w:
        pw = int(rng.integers(250, 360))
        x0, x1 = max(0, x), min(w, x + pw)
        if x1 > x0:
            g[:, x0:x1] = np.roll(g[:, x0:x1], int(rng.integers(0, h)), 0)
            tone[x0:x1] = rng.uniform(-0.05, 0.05)
        seams.append(x + pw)
        x += pw
    xi = np.clip(np.arange(w, dtype=np.int32)[None, :] + warp.astype(np.int32), 0, w - 1)
    g = np.take_along_axis(g, xi, 1)
    v = np.clip(0.5 + g + 0.06 * big + tone[None, :], 0, 1)
    stops = [(0.0, (20, 11, 7)), (0.3, (50, 30, 18)), (0.5, (76, 47, 28)), (0.7, (104, 67, 40)), (1.0, (142, 96, 60))]
    pos = [s[0] for s in stops]
    out = np.stack([np.interp(v, pos, [s[1][i] for s in stops]) for i in range(3)], -1).astype(np.float32)
    for sx in seams:
        if 0 <= sx < w - 4:
            out[:, sx:sx + 3] *= 0.32
            out[:, sx + 3:sx + 4] *= 1.25
    return np.clip(out, 0, 255).astype(np.uint8)


def _light(sx=620, sy=820, amb=0.38, k=0.64):
    """Карта света лампы (RGBA, больше кадра на LP с каждой стороны): тёплое пятно + виньетка."""
    h, w = H + 2 * LP, W + 2 * LP
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, LP + H * 0.45
    pool = np.exp(-0.5 * (((x - cx) / sx) ** 2 + ((y - cy) / sy) ** 2))
    b = amb + k * pool
    ys = y - LP                                             # ниже и выше безопасной зоны — темнее
    b *= 1 - 0.38 * np.clip((ys - 1490) / 430, 0, 1) - 0.22 * np.clip((210 - ys) / 210, 0, 1)
    b = np.clip(b, 0, 1.0)
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., 0] = b * 255
    arr[..., 1] = b * (0.89 + 0.09 * b) * 255
    arr[..., 2] = b * (0.70 + 0.21 * b) * 255
    arr[..., 3] = 255
    return Image.fromarray(arr, 'RGBA')


# ─────────────────────────────── бумага ───────────────────────────────
def _paper(w, h, base, seed, amp=3.2):
    rng = np.random.default_rng(seed)
    n1 = rng.normal(0, 1, (h, w)).astype(np.float32)
    n2 = _small_noise(h, w, 9, rng)
    v = np.array(base, np.float32)[None, None, :] + (amp * 0.45 * n1 + amp * n2)[..., None]
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    v = v * (1.0 - 0.025 * yy)                         # чуть темнее книзу
    return np.clip(v, 0, 255).astype(np.uint8)


def _sheet(w, h, base, seed, r=5, edge=(214, 208, 196), amp=3.2):
    im = Image.fromarray(_paper(w, h, base, seed, amp)).convert('RGBA')
    im.putalpha(C.rrect(w, h, r).getchannel('A'))
    if edge:
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), r, outline=tuple(edge) + (255,), width=1)
    return im


def _tape(w, h, seed, col=(232, 220, 186), a=200):
    """Кусок малярного скотча: рваные края, полупрозрачный."""
    rng = np.random.default_rng(seed)
    S = 3
    pts = []
    n = max(3, h // 5)
    for k in range(n + 1):                                  # левый рваный край сверху вниз
        pts.append((rng.uniform(0, 7), h * k / n))
    for k in range(n + 1):                                  # правый — снизу вверх
        pts.append((w - rng.uniform(0, 7), h * (n - k) / n))
    m = Image.new('L', (w * S, h * S), 0)
    ImageDraw.Draw(m).polygon([(px * S, py * S) for px, py in pts], fill=255)
    m = m.resize((w, h), Image.LANCZOS)
    tex = _paper(w, h, col, seed + 1, amp=5)
    im = Image.fromarray(tex).convert('RGBA')
    im.putalpha(m.point(lambda v: v * a // 255))
    return im


def _rich(parts, name, size, wght=700, max_w=None):
    """Строка из кусков разного цвета [(текст, цвет), …] одним шрифтом → RGBA (обрезка как у C.text)."""
    size = int(size)
    while True:
        f = C.font(name, size, wght)
        s = ''.join(p for p, _ in parts)
        tw = f.getlength(s)
        if not max_w or tw <= max_w or size <= 18:
            break
        size = max(18, int(size * max_w / tw * 0.99))
    asc, desc = f.getmetrics()
    pad = int(size * 0.3) + 2
    im = Image.new('RGBA', (int(math.ceil(tw)) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for p, col in parts:
        d.text((x, pad), p, font=f, fill=tuple(col) + (255,))
        x += f.getlength(p)
    bb = im.getchannel('A').getbbox()
    if bb:
        top = pad + max(0, int(asc - size * 0.78))
        im = im.crop((bb[0], min(top, bb[1]), bb[2], max(pad + asc + 1, bb[3])))
    return im


def _hand(s, size, col=MARK, max_w=None, wght=700):
    return C.text(s, 'hand', size, col, wght, max_w=max_w)


def _imprint(s, size):
    """Оранжевая дата-впечатка плёночной камеры (с ореолом)."""
    t = C.text(s, 'mono', size, AMBER, 700, track=0.06)
    return C.glow(t, 5, 0.9, (255, 110, 20))


def _shadow(im, soft=16, sa=0.5, hard=3, ha=0.42, dy_soft=12, dy_hard=3):
    """Тень предмета на столе (мягкая + контактная) — RGBA того же центра, с полями 3·soft."""
    pad = soft * 3
    a = im.getchannel('A')
    m = Image.new('L', (im.width + 2 * pad, im.height + 2 * pad), 0)
    m1 = m.copy()
    m1.paste(a, (pad + 3, pad + dy_soft))
    m1 = m1.filter(ImageFilter.GaussianBlur(soft)).point(lambda v: int(v * sa))
    m2 = m.copy()
    m2.paste(a, (pad, pad + dy_hard))
    m2 = m2.filter(ImageFilter.GaussianBlur(hard)).point(lambda v: int(v * ha))
    al = ImageChops.lighter(m1, m2)
    out = Image.new('RGBA', al.size, (12, 6, 2, 255))
    out.putalpha(al)
    return out


def _xf(im, rot, s, fine=True):
    if abs(s - 1) > 0.002:
        im = im.resize((max(1, int(round(im.width * s))), max(1, int(round(im.height * s)))), Image.BICUBIC)
    if abs(rot) > 0.03:
        im = im.rotate(rot, Image.BICUBIC if fine else Image.BILINEAR, expand=True)
    return im


# ─────────────────────────────── «снимки» ───────────────────────────────
def _vivid(c, lo=70, hi=215):
    c = np.array(c, np.float32)
    lum = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    if lum < lo:
        c = c + (lo - lum)
    elif lum > hi:
        c = c * (hi / lum)
    return tuple(int(v) for v in np.clip(c, 0, 255))


def _photo_bg(w, h, col, seed, cx=0.5, cy=0.4):
    """Фон «снимка» в цвете клуба: свет в центре, тёмные края, блики ламп арены, светлый лёд внизу. float32 RGB."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    y /= h
    x /= w
    c = np.array(_vivid(col), np.float32)
    hi = np.array(fresh.bright(tuple(int(v) for v in c), 0.28), np.float32)
    lo = c * 0.16 + 4
    r = np.sqrt(((x - cx) / 0.62) ** 2 + ((y - cy) / 0.7) ** 2)
    k = np.clip(r, 0, 1)[..., None] ** 1.25
    arr = hi[None, None, :] * (1 - k) + lo[None, None, :] * k
    # блики ламп арены
    for _ in range(9):
        bx, by = rng.uniform(0.05, 0.95), rng.uniform(0.02, 0.22)
        rr = rng.uniform(0.025, 0.06)
        d = np.sqrt(((x - bx) / rr) ** 2 + ((y - by) / rr) ** 2)
        arr += (np.clip(1 - d, 0, 1) ** 1.6 * rng.uniform(40, 90))[..., None] * np.array([1.0, 0.95, 0.85], np.float32)
    # лёд внизу
    ice = np.clip((y - 0.74) / 0.26, 0, 1) ** 1.3
    arr = arr * (1 - 0.45 * ice[..., None]) + np.array([214, 226, 236], np.float32) * 0.45 * ice[..., None]
    # мягкая виньетка «объектива»
    vg = np.sqrt(((x - 0.5) / 0.5) ** 2 + ((y - 0.5) / 0.5) ** 2)
    arr *= (1 - 0.32 * np.clip(vg - 0.55, 0, 1) ** 1.2)[..., None]
    return arr


def _grade(arr):
    """Плёночная обработка: тёплые света, чуть приподнятые тени, мягкое зерно."""
    arr = arr * np.array([1.04, 1.0, 0.93], np.float32) + np.array([7, 4, 2], np.float32)
    arr = 10 + arr * (236 / 255)
    return np.clip(arr, 0, 255)


def _emb_shadow(emb, r=10, a=0.55):
    return C.with_shadow(emb, r, a, 8)


class _Pic:
    """Снимок для проявки: финальная картинка (float32) + маска неравномерности проявки + блик глянца."""

    def __init__(self, img_rgb, seed):
        a = np.asarray(img_rgb.convert('RGB'), np.float32)
        self.h, self.w = a.shape[:2]
        rng = np.random.default_rng(seed)
        self.noise = np.clip(_small_noise(self.h, self.w, 40, rng) * 0.5, -1, 1)
        y, x = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        band = (x / self.w * 0.8 + y / self.h * 0.55)
        sheen = np.exp(-((band - 0.42) / 0.12) ** 2) * 16 + np.exp(-((band - 0.62) / 0.04) ** 2) * 7
        self.sheen = sheen[..., None].astype(np.float32)
        self.img = a
        self.final = np.clip(a + self.sheen, 0, 255).astype(np.uint8)
        self.lum = (a @ np.array([0.3, 0.59, 0.11], np.float32))[..., None]

    def at(self, k):
        """Проявка k∈[0,1]: буро-серый → блёклый холодный → полный цвет."""
        if k >= 1:
            return self.final
        kk = np.clip(k * 1.3 - 0.06 + 0.2 * self.noise * (1 - k), 0, 1)[..., None]
        e1 = kk * kk * (3 - 2 * kk)
        e2 = np.clip((kk - 0.3) / 0.7, 0, 1)
        e2 = e2 * e2 * (3 - 2 * e2)
        col = self.lum + (self.img - self.lum) * e2
        col = 128 + (col - 128) * (0.45 + 0.55 * e2)
        col = col * (np.array([0.88, 0.96, 1.06], np.float32) * (1 - e2) + e2)
        base = np.array([66, 58, 50], np.float32)
        out = base * (1 - e1) + col * e1 + self.sheen
        return np.clip(out, 0, 255).astype(np.uint8)


# ─────────────────────────────── ролик ───────────────────────────────
class Polaroid(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 76, drop=21 * 60 / 76, line=None, team=7, clear=2,
                 hold=6, cta=3, seed=23, **kw):
        super().__init__(u, drop, seed)
        self.line = tuple(line) if line else None
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef = league, when, coef
        self.tag = F.tag(league)
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
        self.rec = {'h': sh or {}, 'a': sa or {}}
        self.s = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.team_n, self.clear_n, self.hold_n, self.cta_n = team, clear, hold, cta
        self.T1 = self.b(-(2 * team + clear))
        if self.T1 < 2.4:
            raise ValueError('мало времени до дропа для интро')
        self.T2 = self.b(-(team + clear))
        self.TCL = self.b(-clear)
        self.TC = self.b(hold)
        self.dur = self.b(hold + cta)
        self.pan = 0.5 * u
        self.cover_t = self.T1 - self.pan - 0.3
        self.key = (home, away, league, when, pick, coef, self.line, u, round(drop, 4), team, clear, hold, cta, seed)
        if self.key not in _CACHE:
            _CACHE[self.key] = self._prep()
        self.P = _CACHE[self.key]
        self._xc = {}

    # ── заготовки ──
    def _prep(self):
        P = {}
        P['wood'] = _wood(2 * SX + W + 2 * PX, H + 2 * PY, self.seed)
        P['light'] = _light()
        P['tlight'] = _light(470, 640, 0.42, 0.68)                       # стол — пятно лампы контрастнее, чем на бумаге
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)                    # перед дропом свет сужается в пятно
        b = 0.12 + 0.88 * np.exp(-0.5 * (((x - 480) / 300) ** 2 + ((y - 760) / 390) ** 2))
        sp = np.zeros((H, W, 4), np.uint8)
        sp[..., 0], sp[..., 1], sp[..., 2], sp[..., 3] = b * 255, b * 0.93 * 255, b * 0.82 * 255, 255
        P['spot'] = Image.fromarray(sp, 'RGBA')
        tg = C.text(self.tag, 'unb', 32, CREAM, 600, track=0.1)
        P['tag'] = C.with_shadow(tg, 6, 0.8, 2)
        hd = C.text(C.HANDLE, 'unb', 46, CREAM, 700)
        P['handle'] = C.with_shadow(hd, 7, 0.85, 3)
        rng = np.random.default_rng(self.seed + 99)                     # пылинки в луче лампы
        P['mote'] = [C.radial(d, d, (255, 232, 190), 255, 1.6) for d in (5, 8, 12, 30)]
        P['motes'] = [(rng.uniform(0, W + 80), rng.uniform(0, 1300), rng.uniform(-9, 9), rng.uniform(-14, -4),
                       rng.uniform(0, 6.28), int(rng.choice([0, 0, 1, 1, 2, 3])), rng.uniform(0.25, 0.6)) for _ in range(22)]
        self.E = []
        self._intro_items()
        for side in ('h', 'a'):
            self._team_items(side)
        self._pick_items()
        for k, e in enumerate(self.E):
            e['z'] = k
            self._finish(e)
        P['E'] = self.E
        return P

    def _add(self, **e):
        e.setdefault('ovl', [])
        e.setdefault('dev', None)
        e.setdefault('exit', None)
        e.setdefault('lay2', None)
        e['id'] = len(self.E)
        self.E.append(e)
        return e

    def _finish(self, e):
        """Финальный вид предмета (проявлен, все надписи), его тень и момент, после которого он неподвижен."""
        im = e['base'].copy()
        t_done = e['enter']['t0'] + 0.25
        if e['dev']:
            dv = e['dev']
            im.paste(Image.fromarray(dv['pic'].final), dv['box'])
            t_done = max(t_done, dv['t0'] + dv['d'])
        for o in e['ovl']:
            C.put(im, o['im'], o['x'], o['y'], anchor='tl')
            t_done = max(t_done, o['t0'] + o['d'] + 0.02)
        e['final'] = im
        e['t_done'] = t_done
        e['shadow'] = _shadow(im, **e.get('shadow_kw', {}))

    def _polaroid(self, w, h, bd, bot, pic_img, seed):
        """Полароид: бумага с «колодцем» снимка. → (бумага RGBA, место снимка (x, y), _Pic)."""
        im = _sheet(w, h, PAPER, seed)
        iw, ih = w - 2 * bd, h - bd - bot
        d = ImageDraw.Draw(im)
        d.rectangle((bd - 2, bd - 2, bd + iw + 1, bd + ih + 1), fill=(196, 190, 178, 255))
        d.line((bd - 2, bd + ih + 2, bd + iw + 1, bd + ih + 2), fill=(255, 255, 252, 255), width=1)
        pic = _Pic(pic_img.resize((iw, ih), Image.LANCZOS) if pic_img.size != (iw, ih) else pic_img, seed + 5)
        return im, (bd, bd), pic

    def _caption(self, txt, size, max_w, col=MARK, rot=-1.2):
        im = _hand(txt, size, col, max_w=max_w)
        return C.rotate(im, rot)

    # ── снимки ──
    def _img_duo(self, w, h):
        left = _photo_bg(w, h, fresh.club(self.h), self.seed + 2, cx=0.26, cy=0.4)
        right = _photo_bg(w, h, fresh.club(self.a), self.seed + 3, cx=0.74, cy=0.4)
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        edge = w / 2 + (0.5 - y / h) * w * 0.16
        m = np.clip((x - edge) / 3 + 0.5, 0, 1)[..., None]
        arr = left * (1 - m) + right * m
        seam = np.exp(-((x - edge) / 2.2) ** 2)[..., None] * 70
        arr = _grade(arr + seam)
        img = Image.fromarray(arr.astype(np.uint8)).convert('RGBA')
        es = int(min(w * 0.4, h * 0.46))
        for tm, cx in ((self.h, w * 0.25), (self.a, w * 0.75)):
            C.put(img, _emb_shadow(tm.emb(es), 12, 0.6), cx, h * 0.41)
            nm = C.text(tm.up, 'osw', int(h * 0.098), (255, 255, 255), 700, max_w=w * 0.44, track=0.02)
            C.put(img, C.with_shadow(nm, 6, 0.85, 3), cx, h * 0.80)
        return img.convert('RGB')

    def _img_team(self, tm, w, h, seed, imprint=None, es=0.72, glow=False):
        arr = _grade(_photo_bg(w, h, fresh.club(tm), seed, cy=0.42))
        img = Image.fromarray(arr.astype(np.uint8)).convert('RGBA')
        if glow:
            img = C.add_light(img, C.radial(int(w * 0.95), int(w * 0.95), (255, 240, 210), 80, 1.5), w / 2, h * 0.44)
        C.put(img, _emb_shadow(tm.emb(int(w * es)), 14, 0.6), w / 2, h * 0.46)
        if imprint:
            ip = _imprint(imprint, max(24, int(w * 0.082)))
            C.put(img, ip, w - 14 - ip.width / 2, h - 12 - ip.height / 2)
        return img.convert('RGB')

    def _img_game(self, g, w, h, seed):
        ok = g.get('opp_key')
        opp = C.Team(ok) if ok else None
        col = fresh.club(opp) if opp else (90, 96, 110)
        arr = _grade(_photo_bg(w, h, col, seed, cy=0.36))
        img = Image.fromarray(arr.astype(np.uint8)).convert('RGBA')
        if opp:
            C.put(img, _emb_shadow(opp.emb(int(w * 0.5)), 10, 0.6), w / 2, h * 0.36)
        sc = C.text(g['score'], 'osw', int(h * 0.3), (255, 255, 255), 700)
        nt = C.text(g['note'], 'osw', int(h * 0.13), (255, 226, 150), 700) if g['note'] else None
        tw = sc.width + (nt.width + 8 if nt else 0)
        x0 = w / 2 - tw / 2
        cy = h * 0.765
        C.put(img, C.with_shadow(sc, 8, 0.85, 4), x0 + sc.width / 2, cy)
        if nt:
            C.put(img, C.with_shadow(nt, 6, 0.85, 3), x0 + sc.width + 8 + nt.width / 2, cy + sc.height / 2 - nt.height / 2 - 2)
        if g['date']:
            ip = _imprint(g['date'], max(20, int(w * 0.075)))
            C.put(img, ip, w - 10 - ip.width / 2, 12 + ip.height / 2)
        return img.convert('RGB')

    def _sticker(self, r, d=78):
        col = WIN_C if r == 'В' else LOSS_C if r == 'П' else (130, 130, 140)
        S = 3
        im = Image.new('RGBA', (d * S, d * S), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        dr.ellipse((0, 0, d * S - 1, d * S - 1), fill=(255, 255, 255, 255))
        dr.ellipse((5 * S, 5 * S, d * S - 1 - 5 * S, d * S - 1 - 5 * S), fill=tuple(col) + (255,))
        im = im.resize((d, d), Image.LANCZOS)
        C.put(im, C.text(r or '?', 'unb', int(d * 0.46), (255, 255, 255), 800), d / 2, d / 2 + 1)
        return C.with_shadow(im, 4, 0.45, 2)

    # ── бирки, карточки, ленты ──
    def _label(self, lab, val, w=300, h=204, seed=0):
        """Бумажная бирка линии: «П1» мелко, кэф крупно; сверху — скотч."""
        mt = 26
        im = Image.new('RGBA', (w, h + mt), (0, 0, 0, 0))
        sh = _sheet(w, h, CARD, seed, r=4, edge=(210, 200, 182))
        im.alpha_composite(sh, (0, mt))
        C.put(im, C.text(lab, 'osw', 50, (128, 108, 86), 600, track=0.08), w / 2, mt + 46)
        C.put(im, C.text(val, 'osw', 118, (24, 26, 32), 700, max_w=w - 30), w / 2, mt + 134)
        tp = C.rotate(_tape(int(w * 0.5), 46, seed + 3), (seed % 5 - 2) * 2.2)
        C.put(im, tp, w / 2 + (seed % 3 - 1) * 14, mt + 2)
        return im

    def _card_rows(self, side):
        s, rec = self.s[side], self.rec[side]
        rows = []
        if s['points'] is not None:
            r = [('%d' % s['points'], RED), (' ' + plural(s['points'], 'очко', 'очка', 'очков'), INK)]
            if s['gp'] is not None:
                r += [(' за ', INK), ('%d' % s['gp'], RED), (' ' + plural(s['gp'], 'игру', 'игры', 'игр'), INK)]
            rows.append(r)
        elif s['gp'] is not None:
            rows.append([('%d' % s['gp'], RED), (' ' + plural(s['gp'], 'игра', 'игры', 'игр') + ' в сезоне', INK)])
        if s['place'] is not None:
            rows.append([('%d-е' % s['place'], RED), (' место' + (' ' + s['place_scope'] if s['place_scope'] else ''), INK)])
        if s['gd'] is not None:
            rows.append([('разница шайб ', INK), (F.gd_txt(s['gd']), RED)])
        st = _streak(rec.get('streak'))
        if st:
            rows.append([(st[0], RED), (st[1], INK)])
        pp = _fnum(rec.get('pp'))
        if pp is not None and len(rows) < 5:
            v = ('%.1f' % pp).rstrip('0').rstrip('.').replace('.', ',') + '%'
            rows.append([('большинство ', INK), (v, RED)])
        return rows[:5]

    def _card(self, rows, w=588, seed=0):
        """Карточка в линейку на скотче; строки — отдельными надписями (пишутся от руки по долям)."""
        lh, top, mt = 82, 30, 24
        n = max(1, len(rows))
        h = top + n * lh + 26
        im = Image.new('RGBA', (w, h + mt), (0, 0, 0, 0))
        sh = _sheet(w, h, CARD, seed, r=4, edge=(212, 202, 186))
        d = ImageDraw.Draw(sh)
        for k in range(n + 1):
            yy = top + k * lh + lh - 12
            if yy < h - 6:
                d.line((10, yy, w - 10, yy), fill=(150, 178, 214, 255), width=2)
        d.line((54, 6, 54, h - 6), fill=(226, 128, 124, 255), width=2)
        im.alpha_composite(sh, (0, mt))
        tp = C.rotate(_tape(170, 48, seed + 7), 3 if seed % 2 else -3)
        C.put(im, tp, w / 2, mt + 4)
        ovl = []
        f = C.font('hand', 70, 700)
        widest = max(f.getlength(''.join(p for p, _ in parts)) for parts in rows) if rows else 1
        size = int(min(72, 70 * (w - 92) / widest))
        for k, parts in enumerate(rows):
            ri = _rich(parts, 'hand', size, 700)
            ovl.append(dict(im=ri, x=72, y=mt + top + k * lh + (lh - 12) - ri.height - 2))
        return im, ovl

    def _dymo(self, s, h, max_w, col=(26, 26, 30), seed=0):
        """Тиснёная лента этикет-пистолета: белые выпуклые буквы на глянцевой ленте."""
        size = int(h * 0.56)
        track = 0.07
        while True:
            f = C.font('osw', size, 700)
            ws = [f.getlength(c) for c in s]
            tw = sum(ws) + track * size * (len(s) - 1)
            if tw + h * 0.9 <= max_w or size < 30:
                break
            size = int(size * 0.96)
        w = int(tw + h * 0.9)
        rng = np.random.default_rng(seed)
        # лента
        base = np.zeros((h, w, 3), np.float32) + np.array(col, np.float32)
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        gloss = 34 * np.exp(-((yy - 0.16) / 0.1) ** 2) - 12 * yy
        base = base + gloss + rng.normal(0, 2.2, (h, w, 1)).astype(np.float32)
        tape = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert('RGBA')
        S = 3
        m = Image.new('L', (w * S, h * S), 0)
        c = h * 0.12 * S
        ImageDraw.Draw(m).polygon([(c, 0), (w * S - c * 0.6, 0), (w * S, c), (w * S - c * 0.3, h * S), (c * 0.4, h * S), (0, h * S - c)],
                                  fill=255)
        tape.putalpha(m.resize((w, h), Image.LANCZOS))
        # буквы: маска, тень снизу, светлая кромка сверху
        asc, desc = f.getmetrics()
        tm = Image.new('L', (w, h), 0)
        dr = ImageDraw.Draw(tm)
        x = (w - tw) / 2
        y = (h - (asc - size * 0.22)) / 2 - size * 0.2
        for ch, cw in zip(s, ws):
            dr.text((x, y), ch, font=f, fill=255)
            x += cw + track * size
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 255))
        sh.putalpha(ImageChops.offset(tm, 1, 3).point(lambda v: v * 150 // 255))
        tape.alpha_composite(sh)
        hl = Image.new('RGBA', (w, h), (255, 255, 255, 255))
        hl.putalpha(ImageChops.offset(tm, 0, -1).point(lambda v: v * 120 // 255))
        tape.alpha_composite(hl)
        fg = Image.new('RGBA', (w, h), (236, 236, 230, 255))
        fg.putalpha(tm)
        tape.alpha_composite(fg)
        a = tape.getchannel('A')
        tape.putalpha(ImageChops.multiply(a, m.resize((w, h), Image.LANCZOS)))
        return tape

    def _sticky(self, w=330, h=330, seed=0):
        rng = np.random.default_rng(seed)
        top = np.array([253, 226, 96], np.float32)
        bot = np.array([240, 200, 66], np.float32)
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        arr = top * (1 - yy) + bot * yy + rng.normal(0, 2.0, (h, w, 1)).astype(np.float32)
        arr[:int(h * 0.16)] *= 0.975                       # клеевая полоса
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')
        S = 3
        m = Image.new('L', (w * S, h * S), 0)
        cut = 16 * S
        ImageDraw.Draw(m).polygon([(0, 0), (w * S, 0), (w * S, h * S - cut), (w * S - cut * 1.6, h * S), (0, h * S)], fill=255)
        im.putalpha(m.resize((w, h), Image.LANCZOS))
        return im

    # ── сцены ──
    def _intro_items(self):
        u = self.u
        pw, ph, bd, bot = 720, 800, 30, 150
        img = self._img_duo(pw - 2 * bd, ph - bd - bot)
        paper, box, pic = self._polaroid(pw, ph, bd, bot, img, self.seed + 10)
        cap = self._caption(self.when, 80, pw - 70, MARK)
        e = self._add(base=paper, x=540, y=726, rot=-2.0, wx=0,
                      enter=dict(kind='fall', t0=0.15, d=0.24, ox=-40, oy=-150, dr=-7),
                      dev=dict(pic=pic, box=box, t0=0.15, d=1.25 * u))
        e['ovl'].append(dict(im=cap, x=(pw - cap.width) / 2, y=ph - bot / 2 - cap.height / 2 + 2, t0=0.42, d=0.5, mode='wipe'))
        if self.line:
            tb = self.b(math.ceil((0.45 - self.drop) / u))              # первая доля после падения снимка
            xs, ys, rots = (185, 540, 895), (1272, 1280, 1270), (-3.0, 1.5, 3.2)
            for k, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), self.line)):
                self._add(base=self._label(lab, C.fmt_k(v), seed=self.seed * 3 + k), x=xs[k], y=ys[k], rot=rots[k], wx=0,
                          enter=dict(kind='slap', t0=tb + 0.5 * k * u, d=0.13, ox=0, oy=-40, dr=4 * (1 if k % 2 else -1)))

    def _team_items(self, side):
        u = self.u
        T = self.T1 if side == 'h' else self.T2
        wx = SX if side == 'h' else 2 * SX
        tm = self.h if side == 'h' else self.a
        s = self.s[side]
        mir = side == 'a'
        X = (lambda x: W - x) if mir else (lambda x: x)
        sg = -1 if mir else 1
        sd = self.seed * 17 + (0 if side == 'h' else 100)
        # снимок клуба
        pw, ph, bd, bot = 372, 458, 22, 104
        img = self._img_team(tm, pw - 2 * bd, ph - bd - bot, sd + 1, imprint='ХОЗЯЕВА' if side == 'h' else 'ГОСТИ')
        paper, box, pic = self._polaroid(pw, ph, bd, bot, img, sd + 2)
        cap = self._caption(tm.short, 80, pw - 50)
        e = self._add(base=paper, x=X(226), y=598, rot=-4.0 * sg, wx=wx,
                      enter=dict(kind='fall', t0=T, d=0.24, ox=-50 * sg, oy=-140, dr=-8 * sg),
                      dev=dict(pic=pic, box=box, t0=T, d=1.0 * u))
        e['ovl'].append(dict(im=cap, x=(pw - cap.width) / 2, y=ph - bot / 2 - cap.height / 2 + 2, t0=T + 0.22, d=0.42, mode='wipe'))
        e['exit'] = self._exit(side, 0)
        # карточка с цифрами
        rows = self._card_rows(side)
        if rows:
            im, ovl = self._card(rows, seed=sd + 3)
            e = self._add(base=im, x=X(744), y=592, rot=2.0 * sg, wx=wx,
                          enter=dict(kind='slap', t0=T + 0.5 * u, d=0.14, ox=30 * sg, oy=-50, dr=5 * sg),
                          shadow_kw=dict(soft=12, sa=0.42, dy_soft=9))
            times = [1.5, 2.5, 3.5, 4.0, 4.5]
            for k, o in enumerate(ovl):
                o.update(t0=T + times[k] * u, d=0.42, mode='wipe')
                e['ovl'].append(o)
            e['exit'] = self._exit(side, 1)
        # три последние игры
        gw, gh, gbd, gbot = 320, 392, 17, 86
        xs, ys, rots = (198, 540, 882), (1142, 1162, 1138), (-4.6, 2.2, 5.0)
        for k, g in enumerate(s['games'][:3]):
            img = self._img_game(g, gw - 2 * gbd, gh - gbd - gbot, sd + 10 + k)
            paper, box, pic = self._polaroid(gw, gh, gbd, gbot, img, sd + 20 + k)
            t0 = T + (1 + k) * u
            e = self._add(base=paper, x=xs[k], y=ys[k], rot=rots[k], wx=wx,
                          enter=dict(kind='fall', t0=t0, d=0.22, ox=(k - 1) * 40, oy=-130, dr=8 * (1 if k % 2 else -1)),
                          dev=dict(pic=pic, box=box, t0=t0, d=0.9 * u))
            cap = self._caption(g['opp'], 64, gw - 40, rot=-1.0 + k)
            e['ovl'].append(dict(im=cap, x=(gw - cap.width) / 2, y=gh - gbot / 2 - cap.height / 2 + 1, t0=t0 + 0.14, d=0.36,
                                 mode='wipe'))
            st = self._sticker(g['res'])
            e['ovl'].append(dict(im=st, x=gbd - 22, y=gbd - 22, t0=t0 + 0.5 * u, d=0.14, mode='pop'))
            e['exit'] = self._exit(side, 2 + k)

    def _exit(self, side, k):
        """Сметание со стола перед дропом (только у второй команды; первая уходит панорамой)."""
        if side != 'a':
            return None
        dirs = [(-900, -260, -24), (900, -300, 20), (-1000, 380, -30), (60, 1100, 18), (1000, 420, 28)]
        dx, dy, dr = dirs[k % len(dirs)]
        return dict(t0=self.TCL + 0.055 * k, d=0.5, dx=dx, dy=dy, dr=dr)

    def _pick_items(self):
        u, D, TC = self.u, self.drop, self.TC
        wx = 2 * SX
        tm = self.fav
        sd = self.seed * 31
        pw, ph, bd, bot = 620, 720, 30, 132
        img = self._img_team(tm, pw - 2 * bd, ph - bd - bot, sd + 1, imprint=None, es=0.74, glow=True)
        paper, box, pic = self._polaroid(pw, ph, bd, bot, img, sd + 2)
        cap = self._caption(tm.short, 100, pw - 80)
        e = self._add(base=paper, x=468, y=692, rot=-3.0, wx=wx,
                      enter=dict(kind='eject', t0=D, d=0.26),
                      dev=dict(pic=pic, box=box, t0=D, d=0.6 * u, pow=0.5),
                      lay2=dict(t0=TC, d=0.45, x=322, y=612, s=0.72, rot=-4.0))
        e['ovl'].append(dict(im=cap, x=(pw - cap.width) / 2, y=ph - bot / 2 - cap.height / 2 + 2, t0=D + 0.3, d=0.42, mode='wipe'))
        d1 = self._dymo(self.pick1, 136, 980, seed=sd + 5)
        self._add(base=d1, x=540, y=1168, rot=-1.6, wx=wx, enter=dict(kind='slap', t0=D + 0.1, d=0.1, ox=0, oy=-30, dr=-3),
                  shadow_kw=dict(soft=8, sa=0.5, dy_soft=6, hard=2, ha=0.5),
                  lay2=dict(t0=TC, d=0.45, x=540, y=976, s=0.9, rot=-1.2))
        if self.pick2:
            d2 = self._dymo(self.pick2, 100, 760, col=(150, 26, 34), seed=sd + 6)
            self._add(base=d2, x=566, y=1304, rot=1.3, wx=wx, enter=dict(kind='slap', t0=D + 0.5 * u, d=0.12, ox=0, oy=-30, dr=3),
                      shadow_kw=dict(soft=8, sa=0.5, dy_soft=6, hard=2, ha=0.5),
                      lay2=dict(t0=TC, d=0.45, x=540, y=1090, s=0.92, rot=1.0))
        if self.coef:
            st = self._sticky(306, 306, seed=sd + 7)
            C.put(st, _hand('кэф', 70, (92, 70, 30)), 153, 68)
            val = C.text(C.fmt_k(self.coef), 'hand', 156, MARK, 700, max_w=226)
            C.put(st, val, 153, 184)
            ring = self._ring(min(300, val.width + 84), val.height + 54)
            e = self._add(base=st, x=860, y=872, rot=6.0, wx=wx,
                          enter=dict(kind='slap', t0=D + u, d=0.14, ox=40, oy=-60, dr=8),
                          shadow_kw=dict(soft=12, sa=0.5, dy_soft=12),
                          lay2=dict(t0=TC, d=0.45, x=806, y=600, s=0.88, rot=7.0))
            e['ovl'].append(dict(im=ring, x=153 - ring.width / 2, y=186 - ring.height / 2, t0=D + 2 * u, d=0.42, mode='arc'))
        tg = C.tg_plate(960, 180, font='mont')
        self._add(base=tg, x=540, y=1300, rot=0.0, wx=wx, enter=dict(kind='slap', t0=TC + 0.34, d=0.18, ox=0, oy=40, dr=-2),
                  shadow_kw=dict(soft=14, sa=0.55, dy_soft=12))

    def _ring(self, w, h):
        """Обводка маркером (рисуется по дуге при появлении — mode 'arc')."""
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        S = 3
        big = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(big)
        d.arc((8 * S, 8 * S, (w - 8) * S, (h - 8) * S), -200, 165, fill=RED + (235,), width=8 * S)
        d.arc((14 * S, 4 * S, (w - 4) * S, (h - 14) * S), 160, 200, fill=RED + (235,), width=7 * S)
        im = big.resize((w, h), Image.LANCZOS)
        return im

    # ── время и камера ──
    def _cam(self, t):
        x = 0.0
        for k, T in enumerate((self.T1, self.T2)):
            x += SX * C.in_out(C.seg(t, T - self.pan, T))
        return x

    def _drift(self, t):
        dx = 13 * math.sin(0.41 * t + 0.3) + 4 * math.sin(1.07 * t + 2.0)
        dy = 9 * math.sin(0.33 * t + 1.2) + 3 * math.sin(0.87 * t)
        for tl, amp in ((0.15, 7), (self.drop, 9)):
            sx, sy = C.shake(t, tl, amp, 0.3)
            dx += sx
            dy += sy
        return dx, dy

    def _pose(self, e, t):
        """→ None | (x, y, rot, s, z, a, settled) в координатах мира."""
        en = e['enter']
        t0, kind, fd = en['t0'], en['kind'], en.get('d', 0.2)
        if t < (t0 if kind == 'eject' else t0 - fd):                  # 'eject' появляется ровно в t0 (дроп)
            return None
        x, y, rot, s = e['x'] + e['wx'], e['y'], e['rot'], 1.0
        z, a = 0.0, 1.0
        settled = True
        if kind in ('fall', 'slap'):
            if t < t0:
                p = C.seg(t, t0 - fd, t0)
                z = 1 - _ease_fall(p)
                a = C.seg(t, t0 - fd, t0 - fd + 0.05)
                settled = False
            else:
                q = (t - t0) / 0.2
                if q < 1:
                    z = 0.07 * math.sin(math.pi * q) * (1 - q)
                    settled = False
            zs = 0.32 if kind == 'fall' else 0.2
            x += en['ox'] * z
            y += en['oy'] * z
            rot += en['dr'] * z
            s = 1 + zs * z
        elif kind == 'eject':
            q = C.out_cubic(C.seg(t, t0, t0 + fd))
            if q < 1:
                settled = False
            z = 0.5 * (1 - q)
            s = 1 + 0.14 * (1 - q)
            rot += 4 * (1 - q)
        ex = e['exit']
        if ex and t >= ex['t0']:
            p = C.in_cubic(C.seg(t, ex['t0'], ex['t0'] + ex['d']))
            if p >= 1:
                return None
            x += ex['dx'] * p
            y += ex['dy'] * p
            rot += ex['dr'] * p
            settled = False
        L = e['lay2']
        if L and t >= L['t0']:
            p = C.out_cubic(C.seg(t, L['t0'], L['t0'] + L['d']))
            x = C.lerp(x, L['x'] + e['wx'], p)
            y = C.lerp(y, L['y'], p)
            rot = C.lerp(rot, L['rot'], p)
            s *= C.lerp(1.0, L['s'], p)
            if p < 1:
                settled = False
        return x, y, rot, s, z, a, settled

    def _sprite(self, e, t):
        if t >= e['t_done']:
            return e['final'], True
        im = e['base'].copy()
        dv = e['dev']
        if dv:
            k = C.seg(t, dv['t0'], dv['t0'] + dv['d']) ** dv.get('pow', 1.0)
            im.paste(Image.fromarray(dv['pic'].at(k)), dv['box'])
        for o in e['ovl']:
            if t < o['t0']:
                continue
            p = C.seg(t, o['t0'], o['t0'] + o['d'])
            oi = o['im']
            if o['mode'] == 'wipe' and p < 1:
                ww = max(1, int(oi.width * p))
                C.put(im, oi.crop((0, 0, ww, oi.height)), o['x'], o['y'], anchor='tl')
            elif o['mode'] == 'pop' and p < 1:
                sc = 1 + 0.5 * (1 - C.out_back(p, 2.2))
                si = C.scale(oi, max(0.3, sc))
                C.put(im, si, o['x'] + oi.width / 2, o['y'] + oi.height / 2, min(1.0, p * 3))
            elif o['mode'] == 'arc' and p < 1:
                cx, cy = oi.width / 2, oi.height / 2
                m = Image.new('L', oi.size, 0)
                R = max(oi.size)
                ang = -200 + 365 * C.out_cubic(p)
                ImageDraw.Draw(m).pieslice((cx - R, cy - R, cx + R, cy + R), -200, ang, fill=255)
                part = oi.copy()
                part.putalpha(ImageChops.multiply(oi.getchannel('A'), m))
                C.put(im, part, o['x'], o['y'], anchor='tl')
            else:
                C.put(im, oi, o['x'], o['y'], anchor='tl')
        return im, False

    def _draw(self, fr, e, t, ox, oy):
        ps = self._pose(e, t)
        if ps is None:
            return
        x, y, rot, s, z, a, settled = ps
        sx, sy = x - ox, y - oy
        r = max(e['base'].width, e['base'].height) * s * 0.75
        if sx + r < 0 or sx - r > W or sy + r < 0 or sy - r > H:
            return
        spr, done = self._sprite(e, t)
        if done and settled:
            key = (e['id'], round(rot, 3), round(s, 4))
            if key not in self._xc:
                self._xc[key] = (_xf(spr, rot, s), _xf(e['shadow'], rot, s, False))
            im, shd = self._xc[key]
        else:
            im, shd = _xf(spr, rot, s), _xf(e['shadow'], rot, s, False)
        C.put(fr, shd, sx + 30 * z, sy + 62 * z, a * (1 - 0.5 * z))
        C.put(fr, im, sx, sy, a)

    def _motes(self, fr, t, lx, ly):
        for x0, y0, vx, vy, ph, k, a0 in self.P['motes']:
            x = (x0 + vx * t + 16 * math.sin(0.6 * t + ph)) % (W + 80) - 40
            y = (y0 + vy * t + 12 * math.sin(0.45 * t + 2 * ph)) % 1300 + 240
            d2 = ((x - W / 2 - lx) / 560) ** 2 + ((y - H * 0.45 - ly) / 760) ** 2
            a = a0 * (0.55 + 0.45 * math.sin(2.1 * t + 3 * ph)) * math.exp(-d2)
            if k == 3:
                a *= 0.3
            C.put(fr, self.P['mote'][k], x, y, a)

    # ── кадр ──
    def frame(self, t):
        u, D = self.u, self.drop
        P = self.P
        cam = self._cam(t)
        dx, dy = self._drift(t)
        # стол (чуть медленнее предметов — параллакс)
        bx = int(round(PX + cam + 0.82 * dx))
        by = int(round(PY + 0.82 * dy))
        bx = min(max(0, bx), P['wood'].shape[1] - W)
        by = min(max(0, by), P['wood'].shape[0] - H)
        lx = int(LP + 34 * math.sin(0.52 * t + 0.6))
        ly = int(LP + 18 * math.sin(0.37 * t + 2.1))
        fr = Image.fromarray(P['wood'][by:by + H, bx:bx + W]).convert('RGBA')
        fr = ImageChops.multiply(fr, P['tlight'].crop((lx, ly, lx + W, ly + H)))
        ox, oy = cam + dx, dy
        for e in P['E']:
            self._draw(fr, e, t, ox, oy)
        # панорама — смаз по горизонтали
        v = abs(self._cam(t + 0.01) - self._cam(t - 0.01)) / 0.02
        k = int(v / C.FPS * 0.45)
        if k >= 3:
            fr = fr.resize((max(1, W // k), H), Image.BOX).resize((W, H), Image.BILINEAR)
        # свет лампы (качается)
        fr = ImageChops.multiply(fr, P['light'].crop((lx, ly, lx + W, ly + H)))
        self._motes(fr, t, lx - LP, ly - LP)
        # камера: наезд перед дропом, пульс на долях после
        z = 1.0
        if self.TCL <= t < D:
            z += 0.07 * C.in_out(C.seg(t, self.TCL + 0.3, D))
        for n in (-12, -4):
            tb = self.b(n)
            if tb <= t < tb + 0.35:
                z += 0.016 * (1 - C.seg(t, tb, tb + 0.35)) ** 2
        if D <= t < self.TC:
            z += 0.035 * (1 - C.out_cubic(C.seg(t, D, D + 0.4)))
            for n in range(2, self.hold_n):
                tb = self.b(n)
                if tb <= t < tb + 0.3:
                    z += 0.014 * (1 - C.seg(t, tb, tb + 0.3)) ** 2
        if z > 1.001:
            fr = C.zoom(fr, z, W / 2, H * 0.48)
        # перед дропом лампа сужается в пятно (там ляжет снимок) и подмигивает; на дропе — вспышка
        dim = 1.0
        if self.TCL + 0.3 <= t < D:
            q = C.in_out(C.seg(t, self.TCL + 0.3, D - 0.1))
            fr = Image.blend(fr, ImageChops.multiply(fr, P['spot']), 0.9 * q)
            if q > 0.4 and math.sin(t * 61) > 0.8:
                dim = 0.88
        flash = 0.0
        if t >= D:
            flash = math.exp(-(t - D) / 0.08)
            if flash < 0.01:
                flash = 0.0
        if dim < 0.999 or flash > 0:
            lut = [int(min(255, v * dim + (255 - v * dim) * flash)) for v in range(256)]
            fr = fr.point(lut * 3 + list(range(256)))
        fr = C.grain(fr, t, k=6)
        # экранные подписи
        _paste(fr, P['tag'], W / 2, TAG_Y)
        if t < self.TC + 0.14:
            a = 1.0 if t < self.TC else 1 - C.seg(t, self.TC, self.TC + 0.14)
            _paste(fr, P['handle'], W / 2, HANDLE_Y, a)
        return fr


def _paste(fr, im, cx, cy, a=1.0):
    if a <= 0.003:
        return
    if a < 0.997:
        im = C.fade(im, a)
    fr.paste(im, (int(round(cx - im.width / 2)), int(round(cy - im.height / 2))), im)
