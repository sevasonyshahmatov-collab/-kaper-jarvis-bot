# -*- coding: utf-8 -*-
"""«Коллаж» — зин из вырезок, стоп-моушен 12 кадров/с.

Бумажный фон; «ПРОГНОЗ» собирается из букв, вырезанных из разных журналов (разные шрифты, плашки, наклоны);
на дропе с двух сторон шлёпаются рваные листы цветов клубов с эмблемами и скотчем, стикер «VS», названия
клубов собираются из вырезанных букв; потом — новая страница: полоска с машинописным прогнозом на скотче,
звезда-стикер с кэфом и обводка маркером; в конце — тетрадный листок «TELEGRAM @jarvibet».
Всё дрожит на 1–2 пикселя от кадра к кадру — как настоящая покадровая анимация.
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from reels import core as C
from reels.core import W, H

PAPER = (236, 230, 216)
INK = (24, 22, 22)
RED = (214, 38, 38)
YEL = (250, 214, 60)
FONTS = ['dela', 'rmono', 'prata', 'play', 'russo', 'unb', 'osw', 'mono', 'rubik', 'tenor', 'corm']
STYLES = [((24, 22, 22), (250, 248, 240)), ((250, 248, 240), (24, 22, 22)), (RED, (250, 248, 240)), ((24, 22, 22), YEL),
          ((250, 248, 240), RED), ((30, 60, 160), (250, 248, 240)), ((24, 22, 22), (180, 220, 240))]
FPS_SM = 12


def torn(w, h, col, seed, edge=7, fiber=True):
    """Рваный лист: зубчатые края и белые волокна по краю."""
    rnd = random.Random(seed)
    pts = []
    for x in range(0, w + 1, 9):
        pts.append((x, rnd.uniform(0, edge)))
    for y in range(0, h + 1, 9):
        pts.append((w - rnd.uniform(0, edge), y))
    for x in range(w, -1, -9):
        pts.append((x, h - rnd.uniform(0, edge)))
    for y in range(h, -1, -9):
        pts.append((rnd.uniform(0, edge), y))
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    if fiber:
        fb = Image.new('RGBA', (w, h), (250, 248, 242, 255))
        im.paste(fb, (0, 0), m)
        m2 = m.filter(ImageFilter.MinFilter(7))
    else:
        m2 = m
    body = Image.new('RGBA', (w, h), tuple(col) + (255,))
    arr = np.asarray(body, np.int16).copy()
    noise = np.random.default_rng(seed).normal(0, 6, (h, w)).astype(np.int16)
    arr[..., :3] += noise[..., None]
    body = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
    im.paste(body, (0, 0), m2)
    return im


def tape(w=200, seed=0):
    t = torn(w, 64, (232, 220, 180), seed, 5, False)
    t.putalpha(t.getchannel('A').point(lambda v: int(v * 0.72)))
    return t


def letter(ch, seed, size=120):
    rnd = random.Random(seed)
    if ch == ' ':
        return None
    fnt = rnd.choice(FONTS)
    fg, bg = rnd.choice(STYLES)
    g = C.text(ch, fnt, int(size * rnd.uniform(0.85, 1.1)), fg, 800)
    pad = int(size * 0.14)
    w, h = g.width + 2 * pad + rnd.randint(0, 14), g.height + 2 * pad + rnd.randint(0, 14)
    im = torn(w, h, bg, seed + 1, 4, False)
    C.put(im, g, w / 2 + rnd.uniform(-4, 4), h / 2 + rnd.uniform(-4, 4))
    im = C.rotate(im, rnd.uniform(-9, 9))
    return C.with_shadow(im, 6, 0.35, 5)


def word(s, seed, size=120, max_w=980):
    """Слово из вырезанных букв → (картинка, [x-центры букв]) — буквы появляются по одной."""
    ls = [letter(ch, seed + i * 17, size) for i, ch in enumerate(s)]
    gap = int(size * 0.32)
    xs, x = [], 0
    for im in ls:
        w = im.width if im is not None else gap
        xs.append(x + w / 2)
        x += w - (14 if im is not None else 0)
    k = min(1.0, max_w / max(1, x))
    return ls, [v * k for v in xs], x * k, k


class Collage(C.Reel):
    def __init__(self, home, away, league, pick, coef, when, u=60 / 72, drop=3.33, seed=17):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.pick, self.coef, self.when = pick, coef, when
        self.league = 'НХЛ' if str(league).upper() == 'NHL' else 'КХЛ'
        self.page2 = self.b(6)
        self.t_cta = self.b(9.5)
        self.dur = self.b(13)
        self.cover_t = self.b(10.6)
        self._prep()

    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        arr = np.ones((H, W, 3), np.float32) * np.array(PAPER, np.float32)
        arr += rnd.normal(0, 5, (H, W))[..., None]
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        for _ in range(5):                                         # сгибы бумаги
            a = rnd.uniform(0, math.pi)
            c = rnd.uniform(-400, 400)
            dist = (x - W / 2) * math.cos(a) + (y - H / 2) * math.sin(a) - c
            arr += (8 * np.exp(-(dist / 6) ** 2) - 6 * np.exp(-((dist - 9) / 10) ** 2))[..., None]
        self.bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        # крупная эмблема полутоном на фоне
        self.ht = {k: self.halftone(t.emb(760), t.c0) for k, t in (('h', self.h), ('a', self.a))}
        self.title = word('ПРОГНОЗ', 100, 150, 900)
        self.n1 = word(self.h.up, 300, 112, 960)
        self.n2 = word(self.a.up, 500, 112, 960)
        self.sheet = {}
        for k, t, sd, rot in (('h', self.h, 7, -6), ('a', self.a, 9, 5)):
            sh = torn(520, 430, t.c1, sd)
            C.put(sh, C.glow(t.emb(300), 10, 0.6, (255, 255, 255)), 260, 215)
            sh.alpha_composite(tape(190, sd), (165, -12))
            self.sheet[k] = C.with_shadow(C.rotate(sh, rot), 12, 0.4, 10)
        vs = Image.new('RGBA', (220, 220), (0, 0, 0, 0))
        ImageDraw.Draw(vs).ellipse((0, 0, 219, 219), fill=YEL + (255,))
        ImageDraw.Draw(vs).ellipse((10, 10, 209, 209), outline=INK + (255,), width=6)
        C.put(vs, C.text('VS', 'dela', 100, INK), 110, 110)
        self.vs = C.with_shadow(C.rotate(vs, 12), 8, 0.4, 8)
        # страница 2
        strip = torn(940, 300, (250, 248, 240), 31)
        C.put(strip, C.text('ПРОГНОЗ:', 'mono', 44, INK, 700), 470, 70)
        C.put(strip, C.lines(self.pick.upper(), 'mono', 76, 860, INK, 800, gap=0.05, max_lines=2), 470, 180)
        strip.alpha_composite(tape(170, 32), (-20, -10))
        strip.alpha_composite(tape(170, 33), (790, 230))
        self.strip = C.with_shadow(C.rotate(strip, -3), 12, 0.4, 10)
        star = self.starburst(420, RED)
        C.put(star, C.text('КЭФ', 'dela', 56, (255, 255, 255)), 210, 160)
        C.put(star, C.text(C.fmt_k(self.coef), 'dela', 110, (255, 255, 255)), 210, 245)
        self.star = C.with_shadow(C.rotate(star, -10), 10, 0.45, 10)
        self.mini = {}
        for k, t, sd in (('h', self.h, 41), ('a', self.a, 43)):
            p = torn(300, 300, (250, 248, 240), sd)
            C.put(p, t.emb(220), 150, 150)
            p.alpha_composite(tape(140, sd), (80, -14))
            self.mini[k] = C.with_shadow(C.rotate(p, 7 if k == 'h' else -6), 10, 0.4, 8)
        dl = torn(540, 110, INK, 51, 4, False)
        C.put(dl, C.text('%s · %s' % (self.league, self.when), 'mono', 34, (250, 248, 240), 700, max_w=500), 270, 55)
        self.dateline = C.with_shadow(C.rotate(dl, 2), 6, 0.35, 6)
        self.note = self.notebook()

    def halftone(self, emb, col, step=14):
        g = ImageOps.grayscale(Image.alpha_composite(Image.new('RGBA', emb.size, (255, 255, 255, 255)), emb).convert('RGB'))
        a = np.asarray(emb.getchannel('A'), np.float32) / 255
        arr = 1 - np.asarray(g, np.float32) / 255
        im = Image.new('RGBA', emb.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for yy in range(0, emb.height, step):
            for xx in range(0, emb.width, step):
                v = arr[yy, xx] * a[yy, xx] * 0.6 + a[yy, xx] * 0.25
                r = step * 0.62 * math.sqrt(max(0.0, v))
                if r > 0.8:
                    d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=tuple(col) + (70,))
        return im

    def starburst(self, s, col):
        pts = []
        for i in range(32):
            r = s / 2 * (1 if i % 2 == 0 else 0.8)
            a = i * math.pi / 16
            pts.append((s / 2 + r * math.cos(a), s / 2 + r * math.sin(a)))
        return C.polygon(pts, (s, s), col)

    def notebook(self):
        w, h = 760, 420
        im = torn(w, h, (250, 250, 246), 61)
        d = ImageDraw.Draw(im)
        for y in range(70, h - 10, 52):
            d.line((20, y, w - 20, y), fill=(150, 180, 220, 255), width=2)
        d.line((90, 10, 90, h - 10), fill=(230, 120, 120, 255), width=3)
        C.put(im, C.text('больше прогнозов:', 'hand', 64, (30, 60, 160), 700), 430, 90)
        C.put(im, C.tg_icon(110), 180, 250)
        C.put(im, C.text('TELEGRAM', 'dela', 66, INK), 470, 220)
        C.put(im, C.text(C.HANDLE, 'hand', 86, RED, 700), 470, 320)
        im.alpha_composite(tape(200, 62), (280, -16))
        return C.scale(C.with_shadow(C.rotate(im, 4), 12, 0.45, 10), 0.84, Image.LANCZOS)

    # ── кадр: время округляется до 1/12 с, каждый «кадр» — своё дрожание ──
    def jit(self, key, n, amp=2.0):
        r = random.Random(hash((key, n)) & 0xffffffff)
        return r.uniform(-amp, amp), r.uniform(-amp, amp)

    def slap(self, fr, im, x, y, t, t0, key, n, dur=0.17):
        if t < t0:
            return
        k = C.seg(t, t0, t0 + dur)
        s = 1.25 - 0.25 * k
        jx, jy = self.jit(key, n)
        C.put(fr, C.scale(im, s) if s > 1.001 else im, x + jx, y + jy, min(1.0, 0.4 + k))

    def put_word(self, fr, wd, cx, cy, t, t0, t1, key, n):
        ls, xs, tw, k = wd
        cnt = len(ls)
        for i, (im, x) in enumerate(zip(ls, xs)):
            ti = t0 + (t1 - t0) * i / max(1, cnt)
            if im is None or t < ti:
                continue
            jx, jy = self.jit((key, i), n, 1.5)
            img = C.scale(im, k) if k < 0.999 else im
            C.put(fr, img, cx - tw / 2 + x + jx, cy + jy + (i % 2) * 6)

    def frame(self, t):
        n = int(t * FPS_SM)
        t = n / FPS_SM                                    # покадровая анимация
        u, D = self.u, self.drop
        fr = self.bg.copy()
        jx, jy = self.jit('bg', n, 1.0)
        if t < self.page2:
            C.put(fr, self.ht['h'], 300 + jx, 560 + jy, 1.0)
            C.put(fr, self.ht['a'], 800 + jx, 1180 + jy, 1.0)
            self.put_word(fr, self.title, W / 2, 330, t, 0.1, self.b(-1), 'title', n)
            self.slap(fr, self.dateline, W / 2 + 120, 470, t, self.b(-0.7), 'dl', n)
            self.slap(fr, self.sheet['h'], 320, 720, t, D, 'sh', n)
            self.slap(fr, self.sheet['a'], 760, 1110, t, D + 0.08, 'sa', n)
            self.slap(fr, self.vs, 560, 930, t, D + 0.25, 'vs', n)
            self.put_word(fr, self.n1, W / 2, 985, t, self.b(2), self.b(3.2), 'n1', n)
            self.put_word(fr, self.n2, W / 2, 1385, t, self.b(3.5), self.b(4.7), 'n2', n)
        else:
            # новая страница наезжает снизу за 3 кадра
            k = C.seg(t, self.page2, self.page2 + 0.25)
            C.put(fr, self.mini['h'], 260 + jx, 560 + jy)
            C.put(fr, self.mini['a'], 820 + jx, 540 + jy)
            C.put(fr, self.dateline, W / 2, 330 + jy)
            self.slap(fr, self.strip, W / 2, 880, t, self.page2 + 0.1, 'strip', n)
            self.slap(fr, self.star, 868, 1200, t, self.b(7.5), 'star', n)
            if t >= self.b(8.3):                                  # обводка маркером вокруг прогноза
                p = C.seg(t, self.b(8.3), self.b(9))
                d = ImageDraw.Draw(fr)
                angs = np.linspace(-2.6, -2.6 + 2 * math.pi * 1.06 * p, 70)
                pts = [(W / 2 + 470 * math.cos(a), 890 + 185 * math.sin(a) + 12 * math.sin(3 * a)) for a in angs]
                if len(pts) > 1:
                    d.line(pts, fill=RED + (230,), width=10, joint='curve')
            if t >= self.t_cta:
                self.slap(fr, self.note, 390, 1310, t, self.t_cta, 'note', n)
            if k < 1:                                             # смена страницы: старая уезжает вверх
                y = int(H * C.out_cubic(k))
                old = self.frame_page1(t)
                fr.paste(old.crop((0, y, W, H)), (0, 0))
        dx, dy = C.shake(t, D, 10, 0.3)
        fr = C.zoom(fr, 1.0 + 0.012 * math.sin(n * 0.7), dx=dx, dy=dy)
        return C.vignette(fr, 0.3)

    def frame_page1(self, t):
        n = int(t * FPS_SM)
        fr = self.bg.copy()
        C.put(fr, self.ht['h'], 300, 560)
        C.put(fr, self.ht['a'], 800, 1180)
        tt = self.page2 - 0.01
        self.put_word(fr, self.title, W / 2, 330, tt, 0.1, self.b(-1), 'title', n)
        C.put(fr, self.dateline, W / 2 + 120, 470)
        C.put(fr, self.sheet['h'], 320, 720)
        C.put(fr, self.sheet['a'], 760, 1110)
        C.put(fr, self.vs, 560, 930)
        self.put_word(fr, self.n1, W / 2, 985, tt, self.b(2), self.b(3.2), 'n1', n)
        self.put_word(fr, self.n2, W / 2, 1385, tt, self.b(3.5), self.b(4.7), 'n2', n)
        return fr
