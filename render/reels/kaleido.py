# -*- coding: utf-8 -*-
"""«Калейдоскоп» — психоделическая мандала (трек «XPERIENCE», 60 BPM): весь кадр — зеркальный калейдоскоп
из цветов клуба и осколков его эмблемы (6 зеркал, на дропе — 8), он вращается щелчками на каждую долю
и пересобирается (узор «перетекает» за полдоли). Факты — на чистых «стеклянных» плашках (под стеклом узор
размыт и притушен, текст читается), эмблема клуба — в «глазу» мандалы. Не жидкость (liquid.py) и не частицы
(particles.py): узор строится зеркальной выборкой из текстуры (полярные координаты, складка по сектору).

Сцены (u — доля трека, D — дроп; доли считаются от дропа, team / pre / hold / cta — параметры):
  интро (до D − (2·team + pre) долей) — сам матч: обе эмблемы зеркально по сторонам от глаза мандалы в стеклянных
                 кругах, названия и «хозяева / гости», сверху лига, день и время МСК; ниже — линия основного
                 времени П1 · Х · П2 крупными стеклянными плашками. Мандала — смесь цветов обоих клубов;
  команда (team долей) ×2 — на первой доле калейдоскоп «поворачивается»: сектора по одному перекрашиваются
                 в палитру клуба, узор доворачивается на сектор. Эмблема в глазу, название, «хозяева / гости»;
                 стеклянная панель: последние 3 игры (по строке на полдоли с 1-й доли: В/П, соперник с эмблемой,
                 дата, дома / в гостях, счёт, ОТ/Б), затем плитки по ряду на полдоли: очки за N матчей, место,
                 разница шайб; серия, большинство, меньшинство — только если такие цифры есть;
  разгон (pre долей) — смесь цветов, узор закручивается в спиральный тоннель и ускоряется, обе эмблемы кружат
                 вокруг глаза, названия клубов внизу перемигиваются на половинах долей (в последней доле — на четвертях);
  ДРОП (hold долей) — ровно на дропе вспышка и щелчок: мандала распускается в идеально симметричный цветок
                 (8 зеркал, лепестки из глаза) вокруг ОДНОЙ эмблемы — команды прогноза; «ПОБЕДА / КЛУБ»,
                 «В ОСНОВНОЕ ВРЕМЯ» (form.split_pick) и кэф; на каждую долю — дыхание лепестков;
  финал (cta долей) — всё поднимается, снизу плашка Telegram (C.tg_plate, текст по центру плашки).
lag — на сколько долей настоящий удар баса позже точки дропа, которую передаёт сборка (xperience: точка 17,79 с,
удар 808 — 18,03 с): видимый дроп self.drop = drop + lag·u, прогноз и все доли встают на сетку баса.
@jarvibet — у низа безопасной зоны (y 1448), одинаково во всех сценах до плашки Telegram.
Кадр — чистая функция t: текстуры, стекло, плашки и полярные поля кешируются на уровне модуля (до fork — общие);
мандала считается в 540×960 и масштабируется.
"""
import colorsys
import math
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels.core import W, H

SW, SH = 540, 960                 # мандала считается в половинном размере
KS = W / SW
TS = 1800                         # текстура-«начинка» калейдоскопа (вдвое плотнее выборки — без «лесенки»)
TK = TS / 900.0
WHITE = (255, 255, 255)
INK = (12, 6, 22)
GRAY = (200, 192, 222)
NIGHT = (24, 8, 44)               # глубокий фиолетовый (база психоделики)
EYE = (540.0, 585.0)              # глаз мандалы (центр симметрии)
EYE_CTA = (540.0, 470.0)
TAG_Y, HY = 262, 1448
PX, PY, PW = 60, 772, 960         # стеклянная панель фактов
ROW_H, ROW_G = 92, 10
TILE_H, TILE_G = 122, 14
_TEX, _POL, _MSK, _SPR = {}, {}, {}, {}


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def pct(v):
    try:
        return ('%.1f' % float(v)).rstrip('0').rstrip('.').replace('.', ',') + '%'
    except (TypeError, ValueError):
        return None


def _hsv(c):
    return colorsys.rgb_to_hsv(*(x / 255 for x in c))


def _rgb(h, s, v):
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h % 1.0, C.clamp(s), C.clamp(v)))


def vivid(c, s_min=0.72, v_min=0.92):
    h, s, v = _hsv(c)
    return _rgb(h, max(s, s_min) if s > 0.12 else s, max(v, v_min))


def _chroma(c):
    return (max(c) - min(c)) / 255


def palette(team):
    """Палитра клуба для калейдоскопа: основной, второй, светлый блик, глубокий дополнительный, тёмная база."""
    cand = [c for c in (team.c1, team.c0, team.c2) if _chroma(c) > 0.2]
    main = vivid(cand[0]) if cand else (235, 235, 245)
    h, s, v = _hsv(main)
    sec = None
    for c in cand[1:]:
        cv = vivid(c)
        if sum((a - b) ** 2 for a, b in zip(cv, main)) ** 0.5 > 90:
            sec = cv
            break
    if sec is None:
        sec = _rgb(h + 0.09, 0.8, 1.0)
    return dict(main=main, sec=sec, glow=_rgb(h - 0.03, 0.42, 1.0), comp=_rgb(h + 0.52, 0.72, 0.62),
                deep=_rgb(h + 0.5, 0.8, 0.28), dark=C.mix(NIGHT, _rgb(h, 0.9, 0.3), 0.25))


