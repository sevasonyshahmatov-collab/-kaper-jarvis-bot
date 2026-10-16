"""Послематчевый баннер одного матча — анимированные шаблоны (16.10.2026, просьба владельца: «как прошёл наш прогноз»
в семье анимированных предматчевых баннеров). Рядом со статичным «Вердиктом» (ice_more2, style 'verdict' / 'final' —
его вывод не меняется); флаги, «парящие» эмблемы, холст, светодиоды и кодирование — из versus_anim и prematch_styles.
Три шаблона нарочно разные — своя композиция, палитра и движение:

    versus_final  «Versus-итог»       — пара к предматчевому Versus: флаг победителя в полном цвете, флаг проигравшего
                                        бледный, ниже и колышется спокойнее; крупный счёт; резиновый штамп
                                        «ЗАШЛО» / «МИНУС» / «ВОЗВРАТ» лежит с первого кадра, раз за цикл
                                        приподнимается и «бьёт» (вспышка, лёгкая встряска кадра, блик по чернилам)
    tablo_final   «Табло-финал»       — светодиодное табло арены, без флагов: «ФИНАЛ», счёт, таблица периодов
                                        (1 · 2 · 3 · ОТ · Б · ИТОГ), эмблемы на экранах, у победителя мигает
                                        голевая лампа; ниже — табличка прогноза с нарисованной ✓ / ✗ и вердиктом
    stamp_pick    «Штамп на прогнозе» — печатный лист на светлой бумаге: печатные флаги клубов колышутся, итоговый
                                        счёт, прогноз и кэф крупно, поперёк — диагональный штамп «ЗАШЛО ✓» / «МИНУС ✗»
                                        с неровными чернилами; по сырым чернилам пробегает блик

    import postmatch_styles as pm
    pm.render('Адмирал', 'Спартак', 1, 5, 'out/pm.mp4', league='KHL', date='четверг, 16 октября',
              pick='победа Спартака в основное время', kef=1.95, hit=True, periods=[(0, 1), (1, 0), (0, 4)],
              style='versus_final', plates_dir='out/anim/plates', first=True)
→ MP4 H.264 1080×1350 (4:5), 30 fps, 4 с, бесшовный цикл, ≤ target_mb (Telegram показывает как GIF-анимацию);
  first — .jpg первого кадра (True — рядом с mp4); sheet=True — контактный лист 6 кадров (_frames.jpg).
mark: '' — основное время, 'ОТ' — овертайм, 'Б' — буллиты. hit: True — зашло, False — минус, None — возврат.
periods: [(х, г), …] — 1-й, 2-й, 3-й период, дальше ОТ и Б (или с подписью: ('ОТ', 1, 0)); None — без таблицы.
Флаги «Versus-итога» — плашки versus_anim со своей геометрией 4:5 (рисуются один раз на клуб в plates_dir: у победителя
обычная волна, у проигравшего — спокойная). Запуск из папки render.
"""
import contextlib
import math
import os
import time as _clock
from collections import namedtuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import brand_kit
import poster
import prematch_styles as ps
import versus
import versus_anim as va
from prematch_styles import F, OSW, MAN, ALU, UNB, WHITE, _t, _fit, _wrap_fit, _spaced, _shadow_text, _n

W, H = 1080, 1350
SIZE = (W, H)
SS = ps.SS
F32 = np.float32
FPS, SECONDS = 30, 4
GRAIN = va.GRAIN

STYLES = ['versus_final', 'tablo_final', 'stamp_pick', 'verdict_anim', 'verdict_rings']
NAMES = {'versus_final': 'Versus-итог', 'tablo_final': 'Табло-финал', 'stamp_pick': 'Штамп на прогнозе',
         'verdict_anim': 'Вердикт (анимация)', 'verdict_rings': 'Вердикт (кольца)'}

HIT, MISS, VOID = (47, 191, 95), (228, 58, 62), (150, 152, 160)             # зашло / минус / возврат
INK_HIT, INK_MISS, INK_VOID = (22, 140, 66), (200, 32, 40), (112, 116, 124)  # те же — чернилами по бумаге
LED_RED = (255, 66, 56)


# ───────────────────────────── данные ─────────────────────────────
Result = namedtuple('Result', 'm sh sa mark win periods hit word col ink')


def _verdict(hit):
    if hit is None:
        return 'ВОЗВРАТ', VOID, INK_VOID
    return ('ЗАШЛО', HIT, INK_HIT) if hit else ('МИНУС', MISS, INK_MISS)


def _periods(periods, mark):
    """→ [(подпись, х, г), …]: 1, 2, 3, дальше ОТ и Б. При mark='Б' и четырёх периодах ненулевой 4-й — это буллиты."""
    out = []
    for k, p in enumerate(periods or ()):
        if len(p) == 3:
            lab, a, b = p
        else:
            a, b = p
            lab = ('1', '2', '3', 'ОТ', 'Б')[k] if k < 5 else str(k + 1)
            if k == 3 and mark == 'Б' and len(periods) == 4 and (a or b):
                lab = 'Б'
        out.append((str(lab), int(a), int(b)))
    return out


def _result(home, away, sh, sa, mark, league, date, pick, kef, hit, periods):
    m = ps._match(home, away, league, date, '', None, pick, kef)
    win = 'home' if sh > sa else 'away' if sa > sh else None
    word, col, ink = _verdict(hit)
    return Result(m, int(sh), int(sa), (mark or '').strip(), win, _periods(periods, mark), hit, word, col, ink)


def _mark_text(mark):
    return {'ОТ': 'ОВЕРТАЙМ', 'Б': 'БУЛЛИТЫ'}.get(mark, mark)


# ───────────────────────────── сцена 4:5 ─────────────────────────────
class Scene(ps.Scene):
    """prematch_styles.Scene в кадре 1080×1350; post(img, i, tau) → img — правка всего кадра (встряска)."""

    def __init__(self, grain=GRAIN):
        self.cv = va._Canvas(grain, size=SIZE)
        self.items, self.closers, self.post = [], [], None

    def layer(self, img):
        self.static(*ps._arr(img, SIZE))

    def frame(self, i, tau):
        img = np.zeros((H, W, 3), F32)
        for it in self.items:
            if it[0] == 's':
                img *= 1 - it[2][..., None]
                img += it[1]
            else:
                it[1](img, i, tau)
        if self.post:
            img = self.post(img, i, tau)
        return np.clip(img, 0, 255).astype(np.uint8)


def _layer():
    return ps._layer(SIZE)


def _arr(img):
    return ps._arr(img, SIZE)


def _grid():
    return ps._grid(W, H)


def _ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def _sym(d, cx, cy, r, hit, fill, w):
    """✓ (hit), ✗ (False) или черта (None) линиями со скруглёнными концами; координаты — px кадра (слой 3×)."""
    s = SS
    x, y, r, w = cx * s, cy * s, r * s, max(1, int(w * s))
    if hit is None:
        strokes = [[(x - r * .8, y), (x + r * .8, y)]]
    elif hit:
        strokes = [[(x - r, y + r * 0.02), (x - r * 0.32, y + r * 0.68), (x + r, y - r * 0.72)]]
    else:
        strokes = [[(x - r * .72, y - r * .72), (x + r * .72, y + r * .72)], [(x - r * .72, y + r * .72), (x + r * .72, y - r * .72)]]
    for pts in strokes:
        d.line(pts, fill=fill, width=w, joint='curve')
        for px, py in pts:
            d.ellipse((px - w / 2, py - w / 2, px + w / 2, py + w / 2), fill=fill)
    return strokes


def _pass(tau, xx, yy, box, ang, width, k, t0, t1):
    """prematch_styles._sweep, но полоса проходит box (x0, y0, x1, y1) целиком: вне [t0, t1] она за его краем
    (у _sweep начало и конец — по оси, наклонённой на ang, а не по x)."""
    x0, y0, x1, y1 = box
    tn = math.tan(math.radians(ang))
    cu = (x0 + x1) / 2 + (y0 + y1) / 2 * tn
    half = (x1 - x0) / 2 + (y1 - y0) / 2 * abs(tn) + 3.6 * width
    return ps._sweep(tau, xx, yy, cu - half, cu + half, ang=ang, width=width, k=k, t0=t0, t1=t1)


