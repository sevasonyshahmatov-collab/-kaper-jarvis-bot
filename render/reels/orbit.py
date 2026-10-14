# -*- coding: utf-8 -*-
"""«Орбиты» — матч как звёздная система: глубокий космос и психоделика в духе Astroworld (фиолетово-оранжевая
туманность «дышит» между тёплой и холодной палитрой, звёзды в три слоя с медленным параллаксом). Каждая команда —
планета: полосатая газовая сфера в цветах клуба, эмблема «напечатана» на поверхности (с белой обводкой — читается на
любом цвете), атмосфера, контровой свет. Орбиты — эллипсы в перспективе (дальняя дуга уходит за планету, ближняя —
дугой вниз). Время сцен — в долях трека u от дропа (self.b(n)); все смены сцен и удары — на долях.

Сцены (по умолчанию дроп = 17 долей; трек DOWN DOWN, 61 BPM → u ≈ 0,98 с, дроп ≈ 16,7 с, ролик ≈ 23 с):
  интро (intro=3)    — обе планеты со своими кольцами и лунами, названия и роли, день и время МСК, линия основного
                       времени П1 · Х · П2 крупными плашками; на доли — пульс атмосфер;
  команда 1 (team=6) — камера перелетает к планете хозяев (параллакс звёзд); на доли и полудоли с планеты по спирали
                       стартуют луны и встают на свои орбиты: луна = один факт, плашка всегда прямо. Три луны
                       В/П (цвет луны — результат) — последние 3 игры: соперник, дата, дома/в гостях, счёт, ОТ/Б;
                       жемчужная луна — очки, игры, место, разница шайб; две малые луны по бокам планеты — серия
                       и большинство (или дома/в гостях), только если цифры есть; команда на экране ≈ 5,9 с;
  команда 2 (team=6) — то же для гостей (вход справа);
  сближение (near=2) — планеты сходятся, гравитационная линза тянет звёзды и туманность, растёт кольцо Эйнштейна;
                       на подхват трека (−¾ доли) — импульс линзы;
  ДРОП (hold=4)      — затмение: планета прогноза проходит впереди, вспышка короны и ударная волна по плоскости
                       орбит, вторая планета исчезает. Крупно — только выбранная команда (одна эмблема), «ПРОГНОЗ»,
                       текст прогноза (form.split_pick) и кэф на плашке, через которую идёт орбита; ≈ 3,9 с;
  финал (cta=2,5)    — «ВСЕ ПРОГНОЗЫ» и плашка Telegram (C.tg_plate, текст по центру плашки) прилетает по орбите.
@jarvibet — у низа безопасной зоны (y 1445) во всех сценах; сверху — тег лиги (form.tag). Кадр зависит только от t:
тяжёлые заготовки (туманность, текстуры планет, кольца) считаются в __init__ (до fork) и в кешах модуля.
"""
import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels import fresh
from reels.core import W, H

SPACE = (6, 3, 18)
VIOLET = (138, 76, 240)
MAGENTA = (236, 72, 170)
ORANGE = (255, 146, 60)
GOLD = (255, 204, 128)
WHITE = (255, 255, 255)
MUTE = (206, 196, 236)
GLASS = (22, 12, 46)
WIN = (52, 214, 120)
LOSS = (240, 76, 70)
TAG_Y, HANDLE_Y = 262, 1445
M = 150                                   # запас туманности под параллакс

# перспектива плоскости орбит: камера на высоте HC над плоскостью, планета на расстоянии ZP (в радиусах планеты)
ZP, HC = 10.0, 2.6
N2 = ZP * ZP + HC * HC
TILT = HC / math.sqrt(N2)

_RING, _GLASS, _MOON = {}, {}, {}


# ─────────────────────────────── геометрия орбит ───────────────────────────────
def proj(cx, cy, R, r, th):
    """Точка орбиты радиуса r (в радиусах планеты) под углом th → (x, y, k); th = π/2 — ближняя точка (низ)."""
    s, c = math.sin(th), math.cos(th)
    k = N2 / (N2 - ZP * r * s)
    return cx + R * r * c * k, cy + R * r * s * TILT * k, k


def ring_xy(cx, cy, R, r, n=720):
    th = np.linspace(0, 2 * math.pi, n)
    s, c = np.sin(th), np.cos(th)
    k = N2 / (N2 - ZP * r * s)
    return cx + R * r * c * k, cy + R * r * s * TILT * k, s


def theta_at_x(R, r, dx):
    """Угол ближней дуги, на котором орбита проходит через смещение dx от центра планеты."""
    sg = 1.0 if dx < 0 else -1.0
    th = math.pi / 2 + sg * np.linspace(0, math.pi / 2, 1200)
    fx = np.abs(R * r * np.cos(th) * N2 / (N2 - ZP * r * np.sin(th)))
    i = int(np.argmax(fx))
    return float(np.interp(abs(dx), fx[:i + 1], th[:i + 1]))


def ring_r(R, off):
    """Радиус орбиты, ближняя точка которой на off px ниже центра планеты радиуса R."""
    return off * N2 / (R * TILT * N2 + off * ZP)


