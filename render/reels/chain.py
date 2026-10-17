# -*- coding: utf-8 -*-
"""«Цепь» — экспресс как цепь: каждое событие — стальное звено, замок защёлкивается на общем кэфе.

Сцены (u — доля трека, D — дроп):
  интро (0 … 3u)   — «ЭКСПРЕСС ДНЯ», число событий и дата, сверху крюк;
  звенья           — на каждое событие 2 доли: звено влетает сбоку, качается и со звоном (искры) повисает на цепи
                     ровно на доле; внутри звена — матч, эмблемы, ставка, кэф и короткий довод;
  итог             — снизу висит открытый замок, на нём кэф перемножается от первого события к итогу;
  перед дропом     — замок светится, «ЗАМЫКАЕМ?»;
  ДРОП             — дужка защёлкивается, сноп искр, итоговый кэф золотом.
legs — [(хозяева, гости, лига, ставка, кэф, довод, время МСК)] (2–3 события).
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import parts as P
from reels.core import W, H

STEEL = [(0, (40, 44, 52)), (.45, (120, 128, 142)), (.75, (200, 206, 218)), (1, (250, 252, 255))]
BRASS = [(0, (90, 60, 14)), (.45, (196, 146, 52)), (.75, (240, 200, 110)), (1, (255, 240, 190))]
ORANGE = (255, 150, 40)
LW, LH, TH = 940, 330, 44      # звено события
GAPY = 352                     # шаг звеньев


def ramp(v, stops):
    return np.stack([np.interp(v, [s[0] for s in stops], [s[1][i] for s in stops]) for i in range(3)], -1)


def ring(w, h, th, stops=STEEL, vertical=False):
    """Звено-«стадион»: трубка толщиной th с бликом сверху слева."""
    def make():
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        px, py = x - w / 2, y - h / 2
        if vertical:
            px, py = py, px
            Lx, R = (h - w) / 2, w / 2 - th / 2
        else:
            Lx, R = (w - h) / 2, h / 2 - th / 2
        qx = np.clip(px, -Lx, Lx)
        dx, dy = px - qx, py
        dist = np.hypot(dx, dy) + 1e-6
        n = (dist - R) / (th / 2)
        m = np.clip((1 - np.abs(n)) * th / 2, 0, 1)
        ny = dy / dist if not vertical else dx / dist
        v = np.sqrt(np.clip(1 - n ** 2, 0, 1)) * (0.62 - 0.38 * ny) + 0.25 * (n < 0)
        rgb = ramp(np.clip(v, 0, 1), stops)
        return Image.fromarray(np.dstack([rgb, m * 255]).astype(np.uint8), 'RGBA')
    return P.cached(('ring', w, h, th, stops is BRASS, vertical), make)


def sparks(t, t0, x, y, n=46, seed=1, spread=1.0):
    """Искры от удара в t0 (детерминированно)."""
    if t < t0 or t > t0 + 0.9:
        return None
    rnd = random.Random(seed)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    dt = t - t0
    for _ in range(n):
        a = rnd.uniform(-math.pi, 0) if rnd.random() < 0.8 else rnd.uniform(0, math.pi)
        v = rnd.uniform(400, 1300) * spread
        life = rnd.uniform(0.35, 0.85)
        if dt > life:
            continue
        sx, sy = x + math.cos(a) * v * dt, y + math.sin(a) * v * dt + 1400 * dt * dt
        tx, ty = sx - math.cos(a) * 26, sy - math.sin(a) * 26 - 30 * dt
        k = 1 - dt / life
        d.line((tx, ty, sx, sy), fill=(255, int(170 + 80 * k), int(60 * k), int(255 * k)), width=4)
    g = lay.filter(ImageFilter.GaussianBlur(5))
    g.alpha_composite(lay)
    return g


class Chain(C.Reel):
    def __init__(self, legs, title, date, u=60 / 67, drop=None, seed=12):
        n = len(legs)
        drop = drop if drop is not None else (3 + 2 * n + 3) * u
        super().__init__(u, drop, seed)
        self.legs = []
        for hh, aa, lg, bet, k, why, tm in legs:
            h, a = C.match(hh, aa, lg)
            self.legs.append((h, a, lg, bet, k, why, tm))
        self.title, self.date = title, date
        self.total = 1.0
        for lg in self.legs:
            self.total *= lg[4]
        self.T1 = 3 * u
        self.land = [self.T1 + (2 * i + 1) * u for i in range(n)]
        self.dur = drop + 6 * u
        self.cover_t = drop + 3 * u
        top = 575 if n == 2 else 520
        gap = GAPY if n == 2 else 300
        self.ys = [top + i * gap for i in range(n)]
        self.lock_y = self.ys[-1] + LH / 2 + 160

    def _plate(self, i):
        h, a, lg, bet, k, why, tm = self.legs[i]
        def make():
            pw, ph = LW - 2 * TH - 40, LH - 2 * TH - 30
            pl = C.rrect(pw, ph, 22, (16, 17, 22), 245, outline=(70, 74, 84), width=2)
            for j, t_ in enumerate((h, a)):
                C.put(pl, t_.emb(66), 52 + j * 74, 48)
            C.put(pl, C.text('%s — %s' % (h.up, a.up), 'osw', 36, (235, 238, 245), 700, max_w=pw - 360), 176, 18, anchor='tl')
            C.put(pl, C.text(tm, 'mont', 21, (160, 166, 180), 700, track=0.1), 178, 64, anchor='tl')
            C.put(pl, C.text(bet, 'osw', 46, (255, 210, 120), 700, max_w=pw - 240), 30, 100, anchor='tl')
            C.put(pl, C.text(why, 'mont', 22, (190, 196, 210), 700, max_w=pw - 240), 32, 166, anchor='tl')
            kb = C.rrect(176, 112, 20, (255, 196, 61))
            C.put(kb, C.text('×' + C.fmt_k(k), 'osw', 56, (24, 18, 6), 700, max_w=156), 88, 58)
            C.put(pl, kb, pw - 108, ph - 70)
            return pl
        return P.cached(('ch_plate', i), make)

    def _link(self, i):
        def make():
            im = ring(LW, LH, TH).copy()
            C.put(im, self._plate(i), LW / 2, LH / 2)
            return im
        return P.cached(('ch_link', i), make)

    def _lock(self, val, closed):
        def make():
            w, h = 380, 250
            im = Image.new('RGBA', (w, h + 210), (0, 0, 0, 0))
            sh = ring(200, 300, 38, BRASS, vertical=True)
            im.alpha_composite(sh.crop((0, 0, 200, 190)), ((w - 200) // 2, 40 if closed else 0))
            y = np.linspace(0, 1, h, dtype=np.float32)
            body = Image.fromarray(np.broadcast_to(ramp(1 - y * 0.8, BRASS)[:, None, :], (h, w, 3)).astype(np.uint8)).convert('RGBA')
            body.putalpha(C.rrect(w, h, 40, (255, 255, 255)).getchannel('A'))
            im.alpha_composite(body, (0, 210))
            C.put(im, C.text('ИТОГО', 'mont', 26, (60, 40, 8), 900, track=0.3), w / 2, 210 + 56)
            C.put(im, C.text(val, 'osw', 96, (40, 26, 4), 700, max_w=w - 40), w / 2, 210 + 150)
            C.put(im, C.ellipse(30, 30, (60, 40, 10)), w / 2, 210 + 218)
            return im
        return P.cached(('ch_lock', val, closed), make)

    def frame(self, t):
        u, D = self.u, self.drop
        fr = P.vbg((22, 20, 22), (8, 7, 8), glow=(80, 40, 12), glow_xy=(W / 2, 1300), glow_r=700, glow_k=0.35).convert('RGBA')
        P.header(fr, 'NHL' if all(lg[2].upper() == 'NHL' for lg in self.legs) else 'KHL', self.date, acc=ORANGE)
        n = len(self.legs)
        # заголовок
        ttl = P.cached(('ch_ttl',), lambda: C.text(self.title, 'osw', 78, (245, 240, 232), 700, max_w=W - 120))
        if t < self.T1:
            C.put(fr, ttl, W / 2, 470, a=C.clamp(t / 0.35))
            sub = P.cached(('ch_sub',), lambda: C.text('%d %s' % (n, 'СОБЫТИЯ' if n < 5 else 'СОБЫТИЙ'), 'mont', 34,
                                                      ORANGE, 800, track=0.3))
            C.put(fr, sub, W / 2, 560, a=C.clamp((t - 0.3) / 0.35))
        # звенья
        for i in range(n):
            tl = self.land[i]
            if t < tl - u:
                continue
            x, y, rot = W / 2, self.ys[i], 0.0
            if t < tl:                                            # влетает сбоку
                k = C.out_cubic(C.clamp((t - (tl - u)) / u))
                sgn = -1 if i % 2 == 0 else 1
                x = W / 2 + sgn * (1 - k) * 1100
                y = self.ys[i] - (1 - k) * 160
                rot = sgn * (1 - k) * 25
            else:                                                 # качается после удара
                x0 = t - tl
                rot = 3.5 * math.exp(-x0 * 3) * math.sin(x0 * 9) * (1 if i % 2 else -1)
            if i > 0 and t >= tl - 0.4 * u:                       # соединительное звено
                cy = (self.ys[i - 1] + LH / 2 + y - LH / 2) / 2
                C.put(fr, ring(84, 150, 24, vertical=True), (W / 2 + x) / 2, cy)
            C.put(fr, C.rotate(self._link(i), rot), x, y)
        for i in range(n):
            sp = sparks(t, self.land[i], W / 2 + (-300 if i % 2 == 0 else 300), self.ys[i] - LH / 2 + 10, seed=10 + i)
            if sp is not None:
                fr.alpha_composite(sp)
        # замок: кэф перемножается после последнего звена
        t_mul = self.land[-1] + 0.3 * u
        if t >= t_mul:
            prod, steps = 1.0, []
            for lg in self.legs:
                prod *= lg[4]
                steps.append(prod)
            j = min(n - 1, int((t - t_mul) / (0.5 * u)))
            val = '×' + C.fmt_k(steps[j] if t < D else self.total)
            closed = t >= D
            lk = self._lock(val, closed)
            yy = self.lock_y + (0 if closed else -0) + (C.out_back(C.clamp((t - t_mul) / 0.4)) - 1) * 300
            if closed:
                lk = C.glow(lk, 22, 1.2 + 0.8 * max(0, 1 - (t - D) / (2 * u)), (255, 200, 90))
            elif t > D - u:
                lk = C.glow(lk, 16, 0.8 + 0.6 * (int(t * 8) % 2), (255, 180, 60))
            C.put(fr, lk, W / 2, yy)
        if D - u < t < D:
            q = P.cached(('ch_q',), lambda: C.text('ЗАМЫКАЕМ?', 'osw', 64, ORANGE, 700))
            C.put(fr, q, W / 2, 378)
        if t >= D:
            sp = sparks(t, D, W / 2, self.lock_y - 100, n=90, seed=99, spread=1.3)
            if sp is not None:
                fr.alpha_composite(sp)
            lab = P.cached(('ch_fin',), lambda: C.text('%s · КЭФ %s' % (self.title, C.fmt_k(self.total)), 'osw', 62,
                                                      (255, 214, 120), 700, max_w=W - 100))
            C.put(fr, lab, W / 2, 378, a=C.clamp((t - D) / 0.25))
            fr = P.flash(fr, max(0.0, 1 - (t - D) / 0.22) * 0.6, (255, 220, 160))
        return P.finish(fr, t, 7)
