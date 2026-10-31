# -*- coding: utf-8 -*-
"""Ролики v3 (владелец 31.10, ТЗ docs/handoff/REELS_V3_BRIEF.md): 8–15 с, живой голос, крупные субтитры, крючок с
первого кадра, ставка/итог — развязка в конце. Пять форматов — пять разных визуальных языков (jarvis-creative 31.10):
  1 «Формула»     — экспресс дня: кэфы ног складываются в уравнение и схлопываются в общий кэф;
  2 «Кардиограмма» — «весь сезон ставим X на команду»: линия матч за матчем, итог в конце;
  3 «Угадай»      — закономерность сезона: вопрос, три эмблемы и пауза, лидер и аутсайдер «N из M»;
  4 «Открытка»    — клубный: «Болеешь за X? Это тебе» → три цифры → «отправь тому, кто болеет за X»;
  5 «Серия»       — прогноз с крючком: цифра серии, точки-матчи, пустая точка «сегодня?», ставка и кэф.
Сцены задаются списком {k, say, sub, min}: длина сцены = max(min, длина голоса + пауза), поэтому кадр сам
подстраивается под озвучку (team/reels_v3/tts.py). Без голоса (локальная проверка кадров) длина оценивается по тексту.
Никаких плашек/табло прежних шаблонов, без процентов шанса, без названий БК.
"""
import math
import os
import re

from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels.core import W, H

BG = (12, 14, 18)
BG2 = (6, 7, 10)
GOLD = (233, 180, 76)
GOLD2 = (255, 217, 138)
ICE = (238, 242, 246)
MUTED = (124, 135, 148)
OK = (63, 208, 143)
BAD = (226, 87, 87)
LINE0 = (42, 48, 56)
ACC = {'KHL': (90, 169, 230), 'NHL': (201, 209, 218)}
SUB_Y = 1395
GAP = 0.2
PREP = {'в', 'на', 'за', 'из', 'к', 'и', 'без', 'у', 'с', 'по', 'от', 'до', 'а', '—'}


def est(say):
    """Оценка длины фразы без синтеза (≈14,5 знака в секунду у Edge +6 %)."""
    return 0.35 + len(say) / 14.5


_BG = {}


def background(league, tint=None):
    key = (league, tint)
    if key not in _BG:
        im = C.vgrad(W, H, [(0.0, BG2), (0.45, BG), (1.0, BG2)]).convert('RGBA')
        acc = tint or ACC.get(league, ACC['KHL'])
        g = C.radial(1400, 1400, acc, a0=46, power=2.4)
        C.put(im, g, W / 2, 760)
        _BG[key] = C.vignette(im, 0.5).convert('RGBA')
    return _BG[key].copy()


def team(name, league):
    if str(league).upper() == 'NHL':
        import nhl
        nhl.register()
        name = nhl.resolve(name)
    return C.Team(name)


def sheen(im, k):
    """Блик, один раз проходящий по тексту (k 0…1)."""
    if k <= 0 or k >= 1:
        return im
    w, h = im.size
    band = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(band)
    x = -w * 0.3 + k * w * 1.6
    d.polygon([(x, 0), (x + w * 0.18, 0), (x + w * 0.18 - h * 0.5, h), (x - h * 0.5, h)], fill=200)
    band = band.filter(ImageFilter.GaussianBlur(12))
    lay = Image.new('RGBA', (w, h), GOLD2 + (0,))
    lay.putalpha(Image.composite(band, Image.new('L', (w, h), 0), im.getchannel('A')))
    out = im.copy()
    out.alpha_composite(lay)
    return out


