# -*- coding: utf-8 -*-
"""«Голограмма» — голографический стол в тёмной комнате (трек «Gem», поздний участок): внизу кадра — диск-проектор,
из него вверх бьёт конус света (голубой, с уклоном в цвет клуба); над диском вращается объёмная голограмма эмблемы
(строки развёртки, мерцание, лёгкое расслоение цвета, свечение), выше в луче раскрываются на долях трека
голографические панели с фактами — повёрнуты в псевдо-3D, как вогнутый экран вокруг зрителя, текст чёткий.
Не терминал (jarvis.py) и не точечные эмблемы (particles.py).

Сцены (u — доля трека, D — дроп; доли считаются от дропа, team / pre / hold / cta — параметры):
  интро (до D − (2·team + pre) долей) — проектор включается, обе эмблемы собираются из вокселей, сверху лига
                 и время МСК, под названиями клубов — линия основного времени П1 · Х · П2 крупными панелями
                 (раскрываются с первой доли по четвертям);
  команда (team долей) ×2 — конус и панели в цвете клуба, название клуба сверху, «ХОЗЯЕВА» / «ГОСТИ»;
                 голограмма эмблемы над диском собирается из вокселей, поднятых с диска; с полудоли по четвертям
                 раскрываются панели последних 3 игр (соперник, дата, дома/в гостях, счёт, ОТ/Б, В/П), со второй
                 полудоли — очки за N матчей, место, разница шайб; затем большинство / меньшинство (и серия от 2 игр),
                 если такие цифры есть. Ровно на долю склейки голограмма рассыпается вокселями, панели гаснут;
  помехи (pre долей) — обе голограммы рядом, мерцают попеременно на четвертях доли (в конце — на восьмых),
                 интерференция: сдвиги строк, расслоение, кольца от диска, камера наезжает;
  ДРОП (hold долей) — ровно на дропе проекция стабилизируется: только команда прогноза (одна эмблема, без «VS»)
                 в полном цвете, вспышка и ударные кольца от диска; большая панель «ПОБЕДА / КЛУБ / В ОСНОВНОЕ ВРЕМЯ»
                 и панель кэфа; на каждую долю — импульс проектора;
  финал (cta долей) — всё поднимается и уменьшается, снизу плашка Telegram (C.tg_plate, текст по центру плашки).
@jarvibet — у низа безопасной зоны (y 1450), одинаково во всех сценах до плашки Telegram.
Кадр зависит только от t; фон, конусы, диски, панели и голограммы кешируются (до fork — общие для процессов).
"""
import colorsys
import math
import re

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels.core import W, H

CYAN = (64, 226, 255)
WHITE = (255, 255, 255)
TXT = (236, 250, 255)
DIM = (150, 196, 214)
INK = (4, 12, 22)
TAG_Y, HY = 262, 1450
DX, DY, DRX, DRY = 540, 1322, 262, 46            # диск-проектор: центр верхней грани и полуоси
APEX_Y = 1300                                    # откуда идёт конус
TOP_Y = 236                                      # докуда доходит конус
_CACHE = {}


# ─────────────────────────────── цвет ───────────────────────────────
def neon(c, v_min=0.95, s_min=0.62):
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    s = min(0.9, max(s, s_min)) if s > 0.12 else s
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, s, max(v, v_min)))


def club(t):
    cand = [c for c in (t.c0, t.c1, t.c2) if (max(c) - min(c)) / 255 > 0.2 and 40 < 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] < 235]
    return neon(cand[0] if cand else t.c1)


def holo(c, k=0.8):
    """Голографический цвет: тон голубого света, сдвинутый к тону клуба на долю k."""
    h1, s1, _ = colorsys.rgb_to_hsv(*(x / 255 for x in CYAN))
    h2, s2, _ = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    dh = ((h2 - h1 + 0.5) % 1.0) - 0.5
    h = (h1 + dh * k) % 1.0
    s = C.lerp(s1, s2, k) * 0.92
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, min(0.85, s), 1.0))


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


def noise(i, salt=0):
    """Детерминированный шум 0..1 по номеру кадра."""
    x = (int(i) * 2654435761 + salt * 40503 + 12345) & 0xFFFFFFFF
    x ^= x >> 13
    x = (x * 1274126177) & 0xFFFFFFFF
    return (x & 0xFFFF) / 65535.0


# ─────────────────────────────── свет (сложение) ───────────────────────────────
_LUT = {}


def kscale(im, k):
    k = round(max(0.0, k), 2)
    if k == 1.0:
        return im
    if k not in _LUT:
        _LUT[k] = [min(255, int(v * k)) for v in range(256)] * 3
    return im.point(_LUT[k])


def add(fr, light, x, y, k=1.0):
    """Сложить свет (RGB, премультиплицированный) в кадр, левый верхний угол (x, y)."""
    if light is None or k <= 0.01:
        return
    x, y = int(round(x)), int(round(y))
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(fr.width, x + light.width), min(fr.height, y + light.height)
    if x1 <= x0 or y1 <= y0:
        return
    lt = light.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    lt = kscale(lt, k)
    reg = fr.crop((x0, y0, x1, y1)).convert('RGB')
    fr.paste(ImageChops.add(reg, lt), (x0, y0))


def light_of(im, col=None, blur=0, k=1.0):
    """RGBA → свет RGB (цвет × альфа)."""
    a = np.asarray(im, np.float32)
    al = a[..., 3:4] / 255.0 * k
    rgb = (np.array(col, np.float32)[None, None, :] if col is not None else a[..., :3]) * al
    out = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB')
    if blur:
        out = out.filter(ImageFilter.GaussianBlur(blur))
    return out


def radial_light(d, col, k=1.0, power=2.0):
    key = ('rl', d, col, k, power)
    if key not in _CACHE:
        y, x = np.mgrid[0:d, 0:d].astype(np.float32)
        r = np.hypot(x - d / 2 + 0.5, y - d / 2 + 0.5) / (d / 2)
        v = np.clip(1 - r, 0, 1) ** power * k
        _CACHE[key] = Image.fromarray(np.clip(v[..., None] * np.array(col, np.float32), 0, 255).astype(np.uint8), 'RGB')
    return _CACHE[key]


# ─────────────────────────────── перспектива ───────────────────────────────
def _coeffs(dst, src):
    A, B = [], []
    for (x, y), (X, Y) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -X * x, -X * y])
        B.append(X)
        A.append([0, 0, 0, x, y, 1, -Y * x, -Y * y])
        B.append(Y)
    return tuple(np.linalg.solve(np.array(A, float), np.array(B, float)))


