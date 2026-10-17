# -*- coding: utf-8 -*-
"""«Пак дня» — открытие пака, как в FIFA/FC Ultimate Team (walkout).

До дропа — золотой пак в лучах, на каждую долю — подсказка (лига → город → кэф), пак дрожит и надрывается;
на дропе пак рвётся, вспышка, из него вылетает чёрно-золотая карточка клуба с голографическим бликом
(«рейтинг» — шанс по кэфу, поля — кэф, шанс, дата, время, соперник, лига); через 4 доли карточка
переворачивается — на обороте прогноз; в конце — «новый пак каждый день · Telegram @jarvibet».
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels.core import W, H

GOLD = (236, 190, 92)
GOLD_HI = (255, 232, 160)
GOLD_LO = (150, 104, 34)
INK = (14, 12, 10)


def _card_shape(w, h):
    c = 0.10 * w
    return [(c, 0), (w - c, 0), (w, c), (w, h - 0.17 * h), (w / 2, h), (0, h - 0.17 * h), (0, c)]


def _mask(w, h, inset=0, ss=3):
    m = Image.new('L', (w * ss, h * ss), 0)
    pts = _card_shape(w - 2 * inset, h - 2 * inset)
    ImageDraw.Draw(m).polygon([((x + inset) * ss, (y + inset) * ss) for x, y in pts], fill=255)
    return m.resize((w, h), Image.LANCZOS)


def _gold(w, h, angle=-60):
    """Металлическое золото: несколько полос света по диагонали."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    p = (x * math.cos(math.radians(angle)) + y * math.sin(math.radians(angle))) / max(w, h)
    k = 0.55 + 0.25 * np.sin(p * 9.0) + 0.2 * np.sin(p * 23.0 + 1.3)
    k = np.clip(k, 0, 1)[..., None]
    lo, hi = np.array(GOLD_LO, np.float32), np.array(GOLD_HI, np.float32)
    arr = lo + (hi - lo) * k
    return Image.fromarray(arr.astype(np.uint8), 'RGB').convert('RGBA')


