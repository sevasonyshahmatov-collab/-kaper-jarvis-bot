# -*- coding: utf-8 -*-
"""Серия 3 · «Кейс» (трек Militant). Вид сверху: алюминиевый кейс на тёмном столе. На доли прокручиваются колёсики
кодового замка (набирается кэф), щёлкают защёлки, крышка приоткрывается полоской тёплого света — и на дропе
распахивается: в чёрном поролоне две монеты с эмблемами и карточка прогноза. Карточка поднимается к камере, кэф, заставка.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import s3
from reels import s3_coin

W, H = C.W, C.H
CW, CH = 960, 660                    # кейс
X0, Y0 = (W - CW) // 2, 640          # левый верх корпуса (петли сверху)
INS = 34                             # толщина борта


def _brushed(w, h, seed, base=(172, 176, 183)):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (h, w // 8 + 2))
    n = np.array(Image.fromarray(((n * 30) + 128).clip(0, 255).astype('uint8')).resize((w, h), Image.BILINEAR), float) - 128
    rows = rng.normal(0, 1, (h, 1)) * 6
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    light = 1.06 - 0.22 * (xx / w * 0.6 + yy / h * 0.4)
    sheen = np.exp(-((xx / w - yy / h * 0.5 - 0.25) / 0.12) ** 2) * 0.12
    arr = (np.array(base, float)[None, None, :] + (n * 0.12 + rows)[..., None]) * (light + sheen)[..., None]
    return np.clip(arr, 0, 255)


def _rmask(w, h, r):
    m = Image.new('L', (w * 3, h * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 3 - 1, h * 3 - 1), radius=r * 3, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def lid_outer(seed=4):
    arr = _brushed(CW, CH, seed, (150, 154, 162))
    yy, xx = np.mgrid[0:CH, 0:CW].astype(float)
    # рёбра жёсткости: две выпуклые полосы поперёк крышки
    for yc in (CH * 0.33, CH * 0.67):
        d = (yy - yc) / 9
        prof = np.exp(-d ** 2)
        arr += (np.clip(-np.gradient(prof, axis=0) * 300, -55, 75))[..., None]
    # кант по периметру: скос со светом сверху слева
    e = np.minimum.reduce([xx, yy, CW - 1 - xx, CH - 1 - yy])
    bev = np.clip(1 - e / 26, 0, 1)
    tl = ((xx < yy * CW / CH) & (xx + yy < CW))
    arr = arr * (1 - 0.18 * bev)[..., None] + (np.where(e < 26, np.where((xx < 26) | (yy < 26), 34, -30), 0) * bev)[..., None]
    img = Image.fromarray(np.clip(arr, 0, 255).astype('uint8'), 'RGB').convert('RGBA')
    d = ImageDraw.Draw(img)
    # угловые накладки
    for cx, cy in ((0, 0), (CW, 0), (0, CH), (CW, CH)):
        d.ellipse((cx - 58, cy - 58, cx + 58, cy + 58), fill=(70, 72, 78, 255))
        d.ellipse((cx - 50, cy - 50, cx + 50, cy + 50), fill=(96, 99, 106, 255))
    # именная пластина
    pl = C.rrect(300, 64, 10, (44, 46, 52))
    C.put(pl, C.rrect(292, 56, 8, None, outline=(120, 124, 132), width=2), 150, 32)
    C.put(pl, C.text('JARVIBET', 'unb', 26, (190, 194, 202), 700, track=0.3), 150, 33)
    C.put(img, C.shadow(pl, r=4, a=0.6), CW / 2 + 2, CH * 0.5 + 4)
    C.put(img, pl, CW / 2, CH * 0.5)
    img.putalpha(_rmask(CW, CH, 40))
    return img


def lid_inner(seed=5):
    """Изнанка крышки: «яичная» пена."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:CH, 0:CW].astype(float)
    egg = (np.sin(xx / 22) * np.sin(yy / 22)) * 7
    arr = np.array((24, 25, 28.))[None, None, :] + (egg + rng.normal(0, 3, (CH, CW)))[..., None]
    img = Image.fromarray(np.clip(arr, 0, 255).astype('uint8'), 'RGB').convert('RGBA')
    rim = Image.fromarray(_brushed(CW, CH, seed + 1, (150, 154, 160)).astype('uint8'), 'RGB').convert('RGBA')
    m = Image.new('L', (CW, CH), 255)
    ImageDraw.Draw(m).rounded_rectangle((INS, INS, CW - INS, CH - INS), radius=20, fill=0)
    rim.putalpha(m)
    img.alpha_composite(rim)
    img.putalpha(_rmask(CW, CH, 40))
    return img


