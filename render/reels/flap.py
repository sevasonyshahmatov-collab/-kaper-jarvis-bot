# -*- coding: utf-8 -*-
"""«Табло» — перекидное табло вылетов (split-flap): буквы щёлкают половинками, как в аэропорту.

Сцены (u — доля трека, D — дроп):
  интро (0 … 4u)      — табло собирает матч: лига и дата, хозяева / гости, время МСК, линия П1 · Х · П2;
  история (4u … D−u)  — «ЧТО ЗАХОДИЛО»: строки прошлых прогнозов канала в заданной вилке кэфов встают по одной
                        на каждые полдоли (клуб, ставка, кэф); строки нужного клуба подсвечены; внизу честный итог
                        «N ИЗ M» (все прогнозы в этой вилке, не только зашедшие);
  перед дропом (1u)   — всё табло крутится;
  ДРОП                — табло встаёт на прогноз (ровно на ударе), вспышка, эмблема клуба над нижними рядами.
Табло — сетка ROWS×COLS одинаковых ячеек; каждая ячейка хранит переходы (начало, конец, целевой символ) и в кадре t
сама решает, стоит ли она или листает случайные символы (половинка падает — настоящая механика сплит-флэпа).
"""
import math
import random

from PIL import Image, ImageDraw

from reels import core as C
from reels import parts as P
from reels.core import W, H

COLS, ROWS = 20, 14
CW, CH, GAP = 46, 70, 4
BX = (W - COLS * (CW + GAP) + GAP) // 2
BY = 372
FG = (238, 236, 228)
AMBER = (255, 190, 46)
GREEN = (60, 220, 120)
CHARSET = 'АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЭЮЯ0123456789.-+'
RATE = 16.0                   # перелистываний в секунду
_T = {}