def warp(im, kl, kr, sq=1.0):
    """Поворот карточки вокруг вертикали: высота левого края × kl, правого × kr, ширина × sq."""
    w, h = im.size
    w2 = max(2, int(round(w * sq)))
    h2 = int(math.ceil(h * max(kl, kr))) + 2
    cy = h2 / 2
    dst = [(0, cy - h * kl / 2), (w2, cy - h * kr / 2), (w2, cy + h * kr / 2), (0, cy + h * kl / 2)]
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    return im.transform((w2, h2), Image.PERSPECTIVE, _coeffs(dst, src), Image.BICUBIC)


def glitch(im, g, seed):
    """Помехи голограммы: горизонтальные сдвиги полос строк и расслоение каналов (g 0..1)."""
    if g < 0.03:
        return im
    a = np.array(im)
    h = a.shape[0]
    rnd = np.random.default_rng(seed)
    for _ in range(4):
        y0 = int(rnd.uniform(0, h - 6))
        hh = int(rnd.uniform(4, max(6, h * 0.14)))
        a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], int(rnd.uniform(-1, 1) * 46 * g), axis=1)
    d = int(round(7 * g))
    if d:
        a[..., 0] = np.roll(a[..., 0], d, axis=1)
        a[..., 2] = np.roll(a[..., 2], -d, axis=1)
    return Image.fromarray(a, 'RGBA')


