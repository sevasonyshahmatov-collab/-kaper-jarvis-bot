# -*- coding: utf-8 -*-
"""«Приборка» — ночная приборная панель дорогого автомобиля (трек «TRUCK», поздний участок после брейка):
два больших хромированных круглых прибора со светящимися стрелками, между ними и под ними — цифровой дисплей,
внизу — малые приборы (топливо, температура) и одометр. Подсветка шкал — в цвете клуба, который сейчас на экране.
Не табло арены (это led.py) и не терминал (jarvis.py) — именно приборка: стрелки, шкалы, барабаны одометра,
поворотники мигают в долю трека.

Сцены (u — доля трека, D — дроп; доли считаются от дропа, team / pre / hold / cta / hit — параметры из
reels_cfg/dashboard.json):
  интро (до D − (2·team + pre) долей) — «зажигание»: панель загорается на долю, стрелки проходят самотест
                 (до упора и обратно); в больших приборах — эмблемы хозяев и гостей с названиями, «ХОЗЯЕВА / ГОСТИ»;
                 на дисплее — лига, день и время МСК и линия основного времени П1 · Х · П2 тремя крупными
                 цифровыми плашками; в окне одометра — часы с временем начала (МСК);
  команда (team долей) ×2 — подсветка гаснет и загорается в цвете клуба (склейка ровно на долю/полдоли);
                 на дисплее: эмблема, название, «ХОЗЯЕВА» / «ГОСТИ», место; на доли ½, 1, 1½ — бортжурнал
                 последних 3 игр (дата, соперник, счёт, ОТ/Б, В/П цветом); на долю 2 спидометр «ОЧКИ» (шкала до
                 максимума очков за сыгранные матчи) — стрелка взлетает с перелётом, цифра считается; на 2½ —
                 тахометр «ЗАБИВАЕТ» (шайбы за матч, красная зона с 5); на 3 — одометр докручивает барабаны до
                 разницы шайб; на 3½ — «топливо» = большинство, на 4 —
                 «температура» = меньшинство; за полдоли до конца сцены стрелки падают в ноль;
                 поворотник мигает в долю (хозяева — левый, гости — правый);
  перегазовка (pre долей) — нейтральная подсветка, стрелки отскакивают к красной зоне на каждой половине доли,
                 на дисплее обе эмблемы и шкала переключения передач заполняется; в паузе трека перед дропом
                 подсветка гаснет, мигает только красная шкала;
  ДРОП (hold долей) — ровно на дропе (удар трека; hit — сдвиг удара относительно разметки трека) «старт»:
                 вспышка, рывок камеры, лучи скорости; дисплей разворачивается на всю панель: только команда
                 прогноза (одна эмблема, без «VS») в цифровом кольце тахометра, «ПОБЕДА …», «В ОСНОВНОЕ ВРЕМЯ»
                 и кэф крупно; на каждую долю — пульс кольца;
  финал (cta долей) — дисплей поджимается вверх, снизу плашка Telegram (C.tg_plate, текст по центру плашки).
@jarvibet — у низа безопасной зоны (y 1456), одинаково во всех сценах до плашки Telegram.
Пустые (None) поля статистики не показываются (прибор остаётся без стрелки и цифры).
Кадр зависит только от t; корпус, хром, шкалы клубов и дисплейные блоки считаются один раз (кеш модуля, до fork).
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
GRAY = (156, 166, 180)
LABEL = (206, 214, 226)
INK = (8, 10, 14)
NEUT = (140, 200, 255)            # нейтральная подсветка (зажигание, перегазовка)
NEEDLE = (255, 86, 34)
REDZ = (240, 44, 32)
AMBER = (255, 178, 36)
GREEN = (60, 226, 104)

TAG_Y, HY = 270, 1456
RG, RIM = 224, 22                 # большой прибор: шкала и ширина хромового кольца
PADG = RIM + 46                   # поле слоя прибора (ореол)
GL, GR_ = (282.0, 558.0), (798.0, 558.0)
DISP = (46, 830, 1034, 1248)      # дисплей (x0, y0, x1, y1)
BIGP = (40, 296, 1040, 1414)      # дисплей на прогнозе
CTAP = (40, 296, 1040, 1248)      # дисплей на финале
RS, RIMS = 58, 9                  # малые приборы
SL, SR_ = (128.0, 1342.0), (952.0, 1342.0)
ODO_C = (540.0, 1348.0)
ODO_W, ODO_H, CELL_W = 264, 92, 58
A0, A1 = -135.0, 135.0            # дуга больших шкал (° от верха по часовой)
S0, S1 = -112.0, 112.0            # дуга малых шкал
_ST, _SPR, _TX = {}, {}, {}


# ─────────────────────────────── мелочи ───────────────────────────────
def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def neon(c, v_min=0.92, s_min=0.62):
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    s = min(0.9, max(s, s_min)) if s > 0.12 else s
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


def num(v):
    try:
        return None if v is None or isinstance(v, bool) else float(v)
    except (TypeError, ValueError):
        return None


def dec(v, nd=1):
    """3.0 → «3,0»; 9.4 → «9,4»; 75.0 → «75» (проценты без лишнего нуля)."""
    s = ('%.' + str(nd) + 'f') % v
    if nd and s.endswith('.0') and abs(v) >= 10:
        s = s[:-2]
    return s.replace('.', ',')


def pol(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def glow_txt(s, fnt, size, col, wght=800, r=12, k=0.7, gcol=None, **kw):
    key = (s, fnt, size, col, wght, r, k, gcol, tuple(sorted(kw.items())))
    if key not in _TX:
        _TX[key] = C.glow(C.text(s, fnt, size, col, wght, **kw), r, k, gcol or col)
    return _TX[key]


def _rgba(arr_rgb, alpha):
    a = np.concatenate([np.clip(arr_rgb, 0, 255), np.clip(alpha, 0, 255)[..., None]], -1)
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


def _grid(S):
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    c = S / 2.0
    dx, dy = xx - c + 0.5, yy - c + 0.5
    return dx, dy, np.hypot(dx, dy)


# ─────────────────────────────── хром, циферблаты, стрелки ───────────────────────────────
def chrome(rin, rout, S):
    """Хромированное кольцо rin..rout в квадрате S: свет сверху-слева, скруглённый профиль, блик."""
    key = ('chrome', rin, rout, S)
    if key in _SPR:
        return _SPR[key]
    dx, dy, r = _grid(S)
    th = np.arctan2(dy, dx)
    q = np.clip((r - rin) / (rout - rin), 0, 1)
    prof = 0.5 + 0.5 * np.sin(np.pi * q)
    li = np.cos(th + 2.36)
    v = (0.42 + 0.3 * li + 0.12 * np.cos(3 * th + 0.4)) * prof
    spec = 0.55 * np.exp(-((q - 0.38) / 0.1) ** 2) * np.clip(li, 0, 1) ** 3
    v = np.clip(v + spec, 0, 1.15)
    rgb = np.stack([v * 222 + 16, v * 226 + 17, v * 236 + 20], -1)
    lip = np.exp(-((r - rin - 1.5) / 1.6) ** 2)                 # тёмная кромка внутри кольца
    rgb = rgb * (1 - 0.7 * lip[..., None])
    al = np.clip(r - rin + 0.5, 0, 1) * np.clip(rout - r + 0.5, 0, 1) * 255
    _SPR[key] = _rgba(rgb, al)
    return _SPR[key]


def face_dark(R, S):
    """Чёрный циферблат (без подсветки): радиальный градиент и тонкая концентрическая шлифовка."""
    key = ('face', R, S)
    if key in _SPR:
        return _SPR[key]
    dx, dy, r = _grid(S)
    q = np.clip(r / R, 0, 1)
    v = 21 - 13 * q ** 1.6 + 1.6 * np.sin(r * 1.9) * (1 - q * 0.5)
    rgb = np.stack([v, v * 1.06, v * 1.22], -1)
    al = np.clip(R - r + 0.5, 0, 1) * 255
    _SPR[key] = _rgba(rgb, al)
    return _SPR[key]


def well(R, S):
    """Утопленный колодец под прибор: мягкая тень вокруг хрома."""
    key = ('well', R, S)
    if key in _SPR:
        return _SPR[key]
    dx, dy, r = _grid(S)
    al = np.clip(1 - (r - R) / 34, 0, 1) ** 1.8 * 200 * (r > R - 4)
    dyk = np.clip((dy / R), -1, 1)
    rgb = np.zeros(r.shape + (3,), np.float32)
    al = al * (0.75 + 0.25 * dyk)
    _SPR[key] = _rgba(rgb, al)
    return _SPR[key]


def needle(L, tail, w0, col=NEEDLE):
    """Стрелка вверх от центра квадратного слоя (ось — центр), со свечением; поворот — C.rotate."""
    key = ('needle', L, tail, w0, col)
    if key in _SPR:
        return _SPR[key]
    ss = 4
    S = 2 * (L + 6)
    im = Image.new('RGBA', (S * ss, S * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S * ss / 2
    w1 = max(1.6, w0 * 0.28)
    body = [(c - w0 * ss, c), (c - w1 * ss, c - L * ss), (c + w1 * ss, c - L * ss), (c + w0 * ss, c),
            (c + w0 * 1.1 * ss, c + tail * ss), (c - w0 * 1.1 * ss, c + tail * ss)]
    d.polygon(body, fill=tuple(col) + (255,))
    core = [(c - w0 * 0.32 * ss, c - 4 * ss), (c - w1 * 0.4 * ss, c - (L - 3) * ss), (c + w1 * 0.4 * ss, c - (L - 3) * ss),
            (c + w0 * 0.32 * ss, c - 4 * ss)]
    d.polygon(core, fill=C.mix(col, WHITE, 0.72) + (255,))
    im = im.resize((S, S), Image.LANCZOS)
    _SPR[key] = C.glow(im, max(4, L // 22), 1.25, col)
    return _SPR[key]


def hub(r):
    key = ('hub', r)
    if key in _SPR:
        return _SPR[key]
    S = 2 * r + 24
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    C.put(im, C.shadow(C.ellipse(2 * r, 2 * r, (0, 0, 0)), 5, 0.7), S / 2, S / 2 + 3)
    ch = chrome(0, r, 2 * r + 2)
    C.put(im, ch, S / 2, S / 2)
    C.put(im, C.ellipse(int(r * 0.9), int(r * 0.9), (24, 26, 30)), S / 2, S / 2)
    C.put(im, C.ellipse(int(r * 0.34), int(r * 0.34), C.mix(NEEDLE, WHITE, 0.3)), S / 2, S / 2)
    _SPR[key] = im
    return im


def arrow(on, flip=False):
    """Стрелка поворотника (вкл/выкл)."""
    key = ('arrow', on, flip)
    if key in _SPR:
        return _SPR[key]
    w, h = 58, 50
    pts = [(0, h / 2), (w * 0.48, 0), (w * 0.48, h * 0.27), (w, h * 0.27), (w, h * 0.73), (w * 0.48, h * 0.73), (w * 0.48, h)]
    im = C.polygon(pts, (w, h), GREEN if on else (30, 44, 34))
    if on:
        im = C.glow(im, 12, 1.3, GREEN)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    _SPR[key] = im
    return im


def ticks_layer(R, S, spec, col, a0=A0, a1=A1, major_w=7, minor_w=3, nums=True, num_size=44):
    """Подсветка шкалы: ореол, риски, красная зона, цифры. spec = (vmin, vmax, step, minor, red_from | None)."""
    vmin, vmax, step, minor, red = spec
    c = S / 2.0
    dx, dy, r = _grid(S)
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    halo = 0.36 * np.exp(-((r - 0.9 * R) / (0.075 * R)) ** 2) + 0.1 * np.clip(1 - r / R, 0, 1) ** 2
    halo *= (r < R)
    lay = np.zeros((S, S, 4), np.float32)
    lay[..., :3] = col
    lay[..., 3] = halo * 255
    out.alpha_composite(Image.fromarray(lay.astype(np.uint8), 'RGBA'))
    ss = 3
    mk = Image.new('L', (S * ss, S * ss), 0)
    rz = Image.new('L', (S * ss, S * ss), 0)
    d, dr = ImageDraw.Draw(mk), ImageDraw.Draw(rz)

    def ang(v):
        return a0 + (a1 - a0) * (v - vmin) / (vmax - vmin)

    def seg_(dd, deg, r0, r1, wdt, fill=255):
        x0, y0 = pol(c * ss, c * ss, r0 * ss, deg)
        x1, y1 = pol(c * ss, c * ss, r1 * ss, deg)
        dd.line((x0, y0, x1, y1), fill=fill, width=int(wdt * ss))

    nmin = int(round((vmax - vmin) / minor))
    for i in range(nmin + 1):
        v = vmin + i * minor
        is_major = abs((v - vmin) / step - round((v - vmin) / step)) < 1e-6
        if is_major:
            seg_(d, ang(v), 0.8 * R, 0.965 * R, major_w)
        else:
            seg_(d, ang(v), 0.885 * R, 0.965 * R, minor_w)
    bb = (c * ss - 0.975 * R * ss, c * ss - 0.975 * R * ss, c * ss + 0.975 * R * ss, c * ss + 0.975 * R * ss)
    d.arc(bb, a0 - 90, a1 - 90, fill=200, width=int(2.5 * ss))
    if red is not None:
        rb = (c * ss - 0.93 * R * ss, c * ss - 0.93 * R * ss, c * ss + 0.93 * R * ss, c * ss + 0.93 * R * ss)
        dr.arc(rb, ang(red) - 90, a1 - 90, fill=255, width=int(0.07 * R * ss))
    mk = mk.resize((S, S), Image.LANCZOS)
    rz = rz.resize((S, S), Image.LANCZOS)
    for m, cl, gk in ((mk, col, 1.5), (rz, REDZ, 1.6)):
        g = Image.new('RGBA', (S, S), tuple(cl) + (0,))
        g.putalpha(m.filter(ImageFilter.GaussianBlur(max(3, R // 30))).point(lambda v, gk=gk: min(255, int(v * gk))))
        out.alpha_composite(g)
    t_on = Image.new('RGBA', (S, S), C.mix(col, WHITE, 0.82) + (0,))
    t_on.putalpha(mk)
    out.alpha_composite(t_on)
    r_on = Image.new('RGBA', (S, S), REDZ + (0,))
    r_on.putalpha(rz.point(lambda v: int(v * 0.95)))
    out.alpha_composite(r_on)
    if nums:
        v = vmin
        while v <= vmax + 1e-6:
            s = ('%d' % round(v)) if abs(v - round(v)) < 1e-6 else dec(v)
            red_n = red is not None and v >= red - 1e-6
            im = C.text(s, 'exo', num_size, (255, 120, 104) if red_n else (238, 242, 250), 800)
            x, y = pol(c, c, 0.665 * R, ang(v))
            C.put(out, im, x, y)
            v += step
    return out


def nice_scale(vmax):
    for st in (1, 2, 5, 10, 20, 50):
        if vmax / st <= 8:
            return st, int(math.ceil(vmax / st)) * st
    return 100, int(math.ceil(vmax / 100)) * 100


def icon(kind, col, size=34):
    """Значки малых приборов: топливо (колонка) и температура (термометр)."""
    key = ('icon', kind, col, size)
    if key in _SPR:
        return _SPR[key]
    ss = 4
    S = size * ss
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = tuple(col) + (255,)
    k = S / 34.0
    if kind == 'fuel':
        d.rounded_rectangle((4 * k, 4 * k, 20 * k, 31 * k), radius=2 * k, fill=f)
        d.rectangle((7 * k, 7 * k, 17 * k, 14 * k), fill=(0, 0, 0, 0))
        d.line((20 * k, 11 * k, 26 * k, 15 * k, 26 * k, 26 * k, 29 * k, 26 * k, 29 * k, 9 * k), fill=f, width=int(2.4 * k))
        d.rectangle((2 * k, 29 * k, 22 * k, 32 * k), fill=f)
    else:
        d.rounded_rectangle((14 * k, 2 * k, 20 * k, 24 * k), radius=3 * k, fill=f)
        d.ellipse((10 * k, 20 * k, 24 * k, 33 * k), fill=f)
        for yy in (7, 12, 17):
            d.line((21 * k, yy * k, 28 * k, yy * k), fill=f, width=int(2.2 * k))
        d.line((4 * k, 30 * k, 9 * k, 28 * k), fill=f, width=int(2 * k))
        d.line((25 * k, 28 * k, 31 * k, 30 * k), fill=f, width=int(2 * k))
    im = im.resize((size, size), Image.LANCZOS)
    _SPR[key] = im
    return im


# ─────────────────────────────── ролик ───────────────────────────────
class Dashboard(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 65, drop=18 * 60 / 65, line=None, team=6.5,
                 pre=1.5, hold=4.5, cta=2.5, hit=0.0, seed=41, **kw):
        """Сцены: интро → команда (team долей) ×2 → перегазовка (pre) → прогноз (hold) → Telegram (cta).
        hit — сдвиг удара трека относительно его разметки (с): дроп ролика = drop + hit."""
        super().__init__(u, drop + hit, seed)
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
        if self.t1 < 2.0:
            raise ValueError('мало времени до дропа')
        self.t_cta = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = round((self.t1 - 0.55) * 30) / 30
        self.ign = self.b(-int(math.floor(self.drop / self.u + 1e-6)))   # первая доля ролика — «зажигание»
        if self.ign < -1e-6:
            self.ign += self.u
        self._prep()

    # ── заготовки ──
    def _prep(self):
        self.col = {'h': club(self.h)}
        self.col['a'] = club(self.a, avoid=self.col['h'])
        self.col['neu'] = NEUT
        self.cf = self.col[self.side]
        self.T = {k: self._team_data(k) for k in ('h', 'a')}
        m = re.search(r'(\d{1,2}):(\d{2})', self.when or '')
        self.clock = (int(m.group(1)), int(m.group(2))) if m else None
        self.clock_lab = C.text('МСК', 'robc', 28, C.mix(NEUT, WHITE, 0.3), 800, track=0.3)
        key = (self.h.name, self.a.name, self.when, repr(self.line), repr(sorted(self.raw['h'].items())),
               repr(sorted(self.raw['a'].items())))
        if key not in _ST:
            dark = self._dark_frame()
            lit = {m: self._lit_frame(dark, m) for m in ('neu', 'h', 'a')}
            _ST[key] = (dark, lit)
        self.dark, self.lit = _ST[key]
        self.tag = C.text(F.tag(self.league), 'exo', 34, (196, 206, 220), 700, track=0.14)
        self.handle_im = C.text(C.HANDLE, 'exo', 44, (226, 234, 244), 700)
        self.tg = C.tg_plate(960, 172, font='exo')
        self.nd_big = needle(int(RG * 0.86), int(RG * 0.17), 8)
        self.nd_small = needle(int(RS * 0.84), int(RS * 0.2), 4)
        self.hub_big, self.hub_small = hub(25), hub(11)
        self.glare = self._glare(RG + RIM)
        # интро
        self.i_emb = {s: C.glow(t.emb(172), 16, 0.6, NEUT) for s, t in (('h', self.h), ('a', self.a))}
        self.i_role = {s: C.text(r, 'robc', 30, C.mix(NEUT, WHITE, 0.35), 800, track=0.2) for s, r in (('h', 'ХОЗЯЕВА'), ('a', 'ГОСТИ'))}
        self.i_name = {s: C.text(t.up, 'exo', 50, WHITE, 800, max_w=250) for s, t in (('h', self.h), ('a', self.a))}
        self.i_date = C.text('%s · %s' % (F.lg_ru(self.league), self.when), 'exo', 44, WHITE, 700, max_w=920)
        self.i_lab = C.text('ОСНОВНОЕ ВРЕМЯ', 'robc', 30, C.mix(NEUT, WHITE, 0.3), 700, track=0.26)
        self.plates = [self._odds_plate(lab, v) for lab, v in zip(('П1', 'Х', 'П2'), self.line)] if self.line else []
        # перегазовка
        self.r_emb = {s: C.glow(t.emb(150), 14, 0.6, NEUT) for s, t in (('h', self.h), ('a', self.a))}
        self.r_name = {s: C.text(t.up, 'exo', 44, WHITE, 800, max_w=380) for s, t in (('h', self.h), ('a', self.a))}
        self.leds = self._leds()
        # прогноз
        cf = self.cf
        self.p_emb = C.glow(self.fav.emb(300), 22, 0.75, cf)
        l1, l2 = F.head_main(self.pick1)                     # «ИНДИВИДУАЛЬНЫЙ ТОТАЛ …» сверху, «МЕНЬШЕ 2,5» крупно (19.10)
        self.p_l1 = C.text(l1, 'exo', 66, WHITE, 800, track=0.12 if len(l1) < 12 else 0.04, max_w=900) if l1 else None
        self.p_l2 = glow_txt(l2, 'exoi', 134, cf, 900, 16, 0.7, max_w=900)
        self.p_l3 = C.text(self.pick2, 'robc', 46, (218, 228, 238), 700, track=0.16, max_w=900) if self.pick2 else None
        self.kef = self._kef() if self.coef else None
        self.ring_off, self.ring_on, self.ring_th = self._launch_ring(250, 210, cf)
        self.panel_big = self._panel(BIGP[2] - BIGP[0], BIGP[3] - BIGP[1], cf)
        self.streaks = self._streaks()

    def _team_data(self, k):
        tm = self.h if k == 'h' else self.a
        col = self.col[k]
        s, rec = self.st[k], self.raw[k]
        pts, gp = s['points'], s['gp']
        if pts is not None:
            vmax = 2 * gp if gp else max(4, pts * 1.5)
            vmax = max(vmax, pts, 2)
            st, vmax = nice_scale(vmax)
            spd = dict(spec=(0, vmax, st, st / 2 if st > 1 else 0.5, None), val=float(pts), unit='ОЧКИ',
                       sub=('ЗА %d %s' % (gp, plural(gp, 'МАТЧ', 'МАТЧА', 'МАТЧЕЙ'))) if gp else '', fmt='int')
        else:
            spd = dict(spec=(0, 8, 1, 0.5, None), val=None, unit='ОЧКИ', sub='', fmt='int')
        gf = num(rec.get('gf_pg'))
        if gf is None and num(rec.get('gf')) is not None and gp:
            gf = num(rec.get('gf')) / gp
        tach = dict(spec=(0, 6, 1, 0.5, 5), val=gf, unit='ЗАБИВАЕТ', sub='ШАЙБЫ ЗА МАТЧ' if gf is not None else '', fmt='dec')
        pp, pk = num(rec.get('pp')), num(rec.get('pk'))
        place = ''
        if s['place'] is not None:
            place = ('%d МЕСТО %s' % (s['place'], s['place_scope'].upper())).strip()
        lines = [self._trip_line(g, col) for g in s['games'][:3]]
        return dict(tm=tm, col=col, spd=spd, tach=tach, pp=pp, pk=pk, gd=s['gd'],
                    head=self._header(tm, col, 'ХОЗЯЕВА' if k == 'h' else 'ГОСТИ', place), lines=lines,
                    div=C.rrect(928, 3, 1, col, 120))

    # кадры-основы: корпус без подсветки и с подсветкой режима
    def _dark_frame(self):
        bg = C.vgrad(W, H, [(0, (14, 15, 18)), (0.5, (8, 9, 11)), (1, (3, 3, 4))]).convert('RGBA')
        yy, xx = np.mgrid[0:H, 0:W]
        weave = (((xx // 7) + (yy // 7)) % 2).astype(np.float32) * 2.5 + (((xx + yy) // 3) % 2) * 1.2
        arr = np.asarray(bg, np.float32).copy()
        arr[..., :3] += weave[..., None]
        bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
        # кожух приборки
        bx0, by0, bx1, by1 = 14, 232, 1066, 1426
        hood = C.vgrad(bx1 - bx0, by1 - by0, [(0, (30, 32, 37)), (0.12, (21, 23, 27)), (1, (11, 12, 14))]).convert('RGBA')
        hood.putalpha(C.rrect(bx1 - bx0, by1 - by0, 58, WHITE).getchannel('A'))
        C.put(bg, C.shadow(hood, 26, 0.85), (bx0 + bx1) / 2, (by0 + by1) / 2 + 14)
        C.put(bg, hood, bx0, by0, anchor='tl')
        edge = C.rrect(bx1 - bx0, by1 - by0, 58, None, outline=(74, 78, 86), width=2)
        C.put(bg, edge, bx0, by0, anchor='tl')
        d = ImageDraw.Draw(bg)
        for x in range(96, 986, 22):                                  # строчка по коже кожуха
            d.line((x, 247, x + 12, 247), fill=(86, 82, 76, 255), width=2)
        # большие приборы
        Sg = 2 * (RG + PADG)
        for cx, cy in (GL, GR_):
            C.put(bg, well(RG + RIM, Sg), cx, cy + 6)
            C.put(bg, face_dark(RG, Sg), cx, cy)
            C.put(bg, chrome(RG, RG + RIM, Sg), cx, cy)
        # малые приборы
        Ss = 2 * (RS + 40)
        for cx, cy in (SL, SR_):
            C.put(bg, well(RS + RIMS, Ss), cx, cy + 4)
            C.put(bg, face_dark(RS, Ss), cx, cy)
            C.put(bg, chrome(RS, RS + RIMS, Ss), cx, cy)
        # окно одометра
        win = C.rrect(ODO_W + 16, ODO_H + 16, 16, (120, 124, 132))
        C.put(win, C.rrect(ODO_W + 6, ODO_H + 6, 12, (10, 10, 12)), win.width / 2, win.height / 2)
        C.put(bg, win, ODO_C[0], ODO_C[1])
        # дисплей
        C.put(bg, self._panel(DISP[2] - DISP[0], DISP[3] - DISP[1], None), (DISP[0] + DISP[2]) / 2, (DISP[1] + DISP[3]) / 2)
        return bg

    def _panel(self, w, h, col):
        key = ('panel', int(w), int(h), col)
        if key in _SPR:
            return _SPR[key]
        w, h = int(w), int(h)
        bez = C.rrect(w + 14, h + 14, 38, (104, 108, 116))
        inner = C.rrect(w + 8, h + 8, 35, (30, 32, 36))
        C.put(bez, inner, bez.width / 2, bez.height / 2)
        glass = C.vgrad(w, h, [(0, (16, 18, 24)), (0.5, (9, 10, 14)), (1, (5, 6, 8))]).convert('RGBA')
        if col is not None:
            tint = C.vgrad(w, h, [(0, C.mix(col, (0, 0, 0), 0.82)), (0.35, (8, 9, 12)), (1, (5, 6, 8))]).convert('RGBA')
            glass = Image.blend(glass, tint, 0.8)
        mask = C.rrect(w, h, 32, WHITE).getchannel('A')
        glass.putalpha(mask)
        sheen = C.lgrad(w, h, (255, 255, 255), (255, 255, 255), 60, 14, 0)          # отражение стекла
        sh_m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(sh_m).polygon([(0, 0), (w * 0.55, 0), (w * 0.25, h), (0, h)], fill=255)
        sheen.putalpha(Image.fromarray((np.asarray(sheen.getchannel('A'), np.float32) * np.asarray(sh_m, np.float32) / 255
                                        * np.asarray(mask, np.float32) / 255).astype(np.uint8), 'L'))
        glass.alpha_composite(sheen)
        C.put(bez, glass, bez.width / 2, bez.height / 2)
        _SPR[key] = bez
        return bez

    def _lit_frame(self, dark, mode):
        fr = dark.copy()
        col = self.col[mode]
        Sg = 2 * (RG + PADG)
        Ss = 2 * (RS + 40)
        if mode == 'neu':
            specs = [((0, 8, 1, 0.5, 6.5), None, None, False), ((0, 8, 1, 0.5, 6.5), None, None, False)]
        else:
            T = self.T[mode]
            specs = [(T['spd']['spec'], T['spd']['unit'] if T['spd']['val'] is not None else None, T['spd']['sub'], True),
                     (T['tach']['spec'], T['tach']['unit'] if T['tach']['val'] is not None else None, T['tach']['sub'], True)]
        for (cx, cy), (spec, unit, sub, nums) in zip((GL, GR_), specs):
            lay = ticks_layer(RG, Sg, spec, col, nums=nums)
            c = Sg / 2
            if unit:
                C.put(lay, C.text(unit, 'robc', 32, LABEL, 800, track=0.16), c, c - 0.37 * RG)
            if sub:
                C.put(lay, C.text(sub, 'robc', 30, GRAY, 700, track=0.06, max_w=250), c, c + 0.72 * RG)
            C.put(fr, lay, cx, cy)
        for (cx, cy), red in ((SL, 0.0), (SR_, 0.82)):
            sp = (0, 1, 0.25, 0.125, None)
            lay = ticks_layer(RS, Ss, sp, col, S0, S1, major_w=4, minor_w=2, nums=False)
            c = Ss / 2
            m = Image.new('L', (Ss * 3, Ss * 3), 0)                       # красный край шкалы (пусто / перегрев)
            dd = ImageDraw.Draw(m)
            rr = 0.93 * RS * 3
            if red == 0.0:
                aa, bb = S0, S0 + (S1 - S0) * 0.16
            else:
                aa, bb = S0 + (S1 - S0) * red, S1
            dd.arc((c * 3 - rr, c * 3 - rr, c * 3 + rr, c * 3 + rr), aa - 90, bb - 90, fill=255, width=int(0.12 * RS * 3))
            m = m.resize((Ss, Ss), Image.LANCZOS)
            rl = Image.new('RGBA', (Ss, Ss), REDZ + (0,))
            rl.putalpha(m)
            lay.alpha_composite(rl)
            C.put(lay, icon('fuel' if red == 0.0 else 'temp', C.mix(col, WHITE, 0.7), 30), c, c + 0.5 * RS)
            C.put(fr, lay, cx, cy)
        # подписи малых приборов и одометра
        if mode == 'neu':
            if self.clock:
                C.put(fr, self.clock_lab, ODO_C[0], ODO_C[1] - ODO_H / 2 - 30)
        else:
            T = self.T[mode]
            if T['pp'] is not None:
                C.put(fr, C.text('БОЛЬШИНСТВО', 'robc', 27, LABEL, 800, track=0.06, max_w=176), 290, 1298)
            if T['pk'] is not None:
                C.put(fr, C.text('МЕНЬШИНСТВО', 'robc', 27, LABEL, 800, track=0.06, max_w=176), W - 290, 1298)
            if T['gd'] is not None:
                C.put(fr, C.text('РАЗНИЦА ШАЙБ', 'robc', 27, LABEL, 800, track=0.16), ODO_C[0], ODO_C[1] - ODO_H / 2 - 30)
        # подсветка дисплея: тонкая кромка в цвете режима
        w, h = DISP[2] - DISP[0], DISP[3] - DISP[1]
        ed = C.rrect(w - 4, h - 4, 31, None, outline=col, width=2)
        ed = C.glow(ed, 8, 0.8, col)
        C.put(fr, ed, (DISP[0] + DISP[2]) / 2, (DISP[1] + DISP[3]) / 2, 0.55)
        return fr

    def _glare(self, R):
        key = ('glare', R)
        if key in _SPR:
            return _SPR[key]
        S = 2 * R
        dx, dy, r = _grid(S)
        k = np.clip((dx * -0.6 + dy * -0.8) / R, 0, 1) ** 1.6 * 26 * (r < R - 2)
        band = np.exp(-(((dx + dy) / R + 0.55) / 0.08) ** 2) * 18 * (r < R - 2)
        al = k + band
        rgb = np.full((S, S, 3), 255, np.float32)
        _SPR[key] = _rgba(rgb, al)
        return _SPR[key]

    def _odds_plate(self, lab, v):
        w, h = 292, 206
        pl = C.rrect(w, h, 24, (11, 13, 18), outline=C.mix(NEUT, INK, 0.45), width=3)
        C.put(pl, C.text(lab, 'exo', 42, NEUT, 800, track=0.08), w / 2, 48)
        C.put(pl, glow_txt(C.fmt_k(v), 'exo', 104, WHITE, 800, 10, 0.35, NEUT, max_w=w - 30), w / 2, 136)
        return pl

    def _header(self, tm, col, role, place):
        w, h = 940, 130
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        C.put(im, C.glow(tm.emb(112), 10, 0.5, col), 62, 64)
        rt = C.text(role, 'robc', 30, INK, 800, track=0.18)
        pill = C.rrect(rt.width + 44, 52, 26, col)
        C.put(pill, rt, pill.width / 2, 26)
        C.put(im, pill, w - pill.width / 2 - 4, 46)
        nm = C.text(tm.up, 'exo', 66, WHITE, 800, max_w=w - 140 - pill.width - 30)
        C.put(im, nm, 136, 46 - nm.height / 2, anchor='tl')
        if place:
            pt = C.text(place, 'robc', 33, GRAY, 700, track=0.05, max_w=w - 150)
            C.put(im, pt, 138, 104 - pt.height / 2, anchor='tl')
        return im

    def _trip_line(self, g, col):
        w, h = 928, 70
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        if g['date']:
            dt = C.text(g['date'], 'robc', 31, GRAY, 700)
            C.put(im, dt, 0, h / 2 - dt.height / 2, anchor='tl')
        opp = C.text(g['opp'].upper(), 'exo', 46, WHITE, 700, max_w=400)
        C.put(im, opp, 104, h / 2 - opp.height / 2, anchor='tl')
        sc = C.text(g['score'], 'exo', 56, WHITE, 800)
        C.put(im, sc, 640, h / 2)
        if g['note']:
            nt = C.text(g['note'], 'robc', 32, GRAY, 700)
            C.put(im, nt, 640 + sc.width / 2 + 12, h / 2 + sc.height / 2 - nt.height, anchor='tl')
        C.put(im, F.chip(g['res'], 58), w - 30, h / 2)
        return im

    def _leds(self):
        n, d = 15, 42
        out = []
        for i in range(n):
            cl = GREEN if i < 5 else AMBER if i < 10 else REDZ
            on = C.glow(C.ellipse(d, d, C.mix(cl, WHITE, 0.25)), 10, 1.2, cl)
            off = C.ellipse(d, d, (34, 36, 40))
            out.append((on, off))
        return out

    def _kef(self):
        lab = C.text('КЭФ', 'robc', 46, GRAY, 800, track=0.18)
        val = C.text(C.fmt_k(self.coef), 'exo', 112, WHITE, 800)
        w = lab.width + val.width + 140
        pl = C.rrect(w, 156, 32, (10, 12, 16), outline=self.cf, width=4)
        x = (w - lab.width - 26 - val.width) / 2
        C.put(pl, lab, x, 78 - lab.height / 2 + 6, anchor='tl')
        C.put(pl, val, x + lab.width + 26, 78 - val.height / 2, anchor='tl')
        return C.glow(pl, 16, 0.75, self.cf)

    def _launch_ring(self, r_out, r_in, col):
        S = 2 * r_out + 80
        ss = 3
        on = Image.new('L', (S * ss, S * ss), 0)
        d = ImageDraw.Draw(on)
        c = S * ss / 2
        n = 40
        for i in range(n):
            a0 = A0 + (A1 - A0) * i / n + 1.6
            a1 = A0 + (A1 - A0) * (i + 1) / n - 1.6
            pts = [pol(c, c, r_out * ss, a0), pol(c, c, r_out * ss, a1), pol(c, c, r_in * ss, a1), pol(c, c, r_in * ss, a0)]
            d.polygon(pts, fill=255)
        on = on.resize((S, S), Image.LANCZOS)
        dx, dy, r = _grid(S)
        th = np.degrees(np.arctan2(dx, -dy))
        frac = ((th - A0) / (A1 - A0)).astype(np.float32)
        red = np.clip((frac - 0.82) / 0.05, 0, 1)[..., None]
        colarr = np.array(C.mix(col, WHITE, 0.2), np.float32) * (1 - red) + np.array(REDZ, np.float32) * red
        lay = np.concatenate([colarr * np.ones((S, S, 1), np.float32), np.asarray(on, np.float32)[..., None]], -1)
        ring = Image.fromarray(lay.astype(np.uint8), 'RGBA')
        gl = ring.filter(ImageFilter.GaussianBlur(10))
        gl.putalpha(gl.getchannel('A').point(lambda v: min(255, int(v * 1.6))))
        gl.alpha_composite(ring)
        off = Image.new('RGBA', (S, S), (32, 34, 40, 0))
        off.putalpha(on.point(lambda v: int(v * 0.9)))
        return off, gl, frac

    def _streaks(self):
        rnd = np.random.default_rng(self.seed)
        return [(rnd.uniform(0, 360), rnd.uniform(0.0, 0.25), rnd.uniform(0.5, 1.0), rnd.integers(2, 6)) for _ in range(46)]

    # ── время ──
    def lights(self, t):
        """(режим подсветки, яркость 0..~1.2)."""
        D, u = self.drop, self.u
        if t < self.t1:
            mode = 'neu'
        elif t < self.t2:
            mode = 'h'
        elif t < self.tp:
            mode = 'a'
        else:
            mode = 'neu'
        k = C.out_cubic(C.seg(t, self.ign, self.ign + 0.3))
        for T in (self.t1, self.t2, self.tp):
            if T - 0.16 <= t < T:
                k = 1 - C.seg(t, T - 0.16, T - 0.04)
            elif T <= t < T + 0.25:
                k = C.out_cubic(C.seg(t, T, T + 0.25)) * (1 + 0.25 * math.exp(-(t - T) / 0.12))
        if t < D and t >= D - 0.42:                               # пауза трека перед ударом: подсветка гаснет
            k = min(k, 1 - 0.85 * C.seg(t, D - 0.42, D - 0.3))
        # пульс в долю
        if self.ign <= t < D - 0.45:
            ph = ((t - D) / u) % 1.0
            k *= 1 + 0.1 * math.exp(-ph * 7)
        return mode, k

    def needle_big(self, t, which):
        """Доля шкалы стрелки большого прибора (0..1) и прозрачность; None — стрелки нет."""
        D, u = self.drop, self.u
        if t < self.t1:
            q = C.seg(t, self.ign, self.ign + u)
            r = C.seg(t, self.ign + u + 0.1, self.ign + 1.8 * u)
            f = C.in_out(q) * (1 - C.in_out(r))
            a = 1.0 if r <= 0 else min(1.0, f / 0.35)
            return (f, a) if t >= self.ign else None
        if t < self.tp:
            key, t0, te = ('h', self.t1, self.t2) if t < self.t2 else ('a', self.t2, self.tp)
            G = self.T[key]['spd' if which == 0 else 'tach']
            if G['val'] is None:
                return None
            vmin, vmax = G['spec'][0], G['spec'][1]
            tgt = C.clamp((G['val'] - vmin) / (vmax - vmin))
            tr = t0 + (2.0 if which == 0 else 2.5) * u
            f = tgt * self.spring(t - tr) if t >= tr else 0.0
            f *= 1 - C.in_out(C.seg(t, te - 0.5 * u, te - 0.5 * u + 0.32))
            f += 0.003 * math.sin(t * 37 + which)
            return max(0.0, f), 1.0
        if t < D:
            q = C.seg(t, self.tp, D - 0.45)
            ph = ((t - self.tp) / (0.5 * u)) % 1.0
            f = 0.45 + 0.4 * q + 0.14 * math.exp(-ph * 5) - 0.04 * which
            if t >= D - 0.45:
                f = 0.985 + 0.012 * math.sin(t * 90 + which)
            return min(1.0, f), 1.0
        return None

    def needle_small(self, t, which):
        D, u = self.drop, self.u
        if t < self.t1:
            if t < self.ign:
                return None
            q = C.seg(t, self.ign + 0.1, self.ign + u)
            r = C.seg(t, self.ign + u + 0.1, self.ign + 1.8 * u)
            return C.in_out(q) * (1 - C.in_out(r))
        if t < self.tp:
            key, t0, te = ('h', self.t1, self.t2) if t < self.t2 else ('a', self.t2, self.tp)
            T = self.T[key]
            v = T['pp'] if which == 0 else T['pk']
            if v is None:
                return 0.0
            tgt = C.clamp(v / 40.0) if which == 0 else C.clamp((v - 60) / 40.0)
            tr = t0 + (3.5 if which == 0 else 4.0) * u
            f = tgt * self.spring(t - tr) if t >= tr else 0.0
            return max(0.0, f * (1 - C.in_out(C.seg(t, te - 0.5 * u, te - 0.5 * u + 0.32))))
        if t < D:
            return 0.0
        return None

    @staticmethod
    def spring(s):
        if s <= 0:
            return 0.0
        return 1 - math.exp(-7.5 * s) * math.cos(12.5 * s)

    # ── рисование ──
    def draw_needle(self, fr, cx, cy, deg, big=True, a=1.0):
        nd = self.nd_big if big else self.nd_small
        C.put(fr, C.rotate(nd, -deg), cx, cy, a)

    def gauges(self, fr, t):
        D, u = self.drop, self.u
        intro = t < self.t1
        for which, (cx, cy) in enumerate((GL, GR_)):
            side = 'h' if which == 0 else 'a'
            n = self.needle_big(t, which)
            if intro:
                if n is not None:
                    self.draw_needle(fr, cx, cy, A0 + (A1 - A0) * n[0], True, n[1] * 0.95)
                d0 = self.ign + 0.08 + 0.14 * which
                qe = C.out_back(C.seg(t, d0, d0 + 0.4), 1.5)
                ae = (1 - C.seg(t, self.t1 - 0.18, self.t1 - 0.04))
                if qe > 0.01:
                    C.put(fr, C.scale(self.i_emb[side], max(0.05, qe)), cx, cy - 22, min(1.0, qe * 1.5) * ae)
                qt = C.out_expo(C.seg(t, d0 + 0.2, d0 + 0.6))
                C.put(fr, self.i_role[side], cx, cy - 0.58 * RG - 10 * (1 - qt), qt * ae)
                C.put(fr, self.i_name[side], cx, cy + 0.45 * RG + 14 * (1 - qt), qt * ae)
                continue
            if n is not None:
                self.draw_needle(fr, cx, cy, A0 + (A1 - A0) * n[0], True, n[1])
            if t < self.tp:
                self.readout(fr, t, which, cx, cy)
            C.put(fr, self.hub_big, cx, cy)
        for which, (cx, cy) in enumerate((SL, SR_)):
            f = self.needle_small(t, which)
            if f is not None:
                self.draw_needle(fr, cx, cy, S0 + (S1 - S0) * f, False)
                C.put(fr, self.hub_small, cx, cy)
        for cx, cy in (GL, GR_):
            C.put(fr, self.glare, cx, cy)

    def readout(self, fr, t, which, cx, cy):
        key, t0, te = ('h', self.t1, self.t2) if t < self.t2 else ('a', self.t2, self.tp)
        G = self.T[key]['spd' if which == 0 else 'tach']
        if G['val'] is None:
            return
        u = self.u
        tr = t0 + (2.0 if which == 0 else 2.5) * u
        if t < tr:
            return
        a = C.seg(t, tr, tr + 0.12) * (1 - C.seg(t, te - 0.5 * u, te - 0.5 * u + 0.25))
        cur = min(G['val'], G['val'] * self.spring(t - tr)) if t - tr < 0.45 else G['val']
        s = ('%d' % int(round(cur))) if G['fmt'] == 'int' else dec(cur)
        im = glow_txt(s, 'exo', 96, WHITE, 800, 12, 0.45, self.T[key]['col'])
        C.put(fr, im, cx, cy + 0.35 * RG, a)

    def small_values(self, fr, t):
        if not self.t1 <= t < self.tp:
            return
        key, t0, te = ('h', self.t1, self.t2) if t < self.t2 else ('a', self.t2, self.tp)
        T = self.T[key]
        u = self.u
        for which, v, x in ((0, T['pp'], 290), (1, T['pk'], W - 290)):
            if v is None:
                continue
            tr = t0 + (3.5 if which == 0 else 4.0) * u
            if t < tr:
                continue
            q = C.out_expo(C.seg(t, tr, tr + 0.3))
            a = q * (1 - C.seg(t, te - 0.5 * u, te - 0.5 * u + 0.25))
            im = glow_txt(dec(v) + '%', 'exo', 66, WHITE, 800, 10, 0.4, T['col'])
            C.put(fr, im, x, 1364 + 10 * (1 - q), a)

    def odometer(self, fr, t):
        """Барабаны одометра: часы в интро, разница шайб в сценах команд."""
        u = self.u
        if t < self.t1:
            if not self.clock or t < self.ign:
                return
            hh, mm = self.clock
            digs = [hh // 10, hh % 10, None, mm // 10, mm % 10]
            vals = []
            for i, dg in enumerate(digs):
                if dg is None:
                    vals.append(None)
                    continue
                q = C.out_cubic(C.seg(t, self.ign + 0.9 * u + 0.08 * i, self.ign + 1.6 * u + 0.08 * i))
                vals.append(dg * q)
            a = 1 - C.seg(t, self.t1 - 0.16, self.t1 - 0.04)
            self.drums(fr, vals, None, a)
            return
        if t >= self.tp:                                  # перегазовка: снова часы начала матча
            if self.clock and t < self.drop:
                hh, mm = self.clock
                self.drums(fr, [hh // 10, hh % 10, None, mm // 10, mm % 10], None,
                           C.seg(t, self.tp, self.tp + 0.2) * (1 - 0.7 * C.seg(t, self.drop - 0.42, self.drop - 0.3)))
            return
        key, t0, te = ('h', self.t1, self.t2) if t < self.t2 else ('a', self.t2, self.tp)
        gd = self.T[key]['gd']
        if gd is None:
            return
        tr = t0 + 3.0 * u
        q = C.out_cubic(C.seg(t, tr, tr + 0.7 * u))
        a = 1 - C.seg(t, te - 0.5 * u, te - 0.5 * u + 0.25)
        val = abs(gd) * q
        nd = len(str(abs(gd)))
        if nd == 1:
            vals = [val]
        else:
            units = val % 10
            tens = math.floor(val / 10) + max(0.0, units - 9)
            vals = [tens, units]
        sign = None if gd == 0 else ('−' if gd < 0 else '+')
        self.drums(fr, vals, sign if t >= tr else None, a, F.LOSS if gd < 0 else F.WIN)

    def drum_strip(self):
        key = 'drum'
        if key not in _SPR:
            ch = ODO_H - 8
            strip = Image.new('RGBA', (CELL_W, ch * 11), (0, 0, 0, 0))
            for i in range(11):
                C.put(strip, C.text(str(i % 10), 'exo', 64, (240, 242, 246), 800), CELL_W / 2, ch * i + ch / 2)
            sh = np.zeros((ch, CELL_W, 4), np.uint8)                     # затенение барабана сверху и снизу
            yy = np.linspace(-1, 1, ch)[:, None]
            sh[..., 3] = (np.clip(np.abs(yy) ** 2.2, 0, 1) * 235).astype(np.uint8).repeat(CELL_W, 1)
            _SPR[key] = (strip, Image.fromarray(sh, 'RGBA'), ch)
        return _SPR[key]

    def drums(self, fr, vals, sign, a, sign_col=WHITE):
        strip, shade, ch = self.drum_strip()
        cells = []
        if sign:
            cells.append(('s', sign))
        cells += [('c', None) if v is None else ('d', v) for v in vals]
        widths = [CELL_W if k != 'c' else 26 for k, _ in cells]
        gap = 6
        x = ODO_C[0] - (sum(widths) + gap * (len(cells) - 1)) / 2
        y0 = ODO_C[1] - ch / 2
        for (kind, v), wd in zip(cells, widths):
            if kind == 'c':
                C.put(fr, C.text(':', 'exo', 60, (240, 242, 246), 800), x + wd / 2, ODO_C[1] - 4, a)
            else:
                cell = Image.new('RGBA', (CELL_W, ch), (20, 21, 24, 255))
                if kind == 'd':
                    off = int(round((v % 10) * ch))
                    cell.alpha_composite(strip.crop((0, off, CELL_W, off + ch)))
                else:
                    C.put(cell, C.text(v, 'exo', 64, sign_col, 800), CELL_W / 2, ch / 2)
                cell.alpha_composite(shade)
                C.put(fr, cell, x, y0, a, anchor='tl')
            x += wd + gap

    def blinkers(self, fr, t):
        D, u = self.drop, self.u
        if t >= D or t < self.ign:
            onl = onr = False
        else:
            if t >= self.tp:
                ph = ((t - D) / (0.5 * u)) % 1.0
                on = ph < 0.5
                onl = onr = on
            else:
                ph = ((t - D) / u) % 1.0
                on = ph < 0.45
                if t < self.t1:
                    onl = onr = on
                elif t < self.t2:
                    onl, onr = on, False
                else:
                    onl, onr = False, on
        C.put(fr, arrow(onl), W / 2 - 236, TAG_Y)
        C.put(fr, arrow(onr, True), W / 2 + 236, TAG_Y)

    # ── дисплей ──
    def display(self, fr, t):
        D, u = self.drop, self.u
        x0, y0 = DISP[0], DISP[1]
        cx = (DISP[0] + DISP[2]) / 2
        if t < self.t1:
            if t < self.ign:
                return
            a = 1 - C.seg(t, self.t1 - 0.16, self.t1 - 0.04)
            q = C.out_expo(C.seg(t, self.ign + 0.15, self.ign + 0.5))
            C.put(fr, self.i_date, cx, y0 + 54 + 14 * (1 - q), q * a)
            q = C.out_expo(C.seg(t, self.ign + 0.3, self.ign + 0.65))
            C.put(fr, self.i_lab, cx, y0 + 112, q * a)
            for i, pl in enumerate(self.plates):
                tb = self.ign + u + 0.12 * i
                q = C.out_back(C.seg(t, tb, tb + 0.35), 1.4)
                if q > 0.01:
                    px = x0 + 34 + 146 + i * (292 + 22)
                    C.put(fr, C.scale(pl, 0.75 + 0.25 * q), px, y0 + 266, min(1.0, q * 1.6) * a)
            return
        if t < self.tp:
            key, t0, te = ('h', self.t1, self.t2) if t < self.t2 else ('a', self.t2, self.tp)
            T = self.T[key]
            a = 1 - C.seg(t, te - 0.2, te - 0.06)
            q = C.out_expo(C.seg(t, t0, t0 + 0.35))
            C.put(fr, T['head'], cx + 40 * (1 - q), y0 + 18 + T['head'].height / 2, q * a)
            C.put(fr, T['div'], cx, y0 + 156, C.seg(t, t0 + 0.1, t0 + 0.4) * a)
            for i, im in enumerate(T['lines']):
                tb = t0 + (0.5 + 0.5 * i) * u
                if t < tb:
                    continue
                ql = C.out_expo(C.seg(t, tb, tb + 0.3))
                C.put(fr, im, cx - 50 * (1 - ql), y0 + 200 + 76 * i, ql * a)
            return
        if t < D:
            q = C.out_expo(C.seg(t, self.tp, self.tp + 0.3))
            fill = C.seg(t, self.tp + 0.05, D - 0.5)
            n = len(self.leds)
            lit = int(round(fill * n))
            blink = t >= D - 0.5 and ((t - D) * 14) % 1.0 < 0.55
            for i, (on, off) in enumerate(self.leds):
                x = x0 + 74 + i * 60 + 10
                y = y0 + 64
                C.put(fr, off, x, y, q)
                if (i < lit and t < D - 0.5) or blink:
                    C.put(fr, on, x, y, q)
            dim = 1 - 0.7 * C.seg(t, D - 0.42, D - 0.3)
            for s, xx in (('h', x0 + 250), ('a', x0 + 738)):
                k = 1 + 0.05 * math.exp(-(((t - D) / (0.5 * u)) % 1.0) * 6)
                C.put(fr, C.scale(self.r_emb[s], k), xx, y0 + 226, q * dim)
                C.put(fr, self.r_name[s], xx, y0 + 356, q * dim)

    def pick(self, fr, t):
        D, u = self.drop, self.u
        tc = self.t_cta
        ke = C.out_expo(C.seg(t, D, D + 0.32))
        kc = C.in_out(C.seg(t, tc, tc + 0.5))
        if kc > 0:
            r = tuple(C.lerp(a, b, kc) for a, b in zip(BIGP, CTAP))
        else:
            r = tuple(C.lerp(a, b, ke) for a, b in zip(DISP, BIGP))
        pw, ph = r[2] - r[0], r[3] - r[1]
        if ke >= 1 and kc <= 0:
            pan = self.panel_big
        else:
            pan = self._panel(int(pw // 4 * 4), int(ph // 4 * 4), self.cf)
        C.put(fr, pan, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        s = 1 - 0.14 * kc
        top = r[1] + 20 * kc
        bp = math.exp(-(((t - D) / u) % 1.0) * 6) if t < tc + 0.5 else 0.0

        def Y(off):
            return top + 20 * (1 - kc) + s * (off - 20 * (1 - kc)) if kc else top + off

        ry = Y(330)
        # лучи скорости из-за эмблемы
        dt = t - D
        if 0 <= dt < 0.9:
            lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            for ang, dl, sp, wd in self.streaks:
                tt = dt - dl * 0.4
                if tt <= 0:
                    continue
                r0 = 120 + 1500 * sp * tt
                r1 = r0 + 160 + 300 * sp
                al = int(200 * max(0.0, 1 - dt / 0.9))
                xa, ya = pol(W / 2, ry, r0, ang)
                xb, yb = pol(W / 2, ry, r1, ang)
                d.line((xa, ya, xb, yb), fill=C.mix(self.cf, WHITE, 0.55) + (al,), width=int(wd))
            mask = Image.new('L', (W, H), 0)
            ImageDraw.Draw(mask).rounded_rectangle((r[0] + 8, r[1] + 8, r[2] - 8, r[3] - 8), radius=30, fill=255)
            lay.putalpha(Image.fromarray((np.asarray(lay.getchannel('A'), np.uint16) * np.asarray(mask, np.uint16) // 255)
                                         .astype(np.uint8), 'L'))
            fr.alpha_composite(lay)
        # цифровое кольцо: заполняется на ударе, пульс в долю
        rs = s * (0.7 + 0.3 * ke)
        fill = C.out_cubic(C.seg(t, D, D + 0.42))
        off = self.ring_off
        on = self.ring_on.copy()
        al = np.asarray(on.getchannel('A'), np.float32)
        fm = (self.ring_th <= fill + 1e-3).astype(np.float32) * (np.hypot(*_grid(on.width)[:2]) > 60)
        on.putalpha(Image.fromarray((al * fm * (0.82 + 0.18 * bp)).astype(np.uint8), 'L'))
        C.put(fr, C.scale(off, rs), W / 2, ry, ke)
        C.put(fr, C.scale(on, rs), W / 2, ry, ke)
        qe = C.out_back(C.seg(t, D + 0.02, D + 0.4), 1.5)
        if qe > 0.01:
            C.put(fr, C.scale(self.p_emb, max(0.05, qe) * s * (1 + 0.035 * bp)), W / 2, ry, min(1.0, qe * 1.5))
        y = Y(640)
        if self.p_l1 is not None:
            q1 = C.out_expo(C.seg(t, D + 0.08, D + 0.36))
            C.put(fr, C.scale(self.p_l1, s * (1.4 - 0.4 * q1)), W / 2, y, min(1.0, q1 * 2))
        q2 = C.out_expo(C.seg(t, D + 0.14, D + 0.46))
        C.put(fr, C.scale(self.p_l2, s * (1.5 - 0.5 * q2) * (1 + 0.015 * bp)), W / 2, Y(748), min(1.0, q2 * 2))
        if self.p_l3 is not None:
            q3 = C.out_expo(C.seg(t, D + 0.5 * u, D + 0.85 * u))
            C.put(fr, C.scale(self.p_l3, s), W / 2, Y(848) + 20 * (1 - q3), q3)
        if self.kef is not None:
            q4 = C.out_back(C.seg(t, D + 1.0 * u, D + 1.35 * u), 1.7)
            if q4 > 0.01:
                C.put(fr, C.scale(self.kef, s * (0.5 + 0.5 * q4)), W / 2, Y(990), min(1.0, q4 * 1.5))

    # ── кадр ──
    def frame(self, t):
        u, D = self.u, self.drop
        mode, k = self.lights(t)
        if t >= D:
            mode, k = 'neu', 0.35
        if k <= 0.003:
            fr = self.dark.copy()
        elif abs(k - 1) < 0.003:
            fr = self.lit[mode].copy()
        else:
            fr = Image.blend(self.dark, self.lit[mode], k)
        if t < D + 0.4:
            self.gauges(fr, t)
            self.odometer(fr, t)
            self.small_values(fr, t)
            self.display(fr, t)
        if t >= D:
            self.pick(fr, t)
        self.blinkers(fr, t)
        C.put(fr, self.tag, W / 2, TAG_Y, 0.95)
        ha = 1 - C.seg(t, self.t_cta, self.t_cta + 0.2)
        C.put(fr, self.handle_im, W / 2, HY, 0.92 * ha * C.HANDLE_BOTTOM)
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.05, self.t_cta + 0.5))
            C.put(fr, self.tg, W / 2, 1344 + 50 * (1 - q), q)
        # камера: толчки на склейках, дрожь на перегазовке, рывок на дропе
        z, dx, dy, rot = 1.0, 0.0, 0.0, 0.0
        for th in (self.t1, self.t2, self.tp):
            if t >= th:
                z += 0.022 * (1 - C.seg(t, th, th + 0.3)) ** 2
        if self.ign <= t < D - 0.45:
            ph = ((t - D) / u) % 1.0
            z += 0.005 * math.exp(-ph * 8)
        if self.tp <= t < D:
            q = C.seg(t, self.tp, D)
            dx += 4 * q * math.sin(t * 97)
            dy += 4 * q * math.cos(t * 83)
        if t >= D:
            kk = 1 - C.seg(t, D, D + 0.55)
            z += 0.08 * kk ** 2
            sx, sy = C.shake(t, D, 26, 0.5)
            dx, dy = dx + sx, dy + sy
            rot = 1.2 * kk ** 2 * math.sin((t - D) * 36)
            if t < self.t_cta:
                z += 0.006 * math.exp(-(((t - D) / u) % 1.0) * 7)
        fr = C.zoom(fr.convert('RGB'), z, dx=dx, dy=dy, rot=rot)
        if D <= t < D + 0.2:
            fr = C.rgb_split(fr, 14 * (1 - C.seg(t, D, D + 0.2)))
        if D <= t < D + 0.36:
            fa = 1.0 if t < D + 1 / 30 else (1 - C.seg(t, D + 1 / 30, D + 0.36)) ** 1.5
            fr = Image.blend(fr.convert('RGB'), Image.new('RGB', fr.size, C.mix(WHITE, self.cf, 0.15)), 0.85 * fa)
        if t < 0.3:
            fr = Image.blend(Image.new('RGB', fr.size, (0, 0, 0)), fr.convert('RGB'), C.seg(t, 0, 0.3))
        fr = C.vignette(fr, 0.38)
        return C.grain(fr, t, 3)
