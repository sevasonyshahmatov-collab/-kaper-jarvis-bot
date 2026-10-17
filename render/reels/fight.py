# -*- coding: utf-8 -*-
"""«Файтинг» — матч как бой из Street Fighter / Mortal Kombat.

До дропа — «ВЫБЕРИ БОЙЦА»: сетка эмблем клубов лиги, курсоры P1 и P2 прыгают по долям и фиксируются на
командах матча. На дропе — экран VS: диагональный раскол цветов клубов, эмблемы влетают, молнии, «РАУНД 1».
Дальше — бой на льду: полоски здоровья, таймер, на каждую долю удар (рывок, вспышка, искры, «КОМБО ×3»),
у соперника фаворита здоровье кончается — «K.O.»; финал — «ПОБЕДИТЕЛЬ», прогноз с кэфом и подписка.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from reels import core as C
from reels.core import W, H

YEL = (255, 214, 0)
RED = (230, 30, 40)
WHITE = (255, 255, 255)
DARK = (10, 10, 16)


def italic(im, k=0.22):
    """Наклон (курсив) для «игровых» надписей."""
    w, h = im.size
    out = im.transform((int(w + h * k), h), Image.AFFINE, (1, k, -h * k, 0, 1, 0), Image.BICUBIC)
    return out


def burst(r, n=14, col=WHITE, inner=0.45, seed=0):
    rnd = np.random.default_rng(seed)
    pts = []
    for i in range(n * 2):
        a = i * math.pi / n
        rr = r * (1 if i % 2 == 0 else inner) * (rnd.uniform(0.8, 1.1) if i % 2 == 0 else 1)
        pts.append((r + rr * math.cos(a), r + rr * math.sin(a)))
    return C.polygon(pts, (2 * r, 2 * r), col)


class Fight(C.Reel):
    def __init__(self, home, away, league, side, pick, coef, when, roster, u=60 / 81, drop=2.96, seed=6):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.side = side
        self.win, self.lose = (self.h, self.a) if side == 'h' else (self.a, self.h)
        self.pick, self.coef, self.when = pick, coef, when
        self.league = 'НХЛ' if str(league).upper() == 'NHL' else 'КХЛ'
        lg = 'NHL' if self.league == 'НХЛ' else 'KHL'
        self.roster = [C.match(n, n, lg)[0] for n in roster]
        names = [t.name for t in self.roster]
        for t in (self.h, self.a):
            if t.name not in names:
                self.roster[len(names) % len(self.roster)] = t
                names = [x.name for x in self.roster]
        self.hits = [self.b(4 + 1.0 * i) for i in range(6)]          # удары после «БОЙ!»
        self.ko = self.b(10)
        self.dur = self.b(15.5)
        self.cover_t = self.b(12.4)
        self._prep()

    def _prep(self):
        # фон выбора: тёмная сетка
        self.sel_bg = C.vgrad(W, H, [(0, (18, 12, 40)), (1, (4, 4, 10))]).convert('RGBA')
        self.tiles = []
        for t in self.roster:
            tile = C.rrect(220, 220, 18, (30, 26, 52))
            C.put(tile, t.emb(170), 110, 110)
            self.tiles.append(tile)
        # сцена боя: лёд в перспективе и свет
        y = np.linspace(0, 1, H)[:, None]
        sky = np.array((30, 18, 60), np.float32) * (1 - y) + np.array((8, 6, 18), np.float32) * y
        arr = np.repeat(sky[:, None, :], W, 1).reshape(H, W, 3)
        floor = 1180
        fy = np.clip((np.arange(H) - floor) / (H - floor), 0, 1)[:, None, None]
        ice = np.array((150, 190, 230), np.float32) * (0.25 + 0.5 * fy) + 0 * arr
        arr = np.where(np.arange(H)[:, None, None] >= floor, ice * 0.6, arr)
        self.stage = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        self.stage = C.add_light(self.stage, C.radial(1600, 900, (90, 60, 160), 255, 1.6), W / 2, 700, 0.8)
        d = ImageDraw.Draw(self.stage)
        for i in range(-8, 9):                                     # линии льда в перспективе
            d.line((W / 2 + i * 40, floor, W / 2 + i * 260, H), fill=(200, 220, 255, 40), width=2)
        self.emb_big = {k: t.emb(420) for k, t in (('h', self.h), ('a', self.a))}
        self.emb_fight = {k: t.emb(330) for k, t in (('h', self.h), ('a', self.a))}

    # ── сцены ──
    def select(self, fr, t):
        fr.alpha_composite(self.sel_bg)
        C.put(fr, italic(C.text('ВЫБЕРИ БОЙЦА', 'dela', 96, YEL, stroke=6, stroke_fill=(120, 40, 0), max_w=900)), W / 2, 300)
        cols, rows = 4, 2
        x0, y0, gap = W / 2 - 1.5 * 236, 980, 236
        pos = [(x0 + (i % cols) * gap, y0 + (i // cols) * gap) for i in range(len(self.tiles))]
        for (x, y), tile in zip(pos, self.tiles):
            C.put(fr, tile, x, y)
        hi = [t.name for t in self.roster].index(self.h.name)
        ai = [t.name for t in self.roster].index(self.a.name)
        n = int(t / (self.u / 2))
        rnd = np.random.default_rng(n)
        p1 = hi if t >= self.b(-2) else int(rnd.integers(0, len(pos)))
        p2 = ai if t >= self.b(-1) else int(rnd.integers(0, len(pos)))
        for idx, col, lab, lock in ((p1, RED, '1P', t >= self.b(-2)), (p2, (40, 140, 255), '2P', t >= self.b(-1))):
            x, y = pos[idx]
            fr_ = Image.new('RGBA', (240, 240), (0, 0, 0, 0))
            ImageDraw.Draw(fr_).rounded_rectangle((4, 4, 236, 236), 20, outline=col + (255,), width=10 if lock else 7)
            C.put(fr, fr_, x, y)
            C.put(fr, C.text(lab, 'russo', 46, col, stroke=4, stroke_fill=DARK), x - 80 if lab == '1P' else x + 80, y - 120)
        # превью выбранных сверху
        for idx, x, col in ((p1, W / 2 - 250, RED), (p2, W / 2 + 250, (40, 140, 255))):
            tm = self.roster[idx]
            C.put(fr, C.glow(tm.emb(300), 30, 0.9, col), x, 620)
            C.put(fr, italic(C.text(tm.up, 'russo', 54, WHITE, stroke=4, stroke_fill=DARK, max_w=440)), x, 820)
        return fr

    def versus(self, fr, t):
        D = self.drop
        k = C.out_expo(C.seg(t, D, D + 0.35))
        c1, c2 = self.h.c1, self.a.c1
        fr.alpha_composite(Image.new('RGBA', (W, H), DARK + (255,)))
        sl = 260 * math.sin(0.0)
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        off = (1 - k) * 900
        d.polygon([(0 - off, 0), (W * 0.62 - off, 0), (W * 0.38 - off, H), (0 - off, H)], fill=c1 + (255,))
        d.polygon([(W * 0.62 + off, 0), (W + off, 0), (W + off, H), (W * 0.38 + off, H)], fill=c2 + (255,))
        fr.alpha_composite(lay)
        # линии скорости
        rnd = np.random.default_rng(int(t * 20))
        sp = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ds = ImageDraw.Draw(sp)
        for _ in range(26):
            y = rnd.uniform(0, H)
            ds.line((0, y, W, y - 300), fill=(255, 255, 255, int(rnd.uniform(20, 70))), width=int(rnd.uniform(2, 6)))
        fr.alpha_composite(sp)
        dark = Image.new('RGBA', (W, H), (0, 0, 0, 70))
        fr.alpha_composite(dark)
        e1 = C.glow(self.emb_big['h'], 30, 1.0, (255, 255, 255))
        e2 = C.glow(self.emb_big['a'], 30, 1.0, (255, 255, 255))
        C.put(fr, e1, W * 0.3 - (1 - k) * 700, 520)
        C.put(fr, e2, W * 0.7 + (1 - k) * 700, 1150)
        n1 = italic(C.text(self.h.up, 'dela', 92, WHITE, stroke=6, stroke_fill=DARK, max_w=900))
        n2 = italic(C.text(self.a.up, 'dela', 92, WHITE, stroke=6, stroke_fill=DARK, max_w=900))
        C.put(fr, n1, W * 0.40 - (1 - k) * 900, 770)
        C.put(fr, n2, W * 0.60 + (1 - k) * 900, 1400)
        vk = C.out_back(C.seg(t, D + 0.15, D + 0.5), 2.0)
        if vk > 0:
            vs = italic(C.text('VS', 'dela', 260, YEL, stroke=10, stroke_fill=(140, 30, 0)))
            C.put(fr, C.glow(C.scale(vs, max(0.05, vk)), 24, 1.2, (255, 160, 0)), W / 2, 965)
        if t >= self.b(2):
            C.put(fr, C.text('РАУНД 1', 'russo', 64, WHITE, stroke=5, stroke_fill=DARK), W / 2, 300, C.seg(t, self.b(2), self.b(2) + 0.2))
        return fr

    def health(self, t):
        """Здоровье проигрывающего (0..1) и победителя."""
        lose = 1.0
        dmg = [0.18, 0.2, 0.16, 0.22, 0.24]
        for i, th in enumerate(self.hits[:5]):
            if t >= th:
                lose -= dmg[i] * C.out_cubic(C.seg(t, th, th + 0.25))
        if t >= self.ko - 0.01:
            lose = 0.0
        win = 1.0 - (0.12 * C.seg(t, self.hits[1] + 0.4, self.hits[1] + 0.6))
        return max(0.0, lose), win

    def fight(self, fr, t):
        fr.alpha_composite(self.stage)
        lose_hp, win_hp = self.health(t)
        hp = {'h': win_hp if self.side == 'h' else lose_hp, 'a': win_hp if self.side == 'a' else lose_hp}
        # бойцы
        wk = 'h' if self.side == 'h' else 'a'
        lk = 'a' if wk == 'h' else 'h'
        base_x = {'h': W / 2 - 250, 'a': W / 2 + 250}
        xs, ys = dict(base_x), {'h': 900.0, 'a': 900.0}
        for k in ('h', 'a'):
            ys[k] += 18 * math.sin(t * 5 + (0 if k == 'h' else 1.5))
        last = None
        for th in self.hits:
            if t >= th:
                last = th
        dirw = 1 if wk == 'h' else -1
        if last is not None and t < self.ko + 0.8:
            q = C.seg(t, last - 0.12, last + 0.25)
            lunge = math.sin(min(1.0, q) * math.pi) * 150
            xs[wk] += dirw * lunge
            knock = C.out_cubic(C.seg(t, last, last + 0.2)) * (1 - C.seg(t, last + 0.2, last + 0.5))
            xs[lk] += dirw * 70 * knock
        if t >= self.ko:                                            # нокаут: проигравший падает
            q = C.out_cubic(C.seg(t, self.ko, self.ko + 0.6))
            xs[lk] += dirw * 260 * q
            ys[lk] += 260 * q
        for k in ('h', 'a'):
            e = self.emb_fight[k]
            if t >= self.ko and k == lk:
                e = C.rotate(e, -80 * dirw * C.out_cubic(C.seg(t, self.ko, self.ko + 0.6)))
                e = ImageOps.grayscale(e.convert('RGB')).convert('RGBA') if False else e
            sh = C.ellipse(300, 60, (0, 0, 0), 120)
            C.put(fr, sh, xs[k], 1200)
            refl = e.transpose(Image.FLIP_TOP_BOTTOM)
            C.put(fr, refl, xs[k], 1200 + refl.height / 2 + 10, 0.18)
            C.put(fr, e, xs[k], ys[k])
        # вспышки ударов
        for i, th in enumerate(self.hits[:5] + [self.ko]):
            if th <= t < th + 0.25:
                q = C.seg(t, th, th + 0.25)
                bx = xs[lk] - dirw * 120
                b = burst(int(160 + 140 * q), 12, YEL if i % 2 else WHITE, seed=i)
                C.put(fr, b, bx, ys[lk] - 40, 1 - q)
                C.put(fr, burst(int(80 + 60 * q), 10, RED, seed=i + 5), bx, ys[lk] - 40, 1 - q)
        # комбо
        n = sum(1 for th in self.hits[:5] if t >= th)
        if 2 <= n and t < self.ko:
            th = self.hits[n - 1]
            pk = C.out_back(C.seg(t, th, th + 0.2), 2.5)
            C.put(fr, italic(C.scale(C.text('КОМБО ×%d' % n, 'dela', 84, YEL, stroke=6, stroke_fill=(140, 30, 0)), max(0.1, pk))),
                  W / 2 + 160 * dirw, 600)
        # полоски здоровья и таймер
        for k, x0, flip in (('h', 40, False), ('a', W / 2 + 70, True)):
            bw, bh = W / 2 - 110, 52
            bar = C.rrect(bw, bh, 8, (60, 0, 0))
            fill_w = max(1, int(bw * hp[k]))
            col = YEL if hp[k] > 0.3 else RED
            f = C.rrect(fill_w, bh, 8, col)
            bar.alpha_composite(f, (int(bw - fill_w) if flip else 0, 0))
            ol = Image.new('RGBA', bar.size, (0, 0, 0, 0))
            ImageDraw.Draw(ol).rounded_rectangle((0, 0, bw - 1, bh - 1), 8, outline=WHITE + (255,), width=4)
            bar.alpha_composite(ol)
            C.put(fr, bar, x0, 280, anchor='tl')
            tm = self.h if k == 'h' else self.a
            nm = italic(C.text(tm.up, 'russo', 44, WHITE, stroke=4, stroke_fill=DARK, max_w=380))
            C.put(fr, nm, (x0 + 10) if not flip else (x0 + bw - nm.width - 10), 348, anchor='tl')
        clock = max(0, 99 - int((t - self.b(3)) * 6))
        C.put(fr, C.text('%02d' % clock, 'russo', 76, WHITE, stroke=5, stroke_fill=DARK), W / 2, 306)
        # «БОЙ!» / «K.O.»
        if self.b(3) <= t < self.b(4):
            k = C.out_back(C.seg(t, self.b(3), self.b(3) + 0.25), 2.2)
            C.put(fr, italic(C.scale(C.text('БОЙ!', 'dela', 230, YEL, stroke=12, stroke_fill=(140, 30, 0)), max(0.1, k))), W / 2, 700)
        if self.ko <= t < self.b(11.6):
            k = C.out_back(C.seg(t, self.ko + 0.1, self.ko + 0.4), 2.2)
            if k > 0:
                ko = italic(C.text('K.O.', 'dela', 300, RED, stroke=14, stroke_fill=(255, 230, 200)))
                C.put(fr, C.glow(C.scale(ko, max(0.1, k)), 26, 1.1, (255, 60, 40)), W / 2, 640)
        return fr

    def winner(self, fr, t):
        t0 = self.b(11.5)
        k = C.out_expo(C.seg(t, t0, t0 + 0.5))
        dim = Image.new('RGBA', (W, H), (6, 4, 12, int(215 * k)))
        fr.alpha_composite(dim)
        C.put(fr, italic(C.text('ПОБЕДИТЕЛЬ', 'russo', 70, YEL, stroke=5, stroke_fill=DARK)), W / 2, 330 - 40 * (1 - k), k)
        C.put(fr, C.glow(self.win.emb(380), 34, 1.0, YEL), W / 2, 640, k)
        pl = self._plate()
        C.put(fr, pl, W / 2, 1060 + 80 * (1 - k), k)
        if t >= self.b(13):
            k2 = C.out_expo(C.seg(t, self.b(13), self.b(13) + 0.4))
            C.put(fr, self._cta(), W / 2, 1340 + 50 * (1 - k2), k2)
        return fr

    def _plate(self):
        if not hasattr(self, '_pl'):
            w, h = 960, 290
            im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            body = C.polygon([(40, 0), (w, 0), (w - 40, h), (0, h)], (w, h), (20, 16, 30))
            im.alpha_composite(body)
            ol = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(ol).polygon([(40, 0), (w - 1, 0), (w - 41, h - 1), (0, h - 1)], outline=YEL + (255,), width=5)
            im.alpha_composite(ol)
            C.put(im, C.text('ПРОГНОЗ · %s · %s' % (self.league, self.when), 'russo', 34, (200, 200, 220)), w / 2, 56)
            C.put(im, italic(C.text(self.pick.upper(), 'dela', 74, WHITE, max_w=w - 120)), w / 2, 140)
            C.put(im, italic(C.text('КЭФ ' + C.fmt_k(self.coef), 'dela', 64, YEL)), w / 2, 225)
            self._pl = im
        return self._pl

    def _cta(self):
        if not hasattr(self, '_ct'):
            pl = C.rrect(860, 130, 65, C.TG_BLUE)
            C.put(pl, C.tg_icon(96, WHITE, C.TG_BLUE), 75, 65)
            C.put(pl, C.text('СЛЕДУЮЩИЙ БОЙ · ' + C.HANDLE, 'russo', 46, WHITE, max_w=680), 470, 65)
            self._ct = pl
        return self._ct

    def frame(self, t):
        D = self.drop
        fr = Image.new('RGBA', (W, H), DARK + (255,))
        if t < D:
            self.select(fr, t)
        elif t < self.b(3):
            self.versus(fr, t)
        else:
            self.fight(fr, t)
            if t >= self.b(11.5):
                self.winner(fr, t)
        # камера: удары трясут кадр
        dx = dy = 0.0
        z = 1.0
        for th in [D] + self.hits[:5] + [self.ko]:
            sx, sy = C.shake(t, th, 22 if th in (D, self.ko) else 12, 0.3)
            dx, dy = dx + sx, dy + sy
            if t >= th:
                z += 0.04 * (1 - C.seg(t, th, th + 0.3)) ** 2
        if self.ko <= t < self.ko + 0.8:                              # замедление на нокауте — наезд
            z += 0.06 * math.sin(C.seg(t, self.ko, self.ko + 0.8) * math.pi)
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        for th in [D, self.ko]:
            if th <= t < th + 0.18:
                fr = Image.blend(fr.convert('RGB'), Image.new('RGB', (W, H), (255, 255, 255)), 0.7 * (1 - C.seg(t, th, th + 0.18)))
        return C.vignette(fr, 0.45)
