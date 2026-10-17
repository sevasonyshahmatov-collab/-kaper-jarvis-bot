# -*- coding: utf-8 -*-
"""«Тоннель» — полёт сквозь бесконечный неоновый тоннель (трек «XPERIENCE», 60 BPM, поздний участок — дроп 82,00 с).

Абстрактный футуристичный тоннель из светящихся колец: контуры уходят к точке схода, вдоль стен тянутся рельсы-спирали
и световые штрихи, в глубине — туман и свечение; камера летит вперёд с толчком скорости на каждую долю. В точке схода
горит эмблема клуба. Каждый факт прилетает «воротами» из глубины: кольцо-ворота несётся на камеру, факт вырастает
из точки схода по перспективе и ровно на долю встаёт читаемой плашкой-«шлюзом» (срезанные углы), ворота пролетают
мимо. Не трасса (highway — дорога) и не орбиты (orbit — планеты): только тоннель, кольца и свет.

Сцены (u — доля трека, D — дроп; доли считаются от дропа, team / pre / hold / cta — параметры):
  интро (до D − (2·team + pre) долей) — вход в тоннель: кольца-круги поочерёдно в цветах обоих клубов, обе эмблемы
                 вылетают из точки схода по сторонам, названия, «хозяева / гости», сверху лига, день и время МСК,
                 ниже — линия основного времени П1 · Х · П2 тремя крупными плашками-шлюзами (прилетают на 1-й доле);
  команда (team долей) ×2 — на первой доле «варп»: вспышка-кольцо, рывок камеры, тоннель меняет цвет и форму
                 (хозяева — шестигранник, гости — ромб); название клуба сверху, «хозяева / гости», эмблема в точке
                 схода. С половины 1-й доли каждые полдоли прилетают ворота с фактом: последние 3 игры (В/П, соперник,
                 дата, дома / в гостях, счёт, ОТ/Б), затем очки за N матчей, место, разница шайб, затем большинство,
                 меньшинство и серия (от 2 игр) — только если такие цифры есть. В конце сцены плашки пролетают мимо;
  разгон (pre долей) — тоннель белеет и сжимается (кольца вдвое чаще), скорость растёт, варп-штрихи; обе эмблемы
                 по краям точки схода, в последней доле их затягивает в растущий свет в конце тоннеля;
  ДРОП (hold долей) — ровно на дропе вылет из тоннеля в открытый свет: последние кольца проносятся мимо, вспышка,
                 огромная эмблема ТОЛЬКО выбранной команды в сиянии с лучами, «ПОБЕДА / КЛУБ», «В ОСНОВНОЕ ВРЕМЯ»
                 (form.split_pick) и кэф; на каждую долю из эмблемы расходится световое кольцо;
  финал (cta долей) — всё поднимается, снизу плашка Telegram (C.tg_plate, текст по центру плашки).
lag — на сколько долей настоящий удар трека позже точки дропа сборки (xperience 82,00 с: удар на 82,03 с).
JARVIS | NHL — у верха безопасной зоны, @jarvibet — у низа (y 1448) на одинаковой тёмной плашке во всех сценах до
плашки Telegram. Кадр — чистая функция t: путь камеры заранее проинтегрирован, фоны, плашки, свечения и поля
кешируются на уровне модуля (до fork — общие для процессов); неон рисуется линиями, ореол — размытием в 1/4.
"""
import colorsys
import math
import re

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels.core import W, H

WHITE = (255, 255, 255)
INK = (6, 8, 20)
GRAY = (168, 178, 200)
PRE_C = (200, 228, 255)                    # белый неон разгона
TAG_Y, HY = 262, 1448
VP_INTRO, VP_TEAM, VP_PRE, VP_PICK = (540, 690), (540, 606), (540, 790), (540, 600)
FOC = 600.0                                # фокус проекции (px на единицу радиуса тоннеля)
ASP = 1.32                                 # тоннель вытянут по вертикали (кадр 9:16)
Z0, SPAN, GAP = 0.36, 12.0, 0.6            # ближняя глубина, длина видимого тоннеля, шаг колец
NP = 48                                    # точек на контур
ROW_W = 960
GAME_Y = (826, 940, 1054)
STAT_Y, EXT_Y = 1192, 1342
_BG, _SPR = {}, {}


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def neon(c, v_min=0.95, s_min=0.6):
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    s = min(0.92, max(s, s_min)) if s > 0.12 else s
    v = max(v, v_min)
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, s, v))


def deep(c, v=0.32, s_k=1.0):
    h, s, _ = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, min(1, s * s_k), v))


def colorful(t):
    cand = [c for c in (t.c1, t.c0, t.c2) if (max(c) - min(c)) / 255 > 0.2 and 30 < 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] < 235]
    out = []
    for c in cand:
        n = neon(c)
        if all(sum((a - b) ** 2 for a, b in zip(n, o)) ** 0.5 > 90 for o in out):
            out.append(n)
    return out or [neon(t.c1)]


def pct(v):
    try:
        return ('%.1f' % float(v)).rstrip('0').rstrip('.').replace('.', ',') + '%'
    except (TypeError, ValueError):
        return None


