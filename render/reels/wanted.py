# -*- coding: utf-8 -*-
"""«Розыск» — Дикий Запад: обветренная дощатая стена салуна на закате, пыль в косых лучах, на доли трека к стене
прибивают старые бумажные плакаты «РАЗЫСКИВАЕТСЯ».

Мир — одна длинная стена (вагонка, гвозди, стыки досок, тёплый закатный свет сверху, сумрак снизу); камера едет вдоль
неё от места к месту, на переездах по низу кадра катится перекати-поле. Плакат клуба — состаренная бумага с рваным
краем и подпалинами: «РАЗЫСКИВАЕТСЯ» жирным антиквенным шрифтом, «портрет» — эмблема сепией (печать с гравировкой),
по бокам портрета очки за N матчей и место, ниже имя клуба брусковым «вестерн»-шрифтом и «приметы» — последние 3 игры
печатными строками (штамп В зелёной краской / П красной, у поражения — пулевое отверстие; счёт, ОТ/Б, соперник,
дата, дома/в гостях), разница шайб и серия — косым штампом. Пустые (None) поля не показываются.

Сцены (u — доля трека, D — дроп; всё — на долях от дропа, team / duel / hold / cta — параметры):
  интро (до D − (2·team + duel) долей) — указатель на столбе: доска JARVIS | NHL, две доски-стрелки с эмблемами
                  (хозяева влево, гости вправо), доска со временем МСК и линия П1 · Х · П2 — три большие латунные
                  таблички (доски въезжают на половинах долей, таблички падают на цепях);
  клуб ×2 (team долей) — за полдоли до сцены камера едет вдоль стены (перекати-поле), ровно на долю плакат
                  прибивают (удар, тряска, пыль из-под гвоздей); через полдоли — по строке игр на каждую половину
                  доли (штамп; у поражения — выстрел), затем цифры по бокам портрета и разница шайб, штамп серии;
  дуэль (duel долей) — камера отъезжает, оба плаката рядом трепещут на ветру (всё сильнее), сверху часы:
                  секундная стрелка щёлкает на половинах долей 11:59:56 → 57 → 58 → 59, под плакатами П1 и П2;
  ДРОП (hold долей) — ровно на дропе полдень: вспышка, удар латунной звезды шерифа, второй плакат разлетается
                  клочками; остаётся только плакат команды прогноза (одна эмблема, уже в цвете, без второй и без «VS»):
                  прогноз (form.split_pick) и кэф строкой «НАГРАДА»; на каждую долю — блик по звезде и пульс кэфа;
  финал (cta долей) — плакат падает, звезда поднимается, прогноз коротко и плашка Telegram (C.tg_plate).
@jarvibet — у низа безопасной зоны (y 1448), одинаково во всех сценах до плашки Telegram (там он — в плашке).
Кадр — чистая функция t: стена, плакаты, таблички, звезда и часы строятся один раз в конструкторе (до fork —
общие для процессов), случайность — только с фиксированным зерном.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels.core import W, H

C.FONTS.setdefault('podkova', 'Podkova[wght].ttf')          # брусковый «вестерн» (кириллица)
C.FONTS.setdefault('yeseva', 'YesevaOne-Regular.ttf')        # жирная антиква «афиши»

SLAB, FAT = 'podkova', 'yeseva'
INK = (46, 28, 16)
INK_RED = (156, 34, 24)
INK_GREEN = (34, 100, 52)
PAPER = (228, 206, 160)
CREAM = (248, 232, 196)
BRASS_L, BRASS, BRASS_D = (255, 228, 150), (214, 164, 72), (112, 72, 24)

MX, VY = 40, 960                      # мир: поле слева и высота над «обычным» кадром
WW, WH = 3 * W + 2 * MX + 40, 2 * H   # стена: три места (указатель, плакат 1, плакат 2) + отъезд камеры ×0,5
PW, PH = 920, 1160                    # плакат
PCY = 825                             # центр плаката в кадре (верх 245, низ 1405)
HY = 1448                             # @jarvibet
DUEL_Z = 0.5

_CACHE = {}


# ─────────────────────────────── утилиты ───────────────────────────────
def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def streak_txt(s):
    """«В2» → «2 ПОБЕДЫ ПОДРЯД» (серии от двух игр), иначе ''."""
    s = str(s or '').strip().upper()
    if len(s) < 2 or not s[1:].isdigit():
        return '', None
    n = int(s[1:])
    if n < 2:
        return '', None
    if s[0] in ('В', 'W'):
        return '%d %s ПОДРЯД' % (n, plural(n, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД')), 'В'
    if s[0] in ('П', 'L'):
        return '%d %s ПОДРЯД' % (n, plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ')), 'П'
    return '', None


def _noise(w, h, cell, rng, smooth=Image.BICUBIC):
    """Плавный шум N(0,1)-подобный (w×h, «зерно» cell px) → float32."""
    sw, sh = max(2, int(w / cell) + 2), max(2, int(h / cell) + 2)
    a = rng.normal(0, 1, (sh, sw)).astype(np.float32)
    a = (np.clip(a, -3, 3) + 3) / 6 * 255
    im = Image.fromarray(a.astype(np.uint8), 'L').resize((w, h), smooth)
    return (np.asarray(im, np.float32) / 255 * 6 - 3) / 1.0


def _ink(im, seed=1, k=0.28):
    """«Печать по бумаге»: альфа текста с пятнистым недоливом краски."""
    rng = np.random.default_rng(seed)
    a = np.asarray(im.getchannel('A'), np.float32)
    n = _noise(im.width, im.height, 3, rng) * 0.5 + _noise(im.width, im.height, 22, rng) * 0.5
    m = np.clip(1 - k * np.clip(n, 0, 3) / 1.6, 0.55, 1)
    out = im.copy()
    out.putalpha(Image.fromarray((a * m).astype(np.uint8), 'L'))
    return out


def txt(s, size, col=INK, font=SLAB, wght=800, max_w=None, track=0.0, seed=3, ink=True):
    im = C.text(s, font, size, col, wght, track=track, max_w=max_w)
    return _ink(im, seed) if ink else im


def _rotate(im, deg):
    return im if abs(deg) < 0.05 else im.rotate(deg, Image.BICUBIC, expand=True)


# ─────────────────────────────── фактуры ───────────────────────────────
def _wall(seed=11):
    """Дощатая стена (вагонка) с закатным светом → RGBA WW×WH."""
    rng = np.random.default_rng(seed)
    out = np.empty((WH, WW, 3), np.uint8)
    ph = 118
    ys = np.arange(WH, dtype=np.float32)
    gl = np.interp(ys, [0, VY - 300, VY + 180, VY + 900, VY + 1500, VY + 1920, WH],
                   [0.55, 0.9, 1.16, 1.0, 0.82, 0.66, 0.42]).astype(np.float32)
    warm = np.stack([np.interp(ys, [0, VY + 200, VY + 1920, WH], v) for v in
                     ([1.0, 1.10, 0.92, 0.80], [0.86, 0.95, 0.84, 0.76], [0.80, 0.78, 0.84, 0.86])], 1).astype(np.float32)
    patch = _noise(WW, WH // 4, 90, rng)
    patch = np.asarray(Image.fromarray(((np.clip(patch, -3, 3) + 3) * 42).astype(np.uint8)).resize((WW, WH), Image.BILINEAR),
                       np.float32) / 42 - 3
    xs = np.arange(WW, dtype=np.float32)
    joints = []
    for y0 in range(0, WH, ph):
        h = min(ph, WH - y0)
        lum0 = rng.uniform(0.82, 1.1)
        grey = rng.uniform(0, 0.35)
        base = np.array([118, 76, 44], np.float32) * lum0
        base = base * (1 - grey) + np.array([104, 90, 76], np.float32) * lum0 * grey
        n1 = np.interp(xs, np.linspace(0, WW, 48), rng.normal(0, 1, 48)).astype(np.float32) * rng.uniform(8, 22)
        yy = np.arange(h, dtype=np.float32)[:, None]
        s1 = np.sin((yy + n1[None, :]) * (2 * np.pi / rng.uniform(7, 12)) + rng.uniform(0, 6))
        s2 = np.sin((yy * 1.9 + n1[None, :] * 0.7) * (2 * np.pi / rng.uniform(3.5, 5)) + rng.uniform(0, 6))
        fl = rng.normal(0, 1, (max(2, h // 3), WW // 40 + 2)).astype(np.float32)
        fl = np.asarray(Image.fromarray(((np.clip(fl, -3, 3) + 3) * 42).astype(np.uint8)).resize((WW, h), Image.BILINEAR),
                        np.float32) / 42 - 3
        lum = 1 + 0.055 * s1 + 0.03 * s2 + 0.07 * fl + 0.06 * patch[y0:y0 + h]
        prof = np.ones(h, np.float32)
        k = min(16, h)
        prof[:k] = np.linspace(0.35, 1.0, k) ** 0.8          # тень под нахлёстом верхней доски
        if h > 6:
            prof[-4:] = (1.18, 1.14, 1.08, 1.04)
        lum *= prof[:, None] * gl[y0:y0 + h, None]
        band = base[None, None, :] * lum[..., None] * warm[y0:y0 + h, None, :]
        for _ in range(rng.integers(1, 3)):                   # стыки досок
            jx = int(rng.uniform(60, WW - 60))
            band[k:, jx:jx + 3] *= 0.38
            band[k:, jx + 3:jx + 5] *= 1.12
            joints.append((jx, y0 + h * 0.55))
        out[y0:y0 + h] = np.clip(band, 0, 255).astype(np.uint8)
    im = Image.fromarray(out, 'RGB').convert('RGBA')
    d = ImageDraw.Draw(im)
    for jx, jy in joints:                                      # гвозди у стыков и старые дырки
        for dx in (-14, 16):
            x, y = jx + dx, jy + rng.uniform(-8, 8)
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(36, 26, 20, 255))
            d.ellipse((x - 3, y - 4, x + 1, y), fill=(120, 104, 86, 255))
    for _ in range(260):
        x, y = rng.uniform(0, WW), rng.uniform(0, WH)
        r = rng.uniform(1.5, 3.2)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(30, 20, 14, 200))
    return im


def _paper(w, h, seed):
    """Состаренная бумага: пятна, волокна, подпалины, сгибы, рваный край → RGBA."""
    rng = np.random.default_rng(seed)
    big = _noise(w, h, 140, rng)
    mid = _noise(w, h, 30, rng)
    fib = rng.normal(0, 1, (h, w)).astype(np.float32)
    lum = 1 + 0.035 * big + 0.02 * mid + 0.025 * fib
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    en = _noise(w, h, 18, rng) * 7 + _noise(w, h, 60, rng) * 9
    burn = np.clip(1 - (d - en * 0.6) / 70, 0, 1) ** 1.6                # подпалины к краю
    for _ in range(5):                                                   # пятна
        cx, cy, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(40, 130)
        s = np.clip(1 - np.hypot(xx - cx, yy - cy) / r, 0, 1) ** 2
        lum -= s * rng.uniform(0.04, 0.09)
    for fy in (h * rng.uniform(0.47, 0.53),):                            # сгиб
        lum += np.exp(-((yy - fy) / 2.0) ** 2) * 0.05 - np.exp(-((yy - fy - 4) / 3.0) ** 2) * 0.05
    for fx in (w * rng.uniform(0.48, 0.52),):
        lum += np.exp(-((xx - fx) / 2.0) ** 2) * 0.04 - np.exp(-((xx - fx - 4) / 3.0) ** 2) * 0.04
    col = np.array(PAPER, np.float32)[None, None, :] * lum[..., None]
    col = col * (1 - burn[..., None] * 0.62) + np.array([92, 52, 22], np.float32) * burn[..., None] * 0.62
    alpha = np.where(d > 3 + np.clip(en, -2, 14) * 0.7, 255, 0).astype(np.uint8)
    cut = rng.integers(0, 4)                                             # один оторванный угол
    cx, cy = (w if cut % 2 else 0), (h if cut // 2 else 0)
    alpha[np.hypot(xx - cx, yy - cy) < 46 + en * 2] = 0
    arr = np.dstack([np.clip(col, 0, 255).astype(np.uint8), alpha])
    im = Image.fromarray(arr, 'RGBA')
    a = im.getchannel('A').filter(ImageFilter.GaussianBlur(0.8))
    im.putalpha(a)
    im.info['cut'] = (cx, cy)
    return im


def _nails(p):
    """Гвозди по углам плаката (кроме оторванного угла)."""
    cx, cy = p.info.get('cut', (-1, -1))
    for x, y in ((38, 38), (PW - 38, 38), (38, PH - 38), (PW - 38, PH - 38)):
        if abs(x - cx) < 100 and abs(y - cy) < 100:
            continue
        C.put(p, _nail(30), x, y)


def _sepia(emb, ink=INK, light=(238, 220, 182)):
    """Эмблема → сепия-печать с гравировкой."""
    l = np.asarray(emb.convert('L'), np.float32)
    a = emb.getchannel('A')
    am = np.asarray(a, np.float32) > 20
    if am.any():
        lo, hi = np.percentile(l[am], 3), np.percentile(l[am], 97)
        l = np.clip((l - lo) / max(1, hi - lo), 0, 1)
    else:
        l = l / 255
    yy = np.arange(l.shape[0])[:, None]
    lines = 1 - 0.18 * ((yy % 5) < 2) * (1 - l)                  # гравировка — по тёмным местам
    k = (l * lines)[..., None]
    col = np.array(ink, np.float32) * (1 - k) + np.array(light, np.float32) * k
    out = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    out.putalpha(a)
    return out


def _nail(d=30):
    S = 4
    im = Image.new('RGBA', (d * S, d * S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse((S * 2, S * 3, d * S - S, d * S), fill=(0, 0, 0, 110))
    dr.ellipse((0, 0, d * S - S * 3, d * S - S * 3), fill=(58, 46, 38, 255))
    dr.ellipse((S * 4, S * 4, d * S - S * 7, d * S - S * 7), fill=(104, 90, 76, 255))
    dr.ellipse((S * 6, S * 5, S * 13, S * 11), fill=(196, 182, 160, 255))
    return im.resize((d, d), Image.LANCZOS)


def _hole(d=54, seed=5):
    """Пулевое отверстие в бумаге: рваный край, подпалина, тёмная дыра."""
    rng = np.random.default_rng(seed)
    S = 3
    D = d * S
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    c = D / 2
    pts = []
    for k in range(26):
        a = k / 26 * 2 * math.pi
        r = D * (0.36 + rng.uniform(-0.05, 0.1))
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    dr.polygon(pts, fill=(84, 48, 22, 150))
    pts = []
    for k in range(18):
        a = k / 18 * 2 * math.pi
        r = D * (0.2 + rng.uniform(-0.03, 0.07))
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    dr.polygon(pts, fill=(250, 238, 210, 255))
    pts = []
    for k in range(16):
        a = k / 16 * 2 * math.pi
        r = D * (0.15 + rng.uniform(-0.02, 0.04))
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    dr.polygon(pts, fill=(16, 10, 8, 255))
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    return im.resize((d, d), Image.LANCZOS)


def _stamp(letter, col, d=86, seed=1):
    """Круглый штамп краской с буквой."""
    S = 3
    D = d * S
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    w = int(D * 0.075)
    dr.ellipse((w, w, D - w, D - w), outline=tuple(col) + (255,), width=w)
    dr.ellipse((w * 2.6, w * 2.6, D - w * 2.6, D - w * 2.6), outline=tuple(col) + (255,), width=max(2, w // 3))
    im = im.resize((d, d), Image.LANCZOS)
    C.put(im, C.text(letter, SLAB, d * 0.5, col, 800), d / 2, d / 2 + 1)
    return _ink(_rotate(im, (seed * 37) % 21 - 10), seed, 0.42)


def _star(d=260, word='ПРОГНОЗ'):
    """Латунная звезда шерифа: шесть лучей с шариками, гравированное кольцо, слово в центре."""
    S = 3
    D = d * S
    c = D / 2
    R, r = D * 0.40, D * 0.22

    def pts(R, r):
        out = []
        for k in range(12):
            a = -math.pi / 2 + k * math.pi / 6
            rr = R if k % 2 == 0 else r
            out.append((c + rr * math.cos(a), c + rr * math.sin(a)))
        return out
    m = Image.new('L', (D, D), 0)
    dm = ImageDraw.Draw(m)
    dm.polygon(pts(R, r), fill=255)
    for k in range(6):
        a = -math.pi / 2 + k * math.pi / 3
        bx, by = c + (R + D * 0.035) * math.cos(a), c + (R + D * 0.035) * math.sin(a)
        br = D * 0.058
        dm.ellipse((bx - br, by - br, bx + br, by + br), fill=255)
    yy, xx = np.mgrid[0:D, 0:D].astype(np.float32)
    g = np.clip(((xx - D * 0.25) * 0.6 + (yy - D * 0.2)) / (D * 1.1), 0, 1)
    base = np.array(BRASS_L, np.float32) * (1 - g[..., None]) + np.array(BRASS_D, np.float32) * g[..., None]
    sh = np.clip(1 - np.hypot(xx - c * 0.8, yy - c * 0.7) / (D * 0.55), 0, 1)
    base = base + sh[..., None] * 60
    im = Image.fromarray(np.dstack([np.clip(base, 0, 255).astype(np.uint8), np.asarray(m)]), 'RGBA')
    dr = ImageDraw.Draw(im)
    dr.polygon(pts(R * 0.9, r * 0.9), outline=(120, 80, 26, 255), width=int(S * 3))
    cr = D * 0.2
    dr.ellipse((c - cr, c - cr, c + cr, c + cr), fill=(176, 126, 48, 255), outline=(96, 60, 18, 255), width=S * 4)
    cr2 = cr * 0.84
    dr.ellipse((c - cr2, c - cr2, c + cr2, c + cr2), outline=(255, 226, 150, 255), width=S * 2)
    im = im.resize((d, d), Image.LANCZOS)
    C.put(im, C.text(word, SLAB, d * 0.1, (60, 36, 10), 800, max_w=d * 0.35), d / 2, d / 2)
    ed = im.filter(ImageFilter.GaussianBlur(1))
    out = C.with_shadow(im, 10, 0.55, 8)
    return out, ed


def _brass(w, h, r=16):
    """Латунная табличка с фаской и заклёпками."""
    g = C.lgrad(w, h, BRASS_L, BRASS_D, angle=70)
    m = C.rrect(w, h, r, (255, 255, 255)).getchannel('A')
    g.putalpha(m)
    inner = C.rrect(w - 16, h - 16, r * 0.7, None, outline=(255, 236, 170), width=2)
    C.put(g, inner, w / 2, h / 2)
    inner2 = C.rrect(w - 22, h - 22, r * 0.6, None, outline=(110, 70, 22), width=2)
    C.put(g, fade_im(inner2, 0.6), w / 2, h / 2 + 1)
    for x, y in ((22, 22), (w - 22, 22), (22, h - 22), (w - 22, h - 22)):
        C.put(g, C.ellipse(16, 16, (96, 60, 20)), x + 1, y + 1)
        C.put(g, C.ellipse(13, 13, (240, 210, 140)), x, y)
    return g


def fade_im(im, a):
    return C.fade(im, a)


def _plank(w, h, arrow=None, seed=3, tone=1.0):
    """Доска указателя (стрелка влево 'l' / вправо 'r' / без) → RGBA."""
    rng = np.random.default_rng(seed)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xs = np.arange(w, dtype=np.float32)
    n1 = np.interp(xs, np.linspace(0, w, 16), rng.normal(0, 1, 16)).astype(np.float32) * 9
    s1 = np.sin((yy + n1[None, :]) * (2 * np.pi / 9.5) + rng.uniform(0, 6))
    fl = _noise(w, h, 6, rng)
    lum = (1 + 0.07 * s1 + 0.05 * fl) * tone
    lum *= np.interp(np.arange(h), [0, 6, h - 10, h], [1.25, 1.05, 0.95, 0.6])[:, None]
    col = np.array([150, 98, 56], np.float32)[None, None, :] * lum[..., None]
    im = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    S = 2
    m = Image.new('L', (w * S, h * S), 0)
    dm = ImageDraw.Draw(m)
    tip = h * 0.42
    if arrow == 'l':
        poly = [(0, h / 2), (tip, 0), (w, 0), (w, h), (tip, h)]
    elif arrow == 'r':
        poly = [(0, 0), (w - tip, 0), (w, h / 2), (w - tip, h), (0, h)]
    else:
        poly = [(0, 0), (w, 0), (w, h), (0, h)]
    dm.polygon([(x * S, y * S) for x, y in poly], fill=255)
    m = m.resize((w, h), Image.LANCZOS)
    im.putalpha(m)
    edge = m.filter(ImageFilter.MinFilter(9))
    dark = Image.new('RGBA', (w, h), (40, 22, 10, 120))
    ring = Image.fromarray(np.clip(np.asarray(m, np.int16) - np.asarray(edge, np.int16), 0, 255).astype(np.uint8))
    im.alpha_composite(Image.composite(dark, Image.new('RGBA', (w, h), (0, 0, 0, 0)), ring))
    return im


def _tumbleweed(d=210, seed=9):
    rng = np.random.default_rng(seed)
    S = 3
    D = d * S
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    c = D / 2
    for k in range(70):
        r = rng.uniform(0.15, 0.47) * D
        ox, oy = rng.uniform(-0.12, 0.12) * D, rng.uniform(-0.12, 0.12) * D
        a0 = rng.uniform(0, 360)
        col = (int(rng.uniform(96, 168)), int(rng.uniform(66, 116)), int(rng.uniform(30, 60)), 255)
        dr.arc((c + ox - r, c + oy - r, c + ox + r, c + oy + r), a0, a0 + rng.uniform(60, 200), fill=col,
               width=int(rng.uniform(1.5, 3.5) * S))
    return im.resize((d, d), Image.LANCZOS)


def _clock(r=130):
    """Циферблат: латунный обод, римские цифры, риски."""
    S = 3
    D = int(2 * r * S)
    c = D / 2
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse((0, 0, D - 1, D - 1), fill=(96, 60, 20, 255))
    dr.ellipse((S * 6, S * 6, D - S * 6, D - S * 6), fill=(214, 164, 72, 255))
    dr.ellipse((S * 13, S * 13, D - S * 13, D - S * 13), fill=(242, 228, 196, 255), outline=(70, 44, 18, 255), width=S * 2)
    for k in range(60):
        a = k / 60 * 2 * math.pi - math.pi / 2
        r0 = c - S * 20
        r1 = r0 - (S * 16 if k % 5 == 0 else S * 7)
        dr.line((c + r0 * math.cos(a), c + r0 * math.sin(a), c + r1 * math.cos(a), c + r1 * math.sin(a)),
                fill=(46, 28, 16, 255), width=S * (4 if k % 5 == 0 else 2))
    im = im.resize((2 * r, 2 * r), Image.LANCZOS)
    for k, s in ((0, 'XII'), (3, 'III'), (6, 'VI'), (9, 'IX')):
        a = k / 12 * 2 * math.pi - math.pi / 2
        rr = r * 0.62
        C.put(im, C.text(s, FAT, r * 0.2, INK), r + rr * math.cos(a), r + rr * math.sin(a))
    return C.with_shadow(im, 12, 0.5, 10)


def _hand(length, width, col=(30, 18, 10), tail=0.18):
    """Стрелка часов, ось — в центре картинки (для поворота)."""
    S = 3
    L = int(length * S)
    D = 2 * L + 8
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    c = D / 2
    w = width * S
    dr.polygon([(c - w / 2, c + L * tail), (c + w / 2, c + L * tail), (c + w * 0.18, c - L), (c - w * 0.18, c - L)],
               fill=tuple(col) + (255,))
    dr.ellipse((c - w, c - w, c + w, c + w), fill=tuple(col) + (255,))
    return im.resize((D // S, D // S), Image.LANCZOS)


def _rule(w, col=INK, seed=2):
    """Двойная линейка с ромбом посередине."""
    im = Image.new('RGBA', (w, 22), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line((0, 6, w / 2 - 22, 6), fill=tuple(col) + (255,), width=4)
    d.line((w / 2 + 22, 6, w, 6), fill=tuple(col) + (255,), width=4)
    d.line((0, 15, w / 2 - 22, 15), fill=tuple(col) + (255,), width=2)
    d.line((w / 2 + 22, 15, w, 15), fill=tuple(col) + (255,), width=2)
    d.polygon([(w / 2, 0), (w / 2 + 12, 11), (w / 2, 22), (w / 2 - 12, 11)], fill=tuple(col) + (255,))
    return _ink(im, seed, 0.3)


def _puff(d, col=(214, 186, 140)):
    return C.radial(d, d, col, 150, 1.6)


# ─────────────────────────────── ролик ───────────────────────────────
class Wanted(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 67, drop=19 * 60 / 67, line=None, team=6.5,
                 duel=2, hold=5, cta=2.5, seed=31, **kw):
        super().__init__(u, drop, seed)
        self.h, self.a = C.match(home, away, league)
        self.T = {'h': self.h, 'a': self.a}
        self.league, self.when, self.coef, self.line = league, when, coef, line
        self.tag = F.tag(league)
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.raw = {'h': sh or {}, 'a': sa or {}}
        self.st = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.team, self.duel, self.hold, self.cta = team, duel, hold, cta
        self.TS = {'h': self.b(-(2 * team + duel)), 'a': self.b(-(team + duel))}    # удар плаката
        if self.TS['h'] < 2.4:
            raise ValueError('мало времени до дропа для интро')
        self.PAN = 0.5 * u
        self.TD = self.b(-duel)
        self.TC = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = round(min(self.TS['h'] - self.PAN - 0.3, 2.7), 2)
        key = (home, away, league, when, pick, coef, tuple(line or ()), repr(sorted((sh or {}).items()))[:3000],
               repr(sorted((sa or {}).items()))[:3000], seed)
        if 'wall' not in _CACHE:
            _CACHE['wall'] = _wall(11)
        self.wall = _CACHE['wall']
        if key not in _CACHE:
            _CACHE[key] = self._prep()
        self.L = _CACHE[key]
        rng = np.random.default_rng(seed)
        self.motes = [(rng.uniform(0, W), rng.uniform(C.SAFE_TOP - 100, H - 300), rng.uniform(-14, 8), rng.uniform(-10, -2),
                       rng.uniform(0, 6.3), rng.uniform(0.5, 1.4), int(rng.integers(0, 3))) for _ in range(44)]
        self.scraps = [(rng.uniform(-1, 1), rng.uniform(-1.3, 0.3), rng.uniform(26, 70), rng.uniform(16, 44),
                        rng.uniform(-900, 900), rng.uniform(0.85, 1.05)) for _ in range(22)]

    # ── заготовки ──
    def _prep(self):
        L = {}
        L['nail'] = _nail(30)
        L['hole'] = _hole(58)
        L['tw'] = _tumbleweed(210)
        L['puff'] = [_puff(d) for d in (60, 100, 150)]
        L['mote'] = [C.radial(d, d, (255, 222, 160), 200, 1.8) for d in (8, 12, 18)]
        L['handle'] = self._handle()
        L['shadow'] = C.shadow(Image.new('RGBA', (PW, PH), (0, 0, 0, 255)), 22, 0.62)
        L['sign'] = self._signpost()
        for s in ('h', 'a'):
            L['p_' + s] = self._poster(s)
            full = L['p_' + s]['full']
            L['ph_' + s] = full.resize((int(PW * DUEL_Z), int(PH * DUEL_Z)), Image.LANCZOS)
        L['pick'] = self._pick_poster()
        L['star'], _ = _star(250)
        L['star_big'], _ = _star(330)
        L['clock'] = _clock(128)
        L['hand_m'] = _hand(92, 12)
        L['hand_h'] = _hand(60, 16)
        L['hand_s'] = _hand(104, 6, INK_RED, 0.25)
        L['duel_pl'] = {}
        for s, lab, v in (('h', 'П1', (self.line or (None,) * 3)[0]), ('a', 'П2', (self.line or (None,) * 3)[2])):
            if v is None:
                continue
            pl = _brass(400, 118, 18)
            C.put(pl, C.text(lab, SLAB, 50, (70, 40, 12), 800), 100, 60)
            C.put(pl, C.text(C.fmt_k(v), FAT, 84, (40, 22, 6)), 260, 58)
            L['duel_pl'][s] = C.with_shadow(pl, 12, 0.6, 10)
        L['beams'] = self._beams()
        L['vig'] = self._vig()
        rng = np.random.default_rng(4)
        L['grain'] = [(rng.normal(0, 1, (H // 2, W // 2)) * 7).astype(np.int8) for _ in range(6)]
        L['cta'] = self._cta()
        return L

    def _handle(self):
        t = C.text(C.HANDLE, SLAB, 52, CREAM, 800, track=0.04)
        return C.with_shadow(t, 8, 0.85, 3)

    def _beams(self):
        """Косые закатные лучи (экран): добавка к цвету int16, сверху справа."""
        yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) * 4
        p = xx * math.cos(math.radians(62)) - yy * math.sin(math.radians(62))
        rng = np.random.default_rng(12)
        acc = np.zeros_like(p)
        for _ in range(7):
            c0, wd = rng.uniform(-1500, 800), rng.uniform(30, 120)
            acc += np.exp(-((p - c0) / wd) ** 2) * rng.uniform(0.4, 1)
        fall = np.clip(1 - np.hypot(xx - W * 1.05, yy + 200) / 2300, 0, 1) ** 1.3
        a = np.clip(acc, 0, 1.3) * fall
        a = np.asarray(Image.fromarray((np.clip(a, 0, 1.3) * 190).astype(np.uint8)).resize((W, H), Image.BILINEAR),
                       np.float32) / 190
        out = (a[..., None] * np.array([66, 40, 12], np.float32)).astype(np.int16)
        return out

    def _vig(self):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 * 0.7 + ((yy - H * 0.47) / (H / 2)) ** 2)
        v = 1 - 0.58 * np.clip(d / 1.3, 0, 1) ** 2.3
        return (v * 256).astype(np.uint16)[..., None]

    # ── указатель (интро) ──
    def _signpost(self):
        S = {}
        post = _plank(118, 1500, None, 21, 0.62).rotate(0)
        S['post'] = post
        tagp = _plank(460, 76, None, 22, 0.8)
        C.put(tagp, C.with_shadow(C.text(self.tag, SLAB, 40, CREAM, 800, track=0.08), 5, 0.8, 2), 230, 38)
        S['tag'] = C.with_shadow(tagp, 14, 0.6, 12)
        for s, arrow, lab in (('h', 'l', 'ХОЗЯЕВА'), ('a', 'r', 'ГОСТИ')):
            t = self.T[s]
            pw, ph = 960, 236
            p = _plank(pw, ph, arrow, 23 if s == 'h' else 24, 1.0)
            emb = C.fit(t.emb(200), 184, 184)
            ex = 205 if arrow == 'l' else pw - 205 - 30
            tx0, tx1 = (ex + 112, pw - 40) if arrow == 'l' else (60, ex - 112)
            C.put(p, C.with_shadow(emb, 8, 0.7, 6), ex, ph / 2 + 2)
            nm = C.text(t.up, SLAB, 104, CREAM, 800, max_w=tx1 - tx0)
            lb = C.text(lab, SLAB, 36, (238, 206, 150), 700, track=0.18)
            cx = (tx0 + tx1) / 2
            C.put(p, C.with_shadow(lb, 5, 0.8, 2), cx, ph / 2 - 62)
            C.put(p, C.with_shadow(nm, 6, 0.85, 3), cx, ph / 2 + 28)
            C.put(p, _nail(24), pw / 2, 22)
            C.put(p, _nail(24), pw / 2, ph - 22)
            S[s] = C.with_shadow(p, 16, 0.65, 14)
        tp = _plank(760, 98, None, 25, 0.9)
        C.put(tp, C.with_shadow(C.text(self.when.upper(), SLAB, 56, CREAM, 800, max_w=700), 5, 0.85, 3), 380, 50)
        S['time'] = C.with_shadow(tp, 14, 0.6, 12)
        S['odds'] = []
        if self.line:
            for lab, v in zip(('П1', 'Х', 'П2'), self.line):
                pl = _brass(282, 286, 22)
                C.put(pl, C.text(lab, SLAB, 66, (74, 44, 12), 800), 141, 82)
                C.put(pl, C.text(C.fmt_k(v), FAT, 112, (40, 22, 6), max_w=240), 141, 192)
                S['odds'].append(C.with_shadow(pl, 14, 0.65, 12))
        S['chain'] = self._chain(110)
        return S

    def _chain(self, h):
        im = Image.new('RGBA', (22, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for y in range(0, h, 16):
            if (y // 16) % 2:
                d.ellipse((7, y, 15, y + 18), outline=(70, 56, 40, 255), width=3)
            else:
                d.ellipse((3, y, 19, y + 18), outline=(110, 92, 64, 255), width=3)
        return im

    # ── плакаты ──
    def _paper_base(self, s, seed):
        p = _paper(PW, PH, seed)
        cut = p.info['cut']
        C.put(p, txt('РАЗЫСКИВАЕТСЯ', 106, INK, FAT, 400, max_w=820, track=0.02, seed=seed), PW / 2, 106)
        C.put(p, _rule(820, INK, seed), PW / 2, 180)
        p.info['cut'] = cut
        return p

    def _portrait(self, t, sepia=True, w=300, h=270):
        fr = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        bg = C.radial(w * 2, h * 2, (150, 112, 70), 110, 1.2).crop((w / 2, h / 2, w * 1.5, h * 1.5))
        fr.alpha_composite(bg)
        d = ImageDraw.Draw(fr)
        d.rectangle((0, 0, w - 1, h - 1), outline=INK + (255,), width=5)
        d.rectangle((10, 10, w - 11, h - 11), outline=INK + (255,), width=2)
        emb = C.fit(t.emb(260), w - 56, h - 50)
        if sepia:
            emb = _sepia(emb)
        C.put(fr, emb, w / 2, h / 2)
        return _ink(fr, 7, 0.22)

    def _poster(self, s):
        t, st, raw = self.T[s], self.st[s], self.raw[s]
        seed = 41 if s == 'h' else 43
        base = self._paper_base(s, seed)
        C.put(base, self._portrait(t), PW / 2, 330)
        C.put(base, txt(t.up, 112, INK, SLAB, 800, max_w=840, seed=seed + 1), PW / 2, 530)
        C.put(base, _rule(820, INK, seed + 2), PW / 2, 608)
        _nails(base)
        els = []                    # (картинка, x, y, доля от удара, вид)
        games = st['games']
        for k, g in enumerate(games):
            y = 676 + k * 100
            row, hole = self._row(g, k + seed)
            els.append((row, PW / 2, y, 0.5 + 0.5 * k, 'loss' if g['res'] == 'П' else 'win', hole))
        # по бокам портрета: очки и место
        if st['points'] is not None:
            blk = self._side_blk('%d' % st['points'], plural(st['points'], 'ОЧКО', 'ОЧКА', 'ОЧКОВ'),
                                 ('ЗА %d %s' % (st['gp'], plural(st['gp'], 'МАТЧ', 'МАТЧА', 'МАТЧЕЙ'))) if st['gp'] is not None else '',
                                 seed + 5)
            els.append((blk, 152, 330, 2.0, 'stat', None))
        if st['place'] is not None:
            blk = self._side_blk('%d' % st['place'], 'МЕСТО', st['place_scope'].upper(), seed + 6)
            els.append((blk, PW - 152, 330, 2.0, 'stat', None))
        # низ: разница шайб и серия
        bot = []
        if st['gd'] is not None:
            gf, ga = raw.get('gf'), raw.get('ga')
            s1 = 'РАЗНИЦА ШАЙБ  %s' % F.gd_txt(st['gd'])
            if gf is not None and ga is not None:
                s1 += '  (%s–%s)' % (gf, ga)
            bot.append((txt(s1, 50, INK, SLAB, 800, max_w=820, seed=seed + 7), PW / 2, 990, 2.0, 'stat', None))
        sw, sr = streak_txt(raw.get('streak'))
        if sw:
            rb = self._ribbon(sw, INK_GREEN if sr == 'В' else INK_RED, seed + 8)
        else:                                    # серии нет — штамп «хозяева / гости»
            rb = self._ribbon('ХОЗЯЕВА' if s == 'h' else 'ГОСТИ', INK, seed + 8)
        bot.append((rb, PW / 2, 1074, 2.5, 'ribbon', None))
        els += bot
        full = base.copy()
        hole = _hole(58)
        for im, x, y, _, kind, hx in els:
            C.put(full, im, x, y)
            if hx:
                C.put(full, hole, hx, y - 22)
        return dict(base=base, els=els, full=full)

    def _row(self, g, seed):
        """Строка игры: штамп В/П, счёт (+ОТ/Б), соперник, дата и дома/в гостях. → (картинка, позиция дыры)."""
        rw, rh = 840, 96
        im = Image.new('RGBA', (rw, rh), (0, 0, 0, 0))
        col = INK_GREEN if g['res'] == 'В' else INK_RED if g['res'] == 'П' else INK
        C.put(im, _stamp(g['res'] or '?', col, 84, seed), 46, rh / 2)
        sc = txt(g['score'], 66, INK, SLAB, 800, seed=seed)
        C.put(im, sc, 110 + sc.width / 2, rh / 2)
        x = 110 + sc.width + 14
        if g['note']:
            nt = txt(g['note'], 34, INK_RED, SLAB, 800, seed=seed + 1)
            C.put(im, nt, x + nt.width / 2, rh / 2 - 14)
            x += nt.width + 12
        x = max(x, 262)
        where = 'ДОМА' if g.get('home') else 'В ГОСТЯХ' if g.get('home') is not None else ''
        d1 = txt(g['date'], 36, INK, SLAB, 700, seed=seed + 2)
        d2 = txt(where, 28, INK, SLAB, 700, track=0.08, seed=seed + 3) if where else None
        rcol = max(d1.width, d2.width if d2 else 0)
        C.put(im, d1, rw - rcol / 2, rh / 2 - (17 if d2 else 0))
        if d2:
            C.put(im, d2, rw - rcol / 2, rh / 2 + 22)
        opp = txt(g['opp'].upper(), 56, INK, SLAB, 800, max_w=rw - rcol - 24 - x, seed=seed + 4)
        C.put(im, opp, x + opp.width / 2, rh / 2 + 1)
        return im, ((PW / 2 - rw / 2 + 46 + 36) if g['res'] == 'П' else None)

    def _side_blk(self, big, lab, sub, seed):
        n = txt(big, 128, INK, FAT, 400, seed=seed)
        l1 = txt(lab, 38, INK, SLAB, 800, track=0.08, max_w=250, seed=seed + 1)
        l2 = txt(sub, 30, INK, SLAB, 700, max_w=250, seed=seed + 2) if sub else None
        hgt = n.height + 14 + l1.height + (8 + l2.height if l2 else 0)
        im = Image.new('RGBA', (260, hgt), (0, 0, 0, 0))
        C.put(im, n, 130, n.height / 2)
        C.put(im, l1, 130, n.height + 14 + l1.height / 2)
        if l2:
            C.put(im, l2, 130, n.height + 14 + l1.height + 8 + l2.height / 2)
        return im

    def _ribbon(self, word, col, seed):
        t = C.text(word, SLAB, 52, col, 800, track=0.06, max_w=680)
        w, h = t.width + 70, 88
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((2, 2, w - 3, h - 3), outline=tuple(col) + (255,), width=6)
        d.rectangle((12, 12, w - 13, h - 13), outline=tuple(col) + (255,), width=2)
        C.put(im, t, w / 2, h / 2 + 1)
        return _ink(_rotate(im, -2.5), seed, 0.4)

    def _pick_poster(self):
        t = self.T[self.side]
        seed = 47
        p = self._paper_base(self.side, seed)
        C.put(p, self._portrait(t, sepia=False), PW / 2, 330)
        # слева — когда матч
        parts = [x.strip() for x in self.when.replace('МСК', '').split('·')]
        ys = 270
        if len(parts) >= 2:
            C.put(p, txt(parts[0], 44, INK, SLAB, 800, max_w=240, seed=seed), 152, 262)
            C.put(p, txt(parts[1], 66, INK, SLAB, 800, max_w=240, seed=seed + 1), 152, 335)
            C.put(p, txt('МСК', 34, INK, SLAB, 700, track=0.2, seed=seed + 2), 152, 400)
        C.put(p, txt(t.up, 112, INK, SLAB, 800, max_w=840, seed=seed + 3), PW / 2, 530)
        C.put(p, _rule(820, INK, seed + 4), PW / 2, 608)
        C.put(p, txt(self.pick1, 92, INK_RED, SLAB, 800, max_w=840, seed=seed + 5), PW / 2, 690)
        if self.pick2:
            C.put(p, txt(self.pick2, 50, INK, SLAB, 800, track=0.06, max_w=820, seed=seed + 6), PW / 2, 778)
        C.put(p, _rule(820, INK, seed + 7), PW / 2, 846)
        C.put(p, txt('НАГРАДА', 66, INK, FAT, 400, track=0.12, seed=seed + 8), PW / 2, 912)
        _nails(p)
        coef = txt(C.fmt_k(self.coef), 190, INK_RED, FAT, 400, seed=seed + 9) if self.coef else None
        return dict(base=p, coef=coef)

    def _cta(self):
        S = {}
        S['p1'] = C.with_shadow(C.text(self.pick1, SLAB, 92, CREAM, 800, max_w=940), 10, 0.9, 4)
        s2 = (self.pick2 + ' · ' if self.pick2 else '') + (C.fmt_k(self.coef) if self.coef else '')
        S['p2'] = C.with_shadow(C.text(s2.strip(' ·'), SLAB, 54, (255, 214, 140), 800, max_w=940), 8, 0.9, 3)
        S['tg'] = C.with_shadow(C.tg_plate(940, 176), 18, 0.6, 14)
        return S

    # ── камера ──
    def _cam(self, t):
        """→ (x0, y0, z): левый верх видимой части стены и масштаб."""
        u, D = self.u, self.drop
        drift = 5 * math.sin(t * 0.9)
        th, ta = self.TS['h'], self.TS['a']
        if t >= D:
            sx = W if self.side == 'h' else 2 * W
            return MX + sx + drift, VY, 1.0
        if t < th - self.PAN:
            x = 0.0
        elif t < th:
            x = W * C.in_out(C.seg(t, th - self.PAN, th))
        elif t < ta - self.PAN:
            x = W
        elif t < ta:
            x = W + W * C.in_out(C.seg(t, ta - self.PAN, ta))
        else:
            x = 2 * W
        if t < self.TD:
            return MX + x + drift, VY, 1.0
        k = C.out_cubic(C.seg(t, self.TD, self.TD + 0.25 * u))
        z = 1 / C.lerp(1.0, 1 / DUEL_Z, k)
        z *= 1 + 0.06 * C.in_cubic(C.seg(t, self.TD + 0.25 * u, D))           # наезд к полудню
        cx = C.lerp(MX + 2 * W + W / 2, MX + 2 * W, k)
        cy = VY + H * C.lerp(0.5, 0.52, k)
        return cx - W / 2 / z + drift * k * 0, cy - H / 2 / z, z

    def _shake(self, t):
        u, D = self.u, self.drop
        dx = dy = 0.0
        hits = [(self.TS['h'], 14), (self.TS['a'], 14), (D, 26), (self.TD + 0.25 * u, 8)]
        for s in ('h', 'a'):
            for im, x, y, off, kind, hole in self.L['p_' + s]['els']:
                if kind in ('loss', 'ribbon'):
                    hits.append((self.TS[s] + off * u, 7 if kind == 'loss' else 5))
        for t0, amp in hits:
            a, b = C.shake(t, t0, amp, 0.32)
            dx += a
            dy += b
        return dx, dy

    def _view(self, x0, y0, z):
        if abs(z - 1) < 1e-4:
            x0 = int(round(C.clamp(x0, 0, WW - W)))
            y0 = int(round(C.clamp(y0, 0, WH - H)))
            return self.wall.crop((x0, y0, x0 + W, y0 + H))
        vw, vh = W / z, H / z
        x0, y0 = C.clamp(x0, 0, WW - vw), C.clamp(y0, 0, WH - vh)
        return self.wall.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + vw, y0 + vh), reducing_gap=None)

    # ── слои ──
    def _poster_img(self, s, t):
        """Плакат клуба в момент t (строки штампуются на половинах долей)."""
        P = self.L['p_' + s]
        u, t0 = self.u, self.TS[s]
        prog = [C.seg(t, t0 + off * u, t0 + off * u + 0.13) for _, _, _, off, _, _ in P['els']]
        if all(p >= 1 for p in prog):
            return P['full']
        key = ('pst', s, tuple(round(p, 3) for p in prog))
        if all(p in (0.0, 1.0) for p in prog) and key in _CACHE:
            return _CACHE[key]
        im = P['base'].copy()
        for (el, x, y, off, kind, hole), p in zip(P['els'], prog):
            if p <= 0:
                continue
            k = C.out_cubic(p)
            sc = C.lerp(1.45 if kind in ('loss', 'win', 'ribbon') else 1.2, 1.0, k)
            C.put(im, C.scale(el, sc), x, y, min(1, p * 2.2))
            if hole and p > 0.3:
                C.put(im, self.L['hole'], hole, y - 22)
        if all(p in (0.0, 1.0) for p in prog):
            _CACHE[key] = im
        return im

    def _draw_sign(self, fr, t, dx):
        S, u = self.L['sign'], self.u
        jolt = 0.0
        for n in (2, 3):
            jolt += 6 * math.exp(-max(0, t - n * u) * 9) * (t >= n * u) * math.sin(max(0, t - n * u) * 40)
        C.put(fr, S['post'], 540 + dx, 260 + 750)
        k = C.out_back(C.seg(t, 0.0, 0.34), 1.2)
        C.put(fr, S['tag'], 540 + dx, C.lerp(-120, 292, k))
        rows = (('h', 0.0, 470, -1), ('a', 0.5, 728, 1))
        for s, off, y, dirn in rows:
            p = C.seg(t, off * u, off * u + 0.42)
            if p <= 0:
                continue
            k = C.out_back(p, 1.1)
            rot = dirn * 7 * (1 - C.out_cubic(p)) * math.cos(p * 9)
            im = _rotate(S[s], rot) if abs(rot) > 0.3 else S[s]
            x = 540 + dirn * (1 - k) * 1150
            C.put(fr, im, x + dx, y + (jolt if s == 'h' else -jolt * 0.6))
        for k_, pl in enumerate(S['odds']):
            t0 = 1.5 * u + k_ * 0.12
            p = C.seg(t, t0, t0 + 0.36)
            if p <= 0:
                continue
            kk = C.out_back(p, 1.5)
            x = 540 + (k_ - 1) * 304 + dx
            y = C.lerp(-300, 1170, kk) + (jolt * 0.5 if k_ != 1 else 0)
            C.put(fr, S['chain'], x - 80, y - 196, anchor='c')
            C.put(fr, S['chain'], x + 80, y - 196, anchor='c')
            C.put(fr, pl, x, y)
        p = C.seg(t, 1.0 * u, 1.0 * u + 0.3)
        if p > 0:
            sy = max(0.02, C.out_back(p, 1.6))
            im = S['time']
            im = im.resize((im.width, max(2, int(im.height * sy))), Image.BILINEAR) if sy < 0.995 or sy > 1.005 else im
            C.put(fr, im, 540 + dx, 912)

    def _tumble(self, fr, t, t0, d, y, size=1.0, rev=False):
        """Перекати-поле катится через кадр за d секунд, начиная с t0."""
        p = (t - t0) / d
        if not 0 <= p <= 1:
            return
        tw = self.L['tw'] if size == 1.0 else C.scale(self.L['tw'], size)
        r = tw.width / 2
        x = C.lerp(-r - 20, W + r + 20, p)
        if rev:
            x = W - x
        hop = abs(math.sin(p * math.pi * 3.2)) * 70 * size
        ang = (-1 if not rev else 1) * (x / r) * 57.3
        im = tw.rotate(ang, Image.BILINEAR)
        C.put(fr, im, x, y - hop)

    def _motes(self, fr, t, a=1.0):
        for x0, y0, vx, vy, ph, sp, sz in self.motes:
            x = (x0 + vx * t * 3 + 18 * math.sin(t * sp + ph)) % W
            y = (y0 + vy * t * 3 + 12 * math.cos(t * sp * 0.8 + ph)) % (H - 360) + 200
            fl = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * sp * 3 + ph * 2))
            C.put(fr, self.L['mote'][sz], x, y, a * fl)

    def _puffs(self, fr, t, t0, pts, d=0.55):
        p = C.seg(t, t0, t0 + d)
        if p <= 0 or p >= 1:
            return
        for k, (x, y, vx, vy) in enumerate(pts):
            im = self.L['puff'][k % 3]
            sc = 0.6 + 1.2 * C.out_cubic(p)
            C.put(fr, C.scale(im, sc), x + vx * C.out_cubic(p), y + vy * C.out_cubic(p), (1 - p) ** 1.5 * 0.9)

    # ── кадр ──
    def frame(self, t):
        u, D, L = self.u, self.drop, self.L
        x0, y0, z = self._cam(t)
        sdx, sdy = self._shake(t)
        x0 -= sdx / z
        y0 -= sdy / z
        fr = self._view(x0, y0, z)

        def scr(wx, wy):
            return (wx - x0) * z, (wy - y0) * z

        # указатель
        if t < self.TS['h'] + 0.1:
            self._draw_sign(fr, t, (MX - x0))
        # плакаты клубов
        if t < D:
            for s, sx in (('h', W), ('a', 2 * W)):
                t0 = self.TS[s]
                if t < t0:
                    continue
                cx, cy = scr(MX + sx + W / 2, VY + PCY)
                if cx < -PW or cx > W + PW:
                    continue
                if t >= self.TD + 0.25 * u:
                    continue                                   # дуэль: плакаты на ветру рисует _duel
                if True:
                    im = self._poster_img(s, t)
                    p = C.seg(t, t0, t0 + 0.14)
                    sc = C.lerp(1.12, 1.0, C.out_cubic(p)) * z
                    if abs(sc - 1) > 0.002:
                        im = im.resize((max(1, int(PW * sc)), max(1, int(PH * sc))), Image.BILINEAR)
                    shd = L['shadow'] if abs(sc - 1) < 0.002 else C.scale(L['shadow'], sc)
                    C.put(fr, shd, cx + 6 * sc, cy + 16 * sc, 0.9 * min(1, p * 3))
                    C.put(fr, im, cx, cy, min(1, p * 4))
                    if p < 1 or t < t0 + 0.6:
                        self._puffs(fr, t, t0, [(cx - 420 * z, cy - 540 * z, -60, -30), (cx + 420 * z, cy - 540 * z, 60, -30),
                                                (cx - 420 * z, cy + 540 * z, -80, 30), (cx + 420 * z, cy + 540 * z, 80, 30),
                                                (cx, cy + 580 * z, 0, 50)])
                    # выстрелы — вспышка у дыры
                    for el, ex, ey, off, kind, hole in L['p_' + s]['els']:
                        if hole:
                            tt = t0 + off * u
                            if tt <= t < tt + 0.12:
                                k = 1 - (t - tt) / 0.12
                                px, py = cx + (hole - PW / 2) * z, cy + (ey - 22 - PH / 2) * z
                                C.put(fr, C.radial(160, 160, (255, 230, 170), int(255 * k), 1.3), px, py)
            if t >= self.TD:
                self._duel(fr, t)
        else:
            self._pick(fr, t)
        # перекати-поле на переездах камеры
        for s in ('h', 'a'):
            self._tumble(fr, t, self.TS[s] - self.PAN - 0.25, 1.15, 1330)
        self._motes(fr, t)
        # @jarvibet — одинаково во всех сценах до плашки Telegram
        ha = 1 - C.seg(t, self.TC, self.TC + 0.2)
        if ha > 0:
            C.put(fr, L['handle'], W / 2, HY, ha)
        return self._post(fr, t)

    def _flap(self, s, t, z):
        """Плакат на ветру (дуэль): ряды бумаги колышутся, сильнее к низу и к полудню."""
        base = self.L['ph_' + s]
        sc = z / DUEL_Z
        if abs(sc - 1) > 0.004:
            base = base.resize((max(1, int(base.width * sc)), max(1, int(base.height * sc))), Image.BILINEAR)
        arr = np.asarray(base)
        h, w = arr.shape[:2]
        k = 0.4 + 0.9 * C.seg(t, self.TD, self.drop)
        ph = 1.3 if s == 'h' else 0.0
        yy = np.arange(h, dtype=np.float32) / h
        off = (k * 10 * yy ** 1.6 * np.sin(t * 9.0 + ph - yy * 5.0)).astype(np.float32)
        pad = 16
        out = np.zeros((h, w + 2 * pad, 4), np.uint8)
        xs = np.arange(w)
        for y in range(0, h, 2):
            o = int(round(off[y]))
            out[y:y + 2, pad + o:pad + o + w] = arr[y:y + 2]
        shade = 1 + 0.10 * k * np.cos(t * 9.0 + ph - yy * 5.0) * yy
        out[..., :3] = np.clip(out[..., :3] * shade[:, None, None], 0, 255).astype(np.uint8)
        return Image.fromarray(out, 'RGBA')

    def _duel(self, fr, t):
        L, u, D = self.L, self.u, self.drop
        x0, y0, z = self._cam(t)
        self._tumble(fr, t, self.TD + 0.2 * u, 1.6, 1245, 0.72, rev=True)    # за плакатами и табличками
        # плакаты дуэли рисуются тут (во время перехода — обычным путём в frame)
        if t >= self.TD + 0.25 * u:
            for s, sx in (('h', W), ('a', 2 * W)):
                im = self._flap(s, t, z)
                cx, cy = (MX + sx + W / 2 - x0) * z, (VY + PCY - y0) * z
                rot = (-3.5 if s == 'h' else 3.5)
                C.put(fr, C.scale(L['shadow'], z), cx + 5, cy + 10, 0.8)
                C.put(fr, _rotate(im, rot), cx, cy)
        p = C.seg(t, self.TD, self.TD + 0.3)
        # часы
        if p > 0:
            k = C.out_back(p, 1.3)
            cy = C.lerp(-200, 412, k)
            C.put(fr, L['clock'], 540, cy)
            tick = math.floor((t - self.TD) / (0.5 * u) + 1e-6)          # 0..3 → 56..59 с
            sec = 56 + min(3, max(0, tick))
            ts = self.TD + tick * 0.5 * u
            ov = 4 * math.exp(-(t - ts) * 18) * math.sin((t - ts) * 50)  # щелчок стрелки
            a_s = sec * 6 + ov
            a_m = 59 * 6 + sec * 0.1
            a_h = 359.5
            C.put(fr, L['hand_h'].rotate(-a_h, Image.BICUBIC), 540, cy)
            C.put(fr, L['hand_m'].rotate(-a_m, Image.BICUBIC), 540, cy)
            C.put(fr, L['hand_s'].rotate(-a_s, Image.BICUBIC), 540, cy)
            C.put(fr, C.ellipse(16, 16, BRASS), 540, cy)
        # П1 / П2 под плакатами
        for k_, s in enumerate(('h', 'a')):
            pl = L['duel_pl'].get(s)
            if pl is None:
                continue
            q = C.seg(t, self.TD + 0.25 * u + k_ * 0.1, self.TD + 0.25 * u + k_ * 0.1 + 0.3)
            if q <= 0:
                continue
            C.put(fr, pl, 270 + 540 * k_, C.lerp(1700, 1262, C.out_back(q, 1.3)))

    def _pick(self, fr, t):
        L, u, D = self.L, self.u, self.drop
        P = L['pick']
        tc = self.TC
        fall = C.seg(t, tc, tc + 0.45)
        p = C.seg(t, D, D + 0.14)
        sc = C.lerp(1.10, 1.0, C.out_cubic(p))
        cy = PCY + C.in_cubic(fall) * 1500
        rot = -9 * C.in_cubic(fall)
        if fall < 1:
            im = P['base']
            if P['coef'] is not None:
                # пульс кэфа на доли
                pulse = 0.0
                for n in range(1, int(self.hold) + 1):
                    pulse = max(pulse, math.exp(-max(0, t - self.b(n)) * 7) * (t >= self.b(n)))
                im = im.copy()
                C.put(im, C.scale(P['coef'], 1 + 0.07 * pulse), PW / 2, 1036)
            if abs(sc - 1) > 0.002:
                im = im.resize((int(PW * sc), int(PH * sc)), Image.BILINEAR)
            if abs(rot) > 0.05:
                im = _rotate(im, rot)
            C.put(fr, L['shadow'], 546, cy + 16, 0.9 * (1 - fall))
            C.put(fr, im, 540, cy)
        # клочья второго плаката
        q = C.seg(t, D, D + 0.75)
        if 0 < q < 1:
            d = ImageDraw.Draw(fr)
            ox = 540 + (-1 if self.side == 'h' else 1) * 470
            for vx, vy, w_, h_, rv, tone in self.scraps:
                tt = q * 0.75
                x = ox + vx * 900 * tt
                y = PCY + vy * 700 * tt + 1600 * tt * tt
                a = math.radians(rv * tt)
                ca, sa = math.cos(a), math.sin(a)
                pts = [(x + ca * px - sa * py, y + sa * px + ca * py) for px, py in
                       ((-w_ / 2, -h_ / 2), (w_ / 2, -h_ / 2), (w_ / 2, h_ / 2), (-w_ / 2, h_ / 2))]
                col = tuple(int(c * tone) for c in PAPER) + (255,)
                d.polygon(pts, fill=col)
        # звезда шерифа
        sp = C.seg(t, D, D + 0.16)
        if fall < 1:
            k = C.out_back(sp, 1.2)
            s_sc = C.lerp(2.6, 1.0, k)
            star = L['star']
            glint = 0.0
            for n in range(1, int(self.hold) + 1):
                if self.b(n) <= t < self.b(n) + 0.35:
                    glint = (t - self.b(n)) / 0.35
            im = _rotate(C.scale(star, s_sc), -12 + 10 * (1 - k))
            sx = 540 + (PW / 2 - 150) - 6
            sy = PCY - PH / 2 + 330 + C.in_cubic(fall) * 1500
            C.put(fr, im, sx, sy, min(1, sp * 5))
            if glint:
                C.put(fr, C.radial(220, 220, (255, 246, 210), int(220 * math.sin(glint * math.pi)), 2.2),
                      sx - 60 + 120 * glint, sy - 40 + 80 * glint)
        # финал: прогноз коротко и плашка Telegram
        if t >= tc:
            S = L['cta']
            q = C.seg(t, tc + 0.15, tc + 0.55)
            k = C.out_back(q, 1.2)
            C.put(fr, L['star_big'], 540, C.lerp(-260, 590, k))
            C.put(fr, S['p1'], 540, 910, C.seg(t, tc + 0.3, tc + 0.55))
            C.put(fr, S['p2'], 540, 1002, C.seg(t, tc + 0.4, tc + 0.65))
            C.put(fr, S['tg'], 540, C.lerp(1800, 1262, C.out_back(C.seg(t, tc + 0.35, tc + 0.75), 1.1)))

    def _post(self, fr, t):
        L, D = self.L, self.drop
        arr = np.asarray(fr.convert('RGB'), np.uint16)
        arr = (arr * L['vig']) >> 8
        out = arr.astype(np.int16)
        bk = 0.85 + 0.15 * math.sin(t * 0.7)
        out += (L['beams'] * bk).astype(np.int16)
        g = L['grain'][int(t * 24) % len(L['grain'])]
        out += np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None]
        fl = 0.0
        if D <= t < D + 0.3:
            fl = (1 - (t - D) / 0.3) ** 2
        if fl > 0:
            out += (np.array([255, 236, 200], np.float32) * fl * 0.9).astype(np.int16)
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')

