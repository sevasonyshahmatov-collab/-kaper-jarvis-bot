# -*- coding: utf-8 -*-
"""Серия 3 · «Монетка» (трек Two Faced). Вид сверху на тёмный стол под лампой: эмалевая монета (лицо — хозяева,
оборот — гости) парит и переворачивается на каждую долю, под ней меняется имя клуба. За две доли до дропа — подброс,
на дропе монета падает на стол (удар, пыль, вспышка света) и ложится стороной команды из прогноза.
Дальше монета уходит вверх, снизу выезжает карточка прогноза с кэфом, в конце — заставка на непрозрачном фоне.
"""
import colorsys
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import fresh as F
from reels import s3

W, H = C.W, C.H
D = 600                  # диаметр монеты, px
T = 30                   # толщина ребра, px
CY0 = 880                # центр монеты во вступлении
CY1 = 470                # центр монеты под карточкой прогноза
S1 = 0.7                 # масштаб монеты под карточкой


# ─────────────────────────── металл и эмаль ───────────────────────────
def _gold(v):
    """v 0..1 → цвет золота (тень → тело → блик). v может быть массивом."""
    v = np.clip(v, 0, 1)[..., None]
    c0, c1, c2 = np.array((58, 38, 14.)), np.array((190, 142, 66.)), np.array((255, 238, 186.))
    lo = c0 + (c1 - c0) * np.clip(v / 0.6, 0, 1)
    return np.where(v < 0.6, lo, c1 + (c2 - c1) * np.clip((v - 0.6) / 0.4, 0, 1))


def _enamel_col(t):
    c = F.club(t)
    hh, ll, ss = colorsys.rgb_to_hls(*[x / 255 for x in c])
    if 0.07 < hh < 0.16 or ss < 0.18:            # золото / жёлтый / серый — на золотой монете тёмная эмаль
        c = t.c2 if sum(t.c2) < 200 else (18, 18, 22)
        return tuple(int(x) for x in np.clip(np.array(c, float) * 0.9 + 6, 0, 255))
    return tuple(int(x * 0.62) for x in c)


def _ring_text(img, unit, r, size, col=(70, 48, 16), hi=(255, 236, 184)):
    """Гравировка по всему кругу: unit повторяется, буквы растянуты ровно на окружность; выемка + светлая кромка."""
    cx = cy = D / 2
    gl = {ch: C.text(ch, 'mont', size, (255, 255, 255), 800) for ch in set(unit) if ch != ' '}
    wid = lambda ch: gl[ch].width * 0.84 if ch in gl else size * 0.36
    one = sum(wid(ch) for ch in unit)
    n = max(1, int(round(2 * math.pi * r / one)))
    s = unit * n
    k = 2 * math.pi * r / (one * n)
    a = -math.pi / 2 - wid(s[0]) * k / r / 2
    for ch in s:
        w = wid(ch) * k
        am = a + w / r / 2
        if ch in gl:
            deg = -math.degrees(am) - 90
            for col_, dd in ((hi, 1.4), ((30, 20, 6), -0.8), (col, 0.0)):
                g = C.tint(gl[ch], col_).rotate(deg, resample=Image.BICUBIC, expand=True)
                C.put(img, g, cx + r * math.cos(am) + dd * 0.5, cy + r * math.sin(am) + dd, 1.0 if dd == 0 else 0.7)
        a += w / r


def _wrap(x):
    return (x + math.pi) % (2 * math.pi) - math.pi


