# -*- coding: utf-8 -*-
"""«Кино» — прогноз как трейлер и титры фильма: каше (чёрные полосы ровно за краями безопасной зоны), плёночное зерно,
пыль и мерцание проектора, анаморфные блики (длинные голубые полосы света), лучи за эмблемой, грейдинг «тил-оранж»
(хозяева — тёплый оранжевый свет, гости — холодный бирюзовый), медленные наезды камеры, затемнения в чёрное на долях.
Шрифты — антиква Playfair (имена, счёт, кэфы), Tenor Sans разрядкой (даты, подписи), курсив Cormorant (роли и исходы).
Не газета (paper) и не презентация (keynote): каждая команда — «персонаж» со своим титром, факты — строки титров.

Сцены (u — доля трека, D — дроп; доли от дропа; team / build / hold / cta — параметры):
  интро (до D − (2·team + build) долей) — «фильм в двух частях»: обе эмблемы с лучами (I и II над ними), названия,
        «против» между ними, время МСК и линия основного времени П1 · Х · П2 крупными плашками в двойной золотой рамке;
  команда ×2 (team долей) — из черноты на долю: титр-«герой» (эмблема крупно в лучах, анаморфный блик проходит по кадру,
        огромное имя, «в роли хозяев / гостей», три медальона В/П); через 2 доли эмблема и имя уезжают наверх и идут
        титры: 3 последние игры (дата · дома/в гостях, соперник и счёт крупно, исход курсивом; ОТ/Б — пометка у счёта)
        по строке на полдоли, затем строка сезона — очки за N матчей, место, разница шайб (пустые поля не показываются);
        в конце — затемнение в чёрное ровно на долю;
  трейлер (build долей) — быстрые склейки эмблем двух клубов в одном плане (match cut), всё чаще: полдоли, четверти;
        перед дропом — 0,09 с черноты;
  ДРОП (hold долей) — «афиша»: вспышка и ровно на дропе только выбранная команда (одна эмблема, без второй и «VS»),
        прогноз как название фильма (form.split_pick), кэф — как строка даты премьеры, ниже время матча;
        блик и лучи пульсируют на каждую долю;
  финал (cta долей) — затемнение на долю, эмблема, прогноз, кэф, время и плашка Telegram (C.tg_plate, текст по центру).
@jarvibet — «субтитр» у низа безопасной зоны (y 1440), одинаково во всех сценах (и поверх затемнений) до финала,
в финале его несёт плашка Telegram.
lag — на сколько долей настоящий удар трека позже точки дропа сборки (withyou, точка 52,11 с: удар 808 — 52,637 с,
0,641 доли): видимый дроп self.drop = drop + lag·u — афиша встаёт точно на удар, сетка долей совпадает с ударами трека.
Кадр — чистая функция t (зерно, пыль и мерцание — от номера кадра); фоны, эмблемы и титры кешируются на уровне модуля.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels import fresh
from reels.core import W, H

BAR_T, BAR_B = 206, 1504                 # каше: картинка — только между полосами (чуть шире безопасной зоны)
INK = (246, 238, 224)                    # тёплый белый титров
GOLD = (226, 190, 126)
GOLD2 = (255, 214, 148)
DIM = (186, 194, 192)
WINC = (128, 220, 160)
LOSSC = (244, 110, 92)
NEUT = (190, 190, 200)
FLARE = (96, 176, 255)                   # анаморфный блик
WARM = (255, 158, 72)                    # свет хозяев
TEAL = (64, 200, 214)                    # свет гостей
Y_TAG, Y_HANDLE = 268, 1440
ROMAN = {'h': 'I', 'a': 'II'}

_S, _BG, _RB, _RP, _FL, _GR = {}, {}, {}, {}, {}, []


# ─────────────────────────────── спрайты ───────────────────────────────
def _spr(key, fn):
    if key not in _S:
        _S[key] = fn()
    return _S[key]


def txt(s, name, size, col=INK, track=0.0, max_w=None, wght=700, shade=True):
    """Строка титра с мягкой тенью (центр картинки = центр строки)."""
    def mk():
        im = C.text(s, name, size, col, wght, track=track, max_w=max_w)
        if shade:
            r = max(4, int(size) // 9)
            im = C.with_shadow(im, r, 0.6, max(2, int(size) // 22))
        return im
    return _spr(('t', s, name, int(size), col, track, max_w, wght, shade), mk)


def blur(im, r=9):
    """Расфокусированная копия (для «перевода фокуса» при появлении)."""
    return _spr(('blur', id(im), r), lambda: im.filter(ImageFilter.GaussianBlur(r)))


def hline(w, col=GOLD, a=220, th=2):
    """Тонкая золотая линейка, к краям тает."""
    def mk():
        x = np.linspace(-1, 1, int(w))
        al = (np.clip(1 - np.abs(x) ** 6, 0, 1) * a).astype(np.uint8)
        arr = np.zeros((th, int(w), 4), np.uint8)
        arr[..., :3] = col
        arr[..., 3] = al[None, :]
        return Image.fromarray(arr, 'RGBA')
    return _spr(('hl', int(w), col, a, th), mk)


def frame_plate(w, h, a=150):
    """Плашка в двойной золотой рамке (как титры старого кино)."""
    def mk():
        ss = 2
        im = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, w * ss - 1, h * ss - 1), fill=(4, 12, 16, a))
        d.rectangle((0, 0, w * ss - 1, h * ss - 1), outline=GOLD + (235,), width=2 * ss)
        i = 11 * ss
        d.rectangle((i, i, w * ss - 1 - i, h * ss - 1 - i), outline=GOLD + (95,), width=ss)
        for cx, cy in ((i, i), (w * ss - 1 - i, i), (i, h * ss - 1 - i), (w * ss - 1 - i, h * ss - 1 - i)):
            r = 5 * ss
            d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=GOLD + (230,))
        return im.resize((w, h), Image.LANCZOS)
    return _spr(('fp', w, h, a), mk)


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def streak_txt(s):
    """«В3» → «3 ПОБЕДЫ ПОДРЯД» (серии от двух игр; прочее — пусто)."""
    s = str(s or '').strip().upper()
    if len(s) < 2 or not s[1:].isdigit() or int(s[1:]) < 2:
        return ''
    n = int(s[1:])
    if s[0] in ('В', 'W'):
        return '%d %s ПОДРЯД' % (n, plural(n, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'))
    if s[0] in ('П', 'L'):
        return '%d %s ПОДРЯД' % (n, plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ'))
    return ''


def outcome(g):
    """Исход игры словами: «победа», «поражение по буллитам», «победа в овертайме»."""
    base = 'победа' if g['res'] == 'В' else 'поражение' if g['res'] == 'П' else ''
    tail = {'ОТ': 'в овертайме', 'Б': 'по буллитам', 'ОТ/Б': 'после основного времени'}.get(g['note'], '')
    return (base + ' ' + tail).strip()


def res_col(r):
    return WINC if r == 'В' else LOSSC if r == 'П' else NEUT


# ─────────────────────────────── свет: лучи, блики, зерно ───────────────────────────────
def _add(arr, src, cx, cy):
    """Сложить свет src (uint8 h×w×3) в arr центром в (cx, cy), с насыщением."""
    h, w = src.shape[:2]
    x, y = int(round(cx - w / 2)), int(round(cy - h / 2))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(arr.shape[1], x + w), min(arr.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return
    reg = arr[y0:y1, x0:x1].astype(np.uint16)
    reg += src[y0 - y:y1 - y, x0 - x:x1 - x]
    np.minimum(reg, 255, out=reg)
    arr[y0:y1, x0:x1] = reg


def _ray_base(n):
    if n not in _RB:
        y, x = np.mgrid[0:n, 0:n].astype(np.float32)
        dx, dy = x - n / 2 + 0.5, y - n / 2 + 0.5
        idx = ((np.arctan2(dy, dx) + np.pi) / (2 * np.pi) * 1024).astype(np.int32) % 1024
        r = np.sqrt(dx * dx + dy * dy) / (n / 2)
        fall = (np.clip(1 - r, 0, 1) ** 1.8 * np.clip(r * 3.5, 0, 1)).astype(np.float32)
        _RB[n] = (idx, fall)
    return _RB[n]


def _ray_pat(seed):
    if seed not in _RP:
        rng = np.random.default_rng(seed)
        i = np.arange(1024)
        p = np.zeros(1024)
        for k in (5, 9, 13, 17, 22, 29, 37):
            p += rng.uniform(0.4, 1.0) * np.cos(2 * np.pi * k * i / 1024 + rng.uniform(0, 6.283))
        p = (p - p.min()) / (p.max() - p.min())
        _RP[seed] = (0.10 + 0.9 * p ** 2.4).astype(np.float32)
    return _RP[seed]


def rays(arr, cx, cy, size, rot, k, col, seed=3):
    """Лучи прожектора из-за эмблемы (считаются в половинном размере, медленно вращаются)."""
    if k <= 0.01:
        return
    n = max(16, int(size) // 2)
    idx, fall = _ray_base(n)
    p = np.roll(_ray_pat(seed), int(rot * 1024) % 1024)
    v = p[idx] * fall
    rgb = (v[..., None] * (np.array(col, np.float32) * k)).clip(0, 255).astype(np.uint8)
    _add(arr, np.asarray(Image.fromarray(rgb).resize((n * 2, n * 2), Image.BILINEAR)), cx, cy)


def _flare_strip():
    if not _FL:
        hh, ww = 160, 3 * W
        y = (np.arange(hh) - hh / 2)[:, None]
        x = (np.arange(ww) - ww / 2)[None, :]
        core = np.exp(-(y / 2.4) ** 2) * (0.9 * np.exp(-(x / 600) ** 2) + 0.28 * np.exp(-(x / 1700) ** 2))
        haze = np.exp(-(y / 22) ** 2) * 0.32 * np.exp(-(x / 340) ** 2)
        hot = np.exp(-((x / 70) ** 2 + (y / 40) ** 2))
        _FL['c'] = (core + haze).astype(np.float32)
        _FL['h'] = hot.astype(np.float32)
    return _FL['c'], _FL['h']


def flare(arr, cx, cy, k, col=FLARE):
    """Анаморфный блик: тонкая длинная голубая полоса через весь кадр + белое ядро в (cx, cy)."""
    if k <= 0.01:
        return
    c, h = _flare_strip()
    ww = c.shape[1]
    x0 = int(round(ww / 2 - cx))
    x0 = max(0, min(ww - W, x0))
    cc, hc = c[:, x0:x0 + W], h[:, x0:x0 + W]
    rgb = cc[..., None] * (np.array(col, np.float32) * k) + hc[..., None] * (np.array((255, 250, 240), np.float32) * 0.75 * k)
    _add(arr, rgb.clip(0, 255).astype(np.uint8), W / 2, cy)
    # «призраки» объектива — два мягких кольца по линии через центр кадра
    for f, r, a in ((-0.55, 46, 0.16), (-1.15, 80, 0.10)):
        gx, gy = W / 2 + (cx - W / 2) * f, H / 2 + (cy - H / 2) * f
        g = _spr(('ghost', r), lambda r=r: np.asarray(C.radial(2 * r, 2 * r, (255, 255, 255), 255, 0.7).convert('RGBA')))
        al = g[..., 3:4].astype(np.float32) / 255
        _add(arr, (al * np.array(col, np.float32) * a * k * 1.4).clip(0, 255).astype(np.uint8), gx, gy)


def _grain_frames():
    if not _GR:
        rng = np.random.default_rng(11)
        ph = BAR_B - BAR_T
        for _ in range(8):
            g = rng.normal(0, 1, (ph // 2 + 1, W // 2 + 1)).astype(np.float32)
            g = np.repeat(np.repeat(g, 2, 0), 2, 1)[:ph, :W]
            _GR.append((g * 7).astype(np.int16))
    return _GR


# ─────────────────────────────── ролик ───────────────────────────────
class Cinema(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 73, drop=20 * 60 / 73, line=None, team=7, build=2,
                 hold=5, cta=3, lag=0.0, seed=29, **kw):
        super().__init__(u, drop + lag * u, seed)
        self.line = tuple(line) if line else None
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.pick = league, when, coef, pick
        self.tag = F.tag(league)
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
        self.rec = {'h': sh or {}, 'a': sa or {}}
        self.s = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.team, self.build, self.hold = team, build, hold
        self.T1 = self.b(-(2 * team + build))
        if self.T1 < 2.4:
            raise ValueError('мало времени до дропа для интро')
        self.T2 = self.b(-(team + build))
        self.TB = self.b(-build)
        self.TC = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = round(self.T1 - 0.45, 2)
        self.key = (home, away, league, when, pick, coef, self.line, seed)
        self.light = {'h': WARM, 'a': TEAL}
        self.club = {'h': fresh.club(self.h), 'a': fresh.club(self.a)}

    def tm(self, side):
        return self.h if side == 'h' else self.a

    # ── фоны ──
    def _bg(self, kind):
        key = (self.key, kind)
        if key in _BG:
            return _BG[key]
        rng = np.random.default_rng(self.seed * 31 + sum(ord(c) for c in kind))
        base = C.vgrad(W, H, [(0, (4, 14, 18)), (0.3, (9, 30, 38)), (0.62, (7, 24, 30)), (1, (3, 9, 12))])
        if kind == 'intro':
            base = C.add_light(base, C.radial(1500, 1500, WARM, 120, 1.6), 140, 640)
            base = C.add_light(base, C.radial(1500, 1500, TEAL, 105, 1.6), 940, 640)
            for side, x in (('h', 230), ('a', 850)):
                big = self.tm(side).emb(1100).filter(ImageFilter.GaussianBlur(30))
                lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                C.put(lay, C.fade(big, 0.16), x, 1180)
                base = base.convert('RGBA')
                base.alpha_composite(lay)
                base = base.convert('RGB')
        else:
            side = {'h': 'h', 'a': 'a'}.get(kind, self.side)
            tm, lc = self.tm(side), self.light[side]
            cc = fresh.bright(self.club[side], 0.25)
            dark = 0.7 if kind == 'end' else 1.0
            base = C.add_light(base, C.radial(1600, 1600, cc, int(70 * dark), 1.7), W / 2, 640)
            base = C.add_light(base, C.radial(1700, 1700, lc, int(130 * dark), 1.5), -60 if side == 'h' else W + 60, 520)
            base = C.add_light(base, C.radial(1300, 1300, lc, int(60 * dark), 1.6), W + 100 if side == 'h' else -100, 1300)
            big = tm.emb(1500).filter(ImageFilter.GaussianBlur(34))
            lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            C.put(lay, C.fade(big, 0.14 * dark), W * (0.7 if side == 'h' else 0.3), 1220)
            base = base.convert('RGBA')
            base.alpha_composite(lay)
            base = base.convert('RGB')
        # дымка: низкочастотный шум, «воздух» в луче проектора
        sm = rng.normal(0, 1, (12, 7)).astype(np.float32)
        sm = np.asarray(Image.fromarray(((sm - sm.min()) / (np.ptp(sm) + 1e-6) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                        np.float32) / 255
        arr = np.asarray(base, np.float32) * (0.78 + 0.4 * sm[..., None])
        # тил-оранж: тени в бирюзу, света в тёплое
        lum = arr.mean(2, keepdims=True) / 255
        arr = arr + (1 - lum) * np.array([-4, 3, 6], np.float32) * 2 + lum * np.array([10, 2, -8], np.float32)
        img = Image.fromarray(arr.clip(0, 255).astype(np.uint8), 'RGB')
        img = C.vignette(img, 0.62, 2.0)
        _BG[key] = img
        return img

    def _emb(self, side, size, glow=True):
        tm = self.tm(side)

        def mk():
            e = tm.emb(size)
            if not glow:
                return e
            g = C.glow(e, max(10, size // 22), 0.9, fresh.bright(self.light[side], 0.2))
            return g
        return _spr(('emb', self.key, side, size, glow), mk)

    # ── появление ──
    @staticmethod
    def show(fr, im, x, y, t, t0, d=0.4, kind='focus', a=1.0, rise=26, s0=1.06):
        """Титр: «перевод фокуса» (из размытия в резкость) с лёгким подъёмом / наездом."""
        if t < t0 or a <= 0.003:
            return
        q = C.seg(t, t0, t0 + d)
        if q >= 1:
            C.put(fr, im, x, y, a)
            return
        e = C.out_cubic(q)
        if kind == 'rise':
            y += rise * (1 - e)
        elif kind == 'zoom':
            im = C.scale(im, 1 + (s0 - 1) * (1 - e))
        elif kind == 'wipe':
            w = max(1, int(im.width * e))
            C.put(fr, im.crop(((im.width - w) // 2, 0, (im.width - w) // 2 + w, im.height)), x, y, a)
            return
        bl = blur(im) if kind != 'zoom' else None
        if bl is not None and q < 0.8:
            C.put(fr, bl, x, y, a * min(1.0, q * 3) * (1 - q / 0.8))
        C.put(fr, im, x, y, a * e)

    # ── сцены ──
    def _scene(self, t):
        if t < self.T1:
            return 'intro'
        if t < self.T2:
            return 'h'
        if t < self.TB:
            return 'a'
        if t < self.drop:
            return 'build'
        if t < self.TC:
            return 'pick'
        return 'end'

    def _intro(self, t):
        u, T1 = self.u, self.T1
        b0 = self.b(-(2 * self.team + self.build) - 4)          # первая доля ролика, на которой ставятся акценты
        while b0 < 0.25:
            b0 += u
        z = 1.0 + 0.045 * C.seg(t, 0, T1)
        arr = np.array(C.zoom(self._bg('intro'), z, W / 2, 700))
        ap = [C.out_cubic(C.seg(t, 0.12 + 0.18 * k, 0.9 + 0.18 * k)) for k in range(2)]
        for k, (side, x) in enumerate((('h', 270), ('a', 810))):
            pulse = sum(0.25 * (1 - C.seg(t, self.b(n), self.b(n) + 0.5)) ** 2 for n in range(-20, -15) if t >= self.b(n))
            rays(arr, x, 545, 820, t * 0.012 + 0.3 * k, (0.55 + pulse) * ap[k], self.light[side], seed=3 + k)
        fr = Image.fromarray(arr).convert('RGBA')
        self.show(fr, txt(self.tag, 'tenor', 34, GOLD, 0.32), W / 2, Y_TAG, t, 0.1, 0.6)
        for k, (side, x) in enumerate((('h', 270), ('a', 810))):
            self.show(fr, txt(ROMAN[side], 'playi', 66, GOLD), x, 338, t, 0.2 + 0.18 * k, 0.6)
            e = self._emb(side, 300)
            self.show(fr, e, x, 545, t, 0.12 + 0.18 * k, 0.7, 'zoom', s0=1.1)
            self.show(fr, txt(self.tm(side).up, 'play', 70, INK, 0.02, max_w=470), x, 752, t, b0 + 0.06 * k, 0.5, 'rise')
        self.show(fr, txt('против', 'corm', 58, DIM, wght=600), W / 2, 540, t, 0.45, 0.6)
        self.show(fr, hline(620), W / 2, 822, t, b0 + 0.2, 0.5, 'wipe')
        self.show(fr, txt(self.when, 'tenor', 48, INK, 0.08, max_w=940), W / 2, 880, t, b0 + 0.3, 0.5, 'rise')
        if self.line:
            pw, gap, ph = 296, 36, 258
            for k, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), self.line)):
                pl = _spr(('odd', lab, v), lambda lab=lab, v=v: self._odd(lab, v, pw, ph))
                x = W / 2 + (k - 1) * (pw + gap)
                self.show(fr, pl, x, 1108, t, b0 + u * (1 + 0.5 * k), 0.4, 'rise', rise=34)
            self.show(fr, txt('основное время', 'corm', 50, GOLD, wght=600), W / 2, 1296, t, b0 + 2.5 * u, 0.5, 'rise')
        fl = []
        sw = C.seg(t, b0, b0 + 1.3)
        if 0 < sw < 1:
            fl.append((-250 + (W + 500) * C.in_out(sw), 545, 1.1 * math.sin(math.pi * sw)))
        fl.append((540, 545, 0.18 + sum(0.3 * (1 - C.seg(t, self.b(n), self.b(n) + 0.45)) ** 2
                                        for n in range(-19, -15) if t >= self.b(n))))
        return fr, fl

    def _odd(self, lab, v, pw, ph):
        pl = frame_plate(pw, ph, 165).copy()
        C.put(pl, C.text(lab, 'tenor', 46, GOLD, track=0.12), pw / 2, 66)
        C.put(pl, C.text(C.fmt_k(v), 'play', 118, INK, max_w=pw - 40), pw / 2, 166)
        return pl

    def _game_block(self, g):
        """Строка титров одной игры: «11.10 · В ГОСТЯХ» / «МОНРЕАЛЬ  0:1 Б» / «поражение по буллитам»."""
        def mk():
            col = res_col(g['res'])
            top = ' · '.join(x for x in (g['date'], {True: 'ДОМА', False: 'В ГОСТЯХ'}.get(g['home'], '')) if x)
            a = C.text(top, 'tenor', 34, GOLD, track=0.14)
            sc = C.text(g['score'], 'play', 72, col)
            nt = C.text(g['note'], 'tenor', 34, col, track=0.05) if g['note'] else None
            room = 960 - sc.width - (nt.width + 10 if nt else 0) - 44
            op = C.text(g['opp'].upper(), 'play', 66, INK, max_w=room)
            oc = C.text(outcome(g), 'corm', 46, col, 700)
            lw = op.width + 44 + sc.width + (nt.width + 10 if nt else 0)
            hh = 170
            im = Image.new('RGBA', (980, hh), (0, 0, 0, 0))
            C.put(im, a, 490, 18)
            x0 = 490 - lw / 2
            yb = 76
            C.put(im, op, x0, yb - op.height / 2, anchor='tl')
            C.put(im, sc, x0 + op.width + 44, yb - sc.height / 2, anchor='tl')
            if nt:
                C.put(im, nt, x0 + op.width + 44 + sc.width + 10, yb - sc.height / 2 - 2, anchor='tl')
            C.put(im, oc, 490, 136)
            return C.with_shadow(im, 8, 0.65, 3)
        return _spr(('game', self.key, tuple(sorted(g.items()))), mk)

    def _season(self, s):
        """Строка сезона: три колонки «число / подпись» с тонкими разделителями."""
        def mk():
            items = []
            if s['points'] is not None:
                lab = plural(s['points'], 'ОЧКО', 'ОЧКА', 'ОЧКОВ')
                if s['gp'] is not None:
                    lab += ' · %d %s' % (s['gp'], plural(s['gp'], 'МАТЧ', 'МАТЧА', 'МАТЧЕЙ'))
                items.append(('%d' % s['points'], lab, INK))
            if s['place'] is not None:
                items.append(('%d' % s['place'], ('МЕСТО ' + (s['place_scope'] or '').upper()).strip(), INK))
            if s['gd'] is not None:
                items.append((F.gd_txt(s['gd']), 'РАЗНИЦА ШАЙБ', WINC if s['gd'] > 0 else LOSSC if s['gd'] < 0 else INK))
            if not items:
                return None
            n = len(items)
            cw = 980 // n
            im = Image.new('RGBA', (980, 196), (0, 0, 0, 0))
            for k, (v, lab, col) in enumerate(items):
                cx = cw * k + cw / 2
                C.put(im, C.text(v, 'play', 112, col), cx, 70)
                C.put(im, C.text(lab, 'tenor', 30, GOLD, track=0.08, max_w=cw - 26), cx, 166)
                if k:
                    C.put(im, Image.new('RGBA', (2, 150), GOLD + (110,)), cw * k, 98)
            return C.with_shadow(im, 8, 0.65, 3)
        return _spr(('season', self.key, tuple(sorted((k, v) for k, v in s.items() if k != 'games'))), mk)

    def _team(self, t, side):
        u = self.u
        T = self.T1 if side == 'h' else self.T2
        tm, s = self.tm(side), self.s[side]
        z = 1.0 + 0.055 * C.seg(t, T, T + self.team * u)
        arr = np.array(C.zoom(self._bg(side), z, W / 2, 640))
        m = C.in_out(C.seg(t, T + 2 * u, T + 2 * u + 0.55))         # титр-«герой» → титры
        hero = self._emb(side, 560)
        small = self._emb(side, 186)
        sc = C.lerp(1.0, small.width / hero.width, m)
        ey = C.lerp(625, 352, m)
        ap = C.out_cubic(C.seg(t, T, T + 0.7))
        beat = sum(0.22 * (1 - C.seg(t, T + n * u, T + n * u + 0.45)) ** 2 for n in range(0, self.team) if t >= T + n * u)
        rays(arr, W / 2, ey, C.lerp(1250, 560, m), t * 0.014 + (0.5 if side == 'a' else 0), (0.85 - 0.4 * m + beat) * ap,
             self.light[side], seed=5 if side == 'h' else 8)
        fr = Image.fromarray(arr).convert('RGBA')
        # эмблема
        if m <= 0:
            self.show(fr, hero, W / 2, ey, t, T, 0.75, 'zoom', s0=1.14)
        elif m < 1:
            C.put(fr, C.scale(hero, sc), W / 2, ey)
        else:
            C.put(fr, small, W / 2, ey)
        # номер части, имя, роль
        C.put(fr, txt(ROMAN[side], 'playi', 76, GOLD), W / 2, 300, (1 - m) * C.out_cubic(C.seg(t, T + 0.1, T + 0.6)))
        big = txt(tm.up, 'play', 142, INK, 0.03, max_w=960)
        fin = txt(tm.up, 'play', 92, INK, 0.03, max_w=900)
        ny = C.lerp(1000, 508, m)
        if m <= 0:
            self.show(fr, big, W / 2, ny, t, T + 0.18, 0.6, 'rise', rise=40)
        elif m < 1:
            C.put(fr, C.scale(big, C.lerp(1.0, fin.width / big.width, m)), W / 2, ny)
        else:
            C.put(fr, fin, W / 2, ny)
        role = 'в роли хозяев' if side == 'h' else 'в роли гостей'
        self.show(fr, txt(role, 'corm', 60, GOLD, wght=600), W / 2, 1110, t, T + 0.4, 0.5, 'rise', a=1 - m)
        if m > 0:
            C.put(fr, txt(role + ' · ' + F.lg_ru(self.league), 'corm', 46, GOLD, wght=600), W / 2, 574, C.seg(m, 0.5, 1))
        stk = streak_txt(self.rec[side].get('streak'))
        if stk:
            self.show(fr, txt(stk, 'tenor', 36, INK, 0.12), W / 2, 1186, t, T + 0.6, 0.5, 'rise', a=1 - m)
        g = s['games']
        n = len(g)
        for k, x in enumerate(g):                                     # медальоны В/П в титре-«герое»
            md = _spr(('med', x['res']), lambda r=x['res']: self._medal(r))
            cx = W / 2 + (k - (n - 1) / 2) * 132
            self.show(fr, md, cx, 1290, t, T + u * (1 + 0.25 * k), 0.35, 'zoom', a=1 - m, s0=1.3)
        # титры: 3 игры по строке на полдоли
        for k, x in enumerate(g):
            self.show(fr, self._game_block(x), W / 2, 718 + k * 178, t, T + (2.5 + 0.5 * k) * u, 0.45, 'rise', rise=30)
        ss = self._season(s)
        if ss is not None:
            self.show(fr, hline(900), W / 2, 1222, t, T + 3.9 * u, 0.5, 'wipe')
            self.show(fr, ss, W / 2, 1338, t, T + 4 * u, 0.45, 'rise', rise=30)
        fl = []
        sw = C.seg(t, T, T + 1.1)
        if 0 < sw < 1:
            d = 1 if side == 'h' else -1
            fl.append((W / 2 + d * (-W * 0.75 + W * 1.5 * C.in_out(sw)), ey, 1.25 * math.sin(math.pi * sw)))
        fl.append((W / 2, ey, (0.25 + beat * 1.4) * ap * (1 - 0.35 * m)))
        return fr, fl

    def _medal(self, r):
        d = 104
        im = Image.new('RGBA', (d * 3, d * 3), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        col = res_col(r)
        dr.ellipse((3, 3, d * 3 - 4, d * 3 - 4), fill=(6, 14, 18, 190), outline=col + (255,), width=9)
        dr.ellipse((27, 27, d * 3 - 28, d * 3 - 28), outline=col + (110,), width=3)
        im = im.resize((d, d), Image.LANCZOS)
        C.put(im, C.text(r or '?', 'play', 56, col), d / 2, d / 2 + 1)
        return im

    def _build(self, t):
        u, TB, D = self.u, self.TB, self.drop
        cuts = [0, 0.5, 1.0, 1.25, 1.5, 1.75]
        ph = (t - TB) / u
        k = max(i for i, c in enumerate(cuts) if ph >= c)
        side = 'h' if k % 2 == 0 else 'a'
        c0 = TB + cuts[k] * u
        c1 = TB + (cuts[k + 1] * u if k + 1 < len(cuts) else self.build * u)
        q = C.seg(t, c0, c1)
        if t >= D - 0.09:                                            # чернота перед ударом
            return Image.new('RGBA', (W, H), (0, 0, 0, 255)), []
        z = 1.04 + 0.1 * q + 0.03 * k
        arr = np.array(C.zoom(self._bg(side), z, W / 2, 800))
        rays(arr, W / 2, 790, 1400, t * 0.05 + k * 0.17, 1.0 + 0.3 * (1 - q), self.light[side], seed=5 if side == 'h' else 8)
        fr = Image.fromarray(arr).convert('RGBA')
        C.put(fr, txt(ROMAN[side], 'playi', 76, GOLD), W / 2, 300)
        C.put(fr, C.scale(self._emb(side, 640), 1.0 + 0.07 * q), W / 2, 790)
        C.put(fr, txt(self.tm(side).up, 'play', 142, INK, 0.03, max_w=960), W / 2, 1230)
        d = 1 if k % 2 == 0 else -1
        return fr, [(W / 2 + d * (-260 + 520 * q), 790, 1.0 + 0.4 * (1 - q))]

    def _pick_els(self, fr, t, t0, y_off=0):
        """Афиша: прогноз как название фильма, кэф — как строка премьеры."""
        D = t0
        w1, _, w2 = self.pick1.partition(' ')
        if w2:
            self.show(fr, txt(w1, 'tenor', 64, GOLD, 0.34), W / 2, 852 + y_off, t, D, 0.35, 'zoom', s0=1.18)
            self.show(fr, txt(w2, 'play', 150, INK, 0.02, max_w=960), W / 2, 968 + y_off, t, D, 0.4, 'zoom', s0=1.16)
        else:
            self.show(fr, txt(self.pick1, 'play', 150, INK, 0.02, max_w=960), W / 2, 930 + y_off, t, D, 0.4, 'zoom', s0=1.16)
        if self.pick2:
            p2 = txt(self.pick2, 'tenor', 44, INK, 0.2, max_w=760)
            self.show(fr, p2, W / 2, 1078 + y_off, t, D + 0.06, 0.4, 'rise')
            for sgn in (-1, 1):
                self.show(fr, hline(90, GOLD, 230), W / 2 + sgn * (p2.width / 2 + 40), 1078 + y_off, t, D + 0.06, 0.4, 'wipe')
        if self.coef:
            cb = _spr(('coefblk', self.coef), self._coef_block)
            self.show(fr, cb, W / 2, 1222 + y_off, t, D + 0.1, 0.4, 'zoom', s0=1.12)

    def _coef_block(self):
        lab = C.text('КЭФ', 'tenor', 54, GOLD, track=0.2)
        val = C.text(C.fmt_k(self.coef), 'play', 150, GOLD2)
        w = lab.width + 40 + val.width
        im = Image.new('RGBA', (760, 200), (0, 0, 0, 0))
        C.put(im, hline(700, GOLD, 200), 380, 10)
        C.put(im, hline(700, GOLD, 200), 380, 190)
        x0 = 380 - w / 2
        C.put(im, lab, x0, 100 + val.height / 2 - lab.height - 14, anchor='tl')
        C.put(im, val, x0 + lab.width + 40, 100 - val.height / 2, anchor='tl')
        return C.with_shadow(im, 10, 0.6, 4)

    def _pick(self, t):
        u, D = self.u, self.drop
        side = self.side
        z = 1.0 + 0.05 * C.seg(t, D, self.TC)
        arr = np.array(C.zoom(self._bg('pick'), z, W / 2, 600))
        beat = sum(0.3 * (1 - C.seg(t, self.b(n), self.b(n) + 0.45)) ** 2 for n in range(1, self.hold) if t >= self.b(n))
        burst = 1.2 * (1 - C.out_cubic(C.seg(t, D, D + 0.8)))
        rays(arr, W / 2, 565, 1350, t * 0.016, 0.8 + beat + burst, self.light[side], seed=5 if side == 'h' else 8)
        fr = Image.fromarray(arr).convert('RGBA')
        C.put(fr, txt(self.tag, 'tenor', 34, GOLD, 0.32), W / 2, Y_TAG)
        e = self._emb(side, 450)
        s = 1 + 0.2 * (1 - C.out_expo(C.seg(t, D, D + 0.55))) + 0.6 * beat / 0.3 * 0.025
        C.put(fr, C.scale(e, s), W / 2, 565)
        self._pick_els(fr, t, D)
        self.show(fr, txt(self.when, 'tenor', 38, DIM, 0.08, max_w=900), W / 2, 1360, t, D + 0.2, 0.4, 'rise')
        sw = C.seg(t, D, D + 0.9)
        fl = [(W / 2, 565, 0.35 + beat * 1.5 + 1.6 * (1 - C.out_cubic(sw)))]
        return fr, fl

    def _end(self, t):
        TC = self.TC
        side = self.side
        arr = np.array(C.zoom(self._bg('end'), 1.0 + 0.03 * C.seg(t, TC, self.dur), W / 2, 600))
        rays(arr, W / 2, 470, 760, t * 0.016, 0.55, self.light[side], seed=5 if side == 'h' else 8)
        fr = Image.fromarray(arr).convert('RGBA')
        self.show(fr, self._emb(side, 300), W / 2, 470, t, TC, 0.5, 'zoom', s0=1.1)
        self.show(fr, txt(self.pick1, 'play', 88, INK, 0.02, max_w=960), W / 2, 728, t, TC + 0.08, 0.45, 'rise')
        if self.pick2:
            self.show(fr, txt(self.pick2, 'tenor', 42, GOLD, 0.2, max_w=900), W / 2, 812, t, TC + 0.14, 0.45, 'rise')
        if self.coef:
            self.show(fr, txt('КЭФ ' + C.fmt_k(self.coef), 'play', 104, GOLD2), W / 2, 922, t, TC + 0.2, 0.45, 'rise')
        self.show(fr, txt(self.when, 'tenor', 40, DIM, 0.08, max_w=900), W / 2, 1030, t, TC + 0.26, 0.45, 'rise')
        tg = _spr(('tg',), lambda: C.tg_plate(960, 180, font='mont'))
        self.show(fr, tg, W / 2, 1262, t, TC + self.u * 0.5, 0.45, 'rise', rise=40)
        return fr, [(W / 2, 470, 0.3)]

    # ── экспозиция ──
    def _dark(self, t):
        """Множитель яркости: проявление в начале, затемнения в чёрное на долях."""
        f = C.out_cubic(C.seg(t, 0, 0.4))
        for Tb in (self.T1, self.T2, self.TC):
            if Tb - 0.24 <= t < Tb:
                f *= 1 - C.in_out(C.seg(t, Tb - 0.24, Tb))
            elif Tb <= t < Tb + 0.22:
                f *= C.out_cubic(C.seg(t, Tb, Tb + 0.22))
        return f

    def _flash(self, t):
        u, TB, D = self.u, self.TB, self.drop
        k = 0.0
        if TB <= t < D:
            for c in (0, 0.5, 1.0, 1.25, 1.5, 1.75):
                tc = TB + c * u
                if tc <= t < tc + 0.1:
                    k = max(k, (0.55 if c == 0 else 0.35) * (1 - C.seg(t, tc, tc + 0.1)))
        if D <= t < D + 0.4:
            k = max(k, 0.95 * (1 - C.out_cubic(C.seg(t, D, D + 0.4))))
        return k

    def frame(self, t):
        fi = int(round(t * C.FPS))
        rng = np.random.default_rng(self.seed * 100003 + fi)
        sc = self._scene(t)
        if sc == 'intro':
            fr, fl = self._intro(t)
        elif sc in ('h', 'a'):
            fr, fl = self._team(t, sc)
        elif sc == 'build':
            fr, fl = self._build(t)
        elif sc == 'pick':
            fr, fl = self._pick(t)
        else:
            fr, fl = self._end(t)
        arr = np.array(fr.convert('RGB'))
        for cx, cy, k in fl:
            flare(arr, cx, cy, k)
        # проектор: мерцание, вспышки, затемнения
        f = self._dark(t) * (1 + 0.018 * math.sin(fi * 2.7) + 0.012 * float(rng.normal()))
        if abs(f - 1) > 0.004:
            arr = (arr.astype(np.float32) * max(0.0, f)).clip(0, 255).astype(np.uint8)
        fk = self._flash(t)
        if fk > 0.01:
            arr = (arr + (255 - arr.astype(np.float32)) * fk).astype(np.uint8)
        pic = arr[BAR_T:BAR_B]
        # пыль и царапины
        for _ in range(int(rng.integers(0, 4))):
            r = int(rng.integers(2, 6))
            x, y = int(rng.integers(20, W - 20)), int(rng.integers(20, BAR_B - BAR_T - 20))
            v = 230 if rng.random() < 0.4 else 12
            yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
            msk = (xx * xx + yy * yy * 1.6 <= r * r)
            reg = pic[y - r:y + r + 1, x - r:x + r + 1]
            reg[msk] = (reg[msk] * 0.4 + v * 0.6).astype(np.uint8)
        if rng.random() < 0.18:
            x = int(rng.integers(40, W - 40))
            pic[:, x] = (pic[:, x].astype(np.float32) * 0.75 + 200 * 0.25).astype(np.uint8)
        g = _grain_frames()[fi % 8]
        p16 = pic.astype(np.int16)
        p16 += g[..., None]
        np.clip(p16, 0, 255, out=p16)
        out = np.zeros((H, W, 3), np.uint8)
        out[BAR_T:BAR_B] = p16
        img = Image.fromarray(out).convert('RGBA')
        if t < self.TC:
            a = 1.0 - C.seg(t, self.TC - 0.2, self.TC)
            C.put(img, txt(C.HANDLE, 'tenor', 50, INK, 0.08), W / 2, Y_HANDLE, a)
        return img.convert('RGB')
