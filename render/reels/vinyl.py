# -*- coding: utf-8 -*-
"""«Винил» — проигрыватель ночью под тёплой лампой: каждая команда — пластинка, прогноз — игла на дроп.

Вид сверху: тёмный стол, свет настольной лампы из левого верхнего угла, пылинки в луче. Проигрыватель — деревянный
корпус, матовая чёрная панель, серебряный диск со стробоскопическими метками, тонарм с противовесом. Пластинка —
чёрный винил с канавками и тремя «дорожками», неподвижный блик-«бабочка» (как в жизни: канавки крутятся, блик стоит),
вращается наклейка-яблоко с кольцевой надписью, эмблема клуба в центре наклейки стоит прямо (читается).
Конверт — в цветах клуба с большой эмблемой; его оборот — «трек-лист» на кремовой бумаге: А1–А3 (хозяева, сторона А)
или Б1–Б3 (гости, сторона Б) — последние 3 игры (соперник, дата, дома/в гостях, счёт как длительность трека, В/П,
пометка ОТ/Б), ниже колонками очки (за сколько матчей), место (где), разница шайб; серия от двух игр — в подписи.

Сцены (u — доля трека; все склейки и акценты — на долях от дропа, параметры — reels_cfg/vinyl.json):
  интро (до b(−2·team−bridge)) — две пластинки рядом (обе эмблемы), хозяева / гости, день и время МСК, линия
                основного времени П1 · Х · П2 крупными кремовыми плашками (встают на долю); в конце — панорама вниз;
  команда 1 (team долей, ~5,8 с) — конверт хозяев лицом; на 1-ю долю пластинка выезжает из конверта на диск и
                раскручивается; тонарм поднимается и идёт к пластинке; на 2-ю долю конверт переворачивается на
                трек-лист и игла падает на дорожку А1; на 3-ю и 4-ю доли тонарм переходит на А2 и А3, строки
                подсвечиваются по очереди; на 5-ю — акцент на очках, месте и шайбах; в конце сцены игла поднимается,
                пластинка и конверт уезжают влево, как в ящике с пластинками;
  команда 2 (team долей) — то же для гостей (сторона Б);
  перед дропом (bridge долей) — игла поднимается и тонарм уходит на подставку, диск замедляется, пластинка
                поднимается с диска; внизу два конверта рядом (обе команды), за кадр до дропа уходят вниз, свет приглушается;
  ДРОП (hold долей, ~4,1 с) — вспышка, крупный план: на диск падает пластинка ТОЛЬКО выбранной команды (одна эмблема),
                игла опускается ровно на удар, из канавки — световой импульс-звуковая волна, наклейка «наезжает»;
                на конверте клуба — наклейка с прогнозом (form.split_pick) и кэфом; на каждую долю — новый импульс;
  финал (cta долей, ~2,5 с) — всё поднимается, снизу плашка Telegram (C.tg_plate, текст по центру плашки).
@jarvibet — у низа безопасной зоны (y 1446) одинаково во всех сценах до плашки Telegram; JARVIS | NHL — в интро сверху
и шильдиком на корпусе проигрывателя.
lag — сдвиг видимого дропа в долях от точки, которую передаёт сборка (withyou: точка 81,59 с — слабая доля «и»
внутри такта, а бас после паузы возвращается на сильную долю на 3/16 такта раньше — 80,97 с; поэтому lag = −0,75).
Кадр — чистая функция t; фоны, корпус, пластинки, конверты и тексты строятся один раз в __init__ (до форка процессов)
и лежат в кеше модуля.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels import fresh
from reels.core import W, H

INK = (38, 29, 24)
CREAM = (242, 231, 208)
PAPER = (236, 224, 197)
RUST = (172, 60, 34)
AMBER = (255, 190, 102)
MUTED = (112, 94, 78)
WIN = (40, 138, 78)
LOSS = (190, 52, 38)
HANDLE_Y = 1446

R0 = 240                                   # радиус пластинки на корпусе (масштаб 1)
CAM_T = (390.0, 505.0, 1.0)                # камера сцен клубов: центр пластинки и масштаб корпуса
CAM_P = (430.0, 600.0, 1.3)                # крупный план прогноза
PIV = (490.0, -180.0)                      # ось тонарма относительно центра пластинки (масштаб 1)
ARM_L = 420.0                              # длина тонарма до иглы (масштаб 1)
SLV_X, SLV_Y, SLV_S = 70, 790, 940         # большой конверт: левый верх и сторона
OM = 200.0                                 # 33⅓ об/мин — градусов в секунду
LAB_K = 0.5                                # радиус наклейки / радиус пластинки
GROOVE = (0.53, 0.955)                     # канавки — доли радиуса

_S = {}


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def streak_txt(s):
    """«В3» → «3 ПОБЕДЫ ПОДРЯД»; серии короче двух — пусто."""
    s = str(s or '').strip().upper()
    if len(s) < 2 or not s[1:].isdigit() or int(s[1:]) < 2:
        return ''
    n = int(s[1:])
    if s[0] in ('В', 'W'):
        return '%d %s ПОДРЯД' % (n, plural(n, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'))
    if s[0] in ('П', 'L'):
        return '%d %s ПОДРЯД' % (n, plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ'))
    return ''


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _on(c):
    """Цвет текста поверх цвета клуба."""
    return INK if _lum(c) > 150 else CREAM


def _F(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def _rgba(rgb, alpha):
    arr = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), np.clip(alpha, 0, 255).astype(np.uint8)])
    return Image.fromarray(arr, 'RGBA')


def _smooth_noise(h, w, cell, rng, amp=1.0):
    n = rng.normal(0, 1, (max(2, h // cell + 2), max(2, w // cell + 2))).astype(np.float32)
    im = Image.fromarray(n, 'F').resize((w, h), Image.BICUBIC)
    return np.asarray(im, np.float32) * amp


def _paste(fr, im, cx, cy, anchor='c'):
    """Наложить RGBA на RGB-кадр (маска — альфа), можно за край."""
    x = int(round(cx - im.width / 2)) if anchor == 'c' else int(round(cx))
    y = int(round(cy - im.height / 2)) if anchor == 'c' else int(round(cy))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(fr.width, x + im.width), min(fr.height, y + im.height)
    if x1 <= x0 or y1 <= y0:
        return
    if (x0, y0, x1, y1) != (x, y, x + im.width, y + im.height):
        im = im.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    fr.paste(im, (x0, y0), im)


def _rot_about(im, deg, pivot):
    """Повернуть спрайт против часовой на deg вокруг точки pivot → (картинка, где теперь pivot)."""
    w, h = im.size
    r = im.rotate(deg, Image.BICUBIC, expand=True)
    a = math.radians(deg)
    dx, dy = pivot[0] - w / 2, pivot[1] - h / 2
    nx = dx * math.cos(a) + dy * math.sin(a)
    ny = -dx * math.sin(a) + dy * math.cos(a)
    return r, (r.width / 2 + nx, r.height / 2 + ny)


# ─────────────────────────────── стол, свет ───────────────────────────────
def _table():
    if 'table' in _S:
        return _S['table']
    rng = np.random.default_rng(11)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    warp = _smooth_noise(H, W, 220, rng, 38)
    fine = rng.normal(0, 1, W + 400).astype(np.float32)
    fine = np.convolve(fine, np.ones(5) / 5, 'same')
    xx = np.clip((x + warp + 200).astype(np.int32), 0, W + 399)
    grain = fine[xx] * 0.55 + np.sin((x + warp * 1.6) * 0.06 + np.sin(y * 0.0035) * 2.2) * 0.45
    plank = ((x + 30) // 270).astype(np.int32)
    tone = np.array([0.0, 0.07, -0.05, 0.04, -0.02, 0.05], np.float32)[plank % 6]
    v = 1 + 0.10 * grain + tone + _smooth_noise(H, W, 90, rng, 0.04)
    seam = np.abs(((x + 30) % 270) - 0) < 1.5
    v[seam] *= 0.55
    base = np.array((50, 33, 23), np.float32)
    arr = v[..., None] * base
    _S['table'] = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    return _S['table']


def _light():
    """Карта света лампы (множитель ×256 по каналам): тёплое пятно слева сверху, низ кадра — в тень (под @jarvibet)."""
    if 'light' in _S:
        return _S['light']
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d2 = (x - 150) ** 2 + ((y - 230) * 0.92) ** 2
    pool = np.exp(-d2 / (2 * 980.0 ** 2))
    hot = np.exp(-d2 / (2 * 420.0 ** 2))
    f = 0.60 + 0.42 * pool + 0.12 * hot
    bot = np.clip((y - 1395) / 170, 0, 1)
    f *= 1 - 0.62 * bot ** 1.4
    top = np.clip((235 - y) / 200, 0, 1)
    f *= 1 - 0.30 * top
    warm = np.stack([1.0 + 0.07 * pool, 1.0 + 0.0 * pool, 1.0 - 0.10 * pool], -1)
    lm = (f[..., None] * warm * 256).astype(np.uint16)
    _S['light'] = lm
    return lm


def _mote(d):
    key = ('mote', d)
    if key not in _S:
        _S[key] = C.radial(d, d, (255, 236, 200), 255, 1.6)
    return _S[key]


# ─────────────────────────────── корпус проигрывателя ───────────────────────────────
def _brushed(w, h, rng, base=30, amp=5.0):
    n = rng.normal(0, 1, (h, max(2, w // 10))).astype(np.float32)
    n = np.asarray(Image.fromarray(n, 'F').resize((w, h), Image.BILINEAR), np.float32)
    n += rng.normal(0, 0.35, (h, w)).astype(np.float32)
    return base + amp * n


def _plinth(s):
    """Корпус (вид сверху) в координатах «центр пластинки = (0, 0)» → (RGBA, (x0, y0) левого верха)."""
    key = ('plinth', s)
    if key in _S:
        return _S[key]
    rng = np.random.default_rng(5)
    pad = int(70 * s)
    px0, py0, px1, py1 = -370 * s, -265 * s, 650 * s, 265 * s
    w, h = int(px1 - px0) + 2 * pad, int(py1 - py0) + 2 * pad
    ox, oy = px0 - pad, py0 - pad                       # где (0,0) спрайта в координатах пластинки
    cx, cy = -ox, -oy                                   # центр пластинки в спрайте
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    bw, bh = int(px1 - px0), int(py1 - py0)
    rad = 30 * s
    # тень корпуса на столе
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((pad + 10 * s, pad + 26 * s, pad + bw + 10 * s, pad + bh + 26 * s), radius=rad, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(26 * s)).point(lambda v: int(v * 0.78))
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 255))
    sh.putalpha(m)
    out.alpha_composite(sh)
    # деревянная рамка (орех)
    yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
    warp = _smooth_noise(bh, bw, int(60 * s) + 1, rng, 10 * s)
    fine = rng.normal(0, 1, bh + 200).astype(np.float32)
    fine = np.convolve(fine, np.ones(3) / 3, 'same')
    gy = np.clip((yy + warp + 100).astype(np.int32), 0, bh + 199)
    g = fine[gy] * 0.6 + np.sin((yy + warp) * 0.11 / s) * 0.4
    wood = (1 + 0.12 * g)[..., None] * np.array((104, 64, 38), np.float32)
    # фаска: светлее сверху-слева, темнее снизу-справа
    edge = np.minimum(np.minimum(xx, yy), np.minimum(bw - 1 - xx, bh - 1 - yy))
    bev = np.clip(1 - edge / (7 * s), 0, 1)
    side = np.where((xx < bw * 0.5) & (yy < bh * 0.5), 1.0, -1.0) * 0 + ((bw - xx) / bw * 0.5 + (bh - yy) / bh * 0.5 - 0.5)
    wood *= (1 + bev[..., None] * (0.35 * side[..., None]))
    m = Image.new('L', (bw * 2, bh * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, bw * 2 - 1, bh * 2 - 1), radius=rad * 2, fill=255)
    m = m.resize((bw, bh), Image.LANCZOS)
    wim = Image.fromarray(np.clip(wood, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    wim.putalpha(m)
    out.alpha_composite(wim, (pad, pad))
    # матовая чёрная панель
    ins = 24 * s
    tw, th = int(bw - 2 * ins), int(bh - 2 * ins)
    met = _brushed(tw, th, rng, 27, 3.2)
    ty = np.linspace(1.08, 0.92, th, dtype=np.float32)[:, None]
    met = met * ty
    top = np.stack([met, met, met * 1.04], -1)
    tim = Image.fromarray(np.clip(top, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    m = Image.new('L', (tw * 2, th * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, tw * 2 - 1, th * 2 - 1), radius=14 * s * 2, fill=255)
    tim.putalpha(m.resize((tw, th), Image.LANCZOS))
    # тонкая светлая кромка панели
    rim = Image.new('RGBA', (tw * 2, th * 2), (0, 0, 0, 0))
    ImageDraw.Draw(rim).rounded_rectangle((1, 1, tw * 2 - 2, th * 2 - 2), radius=14 * s * 2, outline=(120, 104, 88, 150),
                                          width=max(2, int(2 * s)))
    tim.alpha_composite(rim.resize((tw, th), Image.LANCZOS))
    out.alpha_composite(tim, (int(pad + ins), int(pad + ins)))
    # ── детали (рисуем с запасом ×3 и уменьшаем) ──
    SS = 3
    det = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(det)

    def P(x, y):
        return ((cx + x * s) * SS, (cy + y * s) * SS)

    def circ(x, y, r, **kw):
        X, Y = P(x, y)
        d.ellipse((X - r * s * SS, Y - r * s * SS, X + r * s * SS, Y + r * s * SS), **kw)

    # колодец диска и обод
    circ(0, 0, 262, fill=(10, 10, 11, 255))
    circ(0, 0, 253, fill=(150, 150, 154, 255))
    circ(0, 0, 249, fill=(186, 186, 190, 255))
    circ(0, 0, 241, fill=(40, 40, 42, 255))
    # стробоскопические метки по ободу (стоят — так и задумано у стробоскопа)
    for k in range(120):
        a = 2 * math.pi * k / 120
        x1, y1 = P(244.5 * math.cos(a), 244.5 * math.sin(a))
        x2, y2 = P(251 * math.cos(a), 251 * math.sin(a))
        d.line((x1, y1, x2, y2), fill=(70, 70, 74, 255), width=max(1, int(1.6 * s * SS)))
    # резиновый мат (виден без пластинки)
    circ(0, 0, 240, fill=(24, 24, 26, 255))
    for rr in range(60, 236, 9):
        circ(0, 0, rr, outline=(34, 34, 37, 255), width=max(1, int(2 * s * SS)))
    circ(0, 0, 9, fill=(200, 200, 205, 255))
    circ(0, 0, 5, fill=(240, 240, 244, 255))
    # база тонарма
    bx, by = PIV
    circ(bx, by, 66, fill=(14, 14, 15, 255))
    circ(bx, by, 62, fill=(168, 168, 172, 255))
    circ(bx, by, 56, fill=(120, 120, 124, 255))
    circ(bx, by, 46, fill=(28, 28, 30, 255))
    circ(bx, by, 36, outline=(196, 156, 92, 255), width=int(3 * s * SS))
    # регулятор антискейтинга и рычаг микролифта
    circ(bx - 86, by + 40, 17, fill=(160, 160, 164, 255))
    circ(bx - 86, by + 40, 12, fill=(60, 60, 64, 255))
    X, Y = P(bx - 86, by + 40)
    d.line((X, Y, X, Y - 12 * s * SS), fill=(230, 230, 230, 255), width=int(2 * s * SS))
    X0, Y0 = P(bx - 52, by + 86)
    X1, Y1 = P(bx - 30, by + 132)
    d.rounded_rectangle((X0, Y0, X1, Y1), radius=6 * s * SS, fill=(150, 150, 154, 255))
    # подставка тонарма
    rx, ry = bx + 6, by + 300
    circ(rx, ry, 18, fill=(12, 12, 13, 255))
    circ(rx, ry, 14, fill=(150, 150, 154, 255))
    circ(rx, ry, 9, fill=(40, 40, 42, 255))
    # кнопки: старт и скорости
    circ(-322, 150, 30, fill=(12, 12, 13, 255))
    circ(-322, 150, 26, fill=(170, 170, 174, 255))
    circ(-322, 150, 20, fill=(200, 200, 204, 255))
    for k, yy_ in enumerate((206, 240)):
        X0, Y0 = P(-350, yy_ - 13)
        X1, Y1 = P(-294, yy_ + 13)
        d.rounded_rectangle((X0, Y0, X1, Y1), radius=6 * s * SS, fill=(160, 160, 164, 255) if k else (196, 156, 92, 255))
    det = det.resize((w, h), Image.LANCZOS)
    out.alpha_composite(det)
    for k, (txt, yy_) in enumerate((('33', 206), ('45', 240))):
        C.put(out, C.text(txt, 'osw', 20 * s, (24, 24, 26), 700), cx - 322 * s, cy + yy_ * s)
    # шильдик бренда и светодиод
    br = C.text('JARVIS | NHL', 'mont', 22 * s, (196, 186, 170), 800, track=0.22)
    C.put(out, br, cx + 625 * s - br.width, cy + 228 * s - br.height / 2, anchor='tl')
    led = C.radial(int(40 * s), int(40 * s), (255, 120, 40), 230, 1.4)
    C.put(out, led, cx + 625 * s - br.width - 24 * s, cy + 228 * s)
    C.put(out, C.ellipse(int(9 * s), int(9 * s), (255, 190, 120)), cx + 625 * s - br.width - 24 * s, cy + 228 * s)
    _S[key] = (out, (ox, oy))
    return _S[key]


# ─────────────────────────────── пластинка ───────────────────────────────
def _rfield(n):
    key = ('rf', n)
    if key not in _S:
        y, x = np.mgrid[0:n, 0:n].astype(np.float32)
        c = (n - 1) / 2
        _S[key] = (np.hypot(x - c, y - c), np.arctan2(y - c, x - c))
    return _S[key]


def _gaps(R):
    """Радиусы зазоров между тремя дорожками и радиусы начала дорожек."""
    g0, g1 = GROOVE[0] * R, GROOVE[1] * R
    band = (g1 - g0) / 3
    gaps = [g1 - band, g1 - 2 * band]
    starts = [g1 - 0.012 * R, gaps[0] - 0.018 * R, gaps[1] - 0.018 * R]
    return gaps, starts, g0, g1


def _disc(R):
    """Чёрный винил: канавки, вводная дорожка, три дорожки с зазорами, выводная канавка, кромка."""
    key = ('disc', R)
    if key in _S:
        return _S[key]
    n = 2 * R + 4
    r, phi = _rfield(n)
    rng = np.random.default_rng(R)
    gaps, _, g0, g1 = _gaps(R)
    rn = rng.normal(0, 1, int(R * 4) + 8).astype(np.float32)
    rn = np.convolve(rn, np.ones(3) / 3, 'same')
    ri = np.clip((r * 4).astype(np.int32), 0, len(rn) - 1)
    v = 15.5 + 2.6 * np.sin(2 * np.pi * r / 2.3) + 1.6 * rn[ri]
    smooth = (r > g1) | (r < g0)
    for gp in gaps:
        smooth |= np.abs(r - gp) < 0.008 * R
    v = np.where(smooth, 19.0, v)
    v = np.where(r > 0.985 * R, 30 + 26 * np.clip((r - 0.985 * R) / (0.012 * R), 0, 1), v)    # приподнятая кромка
    v = np.where(r > 0.997 * R, 22.0, v)
    alpha = np.clip(R - r + 0.5, 0, 1) * 255
    rgb = np.stack([v, v, v + 1.5], -1)
    _S[key] = _rgba(rgb, alpha)
    return _S[key]


def _sheen(R):
    """Неподвижный блик на канавках — «бабочка» по оси к лампе (лево-верх → право-низ) + холодный отсвет."""
    key = ('sheen', R)
    if key in _S:
        return _S[key]
    n = 2 * R + 4
    r, phi = _rfield(n)
    gaps, _, g0, g1 = _gaps(R)
    ax = math.radians(-135)
    dphi = np.abs((phi - ax + np.pi / 2) % np.pi - np.pi / 2)          # расстояние до оси (по модулю π)
    near = np.cos(phi - ax) > 0                                         # половина «к лампе» ярче
    main = np.exp(-(dphi / 0.30) ** 2)
    core = np.exp(-(dphi / 0.075) ** 2)
    rad = np.clip((r - g0) / (0.06 * R), 0, 1) * np.clip((g1 + 0.03 * R - r) / (0.05 * R), 0, 1)
    tex = 0.62 + 0.38 * np.sin(2 * np.pi * r / 2.3) ** 2
    I = (0.55 * main + 0.55 * core) * rad * tex * np.where(near, 1.0, 0.68)
    gl = np.zeros_like(r)
    for gp in gaps + [g1 + 0.012 * R]:
        gl = np.maximum(gl, np.exp(-((r - gp) / (0.004 * R + 0.8)) ** 2))
    I = I + 0.9 * gl * (0.25 + main) * (r > g0 * 0.98)
    perp = np.abs((phi - ax) % np.pi - np.pi / 2)
    cool = 0.16 * np.exp(-(perp / 0.32) ** 2) * rad * tex
    rim = np.exp(-((r - 0.99 * R) / 1.6) ** 2) * (0.35 + 0.65 * np.clip(np.cos(phi - ax), 0, 1))
    tot = np.clip(I + cool + rim * 0.9, 0, 1.2)
    w_ = np.clip(I + rim, 0, None) / np.maximum(tot, 1e-4)
    col = np.array((255, 238, 214), np.float32) * w_[..., None] + np.array((176, 204, 255), np.float32) * (1 - w_[..., None])
    alpha = np.clip(tot * 175, 0, 255) * (r < R - 0.5)
    _S[key] = _rgba(col, alpha)
    return _S[key]


def _shadow_disc(R):
    key = ('dsh', R)
    if key not in _S:
        _S[key] = C.shadow(C.ellipse(2 * R, 2 * R, (0, 0, 0)), int(R * 0.06) + 6, 0.75)
    return _S[key]


def _ring_text(im, txt, cx, cy, rt, size, col, font='mont', wght=800, track=0.18):
    """Надпись по окружности (по часовой, верх букв — наружу), начиная сверху."""
    f = C.font(font, int(size), wght)
    adv = [f.getlength(ch) + track * size for ch in txt]
    tot = sum(adv)
    a = -math.pi / 2 - (tot / rt) / 2
    for ch, w in zip(txt, adv):
        mid = a + (w / 2) / rt
        if ch != ' ':
            g = C.text(ch, font, size, col, wght, trim=False)
            g = g.rotate(-math.degrees(mid) - 90, Image.BICUBIC, expand=True)
            C.put(im, g, cx + rt * math.cos(mid), cy + rt * math.sin(mid))
        a += w / rt


def _label(tm, side, Rl):
    """Наклейка-«яблоко»: кольцо цвета клуба с надписью по кругу, кремовая середина (эмблема — отдельно, стоит прямо)."""
    key = ('label', tm.name, side, Rl)
    if key in _S:
        return _S[key]
    SS = 3
    n = 2 * Rl + 2
    big = Image.new('RGBA', (n * SS, n * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    c = fresh.club(tm)
    cc = n * SS / 2
    d.ellipse((cc - Rl * SS, cc - Rl * SS, cc + Rl * SS, cc + Rl * SS), fill=c + (255,))
    ri = Rl * 0.76
    d.ellipse((cc - ri * SS, cc - ri * SS, cc + ri * SS, cc + ri * SS), fill=PAPER + (255,))
    d.ellipse((cc - ri * SS, cc - ri * SS, cc + ri * SS, cc + ri * SS), outline=C.mix(c, (0, 0, 0), 0.25) + (255,), width=2 * SS)
    ro = Rl * 0.965
    tc = _on(c)
    d.ellipse((cc - ro * SS, cc - ro * SS, cc + ro * SS, cc + ro * SS), outline=tc + (110,), width=SS)
    words = '%s · НХЛ · СТОРОНА %s · ' % (tm.up, 'А' if side == 'h' else 'Б')
    size = Rl * 0.13 * SS
    rt = Rl * 0.875 * SS
    f = C.font('mont', int(size), 800)
    one = sum(f.getlength(ch) + 0.18 * size for ch in words)
    reps = max(1, int(2 * math.pi * rt / one))
    _ring_text(big, (words * reps).rstrip(' ·'), cc, cc, rt, size, tc)
    # мелкий штрих — чтобы вращение было видно даже на однотонном кольце
    for k in range(4):
        a = math.pi / 2 + k * math.pi / 2 + 0.3
        x1, y1 = cc + ri * 1.03 * SS * math.cos(a), cc + ri * 1.03 * SS * math.sin(a)
        d.ellipse((x1 - 2 * SS, y1 - 2 * SS, x1 + 2 * SS, y1 + 2 * SS), fill=tc + (160,))
    im = big.resize((n, n), Image.LANCZOS)
    # лёгкая бумажная фактура и объём
    r, phi = _rfield(n)
    arr = np.asarray(im, np.float32).copy()
    sh = 1 + 0.10 * np.cos(phi + math.radians(135)) * np.clip(r / Rl, 0, 1)
    arr[..., :3] *= sh[..., None]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
    _S[key] = im
    return im


def _emb_fit(tm, box):
    box = int(box)
    key = ('emb', tm.name, box)
    if key not in _S:
        e = tm.emb(box)
        _S[key] = C.fit(e, box, box) if max(e.size) > box else e
    return _S[key]


# ─────────────────────────────── тонарм ───────────────────────────────
def _arm(s):
    """Тонарм вдоль +x, ось — в точке pivot спрайта; игла — (ARM_L·s, 0) от оси. → (arm, shadow, pivot)."""
    key = ('arm', s)
    if key in _S:
        return _S[key]
    SS = 3
    L = ARM_L * s
    x0, x1, hh = -150 * s, L + 60 * s, 62 * s
    pad = int(30 * s)
    w, h = int(x1 - x0) + 2 * pad, int(2 * hh) + 2 * pad
    pv = (pad - x0, pad + hh)
    big = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)

    def P(x, y):
        return ((pv[0] + x) * SS, (pv[1] + y) * SS)

    def rect(xa, ya, xb, yb, col, r=0):
        A, B = P(xa, ya), P(xb, yb)
        d.rounded_rectangle((A[0], A[1], B[0], B[1]), radius=r * SS, fill=col)

    # противовес — цилиндр полосами
    cw0, cw1, cr = -146 * s, -62 * s, 30 * s
    bands = [(0.0, (70, 70, 74)), (0.25, (150, 150, 156)), (0.42, (226, 226, 230)), (0.55, (170, 170, 176)),
             (0.8, (90, 90, 96)), (1.0, (50, 50, 54))]
    for k in range(len(bands) - 1):
        ya = -cr + 2 * cr * bands[k][0]
        yb = -cr + 2 * cr * bands[k + 1][0]
        rect(cw0, ya, cw1, yb + 0.5, bands[k][1] + (255,))
    rect(cw0 - 4 * s, -cr * 0.8, cw0, cr * 0.8, (40, 40, 44, 255))
    for xx in (-128, -110, -92):
        A, B = P(xx * s, -cr), P(xx * s, cr)
        d.line((A[0], A[1], B[0], B[1]), fill=(60, 60, 64, 200), width=max(1, int(1.2 * s * SS)))
    # трубка
    t0, t1, tr = -62 * s, L - 92 * s, 7.5 * s
    rect(t0, -tr, t1, tr, (120, 120, 126, 255), tr)
    rect(t0, -tr * 0.75, t1, -tr * 0.05, (214, 214, 220, 255), tr * 0.4)
    rect(t0, -tr * 0.55, t1, -tr * 0.32, (250, 250, 252, 255), tr * 0.2)
    rect(t0, tr * 0.45, t1, tr, (84, 84, 90, 255), tr * 0.4)
    # карданный узел
    A = P(0, 0)
    for rr, col in ((30, (30, 30, 32)), (26, (190, 190, 196)), (19, (110, 110, 116)), (10, (40, 40, 44))):
        d.ellipse((A[0] - rr * s * SS, A[1] - rr * s * SS, A[0] + rr * s * SS, A[1] + rr * s * SS), fill=col + (255,))
    rect(-8 * s, -40 * s, 8 * s, -24 * s, (170, 170, 176, 255), 3 * s)
    # головка (повёрнута на −22° к трубке) с картриджем и подъёмным язычком
    ang = math.radians(-22)
    ca, sa = math.cos(ang), math.sin(ang)

    def hp(u_, v_):
        return P(L + u_ * ca - v_ * sa, 0 + u_ * sa + v_ * ca)

    poly = [hp(-104 * s, -19 * s), hp(14 * s, -19 * s), hp(22 * s, -10 * s), hp(22 * s, 19 * s), hp(-104 * s, 19 * s)]
    d.polygon([(a, b) for a, b in poly], fill=(26, 26, 28, 255))
    d.line([poly[0], poly[1], poly[2]], fill=(150, 150, 156, 255), width=max(1, int(2 * s * SS)))
    cart = [hp(-58 * s, -13 * s), hp(10 * s, -13 * s), hp(10 * s, 13 * s), hp(-58 * s, 13 * s)]
    d.polygon(cart, fill=(196, 156, 92, 255))
    cart2 = [hp(-52 * s, -9 * s), hp(4 * s, -9 * s), hp(4 * s, 9 * s), hp(-52 * s, 9 * s)]
    d.polygon(cart2, fill=(46, 40, 34, 255))
    lift = [hp(-10 * s, 19 * s), hp(4 * s, 19 * s), hp(10 * s, 46 * s), hp(-2 * s, 48 * s)]
    d.polygon(lift, fill=(190, 190, 196, 255))
    # переход трубки в головку
    A, B = P(L - 96 * s, 0), hp(-100 * s, 0)
    d.line((A[0], A[1], B[0], B[1]), fill=(170, 170, 176, 255), width=int(13 * s * SS))
    arm = big.resize((w, h), Image.LANCZOS)
    m = arm.getchannel('A').filter(ImageFilter.GaussianBlur(5 * s))
    shd = Image.new('RGBA', (w, h), (0, 0, 0, 255))
    shd.putalpha(m.point(lambda v: int(v * 0.62)))
    _S[key] = (arm, shd, pv)
    return _S[key]


# ─────────────────────────────── бумага и конверты ───────────────────────────────
def _paper(w, h, col=PAPER, seed=3):
    rng = np.random.default_rng(seed)
    v = 1 + rng.normal(0, 0.018, (h, w)).astype(np.float32) + _smooth_noise(h, w, 70, rng, 0.022)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    e = np.minimum(np.minimum(xx, yy), np.minimum(w - 1 - xx, h - 1 - yy))
    v *= 1 - 0.10 * np.clip(1 - e / 26, 0, 1) ** 2
    return v[..., None] * np.array(col, np.float32)


def _wear(arr, S, cx, cy, k=0.06):
    """Потёртость от пластинки внутри конверта — светлое кольцо."""
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot(xx - cx, yy - cy)
    ring = np.exp(-((r - S * 0.455) / (S * 0.012)) ** 2) + 0.35 * np.exp(-((r - S * 0.17) / (S * 0.01)) ** 2)
    arr += ring[..., None] * k * 255 * (0.6 + 0.4 * np.sin(np.arctan2(yy - cy, xx - cx) * 3 + 1)[..., None])
    return arr


def _front(tm, side, S, mode='big'):
    """Лицевая сторона конверта в цветах клуба. mode: 'big' (видна верхняя часть 630 px), 'sq' (квадрат целиком),
    'plain' (без эмблемы и имени — под наклейку прогноза)."""
    key = ('front', tm.name, side, S, mode)
    if key in _S:
        return _S[key]
    rng = np.random.default_rng(len(tm.name) * 7 + S)
    c = fresh.club(tm)
    c0 = tuple(tm.c0)
    dark = C.mix(c, (0, 0, 0), 0.45)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    k = np.clip((xx * 0.4 + yy) / (1.4 * S), 0, 1)[..., None]
    arr = np.array(c, np.float32) * (1 - k) + np.array(dark, np.float32) * k
    vis = 630 / 940 * S if mode in ('big', 'plain') else S
    ex, ey = S * 0.5, (vis * 0.43 if mode == 'big' else S * 0.40 if mode == 'sq' else vis * 0.5)
    r = np.hypot(xx - ex, yy - ey)
    rings = (np.sin(r / (S * 0.0105) * 2 * np.pi) > 0.86) & (r > S * 0.22) & (r < S * 0.9)
    tc = np.array(_on(c), np.float32)
    arr = np.where(rings[..., None], arr * 0.86 + tc * 0.14, arr)
    if c0 != c and max(c0) - min(c0) > 40:
        band = (yy > vis * 0.80) & (yy < vis * 0.80 + S * 0.018)
        arr = np.where(band[..., None], np.array(c0, np.float32) * 0.5 + arr * 0.5, arr)
    arr *= (1 + rng.normal(0, 0.012, (S, S)).astype(np.float32))[..., None]
    arr = _wear(arr, S, S * 0.5, S * 0.5, 0.035)
    # глянец ламинации — широкая диагональная полоса
    g = np.exp(-(((xx - yy * 0.55) - S * 0.18) / (S * 0.22)) ** 2) * 0.10
    arr = arr + g[..., None] * 255
    e = np.minimum(np.minimum(xx, yy), np.minimum(S - 1 - xx, S - 1 - yy))
    arr = arr * (1 - 0.18 * np.clip(1 - e / 10, 0, 1))[..., None] + 30 * np.clip(1 - np.abs(e - 2) / 2, 0, 1)[..., None]
    im = _F(arr).convert('RGBA')
    on = _on(c)
    if mode != 'plain':
        disc_r = S * (0.215 if mode == 'big' else 0.25)
        C.put(im, C.ellipse(int(disc_r * 2), int(disc_r * 2), PAPER), ex, ey)
        ring = Image.new('RGBA', (int(disc_r * 2 + 40), int(disc_r * 2 + 40)), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((6, 6, ring.width - 7, ring.height - 7), outline=on + (150,), width=3)
        C.put(im, ring, ex, ey)
        eb = disc_r * 1.45
        C.put(im, C.with_shadow(_emb_fit(tm, eb), 10, 0.35, 6), ex, ey)
        nm_size = S * (0.094 if mode == 'big' else 0.105)
        nm = C.text(tm.up, 'unb', nm_size, on, 900, max_w=S * 0.88)
        ny = vis * 0.885 if mode == 'big' else S * 0.83
        C.put(im, nm, S / 2, ny)
        role = 'ХОЗЯЕВА' if side == 'h' else 'ГОСТИ'
        rl = C.text(role, 'mont', S * (0.029 if mode == 'big' else 0.042), on, 800, track=0.24)
        C.put(im, rl, S * 0.05, S * 0.05, anchor='tl')
        bd = int(S * (0.095 if mode == 'big' else 0.13))
        badge = Image.new('RGBA', (bd * 3, bd * 3), (0, 0, 0, 0))
        ImageDraw.Draw(badge).ellipse((3, 3, bd * 3 - 4, bd * 3 - 4), outline=on + (230,), width=7)
        badge = badge.resize((bd, bd), Image.LANCZOS)
        C.put(badge, C.text('А' if side == 'h' else 'Б', 'prata', bd * 0.56, on, 400), bd / 2, bd / 2 + 1)
        C.put(im, badge, S - S * 0.05 - bd / 2, S * 0.05 + bd / 2 - S * 0.008)
    m = C.rrect(S, S, 6, (255, 255, 255)).getchannel('A')
    im.putalpha(m)
    _S[key] = im
    return im


def _sleeve_shadow(S):
    key = ('ssh', S)
    if key not in _S:
        _S[key] = C.shadow(C.rrect(S, S, 6, (0, 0, 0)), 22, 0.7)
    return _S[key]


def _sweep(h):
    key = ('sweep', h)
    if key not in _S:
        bw = 420
        x = np.linspace(-1, 1, bw, dtype=np.float32)
        a = np.exp(-(x / 0.42) ** 2) * 70 + np.exp(-(x / 0.08) ** 2) * 50
        al = np.repeat(a[None, :], h, 0)
        im = _rgba(np.full((h, bw, 3), 255, np.float32), al)
        im = im.transform((bw + int(h * 0.45), h), Image.AFFINE, (1, -0.45, 0, 0, 1, 0), Image.BILINEAR)
        _S[key] = im
    return _S[key]


# ─────────────────────────────── ролик ───────────────────────────────
class Vinyl(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 73, drop=21 * 60 / 73, line=None, team=7,
                 bridge=2, hold=5, cta=3, lag=-0.75, seed=23, **kw):
        super().__init__(u, drop + lag * u, seed)
        self.line = tuple(line) if line else None
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef = league, when, coef
        self.tag = F.tag(league)
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
        self.rec = {'h': sh or {}, 'a': sa or {}}
        self.s = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.team_n = team
        self.T1 = self.b(-(2 * team + bridge))
        if self.T1 < 2.4:
            raise ValueError('мало времени до дропа для интро')
        self.T2 = self.b(-(team + bridge))
        self.TB = self.b(-bridge)
        self.TC = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = self.T1 - 0.5
        self.key = (home, away, league, when, pick, coef, self.line, seed)
        self.PAN = 0.32
        self._build()

    # ── заготовки (до форка) ──
    def _build(self):
        _table()
        _light()
        _plinth(CAM_T[2])
        _plinth(CAM_P[2])
        _arm(CAM_T[2])
        _arm(CAM_P[2])
        self.RT, self.RP = int(R0 * CAM_T[2]), int(R0 * CAM_P[2])
        for R in (self.RT, self.RP):
            _disc(R)
            _sheen(R)
            _shadow_disc(R)
        for side in ('h', 'a'):
            tm = self.tm(side)
            _label(tm, side, int(self.RT * LAB_K))
            _front(tm, side, SLV_S, 'big')
            _front(tm, side, 420, 'sq')
            self._back(side)
        _label(self.fav, self.side, int(self.RP * LAB_K))
        _front(self.fav, self.side, SLV_S, 'plain')
        _sleeve_shadow(SLV_S)
        _sleeve_shadow(420)
        _sweep(SLV_S)
        self._intro_els()
        self._pick_els()
        self.handle_im = self._handle()
        self.plate = C.tg_plate(960, 170, font='mont')
        rng = np.random.default_rng(self.seed)
        self.motes = [(rng.uniform(40, 760), rng.uniform(260, 1100), rng.uniform(6, 15), rng.uniform(0, 6.3),
                       rng.uniform(0.15, 0.45), rng.uniform(-1, 1)) for _ in range(30)]
        self.rows_h = {}

    def tm(self, side):
        return self.h if side == 'h' else self.a

    def _handle(self):
        t = C.text(C.HANDLE, 'mont', 44, CREAM, 800, track=0.03)
        return C.with_shadow(t, 10, 0.75, 2)

    # ── оборот конверта: трек-лист ──
    def _back(self, side):
        """→ (бумага RGBA, слой текста RGBA, центры строк, центры колонок)."""
        key = ('back', self.key, side)
        if key in _S:
            return _S[key]
        S = SLV_S
        tm = self.tm(side)
        s = self.s[side]
        arr = _paper(S, S, PAPER, 7 if side == 'h' else 9)
        arr = _wear(arr, S, S * 0.5, S * 0.5, -0.03)
        paper = _F(arr).convert('RGBA')
        paper.putalpha(C.rrect(S, S, 6, (255, 255, 255)).getchannel('A'))
        im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        X0, X1 = 52, S - 52
        L = 'А' if side == 'h' else 'Б'
        # имя и сторона
        nm = C.text(tm.up, 'prata', 84, INK, 400, track=0.03, max_w=X1 - X0 - 120, stroke=1, stroke_fill=INK)
        C.put(im, nm, X0, 64 - nm.height / 2, anchor='tl')
        bd = 88
        badge = Image.new('RGBA', (bd * 3, bd * 3), (0, 0, 0, 0))
        ImageDraw.Draw(badge).ellipse((4, 4, bd * 3 - 5, bd * 3 - 5), outline=RUST + (255,), width=8)
        badge = badge.resize((bd, bd), Image.LANCZOS)
        C.put(badge, C.text(L, 'prata', 50, RUST, 400), bd / 2, bd / 2 + 1)
        C.put(im, badge, X1 - bd / 2, 62)
        role = 'ХОЗЯЕВА' if side == 'h' else 'ГОСТИ'
        stk = streak_txt(self.rec[side].get('streak'))
        rl = C.text(role + (' · ' + stk if stk else ''), 'mont', 27, RUST, 800, track=0.14, max_w=X1 - X0 - 120)
        C.put(im, rl, X0 + 2, 126 - rl.height / 2, anchor='tl')
        C.put(im, Image.new('RGBA', (X1 - X0, 3), INK + (150,)), X0, 158, anchor='tl')
        # строки — последние игры
        rows = []
        g = s['games']
        right = X1 - 76                                            # правый край счёта (дальше — фишка В/П)
        dd = ImageDraw.Draw(im)
        for k, x in enumerate(g):
            y = 210 + 94 * k
            rows.append(y)
            num = C.text('%s%d' % (L, k + 1), 'osw', 44, RUST, 700)
            C.put(im, num, X0, y - num.height / 2, anchor='tl')
            sc = C.text(x['score'], 'osw', 62, INK, 700)
            nt = C.text(x['note'], 'mont', 26, RUST, 800) if x['note'] else None
            sx = right - sc.width - (nt.width + 8 if nt else 0)
            C.put(im, sc, sx, y - sc.height / 2, anchor='tl')
            if nt:
                C.put(im, nt, right - nt.width, y - sc.height / 2, anchor='tl')
            ox = X0 + 78
            op = C.text(x['opp'], 'mont', 46, INK, 800, max_w=sx - ox - 60)
            C.put(im, op, ox, y - 20 - op.height / 2, anchor='tl')
            sub = x['date']
            if x['home'] is not None:
                sub = (sub + ' · ' if sub else '') + ('дома' if x['home'] else 'в гостях')
            if sub:
                st = C.text(sub, 'mont', 27, MUTED, 600)
                C.put(im, st, ox + 2, y + 24 - st.height / 2, anchor='tl')
            xx = ox + op.width + 22                                # точки-«лидер» до счёта
            while xx < sx - 22:
                dd.ellipse((xx - 2.2, y - 9, xx + 2.2, y - 4.6), fill=INK + (120,))
                xx += 15
            ch = C.rrect(58, 58, 13, WIN if x['res'] == 'В' else LOSS if x['res'] == 'П' else MUTED)
            C.put(ch, C.text(x['res'] or '?', 'mont', 36, CREAM, 900), 29, 30)
            C.put(im, ch, X1 - 29, y)
        ry = (210 + 94 * len(g) - 30) if g else 190
        C.put(im, Image.new('RGBA', (X1 - X0, 3), INK + (150,)), X0, ry, anchor='tl')
        # колонки: очки / место / шайбы
        items = []
        if s['points'] is not None:
            sub = ('за %d %s' % (s['gp'], plural(s['gp'], 'матч', 'матча', 'матчей'))) if s['gp'] is not None else ''
            items.append(('ОЧКИ', '%d' % s['points'], sub, INK))
        if s['place'] is not None:
            items.append(('МЕСТО', '%d' % s['place'], s['place_scope'] or '', INK))
        if s['gd'] is not None:
            gf, ga = self.rec[side].get('gf'), self.rec[side].get('ga')
            sub = ('забито %s, пропущено %s' % (gf, ga)) if gf is not None and ga is not None else ''
            items.append(('ШАЙБЫ ±', F.gd_txt(s['gd']), sub, WIN if s['gd'] > 0 else LOSS if s['gd'] < 0 else INK))
        cols = []
        if items:
            n = len(items)
            cw = (X1 - X0) / n
            top = ry + 14
            for k, (lab, v, sub, col) in enumerate(items):
                x = X0 + cw * k + cw / 2
                C.put(im, C.text(lab, 'mont', 25, RUST, 800, track=0.16), x, top + 26)
                C.put(im, C.text(v, 'osw', 84, col, 700), x, top + 92)
                if sub:
                    C.put(im, C.text(sub, 'mont', 24, MUTED, 600, max_w=cw - 20), x, top + 154)
                if k:
                    C.put(im, Image.new('RGBA', (2, 150), INK + (90,)), X0 + cw * k, top + 12, anchor='tl')
                cols.append((x, top + 92))
        _S[key] = (paper, im, rows, cols)
        return _S[key]

    # ── интро ──
    def _intro_els(self):
        e = {}
        e['tag'] = C.text(self.tag, 'mont', 30, AMBER, 800, track=0.3)
        e['when'] = C.text(self.when.upper(), 'unb', 44, CREAM, 700, max_w=980)
        for side in ('h', 'a'):
            tm = self.tm(side)
            e['name_' + side] = C.text(tm.up, 'unb', 50, CREAM, 800, max_w=480)
            e['role_' + side] = C.text('ХОЗЯЕВА' if side == 'h' else 'ГОСТИ', 'mont', 26, AMBER, 800, track=0.26)
            e['halo_' + side] = C.radial(760, 760, fresh.bright(fresh.club(tm), 0.25), 120, 1.8)
        if self.line:
            e['ot'] = C.text('ОСНОВНОЕ ВРЕМЯ', 'mont', 27, (214, 196, 170), 800, track=0.26)
            pw, ph = 300, 212
            plates = []
            for lab, v in zip(('П1', 'Х', 'П2'), self.line):
                p = C.rrect(pw, ph, 26, (246, 236, 216))
                inner = Image.new('RGBA', (pw * 2, ph * 2), (0, 0, 0, 0))
                ImageDraw.Draw(inner).rounded_rectangle((22, 22, pw * 2 - 23, ph * 2 - 23), radius=36, outline=RUST + (200,), width=4)
                p.alpha_composite(inner.resize((pw, ph), Image.LANCZOS))
                C.put(p, C.text(lab, 'mont', 34, RUST, 800, track=0.14), pw / 2, 56)
                C.put(p, C.text(C.fmt_k(v), 'unb', 82, INK, 900, max_w=pw - 40), pw / 2, 138)
                plates.append(C.with_shadow(p, 16, 0.6, 10))
            e['plates'] = plates
        self.IE = e

    # ── прогноз ──
    def _pick_els(self):
        w = 900
        f1 = C.text(self.pick1, 'unb', 84, INK, 900)
        two = f1.width > (w - 90) / 0.78 and ' ' in self.pick1
        if two:
            a_, b_ = self.pick1.split(' ', 1)
            l1 = [C.text(a_, 'unb', 80, INK, 900, max_w=w - 90), C.text(b_, 'unb', 80, INK, 900, max_w=w - 90)]
        else:
            l1 = [C.text(self.pick1, 'unb', 84, INK, 900, max_w=w - 90)]
        l2 = C.text(self.pick2, 'mont', 38, RUST, 800, track=0.14, max_w=w - 120) if self.pick2 else None
        pill = None
        if self.coef:
            kl = C.text('КЭФ', 'mont', 34, AMBER, 800, track=0.2)
            kv = C.text(C.fmt_k(self.coef), 'unb', 70, CREAM, 900)
            pw = kl.width + kv.width + 110
            pill = C.rrect(pw, 118, 59, INK)
            C.put(pill, kl, 40 + kl.width / 2, 60)
            C.put(pill, kv, pw - 40 - kv.width / 2, 60)
        hgt = 40 + sum(98 for _ in l1) + (60 if l2 else 0) + (150 if pill else 10) + 20
        st = C.rrect(w, hgt, 40, (247, 239, 221))
        brd = Image.new('RGBA', (w * 2, hgt * 2), (0, 0, 0, 0))
        ImageDraw.Draw(brd).rounded_rectangle((26, 26, w * 2 - 27, hgt * 2 - 27), radius=56, outline=RUST + (220,), width=5)
        ImageDraw.Draw(brd).rounded_rectangle((42, 42, w * 2 - 43, hgt * 2 - 43), radius=44, outline=RUST + (120,), width=2)
        st.alpha_composite(brd.resize((w, hgt), Image.LANCZOS))
        y = 40
        for im in l1:
            C.put(st, im, w / 2, y + 49)
            y += 98
        if l2:
            C.put(st, l2, w / 2, y + 26)
            y += 60
        if pill:
            C.put(st, pill, w / 2, y + 75)
        st = st.rotate(2.0, Image.BICUBIC, expand=True)
        self.sticker = C.with_shadow(st, 18, 0.55, 12)

    # ── геометрия тонарма ──
    def _theta(self, r, s):
        """Угол тонарма (экранный, градусы, y вниз) при игле на радиусе r пластинки, масштаб s."""
        px, py = PIV[0] * s, PIV[1] * s
        L = ARM_L * s
        d = math.hypot(px, py)
        beta = math.atan2(-py, -px)
        cd = (L * L + d * d - r * r) / (2 * L * d)
        return math.degrees(beta - math.acos(max(-1.0, min(1.0, cd))))

    def _draw_arm(self, fr, cam, th, lift, dx=0.0, dy=0.0):
        cx, cy, s = cam
        arm, shd, pv = _arm(s)
        px, py = cx + PIV[0] * s + dx, cy + PIV[1] * s + dy
        so = (10 + 22 * lift) * s, (14 + 30 * lift) * s
        ims, p2 = _rot_about(shd, -th, pv)
        C.put(fr, ims, px + so[0] - p2[0], py + so[1] - p2[1], 1.0 - 0.35 * lift, anchor='tl')
        ima, p2 = _rot_about(arm, -th, pv)
        C.put(fr, ima, px - p2[0], py - p2[1], anchor='tl')

    # ── пластинка на экране ──
    def _draw_record(self, fr, tm, side, cx, cy, R, ang, a=1.0, sc=1.0, lab_z=1.0, spin=True, stylus=None, shadow=True):
        Rl = int(R * LAB_K)
        disc, sheen = _disc(R), _sheen(R)
        lab = _label(tm, side, Rl)
        if sc != 1.0:
            disc, sheen = C.scale(disc, sc), C.scale(sheen, sc)
        if shadow:
            shd = _shadow_disc(R)
            if sc != 1.0:
                shd = C.scale(shd, sc)
            C.put(fr, shd, cx + 8 * sc, cy + 16 * sc + (sc - 1) * 120, a * 0.95)
        C.put(fr, disc, cx, cy, a)
        if stylus is not None and a > 0.5:                              # «играет» — тёплая тонкая линия на канавке
            self._groove_glow(fr, cx, cy, R * sc, stylus * sc, 0.55 * a)
        C.put(fr, sheen, cx, cy, a)
        # наклейка крутится (с лёгким смазом), эмблема стоит
        lz = lab_z * sc
        labs = lab if abs(lz - 1) < 0.003 else C.scale(lab, lz)
        if spin:
            acc = None
            for k, da in enumerate((-2.0, 0.0, 2.0)):
                rr = labs.rotate(-(ang + da), Image.BICUBIC)
                acc = np.asarray(rr, np.float32) if acc is None else acc + np.asarray(rr, np.float32)
            labr = Image.fromarray((acc / 3).astype(np.uint8), 'RGBA')
        else:
            labr = labs.rotate(-ang, Image.BICUBIC)
        C.put(fr, labr, cx, cy, a)
        eb = _emb_fit(tm, Rl * 0.76 * 1.42)
        if abs(lz - 1) > 0.003:
            eb = _emb_fit(tm, Rl * 0.76 * 1.42 * lz)
        C.put(fr, eb, cx, cy, a)
        # пылинки на виниле крутятся вместе с пластинкой
        for k in range(5):
            rr = R * sc * (0.62 + 0.07 * k)
            aa = math.radians(ang + k * 73 + 20)
            C.put(fr, _mote(6), cx + rr * math.cos(aa), cy + rr * math.sin(aa), 0.45 * a)

    def _groove_glow(self, fr, cx, cy, R, rs, k):
        key = ('gg', int(R))
        n = 2 * int(R) + 4
        r, _ = _rfield(n)
        al = np.clip(1 - np.abs(r - rs) / 2.2, 0, 1) * 150 * k
        al += np.exp(-((r - rs) / 9.0) ** 2) * 40 * k
        col = np.empty((n, n, 3), np.float32)
        col[...] = (255, 200, 130)
        C.put(fr, _rgba(col, al), cx, cy)

    # ── время: вращение ──
    def _ang_team(self, t, T):
        """Угол пластинки клуба (сцена с T): с посадки на диск (T+u) разгон 0,3 с; у гостей в мосту — замедление."""
        tl = T + self.u
        if t <= tl:
            return 0.0
        ramp = 0.3

        def run(tt):
            x = tt - tl
            return OM * x * x / (2 * ramp) if x < ramp else OM * (x - ramp / 2)
        if t <= self.TB or T != self.T2:
            return run(t)
        ts = self.drop - 0.5 * self.u
        a0 = run(self.TB)
        sp = OM * (ts - self.TB) / 3
        p = C.seg(t, self.TB, ts)
        return a0 + sp * (1 - (1 - p) ** 3)

    # ── рисование сцен ──
    def _bg(self):
        return _table().copy()

    def _motes(self, fr, t, k=1.0):
        for x, y, d, ph, sp, dr in self.motes:
            xx = x + 40 * math.sin(t * sp + ph) + dr * 12 * t
            yy = y - 18 * t * sp + 25 * math.cos(t * sp * 0.7 + ph)
            tw = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * 1.7 + ph * 3))
            C.put(fr, _mote(int(d)), xx, yy, 0.55 * tw * k)

    def _intro(self, fr, t, dy=0.0):
        e = self.IE
        u = self.u
        T1 = self.T1
        beat0 = T1 - 4 * u
        q = C.out_cubic(C.seg(t, 0, 0.55))
        for side, x0 in (('h', 280), ('a', 800)):
            tm = self.tm(side)
            dx = (-1 if side == 'h' else 1) * (1 - q) * 640
            pulse = 0.0
            for n in range(1, 4):
                tb = beat0 + n * u
                if t >= tb:
                    pulse = max(pulse, (1 - C.seg(t, tb, tb + 0.5)) ** 2)
            C.put(fr, e['halo_' + side], x0 + dx, 650 + dy, 0.75 + 0.25 * pulse)
            ang = OM * 0.75 * t + (0 if side == 'h' else 140) - (1 - q) * 260 * (1 if side == 'h' else -1)
            self._draw_record(fr, tm, side, x0 + dx, 650 + dy, self.RT, ang, 1.0)
            a = C.out_cubic(C.seg(t, beat0, beat0 + 0.3))
            C.put(fr, e['role_' + side], x0, 936 + dy + (1 - a) * 16, a)
            C.put(fr, e['name_' + side], x0, 990 + dy + (1 - a) * 22, a)
        a = C.out_cubic(C.seg(t, 0.0, 0.35))
        C.put(fr, e['tag'], W / 2, 272 + dy - (1 - a) * 14, a)
        C.put(fr, e['when'], W / 2, 336 + dy - (1 - a) * 14, a)
        if self.line:
            tb = beat0 + u
            a = C.out_cubic(C.seg(t, tb - 0.2, tb + 0.1))
            C.put(fr, e['ot'], W / 2, 1086 + dy, a)
            for k, p in enumerate(e['plates']):
                t0 = tb + 0.09 * k
                if t < t0:
                    continue
                z = C.out_back(C.seg(t, t0, t0 + 0.32), 2.2)
                pi = C.scale(p, 0.82 + 0.18 * z)
                C.put(fr, pi, 225 + 315 * k, 1238 + dy, C.seg(t, t0, t0 + 0.08))

    def _team_state(self, t):
        """Какая команда на корпусе и её сцена: (side, T, Tend)."""
        if t < self.T2:
            return 'h', self.T1, self.T2
        return 'a', self.T2, self.TB

    def _arm_team(self, t, side, T, Tend):
        """(угол, подъём) тонарма в сцене клуба; Tend — конец сцены (для гостей — начало моста)."""
        u = self.u
        R = self.RT
        s = CAM_T[2]
        rest = 90.0
        _, starts, _, _ = _gaps(R)
        g = self.s[side]['games']
        n = max(1, len(g))
        rs = [starts[min(k, 2)] for k in range(n)]
        hover = self._theta(rs[0] + 6, s)
        if t < T + u:
            return rest, 0.0, None
        if t < T + 2 * u - 0.12:
            lift = C.seg(t, T + u, T + u + 0.1)
            th = C.lerp(rest, hover, C.in_out(C.seg(t, T + u + 0.06, T + 2 * u - 0.16)))
            return th, lift, None
        # игла на дорожке
        k = 0
        for j in range(1, n):
            if t >= T + (2 + j) * u - 0.1:
                k = j
        r = rs[k]
        if k > 0:
            ta = T + (2 + k) * u - 0.1
            p = C.in_out(C.seg(t, ta, ta + 0.2))
            r = C.lerp(rs[k - 1] - 0.4 * u * 6, rs[k], p)
            lift = math.sin(math.pi * p) * 0.6
        else:
            lift = 1 - C.seg(t, T + 2 * u - 0.12, T + 2 * u)
        tk = T + (2 + k) * u
        r -= max(0.0, t - tk) * 6 * (1 if k < n - 1 else 0.7)
        th = self._theta(r, s)
        tl = Tend - 0.36 if side == 'h' else self.TB
        if t >= tl:
            lift = max(lift, C.seg(t, tl, tl + 0.09))
            d = 0.32 if side == 'h' else 0.6
            th = C.lerp(th, rest, C.in_out(C.seg(t, tl + 0.05, tl + 0.05 + d)))
            return th, lift, None
        return th, lift, (r if lift < 0.2 else None)

    def _team(self, fr, t, dy=0.0):
        """Сцены клубов и мост (корпус в общем плане)."""
        u = self.u
        cx, cy, s = CAM_T
        side, T, Tend = self._team_state(t)
        pl, (ox, oy) = _plinth(s)
        C.put(fr, pl, cx + ox, cy + oy + dy, anchor='tl')
        R = self.RT
        bridge = t >= self.TB
        swap = (side == 'h' and t >= Tend - 0.36)
        # ── пластинка ──
        tm = self.tm(side)
        th, lift, stylus = self._arm_team(t, side, T, Tend)
        if t >= T + 0.4 * u:
            p = C.in_out(C.seg(t, T + 0.4 * u, T + u))
            ry = C.lerp(SLV_Y + R + 40, cy, p)
            sc = 1.0 + 0.035 * math.sin(math.pi * p)
            a = 1.0
            rx = cx
            if t >= T + u:                                              # посадка — лёгкая отдача
                sc = 1.0 + 0.012 * (1 - C.seg(t, T + u, T + u + 0.18)) * math.sin(C.seg(t, T + u, T + u + 0.18) * math.pi)
            if swap:
                q = C.in_cubic(C.seg(t, Tend - 0.36, Tend))
                rx -= 1150 * q
                sc = 1.0 + 0.04 * q
            if bridge:
                ts = self.drop - 0.5 * u
                q = C.seg(t, ts, self.drop - 0.1)
                sc = 1.0 + 0.10 * C.out_cubic(q)
                ry -= 70 * C.out_cubic(q)
                a = 1 - q
            if a > 0.01:
                self._draw_record(fr, tm, side, rx, ry + dy, R, self._ang_team(t, T), a, sc, 1.0, True,
                                  stylus=stylus)
        # ── тонарм ──
        self._draw_arm(fr, CAM_T, th, lift, 0, dy)
        # ── конверт ──
        self._sleeve_team(fr, t, side, T, Tend, dy)
        if bridge:
            self._bridge_sleeves(fr, t)

    def _sleeve_team(self, fr, t, side, T, Tend, dy):
        u = self.u
        S = SLV_S
        x, y = SLV_X, SLV_Y + dy
        if side == 'a' and t < T + 0.36:                                # ящик: конверт гостей въезжает справа
            q = C.in_cubic(C.seg(t, T - 0.36, T))
            x += 1150 * (1 - q) if t < T else 0
        if side == 'a' and t >= self.TB:                                # мост: уезжает вниз
            y += 900 * C.in_cubic(C.seg(t, self.TB, self.TB + 0.3))
            if y > H:
                return
        if side == 'h' and t >= Tend - 0.36:
            x -= 1150 * C.in_cubic(C.seg(t, Tend - 0.36, Tend))
            if side == 'h' and t >= Tend - 0.36:                        # одновременно въезжает конверт гостей
                self._sleeve_team(fr, t + 0.0, 'a', self.T2, self.TB, dy) if False else None
        fl0, fl1 = T + 2 * u - 0.16, T + 2 * u + 0.16
        back, rows, cols = self._back(side)
        front = _front(self.tm(side), side, S, 'big')
        C.put(fr, _sleeve_shadow(S), x + S / 2 + 8, y + S / 2 + 16, anchor='c')
        if t < fl0:
            im = front
        elif t < fl1:
            q = C.seg(t, fl0, fl1)
            k = abs(math.cos(math.pi * q))
            im = front if q < 0.5 else self._back_lit(side, t, T)
            ww = max(2, int(S * k))
            im = im.resize((ww, S), Image.BILINEAR)
            C.put(fr, im, x + (S - ww) / 2, y, anchor='tl')
            return
        else:
            im = self._back_lit(side, t, T)
        C.put(fr, im, x, y, anchor='tl')
        # блик глянца на лицевой стороне при въезде
        if t < fl0:
            t0 = T + 0.1 if side == 'h' else T
            p = C.seg(t, t0, t0 + 0.75)
            if 0 < p < 1:
                sw = _sweep(S)
                bx = x - sw.width + p * (S + sw.width)
                x0c, x1c = max(x, bx), min(x + S, bx + sw.width)
                if x1c > x0c:
                    part = sw.crop((int(x0c - bx), 0, int(x1c - bx), S))
                    C.put(fr, part, x0c, y, 0.9, anchor='tl')

    def _back_lit(self, side, t, T):
        """Трек-лист с подсветкой текущей строки (по долям) и акцентом на колонках."""
        u = self.u
        paper, ink, rows, cols = self._back(side)
        im = paper.copy()
        n = len(rows)
        if n:
            k = -1
            for j in range(n):
                if t >= T + (2 + j) * u:
                    k = j
            if k >= 0:
                ta = T + (2 + k) * u
                fade = 1.0
                if t >= T + (2 + n) * u:
                    fade = 1 - C.seg(t, T + (2 + n) * u, T + (2 + n) * u + 0.3)
                if fade > 0.01:
                    p = C.out_cubic(C.seg(t, ta, ta + 0.18))
                    y_prev = rows[k - 1] if k > 0 else rows[0]
                    yc = C.lerp(y_prev, rows[k], p)
                    pulse = 1 + 0.5 * (1 - C.seg(t, ta, ta + 0.35))
                    C.put(im, self._bar(), SLV_S / 2, yc, min(1.0, 0.7 * pulse) * fade)
        if cols:
            ta = T + 5 * u
            if t >= ta:
                p = 1 - C.seg(t, ta, ta + 0.6)
                if p > 0:
                    for x, y in cols:
                        C.put(im, self._glow_dot(), x, y, p)
        im.alpha_composite(ink)
        return im

    def _bar(self):
        key = ('bar',)
        if key not in _S:
            _S[key] = C.rrect(SLV_S - 70, 90, 20, (255, 196, 110), 150)
        return _S[key]

    def _glow_dot(self):
        key = ('gdot',)
        if key not in _S:
            _S[key] = C.radial(300, 200, (255, 190, 100), 150, 1.4)
        return _S[key]

    def _bridge_sleeves(self, fr, t):
        u = self.u
        D = self.drop
        for k, (side, x) in enumerate((('h', 285), ('a', 795))):
            t0 = self.TB + 0.12 + 0.08 * k
            if t < t0:
                continue
            p = C.out_back(C.seg(t, t0, t0 + 0.38), 1.3)
            y = 1080 + (1 - p) * 700
            q = C.in_cubic(C.seg(t, D - 0.2, D))
            y += q * 800
            im = _front(self.tm(side), side, 420, 'sq')
            C.put(fr, _sleeve_shadow(420), x + 8, y + 14)
            C.put(fr, im, x, y)

    # ── прогноз и финал ──
    def _pick(self, fr, t):
        u = self.u
        D, TC = self.drop, self.TC
        cx, cy, s = CAM_P
        up = 150 * C.out_cubic(C.seg(t, TC, TC + 0.42))
        cy -= up
        pl, (ox, oy) = _plinth(s)
        C.put(fr, pl, cx + ox, cy + oy, anchor='tl')
        R = self.RP
        p = C.seg(t, D, D + 0.16)
        sc = 1 + 0.14 * (1 - C.out_cubic(p))
        lz = 1 + 0.28 * C.out_back(C.seg(t, D + 0.06, D + 0.5), 2.0)
        for n in range(1, 8):
            tb = self.b(n)
            if t >= tb:
                lz += 0.05 * (1 - C.seg(t, tb, tb + 0.3)) ** 2
        r_st = 0.935 * R - (t - D) * 5
        lift = 0.0 if t >= D + 0.07 else 0.6 * (1 - C.seg(t, D, D + 0.07))
        self._draw_record(fr, self.fav, self.side, cx, cy, R, OM * (t - D) + 30, 1.0, sc, lz, True,
                          stylus=r_st if lift < 0.2 else None)
        self._draw_arm(fr, (cx, cy, s), self._theta(r_st, s), lift)
        # конверт клуба и наклейка с прогнозом
        S = SLV_S
        sy = 952 - up
        q = C.seg(t, D, D + 0.18)
        slide = (1 - C.out_cubic(q)) * 260
        C.put(fr, _sleeve_shadow(S), W / 2 + 8, sy + S / 2 + 16 + slide)
        C.put(fr, _front(self.fav, self.side, S, 'plain'), SLV_X, sy + slide, anchor='tl')
        st = self.sticker
        z = 1 + 0.22 * (1 - C.out_back(C.seg(t, D, D + 0.24), 1.6))
        for n in range(1, 5):
            tb = self.b(n)
            if t >= tb:
                z += 0.025 * (1 - C.seg(t, tb, tb + 0.28)) ** 2
        z *= 1 - 0.1 * C.out_cubic(C.seg(t, TC, TC + 0.42))
        sty = sy + 205 + st.height / 2 - 60 + slide * 0.4
        sty -= 30 * C.out_cubic(C.seg(t, TC, TC + 0.42))
        C.put(fr, C.scale(st, z), W / 2, sty)
        return (cx, cy, R * sc, r_st * sc)

    def _pulses(self, arr, t, geo):
        """Световой импульс из канавки на дроп и на каждую долю — волна расходится от пластинки."""
        cx, cy, R, rs = geo
        D, u = self.drop, self.u
        waves = []
        for n in range(0, 5):
            tb = self.b(n)
            if tb <= t < tb + 1.0:
                waves.append((t - tb, 1.0 if n == 0 else 0.42))
        if not waves:
            return arr
        col = np.array(fresh.bright(fresh.club(self.fav), 0.45), np.float32) * 0.6 + np.array((255, 200, 130), np.float32) * 0.4
        rmax = R + 620
        x0, x1 = int(max(0, cx - rmax)), int(min(W, cx + rmax))
        y0, y1 = int(max(0, cy - rmax)), int(min(H, cy + rmax))
        key = ('pf', int(cx), int(cy))
        if key not in _S:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            _S[key] = (np.hypot(xx - cx, yy - cy), np.arctan2(yy - cy, xx - cx))
        rf, pf = _S[key]
        rf, pf = rf[y0:y1, x0:x1], pf[y0:y1, x0:x1]
        acc = np.zeros(rf.shape, np.float32)
        for age, k in waves:
            e = C.out_cubic(age / 1.0)
            rr = rs + (R + 560 - rs) * e
            wv = rr + 9 * np.sin(pf * 14 + age * 9) * (0.4 + e)
            wd = 6 + 26 * e
            acc += np.clip(1 - np.abs(rf - wv) / wd, 0, 1) ** 2 * (1 - e) ** 1.4 * k * 0.95
            acc += np.exp(-((rf - rs) / (5 + 10 * age)) ** 2) * (rf < R) * (1 - C.seg(age, 0, 0.6)) * k * 1.1
        if acc.max() < 0.01:
            return arr
        sub = arr[y0:y1, x0:x1].astype(np.float32)
        sub += acc[..., None] * col
        arr[y0:y1, x0:x1] = np.clip(sub, 0, 255).astype(np.uint8)
        return arr

    # ── кадр ──
    def frame(self, t):
        u, D = self.u, self.drop
        fr = self._bg()
        geo = None
        if t < self.T1 - self.PAN:
            self._intro(fr, t)
        elif t < self.T1:
            q = C.in_out(C.seg(t, self.T1 - self.PAN, self.T1))
            self._intro(fr, t, -1300 * q)
            self._team(fr, self.T1, 1300 * (1 - q))
        elif t < D:
            self._team(fr, t)
        else:
            geo = self._pick(fr, t)
        self._motes(fr, t, 0.6 if t < D else 0.9)
        arr = np.asarray(fr.convert('RGB'))
        lm = _light()
        k = 1.0
        if self.TB <= t < D:
            k = 1 - 0.24 * C.in_out(C.seg(t, self.TB, D - 0.05))
        if k < 0.999:
            arr = ((arr.astype(np.uint32) * lm) * int(k * 256)) >> 16
        else:
            arr = (arr.astype(np.uint16) * lm) >> 8
        arr = np.minimum(arr, 255).astype(np.uint8)
        if geo is not None:
            arr = self._pulses(arr, t, geo)
            if t < D + 0.22:
                f = (1 - C.seg(t, D, D + 0.22)) ** 1.5 * 0.62
                arr = (arr + (np.array((255, 236, 206), np.float32) - arr) * f).astype(np.uint8)
        out = Image.fromarray(arr, 'RGB')
        # @jarvibet — одинаково во всех сценах; на финале его заменяет плашка Telegram
        ha = 1.0 if t < self.TC else 1 - C.seg(t, self.TC, self.TC + 0.22)
        if ha > 0.01:
            im = self.handle_im if ha > 0.997 else C.fade(self.handle_im, ha)
            _paste(out, im, W / 2, HANDLE_Y)
        if t >= self.TC:
            q = C.out_cubic(C.seg(t, self.TC + 0.05, self.TC + 0.45))
            if q > 0:
                y = 1330 + (1 - q) * 420
                _paste(out, self.plate, W / 2, y)
        return out