# ───────────────────────────── штамп ─────────────────────────────
def _noise(rng, w, h, cell):
    n = rng.random((h // cell + 3, w // cell + 3))
    im = Image.fromarray((n * 255).astype(np.uint8), 'L').resize((w + 3 * cell, h + 3 * cell), Image.BICUBIC)
    return np.asarray(im, F32)[cell:cell + h, cell:cell + w] / 255


def _stamp_master(word, hit, ink, w, h, seed=7, backing=None, sym=True):
    """Резиновый штамп w×h (px кадра) → (RGB, альфа) в SS×: двойная рамка, слово и знак ✓/✗; чернила неровные —
    рваный край, поры, пятна плотности, одна сторона прижата слабее. backing — (цвет, непрозрачность) подложки
    внутри рамки (на флагах — чтобы читалось на любом цвете клуба)."""
    s = SS
    W3, H3 = int(w * s), int(h * s)
    m = Image.new('L', (W3, H3), 0)
    d = ImageDraw.Draw(m)
    o, bw = 5, 11
    d.rounded_rectangle((o * s, o * s, W3 - o * s, H3 - o * s), radius=24 * s, outline=255, width=bw * s)
    i = o + bw + 9
    d.rounded_rectangle((i * s, i * s, W3 - i * s, H3 - i * s), radius=12 * s, outline=255, width=3 * s)
    inner = h - 2 * i
    show = sym and hit is not None
    size = inner * 0.86
    while True:
        f = F(OSW, size, 700)
        l, t, r, b = f.getbbox(word)
        tw, th = (r - l) / s, (b - t) / s
        symw = th * 0.95 if show else 0
        gap = th * 0.30 if show else 0
        if tw + gap + symw <= w - 2 * i - 44 and th <= inner * 0.66:
            break
        size -= 2
    x = (w - (tw + gap + symw)) / 2
    d.text(((x * s - l), (h / 2 * s - (t + b) / 2)), word, font=f, fill=255)
    if show:
        _sym(d, x + tw + gap + symw / 2, h / 2, symw / 2 * 0.92, hit, 255, th * 0.17)
    a = np.asarray(m, F32) / 255
    rng = np.random.default_rng(seed)
    fine, mid, big = _noise(rng, W3, H3, 2 * s), _noise(rng, W3, H3, 7 * s), _noise(rng, W3, H3, 46 * s)
    soft = ps._blur_arr(a, 1.3 * s)
    rough = np.clip((soft - 0.5) * 3.2 + 0.5 + (mid - 0.5) * 1.0 + (fine - 0.5) * 0.55, 0, 1)
    pores = np.clip((fine - 0.78) * 6, 0, 1) * 0.75 + np.clip((mid - 0.86) * 8, 0, 1) * 0.5
    xs = np.linspace(0, 1, W3, dtype=F32)[None, :]
    dens = (0.80 + 0.22 * big) * (0.88 + 0.12 * xs)
    alpha = np.clip(rough * (1 - np.clip(pores, 0, 1)) * dens, 0, 1)
    rgb = np.empty((H3, W3, 3), F32)
    rgb[:] = ink
    if backing is not None:
        bc, bk = backing
        bm = Image.new('L', (W3, H3), 0)
        ImageDraw.Draw(bm).rounded_rectangle(((o + 4) * s, (o + 4) * s, W3 - (o + 4) * s, H3 - (o + 4) * s),
                                             radius=22 * s, fill=255)
        ba = np.asarray(bm, F32) / 255 * bk * (0.92 + 0.08 * big)
        out_a = alpha + ba * (1 - alpha)
        rgb = (rgb * alpha[..., None] + np.array(bc, F32) * (ba * (1 - alpha))[..., None]) / \
            np.maximum(out_a, 1e-4)[..., None]
        return rgb, out_a, alpha
    return rgb, alpha, alpha


class Stamp:
    """Штамп (или любой спрайт), повёрнутый на angle (°, + — против часовой) вокруг (cx, cy).
    pose(tau) → (масштаб, подъём 0..1) или (масштаб, подъём, dx, dy, доворот °) — для «парящей» эмблемы.
    Покой рисуется один раз; движение — только в кадрах, где поза не нулевая. sheen(tau, xx, yy) → добавка света
    по чернилам. shadow — (dx, dy, размытие, сила); тень цвета shadow_rgb отстаёт от сдвига спрайта (lag)."""

    def __init__(self, master, cx, cy, angle, pose=None, shadow=(5, 12, 9, 0.55), sheen=None, shadow_rgb=(0, 0, 0),
                 lag=0.6):
        rgb, a, ink = master
        prem = rgb * a[..., None]
        self.ch = [Image.fromarray(np.clip(c, 0, 255).astype(np.uint8), 'L') for c in
                   (prem[..., 0], prem[..., 1], prem[..., 2], a * 255, ink * 255)]
        self.ms = np.array((a.shape[1], a.shape[0]), F32)
        self.T = int(math.ceil(math.hypot(*(self.ms / SS)) * 1.12)) + 16
        self.c = np.array((cx, cy), F32)
        self.ox, self.oy = int(round(cx - self.T / 2)), int(round(cy - self.T / 2))
        self.angle, self.pose, self.shadow, self.sheen = angle, pose or (lambda tau: (1.0, 0.0)), shadow, sheen
        self.shadow_rgb, self.lag = np.array(shadow_rgb, F32), lag
        self.cache = {}
        T = self.T
        # видимая часть тайла (штамп у края кадра): кадр[fy, fx] ↔ тайл[ty, tx]
        X0, Y0 = max(0, self.ox), max(0, self.oy)
        X1, Y1 = min(W, self.ox + T), min(H, self.oy + T)
        self.fy, self.fx = slice(Y0, Y1), slice(X0, X1)
        self.ty, self.tx = slice(Y0 - self.oy, Y1 - self.oy), slice(X0 - self.ox, X1 - self.ox)
        self.xx, self.yy = np.meshgrid(np.arange(X0, X1, dtype=F32), np.arange(Y0, Y1, dtype=F32))

    def tile(self, scale, dx=0.0, dy=0.0, dang=0.0):
        key = round(scale, 4) if not (dx or dy or dang) else None
        if key in self.cache:
            return self.cache[key]
        T = self.T
        ct = SS * (self.c + (dx, dy) - (self.ox, self.oy))
        cm = self.ms / 2
        th = math.radians(self.angle + dang)
        cs, sn = math.cos(th) / scale, math.sin(th) / scale
        a, b, dd, e = cs, -sn, sn, cs
        coef = (a, b, cm[0] - a * ct[0] - b * ct[1], dd, e, cm[1] - dd * ct[0] - e * ct[1])
        ch = [np.asarray(c.transform((T * SS, T * SS), Image.AFFINE, coef, resample=Image.BICUBIC)
                         .resize((T, T), Image.BOX), F32) for c in self.ch]
        out = (np.dstack(ch[:3]), ch[3] / 255, ch[4] / 255)
        if key is not None and (key == 1.0 or len(self.cache) < 2):
            self.cache[key] = out
        return out

    def rest(self):
        """→ (премультиплицированный RGB, альфа, чернила) в покое — видимая часть (кадр[self.fy, self.fx])."""
        return tuple(x[self.ty, self.tx] for x in self.tile(1.0))

    def __call__(self, img, i, tau):
        pose = self.pose(tau)
        scale, lift = pose[:2]
        mx, my, dang = pose[2:] if len(pose) > 2 else (0.0, 0.0, 0.0)
        prem, a, ink = self.tile(scale, mx, my, dang)
        if self.shadow:
            dx, dy, blur, k = self.shadow
            sh = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur + 10 * lift))
            sh = np.asarray(sh, F32) / 255 * k * (1 - 0.35 * lift)
            ps._over(img, self.ox + int(round(dx + 8 * lift - self.lag * mx)),
                     self.oy + int(round(dy + 22 * lift - self.lag * my)), np.broadcast_to(self.shadow_rgb, sh.shape + (3,)), sh)
        reg = img[self.fy, self.fx]
        a, prem, ink = a[self.ty, self.tx], prem[self.ty, self.tx], ink[self.ty, self.tx]
        reg *= 1 - a[..., None]
        reg += prem
        if self.sheen:
            reg += self.sheen(tau, self.xx, self.yy) * ink[..., None]


# ═════════════════════════════ 1. VERSUS-ИТОГ ═════════════════════════════
VF_WIN = {'home': (36, 140, 556, 820), 'away': (524, 140, 1044, 820)}
VF_LOSE = {'home': (60, 202, 548, 856), 'away': (532, 202, 1020, 856)}
VF_EM = (330, 236)                                # эмблема победителя / проигравшего
VF_STAMP = (540, 742, 9.0, 560, 170)              # центр, угол, размер штампа
VF_HIT = 0.15                                     # момент удара штампа (доля цикла)


def vf_geometry(side, win):
    x0, y0, x1, y1 = (VF_WIN if win else VF_LOSE)[side]
    return va.side_geometry('pmw' if win else 'pml', side, SIZE, (x0, y0, x1, y1), VF_EM[0 if win else 1],
                            ((x0 + x1) / 2, y0 + (y1 - y0) * 0.42), fade='down')


@contextlib.contextmanager
def _calm(k=0.42):
    """Спокойная волна и парение (плашки проигравшего): амплитуды versus_anim меньше; версия плашки — своя."""
    saved = va.WAVES, va.BOB, va.DRIFT, va.ROT, va.BREATH, va.FOLD
    va.WAVES = tuple((amp * k,) + tuple(w) for amp, *w in saved[0])
    va.BOB, va.DRIFT, va.ROT, va.BREATH, va.FOLD = saved[1] * 0.4, saved[2] * 0.5, saved[3] * 0.4, saved[4] * 0.4, \
        saved[5] * 0.7
    try:
        yield
    finally:
        va.WAVES, va.BOB, va.DRIFT, va.ROT, va.BREATH, va.FOLD = saved


