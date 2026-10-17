# -*- coding: utf-8 -*-
"""Серия 3 · «Тактическая доска» (трек Demons). Тёмная глянцевая доска тренера с напечатанной зоной атаки:
на доли щёлкают магниты-фишки с эмблемами (сначала обороняющиеся, потом атакующие — команда из прогноза),
белым маркером рисуются стрелки розыгрыша, бросок доходит до ворот ровно на дроп — и золотым маркером
обводится ключевая фишка, рядом от руки пометка из прогноза. Затем карточка прогноза с кэфом и заставка.
"""
import math
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import fresh as F
from reels import s3

W, H = C.W, C.H
BOARD = (22, 24, 28)
INK = (238, 240, 236)
LINE = (196, 200, 208)
RED = (196, 58, 62)
BLUE = (70, 116, 206)

# зона атаки: торцевой борт сверху, центральная линия внизу (1 фут ≈ 10,3 px)
X0, X1, Y0 = 100, 980, 420
FT = (X1 - X0) / 85.0
GY = Y0 + 11 * FT            # линия ворот
BY = Y0 + 75 * FT            # синяя
CY = Y0 + 100 * FT           # красная центральная


def _fy(ft):
    return Y0 + ft * FT


# ─────────────────────────── доска ───────────────────────────
def bez(ctrl, step=2.0, wob=1.2, seed=0):
    """Точки кривой Безье с шагом ~step px и лёгкой дрожью руки."""
    ctrl = np.array(ctrl, float)
    t = np.linspace(0, 1, 400)
    n = len(ctrl) - 1
    pts = sum(math.comb(n, k) * ((1 - t) ** (n - k) * t ** k)[:, None] * ctrl[k] for k in range(n + 1))
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    s = np.arange(0, d[-1], step)
    out = np.c_[np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])]
    if wob and len(out) > 2:
        rng = np.random.default_rng(seed)
        tang = np.gradient(out, axis=0)
        nrm = np.c_[-tang[:, 1], tang[:, 0]] / (np.hypot(*tang.T)[:, None] + 1e-6)
        ph = rng.uniform(0, 6.28, 2)
        u = np.linspace(0, 1, len(out))
        off = wob * (np.sin(u * 7 + ph[0]) + 0.5 * np.sin(u * 17 + ph[1])) * np.sin(u * math.pi)
        out = out + nrm * off[:, None]
    return out


class Stroke:
    """Линия маркера, которая «пишется» от начала к концу: render(q) → (RGBA, x, y)."""

    def __init__(self, pts, w=10, col=INK, seed=0):
        pts = np.asarray(pts, float)
        self.n = len(pts)
        x0, y0 = pts.min(0) - w - 4
        x1, y1 = pts.max(0) + w + 4
        self.x0, self.y0 = int(x0), int(y0)
        ww, hh = int(x1) - self.x0 + 1, int(y1) - self.y0 + 1
        p = pts - (self.x0, self.y0)
        # сглаженная маска (4×) и карта «порядка письма»
        ss = 4
        big = Image.new('L', (ww * ss, hh * ss), 0)
        d = ImageDraw.Draw(big)
        r = w * ss / 2
        for x, y in p * ss:
            d.ellipse((x - r, y - r, x + r, y + r), fill=255)
        al = np.array(big.resize((ww, hh), Image.LANCZOS), float) / 255
        order = np.full((hh, ww), np.inf)
        R = int(w / 2 + 2)
        yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
        disk = xx ** 2 + yy ** 2 <= R * R
        for i, (x, y) in enumerate(p):
            xi, yi = int(round(x)), int(round(y))
            sl = order[yi - R:yi + R + 1, xi - R:xi + R + 1]
            dk = disk[:sl.shape[0], :sl.shape[1]]
            m = dk & (sl > i)
            sl[m] = i
        rng = np.random.default_rng(seed)
        tex = np.array(Image.fromarray((rng.normal(0, 1, (hh, ww)) * 40 + 128).clip(0, 255).astype('uint8'))
                       .filter(ImageFilter.GaussianBlur(1.2)), float) / 255
        self.al = al * (0.84 + 0.3 * (tex - 0.5))
        self.order = order
        self.col = col

    def render(self, q):
        if q <= 0:
            return None
        lim = q * self.n
        a = np.where(self.order <= lim, self.al, 0) * 255
        arr = np.zeros(a.shape + (4,), np.uint8)
        arr[..., :3] = self.col
        arr[..., 3] = np.clip(a, 0, 255).astype(np.uint8)
        return Image.fromarray(arr, 'RGBA')


