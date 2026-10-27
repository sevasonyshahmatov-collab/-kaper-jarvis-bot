# -*- coding: utf-8 -*-
"""Заставка перед роликом (владелец 24.10): на 1 с «ПРОГНОЗ НА МАТЧ» + обе команды, дальше — ролик шаблона как есть.
«В тему к ролику»: фон заставки — размытый кадр самого ролика (цвета и стиль шаблона), акцент — главный цвет этого кадра,
эмблемы клубов. Музыка начинается на 1 с раньше, дроп остаётся на прогнозе (make.one: start -= DUR).

    r = intro.wrap(r, 'Сибирь', 'Трактор', 'KHL')      # REELS_INTRO=0 — без заставки

Сравнение заставок (владелец 27.10): lines — свои строки вместо «ПРОГНОЗ НА МАТЧ / команды»: первая — цветом акцента,
крупно (длинная — в две строки), остальные — белым, мельче (make.ab_lines: А — прогноз и кэф, Б — вопрос без ответа).
"""
import os

import numpy as np
from PIL import Image, ImageFilter

from reels import core as C

DUR = float(os.environ.get('REELS_INTRO', '1.0'))
BG_T = 1.5                     # с какой секунды ролика берём кадр для фона (сцены уже на экране)
XF = 0.15                      # последние 0,15 с заставки — переход в первый кадр ролика


def accent(fr):
    """Главный яркий цвет кадра: медиана насыщенных светлых пикселей; нет таких — None."""
    a = np.asarray(fr.convert('RGB').resize((108, 192)), dtype=np.float32)
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1)
    m = (sat > 0.45) & (mx > 140)
    if m.sum() < 60:
        return None
    return tuple(int(v) for v in np.median(a[m], axis=0))


class Intro:
    """Ролик шаблона с заставкой в начале. Остальные атрибуты (ticker, voice_only…) — от ролика шаблона."""

    def __init__(self, base, home, away, league='KHL', dur=DUR, lines=None):
        d = self.__dict__
        d['base'], d['intro'], d['_lay'], d['lines'] = base, float(dur), None, lines
        d['teams'] = C.match(home, away, league)

    def __getattr__(self, k):
        return getattr(self.base, k)

    def __setattr__(self, k, v):
        setattr(self.base, k, v)

    @property
    def dur(self):
        return self.base.dur + self.intro

    @property
    def drop(self):
        return self.base.drop + self.intro

    @property
    def cover_t(self):
        c = getattr(self.base, 'cover_t', None)
        return None if c is None else c + self.intro

    def _base_frame(self, t):
        fr = self.base.frame(t)
        if fr.size != (C.W, C.H):
            fr = fr.resize((C.W, C.H), Image.LANCZOS)
        return fr.convert('RGB')

    def _layers(self):
        """Фон и надписи — один раз (кадр зависит только от t; в каждом процессе пула — свой кеш)."""
        if self._lay is None:
            src = self._base_frame(min(BG_T, self.base.dur / 3))
            h, a = self.teams
            col = accent(src) or h.c1
            bg = src.resize((C.W // 6, C.H // 6), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
            bg = Image.eval(bg.resize((C.W, C.H), Image.BILINEAR), lambda v: int(v * 0.38)).convert('RGBA')
            glow = C.radial(C.W, C.H, col, a0=90, power=2.4)
            bg.alpha_composite(glow)
            if self.lines:                                    # сравнение заставок: акцент — первая строка, крупно
                main, rest = self.lines[0], list(self.lines[1:])
                parts = [main]
                if C.text(main, 'mont', 84, wght=900).width > C.W - 150 and ' ' in main:   # длинная — в две строки
                    w = main.split(' ')
                    k = min(range(1, len(w)), key=lambda i: abs(len(' '.join(w[:i])) - len(' '.join(w[i:]))))
                    parts = [' '.join(w[:k]), ' '.join(w[k:])]
                size = 84
                while size > 40 and max(C.text(x, 'mont', size, wght=900).width for x in parts) > C.W - 150:
                    size -= 2
                heads = [C.text(x, 'mont', size, col, 900) for x in parts]
                head = Image.new('RGBA', (max(x.width for x in heads), sum(x.height for x in heads) + 12 * (len(heads) - 1)))
                y = 0
                for x in heads:
                    head.alpha_composite(x, ((head.width - x.width) // 2, y))
                    y += x.height + 12
                small = 60
                while small > 30 and max(C.text(x, 'mont', small, wght=800).width for x in rest) > C.W - 150:
                    small -= 2
                subs = [C.text(x, 'mont', small, (255, 255, 255), 800) for x in rest]
                vs = Image.new('RGBA', (max(x.width for x in subs), sum(x.height for x in subs) + 22 * (len(subs) - 1)))
                y = 0
                for x in subs:
                    vs.alpha_composite(x, ((vs.width - x.width) // 2, y))
                    y += x.height + 22
            else:
                # однотипные надписи — один кегль (team/RULES.md): заголовок и команды подгоняются под самую длинную строку
                lines = ['ПРОГНОЗ НА МАТЧ', '%s — %s' % (h.up, a.up)]
                size = 92
                while size > 40 and max(C.text(s, 'mont', size, wght=900).width for s in lines) > C.W - 150:
                    size -= 2
                head = C.text(lines[0], 'mont', size, col, 900, track=0.03)
                vs = C.text(lines[1], 'mont', size, (255, 255, 255), 900)
            bar = C.rrect(min(C.W - 300, head.width), 10, 5, fill=col)
            e = 300
            halo = C.radial(int(e * 1.7), int(e * 1.7), (255, 255, 255), a0=70, power=1.8)   # тёмные эмблемы не тонут в фоне
            embs = []
            for t in (h, a):
                im = halo.copy()
                C.put(im, t.emb(e), im.width / 2, im.height / 2)
                embs.append(im)
            self.__dict__['_lay'] = dict(bg=bg, head=head, vs=vs, bar=bar, embs=embs, e=e, first=self._base_frame(0))
        return self._lay

    def frame(self, t):
        if t >= self.intro:
            return self.base.frame(t - self.intro)
        L = self._layers()
        fr = L['bg'].copy()
        k = C.out_back(C.seg(t, 0.0, 0.28))                   # въезд за 0,28 с
        ka = C.clamp(t / 0.12)
        cy = (C.SAFE_TOP + C.SAFE_BOT) / 2
        gap = 70
        for i, im in enumerate(L['embs']):
            x = C.W / 2 + (-1 if i == 0 else 1) * (L['e'] / 2 + gap / 2 + (1 - k) * 260)       # центр эмблемы
            C.put(fr, im, x, cy - 250, a=ka)
        C.put(fr, L['head'], C.W / 2, cy + 20 + (1 - k) * 60, a=ka)
        C.put(fr, C.scale(L['bar'], max(0.02, k)), C.W / 2, cy + 20 + L['head'].height / 2 + 34, a=ka)
        C.put(fr, L['vs'], C.W / 2, cy + 20 + L['head'].height + 110 + (1 - k) * 90, a=ka)
        x = C.seg(t, self.intro - XF, self.intro)
        if x > 0:
            fr = Image.blend(fr.convert('RGB'), L['first'], x)
        return fr


def wrap(r, home, away, league='KHL', lines=None, dur=None):
    if DUR <= 0:
        return r
    return Intro(r, home, away, league, dur=dur or DUR, lines=lines)