def coin_face(t, unit):
    """Лицевая сторона монеты D×D (RGBA): насечка, точёное кольцо с гравировкой, бортик, эмаль, медальон с эмблемой."""
    R = D / 2
    yy, xx = np.mgrid[0:D, 0:D].astype(float) + 0.5
    dx, dy = xx - R, yy - R
    r = np.hypot(dx, dy)
    phi = np.arctan2(dy, dx)
    L = math.radians(-125)                                   # свет — сверху слева
    lam = np.cos(phi - L)
    rng = np.random.default_rng(4)
    lathe = np.convolve(rng.normal(0, 1, int(R) + 8), np.ones(2) / 2, 'same')
    lt = lathe[np.clip(r.astype(int), 0, len(lathe) - 1)]
    spec = np.exp(-_wrap(phi - L) ** 2 / 0.03) + 0.55 * np.exp(-_wrap(phi - L - math.pi) ** 2 / 0.03)
    out = np.zeros((D, D, 3))
    # 1) эмаль: глубокий цвет, гильош-лучи и кольца, светлее к центру
    ec = np.array(_enamel_col(t), float)
    rf = R - 96
    k = np.clip(1 - (r / rf) ** 2, 0, 1)
    gl = 1 + 0.07 * (np.sin(phi * 40) > 0) * np.clip(r / rf, 0, 1) + 0.03 * np.sin(r * 0.7)
    out[:] = ec[None, None, :] * ((0.7 + 0.45 * k) * gl)[..., None]
    # 2) бортик вокруг эмали (выпуклый)
    m = (r >= rf) & (r < rf + 10)
    pr = (r - rf) / 10
    out[m] = _gold(0.45 + 0.4 * np.cos((pr - 0.5) * math.pi) * (0.55 + 0.45 * np.where(pr < 0.5, -lam, lam)) + 0.25 * spec)[m]
    # 3) точёное кольцо: анизотропный блик по лучу света, скосы по краям, следы резца
    r0, r1 = rf + 10, R - 20
    m = (r >= r0) & (r < r1)
    v = 0.36 + 0.16 * lam + 0.55 * spec + 0.035 * lt
    v = v + 0.28 * np.clip(1 - (r - r0) / 7, 0, 1) * (-lam) + 0.28 * np.clip(1 - (r1 - r) / 7, 0, 1) * lam
    out[m] = _gold(v)[m]
    # 4) канавка
    m = (r >= R - 20) & (r < R - 15)
    out[m] = _gold(0.14 + 0.08 * lam)[m]
    # 5) насечка по краю
    m = r >= R - 15
    rid = 0.5 + 0.5 * np.cos(phi * 200)
    out[m] = _gold(0.3 + 0.22 * rid + 0.2 * lam + 0.25 * spec * rid - 0.25 * np.clip((r - R + 3) / 3, 0, 1))[m]
    a = np.clip(R - r + 0.5, 0, 1) * 255
    img = Image.fromarray(np.dstack([np.clip(out, 0, 255), a]).astype('uint8'), 'RGBA')
    _ring_text(img, unit, (r0 + r1) / 2, 27)
    # медальон с эмблемой: утоплен в эмаль, золотой ободок
    md = int(rf * 2 * 0.6)
    gold_rim = Image.fromarray(np.dstack([_gold(0.5 + 0.35 * lam + 0.3 * spec), np.full((D, D), 255.)]).astype('uint8'), 'RGBA')
    ring_m = Image.new('L', (D, D), 0)
    ImageDraw.Draw(ring_m).ellipse((R - md / 2 - 7, R - md / 2 - 7, R + md / 2 + 7, R + md / 2 + 7), fill=255)
    gold_rim.putalpha(ring_m.filter(ImageFilter.GaussianBlur(0.7)))
    C.put(img, C.shadow(gold_rim.crop((int(R - md / 2 - 10), int(R - md / 2 - 10), int(R + md / 2 + 10), int(R + md / 2 + 10))),
                        r=8, a=0.6), R + 3, R + 7)
    img.alpha_composite(gold_rim)
    med = C.ellipse(md, md, (244, 240, 230))
    inner = C.radial(md, md, (255, 255, 255), 0)
    yv = np.linspace(0, 1, md)
    sh = np.clip(1 - np.hypot(*np.meshgrid(yv * 2 - 1, yv * 2 - 1)), 0, 1)
    medc = np.array(med, float)
    medc[..., :3] *= (0.86 + 0.14 * np.clip(sh * 3, 0, 1))[..., None]
    med = Image.fromarray(medc.astype('uint8'), 'RGBA')
    C.put(img, med, R, R)
    es = int(md * 0.72)
    C.put(img, C.fit(t.emb(es), es, es), R, R)
    # общий глянец: мягкая диагональная полоса по всей монете
    gl_ = C.lgrad(D, D, (255, 255, 255), (255, 255, 255), angle=55, a1=0, a2=0)
    ga = np.clip(1 - np.abs((dx * 0.57 + dy * 0.82) / R + 0.45) / 0.35, 0, 1) ** 2 * 38
    gl_.putalpha(Image.fromarray(np.minimum(ga, a).astype('uint8')))
    img.alpha_composite(gl_)
    return img


