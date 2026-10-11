# -*- coding: utf-8 -*-
"""«Чернила» — капли туши растекаются по бумаге.

На тёплой бумаге падает капля, и расплываются два пятна туши в цветах клубов — в каждом проступает эмблема.
На дропе тушь фаворита заливает лист, чужое пятно бледнеет; поверх белым курсивом пишется прогноз, затем шанс и линия.
Край пятна темнее (тушь собирается на границе), брызги вокруг; всё рисуется полем «времени прихода» туши.
"""
import math

import numpy as np
from PIL import Image, ImageFilter

from reels import core as C
from reels import fresh as F
from reels.core import H, W


def _noise(w, h, scale, rng):
    n = rng.random((int(h / scale) + 3, int(w / scale) + 3)).astype(np.float32)
    im = Image.fromarray((n * 255).astype(np.uint8), 'L').resize((w, h), Image.BICUBIC)
    if scale >= 8:
        im = im.filter(ImageFilter.GaussianBlur(scale / 3))       # без «ступенек» на краю пятна
    a = np.asarray(im, np.float32) / 255
    return (a - a.min()) / (a.max() - a.min() + 1e-6)


class Ink(C.Reel):
    def __init__(self, m, u=1.0, drop=3.0, seed=41):
        super().__init__(u, drop, seed)
        self.m = m
        self.h, self.a = C.match(m['home'], m['away'], m['league'])
        self.fav_h = m['side'] == 'h'
        self.fav = self.h if self.fav_h else self.a
        D = drop
        self.t_pick = D + 2 * u
        self.t_chance = D + 4.5 * u
        self.t_cta = D + 7.5 * u
        self.dur = D + 11 * u
        self.cover_t = D + 9 * u
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        fract = (_noise(W, H, 260, rng) * 0.55 + _noise(W, H, 70, rng) * 0.3 + _noise(W, H, 18, rng) * 0.15)
        # время прихода туши: расстояние от центра пятна (вытянуто) + шум края
        def arrival(cx, cy, rx, ry, k=0.55):
            d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
            return d + (fract - 0.5) * k
        self.A_h = arrival(330, 760, 420, 420)
        self.A_a = arrival(750, 1080, 400, 400)
        fx, fy = (330, 760) if self.fav_h else (750, 1080)
        self.A_f = arrival(fx, fy, 1500, 1500, 0.22)
        paper = np.array((244, 238, 226), np.float32)
        tex = (_noise(W, H, 4, rng) - 0.5) * 10 + (_noise(W, H, 120, rng) - 0.5) * 14
        self.paper = paper[None, None, :] + tex[..., None]
        self.ch = np.array(F.club(self.h), np.float32)
        self.ca = np.array(F.club(self.a), np.float32)
        self.cf = self.ch if self.fav_h else self.ca
        self.grain = (_noise(W, H, 2.5, rng) - 0.5)[..., None] * 18
        self.splats = [(rng.uniform(80, 1000), rng.uniform(380, 1420), rng.uniform(4, 16), rng.uniform(0, 1)) for _ in range(40)]
        self.e_h, self.e_a = self.h.emb(250), self.a.emb(250)

    def _stain(self, A, prog, col, k=1.0):
        """Покрытие и цвет пятна: внутри ровно, у края темнее (тушь собирается на границе)."""
        soft = 0.035
        cov = np.clip((prog - A) / soft + 0.5, 0, 1)
        edge = np.exp(-((A - prog + 0.04) / 0.05) ** 2) * (cov > 0)
        dark = col * (1 - 0.35 * edge[..., None])
        return cov * k, dark

    def frame(self, t):
        u, D = self.u, self.drop
        m = self.m
        img = self.paper.copy()
        # два пятна до дропа, затем фаворит заливает лист
        ph = 0.55 * C.out_cubic(C.seg(t, 0.35, D)) + 0.03 * math.sin(t * 2)
        pa = 0.52 * C.out_cubic(C.seg(t, 0.6, D)) + 0.03 * math.sin(t * 2 + 1)
        fade_other = 1 - 0.75 * C.in_out(C.seg(t, D, D + 1.5 * u))
        for A, p_, col, is_fav in ((self.A_h, ph, self.ch, self.fav_h), (self.A_a, pa, self.ca, not self.fav_h)):
            cov, dark = self._stain(A, p_, col, 1.0 if is_fav else fade_other)
            img = img * (1 - cov[..., None]) + dark * cov[..., None]
        pf = 1.25 * C.out_cubic(C.seg(t, D, D + 2.2 * u))
        if pf > 0:
            cov, dark = self._stain(self.A_f, pf, self.cf * 0.92, 0.94)
            img = img * (1 - cov[..., None]) + dark * cov[..., None]
        img = img + self.grain
        fr = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        for sx, sy, r, ph_ in self.splats:                     # брызги
            a = C.seg(t, 0.3 + ph_ * 1.5, 0.5 + ph_ * 1.5) * (1 - C.seg(t, D + 1.5 * u, D + 2.2 * u))
            col = tuple(int(c) for c in (self.ch if sx < W / 2 else self.ca))
            C.put(fr, C.ellipse(int(r), int(r), col), sx, sy, a * 0.9)
        # капля, падающая в начале
        if t < 0.45:
            y = -50 + (760 + 50) * C.in_cubic(C.seg(t, 0, 0.35))
            C.put(fr, C.ellipse(34, 46, tuple(int(c) for c in self.ch)), 330, y)
        ink_dark = (40, 34, 30)
        on_ink = (255, 255, 255)
        # эмблемы проступают в своих пятнах
        if t < D + 0.8 * u:
            a_out = 1 - C.seg(t, D, D + 0.8 * u)
            C.put(fr, self.e_h, 330, 760, C.seg(t, 0.9, 1.6) * a_out)
            C.put(fr, self.e_a, 750, 1080, C.seg(t, 1.2, 1.9) * a_out)
        else:
            q = C.out_cubic(C.seg(t, D + 0.8 * u, D + 1.6 * u))
            C.put(fr, C.with_shadow(self.fav.emb(300), 16, 0.3, 10), W / 2, 640, q)
        F.header(fr, m, C.seg(t, 0.2, 0.8), col=ink_dark if t < D + 0.8 * u else on_ink)
        if t < D:
            a = C.seg(t, 0.4, 1.0) * (1 - C.seg(t, D - 0.25, D))
            C.put(fr, C.text('%s — %s' % (self.h.short, self.a.short), 'playi', 86, ink_dark, 400, max_w=960), W / 2, 380, a)
            C.put(fr, C.text('%s · %s МСК' % (F.lg_ru(m), m['when']), 'mono', 34, (110, 100, 90), 600, track=0.12),
                  W / 2, 455, a)
        if t >= self.t_pick:
            # прогноз «пишется» слева направо
            txt = C.text(F.sentence(m), 'playi', 104, on_ink, 400, max_w=980)
            q = C.in_out(C.seg(t, self.t_pick, self.t_pick + 1.1 * u))
            w = max(2, int(txt.width * q))
            C.put(fr, C.text('наш прогноз', 'playi', 50, (255, 255, 255), 400), W / 2, 900, C.seg(t, self.t_pick, self.t_pick + 0.4))
            C.put(fr, txt.crop((0, 0, w, txt.height)), (W - txt.width) / 2, 990 - txt.height / 2, anchor='tl')
            if m.get('line'):
                C.put(fr, C.text('линия (осн. время): ' + F.line_text(m), 'mono', 30, (255, 255, 255), 600, max_w=1000),
                      W / 2, 1080, C.seg(t, self.t_pick + 1.2 * u, self.t_pick + 1.6 * u) * 0.9)
        if t >= self.t_chance:
            q = C.out_cubic(C.seg(t, self.t_chance, self.t_chance + 0.6))
            C.put(fr, C.text('%d%%' % m['chance'], 'play', 230, on_ink, 400), W / 2, 1230 + 20 * (1 - q), q)
            C.put(fr, C.text('наша оценка шанса · с учётом ОТ', 'playi', 44, on_ink, 400), W / 2, 1368,
                  C.seg(t, self.t_chance + 0.3, self.t_chance + 0.7) * (1 - C.seg(t, self.t_cta - 0.2, self.t_cta)))
        F.cta(fr, t, self.t_cta, y=1418)
        z = 1.0 + 0.02 * C.seg(t, 0, self.dur)
        fr = C.zoom(fr, z)
        return fr.convert('RGB')
