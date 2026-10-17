# -*- coding: utf-8 -*-
"""«Тактическая доска» — тренерская доска, маркер рисует разбор на долях трека.

Белая доска с напечатанной половиной площадки; маркер пишет от руки (Caveat) название матча, магниты с
эмблемами клубов, на дропе камера уезжает вниз к площадке: «О» и «Х», стрелки передач, бросок в ворота;
дальше — заметки (только факты: кто дома, кто фаворит по линии), прогноз от руки, кэф в рамке, двойное
подчёркивание и в конце — жёлтый стикер «Telegram @jarvibet».
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels.core import W, H

BOARD = (238, 239, 236)
BLACK = (28, 30, 36)
BLUE = (28, 70, 175)
RED = (205, 36, 44)
CH = 3700                 # высота доски


def bez(p0, p1, p2, n=40):
    return [((1 - s) ** 2 * p0[0] + 2 * (1 - s) * s * p1[0] + s * s * p2[0],
             (1 - s) ** 2 * p0[1] + 2 * (1 - s) * s * p1[1] + s * s * p2[1]) for s in np.linspace(0, 1, n)]


def prefix(pts, p):
    """Часть ломаной длиной p (0..1)."""
    if p >= 1:
        return pts
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    tot, out, acc = sum(seg) * p, [pts[0]], 0.0
    for (a, b), L in zip(zip(pts, pts[1:]), seg):
        if acc + L >= tot:
            k = (tot - acc) / L if L else 0
            out.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
            return out
        out.append(b)
        acc += L
    return out


class Board(C.Reel):
    def __init__(self, home, away, league, pick, coef, when, notes, u=60 / 77, drop=2.34, seed=13):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.pick, self.coef, self.when, self.notes = pick, coef, when, notes
        self.league = 'НХЛ' if str(league).upper() == 'NHL' else 'КХЛ'
        self.rx0, self.ry0, self.rw, self.rh = 90, 800, 900, 1060          # половина площадки на доске
        self.strokes = []
        self._plan()
        self.dur = self.b(15)
        self.cover_t = self.b(12.8)
        self._prep()

    # координаты на площадке в футах: x 0..85 (поперёк), y 0..100 (от центральной линии к борту)
    def P(self, x, y):
        return self.rx0 + x / 85 * self.rw, self.ry0 + y / 100 * self.rh

    def _plan(self):
        b, D = self.b, self.drop
        S = self.strokes
        # заголовок от руки
        S.append(('text', 0.15, b(-1.2), self._hand('%s — %s' % (self.h.up, self.a.up), 112, BLACK, 960), (W / 2, 330)))
        S.append(('text', b(-1.4), b(-0.4), self._hand('%s · %s' % (self.league, self.when), 64, BLUE, 900), (W / 2, 450)))
        S.append(('line', b(-0.6), b(-0.1), [(170, 505), (910, 498)], BLACK, 7))
        # магниты-легенда
        S.append(('magnet', b(-1), None, self.h, (240, 640)))
        S.append(('magnet', b(-0.5), None, self.a, (650, 640)))
        S.append(('text', b(-0.9), b(-0.3), self._hand('= O', 80, BLUE, 200), (360, 640)))
        S.append(('text', b(-0.4), b(0), self._hand('= X', 80, RED, 200), (770, 640)))
        # игроки: О — хозяева (атакуют вниз), Х — гости
        os_ = [(22, 40), (63, 44), (42, 58)]
        xs = [(30, 62), (55, 66), (42, 80)]
        for i, (x, y) in enumerate(os_):
            S.append(('circle', D + 0.08 * i, D + 0.08 * i + 0.3, self.P(x, y), BLUE))
        for i, (x, y) in enumerate(xs):
            S.append(('x', b(1) + 0.08 * i, b(1) + 0.08 * i + 0.3, self.P(x, y), RED))
        # передачи и бросок
        S.append(('arrow', b(2), b(2.8), bez(self.P(22, 43), self.P(40, 36), self.P(60, 46)), BLUE, 9))
        S.append(('arrow', b(3), b(3.8), bez(self.P(63, 48), self.P(60, 58), self.P(46, 60)), BLUE, 9))
        S.append(('arrow', b(4), b(4.6), bez(self.P(42, 62), self.P(44, 74), self.P(42.5, 86)), RED, 11))
        S.append(('scribble', b(4.5), b(5.2), self.P(42.5, 88), RED))
        # заметки
        for i, s in enumerate(self.notes):
            S.append(('text', b(6 + i), b(6.8 + i), self._hand('• ' + s, 84, BLACK, 940, align='l'), (W / 2, 1985 + i * 92)))
        # прогноз
        S.append(('text', b(8), b(9.2), self._hand(self.pick.upper(), 120, BLUE, 960), (W / 2, 2290)))
        kf = self._hand('КЭФ ' + C.fmt_k(self.coef), 120, RED, 700)
        S.append(('text', b(9.2), b(9.9), kf, (W / 2, 2440)))
        bw, bh = kf.width + 80, kf.height + 40
        x0, y0 = W / 2 - bw / 2, 2440 - bh / 2
        S.append(('line', b(10), b(10.6), [(x0, y0 + 6), (x0 + bw, y0 - 4), (x0 + bw + 6, y0 + bh), (x0 - 4, y0 + bh + 4), (x0 + 2, y0 - 10)], RED, 9))
        S.append(('line', b(10.6), b(10.9), [(220, 2360), (860, 2352)], BLUE, 8))
        S.append(('line', b(10.9), b(11.2), [(240, 2378), (840, 2372)], BLUE, 8))

    def _hand(self, s, size, col, max_w, align='c'):
        return C.text(s, 'hand', size, col, 700, max_w=max_w)

    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        arr = np.ones((CH, W, 3), np.float32) * np.array(BOARD, np.float32)
        # блик и следы стёртого маркера
        y, x = np.mgrid[0:CH, 0:W].astype(np.float32)
        arr += 10 * np.exp(-(((x * 0.6 + y * 0.35) - 900) / 260) ** 2)[..., None]
        board = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        ghost = Image.new('RGBA', (W, CH), (0, 0, 0, 0))
        gd = ImageDraw.Draw(ghost)
        for _ in range(14):
            x0, y0 = rnd.uniform(0, W), rnd.uniform(0, CH)
            pts = [(x0 + rnd.uniform(-160, 160), y0 + rnd.uniform(-60, 60)) for _ in range(4)]
            gd.line(pts, fill=(120, 130, 150, 16), width=int(rnd.uniform(8, 18)), joint='curve')
        board.alpha_composite(ghost.filter(ImageFilter.GaussianBlur(5)))
        # напечатанная половина площадки
        lay = Image.new('RGBA', (W, CH), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        x0, y0, rw, rh = self.rx0, self.ry0, self.rw, self.rh
        r = 28 / 85 * rw
        pr = (196, 40, 50, 150)
        pb = (60, 110, 200, 160)
        d.rounded_rectangle((x0, y0 - r, x0 + rw, y0 + rh), radius=int(r), outline=(90, 96, 110, 220), width=6)
        lay2 = Image.new('RGBA', (W, CH), (0, 0, 0, 0))
        lay2.paste(lay.crop((0, int(y0), W, CH)), (0, int(y0)))
        lay = lay2
        d = ImageDraw.Draw(lay)
        d.line((x0, y0, x0 + rw, y0), fill=pr, width=10)                         # центральная
        _, yb = self.P(0, 25)
        d.line((x0, yb, x0 + rw, yb), fill=pb, width=12)                          # синяя
        _, yg = self.P(0, 89)
        d.line((x0 + 30, yg, x0 + rw - 30, yg), fill=pr, width=5)                 # линия ворот
        for fx in (20.5, 64.5):                                                   # круги вбрасывания
            cx, cy = self.P(fx, 69)
            rr = 15 / 85 * rw
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=pr, width=5)
            d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=pr)
            ncx, ncy = self.P(fx, 30)
            d.ellipse((ncx - 9, ncy - 9, ncx + 9, ncy + 9), fill=pr)
        cx, cy = self.P(42.5, 89)
        cr = 6 / 85 * rw
        d.pieslice((cx - cr, cy - cr, cx + cr, cy + cr), 180, 360, fill=(120, 170, 230, 90), outline=pr, width=4)
        nw, nd = 3 / 85 * rw, 3.5 / 100 * rh
        d.rectangle((cx - nw, cy, cx + nw, cy + nd), outline=(196, 40, 50, 200), width=5)
        cx, cy = self.P(42.5, 0)
        d.arc((cx - 15 / 85 * rw, cy - 15 / 85 * rw, cx + 15 / 85 * rw, cy + 15 / 85 * rw), 0, 180, fill=pb, width=5)
        board.alpha_composite(lay)
        self.board = board
        self.mag = {}
        for t in (self.h, self.a):
            m = C.ellipse(150, 150, (250, 250, 250))
            rim = Image.new('RGBA', (150, 150), (0, 0, 0, 0))
            ImageDraw.Draw(rim).ellipse((3, 3, 147, 147), outline=(200, 200, 205, 255), width=5)
            m.alpha_composite(rim)
            C.put(m, t.emb(104), 75, 75)
            self.mag[t.name] = C.with_shadow(m, 10, 0.45, 8)
        self.note = self._sticky()

    def _sticky(self):
        w, h = 640, 520
        im = Image.new('RGBA', (w, h), (255, 226, 92, 255))
        g = C.lgrad(w, h, (255, 236, 130), (246, 206, 60), 70)
        im.alpha_composite(g)
        C.put(im, C.text('разбор каждого', 'hand', 74, BLACK, 700), w / 2, 110)
        C.put(im, C.text('матча тут:', 'hand', 74, BLACK, 700), w / 2, 190)
        C.put(im, C.tg_icon(96), 100, 330)
        C.put(im, C.text('Telegram', 'hand', 84, BLUE, 700), 380, 300)
        C.put(im, C.text(C.HANDLE, 'hand', 84, RED, 700), w / 2, 430)
        im = C.rotate(im, -4)
        return C.with_shadow(im, 16, 0.4, 14)

    def draw_strokes(self, img, t):
        d = ImageDraw.Draw(img)
        for st in self.strokes:
            kind, t0, t1 = st[0], st[1], st[2]
            if t < t0:
                continue
            p = 1.0 if t1 is None else C.seg(t, t0, t1)
            if kind == 'text':
                im, (cx, cy) = st[3], st[4]
                wv = int(im.width * C.in_out(p) * 1.0)
                if wv > 0:
                    part = im.crop((0, 0, wv, im.height))
                    img.alpha_composite(part, (int(cx - im.width / 2), int(cy - im.height / 2)))
                    if p < 1:
                        tip = (int(cx - im.width / 2 + wv), int(cy))
                        d.ellipse((tip[0] - 6, tip[1] - 6, tip[0] + 6, tip[1] + 6), fill=BLACK + (200,))
            elif kind in ('line', 'arrow'):
                pts, col, wd = st[3], st[4], st[5]
                pp = prefix(pts, C.in_out(p))
                if len(pp) > 1:
                    d.line(pp, fill=col + (235,), width=wd, joint='curve')
                    for q in (pp[0], pp[-1]):
                        d.ellipse((q[0] - wd / 2, q[1] - wd / 2, q[0] + wd / 2, q[1] + wd / 2), fill=col + (235,))
                if kind == 'arrow' and p >= 1:
                    (ax, ay), (bx, by) = pts[-4], pts[-1]
                    ang = math.atan2(by - ay, bx - ax)
                    for s in (2.6, -2.6):
                        d.line((bx, by, bx + 38 * math.cos(ang + s), by + 38 * math.sin(ang + s)), fill=col + (235,), width=wd)
            elif kind == 'circle':
                (cx, cy), col = st[3], st[4]
                r = 34
                d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * C.out_cubic(p), fill=col + (240,), width=10)
            elif kind == 'x':
                (cx, cy), col = st[3], st[4]
                r = 30
                q1, q2 = C.seg(p, 0, 0.5), C.seg(p, 0.5, 1)
                if q1 > 0:
                    d.line((cx - r, cy - r, cx - r + 2 * r * q1, cy - r + 2 * r * q1), fill=col + (240,), width=10)
                if q2 > 0:
                    d.line((cx + r, cy - r, cx + r - 2 * r * q2, cy - r + 2 * r * q2), fill=col + (240,), width=10)
            elif kind == 'scribble':
                (cx, cy), col = st[3], st[4]
                n = int(60 * p)
                pts = [(cx + 70 * math.cos(i * 0.55) * (0.5 + 0.5 * math.sin(i * 0.21)),
                        cy + 40 * math.sin(i * 0.55) * (0.6 + 0.4 * math.cos(i * 0.17))) for i in range(n)]
                if len(pts) > 1:
                    d.line(pts, fill=col + (230,), width=7, joint='curve')
            elif kind == 'magnet':
                tm, (cx, cy) = st[3], st[4]
                k = C.seg(t, t0, t0 + 0.18)
                m = C.scale(self.mag[tm.name], 1.25 - 0.25 * C.out_cubic(k))
                C.put(img, m, cx, cy + 8, min(1.0, k * 3))
        return img

    def cam(self, t):
        """Положение камеры на доске (верх кадра, с) и наезд."""
        b = self.b
        keys = [(0, 0.0), (self.drop - 0.05, 0.0), (self.drop + 0.35, 640.0), (b(5.4), 640.0), (b(6.2), 1290.0),
                (b(11.3), 1290.0), (b(11.7), 1690.0), (b(15), 1690.0)]
        y = keys[-1][1]
        for (t0, y0), (t1, y1) in zip(keys, keys[1:]):
            if t0 <= t < t1:
                y = C.lerp(y0, y1, C.in_out(C.seg(t, t0, t1)))
                break
        return y

    def frame(self, t):
        img = self.board.copy()
        self.draw_strokes(img, t)
        cy = self.cam(t)
        v = abs(self.cam(t + 1 / 30) - cy)
        fr = img.crop((0, int(cy), W, int(cy) + H))
        if v > 6:                                                 # смаз по вертикали при быстром проезде камеры
            k = max(1, int(min(v / 3, 24)))
            fr = fr.resize((W, max(1, H // k)), Image.BILINEAR).resize((W, H), Image.BILINEAR)
        z = 1.0 + 0.03 * math.sin(t * 0.5)
        if t >= self.b(11.8):                                     # стикер поверх кадра
            k = C.seg(t, self.b(11.8), self.b(11.8) + 0.16)
            sn = C.scale(self.note, 1.4 - 0.4 * C.out_cubic(k))
            C.put(fr, sn, W / 2 + 90, 1150, min(1.0, k * 2.5))
        dx, dy = C.shake(t, self.drop + 0.35, 10, 0.3)
        sx, sy = C.shake(t, self.b(11.8) + 0.16, 8, 0.25)
        fr = C.zoom(fr, z, dx=dx + sx, dy=dy + sy)
        return C.vignette(fr, 0.25)
