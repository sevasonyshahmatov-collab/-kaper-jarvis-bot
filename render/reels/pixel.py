# -*- coding: utf-8 -*-
"""«8-бит» — прогноз как ретро-игра про хоккей (NES/Sega).

Всё рисуется в низком разрешении 216×384 и увеличивается ×5 без сглаживания (чёткие пиксели), шрифт
Press Start 2P, поверх — строки кинескопа. До дропа — титульный экран «JARVIS HOCKEY», мигает «НАЖМИ СТАРТ»;
на дропе — выбор команд (пиксельные эмбемы, 1P / 2P, VS); дальше — матч: пиксельные игроки в цветах клубов
катаются, пас, бросок, «ГОЛ!» у фаворита; потом — окно диалога как в RPG: прогноз печатается по буквам;
в конце — «ПРОДОЛЖИТЬ? 9…8…» и «ПОДПИШИСЬ · TELEGRAM @JARVIBET».
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import nhl
from reels import core as C
from reels.core import W, H

S = 5
LW, LH = W // S, H // S          # 216 × 384
BLACK, WHITE = (0, 0, 0), (252, 252, 252)
NAVY = (16, 20, 72)
SKY = (60, 188, 252)
YEL = (252, 216, 60)
RED = (228, 40, 72)
GRAY = (188, 188, 188)
ICE = (236, 244, 252)

SPRITE = [            # игрок сбоку: H — шлем, F — лицо, J — свитер, P — шорты, L — ноги, K — коньки, S — клюшка
    '...HHHH.....',
    '..HHHHHH....',
    '..HFFFF.....',
    '...FFFF.....',
    '.JJJJJJJ....',
    'JJJJJJJJJ...',
    'JJJJJJJJJ...',
    '.JJJJJJJF...',
    '..PPPPPP.S..',
    '..PPPPPP..S.',
    '..LL..LL..S.',
    '.LL....LL.S.',
    'KKK...KKK.SS',
]
SPRITE2 = SPRITE[:10] + ['...LLLL...S.', '...LL.LL..S.', '..KKK.KKK.SS']


def font(size):
    return C.font('pixel', size, 400)


def ptext(s, size=8, col=WHITE, shadow=BLACK):
    """Пиксельный текст без сглаживания (+ тень на 1 пиксель)."""
    f = font(size)
    w = int(f.getlength(s)) + 2
    im = Image.new('RGBA', (w, size + 3), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.fontmode = '1'
    if shadow:
        d.text((1, 1), s, font=f, fill=shadow + (255,))
    d.text((0, 0), s, font=f, fill=col + (255,))
    return im


def sprite(rows, jersey, helmet, flip=False):
    pal = {'H': helmet, 'F': (252, 196, 160), 'J': jersey, 'P': (30, 30, 40), 'L': (30, 30, 40), 'K': (200, 200, 210),
           'S': (150, 100, 50)}
    im = Image.new('RGBA', (len(rows[0]), len(rows)), (0, 0, 0, 0))
    px = im.load()
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in pal:
                px[x, y] = pal[ch] + (255,)
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im


def pix_emblem(team, size):
    e = team.emb(size * 4)
    sm = e.resize((size, size), Image.LANCZOS) if e.width == e.height else C.fit(e, size, size)
    a = np.asarray(sm.getchannel('A'))
    rgb = sm.convert('RGB').quantize(12, dither=Image.Dither.NONE).convert('RGB')
    out = rgb.convert('RGBA')
    out.putalpha(Image.fromarray(np.where(a > 110, 255, 0).astype(np.uint8)))
    return out


def abbr(team):
    v = nhl.TEAMS.get(team.name)
    return v[3] if v else team.up[:3]


class Pixel(C.Reel):
    def __init__(self, home, away, league, side, pick, coef, when, u=120 / 142, drop=3.38, seed=4):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.side = side
        self.fav = self.h if side == 'h' else self.a
        self.pick, self.coef, self.when = pick, coef, when
        self.league = 'NHL' if str(league).upper() == 'NHL' else 'KHL'
        self.dur = self.b(12.4)
        self.cover_t = self.b(9.3)
        rnd = np.random.default_rng(seed)
        self.stars = [(rnd.uniform(0, LW), rnd.uniform(0, LH), int(rnd.choice([1, 1, 2])), rnd.uniform(8, 40)) for _ in range(70)]
        self.pe = {k: pix_emblem(t, 44) for k, t in (('h', self.h), ('a', self.a))}
        self.spr = {}
        for k, t in (('h', self.h), ('a', self.a)):
            c2 = t.c2 if sum(t.c2) > 120 else WHITE
            self.spr[k] = [sprite(SPRITE, t.c1, c2, k == 'a'), sprite(SPRITE2, t.c1, c2, k == 'a')]
        self.rink = self._rink()
        scan = np.zeros((H, W, 4), np.uint8)
        for y in range(0, H, S):
            scan[y + S - 1, :, 3] = 70
        self.scan = Image.fromarray(scan, 'RGBA')
        gl = 'JARVIS: ' + self.pick.upper() + '! КЭФ ' + C.fmt_k(self.coef)
        self.dialog_text = gl

    def _rink(self):
        """Половина площадки (атака вправо): центральная линия слева, ворота справа."""
        im = Image.new('RGBA', (LW, 160), ICE + (255,))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((-30, 0, LW - 1, 159), radius=34, outline=(40, 60, 120, 255), width=3)
        d.line((10, 3, 10, 156), fill=RED + (255,), width=3)
        d.line((70, 3, 70, 156), fill=(0, 88, 248, 255), width=3)
        d.line((196, 8, 196, 151), fill=RED + (255,), width=1)
        for cy in (38, 122):
            d.ellipse((150 - 22, cy - 22, 150 + 22, cy + 22), outline=RED + (255,), width=1)
            d.rectangle((149, cy - 1, 151, cy + 1), fill=RED + (255,))
        d.pieslice((196 - 10, 80 - 10, 196 + 10, 80 + 10), 90, 270, fill=(150, 200, 250, 255))
        d.rectangle((196, 72, 205, 88), outline=RED + (255,), width=2)
        return im

    def low(self, t):
        u, D = self.u, self.drop
        im = Image.new('RGBA', (LW, LH), NAVY + (255,))
        d = ImageDraw.Draw(im)
        if t < D:
            # титульный экран: звёзды летят вниз
            for (x, y, s, sp) in self.stars:
                yy = (y + t * sp) % LH
                d.rectangle((int(x), int(yy), int(x) + s - 1, int(yy) + s - 1), fill=WHITE + (255,))
            C.put(im, ptext('JARVIS', 24, YEL, (160, 60, 0)), LW / 2, 92)
            C.put(im, ptext('HOCKEY', 24, WHITE, (0, 88, 248)), LW / 2, 124)
            C.put(im, ptext("'26", 16, RED), LW / 2 + 70, 150)
            C.put(im, self.pe['h'], LW / 2 - 40, 200)
            C.put(im, self.pe['a'], LW / 2 + 40, 200)
            C.put(im, ptext('VS', 8, YEL), LW / 2, 200)
            if int((t - 0) / (u / 2)) % 2 == 0 or t > self.b(-1):
                C.put(im, ptext('НАЖМИ СТАРТ' if t < self.b(-1) else '> СТАРТ <', 8, WHITE if t < self.b(-1) else YEL), LW / 2, 252)
            C.put(im, ptext('© 2026 ' + C.HANDLE.upper(), 8, GRAY), LW / 2, 280)
        elif t < self.b(2):
            # выбор команд
            d.rectangle((0, 0, LW, LH / 2), fill=tuple(int(c * 0.6) for c in self.h.c1) + (255,))
            d.rectangle((0, LH / 2, LW, LH), fill=tuple(int(c * 0.6) for c in self.a.c1) + (255,))
            C.put(im, ptext('ВЫБОР КОМАНД', 8, YEL), LW / 2, 56)
            k1 = C.out_cubic(C.seg(t, D, D + 0.3))
            k2 = C.out_cubic(C.seg(t, self.b(1), self.b(1) + 0.3))
            C.put(im, ptext('1P', 16, WHITE), 30, 106)
            C.put(im, C.scale(self.pe['h'], 2, Image.NEAREST), LW / 2 + 20 + (1 - k1) * 200, 112)
            C.put(im, ptext(self.h.up, 8, WHITE), LW / 2, 162 + (1 - k1) * 100)
            if t >= self.b(1):
                C.put(im, ptext('2P', 16, WHITE), 30, 224)
                C.put(im, C.scale(self.pe['a'], 2, Image.NEAREST), LW / 2 + 20 - (1 - k2) * 200, 232)
                C.put(im, ptext(self.a.up, 8, WHITE), LW / 2, 282 + (1 - k2) * 100)
            if int(t / (u / 4)) % 2 == 0:
                C.put(im, ptext('VS', 16, YEL), LW / 2, LH / 2)
        elif t < self.b(6):
            self.game(im, t)
        elif t < self.b(9.5):
            self.game(im, t if t < self.b(6.6) else self.b(6.6), celebrate=False)
            self.dialog(im, t)
        else:
            for (x, y, s, sp) in self.stars:
                yy = (y + t * sp * 0.4) % LH
                d.rectangle((int(x), int(yy), int(x) + s - 1, int(yy) + s - 1), fill=(120, 120, 160, 255))
            n = 9 - int((t - self.b(9.5)) / u)
            C.put(im, ptext('ПРОДОЛЖИТЬ?', 16, WHITE), LW / 2, 70)
            C.put(im, ptext(str(max(0, n)), 32, YEL, RED), LW / 2, 116)
            C.put(im, ptext('ПОДПИШИСЬ', 16, SKY), LW / 2, 180)
            C.put(im, ptext('TELEGRAM', 16, WHITE), LW / 2, 208)
            C.put(im, ptext(C.HANDLE.upper(), 16, YEL), LW / 2, 236)
            if int(t / (u / 2)) % 2 == 0:
                C.put(im, ptext('ВСТАВЬ МОНЕТКУ', 8, GRAY), LW / 2, 276)
        return im

    def game(self, im, t, celebrate=True):
        u = self.u
        d = ImageDraw.Draw(im)
        tg, goal_t = self.b(2), self.b(4)
        # табло
        d.rectangle((0, 40, LW, 106), fill=BLACK + (255,))
        sc_h = 1 if (t >= goal_t and self.side == 'h') else 0
        sc_a = 1 if (t >= goal_t and self.side == 'a') else 0
        C.put(im, self.pe['h'].resize((22, 22), Image.NEAREST), 18, 62)
        C.put(im, self.pe['a'].resize((22, 22), Image.NEAREST), LW - 18, 62)
        C.put(im, ptext(abbr(self.h), 8, WHITE), 50, 62)
        C.put(im, ptext(abbr(self.a), 8, WHITE), LW - 50, 62)
        pop = 2 if (goal_t <= t < goal_t + 0.6 and int(t / 0.1) % 2 == 0) else 1
        C.put(im, ptext('%d:%d' % (sc_h, sc_a), 16, YEL), LW / 2, 62)
        clock = max(0, 1200 - int((t - tg) * 240))
        C.put(im, ptext('%02d:%02d  1-Й ПЕРИОД' % (clock // 60, clock % 60), 8, GRAY), LW / 2, 90)
        # площадка (половина, атакует команда прогноза)
        ry = 116
        im.alpha_composite(self.rink, (0, ry))
        att = self.side
        opp = 'a' if att == 'h' else 'h'
        A = [C.scale(sp, 2, Image.NEAREST) for sp in self.spr[att]]
        B = [C.scale(sp.transpose(Image.FLIP_LEFT_RIGHT) if att == 'a' else sp, 2, Image.NEAREST) for sp in self.spr[opp]]
        A = [sp.transpose(Image.FLIP_LEFT_RIGHT) if att == 'a' else sp for sp in A]
        B = [sp.transpose(Image.FLIP_LEFT_RIGHT) for sp in B] if att == 'h' else B
        b3 = self.b(3)
        # шайба и игроки по ходу атаки
        c1 = (C.lerp(30, 112, C.in_out(C.seg(t, tg, b3))), C.lerp(80, 40, C.in_out(C.seg(t, tg, b3))))
        c2 = (C.lerp(60, 140, C.in_out(C.seg(t, tg, b3 + 0.25))), C.lerp(140, 118, C.in_out(C.seg(t, tg, b3 + 0.25))))
        c2 = (C.lerp(c2[0], 168, C.in_out(C.seg(t, b3 + 0.25, goal_t))), C.lerp(c2[1], 104, C.in_out(C.seg(t, b3 + 0.25, goal_t))))
        c3 = (C.lerp(20, 96, C.seg(t, tg, goal_t)), C.lerp(100, 82, C.seg(t, tg, goal_t)))
        if t < b3:
            pk = (c1[0] + 10, c1[1] + 10)
        elif t < b3 + 0.25:
            k = C.seg(t, b3, b3 + 0.25)
            pk = (C.lerp(c1[0] + 10, c2[0] + 10, k), C.lerp(c1[1] + 10, c2[1] + 10, k))
        elif t < goal_t:
            pk = (c2[0] + 10, c2[1] + 10)
        else:
            k = C.seg(t, goal_t, goal_t + 0.12)
            pk = (C.lerp(c2[0] + 10, 201, k), C.lerp(c2[1] + 10, 80, k))
        fi = int(t * 8) % 2
        jump = (lambda i: -6 * abs(math.sin(t * 9 + i))) if t >= goal_t else (lambda i: 0)
        for i, (x, y) in enumerate((c1, c2, c3)):
            C.put(im, A[(fi + i) % 2], x, ry + y - 10 + jump(i))
        foes = [(150 - 30 * C.seg(t, tg, goal_t), 60), (130, 120 - 10 * math.sin(t * 2)), (175, 46 + 30 * C.seg(t, tg, goal_t))]
        for i, (x, y) in enumerate(foes):
            C.put(im, B[(fi + i + 1) % 2], x + 3 * math.sin(t * 4 + i), ry + y - 10)
        gy = 80 + C.clamp((pk[1] - 80) * 0.5, -10, 10)
        C.put(im, B[0], 186, ry + gy - 10)                                # вратарь
        d.rectangle((pk[0] - 1, ry + pk[1] - 1, pk[0] + 2, ry + pk[1] + 2), fill=BLACK + (255,))
        if t >= goal_t and celebrate:
            if int(t / 0.12) % 2 == 0:
                C.put(im, ptext('ГОЛ!', 32, YEL, RED), LW / 2, ry + 80)
            C.put(im, ptext(self.fav.up, 8, WHITE, BLACK), LW / 2, ry + 112)

    def dialog(self, im, t):
        d = ImageDraw.Draw(im)
        y0 = 196
        d.rectangle((6, y0, LW - 7, y0 + 92), fill=BLACK + (255,), outline=WHITE + (255,), width=2)
        d.rectangle((10, y0 + 4, LW - 11, y0 + 88), outline=GRAY + (255,), width=1)
        t0 = self.b(6.2)
        s = self.dialog_text
        n = int(C.clamp((t - t0) / (self.u * 2.4)) * len(s))
        # перенос по словам на ширину окна (8 px на знак)
        words, rows, cur = s[:n].split(' '), [], ''
        for w in words:
            if len(cur) + len(w) + 1 > 23:
                rows.append(cur)
                cur = w
            else:
                cur = (cur + ' ' + w).strip()
        rows.append(cur)
        for i, r in enumerate(rows[:5]):
            C.put(im, ptext(r, 8, YEL if i == 0 else WHITE, None), 16, y0 + 12 + i * 14, anchor='tl')
        if n >= len(s) and int(t / 0.25) % 2 == 0:
            d.polygon([(LW - 24, y0 + 78), (LW - 14, y0 + 78), (LW - 19, y0 + 84)], fill=WHITE + (255,))
        C.put(im, ptext(self.when, 8, WHITE, BLACK), LW / 2, y0 - 10)

    def frame(self, t):
        lo = self.low(t)
        fr = lo.resize((W, H), Image.NEAREST)
        fr.alpha_composite(self.scan)
        D = self.drop
        if D <= t < D + 0.15:
            fr = Image.blend(fr.convert('RGB'), Image.new('RGB', (W, H), WHITE), 0.8 * (1 - C.seg(t, D, D + 0.15)))
        if self.b(4) <= t < self.b(4) + 0.4:
            dx, dy = C.shake(t, self.b(4), 20, 0.4)
            fr = C.zoom(fr, 1.0, dx=int(dx / S) * S, dy=int(dy / S) * S)
        return C.vignette(fr, 0.35)
