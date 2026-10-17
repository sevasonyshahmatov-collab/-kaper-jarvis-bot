# -*- coding: utf-8 -*-
"""«Погода на льду» — прогноз на матч как прогноз погоды на ТВ.

Карта северо-востока США (us-atlas), значок канала «JARVIS ТВ», плашка «ПОГОДА НА ЛЬДУ», на долях
появляются булавки городов с эмблемами; на дропе над городом соперника фаворита — грозовая туча с молниями
и дождём, над городом фаворита — солнце; карточки городов «ЯСНО · шанс 58%» / «ГРОЗА · 42%», затем —
карточка «ПРОГНОЗ НА МАТЧ» с кэфом и подписка. Шансы — наш прогноз на победу с учётом ОТ и буллитов.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import geo
from reels.core import W, H

NAVY = (8, 18, 40)
LAND = (26, 66, 78)
LAND2 = (36, 92, 98)
BORDER = (120, 170, 190)
SUN = (255, 196, 50)
TV = (24, 92, 200)
WHITE = (255, 255, 255)
INK = (16, 26, 44)

X0, Y0, SC, MY = 700, 60, 3.93, 440        # окно карты (координаты Albers) → кадр


def to_screen(x, y):
    return (x - X0) * SC, MY + (y - Y0) * SC


def sun_icon(r, t, glow=True):
    S = int(r * 3.2)
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S / 2
    for i in range(12):
        a = math.radians(i * 30 + t * 25)
        pts = [(c + r * 1.25 * math.cos(a - 0.12), c + r * 1.25 * math.sin(a - 0.12)),
               (c + r * 1.55 * math.cos(a), c + r * 1.55 * math.sin(a)),
               (c + r * 1.25 * math.cos(a + 0.12), c + r * 1.25 * math.sin(a + 0.12))]
        d.polygon(pts, fill=SUN + (255,))
    d.ellipse((c - r, c - r, c + r, c + r), fill=SUN + (255,))
    d.ellipse((c - r * 0.8, c - r * 0.85, c + r * 0.5, c + r * 0.3), fill=(255, 226, 120, 255))
    return C.glow(im, int(r * 0.35), 0.9, (255, 170, 40)) if glow else im


def cloud(w, dark=False):
    h = int(w * 0.62)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    top = (90, 96, 110) if dark else (250, 252, 255)
    bot = (52, 56, 68) if dark else (205, 215, 230)
    for (cx, cy, r) in ((0.30, 0.62, 0.22), (0.50, 0.42, 0.30), (0.72, 0.58, 0.22), (0.50, 0.70, 0.24)):
        d.ellipse(((cx - r) * w, cy * h - r * w, (cx + r) * w, cy * h + r * w), fill=top + (255,))
    shade = C.lgrad(w, h, top, bot, 90)
    shade.putalpha(im.getchannel('A'))
    return shade


def bolt(h):
    w = int(h * 0.55)
    pts = [(0.55, 0), (0.12, 0.55), (0.45, 0.55), (0.30, 1.0), (0.88, 0.38), (0.55, 0.38), (0.78, 0)]
    im = C.polygon([(x * w, y * h) for x, y in pts], (w, h), (255, 230, 70))
    return C.glow(im, 14, 1.2, (255, 240, 150))


class Weather(C.Reel):
    def __init__(self, home, away, league, side, pick, coef, when, chance, u=0.9375, drop=2.81, seed=12):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.fav, self.dog = (self.h, self.a) if side == 'h' else (self.a, self.h)
        self.pick, self.coef, self.when, self.chance = pick, coef, when, chance
        self.pos = {t.name: to_screen(*geo.albers_usa(*geo.CITIES[t.short])) for t in (self.h, self.a)}
        self.dur = self.b(12.2)
        self.cover_t = self.b(7.4)
        self._prep()

    def _prep(self):
        bg = C.vgrad(W, H, [(0, (10, 24, 52)), (1, NAVY)]).convert('RGBA')
        d = ImageDraw.Draw(bg)
        for i in range(-2, 14):                                   # сетка широт и долгот
            d.line((i * 110, 0, i * 110 - 160, H), fill=(40, 70, 110, 90), width=2)
            d.line((0, i * 150, W, i * 150 + 60), fill=(40, 70, 110, 90), width=2)
        ss = 2
        land = Image.new('L', (W * ss, H * ss), 0)
        lines = Image.new('L', (W * ss, H * ss), 0)
        dl, dn = ImageDraw.Draw(land), ImageDraw.Draw(lines)
        for name, rings in geo.states().items():
            for r in rings:
                pts = [((x - X0) * SC * ss, (MY + (y - Y0) * SC) * ss) for x, y in r]
                if max(p[0] for p in pts) < -50 or min(p[0] for p in pts) > W * ss + 50:
                    continue
                dl.polygon(pts, fill=255)
                dn.line(pts + pts[:1], fill=255, width=3 * ss)
        land = land.resize((W, H), Image.LANCZOS)
        lines = lines.resize((W, H), Image.LANCZOS)
        coast = land.filter(ImageFilter.GaussianBlur(14))
        glow = Image.new('RGBA', (W, H), (60, 160, 220, 0))
        glow.putalpha(coast.point(lambda v: int(min(255, v * 0.5))))
        bg.alpha_composite(glow)
        lg = C.lgrad(W, H, LAND2, LAND, 70)
        lg.putalpha(land)
        bg.alpha_composite(lg)
        bl = Image.new('RGBA', (W, H), BORDER + (0,))
        bl.putalpha(lines.point(lambda v: int(v * 0.55)))
        bg.alpha_composite(bl)
        self.map = bg
        self.cloud_d = cloud(420, True)
        self.cloud_l = cloud(300, False)
        self.bolt = bolt(230)
        self.pins = {t.name: self._pin(t) for t in (self.h, self.a)}

    def _pin(self, t):
        w = 190
        im = Image.new('RGBA', (w, w + 60), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.polygon([(w / 2 - 34, w - 30), (w / 2 + 34, w - 30), (w / 2, w + 50)], fill=WHITE + (255,))
        im.alpha_composite(C.ellipse(w, w, WHITE))
        C.put(im, t.emb(130), w / 2, w / 2)
        out = C.with_shadow(im, 12, 0.5, 10)
        lab = C.text(t.up, 'onest', 44, WHITE, 800, stroke=5, stroke_fill=INK)
        res = Image.new('RGBA', (max(out.width, lab.width), out.height + lab.height + 4), (0, 0, 0, 0))
        C.put(res, out, res.width / 2, out.height / 2)
        C.put(res, lab, res.width / 2, out.height + lab.height / 2 - 30)
        return res

    def card(self, team, good):
        w, h = 560, 290
        im = C.rrect(w, h, 30, (255, 255, 255), 240)
        hd = C.rrect(w, 86, 30, TV if good else (60, 66, 90))
        hd.alpha_composite(C.rrect(w, 40, 0, TV if good else (60, 66, 90)), (0, 46))
        im.alpha_composite(hd)
        C.put(im, C.text(team.up, 'onest', 46, WHITE, 800, max_w=w - 60), w / 2, 44)
        if good:
            C.put(im, sun_icon(48, 0, False), 120, 190)
        else:
            C.put(im, C.scale(self.cloud_d, 0.44), 120, 180)
            C.put(im, C.scale(self.bolt, 0.36), 128, 222)
        C.put(im, C.text('ЯСНО' if good else 'ГРОЗА', 'onest', 40, INK, 800), 360, 128)
        p = self.chance if good else 100 - self.chance
        C.put(im, C.text('%d%%' % p, 'onest', 96, TV if good else (120, 126, 150), 800), 360, 200)
        C.put(im, C.text('шанс на победу', 'onest', 26, (90, 100, 120), 600), 360, 262)
        return C.with_shadow(im, 18, 0.45, 12)

    def frame(self, t):
        u, D = self.u, self.drop
        # камера: медленный наезд на середину между городами
        fr = self.map.copy()
        (fx, fy), (dx_, dy_) = self.pos[self.fav.name], self.pos[self.dog.name]
        # булавки городов
        for i, tm in enumerate((self.h, self.a)):
            tp = self.b(-2 + i)
            if t >= tp:
                p = C.out_back(C.seg(t, tp, tp + 0.35), 2.0)
                x, y = self.pos[tm.name]
                pin = C.scale(self.pins[tm.name], max(0.05, p))
                C.put(fr, pin, x, y - 276 * max(0.05, p) + pin.height / 2)          # остриё булавки — в городе
        # погода
        if t >= D:
            k = C.out_cubic(C.seg(t, D, D + 0.6 * u))
            # солнце над фаворитом
            sx, sy = fx + 90, fy - 330
            fr = C.add_light(fr, C.radial(900, 900, (120, 80, 10), 255, 1.6), sx, sy, k)
            C.put(fr, C.scale(sun_icon(95, t), 0.4 + 0.6 * k), sx, sy, k)
            # туча, дождь и молнии над соперником
            cx, cy = dx_ - 200 + (1 - k) * 600, dy_ - 400
            rain = Image.new('RGBA', (440, 420), (0, 0, 0, 0))
            dr = ImageDraw.Draw(rain)
            rnd = np.random.default_rng(int(t * 30))
            for _ in range(60):
                x, y = rnd.uniform(0, 440), rnd.uniform(0, 420)
                dr.line((x, y, x - 14, y + 44), fill=(160, 200, 255, 170), width=4)
            C.put(fr, rain, cx, cy + 300, k)
            for n in range(0, 12):
                tb = self.b(n)
                if tb <= t < tb + 0.22 and n % 2 == 0:
                    q = 1 - C.seg(t, tb, tb + 0.22)
                    C.put(fr, self.bolt, cx + (30 if n % 4 else -50), cy + 230, q)
                    fr.alpha_composite(Image.new('RGBA', (W, H), (200, 220, 255, int(70 * q))))
            C.put(fr, self.cloud_d, cx, cy, k)
            C.put(fr, C.scale(self.cloud_l, 0.7), sx - 180 + 30 * math.sin(t * 0.5), sy + 60, 0.35 * k)
        # карточки городов — по очереди в нижнем слоте
        tc, te = self.b(2), self.b(6)
        if tc <= t < te + 0.4:
            for i, (tm, good) in enumerate(((self.fav, True), (self.dog, False))):
                t0 = tc + i * 2 * u
                t1 = tc + (i + 1) * 2 * u if i == 0 else te
                if not (t0 <= t < t1 + 0.4):
                    continue
                p = C.out_expo(C.seg(t, t0, t0 + 0.4))
                a = p * (1 - C.seg(t, t1, t1 + 0.3))
                cd = self.card(tm, good)
                x = 300 if i == 0 else W - 300
                C.put(fr, cd, x + (1 - p) * (-400 if i == 0 else 400), 1330, a)
        if t >= te:
            p = C.out_expo(C.seg(t, te + 0.2, te + 0.7))
            C.put(fr, self._final(t), W / 2, 980 + 60 * (1 - p), p)
        # ТВ-графика поверх
        self.tv(fr, t)
        z = 1.0 + 0.06 * C.in_out(C.seg(t, 0, self.dur))
        dx, dy = C.shake(t, D, 12, 0.35)
        fr = C.zoom(fr, z, W / 2, 900, dx=dx, dy=dy)
        return C.vignette(fr, 0.4)

    def tv(self, fr, t):
        u = self.u
        # значок канала
        bug = C.rrect(300, 74, 14, (0, 0, 0), 150)
        C.put(bug, C.ellipse(22, 22, (240, 40, 50), int(255 * (0.5 + 0.5 * math.sin(t * 6)))), 32, 37)
        C.put(bug, C.text('JARVIS ТВ', 'onest', 38, WHITE, 800), 168, 37)
        C.put(fr, bug, 40, 230, anchor='tl')
        C.put(fr, C.text(self.when, 'onest', 34, WHITE, 700, stroke=4, stroke_fill=INK), W - 40 - C.text(self.when, 'onest', 34, WHITE, 700, stroke=4, stroke_fill=INK).width, 248, anchor='tl')
        # нижняя плашка
        k = C.out_expo(C.seg(t, 0.05, 0.5))
        if True:
            lt = Image.new('RGBA', (W - 80, 150), (0, 0, 0, 0))
            lt.alpha_composite(C.rrect(W - 80, 150, 20, TV))
            lt.alpha_composite(C.rrect(250, 150, 20, SUN), (0, 0))
            lt.alpha_composite(C.rrect(40, 150, 0, SUN), (220, 0))
            C.put(lt, sun_icon(32, t, False), 125, 75)
            C.put(lt, C.text('ПОГОДА НА ЛЬДУ', 'onest', 58, WHITE, 800), 290 + 330, 52)
            C.put(lt, C.text('%s — %s' % (self.h.up, self.a.up), 'onest', 36, (220, 235, 255), 700, max_w=640), 290 + 330, 112)
            C.put(fr, lt, 40 - (1 - k) * 1100, 320, anchor='tl')
        if t >= self.b(9.5):
            p = C.out_expo(C.seg(t, self.b(9.5), self.b(9.5) + 0.5))
            C.put(fr, self._cta(), W / 2, 1360 + 40 * (1 - p), p)

    def _final(self, t):
        w, h = 940, 470
        im = C.rrect(w, h, 34, (255, 255, 255), 245)
        hd = C.rrect(w, 100, 34, TV)
        hd.alpha_composite(C.rrect(w, 50, 0, TV), (0, 50))
        im.alpha_composite(hd)
        C.put(im, C.text('ПРОГНОЗ НА МАТЧ', 'onest', 52, WHITE, 800), w / 2, 52)
        C.put(im, sun_icon(70, t, False), 150, 270)
        C.put(im, self.fav.emb(150), w - 140, 270)
        C.put(im, C.lines(self.pick.upper(), 'onest', 72, 520, INK, 800, gap=0.05, max_lines=2), w / 2 - 10, 230)
        pill = C.rrect(300, 90, 45, SUN)
        C.put(pill, C.text('КЭФ ' + C.fmt_k(self.coef), 'onest', 50, INK, 800), 150, 45)
        C.put(im, pill, w / 2 - 10, 380)
        return C.with_shadow(im, 20, 0.5, 14)

    def _cta(self):
        if not hasattr(self, '_ct'):
            w, h = 1000, 170
            im = C.rrect(w, h, 26, TV)
            C.put(im, C.tg_icon(120), 100, h / 2)
            C.put(im, C.text('ПРОГНОЗ НА КАЖДЫЙ МАТЧ', 'onest', 46, WHITE, 800), 570, 58)
            C.put(im, C.text('TELEGRAM ' + C.HANDLE, 'onest', 52, SUN, 800), 570, 118)
            self._ct = im
        return self._ct
