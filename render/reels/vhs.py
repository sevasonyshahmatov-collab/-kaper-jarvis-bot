# -*- coding: utf-8 -*-
"""«VHS» — прогноз как запись на старой кассете: видеомагнитофон, экранное меню и плёночный шум.

Картинка — тёплая «съёмка камкордером» в цветах клубов: мягкий фокус, растёкшийся цвет, засветка ламп арены,
полоса трекинга, шум головок у нижнего края, выпадения плёнки, лёгкое дрожание строк. Поверх — чёткое экранное
меню видеомагнитофона (крупный моноширинный «пиксельный» шрифт с чёрной окантовкой): режим ленты ▶ ВОСПР. /
▶▶ ВПЕРЁД / ◀◀ НАЗАД / ❚❚ ПАУЗА / ■ СТОП (значки нарисованы, не эмодзи), счётчик ленты, JARVIS | NHL и @jarvibet
у низа безопасной зоны (одинаково во всех сценах до плашки Telegram). Помехи — только на «плёнке» (фон и записанные
титры во время перемотки), меню и все цифры остаются чёткими.

Сцены (u — доля трека; все склейки и акценты — на долях от дропа):
  интро (до b(−2·team−rew))  — обе эмблемы и названия, «дата съёмки» = день и время матча МСК, линия П1 · Х · П2
                                крупными плашками меню;
  клуб ×2 (team долей)        — склейка «перемоткой вперёд» ровно на долю: титр, как в домашнем видео (эмблема, огромное
                                имя, форма тремя квадратами), через долю — «пауза записи» и сам сюжет: эмблема и имя
                                сверху, последние 3 игры строками меню (В/П, счёт, ОТ/Б, соперник, дата, дома/выезд) —
                                по строке на полдоли, затем очки, место и разница шайб (пустые поля не показываются);
  перемотка (rew долей)       — ◀◀ НАЗАД: кадры ролика мелькают в обратном порядке, трекинг всё хуже, в конце «снег»;
  ДРОП (hold долей)           — картинка резко чистая (▶ ВОСПР.): только выбранная команда — одна эмблема, прогноз
                                (form.split_pick) и кэф крупными титрами; через долю — стоп-кадр (❚❚ ПАУЗА), пульс на доли;
  финал (cta долей)           — стоп-кадр прогноза (❚❚ ПАУЗА) держится до конца ролика (владелец 14.10: без синего экрана);
                                плашка Telegram — в общем подвале core.footer до последнего кадра.
lag — на сколько долей настоящий удар трека позже точки дропа, которую передаёт сборка (downdown: точка 78,25 с,
удар баса — 78,74 с, ровно полдоли): видимый дроп self.drop = drop + lag·u, прогноз встаёт точно на удар.
Кадр — чистая функция t (случайность — от номера кадра), фоны и титры кешируются на уровне модуля.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels import fresh
from reels.core import W, H

P = 40                                   # запас фона на «ручную камеру»
BW, BH = W + 2 * P, H + 2 * P
OW = (246, 246, 238)                     # белый меню
OY = (255, 206, 64)                      # жёлтый «дата съёмки»
OC = (130, 226, 255)                     # голубой подписей
OG = (70, 222, 104)                      # В
OR = (255, 78, 66)                       # П
OK_ = (176, 176, 186)
PANEL = (6, 8, 24)
VCR_BLUE = (14, 30, 160)
X0, X1 = 60, 1020                        # поля контента
Y_OSD, Y_CNT, Y_HANDLE = 282, 344, 1438

_SPR, _BG, _STILL, _NZ, _REF = {}, {}, {}, [], {}


# ─────────────────────────────── меню видеомагнитофона ───────────────────────────────
def _ref_box(fs, wght):
    key = (fs, wght)
    if key not in _REF:
        f = C.font('mono', fs, wght)
        m = Image.new('L', (fs * 5, fs * 3), 0)
        d = ImageDraw.Draw(m)
        d.fontmode = '1'
        d.text((4, 4), 'ДЩ8', font=f, fill=255)
        bb = m.getbbox()
        _REF[key] = (bb[1] - 4, bb[3] - 4)
    return _REF[key]


def _edge(m, edge, col, k):
    """Маска (низкое разрешение) → RGBA с чёрной окантовкой и тенью, увеличение ×k без сглаживания."""
    m = m.crop((-2, -2, m.width + 3, m.height + 3))
    out = Image.new('RGBA', m.size, (0, 0, 0, 0))
    if edge:
        dil = m.filter(ImageFilter.MaxFilter(3))
        if edge > 1:
            sh = Image.new('L', m.size, 0)
            sh.paste(dil, (1, 1))
            out.paste(Image.new('RGBA', m.size, (0, 0, 0, 255)), (0, 0), sh.point(lambda v: v * 150 // 255))
        blk = Image.new('RGBA', m.size, (0, 0, 0, 255))
        out.paste(blk, (0, 0), dil.point(lambda v: v * 235 // 255))
    out.paste(Image.new('RGBA', m.size, tuple(col)[:3] + (255,)), (0, 0), m)
    return out.resize((out.width * k, out.height * k), Image.NEAREST)


def osd(s, size, col=OW, k=None, wght=800, max_w=None, edge=2):
    """Строка шрифтом экранного меню: моноширинный, без сглаживания, увеличен ×k (крупные «пиксели»).
    max_w — ужать кегль до ширины. Ширина знака — im.info['cw'], отступ первого знака — im.info['x0']."""
    k = k or (3 if size >= 64 else 2)
    key = ('osd', s, int(size), tuple(col), k, wght, max_w, edge)
    if key in _SPR:
        return _SPR[key]
    fs = max(7, int(round(size / k)))
    f = C.font('mono', fs, wght)
    while max_w and fs > 7 and (f.getlength(s) + 6) * k > max_w:
        fs -= 1
        f = C.font('mono', fs, wght)
    tw = int(math.ceil(f.getlength(s)))
    m = Image.new('L', (tw + 8, fs * 2 + 8), 0)
    d = ImageDraw.Draw(m)
    d.fontmode = '1'
    d.text((4, 4), s.replace('0', 'O'), font=f, fill=255)          # ноль с точкой в «пикселях» похож на 8
    top, bot = _ref_box(fs, wght)
    bb = m.getbbox() or (4, 4, 5, 5)
    x0 = 4
    m = m.crop((x0, min(4 + top, bb[1]), max(bb[2], x0 + 1), max(4 + bot, bb[3])))
    im = _edge(m, edge, col, k)
    im.info['cw'] = f.getlength('0') * k
    im.info['x0'] = 2 * k
    im.info['n'] = len(s)
    _SPR[key] = im
    return im


def symbol(kind, size, col=OW, k=3):
    """Значок режима ленты (рисуется, не шрифт): play, ff, rew, pause, stop."""
    key = ('sym', kind, size, col, k)
    if key in _SPR:
        return _SPR[key]
    n = max(7, int(round(size / k)))
    w = {'play': n * 0.8, 'ff': n * 1.45, 'rew': n * 1.45, 'pause': n * 0.85, 'stop': n * 0.85}[kind]
    m = Image.new('L', (int(math.ceil(w)) + 1, n), 0)
    d = ImageDraw.Draw(m)
    hh = (n - 1) / 2
    if kind == 'play':
        d.polygon([(0, 0), (0, n - 1), (n * 0.8 - 1, hh)], fill=255)
    elif kind in ('ff', 'rew'):
        tw = n * 0.72
        for x in (0, tw):
            pts = [(x, 0), (x, n - 1), (x + tw - 1, hh)]
            if kind == 'rew':
                pts = [(w - 1 - px, py) for px, py in pts]
            d.polygon(pts, fill=255)
    elif kind == 'pause':
        bw = max(2, int(n * 0.3))
        d.rectangle((0, 0, bw - 1, n - 1), fill=255)
        d.rectangle((int(w) - bw, 0, int(w) - 1, n - 1), fill=255)
    else:
        d.rectangle((0, 0, int(w) - 1, n - 1), fill=255)
    im = _edge(m, 2, col, k)
    _SPR[key] = im
    return im


def transport(mode, size=52):
    """«▶ ВОСПР.» и т. п. — значок + слово, одной картинкой."""
    key = ('tr', mode, size)
    if key in _SPR:
        return _SPR[key]
    word = {'play': 'ВОСПР.', 'ff': 'ВПЕРЁД', 'rew': 'НАЗАД', 'pause': 'ПАУЗА', 'stop': 'СТОП'}[mode]
    k = 3
    sym = symbol(mode, int(size * 0.74), OW, k)
    tx = osd(word, size, OW, k)
    im = Image.new('RGBA', (sym.width + tx.width + 6 * k, max(sym.height, tx.height)), (0, 0, 0, 0))
    im.alpha_composite(sym, (0, (im.height - sym.height) // 2))
    im.alpha_composite(tx, (sym.width + 4 * k, (im.height - tx.height) // 2))
    _SPR[key] = im
    return im


def panel(w, h, fill=PANEL, a=170, border=OW, ba=200, k=3):
    """Плашка меню: тёмная полупрозрачная, рамка в «пиксель», срезанные углы."""
    key = ('pan', int(w), int(h), fill, a, border, ba, k)
    if key in _SPR:
        return _SPR[key]
    lw, lh = int(w) // k, int(h) // k
    im = Image.new('RGBA', (lw, lh), tuple(fill) + (a,))
    d = ImageDraw.Draw(im)
    if border:
        d.rectangle((0, 0, lw - 1, lh - 1), outline=tuple(border) + (ba,), width=1)
    for x, y in ((0, 0), (lw - 1, 0), (0, lh - 1), (lw - 1, lh - 1)):
        im.putpixel((x, y), (0, 0, 0, 0))
    im = im.resize((lw * k, lh * k), Image.NEAREST)
    _SPR[key] = im
    return im


def chip(r, d=88, size=62):
    col = OG if r == 'В' else OR if r == 'П' else OK_
    key = ('chip', r, d, size)
    if key in _SPR:
        return _SPR[key]
    k = 2
    lw = d // k
    im = Image.new('RGBA', (lw, lw), tuple(col) + (255,))
    dr = ImageDraw.Draw(im)
    dr.rectangle((0, 0, lw - 1, lw - 1), outline=(0, 0, 0, 255), width=1)
    for x, y in ((0, 0), (lw - 1, 0), (0, lw - 1), (lw - 1, lw - 1)):
        im.putpixel((x, y), (0, 0, 0, 0))
    im = im.resize((lw * k, lw * k), Image.NEAREST)
    C.put(im, osd(r or '?', size, OW, 2), im.width / 2 + 1, im.height / 2)
    _SPR[key] = im
    return im


# ─────────────────────────────── «плёнка» ───────────────────────────────
def _hbox(a, r):
    """Горизонтальное среднее окна 2r+1 (по оси x), края — повтором."""
    if r < 1:
        return a
    pad = np.concatenate([np.repeat(a[:, :1], r + 1, 1), a, np.repeat(a[:, -1:], r, 1)], 1)
    cs = np.cumsum(pad, 1, dtype=np.float32)
    return (cs[:, 2 * r + 1:] - cs[:, :-2 * r - 1]) / (2 * r + 1)


def vhs_grade(img, warm=True):
    """Обработка «как с кассеты»: мягкая яркость с ореолом справа от контуров, растёкшийся и сдвинутый цвет,
    тёплый оттенок, приподнятые тени и мягкие света. img — RGB (PIL) → RGB."""
    a = np.asarray(img.convert('RGB'), np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    i = 0.596 * r - 0.274 * g - 0.322 * b
    q = 0.211 * r - 0.523 * g + 0.312 * b
    ys = _hbox(y, 1)
    ring = ys - _hbox(ys, 6)
    ys = ys + 0.55 * np.roll(ring, 3, 1)                  # ореол «подчёркивания контуров»
    i = np.roll(_hbox(i, 14), 8, 1) * 1.18                # цвет течёт вправо, чуть насыщеннее
    q = np.roll(_hbox(q, 14), 8, 1) * 1.18
    i = (i + np.roll(i, 1, 0) + np.roll(i, -1, 0)) / 3
    q = (q + np.roll(q, 1, 0) + np.roll(q, -1, 0)) / 3
    r = ys + 0.956 * i + 0.621 * q
    g = ys - 0.272 * i - 0.647 * q
    b = ys - 1.106 * i + 1.703 * q
    out = np.stack([r, g, b], -1)
    if warm:
        out = out * np.array([1.06, 1.0, 0.86], np.float32) + np.array([8, 4, 0], np.float32)
    out = 16 + np.clip(out, 0, 400) * (222 / 255)
    out = np.where(out > 200, 200 + (out - 200) * 0.55, out)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')


def _noise():
    """Шесть заготовок «снега»: полосчатый по горизонтали шум (int16, σ≈1·16)."""
    if not _NZ:
        rng = np.random.default_rng(5)
        for _ in range(6):
            a = rng.normal(0, 16, (H, W // 6 + 2)).astype(np.float32)
            a = np.repeat(a, 6, 1)[:, :W]
            a = 0.7 * a + rng.normal(0, 7, (H, W)).astype(np.float32)
            _NZ.append(a.astype(np.int16))
    return _NZ


def _shift_rows(arr, y0, y1, off):
    if off and y1 > y0:
        arr[y0:y1] = np.roll(arr[y0:y1], int(off), 1)


def tape_fx(arr, t, rng, trk=0.15, nz=8, head=True, edges=True):
    """Помехи плёнки на фоне (in place, uint8 H×W×3): дрожание строк, полоса трекинга, выпадения, шум головок,
    неровные чёрные края, «снег»."""
    # дрожание строк (тайм-база): полосы по 6 строк
    amp = 1.0 + 3.0 * trk
    offs = np.round(rng.normal(0, amp * 0.6, H // 6 + 1)).astype(int)
    for j in np.nonzero(offs)[0]:
        _shift_rows(arr, j * 6, min(H, j * 6 + 6), offs[j])
    # полоса трекинга: медленно ползёт вниз (при плохом трекинге — две и шире)
    nb = 1 if trk < 0.5 else 2
    for bi in range(nb):
        yc = ((t * 210 + bi * 900 + 400) % (H + 300)) - 150
        hb = int(60 + 200 * trk)
        y0, y1 = int(max(0, yc - hb / 2)), int(min(H, yc + hb / 2))
        if y1 - y0 > 4:
            for y in range(y0, y1, 3):
                prof = math.sin(math.pi * (y - yc + hb / 2) / hb)
                _shift_rows(arr, y, min(y1, y + 3), rng.normal(0, 6 + 70 * trk) * prof)
            nzb = rng.integers(0, 255, (y1 - y0, W // 8 + 1)).repeat(8, 1)[:, :W]
            m = (nzb > 255 - (25 + 120 * trk)).astype(np.uint8)
            seg_ = arr[y0:y1]
            seg_[m.astype(bool)] = np.uint8(min(255, 170 + int(80 * trk)))
    # выпадения: короткие белые чёрточки
    for _ in range(int(2 + 25 * trk + rng.integers(0, 3))):
        y = int(rng.integers(0, H - 2))
        x = int(rng.integers(-100, W))
        ln = int(rng.integers(20, 120 + int(400 * trk)))
        arr[y:y + int(rng.integers(1, 3)), max(0, x):max(0, min(W, x + ln))] = 235
    # шум головок у нижнего края (под интерфейсом площадки — для достоверности)
    if head:
        hh = 30
        for y in range(H - hh, H, 3):
            _shift_rows(arr, y, y + 3, 30 + rng.integers(0, 60))
        arr[H - hh:H] = (arr[H - hh:H] * 0.55 + rng.integers(0, 120, (hh, W, 1))).clip(0, 255).astype(np.uint8)
    # неровные чёрные края захвата
    if edges:
        for j in range(0, H, 24):
            arr[j:j + 24, :int(rng.integers(6, 16))] = 6
            arr[j:j + 24, W - int(rng.integers(3, 9)):] = 6
    # «снег»
    if nz > 0:
        n = _noise()[int(t * C.FPS) % 6]
        a16 = arr.astype(np.int16)
        a16 += ((n * int(nz)) >> 4)[..., None]
        np.clip(a16, 0, 255, out=a16)
        arr[:] = a16
    return arr


def glitch(arr, t, rng, k, roll=0, up=False, bars=2):
    """Сильный сбой всего кадра (перемотка, склейки): прокрутка по вертикали, разрывы строк, шумовые полосы,
    расслоение цвета. k — сила 0..1."""
    if k <= 0.01:
        return arr
    if roll:
        arr = np.roll(arr, int(roll), 0)
    for _ in range(int(4 + 26 * k)):
        y = int(rng.integers(0, H - 8))
        h = int(rng.integers(3, 8 + int(40 * k)))
        _shift_rows(arr, y, min(H, y + h), rng.normal(0, 90 * k))
    for j in range(bars):
        sp = -2300 if up else 2300
        yc = ((t * sp + j * H / bars + 137 * j) % (H + 240)) - 120
        hb = int(40 + 110 * k)
        y0, y1 = int(max(0, yc - hb / 2)), int(min(H, yc + hb / 2))
        if y1 - y0 > 2:
            nzb = rng.integers(0, 256, (y1 - y0, W // 4 + 1)).repeat(4, 1)[:, :W]
            reg = arr[y0:y1].astype(np.int16)
            reg = (reg * (1 - 0.75 * k) + nzb[..., None] * 0.75 * k).astype(np.uint8)
            arr[y0:y1] = reg
    s = int(round(14 * k))
    if s:
        arr[..., 0] = np.roll(arr[..., 0], s, 1)
        arr[..., 2] = np.roll(arr[..., 2], -s, 1)
    return arr


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def streak_txt(s):
    """«В2» → «2 ПОБЕДЫ ПОДРЯД»; серии короче двух и прочее — пусто."""
    s = str(s or '').strip().upper()
    if len(s) < 2 or not s[1:].isdigit():
        return ''
    n = int(s[1:])
    if n < 2:
        return ''
    if s[0] in ('В', 'W'):
        return '%d %s ПОДРЯД' % (n, plural(n, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'))
    if s[0] in ('П', 'L'):
        return '%d %s ПОДРЯД' % (n, plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ'))
    return ''


# ─────────────────────────────── ролик ───────────────────────────────
class Vhs(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 61, drop=16 * 60 / 61, line=None, team=6, rew=1,
                 hold=4, cta=2.5, lag=0.0, seed=19, **kw):
        super().__init__(u, drop + lag * u, seed)
        self.line = line
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef = league, when, coef
        self.tag = F.tag(league)
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
        self.rec = {'h': sh or {}, 'a': sa or {}}
        self.s = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.T1 = self.b(-(2 * team + rew))
        if self.T1 < 2.0:
            raise ValueError('мало времени до дропа для интро')
        self.T2 = self.b(-(team + rew))
        self.TR = self.b(-rew)
        self.TC = self.b(hold)
        self.dur = self.b(hold + cta)
        self.footer_plate_to_end = True             # своей плашки Telegram в финале нет — плашка подвала до конца
        self.cover_t = min(self.T1 - 0.6, 2.7)
        self.key = (home, away, league, when, pick, coef, tuple(line or ()), seed)
        self.col = {'h': fresh.club(self.h), 'a': fresh.club(self.a)}
        if sum((p - q) ** 2 for p, q in zip(self.col['h'], self.col['a'])) ** 0.5 < 90:
            alt = [c for c in (self.a.c0, self.a.c2, self.a.c1) if (max(c) - min(c)) > 50]
            if alt:
                self.col['a'] = tuple(alt[-1])
        self._els()

    # ── фоны («съёмка») ──
    def _lights(self, base, rnd, n=9, y1=430):
        for _ in range(n):
            r = int(rnd.uniform(26, 70))
            x, y = rnd.uniform(40, BW - 40), rnd.uniform(40, y1)
            base = C.add_light(base, C.radial(r * 4, r * 4, (255, 236, 200), int(rnd.uniform(150, 230)), 1.5), x, y, 1.0)
            if rnd.random() < 0.45:                                             # вертикальный «смаз» ПЗС-матрицы
                sm = Image.new('RGBA', (6, BH), (255, 240, 210, 0))
                al = np.zeros((BH, 6), np.uint8)
                al[:, 1:5] = 26
                sm.putalpha(Image.fromarray(al))
                base = C.add_light(base, sm, x, BH / 2, 1.0)
        return base

    def _team_base(self, side, rnd):
        c = self.col[side]
        tm = self.h if side == 'h' else self.a
        base = C.vgrad(BW, BH, [(0, C.mix(c, (0, 0, 0), 0.62)), (0.32, C.mix(c, (0, 0, 0), 0.35)),
                                (0.68, C.mix(c, (0, 0, 0), 0.6)), (1, C.mix(c, (0, 0, 0), 0.82))])
        big = tm.emb(1500).filter(ImageFilter.GaussianBlur(28))
        lay = Image.new('RGBA', (BW, BH), (0, 0, 0, 0))
        C.put(lay, C.fade(big, 0.30), BW * (0.72 if side == 'h' else 0.28), BH * 0.62)
        base = base.convert('RGBA')
        base.alpha_composite(lay)
        base = C.add_light(base.convert('RGB'), C.radial(1400, 1400, fresh.bright(c, 0.3), 120, 1.7), BW / 2, BH * 0.36, 1.0)
        base = self._lights(base, rnd)
        leak = C.radial(1500, 1500, (255, 150, 60), 70, 1.4)                    # тёплая засветка из угла
        base = C.add_light(base, leak, 0 if side == 'h' else BW, BH * 0.18, 1.0)
        ice = Image.new('RGBA', (BW, BH), (0, 0, 0, 0))                         # светлый «лёд» внизу
        ice.alpha_composite(C.lgrad(BW, 700, (200, 225, 255), (200, 225, 255), 90, 0, 48), (0, BH - 700))
        base = base.convert('RGBA')
        base.alpha_composite(ice)
        return base.convert('RGB')

    def _bg(self, state):
        key = (self.key, state)
        if key in _BG:
            return _BG[key]
        rnd = np.random.default_rng(self.seed * 7919 + sum(ord(c) * (i + 1) for i, c in enumerate(state)))
        if state == 'blue':
            img = C.vgrad(BW, BH, [(0, (22, 40, 176)), (0.5, VCR_BLUE), (1, (10, 22, 128))])
            arr = np.asarray(img).copy()
            _BG[key] = (img, arr)
            return _BG[key]
        if state == 'intro':
            hb, ab = self._team_base('h', rnd), self._team_base('a', rnd)
            m = C.lgrad(BW, BH, (0, 0, 0), (0, 0, 0), 12, 0, 255).getchannel('A')
            m = m.point(lambda v: int(C.clamp((v - 100) * 255 / 56, 0, 255)))
            base = Image.composite(ab, hb, m).convert('RGBA')
            for side, x in (('h', 270), ('a', 810)):
                tm = self.h if side == 'h' else self.a
                C.put(base, C.with_shadow(tm.emb(330), 22, 0.55, 14), x + P, 560 + P)
        else:
            side = self.side if state == 'pick' else state[0]
            tm = self.h if side == 'h' else self.a
            base = self._team_base(side, rnd).convert('RGBA')
            if state == 'pick':
                base = C.add_light(base.convert('RGB'), C.radial(1100, 1100, (255, 255, 255), 60, 1.6), W / 2 + P, 600 + P).convert('RGBA')
                C.put(base, C.with_shadow(tm.emb(520), 26, 0.6, 16), W / 2 + P, 610 + P)
            elif state.endswith('title'):
                C.put(base, C.with_shadow(tm.emb(560), 26, 0.6, 16), W / 2 + P, 650 + P)
            else:
                C.put(base, C.with_shadow(tm.emb(270), 18, 0.55, 10), (200 if side == 'h' else 880) + P, 498 + P)
        img = vhs_grade(base.convert('RGB'))
        img = C.vignette(img, 0.42)
        arr = np.asarray(img).copy()
        _BG[key] = (img, arr)
        return _BG[key]

    # ── титры и элементы ──
    def _row(self, g, opp_x):
        w, h = X1 - X0, 116
        r = panel(w, h, a=165, border=OW, ba=60, k=2).copy()
        C.put(r, chip(g['res'], 88, 62), 16 + 44, h / 2)
        sc = osd(g['score'], 76, OW, 2)
        C.put(r, sc, 128, h / 2 - sc.height / 2, anchor='tl')
        if g['note']:
            nt = osd(g['note'], 42, OY, 2)
            C.put(r, nt, 128 + sc.width + 4, h / 2 + sc.height / 2 - nt.height - 2, anchor='tl')
        rt = []
        if g['date']:
            rt.append(osd(g['date'], 36, OW, 2))
        if g['home'] is not None:
            rt.append(osd('ДОМА' if g['home'] else 'ВЫЕЗД', 30, OC, 2))
        rw = max([x.width for x in rt] + [0])
        if len(rt) == 2:
            C.put(r, rt[0], w - 20 - rt[0].width, 36 - rt[0].height / 2 + 2, anchor='tl')
            C.put(r, rt[1], w - 20 - rt[1].width, 80 - rt[1].height / 2, anchor='tl')
        elif rt:
            C.put(r, rt[0], w - 20 - rt[0].width, h / 2 - rt[0].height / 2, anchor='tl')
        op = osd(g['opp'].upper(), 52, OW, 2, max_w=w - opp_x - rw - 44)
        C.put(r, op, opp_x, h / 2 - op.height / 2, anchor='tl')
        return r

    def _stats(self, s):
        items = []
        if s['points'] is not None:
            sub = ('ЗА %d %s' % (s['gp'], plural(s['gp'], 'МАТЧ', 'МАТЧА', 'МАТЧЕЙ'))) if s['gp'] is not None else ''
            items.append(('%d' % s['points'], 'ОЧКИ', sub, OW))
        if s['place'] is not None:
            items.append(('%d' % s['place'], 'МЕСТО', (s['place_scope'] or '').upper(), OW))
        if s['gd'] is not None:
            v = F.gd_txt(s['gd'])
            items.append((v, 'ШАЙБЫ ±', 'РАЗНИЦА', OG if s['gd'] > 0 else OR if s['gd'] < 0 else OW))
        if not items:
            return []
        n = len(items)
        gap = 24
        bw = int((X1 - X0 - gap * (n - 1)) / n) // 3 * 3
        out = []
        for k, (v, lab, sub, col) in enumerate(items):
            bx = panel(bw, 234, a=175, border=OW, ba=150, k=3).copy()
            C.put(bx, osd(lab, 38, OY, 2, max_w=bw - 30), bw / 2, 40)
            C.put(bx, osd(v, 124, col, 3, max_w=bw - 30), bw / 2, 124)
            if sub:
                C.put(bx, osd(sub, 30, OW, 2, max_w=bw - 24), bw / 2, 200)
            x = X0 + k * (bw + gap) + bw / 2 + ((X1 - X0) - (n * bw + (n - 1) * gap)) / 2
            out.append((bx, x))
        return out

    def _els(self):
        """Элементы сцен: dict(im, x, y, t0, d, kind, anchor, t1). Время — абсолютное."""
        u = self.u
        E = {}
        # интро
        el = []
        for side, x in (('h', 270), ('a', 810)):
            tm = self.h if side == 'h' else self.a
            el.append(dict(im=osd(tm.up, 66, OW, 3, max_w=480), x=x, y=788, t0=0.12 + 0.12 * (side == 'a'), d=0.28, kind='type'))
        el.append(dict(im=osd(self.when.upper(), 62, OY, 3, max_w=X1 - X0), x=W / 2, y=902, t0=0.42, d=0.4, kind='type'))
        if self.line:
            el.append(dict(im=osd('ОСНОВНОЕ ВРЕМЯ', 38, OC, 2), x=W / 2, y=1010, t0=0.7, d=0.25, kind='type'))
            gap = 30
            bw = (X1 - X0 - 2 * gap) // 3 // 3 * 3
            for k, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), self.line)):
                bx = panel(bw, 252, a=180, border=OW, ba=210, k=3).copy()
                C.put(bx, osd(lab, 50, OY, 2), bw / 2, 52)
                C.put(bx, osd(C.fmt_k(v), 112, OW, 3, max_w=bw - 24), bw / 2, 160)
                x = X0 + k * (bw + gap) + bw / 2 + ((X1 - X0) - (3 * bw + 2 * gap)) / 2
                el.append(dict(im=bx, x=x, y=1186, t0=0.82 + 0.14 * k, d=0.12, kind='pop'))
        E['intro'] = el
        # клубы
        for side, T in (('h', self.T1), ('a', self.T2)):
            tm = self.h if side == 'h' else self.a
            s = self.s[side]
            role = 'ХОЗЯЕВА' if side == 'h' else 'ГОСТИ'
            stk = streak_txt(self.rec[side].get('streak'))
            # титр
            el = [dict(im=osd(tm.up, 150, OW, 3, max_w=X1 - X0 + 20), x=W / 2, y=1068, t0=T + 0.04, d=0.3, kind='type', t1=T + u),
                  dict(im=osd(role + ' · ' + F.lg_ru(self.league), 48, OY, 2), x=W / 2, y=1172, t0=T + 0.22, d=0.25, kind='type',
                       t1=T + u)]
            g = s['games']
            if g:
                n = len(g)
                cw, gp = 104, 26
                for k, x in enumerate(g):
                    cx = W / 2 - (n * cw + (n - 1) * gp) / 2 + cw / 2 + k * (cw + gp)
                    el.append(dict(im=chip(x['res'], cw, 72), x=cx, y=1300, t0=T + 0.4 + 0.1 * k, d=0.06, kind='pop', t1=T + u))
            E[side + '_title'] = el
            # сюжет
            el = []
            tm_t = T + u
            name = osd(tm.up, 100, OW, 3, max_w=640)
            sub = osd(role + (' · ' + stk if stk else ''), 40, OY, 2, max_w=640)
            if side == 'h':
                el.append(dict(im=name, x=372, y=462, t0=tm_t, d=0.2, kind='type', anchor='l'))
                el.append(dict(im=sub, x=372, y=556, t0=tm_t + 0.1, d=0.25, kind='type', anchor='l'))
            else:
                el.append(dict(im=name, x=708, y=462, t0=tm_t, d=0.2, kind='type', anchor='r'))
                el.append(dict(im=sub, x=708, y=556, t0=tm_t + 0.1, d=0.25, kind='type', anchor='r'))
            sw = max([osd(x['score'], 76, OW, 2).width + (osd(x['note'], 42, OY, 2).width + 4 if x['note'] else 0) for x in g] + [0])
            opp_x = 128 + sw + 26
            for k, x in enumerate(g):
                el.append(dict(im=self._row(x, opp_x), x=W / 2, y=736 + k * 128, t0=T + (1.5 + 0.5 * k) * u, d=0.16, kind='wipe'))
            for k, (bx, x) in enumerate(self._stats(s)):
                el.append(dict(im=bx, x=x, y=1206, t0=T + 3 * u + 0.08 * k, d=0.12, kind='pop'))
            E[side + '_main'] = el
        # прогноз
        D = self.drop
        el = []
        p1 = osd(self.pick1, 112, OW, 3, max_w=X1 - X0 + 20)
        if p1.height < 90 and ' ' in self.pick1:                               # не влезло крупно — в две строки
            a_, b_ = self.pick1.split(' ', 1)
            el.append(dict(im=osd(a_, 104, OW, 3, max_w=X1 - X0), x=W / 2, y=920, t0=D, d=0.16, kind='slam'))
            el.append(dict(im=osd(b_, 104, OW, 3, max_w=X1 - X0), x=W / 2, y=1020, t0=D, d=0.16, kind='slam'))
            y2 = 1110
        else:
            el.append(dict(im=p1, x=W / 2, y=950, t0=D, d=0.16, kind='slam'))
            y2 = 1046
        if self.pick2:
            el.append(dict(im=osd(self.pick2, 56, OY, 2, max_w=X1 - X0), x=W / 2, y=y2, t0=D + 0.08, d=0.3, kind='type'))
        if self.coef:
            lab, val = osd('КЭФ', 64, OY, 3), osd(C.fmt_k(self.coef), 150, OW, 3)
            cw = (lab.width + val.width + 120) // 3 * 3
            cp = panel(cw, 204, a=185, border=OW, ba=220, k=3).copy()
            C.put(cp, lab, 42 + lab.width / 2, 102)
            C.put(cp, val, cw - 42 - val.width / 2, 104)
            el.append(dict(im=cp, x=W / 2, y=1238 + (y2 - 1046), t0=D + 0.1, d=0.12, kind='pop'))
        E['pick'] = el
        # финал
        TC = self.TC
        el = [dict(im=self.fav.emb(360), x=W / 2, y=590, t0=TC + 0.04, d=0.1, kind='pop'),
              dict(im=osd(self.pick1, 86, OW, 3, max_w=X1 - X0), x=W / 2, y=850, t0=TC + 0.08, d=0.28, kind='type')]
        if self.pick2:
            el.append(dict(im=osd(self.pick2, 46, OY, 2, max_w=X1 - X0), x=W / 2, y=934, t0=TC + 0.16, d=0.28, kind='type'))
        if self.coef:
            el.append(dict(im=osd('КЭФ ' + C.fmt_k(self.coef), 92, OW, 3), x=W / 2, y=1060, t0=TC + 0.24, d=0.24, kind='type'))
        el.append(dict(im=C.tg_plate(960, 180, font='mont'), x=W / 2, y=1330, t0=TC + 0.2, d=0.4, kind='wipe'))
        E['end'] = el
        for v in E.values():
            for e in v:
                e.setdefault('anchor', 'c')
                e.setdefault('t1', 1e9)
        self.E = E

    def _draw(self, fr, e, t, a=1.0):
        if t < e['t0'] or t >= e['t1']:
            return
        im, kind = e['im'], e['kind']
        q = C.seg(t, e['t0'], e['t0'] + e['d'])
        fw, fh = im.width, im.height
        x = e['x'] - (fw / 2 if e['anchor'] == 'c' else fw if e['anchor'] == 'r' else 0)
        y = e['y'] - fh / 2
        cur = None
        if q < 1:
            if kind == 'type' and 'cw' in im.info:
                n = im.info['n']
                vis = int(math.ceil(n * q))
                ww = int(min(fw, im.info['x0'] + vis * im.info['cw'] + 2))
                if vis < n:
                    k = 3 if fh > 60 else 2
                    cur = (x + ww, y + k, max(6, int(im.info['cw'] * 0.8)), fh - 2 * k)
                im = im.crop((0, 0, max(1, ww), fh))
            elif kind == 'wipe':
                im = im.crop((0, 0, max(1, int(fw * C.out_cubic(q))), fh))
            elif kind == 'pop':
                ph = t - e['t0']
                if 0.034 < ph < 0.067:                                           # мигнуло при появлении
                    return
                x += (1 - q) * 18
            elif kind == 'slam':
                s = 1 + 0.32 * (1 - C.out_cubic(q))
                im = C.scale(im, s)
                x, y = e['x'] - im.width / 2, e['y'] - im.height / 2
        C.put(fr, im, x, y, a, anchor='tl')
        if cur:
            C.put(fr, Image.new('RGBA', (cur[2], cur[3]), OW + (230,)), cur[0], cur[1], a, anchor='tl')

    # ── время сцен ──
    def _state(self, t):
        u = self.u
        if t < self.T1:
            return 'intro', 'intro'
        if t < self.T2:
            return ('h_title' if t < self.T1 + u else 'h_main'), 'h'
        if t < self.TR:
            return ('a_title' if t < self.T2 + u else 'a_main'), 'a'
        if t < self.drop:
            return 'rew', 'rew'
        if t < self.TC:
            return 'pick', 'pick'
        return 'pick', 'pick'                       # владелец 14.10: без синего экрана — стоп-кадр прогноза до конца

    def _mode(self, t):
        u, D = self.u, self.drop
        for T in (self.T1, self.T2):
            if T - 0.36 <= t < T + 0.04:
                return 'ff'
        if self.TR <= t < D:
            return 'rew'
        if t >= D + u:
            return 'pause'
        return 'play'

    def _counter(self, t):
        """Счётчик ленты: на перемотке вперёд бежит, назад — откручивается, на паузе и стопе стоит."""
        u, D = self.u, self.drop
        te = min(t, D + u)                                       # с паузы лента стоит
        v = 22 * 60 + 47 + te
        for T in (self.T1, self.T2):
            v += 95 * C.seg(t, T - 0.36, T + 0.04)
        v -= 410 * C.in_out(C.seg(t, self.TR, D))
        v = int(max(0, v))
        return '%d:%02d:%02d' % (v // 3600, v // 60 % 60, v % 60)

    def _glitch_k(self, t):
        u = self.u
        k = 0.0
        if t < 0.32:
            k = max(k, 0.75 * (1 - C.seg(t, 0, 0.32)))
        for T in (self.T1, self.T2):
            if T - 0.36 <= t < T:
                k = max(k, 0.25 + 0.75 * C.in_cubic(C.seg(t, T - 0.36, T)))
            if T <= t < T + 0.2:
                k = max(k, 0.85 * (1 - C.out_cubic(C.seg(t, T, T + 0.2))))
            if T + u <= t < T + u + 0.16:
                k = max(k, 0.6 * (1 - C.seg(t, T + u, T + u + 0.16)))
        return k

    def _trk(self, t):
        """Сила помех трекинга: фон слегка «живой», к концу второй команды хуже, на дропе — чисто."""
        u, D = self.u, self.drop
        if t >= D:
            return 0.0 if t < D + u else 0.1
        return 0.14 + 0.3 * C.seg(t, D - 3 * u, self.TR)

    # ── кадр ──
    def _bg_arr(self, state, t, z=1.0, freeze=None, dy_extra=0):
        img, arr = self._bg(state)
        tt = t if freeze is None else freeze
        sp = 0.0
        for T in (self.T1, self.T2):                                    # перемотка вперёд — камера «спешит»
            sp += 7 * max(0.0, min(t, T + 0.04) - (T - 0.36)) if t >= T - 0.36 else 0
        tt += sp
        dx = 11 * math.sin(tt * 0.71 + 0.4) + 5 * math.sin(tt * 1.93 + 1.1)
        dy = 8 * math.sin(tt * 0.53 + 2.0) + 4 * math.sin(tt * 1.37) + dy_extra
        if z > 1.002:
            cw, ch = W / z, H / z
            x0, y0 = P + dx + (W - cw) / 2, P + dy + (H - ch) / 2
            return np.asarray(img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))).copy()
        x0, y0 = int(round(P + dx)), int(round(P + dy))
        x0, y0 = min(max(0, x0), 2 * P), min(max(0, y0), 2 * P)
        return arr[y0:y0 + H, x0:x0 + W].copy()

    def _still(self, state):
        """Кадр сцены целиком (фон + все титры) без помех — для перемотки назад."""
        key = (self.key, state)
        if key not in _STILL:
            arr = self._bg(state)[1][P:P + H, P:P + W].copy()
            fr = Image.fromarray(arr).convert('RGBA')
            for e in self.E.get(state, []):
                self._draw(fr, dict(e, t1=1e9), 1e8)
            _STILL[key] = np.asarray(fr.convert('RGB')).copy()
        return _STILL[key]

    def frame(self, t):
        u, D = self.u, self.drop
        fi = int(round(t * C.FPS))
        rng = np.random.default_rng(self.seed * 100003 + fi)
        state, sc = self._state(t)
        if sc == 'rew':
            # перемотка назад: кадры ролика в обратном порядке, прокрутка вверх, снег в конце
            p = C.seg(t, self.TR, D)
            seq = ['a_main', 'a_title', 'h_main', 'h_title', 'intro']
            snow_t = 0.13
            if t >= D - snow_t:
                n = rng.integers(0, 256, (H // 2, W // 4), dtype=np.uint8).repeat(2, 0).repeat(4, 1)
                arr = np.stack([n, n, np.minimum(255, n.astype(np.int16) + 30).astype(np.uint8)], -1)
            else:
                k = min(len(seq) - 1, int(C.seg(t, self.TR, D - snow_t) * len(seq)))
                arr = self._still(seq[k]).copy()
                arr = glitch(arr, t, rng, 0.55 + 0.4 * p, roll=-int((t - self.TR) * 2600) % H, up=True, bars=3)
                arr = tape_fx(arr, t, rng, trk=0.6 + 0.4 * p, nz=40 + 50 * p)
                g = arr.mean(2, keepdims=True)
                arr = (arr * (1 - 0.5 * p) + g * 0.5 * p).astype(np.uint8)
            fr = Image.fromarray(arr).convert('RGBA')
        else:
            z, freeze, dy_extra = 1.0, None, 0
            if sc == 'pick':
                z = 1 + 0.085 * (1 - C.out_cubic(C.seg(t, D, D + 0.45)))
                for n in range(1, 5):
                    tb = self.b(n)
                    if t >= tb:
                        z += 0.014 * (1 - C.seg(t, tb, tb + 0.3)) ** 2
                if t >= D + u:
                    freeze = D + u
                    dy_extra = int(rng.integers(-2, 3))
            elif sc == 'end':
                freeze = 0.0
            arr = self._bg_arr(state, t, z, freeze, dy_extra)
            if sc == 'end':
                arr = arr.astype(np.int16)
                arr += ((_noise()[fi % 6] * 3) >> 4)[..., None]
                arr = arr.clip(0, 255).astype(np.uint8)
            else:
                trk = self._trk(t)
                tape_fx(arr, t, rng, trk=trk, nz=6 + 10 * trk, edges=True)
                if sc == 'pick' and t >= D + u:                              # стоп-кадр: полоса паузы внизу
                    y0 = 1590 + int(rng.integers(-3, 4))
                    nzb = rng.integers(0, 256, (46, W // 6 + 1)).repeat(6, 1)[:, :W]
                    arr[y0:y0 + 46] = (arr[y0:y0 + 46] * 0.35 + nzb[..., None] * 0.65).astype(np.uint8)
                if sc == 'pick' and t < D + 0.1:                             # чистая вспышка на дропе
                    f = 1 - C.seg(t, D, D + 0.1)
                    arr = np.minimum(255, arr.astype(np.int16) + int(110 * f)).astype(np.uint8)
            fr = Image.fromarray(arr).convert('RGBA')
            key = state if sc != 'end' else 'end'
            if sc in ('h', 'a'):
                for e in self.E[sc + '_title'] + self.E[sc + '_main']:
                    self._draw(fr, e, t)
            else:
                for e in self.E.get(key, []):
                    self._draw(fr, e, t)
            k = self._glitch_k(t)
            if k > 0.01:
                arr = np.asarray(fr.convert('RGB')).copy()
                roll = int(rng.normal(0, 140 * k)) if k > 0.3 else 0
                arr = glitch(arr, t, rng, k, roll=roll, bars=2 if k > 0.3 else 1)
                if t >= self.TC - 0.12 and t < self.TC:
                    n = rng.integers(0, 256, (H // 2, W // 4), dtype=np.uint8).repeat(2, 0).repeat(4, 1)
                    arr = (arr * (1 - k * 0.8) + n[..., None] * k * 0.8).astype(np.uint8)
                fr = Image.fromarray(arr).convert('RGBA')
        self._osd(fr, t)
        return fr.convert('RGB')

    def _osd(self, fr, t):
        """Меню видеомагнитофона — всегда чёткое, поверх любых помех."""
        mode = self._mode(t)
        blink = mode in ('rew', 'ff') and (t * 4) % 1 > 0.62
        if not blink:
            C.put(fr, transport(mode, 54), X0, Y_OSD - transport(mode, 54).height / 2, anchor='tl')
        cnt = osd(self._counter(t), 42, OW, 2)
        C.put(fr, cnt, X0, Y_CNT - cnt.height / 2, anchor='tl')
        tg = osd(self.tag, 40, OW, 2)
        C.put(fr, tg, X1 - tg.width, Y_OSD - tg.height / 2, anchor='tl')
        C.put(fr, osd(C.HANDLE, 48, OW, 2), W / 2, Y_HANDLE, float(C.HANDLE_BOTTOM))
