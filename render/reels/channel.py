# -*- coding: utf-8 -*-
"""«Канал» — лента Telegram-канала: посты приходят на доли трека, на дропе — настоящий баннер прогноза.

Шапка канала (аватар J, название), посты снизу вверх, как в Telegram: итоги («3 из 3 ✅» со счетами),
утренний анонс, на дропе — пост-картинка в фирменном стиле (nhl_kit.pick) с подписью; потом внизу пульсирует
«Подписаться», нажатие (круг от пальца), «Вы подписались», в конце — крупное «ПОДПИШИСЬ · @jarvibet».
"""
import math
import os
import tempfile

import numpy as np
from PIL import Image, ImageDraw

import nhl_kit
import poster
from reels import core as C
from reels.core import W, H

BG = (14, 22, 33)
POST = (33, 45, 59)
TXT = (240, 244, 248)
SUB = (140, 160, 180)
ACC = (100, 181, 246)
GOLD = (255, 196, 60)
TOP, BOT = 380, 1360


class Channel(C.Reel):
    def __init__(self, home, away, league, pick, coef, chance, when, results, morning, u=60 / 77, drop=2.34, seed=41):
        """results = ('заголовок', ['строка', ...]); morning — текст утреннего анонса."""
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.league = str(league).upper()
        self.pick, self.coef, self.chance, self.when = pick, coef, chance, when
        self.results, self.morning = results, morning
        b = self.b
        self.t_pulse, self.t_tap = b(4), b(5.5)
        self.t_end = b(8)
        self.dur = b(12)
        self.cover_t = b(3)
        self._prep()

    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        bg = Image.new('RGBA', (W, H), BG + (255,))
        d = ImageDraw.Draw(bg)
        for _ in range(60):
            x, y = rnd.uniform(0, W), rnd.uniform(0, H)
            d.ellipse((x - 20, y - 8, x + 20, y + 8), outline=(22, 33, 47, 255), width=4)
        self.bg = bg
        hd = Image.new('RGBA', (W, 170), (20, 30, 43, 255))
        av = C.ellipse(104, 104, (20, 20, 26))
        C.put(av, C.text('J', 'dela', 64, GOLD), 52, 54)
        C.put(hd, av, 130, 92)
        C.put(hd, C.text('‹', 'golos', 80, ACC, 500), 50, 88)
        C.put(hd, C.text('JARVIS · прогнозы на хоккей', 'golos', 44, TXT, 700, max_w=780), 210, 50, anchor='tl')
        C.put(hd, C.text('канал', 'golos', 34, SUB, 500), 210, 108, anchor='tl')
        self.hd = hd
        # пост-картинка: настоящий баннер прогноза
        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False).name
        m = dict(when=self.when, pred=self.pick, coef=self.coef, home=dict(team=self.h.name), away=dict(team=self.a.name))
        kw = dict(tag='KXL', accent=poster.ACC) if self.league == 'KHL' else {}
        path = nhl_kit.pick(m, tmp, scale=2, **kw)
        ban = Image.open(path).convert('RGBA')
        os.unlink(path)
        self.posts = [
            (0.25, self.text_post(self.results[0], self.results[1], '00:30')),
            (self.b(-1.6), self.text_post('Доброе утро ☀️', [self.morning], '09:00')),
            (self.drop, self.image_post(ban, '09:01')),
        ]
        self.events = [p[0] for p in self.posts]
        self.bar = self._bar(False)
        self.bar2 = self._bar(True)

    def _meta(self, im, clk):
        mt = C.text(clk, 'golos', 26, SUB, 500)
        C.put(im, mt, im.width - 28 - mt.width, im.height - 42, anchor='tl')

    def text_post(self, title, lines_, clk):
        w = 960
        body = [C.text(title, 'golos', 50, TXT, 700, max_w=w - 70)]
        for s in lines_:
            body.append(C.lines(s, 'golos', 44, w - 70, TXT, 500, gap=0.16, align='l', max_lines=3))
        h = sum(b.height for b in body) + 26 * (len(body) - 1) + 100
        im = C.rrect(w, h, 34, POST)
        y = 26
        for b in body:
            im.alpha_composite(b, (34, y))
            y += b.height + 26
        self._meta(im, clk)
        return im

    def image_post(self, ban, clk):
        w = 960
        img = C.fit(ban, w - 16, 1000)
        cap = [C.text('%s — %s · %s' % (self.h.short, self.a.short, self.when.split('·')[-1].strip()), 'golos', 44, TXT, 700, max_w=w - 70),
               C.text('Прогноз: %s · кэф %s · шанс %d%%' % (self.pick[:1].lower() + self.pick[1:], C.fmt_k(self.coef), self.chance), 'golos', 40, TXT, 500, max_w=w - 70)]
        h = 8 + img.height + 24 + sum(c.height for c in cap) + 20 + 90
        im = C.rrect(w, h, 34, POST)
        mask = C.rrect(img.width, img.height, 28).getchannel('A')
        im.paste(img, (8, 8), mask)
        y = 8 + img.height + 24
        for c in cap:
            im.alpha_composite(c, (34, y))
            y += c.height + 20
        self._meta(im, clk)
        return im

    def _bar(self, done):
        im = Image.new('RGBA', (W, 110), (20, 30, 43, 255))
        C.put(im, C.text('ВЫ ПОДПИСАНЫ ✓' if done else 'ПОДПИСАТЬСЯ', 'golos', 48, SUB if done else ACC, 800), W / 2, 55)
        return im

    def content_h(self, t):
        return sum(p.height + 24 for t0, p in self.posts if t >= t0)

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        ev = [x for x in self.events if x <= t]
        te = ev[-1] if ev else 0.0
        hc = C.lerp(self.content_h(te - 0.001), self.content_h(te + 0.001), C.out_cubic(C.seg(t, te, te + 0.35)))
        y = BOT - hc
        for t0, p in self.posts:
            if t < t0:
                continue
            k = C.out_cubic(C.seg(t, t0, t0 + 0.25))
            img = p
            if t0 == D:                                              # пост на дропе — с толчком
                img = C.scale(p, 0.9 + 0.1 * C.out_back(C.seg(t, t0, t0 + 0.4), 1.6))
            C.put(fr, img, W / 2, y + p.height / 2 + (1 - k) * 30, k)
            y += p.height + 24
        # дата-разделитель над лентой
        top_msg = BOT - hc
        if top_msg > TOP + 120:
            C.put(fr, self._hook(), W / 2, (TOP + top_msg) / 2, C.seg(top_msg, TOP + 160, TOP + 300))
        fr.alpha_composite(Image.new('RGBA', (W, 190), (20, 30, 43, 255)), (0, 0))
        fr.alpha_composite(self.hd, (0, 190))
        # нижняя кнопка «Подписаться»
        done = t >= self.t_tap + 0.15
        bar = self.bar2 if done else self.bar
        if self.t_pulse <= t < self.t_tap and not done:
            pz = 1 + 0.04 * max(0.0, math.sin((t - self.t_pulse) * math.pi / u))
            bar = C.scale(bar, pz)
        C.put(fr, bar, W / 2, BOT + 24 + 55)
        if self.t_tap <= t < self.t_tap + 0.6:                      # круг от пальца
            q = C.seg(t, self.t_tap, self.t_tap + 0.6)
            r = int(40 + 160 * q)
            ring = Image.new('RGBA', (2 * r + 4, 2 * r + 4), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse((2, 2, 2 * r + 2, 2 * r + 2), fill=(255, 255, 255, int(90 * (1 - q))))
            C.put(fr, ring, W / 2 + 80, BOT + 79)
        if self.t_tap + 0.15 <= t < self.t_end:                      # всплывашка
            q = C.out_back(C.seg(t, self.t_tap + 0.15, self.t_tap + 0.45), 1.5) * (1 - C.seg(t, self.t_end - 0.4, self.t_end))
            toast = C.rrect(760, 110, 55, (40, 52, 66), 240)
            C.put(toast, C.text('Вы подписались на канал 🔔', 'golos', 40, TXT, 600), 380, 55)
            C.put(fr, toast, W / 2, BOT - 70 + (1 - q) * 40, min(1.0, q))
        if t >= self.t_end:
            k = C.out_expo(C.seg(t, self.t_end, self.t_end + 0.6 * u))
            fr.alpha_composite(Image.new('RGBA', (W, H), (6, 10, 16, int(170 * k))))
            C.put(fr, self._end(), W / 2, 900 + 60 * (1 - k), k)
        z = 1 + 0.025 * (1 - C.seg(t, D, D + 0.5)) * (t >= D)
        # пока лента стоит — камера наезжает на баннер с прогнозом
        zf = 0.14 * C.in_out(C.seg(t, D + 0.6, self.b(3))) * (1 - C.in_out(C.seg(t, self.b(3.6), self.b(4.2))))
        post = self.posts[-1][1]
        fr = C.zoom(fr, z + zf, W / 2, BOT - post.height / 2 - 60)
        return C.vignette(fr, 0.3)

    def _hook(self):
        if not hasattr(self, '_hk'):
            im = C.lines('КАНАЛ, ГДЕ ПРОГНОЗ ГОТОВ ДО МАТЧА', 'onest', 78, 960, (255, 255, 255), 800, gap=0.05, max_lines=2)
            self._hk = C.with_shadow(im, 10, 0.9, 4)
        return self._hk

    def _end(self):
        if not hasattr(self, '_e'):
            w, h = 900, 520
            im = C.rrect(w, h, 44, (20, 30, 43), outline=ACC, width=3)
            C.put(im, C.text('ПОДПИШИСЬ', 'unb', 80, TXT, 900), w / 2, 100)
            C.put(im, C.text('КХЛ и НХЛ · прогноз до матча · честные итоги', 'golos', 36, SUB, 500, max_w=w - 60), w / 2, 175)
            C.put(im, C.tg_icon(150), w / 2, 300)
            C.put(im, C.text(C.HANDLE, 'unb', 64, ACC, 800), w / 2, 445)
            self._e = im
        return self._e
