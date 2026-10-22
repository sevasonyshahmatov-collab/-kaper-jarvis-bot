# -*- coding: utf-8 -*-
"""«Как работает JARVIS» — три формата с визуалом на пробу (владелец 22.10: «попробуй разные форматы, выберем»).
Данные — матчи следующего игрового дня (team/series/series_data.py: приложение КХЛ / API НХЛ, линия Pinnacle, прогноз по
правилу владельца — как у конвейера шортсов); D = dict(day='23.10', lg='КХЛ', rows=[(время, хоз, гости, П1, Х, П2,
прогноз, кэф)], case=dict(h, a, time, last_h=[(счёт, 'В'|'П')], last_a=[…])). Пример без сети — SAMPLE (КХЛ 22.10,
team/out/2026-10-22/facts_khl.md).
  Sheet  — экран таблицы: строки матчей заполняются, камера идёт к колонке прогноза;
  Scale  — инфографика: шкала кэфов, зоны «мало» / 1,6–2,3 / «лотерея», реальные прогнозы падают на шкалу;
  Case   — разбор одного матча (СКА — Сибирь): эмблемы, форма, цифры по шагам.
Без слов «вероятность» и «расчёт», без столбца процентов.
"""
from PIL import Image, ImageDraw

from reels import core as C
from reels.core import W
from reels.explainer import Explainer, ACC, WHITE, GREY

SAMPLE = dict(day='22.10', lg='КХЛ', rows=[
    ('16:30', 'Авангард', 'Нефтехимик', '1.87', '3.81', '3.66', 'Х2 Нефтехимик', '1.95'),
    ('19:30', 'СКА', 'Сибирь', '1.73', '3.97', '4.17', 'Ф2 (+1,5) Сибирь', '1.63'),
    ('19:30', 'Сочи', 'Динамо Минск', '4.41', '4.20', '1.65', 'П2 Динамо Минск', '1.65'),
], case=dict(h='СКА', a='Сибирь', time='19:30', last_h=[('0:2', 'П'), ('0:1', 'П'), ('1:3', 'П')],
             last_a=[('3:2 ОТ', 'В')]))
GREEN = (52, 199, 120)
RED = (235, 87, 87)
INK = (10, 16, 28)


