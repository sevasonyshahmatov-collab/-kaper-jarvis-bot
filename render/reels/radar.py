# -*- coding: utf-8 -*-
"""«Радар» — ночной сонар, эхолокация (трек «BATS»): круглый экран с люминофором, кольцами дальности, рисками пеленга
и лучом развёртки; на каждую долю трека из центра уходит эхо-импульс. Не терминал (это jarvis.py) — прибор с крупными
выносками у отметок.

Сцены (u — доля трека, D — дроп; доли считаются от дропа, team / pre / hold / cta — параметры):
  интро (до D − (2·team + pre) долей) — сам матч на экране: обе эмблемы — цели с метками «хозяева / гости»,
                 сверху лига и время МСК, под экраном — линия основного времени П1 · Х · П2 крупными плашками;
  команда (team долей) ×2 — экран в цвете клуба, эмблема в центре, название клуба сверху, «ХОЗЯЕВА» / «ГОСТИ» на корпусе;
                 луч делает оборот за 3 доли и на каждой половине доли засвечивает отметку с выноской
                 (с 1-й доли сцены): последние 3 игры (соперник, дата, счёт, ОТ/Б, В/П цветом) по верхней дуге,
                 очки за N матчей, место, разница шайб — по нижней; под экраном — большинство / меньшинство
                 (и серия от 2 игр), если такие цифры есть. Пройденные лучом отметки вспыхивают на каждом обороте;
  поиск (pre долей) — обе цели на экране, прицел мечется между ними на половинах долей, в последней доле — на четвертях,
                 импульсы чаще, луч вдвое быстрее, камера наезжает;
  ДРОП (hold долей) — ровно на дропе прицел защёлкивается на команде прогноза, вторая цель исчезает (одна эмблема,
                 без «VS»), ударная эхо-волна и вспышка; эмблема уходит в центр экрана, «ПОБЕДА / КЛУБ»,
                 «В ОСНОВНОЕ ВРЕМЯ» и кэф; на каждую долю — эхо;
  финал (cta долей) — экран уменьшается, снизу плашка Telegram (C.tg_plate, текст по центру плашки).
@jarvibet — у низа безопасной зоны (y 1448), одинаково во всех сценах до плашки Telegram.
Кадр зависит только от t; экран в цвете, выноски, эмблемы и поля углов кешируются (до fork — общие для процессов).
"""
import colorsys
import math
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels.core import W, H

BG0 = (4, 8, 14)
NEUT = (110, 214, 255)            # люминофор интро и поиска (холодный голубой)
AMBER = (255, 190, 64)            # прицел на поиске
WHITE = (255, 255, 255)
GRAY = (148, 168, 182)
INK = (5, 11, 18)
TAG_Y, TOP_Y, HY = 262, 334, 1448  # метка JARVIS | NHL, строка над экраном, @jarvibet
PAD = 190                         # поле вокруг экрана в слое (ореол)
BW, BH = 304, 124                 # выноска
SLOTS = (300, 0, 60, 120, 180, 240)   # пеленги выносок по часовой от верха — в порядке засветки лучом
SLOT_D = 274
G_INTRO = (540.0, 712.0, 322.0)   # (центр x, центр y, радиус) экрана по сценам
G_TEAM = (540.0, 862.0, 432.0)
G_PICK = (540.0, 640.0, 300.0)
G_CTA = (540.0, 602.0, 232.0)
HUNT_DX, HUNT_E = 214, 210        # цели на поиске: смещение от центра и размер эмблем
PICK_E = 270                      # эмблема прогноза
_ST, _FLD, _SPR = {}, {}, {}


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def neon(c, v_min=0.9, s_min=0.62):
    """Клубный цвет как свечение люминофора: насыщенный и яркий (тот же тон)."""
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    s = min(0.9, max(s, s_min)) if s > 0.12 else s
    v = max(v, v_min)
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, s, v))


def club(t, avoid=None):
    """Цветной клубный цвет (не серый/чёрный); если близок к avoid — следующий цвет клуба."""
    cand = [c for c in (t.c1, t.c0, t.c2) if (max(c) - min(c)) / 255 > 0.2 and 40 < 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] < 235]
    cand = [neon(c) for c in cand] or [neon(t.c1)]
    if avoid is not None:
        far = [c for c in cand if sum((a - b) ** 2 for a, b in zip(c, avoid)) ** 0.5 > 120]
        if far:
            return far[0]
    return cand[0]


def pct(v):
    try:
        return ('%.1f' % float(v)).rstrip('0').rstrip('.') + '%'
    except (TypeError, ValueError):
        return None


def lerp3(a, b, k):
    return tuple(C.lerp(x, y, k) for x, y in zip(a, b))


# ─────────────────────────────── экран сонара ───────────────────────────────
def _tinted(mask, col, k=1.0):
    lay = Image.new('RGBA', mask.size, tuple(col) + (0,))
    lay.putalpha(mask if k == 1.0 else mask.point(lambda v: min(255, int(v * k))))
    return lay


