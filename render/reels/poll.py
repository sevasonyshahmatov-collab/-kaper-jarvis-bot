# -*- coding: utf-8 -*-
"""«Опрос» — история (сторис) со стикером-опросом «Кто выиграет?».

Фон — размытые цвета клубов и эмблемы, сверху полоски историй и аккаунт; до дропа — стикер-опрос с двумя
клубами; на дропе — «нажатие» на наш вариант, шкалы заполняются (это шанс по нашему расчёту, так и подписано);
затем стикер с прогнозом и кэфом, стикер-вопрос «А твой прогноз?» (зовём в комментарии), стикер-ссылка на канал.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels.core import W, H

INK = (22, 22, 28)
GRAY = (120, 120, 130)
WHITE = (255, 255, 255)


class Poll(C.Reel):
    def __init__(self, home, away, league, side, pick, coef, chance, when, u=60 / 96.5, drop=2.49, seed=91):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.side = side
        self.fav = self.h if side == 'h' else self.a
        self.pick, self.coef, self.chance, self.when = pick, coef, chance, when
        self.t_pick = self.b(6)
        self.t_ask = self.b(12)
        self.t_link = self.b(17)
        self.t_tap = self.b(19)
        self.dur = self.b(23)
        self.cover_t = self.b(4)
        self._prep()

    def _prep(self):
        sm = Image.new('RGB', (W // 4, H // 4), (14, 12, 20))
        d = ImageDraw.Draw(sm)
        d.ellipse((-80, -60, 220, 240), fill=self.h.c1)
        d.ellipse((60, 260, 360, 560), fill=self.a.c1)
        sm = sm.filter(ImageFilter.GaussianBlur(40))
        bg = sm.resize((W, H), Image.BICUBIC).convert('RGBA')
        for tm, (x, y) in ((self.h, (250, 520)), (self.a, (830, 1400))):
            e = tm.emb(700).filter(ImageFilter.GaussianBlur(14))
            C.put(bg, C.fade(e, 0.35), x, y)
        bg.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, 70)))
        self.bg = bg
        av = C.ellipse(84, 84, (20, 20, 26))
        C.put(av, C.text('J', 'dela', 52, (255, 196, 60)), 42, 44)
        ring = Image.new('RGBA', (96, 96), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((2, 2, 94, 94), outline=(255, 120, 80, 255), width=5)
        ring.alpha_composite(av, (6, 6))
        self.avatar = ring

    def poll_card(self, t):
        w, h = 900, 560
        im = C.rrect(w, h, 40, WHITE)
        title = C.text('КТО ВЫИГРАЕТ?', 'unb', 64, INK, 900)
        g = C.lgrad(title.width, title.height, (255, 90, 120), (120, 80, 255), 0)
        g.putalpha(title.getchannel('A'))
        C.put(im, g, w / 2, 80)
        C.put(im, C.text('%s · %s МСК' % ('НХЛ', self.when), 'golos', 32, GRAY, 600), w / 2, 140)
        voted = t >= self.drop + 0.15
        q = C.out_cubic(C.seg(t, self.drop + 0.15, self.drop + 0.9))
        for i, tm in enumerate((self.h, self.a)):
            y = 200 + i * 170
            mine = (i == 0) == (self.side == 'h')
            p = self.chance if mine else 100 - self.chance
            bar = C.rrect(w - 80, 140, 70, (242, 242, 246))
            if voted:
                fw = max(140, int((w - 80) * p / 100 * q))
                fill = C.lgrad(fw, 140, (255, 90, 120), (120, 80, 255), 0) if mine else C.rrect(fw, 140, 70, (214, 214, 222))
                if mine:
                    fill.putalpha(C.rrect(fw, 140, 70).getchannel('A'))
                bar.alpha_composite(fill, (0, 0))
            C.put(bar, tm.emb(96), 80, 70)
            C.put(bar, C.text(tm.up, 'unb', 46, WHITE if (voted and mine and q > 0.4) else INK, 800, max_w=480), 150, 70 - 24, anchor='tl')
            if voted:
                pt = C.text('%d%%' % round(p * q), 'unb', 50, INK, 900)
                C.put(bar, pt, w - 80 - 40 - pt.width, 70 - pt.height / 2, C.seg(t, self.drop + 0.3, self.drop + 0.6), anchor='tl')
            C.put(im, bar, w / 2, y + 70)
        C.put(im, C.text('шанс по расчёту JARVIS' if voted else 'нажми на свой вариант', 'golos', 32, GRAY, 600), w / 2, h - 50)
        return im

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        # полоски историй
        segs = [(0, self.t_pick), (self.t_pick, self.t_link), (self.t_link, self.dur)]
        sw = (W - 60 - 2 * 12) / 3
        for i, (a, b) in enumerate(segs):
            x = 30 + i * (sw + 12)
            fr.alpha_composite(C.rrect(sw, 8, 4, WHITE, 90), (int(x), 210))
            k = C.seg(t, a, b)
            if k > 0:
                fr.alpha_composite(C.rrect(max(8, sw * k), 8, 4, WHITE), (int(x), 210))
        C.put(fr, self.avatar, 90, 290)
        C.put(fr, C.text('jarvibet', 'golos', 40, WHITE, 700), 150, 268, anchor='tl')
        C.put(fr, C.text('2 ч', 'golos', 36, (230, 230, 236), 500), 330, 270, anchor='tl')
        # сцена 1: опрос
        if t < self.t_pick + 0.3:
            k = C.out_back(C.seg(t, 0.1, 0.5), 1.5) * (1 - C.seg(t, self.t_pick, self.t_pick + 0.3))
            C.put(fr, C.with_shadow(C.text('ГОЛОСУЙ 👇', 'unb', 90, WHITE, 900), 12, 0.6, 6), W / 2, 560, min(1.0, k))
            card = self.poll_card(t)
            C.put(fr, C.scale(card, max(0.1, k)), W / 2, 1000, min(1.0, k))
            if D - 0.25 <= t < D + 0.6:                               # палец нажимает
                q = C.seg(t, D - 0.25, D + 0.6)
                y_opt = 1000 - 280 + 200 + (0 if self.side == 'h' else 170) + 70
                r = int(36 + 70 * C.seg(q, 0.3, 1))
                ring = Image.new('RGBA', (2 * r + 4, 2 * r + 4), (0, 0, 0, 0))
                ImageDraw.Draw(ring).ellipse((2, 2, 2 * r + 2, 2 * r + 2), fill=(255, 255, 255, int(150 * (1 - q))))
                C.put(fr, ring, W / 2 + 200, y_opt)
        # сцена 2: прогноз
        if self.t_pick <= t < self.t_link + 0.3:
            k = C.out_back(C.seg(t, self.t_pick, self.t_pick + 0.4), 1.5) * (1 - C.seg(t, self.t_link, self.t_link + 0.3))
            st = self.pick_sticker()
            C.put(fr, C.rotate(C.scale(st, max(0.1, k)), -3), W / 2, 780, min(1.0, k))
            if t >= self.t_ask:
                q = C.out_back(C.seg(t, self.t_ask, self.t_ask + 0.4), 1.5) * (1 - C.seg(t, self.t_link, self.t_link + 0.3))
                C.put(fr, C.rotate(C.scale(self.ask_sticker(t), max(0.1, q)), 3), W / 2, 1230, min(1.0, q))
        # сцена 3: ссылка
        if t >= self.t_link:
            k = C.out_back(C.seg(t, self.t_link, self.t_link + 0.4), 1.5)
            C.put(fr, C.with_shadow(C.text('ВСЕ ПРОГНОЗЫ ТУТ 👇', 'unb', 76, WHITE, 900, max_w=980), 12, 0.6, 6), W / 2, 760, min(1.0, k))
            ln = self.link_sticker()
            pz = 1.0 + (0.08 * math.sin(C.seg(t, self.t_tap, self.t_tap + 0.4) * math.pi) if t >= self.t_tap else 0)
            C.put(fr, C.scale(ln, max(0.1, k) * pz), W / 2, 980, min(1.0, k))
            if t >= self.t_tap + 0.3:
                q = C.out_expo(C.seg(t, self.t_tap + 0.3, self.t_tap + 0.8))
                pl = C.rrect(900, 150, 75, C.TG_BLUE)
                C.put(pl, C.tg_icon(110, WHITE, C.TG_BLUE), 85, 75)
                C.put(pl, C.text('ПОДПИСАТЬСЯ · ' + C.HANDLE, 'golos', 52, WHITE, 800, max_w=700), 500, 75)
                C.put(fr, pl, W / 2, 1220 + 40 * (1 - q), q)
        z = 1 + 0.03 * (1 - C.seg(t, D, D + 0.35)) * (t >= D)
        for th in (self.t_pick, self.t_ask, self.t_link):
            if t >= th:
                z += 0.02 * (1 - C.seg(t, th, th + 0.3))
        return C.zoom(fr, z, W / 2, 900)

    def pick_sticker(self):
        if not hasattr(self, '_ps'):
            w, h = 900, 380
            im = C.rrect(w, h, 40, INK)
            C.put(im, C.text('НАШ ПРОГНОЗ', 'golos', 36, (180, 180, 190), 700, track=0.2), w / 2, 60)
            C.put(im, C.text(self.pick.upper(), 'unb', 72, WHITE, 900, max_w=w - 80), w / 2, 160)
            tk = C.text('КЭФ ' + C.fmt_k(self.coef), 'unb', 48, INK, 900)
            tc = C.text('ШАНС %d%%' % self.chance, 'unb', 48, INK, 900)
            k = C.rrect(tk.width + 70, 110, 55, (255, 196, 60))
            C.put(k, tk, k.width / 2, 55)
            c = C.rrect(tc.width + 70, 110, 55, (255, 255, 255))
            C.put(c, tc, c.width / 2, 55)
            x0 = (w - k.width - c.width - 24) / 2
            C.put(im, k, x0, 235, anchor='tl')
            C.put(im, c, x0 + k.width + 24, 235, anchor='tl')
            self._ps = C.with_shadow(im, 20, 0.45, 12)
        return self._ps

    def ask_sticker(self, t):
        w, h = 820, 300
        im = C.rrect(w, h, 36, WHITE)
        hd = C.lgrad(w, 110, (255, 90, 120), (255, 160, 60), 0)
        hd.putalpha(C.rrect(w, 160, 36).crop((0, 0, w, 110)).getchannel('A'))
        im.alpha_composite(hd)
        C.put(im, C.text('А ТВОЙ ПРОГНОЗ?', 'unb', 52, WHITE, 900), w / 2, 55)
        msg = 'пиши в комментариях 👇'
        n = int(max(0.0, t - self.t_ask - 0.4) * 22)
        s = msg[:n] if n < len(msg) else msg
        field = C.rrect(w - 80, 110, 30, (242, 242, 246))
        C.put(field, C.text(s or ' ', 'golos', 44, INK if s else GRAY, 600), (w - 80) / 2, 55)
        C.put(im, field, w / 2, 200)
        return C.with_shadow(im, 20, 0.4, 12)

    def link_sticker(self):
        if not hasattr(self, '_ls'):
            tx = C.text('🔗 T.ME/' + C.HANDLE[1:].upper(), 'unb', 56, (60, 110, 230), 900)
            im = C.rrect(tx.width + 90, 130, 30, WHITE)
            C.put(im, tx, im.width / 2, 65)
            self._ls = C.with_shadow(im, 18, 0.4, 10)
        return self._ls
