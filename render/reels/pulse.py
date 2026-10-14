# -*- coding: utf-8 -*-
"""«Пульс» — форма команды как кардиограмма (трек на 60 уд/мин — один удар сердца на долю).

Сцены (u — доля трека, D — дроп):
  интро (0 … 3u)       — монитор включается: матч, время МСК, линия П1 · Х · П2 в зелёном люминофоре;
  кардиограмма (3u …)  — на каждую долю — один комплекс PQRST = один из последних матчей: высота зубца R — шайбы
                         команды, зелёный — победа, красный — поражение; под зубцом соперник и счёт;
  показатели (2u)      — четыре плашки монитора: победы, шайб за игру, большинство, лидер по очкам;
  перед дропом (1u)    — линия ровная, писк, мигает «НА КОНУ»;
  ДРОП                 — огромный зубец во весь экран, вспышка, карточка прогноза; пульс дальше бьётся на каждую долю.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import parts as P
from reels.core import W, H

GRN = (70, 255, 150)
RED = (255, 84, 84)
DIM = (24, 70, 44)
TX0, TX1 = 70, W - 70            # полоса кардиограммы
BASE = 900                       # изолиния
PX_GOAL = 44                     # высота зубца на шайбу


def complex_y(x, amp):
    """Комплекс PQRST, x — в долях интервала (−0.5 … 0.5), amp — высота R (px). Возвращает смещение вверх."""
    g = lambda c, w, a: a * np.exp(-((x - c) / w) ** 2)
    return (g(-0.27, 0.05, 14) - g(-0.045, 0.012, 22) + g(0.0, 0.016, amp) - g(0.045, 0.014, 34) + g(0.24, 0.07, 26))


class Pulse(C.Reel):
    def __init__(self, team, opp, league, when, line, games, tiles, pick_team, pick1, pick2, odds, home=True,
                 u=1.0, drop=12.0, seed=6):
        """games — [(соперник, 'В'/'П', забили, пропустили, 'ОТ'/'Б'/'')] от старых к новым (до 6);
        tiles — [(подпись, значение)] ×4."""
        super().__init__(u, drop, seed)
        h, a = (team, opp) if home else (opp, team)
        self.h, self.a = C.match(h, a, league)
        self.t = self.h if home else self.a
        self.league, self.when, self.line = league, when, line
        self.games, self.tiles = games[-6:], tiles[:4]
        self.pick_t = {'home': self.h, 'away': self.a}.get(pick_team)
        self.pick1, self.pick2, self.odds = pick1, pick2, odds
        self.T0 = 3 * u                                      # первый удар — комплекс первого матча
        self.dur = drop + 5.6 * u
        self.cover_t = drop + 2.5 * u
        n = len(self.games)
        self.step = (TX1 - TX0) / n
        xs = np.arange(TX0, TX1, dtype=np.float32)
        y = np.zeros_like(xs)
        self.cols = []
        for i, (opp_, res, gf, ga, ot) in enumerate(self.games):
            cx = TX0 + (i + 0.5) * self.step
            y += complex_y((xs - cx) / self.step, PX_GOAL * min(gf, 8))
            self.cols.append(GRN if res == 'В' else RED)
        self.xs, self.ys = xs, BASE - y

    # ── фон монитора ──
    def _bg(self):
        def make():
            bg = P.vbg((6, 16, 12), (2, 6, 4), glow=(10, 40, 24), glow_xy=(W / 2, 800), glow_r=700, glow_k=0.5).convert('RGBA')
            d = ImageDraw.Draw(bg)
            for x in range(0, W, 30):
                d.line((x, 330, x, 1470), fill=DIM + (90 if x % 150 else 170,), width=1)
            for y in range(330, 1471, 30):
                d.line((0, y, W, y), fill=DIM + (90 if (y - 330) % 150 else 170,), width=1)
            sl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ds = ImageDraw.Draw(sl)
            for y in range(0, H, 4):
                ds.line((0, y, W, y), fill=(0, 0, 0, 46))
            bg.alpha_composite(sl)
            return bg
        return P.cached(('pulsebg',), make)

    def _trace(self, x_head, boost=0.0):
        """Слой с кардиограммой до x_head (с бегущей точкой и свечением)."""
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        k = int(max(0, min(len(self.xs), x_head - TX0)))
        if k > 1:
            for i in range(len(self.games)):
                a = int(i * self.step)
                b = min(k, int((i + 1) * self.step) + 1)
                if b - a < 2:
                    continue
                pts = list(zip(self.xs[a:b].tolist(), self.ys[a:b].tolist()))
                d.line(pts, fill=self.cols[i] + (255,), width=6, joint='curve')
        if TX0 < x_head < TX1 + 4:
            yh = float(np.interp(x_head, self.xs, self.ys))
            d.ellipse((x_head - 11, yh - 11, x_head + 11, yh + 11), fill=(230, 255, 240, 255))
        gl = lay.filter(ImageFilter.GaussianBlur(10))
        gl.putalpha(gl.getchannel('A').point(lambda v: min(255, int(v * (2.2 + boost)))))
        gl.alpha_composite(lay)
        return gl

    def _labels(self, fr, t):
        for i, (opp_, res, gf, ga, ot) in enumerate(self.games):
            tb = self.T0 + i * self.u
            if t < tb - 0.05:
                continue
            k = C.clamp((t - tb + 0.05) / 0.25)
            cx = TX0 + (i + 0.5) * self.step
            col = GRN if res == 'В' else RED
            nm = P.cached(('pl_nm', opp_), lambda: C.text(opp_.upper(), 'mont', 22, (170, 220, 190), 800, max_w=self.step - 10))
            sc = P.cached(('pl_sc', gf, ga, ot, col), lambda: C.text('%d:%d%s' % (gf, ga, (' ' + ot) if ot else ''),
                                                                  'osw', 44, col, 700))
            C.put(fr, nm, cx, BASE + 92, a=k)
            C.put(fr, sc, cx, BASE + 140, a=k)
            top = BASE - PX_GOAL * min(gf, 8) - 34
            C.put(fr, P.cached(('pl_g', gf, col), lambda: C.text(str(gf), 'osw', 40, col, 700)), cx + 34, top + 10, a=k)

    def _tile(self, lab, val):
        def make():
            pl = C.rrect(470, 150, 18, (8, 26, 16), 230, outline=(50, 140, 90), width=2)
            C.put(pl, C.text(lab, 'mont', 24, (150, 210, 175), 800, track=0.18, max_w=430), 235, 40)
            C.put(pl, C.text(val, 'osw', 64, GRN, 700, max_w=430), 235, 100)
            return pl
        return P.cached(('pl_tile', lab, val), make)

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self._bg().copy()
        P.header(fr, self.league, self.when, acc=GRN, sub=(150, 210, 175))
        # заголовок монитора
        if t < self.T0 - 0.3:
            a = C.clamp(t / 0.4)
            C.put(fr, P.cached(('pl_m', 0), lambda: C.text('%s — %s' % (self.h.up, self.a.up), 'osw', 74, (230, 255, 240), 700,
                                                          max_w=W - 120)), W / 2, 470, a=a)
            for j, tm in enumerate((self.h, self.a)):
                em = P.cached(('pl_em', tm.name), lambda tm=tm: C.with_shadow(tm.emb(250), 16, 0.6, 8))
                C.put(fr, C.scale(em, 0.8 + 0.2 * P.pop(t, 0.15 + 0.2 * j)), W / 2 + (-230 if j == 0 else 230), 760,
                      a=C.clamp((t - 0.15 - 0.2 * j) / 0.3))
            C.put(fr, P.cached(('pl_vs',), lambda: C.text('VS', 'osw', 64, GRN, 700)), W / 2, 760, a=a)
            od = P.cached(('pl_odds', self.line), lambda: C.odds_row(self.line, w=900, h=170, fill=(8, 40, 24), fill_a=230,
                                                                     val_col=GRN, lab_col=(150, 210, 175), outline=(50, 140, 90)))
            C.put(fr, od, W / 2, 1120, a=C.clamp((t - 0.8) / 0.4))
        else:
            ttl = P.cached(('pl_t',), lambda: C.text('ФОРМА · %s' % self.t.up, 'osw', 70, (230, 255, 240), 700, max_w=W - 260))
            sub = P.cached(('pl_s', len(self.games)), lambda: C.text('ПОСЛЕДНИЕ %d МАТЧЕЙ' % len(self.games), 'mont', 28,
                                                                     (150, 210, 175), 800, track=0.2))
            em = P.cached(('pl_em_s', self.t.name), lambda: self.t.emb(120))
            C.put(fr, em, 120, 440)
            C.put(fr, ttl, 210, 410, anchor='tl')
            C.put(fr, sub, 214, 410 + ttl.height + 14, anchor='tl')
            # кардиограмма: удар i — на долю T0 + i·u, голова идёт равномерно между ударами
            tp = (t - self.T0) / u + 0.5
            x_head = TX0 + C.clamp(tp / len(self.games), 0, 1.02) * (TX1 - TX0)
            if t < D:
                fr.alpha_composite(self._trace(x_head))
                self._labels(fr, t)
                t_tiles = self.T0 + len(self.games) * u
                for j, (lab, val) in enumerate(self.tiles):
                    tj = t_tiles + j * 0.4 * u
                    if t >= tj:
                        k = P.pop(t, tj, 0.3)
                        C.put(fr, C.scale(self._tile(lab, val), 0.85 + 0.15 * k), 285 + (j % 2) * 510, 1150 + (j // 2) * 162,
                              a=min(1, k * 1.4))
                if t > D - u:                                     # тишина перед ударом
                    blink = 1.0 if int((t - (D - u)) * 6) % 2 == 0 else 0.35
                    C.put(fr, P.cached(('pl_alarm',), lambda: C.text('НА КОНУ: %s — %s' % (self.h.up, self.a.up), 'mont', 34,
                                                                     RED, 900, track=0.08, max_w=W - 100)), W / 2, 1440, a=blink)
            else:
                # после дропа: на каждую долю — новый удар через весь экран, карточка прогноза
                beat = (t - D) / u
                ph = beat - math.floor(beat)
                lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(lay)
                xs = np.arange(0, W, 3, dtype=np.float32)
                amp = 330 if beat < 1 else 220
                ys = 870 - complex_y((xs - W / 2) / 700, amp)
                head = int(len(xs) * min(1, ph * 1.6 + (0.4 if beat >= 1 else 0)))
                if head > 2:
                    d.line(list(zip(xs[:head].tolist(), ys[:head].tolist())), fill=GRN + (255,), width=8, joint='curve')
                gl = lay.filter(ImageFilter.GaussianBlur(12))
                gl.putalpha(gl.getchannel('A').point(lambda v: min(255, int(v * 2.6))))
                gl.alpha_composite(lay)
                fr.alpha_composite(gl)
                card = P.pick_card(self.pick_t, self.pick1, self.pick2, self.odds, acc=GRN, dark=(6, 22, 14))
                k = P.pop(t, D + 0.05, 0.4)
                C.put(fr, C.scale(card, 0.7 + 0.3 * k), W / 2, 1210 + 6 * P.beat_pulse(t, D, u), a=min(1, k * 1.5))
                fr = P.flash(fr, max(0.0, 1 - (t - D) / 0.22) * 0.7, (200, 255, 220))
        return P.finish(fr, t, 7)