def _edge_strip():
    """Ребро монеты (D×T): цилиндр — светлее по центру, насечка сжимается к краям."""
    x = (np.arange(D) + 0.5) / D * 2 - 1
    ang = np.arcsin(np.clip(x, -1, 1))
    rid = 0.5 + 0.5 * np.cos(ang * 90)
    v = 0.22 + 0.32 * np.cos(ang) ** 1.5 + 0.12 * rid
    yv = np.linspace(0, 1, T)
    v2 = v[None, :] * (0.85 + 0.25 * np.sin(yv * math.pi))[:, None]
    return np.clip(_gold(v2), 0, 255)


# ─────────────────────────── стол ───────────────────────────
def _table(seed=3):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (H // 2, W // 2))
    big = np.array(Image.fromarray(((n * 30) + 128).clip(0, 255).astype('uint8')).filter(ImageFilter.GaussianBlur(14))
                   .resize((W, H), Image.BICUBIC), float) - 128
    fine = rng.normal(0, 1, (H, W)) * 5
    base = np.array((19, 18, 17.))[None, None, :] + (big * 0.16 + fine)[..., None]
    return C.vignette(Image.fromarray(np.clip(base, 0, 255).astype('uint8'), 'RGB'), 0.55, 2.2)


class Coin(C.Reel):
    def __init__(self, m, u, drop, seed=12):
        super().__init__(u, drop, seed)
        self.m = m
        self.h, self.a = C.match(m['home'], m['away'], m['league'])
        side = s3.pick_side(m, self.h, self.a) or 'h'
        lg = s3.lg_ru(m)
        self.face = {k: coin_face(t, '%s  •  %s  •  ' % (t.up, lg)) for k, t in (('h', self.h), ('a', self.a))}
        self.edge = _edge_strip()
        self.side = side
        self.table = _table()
        self.pool = C.radial(1500, 1500, (255, 214, 150), 120, power=1.7)
        # тайминг
        self.t_toss = self.b(-2)
        self.t_up = self.b(3)
        self.t_card = self.b(3.5)
        self.t_kef = self.b(6)
        self.t_end = self.b(15)
        self.dur = self.t_end + 2.8
        self.cover_t = self.b(8)
        # углы: вступление — полуоборот на каждую долю, подброс — 11 полуоборотов, лечь нужной стороной
        self.n_intro = int(round(self.t_toss / u))
        th0 = math.pi * (self.n_intro - 1)
        n = 11
        if (self.n_intro - 1 + n) % 2 != (0 if side == 'h' else 1):
            n += 1
        self.th_toss, self.th_end = th0, th0 + math.pi * n
        self.hook = s3.hook('%s ИЛИ %s?' % (self.h.up, self.a.up), 80)
        self.sub = C.text(s3.sub_line(m), 'mont', 30, s3.GOLD, 700, track=0.14)
        self.names = {k: C.text(t.up, 'unb', 62, (255, 255, 255), 800, track=0.04, max_w=980)
                      for k, t in (('h', self.h), ('a', self.a))}
        self.lab = C.text('НАШ ПРОГНОЗ', 'mont', 34, s3.GOLD, 800, track=0.3)
        rng = np.random.default_rng(5)
        self.dust = [(rng.uniform(0, 2 * math.pi), rng.uniform(0.9, 1.15), rng.uniform(120, 420), rng.uniform(1.5, 4.5),
                      rng.uniform(0.5, 1.0)) for _ in range(70)]
        self.motes = [(rng.uniform(0, W), rng.uniform(300, 1450), rng.uniform(0, 6.28), rng.uniform(1, 2.6)) for _ in range(26)]

    # ── движение монеты: угол, высота (0 — на столе), смещение центра и масштаб раскладки ──
    def state(self, t):
        u, D_ = self.u, self.drop
        if t < self.t_toss:
            n = int(t // u)
            fr = (t - n * u) / u
            th = math.pi * max(0, n - 1 + C.in_out(C.clamp(fr / 0.62))) if n >= 1 else 0.0
            h = 0.2 + 0.03 * math.sin(t * 2.1)
            if t < 0.5:
                h = 0.2 * C.out_cubic(t / 0.5) + 0.03 * math.sin(t * 2.1)
        elif t < self.t_toss + 0.4 * u:
            q = C.seg(t, self.t_toss, self.t_toss + 0.4 * u)
            th = self.th_toss
            h = 0.2 + 0.03 * math.sin(self.t_toss * 2.1) - 0.15 * C.in_out(q)
        elif t < D_:
            t1 = self.t_toss + 0.4 * u
            q = C.seg(t, t1, D_)
            th = self.th_toss + (self.th_end - self.th_toss) * (1 - (1 - q) ** 1.6)
            h = 0.06 + 4 * 1.05 * q * (1 - q) - 0.06 * q
        else:
            q = t - D_
            th = self.th_end + 0.42 * math.exp(-7 * q) * math.sin(q * 34)
            h = 0.07 * abs(math.sin(q * math.pi / 0.22)) * math.exp(-q * 9) if q < 0.6 else 0.0
        mv = C.in_out(C.seg(t, self.t_up, self.t_up + 0.7))
        cy = C.lerp(CY0, CY1, mv)
        sc = C.lerp(1.0, S1, mv)
        return th, max(0.0, h), cy, sc

    def coin_layer(self, th, s=1.0):
        """Монета под углом th (переворот вокруг горизонтальной оси). Возвращает RGBA и маску силуэта."""
        c, sn = math.cos(th), math.sin(th)
        face = self.face['h' if c >= 0 else 'a']
        dd = max(2, int(round(D * s)))
        hf = max(2, int(round(dd * abs(c))))
        e = int(round(T * s * abs(sn)))
        ww, hh = dd, hf + e + 2
        lay = np.zeros((hh, ww, 4))
        if e > 0:
            xs = (np.arange(ww) + 0.5) / ww * 2 - 1
            half = hf / 2 * np.sqrt(np.clip(1 - xs ** 2, 0, 1))
            ys = np.arange(hh)[:, None] + 0.5
            top = hf / 2 - half[None, :]
            bot = hf / 2 + e + half[None, :]
            inside = np.clip(np.minimum(ys - top, bot - ys) + 0.5, 0, 1) * (np.abs(xs) <= 1)[None, :]
            strip = np.array(Image.fromarray(self.edge.astype('uint8')).resize((ww, max(1, e)), Image.BILINEAR), float)
            col = np.zeros((hh, ww, 3))
            col[:] = strip.mean(0)[None, :, :]
            shade = 0.55 + 0.45 * abs(c)
            lay[..., :3] = col * shade
            lay[..., 3] = inside * 255
        img = Image.fromarray(lay.astype('uint8'), 'RGBA')
        f = face.resize((dd, hf), Image.LANCZOS) if (dd, hf) != face.size else face
        # свет: при наклоне лицо темнеет, по нему скользит блик
        fa = np.array(f, float)
        tilt = abs(c)
        fa[..., :3] *= 0.62 + 0.38 * tilt ** 0.6
        yy = np.arange(hf)[:, None] / max(1, hf)
        xx = np.arange(dd)[None, :] / dd
        pos = 0.5 + 0.75 * sn * (1 if c >= 0 else -1) - 0.18
        band = np.exp(-((xx * 0.55 + yy * 0.45 - pos) / 0.11) ** 2) * (0.22 + 0.5 * (1 - tilt))
        fa[..., :3] = fa[..., :3] + (255 - fa[..., :3]) * band[..., None]
        f = Image.fromarray(np.clip(fa, 0, 255).astype('uint8'), 'RGBA')
        img.alpha_composite(f, (0, 0))
        return img

    def coin_blur(self, t, s):
        th, *_ = self.state(t)
        if self.t_toss + 0.4 * self.u < t < self.drop:
            dt = 1 / C.FPS
            acc = None
            ims = [self.coin_layer(self.state(t + k * dt / 6)[0], s) for k in range(-3, 3)]
            hh = max(i.height for i in ims)
            for im in ims:
                cnv = Image.new('RGBA', (ims[0].width, hh), (0, 0, 0, 0))
                cnv.alpha_composite(im, (0, (hh - im.height) // 2))
                a = np.array(cnv, float)
                acc = a if acc is None else acc + a
            acc /= len(ims)
            return Image.fromarray(acc.astype('uint8'), 'RGBA')
        return self.coin_layer(th, s)

    def frame(self, t):
        u, D_ = self.u, self.drop
        th, h, cy, sc = self.state(t)
        fr = self.table.copy().convert('RGBA')
        # свет лампы: пятно на столе под монетой; вспышка на ударе и лёгкая пульсация на доли после дропа
        flash = 0.0
        if t >= D_:
            flash = 0.55 * math.exp(-(t - D_) * 7)
            ph = ((t - D_) / u) % 1
            flash += 0.06 * math.exp(-ph * 5)
        k = 0.85 + flash
        C.put(fr, self.pool, W / 2, cy + 40, min(1.0, k))
        if k > 1:
            fr = C.add_light(fr, self.pool, W / 2, cy + 40, (k - 1) * 0.8)
        # пыль в луче
        for x, y, p, r in self.motes:
            yy = (y - t * 22 * r) % 1250 + 250
            xx = x + 30 * math.sin(t * 0.6 + p)
            a = 0.25 + 0.25 * math.sin(t * 1.3 + p * 3)
            C.put(fr, C.ellipse(int(r * 3), int(r * 3), (255, 230, 190)), xx, yy, a * 0.5)
        s = sc * (1 + 0.55 * h)
        coin = self.coin_blur(t, s)
        # тень на столе: силуэт, размытый и смещённый по высоте
        sh_a = coin.getchannel('A')
        blur = 6 + 40 * h
        pad = int(blur * 2 + 20)
        sh = Image.new('L', (coin.width + 2 * pad, coin.height + 2 * pad), 0)
        sh.paste(sh_a, (pad, pad))
        sh = sh.filter(ImageFilter.GaussianBlur(blur))
        shi = Image.new('RGBA', sh.size, (0, 0, 0, 255))
        shi.putalpha(sh.point(lambda v: int(v * (0.78 - 0.35 * min(1, h)))))
        C.put(fr, shi, W / 2 + (14 + 90 * h) * sc, cy + (26 + 150 * h) * sc)
        # удар: кольцо света и пыль по столу
        if D_ <= t < D_ + 1.2:
            q = (t - D_) / 1.2
            rr = D / 2 * sc * (1.02 + 0.9 * C.out_cubic(q))
            ring = Image.new('RGBA', (int(rr * 2 + 20), int(rr * 2 + 20)), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse((10, 10, 10 + rr * 2, 10 + rr * 2), outline=(255, 226, 170, 255), width=4)
            ring = ring.filter(ImageFilter.GaussianBlur(3))
            C.put(fr, ring, W / 2, cy, (1 - q) ** 2 * 0.55)
            for ang, rk, sp, sz, al in self.dust:
                d = D / 2 * sc * rk + sp * C.out_expo(q)
                C.put(fr, C.ellipse(int(sz * 2), int(sz * 2), (210, 196, 176)), W / 2 + d * math.cos(ang),
                      cy + d * math.sin(ang), al * (1 - q) ** 1.5)
        C.put(fr, coin, W / 2, cy)
        # тексты вступления
        qa = C.out_expo(C.seg(t, 0.15, 0.75)) * (1 - C.seg(t, D_ - 0.25, D_))
        if qa > 0:
            C.put(fr, self.hook, W / 2, 300 - 30 * (1 - qa), qa)
            C.put(fr, self.sub, W / 2, 300 + self.hook.height / 2 + 50, qa)
        # имя клуба на видимой стороне
        c = math.cos(th)
        na = (abs(c) ** 2) * C.out_expo(C.seg(t, 0.3, 0.9)) * (1 - C.seg(t, self.t_up - 0.1, self.t_up + 0.35))
        if self.t_toss + 0.4 * u < t < D_:
            na = 0.0
        if t >= D_:
            na *= C.out_back(C.seg(t, D_ + 0.05, D_ + 0.45))
        if na > 0:
            nm = self.names['h' if c >= 0 else 'a']
            C.put(fr, nm, W / 2, cy + D / 2 * sc + 120, na)
        # карточка прогноза
        if t >= self.t_card:
            q = C.out_expo(C.seg(t, self.t_card, self.t_card + 0.6))
            card = s3.pick_card(self.m, self.h, self.a, kef_q=C.out_back(C.seg(t, self.t_kef, self.t_kef + 0.35)))
            ccy = 1145
            C.put(fr, C.shadow(card, r=30, a=0.6), W / 2, ccy + 18 + 300 * (1 - q), q)
            C.put(fr, card, W / 2, ccy + 300 * (1 - q), q)
            C.put(fr, self.lab, W / 2, ccy - card.height / 2 - 62 + 40 * (1 - q), q)
        # камера: медленный наезд во вступлении, толчок и тряска на ударе
        z = 1.0 + 0.035 * C.seg(t, 0, D_)
        if t >= D_:
            z = 1.035 + 0.03 * math.exp(-(t - D_) * 5) - 0.035 * C.seg(t, D_, D_ + 1.5)
        dx, dy = C.shake(t, D_, amp=18, d=0.4)
        fr = C.zoom(fr.convert('RGB'), z, dx=dx, dy=dy)
        fr = C.grain(fr, t, 7)
        return s3.wipe_in(fr, s3.end_card(t, self.t_end), t, self.t_end)
