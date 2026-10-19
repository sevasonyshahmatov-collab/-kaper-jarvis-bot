# -*- coding: utf-8 -*-
"""«Эфир» — графика большой спортивной трансляции (предматчевая студия), переложенная в вертикаль (трек «PACKS»,
UK-дрилл, 71 BPM половинным темпом). Не табло (led), не терминал (jarvis), не кинетическая типографика (kinetic):
это пакет эфирной графики — стеклянные панели, «нижние трети», плашки-параллелограммы, угловые шторки.

Фон — тёмная размытая арена (огни под крышей, трибуны, лёд) с цветными засветками клубов, медленно «плывёт».
Сверху на всё время — эфирная плашка-«баг»: JARVIS | NHL, обе команды с эмблемами (текущая — в цвете клуба) и время
МСК; на прогнозе в баге остаётся только выбранная команда. Внизу безопасной зоны — @jarvibet на стеклянной плашке
(y 1440), одинаково во всех сценах до плашки Telegram. Склейки — жёсткие эфирные шторки: три косые полосы в цветах
клуба и белая проходят через кадр и закрывают его ровно на долю трека, баг и @jarvibet остаются поверх шторки.
Шрифт трансляции — Roboto Condensed (курсив 900 для имён и цифр).

Сцены (u — доля трека, D — дроп; доли считаются от дропа; team / pre / hold / cta — reels_cfg/broadcast.json):
  интро (до b(−2·team−pre), 4 доли при drop_beats = 20) — большая доска матча: две эмблемы на клубных засветках,
             имена на плашках, «хозяева / гости», в центре день и время МСК; на 1-ю долю — линия основного
             времени П1 · Х · П2 тремя крупными стеклянными плашками (подписи на вкладках в цветах клубов);
  клуб ×2 (team долей, ~5,9 с) — шторка в цвете клуба на долю, карточка клуба: эмблема, огромное имя, «хозяева /
             гости», плашки серии побед и побед дома / в гостях (если есть record-поля); на 1-ю, 1,5-ю и 2-ю доли
             выезжают «нижние трети» — последние 3 игры строками результатов (дата, эмблема и имя соперника, дома /
             в гостях, счёт, ОТ/Б, В/П); с 2,5-й доли — панель цифр с полосками, числа «набегают»: очки за N матчей,
             место, разница шайб (забито–пропущено), большинство, меньшинство, шайбы за матч (пустые не показываются);
  сравнение (pre долей, тихий провал трека перед дропом) — экран делится косой чертой на два цвета: обе эмблемы
             сверху, ниже — встречные полосы цифр (очки, забивает / пропускает за матч, большинство, меньшинство),
             строки на пятых долях; камера медленно наезжает;
  ДРОП (hold долей, ~4,2 с) — ровно на дропе графический захват эфира: вспышка, кадр заливает цвет выбранного клуба
             (косые полосы уходят), эмблема влетает с ударом (одна эмблема, без второй и без «VS»), ПОБЕДА …,
             «В ОСНОВНОЕ ВРЕМЯ» на белой нижней трети, кэф — на 1-ю долю; на каждую долю — кольцо и толчок;
  финал (cta долей, ~2,3 с) — прогноз уходит выше и уменьшается, снизу — плашка Telegram (C.tg_plate, текст по центру).
Никаких шансов на исход и рубрик. Кадр — чистая функция t; фоны, панели, баги и спрайты готовятся
в конструкторе (до разветвления процессов) и кешируются на уровне модуля.
"""
import colorsys
import math
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels.core import W, H

WHITE = (255, 255, 255)
GRAY = (170, 180, 198)
DIM = (112, 122, 142)
INK = (8, 11, 20)
NEUT = (44, 52, 72)
BUG_Y, HY = 282, 1440            # центр бага, центр @jarvibet
X0, XW = 40, 1000                # поле панелей
PADB = 60                        # запас фона на «дыхание»
_BG, _SP = {}, {}


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def vivid(c, v_min=0.78, s_min=0.6):
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    s = min(0.92, max(s, s_min)) if s > 0.12 else s
    v = max(v, v_min)
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, s, v))


def deep(c, v=0.36):
    h, s, _ = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, min(1.0, s * 1.05 + 0.05), v))


def club(t, avoid=None):
    """Насыщенный клубный цвет (не серый); если близок к avoid — другой цвет клуба."""
    cand = [c for c in (t.c0, t.c1, t.c2) if (max(c) - min(c)) / 255 > 0.2 and 30 < 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] < 235]
    cand = [vivid(c) for c in cand] or [vivid(t.c1)]
    if avoid is not None:
        far = [c for c in cand if sum((a - b) ** 2 for a, b in zip(c, avoid)) ** 0.5 > 130]
        if far:
            return far[0]
    return cand[0]


def num_txt(v, kind):
    if kind == 'int':
        return '%d' % int(round(v))
    if kind == 'gd':
        return F.gd_txt(int(round(v)))
    if kind == 'pct':
        s = ('%.1f' % v).replace('.', ',')
        return (s[:-2] if s.endswith(',0') else s) + '%'
    s = ('%.2f' % v).rstrip('0').rstrip('.').replace('.', ',')
    return s


def fnum(v):
    try:
        return None if v is None or isinstance(v, bool) else float(v)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────── графика ───────────────────────────────
def para_pts(w, h, sk):
    return [(sk, 0), (w, 0), (w - sk, h), (0, h)]


def para(w, h, sk, fill, a=255):
    key = ('para', int(w), int(h), int(sk), tuple(fill), a)
    if key not in _SP:
        _SP[key] = C.polygon(para_pts(w, h, sk), (w, h), fill, a)
    return _SP[key]


