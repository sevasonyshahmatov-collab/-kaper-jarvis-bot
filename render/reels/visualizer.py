# -*- coding: utf-8 -*-
"""«Визуализатор» — кольцо полос спектра, которое двигается под настоящий звук трека.

Спектр считается из самого трека (тот же отрезок, что в предпросмотре): 60 полос по частотам, зеркально по кругу.
До дропа левая половина кольца — цвет хозяев, правая — гостей, в центре обе эмблемы. На дропе кольцо перекрашивается
в цвет фаворита, в центре — его эмблема, пульсирует от баса; от кольца разлетаются искры. Дальше прогноз, линия, шанс.
Без трека (или в версии без звука) рисунок тот же — полосы считаны заранее.
"""
import math
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import fresh as F
from reels.core import FPS, H, W

NB = 60                  # полос на половину кольца
SR = 22050


def _spectrum(track, start, dur):
    """[кадры × NB] 0..1 и бас [кадры] 0..1 по отрезку трека."""
    n_fr = int(round(dur * FPS)) + 2
    if not track:
        return np.zeros((n_fr, NB), np.float32), np.zeros(n_fr, np.float32), np.zeros((n_fr, 256), np.float32)
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-ss', '%.3f' % max(0, start - 0.1), '-t', '%.3f' % (dur + 0.4), '-i', track,
                          '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    off = int(min(0.1, start) * SR)
    nfft = 4096
    win = np.hanning(nfft).astype(np.float32)
    freqs = np.fft.rfftfreq(nfft, 1 / SR)
    edges = np.geomspace(35, 9000, NB + 1)
    bands = [(np.searchsorted(freqs, edges[i]), max(np.searchsorted(freqs, edges[i + 1]), np.searchsorted(freqs, edges[i]) + 1))
             for i in range(NB)]
    spec = np.zeros((n_fr, NB), np.float32)
    bass = np.zeros(n_fr, np.float32)
    wave = np.zeros((n_fr, 256), np.float32)
    for i in range(n_fr):
        c = off + int(i / FPS * SR)
        seg = x[max(0, c - nfft // 2): c + nfft // 2]
        if len(seg) < nfft:
            seg = np.pad(seg, (0, nfft - len(seg)))
        mag = np.abs(np.fft.rfft(seg * win))
        spec[i] = [20 * np.log10(mag[a:b].mean() + 1e-6) for a, b in bands]
        bass[i] = mag[np.searchsorted(freqs, 30):np.searchsorted(freqs, 140)].mean()
        w = x[c: c + 1024]
        wave[i, :len(w[::4])] = w[::4][:256]
    lo, hi = np.percentile(spec, 20), np.percentile(spec, 99.5)
    spec = np.clip((spec - lo) / (hi - lo + 1e-6), 0, 1) ** 1.4
    spec *= np.linspace(0.85, 1.25, NB)[None, :]                # верха тише — поднимем
    for i in range(1, n_fr):                                    # быстрая атака, плавный спад
        spec[i] = np.maximum(spec[i], spec[i - 1] * 0.82)
    bass = np.clip((bass - np.percentile(bass, 10)) / (np.percentile(bass, 98) - np.percentile(bass, 10) + 1e-6), 0, 1)
    for i in range(1, n_fr):
        bass[i] = max(bass[i], bass[i - 1] * 0.86)
    wave = wave / (np.abs(wave).max() + 1e-6)
    return np.clip(spec, 0, 1), bass, wave


class Visualizer(C.Reel):
    def __init__(self, m, u=1.0, drop=3.0, seed=31, track=None, start=0.0):
        super().__init__(u, drop, seed)
        self.m = m
        self.h, self.a = C.match(m['home'], m['away'], m['league'])
        self.fav = self.h if m['side'] == 'h' else self.a
        self.ch = np.array(F.bright(F.club(self.h), 0.25), np.float32)
        self.ca = np.array(F.bright(F.club(self.a), 0.25), np.float32)
        self.cf = np.array(F.bright(F.club(self.fav), 0.3), np.float32)
        D = drop
        self.t_up = D + 2 * u
        self.t_pick = D + 2.5 * u
        self.t_chance = D + 5 * u
        self.t_cta = D + 9 * u
        self.dur = D + 16 * u
        self.cover_t = D + 12 * u
        self.spec, self.bass, self.wave = _spectrum(track, start, self.dur)
        rng = np.random.default_rng(seed)
        self.sparks = [(rng.uniform(0, 2 * math.pi), rng.uniform(0, 1), rng.uniform(120, 260)) for _ in range(140)]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.dist = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - 800) / H) ** 2)
        self.e_h, self.e_a, self.e_f = self.h.emb(150), self.a.emb(150), self.fav.emb(290)

    def _at(self, arr, t):
        i = min(len(arr) - 1, max(0, int(t * FPS)))
        return arr[i]

    def frame(self, t):
        u, D = self.u, self.drop
        spec, bass = self._at(self.spec, t), float(self._at(self.bass, t))
        up = C.in_out(C.seg(t, self.t_up, self.t_up + 0.8))
        cx, cy = W / 2, 800 - 100 * up
        R0 = 230 - 25 * up + 10 * bass
        maxl = 175 - 25 * up
        # фон: тёмный, свечение цветом фаворита от баса после дропа
        post = C.seg(t, D, D + 1.2 * u)
        glowc = self.cf * post + (self.ch + self.ca) / 2 * (1 - post)
        base = np.stack([10 + 0 * self.dist] * 3, -1) + (1 - np.clip(self.dist * 2.2, 0, 1))[..., None] * glowc[None, None, :] * (0.10 + 0.22 * bass)
        fl = max(0.0, 1 - abs(t - D) / 0.22) if t >= D - 0.05 else 0.0
        base = base + self.cf * 0.4 * fl
        fr = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        # кольцо полос (рисуем вдвое крупнее и уменьшаем — гладкие края)
        SS = 2
        box = int((R0 + maxl + 40) * 2)
        lay = Image.new('RGBA', (box * SS, box * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        c0 = box * SS / 2
        sweep = C.seg(t, D, D + 1.2 * u)                      # перекраска в цвет фаворита идёт по кругу
        for side in (-1, 1):
            for i in range(NB):
                ang = math.pi / 2 + side * (math.pi * (i + 0.5) / NB)          # снизу вверх по обе стороны
                v = float(spec[i])
                ln = 10 + maxl * v
                col0 = self.ch if side == 1 else self.ca
                k = 1.0 if sweep >= 1 else float(np.clip(sweep * 1.3 - (i / NB) * 0.3, 0, 1))
                col = col0 * (1 - k) + self.cf * k
                col = col * (0.75 + 0.25 * v) + 255 * 0.25 * v
                r1, r2 = (R0 + 8) * SS, (R0 + 8 + ln) * SS
                x1, y1 = c0 + math.cos(ang) * r1, c0 - math.sin(ang) * r1
                x2, y2 = c0 + math.cos(ang) * r2, c0 - math.sin(ang) * r2
                d.line((x1, y1, x2, y2), fill=tuple(int(c) for c in np.clip(col, 0, 255)) + (255,), width=9 * SS)
        # волна внутри кольца
        wv = self._at(self.wave, t)
        pts = []
        for j in range(257):
            a = 2 * math.pi * j / 256
            rr = (R0 - 22 + 16 * wv[j % 256]) * SS
            pts.append((c0 + math.cos(a) * rr, c0 + math.sin(a) * rr))
        d.line(pts, fill=(255, 255, 255, 110), width=3 * SS)
        lay = lay.resize((box, box), Image.LANCZOS)
        gl = lay.filter(ImageFilter.GaussianBlur(14))
        C.put(fr, gl, cx, cy, 0.8)
        C.put(fr, lay, cx, cy)
        # искры
        for ang, ph, sp in self.sparks:
            prog = (ph + t * sp / 600) % 1
            rr = R0 + maxl * 0.6 + prog * 420
            a = (1 - prog) * (0.25 + 0.75 * bass) * C.seg(t, 0.3, 1.0)
            col = tuple(int(c) for c in (self.cf if t > D else (self.ch if math.cos(ang) > 0 else self.ca)))
            C.put(fr, C.ellipse(6, 6, col), cx + math.cos(ang) * rr, cy + math.sin(ang) * rr, a)
        # центр: тёмный диск и эмблемы
        disk = C.ellipse(int(2 * (R0 - 32)), int(2 * (R0 - 32)), (14, 14, 20))
        C.put(fr, disk, cx, cy)
        m = self.m
        if t < D + 0.3 * u:
            a = 1 - C.seg(t, D, D + 0.3 * u)
            C.put(fr, self.e_h, cx - 85, cy - 10, a)
            C.put(fr, self.e_a, cx + 85, cy - 10, a)
            C.put(fr, C.text('VS', 'unb', 34, (200, 200, 210), 900), cx, cy + 105, a)
        else:
            q = C.out_back(C.seg(t, D + 0.2 * u, D + 1.0 * u))
            if q > 0:
                C.put(fr, C.scale(self.e_f, max(0.05, q) * (0.94 + 0.08 * bass)), cx, cy)
        F.header(fr, m, C.seg(t, 0.2, 0.8) * 0.9)
        if t < self.t_pick:
            a = C.seg(t, 0.3, 0.9) * (1 - C.seg(t, self.t_pick - 0.3, self.t_pick))
            C.put(fr, C.text('%s — %s' % (self.h.up, self.a.up), 'unb', 58, (255, 255, 255), 900, max_w=960), W / 2, 330, a)
            C.put(fr, C.text('%s · %s МСК' % (F.lg_ru(m), m['when']), 'mono', 34, (180, 185, 200), 600, track=0.12), W / 2, 385, a)
        if t >= self.t_pick:
            q = C.out_expo(C.seg(t, self.t_pick, self.t_pick + 0.5))
            C.put(fr, C.text('НАШ ПРОГНОЗ', 'mono', 34, (200, 205, 220), 700, track=0.3), W / 2, 1085, q)
            C.put(fr, C.text(m['pick'], 'unb', 64, (255, 255, 255), 900, max_w=960), W / 2, 1147 + 30 * (1 - q), q)
            if m.get('line'):
                C.put(fr, C.text('ЛИНИЯ (ОСН. ВРЕМЯ)  ' + F.line_text(m), 'mono', 30, (175, 180, 200), 600, max_w=1000),
                      W / 2, 1208, C.seg(t, self.t_pick + 0.8 * u, self.t_pick + 1.3 * u))
        if t >= self.t_chance:
            q = C.out_expo(C.seg(t, self.t_chance, self.t_chance + 0.5))
            num = C.text('ШАНС %d%%' % m['chance'], 'unb', 84, tuple(int(c) for c in self.cf), 900)
            C.put(fr, C.glow(num, 14, 0.8), W / 2, 1285, q)
            C.put(fr, C.text('НАША ОЦЕНКА · С УЧЁТОМ ОТ', 'mono', 28, (200, 205, 220), 700, track=0.12),
                  W / 2, 1345, C.seg(t, self.t_chance + 0.3, self.t_chance + 0.7) * (1 - C.seg(t, self.t_cta - 0.2, self.t_cta)))
        F.cta(fr, t, self.t_cta, y=1418)
        z = 1.0 + 0.012 * bass
        dx, dy = C.shake(t, D, 8, 0.3)
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        return C.grain(fr, t, 3)