class V3(C.Reel):
    league = 'KHL'
    tail = 0.0
    cover_t = 0.6

    def __init__(self, scenes, league='KHL', durs=None, **kw):
        super().__init__(**kw)
        self.league = 'NHL' if str(league).upper() in ('NHL', 'НХЛ') else 'KHL'
        self.scenes = scenes
        self.timing(durs)

    def timing(self, durs=None):
        """durs — длины голоса по сценам (с); None — оценка по тексту."""
        self.vd = list(durs) if durs else [est(s['say']) for s in self.scenes]
        self.T, t = [], 0.0
        for s, d in zip(self.scenes, self.vd):
            self.T.append(t)
            t += max(s.get('min', 1.4), d + GAP)
        self.dur = round(max(t, 8.0), 2)
        self.L = [b - a for a, b in zip(self.T, self.T[1:] + [self.dur])]

    def at(self, t):
        i = max(j for j, a in enumerate(self.T) if a <= t + 1e-6)
        return i, t - self.T[i], self.L[i]

    def start(self, k):
        for s, a in zip(self.scenes, self.T):
            if s['k'] == k:
                return a
        return None

    # ── субтитры: по 1–3 слова, звучащее слово — золотом ──
    def subtitle(self, fr, t):
        i, lt, _ = self.at(t)
        sub = self.scenes[i].get('sub')
        if not sub:
            return
        sub = re.sub(r'(\d+) из (\d+)', '\\1\u00a0из\u00a0\\2', sub)
        words = sub.split(' ')
        if not words:
            return
        d = max(0.4, self.vd[i])
        w = [len(x) + 2 for x in words]
        tot = float(sum(w))
        acc, cur = 0.0, 0
        for j, x in enumerate(w):
            if lt < 0.05 + d * (acc + x) / tot:
                cur = j
                break
            acc += x
        else:
            cur = len(words) - 1
        chunks, c = [], []
        for j, x in enumerate(words):
            nxt = words[j + 1] if j + 1 < len(words) else ''
            if c and len(' '.join(words[k] for k in c + [j])) > 18 and words[c[-1]].lower() not in PREP:
                chunks.append(c)
                c = []
            c.append(j)
            if (len(c) >= 3 and x.lower() not in PREP) or (x.endswith((',', '.', '?', ':')) and nxt):
                chunks.append(c)
                c = []
        if c:
            chunks.append(c)
        ch = next(c for c in chunks if cur in c)
        f = C.font('mont', 74, 900)
        parts = [words[k] for k in ch]
        sp = f.getlength(' ')
        widths = [f.getlength(p) for p in parts]
        total = sum(widths) + sp * (len(parts) - 1)
        scale = min(1.0, 960 / max(1, total))
        size = int(74 * scale)
        f = C.font('mont', size, 900)
        widths = [f.getlength(p) for p in parts]
        total = sum(widths) + f.getlength(' ') * (len(parts) - 1)
        x = W / 2 - total / 2
        for k, p, wd in zip(ch, parts, widths):
            col = GOLD2 if k == cur else ICE
            im = C.text(p, 'mont', size, col, 900, stroke=6, stroke_fill=(0, 0, 0), trim=False)
            C.put(fr, im, x + wd / 2, SUB_Y)
            x += wd + f.getlength(' ')

    def frame(self, t):
        fr = background(self.league, getattr(self, 'tint', None))
        i, lt, L = self.at(t)
        getattr(self, 'draw_' + self.scenes[i]['k'])(fr, lt, L, t)
        self.subtitle(fr, t)
        return fr


def hdr(fr, s, y=300, col=MUTED, size=34):
    C.put(fr, C.text(s, 'mont', size, col, 800, track=0.16), W / 2, y)


