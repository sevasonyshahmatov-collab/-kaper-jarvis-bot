# -*- coding: utf-8 -*-
"""«Уведомления» — экран блокировки телефона, пуши от JARVIS приходят на доли трека.

Обои — размытые пятна цветов клубов, дата и большие часы; до дропа приходят «Матч дня» и «Линия», на дропе —
«Прогноз готов» (телефон вздрагивает), затем уведомление раскрывается в карточку (эмблемы, прогноз, кэф, шанс,
кнопки), фон размывается; в конце — пуш «Подпишись, чтобы получать первым» и часы доходят до начала матча.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels.core import W, H

WHITE = (255, 255, 255)
INK = (18, 18, 24)
GOLD = (255, 196, 60)


class Notify(C.Reel):
    def __init__(self, home, away, league, side, pick, coef, odds, chance, day, clock0, clock1, u=0.9375, drop=2.81, seed=31):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.fav = self.h if side == 'h' else self.a
        self.pick, self.coef, self.odds, self.chance = pick, coef, odds, chance
        self.day, self.clock0, self.clock1 = day, clock0, clock1
        self.league = 'НХЛ' if str(league).upper() == 'NHL' else 'КХЛ'
        self.t_open = self.b(1)
        self.t_cta = self.b(7)
        self.dur = self.b(11)
        self.cover_t = self.b(4)
        b = self.b
        self.notes = [
            (b(-2), 'Матч дня 🏒', '%s — %s, %s МСК' % (self.h.short, self.a.short, clock1)),
            (b(-1), 'Линия обновилась', 'П1 %s · Х %s · П2 %s' % tuple(C.fmt_k(x) for x in odds)),
            (self.drop, '🔔 Прогноз готов', '%s · кэф %s · шанс %d%%' % (pick, C.fmt_k(coef), chance)),
        ]
        self._prep()

    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        sm = Image.new('RGB', (W // 4, H // 4), (12, 12, 18))
        d = ImageDraw.Draw(sm)
        for col, (x, y, r) in ((self.h.c1, (60, 150, 170)), (self.a.c1, (210, 330, 190)), (self.h.c2 if sum(self.h.c2) > 90 else (60, 60, 90), (220, 80, 110)),
                               (self.a.c1, (40, 420, 120))):
            d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(c * 0.85) for c in col))
        sm = sm.filter(ImageFilter.GaussianBlur(60))
        wall = sm.resize((W, H), Image.BICUBIC)
        arr = np.asarray(wall, np.float32) * 0.8 + rnd.normal(0, 3, (H, W, 1))
        self.wall = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        self.wall_blur = self.wall.filter(ImageFilter.GaussianBlur(28))
        self.icon = self._icon(92)
        self.cards = [self.note(i) for i in range(len(self.notes))]
        self.big = self.expanded()
        self.cta_note = self.note_img('Подпишись на канал', 'Прогнозы приходят первыми · Telegram ' + C.HANDLE, tg=True)

    def _icon(self, s):
        im = C.rrect(s, s, s * 0.24, (20, 20, 26))
        C.put(im, C.text('J', 'dela', int(s * 0.62), GOLD), s / 2, s / 2 + 2)
        return im

    def note_img(self, title, body, tg=False):
        w, h = 1000, 210
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        im.alpha_composite(C.rrect(w, h, 46, (250, 250, 252), 52))
        C.put(im, C.tg_icon(92) if tg else self.icon, 34 + 46, 105)
        C.put(im, C.text('JARVIS' if not tg else 'TELEGRAM', 'golos', 30, (230, 230, 236), 600), 156, 34, anchor='tl')
        tn = C.text('сейчас', 'golos', 30, (210, 210, 220), 500)
        C.put(im, tn, w - 40 - tn.width, 34, anchor='tl')
        C.put(im, C.text(title, 'golos', 42, WHITE, 700, max_w=w - 200), 156, 76, anchor='tl')
        C.put(im, C.text(body, 'golos', 38, (236, 236, 242), 500, max_w=w - 200), 156, 132, anchor='tl')
        return im

    def note(self, i):
        t0, title, body = self.notes[i]
        return self.note_img(title, body)

    def expanded(self):
        w, h = 1000, 1040
        im = C.rrect(w, h, 50, (248, 248, 250))
        top = Image.new('RGBA', (w, 420), (0, 0, 0, 0))
        g = C.lgrad(w, 420, C.mix(self.h.c1, INK, 0.25), C.mix(self.a.c1, INK, 0.25), 0)
        g.putalpha(C.rrect(w, 420, 50).getchannel('A'))
        top.alpha_composite(g)
        top.alpha_composite(Image.new('RGBA', (w, 60), (0, 0, 0, 0)), (0, 360))
        im.alpha_composite(top.crop((0, 0, w, 420)))
        im.alpha_composite(C.lgrad(w, 60, C.mix(self.h.c1, INK, 0.25), C.mix(self.a.c1, INK, 0.25), 0), (0, 370))
        C.put(im, self.h.emb(230), w / 2 - 250, 200)
        C.put(im, self.a.emb(230), w / 2 + 250, 200)
        C.put(im, C.text('VS', 'unb', 60, WHITE, 800), w / 2, 200)
        C.put(im, C.text('%s · %s · %s МСК' % (self.league, self.day.split(',')[0].upper(), self.clock1), 'golos', 34, WHITE, 600), w / 2, 372)
        C.put(im, C.text('ПРОГНОЗ', 'golos', 32, (130, 130, 140), 700, track=0.3), w / 2, 480)
        C.put(im, C.text(self.pick.upper(), 'unb', 70, INK, 800, max_w=w - 80), w / 2, 560)
        k = C.rrect(380, 120, 60, INK)
        C.put(k, C.text('КЭФ ' + C.fmt_k(self.coef), 'unb', 54, GOLD, 800), 190, 60)
        c = C.rrect(380, 120, 60, (236, 236, 240))
        C.put(c, C.text('ШАНС %d%%' % self.chance, 'unb', 50, INK, 800), 190, 60)
        C.put(im, k, w / 2 - 200, 700)
        C.put(im, c, w / 2 + 200, 700)
        d = ImageDraw.Draw(im)
        d.line((0, 820, w, 820), fill=(220, 220, 226, 255), width=2)
        d.line((w / 2, 820, w / 2, h), fill=(220, 220, 226, 255), width=2)
        C.put(im, C.text('Открыть', 'golos', 44, (0, 122, 255), 600), w / 4, 930)
        C.put(im, C.text('Подписаться', 'golos', 44, (0, 122, 255), 700), 3 * w / 4, 930)
        return im

    def clock(self, t):
        return self.clock0 if t < self.b(9) else self.clock1

    def frame(self, t):
        u, D = self.u, self.drop
        opened = C.out_expo(C.seg(t, self.t_open, self.t_open + 0.5 * u)) * (1 - C.in_cubic(C.seg(t, self.t_cta - 0.3, self.t_cta + 0.2)))
        fr = Image.blend(self.wall, self.wall_blur, min(1.0, opened)) if opened > 0.01 else self.wall.copy()
        # замок, дата, часы
        C.put(fr, C.text('🔒', 'golos', 40), W / 2, 250)
        C.put(fr, C.text(self.day, 'golos', 46, (240, 240, 245), 600), W / 2, 330)
        ck = C.text(self.clock(t), 'manrope', 250, WHITE, 600)
        if self.b(9) <= t < self.b(9) + 0.3:
            ck = C.scale(ck, 1 + 0.06 * (1 - C.seg(t, self.b(9), self.b(9) + 0.3)))
        C.put(fr, ck, W / 2, 480)
        # кнопки фонарика и камеры, полоска «домой»
        for x in (150, W - 150):
            C.put(fr, C.ellipse(120, 120, (30, 30, 36), 150), x, 1760)
        C.put(fr, C.rrect(300, 12, 6, WHITE, 200), W / 2, 1880)
        # уведомления: новое сверху, старые сдвигаются вниз
        y0 = 680
        shown = [(i, n) for i, n in enumerate(self.notes) if t >= n[0]]
        if t >= self.t_cta:
            shown = []
        ys = 0.0
        for rank, (i, n) in enumerate(reversed(shown)):
            t0 = n[0]
            card = self.cards[i]
            a = (1 - 0.15 * rank) * (1 - opened)
            if rank == 0:                                          # новое — падает сверху с отскоком
                p = C.out_back(C.seg(t, t0, t0 + 0.35), 1.3)
                jx, _ = C.shake(t, t0, 10, 0.3, 120, 90)
                C.put(fr, card, W / 2 + jx, y0 + card.height / 2 - (1 - p) * 120, min(1.0, C.seg(t, t0, t0 + 0.15)) * a)
                ys = (card.height + 22) * C.out_cubic(C.seg(t, t0, t0 + 0.3))
            else:                                                  # старые сдвигаются вниз
                C.put(fr, card, W / 2, y0 + ys + card.height / 2, a)
                ys += card.height + 22
        # раскрытое уведомление
        if opened > 0.01:
            dim = Image.new('RGBA', (W, H), (0, 0, 0, int(90 * opened)))
            fr.alpha_composite(dim)
            s = 0.6 + 0.4 * opened
            big = C.scale(self.big, s)
            C.put(fr, C.shadow(big, 30, 0.45 * opened), W / 2, 980 + 30)
            C.put(fr, big, W / 2, 680 + big.height / 2 + (1 - opened) * 60, opened)
        # пуш-подписка
        if t >= self.t_cta:
            p = C.out_back(C.seg(t, self.t_cta, self.t_cta + 0.35), 1.3)
            jx, _ = C.shake(t, self.t_cta, 10, 0.3, 120, 90)
            C.put(fr, self.cta_note, W / 2 + jx, 680 + self.cta_note.height / 2 - (1 - p) * 120, C.seg(t, self.t_cta, self.t_cta + 0.15))
            if t >= self.b(8):
                k = C.out_expo(C.seg(t, self.b(8), self.b(8) + 0.5))
                big = C.text('ПОДПИШИСЬ', 'unb', 110, WHITE, 900, max_w=980)
                C.put(fr, C.with_shadow(big, 16, 0.5, 6), W / 2, 1060 + 40 * (1 - k), k)
                C.put(fr, C.with_shadow(C.text('прогнозы приходят первыми', 'golos', 52, WHITE, 600), 12, 0.5, 4), W / 2, 1180 + 40 * (1 - k), k)
        # телефон вздрагивает на дропе
        dx, dy = C.shake(t, D, 12, 0.35)
        z = 1 + 0.03 * (1 - C.seg(t, D, D + 0.4)) * (t >= D)
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        return C.vignette(fr, 0.3)
