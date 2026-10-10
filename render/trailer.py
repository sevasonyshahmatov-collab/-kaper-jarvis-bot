# -*- coding: utf-8 -*-
"""Ролики-трейлеры под трек: три разных подачи, всё на долях трека (track_sync).

    import trailer
    trailer.cinema(match, 'out.mp4', beat=1.0, drop=8.0, track=..., track_start=...)     # «Кино»
    trailer.hype(match, 'out.mp4', beat=0.6316, drop=2.53, stop=10.2, drop2=12.64, ...)    # «Хайп»
    trailer.vhs(match, 'out.mp4', beat=1.0, drop=4.0, ...)                                  # «VHS»

match = dict(home, away, league, when, pred, coef).
«Кино» — тёмный киношный трейлер: полосы кадра, дым, луч прожектора, титры по одному («ДВА КЛУБА.»), на дропе —
вспышка, эмблемы в свете, анаморфный блик, название матча; прогноз — аккуратная плашка; финал — JARVIS и @jarvibet.
«Хайп» — яркое промо: заливки цветами клубов, эмблемы в два цвета, бегущие строки, контурный текст, стикеры;
на стопе трека — пауза («ГОТОВ?»), на втором ударе — всё вместе.
«VHS» — запись на кассету: «PLAY ▶», «REC ●», помехи, строчная развёртка, хромированные буквы; прогноз —
экранное меню видеомагнитофона.
"""
import math
import os
import random
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

import nhl
import nhl_kit
import poster
import shorts as base

W, H, FPS = base.W, base.H, base.FPS
put, alpha = base._put, base._alpha
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
_F, _T = {}, {}
FILES = {'unb': ('Unbounded[wght].ttf', [None]), 'osw': ('Oswald[wght].ttf', [None]), 'tek': ('Tektur[wdth,wght].ttf', [100, None]),
         'mono': ('JetBrainsMono[wght].ttf', [None]), 'russo': ('RussoOne-Regular.ttf', None), 'onest': ('Onest[wght].ttf', [None])}


def F(name, size, wght=700):
    key = (name, int(size), wght)
    if key not in _F:
        f, ax = FILES[name]
        ft = ImageFont.truetype(os.path.join(FD, f), int(size))
        if ax:
            try:
                ft.set_variation_by_axes([wght if a is None else a for a in ax])
            except Exception:
                pass
        _F[key] = ft
    return _F[key]


