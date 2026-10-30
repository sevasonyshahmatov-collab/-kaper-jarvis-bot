# -*- coding: utf-8 -*-
"""«Отсчёт» — рейтинг 5→1 со скрытым №1 (владелец 30.10: «Топ недели» и антирейтинги сезона, team/reels_weekly/BRIEF.md).

Тёмный фон с золотом и свечением цвета клуба. Крючок ~1,5 с → места 5…2 по 3 доли трека (эмблема, название,
крупная цифра с отсчётом, полоска доли, плашка второй цифры) → №1 скрыт 2 доли (размытый золотой силуэт, цифры — «??»)
→ на дроп трека резкость, вспышка → итог наших прогнозов недели (если есть) → вопрос в комментарии + плашка Telegram.
Счётчик «5 из 5 → 1 из 5» вверху справа всё время отсчёта. Заимствовано из top3.py (выезд текста из-под линии).

spec = dict(hook=['СТРОКА 1', 'строка 2', …], tag='КХЛ · СЕЗОН 2026/27', src='источник: приложение КХЛ, на 30.10',
            items=[dict(team, big='12 ИЗ 16', sub='МАТЧЕЙ МЕНЬШЕ 5,5 ШАЙБ', n=12, share=0.75, chip='СРЕДНИЙ ТОТАЛ 4,4'), …]
                  — от 5-го места к 1-му, league='KHL'|'NHL',
            ours=dict(title=['НАШИ ПРОГНОЗЫ КХЛ', 'ЗА 19–25 ОКТЯБРЯ'], big='9 ИЗ 11', sub='ЗАШЛО') | None,
            question=['КАКАЯ КОМАНДА', 'ДОЛЖНА БЫТЬ', 'ШЕСТОЙ?'])
"""
import math
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels.core import W, H
from reels.top3 import reveal

BG = (11, 11, 15)
GOLD = (236, 192, 92)
GOLD2 = (255, 226, 150)
WHITE = (246, 244, 238)
GRAY = (150, 148, 140)


