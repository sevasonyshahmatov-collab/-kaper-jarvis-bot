# -*- coding: utf-8 -*-
"""Трейлер таблицы, 2-й ролик (владелец 20.10: «ещё один ролик, но с другой музыкой и другим содержанием»).

Те же листы, что в sheet_trailer.py (окно Google Таблиц нарисовано кодом, данные — render/sheet_data.build), но другая
история: крючок «182 матча сезона в одной таблице — вот что она видит» (число матчей — настоящее), сначала доказательство
(точность за сезон), потом «Что заходит», сравнение с линией, Elo, таблица лиги и прогнозы — в конце призыв к полной
таблице. Без обещаний выигрыша и без букмекеров.
"""
import math

from PIL import Image, ImageDraw

from reels import core as C
from reels import sheet_trailer as S
from reels.core import W, H

ORDER = [5, 1, 4, 3, 2, 0]             # индексы листов sheet_trailer.TABS: точность, что заходит, сравнение, Elo, таблица, прогнозы
TITLES2 = {5: 'СНАЧАЛА — ЦИФРЫ', 1: 'ЧТО ЗАХОДИТ У КАЖДОЙ КОМАНДЫ', 4: 'ГДЕ ЛИНИЯ ОШИБАЕТСЯ', 3: 'КТО НАБИРАЕТ ФОРМУ',
           2: 'ТАБЛИЦА ЛИГИ', 0: 'И ПРОГНОЗ НА МАТЧ'}
SUBS2 = {5: 'каждый матч сезона — проверен', 1: 'победа, тоталы, форы — в процентах', 4: 'модель против коэффициентов',
         3: 'рейтинг силы elo по дням', 2: 'обновляется сама после матчей', 0: 'шанс, счёт и «зашло» — всё открыто'}


class SheetTrailer2(S.SheetTrailer):
    def __init__(self, data, u=1.0, pre=4, beats=(6, 5, 4, 4, 4, 5), cta=4, seed=23):
        super().__init__(data, u=u, pre=pre, beats=beats, cta=cta, seed=seed)
        n = data['acc']['n']
        self.hook_words = [('%d МАТЧЕЙ' % n, 0), ('СЕЗОНА КХЛ', 0), ('В ОДНОЙ', 1), ('ТАБЛИЦЕ', 1), ('ВОТ ЧТО', 2),
                           ('ОНА ВИДИТ', 2)]
        self.hook = [C.with_shadow(C.text(w, 'unb', 104 if len(w) < 10 else 86, S.GOLD if g == 2 else (255, 255, 255), 900,
                                          max_w=980), 18, 0.7, 8) for w, g in self.hook_words]
        self.titles2 = {i: C.text(s, 'unb', 58 if len(s) < 20 else 46, (255, 255, 255), 900, max_w=980)
                        for i, s in TITLES2.items()}
        self.subs2 = {i: C.text(s.upper(), 'mont', 32, (150, 196, 255), 800, track=0.12, max_w=980) for i, s in SUBS2.items()}
        self.nums2 = [C.text('%02d / %02d' % (k + 1, len(ORDER)), 'mono', 30, S.GOLD, 800, track=0.1)
                      for k in range(len(ORDER))]
        self.cta1 = C.text('ПОЛНАЯ ТАБЛИЦА', 'unb', 84, (255, 255, 255), 900, max_w=980)
        self.cta2 = C.text('ВСЕ ЛИСТЫ И ПРОГНОЗЫ — В TELEGRAM', 'mont', 40, (150, 196, 255), 900, track=0.06, max_w=980)
        self.cover_t = self.drop + 2.6 * u

    def frame(self, t):
        fr = self.bg.copy()
        u, D = self.u, self.drop
        if t < D:
            return self.hook_frame2(fr, t)
        pos = next((i for i in range(len(self.beats)) if t < self.t_sc[i + 1]), None)
        if pos is None:
            return self.cta_frame(fr, t)
        sc = ORDER[pos]
        pulse = math.exp(-((t - D) % u) / u * 5)
        t0 = self.t_sc[pos]
        fr = C.add_light(fr, self.glow, W / 2, S.WY + S.WH / 2, 0.55 + 0.15 * pulse).convert('RGBA')
        qh = C.out_expo(C.seg(t, t0, t0 + 0.3))
        C.put(fr, self.nums2[pos], W / 2, 262, qh)
        C.put(fr, C.scale(self.titles2[sc], 1.25 - 0.25 * qh), W / 2, 330, min(1.0, qh * 1.6))
        C.put(fr, self.subs2[sc], W / 2, 405, qh)
        win = self.frames[sc].copy()
        body = Image.new('RGBA', (S.CW_, S.CH_), (0, 0, 0, 0))
        body = [self.sc_pred, self.sc_what, self.sc_table, self.sc_elo, self.sc_cmp, self.sc_acc][sc](body, t, t0)
        win.alpha_composite(body, (S.NUM_W, S.BAR_H + S.COL_H))
        if t - t0 < 0.5 * u and pos > 0:                          # курсор переходит на вкладку следующего листа
            k = C.in_out(C.seg(t, t0 - 0.05, t0 + 0.3 * u))
            cx = C.lerp(self.tab_x[ORDER[pos - 1]], self.tab_x[sc], k)
            win.alpha_composite(self.cursor, (int(cx), int(S.WH - S.TAB_H / 2 - 6)))
        zin = C.out_expo(C.seg(t, D, D + 0.45)) if pos == 0 else 1.0
        sw = C.seg(t, t0, t0 + 0.18)
        s = (0.62 + 0.38 * zin) * (1.0 + 0.018 * pulse) * (1.0 + 0.05 * (1 - sw) * (pos > 0))
        w2 = C.scale(win, s)
        if zin < 1:
            w2 = C.rotate(w2, 6 * (1 - zin))
        C.put(fr, C.shadow(w2, 30, 0.6), W / 2 + 12, S.WY + S.WH / 2 + 26)
        C.put(fr, w2, W / 2, S.WY + S.WH / 2)
        if t - D < 0.25:
            fr = C.add_light(fr, C.radial(1600, 1600, (255, 255, 255), 255, 1.4), W / 2, H / 2,
                             1.2 * (1 - (t - D) / 0.25)).convert('RGBA')
        return fr

    def hook_frame2(self, fr, t):
        """Крючок: на фоне — лист «Что заходит» (размыт), слова по третям до дропа."""
        k = C.seg(t, 0, self.drop)
        if not hasattr(self, 'hook_win2'):
            from PIL import ImageFilter
            win = self.frames[1].copy()
            body = Image.new('RGBA', (S.CW_, S.CH_), (0, 0, 0, 0))
            win.alpha_composite(self.sc_what(body, 99.0, 0.0), (S.NUM_W, S.BAR_H + S.COL_H))
            self.hook_win2 = C.rotate(C.scale(win, 0.78).filter(ImageFilter.GaussianBlur(2)), 6)
        C.put(fr, C.scale(self.hook_win2, 0.94 + 0.06 * k), W / 2, 1180 + 30 * (1 - k), 0.5)
        fr.alpha_composite(self.hook_shade)
        fr = C.add_light(fr, self.glow, W / 2, 900, 0.5).convert('RGBA')
        ys = [520, 640, 790, 910, 1080, 1210]
        for i, (im, (w, g)) in enumerate(zip(self.hook, self.hook_words)):
            ti = g * (self.drop / 3) + (i % 2) * 0.12
            q = C.out_back(C.seg(t, ti, ti + 0.28), 1.5)
            if q > 0.01:
                C.put(fr, C.scale(im, max(0.05, 1.6 - 0.6 * min(1.0, q))), W / 2, ys[i], min(1.0, q * 1.5))
        return fr