def _cell(s, w, h, size=30, col=(30, 34, 44), bold=700, fill=None, align='l'):
    im = Image.new('RGBA', (w, h), fill + (255,) if fill else (0, 0, 0, 0))
    tx = C.text(s, 'mont', size, col, bold, max_w=w - 20, trim=True) if s else None
    if tx:
        x = 12 if align == 'l' else (w - tx.width) // 2
        im.alpha_composite(tx, (x, (h - tx.height) // 2))
    return im


class Sheet(Explainer):
    """Формат 1: «экран таблицы»."""
    VIZ = True
    COLS = [('Время', 104), ('Хозяева', 190), ('Гости', 214), ('П1', 82), ('Х', 82), ('П2', 82), ('Прогноз', 280), ('Кэф', 86)]
    RH = 86

    def __init__(self, ep, u=0.5, D=None):
        super().__init__(ep, u=u)
        self.D = D = D or SAMPLE
        self.sw = sum(w for _, w in self.COLS)
        self.head = self._row([c for c, _ in self.COLS], fill=(232, 236, 244), bold=900, col=(70, 78, 96))
        self.rows = [self._row(r) for r in D['rows'][:5]]
        self.nr = len(self.rows)
        self.title = C.text('%s · МАТЧИ %s' % (D['lg'], D['day']), 'mont', 34, WHITE, 900, track=0.1)
        self.paper = C.rrect(self.sw + 24, self.RH * (self.nr + 1) + 24, 18, fill=(255, 255, 255))
        x0 = sum(w for _, w in self.COLS[:6])
        self.px = x0 + (self.COLS[6][1] + self.COLS[7][1]) / 2             # центр колонок «Прогноз»+«Кэф»
        self.pw = self.COLS[6][1] + self.COLS[7][1]
        self.upd = C.text('ОБНОВЛЕНО · 05:00 МСК', 'mont', 30, (10, 16, 28), 900, track=0.08)
        self.updbox = C.rrect(self.upd.width + 40, self.upd.height + 26, 12, fill=GREEN)

    def _row(self, vals, fill=None, bold=700, col=(30, 34, 44)):
        im = Image.new('RGBA', (self.sw, self.RH), (255, 255, 255, 255) if not fill else fill + (255,))
        x = 0
        d = ImageDraw.Draw(im)
        for (name, w), v in zip(self.COLS, vals):
            im.alpha_composite(_cell(v, w, self.RH, col=col, bold=bold, align='c' if w < 110 else 'l'), (x, 0))
            d.line([(x, 0), (x, self.RH)], fill=(214, 219, 228), width=2)
            x += w
        d.line([(0, self.RH - 1), (self.sw, self.RH - 1)], fill=(214, 219, 228), width=2)
        return im

    def _sheet(self, t, phase, t0):
        im = Image.new('RGBA', (self.sw, self.RH * (self.nr + 1)), (255, 255, 255, 255))
        im.alpha_composite(self.head, (0, 0))
        for i, r in enumerate(self.rows):
            if phase == 'hook':
                k = 1.0
            elif phase == 's2':                                          # строки «печатаются» по очереди
                k = C.clamp((t - t0 - 0.4 - i * 0.6) / 0.35)
            else:
                k = 1.0
            if k <= 0:
                continue
            row = r.copy()
            if k < 1:
                row = row.crop((0, 0, max(1, int(self.sw * k)), self.RH))
            im.alpha_composite(row, (0, self.RH * (i + 1)))
        if phase == 's3':                                                # прогон обновления: зелёная полоса сверху вниз
            y = int(C.clamp((t - t0 - 0.3) / 1.2) * self.RH * (self.nr + 1))
            band = Image.new('RGBA', (self.sw, 30), GREEN + (110,))
            if 0 < y < self.RH * (self.nr + 1):
                im.alpha_composite(band, (0, max(0, y - 30)))
            k = C.clamp((t - t0 - 1.6) / 0.4)                            # подсветка колонки прогноза
            if k > 0:
                hl = Image.new('RGBA', (self.pw, self.RH * self.nr), ACC + (int(70 * k),))
                im.alpha_composite(hl, (int(self.px - self.pw / 2), self.RH))
        return im

    def visual(self, fr, t, phase, t0):
        sh = self._sheet(t, phase, t0)
        card = self.paper.copy()
        card.alpha_composite(sh, (12, 12))
        if phase == 'hook':                                              # влетает с наклоном
            k = C.out_cubic(C.seg(t, 0.4, 1.2))
            card = C.rotate(card, -6 * (1 - k))
            s = (W - 60) / card.width * (0.8 + 0.2 * k)
            C.put(fr, C.scale(card, s), W / 2, self.VIZ_Y + 120 * (1 - k), a=k)
        elif phase == 's2':
            s = (W - 60) / card.width
            C.put(fr, C.scale(card, s), W / 2, self.VIZ_Y)
        else:                                                            # наезд на колонку прогноза
            k = C.in_out(C.seg(t, t0 + 1.6, t0 + 3.0))
            s = (W - 60) / card.width * (1 + 0.7 * k)
            cx = W / 2 - (self.px + 12 - card.width / 2) * s * k
            C.put(fr, C.scale(card, s), cx, self.VIZ_Y)
            if t > t0 + 0.3:
                self._slam(fr, self.updbox, W / 2, self.VIZ_Y - 300, t, t0 + 0.3, z0=1.3)
                self._slam(fr, self.upd, W / 2, self.VIZ_Y - 300, t, t0 + 0.3, z0=1.3)
        if phase != 's3':
            C.put(fr, self.title, W / 2, self.VIZ_Y - 290)


class Scale(Explainer):
    """Формат 2: инфографика — шкала кэфов."""
    VIZ = True
    LO, HI = 1.2, 3.0
    X0, X1 = 90, W - 90

    def __init__(self, ep, u=0.5, D=None):
        super().__init__(ep, u=u)
        self.D = D = D or SAMPLE
        self.ticks = {v: C.text(('%.1f' % v).replace('.', ','), 'mont', 34, GREY, 800) for v in (1.2, 1.6, 2.0, 2.3, 2.6, 3.0)}
        self.lab_lo = C.text('МАЛО', 'unb', 34, GREY, 900)
        self.lab_ok = C.text('НАШ КОРИДОР', 'unb', 40, INK, 900)
        self.lab_hi = C.text('ЛОТЕРЕЯ', 'unb', 34, RED, 900)
        self.picks = []
        for r in D['rows'][:4]:
            k = float(r[7])
            self.picks.append((k, C.text(r[6], 'mont', 30, WHITE, 800, max_w=420), C.text(r[7].replace('.', ','), 'dela', 44, WHITE)))

    def x(self, v):
        return self.X0 + (v - self.LO) / (self.HI - self.LO) * (self.X1 - self.X0)

    def visual(self, fr, t, phase, t0):
        y = self.VIZ_Y - 60
        grow = C.out_cubic(C.seg(t, 0.4, 1.4)) if phase == 'hook' else 1.0
        x1 = self.X0 + (self.X1 - self.X0) * grow
        C.put(fr, C.rrect(int(x1 - self.X0) + 1, 26, 13, fill=(255, 255, 255), a=60), (self.X0 + x1) / 2, y)
        for v, im in self.ticks.items():                                 # деления
            if self.x(v) <= x1:
                C.put(fr, C.rrect(4, 40, 2, fill=(255, 255, 255), a=120), self.x(v), y)
                C.put(fr, im, self.x(v), y + 60)
        zones = []
        if phase in ('s2', 's3'):
            zones.append((self.LO, 1.6, (150, 156, 170), self.lab_lo, C.clamp((t - (t0 if phase == 's2' else 0) - 0.2) / 0.3) if phase == 's2' else 1))
        if phase == 's3':
            zones.append((2.3, self.HI, RED, self.lab_hi, C.clamp((t - t0 - 0.2) / 0.3)))
            zones.append((1.6, 2.3, GREEN, self.lab_ok, C.clamp((t - t0 - 1.3) / 0.3)))
        for a, b, col, lab, k in zones:
            if k <= 0:
                continue
            w = int(self.x(b) - self.x(a))
            C.put(fr, C.rrect(w, 26, 13, fill=col, a=int(230 * k)), (self.x(a) + self.x(b)) / 2, y)
            ly = y - 190 if col == GREEN else y - 80
            if col == GREEN:
                C.put(fr, C.rrect(lab.width + 40, lab.height + 24, 12, fill=GREEN, a=int(255 * k)), (self.x(a) + self.x(b)) / 2, ly)
            C.put(fr, lab, (self.x(a) + self.x(b)) / 2, ly, a=k)
        if phase == 's3':                                                # реальные прогнозы 22.10 падают в коридор
            for i, (k, name, kf) in enumerate(self.picks):
                f = C.out_back(C.seg(t, t0 + 1.8 + i * 0.35, t0 + 2.3 + i * 0.35))
                if f <= 0:
                    continue
                px = self.x(k)
                C.put(fr, C.ellipse(46, 46, fill=WHITE), px, y - 300 * (1 - f) + 0)
                row_y = y + 170 + i * 92
                C.put(fr, kf, 160, row_y, a=f)
                C.put(fr, name, 220 + name.width / 2, row_y, a=f)
                C.put(fr, C.rrect(3, int(max(1, row_y - y - 40)), 1, fill=(255, 255, 255), a=int(60 * f)), px, (y + row_y) / 2)
            if t > t0 + 1.8:
                C.put(fr, C.text('ПРОГНОЗЫ %s · %s' % (self.D['lg'], self.D['day']), 'mont', 28, GREY, 900, track=0.1), W / 2, y + 140 + len(self.picks) * 92 + 40)


class Case(Explainer):
    """Формат 3: разбор одного матча дня (D['case']): эмблемы → форма хозяев → форма гостей."""
    VIZ = True

    def __init__(self, ep, u=0.5, D=None):
        super().__init__(ep, u=u)
        self.D = D = D or SAMPLE
        c = D['case']
        self.h, self.a = C.match(c['h'], c['a'], 'NHL' if D['lg'] == 'НХЛ' else 'KHL')
        self.eh, self.ea = self.h.emb(300), self.a.emb(300)
        self.vs = C.text('%s · %s МСК' % (D['day'], c['time']), 'mont', 36, GREY, 900, track=0.1)
        self.nh, self.na = (C.text(x.up, 'dela', 64, WHITE, max_w=440) for x in (self.h, self.a))
        self.forms = []
        for t, last in ((self.h, c['last_h']), (self.a, c['last_a'])):
            cap = C.text('%s · ПОСЛЕДНИЕ МАТЧИ' % t.up, 'mont', 32, GREY, 900, track=0.1, max_w=W - 120)
            chips = [(C.text(sc, 'dela', 64 if len(sc) <= 4 else 46, WHITE), GREEN if r == 'В' else RED) for sc, r in last[:3]]
            w = sum(1 for _, r in last[:3] if r == 'В')
            res = C.text('%d %s из %d' % (w, 'победа' if w == 1 else 'победы' if 1 < w < 5 else 'побед', len(chips)),
                         'unb', 48, WHITE, 800)
            self.forms.append((cap, chips, res))

    def visual(self, fr, t, phase, t0):
        y = self.VIZ_Y
        if phase == 'hook':
            for i, (e, n, side) in enumerate(((self.eh, self.nh, -1), (self.ea, self.na, 1))):
                k = C.out_back(C.seg(t, 0.5 + i * 0.25, 1.0 + i * 0.25))
                C.put(fr, e, W / 2 + side * 260 + side * (1 - k) * 400, y - 20, a=C.clamp(k))
                C.put(fr, n, W / 2 + side * 260, y + 190, a=C.clamp(k))
            C.put(fr, C.text('VS', 'dela', 70, ACC), W / 2, y - 20, a=C.clamp((t - 1.1) / 0.3))
            C.put(fr, self.vs, W / 2, y + 280, a=C.clamp((t - 1.3) / 0.3))
            return
        second = phase == 's3'
        cap, chips, res = self.forms[1 if second else 0]
        C.put(fr, C.scale(self.ea if second else self.eh, 0.5), W / 2, y - 260)
        C.put(fr, cap, W / 2, y - 120)
        n = len(chips)
        for i, (im, col) in enumerate(chips):
            k = C.out_back(C.seg(t, t0 + 0.5 + i * 0.35, t0 + 0.9 + i * 0.35))
            if k <= 0:
                continue
            cx = W / 2 + (i - (n - 1) / 2) * 300
            C.put(fr, C.scale(C.rrect(270, 150, 22, fill=col, a=230), 0.6 + 0.4 * k), cx, y + 20)
            C.put(fr, C.scale(im, 0.6 + 0.4 * k), cx, y + 20)
        C.put(fr, res, W / 2, y + 180, a=C.clamp((t - t0 - 0.6 - n * 0.35) / 0.3))
