# -*- coding: utf-8 -*-
"""Общий движок серии роликов «reels» (Shorts / Клипы 1080×1920, 30 к/с).

Каждый формат — класс-наследник Reel с методом frame(t) → RGB/RGBA 1080×1920 (кадр зависит только от t,
поэтому кадры считаются параллельно на всех ядрах). Время сцен — в долях трека: u — доля (сцена-такт берёт
1 или 2 доли трека, см. track_sync), drop — время дропа в ролике. render() пишет два файла:
  *_preview.mp4 — с отрезком трека (только для проверки синхронности; в репозиторий треки не кладём);
  *_clean.mp4   — без музыки (тихая дорожка) — для загрузки, трек добавляется в редакторе Shorts/VK;
  *_cover.jpg   — обложка (кадр cover_t).
"""
import math
import multiprocessing
import os
import random
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

import nhl
import nhl_kit
import poster

W, H, FPS = 1080, 1920, 30
SAFE_TOP, SAFE_BOT = 230, 1480          # выше/ниже — интерфейс площадки (шапка, подпись, кнопки)
HANDLE = '@jarvibet'
# @jarvibet у низа безопасной зоны в шаблонах — выключен (владелец 19.10: мешает бегущей строке «МАТЧИ ДНЯ»; вернуть —
# REELS_HANDLE_BOTTOM=1). Плашки Telegram в финале роликов это не трогает.
HANDLE_BOTTOM = os.environ.get('REELS_HANDLE_BOTTOM', '0') == '1'
TG_BLUE = (42, 171, 238)
FD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts')

FONTS = {
    'unb': 'Unbounded[wght].ttf', 'osw': 'Oswald[wght].ttf', 'mont': 'Montserrat[wght].ttf', 'monti': 'Montserrat-Italic[wght].ttf',
    'manrope': 'Manrope[wght].ttf', 'onest': 'Onest[wght].ttf', 'golos': 'GolosText[wght].ttf', 'rubik': 'Rubik[wght].ttf',
    'rubiki': 'Rubik-Italic[wght].ttf', 'russo': 'RussoOne-Regular.ttf', 'mono': 'JetBrainsMono[wght].ttf',
    'prata': 'Prata-Regular.ttf', 'corm': 'CormorantGaramond-Italic[wght].ttf', 'tenor': 'TenorSans-Regular.ttf',
    'tek': 'Tektur[wdth,wght].ttf', 'exo': 'Exo2[wght].ttf', 'exoi': 'Exo2-Italic[wght].ttf', 'robc': 'RobotoCondensed[wght].ttf',
    'robci': 'RobotoCondensed-Italic[wght].ttf', 'play': 'PlayfairDisplay-Regular.ttf', 'playi': 'PlayfairDisplay-Italic.ttf',
    'pixel': 'PressStart2P-Regular.ttf', 'hand': 'Caveat[wght].ttf', 'dela': 'DelaGothicOne-Regular.ttf',
    'rmono': 'RubikMonoOne-Regular.ttf',
}
_FC, _TC = {}, {}


# ─────────────────────────────── шрифты и текст ───────────────────────────────
def font(name, size, wght=700, wdth=None):
    key = (name, int(size), wght, wdth)
    if key not in _FC:
        ft = ImageFont.truetype(os.path.join(FD, FONTS[name]), int(size))
        try:
            vals = []
            for ax in ft.get_variation_axes():
                n = ax.get('name', b'')
                n = n.decode() if isinstance(n, bytes) else str(n)
                if n.lower().startswith('weight'):
                    vals.append(max(ax['minimum'], min(ax['maximum'], wght)))
                elif n.lower().startswith('width'):
                    vals.append(ax['default'] if wdth is None else max(ax['minimum'], min(ax['maximum'], wdth)))
                else:
                    vals.append(ax['default'])
            if vals:
                ft.set_variation_by_axes(vals)
        except Exception:
            pass
        _FC[key] = ft
    return _FC[key]


EMOJI_FONT = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'


def is_emoji(ch):
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or o in (0x200D, 0xFE0F, 0x2B50, 0x2B55)


def emoji(s, size):
    """Цветные эмодзи (Noto Color Emoji рисуется только кеглем 109 — потом масштаб)."""
    key = ('emoji', s, int(size))
    if key not in _TC:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        w = int(f.getlength(s)) + 8
        im = Image.new('RGBA', (w, 136), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4, 4), s, font=f, embedded_color=True)
        bb = im.getbbox()
        im = im.crop(bb) if bb else im
        k = size / 109
        _TC[key] = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    return _TC[key]


ICONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons')
LOTTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lottie')