# ───────────────────────────── 1. «Формула» — экспресс дня ─────────────────────────────
class Formula(V3):
    """legs: [{team, bet, kef}], kef — общий кэф, day — подпись."""

    def __init__(self, scenes, legs, kef, day='', **kw):
        self.legs, self.kef, self.day = legs, kef, day
        super().__init__(scenes, **kw)
        self.cover_t = 0.5

    def eq(self, n):
        return ' × '.join(C.fmt_k(l['kef']).replace('.', ',') for l in self.legs[:n])

    def draw_eqrow(self, fr, n, y=1150, a=1.0, extra=None):
        s = self.eq(n)
        if not s:
            return
        im = C.text(s, 'unb', 92, GOLD, 800, max_w=980)
        C.put(fr, im, W / 2, y, a)

    def draw_hook(self, fr, lt, L, t):
        k = C.out_cubic(C.clamp(lt / 0.5))
        hdr(fr, '%d %s · ОДИН КЭФ' % (len(self.legs), 'МАТЧА' if len(self.legs) < 5 else 'МАТЧЕЙ'), 470, ICE, 48)
        big = C.text(C.fmt_k(self.kef).replace('.', ','), 'unb', 330, GOLD, 900)
        big = C.scale(big, 1.08 - 0.08 * k)
        C.put(fr, C.glow(big, 30, 0.9, GOLD), W / 2, 820)
        hdr(fr, 'ЭКСПРЕСС ДНЯ' + (' · ' + self.day if self.day else ''), 1110, MUTED, 34)

    def draw_leg(self, fr, lt, L, t):
        i = int(self.scenes[self.at(t)[0]]['i'])
        leg = self.legs[i]
        k = C.out_back(C.clamp(lt / 0.45), 1.2)
        hdr(fr, 'МАТЧ %d ИЗ %d' % (i + 1, len(self.legs)), 330, MUTED, 34)
        if leg.get('team'):
            e = team(leg['team'], leg.get('league', self.league)).emb(380)
            C.put(fr, e, W / 2, 610 - 160 * (1 - k), C.clamp(lt / 0.25))
        C.put(fr, C.lines(leg['bet'], 'mont', 74, 940, ICE, 900), W / 2, 880, C.clamp(lt / 0.3))
        # кэф ноги падает справа в строку уравнения
        kd = C.out_cubic(C.clamp((lt - 0.35) / 0.5))
        kim = C.text(C.fmt_k(leg['kef']).replace('.', ','), 'unb', 120, GOLD, 900)
        if kd < 1:
            C.put(fr, kim, W / 2, 1020 + 130 * kd, 1.0)
            self.draw_eqrow(fr, i, 1150)
        else:
            self.draw_eqrow(fr, i + 1, 1150)

    def draw_total(self, fr, lt, L, t):
        k = C.out_back(C.clamp(lt / 0.35), 1.6)
        if k < 0.98:
            row = C.text(self.eq(len(self.legs)), 'unb', 92, GOLD, 800, max_w=980)
            C.put(fr, C.scale(row, max(0.05, 1 - k)), W / 2, 1150 - 400 * k, 1 - k)
        big = C.text('= ' + C.fmt_k(self.kef).replace('.', ','), 'unb', 260, GOLD, 900)
        big = sheen(big, C.clamp((lt - 0.45) / 0.7))
        C.put(fr, C.glow(C.scale(big, 0.7 + 0.3 * k), 30, 0.9, GOLD), W / 2, 760, C.clamp(lt / 0.2))
        C.put(fr, C.text(self.eq(len(self.legs)), 'unb', 54, MUTED, 700, max_w=900), W / 2, 1000, C.clamp((lt - 0.4) / 0.3))
        hdr(fr, 'ОБЩИЙ КЭФ', 470, ICE, 46)

    def draw_cta(self, fr, lt, L, t):
        a = C.clamp(lt / 0.3)
        C.put(fr, C.text('= ' + C.fmt_k(self.kef).replace('.', ','), 'unb', 150, GOLD, 900), W / 2, 520, a)
        C.put(fr, C.lines('Все купоны и итоги — в канале', 'mont', 84, 920, ICE, 900), W / 2, 820, a)
        C.put(fr, C.text('@jarvibet', 'mont', 60, GOLD2, 800), W / 2, 1040, a)


