# -*- coding: utf-8 -*-
"""«Итоги ночи» — экран биржевого терминала: банк растёт по ходу ночи.

Крючок — сразу итог («+1.38 ЕД.», «4 ИЗ 6»); на дропе — «КАК ШЛА НОЧЬ»: график прибыли рисуется матч за
матчем (каждые 2 доли — точка), карточка текущего матча (эмблемы, счёт, прогноз, «+1.05» зелёным или «−1.00»
красным), бегущая строка с результатами; в конце — итог, ROI и подписка. Проигрыши показываем честно.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels.core import W, H

BG = (11, 14, 17)
PANEL = (22, 26, 30)
LINE = (43, 49, 57)
GREEN = (14, 203, 129)
RED = (246, 70, 93)
GRAY = (132, 142, 156)
WHITE = (234, 236, 239)


def tri(size, up=True, col=GREEN):
    s = size
    pts = [(0, s), (s / 2, 0), (s, s)] if up else [(0, 0), (s, 0), (s / 2, s)]
    return C.polygon(pts, (s, s), col)


class Results(C.Reel):
    def __init__(self, title, date, league, bets, u=0.9375, drop=1.875, seed=3):
        """bets = [(хозяева, гости, 'счёт', 'прогноз', прибыль), ...] в порядке начала матчей."""
        super().__init__(u, drop, seed)
        self.title, self.date = title, date
        self.bets = [(C.match(h, a, league), sc, pk, pr) for h, a, sc, pk, pr in bets]
        self.cum = list(np.cumsum([b[3] for b in self.bets]))
        self.total = self.cum[-1]
        self.wins = sum(1 for b in self.bets if b[3] > 0)
        self.roi = self.total / len(self.bets) * 100
        self.dur = self.b(2 * len(self.bets) + 6.5)
        self.cover_t = self.b(2 * len(self.bets) + 1.5)
        self.bg = Image.new('RGBA', (W, H), BG + (255,))
        self.ticker = self._ticker()

    def tb(self, i):
        return self.b(2 * i)

    def _ticker(self):
        parts = []
        for (h, a), sc, pk, pr in self.bets:
            col = GREEN if pr > 0 else RED
            parts.append((('%s—%s %s' % (h.up, a.up, sc)), WHITE))
            parts.append((('%+.2f' % pr), col))
            parts.append(('  ·  ', GRAY))
        ims = [C.text(s, 'mono', 30, c, 700, trim=False) for s, c in parts]
        w = sum(i.width for i in ims)
        im = Image.new('RGBA', (w * 2, max(i.height for i in ims)), (0, 0, 0, 0))
        x = 0
        for rep in range(2):
            for i in ims:
                im.alpha_composite(i, (x, 0))
                x += i.width
        return im

    def value(self, t):
        """Текущее значение банка на графике (плавно между точками)."""
        if t < self.drop:
            return self.total
        v = 0.0
        for i, c in enumerate(self.cum):
            t0 = self.tb(i)
            if t >= t0:
                prev = self.cum[i - 1] if i else 0.0
                v = C.lerp(prev, c, C.out_cubic(C.seg(t, t0, t0 + 0.5 * self.u)))
        return v

    def chart(self, t):
        w, h = 960, 430
        im = C.rrect(w, h, 26, PANEL)
        d = ImageDraw.Draw(im)
        lo, hi = min(min(self.cum), 0) - 0.4, max(max(self.cum), 0) + 0.5
        yv = lambda v: 30 + (hi - v) / (hi - lo) * (h - 60)
        n = len(self.bets)
        xv = lambda i: 70 + i * (w - 140) / n
        for v in np.arange(math.ceil(lo), math.floor(hi) + 1):
            d.line((50, yv(v), w - 30, yv(v)), fill=LINE + (255,), width=1)
            d.text((14, yv(v) - 12), '%+d' % v if v else '0', font=C.font('mono', 22, 600), fill=GRAY + (255,))
        for x in range(50, w - 30, 22):                       # ноль — пунктиром
            d.line((x, yv(0), x + 11, yv(0)), fill=(90, 98, 110, 255), width=2)
        if t >= self.drop:
            pts = [(xv(0), yv(0))]
            for i, c in enumerate(self.cum):
                t0 = self.tb(i)
                if t < t0:
                    break
                k = C.out_cubic(C.seg(t, t0, t0 + 0.5 * self.u))
                px, py = pts[-1]
                pts.append((C.lerp(px, xv(i + 1), k), C.lerp(py, yv(c), k)))
            # заливка под линией
            v = self.value(t)
            col = GREEN if v >= 0 else RED
            if len(pts) > 1:
                poly = pts + [(pts[-1][0], yv(0)), (pts[0][0], yv(0))]
                fill = Image.new('RGBA', (w, h), (0, 0, 0, 0))
                ImageDraw.Draw(fill).polygon(poly, fill=col + (60,))
                im.alpha_composite(fill)
                d = ImageDraw.Draw(im)
                d.line(pts, fill=col + (255,), width=7, joint='curve')
                for j, (x, y) in enumerate(pts[1:]):
                    pr = self.bets[j][3]
                    c2 = GREEN if pr > 0 else RED
                    d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=BG + (255,), outline=c2 + (255,), width=5)
                x, y = pts[-1]
                d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=WHITE + (255,))
        return im

    def card(self, i, t):
        (h, a), sc, pk, pr = self.bets[i]
        key = ('card', i)
        if not hasattr(self, '_cards'):
            self._cards = {}
        if key not in self._cards:
            w, hh = 960, 330
            im = C.rrect(w, hh, 26, PANEL)
            C.put(im, h.emb(120), 100, 110)
            C.put(im, a.emb(120), 250, 110)
            nm = C.text('%s — %s' % (h.up, a.up), 'onest', 40, WHITE, 800, max_w=470)
            C.put(im, nm, 350, 82 - nm.height / 2, anchor='tl')
            C.put(im, C.text('счёт ' + sc, 'onest', 36, GRAY, 600), 350, 118, anchor='tl')
            C.put(im, C.text('ПРОГНОЗ', 'mono', 24, GRAY, 700, track=0.2), 60, 220, anchor='tl')
            C.put(im, C.text(pk, 'onest', 46, WHITE, 800, max_w=560), 60, 254, anchor='tl')
            col = GREEN if pr > 0 else RED
            chip = C.rrect(300, 132, 24, col, 40, outline=col, width=3)
            C.put(chip, C.text('ЗАШЁЛ' if pr > 0 else 'МИМО', 'mono', 28, col, 800, track=0.2), 150, 36)
            C.put(chip, C.text('%+.2f' % pr if pr > 0 else '−%.2f' % abs(pr), 'onest', 60, col, 800), 150, 90)
            C.put(im, chip, w - 190, 236)
            C.put(im, C.text('%d/%d' % (i + 1, len(self.bets)), 'mono', 26, GRAY, 700), w - 70, 50)
            self._cards[key] = im
        return self._cards[key]

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        # шапка
        C.put(fr, C.text('JRVS / ' + self.title, 'onest', 44, WHITE, 800), 60, 236, anchor='tl')
        C.put(fr, C.text(self.date, 'mono', 30, GRAY, 600), W - 60 - C.text(self.date, 'mono', 30, GRAY, 600).width, 246, anchor='tl')
        # бегущая строка
        off = int((t * 140) % (self.ticker.width / 2))
        strip = self.ticker.crop((off, 0, off + W, self.ticker.height))
        C.put(fr, C.rrect(W, 64, 0, (16, 19, 23)), W / 2, 330)
        C.put(fr, strip, 0, 330 - strip.height / 2, anchor='tl')
        # баланс
        v = self.value(t)
        col = GREEN if v >= 0 else RED
        s = ('+%.2f' % v) if v >= 0 else ('−%.2f' % abs(v))
        pop = 1.0
        for i in range(len(self.bets)):
            if t >= self.tb(i):
                pop = 1 + 0.06 * (1 - C.seg(t, self.tb(i), self.tb(i) + 0.3))
        big = C.scale(C.text(s, 'onest', 170, col, 800), pop)
        x0 = 60
        C.put(fr, tri(56, v >= 0, col), x0 + 28, 500)
        C.put(fr, big, x0 + 80, 500 - big.height / 2, anchor='tl')
        C.put(fr, C.text('ЕД.', 'onest', 60, col, 800), x0 + 100 + big.width, 520 - 30, anchor='tl')
        if t < D or t >= self.tb(len(self.bets) - 1) + u:
            k = 1.0 if t < D else C.seg(t, self.tb(len(self.bets) - 1) + u, self.tb(len(self.bets) - 1) + 1.5 * u)
            C.put(fr, C.text('%d ИЗ %d · ROI %+d%%' % (self.wins, len(self.bets), round(self.roi)), 'onest', 52, WHITE, 700), 60, 600, k, anchor='tl')
        else:
            n = sum(1 for i in range(len(self.bets)) if t >= self.tb(i))
            C.put(fr, C.text('КАК ШЛА НОЧЬ · МАТЧ %d ИЗ %d' % (n, len(self.bets)), 'onest', 44, GRAY, 700), 60, 606, anchor='tl')
        # график
        C.put(fr, self.chart(t), W / 2, 905)
        # карточка матча
        if D <= t < self.tb(len(self.bets) - 1) + 2 * u:
            i = max(j for j in range(len(self.bets)) if t >= self.tb(j))
            p = C.out_expo(C.seg(t, self.tb(i), self.tb(i) + 0.35 * u))
            cd = self.card(i, t)
            C.put(fr, cd, W / 2 + (1 - p) * 120, 1300, p)
        if t < D:
            C.put(fr, C.text('КАК ШЛА НОЧЬ →', 'onest', 56, WHITE, 800), W / 2, 1300, C.seg(t, 0.4, 0.8))
        tf = self.tb(len(self.bets) - 1) + 2 * u
        if t >= tf:
            k = C.out_expo(C.seg(t, tf, tf + 0.5 * u))
            C.put(fr, self._cta(), W / 2, 1300 + 50 * (1 - k), k)
        # толчки на каждом матче
        dx, dy = 0.0, 0.0
        for i in range(len(self.bets)):
            sx, sy = C.shake(t, self.tb(i), 9, 0.3)
            dx, dy = dx + sx, dy + sy
        fr = C.zoom(fr, 1.0 + 0.012 * math.sin(t * 0.6), dx=dx, dy=dy)
        return C.vignette(fr, 0.35)

    def _cta(self):
        if not hasattr(self, '_ct'):
            w, h = 960, 330
            im = C.rrect(w, h, 26, PANEL, outline=C.TG_BLUE, width=3)
            C.put(im, C.text('КАЖДЫЙ ПРОГНОЗ — ДО МАТЧА', 'onest', 40, WHITE, 800), w / 2, 70)
            C.put(im, C.text('и честные итоги после', 'onest', 34, GRAY, 600), w / 2, 120)
            pl = C.rrect(720, 120, 60, C.TG_BLUE)
            C.put(pl, C.tg_icon(90, (255, 255, 255), C.TG_BLUE), 70, 60)
            C.put(pl, C.text('TELEGRAM ' + C.HANDLE, 'onest', 46, (255, 255, 255), 800, max_w=560), 400, 60)
            C.put(im, pl, w / 2, 236)
            self._ct = im
        return self._ct