class Case(C.Reel):
    def __init__(self, m, u, drop, seed=44):
        super().__init__(u, drop, seed)
        self.m = m
        self.h, self.a = C.match(m['home'], m['away'], m['league'])
        b = self.b
        self.lo = lid_outer()
        self.li = lid_inner()
        self.table = self._table()
        self.body = self._body()
        # колёсики замка: цифры кэфа (без запятой), каждое встаёт на свою долю
        self.code = [c for c in s3.kef_s(m['kef']) if c.isdigit()][:3]
        self.t_wheels = [b(-8) + k * u for k in range(len(self.code))]
        self.t_latch = [b(-3), b(-2)]
        self.t_crack = b(-1)
        self.t_lift = b(2)
        self.t_kef = b(4)
        self.t_end = b(14)
        self.dur = self.t_end + 2.8
        self.cover_t = b(6)
        self.hook = s3.hook('%s — %s' % (self.h.up, self.a.up), 64)
        self.sub = C.text(s3.sub_line(m), 'mont', 30, s3.GOLD, 700, track=0.14)
        self.warm = C.radial(1100, 800, (255, 196, 120), 200, 1.5)

    def _table(self):
        rng = np.random.default_rng(8)
        n = rng.normal(0, 1, (H // 4, W // 4))
        wood = np.array(Image.fromarray((n * 40 + 128).clip(0, 255).astype('uint8')).resize((W, H), Image.BICUBIC)
                        .filter(ImageFilter.BoxBlur(1)), float)
        yy, xx = np.mgrid[0:H, 0:W].astype(float)
        grain = np.sin(xx / 7 + np.sin(yy / 90) * 3 + wood / 40) * 4
        arr = np.array((26, 20, 16.))[None, None, :] + (grain + (wood - 128) * 0.05)[..., None]
        light = np.exp(-(((xx - 540) / 700) ** 2 + ((yy - 1000) / 900) ** 2)) * 34
        arr = arr + light[..., None] * np.array((1.0, 0.85, 0.7))[None, None, :]
        img = Image.fromarray(np.clip(arr, 0, 255).astype('uint8'), 'RGB')
        return C.vignette(img, 0.55, 2.0).convert('RGBA')

    def _body(self):
        """Открытый корпус: алюминиевый борт, чёрный поролон, две монеты, гнездо карточки."""
        img = Image.fromarray(_brushed(CW, CH, 11, (150, 154, 160)).astype('uint8'), 'RGB').convert('RGBA')
        rng = np.random.default_rng(12)
        iw, ih = CW - 2 * INS, CH - 2 * INS
        foam = np.array((20, 21, 24.))[None, None, :] + rng.normal(0, 4, (ih, iw))[..., None]
        yy, xx = np.mgrid[0:ih, 0:iw].astype(float)
        foam = foam * (0.85 + 0.25 * np.exp(-(((xx - iw / 2) / iw) ** 2 + ((yy - ih / 2) / ih) ** 2) * 2))[..., None]
        fimg = Image.fromarray(np.clip(foam, 0, 255).astype('uint8'), 'RGB').convert('RGBA')
        fd = ImageDraw.Draw(fimg)
        self.slots = {}
        dcoin = 230
        for k, (tm, cx) in enumerate(((self.h, iw * 0.27), (self.a, iw * 0.73))):
            cy = 160
            fd.ellipse((cx - dcoin / 2 - 6, cy - dcoin / 2 - 6, cx + dcoin / 2 + 6, cy + dcoin / 2 + 6), fill=(6, 6, 8, 255))
            face = s3_coin.coin_face(tm, '%s  •  %s  •  ' % (tm.up, s3.lg_ru(self.m))).resize((dcoin, dcoin), Image.LANCZOS)
            fimg.alpha_composite(face, (int(cx - dcoin / 2), int(cy - dcoin / 2)))
        card = s3.pick_card(self.m, self.h, self.a, kef_q=0)
        sc = min(0.56, (ih - 330) / card.height)
        cw, chh = int(card.width * sc), int(card.height * sc)
        sx, sy = iw / 2, 330 + (ih - 330) / 2 - 6
        fd.rounded_rectangle((sx - cw / 2 - 8, sy - chh / 2 - 8, sx + cw / 2 + 8, sy + chh / 2 + 8), radius=26, fill=(6, 6, 8, 255))
        self.card_home = (X0 + INS + sx, Y0 + INS + sy, sc)
        self.slot_rect = (sx - cw / 2 - 8, sy - chh / 2 - 8, sx + cw / 2 + 8, sy + chh / 2 + 8)
        fm = _rmask(iw, ih, 20)
        fimg.putalpha(fm)
        sh = Image.new('RGBA', (iw, ih), (0, 0, 0, 0))
        sm = Image.new('L', (iw, ih), 0)
        ImageDraw.Draw(sm).rectangle((0, 0, iw, 22), fill=150)
        sm = sm.filter(ImageFilter.GaussianBlur(10))
        sh.putalpha(sm)
        fimg.alpha_composite(sh)
        img.alpha_composite(fimg, (INS, INS))
        img.putalpha(_rmask(CW, CH, 40))
        return img

    def _wheels(self, t):
        """Окошко кодового замка с тремя колёсиками."""
        n = len(self.code)
        ww, wh = 46, 64
        win = Image.new('RGBA', (n * ww + (n - 1) * 8 + 24, wh + 20), (40, 42, 46, 255))
        for k, dg in enumerate(self.code):
            t0 = self.t_wheels[k]
            target = int(dg)
            if t < t0 - 0.9:
                pos = 0.0
            elif t < t0:
                q = C.seg(t, t0 - 0.9, t0)
                pos = (10 + target) * C.out_cubic(q)
            else:
                pos = 10 + target - 0.08 * math.exp(-(t - t0) * 12) * math.sin((t - t0) * 50)
            col = Image.new('RGBA', (ww, wh), (0, 0, 0, 0))
            for j in (-1, 0, 1):
                v = int(math.floor(pos) + j) % 10
                off = (j - (pos - math.floor(pos))) * wh * 0.62
                tx = C.text(str(v), 'mono', 42, (30, 30, 32), 800)
                C.put(col, tx, ww / 2, wh / 2 + off)
            cyl = np.linspace(-1, 1, wh)
            shade = (0.45 + 0.55 * np.sqrt(np.clip(1 - cyl ** 2, 0, 1)))
            bg = (np.array((226, 222, 210.))[None, None, :] * shade[:, None, None]) * np.ones((wh, ww, 1))
            base = Image.fromarray(bg.astype('uint8'), 'RGB').convert('RGBA')
            base.alpha_composite(col)
            arr = np.asarray(base, np.float32)
            arr[..., :3] *= shade[:, None, None] ** 0.5
            base = Image.fromarray(arr.astype('uint8'), 'RGBA')
            win.alpha_composite(base, (12 + k * (ww + 8), 10))
        return win

    def _latch(self, t, k):
        t0 = self.t_latch[k]
        q = C.seg(t, t0, t0 + 0.12)
        img = Image.new('RGBA', (150, 120), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((15, 20, 135, 100), radius=10, fill=(58, 60, 66, 255))
        # пластина: при открытии откидывается вниз (к камере) — короче и темнее
        if q <= 0:
            plate = C.lgrad(104, 66, (236, 238, 242), (150, 154, 162), angle=90)
            C.put(img, C.rrect(104, 66, 8, None, outline=(80, 82, 88), width=2), 75, 60)
            img.alpha_composite(Image.composite(plate, Image.new('RGBA', plate.size), _rmask(104, 66, 8)), (23, 27))
            d.rectangle((60, 46, 90, 74), fill=(120, 124, 132, 255))
        else:
            e = C.out_back(q, 2.2)
            hgt = int(66 * (1 - 0.5 * e))
            plate = C.lgrad(104, max(4, hgt), (130, 134, 140), (210, 214, 220), angle=90)
            img.alpha_composite(Image.composite(plate, Image.new('RGBA', plate.size), _rmask(104, max(4, hgt), 8)), (23, 27 + 66 - hgt + int(10 * e)))
            d.rectangle((50, 30, 100, 40), fill=(16, 16, 18, 255))
        return img

    def lid_angle(self, t):
        D_ = self.drop
        if t < self.t_crack:
            return 0.0
        if t < D_ - 0.05:
            q = C.seg(t, self.t_crack, self.t_crack + 0.2)
            return math.radians(9) * C.out_back(q, 2.0)
        q = C.seg(t, D_ - 0.05, D_ + 0.38)
        a = math.radians(9) + (math.radians(122) - math.radians(9)) * C.out_cubic(q)
        if q >= 1:
            a += math.radians(4) * math.exp(-(t - D_ - 0.33) * 8) * math.sin((t - D_ - 0.33) * 30)
        return a

    def frame(self, t):
        D_ = self.drop
        fr = self.table.copy()
        th = self.lid_angle(t)
        c = math.cos(th)
        glow = 0.0
        if th > 0:
            glow = C.clamp((1 - c) * 2.2) * (0.6 if t < D_ else 1.0)
            if D_ <= t < D_ + 0.6:
                glow += 0.9 * math.exp(-(t - D_) * 6)
        # тень кейса
        sh = C.shadow(Image.new('RGBA', (CW, CH), (0, 0, 0, 255)), r=26, a=0.75)
        C.put(fr, sh, X0 + CW / 2 + 16, Y0 + CH / 2 + 30)
        # корпус (внутренность видна, когда крышка поднята)
        if th > 0:
            body = self.body.copy()
            if t >= self.t_lift:
                q = C.seg(t, self.t_lift, self.t_lift + 0.6)
                d = ImageDraw.Draw(body)
                x0, y0, x1, y1 = self.slot_rect
                d.rounded_rectangle((INS + x0, INS + y0, INS + x1, INS + y1), radius=26, fill=(6, 6, 8, 255))
            fr.alpha_composite(body, (X0, Y0))
            if t < self.t_lift:
                card = s3.pick_card(self.m, self.h, self.a, kef_q=0)
                hx, hy, sc = self.card_home
                C.put(fr, C.scale(card, sc), hx, hy)
        # свет изнутри
        if glow > 0:
            fr = C.add_light(fr, self.warm, X0 + CW / 2, Y0 + CH * 0.6, glow * 0.45)
        # крышка
        if c > 0:
            hgt = max(2, int(CH * c))
            sx = 1 + 0.08 * math.sin(th)
            lid = self.lo.resize((int(CW * sx), hgt), Image.LANCZOS)
            # детали на крышке: замок, защёлки, ручка
            if c > 0.98:
                lid2 = self.lo.copy()
                wh = self._wheels(t)
                C.put(lid2, wh, CW / 2, CH - 70)
                for k, xx in enumerate((CW * 0.2, CW * 0.8)):
                    C.put(lid2, C.scale(self._latch(t, k), 1.45), xx, CH - 72)
                lid = lid2.resize((int(CW * sx), hgt), Image.LANCZOS) if hgt != CH or sx != 1 else lid2
            C.put(fr, C.shadow(lid, r=12, a=0.5), X0 + CW / 2 + 6, Y0 + hgt / 2 + 12)
            fr.alpha_composite(lid, (int(X0 + CW / 2 - lid.width / 2), Y0))
            if 0 < th and t < D_:
                # полоска света в щели
                strip = C.radial(CW, 60, (255, 210, 140), 255, 1.2)
                fr = C.add_light(fr, strip, X0 + CW / 2, Y0 + hgt + 8, 0.6 * C.seg(t, self.t_crack, self.t_crack + 0.2))
        else:
            hgt = max(2, int(CH * -c))
            sx = 1 + 0.08 * math.sin(th)
            lid = self.li.transpose(Image.FLIP_TOP_BOTTOM).resize((int(CW * sx), hgt), Image.LANCZOS)
            fr.alpha_composite(lid, (int(X0 + CW / 2 - lid.width / 2), Y0 - hgt))
        # ручка у переднего края (на корпусе, видна всегда)
        hd = C.rrect(300, 54, 27, (34, 35, 38))
        C.put(fr, C.shadow(hd, r=8, a=0.6), X0 + CW / 2 + 4, Y0 + CH + 30)
        C.put(fr, hd, X0 + CW / 2, Y0 + CH + 24)
        # шапка
        qa = C.out_expo(C.seg(t, 0.15, 0.7)) * (1 - C.seg(t, D_ - 0.2, D_ + 0.1))
        if qa > 0:
            C.put(fr, self.hook, W / 2, 300 - 24 * (1 - qa), qa)
            C.put(fr, self.sub, W / 2, 300 + self.hook.height / 2 + 46, qa)
        # карточка поднимается к камере
        if t >= self.t_lift:
            q = C.in_out(C.seg(t, self.t_lift, self.t_lift + 0.7))
            hx, hy, sc0 = self.card_home
            dim = Image.new('RGBA', (W, H), (0, 0, 0, int(165 * q)))
            fr.alpha_composite(dim)
            card = s3.pick_card(self.m, self.h, self.a, kef_q=C.out_back(C.seg(t, self.t_kef, self.t_kef + 0.35)))
            s = C.lerp(sc0, 1.0, q) * (1 + 0.06 * math.sin(q * math.pi))
            x, y = C.lerp(hx, W / 2, q), C.lerp(hy, 1040, q)
            C.put(fr, C.shadow(C.scale(card, s), r=int(10 + 30 * q), a=0.75), x + 10 * q, y + 10 + 40 * q)
            C.put(fr, C.scale(card, s), x, y)
        # камера
        z = 1.0 + 0.05 * C.in_out(C.seg(t, 0, D_))
        if t >= D_:
            z = 1.05 + 0.03 * math.exp(-(t - D_) * 6) - 0.05 * C.in_out(C.seg(t, self.t_lift, self.t_lift + 0.7))
        dx, dy = C.shake(t, D_, amp=14, d=0.35)
        for t0 in self.t_latch + self.t_wheels:
            ex, ey = C.shake(t, t0, amp=4, d=0.12)
            dx, dy = dx + ex, dy + ey
        fr = C.zoom(fr.convert('RGB'), z, cx=540, cy=820, dx=dx, dy=dy)
        fr = C.grain(fr, t, 6)
        return s3.wipe_in(fr, s3.end_card(t, self.t_end), t, self.t_end)