def solve_r(R, dx, dy):
    """Радиус орбиты, ближняя дуга которой проходит через точку (dx, dy) от центра планеты."""
    lo, hi = 1.05, 10.2
    for _ in range(40):
        mid = (lo + hi) / 2
        th = theta_at_x(R, mid, dx)
        y = proj(0, 0, R, mid, th)[1]
        if y < dy:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def ring_layer(cx, cy, R, r, part, col=(200, 180, 255), a=150, width=3):
    """Кольцо орбиты (part='front' — ближняя половина, 'back' — дальняя) со сглаживанием и ореолом → (RGBA, x0, y0)."""
    key = (int(cx), int(cy), int(R), round(r, 3), part, col, a, width)
    if key in _RING:
        return _RING[key]
    x, y, s = ring_xy(cx, cy, R, r, 1440)
    m = (s >= 0) if part == 'front' else (s < 0)
    m &= (x > -300) & (x < W + 300) & (y > -300) & (y < H + 300)
    if m.sum() < 2:
        _RING[key] = None
        return None
    idx = np.nonzero(m)[0]
    # непрерывные куски
    runs, cur = [], [idx[0]]
    for i in idx[1:]:
        if i == cur[-1] + 1:
            cur.append(i)
        else:
            runs.append(cur)
            cur = [i]
    runs.append(cur)
    pad = 24
    x0 = int(max(0, x[m].min() - pad))
    x1 = int(min(W, x[m].max() + pad))
    y0 = int(max(0, y[m].min() - pad))
    y1 = int(min(H, y[m].max() + pad))
    if x1 - x0 < 4 or y1 - y0 < 4:
        _RING[key] = None
        return None
    S = 2
    big = Image.new('RGBA', ((x1 - x0) * S, (y1 - y0) * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    for run in runs:
        pts = [((x[i] - x0) * S, (y[i] - y0) * S) for i in run]
        if len(pts) > 1:
            d.line(pts, fill=tuple(col) + (int(a),), width=int(width * S), joint='curve')
    sharp = big.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    halo = Image.new('RGBA', sharp.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    for run in runs:
        pts = [(x[i] - x0, y[i] - y0) for i in run]
        if len(pts) > 1:
            hd.line(pts, fill=tuple(col) + (int(a * 0.45),), width=int(width * 5), joint='curve')
    halo = halo.filter(ImageFilter.GaussianBlur(7))
    halo.alpha_composite(sharp)
    _RING[key] = (halo, x0, y0)
    return _RING[key]


def draw_ring(d, cx, cy, R, r, part, col, a, width, n=360):
    """Кольцо прямо в кадр (без сглаживания) — для движущихся колец и ударной волны."""
    x, y, s = ring_xy(cx, cy, R, r, n)
    m = (s >= 0) if part == 'front' else (s < 0) if part == 'back' else np.ones_like(s, bool)
    pts, out = [], []
    for i in range(len(x)):
        if m[i] and -400 < x[i] < W + 400 and -400 < y[i] < H + 400:
            pts.append((float(x[i]), float(y[i])))
        elif pts:
            out.append(pts)
            pts = []
    if pts:
        out.append(pts)
    for p in out:
        if len(p) > 1:
            d.line(p, fill=tuple(col) + (int(a),), width=int(width), joint='curve')


# ─────────────────────────────── плашки, луны ───────────────────────────────
def glass(w, h, r, a=212, c1=VIOLET, c2=ORANGE, bw=3):
    """Стеклянная плашка: тёмное стекло с подсветкой сверху и градиентной рамкой (фиолетовый → оранжевый)."""
    w, h = int(w), int(h)
    key = (w, h, int(r), a, c1, c2, bw)
    if key in _GLASS:
        return _GLASS[key]
    base = C.rrect(w, h, r, GLASS, a)
    g = C.lgrad(w, h, (64, 34, 112), GLASS, 90, 255, 0)
    am = np.minimum(np.asarray(g.getchannel('A')), np.asarray(base.getchannel('A')))
    g.putalpha(Image.fromarray(am.astype(np.uint8)))
    base.alpha_composite(g)
    outer = C.rrect(w, h, r, WHITE).getchannel('A')
    inner = Image.new('L', (w, h), 0)
    inner.paste(C.rrect(w - 2 * bw, h - 2 * bw, max(1, r - bw), WHITE).getchannel('A'), (bw, bw))
    ring = ImageChops.subtract(outer, inner)
    grad = C.lgrad(w, h, c1, c2, 20)
    grad.putalpha(ring)
    base.alpha_composite(grad)
    _GLASS[key] = base
    return base


def moon(col, d, letter=None, lcol=WHITE):
    """Луна: шар с освещением слева сверху, бликом и контровым ободком; на ней — буква (В / П)."""
    key = (tuple(col), int(d), letter)
    if key in _MOON:
        return _MOON[key]
    S = 3
    D = int(d) * S
    yy, xx = np.mgrid[0:D, 0:D].astype(np.float32)
    px, py = (xx + 0.5 - D / 2) / (D / 2), (yy + 0.5 - D / 2) / (D / 2)
    rr = px * px + py * py
    nz = np.sqrt(np.clip(1 - rr, 0, 1))
    L = np.array([-0.5, -0.6, 0.62])
    L /= np.linalg.norm(L)
    lam = np.clip(px * L[0] + py * L[1] + nz * L[2], 0, 1)
    c = np.array(col, np.float32)
    lite = np.array(fresh.bright(tuple(col), 0.45), np.float32)
    rgb = c[None, None] * (0.35 + 0.75 * lam[..., None]) + lite * (lam[..., None] ** 6) * 0.35
    rgb += 255 * (lam[..., None] ** 40) * 0.55
    rim = np.clip((1 - nz) ** 3 * np.clip(px * 0.6 + py * 0.7, 0, 1), 0, 1)
    rgb += np.array(ORANGE, np.float32) * rim[..., None] * 0.8
    al = np.clip((1 - np.sqrt(rr)) * D / 2 + 0.5, 0, 1) * 255
    arr = np.dstack([np.clip(rgb, 0, 255), al]).astype(np.uint8)
    im = Image.fromarray(arr, 'RGBA').resize((int(d), int(d)), Image.LANCZOS)
    if letter:
        tx = C.text(letter, 'unb', d * 0.46, lcol, 900, stroke=2, stroke_fill=tuple(int(v * 0.45) for v in col))
        C.put(im, tx, d / 2, d / 2 + 1)
    _MOON[key] = im
    return im


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────── планета ───────────────────────────────
class Planet:
    """Газовая планета в цветах клуба с эмблемой на поверхности. Поверхность медленно вращается (полосы текут),
    эмблема — «наклейка» на обращённой к зрителю стороне (с лёгкой выпуклостью и тем же светом)."""

    D0 = 500
    TW, TH = 1024, 256

    def __init__(self, team, seed):
        rnd = np.random.default_rng(seed)
        self.team = team
        base = fresh.club(team)
        self.col = base
        self.lite = fresh.bright(base, 0.45)
        sec = None
        for c in (team.c2, team.c0, team.c1):
            if sum((a - b) ** 2 for a, b in zip(c, base)) ** 0.5 > 120:
                sec = tuple(c)
                break
        sec = sec or C.mix(base, WHITE, 0.6)
        dark = C.mix(base, SPACE, 0.62)
        D0, TW, TH = self.D0, self.TW, self.TH
        # ── текстура: полосы с турбулентностью (периодична по долготе) ──
        lat = np.linspace(-1, 1, TH, dtype=np.float32)[:, None]
        lon = np.linspace(0, 2 * math.pi, TW, endpoint=False, dtype=np.float32)[None, :]
        turb = np.zeros((TH, TW), np.float32)
        for k in range(7):
            f = int(rnd.integers(1, 7))
            turb += rnd.uniform(0.2, 0.6) / (1 + k * 0.4) * np.sin(f * lon + rnd.uniform(2, 9) * lat + rnd.uniform(0, 6.28))
        v = 0.5 + 0.5 * np.sin(lat * math.pi * 5.5 + turb * 1.5)
        v2 = 0.5 + 0.5 * np.sin(lat * math.pi * 12.5 + turb * 2.4 + 1.3)
        ramp = np.array([dark, base, self.lite], np.float32)
        vv = np.clip(v, 0, 1) * 2
        i0 = np.clip(vv.astype(int), 0, 1)
        fr = (vv - i0)[..., None]
        tex = ramp[i0] * (1 - fr) + ramp[i0 + 1] * fr
        sk = np.clip((v2 - 0.78) / 0.17, 0, 1)[..., None] * 0.8
        tex = tex * (1 - sk) + np.array(sec, np.float32) * sk
        # вихрь-«пятно»
        sy, sx = rnd.uniform(-0.5, 0.5), rnd.uniform(0, 2 * math.pi)
        dl = np.angle(np.exp(1j * (lon - sx)))
        spot = np.exp(-((dl / 0.32) ** 2 + ((lat - sy) / 0.1) ** 2))[..., None]
        tex = tex * (1 - 0.7 * spot) + np.array(sec, np.float32) * 0.7 * spot
        self.tex = np.clip(tex, 0, 255).astype(np.uint8)
        # ── геометрия сферы на D0 ──
        R0 = D0 / 2
        yy, xx = np.mgrid[0:D0, 0:D0].astype(np.float32)
        px, py = (xx + 0.5 - R0) / R0, (yy + 0.5 - R0) / R0
        rr = px * px + py * py
        al = np.clip((1 - np.sqrt(rr)) * R0 + 0.5, 0, 1)
        m = al > 0
        self.mask = m
        self.alpha = (al * 255).astype(np.uint8)
        nz = np.sqrt(np.clip(1 - rr, 0, 1))
        L = np.array([-0.55, -0.5, 0.67])
        L /= np.linalg.norm(L)
        lam = np.clip(px * L[0] + py * L[1] + nz * L[2], 0, 1)
        shade = 0.07 + 1.0 * lam ** 0.9
        L2 = np.array([0.75, 0.6, -0.25])
        L2 /= np.linalg.norm(L2)
        back = np.clip(px * L2[0] + py * L2[1] + nz * L2[2], 0, 1) ** 1.5 * (1 - nz) ** 0.8
        fres = (1 - nz) ** 2.5
        rimcol = (np.array(MAGENTA, np.float32)[None] * 0.55 + np.array(ORANGE, np.float32)[None] * 0.45) * back[m][:, None] * 0.95
        rimcol += np.array(self.lite, np.float32)[None] * (fres[m] * lam[m] ** 0.5)[:, None] * 0.55
        self.shade = shade[m][:, None].astype(np.float32)
        self.rim = rimcol.astype(np.float32)
        latv = np.arcsin(np.clip(py, -1, 1))
        lonv = np.arctan2(px, np.maximum(nz, 1e-4))
        self.lat_i = np.clip(((latv / (math.pi / 2)) * 0.5 + 0.5) * (TH - 1), 0, TH - 1).astype(np.int32)[m]
        self.lon_i = (((lonv + math.pi) / (2 * math.pi)) * TW).astype(np.int32)[m] % TW
        # ── эмблема-наклейка: координаты (долгота, широта) → чуть выпуклая, свет тот же ──
        emb = team.emb(int(D0 * 0.6))
        sw = max(6, int(D0 * 0.018))
        big = Image.new('RGBA', (emb.width + 4 * sw, emb.height + 4 * sw), (0, 0, 0, 0))
        big.alpha_composite(emb, (2 * sw, 2 * sw))
        a = big.getchannel('A').point(lambda q: 255 if q > 60 else 0).filter(ImageFilter.MaxFilter(2 * sw + 1))
        a = a.filter(ImageFilter.GaussianBlur(1.2))
        stk = Image.new('RGBA', big.size, (250, 248, 255, 255))
        stk.putalpha(a)
        shd = Image.new('RGBA', big.size, (8, 4, 20, 255))
        shd.putalpha(a.filter(ImageFilter.GaussianBlur(sw)).point(lambda q: int(q * 0.6)))
        dec = Image.new('RGBA', big.size, (0, 0, 0, 0))
        dec.alpha_composite(shd)
        dec.alpha_composite(stk)
        dec.alpha_composite(big)
        dw, dh = dec.size
        Sx = R0 * 1.0
        jj = np.clip(lonv * Sx + dw / 2, 0, dw - 1).astype(np.int32)
        ii = np.clip(latv * Sx + dh / 2, 0, dh - 1).astype(np.int32)
        inside = (np.abs(lonv * Sx) < dw / 2 - 1) & (np.abs(latv * Sx) < dh / 2 - 1) & m
        darr = np.asarray(dec).astype(np.float32)
        samp = darr[ii, jj]
        samp[~inside] = 0
        k = (0.6 + 0.42 * np.clip(shade, 0, 1.05))[..., None]
        samp[..., :3] = np.clip(samp[..., :3] * k, 0, 255)
        samp[..., 3] *= al
        self.decal = Image.fromarray(samp.astype(np.uint8), 'RGBA')
        # ── атмосфера (ореол снаружи диска) ──
        P = int(D0 * 0.34)
        A = D0 + 2 * P
        yy, xx = np.mgrid[0:A, 0:A].astype(np.float32)
        dx, dy = xx + 0.5 - A / 2, yy + 0.5 - A / 2
        dist = np.sqrt(dx * dx + dy * dy)
        out = np.clip(dist - R0, 0, None)
        prof = np.exp(-out / (D0 * 0.055)) * 0.85 + np.exp(-out / (D0 * 0.16)) * 0.35
        prof[dist < R0 - 2] = 0
        prof[(dist >= R0 - 2) & (dist < R0)] *= 0.6
        ang = (-(dx * L[0] + dy * L[1]) / np.maximum(dist, 1))       # освещённая сторона ярче
        lit = np.clip(0.55 + 0.6 * -ang, 0.25, 1.2)
        cA = np.array(self.lite, np.float32)
        cB = np.array(MAGENTA, np.float32) * 0.5 + np.array(ORANGE, np.float32) * 0.5
        wB = np.clip(ang * 0.9 + 0.3, 0, 1)[..., None]
        rgb = cA * (1 - wB) + cB * wB
        aa = np.clip(prof * lit * 255, 0, 255)
        self.atmo = Image.fromarray(np.dstack([rgb, aa]).astype(np.uint8), 'RGBA')

    def surface(self, phase):
        """Диск планеты D0×D0 при повороте phase (доля оборота)."""
        D0 = self.D0
        sh = int(phase * self.TW) % self.TW
        rgb = self.tex[self.lat_i, (self.lon_i + sh) % self.TW].astype(np.float32)
        rgb = rgb * self.shade + self.rim
        arr = np.zeros((D0, D0, 4), np.uint8)
        arr[self.mask, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        arr[..., 3] = self.alpha
        im = Image.fromarray(arr, 'RGBA')
        im.alpha_composite(self.decal)
        return im

    def draw(self, fr, x, y, R, phase, a=1.0, glow=1.0):
        if R < 4 or a <= 0.01:
            return
        s = 2 * R / self.D0
        atm = self.atmo.resize((max(2, int(self.atmo.width * s)), max(2, int(self.atmo.height * s))), Image.BILINEAR)
        C.put(fr, atm, x, y, min(1.0, a * glow))
        if glow > 1.0:
            C.put(fr, atm, x, y, min(1.0, a * (glow - 1.0)))
        sf = self.surface(phase)
        if abs(s - 1) > 0.004:
            sf = sf.resize((max(2, int(round(2 * R))), max(2, int(round(2 * R)))), Image.BILINEAR)
        C.put(fr, sf, x, y, a)


# ─────────────────────────────── ролик ───────────────────────────────
class Orbit(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 61, drop=17 * 60 / 61, line=None, intro=3,
                 team=6, near=2, hold=4, cta=2.5, seed=61, **kw):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.line = league, when, coef, line
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.raw = {'h': sh or {}, 'a': sa or {}}
        self.st = {'h': F.norm(sh), 'a': F.norm(sa)}
        b = self.b
        self.T3 = b(-near)                          # сближение
        self.T2 = b(-near - team)                   # гости
        self.T1 = b(-near - 2 * team)               # хозяева
        if self.T1 < 1.5:
            raise ValueError('мало времени до дропа: интро %.2f с' % self.T1)
        self.T5 = b(hold)                           # плашка Telegram
        self.dur = b(hold + cta)
        self.cover_t = min(self.T1 - 0.45, 2.4)
        self.PICK_R = ring_r(self.PR, 1262 - self.PY)       # орбита проходит через плашку кэфа
        self.FIN_R = ring_r(self.FR, 1085 - self.FY)        # орбита плашки Telegram
        self._prep()

    # ── заготовки ──
    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        self.neb = self._nebula(rnd)
        self.stars = [(rnd.uniform(0, W + 400), rnd.uniform(0, H + 400), rnd.uniform(0.25, 1.0), rnd.uniform(0, 6.28),
                       rnd.choice([0, 0, 0, 1, 2])) for _ in range(150)]
        self.flare = C.radial(46, 46, WHITE, 255, 2.2)
        self.flare_w = C.radial(70, 70, (255, 226, 190), 230, 1.8)
        self.sprite = {k: C.radial(d, d, c, 255, 1.6) for k, d, c in (('w', 34, (255, 240, 220)), ('v', 60, (200, 150, 255)),
                                                                        ('o', 60, (255, 170, 90)))}
        self.cross = self._cross(90)
        self.P = {'h': Planet(self.h, self.seed + 1), 'a': Planet(self.a, self.seed + 2)}
        self.tag = C.text(F.tag(self.league), 'unb', 34, MUTE, 700, track=0.12)
        self.handle = C.text(C.HANDLE, 'unb', 38, WHITE, 600)
        self.when_im = C.text(self.when, 'unb', 46, GOLD, 800, track=0.04, max_w=980)
        # интро
        self.i_name = {k: C.text(t.up, 'unb', 64, WHITE, 900, max_w=440) for k, t in (('h', self.h), ('a', self.a))}
        self.i_role = {'h': C.text('ХОЗЯЕВА', 'mont', 32, GOLD, 800, track=0.3),
                       'a': C.text('ГОСТИ', 'mont', 32, GOLD, 800, track=0.3)}
        self.odds = self._odds() if self.line else None
        self.odds_lab = C.text('ОСНОВНОЕ ВРЕМЯ', 'mont', 34, MUTE, 800, track=0.3)
        # команды
        self.S = {k: self._team(k) for k in ('h', 'a')}
        # прогноз
        fav = self.h if self.side == 'h' else self.a
        self.fav = fav
        self.fcol = fresh.bright(self.P[self.side].col, 0.3)
        self.p_lab = C.text('ПРОГНОЗ', 'mont', 40, GOLD, 900, track=0.45)
        nm = C.text(self.pick1, 'unb', 98, WHITE, 900, max_w=980)
        self.p_main = C.glow(nm, 16, 1.1, self.P[self.side].col)
        self.p_sub = C.text(self.pick2, 'mont', 46, WHITE, 800, track=0.12, max_w=960) if self.pick2 else None
        self.coef_pl = self._coef() if self.coef else None
        self.corona = self._corona(rnd)
        self.streak = self._streak()
        # финал
        self.f_all = C.text('ВСЕ ПРОГНОЗЫ', 'unb', 84, WHITE, 900, max_w=980)
        self.f_sub = C.text('КАЖДЫЙ ДЕНЬ · КХЛ И НХЛ', 'mont', 42, MUTE, 800, track=0.16, max_w=960)
        self.tg = C.tg_plate(960, 196, font='unb')
        # сетка для линзы
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.gx, self.gy = xx, yy
        # кольца героя — заранее (до fork, чтобы не считать в каждом процессе)
        for k in ('h', 'a'):
            for sl in self.S[k]['slots']:
                ring_layer(self.HX, self.HY, self.HR, sl['r'], 'front', a=120)
                ring_layer(self.HX, self.HY, self.HR, sl['r'], 'back', a=60)
            ring_layer(self.HX, self.HY, self.HR, self.SAT_R, 'front', col=(255, 200, 150), a=110, width=2)
            ring_layer(self.HX, self.HY, self.HR, self.SAT_R, 'back', col=(255, 200, 150), a=70, width=2)
        for part, a in (('front', 140), ('back', 70)):
            ring_layer(540, self.PY, self.PR, self.PICK_R, part, col=(255, 200, 150), a=a)
            ring_layer(540, self.FY, self.FR, self.FIN_R, part, col=(200, 180, 255), a=a)

    HX, HY, HR = 540, 668, 172          # планета-герой в сцене команды
    SAT_R = 1.95                        # орбита малых лун (по бокам планеты)
    PY, PR = 615, 212                   # планета прогноза
    FY, FR = 560, 160                   # планета в финале
    IY, IR = 650, 150                   # интро: центр по высоте и радиус планет
    NY, NR = 790, 175                   # сближение

    def _nebula(self, rnd):
        """Туманность (две палитры для «дыхания»): шум в 4 октавы, нити (ridged), тёплое солнце слева сверху."""
        w, h = W + 2 * M, H + 2 * M

        def noise(cells):
            acc = np.zeros((h, w), np.float32)
            for cell, amp in cells:
                g = rnd.normal(0, 1, (h // cell + 3, w // cell + 3)).astype(np.float32)
                im = Image.fromarray(g).resize(((w // cell + 3) * cell, (h // cell + 3) * cell), Image.BICUBIC)
                acc += np.asarray(im, np.float32)[:h, :w] * amp
            return (acc - acc.mean()) / (acc.std() + 1e-6)

        n1 = noise(((460, 1.0), (220, 0.55), (100, 0.3), (44, 0.14)))
        n2 = noise(((300, 1.0), (140, 0.5), (60, 0.25)))
        n3 = noise(((520, 1.0), (240, 0.4)))
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        band = np.exp(-(((xx - w * 0.5) * 0.55 + (yy - h * 0.48) * 0.84) / (h * 0.26)) ** 2)        # диагональный рукав
        dens = np.clip(n1 * 0.32 + 0.38, 0, 1) ** 1.7 * (0.35 + 0.75 * band)
        ridge = (1 - np.abs(np.tanh(n2 * 0.9))) ** 5 * (0.25 + 0.9 * band)
        sun = np.exp(-np.sqrt((xx + 120) ** 2 + (yy - 240) ** 2) / 620)
        low = np.exp(-np.sqrt((xx - w * 1.05) ** 2 + (yy - h * 0.95) ** 2) / 700)
        warm = np.clip(n3 * 0.5 + 0.5, 0, 1)
        out = []
        for mode in (0, 1):
            cv = np.array(VIOLET, np.float32) * (0.62 if mode == 0 else 0.42)
            cm = np.array(MAGENTA, np.float32) * (0.32 if mode == 0 else 0.5)
            co = np.array(ORANGE, np.float32) * (0.28 if mode == 0 else 0.45)
            rgb = np.array(SPACE, np.float32)[None, None] + np.zeros((h, w, 1), np.float32)
            rgb += dens[..., None] * (cv * (1 - warm[..., None] * 0.6) + cm * warm[..., None] * 0.9)
            rgb += ridge[..., None] * (cm * 0.75 + co * warm[..., None])
            rgb += (dens * ridge)[..., None] * co * 1.2
            rgb += sun[..., None] * np.array((255, 120, 60), np.float32) * (0.42 if mode == 0 else 0.55)
            rgb += low[..., None] * np.array((120, 40, 160), np.float32) * 0.45
            out.append(rgb)
        # дальние звёзды — впечатаны в туманность
        n = 2600
        sx, sy = rnd.integers(0, w, n), rnd.integers(0, h, n)
        br = rnd.uniform(40, 200, n) ** 1.0 * rnd.choice([0.4, 0.6, 1.0, 1.0], n)
        tintc = np.array([(255, 255, 255), (210, 200, 255), (255, 220, 190)], np.float32)[rnd.integers(0, 3, n)]
        star = np.zeros((h, w, 3), np.float32)
        star[sy, sx] = tintc * (br / 255)[:, None]
        big = rnd.random(n) < 0.12
        for ddx, ddy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            star[np.clip(sy[big] + ddy, 0, h - 1), np.clip(sx[big] + ddx, 0, w - 1)] += tintc[big] * (br[big] / 255 * 0.45)[:, None]
        res = []
        for rgb in out:
            rgb = rgb + star
            res.append(Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB'))
        return res

    def _cross(self, d):
        """Блик звезды — крест."""
        arr = np.zeros((d, d), np.float32)
        c = d / 2
        yy, xx = np.mgrid[0:d, 0:d].astype(np.float32)
        arr += np.exp(-np.abs(yy - c) / 1.2) * np.exp(-np.abs(xx - c) / (d * 0.22))
        arr += np.exp(-np.abs(xx - c) / 1.2) * np.exp(-np.abs(yy - c) / (d * 0.22))
        arr += np.exp(-((xx - c) ** 2 + (yy - c) ** 2) / 18)
        a = np.clip(arr * 255, 0, 255).astype(np.uint8)
        im = Image.new('RGBA', (d, d), (255, 244, 230, 255))
        im.putalpha(Image.fromarray(a))
        return im

    def _odds(self):
        w, h, gap = 960, 214, 26
        out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        bw = (w - 2 * gap) / 3
        for k, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), self.line)):
            bx = glass(bw, h, 44).copy()
            C.put(bx, C.text(lab, 'mont', 42, GOLD, 900, track=0.2), bw / 2, h * 0.28)
            C.put(bx, C.text(C.fmt_k(v), 'unb', 82, WHITE, 900, max_w=bw - 36), bw / 2, h * 0.64)
            C.put(out, bx, k * (bw + gap), 0, anchor='tl')
        return out

    def _game_plate(self, g, w=700, h=100):
        pl = glass(w, h, h / 2).copy()
        x0 = 66
        opp = C.text(g['opp'].upper(), 'unb', 40, WHITE, 800, max_w=390)
        C.put(pl, opp, x0, 38 - opp.height / 2, anchor='tl')
        sub = []
        if g.get('date'):
            sub.append(g['date'])
        if g.get('home') is not None:
            sub.append('ДОМА' if g['home'] else 'В ГОСТЯХ')
        if sub:
            st = C.text(' · '.join(sub), 'mont', 26, MUTE, 700, track=0.08)
            C.put(pl, st, x0, 74 - st.height / 2, anchor='tl')
        sc = C.text(g['score'], 'unb', 58, WHITE, 900)
        xr = w - 34
        if g['note']:
            nt = C.text(g['note'], 'unb', 28, GOLD, 800)
            C.put(pl, nt, xr - nt.width, h / 2 - nt.height / 2 + 2, anchor='tl')
            xr -= nt.width + 12
        C.put(pl, sc, xr - sc.width, h / 2 - sc.height / 2, anchor='tl')
        return pl

    def _stat_plate(self, s, w=880, h=136):
        cells = []
        if s['points'] is not None:
            cells.append(('%d' % s['points'], plural(s['points'], 'ОЧКО', 'ОЧКА', 'ОЧКОВ'), WHITE))
        if s['gp'] is not None:
            cells.append(('%d' % s['gp'], plural(s['gp'], 'ИГРА', 'ИГРЫ', 'ИГР'), WHITE))
        if s['place'] is not None:
            cells.append(('%d' % s['place'], (s['place_scope'] or 'МЕСТО').upper(), WHITE))
        if s['gd'] is not None:
            col = (130, 245, 170) if s['gd'] > 0 else (255, 140, 130) if s['gd'] < 0 else WHITE
            cells.append((F.gd_txt(s['gd']), 'ШАЙБЫ ±', col))
        if not cells:
            return None
        pl = glass(w, h, 40).copy()
        x0, x1 = 70, w - 22
        cw = (x1 - x0) / len(cells)
        d = ImageDraw.Draw(pl)
        for k, (v, lab, col) in enumerate(cells):
            cx = x0 + cw * (k + 0.5)
            C.put(pl, C.text(v, 'unb', 60, col, 900, max_w=cw - 20), cx, 56)
            C.put(pl, C.text(lab, 'mont', 25, GOLD, 800, track=0.06, max_w=cw - 32), cx, 106)
            if k:
                d.line((x0 + cw * k, 26, x0 + cw * k, h - 26), fill=(255, 255, 255, 46), width=2)
        return pl

    def _sat_plate(self, val, lab, w=262, h=124):
        pl = glass(w, h, 30).copy()
        C.put(pl, C.text(val, 'unb', 54, WHITE, 900, max_w=w - 30), w / 2, 48)
        C.put(pl, C.text(lab, 'mont', 24, GOLD, 800, track=0.08, max_w=w - 24), w / 2, 96)
        return pl

    def _sats(self, k):
        """Малые луны по бокам: серия; большинство (или дома/в гостях) — только если цифры есть."""
        raw = self.raw[k]
        out = []
        stk = str(raw.get('streak') or '').strip().upper()
        if stk:
            out.append((stk, 'СЕРИЯ'))
        pp = _num(raw.get('pp'))
        if pp is not None:
            out.append(('%d%%' % round(pp), 'БОЛЬШИНСТВО'))
        else:
            key, lab = ('home_rec', 'ДОМА') if (raw.get('home_today') if raw.get('home_today') is not None else k == 'h') \
                else ('road_rec', 'В ГОСТЯХ')
            if raw.get(key):
                out.append((str(raw[key]), lab))
        return out[:2]

    def _team(self, k):
        tm = self.h if k == 'h' else self.a
        s = self.st[k]
        name = C.text(tm.up, 'unb', 112, WHITE, 900, max_w=960)
        name = C.glow(name, 14, 0.9, self.P[k].col)
        role = C.text('ХОЗЯЕВА' if k == 'h' else 'ГОСТИ', 'mont', 34, GOLD, 800, track=0.4)
        slots = []
        ys = [930, 1043, 1156]
        for i, g in enumerate(s['games'][:3]):
            pl = self._game_plate(g)
            mcol = WIN if g['res'] == 'В' else LOSS if g['res'] == 'П' else (150, 150, 170)
            slots.append(dict(pl=pl, moon=moon(mcol, 92, g['res'] or '?'), y=ys[i]))
        sp = self._stat_plate(s)
        if sp is not None:
            slots.append(dict(pl=sp, moon=moon((236, 214, 170), 92), y=1298))
        R = self.HR
        for i, sl in enumerate(slots):
            pw = sl['pl'].width
            mx = W / 2 - pw / 2 + 10                    # луна — у левого края плашки
            sl['dx'] = mx - self.HX
            sl['r'] = solve_r(R, sl['dx'], sl['y'] - self.HY)
            sl['dir'] = 1 if i % 2 == 0 else -1
        sats = []
        for j, (val, lab) in enumerate(self._sats(k)):
            th = math.pi if j == 0 else 0.0
            sats.append(dict(pl=self._sat_plate(val, lab), moon=moon(ORANGE if j == 0 else VIOLET, 46), th=th))
        return dict(name=name, role=role, slots=slots, sats=sats)

    def _coef(self):
        kt = C.text('КЭФ ' + C.fmt_k(self.coef), 'unb', 84, (30, 10, 40), 900)
        w, h = kt.width + 150, 156
        pl = C.lgrad(w, h, (255, 214, 120), (246, 92, 170), 0)
        m = C.rrect(w, h, h / 2, WHITE)
        pl.putalpha(m.getchannel('A'))
        hl = C.rrect(w - 30, h * 0.42, h * 0.21, WHITE, 70)
        C.put(pl, hl, w / 2, h * 0.27)
        C.put(pl, kt, w / 2, h / 2 + 2)
        return pl

    def _corona(self, rnd):
        """Корона затмения: лучи разной длины + мягкое сияние (аддитивно)."""
        S = 1200
        R0 = self.PR
        yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
        dx, dy = xx - S / 2, yy - S / 2
        dist = np.sqrt(dx * dx + dy * dy)
        ang = np.arctan2(dy, dx)
        rays = np.zeros_like(dist)
        for _ in range(46):
            a0 = rnd.uniform(-math.pi, math.pi)
            wdt = rnd.uniform(0.01, 0.05)
            ln = rnd.uniform(0.25, 1.0)
            da = np.angle(np.exp(1j * (ang - a0)))
            rays += np.exp(-(da / wdt) ** 2) * ln
        out = np.clip(dist - R0, 0, None)
        prof = np.exp(-out / (R0 * 0.18)) * 1.1
        ray = np.clip(rays, 0, 1.4) * np.exp(-out / (R0 * 0.75))
        val = np.clip(prof + ray * 0.9, 0, 2)
        val[dist < R0 - 3] = 0
        warm = np.clip(out / (R0 * 0.9), 0, 1)[..., None]
        c1 = np.array((255, 250, 235), np.float32)
        c2 = np.array(MAGENTA, np.float32) * 0.6 + np.array(ORANGE, np.float32) * 0.4
        rgb = c1 * (1 - warm) + c2 * warm
        a = np.clip(val * 200, 0, 255)
        return Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), 'RGBA')

    def _streak(self):
        """Анаморфный блик — горизонтальная полоса света."""
        w, h = 1400, 70
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        v = np.exp(-((yy - h / 2) / 7) ** 2) * np.exp(-np.abs(xx - w / 2) / (w * 0.2))
        im = Image.new('RGBA', (w, h), (255, 230, 220, 255))
        im.putalpha(Image.fromarray(np.clip(v * 255, 0, 255).astype(np.uint8)))
        return im

    # ── время ──
    def beat_pulse(self, t, k=7.0):
        """1 на каждой доле трека (отсчёт от дропа), затем затухание."""
        x = (t - self.drop) / self.u
        return math.exp(-(x - math.floor(x)) * k)

    def pan(self, t):
        """Сдвиг камеры (для параллакса): интро 0 → хозяева −1 → гости +1 → сближение 0."""
        u = self.u
        p = 0.0
        p += -1.0 * C.in_out(C.seg(t, self.T1, self.T1 + 0.7 * u))
        p += 2.0 * C.in_out(C.seg(t, self.T2, self.T2 + 0.7 * u))
        p += -1.0 * C.in_out(C.seg(t, self.T3, self.T3 + 1.2 * u))
        return p

    # ── фон ──
    def background(self, t, lens=None):
        u, D = self.u, self.drop
        p = self.pan(t)
        kb = 0.5 + 0.5 * math.sin(2 * math.pi * t / (8 * u) - 1.2)
        if t >= D:
            kb = max(kb, 0.85 - 0.5 * C.seg(t, D, D + 2 * u))
        ox = M + p * 60 - 2.0 * t
        oy = M - 3.2 * t + 40 * math.sin(t * 0.13)
        ox, oy = int(C.clamp(ox, 0, 2 * M)), int(C.clamp(oy, 0, 2 * M))
        box = (ox, oy, ox + W, oy + H)
        a, b = self.neb[0].crop(box), self.neb[1].crop(box)
        fr = Image.blend(a, b, kb)
        d = ImageDraw.Draw(fr, 'RGBA')
        bp = self.beat_pulse(t, 5)
        lay = []
        for x0, y0, al, ph, kind in self.stars:
            par = 0.6 + 0.9 * al
            x = (x0 - p * 150 * par - t * 7 * par) % (W + 400) - 200
            y = (y0 - t * 12 * par) % (H + 400) - 200
            tw = 0.55 + 0.45 * math.sin(t * 2.3 + ph)
            v = int(255 * al * tw * (0.8 + 0.2 * bp))
            if kind == 0:
                r = 1.0 + 1.6 * al
                d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 246, 236, v))
            else:
                lay.append((x, y, al * tw * (0.75 + 0.35 * bp), kind))
        fr = fr.convert('RGBA')
        for x, y, k, kind in lay:
            im = self.cross if kind == 1 else self.flare_w
            C.put(fr, im, x, y, min(1.0, k))
        if lens is not None:
            fr = self.warp(fr, *lens)
        return fr

    def warp(self, fr, cx, cy, te):
        """Гравитационная линза вокруг (cx, cy) с радиусом Эйнштейна te."""
        if te < 2:
            return fr
        arr = np.asarray(fr)
        dx, dy = self.gx - cx, self.gy - cy
        k = 1.0 - (te * te) / (dx * dx + dy * dy + 400.0)
        sx = np.clip(cx + dx * k, 0, W - 1).astype(np.int32)
        sy = np.clip(cy + dy * k, 0, H - 1).astype(np.int32)
        return Image.fromarray(arr[sy, sx], 'RGBA')

    # ── состояния планет ──
    def planets(self, t):
        """→ список (ключ, x, y, R) в порядке отрисовки (дальняя — первой)."""
        u, D = self.u, self.drop
        T1, T2, T3 = self.T1, self.T2, self.T3
        bob = lambda ph: 8 * math.sin(t * 1.1 + ph)
        intro = {'h': (290, self.IY + bob(0), self.IR), 'a': (790, self.IY + bob(2), self.IR)}
        hero = (self.HX, self.HY + 4 * math.sin(t * 0.9), self.HR)
        offL, offR = (-330, 560, 120), (W + 330, 560, 120)

        def lerp3(p, q, k):
            return tuple(C.lerp(a, b, k) for a, b in zip(p, q))
        out = []
        if t < T1:
            return [('h',) + intro['h'], ('a',) + intro['a']]
        if t < T2:
            k = C.in_out(C.seg(t, T1, T1 + 0.75 * u))
            if k < 1:
                out.append(('a',) + lerp3(intro['a'], offR, k))
            out.append(('h',) + lerp3(intro['h'], hero, k))
            return out
        if t < T3:
            k1 = C.in_out(C.seg(t, T2, T2 + 0.6 * u))
            k2 = C.in_out(C.seg(t, T2 + 0.1 * u, T2 + 0.85 * u))
            if k1 < 1:
                out.append(('h',) + lerp3(hero, offL, k1))
            out.append(('a',) + lerp3(offR, hero, k2))
            return out
        fav, oth = self.side, ('a' if self.side == 'h' else 'h')
        if t < D:
            # 1) расстановка по сторонам, 2) сближение — к дропу планета прогноза впереди закрывает вторую
            k1 = C.in_out(C.seg(t, T3, T3 + 0.7 * u))
            k2 = C.in_cubic(C.seg(t, T3 + 0.55 * u, D - 0.04))
            side_f = (W / 2 - 250, self.NY, 158)
            side_o = (W / 2 + 250, self.NY, 158)
            start = {'h': offL, 'a': hero}
            pf = lerp3(start[fav], side_f, k1)
            po = lerp3(start[oth], side_o, k1)
            pf = lerp3(pf, (W / 2, self.NY, self.NR + 30), k2)
            po = lerp3(po, (W / 2 + 6, self.NY - 4, 128), k2)
            return [(oth,) + po, (fav,) + pf]
        if t < self.T5:
            k = C.out_expo(C.seg(t, D + 0.05, D + 0.65 * u))
            return [(fav,) + lerp3((W / 2, self.NY, self.NR + 30), (W / 2, self.PY, self.PR), k)]
        k = C.in_out(C.seg(t, self.T5, self.T5 + 0.6 * u))
        return [(fav,) + lerp3((W / 2, self.PY, self.PR), (W / 2, self.FY, self.FR), k)]

    def phase(self, key, t):
        return (t / 40.0 + (0.37 if key == 'a' else 0.0)) % 1.0

    # ── сцены ──
    def intro_layer(self, fr, t, pl):
        """Интро: кольца с лунами вокруг обеих планет, названия, время, линия П1 · Х · П2."""
        u = self.u
        fo = 1 - C.seg(t, self.T1 - 0.12, self.T1 + 0.18)
        if fo <= 0:
            return
        q = C.out_expo(C.seg(t, 0.05, 0.6))
        C.put(fr, self.when_im, W / 2, 345 + 20 * (1 - q), q * fo)
        for k, x, y, R in pl:
            if k not in self.i_name:
                continue
            qn = C.out_expo(C.seg(t, 0.25 + (0.1 if k == 'a' else 0), 0.75))
            cx = 290 if k == 'h' else 790
            C.put(fr, self.i_name[k], cx, 888 + 30 * (1 - qn), qn * fo)
            C.put(fr, self.i_role[k], cx, 952 + 30 * (1 - qn), qn * fo)
        if self.odds is not None:
            q3 = C.out_expo(C.seg(t, 0.45, 0.95))
            C.put(fr, self.odds_lab, W / 2, 1066, q3 * fo)
            C.put(fr, self.odds, W / 2, 1236 + 50 * (1 - q3), q3 * fo)

    def small_rings(self, fr, t, pl, part):
        """Кольцо и луна-спутник вокруг каждой планеты (интро)."""
        if t >= self.T1 + 0.4 * self.u:
            return
        a = C.seg(t, 0.1, 0.7) * (1 - C.seg(t, self.T1 - 0.1, self.T1 + 0.3))
        if a <= 0:
            return
        lay = Image.new('RGBA', fr.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for k, x, y, R in pl:
            col = (255, 200, 150) if k == 'h' else (200, 180, 255)
            rr = 1.72 * C.out_expo(C.seg(t, 0.1, 0.8)) + 0.01
            draw_ring(d, x, y, R, rr, part, col, 60 * a, 9)
            draw_ring(d, x, y, R, rr, part, col, 170 * a, 3)
        fr.alpha_composite(lay)
        for k, x, y, R in pl:
            th = 2 * math.pi * (t / (4 * self.u)) + (0 if k == 'h' else math.pi)
            mx, my, kk = proj(x, y, R, 1.72, th)
            front = math.sin(th) >= 0
            if front != (part == 'front'):
                continue
            col = ORANGE if k == 'h' else VIOLET
            m = moon(col, 30)
            C.put(fr, self.sprite['o' if k == 'h' else 'v'], mx, my, 0.6 * a)
            C.put(fr, C.scale(m, 0.8 + 0.25 * kk), mx, my, a)

    def slot_pos(self, sl, t, t0, i):
        """Положение луны слота: спираль с планеты → своя точка орбиты, затем медленный дрейф."""
        u = self.u
        R, cx, cy = self.HR, self.HX, self.HY
        tl = t0 + self.launch[i] * u
        q = C.out_cubic(C.seg(t, tl, tl + 0.62 * u))
        drift = 16 * (t - tl) * (1.0 + 0.25 * (i % 2)) / 6.0
        th_end = theta_at_x(R, sl['r'], sl['dx'] + drift)
        if q >= 1:
            x, y, kk = proj(cx, cy, R, sl['r'], th_end)
            return x, y, 1.0, True, q, tl
        r = C.lerp(0.9, sl['r'], q)
        th = th_end - sl['dir'] * (1 - q) * 1.65 * math.pi
        x, y, kk = proj(cx, cy, R, r, th)
        front = math.sin(th) >= 0 or math.hypot(x - cx, y - cy) > R
        return x, y, 0.55 + 0.45 * q, front, q, tl

    launch = (1.0, 1.5, 2.0, 2.5)          # доли от начала сцены команды: старт лун (игры ×3, сезон)
    sat_launch = (3.0, 3.5)

    def team_layer(self, fr, t, key, t0, part, P):
        """Сцена команды: part='back' — дальние дуги и луны за планетой, 'front' — всё остальное."""
        u = self.u
        S = self.S[key]
        t1 = t0 + 6 * u if key == 'h' else self.T3
        fo = 1 - C.seg(t, t1 - 0.32 * u, t1 - 0.02)
        if fo <= 0:
            return
        R, cx, cy = self.HR, self.HX, self.HY
        if P is None:
            return
        px, py, pR = P
        ready = abs(px - cx) < 2 and abs(pR - R) < 1
        for i, sl in enumerate(S['slots']):
            tl = t0 + self.launch[i] * u
            ra = C.seg(t, tl, tl + 0.5 * u) * fo
            if ra > 0 and ready:
                rl = ring_layer(cx, cy, R, sl['r'], part, a=120 if part == 'front' else 60)
                if rl:
                    C.put(fr, rl[0], rl[1], rl[2] + (py - cy), ra, anchor='tl')
        for j, sa in enumerate(S['sats']):
            tl = t0 + self.sat_launch[j] * u
            ra = C.seg(t, tl, tl + 0.5 * u) * fo
            if ra > 0 and ready:
                rl = ring_layer(cx, cy, R, self.SAT_R, part, col=(255, 200, 150), a=110 if part == 'front' else 70, width=2)
                if rl:
                    C.put(fr, rl[0], rl[1], rl[2] + (py - cy), ra, anchor='tl')
                break
        if not ready:
            return
        dy = py - cy
        # луны со спиралью
        for i, sl in enumerate(S['slots']):
            x, y, sc, front, q, tl = self.slot_pos(sl, t, t0, i)
            if t < tl:
                continue
            y += dy
            if (part == 'front') != front:
                continue
            if q < 1:                                     # хвост кометы
                for n in range(1, 9):
                    qq = q - n * 0.035
                    if qq <= 0:
                        break
                    r_ = C.lerp(0.9, sl['r'], qq)
                    th_end = theta_at_x(R, sl['r'], sl['dx'])
                    th_ = th_end - sl['dir'] * (1 - qq) * 1.65 * math.pi
                    xx, yy, _ = proj(cx, cy, R, r_, th_)
                    if math.sin(th_) < 0 and math.hypot(xx - cx, yy - cy) < R:
                        continue
                    C.put(fr, self.sprite['w'], xx, yy + dy, 0.55 * (1 - n / 9) * fo)
            if part == 'front':
                pq = C.out_expo(C.seg(t, tl + 0.42 * u, tl + 0.78 * u))
                if pq > 0:
                    pl = sl['pl']
                    ww = max(2, int(pl.width * pq))
                    C.put(fr, pl.crop((0, 0, ww, pl.height)), x - 10, y - pl.height / 2, fo * min(1, pq * 1.6), anchor='tl')
            m = C.scale(sl['moon'], sc)
            C.put(fr, self.sprite['w'], x, y, 0.35 * fo)
            C.put(fr, m, x, y, fo)
        # малые луны по бокам
        for j, sa in enumerate(S['sats']):
            tl = t0 + self.sat_launch[j] * u
            if t < tl:
                continue
            q = C.out_cubic(C.seg(t, tl, tl + 0.55 * u))
            th_end = sa['th'] + (0.06 * math.sin((t - tl) * 0.7) if q >= 1 else 0)
            r = C.lerp(0.9, self.SAT_R, q)
            th = th_end + (1 if j == 0 else -1) * (1 - q) * 1.3 * math.pi
            x, y, kk = proj(cx, cy, R, r, th)
            y += dy
            front = math.sin(th) >= 0 or math.hypot(x - cx, y - py) > R
            if (part == 'front') != front:
                continue
            if part == 'front':
                pq = C.out_expo(C.seg(t, tl + 0.35 * u, tl + 0.7 * u))
                if pq > 0:
                    pl = sa['pl']
                    C.put(fr, C.scale(pl, 0.7 + 0.3 * pq), x, y - 112 + 20 * (1 - pq), fo * pq)
            C.put(fr, self.sprite['o' if j == 0 else 'v'], x, y, 0.5 * fo)
            C.put(fr, sa['moon'], x, y, fo)

    def team_text(self, fr, t, key, t0):
        u = self.u
        S = self.S[key]
        t1 = t0 + 6 * u if key == 'h' else self.T3
        fo = 1 - C.seg(t, t1 - 0.32 * u, t1 - 0.02)
        q = C.out_expo(C.seg(t, t0 + 0.2 * u, t0 + 0.65 * u))
        if q <= 0 or fo <= 0:
            return
        sg = 1 if key == 'h' else -1
        C.put(fr, S['name'], W / 2 + sg * 80 * (1 - q), 352, q * fo)
        C.put(fr, S['role'], W / 2, 440, C.seg(t, t0 + 0.35 * u, t0 + 0.7 * u) * fo)

    def near_layer(self, fr, t, pl):
        """Сближение: подписи под планетами, кольцо Эйнштейна."""
        u, D = self.u, self.drop
        q = C.seg(t, self.T3 + 0.3 * u, self.T3 + 0.8 * u) * (1 - C.seg(t, D - 0.35 * u, D - 0.05))
        C.put(fr, self.when_im, W / 2, 345, C.seg(t, self.T3 + 0.05 * u, self.T3 + 0.4 * u) * (1 - C.seg(t, D - 0.2, D)))
        # подписи стоят на местах планет «по сторонам» и гаснут до того, как планеты сойдутся (без наложений)
        qn = q * (1 - C.seg(t, D - 1.0 * u, D - 0.6 * u))
        for k, x, y, R in pl:
            if qn > 0:
                sx = W / 2 + (-250 if k == self.side else 250)
                C.put(fr, self.i_name[k], sx, self.NY + 158 + 72 + 16 * (1 - q), qn)
        # линия основного времени ещё раз — под сходящимися планетами (кадр заполнен до низа)
        if self.odds is not None:
            qo = C.out_expo(C.seg(t, self.T3 + 0.1 * u, self.T3 + 0.6 * u)) * (1 - C.seg(t, D - 0.3 * u, D - 0.03))
            C.put(fr, self.odds, W / 2, 1250 + 40 * (1 - qo), qo)

    def einstein(self, fr, t, pl):
        u, D = self.u, self.drop
        if not (self.T3 <= t < D) or len(pl) < 2:
            return None
        k, x, y, R = pl[0]
        q = C.seg(t, self.T3 + 0.3 * u, D)
        kick = math.exp(-max(0.0, t - (D - 0.75 * u)) * 9) if t >= D - 0.75 * u else 0.0
        te = R * (0.4 + 1.25 * C.in_cubic(q)) + 60 * kick
        return (x, y, te, q, kick)

    def pick_layer(self, fr, t):
        u, D = self.u, self.drop
        fo = 1 - C.seg(t, self.T5 - 0.1, self.T5 + 0.25 * u)
        if fo <= 0:
            return
        q = C.out_expo(C.seg(t, D, D + 0.4 * u))
        C.put(fr, C.scale(self.p_lab, 1.25 - 0.25 * q), W / 2, 912, q * fo)
        q2 = C.out_expo(C.seg(t, D, D + 0.45 * u))
        pul = 1 + 0.025 * self.beat_pulse(t, 8) * C.seg(t, D + u, D + 1.2 * u)
        C.put(fr, C.scale(self.p_main, (1.5 - 0.5 * q2) * pul), W / 2, 1003, min(1, q2 * 1.4) * fo)
        if self.p_sub is not None:
            q3 = C.out_expo(C.seg(t, D + 0.4 * u, D + 0.8 * u))
            C.put(fr, self.p_sub, W / 2, 1100 + 26 * (1 - q3), q3 * fo)
        if self.coef_pl is not None:
            q4 = C.out_back(C.seg(t, D + 0.75 * u, D + 1.15 * u), 1.6)
            if q4 > 0.01:
                C.put(fr, self.sprite['o'].resize((700, 260)), W / 2, 1262, 0.35 * min(1, q4) * fo)
                C.put(fr, C.scale(self.coef_pl, (0.5 + 0.5 * q4) * pul), W / 2, 1262, min(1.0, q4 * 1.5) * fo)

    def final_layer(self, fr, t):
        u, t0 = self.u, self.T5
        q = C.out_expo(C.seg(t, t0 + 0.15 * u, t0 + 0.55 * u))
        C.put(fr, self.f_all, W / 2, 878 + 40 * (1 - q), q)
        # плашка Telegram прилетает по ближней дуге орбиты справа
        qp = C.out_cubic(C.seg(t, t0 + 0.2 * u, t0 + 0.85 * u))
        if qp > 0:
            r = self.FIN_R
            th_end = math.pi / 2
            th = th_end - (1 - qp) * 0.9
            x, y, kk = proj(W / 2, self.FY, self.FR, r, th)
            x0, y0, _ = proj(W / 2, self.FY, self.FR, r, th_end)
            C.put(fr, C.scale(self.tg, 0.75 + 0.25 * qp), x, y - y0 + 1085, min(1.0, qp * 1.5))
        q = C.seg(t, t0 + 0.7 * u, t0 + 1.1 * u)
        C.put(fr, self.f_sub, W / 2, 1268, q)

    # ── кадр ──
    def frame(self, t):
        u, D = self.u, self.drop
        pl = self.planets(t)
        ein = self.einstein(fr=None, t=t, pl=pl)
        lens = (ein[0], ein[1], ein[2]) if ein else None
        fr = self.background(t, lens)
        bp = self.beat_pulse(t, 6)
        intro = t < self.T1 + 0.4 * u
        # дальние дуги, луны за планетой
        if intro:
            self.small_rings(fr, t, pl, 'back')
        hero = None
        team_key, t0 = (None, None)
        if self.T1 <= t < self.T2:
            team_key, t0 = 'h', self.T1
        elif self.T2 <= t < self.T3:
            team_key, t0 = 'a', self.T2
        if team_key:
            for k, x, y, R in pl:
                if k == team_key:
                    hero = (x, y, R)
            self.team_layer(fr, t, team_key, t0, 'back', hero)
        if D <= t:
            self.pick_rings(fr, t, 'back')
        # корона за планетой прогноза
        if t >= D - 0.03:
            self.corona_layer(fr, t, pl)
        if ein:
            self.einstein_ring(fr, ein)
        for k, x, y, R in pl:
            glow = 1.0 + 0.55 * bp
            if t >= D and t < self.T5:
                glow += 0.6 * (1 - C.seg(t, D, D + 0.6))
            self.P[k].draw(fr, x, y, R, self.phase(k, t), 1.0, glow)
        if intro:
            self.small_rings(fr, t, pl, 'front')
            self.intro_layer(fr, t, pl)
        if team_key:
            self.team_layer(fr, t, team_key, t0, 'front', hero)
            self.team_text(fr, t, team_key, t0)
        if self.T3 <= t < D:
            self.near_layer(fr, t, pl)
        if t >= D:
            self.pick_rings(fr, t, 'front')
            self.shock(fr, t)
            if t < self.T5 + 0.3 * u:
                self.pick_layer(fr, t)
            if t >= self.T5:
                self.final_layer(fr, t)
        # постоянные: тег лиги сверху, @jarvibet у низа безопасной зоны
        C.put(fr, self.tag, W / 2, TAG_Y, 0.95)
        C.put(fr, self.handle, W / 2, HANDLE_Y, 0.92)
        fr = fr.convert('RGB')
        if D <= t < D + 0.6:
            fr = C.add_light(fr, self.streak, W / 2, self.NY + (self.PY - self.NY) * C.out_expo(C.seg(t, D + 0.05, D + 0.65 * u)),
                             1.6 * (1 - C.seg(t, D, D + 0.6)))
        # камера: толчки на сменах сцен, удар на дропе
        z, dx, dy, rot = 1.0, 0.0, 0.0, 0.0
        for tb, amp in ((self.T1, 6), (self.T2, 6), (self.T3, 5)):
            if t >= tb:
                z += 0.025 * (1 - C.seg(t, tb, tb + 0.4)) ** 2
            sx, sy = C.shake(t, tb, amp, 0.3)
            dx, dy = dx + sx, dy + sy
        if self.T3 <= t < D:
            q = C.seg(t, self.T3, D)
            z += 0.05 * C.in_cubic(q)
            dx += 5 * q * q * math.sin(t * 67)
            dy += 5 * q * q * math.cos(t * 51)
        if t >= D:
            k = 1 - C.seg(t, D, D + 0.55)
            z += 0.12 * k ** 2
            sx, sy = C.shake(t, D, 30, 0.55)
            dx, dy = dx + sx, dy + sy
            rot = 1.6 * k ** 2 * math.sin((t - D) * 38)
            if t < self.T5:
                z += 0.008 * self.beat_pulse(t, 8)
        fr = C.zoom(fr, z, dx=dx, dy=dy, rot=rot)
        if D <= t < D + 0.2:
            fr = C.rgb_split(fr, 16 * (1 - C.seg(t, D, D + 0.2)))
        if D - 0.02 <= t < D + 0.34:
            a = 1.0 if t < D + 1 / 30 else 0.85 * (1 - C.seg(t, D + 1 / 30, D + 0.3)) ** 1.8
            fr = Image.blend(fr, Image.new('RGB', fr.size, (255, 244, 236)), 0.7 * a)
        fr = C.vignette(fr, 0.42)
        return C.grain(fr, t, 4)

    def corona_layer(self, fr, t, pl):
        u, D = self.u, self.drop
        if not pl:
            return
        k, x, y, R = pl[-1]
        dt = t - D
        burst = math.exp(-max(0.0, dt) * 3.2)
        s = (R / self.PR) * (1.0 + 0.35 * burst + 0.03 * self.beat_pulse(t, 7))
        a = 0.55 + 0.45 * burst + 0.15 * self.beat_pulse(t, 6)
        if t >= self.T5:
            a *= 1 - 0.6 * C.seg(t, self.T5, self.T5 + 0.6 * u)
        im = self.corona if abs(s - 1) < 0.01 else self.corona.resize((int(self.corona.width * s), int(self.corona.height * s)),
                                                                      Image.BILINEAR)
        rgb = C.add_light(fr, im, x, y, min(2.0, a * 1.2))
        fr.paste(rgb.convert('RGBA'))

    def einstein_ring(self, fr, ein):
        x, y, te, q, kick = ein
        a = C.clamp(q * 1.2) * 0.9 + 0.3 * kick
        if a <= 0.02:
            return
        lay = Image.new('RGBA', (int(te * 2 + 80), int(te * 2 + 80)), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        c = lay.width / 2
        d.ellipse((c - te, c - te, c + te, c + te), outline=(255, 210, 170, int(90 * a)), width=14)
        d.ellipse((c - te, c - te, c + te, c + te), outline=(255, 244, 230, int(220 * a)), width=3)
        lay = lay.filter(ImageFilter.GaussianBlur(2))
        C.put(fr, lay, x, y)

    def pick_rings(self, fr, t, part):
        """Орбита плашки кэфа вокруг планеты прогноза (после дропа) и орбита финала."""
        u, D = self.u, self.drop
        if t < self.T5 + 0.3 * u:
            a = C.seg(t, D + 0.6 * u, D + 1.1 * u) * (1 - C.seg(t, self.T5 - 0.1, self.T5 + 0.2 * u))
            if a > 0:
                rl = ring_layer(540, self.PY, self.PR, self.PICK_R, part, col=(255, 200, 150), a=140 if part == 'front' else 70)
                if rl:
                    C.put(fr, rl[0], rl[1], rl[2], a, anchor='tl')
        if t >= self.T5:
            a = C.seg(t, self.T5 + 0.3 * u, self.T5 + 0.7 * u)
            if a > 0:
                rl = ring_layer(540, self.FY, self.FR, self.FIN_R, part, col=(200, 180, 255), a=140 if part == 'front' else 70)
                if rl:
                    C.put(fr, rl[0], rl[1], rl[2], a, anchor='tl')

    def shock(self, fr, t):
        """Ударная волна по плоскости орбит после дропа."""
        dt = t - self.drop
        if dt < 0 or dt > 1.2:
            return
        lay = Image.new('RGBA', fr.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for k0, col in ((0.0, (255, 236, 220)), (0.12, (255, 150, 200))):
            e = dt - k0
            if e <= 0:
                continue
            r = 1.05 + 9.0 * (1 - math.exp(-2.6 * e))
            a = 220 * max(0.0, 1 - e / 1.0) ** 1.4
            y = self.NY + (self.PY - self.NY) * C.out_expo(C.seg(t, self.drop + 0.05, self.drop + 0.65 * self.u))
            draw_ring(d, W / 2, y, self.NR + 30, r, 'all', col, a * 0.35, 18, 240)
            draw_ring(d, W / 2, y, self.NR + 30, r, 'all', col, a, 4, 240)
        fr.alpha_composite(lay)
