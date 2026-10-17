# -*- coding: utf-8 -*-
"""«Заметки» — честные итоги как заметка в телефоне.

Светлый экран заметок; до дропа набираются заголовок и прогнозы списком с пустыми кружками, на дропе и далее
на каждую долю кружок закрашивается галочкой (или крестиком, если не зашло) и дописывается счёт; потом —
итог «3 из 3 ✅ · +2.04 ед.», строка «сегодня — новые прогнозы» и ссылка на канал, по которой «нажимают».
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from reels import core as C
from reels.core import W, H

BG = (255, 255, 255)
INK = (20, 20, 22)
GRAY = (142, 142, 147)
ACC = (227, 166, 0)
GREEN = (52, 199, 89)
RED = (255, 59, 48)
LINK = (0, 122, 255)


class Notes(C.Reel):
    def __init__(self, title, stamp, items, total, today, plan=(), u=60 / 72, drop=3.33, seed=81):
        """items = [('Металлург ИТБ 2,5', 1.68, '7:1', True), ...]; plan — прогнозы на сегодня (ещё не сыграли)"""
        super().__init__(u, drop, seed)
        self.title, self.stamp, self.items, self.total, self.today, self.plan = title, stamp, items, total, today, list(plan)
        n = len(items)
        self.t_type = [self.b(-3 + 2.6 * i / max(1, n - 1)) for i in range(n)]      # строки набираются до дропа
        self.t_tick = [self.b(i) for i in range(n)]                                   # галочки — с дропа по долям
        self.t_total = self.b(n + 0.5)
        self.t_today = self.b(n + 3)
        self.t_plan = [self.t_today + (1.0 + 0.8 * j) * u for j in range(len(self.plan))]
        self.t_link = self.t_today + (1.4 + 0.8 * len(self.plan)) * u
        self.t_tap = self.t_link + 1.6 * u
        self.dur = self.t_tap + 4 * u
        self.cover_t = self.b(n + 2.5)
        self.wins = sum(1 for it in items if it[3])
        self.profit = sum((it[1] - 1) if it[3] else -1 for it in items)

    def typed(self, s, t, t0, cps=26):
        n = int(max(0.0, t - t0) * cps)
        return s[:n], n < len(s)

    def body(self, fr, d, t):
        u, D = self.u, self.drop
        # к концу заметка прокручивается к ссылке
        off = 330 * C.in_out(C.seg(t, self.t_today - 0.5, self.t_today + 0.3)) + \
            (110 * len(self.plan) + 40) * C.in_out(C.seg(t, self.t_link - 0.6, self.t_link + 0.2))
        C.put(fr, C.text(self.stamp, 'golos', 34, GRAY, 500), W / 2, 340 - off)
        # заголовок
        s, typing = self.typed(self.title, t, 0.15, 30)
        y = 400 - off
        if s:
            C.put(fr, C.text(s, 'golos', 84, INK, 800, trim=False), 40, y, anchor='tl')
        caret_y = None
        if typing:
            caret_y = (40 + C.font('golos', 84, 800).getlength(s) + 6, y + 30, 84)
        y += 160
        # пункты
        for i, (name, k, score, ok) in enumerate(self.items):
            t0 = self.t_type[i]
            if t < t0:
                continue
            line = '%s · %s' % (name, C.fmt_k(k))
            s, typing = self.typed(line, t, t0, 34)
            cx, cy = 80, y + 48
            ticked = t >= self.t_tick[i]
            if ticked:
                q = C.out_back(C.seg(t, self.t_tick[i], self.t_tick[i] + 0.3), 2.2)
                circ = C.ellipse(64, 64, GREEN if ok else RED)
                cd = ImageDraw.Draw(circ)
                if ok:
                    cd.line((17, 33, 28, 44, 48, 22), fill=(255, 255, 255, 255), width=7, joint='curve')
                else:
                    cd.line((20, 20, 44, 44), fill=(255, 255, 255, 255), width=7)
                    cd.line((44, 20, 20, 44), fill=(255, 255, 255, 255), width=7)
                C.put(fr, C.scale(circ, max(0.1, q)), cx, cy)
            else:
                ring = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
                ImageDraw.Draw(ring).ellipse((3, 3, 61, 61), outline=(199, 199, 204, 255), width=4)
                C.put(fr, ring, cx, cy)
            C.put(fr, C.text(s, 'golos', 56, INK, 600, trim=False, max_w=900), 140, y + 6, anchor='tl')
            if typing:
                caret_y = (140 + C.font('golos', 56, 600).getlength(s) + 4, y + 20, 62)
            if ticked:
                q = C.out_expo(C.seg(t, self.t_tick[i] + 0.1, self.t_tick[i] + 0.4))
                sc = C.text('счёт %s · %s' % (score, 'зашёл' if ok else 'мимо'), 'golos', 46, GREEN if ok else RED, 700)
                C.put(fr, sc, 140 + (1 - q) * 30, y + 86, q, anchor='tl')
            y += 170
        # итог
        if t >= self.t_total:
            d.line((40, y + 10, (W - 40) * 1.0, y + 10), fill=(229, 229, 234, 255), width=3)
            s1 = 'Итог: %d из %d ✅' % (self.wins, len(self.items))
            q = C.out_back(C.seg(t, self.t_total, self.t_total + 0.4), 1.8)
            C.put(fr, C.scale(C.text(s1, 'golos', 100, INK, 800), max(0.1, q)), 40, y + 50, min(1.0, q * 1.5), anchor='tl')
            sg = '+' if self.profit >= 0 else '−'
            C.put(fr, C.text('%s%.2f ед. · ставка 1 ед. на матч' % (sg, abs(self.profit)), 'golos', 50, GREEN if self.profit >= 0 else RED, 700),
                  40, y + 190, C.seg(t, self.t_total + 0.3, self.t_total + 0.6), anchor='tl')
            y += 290
        # сегодня + ссылка
        if t >= self.t_today:
            s, typing = self.typed(self.today, t, self.t_today, 30)
            C.put(fr, C.text(s, 'golos', 58, INK, 600, trim=False), 40, y + 10, anchor='tl')
            if typing:
                caret_y = (40 + C.font('golos', 58, 600).getlength(s) + 4, y + 24, 64)
            y += 100
            for j, line in enumerate(self.plan):                     # сегодняшние — пустые кружки
                if t < self.t_plan[j]:
                    break
                sp, typing_p = self.typed(line, t, self.t_plan[j], 40)
                ring = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
                ImageDraw.Draw(ring).ellipse((3, 3, 61, 61), outline=(199, 199, 204, 255), width=4)
                C.put(fr, ring, 80, y + 44)
                C.put(fr, C.text(sp, 'golos', 54, INK, 600, trim=False), 140, y + 8, anchor='tl')
                if typing_p:
                    caret_y = (140 + C.font('golos', 54, 600).getlength(sp) + 4, y + 20, 60)
                y += 110
            y -= 100
            lk = 't.me/' + C.HANDLE[1:]
            t1 = self.t_link
            if t >= t1:
                s2, typing2 = self.typed(lk, t, t1, 24)
                tx = C.text(s2, 'golos', 66, LINK, 600, trim=False)
                C.put(fr, tx, 40, y + 100, anchor='tl')
                ImageDraw.Draw(fr).line((44, y + 182, 44 + tx.width - 16, y + 182), fill=LINK + (255,), width=4)
                if typing2:
                    caret_y = (40 + C.font('golos', 66, 600).getlength(s2) + 4, y + 112, 72)
                if t >= self.t_tap:                                # «нажатие» на ссылку
                    q = C.seg(t, self.t_tap, self.t_tap + 0.5)
                    r = int(30 + 90 * q)
                    ring = Image.new('RGBA', (2 * r + 4, 2 * r + 4), (0, 0, 0, 0))
                    ImageDraw.Draw(ring).ellipse((2, 2, 2 * r + 2, 2 * r + 2), fill=LINK + (int(80 * (1 - q)),))
                    C.put(fr, ring, 40 + tx.width / 2, y + 140)
                    if t >= self.t_tap + 0.3:
                        k = C.out_expo(C.seg(t, self.t_tap + 0.3, self.t_tap + 0.8))
                        pl = C.rrect(900, 150, 75, C.TG_BLUE)
                        C.put(pl, C.tg_icon(110, (255, 255, 255), C.TG_BLUE), 85, 75)
                        C.put(pl, C.text('ОТКРЫТЬ КАНАЛ ' + C.HANDLE, 'golos', 50, (255, 255, 255), 800, max_w=700), 500, 75)
                        C.put(fr, pl, W / 2, y + 310 + 40 * (1 - k), k)
        if caret_y and int(t * 2.5) % 2 == 0:
            x, yy, hh = caret_y
            d.rectangle((x, yy, x + 5, yy + hh), fill=ACC + (255,))

    def frame(self, t):
        u, D = self.u, self.drop
        fr = Image.new('RGBA', (W, H), BG + (255,))
        d = ImageDraw.Draw(fr)
        self.body(fr, d, t)
        # верхняя панель
        fr.alpha_composite(Image.new('RGBA', (W, 300), BG + (255,)), (0, 0))
        C.put(fr, C.text('‹ Заметки', 'golos', 46, ACC, 500), 40, 236, anchor='tl')
        for i, x in enumerate((W - 190, W - 90)):
            C.put(fr, C.ellipse(56, 56, (255, 255, 255)), x, 262)
            r = Image.new('RGBA', (56, 56), (0, 0, 0, 0))
            ImageDraw.Draw(r).ellipse((3, 3, 53, 53), outline=ACC + (255,), width=4)
            C.put(fr, r, x, 262)
            if i == 1:
                for k in (-12, 0, 12):
                    C.put(fr, C.ellipse(8, 8, ACC), x + k, 262)
            else:
                ImageDraw.Draw(fr).line((x, 250, x, 276), fill=ACC + (255,), width=4)
                ImageDraw.Draw(fr).line((x - 10, 260, x, 250, x + 10, 260), fill=ACC + (255,), width=4)
        z = 1 + 0.02 * (1 - C.seg(t, D, D + 0.4)) * (t >= D)
        return C.zoom(fr, z, W / 2, 900)