def T(s, name, size, fill=(255, 255, 255), wght=700, track=0.0, stroke=0, outline=False, max_w=None):
    """Строка текста RGBA (кеш). track — разрядка в долях кегля; outline — только контур толщиной stroke."""
    key = (s, name, int(size), fill, wght, track, stroke, outline, max_w)
    if key in _T:
        return _T[key]
    while True:
        f = F(name, size, wght)
        ws = [f.getlength(c) for c in s]
        tw = sum(ws) + track * size * max(0, len(s) - 1)
        if not max_w or tw <= max_w or size < 20:
            break
        size = int(size * max_w / tw)
    asc, desc = f.getmetrics()
    pad = int(size * 0.15) + stroke
    im = Image.new('RGBA', (int(tw) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for c, w in zip(s, ws):
        if outline:
            d.text((x, pad), c, font=f, fill=(0, 0, 0, 0), stroke_width=stroke, stroke_fill=fill + (255,))
        else:
            d.text((x, pad), c, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=(0, 0, 0, 255) if stroke else None)
        x += w + track * size
    _T[key] = im
    return im


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def p(t, a, b):
    return 0.0 if t <= a else 1.0 if t >= b else (t - a) / (b - a)


def win(t, a, b, fi=0.25, fo=0.25):
    """Прозрачность для окна [a, b]: проявление и угасание."""
    if t < a or t >= b:
        return 0.0
    return min(1.0, p(t, a, a + fi) if fi else 1.0, 1 - p(t, b - fo, b) if fo else 1.0)


def scaled(im, s):
    return im if abs(s - 1) < 0.003 else im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)


def light(fr, im, cx, cy, k=1.0):
    """Сложить свет (аддитивно) — для бликов и сияния."""
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    put(lay, im, cx, cy)
    rgb = lay.convert('RGB')
    a = lay.getchannel('A').point(lambda v: int(v * k))
    rgb = Image.composite(rgb, Image.new('RGB', (W, H)), a)
    out = ImageChops.add(fr.convert('RGB'), rgb)
    return out.convert('RGBA')


def glow(im, r=18, k=1.6):
    """Свечение вокруг элемента: размытая копия под ним."""
    pad = r * 3
    big = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(im, (pad, pad))
    g = big.filter(ImageFilter.GaussianBlur(r))
    g.putalpha(g.getchannel('A').point(lambda v: min(255, int(v * k))))
    g.alpha_composite(big)
    return g


def flare(length=1400, color=(150, 200, 255)):
    """Анаморфный блик: тонкая длинная полоса света с ядром."""
    im = Image.new('RGBA', (length, 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 70, length, 90), fill=color + (200,))
    d.ellipse((length / 2 - 160, 50, length / 2 + 160, 110), fill=(255, 255, 255, 230))
    return im.filter(ImageFilter.GaussianBlur(9))


def duotone(im, dark, bright):
    g = ImageOps.autocontrast(ImageOps.grayscale(im.convert('RGB')), cutoff=1)
    out = ImageOps.colorize(g, dark, bright).convert('RGBA')
    out.putalpha(im.getchannel('A'))
    return out


def chrome(s, name, size, wght=900, track=0.02, max_w=None):
    """Хромированные буквы: «горизонт» в заливке, тёмный контур, лёгкое сияние."""
    m = T(s, name, size, (255, 255, 255), wght, track, 0, False, max_w)
    h, w = m.height, m.width
    y = np.linspace(0, 1, h)[:, None]
    g = np.where(y < 0.52, 0.30 + 0.70 * (np.clip(y, 0, 0.52) / 0.52) ** 0.8, 0.12 + 0.55 * (np.clip(y - 0.52, 0, 1) / 0.48) ** 1.4)
    g = np.repeat(g, w, axis=1)
    rgb = np.stack([g * 235 + 10, g * 240 + 12, g * 250 + 18], axis=-1)
    out = Image.fromarray(np.clip(rgb, 0, 255).astype('uint8'), 'RGB').convert('RGBA')
    out.putalpha(m.getchannel('A'))
    edge = m.getchannel('A').filter(ImageFilter.MaxFilter(5))
    sh = Image.new('RGBA', (w, h), (8, 10, 18, 0))
    sh.putalpha(edge)
    sh.alpha_composite(out)
    return sh


class _Base:
    def __init__(self, m, beat, seed=None):
        self.league = 'NHL' if str(m.get('league', 'KHL')).upper() == 'NHL' else 'KHL'
        if self.league == 'NHL':
            nhl.register()
        h, a = nhl_kit._prep(m['home'], m['away'])
        self.home, self.away = h, a
        self.hn, self.an = poster.SHORT.get(h, h).upper(), poster.SHORT.get(a, a).upper()
        self.c1, self.c2 = poster.BANNER[h], poster.BANNER[a]
        self.when, self.pred, self.coef = m.get('when'), m.get('pred'), m.get('coef')
        self.acc = poster.ACC if self.league == 'KHL' else nhl.ICE
        self.beat = beat
        self.seed = sum(map(ord, h + a)) % 997 if seed is None else seed
        self.rnd = random.Random(self.seed)
        self.flashes, self.shakes, self.punches = [], [], []

    def emb(self, team, size):
        return poster._raw_emblem(team, size, size)

    def camera(self, fr, t):
        z, sx, sy = 1.0, 0.0, 0.0
        for (tp, s, d) in self.punches:
            if 0 <= t - tp < d:
                z += s * (1 - (t - tp) / d) ** 2
        for (ts, amp, d) in self.shakes:
            if 0 <= t - ts < d:
                a = amp * (1 - (t - ts) / d) ** 2
                sx += a * math.sin((t - ts) * 90)
                sy += a * math.cos((t - ts) * 71)
        for (tf, al, d, col) in self.flashes:
            if 0 <= t - tf < d:
                fr.alpha_composite(Image.new('RGBA', (W, H), col + (int(255 * al * (1 - (t - tf) / d) ** 2),)))
        z = max(z, 1 + 2.2 * max(abs(sx) / W, abs(sy) / H))
        if z > 1.001:
            cw, ch = W / z, H / z
            fr = fr.resize((W, H), Image.BILINEAR, box=(W / 2 - cw / 2 + sx, H / 2 - ch / 2 + sy, W / 2 + cw / 2 + sx, H / 2 + ch / 2 + sy))
        return fr

    def hit(self, t, k=1.0, flash=0.0, col=(255, 255, 255)):
        self.punches.append((t, 0.05 * k, 0.3))
        self.shakes.append((t, 14 * k, 0.3))
        if flash:
            self.flashes.append((t, flash, 0.3, col))

    def render(self, path, track=None, track_start=0.0, cover_t=None):
        saved = poster.FONTS7
        poster.FONTS7 = dict(saved, **poster.FONTS_SIDE)
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            base._Audio(self.dur, self.seed).write(wav, self.dur)
            if track:
                base._mix_track(wav, track, track_start, self.dur, 0.0)
            cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                   '-r', str(FPS), '-i', '-', '-i', wav, '-shortest', '-c:v', 'libx264', '-preset', 'medium', '-crf', '21',
                   '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', path]
            pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            try:
                for i in range(int(round(self.dur * FPS))):
                    pr.stdin.write(self.frame(i / FPS).convert('RGB').tobytes())
            finally:
                pr.stdin.close()
                code = pr.wait()
                os.unlink(wav)
            if code != 0:
                raise RuntimeError('ffmpeg не собрал ролик: %s' % path)
            if cover_t is not None:
                self.frame(cover_t).convert('RGB').save(os.path.splitext(path)[0] + '_cover.jpg', quality=93)
            return path
        finally:
            poster.FONTS7 = saved


