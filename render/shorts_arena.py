# -*- coding: utf-8 -*-
"""Ролики «Арена» — третий стиль Shorts / VK Клипов под трек: эфирная графика хоккейной трансляции.

    import shorts_arena as arena
    arena.pick('Трактор', 'Амур', 'ЧТ 08.10 · 17:00 МСК', 'Тотал меньше 4,5', 2.00, 'out.mp4', league='KHL',
               odds=(1.93, 3.69, 3.51), beat=0.8333, track='трек.wav', track_start=9.40)

Фон — арена: тёмные трибуны с огоньками и лучами прожекторов, борт, внизу лёд с разметкой (синяя и красная
линии, круг вбрасывания). Всё остальное — плашки, как в эфирной графике: шапка «МАТЧ ДНЯ», плашки команд в цветах
клубов с эмблемами, фишки линии П1/Х/П2, прогноз — одна плашка «ПРОГНОЗ | текст | КЭФ» внизу (не на весь экран),
в конце плашка подписки в Telegram. Плашки выезжают в такт трека плавно, без пружины, по каждой пробегает блик;
камера медленно наезжает, на дропе — вспышка. Одна композиция без смены «экранов»: картинка собирается к концу,
последний кадр годится в обложку (cover=True сохраняет *_cover.jpg).
"""
import math
import os
import random
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import nhl
import nhl_kit
import poster
import shorts as base

W, H, FPS = base.W, base.H, base.FPS
put, alpha = base._put, base._alpha
ACC = {'KHL': poster.ACC, 'NHL': nhl.ICE}
DARK = (12, 16, 26)
WHITE = (246, 248, 252)


def expo(x):
    x = min(1.0, max(0.0, x))
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def p(t, a, b):
    return 0.0 if t <= a else 1.0 if t >= b else (t - a) / (b - a)


def font(kind, size):
    return poster._f7(kind, int(size))


def _skew(im, k=0.18):
    """Наклон плашки, как в эфирной графике."""
    w, h = im.size
    return im.transform((w + int(h * k), h), Image.AFFINE, (1, k, -h * k, 0, 1, 0), Image.BICUBIC)


def _shine(im, k):
    """Блик, пробегающий по плашке (k 0→1)."""
    if not 0 < k < 1:
        return im
    w, h = im.size
    band = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(band)
    x = -0.3 * w + 1.6 * w * k
    d.polygon([(x, h), (x + 0.12 * w, 0), (x + 0.2 * w, 0), (x + 0.08 * w, h)], fill=110)
    band = band.filter(ImageFilter.GaussianBlur(12))
    a = ImageChops.darker(band, im.getchannel('A'))                    # блик — только по самой плашке
    out = im.copy()
    out.alpha_composite(Image.merge('RGBA', (Image.new('L', (w, h), 255),) * 3 + (a,)))
    return out