def pal_text(p):
    """Цвет имени клуба на тёмном стекле — светлый вариант основного."""
    return C.mix(p['main'], WHITE, 0.22)


# ─────────────────────────────── текстура и выборка ───────────────────────────────
def texture(key, pals, embs, seed):
    """Начинка калейдоскопа (TS×TS): градиент, мягкие пятна, полосы, ромбы, кольца, осколки эмблем, точки."""
    if key in _TEX:
        return _TEX[key]
    rnd = np.random.default_rng(seed)
    ss = 2
    S = TS * ss
    p0, p1 = pals[0], pals[-1]
    base = C.lgrad(600, 600, p0['dark'], C.mix(p1['deep'], NIGHT, 0.35), angle=35.0).resize((S, S), Image.BILINEAR)
    im = base.copy()
    d = ImageDraw.Draw(im)

    def col(i, k):
        p = pals[i % len(pals)]
        return [p['main'], p['sec'], p['glow'], p['comp'], WHITE, p['main']][k % 6]

    # мягкие пятна света
    for i in range(9):
        r = int(rnd.uniform(0.12, 0.3) * S)
        c = col(i, int(rnd.integers(0, 4)))
        C.put(im, C.radial(2 * r, 2 * r, c, int(rnd.uniform(120, 220)), 1.4), rnd.uniform(0, S), rnd.uniform(0, S))
    d = ImageDraw.Draw(im)
    # полосы
    for i in range(10):
        x, y = rnd.uniform(0, S), rnd.uniform(0, S)
        ang = rnd.uniform(0, math.pi)
        L = rnd.uniform(0.4, 1.0) * S
        wd = int(rnd.uniform(0.012, 0.05) * S)
        c = col(i + 1, int(rnd.integers(0, 6)))
        d.line((x - L * math.cos(ang), y - L * math.sin(ang), x + L * math.cos(ang), y + L * math.sin(ang)),
               fill=tuple(c) + (int(rnd.uniform(150, 255)),), width=wd)
    # ромбы и треугольники
    for i in range(22):
        x, y = rnd.uniform(0, S), rnd.uniform(0, S)
        r = rnd.uniform(0.03, 0.11) * S
        n = int(rnd.choice([3, 4, 4, 6]))
        a0 = rnd.uniform(0, 2 * math.pi)
        st = rnd.uniform(0.55, 1.0)
        pts = [(x + r * (st if k % 2 and n == 4 else 1) * math.cos(a0 + 2 * math.pi * k / n),
                y + r * (st if k % 2 and n == 4 else 1) * math.sin(a0 + 2 * math.pi * k / n)) for k in range(n)]
        c = col(i, int(rnd.integers(0, 6)))
        d.polygon(pts, fill=tuple(c) + (int(rnd.uniform(170, 255)),))
    # кольца
    for i in range(16):
        x, y = rnd.uniform(0, S), rnd.uniform(0, S)
        r = rnd.uniform(0.03, 0.16) * S
        wd = int(rnd.uniform(0.006, 0.025) * S)
        c = col(i + 2, int(rnd.integers(0, 6)))
        d.ellipse((x - r, y - r, x + r, y + r), outline=tuple(c) + (255,), width=wd)
    im = im.resize((TS, TS), Image.LANCZOS)
    # осколки эмблем (резкие, с тёмной каймой)
    for i in range(4 if len(embs) == 1 else 6):
        e = embs[i % len(embs)]
        sz = int(rnd.uniform(0.12, 0.22) * TS)
        em = C.fit(e, sz, sz)
        em = em.rotate(float(rnd.uniform(0, 360)), Image.BICUBIC, expand=True)
        C.put(im, C.shadow(em, 6, 0.6, NIGHT), rnd.uniform(0.1, 0.9) * TS, rnd.uniform(0.1, 0.9) * TS)
        C.put(im, em, rnd.uniform(0.1, 0.9) * TS, rnd.uniform(0.1, 0.9) * TS)
    d = ImageDraw.Draw(im)
    for i in range(140):                                   # искры
        x, y = rnd.uniform(0, TS), rnd.uniform(0, TS)
        r = rnd.uniform(1.5, 4.5) * TK
        c = col(i, int(rnd.integers(2, 5)))
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(c) + (230,))
    arr = np.ascontiguousarray(np.asarray(im.convert('RGB'), np.uint8).reshape(-1, 3))
    _TEX[key] = arr
    return arr


def polar(cx, cy, keep=False):
    """Полярные поля мандалы (в координатах 540×960): r, угол, ln r, свет к глазу."""
    key = (round(cx, 1), round(cy, 1))
    if key in _POL:
        return _POL[key]
    ys, xs = np.mgrid[0:SH, 0:SW].astype(np.float32)
    dx, dy = xs + 0.5 - cx / KS, ys + 0.5 - cy / KS
    r = np.sqrt(dx * dx + dy * dy)
    th = np.arctan2(dy, dx).astype(np.float32)
    lr = np.log(r + 6.0).astype(np.float32)
    prof = (0.7 + 0.5 * np.exp(-r / 260.0)).astype(np.float32)
    rc = (np.power(r + 1.0, 0.8) * 150.0 ** 0.2).astype(np.float32)     # дальние кольца плотнее — узор мельче к краям
    out = (r, th, lr, prof, rc)
    if keep:
        _POL[key] = out
    return out