def scope(R, col):
    """Экран радиуса R в цвете col (слой 2·(R+PAD)): ореол, корпус с рисками, диск со строками развёртки,
    кольца дальности, перекрестье, пунктир диагоналей, риски пеленга."""
    R = int(R)
    key = (R, tuple(col))
    if key in _ST:
        return _ST[key]
    S = 2 * (R + PAD)
    c = S / 2.0
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    dx, dy = xx - c + 0.5, yy - c + 0.5
    r = np.hypot(dx, dy)
    colf = np.array(col, np.float32)
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    # ореол вокруг корпуса
    k = np.clip(1 - (r - R) / PAD, 0, 1) ** 2.6 * (r > R)
    lay = np.zeros((S, S, 4), np.uint8)
    lay[..., :3] = col
    lay[..., 3] = (k * 80).astype(np.uint8)
    out.alpha_composite(Image.fromarray(lay, 'RGBA'))
    # корпус: тёмный металл, свет сверху-слева, ребро посередине
    r0, r1 = R + 3, R + 34
    light = np.cos(np.arctan2(dy, dx) + 2.36)
    v = 30 + 17 * light + 12 * np.exp(-((r - (R + 18)) / 5.0) ** 2) + 26 * np.exp(-((r - r1 + 1.5) / 1.4) ** 2)
    a = np.clip(r - r0 + 0.5, 0, 1) * np.clip(r1 - r + 0.5, 0, 1)
    lay = np.zeros((S, S, 4), np.float32)
    lay[..., 0], lay[..., 1], lay[..., 2], lay[..., 3] = v * 0.84, v * 0.94, v * 1.1, a * 255
    out.alpha_composite(Image.fromarray(np.clip(lay, 0, 255).astype(np.uint8), 'RGBA'))
    # диск: люминофор светлее к центру, строки развёртки
    q = np.clip(r / R, 0, 1)
    kk = (0.04 + 0.17 * (1 - q ** 2) ** 1.3)[..., None]
    disc = np.array(BG0, np.float32) * (1 - kk) + colf * kk
    disc[np.arange(S) % 3 == 0] *= 0.72
    lay = np.concatenate([disc, (np.clip(R + 4 - r, 0, 1) * 255)[..., None]], -1)
    out.alpha_composite(Image.fromarray(np.clip(lay, 0, 255).astype(np.uint8), 'RGBA'))
    # сетка (2× со сглаживанием): dim — кольца, перекрестье, мелкие риски; br — край экрана и риски через 30°
    ss = 2
    dim, br, bz = (Image.new('L', (S * ss, S * ss), 0) for _ in range(3))
    dd, db, dz = ImageDraw.Draw(dim), ImageDraw.Draw(br), ImageDraw.Draw(bz)
    c2 = c * ss

    def ring(d, rad, wdt, fill):
        d.ellipse((c2 - rad * ss, c2 - rad * ss, c2 + rad * ss, c2 + rad * ss), outline=fill, width=int(wdt * ss))

    def ray(d, deg, a0, a1, fill, wdt):
        sa, ca = math.sin(math.radians(deg)), -math.cos(math.radians(deg))
        d.line((c2 + sa * a0 * ss, c2 + ca * a0 * ss, c2 + sa * a1 * ss, c2 + ca * a1 * ss), fill=fill, width=int(wdt * ss))

    for f in (0.25, 0.5, 0.75):
        ring(dd, R * f, 2, 125)
    ring(db, R + 1, 4, 255)
    for deg in (0, 90):
        ray(dd, deg, -R, R, 95, 2)
    for deg in (45, 135, 225, 315):
        n = 22
        for i in range(0, n, 2):
            ray(dd, deg, R * i / n, R * (i + 1) / n, 60, 2)
    for deg in range(0, 360, 5):
        if deg % 30 == 0:
            ray(db, deg, R - 26, R, 230, 3)
        else:
            ray(dd, deg, R - (13 if deg % 10 == 0 else 7), R, 150, 2)
    for i in range(1, 20):                                 # риски дальности на осях
        rad = R * i / 20
        L = 9 if i % 5 else 15
        for deg in (0, 90, 180, 270):
            sa, ca = math.sin(math.radians(deg)), -math.cos(math.radians(deg))
            px, py = c2 + sa * rad * ss, c2 + ca * rad * ss
            dd.line((px - ca * L * ss, py + sa * L * ss, px + ca * L * ss, py - sa * L * ss), fill=110, width=2 * ss)
    for deg in range(0, 360, 10):                          # риски на корпусе (нейтральные)
        ray(dz, deg, R + 9, R + (28 if deg % 30 == 0 else 17), 170 if deg % 30 == 0 else 95, 3 if deg % 30 == 0 else 2)
    dim, br, bz = (im.resize((S, S), Image.LANCZOS) for im in (dim, br, bz))
    out.alpha_composite(_tinted(dim, col, 0.8))
    out.alpha_composite(_tinted(br.filter(ImageFilter.GaussianBlur(9)), col, 1.3))
    out.alpha_composite(_tinted(br, C.mix(col, WHITE, 0.3)))
    out.alpha_composite(_tinted(bz, (200, 214, 226)))
    _ST[key] = out
    return out


def fields(R, keep=False):
    """Поля для луча: пеленг каждой точки диска (0 — верх, по часовой) и яркость по радиусу с краем диска."""
    R = int(R)
    if R in _FLD:
        return _FLD[R]
    n = 2 * R
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    dx, dy = xx - R + 0.5, yy - R + 0.5
    th = np.mod(np.arctan2(dx, -dy), 2 * np.pi).astype(np.float32)
    rr = np.hypot(dx, dy) / R
    rad = ((0.45 + 0.55 * np.clip(rr, 0, 1)) * np.clip((1 - rr) * R - 2, 0, 1)).astype(np.float32)
    out = (th, rad)
    if keep:
        _FLD[R] = out
    return out


_LUT_N = 2048
_dd = np.linspace(0, 2 * np.pi, _LUT_N, endpoint=False)
SWEEP_LUT = (0.6 * np.exp(-_dd / 0.62) + 0.4 * np.exp(-_dd / 0.03)).astype(np.float32) * (_dd < 2.6)