class Countdown(C.Reel):
    footer_plate_to_end = True                         # своей плашки Telegram в финале нет — core.footer ставит свою

    def __init__(self, spec, u=1.0, drop=16.5, seed=31):
        super().__init__(u, drop, seed)
        self.s = spec
        lg = spec.get('league', 'KHL')
        if lg == 'NHL':
            C.nhl.register()
        self.items = [dict(it, T=C.Team(it['team'])) for it in spec['items']]
        assert len(self.items) == 5
        self.per = 3 * u                               # места 5…2
        self.t_places = drop - 2 * u - 4 * self.per    # конец крючка
        assert self.t_places >= 1.3, 'дроп слишком рано: крючку нужно ≥ 1,3 с'
        self.t_tease = drop - 2 * u
        self.t_ours = drop + 2.6 * u
        self.t_q = self.t_ours + (2.4 * u if spec.get('ours') else 0)
        self.dur = self.t_q + 3.0
        self.cover_t = drop - 0.9 * u                  # обложка — №1 ещё скрыт
        self._c = {}
        self._prep()

    # ─────────────── заготовки
    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        y = np.linspace(0, 1, H)[:, None, None]
        arr = np.array(BG, np.float32) * (1.0 + 0.5 * (1 - y)) + rnd.normal(0, 2.0, (H, W))[..., None]
        self.bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        self.blob = C.radial(1400, 1400, (255, 255, 255), 255, 1.6)

    def cache(self, key, fn):
        if key not in self._c:
            self._c[key] = fn()
        return self._c[key]

    def tint_blob(self, col, a):
        def mk():
            b = Image.new('RGBA', self.blob.size, tuple(col) + (0,))
            b.putalpha(self.blob.getchannel('A').point(lambda v: int(v * a)))
            return b
        return self.cache(('blob', tuple(col), a), mk)

    def emb(self, i, size=540, hidden=False):
        def mk():
            e = self.items[i]['T'].emb(size)
            if not hidden:
                return C.with_shadow(e, 26, 0.55, 18)
            # только силуэт без цветов клуба (по цвету №1 угадывается сразу), размыт, золотом
            m = Image.new('L', (e.width + 200, e.height + 200), 0)
            m.paste(e.getchannel('A'), (100, 100))
            m = m.filter(ImageFilter.GaussianBlur(52)).point(lambda v: min(255, int(v * 1.3)))
            b = Image.new('RGBA', m.size, GOLD + (0,))
            b.putalpha(m)
            return b
        return self.cache(('emb', i, size, hidden), mk)

    def num(self, n):
        return self.cache(('num', n), lambda: C.text(str(n), 'unb', 760, GOLD, 900, outline=True, stroke=7, a=95))

    def counter(self, place):
        def mk():
            tx = C.text('%d ИЗ 5' % place, 'unb', 40, BG, 900)
            pl = C.rrect(tx.width + 64, 84, 42, GOLD)
            C.put(pl, tx, pl.width / 2, 42)
            return pl
        return self.cache(('cnt', place), mk)

    def bar(self, share, k):
        w, h = 900, 26
        im = C.rrect(w, h, 13, (255, 255, 255), a=34)
        fw = int(w * share * k)
        if fw > h:
            im.alpha_composite(C.rrect(fw, h, 13, GOLD), (0, 0))
        return im

    def chip(self, s):
        def mk():
            tx = C.text(s, 'mont', 44, WHITE, 800, track=0.04, max_w=860)
            pl = C.rrect(tx.width + 80, 96, 48, (255, 255, 255), a=20, outline=GOLD, width=3)
            C.put(pl, tx, pl.width / 2, 48)
            return pl
        return self.cache(('chip', s), mk)

    # ─────────────── общие слои
    def top_row(self, fr, t, place, a=1.0):
        C.put(fr, C.text(self.s.get('tag', ''), 'mono', 34, GOLD, 700, track=0.12, max_w=640), 90, 300, a, anchor='tl')
        cnt = self.counter(place)
        C.put(fr, cnt, W - 90 - cnt.width / 2, 322, a)

    def place_scene(self, fr, t, i, t0, hidden=False, burst=0.0):
        it = self.items[i]
        T = it['T']
        place = 5 - i
        lt = t - t0
        k = C.out_expo(C.seg(t, t0, t0 + 0.45))
        fr.alpha_composite(self.tint_blob(T.c1, 0.16 if hidden else 0.36), (int(-160 + 30 * math.sin(t * 0.5)), 60))
        fr.alpha_composite(self.tint_blob(GOLD, 0.10), (200, 900))
        self.top_row(fr, t, place, C.seg(t, t0, t0 + 0.25) if i == 0 else 1.0)
        # гигантская цифра места — за эмблемой, медленно уезжает
        C.put(fr, self.num(place), W - 250 - 40 * C.seg(t, t0, t0 + 4 * self.u) + (1 - k) * 200, 720, 0.9 * k)
        # эмблема
        s = 1.0 + 0.25 * burst if burst else (0.86 + 0.14 * C.out_back(C.seg(t, t0 + 0.05, t0 + 0.5)))
        if hidden:
            s *= 1.0 + 0.035 * max(0.0, math.cos(2 * math.pi * (t - t0) / self.u)) ** 8
        e = self.emb(i, hidden=hidden)
        C.put(fr, C.scale(e, s) if abs(s - 1) > 0.004 else e, W / 2 - 40, 720, k)
        # название
        name = 'НОМЕР ОДИН' if hidden else T.name.upper()
        im, _ = reveal(C.text(name, 'unb', 92, GOLD if hidden else WHITE, 900, max_w=940), C.seg(t, t0 + 0.15, t0 + 0.6))
        C.put(fr, im, W / 2, 1090)
        # крупная цифра: число в начале строки досчитывается
        q = C.seg(t, t0 + 0.35, t0 + 1.1)
        if hidden:
            big = re.sub(r'\d+(,\d+)?', '??', it['big'])
        else:
            n = it.get('n')
            big = it['big'] if n is None or q >= 1 else it['big'].replace(str(n), str(int(round(n * C.out_cubic(q)))), 1)
        im, _ = reveal(C.text(big, 'unb', 150, GOLD2, 900, max_w=960), C.seg(t, t0 + 0.3, t0 + 0.7))
        C.put(fr, im, W / 2, 1265)
        im, _ = reveal(C.text(it['sub'], 'mont', 46, WHITE, 800, track=0.06, max_w=960), C.seg(t, t0 + 0.4, t0 + 0.8))
        C.put(fr, im, W / 2, 1385)
        if it.get('share') is not None:
            C.put(fr, self.bar(0.0 if hidden else it['share'], C.out_expo(C.seg(t, t0 + 0.4, t0 + 1.2))), W / 2, 1460,
                  C.seg(t, t0 + 0.3, t0 + 0.6))
        if it.get('chip') and lt >= 0.6:
            C.put(fr, self.chip(re.sub(r'\d+(,\d+)?', '??', it['chip']) if hidden else it['chip']),
                  W / 2, 1555, C.seg(t, t0 + 0.6, t0 + 0.9))
        if self.s.get('src'):
            C.put(fr, C.text(self.s['src'], 'mono', 28, GRAY, 600, max_w=900), W / 2, 1650, 0.9 * k)

    def hook(self, fr, t):
        fr.alpha_composite(self.tint_blob(GOLD, 0.16), (-300, 300))
        # силуэт №1 уже виден — причина досмотреть
        C.put(fr, C.scale(self.emb(4, hidden=True), 1.0 + 0.04 * t), W / 2, 1290, C.seg(t, 0.15, 0.7))
        C.put(fr, C.text('?', 'unb', 300, BG, 900), W / 2, 1290, 0.85 * C.seg(t, 0.3, 0.8))
        rows = self.s['hook']
        y = 290
        for j, s in enumerate(rows):
            sz = 116 if j < len(rows) - 1 else 74
            col = WHITE if j < len(rows) - 1 else GOLD
            tx = C.text(s, 'unb', sz, col, 900, max_w=940)
            im, _ = reveal(tx, C.seg(t, 0.05 + 0.12 * j, 0.45 + 0.12 * j))
            C.put(fr, im, 70, y, anchor='tl')
            y += tx.height + (26 if j < len(rows) - 2 else 44)
        d = ImageDraw.Draw(fr)
        d.line((76, y + 10, 76 + 920 * C.out_expo(C.seg(t, 0.2, 1.2)), y + 10), fill=GOLD + (255,), width=8)
        C.put(fr, self.counter(5), W / 2, 1650, C.seg(t, 0.5, 0.8))

    def ours(self, fr, t, t0):
        o = self.s['ours']
        fr.alpha_composite(self.tint_blob(GOLD, 0.22), (-200, 400))
        y = 520
        for j, s in enumerate(o['title']):
            im, _ = reveal(C.text(s, 'unb', 78 if j == 0 else 56, WHITE if j == 0 else GOLD, 900, max_w=940),
                           C.seg(t, t0 + 0.08 * j, t0 + 0.4 + 0.08 * j))
            C.put(fr, im, W / 2, y)
            y += 100
        im, _ = reveal(C.text(o['big'], 'unb', 230, GOLD2, 900, max_w=960), C.seg(t, t0 + 0.25, t0 + 0.7))
        C.put(fr, im, W / 2, 960)
        im, _ = reveal(C.text(o['sub'], 'unb', 84, WHITE, 900, max_w=940), C.seg(t, t0 + 0.35, t0 + 0.8))
        C.put(fr, im, W / 2, 1180)
        if o.get('note'):
            C.put(fr, C.text(o['note'], 'mont', 40, GRAY, 700, max_w=940), W / 2, 1300, C.seg(t, t0 + 0.6, t0 + 0.9))
        if o.get('src'):
            C.put(fr, C.text(o['src'], 'mono', 26, GRAY, 600, max_w=900), W / 2, 1620, C.seg(t, t0 + 0.6, t0 + 0.9))

    def question(self, fr, t, t0):
        fr.alpha_composite(self.tint_blob(C.TG_BLUE, 0.16), (-100, 500))
        y = 300
        for j, s in enumerate(self.s['question']):
            tx = C.text(s, 'unb', 112, GOLD2 if j == len(self.s['question']) - 1 else WHITE, 900, max_w=940)
            im, _ = reveal(tx, C.seg(t, t0 + 0.1 * j, t0 + 0.45 + 0.1 * j))
            C.put(fr, im, 70, y, anchor='tl')
            y += tx.height + 24
        C.put(fr, C.text('ПИШИ В КОММЕНТАРИЯХ', 'mont', 48, GOLD, 800, track=0.1), 74, y + 40, C.seg(t, t0 + 0.4, t0 + 0.8),
              anchor='tl')
        # весь рейтинг в одну строку — 5 эмблем, №1 крупнее
        x0, ew = 110, 190
        for r in range(5):
            i = 4 - r
            tr = t0 + 0.3 + 0.08 * r
            a = C.out_expo(C.seg(t, tr, tr + 0.35))
            sz = 230 if r == 0 else 170
            cx = x0 + r * ew + (20 if r else 0)
            C.put(fr, self.items[i]['T'].emb(sz), cx, 1080, a)
            C.put(fr, C.text(str(r + 1), 'unb', 52, GOLD, 900), cx, 1240, a)

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        if t < self.t_places:
            self.hook(fr, t)
        elif t < self.t_tease:
            i = min(3, int((t - self.t_places) / self.per))
            t0 = self.t_places + i * self.per
            self.place_scene(fr, t, i, t0)
            te = t0 + self.per                              # смена места: вспышка-шторка золотом
            if t >= te - 0.18:
                q = C.seg(t, te - 0.18, te)
                fr.alpha_composite(Image.new('RGBA', (W, H), BG + (int(255 * C.in_cubic(q)),)))
        elif t < D:
            self.place_scene(fr, t, 4, self.t_tease, hidden=True)
        elif t < self.t_ours:
            q = C.seg(t, D, D + 0.35)
            self.place_scene(fr, t, 4, D - 0.6, burst=1 - C.out_expo(q))
            if q < 1:
                fr.alpha_composite(Image.new('RGBA', (W, H), GOLD2 + (int(235 * (1 - C.out_cubic(q))),)))
        elif t < self.t_q:
            self.ours(fr, t, self.t_ours)
        else:
            self.question(fr, t, self.t_q)
        z = 1.0 + 0.015 * math.sin(t * 0.4)
        dx, dy = C.shake(t, D, 18, 0.4)
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        if D <= t < D + 0.25:
            fr = C.rgb_split(fr, int(14 * (1 - C.seg(t, D, D + 0.25))))
        return C.grain(fr, t, 3)
