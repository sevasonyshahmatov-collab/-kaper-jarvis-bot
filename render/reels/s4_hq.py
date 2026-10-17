# -*- coding: utf-8 -*-
"""Серия 4 · «Штаб» (Militant). Стол оперативного штаба сверху: тёмная карта с изолиниями и координатной сеткой,
под лампой. Команды — значки-подразделения с эмблемами. Матч и линия на брифинг-панели → значок хозяев и форма →
значок гостей → прицел наводится → на дропе через карту проходит стрелка удара от команды из прогноза, прогноз и кэф.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels import fresh as FR
from reels import s4

W, H = C.W, C.H
AMBER = (232, 176, 72)
TEAL = (120, 176, 170)


def _contours(seed=6):
    """Изолинии рельефа: шум → уровни → тонкие линии."""
    rng = np.random.default_rng(seed)
    n = np.zeros((H // 4, W // 4), np.float32)
    for k in (1, 2, 4):
        g = rng.random((H // (240 // k) + 2, W // (240 // k) + 2)).astype(np.float32)
        n += np.asarray(Image.fromarray(g).resize((W // 4, H // 4), Image.BICUBIC)) / k
    n = (n - n.min()) / (n.max() - n.min())
    lv = n * 18
    edge = np.abs(lv - np.round(lv)) < 0.06
    major = edge & (np.round(lv) % 5 == 0)
    img = np.zeros((H // 4, W // 4), np.uint8)
    img[edge] = 70
    img[major] = 140
    return Image.fromarray(img).resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(0.8))


def hexagon(d, fill, outline, width=6):
    im = Image.new('RGBA', (d * 3, d * 3), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    pts = [(d * 1.5 + d * 1.45 * math.cos(math.radians(60 * k + 30)), d * 1.5 + d * 1.45 * math.sin(math.radians(60 * k + 30)))
           for k in range(6)]
    dr.polygon(pts, fill=fill + (255,))
    dr.line(pts + [pts[0]], fill=outline + (255,), width=width * 3, joint='curve')
    return im.resize((d, d), Image.LANCZOS)


def arrow_poly(p0, p1, p2, q, w0=34, w1=20, head=90):
    """Широкая стрелка по кривой Безье p0→p2 (контроль p1), нарисованная до доли q. → [точки многоугольника]."""
    n = 80
    ts = np.linspace(0, max(0.02, q), n)
    pts = [(1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1) + t ** 2 * np.array(p2) for t in ts]
    pts = np.array(pts)
    tang = np.gradient(pts, axis=0)
    tang /= np.linalg.norm(tang, axis=1)[:, None] + 1e-6
    nrm = np.c_[-tang[:, 1], tang[:, 0]]
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    total = L[-1] + 1e-6
    body_end = max(0.0, total - head * 0.8)
    keep = L <= body_end
    if keep.sum() < 2:
        keep[:2] = True
    wid = w0 + (w1 - w0) * (L / total)
    left = pts[keep] + nrm[keep] * wid[keep, None] / 2
    right = pts[keep] - nrm[keep] * wid[keep, None] / 2
    tip, tg = pts[-1], tang[-1]
    nb = np.array([-tg[1], tg[0]])
    base = tip - tg * head * 0.8
    hd = [tuple(base + nb * w1 * 1.6), tuple(tip), tuple(base - nb * w1 * 1.6)]
    poly = [tuple(p) for p in left] + [hd[0], hd[1], hd[2]] + [tuple(p) for p in right[::-1]]
    return poly


class HQ(s4.Base):
    STYLE = dict(font='mont', title='tek', ink=(232, 236, 232), sub=(150, 168, 164), accent=AMBER, panel=(10, 16, 20),
                 panel_a=222, line=TEAL, line_a=90, radius=8)

    def __init__(self, *a, **kw):
        super().__init__(*a, seed=51, **kw)
        self.map = self._map()
        self.col = {k: FR.club(self.team_of(k)) for k in 'ha'}
        self.marker = {k: self._marker(self.team_of(k), self.col[k], 230) for k in 'ha'}
        self.marker_s = {k: self._marker(self.team_of(k), self.col[k], 170) for k in 'ha'}
        sty = self.STYLE
        self.tag = C.text(F.tag(self.league), 'tek', 30, TEAL, 700, track=0.3)
        self.handle = C.text(C.HANDLE, 'tek', 34, (190, 206, 202), 600)
        self.names = {k: C.text(self.team_of(k).up, 'tek', 96, sty['ink'], 800, max_w=980) for k in 'ha'}
        self.small_names = {k: C.text(self.team_of(k).up, 'tek', 46, sty['ink'], 800, max_w=440) for k in 'ha'}
        self.role = {'h': C.text('ХОЗЯЕВА', 'tek', 28, AMBER, 700, track=0.4), 'a': C.text('ГОСТИ', 'tek', 28, AMBER, 700, track=0.4)}
        self.brief = self._brief()
        self.blocks = {k: self.team_blocks(k) for k in 'ha'}
        self.pos_i = {'h': (300, 560), 'a': (780, 560)}

    def _map(self):
        yy, xx = np.mgrid[0:H, 0:W].astype(float)
        lamp = np.exp(-(((xx - 540) / 720) ** 2 + ((yy - 820) / 980) ** 2))
        base = np.array((9, 14, 17.))[None, None, :] + (lamp * 18)[..., None] * np.array((0.8, 1.0, 1.0))
        img = Image.fromarray(np.clip(base, 0, 255).astype('uint8'), 'RGB').convert('RGBA')
        ct = _contours()
        lay = Image.new('RGBA', (W, H), TEAL + (0,))
        lay.putalpha(ct.point(lambda v: int(v * 0.55)))
        img.alpha_composite(lay)
        d = ImageDraw.Draw(img)
        step = 135
        for i, x in enumerate(range(0, W + 1, step)):
            d.line((x, 0, x, H), fill=TEAL + (34,), width=1)
        for j, y in enumerate(range(0, H + 1, step)):
            d.line((0, y, W, y), fill=TEAL + (34,), width=1)
            if 2 <= j <= 11:
                d.text((10, y + 6), str(j - 1), font=C.font('tek', 22, 600), fill=TEAL + (90,))
        return C.vignette(img, 0.5).convert('RGBA')

    def _marker(self, tm, col, d):
        m = Image.new('RGBA', (d + 40, d + 40), (0, 0, 0, 0))
        C.put(m, C.shadow(hexagon(d, (16, 22, 26), col, 7), r=10, a=0.8), m.width / 2 + 6, m.height / 2 + 10)
        C.put(m, hexagon(d, (16, 22, 26), col, 7), m.width / 2, m.height / 2)
        C.put(m, C.fit(tm.emb(d * 2), int(d * 0.58), int(d * 0.58)), m.width / 2, m.height / 2)
        return m

    def _brief(self):
        w, h = 940, 360
        p = self.panel(w, h)
        dr = ImageDraw.Draw(p)
        for (x, y, sx, sy) in ((0, 0, 1, 1), (w, 0, -1, 1), (0, h, 1, -1), (w, h, -1, -1)):
            dr.line((x, y + sy * 4, x + sx * 40, y + sy * 4), fill=AMBER + (255,), width=4)
            dr.line((x + sx * 4, y, x + sx * 4, y + sy * 40), fill=AMBER + (255,), width=4)
        C.put(p, C.text(self.when_txt(), 'tek', 34, self.STYLE['ink'], 700, track=0.08), w / 2, 56)
        C.put(p, self.odds(w=860, h=170), w / 2, 196)
        C.put(p, C.text('ОСНОВНОЕ ВРЕМЯ', 'tek', 24, self.STYLE['sub'], 700, track=0.3), w / 2, 316)
        return p

    def rings(self, fr, x, y, t, col, r0=130, a=1.0):
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for k in range(3):
            ph = ((t / (2 * self.u)) + k / 3) % 1
            r = r0 + 140 * ph
            al = int(110 * (1 - ph) * a)
            d.ellipse((x - r, y - r, x + r, y + r), outline=col + (al,), width=3)
        fr.alpha_composite(lay)

    def crosshair(self, fr, x, y, a=1.0, col=AMBER):
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        al = int(230 * a)
        d.ellipse((x - 70, y - 70, x + 70, y + 70), outline=col + (al,), width=4)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            d.line((x + dx * 50, y + dy * 50, x + dx * 110, y + dy * 110), fill=col + (al,), width=4)
        fr.alpha_composite(lay)

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.map.copy()
        sc, t0, t1 = self.scene(t)
        C.put(fr, self.tag, W / 2, 262, C.seg(t, 0, 0.4) * 0.95)
        if sc == 'intro':
            a = 1 - C.seg(t, t1 - 0.15, t1)
            for key, d in (('h', 0.0), ('a', u)):
                x, y = self.pos_i[key]
                q = C.out_back(C.seg(t, 0.1 + d, 0.45 + d))
                self.rings(fr, x, y, t, self.col[key], 110, a * min(1, q))
                C.put(fr, C.scale(self.marker[key], 0.6 + 0.4 * min(1, q)), x, y, min(1, q) * a)
                C.put(fr, self.small_names[key], x, y + 165, min(1, q) * a)
                C.put(fr, self.role[key], x, y + 215, min(1, q) * a)
            qb = C.out_expo(C.seg(t, 0.4, 1.0))
            C.put(fr, self.brief, W / 2, 1110 + 40 * (1 - qb), qb * a)
        elif sc in ('h', 'a'):
            a = 1 - C.seg(t, t1 - 0.15, t1)
            q = C.out_expo(C.seg(t, t0, t0 + 0.5))
            self.rings(fr, W / 2, 450, t, self.col[sc], 120, q * a)
            C.put(fr, self.marker[sc], W / 2, 450 + 30 * (1 - q), q * a)
            C.put(fr, self.role[sc], W / 2, 600, q * a)
            C.put(fr, self.names[sc], W / 2, 668, q * a)
            self.stack(fr, self.blocks[sc], t, t0 + 0.35, W / 2, 740, gap=16, a=a)
        elif sc == 'pre':
            q = C.in_out(C.seg(t, t0, D))
            other = 'a' if self.side == 'h' else 'h'
            xs, xo = (230, 850) if self.side == 'h' else (850, 230)
            C.put(fr, self.marker_s[self.side], xs, 600, 1)
            C.put(fr, self.marker_s[other], xo, 600, 1)
            cx = C.lerp(W / 2, xo, q) + 18 * math.sin(t * 23) * (1 - q)
            self.crosshair(fr, cx, 600 + 14 * math.cos(t * 19) * (1 - q), 0.5 + 0.5 * q)
        else:
            other = 'a' if self.side == 'h' else 'h'
            xs, xo = (230, 850) if self.side == 'h' else (850, 230)
            qa = C.out_cubic(C.seg(t, D, D + 0.4))
            hit = C.seg(t, D + 0.35, D + 0.9)
            C.put(fr, self.marker_s[other], xo, 600, 1 - 0.55 * hit)
            if hit > 0:
                lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(lay)
                r = 60 + 160 * hit
                d.ellipse((xo - r, 600 - r, xo + r, 600 + r), outline=AMBER + (int(200 * (1 - hit)),), width=6)
                fr.alpha_composite(lay)
            col = self.col[self.side]
            poly = arrow_poly((xs + (90 if xs < xo else -90), 640), (W / 2, 410), (xo + (-80 if xs < xo else 80), 550), qa)
            ar = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ar).polygon(poly, fill=col + (235,))
            fr.alpha_composite(C.glow(ar, 14, 0.6, col).crop((42, 42, 42 + W, 42 + H)))
            C.put(fr, self.marker_s[self.side], xs, 600, 1)
            pb = self.pick_block(kef_q=C.out_back(C.seg(t, D + 2 * u, D + 2 * u + 0.4)))
            qp = C.out_expo(C.seg(t, D + 0.4, D + 0.9))
            C.put(fr, pb, W / 2, 810 + pb.height / 2 + 40 * (1 - qp), qp)
            self.cta(fr, t)
        if t < self.t_cta:
            C.put(fr, self.handle, W / 2, 1440, C.seg(t, 0.3, 0.8) * 0.85)
        fr = self.camera(fr, t, cy=800)
        return C.grain(fr, t, 5)
