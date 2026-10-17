# -*- coding: utf-8 -*-
"""«Табло» — прогноз на светодиодном табло арены (джамботрон).

Содержимое рисуется в разрешении табло 96×104 «лампочки» и выводится круглыми светодиодами с шагом 10 px
(погасшие — тусклые точки), со свечением; вокруг — тёмная арена с огнями трибун, сверху — бегущая LED-лента.
До дропа — бегущая строка «ИГРА ДНЯ» и бегущие огни по краю; на дропе — салют лучами в цветах клубов,
эмблемы «лампочками» и VS; дальше — названия на половинках цветов клубов, время, «ПРОГНОЗ», огромное «П1»,
бегущей строкой — прогноз, мигающий кэф; в конце — «ПОДПИШИСЬ · @JARVIBET».
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels.core import W, H
from reels.pixel import ptext, pix_emblem

P = 10
LW_, LH_ = 96, 104
AMBER = (255, 170, 30)
WHITE = (255, 255, 255)
X0, Y0 = (W - LW_ * P) // 2, 400


class Led(C.Reel):
    def __init__(self, home, away, league, short_pick, pick, coef, when, u=60 / 96.5, drop=2.49, seed=19):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.short_pick, self.pick, self.coef, self.when = short_pick, pick, coef, when
        self.league = 'НХЛ' if str(league).upper() == 'NHL' else 'КХЛ'
        self.dur = self.b(24)
        self.cover_t = self.b(12) + 0.45
        self._prep()

    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        # маска светодиода
        yy, xx = np.mgrid[0:P, 0:P].astype(np.float32)
        d = np.sqrt((xx - P / 2 + 0.5) ** 2 + (yy - P / 2 + 0.5) ** 2)
        m = np.clip(4.3 - d, 0, 1)
        self.mask = np.tile(m, (LH_, LW_))[..., None].astype(np.float32)
        # арена
        bg = C.vgrad(W, H, [(0, (6, 6, 12)), (0.5, (12, 10, 22)), (1, (4, 4, 8))]).convert('RGBA')
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        for _ in range(160):
            x, y = rnd.uniform(0, W), rnd.uniform(1200, H)
            r = rnd.uniform(4, 18)
            col = [(255, 200, 120), (120, 180, 255), (255, 255, 255), (255, 90, 90)][int(rnd.integers(0, 4))]
            dl.ellipse((x - r, y - r, x + r, y + r), fill=col + (int(rnd.uniform(40, 140)),))
        bg.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6)))
        # корпус табло
        frame = C.rrect(LW_ * P + 60, LH_ * P + 60, 18, (26, 26, 32))
        inner = C.rrect(LW_ * P + 20, LH_ * P + 20, 8, (4, 4, 6))
        C.put(frame, inner, frame.width / 2, frame.height / 2)
        for x in (14, frame.width - 14):
            for y in range(30, frame.height - 20, 120):
                C.put(frame, C.ellipse(10, 10, (90, 90, 100)), x, y)
        bg.alpha_composite(frame, (X0 - 30, Y0 - 30))
        self.bg = bg
        self.pe = {k: pix_emblem(t, 40) for k, t in (('h', self.h), ('a', self.a))}
        self.ribbon_txt = ptext('  JARVIS · ПРОГНОЗЫ НА ХОККЕЙ · %s · %s — %s ·' % (C.HANDLE.upper(), self.h.up, self.a.up), 8, AMBER, None)

    # ── содержимое табло ──
    def chaser(self, d, t, col=AMBER):
        n = int(t * 12)
        per = []
        for x in range(0, LW_, 2):
            per.append((x, 0))
        for y in range(0, LH_, 2):
            per.append((LW_ - 1, y))
        for x in range(LW_ - 1, -1, -2):
            per.append((x, LH_ - 1))
        for y in range(LH_ - 1, -1, -2):
            per.append((0, y))
        for i, (x, y) in enumerate(per):
            if (i + n) % 4 == 0:
                d.point((x, y), fill=col + (255,))

    def marquee(self, im, s, y, t, speed=40, size=8, col=AMBER):
        tx = ptext(s + '   ', size, col, None)
        off = int(t * speed) % tx.width
        x = -off
        while x < LW_:
            C.put(im, tx, x, y, anchor='tl')
            x += tx.width

    def content(self, t):
        u, D = self.u, self.drop
        b = self.b
        im = Image.new('RGBA', (LW_, LH_), (0, 0, 0, 255))
        d = ImageDraw.Draw(im)
        d.fontmode = '1'
        if t < D:
            self.marquee(im, 'ИГРА ДНЯ ★ ИГРА ДНЯ ★', 20, t, 46, 16, AMBER)
            if int(t / (u / 2)) % 2 == 0:
                C.put(im, self.pe['h'].resize((30, 30), Image.NEAREST), 26, 66)
                C.put(im, self.pe['a'].resize((30, 30), Image.NEAREST), LW_ - 26, 66)
            C.put(im, ptext('VS', 8, WHITE, None), LW_ / 2, 66)
            self.chaser(d, t)
        elif t < b(4):
            k = C.seg(t, D, D + 2 * u)
            for i in range(24):                                   # салют лучами
                a = i * math.pi / 12 + t * 0.6
                r0, r1 = 6 + 50 * k, 12 + 70 * k
                col = self.h.c1 if i % 2 == 0 else self.a.c1
                d.line((LW_ / 2 + r0 * math.cos(a), LH_ / 2 + r0 * math.sin(a), LW_ / 2 + r1 * math.cos(a), LH_ / 2 + r1 * math.sin(a)),
                       fill=tuple(col) + (255,), width=2)
            p = C.out_cubic(C.seg(t, D + 0.2, D + 0.6))
            C.put(im, self.pe['h'], 26 - (1 - p) * 60, 40)
            C.put(im, self.pe['a'], LW_ - 26 + (1 - p) * 60, 64)
            if int(t / (u / 2)) % 2 == 0:
                C.put(im, ptext('VS', 16, WHITE, None), LW_ / 2, 52)
        elif t < b(8):
            d.rectangle((0, 0, LW_, LH_ / 2), fill=tuple(int(c * 0.8) for c in self.h.c1) + (255,))
            d.rectangle((0, LH_ / 2, LW_, LH_), fill=tuple(int(c * 0.8) for c in self.a.c1) + (255,))
            for k, (tm, y) in enumerate(((self.h, 26), (self.a, 78))):
                tx = ptext(tm.up, 16 if len(tm.up) * 16 <= LW_ - 4 else 8, WHITE, (0, 0, 0))
                q = C.out_cubic(C.seg(t, b(4) + k * u, b(4) + k * u + 0.3))
                C.put(im, tx, LW_ / 2 + (1 - q) * 100 * (1 if k else -1), y)
            C.put(im, ptext('VS', 8, AMBER, (0, 0, 0)), LW_ / 2, LH_ / 2)
        elif t < b(12):
            C.put(im, ptext(self.league, 16, AMBER, None), LW_ / 2, 16)
            dd = self.when.split('·')
            day = dd[0].strip().split()
            C.put(im, ptext(day[-1], 16, WHITE, None), LW_ / 2, 42)
            C.put(im, ptext(' '.join(day[:-1] + [dd[1].strip()] if len(dd) > 1 else day[:-1]), 8, WHITE, None), LW_ / 2, 62)
            if int(t / (u / 2)) % 2 == 0:
                C.put(im, ptext('ПРОГНОЗ', 8, (60, 255, 120), None), LW_ / 2, 86)
            self.chaser(d, t, (60, 255, 120))
        elif t < b(18):
            k = C.out_back(C.seg(t, b(12), b(12) + 0.3), 2.0)
            big = ptext(self.short_pick, 32, AMBER, (120, 40, 0))
            C.put(im, C.scale(big, max(0.1, k), Image.NEAREST), LW_ / 2, 30)
            self.marquee(im, self.pick.upper() + ' ★', 60, max(0.0, t - b(12) - 0.7), 44, 16, WHITE)   # строка сначала стоит
            if int(t / (u / 2)) % 2 == 0 or t < b(14):
                C.put(im, ptext('КЭФ ' + C.fmt_k(self.coef), 8, (60, 255, 120), None), LW_ / 2, 92)
        else:
            C.put(im, ptext('ПОДПИШИСЬ', 8, WHITE, None), LW_ / 2, 14)
            ic = C.tg_icon(36).resize((30, 30), Image.NEAREST)
            C.put(im, ic, LW_ / 2, 44)
            self.marquee(im, C.HANDLE.upper() + ' · TELEGRAM ·', 72, t - b(18), 40, 16, C.TG_BLUE)
            self.chaser(d, t, C.TG_BLUE)
        return im

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        c = np.asarray(self.content(t).convert('RGB'), np.float32)
        big = np.repeat(np.repeat(c, P, 0), P, 1)
        big = np.maximum(big, 24.0)
        ledim = big * self.mask
        panel = Image.fromarray(np.clip(ledim, 0, 255).astype(np.uint8), 'RGB')
        glow = panel.resize((LW_ * P // 4, LH_ * P // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize(panel.size, Image.BILINEAR)
        panel = Image.fromarray(np.clip(np.asarray(panel, np.float32) + np.asarray(glow, np.float32) * 0.8, 0, 255).astype(np.uint8))
        fr.paste(panel, (X0, Y0))
        # свет табло на арену
        avg = tuple(int(v) for v in c.reshape(-1, 3).mean(0))
        fr = C.add_light(fr, C.radial(1400, 700, avg, 255, 1.4), W / 2, Y0 + LH_ * P + 300, 0.9)
        # LED-лента сверху
        rib = Image.new('RGBA', (W // 6, 14), (0, 0, 0, 255))
        off = int(t * 30) % self.ribbon_txt.width
        x = -off
        while x < rib.width:
            C.put(rib, self.ribbon_txt, x, 2, anchor='tl')
            x += self.ribbon_txt.width
        rc = np.asarray(rib.convert('RGB'), np.float32)
        rb = np.maximum(np.repeat(np.repeat(rc, 6, 0), 6, 1), 20.0)
        ym, xm = np.mgrid[0:6, 0:6].astype(np.float32)
        rm = np.clip(2.6 - np.sqrt((xm - 2.5) ** 2 + (ym - 2.5) ** 2), 0, 1)
        rb = rb * np.tile(rm, (14, W // 6))[..., None]
        fr.paste(Image.fromarray(np.clip(rb, 0, 255).astype(np.uint8)), (0, 262))
        # удары
        z = 1.0
        dx = dy = 0.0
        for n in range(0, 24, 2):
            th = self.b(n)
            if t >= th:
                z += 0.018 * (1 - C.seg(t, th, th + 0.25)) ** 2
        sx, sy = C.shake(t, D, 14, 0.35)
        fr = C.zoom(fr, z, dx=sx, dy=sy)
        if D <= t < D + 0.15:
            fr = Image.blend(fr.convert('RGB'), Image.new('RGB', (W, H), (255, 240, 220)), 0.6 * (1 - C.seg(t, D, D + 0.15)))
        return C.vignette(fr, 0.4)