# ───────────────────────────── 2. «Кардиограмма» — весь сезон на … ─────────────────────────────
class Cardio(V3):
    """games: [[ММ-ДД, соперник, счёт, кэф победы|None]], seq: '1011…', bal: баланс в ставках или None."""

    def __init__(self, scenes, team_name, bet, games, seq, n, m, bal=None, season='', note='', **kw):
        self.tn, self.bet, self.games, self.seq = team_name, bet, games, seq
        self.n, self.m, self.bal, self.season, self.note = n, m, bal, season, note
        super().__init__(scenes, **kw)
        self.T_ = team(team_name, self.league)
        self.tint = self.T_.c1
        # точки линии: с кэфами — баланс в ставках, без — шаг вверх/вниз (без шкалы)
        ys, v = [0.0], 0.0
        for i, s in enumerate(seq):
            if bal is not None:
                k = games[i][3] or 0
                v += (k - 1) if s == '1' else -1
            else:
                v += 1 if s == '1' else -1
            ys.append(v)
        self.ys = ys
        self.cover_t = 0.5

    def chart(self, fr, upto, flash=0.0, box=(90, 640, 990, 1230)):
        x0, y0, x1, y1 = box
        lo, hi = min(self.ys), max(self.ys)
        span = max(1e-6, hi - lo)
        X = lambda i: x0 + (x1 - x0) * i / max(1, len(self.ys) - 1)
        Y = lambda v: y1 - (y1 - y0) * (v - lo) / span
        ss = 2
        lay = Image.new('RGBA', (W * ss // 2, H * ss // 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        if self.bal is not None:
            zy = Y(0)
            for x in range(x0, x1, 28):
                d.line([(x, zy), (x + 14, zy)], fill=LINE0 + (255,), width=3)
        n = int(upto)
        frac = upto - n
        pts = [(X(i), Y(v)) for i, v in enumerate(self.ys[:n + 1])]
        if n + 1 < len(self.ys) and frac > 0:
            ax, ay = X(n), Y(self.ys[n])
            bx, by = X(n + 1), Y(self.ys[n + 1])
            pts.append((ax + (bx - ax) * frac, ay + (by - ay) * frac))
        if len(pts) > 1:
            gl = Image.new('RGBA', lay.size, (0, 0, 0, 0))
            ImageDraw.Draw(gl).line(pts, fill=GOLD + (200,), width=18, joint='curve')
            lay.alpha_composite(gl.filter(ImageFilter.GaussianBlur(10)))
            d.line(pts, fill=GOLD + (255,), width=7, joint='curve')
        for i in range(1, min(n, len(self.seq)) + 1):
            col = OK if self.seq[i - 1] == '1' else BAD
            x, y = X(i), Y(self.ys[i])
            r = 9
            d.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,))
        if len(pts) > 1:
            x, y = pts[-1]
            r = 16 + 10 * flash
            d.ellipse([x - r, y - r, x + r, y + r], fill=GOLD2 + (255,))
        fr.alpha_composite(lay)

    def draw_hook(self, fr, lt, L, t):
        k = C.out_cubic(C.clamp(lt / 0.5))
        C.put(fr, C.glow(self.T_.emb(250), 26, 0.7, self.T_.c1), W / 2, 420)
        hdr(fr, 'ВЕСЬ СЕЗОН СТАВИМ', 610, GOLD, 40)
        C.put(fr, C.text(self.bet.upper(), 'unb', 72, ICE, 800, max_w=980), W / 2, 740 + 20 * (1 - k))
        C.put(fr, C.text('НА ' + self.T_.up, 'unb', 64, ICE, 800, max_w=960), W / 2, 880)
        C.put(fr, C.text('Сколько зашло?', 'mont', 52, MUTED, 700), W / 2, 1040, C.clamp((lt - 0.4) / 0.3))

    def head(self, fr, i):
        C.put(fr, self.T_.emb(120), 150, 340)
        C.put(fr, C.text(self.bet, 'mont', 40, ICE, 800, max_w=760), 230, 318, anchor='tl')
        C.put(fr, C.text('%s · %s' % (self.T_.short, self.season), 'mont', 32, MUTED, 700), 230, 368, anchor='tl')
        hits = self.seq[:i].count('1')
        C.put(fr, C.text('МАТЧ %d ИЗ %d' % (i, self.m), 'unb', 48, ICE, 800), W / 2, 520)
        C.put(fr, C.text('зашло %d' % hits, 'mont', 40, OK, 800), W / 2, 580)

    def draw_run(self, fr, lt, L, t):
        k = C.clamp((lt - 0.2) / max(0.5, L - 0.5))
        upto = k * self.m
        i = min(self.m, int(math.ceil(upto - 1e-6)))
        # «камера» чуть приближается на середине
        self.head(fr, i)
        self.chart(fr, upto)
        if 0 < i <= len(self.games):
            g = self.games[i - 1]
            col = OK if self.seq[i - 1] == '1' else BAD
            C.put(fr, C.text('%s  %s  %s' % (g[0][3:] + '.' + g[0][:2], g[1], g[2]), 'mont', 40, col, 800, max_w=960),
                  W / 2, 1290)

    def draw_result(self, fr, lt, L, t):
        k = C.out_back(C.clamp(lt / 0.35), 1.5)
        self.head(fr, self.m)
        self.chart(fr, self.m, flash=math.sin(min(1.0, lt / 0.5) * math.pi))
        if self.bal is not None:
            s = ('+' if self.bal > 0 else '−' if self.bal < 0 else '') + ('%.1f' % abs(self.bal)).replace('.', ',')
            big, sub = s, 'ставки за сезон'
            col = OK if self.bal > 0 else BAD
        else:
            big, sub = '%d из %d' % (self.n, self.m), 'зашло'
            col = GOLD
        dark = Image.new('RGBA', (W, 520), (6, 7, 10, int(200 * C.clamp(lt / 0.25))))
        fr.alpha_composite(dark, (0, 680))
        C.put(fr, C.glow(C.scale(C.text(big, 'unb', 190, col, 900, max_w=980), 0.6 + 0.4 * k), 26, 0.8, col),
              W / 2, 880, C.clamp(lt / 0.2))
        C.put(fr, C.text(sub, 'mont', 56, ICE, 800), W / 2, 1040, C.clamp((lt - 0.2) / 0.3))
        if self.note:
            C.put(fr, C.text(self.note, 'mont', 30, MUTED, 600, max_w=960), W / 2, 1120, C.clamp((lt - 0.3) / 0.3))

    def draw_cta(self, fr, lt, L, t):
        a = C.clamp(lt / 0.3)
        C.put(fr, self.T_.emb(200), W / 2, 470, a)
        C.put(fr, C.lines('Какую команду посчитать завтра?', 'mont', 80, 940, ICE, 900), W / 2, 780, a)
        C.put(fr, C.text('пиши в комментариях', 'mont', 52, GOLD2, 800), W / 2, 960, a)
        C.put(fr, C.text('история сезона, не совет', 'mont', 30, MUTED, 600), W / 2, 1060, a)