def icon(name, size, fill=(255, 255, 255), weight='bold'):
    """Иконка Phosphor (MIT, render/reels/icons/<имя>-<bold|fill|duotone>.svg; владелец 20.10) — RGBA size×size.
    Нужен cairosvg (в Actions ставится); без него — пустой слой, ролик не падает."""
    key = ('icon', name, int(size), tuple(fill), weight)
    if key not in _TC:
        try:
            import cairosvg
            with open(os.path.join(ICONS, '%s-%s.svg' % (name, weight)), encoding='utf-8') as f:
                svg = f.read().replace('currentColor', '#%02x%02x%02x' % tuple(fill[:3]))
            import io
            _TC[key] = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=int(size),
                                                              output_height=int(size)))).convert('RGBA')
        except (ImportError, OSError) as e:
            print('icon %s: %s' % (name, e), flush=True)
            _TC[key] = Image.new('RGBA', (int(size), int(size)), (0, 0, 0, 0))
    return _TC[key]


def icon_text(name, im, size, fill, gap=14, weight='bold'):
    """Иконка слева от готовой надписи im, по центру строки."""
    ic = icon(name, size, fill, weight)
    out = Image.new('RGBA', (ic.width + gap + im.width, max(ic.height, im.height)), (0, 0, 0, 0))
    out.alpha_composite(ic, (0, (out.height - ic.height) // 2))
    out.alpha_composite(im, (ic.width + gap, (out.height - im.height) // 2))
    return out


class Lottie:
    """Анимация LottieFiles (Lottie Simple License; render/reels/lottie/<имя>.json; владелец 20.10) через rlottie.
    frame(t, size) — RGBA кадр на время t от начала (с; дальше последнего кадра — последний кадр, loop=True — по кругу)."""

    def __init__(self, name, loop=False):
        from rlottie_python import LottieAnimation
        self.anim = LottieAnimation.from_file(os.path.join(LOTTIE, name + '.json'))
        self.n = self.anim.lottie_animation_get_totalframe()
        self.fps = self.anim.lottie_animation_get_framerate() or 30
        self.dur = self.n / self.fps
        self.loop = loop
        self._c = {}

    def frame(self, t, size):
        i = int(max(0.0, t) * self.fps)
        i = i % self.n if self.loop else min(i, self.n - 1)
        key = (i, int(size))
        if key not in self._c:
            self._c[key] = self.anim.render_pillow_frame(frame_num=i, width=int(size), height=int(size)).convert('RGBA')
        return self._c[key]


def text(s, name, size, fill=(255, 255, 255), wght=700, track=0.0, max_w=None, stroke=0, stroke_fill=(0, 0, 0),
         outline=False, trim=True, wdth=None, a=255):
    """Строка текста → RGBA (кеш). track — разрядка в долях кегля; max_w — ужать кегль до ширины;
    outline — только контур толщиной stroke; trim — обрезать по видимым пикселям (для точного центрирования).
    Эмодзи внутри строки рисуются цветными."""
    key = (s, name, int(size), tuple(fill), wght, track, max_w, stroke, tuple(stroke_fill), outline, trim, wdth, a)
    if key in _TC:
        return _TC[key]
    if any(is_emoji(c) for c in s):
        parts, cur, em = [], '', None
        for c in s:
            e = is_emoji(c)
            if em is None or e == em:
                cur += c
            else:
                parts.append((cur, em))
                cur = c
            em = e
        parts.append((cur, em))
        ims = []
        for seg_, e in parts:
            if e:
                ims.append(emoji(seg_, size * 0.95))
            elif seg_.strip():
                lead = seg_[0] == ' '
                tail = seg_[-1] == ' '
                im = text(seg_.strip(), name, size, fill, wght, track, None, stroke, stroke_fill, outline, True, wdth, a)
                sp = int(size * 0.28)
                pad = Image.new('RGBA', (im.width + sp * lead + sp * tail, im.height), (0, 0, 0, 0))
                pad.alpha_composite(im, (sp * lead, 0))
                ims.append(pad)
            else:
                ims.append(Image.new('RGBA', (int(size * 0.28), 2), (0, 0, 0, 0)))
        hh = max(i.height for i in ims)
        out = Image.new('RGBA', (sum(i.width for i in ims) + 4 * (len(ims) - 1), hh), (0, 0, 0, 0))
        x = 0
        for i in ims:
            out.alpha_composite(i, (x, (hh - i.height) // 2))
            x += i.width + 4
        if max_w and out.width > max_w:
            out = out.resize((int(max_w), max(1, int(out.height * max_w / out.width))), Image.LANCZOS)
        _TC[key] = out
        return out
    size = int(size)
    while True:
        f = font(name, size, wght, wdth)
        if track:
            ws = [f.getlength(c) for c in s]
            tw = sum(ws) + track * size * max(0, len(s) - 1)
        else:
            tw = f.getlength(s)
        if not max_w or tw <= max_w or size <= 16:
            break
        size = max(16, int(size * max_w / tw * 0.995))
    asc, desc = f.getmetrics()
    pad = int(size * 0.25) + stroke + 2
    im = Image.new('RGBA', (int(math.ceil(tw)) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = tuple(fill)[:3] + (a,)
    kw = dict(font=f)
    if stroke:
        kw.update(stroke_width=stroke, stroke_fill=tuple(stroke_fill)[:3] + (a,) if not outline else col)
    fl = (0, 0, 0, 0) if outline else col
    if track:
        x = pad
        for c, w in zip(s, ws):
            d.text((x, pad), c, fill=fl, **kw)
            x += w + track * size
    else:
        d.text((pad, pad), s, fill=fl, **kw)
    if trim:
        bb = im.getchannel('A').getbbox()
        if bb:
            # по вертикали обрезаем по метрикам шрифта (строки одной высоты стоят ровно), по горизонтали — по пикселям
            top = pad + max(0, int(asc - size * 0.78)) - stroke
            bot = pad + asc + stroke + 1
            im = im.crop((bb[0], max(0, min(top, bb[1])), bb[2], max(bot, bb[3])))
    _TC[key] = im
    return im


def lines(words, name, size, max_w, fill=(255, 255, 255), wght=700, gap=0.12, align='c', track=0.0, max_lines=3):
    """Перенос по словам в max_w; если слов слишком много — кегль уменьшается. → RGBA блок."""
    while True:
        f = font(name, size, wght)
        rows, cur = [], ''
        for w in words.split():
            t = (cur + ' ' + w).strip()
            if f.getlength(t) * (1 + track) <= max_w or not cur:
                cur = t
            else:
                rows.append(cur)
                cur = w
        if cur:
            rows.append(cur)
        for k in range(len(rows) - 1):                       # предлог/союз в конце строки — на следующую
            ws = rows[k].split()
            if len(ws) > 1 and len(ws[-1]) <= 2:
                rows[k] = ' '.join(ws[:-1])
                rows[k + 1] = ws[-1] + ' ' + rows[k + 1]
        if len(rows) <= max_lines or size < 30:
            break
        size = int(size * 0.9)
    ims = [text(r, name, size, fill, wght, track, max_w=max_w) for r in rows]
    lh = int(size * (1 + gap))
    out = Image.new('RGBA', (max(i.width for i in ims), lh * (len(ims) - 1) + ims[-1].height), (0, 0, 0, 0))
    for k, im in enumerate(ims):
        x = 0 if align == 'l' else (out.width - im.width) // 2 if align == 'c' else out.width - im.width
        out.alpha_composite(im, (x, k * lh))
    return out


# ─────────────────────────────── время и плавность ───────────────────────────────
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def seg(t, a, b):
    """0..1 на отрезке [a, b]."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return clamp((t - a) / (b - a))


def out_expo(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def in_cubic(x):
    x = clamp(x)
    return x ** 3


def in_out(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def out_back(x, s=1.4):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def lerp(a, b, k):
    return a + (b - a) * k


def mix(c1, c2, k):
    return tuple(int(round(lerp(a, b, k))) for a, b in zip(c1, c2))


def window(t, a, b, fi=0.2, fo=0.2):
    """Прозрачность «видно на [a, b)» с проявлением fi и угасанием fo."""
    if t < a or t >= b:
        return 0.0
    k = 1.0
    if fi:
        k = min(k, seg(t, a, a + fi))
    if fo:
        k = min(k, 1 - seg(t, b - fo, b))
    return k


def text2(s, name, size, fill=(255, 255, 255), wght=700, max_w=None, k=0.8, gap=0.16, **kw):
    """Строка, а если в max_w кеглем size не помещается — две сбалансированные строки кеглем size·k (владелец 19.10:
    длинный прогноз не мельчить). → (картинка, на сколько она выше однострочной)."""
    one = text(s, name, size, fill, wght, max_w=max_w, **kw)
    if not max_w or ' ' not in s.strip() or text(s, name, size, fill, wght, **kw).width <= max_w:
        return one, 0
    w = s.split()
    i = min(range(1, len(w)), key=lambda j: max(len(' '.join(w[:j])), len(' '.join(w[j:]))))
    r1, r2 = (text(x, name, size * k, fill, wght, max_w=max_w, **kw) for x in (' '.join(w[:i]), ' '.join(w[i:])))
    g = int(size * k * gap)
    im = Image.new('RGBA', (max(r1.width, r2.width), r1.height + g + r2.height), (0, 0, 0, 0))
    im.alpha_composite(r1, ((im.width - r1.width) // 2, 0))
    im.alpha_composite(r2, ((im.width - r2.width) // 2, r1.height + g))
    return im, max(0, im.height - one.height)


# ─────────────────────────────── картинки ───────────────────────────────
def put(dst, im, cx, cy, a=1.0, anchor='c'):
    """Наложить im на dst центром (anchor='c') или левым верхним углом ('tl'), с прозрачностью a; можно за край."""
    if im is None or a <= 0.003:
        return dst
    if a < 0.997:
        im = fade(im, a)
    x = int(round(cx - im.width / 2)) if anchor == 'c' else int(round(cx))
    y = int(round(cy - im.height / 2)) if anchor == 'c' else int(round(cy))
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(dst.width, x + im.width), min(dst.height, y + im.height)
    if x1 <= x0 or y1 <= y0:
        return dst
    if (x0, y0, x1, y1) != (x, y, x + im.width, y + im.height):
        im = im.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    dst.alpha_composite(im, (x0, y0))
    return dst


def fade(im, a):
    if a >= 0.997:
        return im
    im = im.copy()
    im.putalpha(im.getchannel('A').point(lambda v, a=a: int(v * a)))
    return im


def scale(im, s, resample=Image.BILINEAR):
    if abs(s - 1) < 0.002:
        return im
    return im.resize((max(1, int(round(im.width * s))), max(1, int(round(im.height * s)))), resample)


def fit(im, w, h, resample=Image.LANCZOS):
    k = min(w / im.width, h / im.height)
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), resample)


def rotate(im, deg):
    if abs(deg) < 0.05:
        return im
    return im.rotate(deg, Image.BICUBIC, expand=True)


def tint(im, col, k=1.0):
    """Перекрасить непрозрачные пиксели в col (k — доля перекраски)."""
    flat = Image.new('RGBA', im.size, tuple(col)[:3] + (255,))
    flat.putalpha(im.getchannel('A'))
    return flat if k >= 0.999 else Image.blend(im, flat, k)


def rrect(w, h, r, fill=(255, 255, 255), a=255, outline=None, width=0, ss=2):
    """Скруглённый прямоугольник со сглаживанием."""
    im = Image.new('RGBA', (int(w) * ss, int(h) * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=int(r * ss), fill=tuple(fill)[:3] + (a,) if fill else None,
                        outline=tuple(outline)[:3] + (255,) if outline else None, width=int(width * ss))
    return im.resize((int(w), int(h)), Image.LANCZOS) if ss > 1 else im


def ellipse(w, h, fill=(255, 255, 255), a=255, ss=3):
    im = Image.new('RGBA', (int(w) * ss, int(h) * ss), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((0, 0, im.width - 1, im.height - 1), fill=tuple(fill)[:3] + (a,))
    return im.resize((int(w), int(h)), Image.LANCZOS)


def polygon(pts, size, fill=(255, 255, 255), a=255, ss=3):
    """Многоугольник (координаты в пикселях внутри size) со сглаживанием."""
    im = Image.new('RGBA', (int(size[0]) * ss, int(size[1]) * ss), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon([(x * ss, y * ss) for x, y in pts], fill=tuple(fill)[:3] + (a,))
    return im.resize((int(size[0]), int(size[1])), Image.LANCZOS)


def shadow(im, r=24, a=0.55, col=(0, 0, 0), spread=0):
    """Мягкая тень по форме im (картинка больше на 3r с каждой стороны)."""
    pad = r * 3
    m = Image.new('L', (im.width + 2 * pad, im.height + 2 * pad), 0)
    m.paste(im.getchannel('A'), (pad, pad))
    if spread:
        m = m.filter(ImageFilter.MaxFilter(spread * 2 + 1))
    m = m.filter(ImageFilter.GaussianBlur(r)).point(lambda v: int(v * a))
    out = Image.new('RGBA', m.size, tuple(col) + (255,))
    out.putalpha(m)
    return out


def with_shadow(im, r=22, a=0.5, dy=14, col=(0, 0, 0)):
    sh = shadow(im, r, a, col)
    out = Image.new('RGBA', sh.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, dy) if dy >= 0 else (0, 0))
    out.alpha_composite(im, (r * 3, r * 3))
    return out


def glow(im, r=18, k=1.5, col=None):
    """Свечение вокруг элемента (размытая копия под ним)."""
    pad = r * 3
    big = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(im, (pad, pad))
    g = big if col is None else tint(big, col)
    g = g.filter(ImageFilter.GaussianBlur(r))
    g.putalpha(g.getchannel('A').point(lambda v: min(255, int(v * k))))
    g.alpha_composite(big)
    return g


def add_light(fr, im, cx, cy, k=1.0):
    """Сложить свет (аддитивно): блики, сияние."""
    lay = Image.new('RGB', fr.size, (0, 0, 0))
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    rgb = Image.new('RGB', im.size, (0, 0, 0))
    a = im.getchannel('A')
    if k != 1.0:
        a = a.point(lambda v: min(255, int(v * k)))
    rgb.paste(im.convert('RGB'), (0, 0), a)
    lay.paste(rgb, (x, y))
    out = ImageChops.add(fr.convert('RGB'), lay)
    return out.convert('RGBA') if fr.mode == 'RGBA' else out


def radial(w, h, col, a0=255, power=2.0):
    """Круглое пятно света: col в центре → прозрачность к краю."""
    y, x = np.mgrid[0:h, 0:w]
    d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    al = np.clip(1 - d, 0, 1) ** power * a0
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., :3] = col
    arr[..., 3] = al.astype(np.uint8)
    return Image.fromarray(arr, 'RGBA')


def vgrad(w, h, stops):
    """Вертикальный градиент: stops = [(0, (r,g,b)), (0.5, ...), (1, ...)] → RGB."""
    ys = np.linspace(0, 1, h)
    pos = [s[0] for s in stops]
    cols = np.array([s[1] for s in stops], float)
    ch = [np.interp(ys, pos, cols[:, i]) for i in range(3)]
    arr = np.stack(ch, -1)[:, None, :].repeat(w, 1)
    return Image.fromarray(arr.astype(np.uint8), 'RGB')


def lgrad(w, h, c1, c2, angle=0.0, a1=255, a2=255):
    """Линейный градиент под углом angle (градусы, 0 — слева направо) → RGBA."""
    y, x = np.mgrid[0:h, 0:w].astype(float)
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    p = (x - w / 2) * ca + (y - h / 2) * sa
    span = abs(w / 2 * ca) + abs(h / 2 * sa)
    k = np.clip((p + span) / (2 * span + 1e-6), 0, 1)[..., None]
    c = np.array(c1 + (a1,), float) * (1 - k) + np.array(c2 + (a2,), float) * k
    return Image.fromarray(c.astype(np.uint8), 'RGBA')


def motion_blur(im, dx, dy, n=7):
    """Смаз движения вдоль (dx, dy) — среднее сдвинутых копий."""
    if abs(dx) + abs(dy) < 1.5:
        return im
    pad = int(max(abs(dx), abs(dy))) + 2
    base = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    acc = np.zeros((base.height, base.width, 4), np.float32)
    for k in range(n):
        f = k / (n - 1) - 0.5
        lay = base.copy()
        lay.alpha_composite(im, (int(pad + dx * f), int(pad + dy * f)))
        acc += np.asarray(lay, np.float32)
    return Image.fromarray((acc / n).astype(np.uint8), 'RGBA')


def rgb_split(fr, amt):
    """Расслоение цветов по горизонтали на amt пикселей."""
    if amt < 1:
        return fr
    r, g, b = fr.convert('RGB').split()
    r = ImageChops.offset(r, int(amt), 0)
    b = ImageChops.offset(b, -int(amt), 0)
    return Image.merge('RGB', (r, g, b))


def zoom(fr, z, cx=W / 2, cy=H / 2, dx=0.0, dy=0.0, rot=0.0):
    """Камера: наезд z (>1 — ближе) к точке (cx, cy), сдвиг и наклон."""
    if abs(z - 1) < 0.001 and not dx and not dy and not rot:
        return fr
    z = max(z, 1.0 + 2.2 * max(abs(dx) / fr.width, abs(dy) / fr.height))     # сдвиг без чёрных краёв
    cw, ch = fr.width / z, fr.height / z
    x0 = cx - cw * (cx / fr.width) + dx
    y0 = cy - ch * (cy / fr.height) + dy
    x0, y0 = clamp(x0, 0, fr.width - cw), clamp(y0, 0, fr.height - ch)
    out = fr.resize(fr.size, Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
    if rot:
        out = out.rotate(rot, Image.BILINEAR, expand=False, fillcolor=(0, 0, 0))
    return out


def shake(t, t0, amp=16, d=0.35, f1=83, f2=61):
    """Тряска после удара в t0 → (dx, dy)."""
    if t < t0 or t - t0 >= d:
        return 0.0, 0.0
    k = amp * (1 - (t - t0) / d) ** 2
    return k * math.sin((t - t0) * f1), k * math.cos((t - t0) * f2)


_GRAIN = {}


def grain(fr, t, k=10, size=(W, H)):
    """Плёночное зерно (8 заготовленных кадров по кругу), k — сила."""
    key = (size, k)
    if key not in _GRAIN:
        rnd = np.random.default_rng(7)
        _GRAIN[key] = [(rnd.normal(0, 1, (size[1] // 3 + 1, size[0] // 3 + 1)) * k).astype(np.int16).repeat(3, 0).repeat(3, 1)[:size[1], :size[0]]
                       for _ in range(8)]
    g = _GRAIN[key][int(t * 24) % 8]
    arr = np.asarray(fr.convert('RGB'), np.int16) + g[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')


_VIG = {}


def vignette(fr, k=0.55, power=2.2):
    key = (fr.size, k, power)
    if key not in _VIG:
        w, h = fr.size
        y, x = np.mgrid[0:h, 0:w]
        d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 * 0.8 + ((y - h / 2) / (h / 2)) ** 2)
        _VIG[key] = (1 - k * np.clip(d / 1.25, 0, 1) ** power)[..., None].astype(np.float32)
    arr = np.asarray(fr.convert('RGB'), np.float32) * _VIG[key]
    return Image.fromarray(arr.astype(np.uint8), 'RGB')


def tg_icon(d=150, col=TG_BLUE, plane=(255, 255, 255)):
    """Значок Telegram: круг с бумажным самолётиком."""
    S = 4
    D = d * S
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse((0, 0, D - 1, D - 1), fill=tuple(col) + (255,))
    c, r = D / 2, D / 2
    pt = lambda x, y: (c + x * r, c + y * r)
    dr.polygon([pt(-0.52, 0.02), pt(0.46, -0.40), pt(0.29, 0.44), pt(0.05, 0.24), pt(-0.06, 0.38), pt(-0.11, 0.15)], fill=tuple(plane) + (255,))
    dr.polygon([pt(-0.11, 0.15), pt(0.32, -0.20), pt(0.05, 0.24), pt(-0.06, 0.38)], fill=mix(plane, col, 0.22) + (255,))
    return im.resize((d, d), Image.LANCZOS)


def tg_plate(w=960, h=170, top='TELEGRAM', handle=None, fill=TG_BLUE, top_col=(215, 236, 255), font='mont'):
    """Плашка Telegram (правило владельца 12.10): значок внутри левого края, обе строки текста — ровно по центру плашки
    (значок текст не сдвигает: поле текста симметрично, ширина = w − 2·(отступ значка + значок))."""
    handle = handle or HANDLE
    pl = rrect(w, h, h / 2, fill)
    d = int(h * 0.74)
    pad = (h - d) / 2
    put(pl, tg_icon(d, (255, 255, 255), fill), pad + d / 2, h / 2)
    room = w - 2 * (pad + d + 18)
    t1 = text(top, font, int(h * 0.235), top_col, 800, track=0.25, max_w=room) if top else None
    t2 = text(handle, font, int(h * 0.42), (255, 255, 255), 900, max_w=room)
    if t1 is None:
        put(pl, t2, w / 2, h / 2)
        return pl
    gap = h * 0.03
    y0 = (h - t1.height - gap - t2.height) / 2
    put(pl, t1, w / 2, y0 + t1.height / 2)
    put(pl, t2, w / 2, y0 + t1.height + gap + t2.height / 2)
    return pl


def odds_row(line, w=960, h=190, font='mont', lab_font=None, fill=(255, 255, 255), fill_a=34, val_col=(255, 255, 255),
             lab_col=(190, 196, 210), outline=None, radius=None, gap=24):
    """Линия основного времени П1 · Х · П2 крупными плашками: подпись сверху, кэф крупно. line = (п1, х, п2)."""
    if not line:
        return None
    lab_font = lab_font or font
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    bw = (w - 2 * gap) / 3
    for k, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), line)):
        bx = rrect(bw, h, radius if radius is not None else h * 0.2, fill, fill_a,
                   **({'outline': outline, 'width': 3} if outline else {}))
        put(bx, text(lab, lab_font, int(h * 0.2), lab_col, 800, track=0.15), bw / 2, h * 0.27)
        put(bx, text(fmt_k(v), font, int(h * 0.38), val_col, 900, max_w=bw - 24), bw / 2, h * 0.64)
        put(out, bx, k * (bw + gap), 0, anchor='tl')
    return out


# ─────────────────────────────── клубы ───────────────────────────────
_EMB = {}


class Team:
    def __init__(self, name):
        self.name = name
        self.short = poster.SHORT.get(name, name)
        self.up = self.short.upper()
        self.c1 = tuple(poster.BANNER.get(name, poster.TEAMS[name][1]))
        info = poster.TEAMS.get(name)
        self.c0 = tuple(info[1]) if info else self.c1          # основной цвет клуба (может быть тёмным)
        self.c2 = tuple(info[2]) if info else (20, 20, 24)    # второй цвет

    def emb(self, size, h=None):
        key = (self.name, int(size), int(h or size))
        if key not in _EMB:
            _EMB[key] = poster._raw_emblem(self.name, int(size), int(h or size))
        return _EMB[key]


def match(home, away, league='KHL'):
    if str(league).upper() == 'NHL':
        nhl.register()
    h, a = nhl_kit._prep(home, away)
    return Team(h), Team(a)


def fmt_k(k):
    return ('%.2f' % k) if k is not None else ''


def gen_case(team_short, case):
    """Родительный падеж короткого имени для «победа ...» (как в постерах; без словаря — как есть)."""
    G = {'Трактор': 'Трактора', 'Локомотив': 'Локомотива', 'Авангард': 'Авангарда', 'Ак Барс': 'Ак Барса',
         'Адмирал': 'Адмирала', 'Колорадо': 'Колорадо', 'Оттава': 'Оттавы', 'Айлендерс': 'Айлендерс', 'Барыс': 'Барыса',
         'Сибирь': 'Сибири', 'Лада': 'Лады', 'Северсталь': 'Северстали', 'Монреаль': 'Монреаля', 'Детройт': 'Детройта',
         'Каролина': 'Каролины', 'Вегас': 'Вегаса', 'Бостон': 'Бостона', 'Эдмонтон': 'Эдмонтона', 'Тампа-Бэй': 'Тампы',
         'Динамо Мн': 'Динамо Мн', 'СКА': 'СКА', 'Даллас': 'Далласа', 'Флорида': 'Флориды', 'Анахайм': 'Анахайма'}
    return G.get(team_short, team_short) if case == 'g' else team_short


# ─────────────────────────────── база ролика ───────────────────────────────
class Reel:
    """Наследник задаёт self.dur и frame(t). u — доля трека (с), drop — время дропа в ролике (с)."""
    dur = 15.0
    cover_t = None

    def __init__(self, u=1.0, drop=0.0, seed=7):
        self.u, self.drop = float(u), float(drop)
        self.rnd = random.Random(seed)
        self.seed = seed

    def b(self, n):
        """Время n-й доли от дропа (отрицательные — до дропа)."""
        return self.drop + n * self.u

    def frame(self, t):
        raise NotImplementedError


_R = None


# Нижняя зона под безопасной (ниже SAFE_BOT): плашка Telegram — только в последние FOOTER_END_S секунд (владелец 18.10:
# «из-за неё текст плохо читается — убрать и показывать только в конце»; раньше, 14.10, она стояла весь ролик).
# В конце: затемнение снизу и строка «ссылка на канал — в описании» (у ролика своя плашка Telegram в финале) или,
# если ролик просит footer_plate_to_end, — плашка Telegram. Отключить: REELS_FOOTER=0.
FOOTER = os.environ.get('REELS_FOOTER', '1') != '0'
FOOTER_END_S = 2.5
_FOOT = {}


def _footer_layers():
    if not _FOOT:
        top = SAFE_BOT + 10
        band = Image.new('RGBA', (W, H - top), (0, 0, 0, 0))
        a = np.clip(np.linspace(0, 1, H - top) / 0.28, 0, 1) * 215
        band.putalpha(Image.fromarray(np.repeat(a[:, None], W, axis=1).astype('uint8')))
        plate = tg_plate(w=980, h=200)
        sub = text('ПРОГНОЗЫ НА КХЛ И НХЛ', 'mont', 34, (205, 214, 228), 800, track=0.18, max_w=W - 120)
        last = text('ССЫЛКА НА КАНАЛ — В ОПИСАНИИ', 'mont', 44, (255, 255, 255), 900, track=0.08, max_w=W - 100)
        _FOOT.update(top=top, band=band, plate=plate, sub=sub, last=last)
    return _FOOT


# Бегущая строка на месте плашки (владелец 18.10): весь ролик, кроме последних FOOTER_END_S секунд, сразу под безопасной
# зоной — ярлык «МАТЧИ ДНЯ» и матчи дня бегут влево. Ролик задаёт reel.ticker = ['НХЛ · 19.10', 'Калгари — Каролина 03:00', …];
# нет списка — строки нет.
TICK_Y, TICK_H, TICK_V = SAFE_BOT + 22, 76, 110                        # верх, высота, скорость (px/с)
TICK_X = 110                                                           # отступ ярлыка слева (владелец 18.10: «М» не видно на телефоне; 19.10 — с запасом под увеличенную копию для Instagram)
_TICK = {}


def _ticker_layers(items, label='МАТЧИ ДНЯ'):
    key = (label,) + tuple(items)
    if key not in _TICK:
        _TICK.clear()
        tag = text(label, 'mont', 26, (10, 16, 28), 900, track=0.1)
        tw = tag.width + 36
        sep = '   •   '
        one = text(sep.join(items) + sep, 'mont', 34, (236, 241, 250), 800, track=0.04, trim=False)
        strip = Image.new('RGBA', (one.width * (2 + W // max(1, one.width)), one.height), (0, 0, 0, 0))
        for x in range(0, strip.width, one.width):
            strip.alpha_composite(one, (x, 0))
        band = Image.new('RGBA', (W, TICK_H), (8, 12, 22, 200))
        band.alpha_composite(Image.new('RGBA', (W, 3), (120, 200, 255, 230)), (0, 0))
        box = Image.new('RGBA', (tw, TICK_H), (120, 200, 255, 255))
        put(box, tag, tw / 2, TICK_H / 2)
        _TICK.update(key=key, tw=tw, one=one.width, strip=strip, band=band, box=box)
    return _TICK


def ticker(fr, t, end):
    items = getattr(_R, 'ticker', None)
    if not items or t > end:
        return fr
    L = _ticker_layers(items, getattr(_R, 'ticker_tag', None) or 'МАТЧИ ДНЯ')   # дата — в ярлыке, иначе уезжает под него
    k = min(1.0, t / 0.4, max(0.0, (end - t) / 0.3))                     # появление в начале, уход перед финалом
    lay = Image.new('RGBA', (W, TICK_H), (0, 0, 0, 0))
    lay.alpha_composite(L['band'])
    off = int(max(0.0, t - 2.0) * TICK_V) % L['one']                    # первые 2 с стоит — начало ленты читается
    x0 = TICK_X + L['tw']
    s = L['strip'].crop((off, 0, off + W - x0, L['strip'].height))
    lay.alpha_composite(s, (x0, (TICK_H - s.height) // 2 + 2))
    lay.alpha_composite(L['box'], (TICK_X, 0))
    if k < 1:
        lay.putalpha(lay.getchannel('A').point(lambda v: int(v * k)))
    fr = fr.convert('RGBA')
    fr.alpha_composite(lay, (0, TICK_Y))
    return fr


def footer(fr, t, dur):
    """Нижняя зона кадра — только в конце ролика: затемнение + строка про ссылку (или плашка Telegram). fr — RGB/RGBA W×H."""
    end = dur - FOOTER_END_S
    if t < end:
        return ticker(fr, t, end)
    L = _footer_layers()
    k = min(1.0, (t - end) / 0.3)                                       # плавное появление за 0,3 с
    fr = fr.convert('RGBA')
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    lay.alpha_composite(L['band'], (0, L['top']))
    cy = (L['top'] + H) // 2 + 10
    if getattr(_R, 'footer_plate_to_end', False):                       # у ролика нет своей плашки в финале
        put(lay, L['plate'], W / 2, cy - 22)
        put(lay, L['sub'], W / 2, cy - 22 + 100 + 34)
    else:
        put(lay, L['last'], W / 2, cy)
    if k < 1:
        lay.putalpha(lay.getchannel('A').point(lambda v: int(v * k)))
    fr.alpha_composite(lay)
    return fr


# Поле по краям (владелец 18.10: на телефоне картинка «тютелька в тютельку», как будто чуть больше кадра):
# кадр ужимается до INSET и ставится по центру на размытую растянутую копию самого себя — края не обрезаются
# скруглёнными углами и интерфейсом плеера. REELS_INSET=1 — без поля.
INSET = float(os.environ.get('REELS_INSET', '0.94'))


def inset(fr):
    if INSET >= 0.999:
        return fr
    from PIL import ImageFilter
    fr = fr.convert('RGB')
    bg = fr.resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
    bg = Image.eval(bg, lambda v: int(v * 0.55))                         # фон темнее — внимание на кадре
    w, h = int(round(W * INSET)), int(round(H * INSET))
    bg.paste(fr.resize((w, h), Image.LANCZOS), ((W - w) // 2, (H - h) // 2))
    return bg


def _frame_bytes(i):
    fr = _R.frame(i / FPS)
    if fr.size != (W, H):
        fr = fr.resize((W, H), Image.LANCZOS)
    if FOOTER:
        fr = footer(fr, i / FPS, _R.dur)
    fr = inset(fr)
    return fr.convert('RGB').tobytes()


def _audio(path, dur, track=None, start=0.0):
    if track:
        # музыка играет до последнего кадра без затухания (владелец 14.10); 30 мс в самом конце — только от щелчка
        af = 'afade=t=in:st=0:d=0.02,afade=t=out:st=%.3f:d=0.03,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100' % (dur - 0.03)
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-ss', '%.3f' % start, '-t', '%.3f' % dur, '-i', track, '-af', af,
               '-ac', '2', '-ar', '44100', path]
    else:
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-t', '%.3f' % dur, path]
    subprocess.run(cmd, check=True)


def render(reel, path, track=None, start=0.0, crf=20, workers=None, frames=None, extra_out=None):
    """Собрать ролик. path — mp4. track/start — трек и секунда трека, с которой он играет на t=0 ролика.
    extra_out — ещё путь, куда положить тот же видеоряд с другой звуковой дорожкой (без музыки):
    кадры считаются один раз. frames — список номеров кадров (для быстрой проверки) — тогда только jpg."""
    global _R
    _R = reel
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if frames is not None:
        out = []
        for i in frames:
            p = os.path.splitext(path)[0] + '_f%04d.jpg' % i
            Image.frombytes('RGB', (W, H), _frame_bytes(i)).save(p, quality=90)
            out.append(p)
        return out
    n = int(round(reel.dur * FPS))
    tmpv = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS),
           '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-maxrate', '9M', '-bufsize', '18M', '-pix_fmt',
           'yuv420p', '-profile:v', 'high', '-g', '60', '-movflags', '+faststart', tmpv]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    ctx = multiprocessing.get_context('fork')
    try:
        with ctx.Pool(workers or os.cpu_count() or 2) as pool:
            for b in pool.imap(_frame_bytes, range(n), chunksize=3):
                pr.stdin.write(b)
    finally:
        pr.stdin.close()
        code = pr.wait()
    if code != 0:
        raise RuntimeError('ffmpeg не собрал видеоряд: %s' % path)
    # чистая версия — без музыки; у озвученного ролика (team/reels_daily/voice.py) в ней остаётся голос
    outs = [(path, track)] + ([(extra_out, getattr(reel, 'voice_only', None))] if extra_out else [])
    for p, tr in outs:
        wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        _audio(wav, reel.dur, tr, start if tr == track else 0.0)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmpv, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', p], check=True)
        os.unlink(wav)
    os.unlink(tmpv)
    if reel.cover_t is not None:
        cov = os.path.splitext(extra_out or path)[0]
        for suf in ('_clean', '_preview'):
            if cov.endswith(suf):
                cov = cov[:-len(suf)]
        Image.frombytes('RGB', (W, H), _frame_bytes(int(round(reel.cover_t * FPS)))).save(cov + '_cover.jpg', quality=93)
    return path
