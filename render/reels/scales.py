# -*- coding: utf-8 -*-
"""«Весы» — кто перевешивает: золотые весы, на чашки падают гири-показатели.

Сцены (u — доля трека, D — дроп):
  интро (0 … 4u)   — матч, время МСК, линия П1 · Х · П2; над концами коромысла — медальоны клубов;
  показатели       — на каждую долю сверху карточка показателя (подпись, цифры обоих клубов, лучший — золотом),
                     гиря с коротким названием падает в чашку лучшего и встаёт точно на следующую долю,
                     коромысло наклоняется по разнице гирь (с перелётом и затуханием);
  перед дропом     — карточка «ПЕРЕВЕС N : M», весы покачиваются;
  ДРОП             — коромысло уходит до упора, чашка лидера вспыхивает, карточка прогноза.
stats — [(подпись, значение хозяев, значение гостей, кому гиря 'home'/'away', надпись на гире)].
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from reels import core as C
from reels import parts as P
from reels.core import W, H

GOLD = (236, 190, 92)
GOLD_HI = (255, 236, 170)
GOLD_LO = (150, 104, 30)
INK = (34, 24, 6)
PIV = (W / 2, 640)        # ось коромысла
ARM = 370                 # полудлина коромысла
HANG = 300                # длина подвеса чашки
MAXA = 15.0               # предельный наклон, градусы


def metal(w, h, r, vertical=True):
    def make():
        y = np.linspace(0, 1, h if vertical else w, dtype=np.float32)
        st = [(0, GOLD_HI), (.35, GOLD), (.55, (200, 150, 60)), (.8, GOLD), (1, GOLD_LO)]
        cols = np.stack([np.interp(y, [s[0] for s in st], [s[1][i] for s in st]) for i in range(3)], -1)
        arr = np.broadcast_to(cols[:, None, :] if vertical else cols[None, :, :], (h, w, 3)).astype(np.uint8)
        im = Image.fromarray(np.ascontiguousarray(arr), 'RGB').convert('RGBA')
        im.putalpha(C.rrect(w, h, r, (255, 255, 255)).getchannel('A'))
        return im
    return P.cached(('metal', w, h, r, vertical), make)


def weight(lbl):
    def make():
        w, h = 168, 84
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        body = metal(w, h - 14, 10)
        m = C.polygon([(18, 0), (w - 18, 0), (w, h - 14), (0, h - 14)], (w, h - 14))
        b = body.copy()
        b.putalpha(m.getchannel('A'))
        im.alpha_composite(b, (0, 14))
        im.alpha_composite(C.ellipse(44, 22, GOLD_LO), (w // 2 - 22, 0))
        im.alpha_composite(C.ellipse(30, 14, (40, 30, 10)), (w // 2 - 15, 4))
        C.put(im, C.text(lbl, 'mont', 22, INK, 900, max_w=w - 40), w / 2, 14 + (h - 14) / 2)
        return im
    return P.cached(('weight', lbl), make)


def pan():
    def make():
        w, h = 330, 96
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        bowl = metal(w, h, 0)
        m = Image.new('L', (w * 3, h * 3), 0)
        ImageDraw.Draw(m).pieslice((0, -h * 3, w * 3 - 1, h * 3 - 1), 0, 180, fill=255)
        b = bowl.copy()
        b.putalpha(m.resize((w, h), Image.LANCZOS))
        im.alpha_composite(b)
        im.alpha_composite(C.ellipse(w, 26, GOLD_HI), (0, 0))
        im.alpha_composite(C.ellipse(w - 16, 18, (170, 120, 40)), (8, 4))
        return im
    return P.cached(('pan',), make)


class Scales(C.Reel):
    def __init__(self, home, away, league, when, line, stats, pick_team, pick1, pick2, odds, u=60 / 73, drop=None, seed=8):
        n = len(stats)
        drop = drop if drop is not None else (4 + n + 2) * u
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.line, self.stats = league, when, line, stats
        self.pick_t = {'home': self.h, 'away': self.a}.get(pick_team)
        self.pick1, self.pick2, self.odds = pick1, pick2, odds
        self.T1 = 4 * u
        self.dur = drop + 6.5 * u
        self.cover_t = drop + 3 * u
        self.land = [self.T1 + (i + 1) * u for i in range(n)]        # гиря встаёт на долю
        self.score = (sum(s[3] == 'home' for s in stats), sum(s[3] == 'away' for s in stats))

    def _angle(self, t):
        """Наклон коромысла (градусы, + — вниз левая чашка): сумма затухающих толчков от каждой гири."""
        a = 0.0
        for (lab, vh, va, side, short), tl in zip(self.stats, self.land):
            if t >= tl:
                s = 1 if side == 'home' else -1
                x = t - tl
                a += s * 3.4 * (1 - math.exp(-x * 7) * math.cos(x * 16))
        if t >= self.drop:                                            # дроп: до упора к лидеру
            lead = 1 if self.score[0] >= self.score[1] else -1
            x = t - self.drop
            a = a + (lead * MAXA - a) * (1 - math.exp(-x * 9) * math.cos(x * 14))
        elif t > self.drop - 2 * self.u:
            a += 0.8 * math.sin((t - (self.drop - 2 * self.u)) * 9)
        return max(-MAXA - 3, min(MAXA + 3, a))

    def _card(self, i):
        lab, vh, va, side, short = self.stats[i]
        def make():
            pl = C.rrect(940, 170, 26, (16, 14, 20), 236, outline=GOLD, width=3)
            C.put(pl, C.text(lab, 'mont', 28, (210, 200, 180), 800, track=0.2, max_w=600), 470, 40)
            ch = GOLD if side == 'home' else (190, 190, 196)
            ca = GOLD if side == 'away' else (190, 190, 196)
            C.put(pl, C.text(vh, 'osw', 70, ch, 700, max_w=330), 240, 110)
            C.put(pl, C.text(va, 'osw', 70, ca, 700, max_w=330), 700, 110)
            tri = [(40, 0), (40, 44), (0, 22)] if side == 'home' else [(0, 0), (0, 44), (40, 22)]
            C.put(pl, C.polygon(tri, (40, 44), GOLD), 470, 110)
            return pl
        return P.cached(('sc_card', i), make)

    def _ends(self, t):
        a = math.radians(self._angle(t))
        dx, dy = ARM * math.cos(a), ARM * math.sin(a)
        return a, (PIV[0] - dx, PIV[1] + dy), (PIV[0] + dx, PIV[1] - dy)

    def frame(self, t):
        u, D = self.u, self.drop
        fr = P.vbg((20, 18, 30), (6, 6, 10), glow=(90, 70, 30), glow_xy=(W / 2, 640), glow_r=560, glow_k=0.35).convert('RGBA')
        P.header(fr, self.league, self.when, acc=GOLD)
        ang, L, R = self._ends(t)
        # стойка и основание
        fr.alpha_composite(metal(36, 640, 14), (int(PIV[0] - 18), int(PIV[1])))
        fr.alpha_composite(metal(360, 40, 18), (int(PIV[0] - 180), int(PIV[1] + 620)))
        fr.alpha_composite(metal(220, 30, 14), (int(PIV[0] - 110), int(PIV[1] + 596)))
        # подвесы, чашки, гири
        d = ImageDraw.Draw(fr)
        lead = 'home' if self.score[0] >= self.score[1] else 'away'
        for side, (ex, ey) in (('home', L), ('away', R)):
            py = ey + HANG
            for ox in (-150, 150):
                d.line((ex, ey, ex + ox, py), fill=GOLD_LO + (255,), width=4)
            if t >= D and side == lead:
                k = max(0.0, 1 - (t - D) / (2 * u))
                C.put(fr, C.radial(560, 300, GOLD_HI, int(200 * (0.35 + 0.65 * k))), ex, py - 40)
            C.put(fr, pan(), ex, py + 30)
            stack = [i for i, s in enumerate(self.stats) if s[3] == side]
            for j, i in enumerate(stack):
                tl = self.land[i]
                if t < tl - 0.45 * u:
                    continue
                yy = py - 20 - j * 74
                if t < tl:                                                    # летит сверху
                    k = C.in_cubic(C.clamp((t - (tl - 0.45 * u)) / (0.45 * u)))
                    yy = C.lerp(470, yy, k)
                C.put(fr, weight(self.stats[i][4]), ex, yy)
        # коромысло
        beam = P.cached(('beam',), lambda: metal(2 * ARM + 60, 34, 17))
        C.put(fr, C.rotate(beam, math.degrees(ang)), PIV[0], PIV[1])
        C.put(fr, P.cached(('pivc',), lambda: C.ellipse(70, 70, GOLD_HI)), PIV[0], PIV[1])
        C.put(fr, P.cached(('pivc2',), lambda: C.ellipse(40, 40, GOLD_LO)), PIV[0], PIV[1])
        # медальоны клубов над концами
        for tm, (ex, ey) in ((self.h, L), (self.a, R)):
            md = P.cached(('sc_md', tm.name), lambda tm=tm: C.with_shadow(tm.emb(170), 12, 0.6, 8))
            C.put(fr, md, ex, ey - 96)
        # карточки сверху
        n = len(self.stats)
        if t < self.T1:
            ttl = P.cached(('sc_ttl',), lambda: C.text('%s — %s' % (self.h.up, self.a.up), 'osw', 64, (245, 240, 228), 700,
                                                     max_w=W - 100))
            C.put(fr, ttl, W / 2, 400, a=C.clamp(t / 0.4))
            od = P.cached(('sc_odds',), lambda: C.odds_row(self.line, w=820, h=150, fill=(30, 26, 18), fill_a=230, val_col=GOLD_HI,
                                                          lab_col=(200, 190, 160), outline=GOLD))
            C.put(fr, od, W / 2, 1390, a=C.clamp((t - 0.6) / 0.4))
        elif t < self.T1 + n * u:
            i = int((t - self.T1) / u)
            k = P.pop(t, self.T1 + i * u, 0.25)
            C.put(fr, C.scale(self._card(i), 0.9 + 0.1 * k), W / 2, 430, a=min(1, k * 1.5))
        elif t < D:
            sc = P.cached(('sc_sum',), lambda: C.text('ПЕРЕВЕС  %d : %d' % self.score, 'osw', 86, GOLD_HI, 700))
            C.put(fr, sc, W / 2, 430, a=C.clamp((t - self.T1 - n * u) / 0.3))
        else:
            card = P.pick_card(self.pick_t, self.pick1, self.pick2, self.odds, acc=GOLD, dark=(18, 14, 8), h=280)
            k = P.pop(t, D + 0.04, 0.4)
            C.put(fr, C.scale(card, 0.75 + 0.25 * k), W / 2, 1330, a=min(1, k * 1.5))
            sc = P.cached(('sc_sum',), lambda: C.text('ПЕРЕВЕС  %d : %d' % self.score, 'osw', 86, GOLD_HI, 700))
            C.put(fr, sc, W / 2, 430)
            fr = P.flash(fr, max(0.0, 1 - (t - D) / 0.22) * 0.6, (255, 240, 200))
        return P.finish(fr, t, 7)
