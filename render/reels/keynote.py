# -*- coding: utf-8 -*-
"""«Матч дня» — один матч в светлом стиле презентации (родственник «Топ-3»).

Крючок «МАТЧ ДНЯ» выезжает из-под линии; на дропе — крупные эмблемы и названия; затем три «слайда» с большими
цифрами по очереди (шанс по нашему расчёту → кэф → время начала), каждый — на 2 доли; потом прогноз чёрной
плашкой и подписка. Мягкое свечение цветом фаворита, текст без пружин.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from reels import core as C
from reels.core import W, H
from reels.top3 import BG, GRAY, INK, reveal


class Keynote(C.Reel):
    def __init__(self, home, away, league, side, pick, coef, chance, when, time_msk, fav_gen, u=1.0, drop=3.0, seed=97):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.fav = self.h if side == 'h' else self.a
        self.pick, self.coef, self.chance, self.when, self.time_msk, self.fav_gen = pick, coef, chance, when, time_msk, fav_gen
        self.league = 'НХЛ' if str(league).upper() == 'NHL' else 'КХЛ'
        self.stats = [('%d%%' % chance, 'шанс %s на победу — по нашему расчёту' % fav_gen),
                      (C.fmt_k(coef), 'коэффициент на победу %s' % fav_gen),
                      (time_msk, 'начало матча по Москве')]
        self.t_stats = [self.b(3 + 2 * i) for i in range(len(self.stats))]
        self.t_pick = self.b(9.5)
        self.t_cta = self.b(12.5)
        self.dur = self.b(15.5)
        self.cover_t = self.b(11.5)
        rnd = np.random.default_rng(seed)
        arr = np.ones((H, W, 3), np.float32) * np.array(BG, np.float32) + rnd.normal(0, 2.2, (H, W))[..., None]
        self.bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        self.blob = C.radial(1400, 1400, (255, 255, 255), 255, 1.3)
        self.e1, self.e2 = self.h.emb(330), self.a.emb(330)
        lum = lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
        self.col = self.fav.c1 if lum(self.fav.c1) < 140 else self.fav.c0          # цвет цифр — тёмный клубный

    def tint(self, col, a):
        b = Image.new('RGBA', self.blob.size, tuple(col) + (0,))
        b.putalpha(self.blob.getchannel('A').point(lambda v: int(v * a)))
        return b

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        fr.alpha_composite(self.tint(self.col, 0.22), (int(-300 + 60 * math.sin(t * 0.3)), 300))
        other = self.a if self.fav is self.h else self.h
        fr.alpha_composite(self.tint(other.c1, 0.10), (200, 900))
        if t < D:
            q = C.seg(t, 0.15, 0.7)
            im, _ = reveal(C.text('МАТЧ', 'unb', 250, INK, 900, max_w=940), q)
            C.put(fr, im, 70, 560, anchor='tl')
            im, _ = reveal(C.text('ДНЯ', 'unb', 250, INK, 900, max_w=940), C.seg(t, 0.35, 0.9))
            C.put(fr, im, 70, 820, anchor='tl')
            d = ImageDraw.Draw(fr)
            d.line((80, 1110, 80 + 900 * C.out_expo(C.seg(t, 0.6, 1.8)), 1110), fill=INK + (255,), width=8)
            C.put(fr, C.text('%s · %s' % (self.league, self.when), 'mono', 42, GRAY, 700, track=0.2), 80, 1150, C.seg(t, 1.2, 1.6), anchor='tl')
        else:
            # эмблемы и названия: на дропе выезжают, потом уходят вверх и уменьшаются
            k = C.out_expo(C.seg(t, D, D + 0.6))
            up = C.in_out(C.seg(t, self.t_stats[0] - 0.4, self.t_stats[0] + 0.2))
            s = 1.0 - 0.45 * up
            y = 700 - 260 * up
            C.put(fr, C.with_shadow(C.scale(self.e1, s), 18, 0.2, 12), W / 2 - 230 * (1 - 0.25 * up) - (1 - k) * 600, y)
            C.put(fr, C.with_shadow(C.scale(self.e2, s), 18, 0.2, 12), W / 2 + 230 * (1 - 0.25 * up) + (1 - k) * 600, y)
            C.put(fr, C.text('—', 'unb', int(80 * s), INK, 800), W / 2, y, k)
            na = 1 - up
            if na > 0.01:
                im, _ = reveal(C.text('%s — %s' % (self.h.up, self.a.up), 'unb', 70, INK, 900, max_w=960), C.seg(t, D + 0.2, D + 0.7))
                C.put(fr, im, W / 2, 1010, na)
                C.put(fr, C.text('%s · %s' % (self.league, self.when), 'mono', 40, GRAY, 700, track=0.15), W / 2, 1100, na * C.seg(t, D + 0.5, D + 0.9))
            # слайды с цифрами
            for i, (num, cap) in enumerate(self.stats):
                t0 = self.t_stats[i]
                t1 = self.t_stats[i + 1] if i + 1 < len(self.stats) else self.t_pick
                if not (t0 <= t < t1 + 0.4):
                    continue
                q = C.seg(t, t0, t0 + 0.5)
                out = C.in_cubic(C.seg(t, t1 - 0.05, t1 + 0.35))
                col = C.mix(self.col, INK, 0.1)
                nm, _ = reveal(C.text(num, 'unb', 300, col, 900, max_w=960), q)
                C.put(fr, nm, 70, 640 - 120 * out, 1 - out, anchor='tl')
                cp = C.lines(cap, 'golos', 58, 920, INK, 600, gap=0.15, align='l', max_lines=2)
                cpi, _ = reveal(cp, C.seg(t, t0 + 0.2, t0 + 0.7))
                C.put(fr, cpi, 80, 990 - 120 * out, 1 - out, anchor='tl')
                x = 80                                                  # точки-индикатор
                for j in range(len(self.stats)):
                    on = j == i
                    dot = C.rrect(64 if on else 22, 22, 11, INK if on else (200, 200, 205))
                    C.put(fr, dot, x, 1250, 1 - out, anchor='tl')
                    x += dot.width + 16
            # прогноз
            if t >= self.t_pick:
                q = C.out_expo(C.seg(t, self.t_pick, self.t_pick + 0.5))
                C.put(fr, C.text('ПРОГНОЗ', 'mono', 44, GRAY, 700, track=0.4), 80, 640, C.seg(t, self.t_pick, self.t_pick + 0.3), anchor='tl')
                tx = C.text(self.pick.upper(), 'unb', 64, (255, 255, 255), 800, max_w=860)
                pl = C.rrect(tx.width + 100, 150, 75, INK)
                C.put(pl, tx, pl.width / 2, 75)
                w = max(2, int(pl.width * q))
                C.put(fr, pl.crop((0, 0, w, pl.height)), 80, 720, anchor='tl')
                if t >= self.t_pick + 0.8 * u:
                    q2 = C.seg(t, self.t_pick + 0.8 * u, self.t_pick + 1.2 * u)
                    tk = C.text('КЭФ %s · ШАНС %d%%' % (C.fmt_k(self.coef), self.chance), 'unb', 54, INK, 800)
                    kp = C.rrect(tk.width + 90, 140, 70, C.mix(self.col, (255, 255, 255), 0.7))
                    C.put(kp, tk, kp.width / 2, 70)
                    im, _ = reveal(kp, q2)
                    C.put(fr, im, 80, 900, anchor='tl')
            if t >= self.t_cta:
                q = C.out_expo(C.seg(t, self.t_cta, self.t_cta + 0.5))
                im, _ = reveal(C.text('ПОДРОБНЫЙ РАЗБОР —', 'unb', 58, INK, 900, max_w=920), q)
                C.put(fr, im, 80, 1110, anchor='tl')
                pl = C.rrect(900, 150, 75, C.TG_BLUE)
                C.put(pl, C.tg_icon(110, (255, 255, 255), C.TG_BLUE), 85, 75)
                C.put(pl, C.text('В TELEGRAM ' + C.HANDLE, 'unb', 48, (255, 255, 255), 800, max_w=680), 500, 75)
                w = max(2, int(pl.width * C.out_expo(C.seg(t, self.t_cta + 0.3, self.t_cta + 0.8))))
                C.put(fr, pl.crop((0, 0, w, pl.height)), 80, 1210, anchor='tl')
        z = 1.0 + 0.02 * math.sin(t * 0.35)
        dx, dy = C.shake(t, D, 6, 0.25)
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        return C.grain(fr, t, 2)