def tile(ch, col):
    key = (ch, col)
    if key not in _T:
        im = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for y in range(CH):
            k = y / CH
            c = int(44 - 18 * k) if y < CH // 2 else int(34 - 14 * (k - .5))
            d.line((0, y, CW, y), fill=(c, c, c + 4, 255))
        m = C.rrect(CW, CH, 6, (255, 255, 255)).getchannel('A')
        im.putalpha(m)
        if ch.strip():
            g = C.text(ch, 'osw', 56, col, 600)
            C.put(im, g, CW / 2, CH / 2 + 1)
        d = ImageDraw.Draw(im)
        d.line((2, CH // 2, CW - 3, CH // 2), fill=(6, 6, 8, 255), width=2)
        d.line((3, 1, CW - 4, 1), fill=(80, 80, 86, 160), width=1)
        _T[key] = (im, im.crop((0, 0, CW, CH // 2)), im.crop((0, CH // 2, CW, CH)))
    return _T[key]


class Board:
    def __init__(self, seed=3):
        self.tr = [[[] for _ in range(COLS)] for _ in range(ROWS)]      # (начало, конец, символ, цвет)
        self.rnd = random.Random(seed)

    def set_row(self, r, s, t0, t1, col=FG, align='l', stagger=0.03):
        s = s[:COLS]
        if align == 'c':
            s = s.center(COLS)
        s = s.ljust(COLS)
        for c, ch in enumerate(s):
            self.tr[r][c].append((t0, t1 + c * stagger, ch, col))

    def clear(self, rows, t0, t1):
        for r in rows:
            self.set_row(r, '', t0, t1, stagger=0.0)

    def cell(self, r, c, t):
        prev, cur = (' ', FG), None
        for i, (t0, t1, ch, col) in enumerate(self.tr[r][c]):
            if t < t0:
                break
            if t < t1:
                n = int((t - t0) * RATE)
                p = (t - t0) * RATE - n
                rnd = random.Random(hash((r, c, i, n)) & 0xffffff)
                a = rnd.choice(CHARSET) if n else prev[0]
                b = rnd.choice(CHARSET)
                return ('flip', (a, prev[1]), (b, col), p)
            prev = (ch, col)
        return ('still', prev)

    def draw(self, fr, t):
        for r in range(ROWS):
            for c in range(COLS):
                x, y = BX + c * (CW + GAP), BY + r * (CH + GAP)
                st = self.cell(r, c, t)
                if st[0] == 'still':
                    fr.alpha_composite(tile(*st[1])[0], (x, y))
                    continue
                _, (a, ca), (b, cb), p = st
                ta, tb = tile(a, ca), tile(b, cb)
                fr.alpha_composite(tb[1], (x, y))                      # верх — уже новый символ
                fr.alpha_composite(ta[2], (x, y + CH // 2))            # низ — ещё старый
                if p < 0.5:                                            # падает верхняя половинка старого
                    k = math.cos(p * math.pi)
                    hh = max(1, int(CH // 2 * k))
                    fl = ta[1].resize((CW, hh))
                    fr.alpha_composite(C.fade(fl, 0.75 + 0.25 * k), (x, y + CH // 2 - hh))
                else:                                                  # ложится нижняя половинка нового
                    k = -math.cos(p * math.pi)
                    hh = max(1, int(CH // 2 * k))
                    fr.alpha_composite(tb[2].resize((CW, hh)), (x, y + CH // 2))


class Flap(C.Reel):
    def __init__(self, home, away, league, when, line, history, record, focus, pick_team, pick1, pick2, odds,
                 date_title, u=60 / 65, drop=10.6, seed=4):
        """history — [(клуб ≤8, ставка ≤6, кэф)], record — (зашло, всего, 'КЭФ 1.60-2.20'), focus — клуб для подсветки."""
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when = league, when
        self.pick_t = {'home': self.h, 'away': self.a}.get(pick_team)
        self.pick1, self.pick2, self.odds = pick1, pick2, odds
        self.dur = drop + 6.2 * u
        self.cover_t = drop + 3 * u
        b = Board(seed)
        D = drop
        # интро
        b.set_row(1, '%s · %s' % ('НХЛ' if league.upper() == 'NHL' else 'КХЛ', date_title), 0.05, 0.55, AMBER, 'c')
        b.set_row(3, self.h.up, 0.15, 0.85, FG, 'c')
        b.set_row(4, '—', 0.25, 0.9, FG, 'c')
        b.set_row(5, self.a.up, 0.3, 1.0, FG, 'c')
        b.set_row(7, when, 0.4, 1.1, AMBER, 'c')
        b.set_row(9, 'П1    Х     П2', 0.55, 1.2, FG, 'c')
        b.set_row(10, '%s  %s  %s' % tuple(C.fmt_k(k) for k in line), 0.7, 1.4, FG, 'c')
        # история прогнозов
        T1 = 4 * u
        b.clear(range(ROWS), T1 - 0.45, T1)
        b.set_row(0, 'ЧТО ЗАХОДИЛО', T1, T1 + 0.4, AMBER, 'c')
        b.set_row(1, record[2], T1 + 0.1, T1 + 0.5, FG, 'c')
        for i, (club, bet, k) in enumerate(history[:9]):
            ts = T1 + 0.55 + i * 0.5 * u
            col = AMBER if club == focus else FG
            b.set_row(3 + i, '%-8s %-6s %s' % (club[:8], bet[:6], C.fmt_k(k)), ts - 0.5, ts, col, stagger=0.02)
        tsum = T1 + 0.55 + len(history[:9]) * 0.5 * u + 0.2
        b.set_row(13, 'ИТОГ %d ИЗ %d' % record[:2], tsum, tsum + 0.4, GREEN, 'c')
        self.t_hist, self.t_sum = T1, tsum
        # перед дропом всё крутится и встаёт ровно на дроп
        pr = D - u
        b.set_row(0, '', pr, D, stagger=0.0)
        b.set_row(1, 'ПРОГНОЗ', pr, D, AMBER, 'c', stagger=0.006)
        b.set_row(2, '', pr, D, stagger=0.0)
        b.set_row(3, pick1, pr, D, FG, 'c', stagger=0.006)
        b.set_row(4, self.pick_t.up if self.pick_t else '', pr, D, AMBER, 'c', stagger=0.006)
        b.set_row(5, pick2, pr, D, FG, 'c', stagger=0.006)
        b.set_row(6, '', pr, D, stagger=0.0)
        b.set_row(7, 'КЭФ %s' % C.fmt_k(odds), pr, D, AMBER, 'c', stagger=0.006)
        for r in range(8, ROWS):
            b.set_row(r, '', pr, D, stagger=0.0)
        self.board = b

    def _bg(self):
        def make():
            bg = P.vbg((26, 24, 28), (8, 8, 10), glow=(70, 54, 24), glow_xy=(W / 2, 560), glow_r=620, glow_k=0.3).convert('RGBA')
            fx0, fy0 = BX - 26, BY - 26
            fx1, fy1 = BX + COLS * (CW + GAP) - GAP + 26, BY + ROWS * (CH + GAP) - GAP + 26
            fr = C.rrect(fx1 - fx0, fy1 - fy0, 26, (14, 14, 16), outline=(70, 66, 58), width=3)
            C.put(bg, C.shadow(fr, 30, 0.7), (fx0 + fx1) / 2, (fy0 + fy1) / 2 + 16)
            bg.alpha_composite(fr, (fx0, fy0))
            for x in (fx0 + 12, fx1 - 12):                             # заклёпки
                for y in (fy0 + 12, fy1 - 12):
                    C.put(bg, C.ellipse(10, 10, (96, 92, 84)), x, y)
            return bg
        return P.cached(('flapbg',), make)

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self._bg().copy()
        P.header(fr, self.league, self.when)
        self.board.draw(fr, t)
        if t >= D and self.pick_t is not None:                           # эмблема в пустых нижних рядах
            k = P.pop(t, D, 0.4)
            em = P.cached(('flapem', self.pick_t.name), lambda: C.glow(self.pick_t.emb(330), 26, 1.6, AMBER))
            bob = 6 * math.sin((t - D) / u * math.pi)
            C.put(fr, C.scale(em, 0.6 + 0.4 * k), W / 2, BY + 10.6 * (CH + GAP) + bob, a=min(1, k * 1.5))
            fl = max(0.0, 1 - (t - D) / 0.25) * 0.65
            fr = P.flash(fr, fl, (255, 236, 190))
        return P.finish(fr, t)
