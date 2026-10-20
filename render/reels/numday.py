# -*- coding: utf-8 -*-
"""«Цифра дня» — ролик открывается одной сильной цифрой из сезона (владелец 20.10: формат «тренд-цифра как крючок»).

Цифра настоящая (team/reels_daily/pick.py fact): как часто ставка прогноза заходила в матчах сезона у одной из команд
(хозяева — их глазами, гости — глазами соперника, как в «Что заходит»; берётся команда с большей долей). В ролик
приходят team, side, k, n и games — [(заход, счёт, дома)] по порядку.

Сцены (u — доля трека, D — дроп; доли от дропа; num / pre / hold / cta — параметры):
  интро (до D − num − pre) — жёлтая плашка «ЦИФРА ДНЯ», лига и время МСК, две эмблемы матча;
  цифра (num долей) — крупно «7 ИЗ 9» (числитель набегает), сверху «ЭТОТ ПРОГНОЗ ЗАХОДИЛ», снизу «В МАТЧАХ <КЛУБА>
             В СЕЗОНЕ»; ниже сетка матчей сезона (до 20 последних): на каждую половину доли открывается плашка — счёт,
             дома / в гостях, зелёная — зашло, серая — нет;
  вопрос (pre долей) — «А СЕГОДНЯ?» на всю ширину, камера наезжает;
  ДРОП (hold долей) — вспышка, эмблема команды прогноза (обе — если прогноз на матч целиком), прогноз крупно, кэф,
             доля сезона в процентах;
  финал (cta долей) — плашка Telegram (C.tg_plate).
"""
import math

from PIL import Image, ImageDraw

from reels import core as C
from reels import form as F
from reels.core import W, H

BG = (12, 12, 14)
YEL = (255, 210, 40)
INK = (14, 14, 16)
WHITE = (246, 246, 242)
GRAY = (150, 150, 156)
OKC = (52, 210, 120)
NOC = (58, 58, 64)
TOP_Y, HY = 268, 1440
COLS, CW, CH, GAP = 5, 176, 96, 14


def gen(t):
    return C.gen_case(t.short, 'g').upper()


