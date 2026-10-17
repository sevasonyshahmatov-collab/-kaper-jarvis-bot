# -*- coding: utf-8 -*-
"""Серия 4 · «Гроза» (DOOMSDAY). Чёрно-белое ночное небо, тяжёлые облака подсвечиваются вспышками (как в образце
владельца). Каждая сцена открывается ударом молнии: матч и линия → команда 1 → команда 2 → нарастающие зарницы →
на дропе удар через весь кадр в эмблему команды из прогноза, белая вспышка, прогноз и кэф → Telegram.
"""
import math

import numpy as np
from PIL import Image, ImageFilter

from reels import core as C
from reels import form as F
from reels import s4
from reels.premium import add_rgb, bolt_layer

W, H = C.W, C.H
SILVER = (228, 230, 236)
GRAY = (150, 152, 160)


class Storm(s4.Base):
    STYLE = dict(font='mont', title='osw', ink=(240, 240, 244), sub=(160, 162, 170), accent=SILVER, panel=(8, 8, 10),
                 panel_a=200, line=(255, 255, 255), line_a=46, radius=18)

    def __init__(self, *a, **kw):
        super().__init__(*a, seed=31, **kw)
        rng = np.random.default_rng(11)
        n = np.zeros((H // 8, (W + 400) // 8), np.float32)
        for k in (1, 2, 4, 8):
            g = rng.random((H // (200 // k) + 2, (W + 400) // (200 // k) + 2)).astype(np.float32)
            n += np.asarray(Image.fromarray(g).resize((n.shape[1], n.shape[0]), Image.BICUBIC)) / k
        n = (n - n.min()) / (n.max() - n.min())
        self.clouds = Image.fromarray((n ** 1.5 * 255).astype(np.uint8)).resize((W + 400, H), Image.BICUBIC) \
            .filter(ImageFilter.GaussianBlur(26))
        self.sky = C.vgrad(W, H, [(0, (10, 10, 11)), (0.55, (6, 6, 7)), (1, (2, 2, 2))]).convert('RGBA')
        self.small = [bolt_layer(s, x0, x1, 700) for s, x0, x1 in ((3, 240, 470), (7, 880, 610), (21, 120, 420), (33, 990, 700))]
        fx = 540
        self.strike = bolt_layer(99, 600, fx, 420)                    # удар в эмблему сцены (верх кадра → эмблема)
        self.big = bolt_layer(55, 520, fx, 520)
        self.big2 = bolt_layer(77, 140, 360, 900)
        u, D = self.u, self.drop
        hits = [(self.b(-k), k % 4) for k in range(2, int(D / u) + 1, 2) if self.b(-k) < self.t1]      # интро: раз в 2 доли
        hits += [(self.t1, 's'), (self.t2, 's')]                                                      # удар на сцене
        hits += [(t0, k % 4) for k, t0 in enumerate([self.t1 + 4 * u * i for i in range(1, self.bt['team'] // 4)] +
                                                    [self.t2 + 4 * u * i for i in range(1, self.bt['team'] // 4)])]
        hits += [(self.tp + i * u / 2, i % 4) for i in range(2 * self.bt['pre'])]                    # подводка: чаще
        hits += [(D + 4 * u * i, i % 4) for i in range(1, self.bt['hold'] // 4 + 1)]
        self.hits = hits
        sty = self.STYLE
        self.tag = C.text(F.tag(self.league), 'mont', 30, GRAY, 800, track=0.3)
        self.handle = C.text(C.HANDLE, 'mont', 34, (200, 200, 206), 700)
        self.e_big = {'h': C.fit(self.h.emb(440), 440, 440), 'a': C.fit(self.a.emb(440), 440, 440)}
        self.e_mid = {'h': C.fit(self.h.emb(300), 300, 300), 'a': C.fit(self.a.emb(300), 300, 300)}
        self.names = {k: C.text(self.team_of(k).up, 'osw', 112, sty['ink'], 700, max_w=980) for k in 'ha'}
        self.small_names = {k: C.text(self.team_of(k).up, 'osw', 58, sty['ink'], 700, max_w=440) for k in 'ha'}
        self.role = {'h': C.text('ХОЗЯЕВА', 'mont', 28, GRAY, 800, track=0.4), 'a': C.text('ГОСТИ', 'mont', 28, GRAY, 800, track=0.4)}
        self.when_im = C.text(self.when_txt(), 'mont', 34, (210, 210, 216), 700, track=0.12)
        self.ot = C.text('ОСНОВНОЕ ВРЕМЯ', 'mont', 26, GRAY, 800, track=0.3)
        self.odds_im = self.odds()
        self.blocks = {k: self.team_blocks(k) for k in 'ha'}
        self.vs = C.text('VS', 'osw', 64, GRAY, 600, track=0.2)

    def flash(self, t):
        best = (0.0, None)
        for t0, i in [(self.drop, 'D')] + self.hits:
            dt = t - t0
            if 0 <= dt < 0.5:
                k = math.exp(-dt * 6) * (0.55 + 0.45 * abs(math.cos(dt * 38)))
                if i not in ('D', 's'):
                    k *= 0.6
                if k > best[0]:
                    best = (k, i)
        return best

    def sky_frame(self, t, k):
        fr = self.sky.copy()
        off = int((t * 16) % 400)
        cl = self.clouds.crop((off, 0, off + W, H))
        base = 0.3 + 0.05 * math.sin(t * 0.7) + (0.08 if self.tp <= t < self.drop else 0)
        cl_a = cl.point(lambda v: int(min(255, v * (base + 0.95 * k))))
        fr.alpha_composite(Image.merge('RGBA', (Image.new('L', (W, H), 150), Image.new('L', (W, H), 150),
                                                Image.new('L', (W, H), 156), cl_a)))
        return fr

    def lit(self, im, k, base=0.35):
        """Эмблема в темноте: тусклая, вспышкой высвечивается и светится."""
        a = base + (1 - base) * min(1.0, k * 1.5)
        if k > 0.15:
            im = C.glow(im, 24, 1.1 * k, (225, 228, 236))
        return im, a

    def frame(self, t):
        u, D = self.u, self.drop
        k, bi = self.flash(t)
        fr = self.sky_frame(t, k)
        if bi is not None and k > 0.05:
            bolt = self.big if bi == 'D' else self.strike if bi == 's' else self.small[bi]
            fr = add_rgb(fr, bolt, min(1.25, k * 1.35))
        sc, t0, t1 = self.scene(t)
        C.put(fr, self.tag, W / 2, 262, C.seg(t, 0, 0.4) * 0.95)
        if sc == 'intro':
            a = 1 - C.seg(t, t1 - 0.15, t1)
            for key, x in (('h', 280), ('a', 800)):
                em, la = self.lit(self.e_mid[key], k, 0.55)
                q = C.out_expo(C.seg(t, 0.1 + (0 if key == 'h' else 0.15), 0.8))
                C.put(fr, em, x, 640 + 30 * (1 - q), q * a * la)
                C.put(fr, self.small_names[key], x, 860, q * a)
                C.put(fr, self.role[key], x, 922, q * a)
            C.put(fr, self.vs, W / 2, 640, C.seg(t, 0.4, 0.9) * a)
            qo = C.out_expo(C.seg(t, 0.35, 1.0))
            C.put(fr, self.when_im, W / 2, 1030, qo * a)
            C.put(fr, self.odds_im, W / 2, 1180 + 30 * (1 - qo), qo * a)
            C.put(fr, self.ot, W / 2, 1292, qo * a)
        elif sc in ('h', 'a'):
            a = 1 - C.seg(t, t1 - 0.15, t1)
            q = C.out_expo(C.seg(t, t0, t0 + 0.5))
            em, la = self.lit(self.e_mid[sc], k, 0.6)
            C.put(fr, em, W / 2, 470 + 30 * (1 - q), q * a * la)
            C.put(fr, self.names[sc], W / 2, 690, q * a)
            C.put(fr, self.role[sc], W / 2, 762, q * a)
            self.stack(fr, self.blocks[sc], t, t0 + 0.35, W / 2, 810, gap=16, a=a)
        elif sc == 'pre':
            q = C.seg(t, t0, D)
            em, la = self.lit(self.e_mid[self.side], k, 0.15)
            C.put(fr, em, W / 2, 520, (0.25 + 0.5 * q) * la)
        else:
            q = C.out_expo(C.seg(t, D, D + 0.5))
            em = C.scale(self.e_big[self.side], 1 + 0.08 * math.exp(-(t - D) * 5))
            em, la = self.lit(em, max(k, 0.25), 0.8)
            C.put(fr, em, W / 2, 560, q * la)
            pb = self.pick_block(kef_q=C.out_back(C.seg(t, D + 2 * u, D + 2 * u + 0.4)))
            qp = C.out_expo(C.seg(t, D + 0.15, D + 0.7))
            C.put(fr, pb, W / 2, 860 + pb.height / 2 + 40 * (1 - qp), qp * (1 - C.seg(t, self.t_cta - 0.2, self.t_cta + 0.2) * 0.0))
            self.cta(fr, t)
        if t < self.t_cta:
            C.put(fr, self.handle, W / 2, 1440, C.seg(t, 0.3, 0.8) * 0.85)
        # белая вспышка на дропе
        wf = max(0.0, 1 - abs(t - D) / 0.16) if t >= D - 0.03 else 0.0
        wf = max(wf, 0.2 * k if bi == 's' else 0.0)
        if wf > 0:
            fr.alpha_composite(Image.new('RGBA', (W, H), (236, 236, 240, int(170 * wf))))
        fr = self.camera(fr, t, cy=760, amp=14)
        return C.grain(C.vignette(fr, 0.5), t, 7)