def glass(w, h, sk=0, tab=None, tabw=12, a=226, top=(36, 44, 66), bot=(11, 15, 27), line=True):
    """Стеклянная эфирная панель (параллелограмм со скосом sk): градиент, блик сверху, тонкая кромка, вкладка цвета."""
    key = ('glass', int(w), int(h), int(sk), tab, tabw, a, top, bot, line)
    if key in _SP:
        return _SP[key]
    w, h = int(w), int(h)
    ss = 3
    m = Image.new('L', (w * ss, h * ss), 0)
    ImageDraw.Draw(m).polygon([(x * ss, y * ss) for x, y in para_pts(w, h, sk)], fill=255)
    m = m.resize((w, h), Image.LANCZOS)
    body = C.vgrad(w, h, [(0, top), (0.55, C.mix(top, bot, 0.6)), (1, bot)]).convert('RGBA')
    arr = np.asarray(body, np.float32).copy()
    if line:                                                                 # блик верхней кромки
        arr[0:3, :, :3] = arr[0:3, :, :3] * 0.5 + 255 * 0.5
        arr[3:5, :, :3] = arr[3:5, :, :3] * 0.8 + 255 * 0.2
    body = Image.fromarray(arr.astype(np.uint8), 'RGBA')
    body.putalpha(m.point(lambda v: int(v * a / 255)))
    if tab:                                                                  # вкладка — непрозрачная
        tm = Image.new('L', (w * ss, h * ss), 0)
        ImageDraw.Draw(tm).polygon([(sk * ss, 0), ((sk + tabw) * ss, 0), (tabw * ss, h * ss), (0, h * ss)], fill=255)
        tm = tm.resize((w, h), Image.LANCZOS)
        tl = Image.new('RGBA', (w, h), tuple(tab) + (255,))
        tl.putalpha(tm)
        body.alpha_composite(tl)
    _SP[key] = body
    return body


def lit(e, col):
    """Эмблема «под софитом»: светлый ореол (тёмные эмблемы читаются на тёмном фоне) и клубное свечение."""
    g = C.glow(e, 10, 1.25, (236, 242, 255))
    return C.glow(g, 26, 0.75, C.mix(col, WHITE, 0.35))


def chip_txt(s, col, fs=30, h=54, sk=12, txt=WHITE):
    tx = C.text(s, 'robc', fs, txt, 800, track=0.06)
    pl = para(tx.width + 46 + sk, h, sk, col)
    pl = pl.copy()
    C.put(pl, tx, pl.width / 2, h / 2)
    return pl