def _faded(rgb):
    g = rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114
    return (rgb * 0.2 + g[..., None] * 0.8) * 0.56 + np.array((7, 8, 10), F32)


class FxPlate(ps.Plate):
    """Плашка versus_anim с правкой цвета fx(rgb) (бледный проигравший)."""

    def __init__(self, scene, club, side, league, plates_dir, geom, fx=None):
        super().__init__(scene, club, side, league, plates_dir, geom)
        self.fx = fx

    def __call__(self, img, i, tau):
        if self.rd is None or i != self.next:
            self.close()
            self.rd = va._read_plate(self.path, self.meta)
            for _ in range(i):
                next(self.rd)
        fr = next(self.rd)
        self.next = i + 1
        x0, y0 = self.meta['origin']
        rgb = fr[..., :3].astype(F32)
        ps._over(img, x0, y0, self.fx(rgb) if self.fx else rgb, fr[..., 3].astype(F32) / 255)


def _vf_pose(tau):
    """Штамп лежит; раз за цикл: подъём → удар (VF_HIT) → отскок и покой. → (масштаб, подъём)."""
    t0, t1, t2, t3 = 0.04, VF_HIT - 0.03, VF_HIT, VF_HIT + 0.17
    if tau < t0 or tau >= t3:
        return 1.0, 0.0
    if tau < t1:
        u = _ease((tau - t0) / (t1 - t0))
        return 1 + 0.075 * u, u
    if tau < t2:
        u = ((tau - t1) / (t2 - t1)) ** 2
        return 1.075 - 0.105 * u, 1 - u
    u = (tau - t2) / (t3 - t2)
    return 1 - 0.03 * (1 - u) ** 2 * math.cos(3 * math.pi * u), 0.0


def _versus_final(r, plates_dir):
    m = r.m
    sc = Scene()
    acc = m.acc
    clubs = {'home': m.home, 'away': m.away}
    wc = clubs[r.win]['color'] if r.win else acc
    gx = 790 if r.win == 'away' else 290
    sc.static(ps._bg((20, 19, 23), [(gx, 470, 420, wc, 0.10), (540, 1150, 520, acc, 0.035)], vignette=0.34, w=W, h=H))
    # флаги: проигравший (спокойный, бледный) — снизу, победитель поверх
    order = [s for s in ('home', 'away') if s != r.win] + ([r.win] if r.win else [])
    for side in order:
        win = r.win is None or side == r.win
        if win:
            sc.dyn(FxPlate(sc, clubs[side], side, m.league, plates_dir, vf_geometry(side, True)))
        else:
            with _calm():
                sc.dyn(FxPlate(sc, clubs[side], side, m.league, plates_dir, vf_geometry(side, False), _faded))

    lay = _layer()
    d = ImageDraw.Draw(lay)
    _spaced(d, 540, 58, 'ИТОГ МАТЧА', F(OSW, 44, 700), WHITE, 5)
    sub = ' · '.join(x for x in (m.date.upper(), m.tag) if x)
    _t(d, 540, 106, sub, _fit(sub, 700, 19, MAN, 800), acc)
    # счёт: цифра победителя белая, проигравшего — серая; по бокам имена
    fs = F(UNB, 150, 700)
    dim = (112, 110, 120)
    ys = 962
    hc, ac = (WHITE if r.win != 'away' else dim), (WHITE if r.win != 'home' else dim)
    _shadow_text(lay, 486, ys, str(r.sh), fs, hc, anchor='rm', blur=14, off=(0, 6), alpha=200)
    _shadow_text(lay, 594, ys, str(r.sa), fs, ac, anchor='lm', blur=14, off=(0, 6), alpha=200)
    _t(d, 540, ys - 12, ':', F(UNB, 96, 500), dim)
    dw = max(fs.getlength(str(v)) for v in (r.sh, r.sa)) / SS
    zw = min(330, 486 - dw - 70)                    # место под имя сбоку от цифры
    for cl, side, cx in ((m.home, 'home', 40 + zw / 2), (m.away, 'away', W - 40 - zw / 2)):
        won = r.win is None or side == r.win
        nm = cl['ru'].upper()
        f = _fit(nm, zw, 50, OSW, 700)
        _t(d, cx, ys - 16, nm, f, WHITE if won else (150, 148, 156))
        city = (cl['sub'] or ('Москва' if 'Москва' in cl['ru'] else '')).upper()
        if city:
            _t(d, cx, ys + 30, city, _fit(city, zw, 16, MAN, 700), versus._mix(cl['color'], 0.45) if won else
               (110, 108, 116))
    if r.mark:
        fm = F(MAN, 17, 800)
        lab = _mark_text(r.mark)
        tw = fm.getlength(lab) / SS + 34
        d.rounded_rectangle(((540 - tw / 2) * SS, (ys + 74) * SS, (540 + tw / 2) * SS, (ys + 108) * SS),
                            radius=17 * SS, fill=acc)
        _t(d, 540, ys + 92, lab, fm, (24, 20, 14))
    # прогноз и кэф
    if m.pick:
        ps._pick_bar(lay, (56, 1104, 1024, 1180), m.pick, m.kef, acc, bg=(10, 10, 13, 200), size=34)
    if r.periods:
        line = 'ПО ПЕРИОДАМ:  ' + '  ·  '.join(('%d:%d' % (a, b)) if lab in '123' else '%s %d:%d' % (lab, a, b)
                                               for lab, a, b in r.periods)
        _t(d, 540, 1222, line, _fit(line, 900, 19, MAN, 700), (150, 148, 158))
    ps._brand(d, 540, 1298, acc, m.tag, 26)
    sc.layer(lay)

    # штамп поверх флагов
    cx, cy, ang, sw, sh_ = VF_STAMP
    master = _stamp_master(r.word, r.hit, versus._mix(r.col, 0.08), sw, sh_, seed=11, backing=((12, 13, 16), 0.80))

    def sheen(tau, xx, yy):
        return _pass(tau, xx, yy, (cx - sw / 2, cy - sh_ / 2 - 50, cx + sw / 2, cy + sh_ / 2 + 50), -30, 34, 0.42, 0.30, 0.62)
    stamp = Stamp(master, cx, cy, ang, pose=_vf_pose, shadow=(6, 14, 10, 0.6), sheen=sheen)
    # вспышка удара: ореол по контуру штампа цвета вердикта
    a0 = stamp.rest()[1]
    halo = ps._blur_arr(a0, 16) * 1.6 * (1 - 0.9 * a0)          # ореол — снаружи штампа, буквы не засвечивает
    hcol = np.array(versus._mix(r.col, 0.2), F32)

    def stamp_fx(img, i, tau):
        stamp(img, i, tau)
        e = (tau - VF_HIT) % 1.0
        if e < 0.16:
            k = (1 - e / 0.16) ** 2
            img[stamp.fy, stamp.fx] += (halo * k * 0.75)[..., None] * hcol
    sc.dyn(stamp_fx)

    def shake(img, i, tau):
        e = (tau - VF_HIT) % 1.0
        if e >= 0.09:
            return img
        amp = 4.0 * (1 - e / 0.09)
        dy = int(round(amp * math.cos(2 * math.pi * e / 0.03)))
        dx = int(round(amp * 0.5 * math.sin(2 * math.pi * e / 0.04)))
        return np.roll(img, (dy, dx), axis=(0, 1)) if (dx or dy) else img
    sc.post = shake
    return sc


# ═════════════════════════════ 2. ТАБЛО-ФИНАЛ ═════════════════════════════
TB_HOUSE = (36, 124, 1044, 1060)
TB_LED = (58, 146, 1022, 1038)
TB_SCR = [(84, 312, 364, 592), (716, 312, 996, 592)]
TB_LAMP_Y, TB_LAMP_R = 70, 40
TB_STRIP = (36, 1090, 1044, 1314)


def _led_wrap(text, rows, pitch, max_w, max_lines=2):
    words = text.split()
    for k in range(1, min(max_lines, len(words)) + 1):
        best = min(ps._splits(words, k), key=lambda ls: max(ps._bits(x, rows).shape[1] for x in ls))
        if max(ps._bits(x, rows).shape[1] for x in best) * pitch <= max_w:
            return best, pitch
    best = min(ps._splits(words, min(max_lines, len(words))), key=lambda ls: max(ps._bits(x, rows).shape[1] for x in ls))
    return best, min(pitch, max_w / max(ps._bits(x, rows).shape[1] for x in best))


def _led_parts(lay, parts, cx, cy, rows, pitch, max_w, gap=3):
    """Светодиодная строка из кусков [(текст, цвет), …] по центру (cx, cy). → [(x0, ширина)] кусков."""
    bits = [ps._bits(t, rows) for t, _ in parts]
    total = sum(b.shape[1] for b in bits) + gap * (len(bits) - 1)
    pitch = min(pitch, max_w / total)
    x = cx - total * pitch / 2
    out = []
    for b, (_, col) in zip(bits, parts):
        tile = ps._led(b, pitch, col, glow=0.6)
        mm = (tile.width / SS - b.shape[1] * pitch) / 2
        lay.alpha_composite(tile, (int(round((x - mm) * SS)), int(round((cy - (2 + rows / 2) * pitch - mm) * SS))))
        out.append((x, b.shape[1] * pitch))
        x += (b.shape[1] + gap) * pitch
    return out, pitch


