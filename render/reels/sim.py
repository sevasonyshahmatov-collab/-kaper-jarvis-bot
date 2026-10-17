# -*- coding: utf-8 -*-
"""«JARVIS считает» — экран ИИ-ассистента: матч прогоняется 10 000 раз.

До дропа — терминал набирает строки («загружаю матч…», «запускаю 10 000 симуляций»), вокруг эмблем
собираются прицелы. На дропе — вспышка, эмблемы в цвет, счётчик симуляций бежит до 10 000, проценты клубов
живут и сходятся, график шанса рисуется в реальном времени (симуляция настоящая: пуассоновские голы и
овертайм), дальше — вердикт: шанс → честный кэф против кэфа линии (перевес), финал — подписка.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels.core import W, H

BG = (4, 9, 16)
CY = (90, 220, 255)
CY_D = (24, 70, 96)
WHITE = (236, 248, 255)
N = 10000


class Sim(C.Reel):
    def __init__(self, home, away, league, side, pick, coef, when, lam=(2.8, 3.3), u=1.0, drop=3.0, seed=21):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.side = side                  # 'h' / 'a' — за кого прогноз
        self.pick, self.coef, self.when = pick, coef, when
        self.league = 'НХЛ' if str(league).upper() == 'NHL' else 'КХЛ'
        rng = np.random.default_rng(seed)
        gh, ga = rng.poisson(lam[0], N), rng.poisson(lam[1], N)
        ot = rng.random(N) < 0.5
        win_h = (gh > ga) | ((gh == ga) & ot)
        self.cum_h = np.cumsum(win_h) / np.arange(1, N + 1)
        self.p = self.cum_h[-1] if side == 'h' else 1 - self.cum_h[-1]
        self.fair = 1 / self.p
        self.edge = self.p * coef - 1
        self.t_sim = (self.drop, self.b(5))
        self.dur = self.b(11.5)
        self.cover_t = self.b(7.6)
        self._prep()

    def _prep(self):
        bg = Image.new('RGBA', (W, H), BG + (255,))
        d = ImageDraw.Draw(bg)
        for x in range(0, W, 54):                       # точечная сетка
            for y in range(0, H, 54):
                d.point((x, y), fill=(30, 60, 80, 255))
                d.point((x + 1, y), fill=(30, 60, 80, 255))
        bg = C.add_light(bg, C.radial(1400, 1400, (0, 60, 90), 255, 2.0), W / 2, 600, 0.7)
        self.bg = bg
        sl = np.zeros((H, W, 4), np.uint8)              # строки экрана
        sl[::4, :, 3] = 26
        self.scan = Image.fromarray(sl, 'RGBA')
        self.emb = {k: t.emb(250) for k, t in (('h', self.h), ('a', self.a))}
        self.emb_g = {k: C.tint(e, CY, 0.85) for k, e in self.emb.items()}
        self.term = ['> матч: %s — %s · %s' % (self.h.up, self.a.up, self.league),
                     '> состав, форма, броски, вратари ... ok',
                     '> запускаю 10 000 симуляций']

    def reticle(self, t, k=1.0, col=CY):
        """Прицел вокруг эмблемы: дуги крутятся в разные стороны."""
        S = 460
        im = Image.new('RGBA', (S * 2, S * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = S
        for r, n, sp, wd, al in ((330, 3, 40, 10, 230), (290, 6, -70, 4, 160), (360, 24, 15, 3, 120)):
            span = 360 / n
            for i in range(n):
                a0 = i * span + t * sp
                d.arc((c - r, c - r, c + r, c + r), a0, a0 + span * 0.55 * k, fill=tuple(col) + (al,), width=wd)
        for i in range(4):                             # засечки
            ang = math.radians(i * 90 + t * 10)
            x1, y1 = c + 300 * math.cos(ang), c + 300 * math.sin(ang)
            x2, y2 = c + 378 * math.cos(ang), c + 378 * math.sin(ang)
            d.line((x1, y1, x2, y2), fill=tuple(col) + (220,), width=5)
        return im.resize((S, S), Image.LANCZOS)

    def chart(self, t):
        """График шанса по мере симуляций (живой, сходится)."""
        w, h = 960, 300
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, w - 1, h - 1), outline=CY_D + (255,), width=2)
        for k in range(1, 4):
            d.line((0, h * k / 4, w, h * k / 4), fill=(20, 50, 66, 255), width=1)
        y50 = h / 2
        d.line((0, y50, w, y50), fill=(60, 110, 130, 255), width=2)
        n = self.nsim(t)
        if n >= 2:
            # логарифмическая шкала по x: начало видно подробно
            xs = np.unique(np.clip(np.logspace(math.log10(30), math.log10(max(n, 31)), 300).astype(int), 1, n)) - 1
            ser = self.cum_h if self.side == 'h' else 1 - self.cum_h
            pts = [(w * (math.log10(i + 1) - math.log10(30)) / (4.0 - math.log10(30)), y50 - (ser[i] - 0.5) * h * 1.8) for i in xs]
            pts = [(x, C.clamp(y, 4, h - 4)) for x, y in pts]
            d.line(pts, fill=CY + (255,), width=5, joint='curve')
            x, y = pts[-1]
            d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=WHITE + (255,))
        im = C.glow(im, 8, 0.8, CY)
        return im

    def nsim(self, t):
        a, b = self.t_sim
        return int(round(N * C.in_out(C.seg(t, a, b)) ** 1.6))

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        # шапка
        C.put(fr, C.text('JARVIS · СИМУЛЯЦИЯ МАТЧА', 'mono', 34, CY, 700, track=0.25), W / 2, 262)
        C.put(fr, C.text('%s · %s' % (self.league, self.when), 'mono', 28, (110, 160, 180), 500, track=0.12), W / 2, 312)
        # эмблемы в прицелах
        k_ret = C.out_expo(C.seg(t, 0, 1.6))
        for side, x in (('h', W / 2 - 262), ('a', W / 2 + 262)):
            col = CY if t < D else (self.h if side == 'h' else self.a).c1
            col = C.mix(col, WHITE, 0.25) if t >= D else col
            r = self.reticle(t * (1 if side == 'h' else -1), k_ret, CY if t < D else col)
            pulse = 1 + 0.05 * max(0.0, 1 - ((t - D) % u) / (0.35 * u)) * (t >= D)
            C.put(fr, C.scale(r, pulse), x, 600)
            e = self.emb_g[side] if t < D else self.emb[side]
            C.put(fr, C.scale(e, 0.92), x, 600, 0.35 + 0.65 * C.seg(t, 0, 1.2))
        C.put(fr, C.text('VS', 'tek', 60, WHITE, 800), W / 2, 600, C.seg(t, 0.5, 1.2))
        # проценты (после дропа — живые)
        n = self.nsim(t)
        if t >= D:
            ph = self.cum_h[max(0, n - 1)] if n > 0 else 0.5
            for side, x, p in (('h', W / 2 - 262, ph), ('a', W / 2 + 262, 1 - ph)):
                mine = side == self.side
                col = WHITE if mine else (120, 150, 165)
                C.put(fr, C.text('%d%%' % round(p * 100), 'tek', 130 if mine else 96, col, 800), x, 900)
                C.put(fr, C.text((self.h if side == 'h' else self.a).up, 'mono', 34, (130, 175, 195), 700, track=0.1), x, 985)
            # счётчик симуляций
            ca = 1 - C.seg(t, self.b(6), self.b(6.3))
            C.put(fr, C.text('СИМУЛЯЦИЙ', 'mono', 30, (110, 160, 180), 700, track=0.3), W / 2 - 250, 1080, ca)
            C.put(fr, C.text('{:,}'.format(n).replace(',', ' '), 'tek', 96, CY, 800), W / 2 + 120, 1080, ca)
            ch = self.chart(t)
            C.put(fr, ch, W / 2, 1320)
        # терминал до дропа
        if t < D + 0.4:
            a = 1 - C.seg(t, D, D + 0.4)
            y = 1060
            for i, s in enumerate(self.term):
                t0 = 0.2 + i * u * 0.95
                if t < t0:
                    break
                n_ch = int(len(s) * C.seg(t, t0, t0 + 0.6 * u))
                caret = '█' if (int(t * 4) % 2 == 0 and n_ch < len(s)) or (i == len(self.term) - 1 and n_ch == len(s)) else ''
                C.put(fr, C.text(s[:n_ch] + caret, 'mono', 34, CY if i < 2 else WHITE, 600, trim=False), 90, y + i * 66, a, anchor='tl')
            if t < D:
                p = C.seg(t, self.b(-1), D)
                bar = C.rrect(900, 26, 13, CY_D)
                fill = C.rrect(max(26, int(900 * p)), 26, 13, CY)
                bar.alpha_composite(fill, (0, 0))
                C.put(fr, bar, W / 2, 1330, C.seg(t, self.b(-1), self.b(-0.8)))
        # вердикт
        tv = self.b(6)
        if t >= tv:
            k = C.out_expo(C.seg(t, tv, tv + 0.6 * u))
            pl = self._verdict()
            ca = 1 - C.seg(t, self.b(9), self.b(9.4))
            C.put(fr, pl, W / 2, 1270 + 60 * (1 - k), k * ca)
        tc = self.b(9.2)
        if t >= tc:
            k = C.out_expo(C.seg(t, tc, tc + 0.6 * u))
            C.put(fr, self._cta(), W / 2, 1270 + 60 * (1 - k), k)
        # строки экрана, вспышка, тряска
        fr.alpha_composite(self.scan)
        if D <= t < D + 0.4:
            fr.alpha_composite(Image.new('RGBA', (W, H), CY + (int(150 * (1 - C.seg(t, D, D + 0.4))),)))
        dx, dy = C.shake(t, D, 18, 0.4)
        z = 1 + 0.035 * (1 - C.seg(t, D, D + 0.5)) * (t >= D) + 0.02 * C.seg(t, 0, D)
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        if D <= t < D + 0.3:
            fr = C.rgb_split(fr, 10 * (1 - C.seg(t, D, D + 0.3)))
        fr = C.vignette(fr, 0.55)
        return C.grain(fr, t, 3)

    def _verdict(self):
        if not hasattr(self, '_vd'):
            w, h = 940, 400
            im = C.rrect(w, h, 30, (8, 22, 32), 245, outline=CY, width=3)
            C.put(im, C.text('ВЕРДИКТ', 'mono', 30, CY, 700, track=0.4), w / 2, 52)
            C.put(im, C.text(self.pick.upper(), 'tek', 76, WHITE, 800, max_w=w - 80), w / 2, 128)
            cols = [('ШАНС', '%d%%' % round(self.p * 100)), ('ЧЕСТНЫЙ КЭФ', '%.2f' % self.fair), ('КЭФ ЛИНИИ', C.fmt_k(self.coef))]
            for i, (k, v) in enumerate(cols):
                x = w / 2 + (i - 1) * 300
                C.put(im, C.text(k, 'mono', 24, (110, 160, 180), 700, track=0.12), x, 222)
                C.put(im, C.text(v, 'tek', 64, CY if i == 2 else WHITE, 800), x, 282)
            msg = 'ЛИНИЯ ДАЁТ БОЛЬШЕ, ЧЕМ СТОИТ ИСХОД · ПЕРЕВЕС +%d%%' % round(self.edge * 100) if self.edge > 0 else 'ПЕРЕВЕСА НЕТ'
            C.put(im, C.text(msg, 'mono', 24, WHITE, 600, max_w=w - 60), w / 2, 356)
            self._vd = C.glow(im, 14, 0.6, CY)
        return self._vd

    def _cta(self):
        if not hasattr(self, '_ct'):
            w, h = 940, 300
            im = C.rrect(w, h, 30, (8, 22, 32), 245, outline=CY, width=3)
            C.put(im, C.text('РАСЧЁТ НА КАЖДЫЙ МАТЧ', 'mono', 32, CY, 700, track=0.2), w / 2, 60)
            C.put(im, C.tg_icon(120), 150, 180)
            C.put(im, C.text('TELEGRAM', 'tek', 70, WHITE, 800), 560, 150)
            C.put(im, C.text(C.HANDLE, 'mono', 48, CY, 800), 560, 222)
            self._ct = C.glow(im, 14, 0.6, CY)
        return self._ct
