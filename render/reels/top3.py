# -*- coding: utf-8 -*-
"""«Топ-3» — три прогноза дня обратным отсчётом, светлый стиль презентации.

Светлый фон с мягким цветным свечением (цвет клуба), гигантская цифра места с заливкой цветами клуба,
текст выезжает из-под линии (без пружин), на каждую долю — следующий слой: эмблемы и матч → прогноз
чёрной плашкой → кэф. Переход между местами — «сквозь цифру»: она вырастает во весь кадр и открывает
следующую. Крючок до дропа — «ТОП-3 ПРОГНОЗА НА СУББОТУ», в конце — подписка.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels.core import W, H

BG = (246, 245, 241)
INK = (14, 14, 18)
GRAY = (120, 122, 130)


def reveal(im, p):
    """Текст выезжает снизу из-под невидимой линии (маска по нижнему краю)."""
    if p >= 1:
        return im, 0
    h = im.height
    off = int(h * (1 - C.out_expo(p)))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(im.crop((0, 0, im.width, h - off)), (0, off))
    return out, off


class Top3(C.Reel):
    def __init__(self, title, picks, u=1.0, drop=2.0, seg=4, seed=23):
        """picks — от 3-го места к 1-му: [(хозяева, гости, лига, прогноз, кэф, 'СБ 10.10 · 17:00 МСК', сторона), ...]"""
        super().__init__(u, drop, seed)
        self.title = title
        self.picks = []
        for h, a, lg, pk, k, when, side in picks:
            th, ta = C.match(h, a, lg)
            self.picks.append(dict(h=th, a=ta, league='НХЛ' if lg == 'NHL' else 'КХЛ', pick=pk, coef=k, when=when,
                                   fav=th if side == 'h' else ta))
        self.seg = seg
        self.t_cta = self.b(seg * len(self.picks))
        self.dur = self.t_cta + 4 * u
        self.cover_t = self.b(seg * 2 + 2.6)
        self._prep()

    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        arr = np.ones((H, W, 3), np.float32) * np.array(BG, np.float32) + rnd.normal(0, 2.2, (H, W))[..., None]
        self.bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        self.blob = C.radial(1300, 1300, (255, 255, 255), 255, 1.3)
        self.nums = {}
        for i, p in enumerate(self.picks):
            n = len(self.picks) - i
            m = C.text(str(n), 'unb', 1250, (255, 255, 255), 900)
            g = C.lgrad(m.width, m.height, C.mix(p['fav'].c1, (255, 255, 255), 0.1), C.mix(p['fav'].c1, INK, 0.35), 60)
            g.putalpha(m.getchannel('A'))
            self.nums[i] = g

    def tint_blob(self, col, a):
        b = Image.new('RGBA', self.blob.size, tuple(col) + (0,))
        b.putalpha(self.blob.getchannel('A').point(lambda v: int(v * a)))
        return b

    def scene(self, fr, i, t, t0):
        u = self.u
        p = self.picks[i]
        lt = t - t0
        # свечение цветом фаворита
        fr.alpha_composite(self.tint_blob(p['fav'].c1, 0.30), (int(-250 + 40 * math.sin(t * 0.4)), 200))
        fr.alpha_composite(self.tint_blob(p['h'].c1 if p['fav'] is p['a'] else p['a'].c1, 0.14), (300, 900))
        # цифра (параллакс: медленно уезжает)
        num = self.nums[i]
        k0 = C.out_expo(C.seg(t, t0, t0 + 0.6))
        x = W - num.width / 2 + 420 - 60 * C.seg(t, t0, t0 + self.seg * u)
        C.put(fr, num, x + (1 - k0) * 300, 900, k0)
        # место
        C.put(fr, C.text('МЕСТО %d' % (len(self.picks) - i), 'mono', 44, GRAY, 700, track=0.4), 100, 400, C.seg(t, t0, t0 + 0.3), anchor='tl')
        # эмблемы и матч
        if lt >= 0.6 * u:
            q = C.seg(t, t0 + 0.6 * u, t0 + 1.0 * u)
            e1, e2 = p['h'].emb(230), p['a'].emb(230)
            C.put(fr, C.with_shadow(e1, 16, 0.25, 12), 220, 680 + 40 * (1 - C.out_expo(q)), q)
            C.put(fr, C.with_shadow(e2, 16, 0.25, 12), 480, 680 + 40 * (1 - C.out_expo(q)), C.seg(t, t0 + 0.75 * u, t0 + 1.1 * u))
            m1, _ = reveal(C.text(p['h'].up, 'unb', 70, INK, 800, max_w=760), q)
            m2, _ = reveal(C.text(p['a'].up, 'unb', 70, INK, 800, max_w=760), C.seg(t, t0 + 0.7 * u, t0 + 1.1 * u))
            C.put(fr, m1, 100, 880, anchor='tl')
            C.put(fr, m2, 100, 970, anchor='tl')
            C.put(fr, C.text('%s · %s' % (p['league'], p['when']), 'mono', 34, (70, 72, 80), 700), 100, 1080, C.seg(t, t0 + 0.9 * u, t0 + 1.2 * u), anchor='tl')
        # прогноз
        if lt >= 1.6 * u:
            q = C.seg(t, t0 + 1.6 * u, t0 + 2.0 * u)
            pl = self.plate(i)
            w = int(pl.width * C.out_expo(q))
            if w > 2:
                C.put(fr, pl.crop((0, 0, w, pl.height)), 100, 1160, anchor='tl')
        if lt >= 2.4 * u:
            q = C.seg(t, t0 + 2.4 * u, t0 + 2.8 * u)
            kp = self.kef(i)
            img, _ = reveal(kp, q)
            C.put(fr, img, 100, 1320, anchor='tl')
        return fr

    def plate(self, i):
        key = ('pl', i)
        if not hasattr(self, '_c'):
            self._c = {}
        if key not in self._c:
            p = self.picks[i]
            tx = C.text(p['pick'].upper(), 'unb', 54, (255, 255, 255), 800, max_w=820)
            im = C.rrect(tx.width + 90, 130, 65, INK)
            C.put(im, tx, im.width / 2, 65)
            self._c[key] = im
        return self._c[key]

    def kef(self, i):
        key = ('kf', i)
        if key not in self._c:
            p = self.picks[i]
            tx = C.text('КЭФ ' + C.fmt_k(p['coef']), 'unb', 54, INK, 800)
            im = C.rrect(tx.width + 90, 130, 65, C.mix(p['fav'].c1, (255, 255, 255), 0.55))
            C.put(im, tx, im.width / 2, 65)
            self._c[key] = im
        return self._c[key]

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        if t < D:
            # крючок: строки выезжают из-под линии
            words = self.title.split('|')
            y = 520
            for j, s in enumerate(words):
                q = C.seg(t, 0.1 + j * 0.2, 0.6 + j * 0.2)
                tx = C.text(s, 'unb', 290 if j == 0 else 112, INK, 900 if j == 0 else 800, max_w=920)
                im, _ = reveal(tx, q)
                C.put(fr, im, 80, y, anchor='tl')
                y += tx.height + (30 if j == 0 else 14)
            d = ImageDraw.Draw(fr)
            d.line((90, y + 40, 90 + 900 * C.out_expo(C.seg(t, 0.3, 1.4)), y + 40), fill=INK + (255,), width=8)
            C.put(fr, C.text('КХЛ + НХЛ · ПО ВЕРОЯТНОСТИ', 'mono', 40, GRAY, 700, track=0.2), 90, y + 80, C.seg(t, 0.8, 1.2), anchor='tl')
        elif t < self.t_cta:
            i = int((t - D) / (self.seg * u))
            t0 = D + i * self.seg * u
            self.scene(fr, i, t, t0)
            # переход «сквозь цифру» в последние 0.45 доли
            te = t0 + self.seg * u
            if t >= te - 0.45 * u:
                q = C.in_cubic(C.seg(t, te - 0.45 * u, te))
                p = self.picks[i]
                cover = Image.new('RGBA', (W, H), tuple(C.mix(p['fav'].c1, INK, 0.2)) + (int(255 * q),))
                num = C.scale(self.nums[i], 1 + 7 * q)
                C.put(fr, num, W / 2, H / 2, min(1.0, q * 2))
                fr.alpha_composite(cover)
            if t < t0 + 0.25 * u and i > 0:                     # вход после перехода: цвет уходит
                pv = self.picks[i - 1]
                q = 1 - C.seg(t, t0, t0 + 0.25 * u)
                fr.alpha_composite(Image.new('RGBA', (W, H), tuple(C.mix(pv['fav'].c1, INK, 0.2)) + (int(255 * q),)))
        else:
            q = C.seg(t, self.t_cta, self.t_cta + 0.5 * u)
            fr.alpha_composite(self.tint_blob(C.TG_BLUE, 0.25), (-100, 300))
            im, _ = reveal(C.text('ВСЕ ПРОГНОЗЫ', 'unb', 104, INK, 900, max_w=920), q)
            C.put(fr, im, 90, 680, anchor='tl')
            im, _ = reveal(C.text('КАЖДЫЙ ДЕНЬ', 'unb', 104, INK, 900, max_w=920), C.seg(t, self.t_cta + 0.15, self.t_cta + 0.65))
            C.put(fr, im, 90, 820, anchor='tl')
            if t >= self.t_cta + 0.6 * u:
                k = C.out_expo(C.seg(t, self.t_cta + 0.6 * u, self.t_cta + 1.1 * u))
                pl = C.rrect(800, 150, 75, C.TG_BLUE)
                C.put(pl, C.tg_icon(110, (255, 255, 255), C.TG_BLUE), 85, 75)
                C.put(pl, C.text('TELEGRAM ' + C.HANDLE, 'unb', 46, (255, 255, 255), 800, max_w=600), 470, 75)
                w = max(2, int(pl.width * k))
                C.put(fr, pl.crop((0, 0, w, pl.height)), 90, 1030, anchor='tl')
        z = 1.0 + 0.02 * math.sin(t * 0.35)
        dx, dy = C.shake(t, D, 6, 0.25)
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        return C.grain(fr, t, 2)