def _lamp(on):
    """Голевая лампа (купол на подставке) → RGBA 1× в квадрате 2·(R + 30)."""
    R = TB_LAMP_R
    n = 2 * (R + 30)
    k = SS
    im = Image.new('RGBA', (n * k, n * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = n / 2
    # подставка
    d.rounded_rectangle(((c - R - 14) * k, (c + R * 0.30) * k, (c + R + 14) * k, (c + R * 0.30 + 18) * k), radius=5 * k,
                        fill=(52, 52, 60))
    d.rectangle(((c - R - 14) * k, (c + R * 0.30) * k, (c + R + 14) * k, (c + R * 0.30 + 3) * k), fill=(92, 92, 102))
    yy, xx = np.mgrid[0:n * k, 0:n * k].astype(F32) / k
    dx, dy = (xx - c) / R, (yy - c) / R
    rr = np.hypot(dx, dy)
    dome = np.clip((1 - rr) * R + 0.5, 0, 1) * np.clip((R * 0.30 - (yy - c)) + 0.5, 0, 1)
    if on:
        core = np.exp(-(dx ** 2 + (dy + 0.1) ** 2) / 0.22)[..., None]
        col = np.array((205, 22, 20), F32) * (1 - core) + np.array((255, 214, 170), F32) * core
    else:
        col = np.array((70, 12, 14), F32) * (1.15 - 0.4 * np.clip(rr, 0, 1))[..., None]
    spec = np.exp(-(((dx + 0.38) / 0.18) ** 2 + ((dy + 0.42) / 0.12) ** 2))[..., None] * (120 if on else 150)
    col = col + spec
    rgba = np.asarray(im, F32)
    a0 = rgba[..., 3:] / 255
    rgb = rgba[..., :3] * (1 - dome[..., None]) + np.clip(col, 0, 255) * dome[..., None]
    a = np.maximum(a0[..., 0], dome)
    out = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), 'RGBA')
    arr = np.asarray(out.resize((n, n), Image.LANCZOS), F32)
    return arr[..., :3], arr[..., 3] / 255


