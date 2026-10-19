# -*- coding: utf-8 -*-
"""Трейлер таблицы прогнозов (владелец 19.10): кликбейт-шортс «Я сделал таблицу, которая прогнозирует лучше букмекера»
(заголовок — решение владельца, исключение из правила «без букмекеров» только для этого ролика), дальше листы таблицы
по одному на такт: прогнозы с вероятностью и «зашло / не зашло», «Что заходит», таблица, Elo, сравнение с линией,
точность; в конце — Telegram. Таблица нарисована кодом в виде окна Google Таблиц (скриншотов нет), данные —
render/sheet_data.build (настоящие матчи КХЛ сезона; модель накануне каждого матча — честный «зашло / не зашло»).

    from reels.sheet_trailer import SheetTrailer
    r = SheetTrailer(sheet_data.build(games, nxt), u=60 / 71, pre=4)

Тайминг: до дропа pre долей — крючок (заголовок по словам), на дропе окно таблицы влетает; дальше сцены по долям трека."""
import math

import numpy as np
from PIL import Image, ImageDraw

from reels import core as C
from reels.core import W, H

# окно таблицы
WX, WY, WW, WH = 22, 452, 1036, 1030
RH = 72                                               # высота строки
BAR_H, COL_H, NUM_W, TAB_H = 66, 38, 46, 64
CX0, CY0 = WX + NUM_W, WY + BAR_H + COL_H            # левый верх области ячеек
CW_ = WW - NUM_W                                      # ширина области ячеек
CH_ = WH - BAR_H - COL_H - TAB_H
BG = (9, 12, 20)
PAPER = (255, 255, 255)
GRID = (226, 229, 234)
CHROME = (241, 243, 246)
INK = (32, 33, 36)
DIM = (95, 99, 104)
SEL = (26, 115, 232)
GREEN = (30, 142, 62)
GREEN_L = (206, 234, 214)
RED = (217, 48, 37)
RED_L = (250, 210, 207)
GOLD = (255, 196, 64)
TABS = ['прогнозы', 'Что заходит', 'Таблица', 'Elo', 'Сравнение', 'Точность']
TITLES = ['ПРОГНОЗ НА КАЖДЫЙ МАТЧ', 'ЧТО ЗАХОДИТ У КОМАНД', 'ТАБЛИЦА ЛИГИ', 'РЕЙТИНГ СИЛЫ ELO', 'СРАВНЕНИЕ С ЛИНИЕЙ',
          'ТОЧНОСТЬ ЗА СЕЗОН']
SUBS = ['вероятность · зашло или нет', 'по каждой команде за сезон', 'обновляется сама после матчей',
        'кто набирает форму', 'где модель видит иначе', 'считаю честно — всё видно']
HOOK = [('Я СДЕЛАЛ', 0), ('ТАБЛИЦУ,', 0), ('КОТОРАЯ', 1), ('ПРОГНОЗИРУЕТ', 1), ('ЛУЧШЕ', 2), ('БУКМЕКЕРА', 2)]


def T(s, size, fill=INK, wght=600, font='robc', **kw):
    return C.text(str(s), font, size * 1.14, fill, wght, **kw)      # всё в ячейках чуть крупнее — читается с телефона


def team(name):
    return C.match(name, name, 'KHL')[0]


def heat(v):
    """Заливка ячейки «Что заходит»: красный → белый → зелёный (как условное форматирование)."""
    k = max(0.0, min(1.0, v / 100))
    if k < 0.5:
        return C.mix(RED_L, PAPER, k * 2)
    return C.mix(PAPER, (148, 210, 165), (k - 0.5) * 2)


