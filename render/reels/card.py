# -*- coding: utf-8 -*-
"""«Коллекционная карточка» — хоккейная trading card.

Карточка первой команды вылетает лицом (эмблема, имя, голографический блик), на долю переворачивается —
на обороте по строке на долю — последние 3 игры и очки за сезон (команда на экране 6–8 с); затем то же со второй.
Сверху весь ролик — сам матч (команды, лига, время МСК), без заголовков-рубрик. Перед дропом обе карточки
разлетаются по краям и несутся навстречу, на дропе сталкиваются (вспышка, искры) — и из удара выпадает
золотая «карточка-прогноз» с кэфом. В конце — плашка Telegram.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels import fresh
from reels.core import W, H

CW, CH = 720, 1000
CX, CY = W / 2, 905
INK = (18, 18, 24)
GOLD1, GOLD2, GOLD3 = (255, 232, 150), (214, 160, 52), (150, 100, 22)
GDARK = (40, 25, 0)


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


class Card(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 64, drop=20 * 60 / 64, team=8, rush=2, hold=5,
                 cta=3, seed=31):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef = league, when, coef
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
        self.sh, self.sa = F.norm(sh), F.norm(sa)
        b = self.b
        self.t_in1 = b(-(2 * team + rush))
        if self.t_in1 < 1.0:
            raise ValueError('мало времени до дропа')
        self.t_flip1 = self.t_in1 + 1.5 * u                  # лицо 1,5 доли, затем оборот с фактами
        self.t_in2 = b(-(team + rush))
        self.t_flip2 = self.t_in2 + 1.5 * u
        self.t_rush = b(-rush)
        self.t_cta = b(hold)
        self.dur = b(hold + cta)
        self.cover_t = b(3)
        self._prep()

    # ── карточки ──
    def _frame_card(self, c1, c2):
        """Заготовка: рамка-серебро, внутри поле цвета клуба."""
        card = C.rrect(CW, CH, 34, (236, 238, 244))
        g = C.lgrad(CW, CH, (250, 250, 255), (170, 176, 190), 60)
        g.putalpha(card.getchannel('A'))
        inner = C.lgrad(CW - 44, CH - 44, c1, c2, 70)
        m = C.rrect(CW - 44, CH - 44, 22, (255, 255, 255))
        inner.putalpha(m.getchannel('A'))
        g.alpha_composite(inner, (22, 22))
        return g

    def _front(self, team, sh, role, num):
        c = fresh.club(team)
        im = self._frame_card(C.mix(c, (255, 255, 255), 0.15), C.mix(c, (0, 0, 0), 0.55))
        st = Image.new('RGBA', (CW - 44, CH - 44), (0, 0, 0, 0))
        d = ImageDraw.Draw(st)
        for k in range(-CH, CW, 46):                                   # диагональные полосы
            d.line((k, CH, k + CH, 0), fill=(255, 255, 255, 16), width=14)
        m = np.minimum(np.asarray(st.getchannel('A')), np.asarray(C.rrect(CW - 44, CH - 44, 22, (255, 255, 255)).getchannel('A')))
        st.putalpha(Image.fromarray(m.astype(np.uint8)))
        im.alpha_composite(st, (22, 22))
        im.alpha_composite(C.radial(640, 640, (255, 255, 255), 120, 1.6), (40, 150))
        C.put(im, C.with_shadow(team.emb(470), 20, 0.5, 12), CW / 2, 450)
        top = C.rrect(CW - 120, 76, 38, INK, 225)
        C.put(top, C.text('%s · %s' % (F.lg_ru(self.league), role), 'mono', 34, (255, 255, 255), 800, track=0.2), top.width / 2, 38)
        C.put(im, top, CW / 2, 92)
        plate = C.rrect(CW - 70, 190, 26, INK, 238)
        C.put(plate, C.text(team.up, 'unb', 84, (255, 255, 255), 900, max_w=CW - 140), plate.width / 2, 78)
        g = sh['games']
        nw = sum(1 for x in g if x['res'] == 'В')
        sub = ('%d %s ИЗ %d ПОСЛЕДНИХ' % (nw, plural(nw, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'), len(g))) if g else ''
        if sub:
            C.put(plate, C.text(sub, 'mono', 32, (255, 214, 90), 800, track=0.1), plate.width / 2, 150)
        C.put(im, plate, CW / 2, CH - 150)
        badge = C.ellipse(86, 86, (255, 214, 90))
        C.put(badge, C.text(str(num), 'unb', 44, INK, 900), 43, 43)
        C.put(im, badge, CW - 80, CH - 255)
        return im

    def _back(self, team, s):
        c = fresh.club(team)
        im = self._frame_card((248, 246, 240), (226, 222, 212))
        hd = C.rrect(CW - 44, 170, 22, C.mix(c, (0, 0, 0), 0.25))
        C.put(hd, team.emb(130), 100, 85)
        C.put(hd, C.text(team.up, 'unb', 64, (255, 255, 255), 900, max_w=CW - 260), 190, 85 - 22, anchor='tl')
        C.put(im, hd, CW / 2, 22 + 85)
        rows = []                       # (картинка, y) — проявляются по очереди
        y = 245
        rows.append((C.text('ПОСЛЕДНИЕ 3 ИГРЫ', 'mono', 34, (110, 104, 92), 800, track=0.16), y + 4))
        y += 70
        for g in s['games']:
            r = Image.new('RGBA', (CW - 100, 96), (0, 0, 0, 0))
            C.put(r, F.chip(g['res'], 80), 40, 48)
            sc = C.text(g['score'], 'unb', 60, INK, 900)
            C.put(r, sc, 100, 48 - sc.height / 2, anchor='tl')
            x = 100 + sc.width + 12
            if g['note']:
                nt = C.text(g['note'], 'unb', 30, (120, 116, 108), 800)
                C.put(r, nt, x, 56 - nt.height / 2, anchor='tl')
                x += nt.width + 8
            op = C.text(g['opp'], 'golos', 46, (50, 50, 60), 600, max_w=CW - 100 - x - 24)
            C.put(r, op, CW - 100 - op.width, 50 - op.height / 2, anchor='tl')
            rows.append((r, y + 48))
            y += 104
        y += 20
        stats = []                                                  # (подпись, значение, мелко)
        if s['points'] is not None:
            stats.append(('ОЧКИ', '%d' % s['points'],
                          'за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей')) if s['gp'] is not None else ''))
        if s['place'] is not None:
            stats.append(('МЕСТО', '%d' % s['place'], s['place_scope']))
        if s['gd'] is not None:
            stats.append(('ШАЙБЫ ±', F.gd_txt(s['gd']), 'разница'))
        if stats:
            n = len(stats)
            bw = (CW - 100 - 20 * (n - 1)) / n
            r = Image.new('RGBA', (CW - 100, 210), (0, 0, 0, 0))
            for k, (lab, v, sub) in enumerate(stats):
                bx = C.rrect(bw, 210, 24, C.mix(c, (0, 0, 0), 0.25) if k == 0 else INK)
                col = (255, 255, 255)
                if lab == 'ШАЙБЫ ±':
                    col = (120, 240, 160) if v.startswith('+') else (255, 130, 120) if v.startswith('−') else col
                C.put(bx, C.text(v, 'unb', 84, col, 900, max_w=bw - 30), bw / 2, 74)
                C.put(bx, C.text(lab, 'mono', 30, (230, 232, 238), 800, track=0.08, max_w=bw - 20), bw / 2, 146)
                if sub:
                    C.put(bx, C.text(sub, 'golos', 26, (175, 178, 190), 600, max_w=bw - 20), bw / 2, 184)
                C.put(r, bx, k * (bw + 20), 0, anchor='tl')
            rows.append((r, y + 105))
            y += 210
        foot = C.text('JARVIS · %s' % F.lg_ru(self.league), 'mono', 26, (130, 124, 112), 700, track=0.2)
        C.put(im, foot, CW / 2, CH - 52)
        return im, rows

    def _gold(self):
        card = C.rrect(CW, CH, 34, (255, 255, 255))
        g = C.lgrad(CW, CH, GOLD1, GOLD3, 55)
        arr = np.asarray(g, np.float32).copy()
        yy, xx = np.mgrid[0:CH, 0:CW]
        arr[..., :3] *= (0.95 + 0.05 * np.sin((xx + yy) * 0.09))[..., None]
        g = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
        g.putalpha(card.getchannel('A'))
        d = ImageDraw.Draw(g)
        d.rounded_rectangle((20, 20, CW - 21, CH - 21), 24, outline=(255, 246, 210, 255), width=5)
        d.rounded_rectangle((36, 36, CW - 37, CH - 37), 18, outline=GOLD3 + (255,), width=3)
        top = C.rrect(CW - 140, 80, 40, GDARK)
        C.put(top, C.text('ПРОГНОЗ', 'mono', 40, GOLD1, 800, track=0.35), top.width / 2, 40)
        C.put(g, top, CW / 2, 100)
        C.put(g, C.with_shadow(self.fav.emb(330), 18, 0.45, 10), CW / 2, 345)
        C.put(g, C.text(self.pick1, 'unb', 76, GDARK, 900, max_w=CW - 90), CW / 2, 590)
        if self.pick2:
            C.put(g, C.text(self.pick2, 'unb', 44, GDARK, 800, max_w=CW - 120), CW / 2, 672)
        kt = C.text('КЭФ ' + C.fmt_k(self.coef), 'unb', 78, GOLD1, 900)
        kp = C.rrect(kt.width + 100, 140, 70, GDARK)
        C.put(kp, kt, kp.width / 2, 70)
        C.put(g, kp, CW / 2, 800)
        C.put(g, C.text('%s — %s · %s' % (self.h.up, self.a.up, self.when), 'mono', 28, GDARK, 800, max_w=CW - 110), CW / 2, CH - 82)
        return g

    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        bg = C.vgrad(W, H, [(0, (26, 24, 34)), (0.55, (12, 11, 17)), (1, (4, 4, 6))]).convert('RGBA')
        d = ImageDraw.Draw(bg)
        for _ in range(140):                                         # пылинки в свете
            x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1, 3)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(rnd.uniform(20, 70))))
        self.bg = bg
        self.glow = {s: C.radial(1300, 1300, fresh.bright(fresh.club(t), 0.2), 150, 1.8) for s, t in (('h', self.h), ('a', self.a))}
        self.glow['g'] = C.radial(1400, 1400, (255, 200, 80), 190, 1.6)
        self.front = {'h': self._front(self.h, self.sh, 'ХОЗЯЕВА', 1), 'a': self._front(self.a, self.sa, 'ГОСТИ', 2)}
        self.back = {'h': self._back(self.h, self.sh), 'a': self._back(self.a, self.sa)}
        self.gold = self._gold()
        self.gold_back = self._gold_back()
        band = Image.new('RGBA', (CW * 3, CH), (0, 0, 0, 0))
        bd = C.lgrad(360, CH, (255, 255, 255), (255, 255, 255), 0, 0, 0)
        arr = np.zeros((CH, 360, 4), np.uint8)
        arr[..., :3] = 255
        arr[..., 3] = (np.sin(np.linspace(0, math.pi, 360)) ** 2 * 95).astype(np.uint8)[None, :]
        bd = Image.fromarray(arr, 'RGBA')
        band.alpha_composite(bd, (CW, 0))
        self.band = band
        self.title = C.text('%s — %s' % (self.h.up, self.a.up), 'unb', 50, (255, 255, 255), 900, max_w=980)
        self.sub = C.text('%s · %s' % (F.lg_ru(self.league), self.when), 'mono', 34, (255, 214, 90), 800, track=0.08)
        self.spark = C.radial(26, 26, (255, 236, 170), 255, 1.2)
        self.m_emb = {s: C.with_shadow(t.emb(330), 20, 0.6, 10) for s, t in (('h', self.h), ('a', self.a))}
        self.m_vs = C.text('VS', 'unb', 90, (255, 214, 90), 900)
        self.flash = C.radial(1200, 1200, (255, 240, 200), 255, 1.3)
        self.sparks = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(500, 1500), rnd.uniform(0.6, 1.4)) for _ in range(70)]

    def _gold_back(self):
        card = C.rrect(CW, CH, 34, (255, 255, 255))
        g = C.lgrad(CW, CH, GOLD2, GOLD3, 120)
        g.putalpha(card.getchannel('A'))
        C.put(g, C.text('J', 'unb', 420, GOLD1, 900), CW / 2, CH / 2 - 40)
        C.put(g, C.text('JARVIS', 'unb', 70, GOLD1, 900, track=0.3), CW / 2, CH / 2 + 220)
        return g

    def shine(self, im, t, speed=0.55, off=0.0):
        """Голографический блик: светлая полоса едет по диагонали."""
        ph = ((t * speed + off) % 1.6) / 1.6
        x = int(-CW * 2 + ph * CW * 3)
        lay = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
        lay.alpha_composite(C.rotate(self.band, 0).crop((0, 0, CW * 3, CH)), (x, 0))
        a = np.minimum(np.asarray(lay.getchannel('A'), np.uint16), np.asarray(im.getchannel('A'), np.uint16)).astype(np.uint8)
        lay.putalpha(Image.fromarray(a))
        out = im.copy()
        out.alpha_composite(lay)
        return out

    def back_img(self, side, t, t0):
        """Оборот: строки проявляются по долям после переворота."""
        im, rows = self.back[side]
        key = (side, sum(1 for k in range(len(rows)) if t >= t0 + 0.1 + k * self.u))          # строка на долю
        if not hasattr(self, '_bc'):
            self._bc = {}
        if key not in self._bc:
            out = im.copy()
            for k, (r, y) in enumerate(rows[:key[1]]):
                C.put(out, r, CW / 2, y)
            self._bc[key] = out
        out = self._bc[key]
        # последняя строка — с проявлением
        n = key[1]
        if 0 < n <= len(rows):
            tk = t0 + 0.1 + (n - 1) * self.u
            q = C.out_expo(C.seg(t, tk, tk + 0.3))
            if q < 1:
                out = im.copy()
                for k, (r, y) in enumerate(rows[:n]):
                    C.put(out, r, CW / 2 + (0 if k < n - 1 else 60 * (1 - q)), y, 1.0 if k < n - 1 else q)
        return out

    def flipped(self, front, back, k):
        """Переворот по вертикальной оси: k 0..1 (0 — лицо, 1 — оборот)."""
        ang = k * math.pi
        sx = abs(math.cos(ang))
        im = front if k < 0.5 else back
        w = max(2, int(CW * sx))
        im = im.resize((w, CH), Image.BILINEAR)
        if sx < 0.6:                                                  # ребром — темнее
            dk = Image.new('RGBA', im.size, (0, 0, 0, int(140 * (1 - sx / 0.6))))
            dk.putalpha(Image.fromarray(np.minimum(np.asarray(im.getchannel('A')), int(140 * (1 - sx / 0.6))).astype(np.uint8)))
            im = im.copy()
            im.alpha_composite(dk)
        return im

    def place(self, fr, im, x, y, s=1.0, rot=0.0, a=1.0, sh=True):
        im = C.scale(im, s)
        if rot:
            im = C.rotate(im, rot)
        if sh:
            C.put(fr, C.shadow(im, 30, 0.65 * a), x + 14, y + 30)
        C.put(fr, im, x, y, a)

    def team_card(self, side, t, t_in, t_flip):
        fk = C.in_out(C.seg(t, t_flip, t_flip + 0.4))
        fr_ = self.shine(self.front[side], t, off=0.3 if side == 'a' else 0)
        bk = self.back_img(side, t, t_flip + 0.1) if fk > 0.5 else None
        return self.flipped(fr_, bk, fk) if fk > 0 else fr_

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        # подсветка: цвет текущей карточки → золото после дропа
        if t < self.t_in2:
            gk, gs = C.seg(t, 0.1, 0.6), 'h'
        elif t < D:
            gk, gs = 1.0, 'a'
        else:
            gk, gs = 1.0, 'g'
        fr = C.add_light(fr, self.glow[gs], CX, CY, 0.9 * gk).convert('RGBA')
        fresh.header(fr, {'league': self.league}, C.seg(t, 0, 0.3), col=(200, 200, 210))
        if t < self.t_cta:
            ta = C.seg(t, 0.0, 0.3) * (1 - C.seg(t, D - 0.2, D))
            if t >= D + 0.6:
                ta = C.seg(t, D + 0.6, D + 0.9)
            C.put(fr, self.title, W / 2, 322, ta)
            C.put(fr, self.sub, W / 2, 378, ta)
        # первая карточка
        if t < self.t_rush:
            if t < self.t_in1 + 0.3:                                 # до карточек — сам матч: обе эмблемы
                q = C.out_expo(C.seg(t, 0.1, 0.6)) * (1 - C.seg(t, self.t_in1 - 0.1, self.t_in1 + 0.3))
                for e, x in ((self.m_emb['h'], CX - 275), (self.m_emb['a'], CX + 275)):
                    C.put(fr, e, x, CY - 60 + 30 * (1 - q), q)
                C.put(fr, self.m_vs, CX, CY - 60, q)
            if self.t_in1 <= t < self.t_in2 + 0.5:
                q = C.out_cubic(C.seg(t, self.t_in1, self.t_in1 + 0.55))
                ex = C.in_cubic(C.seg(t, self.t_in2, self.t_in2 + 0.45))
                im = self.team_card('h', t, self.t_in1, self.t_flip1)
                x = CX - 900 * ex
                y = CY + 1100 * (1 - q)
                self.place(fr, im, x, y, 1.0 - 0.15 * ex, -14 * (1 - q) - 18 * ex)
            if t >= self.t_in2:
                q = C.out_cubic(C.seg(t, self.t_in2, self.t_in2 + 0.55))
                im = self.team_card('a', t, self.t_in2, self.t_flip2)
                self.place(fr, im, CX + 900 * (1 - q), CY, 1.0, 14 * (1 - q))
        elif t < D:
            # обе лицом, разлетаются и несутся навстречу
            k1 = C.out_cubic(C.seg(t, self.t_rush, self.t_rush + 0.4))
            k2 = C.in_cubic(C.seg(t, D - 0.32, D))
            s = 0.62 - 0.08 * k2
            xh = C.lerp(CX - 1000, 250, k1) + (CX - 160 - 250) * k2
            xa = C.lerp(CX, 830, k1) + (CX + 160 - 830) * k2
            self.place(fr, self.shine(self.front['h'], t), xh, CY, s, 8 - 4 * k2)
            ka = C.seg(t, self.t_rush, self.t_rush + 0.35)
            im = self.flipped(self.front['a'], self.back_img('a', t, 0), 1 - ka) if ka < 1 else self.shine(self.front['a'], t, off=0.3)
            self.place(fr, im, xa, CY, s, -8 + 4 * k2)
        else:
            # столкновение: карточки отлетают, искры, золотая карточка
            k = C.out_cubic(C.seg(t, D, D + 0.6))
            if k < 1:
                self.place(fr, self.front['h'], CX - 160 - 900 * k, CY + 300 * k, 0.54, 8 + 50 * k, 1 - k * 0.5)
                self.place(fr, self.front['a'], CX + 160 + 900 * k, CY + 300 * k, 0.54, -8 - 50 * k, 1 - k * 0.5)
            ts = t - D
            if ts < 0.9:
                for ang, sp, sz in self.sparks:
                    r = sp * ts * (1 - 0.35 * ts)
                    x, y = CX + r * math.cos(ang), CY + r * math.sin(ang) + 260 * ts * ts
                    fr = C.add_light(fr, C.scale(self.spark, sz), x, y, 1.6 * (1 - ts / 0.9))
            g = C.out_back(C.seg(t, D + 0.05, D + 0.55), 1.3)
            fl = C.in_out(C.seg(t, D + 0.15, D + 0.55))
            im = self.flipped(self.gold_back, self.shine(self.gold, t, 0.45), fl) if fl < 1 else self.shine(self.gold, t, 0.45)
            sc = max(0.05, 0.25 + 0.75 * g)
            ck = C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.5))
            sc *= 1 - 0.1 * ck
            self.place(fr, im, CX, CY - 40 * ck + 60 * (1 - min(1, g)), sc, -6 * (1 - C.seg(t, D, D + 0.7)))
            if ts < 0.35:
                fr = C.add_light(fr, self.flash, CX, CY, 1.4 * (1 - ts / 0.35)).convert('RGBA')
        if t >= self.t_cta:
            fresh.cta(fr, t, self.t_cta, y=1410)
        # удары: переворот, вход, дроп
        z, dx, dy = 1.0 + 0.012 * math.sin(t * 0.6), 0.0, 0.0
        for th, amp in ((self.t_flip1, 4), (self.t_in2, 5), (self.t_flip2, 4), (D, 20)):
            sx, sy = C.shake(t, th, amp, 0.35 if th == D else 0.2)
            dx, dy = dx + sx, dy + sy
            if t >= th:
                z += (0.06 if th == D else 0.012) * (1 - C.seg(t, th, th + 0.35)) ** 2
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        fr = C.vignette(fr, 0.45)
        return C.grain(fr, t, 4)