def rgb_off(im, d):
    if d < 1:
        return im
    a = np.array(im)
    al = a[..., 3].copy()
    r = np.roll(a[..., 0], d, axis=1)
    ra = np.roll(al, d, axis=1)
    b = np.roll(a[..., 2], -d, axis=1)
    ba = np.roll(al, -d, axis=1)
    a[..., 0] = np.maximum(r * (ra > 0), a[..., 0] * (al > 0) * 0)
    a[..., 0] = np.where(ra > al, r, a[..., 0])
    a[..., 2] = np.where(ba > al, b, a[..., 2])
    a[..., 3] = np.maximum(al, np.maximum(ra, ba) // 2)
    return Image.fromarray(a, 'RGBA')


# ─────────────────────────────── голографические панели ───────────────────────────────
def panel_base(w, h, col, fill_a=205, ch=22):
    """Панель со срезанными углами: тёмное стекло с подсветкой сверху, строки развёртки, контур и уголки.
    → (панель RGBA w×h, слой контура для свечения)."""
    ss = 3
    pts = [(ch, 0), (w, 0), (w, h - ch), (w - ch, h), (0, h), (0, ch)]
    sp = [(x * ss, y * ss) for x, y in pts]
    m = Image.new('L', (w * ss, h * ss), 0)
    ImageDraw.Draw(m).polygon(sp, fill=255)
    m = np.asarray(m.resize((w, h), Image.LANCZOS), np.float32) / 255
    yy = np.arange(h, dtype=np.float32)[:, None]
    base = np.array(C.mix(INK, col, 0.10), np.float32)
    colf = np.array(col, np.float32)
    k = (0.20 * (1 - yy / h) ** 2.2 + 0.04)[..., None]
    rgb = base[None, None, :] * (1 - k) + colf[None, None, :] * k
    rgb = np.broadcast_to(rgb, (h, w, 3)).copy()
    rgb[(np.arange(h) % 4) == 0] += colf * 0.07
    al = m * fill_a
    al[(np.arange(h) % 4) == 0] *= 1.08
    arr = np.concatenate([np.clip(rgb, 0, 255), np.clip(al, 0, 255)[..., None]], -1).astype(np.uint8)
    pl = Image.fromarray(arr, 'RGBA')
    ol = Image.new('L', (w * ss, h * ss), 0)
    d = ImageDraw.Draw(ol)
    d.polygon(sp, outline=255, width=int(2.4 * ss))
    L = min(64, w // 4) * ss
    wd = int(5 * ss)
    x1, y1 = w * ss - 1, h * ss - 1
    d.line((x1 - L, wd // 2, x1 - wd // 2, wd // 2, x1 - wd // 2, L), fill=255, width=wd)        # уголки
    d.line((wd // 2, y1 - L, wd // 2, y1 - wd // 2, L, y1 - wd // 2), fill=255, width=wd)
    ol = ol.resize((w, h), Image.LANCZOS)
    oc = Image.new('RGBA', (w, h), C.mix(col, WHITE, 0.25) + (0,))
    oc.putalpha(ol)
    pl.alpha_composite(oc)
    return pl, oc


def panel_finish(pl, oc, col, r=9):
    """Свечение контура вокруг панели → картинка больше на 3r с каждой стороны."""
    g = C.glow(oc, r, 1.1, col)
    pad = r * 3
    out = Image.new('RGBA', g.size, (0, 0, 0, 0))
    out.alpha_composite(g)
    out.alpha_composite(pl, (pad, pad))
    return out


# ─────────────────────────────── голограмма эмблемы ───────────────────────────────
def holo_emblem(team, size, col, k):
    """Эмблема как голограмма: цвета смешаны с цветом света (k — доля), тёмное приподнято, строки развёртки."""
    key = ('he', team.name, size, col, k)
    if key in _CACHE:
        return _CACHE[key]
    e = team.emb(size)
    a = np.asarray(e, np.float32)
    rgb, al = a[..., :3], a[..., 3]
    lum = rgb @ np.array([0.3, 0.59, 0.11], np.float32)
    mono = np.array(col, np.float32)[None, None, :] * (0.32 + 0.95 * lum / 255)[..., None]
    out = rgb * (1 - k) + mono * k
    out = out * 0.86 + 34 + 30 * k
    rows = np.arange(al.shape[0]) % 4
    al = al * 0.94
    al[rows == 0] *= 0.42
    al[rows == 1] *= 0.82
    im = Image.fromarray(np.concatenate([np.clip(out, 0, 255), al[..., None]], -1).astype(np.uint8), 'RGBA')
    im = C.glow(im, 13, 0.75, col)
    _CACHE[key] = im
    return im


def voxels(team, size, col, k, cell=12):
    """Воксели эмблемы: центры клеток (от центра эмблемы) и их цвета."""
    key = ('vx', team.name, size, col, k, cell)
    if key in _CACHE:
        return _CACHE[key]
    e = holo_emblem(team, size, col, k)
    pad = (e.width - size) // 2
    a = np.asarray(e.crop((pad, pad, pad + size, pad + size)), np.float32)
    n = size // cell
    a = a[:n * cell, :n * cell].reshape(n, cell, n, cell, 4)
    al = a[..., 3].mean(axis=(1, 3))
    rgb = (a[..., :3] * a[..., 3:4]).sum(axis=(1, 3)) / np.maximum(1, a[..., 3].sum(axis=(1, 3)))[..., None]
    ys, xs = np.nonzero(al > 70)
    pts = np.stack([(xs + 0.5) * cell - n * cell / 2, (ys + 0.5) * cell - n * cell / 2], -1)
    cols = np.clip(rgb[ys, xs] * 1.15 + 20, 0, 255)
    rnd = np.random.default_rng(len(team.name) * 7 + size)
    out = dict(p=pts, c=cols, cell=cell, r1=rnd.uniform(0, 1, len(pts)), r2=rnd.uniform(-1, 1, len(pts)),
               r3=rnd.uniform(-1, 1, len(pts)))
    _CACHE[key] = out
    return out


class Hologram(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 70, drop=19 * 60 / 70, line=None, team=7, pre=1,
                 hold=5, cta=3, seed=31, **kw):
        """Сцены: интро → команда (team долей) ×2 → помехи (pre) → дроп-прогноз (hold) → Telegram (cta); доли — от дропа."""
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.line = league, when, coef, line
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
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
        self.cover_t = max(1.6, self.t1 - 0.5)
        self._prep()

    # ── заготовки ──
    def _prep(self):
        self.club = {'h': club(self.h), 'a': club(self.a)}
        self.col = {s: holo(self.club[s], 0.8) for s in ('h', 'a')}
        self.cf = holo(self.club[self.side], 0.92)
        self.bg = self._bg()
        for c in (CYAN, self.col['h'], self.col['a'], self.cf):
            self._cone(c)
            self._disc(c)
        self.tag = C.text(F.tag(self.league), 'mono', 30, DIM, 700, track=0.22)
        self.handle_im = C.text(C.HANDLE, 'exo', 44, (214, 238, 248), 700)
        # интро
        self.date = C.glow(C.text('%s · %s' % (F.lg_ru(self.league), self.when), 'exo', 52, TXT, 800, max_w=980), 10, 0.6, CYAN)
        self.i_role = {s: C.text('ХОЗЯЕВА' if s == 'h' else 'ГОСТИ', 'mono', 27, DIM, 700, track=0.24) for s in 'ha'}
        self.i_name = {s: C.glow(C.text(t.up, 'exo', 60, TXT, 900, max_w=450), 10, 0.5, CYAN) for s, t in (('h', self.h), ('a', self.a))}
        self.odds_lab = C.text('ОСНОВНОЕ ВРЕМЯ', 'mono', 30, CYAN, 700, track=0.26)
        self.odds = self._odds() if self.line else []
        # команды
        self.T = {s: self._team_data(s) for s in 'ha'}
        # помехи
        self.title = C.glow(C.text('%s — %s' % (self.h.up, self.a.up), 'exo', 66, TXT, 900, max_w=980), 10, 0.5, CYAN)
        self.pre_name = {s: C.glow(C.text(t.up, 'exo', 52, TXT, 900, max_w=450), 10, 0.5, self.col[s]) for s, t in (('h', self.h), ('a', self.a))}
        # прогноз
        self.p_panel = self._pick_panel()
        self.kef = self._kef_panel() if self.coef else None
        self.tg = C.tg_plate(960, 172, font='exo')
        # голограммы (до fork)
        for s, t in (('h', self.h), ('a', self.a)):
            holo_emblem(t, 260, CYAN, 0.55)
            holo_emblem(t, 270, self.col[s], 0.62)
            holo_emblem(t, 300, self.col[s], 0.6)
            voxels(t, 260, CYAN, 0.55)
            voxels(t, 270, self.col[s], 0.62)
        holo_emblem(self.fav, 380, self.cf, 0.12)

    def _bg(self):
        """Тёмная комната: градиент, пол-сетка в перспективе под диском, пылинки, виньетка."""
        bg = C.vgrad(W, H, [(0, (6, 12, 22)), (0.55, (3, 8, 15)), (0.7, (4, 10, 18)), (1, (2, 4, 8))])
        d = ImageDraw.Draw(bg)
        vy, y0 = 980, 1366
        for i in range(-14, 15):                              # линии пола к точке схода
            xb = DX + i * 150
            d.line((DX + (xb - DX) * 0.0, vy, xb, H), fill=(0, 0, 0), width=1)
            x_top = DX + (xb - DX) * (y0 - vy) / (H - vy)
            d.line((x_top, y0, xb, H), fill=(16, 34, 48), width=2)
        for j in range(12):
            f = (j + 1) / 12
            y = y0 + (H - y0) * f ** 1.8
            d.line((0, y, W, y), fill=(14, 30, 44), width=2)
        rnd = np.random.default_rng(5)
        for _ in range(140):
            x, y, r = rnd.uniform(0, W), rnd.uniform(0, 1300), rnd.uniform(0.7, 1.8)
            v = int(rnd.uniform(28, 70))
            d.ellipse((x - r, y - r, x + r, y + r), fill=(v // 2, v, v + 10))
        bg = C.vignette(bg, 0.5, 2.0)
        return bg.convert('RGBA')

    def _cone(self, col):
        """Конус света от диска вверх (RGB-свет) + маска для полосы обновления."""
        key = ('cone', col)
        if key in _CACHE:
            return _CACHE[key]
        y0, y1 = TOP_Y, APEX_Y + 20
        hh = y1 - y0
        yy, xx = np.mgrid[y0:y1, 0:W].astype(np.float32)
        f = np.clip((APEX_Y - yy) / (APEX_Y - TOP_Y), 0, 1)            # 0 у диска, 1 сверху
        hw = 210 + f * 380
        dx = np.abs(xx - DX)
        edge = np.clip((hw - dx) / (50 + 140 * f), 0, 1) ** 1.3
        inten = (0.62 * (1 - f) ** 1.5 + 0.13) * edge
        ang = np.arctan2(xx - DX, (APEX_Y + 160) - yy)
        rays = 0.78 + 0.22 * np.cos(ang * 46) ** 2
        inten *= rays
        inten *= np.clip((yy - TOP_Y) / 220, 0, 1)                    # мягко гаснет сверху
        inten *= np.clip((APEX_Y + 14 - yy) / 20, 0, 1)
        core = np.exp(-(dx / (40 + 160 * f)) ** 2) * (1 - f) ** 2 * 0.35  # яркая сердцевина над диском
        inten = inten + core
        light = np.clip(inten[..., None] * np.array(col, np.float32) * 0.42, 0, 255).astype(np.uint8)
        out = (Image.fromarray(light, 'RGB'), y0)
        _CACHE[key] = out
        return out

    def _disc(self, col):
        """Диск-проектор: металлический цилиндр, стеклянная верхняя грань с кольцами света, отблеск на полу."""
        key = ('disc', col)
        if key in _CACHE:
            return _CACHE[key]
        ss = 3
        w, h = 2 * DRX + 120, 2 * DRY + 140
        cx, cy = w / 2, 60 + DRY
        im = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        S = lambda *v: [x * ss for x in v]
        body = 38
        d.ellipse(S(cx - DRX, cy + body - DRY, cx + DRX, cy + body + DRY), fill=(14, 20, 28, 255))
        d.rectangle(S(cx - DRX, cy, cx + DRX, cy + body), fill=(18, 26, 36, 255))
        for i in range(0, 2 * DRX, 4):                         # блик на боковине
            x = cx - DRX + i
            v = 22 + int(26 * math.exp(-((i - DRX * 0.7) / (DRX * 0.5)) ** 2))
            d.line(S(x, cy, x, cy + body + DRY * math.sqrt(max(0, 1 - ((x - cx) / DRX) ** 2))), fill=(v, v + 8, v + 16, 255), width=4 * ss)
        d.ellipse(S(cx - DRX, cy - DRY, cx + DRX, cy + DRY), fill=(10, 18, 28, 255), outline=(70, 90, 110, 255), width=3 * ss)
        lc = tuple(col) + (255,)
        for f, wd in ((0.93, 3), (0.72, 2), (0.5, 2)):
            d.ellipse(S(cx - DRX * f, cy - DRY * f, cx + DRX * f, cy + DRY * f), outline=C.mix(col, INK, 0.25) + (255,), width=wd * ss)
        d.ellipse(S(cx - DRX * 0.22, cy - DRY * 0.22, cx + DRX * 0.22, cy + DRY * 0.22), fill=lc)
        im = im.resize((w, h), Image.LANCZOS)
        # свет: кольца и сердцевина + отблеск на полу
        lt = Image.new('L', (w * ss, h * ss), 0)
        dl = ImageDraw.Draw(lt)
        dl.ellipse(S(cx - DRX * 0.93, cy - DRY * 0.93, cx + DRX * 0.93, cy + DRY * 0.93), outline=200, width=5 * ss)
        dl.ellipse(S(cx - DRX * 0.3, cy - DRY * 0.3, cx + DRX * 0.3, cy + DRY * 0.3), fill=255)
        lt = lt.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(10))
        light = Image.merge('RGB', [lt.point(lambda v, c=c: int(v * c / 255)) for c in col])
        floor = radial_light(2 * DRX + 300, col, 0.55, 1.6).resize((2 * DRX + 300, 2 * DRY + 120))
        out = (im, light, floor)
        _CACHE[key] = out
        return out

    def _card(self, w, h, col, fn):
        pl, oc = panel_base(w, h, col)
        fn(pl)
        return panel_finish(pl, oc, col)

    def _odds(self):
        out = []
        n = len(self.line)
        for i, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), self.line)):
            def fill(pl, lab=lab, v=v):
                C.put(pl, C.text(lab, 'mono', 40, CYAN, 800, track=0.1), pl.width / 2, 52)
                C.put(pl, C.text(C.fmt_k(v), 'exo', 104, WHITE, 900, max_w=pl.width - 40), pl.width / 2, 140)
            im = self._card(312, 212, CYAN, fill)
            out.append(self._angled(im, i, n))
        return out

    def _angled(self, im, i, n):
        """Вогнутый экран: крайние панели повёрнуты к зрителю внешним краем."""
        if n < 2:
            return im
        f = (i - (n - 1) / 2) / ((n - 1) / 2)                 # −1 … 1
        if abs(f) < 0.01:
            return im
        kk = 0.075 * abs(f)
        kl, kr = (1 + kk, 1 - kk * 0.6) if f < 0 else (1 - kk * 0.6, 1 + kk)
        return warp(im, kl, kr, 1 - 0.05 * abs(f))

    # ── карточки команды ──
    def _game_card(self, g, col):
        def fill(pl):
            w, h = pl.size
            dt = C.text(g['date'], 'mono', 25, DIM, 700) if g['date'] else None
            room = w - 46 - (dt.width + 14 if dt else 0)
            nm = C.text(g['opp'].upper(), 'exo', 38, TXT, 800, max_w=room)
            C.put(pl, nm, 26, 46 - nm.height / 2, anchor='tl')
            if dt:
                C.put(pl, dt, w - 22 - dt.width, 46 - dt.height / 2, anchor='tl')
            if g['home'] is not None:
                hm = C.text('ДОМА' if g['home'] else 'В ГОСТЯХ', 'mono', 23, C.mix(col, WHITE, 0.2), 700, track=0.12)
                C.put(pl, hm, 26, 86 - hm.height / 2, anchor='tl')
            sc = C.text(g['score'], 'exo', 86, WHITE, 900)
            yc = 152
            C.put(pl, sc, 24, yc - sc.height / 2, anchor='tl')
            if g['note']:
                nt = C.text(g['note'], 'mono', 30, DIM, 800, max_w=w - sc.width - 120)
                C.put(pl, nt, 24 + sc.width + 10, yc + sc.height / 2 - nt.height, anchor='tl')
            rc = F.res_col(g['res'])
            ch = C.rrect(66, 66, 14, rc)
            C.put(ch, C.text(g['res'] or '?', 'exo', 44, WHITE, 900), 33, 33)
            C.put(pl, C.glow(ch, 8, 0.7, rc), w - 26 - 33, yc)
            C.put(pl, C.rrect(w - 52, 6, 3, rc, 230), w / 2, h - 13)
        return self._card(320, 212, col, fill)

    def _stat_card(self, lab, val, sub, col, vcol):
        def fill(pl):
            w, h = pl.size
            lb = C.text(lab, 'mono', 26, DIM, 700, track=0.12, max_w=w - 46)
            C.put(pl, lb, 26, 36 - lb.height / 2, anchor='tl')
            v = C.text(val, 'exo', 84, vcol, 900, max_w=w - 46)
            yc = 102
            C.put(pl, v, 24, yc - v.height / 2, anchor='tl')
            if sub:
                room = w - 24 - v.width - 14 - 20
                if room > 60:
                    s = C.text(sub, 'mono', 27, C.mix(col, WHITE, 0.3), 700, max_w=room)
                    C.put(pl, s, 24 + v.width + 14, yc + v.height / 2 - s.height - 4, anchor='tl')
        return self._card(320, 152, col, fill)

    def _stats(self, s):
        out = []
        if s['points'] is not None:
            sub = ('за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей'))) if s['gp'] is not None else ''
            out.append(('ОЧКИ', '%d' % s['points'], sub, WHITE))
        if s['place'] is not None:
            out.append(('МЕСТО', '%d' % s['place'], s['place_scope'], WHITE))
        if s['gd'] is not None:
            gcol = F.WIN if s['gd'] > 0 else F.LOSS if s['gd'] < 0 else WHITE
            out.append(('РАЗНИЦА ШАЙБ', F.gd_txt(s['gd']), '', gcol))
        return out

    def _extras(self, rec):
        out = []
        for key, lab in (('pp', 'БОЛЬШИНСТВО'), ('pk', 'МЕНЬШИНСТВО')):
            v = pct(rec.get(key)) if rec.get(key) is not None else None
            if v:
                out.append((lab, v))
        m = re.match(r'\s*(ОТ|В|П)\s*(\d+)', str(rec.get('streak') or ''))
        if m and int(m.group(2)) >= 2:
            n = int(m.group(2))
            word = {'В': plural(n, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'), 'П': plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ'),
                    'ОТ': plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ') + ' В ОТ'}[m.group(1)]
            out.append(('СЕРИЯ', '%d %s' % (n, word)))
        return out[:3]

    def _pills(self, ext, col):
        n = len(ext)
        out = []
        if not n:
            return out
        gap = 22
        w = int((1000 - gap * (n - 1)) / n)
        h = 70
        for lab, val in ext:
            def fill(pl, lab=lab, val=val):
                v = C.text(val, 'exo', 40, WHITE, 900, max_w=w - 60)
                lb = C.text(lab, 'mono', 24 if n > 2 else 27, DIM, 700, track=0.08, max_w=max(60, w - v.width - 56))
                tot = lb.width + 14 + v.width
                x = (w - tot) / 2
                C.put(pl, lb, x, h / 2 - lb.height / 2, anchor='tl')
                C.put(pl, v, x + lb.width + 14, h / 2 - v.height / 2, anchor='tl')
            pl, oc = panel_base(w, h, col, 215, ch=14)
            fill(pl)
            out.append(panel_finish(pl, oc, col, 6))
        return out

    def _team_data(self, s):
        tm = self.h if s == 'h' else self.a
        col = self.col[s]
        st = self.st[s]
        games = [self._game_card(g, col) for g in st['games'][:3]]
        games = [self._angled(im, i, len(games)) for i, im in enumerate(games)]
        stats = [self._stat_card(lab, v, sub, col, vc) for lab, v, sub, vc in self._stats(st)[:3]]
        stats = [self._angled(im, i, len(stats)) for i, im in enumerate(stats)]
        pills = self._pills(self._extras(self.raw[s]), col)
        name = C.glow(C.text(tm.up, 'exo', 104, TXT, 900, max_w=960), 14, 0.7, col)
        rt = C.text('ХОЗЯЕВА' if s == 'h' else 'ГОСТИ', 'mono', 28, INK, 800, track=0.26)
        role = C.rrect(rt.width + 54, 48, 10, col)
        C.put(role, rt, role.width / 2, 24)
        return dict(tm=tm, col=col, games=games, stats=stats, pills=pills, name=name, role=C.glow(role, 8, 0.6, col))

    # ── прогноз ──
    def _pick_panel(self):
        col = self.cf
        m = re.match(r'(ПОБЕДА)\s+(.+)$', self.pick1)
        l1 = m.group(1) if m else ''
        nm = m.group(2) if m else self.pick1

        def fill(pl):
            w, h = pl.size
            y = 62
            if l1:
                C.put(pl, C.text(l1, 'exo', 64, TXT, 800, track=0.1), w / 2, y)
                y += 104
            else:
                y += 50
            big = C.text(nm, 'exo', 140, WHITE, 900, max_w=w - 70)
            C.put(pl, C.glow(tint_text(big, col), 14, 0.6, col), w / 2, y)
            if self.pick2:
                C.put(pl, C.text(self.pick2, 'mono', 38, C.mix(col, WHITE, 0.45), 700, track=0.14, max_w=w - 60), w / 2, h - 46)
        return self._card(960, 300, col, fill)

    def _kef_panel(self):
        col = self.cf
        pl, oc = panel_base(540, 116, col, 235, ch=18)
        kt = C.text('КЭФ', 'mono', 40, C.mix(col, WHITE, 0.4), 800, track=0.14)
        kv = C.text(C.fmt_k(self.coef), 'exo', 84, WHITE, 900)
        tot = kt.width + 26 + kv.width
        x = (540 - tot) / 2
        C.put(pl, kt, x, 58 - kt.height / 2 + 6, anchor='tl')
        C.put(pl, kv, x + kt.width + 26, 58 - kv.height / 2, anchor='tl')
        return panel_finish(pl, oc, col, 12)

    # ── время ──
    def beat_pulse(self, t):
        x = ((t - self.drop) / self.u) % 1.0
        return math.exp(-x * 6)

    def scene_col(self, t):
        if t < self.t1:
            return CYAN
        if t < self.t2:
            return self.col['h']
        if t < self.tp:
            return self.col['a']
        if t < self.drop:
            q = int((t - self.tp) / (self.u / (4 if t < self.drop - self.u / 2 else 8)))
            return self.col['h'] if q % 2 == 0 else self.col['a']
        return self.cf

    # ── слои ──
    def draw_cone(self, fr, t, col, k):
        cone, y0 = self._cone(col)
        add(fr, cone, 0, y0, k)
        # полоса обновления: на каждую долю снизу вверх
        x = ((t - self.drop) / self.u) % 1.0
        yb = APEX_Y - x * (APEX_Y - TOP_Y) * 1.1
        hb = 70
        a, b = int(yb - hb), int(yb + hb)
        a, b = max(y0, a), min(y0 + cone.height, b)
        if b - a > 4:
            strip = np.asarray(cone.crop((0, a - y0, W, b - y0)), np.float32)
            wy = np.exp(-((np.arange(a, b) - yb) / (hb * 0.45)) ** 2)[:, None, None]
            strip = Image.fromarray(np.clip(strip * wy * 1.3 * k, 0, 255).astype(np.uint8), 'RGB')
            add(fr, strip, 0, a, 1.0)

    def draw_disc(self, fr, t, col, k=1.0, pulse=0.0):
        im, light, floor = self._disc(col)
        add(fr, floor, DX - floor.width / 2, DY + 20 - floor.height / 2, 0.8 * k * (0.7 + 0.5 * pulse))
        C.put(fr, im, DX, DY - 60 - DRY + im.height / 2, k)
        # бегущие риски по кольцу
        lay = Image.new('RGBA', (2 * DRX + 40, 2 * DRY + 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        cx, cy = lay.width / 2, lay.height / 2
        rot = t * 0.9
        cc = C.mix(col, WHITE, 0.3)
        for i in range(40):
            ang = rot + i * 2 * math.pi / 40
            if i % 5 == 4:
                continue
            r0, r1 = 0.78, 0.86
            x0, y0 = cx + DRX * r0 * math.cos(ang), cy + DRY * r0 * math.sin(ang)
            x1, y1 = cx + DRX * r1 * math.cos(ang), cy + DRY * r1 * math.sin(ang)
            front = 0.55 + 0.45 * math.sin(ang)
            d.line((x0, y0, x1, y1), fill=cc + (int(255 * k * front),), width=3)
        fr.alpha_composite(lay, (int(DX - cx), int(DY - cy)))
        add(fr, light, DX - light.width / 2, DY - 60 - DRY, k * (0.75 + 0.6 * pulse))

    def floor_ring(self, fr, t, t0, col, dur=0.8, big=1.0):
        dt = t - t0
        if not 0 <= dt < dur:
            return
        q = C.out_cubic(dt / dur)
        rx, ry = DRX * (1 + 1.6 * big * q), DRY * (1 + 1.6 * big * q)
        a = (1 - dt / dur) ** 1.5
        lay = Image.new('RGB', (int(2 * rx + 40), int(2 * ry + 40)), (0, 0, 0))
        d = ImageDraw.Draw(lay)
        c = tuple(int(v * a) for v in C.mix(col, WHITE, 0.3))
        d.ellipse((20, 20, 20 + 2 * rx, 20 + 2 * ry), outline=c, width=5)
        lay = ImageChops.add(lay, lay.filter(ImageFilter.GaussianBlur(6)))
        add(fr, lay, DX - lay.width / 2, DY + 18 - lay.height / 2)

    def emblem(self, fr, t, im, cx, cy, a=1.0, phase=0.0, amp=0.4, flick=0.1, gl=0.0, period=4.0, halo=None, halo_k=0.5):
        """Голограмма эмблемы: поворот вокруг вертикали (псевдо-3D), покачивание, мерцание, расслоение, помехи."""
        if a <= 0.01:
            return
        fi = int(round(t * C.FPS))
        th = amp * math.sin(2 * math.pi * t / (period * self.u) + phase)
        kk = 0.11 * math.sin(th)
        img = warp(im, 1 + kk, 1 - kk, math.cos(th))
        img = rgb_off(img, 3)
        if gl > 0.03:
            img = glitch(img, gl, fi + int(phase * 100))
        if halo is not None:
            add(fr, halo, cx - halo.width / 2, cy - halo.height / 2, halo_k * a)
        al = a * (1 - flick * noise(fi, int(phase * 10)))
        C.put(fr, img, cx, cy + 7 * math.sin(2 * math.pi * t / (2 * self.u) + phase), al)

    def vox(self, fr, t, vx, cx, cy, q, mode):
        """Воксели: mode 'out' — рассыпаются вверх (q 0..1), 'in' — летят с диска и собираются (q 0..1)."""
        p, cols, cell = vx['p'], vx['c'], vx['cell']
        d = ImageDraw.Draw(fr)
        n = len(p)
        if mode == 'out':
            tl = np.clip((q - vx['r1'] * 0.35) / 0.65, 0, 1)
            x = cx + p[:, 0] * (1 + 0.6 * tl) + vx['r2'] * 160 * tl
            y = cy + p[:, 1] - (220 + 260 * vx['r1']) * tl ** 1.4 + vx['r3'] * 40 * tl
            sz = cell * (1 - tl) * 0.9
            br = (1 - tl) ** 0.8
        else:
            order = (0.5 - p[:, 1] / (2 * np.abs(p[:, 1]).max() + 1))      # снизу вверх
            tl = np.clip((q - order * 0.45 - vx['r1'] * 0.1) / 0.45, 0, 1)
            e = 1 - (1 - tl) ** 3
            sx = DX + vx['r2'] * DRX * 0.8
            sy = DY + vx['r3'] * DRY * 0.6
            x = sx + (cx + p[:, 0] - sx) * e
            y = sy + (cy + p[:, 1] - sy) * e
            sz = cell * (0.35 + 0.55 * e)
            br = 0.4 + 0.6 * e
            br = br * (tl > 0)
        for i in range(n):
            if sz[i] < 1.2 or br[i] < 0.03:
                continue
            c = tuple(int(v * br[i]) for v in cols[i])
            hs = sz[i] / 2
            d.rectangle((x[i] - hs, y[i] - hs, x[i] + hs, y[i] + hs), fill=c)

    def unfold(self, fr, im, cx, cy, ta, t, te=None, a=1.0):
        """Панель раскрывается из светящейся линии (ta) и схлопывается (te)."""
        if t < ta:
            return
        p = C.seg(t, ta, ta + 0.26)
        sy = max(0.02, C.out_back(p, 1.5))
        sx = 0.9 + 0.1 * C.out_cubic(p)
        al = a * min(1.0, 0.35 + p * 1.3)
        if p < 1 and int(round(t * C.FPS)) % 2 == 0:
            al *= 0.7
        if te is not None and t >= te:
            q = C.seg(t, te, te + 0.22)
            if q >= 1:
                return
            sy *= max(0.02, 1 - C.in_cubic(q))
            sx *= 1 + 0.08 * q
            al *= 1 - q * 0.5
        if abs(sx - 1) > 0.003 or abs(sy - 1) > 0.003:
            im = im.resize((max(2, int(im.width * sx)), max(2, int(im.height * sy))), Image.BILINEAR)
        C.put(fr, im, cx, cy, al)
        if p < 1:                                            # вспышка-линия раскрытия
            ln = radial_light(int(im.width * 1.1), C.mix(CYAN, WHITE, 0.5), 1.0, 1.2).resize((int(im.width * 1.1), 24))
            add(fr, ln, cx - ln.width / 2, cy - 12, (1 - p) * 0.9)

    def ray(self, fr, x0, y0, x1, y1, col, k):
        if k <= 0.02:
            return
        xa, ya = min(x0, x1) - 6, min(y0, y1) - 6
        lay = Image.new('RGB', (int(abs(x1 - x0)) + 13, int(abs(y1 - y0)) + 13), (0, 0, 0))
        ImageDraw.Draw(lay).line((x0 - xa, y0 - ya, x1 - xa, y1 - ya), fill=tuple(int(c * k) for c in col), width=2)
        add(fr, lay, xa, ya)

    # ── сцены ──
    def intro(self, fr, t):
        u = self.u
        te = self.t1
        out = C.seg(t, te, te + 0.3)
        # дата / время
        q = C.out_expo(C.seg(t, 0.05, 0.45))
        if out < 1:
            g = (1 - q) * 0.9 + out
            C.put(fr, glitch(self.date, g, int(t * 30)), W / 2, 336 + 14 * (1 - q), q * (1 - out))
        for s, x, t0 in (('h', 285, 0.15), ('a', 795, 0.3)):
            tm = self.h if s == 'h' else self.a
            im = holo_emblem(tm, 260, CYAN, 0.55)
            cy = 600
            if t < te:
                qa = C.seg(t, t0, t0 + 0.6)
                if qa < 1:
                    self.vox(fr, t, voxels(tm, 260, CYAN, 0.55), x, cy, qa, 'in')
                ka = C.seg(qa, 0.75, 1.0)
                self.emblem(fr, t, im, x, cy, ka, phase=0.0 if s == 'h' else 2.1, amp=0.42, halo=radial_light(520, CYAN, 0.35),
                            halo_k=0.6)
            else:
                self.vox(fr, t, voxels(tm, 260, CYAN, 0.55), x, cy, C.seg(t, te, te + 0.55), 'out')
            qn = C.out_expo(C.seg(t, t0 + 0.35, t0 + 0.75)) * (1 - out)
            C.put(fr, self.i_role[s], x, 775 + 10 * (1 - qn), qn * 0.95)
            C.put(fr, self.i_name[s], x, 826 + 10 * (1 - qn), qn)
        if self.odds:
            tb = self.b(-(2 * self.team_n + self.pre) - 3) if self.b(-(2 * self.team_n + self.pre) - 3) > 0.4 else 0.6
            ql = C.out_expo(C.seg(t, tb - 0.2, tb + 0.2)) * (1 - out)
            C.put(fr, self.odds_lab, W / 2, 925, ql)
            n = len(self.odds)
            for i, im in enumerate(self.odds):
                x = W / 2 + (i - (n - 1) / 2) * 345
                self.unfold(fr, im, x, 1068, tb + i * u / 4, t, te)

    def team(self, fr, t, s, ts, te):
        u = self.u
        T = self.T[s]
        col = T['col']
        tm = T['tm']
        out = C.seg(t, te, te + 0.3)
        # название и роль
        if out < 1:
            q = C.out_expo(C.seg(t, ts + 0.04, ts + 0.4))
            g = (1 - q) + out * 1.2 + 0.5 * math.exp(-((t - ts) % u) / 0.05) * (t - ts > 0.5)
            C.put(fr, glitch(T['name'], min(1.0, g * 0.8), int(t * 30) + 7), W / 2, 334, q * (1 - out))
            C.put(fr, T['role'], W / 2, 412, C.seg(t, ts + 0.2, ts + 0.45) * (1 - out))
        # голограмма над диском
        ex, ey = W / 2, 1100
        im = holo_emblem(tm, 270, col, 0.62)
        vx = voxels(tm, 270, col, 0.62)
        if t < te:
            qa = C.seg(t, ts + 0.08, ts + 0.62)
            if qa < 1:
                self.vox(fr, t, vx, ex, ey, qa, 'in')
            ka = C.seg(qa, 0.75, 1.0)
            gl = 0.55 * math.exp(-((t - ts) % u) / 0.07) if t - ts > 0.6 else 0.0
            self.emblem(fr, t, im, ex, ey, ka, phase=1.0, amp=0.45, gl=gl, halo=radial_light(560, col, 0.4), halo_k=0.7)
        else:
            self.vox(fr, t, vx, ex, ey, C.seg(t, te, te + 0.55), 'out')
        # панели
        xs = [W / 2 + (i - 1) * 350 for i in range(3)]
        for i, im in enumerate(T['games']):
            ta = ts + 0.5 * u + i * u / 4
            x = xs[i] if len(T['games']) == 3 else W / 2 + (i - (len(T['games']) - 1) / 2) * 350
            self.ray(fr, ex, ey - 120, x, 580 + 100, col, 0.5 * (1 - C.seg(t, ta, ta + 0.5)) * (t >= ta) * (t < te))
            self.unfold(fr, im, x, 575, ta, t, te)
        for i, im in enumerate(T['stats']):
            ta = ts + 1.5 * u + i * u / 4
            x = W / 2 + (i - (len(T['stats']) - 1) / 2) * 350
            self.ray(fr, ex, ey - 120, x, 800 + 70, col, 0.5 * (1 - C.seg(t, ta, ta + 0.5)) * (t >= ta) * (t < te))
            self.unfold(fr, im, x, 800, ta, t, te)
        n = len(T['pills'])
        if n:
            gap = 22
            w = (1000 - gap * (n - 1)) / n
            for i, im in enumerate(T['pills']):
                ta = ts + 2.5 * u + i * u / 8
                x = W / 2 + (i - (n - 1) / 2) * (w + gap)
                self.unfold(fr, im, x, 930, ta, t, te)

    def interference(self, fr, t):
        u, D = self.u, self.drop
        ts = self.tp
        q = C.out_expo(C.seg(t, ts, ts + 0.2))
        fi = int(round(t * C.FPS))
        C.put(fr, glitch(self.title, 0.25 + 0.5 * noise(fi, 3), fi), W / 2, 338, q)
        step = u / 4 if t < D - u / 2 else u / 8
        k = int((t - ts) / step) % 2
        for s, x, ph in (('h', 300, 0.0), ('a', 780, 2.0)):
            tm = self.h if s == 'h' else self.a
            on = (k == 0) == (s == 'h')
            a = (1.0 if on else 0.38) * q
            g = 0.25 + (0.5 if on else 0.15) * noise(fi, 5 if s == 'h' else 9)
            self.emblem(fr, t, holo_emblem(tm, 300, self.col[s], 0.6), x, 730, a, phase=ph, amp=0.5, flick=0.35, gl=g,
                        halo=radial_light(520, self.col[s], 0.35), halo_k=0.8 if on else 0.3)
            C.put(fr, self.pre_name[s], x, 948, q * (1.0 if on else 0.5))
        # кольца интерференции от диска вверх
        for j in range(3):
            ph = ((t - ts) / (u / 2) + j / 3) % 1.0
            y = DY - 40 - ph * 300
            rx = DRX * (0.9 + 0.5 * ph)
            lay = Image.new('RGB', (int(2 * rx + 20), 60), (0, 0, 0))
            c = tuple(int(v * (1 - ph) * 0.7) for v in C.mix(self.scene_col(t), WHITE, 0.3))
            ImageDraw.Draw(lay).ellipse((10, 30 - DRY * 0.5 * (1 - ph * 0.3), 10 + 2 * rx, 30 + DRY * 0.5 * (1 - ph * 0.3)), outline=c, width=3)
            add(fr, lay, DX - lay.width / 2, y - 30)
        # строки помех через весь луч
        for j in range(5):
            y = int(TOP_Y + noise(fi, 20 + j) * (APEX_Y - TOP_Y))
            hh = 2 + int(noise(fi, 40 + j) * 5)
            add(fr, Image.new('RGB', (W, hh), tuple(int(v * 0.22) for v in self.scene_col(t))), 0, y)

    def pick(self, fr, t):
        u, D = self.u, self.drop
        tc = self.t_cta
        kc = C.in_out(C.seg(t, tc, tc + 0.5))
        dt = t - D
        bp = self.beat_pulse(t)
        # голограмма прогноза — полный цвет, стабильная
        ey = C.lerp(608, 470, kc)
        es = C.lerp(1.0, 0.74, kc) * (1.22 - 0.22 * C.out_expo(C.seg(t, D, D + 0.4))) * (1 + 0.03 * bp)
        im = holo_emblem(self.fav, 380, self.cf, 0.12)
        halo = radial_light(820, self.cf, 0.55, 1.6)
        add(fr, halo, W / 2 - halo.width / 2, ey - halo.height / 2, (0.55 + 0.35 * bp) * C.lerp(1, 0.7, kc))
        self.emblem(fr, t, C.scale(im, es), W / 2, ey, 1.0, phase=0.4, amp=0.3, flick=0.04, period=8,
                    gl=0.6 * math.exp(-max(0.0, dt) / 0.12))
        # панель прогноза
        q = C.out_expo(C.seg(t, D, D + 0.3))
        ps = C.lerp(1.0, 0.88, kc) * (0.9 + 0.1 * q)
        py = C.lerp(968, 762, kc)
        C.put(fr, C.scale(self.p_panel, ps), W / 2, py, min(1.0, 0.45 + q))
        if self.kef is not None:
            qk = C.out_back(C.seg(t, D + 0.06, D + 0.36), 1.6)
            ks = C.lerp(1.0, 0.92, kc) * (0.75 + 0.25 * qk) * (1 + 0.035 * bp * (dt > 0.4))
            ky = C.lerp(1190, 985, kc)
            C.put(fr, C.scale(self.kef, ks), W / 2, ky, min(1.0, 0.3 + qk))

    def burst(self, fr, t):
        dt = t - self.drop
        if not 0 <= dt < 0.9:
            return
        for lag, big in ((0.0, 2.2), (0.12, 1.4)):
            self.floor_ring(fr, t, self.drop + lag, self.cf, 0.75, big)
        r = int(300 + 900 * C.out_expo(dt / 0.5))
        lt = radial_light(256, C.mix(self.cf, WHITE, 0.4), 1.0, 1.4).resize((r * 2, r * 2), Image.BILINEAR)
        add(fr, lt, W / 2 - r, 608 - r, 0.9 * (1 - dt / 0.9) ** 2)

    # ── кадр ──
    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        col = self.scene_col(t)
        bp = self.beat_pulse(t)
        fi = int(round(t * C.FPS))
        on = C.out_cubic(C.seg(t, 0.0, 0.45))
        cta = C.seg(t, self.t_cta, self.t_cta + 0.4)
        flick = 1 - 0.08 * noise(fi, 1)
        if self.tp <= t < D:
            flick = 0.65 + 0.45 * noise(fi, 2)
        ck = on * flick * (0.85 + 0.35 * bp) * (1 - 0.65 * cta)
        if t >= D:
            ck *= 1 + 0.6 * math.exp(-(t - D) / 0.3)
        # конус: при включении растёт снизу вверх
        self.draw_cone(fr, t, col, ck)
        if on < 1:
            cut = int(TOP_Y + (APEX_Y - TOP_Y) * (1 - on))
            fr.paste(self.bg.crop((0, 0, W, cut)), (0, 0))
        self.draw_disc(fr, t, col, min(1.0, C.seg(t, 0, 0.25) * 1.0), bp)
        # импульс проектора на долях
        nb = int((t - D) // u)
        for k in (nb, nb - 1):
            tb = D + k * u
            if 0 <= tb <= t and not (self.tp <= tb < D):
                self.floor_ring(fr, t, tb, col, 0.7, 0.8)
        if t < self.t1 + 0.6:
            self.intro(fr, t)
        if self.t1 <= t < self.t2 + 0.6:
            self.team(fr, t, 'h', self.t1, self.t2)
        if self.t2 <= t < self.tp + 0.6:
            self.team(fr, t, 'a', self.t2, self.tp)
        if self.tp <= t < D:
            self.interference(fr, t)
        if t >= D:
            self.burst(fr, t)
            self.pick(fr, t)
        C.put(fr, self.tag, W / 2, TAG_Y, C.seg(t, 0, 0.3) * 0.95)
        ha = C.seg(t, 0.2, 0.5) * (1 - cta)
        C.put(fr, self.handle_im, W / 2, HY, 0.92 * ha)
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.05, self.t_cta + 0.5))
            C.put(fr, self.tg, W / 2, 1172 + 60 * (1 - q), q)
        # камера и вспышки
        z, dx, dy = 1.0, 0.0, 0.0
        for th in (self.t1, self.t2, self.tp):
            if t >= th:
                z += 0.025 * (1 - C.seg(t, th, th + 0.3)) ** 2
            sx, sy = C.shake(t, th, 6, 0.22)
            dx, dy = dx + sx, dy + sy
        if self.tp <= t < D:
            qq = C.seg(t, self.tp, D)
            z += 0.045 * C.in_cubic(qq)
            dx += 5 * qq * math.sin(t * 71)
        if t >= D:
            z += 0.05 * (1 - C.seg(t, D, D + 0.45)) ** 2
            sx, sy = C.shake(t, D, 16, 0.4)
            dx, dy = dx + sx, dy + sy
        if z > 1.001 or abs(dx) + abs(dy) > 0.5:
            fr = C.zoom(fr.convert('RGB'), z, W / 2, 900, dx, dy)
        else:
            fr = fr.convert('RGB')
        split = 0
        for th in (self.t1, self.t2, self.tp):
            if 0 <= t - th < 0.15:
                split = max(split, 8 * (1 - (t - th) / 0.15))
        if self.tp <= t < D:
            split = max(split, 3 + 5 * noise(fi, 4))
        if 0 <= t - D < 0.25:
            split = max(split, 12 * (1 - (t - D) / 0.25))
        if split >= 1:
            fr = C.rgb_split(fr, split)
        if 0 <= t - D < 0.35:
            fr = Image.blend(fr, Image.new('RGB', fr.size, C.mix(self.cf, WHITE, 0.75)), 0.85 * (1 - (t - D) / 0.35) ** 2)
        for th in (self.t1, self.t2):
            if 0 <= t - th < 0.14:
                fr = Image.blend(fr, Image.new('RGB', fr.size, C.mix(self.col['h' if th == self.t1 else 'a'], WHITE, 0.5)),
                                 0.28 * (1 - (t - th) / 0.14))
        return fr


def tint_text(im, col):
    """Белый текст → градиент от светлого к цвету снизу (голографический)."""
    h = im.height
    g = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    top = np.array(C.mix(col, WHITE, 0.75), np.float32)
    bot = np.array(C.mix(col, WHITE, 0.15), np.float32)
    a = np.asarray(im, np.float32)
    rgb = top * (1 - g) + bot * g
    rgb = np.broadcast_to(rgb, a[..., :3].shape)
    return Image.fromarray(np.concatenate([rgb, a[..., 3:4]], -1).astype(np.uint8), 'RGBA')
