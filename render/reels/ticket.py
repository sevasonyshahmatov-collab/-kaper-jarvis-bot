# -*- coding: utf-8 -*-
"""«Табло вылетов» — матчи ночи как рейсы на перекидном табло аэропорта, затем посадочный талон.

До дропа строки табло перебирают буквы и встают по одной на каждую долю; на дропе строка нашего прогноза
загорается «ПОСАДКА», камера наезжает; потом снизу выезжает посадочный талон (матч, дата, время, «выход» —
исход, кэф, шанс, штрихкод на корешке) и на долю ложится печать «ПОСАДКА ОТКРЫТА»; финал — «посадка в Telegram».
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw

from reels import core as C
from reels.core import W, H

BOARD = (16, 16, 18)
CELL = (34, 34, 38)
FLAP = (238, 236, 226)
YEL = (255, 204, 40)
GREEN = (60, 220, 120)
INK = (20, 22, 28)
CODES = {'Монреаль': 'МОН', 'Детройт': 'ДЕТ', 'Чикаго': 'ЧИК', 'Каролина': 'КАР', 'Колорадо': 'КОЛ', 'Торонто': 'ТОР',
         'Вегас': 'ВЕГ', 'Лос-Анджелес': 'ЛА', 'Айлендерс': 'АЙЛ', 'Тампа-Бэй': 'ТАМ', 'Калгари': 'КАЛ', 'Анахайм': 'АНА'}
ALPHA = 'АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЭЮЯ0123456789'
CW, CH_ = 42, 66
NCOL = 21


def code(team):
    return CODES.get(team.short, team.up[:3])


class Ticket(C.Reel):
    def __init__(self, flights, ours, league, chance, day, u=60 / 81, drop=2.96, seed=51):
        """flights = [('02:00', хозяева, гости, 'П1', 1.81), ...]; ours — индекс нашего рейса."""
        super().__init__(u, drop, seed)
        lg = league
        self.flights = []
        for tm, h, a, gate, k in flights:
            th, ta = C.match(h, a, lg)
            self.flights.append((tm, th, ta, gate, k))
        self.ours, self.chance, self.day = ours, chance, day
        self.league = 'НХЛ' if str(league).upper() == 'NHL' else 'КХЛ'
        tm, th, ta, gate, k = self.flights[ours]
        self.fav = th if gate == 'П1' else ta
        self.t_pass = self.b(2)
        self.t_stamp = self.b(6)
        self.t_cta = self.b(8.5)
        self.dur = self.b(12)
        self.cover_t = self.b(7.4)
        self.rows = []
        for tm, th, ta, gate, k in self.flights:
            s = '%s %s-%s %s %s' % (tm, code(th), code(ta), gate, C.fmt_k(k))
            self.rows.append(s.ljust(NCOL)[:NCOL])
        self._prep()

    def _prep(self):
        self.cells = {}
        for ch in set(ALPHA + ''.join(self.rows) + ' -.:'):
            self.cells[ch] = self._cell(ch)
        self.cells_hi = {ch: self._cell(ch, YEL) for ch in set(self.rows[self.ours])}
        bw, bh = NCOL * (CW + 4) + 60, 220 + len(self.rows) * (CH_ + 26)
        bd = C.rrect(bw, bh, 26, BOARD)
        C.put(bd, C.text('ВЫЛЕТ', 'robc', 56, YEL, 800, track=0.15), 140, 64)
        C.put(bd, C.text('DEPARTURES · %s · %s' % (self.league, self.day), 'robc', 30, (170, 170, 176), 600), bw - 40 - C.text(
            'DEPARTURES · %s · %s' % (self.league, self.day), 'robc', 30, (170, 170, 176), 600).width, 52, anchor='tl')
        hdr = ['ВРЕМЯ', 'МАТЧ', 'ВЫХОД', 'КЭФ']
        xs = [30, 30 + 6 * (CW + 4), 30 + 14 * (CW + 4), 30 + 17 * (CW + 4)]
        for s, x in zip(hdr, xs):
            C.put(bd, C.text(s, 'robc', 26, (150, 150, 156), 700, track=0.1), x, 128, anchor='tl')
        self.board_im = bd
        self.bg = C.vgrad(W, H, [(0, (40, 44, 52)), (0.5, (22, 24, 30)), (1, (10, 10, 14))]).convert('RGBA')
        self.bg = C.add_light(self.bg, C.radial(1400, 1000, (60, 60, 70), 255, 1.6), W / 2, 700, 1.0)
        self.pass_im = self._pass()
        self.stamp = self._stamp()

    def _cell(self, ch, col=FLAP):
        im = C.rrect(CW, CH_, 6, CELL)
        if ch.strip():
            C.put(im, C.text(ch, 'robc', 54, col, 800), CW / 2, CH_ / 2)
        d = ImageDraw.Draw(im)
        d.line((0, CH_ / 2, CW, CH_ / 2), fill=(8, 8, 10, 255), width=3)
        sh = Image.new('RGBA', (CW, CH_ // 2), (0, 0, 0, 40))
        im.alpha_composite(sh, (0, CH_ // 2))
        return im

    def row_text(self, i, t):
        """Строка табло на момент t: пока не встала — перебирает буквы."""
        target = self.rows[i]
        t_lock = self.b(-3 + 3 * i / max(1, len(self.rows) - 1))
        out = []
        for j, ch in enumerate(target):
            tj = t_lock - 0.5 + j * 0.025
            if t >= tj + 0.5 or ch == ' ':
                out.append(ch)
            elif t < 0.15:
                out.append(' ')
            else:
                r = random.Random(hash((i, j, int(t * 18))) & 0xffff)
                out.append(r.choice(ALPHA))
        return ''.join(out), t >= t_lock

    def board(self, t):
        bd = self.board_im.copy()
        for i in range(len(self.rows)):
            s, locked = self.row_text(i, t)
            hi = i == self.ours and t >= self.drop
            y = 180 + i * (CH_ + 26)
            for j, ch in enumerate(s):
                cell = (self.cells_hi.get(ch) if hi else None) or self.cells.get(ch) or self.cells[' ']
                bd.alpha_composite(cell, (30 + j * (CW + 4), y))
            if hi:
                blink = int((t - self.drop) / (self.u / 2)) % 2 == 0
                lamp = C.ellipse(26, 26, GREEN if blink else (30, 80, 50))
                C.put(bd, lamp, 30 + NCOL * (CW + 4) + 4, y + CH_ / 2)
                d = ImageDraw.Draw(bd)
                d.rounded_rectangle((20, y - 8, 30 + NCOL * (CW + 4) + 22, y + CH_ + 8), 10, outline=YEL + (255,), width=4)
        return bd

    def _pass(self):
        tm, th, ta, gate, k = self.flights[self.ours]
        w, h = 980, 1060
        im = C.rrect(w, h, 36, (250, 249, 245))
        band = Image.new('RGBA', (w, 190), (0, 0, 0, 0))
        g = C.lgrad(w, 190, C.mix(th.c1, INK, 0.15), C.mix(ta.c1, INK, 0.15), 0)
        g.putalpha(C.rrect(w, 190, 36).getchannel('A'))
        band.alpha_composite(g)
        band.alpha_composite(C.lgrad(w, 40, C.mix(th.c1, INK, 0.15), C.mix(ta.c1, INK, 0.15), 0), (0, 150))
        im.alpha_composite(band)
        C.put(im, C.text('ПОСАДОЧНЫЙ ТАЛОН', 'robc', 44, (255, 255, 255), 800, track=0.12), 50, 50, anchor='tl')
        C.put(im, C.text('JARVIS · ПРОГНОЗЫ НА ХОККЕЙ', 'robc', 28, (235, 235, 240), 600, track=0.1), 50, 112, anchor='tl')
        C.put(im, C.text(code(th), 'robc', 150, INK, 800), 200, 330)
        C.put(im, C.text(code(ta), 'robc', 150, INK, 800), w - 200, 330)
        d = ImageDraw.Draw(im)
        d.line((330, 330, w - 330, 330), fill=(180, 180, 186, 255), width=4)
        C.put(im, C.text('VS', 'robc', 48, (150, 150, 156), 800), w / 2, 330)
        C.put(im, th.emb(110), 200, 470)
        C.put(im, ta.emb(110), w - 200, 470)
        C.put(im, C.text(th.up, 'robc', 32, (110, 110, 118), 700, max_w=300), 200, 550)
        C.put(im, C.text(ta.up, 'robc', 32, (110, 110, 118), 700, max_w=300), w - 200, 550)
        fields = [('ДАТА', self.day), ('ВЫЛЕТ', tm + ' МСК'), ('ВЫХОД', gate), ('КЭФ', C.fmt_k(k)), ('ШАНС', '%d%%' % self.chance),
                  ('РЕЙС', '%s-%s' % (self.league, self.day.replace('.', '')))]
        for n, (lab, val) in enumerate(fields):
            x = 70 + (n % 3) * 300
            y = 630 + (n // 3) * 130
            C.put(im, C.text(lab, 'robc', 28, (140, 140, 148), 700, track=0.12), x, y, anchor='tl')
            C.put(im, C.text(val, 'robc', 56, INK if lab != 'ВЫХОД' else C.mix(self.fav.c1, INK, 0.2), 800), x, y + 36, anchor='tl')
        # перфорация и корешок со штрихкодом
        for x in range(30, w - 20, 26):
            d.ellipse((x, 892, x + 10, 902), fill=(200, 200, 206, 255))
        C.put(im, C.text('ПРОГНОЗ: ' + self.flights_pick().upper(), 'robc', 46, INK, 800, max_w=w - 100), w / 2, 950)
        rnd = np.random.default_rng(5)
        x = 120
        while x < w - 120:
            ww = int(rnd.choice([3, 4, 6, 8]))
            d.rectangle((x, 990, x + ww, 1035), fill=INK + (255,))
            x += ww + int(rnd.choice([3, 4, 6]))
        return C.with_shadow(im, 24, 0.5, 18)

    def flights_pick(self):
        tm, th, ta, gate, k = self.flights[self.ours]
        return 'победа ' + C.gen_case(self.fav.short, 'g') if gate in ('П1', 'П2') else gate

    def _stamp(self):
        w, h = 560, 210
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        col = (30, 150, 80)
        d.rounded_rectangle((6, 6, w - 6, h - 6), 24, outline=col + (255,), width=10)
        C.put(im, C.text('ПОСАДКА', 'dela', 76, col, max_w=w - 80), w / 2, 80)
        C.put(im, C.text('ОТКРЫТА', 'dela', 56, col, max_w=w - 80), w / 2, 150)
        al = np.asarray(im.getchannel('A'), np.float32) * np.clip(np.random.default_rng(2).normal(0.9, 0.22, (h, w)), 0.3, 1)
        im.putalpha(Image.fromarray(al.astype(np.uint8)))
        return C.rotate(im, -10)

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        bd = self.board(t)
        # табло: после дропа — наезд на нашу строку; когда выезжает талон — уходит вверх и темнеет
        zp = C.in_out(C.seg(t, D, D + 0.8 * u))
        up = C.in_out(C.seg(t, self.t_pass, self.t_pass + 0.8 * u))
        s = 1.0 + 0.12 * zp * (1 - up) - 0.25 * up
        bimg = C.scale(bd, s)
        yc = 860 - 260 * zp * (1 - up) - 420 * up
        oy = (180 + self.ours * (CH_ + 26) + CH_ / 2 - bd.height / 2) * s * zp * (1 - up)
        C.put(fr, C.shadow(bimg, 26, 0.6), W / 2, yc + 30 - oy)
        C.put(fr, bimg, W / 2, yc - oy, 1 - 0.55 * up)
        if t < D:
            C.put(fr, C.text('ТАБЛО ПРОГНОЗОВ', 'robc', 92, (255, 255, 255), 800, track=0.04), W / 2, 330, C.seg(t, 0.1, 0.5))
        # посадочный талон
        if t >= self.t_pass:
            k = C.out_expo(C.seg(t, self.t_pass, self.t_pass + 0.9 * u))
            ps = self.pass_im
            C.put(fr, ps, W / 2, 1010 + (1 - k) * 1100)
            if t >= self.t_stamp:
                q = C.seg(t, self.t_stamp, self.t_stamp + 0.14)
                C.put(fr, C.scale(self.stamp, 1.5 - 0.5 * q), W / 2 + 250, 1290, min(1.0, 0.3 + q))
        if t >= self.t_cta:
            k = C.out_expo(C.seg(t, self.t_cta, self.t_cta + 0.6 * u))
            pl = C.rrect(900, 140, 70, C.TG_BLUE)
            C.put(pl, C.tg_icon(104, (255, 255, 255), C.TG_BLUE), 80, 70)
            C.put(pl, C.text('ПОСАДКА — В TELEGRAM ' + C.HANDLE, 'robc', 48, (255, 255, 255), 800, max_w=720), 520, 70)
            C.put(fr, pl, W / 2, 330 + 40 * (1 - k), k)
        dx, dy = 0.0, 0.0
        for th in [D, self.t_stamp]:
            sx, sy = C.shake(t, th, 14, 0.3)
            dx, dy = dx + sx, dy + sy
        fr = C.zoom(fr, 1.0 + 0.01 * math.sin(t * 0.5), dx=dx, dy=dy)
        return C.vignette(fr, 0.45)
