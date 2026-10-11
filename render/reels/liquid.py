# -*- coding: utf-8 -*-
"""«Жидкость» — глянцевые капли (метаболы) в цветах клубов.

До дропа у каждой команды своя капля из нескольких шаров: они перетекают и пульсируют на доли, внутри — эмблема.
На дропе капли летят друг к другу и сливаются; капля фаворита поглощает соперника (его шары тают, цвет растворяется).
Дальше — большая капля фаворита с эмблемой, прогноз, линия, шанс и подписка. Блик и объём — по нормалям поля.
"""
import math

import numpy as np
from PIL import Image, ImageFilter

from reels import core as C
from reels import fresh as F
from reels.core import H, W

S = 4                      # поле считаем в 4 раза мельче кадра
LW, LH = W // S, H // S


def _sm(a, b, x):
    k = np.clip((x - a) / (b - a), 0, 1)
    return k * k * (3 - 2 * k)


class Liquid(C.Reel):
    def __init__(self, m, u=1.0, drop=3.0, seed=23):
        super().__init__(u, drop, seed)
        self.m = m
        self.h, self.a = C.match(m['home'], m['away'], m['league'])
        self.fav_h = m['side'] == 'h'
        self.fav = self.h if self.fav_h else self.a
        self.ch = np.array(F.club(self.h), np.float32)
        self.ca = np.array(F.club(self.a), np.float32)
        rng = np.random.default_rng(seed)
        self.balls = []                    # (команда 0/1, радиус, орбита, скорость, фаза)
        for team in (0, 1):
            for i in range(5):
                self.balls.append((team, rng.uniform(70, 120), rng.uniform(20, 75), rng.uniform(0.6, 1.3) * rng.choice([-1, 1]),
                                   rng.uniform(0, 2 * math.pi)))
        D = drop
        self.t_merge = D
        self.t_pick = D + 2 * u
        self.t_chance = D + 4 * u
        self.t_cta = D + 7 * u
        self.dur = D + 11 * u
        self.cover_t = D + 9 * u
        y, x = np.mgrid[0:LH, 0:LW].astype(np.float32)
        self.gx, self.gy = x * S + S / 2, y * S + S / 2
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - 760) / H) ** 2)
        self.bg = np.stack([14 + 16 * (1 - d), 14 + 16 * (1 - d), 20 + 22 * (1 - d)], -1).astype(np.float32)
        self.e_small = (self.h.emb(230), self.a.emb(230))
        self.e_big = self.fav.emb(360)

    def _layout(self, t):
        """Центр и масштаб радиусов каждой команды в момент t."""
        u, D = self.u, self.drop
        beat = 0.5 + 0.5 * math.cos(2 * math.pi * ((t - D) / u))
        k = C.in_out(C.seg(t, D - 0.1, D + 1.4 * u))
        ch = (300 + (540 - 300) * k, 820 + (680 - 820) * k)
        ca = (780 + (540 - 780) * k, 820 + (680 - 820) * k)
        grow = 1 + 0.42 * C.out_cubic(C.seg(t, D, D + 2 * u))
        melt = 1 - C.in_out(C.seg(t, D + 0.3 * u, D + 2.2 * u))
        sh = (grow if self.fav_h else melt) * (1 + 0.06 * beat)
        sa = (melt if self.fav_h else grow) * (1 + 0.06 * beat)
        return (ch, ca), (sh, sa), k

    def _field(self, t):
        (ch, ca), (sh, sa), k = self._layout(t)
        fh = np.zeros((LH, LW), np.float32)
        fa = np.zeros((LH, LW), np.float32)
        for team, r, orb, sp, ph in self.balls:
            c, sc = (ch, sh) if team == 0 else (ca, sa)
            if sc <= 0.01:
                continue
            o = orb * (1 - 0.4 * k)
            bx = c[0] + o * math.cos(sp * t * 1.6 + ph)
            by = c[1] + o * 1.3 * math.sin(sp * t * 1.3 + ph)
            rr = r * sc
            f = rr * rr / ((self.gx - bx) ** 2 + (self.gy - by) ** 2 + 30.0)
            if team == 0:
                fh += f
            else:
                fa += f
        return fh, fa

    def frame(self, t):
        u, D = self.u, self.drop
        fh, fa = self._field(t)
        f = fh + fa
        wh = fh / (f + 1e-6)
        col = self.ch[None, None, :] * wh[..., None] + self.ca[None, None, :] * (1 - wh[..., None])
        gy, gx = np.gradient(f)
        n = np.stack([-gx * 6, -gy * 6, np.ones_like(f)], -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        L = np.array([-0.45, -0.6, 0.66], np.float32)
        L /= np.linalg.norm(L)
        Hh = L + np.array([0, 0, 1], np.float32)
        Hh /= np.linalg.norm(Hh)
        diff = np.clip(n @ L, 0, 1)
        spec = np.clip(n @ Hh, 0, 1) ** 60
        rim = (1 - n[..., 2]) ** 2
        rgb = col * (0.35 + 0.75 * diff[..., None]) + 255 * (spec[..., None] * 0.9 + rim[..., None] * 0.18)
        alpha = _sm(0.9, 1.1, f)
        small = np.concatenate([np.clip(rgb, 0, 255), alpha[..., None] * 255], -1).astype(np.uint8)
        blob = Image.fromarray(small, 'RGBA').resize((W, H), Image.BICUBIC)
        glow_col = Image.fromarray(np.clip(col * alpha[..., None], 0, 255).astype(np.uint8), 'RGB')
        glow = np.asarray(glow_col.filter(ImageFilter.GaussianBlur(14)).resize((W, H), Image.BILINEAR), np.float32)
        base = self.bg + glow * 0.45
        fl = max(0.0, 1 - abs(t - D) / 0.22) if t >= D - 0.05 else 0.0
        base = base + (np.array(F.bright(F.club(self.fav), 0.3), np.float32) * 0.35 + 20) * fl
        fr = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        fr.alpha_composite(blob)
        m = self.m
        (ch, ca), (sh, sa), k = self._layout(t)
        # эмблемы: до слияния — у каждой капли; потом — большая эмблема фаворита
        if t < D + 0.6 * u:
            a = 1 - C.seg(t, D, D + 0.6 * u)
            for e, c, sc in ((self.e_small[0], ch, sh), (self.e_small[1], ca, sa)):
                if sc > 0.05:
                    C.put(fr, C.with_shadow(C.scale(e, 0.92 + 0.08 * sc), 10, 0.45, 8), c[0], c[1], a)
        else:
            q = C.out_back(C.seg(t, D + 0.6 * u, D + 1.4 * u))
            if q > 0:
                C.put(fr, C.with_shadow(C.scale(self.e_big, max(0.05, q)), 14, 0.5, 10), W / 2, 680)
        F.header(fr, m, C.seg(t, 0.2, 0.8) * 0.9)
        if t < D:
            a = C.seg(t, 0.3, 0.9) * (1 - C.seg(t, D - 0.25, D))
            C.put(fr, C.text('%s — %s' % (self.h.up, self.a.up), 'unb', 64, (255, 255, 255), 900, max_w=960), W / 2, 470, a)
            C.put(fr, C.text('%s · %s МСК' % (F.lg_ru(m), m['when']), 'mono', 36, (190, 195, 210), 600, track=0.12), W / 2, 545, a)
            C.put(fr, C.text('КТО КОГО ПОГЛОТИТ?', 'unb', 50, (255, 255, 255), 900), W / 2, 1180,
                  C.seg(t, D - 2.2 * u, D - 1.8 * u) * (1 - C.seg(t, D - 0.2, D)))
        if t >= self.t_pick:
            q = C.out_expo(C.seg(t, self.t_pick, self.t_pick + 0.5))
            C.put(fr, C.text('НАШ ПРОГНОЗ', 'mono', 34, (200, 205, 220), 700, track=0.3), W / 2, 1012, q)
            C.put(fr, C.text(m['pick'], 'unb', 66, (255, 255, 255), 900, max_w=960), W / 2, 1078 + 30 * (1 - q), q)
            if m.get('line'):
                C.put(fr, C.text('ЛИНИЯ (ОСН. ВРЕМЯ)  ' + F.line_text(m), 'mono', 30, (175, 180, 200), 600, max_w=1000),
                      W / 2, 1146, C.seg(t, self.t_pick + 0.8 * u, self.t_pick + 1.2 * u))
        if t >= self.t_chance:
            q = C.out_expo(C.seg(t, self.t_chance, self.t_chance + 0.6))
            num = C.text('%d%%' % m['chance'], 'unb', 150, F.bright(F.club(self.fav), 0.4), 900)
            C.put(fr, C.glow(num, 16, 0.8), W / 2, 1245, q)
            C.put(fr, C.text('НАША ОЦЕНКА ШАНСА · С УЧЁТОМ ОТ', 'mono', 30, (200, 205, 220), 700, track=0.12, max_w=980),
                  W / 2, 1335, C.seg(t, self.t_chance + 0.3, self.t_chance + 0.7) * (1 - C.seg(t, self.t_cta - 0.2, self.t_cta)))
        F.cta(fr, t, self.t_cta, y=1400)
        z = 1.0 + 0.015 * math.sin(t * 0.5)
        dx, dy = C.shake(t, D, 10, 0.3)
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        return C.grain(fr, t, 3)
