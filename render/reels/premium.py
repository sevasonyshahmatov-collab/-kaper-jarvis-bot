# -*- coding: utf-8 -*-
"""«Премиум»-серия роликов-прогнозов (16.10.2026, просьба владельца: «очень премиально, по-богатому, без космоса —
просто по факту, но очень стильно»). Восемь разных подач, каждая — под свой трек (render/reels/run_premium.py):

  Editorial  — чёрный матовый журнал: золотые волоски, огромный узкий шрифт, жёсткие склейки на долю
  Spotlight  — тёмная арена: луч прожектора сверху, эмблемы по очереди в свете, спокойный наезд
  Broadcast  — графика ТВ-трансляции: плашки-«нижние трети» с цветными торцами, табло сверху, быстрые шторки
  Split      — экран делится на два цвета клубов по диагонали, на дропе — белая карточка прогноза
  Card       — чёрная металлическая карта с золотым тиснением: поворот в 3D, на дропе — переворот на прогноз
  Kinetic    — светлая подача: крупная чёрная типографика бегущими строками, цветные плашки клубов
  Glass      — матовое стекло поверх мягких пятен клубных цветов, тонкая светлая рамка
  Film       — кино: шторки-кашеты, тёплое зерно, блик плёнки, титры с антиквой

Матч и прогноз — dict: league, date ('16 октября'), time ('19:00'), home, away, pick, kef, facts (две строки).
Время в ролике: drop — дроп трека (с), u — доля (с). После дропа: прогноз → кэф → два факта → финал.
Всё содержимое — в безопасной зоне Shorts (C.SAFE_TOP…C.SAFE_BOT); ниже — плашка Telegram из core.footer.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import fresh as F

W, H = C.W, C.H
GOLD = (214, 180, 106)
GOLD_HI = (246, 222, 160)
INK = (12, 12, 14)
PAPER = (242, 239, 232)


def kef_s(k):
    return ('%.2f' % float(k)).replace('.', ',')


def lg_ru(m):
    return 'НХЛ' if str(m['league']).upper() == 'NHL' else 'КХЛ'


def head_line(m):
    return '%s · %s · %s МСК' % (lg_ru(m), m['date'].upper(), m['time'])


def ease(x):
    return C.in_out(C.clamp(x))


def mix(c1, c2, k):
    return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))


def cdist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def distinct(team, ch):
    """Цвет гостей, заметно отличный от цвета хозяев (иначе — второй цвет клуба или графит)."""
    ca = F.club(team)
    if cdist(ca, ch) > 110:
        return ca
    for c in (team.c2, team.c0, team.c1):
        if cdist(c, ch) > 110 and 30 < sum(c) / 3 < 230:
            return tuple(c)
    return (46, 48, 56)


def dark(c, k=0.5):
    return tuple(int(v * k) for v in c)


class Base(C.Reel):
    """Общее: команды, цвета, время сцен по долям после дропа."""
    POST = 11.5                       # секунд после дропа

    def __init__(self, m, u=0.5, drop=4.5, seed=5):
        super().__init__(u, drop, seed)
        self.m = m
        self.h, self.a = C.match(m['home'], m['away'], m['league'])
        self.ch = F.club(self.h)
        self.ca = distinct(self.a, self.ch)
        self.dur = drop + self.snap(self.POST)
        self.t_pick = drop
        self.t_kef = drop + self.snap(1.6)
        self.t_f1 = drop + self.snap(3.4)
        self.t_f2 = drop + self.snap(5.2)
        self.t_end = drop + self.snap(8.4)
        self.cover_t = drop + self.snap(6.6)
        self.pick_up = m['pick'].upper()

    def snap(self, sec):
        return max(1, round(sec / self.u)) * self.u

    def beat_idx(self, t):
        return math.floor((t - self.drop) / self.u + 1e-6)

    def q(self, t, t0, d=0.45):
        return C.out_expo(C.seg(t, t0, t0 + d))

    def gone(self, t, t1, d=0.3):
        return 1 - C.seg(t, t1 - d, t1)

    def emb(self, team, size):
        return team.emb(size)


# ════════════════════════════ 1. Editorial ════════════════════════════
class Editorial(Base):
    def __init__(self, m, **kw):
        super().__init__(m, **kw)
        self.bg = Image.new('RGBA', (W, H), (11, 11, 12, 255))
        fr = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(fr)
        d.rectangle((54, 200, W - 54, 1500), outline=GOLD + (150,), width=2)
        self.frame_ln = fr
        self.head = C.text(head_line(m), 'manrope', 30, GOLD, 800, track=0.22)
        self.hn = C.text(self.h.up, 'osw', 230, (245, 243, 238), 700, max_w=900)
        self.an = C.text(self.a.up, 'osw', 230, (245, 243, 238), 700, max_w=900)
        self.vs = C.text('ПРОТИВ', 'manrope', 34, GOLD, 800, track=0.6)
        self.e_h, self.e_a = self.h.emb(520), self.a.emb(520)
        self.s_h, self.s_a = self.h.emb(210), self.a.emb(210)
        self.lab = C.text('ПРОГНОЗ', 'manrope', 32, GOLD, 800, track=0.6)
        self.pick = C.lines(self.pick_up, 'osw', 102, 900, (245, 243, 238), 700, gap=0.02, max_lines=3)
        self.klab = C.text('КОЭФФИЦИЕНТ', 'manrope', 30, (170, 168, 160), 800, track=0.5)
        self.kef = C.text(kef_s(m['kef']), 'osw', 200, GOLD_HI, 600)
        self.facts = [C.lines(f.upper(), 'manrope', 36, 900, (230, 228, 222), 700, gap=0.18, max_lines=2) for f in m['facts']]
        self.mark = C.text('JARVIS', 'osw', 64, (245, 243, 238), 700, track=0.3)
        self.handle = C.text(C.HANDLE, 'manrope', 40, GOLD, 800, track=0.1)

    def frame(self, t):
        fr = self.bg.copy()
        D = self.drop
        if t < D:
            # склейки на долю: эмблема хозяев на их цвете → эмблема гостей → имена
            k = int((t - D) / self.u) % 4 if t >= D - 4 * self.u * 2 else -1
            n = math.floor((t - 0.0) / (self.u * 2))
            scene = n % 3 if t < D - 2 * self.u else 2
            if scene in (0, 1):
                team, col, e = (self.h, self.ch, self.e_h) if scene == 0 else (self.a, self.ca, self.e_a)
                fr.paste(dark(col, 0.42) + (255,), (54, 200, W - 54, 1500))
                lt = (t % (self.u * 2)) / (self.u * 2)
                C.put(fr, C.scale(e, 1.0 + 0.05 * lt), W / 2, 820)
                nm = C.text(team.up, 'osw', 150, (245, 243, 238), 700, max_w=900)
                C.put(fr, nm, W / 2, 1270)
            else:
                ts = min(n * self.u * 2, D - 2 * self.u) if t < D - 2 * self.u else D - 2 * self.u
                C.put(fr, self.hn, W / 2, 700, self.q(t, ts, 0.25))
                C.put(fr, self.vs, W / 2, 860, self.q(t, ts + 0.4 * self.u, 0.25))
                C.put(fr, self.an, W / 2, 1020, self.q(t, ts + 0.8 * self.u, 0.25))
            C.put(fr, self.head, W / 2, 258)
        else:
            z = 1 + 0.03 * C.seg(t, D, self.dur)
            # эмблемы и золотая черта
            q = self.q(t, D, 0.5)
            C.put(fr, self.s_h, W / 2 - 230 - 40 * (1 - q), 420, q)
            C.put(fr, self.s_a, W / 2 + 230 + 40 * (1 - q), 420, q)
            ln = int(240 * self.q(t, D + 0.1, 0.6))
            if ln > 2:
                ImageDraw.Draw(fr).line((W / 2 - ln / 2, 420, W / 2 + ln / 2, 420), fill=GOLD + (255,), width=2)
            C.put(fr, self.lab, W / 2, 600, self.q(t, D + 0.05))
            qp = self.q(t, D + 0.1, 0.5)
            C.put(fr, self.pick, W / 2, 600 + 40 + self.pick.height / 2 + 30 * (1 - qp), qp)
            y = 640 + self.pick.height + 60
            qk = self.q(t, self.t_kef, 0.5)
            C.put(fr, self.klab, W / 2, y, qk)
            C.put(fr, C.scale(self.kef, 0.9 + 0.1 * qk), W / 2, y + 125, qk)
            y2 = y + 280
            for i, (f, t0) in enumerate(((self.facts[0], self.t_f1), (self.facts[1], self.t_f2))):
                qf = self.q(t, t0, 0.5)
                yy = y2 + i * 125
                if qf > 0:
                    ImageDraw.Draw(fr).line((W / 2 - 60 * qf, yy - 50, W / 2 + 60 * qf, yy - 50), fill=GOLD + (255,), width=2)
                C.put(fr, f, W / 2, yy + 10 + 20 * (1 - qf), qf)
            C.put(fr, self.head, W / 2, 258)
            if t > self.t_end:
                qe = self.q(t, self.t_end, 0.6)
                ov = Image.new('RGBA', (W, H), (11, 11, 12, int(235 * qe)))
                fr.alpha_composite(ov)
                C.put(fr, self.mark, W / 2, 820, qe)
                C.put(fr, self.handle, W / 2, 920, qe)
                C.put(fr, C.text('ПРОГНОЗЫ НА КХЛ И НХЛ КАЖДЫЙ ДЕНЬ', 'manrope', 30, (190, 188, 180), 800, track=0.2), W / 2, 1000, qe)
            fr = C.zoom(fr, z)
        # вспышка на дропе
        fl = max(0.0, 1 - abs(t - D) / 0.12) if t >= D - 0.05 else 0
        if fl:
            fr.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(200 * fl))))
        fr.alpha_composite(self.frame_ln)
        return C.grain(fr, t, 5)


# ════════════════════════════ 2. Spotlight ════════════════════════════
class Spotlight(Base):
    def __init__(self, m, **kw):
        super().__init__(m, **kw)
        bg = C.vgrad(W, H, [(0, (6, 8, 14)), (0.5, (14, 16, 24)), (1, (5, 6, 10))]).convert('RGBA')
        self.bg = bg
        # конус света сверху
        cone = Image.new('L', (W, H), 0)
        ImageDraw.Draw(cone).polygon([(W / 2 - 70, 0), (W / 2 + 70, 0), (W / 2 + 470, 1250), (W / 2 - 470, 1250)], fill=90)
        cone = cone.filter(ImageFilter.GaussianBlur(70))
        y = np.linspace(1, 0.25, H)[:, None]
        cone = Image.fromarray((np.asarray(cone, np.float32) * y).astype(np.uint8))
        self.cone = cone
        self.floor = C.radial(900, 220, (255, 255, 255), 60, 1.6)
        self.e_h, self.e_a = self.h.emb(500), self.a.emb(500)
        self.s_h, self.s_a = self.h.emb(240), self.a.emb(240)
        self.head = C.text(head_line(m), 'manrope', 30, (200, 205, 220), 700, track=0.25)
        self.lab = C.text('НАШ ПРОГНОЗ', 'manrope', 30, (190, 196, 214), 700, track=0.5)
        self.pick = C.lines(self.pick_up, 'osw', 104, 920, (255, 255, 255), 500, gap=0.04, max_lines=3)
        kb = C.rrect(420, 150, 75, None, outline=(255, 255, 255), width=2)
        C.put(kb, C.text(kef_s(m['kef']), 'osw', 110, (255, 255, 255), 500), 210, 75)
        self.kbox = kb
        self.klab = C.text('КЭФ', 'manrope', 28, (170, 176, 196), 800, track=0.5)
        self.facts = [C.lines(f, 'manrope', 40, 880, (225, 228, 238), 600, gap=0.2, max_lines=2) for f in m['facts']]

    def light(self, fr, col, k):
        lay = Image.new('RGBA', (W, H), tuple(F.bright(col, 0.6)) + (0,))
        lay.putalpha(self.cone.point(lambda v: int(v * k)))
        fr.alpha_composite(lay)

    def frame(self, t):
        fr = self.bg.copy()
        D = self.drop
        if t < D:
            half = D / 2
            first = t < half
            team, e, col = (self.h, self.e_h, self.ch) if first else (self.a, self.e_a, self.ca)
            t0 = 0 if first else half
            q = C.seg(t, t0, t0 + 0.8)
            out = 1 - C.seg(t, t0 + half - 0.35, t0 + half)
            self.light(fr, col, 1.6 * q * out)
            C.put(fr, self.floor, W / 2, 1150, q * out)
            z = 0.92 + 0.08 * C.seg(t, t0, t0 + half)
            C.put(fr, C.with_shadow(C.scale(e, z), 30, 0.6, 30), W / 2, 760, q * out)
            C.put(fr, C.text(team.up, 'osw', 120, (255, 255, 255), 500, track=0.06, max_w=920), W / 2, 1230, q * out)
            C.put(fr, self.head, W / 2, 260, C.seg(t, 0.2, 1.0))
        else:
            self.light(fr, mix(self.ch, self.ca, 0.5), 1.1)
            q = self.q(t, D, 0.6)
            C.put(fr, self.s_h, W / 2 - 210, 430 + 30 * (1 - q), q)
            C.put(fr, self.s_a, W / 2 + 210, 430 + 30 * (1 - q), q)
            C.put(fr, C.text('—', 'osw', 60, (200, 205, 220), 400), W / 2, 430, q)
            C.put(fr, self.lab, W / 2, 640, self.q(t, D + 0.15))
            qp = self.q(t, D + 0.2, 0.6)
            yp = 690 + self.pick.height / 2
            C.put(fr, self.pick, W / 2, yp + 20 * (1 - qp), qp)
            y = 700 + self.pick.height + 110
            qk = self.q(t, self.t_kef, 0.5)
            C.put(fr, self.klab, W / 2, y - 20, qk)
            C.put(fr, self.kbox, W / 2, y + 90, qk)
            for i, (f, t0) in enumerate(((self.facts[0], self.t_f1), (self.facts[1], self.t_f2))):
                qf = self.q(t, t0, 0.6)
                C.put(fr, f, W / 2, y + 290 + i * 130, qf)
            C.put(fr, self.head, W / 2, 260)
            if t > self.t_end:
                qe = self.q(t, self.t_end, 0.7)
                fr.alpha_composite(Image.new('RGBA', (W, H), (6, 8, 14, int(230 * qe))))
                self.light(fr, (255, 255, 255), 0.8 * qe)
                C.put(fr, C.text('JARVIS', 'osw', 90, (255, 255, 255), 500, track=0.35), W / 2, 780, qe)
                C.put(fr, C.text(C.HANDLE, 'manrope', 42, (210, 215, 230), 700, track=0.1), W / 2, 880, qe)
            fr = C.zoom(fr, 1 + 0.025 * C.seg(t, D, self.dur))
        return C.grain(C.vignette(fr, 0.5), t, 4)


# ════════════════════════════ 3. Broadcast ════════════════════════════
class Broadcast(Base):
    def __init__(self, m, **kw):
        super().__init__(m, **kw)
        bg = C.vgrad(W, H, [(0, (16, 22, 34)), (1, (8, 10, 16))]).convert('RGBA')
        d = ImageDraw.Draw(bg)
        for x in range(-H, W, 46):
            d.line((x, H, x + H * 0.5, 0), fill=(255, 255, 255, 7), width=2)
        self.bg = bg
        self.s_h, self.s_a = self.h.emb(130), self.a.emb(130)
        self.e_h, self.e_a = self.h.emb(420), self.a.emb(420)
        self.bug = self._bug()
        self.pick_bar = self._bar('НАШ ПРОГНОЗ', self.pick_up, (255, 255, 255), (12, 16, 26))
        self.facts = [self._fact(i, f) for i, f in enumerate(m['facts'])]

    def _bug(self):
        bw, bh = 960, 120
        b = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
        b.alpha_composite(C.rrect(bw, bh, 14, (14, 18, 28)), (0, 0))
        b.alpha_composite(Image.new('RGBA', (12, bh), self.ch + (255,)), (0, 0))
        b.alpha_composite(Image.new('RGBA', (12, bh), self.ca + (255,)), (bw - 12, 0))
        C.put(b, C.fit(self.s_h, 90, 90), 70, 60)
        C.put(b, C.text(self.h.up, 'robc', 46, (255, 255, 255), 800, max_w=280), 260, 60)
        C.put(b, C.fit(self.s_a, 90, 90), bw - 70, 60)
        C.put(b, C.text(self.a.up, 'robc', 46, (255, 255, 255), 800, max_w=280), bw - 260, 60)
        C.put(b, C.rrect(150, 76, 10, (255, 255, 255)), bw / 2, 60)
        C.put(b, C.text(self.m['time'], 'robc', 44, (12, 16, 26), 800), bw / 2, 60)
        return b

    def _bar(self, lab, txt, fill, ink):
        body = C.lines(txt, 'robc', 96, 860, ink, 800, gap=0.04, max_lines=3)
        bw, bh = 960, body.height + 150
        b = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
        b.alpha_composite(C.rrect(bw, bh, 16, fill), (0, 0))
        top = C.rrect(340, 56, 10, mix(self.ch, self.ca, 0.0))
        C.put(top, C.text(lab, 'robc', 30, (255, 255, 255), 800, track=0.2), 170, 28)
        b.alpha_composite(top, (40, 30))
        b.alpha_composite(body, (50, 108))
        return b

    def _fact(self, i, f):
        body = C.lines(f, 'robc', 52, 740, (255, 255, 255), 600, gap=0.12, max_lines=2)
        bw, bh = 960, max(160, body.height + 70)
        b = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
        b.alpha_composite(C.rrect(bw, bh, 14, (20, 26, 40), 235), (0, 0))
        b.alpha_composite(Image.new('RGBA', (10, bh), (self.ch, self.ca)[i % 2] + (255,)), (0, 0))
        C.put(b, C.text('0%d' % (i + 1), 'robc', 64, F.bright((self.ch, self.ca)[i % 2], 0.4), 800), 90, bh / 2)
        b.alpha_composite(body, (170, (bh - body.height) // 2))
        return b

    def wipe(self, im, q, fr, x, y):
        if q <= 0:
            return
        w = max(2, int(im.width * q))
        C.put(fr, im.crop((0, 0, w, im.height)), x, y, anchor='tl')

    def frame(self, t):
        fr = self.bg.copy()
        D = self.drop
        self.wipe(self.bug, self.q(t, 0.2, 0.4), fr, 60, 250)
        if t < D:
            n = int(t / (self.u * 2))
            team, e, col = (self.h, self.e_h, self.ch) if n % 2 == 0 else (self.a, self.e_a, self.ca)
            lt = (t % (self.u * 2)) / (self.u * 2)
            band = Image.new('RGBA', (W, 640), dark(col, 0.55) + (255,))
            C.put(fr, band, W / 2 + (1 - C.out_expo(min(1, lt * 3))) * W, 840)
            C.put(fr, C.scale(e, 0.95 + 0.06 * lt), W / 2, 800)
            name = C.text(team.up, 'robc', 110, (255, 255, 255), 800, max_w=900)
            self.wipe(name.copy(), C.out_expo(min(1, lt * 2.5)), fr, (W - name.width) / 2, 1150)
            C.put(fr, C.text('%s · %s' % (lg_ru(self.m), self.m['date'].upper()), 'robc', 40, (180, 190, 210), 700, track=0.2), W / 2, 450)
        else:
            y0 = 520
            self.wipe(self.pick_bar, self.q(t, D, 0.35), fr, 60, y0)
            y = y0 + self.pick_bar.height + 40
            kb = C.rrect(960, 210, 16, dark(self.ca, 0.8) if sum(self.ca) > 120 else (40, 50, 70))
            C.put(kb, C.text('КЭФ', 'robc', 50, (255, 255, 255), 800, track=0.3), 150, 105)
            C.put(kb, C.text(kef_s(self.m['kef']), 'robc', 170, (255, 255, 255), 800), 640, 105)
            self.wipe(kb, self.q(t, self.t_kef, 0.35), fr, 60, y)
            y += 250
            for i, (f, t0) in enumerate(((self.facts[0], self.t_f1), (self.facts[1], self.t_f2))):
                self.wipe(f, self.q(t, t0, 0.35), fr, 60, y)
                y += f.height + 24
            if t > self.t_end:
                qe = self.q(t, self.t_end, 0.4)
                end = C.rrect(960, 300, 18, (255, 255, 255))
                C.put(end, C.text('JARVIS', 'robc', 110, (12, 16, 26), 800, track=0.15), 480, 115)
                C.put(end, C.text('ПРОГНОЗЫ КХЛ И НХЛ · %s' % C.HANDLE, 'robc', 38, (60, 70, 90), 700, track=0.08), 480, 225)
                fr.alpha_composite(Image.new('RGBA', (W, H), (8, 10, 16, int(200 * qe))))
                self.wipe(end, qe, fr, 60, 760)
        return C.grain(fr, t, 3)


# ════════════════════════════ 4. Split ════════════════════════════
class Split(Base):
    def __init__(self, m, **kw):
        super().__init__(m, **kw)
        self.e_h, self.e_a = self.h.emb(400), self.a.emb(400)
        self.head = C.text(head_line(m), 'mont', 30, (255, 255, 255), 800, track=0.2)
        cw = 900
        body = C.lines(self.pick_up, 'mont', 72, cw - 120, INK, 900, gap=0.06, max_lines=3)
        facts = [C.lines(f, 'mont', 40, cw - 150, (60, 62, 70), 600, gap=0.2, max_lines=2) for f in m['facts']]
        self.card_h = 200 + body.height + 240
        self.body, self.cfacts = body, facts
        self.cw = cw
        self.n_h = C.text(self.h.up, 'mont', 92, (255, 255, 255), 900, max_w=860)
        self.n_a = C.text(self.a.up, 'mont', 92, (255, 255, 255), 900, max_w=860)

    def halves(self, k):
        """k: 0 — пусто, 1 — обе половины на месте."""
        fr = Image.new('RGBA', (W, H), (14, 14, 16, 255))
        top = Image.new('RGBA', (W, H), dark(self.ch, 0.75) + (255,))
        bot = Image.new('RGBA', (W, H), dark(self.ca, 0.75) + (255,))
        mk = Image.new('L', (W, H), 0)
        sh = int((1 - k) * W)
        ImageDraw.Draw(mk).polygon([(-sh, 0), (W - sh, 0), (W - sh, 760), (-sh, 1100)], fill=255)
        fr.paste(top, (0, 0), mk)
        mk2 = Image.new('L', (W, H), 0)
        ImageDraw.Draw(mk2).polygon([(sh, 1100), (W + sh, 760), (W + sh, H), (sh, H)], fill=255)
        fr.paste(bot, (0, 0), mk2)
        return fr

    def frame(self, t):
        D = self.drop
        k = ease(C.seg(t, 0.1, 0.9))
        fr = self.halves(k)
        lt = C.seg(t, 0, D)
        C.put(fr, C.with_shadow(C.scale(self.e_h, 0.95 + 0.05 * lt), 24, 0.45, 18), W / 2 - 160 + 40 * lt, 560, k)
        C.put(fr, C.with_shadow(C.scale(self.e_a, 0.95 + 0.05 * lt), 24, 0.45, 18), W / 2 + 160 - 40 * lt, 1180, k)
        if t < D:
            C.put(fr, self.n_h, W / 2, 340, self.q(t, 0.6))
            C.put(fr, self.n_a, W / 2, 1420, self.q(t, 1.0))
            C.put(fr, self.head, W / 2, 250, self.q(t, 0.3))
        else:
            fr.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(120 * self.q(t, D, 0.4)))))
            q = self.q(t, D, 0.5)
            card = C.rrect(self.cw, self.card_h + 160, 36, (250, 249, 246))
            C.put(card, C.text('ПРОГНОЗ', 'mont', 30, (140, 142, 150), 800, track=0.4), self.cw / 2, 80)
            card.alpha_composite(self.body, ((self.cw - self.body.width) // 2, 130))
            y = 130 + self.body.height + 50
            qk = self.q(t, self.t_kef, 0.4)
            if qk > 0:
                pill = C.rrect(380, 110, 55, INK)
                C.put(pill, C.text('КЭФ  ' + kef_s(self.m['kef']), 'mont', 52, (255, 255, 255), 900), 190, 55)
                C.put(card, C.scale(pill, 0.9 + 0.1 * qk), self.cw / 2, y + 55, qk)
            y += 150
            for i, (f, t0) in enumerate(((self.cfacts[0], self.t_f1), (self.cfacts[1], self.t_f2))):
                qf = self.q(t, t0, 0.4)
                if qf > 0:
                    dot = C.ellipse(18, 18, (self.ch, self.ca)[i])
                    C.put(card, dot, 70, y + 26, qf)
                    C.put(card, f, 110, y, qf, anchor='tl')
                y += f.height + 30
            sc = 0.9 + 0.1 * q
            C.put(fr, C.with_shadow(C.scale(card, sc), 30, 0.45, 24), W / 2, 860 + 60 * (1 - q), q)
            C.put(fr, self.head, W / 2, 250)
            if t > self.t_end:
                qe = self.q(t, self.t_end, 0.5)
                fr.alpha_composite(Image.new('RGBA', (W, H), (14, 14, 16, int(235 * qe))))
                C.put(fr, C.text('JARVIS', 'mont', 110, (255, 255, 255), 900, track=0.1), W / 2, 790, qe)
                C.put(fr, C.text(C.HANDLE, 'mont', 46, (200, 200, 205), 700), W / 2, 900, qe)
        return C.grain(fr, t, 3)


# ════════════════════════════ 5. Card ════════════════════════════
def perspective(im, ang):
    """Поворот плоской карты вокруг вертикальной оси на ang (рад) — перспектива."""
    w, h = im.size
    c = math.cos(ang)
    if abs(c) < 0.03:
        return None
    nw = max(2, int(w * abs(c)))
    depth = 0.16 * math.sin(ang)
    out_w, out_h = nw, int(h * (1 + abs(depth)))
    # углы цели: левый край выше/ниже правого
    lh, rh = h * (1 + depth), h * (1 - depth)
    tl, bl = (0, (out_h - lh) / 2), (0, (out_h + lh) / 2)
    tr, br = (nw, (out_h - rh) / 2), (nw, (out_h + rh) / 2)
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    dst = [tl, tr, br, bl]
    A = []
    B = []
    for (xs, ys), (xd, yd) in zip(src, dst):
        A.append([xd, yd, 1, 0, 0, 0, -xs * xd, -xs * yd]); B.append(xs)
        A.append([0, 0, 0, xd, yd, 1, -ys * xd, -ys * yd]); B.append(ys)
    coef = np.linalg.solve(np.array(A, float), np.array(B, float))
    img = im if c > 0 else im.transpose(Image.FLIP_LEFT_RIGHT)
    return img.transform((out_w, out_h), Image.PERSPECTIVE, tuple(coef), Image.BICUBIC)


class Card(Base):
    CW, CH = 880, 1120

    def __init__(self, m, **kw):
        super().__init__(m, **kw)
        bg = C.vgrad(W, H, [(0, (18, 18, 20)), (1, (6, 6, 7))]).convert('RGBA')
        d = ImageDraw.Draw(bg)
        for y in range(0, H, 6):
            d.line((0, y, W, y), fill=(255, 255, 255, 4))
        self.bg = bg
        self.front = self._front()
        self.backs = [self._back(k) for k in range(4)]

    def _metal(self):
        w, h = self.CW, self.CH
        base = C.lgrad(w, h, (34, 34, 38), (14, 14, 16), 60)
        noise = np.random.default_rng(3).normal(0, 6, (h, 1)).repeat(w, 1)
        arr = np.asarray(base, np.float32)
        arr[..., :3] += noise[..., None]
        card = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
        mk = C.rrect(w, h, 44, (255, 255, 255)).getchannel('A')
        card.putalpha(mk)
        d = ImageDraw.Draw(card)
        d.rounded_rectangle((18, 18, w - 18, h - 18), radius=32, outline=GOLD + (170,), width=2)
        return card

    def _front(self):
        c = self._metal()
        C.put(c, C.text('JARVIS', 'osw', 54, GOLD, 600, track=0.45), self.CW / 2, 110)
        C.put(c, C.text(head_line(self.m), 'manrope', 26, (170, 160, 130), 700, track=0.2), self.CW / 2, 175)
        eh, ea = C.fit(self.h.emb(260), 260, 260), C.fit(self.a.emb(260), 260, 260)
        C.put(c, eh, self.CW / 2, 380)
        C.put(c, C.text(self.h.up, 'osw', 72, (240, 236, 226), 500, track=0.08, max_w=760), self.CW / 2, 575)
        C.put(c, C.text('VS', 'osw', 44, GOLD, 500, track=0.3), self.CW / 2, 650)
        C.put(c, C.text(self.a.up, 'osw', 72, (240, 236, 226), 500, track=0.08, max_w=760), self.CW / 2, 725)
        C.put(c, ea, self.CW / 2, 930)
        return c

    def _back(self, level=3):
        """Оборот карты: 0 — только прогноз, 1 — + кэф, 2 — + первый факт, 3 — + второй факт."""
        c = self._metal()
        C.put(c, C.text('ПРОГНОЗ', 'manrope', 30, GOLD, 800, track=0.6), self.CW / 2, 120)
        pk = C.lines(self.pick_up, 'osw', 96, 760, (244, 240, 230), 500, gap=0.04, max_lines=3)
        C.put(c, pk, self.CW / 2, 170 + pk.height / 2)
        y = 210 + pk.height + 60
        ImageDraw.Draw(c).line((self.CW / 2 - 80, y, self.CW / 2 + 80, y), fill=GOLD + (255,), width=2)
        if level >= 1:
            C.put(c, C.text('КОЭФФИЦИЕНТ', 'manrope', 26, (170, 160, 130), 800, track=0.5), self.CW / 2, y + 60)
            C.put(c, C.text(kef_s(self.m['kef']), 'osw', 180, GOLD_HI, 500), self.CW / 2, y + 185)
        y += 320
        for i, f in enumerate(self.m['facts']):
            if level >= 2 + i:
                fl = C.lines(f, 'manrope', 38, 740, (220, 214, 200), 600, gap=0.2, max_lines=2)
                C.put(c, fl, self.CW / 2, y + fl.height / 2)
                y += fl.height + 40
        C.put(c, C.text(C.HANDLE, 'manrope', 30, GOLD, 800, track=0.1), self.CW / 2, self.CH - 70)
        return c

    def frame(self, t):
        fr = self.bg.copy()
        D = self.drop
        # до дропа — лицо карты, лёгкое покачивание; на дропе — переворот за 0.6 с; дальше — медленное покачивание
        if t < D:
            ang = 0.35 * math.sin(t * 0.9) * (1 - C.seg(t, D - 0.6, D)) - 0.5 * (1 - C.out_cubic(C.seg(t, 0, 1.2)))
            im = self.front
        else:
            p = C.in_out(C.seg(t, D, D + 0.6))
            ang = math.pi * p + 0.12 * math.sin((t - D) * 0.8) * C.seg(t, D + 0.6, D + 1.5)
            im = self.front
            if p >= 0.5:
                ang = ang - math.pi
        if t >= D and im is self.front and p >= 0.5:
            im = self.backs[0]
        if t >= D and p >= 0.5:
            lvl = sum(1 for t0 in (self.t_kef, self.t_f1, self.t_f2) if t >= t0)
            im = self.backs[lvl]
        pc = perspective(im, ang)
        if pc is not None:
            sh = C.shadow(pc, 40, 0.65)
            C.put(fr, sh, W / 2, 880 + 40)
            C.put(fr, pc, W / 2, 860)
            # блик по металлу
            gx = (math.sin(t * 0.7) * 0.5 + 0.5) * pc.width
            hl = C.lgrad(pc.width, pc.height, (255, 255, 255), (255, 255, 255), 20, 0, 0)
            band = Image.new('L', pc.size, 0)
            ImageDraw.Draw(band).polygon([(gx - 120, 0), (gx + 20, 0), (gx - 260, pc.height), (gx - 400, pc.height)], fill=40)
            band = band.filter(ImageFilter.GaussianBlur(30))
            band = Image.fromarray(np.minimum(np.asarray(band), np.asarray(pc.getchannel('A'))))
            hl = Image.new('RGBA', pc.size, (255, 248, 230, 0))
            hl.putalpha(band)
            C.put(fr, hl, W / 2, 860)
        if t > self.t_end:
            qe = self.q(t, self.t_end, 0.6)
            fr.alpha_composite(Image.new('RGBA', (W, H), (8, 8, 9, int(235 * qe))))
            C.put(fr, C.text('JARVIS', 'osw', 110, GOLD, 600, track=0.45), W / 2, 800, qe)
            C.put(fr, C.text(C.HANDLE, 'manrope', 44, (220, 214, 200), 800, track=0.1), W / 2, 910, qe)
        return C.grain(C.vignette(fr, 0.45), t, 4)

    def _metal_cache(self):
        if not hasattr(self, '_mc'):
            self._mc = self._metal()
        return self._mc


# ════════════════════════════ 6. Kinetic ════════════════════════════
class Kinetic(Base):
    def __init__(self, m, **kw):
        super().__init__(m, **kw)
        self.bg = Image.new('RGBA', (W, H), PAPER + (255,))
        self.big_h = C.text(self.h.up, 'osw', 250, INK, 700)
        self.big_a = C.text(self.a.up, 'osw', 250, INK, 700)
        self.vs = C.text('VS', 'osw', 200, INK, 700, stroke=4, outline=True)
        self.e_h, self.e_a = self.h.emb(240), self.a.emb(240)
        # прогноз — строками по ширине, каждая строка на свою долю
        f = C.font('osw', 132, 700)
        rows, cur = [], ''
        for w in self.pick_up.split():
            tt = (cur + ' ' + w).strip()
            if f.getlength(tt) <= 950 or not cur:
                cur = tt
            else:
                rows.append(cur)
                cur = w
        rows.append(cur)
        self.rows = [C.text(r, 'osw', 132, INK, 700, max_w=960) for r in rows[:4]]
        self.kef = C.text(kef_s(m['kef']), 'osw', 220, INK, 700)
        self.facts = [C.lines(f_.upper(), 'osw', 52, 940, INK, 500, gap=0.08, max_lines=2) for f_ in m['facts']]
        self.head = C.text(head_line(m), 'mont', 30, INK, 800, track=0.2)

    def frame(self, t):
        fr = self.bg.copy()
        D = self.drop
        C.put(fr, self.head, W / 2, 255)
        if t < D:
            # имена огромным шрифтом проезжают через кадр навстречу друг другу, цветные плашки клубов
            p = C.seg(t, 0, D)
            C.put(fr, self.big_h, W + self.big_h.width / 2 - p * (W + self.big_h.width * 0.9), 560)
            C.put(fr, self.vs, W / 2, 820, C.seg(t, 0.5, 1.2))
            C.put(fr, self.big_a, -self.big_a.width / 2 + p * (W + self.big_a.width * 0.9), 1080)
            for i, (col, e, t0, x) in enumerate(((self.ch, self.e_h, D - 4 * self.u, 0), (self.ca, self.e_a, D - 2 * self.u, 540))):
                bq = ease(C.seg(t, t0, t0 + self.u))
                if bq > 0:
                    b = Image.new('RGBA', (540, int(260 * bq)), col + (255,))
                    C.put(fr, b, x, 1220, anchor='tl')
                    C.put(fr, C.fit(e, 210, 210), x + 270, 1350, bq)
        else:
            y = 400
            for i, im in enumerate(self.rows):
                q = self.q(t, D + i * self.u, 0.25)
                if q > 0:
                    C.put(fr, im, 60 + 40 * (1 - q), y, q, anchor='tl')
                y += im.height + 22
            y += 30
            qk = self.q(t, self.t_kef, 0.35)
            if qk > 0:
                C.put(fr, C.text('КЭФ', 'mont', 40, INK, 900, track=0.3), 60, y, qk, anchor='tl')
                C.put(fr, self.kef, 60, y + 60, qk, anchor='tl')
                bar = Image.new('RGBA', (int(self.kef.width * qk), 24), self.ch + (255,))
                C.put(fr, bar, 60, y + 60 + self.kef.height + 20, anchor='tl')
            yy = y + 60 + self.kef.height + 80
            for i, (f_, t0) in enumerate(((self.facts[0], self.t_f1), (self.facts[1], self.t_f2))):
                qf = self.q(t, t0, 0.35)
                C.put(fr, f_, 60 + 30 * (1 - qf), yy, qf, anchor='tl')
                yy += f_.height + 26
            if t > self.t_end:
                qe = ease(C.seg(t, self.t_end, self.t_end + 0.45))
                cov = Image.new('RGBA', (W, max(1, int(H * qe))), INK + (255,))
                C.put(fr, cov, 0, 0, anchor='tl')
                if qe > 0.6:
                    a = (qe - 0.6) / 0.4
                    C.put(fr, C.text('JARVIS', 'osw', 200, PAPER, 700, track=0.05), W / 2, 790, a)
                    C.put(fr, C.text(C.HANDLE, 'mont', 48, PAPER, 800), W / 2, 930, a)
        return C.grain(fr, t, 3)


# ════════════════════════════ 7. Glass ════════════════════════════
class Glass(Base):
    def __init__(self, m, **kw):
        super().__init__(m, **kw)
        self.blobs = [(self.ch, 0.25, 0.3, 760), (self.ca, 0.75, 0.7, 820), (mix(self.ch, self.ca, 0.5), 0.6, 0.15, 560)]
        self.head = C.text(head_line(m), 'manrope', 30, (255, 255, 255), 700, track=0.22)
        self.e_h, self.e_a = self.h.emb(300), self.a.emb(300)
        self.names = C.text('%s  ·  %s' % (self.h.up, self.a.up), 'manrope', 40, (255, 255, 255), 800, track=0.12, max_w=780)
        self.pick = C.lines(self.pick_up, 'manrope', 80, 780, (255, 255, 255), 800, gap=0.08, max_lines=3)
        self.kef = C.text(kef_s(m['kef']), 'manrope', 130, (255, 255, 255), 800)
        self.facts = [C.lines(f, 'manrope', 42, 760, (245, 246, 250), 600, gap=0.22, max_lines=2) for f in m['facts']]

    def backdrop(self, t):
        small = Image.new('RGB', (W // 8, H // 8), (16, 16, 22))
        for i, (col, x, y, r) in enumerate(self.blobs):
            dx = 0.06 * math.sin(t * 0.35 + i * 2.1)
            dy = 0.04 * math.cos(t * 0.3 + i * 1.3)
            bl = C.radial(r // 4, r // 4, F.bright(col, 0.1), 255, 1.2)
            small.paste(bl, (int((x + dx) * W / 8 - r / 8), int((y + dy) * H / 8 - r / 8)), bl)
        return small.filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BICUBIC).convert('RGBA')

    def glass(self, fr, box, a=1.0):
        x0, y0, x1, y1 = [int(v) for v in box]
        if a <= 0.01 or y1 - y0 < 4:
            return
        reg = fr.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(28))
        reg.alpha_composite(Image.new('RGBA', reg.size, (255, 255, 255, int(34 * a))))
        mk = C.rrect(x1 - x0, y1 - y0, 40, (255, 255, 255), int(255 * a)).getchannel('A')
        fr.paste(reg, (x0, y0), mk)
        ol = C.rrect(x1 - x0, y1 - y0, 40, None, outline=(255, 255, 255), width=2)
        ol.putalpha(ol.getchannel('A').point(lambda v: int(v * 0.45 * a)))
        fr.alpha_composite(ol, (x0, y0))

    def frame(self, t):
        fr = self.backdrop(t)
        D = self.drop
        C.put(fr, self.head, W / 2, 255, self.q(t, 0.2, 0.8))
        if t < D:
            q0 = self.q(t, 0.3, 0.9)
            self.glass(fr, (90, 420, W - 90, 1300), q0)
            C.put(fr, self.e_h, W / 2, 640 - 20 * (1 - q0), q0)
            C.put(fr, C.text('VS', 'manrope', 44, (255, 255, 255), 800, track=0.4), W / 2, 860, self.q(t, 0.8))
            C.put(fr, self.e_a, W / 2, 1080 + 20 * (1 - self.q(t, 1.2)), self.q(t, 1.2, 0.9))
            C.put(fr, self.names, W / 2, 1240, self.q(t, 1.6))
        else:
            q = self.q(t, D, 0.6)
            self.glass(fr, (90, 340, W - 90, 560), q)
            C.put(fr, C.fit(self.e_h, 150, 150), W / 2 - 300, 450, q)
            C.put(fr, C.fit(self.e_a, 150, 150), W / 2 + 300, 450, q)
            C.put(fr, C.text(self.m['time'], 'manrope', 64, (255, 255, 255), 800), W / 2, 450, q)
            ph = self.pick.height + 140
            self.glass(fr, (90, 600, W - 90, 600 + ph), q)
            C.put(fr, C.text('НАШ ПРОГНОЗ', 'manrope', 28, (230, 232, 240), 700, track=0.45), W / 2, 660, q)
            C.put(fr, self.pick, W / 2, 700 + self.pick.height / 2 + 10 * (1 - q), q)
            y = 600 + ph + 40
            qk = self.q(t, self.t_kef, 0.5)
            self.glass(fr, (90, y, W - 90, y + 200), qk)
            C.put(fr, C.text('КЭФ', 'manrope', 34, (230, 232, 240), 700, track=0.45), 260, y + 100, qk)
            C.put(fr, self.kef, W / 2 + 140, y + 100, qk)
            y += 240
            for i, (f_, t0) in enumerate(((self.facts[0], self.t_f1), (self.facts[1], self.t_f2))):
                qf = self.q(t, t0, 0.6)
                C.put(fr, f_, W / 2, y + f_.height / 2 + 10 * (1 - qf), qf)
                y += f_.height + 34
            if t > self.t_end:
                qe = self.q(t, self.t_end, 0.8)
                fr.alpha_composite(Image.new('RGBA', (W, H), (14, 14, 20, int(200 * qe))))
                self.glass(fr, (190, 700, W - 190, 1000), qe)
                C.put(fr, C.text('JARVIS', 'manrope', 92, (255, 255, 255), 800, track=0.3), W / 2, 810, qe)
                C.put(fr, C.text(C.HANDLE, 'manrope', 42, (230, 232, 240), 600), W / 2, 905, qe)
        return C.grain(fr, t, 3)


# ════════════════════════════ 8. Film ════════════════════════════
class Film(Base):
    def __init__(self, m, **kw):
        super().__init__(m, **kw)
        self.bg = C.vgrad(W, H, [(0, (22, 16, 12)), (0.5, (34, 24, 18)), (1, (14, 10, 8))]).convert('RGBA')
        self.e_h, self.e_a = self.h.emb(560), self.a.emb(560)
        cream = (240, 226, 200)
        self.cream = cream
        self.t1 = C.text(lg_ru(m) + '  ·  ' + m['date'], 'playi', 54, cream, 400)
        self.t2 = C.text(m['time'] + ' по Москве', 'playi', 40, (200, 182, 150), 400)
        self.hn = C.text(self.h.short, 'play', 110, cream, 400, max_w=900)
        self.an = C.text(self.a.short, 'play', 110, cream, 400, max_w=900)
        self.pick = C.lines(m['pick'][0].upper() + m['pick'][1:], 'play', 88, 900, cream, 400, gap=0.1, max_lines=3)
        self.facts = [C.lines(f, 'playi', 52, 900, (230, 214, 186), 400, gap=0.2, max_lines=2) for f in m['facts']]

    def letterbox(self, fr, k=1.0):
        b = int(150 * k)
        fr.alpha_composite(Image.new('RGBA', (W, b), (0, 0, 0, 255)), (0, 0))
        fr.alpha_composite(Image.new('RGBA', (W, b), (0, 0, 0, 255)), (0, H - b))

    def leak(self, fr, t):
        x = (math.sin(t * 0.45) * 0.5 + 0.5) * W
        lk = C.radial(900, 1400, (255, 150, 70), 70, 1.5)
        return C.add_light(fr, lk, x, 500, 0.9)

    def frame(self, t):
        fr = self.bg.copy()
        D = self.drop
        if t < D:
            half = D / 2
            first = t < half
            e = self.e_h if first else self.e_a
            nm = self.hn if first else self.an
            t0 = 0 if first else half
            a = C.seg(t, t0, t0 + 0.9) * (1 - C.seg(t, t0 + half - 0.5, t0 + half))
            z = 1.0 + 0.06 * C.seg(t, t0, t0 + half)
            C.put(fr, C.scale(e, z), W / 2, 780, a)
            C.put(fr, nm, W / 2, 1200, a)
            C.put(fr, self.t1, W / 2, 330, C.seg(t, 0.3, 1.5))
            C.put(fr, self.t2, W / 2, 400, C.seg(t, 0.6, 1.8))
        else:
            a = C.seg(t, D, D + 0.9)
            C.put(fr, C.text('прогноз', 'playi', 50, (200, 182, 150), 400), W / 2, 420, a)
            C.put(fr, self.pick, W / 2, 480 + self.pick.height / 2, a)
            y = 520 + self.pick.height + 70
            ak = C.seg(t, self.t_kef, self.t_kef + 0.9)
            C.put(fr, C.text('коэффициент', 'playi', 44, (200, 182, 150), 400), W / 2, y, ak)
            C.put(fr, C.text(kef_s(self.m['kef']), 'play', 190, self.cream, 400), W / 2, y + 130, ak)
            y += 300
            for i, (f, t0) in enumerate(((self.facts[0], self.t_f1), (self.facts[1], self.t_f2))):
                af = C.seg(t, t0, t0 + 0.9)
                C.put(fr, f, W / 2, y + 30 + f.height / 2, af)
                y += f.height + 60
            if t > self.t_end:
                ae = C.seg(t, self.t_end, self.t_end + 1.0)
                fr.alpha_composite(Image.new('RGBA', (W, H), (10, 7, 5, int(240 * ae))))
                C.put(fr, C.text('Jarvis', 'playi', 130, self.cream, 400), W / 2, 790, ae)
                C.put(fr, C.text(C.HANDLE, 'play', 44, (200, 182, 150), 400), W / 2, 900, ae)
        fr = self.leak(fr, t)
        self.letterbox(fr)
        fr = C.vignette(fr, 0.55)
        return C.grain(fr, t, 9)


# ════════════════════════════ 9. Storm ════════════════════════════
def _bolt(rng, x0, y0, x1, y1, depth=8, spread=0.13):
    """Ломаная молнии: деление отрезков пополам со случайным сдвигом поперёк (мелкая «рваность» на всех масштабах)."""
    pts = [(x0, y0), (x1, y1)]
    for lvl in range(depth):
        new = [pts[0]]
        sp = spread * (0.72 ** lvl)
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            L = math.hypot(bx - ax, by - ay)
            mx, my = (ax + bx) / 2, (ay + by) / 2
            nx, ny = -(by - ay) / (L + 1e-6), (bx - ax) / (L + 1e-6)
            off = rng.normal(0, sp * L * 2)
            new += [(mx + nx * off, my + ny * off), (bx, by)]
        pts = new
    return pts


def _tree(rng, d, x0, y0, x1, y1, level, out):
    """Молния с ветками: ветки короче, тоньше и тусклее; ветка от ветки — ещё слабее."""
    pts = _bolt(rng, x0, y0, x1, y1, depth=7 - level, spread=0.11)
    width, val = (5, 255) if level == 0 else (2, 170) if level == 1 else (1, 80)
    out.append((pts, width, val))
    if level >= 2:
        return
    nb = int(rng.integers(1, 4)) if level == 0 else int(rng.integers(0, 2))
    for _ in range(nb):
        k = int(rng.integers(len(pts) // 8, len(pts) * 4 // 5))
        bx, by = pts[k]
        L = math.hypot(x1 - x0, y1 - y0) * (0.35 if level == 0 else 0.25) * rng.uniform(0.5, 1.2)
        ang = math.atan2(y1 - y0, x1 - x0) + rng.choice([-1, 1]) * rng.uniform(0.35, 0.9)
        _tree(rng, d, bx, by, bx + math.cos(ang) * L, by + math.sin(ang) * L, level + 1, out)


def bolt_layer(seed, x0, x1, y1=1300, y0=-20):
    """Молния как свет (RGB для сложения): тонкое пересвеченное ядро и многослойное свечение — от резкого к широкому,
    ядро белое, ореол холодный сине-фиолетовый, как на фото ночной грозы."""
    rng = np.random.default_rng(seed)
    segs = []
    _tree(rng, None, x0, y0, x1, y1, 0, segs)
    core = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(core)
    for pts, width, val in sorted(segs, key=lambda s: s[2]):
        d.line(pts, fill=val, width=width, joint='curve')
    c = np.asarray(core, np.float32) / 255
    layers = [(c, 1.0), (np.asarray(core.filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255, 1.6),
              (np.asarray(core.filter(ImageFilter.GaussianBlur(7)), np.float32) / 255, 1.4),
              (np.asarray(core.filter(ImageFilter.GaussianBlur(30)), np.float32) / 255, 1.6)]
    cols = [(255, 255, 255), (245, 245, 248), (225, 226, 232), (200, 202, 210)]   # как на ч/б съёмке грозы
    acc = np.zeros((H, W, 3), np.float32)
    for (lay, g), col in zip(layers, cols):
        acc += lay[..., None] * g * np.array(col, np.float32)
    return Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8), 'RGB')


def add_rgb(fr, light, k):
    """Сложить свет: fr (RGBA) + light (RGB) × k."""
    if k <= 0.01:
        return fr
    arr = np.asarray(fr.convert('RGB'), np.float32) + np.asarray(light, np.float32) * k
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')


class Storm(Base):
    """Гроза: ночное небо, облака, косой дождь; молнии бьют на доли до дропа, на дропе — удар через весь кадр
    и белая вспышка; эмблемы на мгновение «высвечиваются» молнией. Мрачно, но читаемо."""

    def __init__(self, m, **kw):
        super().__init__(m, **kw)
        rng = np.random.default_rng(11)
        # облака: шум низкого разрешения, растянутый
        n = np.zeros((H // 8, (W + 400) // 8), np.float32)
        for k in (1, 2, 4):
            g = rng.random((H // (160 // k) + 2, (W + 400) // (160 // k) + 2)).astype(np.float32)
            n += np.asarray(Image.fromarray(g).resize((n.shape[1], n.shape[0]), Image.BICUBIC)) / k
        n = (n - n.min()) / (n.max() - n.min())
        cl = Image.fromarray((n ** 1.6 * 255).astype(np.uint8)).resize((W + 400, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(34))
        self.clouds = cl
        self.sky = C.vgrad(W, H, [(0, (9, 9, 10)), (0.6, (5, 5, 6)), (1, (2, 2, 2))]).convert('RGBA')
        # дождь — три слоя разной скорости
        self.rain = []
        for k, (cnt, ln, al) in enumerate(((260, 46, 60), (180, 70, 90), (90, 110, 120))):
            lay = Image.new('RGBA', (W + 200, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            for _ in range(cnt):
                x, y = rng.uniform(0, W + 200), rng.uniform(0, H)
                d.line((x, y, x - ln * 0.25, y + ln), fill=(190, 205, 230, al), width=1 + k // 2)
            self.rain.append((lay, 900 + 500 * k))
        self.dry = True                      # как в образце владельца (ч/б гроза) — без дождя
        self.bolts = [bolt_layer(s, x0, x1, 720) for s, x0, x1 in ((3, 260, 500), (7, 860, 590), (12, 480, 545), (21, 120, 470), (33, 980, 620))]
        self.big = bolt_layer(99, 560, 520, 1500)
        self.big2 = bolt_layer(55, 120, 900, 1200)
        self.big3 = bolt_layer(77, 1000, 180, 1250)
        self.e_h, self.e_a = self.h.emb(420), self.a.emb(420)
        self.s_h, self.s_a = self.h.emb(200), self.a.emb(200)
        self.head = C.text(head_line(m), 'manrope', 30, (170, 170, 176), 800, track=0.25)
        self.hn = C.text(self.h.up, 'osw', 130, (238, 238, 240), 700, max_w=920)
        self.an = C.text(self.a.up, 'osw', 130, (238, 238, 240), 700, max_w=920)
        self.lab = C.text('ПРОГНОЗ', 'manrope', 32, (170, 170, 176), 800, track=0.6)
        self.pick = C.lines(self.pick_up, 'osw', 110, 920, (242, 242, 244), 700, gap=0.03, max_lines=3)
        self.kef = C.text(kef_s(m['kef']), 'osw', 210, (255, 255, 255), 700)
        self.facts = [C.lines(f.upper(), 'manrope', 38, 900, (210, 210, 214), 700, gap=0.2, max_lines=2) for f in m['facts']]
        # удары: каждые две доли до дропа, на дропе — большой, после — раз в 4 доли
        u, D = self.u, self.drop
        self.hits = [(D - k * 2 * u, k % len(self.bolts)) for k in range(1, int(D / (2 * u)) + 1)]
        self.hits += [(D + k * 4 * u, (k + 2) % len(self.bolts)) for k in range(1, int((self.dur - D) / (4 * u)))]

    def flash(self, t):
        """Сила текущей вспышки и номер молнии (−1 — большая на дропе)."""
        best = (0.0, None)
        for t0, i in [(self.drop, -1)] + self.hits:
            dt = t - t0
            if 0 <= dt < 0.45:
                k = math.exp(-dt * 6) * (0.55 + 0.45 * abs(math.cos(dt * 38)))   # 2–3 вспышки подряд
                if k > best[0]:
                    best = (k, i)
        return best

    def frame(self, t):
        D = self.drop
        fr = self.sky.copy()
        k, bi = self.flash(t)
        # облака подсвечены вспышкой
        off = int((t * 18) % 400)
        cl = self.clouds.crop((off, 0, off + W, H))
        cl_a = cl.point(lambda v: int(min(255, v * (0.17 + 0.85 * k))))
        fr.alpha_composite(Image.merge('RGBA', (Image.new('L', (W, H), 150), Image.new('L', (W, H), 150),
                                                Image.new('L', (W, H), 156), cl_a)))
        if bi is not None and k > 0.05:
            bl = [self.big] if bi == -1 else [self.bolts[bi]]
            for b in bl:
                fr = add_rgb(fr, b, min(1.2, k * 1.3))
        for lay, sp in ([] if self.dry else self.rain):
            y = int((t * sp) % H)
            x = int((t * sp * 0.25) % 200)
            part = lay.crop((x, 0, x + W, H))
            fr.alpha_composite(part, (0, y - H))
            fr.alpha_composite(part, (0, y))
        if t < D:
            half = D / 2
            first = t < half
            e, nm = (self.e_h, self.hn) if first else (self.e_a, self.an)
            t0 = 0 if first else half
            a = C.seg(t, t0 + 0.1, t0 + 0.6) * (1 - C.seg(t, t0 + half - 0.25, t0 + half))
            lit = 0.22 + 0.78 * min(1.0, k * 1.4)
            em = C.scale(e, 1 + 0.06 * k)
            if k > 0.15:
                em = C.glow(em, 26, 1.2 * k, (225, 228, 236))
            C.put(fr, C.with_shadow(em, 30, 0.7, 20) if k <= 0.15 else em, W / 2, 800, a * lit)
            C.put(fr, nm, W / 2, 1180, a)
            C.put(fr, self.head, W / 2, 262, C.seg(t, 0.2, 0.9))
        else:
            q = self.q(t, D + 0.05, 0.5)
            C.put(fr, self.s_h, W / 2 - 230, 430, q)
            C.put(fr, self.s_a, W / 2 + 230, 430, q)
            C.put(fr, C.text('VS', 'osw', 56, (170, 170, 176), 600, track=0.2), W / 2, 430, q)
            C.put(fr, self.lab, W / 2, 610, self.q(t, D + 0.1))
            qp = self.q(t, D + 0.15, 0.5)
            pg = self.pick if k < 0.1 else C.glow(self.pick, 14, 0.9 * k, (220, 222, 230))
            C.put(fr, pg, W / 2, 650 + self.pick.height / 2 + 30 * (1 - qp), qp)
            y = 680 + self.pick.height + 40
            qk = self.q(t, self.t_kef, 0.4)
            C.put(fr, C.text('КЭФ', 'manrope', 30, (170, 170, 176), 800, track=0.6), W / 2, y, qk)
            C.put(fr, C.glow(self.kef, 16, 0.6, (220, 222, 230)), W / 2, y + 125, qk)
            y += 270
            for i, (f_, t0) in enumerate(((self.facts[0], self.t_f1), (self.facts[1], self.t_f2))):
                qf = self.q(t, t0, 0.45)
                C.put(fr, f_, W / 2, y + f_.height / 2 + 20 * (1 - qf), qf)
                y += f_.height + 40
            C.put(fr, self.head, W / 2, 262)
            if t > self.t_end:
                qe = self.q(t, self.t_end, 0.6)
                fr.alpha_composite(Image.new('RGBA', (W, H), (5, 7, 12, int(225 * qe))))
                C.put(fr, C.glow(C.text('JARVIS', 'osw', 130, (242, 242, 244), 700, track=0.2), 18, 0.7, (220, 222, 230)), W / 2, 800, qe)
                C.put(fr, C.text(C.HANDLE, 'manrope', 44, (200, 200, 205), 800), W / 2, 920, qe)
        # белая вспышка на дропе и лёгкая на каждом ударе
        wf = max(0.0, 1 - abs(t - D) / 0.14) if t >= D - 0.02 else 0
        wf = max(wf, 0.25 * k if bi != -1 else 0)
        if wf > 0:
            fr.alpha_composite(Image.new('RGBA', (W, H), (235, 235, 238, int(150 * wf))))
        dx, dy = C.shake(t, D, 26, 0.5)
        fr = C.zoom(fr, 1.02, dx=dx, dy=dy)
        return C.grain(C.vignette(fr, 0.55), t, 6)


STYLES = {'editorial': Editorial, 'spotlight': Spotlight, 'broadcast': Broadcast, 'split': Split,
          'card': Card, 'kinetic': Kinetic, 'glass': Glass, 'film': Film, 'storm': Storm}