# ───────────────────────────── 3. «Угадай» — закономерность сезона ─────────────────────────────
class Guess(V3):
    """three: [имя×3] (порядок на экране), leader: (имя, n, m), worst: (имя, n, m), note: «КХЛ 2026/27 · N матчей»."""

    def __init__(self, scenes, question, three, leader, worst, note, **kw):
        self.q, self.three, self.leader, self.worst, self.note = question, three, leader, worst, note
        super().__init__(scenes, **kw)
        self.cover_t = 0.5

    def draw_q(self, fr, lt, L, t):
        k = C.out_cubic(C.clamp(lt / 0.4))
        hdr(fr, self.note.upper(), 420, MUTED, 32)
        C.put(fr, C.lines(self.q, 'unb', 86, 950, ICE, 800, max_lines=5), W / 2, 800 - 20 * (1 - k))

    def emb3(self, fr, lt, keep=None, kk=0.0):
        xs = [210, 540, 870]
        for x, n in zip(xs, self.three):
            T = team(n, self.league)
            e = T.emb(250)
            if keep is not None and n != keep:
                e = C.fade(e.convert('LA').convert('RGBA'), 1 - kk)
                C.put(fr, e, x, 900 + 300 * kk)
                continue
            if keep is not None:
                s = 1 + 0.6 * kk
                C.put(fr, C.glow(C.scale(e, s), 30, 0.8 * kk, T.c1), x + (540 - x) * kk, 900 - 160 * kk)
            else:
                C.put(fr, e, x, 900)
                C.put(fr, C.text(T.short, 'mont', 38, ICE, 800, max_w=300), x, 1080)

    def draw_guess(self, fr, lt, L, t):
        C.put(fr, C.lines(self.q, 'mont', 50, 940, MUTED, 800, max_lines=3), W / 2, 470)
        self.emb3(fr, lt)
        k = C.clamp(lt / max(0.8, L - 0.2))
        w = int(800 * (1 - k))
        if w > 2:
            fr.alpha_composite(Image.new('RGBA', (w, 10), GOLD + (255,)), (W // 2 - w // 2, 1200))
        C.put(fr, C.text('Угадаешь?', 'unb', 70, GOLD2, 800), W / 2, 660)

    def draw_reveal(self, fr, lt, L, t):
        kk = C.in_out(C.clamp(lt / 0.5))
        C.put(fr, C.lines(self.q, 'mont', 50, 940, MUTED, 800, max_lines=3), W / 2, 470, 1 - kk)
        self.emb3(fr, lt, self.leader[0], kk)
        T = team(self.leader[0], self.league)
        a = C.clamp((lt - 0.45) / 0.3)
        C.put(fr, C.text(T.up, 'unb', 64, ICE, 800, max_w=960), W / 2, 1000, a)
        C.put(fr, C.text('%d из %d' % self.leader[1:], 'unb', 150, GOLD, 900), W / 2, 1150, a)
        lab = getattr(self, 'lead_label', '')
        if lab:
            C.put(fr, C.text(lab, 'mont', 34, MUTED, 700, max_w=960), W / 2, 1265, a)

    def draw_worst(self, fr, lt, L, t):
        k = C.out_cubic(C.clamp(lt / 0.35))
        T = team(self.leader[0], self.league)
        C.put(fr, T.emb(150), 200, 360 - 40 * (1 - k))
        C.put(fr, C.text('%d из %d' % self.leader[1:], 'unb', 56, GOLD, 800), 300, 330, anchor='tl')
        C.put(fr, C.text(getattr(self, 'worst_label', 'А хуже всех —'), 'mont', 60, MUTED, 800), W / 2, 590, k)
        T2 = team(self.worst[0], self.league)
        C.put(fr, T2.emb(300), W / 2, 800 + 200 * (1 - k), k)
        C.put(fr, C.text(T2.up, 'unb', 60, ICE, 800, max_w=960), W / 2, 1010, k)
        C.put(fr, C.text('%d из %d' % self.worst[1:], 'unb', 140, ICE, 900), W / 2, 1170, C.clamp((lt - 0.3) / 0.3))

    def draw_cta(self, fr, lt, L, t):
        a = C.clamp(lt / 0.3)
        C.put(fr, C.lines('А твоя команда?', 'unb', 92, 940, ICE, 800), W / 2, 640, a)
        C.put(fr, C.text('ответ — в комментарии', 'mont', 56, GOLD2, 800), W / 2, 820, a)
        C.put(fr, C.text(self.note, 'mont', 34, MUTED, 600, max_w=960), W / 2, 960, a)


# ───────────────────────────── 4. «Открытка» — клубный ─────────────────────────────
class Postcard(V3):
    """facts: [(большая цифра, подпись)] — три штуки."""

    def __init__(self, scenes, team_name, facts, note='', **kw):
        self.facts, self.note = facts, note
        super().__init__(scenes, **kw)
        self.T_ = team(team_name, self.league)
        self.tint = self.T_.c1
        self.cover_t = 0.5

    def draw_hook(self, fr, lt, L, t):
        k = C.out_cubic(C.clamp(lt / 0.5))
        C.put(fr, C.glow(C.scale(self.T_.emb(420), 1.05 - 0.05 * k), 40, 1.0, self.T_.c1), W / 2, 640)
        C.put(fr, C.text('Болеешь за', 'mont', 64, MUTED, 800), W / 2, 960)
        C.put(fr, C.text(self.T_.up + '?', 'unb', 96, ICE, 900, max_w=980), W / 2, 1060)
        C.put(fr, C.text('Это тебе', 'unb', 64, GOLD2, 800), W / 2, 1180, C.clamp((lt - 0.3) / 0.3))

    def marks(self, fr, upto, y0=330):
        for j in range(upto):
            big, small = self.facts[j]
            C.put(fr, C.text('%s  %s' % (big, small), 'mont', 34, MUTED, 700, max_w=860), W / 2, y0 + j * 56)

    def draw_fact(self, fr, lt, L, t):
        i = int(self.scenes[self.at(t)[0]]['i'])
        k = C.out_back(C.clamp(lt / 0.4), 1.3)
        C.put(fr, self.T_.emb(110), 120, 250)
        self.marks(fr, i)
        big, small = self.facts[i]
        C.put(fr, C.glow(C.scale(C.text(big, 'unb', 230, GOLD, 900, max_w=980), 0.7 + 0.3 * k), 26, 0.7, GOLD),
              W / 2, 800, C.clamp(lt / 0.15))
        C.put(fr, C.lines(small, 'mont', 62, 940, ICE, 800), W / 2, 1050, C.clamp((lt - 0.15) / 0.3))

    def draw_cta(self, fr, lt, L, t):
        a = C.clamp(lt / 0.3)
        C.put(fr, C.glow(self.T_.emb(220), 26, 0.8, self.T_.c1), W / 2, 420, a)
        self.marks(fr, len(self.facts), 590)
        C.put(fr, C.lines('Отправь тому, кто болеет за ' + self.T_.short, 'unb', 70, 960, ICE, 800), W / 2, 960, a)
        # «самолётик» один раз пролетает
        k = C.clamp((lt - 0.4) / 0.9)
        if 0 < k < 1:
            pl = C.tg_icon(110)
            C.put(fr, pl, 120 + 860 * C.in_out(k), 1170 - 140 * math.sin(k * math.pi), 1 - abs(k - 0.5) * 0.6)
        if self.note:
            C.put(fr, C.text(self.note, 'mont', 30, MUTED, 600, max_w=960), W / 2, 1260, a)


# ───────────────────────────── 5. «Серия» — прогноз с крючком ─────────────────────────────
class Series(V3):
    """n — число в крючке, label — подпись, dots: [строки счёта] (n штук), bet, kef, match — «сегодня · 15:00 · …»."""

    def __init__(self, scenes, team_name, n, label, dots, bet, kef, match, **kw):
        self.n, self.label, self.dots, self.bet, self.kef, self.match = n, label, dots, bet, kef, match
        super().__init__(scenes, **kw)
        self.T_ = team(team_name, self.league)
        self.tint = self.T_.c1
        self.cover_t = 0.5

    def row(self, fr, filled, y=900, pulse=0.0, last=None):
        cnt = len(self.dots) + 1
        step = min(130, 960 / cnt)
        x0 = W / 2 - step * (cnt - 1) / 2
        for j in range(cnt):
            x = x0 + j * step
            r = int(step * 0.36)
            if j < len(self.dots):
                hits = getattr(self, 'hits', None)
                if j < filled:
                    C.put(fr, C.ellipse(2 * r, 2 * r, GOLD if not hits or hits[j] else (70, 76, 86)), x, y)
                    C.put(fr, C.text(self.dots[j], 'mont', 26, MUTED, 700), x, y + r + 34)
                else:
                    C.put(fr, C.ellipse(2 * r, 2 * r, LINE0), x, y)
            else:
                if last is not None:
                    C.put(fr, last, x, y)
                else:
                    rr = r * (1 + 0.15 * pulse)
                    ring = C.ellipse(int(2 * rr), int(2 * rr), MUTED)
                    hole = C.ellipse(int(2 * rr) - 10, int(2 * rr) - 10, BG)
                    C.put(ring, hole, ring.width / 2, ring.height / 2)
                    C.put(fr, ring, x, y)
                    C.put(fr, C.text('?', 'unb', int(r), MUTED, 800), x, y)

    def draw_hook(self, fr, lt, L, t):
        k = C.out_cubic(C.clamp(lt / 0.5))
        C.put(fr, C.glow(C.scale(C.text(str(self.n), 'unb', 520, GOLD, 900), 1.06 - 0.06 * k), 40, 0.9, GOLD), W / 2, 700)
        C.put(fr, C.lines(self.label, 'mont', 64, 940, ICE, 800), W / 2, 1070)
        who = getattr(self, 'dot_team', None)
        C.put(fr, C.text(team(who, self.league).up if who else self.T_.up, 'unb', 52, MUTED, 800, max_w=900), W / 2, 380)

    def draw_dots(self, fr, lt, L, t):
        C.put(fr, C.text(str(self.n), 'unb', 200, GOLD, 900), W / 2, 450)
        C.put(fr, C.lines(self.label, 'mont', 44, 900, ICE, 800), W / 2, 620)
        per = max(0.2, min(0.4, (L - 0.3) / max(1, len(self.dots))))
        self.row(fr, int(lt / per) + 1)

    def draw_empty(self, fr, lt, L, t):
        C.put(fr, self.T_.emb(260), W / 2, 470)
        C.put(fr, C.text(self.match, 'mont', 40, MUTED, 700, max_w=960), W / 2, 660)
        self.row(fr, len(self.dots), pulse=0.5 + 0.5 * math.sin(lt * 7))
        C.put(fr, C.text(getattr(self, 'today', 'Сегодня — ещё один?'), 'unb', 62, ICE, 800, max_w=980), W / 2, 1150)

    def draw_bet(self, fr, lt, L, t):
        k = C.out_back(C.clamp(lt / 0.4), 1.4)
        self.row(fr, len(self.dots), y=380, last=C.scale(self.T_.emb(110), max(0.05, k)))
        C.put(fr, C.text('НАШ ПРОГНОЗ', 'mont', 40, GOLD, 800, track=0.16), W / 2, 600, C.clamp(lt / 0.2))
        C.put(fr, C.glow(self.T_.emb(250), 24, 0.6, self.T_.c1), W / 2, 790, C.clamp(lt / 0.25))
        C.put(fr, C.lines(self.bet, 'unb', 70, 960, ICE, 800), W / 2, 1010, C.clamp((lt - 0.1) / 0.3))
        kim = sheen(C.text('кэф ' + C.fmt_k(self.kef).replace('.', ','), 'unb', 92, GOLD, 900), C.clamp((lt - 0.6) / 0.7))
        C.put(fr, kim, W / 2, 1200, C.clamp((lt - 0.3) / 0.3))
