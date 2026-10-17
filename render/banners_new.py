# -*- coding: utf-8 -*-
"""Новые баннеры (11.10) — подачи, которых ещё не было ни в STYLES.md, ни в роликах reels.

4К, как рабочие шаблоны: альбом 3840×1920, портрет 3240×4050.
    stamp(m, path)     — «Почтовая марка» (после матча): конверт авиапочты в цветах клубов, гравированная марка
                         с номиналом-кэфом, почтовый штемпель «ЗАШЁЛ» / «НЕ ЗАШЁЛ», счёт и прогноз на конверте
    afisha(m, path)    — «Афиша» (до матча): типографский плакат в две краски, растровые эмблемы, сгибы бумаги
    diary(day, path)   — «Дневник» (итоги дня по прогнозам): школьный дневник, матчи и прогнозы от руки,
                         отметки «5» / «2» красной ручкой, замечание учителя — итог дня
    teletext(day, path)— «Телетекст» (прогнозы на ночь списком): страница 302, двойная высота, фастекст-кнопки, ЭЛТ
    neon(m, path)      — «Неон» (до матча): кирпичная стена ночью, неоновые эмблемы, прогноз и кэф трубками
    comic(m, path)     — «Комикс» (после матча): страница поп-арт, точки Бен-Дэй, «ЗАШЁЛ!» во взрыве
    blueprint(m, path) — «Чертёж» (до матча): синька, площадка в линиях, размерные линии, штамп чертежа с прогнозом
    swiss(m, path)     — «Швейцарский плакат» (до матча): сетка, огромные геометрия и цифры
    vinyl(m, path)     — «Пластинка» (до матча): конверт альбома и пластинка, на яблоке — прогноз и кэф

m — dict(home, away, league='NHL'|'KHL', day='СБ 10.10', date_long='суббота, 10 октября', time='20:00',
         pick='ПОБЕДА БОСТОНА', odds=2.21 | None, sh, sa, mark=''|'ОТ'|'Б', hit=True|False|None).
Пример запуска — make_banners_new_1110.py.
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reels import core as C  # noqa: E402  (шрифты, текст, эмблемы и цвета клубов)

C.FONTS.update(yeseva='YesevaOne-Regular.ttf', podkova='Podkova[wght].ttf', kelly='KellySlab-Regular.ttf',
               lobster='Lobster-Regular.ttf', comfortaa='Comfortaa[wght].ttf', pangolin='Pangolin-Regular.ttf',
               alumni='AlumniSans[wght].ttf', crisis='ClimateCrisis[YEAR].ttf', bad='BadScript-Regular.ttf')

LW, LH = 3840, 1920
PW, PH = 3240, 4050
HANDLE = '@jarvibet'


# ─────────────────────────────── общие помощники ───────────────────────────────
def T(s, f, size, fill=(0, 0, 0), wght=700, **kw):
    return C.text(s, f, size, tuple(fill), wght, **kw)


def tag(m):
    return 'JARVIS | NHL' if lg(m) == 'NHL' else 'JARVIS | KXL'


def lg(m):
    return 'NHL' if str(m.get('league', 'NHL')).upper() == 'NHL' else 'KHL'


def lg_ru(m):
    return 'НХЛ' if lg(m) == 'NHL' else 'КХЛ'


def teams(m):
    return C.match(m['home'], m['away'], lg(m))


def fk(k):
    return '%.2f' % k if k is not None else ''


def pick_sentence(m, text=None):
    """Прогноз обычным предложением: «Победа Анахайма с учётом ОТ» (названия клубов — с заглавной)."""
    stems = [w.lower()[:4] for t in teams(m) for w in t.short.replace('-', ' ').split() if len(w) >= 2]
    out = []
    for w in (text or m['pick']).lower().split():
        if any(w.replace('-', ' ').startswith(st) for st in stems):
            w = '-'.join(x.capitalize() for x in w.split('-'))
        elif w.strip('(),.') == 'от':
            w = w.upper()
        out.append(w)
    s = ' '.join(out)
    return s[:1].upper() + s[1:]


def score(m):
    return '%d:%d' % (m['sh'], m['sa'])


def goals(n):
    w = 'ГОЛ' if n % 10 == 1 and n % 100 != 11 else 'ГОЛА' if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else 'ГОЛОВ'
    return '%d %s' % (n, w)


def mark_ru(mark):
    return {'ОТ': 'ОВЕРТАЙМ', 'Б': 'БУЛЛИТЫ', 'ОТ/Б': 'ОВЕРТАЙМ'}.get(mark or '', '')


def dark(c, k):
    return tuple(int(v * (1 - k)) for v in c)


def light(c, k):
    return tuple(int(v + (255 - v) * k) for v in c)


def lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def sat(c):
    return (max(c) - min(c)) / 255


def club(t):
    """Клубный цвет команды: первый «цветной» из c1 / c0 / c2 (не серый, не чёрный, не белый)."""
    for c in (t.c1, t.c0, t.c2):
        if sat(c) > 0.2 and 40 < lum(c) < 235:
            return c
    return t.c1 if lum(t.c1) < 235 else t.c0


def noise(w, h, scale, seed):
    """Плавный шум 0..1 с размером пятна ~scale px."""
    rnd = np.random.default_rng(seed)
    n = rnd.random((max(2, int(h / scale) + 2), max(2, int(w / scale) + 2))).astype(np.float32)
    im = Image.fromarray((n * 255).astype(np.uint8), 'L').resize((w, h), Image.BICUBIC)
    return np.asarray(im, np.float32) / 255


def paper(w, h, base, seed=1, k=1.0, fibers=900):
    """Бумага: крупные пятна, мелкое зерно и волокна."""
    v = (noise(w, h, 420, seed) - 0.5) * 24 + (noise(w, h, 70, seed + 1) - 0.5) * 10
    v += np.random.default_rng(seed + 2).normal(0, 3.2, (h, w)).astype(np.float32)
    arr = np.array(base, np.float32)[None, None, :] + (v * k)[..., None]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    if fibers:
        rnd = random.Random(seed)
        lay = Image.new('L', (w, h), 0)
        d = ImageDraw.Draw(lay)
        for _ in range(fibers):
            x, y = rnd.uniform(0, w), rnd.uniform(0, h)
            a, ln = rnd.uniform(0, math.pi), rnd.uniform(20, 90)
            pts = [(x + math.cos(a + 0.3 * math.sin(i)) * ln * i / 6, y + math.sin(a + 0.3 * math.sin(i)) * ln * i / 6)
                   for i in range(7)]
            d.line(pts, fill=rnd.randint(20, 60), width=2)
        lay = lay.filter(ImageFilter.GaussianBlur(1))
        dk = Image.new('RGBA', (w, h), tuple(dark(base, 0.35)) + (0,))
        dk.putalpha(lay)
        im.alpha_composite(dk)
    return im


def vignette(im, k=0.35, power=2.0, col=(0, 0, 0)):
    w, h = im.size
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) / math.sqrt(2)
    a = (np.clip(d, 0, 1) ** power * k * 255).astype(np.uint8)
    lay = Image.new('RGBA', (w, h), tuple(col) + (0,))
    lay.putalpha(Image.fromarray(a, 'L'))
    out = im.convert('RGBA')
    out.alpha_composite(lay)
    return out


def tone_of(im, floor=0.0, gamma=1.0):
    """Сколько краски нужно под эмблему: тёмное — больше; floor — минимальная заливка силуэта."""
    a = np.asarray(im.getchannel('A'), np.float32) / 255
    rgb = np.asarray(im.convert('RGB'), np.float32) / 255
    l_ = rgb @ np.array([0.3, 0.59, 0.11], np.float32)
    return a * (floor + (1 - floor) * (1 - l_) ** gamma)


def _blur_arr(a, r):
    if r < 0.5:
        return a
    im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32) / 255


def layer(cov, ink):
    """Покрытие 0..1 → RGBA слой краски ink."""
    h, w = cov.shape
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., :3] = ink[:3]
    arr[..., 3] = np.clip(cov * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, 'RGBA')


def halftone(tone, cell, ink, angle=45, aa=1.4):
    """Растр: точки на сетке под углом, размер точки — по тону."""
    h, w = tone.shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    u, v = (x * ca + y * sa) / cell, (-x * sa + y * ca) / cell
    du, dv = u - np.floor(u) - 0.5, v - np.floor(v) - 0.5
    d = np.sqrt(du * du + dv * dv) * cell
    r = np.sqrt(_blur_arr(tone, cell * 0.35)) * cell * 0.74
    return layer(np.clip((r - d) / aa + 0.5, 0, 1) * (r > 0.6), ink)


def engrave(tone, period, ink, angle=0.0, amp=0.0, wl=300.0, minw=0.0, aa=1.2):
    """Гравюра: параллельные линии, толщина — по тону (как на марках и банкнотах)."""
    h, w = tone.shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    p = -x * sa + y * ca + amp * np.sin((x * ca + y * sa) / wl * 2 * math.pi)
    dist = np.abs((p / period) % 1 - 0.5) * period
    t = _blur_arr(tone, period * 0.3)
    half = (np.where(t > 0.02, minw, 0) + t * (1 - minw)) * period * 0.5
    return layer(np.clip((half - dist) / aa + 0.5, 0, 1), ink)


def wear(im, seed, k=0.3, speck=0.04):
    """Стёртая краска: пятна и проплешины на непрозрачных пикселях."""
    w, h = im.size
    n = noise(w, h, 5, seed) * 0.5 + noise(w, h, 45, seed + 1) * 0.5
    m = np.clip(1 - k * np.clip((n - 0.35) * 3, 0, 1), 0, 1)
    rnd = np.random.default_rng(seed + 2)
    m = m * np.where(rnd.random((h, w)) < speck, 0.25, 1.0)
    a = np.asarray(im.getchannel('A'), np.float32) * m
    out = im.copy()
    out.putalpha(Image.fromarray(a.astype(np.uint8), 'L'))
    return out


def pad(im, p):
    out = Image.new('RGBA', (im.width + 2 * p, im.height + 2 * p), (0, 0, 0, 0))
    out.alpha_composite(im, (p, p))
    return out


def contour(im, width, thr=90):
    """Внешний контур силуэта эмблемы шириной width (маска L, картинка с полями)."""
    p = width * 2 + 4
    a = pad(im, p).getchannel('A').point(lambda v: 255 if v > thr else 0)
    a = a.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))    # убрать дырочки
    big = a.filter(ImageFilter.MaxFilter(2 * (width // 2) + 1))
    return ImageChops.subtract(big, a)


def star(r, n=5, k=0.45, rot=-90):
    pts = []
    for i in range(2 * n):
        rr = r if i % 2 == 0 else r * k
        a = math.radians(rot + i * 180 / n)
        pts.append((r + rr * math.cos(a), r + rr * math.sin(a)))
    return pts


def burst(rx, ry, n=14, k=0.72, seed=3, jit=0.12):
    rnd = random.Random(seed)
    pts = []
    for i in range(2 * n):
        f = 1.0 if i % 2 == 0 else k
        f *= 1 + rnd.uniform(-jit, jit)
        a = 2 * math.pi * i / (2 * n)
        pts.append((rx + rx * f * math.cos(a), ry + ry * f * math.sin(a)))
    return pts


def curved(s, f, size, r, fill, wght=700, start=-90.0, track=0.0):
    """Текст по окружности радиуса r (по часовой, начиная с угла start). → квадрат 2r+pad."""
    S = int(2 * r + size * 3)
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ft = C.font(f, size, wght)
    ws = [ft.getlength(c) + track * size for c in s]
    ang = math.radians(start)
    for c, w in zip(s, ws):
        a = ang + w / 2 / r
        g = T(c, f, size, fill, wght, trim=False) if c.strip() else None
        if g is not None:
            g = g.rotate(-math.degrees(a) - 90, Image.BICUBIC, expand=True)
            C.put(out, g, S / 2 + r * math.cos(a), S / 2 + r * math.sin(a))
        ang += w / r
    return out


def save(im, path, q=93):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    im.convert('RGB').save(path, quality=q, subsampling=0)
    return path


# ─────────────────────────────── 1. Почтовая марка ───────────────────────────────
def _perforate(im, r, step):
    """Зубцы марки: вырезать полукруги по краям."""
    w, h = im.size
    m = Image.new('L', (w * 2, h * 2), 255)
    d = ImageDraw.Draw(m)
    for x in np.arange(step / 2, w, step):
        for y in (0, h):
            d.ellipse(((x - r) * 2, (y - r) * 2, (x + r) * 2, (y + r) * 2), fill=0)
    for y in np.arange(step / 2, h, step):
        for x in (0, w):
            d.ellipse(((x - r) * 2, (y - r) * 2, (x + r) * 2, (y + r) * 2), fill=0)
    m = m.resize((w, h), Image.LANCZOS)
    out = im.copy()
    out.putalpha(ImageChops.multiply(im.getchannel('A'), m))
    return out


def _rosette(w, h, ink, a=0.32, n=34, seed=5):
    """Гильош: розетка из синусоидальных колец, как фон на марках."""
    lay = Image.new('RGBA', (w * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx, cy = w, h
    for k in range(n):
        r0 = (0.18 + 0.82 * k / n) * min(w, h) * 1.25
        pts = []
        for i in range(721):
            t = 2 * math.pi * i / 720
            r = r0 + 0.035 * r0 * math.sin(18 * t + k * 0.5) + 0.02 * r0 * math.sin(7 * t)
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
        d.line(pts, fill=tuple(ink[:3]) + (int(255 * a),), width=3)
    return lay.resize((w, h), Image.LANCZOS)


def stamp(m, path):
    """«Почтовая марка» — баннер после матча (альбом)."""
    h, a = teams(m)
    W, H = LW, LH
    base = (224, 199, 156)
    im = paper(W, H, base, seed=11, k=1.0, fibers=1600)
    # кайма авиапочты — полосы цветов клубов
    yy, xx = np.mgrid[0:H, 0:W]
    L = 120
    ph = ((xx + yy) % (3 * L))
    band = 92
    edge = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy)) < band
    c1, c2 = club(h), club(a)
    for i, col in ((0, c1), (2, c2)):
        cov = ((ph >= i * L) & (ph < (i + 1) * L) & edge).astype(np.float32)
        im.alpha_composite(wear(layer(cov, col), 21 + i, k=0.35, speck=0.02))
    d = ImageDraw.Draw(im)
    brown = (58, 42, 30)
    # обратный адрес
    x0 = 250
    for i, s in enumerate(('ОТ: ' + tag(m), 'ИТОГ МАТЧА · ' + m['day'])):
        C.put(im, T(s, 'mono', 62, brown, 600, track=0.04), x0, 215 + i * 92, anchor='tl')
    # матч и счёт
    names = '%s — %s' % (h.up, a.up)
    C.put(im, T(names, 'podkova', 150, brown, 800, max_w=1560), x0, 600, anchor='tl')
    sc = T('%d : %d' % (m['sh'], m['sa']), 'yeseva', 560, (40, 28, 22), 400)
    C.put(im, sc, x0 - 10, 790, anchor='tl')
    sub = goals(m['sh'] + m['sa']) + ' В МАТЧЕ' + (' · ' + mark_ru(m.get('mark')) if m.get('mark') else '')
    C.put(im, T(sub, 'podkova', 92, brown, 700, track=0.06), x0, 790 + sc.height + 70, anchor='tl')
    # строки адреса — прогноз от руки
    blue = (28, 46, 120)
    res = 'прогноз зашёл' if m.get('hit') else 'прогноз не зашёл'
    for i, (lab, val) in enumerate((('Кому:', 'подписчикам ' + HANDLE), ('Итог:', res))):
        y = 1545 + i * 160
        d.line((x0, y + 20, 2050, y + 20), fill=dark(base, 0.45), width=5)
        C.put(im, T(lab, 'podkova', 64, brown, 600), x0, y - 60, anchor='tl')
        hw = T(val, 'hand', 128, blue, 600, max_w=1500)
        C.put(im, hw, x0 + 330, y + 12 - hw.height, anchor='tl')
    # марка
    ink = dark(club(a if m['sa'] > m['sh'] else h), 0.35)
    if lum(ink) > 110:
        ink = dark(ink, 0.4)
    SW, SH = 1060, 1300
    st = Image.new('RGBA', (SW, SH), (251, 248, 240, 255))
    st.alpha_composite(paper(SW, SH, (251, 248, 240), seed=3, k=0.35, fibers=80))
    sd = ImageDraw.Draw(st)
    m0 = 62
    sd.rectangle((m0, m0, SW - m0, SH - m0), outline=ink, width=10)
    sd.rectangle((m0 + 22, m0 + 22, SW - m0 - 22, SH - m0 - 22), outline=ink, width=3)
    top = (m0 + 22, m0 + 22, SW - m0 - 22, m0 + 190)
    sd.rectangle(top, fill=ink)
    C.put(st, T('ПОЧТА JARVIS', 'podkova', 88, (251, 248, 240), 800, track=0.12), SW / 2, (top[1] + top[3]) / 2)
    ix0, iy0, ix1, iy1 = m0 + 22, top[3], SW - m0 - 22, 880
    st.alpha_composite(_rosette(ix1 - ix0, iy1 - iy0, ink), (ix0, iy0))
    for t_, cx in ((h, SW / 2 - 205), (a, SW / 2 + 205)):
        e = t_.emb(380)
        g = engrave(tone_of(e, floor=0.18, gamma=0.9), 9, ink, angle=-30, amp=2, wl=160, minw=0.12)
        bg = Image.new('RGBA', g.size, (251, 248, 240, 0))
        bg.putalpha(e.getchannel('A').point(lambda v: int(v * 0.92)))
        C.put(st, bg, cx, (iy0 + iy1) / 2 + 10)
        C.put(st, g, cx, (iy0 + iy1) / 2 + 10)
    sd.line((ix0, iy1, ix1, iy1), fill=ink, width=4)
    pk = C.lines(m['pick'], 'podkova', 70, 520, ink, 800, gap=0.1, align='l', max_lines=3)
    C.put(st, pk, ix0 + 40, (iy1 + SH - m0 - 22) / 2 - pk.height / 2, anchor='tl')
    if m.get('odds'):
        C.put(st, T('КЭФ', 'podkova', 56, ink, 700, track=0.2), ix1 - 200, iy1 + 85)
        C.put(st, T(fk(m['odds']), 'yeseva', 190, ink, 400), ix1 - 200, iy1 + 240)
    C.put(st, T('%s · 2026' % lg_ru(m), 'mono', 40, ink, 600, track=0.2), ix0 + 30, iy1 - 75, anchor='tl')
    st = wear(st, 7, k=0.12, speck=0.01)
    st = _perforate(st, 22, 64)
    st = st.rotate(4, Image.BICUBIC, expand=True)
    sx, sy = 2930, 990
    C.put(im, C.shadow(st, 26, 0.45), sx + 10, sy + 26)
    C.put(im, st, sx, sy)
    # штемпель
    hit = m.get('hit')
    pink = (26, 26, 34) if hit else (178, 30, 36)
    R = 330
    pm = Image.new('RGBA', (2 * R + 1400, 2 * R + 80), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pm)
    cx, cy = R + 40, R + 40
    pd.ellipse((cx - R, cy - R, cx + R, cy + R), outline=pink, width=16)
    pd.ellipse((cx - R + 92, cy - R + 92, cx + R - 92, cy + R - 92), outline=pink, width=9)
    ring = curved('%s — %s · %s ·' % (h.up, a.up, score(m)), 'podkova', 50, R - 50, pink, 800, start=-90, track=0.06)
    C.put(pm, ring, cx, cy)
    word = 'ЗАШЁЛ' if hit else 'НЕ ЗАШЁЛ'
    C.put(pm, T(word, 'podkova', 92 if hit else 66, pink, 800, max_w=400), cx, cy - 40)
    pd.line((cx - 190, cy + 30, cx + 190, cy + 30), fill=pink, width=7)
    C.put(pm, T(m['day'].split()[-1] + '.26', 'mono', 60, pink, 700), cx, cy + 95)
    for i in range(5):                                       # волнистые линии гашения
        yy0 = cy - 150 + i * 75
        pts = [(cx + R + 40 + x, yy0 + 22 * math.sin(x / 130 * math.pi)) for x in range(0, 1300, 8)]
        pd.line(pts, fill=pink, width=13)
    pm = wear(pm, 33, k=0.55, speck=0.05).rotate(-7, Image.BICUBIC, expand=True)
    C.put(im, pm, 2170 + pm.width / 2 - (R + 40), 560)
    return save(vignette(im, 0.28), path)


# ─────────────────────────────── 2. Афиша ───────────────────────────────
def _fold(im, x=None, y=None, k=1.0):
    """Сгиб бумаги: светлая грань и тень рядом."""
    w, h = im.size
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    if x is not None:
        d.rectangle((x - 26, 0, x, h), fill=(60, 40, 20, int(34 * k)))
        d.rectangle((x, 0, x + 26, h), fill=(255, 250, 235, int(40 * k)))
        d.line((x, 0, x, h), fill=(80, 60, 40, int(60 * k)), width=3)
    if y is not None:
        d.rectangle((0, y - 26, w, y), fill=(60, 40, 20, int(34 * k)))
        d.rectangle((0, y, w, y + 26), fill=(255, 250, 235, int(40 * k)))
        d.line((0, y, w, y), fill=(80, 60, 40, int(60 * k)), width=3)
    lay = lay.filter(ImageFilter.GaussianBlur(9))
    im.alpha_composite(lay)


def afisha(m, path):
    """«Афиша» — типографский плакат в две краски (портрет), до матча."""
    h, a = teams(m)
    W, H = PW, PH
    base = (238, 227, 202)
    im = paper(W, H, base, seed=41, k=1.15, fibers=2600)
    red, blk = (184, 38, 34), (32, 30, 34)
    R = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    K = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dK, dR = ImageDraw.Draw(K), ImageDraw.Draw(R)
    M = 170
    dK.rectangle((M, 150, W - M, 166), fill=blk)
    dK.rectangle((M, 186, W - M, 192), fill=blk)
    C.put(K, T(tag(m) + ' · ПРЕДСТАВЛЯЕТ', 'alumni', 128, blk, 800, track=0.22, max_w=W - 2 * M), W / 2, 300)
    dt = T(m['date_long'].upper(), 'podkova', 140, blk, 800, max_w=W - 2 * M - 400)
    C.put(K, dt, W / 2, 470)
    for sx in (-1, 1):
        st = C.polygon(star(46), (92, 92), red)
        C.put(R, st, W / 2 + sx * (dt.width / 2 + 110), 470)
    C.put(R, T('БОЛЬШОЙ ХОККЕЙ', 'yeseva', 340, red, 400, max_w=W - 2 * M), W / 2, 730)
    dK.rectangle((M, 930, W - M, 936), fill=blk)
    C.put(K, T('ЧЕМПИОНАТ %s · РЕГУЛЯРНЫЙ СЕЗОН' % lg_ru(m), 'alumni', 96, blk, 700, track=0.2, max_w=W - 2 * M),
          W / 2, 1000)
    dK.rectangle((M, 1066, W - M, 1072), fill=blk)
    # эмблемы — растр в медальонах
    cy = 1700
    for t_, cx in ((h, W / 2 - 830), (a, W / 2 + 830)):
        rr = 510
        dR.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=red, width=26)
        dR.ellipse((cx - rr + 48, cy - rr + 48, cx + rr - 48, cy + rr - 48), outline=red, width=8)
        e = t_.emb(780)
        C.put(K, halftone(tone_of(e, floor=0.22, gamma=0.8), 24, blk, angle=45), cx, cy)
        C.put(K, T(t_.up, 'alumni', 250, blk, 900, max_w=1300), cx, cy + rr + 190)
    C.put(R, T('против', 'playi', 150, red, 400), W / 2, cy - 20)
    # прогноз — плашка красной краской, текст «выворотка»
    y0, y1 = 2600, 3330
    dR.rectangle((M, y0, W - M, y1), fill=red)
    xc = (M + W - M - 560) / 2 + 40                          # правее — печать кэфа
    C.put(R, T('НАШ ПРОГНОЗ', 'alumni', 130, base, 800, track=0.3), xc, y0 + 130)
    pk = C.lines(m['pick'], 'yeseva', 250, W - 2 * M - 760, base, 400, gap=0.05, max_lines=2)
    pk = C.fit(pk, W - 2 * M - 760, y1 - y0 - 300) if pk.height > y1 - y0 - 300 else pk
    C.put(R, pk, xc, (y0 + 230 + y1) / 2)
    # кэф — круглая печать
    if m.get('odds'):
        sd_ = 660
        seal = Image.new('RGBA', (sd_, sd_), (0, 0, 0, 0))
        sdd = ImageDraw.Draw(seal)
        sdd.ellipse((0, 0, sd_ - 1, sd_ - 1), fill=blk)
        sdd.ellipse((34, 34, sd_ - 35, sd_ - 35), outline=base, width=7)
        C.put(seal, T('КЭФ', 'alumni', 110, base, 800, track=0.3), sd_ / 2, sd_ / 2 - 150)
        C.put(seal, T(fk(m['odds']), 'yeseva', 200, base, 400), sd_ / 2, sd_ / 2 + 50)
        C.put(seal, C.polygon(star(26), (52, 52), base), sd_ / 2, sd_ / 2 + 210)
        C.put(K, seal.rotate(-12, Image.BICUBIC, expand=True), W - M - 290, y1 + 40)
    C.put(K, T('НАЧАЛО В %s ПО МОСКВЕ' % m['time'], 'podkova', 130, blk, 800, max_w=2150), M, 3420, anchor='tl')
    C.put(K, T('ПОДРОБНЫЙ РАЗБОР — В TELEGRAM', 'alumni', 112, red, 700, track=0.12, max_w=2150), M, 3610, anchor='tl')
    dK.rectangle((M, 3790, W - M, 3796), fill=blk)
    dK.rectangle((M, 3812, W - M, 3828), fill=blk)
    C.put(K, T('ПРОГНОЗЫ НА ХОККЕЙ · ' + HANDLE, 'alumni', 100, blk, 800, track=0.25), W / 2, 3910)
    R = wear(R, 51, k=0.32, speck=0.03)
    K = wear(K, 52, k=0.2, speck=0.02)
    im.alpha_composite(R, (7, -5))                          # приводка краски чуть съехала
    im.alpha_composite(K)
    _fold(im, x=W // 2)
    _fold(im, y=H // 2, k=0.8)
    return save(vignette(im, 0.42, 2.4, (96, 66, 30)), path)


# ─────────────────────────────── 3. Дневник ───────────────────────────────
def wood(w, h, seed=61, base=(98, 66, 44)):
    rnd = np.random.default_rng(seed)
    g = rnd.random((max(2, h // 7), max(2, w // 420))).astype(np.float32)
    g = np.asarray(Image.fromarray((g * 255).astype(np.uint8), 'L').resize((w, h), Image.BICUBIC), np.float32) / 255
    ring = np.sin((np.arange(h)[:, None] / 9.0) + g * 9.0) * 0.5 + 0.5
    v = (g - 0.5) * 34 + (ring - 0.5) * 14 + rnd.normal(0, 3, (h, w))
    arr = np.array(base, np.float32)[None, None, :] + v[..., None] * np.array([1.0, 0.8, 0.6], np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')


def squiggle(w, h, col, seed, width=6):
    """Подпись учителя — росчерк."""
    rnd = random.Random(seed)
    S = 2
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = rnd.choice((2, 3))                                   # петли, как в беглой подписи
    r = h * 0.3 * S
    pts = []
    for i in range(160):
        t = i / 159
        x = (0.08 + 0.7 * t) * w * S + r * 0.8 * math.sin(2 * math.pi * k * t)
        y = h * 0.62 * S - r * math.cos(2 * math.pi * k * t) * (1 - 0.3 * t) - t * h * 0.15 * S
        pts.append((x, y))
    d.line(pts, fill=tuple(col) + (255,), width=width * S, joint='curve')
    x1, y1 = pts[-1]
    d.line([(x1 + (w * S * 0.95 - x1) * j / 20, y1 + math.sin(j / 20 * math.pi) * h * 0.12 * S) for j in range(21)],
           fill=tuple(col) + (255,), width=width * S, joint='curve')
    return im.resize((w, h), Image.LANCZOS)


def _hand(s, f, size, col, max_w, seed, lines_=1):
    rnd = random.Random(seed)
    if lines_ > 1:
        im = C.lines(s, f, size, max_w, col, 400, gap=0.0, align='l', max_lines=lines_)
    else:
        im = T(s, f, size, col, 400, max_w=max_w)
    return im.rotate(rnd.uniform(-1.2, 1.2), Image.BICUBIC, expand=True)


def diary(day, path):
    """«Дневник» — итоги дня по прогнозам (альбом): KHL на левой странице, NHL на правой."""
    W, H = LW, LH
    im = wood(W, H)
    im = vignette(im, 0.5, 1.8)
    bx0, by0, bx1, by1 = 110, 80, 3730, 1840
    PWd, PHd = (bx1 - bx0 - 20) // 2, by1 - by0
    # тень книги и срезы страниц
    blk = Image.new('RGBA', (bx1 - bx0 + 40, PHd + 40), (0, 0, 0, 255))
    C.put(im, C.shadow(blk, 40, 0.6), (bx0 + bx1) / 2 + 20, (by0 + by1) / 2 + 40)
    d = ImageDraw.Draw(im)
    for k in range(6, 0, -1):
        d.rectangle((bx0 - k * 5, by0 + k * 3, bx1 + k * 5, by1 + k * 4), fill=(226 - k * 9, 220 - k * 9, 204 - k * 9))
    blue_ink, red_ink = (28, 46, 132), (196, 28, 36)
    print_c, rule = (52, 62, 92), (150, 172, 205)
    units = 0.0
    hits = total = 0
    for side, items, title, tg_ in (('l', day['khl'], day['khl_title'], 'JARVIS | KXL'),
                                    ('r', day['nhl'], day['nhl_title'], 'JARVIS | NHL')):
        pg = paper(PWd, PHd, (250, 247, 236), seed=71 if side == 'l' else 72, k=0.45, fibers=300)
        pd = ImageDraw.Draw(pg)
        x0 = 90
        iw = PWd - 2 * x0
        C.put(pg, T('ДНЕВНИК ПРОГНОЗОВ' if side == 'l' else 'ПРОГНОЗЫ И ОТМЕТКИ', 'prata', 78, print_c, 400),
              x0, 70, anchor='tl')
        tg = T(tg_, 'mono', 44, print_c, 700, track=0.08)
        C.put(pg, tg, PWd - x0 - tg.width, 92, anchor='tl')
        pd.line((x0, 196, PWd - x0, 196), fill=print_c, width=4)
        C.put(pg, T('ДЕНЬ', 'golos', 36, print_c, 700, track=0.2), x0, 248, anchor='tl')
        C.put(pg, _hand(title, 'bad', 82, blue_ink, iw - 220, 3 if side == 'l' else 4), x0 + 160, 222, anchor='tl')
        pd.line((x0 + 150, 312, PWd - x0, 312), fill=rule, width=3)
        cols = [('МАТЧ', 600), ('ПРОГНОЗ · КЭФ', 640), ('СЧЁТ', 200), ('ОЦЕНКА', iw - 1440)]
        ty = 350
        pd.line((x0, ty, PWd - x0, ty), fill=print_c, width=4)
        xx = x0
        for lab, cw in cols:
            C.put(pg, T(lab, 'golos', 32, print_c, 700, track=0.1), xx + 18, ty + 22, anchor='tl')
            xx += cw
        ty2 = ty + 76
        pd.line((x0, ty2, PWd - x0, ty2), fill=print_c, width=3)
        rh = 158
        nrows = 8
        for i in range(nrows):
            yb = ty2 + (i + 1) * rh
            if side == 'l' and i >= len(items):
                break
            pd.line((x0, yb, PWd - x0, yb), fill=rule, width=3)
        yend = ty2 + (len(items) if side == 'l' else nrows) * rh
        xx = x0
        for _, cw in cols[:-1]:
            xx += cw
            pd.line((xx, ty, xx, yend), fill=rule, width=3)
        for i, it in enumerate(items):
            yc = ty2 + i * rh + rh / 2
            hh, aa = teams(it)
            sd = 100 + i * 7 + (0 if side == 'l' else 50)
            C.put(pg, _hand('%s — %s' % (hh.short, aa.short), 'bad', 62, blue_ink, 560, sd), x0 + 18, yc - 34, anchor='tl')
            pk = it['pick'].lower().replace('итоговая ', '').replace('индивидуальный тотал', 'инд. тотал')
            pk = pk.replace('тотал матча', 'тотал').replace(' с учётом от', ' (с ОТ)')
            pk = pick_sentence(it, pk)
            pk = pk[:1].lower() + pk[1:] if not pk.split()[0].lower().startswith(hh.short.lower()[:4]) else pk
            pk += ' · ' + (fk(it['odds']).replace('.', ',') if it.get('odds') else 'без кэфа')
            ph = _hand(pk, 'bad', 52, blue_ink, 600, sd + 1, lines_=2)
            C.put(pg, ph, x0 + 600 + 18, yc - ph.height / 2, anchor='tl')
            sc = score(it) + (' ' + it['mark'] if it.get('mark') else '')
            C.put(pg, _hand(sc, 'bad', 62, blue_ink, 180, sd + 2), x0 + 1240 + 100, yc)
            hit = bool(it.get('hit'))
            total += 1
            hits += hit
            units += ((it['odds'] or 1) - 1) if hit else -1
            gx = x0 + 1440 + 60
            C.put(pg, _hand('5' if hit else '2', 'hand', 150, red_ink, 200, sd + 3), gx, yc - 4)
            C.put(pg, squiggle(96, 50, red_ink, sd + 4, 4), gx + 88, yc + 26)
        if side == 'l':
            ry = yend + 70
            C.put(pg, T('ЗАМЕЧАНИЯ', 'golos', 36, print_c, 700, track=0.2), x0, ry, anchor='tl')
            for k in range(3):
                yy = ry + 150 + k * 150
                pd.line((x0, yy, PWd - x0, yy), fill=rule, width=3)
            C.put(pg, T('5 — ЗАШЁЛ · 2 — НЕ ЗАШЁЛ', 'golos', 32, print_c, 700, track=0.12), x0, PHd - 92, anchor='tl')
            hd = T(HANDLE, 'mono', 40, print_c, 700, track=0.06)
            C.put(pg, hd, PWd - x0 - hd.width, PHd - 96, anchor='tl')
            left_pg = pg
        else:
            right_pg = pg
    note1 = 'Итог дня: %d из %d' % (hits, total)
    note2 = '%+.2f ед. Так держать!' % units
    note2 = note2.replace('.', ',', 1) if '.' in note2.split()[0] else note2
    ry = ty2 + len(day['khl']) * rh + 70
    C.put(left_pg, _hand(note1, 'hand', 128, red_ink, 1300, 901), 110, ry + 150 - 118, anchor='tl')
    C.put(left_pg, _hand(note2, 'hand', 128, red_ink, 1300, 902), 110, ry + 300 - 118, anchor='tl')
    C.put(left_pg, squiggle(360, 130, red_ink, 903, 7), PWd - 360, ry + 410)
    # корешок: тень к середине
    for pg, side in ((left_pg, 'l'), (right_pg, 'r')):
        g = np.linspace(0, 1, 220, dtype=np.float32) ** 2
        a = (g * 120).astype(np.uint8)
        if side == 'r':
            a = a[::-1]
        sh = Image.new('RGBA', (220, PHd), (40, 30, 20, 0))
        sh.putalpha(Image.fromarray(np.repeat(a[None, :], PHd, 0), 'L'))
        pg.alpha_composite(sh, (PWd - 220, 0) if side == 'l' else (0, 0))
    im.alpha_composite(left_pg, (bx0, by0))
    im.alpha_composite(right_pg, (bx0 + PWd + 20, by0))
    d = ImageDraw.Draw(im)
    d.rectangle((bx0 + PWd, by0, bx0 + PWd + 20, by1), fill=(150, 138, 118))
    return save(im, path)


# ─────────────────────────────── 4. Телетекст ───────────────────────────────
TT = dict(k=(0, 0, 0), r=(240, 44, 44), g=(44, 226, 70), y=(250, 232, 44), b=(36, 60, 226), m=(226, 50, 226),
          c=(44, 226, 236), w=(244, 244, 244))


class _TTPage:
    """Страница телетекста: 64×24 знакоместа 12×16, потом ×5 «по пикселям»."""
    CW, CH, COLS, ROWS = 12, 16, 64, 24

    def __init__(self):
        self.im = Image.new('RGB', (self.CW * self.COLS, self.CH * self.ROWS), TT['k'])
        self.d = ImageDraw.Draw(self.im)
        self.d.fontmode = '1'
        self.f = C.font('mono', 14, 800)
        bb = self.f.getbbox('ЁЙ')
        self.dy = 1 - bb[1]                                  # верх заглавных с «Ё» — на 1-й строке пикселей

    def bg(self, row, c0, c1, col, rows=1):
        self.d.rectangle((c0 * self.CW, row * self.CH, c1 * self.CW - 1, (row + rows) * self.CH - 1), fill=TT[col])

    def put(self, row, col, s, fg='w', bg=None, dh=False):
        if bg:
            self.bg(row, col, col + len(s), bg, 2 if dh else 1)
        strip = Image.new('RGB', (self.CW * len(s), self.CH), TT[bg] if bg else TT['k'])
        sd = ImageDraw.Draw(strip)
        sd.fontmode = '1'
        for i, ch in enumerate(s):
            if ch != ' ':
                w = self.f.getlength(ch)
                sd.text((i * self.CW + (self.CW - w) / 2, self.dy), ch, font=self.f, fill=TT[fg])
        if dh:
            strip = strip.resize((strip.width, strip.height * 2), Image.NEAREST)
        self.im.paste(strip, (col * self.CW, row * self.CH))

    def mosaic(self, row, col, bits, fg):
        """Блочная графика: bits — 6 бит знакоместа 2×3."""
        w2, h3 = self.CW // 2, self.CH / 3
        for k in range(6):
            if bits >> k & 1:
                x, y = col * self.CW + (k % 2) * w2, row * self.CH + (k // 2) * h3
                self.d.rectangle((x, int(y), x + w2 - 1, int(y + h3) - 1), fill=TT[fg])


def teletext(day, path):
    """«Телетекст» — прогнозы на ночь одной страницей (альбом). day = dict(items, title, day, clock, league)."""
    p = _TTPage()
    items = day['items']
    p.put(0, 1, 'P302', 'w')
    p.put(0, 7, 'JARVIS ТЕКСТ', 'c')
    p.put(0, 22, day['day'], 'y')
    p.put(0, 34, 'ВРЕМЯ МСК', 'w')
    p.put(0, 55, day['clock'], 'y')
    p.bg(1, 0, 64, 'b', 2)
    p.put(1, 2, day['title'], 'y', 'b', dh=True)
    rnd = random.Random(5)
    for c in range(64):
        p.mosaic(3, c, rnd.choice((0b001111, 0b111100, 0b110011, 0b001100, 0b111111)), 'c' if c % 8 < 4 else 'b')
    row = 4
    for it in items:
        h, a = teams(it)
        p.put(row, 1, it['time'], 'g')
        p.put(row, 8, ('%s — %s' % (h.up, a.up))[:52], 'w')
        p.put(row + 1, 8, it['pick'][:44], 'y')
        k = ('КЭФ ' + fk(it['odds'])) if it.get('odds') else 'БЕЗ КЭФА'
        p.put(row + 1, 63 - len(k), k, 'c')
        row += 2
    p.put(20, 1, 'Подробный разбор каждого матча — в Telegram', 'w')
    p.put(20, 63 - len(HANDLE), HANDLE, 'c')
    for i, (lab, col) in enumerate((('ИТОГИ', 'r'), ('КХЛ', 'g'), ('НХЛ', 'y'), ('TELEGRAM', 'c'))):
        p.put(22, 1 + i * 16, lab, col)
    big = p.im.resize((LW, LH), Image.NEAREST)
    arr = np.asarray(big, np.float32)
    bloom = np.asarray(big.filter(ImageFilter.GaussianBlur(14)), np.float32)
    arr = arr * 0.92 + bloom * 0.55
    y = np.arange(LH)
    arr *= np.where(y % 5 == 4, 0.55, 1.0)[:, None, None]           # строки развёртки
    arr += np.random.default_rng(3).normal(0, 4, arr.shape[:2])[..., None]
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
    r, g, b = out.split()
    out = Image.merge('RGB', (ImageChops.offset(r, 3, 0), g, ImageChops.offset(b, -3, 0)))
    return save(vignette(out.convert('RGBA'), 0.55, 2.6), path)


# ─────────────────────────────── 5. Неон ───────────────────────────────
def bricks(w, h, seed=81):
    rnd = random.Random(seed)
    im = Image.new('RGB', (w, h), (34, 30, 30))
    d = ImageDraw.Draw(im)
    bw, bh, mt = 330, 112, 14
    for r in range(h // bh + 2):
        off = (r % 2) * bw / 2
        for c in range(-1, w // bw + 2):
            x0, y0 = c * bw + off + mt / 2, r * bh + mt / 2
            v = rnd.randint(-16, 16)
            col = (92 + v + rnd.randint(-6, 6), 46 + v // 2, 38 + v // 2)
            d.rectangle((x0, y0, x0 + bw - mt, y0 + bh - mt), fill=col)
    arr = np.asarray(im, np.float32)
    arr *= (0.75 + 0.5 * noise(w, h, 9, seed))[..., None]
    arr *= (0.85 + 0.3 * noise(w, h, 260, seed + 1))[..., None]
    return arr * 0.42


def _glowadd(acc, mask, col, halo=26, spill=150, k_spill=0.55, k_halo=1.25, core=0.65):
    """Добавить неоновую трубку (mask 0..1) в накопитель света acc."""
    col = np.array(col, np.float32)
    acc += _blur_arr(mask, spill)[..., None] * col * k_spill
    acc += _blur_arr(mask, halo)[..., None] * col * k_halo
    body = _blur_arr(mask, 2)[..., None]
    acc += body * (col * 0.75 + 255 * 0.35)
    acc += _blur_arr(np.clip(mask * 1.6 - 0.75, 0, 1), 1.5)[..., None] * 255 * core


def _mask(im, w, h, cx, cy):
    lay = Image.new('L', (w, h), 0)
    lay.paste(im.getchannel('A'), (int(cx - im.width / 2), int(cy - im.height / 2)))
    return np.asarray(lay, np.float32) / 255


def neon(m, path):
    """«Неон» — вывеска на кирпичной стене (альбом), до матча. side='h'|'a' — за кого прогноз (иначе горят обе)."""
    h, a = teams(m)
    W, H = LW, LH
    wall = bricks(W, H)
    acc = np.zeros((H, W, 3), np.float32)
    shadow_m = np.zeros((H, W), np.float32)
    side = m.get('side')
    pink, yel, cyan = (255, 64, 120), (255, 214, 60), (60, 220, 255)
    # эмблемы: у фаворита горит контур в цвете клуба, у соперника вывеска «выключена»
    for t_, cx, on in ((h, 450, side in (None, 'h')), (a, W - 450, side in (None, 'a'))):
        e = t_.emb(600)
        cont = contour(e, 22)
        cm = _mask(Image.merge('LA', (cont, cont)).convert('RGBA'), W, H, cx, 900)
        em = _mask(e, W, H, cx, 900)
        shadow_m += cm
        col = club(t_)
        col = tuple(min(255, int(v * 1.25 + 30)) for v in col) if on else (70, 70, 76)
        if on:
            _glowadd(acc, cm, col, halo=30, spill=170)
            lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            C.put(lay, e, cx, 900)
            ea = np.asarray(lay.convert('RGB'), np.float32) * em[..., None]
            acc += ea * 0.8
        else:
            acc += cm[..., None] * np.array(col, np.float32) * 0.9
            lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            C.put(lay, e, cx, 900)
            acc += np.asarray(lay.convert('RGB'), np.float32) * em[..., None] * 0.12
    # надписи
    def tube(s, f, size, col, cx, cy, wght=400, max_w=None, **kw):
        im_ = T(s, f, size, (255, 255, 255), wght, max_w=max_w)
        mk = _mask(im_, W, H, cx, cy)
        _glowadd(acc, mk, col, **kw)
        return mk
    shadow_m += tube(tag(m), 'comfortaa', 92, cyan, W / 2, 190, 500, k_spill=0.35)
    shadow_m += tube('%s — %s' % (h.up, a.up), 'comfortaa', 128, (235, 240, 255), W / 2, 470, 500, max_w=2200,
                     k_spill=0.35)
    pk = m.get('pick_script') or pick_sentence(m)
    shadow_m += tube(pk, 'lobster', 300, pink, W / 2, 880, 400, max_w=2050, k_spill=0.8)
    # кэф в рамке
    box = Image.new('RGBA', (980, 360), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle((10, 10, 969, 349), radius=60, outline=(255, 255, 255, 255), width=18)
    bm = _mask(box, W, H, W / 2, 1340)
    _glowadd(acc, bm, yel, k_spill=0.4)
    shadow_m += bm
    if m.get('odds'):
        shadow_m += tube('КЭФ ' + fk(m['odds']), 'comfortaa', 200, yel, W / 2, 1345, 600, k_spill=0.3)
    shadow_m += tube('%s · %s МСК' % (m['day'], m['time']), 'comfortaa', 86, cyan, W / 2, 1690, 600, k_spill=0.3)
    shadow_m += tube(HANDLE, 'comfortaa', 70, (235, 240, 255), W - 330, H - 120, 600, k_spill=0.2)
    sh = _blur_arr(np.clip(shadow_m, 0, 1), 10)
    sh = np.roll(np.roll(sh, 26, 0), 14, 1)
    out = wall * (1 - 0.6 * sh[..., None]) + acc
    out = 255 * (1 - np.exp(-out / 255 * 1.1))                       # мягкое насыщение ярких мест
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    return save(vignette(im, 0.45, 2.0), path)


# ─────────────────────────────── 6. Комикс ───────────────────────────────
def _dots(w, h, col, bg, cell=40, k=0.42, angle=45):
    out = Image.new('RGBA', (w, h), tuple(bg) + (255,))
    out.alpha_composite(halftone(np.full((h, w), k, np.float32), cell, col, angle))
    return out


def _rays(w, h, cx, cy, col, n=64, seed=3, a=255):
    rnd = random.Random(seed)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    R = math.hypot(w, h)
    for i in range(n):
        t = 2 * math.pi * i / n + rnd.uniform(-0.02, 0.02)
        dt = rnd.uniform(0.008, 0.03)
        d.polygon([(cx, cy), (cx + R * math.cos(t - dt), cy + R * math.sin(t - dt)),
                   (cx + R * math.cos(t + dt), cy + R * math.sin(t + dt))], fill=tuple(col) + (a,))
    return im


def _panel(canvas, poly, content, border=22):
    """Вставить содержимое в многоугольную панель с чёрной рамкой."""
    w, h = canvas.size
    mk = Image.new('L', (w * 2, h * 2), 0)
    ImageDraw.Draw(mk).polygon([(x * 2, y * 2) for x, y in poly], fill=255)
    mk = mk.resize((w, h), Image.LANCZOS)
    lay = content.copy()
    lay.putalpha(ImageChops.multiply(lay.getchannel('A'), mk))
    canvas.alpha_composite(lay)
    d = ImageDraw.Draw(canvas)
    d.line(poly + [poly[0]], fill=(16, 16, 18), width=border, joint='curve')


def _caption(s, size, max_w, bg=(255, 226, 84), lines_=3):
    t = C.lines(s.upper(), 'pangolin', size, max_w, (16, 16, 18), 400, gap=0.12, align='l', max_lines=lines_)
    box = Image.new('RGBA', (t.width + 90, t.height + 70), tuple(bg) + (255,))
    ImageDraw.Draw(box).rectangle((0, 0, box.width - 1, box.height - 1), outline=(16, 16, 18), width=9)
    box.alpha_composite(t, (45, 35))
    return box


def _sfx(s, size, fill, shadow=(214, 34, 40), rot=-8, stroke=18, max_w=None):
    t = T(s, 'crisis', size, fill, 700, stroke=stroke, stroke_fill=(16, 16, 18), max_w=max_w)
    sh = T(s, 'crisis', size, shadow, 700, stroke=stroke, stroke_fill=shadow, max_w=max_w)
    out = Image.new('RGBA', (t.width + 40, t.height + 40), (0, 0, 0, 0))
    out.alpha_composite(sh, (32, 32))
    out.alpha_composite(t, (0, 0))
    return out.rotate(rot, Image.BICUBIC, expand=True)


def comic(m, path):
    """«Комикс» — страница поп-арт после матча (портрет)."""
    h, a = teams(m)
    W, H = PW, PH
    im = paper(W, H, (250, 242, 222), seed=91, k=0.6, fibers=600)
    win, lose = (h, a) if m['sh'] > m['sa'] else (a, h)
    hit = m.get('hit')
    M, G = 120, 56
    # шапка
    C.put(im, _sfx('ИТОГ МАТЧА', 300, (255, 218, 50), rot=-3, max_w=W - 2 * M - 700), W / 2 - 150, 330)
    box = _caption(tag(m), 64, 600, bg=(255, 255, 255), lines_=1)
    C.put(im, box.rotate(4, Image.BICUBIC, expand=True), W - M - box.width / 2 - 20, 300)
    # панель 1 — матч
    y0, y1 = 590, 1600
    c1 = _dots(W, H, light(club(h), 0.15), light(club(h), 0.55), cell=46, k=0.35)
    half = Image.new('L', (W, H), 0)
    ImageDraw.Draw(half).polygon([(W / 2 + 220, 0), (W, 0), (W, H), (W / 2 - 220, H)], fill=255)
    c1.paste(_dots(W, H, light(club(a), 0.15), light(club(a), 0.55), cell=46, k=0.35), (0, 0), half)
    for t_, cx in ((h, 820), (a, W - 820)):
        e = t_.emb(760)
        C.put(c1, C.with_shadow(e, 6, 0.9, 18, (16, 16, 18)), cx, (y0 + y1) / 2 + 40)
    C.put(c1, _sfx('VS', 230, (255, 255, 255), rot=6, stroke=16), W / 2, (y0 + y1) / 2 + 40)
    cap = _caption('%s, %s МСК. %s принимает %s.' % (m['day'], m['time'], h.short, a.short), 84, 1450)
    C.put(c1, cap, M + 50, y0 + 50, anchor='tl')
    k = ('КЭФ ' + fk(m['odds'])) if m.get('odds') else ''
    cap2 = _caption('Наш прогноз: %s%s' % (m['pick'], (' · ' + k) if k else ''), 84, 1650,
                    bg=(255, 255, 255))
    C.put(c1, cap2, W - M - 50 - cap2.width, y1 - 50 - cap2.height, anchor='tl')
    _panel(im, [(M, y0), (W - M, y0), (W - M, y1), (M, y1)], c1)
    # панель 2 — счёт и победитель (разрез наискось)
    y2, y3 = y1 + G, 2780
    xa, xb = 1700, 1540
    c2 = Image.new('RGBA', (W, H), (232, 40, 46, 255))
    c2.alpha_composite(_rays(W, H, 900, (y2 + y3) / 2, (255, 214, 60), n=70))
    sc = _sfx('%d:%d' % (m['sh'], m['sa']), 430, (255, 255, 255), shadow=(16, 16, 18), rot=-6, stroke=20)
    C.put(c2, sc, 860, (y2 + y3) / 2 + 30)
    if m.get('mark'):
        C.put(c2, _caption(mark_ru(m['mark']), 70, 700, lines_=1).rotate(-6, Image.BICUBIC, expand=True), 860, y3 - 170)
    bst = C.polygon(burst(230, 150, 11, 0.62, seed=4), (460, 300), (255, 236, 80))
    C.put(c2, bst, 420, y2 + 230)
    C.put(c2, _sfx('БАХ!', 110, (232, 40, 46), shadow=(16, 16, 18), rot=-12, stroke=10), 420, y2 + 225)
    _panel(im, [(M, y2), (xa - G / 2, y2), (xb - G / 2, y3), (M, y3)], c2)
    c3 = _dots(W, H, dark(club(win), 0.1), light(club(win), 0.6), cell=38, k=0.38, angle=15)
    c3.alpha_composite(_rays(W, H, 2480, (y2 + y3) / 2, (255, 255, 255), n=48, seed=8, a=150))
    e = win.emb(800)
    C.put(c3, C.with_shadow(e, 6, 0.9, 18, (16, 16, 18)), 2470, (y2 + y3) / 2 + 60)
    cap3 = _caption('Финальная сирена!', 84, 900)
    C.put(c3, cap3, xa + 60, y2 + 50, anchor='tl')
    _panel(im, [(xa + G / 2, y2), (W - M, y2), (W - M, y3), (xb + G / 2, y3)], c3)
    # панель 3 — вердикт
    y4, y5 = y3 + G, 3800
    if hit:
        c4 = Image.new('RGBA', (W, H), (40, 120, 230, 255))
        c4.alpha_composite(_rays(W, H, W / 2, (y4 + y5) / 2, (90, 170, 255), n=80, seed=11))
        b = C.polygon(burst(1250, 430, 16, 0.78, seed=6), (2500, 860), (255, 226, 60))
        C.put(c4, C.with_shadow(b, 4, 0.9, 16, (16, 16, 18)), W / 2, (y4 + y5) / 2 - 40)
        C.put(c4, _sfx('ЗАШЁЛ!', 360, (232, 40, 46), shadow=(16, 16, 18), rot=-5, stroke=20), W / 2, (y4 + y5) / 2 - 60)
    else:
        c4 = _dots(W, H, (60, 64, 80), (150, 156, 172), cell=40, k=0.4)
        C.put(c4, _sfx('НЕ ЗАШЁЛ…', 300, (230, 232, 240), shadow=(16, 16, 18), rot=-3, stroke=18,
                       max_w=W - 2 * M - 300), W / 2, (y4 + y5) / 2 - 60)
    if m.get('why'):
        res = m['why']
    elif 'ТОТАЛ МАТЧА' in m['pick'] or m['pick'].startswith('ТОТАЛ'):
        res = goals(m['sh'] + m['sa']).lower() + ' в матче'
    else:
        res = '%s выиграл %d:%d' % (win.short, max(m['sh'], m['sa']), min(m['sh'], m['sa']))
        if m.get('mark'):
            res += ' (%s)' % m['mark']
    cap4 = _caption(res + ((' · ' + k) if k else ''), 92, 2600, bg=(255, 255, 255), lines_=1)
    C.put(c4, cap4, W / 2, y5 - 70 - cap4.height / 2)
    _panel(im, [(M, y4), (W - M, y4), (W - M, y5), (M, y5)], c4)
    C.put(im, T('ПРОДОЛЖЕНИЕ — В TELEGRAM ' + HANDLE, 'pangolin', 84, (16, 16, 18), 400), W / 2, 3920)
    return save(im, path)


# ─────────────────────────────── 7. Чертёж ───────────────────────────────
def _arrow(d, x0, y0, x1, y1, col, w=6, head=34, ends=(1, 1)):
    d.line((x0, y0, x1, y1), fill=col, width=w)
    for on, (xa, ya, xb, yb) in zip(ends, ((x0, y0, x1, y1), (x1, y1, x0, y0))):
        if not on:
            continue
        ang = math.atan2(yb - ya, xb - xa)
        for s in (-0.32, 0.32):
            d.line((xa, ya, xa + head * math.cos(ang + s), ya + head * math.sin(ang + s)), fill=col, width=w)


def lineart(e, col, k=1.0):
    """Эмблема линиями: контур силуэта + перепады яркости внутри."""
    L = e.convert('L')
    a = e.getchannel('A')
    ed = ImageChops.lighter(L.filter(ImageFilter.FIND_EDGES), a.filter(ImageFilter.FIND_EDGES))
    ed = ed.point(lambda v: 255 if v > 38 else 0).filter(ImageFilter.MaxFilter(3))
    ed = ImageChops.multiply(ed, a.filter(ImageFilter.MaxFilter(5)))
    out = Image.new('RGBA', e.size, tuple(col) + (0,))
    out.putalpha(ed.point(lambda v: int(v * k)))
    return out


def blueprint(m, path):
    """«Чертёж» — синька: площадка в линиях, размерные линии, штамп с прогнозом (альбом), до матча."""
    h, a = teams(m)
    W, H = LW, LH
    im = paper(W, H, (24, 66, 142), seed=101, k=0.9, fibers=0)
    S = 2
    lay = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    g1, g2 = (190, 214, 255, 34), (190, 214, 255, 70)
    for x in range(0, W, 48):
        d.line((x * S, 0, x * S, H * S), fill=g2 if x % 240 == 0 else g1, width=2 if x % 240 else 3)
    for y in range(0, H, 48):
        d.line((0, y * S, W * S, y * S), fill=g2 if y % 240 == 0 else g1, width=2 if y % 240 else 3)
    ink = (236, 244, 255, 255)
    x0, y0, x1, y1 = 420, 250, 3180, 1430
    rw, rh = x1 - x0, y1 - y0
    ft = rw / 200.0
    P = lambda x, y: (x * S, y * S)                        # noqa: E731
    d.rounded_rectangle((*P(x0, y0), *P(x1, y1)), radius=28 * ft * S, outline=ink, width=10 * S)
    cy = (y0 + y1) / 2
    for gx in (x0 + 11 * ft, x1 - 11 * ft):
        d.line((*P(gx, y0 + 8), *P(gx, y1 - 8)), fill=ink, width=3 * S)
        sg = 1 if gx < W / 2 else -1
        d.arc((*P(gx - 6 * ft, cy - 6 * ft), *P(gx + 6 * ft, cy + 6 * ft)), -90 if sg > 0 else 90, 90 if sg > 0 else 270,
              fill=ink, width=3 * S)
        d.rectangle((*P(min(gx, gx - sg * 3.3 * ft), cy - 3 * ft), *P(max(gx, gx - sg * 3.3 * ft), cy + 3 * ft)),
                    outline=ink, width=3 * S)
        for fy in (cy - 22 * ft, cy + 22 * ft):
            fx = gx + sg * 20 * ft
            d.ellipse((*P(fx - 15 * ft, fy - 15 * ft), *P(fx + 15 * ft, fy + 15 * ft)), outline=ink, width=3 * S)
            d.ellipse((*P(fx - 1 * ft, fy - 1 * ft), *P(fx + 1 * ft, fy + 1 * ft)), fill=ink)
    for bx in (x0 + 75 * ft, x1 - 75 * ft):
        d.line((*P(bx - 0.5 * ft, y0 + 4), *P(bx - 0.5 * ft, y1 - 4)), fill=ink, width=4 * S)
        d.line((*P(bx + 0.5 * ft, y0 + 4), *P(bx + 0.5 * ft, y1 - 4)), fill=ink, width=4 * S)
    cx = x0 + rw / 2
    for yy in range(int(y0), int(y1), 36):                         # центральная линия — пунктиром
        d.line((*P(cx, yy), *P(cx, min(yy + 22, y1))), fill=ink, width=4 * S)
    d.ellipse((*P(cx - 15 * ft, cy - 15 * ft), *P(cx + 15 * ft, cy + 15 * ft)), outline=ink, width=3 * S)
    for nx in (x0 + 75 * ft + 5 * ft, x1 - 75 * ft - 5 * ft):
        for fy in (cy - 22 * ft, cy + 22 * ft):
            d.ellipse((*P(nx - ft, fy - ft), *P(nx + ft, fy + ft)), fill=ink)
    # размерная линия снизу — прогноз, слева — кэф (с разрывом под надпись)
    dy, dx = 1530, 300
    lab_b = T(m['pick'], 'kelly', 84, ink[:3], 400)
    lab_l = T(('КЭФ ' + fk(m['odds'])) if m.get('odds') else 'БЕЗ КЭФА', 'kelly', 84, ink[:3], 400)
    for xx in (x0, x1):
        d.line((*P(xx, y1 + 20), *P(xx, dy + 40)), fill=ink, width=2 * S)
    for yy in (y0, y1):
        d.line((*P(x0 - 20, yy), *P(dx - 40, yy)), fill=ink, width=2 * S)
    mx, gb = (x0 + x1) / 2, lab_b.width / 2 + 40
    _arrow(d, x0 * S, dy * S, (mx - gb) * S, dy * S, ink, 3 * S, 34 * S, ends=(1, 0))
    _arrow(d, (mx + gb) * S, dy * S, x1 * S, dy * S, ink, 3 * S, 34 * S, ends=(0, 1))
    my, gl = (y0 + y1) / 2, lab_l.width / 2 + 40
    _arrow(d, dx * S, y0 * S, dx * S, (my - gl) * S, ink, 3 * S, 34 * S, ends=(1, 0))
    _arrow(d, dx * S, (my + gl) * S, dx * S, y1 * S, ink, 3 * S, 34 * S, ends=(0, 1))
    lay = lay.resize((W, H), Image.LANCZOS)
    im.alpha_composite(lay)
    inkc = ink[:3]

    C.put(im, lab_b, (x0 + x1) / 2, dy)
    C.put(im, lab_l.rotate(90, Image.BICUBIC, expand=True), dx, cy)
    # эмблемы линиями и выноски
    for t_, ex, lx, role in ((h, x0 + 43 * ft, 760, 'ХОЗЯЕВА'), (a, x1 - 43 * ft, W - 760, 'ГОСТИ')):
        e = t_.emb(560)
        C.put(im, lineart(e, inkc, 0.95), ex, cy)
        dd = ImageDraw.Draw(im)
        dd.line((ex, cy - 300, lx, 150), fill=inkc, width=4)
        dd.ellipse((ex - 9, cy - 309, ex + 9, cy - 291), fill=inkc)
        lt = T('%s · %s' % (t_.up, role), 'kelly', 66, inkc, 400)
        lx2 = lx - lt.width - 40 if lx < W / 2 else lx + 40
        dd.line((lx, 150, lx2 + (lt.width if lx < W / 2 else 0), 150), fill=inkc, width=4)
        C.put(im, lt, lx2, 150 - lt.height - 12, anchor='tl')
    # штамп
    bx0, by0, bx1, by1 = 2380, 1640, 3780, 1880
    dd = ImageDraw.Draw(im)
    dd.rectangle((bx0, by0, bx1, by1), outline=inkc, width=6)
    cols = [bx0, bx0 + 300, bx1 - 360, bx1]
    rows = [by0, by0 + 80, by0 + 160, by1]
    for x in cols[1:-1]:
        dd.line((x, by0, x, by1), fill=inkc, width=3)
    for y in rows[1:-1]:
        dd.line((bx0, y, cols[2], y), fill=inkc, width=3)
    for i, (k_, v_) in enumerate((('МАТЧ', '%s — %s' % (h.up, a.up)), ('НАЧАЛО', '%s · %s МСК' % (m['day'], m['time'])),
                                  ('РАЗРАБОТАЛ', tag(m)))):
        kk = T(k_, 'kelly', 44, inkc, 400)
        C.put(im, kk, cols[0] + 22, (rows[i] + rows[i + 1]) / 2 - kk.height / 2, anchor='tl')
        vv = T(v_, 'kelly', 50, inkc, 400, max_w=cols[2] - cols[1] - 40)
        C.put(im, vv, cols[1] + 20, (rows[i] + rows[i + 1]) / 2 - vv.height / 2, anchor='tl')
    C.put(im, T(lg_ru(m), 'kelly', 120, inkc, 400), (cols[2] + bx1) / 2, (by0 + by1) / 2 - 20)
    C.put(im, T('ЛИСТ 1', 'kelly', 40, inkc, 400), (cols[2] + bx1) / 2, by1 - 36)
    nm = 'ЧЕРТЁЖ JRV-%s-%s' % (lg(m), m['day'].split()[-1].replace('.', ''))
    C.put(im, T(nm, 'kelly', 56, inkc, 400), 140, 1700, anchor='tl')
    ms = T('МАСШТАБ 1:1 ·', 'kelly', 56, inkc, 400)
    C.put(im, ms, 140, 1790, anchor='tl')
    C.put(im, T(HANDLE, 'mono', 50, inkc, 500), 140 + ms.width + 24, 1790 + ms.height - 50, anchor='tl')
    return save(vignette(im, 0.4, 2.2), path)


# ─────────────────────────────── 8. Швейцарский плакат ───────────────────────────────
def swiss(m, path):
    """«Швейцарский плакат» — сетка, круг и квадрат в цветах клубов, огромный кэф (портрет), до матча."""
    h, a = teams(m)
    W, H = PW, PH
    ink = (18, 18, 20)
    im = paper(W, H, (240, 237, 230), seed=111, k=0.35, fibers=120)
    ch, ca = club(h), club(a)
    M = 160
    circ = C.ellipse(2400, 2400, ch)
    C.put(im, circ, 2280, 1320)
    sq = Image.new('RGBA', (560, 560), tuple(ca) + (255,))
    C.put(sq, T(m['time'], 'onest', 190, (255, 255, 255), 900), 280, 250)
    C.put(sq, T('МСК', 'onest', 64, (255, 255, 255), 700, track=0.2), 280, 420)
    C.put(im, sq, M, 1880, anchor='tl')
    d = ImageDraw.Draw(im)
    d.line((M, 400, W - M, 400), fill=ink, width=8)
    C.put(im, T(tag(m), 'onest', 72, ink, 800), M, 220, anchor='tl')
    C.put(im, T('прогноз на матч', 'onest', 72, ink, 400), M + 1140, 220, anchor='tl')
    for i, t_ in enumerate((h, a)):
        nm = T(t_.short, 'onest', 300, ink, 900, max_w=1900)
        C.put(im, nm, M - 12, 700 + i * 380, anchor='tl')
        C.put(im, t_.emb(380), 2780, 860 + i * 520)
    lines_ = (m['date_long'].capitalize(), 'Чемпионат %s' % lg_ru(m))
    for i, s_ in enumerate(lines_):
        C.put(im, T(s_, 'onest', 96, ink, 700 if i == 0 else 400), M + 640, 1930 + i * 140, anchor='tl')
    d.line((M, 2560, W - M, 2560), fill=ink, width=8)
    C.put(im, T('Наш прогноз', 'onest', 72, ink, 400), M, 2620, anchor='tl')
    pk = C.lines(pick_sentence(m), 'onest', 150, W - 2 * M, ink, 800, gap=0.08, align='l', max_lines=2)
    C.put(im, pk, M - 6, 2740, anchor='tl')
    if m.get('odds'):
        C.put(im, T('Кэф', 'onest', 72, ink, 400), M, 3120, anchor='tl')
        kf = T(fk(m['odds']), 'onest', 980, ink, 900, max_w=W - 2 * M - 700)
        C.put(im, kf, M - 30, 3880 - kf.height, anchor='tl')
    hd = T(HANDLE, 'onest', 80, ink, 700)
    C.put(im, hd, W - M - hd.width, 3800, anchor='tl')
    vt = T('ПРОГНОЗЫ НА ХОККЕЙ', 'onest', 54, ink, 700, track=0.3).rotate(90, expand=True)
    C.put(im, vt, W - M - vt.width / 2, 3200)
    return save(im, path)


# ─────────────────────────────── 9. Пластинка ───────────────────────────────
def vinyl(m, path):
    """«Пластинка» — конверт и диск, на яблоке пластинки прогноз (альбом), до матча."""
    h, a = teams(m)
    W, H = LW, LH
    fav = a if m.get('side') == 'a' else h
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    dd_ = np.sqrt(((x - 1900) / 2600) ** 2 + ((y - 760) / 1500) ** 2)
    bg = np.clip(1 - dd_, 0, 1)[..., None] * np.array([46, 40, 44], np.float32) + 9
    im = Image.fromarray(np.clip(bg + np.random.default_rng(5).normal(0, 2.5, (H, W, 1)), 0, 255).astype(np.uint8),
                         'RGB').convert('RGBA')
    # диск
    R = 760
    dcx, dcy = 2660, 960
    yy, xx = np.mgrid[-R:R, -R:R].astype(np.float32)
    r = np.sqrt(xx ** 2 + yy ** 2)
    th = np.arctan2(yy, xx)
    groove = 0.5 + 0.5 * np.sin(r * 1.9)
    sheen = np.abs(np.cos(th - 0.6)) ** 14 * 0.9 + np.abs(np.cos(th + 1.1)) ** 30 * 0.35
    v = 14 + groove * 7 + sheen * 70 * (0.6 + 0.4 * groove)
    v = np.where(r < 300, 0, v)
    disc = np.zeros((2 * R, 2 * R, 4), np.uint8)
    disc[..., :3] = np.clip(v, 0, 255)[..., None].astype(np.uint8)
    disc[..., 3] = (np.clip(R - r, 0, 1.5) / 1.5 * 255).astype(np.uint8)
    dimg = Image.fromarray(disc, 'RGBA')
    lab = C.ellipse(600, 600, club(fav))
    ld = ImageDraw.Draw(lab)
    ld.ellipse((26, 26, 574, 574), outline=light(club(fav), 0.5), width=4)
    C.put(lab, T('СТОРОНА А · %s' % lg_ru(m), 'onest', 30, (255, 255, 255), 700, track=0.2), 300, 92)
    pk = C.lines(m['pick'], 'onest', 46, 400, (255, 255, 255), 800, gap=0.06, max_lines=3)
    pk = C.fit(pk, 420, 130) if pk.height > 130 or pk.width > 420 else pk
    C.put(lab, pk, 300, 196)
    if m.get('odds'):
        C.put(lab, T('КЭФ ' + fk(m['odds']), 'onest', 70, (255, 255, 255), 900), 300, 408)
    C.put(lab, T('%s · %s МСК' % (m['day'], m['time']), 'onest', 30, (255, 255, 255), 600, track=0.1), 300, 494)
    ld.ellipse((300 - 16, 300 - 16, 300 + 16, 300 + 16), fill=(12, 12, 14, 255))
    C.put(dimg, lab, R, R)
    C.put(im, C.shadow(dimg, 30, 0.7), dcx + 20, dcy + 30)
    C.put(im, dimg, dcx, dcy)
    # конверт
    SZ = 1560
    sl = Image.new('RGBA', (SZ, SZ), tuple(club(fav)) + (255,))
    e = fav.emb(1500)
    tone = tone_of(e, floor=0.15)
    sl.alpha_composite(halftone(tone, 30, dark(club(fav), 0.55), angle=30), (int(SZ * 0.22), int(SZ * 0.05)))
    sd = ImageDraw.Draw(sl)
    sd.rectangle((0, SZ - 430, SZ, SZ), fill=(16, 16, 18))
    C.put(sl, C.with_shadow(h.emb(200), 8, 0.4, 6), 140, SZ - 330)
    C.put(sl, C.with_shadow(a.emb(200), 8, 0.4, 6), 360, SZ - 330)
    C.put(sl, T('%s — %s' % (h.up, a.up), 'unb', 76, (255, 255, 255), 800, max_w=SZ - 560), 500, SZ - 360, anchor='tl')
    C.put(sl, T('%s · %s МСК' % (m['day'], m['time']), 'onest', 54, (200, 200, 205), 600, track=0.06), 500, SZ - 230,
          anchor='tl')
    C.put(sl, T(HANDLE, 'onest', 50, (150, 150, 158), 600), 500, SZ - 140, anchor='tl')
    C.put(sl, T(tag(m), 'onest', 64, (255, 255, 255), 800, track=0.1), 80, 80, anchor='tl')
    st = C.ellipse(400, 400, (255, 214, 64))
    C.put(st, T('НАШ', 'onest', 54, (20, 20, 22), 800, track=0.2), 200, 120)
    C.put(st, T('ПРОГНОЗ', 'onest', 54, (20, 20, 22), 800, track=0.1), 200, 180)
    if m.get('odds'):
        C.put(st, T(fk(m['odds']), 'onest', 120, (20, 20, 22), 900), 200, 280)
    C.put(sl, st.rotate(12, Image.BICUBIC, expand=True), SZ - 260, 300)
    edge = Image.new('RGBA', (SZ, SZ), (0, 0, 0, 0))
    ImageDraw.Draw(edge).rectangle((0, 0, SZ - 1, SZ - 1), outline=(255, 255, 255, 60), width=6)
    sl.alpha_composite(edge)
    sl = wear(sl, 9, k=0.08, speck=0.004)
    C.put(im, C.shadow(sl, 40, 0.75), 1260 + 30, 960 + 40)
    C.put(im, sl, 1260, 960)
    return save(vignette(im, 0.35), path)