def _arena(spec, size):
    """Размытая арена: огни под крышей, трибуны, лёд; засветки клубов spec = [(цвет, cx, cy, r, сила)]."""
    key = ('arena', tuple(spec), size)
    if key in _BG:
        return _BG[key]
    w, h = size
    rnd = np.random.default_rng(11)
    im = C.vgrad(w, h, [(0, (12, 16, 30)), (0.35, (8, 11, 21)), (0.75, (6, 8, 15)), (1, (10, 14, 24))]).convert('RGBA')
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # огни под крышей (три ряда с перспективой)
    for row, (y, n, r, a) in enumerate(((70, 9, 16, 230), (170, 13, 12, 190), (250, 17, 9, 150))):
        for i in range(n):
            x = (i + 0.5) / n * w + rnd.uniform(-12, 12)
            d.ellipse((x - r, y - r * 0.7, x + r, y + r * 0.7), fill=(255, 244, 222, a))
    # трибуны: точки зрителей
    for _ in range(5200):
        y = rnd.uniform(330, 1150)
        x = rnd.uniform(0, w)
        k = rnd.uniform(0.25, 1)
        c = rnd.choice([0, 1, 2])
        col = [(200, 205, 220), (150, 160, 190), (230, 210, 190)][c]
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=col + (int(46 * k),))
    # борт и лёд снизу
    d.rectangle((0, 1180, w, 1215), fill=(220, 226, 236, 70))
    d.ellipse((-w * 0.4, 1230, w * 1.4, h + 700), fill=(170, 190, 215, 70))
    d.rectangle((w / 2 - 6, 1230, w / 2 + 6, h), fill=(200, 40, 50, 60))
    lay = lay.filter(ImageFilter.GaussianBlur(9))
    im.alpha_composite(lay)
    for col, cx, cy, r, k in spec:
        bl = C.radial(int(2 * r), int(2 * r), col, int(255 * k), 1.7)
        C.put(im, bl, cx, cy)
    # тонкая косая штриховка (эфирная фактура) и затемнение
    arr = np.asarray(im.convert('RGB'), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    st = ((xx + yy * 0.42) % 14 < 2).astype(np.float32)[..., None]
    arr = arr * (1 - 0.06 * st) + 255 * 0.012 * st
    arr *= 0.9
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    _BG[key] = out
    return out


def _stripes_bg(col, size):
    """Фон захвата эфира: цвет клуба косыми полосами трёх тонов, светлое пятно за эмблемой."""
    key = ('stripes', tuple(col), size)
    if key in _BG:
        return _BG[key]
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    p = xx + yy * 0.42
    band = (np.floor(p / 120) % 3)
    c0, c1, c2 = (np.array(deep(col, v), np.float32) for v in (0.30, 0.40, 0.52))
    arr = np.where(band[..., None] == 0, c0, np.where(band[..., None] == 1, c1, c2))
    thin = ((p % 120) < 3).astype(np.float32)[..., None]
    arr = arr * (1 - 0.35 * thin) + 255 * 0.35 * thin * 0.4
    # мягкий свет за эмблемой и тень книзу
    cx, cy = w / 2, 600
    dd = np.sqrt(((xx - cx) / 700) ** 2 + ((yy - cy) / 760) ** 2)
    glow_k = np.clip(1 - dd, 0, 1) ** 1.6
    arr = arr + (np.array(vivid(col, 0.95), np.float32) - arr) * (0.5 * glow_k[..., None])
    arr = arr * (1 - 0.45 * np.clip((yy - 900) / 1100, 0, 1))[..., None]
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    _BG[key] = out
    return out


class Broadcast(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 71, drop=20 * 60 / 71, line=None, team=7, pre=2,
                 hold=5, cta=2.75, seed=31, **kw):
        """Сцены: интро → клуб (team долей) ×2 → сравнение (pre) → дроп-прогноз (hold) → Telegram (cta); доли — от дропа."""
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.line = league, when, coef, line
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.both = F.pick_team(self.h, self.a, pick) is None      # прогноз на матч целиком (тотал) — в финале обе команды
        self.other = 'a' if self.side == 'h' else 'h'
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
        self.cover_t = max(1.4, self.t1 - 0.5)
        self._prep()

    # ── заготовки ──
    def _prep(self):
        col = {}
        col[self.side] = club(self.fav)
        col[self.other] = club(self.h if self.other == 'h' else self.a, avoid=col[self.side])
        self.col = col
        self.dk = {k: deep(c, 0.42) for k, c in col.items()}
        self.cf = col[self.side]
        T = {'h': self.h, 'a': self.a}
        self.T = T
        bs = (W + 2 * PADB, H + 2 * PADB)
        ch, ca = col['h'], col['a']
        self.bgs = {
            'intro': _arena(((ch, 120, 520, 760, 0.55), (ca, bs[0] - 120, 520, 760, 0.55), (ch, 200, 1500, 600, 0.25),
                             (ca, bs[0] - 200, 1500, 600, 0.25)), bs),
            'h': _arena(((ch, bs[0] - 160, 420, 900, 0.62), (ch, 140, 1450, 760, 0.35)), bs),
            'a': _arena(((ca, bs[0] - 160, 420, 900, 0.62), (ca, 140, 1450, 760, 0.35)), bs),
        }
        self.bgs['cmp'] = self._split_bg(bs)
        self.bg_pick = _stripes_bg(self.cf, (W + 400, H))
        # общее: баги, @jarvibet
        m = re.match(r'\s*(.*?)\s*·\s*(\d{1,2}:\d{2})\s*(\S*)\s*$', self.when or '')
        self.day, self.hm, self.tz = (m.group(1), m.group(2), m.group(3) or 'МСК') if m else ('', self.when or '', '')
        self.bugs = {k: self._bug(k) for k in (None, 'h', 'a', 'pick')}
        hp = C.text(C.HANDLE, 'unb', 40, (236, 242, 250), 600)
        pl = glass(hp.width + 96, 66, 0, a=210, line=True)
        C.put(pl, hp, pl.width / 2, 33)
        self.handle = pl
        self.tg = C.tg_plate(960, 172, font='unb')
        # интро
        self.i_emb = {k: lit(T[k].emb(296), col[k]) for k in 'ha'}
        self.i_spot = {k: C.radial(560, 560, col[k], 150, 1.8) for k in 'ha'}
        self.i_name = {k: self._name_plate(T[k].up, k) for k in 'ha'}
        self.i_role = {k: C.text('ХОЗЯЕВА' if k == 'h' else 'ГОСТИ', 'robc', 30, GRAY, 800, track=0.22) for k in 'ha'}
        self.i_day = C.text(self.day, 'robc', 40, GRAY, 800, track=0.08) if self.day else None
        self.i_hm = C.text(self.hm, 'robci', 112, WHITE, 900, max_w=330)
        self.i_tz = chip_txt(self.tz, NEUT, 30, 50, 10) if self.tz else None
        self.i_odds_lab = C.text('ОСНОВНОЕ ВРЕМЯ', 'robc', 34, GRAY, 800, track=0.24)
        self.i_odds = self._odds() if self.line else []
        # клубы
        self.TD = {k: self._team_data(k) for k in 'ha'}
        # сравнение
        self.cmp = self._cmp_data()
        # прогноз
        if self.both:
            pe = Image.new('RGBA', (820, 410), (0, 0, 0, 0))
            C.put(pe, C.fit(self.h.emb(340), 330, 330), 200, 205)
            C.put(pe, C.fit(self.a.emb(340), 330, 330), 620, 205)
            self.p_emb = C.glow(pe, 26, 0.9, (255, 255, 255))
        else:
            self.p_emb = C.glow(self.fav.emb(410), 26, 0.9, (255, 255, 255))
        m = re.match(r'(ПОБЕДА)\s+(.+)$', self.pick1)
        self.p_l1 = C.text(m.group(1), 'robci', 92, WHITE, 900, track=0.04) if m else None
        self.p_l2 = C.text(m.group(2) if m else self.pick1, 'robci', 184, WHITE, 900, max_w=1000)
        self.p_l2s = C.shadow(self.p_l2, 16, 0.55)
        self.p_l3 = None
        if self.pick2:
            tx = C.text(self.pick2, 'robc', 44, deep(self.cf, 0.3), 900, track=0.08, max_w=720)
            pl = para(tx.width + 120, 80, 22, WHITE).copy()
            C.put(pl, tx, pl.width / 2, 40)
            self.p_l3 = pl
        self.kef = None
        if self.coef:
            lab = C.text('КЭФ', 'robc', 44, GRAY, 800, track=0.18)
            val = C.text(C.fmt_k(self.coef), 'robci', 118, WHITE, 900)
            w = lab.width + val.width + 150
            pl = glass(w, 150, 26, tab=self.cf, tabw=16, a=236).copy()
            C.put(pl, lab, 70 + lab.width / 2, 75)
            C.put(pl, val, 70 + lab.width + 40 + val.width / 2, 75)
            self.kef = pl
        # шторки: (время закрытия, цвета полос, направление)
        D = self.drop
        self.cuts = [(0.0, (deep(ch, 0.5), WHITE, ca), 1), (self.t1, (self.dk['h'], WHITE, ch), -1),
                     (self.t2, (self.dk['a'], WHITE, ca), 1), (self.tp, (ch, WHITE, ca), -1), (D, (deep(self.cf, 0.3), WHITE, self.cf), 1)]

    def _split_bg(self, bs):
        key = ('split', self.col['h'], self.col['a'], bs)
        if key in _BG:
            return _BG[key]
        w, h = bs
        L = _arena(((self.col['h'], 200, 500, 820, 0.7), (self.col['h'], 200, 1500, 700, 0.35)), bs)
        R = _arena(((self.col['a'], w - 200, 500, 820, 0.7), (self.col['a'], w - 200, 1500, 700, 0.35)), bs)
        m = Image.new('L', bs, 0)
        sk = 0.12 * h
        ImageDraw.Draw(m).polygon([(w / 2 + sk, 0), (w, 0), (w, h), (w / 2 - sk, h)], fill=255)
        out = L.copy()
        out.paste(R, (0, 0), m)
        d = ImageDraw.Draw(out)
        d.line((w / 2 + sk, 0, w / 2 - sk, h), fill=(255, 255, 255, 255), width=6)
        _BG[key] = out
        return out

    def _bug(self, mode):
        """Эфирный баг: [JARVIS | NHL] [эмблема клуб] [эмблема клуб] [время]; mode — подсвеченная команда или 'pick'."""
        w, h = 1000, 76
        im = glass(w, h, 0, a=232)
        im = im.copy()
        tg = C.text(F.tag(self.league), 'unb', 24, INK, 800, track=0.08)
        tw = tg.width + 44
        C.put(im, para(tw + 18, h, 18, WHITE), 0, 0, anchor='tl')
        C.put(im, tg, (tw + 18) / 2 - 6, h / 2)
        tm = C.text('%s %s' % (self.hm, self.tz) if self.tz else self.hm, 'robci', 34, WHITE, 900)
        tmw = tm.width + 40
        C.put(im, tm, w - tmw / 2 - 6, h / 2)
        x0, x1 = tw + 18, w - tmw - 10
        sides = [self.side] if mode == 'pick' and not self.both else ['h', 'a']
        sw = (x1 - x0) / len(sides)
        for i, k in enumerate(sides):
            sx = x0 + i * sw
            on = mode == k or mode == 'pick'
            if on:
                C.put(im, para(int(sw) + 4, h, 18, self.dk[k]), sx - 2, 0, anchor='tl')
                C.put(im, para(int(sw) + 4, 6, 0, self.col[k]), sx - 2, h - 6, anchor='tl')
            e = C.glow(self.T[k].emb(54), 5, 1.1, (235, 240, 255))
            C.put(im, e, sx + 22 + 27, h / 2)
            nm = C.text(self.T[k].up, 'robci', 34, WHITE if (on or mode is None) else GRAY, 900, max_w=sw - 100)
            C.put(im, nm, sx + 22 + 54 + 12 + nm.width / 2, h / 2)
        return im

    def _name_plate(self, s, k):
        tx = C.text(s, 'robci', 58, WHITE, 900, max_w=360)
        w = 410
        pl = para(w, 90, 20, self.dk[k]).copy()
        C.put(pl, para(w, 6, 0, self.col[k]), 0, 84, anchor='tl')
        C.put(pl, tx, w / 2, 44)
        return pl

    def _odds(self):
        gap = 22
        bw = int((XW - 2 * gap) / 3)
        out = []
        for i, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), self.line)):
            tabc = self.dk['h'] if i == 0 else self.dk['a'] if i == 2 else NEUT
            pl = glass(bw, 252, 0, a=232).copy()
            C.put(pl, C.rrect(bw, 62, 0, tabc), 0, 0, anchor='tl')
            if i != 1:
                C.put(pl, C.rrect(bw, 5, 0, self.col['h' if i == 0 else 'a']), 0, 60, anchor='tl')
            C.put(pl, C.text(lab, 'robc', 38, WHITE, 900, track=0.12), bw / 2, 31)
            C.put(pl, C.text(C.fmt_k(v), 'robci', 120, WHITE, 900, max_w=bw - 30), bw / 2, 62 + (252 - 62) / 2)
            out.append(pl)
        return out

    def _chips(self, k):
        rec = self.raw[k]
        out = []
        m = re.match(r'\s*(ОТ|В|П)\s*(\d+)', str(rec.get('streak') or ''))
        if m and int(m.group(2)) >= 2 and m.group(1) == 'В':
            n = int(m.group(2))
            out.append('%d %s ПОДРЯД' % (n, plural(n, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД')))
        home = rec.get('home_today')
        home = (k == 'h') if home is None else bool(home)
        r = rec.get('home_rec' if home else 'road_rec')
        mm = re.match(r'\s*(\d+)-(\d+)-(\d+)', str(r or ''))
        if mm:
            wv, n = int(mm.group(1)), sum(int(x) for x in mm.groups())
            if n:
                out.append('ПОБЕДЫ %s %d ИЗ %d' % ('ДОМА' if home else 'В ГОСТЯХ', wv, n))
        fs = 30 if len(out) < 2 else 26
        return [chip_txt(s, self.dk[k] if i == 0 else NEUT, fs, 54, 12) for i, s in enumerate(out)]

    def _game_row(self, g, k):
        w, h = XW, 112
        pl = glass(w, h, 16, tab=F.res_col(g['res']), tabw=14, a=230).copy()
        dt = C.text(g['date'], 'robc', 32, GRAY, 800) if g['date'] else None
        if dt:
            C.put(pl, dt, 44 + dt.width / 2, h / 2)
        ex = 190
        if g['opp_key']:
            try:
                C.put(pl, C.Team(g['opp_key']).emb(80), ex, h / 2)
            except Exception:
                pass
        nm = C.text(g['opp'].upper(), 'robci', 50, WHITE, 900, max_w=410)
        wh = 'ДОМА' if g['home'] is True else 'В ГОСТЯХ' if g['home'] is False else ''
        nx = 248
        if wh:
            sub = C.text(wh, 'robc', 26, GRAY, 800, track=0.12)
            C.put(pl, nm, nx, 14, anchor='tl')
            C.put(pl, sub, nx, 14 + nm.height + 8, anchor='tl')
        else:
            C.put(pl, nm, nx, h / 2 - nm.height / 2, anchor='tl')
        ch = F.chip(g['res'], 70)
        cx = w - 30 - 35
        C.put(pl, ch, cx, h / 2)
        sc = C.text(g['score'], 'robci', 82, WHITE, 900)
        sx = cx - 35 - 26 - sc.width
        C.put(pl, sc, sx, h / 2 - sc.height / 2, anchor='tl')
        if g['note']:
            nt = C.text(g['note'], 'robc', 30, GRAY, 800)
            C.put(pl, nt, sx - 14 - nt.width, h / 2 - nt.height / 2 + 14, anchor='tl')
        return pl

    def _tiles(self, k):
        s, rec = self.st[k], self.raw[k]
        out = []
        if s['points'] is not None:
            sub = ('за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей'))) if s['gp'] else ''
            out.append(('ОЧКИ', s['points'], 'int', sub, C.clamp(s['points'] / (2.0 * s['gp'])) if s['gp'] else 0.5, False))
        if s['place'] is not None:
            out.append(('МЕСТО', s['place'], 'int', s['place_scope'], C.clamp((17 - s['place']) / 16.0), False))
        if s['gd'] is not None:
            gf, ga = fnum(rec.get('gf')), fnum(rec.get('ga'))
            sub = ('%d–%d' % (gf, ga)) if gf is not None and ga is not None else ''
            out.append(('РАЗНИЦА ШАЙБ', s['gd'], 'gd', sub, C.clamp(s['gd'] / 20.0, -1, 1), True))
        for key, lab, kind, norm in (('pp', 'БОЛЬШИНСТВО', 'pct', 40.0), ('pk', 'МЕНЬШИНСТВО', 'pct', 100.0),
                                     ('gf_pg', 'ЗАБИВАЕТ ЗА МАТЧ', 'dec', 5.0)):
            v = fnum(rec.get(key))
            if v is not None:
                out.append((lab, v, kind, '', C.clamp(v / norm), False))
        out = out[:6]
        n = len(out)
        if not n:
            return []
        rows = (n + 1) // 2
        y0, y1 = 1050, 1394
        gap_y, gap_x = 14, 20
        th = min(150, (y1 - y0 - gap_y * (rows - 1)) / rows)
        tw = (XW - gap_x) / 2
        tiles = []
        for i, (lab, v, kind, sub, bar, div) in enumerate(out):
            r, c = divmod(i, 2)
            if n % 2 == 1 and i == n - 1:
                c, w = None, XW
            else:
                w = tw
            x = X0 if c in (0, None) else X0 + tw + gap_x
            y = y0 + r * (th + gap_y)
            pl = glass(int(w), int(th), 10, tab=self.col[k], tabw=8, a=226).copy()
            lb = C.text(lab, 'robc', 30, GRAY, 800, track=0.08, max_w=w * 0.62)
            C.put(pl, lb, 34, 18, anchor='tl')
            sb = None
            if sub:
                sb = C.text(sub, 'robc', 27, (150, 160, 180), 700, max_w=w * 0.55)
                C.put(pl, sb, 34, 18 + lb.height + 8, anchor='tl')
            tiles.append(dict(img=pl, x=x, y=y, w=w, h=th, v=v, kind=kind, bar=bar, div=div, row=r,
                              vx=x + w - 34, vy=y + th * 0.44))
        return tiles

    def _team_data(self, k):
        tm = self.T[k]
        col = self.col[k]
        rows = [self._game_row(g, k) for g in self.st[k]['games'][:3]]
        return dict(emb=lit(tm.emb(270), col), spot=C.radial(620, 620, col, 140, 1.7),
                    role=chip_txt('ХОЗЯЕВА' if k == 'h' else 'ГОСТИ', self.col[k], 30, 52, 12),
                    name=C.text(tm.up, 'robci', 116, WHITE, 900, max_w=690), chips=self._chips(k), rows=rows,
                    tiles=self._tiles(k), flash=para(XW, 112, 16, WHITE))

    def _cmp_data(self):
        out = []
        rh, ra = self.raw['h'], self.raw['a']
        sh, sa = self.st['h'], self.st['a']
        cand = [('ОЧКИ', sh['points'], sa['points'], 'int'),
                ('ЗАБИВАЕТ ЗА МАТЧ', fnum(rh.get('gf_pg')), fnum(ra.get('gf_pg')), 'dec'),
                ('ПРОПУСКАЕТ ЗА МАТЧ', fnum(rh.get('ga_pg')), fnum(ra.get('ga_pg')), 'dec'),
                ('БОЛЬШИНСТВО', fnum(rh.get('pp')), fnum(ra.get('pp')), 'pct'),
                ('МЕНЬШИНСТВО', fnum(rh.get('pk')), fnum(ra.get('pk')), 'pct'),
                ('БРОСКИ ЗА МАТЧ', fnum(rh.get('sf_pg')), fnum(ra.get('sf_pg')), 'dec')]
        for lab, vh, va, kind in cand:
            if vh is None or va is None:
                continue
            out.append(dict(lab=C.text(lab, 'robc', 32, (226, 232, 242), 800, track=0.1), vh=vh, va=va, kind=kind,
                            mx=max(abs(vh), abs(va)) or 1.0))
        out = out[:5]
        return dict(rows=out, emb={k: lit(self.T[k].emb(220), self.col[k]) for k in 'ha'},
                    name={k: C.text(self.T[k].up, 'robci', 60, WHITE, 900, max_w=430) for k in 'ha'},
                    under={k: para(300, 8, 0, self.col[k]) for k in 'ha'})

    # ── шторки ──
    def wipe(self, fr, t):
        """Эфирные шторки: полосы закрывают кадр к моменту склейки tc и уходят, открывая новую сцену."""
        S = 0.3 * H
        for tc, cols, dr in self.cuts:
            if not (tc - 0.3 <= t < tc + 0.34) or (tc == self.drop and t < tc):
                continue
            n = len(cols)
            d = ImageDraw.Draw(fr)
            for i, cl in enumerate(cols):
                if tc <= 0.01 or (tc == self.drop):
                    e = 1.0
                else:
                    e = C.in_out(C.seg(t, tc - 0.26 + 0.06 * i, tc - 0.12 + 0.06 * i))
                x_out = C.out_cubic(C.seg(t, tc + 0.02 + 0.06 * (n - 1 - i), tc + 0.22 + 0.06 * (n - 1 - i)))
                if tc == self.drop and t >= tc:
                    x_out = C.out_cubic(C.seg(t, tc + 0.035 * (n - 1 - i), tc + 0.16 + 0.035 * (n - 1 - i)))
                R = C.lerp(-S - 20, W + S + 20, e)
                L = C.lerp(-S - 20, W + S + 20, x_out) if t >= tc else -S - 20
                if R - L < 1:
                    continue
                pts = [(L + S, 0), (R + S, 0), (R, H), (L, H)]
                if dr < 0:
                    pts = [(W - x, y) for x, y in pts]
                d.polygon(pts, fill=tuple(cl) + (255,))

    # ── сцены ──
    def bg(self, key, t, zoom_k=0.0):
        im = self.bgs[key]
        ox = PADB + 34 * math.sin(t * 0.37)
        oy = PADB + 30 * math.cos(t * 0.29)
        if zoom_k > 0:
            cw, chh = W / (1 + zoom_k), H / (1 + zoom_k)
            x0 = ox + (W - cw) / 2
            y0 = oy + (H - chh) / 2
            return im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + chh))
        return im.crop((int(ox), int(oy), int(ox) + W, int(oy) + H))

    def intro(self, fr, t):
        u = self.u
        pulse = math.exp(-((t / u) % 1.0) * 6)
        for k, sg, d0 in (('h', -1, 0.08), ('a', 1, 0.2)):
            x = W / 2 + sg * 300
            q = C.out_back(C.seg(t, d0, d0 + 0.36), 1.5)
            C.put(fr, self.i_spot[k], x, 590, min(1.0, C.seg(t, d0 - 0.05, d0 + 0.3)))
            if q > 0.01:
                C.put(fr, C.scale(self.i_emb[k], max(0.05, q) * (1 + 0.025 * pulse)), x, 590, min(1.0, q * 1.6))
            qn = C.out_expo(C.seg(t, d0 + 0.14, d0 + 0.5))
            C.put(fr, self.i_name[k], x + sg * 160 * (1 - qn), 846, qn)
            qr = C.seg(t, d0 + 0.3, d0 + 0.6)
            C.put(fr, self.i_role[k], x, 922, qr)
        qc = C.out_expo(C.seg(t, 0.3, 0.65))
        if self.i_day is not None:
            C.put(fr, self.i_day, W / 2, 506 - 20 * (1 - qc), qc)
        C.put(fr, C.scale(self.i_hm, 0.8 + 0.2 * qc), W / 2, 594, qc)
        if self.i_tz is not None:
            C.put(fr, self.i_tz, W / 2, 682, C.seg(t, 0.45, 0.7))
        if self.i_odds:
            tb = self.b(math.ceil((0.6 - self.drop) / self.u))   # первая доля интро не раньше 0,6 с
            C.put(fr, self.i_odds_lab, W / 2, 1022, C.seg(t, tb - 0.1, tb + 0.15))
            bw = self.i_odds[0].width
            for i, pl in enumerate(self.i_odds):
                q = C.out_expo(C.seg(t, tb + 0.07 * i, tb + 0.07 * i + 0.36))
                if q <= 0.003:
                    continue
                x = X0 + i * (bw + 22) + bw / 2
                C.put(fr, pl, x, 1196 + 120 * (1 - q), min(1.0, q * 1.4))

    def team(self, fr, t, k, t0):
        u = self.u
        D = self.TD[k]
        kb = (t - t0) / u
        pulse = math.exp(-(kb % 1.0) * 6) if kb >= 0 else 0
        # шапка клуба
        C.put(fr, D['spot'], 190, 490, C.seg(t, t0, t0 + 0.25))
        qe = C.out_back(C.seg(t, t0 + 0.03, t0 + 0.36), 1.6)
        if qe > 0.01:
            C.put(fr, C.scale(D['emb'], max(0.05, qe) * (1 + 0.025 * pulse)), 190, 490, min(1.0, qe * 1.6))
        qr = C.out_expo(C.seg(t, t0 + 0.06, t0 + 0.36))
        C.put(fr, D['role'], 352 + D['role'].width / 2 + 60 * (1 - qr), 388, qr)
        qn = C.out_expo(C.seg(t, t0 + 0.1, t0 + 0.45))
        C.put(fr, D['name'], 350 + D['name'].width / 2 + 220 * (1 - qn), 486, qn)
        x = 352
        for i, chp in enumerate(D['chips']):
            tc = t0 + (0.5 + 0.25 * i) * u
            q = C.out_expo(C.seg(t, tc, tc + 0.3))
            if x + chp.width > X0 + XW + 4:
                break
            C.put(fr, chp, x + chp.width / 2 + 50 * (1 - q), 584, q)
            x += chp.width + 14
        # нижние трети: последние игры
        for i, row in enumerate(D['rows']):
            tr = t0 + (1.0 + 0.5 * i) * u
            if t < tr - 0.01:
                continue
            q = C.out_expo(C.seg(t, tr, tr + 0.3))
            y = 712 + i * 126
            C.put(fr, row, X0 + XW / 2 - 1150 * (1 - q), y)
            fl = 1 - C.seg(t, tr + 0.05, tr + 0.32)
            if fl > 0:
                C.put(fr, D['flash'], X0 + XW / 2 - 1150 * (1 - q), y, 0.7 * fl)
        # цифры (полупрозрачные полоски — на отдельном слое: ImageDraw по RGBA не смешивает)
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for tl in D['tiles']:
            ta = t0 + (2.5 + 0.5 * tl['row']) * u + (0.08 if tl['x'] > X0 + 10 else 0)
            if t < ta:
                continue
            q = C.out_expo(C.seg(t, ta, ta + 0.3))
            xx = tl['x'] + 80 * (1 - q)
            C.put(fr, tl['img'], xx, tl['y'], q, anchor='tl')
            kc = C.out_cubic(C.seg(t, ta + 0.05, ta + 0.7))
            vt = C.text(num_txt(tl['v'] * kc, tl['kind']), 'robci', 64 if tl['h'] < 120 else 76, WHITE, 900)
            C.put(fr, vt, tl['vx'] - vt.width / 2 + 80 * (1 - q), tl['vy'], q)
            # полоска
            bx0, bx1 = xx + 34, xx + tl['w'] - 34
            by = tl['y'] + tl['h'] - 20
            al = int(255 * q)
            d.rectangle((bx0, by, bx1, by + 7), fill=(255, 255, 255, int(40 * q)))
            if tl['div']:
                mid = (bx0 + bx1) / 2
                L = (bx1 - bx0) / 2 * tl['bar'] * kc
                xa, xb = (mid, mid + L) if L >= 0 else (mid + L, mid)
                d.rectangle((mid - 1, by - 4, mid + 1, by + 11), fill=(255, 255, 255, al))
                d.rectangle((xa, by, xb, by + 7), fill=tuple(F.WIN if L >= 0 else F.LOSS) + (al,))
            else:
                d.rectangle((bx0, by, bx0 + (bx1 - bx0) * tl['bar'] * kc, by + 7), fill=tuple(self.col[k]) + (al,))
        if D['tiles'] and t >= t0 + 2.5 * u:
            fr.alpha_composite(ov)

    def compare(self, fr, t):
        u, t0 = self.u, self.tp
        cm = self.cmp
        q = C.out_expo(C.seg(t, t0, t0 + 0.3))
        for k, sg in (('h', -1), ('a', 1)):
            x = W / 2 + sg * 270
            C.put(fr, cm['emb'][k], x - sg * 200 * (1 - q), 452, q)
            C.put(fr, cm['name'][k], x, 612, C.seg(t, t0 + 0.08, t0 + 0.3))
            C.put(fr, cm['under'][k], x, 660, C.seg(t, t0 + 0.12, t0 + 0.35))
        rows = cm['rows']
        if not rows:
            return
        n = len(rows)
        y0, y1 = 700, 1392
        rh = (y1 - y0) / n
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        band = glass(XW, int(rh - 12), 14, a=205, line=False)
        for i, r in enumerate(rows):
            ta = t0 + (0.12 + 0.18 * i) * u
            if t < ta:
                continue
            qa = C.out_expo(C.seg(t, ta, ta + 0.25))
            kc = C.out_cubic(C.seg(t, ta, ta + 0.45))
            y = y0 + i * rh
            C.put(fr, band, W / 2 + 60 * (1 - qa), y + rh / 2, qa)
            C.put(fr, r['lab'], W / 2, y + 30, qa)
            by = y + rh * 0.62
            al = int(255 * qa)
            for k, v, sg in (('h', r['vh'], -1), ('a', r['va'], 1)):
                L = 310 * abs(v) / r['mx'] * kc
                xa = W / 2 + sg * 18
                xb = xa + sg * L
                d.rectangle((min(xa, xb), by - 15, max(xa, xb), by + 15), fill=tuple(self.col[k]) + (al,))
                d.rectangle((min(xa, xb), by - 15, max(xa, xb), by - 12), fill=(255, 255, 255, int(al * 0.5)))
                vt = C.text(num_txt(v * kc, r['kind']), 'robci', 58, WHITE, 900, max_w=150)
                vx = W / 2 + sg * 438
                C.put(fr, vt, vx, by, qa)
            d.rectangle((W / 2 - 2, by - 26, W / 2 + 2, by + 26), fill=(255, 255, 255, al))
        fr.alpha_composite(ov)

    def pick_geo(self, t):
        """Позиции и масштаб элементов прогноза: на финале группа поднимается и уменьшается."""
        kc = C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.36))
        A = dict(emb=(590, 1.0), l1=(880, 1.0), l2=(1000, 1.0), l3=(1132, 1.0), kef=(1282, 1.0))
        B = dict(emb=(468, 0.7), l1=(690, 0.86), l2=(790, 0.84), l3=(902, 0.9), kef=(1036, 0.86))
        return {k: (C.lerp(A[k][0], B[k][0], kc), C.lerp(A[k][1], B[k][1], kc)) for k in A}

    def pick(self, fr, t):
        u, D = self.u, self.drop
        g = self.pick_geo(t)
        bp = math.exp(-(((t - D) / u) % 1.0) * 6) if t < self.t_cta else 0.0
        # кольца на долях
        ov = None
        for n in range(0, 8):
            tb = self.b(n)
            age = t - tb
            if 0 <= age < 0.7 and tb < self.t_cta + 0.01:
                r = 240 + 640 * C.out_cubic(age / 0.7)
                a = int(150 * (1 - age / 0.7) ** 1.5)
                cy = g['emb'][0]
                if ov is None:
                    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(ov).ellipse((W / 2 - r, cy - r, W / 2 + r, cy + r), outline=(255, 255, 255, a), width=9)
        if ov is not None:
            fr.alpha_composite(ov)
        ye, se = g['emb']
        qe = C.out_cubic(C.seg(t, D, D + 0.2))
        s = se * (2.1 - 1.1 * qe) * (1 + 0.03 * bp)
        C.put(fr, C.scale(self.p_emb, s), W / 2, ye, min(1.0, 0.8 + qe))
        if self.p_l1 is not None:
            y, s1 = g['l1']
            q1 = C.out_expo(C.seg(t, D + 0.03, D + 0.3))
            C.put(fr, C.scale(self.p_l1, s1), W / 2 - 260 * (1 - q1), y, q1)
        y, s2 = g['l2']
        q2 = C.out_expo(C.seg(t, D + 0.06, D + 0.32))
        C.put(fr, C.scale(self.p_l2s, s2), W / 2, y + 14, q2)
        C.put(fr, C.scale(self.p_l2, s2 * (1.5 - 0.5 * q2) * (1 + 0.012 * bp)), W / 2, y, min(1.0, q2 * 1.8))
        if self.p_l3 is not None:
            y, s3 = g['l3']
            q3 = C.out_expo(C.seg(t, D + 0.5 * u, D + 0.5 * u + 0.3))
            C.put(fr, C.scale(self.p_l3, s3), W / 2 + 300 * (1 - q3), y, q3)
        if self.kef is not None:
            y, s4 = g['kef']
            q4 = C.out_back(C.seg(t, D + u, D + u + 0.32), 1.7)
            if q4 > 0.01:
                C.put(fr, C.scale(self.kef, s4 * (0.6 + 0.4 * q4)), W / 2, y, min(1.0, q4 * 1.5))

    # ── кадр ──
    def frame(self, t):
        u, D = self.u, self.drop
        if t < self.t1:
            sc, fr = 'intro', self.bg('intro', t).copy()
            self.intro(fr, t)
        elif t < self.t2:
            sc, fr = 'h', self.bg('h', t).copy()
            self.team(fr, t, 'h', self.t1)
        elif t < self.tp:
            sc, fr = 'a', self.bg('a', t).copy()
            self.team(fr, t, 'a', self.t2)
        elif t < D:
            sc = 'cmp'
            fr = self.bg('cmp', t, 0.05 * C.in_cubic(C.seg(t, self.tp, D)))
            self.compare(fr, t)
        else:
            sc = 'pick'
            off = int(min(399, (t - D) * 55))
            fr = self.bg_pick.crop((off, 0, off + W, H))
        if sc == 'pick':
            self.wipe(fr, t)
            self.pick(fr, t)
        else:
            self.wipe(fr, t)
        # камера: толчок на склейках и на долях после дропа, удар на дропе
        z, dx, dy, rot = 1.0, 0.0, 0.0, 0.0
        for th in (self.t1, self.t2, self.tp):
            if t >= th:
                z += 0.03 * (1 - C.seg(t, th, th + 0.3)) ** 2
            sx, sy = C.shake(t, th, 6, 0.22)
            dx, dy = dx + sx, dy + sy
        if t >= D:
            kk = 1 - C.seg(t, D, D + 0.45)
            z += 0.07 * kk ** 2
            for n in range(1, 8):
                tb = self.b(n)
                if tb < self.t_cta and t >= tb:
                    z += 0.012 * (1 - C.seg(t, tb, tb + 0.25)) ** 2
            sx, sy = C.shake(t, D, 24, 0.45)
            dx, dy = dx + sx, dy + sy
            rot = 1.1 * kk ** 2 * math.sin((t - D) * 40)
        fr = C.zoom(fr.convert('RGB'), z, dx=dx, dy=dy, rot=rot)
        if D <= t < D + 0.2:
            fr = C.rgb_split(fr, 14 * (1 - C.seg(t, D, D + 0.2)))
        if D <= t < D + 0.26:
            fa = 1.0 if t < D + 1 / 30 else (1 - C.seg(t, D + 1 / 30, D + 0.26)) ** 1.6
            fr = Image.blend(fr, Image.new('RGB', fr.size, C.mix(WHITE, self.cf, 0.15)), 0.7 * fa)
        fr = C.vignette(fr, 0.38).convert('RGBA')
        # поверх всего: баг, @jarvibet, Telegram
        bq = C.out_expo(C.seg(t, 0.12, 0.45))
        mode = None if t < self.t1 else 'h' if t < self.t2 else 'a' if t < self.tp else None if t < D else 'pick'
        C.put(fr, self.bugs[mode], W / 2, BUG_Y - 40 * (1 - bq), bq)
        ha = C.seg(t, 0.2, 0.45) * (1 - C.seg(t, self.t_cta, self.t_cta + 0.2))
        C.put(fr, self.handle, W / 2, HY, ha * C.HANDLE_BOTTOM)
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.24, self.t_cta + 0.6))
            C.put(fr, self.tg, W / 2, 1316 + 60 * (1 - q), q)
        return C.grain(fr, t, 4)