# ═══════════════════════════════ «КИНО» ═══════════════════════════════
class Cinema(_Base):
    """Тёмный киношный трейлер. drop — время дропа в ролике (до него — тихие титры)."""

    def __init__(self, m, beat, drop, seed=None):
        super().__init__(m, beat, seed)
        b = beat
        self.drop = drop
        self.dur = drop + 11 * b
        rng = np.random.default_rng(self.seed)
        n = np.zeros((H // 8 + 40, W // 8 + 40))                      # дым: несколько октав шума, медленно плывёт
        for o, amp in ((24, 1.0), (12, 0.5), (6, 0.25)):
            r = rng.normal(0, 1, (n.shape[0] // o + 2, n.shape[1] // o + 2))
            n += amp * np.asarray(Image.fromarray(((r - r.min()) / (r.max() - r.min()) * 255).astype('uint8')).resize((n.shape[1], n.shape[0]), Image.BICUBIC), np.float32) / 255
        n = (n - n.min()) / (n.max() - n.min())
        sm = Image.fromarray((np.clip(n - 0.35, 0, 1) * 150).astype('uint8')).resize((W + 320, H + 320), Image.BICUBIC)
        self.smoke = Image.new('RGBA', sm.size, (170, 185, 210, 0))
        self.smoke.putalpha(sm)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        cone = np.clip(1 - np.abs(xx - W / 2) / (90 + yy * 0.42), 0, 1) ** 1.6 * np.clip(1 - yy / (H * 0.9), 0, 1)
        self.beam = Image.new('RGBA', (W, H), (200, 215, 255, 0))
        self.beam.putalpha(Image.fromarray((cone * 120).astype('uint8')))
        vig = np.clip(1.15 - 1.05 * np.sqrt(((xx / W - 0.5) * 1.1) ** 2 + ((yy / H - 0.5) * 0.9) ** 2) ** 1.5, 0, 1)
        self.vig = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        self.vig.putalpha(Image.fromarray(((1 - vig) * 255).astype('uint8')))
        self.flare = flare(1600, (120, 180, 255))
        self.e1, self.e2 = self.emb(self.home, 470), self.emb(self.away, 470)
        self.embers = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1.5, 4), rng.uniform(40, 120), rng.uniform(0, 6)) for _ in range(70)]
        self.hit(drop, 1.4, 0.9)
        for k in (4, 6, 8):
            self.hit(drop + k * b, 0.6, 0.35)

    def frame(self, t):
        b, D = self.beat, self.drop
        fr = Image.new('RGBA', (W, H), (4, 5, 8, 255))
        lit = 0.35 + 0.65 * p(t, D - 2 * b, D) if t < D else 1.0
        put(fr, alpha(self.smoke, 0.55 * lit), W / 2 + 120 * math.sin(t * 0.13), H / 2 - 50 * math.sin(t * 0.21))
        fr = light(fr, self.beam, W / 2, H / 2, 0.25 + 0.75 * (lit if t >= D else lit * 0.6))
        d = ImageDraw.Draw(fr)
        for (x, y, r, v, ph) in self.embers:                           # искры поднимаются в луче
            if t >= D - b:
                yy = (y - v * t) % H
                d.ellipse((x - r, yy - r, x + r, yy + r), fill=(255, 200, 140, int(140 * (0.5 + 0.5 * math.sin(t * 3 + ph)))))
        # 1) титры до дропа — по одному, медленный наезд
        cards = [('ДВА КЛУБА.', 0.0), ('ОДИН ЛЁД.', D * 0.36), ('ОДИН ПРОГНОЗ.', D * 0.68)]
        for i, (s, a) in enumerate(cards):
            z = cards[i + 1][1] if i + 1 < len(cards) else D - 0.15
            k = win(t, a + 0.15, z, 0.5, 0.35)
            if k:
                im = scaled(T(s, 'unb', 84, (236, 240, 248), 300, 0.26, 0, False, 1000), 1 + 0.06 * p(t, a, z))
                put(fr, alpha(glow(im, 10, 1.2), k), W / 2, H / 2)
        if D - 0.5 <= t < D:                                           # блик тянется перед дропом
            fr = light(fr, scaled(self.flare, 0.3 + 0.7 * p(t, D - 0.5, D)), W / 2, H / 2, p(t, D - 0.5, D))
        # 2) дроп: эмблемы в свете, название матча
        if D <= t < D + 4 * b:
            u = t - D
            k = ease(p(u, 0, 0.5))
            s = 1.08 - 0.08 * k + 0.04 * p(u, 0, 4 * b)
            for e, x in ((self.e1, W / 2 - 240), (self.e2, W / 2 + 240)):
                put(fr, alpha(glow(scaled(e, s), 26, 1.0), k), x + (x - W / 2) * 0.06 * p(u, 0, 4 * b), 760)
            put(fr, alpha(glow(T('×', 'unb', 90, (255, 255, 255), 300), 12), k), W / 2, 760)
            t1 = T(self.hn, 'unb', 92, (255, 255, 255), 800, 0.06, 0, False, 960)
            t2 = T(self.an, 'unb', 92, (255, 255, 255), 800, 0.06, 0, False, 960)
            put(fr, alpha(t1, win(u, b, 9, 0.3, 0)), W / 2, 1110)
            put(fr, alpha(glow(T('ПРОТИВ', 'unb', 48, self.acc, 600, 0.5), 8), win(u, 1.5 * b, 9, 0.3, 0)), W / 2, 1210)
            put(fr, alpha(t2, win(u, 2 * b, 9, 0.3, 0)), W / 2, 1310)
            fr = light(fr, self.flare, W / 2 + 500 * math.sin(u * 0.6) - 0, 760, 0.8 * (1 - p(u, 0, 1.2)) + 0.2)
        # 3) когда и прогноз — плашка
        if D + 4 * b <= t < D + 8 * b:
            u = t - D - 4 * b
            put(fr, alpha(glow(T(self.when or '', 'unb', 56, (230, 236, 246), 500, 0.14, 0, False, 980), 8), win(u, 0, 9, 0.35, 0)), W / 2, 520)
            for e, x in ((self.e1, W / 2 - 150), (self.e2, W / 2 + 150)):
                put(fr, alpha(scaled(e, 0.5), win(u, 0.2, 9, 0.4, 0)), x, 760)
            k = ease(p(u, 2 * b, 2 * b + 0.6))
            if k:
                pl = self.plate()
                put(fr, alpha(pl, k), W / 2, 1150 + 40 * (1 - k))
                if u < 2 * b + 1.2:
                    fr = light(fr, scaled(self.flare, 0.7), W / 2 - 600 + 1200 * p(u, 2 * b, 2 * b + 1.2), 1150, 0.7)
        # 4) финал
        if t >= D + 8 * b:
            u = t - D - 8 * b
            put(fr, alpha(glow(T('JARVIS', 'unb', 150, (255, 255, 255), 800, 0.18), 20, 1.3), ease(p(u, 0, 0.6))), W / 2, 820)
            put(fr, alpha(T('ПРОГНОЗЫ НА ХОККЕЙ — В TELEGRAM', 'unb', 44, (220, 226, 238), 500, 0.08, 0, False, 990), win(u, 0.4, 9, 0.4, 0)), W / 2, 990)
            put(fr, alpha(glow(T('@jarvibet', 'unb', 96, self.acc, 700, 0.02), 14), win(u, b, 9, 0.4, 0)), W / 2, 1120)
            fr = light(fr, self.flare, W / 2, 820, 0.6 * (1 - p(u, 0, 1.5)) + 0.15)
        fr.alpha_composite(self.vig)
        bar = 210                                                      # киношные полосы
        d = ImageDraw.Draw(fr)
        d.rectangle((0, 0, W, bar), fill=(0, 0, 0, 255))
        d.rectangle((0, H - bar, W, H), fill=(0, 0, 0, 255))
        return self.camera(fr, t)

    def plate(self):
        w, h = 940, 230
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, w - 1, h - 1), fill=(8, 10, 16, 200), outline=(255, 255, 255, 90), width=2)
        d.rectangle((0, 0, 8, h), fill=self.acc + (255,))
        put(im, T('ПРОГНОЗ', 'unb', 34, self.acc, 600, 0.3), 50 + T('ПРОГНОЗ', 'unb', 34, self.acc, 600, 0.3).width / 2, 52)
        put(im, T(str(self.pred).upper(), 'unb', 64, (255, 255, 255), 700, 0.0, 0, False, w - 100), w / 2, 130)
        if self.coef:
            c = T('КЭФ %.2f' % float(self.coef), 'unb', 42, self.acc, 700, 0.1)
            put(im, c, w - 40 - c.width / 2, 52)
        return im