def chamfer(w, h, c, fill=INK, a=215, outline=None, width=0, ss=3):
    """Плашка-шлюз: прямоугольник со срезанными углами (c — срез), стекло + неоновый контур."""
    W2, H2, c2 = w * ss, h * ss, c * ss
    pts = [(c2, 0), (W2 - c2, 0), (W2 - 1, c2), (W2 - 1, H2 - c2), (W2 - c2, H2 - 1), (c2, H2 - 1), (0, H2 - c2), (0, c2)]
    im = Image.new('RGBA', (int(W2), int(H2)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon(pts, fill=tuple(fill) + (a,) if fill else None)
    if outline:
        d.line(pts + [pts[0], pts[1]], fill=tuple(outline) + (255,), width=int(width * ss), joint='curve')
    return im.resize((int(w), int(h)), Image.LANCZOS)


def shape_r(n, th):
    """Радиус контура правильного n-угольника (вписанного в окружность 1) по углу th; n = 0 — круг."""
    if not n:
        return np.ones_like(th)
    seg_ = 2 * np.pi / n
    x = np.mod(th, seg_) - seg_ / 2
    return np.cos(np.pi / n) / np.cos(x)


class Tunnel(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=1.0, drop=17.0, line=None, team=6, pre=2, hold=4,
                 cta=2.5, lag=0.0, seed=31, **kw):
        """Сцены: интро → команда (team долей) ×2 → разгон (pre) → дроп-прогноз (hold) → Telegram (cta); доли — от дропа."""
        super().__init__(u, drop + lag * u, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.line = league, when, coef, line
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
        self.raw = {'h': sh or {}, 'a': sa or {}}
        self.st = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.team_n, self.pre = team, pre
        self.t1 = self.b(-(2 * team + pre))
        self.t2 = self.b(-(team + pre))
        self.tp = self.b(-pre)
        if self.t1 < 1.5:
            raise ValueError('мало времени до дропа')
        self.t_cta = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = max(1.6, self.t1 - 0.5)
        self.warps = [self.t1, self.t2, self.tp]
        self._prep()

    # ─────────────────────────── заготовки ───────────────────────────
    def _prep(self):
        ch, ca = colorful(self.h), colorful(self.a)
        hc1 = ch[0]
        far = [c for c in ca if sum((x - y) ** 2 for x, y in zip(c, hc1)) ** 0.5 > 120]
        ac1 = (far or ca)[0]
        hc2 = next((c for c in ch[1:]), C.mix(hc1, WHITE, 0.45))
        ac2 = next((c for c in ca if c != ac1), C.mix(ac1, WHITE, 0.45))
        self.col = {'h': hc1, 'a': ac1}
        self.col2 = {'h': hc2, 'a': ac2}
        self.cf = self.col[self.side]
        self.cf2 = self.col2[self.side]
        # палитры сцен тоннеля: (основной, второй, форма, вращение)
        self.pal = {'intro': (hc1, ac1, 0, 0.0), 'h': (hc1, hc2, 6, 0.0), 'a': (ac1, ac2, 4, math.pi / 4),
                    'pre': (PRE_C, self.cf, 0, 0.0)}
        self.vp = {'intro': VP_INTRO, 'h': VP_TEAM, 'a': VP_TEAM, 'pre': VP_PRE}
        for k in ('intro', 'h', 'a', 'pre'):
            self._bg(k)
        self._light_bg()
        # путь камеры: скорость с толчками на доли, рывками на варпах и разгоном перед дропом
        dt = 1 / 240
        ts = np.arange(0, self.dur + 1, dt)
        v = np.array([self.speed(x) for x in ts])
        self._ts, self._trav = ts, np.concatenate([[0], np.cumsum(v[:-1]) * dt])
        rnd = np.random.default_rng(self.seed)
        self.streaks = [(rnd.uniform(0, 2 * np.pi), rnd.uniform(0.55, 0.93), rnd.uniform(0, SPAN), rnd.uniform(0.7, 1.0))
                        for _ in range(64)]
        self.dust = [(rnd.uniform(0, 2 * np.pi), rnd.uniform(0, 1), rnd.uniform(0.6, 1.4)) for _ in range(70)]
        self.th = np.linspace(0, 2 * np.pi, NP, endpoint=False)
        # общее
        self.tag = self._pill(C.text(F.tag(self.league), 'unb', 30, (205, 214, 232), 700, track=0.12), 58)
        self.handle_im = self._pill(C.text(C.HANDLE, 'unb', 38, WHITE, 600), 64)
        # интро
        self.date = C.glow(C.text('%s · %s' % (F.lg_ru(self.league), self.when), 'exo', 56, WHITE, 800, track=0.03, max_w=980),
                           10, 0.5, C.mix(hc1, ac1, 0.5))
        self.i_emb = {s: C.glow(t.emb(270), 22, 0.9, self.col[s]) for s, t in (('h', self.h), ('a', self.a))}
        self.i_name = {s: C.glow(C.text(t.up, 'exoi', 66, WHITE, 900, max_w=480), 12, 0.55, self.col[s])
                       for s, t in (('h', self.h), ('a', self.a))}
        self.i_role = {s: C.text('ХОЗЯЕВА' if s == 'h' else 'ГОСТИ', 'mont', 30, C.mix(self.col[s], WHITE, 0.45), 800, track=0.22)
                       for s in ('h', 'a')}
        self.odds_lab = C.text('ОСНОВНОЕ ВРЕМЯ', 'mont', 32, (200, 210, 230), 800, track=0.24)
        self.odds = self._odds() if self.line else []
        # команды
        self.T = {k: self._team_data(k) for k in ('h', 'a')}
        # разгон
        self.pre_emb = {s: C.glow(t.emb(200), 18, 0.8, self.col[s]) for s, t in (('h', self.h), ('a', self.a))}
        self.pre_name = {s: C.glow(C.text(t.up, 'exoi', 84, WHITE, 900, max_w=900), 12, 0.6, self.col[s])
                         for s, t in (('h', self.h), ('a', self.a))}
        # прогноз
        self.p_emb = C.glow(self.fav.emb(420), 30, 1.0, self.cf)
        self.halo = C.radial(820, 820, C.mix(self.cf, WHITE, 0.55), 235, 1.5)
        m = re.match(r'(ПОБЕДА)\s+(.+)$', self.pick1)
        self.p_l1 = C.text(m.group(1), 'exo', 62, WHITE, 800, track=0.16) if m else None
        nm = m.group(2) if m else self.pick1
        self.p_l2 = C.glow(C.text(nm, 'exoi', 128, WHITE, 900, max_w=940), 18, 0.85, self.cf)
        self.p_l3 = C.text(self.pick2, 'mont', 38, C.mix(self.cf, WHITE, 0.6), 800, track=0.14, max_w=900) if self.pick2 else None
        self.panel = chamfer(1000, 470, 46, INK, 200, C.mix(self.cf, WHITE, 0.2), 3)
        self.kef = None
        if self.coef:
            kl = C.text('КЭФ', 'mont', 40, C.mix(self.cf, WHITE, 0.55), 800, track=0.18)
            kv = C.text(C.fmt_k(self.coef), 'exo', 84, WHITE, 900)
            w = kl.width + kv.width + 130
            kp = chamfer(w, 124, 30, deep(self.cf, 0.42, 1.05), 255, C.mix(self.cf, WHITE, 0.35), 4)
            C.put(kp, kl, 50 + kl.width / 2, 62)
            C.put(kp, kv, w - 50 - kv.width / 2, 62)
            self.kef = C.glow(kp, 16, 0.8, self.cf)
        self.tg = C.tg_plate(960, 172, font='unb')

    def _pill(self, im, h):
        pl = C.rrect(im.width + 2 * h * 0.62, h, h / 2, INK, 205, outline=(70, 80, 110), width=2)
        C.put(pl, im, pl.width / 2, h / 2)
        return pl

    def _bg(self, key):
        """Фон сцены: тёмный градиент + свечение глубины в точке схода (RGB)."""
        ck = (key, self.h.name, self.a.name, self.side)
        if ck in _BG:
            return _BG[ck]
        c1, c2, _, _ = self.pal[key]
        vx, vy = self.vp[key]
        base = np.asarray(C.vgrad(W, H, [(0, (6, 7, 18)), (0.5, (3, 4, 12)), (1, (2, 2, 8))]), np.float32)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.hypot((xx - vx) / 520, (yy - vy) / 680)
        g1 = np.clip(1 - d, 0, 1) ** 2.2
        g2 = np.exp(-(d / 0.16) ** 2)
        arr = base + g1[..., None] * np.array(c1, np.float32) * 0.34 + g2[..., None] * np.array(C.mix(c1, WHITE, 0.4), np.float32) * 0.5
        if key == 'intro':
            gl = np.clip(1 - np.hypot((xx - vx + 300) / 520, (yy - vy) / 760), 0, 1) ** 2 * 0.18
            gr = np.clip(1 - np.hypot((xx - vx - 300) / 520, (yy - vy) / 760), 0, 1) ** 2 * 0.18
            arr += gl[..., None] * np.array(c1, np.float32) + gr[..., None] * np.array(c2, np.float32)
        _BG[ck] = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
        return _BG[ck]

    def _light_bg(self):
        """Открытый свет после вылета: белое ядро → светлый клубный → насыщенный → глубокий внизу; поля углов для лучей."""
        ck = ('light', self.fav.name)
        if ck in _BG:
            self.light, self.ray_th, self.ray_fall = _BG[ck]
            return
        vx, vy = VP_PICK
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.hypot((xx - vx) / 760, (yy - vy) / 900)
        stops = [(0.0, WHITE), (0.13, C.mix(self.cf, WHITE, 0.75)), (0.32, C.mix(self.cf, WHITE, 0.15)),
                 (0.62, deep(self.cf, 0.55, 1.05)), (1.0, deep(self.cf2, 0.24, 1.0)), (1.6, (4, 5, 14))]
        pos = [s[0] for s in stops]
        cols = np.array([s[1] for s in stops], np.float32)
        arr = np.stack([np.interp(d, pos, cols[:, i]) for i in range(3)], -1)
        light = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
        h2, w2 = H // 4, W // 4
        y2, x2 = np.mgrid[0:h2, 0:w2].astype(np.float32)
        th = np.arctan2((y2 * 4 - vy), (x2 * 4 - vx)).astype(np.float32)
        r = np.hypot((x2 * 4 - vx) / 700, (y2 * 4 - vy) / 800)
        fall = (np.clip(r / 0.25, 0, 1) * np.clip(1.4 - r, 0, 1) ** 1.2).astype(np.float32)
        _BG[ck] = (light, th, fall)
        self.light, self.ray_th, self.ray_fall = _BG[ck]

    def _odds(self):
        out = []
        bw, bh = 300, 232
        for lab, v in zip(('П1', 'Х', 'П2'), self.line):
            col = self.col['h'] if lab == 'П1' else self.col['a'] if lab == 'П2' else (200, 214, 240)
            pl = chamfer(bw, bh, 36, INK, 222, C.mix(col, WHITE, 0.15), 3)
            C.put(pl, C.rrect(110, 6, 3, col), bw / 2, 16)
            C.put(pl, C.text(lab, 'mont', 44, C.mix(col, WHITE, 0.35), 800, track=0.12), bw / 2, 68)
            C.put(pl, C.text(C.fmt_k(v), 'exo', 104, WHITE, 900, max_w=bw - 36), bw / 2, 158)
            out.append(C.glow(pl, 14, 0.55, col))
        return out

    # ── плашки команды ──
    def _game_plate(self, g, col):
        w, h = ROW_W, 104
        pl = chamfer(w, h, 26, INK, 218, C.mix(col, INK, 0.25), 3)
        ch = chamfer(72, 72, 16, F.res_col(g['res']), 255)
        C.put(ch, C.text(g['res'] or '?', 'exo', 46, WHITE, 900), 36, 37)
        C.put(pl, ch, 30 + 36, h / 2)
        sc = C.text(g['score'], 'exo', 66, WHITE, 900)
        nt = C.text(g['note'], 'mont', 30, GRAY, 800) if g['note'] else None
        xr = w - 34
        if nt is not None:
            C.put(pl, nt, xr - nt.width, h / 2 + 22 - nt.height, anchor='tl')
            xr -= nt.width + 12
        C.put(pl, sc, xr - sc.width, h / 2 - sc.height / 2, anchor='tl')
        x0 = 30 + 72 + 24
        room = xr - sc.width - 30 - x0
        place = 'ДОМА' if g['home'] is True else 'В ГОСТЯХ' if g['home'] is False else ''
        sub = ' · '.join(x for x in (g['date'], place) if x)
        nm = C.text(g['opp'].upper(), 'exo', 40, WHITE, 800, max_w=room)
        sb = C.text(sub, 'mont', 24, GRAY, 700, track=0.06, max_w=room) if sub else None
        if sb is not None:
            C.put(pl, nm, x0, 13, anchor='tl')
            C.put(pl, sb, x0, h - 13 - sb.height, anchor='tl')
        else:
            C.put(pl, nm, x0, h / 2 - nm.height / 2, anchor='tl')
        return pl

    def _stat_tiles(self, s, col):
        items = []
        if s['points'] is not None:
            sub = ('за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей'))) if s['gp'] is not None else ''
            items.append(('ОЧКИ', '%d' % s['points'], sub, WHITE))
        if s['place'] is not None:
            items.append(('МЕСТО', '%d' % s['place'], s['place_scope'], WHITE))
        if s['gd'] is not None:
            gcol = F.WIN if s['gd'] > 0 else F.LOSS if s['gd'] < 0 else WHITE
            items.append(('РАЗНИЦА ШАЙБ', F.gd_txt(s['gd']), '', gcol))
        n = len(items)
        if not n:
            return []
        gap = 20
        w = int((ROW_W - gap * (n - 1)) / n)
        h = 150
        out = []
        for lab, val, sub, vc in items:
            pl = chamfer(w, h, 28, INK, 218, C.mix(col, INK, 0.25), 3)
            C.put(pl, C.text(lab, 'mont', 26, C.mix(col, WHITE, 0.5), 800, track=0.12, max_w=w - 40), w / 2, 30)
            C.put(pl, C.text(val, 'exo', 72, vc, 900, max_w=w - 40), w / 2, 82 if sub else 92)
            if sub:
                C.put(pl, C.text(sub, 'mont', 25, GRAY, 700, max_w=w - 36), w / 2, 126)
            out.append(pl)
        return out

    def _extras(self, rec, col):
        ext = []
        for key, lab in (('pp', 'БОЛЬШИНСТВО'), ('pk', 'МЕНЬШИНСТВО')):
            v = pct(rec.get(key)) if rec.get(key) is not None else None
            if v:
                ext.append((lab, v))
        m = re.match(r'\s*(ОТ|В|П)\s*(\d+)', str(rec.get('streak') or ''))
        if m and int(m.group(2)) >= 2:
            n = int(m.group(2))
            word = {'В': plural(n, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'), 'П': plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ'),
                    'ОТ': plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ') + ' В ОТ'}[m.group(1)]
            ext.append(('СЕРИЯ', '%d %s' % (n, word)))
        ext = ext[:3]
        n = len(ext)
        if not n:
            return []
        gap = 20
        w = int((ROW_W - gap * (n - 1)) / n)
        h = 96
        out = []
        for lab, val in ext:
            pl = chamfer(w, h, 22, INK, 218, C.mix(col, INK, 0.25), 3)
            if n <= 2:
                v = C.text(val, 'exo', 52, WHITE, 900)
                lb = C.text(lab, 'mont', 28, C.mix(col, WHITE, 0.5), 800, track=0.1, max_w=w - v.width - 80)
                tot = lb.width + 22 + v.width
                x = (w - tot) / 2
                C.put(pl, lb, x, h / 2 - lb.height / 2, anchor='tl')
                C.put(pl, v, x + lb.width + 22, h / 2 - v.height / 2, anchor='tl')
            else:
                C.put(pl, C.text(lab, 'mont', 23, C.mix(col, WHITE, 0.5), 800, track=0.1, max_w=w - 30), w / 2, 26)
                C.put(pl, C.text(val, 'exo', 40, WHITE, 900, max_w=w - 30), w / 2, 64)
            out.append(pl)
        return out

    def _team_data(self, key):
        tm = self.h if key == 'h' else self.a
        col = self.col[key]
        s = self.st[key]
        items = []
        k = 1
        for i, g in enumerate(s['games'][:3]):
            items.append(dict(img=self._game_plate(g, col), pos=(W / 2, GAME_Y[i]), k=0.5 * k))
            k += 1
        k = max(k, 4)
        for plates, y in ((self._stat_tiles(s, col), STAT_Y), (self._extras(self.raw[key], col), EXT_Y)):
            if not plates:
                continue
            gap = 20
            tot = sum(p.width for p in plates) + gap * (len(plates) - 1)
            x = (W - tot) / 2
            for p in plates:
                items.append(dict(img=p, pos=(x + p.width / 2, y), k=0.5 * k))
                x += p.width + gap
                k += 1
        flash = {}
        for it in items:
            sz = it['img'].size
            if sz not in flash:
                ol = chamfer(sz[0], sz[1], 22 if sz[1] <= 96 else 26 if sz[1] <= 104 else 28, None, 0, C.mix(col, WHITE, 0.55), 4)
                flash[sz] = C.glow(ol, 10, 1.3, col)
            it['flash'] = flash[sz]
        name = C.glow(C.text(tm.up, 'exoi', 112, WHITE, 900, max_w=1000), 16, 0.8, col)
        role = C.text('ХОЗЯЕВА' if key == 'h' else 'ГОСТИ', 'mont', 30, C.mix(col, WHITE, 0.5), 800, track=0.3)
        rp = chamfer(role.width + 70, 52, 14, INK, 210, C.mix(col, INK, 0.2), 2)
        C.put(rp, role, rp.width / 2, 26)
        return dict(col=col, items=items, name=name, role=rp, emb=C.glow(tm.emb(236), 24, 1.0, col))

    # ─────────────────────────── время ───────────────────────────
    def speed(self, t):
        """Скорость камеры (ед. глубины / с): база + толчок на каждую долю + рывок на варпах + разгон перед дропом."""
        u, D = self.u, self.drop
        v = 2.0
        if t < D:
            ph = ((t - D) / u) % 1.0
            v += 2.6 * math.exp(-ph * 6)
            for tw in self.warps:
                if tw <= t < tw + 0.6:
                    v += 14 * math.exp(-(t - tw) * 7)
            if t >= self.tp:
                q = C.seg(t, self.tp, D)
                v += 16 * q ** 2.2
        else:
            v += 22 * math.exp(-(t - D) * 5)
        return v

    def travel(self, t):
        return float(np.interp(t, self._ts, self._trav))

    def scene(self, t):
        if t < self.t1:
            return 'intro'
        if t < self.t2:
            return 'h'
        if t < self.tp:
            return 'a'
        if t < self.drop:
            return 'pre'
        return 'pick'

    def state(self, t):
        """(палитра A, палитра B, доля B, точка схода) — смена цвета/формы за 0,22 с после варпа."""
        seq = [('intro', 0.0), ('h', self.t1), ('a', self.t2), ('pre', self.tp)]
        cur, prev, ts = 'intro', 'intro', 0.0
        for k, t0 in seq:
            if t >= t0:
                prev, cur, ts = cur, k, t0
        k = C.out_cubic(C.seg(t, ts, ts + 0.22)) if ts > 0 else 1.0
        v0, v1 = self.vp[prev], self.vp[cur]
        kv = C.in_out(C.seg(t, ts, ts + 0.45)) if ts > 0 else 1.0
        vp = (C.lerp(v0[0], v1[0], kv), C.lerp(v0[1], v1[1], kv))
        return prev, cur, k, vp

    # ─────────────────────────── тоннель ───────────────────────────
    def proj(self, vp, z, t):
        """Центр кольца на глубине z: тоннель слегка изгибается вдали."""
        f = min(1.0, z / SPAN) ** 1.4
        return vp[0] + 46 * f * math.sin(0.55 * t + 0.6), vp[1] + 34 * f * math.cos(0.43 * t)

    def ring_pts(self, cx, cy, R, rr, rot):
        x = cx + R * rr * np.cos(self.th + rot)
        y = cy + R * ASP * rr * np.sin(self.th + rot)
        return list(zip(x.tolist(), y.tolist()))

    def draw_tunnel(self, L, t, pa, pb, k, vp, zmax=None, bright=1.0):
        d = ImageDraw.Draw(L)
        A, B = self.pal[pa], self.pal[pb]
        rot_a, rot_b = A[3], B[3]
        rr = (1 - k) * shape_r(A[2], self.th + 0.0) + k * shape_r(B[2], self.th + 0.0)
        c1 = C.mix(A[0], B[0], k)
        c2 = C.mix(A[1], B[1], k)
        rot0 = rot_a + (rot_b - rot_a) * k
        sides = B[2] if k > 0.5 else A[2]
        trav = self.travel(t)
        tight = C.seg(t, self.tp, self.drop - 0.25 * self.u) if t < self.drop + 1 else 0.0
        if t >= self.drop:
            tight = 1.0
        step = GAP / 2
        n = int(SPAN / step) + 1
        twist = 0.05
        rings = []
        for i in range(n):
            idx = i + int(math.floor(trav / step))
            z = Z0 + (idx * step - trav)
            if z < Z0 - 1e-6:
                z += n * step
            odd = idx % 2 == 1
            if odd and tight <= 0.01:
                continue
            rings.append((z, idx, odd))
        rings.sort(key=lambda r: -r[0])
        if zmax is not None:
            rings = [r for r in rings if r[0] < zmax]
        rail_pts = []
        for z, idx, odd in rings:
            fog = C.clamp(1.12 - z / SPAN) ** 1.6 * C.clamp((z - Z0) / 0.5) * bright
            if odd:
                fog *= tight * 0.85
            if fog < 0.02:
                continue
            cx, cy = self.proj(vp, z, t)
            R = FOC / z
            rot = rot0 + twist * (idx * step) + 0.12 * t
            if pa == 'intro' and pb == 'intro' or (pb == 'intro'):
                col = c1 if (idx // 2) % 2 == 0 else c2
            else:
                col = c2 if (idx // 2) % 3 == 2 else c1
            if pb == 'pre' or pa == 'pre':
                col = C.mix(col, PRE_C, 0.0)
            col = tuple(int(v * fog) for v in col)
            wdt = int(C.clamp(1.5 + 7.5 / z, 1, 22))
            pts = self.ring_pts(cx, cy, R, rr, rot)
            d.line(pts + pts[:1], fill=col, width=wdt, joint='curve' if wdt > 4 else None)
            rail_pts.append((pts, fog, wdt))
        # рельсы — по вершинам контура (спираль из-за закрутки)
        stepj = NP // (sides if sides else 8)
        for j in range(0, NP, stepj):
            for a_, b_ in zip(rail_pts[:-1], rail_pts[1:]):
                f = min(a_[1], b_[1]) * 0.55
                if f < 0.03:
                    continue
                cc = tuple(int(v * f) for v in c1)
                d.line((a_[0][j], b_[0][j]), fill=cc, width=max(1, int(min(a_[2], b_[2]) * 0.45)))
        # световые штрихи вдоль стен
        sp = self.speed(t)
        ln = 0.25 + 0.06 * sp
        for th, rf, z0, br in self.streaks:
            z = Z0 + ((z0 - 1.7 * trav) % SPAN)
            if zmax is not None and z > zmax + 2:
                continue
            z2 = z + ln
            fog = C.clamp(1.1 - z / SPAN) ** 1.3 * C.clamp((z - Z0) / 0.3) * br * bright
            if fog < 0.04:
                continue
            p = []
            for zz in (z, z2):
                cx, cy = self.proj(vp, zz, t)
                R = FOC / zz * rf
                p.append((cx + R * math.cos(th), cy + R * ASP * math.sin(th)))
            cc = C.mix(c2 if br > 0.85 else c1, WHITE, 0.55)
            d.line(p, fill=tuple(int(v * fog) for v in cc), width=max(1, int(1 + 3.2 / z)))

    def gate(self, L, t, vp, tr, col, pb):
        """Ворота факта: яркое кольцо формы тоннеля летит на камеру и проходит мимо в момент tr."""
        lead = 0.42
        if not tr - lead <= t < tr + 0.2:
            return
        q = (t - (tr - lead)) / lead
        z = 7.0 + (1.0 - 7.0) * q if q <= 1 else 1.0 - 0.6 * (t - tr) / 0.2
        if z <= Z0:
            return
        sides, rot = self.pal[pb][2], self.pal[pb][3]
        rr = shape_r(sides, self.th)
        cx, cy = self.proj(vp, z, t)
        R = FOC / z
        a = C.clamp((1.3 - z / 7) * 1.1) * (1 - C.seg(t, tr + 0.05, tr + 0.2))
        pts = self.ring_pts(cx, cy, R * 1.04, rr, rot + 0.12 * t)
        cc = tuple(int(v * a) for v in C.mix(col, WHITE, 0.45))
        ImageDraw.Draw(L).line(pts + pts[:1], fill=cc, width=int(C.clamp(3 + 10 / z, 3, 30)), joint='curve')

    def flash_ring(self, L, t, vp, tw, col):
        if not tw <= t < tw + 0.45:
            return
        q = (t - tw) / 0.45
        r = 60 + 1500 * C.out_cubic(q)
        a = (1 - q) ** 1.5
        d = ImageDraw.Draw(L)
        cc = tuple(int(v * a) for v in C.mix(col, WHITE, 0.6))
        d.ellipse((vp[0] - r, vp[1] - r * ASP, vp[0] + r, vp[1] + r * ASP), outline=cc, width=int(10 + 30 * (1 - q)))

    def glow_add(self, base, L, k=1.6):
        sm = L.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
        sm = sm.point(lambda v: min(255, int(v * k)))
        g = sm.resize((W, H), Image.BILINEAR)
        return ImageChops.add(ImageChops.add(base, L), g)

    # ─────────────────────────── плашки в перспективе ───────────────────────────
    def fly(self, out, im, pos, vp, t, tr, t_end, flash=None, a=1.0):
        """Плашка прилетает из точки схода (глубина 7 → 1) к моменту tr и в конце сцены пролетает мимо.
        Не рисует сразу, а кладёт в очередь out: flush рисует дальние раньше ближних (летящая плашка — за вставшими)."""
        lead = 0.42
        if t < tr - lead:
            return
        if t < tr:
            q = (t - (tr - lead)) / lead
            z = 7.0 + (1.0 - 7.0) * q
        else:
            z = 1.0 - 0.05 * math.exp(-(t - tr) / 0.06) * math.sin((t - tr) * 30)
        al = a * C.clamp((7.4 - z) / 2.2)
        if t >= t_end - 0.26:
            qo = C.seg(t, t_end - 0.26, t_end)
            z = 1.0 / (1 + 1.5 * C.in_cubic(qo))
            al *= 1 - qo
        s = 1 / z
        x = vp[0] + (pos[0] - vp[0]) * s
        y = vp[1] + (pos[1] - vp[1]) * s
        fl = math.exp(-(t - tr) / 0.16) if (flash is not None and t >= tr) else 0.0
        out.append((z, len(out), im, flash if fl > 0.03 else None, s, x, y, al, fl))

    @staticmethod
    def flush(fr, q):
        for z, _, im, flash, s, x, y, al, fl in sorted(q, key=lambda e: (-round(e[0], 3), e[1])):
            C.put(fr, C.scale(im, s) if abs(s - 1) > 0.004 else im, x, y, al)
            if flash is not None:
                C.put(fr, C.scale(flash, s) if abs(s - 1) > 0.004 else flash, x, y, al * fl)

    # ─────────────────────────── сцены ───────────────────────────
    def intro(self, fr, t, vp):
        u = self.u
        te = self.t1
        a = 1.0
        q = C.out_expo(C.seg(t, 0.05, 0.45))
        if t >= te - 0.26:
            a = 1 - C.seg(t, te - 0.26, te)
        C.put(fr, self.date, W / 2, 360 + 20 * (1 - q), q * a)
        first = self.b(-math.floor((self.drop - 0.9) / u))         # первая доля после 0,9 с — линия; за полдоли до — эмблемы
        fq = []
        for side, x in (('h', 275), ('a', 805)):
            tr = first - 0.5 * u
            self.fly(fq, self.i_emb[side], (x, VP_INTRO[1]), vp, t, tr, te)
            self.fly(fq, self.i_name[side], (x, 890), vp, t, tr + 0.08, te)
            self.fly(fq, self.i_role[side], (x, 952), vp, t, tr + 0.12, te)
        if self.odds:
            qo = C.out_expo(C.seg(t, first - 0.3, first + 0.1))
            C.put(fr, self.odds_lab, W / 2, 1060, qo * a)
            for i, im in enumerate(self.odds):
                self.fly(fq, im, (W / 2 + (i - 1) * 330, 1222), vp, t, first + 0.09 * i, te)
        self.flush(fr, fq)

    def team(self, fr, t, key, t0, t_end, vp):
        T = self.T[key]
        a = 1 - C.seg(t, t_end - 0.26, t_end)
        q = C.out_expo(C.seg(t, t0, t0 + 0.4))
        sg = 1 if key == 'h' else -1
        C.put(fr, T['name'], W / 2 + sg * 120 * (1 - q), 364, a * q)
        C.put(fr, T['role'], W / 2, 452, a * C.seg(t, t0 + 0.12, t0 + 0.4))
        # эмблема в точке схода: вылетает из глубины, пульс на доли
        qe = C.out_back(C.seg(t, t0 + 0.05, t0 + 0.45), 1.5)
        if qe > 0.01:
            ph = ((t - self.drop) / self.u) % 1.0
            s = max(0.05, qe) * (1 + 0.05 * math.exp(-ph * 6))
            C.put(fr, C.scale(T['emb'], s), vp[0], vp[1], a * min(1.0, qe * 1.4))
        fq = []
        for it in T['items']:
            self.fly(fq, it['img'], it['pos'], vp, t, t0 + it['k'] * self.u, t_end, it['flash'])
        self.flush(fr, fq)

    def pre_scene(self, fr, t, vp):
        D, u = self.drop, self.u
        tp = self.tp
        q = C.out_expo(C.seg(t, tp, tp + 0.4))
        suck = C.in_cubic(C.seg(t, D - 0.6 * u, D))
        for side, sy, ny in (('h', -1, 380), ('a', 1, 1240)):
            ex, ey = VP_PRE[0], VP_PRE[1] + sy * 250                   # точка схода разгона — без съезда на склейке
            x, y = C.lerp(ex, VP_PRE[0], suck), C.lerp(ey, VP_PRE[1], suck)
            s = (0.6 + 0.4 * q) * (1 - 0.85 * suck)
            jit = C.seg(t, D - u, D)
            x += 4 * jit * math.sin(t * 83 + sy)
            C.put(fr, C.scale(self.pre_emb[side], s), x, y, q * (1 - suck ** 3))
            C.put(fr, self.pre_name[side], W / 2 + sy * 140 * (1 - q), ny, q * (1 - suck))

    def light_core(self, base, t, vp):
        """Растущий свет в конце тоннеля (разгон) — аддитивно."""
        D = self.drop
        g = C.seg(t, self.tp, D)
        r = 260 + 2200 * g ** 4
        k = 0.45 + 0.55 * g
        y, x = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)          # считаем в 1/4 и растягиваем
        d = np.hypot(x * 4 + 2 - vp[0], (y * 4 + 2 - vp[1]) / 1.15) / r
        al = (np.clip(1 - d, 0, 1) ** 1.7 * 255 * k).astype(np.uint8)
        li = Image.fromarray(al, 'L').resize((W, H), Image.BILINEAR)
        return ImageChops.add(base, Image.merge('RGB', (li, li, li)))

    def pick_bg(self, t):
        D, u = self.drop, self.u
        base = self.light.copy()
        # лучи света из эмблемы — медленно вращаются (в 1/4 и растягиваются)
        ang = 0.18 * (t - D)
        ph = ((t - D) / u) % 1.0
        pulse = math.exp(-ph * 5)
        rays = (0.5 + 0.5 * np.cos(14 * (self.ray_th - ang))) ** 5 * self.ray_fall * (70 + 40 * pulse)
        rays2 = (0.5 + 0.5 * np.cos(9 * (self.ray_th + ang * 0.7))) ** 8 * self.ray_fall * 45
        rr = np.clip(rays + rays2, 0, 255).astype(np.uint8)
        ri = Image.fromarray(rr, 'L').resize((W, H), Image.BILINEAR)
        lay = Image.merge('RGB', (ri, ri, ri))
        lay = ImageChops.multiply(lay, Image.new('RGB', (W, H), C.mix(self.cf, WHITE, 0.6)))
        return ImageChops.add(base, lay)

    def pick_lines(self, L, t):
        """После вылета: световые кольца формы тоннеля на каждую долю расходятся от эмблемы; световая пыль."""
        D, u = self.drop, self.u
        d = ImageDraw.Draw(L)
        vx, vy = self.pick_pos(t)[:2]
        sides = self.pal[self.side][2]
        rot = self.pal[self.side][3]
        rr = shape_r(sides, self.th)
        nb = int((t - D) / u)
        for n in range(max(0, nb - 1), nb + 1):
            tb = D + n * u
            age = t - tb
            if not 0 <= age < 1.4 * u:
                continue
            q = age / (1.4 * u)
            R = 230 + 1100 * C.out_cubic(q)
            a = (1 - q) ** 1.6 * (1.0 if n else 1.4)
            pts = self.ring_pts(vx, vy, R, rr, rot + 0.3 * age)
            cc = tuple(min(255, int(v * a)) for v in C.mix(self.cf, WHITE, 0.5))
            d.line(pts + pts[:1], fill=cc, width=int(6 + 10 * (1 - q)), joint='curve')
        for th, r0, sp in self.dust:
            r = ((r0 + (t - D) * 0.22 * sp) % 1.0)
            R = 200 + 1100 * r
            fade = math.sin(math.pi * r)
            x, y = vx + R * math.cos(th), vy + R * ASP * math.sin(th)
            x2, y2 = vx + (R + 26 * sp) * math.cos(th), vy + (R + 26 * sp) * ASP * math.sin(th)
            cc = tuple(int(v * fade * 0.8) for v in C.mix(self.cf, WHITE, 0.7))
            d.line((x, y, x2, y2), fill=cc, width=3)

    def pick_pos(self, t):
        D = self.drop
        kc = C.out_cubic(C.seg(t, self.t_cta, self.t_cta + 0.4))
        s = 1 - 0.26 * kc
        return VP_PICK[0], VP_PICK[1] - 90 * kc, s, kc

    def pick(self, fr, t):
        D, u = self.drop, self.u
        x, y, s, kc = self.pick_pos(t)
        q = C.out_back(C.seg(t, D, D + 0.4), 1.4)
        ph = ((t - D) / u) % 1.0
        pulse = math.exp(-ph * 6)
        hs = (0.4 + 0.6 * C.out_expo(C.seg(t, D, D + 0.5))) * s * (1 + 0.06 * pulse)
        C.put(fr, C.scale(self.halo, hs), x, y, 0.75 + 0.25 * pulse)
        es = max(0.05, (0.3 + 0.7 * q)) * s * (1 + 0.025 * pulse)
        C.put(fr, C.scale(self.p_emb, es), x, y, min(1.0, C.seg(t, D, D + 0.12) * 1.0 + 0.0))
        # панель текста
        dy = -120 * kc
        qp = C.out_expo(C.seg(t, D + 0.05, D + 0.45))
        C.put(fr, C.scale(self.panel, 0.9 + 0.1 * qp), W / 2, 1110 + dy, qp)
        y1 = 935 + dy
        if self.p_l1 is not None:
            q1 = C.out_expo(C.seg(t, D + 0.08, D + 0.4))
            C.put(fr, C.scale(self.p_l1, 1.4 - 0.4 * q1), W / 2, y1, min(1.0, q1 * 2))
            y2 = y1 + 104
        else:
            y2 = y1 + 40
        q2 = C.out_expo(C.seg(t, D + 0.14, D + 0.5))
        C.put(fr, C.scale(self.p_l2, (1.5 - 0.5 * q2) * (1 + 0.015 * pulse)), W / 2, y2, min(1.0, q2 * 2))
        y3 = y2 + 100
        if self.p_l3 is not None:
            q3 = C.out_expo(C.seg(t, D + 0.5 * u, D + 0.85 * u))
            C.put(fr, self.p_l3, W / 2, y3 + 20 * (1 - q3), q3)
        if self.kef is not None:
            q4 = C.out_back(C.seg(t, D + 1.0 * u, D + 1.0 * u + 0.35), 1.8)
            if q4 > 0.01:
                C.put(fr, C.scale(self.kef, 0.5 + 0.5 * q4), W / 2, y3 + 116, min(1.0, q4 * 1.5))

    # ─────────────────────────── кадр ───────────────────────────
    def frame(self, t):
        u, D = self.u, self.drop
        sc = self.scene(t)
        if sc != 'pick':
            pa, pb, k, vp = self.state(t)
            base = self._bg(pb) if k >= 1 else Image.blend(self._bg(pa), self._bg(pb), k)
            if sc == 'pre':
                base = self.light_core(base, t, vp)
            L = Image.new('RGB', (W, H), (0, 0, 0))
            self.draw_tunnel(L, t, pa, pb, k, vp, bright=C.seg(t, 0, 0.3) * 0.8 + 0.2)
            for tw in self.warps:
                self.flash_ring(L, t, self.vp[self.scene(tw)], tw, self.pal[self.scene(tw)][0])
            if sc in ('h', 'a'):
                T = self.T[sc]
                t0 = self.t1 if sc == 'h' else self.t2
                for it in T['items']:
                    self.gate(L, t, vp, t0 + it['k'] * u, T['col'], sc)
            fr = self.glow_add(base, L).convert('RGBA')
            if sc == 'intro':
                self.intro(fr, t, vp)
            elif sc == 'h':
                self.team(fr, t, 'h', self.t1, self.t2, vp)
            elif sc == 'a':
                self.team(fr, t, 'a', self.t2, self.tp, vp)
            else:
                self.pre_scene(fr, t, vp)
        else:
            base = self.pick_bg(t)
            L = Image.new('RGB', (W, H), (0, 0, 0))
            if t < D + 0.4:                                         # последние кольца тоннеля проносятся мимо
                self.draw_tunnel(L, t, 'pre', 'pre', 1.0, VP_PRE, zmax=1.6, bright=1 - C.seg(t, D, D + 0.4))
            self.pick_lines(L, t)
            fr = self.glow_add(base, L, 1.3).convert('RGBA')
            self.pick(fr, t)
        C.put(fr, self.tag, W / 2, TAG_Y, C.seg(t, 0, 0.3))
        ha = C.seg(t, 0.1, 0.4) * (1 - C.seg(t, self.t_cta, self.t_cta + 0.2))
        C.put(fr, self.handle_im, W / 2, HY, ha)
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.18, self.t_cta + 0.6))
            C.put(fr, self.tg, W / 2, 1372 + 60 * (1 - q), q)
        # камера: рывок на варпах, дрожь на разгоне, удар на дропе, пульс на долях после дропа
        z, dx, dy, rot = 1.0, 0.0, 0.0, 0.0
        for tw in self.warps:
            if tw <= t < tw + 0.4:
                z += 0.05 * (1 - C.seg(t, tw, tw + 0.4)) ** 2
            sx, sy = C.shake(t, tw, 8, 0.25)
            dx, dy = dx + sx, dy + sy
        if self.tp <= t < D:
            qq = C.seg(t, self.tp, D)
            z += 0.04 * C.in_cubic(qq)
            dx += 7 * qq ** 2 * math.sin(t * 73)
            dy += 7 * qq ** 2 * math.cos(t * 59)
            rot = 1.2 * qq ** 2 * math.sin(t * 9)
        if t >= D:
            kk = 1 - C.seg(t, D, D + 0.5)
            z += 0.08 * kk ** 2
            sx, sy = C.shake(t, D, 24, 0.45)
            dx, dy = dx + sx, dy + sy
        fr = C.zoom(fr.convert('RGB'), z, dx=dx, dy=dy, rot=rot)
        if D <= t < D + 0.18:
            fr = C.rgb_split(fr, 14 * (1 - C.seg(t, D, D + 0.18)))
        if D - 0.04 <= t < D + 0.4:
            fa = 1.0 if t < D + 1 / 30 else (1 - C.seg(t, D + 1 / 30, D + 0.4)) ** 1.6
            fr = Image.blend(fr, Image.new('RGB', fr.size, C.mix(WHITE, self.cf, 0.12)), 0.9 * fa)
        return C.vignette(fr, 0.38 if t < D else 0.3)
