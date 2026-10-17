# -*- coding: utf-8 -*-
"""Ролики «Нуар» — другой стиль Shorts / VK Клипов под трек: тёмный, журнальный, «дорогой».

    import shorts_noir as noir
    noir.pick('Трактор', 'Амур', 'ЧТ 08.10 · 17:00 МСК', 'Тотал меньше 4,5', 2.00, 'out.mp4', league='KHL',
              odds=(1.93, 3.69, 3.51), beat=0.8333, track='трек.wav', track_start=9.40)
    noir.cover(... тот же матч ..., 'cover.jpg')                    # обложка 1080×1920

Язык: почти чёрный фон с киношным зерном и мягкими цветными свечениями клубов, огромные бесцветные эмблемы за сценой;
шрифты — Prata (контрастная антиква, заголовки и цифры), Cormorant Garamond Italic (курсив-акцент), JetBrains Mono
(подписи разрядкой), тонкие линии и номер сцены «01 / 06», как в журнальной вёрстке. Один акцент: шампань у КХЛ,
лёд у НХЛ. Движение без «прыжков»: строки выезжают из-под маски (как в дорогих промо), подписи набираются,
линии прорисовываются, кэф прокручивается барабаном. Эмблемы в цвете вспыхивают только на дропе.
Каждая сцена — такт трека (доля — beat), смены сцен — на сильную долю, четыре разных перехода: «диафрагма»
из центра (на дропе), жалюзи, наклонная шторка акцентом, сдвиг вверх.
Музыка — как у shorts: предпросмотр с треком (track=…) только для проверки, для загрузки — без музыки.
"""
import math
import os
import random
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

import nhl
import nhl_kit
import poster
import shorts as base

W, H, FPS = base.W, base.H, base.FPS
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
FONTS = {'serif': ('Prata-Regular.ttf', None), 'ital': ('CormorantGaramond-Italic[wght].ttf', 500),
         'mono': ('JetBrainsMono[wght].ttf', 500), 'monob': ('JetBrainsMono[wght].ttf', 750), 'sans': ('TenorSans-Regular.ttf', None)}
INK = (242, 238, 230)
DIM = (150, 148, 142)
BG = (10, 10, 13)
ACCENT = {'KHL': (222, 186, 118), 'NHL': (150, 205, 245)}
M = 78                                   # поля
TOP, BOTTOM = 112, 1478                  # линии шапки и подвала (ниже подвала — подпись площадки)
_FC, _TC = {}, {}


def font(kind, size):
    key = (kind, int(size))
    if key not in _FC:
        f, w = FONTS[kind]
        ft = ImageFont.truetype(os.path.join(FD, f), int(size))
        if w:
            try:
                ft.set_variation_by_axes([w])
            except Exception:
                pass
        _FC[key] = ft
    return _FC[key]


