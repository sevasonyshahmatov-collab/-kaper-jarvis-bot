# -*- coding: utf-8 -*-
"""Терминал — интерфейс ИИ-ассистента: матч, факты команд и прогноз (без заголовков-рубрик и служебных фраз).

Сверху — HUD: вращающиеся кольца «реактора», матч, лига и время МСК. Ниже — окно терминала: по строке на долю
печатаются факты первой команды (последние 3 игры, очки, место, шайбы), потом второй — команда на экране 6–8 с;
перед дропом — свёрнутые итоги и обе эмблемы, на дропе экран рвёт глитчем и проявляется «ПРОГНОЗ: …» с кэфом
(держим hold долей). В конце — Telegram (cta долей).
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from reels import core as C
from reels import form as F
from reels import fresh
from reels.core import W, H

CY = (40, 220, 255)
CYD = (20, 110, 140)
TXT = (226, 240, 248)
GOLD = (255, 214, 90)
DIM = (110, 140, 160)
BG = (3, 8, 15)
FS = 52                       # кегль терминала
LH = 70                       # строка (было 76: у второй команды «шайбы» упирались в «ФОРМА», 19.10)
PX, PY = 46, 556              # окно терминала
PW, PH = W - 2 * PX, 1400 - 556
TX, TY = PX + 36, PY + 100    # первая строка текста
GLYPHS = 'АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЭЮЯ0123456789#%&@$'


class Jarvis(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=1.0, drop=19.0, team=7, pre=2, hold=4.5, cta=2.5,
                 seed=19, rs=0.5, line=None):
        super().__init__(u, drop, seed)
        self.rs, self.line = rs, line          # шаг строк терминала (долей трека); линия П1 / Х / П2
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.pick = league, when, coef, pick
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
        self.sh, self.sa = F.norm(sh), F.norm(sa)
        self.adv = C.font('mono', FS, 600).getlength('0')
        self.cols = int((PW - 72) / self.adv)
        self.t1, self.t2, self.t_calc = self.b(-(2 * team + pre)), self.b(-(team + pre)), self.b(-pre)
        if self.t1 < 1.5:
            raise ValueError('мало времени до дропа')
        self.block = {'h': self._team(self.h, self.sh, self.t1), 'a': self._team(self.a, self.sa, self.t2)}
        self.summ = {'h': self._summary(self.h, self.sh, self.t2), 'a': self._summary(self.a, self.sa, self.t_calc)}
        self.t_cta = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = self.b(3)
        self._prep()

    def _team(self, team, s, t0):
        """Строки анализа клуба: [(время начала печати, сегменты, эмблема|None)]."""
        u = self.u
        col = fresh.bright(fresh.club(team), 0.45)
        out = [(t0, [('> ', CY), (team.up, col)], team)]
        g = s['games']
        for k, x in enumerate(g):
            sc = x['score'] + (' ' + x['note'] if x['note'] else '')
            seg = [('  ' + (x['date'] + ' ' if x['date'] else ''), DIM), (x['res'] + ' ', F.res_col(x['res'])),
                   ('%-6s ' % sc, TXT), (x['opp'], TXT)]
            if sum(len(a) for a, _ in seg) > self.cols:               # длинное имя соперника — без даты
                seg[0] = ('  ', DIM)
            out.append((t0 + (1.0 + self.rs * k) * u, seg, None))       # строки — на доли трека (шаг rs)
        tl = t0 + (1.0 + self.rs * len(g)) * u
        if s['points'] is not None:
            tail = (' за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей'))) if s['gp'] is not None else ''
            out.append((tl, [('  очки: ', DIM), ('%d' % s['points'], GOLD), (tail, DIM)], None))
            tl += self.rs * u
        if s['place'] is not None:
            out.append((tl, [('  место: ', DIM), ('%d' % s['place'], GOLD), ((' ' + s['place_scope']) if s['place_scope'] else '', DIM)], None))
            tl += self.rs * u
        if s['gd'] is not None:
            out.append((tl, [('  шайбы: ', DIM), (F.gd_txt(s['gd']), GOLD)], None))
        return out

    def _summary(self, team, s, t0):
        """Свёрнутый анализ: «> БАФФАЛО  П В П · 2 очка»."""
        col = fresh.bright(fresh.club(team), 0.45)
        seg = [('> ', CY), (team.up + '  ', col)]
        for x in s['games']:
            seg.append((x['res'] + ' ', F.res_col(x['res'])))
        if s['points'] is not None:
            seg.append(('· %d %s' % (s['points'], plural(s['points'], 'очко', 'очка', 'очков')), GOLD))
        return (t0, seg, team)

    # ── заготовки ──
    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        bg = C.vgrad(W, H, [(0, (6, 16, 28)), (0.5, BG), (1, (1, 3, 6))]).convert('RGBA')
        d = ImageDraw.Draw(bg)
        for x in range(0, W, 54):
            d.line((x, 0, x, H), fill=(10, 26, 40, 255), width=1)
        for y in range(0, H, 54):
            d.line((0, y, W, y), fill=(10, 26, 40, 255), width=1)
        bg = C.add_light(bg, C.radial(1400, 1000, (0, 60, 90), 160, 1.6), W / 2, 420)
        self.bg = bg.convert('RGBA')
        sl = np.zeros((H, W, 4), np.uint8)
        sl[::4, :, 3] = 34
        self.scan = Image.fromarray(sl, 'RGBA')
        # окно терминала
        pan = C.rrect(PW, PH, 26, (5, 14, 24), 236, outline=CYD, width=3)
        d = ImageDraw.Draw(pan)
        d.rounded_rectangle((0, 0, PW - 1, 70), 26, fill=(9, 30, 46, 255))
        d.rectangle((0, 40, PW - 1, 70), fill=(9, 30, 46, 255))
        d.line((0, 70, PW, 70), fill=CYD + (255,), width=2)
        for k, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
            d.ellipse((26 + 36 * k, 24, 48 + 36 * k, 46), fill=c + (255,))
        C.put(pan, C.text('jarvis@hockey: ~/%s' % ('nhl' if str(self.league).upper() == 'NHL' else 'khl'), 'mono', 28, DIM, 600),
              PW / 2 + 40, 36)
        self.panel = pan
        # кольца HUD
        self.rings = []
        for r, wdt, arcs in ((150, 6, [(0, 70), (100, 200), (230, 320)]), (122, 3, [(20, 160), (200, 340)]),
                             (96, 10, [(0, 40), (60, 100), (120, 160), (180, 220), (240, 280), (300, 340)])):
            S = 2
            im = Image.new('RGBA', (320 * S, 320 * S), (0, 0, 0, 0))
            dr = ImageDraw.Draw(im)
            for a0, a1 in arcs:
                dr.arc((160 * S - r * S, 160 * S - r * S, 160 * S + r * S, 160 * S + r * S), a0, a1, fill=CY + (255,), width=wdt * S)
            self.rings.append(im.resize((320, 320), Image.LANCZOS))
        self.core = C.radial(150, 150, (150, 240, 255), 255, 1.2)
        self.sub = C.text('%s · %s' % (F.lg_ru(self.league), self.when), 'mono', 36, CY, 700, max_w=640)
        self.match_t = [C.text(t.up, 'unb', 52, TXT, 800, max_w=640) for t in (self.h, self.a)]
        self.embs = {id(t): C.with_shadow(t.emb(100), 10, 0.5, 4) for t in (self.h, self.a)}
        self.form_lab = C.text('ФОРМА:', 'mono', 46, DIM, 700)
        self.chips = {r: F.chip(r, 100) for r in ('В', 'П', '')}
        self.embs_big = {'h': C.with_shadow(self.h.emb(200), 14, 0.5, 6), 'a': C.with_shadow(self.a.emb(200), 14, 0.5, 6)}
        self.vs = C.text('VS', 'unb', 64, CY, 900)
        self.v_head = C.text('ПРОГНОЗ:', 'mono', 66, CY, 800, track=0.1)
        kt = C.text('КЭФ ' + C.fmt_k(self.coef), 'unb', 64, BG, 900)
        kp = C.rrect(kt.width + 100, 124, 20, CY)
        C.put(kp, kt, kp.width / 2, 62)
        self.kef = kp
        self.odds = C.odds_row(self.line, PW - 100, 210, font='unb', lab_font='mono', fill=(9, 30, 46), fill_a=255,
                               val_col=TXT, lab_col=CY, outline=CYD, radius=20) if self.line else None
        self.odds_lab = C.text('основное время:', 'mono', 40, DIM, 600)
        self.v_emb = C.glow(self.fav.emb(300), 30, 1.0, fresh.bright(fresh.club(self.fav), 0.3))
        self.v1 = C.text(self.pick1, 'unb', 92, (255, 255, 255), 900, max_w=PW - 80)
        self.v_wrap = 0                                         # длинный прогноз — в две строки, а не мелко (19.10)
        if C.text(self.pick1, 'unb', 92, (255, 255, 255), 900).width > PW - 80 and ' ' in self.pick1:
            w = self.pick1.split()
            k = min(range(1, len(w)), key=lambda i: abs(len(' '.join(w[:i])) - len(' '.join(w[i:]))))
            r1, r2 = (C.text(x, 'unb', 74, (255, 255, 255), 900, max_w=PW - 80) for x in (' '.join(w[:k]), ' '.join(w[k:])))
            im = Image.new('RGBA', (max(r1.width, r2.width), r1.height + r2.height + 14), (0, 0, 0, 0))
            C.put(im, r1, im.width / 2, r1.height / 2)
            C.put(im, r2, im.width / 2, r1.height + 14 + r2.height / 2)
            self.v1, self.v_wrap = im, 62
        self.v2 = C.text(self.pick2, 'unb', 54, TXT, 800, max_w=PW - 120) if self.pick2 else None
        self.fav_t = C.text(self.fav.up, 'unb', 52, TXT, 800, max_w=640)

    def seg_img(self, segs, n_chars):
        """Строка из цветных сегментов (моноширинно), видны первые n_chars символов."""
        key = (tuple(segs), n_chars)
        if not hasattr(self, '_sc'):
            self._sc = {}
        if key not in self._sc:
            total = sum(len(a) for a, _ in segs)
            im = Image.new('RGBA', (int(self.adv * max(total, 1)) + 20, LH), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            f = C.font('mono', FS, 600)
            x, left = 0, n_chars
            for s_, col in segs:
                if left <= 0:
                    break
                part = s_[:left]
                d.text((x * self.adv, 6), part, font=f, fill=col + (255,))
                x += len(part)
                left -= len(part)
            mw = PW - 72
            if im.width > mw:
                im = im.resize((mw, int(im.height * mw / im.width)), Image.LANCZOS)
            self._sc[key] = im
        return self._sc[key]

    def terminal(self, fr, t):
        if t < self.t2:
            rows = self.block['h']
        elif t < self.t_calc:
            rows = [self.summ['h'], None] + self.block['a']
        else:
            rows = [self.summ['h'], self.summ['a']]
        y = TY
        last = None
        for row in rows:
            if row is None:
                y += LH * 0.5
                continue
            t0, segs, team = row
            if t < t0:
                break
            total = sum(len(a) for a, _ in segs)
            n = min(total, int((t - t0) * 75) + 1)
            im = self.seg_img(segs, n)
            C.put(fr, im, TX, y, anchor='tl')
            k = im.width / max(1.0, self.adv * total + 20) if im.width >= PW - 80 else 1.0
            last = (TX + n * self.adv * k, y)
            if team is not None and len(segs) == 2 and t >= t0 + 0.2:
                q = C.out_back(C.seg(t, t0 + 0.2, t0 + 0.45))
                C.put(fr, C.scale(self.embs[id(team)], max(0.01, q)), PX + PW - 90, y + LH / 2)
            y += LH
        # крупно внизу окна: форма текущей команды / обе эмблемы на «вычисляю»
        if t < self.t1:                                             # до фактов — сам матч: обе эмблемы
            q = C.out_expo(C.seg(t, 0.5, 1.0)) * (1 - C.seg(t, self.t1 - 0.25, self.t1))
            ye = PY + 260 if self.odds is not None else PY + PH / 2
            C.put(fr, self.embs_big['h'], W / 2 - 230 - 80 * (1 - q), ye, q)
            C.put(fr, self.embs_big['a'], W / 2 + 230 + 80 * (1 - q), ye, q)
            C.put(fr, self.vs, W / 2, ye, q)
            if self.odds is not None:
                q2 = C.out_expo(C.seg(t, 0.8, 1.2)) * (1 - C.seg(t, self.t1 - 0.25, self.t1))
                C.put(fr, self.odds_lab, TX, PY + 450, q2, anchor='tl')
                C.put(fr, self.odds, W / 2, PY + 640 + 30 * (1 - q2), q2)
        elif t < self.t_calc:
            side, t0 = ('h', self.t1) if t < self.t2 else ('a', self.t2)
            s = self.sh if side == 'h' else self.sa
            if s['games']:
                tg = t0 + 1.0 * self.u
                C.put(fr, self.form_lab, TX, PY + PH - 80, C.seg(t, tg, tg + 0.15), anchor='tl')
                for k, x in enumerate(s['games']):
                    tk = tg + k * self.rs * self.u
                    if t >= tk:
                        q = C.out_back(C.seg(t, tk, tk + 0.25))
                        C.put(fr, C.scale(self.chips[x['res']], max(0.01, q)), TX + 270 + 120 * k, PY + PH - 72)
        else:
            q = C.out_expo(C.seg(t, self.t_calc + 0.1, self.t_calc + 0.5))
            C.put(fr, self.embs_big['h'], W / 2 - 230 - 80 * (1 - q), PY + 520, q)
            C.put(fr, self.embs_big['a'], W / 2 + 230 + 80 * (1 - q), PY + 520, q)
            C.put(fr, self.vs, W / 2, PY + 520, q)
        if last and t < self.drop and int(t * 4) % 2 == 0:
            C.put(fr, C.rrect(26, 52, 3, CY), last[0] + 6, last[1] + 14, anchor='tl')

    def hud(self, fr, t):
        sp = 1.0 if t < self.t_calc or t >= self.drop + 0.6 else 6.0
        ang = t * 30 * sp
        cx, cy = 190, 392
        a = C.seg(t, 0, 0.4)
        for k, rg in enumerate(self.rings):
            C.put(fr, C.rotate(rg, ang * (1 if k % 2 == 0 else -1.4) * (1 + 0.3 * k)), cx, cy, a)
        pulse = 0.7 + 0.3 * math.sin(t * 6)
        if self.drop <= t < self.drop + 0.5:
            pulse = 2.0
        fr = C.add_light(fr, self.core, cx, cy, a * pulse)
        y = 318                                                     # матч: хозяева / гости, лига и время
        names = self.match_t if t < self.drop else [self.fav_t]     # на прогнозе — только выбранная команда
        for k, im in enumerate(names):
            C.put(fr, im, 362, y, C.seg(t, 0.1 + 0.1 * k, 0.4 + 0.1 * k), anchor='tl')
            y += im.height + 14
        C.put(fr, self.sub, 362, y + 10, C.seg(t, 0.3, 0.6), anchor='tl')
        return fr

    def scramble(self, s, t, t0, d=0.5):
        """Текст «расшифровывается»: случайные знаки, по очереди встающие на место."""
        out = []
        n = len(s)
        for i, ch in enumerate(s):
            lock = t0 + d * (i + 1) / n
            if ch == ' ' or t >= lock:
                out.append(ch)
            else:
                rr = (int(t * 30) * 31 + i * 17) % len(GLYPHS)
                out.append(GLYPHS[rr])
        return ''.join(out)

    def verdict(self, fr, t):
        D, u = self.drop, self.u
        C.put(fr, self.v_head, W / 2, PY + 130, C.seg(t, D, D + 0.05))
        q = C.out_back(C.seg(t, D + 0.05, D + 0.4), 1.2)
        C.put(fr, C.scale(self.v_emb, max(0.01, q)), W / 2, PY + 340)
        s1 = self.scramble(self.pick1, t, D, 0.55)
        sh = self.v_wrap
        if sh:                                                  # две строки — без «перебора букв», проявлением
            C.put(fr, self.v1, W / 2, PY + 548 + sh / 2, C.seg(t, D, D + 0.4))
        else:
            im = self.v1 if s1 == self.pick1 else C.text(s1, 'unb', 92, (255, 255, 255), 900, max_w=PW - 80)
            C.put(fr, im, W / 2, PY + 548)
        if self.v2:
            C.put(fr, self.v2, W / 2, PY + 632 + sh, C.seg(t, D + 0.4, D + 0.6))
        kq = C.out_expo(C.seg(t, D + 1.0 * u, D + 1.4 * u))
        C.put(fr, self.kef, W / 2, PY + 745 + sh + 30 * (1 - kq), kq)

    def glitch(self, fr, t, k):
        """Рваные горизонтальные полосы + расслоение цвета, k — сила 0..1."""
        if k <= 0.01:
            return fr
        rnd = np.random.default_rng(int(t * 1000))
        arr = np.asarray(fr.convert('RGB')).copy()
        for _ in range(int(14 * k) + 2):
            y0 = int(rnd.integers(0, H - 40))
            hh = int(rnd.integers(8, 90))
            sh = int(rnd.integers(-160, 160) * k)
            arr[y0:y0 + hh] = np.roll(arr[y0:y0 + hh], sh, axis=1)
            if rnd.random() < 0.3:
                arr[y0:y0 + hh, :, int(rnd.integers(0, 3))] = 255
        out = Image.fromarray(arr, 'RGB')
        return C.rgb_split(out, 22 * k)

    def frame(self, t):
        u, D = self.u, self.drop
        fr = self.bg.copy()
        fr = self.hud(fr, t)
        fresh.header(fr, {'league': self.league}, C.seg(t, 0, 0.3), col=DIM)
        pq = C.out_expo(C.seg(t, 0.35, 0.8))
        C.put(fr, self.panel, W / 2, PY + PH / 2 + 60 * (1 - pq), pq)
        if t < D:
            self.terminal(fr, t)
        else:
            self.verdict(fr, t)
        if t >= self.t_cta:
            fresh.cta(fr, t, self.t_cta, y=1492, h=160)
        else:
            fresh.handle(fr, C.seg(t, 0.4, 0.8), col=DIM)
        fr.alpha_composite(self.scan)
        # глитч: короткие вспышки на сменах команд и большой — на дропе
        g = 0.0
        for th, amp, d in ((self.t2, 0.35, 0.15), (self.t_calc, 0.3, 0.12), (D, 1.0, 0.4)):
            if th <= t < th + d:
                g = max(g, amp * (1 - (t - th) / d))
        if D - 0.12 <= t < D:
            g = max(g, 0.5)
        fr = self.glitch(fr, t, g)
        z = 1.0
        dx, dy = C.shake(t, D, 16, 0.35)
        if t >= D:
            z += 0.05 * (1 - C.seg(t, D, D + 0.4)) ** 2
        fr = C.zoom(fr, z, dx=dx, dy=dy)
        if D <= t < D + 0.18:
            fr = Image.blend(fr.convert('RGB'), Image.new('RGB', fr.size, (200, 245, 255)), 0.5 * (1 - C.seg(t, D, D + 0.18)))
        fr = C.vignette(fr, 0.4)
        return C.grain(fr, t, 3)


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many