def sprite(kind, *args):
    """Мелкие спрайты (кеш): точка отметки, рамка цели, прицел."""
    key = (kind,) + args
    if key in _SPR:
        return _SPR[key]
    if kind == 'dot':
        d, col = args
        im = C.radial(d, d, col, 255, 1.6)
        core = C.ellipse(d // 4, d // 4, C.mix(col, WHITE, 0.6))
        C.put(im, core, d / 2, d / 2)
    elif kind == 'reticle':
        size, col, wdt = args
        ss = 3
        S = int(size) + 4 * wdt
        im = Image.new('RGBA', (S * ss, S * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = 2 * wdt * ss, 2 * wdt * ss, (S - 2 * wdt) * ss, (S - 2 * wdt) * ss
        arm = size * 0.27 * ss
        cl = tuple(col) + (255,)
        w = wdt * ss
        for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            d.line((x, y, x + sx * arm, y), fill=cl, width=w)
            d.line((x, y, x, y + sy * arm), fill=cl, width=w)
        tk = size * 0.08 * ss
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        for (xa, ya, xb, yb) in ((mx, y0, mx, y0 + tk), (mx, y1, mx, y1 - tk), (x0, my, x0 + tk, my), (x1, my, x1 - tk, my)):
            d.line((xa, ya, xb, yb), fill=cl, width=max(1, int(w * 0.7)))
        im = im.resize((S, S), Image.LANCZOS)
        im = C.glow(im, 7, 1.1, col)
    elif kind == 'tbox':                                       # рамка цели — тонкие уголки
        size, col = args
        im = sprite('reticle', size, col, 3)
    _SPR[key] = im
    return im


class Radar(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 73, drop=20 * 60 / 73, line=None, team=7, pre=2,
                 hold=5, cta=3, seed=23, **kw):
        """Сцены: интро → команда (team долей) ×2 → поиск (pre) → дроп-прогноз (hold) → Telegram (cta); доли — от дропа."""
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.line = league, when, coef, line
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.other = 'a' if self.side == 'h' else 'h'
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
        self.cover_t = max(1.3, self.t1 - 0.55)
        self.g_intro = G_INTRO if line else (540.0, 800.0, 400.0)
        self.om = 120.0 / u                                     # луч: 60° за полдоли — оборот за 3 доли
        self._prep()

    # ── заготовки ──
    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        bg = C.vgrad(W, H, [(0, (8, 14, 24)), (0.45, BG0), (1, (2, 4, 8))]).convert('RGBA')
        d = ImageDraw.Draw(bg)
        for _ in range(160):                                     # ночное небо: редкие звёзды
            x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0.8, 2.2)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(200, 220, 255, int(rnd.uniform(25, 90))))
        for y in range(0, H, 46):                                # точечная сетка прибора
            for x in range(23, W, 46):
                d.point((x, y), fill=(60, 90, 110, 255))
        self.bg = bg
        self.col = {'h': club(self.h)}
        self.col['a'] = club(self.a, avoid=self.col['h'])
        self.cf = self.col[self.side]
        self.base = {'h': self._base(self.h), 'a': self._base(self.a)}
        # экраны и поля углов для устойчивых размеров (до fork — общие для процессов)
        R0, Rt, Rp, Rc = (int(g[2]) for g in (self.g_intro, G_TEAM, G_PICK, G_CTA))
        for R, col in ((R0, NEUT), (Rt, NEUT), (Rt, self.col['h']), (Rt, self.col['a']), (Rp, self.cf), (Rc, self.cf)):
            scope(R, col)
        for R in (R0, Rt, Rp, Rc):
            fields(R, keep=True)
        self.steady = {R0, Rt, Rp, Rc}
        # общее
        self.tag = C.text(F.tag(self.league), 'unb', 32, (190, 204, 216), 700, track=0.12)
        self.handle_im = C.text(C.HANDLE, 'unb', 40, (226, 236, 244), 600)
        self.date = C.text('%s · %s' % (F.lg_ru(self.league), self.when), 'tek', 48, C.mix(NEUT, WHITE, 0.25), 800,
                           track=0.04, max_w=980)
        self.title = C.text('%s — %s' % (self.h.up, self.a.up), 'tek', 64, WHITE, 800, max_w=1000)
        # интро: цели и линия
        self.i_emb = {s: self._emb(t, 172, NEUT) for s, t in (('h', self.h), ('a', self.a))}
        self.i_lab = {s: self._target_label(t, 'ХОЗЯЕВА' if s == 'h' else 'ГОСТИ') for s, t in (('h', self.h), ('a', self.a))}
        self.odds = C.odds_row(self.line, 980, 214, font='tek', lab_font='tek', fill=INK, fill_a=236, val_col=WHITE,
                               lab_col=NEUT, outline=C.mix(NEUT, INK, 0.45), radius=30) if self.line else None
        self.odds_lab = C.text('ОСНОВНОЕ ВРЕМЯ', 'tek', 36, NEUT, 700, track=0.22)
        # команды
        self.T = {k: self._team_data(k) for k in ('h', 'a')}
        # поиск
        self.hunt_emb = {s: self._emb(t, HUNT_E, NEUT) for s, t in (('h', self.h), ('a', self.a))}
        self.hunt_name = {s: self._name_plate(t.up, NEUT) for s, t in (('h', self.h), ('a', self.a))}
        self.jumps = self._jumps()
        # прогноз
        self.p_emb = self._emb(self.fav, PICK_E, self.cf, 22)
        self.p_lab = self._bezel_lab('ПРОГНОЗ', self.cf)
        l1, nm = F.head_main(self.pick1)                     # «ИНДИВИДУАЛЬНЫЙ ТОТАЛ …» сверху, «МЕНЬШЕ 2,5» крупно (19.10)
        self.p_l1 = C.text(l1, 'tek', 66, WHITE, 800, track=0.08, max_w=900) if l1 else None
        self.p_l2 = C.glow(C.text(nm, 'tek', 124, self.cf, 900, max_w=880), 16, 0.75, self.cf)
        self.p_l3 = C.text(self.pick2, 'tek', 42, (215, 226, 236), 700, track=0.12, max_w=980) if self.pick2 else None
        self.kef = None
        if self.coef:
            kt = C.text('КЭФ ' + C.fmt_k(self.coef), 'tek', 66, WHITE, 900, track=0.04)
            kp = C.rrect(kt.width + 110, 104, 52, self.base[self.side], outline=self.cf, width=4)
            C.put(kp, kt, kp.width / 2, 52)
            self.kef = C.glow(kp, 16, 0.8, self.cf)
        self.tg = C.tg_plate(960, 172, font='unb')
        # события: эхо-импульсы из центра экрана (старт, длительность, сила)
        ev = []
        nb = int(math.ceil(self.dur / self.u)) + 2
        for k in range(-nb, nb):
            tb = self.b(k)
            if 0 <= tb < self.dur and not (self.tp <= tb < self.drop):
                ev.append((tb, 0.95 * self.u, 1.0))
        for tj, _ in self.jumps:
            ev.append((tj, 0.6 * self.u, 1.0))
        self.pulses = sorted(ev)

    def _base(self, team):
        """Клубный цвет для плашек (насыщенный, но тёмный — под белый текст)."""
        h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in self.col['h' if team is self.h else 'a']))
        return tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, min(1, s * 1.05), 0.5))

    def _emb(self, team, size, col, r=16):
        e = team.emb(size)
        return C.glow(e, r, 0.85, col)

    def _bezel_lab(self, s, col):
        tx = C.text(s, 'tek', 30, INK, 800, track=0.22)
        pl = C.rrect(tx.width + 52, 50, 25, col)
        C.put(pl, tx, pl.width / 2, 25)
        return pl

    def _target_label(self, team, role):
        w, h = 262, 92
        pl = C.rrect(w, h, 18, INK, 228, outline=C.mix(NEUT, INK, 0.45), width=2)
        C.put(pl, C.text(role, 'tek', 24, NEUT, 700, track=0.2, max_w=w - 30), w / 2, 24)
        C.put(pl, C.text(team.up, 'tek', 40, WHITE, 800, max_w=w - 26), w / 2, 62)
        return pl

    def _name_plate(self, s, col):
        tx = C.text(s, 'tek', 40, WHITE, 800, max_w=320)
        pl = C.rrect(tx.width + 48, 66, 18, INK, 228, outline=C.mix(col, INK, 0.45), width=2)
        C.put(pl, tx, pl.width / 2, 33)
        return pl

    def _plate(self, col):
        pl = C.rrect(BW, BH, 18, INK, 232, outline=C.mix(col, INK, 0.5), width=2)
        C.put(pl, C.rrect(7, BH - 34, 3, col), 15, BH / 2)
        return pl

    def _flash(self, col):
        key = ('flash', col)
        if key not in _SPR:
            ol = C.rrect(BW, BH, 18, None, outline=C.mix(col, WHITE, 0.35), width=3)
            _SPR[key] = C.glow(ol, 10, 1.2, col)
        return _SPR[key]

    def _game_block(self, g, col):
        im = self._plate(col)
        x0 = 34
        dt = C.text(g['date'], 'tek', 25, GRAY, 600) if g['date'] else None
        room = BW - x0 - 18 - (dt.width + 14 if dt else 0)
        nm = C.text(g['opp'].upper(), 'tek', 34, WHITE, 700, max_w=room)
        C.put(im, nm, x0, 38 - nm.height / 2, anchor='tl')
        if dt:
            C.put(im, dt, BW - 18 - dt.width, 38 - dt.height / 2, anchor='tl')
        ch = F.chip(g['res'], 52)
        sc = C.text(g['score'], 'tek', 60, WHITE, 800)
        yc = 88
        C.put(im, sc, x0, yc - sc.height / 2, anchor='tl')
        if g['note']:
            nt = C.text(g['note'], 'tek', 30, GRAY, 700, max_w=BW - x0 - sc.width - 90)
            C.put(im, nt, x0 + sc.width + 10, yc + sc.height / 2 - nt.height, anchor='tl')
        C.put(im, ch, BW - 18 - 26, yc)
        return im

    def _stat_block(self, lab, val, sub, col, vcol):
        im = self._plate(col)
        x0 = 34
        lb = C.text(lab, 'tek', 26, GRAY, 700, track=0.12, max_w=BW - x0 - 18)
        C.put(im, lb, x0, 36 - lb.height / 2, anchor='tl')
        v = C.text(val, 'tek', 64, vcol, 800, max_w=BW - x0 - 18)
        yc = 86
        C.put(im, v, x0, yc - v.height / 2, anchor='tl')
        if sub:
            room = BW - x0 - v.width - 14 - 16
            if room > 60:
                s = C.text(sub, 'tek', 28, GRAY, 600, max_w=room)
                C.put(im, s, x0 + v.width + 14, yc + v.height / 2 - s.height, anchor='tl')
        return im

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
        if not n:
            return []
        gap = 18
        w = int((980 - gap * (n - 1)) / n)
        out = []
        for lab, val in ext:
            if n <= 2:
                h = 66
                pl = C.rrect(w, h, 33, INK, 232, outline=C.mix(col, INK, 0.45), width=2)
                v = C.text(val, 'mont', 44, WHITE, 800)
                lb = C.text(lab, 'tek', 27, GRAY, 700, track=0.1, max_w=w - v.width - 76)
                tot = lb.width + 18 + v.width
                x = (w - tot) / 2
                C.put(pl, lb, x, h / 2 - lb.height / 2, anchor='tl')
                C.put(pl, v, x + lb.width + 18, h / 2 - v.height / 2, anchor='tl')
            else:
                h = 76
                pl = C.rrect(w, h, 22, INK, 232, outline=C.mix(col, INK, 0.45), width=2)
                C.put(pl, C.text(lab, 'tek', 22, GRAY, 700, track=0.1, max_w=w - 30), w / 2, 22)
                C.put(pl, C.text(val, 'mont', 34, WHITE, 800, max_w=w - 30), w / 2, 52)
            out.append(pl)
        return out

    def _team_data(self, key):
        tm = self.h if key == 'h' else self.a
        col = self.col[key]
        s = self.st[key]
        cx, cy, R = G_TEAM
        items = []
        blocks = [(self._game_block(g, col), i) for i, g in enumerate(s['games'][:3])]
        blocks += [(self._stat_block(lab, v, sub, col, vc), 3 + i) for i, (lab, v, sub, vc) in enumerate(self._stats(s)[:3])]
        for im, slot in blocks:
            bear = SLOTS[slot]
            sa, ca = math.sin(math.radians(bear)), -math.cos(math.radians(bear))
            bx, by = cx + SLOT_D * sa, cy + SLOT_D * ca
            if bear in (0, 180):                               # отметка — между выноской и центром
                ey = by + (BH / 2 if bear == 0 else -BH / 2)
                blip = (bx, ey + (28 if bear == 0 else -28))
                lead = (bx, ey, bx, blip[1])
            else:
                ex = bx + (-BW / 2 if sa > 0 else BW / 2)
                blip = (ex + (-26 if sa > 0 else 26), by)
                lead = (ex, by, blip[0], by)
            items.append(dict(img=im, pos=(bx, by), blip=blip, lead=lead, bear=bear, k=1.0 + 0.5 * slot))
        ext = self._extras(self.raw[key])
        pills = self._pills(ext, col)
        name = C.glow(C.text(tm.up, 'tek', 100, col, 900, max_w=1000), 14, 0.55, col)
        return dict(tm=tm, col=col, items=items, pills=pills, name=name, emb=self._emb(tm, 168, col, 18),
                    lab=self._bezel_lab('ХОЗЯЕВА' if key == 'h' else 'ГОСТИ', col), flash=self._flash(col),
                    dot=sprite('dot', 40, col), ring=self._dash_ring(col))

    def _dash_ring(self, col, rad=112):
        S = 2 * rad + 12
        im = Image.new('RGBA', (S * 2, S * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for i in range(36):
            if i % 3 == 2:
                continue
            a0 = i * 10
            d.arc((12, 12, S * 2 - 12, S * 2 - 12), a0, a0 + 7, fill=tuple(col) + (230,), width=6)
        return im.resize((S, S), Image.LANCZOS)

    def _jumps(self):
        """Прицел на поиске: половины долей, в последней доле — четверти; последний прыжок — на вторую цель."""
        D, u, pre = self.drop, self.u, self.pre
        ts = [D - pre * u + 0.5 * u * i for i in range(max(0, 2 * (pre - 1)))]
        ts += [D - u + 0.25 * u * i for i in range(4)]
        n = len(ts)
        return [(tj, self.other if (n - 1 - i) % 2 == 0 else self.side) for i, tj in enumerate(ts)]

    # ── время ──
    def geo(self, t):
        D, u = self.drop, self.u
        if t < self.t1:
            g = self.g_intro
            if t < 0.5:
                k = 0.86 + 0.14 * C.out_expo(C.seg(t, 0, 0.5))
                g = (g[0], g[1], g[2] * k)
        elif t < D:
            g = lerp3(self.g_intro, G_TEAM, C.out_expo(C.seg(t, self.t1, self.t1 + 0.5)))
        elif t < self.t_cta:
            g = lerp3(G_TEAM, G_PICK, C.out_expo(C.seg(t, D + 0.03, D + 0.6 * u)))
        else:
            g = lerp3(G_PICK, G_CTA, C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.5)))
        return g[0], g[1], int(round(g[2]))

    def tints(self, t):
        """(цвет A, цвет B, доля B) — экран меняет цвет на склейках за 0,25 с."""
        D = self.drop
        seq = [(self.t1, NEUT, self.col['h']), (self.t2, self.col['h'], self.col['a']), (self.tp, self.col['a'], NEUT),
               (D, NEUT, self.cf)]
        if t < self.t1:
            return NEUT, NEUT, 0.0
        for i, (t0, ca, cb) in enumerate(seq):
            t_next = seq[i + 1][0] if i + 1 < len(seq) else 1e9
            if t0 <= t < t_next:
                k = C.seg(t, t0, t0 + (0.12 if t0 == D else 0.25))
                return (ca, cb, k) if k < 1 else (cb, cb, 0.0)
        return self.cf, self.cf, 0.0

    def beam(self, t):
        """Пеленг луча (°) и скорость (°/с): в сцене команды на каждой половине доли луч проходит очередную выноску."""
        om = self.om
        if t < self.t2:
            return 180 + om * (t - self.t1), om
        if t < self.tp:
            return 180 + om * (t - self.t2), om
        if t < self.drop:
            return 180 + 2 * om * (t - self.tp), 2 * om
        return 90 + om * (t - self.drop), om

    def persist(self, t, bear):
        """Послесвечение отметки после прохода луча (1 — луч только что прошёл)."""
        ang, om = self.beam(t)
        return math.exp(-(((ang - bear) % 360) / om) / 0.5)

    def beat_pulse(self, t):
        if t < self.drop:
            return 0.0
        return math.exp(-(((t - self.drop) / self.u) % 1.0) * 7)

    # ── слои экрана ──
    def static_img(self, R, col):
        if (R, tuple(col)) in _ST:
            return _ST[(R, tuple(col))]
        src = max((k for k in _ST if k[1] == tuple(col)), key=lambda k: k[0], default=None)
        base = _ST[src] if src else scope(int(G_TEAM[2]), col)
        S = 2 * (R + PAD)
        return base.resize((S, S), Image.BILINEAR)

    def draw_scope(self, fr, t, cx, cy, R, a=1.0):
        ca, cb, k = self.tints(t)
        st = self.static_img(R, ca)
        if k > 0:
            st = Image.blend(st, self.static_img(R, cb), k)
        C.put(fr, st, cx, cy, a)
        col = C.mix(ca, cb, k)
        # луч развёртки
        ang, om = self.beam(t)
        th, rad = fields(R)
        strength = 0.85 if self.tp <= t < self.drop else 0.7
        if t < 0.5:
            strength *= C.seg(t, 0.1, 0.5)
        idx = (np.mod(math.radians(ang) - th, 2 * np.pi) * (_LUT_N / (2 * np.pi))).astype(np.int32) % _LUT_N
        al = SWEEP_LUT[idx] * rad * (255 * strength * a)
        n = 2 * R
        arr = np.empty((n, n, 4), np.uint8)
        arr[..., :3] = C.mix(col, WHITE, 0.15)
        arr[..., 3] = np.clip(al, 0, 255).astype(np.uint8)
        C.put(fr, Image.fromarray(arr, 'RGBA'), cx, cy)
        # эхо-импульсы
        act = [(t0, life, s) for t0, life, s in self.pulses if t0 <= t < t0 + life]
        if act:
            lay = Image.new('RGBA', (n, n), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            r0 = 0.3 * R if t >= self.drop else (0.21 * R if self.t1 <= t < self.tp else 0.06 * R)
            pc = C.mix(col, WHITE, 0.35)
            for t0, life, s in act:
                q = (t - t0) / life
                rr = r0 + (R - 8 - r0) * C.out_cubic(q)
                al = int(200 * s * a * (1 - q) ** 1.3)
                d.ellipse((R - rr - 7, R - rr - 7, R + rr + 7, R + rr + 7), outline=tuple(col) + (al // 4,), width=14)
                d.ellipse((R - rr, R - rr, R + rr, R + rr), outline=pc + (al,), width=4)
            C.put(fr, lay, cx, cy)
        return col

    def ping(self, fr, x, y, age, col, life=0.5, rmax=80):
        if not 0 <= age < life:
            return
        q = age / life
        r = 10 + rmax * C.out_cubic(q)
        S = int(2 * (rmax + 20))
        lay = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(lay).ellipse((S / 2 - r, S / 2 - r, S / 2 + r, S / 2 + r), outline=C.mix(col, WHITE, 0.4) + (int(230 * (1 - q) ** 1.2),),
                                    width=4)
        C.put(fr, lay, x, y)

    # ── сцены ──
    def intro(self, fr, t, cx, cy, R, a):
        q = C.out_expo(C.seg(t, 0.05, 0.4))
        C.put(fr, self.date, W / 2, TOP_Y + 18 * (1 - q), a * q)
        for side, sg, d0, bear in (('h', -1, 0.12, 270), ('a', 1, 0.26, 90)):
            x, y = cx + sg * 0.5 * R, cy - 34
            qe = C.out_back(C.seg(t, d0, d0 + 0.35), 1.6)
            if qe <= 0.01:
                continue
            fl = self.persist(t, bear) if t > d0 + 0.4 else 0.0
            C.put(fr, sprite('tbox', 200, NEUT), x, y, a * min(1.0, qe) * (0.45 + 0.55 * fl))
            C.put(fr, C.scale(self.i_emb[side], max(0.05, qe)), x, y, a * min(1.0, qe * 1.5))
            qp = C.out_expo(C.seg(t, d0 + 0.15, d0 + 0.55))
            C.put(fr, self.i_lab[side], x, cy + 128 + 20 * (1 - qp), a * qp)
            self.ping(fr, x, y, t - d0, NEUT, 0.55, 120)
        if self.odds is not None:
            q3 = C.out_expo(C.seg(t, 0.45, 0.9))
            yb = cy + R + 34
            C.put(fr, self.odds_lab, W / 2, yb + 52, a * q3)
            C.put(fr, self.odds, W / 2, yb + 52 + 40 + self.odds.height / 2 + 30 * (1 - q3), a * q3)

    def team(self, fr, t, key, t0, t_end, cx, cy, R):
        u = self.u
        T = self.T[key]
        col = T['col']
        sg = 1 if key == 'h' else -1
        a = 1 - C.seg(t, t_end - 0.12, t_end)
        q = C.out_expo(C.seg(t, t0, t0 + 0.35))
        C.put(fr, T['name'], W / 2 + sg * 90 * (1 - q), TOP_Y, a * q)
        C.put(fr, T['lab'], cx, cy - R - 18, a * C.seg(t, t0 + 0.1, t0 + 0.35))
        # центр: эмблема клуба и вращающееся пунктирное кольцо
        qe = C.out_back(C.seg(t, t0 + 0.04, t0 + 0.42), 1.6)
        if qe > 0.01:
            C.put(fr, C.rotate(T['ring'], -(t - t0) * 40), cx, cy, a * min(1.0, qe) * 0.85)
            C.put(fr, C.scale(T['emb'], max(0.05, qe) * (1 + 0.04 * math.exp(-((t - t0) / u % 1.0) * 6))), cx, cy, a * min(1.0, qe * 1.4))
        # отметки и выноски: засвечиваются лучом на половинах долей
        dl = ImageDraw.Draw(fr)
        for it in T['items']:
            tr = t0 + it['k'] * u
            if t < tr:
                continue
            fl = self.persist(t, it['bear'])
            qb = C.out_back(C.seg(t, tr, tr + 0.3), 1.5)
            al = a * min(1.0, C.seg(t, tr, tr + 0.12) * 1.0 + 0.0)
            lx0, ly0, lx1, ly1 = it['lead']
            dl.line((lx0, ly0, lx1, ly1), fill=tuple(col) + (int(200 * al),), width=3)
            C.put(fr, T['dot'], it['blip'][0], it['blip'][1], al * (0.55 + 0.45 * fl))
            self.ping(fr, it['blip'][0], it['blip'][1], t - tr, col, 0.5, 70)
            im = C.scale(it['img'], 0.7 + 0.3 * qb) if qb < 0.999 else it['img']
            C.put(fr, im, it['pos'][0], it['pos'][1], al)
            if fl > 0.03:
                C.put(fr, T['flash'], it['pos'][0], it['pos'][1], al * fl * 0.9)
        # под экраном: большинство / меньшинство / серия
        pills = T['pills']
        if pills:
            n = len(pills)
            gap = 18
            wtot = sum(p.width for p in pills) + gap * (n - 1)
            x = (W - wtot) / 2
            yb = cy + R + 34 + 12 + pills[0].height / 2 + 6
            for i, p in enumerate(pills):
                tr = t0 + (4.0 + 0.5 * i) * u
                if t >= tr:
                    qp = C.out_expo(C.seg(t, tr, tr + 0.3))
                    C.put(fr, p, x + p.width / 2, yb + 24 * (1 - qp), a * qp)
                x += p.width + gap

    def reticle_pos(self, t):
        cx, cy, _ = G_TEAM
        pos = {'h': (cx - HUNT_DX, cy), 'a': (cx + HUNT_DX, cy)}
        prev, cur, tj = None, None, None
        for tt, sd in self.jumps:
            if t >= tt:
                prev, cur, tj = cur, sd, tt
        if cur is None:
            return None, None, None
        p1 = pos[cur]
        p0 = pos[prev] if prev else p1
        k = C.out_expo(C.seg(t, tj, tj + 0.1))
        return (C.lerp(p0[0], p1[0], k), C.lerp(p0[1], p1[1], k)), cur, tj

    def hunt(self, fr, t, cx, cy, R):
        D, u = self.drop, self.u
        q = C.out_expo(C.seg(t, self.tp, self.tp + 0.35))
        C.put(fr, self.title, W / 2, TOP_Y + 16 * (1 - q), q)
        pos, cur, tj = self.reticle_pos(t)
        for side, sg, bear in (('h', -1, 270), ('a', 1, 90)):
            x = cx + sg * (HUNT_DX + 260 * (1 - q))
            fl = self.persist(t, bear)
            hit = math.exp(-(t - tj) / 0.12) if (cur == side and tj is not None) else 0.0
            C.put(fr, sprite('tbox', 250, NEUT), x, cy, q * (0.4 + 0.6 * max(fl, hit)))
            C.put(fr, C.scale(self.hunt_emb[side], 1 + 0.06 * hit), x, cy, q)
            C.put(fr, self.hunt_name[side], x, cy + 172, q)
        if pos is not None:
            sz = 300 + 30 * math.exp(-(t - tj) / 0.08)
            jit = C.seg(t, D - 0.25 * u, D)
            C.put(fr, sprite('reticle', int(sz // 4 * 4), AMBER, 6), pos[0] + 5 * jit * math.sin(t * 90), pos[1] + 5 * jit * math.cos(t * 70))

    def pick(self, fr, t, cx, cy, R):
        D, u = self.drop, self.u
        tc = self.t_cta
        k = C.out_expo(C.seg(t, D + 0.03, D + 0.6 * u))
        x0 = G_TEAM[0] + (HUNT_DX if self.side == 'a' else -HUNT_DX)
        y0 = G_TEAM[1]
        x, y = C.lerp(x0, cx, k), C.lerp(y0, cy, k)
        kc = C.in_out(C.seg(t, tc, tc + 0.5))
        s = C.lerp(HUNT_E / PICK_E, 1.0, k) * (1 - 0.16 * kc) * (1 + 0.035 * self.beat_pulse(t))
        C.put(fr, C.scale(self.p_emb, s), x, y)
        # прицел: защёлкивается ровно на дропе (сжатие от 1,6×), цвет клуба
        snap = 1 + 0.6 * (1 - C.out_expo(C.seg(t, D, D + 0.22)))
        rs = PICK_E * 1.32 * s * snap
        C.put(fr, sprite('reticle', int(rs // 4 * 4), C.mix(WHITE, self.cf, C.seg(t, D, D + 0.3)), 7), x, y)
        C.put(fr, self.p_lab, cx, cy - R - 18, C.seg(t, D + 0.25, D + 0.5))
        # текст прогноза
        dy = ((G_CTA[1] + G_CTA[2]) - (G_PICK[1] + G_PICK[2])) * kc
        yb = G_PICK[1] + G_PICK[2] + 34 + dy
        y1 = yb + 62
        bot = y1 + (92 if self.p_l1 is not None else 30) + 90 + (92 + 56 if self.kef is not None else 30)
        y1 -= max(0.0, bot - 1262) * kc                        # к плашке TG кэф над ней, а не под ней
        if self.p_l1 is not None:
            q1 = C.out_expo(C.seg(t, D + 0.06, D + 0.32))
            C.put(fr, C.scale(self.p_l1, 1.5 - 0.5 * q1), W / 2, y1, min(1.0, q1 * 2))
            y2 = y1 + 92
        else:
            y2 = y1 + 30
        q2 = C.out_expo(C.seg(t, D + 0.12, D + 0.42))
        C.put(fr, C.scale(self.p_l2, (1.6 - 0.6 * q2) * (1 + 0.02 * self.beat_pulse(t))), W / 2, y2, min(1.0, q2 * 2))
        y3 = y2 + 90
        if self.p_l3 is not None:
            q3 = C.out_expo(C.seg(t, D + 0.5 * u, D + 0.85 * u))
            C.put(fr, self.p_l3, W / 2, y3 + 24 * (1 - q3), q3)
        if self.kef is not None:
            q4 = C.out_back(C.seg(t, D + 1.0 * u, D + 1.35 * u), 1.8)
            if q4 > 0.01:
                C.put(fr, C.scale(self.kef, 0.5 + 0.5 * q4), W / 2, y3 + 92, min(1.0, q4 * 1.5))

    def shock(self, fr, t):
        """Ударная эхо-волна от выбранной цели на дропе."""
        dt = t - self.drop
        if not 0 <= dt < 1.1:
            return
        x0 = G_TEAM[0] + (HUNT_DX if self.side == 'a' else -HUNT_DX)
        y0 = G_TEAM[1]
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for lag, wd, al in ((0.0, 22, 240), (0.09, 9, 190), (0.2, 5, 140)):
            tt = dt - lag
            if tt <= 0:
                continue
            r = 40 + 2300 * (1 - math.exp(-2.4 * tt))
            a = int(al * max(0.0, 1 - tt / 1.0) ** 1.4)
            if a > 0:
                d.ellipse((x0 - r, y0 - r, x0 + r, y0 + r), outline=C.mix(self.cf, WHITE, 0.45) + (a,), width=wd)
                d.ellipse((x0 - r - wd * 2, y0 - r - wd * 2, x0 + r + wd * 2, y0 + r + wd * 2), outline=tuple(self.cf) + (a // 4,),
                          width=wd * 2)
        fr.alpha_composite(lay)

    # ── кадр ──
    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        cx, cy, R = self.geo(t)
        self.draw_scope(fr, t, cx, cy, R, C.seg(t, 0.0, 0.25) if t < 0.3 else 1.0)
        if t < self.t1:
            self.intro(fr, t, cx, cy, R, 1 - C.seg(t, self.t1 - 0.12, self.t1))
        elif t < self.t2:
            self.team(fr, t, 'h', self.t1, self.t2, cx, cy, R)
        elif t < self.tp:
            self.team(fr, t, 'a', self.t2, self.tp, cx, cy, R)
        elif t < D:
            self.hunt(fr, t, cx, cy, R)
        else:
            self.pick(fr, t, cx, cy, R)
            self.shock(fr, t)
        C.put(fr, self.tag, W / 2, TAG_Y, C.seg(t, 0, 0.3) * 0.95)
        ha = C.seg(t, 0.2, 0.5) * (1 - C.seg(t, self.t_cta, self.t_cta + 0.2))
        C.put(fr, self.handle_im, W / 2, HY, 0.9 * ha * C.HANDLE_BOTTOM)
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.05, self.t_cta + 0.5))
            C.put(fr, self.tg, W / 2, 1374 + 50 * (1 - q), q)
        # камера: толчки на склейках, наезд на поиске, удар на дропе, пульс на долях после дропа
        z, dx, dy, rot = 1.0, 0.0, 0.0, 0.0
        for th in (self.t1, self.t2, self.tp):
            if t >= th:
                z += 0.03 * (1 - C.seg(t, th, th + 0.3)) ** 2
            sx, sy = C.shake(t, th, 7, 0.25)
            dx, dy = dx + sx, dy + sy
        if self.tp <= t < D:
            q = C.seg(t, self.tp, D)
            z += 0.05 * C.in_cubic(q)
            dx += 6 * q * math.sin(t * 71)
            dy += 6 * q * math.cos(t * 53)
        if t >= D:
            kk = 1 - C.seg(t, D, D + 0.5)
            z += 0.09 * kk ** 2 + (0.01 * self.beat_pulse(t) if t < self.t_cta else 0)
            sx, sy = C.shake(t, D, 28, 0.5)
            dx, dy = dx + sx, dy + sy
            rot = 1.4 * kk ** 2 * math.sin((t - D) * 38)
        fr = C.zoom(fr.convert('RGB'), z, dx=dx, dy=dy, rot=rot)
        if D <= t < D + 0.2:
            fr = C.rgb_split(fr, 16 * (1 - C.seg(t, D, D + 0.2)))
        if D <= t < D + 0.38:
            fa = 1.0 if t < D + 1 / 30 else (1 - C.seg(t, D + 1 / 30, D + 0.38)) ** 1.5
            fr = Image.blend(fr.convert('RGB'), Image.new('RGB', fr.size, C.mix(WHITE, self.cf, 0.18)), 0.85 * fa)
        fr = C.vignette(fr, 0.42)
        return C.grain(fr, t, 4)
