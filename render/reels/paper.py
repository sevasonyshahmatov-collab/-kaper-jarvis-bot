# -*- coding: utf-8 -*-
"""«Газета» — первая полоса «Вестника JARVIS» влетает с кручением, как в старом кино.

До дропа номер крутится и растёт, на дропе ложится на стол (толчок); дальше камера проходит по полосе:
заголовок → «фото» (эмблемы растром, как в газете) → блок «ПРОГНОЗ ДНЯ», который обводится красным маркером;
в колонках — короткая заметка (только то, что известно: кэф, наш шанс, время), врезка «ВЧЕРА: 3 ИЗ 3»;
в конце — наклейка «свежий номер каждый день · Telegram @jarvibet».
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from reels import core as C
from reels.core import W, H

PAPER = (241, 236, 224)
INK = (26, 24, 22)
RED = (205, 34, 40)
PW, PH = 1000, 1500


class Paper(C.Reel):
    def __init__(self, home, away, league, side, pick, coef, chance, when, headline, story, yesterday, issue, date_line,
                 u=0.9375, drop=2.81, seed=71):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.fav = self.h if side == 'h' else self.a
        self.pick, self.coef, self.chance, self.when = pick, coef, chance, when
        self.headline, self.story, self.yesterday = headline, story, yesterday
        self.issue, self.date_line = issue, date_line
        self.dur = self.b(10.5)
        self.cover_t = self.b(6.2)
        self._prep()

    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        # стол
        bg = C.vgrad(W, H, [(0, (52, 46, 42)), (1, (20, 18, 17))]).convert('RGBA')
        self.bg = C.add_light(bg, C.radial(1600, 1500, (70, 60, 50), 255, 1.5), W / 2, 820, 1.0)
        self.page = self._page(rnd)
        self.box_xy = (self.bx0 + self.bw / 2, self.by0 + self.bh / 2)

    def halftone(self, emb, step=8):
        g = ImageOps.grayscale(Image.alpha_composite(Image.new('RGBA', emb.size, (255, 255, 255, 255)), emb).convert('RGB'))
        g = ImageOps.autocontrast(g, cutoff=3).point(lambda v: int(255 * (v / 255) ** 0.7))
        a = np.asarray(emb.getchannel('A'), np.float32) / 255
        arr = 1 - np.asarray(g, np.float32) / 255
        im = Image.new('RGBA', emb.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for y in range(0, emb.height, step):
            for x in range(0, emb.width, step):
                v = arr[y, x] * a[y, x] * 0.9 + a[y, x] * 0.04
                r = step * 0.62 * math.sqrt(max(0.0, v))
                if r > 0.6:
                    d.ellipse((x - r, y - r, x + r, y + r), fill=INK + (235,))
        return im

    def _page(self, rnd):
        pg = Image.new('RGBA', (PW, PH), PAPER + (255,))
        arr = np.asarray(pg, np.int16).copy()
        arr[..., :3] += (rnd.normal(0, 4, (PH, PW)) - np.linspace(0, 10, PH)[:, None]).astype(np.int16)[..., None]
        pg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
        d = ImageDraw.Draw(pg)
        m = 40
        C.put(pg, C.text(self.date_line, 'tenor', 22, INK, 400, track=0.12, max_w=PW - 2 * m), PW / 2, 46)
        d.line((m, 66, PW - m, 66), fill=INK + (255,), width=2)
        C.put(pg, C.text('ВЕСТНИК JARVIS', 'prata', 104, INK, 400, track=0.02, max_w=PW - 2 * m), PW / 2, 140)
        d.line((m, 212, PW - m, 212), fill=INK + (255,), width=5)
        d.line((m, 220, PW - m, 220), fill=INK + (255,), width=2)
        C.put(pg, C.text('ХОККЕЙ · ПРОГНОЗЫ · ИТОГИ', 'tenor', 22, INK, 400, track=0.3), PW / 2, 240)
        # заголовок
        y = 270
        for line in self.headline:
            tx = C.text(line, 'osw', 150, INK, 700, max_w=PW - 2 * m)
            C.put(pg, tx, PW / 2, y + tx.height / 2)
            y += tx.height + 6
        deck = C.lines(self.story[0], 'prata', 34, PW - 2 * m, INK, 400, gap=0.22, align='c', max_lines=3)
        C.put(pg, deck, PW / 2, y + 20 + deck.height / 2)
        y += deck.height + 50
        d.line((m, y, PW - m, y), fill=INK + (255,), width=2)
        # «фото» и блок прогноза
        py0 = y + 20
        ph_w, ph_h = 600, 400
        photo = Image.new('RGBA', (ph_w, ph_h), (226, 220, 206, 255))
        C.put(photo, self.halftone(self.h.emb(250)), ph_w / 2 - 150, ph_h / 2)
        C.put(photo, self.halftone(self.a.emb(250)), ph_w / 2 + 150, ph_h / 2)
        C.put(photo, C.text('VS', 'osw', 60, INK, 700), ph_w / 2, ph_h / 2)
        pg.alpha_composite(photo, (m, py0))
        C.put(pg, C.text('%s принимает «%s» · %s МСК' % (self.h.short, self.a.short, self.when), 'corm', 28, INK, 500,
                         max_w=ph_w), m, py0 + ph_h + 12, anchor='tl')
        bx0, by0, bw, bh = m + ph_w + 30, py0, PW - 2 * m - ph_w - 30, ph_h
        d.rectangle((bx0, by0, bx0 + bw, by0 + bh), outline=INK + (255,), width=4)
        d.rectangle((bx0, by0, bx0 + bw, by0 + 64), fill=INK + (255,))
        C.put(pg, C.text('ПРОГНОЗ ДНЯ', 'osw', 40, PAPER, 700, track=0.06), bx0 + bw / 2, by0 + 32)
        C.put(pg, C.lines(self.pick.upper(), 'osw', 58, bw - 30, INK, 700, gap=0.02, max_lines=3), bx0 + bw / 2, by0 + 160)
        C.put(pg, C.text('КЭФ ' + C.fmt_k(self.coef), 'osw', 64, RED, 700), bx0 + bw / 2, by0 + 270)
        C.put(pg, C.text('шанс %d%%' % self.chance, 'prata', 36, INK, 400), bx0 + bw / 2, by0 + 345)
        self.bx0, self.by0, self.bw, self.bh = bx0, by0, bw, bh
        # колонки текста
        y = py0 + ph_h + 70
        d.line((m, y - 14, PW - m, y - 14), fill=INK + (255,), width=1)
        cw = (PW - 2 * m - 40) / 3
        body = ' '.join(self.story[1:])
        words = body.split()
        f = C.font('prata', 25)
        col, cy, line = 0, y, ''
        rows = []
        for wd in words:
            t = (line + ' ' + wd).strip()
            if f.getlength(t) <= cw - 6:
                line = t
            else:
                rows.append(line)
                line = wd
        rows.append(line)
        per = max(1, math.ceil(len(rows) / 2))
        for i, r in enumerate(rows):
            c = i // per
            if c > 1:
                break
            d.text((m + c * (cw + 20), y + (i % per) * 34), r, font=f, fill=INK + (255,))
        # врезка «вчера»
        x3 = m + 2 * (cw + 20)
        d.rectangle((x3, y, x3 + cw, y + 300), fill=(226, 220, 206, 255), outline=INK + (255,), width=2)
        C.put(pg, C.text('ВЧЕРА', 'osw', 40, INK, 700), x3 + cw / 2, y + 40)
        C.put(pg, C.text(self.yesterday[0], 'osw', 76, RED, 700), x3 + cw / 2, y + 115)
        for i, s in enumerate(self.yesterday[1:]):
            C.put(pg, C.text(s, 'prata', 22, INK, 400, max_w=cw - 20), x3 + cw / 2, y + 180 + i * 34)
        d.line((m, PH - 60, PW - m, PH - 60), fill=INK + (255,), width=2)
        C.put(pg, C.text('Свежий номер — каждый день в Telegram ' + C.HANDLE, 'tenor', 24, INK, 400, track=0.05), PW / 2, PH - 35)
        # тень сгиба посередине
        fold = C.lgrad(PW, 60, (0, 0, 0), (0, 0, 0), 90, 0, 26)
        pg.alpha_composite(fold, (0, PH // 2 - 30))
        return pg

    def cam(self, t):
        """→ (масштаб полосы, центр полосы в кадре x, y, поворот)."""
        u, D = self.u, self.drop
        fit = 0.98 * W / PW
        if t < D:
            k = C.in_cubic(C.seg(t, 0, D))
            return 0.04 + (fit - 0.04) * k, W / 2, 900, (1 - k) * 900 + 4
        keys = [(D, fit, 0.5, 0.5), (self.b(1.5), fit, 0.5, 0.5),
                (self.b(2.5), fit * 1.45, 0.5, 0.17),                           # заголовок
                (self.b(3.8), fit * 1.45, 0.5, 0.17),
                (self.b(4.6), fit * 1.7, (self.bx0 + self.bw / 2) / PW, (self.by0 + self.bh / 2) / PH),   # блок прогноза
                (self.b(6.8), fit * 1.7, (self.bx0 + self.bw / 2) / PW, (self.by0 + self.bh / 2) / PH),
                (self.b(7.6), fit, 0.5, 0.5), (self.b(20), fit, 0.5, 0.5)]
        for (t0, s0, x0, y0), (t1, s1, x1, y1) in zip(keys, keys[1:]):
            if t0 <= t < t1:
                q = C.in_out(C.seg(t, t0, t1))
                s, fx, fy = C.lerp(s0, s1, q), C.lerp(x0, x1, q), C.lerp(y0, y1, q)
                break
        else:
            s, fx, fy = fit, 0.5, 0.5
        # точку полосы (fx, fy) ставим в центр кадра, но край полосы не уводим внутрь кадра сверх меры
        cx = W / 2 - (fx - 0.5) * PW * s
        cy = 860 - (fy - 0.5) * PH * s
        return s, cx, cy, 4 * (1 - C.out_cubic(C.seg(t, D, D + 0.4))) + 1.2

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        pg = self.page
        if t >= self.b(5):                                            # обводка маркером
            p = C.out_cubic(C.seg(t, self.b(5), self.b(5.8)))
            pg = pg.copy()
            d = ImageDraw.Draw(pg)
            cx, cy = self.box_xy
            rx, ry = self.bw / 2 + 34, self.bh / 2 + 30
            angs = np.linspace(-2.4, -2.4 + 2 * math.pi * 1.08 * p, 80)
            pts = [(cx + rx * math.cos(a) + 6 * math.sin(3 * a), cy + ry * math.sin(a)) for a in angs]
            if len(pts) > 1:
                d.line(pts, fill=RED + (220,), width=12, joint='curve')
        s, cx, cy, rot = self.cam(t)
        img = C.scale(pg, s)
        img = C.rotate(img, rot) if abs(rot) > 0.05 else img
        if t < D:
            k = C.seg(t, 0, D)
            C.put(fr, C.shadow(img, int(10 + 30 * k), 0.6), cx + 20, cy + 40)
        else:
            C.put(fr, C.shadow(img, 34, 0.6), cx + 18, cy + 36)
        C.put(fr, img, cx, cy)
        if t >= self.b(7.8):                                           # наклейка-подписка
            q = C.seg(t, self.b(7.8), self.b(7.8) + 0.16)
            st = self._sticker()
            C.put(fr, C.scale(st, 1.4 - 0.4 * q), W / 2 - 40, 1360, min(1.0, q * 2.5))
        dx, dy = C.shake(t, D, 18, 0.4)
        sx, sy = C.shake(t, self.b(7.8) + 0.16, 8, 0.25)
        fr = C.zoom(fr, 1.0, dx=dx + sx, dy=dy + sy)
        if D <= t < D + 0.12:
            fr = Image.blend(fr.convert('RGB'), Image.new('RGB', (W, H), (255, 250, 240)), 0.5 * (1 - C.seg(t, D, D + 0.12)))
        return C.vignette(fr, 0.5)

    def _sticker(self):
        if not hasattr(self, '_st'):
            w, h = 760, 230
            im = C.rrect(w, h, 26, (255, 214, 64))
            C.put(im, C.text('СВЕЖИЙ НОМЕР — КАЖДЫЙ ДЕНЬ', 'osw', 48, INK, 700), w / 2, 62)
            pl = C.rrect(640, 100, 50, C.TG_BLUE)
            C.put(pl, C.tg_icon(76, (255, 255, 255), C.TG_BLUE), 60, 50)
            C.put(pl, C.text('TELEGRAM ' + C.HANDLE, 'osw', 50, (255, 255, 255), 700), 360, 50)
            C.put(im, pl, w / 2, 160)
            self._st = C.with_shadow(C.rotate(im, -5), 16, 0.45, 12)
        return self._st