def mask(kind, *args):
    """Маски стекла (L) и обводки (RGBA) — кеш."""
    key = (kind,) + args
    if key in _MSK:
        return _MSK[key]
    if kind == 'rr':
        w, h, r = args
        im = C.rrect(w, h, r, WHITE).getchannel('A')
    elif kind == 'circ':
        (d,) = args
        im = C.ellipse(d, d, WHITE).getchannel('A')
    elif kind == 'rr_edge':
        w, h, r, col = args
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        sheen = C.lgrad(w, h, (255, 255, 255), (255, 255, 255), 90, 40, 0)
        sheen.putalpha(Image.fromarray((np.asarray(sheen.getchannel('A'), np.float32) *
                                        (np.arange(h)[:, None] < h * 0.45)).astype(np.uint8)))
        m = C.rrect(w, h, r, WHITE).getchannel('A')
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        sh.paste(sheen, (0, 0), m)
        im.alpha_composite(sh)
        im.alpha_composite(C.rrect(w, h, r, None, outline=col, width=3))
    elif kind == 'circ_edge':
        d, col, wd = args
        S = d + 60
        ring = Image.new('RGBA', (S * 3, S * 3), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((90, 90, S * 3 - 91, S * 3 - 91), outline=tuple(col) + (255,), width=wd * 3)
        ring = ring.resize((S, S), Image.LANCZOS)
        im = C.glow(ring, 10, 1.1, col)
    _MSK[key] = im
    return im


class Kaleido(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=1.0, drop=17.0, line=None, team=6, pre=2, hold=4,
                 cta=2.5, lag=0.0, fold=6, seed=41, **kw):
        """Сцены: интро → команда (team долей) ×2 → разгон (pre) → дроп-прогноз (hold) → Telegram (cta); доли — от дропа."""
        super().__init__(u, drop + lag * u, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.line = league, when, coef, line
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.other = 'a' if self.side == 'h' else 'h'
        self.fav = self.h if self.side == 'h' else self.a
        self.raw = {'h': sh or {}, 'a': sa or {}}
        self.st = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.fold = fold
        self.t1 = self.b(-(2 * team + pre))
        self.t2 = self.b(-(team + pre))
        self.tp = self.b(-pre)
        if self.t1 < 1.5:
            raise ValueError('мало времени до дропа')
        self.t_cta = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = round(max(1.4, self.t1 - 0.6), 2)
        self._prep()

    # ── заготовки ──
    def _prep(self):
        self.pal = {'h': palette(self.h), 'a': palette(self.a)}
        P = self.pal
        self.cf = P[self.side]['main']
        nm = (self.h.name, self.a.name, self.seed)
        self.tex = {
            'h': texture(('h',) + nm, [P['h']], [self.h.emb(420)], self.seed + 1),
            'a': texture(('a',) + nm, [P['a']], [self.a.emb(420)], self.seed + 2),
            'mix': texture(('mix',) + nm, [P['h'], P['a']], [self.h.emb(420), self.a.emb(420)], self.seed + 3),
        }
        polar(*EYE, keep=True)
        polar(*EYE_CTA, keep=True)
        lab_c = (236, 226, 255)
        # общее
        self.tag = self._pill(C.text(F.tag(self.league), 'unb', 30, (232, 224, 250), 700, track=0.12), 52)
        hd = C.text(C.HANDLE, 'unb', 40, WHITE, 600)
        pl = C.rrect(hd.width + 64, 70, 35, INK, 150)
        C.put(pl, hd, pl.width / 2, 35)
        self.handle_im = pl
        self.date = C.text('%s · %s' % (F.lg_ru(self.league), self.when), 'unb', 42, WHITE, 700, max_w=980)
        self.date_pl = self._pill(self.date, 84)
        # интро
        self.i_emb = {s: C.with_shadow(t.emb(232), 14, 0.55, 8) for s, t in (('h', self.h), ('a', self.a))}
        self.i_name = {s: C.text(t.up, 'unb', 54, pal_text(P[s]), 800, max_w=440) for s, t in (('h', self.h), ('a', self.a))}
        self.i_role = {s: C.text('ХОЗЯЕВА' if s == 'h' else 'ГОСТИ', 'mont', 30, lab_c, 800, track=0.3) for s in 'ha'}
        self.odds = None
        if self.line:
            self.odds = C.odds_row(self.line, 980, 232, font='unb', lab_font='mont', fill=WHITE, fill_a=14, val_col=WHITE,
                                   lab_col=lab_c, outline=C.mix(P['h']['main'], P['a']['main'], 0.5), radius=40, gap=24)
            self.odds_lab = self._pill(C.text('ОСНОВНОЕ ВРЕМЯ', 'mont', 32, lab_c, 800, track=0.25), 60)
        # команды
        self.T = {k: self._team_data(k) for k in ('h', 'a')}
        # разгон
        self.r_emb = {s: C.with_shadow(t.emb(190), 12, 0.6, 6) for s, t in (('h', self.h), ('a', self.a))}
        self.r_name = {}
        for s, t in (('h', self.h), ('a', self.a)):
            self.r_name[s] = (C.text(t.up, 'unb', 70, WHITE, 800, max_w=700),
                              C.text(t.up, 'unb', 70, (150, 140, 175), 800, max_w=700))
        self.jumps = self._jumps()
        # прогноз
        pf = P[self.side]
        self.p_emb = C.with_shadow(self.fav.emb(300), 16, 0.6, 10)
        m = re.match(r'(ПОБЕДА)\s+(.+)$', self.pick1)
        self.p_l1 = C.text(m.group(1), 'unb', 60, WHITE, 800, track=0.1) if m else None
        self.p_l2 = C.glow(C.text(m.group(2) if m else self.pick1, 'unb', 112, pal_text(pf), 900, max_w=900), 14, 0.7, pf['main'])
        self.p_l3 = C.text(self.pick2, 'mont', 42, lab_c, 800, track=0.16, max_w=880) if self.pick2 else None
        self.kef = None
        if self.coef:
            kt = C.text('КЭФ ' + C.fmt_k(self.coef), 'unb', 64, WHITE, 900, track=0.04)
            kp = C.rrect(kt.width + 120, 116, 58, C.mix(pf['main'], INK, 0.35), outline=C.mix(pf['main'], WHITE, 0.35), width=4)
            C.put(kp, kt, kp.width / 2, 58)
            self.kef = C.glow(kp, 18, 0.9, pf['main'])
        self.tg = C.tg_plate(960, 172, font='unb')

    def _pill(self, im, h):
        pl = C.rrect(im.width + 70, h, h / 2, INK, 170)
        C.put(pl, im, pl.width / 2, h / 2)
        return pl

    def _game_row(self, g, p):
        w, h = PW - 60, ROW_H
        im = C.rrect(w, h, 24, WHITE, 16)
        C.put(im, F.chip(g['res'], 64), 22 + 32, h / 2)
        x = 22 + 64 + 18
        oe = None
        if g.get('opp_key'):
            try:
                oe = C.Team(g['opp_key']).emb(62)
            except Exception:
                oe = None
        if oe is not None:
            C.put(im, oe, x + 31, h / 2)
            x += 62 + 16
        sc = C.text(g['score'], 'unb', 52, WHITE, 800)
        nt = C.text(g['note'], 'mont', 30, GRAY, 800) if g['note'] else None
        right = w - 24
        C.put(im, sc, right - sc.width, h / 2 - sc.height / 2, anchor='tl')
        rx = right - sc.width - 14
        if nt is not None:
            C.put(im, nt, rx - nt.width, h / 2 + sc.height / 2 - nt.height, anchor='tl')
            rx -= nt.width + 14
        room = rx - x - 10
        nm = C.text(g['opp'].upper(), 'mont', 38, WHITE, 800, max_w=room)
        sub = ' · '.join(z for z in (g['date'], 'дома' if g.get('home') else 'в гостях' if g.get('home') is False else '') if z)
        C.put(im, nm, x, 14, anchor='tl')
        if sub:
            C.put(im, C.text(sub, 'mont', 26, GRAY, 600, max_w=room), x, 58, anchor='tl')
        return im

    def _facts(self, key):
        s, rec = self.st[key], self.raw[key]
        out = []
        if s['points'] is not None:
            sub = ('за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей'))) if s['gp'] is not None else ''
            out.append(('ОЧКИ', '%d' % s['points'], sub, WHITE))
        if s['place'] is not None:
            out.append(('МЕСТО', '%d' % s['place'], s['place_scope'], WHITE))
        if s['gd'] is not None:
            out.append(('РАЗНИЦА ШАЙБ', F.gd_txt(s['gd']), '', F.WIN if s['gd'] > 0 else F.LOSS if s['gd'] < 0 else WHITE))
        m = re.match(r'\s*(ОТ|В|П)\s*(\d+)', str(rec.get('streak') or ''))
        if m and int(m.group(2)) >= 2:
            n = int(m.group(2))
            word = {'В': plural(n, 'победа', 'победы', 'побед'), 'П': plural(n, 'поражение', 'поражения', 'поражений'),
                    'ОТ': plural(n, 'поражение', 'поражения', 'поражений') + ' в ОТ'}[m.group(1)]
            out.append(('СЕРИЯ', '%d' % n, word + ' подряд', F.WIN if m.group(1) == 'В' else F.LOSS))
        for k, lab in (('pp', 'БОЛЬШИНСТВО'), ('pk', 'МЕНЬШИНСТВО')):
            v = pct(rec.get(k)) if rec.get(k) is not None else None
            if v:
                out.append((lab, v, '', WHITE))
        return out[:6]

    def _tile(self, w, lab, val, sub, vcol):
        h = TILE_H
        im = C.rrect(w, h, 24, WHITE, 16)
        C.put(im, C.text(lab, 'mont', 24, GRAY, 800, track=0.12, max_w=w - 28), w / 2, 28)
        v = C.text(val, 'unb', 52, vcol, 800, max_w=w - 28)
        if sub:
            sb = C.lines(sub, 'mont', 25, max(60, w - v.width - 44), GRAY, 700, gap=0.02, align='l', max_lines=2)
            tot = v.width + 12 + sb.width
            if tot > w - 24:
                sb = C.fit(sb, max(10, w - 24 - v.width - 12), sb.height)
                tot = v.width + 12 + sb.width
            x = (w - tot) / 2
            yc = 82
            C.put(im, v, x, yc - v.height / 2, anchor='tl')
            C.put(im, sb, x + v.width + 12, yc - sb.height / 2 + 2, anchor='tl')
        else:
            C.put(im, v, w / 2, 82)
        return im

    def _team_data(self, key):
        tm = self.h if key == 'h' else self.a
        p = self.pal[key]
        s = self.st[key]
        rows = [self._game_row(g, p) for g in s['games'][:3]]
        facts = self._facts(key)
        tiles = []                                           # (img, x центра, ряд)
        nrow = (len(facts) + 2) // 3
        inner = PW - 60
        for r in range(nrow):
            part = facts[3 * r:3 * r + 3]
            n = len(part)
            w = int((inner - TILE_G * (n - 1)) / n)
            for i, f in enumerate(part):
                tiles.append((self._tile(w, *f), PX + 30 + i * (w + TILE_G) + w / 2, r))
        ph = 28 + len(rows) * ROW_H + max(0, len(rows) - 1) * ROW_G + (24 if rows and tiles else 0) + \
            nrow * TILE_H + max(0, nrow - 1) * TILE_G + 28
        name = C.text(tm.up, 'unb', 86, pal_text(p), 900, max_w=900)
        role = C.text('ХОЗЯЕВА' if key == 'h' else 'ГОСТИ', 'mont', 30, WHITE, 800, track=0.32)
        rp = C.rrect(role.width + 64, 54, 27, C.mix(p['main'], INK, 0.45), outline=p['main'], width=3)
        C.put(rp, role, rp.width / 2, 27)
        return dict(tm=tm, p=p, rows=rows, tiles=tiles, nrow=nrow, ph=int(ph), name=name, role=rp,
                    emb=C.with_shadow(tm.emb(210), 12, 0.55, 8))

    def _jumps(self):
        """Подсветка названий на разгоне: половины долей, в последней доле — четверти; последняя — на прогноз."""
        D, u, pre = self.drop, self.u, int(round((self.drop - self.tp) / self.u))
        ts = [D - pre * u + 0.5 * u * i for i in range(max(0, 2 * (pre - 1)))]
        ts += [D - u + 0.25 * u * i for i in range(4)]
        n = len(ts)
        return [(tj, self.other if (n - 1 - i) % 2 == 0 else self.side) for i, tj in enumerate(ts)]

    # ── мандала ──
    def _bp(self, k):
        rng = np.random.default_rng(self.seed * 7919 + int(k) + 100000)
        return (rng.uniform(0.3, 0.7) * TS, rng.uniform(0.3, 0.7) * TS, rng.uniform(0, 2 * math.pi), rng.uniform(0.62, 0.95))

    def turns(self, t):
        """(текстура до, текстура после, доля перекрашенных секторов, сколько поворотов позади + текущий)."""
        seq = [(self.t1, 'mix', 'h'), (self.t2, 'h', 'a'), (self.tp, 'a', 'mix')]
        done = 0.0
        cur = ('mix', None, 0.0)
        for t0, a, b in seq:
            if t >= t0:
                k = C.in_out(C.seg(t, t0, t0 + 0.6 * self.u))
                done = done + k if k < 1 else done + 1
                cur = (a, b, k) if k < 1 else (b, None, 0.0)
        return cur[0], cur[1], cur[2], done

    def params(self, t):
        D, u = self.drop, self.u
        q = (t - D) / u
        k = math.floor(q)
        f = q - k
        if t < D:
            N = self.fold
            w = 2 * math.pi / N
            a0, a1 = self._bp(k - 1), self._bp(k)
            e = C.out_cubic(f / 0.55)
            ox, oy, phi, zs = (C.lerp(x, y, e) for x, y in zip(a0, a1))
            ox += 30 * math.sin(t * 0.7)
            oy += 30 * math.cos(t * 0.53)
            ta, tb, kseg, done = self.turns(t)
            rot = 0.1 * t + 0.5 * w * (k + C.out_expo(f / 0.45)) + w * done
            twist = tun = tph = 0.0
            gain = 0.86
            if t < self.t1:
                gain = 0.9
            elif t < self.tp:
                gain = 0.8
            else:
                qp = C.seg(t, self.tp, D)
                tun = 0.92 * C.out_cubic(qp * 2.2)
                twist = 2.4 * C.in_cubic(qp)
                tph = 0.7 * (t - self.tp) + 3.2 * qp ** 3
                rot += 3.5 * qp ** 3
                zs *= 1 + 0.6 * qp
                gain = 0.95
            return dict(c=EYE, N=N, rot=rot, zs=zs, ox=ox, oy=oy, phi=phi, twist=twist, tun=tun, tph=tph, ta=ta, tb=tb,
                        kseg=kseg, gain=gain, seam=0.5)
        # дроп: идеальная симметрия вокруг эмблемы прогноза
        N = 8
        w = 2 * math.pi / N
        dt = t - D
        bloom = C.out_expo(C.seg(dt, 0.0, 0.7 * u))
        zs = 0.72 * (1 + 2.6 * (1 - bloom)) * (1 - 0.035 * self.pulse(t))
        rot = 0.12 * dt + 0.25 * w * (max(0, k) + C.out_expo(f / 0.4)) - 0.9 * (1 - bloom)
        kc = C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.5 * u))
        c = (C.lerp(EYE[0], EYE_CTA[0], kc), C.lerp(EYE[1], EYE_CTA[1], kc))
        return dict(c=c, N=N, rot=rot, zs=zs, ox=TS * 0.5, oy=TS * 0.5, phi=0.35, twist=0.0, tun=0.0, tph=0.0, ta=self.side,
                    tb=None, kseg=0.0, gain=0.82 + 0.18 * self.pulse(t), seam=0.7)

    def pulse(self, t):
        if t < self.drop:
            return 0.0
        return math.exp(-(((t - self.drop) / self.u) % 1.0) * 6)

    def mandala(self, t):
        p = self.params(t)
        cx, cy = p['c']
        r, th0, lr, prof, rc = polar(cx, cy)
        th = th0 + p['twist'] * (lr - 2.0) if p['twist'] else th0
        N = p['N']
        w = 2 * math.pi / N
        rel = np.mod(th - p['rot'], 2 * math.pi)
        f = np.mod(rel, w)
        m = np.minimum(f, w - f)
        rs = rc * (p['zs'] * TK)
        if p['tun'] > 0:
            ring = np.mod(lr * 1.35 - p['tph'], 1.0)
            rs = rs * (1 - p['tun']) + (TS * 0.06 + ring * TS * 0.4) * p['tun']
        ang = m + p['phi']
        sx = p['ox'] + rs * np.cos(ang)
        sy = p['oy'] + rs * np.sin(ang)
        L = TS - 1
        sx = L - np.abs(np.mod(sx, 2 * L) - L)
        sy = L - np.abs(np.mod(sy, 2 * L) - L)
        idx = sy.astype(np.int32) * TS + sx.astype(np.int32)
        img = self.tex[p['ta']].take(idx, axis=0)
        if p['tb'] is not None and p['kseg'] > 0:
            segi = (rel / w).astype(np.int32)
            sel = segi < p['kseg'] * N
            img = np.where(sel[..., None], self.tex[p['tb']].take(idx, axis=0), img)
        gain = prof * p['gain']
        if t < 0.7:                                          # раскрытие из глаза в начале
            rev = 1500 * C.out_cubic(C.seg(t, 0.0, 0.7)) / KS
            gain = gain * np.clip((rev - r) / 40.0, 0, 1)
        out = img.astype(np.float32) * gain[..., None]
        # зеркальные швы — тонкие светлые линии стекла
        dseam = r * np.minimum(m, w * 0.5 - m)
        seam = np.clip(1.0 - dseam * 0.6, 0, 1) * (p['seam'] * np.clip(r / 40.0, 0, 1))
        if t < 0.7:
            seam = seam * np.clip((rev - r) / 40.0, 0, 1)
        out += seam[..., None] * np.array([255, 240, 255], np.float32)[None, None, :] * 0.55
        if t >= self.drop:
            out = self.bloom(out, t, r, th0, p)
        return np.clip(out, 0, 255).astype(np.uint8)

    def bloom(self, out, t, r, th, p):
        """Лепестки из глаза на дропе: три яруса контуров, раскрываются за 0,7 доли и дышат на долях."""
        dt = t - self.drop
        e = C.out_expo(C.seg(dt, 0.0, 0.7 * self.u))
        br = 1 + 0.05 * self.pulse(t)
        pf = self.pal[self.side]
        rot = p['rot'] * 0.5
        lay = np.zeros(r.shape, np.float32)
        acc = None
        for n, R, wd, col, k in ((8, 330, 5.0, pf['glow'], 1.0), (16, 250, 3.5, WHITE, 0.85), (8, 480, 4.5, pf['sec'], 0.8), (12, 640, 4.0, pf['glow'], 0.6)):
            A = np.abs(np.cos((th - rot) * (n / 2.0)))
            bound = (R * e * br / KS) * (0.42 + 0.58 * A)
            edge = np.clip(1.0 - np.abs(r - bound) / wd, 0, 1) * k
            add = edge[..., None] * np.array(col, np.float32)[None, None, :]
            acc = add if acc is None else acc + add
            lay = np.maximum(lay, edge)
            rot = -rot
        fl = 1.0 - C.seg(dt, 0.0, 1.2)
        return out * (1 - 0.25 * lay[..., None]) + acc * (0.75 + 0.6 * fl)

    # ── стекло ──
    def glass(self, fr, blur, x0, y0, m, a=1.0, dark=0.36, tint=INK, tk=0.3):
        x0, y0 = int(round(x0)), int(round(y0))
        reg = blur.crop((x0, y0, x0 + m.width, y0 + m.height))
        arr = np.asarray(reg, np.float32) * dark + np.array(tint, np.float32) * tk
        g = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
        if a < 0.997:
            m = m.point(lambda v, a=a: int(v * a))
        fr.paste(g, (x0, y0), m)

    def glass_circle(self, fr, blur, cx, cy, d, col, a=1.0):
        d = int(d)
        self.glass(fr, blur, cx - d / 2, cy - d / 2, mask('circ', d), a, 0.4, INK, 0.25)
        return (mask('circ_edge', d, tuple(col), 4), cx, cy, a)

    def glass_rect(self, fr, blur, cx, cy, w, h, r, col, a=1.0, dark=0.36):
        w, h = int(w), int(h)
        self.glass(fr, blur, cx - w / 2, cy - h / 2, mask('rr', w, h, int(r)), a, dark)
        return (mask('rr_edge', w, h, int(r), tuple(col)), cx, cy, a * 0.85)

    # ── сцены: (стекло на RGB, затем слои на RGBA) ──
    def intro(self, t, a):
        g, o = [], []
        P = self.pal
        q = C.out_expo(C.seg(t, 0.1, 0.5))
        o.append((self.date_pl, W / 2, 338 + 16 * (1 - q), a * q))
        for s, sg, d0 in (('h', -1, 0.25), ('a', 1, 0.45)):
            x, y = EYE[0] + sg * 262, EYE[1]
            qe = C.out_back(C.seg(t, d0, d0 + 0.45), 1.5)
            if qe <= 0.01:
                continue
            g.append(('circ', x, y, 300, P[s]['main'], a * min(1.0, qe)))
            o.append((C.scale(self.i_emb[s], max(0.05, qe)), x, y + 4, a * min(1.0, qe * 1.4)))
            qn = C.out_expo(C.seg(t, d0 + 0.2, d0 + 0.6))
            g.append(('rect', x, 832 + 20 * (1 - qn), 470, 140, 36, P[s]['main'], a * qn, 0.32))
            o.append((self.i_name[s], x, 808 + 20 * (1 - qn), a * qn))
            o.append((self.i_role[s], x, 866 + 20 * (1 - qn), a * qn))
        if self.odds is not None:
            q3 = C.out_expo(C.seg(t, 0.8, 1.25))
            y = 1170 + 30 * (1 - q3)
            o.append((self.odds_lab, W / 2, 1002 + 20 * (1 - q3), a * q3))
            bw = (980 - 2 * 24) / 3
            for i in range(3):
                g.append(('rect', 50 + i * (bw + 24) + bw / 2, y, bw, 232, 40, None, a * q3, 0.3))
            o.append((self.odds, W / 2, y, a * q3))
        return g, o

    def team(self, t, key, t0, t_end):
        u = self.u
        T = self.T[key]
        p = T['p']
        g, o = [], []
        a = 1 - C.seg(t, t_end - 0.15, t_end)
        q = C.out_expo(C.seg(t, t0, t0 + 0.4))
        sg = 1 if key == 'h' else -1
        g.append(('rect', W / 2 + sg * 80 * (1 - q), 362, T['name'].width + 60, 116, 36, p['main'], a * q, 0.3))
        o.append((T['name'], W / 2 + sg * 80 * (1 - q), 362, a * q))
        qe = C.out_back(C.seg(t, t0 + 0.05, t0 + 0.5), 1.5)
        if qe > 0.01:
            g.append(('circ', EYE[0], EYE[1], 270, p['main'], a * min(1.0, qe)))
            bp = 1 + 0.035 * math.exp(-(((t - t0) / u) % 1.0) * 6)
            o.append((C.scale(T['emb'], max(0.05, qe) * bp), EYE[0], EYE[1] + 4, a * min(1.0, qe * 1.4)))
            o.append((T['role'], W / 2, EYE[1] + 137, a * C.seg(t, t0 + 0.25, t0 + 0.5)))
        # панель
        qp = C.out_expo(C.seg(t, t0 + 0.55 * u, t0 + 0.9 * u))
        if qp > 0.01:
            ph = T['ph']
            g.append(('rect', W / 2, PY + ph / 2 + 30 * (1 - qp), PW, ph, 40, p['main'], a * qp, 0.32))
            y = PY + 28 + 30 * (1 - qp)
            for i, im in enumerate(T['rows']):
                tr = t0 + (1.0 + 0.5 * i) * u
                if t >= tr:
                    qr = C.out_expo(C.seg(t, tr, tr + 0.35))
                    o.append((im, W / 2 + 60 * (1 - qr), y + ROW_H / 2, a * qr))
                y += ROW_H + ROW_G
            y += 24 - ROW_G
            for im, x, r in T['tiles']:
                tr = t0 + (1.0 + 0.5 * len(T['rows']) + 0.5 * r) * u
                if t >= tr:
                    qt = C.out_back(C.seg(t, tr, tr + 0.35), 1.3)
                    o.append((C.scale(im, 0.85 + 0.15 * min(1.0, qt)), x, y + r * (TILE_H + TILE_G) + TILE_H / 2,
                              a * min(1.0, C.seg(t, tr, tr + 0.15) * 1.0)))
        return g, o

    def rush(self, t):
        D, u = self.drop, self.u
        g, o = [], []
        q = C.out_expo(C.seg(t, self.tp, self.tp + 0.4))
        qp = C.seg(t, self.tp, D)
        ang0 = (t - self.tp) * 2.2 + 4.5 * qp ** 3
        rad = 260 - 30 * C.in_cubic(qp)
        cur = None
        for tj, sd in self.jumps:
            if t >= tj:
                cur = (sd, tj)
        for s, off in (('h', math.pi), ('a', 0.0)):
            an = ang0 + off
            x, y = EYE[0] + rad * math.cos(an), EYE[1] + 20 + rad * 0.58 * math.sin(an)
            hit = math.exp(-(t - cur[1]) / 0.15) if cur and cur[0] == s else 0.0
            g.append(('circ', x, y, 240, self.pal[s]['main'], q))
            o.append((C.scale(self.r_emb[s], 1 + 0.08 * hit), x, y + 3, q))
        for i, s in enumerate(('h', 'a')):
            y = 1090 + i * 160
            on = cur is not None and cur[0] == s
            g.append(('rect', W / 2, y, 860, 132, 40, self.pal[s]['main'] if on else (90, 80, 120), q, 0.3 if on else 0.42))
            o.append((self.r_name[s][0 if on else 1], W / 2, y, q))
        return g, o

    def pick(self, t):
        D, u = self.drop, self.u
        g, o = [], []
        pf = self.pal[self.side]
        kc = C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.5 * u))
        ex, ey = C.lerp(EYE[0], EYE_CTA[0], kc), C.lerp(EYE[1], EYE_CTA[1], kc)
        k = C.out_expo(C.seg(t, D, D + 0.45 * u))
        # эмблема с орбиты разгона → в глаз
        x0 = EYE[0] + (180 if self.side == 'a' else -180)
        x, y = C.lerp(x0, ex, k), ey
        s = C.lerp(0.62, 1.0, k) * (1 - 0.2 * kc) * (1 + 0.035 * self.pulse(t))
        g.append(('circ', x, y, int(360 * (1 - 0.2 * kc)), pf['main'], 1.0))
        o.append((C.scale(self.p_emb, s), x, y + 4, 1.0))
        # текст прогноза на стекле
        dy = -165 * kc
        qa = C.out_expo(C.seg(t, D + 0.05, D + 0.4))
        g.append(('rect', W / 2, 1052 + dy, 960, 480, 48, pf['main'], qa, 0.34))
        y1 = 878 + dy
        if self.p_l1 is not None:
            q1 = C.out_expo(C.seg(t, D + 0.06, D + 0.32))
            o.append((C.scale(self.p_l1, 1.4 - 0.4 * q1), W / 2, y1, min(1.0, q1 * 2)))
        q2 = C.out_expo(C.seg(t, D + 0.12, D + 0.45))
        o.append((C.scale(self.p_l2, (1.5 - 0.5 * q2) * (1 + 0.02 * self.pulse(t))), W / 2, y1 + 104, min(1.0, q2 * 2)))
        if self.p_l3 is not None:
            q3 = C.out_expo(C.seg(t, D + 0.5 * u, D + 0.85 * u))
            o.append((self.p_l3, W / 2, y1 + 200 + 20 * (1 - q3), q3))
        if self.kef is not None:
            q4 = C.out_back(C.seg(t, D + 1.0 * u, D + 1.35 * u), 1.8)
            if q4 > 0.01:
                o.append((C.scale(self.kef, 0.5 + 0.5 * q4), W / 2, y1 + 322, min(1.0, q4 * 1.5)))
        return g, o

    # ── кадр ──
    def frame(self, t):
        u, D = self.u, self.drop
        small = self.mandala(t)
        fr = Image.fromarray(small, 'RGB').resize((W, H), Image.BILINEAR)
        blur = Image.fromarray(small, 'RGB').resize((SW // 9, SH // 9), Image.BILINEAR).resize((W, H), Image.BILINEAR)
        if t < self.t1:
            g, o = self.intro(t, 1 - C.seg(t, self.t1 - 0.15, self.t1))
        elif t < self.t2:
            g, o = self.team(t, 'h', self.t1, self.t2)
        elif t < self.tp:
            g, o = self.team(t, 'a', self.t2, self.tp)
        elif t < D:
            g, o = self.rush(t)
        else:
            g, o = self.pick(t)
        edges = []
        for it in g:
            if it[-2 if it[0] == 'rect' else -1] <= 0.01:
                continue
            if it[0] == 'circ':
                _, x, y, d, col, a = it
                edges.append(self.glass_circle(fr, blur, x, y, d, col, a))
            else:
                _, x, y, w, h, r, col, a, dk = it
                e = self.glass_rect(fr, blur, x, y, w, h, r, col or (255, 255, 255), a, dk)
                if col is not None:
                    edges.append(e)
        fr = fr.convert('RGBA')
        for im, x, y, a in edges:
            C.put(fr, im, x, y, a)
        for im, x, y, a in o:
            C.put(fr, im, x, y, a)
        C.put(fr, self.tag, W / 2, TAG_Y, C.seg(t, 0.1, 0.4) * 0.95)
        ha = C.seg(t, 0.2, 0.5) * (1 - C.seg(t, self.t_cta, self.t_cta + 0.2))
        C.put(fr, self.handle_im, W / 2, HY, ha)
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.05, self.t_cta + 0.5))
            C.put(fr, self.tg, W / 2, 1356 + 50 * (1 - q), q)
        # камера: толчки на склейках, наезд на разгоне, удар на дропе, пульс на долях после дропа
        z, dx, dy, rot = 1.0, 0.0, 0.0, 0.0
        for th in (self.t1, self.t2, self.tp):
            if t >= th:
                z += 0.025 * (1 - C.seg(t, th, th + 0.35)) ** 2
        if self.tp <= t < D:
            qp = C.seg(t, self.tp, D)
            z += 0.05 * C.in_cubic(qp)
            dx += 5 * qp * math.sin(t * 71)
            dy += 5 * qp * math.cos(t * 53)
        if t >= D:
            kk = 1 - C.seg(t, D, D + 0.5)
            z += 0.08 * kk ** 2 + (0.008 * self.pulse(t) if t < self.t_cta else 0)
            sx, sy = C.shake(t, D, 22, 0.45)
            dx, dy = dx + sx, dy + sy
            rot = 1.2 * kk ** 2 * math.sin((t - D) * 36)
        fr = C.zoom(fr.convert('RGB'), z, dx=dx, dy=dy, rot=rot)
        if D <= t < D + 0.2:
            fr = C.rgb_split(fr, 14 * (1 - C.seg(t, D, D + 0.2)))
        if D - 1 / 60 <= t < D + 0.4:
            fa = 1.0 if t < D + 1 / 30 else (1 - C.seg(t, D + 1 / 30, D + 0.4)) ** 1.5
            fr = Image.blend(fr.convert('RGB'), Image.new('RGB', fr.size, C.mix(WHITE, self.cf, 0.2)), 0.85 * fa)
        fr = C.vignette(fr, 0.38)
        return C.grain(fr, t, 4)