def _tablo_final(r, plates_dir):
    m = r.m
    sc = Scene()
    acc = m.acc
    clubs = (m.home, m.away)
    sc.static(ps._bg((9, 9, 12), [(540, 600, 640, (40, 44, 60), 0.30), (540, 1200, 500, acc, 0.05)], vignette=0.42,
                     w=W, h=H))
    HX0, HY0, HX1, HY1 = TB_HOUSE
    LX0, LY0, LX1, LY1 = TB_LED
    SX0, SY0, SX1, SY1 = TB_STRIP
    lay = _layer()
    d = ImageDraw.Draw(lay)
    for (x0, y0, x1, y1), rad in ((TB_HOUSE, 26), (TB_STRIP, 22)):
        sh = Image.new('L', lay.size, 0)
        ImageDraw.Draw(sh).rounded_rectangle(((x0 + 6) * SS, (y0 + 20) * SS, (x1 + 6) * SS, (y1 + 26) * SS),
                                             radius=rad * SS, fill=200)
        blk = Image.new('RGBA', lay.size, (0, 0, 0, 255))
        blk.putalpha(sh.filter(ImageFilter.GaussianBlur(28 * SS)))
        lay.alpha_composite(blk)
        d.rounded_rectangle((x0 * SS, y0 * SS, x1 * SS, y1 * SS), radius=rad * SS, fill=(34, 34, 40),
                            outline=(78, 78, 88), width=3 * SS)
        d.rounded_rectangle(((x0 + 8) * SS, (y0 + 8) * SS, (x1 - 8) * SS, (y1 - 8) * SS), radius=(rad - 6) * SS,
                            outline=(20, 20, 24), width=4 * SS)
        for bx, by in ((x0 + 18, y0 + 18), (x1 - 18, y0 + 18), (x0 + 18, y1 - 18), (x1 - 18, y1 - 18)):
            d.ellipse(((bx - 4) * SS, (by - 4) * SS, (bx + 4) * SS, (by + 4) * SS), fill=(70, 70, 78))
    d.rectangle((LX0 * SS, LY0 * SS, LX1 * SS, LY1 * SS), fill=(5, 5, 7))
    for x in range(LX0 + 120, LX1, 120):
        d.line((x * SS, LY0 * SS, x * SS, LY1 * SS), fill=(14, 14, 18), width=SS)
    for y in range(LY0 + 112, LY1, 112):
        d.line((LX0 * SS, y * SS, LX1 * SS, y * SS), fill=(14, 14, 18), width=SS)
    d.rectangle(((SX0 + 20) * SS, (SY0 + 20) * SS, (SX1 - 20) * SS, (SY1 - 20) * SS), fill=(5, 5, 7))
    # кронштейны ламп
    for (x0, _, x1, _) in TB_SCR:
        lx = (x0 + x1) / 2
        d.rectangle(((lx - 10) * SS, (TB_LAMP_Y + 30) * SS, (lx + 10) * SS, HY0 * SS), fill=(44, 44, 52))
    sc.layer(lay)

    # экраны с эмблемами
    lay = _layer()
    d = ImageDraw.Draw(lay)
    for (x0, y0, x1, y1), cl in zip(TB_SCR, clubs):
        d.rectangle(((x0 - 6) * SS, (y0 - 6) * SS, (x1 + 6) * SS, (y1 + 6) * SS), outline=cl['color'] + (150,),
                    width=2 * SS)
    sc.layer(lay)
    xx, yy = _grid()
    scr_bg, scr_a = np.zeros((H, W, 3), F32), np.zeros((H, W), F32)
    for (x0, y0, x1, y1), cl, side in zip(TB_SCR, clubs, ('home', 'away')):
        k = 1.0 if (r.win is None or r.win == side) else 0.45
        g = np.exp(-((xx - (x0 + x1) / 2) ** 2 + (yy - (y0 + y1) / 2) ** 2) / (2 * 150 ** 2))
        sel = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
        scr_bg[sel] = (np.array(cl['color'], F32) * (0.16 + 0.42 * g[..., None]) * k)[sel]
        scr_a[sel] = 1
    sc.static(scr_bg, scr_a)
    for (x0, y0, x1, y1), cl, ph in zip(TB_SCR, clubs, (0.0, 0.6 * np.pi)):
        sc.dyn(ps.FloatEmblem(sc, cl['ru'], (x0 + x1) / 2, (y0 + y1) / 2 + 2, 212, ph, 0.7))
    masks = [ps._led_mask(x1 - x0, y1 - y0, 4.0, 0.5) for x0, y0, x1, y1 in TB_SCR]
    loser = [r.win is not None and r.win != s for s in ('home', 'away')]

    def screens(img, i, tau):
        for (x0, y0, x1, y1), mk, lo in zip(TB_SCR, masks, loser):
            reg = img[y0:y1, x0:x1]
            if lo:                                         # экран проигравшего — приглушён и почти без цвета
                g = reg.mean(axis=2, keepdims=True)
                reg[:] = (reg * 0.35 + g * 0.65) * 0.62
            glow = np.dstack([ps._blur_arr(reg[..., c], 2.2) for c in range(3)])
            reg *= mk[..., None]
            reg += glow * 0.22
            yl = (np.arange(y1 - y0, dtype=F32) + 0.5) / (y1 - y0)
            band = np.exp(-((yl - ((2 * tau) % 1.0) * 1.4 + 0.2) / 0.05) ** 2) * 0.10
            reg *= (1 + band)[:, None, None]
    sc.dyn(screens)

    lay = _layer()
    d = ImageDraw.Draw(lay)
    _led_text = ps._led_text
    _led_text(lay, 'ФИНАЛ', 540, 202, 12, 4.8, LED_RED)
    sub = ' · '.join(x for x in (m.date.upper(), m.tag) if x)
    _led_text(lay, sub, 540, 262, 8, 2.9, (190, 190, 200), max_w=640)
    # счёт
    dim = (120, 120, 132)
    sc_parts = [(str(r.sh), acc if r.win != 'away' else dim), (':', dim), (str(r.sa), acc if r.win != 'home' else dim)]
    pos, pitch = _led_parts(lay, sc_parts, 540, 440, 18, 8.6, 320, gap=3)
    if r.mark:
        _led_text(lay, _mark_text(r.mark), 540, 560, 9, 3.2, acc)
    # имена под экранами
    for (x0, y0, x1, y1), cl, side in zip(TB_SCR, clubs, ('home', 'away')):
        won = r.win is None or r.win == side
        nm = cl['ru'].upper()
        if (x1 - x0 + 40) / ps._bits(nm, 11).shape[1] < 3.2:
            nm = cl['short'].upper()
        _led_text(lay, nm, (x0 + x1) / 2, 636, 11, 4.0, WHITE if won else (128, 128, 138), max_w=x1 - x0 + 40)
    # таблица периодов
    TY0, TY1 = 684, 1012
    d.rectangle((84 * SS, TY0 * SS, 996 * SS, TY1 * SS), fill=(9, 9, 12), outline=(46, 46, 54), width=2 * SS)
    cols = [lab for lab, _, _ in r.periods] + ['ИТОГ']
    CX0, CX1 = 410, 980
    cw = (CX1 - CX0) / len(cols)
    hy, ry = TY0 + 44, (TY0 + 150, TY0 + 260)
    d.line((100 * SS, (TY0 + 82) * SS, 980 * SS, (TY0 + 82) * SS), fill=(46, 46, 54), width=2 * SS)
    _led_text(lay, 'ПЕРИОДЫ', 110, hy, 9, 3.0, (170, 170, 180), anchor='l')
    for k, lab in enumerate(cols):
        x = CX0 + cw * (k + 0.5)
        _led_text(lay, lab, x, hy, 9, 3.0, acc if lab == 'ИТОГ' else (170, 170, 180), max_w=cw - 14)
        if k:
            d.line(((CX0 + cw * k) * SS, (TY0 + 14) * SS, (CX0 + cw * k) * SS, (TY1 - 14) * SS), fill=(26, 26, 32),
                   width=2 * SS)
    for row, (cl, side, y) in enumerate(zip(clubs, ('home', 'away'), ry)):
        won = r.win is None or r.win == side
        nm = cl['short'].upper()
        _led_text(lay, nm, 110, y, 12, 4.2, WHITE if won else (150, 150, 160), max_w=CX0 - 130, anchor='l')
        vals = [p[1 + row] for p in r.periods] + [r.sh if row == 0 else r.sa]
        for k, v in enumerate(vals):
            x = CX0 + cw * (k + 0.5)
            last = k == len(vals) - 1
            col = (acc if won else dim) if last else (WHITE if v else (96, 96, 106))
            _led_text(lay, str(v), x, y, 13 if not last else 15, 4.6, col, max_w=cw - 20)
    # марка между лампами
    ps._brand(d, 540, 84, acc, m.tag, 26)
    # табличка прогноза
    VX0 = 752
    d.line((VX0 * SS, (SY0 + 34) * SS, VX0 * SS, (SY1 - 34) * SS), fill=(40, 40, 48), width=2 * SS)
    ly = SY0 + 56
    if m.pick:
        lw, _ = _led_text(lay, 'ПРОГНОЗ', 84, ly, 9, 3.2, LED_RED, anchor='l')
        if m.kef is not None:
            kw, _ = _led_text(lay, 'КЭФ', 84 + lw + 40, ly, 9, 3.2, (170, 170, 180), anchor='l')
            _led_text(lay, _n(m.kef), 84 + lw + 40 + kw + 18, ly - 2, 11, 3.6, acc, anchor='l')
        lines, p = _led_wrap(m.pick.upper(), 10, 3.6, VX0 - 84 - 30, 2)
        y = ly + 62 if len(lines) > 1 else ly + 84
        for ln in lines:
            _led_text(lay, ln, 84, y, 10, p, WHITE, anchor='l')
            y += 54
    VC = ((VX0 + SX1 - 20) / 2, SY0 + 92)
    _led_text(lay, r.word, VC[0], SY1 - 58, 11, 3.8, r.col, max_w=SX1 - 20 - VX0 - 40)
    sc.layer(lay)

    # нарисованная ✓ / ✗: штрих со свечением, по нему раз за цикл бежит блик
    R = 46
    bx0, by0 = int(VC[0] - R - 40), int(VC[1] - R - 40)
    n = 2 * R + 80
    sl = _layer()
    strokes = _sym(ImageDraw.Draw(sl), VC[0], VC[1], R, r.hit, (255, 255, 255, 255), 13)
    _, sa_ = _arr(sl)
    sa_ = sa_[by0:by0 + n, bx0:bx0 + n]
    glow = ps._blur_arr(sa_, 10)
    col = np.array(r.col, F32)
    hot = np.array(versus._mix(r.col, 0.55), F32)
    # длина дуги вдоль штриха для каждой точки тайла
    yy_, xx_ = np.mgrid[0:n, 0:n].astype(F32)
    px, py = xx_ + bx0 + 0.5, yy_ + by0 + 0.5
    best, arc, s0 = np.full((n, n), 1e9, F32), np.zeros((n, n), F32), 0.0
    for pts in strokes:
        for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
            ax, ay, bx, by = ax / SS, ay / SS, bx / SS, by / SS
            L = math.hypot(bx - ax, by - ay)
            t = np.clip(((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / (L * L), 0, 1)
            dist = np.hypot(px - ax - t * (bx - ax), py - ay - t * (by - ay))
            sel = dist < best
            best[sel], arc[sel] = dist[sel], (s0 + t * L)[sel]
            s0 += L
    arc /= s0

    def check(img, i, tau):
        reg = img[by0:by0 + n, bx0:bx0 + n]
        k = 0.85 + 0.15 * math.cos(2 * math.pi * 2 * tau)
        reg += glow[..., None] * col * 0.9 * k
        p = (tau - 0.15) % 1.0 * 1.6 - 0.2                # блик бежит по штриху за ~0.6 цикла
        hl = np.exp(-((arc - p) / 0.08) ** 2) * sa_
        a = sa_[..., None]
        reg[:] = reg * (1 - a) + (col * a) + hot * (hl * 0.9)[..., None]
    sc.dyn(check)

    # голевая лампа победителя мигает (5 раз за цикл), у проигравшего — погашена
    lamps = {True: _lamp(True), False: _lamp(False)}
    ln = lamps[True][1].shape[0]
    halo = np.zeros((H, W), F32)
    lx = {}
    for (x0, _, x1, _), side in zip(TB_SCR, ('home', 'away')):
        lx[side] = int((x0 + x1) / 2)
    hx = lx.get(r.win, 540)
    xs, ys_ = _grid()
    halo = np.exp(-((xs - hx) ** 2 + (ys_ - TB_LAMP_Y) ** 2) / (2 * 120 ** 2)) * 0.9 + \
        np.exp(-((xs - hx) ** 2 + (ys_ - TB_LAMP_Y) ** 2) / (2 * 34 ** 2)) * 0.8
    HB = (0, 0, W, 420)
    halo_c = halo[HB[1]:HB[3], :, None] * np.array((255, 40, 30), F32)

    def lamp_fx(img, i, tau):
        v = (0.5 + 0.5 * math.cos(2 * math.pi * 5 * tau)) ** 1.6
        for side in ('home', 'away'):
            x0, y0 = lx[side] - ln // 2, TB_LAMP_Y - ln // 2
            if r.win == side or r.win is None:
                on_rgb, on_a = lamps[True]
                off_rgb, off_a = lamps[False]
                ps._over(img, x0, y0, off_rgb * (1 - v) + on_rgb * v, np.maximum(on_a, off_a))
            else:
                ps._over(img, x0, y0, *lamps[False])
        if r.win is not None:
            img[HB[1]:HB[3]] += halo_c * (0.15 + 0.85 * v) * 0.55
    sc.dyn(lamp_fx)
    return sc


# ═════════════════════════════ 3. ШТАМП НА ПРОГНОЗЕ ═════════════════════════════
PAPER = (240, 234, 219)
INK = (30, 30, 36)
GREY_INK = (118, 114, 108)
SP_FLAGS = {'home': (60, 178, 520, 448), 'away': (560, 178, 1020, 448)}
SP_STAMP = (724, 1070, 11.0, 600, 190)


def _paper():
    rng = np.random.default_rng(21)
    xx, yy = _grid()
    img = np.empty((H, W, 3), F32)
    img[:] = PAPER
    low = _noise(rng, W, H, 60) - 0.5
    mid = _noise(rng, W, H, 9) - 0.5
    img += (low * 14 + mid * 5)[..., None] * np.array((1.0, 1.0, 0.9), F32)
    fib = Image.new('L', (W, H), 0)
    df = ImageDraw.Draw(fib)
    for _ in range(1400):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        ang, L = rng.uniform(0, math.pi), rng.uniform(6, 26)
        bend = rng.normal(0, 3)
        pts = [(x + math.cos(ang) * L * t - math.sin(ang) * bend * t * t, y + math.sin(ang) * L * t +
                math.cos(ang) * bend * t * t) for t in np.linspace(0, 1, 6)]
        df.line(pts, fill=int(rng.uniform(20, 70)), width=1)
    fib = np.asarray(fib.filter(ImageFilter.GaussianBlur(0.5)), F32) / 255
    img -= fib[..., None] * np.array((34, 36, 42), F32)
    # сгиб листа посередине
    cy = H * 0.5
    img += (np.exp(-((yy - cy + 2) / 1.6) ** 2) * 10 - np.exp(-((yy - cy - 1.5) / 2.2) ** 2) * 14 -
            np.exp(-((yy - cy) / 40) ** 2) * 3)[..., None]
    rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    img *= (1 - 0.20 * np.clip(rr / 1.414, 0, 1) ** 2.4)[..., None]
    img *= np.array((1.0, 0.99, 0.965), F32)[None, None] ** (np.clip(rr / 1.414, 0, 1) ** 2 * 3)[..., None]
    return img


def _print_flag(team, color, won):
    """Печатный флаг клуба: цвет клуба по бумаге с растром (точки 45°), эмблема отпечатана в центре."""
    def src(w, h, pad):
        W2, H2 = w + 2 * pad, h + 2 * pad
        yy, xx = np.mgrid[0:H2, 0:W2].astype(F32)
        col = np.array(color, F32) * 0.86 + np.array(PAPER, F32) * 0.14
        if not won:
            g = col @ np.array((0.299, 0.587, 0.114), F32)
            col = (col * 0.25 + g * 0.75) * 0.55 + np.array(PAPER, F32) * 0.45
        t = np.clip(((xx - pad) / w) * 0.6 + ((yy - pad) / h) * 0.4, 0, 1)
        base = col[None, None] * (1.06 - 0.16 * t)[..., None]
        u, v = (xx + yy) / math.sqrt(2) / 6.5, (xx - yy) / math.sqrt(2) / 6.5
        dist = np.hypot(u - np.round(u), v - np.round(v))
        dot = np.clip((0.16 + 0.26 * t - dist) * 9 + 0.5, 0, 1)
        base *= (1 - 0.20 * dot)[..., None]
        img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert('RGBA')
        em = poster._emblem(team, int(min(w, h) * 0.74))
        if not won:
            e = np.asarray(em, F32)
            g = e[..., :3] @ np.array((0.299, 0.587, 0.114), F32)
            e[..., :3] = (e[..., :3] * 0.2 + g[..., None] * 0.8) * 0.8 + 40
            em = Image.fromarray(np.clip(e, 0, 255).astype(np.uint8), 'RGBA')
        img.alpha_composite(em, (int(pad + w / 2 - em.width / 2), int(pad + h / 2 - em.height / 2)))
        return img.convert('RGB')
    return src


class PrintFlag:
    """Печатный флаг на бумаге: волна versus_anim._Flag (своя «ткань»), лёгкая тень на листе."""

    def __init__(self, sc, rect, team, color, side, won):
        _, pole, fph, _ = va.SIDES[side]
        self.f = va._Flag((rect, color, team, 0, (0.5, 0.5), None), pole, fph, sc.cv, src=_print_flag(team, color, won))
        self.zero = np.zeros((H, W), F32)

    def __call__(self, img, i, tau):
        box, rgb, a, tex = self.f.frame(tau, self.zero, (0, 0), 0.0)
        sh = va._drop_shadow(box, a, SIZE) * 0.55
        img *= 1 - sh[..., None]
        ps._over(img, box[0], box[1], va._Canvas.apply(rgb, tex * 0.7), a)


def _over_np(img, rgb, a):
    img *= 1 - a[..., None]
    img += rgb * a[..., None]


def _stamp_pick(r, plates_dir):
    m = r.m
    sc = Scene(grain=1.0)
    acc = m.acc
    accp = versus._mix(acc, -0.38)                 # акцент лиги — типографской краской
    base = _paper()
    lay = _layer()
    d = ImageDraw.Draw(lay)
    # шапка
    for y, wd in ((40, 2), (48, 6)):
        d.rectangle((60 * SS, y * SS, 1020 * SS, (y + wd) * SS), fill=INK)
    fm = F(OSW, 46, 700)
    wj, wt = fm.getlength('JARVIS'), fm.getlength(m.tag)
    x = 540 * SS - (wj + wt + 34 * SS) / 2
    d.text((x, 116 * SS), 'JARVIS', font=fm, fill=INK, anchor='ls')
    d.rectangle((x + wj + 14 * SS, 76 * SS, x + wj + 20 * SS, 116 * SS), fill=INK)
    d.text((x + wj + 34 * SS, 116 * SS), m.tag, font=fm, fill=accp, anchor='ls')
    fl = F(MAN, 16, 800)
    _spaced(d, 62, 98, 'ИТОГ ПРОГНОЗА', fl, GREY_INK, 2.5, anchor='l')
    if m.date:
        _spaced(d, 1018, 98, m.date.upper(), _fit(m.date.upper(), 300, 16, MAN, 800), GREY_INK, 2, anchor='r')
    for y, wd in ((136, 6), (146, 2)):
        d.rectangle((60 * SS, y * SS, 1020 * SS, (y + wd) * SS), fill=INK)
    # клубы под флагами
    for cl, side in ((m.home, 'home'), (m.away, 'away')):
        x0, y0, x1, y1 = SP_FLAGS[side]
        won = r.win is None or r.win == side
        nm = cl['ru'].upper()
        _t(d, (x0 + x1) / 2, 500, nm, _fit(nm, x1 - x0 - 40, 60, ALU, 900), INK if won else GREY_INK)
        city = (cl['sub'] or ('Москва' if 'Москва' in cl['ru'] else '')).upper()
        if city:
            _spaced(d, (x0 + x1) / 2, 540, city, _fit(city, 360, 15, MAN, 700), GREY_INK, 2)
    # итоговый счёт в рамке
    lab = 'ФИНАЛ' + (' · ' + _mark_text(r.mark) if r.mark else '')
    fsc = F(OSW, 104, 700)
    score = '%d : %d' % (r.sh, r.sa)
    bw = max(fsc.getlength(score) / SS + 90, F(MAN, 16, 800).getlength(lab) / SS + 60, 300)
    BX0, BY0, BX1, BY1 = 540 - bw / 2, 572, 540 + bw / 2, 730
    d.rectangle((BX0 * SS, BY0 * SS, BX1 * SS, BY1 * SS), outline=INK, width=4 * SS)
    d.rectangle(((BX0 + 8) * SS, (BY0 + 8) * SS, (BX1 - 8) * SS, (BY1 - 8) * SS), outline=INK, width=1 * SS)
    _spaced(d, 540, BY0 + 30, lab, F(MAN, 16, 800), accp, 4)
    _t(d, 540, BY0 + 96, ':', fsc, GREY_INK)
    _t(d, 518, BY0 + 98, str(r.sh), fsc, INK if r.win != 'away' else GREY_INK, anchor='rm')
    _t(d, 562, BY0 + 98, str(r.sa), fsc, INK if r.win != 'home' else GREY_INK, anchor='lm')
    # «ПРОГНОЗ» с линейками
    if m.pick:
        lw = _spaced(d, 540, 772, 'ПРОГНОЗ', F(MAN, 22, 800), accp, 8)
        for s in (-1, 1):
            d.line(((540 + s * (lw / 2 + 22)) * SS, 772 * SS, (540 + s * 460) * SS, 772 * SS), fill=INK, width=2 * SS)
        f, lines, lh = _wrap_fit(m.pick.upper(), 940, 190, 104, ALU, 900, max_lines=2, lead=0.92)
        y = 796 + (190 - lh * len(lines)) / 2
        for ln in lines:
            _t(d, 540, y + lh / 2, ln, f, INK)
            y += lh
        if m.kef is not None:
            fk, fkl = F(OSW, 58, 700), F(MAN, 22, 800)
            kt = _n(m.kef)
            kw = (fk.getlength(kt) + fkl.getlength('КЭФ') + 22 * SS) / SS + 64
            KX0, KY0, KY1 = 60, 1022, 1104
            d.rectangle((KX0 * SS, KY0 * SS, (KX0 + kw) * SS, KY1 * SS), fill=INK)
            _t(d, KX0 + 32, (KY0 + KY1) / 2 + 1, 'КЭФ', fkl, PAPER, anchor='lm')
            _t(d, KX0 + kw - 32, (KY0 + KY1) / 2 + 3, kt, fk, versus._mix(acc, 0.1), anchor='rm')
    # подвал
    d.rectangle((60 * SS, 1236 * SS, 1020 * SS, 1240 * SS), fill=INK)
    if r.periods:
        line = 'ПО ПЕРИОДАМ:  ' + '  ·  '.join(('%d:%d' % (a, b)) if lab_ in '123' else '%s %d:%d' % (lab_, a, b)
                                               for lab_, a, b in r.periods)
        _t(d, 62, 1268, line, _fit(line, 600, 18, MAN, 700), GREY_INK, anchor='lm')
    _spaced(d, 1018, 1268, '%s · СЕЗОН 2026/27' % m.tag, F(MAN, 15, 800), GREY_INK, 2, anchor='r')
    for y, wd in ((1294, 2), (1300, 6)):
        d.rectangle((60 * SS, y * SS, 1020 * SS, (y + wd) * SS), fill=INK)
    rgb, a = _arr(lay)
    _over_np(base, rgb, a)
    # штамп: чернила частью впитаны в лист, частью лежат поверх печати
    cx, cy, ang, sw, sh_ = SP_STAMP
    master = _stamp_master(r.word, r.hit, (255, 255, 255), sw, sh_, seed=5)
    rgb_s, a_s, ink_s = master
    stamp = Stamp((rgb_s, a_s, ink_s), cx, cy, ang, shadow=None)
    prem, sa, ink = stamp.rest()
    reg = base[stamp.fy, stamp.fx]
    inkc = np.array(r.ink, F32)
    k = sa[..., None]
    reg[:] = reg * (1 - 0.45 * k + 0.45 * k * inkc / 255)       # впиталось в бумагу (умножение)
    reg[:] = reg * (1 - 0.72 * k) + inkc * 0.72 * k               # и легло поверх печати
    sc.static(base)
    # печатные флаги колышутся
    for cl, side in ((m.home, 'home'), (m.away, 'away')):
        sc.dyn(PrintFlag(sc, SP_FLAGS[side], cl['ru'], cl['color'], side, r.win is None or r.win == side))
    # блик по сырым чернилам штампа
    xs, ys_ = stamp.xx, stamp.yy

    def sheen(img, i, tau):
        add = _pass(tau, xs, ys_, (cx - sw / 2, cy - sh_ / 2 - 70, cx + sw / 2, cy + sh_ / 2 + 70), -34, 46, 0.30, 0.25, 0.85)
        breath = 0.5 + 0.5 * math.cos(2 * math.pi * tau)
        img[stamp.fy, stamp.fx] += (add + np.array(r.ink, F32) * 0.10 * breath) * sa[..., None]
    sc.dyn(sheen)
    return sc


# ═════════════════════════════ 4. ВЕРДИКТ — АНИМАЦИЯ ═════════════════════════════
# Тот же «Разбор прогноза», что ice_more2.single(m, style='verdict') (его вывод не меняется): все слои рисует
# сам ice_more2 — здесь только перехватываются эмблема победителя (она «парит» отдельно) и готовые фон/слой перед
# сохранением. Движение: верх цвета победителя колышется как ткань, эмблема победителя парит с тенью, проигравший
# неподвижен; по счёту проходит блик; плашка «✓ ЗАШЁЛ» мягко пульсирует, по ней пробегает глянец; маленькая ✓
# в строке расчёта дорисовывается заново. Лёд и карточка неподвижны.
VD_TOP = 640                                  # высота «шёлка» в цвете победителя (ice_more2._final_top)


@contextlib.contextmanager
def _verdict_capture(win_idx):
    """ice_more2._put → эмблема победителя (win_idx-й вызов) не рисуется, а запоминается;
    results_styles._finish → фон и слой запоминаются, файл не пишется."""
    import ice_more2 as im2
    import results_styles as rs
    cap, calls = {}, []
    put0, fin0 = im2._put, rs._finish

    def put(ov, im, cx, cy, shadow=True, blur=8):
        calls.append(1)
        if len(calls) - 1 == win_idx:
            cap['emblem'] = (im, cx, cy, blur)
            return None
        return put0(ov, im, cx, cy, shadow, blur)

    def finish(bg, ov, H_, path, grain):
        cap.update(bg=bg, ov=ov, grain=grain)
        return path
    im2._put, rs._finish = put, finish
    try:
        yield cap
    finally:
        im2._put, rs._finish = put0, fin0


def verdict_m(r, checks=None):
    """Словарь матча для ice_more2.single(..., style='verdict') из данных рендера. checks=None — строка расчёта
    по итогу: «1:5 — ПОБЕДА СПАРТАКА В ОСНОВНОЕ ВРЕМЯ» с отметкой hit."""
    import ice_more2 as im2
    m = r.m
    if checks is None and r.win:
        w = im2._short(m.home['ru'] if r.win == 'home' else m.away['ru'])
        how = {'': 'В ОСНОВНОЕ ВРЕМЯ', 'ОТ': 'В ОВЕРТАЙМЕ', 'Б': 'ПО БУЛЛИТАМ'}.get(r.mark, '')
        checks = [('%d:%d%s — ПОБЕДА %s %s' % (r.sh, r.sa, (' ' + r.mark) if r.mark else '', im2.WIN_GEN.get(w, w), how),
                   r.hit)]
    pick = dict(text=(m.pick or '').upper(), odds=m.kef, hit=r.hit, checks=checks or [])
    return dict(home=m.home['ru'], away=m.away['ru'], sh=r.sh, sa=r.sa, mark=r.mark or '', date=m.date, tag=m.tag,
                pick=pick)


def _verdict_geom(vm):
    """Положение плашки «ЗАШЁЛ» и кружков строки расчёта — те же формулы, что в ice_more2._s_verdict (px кадра)."""
    import ice_more2 as im2
    S = im2.S
    pk = vm['pick']
    hit = pk.get('hit')
    lift = 0 if pk.get('odds') else 40
    word = 'ЗАШЁЛ' if hit else 'НЕ ЗАШЁЛ' if hit is not None else 'ВОЗВРАТ'
    fs = im2.F(OSW, 70 * S, 700)
    sw = (fs.getlength(word) + (150 if hit is not None else 90) * S) / S
    y0, y1 = 690, 1258
    ys0, ys1 = y0 + 262 - lift, y0 + 372 - lift
    pill = (540 - sw / 2, ys0, 540 + sw / 2, ys1)
    fill = im2.GREEN if hit else im2.LOSS if hit is not None else (120, 128, 142)
    ticks = []
    checks = list(pk.get('checks') or [])
    if checks:
        fc = im2.F(MAN, 22 * S, 800)
        lh = 54
        bw = (max(fc.getlength(t) for t, _ in checks) + 46 * S) / S
        bx = 540 - bw / 2
        yc = (ys1 + y1) / 2 - lh * (len(checks) - 1) / 2
        for k, (_, ok) in enumerate(checks):
            ticks.append((bx + 15, yc + k * lh, ok, (120, 128, 142) if ok is None else im2.GREEN if ok else im2.LOSS))
    return pill, fill, ticks


def _float_pose(tau):
    """Парение эмблемы победителя: в нуле цикла — ровно поза статичного баннера."""
    s1 = math.sin(2 * math.pi * tau)
    return 1 + 0.014 * s1, 0.25 * max(0.0, s1), 1.6 * math.sin(2 * math.pi * tau + 0.5) - 1.6 * math.sin(0.5), \
        -5.0 * s1, 1.2 * math.sin(2 * math.pi * tau)


def _bump(tau, t0, t1):
    if not t0 < tau < t1:
        return 0.0
    return math.sin(math.pi * (tau - t0) / (t1 - t0)) ** 2


def _verdict_anim(r, plates_dir, checks=None):
    import ice_more2 as im2
    import quality
    vm = verdict_m(r, checks)
    S = im2.S
    with _verdict_capture(0 if r.sh > r.sa else 1) as cap:
        im2.single(vm, os.devnull, style='verdict', league=r.m.league)
    bg, ov = cap['bg'], cap['ov']
    sc = Scene(grain=cap['grain'])                                  # то же зерно, что у статичного (0.2)
    bg1 = np.asarray(bg.convert('RGB'), F32)
    sc.static(bg1)

    # верх цвета победителя колышется как ткань (versus_anim._Flag; края — за кадром, нижняя кромка ровная)
    silk = bg1[:VD_TOP]

    def src(w, h, pad):
        return Image.fromarray(np.clip(np.pad(silk, ((pad, pad), (pad, pad), (0, 0)), mode='reflect'), 0, 255)
                               .astype(np.uint8))
    flag = va._Flag(((0, 0, W, VD_TOP), (0, 0, 0), '', 0, (0.5, 0.5), None), 'l', 0.0, sc.cv, src=src)
    flag.open['b'] = True
    zero = np.zeros((H, W), F32)
    scr_top = sc.cv.screen[:VD_TOP]

    def cloth(img, i, tau):
        saved = va.WAVES, va.FOLD
        va.WAVES = tuple((amp * 0.85,) + tuple(w) for amp, *w in saved[0])
        va.FOLD = saved[1] * 0.75
        try:
            box, rgb, a, _ = flag.frame(tau, zero, (0, 0), 0.0)
        finally:
            va.WAVES, va.FOLD = saved
        img[:VD_TOP] = va._Canvas.apply(rgb[:VD_TOP - box[1], :W - box[0]], scr_top)
    sc.dyn(cloth)

    # эмблема победителя парит; тень — как у ice_more._put (сдвиг 0/4, размытие 10, (20, 40, 80, 80)), отстаёт
    if 'emblem' in cap:
        em, ecx, ecy, blur = cap['emblem']
        if S != SS:
            em = em.resize((round(em.width * SS / S), round(em.height * SS / S)), Image.LANCZOS)
        e = np.asarray(em, F32)
        master = (e[..., :3], e[..., 3] / 255, e[..., 3] / 255)
        sprite = Stamp(master, ecx / S, ecy / S, 0.0, pose=_float_pose, shadow=(0, 4, blur, 80 / 255),
                       shadow_rgb=(20, 40, 80), lag=0.6)
        sc.dyn(sprite)

    # всё остальное — слой ice_more2 как есть (текст, проигравший, счёт, плашки, карточка, @jarvibet)
    sc.layer(ov)
    ov_a = _arr(ov)[1]

    # блик по счёту: полоса света через цифры и шёлк вокруг (белые цифры светятся ореолом)
    SB = (360, 286, 720, 456)
    xs, ys_ = np.meshgrid(np.arange(SB[0], SB[2], dtype=F32), np.arange(SB[1], SB[3], dtype=F32))
    glyph = ov_a[SB[1]:SB[3], SB[0]:SB[2]]
    halo = np.clip(ps._blur_arr(glyph, 6) * 1.4, 0, 1)
    soft = np.exp(-(((xs - 540) / 170) ** 4 + ((ys_ - 372) / 72) ** 4))

    def score_sweep(img, i, tau):
        if not 0.04 < tau < 0.42:
            return
        add = _pass(tau, xs, ys_, SB, -22, 30, 0.42, 0.05, 0.40)
        img[SB[1]:SB[3], SB[0]:SB[2]] += add * (0.30 * soft + 0.75 * halo)[..., None]
    sc.dyn(score_sweep)

    # плашка вердикта: мягкий пульс (масштаб из кадра 3×), ореол её цвета, потом глянец
    pill, fill, ticks = _verdict_geom(vm)
    comp = quality.compose(bg, ov)                                  # 3× — тот же состав, что у статичного
    PX0, PY0, PX1, PY1 = int(pill[0]) - 34, int(pill[1]) - 30, int(math.ceil(pill[2])) + 34, int(pill[3]) + 40
    crop = comp.crop((PX0 * S, PY0 * S, PX1 * S, PY1 * S))
    cw, ch_ = PX1 - PX0, PY1 - PY0
    pm_ = Image.new('L', (cw * S, ch_ * S), 0)
    ImageDraw.Draw(pm_).rounded_rectangle(((pill[0] - PX0) * S, (pill[1] - PY0) * S, (pill[2] - PX0) * S,
                                           (pill[3] - PY0) * S), radius=55 * S, fill=255)
    pmask = np.asarray(pm_.resize((cw, ch_), Image.LANCZOS), F32) / 255
    pglow = ps._blur_arr(pmask, 12) * (1 - pmask)
    pcol = np.array(versus._mix(fill, 0.25), F32)
    scr_p = sc.cv.screen[PY0:PY1, PX0:PX1]
    pxs, pys = np.meshgrid(np.arange(PX0, PX1, dtype=F32), np.arange(PY0, PY1, dtype=F32))
    pc = np.array(((pill[0] + pill[2]) / 2 - PX0, (pill[1] + pill[3]) / 2 - PY0), F32) * S

    def pill_fx(img, i, tau):
        b = _bump(tau, 0.34, 0.62)
        reg = img[PY0:PY1, PX0:PX1]
        if b > 0:
            sk = 1 + 0.035 * b
            coef = (1 / sk, 0, pc[0] - pc[0] / sk, 0, 1 / sk, pc[1] - pc[1] / sk)
            big = crop.transform(crop.size, Image.AFFINE, coef, resample=Image.BICUBIC)
            rgb = np.asarray(big.convert('RGB').resize((cw, ch_), Image.LANCZOS), F32)
            reg[:] = va._Canvas.apply(rgb, scr_p)
            reg += (pglow * 0.55 * b)[..., None] * pcol
        g = _pass(tau, pxs, pys, pill, -24, 34, 0.38, 0.60, 0.86)
        reg += g * pmask[..., None]
    sc.dyn(pill_fx)

    # маленькая ✓ в строке расчёта дорисовывается заново
    tk = []
    for tx, ty, ok, col in ticks:
        bx0, by0 = int(tx - 22), int(ty - 22)
        base = comp.crop((bx0 * S, by0 * S, (bx0 + 44) * S, (by0 + 44) * S)).convert('RGB')
        tk.append((bx0, by0, tx - bx0, ty - by0, ok, col, base))

    def tick_fx(img, i, tau):
        if not 0.70 <= tau < 0.86:
            return
        p = _ease((tau - 0.70) / 0.12)
        for bx0, by0, cx, cy, ok, col, base in tk:
            t = base.copy()
            d = ImageDraw.Draw(t)
            d.ellipse(((cx - 15) * S, (cy - 15) * S, (cx + 15) * S, (cy + 15) * S), fill=col)
            _partial_tick(d, cx * S, cy * S, 8 * S, ok, (255, 255, 255), 3 * S, p)
            rgb = np.asarray(t.resize((44, 44), Image.LANCZOS), F32)
            img[by0:by0 + 44, bx0:bx0 + 44] = va._Canvas.apply(rgb, sc.cv.screen[by0:by0 + 44, bx0:bx0 + 44])
    sc.dyn(tick_fx)
    return sc


def _partial_tick(d, x, y, r, ok, fill, w, p):
    """ice_more2._tick, нарисованная на долю p длины (✓ — одним штрихом, ✗ — двумя по очереди, черта)."""
    if ok is None:
        strokes = [[(x - r * .75, y), (x + r * .75, y)]]
    elif ok:
        strokes = [[(x - r, y), (x - r * 0.3, y + r * 0.7), (x + r, y - r * 0.7)]]
    else:
        strokes = [[(x - r * .7, y - r * .7), (x + r * .7, y + r * .7)], [(x - r * .7, y + r * .7), (x + r * .7, y - r * .7)]]
    segs = [(a, b) for st in strokes for a, b in zip(st[:-1], st[1:])]
    total = sum(math.dist(a, b) for a, b in segs)
    left = p * total
    for a, b in segs:
        if left <= 0:
            break
        L = math.dist(a, b)
        k = min(1.0, left / L)
        e = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
        d.line((a, e), fill=fill, width=int(w))
        for q in (a, e):
            d.ellipse((q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2), fill=fill)
        left -= L


BUILDERS = {'versus_final': _versus_final, 'tablo_final': _tablo_final, 'stamp_pick': _stamp_pick,
            'verdict_anim': _verdict_anim}


# ───────────────────────────── сборка ─────────────────────────────
def scene(home, away, sh, sa, mark='', league='KHL', date='', pick='', kef=None, hit=True, periods=None,
          style='versus_final', plates_dir='out/anim/plates', checks=None):
    r = _result(home, away, sh, sa, mark, league, date, pick, kef, hit, periods)
    if style == 'verdict_anim':
        return _verdict_anim(r, plates_dir, checks)
    if style == 'verdict_rings':                          # тот же «Итог матча», верх — кольца «Versus» вместо шёлка
        import ice_more2 as im2
        top0, im2.TOP_BG = im2.TOP_BG, 'rings'
        try:
            return _verdict_anim(r, plates_dir, checks)
        finally:
            im2.TOP_BG = top0
    return BUILDERS[style](r, plates_dir)


def still(home, away, sh, sa, path_jpg, tau=0.0, **kw):
    """Один кадр (проверка раскладки) → path_jpg."""
    sc = scene(home, away, sh, sa, **kw)
    n = SECONDS * FPS
    i = int(round(tau * n)) % n
    try:
        fr = sc.frame(i, i / n)
    finally:
        sc.close()
    os.makedirs(os.path.dirname(path_jpg) or '.', exist_ok=True)
    Image.fromarray(fr).save(path_jpg, quality=92)
    return path_jpg


def render(home, away, sh, sa, path_mp4, mark='', league='KHL', date='', pick='', kef=None, hit=True, periods=None,
           style='versus_final', plates_dir='out/anim/plates', first=None, sheet=None, target_mb=2.8, checks=None):
    """Анимированный послематчевый баннер стиля style → path_mp4 (H.264 1080×1350, 30 fps, 4 с, бесшовный цикл).
    → dict(path, seconds — время сборки вместе с недостающими плашками, mb — размер)."""
    t0 = _clock.time()
    sc = scene(home, away, sh, sa, mark, league, date, pick, kef, hit, periods, style, plates_dir, checks)
    n = SECONDS * FPS
    try:
        frames = [sc.frame(i, i / n) for i in range(n)]
    finally:
        sc.close()
    os.makedirs(os.path.dirname(path_mp4) or '.', exist_ok=True)
    va._encode_mp4(frames, path_mp4, FPS, target_mb)
    base = os.path.splitext(path_mp4)[0]
    if first:
        Image.fromarray(frames[0]).save(base + '.jpg' if first is True else first, quality=92)
    if sheet:
        va._sheet(frames, base + '_frames.jpg' if sheet is True else sheet, FPS)
    return dict(path=path_mp4, seconds=_clock.time() - t0, mb=os.path.getsize(path_mp4) / 1e6)


def overview(tiles, path, tile_w=400):
    """Лист «первые кадры рядом»: tiles — [(подпись, путь .jpg), …], плитки 4:5."""
    th = tile_w * H // W
    gap, lab = 14, 40
    n = len(tiles)
    sheet = Image.new('RGB', (n * tile_w + (n + 1) * gap, th + lab + 2 * gap), (32, 32, 36))
    d = ImageDraw.Draw(sheet)
    f = brand_kit.font(MAN, 19, 800)
    for k, (label, p) in enumerate(tiles):
        x = gap + k * (tile_w + gap)
        d.text((x + 4, gap + lab / 2), label, font=f, fill=(230, 200, 120), anchor='lm')
        sheet.paste(Image.open(p).convert('RGB').resize((tile_w, th), Image.LANCZOS), (x, gap + lab))
    sheet.save(path, quality=90)
    return path
