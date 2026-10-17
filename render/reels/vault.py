# -*- coding: utf-8 -*-
"""«Сейф» — очные встречи как код от сейфа: каждая встреча — комбинация на лимбе, на дроп дверь распахивается.

Сцены (u — доля трека, D — дроп):
  интро (0 … 4u)   — матч, время МСК, линия П1 · Х · П2 под закрытой дверью сейфа;
  коды             — на каждую встречу 1,5 доли: лимб крутится к шайбам хозяев, потом к шайбам гостей, на табло
                     дата и счёт, на двери загорается лампа (зелёная — встречу взял клуб из прогноза), под дверью растёт
                     список встреч;
  выводы           — строки на табло (по доле): что дают очные встречи;
  перед дропом     — штурвал крутится, лампы мигают;
  ДРОП             — дверь распахивается на петлях, изнутри золотой свет и карточка прогноза.
meetings — [(дата, хозяева, гости, шайбы хозяев, шайбы гостей, 'ОТ'/'Б'/'', победил ли клуб прогноза)].
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import parts as P
from reels.core import W, H

STEEL_HI, STEEL, STEEL_LO = (200, 206, 216), (120, 126, 138), (48, 52, 60)
LED = (255, 70, 60)
LED_G = (80, 255, 140)
DC = (W / 2, 830)        # центр двери
DR = 330                 # радиус двери


def _steel_disc(r, rings=True):
    def make():
        n = 2 * r
        y, x = np.mgrid[0:n, 0:n].astype(np.float32)
        dx, dy = (x - r) / r, (y - r) / r
        d = np.hypot(dx, dy)
        ang = np.arctan2(dy, dx)
        v = 0.55 + 0.25 * np.cos(ang * 2 + 0.6) + 0.12 * np.sin(d * 60) * (d > 0.15)          # «шлифовка» по кругу
        v += -0.25 * dy
        cols = np.stack([np.interp(v, [0, .5, 1], [STEEL_LO[i], STEEL[i], STEEL_HI[i]]) for i in range(3)], -1)
        a = np.clip((1 - d) * r, 0, 1) * 255
        im = Image.fromarray(np.dstack([cols, a]).astype(np.uint8), 'RGBA')
        if rings:
            dr = ImageDraw.Draw(im)
            for rr, wd, c in ((r - 6, 8, (30, 32, 38)), (r - 40, 3, (70, 74, 84)), (int(r * 0.62), 4, (40, 42, 50))):
                dr.ellipse((r - rr, r - rr, r + rr, r + rr), outline=c + (255,), width=wd)
        return im
    return P.cached(('disc', r, rings), make)


def door():
    def make():
        im = _steel_disc(DR).copy()
        d = ImageDraw.Draw(im)
        for k in range(16):                                            # болты по кругу
            a = k / 16 * 2 * math.pi
            x, y = DR + (DR - 24) * math.cos(a), DR + (DR - 24) * math.sin(a)
            d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=(170, 176, 186, 255), outline=(40, 42, 48, 255), width=3)
        return im
    return P.cached(('door',), make)


def dial():
    def make():
        r = 150
        im = _steel_disc(r, rings=False).copy()
        d = ImageDraw.Draw(im)
        d.ellipse((6, 6, 2 * r - 6, 2 * r - 6), fill=(26, 28, 34, 255))
        for k in range(50):
            a = k / 50 * 2 * math.pi - math.pi / 2
            l = 26 if k % 5 == 0 else 12
            x0, y0 = r + (r - 14) * math.cos(a), r + (r - 14) * math.sin(a)
            x1, y1 = r + (r - 14 - l) * math.cos(a), r + (r - 14 - l) * math.sin(a)
            d.line((x0, y0, x1, y1), fill=(220, 224, 232, 255), width=4 if k % 5 == 0 else 2)
        for k in range(0, 10):
            a = k / 10 * 2 * math.pi - math.pi / 2
            tx = C.text(str(k), 'mont', 30, (220, 224, 232), 800)
            C.put(im, tx, r + (r - 66) * math.cos(a), r + (r - 66) * math.sin(a))
        im.alpha_composite(C.ellipse(90, 90, STEEL), (r - 45, r - 45))
        return im
    return P.cached(('dial',), make)


def wheel():
    def make():
        s = 300
        im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for k in range(3):
            a = k / 3 * math.pi
            dx, dy = 140 * math.cos(a), 140 * math.sin(a)
            d.line((s / 2 - dx, s / 2 - dy, s / 2 + dx, s / 2 + dy), fill=(150, 156, 168, 255), width=16)
            for sgn in (-1, 1):
                d.ellipse((s / 2 + sgn * dx - 16, s / 2 + sgn * dy - 16, s / 2 + sgn * dx + 16, s / 2 + sgn * dy + 16),
                          fill=(190, 196, 206, 255))
        return im
    return P.cached(('wheel',), make)


class Vault(C.Reel):
    def __init__(self, home, away, league, when, line, meetings, facts, pick_team, pick1, pick2, odds, u=60 / 67.5,
                 drop=None, seed=9):
        n = len(meetings)
        drop = drop if drop is not None else (4 + 1.5 * n + len(facts) + 1) * u
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.line = league, when, line
        self.meet, self.facts = meetings, facts
        self.pick_t = {'home': self.h, 'away': self.a}.get(pick_team)
        self.pick1, self.pick2, self.odds = pick1, pick2, odds
        self.T1 = 4 * u
        self.tm = [self.T1 + 1.5 * u * i for i in range(n)]            # начало кода каждой встречи
        self.TF = self.T1 + 1.5 * u * n
        self.dur = drop + 6 * u
        self.cover_t = drop + 3 * u

    def _dial_angle(self, t):
        """Угол лимба: к каждой встрече — сначала цифра хозяев, потом гостей (последняя цифра счёта)."""
        ang, u = 0.0, self.u
        for (dt, hh, aa, sh, sa, ot, win), t0 in zip(self.meet, self.tm):
            for j, v in enumerate((sh, sa)):
                ts = t0 + j * 0.7 * u
                target = -(v % 10) * 36.0 + (360 if j else 720) * (1 if (len(dt) % 2) else -1)
                if t >= ts:
                    k = C.out_cubic(C.clamp((t - ts) / (0.55 * u)))
                    ang = C.lerp(ang, target, k)
        if t > self.drop - self.u:
            ang += (t - (self.drop - self.u)) * 900
        return ang

    def _led(self, s, col=LED):
        def make():
            pl = C.rrect(960, 150, 20, (10, 6, 6), 240, outline=(80, 30, 26), width=3)
            C.put(pl, C.glow(C.text(s, 'mono', 50, col, 800, max_w=900), 10, 1.4, col), 480, 75)
            return pl
        return P.cached(('led', s, col), make)

    def _row(self, i):
        dt, hh, aa, sh, sa, ot, win = self.meet[i]
        def make():
            col = LED_G if win else (255, 110, 100)
            s = '%s  %s %d:%d %s%s' % (dt, hh, sh, sa, aa, (' ' + ot) if ot else '')
            return C.text(s, 'mono', 36, col, 700, max_w=980)
        return P.cached(('vrow', i), make)

    def frame(self, t):
        u, D = self.u, self.drop
        fr = P.vbg((24, 26, 32), (8, 9, 12), glow=(60, 66, 80), glow_xy=DC, glow_r=600, glow_k=0.4).convert('RGBA')
        P.header(fr, self.league, self.when, acc=(255, 200, 80))
        n = len(self.meet)
        # дверь (до дропа закрыта, после — распахивается на левой петле)
        op = C.out_cubic(C.clamp((t - D) / (0.5 * u))) if t >= D else 0.0
        if op > 0:
            inner = P.cached(('vin',), lambda: C.radial(2 * DR + 260, 2 * DR + 260, (255, 214, 120), 255, 1.6))
            C.put(fr, inner, DC[0], DC[1], a=op)
            C.put(fr, P.cached(('vhole',), lambda: C.ellipse(2 * DR - 20, 2 * DR - 20, (40, 30, 14))), DC[0], DC[1], a=1 - op * 0.6)
        dr_im = door().copy()
        ang = self._dial_angle(t)
        C.put(dr_im, C.rotate(dial(), ang), DR, DR)
        whl = C.rotate(wheel(), (t - D + u) * 400 if t > D - u else 0)
        C.put(dr_im, whl, DR, DR)
        C.put(dr_im, P.cached(('dial2',), lambda: dial().crop((105, 105, 195, 195))), DR, DR)
        # лампы встреч
        for i in range(n):
            lx = DR + (i - (n - 1) / 2) * 70
            on = t >= self.tm[i] + 1.2 * u
            win = self.meet[i][6]
            blink = (D - u < t < D) and int(t * 8) % 2
            col = (LED_G if win else LED) if on and not blink else (50, 50, 56)
            C.put(dr_im, C.ellipse(40, 40, col), lx, 90)
        C.put(dr_im, C.polygon([(0, 0), (30, 0), (15, 26)], (30, 26), (255, 220, 120)), DR, DR - 168)      # метка лимба
        if op <= 0:
            C.put(fr, C.shadow(dr_im, 26, 0.7), DC[0], DC[1] + 20)
            C.put(fr, dr_im, DC[0], DC[1])
        else:
            sx = max(0.04, math.cos(op * math.radians(78)))
            dw = max(2, int(dr_im.width * sx))
            sq = dr_im.resize((dw, dr_im.height))
            dk = Image.new('RGBA', sq.size, (0, 0, 0, int(140 * op)))
            dk.putalpha(Image.fromarray((np.asarray(sq.getchannel('A'), np.float32) * 0.55 * op).astype(np.uint8)))
            sq.alpha_composite(dk)
            C.put(fr, sq, DC[0] - DR + dw / 2 - 200 * op, DC[1])
        if t < D:                                                        # эмблемы клубов по бокам двери
            for tm, x in ((self.h, 112), (self.a, W - 112)):
                em = P.cached(('v_em', tm.name), lambda tm=tm: C.with_shadow(tm.emb(150), 12, 0.6, 8))
                C.put(fr, em, x, 600, a=C.clamp((t - 0.2) / 0.4))
        # верхнее табло
        if t < self.T1:
            ttl = P.cached(('v_ttl',), lambda: C.text('%s — %s' % (self.h.up, self.a.up), 'osw', 66, (235, 238, 245), 700,
                                                    max_w=W - 100))
            C.put(fr, ttl, W / 2, 410, a=C.clamp(t / 0.4))
            od = P.cached(('v_odds',), lambda: C.odds_row(self.line, w=860, h=160, fill=(30, 32, 40), fill_a=235,
                                                         val_col=(255, 220, 140), outline=(110, 116, 128)))
            C.put(fr, od, W / 2, 1330, a=C.clamp((t - 0.6) / 0.4))
        elif t < D:
            if t < self.TF:
                i = min(n - 1, int((t - self.T1) / (1.5 * u)))
                dt, hh, aa, sh, sa, ot, win = self.meet[i]
                s = 'ОЧНАЯ %d · %s' % (i + 1, dt) if t < self.tm[i] + 0.7 * u else '%d : %d%s' % (sh, sa, (' ' + ot) if ot else '')
                C.put(fr, self._led(s), W / 2, 420)
            elif t < self.TF + len(self.facts) * u:
                j = int((t - self.TF) / u)
                C.put(fr, self._led(self.facts[j], (255, 210, 90)), W / 2, 420)
            else:
                C.put(fr, self._led('ОТКРЫВАЕМ...', (255, 210, 90)), W / 2, 420, a=0.5 + 0.5 * (int(t * 8) % 2))
            for i in range(n):                                       # список встреч под дверью
                if t >= self.tm[i] + 1.2 * u:
                    C.put(fr, self._row(i), W / 2, 1230 + i * 66, a=C.clamp((t - self.tm[i] - 1.2 * u) / 0.25))
        else:
            card = P.pick_card(self.pick_t, self.pick1, self.pick2, self.odds, acc=(255, 200, 80), dark=(24, 18, 8))
            k = P.pop(t, D + 0.1, 0.45)
            C.put(fr, C.scale(card, 0.5 + 0.5 * k), W / 2, DC[1] + 20, a=min(1, k * 1.4))
            C.put(fr, self._led('%d ИЗ %d ОЧНЫХ' % (sum(m[6] for m in self.meet), n), LED_G), W / 2, 420)
            fr = P.flash(fr, max(0.0, 1 - (t - D) / 0.25) * 0.55, (255, 236, 190))
        return P.finish(fr, t, 7)
