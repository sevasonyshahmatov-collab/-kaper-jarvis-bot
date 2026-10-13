# -*- coding: utf-8 -*-
"""«Скачки» — ночной ипподром под прожекторами: матч как заезд, прогноз — фотофиниш ровно на дроп.

Вид сверху: тёмно-зелёный газон с полосами стрижки, белые бровки на столбиках, дымка в свете прожекторов.
Клуб — «жокей-фишка» (эмблема в круге цвета клуба), бежит по своей дорожке шаг за шагом на доли трека.
Сцены (время — в долях трека u от дропа; доли — из reels_cfg/race.json):
  старт (до первой команды) — две стартовые боксы с фишками, «хозяева — гости», лига и время МСК, под ними табло
                тотализатора с линией основного времени П1 · Х · П2 крупно (цифры «перещёлкиваются» и встают на долю);
                за долю до конца сцены дверцы боксов распахиваются, на долю — наезд камеры в дорожку 1;
  команда 1 (team долей, ~6,3 с) — дорожка хозяев слева, справа попоны-плашки: на доли 1, 2, 3 фишка берёт барьеры —
                последние 3 игры (победа — чистый прыжок, поражение — сбитая жердь; на попоне В/П, счёт, ОТ/Б,
                соперник, дата); дальше на каждую половину доли — дистанционные столбы: очки за матчи, место,
                разница шайб (и большинство, если есть); серия побед — в подписи под названием клуба;
  команда 2 (team долей) — на долю камера «перекидывается» на дорожку гостей справа, то же зеркально;
  финишная прямая (run долей) — обе фишки голова в голову, газон летит, линии скорости, комья из-под копыт на
                половины долей, сверху надвигается финишный створ;
  ДРОП (hold долей, ~4 с) — вспышка и фотофиниш: щелевой снимок (вертикальные полосы, линия судьи, шкала времени)
                проявляется сканом сверху вниз; финиширует только команда прогноза (одна фишка, вторая исчезает),
                «ПОБЕДА …», «В ОСНОВНОЕ ВРЕМЯ», попона с кэфом — на следующую долю; на каждую долю — пульс;
  финал (cta долей, ~2,4 с) — снимок поднимается, плашка Telegram (C.tg_plate, текст по центру плашки).
@jarvibet — у низа безопасной зоны (y 1446) одинаково во всех сценах до плашки Telegram; шапка JARVIS | NHL — сверху.
Пустые (None) поля статистики не показываются; никаких шансов и процентов победы.
"""
import colorsys
import math
import re

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels.core import W, H

GOLD = (232, 194, 106)
GOLD_L = (255, 226, 152)
GOLD_D = (40, 28, 6)
IVORY = (248, 243, 230)
INK = (22, 28, 24)
AMBER = (255, 184, 60)
WIN_D = (22, 150, 78)
LOSS_D = (206, 40, 44)
TURF_DK = (9, 44, 25)
TURF_LT = (18, 66, 37)

TAG_Y, HANDLE_Y = 262, 1446
P = 220                                   # период полос газона / штрихов разметки (для прокрутки)
TOK = 178                                 # фишка в сценах команд
STOP_TOP, STOP_BOT, START_MAX = 532, 1262, 1378
GEO = {'h': dict(lane=190, lx0=60, lx1=322, rail=48, div=334, px0=356, px1=1036),
       'a': dict(lane=890, lx0=758, lx1=1020, rail=1032, div=746, px0=44, px1=724)}
RACE_RAILS, RACE_DIV, RACE_X, RACE_Y, RACE_D = (70, 1010), 540, {'h': 305, 'a': 775}, 790, 250
JUDGE_Y = 408

_CACHE = {}                               # тяжёлые заготовки по параметрам ролика (общие для процессов после fork)


