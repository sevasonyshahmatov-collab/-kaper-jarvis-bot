# -*- coding: utf-8 -*-
"""«Частицы» — эмблемы из тысяч светящихся точек.

До дропа точки слетаются в эмблемы обеих команд (слева и справа), пульсируют на доли. На дропе — взрыв, и все точки
собираются в большую эмблему фаворита; дальше они же складываются в надпись прогноза, затем в огромный шанс;
внизу — линия и подписка в Telegram. Тёмное небо, аддитивное свечение, лёгкий дрейф точек.
"""
import math

import numpy as np
from PIL import Image, ImageFilter

from reels import core as C
from reels import fresh as F
from reels.core import H, W

N = 16000


def _ease(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


class Particles(C.Reel):
    def __init__(self, m, u=1.0, drop=3.0, seed=11):
        super().__init__(u, drop, seed)
        self.m = m
        self.h, self.a = C.match(m['home'], m['away'], m['league'])
        self.fav = self.h if m['side'] == 'h' else self.a
        rng = np.random.default_rng(seed)
        D = drop
        self.t_emb = D                     # взрыв → эмблема фаворита
        self.t_pick = D + 3 * u            # → надпись прогноза
        self.t_num = D + 6 * u             # → шанс
        self.t_line = D + 7 * u
        self.t_cta = D + 9 * u
        self.dur = D + 12 * u
        self.cover_t = D + 8.5 * u
        n2 = N // 2
        e1, e2 = self.h.emb(400), self.a.emb(400)
        p1, c1 = F.mask_points(e1, n2, rng, 290, 900)
        p2, c2 = F.mask_points(e2, N - n2, rng, 790, 900)
        self.P0, self.C0 = np.vstack([p1, p2]), np.vstack([c1, c2])
        self.P1, self.C1 = F.mask_points(self.fav.emb(760), N, rng, W / 2, 820)
        fc = np.array(F.bright(F.club(self.fav), 0.45), np.float32)
        tm = F.text_mask([w for w in self._pick_lines()], 150, 960)
        self.P2, _ = F.mask_points(tm, N, rng, W / 2, 820)
        self.C2 = np.tile(np.array((255, 255, 255), np.float32), (N, 1)) * 0.75 + fc * 0.25
        nm = F.text_mask(['%d%%' % m['chance']], 430, 980)
        self.P3, _ = F.mask_points(nm, N, rng, W / 2, 760)
        self.C3 = np.tile(fc, (N, 1))
        # разброс — откуда точки прилетают в начале, взрыв, дрейф
        ang = rng.uniform(0, 2 * math.pi, N)
        self.Pstart = np.stack([W / 2 + np.cos(ang) * rng.uniform(700, 1400, N), 900 + np.sin(ang) * rng.uniform(700, 1400, N)], 1)
        ang2 = rng.uniform(0, 2 * math.pi, N)
        rr = rng.uniform(250, 900, N)
        self.Boom = np.stack([np.cos(ang2) * rr, np.sin(ang2) * rr], 1)
        self.delay = rng.uniform(0, 0.35, N).astype(np.float32)
        self.ph = rng.uniform(0, 2 * math.pi, N).astype(np.float32)
        self.size = rng.choice([1, 2, 2, 3], N)
        stars = rng.uniform(0, 1, (300, 3))
        self.stars = stars
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - 880) / H) ** 2)
        base = np.stack([8 + 10 * (1 - d), 9 + 12 * (1 - d), 18 + 24 * (1 - d)], -1)
        self.bg = np.clip(base, 0, 255).astype(np.float32)
        self.fc = fc

    def _pick_lines(self):
        words = self.m['pick'].split()
        if len(words) <= 1:
            return words
        return [words[0], ' '.join(words[1:])]

    def _pos(self, t):
        """Положение и цвет каждой точки в момент t."""
        u, D = self.u, self.drop
        wob = np.stack([np.sin(t * 1.3 + self.ph), np.cos(t * 1.1 + self.ph * 1.7)], 1) * 1.2
        if t < self.t_emb:
            k = _ease((t - 0.1 - self.delay * 2) / 1.4)[:, None]
            beat = 0.5 + 0.5 * math.cos(2 * math.pi * ((t - D) / u))
            pul = 1 + 0.015 * beat
            P = self.Pstart * (1 - k) + self.P0 * k
            cx = np.where(np.arange(N) < N // 2, 290, 790)[:, None]
            P = np.concatenate([(P[:, :1] - cx) * pul + cx, (P[:, 1:] - 900) * pul + 900], 1)
            return P + wob, self.C0, 1.0
        segs = [(self.t_emb, self.P0, self.C0, self.P1, self.C1, 1.6 * u, True),
                (self.t_pick, self.P1, self.C1, self.P2, self.C2, 1.4 * u, False),
                (self.t_num, self.P2, self.C2, self.P3, self.C3, 1.2 * u, False)]
        for i, (t0, A, CA, B, CB, dur, boom) in enumerate(segs):
            t1 = segs[i + 1][0] if i + 1 < len(segs) else 1e9
            if t < t1:
                k = _ease((t - t0 - self.delay * dur * 0.5) / dur)[:, None]
                if boom:
                    M = A + self.Boom
                else:
                    M = (A + B) / 2 + self.Boom * 0.35
                P = (1 - k) ** 2 * A + 2 * (1 - k) * k * M + k ** 2 * B
                col = CA * (1 - k) + CB * k
                return P + wob, col, 1.0
        return self.P3 + wob, self.C3, 1.0

    def _splat(self, P, col, gain=1.0):
        acc = np.zeros((H, W, 3), np.float32)
        x = np.round(P[:, 0]).astype(np.int32)
        y = np.round(P[:, 1]).astype(np.int32)
        for s in (1, 2, 3):
            sel = self.size >= s
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))[:(1 if s == 1 else 4)]:
                xx, yy = x[sel] + dx * (s - 1), y[sel] + dy * (s - 1)
                ok = (xx >= 0) & (xx < W) & (yy >= 0) & (yy < H)
                np.add.at(acc, (yy[ok], xx[ok]), col[sel][ok] * gain * 0.95)
        return acc

    def frame(self, t):
        u, D = self.u, self.drop
        P, col, _ = self._pos(t)
        acc = self._splat(P, col)
        small = Image.fromarray(np.clip(acc[::4, ::4] * 2.2, 0, 255).astype(np.uint8), 'RGB')
        glow = small.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
        out = self.bg + acc + np.asarray(glow, np.float32) * 0.7
        # вспышка на дропе
        fl = max(0.0, 1 - abs(t - D) / 0.25) if t >= D - 0.05 else 0.0
        if fl > 0:
            out = out + np.array(self.fc, np.float32) * 0.5 * fl
        fr = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        # звёзды
        for sx, sy, ph in self.stars[:120]:
            a = 0.25 + 0.25 * math.sin(t * 2 + ph * 9)
            C.put(fr, C.ellipse(4, 4, (220, 230, 255)), sx * W, sy * H, a)
        m = self.m
        F.header(fr, m, C.seg(t, 0.2, 0.8) * 0.9)
        # подписи по ходу
        if t < self.t_emb:
            a = C.seg(t, 0.6, 1.2) * (1 - C.seg(t, D - 0.3, D))
            C.put(fr, C.text('%s — %s' % (self.h.up, self.a.up), 'unb', 64, (255, 255, 255), 900, max_w=960), W / 2, 470, a)
            C.put(fr, C.text('%s · %s МСК' % (F.lg_ru(m), m['when']), 'mono', 36, (180, 195, 230), 600, track=0.12),
                  W / 2, 545, a)
            C.put(fr, C.text('ЧЕЙ ВЕЧЕР?', 'unb', 56, F.bright(F.club(self.fav), 0.5), 900), W / 2, 1270, C.seg(t, D - 2 * u, D - 1.6 * u) * (1 - C.seg(t, D - 0.2, D)))
        elif t < self.t_pick:
            a = C.seg(t, self.t_emb + 1.6 * u, self.t_emb + 2 * u) * (1 - C.seg(t, self.t_pick - 0.2, self.t_pick))
            C.put(fr, C.text('НАШ ПРОГНОЗ', 'mono', 40, (200, 210, 235), 700, track=0.3), W / 2, 1300, a)
        elif t < self.t_num:
            a = C.seg(t, self.t_pick + 1.2 * u, self.t_pick + 1.6 * u)
            kef = F.fav_kef(m)
            C.put(fr, C.text('НАШ ПРОГНОЗ' + (' · П%s %s' % ('1' if m['side'] == 'h' else '2', C.fmt_k(kef)) if kef else ''),
                             'mono', 40, (200, 210, 235), 700, track=0.2), W / 2, 1080, a * (1 - C.seg(t, self.t_num - 0.2, self.t_num)))
        if t >= self.t_num:
            a = C.seg(t, self.t_num + 0.9 * u, self.t_num + 1.3 * u)
            C.put(fr, C.text('НАША ОЦЕНКА ШАНСА · С УЧЁТОМ ОТ', 'mono', 34, (200, 210, 235), 700, track=0.12, max_w=980), W / 2, 1040, a)
            C.put(fr, C.text(self.m['pick'], 'unb', 50, (255, 255, 255), 900, max_w=980), W / 2, 470, a)
        if t >= self.t_line and m.get('line'):
            a = C.seg(t, self.t_line, self.t_line + 0.5)
            C.put(fr, C.text('ЛИНИЯ (ОСН. ВРЕМЯ)  ' + F.line_text(m), 'mono', 32, (170, 185, 215), 600, max_w=1000), W / 2, 1125, a)
        F.cta(fr, t, self.t_cta, y=1290)
        z = 1.0 + 0.012 * math.sin(t * 0.4)
        dx, dy = C.shake(t, D, 8, 0.3)
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        return C.grain(fr, t, 3)
