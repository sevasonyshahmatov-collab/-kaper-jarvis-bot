# -*- coding: utf-8 -*-
"""«10 000 симуляций» — модель разыгрывает матч 10 000 раз (владелец 20.10: формат «ИИ / модель прогнала матч N раз»).

Симуляция настоящая (team/reels_daily/pick.py simulate): счёт по модели таблицы (Пуассон, ничьи подогнаны под лигу),
ставка прогноза проверяется в каждом розыгрыше. В ролик приходят n, hits, curve (доля заходов после каждой сотни) и top
(три самых частых счёта).

Сцены (u — доля трека, D — дроп; доли от дропа; intro / hold / cta — параметры):
  интро (до D − intro долей) — тёмный экран аналитика: сверху лига и время МСК, две эмблемы с именами,
             заголовок «МОДЕЛЬ РАЗЫГРЫВАЕТ МАТЧ 10 000 РАЗ», под ним строка прогноза (что проверяем);
  розыгрыш (intro долей) — поле 100×100 точек заполняется построчно с ускорением: зелёная — прогноз зашёл, тёмная —
             нет; сбоку бежит счётчик «4 812 / 10 000» и живой процент заходов (по настоящей кривой); на каждую долю —
             вспышка строки;
  ДРОП (hold долей) — поле сжимается вверх, крупно итоговый процент и «в 6 212 из 10 000 розыгрышей», ниже — прогноз
             и кэф, внизу — самый частый счёт;
  финал (cta долей) — плашка Telegram (C.tg_plate).
Кадр — функция t; поле точек — numpy-маска по порядку заполнения (быстро), всё остальное кешируется в конструкторе.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from reels import core as C
from reels import form as F
from reels.core import W, H

BG = (5, 10, 16)
INK = (8, 14, 22)
HIT = (64, 232, 140)
MISS = (58, 34, 44)
WHITE = (240, 246, 252)
GRAY = (140, 156, 176)
ACC = (255, 214, 92)
GN, CELL = 100, 7                # поле 100×100, клетка 7 px (точка 5 px)
GRID = GN * CELL                 # 700 px
GY = 820                         # центр поля на розыгрыше
TOP_Y, HY = 268, 1440


def fmt_int(n):
    return '{:,}'.format(int(n)).replace(',', ' ')


def _lottie(name, loop=False):
    try:
        return C.Lottie(name, loop)
    except Exception as e:  # noqa: BLE001  (нет rlottie — без анимации)
        print('lottie %s: %r' % (name, e), flush=True)
        return None


class Simulate(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=1.0, drop=12.0, line=None, sim=None, intro=8,
                 hold=6, cta=2.5, seed=41, **kw):
        super().__init__(u, drop, seed)
        if not sim or not sim.get('n'):
            raise ValueError('нет симуляции для шаблона «10 000 симуляций»')
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.pick = F.lg_ru(league), when, coef, pick
        self.sim = sim
        self.n, self.hits = int(sim['n']), int(sim['hits'])
        self.curve = [0.0] + list(sim.get('curve') or [])
        self.side = F.pick_team(self.h, self.a, pick)
        self.ts = self.b(-intro)                      # начало розыгрыша
        if self.ts < 2.0:
            raise ValueError('мало времени до дропа')
        self.t_cta = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = self.drop + 1.2 * u
        self._prep(seed)

    # ── заготовки ──
    def _prep(self, seed):
        bg = Image.new('RGBA', (W, H), BG + (255,))
        d = ImageDraw.Draw(bg)
        for y in range(0, H, 6):                                  # строки экрана
            d.line((0, y, W, y), fill=(9, 16, 24, 255))
        col = {k: C.mix(t.c1, (255, 255, 255), 0.15) for k, t in (('h', self.h), ('a', self.a))}
        bg = C.add_light(bg, C.radial(1100, 1100, col['h'], 90, 2.2), 120, 420, 0.8)
        bg = C.add_light(bg, C.radial(1100, 1100, col['a'], 90, 2.2), W - 120, 420, 0.8)
        bg = C.add_light(bg, C.radial(1500, 1500, (20, 90, 70), 120, 2.0), W / 2, GY, 0.7)
        self.bg = bg
        # поле: порядок заполнения — построчно, цвет — по настоящему исходу (доля зелёных = hits / n)
        rng = np.random.default_rng(seed)
        ok = np.zeros(GN * GN, bool)
        ok[:self.hits] = True
        rng.shuffle(ok)
        rgb = np.zeros((GRID, GRID, 3), np.uint8)
        rank = np.full((GRID, GRID), 10 ** 6, np.int32)
        for idx in range(GN * GN):
            r, c = divmod(idx, GN)
            y0, x0 = r * CELL + 1, c * CELL + 1
            rgb[y0:y0 + 5, x0:x0 + 5] = HIT if ok[idx] else MISS
            rank[y0:y0 + 5, x0:x0 + 5] = idx
        self.g_rgb, self.g_rank = rgb, rank
        self.g_full = self._grid_img(GN * GN)
        self.g_empty = self._grid_img(0)
        # шапка и команды
        self.tag = C.text('%s · %s' % (self.league, self.when.upper()), 'mono', 34, GRAY, 700, track=0.08)
        self.emb = {k: C.with_shadow(t.emb(230)) for k, t in (('h', self.h), ('a', self.a))}
        self.name = {k: C.text(t.up, 'robci', 56, WHITE, 900, max_w=440) for k, t in (('h', self.h), ('a', self.a))}
        self.vs = C.text('—', 'robc', 70, GRAY, 700)
        self.title = C.lines('МОДЕЛЬ РАЗЫГРЫВАЕТ МАТЧ 10 000 РАЗ', 'unb', 58, W - 140, WHITE, 800, max_lines=2)
        p1, p2 = F.split_pick(self.pick)
        self.what = C.lines('ПРОВЕРЯЕМ: ' + p1 + (' ' + p2 if p2 else ''), 'robc', 40, W - 460, ACC, 800,
                            max_lines=2)
        self.lab_n = C.icon_text('dice-five', C.text('РОЗЫГРЫШЕЙ', 'mono', 28, GRAY, 700, track=0.1), 34, GRAY, 10)
        self.lab_p = C.icon_text('target', C.text('ПРОГНОЗ ЗАШЁЛ', 'mono', 28, GRAY, 700, track=0.1), 34, HIT, 10)
        self.lab_go = C.icon_text('cpu', C.text('ЗАПУСК', 'mono', 40, HIT, 800, track=0.2), 52, HIT, 14)
        # дроп
        pct = round(100 * self.hits / self.n)
        self.big = C.glow(C.text('%d%%' % pct, 'unb', 260, HIT, 900), 26, 1.2, HIT)
        self.sub = C.text('в %s из %s розыгрышей' % (fmt_int(self.hits), fmt_int(self.n)), 'robc', 46, WHITE, 700)
        head, main = F.head_main(p1)
        self.p_head = C.text(head, 'robci', 54, GRAY, 900, max_w=W - 120) if head else None
        self.p_main = C.lines(main, 'robci', 92, W - 110, WHITE, 900, max_lines=2)
        self.p_tail = C.text(p2, 'robc', 40, GRAY, 800, track=0.12) if p2 else None
        self.kef = C.rrect(360, 112, 56, ACC, 255)
        C.put(self.kef, C.text('КЭФ ' + C.fmt_k(self.coef).replace('.', ','), 'unb', 50, INK, 900), 180, 56)
        top = (self.sim.get('top') or [None])[0]
        self.score = C.text('чаще всего: %d:%d' % (top[0], top[1]), 'robc', 40, GRAY, 700) if top else None
        self.tg = C.tg_plate()
        self.target = _lottie('target')                              # стрела в мишень LottieFiles на дропе
        self.handle = C.text(C.HANDLE, 'mont', 40, (200, 214, 230), 800)
        self.flash = Image.new('RGBA', (GRID, CELL), (255, 255, 255, 120))

    def _grid_img(self, k):
        a = ((self.g_rank < k) * 255).astype(np.uint8)
        dim = (self.g_rank < 10 ** 6) * 26                       # пустые клетки — едва видны
        a = np.maximum(a, dim.astype(np.uint8))
        rgb = np.where((self.g_rank < k)[..., None], self.g_rgb, np.uint8(60))
        return Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), 'RGBA')

    # ── сцены ──
    def filled(self, t):
        """Сколько розыгрышей показано к моменту t: ускоряющееся заполнение к дропу."""
        x = C.seg(t, self.ts, self.drop - 0.15)
        return int(self.n * (x ** 2.2))

    def head(self, fr, t, k):
        q = C.out_expo(C.seg(t, 0.1, 0.5))
        C.put(fr, self.tag, W / 2, TOP_Y, q * k)
        for side, x in (('h', 250), ('a', W - 250)):
            qe = C.out_back(C.seg(t, 0.2 + (0.15 if side == 'a' else 0), 0.7 + (0.15 if side == 'a' else 0)), 1.5)
            C.put(fr, C.scale(self.emb[side], 0.6 + 0.4 * qe), x, 470, min(1.0, qe * 1.4) * k)
            C.put(fr, self.name[side], x, 640, qe * k)
        C.put(fr, self.vs, W / 2, 480, q * k)

    def intro(self, fr, t):
        self.head(fr, t, 1.0)
        q = C.out_expo(C.seg(t, 0.6, 1.1))
        C.put(fr, self.title, W / 2, 850 + 40 * (1 - q), q)
        q2 = C.out_expo(C.seg(t, 1.2, 1.6))
        C.put(fr, self.what, W / 2, 1060, q2)
        q3 = C.out_expo(C.seg(t, 1.8, 2.2))
        C.put(fr, self.lab_go, W / 2, 1230, q3 * (0.6 + 0.4 * abs(math.sin(t * 4))))

    def play(self, fr, t):
        k = self.filled(t)
        kq = C.in_out(C.seg(t, self.ts, self.ts + 0.4))
        C.put(fr, self.tag, W / 2, TOP_Y, 1.0)
        for side, x in (('h', 95), ('a', W - 95)):
            C.put(fr, C.scale(self.emb[side], 1 - 0.55 * kq), C.lerp(250 if side == 'h' else W - 250, x, kq),
                  C.lerp(470, 370, kq), 1.0)
        C.put(fr, self.what, W / 2, 370, kq)
        grid = self._grid_img(k)
        C.put(fr, grid, W / 2, GY, min(1.0, kq * 1.5))
        # вспышка строки на долях
        for n in range(-12, 0):
            tb = self.b(n)
            age = t - tb
            if tb >= self.ts and 0 <= age < 0.25:
                row = (k // GN) % GN
                C.put(fr, self.flash, W / 2, GY - GRID / 2 + row * CELL + CELL / 2, 1 - age / 0.25)
        # счётчики
        cur = self.curve[min(len(self.curve) - 1, k // 100)] if k >= 100 else (self.hits / self.n if k else 0.0)
        y = GY + GRID / 2 + 70
        C.put(fr, self.lab_n, 290, y)
        C.put(fr, C.text('%s' % fmt_int(k), 'mono', 64, WHITE, 800), 290, y + 60)
        C.put(fr, self.lab_p, W - 290, y)
        C.put(fr, C.text('%d%%' % round(100 * cur), 'mono', 64, HIT, 800), W - 290, y + 60)

    def pick_scene(self, fr, t):
        D, u = self.drop, self.u
        kc = C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.4))
        # поле уходит вверх и уменьшается
        qg = C.in_out(C.seg(t, D, D + 0.5))
        C.put(fr, C.scale(self.g_full, 1 - 0.55 * qg), W / 2, C.lerp(GY, 360, qg), 1 - 0.55 * qg)
        bp = math.exp(-(((t - D) / u) % 1.0) * 6) if t < self.t_cta else 0.0
        qb = C.out_back(C.seg(t, D + 0.1, D + 0.45), 1.6)
        C.put(fr, C.scale(self.big, (0.5 + 0.5 * qb) * (1 + 0.02 * bp) * (1 - 0.3 * kc)), W / 2, C.lerp(640, 560, kc),
              min(1.0, qb * 1.5))
        C.put(fr, self.sub, W / 2, C.lerp(800, 690, kc), C.out_expo(C.seg(t, D + 0.4, D + 0.7)))
        if self.target:
            C.put(fr, self.target.frame(t - D - 0.2, 150), min(W - 92, W / 2 + self.big.width / 2 + 40), C.lerp(560, 480, kc),
                  min(1.0, qb * 1.5) * (1 - kc))
        y0 = C.lerp(930, 800, kc)
        qp = C.out_expo(C.seg(t, D + u, D + u + 0.35))
        if self.p_head is not None:
            C.put(fr, self.p_head, W / 2, y0, qp)
            y0 += 90
        C.put(fr, self.p_main, W / 2 + 200 * (1 - qp), y0 + self.p_main.size[1] / 2 - 40, qp)
        y1 = y0 + self.p_main.size[1] + 20
        if self.p_tail is not None:
            C.put(fr, self.p_tail, W / 2, y1, qp)
            y1 += 70
        qk = C.out_back(C.seg(t, D + 2 * u, D + 2 * u + 0.3), 1.7)
        C.put(fr, C.scale(self.kef, 0.6 + 0.4 * qk), W / 2, y1 + 60, min(1.0, qk * 1.5) * (1 - kc))
        if self.score is not None:
            C.put(fr, self.score, W / 2, y1 + 170, C.out_expo(C.seg(t, D + 3 * u, D + 3 * u + 0.3)) * (1 - kc))

    def frame(self, t):
        D = self.drop
        fr = self.bg.copy()
        if t < self.ts:
            self.intro(fr, t)
        elif t < D:
            self.play(fr, t)
        else:
            self.pick_scene(fr, t)
        z, dx, dy = 1.0, 0.0, 0.0
        if t >= D:
            kk = 1 - C.seg(t, D, D + 0.45)
            z += 0.06 * kk ** 2
            sx, sy = C.shake(t, D, 20, 0.4)
            dx, dy = sx, sy
        elif t >= self.ts:
            z += 0.03 * C.seg(t, self.ts, D)
        fr = C.zoom(fr.convert('RGB'), z, dx=dx, dy=dy)
        if D <= t < D + 0.24:
            fa = 1.0 if t < D + 1 / 30 else (1 - C.seg(t, D + 1 / 30, D + 0.24)) ** 1.6
            fr = Image.blend(fr, Image.new('RGB', fr.size, (220, 255, 236)), 0.65 * fa)
        fr = C.vignette(fr, 0.4).convert('RGBA')
        C.put(fr, self.handle, W / 2, HY, C.seg(t, 0.2, 0.45) * C.HANDLE_BOTTOM)
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.24, self.t_cta + 0.6))
            C.put(fr, self.tg, W / 2, 1316 + 60 * (1 - q), q)
        return C.grain(fr, t, 4)
