# -*- coding: utf-8 -*-
"""«Взвешивание» — tale of the tape, как перед боем UFC.

Две колонки под прожекторами (слева хозяева, справа гости), посередине — подписи строк. На каждую долю трека
прилетает строка сравнения: сначала вся колонка первой команды (последние 3 игры, очки, место, разница шайб),
потом второй. Перед дропом — пульс «VS», на дропе — штамп-прогноз с кэфом, фаворит подсвечивается золотом.
В конце — плашка Telegram.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels import fresh
from reels.core import W, H

GOLD = (255, 200, 70)
RED = (206, 32, 44)
GRAY = (150, 152, 162)
LX, RX = 270, 810                   # центры колонок
G_Y = (918, 996, 1074)              # строки последних игр
S_Y0, S_DY = 1186, 102              # строки цифр


class Tape(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 96.5, drop=16 * 60 / 96.5, seed=11):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef = league, when, coef
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.sh, self.sa = F.norm(sh), F.norm(sa)
        # строки: игры (по 3 на сторону) + цифры, которые есть хотя бы у одной стороны
        labels = []
        for lab, _ in F.stat_rows(self.sh) + F.stat_rows(self.sa):
            if lab not in labels and lab != 'МАТЧИ':
                labels.append(lab)
        order = ['ОЧКИ', 'МЕСТО', 'ШАЙБЫ ±']
        self.labels = [x for x in order if x in labels]
        self.n = max(len(self.sh['games']), len(self.sa['games'])) + len(self.labels)
        n = self.n
        self.t1 = self.b(-(2 * n + 2))                      # первая команда
        self.t2 = self.b(-(n + 2))                          # вторая
        if self.t1 < 0.5:
            raise ValueError('мало времени до дропа')
        self.t_cta = self.b(5)
        self.dur = self.b(11)
        self.cover_t = self.b(3)
        self._prep()

    # ── заготовки ──
    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        bg = C.vgrad(W, H, [(0, (22, 22, 30)), (0.45, (10, 10, 15)), (1, (3, 3, 5))]).convert('RGBA')
        arr = np.asarray(bg, np.int16).copy()
        arr[..., :3] += rnd.normal(0, 3, (H, W, 1)).astype(np.int16)
        self.bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
        self.ch = fresh.bright(fresh.club(self.h), 0.25)
        self.ca = fresh.bright(fresh.club(self.a), 0.25)
        self.spot = {}
        for side, col, x in (('h', self.ch, LX), ('a', self.ca, RX)):
            m = Image.new('L', (W, H), 0)
            d = ImageDraw.Draw(m)
            top = x + (-180 if side == 'h' else 180)
            d.polygon([(top - 60, -40), (top + 60, -40), (x + 330, 1500), (x - 330, 1500)], fill=120)
            m = m.filter(ImageFilter.GaussianBlur(60))
            lay = Image.new('RGBA', (W, H), col + (0,))
            lay.putalpha(m)
            self.spot[side] = lay
        # стол сравнения
        ny = len(self.labels)
        self.tab_top, self.tab_bot = 840, S_Y0 + (ny - 1) * S_DY + 70 if ny else G_Y[-1] + 60
        pan = C.rrect(1010, self.tab_bot - self.tab_top, 34, (16, 16, 22), 225, outline=(60, 54, 36), width=2)
        d = ImageDraw.Draw(pan)
        d.line((505, 90, 505, pan.height - 24), fill=(70, 62, 40, 255), width=2)
        for k in range(ny):
            y = S_Y0 + k * S_DY - self.tab_top - S_DY / 2 + 8
            d.line((40, y, 970, y), fill=(44, 44, 54, 255), width=2)
        self.panel = pan
        self.title = C.with_shadow(C.text('ВЗВЕШИВАНИЕ', 'dela', 104, (255, 255, 255), max_w=960), 14, 0.6, 8)
        self.sub = C.text('%s · %s' % (F.lg_ru(self.league), self.when), 'mono', 36, GOLD, 800, track=0.06, max_w=960)
        self.emb = {s: C.with_shadow(t.emb(250), 20, 0.6, 10) for s, t in (('h', self.h), ('a', self.a))}
        self.name = {s: C.text(t.up, 'unb', 54, (255, 255, 255), 800, max_w=440) for s, t in (('h', self.h), ('a', self.a))}
        self.corner = {'h': C.text('ХОЗЯЕВА', 'mono', 30, self.ch, 800, track=0.25),
                       'a': C.text('ГОСТИ', 'mono', 30, self.ca, 800, track=0.25)}
        self.vs = C.text('VS', 'dela', 96, GOLD)
        self.g_head = C.text('ПОСЛЕДНИЕ 3 ИГРЫ', 'mono', 30, GOLD, 800, track=0.18)
        self.items = {'h': self._items(self.sh, 'h'), 'a': self._items(self.sa, 'a')}
        self.lab = {lab: C.text(lab, 'mono', 30, GOLD, 800, track=0.12) for lab in self.labels}
        self.stamp = self._stamp()
        self.better, self.t_cmp = {}, {}
        vh, va = dict(F.stat_rows(self.sh)), dict(F.stat_rows(self.sa))
        for k, lab in enumerate(self.labels):
            if vh.get(lab) is None or va.get(lab) is None:
                continue
            x, y = (float(v.replace('−', '-').replace('+', '')) for v in (vh[lab], va[lab]))
            if x == y or (lab == 'МЕСТО' and self.sh['place_scope'] != self.sa['place_scope']):
                continue
            self.better[lab] = ('h' if x < y else 'a') if lab == 'МЕСТО' else ('h' if x > y else 'a')
            ka = [i for i, it in enumerate(self.items['a']) if it[2] == lab][0]
            self.t_cmp[lab] = self.t2 + ka * self.u + 0.15
        self.lab_t = {}
        for side, t0 in (('h', self.t1), ('a', self.t2)):
            for k, (im, y, typ) in enumerate(self.items[side]):
                if typ in self.lab and typ not in self.lab_t:
                    self.lab_t[typ] = (t0 + k * self.u, y)
        ring = C.radial(480, 480, GOLD, 200, 1.6)
        self.ring = ring

    def _game(self, g, side):
        w, hh, cd = 466, 72, 64
        im = Image.new('RGBA', (w, hh), (0, 0, 0, 0))
        ch = F.chip(g['res'], cd)
        sc = C.text(g['score'], 'unb', 48, (255, 255, 255), 800)
        nt = C.text(g['note'], 'unb', 23, GRAY, 700) if g['note'] else None
        scw = sc.width + (nt.width + 5 if nt else 0)
        room = w - cd - 14 - scw - 14
        op = C.text(g['opp'], 'golos', 40, (215, 217, 225), 600, max_w=room)
        if side == 'h':
            x = 0
            C.put(im, ch, x, 4, anchor='tl')
            x += cd + 16
            C.put(im, sc, x, hh / 2 - sc.height / 2, anchor='tl')
            x += sc.width + 5
            if nt:
                C.put(im, nt, x, hh / 2 - nt.height / 2 + 6, anchor='tl')
                x += nt.width
            C.put(im, op, x + 14, hh / 2 - op.height / 2 + 2, anchor='tl')
        else:
            x = w
            C.put(im, ch, x - cd, 4, anchor='tl')
            x -= cd + 16
            if nt:
                C.put(im, nt, x - nt.width, hh / 2 - nt.height / 2 + 6, anchor='tl')
                x -= nt.width + 5
            C.put(im, sc, x - sc.width, hh / 2 - sc.height / 2, anchor='tl')
            x -= sc.width
            C.put(im, op, x - 14 - op.width, hh / 2 - op.height / 2 + 2, anchor='tl')
        return im

    def _items(self, s, side):
        """[(картинка, x-центр/край, y, тип)] в порядке появления."""
        out = []
        for k, g in enumerate(s['games']):
            out.append((self._game(g, side), G_Y[k], 'g'))
        vals = dict(F.stat_rows(s))
        for k, lab in enumerate(self.labels):
            v = vals.get(lab)
            if v is None:
                out.append((None, S_Y0 + k * S_DY, lab))
                continue
            col = (255, 255, 255)
            if lab == 'ШАЙБЫ ±':
                col = F.WIN if v.startswith('+') else F.LOSS if v.startswith('−') else (255, 255, 255)
            im = C.text(v, 'unb', 78, col, 900)
            sub = None
            if lab == 'ОЧКИ' and s['gp'] is not None:
                sub = C.text('за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей')), 'golos', 30, GRAY, 600)
            if lab == 'МЕСТО' and s['place_scope']:
                sub = C.text(s['place_scope'], 'golos', 30, GRAY, 600)
            if sub is not None:
                box = Image.new('RGBA', (max(im.width, sub.width), im.height + 8 + sub.height), (0, 0, 0, 0))
                C.put(box, im, box.width / 2, im.height / 2)
                C.put(box, sub, box.width / 2, im.height + 8 + sub.height / 2)
                im = box
            out.append((im, S_Y0 + k * S_DY, lab))
        return out

    def _stamp(self):
        w, h = 940, 440
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), 30, fill=RED + (244,))
        d.rounded_rectangle((16, 16, w - 17, h - 17), 22, outline=(255, 255, 255, 255), width=7)
        d.rounded_rectangle((32, 32, w - 33, h - 33), 16, outline=(255, 255, 255, 200), width=3)
        C.put(im, C.text('ПРОГНОЗ НА МАТЧ', 'mono', 34, (255, 225, 225), 800, track=0.3), w / 2, 78)
        C.put(im, C.text(self.pick1, 'dela', 92, (255, 255, 255), max_w=w - 110), w / 2, 168)
        if self.pick2:
            C.put(im, C.text(self.pick2, 'unb', 44, (255, 255, 255), 800, max_w=w - 140), w / 2, 252)
        kk = C.text('КЭФ ' + C.fmt_k(self.coef), 'dela', 76, GOLD)
        C.put(im, kk, w / 2, 348)
        rnd = np.random.default_rng(4)                        # неровная краска
        al = np.asarray(im.getchannel('A'), np.float32)
        noise = np.asarray(Image.fromarray((rnd.random((h // 6 + 1, w // 6 + 1)) * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR), np.float32) / 255
        al *= np.clip(0.80 + 0.35 * noise, 0.6, 1)
        im.putalpha(Image.fromarray(al.astype(np.uint8)))
        return C.rotate(im, 6)

    # ── кадр ──
    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        # прожекторы: на свою команду — ярко
        for side, t0, t1 in (('h', self.t1, self.t2), ('a', self.t2, self.b(-1))):
            if t < self.t1:
                k = 0.55 * C.seg(t, 0.2, 0.8)
            elif t < D:
                k = 1.0 if t0 <= t < t1 else 0.35
                if t >= self.b(-2):
                    k = 0.6 + 0.4 * abs(math.sin((t - self.b(-2)) * math.pi / u))
            else:
                fav = side == self.side
                k = 1.0 if fav else 0.25
            fr.alpha_composite(C.fade(self.spot[side], k))
        # заголовок
        fresh.header(fr, {'league': self.league}, C.seg(t, 0.0, 0.3))
        q = C.out_expo(C.seg(t, 0.0, 0.35))
        C.put(fr, C.scale(self.title, 1.5 - 0.5 * q), W / 2, 350, q)
        C.put(fr, self.sub, W / 2, 432, C.seg(t, 0.25, 0.55))
        # бойцы
        for side, x, dirn in (('h', LX, -1), ('a', RX, 1)):
            q = C.out_expo(C.seg(t, 0.15 + 0.12 * (side == 'a'), 0.65 + 0.12 * (side == 'a')))
            if t < D:
                foc = 1.0 if t < self.t1 or t >= self.b(-1) else (1.0 if (side == 'h') == (t < self.t2) else 0.45)
            else:
                foc = 1.0 if side == self.side else 0.4
            if t >= D and side == self.side:
                gk = C.out_cubic(C.seg(t, D, D + 0.3))
                fr = C.add_light(fr, self.ring, x, 640, 0.9 * gk)
            pop = 1.0
            ts = self.t1 if side == 'h' else self.t2
            if t >= ts:
                pop += 0.10 * (1 - C.seg(t, ts, ts + 0.3)) ** 2
            C.put(fr, C.scale(self.emb[side], pop), x + dirn * 260 * (1 - q), 640, q * foc)
            C.put(fr, self.corner[side], x, 490, q * foc)
            C.put(fr, self.name[side], x, 800, q * foc)
        vk = C.seg(t, 0.5, 0.8)
        vs = self.vs
        if self.b(-2) <= t < D:
            ph = (t - self.b(-2)) / u
            vs = C.scale(vs, 1 + 0.25 * max(0, 1 - (ph % 1) * 3))
        C.put(fr, vs, W / 2, 640, vk)
        # стол
        if t >= self.t1 - 0.4:
            pk = C.out_cubic(C.seg(t, self.t1 - 0.4, self.t1))
            C.put(fr, self.panel, W / 2, (self.tab_top + self.tab_bot) / 2 + 40 * (1 - pk), pk)
            C.put(fr, self.g_head, W / 2, 870 + 1, pk)
            for lab, (tl, y) in self.lab_t.items():
                if t >= tl:
                    C.put(fr, self.lab[lab], W / 2, y, C.seg(t, tl, tl + 0.2))
            for side, t0 in (('h', self.t1), ('a', self.t2)):
                for k, (im, y, typ) in enumerate(self.items[side]):
                    ti = t0 + k * u
                    if t < ti:
                        break
                    if im is None:
                        continue
                    q = C.out_expo(C.seg(t, ti, ti + 0.32))
                    dx = (-1 if side == 'h' else 1) * 160 * (1 - q)
                    if typ == 'g':
                        xx = 50 if side == 'h' else W - 50 - im.width
                        C.put(fr, im, xx + dx, y - im.height / 2, q, anchor='tl')
                    else:
                        C.put(fr, im, (LX - 20 if side == 'h' else RX + 20) + dx, y + (im.height / 2 - 40 if im.height > 100 else 0), q)
                    if typ != 'g' and side == self.better.get(typ) and t >= self.t_cmp.get(typ, 1e9):
                        mq = C.out_expo(C.seg(t, self.t_cmp[typ], self.t_cmp[typ] + 0.3))
                        mk = C.rrect(int(170 * mq) + 2, 8, 4, GOLD)
                        yb = y + (im.height - 40 if im.height > 100 else im.height / 2) + 12
                        C.put(fr, mk, (LX - 20 if side == 'h' else RX + 20), yb)
                    if t < ti + 0.25:                             # вспышка строки
                        fl = 1 - C.seg(t, ti, ti + 0.25)
                        bar = C.rrect(470, 6, 3, self.ch if side == 'h' else self.ca)
                        C.put(fr, bar, (LX if side == 'h' else RX), y + 40, fl)
        # штамп на дропе
        if t >= D:
            dim = C.seg(t, D, D + 0.15)
            ov = Image.new('RGBA', (1010, self.tab_bot - self.tab_top), (6, 6, 9, int(170 * dim)))
            C.put(fr, ov, W / 2, (self.tab_top + self.tab_bot) / 2)
            ps = C.seg(t, D, D + 0.11)
            st = C.scale(self.stamp, 2.0 - 1.0 * C.out_cubic(ps))
            sy = 1150 - 50 * C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.5))
            C.put(fr, C.shadow(st, 26, 0.7 * ps), W / 2 + 12, sy + 22)
            C.put(fr, st, W / 2, sy, min(1.0, 0.3 + ps))
        if t >= self.t_cta:
            fresh.cta(fr, t, self.t_cta, y=1415)
        else:
            fresh.handle(fr, C.seg(t, 0.4, 0.8) * (1 - C.seg(t, self.t1 - 0.4, self.t1)))
        # камера: удары, пульс
        z, dx, dy = 1.0 + 0.012 * math.sin(t * 0.5), 0.0, 0.0
        hits = [self.t1, self.t2, D]
        for th in hits:
            amp = 18 if th == D else 5
            sx, sy = C.shake(t, th, amp, 0.35 if th == D else 0.2)
            dx, dy = dx + sx, dy + sy
            if t >= th:
                z += (0.05 if th == D else 0.015) * (1 - C.seg(t, th, th + 0.35)) ** 2
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        if D <= t < D + 0.3:
            fr = Image.blend(fr.convert('RGB'), Image.new('RGB', fr.size, (255, 255, 255)), 0.45 * (1 - C.seg(t, D, D + 0.3)))
        fr = C.vignette(fr, 0.45)
        return C.grain(fr, t, 4)


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many
