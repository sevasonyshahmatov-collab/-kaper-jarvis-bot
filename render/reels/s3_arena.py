# -*- coding: utf-8 -*-
"""Серия 3 · «Табло арены» (трек Can't Say). Тёмная арена в дымке, под сводом висит светодиодный куб-табло (вид снизу,
два экрана в перспективе, бегущие ленты сверху и снизу). Экран живёт по долям: включение, хозяева, гости, VS,
отсчёт 3-2-1 — и на дропе вспышка всех экранов и прогноз; лучи прожекторов ходят по дымке. Дальше карточка и заставка.
Экран — настоящая светодиодная матрица: картинка в низком разрешении, каждый пиксель — круглый диод со свечением.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import fresh as F
from reels import s3

W, H = C.W, C.H
GW, GH = 150, 112            # матрица переднего экрана (диоды)
SW = 56                      # матрица бокового экрана по ширине
P = 4                        # шаг диода, px (до перспективы)
DY = -70                     # сдвиг куба вверх

FRONT = [(170, 450 + DY), (720, 420 + DY), (736, 836 + DY), (154, 884 + DY)]
SIDE = [(720, 420 + DY), (932, 470 + DY), (942, 798 + DY), (736, 836 + DY)]


def _coeffs(src, dst):
    """Коэффициенты Image.PERSPECTIVE: точка выхода dst → точка источника src."""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b += [u, v]
    return np.linalg.solve(np.array(A, float), np.array(b, float))


def warp(img, quad):
    """img (RGBA) на четырёхугольник quad кадра → (слой, x0, y0)."""
    xs, ys = [p[0] for p in quad], [p[1] for p in quad]
    x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
    x1, y1 = int(max(xs)) + 3, int(max(ys)) + 3
    q = [(x - x0, y - y0) for x, y in quad]
    w, h = img.size
    co = _coeffs([(0, 0), (w, 0), (w, h), (0, h)], q)
    out = img.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, tuple(co), Image.BILINEAR)
    return out, x0, y0


_DOT = {}


def led(content, glow=1.0):
    """Матрица gw×gh (RGB) → изображение экрана с круглыми диодами и свечением (RGBA, gw*P × gh*P)."""
    gw, gh = content.size
    key = (gw, gh)
    if key not in _DOT:
        yy, xx = np.mgrid[0:P, 0:P] + 0.5
        d = np.hypot(xx - P / 2, yy - P / 2) / (P / 2)
        cell = np.clip(1.25 - d, 0, 1) ** 1.2
        _DOT[key] = np.tile(cell, (gh, gw))[..., None].astype(np.float32)
    big = np.asarray(content.convert('RGB').resize((gw * P, gh * P), Image.NEAREST), np.float32)
    lit = big * _DOT[key]
    base = np.full_like(lit, 9.0) * _DOT[key] * 0.6               # погасшие диоды чуть видны
    arr = np.maximum(lit, base)
    if glow:
        g = np.asarray(Image.fromarray(big.astype(np.uint8)).filter(ImageFilter.GaussianBlur(P * 0.9)), np.float32)
        arr = arr + g * 0.35 * glow
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    return out


def _txt(d, s, cx, cy, size, fill=(255, 255, 255), font='osw', wght=700, max_w=None):
    f = C.font(font, size, wght)
    w = f.getlength(s)
    if max_w and w > max_w:
        size = int(size * max_w / w)
        f = C.font(font, size, wght)
        w = f.getlength(s)
    asc, desc = f.getmetrics()
    d.text((cx - w / 2, cy - asc * 0.62), s, font=f, fill=fill)


def _emb(t, s):
    e = C.fit(t.emb(s * 3), s, s)
    return e


class Arena(C.Reel):
    def __init__(self, m, u, drop, seed=33):
        super().__init__(u, drop, seed)
        self.m = m
        self.h, self.a = C.match(m['home'], m['away'], m['league'])
        side = s3.pick_side(m, self.h, self.a)
        self.pt = {'h': self.h, 'a': self.a}.get(side)
        b = self.b
        self.t_on = b(-12)
        self.t_card = b(4)
        self.t_kef = b(6)
        self.t_end = b(17)
        self.dur = self.t_end + 2.8
        self.cover_t = b(8)
        self.bg = self._arena()
        self.rib = '%s — %s  •  %s  •  @JARVIBET  •  ' % (self.h.up, self.a.up, s3.sub_line(m))
        f = C.font('osw', 11, 600)
        self.rib_w = f.getlength(self.rib)
        rng = np.random.default_rng(3)
        self.on_rows = rng.uniform(0, 1, GH)
        self.pick_lines = C.lines(m['pick'].upper(), 'osw', 22, GW - 12, (255, 255, 255), 700, gap=0.05, max_lines=3)

    # ── арена ──
    def _arena(self):
        rng = np.random.default_rng(5)
        yy, xx = np.mgrid[0:H, 0:W].astype(float)
        base = np.array((6, 7, 11.))[None, None, :] * np.ones((H, W, 1))
        n = rng.normal(0, 1, (H // 16, W // 16))
        haze = np.array(Image.fromarray((n * 40 + 128).clip(0, 255).astype('uint8')).resize((W, H), Image.BICUBIC)
                        .filter(ImageFilter.GaussianBlur(30)), float) / 255
        glow = np.exp(-(((xx - 540) / 620) ** 2 + ((yy - 640) / 560) ** 2))
        arr = base + (glow * (16 + 22 * haze))[..., None] * np.array((0.55, 0.65, 1.0))[None, None, :]
        img = Image.fromarray(np.clip(arr, 0, 255).astype('uint8'), 'RGB').convert('RGBA')
        d = ImageDraw.Draw(img)
        # трибуны: ярусы далёких огоньков
        for k in range(9):
            y = 1080 + k * 44
            for i in range(160):
                x = rng.uniform(-40, W + 40)
                yy_ = y + 26 * math.sin(x / W * math.pi) * -1 + rng.normal(0, 6)
                c = int(rng.uniform(30, 95))
                r = rng.uniform(0.8, 1.8)
                d.ellipse((x - r, yy_ - r, x + r, yy_ + r), fill=(c, c, int(c * 1.1), 255))
        # фермы и тросы к своду
        for x0, x1 in ((230, 200), (690, 720), (900, 980)):
            d.line((x1, 0, x0, 400 + DY), fill=(40, 44, 54, 255), width=3)
        for k in range(4):
            y = 70 + k * 22
            d.line((0, y, W, y + 10), fill=(22, 24, 32, 255), width=2)
        return C.vignette(img, 0.5, 2.0).convert('RGBA')

    # ── содержимое экранов ──
    def screen(self, t):
        u, D_ = self.u, self.drop
        b = self.b
        img = Image.new('RGB', (GW, GH), (0, 0, 0))
        d = ImageDraw.Draw(img)
        pulse = 1.0
        if t < b(-11):
            _txt(d, s3.lg_ru(self.m), GW / 2, GH / 2 - 14, 40, (255, 255, 255))
            _txt(d, self.m['date'].upper(), GW / 2, GH / 2 + 22, 15, s3.GOLD)
        elif t < b(-4):
            tm = self.h if t < b(-7) else self.a
            e = _emb(tm, 62)
            img.paste(e.convert('RGB'), (int(GW / 2 - e.width / 2), 10), e)
            _txt(d, tm.up, GW / 2, 92, 22, (255, 255, 255), max_w=GW - 10)
            ph = ((t - b(-11)) / u) % 1
            pulse = 1 + 0.25 * math.exp(-ph * 6)
        elif t < b(-3):
            for tm, x in ((self.h, GW * 0.24), (self.a, GW * 0.76)):
                e = _emb(tm, 50)
                img.paste(e.convert('RGB'), (int(x - e.width / 2), int(GH / 2 - e.height / 2)), e)
            _txt(d, 'VS', GW / 2, GH / 2, 28, s3.GOLD)
        elif t < D_:
            k = 3 - int((t - b(-3)) // u)
            ph = ((t - b(-3)) / u) % 1
            _txt(d, str(k), GW / 2, GH / 2 + 4, int(96 - 14 * ph), (255, 255, 255))
            pulse = 1 + 0.35 * math.exp(-ph * 5)
        elif t < b(1.5):
            _txt(d, 'ПРОГНОЗ', GW / 2, GH / 2, 30, s3.GOLD)
        else:
            pl = self.pick_lines
            sc = min(1.0, (GW - 10) / pl.width, (GH - 34) / pl.height)
            pl2 = pl.resize((max(1, int(pl.width * sc)), max(1, int(pl.height * sc))), Image.LANCZOS)
            img.paste(pl2.convert('RGB'), (int(GW / 2 - pl2.width / 2), int((GH - 26) / 2 - pl2.height / 2)), pl2)
            _txt(d, 'КЭФ ' + s3.kef_s(self.m['kef']), GW / 2, GH - 16, 16, s3.GOLD)
        arr = np.asarray(img, np.float32) * pulse
        # включение: строки загораются вразнобой
        if t < self.t_on + 0.45:
            q = C.seg(t, self.t_on, self.t_on + 0.45)
            mask = (self.on_rows < q)[:, None, None]
            arr = arr * mask
        # вспышка на дропе
        if D_ <= t < D_ + 0.5:
            k = math.exp(-(t - D_) * 9)
            arr = arr + (255 - arr) * k
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')

    def side_screen(self, t):
        D_ = self.drop
        img = Image.new('RGB', (SW, GH), (0, 0, 0))
        tm = None
        if t < self.b(-7):
            tm = self.h
        elif t < self.b(-4):
            tm = self.a
        elif t >= D_ and self.pt is not None:
            tm = self.pt
        if tm is not None and t >= self.b(-11):
            e = _emb(tm, 44)
            img.paste(e.convert('RGB'), (int(SW / 2 - e.width / 2), int(GH / 2 - e.height / 2)), e)
        elif t >= self.b(-11):
            d = ImageDraw.Draw(img)
            _txt(d, 'VS' if t < D_ else s3.kef_s(self.m['kef']), SW / 2, GH / 2, 20, s3.GOLD)
        arr = np.asarray(img, np.float32)
        if t < self.t_on + 0.45:
            arr = arr * (self.on_rows < C.seg(t, self.t_on, self.t_on + 0.45))[:, None, None]
        if D_ <= t < D_ + 0.5:
            k = math.exp(-(t - D_) * 9)
            arr = arr + (255 - arr) * k
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')

    def ribbon(self, t, gw):
        img = Image.new('RGB', (gw, 9), (0, 0, 0))
        if t < self.t_on + 0.2:
            return img
        d = ImageDraw.Draw(img)
        f = C.font('osw', 11, 600)
        off = (t * 38) % self.rib_w
        x = -off
        while x < gw:
            d.text((x, -3), self.rib, font=f, fill=(255, 196, 92))
            x += self.rib_w
        return img

    def frame(self, t):
        D_ = self.drop
        fr = self.bg.copy()
        scr = self.screen(t)
        mean = np.asarray(scr, np.float32).mean((0, 1))
        # свет экрана в дымке
        lum = C.radial(1300, 1100, tuple(int(min(255, 40 + v * 2.2)) for v in mean), int(min(140, 30 + mean.mean() * 1.3)), 1.6)
        fr = C.add_light(fr, lum, 540, 640 + DY, 0.7)
        # прожекторы после дропа
        if t >= D_ - 0.1:
            beams = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            bd = ImageDraw.Draw(beams)
            for i, (x0, ph) in enumerate(((120, 0.0), (960, 1.7), (380, 3.1), (720, 4.4))):
                ang = math.radians(-90 + 28 * math.sin(t * 1.3 + ph))
                L = 1500
                spread = math.radians(5)
                pts = [(x0, 1500), (x0 + L * math.cos(ang - spread), 1500 + L * math.sin(ang - spread)),
                       (x0 + L * math.cos(ang + spread), 1500 + L * math.sin(ang + spread))]
                bd.polygon(pts, fill=(170, 190, 255, 38))
            beams = beams.filter(ImageFilter.GaussianBlur(18))
            k = C.seg(t, D_ - 0.1, D_ + 0.2)
            ph = ((t - D_) / self.u) % 1 if t > D_ else 0
            fr = C.add_light(fr, beams, W / 2, H / 2, k * (0.9 + 0.5 * math.exp(-ph * 4)))
        # куб: днище, экраны, ленты
        dk = ImageDraw.Draw(fr)
        under = [FRONT[3], FRONT[2], SIDE[2], (SIDE[2][0] - 210, SIDE[2][1] + 70), (FRONT[3][0] + 40, FRONT[3][1] + 64)]
        dk.polygon([(x, y + 52) for x, y in under[:2]] + [(SIDE[2][0], SIDE[2][1] + 52)] +
                   [(x, y + 52) for x, y in under[3:]], fill=(12, 13, 17, 255))
        for i in range(6):
            x = C.lerp(FRONT[3][0] + 80, SIDE[2][0] - 60, i / 5)
            y = C.lerp(FRONT[3][1] + 80, SIDE[2][1] + 70, i / 5)
            C.put(fr, C.radial(26, 14, (255, 236, 200), 220, 1.2), x, y)
        for quad, gw, img in ((FRONT, GW, scr), (SIDE, SW, self.side_screen(t))):
            face = led(img)
            # рамка экрана
            fw, fh = face.size
            frame_ = Image.new('RGBA', (fw + 24, fh + 24), (18, 19, 24, 255))
            frame_.alpha_composite(face, (12, 12))
            # ленты сверху и снизу
            rib = led(self.ribbon(t + (0 if gw == GW else 7), gw), glow=0.8)
            band = Image.new('RGBA', (fw + 24, rib.height + 14), (14, 15, 19, 255))
            band.alpha_composite(rib, (12, 7))
            full = Image.new('RGBA', (fw + 24, fh + 24 + 2 * band.height), (0, 0, 0, 0))
            full.alpha_composite(band, (0, 0))
            full.alpha_composite(frame_, (0, band.height))
            full.alpha_composite(band, (0, band.height + fh + 24))
            k = band.height / (fh + 24)
            (x0, y0), (x1, y1), (x2, y2), (x3, y3) = quad
            q = [(x0 + (x0 - x3) * k, y0 + (y0 - y3) * k), (x1 + (x1 - x2) * k, y1 + (y1 - y2) * k),
                 (x2 + (x2 - x1) * k, y2 + (y2 - y1) * k), (x3 + (x3 - x0) * k, y3 + (y3 - y0) * k)]
            if gw == SW:
                full = Image.fromarray((np.asarray(full, np.float32) * np.array((0.78, 0.78, 0.78, 1))).astype(np.uint8), 'RGBA')
            lay, lx, ly = warp(full, q)
            fr.alpha_composite(lay, (lx, ly))
        # ребро куба — светлая грань
        dk = ImageDraw.Draw(fr)
        dk.line((FRONT[1][0], FRONT[1][1] - 40, FRONT[2][0], FRONT[2][1] + 40), fill=(60, 64, 76, 255), width=3)
        # карточка прогноза
        if t >= self.t_card:
            q = C.out_expo(C.seg(t, self.t_card, self.t_card + 0.55))
            card = s3.pick_card(self.m, self.h, self.a, kef_q=C.out_back(C.seg(t, self.t_kef, self.t_kef + 0.35)))
            ccy = 1195
            C.put(fr, C.shadow(card, r=30, a=0.7), W / 2, ccy + 18 + 320 * (1 - q), q)
            C.put(fr, card, W / 2, ccy + 320 * (1 - q), q)
        # камера: крупно на кубе, наезд к дропу, удар; к карточке — отъезд, куб уходит наверх
        back = C.in_out(C.seg(t, self.t_card - 0.25, self.t_card + 0.5))
        z = 1.17 + 0.05 * C.in_out(C.seg(t, 0, D_))
        if t >= D_:
            z = 1.22 + 0.05 * math.exp(-(t - D_) * 6)
        z = C.lerp(z, 1.0, back)
        dy = -150 * (1 - back)
        sx, sy = C.shake(t, D_, amp=16, d=0.4)
        fr = C.zoom(fr.convert('RGB'), z, cx=540, cy=615, dx=sx, dy=dy + sy)
        fr = C.grain(fr, t, 6)
        return s3.wipe_in(fr, s3.end_card(t, self.t_end), t, self.t_end)