def cover2(data):
    """Обложка 2-го трейлера: «182 МАТЧА В ОДНОЙ ТАБЛИЦЕ», лист «Что заходит» наискосок с выделенной ячейкой и стикер
    с честной долей угаданного."""
    r = SheetTrailer2(data)
    img = r.bg.copy()
    img = C.add_light(img, C.radial(1600, 1500, (30, 140, 255), 170, 1.6), W / 2, 1000, 1.0).convert('RGBA')
    win = r.frames[1].copy()
    body = Image.new('RGBA', (S.CW_, S.CH_), (0, 0, 0, 0))
    win.alpha_composite(r.sc_what(body, 99.0, 0.0), (S.NUM_W, S.BAR_H + S.COL_H))
    w2 = C.rotate(C.scale(win, 0.86), 5)
    C.put(img, C.shadow(w2, 40, 0.75), W / 2 + 16, 1130)
    C.put(img, w2, W / 2, 1100)
    n = data['acc']['n']
    t1 = C.with_shadow(C.text('%d МАТЧЕЙ КХЛ' % n, 'unb', 92, (255, 255, 255), 900, max_w=1000), 14, 0.8, 6)
    t2 = C.glow(C.text('В ОДНОЙ ТАБЛИЦЕ', 'unb', 96, S.GOLD, 900, max_w=1020, stroke=6, stroke_fill=(40, 20, 0)), 26, 0.9,
                (255, 150, 30))
    C.put(img, t1, W / 2, 330)
    C.put(img, t2, W / 2, 450)
    A = data['acc']
    sure = A['sure_n'] >= 20 and A['sure_pct'] > A['pct']
    pct = A['sure_pct'] if sure else A['pct']
    st = C.rrect(470, 250, 40, (30, 170, 80), outline=(255, 255, 255), width=8)
    C.put(st, C.text('%d%%' % pct, 'unb', 120, (255, 255, 255), 900), 235, 105)
    C.put(st, C.text('УГАДАНО', 'unb', 46, (225, 255, 230), 900, track=0.08), 235, 200)
    C.put(img, C.with_shadow(C.rotate(st, -8), 20, 0.6, 10), 300, 1500)
    C.put(img, C.text('КХЛ · ТАБЛИЦА ПРОГНОЗОВ', 'mont', 40, (170, 205, 255), 900, track=0.14), W / 2, 1720)
    return img.convert('RGB')
