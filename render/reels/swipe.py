# -*- coding: utf-8 -*-
"""«Свайп» — матчи листаются карточками, как в приложении знакомств.

Светлый интерфейс; карточка матча — эмблемы на цветах клубов, время, шанс и кэф. Матчи «почти монетка»
(шанс около 50%) уходят влево со штампом «ПРОПУСК», уверенный — на дропе вправо со штампом «СТАВИМ»; дальше —
экран «ЭТО МЭТЧ!»: аватар канала и эмблема клуба, прогноз, кэф, шанс, кнопка превращается в подписку.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels.core import W, H

INK = (24, 22, 30)
GRAY = (130, 128, 140)
RED = (255, 76, 96)
GREEN = (40, 200, 120)
PINK = (255, 90, 120)
GOLD = (255, 196, 60)
CWD, CHT = 900, 1080


class Swipe(C.Reel):
    def __init__(self, cards, title, u=60 / 69, drop=5.22, seed=61):
        """cards = [(хозяева, гости, лига, 'ВС 11.10 · 02:00', шанс, кэф, 'прогноз', сторона, решение 'L'/'R', пояснение)]"""
        super().__init__(u, drop, seed)
        self.cards = []
        for h, a, lg, when, ch, k, pick, side, dec, note in cards:
            th, ta = C.match(h, a, lg)
            self.cards.append(dict(h=th, a=ta, when=when, chance=ch, coef=k, pick=pick, fav=th if side == 'h' else ta,
                                   dec=dec, note=note, league='НХЛ' if lg == 'NHL' else 'КХЛ'))
        n = len(self.cards)
        self.t_sw = [self.b(-2 * (n - 1 - i)) for i in range(n)]      # последний свайп — на дропе
        self.title = title
        self.win = self.cards[-1]
        self.t_cta = self.b(6)
        self.dur = self.b(10)
        self.cover_t = self.b(3.5)
        self._prep()

    def _prep(self):
        self.bg = C.vgrad(W, H, [(0, (252, 246, 249)), (1, (238, 238, 248))]).convert('RGBA')
        self.imgs = [self.card_img(c) for c in self.cards]
        self.st_l = self.stamp('ПРОПУСК', RED, 18)
        self.st_r = self.stamp('СТАВИМ', GREEN, -18)
        self.btns = self.buttons()
        self.match_bg = self._match_bg()

    def card_img(self, c):
        im = C.rrect(CWD, CHT, 50, (255, 255, 255))
        top = C.lgrad(CWD, 620, C.mix(c['h'].c1, INK, 0.1), C.mix(c['a'].c1, INK, 0.1), 20)
        m = C.rrect(CWD, 680, 50).crop((0, 0, CWD, 620))
        top.putalpha(m.getchannel('A'))
        im.alpha_composite(top)
        C.put(im, C.glow(c['h'].emb(270), 18, 0.7, (255, 255, 255)), CWD / 2 - 210, 300)
        C.put(im, C.glow(c['a'].emb(270), 18, 0.7, (255, 255, 255)), CWD / 2 + 210, 300)
        C.put(im, C.text(c['when'] + ' МСК', 'golos', 36, (255, 255, 255), 700), CWD / 2, 560)
        C.put(im, C.text('%s — %s' % (c['h'].short, c['a'].short), 'golos', 62, INK, 800, max_w=CWD - 80), 50, 660, anchor='tl')
        C.put(im, C.text(c['league'] + ' · ' + c['pick'], 'golos', 40, GRAY, 600, max_w=CWD - 80), 50, 750, anchor='tl')
        x = 50
        for txt, col in (('шанс %d%%' % c['chance'], C.mix(c['fav'].c1, (255, 255, 255), 0.75)),
                         ('кэф %s' % C.fmt_k(c['coef']), (240, 238, 246))):
            tx = C.text(txt, 'golos', 40, INK, 700)
            chip = C.rrect(tx.width + 56, 76, 38, col)
            C.put(chip, tx, chip.width / 2, 38)
            C.put(im, chip, x, 830, anchor='tl')
            x += chip.width + 16
        C.put(im, C.text(c['note'], 'golos', 38, (90, 88, 100), 600, max_w=CWD - 100), 50, 950, anchor='tl')
        return C.with_shadow(im, 30, 0.25, 20)

    def stamp(self, s, col, rot):
        tx = C.text(s, 'unb', 92, col, 900)
        im = C.rrect(tx.width + 80, tx.height + 60, 20, (255, 255, 255), 0, outline=col, width=10)
        C.put(im, tx, im.width / 2, im.height / 2)
        return C.rotate(im, rot)

    def buttons(self):
        out = {}
        for key, col, sym, s in (('x', RED, '✕', 150), ('h', GREEN, '❤', 150), ('s', (60, 140, 255), '★', 110)):
            im = C.ellipse(s, s, (255, 255, 255))
            ring = Image.new('RGBA', (s, s), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse((3, 3, s - 3, s - 3), outline=col + (255,), width=5)
            im.alpha_composite(ring)
            if sym == '❤':
                C.put(im, C.text('❤️', 'golos', int(s * 0.42)), s / 2, s / 2)
            elif sym == '✕':
                d = ImageDraw.Draw(im)
                r = s * 0.18
                for sx in (1, -1):
                    d.line((s / 2 - r, s / 2 - r * sx, s / 2 + r, s / 2 + r * sx), fill=col + (255,), width=12)
            else:                                                   # звезда
                pts = []
                for i in range(10):
                    r = s * (0.24 if i % 2 == 0 else 0.1)
                    ang = i * math.pi / 5 - math.pi / 2
                    pts.append((s / 2 + r * math.cos(ang), s / 2 + r * math.sin(ang)))
                im.alpha_composite(C.polygon(pts, (s, s), col))
            out[key] = C.with_shadow(im, 14, 0.2, 8)
        return out

    def _match_bg(self):
        c = self.win
        sm = Image.new('RGB', (W // 4, H // 4), (20, 16, 30))
        d = ImageDraw.Draw(sm)
        d.ellipse((-60, -40, 220, 260), fill=c['h'].c1)
        d.ellipse((60, 230, 340, 520), fill=c['a'].c1)
        sm = sm.filter(ImageFilter.GaussianBlur(50))
        bg = sm.resize((W, H), Image.BICUBIC).convert('RGBA')
        bg.alpha_composite(Image.new('RGBA', (W, H), (10, 8, 18, 110)))
        return bg

    def avatar(self, im, s, ring=(255, 255, 255)):
        av = C.ellipse(s, s, (255, 255, 255))
        C.put(av, im, s / 2, s / 2)
        r = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(r).ellipse((3, 3, s - 3, s - 3), outline=ring + (255,), width=8)
        av.alpha_composite(r)
        return C.with_shadow(av, 20, 0.35, 10)

    def frame(self, t):
        u, D = self.u, self.drop
        if t < D + 0.45:
            fr = self.bg.copy()
            # шапка приложения
            C.put(fr, C.text(self.title, 'golos', 54, INK, 800), W / 2, 280)
            C.put(fr, C.text('листаем матчи ночи', 'golos', 36, GRAY, 600), W / 2, 340)
            # карточки: верхняя — текущая
            cur = sum(1 for ts in self.t_sw if t >= ts + 0.45)
            for i in range(len(self.cards) - 1, cur - 1, -1):
                ts = self.t_sw[i]
                img = self.imgs[i]
                if i > cur:                                         # следующая — под текущей
                    if i == cur + 1:
                        prev_ts = self.t_sw[cur]
                        k = C.out_cubic(C.seg(t, prev_ts, prev_ts + 0.45))
                        C.put(fr, C.scale(img, 0.94 + 0.06 * k), W / 2, 860 + 30 * (1 - k))
                    continue
                q = C.in_cubic(C.seg(t, ts, ts + 0.45))
                pre = C.seg(t, ts - 0.35, ts)                       # перед свайпом карточку тянут и появляется штамп
                dirx = -1 if self.cards[i]['dec'] == 'L' else 1
                dx = dirx * (40 * pre + 1300 * q)
                rot = -dirx * (4 * pre + 22 * q)
                im = C.rotate(img, rot) if abs(rot) > 0.1 else img
                cx, cy = W / 2 + dx, 860 + 60 * q
                C.put(fr, im, cx, cy)
                st = self.st_l if dirx < 0 else self.st_r
                a = min(1.0, pre * 1.5 + q)
                if a > 0:
                    C.put(fr, C.scale(st, 1.2 - 0.2 * min(1.0, pre * 2)), cx + (220 if dirx < 0 else -220), cy - 300, a)
            # кнопки
            for key, x in (('x', W / 2 - 230), ('s', W / 2), ('h', W / 2 + 230)):
                pz = 1.0
                for i, ts in enumerate(self.t_sw):
                    hit = (key == 'x' and self.cards[i]['dec'] == 'L') or (key == 'h' and self.cards[i]['dec'] == 'R')
                    if hit and ts - 0.35 <= t < ts + 0.3:
                        pz = 1 + 0.18 * math.sin(C.seg(t, ts - 0.35, ts + 0.3) * math.pi)
                C.put(fr, C.scale(self.btns[key], pz), x, 1500)
            if t >= D:                                              # вспышка перед экраном мэтча
                fr.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(255 * C.seg(t, D, D + 0.45)))))
        else:
            fr = self.match_bg.copy()
            c = self.win
            k = C.out_expo(C.seg(t, D + 0.45, D + 1.0))
            ttl = C.text('ЭТО МЭТЧ!', 'playi', 170, (255, 255, 255), 700, max_w=980)
            C.put(fr, C.glow(ttl, 20, 0.8, PINK), W / 2, 380 - 60 * (1 - k), k)
            j = self.avatar(C.text('J', 'dela', 160, GOLD), 300)
            e = self.avatar(c['fav'].emb(220), 300)
            sw = 8 * math.sin(t * 2)
            C.put(fr, C.rotate(j, -8 + sw * 0.3), W / 2 - 170 - (1 - k) * 500, 720)
            C.put(fr, C.rotate(e, 8 - sw * 0.3), W / 2 + 170 + (1 - k) * 500, 720)
            C.put(fr, C.text('JARVIS и %s понравились друг другу' % c['fav'].short, 'golos', 40, (255, 255, 255), 600, max_w=980),
                  W / 2, 935, C.seg(t, D + 0.8, D + 1.2))
            if t >= self.b(1.5):
                q = C.out_expo(C.seg(t, self.b(1.5), self.b(1.5) + 0.5))
                pl = C.rrect(940, 230, 50, (255, 255, 255), 245)
                C.put(pl, C.text(c['pick'].upper(), 'unb', 60, INK, 800, max_w=880), 470, 70)
                C.put(pl, C.text('кэф %s · шанс %d%% · %s МСК' % (C.fmt_k(c['coef']), c['chance'], c['when'].split('·')[-1].strip()),
                                 'golos', 44, (90, 88, 100), 600, max_w=880), 470, 160)
                C.put(fr, pl, W / 2, 1120 + 60 * (1 - q), q)
            # кнопка: «написать» → подписка
            if t >= self.b(3):
                q = C.out_expo(C.seg(t, self.b(3), self.b(3) + 0.4))
                done = t >= self.t_cta
                pl = C.rrect(900, 140, 70, C.TG_BLUE if done else PINK)
                if done:
                    C.put(pl, C.tg_icon(100, (255, 255, 255), C.TG_BLUE), 80, 70)
                    C.put(pl, C.text('ПОДПИСАТЬСЯ · ' + C.HANDLE, 'golos', 50, (255, 255, 255), 800, max_w=700), 500, 70)
                else:
                    C.put(pl, C.text('НАПИСАТЬ ПРОГНОЗ ДРУГУ', 'golos', 50, (255, 255, 255), 800), 450, 70)
                pz = 1 + 0.06 * (1 - C.seg(t, self.t_cta, self.t_cta + 0.3)) * (t >= self.t_cta)
                C.put(fr, C.scale(pl, pz), W / 2, 1360 + 40 * (1 - q), q)
            if t < D + 0.75:
                fr.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(255 * (1 - C.seg(t, D + 0.45, D + 0.75))))))
        return C.vignette(fr, 0.2)
