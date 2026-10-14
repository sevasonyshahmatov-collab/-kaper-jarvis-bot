"""Общие детали баннеров post6 / pre6 / day6 (14.10.2026): холст 1080×1350 × quality.S, шрифты, клубы, градиенты,
свечения, тени. Координаты в коде — базовые (1080×1350), умножаются на S внутри хелперов."""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import brand_kit
import nhl
import poster
import quality

S = quality.S
W, H = 1080, 1350
FONTS = {'osw': 'Oswald[wght].ttf', 'alumni': 'AlumniSans[wght].ttf', 'man': 'Manrope[wght].ttf',
         'unb': 'Unbounded[wght].ttf', 'mono': 'JetBrainsMono[wght].ttf', 'play': 'PlayfairDisplay-Regular.ttf',
         'playi': 'PlayfairDisplay-Italic.ttf', 'prata': 'Prata-Regular.ttf', 'hand': 'Caveat[wght].ttf',
         'russo': 'RussoOne-Regular.ttf', 'mont': 'Montserrat[wght].ttf', 'robc': 'RobotoCondensed[wght].ttf',
         'tek': 'Tektur[wdth,wght].ttf', 'dela': 'DelaGothicOne-Regular.ttf', 'pixel': 'PressStart2P-Regular.ttf',
         'yeseva': 'YesevaOne-Regular.ttf', 'kelly': 'KellySlab-Regular.ttf'}
KHL_ABBR = {'Авангард': 'АВГ', 'Автомобилист': 'АВТ', 'Адмирал': 'АДМ', 'Ак Барс': 'АКБ', 'Амур': 'АМР', 'Барыс': 'БАР',
            'Динамо Москва': 'ДИН', 'Динамо Минск': 'ДМН', 'Лада': 'ЛАД', 'Локомотив': 'ЛОК', 'Металлург': 'ММГ',
            'Нефтехимик': 'НХК', 'Салават Юлаев': 'СЮЛ', 'Северсталь': 'СЕВ', 'Сибирь': 'СИБ', 'СКА': 'СКА', 'Сочи': 'СОЧ',
            'Спартак': 'СПР', 'Торпедо': 'ТОР', 'Трактор': 'ТРК', 'ЦСКА': 'ЦСК', 'Шанхайские Драконы': 'ШАН'}
_F = {}


def font(name, size, wght=700):
    key = (name, int(size * S), wght)
    if key not in _F:
        _F[key] = brand_kit.font(FONTS[name], int(size * S), wght)
    return _F[key]