class NumDay(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=1.0, drop=12.0, line=None, fact=None, num=6, pre=2,
                 hold=6, cta=2.5, seed=43, **kw):
        super().__init__(u, drop, seed)
        if not fact or not fact.get('n'):
            raise ValueError('нет цифры для шаблона «Цифра дня»')
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.pick = F.lg_ru(league), when, coef, pick
        self.k, self.n = int(fact['k']), int(fact['n'])
        self.team = self.h if fact.get('side') == 'h' else self.a
        self.games = list(fact.get('games') or [])[-20:]
        self.side = F.pick_team(self.h, self.a, pick)
        self.t1 = self.b(-(num + pre))
        self.tp = self.b(-pre)
        if self.t1 < 1.5:
            raise ValueError('мало времени до дропа')
        self.t_cta = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = self.t1 + 2 * u
        self._prep()

    def _prep(self):
        bg = Image.new('RGBA', (W, H), BG + (255,))
        d = ImageDraw.Draw(bg)
        for x in range(-H, W, 46):                                # косая фактура
            d.line((x, 0, x + H, H), fill=(18, 18, 21, 255), width=10)
        self.bg = C.add_light(bg, C.radial(1300, 1300, C.mix(self.team.c1, YEL, 0.3), 70, 2.0), W / 2, 760, 0.8)
        self.chip = C.rrect(420, 92, 18, YEL, 255)
        C.put(self.chip, C.text('ЦИФРА ДНЯ', 'unb', 48, INK, 900), 210, 46)
        self.tag = C.text('%s · %s' % (self.league, self.when.upper()), 'robc', 36, GRAY, 700, track=0.1)
        self.emb = {k: C.with_shadow(t.emb(250)) for k, t in (('h', self.h), ('a', self.a))}
        self.name = {k: C.text(t.up, 'robci', 54, WHITE, 900, max_w=440) for k, t in (('h', self.h), ('a', self.a))}
        self.l_top = C.text('ЭТОТ ПРОГНОЗ ЗАХОДИЛ', 'robc', 50, WHITE, 800, track=0.06)
        self.l_bot = C.lines('В МАТЧАХ %s В СЕЗОНЕ' % gen(self.team), 'robc', 50, W - 120, WHITE, 800, max_lines=2)
        self.nums = {i: C.text(str(i), 'unb', 250, YEL, 900) for i in range(0, self.k + 1)}
        self.of = C.text('ИЗ %d' % self.n, 'unb', 120, WHITE, 900)
        self.what = C.lines(self.pick.upper(), 'robc', 40, W - 160, GRAY, 800, max_lines=2)
        self.cells = []
        for ok, score, home in self.games:
            c = C.rrect(CW, CH, 16, OKC if ok else NOC, 255)
            C.put(c, C.text(score, 'robci', 44, INK if ok else (200, 200, 206), 900, max_w=CW - 16), CW / 2, CH * 0.42)
            C.put(c, C.text('ДОМА' if home else 'В ГОСТЯХ', 'robc', 20, INK if ok else GRAY, 800, track=0.1), CW / 2,
                  CH * 0.8)
            c.alpha_composite(C.icon('check-circle' if ok else 'x-circle', 26, INK if ok else GRAY, 'fill'), (CW - 32, 6))
            self.cells.append(c)
        self.q = C.text('А СЕГОДНЯ?', 'unb', 130, YEL, 900, max_w=W - 80)
        p1, p2 = F.split_pick(self.pick)
        head, main = F.head_main(p1)
        self.p_head = C.text(head, 'robci', 56, GRAY, 900, max_w=W - 120) if head else None
        self.p_main = C.lines(main, 'robci', 100, W - 100, WHITE, 900, max_lines=2)
        self.p_tail = C.text(p2, 'robc', 40, GRAY, 800, track=0.12) if p2 else None
        self.kef = C.rrect(360, 112, 56, YEL, 255)
        C.put(self.kef, C.text('КЭФ ' + C.fmt_k(self.coef).replace('.', ','), 'unb', 50, INK, 900), 180, 56)
        self.pct = C.text('в сезоне: %d из %d матчей %s' % (self.k, self.n, C.gen_case(self.team.short, 'g')), 'robc', 38,
                          GRAY, 700)
        if self.side:
            self.p_emb = C.with_shadow((self.h if self.side == 'h' else self.a).emb(300))
        else:
            pair = Image.new('RGBA', (560, 260), (0, 0, 0, 0))
            C.put(pair, self.h.emb(240), 140, 130)
            C.put(pair, self.a.emb(240), 420, 130)
            self.p_emb = C.with_shadow(pair)
        self.tg = C.tg_plate()
        self.handle = C.text(C.HANDLE, 'mont', 40, (210, 210, 214), 800)

    # ── сцены ──
    def intro(self, fr, t):
        q = C.out_back(C.seg(t, 0.1, 0.45), 1.6)
        C.put(fr, C.scale(self.chip, 0.7 + 0.3 * q), W / 2, 450, min(1.0, q * 1.5))
        C.put(fr, self.tag, W / 2, 550, C.out_expo(C.seg(t, 0.3, 0.6)))
        for side, x in (('h', 280), ('a', W - 280)):
            dl = 0.15 if side == 'a' else 0.0
            qe = C.out_back(C.seg(t, 0.4 + dl, 0.8 + dl), 1.5)
            C.put(fr, C.scale(self.emb[side], 0.6 + 0.4 * qe), x, 840, min(1.0, qe * 1.4))
            C.put(fr, self.name[side], x, 1020, qe)
        C.put(fr, self.what, W / 2, 1180, C.out_expo(C.seg(t, 0.9, 1.3)))

    def number(self, fr, t):
        u = self.u
        C.put(fr, C.scale(self.chip, 0.6), W / 2, 330, 1.0)
        q = C.out_expo(C.seg(t, self.t1, self.t1 + 0.3))
        C.put(fr, self.l_top, W / 2, 500, q)
        kq = C.seg(t, self.t1 + 0.1, self.t1 + 2 * u)
        cur = int(round(self.k * C.out_cubic(kq)))
        bp = math.exp(-(((t - self.t1) / u) % 1.0) * 6)
        num = self.nums[cur]
        gap = 30
        wn, wo = num.size[0], self.of.size[0]
        x0 = W / 2 - (wn + gap + wo) / 2
        C.put(fr, C.scale(num, 1 + 0.03 * bp), x0 + wn / 2, 700, q)
        C.put(fr, self.of, x0 + wn + gap + wo / 2, 740, C.out_expo(C.seg(t, self.t1 + 0.4, self.t1 + 0.8)))
        C.put(fr, self.l_bot, W / 2, 900, C.out_expo(C.seg(t, self.t1 + 0.6, self.t1 + 1.0)))
        # сетка матчей: по плашке на половину доли
        n = len(self.cells)
        rows = (n + COLS - 1) // COLS
        gw = COLS * CW + (COLS - 1) * GAP
        y0 = 1010
        step = max(0.12, (self.tp - (self.t1 + u) - 0.3) / max(1, n))
        for i, c in enumerate(self.cells):
            ti = self.t1 + u + i * min(step, 0.5 * u)
            qc = C.out_back(C.seg(t, ti, ti + 0.25), 1.8)
            if qc <= 0.01:
                continue
            r, col = divmod(i, COLS)
            last = r == rows - 1 and n % COLS
            off = (COLS - n % COLS) * (CW + GAP) / 2 if last else 0
            x = W / 2 - gw / 2 + off + col * (CW + GAP) + CW / 2
            y = y0 + r * (CH + GAP) + CH / 2
            C.put(fr, C.scale(c, 0.6 + 0.4 * qc), x, y, min(1.0, qc * 1.5))

    def question(self, fr, t):
        q = C.out_back(C.seg(t, self.tp, self.tp + 0.3), 1.6)
        C.put(fr, C.scale(self.q, 0.7 + 0.3 * q), W / 2, 760, min(1.0, q * 1.5))

    def pick_scene(self, fr, t):
        D, u = self.drop, self.u
        kc = C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.4))
        bp = math.exp(-(((t - D) / u) % 1.0) * 6) if t < self.t_cta else 0.0
        qe = C.out_back(C.seg(t, D, D + 0.35), 1.6)
        C.put(fr, C.scale(self.p_emb, (0.6 + 0.4 * qe) * (1 + 0.03 * bp) * (1 - 0.3 * kc)), W / 2, C.lerp(560, 450, kc),
              min(1.0, qe * 1.5))
        y = C.lerp(800, 660, kc)
        qp = C.out_expo(C.seg(t, D + 0.1, D + 0.4))
        if self.p_head is not None:
            C.put(fr, self.p_head, W / 2, y, qp)
            y += 90
        C.put(fr, self.p_main, W / 2 - 220 * (1 - qp), y + self.p_main.size[1] / 2 - 40, qp)
        y += self.p_main.size[1] + 20
        if self.p_tail is not None:
            C.put(fr, self.p_tail, W / 2, y, qp)
            y += 70
        qk = C.out_back(C.seg(t, D + u, D + u + 0.3), 1.7)
        C.put(fr, C.scale(self.kef, 0.6 + 0.4 * qk), W / 2, y + 60, min(1.0, qk * 1.5) * (1 - kc))
        C.put(fr, self.pct, W / 2, y + 170, C.out_expo(C.seg(t, D + 2 * u, D + 2 * u + 0.3)) * (1 - kc))

    def frame(self, t):
        D = self.drop
        fr = self.bg.copy()
        if t < self.t1:
            self.intro(fr, t)
        elif t < self.tp:
            self.number(fr, t)
        elif t < D:
            self.question(fr, t)
        else:
            self.pick_scene(fr, t)
        z, dx, dy = 1.0, 0.0, 0.0
        if self.tp <= t < D:
            z += 0.06 * C.in_cubic(C.seg(t, self.tp, D))
        if t >= D:
            kk = 1 - C.seg(t, D, D + 0.45)
            z += 0.06 * kk ** 2
            dx, dy = C.shake(t, D, 22, 0.4)
        if t >= self.t1:
            z += 0.025 * (1 - C.seg(t, self.t1, self.t1 + 0.3)) ** 2
        fr = C.zoom(fr.convert('RGB'), z, dx=dx, dy=dy)
        if D <= t < D + 0.24:
            fa = 1.0 if t < D + 1 / 30 else (1 - C.seg(t, D + 1 / 30, D + 0.24)) ** 1.6
            fr = Image.blend(fr, Image.new('RGB', fr.size, (255, 236, 150)), 0.65 * fa)
        fr = C.vignette(fr, 0.35).convert('RGBA')
        C.put(fr, self.handle, W / 2, HY, C.seg(t, 0.2, 0.45) * C.HANDLE_BOTTOM)
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.24, self.t_cta + 0.6))
            C.put(fr, self.tg, W / 2, 1316 + 60 * (1 - q), q)
        return C.grain(fr, t, 4)