def text(s, kind, size, fill=INK, track=0.0, max_w=None):
    """Строка текста (RGBA, с запасом под выносные элементы). track — разрядка в долях кегля. Кешируется."""
    key = (s, kind, int(size), fill, track, max_w)
    if key in _TC:
        return _TC[key]
    while True:
        f = font(kind, size)
        sp = track * size
        widths = [f.getlength(c) for c in s]
        tw = sum(widths) + sp * max(0, len(s) - 1)
        if not max_w or tw <= max_w or size <= 20:
            break
        size = int(size * max_w / tw) - 1
    asc, desc = f.getmetrics()
    pad = int(size * 0.12)
    im = Image.new('RGBA', (int(tw) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for c, w in zip(s, widths):
        d.text((x, pad), c, font=f, fill=fill + (255,))
        x += w + sp
    _TC[key] = im
    return im


def expo(x):
    x = min(1.0, max(0.0, x))
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def expo_in(x):
    x = min(1.0, max(0.0, x))
    return 0.0 if x <= 0 else 2 ** (10 * (x - 1))


def p(t, a, b):
    return 0.0 if t <= a else 1.0 if t >= b else (t - a) / (b - a)


put = base._put


def reveal(layer, im, cx, cy, k):
    """Строка выезжает снизу из-под маски (маска — её же рамка): k = 0 — спрятана, 1 — на месте."""
    if k <= 0:
        return
    h = im.height
    off = int(round((1 - expo(k)) * h))
    if off >= h:
        return
    vis = im.crop((0, 0, im.width, h - off)) if off else im
    put(layer, vis, cx, cy - h / 2 + off + vis.height / 2)


def typed(s, k):
    n = int(round(len(s) * min(1, max(0, k))))
    return s[:n]


def hairline(d, x0, y0, x1, y1, k, fill=INK + (90,), width=2):
    if k > 0:
        d.line((x0, y0, x0 + (x1 - x0) * expo(k), y0 + (y1 - y0) * expo(k)), fill=fill, width=width)


def mono_emblem(team, size, alpha=0.12, warm=True):
    e = poster._raw_emblem(team, size, size)
    g = ImageOps.grayscale(e.convert('RGB'))
    g = ImageOps.autocontrast(g, cutoff=2)
    tint = Image.merge('RGB', (g, g.point(lambda v: int(v * 0.97)), g.point(lambda v: int(v * 0.92)))) if warm else g.convert('RGB')
    out = tint.convert('RGBA')
    out.putalpha(e.getchannel('A').point(lambda v: int(v * alpha)))
    return out


def _desat(c, k=0.45):
    g = sum(c) / 3
    return tuple(int(g + (v - g) * k) for v in c)


class _Noir:
    def __init__(self, home, away, league, when, pred, coef, odds, beat, seed=None):
        self.league = 'NHL' if str(league).upper() == 'NHL' else 'KHL'
        if self.league == 'NHL':
            nhl.register()
        self.acc = ACCENT[self.league]
        h, a = nhl_kit._prep(home, away)
        self.home, self.away = h, a
        self.hn = poster.SHORT.get(h, h)
        self.an = poster.SHORT.get(a, a)
        self.c1, self.c2 = poster.BANNER[h], poster.BANNER[a]
        self.when, self.pred, self.coef, self.odds = when, pred, coef, odds
        self.beat = beat
        self.seed = sum(map(ord, h + a)) % 997 if seed is None else seed
        self.rnd = random.Random(self.seed)
        bar = 4 * beat
        plan = [('intro', 1), ('match', 1)]
        if odds:
            plan.append(('line', 1))
        plan.append(('pick', 1 if (coef or bar >= 3.0) else 2))
        if coef:
            plan.append(('kef', 1))
        plan.append(('cta', 1 if bar >= 3.0 else 2))
        self.scenes, t = [], 0.0
        for name, nb in plan:
            self.scenes.append((name, t, t + nb * bar))
            t += nb * bar
        self.dur = t
        kinds = ['shutter', 'push', 'diag', 'shutter', 'push']
        self.trans = [(self.scenes[i][1], 'iris' if i == 1 else kinds[(i - 2) % len(kinds)]) for i in range(1, len(self.scenes))]
        self._prep_assets()

    # ── неизменное: фон, зерно, большие эмблемы ──
    def _prep_assets(self):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx / W - 0.5) * 1.0) ** 2 + ((yy / H - 0.47) * 0.75) ** 2)
        vig = np.clip(1.08 - 0.9 * r ** 1.6, 0.25, 1.0)
        base_ = np.ones((H, W, 3), np.float32) * np.array(BG, np.float32)
        self.base = Image.fromarray(np.clip(base_ * vig[..., None], 0, 255).astype('uint8'), 'RGB').convert('RGBA')
        self.glows = []
        for col in (_desat(self.c1), _desat(self.c2)):
            g = np.exp(-(((xx - W / 2) / 420) ** 2 + ((yy - H / 2) / 520) ** 2))
            im = Image.new('RGBA', (W, H), col + (0,))
            im.putalpha(Image.fromarray((g * 70).astype('uint8'), 'L'))
            self.glows.append(im)
        rng = np.random.default_rng(self.seed)
        self.grain = []
        for _ in range(6):
            n = rng.normal(0, 1, (H // 2, W // 2))
            a = np.clip(np.abs(n) * 9, 0, 24).astype('uint8')            # мягкое зерно: и вид, и вес файла
            gi = Image.new('RGBA', (W // 2, H // 2), (255, 255, 255, 0))
            gi.putalpha(Image.fromarray(a, 'L'))
            self.grain.append(gi.resize((W, H), Image.NEAREST))
        self.big1 = mono_emblem(self.home, 1500, 0.10)
        self.big2 = mono_emblem(self.away, 1500, 0.10)
        self.col1 = base._emblem(self.home, self.c1, 470, 450)
        self.col2 = base._emblem(self.away, self.c2, 470, 450)

    def background(self, t):
        fr = self.base.copy()
        for i, g in enumerate(self.glows):                             # свечения клубов медленно кружат
            a = t * 0.35 + i * math.pi
            cx = W / 2 + math.cos(a) * 260 + (-200 if i == 0 else 200)
            cy = H / 2 + math.sin(a * 0.8) * 420
            put(fr, g, cx, cy)
        return fr

    def watermark(self, layer, name, u, dur):
        """Огромная бесцветная эмблема за сценой, медленно плывёт."""
        k = u / max(dur, 1e-3)
        if name in ('intro', 'pick'):
            put(layer, self.big1, W * 0.22 - 60 * k, H * 0.42)
        elif name in ('line', 'kef'):
            put(layer, self.big2, W * 0.80 + 60 * k, H * 0.55)
        elif name == 'cta':
            put(layer, self.big1, W * 0.5, H * 0.5 - 40 * k)

    def chrome(self, layer, t, idx):
        """Шапка, подвал, номер сцены — постоянная «вёрстка»."""
        d = ImageDraw.Draw(layer)
        k = p(t, 0, 0.6)
        brand = text('JARVIS', 'monob', 36, INK, 0.35)
        put(layer, brand, M + brand.width / 2, TOP - 34)
        lg = text('%s  ·  ПРОГНОЗ' % ('КХЛ' if self.league == 'KHL' else 'НХЛ'), 'mono', 30, DIM, 0.25)
        put(layer, lg, M + brand.width + 30 + lg.width / 2, TOP - 34)
        num = text('%02d / %02d' % (idx + 1, len(self.scenes)), 'mono', 32, self.acc, 0.2)
        put(layer, num, W - M - num.width / 2, TOP - 34)
        hairline(d, M, TOP, W - M, TOP, k)
        hairline(d, W - M, BOTTOM, M, BOTTOM, k)
        f1 = text('ПРОГНОЗЫ НА ХОККЕЙ', 'mono', 32, DIM, 0.2)
        f2 = text('@JARVIBET', 'monob', 34, INK, 0.2)
        put(layer, f1, M + f1.width / 2, BOTTOM + 36)
        put(layer, f2, W - M - f2.width / 2, BOTTOM + 36)
        for x, y in ((M, TOP + 28), (W - M, TOP + 28), (M, BOTTOM - 28), (W - M, BOTTOM - 28)):   # метки-кресты
            d.line((x - 10, y, x + 10, y), fill=INK + (70,), width=2)
            d.line((x, y - 10, x, y + 10), fill=INK + (70,), width=2)

    # ── сцены: u — время от начала сцены, dur — длина сцены ──
    def scene(self, name, u, dur):
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        self.watermark(layer, name, u, dur)
        getattr(self, 's_' + name)(layer, u, dur)
        return layer

    def s_intro(self, L, u, dur):
        b = self.beat
        d = ImageDraw.Draw(L)
        lab = 'МАТЧ ДНЯ — ' + (self.when or '')
        im = text(typed(lab, p(u, 0, 0.7)) or ' ', 'mono', 42, self.acc, 0.12)
        put(L, im, M + im.width / 2, 300)
        hairline(d, M, 340, W - M, 340, p(u, 0.1, 0.9), INK + (60,))
        big = 250
        reveal(L, text(self.hn, 'serif', big, INK, -0.01, W - 2 * M), W / 2, 590, p(u, b, b + 0.45))
        vs = text('против', 'ital', 140, self.acc)
        reveal(L, vs, W / 2, 800, p(u, 2 * b, 2 * b + 0.45))
        hairline(d, M, 806, W / 2 - vs.width / 2 - 30, 806, p(u, 2 * b, 2 * b + 0.6), self.acc + (160,))
        hairline(d, W - M, 806, W / 2 + vs.width / 2 + 30, 806, p(u, 2 * b, 2 * b + 0.6), self.acc + (160,))
        reveal(L, text(self.an, 'serif', big, INK, -0.01, W - 2 * M), W / 2, 1010, p(u, 3 * b, 3 * b + 0.45))
        if self.coef:
            tag = text('ПРОГНОЗ ЗА %.2f' % float(self.coef), 'monob', 40, BG, 0.15)
            k = expo(p(u, 3.4 * b, 3.4 * b + 0.4))
            if k > 0:
                w = int((tag.width + 60) * k)
                d.rectangle((W / 2 - (tag.width + 60) / 2, 1230 - 40, W / 2 - (tag.width + 60) / 2 + w, 1230 + 40), fill=self.acc + (255,))
                if k > 0.6:
                    put(L, tag, W / 2, 1230)

    def s_match(self, L, u, dur):
        b = self.beat
        d = ImageDraw.Draw(L)
        sp = 30 * p(u, 0, dur)                                         # эмблемы медленно расходятся
        k = expo(p(u, 0, 0.35))
        for im, sx in ((self.col1, -1), (self.col2, 1)):
            e = im if k >= 1 else im.resize((int(im.width * (0.92 + 0.08 * k)), int(im.height * (0.92 + 0.08 * k))), Image.BILINEAR)
            put(L, base._alpha(e, k), W / 2 + sx * (250 + sp), 720)
        hairline(d, W / 2, 470, W / 2, 980, p(u, 0.1, 0.8), INK + (110,))
        ring = text('VS', 'monob', 30, INK, 0.2)
        if u > 0.25:
            d.ellipse((W / 2 - 40, 720 - 40, W / 2 + 40, 720 + 40), fill=BG + (255,), outline=INK + (150,), width=2)
            put(L, ring, W / 2 + 2, 720)
        reveal(L, text(self.hn, 'serif', 84, INK, 0, 430), W / 2 - 250 - sp, 1050, p(u, b, b + 0.45))
        reveal(L, text(self.an, 'serif', 84, INK, 0, 430), W / 2 + 250 + sp, 1050, p(u, b, b + 0.45))
        if self.when:
            s = typed(self.when, p(u, 2 * b, 2 * b + 0.6))
            im = text(s or ' ', 'mono', 40, INK, 0.12)
            box_w = text(self.when, 'mono', 40, INK, 0.12).width + 70
            kk = expo(p(u, 2 * b - 0.1, 2 * b + 0.3))
            if kk > 0:
                d.rectangle((W / 2 - box_w / 2, 1230 - 48, W / 2 - box_w / 2 + box_w * kk, 1230 + 48), outline=self.acc + (200,), width=2)
                put(L, im, W / 2 - box_w / 2 + 35 + im.width / 2, 1230)

    def s_line(self, L, u, dur):
        b = self.beat
        d = ImageDraw.Draw(L)
        reveal(L, text('Шансы по линии', 'ital', 150, self.acc), W / 2, 330, p(u, 0, 0.45))
        sub = text('ВЕРОЯТНОСТИ БЕЗ МАРЖИ БУКМЕКЕРА', 'mono', 34, DIM, 0.12)
        put(L, base._alpha(sub, p(u, 0.2, 0.6)), W / 2, 430)
        o = [float(x) for x in self.odds]
        inv = [1 / x for x in o]
        pr = [x / sum(inv) for x in inv]
        fav = max(range(3), key=lambda i: pr[i])
        labels = ['П1', 'Х', 'П2']
        names = [self.hn, 'Ничья', self.an]
        for i in range(3):
            y = 640 + i * 290
            ts = (0.5 + i * 0.75) * b
            k = p(u, ts, ts + 0.45)
            col = self.acc if i == fav else INK
            put(L, base._alpha(text(labels[i], 'monob', 36, self.acc, 0.2), min(1, k * 2)), M + 30, y - 84)
            reveal(L, text(names[i], 'serif', 116, INK, 0, 600), M + text(names[i], 'serif', 116, INK, 0, 600).width / 2 - 12, y, k)
            num = text('%.2f' % o[i], 'serif', 132, col)
            reveal(L, num, W - M - num.width / 2 + 10, y, k)
            hairline(d, M, y + 104, W - M, y + 104, k, INK + (50,), 2)
            kk = expo(p(u, ts + 0.15, ts + 0.9))
            if kk > 0:
                x1 = M + (W - 2 * M) * pr[i] * kk
                d.line((M, y + 104, x1, y + 104), fill=col + (255,), width=10)
                pc = text('%d%%' % round(pr[i] * 100 * kk), 'monob', 42, col, 0.05)
                put(L, pc, min(W - M - pc.width / 2, x1 + 20 + pc.width / 2), y + 150)

    def s_pick(self, L, u, dur):
        b = self.beat
        d = ImageDraw.Draw(L)
        lab = text('НАШ ПРОГНОЗ', 'monob', 44, self.acc, 0.25)
        put(L, base._alpha(lab, p(u, 0, 0.3)), W / 2, 300)
        hairline(d, M, 345, W - M, 345, p(u, 0, 0.8), INK + (60,))
        words = str(self.pred).split()
        size = 230
        while True:                                                    # по строкам: самый крупный кегль, до 4 строк
            f = font('serif', size)
            rows, cur = [], ''
            for w in words:
                nxt = (cur + ' ' + w).strip()
                if cur and f.getlength(nxt) > W - 2 * M:
                    rows.append(cur)
                    cur = w
                else:
                    cur = nxt
            rows.append(cur)
            if (len(rows) <= 4 and all(f.getlength(r) <= W - 2 * M for r in rows)) or size < 90:
                break
            size -= 10
        lh = size * 1.12
        y0 = 830 - lh * len(rows) / 2
        step = min(b, dur * 0.6 / max(1, len(rows)))
        for i, r in enumerate(rows):
            reveal(L, text(r, 'serif', size, INK), W / 2, y0 + lh * i + lh / 2, p(u, 0.15 + i * step, 0.15 + i * step + 0.5))
        it = text('%s — %s' % (self.hn, self.an), 'ital', 84, self.acc)
        reveal(L, it, W / 2, min(1360, y0 + lh * len(rows) + 90), p(u, 0.15 + len(rows) * step, 0.15 + len(rows) * step + 0.5))

    def s_kef(self, L, u, dur):
        b = self.beat
        d = ImageDraw.Draw(L)
        lab = text('КОЭФФИЦИЕНТ', 'monob', 46, self.acc, 0.3)
        put(L, base._alpha(lab, p(u, 0, 0.3)), W / 2, 440)
        hairline(d, M, 490, W - M, 490, p(u, 0, 0.8), INK + (60,))
        s = '%.2f' % float(self.coef)
        size = 400
        f = font('serif', size)
        widths = [f.getlength(c) for c in s]
        x = W / 2 - sum(widths) / 2
        cy = 820
        asc, desc = f.getmetrics()
        hh = asc + desc
        digits = [i for i, c in enumerate(s) if c.isdigit()]
        step = hh * 0.92
        for i, (c, w) in enumerate(zip(s, widths)):
            if c.isdigit():
                j = digits.index(i)
                t_land = (0.6 + j * 0.5) * b
                k = expo(p(u, 0.05, t_land))
                v = int(c)
                pos = v + (9 + j * 4) * (1 - k)                        # барабан крутится и встаёт на свою цифру
                base_d, frac = int(math.floor(pos)), pos - math.floor(pos)
                cell = Image.new('RGBA', (int(w) + 30, int(step)), (0, 0, 0, 0))
                cd = ImageDraw.Draw(cell)
                col = (self.acc if k >= 0.999 else INK) + (255,)
                for dv, dy in ((base_d % 10, frac * step), ((base_d + 1) % 10, (frac - 1) * step)):
                    cd.text((15, dy - (hh - step) / 2), str(dv), font=f, fill=col)
                put(L, cell, x + w / 2, cy)
            else:
                put(L, text(c, 'serif', size, INK), x + w / 2, cy)
            x += w
        t_last = (0.6 + (len(digits) - 1) * 0.5) * b
        hairline(d, W / 2 - 300, cy + 250, W / 2 + 300, cy + 250, p(u, t_last, t_last + 0.6), self.acc + (220,), 4)
        reveal(L, text(str(self.pred), 'ital', 96, INK, 0, W - 2 * M), W / 2, cy + 360, p(u, t_last + 0.1, t_last + 0.6))
        put(L, base._alpha(text('НА МОМЕНТ ПУБЛИКАЦИИ', 'mono', 34, DIM, 0.15), p(u, t_last + 0.3, t_last + 0.8)), W / 2, cy + 470)

    def s_cta(self, L, u, dur):
        b = self.beat
        d = ImageDraw.Draw(L)
        icon = base._tg_icon(150)
        k = expo(p(u, 0, 0.4))
        if k > 0:
            put(L, base._alpha(icon, k), W / 2, 400 - 20 * (1 - k))
        reveal(L, text('Подписывайтесь', 'serif', 140, INK, 0, W - 2 * M), W / 2, 640, p(u, 0.2, 0.65))
        reveal(L, text('на нас в Telegram', 'ital', 140, self.acc, 0, W - 2 * M), W / 2, 810, p(u, b, b + 0.5))
        bw, bh, by = 760, 150, 1010
        kk = expo(p(u, 2 * b - 0.1, 2 * b + 0.35))
        if kk > 0:
            d.rounded_rectangle((W / 2 - bw / 2, by - bh / 2, W / 2 + bw / 2, by + bh / 2), radius=bh // 2, outline=INK + (int(170 * kk),), width=3)
            s = typed(base.HANDLE, p(u, 2 * b, 2 * b + 0.6))
            im = text(s or ' ', 'monob', 70, INK, 0.05)
            caret = '|' if int(u * 3) % 2 == 0 else ' '
            put(L, im, W / 2 - text(base.HANDLE, 'monob', 70, INK, 0.05).width / 2 + im.width / 2, by)
            if len(s) < len(base.HANDLE) or caret == '|':
                cx = W / 2 - text(base.HANDLE, 'monob', 70, INK, 0.05).width / 2 + im.width + 8
                d.rectangle((cx, by - 36, cx + 5, by + 36), fill=self.acc + (255,))
        sm = text('ПРОГНОЗЫ НА КХЛ И НХЛ КАЖДЫЙ ДЕНЬ', 'mono', 36, DIM, 0.08)
        put(L, base._alpha(sm, p(u, 3 * b, 3 * b + 0.4)), W / 2, 1180)
        q = text('А вы как думаете? Пишите в комментариях', 'ital', 72, self.acc, 0, W - 2 * M)
        reveal(L, q, W / 2, 1290, p(u, 3 * b + 0.2, 3 * b + 0.7))

    # ── переходы: окно [T − d_out, T + d_in] ──
    def transition(self, t):
        for T, kind in self.trans:
            if T - 0.32 <= t < T + 0.42:
                return T, kind
        return None

    def frame(self, t):
        fr = self.background(t)
        idx = max(i for i, s in enumerate(self.scenes) if t >= s[1] or i == 0)
        name, a, z = self.scenes[idx]
        cur = self.scene(name, t - a, z - a)
        tr = self.transition(t)
        if tr:
            T, kind = tr
            j = [s[1] for s in self.scenes].index(T)
            prev, nxt = self.scenes[j - 1], self.scenes[j]
            if kind == 'iris' and t >= T:                              # «диафрагма»: новое — в расширяющемся круге
                old = self.scene(prev[0], prev[2] - prev[1], prev[2] - prev[1])
                k = expo(p(t, T, T + 0.42))
                r = 60 + k * 1300
                mask = Image.new('L', (W, H), 0)
                ImageDraw.Draw(mask).ellipse((W / 2 - r, 720 - r, W / 2 + r, 720 + r), fill=255)
                comp = Image.composite(cur, old, mask)
                ImageDraw.Draw(comp).ellipse((W / 2 - r, 720 - r, W / 2 + r, 720 + r), outline=self.acc + (int(220 * (1 - k)),), width=6)
                cur = comp
            elif kind == 'push':                                       # сдвиг вверх: старое уезжает, новое приходит снизу
                if t < T:
                    k = expo_in(p(t, T - 0.32, T))
                    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                    put(lay, cur, W / 2, H / 2 - k * 500)
                    cur = base._alpha(lay, 1 - 0.7 * k)
                else:
                    k = expo(p(t, T, T + 0.42))
                    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                    put(lay, cur, W / 2, H / 2 + (1 - k) * 500)
                    cur = base._alpha(lay, 0.3 + 0.7 * k)
            fr.alpha_composite(cur)
            if kind in ('shutter', 'diag'):                            # заслонка цветом: закрывает к T, открывает после
                k = p(t, T - 0.32, T) if t < T else 1 - p(t, T, T + 0.42)
                ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                od = ImageDraw.Draw(ov)
                if kind == 'shutter':
                    n = 6
                    for i in range(n):
                        kk = expo(min(1, max(0, k * 1.6 - i * 0.1))) if t < T else expo_in(min(1, max(0, k * 1.6 - (n - 1 - i) * 0.1)))
                        x0, x1 = i * W / n, (i + 1) * W / n + 1
                        hh = H * kk
                        if i % 2:
                            od.rectangle((x0, 0, x1, hh), fill=BG + (255,))
                        else:
                            od.rectangle((x0, H - hh, x1, H), fill=BG + (255,))
                    for i in range(1, n):                              # тонкие линии стыков
                        od.line((i * W / n, 0, i * W / n, H), fill=self.acc + (int(120 * k),), width=2)
                else:
                    sh = 700                                           # наклон шторки
                    if t < T:
                        x = -2 * W - sh + 2 * W * expo(p(t, T - 0.32, T))
                    else:
                        x = -sh + (W + sh) * expo(p(t, T, T + 0.42))
                    od.polygon([(x, H), (x + sh, 0), (x + sh + 2 * W, 0), (x + 2 * W, H)], fill=self.acc + (255,))
                    od.line((x + 2 * W + 26, H, x + sh + 2 * W + 26, 0), fill=INK + (220,), width=5)
                fr.alpha_composite(ov)
        else:
            fr.alpha_composite(cur)
        self.chrome(fr, t, idx)
        fr.alpha_composite(self.grain[int(t * 8) % len(self.grain)])      # киношное зерно, 8 смен в секунду
        drop = self.scenes[1][1]                                       # на дропе: вспышка и толчок камеры
        if 0 <= t - drop < 0.25:
            u = t - drop
            fr.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(150 * (1 - u / 0.25) ** 2))))
            z = 1 + 0.05 * (1 - u / 0.25) ** 2
            cw, ch = W / z, H / z
            fr = fr.resize((W, H), Image.BILINEAR, box=(W / 2 - cw / 2, H / 2 - ch / 2, W / 2 + cw / 2, H / 2 + ch / 2))
        return fr.convert('RGB')

    def render(self, path, track=None, track_start=0.0):
        saved = poster.FONTS7
        poster.FONTS7 = dict(saved, **poster.FONTS_SIDE)
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            au = base._Audio(self.dur, self.seed)                       # без своей музыки: тишина, трек — в редакторе
            au.write(wav, self.dur)
            if track:
                base._mix_track(wav, track, track_start, self.dur, 0.0)
            cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                   '-r', str(FPS), '-i', '-', '-i', wav, '-shortest', '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-tune', 'film',
                   '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', path]
            pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            try:
                for i in range(int(round(self.dur * FPS))):
                    pr.stdin.write(self.frame(i / FPS).tobytes())
            finally:
                pr.stdin.close()
                code = pr.wait()
                os.unlink(wav)
            if code != 0:
                raise RuntimeError('ffmpeg не собрал ролик: %s' % path)
            return path
        finally:
            poster.FONTS7 = saved


def pick(home, away, when, pred, coef, path, league='KHL', odds=None, beat=0.8, track=None, track_start=0.0, seed=None):
    """Ролик-прогноз «Нуар» под трек: beat — доля сцены (track_sync.analyze → unit)."""
    return _Noir(home, away, league, when, pred, coef, odds, beat, seed).render(path, track, track_start)


def cover(home, away, when, pred, coef, path, league='KHL', odds=None, seed=None):
    """Обложка 1080×1920 в том же стиле: огромная бесцветная эмблема, «Команда / против / Команда» антиквой,
    прогноз и кэф крупно в рамке акцента, шапка и подвал моно."""
    c = _Noir(home, away, league, when, pred, coef, odds, 0.8, seed)
    saved = poster.FONTS7
    poster.FONTS7 = dict(saved, **poster.FONTS_SIDE)
    try:
        fr = c.background(1.3)
        L = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        put(L, mono_emblem(c.home, 1600, 0.16), W * 0.18, H * 0.36)
        put(L, mono_emblem(c.away, 1600, 0.16), W * 0.86, H * 0.70)
        d = ImageDraw.Draw(L)
        put(L, c.col1, W / 2 - 265, 470)
        put(L, c.col2, W / 2 + 265, 470)
        d.ellipse((W / 2 - 40, 470 - 40, W / 2 + 40, 470 + 40), fill=BG + (255,), outline=INK + (150,), width=2)
        put(L, text('VS', 'monob', 30, INK, 0.2), W / 2 + 2, 470)
        put(L, text(c.hn, 'serif', 150, INK, 0, W - 2 * M), W / 2, 780)
        put(L, text('против', 'ital', 100, c.acc), W / 2, 905)
        put(L, text(c.an, 'serif', 150, INK, 0, W - 2 * M), W / 2, 1025)
        y = 1180
        d.rectangle((M, y, W - M, y + 250), outline=c.acc + (230,), width=3)
        put(L, text('НАШ ПРОГНОЗ', 'monob', 30, c.acc, 0.3), W / 2, y + 40)
        put(L, text(str(pred), 'serif', 92, INK, 0, W - 2 * M - 60), W / 2, y + 120)
        if coef:
            put(L, text('КЭФ  %.2f' % float(coef), 'monob', 54, c.acc, 0.1), W / 2, y + 205)
        if when:
            put(L, text(when, 'mono', 34, DIM, 0.12), W / 2, 1135)
        fr.alpha_composite(L)
        c.chrome(fr, 5.0, 0)
        fr.alpha_composite(c.grain[0])
        fr.convert('RGB').save(path, quality=94)
        return path
    finally:
        poster.FONTS7 = saved