class _Arena:
    def __init__(self, home, away, league, when, pred, coef, odds, beat, seed=None):
        self.league = 'NHL' if str(league).upper() == 'NHL' else 'KHL'
        if self.league == 'NHL':
            nhl.register()
        self.acc = ACC[self.league]
        h, a = nhl_kit._prep(home, away)
        self.home, self.away = h, a
        self.hn, self.an = poster.SHORT.get(h, h).upper(), poster.SHORT.get(a, a).upper()
        self.c1, self.c2 = poster.BANNER[h], poster.BANNER[a]
        self.when, self.pred, self.coef, self.odds = when, pred, coef, odds
        self.beat = beat
        self.seed = sum(map(ord, h + a)) % 997 if seed is None else seed
        bar = 4 * beat
        self.B = [k * bar for k in range(7)]
        self.dur = self.B[5]
        self._assets()

    # ── арена ──
    def _assets(self):
        rng = np.random.default_rng(self.seed)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        top = np.array((7, 11, 22), np.float32)
        mid = np.array((16, 26, 52), np.float32)
        k = np.clip(yy / 1200, 0, 1)[..., None]
        sky = top * (1 - k) + mid * k
        ice_t = np.clip((yy - 1240) / 680, 0, 1)[..., None]
        ice = np.array((150, 172, 196), np.float32) * (1 - ice_t) + np.array((214, 226, 238), np.float32) * ice_t
        img = np.where((yy >= 1240)[..., None], ice, sky)
        r = np.sqrt(((xx / W - 0.5) * 1.1) ** 2 + ((yy / H - 0.55) * 0.8) ** 2)
        img = img * np.clip(1.12 - 0.75 * r, 0.35, 1.0)[..., None]
        base_im = Image.fromarray(np.clip(img, 0, 255).astype('uint8'), 'RGB').convert('RGBA')
        d = ImageDraw.Draw(base_im)
        # разметка льда в перспективе: синяя линия, красная центральная, круг вбрасывания — подо льдом (размыто)
        marks = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        md = ImageDraw.Draw(marks)
        md.polygon([(-200, 1420), (W + 200, 1420), (W + 260, 1465), (-260, 1465)], fill=(30, 70, 170, 150))
        md.polygon([(-300, 1650), (W + 300, 1650), (W + 380, 1700), (-380, 1700)], fill=(190, 30, 40, 140))
        md.ellipse((W / 2 - 430, 1740, W / 2 + 430, 1940), outline=(190, 30, 40, 130), width=10)
        md.ellipse((W / 2 - 20, 1830, W / 2 + 20, 1850), fill=(190, 30, 40, 150))
        base_im.alpha_composite(marks.filter(ImageFilter.GaussianBlur(2)))
        # царапины коньков
        sc = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sc)
        for _ in range(140):
            x0, y0 = rng.uniform(-100, W), rng.uniform(1250, H)
            ln, ang = rng.uniform(60, 320), rng.uniform(-0.35, 0.35)
            sd.line((x0, y0, x0 + ln * math.cos(ang), y0 + ln * math.sin(ang) * 0.4), fill=(255, 255, 255, int(rng.uniform(25, 70))), width=1)
        base_im.alpha_composite(sc)
        # борт: тёмная полоса с отражением и рекламой-полосами цветов клубов
        d.rectangle((0, 1180, W, 1242), fill=(18, 22, 34, 255))
        d.rectangle((0, 1180, W, 1186), fill=(220, 226, 236, 255))
        d.rectangle((0, 1192, W // 2 - 6, 1234), fill=self.c1 + (255,))
        d.rectangle((W // 2 + 6, 1192, W, 1234), fill=self.c2 + (255,))
        for x in range(0, W, 180):
            d.text((x + 40, 1213), 'JARVIS', font=font('brand', 22), fill=(255, 255, 255, 170), anchor='lm')
        refl = base_im.crop((0, 1190, W, 1240)).transpose(Image.FLIP_TOP_BOTTOM)
        base_im.alpha_composite(alpha(refl.filter(ImageFilter.GaussianBlur(3)), 0.25), (0, 1244))
        self.base = base_im
        # огоньки трибун
        self.bokeh = [(rng.uniform(0, W), rng.uniform(140, 1150), rng.uniform(3, 9), rng.uniform(0, 6.3), rng.uniform(0.5, 2.0))
                      for _ in range(110)]
        # лучи прожекторов
        beam = Image.new('L', (900, 1400), 0)
        bd = ImageDraw.Draw(beam)
        bd.polygon([(430, 0), (470, 0), (900, 1400), (0, 1400)], fill=40)
        self.beam = beam.filter(ImageFilter.GaussianBlur(40))
        self.e1 = poster._raw_emblem(self.home, 170, 150)
        self.e2 = poster._raw_emblem(self.away, 170, 150)

    def background(self, t):
        fr = self.base.copy()
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        for i, (x0, ang0, sp) in enumerate(((W * 0.2, -0.35, 0.5), (W * 0.8, 0.35, -0.45), (W * 0.5, 0.0, 0.3))):
            ang = ang0 + 0.22 * math.sin(t * sp + i)
            b = self.beam.rotate(math.degrees(ang), resample=Image.BILINEAR, expand=True)
            col = Image.new('RGBA', b.size, (200, 220, 255, 0))
            col.putalpha(b)
            put(lay, col, x0 + math.sin(ang) * 400, 460)
        d = ImageDraw.Draw(lay)
        for (x, y, r, ph, sp) in self.bokeh:                            # огоньки трибун мерцают
            a = int(60 + 60 * math.sin(t * sp + ph))
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 236, 200, a))
        fr.alpha_composite(lay)
        return fr

    # ── плашки ──
    def header(self):
        acc = self.acc
        w, h = 900, 116
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, w, h), fill=DARK + (235,))
        d.rectangle((0, 0, 270, h), fill=acc + (255,))
        d.text((135, h / 2), 'МАТЧ ДНЯ', font=font('time', 36), fill=DARK + (255,), anchor='mm')
        d.text((270 + (w - 270) / 2, h / 2), ('КХЛ · ' if self.league == 'KHL' else 'НХЛ · ') + (self.when or ''),
               font=font('time', 32), fill=WHITE + (255,), anchor='mm')
        return _skew(im, 0.12)

    def team_plate(self, team, name, col, emb, right=False):
        w, h = 900, 190
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        g = np.zeros((h, w, 4), np.uint8)                              # градиент цвета клуба, к краю темнее
        xs = np.linspace(0, 1, w)[None, :, None]
        c = np.array(col, np.float32)
        rgb = c * (1.0 - 0.45 * (xs if not right else 1 - xs)) + 8
        g[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        g[..., 3] = 240
        im = Image.fromarray(g, 'RGBA')
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, w, 6), fill=(255, 255, 255, 120))
        box = 190
        bx = w - box if right else 0
        d.rectangle((bx, 0, bx + box, h), fill=(250, 250, 252, 255))
        put(im, emb, bx + box / 2, h / 2)
        f = font('team', 104)
        while f.getlength(name) > w - box - 80:
            f = font('team', f.size - 4)
        tx = (w - box) / 2 if right else box + (w - box) / 2
        d.text((tx, h / 2 + 4), name, font=f, fill=(255, 255, 255, 255), anchor='mm')
        return _skew(im, 0.14)

    def chip(self, label, value, hi=False):
        w, h = 300, 112
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=20, fill=DARK + (225,), outline=(self.acc + (255,)) if hi else (255, 255, 255, 70), width=4 if hi else 2)
        d.text((34, h / 2), label, font=font('info', 32), fill=(180, 188, 204, 255), anchor='lm')
        d.text((w - 30, h / 2), value, font=font('num', 56), fill=(self.acc + (255,)) if hi else WHITE + (255,), anchor='rm')
        return im

    def pick_plate(self):
        """Прогноз одной плашкой: ПРОГНОЗ | текст | КЭФ."""
        acc = self.acc
        h = 132
        f_lab, f_txt, f_kef = font('time', 30), font('team', 64), font('num', 58)
        txt = str(self.pred).upper()
        w1 = 200
        w3 = int(f_kef.getlength('%.2f' % float(self.coef)) + f_lab.getlength('КЭФ') + 80) if self.coef else 0
        room = 980 - int(h * 0.12) - w1 - w3 - 70                      # вся плашка с наклоном — не шире 980
        while f_txt.getlength(txt) > room:
            f_txt = font('team', f_txt.size - 2)
        w2 = int(f_txt.getlength(txt)) + 70
        im = Image.new('RGBA', (w1 + w2 + w3, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, w1, h), fill=acc + (255,))
        d.text((w1 / 2, h / 2), 'ПРОГНОЗ', font=f_lab, fill=DARK + (255,), anchor='mm')
        d.rectangle((w1, 0, w1 + w2, h), fill=WHITE + (250,))
        d.text((w1 + w2 / 2, h / 2 + 3), txt, font=f_txt, fill=DARK + (255,), anchor='mm')
        if self.coef:
            d.rectangle((w1 + w2, 0, w1 + w2 + w3, h), fill=DARK + (250,))
            d.text((w1 + w2 + 34, h / 2), 'КЭФ', font=f_lab, fill=(180, 188, 204, 255), anchor='lm')
            d.text((w1 + w2 + w3 - 30, h / 2), '%.2f' % float(self.coef), font=f_kef, fill=acc + (255,), anchor='rm')
        return _skew(im, 0.12), (w1, w1 + w2)

    def tg_plate(self):
        w, h = 900, 150
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, w, h), fill=DARK + (235,))
        d.rectangle((0, 0, 170, h), fill=base.TG_BLUE + (255,))
        put(im, base._tg_icon(112), 85, h / 2)
        d.text((200, 46), 'ПОДПИСЫВАЙТЕСЬ В TELEGRAM', font=font('time', 30), fill=(190, 200, 214, 255), anchor='lm')
        d.text((200, 104), base.HANDLE, font=font('brand', 54), fill=WHITE + (255,), anchor='lm')
        return _skew(im, 0.12)

    # ── кадр ──
    def build(self):
        b, B = self.beat, self.B
        self.items = []                                                # (картинка, x, y, t_in, t_out, откуда, блик)
        brand = base._brand('KXL' if self.league == 'KHL' else 'NHL', self.acc, 52)
        self.items.append((brand, W / 2, 300, 0.0, 1e9, 'fade', False))
        self.items.append((self.header(), W / 2, 450, 0.5 * b, 1e9, 'left', True))
        tp1 = self.team_plate(self.home, self.hn, self.c1, self.e1)
        tp2 = self.team_plate(self.away, self.an, self.c2, self.e2, right=True)
        self.items.append((tp1, W / 2 - 40, 690, B[1] - 0.25, 1e9, 'left', True))
        self.items.append((tp2, W / 2 + 40, 910, B[1] - 0.25, 1e9, 'right', True))
        vs = Image.new('RGBA', (120, 120), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vs)
        vd.ellipse((4, 4, 116, 116), fill=self.acc + (255,), outline=DARK + (255,), width=6)
        vd.text((60, 62), 'VS', font=font('brand', 40), fill=DARK + (255,), anchor='mm')
        self.items.append((vs, W / 2, 800, B[1] + b, 1e9, 'pop', False))
        if self.odds:
            pr = [1 / float(x) for x in self.odds]
            fav = max(range(3), key=lambda i: pr[i])
            for i, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), self.odds)):
                self.items.append((self.chip(lab, '%.2f' % float(v), i == fav), W / 2 + (i - 1) * 322, 1100, B[2] + i * b, B[4], 'up', True))
        pp, _ = self.pick_plate()
        self.items.append((pp, W / 2, 1340, B[3], 1e9, 'left', True))
        self.items.append((self.tg_plate(), W / 2, 1100, B[4], 1e9, 'right', True))

    def frame(self, t):
        fr = self.background(t)
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        for im, x, y, a, z, how, shine in self.items:
            if t < a:
                continue
            if t >= z:                                                 # уходит: уезжает вниз и гаснет
                k = expo(p(t, z, z + 0.35))
                if k >= 1:
                    continue
                put(lay, alpha(im, 1 - k), x, y + 60 * k)
                continue
            k = expo(p(t, a, a + 0.45))
            img = _shine(im, p(t, a + 0.35, a + 1.0)) if shine else im
            if how == 'left':
                put(lay, alpha(img, min(1, k * 1.5)), x - (1 - k) * 900, y)
            elif how == 'right':
                put(lay, alpha(img, min(1, k * 1.5)), x + (1 - k) * 900, y)
            elif how == 'up':
                put(lay, alpha(img, k), x, y + (1 - k) * 80)
            elif how == 'pop':
                s = 0.6 + 0.4 * k
                put(lay, alpha(img.resize((int(img.width * s), int(img.height * s)), Image.BILINEAR), k), x, y)
            else:
                put(lay, alpha(img, k), x, y)
        fr.alpha_composite(lay)
        drop = self.B[1]
        z = 1 + 0.045 * p(t, 0, self.dur)                              # камера медленно наезжает
        if 0 <= t - drop < 0.3:                                        # дроп: вспышка и толчок
            u = (t - drop) / 0.3
            fr.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(140 * (1 - u) ** 2))))
            z += 0.04 * (1 - u) ** 2
        cw, ch = W / z, H / z
        fr = fr.resize((W, H), Image.BILINEAR, box=(W / 2 - cw / 2, H * 0.45 - ch * 0.45, W / 2 + cw / 2, H * 0.45 + ch * 0.55))
        return fr.convert('RGB')

    def render(self, path, track=None, track_start=0.0, cover=False):
        saved = poster.FONTS7
        poster.FONTS7 = dict(saved, **poster.FONTS_SIDE)
        try:
            self.build()
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            base._Audio(self.dur, self.seed).write(wav, self.dur)
            if track:
                base._mix_track(wav, track, track_start, self.dur, 0.0)
            cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                   '-r', str(FPS), '-i', '-', '-i', wav, '-shortest', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                   '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', path]
            pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            try:
                for i in range(int(round(self.dur * FPS))):
                    pr.stdin.write(self.frame(i / FPS).tobytes())
            finally:
                pr.stdin.close()
                code = pr.wait()
                os.unlink(wav)
            if code != 0:
                raise RuntimeError('ffmpeg не собрал ролик: %s' % path)
            if cover:
                self.frame(self.dur - 0.05).save(os.path.splitext(path)[0] + '_cover.jpg', quality=93)
            return path
        finally:
            poster.FONTS7 = saved


def pick(home, away, when, pred, coef, path, league='KHL', odds=None, beat=0.8, track=None, track_start=0.0, seed=None, cover=True):
    """Ролик-прогноз «Арена» под трек (beat — доля сцены из track_sync.analyze)."""
    return _Arena(home, away, league, when, pred, coef, odds, beat, seed).render(path, track, track_start, cover)