class Pack(C.Reel):
    def __init__(self, home, away, league, pick, coef, when, city, side='h', u=0.8696, drop=3.478, seed=11):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.team = self.h if side == 'h' else self.a
        self.opp = self.a if side == 'h' else self.h
        self.league = 'НХЛ' if str(league).upper() == 'NHL' else 'КХЛ'
        self.pick, self.coef, self.when, self.city = pick, coef, when, city
        self.chance = int(round(100 / coef))
        self.dur = self.b(11.2)
        self.cover_t = self.b(6.5)
        self._prep()

    # ── заготовки ──
    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        # фон: глубокий тёмный с тёплым центром
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.45) / H) ** 2)
        base = np.array((8, 9, 14), np.float32) + np.array((70, 48, 18), np.float32) * np.clip(1 - d * 2.1, 0, 1)[..., None] ** 2
        self.bg = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        # лучи
        R = 1500
        rays = Image.new('L', (R, R), 0)
        dr = ImageDraw.Draw(rays)
        for i in range(18):
            a0 = i * 20 + rnd.uniform(-4, 4)
            wdt = rnd.uniform(3, 8)
            dr.pieslice((0, 0, R, R), a0, a0 + wdt, fill=int(rnd.uniform(60, 140)))
        rays = rays.filter(ImageFilter.GaussianBlur(10))
        fall = C.radial(R, R, (255, 255, 255), 255, 1.2).getchannel('A')
        rays = Image.fromarray((np.asarray(rays, np.float32) * np.asarray(fall, np.float32) / 255).astype(np.uint8), 'L')
        self.rays = rays
        # пылинки
        self.dust = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(3, 11), rnd.uniform(15, 60), rnd.uniform(0, 6.28))
                     for _ in range(70)]
        self.dot = {s: C.radial(s * 4, s * 4, (255, 226, 160), 255, 1.6) for s in range(3, 12)}
        self.pack = self._pack()
        self.front = self._front()
        self.back = self._back()
        cw, ch = self.front.size
        self.cmask = _mask(cw, ch)
        # голографическая радуга (широкая полоса, сдвигается по времени)
        hw = cw * 3
        xx = np.linspace(0, 6 * math.pi, hw)
        rgb = np.stack([np.sin(xx) * 0.5 + 0.5, np.sin(xx + 2.1) * 0.5 + 0.5, np.sin(xx + 4.2) * 0.5 + 0.5], -1) * 255
        self.holo = Image.fromarray(rgb[None, :, :].repeat(ch, 0).astype(np.uint8), 'RGB')
        self.burst = C.radial(1400, 1400, (255, 236, 190), 255, 1.8)
        self.flare = C.radial(1500, 90, (255, 240, 200), 255, 1.4)

    def _pack(self):
        w, h = 560, 820
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        body = _gold(w, h)
        m = Image.new('L', (w, h), 0)
        d = ImageDraw.Draw(m)
        tooth = 14
        pts = []
        for i in range(0, w + 1, tooth):                               # «гофра» сверху и снизу
            pts.append((i, 0 if (i // tooth) % 2 == 0 else 14))
        for i in range(w, -1, -tooth):
            pts.append((i, h if (i // tooth) % 2 == 0 else h - 14))
        d.polygon(pts, fill=255)
        im.paste(body, (0, 0), m)
        d = ImageDraw.Draw(im)
        d.rectangle((0, 40, w, 46), fill=GOLD_LO + (255,))
        d.rectangle((0, h - 46, w, h - 40), fill=GOLD_LO + (255,))
        # медальон
        md = C.ellipse(300, 300, INK)
        C.put(im, md, w / 2, h * 0.42)
        ring = Image.new('RGBA', (300, 300), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((8, 8, 292, 292), outline=GOLD_HI + (255,), width=6)
        C.put(im, ring, w / 2, h * 0.42)
        C.put(im, C.text('J', 'dela', 190, GOLD_HI), w / 2, h * 0.42)
        C.put(im, C.text('JARVIS', 'unb', 64, INK, 800, track=0.12), w / 2, h * 0.70)
        C.put(im, C.text('ПАК ДНЯ · %s' % self.league, 'mono', 30, INK, 700, track=0.2), w / 2, h * 0.77)
        return im

    def _front(self):
        w, h = 620, 900
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        # чёрная основа с узором и золотой каймой
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        pat = 0.5 + 0.5 * np.sin((x + y) / 9.0)
        dark = np.array((18, 16, 14), np.float32) + np.array((16, 13, 8), np.float32) * (pat ** 6)[..., None]
        dark += np.array((60, 44, 14), np.float32) * np.clip(1 - np.sqrt(((x - w / 2) / w) ** 2 + ((y - h * 0.35) / h) ** 2) * 2.2, 0, 1)[..., None]
        base = Image.fromarray(np.clip(dark, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        gold = _gold(w, h, -35)
        im.paste(gold, (0, 0), _mask(w, h))
        im.paste(base, (0, 0), _mask(w, h, 9))
        inner = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ol = _mask(w, h, 22).filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 40 else 0)
        inner.paste(Image.new('RGBA', (w, h), GOLD + (150,)), (0, 0), ol)
        im.alpha_composite(inner)
        # «рейтинг» и позиция
        C.put(im, C.text(str(self.chance), 'dela', 112, GOLD_HI), 142, 168)
        C.put(im, C.text('ШАНС %', 'mono', 24, GOLD, 700, track=0.12), 142, 240)
        C.put(im, C.text(self.league, 'unb', 40, GOLD_HI, 800), 142, 296)
        e = self.team.emb(290)
        C.put(im, C.glow(e, 26, 0.9, GOLD), w / 2 + 95, 250)
        # имя
        name = C.text(self.team.up, 'dela', 92, GOLD_HI, max_w=w - 90)
        C.put(im, name, w / 2, 495)
        d = ImageDraw.Draw(im)
        d.line((70, 556, w - 70, 556), fill=GOLD + (200,), width=3)
        # поля 2×2 (значение крупно, подпись мелко — как на карточках FUT) и соперник
        dd = self.when.split('·')
        day = dd[0].strip().split()[-1]
        tm = dd[1].strip().split()[0] if len(dd) > 1 else ''
        rows = [(C.fmt_k(self.coef), 'КЭФ'), ('%d%%' % self.chance, 'ШАНС'), (day, 'ДАТА'), (tm, 'МСК')]
        for i, (v, k) in enumerate(rows):
            x0 = 80 if i % 2 == 0 else w / 2 + 40
            cy = 608 + (i // 2) * 66
            vv = C.text(v, 'unb', 40, GOLD_HI, 800)
            kv = C.text(k, 'mono', 26, GOLD, 600, track=0.1)
            C.put(im, vv, x0, cy - vv.height / 2, anchor='tl')
            C.put(im, kv, x0 + vv.width + 16, cy - kv.height / 2 + 4, anchor='tl')
        d.line((w / 2, 585, w / 2, 700), fill=GOLD + (120,), width=2)
        vs = C.text('ПРОТИВ  ' + self.opp.up, 'mono', 28, GOLD, 700, track=0.12, max_w=w - 160)
        C.put(im, vs, w / 2, 752)
        return im

    def _back(self):
        w, h = self.front.size
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        gold = _gold(w, h, 35)
        im.paste(gold, (0, 0), _mask(w, h))
        dark = Image.new('RGBA', (w, h), (16, 14, 12, 255))
        im.paste(dark, (0, 0), _mask(w, h, 9))
        C.put(im, C.text('ПРОГНОЗ', 'mono', 36, GOLD, 700, track=0.45), w / 2, 120)
        e1, e2 = self.h.emb(150), self.a.emb(150)
        C.put(im, e1, w / 2 - 120, 260)
        C.put(im, e2, w / 2 + 120, 260)
        C.put(im, C.text('—', 'unb', 50, GOLD), w / 2, 260)
        blk = C.lines(self.pick.upper(), 'dela', 84, w - 100, GOLD_HI, gap=0.08, max_lines=3)
        C.put(im, blk, w / 2, 470)
        pill = C.rrect(330, 104, 52, GOLD)
        C.put(pill, C.text('КЭФ ' + C.fmt_k(self.coef), 'unb', 50, INK, 900), 165, 52)
        C.put(im, pill, w / 2, 640)
        C.put(im, C.text('%s · %s' % (self.when.upper(), self.league), 'mono', 26, GOLD, 600, track=0.04, max_w=w - 120), w / 2, 740)
        return im

    # ── кадр ──
    def _holo(self, card, t, k=0.28):
        cw, ch = card.size
        off = int((t * 260) % (cw * 2))
        band = self.holo.crop((off, 0, off + cw, ch)).convert('RGBA')
        # полоса блика по диагонали
        y, x = np.mgrid[0:ch, 0:cw].astype(np.float32)
        pos = ((t * 0.55) % 1.6 - 0.3) * (cw + ch)
        sweep = np.exp(-(((x + y * 0.6) - pos) / 60.0) ** 2)
        al = (np.asarray(self.cmask, np.float32) / 255) * (k + 0.55 * sweep)
        band.putalpha(Image.fromarray((np.clip(al, 0, 1) * 255).astype(np.uint8), 'L'))
        out = card.copy()
        lay = Image.blend(Image.new('RGBA', card.size, (0, 0, 0, 0)), band, 1.0)
        out = Image.alpha_composite(out, Image.composite(lay, Image.new('RGBA', card.size, (0, 0, 0, 0)), band.getchannel('A')))
        # белый блик сверху
        sw = Image.new('RGBA', card.size, (255, 255, 255, 0))
        sw.putalpha(Image.fromarray((np.clip(sweep * 0.45 * np.asarray(self.cmask, np.float32) / 255, 0, 1) * 255).astype(np.uint8), 'L'))
        out.alpha_composite(sw)
        return out

    def _flip(self, t):
        """Угол поворота карточки (0 — лицо, 180 — оборот)."""
        a, b = self.b(4), self.b(4.6)
        return 180 * C.in_out(C.seg(t, a, b))

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        # лучи вращаются; ярче после дропа
        ray_k = 0.35 + 0.25 * C.seg(t, 0, D) + 0.4 * (1 - C.seg(t, D, D + 2 * u)) * (t >= D)
        if t >= D:
            ray_k = max(ray_k, 0.6)
        rot = t * 6
        rays = self.rays.rotate(rot, Image.BILINEAR)
        rl = Image.new('RGBA', rays.size, GOLD_HI + (0,))
        rl.putalpha(rays.point(lambda v, k=ray_k: int(v * k)))
        fr = C.add_light(fr, rl, W / 2, 900, 1.0)
        # пылинки
        for (x0, y0, s, sp, ph) in self.dust:
            y = (y0 - t * sp) % H
            x = x0 + 20 * math.sin(t * 0.7 + ph)
            fr = C.put(fr, self.dot[int(s)], x, y, 0.35 + 0.25 * math.sin(t * 2 + ph))
        cy = 860
        # ── до дропа: пак ──
        if t < D + 0.6 * u:
            pk = self.pack
            bob = 10 * math.sin(t * 2.4)
            sh = 0.0
            for n in (-3, -2, -1):
                dx, _ = C.shake(t, self.b(n), 10 + 4 * (n + 3), 0.4)
                sh += dx
            tear = C.seg(t, self.b(-0.5), D)          # надрыв сверху в последние полдоли
            if t < D:
                glow_k = 0.25 + 0.75 * C.seg(t, 0, D)
                gl = C.glow(pk, 40, glow_k * 1.2, GOLD_HI)
                fr = C.add_light(fr, C.fade(gl, 0.35 * glow_k), W / 2 + sh, cy + bob, 1.0)
                if tear <= 0:
                    C.put(fr, pk, W / 2 + sh, cy + bob)
                else:
                    cut = 120
                    top = pk.crop((0, 0, pk.width, cut))
                    bot = pk.crop((0, cut, pk.width, pk.height))
                    C.put(fr, bot, W / 2 + sh, cy + bob + cut / 2)
                    top = C.rotate(top, -18 * C.out_cubic(tear))
                    C.put(fr, top, W / 2 + sh + 120 * C.out_cubic(tear), cy + bob - pk.height / 2 + cut / 2 - 160 * C.out_cubic(tear))
                    fl = C.fade(self.flare, tear)
                    fr = C.add_light(fr, fl, W / 2, cy + bob - pk.height / 2 + cut + 6, 1.0)
            else:                                         # остаток пака уходит вниз
                k = C.seg(t, D, D + 0.6 * u)
                bot = pk.crop((0, 120, pk.width, pk.height))
                C.put(fr, bot, W / 2, cy + 60 + 900 * C.in_cubic(k), 1 - k)
            # подсказки
            clues = [('ЛИГА', self.league), ('ГОРОД', self.city.upper()), ('КЭФ', C.fmt_k(self.coef))]
            i = self._clue_idx(t)
            if i >= 0 and t < D + 0.3 * u:
                t0 = self.b(-3 + i)
                p = C.out_expo(C.seg(t, t0, t0 + 0.3 * u))
                chip = C.scale(self._chip(*clues[i]), 1.18 - 0.18 * p)
                C.put(fr, chip, W / 2, 1360, p * (1 - C.seg(t, D, D + 0.3 * u)))
                # точки-счётчик подсказок
                for j in range(3):
                    C.put(fr, C.ellipse(18, 18, GOLD_HI if j <= i else (90, 74, 40)), W / 2 - 40 + 40 * j, 1490 - 20,
                          1 - C.seg(t, D, D + 0.3 * u))
            hook_a = 1 - C.seg(t, self.b(-0.6), self.b(-0.3))
            C.put(fr, C.text('ОТКРЫВАЕМ', 'mono', 40, GOLD, 700, track=0.5), W / 2, 300, hook_a)
            C.put(fr, C.text('ПАК ДНЯ', 'dela', 120, GOLD_HI), W / 2, 385, hook_a)
        # ── после дропа: карточка ──
        if t >= D:
            p = C.out_expo(C.seg(t, D, D + 0.9 * u))
            ang = self._flip(t)
            card = self.front if ang < 90 else self.back
            card = self._holo(card, t, 0.16 if ang < 90 else 0.10)
            # к финалу карточка уменьшается и уезжает вверх
            q = C.in_out(C.seg(t, self.b(8), self.b(8.8)))
            s = (1.35 - 0.35 * p) * (1 - 0.32 * q)
            ycard = lerp_y = cy - 40 * (1 - p) + (-150) * q
            sx = abs(math.cos(math.radians(ang)))
            sway = 2.5 * math.sin(t * 1.3) * (1 - q)
            c2 = card.resize((max(2, int(card.width * s * max(0.02, sx))), int(card.height * s)), Image.BILINEAR)
            c2 = C.rotate(c2, sway)
            # отражение на полу
            refl = c2.transpose(Image.FLIP_TOP_BOTTOM)
            rm = Image.linear_gradient('L').resize(refl.size).point(lambda v: int(max(0, 150 - v) * 0.6))
            ra = Image.fromarray((np.asarray(refl.getchannel('A'), np.float32) * np.asarray(rm, np.float32) / 255).astype(np.uint8))
            refl.putalpha(ra)
            C.put(fr, refl, W / 2, ycard + c2.height - 30, 0.8 * p)
            # свечение и карточка
            fr = C.add_light(fr, C.fade(self.burst, 0.55 * (1 - C.seg(t, D, D + 2 * u)) + 0.18), W / 2, ycard, 1.0)
            C.put(fr, C.shadow(c2, 30, 0.6), W / 2, ycard + 30)
            C.put(fr, c2, W / 2, ycard)
            # заголовок над карточкой
            if t < self.b(8):
                ha = C.seg(t, D + 0.4 * u, D + 1.0 * u) * (1 - C.seg(t, self.b(3.8), self.b(4)))
                C.put(fr, C.text('ВЫПАЛ КЛУБ ДНЯ', 'mono', 40, GOLD, 700, track=0.4), W / 2, 300, ha)
                hb = C.seg(t, self.b(4.5), self.b(5)) * (1 - C.seg(t, self.b(7.8), self.b(8)))
                C.put(fr, C.text('ПЕРЕВОРАЧИВАЕМ', 'mono', 40, GOLD, 700, track=0.4), W / 2, 300, hb)
            # финал: подписка
            if t >= self.b(8.3):
                k = C.out_expo(C.seg(t, self.b(8.3), self.b(9)))
                plate = self._cta()
                C.put(fr, plate, W / 2, 1290 + 60 * (1 - k), k)
        # вспышка на дропе
        fl = 1 - C.seg(t, D, D + 0.45 * u) if t >= D else 0
        if fl > 0:
            fr.alpha_composite(Image.new('RGBA', (W, H), (255, 246, 220, int(255 * fl ** 1.5))))
        # толчок камеры
        z = 1.0 + 0.04 * (1 - C.seg(t, D, D + 0.6 * u)) * (t >= D) + 0.015 * C.seg(t, 0, D)
        dx, dy = C.shake(t, D, 22, 0.5)
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        fr = C.vignette(fr, 0.6)
        return C.grain(fr, t, 5)

    def _clue_idx(self, t):
        idx = -1
        for i in range(3):
            if t >= self.b(-3 + i):
                idx = i
        return idx

    def _chip(self, k, v):
        key = ('chip', k, v)
        if not hasattr(self, '_chips'):
            self._chips = {}
        if key not in self._chips:
            kv = C.text(k, 'mono', 34, GOLD, 700, track=0.3)
            vv = C.text(v, 'dela', 84, GOLD_HI)
            w = max(kv.width, vv.width) + 120
            im = C.rrect(w, 190, 34, (20, 17, 12), 230, outline=GOLD, width=3)
            C.put(im, kv, w / 2, 52)
            C.put(im, vv, w / 2, 122)
            self._chips[key] = im
        return self._chips[key]

    def _cta(self):
        if not hasattr(self, '_cta_im'):
            w, h = 900, 250
            im = C.rrect(w, h, 40, (16, 14, 11), 235, outline=GOLD, width=3)
            C.put(im, C.tg_icon(130), 110, h / 2)
            C.put(im, C.text('НОВЫЙ ПАК — КАЖДЫЙ ДЕНЬ', 'mono', 30, GOLD, 700, track=0.08), 190 + 340, 82, anchor='c')
            C.put(im, C.text('TELEGRAM', 'dela', 66, GOLD_HI), 190 + 340, 150)
            C.put(im, C.text(C.HANDLE, 'unb', 40, (255, 255, 255), 700), 190 + 340, 208)
            self._cta_im = im
        return self._cta_im
