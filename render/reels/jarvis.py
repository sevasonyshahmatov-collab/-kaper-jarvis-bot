# -*- coding: utf-8 -*-
"""«Терминал JARVIS» — интерфейс ИИ-ассистента разбирает матч.

Сверху — HUD: вращающиеся кольца «реактора», J.A.R.V.I.S., статус. Ниже — окно терминала: на доли трека печатается
анализ первой команды (последние 3 игры, очки), потом второй; перед дропом — «ВЫЧИСЛЯЮ…» и полоса загрузки
(на треке в это время тишина), на дропе экран рвёт глитчем и проявляется «ВЕРДИКТ: …» с кэфом. В конце — Telegram.
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
LH = 76                       # строка
PX, PY = 46, 556              # окно терминала
PW, PH = W - 2 * PX, 1446 - 556
TX, TY = PX + 36, PY + 100    # первая строка текста
GLYPHS = 'АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЭЮЯ0123456789#%&@$'


class Jarvis(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=1.0, drop=8.0, seed=19):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.pick = league, when, coef, pick
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
        self.sh, self.sa = F.norm(sh), F.norm(sa)
        self.adv = C.font('mono', FS, 600).getlength('0')
        self.cols = int((PW - 72) / self.adv)
        self.t1, self.t2, self.t_calc = self.b(-7), self.b(-4), self.b(-1)
        self.block = {'h': self._team(self.h, self.sh, self.t1), 'a': self._team(self.a, self.sa, self.t2)}
        self.summ = {'h': self._summary(self.h, self.sh, self.t2), 'a': self._summary(self.a, self.sa, self.t_calc)}
        self.t_cta = self.b(4.5)
        self.dur = self.b(9)
        self.cover_t = self.b(3)
        self._prep()

    def _team(self, team, s, t0):
        """Строки анализа клуба: [(время начала печати, сегменты, эмблема|None)]."""
        u = self.u
        col = fresh.bright(fresh.club(team), 0.45)
        out = [(t0, [('> ', CY), ('АНАЛИЗ: ', CY), (team.up, col)], team)]
        g = s['games']
        for k, x in enumerate(g):
            sc = x['score'] + (' ' + x['note'] if x['note'] else '')
            seg = [('  ' + (x['date'] + ' ' if x['date'] else ''), DIM), (x['res'] + ' ', F.res_col(x['res'])),
                   ('%-6s ' % sc, TXT), (x['opp'], TXT)]
            if sum(len(a) for a, _ in seg) > self.cols:               # длинное имя соперника — без даты
                seg[0] = ('  ', DIM)
            out.append((t0 + (0.5 + 0.3 * k) * u, seg, None))
        tl = t0 + 1.5 * u
        if s['points'] is not None:
            tail = (' за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей'))) if s['gp'] is not None else ''
            out.append((tl, [('  очки: ', DIM), ('%d' % s['points'], GOLD), (tail, DIM)], None))
            tl += 0.35 * u
        if s['place'] is not None:
            out.append((tl, [('  место: ', DIM), ('%d' % s['place'], GOLD), ((' ' + s['place_scope']) if s['place_scope'] else '', DIM)], None))
            tl += 0.35 * u
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
        self.title = C.text('J.A.R.V.I.S.', 'unb', 64, TXT, 800)
        self.sub = C.text('%s · %s' % (F.lg_ru(self.league), self.when), 'mono', 34, CY, 700, max_w=640)
        self.match_t = C.text('%s — %s' % (self.h.up, self.a.up), 'unb', 36, TXT, 700, max_w=640)
        self.embs = {id(t): C.with_shadow(t.emb(100), 10, 0.5, 4) for t in (self.h, self.a)}
        self.form_lab = C.text('ФОРМА:', 'mono', 46, DIM, 700)
        self.chips = {r: F.chip(r, 100) for r in ('В', 'П', '')}
        self.embs_big = {'h': C.with_shadow(self.h.emb(200), 14, 0.5, 6), 'a': C.with_shadow(self.a.emb(200), 14, 0.5, 6)}
        self.vs = C.text('VS', 'unb', 64, CY, 900)
        self.v_emb = C.glow(self.fav.emb(240), 26, 1.0, fresh.bright(fresh.club(self.fav), 0.3))
        self.v_head = C.text('ВЕРДИКТ:', 'mono', 66, CY, 800, track=0.1)
        self.v2 = C.text(self.pick2, 'unb', 50, TXT, 800, max_w=PW - 120) if self.pick2 else None
        kt = C.text('КЭФ ' + C.fmt_k(self.coef), 'unb', 64, BG, 900)
        kp = C.rrect(kt.width + 90, 118, 20, CY)
        C.put(kp, kt, kp.width / 2, 59)
        self.kef = kp

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

    def status(self, t):
        if t < self.t1:
            return 'ЗАГРУЗКА МАТЧА'
        if t < self.t2:
            return 'АНАЛИЗ: ' + self.h.up
        if t < self.t_calc:
            return 'АНАЛИЗ: ' + self.a.up
        if t < self.drop:
            return 'ВЫЧИСЛЯЮ' + '.' * (1 + int((t - self.t_calc) * 6) % 3)
        return 'ГОТОВО'

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
            if team is not None and len(segs) == 3 and t >= t0 + 0.2:
                q = C.out_back(C.seg(t, t0 + 0.2, t0 + 0.45))
                C.put(fr, C.scale(self.embs[id(team)], max(0.01, q)), PX + PW - 90, y + LH / 2)
            y += LH
        # крупно внизу окна: форма текущей команды / обе эмблемы на «вычисляю»
        if t < self.t_calc:
            side, t0 = ('h', self.t1) if t < self.t2 else ('a', self.t2)
            s = self.sh if side == 'h' else self.sa
            if s['games']:
                tg = t0 + 0.5 * self.u
                C.put(fr, self.form_lab, TX, PY + PH - 80, C.seg(t, tg, tg + 0.15), anchor='tl')
                for k, x in enumerate(s['games']):
                    tk = tg + 0.3 * k * self.u
                    if t >= tk:
                        q = C.out_back(C.seg(t, tk, tk + 0.25))
                        C.put(fr, C.scale(self.chips[x['res']], max(0.01, q)), TX + 270 + 120 * k, PY + PH - 72)
        else:
            q = C.out_expo(C.seg(t, self.t_calc + 0.1, self.t_calc + 0.5))
            C.put(fr, self.embs_big['h'], W / 2 - 230 - 80 * (1 - q), PY + 760, q)
            C.put(fr, self.embs_big['a'], W / 2 + 230 + 80 * (1 - q), PY + 760, q)
            C.put(fr, self.vs, W / 2, PY + 760, q)
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
        C.put(fr, self.title, 360, 300, C.seg(t, 0.1, 0.4), anchor='tl')
        C.put(fr, self.match_t, 362, 384, C.seg(t, 0.2, 0.5), anchor='tl')
        C.put(fr, self.sub, 362, 436, C.seg(t, 0.25, 0.55), anchor='tl')
        st = self.status(t)
        col = (255, 214, 90) if self.t_calc <= t < self.drop else ((80, 255, 150) if t >= self.drop else CY)
        dot = C.ellipse(18, 18, col)
        C.put(fr, dot, 362, 492, 1 if int(t * 3) % 2 == 0 or t >= self.drop else 0.3, anchor='tl')
        C.put(fr, C.text(st, 'mono', 32, col, 800, max_w=640), 394, 486, C.seg(t, 0.3, 0.5), anchor='tl')
        return fr

    def calc(self, fr, t):
        """«ВЫЧИСЛЯЮ…» поверх терминала: полоса загрузки."""
        q = C.seg(t, self.t_calc, self.drop - 0.05)
        a = C.seg(t, self.t_calc, self.t_calc + 0.15)
        box = C.rrect(PW - 100, 210, 22, (4, 12, 20), 245, outline=(255, 214, 90), width=3)
        C.put(box, C.text('ВЫЧИСЛЯЮ ПРОГНОЗ', 'unb', 50, (255, 214, 90), 800), box.width / 2, 66)
        bar = C.rrect(box.width - 100, 34, 17, (30, 40, 50))
        C.put(box, bar, box.width / 2, 150)
        fw = int((box.width - 100) * C.in_out(q))
        if fw > 34:
            C.put(box, C.rrect(fw, 34, 17, (255, 214, 90)), 50, 133, anchor='tl')
        C.put(fr, box, W / 2, PY + 450, a)

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
        C.put(fr, self.v_head, W / 2, PY + 125, C.seg(t, D, D + 0.05))
        q = C.out_back(C.seg(t, D + 0.05, D + 0.4), 1.2)
        C.put(fr, C.scale(self.v_emb, max(0.01, q)), W / 2, PY + 310)
        s1 = self.scramble(self.pick1, t, D, 0.55)
        C.put(fr, C.text(s1, 'unb', 84, (255, 255, 255), 900, max_w=PW - 80), W / 2, PY + 495)
        if self.v2:
            C.put(fr, self.v2, W / 2, PY + 575, C.seg(t, D + 0.4, D + 0.6))
        kq = C.out_expo(C.seg(t, D + 1.0 * u, D + 1.4 * u))
        C.put(fr, self.kef, W / 2, PY + 672 + 30 * (1 - kq), kq)

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
            if t >= self.t_calc:
                self.calc(fr, t)
        else:
            self.verdict(fr, t)
        if t >= self.t_cta:
            fresh.cta(fr, t, self.t_cta, y=1380)
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
