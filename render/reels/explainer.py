# -*- coding: utf-8 -*-
"""«Как работает JARVIS» — ролик серии про таблицу (владелец 22.10, docs/channel/series/kak_rabotaet.md).

Кинетическая типографика на тёмном фоне, акцент — голубой бренда. Сцены (доли трека от дропа):
  хук (до b(−2·step)) — номер эпизода плашкой, хук огромными буквами по словам с «ударом»;
  тезис 2 и тезис 3 (по step долей) — номер шага в круге, текст строками, прогресс-полоса из трёх отрезков;
  ДРОП (hold долей) — вспышка и волна, главный тезис на акценте;
  финал (cta долей) — подпись и плашка Telegram.
Кадр — чистая функция t; надписи готовятся в конструкторе.
"""
import math

from reels import core as C
from reels.core import W, H

BG0, BG1 = (8, 10, 16), (18, 24, 40)
ACC = (42, 171, 238)
WHITE = (255, 255, 255)
GREY = (170, 178, 194)
SERIES = 'КАК РАБОТАЕТ JARVIS'


class Explainer(C.Reel):
    # длительности сцен в секундах; в доли трека — по ближайшему целому (склейки на долях)
    SEC = dict(hook=3.5, step=4.2, hold=5.0, cta=3.2)
    VIZ = False             # наследник с визуалом (explainer_viz.py): текст сверху меньше, середина — под visual()
    TXT_Y, VIZ_Y = 520, 1130

    def __init__(self, ep, u=0.5):
        n = {k: max(2, round(v / u)) for k, v in self.SEC.items()}
        step, hold, cta = n['step'], n['hold'], n['cta']
        super().__init__(u=u, drop=(n['hook'] + 2 * step) * u, seed=ep['n'])
        self.ep = ep
        self.T_s2 = self.b(-2 * step)
        self.T_s3 = self.b(-step)
        self.T_cta = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = self.T_s2 - 0.3
        self.footer_plate_to_end = False
        self.bg = C.vgrad(W, H, [(0, BG0), (0.55, BG1), (1, BG0)]).convert('RGB')
        self.glow = C.radial(900, 900, ACC, a0=70)
        hs, ss = (76, 58) if self.VIZ else (112, 84)
        self.hook = C.lines(ep['hook'], 'dela', hs, W - 140, fill=WHITE, max_lines=4)
        self.s2 = C.lines(ep['s2'], 'unb', ss, W - 150, fill=WHITE, wght=800, max_lines=4)
        self.s3 = C.lines(ep['s3'], 'unb', ss, W - 150, fill=WHITE, wght=800, max_lines=4)
        self.dropt = C.lines(ep['drop'], 'dela', 76 if self.VIZ else 104, W - 120, fill=WHITE, max_lines=4)
        self.ctat = C.lines(ep['cta'], 'unb', 64, W - 160, fill=WHITE, wght=800, max_lines=3)
        self.plate = C.tg_plate(980, 220, font='unb')
        self.nums = {k: C.text(str(k), 'dela', 92, (10, 16, 28)) for k in (2, 3)}
        self.circle = C.ellipse(170, 170, fill=ACC)

    # фон: градиент, мягкое пятно света, плывущее по кадру, зерно
    def _base(self, t):
        fr = self.bg.copy().convert('RGBA')
        cx = W / 2 + math.sin(t * 0.6) * 260
        cy = H * 0.42 + math.cos(t * 0.45) * 220
        C.put(fr, self.glow, cx, cy)
        return fr

    def _progress(self, fr, k):
        w, gap, y = 260, 24, 300
        x0 = W / 2 - (3 * w + 2 * gap) / 2
        for i in range(3):
            f = C.clamp(k - i)
            C.put(fr, C.rrect(w, 10, 5, fill=(255, 255, 255), a=50), x0 + i * (w + gap) + w / 2, y)
            if f > 0:
                C.put(fr, C.rrect(max(10, int(w * f)), 10, 5, fill=ACC), x0 + i * (w + gap) + w * f / 2, y)

    def _slam(self, fr, im, cx, cy, t, t0, z0=1.35):
        k = C.out_back(C.seg(t, t0, t0 + 0.28))
        C.put(fr, C.scale(im, z0 + (1 - z0) * k), cx, cy, a=C.clamp((t - t0) / 0.12))

    def visual(self, fr, t, phase, t0):
        """Середина кадра в сценах хук / s2 / s3 (только при VIZ)."""

    def frame(self, t):
        fr = self._base(t)
        u = self.u
        if t < self.T_s2:                                               # хук
            if self.VIZ:
                self.visual(fr, t, 'hook', 0.0)
                self._slam(fr, self.hook, W / 2, self.TXT_Y, t, 0.15)
            else:
                self._slam(fr, self.hook, W / 2, H * 0.47, t, 0.15)
        elif t < self.drop:                                             # тезисы 2 и 3
            second = t >= self.T_s3
            t0 = self.T_s3 if second else self.T_s2
            self._progress(fr, 1 + C.clamp((t - self.T_s2) / (self.drop - self.T_s2)) * 2)
            im = self.s3 if second else self.s2
            k = C.out_cubic(C.seg(t, t0 + 0.1, t0 + 0.5))
            if self.VIZ:
                self.visual(fr, t, 's3' if second else 's2', t0)
                C.put(fr, im, W / 2 + (1 - k) * 160, self.TXT_Y, a=k)
            else:
                self._slam(fr, self.circle, W / 2, 560, t, t0, z0=0.4)
                self._slam(fr, self.nums[3 if second else 2], W / 2, 562, t, t0 + 0.05, z0=0.4)
                C.put(fr, im, W / 2 + (1 - k) * 160, H * 0.52, a=k)
            ph = (t - self.drop) / u                                    # разгон к дропу: пульс на каждую долю
            if ph > -4:
                pulse = 1 - (ph % 1)
                C.put(fr, C.radial(W, 400, ACC, a0=int(60 * pulse)), W / 2, H - 200)
        elif t < self.T_cta:                                            # дроп
            # владелец 23.10: без отдельной «плашки»-заливки с текстом — тот же фон и визуал, главный тезис вместо тезиса 3
            n = int((t - self.drop) / u)
            r = (t - self.drop - n * u) / u                              # лёгкий толчок на каждую долю
            if self.VIZ:
                self.visual(fr, t, 's3', self.T_s3)
                self._slam(fr, self.dropt, W / 2, self.TXT_Y, t, self.drop + 0.05, z0=1.3)
            else:
                self._slam(fr, self.dropt, W / 2, H * 0.48, t, self.drop + 0.05, z0=1.3)
            fr = C.zoom(fr.convert('RGB'), 1 + 0.012 * (1 - r)).convert('RGBA')
        else:                                                           # финал
            self._slam(fr, self.ctat, W / 2, 760, t, self.T_cta)
            self._slam(fr, self.plate, W / 2, 1060, t, self.T_cta + 0.2, z0=1.3)
        fr = C.grain(fr.convert('RGB'), t, k=8)
        return C.vignette(fr, k=0.4)