def fit(text, name, size, max_w, wght=700, min_size=10):
    """Шрифт размера ≤ size, при котором текст влезает в max_w (базовые px)."""
    s = size
    while s > min_size:
        f = font(name, s, wght)
        if f.getlength(text) <= max_w * S:
            return f
        s -= max(1, s // 30)
    return font(name, min_size, wght)


def league_of(*teams):
    return 'NHL' if any(t in nhl.TEAMS for t in teams) else 'KHL'


def prep(league):
    if league.upper() == 'NHL':
        nhl.register()


def short(team):
    return poster.SHORT.get(team, team)


def abbr(team):
    if team in nhl.TEAMS:
        return nhl.TEAMS[team][3]
    return KHL_ABBR.get(team, team[:3].upper())


def color(team):
    return tuple(poster.BANNER.get(team, poster.TEAMS.get(team, (None, (120, 120, 130)))[1]))


def color2(team):
    return tuple(poster.TEAMS.get(team, (None, None, (30, 30, 34)))[2])


def mix(c, k):
    t = (255, 255, 255) if k > 0 else (0, 0, 0)
    return tuple(int(a + (b - a) * abs(k)) for a, b in zip(c, t))


def emblem(team, size, sticker=False):
    """Эмблема размера size (базовые px): sticker — с белой «наклейкой»."""
    if sticker:
        return poster._emblem(team, int(size * S))
    return poster._raw_emblem(team, int(size * S), int(size * S))


def canvas(col=(0, 0, 0)):
    return Image.new('RGBA', (W * S, H * S), tuple(col) + (255,))


def vgrad(w, h, stops):
    """Вертикальный градиент (базовые размеры) по [(0..1, rgb)], RGBA ×S."""
    hh = int(h * S)
    t = np.linspace(0, 1, hh, dtype=np.float32)
    cols = np.stack([np.interp(t, [p for p, _ in stops], [c[i] for _, c in stops]) for i in range(3)], -1)
    arr = np.broadcast_to(cols[:, None, :], (hh, int(w * S), 3)).astype(np.uint8)
    return Image.fromarray(np.ascontiguousarray(arr), 'RGB').convert('RGBA')


def glow_blob(img, cx, cy, r, col, a=0.35):
    """Мягкое цветное пятно света (базовые координаты)."""
    n = 256
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    d = np.hypot(x - n / 2, y - n / 2) / (n / 2)
    al = (np.clip(1 - d, 0, 1) ** 2 * 255 * a).astype(np.uint8)
    tile = Image.new('RGBA', (n, n), tuple(col) + (0,))
    tile.putalpha(Image.fromarray(al, 'L'))
    tile = tile.resize((int(2 * r * S), int(2 * r * S)), Image.BICUBIC)
    img.alpha_composite(tile, (int((cx - r) * S), int((cy - r) * S)))


def noise(img, k=6, seed=3):
    a = np.asarray(img.convert('RGB')).astype(np.int16)
    a += np.random.default_rng(seed).integers(-k, k + 1, a.shape[:2], dtype=np.int16)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')


def put(img, im, cx, cy, anchor='mm'):
    """Вставить im (размер уже ×S) по базовым координатам: anchor 'mm' центр, 'lt' левый верх, 'rm' правый центр…"""
    x, y = cx * S, cy * S
    ax, ay = anchor[0], anchor[1]
    x -= {'l': 0, 'm': im.width / 2, 'r': im.width}[ax]
    y -= {'t': 0, 'm': im.height / 2, 'b': im.height}[ay]
    img.alpha_composite(im, (int(x), int(y)))


def text(d, xy, s, f, fill, anchor='mm', **kw):
    """Текст по базовым координатам; цифры — «строчные» (lnum), где шрифт умеет (Playfair рисует 0 как «о»)."""
    try:
        d.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill, anchor=anchor, features=['lnum'], **kw)
    except (KeyError, ValueError, OSError):                       # без libraqm — как есть
        d.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill, anchor=anchor, **kw)


def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle([v * S for v in box], radius=r * S, fill=fill, outline=outline, width=int(width * S) if outline else 0)


def shadow(img, box, r, blur=24, a=150, dy=14):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle([box[0] * S, (box[1] + dy) * S, box[2] * S, (box[3] + dy) * S], radius=r * S,
                                          fill=(0, 0, 0, a))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur * S)))


def glow_text(img, xy, s, f, col, blur=14, k=2.0, anchor='mm', core=(255, 255, 255)):
    """Неоновый текст: размытая цветная подложка + ядро."""
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((xy[0] * S, xy[1] * S), s, font=f, fill=tuple(col) + (255,), anchor=anchor)
    g = lay.filter(ImageFilter.GaussianBlur(blur * S))
    g.putalpha(g.getchannel('A').point(lambda v: min(255, int(v * k))))
    img.alpha_composite(g)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(max(1, S))))
    ImageDraw.Draw(img).text((xy[0] * S, xy[1] * S), s, font=f, fill=core, anchor=anchor)


def fmt_k(k):
    return '%.2f' % k if k else ''


def fmt_odds(k):
    """1.91 → «1,91» (для подписей на русском)."""
    return ('%.2f' % k).replace('.', ',') if k else ''


def save(img, path, grain=4):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    out = noise(img, grain) if grain else img
    out.convert('RGB').save(path, quality=93, optimize=True)
    return path