# ─────────────────────────────── мелочи ───────────────────────────────
def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _fnum(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(str(v).replace(',', '.').replace('%', '').strip())
    except ValueError:
        return None


def _pct(v):
    s = ('%.1f' % v).rstrip('0').rstrip('.')
    return s.replace('.', ',') + '%'


def streak_txt(v):
    """«В5» → «5 ПОБЕД ПОДРЯД»; «П3» → «3 ПОРАЖЕНИЯ ПОДРЯД»; серия из одной игры и ОТ — не показываем."""
    m = re.match(r'\s*(ОТ|OT|В|W|П|L)\s*(\d+)', str(v or '').upper())
    if not m:
        return ''
    k, n = m.group(1), int(m.group(2))
    if n < 2:
        return ''
    if k in ('В', 'W'):
        return '%d %s ПОДРЯД' % (n, plural(n, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'))
    if k in ('П', 'L'):
        return '%d %s ПОДРЯД' % (n, plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ'))
    return ''


def _vivid(c, vmin=0.6, vmax=0.84, smin=0.6):
    r, g, b = (x / 255 for x in c)
    hh, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s > 0.1:
        s = max(s, smin)
    v = min(max(v, vmin), vmax)
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(hh, s, v))


def _dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def club_cols(h, a):
    """Цвет попон хозяев и гостей: цветной, не тёмный; если клубы одного цвета — у гостей второй цвет клуба."""
    def cands(t):
        return [c for c in (t.c1, t.c0, t.c2) if (max(c) - min(c)) / 255 > 0.12] or [t.c1]
    ch = _vivid(cands(h)[0])
    ca = None
    for c in cands(a):
        v = _vivid(c)
        if _dist(v, ch) > 120:
            ca = v
            break
    if ca is None:
        ca = _vivid(cands(a)[0])
        if _dist(ca, ch) < 120:
            ca = (36, 92, 196) if _dist(ch, (36, 92, 196)) > 120 else (196, 150, 40)
    return ch, ca


def _lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def on_col(c):
    return INK if _lum(c) > 165 else (255, 255, 255)


def _shape(w, h, rt, rb, inset=0, S=3):
    """Маска попоны: верхние углы чуть скруглены, нижние — сильно (как у вальтрапа)."""
    def rr(r):
        m = Image.new('L', (w * S, h * S), 0)
        ImageDraw.Draw(m).rounded_rectangle((inset * S, inset * S, (w - inset) * S - 1, (h - inset) * S - 1),
                                            radius=int(max(1, r - inset) * S), fill=255)
        return m
    a, b = rr(rt), rr(rb)
    a.paste(b.crop((0, h * S // 2, w * S, h * S)), (0, h * S // 2))
    return a.resize((w, h), Image.LANCZOS)


def saddle(w, h, col, rt=12, rb=None, pipe=(255, 255, 255), pa=150):
    """Попона-плашка: цвет клуба с объёмом, саржевая фактура и кант."""
    w, h = int(w), int(h)
    rb = rb if rb is not None else h * 0.34
    top, bot = np.array(C.mix(col, (255, 255, 255), 0.12), np.float32), np.array(C.mix(col, (0, 0, 0), 0.3), np.float32)
    g = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    arr = top * (1 - g) + bot * g
    arr = np.repeat(arr, w, 1)
    yy, xx = np.mgrid[0:h, 0:w]
    arr = arr * (1 + 0.035 * np.sin((xx + yy) * 1.1))[..., None]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    im.putalpha(_shape(w, h, rt, rb))
    if pipe:
        ring = ImageChops.subtract(_shape(w, h, rt, rb, 8), _shape(w, h, rt, rb, 11))
        lay = Image.new('RGBA', (w, h), tuple(pipe) + (0,))
        lay.putalpha(ring.point(lambda v: v * pa // 255))
        im.alpha_composite(lay)
    return im


def hblur(fr, k):
    """Быстрый смаз по горизонтали (сжать-растянуть)."""
    return fr.resize((max(8, W // k), H), Image.BILINEAR).resize((W, H), Image.BILINEAR)


def vblur(fr, k):
    return fr.resize((W, max(8, H // k)), Image.BILINEAR).resize((W, H), Image.BILINEAR)


# ─────────────────────────────── ипподром ───────────────────────────────
def _turf(h, seed=5):
    """Газон с полосами стрижки, период P по вертикали (для бесшовной прокрутки)."""
    rnd = np.random.default_rng(seed)
    y = np.arange(P, dtype=np.float32)[:, None]
    band = 0.5 + 0.5 * np.tanh(2.6 * np.cos(2 * np.pi * y / P))
    fine = rnd.normal(0, 1, (P, W)).astype(np.float32)
    fine = np.asarray(Image.fromarray(((fine * 28) + 128).clip(0, 255).astype(np.uint8)).resize((W, P * 3), Image.BILINEAR)
                      .resize((W, P), Image.BILINEAR), np.float32) - 128                 # травинки вдоль хода
    low = rnd.normal(0, 1, (1, W // 60 + 2)).astype(np.float32)
    low = np.asarray(Image.fromarray(((low * 40) + 128).clip(0, 255).astype(np.uint8)).resize((W, 1), Image.BICUBIC), np.float32) - 128
    a, b = np.array(TURF_DK, np.float32), np.array(TURF_LT, np.float32)
    tile = a * (1 - band[..., None]) + b * band[..., None]
    tile = tile * (1 + (fine[..., None] * 0.006 + low[..., None] * 0.003))
    reps = int(math.ceil(h / P))
    return np.clip(np.tile(tile, (reps, 1, 1))[:h], 0, 255)


def _rails(h, rails, divs, post_side=None):
    """Бровки (белые, на столбиках, с тенью) и пунктир между дорожками; период P по вертикали."""
    lay = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for x in divs:
        for y in range(-P, h + P, P // 2):
            d.rounded_rectangle((x - 3, y, x + 3, y + 64), 3, fill=(236, 240, 232, 150))
    sh = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    for x in rails:
        ds.rectangle((x - 2, 0, x + 18, h), fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    lay = Image.alpha_composite(sh, lay)
    d = ImageDraw.Draw(lay)
    for x in rails:
        for y in range(0, h + P, P // 2):
            d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(150, 156, 150, 255))
        d.rectangle((x - 7, 0, x + 7, h), fill=(246, 248, 242, 255))
        d.line((x - 3, 0, x - 3, h), fill=(255, 255, 255, 255), width=2)
    return lay


def _light():
    """Прожекторы: тёплые пятна света, косые лучи и дымка сверху — аддитивный слой RGB."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    acc = np.zeros((H, W), np.float32)
    for cx, cy, r, k in ((150, 150, 1150, 78), (950, 230, 1050, 66), (540, 980, 900, 30), (540, 1700, 800, 16)):
        dd = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
        acc += k * np.clip(1 - dd, 0, 1) ** 2.2
    for x0, ang in ((60, 0.42), (1020, -0.42)):                     # лучи из-за верхних углов
        nx, ny = math.cos(ang), math.sin(ang)
        dist = np.abs((xx - x0) * nx + yy * ny)
        along = np.clip(1 - yy / 1500, 0, 1)
        acc += 22 * np.exp(-(dist / 130) ** 2) * along
    acc += 26 * np.clip(1 - yy / 620, 0, 1) ** 1.6                   # дымка
    col = np.array([1.0, 0.96, 0.86], np.float32)
    return Image.fromarray(np.clip(acc[..., None] * col, 0, 255).astype(np.uint8), 'RGB')


def _token(team, col, d):
    """Жокей-фишка: кольцо цвета клуба с золотым ободком, белое поле, эмблема, блик."""
    S = 3
    D = d * S
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse((0, 0, D - 1, D - 1), fill=GOLD_L + (255,))
    dr.ellipse((int(D * 0.025), int(D * 0.025), int(D * 0.975), int(D * 0.975)), fill=tuple(C.mix(col, (0, 0, 0), 0.1)) + (255,))
    r2 = D * 0.135
    dr.ellipse((r2, r2, D - r2, D - r2), fill=GOLD + (255,))
    r3 = D * 0.15
    dr.ellipse((r3, r3, D - r3, D - r3), fill=IVORY + (255,))
    im = im.resize((d, d), Image.LANCZOS)
    e = C.fit(team.emb(int(d * 0.62)), d * 0.6, d * 0.6)
    C.put(im, e, d / 2, d / 2)
    hl = C.radial(int(d * 0.7), int(d * 0.36), (255, 255, 255), 70, 1.4)
    m = np.minimum(np.asarray(hl.getchannel('A')), 255).astype(np.uint8)
    hl.putalpha(Image.fromarray(m))
    C.put(im, hl, d / 2, d * 0.26)
    return im


class Race(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 76, drop=22 * 60 / 76, team=8, run=2, hold=5,
                 cta=3, seed=23, line=None, **kw):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.T = {'h': self.h, 'a': self.a}
        self.league, self.when, self.coef, self.line = league, when, coef, line
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.raw = {'h': sh or {}, 'a': sa or {}}
        self.st = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.col = dict(zip(('h', 'a'), club_cols(self.h, self.a)))
        self.t1 = self.b(-(2 * team + run))                # дорожка хозяев
        self.t2 = self.b(-(team + run))                    # дорожка гостей
        self.t_run = self.b(-run)                          # финишная прямая
        if self.t1 < 1.5:
            raise ValueError('мало времени до дропа')
        self.t_cta = self.b(hold)
        self.dur = self.b(hold + cta)
        self.t_gate = self.t1 - u                          # дверцы боксов — за долю до первой команды
        self.cover_t = round(min(self.t_gate - 0.15, max(1.3, self.t1 * 0.6)), 2)
        self._plan()
        key = (home, away, league, when, pick, coef, tuple(line or ()), repr(sorted((sh or {}).items()))[:4000],
               repr(sorted((sa or {}).items()))[:4000], self.seed)
        if key not in _CACHE:
            _CACHE[key] = self._prep()
        self.L = _CACHE[key]

    # ── расписание сцен команд ──
    def _plan(self):
        """Ряды дорожки снизу вверх: барьеры (3 игры, от давней к последней) → ряды дистанционных щитов по два.
        Барьер — на долю; ряд щитов — на долю, второй щит ряда — на половину доли позже."""
        u = self.u
        self.stops = {}
        for key, t0 in (('h', self.t1), ('a', self.t2)):
            games = self.st[key]['games']
            posts = self._posts(key)
            items = [('g', g) for g in reversed(games)]
            for i in range(0, len(posts), 2):
                items.append(('p', posts[i:i + 2]))
            n = len(items)
            sp = (STOP_BOT - STOP_TOP) / max(1, n - 1) if n > 1 else 0
            ys = [STOP_BOT - k * sp for k in range(n)]
            start = min(START_MAX, STOP_BOT + (sp or 150))
            out = []
            for k, ((typ, it), y) in enumerate(zip(items, ys)):
                y_prev = ys[k - 1] if k else start
                tk = t0 + (1 + k) * u
                ts = [tk] if typ == 'g' else [tk + 0.5 * u * j for j in range(len(it))]
                out.append(dict(typ=typ, it=it, y=y, y_prev=y_prev, bar=(y + y_prev) / 2, t=tk, ts=ts, d=0.3 * u))
            self.stops[key] = dict(items=out, start=start, ph=int(min(150, max(90, sp - 24))) if n > 1 else 150)

    def _posts(self, key):
        s, r = self.st[key], self.raw[key]
        out = []
        if s['points'] is not None:
            sub = ('за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей'))) if s['gp'] is not None else ''
            out.append(('%d' % s['points'], plural(s['points'], 'ОЧКО', 'ОЧКА', 'ОЧКОВ'), sub))
        if s['place'] is not None:
            out.append(('%d' % s['place'], 'МЕСТО', s['place_scope']))
        if s['gd'] is not None:
            gf, ga = _fnum(r.get('gf')), _fnum(r.get('ga'))
            sub = ('%d забито · %d пропущено' % (gf, ga)) if gf is not None and ga is not None else ''
            out.append((F.gd_txt(s['gd']), 'РАЗНИЦА ШАЙБ', sub))
        pp = _fnum(r.get('pp'))
        if pp is not None:
            pk = _fnum(r.get('pk'))
            out.append((_pct(pp), 'БОЛЬШИНСТВО', ('меньшинство %s' % _pct(pk)) if pk is not None else ''))
        return out

    # ── заготовки ──
    def _prep(self):
        L = {}
        rnd = np.random.default_rng(self.seed)
        light = _light()
        L['light'] = light
        turf = _turf(H + P)
        # прокрутка финишной прямой: газон + бровки, высота H + P
        tr = Image.fromarray(turf.astype(np.uint8), 'RGB').convert('RGBA')
        tr.alpha_composite(_rails(H + P, RACE_RAILS, (RACE_DIV,)))
        L['track_run'] = tr.convert('RGB')
        base = Image.fromarray(turf[:H].astype(np.uint8), 'RGB')
        # старт: обе дорожки, бровки
        bi = base.convert('RGBA')
        bi.alpha_composite(_rails(H, RACE_RAILS, (RACE_DIV,)))
        L['bg_intro'] = ImageChops.add(bi.convert('RGB'), light).convert('RGBA')
        # сцены команд: своя дорожка подсвечена, у неё бровка и пунктир
        for key in ('h', 'a'):
            g = GEO[key]
            arr = np.asarray(base, np.float32).copy()
            xx = np.arange(W, dtype=np.float32)
            inl = ((xx >= g['lx0']) & (xx <= g['lx1'])).astype(np.float32)
            inl = np.asarray(Image.fromarray((inl * 255).astype(np.uint8)[None, :].repeat(4, 0)).filter(ImageFilter.GaussianBlur(6))
                             .resize((W, 1)), np.float32)[0] / 255
            arr *= (0.72 + 0.5 * inl)[None, :, None]
            bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
            bg.alpha_composite(_rails(H, (g['rail'],), (g['div'],)))
            num = C.text('1' if key == 'h' else '2', 'osw', 230, (255, 255, 255), 700, a=46)
            C.put(bg, num, g['lane'], self.stops[key]['start'] + 10)
            L['bg_' + key] = ImageChops.add(bg.convert('RGB'), light).convert('RGBA')
        # фишки
        L['tok'] = {k: _token(self.T[k], self.col[k], TOK) for k in ('h', 'a')}
        L['tok_sh'] = {k: C.shadow(L['tok'][k], 14, 0.75) for k in ('h', 'a')}
        L['tok_run'] = {k: _token(self.T[k], self.col[k], RACE_D) for k in ('h', 'a')}
        L['tok_run_sh'] = {k: C.shadow(L['tok_run'][k], 18, 0.75) for k in ('h', 'a')}
        L['tok_gate'] = {k: _token(self.T[k], self.col[k], 262) for k in ('h', 'a')}
        L['tok_gate_sh'] = {k: C.shadow(L['tok_gate'][k], 16, 0.75) for k in ('h', 'a')}
        # сцены команд: шапка, плашки, барьеры
        for key in ('h', 'a'):
            L['head_' + key] = self._head(key)
            L['plates_' + key] = [[self._game_plate(key, s['it'])] if s['typ'] == 'g' else
                                  [self._post_plate(key, p, len(s['it'])) for p in s['it']] for s in self.stops[key]['items']]
            L['ghost_' + key] = {1: self._ghost(key, 1), 2: self._ghost(key, 2)}
            L['bar_' + key] = self._bar(key)
        L['stand'] = C.rrect(16, 40, 5, (30, 36, 32))
        L['marker'] = self._marker()
        L['glint'] = C.radial(340, 190, (255, 255, 255), 140, 1.4)
        L['bar_glow'] = C.radial(300, 90, (190, 255, 200), 200, 1.3)
        L['mark_glow'] = C.radial(160, 160, (255, 230, 200), 220, 1.3)
        # частицы: комья газона и пыль
        L['dust'] = [C.radial(s, s, c, a, 1.2) for s, c, a in ((14, (120, 98, 62), 230), (20, (70, 96, 52), 220),
                                                               (28, (210, 200, 170), 120), (10, (150, 120, 80), 255))]
        L['streak'] = [C.rrect(4, ln, 2, (240, 244, 236), 255) for ln in (180, 260, 360)]
        # старт
        L.update(self._intro_layers())
        # финишная прямая
        L['speed'] = [(rnd.uniform(90, 990), int(rnd.integers(0, 3)), rnd.uniform(0, 3000), rnd.uniform(1.2, 2.0),
                       rnd.uniform(0.25, 0.6)) for _ in range(26)]
        L['finish'] = self._finish()
        L['names_run'] = {k: self._name_tag(k) for k in ('h', 'a')}
        L['pole'] = self._pole()
        # частицы на долях: (время, x, y, [(угол, скорость, спрайт, жизнь)])
        L['bursts'] = self._bursts(rnd)
        # фотофиниш
        L.update(self._photo(rnd))
        L['tag'] = C.text(F.tag(self.league), 'unb', 32, IVORY, 700, track=0.12)
        L['handle'] = C.text(C.HANDLE, 'unb', 38, IVORY, 600)
        L['tg'] = C.tg_plate(960, 170)
        return L

    def _head(self, key):
        t, col = self.T[key], self.col[key]
        g = GEO[key]
        cw = g['px1'] - g['px0']
        cloth = saddle(96, 100, col, rt=10, rb=30)
        C.put(cloth, C.text('1' if key == 'h' else '2', 'osw', 74, on_col(col), 700), 48, 48)
        nm = C.text(t.up, 'osw', 104, C.mix(col, (255, 255, 255), 0.35) if _lum(col) < 120 else col, 700, max_w=cw - 130)
        nm = C.with_shadow(nm, 10, 0.6, 5)
        w = cloth.width + 22 + nm.width
        hd = Image.new('RGBA', (w, max(cloth.height, nm.height)), (0, 0, 0, 0))
        C.put(hd, cloth, cloth.width / 2, hd.height / 2)
        C.put(hd, nm, cloth.width + 22 + nm.width / 2, hd.height / 2 + 2)
        sub = ['ХОЗЯЕВА' if key == 'h' else 'ГОСТИ', F.lg_ru(self.league)]
        stx = streak_txt(self.raw[key].get('streak'))
        if stx:
            sub.append(stx)
        sb = C.text(' · '.join(sub), 'osw', 38, GOLD_L, 500, track=0.08, max_w=cw)
        return hd, sb

    def _game_plate(self, key, g):
        """Попона барьера: В/П в белом окне, счёт крупно, ОТ/Б, соперник, дата и где играли."""
        col = self.col[key]
        w, h = GEO[key]['px1'] - GEO[key]['px0'], self.stops[key]['ph']
        im = saddle(w, h, col)
        fg = on_col(col)
        bx = int(h * 0.74)
        box = C.rrect(bx, bx, 14, IVORY)
        C.put(box, C.text(g['res'] or '?', 'osw', bx * 0.8, WIN_D if g['res'] == 'В' else LOSS_D, 700), bx / 2, bx / 2 + 1)
        C.put(im, box, 16, (h - bx) / 2 - 2, anchor='tl')
        x = 16 + bx + 20
        sc = C.text(g['score'], 'osw', h * 0.6, fg, 700)
        C.put(im, sc, x, h / 2 - sc.height / 2 - 2, anchor='tl')
        x += sc.width + 12
        if g['note']:
            nt = C.text(g['note'], 'osw', h * 0.24, fg, 600)
            pl = C.rrect(nt.width + 18, nt.height + 12, 8, (255, 255, 255), 64)
            C.put(pl, nt, pl.width / 2, pl.height / 2)
            C.put(im, pl, x, h / 2 - pl.height / 2 - 2, anchor='tl')
            x += pl.width + 12
        x += 12
        room = w - x - 28
        op = C.text(g['opp'].upper(), 'osw', h * 0.36, fg, 600, max_w=room)
        sub = g['date'] + ('' if g['home'] is None else (' · дома' if g['home'] else ' · в гостях'))
        st = C.text(sub, 'golos', h * 0.2, C.mix(fg, col, 0.22), 600, max_w=room)
        top = h / 2 - (op.height + 10 + st.height) / 2 - 2
        C.put(im, op, x, top, anchor='tl')
        C.put(im, st, x, top + op.height + 10, anchor='tl')
        return im

    def _post_w(self, key, n):
        cw = GEO[key]['px1'] - GEO[key]['px0']
        return cw if n == 1 else (cw - 16) // 2

    def _post_plate(self, key, p, n):
        """Дистанционный щит: белая попона с кантом цвета клуба; цифра крупно. n=2 — щит в полряда (столбиком)."""
        col = self.col[key]
        v, lab, sub = p
        h = self.stops[key]['ph']
        w = self._post_w(key, n)
        im = saddle(w, h, IVORY, pipe=col, pa=210)
        num_col = C.mix(col, (0, 0, 0), 0.12) if _lum(col) > 60 else col
        if n == 2:
            vt = C.text(v, 'osw', h * 0.5, num_col, 700, max_w=w - 40)
            lt = C.text(lab, 'osw', h * 0.21, INK, 700, track=0.04, max_w=w - 40)
            st = C.text(sub, 'golos', h * 0.15, (92, 98, 92), 600, max_w=w - 44) if sub else None
            hs = vt.height + 10 + lt.height + ((8 + st.height) if st else 0)
            y = h / 2 - hs / 2 - 2
            C.put(im, vt, w / 2, y + vt.height / 2)
            y += vt.height + 10
            C.put(im, lt, w / 2, y + lt.height / 2)
            if st:
                C.put(im, st, w / 2, y + lt.height + 8 + st.height / 2)
            return im
        vt = C.text(v, 'osw', h * 0.56, (255, 255, 255), 700)
        pw = max(int(h * 0.95), vt.width + 48)
        ph = int(h * 0.74)
        pl = saddle(pw, ph, col, rt=10, rb=ph * 0.3, pipe=None)
        C.put(pl, vt, pw / 2, ph / 2 + 1)
        C.put(im, pl, 16, (h - ph) / 2 - 2, anchor='tl')
        x = 16 + pw + 24
        room = w - x - 30
        lt = C.text(lab, 'osw', h * 0.36, INK, 700, max_w=room)
        if sub:
            st = C.text(sub, 'golos', h * 0.2, (92, 98, 92), 600, max_w=room)
            top = h / 2 - (lt.height + 10 + st.height) / 2 - 2
            C.put(im, lt, x, top, anchor='tl')
            C.put(im, st, x, top + lt.height + 10, anchor='tl')
        else:
            C.put(im, lt, x, h / 2 - lt.height / 2, anchor='tl')
        return im

    def _ghost(self, key, n):
        w, h = self._post_w(key, n), self.stops[key]['ph']
        return C.rrect(w, h, 16, (4, 18, 10), 120, outline=(70, 110, 84), width=2)

    def _bar(self, key):
        """Жердь барьера: полосатая (белый / цвет клуба), вид сверху."""
        g = GEO[key]
        w = g['lx1'] - g['lx0'] - 30
        S = 2
        im = Image.new('RGBA', (w * S, 22 * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w * S - 1, 22 * S - 1), 11 * S, fill=(250, 250, 246, 255))
        seg_w = w * S / 7
        for k in range(1, 7, 2):
            d.rectangle((k * seg_w, 0, (k + 1) * seg_w, 22 * S), fill=self.col[key] + (255,))
        m = Image.new('L', im.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, w * S - 1, 22 * S - 1), 11 * S, fill=255)
        im.putalpha(m)
        d = ImageDraw.Draw(im)
        d.line((10 * S, 6 * S, w * S - 10 * S, 6 * S), fill=(255, 255, 255, 120), width=2 * S)
        return im.resize((w, 22), Image.LANCZOS)

    def _marker(self):
        """Дистанционный столб: диск на столбике (вид сверху)."""
        im = Image.new('RGBA', (60, 60), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse((2, 2, 57, 57), fill=(206, 32, 40, 255))
        d.ellipse((12, 12, 47, 47), fill=(250, 250, 246, 255))
        d.ellipse((23, 23, 36, 36), fill=(30, 30, 30, 255))
        return im

    def _name_tag(self, key):
        col = self.col[key]
        t = C.text(self.T[key].up, 'osw', 46, on_col(col), 700, max_w=380)
        pl = saddle(t.width + 56, 74, col, rt=10, rb=22, pa=120)
        C.put(pl, t, pl.width / 2, 37)
        return pl

    def _pole(self):
        im = Image.new('RGBA', (70, 70), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse((4, 4, 66, 66), fill=(250, 250, 246, 255))
        d.ellipse((14, 14, 56, 56), fill=(206, 32, 40, 255))
        d.ellipse((26, 26, 44, 44), fill=(250, 250, 246, 255))
        return im

    def _finish(self):
        """Финишный створ: шашечная полоса между бровками + столб с круглым зеркалом судьи."""
        x0, x1 = RACE_RAILS
        w = x1 - x0
        im = Image.new('RGBA', (W, 120), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        sq = 17
        for i, x in enumerate(range(x0, x1, sq)):
            for j in range(2):
                c = (250, 250, 246, 255) if (i + j) % 2 == 0 else (16, 16, 16, 255)
                d.rectangle((x, 43 + j * sq, min(x1, x + sq) - 1, 43 + (j + 1) * sq - 1), fill=c)
        d.line((x0, 41, x1, 41), fill=(255, 255, 255, 255), width=3)
        d.line((x0, 43 + 2 * sq + 1, x1, 43 + 2 * sq + 1), fill=(255, 255, 255, 255), width=3)
        d.ellipse((x1 + 6, 16, x1 + 66, 76), fill=(250, 250, 246, 255))
        d.ellipse((x1 + 16, 26, x1 + 56, 66), fill=(206, 32, 40, 255))
        d.ellipse((x0 - 66, 16, x0 - 6, 76), fill=(250, 250, 246, 255))
        d.ellipse((x0 - 56, 26, x0 - 16, 66), fill=(206, 32, 40, 255))
        return im

    def _bursts(self, rnd):
        """Комья газона: приземления в сценах команд и половины долей на финишной прямой."""
        out = []
        for key in ('h', 'a'):
            x = GEO[key]['lane']
            for s in self.stops[key]['items']:
                te = s['t'] + s['d']
                out.append((te, x, s['y'] + TOK * 0.42, self._parts(rnd, 14, 1.0)))
        k = 0
        while self.t_run + k * 0.5 * self.u < self.drop - 0.05:
            te = self.t_run + k * 0.5 * self.u
            for key in ('h', 'a'):
                out.append((te, RACE_X[key], RACE_Y + RACE_D * 0.42, self._parts(rnd, 16, 1.5)))
            k += 1
        return out

    @staticmethod
    def _parts(rnd, n, sp):
        return [(rnd.uniform(math.pi * 0.18, math.pi * 0.82), rnd.uniform(160, 520) * sp, int(rnd.integers(0, 4)),
                 rnd.uniform(0.35, 0.7), rnd.uniform(-40, 40)) for _ in range(n)]

    # ── старт: боксы и табло тотализатора ──
    def _intro_layers(self):
        L = {}
        L['date'] = C.text('%s · %s' % (F.lg_ru(self.league), self.when), 'osw', 46, GOLD_L, 500, track=0.1, max_w=960)
        L['stall'] = self._stall()
        L['door'] = {k: self._door(k) for k in ('h', 'a')}
        L['num'] = {}
        for k in ('h', 'a'):
            cl = saddle(92, 84, self.col[k], rt=10, rb=26)
            C.put(cl, C.text('1' if k == 'h' else '2', 'osw', 62, on_col(self.col[k]), 700), 46, 42)
            L['num'][k] = cl
        L['gname'] = {k: C.with_shadow(C.text(self.T[k].up, 'osw', 78, (255, 255, 255), 700, max_w=440), 10, 0.6, 5)
                      for k in ('h', 'a')}
        L['grole'] = {k: C.text('ХОЗЯЕВА' if k == 'h' else 'ГОСТИ', 'osw', 34, GOLD_L, 500, track=0.25) for k in ('h', 'a')}
        L['tote'], L['tote_cells'] = self._tote()
        return L

    def _stall(self):
        """Стартовый бокс сверху: металлические стенки, мягкий пол, задняя штанга."""
        w, h = 452, 372
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((10, 10, w - 11, h - 11), 18, fill=(6, 22, 14, 200))
        for x0 in (0, w - 28):
            wall = C.lgrad(28, h, (214, 220, 214), (112, 122, 116), 0)
            m = C.rrect(28, h, 9, (255, 255, 255))
            wall.putalpha(m.getchannel('A'))
            im.alpha_composite(wall, (x0, 0))
        back = C.lgrad(w, 26, (196, 204, 198), (110, 120, 114), 90)
        back.putalpha(C.rrect(w, 26, 9, (255, 255, 255)).getchannel('A'))
        im.alpha_composite(back, (0, h - 26))
        d = ImageDraw.Draw(im)
        for y in range(70, h - 40, 60):                                   # мягкая обивка стенок
            d.line((8, y, 20, y), fill=(70, 80, 74, 255), width=3)
            d.line((w - 20, y, w - 8, y), fill=(70, 80, 74, 255), width=3)
        return im

    def _door(self, key):
        """Створка передних дверец (половина ширины бокса), полосы — цвет клуба и белый."""
        w, h = 200, 30
        im = Image.new('RGBA', (w * 2, h * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), 12, fill=self.col[key] + (255,))
        for x in range(-60, w * 2 + 60, 44):
            d.polygon([(x, h * 2), (x + 22, h * 2), (x + 22 + h * 2, 0), (x + h * 2, 0)], fill=(250, 250, 246, 230))
        m = Image.new('L', im.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), 12, fill=255)
        im.putalpha(m)
        ImageDraw.Draw(im).rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), 12, outline=(30, 34, 30, 255), width=4)
        return im.resize((w, h), Image.LANCZOS)

    def _tote(self):
        """Табло тотализатора: П1 · Х · П2 основного времени, янтарные цифры."""
        w, h = 990, 372
        im = C.rrect(w, h, 28, (8, 12, 10), 240, outline=GOLD, width=4)
        C.put(im, C.text('ОСНОВНОЕ ВРЕМЯ', 'osw', 36, GOLD_L, 500, track=0.3), w / 2, 44)
        cells = []
        if not self.line:
            return im, cells
        gap = 18
        cw = (w - 2 * 26 - 2 * gap) / 3
        for k, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), self.line)):
            x0 = 26 + k * (cw + gap)
            cell = C.rrect(cw, 278, 18, (2, 4, 3), 255, outline=(86, 70, 34), width=2)
            C.put(cell, C.text(lab, 'osw', 50, IVORY, 600, track=0.06), cw / 2, 44)
            ImageDraw.Draw(cell).line((14, 176, cw - 14, 176), fill=(0, 0, 0, 255), width=4)
            C.put(im, cell, x0, 76, anchor='tl')
            cells.append((x0 + 26 - 26 + cw / 2, 76 + 172, C.fmt_k(v)))
        return im, cells

    # ── фотофиниш ──
    def _photo(self, rnd):
        L = {}
        # щелевой снимок: строка финишного створа, растянутая по времени (вертикально) → полосы
        row = np.full(W, 46.0, np.float32)
        low = rnd.normal(0, 1, W // 24 + 2).astype(np.float32)
        low = np.interp(np.arange(W), np.linspace(0, W, len(low)), low)
        row += 14 * low + rnd.normal(0, 5, W)
        for x, wd, v in ((RACE_RAILS[0], 14, 190), (RACE_RAILS[1], 14, 190), (RACE_DIV, 5, 120)):
            row[max(0, x - wd // 2):x + wd // 2] = v
        for _ in range(14):
            x = int(rnd.integers(0, W))
            row[x:x + int(rnd.integers(1, 4))] += rnd.uniform(30, 80)
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        v = row[None, :] * (1.08 - 0.18 * yy) + rnd.normal(0, 2.5, (H, 1))         # чуть неровная выдержка по строкам
        rgb = np.stack([v * 0.8, v * 0.96, v * 0.86], -1)
        im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        d = ImageDraw.Draw(im)
        for y in range(JUDGE_Y + 100, 1480, 100):                                 # сетка времени
            d.line((90, y, W - 20, y), fill=(150, 170, 156, 255), width=1)
        for y in range(240, 1480, 20):                                            # шкала времени слева
            ln = 34 if (y - JUDGE_Y) % 100 == 0 else 20 if (y - JUDGE_Y) % 50 == 0 else 11
            d.line((28, y, 28 + ln, y), fill=(206, 214, 206, 255), width=2)
        d.line((28, 240, 28, 1480), fill=(206, 214, 206, 255), width=2)
        L['print'] = im
        L['judge'] = C.rrect(W - 60, 6, 3, (255, 70, 60))
        L['judge_glow'] = C.radial(W, 70, (255, 80, 60), 120, 1.5)
        # выбранная фишка + щелевой «смаз» за ней
        fav = _token(self.T[self.side], self.col[self.side], 384)
        tw, th = fav.size
        smear_h = 230
        sm = fav.crop((0, th // 2 + 30, tw, th // 2 + 31)).resize((tw, smear_h), Image.NEAREST)
        a = np.asarray(sm, np.float32).copy()
        a[..., 3] *= np.linspace(0.9, 0, smear_h, dtype=np.float32)[:, None] ** 1.4
        sm = Image.fromarray(a.astype(np.uint8), 'RGBA')
        comb = Image.new('RGBA', (tw, th + smear_h - th // 2), (0, 0, 0, 0))
        comb.alpha_composite(sm, (0, th // 2))
        comb.alpha_composite(fav, (0, 0))
        L['fav'] = comb
        L['fav_sh'] = C.shadow(fav, 22, 0.7)
        L['flash_ring'] = C.radial(900, 900, (255, 250, 236), 255, 1.4)
        L['p1'] = C.with_shadow(C.text(self.pick1, 'osw', 124, (255, 255, 255), 700, max_w=990), 14, 0.7, 6)
        L['p2'] = C.text(self.pick2, 'osw', 56, GOLD_L, 500, track=0.12, max_w=960) if self.pick2 else None
        kt = C.text('КЭФ ' + C.fmt_k(self.coef), 'osw', 112, GOLD_D, 700)
        kp = saddle(kt.width + 120, 176, GOLD, rt=14, rb=52, pipe=(255, 248, 220), pa=220)
        C.put(kp, kt, kp.width / 2, 88)
        L['kef'] = kp
        L['kef_sh'] = C.shadow(kp, 18, 0.65)
        return L

    # ─────────────────────────────── сцены ───────────────────────────────
    def gallop(self, t, ph=0.0):
        """Подскок галопа: два толчка на долю."""
        x = ((t / self.u) * 2 + ph) % 1.0
        return abs(math.sin(math.pi * x))

    def burst(self, fr, t, x0=None, keys=None):
        L = self.L
        for te, x, y, parts in L['bursts']:
            dt = t - te
            if dt < 0 or dt > 0.75:
                continue
            if x0 is not None and abs(x - x0) > 10:
                continue
            for ang, sp, si, life, sw in parts:
                if dt > life:
                    continue
                k = dt / life
                dist = sp * dt * (1 - 0.45 * k)
                px = x + math.cos(ang) * dist * 0.7 + sw * dt
                py = y + math.sin(ang) * dist
                C.put(fr, L['dust'][si], px, py, (1 - k) ** 1.3)

    def intro(self, t):
        L, u = self.L, self.u
        fr = L['bg_intro'].copy()
        qd = C.out_expo(C.seg(t, 0.0, 0.35))
        C.put(fr, L['date'], W / 2, 338 + 16 * (1 - qd), qd)
        og = C.out_cubic(C.seg(t, self.t_gate, self.t_gate + 0.22))                # дверцы открываются на долю
        for k, cx, d0 in (('h', 282, 0.0), ('a', 798, 0.08)):
            q = C.out_back(C.seg(t, d0, d0 + 0.45), 1.2)
            y0 = 478 + 60 * (1 - q)
            st = L['stall']
            C.put(fr, st, cx, y0 + st.height / 2, min(1.0, q * 1.4))
            # фишка: на открытии дверец рвётся вперёд
            surge = 70 * C.out_cubic(C.seg(t, self.t_gate + 0.05, self.t_gate + 0.5))
            bob = 5 * self.gallop(t, 0.3 if k == 'a' else 0) if t >= self.t_gate else 2 * math.sin(t * 5 + d0 * 20)
            tok = L['tok_gate'][k]
            ty = y0 + 196 - surge - bob
            C.put(fr, L['tok_gate_sh'][k], cx + 8 + 10 * surge / 70, ty + 14, min(1.0, q * 1.4) * 0.85)
            C.put(fr, tok, cx, ty, min(1.0, q * 1.4))
            # дверцы
            for sg in (-1, 1):
                dr = L['door'][k]
                hinge_x = cx + sg * (st.width / 2 - 26)
                ang = sg * 82 * og
                im = dr if sg < 0 else dr.transpose(Image.FLIP_LEFT_RIGHT)
                pad = Image.new('RGBA', (dr.width * 2, dr.width * 2), (0, 0, 0, 0))
                px = dr.width if sg < 0 else 0
                pad.alpha_composite(im, (px, dr.width - dr.height // 2))
                pad = pad.rotate(ang, Image.BICUBIC, center=(dr.width, dr.width)) if ang else pad
                C.put(fr, pad, hinge_x, y0 + 14, min(1.0, q * 1.4))
            C.put(fr, L['num'][k], cx, y0 - 52, min(1.0, q * 1.4))
            qn = C.out_expo(C.seg(t, 0.2 + d0, 0.6 + d0))
            C.put(fr, L['gname'][k], cx, 910 + 24 * (1 - qn), qn)
            C.put(fr, L['grole'][k], cx, 968, qn)
        # табло
        qt = C.out_expo(C.seg(t, 0.3, 0.75))
        if qt > 0:
            tote = L['tote']
            ty = 1196 + 60 * (1 - qt)
            C.put(fr, tote, W / 2, ty, qt)
            x0 = W / 2 - tote.width / 2
            y0 = ty - tote.height / 2
            settle = u                                                     # цифры встают на первую долю
            for i, (cx, cy, v) in enumerate(L['tote_cells']):
                ts = settle + 0.08 * i
                if t < ts:
                    rr = (int(t * 30) * 7 + i * 13) % 900 + 100
                    s = '%d.%02d' % (rr // 100, rr % 100)
                    im = C.text(s, 'osw', 150, C.mix(AMBER, (0, 0, 0), 0.35), 700)
                    C.put(fr, im, x0 + cx, y0 + cy, qt)
                else:
                    im = self._amber(v)
                    pk = 1 + 0.08 * (1 - C.seg(t, ts, ts + 0.25)) ** 2
                    C.put(fr, C.scale(im, pk), x0 + cx, y0 + cy)
        return fr

    def _amber(self, v):
        key = ('amber', v)
        if key not in _CACHE:
            _CACHE[key] = C.glow(C.text(v, 'osw', 150, AMBER, 700), 14, 0.9, (255, 150, 30))
        return _CACHE[key]

    def team(self, key, t):
        L, u = self.L, self.u
        g, S = GEO[key], self.stops[key]
        t0 = self.t1 if key == 'h' else self.t2
        fr = L['bg_' + key].copy()
        hd, sb = L['head_' + key]
        cx = (g['px0'] + g['px1']) / 2
        q = C.out_expo(C.seg(t, t0, t0 + 0.4))
        sg = -1 if key == 'h' else 1
        C.put(fr, hd, cx + sg * 50 * (1 - q), 346, q)
        C.put(fr, sb, cx, 424, C.seg(t, t0 + 0.15, t0 + 0.45))
        items = S['items']
        # плашки: пустые места → попона на долю (щиты ряда — через половину доли)
        for k, s in enumerate(items):
            y = s['y']
            pls = L['plates_' + key][k]
            n = len(pls)
            for j, (pl, tj) in enumerate(zip(pls, s['ts'])):
                x = cx if n == 1 else g['px0'] + pl.width / 2 + j * (pl.width + 16)
                pq = C.out_expo(C.seg(t, tj, tj + 0.32))
                if pq < 1:
                    C.put(fr, L['ghost_' + key][n], x, y, 1 - pq)
                if pq > 0:
                    C.put(fr, pl, x + sg * 90 * (1 - pq), y, min(1.0, pq * 1.6))
                    if pq < 1:                                               # блик по попоне
                        xs = x - pl.width / 2 + pl.width * (pq * 1.3 - 0.15) if key == 'h' else \
                            x + pl.width / 2 - pl.width * (pq * 1.3 - 0.15)
                        fr = C.add_light(fr, L['glint'], xs, y, 0.6 * (1 - pq)).convert('RGBA')
        # барьеры и столбы
        lane = g['lane']
        for k, s in enumerate(items):
            if s['typ'] == 'g':
                for sx in (g['lx0'] + 9, g['lx1'] - 9):
                    C.put(fr, L['stand'], sx, s['bar'])
                bar = L['bar_' + key]
                if s['it']['res'] == 'П' and t >= s['t'] - 0.02:          # поражение — жердь сбита
                    kq = C.out_back(C.seg(t, s['t'] - 0.02, s['t'] + 0.3), 1.6)
                    im = C.rotate(bar, -sg * 17 * kq)
                    C.put(fr, C.shadow(im, 6, 0.6), lane + 6, s['bar'] + 26 * kq + 8)
                    C.put(fr, im, lane + 10 * kq, s['bar'] + 26 * kq, 1 - 0.25 * kq)
                else:
                    C.put(fr, C.shadow(bar, 6, 0.6), lane + 4, s['bar'] + 8)
                    fl = 1 - C.seg(t, s['t'], s['t'] + 0.35) if t >= s['t'] else 0
                    C.put(fr, bar, lane, s['bar'])
                    if fl > 0:
                        fr = C.add_light(fr, L['bar_glow'], lane, s['bar'], fl).convert('RGBA')
            else:
                mx = g['div']
                C.put(fr, L['marker'], mx, s['bar'])
                for tj in s['ts']:
                    if tj <= t < tj + 0.35:
                        fr = C.add_light(fr, L['mark_glow'], mx, s['bar'], 1 - C.seg(t, tj, tj + 0.35)).convert('RGBA')
        # фишка: позиция и прыжок
        y, hgt, spd = S['start'], 0.0, 0.0
        for s in items:
            if t >= s['t'] - s['d']:
                k = C.seg(t, s['t'] - s['d'], s['t'] + s['d'])
                y = C.lerp(s['y_prev'], s['y'], C.in_out(k))
                if k < 1:
                    hgt = math.sin(math.pi * k) * (1.0 if s['typ'] == 'g' else 0.35)
                    spd = math.sin(math.pi * k)
        bob = 0.0 if hgt > 0.05 else 0.12 * self.gallop(t)
        hh = max(hgt, bob)
        if spd > 0.05:                                                       # линии скорости за фишкой
            for j, dx in enumerate((-46, 0, 46)):
                C.put(fr, L['streak'][j], lane + dx, y + TOK * 0.5 + 90 + 30 * j, 0.35 * spd)
        self.burst(fr, t, lane)
        tok = L['tok'][key]
        sc = 1 + 0.22 * hh
        C.put(fr, L['tok_sh'][key], lane + 8 + 34 * hh, y + 14 + 46 * hh, 1 - 0.45 * hh)
        C.put(fr, C.scale(tok, sc), lane, y - 6 * hh)
        return fr

    def run(self, t):
        """Финишная прямая: газон летит вниз, обе фишки голова в голову, сверху надвигается створ."""
        L, u, D = self.L, self.u, self.drop
        lt = t - self.t_run
        T = D - self.t_run
        v0, acc = 1500.0, 900.0
        s = v0 * lt + 0.5 * acc * lt * lt
        sD = v0 * T + 0.5 * acc * T * T
        off = int(s) % P
        crop = L['track_run'].crop((0, P - off, W, P - off + H))
        fr = ImageChops.add(crop, L['light']).convert('RGBA')
        # дистанционные столбы у бровок
        for k in range(-2, 12):
            yw = (s % 640) + k * 640 - 640
            if -60 < yw < H + 60:
                C.put(fr, L['pole'], RACE_RAILS[0] - 34, yw)
                C.put(fr, L['pole'], RACE_RAILS[1] + 34, yw)
        # линии скорости
        sp = v0 + acc * lt
        for x, si, y0, f, a in L['speed']:
            yy = (y0 + s * f) % (H + 800) - 400
            C.put(fr, L['streak'][si], x, yy, a * min(1.0, sp / 1800))
        # финишный створ
        yf = (RACE_Y - RACE_D / 2 - 20) - (sD - s)
        if yf > -140:
            C.put(fr, L['finish'], W / 2, yf)
        self.burst(fr, t)
        # фишки голова в голову: лидер меняется на каждую долю, к финишу — ровно
        ph = lt / u
        lead = 34 * math.sin(math.pi * ph) * (1 - C.seg(t, D - 0.35, D))
        for key, sgn, gp in (('h', 1, 0.0), ('a', -1, 0.5)):
            x = RACE_X[key]
            y = RACE_Y - sgn * lead
            hb = self.gallop(t, gp)
            C.put(fr, L['names_run'][key], x, y + RACE_D / 2 + 64)
            C.put(fr, L['tok_run_sh'][key], x + 10 + 20 * hb, y + 18 + 26 * hb, 0.9 - 0.3 * hb)
            C.put(fr, C.scale(L['tok_run'][key], 1 + 0.06 * hb), x, y - 8 * hb)
        return fr

    def photo(self, t):
        """Фотофиниш: щелевой снимок, только команда прогноза, прогноз и кэф."""
        L, u, D = self.L, self.u, self.drop
        fr = L['print'].copy()
        ck = C.in_out(C.seg(t, self.t_cta, self.t_cta + 0.55))
        pulse = math.exp(-(((t - D) / u) % 1.0) * 7) if t >= D else 0.0
        jy = JUDGE_Y - 40 * ck
        fr = C.add_light(fr, L['judge_glow'], W / 2, jy, 0.6 + 0.6 * pulse).convert('RGBA')
        C.put(fr, L['judge'], W / 2, jy)
        # фишка выбранной команды: нос — за линией судьи
        fs = (1.0 - 0.22 * ck) * (1 + 0.025 * pulse)
        fav = C.scale(L['fav'], fs) if abs(fs - 1) > 0.002 else L['fav']
        tok_d = 384 * fs
        cy = jy - 18 + tok_d / 2
        C.put(fr, C.scale(L['fav_sh'], fs), W / 2 + 10, cy + 24, 0.9)
        C.put(fr, fav, W / 2, cy - tok_d / 2 + fav.height / 2)
        # прогноз
        y1 = C.lerp(912, 800, ck)
        q1 = C.out_expo(C.seg(t, D + 0.04, D + 0.3))
        C.put(fr, C.scale(L['p1'], 1.25 - 0.25 * q1), W / 2, y1, min(1.0, q1 * 1.8))
        if L['p2'] is not None:
            q2 = C.out_expo(C.seg(t, D + 0.2, D + 0.5))
            C.put(fr, L['p2'], W / 2, y1 + 104 + 20 * (1 - q2), q2)
        qk = C.out_back(C.seg(t, D + u, D + u + 0.4), 1.6)
        if qk > 0.01:
            ky = C.lerp(1192, 1048, ck)
            kp = C.scale(L['kef'], max(0.05, (0.5 + 0.5 * qk) * (1 + 0.02 * pulse * (t >= D + 2 * u))))
            C.put(fr, C.scale(L['kef_sh'], kp.width / L['kef'].width), W / 2 + 8, ky + 22, min(1.0, qk))
            C.put(fr, kp, W / 2, ky, min(1.0, qk * 1.5))
        # проявка сканом сверху вниз, вспышка
        if t < D + 0.42:
            ys = 200 + (H - 200) * C.out_cubic(C.seg(t, D, D + 0.3))
            wa = 1 - C.seg(t, D + 0.12, D + 0.42)
            cover = Image.new('RGBA', (W, max(1, int(H - ys))), (255, 252, 244, int(255 * wa)))
            C.put(fr, cover, 0, ys, anchor='tl')
            if ys < H:
                fr = C.add_light(fr, C.radial(W * 2, 120, (255, 246, 220), 255, 1.2), W / 2, ys, 1.2 * wa).convert('RGBA')
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.2, self.t_cta + 0.65))
            if q > 0:
                C.put(fr, C.shadow(L['tg'], 20, 0.6 * q), W / 2, 1290 + 18 + 160 * (1 - q))
                C.put(fr, L['tg'], W / 2, 1290 + 160 * (1 - q), q)
        return fr

    # ─────────────────────────────── кадр ───────────────────────────────
    def scene(self, t):
        if t < self.t1:
            return self.intro(t)
        if t < self.t2:
            return self.team('h', t)
        if t < self.t_run:
            return self.team('a', t)
        if t < self.drop:
            return self.run(t)
        return self.photo(t)

    def frame(self, t):
        u, D = self.u, self.drop
        L = self.L
        fr = self.scene(t)
        z, dx, dy, cx, cy = 1.0, 0.0, 0.0, W / 2, H / 2
        # склейки на долю: наезд в дорожку 1, переброс на дорожку 2, рывок на финишную прямую
        a1, b1 = 0.16, 0.22
        if self.t1 - a1 <= t < self.t1:                                   # наезд в бокс 1
            q = C.in_cubic(C.seg(t, self.t1 - a1, self.t1))
            z, cx, cy = 1 + 1.3 * q, 282, 674
            fr = C.zoom(fr.convert('RGB'), z, cx, cy)
            fr = Image.blend(fr, vblur(fr, 18), 0.8 * q)
            z = 1.0
        elif self.t1 <= t < self.t1 + b1:
            q = C.out_cubic(C.seg(t, self.t1, self.t1 + b1))
            fr = C.zoom(fr.convert('RGB'), 1 + 0.35 * (1 - q), GEO['h']['lane'], self.stops['h']['start'])
            fr = Image.blend(fr, vblur(fr, 18), 0.7 * (1 - q))
        for tb, kind in ((self.t2, 'x'), (self.t_run, 'y')):
            if tb - a1 <= t < tb + b1:
                if t < tb:
                    q = C.in_cubic(C.seg(t, tb - a1, tb))
                    off = -int(760 * q) if kind == 'x' else int(760 * q)
                else:
                    q = C.out_cubic(C.seg(t, tb, tb + b1))
                    off = int(760 * (1 - q)) if kind == 'x' else -int(760 * (1 - q))
                    q = 1 - q
                rgb = fr.convert('RGB')
                rgb = ImageChops.offset(rgb, off, 0) if kind == 'x' else ImageChops.offset(rgb, 0, off)
                fr = Image.blend(rgb, hblur(rgb, 22) if kind == 'x' else vblur(rgb, 22), min(1.0, 0.95 * q + 0.1))
        fr = fr.convert('RGB')
        # камера: толчок на каждой попоне, дрожь к финишу, удар на дроп
        for key in ('h', 'a'):
            for s in self.stops[key]['items']:
                if s['t'] <= t < s['t'] + 0.3:
                    z += 0.012 * (1 - C.seg(t, s['t'], s['t'] + 0.3)) ** 2
        if self.t_run <= t < D:
            q = C.seg(t, self.t_run, D)
            z += 0.05 * C.in_cubic(q)
            dx += (3 + 9 * q) * math.sin(t * 77)
            dy += (3 + 9 * q) * math.cos(t * 59)
        if t >= D:
            sx, sy = C.shake(t, D, 26, 0.45)
            dx, dy = dx + sx, dy + sy
            z += 0.07 * (1 - C.seg(t, D, D + 0.45)) ** 2
            for k in range(1, 12):
                tb = D + k * u
                if tb <= t < tb + 0.25 and tb < self.t_cta:
                    z += 0.012 * (1 - C.seg(t, tb, tb + 0.25)) ** 2
        if z > 1.0005 or dx or dy:
            fr = C.zoom(fr, z, cx, cy, dx=dx, dy=dy)
        fr = fr.convert('RGBA')
        # шапка и @jarvibet — поверх, неподвижно
        C.put(fr, L['tag'], W / 2, TAG_Y, 0.9 * C.seg(t, 0, 0.3))
        ha = 0.92 * C.seg(t, 0.2, 0.5)
        if t >= self.t_cta:
            ha *= 1 - C.seg(t, self.t_cta + 0.1, self.t_cta + 0.35)
        C.put(fr, L['handle'], W / 2, HANDLE_Y, ha)
        fr = fr.convert('RGB')
        if D <= t < D + 1 / 30 + 0.001:                                      # кадр-вспышка фотокамеры
            fr = Image.blend(fr, Image.new('RGB', fr.size, (255, 253, 246)), 0.85)
        if D - 0.1 <= t < D:
            fr = Image.blend(fr, Image.new('RGB', fr.size, (255, 250, 236)), 0.35 * C.seg(t, D - 0.1, D))
        fr = C.vignette(fr, 0.5)
        return C.grain(fr, t, 4)
