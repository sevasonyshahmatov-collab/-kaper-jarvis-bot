# -*- coding: utf-8 -*-
"""«Переписка» — сценка в мессенджере: друг спрашивает, что ставить, автор отвечает карточкой прогноза.

Сообщения приходят на доли трека, «печатает…» с прыгающими точками, на дропе — сообщение-карточка матча
(эмблемы, время, прогноз, кэф); дальше — «почему?», «расписал в канале» + превью ссылки на канал, «подписался»;
в конце — плашка «ПОДПИСЫВАЙСЯ · @jarvibet». Тёмная тема, обои чата — хоккейные каракули.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from reels import core as C
from reels.core import W, H

BG = (14, 22, 33)
IN = (33, 45, 59)
OUT = (43, 82, 120)
TXT = (240, 244, 248)
SUB = (140, 160, 180)
ACC = (100, 181, 246)
TOP, BOT = 380, 1466          # область сообщений


class Chat(C.Reel):
    def __init__(self, home, away, league, pick, coef, when, chance=None, friend='Серёга', u=60 / 65, drop=2.77, seed=8):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.pick, self.coef, self.when, self.friend, self.chance = pick, coef, when, friend, chance
        self.league = 'НХЛ' if str(league).upper() == 'NHL' else 'КХЛ'
        b = self.b
        fav = (self.a if 'ПОБЕДА ' + self.a.up[:4] in pick.upper() else self.h).short
        # (время, кто, содержимое) ; 'typing' — «печатает»
        self.script = [                                       # (время, кто, текст, время на часах)
            (0.25, 'in', 'что ставим сегодня? 👀', '14:02'),
            (b(-1.8), 'in', 'только без «я хз» 😅', '14:02'),
            ((b(-1), self.drop), 'out', 'typing', ''),
            (self.drop, 'out', 'card', '14:03'),
            (b(3), 'in', 'почему %s? 🤔' % fav, '14:03'),
            ((b(4), b(5)), 'out', 'typing', ''),
            (b(5), 'out', 'расписал в канале: составы, форма, цифры', '14:04'),
            (b(6.5), 'out', 'link', '14:04'),
            ((b(7.5), b(8.5)), 'in', 'typing', ''),
            (b(8.5), 'in', 'подписался 🤝 спасибо', '14:05'),
        ]
        self.t_react = b(2)                                   # друг ставит 🔥 на карточку
        self.t_end = b(10)
        self.dur = b(13)
        self.cover_t = b(7.2)
        self._prep()

    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        bg = Image.new('RGBA', (W, H), BG + (255,))
        d = ImageDraw.Draw(bg)
        col = (22, 33, 47, 255)
        for _ in range(70):                                  # обои: шайбы, клюшки, звёздочки
            x, y = rnd.uniform(0, W), rnd.uniform(0, H)
            k = rnd.integers(0, 3)
            if k == 0:
                d.ellipse((x - 22, y - 9, x + 22, y + 9), outline=col, width=4)
                d.ellipse((x - 22, y - 17, x + 22, y + 1), outline=col, width=4)
            elif k == 1:
                a = rnd.uniform(0, math.pi)
                dx, dy = 50 * math.cos(a), 50 * math.sin(a)
                d.line((x - dx, y - dy, x + dx, y + dy), fill=col, width=5)
                d.line((x + dx, y + dy, x + dx + 22 * math.cos(a + 1.3), y + dy + 22 * math.sin(a + 1.3)), fill=col, width=5)
            else:
                pts = []
                for i in range(10):
                    r = 16 if i % 2 == 0 else 7
                    ang = i * math.pi / 5 - math.pi / 2
                    pts.append((x + r * math.cos(ang), y + r * math.sin(ang)))
                d.polygon(pts, outline=col, width=3)
        self.bg = bg
        # шапка
        hd = Image.new('RGBA', (W, 170), (20, 30, 43, 250))
        av = C.lgrad(104, 104, (255, 150, 90), (220, 80, 110), 45)
        av.putalpha(C.ellipse(104, 104).getchannel('A'))
        C.put(av, C.text(self.friend[0], 'golos', 56, (255, 255, 255), 700), 52, 52)
        C.put(hd, av, 130, 92)
        C.put(hd, C.ellipse(30, 30, (20, 30, 43)), 168, 130)
        C.put(hd, C.ellipse(20, 20, (80, 220, 120)), 168, 130)
        C.put(hd, C.text('‹', 'golos', 80, ACC, 500), 50, 88)
        self.hd = hd
        self.name = C.text(self.friend, 'golos', 46, TXT, 700)
        self.st_on = C.text('в сети', 'golos', 34, SUB, 500)
        self.st_ty = C.text('печатает…', 'golos', 34, ACC, 500)
        self.msgs = []
        ins = [tm if not isinstance(tm, tuple) else tm[0] for tm, side, kind, clk in self.script if side == 'in']
        for tm, side, kind, clk in self.script:
            if kind == 'typing':
                continue
            mk = (lambda rd: self.card(clk, rd)) if kind == 'card' else (lambda rd: self.link(clk, rd)) if kind == 'link' \
                else (lambda rd: self.bubble(kind, side, clk, rd))
            t_read = min([x for x in ins if x > tm] or [1e9])        # прочитано — когда друг ответил
            self.msgs.append((tm, side, mk(False), mk(True), t_read, kind))
        self.typing = [(tm, side) for tm, side, kind, clk in self.script if kind == 'typing']
        self.react = C.rrect(150, 64, 32, (70, 120, 170))
        C.put(self.react, C.text('🔥 1', 'golos', 36, (255, 255, 255), 700), 75, 32)
        self.events = sorted(set([m[0] for m in self.msgs] + [a for (a, b), s in self.typing] + [b for (a, b), s in self.typing]))

    def bubble(self, s, side, clk='14:02', read=True):
        body = C.lines(s, 'golos', 56, 760, TXT, 500, gap=0.18, align='l', max_lines=4)
        w = max(body.width + 70, 260)
        h = body.height + 90
        im = C.rrect(w, h, 34, OUT if side == 'out' else IN)
        im.alpha_composite(body, (34, 24))
        self._meta(im, side == 'out', clk, read)
        return im

    def _meta(self, im, out=True, clk='14:02', read=True):
        meta = C.text(clk, 'golos', 26, (170, 200, 230) if out else SUB, 500)
        x = im.width - 28 - meta.width - (52 if out else 0)
        C.put(im, meta, x, im.height - 44, anchor='tl')
        if out:                                              # галочки: одна — доставлено, две — прочитано
            d = ImageDraw.Draw(im)
            for k in ((0, 14) if read else (7,)):
                x0, y0 = im.width - 74 + k, im.height - 30
                d.line((x0, y0, x0 + 7, y0 + 7, x0 + 20, y0 - 8), fill=(170, 210, 245, 255), width=3)

    def card(self, clk='14:03', read=True):
        w, h = 880, 660
        im = C.rrect(w, h, 34, OUT)
        inner = C.rrect(w - 36, 320, 24, (20, 30, 43))
        g = C.lgrad(w - 36, 320, tuple(int(c * 0.55) for c in self.h.c1), tuple(int(c * 0.55) for c in self.a.c1), 0, 255, 255)
        g.putalpha(inner.getchannel('A'))
        C.put(im, g, w / 2, 178)
        C.put(im, self.h.emb(210), w / 2 - 215, 160)
        C.put(im, self.a.emb(210), w / 2 + 215, 160)
        C.put(im, C.text('VS', 'unb', 50, (255, 255, 255), 800), w / 2, 160)
        C.put(im, C.text('%s · %s' % (self.league, self.when), 'golos', 32, (230, 236, 244), 600), w / 2, 296)
        C.put(im, C.text(self.pick.upper(), 'unb', 60, TXT, 800, max_w=w - 70), w / 2, 400)
        pill = C.rrect(330, 90, 45, (255, 255, 255))
        C.put(pill, C.text('КЭФ ' + C.fmt_k(self.coef), 'unb', 44, (30, 60, 90), 800), 165, 45)
        if self.chance:
            ch = C.rrect(300, 90, 45, (30, 50, 72))
            C.put(ch, C.text('ШАНС %d%%' % self.chance, 'unb', 40, (170, 215, 255), 800), 150, 45)
            C.put(im, pill, w / 2 - 170, 495)
            C.put(im, ch, w / 2 + 170, 495)
        else:
            C.put(im, pill, w / 2, 495)
        self._meta(im, True, clk, read)
        return im

    def link(self, clk='14:04', read=True):
        w, h = 860, 340
        im = C.rrect(w, h, 34, OUT)
        C.put(im, C.text('t.me/' + C.HANDLE[1:], 'golos', 48, (170, 215, 255), 600), 34, 30, anchor='tl')
        bar = C.rrect(8, 170, 4, (170, 215, 255))
        C.put(im, bar, 40, 190)
        C.put(im, C.tg_icon(120), w - 110, 190)
        C.put(im, C.text('JARVIS · прогнозы на хоккей', 'golos', 42, TXT, 700, max_w=600), 70, 120, anchor='tl')
        C.put(im, C.text('КХЛ и НХЛ каждый день', 'golos', 38, (200, 220, 240), 500), 70, 180, anchor='tl')
        C.put(im, C.text('разборы, кэфы, итоги', 'golos', 38, (200, 220, 240), 500), 70, 228, anchor='tl')
        self._meta(im, True, clk, read)
        return im

    def typing_bubble(self, t, side):
        im = C.rrect(170, 96, 34, OUT if side == 'out' else IN)
        for i in range(3):
            y = 48 - 10 * max(0.0, math.sin(t * 9 - i * 0.9))
            C.put(im, C.ellipse(20, 20, (200, 214, 230)), 50 + i * 35, y)
        return im

    def items(self, t):
        """Что видно в чате к моменту t: [(картинка, сторона, время появления)]."""
        out = []
        for tm, side, im, im_r, t_read, kind in self.msgs:
            if t >= tm:
                img = im_r if t >= t_read else im
                if kind == 'card' and t >= self.t_react:          # реакция друга
                    img = img.copy()
                    k = C.out_back(C.seg(t, self.t_react, self.t_react + 0.3), 2.0)
                    C.put(img, C.scale(self.react, max(0.1, k)), 30 + 75, img.height - 46)
                out.append((img, side, tm))
        for (a, b), side in self.typing:
            if a <= t < b:
                out.append((self.typing_bubble(t, side), side, a))
        out.sort(key=lambda x: x[2])
        return out

    def content_h(self, t):
        return sum(im.height + 22 for im, _, _ in self.items(t))

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        its = self.items(t)
        ev = [x for x in self.events if x <= t]
        te = ev[-1] if ev else 0.0
        hc = C.lerp(self.content_h(te - 0.001), self.content_h(te + 0.001), C.out_cubic(C.seg(t, te, te + 0.3)))
        y = BOT - hc
        for im, side, tm in its:
            p = C.out_cubic(C.seg(t, tm, tm + 0.22))
            s = 0.9 + 0.1 * p
            img = C.scale(im, s) if s < 0.999 else im
            if side == 'out' and tm == D and t >= D:                         # карточка на дропе — с отскоком
                img = C.scale(im, 0.8 + 0.2 * C.out_back(C.seg(t, tm, tm + 0.4), 1.6))
            x = 40 if side == 'in' else W - 40 - img.width
            C.put(fr, img, x, y + (1 - p) * 30 + (im.height - img.height), p, anchor='tl')
            y += im.height + 22
        # подпись-крючок сверху, пока есть место
        top_msg = BOT - hc
        ka = C.seg(top_msg, 700, 820) * C.seg(t, 0.0, 0.2)
        if ka > 0:
            C.put(fr, self._pov(), W / 2, 520, ka)
        # шапка поверх (и всё, что уехало выше)
        fr.alpha_composite(Image.new('RGBA', (W, 190), (20, 30, 43, 255)), (0, 0))
        fr.alpha_composite(self.hd, (0, 190))
        C.put(fr, self.name, 220, 230, anchor='tl')
        typing_in = any(a <= t < b and side == 'in' for (a, b), side in self.typing)
        C.put(fr, self.st_ty if typing_in else self.st_on, 220, 292, anchor='tl')
        # поле ввода
        fr.alpha_composite(C.rrect(W - 80, 100, 50, (24, 35, 49)), (40, 1490))
        C.put(fr, C.text('Сообщение', 'golos', 36, (110, 128, 146), 500), 100, 1540 - 18, anchor='tl')
        # финал
        if t >= self.t_end:
            k = C.out_expo(C.seg(t, self.t_end, self.t_end + 0.6 * u))
            dim = Image.new('RGBA', (W, H), (6, 10, 16, int(170 * k)))
            fr.alpha_composite(dim)
            pl = self._end()
            C.put(fr, pl, W / 2, 900 + 60 * (1 - k), k)
        # дроп: лёгкий толчок
        z = 1 + 0.025 * (1 - C.seg(t, D, D + 0.5)) * (t >= D)
        fr = C.zoom(fr, z, W / 2, 1100)
        return C.vignette(fr, 0.3)

    def _pov(self):
        if not hasattr(self, '_pv'):
            self._pv = C.lines('КОГДА ДРУГ СПРАШИВАЕТ, ЧТО СТАВИТЬ', 'onest', 76, 960, (255, 255, 255), 800, gap=0.05,
                               max_lines=2)
            self._pv = C.with_shadow(self._pv, 10, 0.9, 4)
        return self._pv

    def _end(self):
        if not hasattr(self, '_e'):
            w, h = 900, 520
            im = C.rrect(w, h, 44, (20, 30, 43), outline=ACC, width=3)
            C.put(im, C.text('НЕ ГАДАЙ — ПОДПИШИСЬ', 'unb', 54, TXT, 800, max_w=w - 80), w / 2, 90)
            C.put(im, C.text('прогнозы на КХЛ и НХЛ каждый день', 'golos', 38, SUB, 500), w / 2, 160)
            C.put(im, C.tg_icon(150), w / 2, 290)
            C.put(im, C.text(C.HANDLE, 'unb', 64, ACC, 800), w / 2, 440)
            self._e = im
        return self._e