# ═══════════════════════════════ «ХАЙП» ═══════════════════════════════
class Hype(_Base):
    """Яркое промо: drop — первый удар, stop — начало паузы трека, drop2 — второй удар (если есть)."""

    def __init__(self, m, beat, drop, stop=None, drop2=None, seed=None):
        super().__init__(m, beat, seed)
        b = beat
        self.drop, self.stop, self.drop2 = drop, stop, drop2
        self.dur = (drop2 + 8 * b) if drop2 else drop + 20 * b
        dk1 = tuple(int(v * 0.35) for v in self.c1)
        dk2 = tuple(int(v * 0.35) for v in self.c2)
        self.d1 = duotone(self.emb(self.home, 820), dk1, (255, 255, 255))
        self.d2 = duotone(self.emb(self.away, 820), dk2, (255, 255, 255))
        self.e1, self.e2 = self.emb(self.home, 300), self.emb(self.away, 300)
        self.mq1 = self.marquee(self.hn)
        self.mq2 = self.marquee(self.an)
        self.mqp = self.marquee('ПРОГНОЗ', (16, 16, 20), self.acc)
        n = int((self.stop or self.dur) - drop) // b
        for k in range(int(n) + 1):
            self.hit(drop + k * b, 0.7 if k % 2 else 1.0, 0.25 if k % 4 == 0 else 0.0)
        if drop2:
            self.hit(drop2, 1.5, 0.8)

    def marquee(self, s, fg=(255, 255, 255), bg=None):
        unit = T(s + '   •   ', 'osw', 120, fg, 700, 0.02)
        band = Image.new('RGBA', (unit.width * 6, unit.height + 20), (bg + (255,)) if bg else (0, 0, 0, 0))
        for i in range(6):
            band.alpha_composite(unit, (i * unit.width, 10))
        return band, unit.width

    def band(self, fr, mq, y, t, speed, angle, k=1.0):
        im, uw = mq
        off = (t * speed) % uw
        strip = im.crop((int(off), 0, int(off) + int(W * 1.6), im.height))
        strip = strip.rotate(angle, resample=Image.BICUBIC, expand=True)
        put(fr, alpha(strip, k), W / 2, y)

    def frame(self, t):
        b, D = self.beat, self.drop
        beat_i = int((t - D) // b) if t >= D else -1
        if t < D:                                                      # вступление: заливки по долям, контурное имя
            col = self.c1 if int(t / b) % 2 == 0 else self.c2
            fr = Image.new('RGBA', (W, H), col + (255,))
            name = self.hn if int(t / b) % 2 == 0 else self.an
            put(fr, T(name, 'osw', 300, (255, 255, 255), 700, 0.0, 6, True, 1500), W / 2 - 200 * (t % b) / b, H / 2)
            put(fr, T('СЕГОДНЯ', 'unb', 40, (255, 255, 255), 800, 0.5), W / 2, 420)
        elif self.stop and self.stop <= t < (self.drop2 or 1e9):         # пауза трека: тишина, вопрос
            u = t - self.stop
            fr = Image.new('RGBA', (W, H), (8, 8, 10, 255))
            put(fr, alpha(T('ГОТОВ?', 'unb', 120, (255, 255, 255), 900, 0.08), ease(p(u, 0.1, 0.5))), W / 2, H / 2 - 40)
            put(fr, alpha(T(self.when or '', 'unb', 36, self.acc, 500, 0.2, 0, False, 980), ease(p(u, 0.6, 1.0))), W / 2, H / 2 + 90)
        elif self.drop2 and t >= self.drop2:                           # второй удар: всё вместе
            u = t - self.drop2
            fr = Image.new('RGBA', (W, H), (12, 12, 16, 255))
            half = Image.new('RGBA', (W, H // 2), self.c1 + (255,))
            fr.alpha_composite(half, (0, 0))
            fr.alpha_composite(Image.new('RGBA', (W, H // 2), self.c2 + (255,)), (0, H // 2))
            put(fr, alpha(self.d1, 0.35), W * 0.3, H * 0.25)
            put(fr, alpha(self.d2, 0.35), W * 0.7, H * 0.75)
            self.band(fr, self.mq1, 330, u, 260, 7)
            self.band(fr, self.mq2, 1590, u, -260, 7)
            k = ease(p(u, 0, 0.35))
            put(fr, scaled(glow(self.e1, 16), 0.8 + 0.2 * k), W / 2 - 280, 720)
            put(fr, scaled(glow(self.e2, 16), 0.8 + 0.2 * k), W / 2 + 280, 720)
            put(fr, T('VS', 'unb', 80, (255, 255, 255), 900, 0.0, 5, False), W / 2, 720)
            self.sticker(fr, u, 1080)
            ks = ease(p(u, 3 * b, 3 * b + 0.4))
            if ks:
                tg = self.tg_sticker()
                put(fr, alpha(tg.rotate(-3, resample=Image.BICUBIC, expand=True), ks), W / 2, 1330 + 30 * (1 - ks))
        else:                                                          # после первого удара: нарезка по долям
            i = beat_i % 8
            u = t - (D + beat_i * b)
            if i in (0, 1):
                fr = Image.new('RGBA', (W, H), self.c1 + (255,))
                put(fr, scaled(self.d1, 1.0 + 0.08 * u / b), W / 2, H / 2 - 40)
                self.band(fr, self.mq1, 1400, t, 300, -8)
            elif i in (2, 3):
                fr = Image.new('RGBA', (W, H), self.c2 + (255,))
                put(fr, scaled(self.d2, 1.0 + 0.08 * u / b), W / 2, H / 2 - 40)
                self.band(fr, self.mq2, 480, t, -300, 8)
            elif i == 4:
                fr = Image.new('RGBA', (W, H), (14, 14, 18, 255))
                put(fr, T('VS', 'unb', 520, (255, 255, 255), 900, 0.0, 10, True), W / 2, H / 2)
            else:
                fr = Image.new('RGBA', (W, H), (14, 14, 18, 255))
                self.band(fr, self.mqp, 360, t, 380, -6)
                self.band(fr, self.mqp, 1560, t, -380, -6)
                self.sticker(fr, t - (D + (beat_i - i + 5) * b), H / 2)
        return self.camera(fr, t)

    def sticker(self, fr, u, y):
        """Прогноз — стикер: белая плашка с текстом и кэф отдельной наклейкой."""
        k = ease(p(u, 0, 0.3))
        if not k:
            return
        txt = T(str(self.pred).upper(), 'osw', 96, (14, 14, 18), 700, 0.0, 0, False, 820)
        pl = Image.new('RGBA', (txt.width + 80, txt.height + 40), (255, 255, 255, 255))
        put(pl, txt, pl.width / 2, pl.height / 2)
        pl = pl.rotate(3, resample=Image.BICUBIC, expand=True)
        put(fr, alpha(scaled(pl, 1.15 - 0.15 * k), k), W / 2, y)
        if self.coef:
            kk = ease(p(u, 0.25, 0.55))
            if kk:
                c = T('×%.2f' % float(self.coef), 'unb', 64, (14, 14, 18), 900)
                st = Image.new('RGBA', (c.width + 50, c.height + 20), self.acc + (255,))
                put(st, c, st.width / 2, st.height / 2)
                st = st.rotate(-7, resample=Image.BICUBIC, expand=True)
                put(fr, alpha(scaled(st, 1.3 - 0.3 * kk), kk), W / 2 + 300, y + 120)

    def tg_sticker(self):
        a = T('ПОДПИСЫВАЙСЯ', 'unb', 34, (14, 14, 18), 800, 0.1)
        h2 = T('@jarvibet', 'unb', 66, (14, 14, 18), 900)
        w = max(a.width, h2.width) + 200
        im = Image.new('RGBA', (w, 190), (255, 255, 255, 255))
        put(im, base._tg_icon(120), 95, 95)
        put(im, a, 175 + a.width / 2, 62)
        put(im, h2, 175 + h2.width / 2, 128)
        return im


# ═══════════════════════════════ «VHS» ═══════════════════════════════
class Vhs(_Base):
    """Кассета: «PLAY ▶» до дропа, на дропе — хром и строб, прогноз — меню видеомагнитофона, «STOP ■» в конце."""

    def __init__(self, m, beat, drop, seed=None):
        super().__init__(m, beat, seed)
        b = beat
        self.drop = drop
        self.dur = drop + 12 * b
        lines = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lines)
        for y in range(0, H, 4):
            d.line((0, y, W, y), fill=(0, 0, 0, 70), width=2)
        self.scan = lines
        rng = np.random.default_rng(self.seed)
        self.noise = []
        for _ in range(5):
            a = (rng.random((H // 3, W // 3)) * 255).astype('uint8')
            im = Image.fromarray(a, 'L').resize((W, H), Image.NEAREST)
            self.noise.append(Image.merge('RGBA', (im, im, im, Image.new('L', (W, H), 34))))
        self.e1, self.e2 = self.emb(self.home, 420), self.emb(self.away, 420)
        self.ch1 = chrome(self.hn, 'unb', 150, 900, 0.02, 1000)
        self.ch2 = chrome(self.an, 'unb', 150, 900, 0.02, 1000)
        self.chj = chrome('JARVIS', 'unb', 190, 900, 0.04, 1000)
        for k in range(0, 8):
            self.hit(drop + k * b, 1.0 if k % 2 == 0 else 0.5, 0.5 if k % 2 == 0 else 0.0)

    def osd(self, s, size=54, col=(235, 245, 235)):
        """Надпись экранного меню (Tektur); значков ▶ ■ в нём нет — берём их из Unbounded."""
        key = ('osd', s, size, col)
        if key in _T:
            return _T[key]
        while True:
            fs = [F('unb', size * 0.8, 700) if c in '▶■' else F('tek', size, 700) for c in s]
            ws = [f.getlength(c) + size * 0.06 for f, c in zip(fs, s)]
            if sum(ws) <= 980 or size < 24:
                break
            size = int(size * 980 / sum(ws))
        asc, desc = F('tek', size, 700).getmetrics()
        pad = int(size * 0.2)
        im = Image.new('RGBA', (int(sum(ws)) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        x = pad
        for f, c, w in zip(fs, s, ws):
            d.text((x, pad + (asc + desc) / 2), c, font=f, fill=col + (255,), anchor='lm')
            x += w
        _T[key] = im
        return im

    def frame(self, t):
        b, D = self.beat, self.drop
        if t < D:                                                      # синий экран, PLAY, помехи
            fr = Image.new('RGBA', (W, H), (18, 32, 150, 255) if t < D * 0.45 else (10, 10, 14, 255))
            if t < D * 0.45:
                put(fr, self.osd('PLAY ▶', 90), W / 2 - 150, 420)
                put(fr, self.osd('КАССЕТА · %s' % ('КХЛ' if self.league == 'KHL' else 'НХЛ'), 48), W / 2, H / 2 + 260)
            else:
                fr.alpha_composite(self.noise[int(t * 20) % len(self.noise)])
                k = p(t, D * 0.45, D)
                put(fr, alpha(self.osd('%s — %s' % (self.hn, self.an), 70), min(1, k * 2)), W / 2, H / 2)
                put(fr, alpha(self.osd(self.when or '', 44, (220, 220, 220)), min(1, k * 2)), W / 2, H / 2 + 100)
        elif t < D + 4 * b:                                            # хром и строб
            u = t - D
            i = int(u / (b / 2))
            fr = Image.new('RGBA', (W, H), (6, 6, 10, 255) if i % 2 == 0 else (24, 24, 30, 255))
            e, ch, col = (self.e1, self.ch1, self.c1) if (i // 2) % 2 == 0 else (self.e2, self.ch2, self.c2)
            g = Image.new('RGBA', (W, H), col + (0,))
            gm = Image.new('L', (W, H), 0)
            ImageDraw.Draw(gm).ellipse((W / 2 - 520, 380, W / 2 + 520, 1300), fill=110)
            g.putalpha(gm.filter(ImageFilter.GaussianBlur(120)))
            fr.alpha_composite(g)
            put(fr, scaled(e, 1.0 + 0.1 * (u % b) / b), W / 2, 760)
            put(fr, glow(ch, 14, 0.9), W / 2, 1180)
        elif t < D + 8 * b:                                            # меню прогноза
            u = t - D - 4 * b
            fr = Image.new('RGBA', (W, H), (8, 10, 14, 255))
            put(fr, scaled(self.e1, 0.55), W / 2 - 170, 470)
            put(fr, scaled(self.e2, 0.55), W / 2 + 170, 470)
            rows = [('ПРОГНОЗ', str(self.pred).upper())] + ([('КЭФ', '%.2f' % float(self.coef))] if self.coef else []) + [('ВРЕМЯ', (self.when or '').split(' · ')[-1])]
            y = 780
            for j, (k_, v) in enumerate(rows):
                if u < j * b * 0.75:
                    break
                sel = j == min(len(rows) - 1, int(u / (b * 0.75)))
                lab = self.osd(('▶ ' if sel else '  ') + k_, 46, (255, 255, 120) if sel else (210, 220, 210))
                val = self.osd(v, 64 if j == 0 else 58, (255, 255, 255))
                put(fr, lab, 110 + lab.width / 2, y)
                put(fr, val, W - 110 - val.width / 2 if val.width < 600 else W / 2, y + (0 if val.width < 600 else 90))
                y += 170 if val.width < 600 else 250
        else:                                                          # финал
            u = t - D - 8 * b
            fr = Image.new('RGBA', (W, H), (6, 6, 10, 255))
            put(fr, glow(self.chj, 16, 1.0), W / 2, 760)
            put(fr, self.osd('ПОДПИСКА ▶ TELEGRAM', 52, (255, 255, 120)), W / 2, 980)
            put(fr, self.osd('@jarvibet', 92, (255, 255, 255)), W / 2, 1110)
            if u > 3 * b:
                put(fr, self.osd('STOP ■', 70), W / 2, 1320)
        # оверлей камеры: REC, время, развёртка, сдвиг цветов, полоса трекинга
        if t >= D * 0.45:
            dd = ImageDraw.Draw(fr)
            if int(t * 2) % 2 == 0:
                dd.ellipse((90, 230, 130, 270), fill=(240, 40, 40, 255))
            put(fr, self.osd('REC', 46, (255, 255, 255)), 200, 250)
            tc = '00:%02d:%02d' % (int(t) // 60, int(t) % 60)
            put(fr, self.osd(tc, 44), W - 230, 250)
            put(fr, self.osd('SP', 40), W - 120, H - 470)
        fr.alpha_composite(self.scan)
        rgb = fr.convert('RGB')
        r, g, bl = rgb.split()
        rgb = Image.merge('RGB', (ImageChops.offset(r, 4, 0), g, ImageChops.offset(bl, -4, 0)))
        ty = int((t * 420) % (H + 300)) - 150                         # полоса трекинга ползёт вниз
        if 0 <= ty < H - 60:
            band = rgb.crop((0, ty, W, ty + 60))
            rgb.paste(ImageChops.offset(band, 18, 0).point(lambda v: min(255, int(v * 1.25))), (0, ty))
        fr = rgb.convert('RGBA')
        fr.alpha_composite(self.noise[int(t * 24) % len(self.noise)])
        return self.camera(fr, t)


def cinema(m, path, beat, drop, track=None, track_start=0.0):
    c = Cinema(m, beat, drop)
    return c.render(path, track, track_start, cover_t=drop + 6.5 * beat)


def hype(m, path, beat, drop, stop=None, drop2=None, track=None, track_start=0.0):
    c = Hype(m, beat, drop, stop, drop2)
    return c.render(path, track, track_start, cover_t=(drop2 + 4 * beat) if drop2 else drop + 6 * beat)


def vhs(m, path, beat, drop, track=None, track_start=0.0):
    c = Vhs(m, beat, drop)
    return c.render(path, track, track_start, cover_t=drop + 6.5 * beat)