class SheetTrailer(C.Reel):
    def __init__(self, data, u=60 / 71, pre=4, beats=(6, 5, 4, 5, 5, 5), cta=5, seed=19):
        super().__init__(u, pre * u, seed)
        self.D = data
        self.beats = beats
        self.t_sc = [self.drop]
        for b in beats:
            self.t_sc.append(self.t_sc[-1] + b * u)
        self.t_cta = self.t_sc[-1]
        self.dur = self.t_cta + cta * u + C.FOOTER_END_S * 0.6
        self.cover_t = self.drop + 2.2 * u
        self._prep()

    # ── слои ──
    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        bg = C.vgrad(W, H, [(0, (16, 22, 38)), (0.5, BG), (1, (4, 6, 10))]).convert('RGBA')
        d = ImageDraw.Draw(bg)
        for x in range(0, W, 54):                                    # еле заметная сетка «как таблица» на фоне
            d.line((x, 0, x, H), fill=(255, 255, 255, 9))
        for y in range(0, H, 54):
            d.line((0, y, W, y), fill=(255, 255, 255, 9))
        for _ in range(60):
            x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1, 2.4)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(160, 200, 255, int(rnd.uniform(20, 60))))
        self.bg = bg
        self.glow = C.radial(1500, 1300, (40, 120, 255), 120, 1.8)
        self.hook = [C.with_shadow(C.text(w, 'unb', 104 if len(w) < 10 else 86, GOLD if g == 2 else (255, 255, 255), 900,
                                          max_w=980), 18, 0.7, 8) for w, g in HOOK]
        self.bodies = [self._body_pred(), self._body_what(), self._body_table(), None, self._body_cmp(), None]
        even = [CW_ * i / 8 for i in range(9)]
        cols = [self.pred_cols, self.what_cols, self.table_cols, even, even, even]
        self.frames = [self._frame_chrome(i, cols[i]) for i in range(len(TABS))]
        self.titles = [C.text(s, 'unb', 58 if len(s) < 20 else 50, (255, 255, 255), 900, max_w=980) for s in TITLES]
        self.subs = [C.text(s.upper(), 'mont', 32, (150, 196, 255), 800, track=0.12, max_w=980) for s in SUBS]
        self.nums = [C.text('%02d / %02d' % (i + 1, len(TABS)), 'mono', 30, GOLD, 800, track=0.1) for i in range(len(TABS))]
        self.tg = C.tg_plate(960, 180, font='unb')
        self.cta1 = C.text('ВСЕ ПРОГНОЗЫ', 'unb', 92, (255, 255, 255), 900, max_w=980)
        self.cta2 = C.text('КАЖДЫЙ ДЕНЬ — В TELEGRAM', 'mont', 44, (150, 196, 255), 900, track=0.06, max_w=980)
        self.cursor = self._cursor()
        sh = np.zeros((H, W), np.float32)                             # затемнение под крупным заголовком крючка
        yy = np.arange(H, dtype=np.float32)[:, None]
        sh[:] = 200 * np.exp(-((yy - 860) / 520) ** 2)
        self.hook_shade = Image.merge('RGBA', [Image.new('L', (W, H), 0)] * 3 + [Image.fromarray(sh.astype(np.uint8))])

    def _cursor(self):
        im = Image.new('RGBA', (44, 60), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        pts = [(4, 2), (4, 46), (15, 36), (23, 56), (31, 52), (23, 33), (38, 33)]
        d.polygon(pts, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
        d.line(pts + [pts[0]], fill=(0, 0, 0, 255), width=3)
        return im

    def _frame_chrome(self, active, xs):
        """Окно Google Таблиц: панель с формулой, буквы столбцов, номера строк, вкладки листов снизу."""
        im = C.rrect(WW, WH, 22, PAPER)
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, WW, BAR_H), fill=CHROME)
        d.rounded_rectangle((0, 0, WW, BAR_H + 22), 22, fill=CHROME)
        d.rectangle((0, BAR_H, WW, BAR_H + COL_H), fill=(248, 249, 250))
        fx = ['=ВЕРОЯТНОСТЬ(Хозяева; Гости)', '=ЧАСТОТА(Команда; Ставка)', '=ОЧКИ(В; П; ОТ)', '=ELO(Рейтинг; Итог)',
              '=МОДЕЛЬ − ЛИНИЯ', '=УГАДАНО / МАТЧЕЙ'][active]
        im.alpha_composite(T('fx', 30, (95, 99, 104), 700, font='robci'), (24, 16))
        t = T(fx, 30, INK, 500)
        im.alpha_composite(t, (74, (BAR_H - t.height) // 2))
        d.line((60, 12, 60, BAR_H - 12), fill=GRID, width=2)
        for i in range(len(xs) - 1):                                  # буквы столбцов — по границам столбцов листа
            x0, x1 = NUM_W + xs[i], NUM_W + xs[i + 1]
            d.line((x0, BAR_H, x0, BAR_H + COL_H), fill=GRID, width=1)
            c = T('ABCDEFGHIJ'[i], 24, DIM, 500)
            im.alpha_composite(c, (int((x0 + x1) / 2 - c.width / 2), BAR_H + (COL_H - c.height) // 2))
        d.line((0, BAR_H + COL_H, WW, BAR_H + COL_H), fill=(200, 204, 210), width=2)
        d.rectangle((0, BAR_H + COL_H, NUM_W, WH - TAB_H), fill=(248, 249, 250))
        for r in range(1, 15):
            y = BAR_H + COL_H + (r - 1) * RH
            if y + RH > WH - TAB_H:
                break
            c = T(str(r), 22, DIM, 500)
            im.alpha_composite(c, ((NUM_W - c.width) // 2, int(y + 31 - c.height / 2)))
            d.line((0, y + RH, NUM_W, y + RH), fill=GRID, width=1)
        d.line((NUM_W, BAR_H + COL_H, NUM_W, WH - TAB_H), fill=(200, 204, 210), width=2)
        # вкладки
        d.rectangle((0, WH - TAB_H, WW, WH), fill=CHROME)
        d.line((0, WH - TAB_H, WW, WH - TAB_H), fill=(200, 204, 210), width=2)
        x = 60
        self.tab_x = []
        for i, nm in enumerate(TABS):
            c = T(nm, 24, (24, 90, 48) if i == active else DIM, 700 if i == active else 500)
            w = c.width + 28
            if i == active:
                d.rounded_rectangle((x, WH - TAB_H + 6, x + w, WH - 8), 8, fill=(230, 244, 234))
                d.line((x + 4, WH - 9, x + w - 4, WH - 9), fill=GREEN, width=4)
            im.alpha_composite(c, (x + 14, WH - TAB_H + (TAB_H - c.height) // 2 - 1))
            self.tab_x.append(x + w / 2)
            x += w + 8
        return im

    # ── тела листов (статичные части) ──
    def _grid(self, cols, n, rh=RH, head=None, fill_head=(232, 240, 254)):
        im = Image.new('RGBA', (CW_, CH_), (255, 255, 255, 0))
        d = ImageDraw.Draw(im)
        xs = [0]
        for c in cols:
            xs.append(xs[-1] + c)
        for r in range(n + 1):
            d.line((0, r * rh + rh, CW_, r * rh + rh), fill=GRID, width=1)
        for x in xs[1:-1]:
            d.line((x, 0, x, (n + 1) * rh), fill=GRID, width=1)
        if head:
            d.rectangle((0, 0, CW_, rh), fill=fill_head)
            for i, h in enumerate(head):
                c = T(h, 25, (25, 60, 120), 800)
                im.alpha_composite(c, (int(xs[i] + (cols[i] - c.width) / 2), int((rh - c.height) / 2)))
            d.line((0, rh, CW_, rh), fill=(170, 190, 225), width=2)
        return im, xs

    def _body_pred(self):
        cols = [80, 330, 190, 126, 110, 118]
        im, xs = self._grid(cols, len(self.D['pred']), head=['ДАТА', 'МАТЧ', 'ПРОГНОЗ', 'ШАНС', 'СЧЁТ', 'ИТОГ'])
        self.pred_cols = xs
        return im

    def _pred_row(self, i, r):
        """Строка листа «прогнозы» (без итога — он загорается отдельно)."""
        xs, rh = self.pred_cols, RH
        row = Image.new('RGBA', (CW_, rh), (0, 0, 0, 0))
        h, a = C.match(r['h'], r['a'], 'KHL')
        cells = [T(r['d'], 24, DIM, 500), None, T((h if r['pick'] == r['h'] else a).short, 25, INK, 700, max_w=180),
                 None, T(r['score'], 25, INK, 600, max_w=104)]
        for j, c in enumerate(cells):
            if c is not None:
                row.alpha_composite(c, (int(xs[j] + (xs[j + 1] - xs[j] - c.width) / 2), int((rh - c.height) / 2)))
        e1, e2 = h.emb(46), a.emb(46)
        row.alpha_composite(e1, (xs[1] + 10, int((rh - e1.height) / 2)))
        m = T('%s — %s' % (h.short, a.short), 24, INK, 600, max_w=xs[2] - xs[1] - 110)
        row.alpha_composite(m, (xs[1] + 56, int((rh - m.height) / 2)))
        row.alpha_composite(e2, (xs[2] - 48, int((rh - e2.height) / 2)))
        return row

    def _body_what(self):
        cols = [250] + [(CW_ - 250) / 5] * 5
        im, xs = self._grid(cols, len(self.D['what']), head=['КОМАНДА'] + self.D['what_cols'])
        self.what_cols = xs
        return im

    def _body_table(self):
        cols = [60, 380, 86, 86, 86, 118, 138]
        im, xs = self._grid(cols, len(self.D['table']), head=['#', 'КОМАНДА', 'И', 'В', 'П', 'ШР', 'ОЧКИ'])
        self.table_cols = xs
        return im

    def _body_cmp(self):
        return None

    # ── сцены ──
    def sc_pred(self, lay, t, t0):
        lay.alpha_composite(self.bodies[0], (0, 0))
        rh, xs = RH, self.pred_cols
        for i, r in enumerate(self.D['pred']):
            ti = t0 + 0.35 + i * 0.5 * self.u
            q = C.out_expo(C.seg(t, ti, ti + 0.25))
            if q <= 0:
                continue
            row = self._pred_row(i, r)
            y = rh + i * rh
            C.put(lay, row, CW_ / 2 + 40 * (1 - q), y + rh / 2, q)
            # шанс: полоса растёт
            qb = C.out_expo(C.seg(t, ti + 0.1, ti + 0.6))
            bw = int((xs[4] - xs[3] - 20) * r['p'] / 100 * qb)
            if bw > 2:
                bar = C.rrect(bw, 38, 6, (66, 133, 244), a=70)
                lay.alpha_composite(bar, (xs[3] + 10, int(y + (rh - 38) / 2)))
            pc = T('%d%%' % round(r['p'] * qb), 26, (25, 60, 120), 800)
            C.put(lay, pc, (xs[3] + xs[4]) / 2, y + rh / 2, q)
            # итог: загорается через пол-доли
            qs = C.out_back(C.seg(t, ti + 0.45 * self.u, ti + 0.45 * self.u + 0.3), 1.6)
            if qs > 0.01:
                ok = r['hit']
                chip = C.rrect(116, 46, 23, GREEN_L if ok else RED_L)
                C.put(chip, T('ЗАШЛО' if ok else 'МИМО', 22, GREEN if ok else RED, 800), 58, 23)
                C.put(lay, C.scale(chip, max(0.05, qs)), (xs[5] + xs[6]) / 2, y + rh / 2)
        return self._sel(lay, t, t0, [(5, 1 + k) for k in range(len(self.D['pred']))], self.pred_cols)

    def sc_what(self, lay, t, t0):
        lay.alpha_composite(self.bodies[1], (0, 0))
        rh, xs = RH, self.what_cols
        best = (0, 0, -1)
        for i, r in enumerate(self.D['what']):
            ti = t0 + 0.25 + i * 0.12
            q = C.out_expo(C.seg(t, ti, ti + 0.3))
            if q <= 0:
                continue
            y = rh + i * rh
            tm = team(r['t'])
            e = tm.emb(46)
            lay.alpha_composite(e, (10, int(y + (rh - e.height) / 2)))
            nm = T(tm.short, 25, INK, 700, max_w=180)
            lay.alpha_composite(nm, (66, int(y + (rh - nm.height) / 2)))
            for j, v in enumerate(r['v']):
                qj = C.seg(t, ti + 0.1 + j * 0.06, ti + 0.4 + j * 0.06)
                if qj <= 0:
                    continue
                cell = Image.new('RGBA', (int(xs[j + 2] - xs[j + 1]) - 2, rh - 2), heat(v) + (int(255 * qj),))
                lay.alpha_composite(cell, (int(xs[j + 1]) + 1, int(y) + 1))
                C.put(lay, T('%d%%' % v, 26, INK, 700 if v >= 70 else 500), (xs[j + 1] + xs[j + 2]) / 2, y + rh / 2, qj)
                if v > best[2] and r['n'] >= 5:
                    best = (i, j, v)
        i, j, v = best
        if i >= 0:
            qk = C.out_back(C.seg(t, t0 + 2.2 * self.u, t0 + 2.2 * self.u + 0.35), 1.5)
            if qk > 0.01:
                y = rh + i * rh
                d = ImageDraw.Draw(lay)
                d.rectangle((xs[j + 1], y, xs[j + 2], y + rh), outline=SEL, width=4)
                r = self.D['what'][i]
                bub = self._bubble('%s · %s — %d%% матчей' % (team(r['t']).short, self.D['what_cols'][j], v))
                by = min(CH_ - 50, rh * (len(self.D['what']) + 1) + 60)
                C.put(lay, C.scale(bub, qk), CW_ / 2, by)
        return lay

    def _bubble(self, s):
        t = T(s, 30, (255, 255, 255), 800, max_w=760)
        b = C.rrect(t.width + 60, 70, 35, SEL)
        C.put(b, t, b.width / 2, 35)
        return C.with_shadow(b, 14, 0.35, 6)

    def sc_table(self, lay, t, t0):
        lay.alpha_composite(self.bodies[2], (0, 0))
        rh, xs = RH, self.table_cols
        for i, r in enumerate(self.D['table']):
            ti = t0 + 0.2 + i * 0.09
            q = C.out_expo(C.seg(t, ti, ti + 0.35))
            if q <= 0:
                continue
            y = rh + i * rh + 50 * (1 - q)
            row = Image.new('RGBA', (CW_, rh), (0, 0, 0, 0))
            if i < 3:
                row.alpha_composite(Image.new('RGBA', (CW_, rh - 1), (255, 244, 214, 255)))
            tm = team(r['t'])
            vals = [str(i + 1), None, r['gp'], r['w'], r['l'], ('+%d' % r['gd']) if r['gd'] > 0 else str(r['gd']).replace('-', '−'),
                    r['pts']]
            for j, v in enumerate(vals):
                if v is None:
                    continue
                c = T(v, 27, INK, 800 if j in (0, 6) else 500)
                row.alpha_composite(c, (int(xs[j] + (xs[j + 1] - xs[j] - c.width) / 2), int((rh - c.height) / 2)))
            e = tm.emb(50)
            row.alpha_composite(e, (xs[1] + 12, int((rh - e.height) / 2)))
            nm = T(tm.short, 27, INK, 700, max_w=xs[2] - xs[1] - 80)
            row.alpha_composite(nm, (xs[1] + 64, int((rh - nm.height) / 2)))
            C.put(lay, row, CW_ / 2, y + rh / 2, q)
        return self._sel(lay, t, t0, [(6, 1), (6, 2), (6, 3)], self.table_cols)

    def sc_elo(self, lay, t, t0):
        E = self.D['elo']
        d = ImageDraw.Draw(lay)
        X0, X1, Y0, Y1 = 90, CW_ - 40, 60, CH_ - 250
        hist = E['hist']
        vals = [v for _, row in hist for v in row]
        lo, hi = min(vals) - 10, max(vals) + 10
        for k in range(5):                                           # сетка графика
            y = Y1 - (Y1 - Y0) * k / 4
            d.line((X0, y, X1, y), fill=GRID, width=1)
            c = T(round(lo + (hi - lo) * k / 4), 22, DIM, 500)
            lay.alpha_composite(c, (X0 - c.width - 10, int(y - c.height / 2)))
        q = C.in_out(C.seg(t, t0 + 0.2, t0 + 3.0 * self.u))
        n = len(hist)
        upto = max(2, int(n * q))
        cols = [team(tn).c1 for tn in E['teams']]
        for k, tn in enumerate(E['teams']):
            pts = [(X0 + (X1 - X0) * i / max(1, n - 1), Y1 - (Y1 - Y0) * (row[k] - lo) / (hi - lo)) for i, (_, row) in
                   enumerate(hist[:upto])]
            col = C.mix(cols[k], (0, 0, 0), 0.1) if sum(cols[k]) < 600 else C.mix(cols[k], (0, 0, 0), 0.35)
            d.line(pts, fill=col + (255,), width=6, joint='curve')
            x, y = pts[-1]
            d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=col + (255,))
        # легенда: эмблемы и рейтинг сейчас
        for k, tn in enumerate(E['teams']):
            ql = C.out_back(C.seg(t, t0 + 1.0 + k * 0.12, t0 + 1.35 + k * 0.12), 1.5)
            if ql <= 0.01:
                continue
            x = 40 + k * (CW_ - 80) / 5 + (CW_ - 80) / 10
            tm = team(tn)
            C.put(lay, C.scale(tm.emb(70), max(0.05, ql)), x, Y1 + 90)
            C.put(lay, T(round(E['now'][k] * ql + 1500 * (1 - ql)), 30, INK, 800), x, Y1 + 160, ql)
            C.put(lay, T(tm.short, 21, DIM, 600, max_w=170), x, Y1 + 196, ql)
        return lay

    def sc_cmp(self, lay, t, t0):
        rows = self.D['cmp']
        hdr = T('МАТЧИ ДНЯ: ГДЕ МОДЕЛЬ НЕ СОГЛАСНА С ЛИНИЕЙ', 26, (25, 60, 120), 800, max_w=CW_ - 40)
        C.put(lay, hdr, CW_ / 2, 40)
        rh = 150
        for i, r in enumerate(rows[:4]):
            ti = t0 + 0.25 + i * 0.4 * self.u
            q = C.out_expo(C.seg(t, ti, ti + 0.35))
            if q <= 0:
                continue
            y = 90 + i * rh
            h, a = C.match(r['h'], r['a'], 'KHL')
            box = C.rrect(CW_ - 40, rh - 18, 16, (248, 250, 253), outline=GRID, width=2)
            box.alpha_composite(h.emb(46), (16, 14))
            mt = T('%s — %s · %s' % (h.short, a.short, r['tm']), 25, INK, 700, max_w=520)
            box.alpha_composite(mt, (72, 22))
            box.alpha_composite(a.emb(46), (72 + mt.width + 14, 14))
            out = {'П1': 'победа ' + h.short, 'П2': 'победа ' + a.short, 'Х': 'ничья'}[r['out']] + ' в осн. время'
            ot = T(out, 22, DIM, 600, max_w=CW_ - 120)
            box.alpha_composite(ot, (CW_ - 40 - ot.width - 18, 26)) if 72 + mt.width + 80 + ot.width < CW_ - 60 else None
            qb = C.out_expo(C.seg(t, ti + 0.15, ti + 0.8))
            full = CW_ - 40 - 260
            for k, (lab, v, col) in enumerate((('МОДЕЛЬ', r['model'], GREEN), ('ЛИНИЯ', r['line'], (150, 155, 165)))):
                yy = 74 + k * 32
                box.alpha_composite(T(lab, 20, DIM, 800), (16, yy))
                bw = max(4, int(full * v / 100 * qb))
                box.alpha_composite(C.rrect(bw, 22, 6, col), (110, yy + 2))
                box.alpha_composite(T('%d%%' % round(v * qb), 22, INK, 800), (120 + bw, yy))
            dv = r['model'] - r['line']
            dd = T('%+d' % dv, 40, GREEN if dv > 0 else RED, 900, font='mont')
            box.alpha_composite(dd, (CW_ - 40 - dd.width - 22, 70))
            C.put(lay, box, CW_ / 2 + 60 * (1 - q), y + rh / 2, q)
        return lay

    def sc_acc(self, lay, t, t0):
        A = self.D['acc']
        q = C.out_expo(C.seg(t, t0 + 0.2, t0 + 1.6))
        C.put(lay, T('УГАДАН ИСХОД МАТЧА', 30, DIM, 800, track=0.1), CW_ / 2, 70)
        big = C.text('%d%%' % round(A['pct'] * q), 'unb', 190, GREEN, 900)
        C.put(lay, big, CW_ / 2, 210)
        C.put(lay, T('%d из %d матчей сезона' % (round(A['hits'] * q), A['n']), 34, INK, 700), CW_ / 2, 345)
        # точки: каждый матч — зелёная или красная
        roll = A.get('dots') or ([1] * A['hits'] + [0] * (A['n'] - A['hits']))
        n = len(roll)
        cols = 24
        r_ = 13
        x0 = (CW_ - cols * 34) / 2 + 17
        shown = int(n * C.seg(t, t0 + 0.3, t0 + 2.4 * self.u))
        d = ImageDraw.Draw(lay)
        for i in range(min(shown, cols * 9)):
            x, y = x0 + (i % cols) * 34, 410 + (i // cols) * 34
            d.ellipse((x - r_, y - r_, x + r_, y + r_), fill=(GREEN if roll[i] else RED) + (255,))
        qs = C.out_back(C.seg(t, t0 + 2.6 * self.u, t0 + 2.6 * self.u + 0.35), 1.5)
        if qs > 0.01 and A['sure_n']:
            s = self._bubble('уверенность от 60%% — угадано %d%% (%d из %d)' % (A['sure_pct'], A['sure_hits'], A['sure_n']))
            C.put(lay, C.scale(s, qs), CW_ / 2, CH_ - 60)
        return lay

    def _sel(self, lay, t, t0, cells, xs, rh=RH):
        """Синяя рамка выделения бегает по ячейкам (как курсор в таблице)."""
        k = int((t - t0) / (self.u / 2))
        if k < 2 or not cells:
            return lay
        c, r = cells[min(len(cells) - 1, k - 2)]
        d = ImageDraw.Draw(lay)
        d.rectangle((xs[c], r * rh, xs[c + 1], r * rh + rh), outline=SEL, width=4)
        d.rectangle((xs[c + 1] - 7, r * rh + rh - 7, xs[c + 1] + 3, r * rh + rh + 3), fill=SEL)
        return lay

    # ── кадр ──
    def frame(self, t):
        fr = self.bg.copy()
        u, D = self.u, self.drop
        if t < D:
            return self.hook_frame(fr, t)
        sc = next((i for i in range(len(self.beats)) if t < self.t_sc[i + 1]), None)
        pulse = math.exp(-((t - D) % u) / u * 5)
        if sc is not None:
            t0 = self.t_sc[sc]
            fr = C.add_light(fr, self.glow, W / 2, WY + WH / 2, 0.55 + 0.15 * pulse).convert('RGBA')
            # заголовок сцены
            qh = C.out_expo(C.seg(t, t0, t0 + 0.3))
            C.put(fr, self.nums[sc], W / 2, 262, qh)
            C.put(fr, C.scale(self.titles[sc], 1.25 - 0.25 * qh), W / 2, 330, min(1.0, qh * 1.6))
            C.put(fr, self.subs[sc], W / 2, 405, qh)
            # окно
            win = self.frames[sc].copy()
            body = Image.new('RGBA', (CW_, CH_), (0, 0, 0, 0))
            body = [self.sc_pred, self.sc_what, self.sc_table, self.sc_elo, self.sc_cmp, self.sc_acc][sc](body, t, t0)
            win.alpha_composite(body, (NUM_W, BAR_H + COL_H))
            # курсор кликает по вкладке в начале сцены
            if t - t0 < 0.5 * u and sc > 0:
                k = C.in_out(C.seg(t, t0 - 0.05, t0 + 0.3 * u))
                cx = C.lerp(self.tab_x[sc - 1], self.tab_x[sc], k)
                win.alpha_composite(self.cursor, (int(cx), int(WH - TAB_H / 2 - 6)))
            zin = C.out_expo(C.seg(t, D, D + 0.45)) if sc == 0 else 1.0
            sw = C.seg(t, t0, t0 + 0.18)                              # смена листа — толчок
            s = (0.62 + 0.38 * zin) * (1.0 + 0.018 * pulse) * (1.0 + 0.05 * (1 - sw) * (sc > 0))
            rot = -6 * (1 - zin)
            w2 = C.scale(win, s)
            if rot:
                w2 = C.rotate(w2, rot)
            C.put(fr, C.shadow(w2, 30, 0.6), W / 2 + 12, WY + WH / 2 + 26)
            C.put(fr, w2, W / 2, WY + WH / 2)
            if t - D < 0.25:
                fr = C.add_light(fr, C.radial(1600, 1600, (255, 255, 255), 255, 1.4), W / 2, H / 2,
                                 1.2 * (1 - (t - D) / 0.25)).convert('RGBA')
        else:
            fr = self.cta_frame(fr, t)
        return fr

    def hook_frame(self, fr, t):
        u = self.u
        # окно таблицы на фоне — размыто и мелко, чтобы сразу было «про таблицу»
        k = C.seg(t, 0, self.drop)
        if not hasattr(self, 'hook_win'):
            win = self.frames[0].copy()
            body = Image.new('RGBA', (CW_, CH_), (0, 0, 0, 0))
            win.alpha_composite(self.sc_pred(body, 99.0, 0.0), (NUM_W, BAR_H + COL_H))
            from PIL import ImageFilter
            self.hook_win = C.rotate(C.scale(win, 0.78).filter(ImageFilter.GaussianBlur(2)), -7)
        w2 = C.scale(self.hook_win, 0.94 + 0.06 * k)
        C.put(fr, w2, W / 2, 1180 + 30 * (1 - k), 0.5)
        fr.alpha_composite(self.hook_shade)
        fr = C.add_light(fr, self.glow, W / 2, 900, 0.5).convert('RGBA')
        ys = [520, 640, 790, 910, 1080, 1210]
        for i, (im, (w, g)) in enumerate(zip(self.hook, HOOK)):
            ti = g * (self.drop / 3) + (i % 2) * 0.12
            q = C.out_back(C.seg(t, ti, ti + 0.28), 1.5)
            if q <= 0.01:
                continue
            C.put(fr, C.scale(im, max(0.05, 1.6 - 0.6 * min(1.0, q))), W / 2, ys[i], min(1.0, q * 1.5))
        return fr

    def cta_frame(self, fr, t):
        t0 = self.t_cta
        q = C.out_expo(C.seg(t, t0, t0 + 0.4))
        fr = C.add_light(fr, self.glow, W / 2, 900, 0.6).convert('RGBA')
        C.put(fr, C.scale(self.cta1, 1.3 - 0.3 * q), W / 2, 960, q)
        C.put(fr, self.cta2, W / 2, 1060, C.seg(t, t0 + 0.2, t0 + 0.5))
        qt = C.out_back(C.seg(t, t0 + 0.4, t0 + 0.8), 1.4)
        if qt > 0.01:
            C.put(fr, C.scale(self.tg, max(0.05, qt)), W / 2, 1250)
        return fr
