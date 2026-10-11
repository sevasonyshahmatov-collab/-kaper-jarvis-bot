# -*- coding: utf-8 -*-
"""«Экспресс дня» — чек печатается из термопринтера.

Внизу кадра — щель принтера, бумага ползёт вверх рывками: шапка до дропа, на дропе и дальше через каждые
2 доли — матч (эмблемы печатаются точками, как на настоящем чеке), сверху растёт общий кэф (×1.89 → ×3.44 → ×6.36).
Потом «ИТОГО», штрихкод, чек отрывается и поднимается в центр; на стопе трека — «ЗАЙДЁТ?», на втором ударе —
красная печать «ЭКСПРЕСС ДНЯ» и подписка в Telegram.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from reels import core as C
from reels.core import W, H

PAPER = (246, 244, 238)
INK = (34, 34, 40)
RED = (214, 40, 46)
GOLD = (255, 200, 70)
PW = 780          # ширина чека
SLOT = 1420       # линия щели принтера


class Coupon(C.Reel):
    def __init__(self, legs, date, league='KHL', u=60 / 95, drop=2.52, stop=10.10, hit2=12.63, seed=5):
        """legs = [(хозяева, гости, 'П1', 'победа Адмирала', 1.89, '10:00'), ...]"""
        super().__init__(u, drop, seed)
        self.legs = [(C.match(h, a, league), p, d, k, tm) for h, a, p, d, k, tm in legs]
        self.date, self.league = date, ('НХЛ' if str(league).upper() == 'NHL' else 'КХЛ')
        self.stop, self.hit2 = stop, hit2
        self.total = 1.0
        for lg in self.legs:
            self.total *= lg[3]
        self.dur = hit2 + 6 * u
        self.cover_t = hit2 + 3 * u
        self._prep()

    # ── чек: строки с временем печати ──
    def _prep(self):
        u, D = self.u, self.drop
        rows = []           # (картинка строки, время печати)
        mono = lambda s, sz=34, wg=700, al='l': C.text(s, 'mono', sz, INK, wg)

        def line(parts, h=58):
            im = Image.new('RGBA', (PW, h), (0, 0, 0, 0))
            for s, x, sz, wg, al in parts:
                t = C.text(s, 'mono', sz, INK, wg)
                if al == 'r':
                    C.put(im, t, PW - 50 - t.width, h / 2 - t.height / 2, anchor='tl')
                elif al == 'c':
                    C.put(im, t, PW / 2, h / 2)
                else:
                    C.put(im, t, x, h / 2 - t.height / 2, anchor='tl')
            return im

        def sep(ch='-', h=40):
            im = Image.new('RGBA', (PW, h), (0, 0, 0, 0))
            C.put(im, C.text(ch * 30, 'mono', 30, INK, 500), PW / 2, h / 2)
            return im

        hdr_t = [0.25, 0.55, 0.85, 1.15, 1.5]
        rows.append((Image.new('RGBA', (PW, 40), (0, 0, 0, 0)), 0.0))
        rows.append((line([('J A R V I S', 0, 64, 800, 'c')], 96), hdr_t[0]))
        rows.append((line([('ПРОГНОЗ НА ХОККЕЙ · ' + self.league, 0, 30, 600, 'c')], 50), hdr_t[1]))
        rows.append((line([(self.date, 50, 30, 600, 'l'), ('ЭКСПРЕСС', 0, 30, 800, 'r')], 50), hdr_t[2]))
        rows.append((sep('='), hdr_t[3]))
        for i, (tm_, p, d, k, tm) in enumerate(self.legs):
            t0 = self.b(2 * i)
            h, a = tm_
            blk = Image.new('RGBA', (PW, 176), (0, 0, 0, 0))
            e1, e2 = self._dither(h.emb(84)), self._dither(a.emb(84))
            C.put(blk, e1, 50, 18, anchor='tl')
            C.put(blk, e2, 50 + 92, 18, anchor='tl')
            C.put(blk, C.text('%d' % (i + 1), 'mono', 30, INK, 800), PW - 70, 40)
            nm = C.text('%s — %s' % (h.up, a.up), 'mono', 32, INK, 800, max_w=PW - 330)
            C.put(blk, nm, 250, 36 - nm.height / 2 + 6, anchor='tl')
            C.put(blk, C.text(tm + ' МСК', 'mono', 28, INK, 500), 250, 74, anchor='tl')
            C.put(blk, C.text(p + ' · ' + d, 'mono', 32, INK, 700, max_w=PW - 330), 50, 128, anchor='tl')
            kk = C.text('×' + C.fmt_k(k), 'mono', 44, INK, 800)
            C.put(blk, kk, PW - 50 - kk.width, 122, anchor='tl')
            rows.append((blk, t0))
            rows.append((sep('-'), t0 + 0.12))
        tt = self.b(6)
        rows.append((line([('ИТОГО КЭФ', 50, 40, 800, 'l'), ('×' + C.fmt_k(self.total), 0, 56, 800, 'r')], 92), tt))
        rows.append((sep('='), tt + 0.1))
        bc = Image.new('RGBA', (PW, 150), (0, 0, 0, 0))
        d = ImageDraw.Draw(bc)
        rnd = np.random.default_rng(3)
        x = 90
        while x < PW - 90:
            w = int(rnd.choice([3, 3, 5, 7]))
            d.rectangle((x, 20, x + w, 120), fill=INK + (255,))
            x += w + int(rnd.choice([3, 5, 6]))
        C.put(bc, C.text('0 4 6 2 1 0 1 0 2 6', 'mono', 22, INK, 500), PW / 2, 136)
        rows.append((bc, self.b(7)))
        rows.append((line([('TELEGRAM · ' + C.HANDLE, 0, 32, 800, 'c')], 70), self.b(7.6)))
        rows.append((Image.new('RGBA', (PW, 60), (0, 0, 0, 0)), self.b(8)))
        self.rows = rows
        self.ph = sum(r[0].height for r in rows)
        # бумага целиком (печатный слой отдельно — для проявления строк)
        paper = Image.new('RGBA', (PW, self.ph), PAPER + (255,))
        arr = np.asarray(paper, np.int16).copy()
        rnd = np.random.default_rng(9)
        arr[..., :3] += (rnd.normal(0, 3, (self.ph, PW)) + np.linspace(-6, 4, PW)[None, :]).astype(np.int16)[..., None]
        self.paper = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
        self.ys = []
        y = 0
        for im, t0 in rows:
            self.ys.append(y)
            y += im.height
        # зубчатый нижний край после отрыва
        m = Image.new('L', (PW, self.ph + 20), 255)
        dd = ImageDraw.Draw(m)
        pts = [(0, self.ph)]
        for i in range(0, PW + 1, 20):
            pts.append((i, self.ph - (10 if (i // 20) % 2 else 0)))
        pts += [(PW, self.ph + 20), (0, self.ph + 20)]
        dd.polygon(pts, fill=0)
        self.tear_mask = m.crop((0, 0, PW, self.ph))
        # фон: тёмный стол и свет сверху
        bg = C.vgrad(W, H, [(0, (26, 26, 32)), (0.55, (14, 14, 18)), (1, (6, 6, 8))]).convert('RGBA')
        bg = C.add_light(bg, C.radial(1500, 1300, (60, 52, 40), 255, 1.6), W / 2, 760, 1.0)
        self.bg = bg
        # принтер
        pr = Image.new('RGBA', (W, H - SLOT + 40), (0, 0, 0, 0))
        body = C.rrect(PW + 120, H - SLOT + 120, 46, (22, 22, 26))
        C.put(pr, body, W / 2, (H - SLOT + 120) / 2 + 10)
        slot = C.rrect(PW + 40, 26, 13, (4, 4, 6))
        C.put(pr, slot, W / 2, 40)
        hl = C.rrect(PW + 116, 6, 3, (70, 70, 80))
        C.put(pr, hl, W / 2, 14)
        self.printer = pr
        self.led = C.radial(60, 60, (80, 255, 140), 255, 1.2)
        self.stamp = self._stamp()

    def _plate(self):
        if not hasattr(self, '_pl'):
            self._pl = C.rrect(900, 250, 44, (14, 14, 18), 238, outline=(70, 60, 30), width=3)
        return self._pl

    def _dither(self, emb):
        """Эмблема, как её печатает термопринтер: серое → точки."""
        g = Image.new('RGB', emb.size, (255, 255, 255))
        g.paste(emb, (0, 0), emb)
        g = ImageOps.autocontrast(ImageOps.grayscale(g), cutoff=2).convert('1')
        g = g.convert('L')
        ink = Image.new('RGBA', emb.size, INK + (255,))
        a = ImageOps.invert(g)
        a = Image.fromarray((np.asarray(a, np.float32) * (np.asarray(emb.getchannel('A'), np.float32) / 255)).astype(np.uint8))
        ink.putalpha(a)
        return ink

    def _stamp(self):
        w, h = 660, 230
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((6, 6, w - 6, h - 6), 22, outline=RED + (255,), width=10)
        d.rounded_rectangle((22, 22, w - 22, h - 22), 14, outline=RED + (255,), width=4)
        C.put(im, C.text('ЭКСПРЕСС ДНЯ', 'dela', 70, RED, max_w=w - 150), w / 2, h / 2 - 16)
        C.put(im, C.text('JARVIS · ' + self.date, 'mono', 28, RED, 800, track=0.15), w / 2, h - 52)
        rnd = np.random.default_rng(4)
        al = np.asarray(im.getchannel('A'), np.float32)
        al *= np.clip(rnd.normal(0.9, 0.25, al.shape), 0.25, 1)          # неровная краска
        im.putalpha(Image.fromarray(al.astype(np.uint8)))
        return C.rotate(im, 9)

    # ── кадр ──
    def printed(self, t):
        """Сколько пикселей бумаги вышло из щели к моменту t (рывками)."""
        y = 0.0
        for (im, t0), y0 in zip(self.rows, self.ys):
            if t >= t0:
                y = y0 + im.height * C.out_cubic(C.seg(t, t0, t0 + 0.16))
        return y

    def ink(self, t):
        """Печатный слой на момент t (строки появляются вместе с бумагой)."""
        lay = Image.new('RGBA', (PW, self.ph), (0, 0, 0, 0))
        for (im, t0), y0 in zip(self.rows, self.ys):
            if t >= t0:
                lay.alpha_composite(im, (0, y0))
        return lay

    def receipt(self, t):
        key = int(sum(1 for r in self.rows if t >= r[1]))
        if getattr(self, '_rk', None) != key:
            out = self.paper.copy()
            out.alpha_composite(self.ink(t))
            self._rk, self._rc = key, out
        return self._rc

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        tear_t = self.b(9)
        py = self.printed(t)
        rc = self.receipt(t)
        # чек: до отрыва — из щели вверх; после — поднимается в центр и поворачивается
        if t < tear_t:
            vis = rc.crop((0, 0, PW, max(1, int(py))))
            top = SLOT - vis.height
            sh = C.shadow(vis, 26, 0.6)
            C.put(fr, sh, W / 2, top + vis.height / 2 + 30)
            C.put(fr, vis, W / 2 - PW / 2, top, anchor='tl')
            # тень от щели на бумаге
            fr.alpha_composite(C.lgrad(PW, 60, (0, 0, 0), (0, 0, 0), 90, 0, 120), (int(W / 2 - PW / 2), SLOT - 60))
        else:
            k = C.in_out(C.seg(t, tear_t, tear_t + 1.4 * u))
            full = rc.copy()
            full.putalpha(Image.fromarray(np.minimum(np.asarray(full.getchannel('A')), np.asarray(self.tear_mask))))
            k2 = C.in_out(C.seg(t, self.stop, self.hit2 - 0.1))       # стоп трека — медленный наезд на «ИТОГО»
            s = (1.0 - 0.24 * k) * (1 + 0.16 * k2)
            im = C.rotate(C.scale(full, s), -3.0 * k)
            cy = C.lerp(SLOT - full.height / 2, 980, k)
            ytot = self.ys[5 + 2 * len(self.legs)] + 46
            pos_total = cy + (ytot - full.height / 2) * s
            cy += (860 - pos_total) * k2
            pos_total = cy + (ytot - full.height / 2) * s
            C.put(fr, C.shadow(im, 34, 0.7), W / 2 + 10, cy + 44)
            C.put(fr, im, W / 2, cy)
            if t >= self.hit2:
                ps = C.seg(t, self.hit2, self.hit2 + 0.12)
                st = C.scale(self.stamp, 1.6 - 0.6 * ps)
                C.put(fr, st, W / 2 + 30, pos_total + 210, 0.95 * ps)
        # принтер (уходит вниз после отрыва)
        pk = C.in_cubic(C.seg(t, tear_t, tear_t + u))
        C.put(fr, self.printer, 0, SLOT - 40 + pk * 400, anchor='tl')
        if t < tear_t:
            blink = 1.0 if int(t * 6) % 2 == 0 or t < 0.2 else 0.3
            fr = C.add_light(fr, self.led, W / 2 + PW / 2 - 10, SLOT + 50 + pk * 400, blink)
        # камера на сцену: крупно у щели, пока чек короткий
        zc = C.clamp(1180.0 / (self.printed(t) + 640.0), 1.0, 1.45) if t < tear_t else 1.0
        fr = C.zoom(fr, zc, W / 2, SLOT - 80)
        # верх: крючок → кэф экспресса
        if t < D:
            a = C.seg(t, 0.0, 0.25)
            C.put(fr, C.text('ЭКСПРЕСС ДНЯ', 'dela', 116, (255, 255, 255), max_w=960), W / 2, 330, a)
            C.put(fr, C.text('%d МАТЧА · %s · %s' % (len(self.legs), self.league, self.date[:5]), 'mono', 40, GOLD, 700, track=0.2),
                  W / 2, 440, a)
        elif t < self.stop:
            n = sum(1 for i in range(len(self.legs)) if t >= self.b(2 * i))
            kprev = 1.0
            for lg in self.legs[:n - 1]:
                kprev *= lg[3]
            knew = kprev * self.legs[n - 1][3]
            q = C.out_cubic(C.seg(t, self.b(2 * (n - 1)), self.b(2 * (n - 1)) + 0.45))
            val = C.lerp(kprev, knew, q) if n > 1 else C.lerp(1.0, knew, q)
            pop = 1 + 0.12 * (1 - C.seg(t, self.b(2 * (n - 1)), self.b(2 * (n - 1)) + 0.3))
            C.put(fr, self._plate(), W / 2, 335)
            C.put(fr, C.text('ОБЩИЙ КЭФ · %d ИЗ %d' % (n, len(self.legs)), 'mono', 34, GOLD, 700, track=0.2), W / 2, 272)
            C.put(fr, C.scale(C.text('×%.2f' % val, 'dela', 136, (255, 255, 255)), pop), W / 2, 372)
        elif t < self.hit2:
            a = C.seg(t, self.stop + 0.2, self.stop + 0.6)
            C.put(fr, self._plate(), W / 2, 335, a)
            C.put(fr, C.text('ЗАЙДЁТ?', 'dela', 118, (255, 255, 255)), W / 2, 335, a)
        else:
            k = C.out_expo(C.seg(t, self.hit2 + 2 * u, self.hit2 + 3 * u))
            C.put(fr, self._plate(), W / 2, 335, 1 - C.seg(t, self.hit2, self.hit2 + 0.5) * 0)
            C.put(fr, C.text('ЗАЙДЁТ?', 'dela', 118, (255, 255, 255)), W / 2, 335 - 30 * k, 1 - k)
            C.put(fr, C.text('ВЕСЬ РАЗБОР — В TELEGRAM', 'mono', 34, GOLD, 700, track=0.12), W / 2, 272, k)
            plate = C.rrect(700, 120, 60, C.TG_BLUE)
            C.put(plate, C.tg_icon(90, (255, 255, 255), C.TG_BLUE), 70, 60)
            C.put(plate, C.text(C.HANDLE, 'unb', 58, (255, 255, 255), 800), 390, 60)
            C.put(fr, plate, W / 2, 372 + 30 * (1 - k), k)
        # удары: толчок и вспышка
        z, dx, dy = 1.0, 0.0, 0.0
        for th in [D, self.b(2), self.b(4), self.hit2]:
            if t >= th:
                z += 0.03 * (1 - C.seg(t, th, th + 0.35)) ** 2
            sx, sy = C.shake(t, th, 14 if th in (D, self.hit2) else 6, 0.3)
            dx, dy = dx + sx, dy + sy
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        if self.hit2 <= t < self.hit2 + 0.25:
            fr = fr.convert('RGB')
            fr = Image.blend(fr, Image.new('RGB', fr.size, (255, 255, 255)), 0.35 * (1 - C.seg(t, self.hit2, self.hit2 + 0.25)))
        fr = C.vignette(fr, 0.5)
        return C.grain(fr, t, 4)