def arrow(ctrl, w=10, col=INK, seed=0, head=34, dashed=False):
    """Стрелка: тело + два штриха наконечника. → (strokes, pts)."""
    pts = bez(ctrl, seed=seed)
    if dashed:
        L = len(pts)
        keep = (np.arange(L) // 9) % 2 == 0
        pts_d = pts[keep]
    end = pts[-1]
    dv = pts[-1] - pts[-6]
    dv = dv / (np.hypot(*dv) + 1e-6)
    hs = []
    for sgn in (1, -1):
        a = math.radians(152 * sgn)
        rv = np.array([dv[0] * math.cos(a) - dv[1] * math.sin(a), dv[0] * math.sin(a) + dv[1] * math.cos(a)])
        hs.append(Stroke(bez([end, end + rv * head], wob=0), w, col, seed + 7))
    body = Stroke(pts_d if dashed else pts, w, col, seed)
    if dashed:
        # для пунктира «порядок письма» по исходной длине
        body.n = len(pts_d)
    return body, hs, pts


def _rink_layer():
    ss = 2
    im = Image.new('RGBA', (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S = lambda v: v * ss
    lw = 4
    # борт: скругления сверху, стороны уходят вниз за центральную линию
    rad = 28 * FT
    d.rounded_rectangle((S(X0), S(Y0), S(X1), S(H + 400)), radius=S(rad), outline=LINE + (255,), width=S(lw))
    # линия ворот (обрезана по закруглению)
    def bx(y):
        dy = max(0.0, (Y0 + rad) - y)
        return rad - math.sqrt(max(0.0, rad * rad - dy * dy))
    g = bx(GY)
    d.line((S(X0 + g), S(GY), S(X1 - g), S(GY)), fill=RED + (230,), width=S(3))
    # площадь ворот и ворота
    cr = 6 * FT
    d.pieslice((S(540 - cr), S(GY - cr), S(540 + cr), S(GY + cr)), 0, 180, fill=BLUE + (70,), outline=RED + (230,), width=S(3))
    d.rectangle((S(540 - 3 * FT), S(GY - 40), S(540 + 3 * FT), S(GY)), outline=RED + (230,), width=S(3))
    for k in range(1, 6):
        x = 540 - 3 * FT + k * 6 * FT / 6
        d.line((S(x), S(GY - 40), S(x), S(GY)), fill=LINE + (90,), width=S(1))
    # круги вбрасывания
    for sx in (-1, 1):
        cx, cy, r = 540 + sx * 22 * FT, _fy(31), 15 * FT
        d.ellipse((S(cx - r), S(cy - r), S(cx + r), S(cy + r)), outline=RED + (230,), width=S(3))
        d.ellipse((S(cx - 10), S(cy - 10), S(cx + 10), S(cy + 10)), fill=RED + (230,))
        for hy in (-1, 1):
            for hx in (-1, 1):
                x = cx + hx * 2 * FT
                y = cy + hy * r
                d.line((S(x), S(y), S(x), S(y + hy * 2 * FT)), fill=RED + (230,), width=S(3))
        for hx in (-1, 1):
            d.line((S(cx + hx * 0.6 * FT), S(cy - 1.5 * FT), S(cx + hx * 0.6 * FT), S(cy + 1.5 * FT)), fill=RED + (150,), width=S(2))
    # синяя линия, точки средней зоны, центральная
    d.line((S(X0), S(BY), S(X1), S(BY)), fill=BLUE + (240,), width=S(12))
    for sx in (-1, 1):
        cx, cy = 540 + sx * 22 * FT, _fy(80)
        d.ellipse((S(cx - 10), S(cy - 10), S(cx + 10), S(cy + 10)), fill=RED + (230,))
    d.line((S(X0), S(CY), S(X1), S(CY)), fill=RED + (240,), width=S(12))
    d.ellipse((S(540 - 15 * FT), S(CY - 15 * FT), S(540 + 15 * FT), S(CY + 15 * FT)), outline=BLUE + (230,), width=S(3))
    im = im.resize((W, H), Image.LANCZOS)
    # печать чуть мягче и тусклее маркера
    a = np.array(im.getchannel('A'), float) * 0.78
    im.putalpha(Image.fromarray(a.astype('uint8')))
    return im.filter(ImageFilter.GaussianBlur(0.4))


def board_bg(seed=9):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (H // 6, W // 6))
    big = np.array(Image.fromarray((n * 30 + 128).clip(0, 255).astype('uint8')).resize((W, H), Image.BICUBIC)
                   .filter(ImageFilter.GaussianBlur(20)), float) - 128
    fine = rng.normal(0, 1, (H, W)) * 3
    arr = np.array(BOARD, float)[None, None, :] + (big * 0.12 + fine)[..., None]
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    light = np.exp(-(((xx - W * 0.5) / (W * 0.8)) ** 2 + ((yy - H * 0.2) / (H * 0.55)) ** 2)) * 26
    sheen = np.clip(1 - np.abs((xx * 0.8 - yy * 0.6 + 260) / 260), 0, 1) ** 2 * 10
    arr += (light + sheen)[..., None]
    img = Image.fromarray(np.clip(arr, 0, 255).astype('uint8'), 'RGB').convert('RGBA')
    # следы стёртого маркера
    ghost = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(ghost)
    for k in range(14):
        p = bez([(rng.uniform(80, 1000), rng.uniform(300, 1450)) for _ in range(3)], step=3, wob=0)
        gd.line([tuple(q) for q in p], fill=(255, 255, 255, int(rng.uniform(8, 18))), width=int(rng.uniform(8, 22)), joint='curve')
    img.alpha_composite(ghost.filter(ImageFilter.GaussianBlur(4)))
    img.alpha_composite(_rink_layer())
    # алюминиевая рама
    fr = np.zeros((H, 24, 4), np.uint8)
    g = np.linspace(0, 1, 24)
    col = (150 + 70 * np.sin(g * math.pi) ** 0.6 - 40 * g).astype(np.uint8)
    fr[..., 0] = col[None, :]
    fr[..., 1] = (col * 1.01).clip(0, 255).astype(np.uint8)[None, :]
    fr[..., 2] = (col * 1.04).clip(0, 255).astype(np.uint8)[None, :]
    fr[..., 3] = 255
    bar = Image.fromarray(fr, 'RGBA')
    img.alpha_composite(bar, (0, 0))
    img.alpha_composite(bar.transpose(Image.FLIP_LEFT_RIGHT), (W - 24, 0))
    edge = Image.new('RGBA', (8, H), (0, 0, 0, 90)).filter(ImageFilter.GaussianBlur(3))
    img.alpha_composite(edge, (24, 0))
    img.alpha_composite(edge, (W - 32, 0))
    return C.vignette(img, 0.4, 2.4).convert('RGBA')


def magnet(t, d=100):
    """Магнитная фишка: ободок цвета клуба, белое поле с эмблемой, глянец."""
    ss = 3
    D = d * ss
    yy, xx = np.mgrid[0:D, 0:D].astype(float) + 0.5
    r = np.hypot(xx - D / 2, yy - D / 2) / (D / 2)
    phi = np.arctan2(yy - D / 2, xx - D / 2)
    lam = np.cos(phi + math.radians(125))
    c = np.array(F.club(t), float)
    rim = c * (0.75 + 0.25 * lam[..., None]) * (1 - 0.25 * np.clip((r - 0.9) / 0.1, 0, 1))[..., None]
    face = np.array((244, 243, 238.)) * (0.94 + 0.06 * np.clip(1 - r / 0.76, 0, 1))[..., None]
    col = np.where((r < 0.76)[..., None], face, rim)
    ring = (np.abs(r - 0.76) < 0.025)
    col[ring] = col[ring] * 0.6
    a = np.clip((1 - r) * D / 2 + 0.5, 0, 1) * 255
    im = Image.fromarray(np.dstack([np.clip(col, 0, 255), a]).astype('uint8'), 'RGBA').resize((d, d), Image.LANCZOS)
    es = int(d * 0.52)
    C.put(im, C.fit(t.emb(es * 2), es, es), d / 2, d / 2)
    gl = C.radial(int(d * 0.8), int(d * 0.5), (255, 255, 255), 70, power=1.8)
    C.put(im, gl.rotate(30, expand=True), d * 0.38, d * 0.3)
    m = im.getchannel('A')
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    lay.alpha_composite(im)
    lay.putalpha(m)
    return lay


def _note(m, side, h, a):
    p = m['pick']
    num = re.search(r'([+−-]\s?\d+[,.]?\d*)', p)
    if 'фора' in p.lower() and num:
        return num.group(1).replace(' ', '').replace('-', '−')
    tot = re.search(r'тотал.*?(больше|меньше)\s*(\d+[,.]?\d*)', p.lower())
    if tot:
        return ('ТБ ' if tot.group(1) == 'больше' else 'ТМ ') + tot.group(2)
    return (h if side == 'h' else a).short


class Board(C.Reel):
    def __init__(self, m, u, drop, seed=21):
        super().__init__(u, drop, seed)
        self.m = m
        self.h, self.a = C.match(m['home'], m['away'], m['league'])
        side = s3.pick_side(m, self.h, self.a) or 'a'
        att, dfn = (self.h, self.a) if side == 'h' else (self.a, self.h)
        self.bg = board_bg()
        md = 104
        self.mg = {'att': magnet(att, md), 'dfn': magnet(dfn, md)}
        self.sh = {k: C.shadow(v, r=6, a=0.75) for k, v in self.mg.items()}
        self.shl = {k: C.shadow(v, r=14, a=0.5) for k, v in self.mg.items()}
        b = self.b
        # расстановка: обороняющиеся (у ворот сверху), атакующие (команда прогноза)
        self.place = [
            ('dfn', 540, GY + 52, b(-6)), ('dfn', 405, _fy(24), b(-6) + 0.09), ('dfn', 655, _fy(21), b(-6) + 0.18),
            ('dfn', 330, _fy(56), b(-5)), ('dfn', 760, _fy(58), b(-5) + 0.12),
            ('att', 380, _fy(72), b(-4)), ('att', 720, _fy(73), b(-4) + 0.12),
            ('att', 235, _fy(36), b(-3)), ('att', 840, _fy(40), b(-3) + 0.1), ('att', 560, _fy(42), b(-3) + 0.2),
        ]
        slot = np.array((560, _fy(42)))
        self.slot = slot
        # стрелки розыгрыша (белый маркер)
        A = []
        A.append((arrow([(840 - 58, _fy(40) + 4), (760, _fy(35)), (680, _fy(36)), (560 + 62, _fy(41))], seed=1, dashed=True),
                  b(-2), b(-1.3)))                                                  # передача с борта на пятак
        A.append((arrow([(720, _fy(73) - 56), (840, _fy(64)), (880, _fy(52)), (858, _fy(46))], seed=2), b(-1.5), b(-0.8)))   # подключение защитника
        A.append((arrow([(slot[0], slot[1] - 58), (548, _fy(32)), (544, _fy(22)), (540, GY + 12)], seed=3, head=40), b(-0.75), b(0)))  # бросок
        self.arrows = A
        # золотое кольцо вокруг ключевой фишки — на дропе
        th = np.linspace(-2.2, -2.2 + 2 * math.pi + 0.5, 360)
        rr = 98 * (1 + 0.045 * np.sin(3 * th + 1)) * np.linspace(1.0, 1.1, len(th))
        ring = np.c_[slot[0] + rr * np.cos(th) * 1.08, slot[1] + rr * np.sin(th)]
        self.ring = Stroke(ring, 11, s3.GOLD, 5)
        self.note = C.text(_note(m, side, self.h, self.a), 'hand', 104, s3.GOLD, 700)
        self.note_xy = (slot[0] + 255, slot[1] - 255)
        self.note_ul = Stroke(bez([(self.note_xy[0] - self.note.width / 2, self.note_xy[1] + 62),
                                   (self.note_xy[0] + self.note.width / 2 + 10, self.note_xy[1] + 56)], seed=8), 7, s3.GOLD, 8)
        # шапка: печатная магнитная плашка с матчем
        tt = C.text('%s — %s' % (self.h.up, self.a.up), 'unb', 46, (16, 17, 20), 800, max_w=820)
        self.strip = C.rrect(tt.width + 90, 104, 16, (238, 238, 233))
        C.put(self.strip, tt, self.strip.width / 2, 52)
        self.strip_sh = C.shadow(self.strip, r=10, a=0.7)
        self.sub = C.text(s3.sub_line(m), 'mont', 28, (176, 180, 190), 700, track=0.14)
        self.t_card = b(2)
        self.t_kef = b(3.5)
        self.t_end = b(11)
        self.dur = self.t_end + 2.8
        self.cover_t = b(5)

    def frame(self, t):
        D_ = self.drop
        fr = self.bg.copy()
        # шапка
        q = C.seg(t, 0.12, 0.42)
        if q > 0:
            s = 1 + 0.12 * (1 - C.out_cubic(q))
            C.put(fr, self.strip_sh, W / 2 + 4, 250 + 12 * s, min(1, q * 2))
            C.put(fr, C.scale(self.strip, s), W / 2, 250, min(1, q * 2))
            C.put(fr, self.sub, W / 2, 340, C.out_expo(C.seg(t, 0.4, 0.9)))
        # фишки
        for k, x, y, t0 in self.place:
            q = C.seg(t, t0, t0 + 0.14)
            if q <= 0:
                continue
            e = C.in_cubic(q)
            s = 1.3 - 0.3 * e
            shk = self.sh[k] if e >= 1 else self.shl[k]
            C.put(fr, shk, x + 3 + 10 * (1 - e), y + 7 + 22 * (1 - e), min(1, q * 1.5))
            C.put(fr, C.scale(self.mg[k], s), x, y, min(1, q * 2))
        # стрелки
        for (body, heads, pts), t0, t1 in self.arrows:
            q = C.seg(t, t0, t1)
            if q <= 0:
                continue
            im = body.render(C.out_cubic(min(1, q / 0.85)))
            if im is not None:
                fr.alpha_composite(im, (body.x0, body.y0))
            qh = C.seg(q, 0.85, 1.0)
            for hs in heads:
                im = hs.render(qh)
                if im is not None:
                    fr.alpha_composite(im, (hs.x0, hs.y0))
        # кольцо и пометка от руки
        q = C.seg(t, D_, D_ + 0.32)
        if q > 0:
            im = self.ring.render(C.out_cubic(q))
            fr.alpha_composite(im, (self.ring.x0, self.ring.y0))
        q = C.seg(t, D_ + 0.35, D_ + 0.75)
        if q > 0:
            ww = max(1, int(self.note.width * C.out_cubic(q)))
            C.put(fr, self.note.crop((0, 0, ww, self.note.height)), self.note_xy[0] - self.note.width / 2,
                  self.note_xy[1] - self.note.height / 2, anchor='tl')
            im = self.note_ul.render(C.seg(t, D_ + 0.7, D_ + 0.9))
            if im is not None:
                fr.alpha_composite(im, (self.note_ul.x0, self.note_ul.y0))
        # карточка прогноза: доска слегка притухает
        if t >= self.t_card:
            q = C.out_expo(C.seg(t, self.t_card, self.t_card + 0.6))
            dim = Image.new('RGBA', (W, H), (8, 9, 11, int(110 * q)))
            fr.alpha_composite(dim)
            card = s3.pick_card(self.m, self.h, self.a, kef_q=C.out_back(C.seg(t, self.t_kef, self.t_kef + 0.35)), dark=False)
            ccy = 1150
            C.put(fr, C.shadow(card, r=30, a=0.7), W / 2, ccy + 20 + 320 * (1 - q), q)
            C.put(fr, card, W / 2, ccy + 320 * (1 - q), q)
        # камера: медленный наезд к пятаку, толчок на дропе, отъезд к карточке
        cx, cy = W / 2, 760
        z = 1.0 + 0.06 * C.in_out(C.seg(t, 0.4, D_))
        if t >= D_:
            z = 1.06 + 0.035 * math.exp(-(t - D_) * 6) - 0.06 * C.in_out(C.seg(t, self.t_card - 0.2, self.t_card + 0.6))
        dx, dy = C.shake(t, D_, amp=10, d=0.35)
        for k, x, y, t0 in self.place:
            if t0 <= t < t0 + 0.2:
                ddx, ddy = C.shake(t, t0 + 0.14, amp=3, d=0.12)
                dx, dy = dx + ddx, dy + ddy
        fr = C.zoom(fr.convert('RGB'), z, cx=cx, cy=cy, dx=dx, dy=dy)
        fr = C.grain(fr, t, 5)
        return s3.wipe_in(fr, s3.end_card(t, self.t_end), t, self.t_end)
