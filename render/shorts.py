# -*- coding: utf-8 -*-
"""Короткие вертикальные ролики (YouTube Shorts, VK Клипы, Rutube) в стиле баннеров «Бока»: свои, из данных канала,
без кадров матчей — претензий правообладателей нет.

    import shorts
    shorts.pick('Вегас', 'Торонто', 'ПТ 09.10 · 05:00 МСК', 'Тотал матча больше 5,5', 1.67, 'out/pick.mp4',
                league='NHL', odds=(1.95, 4.28, 3.21))
    shorts.result('Вегас', 'Торонто', 4, 3, 'out/result.mp4', mark='Б', when='ПТ 09.10',
                  pred='Тотал матча больше 5,5', coef=1.67, won=True, note='3:3 в основное время — 6 шайб', league='NHL')

Чтобы не перелистывали: ролик из коротких сцен по 1,5–2,5 с, смена — на сильную долю бита (120 уд/мин).
  Прогноз: крючок (команды крупно и «прогноз за 1.67») → эмблемы сталкиваются со вспышкой → линия П1/Х/П2
           шкалами шансов → прогноз по словам и кэф «накручивается» → вопрос в комментарии и @jarvibet.
  Итог:    «ЗАШЁЛ ИЛИ НЕТ?» → чем был прогноз → счёт крутится, как барабан, под нарастающий звук →
           печать «ЗАШЁЛ» с конфетти (или «НЕ ЗАШЁЛ» с помехами) → подписка.
Камера живая: удары-приближения, тряска, вспышки, смазанные переходы, блик по фону, ледяная пыль.
Звук свой (синтез numpy): бит, «вжух» на переходах, удары, нарастание, «дзынь» / «бзз» на итог — без чужой музыки.
Оформление каждого ролика немного своё (seed по паре команд): вид крючка, направления переходов, басовая линия.

1080×1920, 30 кадров/с, H.264 + AAC; рядом — обложка *_cover.jpg. Кадры — PIL, склейка — ffmpeg.
Всё важное — выше SAFE_BOTTOM: ниже площадки кладут подпись и кнопки.
"""
import math
import os
import random
import subprocess
import tempfile
import wave

import numpy as np
from PIL import Image, ImageChops, ImageDraw

import nhl
import nhl_kit
import poster

W, H, FPS = 1080, 1920, 30
BPM = 120
BEAT = 60.0 / BPM
PAN = (90, 150)                     # фон чуть больше кадра и медленно сдвигается
SAFE_BOTTOM = 1480                  # ниже — подпись и кнопки Shorts / Клипов: там только фон
HANDLE = '@jarvibet'
GREEN, RED = nhl_kit.GREEN, nhl_kit.RED
SR = 44100


def _style(league):
    """Шапка и акцент как у баннеров лиги: КХЛ — «JARVIS | KXL» золотом, НХЛ — «JARVIS | NHL» ледяным."""
    if str(league).upper() == 'NHL':
        nhl.register()
        return 'NHL', nhl.ICE
    return 'KXL', poster.ACC


# ── плавность ────────────────────────────────────────────────────────────────
def _p(t, a, b):
    return 0.0 if t <= a else 1.0 if t >= b else (t - a) / (b - a)


def _out(x):
    return 1 - (1 - x) ** 3


def _back(x, s=1.9):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


# анимации появления: функция от времени с момента появления → (dx, dy, прозрачность, масштаб)
def fade(d=0.4, dy=36):
    return lambda u: (0, dy * (1 - _out(_p(u, 0, d))), _out(_p(u, 0, d)), 1.0)


def pop(d=0.35, k0=0.5):
    return lambda u: (0, 0, min(1.0, _p(u, 0, d) * 3), k0 + (1 - k0) * _back(_p(u, 0, d)) if u < d else 1.0)


def slam(d=0.22, k0=1.9):
    """Удар: из крупного с размаху на место."""
    return lambda u: (0, 0, min(1.0, _p(u, 0, d * 0.6) * 1.6), k0 - (k0 - 1) * _out(_p(u, 0, d)))


def fly(dx0, dy0=0, d=0.3):
    """Влететь сбоку."""
    return lambda u: (dx0 * (1 - _out(_p(u, 0, d))), dy0 * (1 - _out(_p(u, 0, d))), min(1.0, _p(u, 0, d) * 3), 1.0)


def clash(dx_far, dx_hit, t_hit, d_back=0.35):
    """Эмблемы летят навстречу, сталкиваются в t_hit и отскакивают на свои места."""
    def f(u):
        if u < t_hit:
            k = _p(u, 0, t_hit) ** 2
            return (dx_far + (dx_hit - dx_far) * k, 0, min(1.0, u / max(t_hit, 1e-3) * 3), 1.0)
        k = _back(_p(u, t_hit, t_hit + d_back), 2.4)
        return (dx_hit * (1 - k), 0, 1.0, 1.0 + 0.10 * (1 - _p(u, t_hit, t_hit + d_back)))
    return f


# ── рисование ────────────────────────────────────────────────────────────────
def _font(kind, size):
    return poster._f7(kind, int(size))


def _text(text, kind, size, fill=(255, 255, 255), max_w=None, spacing=0, min_size=24, stroke=0, stroke_fill=(0, 0, 0)):
    f = _font(kind, size)
    if max_w:
        while f.getlength(text) + spacing * max(0, len(text) - 1) > max_w and size > min_size:
            size -= 2
            f = _font(kind, size)
    w = int(f.getlength(text) + spacing * max(0, len(text) - 1)) + 12 + stroke * 2
    asc, desc = f.getmetrics()
    im = Image.new('RGBA', (w, asc + desc + 12 + stroke * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if spacing:
        poster._spaced(d, (6 + stroke, im.height // 2), text, f, fill + (255,), spacing)
    else:
        d.text((w / 2, im.height / 2), text, font=f, fill=fill + (255,), anchor='mm',
               stroke_width=stroke, stroke_fill=stroke_fill + (255,) if stroke else None)
    return im


def _wrap_words(text, kind, size, max_w, lines=3, min_size=48):
    """Слова по строкам: [(слово, x_центра_относительно_середины, номер_строки)], шрифт, размер."""
    words = text.split()
    while True:
        f = _font(kind, size)
        rows, cur = [], []
        for wd in words:
            if cur and f.getlength(' '.join(cur + [wd])) > max_w:
                rows.append(cur)
                cur = [wd]
            else:
                cur.append(wd)
        rows.append(cur)
        if (len(rows) <= lines and all(f.getlength(' '.join(r)) <= max_w for r in rows)) or size <= min_size:
            break
        size -= 6
    sp = f.getlength(' ')
    out = []
    for li, r in enumerate(rows):
        total = f.getlength(' '.join(r))
        x = -total / 2
        for wd in r:
            wl = f.getlength(wd)
            out.append((wd, x + wl / 2, li))
            x += wl + sp
    return out, f, size, len(rows)


def _pill(text, kind, size, fg, fill, outline=None, pad=(44, 22), label=None, label_size=None, min_w=0):
    f = _font(kind, size)
    lf = _font('info', label_size or size * 0.5) if label else None
    tw = f.getlength(text) + (lf.getlength(label) + size * 0.45 if label else 0)
    asc, desc = f.getmetrics()
    w, h = max(min_w, int(tw + pad[0] * 2)), int(asc + desc * 0.4 + pad[1] * 2)
    im = Image.new('RGBA', (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, 4 + w, 4 + h), radius=h // 2, fill=fill, outline=outline, width=4 if outline else 0)
    if text or label:
        x = 4 + (w - tw) / 2
        if label:
            d.text((x, 4 + h / 2), label, font=lf, fill=fg + (255,), anchor='lm')
            x += lf.getlength(label) + size * 0.45
        d.text((x, 4 + h / 2), text, font=f, fill=fg + (255,), anchor='lm')
    return im


def _band(text, kind, size, fg, fill, angle=-6, width=W + 260, max_w=900):
    """Наклонная лента через весь кадр с текстом — для крючка."""
    f = _font(kind, size)
    while f.getlength(text) > max_w and size > 40:
        size -= 4
        f = _font(kind, size)
    asc, desc = f.getmetrics()
    h = int((asc + desc) * 1.25)
    im = Image.new('RGBA', (width, h), fill + (255,))
    ImageDraw.Draw(im).text((width / 2, h / 2 + desc * 0.15), text, font=f, fill=fg + (255,), anchor='mm')
    return im.rotate(angle, resample=Image.BICUBIC, expand=True)


def _brand(tag, accent, size=40):
    fb = _font('brand', size)
    sp, bar = size * 0.12, size * 0.85
    w1 = sum(fb.getlength(c) for c in 'JARVIS') + sp * 5
    w2 = sum(fb.getlength(c) for c in tag) + sp * max(0, len(tag) - 1)
    im = Image.new('RGBA', (int(w1 + 2 * bar + w2) + 8, int(size * 1.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = im.height // 2
    poster._spaced(d, (4, y), 'JARVIS', fb, (255, 255, 255, 255), sp)
    d.rounded_rectangle((4 + w1 + bar - 2, y - size * 0.55, 4 + w1 + bar + 2, y + size * 0.55), radius=2, fill=(255, 255, 255, 150))
    poster._spaced(d, (4 + w1 + 2 * bar, y), tag, fb, accent + (255,), sp)
    return im


def _emblem(team, col, max_w, max_h):
    """Эмблема с тенью; светлая подложка — если эмблема сливается с цветом клуба на фоне (как на баннере)."""
    e = poster._raw_emblem(team, 200, 200)
    arr = np.asarray(e).astype(np.float32)
    op = arr[..., 3] > 128
    plate = bool(op.any()) and float(np.sqrt(((arr[..., :3][op].mean(axis=0) - np.array(col, np.float32)) ** 2).sum())) < 110
    e = poster._raw_emblem(team, max_w, max_h, plate=plate)
    pad = 60
    im = Image.new('RGBA', (e.width + pad * 2, e.height + pad * 2), (0, 0, 0, 0))
    poster._shadowed(im, e, (pad, pad), blur=22, off=(0, 14), color=(0, 0, 0, 130))
    return im


def _background(c1, c2, seed):
    bw, bh = W + PAN[0], H + PAN[1]
    bg = poster._fluid_bg(bw // 2, bh // 2, c1, c2, seed=seed).resize((bw, bh), Image.LANCZOS)
    yy = np.mgrid[0:bh, 0:bw][0].astype(np.float32)
    dim = (0.55 / (1 + np.exp(-((yy / bh) - 0.70) * 9)) + 0.18 * np.exp(-(((yy / bh) - 0.05) ** 2) / 0.01))
    shade = Image.new('RGBA', (bw, bh), (5, 8, 14, 0))
    shade.putalpha(Image.fromarray((np.clip(dim, 0, 1) * 255).astype('uint8'), 'L'))
    bg = Image.alpha_composite(bg.convert('RGBA'), shade)
    return poster._canvas_texture(bg, 1.0).convert('RGBA')


def _sheen():
    """Мягкий диагональный блик, который время от времени проходит по фону."""
    w = 520
    x = np.linspace(-1, 1, w, dtype=np.float32)
    a = (np.exp(-(x ** 2) / 0.08) * 46).astype('uint8')
    im = Image.new('RGBA', (w, H + 600), (255, 255, 255, 0))
    im.putalpha(Image.fromarray(np.tile(a, (H + 600, 1)), 'L'))
    return im.rotate(-18, resample=Image.BICUBIC, expand=True)


def _put(frame, im, cx, cy):
    """Наложить по центру (cx, cy), обрезая то, что за краем кадра."""
    fw, fh = frame.size
    x, y = int(round(cx - im.width / 2)), int(round(cy - im.height / 2))
    l, t = max(0, -x), max(0, -y)
    r, b = min(im.width, fw - x), min(im.height, fh - y)
    if r <= l or b <= t:
        return
    frame.alpha_composite(im.crop((l, t, r, b)) if (l, t, r, b) != (0, 0, im.width, im.height) else im, (x + l, y + t))


def _alpha(im, al):
    im = im.copy()
    im.putalpha(im.getchannel('A').point(lambda v: int(v * al)))
    return im


TG_BLUE = (42, 171, 238)


def _tg_icon(d=170):
    """Значок Telegram: голубой круг с бумажным самолётиком."""
    S = 4
    D = d * S
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse((0, 0, D - 1, D - 1), fill=TG_BLUE + (255,))
    c, r = D / 2, D / 2
    pt = lambda x, y: (c + x * r, c + y * r)
    dr.polygon([pt(-0.52, 0.02), pt(0.46, -0.40), pt(0.29, 0.44), pt(0.05, 0.24), pt(-0.06, 0.38), pt(-0.11, 0.15)], fill=(255, 255, 255, 255))
    dr.polygon([pt(-0.11, 0.15), pt(0.32, -0.20), pt(0.05, 0.24), pt(-0.06, 0.38)], fill=(208, 226, 242, 255))
    return im.resize((d, d), Image.LANCZOS)


def _search_bar(text, n_chars=None, caret=False, w=640, h=118):
    """Строка поиска Telegram с набранным «@jarvibet» (n_chars — сколько букв уже набрано)."""
    im = Image.new('RGBA', (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, 4 + w, 4 + h), radius=h // 2, fill=(255, 255, 255, 245))
    cx, cy, r = 4 + 62, 4 + h / 2 - 4, 20
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(120, 128, 140, 255), width=7)
    d.line((cx + r * 0.7, cy + r * 0.7, cx + r * 1.5, cy + r * 1.5), fill=(120, 128, 140, 255), width=8)
    f = _font('brand', 56)
    s = text if n_chars is None else text[:n_chars]
    d.text((4 + 112, 4 + h / 2), s, font=f, fill=(16, 18, 24, 255), anchor='lm')
    if caret:
        x = 4 + 112 + f.getlength(s) + 6
        d.rectangle((x, 4 + h / 2 - 30, x + 5, 4 + h / 2 + 30), fill=TG_BLUE + (255,))
    return im


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


_SOLID = {}


def _solid(col):
    """Сплошной фон цвета клуба: светлее к середине, текстура холста — для «текстового» варианта."""
    col = tuple(int(v) for v in col)
    if col not in _SOLID:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx / W - 0.5) * 1.0) ** 2 + ((yy / H - 0.42) * 0.8) ** 2)
        k = 1.12 - 0.7 * np.clip(r, 0, 1)
        a = np.array(col, np.float32)[None, None, :] * k[..., None]
        _SOLID[col] = poster._canvas_texture(Image.fromarray(np.clip(a, 0, 255).astype('uint8'), 'RGB'), 0.8).convert('RGBA')
    return _SOLID[col]


# ── звук (свой синтез, без чужой музыки) ─────────────────────────────────────
def _env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-t / d)


def _smooth(x, k):
    k = max(1, int(k))
    return np.convolve(x, np.ones(k) / k, mode='same') if k > 1 else x


def _kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 45 + 85 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16) * 0.95


def _clap(rng):
    n = int(0.25 * SR)
    no = rng.standard_normal(n)
    no = no - _smooth(no, 6)
    env = np.zeros(n)
    for o in (0, 0.012, 0.024):
        i = int(o * SR)
        env[i:] += _env(n - i, 0.001, 0.05)[: n - i]
    return no * env * 0.35


def _hat(rng):
    n = int(0.06 * SR)
    no = rng.standard_normal(n)
    return (no - _smooth(no, 3)) * _env(n, 0.001, 0.015) * 0.12


def _whoosh(rng, dur=0.45):
    n = int(dur * SR)
    no = rng.standard_normal(n)
    lo, hi = _smooth(no, 40), no - _smooth(no, 8)
    t = np.arange(n) / n
    env = np.sin(np.pi * t) ** 2
    return (lo * (1 - t) + hi * t) * env * 0.5


def _impact(rng, big=1.0):
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 30 + 70 * np.exp(-t / 0.06)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)
    no = _smooth(rng.standard_normal(n), 12) * np.exp(-t / 0.08) * 1.6
    return (boom + no) * 0.8 * big


def _tick():
    n = int(0.03 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2200 * t) * np.exp(-t / 0.006) * 0.25


def _riser(rng, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = t / dur
    no = rng.standard_normal(n)
    no = no - _smooth(no, 4)
    tone = np.sin(2 * np.pi * np.cumsum(220 + 900 * k ** 2) / SR)
    return (no * 0.25 + tone * 0.18) * k ** 2


def _ding():
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, a, d in
            ((880, 0.5, 0.9), (1320, 0.3, 0.6), (1760, 0.22, 0.4), (2640, 0.12, 0.25)))
    return s * 0.55


def _buzz():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    saw = ((t * 98) % 1) * 2 - 1 + ((t * 104) % 1) * 2 - 1
    return _smooth(saw, 6) * np.exp(-t / 0.25) * 0.32


def _tock(hi=True):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (1600 if hi else 1050) * t) * np.exp(-t / 0.012) * 0.35


def _click(rng):
    n = int(0.012 * SR)
    no = rng.standard_normal(n)
    return (no - _smooth(no, 2)) * _env(n, 0.0005, 0.003) * 0.25


def _pluck(f, dur=0.45):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)) * np.minimum(1, t / 0.004) * np.exp(-t / 0.22) * 0.16


class _Audio:
    def __init__(self, dur, seed):
        self.n = int(dur * SR) + SR
        self.music = np.zeros(self.n)
        self.fx = np.zeros(self.n)
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    def add(self, t, sig, fx=True, gain=1.0):
        i = int(t * SR)
        if i >= self.n:
            return
        j = min(self.n, i + len(sig))
        (self.fx if fx else self.music)[i:j] += sig[: j - i] * gain

    def beat(self, dur, mute=(), style='drive'):
        """Бит 120 уд/мин, бас — своя линия на каждый ролик. style: 'drive' — бочка на каждую долю, хлопок на 2 и 4;
        'fast' — хлопок на каждую долю и хэт шестнадцатыми; 'show' — без хлопка (под тик-так); 'soft' — спокойнее,
        бочка через долю и перебор аккордов (для «сторис»)."""
        notes = [[55, 55, 65.41, 49], [49, 49, 58.27, 43.65], [55, 65.41, 49, 58.27]][self.seed % 3]
        chords = [(220, 261.6, 329.6), (174.6, 220, 261.6), (261.6, 329.6, 392), (196, 246.9, 293.7)]
        kick, rng = _kick(), self.rng
        nb = int(dur / BEAT) + 1
        for b in range(nb):
            t = b * BEAT
            if any(a <= t < z for a, z in mute):
                self.add(t, _hat(rng), fx=False, gain=0.6)
                continue
            if style == 'soft':
                if b % 2 == 0:
                    self.add(t, kick, fx=False, gain=0.6)
                ch = chords[(b // 4) % 4]
                for k in range(2):
                    self.add(t + k * BEAT / 2, _pluck(ch[(b * 2 + k) % 3] * (2 if k else 1)), fx=False)
                self.add(t + BEAT / 2, _hat(rng), fx=False, gain=0.5)
                continue
            self.add(t, kick, fx=False)
            if (style == 'fast') or (style == 'drive' and b % 2 == 1):
                self.add(t, _clap(rng), fx=False, gain=0.8 if style == 'fast' and b % 2 == 0 else 1.0)
            self.add(t + BEAT / 2, _hat(rng), fx=False)
            if style == 'fast':
                self.add(t + BEAT / 4, _hat(rng), fx=False, gain=0.6)
                self.add(t + 3 * BEAT / 4, _hat(rng), fx=False, gain=0.6)
            n = int(BEAT * 0.9 * SR)
            tt = np.arange(n) / SR
            f = notes[(b // 4) % 4]
            bass = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt)) * np.minimum(1, tt / 0.01) * np.exp(-tt / 0.3) * 0.32
            self.add(t + 0.02, bass, fx=False)

    def write(self, path, dur):
        n = int(dur * SR)
        mix = self.music[:n] * 0.55 + self.fx[:n] * 0.9
        fade = int(0.35 * SR)
        mix[-fade:] *= np.linspace(1, 0, fade)
        mix = np.tanh(mix * 1.2) * 0.68                               # ~ -15 LUFS: площадки сами выравнивают к -14, без перегруза
        pan = np.sin(np.arange(n) / SR * 0.7) * 0.08
        st = np.stack([mix * (1 - pan), mix * (1 + pan)], axis=1)
        data = (np.clip(st, -1, 1) * 32000).astype('<i2')
        with wave.open(path, 'wb') as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(data.tobytes())


# ── ролик ────────────────────────────────────────────────────────────────────
class _Clip:
    def __init__(self, home, away, league, seed=None):
        self.tag, self.accent = _style(league)
        h, a = nhl_kit._prep(home, away)
        self.home, self.away = h, a
        self.c1, self.c2 = poster.BANNER[h], poster.BANNER[a]
        self.seed = sum(map(ord, h + a)) % 997 if seed is None else seed
        self.rnd = random.Random(self.seed)
        self.els = []           # [картинка, cx, cy, t_in, t_out, анимация]
        self.dyn = []           # (t_in, t_out, функция(ov, t)) — то, что меняется каждый кадр
        self.whips = []         # (t, dx, dy) — смазанный переход между сценами
        self.punch = []         # (t, сила) — удар-приближение
        self.shakes = []        # (t, амплитуда, длительность)
        self.flashes = []       # (t, прозрачность, цвет)
        self.glitch = []        # (t, длительность)
        self.confetti = []      # (t, x, y, цвета)
        self.sfx = []           # (t, вид, параметр)
        self.mute = []          # (от, до) — бит молчит (нарастание перед развязкой)
        self.under = []         # (t_in, t_out, функция(кадр, t)) — подложки под элементами (не уезжают с переходом)
        self.top = []           # (t_in, t_out, функция(кадр, t)) — поверх всего (полоски «сторис»)
        self.bgseg = []         # (t_in, t_out, картинка) — сплошной фон вместо перелива («текстовый» вариант)
        self.music_style = 'drive'
        self.cover_t = 0.0

    # служебное
    def el(self, im, cx, cy, t_in, t_out, anim=None):
        self.els.append([im, cx, cy, t_in, t_out, anim or (lambda u: (0, 0, 1.0, 1.0))])

    def whip(self, t, d=None, blur=True, travel=0.55, d_out=0.12, d_in=0.14, sound='whoosh'):
        """Переход между сценами: старое уезжает, новое въезжает (со смазом или без — как перелистывание «сторис»)."""
        d = d or self.rnd.choice([(1, 0), (-1, 0), (0, -1)])
        self.whips.append((t, d[0], d[1], blur, travel, d_out, d_in))
        if sound:
            self.sfx.append((t - 0.22, sound, 0))

    def hit(self, t, big=1.0, flash=0.0, shake=0.0):
        self.punch.append((t, 0.06 * big))
        self.sfx.append((t, 'impact', big))
        if flash:
            self.flashes.append((t, flash, (255, 255, 255)))
        if shake:
            self.shakes.append((t, shake, 0.35))

    def brand(self, t_out):
        self.el(_brand(self.tag, self.accent), W / 2, 120, 0, t_out, fade(0.3, 16))

    def teams(self, t0, t_hit, t_out, cy=680, size=(420, 380), names_y=950):
        e1 = _emblem(self.home, self.c1, *size)
        e2 = _emblem(self.away, self.c2, *size)
        gap = 40
        cx1, cx2 = W / 2 - gap / 2 - (e1.width - 120) / 2, W / 2 + gap / 2 + (e2.width - 120) / 2
        hit = (e1.width - 120) / 2 * 0.55
        self.el(e1, cx1, cy, t0, t_out, clash(-760, hit, t_hit - t0))
        self.el(e2, cx2, cy, t0, t_out, clash(760, -hit, t_hit - t0))
        self.hit(t_hit, 1.0, flash=0.55, shake=18)
        for team, cx, d in ((self.home, cx1, 0.25), (self.away, cx2, 0.4)):
            name = poster.SHORT.get(team, team).upper()
            self.el(_text(name, 'team', 66, max_w=470), cx, names_y, t_hit + d, t_out, pop(0.3, 0.6))
        return cx1, cx2

    def words(self, text, y_top, t0, step, t_out, size=118, max_w=900, fill=(255, 255, 255)):
        """Текст по словам: каждое слово влетает ударом на свой такт."""
        items, f, size, nrows = _wrap_words(str(text).upper(), 'team', size, max_w)
        lh = size * 1.06
        for i, (wd, x, li) in enumerate(items):
            t = t0 + i * step
            self.el(_text(wd, 'team', size, fill=fill), W / 2 + x, y_top + lh * li + lh / 2, t, t_out, slam(0.2, 1.7))
            self.punch.append((t, 0.025))
            self.sfx.append((t, 'tick', 0))
        return y_top + lh * nrows, t0 + step * len(items)

    def counter(self, coef, cy, t0, t_land, t_out):
        """Кэф «накручивается» от 1.00 до значения и встаёт с ударом и «дзынь»."""
        acc = self.accent
        bgp = _pill('', 'num', 96, (16, 18, 24), acc + (255,), min_w=470)
        self.el(bgp, W / 2, cy, t0, t_out, pop(0.3, 0.6))
        f, lf = _font('num', 96), _font('info', 34)
        ink = (16, 18, 24, 255)

        def draw(ov, t):
            v = 1 + (float(coef) - 1) * _out(_p(t, t0 + 0.15, t_land))
            s = '%.2f' % v
            gap = 96 * 0.45
            tw = lf.getlength('КЭФ') + gap + f.getlength(s)
            lay = Image.new('RGBA', (int(tw) + 20, 140), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            d.text((10, 70), 'КЭФ', font=lf, fill=ink, anchor='lm')
            d.text((10 + lf.getlength('КЭФ') + gap, 70), s, font=f, fill=ink, anchor='lm')
            sc = 1 + 0.18 * (1 - _p(t, t_land, t_land + 0.25)) if t >= t_land else 1.0
            if sc != 1:
                lay = lay.resize((int(lay.width * sc), int(lay.height * sc)), Image.BILINEAR)
            _put(ov, lay, W / 2, cy + 4)
        self.dyn.append((t0 + 0.12, t_out, draw))
        k = 0
        while t0 + 0.2 + k * 0.07 < t_land:
            self.sfx.append((t0 + 0.2 + k * 0.07, 'tick', 0))
            k += 1
        self.hit(t_land, 0.9, flash=0.35)
        self.sfx.append((t_land, 'ding', 0))

    def tg_cta(self, t0, extra=None, y0=560):
        """Финал: значок Telegram, «ПОДПИСЫВАЙТЕСЬ НА НАС В TELEGRAM», в строке поиска набирается @jarvibet."""
        acc = self.accent
        self.el(_tg_icon(170), W / 2, y0, t0 + 0.05, t0 + 100, pop(0.35, 0.3))
        self.hit(t0 + 0.05, 0.7)
        self.el(_text('ПОДПИСЫВАЙТЕСЬ', 'team', 112, max_w=980), W / 2, y0 + 205, t0 + 0.3, t0 + 100, slam(0.2, 1.6))
        self.punch.append((t0 + 0.3, 0.03))
        self.el(_text('НА НАС В TELEGRAM', 'team', 84, fill=(110, 200, 250), max_w=980), W / 2, y0 + 320, t0 + 0.55, t0 + 100, slam(0.2, 1.5))
        self.punch.append((t0 + 0.55, 0.03))
        bar_y, t_type = y0 + 470, t0 + 0.95
        self.el(_search_bar(HANDLE, 0), W / 2, bar_y, t0 + 0.8, t_type, pop(0.25, 0.7))

        def typing(ov, t):
            n = min(len(HANDLE), int((t - t_type) / 0.07) + 1)
            done = n >= len(HANDLE)
            caret = (int(t * 3) % 2 == 0) or not done
            _put(ov, _search_bar(HANDLE, n, caret), W / 2, bar_y)
        self.dyn.append((t_type, t0 + 100, typing))
        for i in range(len(HANDLE)):
            self.sfx.append((t_type + i * 0.07, 'click', 0))
        self.el(_text('ПРОГНОЗЫ НА КХЛ И НХЛ КАЖДЫЙ ДЕНЬ', 'info', 28, fill=(230, 234, 242), max_w=960), W / 2, bar_y + 120,
                t_type + 0.7, t0 + 100, fade(0.3, 10))
        if extra:
            self.el(_text(extra, 'info', 26, fill=acc, max_w=960), W / 2, bar_y + 175, t_type + 0.9, t0 + 100, fade(0.3, 10))
        self.sfx.append((t_type + len(HANDLE) * 0.07 + 0.05, 'ding', 0))
        return t0 + 6 * BEAT

    def dust(self):
        rng = random.Random(self.seed * 7 + 1)
        self.specks = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(2, 6), rng.uniform(20, 70), rng.uniform(0.3, 1))
                       for _ in range(46)]

    # кадр
    def frame(self, bg, sheen, t, dur):
        # фон: медленный сдвиг + сдвиг вместе с переходом + проходящий блик
        k = _out(t / dur) if dur else 0
        wx = wy = 0.0
        blur = 0
        for (tw, dx, dy, bl, tr, d_out, d_in) in self.whips:
            if tw - d_out <= t < tw:
                p = _p(t, tw - d_out, tw) ** 2
                wx, wy, blur = -dx * W * tr * p, -dy * H * tr * 0.64 * p, p if bl else 0
            elif tw <= t < tw + d_in:
                p = (1 - _p(t, tw, tw + d_in)) ** 2
                wx, wy, blur = dx * W * tr * p, dy * H * tr * 0.64 * p, p if bl else 0
        seg = None
        for (a, z, img) in self.bgseg:
            if a <= t < z:
                seg = img
        if seg is not None:
            fr = seg.copy()
        else:
            ox = int(min(PAN[0], max(0, PAN[0] * k + wx * 0.12)))
            oy = int(min(PAN[1], max(0, PAN[1] * (1 - k) + wy * 0.12)))
            fr = bg.crop((ox, oy, ox + W, oy + H))
            ph = (t % 3.2) / 3.2
            if ph < 0.5:
                _put(fr, sheen, -sheen.width / 2 + (W + sheen.width) * (ph / 0.5), H / 2)
        for (a, z, fn) in self.under:
            if a <= t < z:
                fn(fr, t)
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for (x, y, r, v, al) in self.specks:                           # ледяная пыль поднимается
            yy = (y - v * t) % H
            xx = x + 14 * math.sin(t * 0.8 + y)
            d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 255, 255, int(70 * al)))
        for im, cx, cy, t_in, t_out, anim in self.els:
            if not (t_in <= t < t_out):
                continue
            dx, dy, al, sc = anim(t - t_in)
            if al <= 0.003:
                continue
            if abs(sc - 1) > 0.004:
                im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
            if al < 0.997:
                im = _alpha(im, al)
            _put(ov, im, cx + dx, cy + dy)
        for t_in, t_out, draw in self.dyn:
            if t_in <= t < t_out:
                draw(ov, t)
        for (tc, x0, y0, cols) in self.confetti:                       # конфетти: разлёт, падение, вращение
            u = t - tc
            if 0 <= u < 2.6:
                rng = random.Random(int(tc * 1000))
                for i in range(150):
                    ang = rng.uniform(-math.pi * 0.95, -math.pi * 0.05)
                    sp = rng.uniform(700, 1700)
                    x = x0 + math.cos(ang) * sp * u * (1 - 0.35 * u / 2.6)
                    y = y0 + math.sin(ang) * sp * u + 900 * u * u
                    if y > H + 40:
                        continue
                    rot = rng.uniform(0, 6.3) + u * rng.uniform(-9, 9)
                    s = rng.uniform(9, 18)
                    c, sn = math.cos(rot), math.sin(rot)
                    pts = [(x + c * a - sn * b, y + sn * a + c * b) for a, b in ((-s, -s * 0.5), (s, -s * 0.5), (s, s * 0.5), (-s, s * 0.5))]
                    d.polygon(pts, fill=cols[i % len(cols)] + (int(255 * min(1, (2.6 - u) * 1.5)),))
        if abs(wx) > 0.5 or abs(wy) > 0.5:                              # переход: сдвиг (и смаз)
            ov2 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            _put(ov2, ov, W / 2 + wx, H / 2 + wy)
            ov = ov2
            if blur > 0.02:
                f = 1 + int(14 * blur)
                if wx:
                    ov = ov.resize((max(1, W // f), H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
                else:
                    ov = ov.resize((W, max(1, H // f)), Image.BILINEAR).resize((W, H), Image.BILINEAR)
        fr.alpha_composite(ov)
        for (a, z, fn) in self.top:
            if a <= t < z:
                fn(fr, t)
        for (tf, al, col) in self.flashes:                              # вспышка
            u = t - tf
            if 0 <= u < 0.3:
                fr.alpha_composite(Image.new('RGBA', (W, H), col + (int(255 * al * (1 - u / 0.3) ** 2),)))
        # камера: удар-приближение и тряска
        z, sx, sy = 1.0, 0.0, 0.0
        for (tp, s) in self.punch:
            u = t - tp
            if 0 <= u < 0.28:
                z += s * (1 - u / 0.28) ** 2
        for (ts, amp, dd) in self.shakes:
            u = t - ts
            if 0 <= u < dd:
                a = amp * (1 - u / dd) ** 2
                sx += a * math.sin(u * 95)
                sy += a * math.cos(u * 77)
        z = max(z, 1 + 2.2 * max(abs(sx) / W, abs(sy) / H))
        if z > 1.001:
            cw, ch = W / z, H / z
            l, tt = W / 2 - cw / 2 + sx, H / 2 - ch / 2 + sy
            fr = fr.resize((W, H), Image.BILINEAR, box=(l, tt, l + cw, tt + ch))
        out = fr.convert('RGB')
        for (tg, dd) in self.glitch:                                    # помехи: сдвиг цветовых каналов и полосы
            u = t - tg
            if 0 <= u < dd:
                a = int(16 * (1 - u / dd)) + 2
                r, g, b = out.split()
                out = Image.merge('RGB', (ImageChops.offset(r, a, 0), g, ImageChops.offset(b, -a, 0)))
                rng = random.Random(int(t * 1000))
                for _ in range(3):
                    y0 = rng.randrange(0, H - 120)
                    hh = rng.randrange(20, 110)
                    band = out.crop((0, y0, W, y0 + hh))
                    out.paste(ImageChops.offset(band, rng.randrange(-60, 60), 0), (0, y0))
        return out

    def render(self, path, music=True):
        saved = poster.FONTS7
        poster.FONTS7 = dict(saved, **poster.FONTS_SIDE)
        try:
            dur = self.build()
            self.dust()
            bg = _background(self.c1, self.c2, self.seed)
            sheen = _sheen()
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            au = _Audio(dur, self.seed)
            if music:
                au.beat(dur, self.mute, self.music_style)
            rng = au.rng
            for (t, kind, prm) in self.sfx:
                sig = {'whoosh': lambda: _whoosh(rng), 'swish': lambda: _whoosh(rng, 0.3) * 0.45,
                       'impact': lambda: _impact(rng, prm or 1.0), 'tick': _tick, 'tock': lambda: _tock(bool(prm)),
                       'click': lambda: _click(rng), 'ding': _ding, 'buzz': _buzz, 'riser': lambda: _riser(rng, prm)}[kind]()
                au.add(max(0.0, t), sig)
            wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            au.write(wav, dur)
            cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                   '-r', str(FPS), '-i', '-', '-i', wav, '-shortest',
                   '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                   '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', path]
            pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            try:
                for i in range(int(round(dur * FPS))):
                    pr.stdin.write(self.frame(bg, sheen, i / FPS, dur).tobytes())
            finally:
                pr.stdin.close()
                code = pr.wait()
                os.unlink(wav)
            if code != 0:
                raise RuntimeError('ffmpeg не собрал ролик: %s' % path)
            self.frame(bg, sheen, self.cover_t, dur).save(os.path.splitext(path)[0] + '_cover.jpg', quality=92)
            return path
        finally:
            poster.FONTS7 = saved


class _Pick(_Clip):
    def __init__(self, home, away, when, pred, coef, odds, hook, league, seed=None):
        super().__init__(home, away, league, seed)
        self.when, self.pred, self.coef, self.odds, self.hook = when, pred, coef, odds, hook

    def build(self):
        acc, b = self.accent, BEAT
        hn = poster.SHORT.get(self.home, self.home).upper()
        an = poster.SHORT.get(self.away, self.away).upper()
        # 1. крючок: команды крупно и «прогноз за 1.67» — с первого кадра
        t1 = 3 * b
        if self.rnd.random() < 0.5:
            self.el(_text(self.hook or 'ПРОГНОЗ НА МАТЧ', 'info', 30, fill=(230, 234, 242), spacing=8), W / 2, 400, 0, t1, fade(0.25, 10))
            self.el(_text(hn, 'team', 170, max_w=980), W / 2, 640, 0, t1, slam())
            self.el(_pill('VS', 'brand', 44, (16, 18, 24), acc + (255,), pad=(34, 18)), W / 2, 850, 0.5 * b, t1, pop(0.25, 0.3))
            self.el(_text(an, 'team', 170, max_w=980), W / 2, 1060, b, t1, slam())
            self.hit(0, 1.0, flash=0.4)
            self.hit(b, 0.8)
        else:
            self.el(_band(self.hook or 'ПРОГНОЗ НА МАТЧ', 'info', 40, (240, 242, 246), (10, 14, 22), angle=-6), W / 2, 560, 0.3 * b, t1, fly(W, 0, 0.22))
            self.el(_band('%s — %s' % (hn, an), 'team', 110, (14, 16, 22), acc, angle=-6), W / 2, 770, 0, t1, fly(-W, 0, 0.22))
            self.hit(0, 1.0, flash=0.4)
            self.sfx.append((0.3 * b, 'whoosh', 0))
        if self.coef:
            st = _pill('ПРОГНОЗ ЗА %.2f' % float(self.coef), 'num', 58, (255, 255, 255), (220, 40, 60, 255), pad=(40, 20)).rotate(4, resample=Image.BICUBIC, expand=True)
            self.el(st, W / 2, 1270, 2 * b, t1, slam(0.2, 2.2))
            self.hit(2 * b, 0.9, shake=10)
        self.whip(t1)
        # 2. эмблемы сталкиваются
        t2 = t1 + 4 * b
        self.brand(t2 + 100)
        self.teams(t1, t1 + b, t2)
        if self.when:
            self.el(_pill(self.when, 'time', 34, (255, 255, 255), (8, 12, 20, 210), acc + (230,)), W / 2, 1080, t1 + 2.5 * b, t2, pop(0.3, 0.6))
            self.sfx.append((t1 + 2.5 * b, 'tick', 0))
        self.whip(t2)
        # 3. линия: шансы по линии без маржи — шкалами
        t3 = t2
        if self.odds:
            t3 = t2 + 4 * b
            self.scene_odds(t2, t3)
            self.whip(t3)
        # 4. прогноз по словам и кэф
        self.mute.append((t3 - 2 * b, t3))
        self.sfx.append((t3 - 2 * b, 'riser', 2 * b))
        self.el(_text('НАШ ПРОГНОЗ', 'info', 34, fill=acc, spacing=10), W / 2, 560, t3, t3 + 100, fade(0.25, 14))
        y, t_w = self.words(self.pred, 630, t3 + 0.5 * b, 0.5 * b, t3 + 100)
        t4 = t_w + 0.5 * b
        if self.coef:
            land = t4 + 1.5 * b
            self.counter(self.coef, min(y + 130, SAFE_BOTTOM - 180), t4, land, t4 + 100)
            self.el(_text('коэффициент на момент публикации', 'info', 22, fill=(196, 202, 214)), W / 2,
                    min(y + 250, SAFE_BOTTOM - 60), land, land + 100, fade(0.3, 0))
            t5 = land + 3 * b
        else:
            t5 = t4 + 2 * b
        self.cover_t = t5 - 0.3
        # убрать всё сцены 4 к заставке
        for e in self.els:
            if e[4] > t5 + 50:
                e[4] = t5
        self.dyn = [(a, min(z, t5), f) for a, z, f in self.dyn]
        self.whip(t5)
        # 5. подписка в Telegram
        return self.tg_cta(t5, extra='А ВЫ КАК ДУМАЕТЕ? ПИШИТЕ В КОММЕНТАРИЯХ')

    def scene_odds(self, t0, t1):
        acc, b = self.accent, BEAT
        o = [float(x) for x in self.odds]
        inv = [1 / x for x in o]
        pr = [x / sum(inv) for x in inv]
        fav = max(range(3), key=lambda i: pr[i])
        names = [poster.SHORT.get(self.home, self.home).upper(), 'НИЧЬЯ', poster.SHORT.get(self.away, self.away).upper()]
        self.el(_text('ШАНСЫ ПО ЛИНИИ', 'info', 34, fill=acc, spacing=10), W / 2, 470, t0, t1, fade(0.25, 14))
        rows = []
        for i in range(3):
            y = 620 + i * 240
            ts = t0 + (0.5 + 0.5 * i) * b
            nm = _text(names[i], 'team', 70, max_w=560)
            self.el(nm, 114 + nm.width / 2, y, ts, t1, fly(-300, 0, 0.25))
            self.el(_text('%.2f' % o[i], 'num', 64, fill=acc if i == fav else (255, 255, 255)), W - 170, y, ts, t1, fly(300, 0, 0.25))
            self.sfx.append((ts, 'tick', 0))
            rows.append((y + 78, ts + 0.15))
        fp = _font('num', 40)

        def draw(ov, t):
            d = ImageDraw.Draw(ov)
            for i, (y, ts) in enumerate(rows):
                if t < ts:
                    continue
                k = _out(_p(t, ts, ts + 0.8))
                x0, full = 120, W - 240
                d.rounded_rectangle((x0, y - 13, x0 + full, y + 13), radius=13, fill=(255, 255, 255, 40))
                wv = max(26, full * pr[i] * k)
                col = acc if i == fav else (235, 238, 244)
                d.rounded_rectangle((x0, y - 13, x0 + wv, y + 13), radius=13, fill=col + (255,))
                d.text((x0 + wv + 16 if wv < full - 140 else x0 + wv - 16, y), '%d%%' % round(pr[i] * 100 * k), font=fp,
                       fill=(255, 255, 255, 255) if wv < full - 140 else (16, 18, 24, 255), anchor='lm' if wv < full - 140 else 'rm')
        self.dyn.append((t0, t1, draw))
        self.el(_text('шансы — из коэффициентов, без маржи букмекера', 'info', 22, fill=(196, 202, 214)), W / 2, 1390, t0 + 2 * b, t1, fade(0.3, 0))
        self.punch.append((t0 + 3 * b, 0.03))
        self.sfx.append((t0 + 3 * b, 'impact', 0.5))


class _Result(_Clip):
    def __init__(self, home, away, sh, sa, mark, when, pred, coef, won, note, league, seed=None):
        super().__init__(home, away, league, seed)
        self.sh, self.sa, self.mark, self.when = int(sh), int(sa), mark, when
        self.pred, self.coef, self.won, self.note = pred, coef, won, note

    def build(self):
        acc, b = self.accent, BEAT
        hn = poster.SHORT.get(self.home, self.home).upper()
        an = poster.SHORT.get(self.away, self.away).upper()
        # 1. крючок-вопрос
        t1 = 3 * b
        self.el(_pill('%s — %s%s' % (hn, an, ' · ' + self.when if self.when else ''), 'time', 30, (255, 255, 255), (8, 12, 20, 210), acc + (230,)),
                W / 2, 500, 0, t1, fade(0.25, 10))
        if self.rnd.random() < 0.5:
            self.el(_text('ЗАШЁЛ', 'team', 230, max_w=980), W / 2, 760, 0, t1, slam())
            self.el(_text('ИЛИ НЕТ?', 'team', 200, fill=acc, max_w=980), W / 2, 1000, b, t1, slam())
        else:
            self.el(_band('ЗАШЁЛ', 'team', 190, (14, 16, 22), acc, angle=-6), W / 2, 740, 0, t1, fly(-W, 0, 0.22))
            self.el(_band('ИЛИ НЕТ?', 'team', 170, (255, 255, 255), (10, 14, 22), angle=-6), W / 2, 1010, b, t1, fly(W, 0, 0.22))
        self.hit(0, 1.0, flash=0.4)
        self.hit(b, 0.9, shake=12)
        self.whip(t1)
        # 2. каким был прогноз
        t2 = t1 + 5 * b
        self.brand(t2 + 100)
        self.teams(t1, t1 + b, t2, cy=620, size=(360, 320), names_y=860)
        if self.pred:
            self.el(_text('НАШ ПРОГНОЗ', 'info', 30, fill=acc, spacing=10), W / 2, 980, t1 + 2 * b, t2, fade(0.25, 14))
            y, tw = self.words(self.pred, 1020, t1 + 2.5 * b, 0.35 * b, t2, size=92, max_w=920)
            if self.coef:
                self.el(_pill('%.2f' % float(self.coef), 'num', 72, (16, 18, 24), acc + (255,), label='КЭФ', label_size=30),
                        W / 2, min(y + 95, SAFE_BOTTOM - 70), tw + 0.25 * b, t2, pop(0.3, 0.5))
                self.sfx.append((tw + 0.25 * b, 'tick', 0))
        self.whip(t2)
        # 3. счёт крутится, как барабан, под нарастание (бит молчит)
        t_h, t_a = t2 + 3 * b, t2 + 4 * b
        t3 = t2 + 5.5 * b
        self.mute.append((t2, t3))
        self.sfx.append((t2, 'riser', t3 - t2))
        self.el(_text('СЧЁТ МАТЧА', 'info', 34, fill=acc, spacing=10), W / 2, 400, t2, t3 + 100, fade(0.25, 14))
        e1 = _emblem(self.home, self.c1, 260, 240)
        e2 = _emblem(self.away, self.c2, 260, 240)
        cx1, cx2 = W / 2 - 230, W / 2 + 230
        self.el(e1, cx1, 610, t2, t3 + 100, fly(-500, 0, 0.3))
        self.el(e2, cx2, 610, t2, t3 + 100, fly(500, 0, 0.3))
        fd = _font('num', 260)
        win, lose = (255, 255, 255), (178, 188, 204)

        def drum(cx, val, t_land, col):
            rng = random.Random(val * 31 + int(t_land * 100))
            seq = [rng.randrange(10) for _ in range(200)]

            def draw(ov, t):
                if t < t_land:
                    i = int((t - t2) * 22)
                    s, al = str(seq[i % 200]), 150
                    lay = Image.new('RGBA', (300, 330), (0, 0, 0, 0))
                    ImageDraw.Draw(lay).text((150, 165), s, font=fd, fill=(255, 255, 255, al), anchor='mm')
                    lay = lay.resize((300, 360), Image.BILINEAR)
                    _put(ov, lay, cx, 940)
                else:
                    sc = 1 + 0.35 * (1 - _out(_p(t, t_land, t_land + 0.25)))
                    lay = Image.new('RGBA', (300, 330), (0, 0, 0, 0))
                    ImageDraw.Draw(lay).text((150, 165), str(val), font=fd, fill=col + (255,), anchor='mm')
                    if sc != 1:
                        lay = lay.resize((int(300 * sc), int(330 * sc)), Image.BILINEAR)
                    _put(ov, lay, cx, 940)
            return draw
        self.dyn.append((t2 + 0.6 * b, t3 + 100, drum(cx1, self.sh, t_h, win if self.sh > self.sa else lose)))
        self.dyn.append((t2 + 0.6 * b, t3 + 100, drum(cx2, self.sa, t_a, win if self.sa > self.sh else lose)))
        self.el(_text(':', 'num', 180, fill=acc), W / 2, 925, t2 + 0.6 * b, t3 + 100, fade(0.2, 0))
        k = 0
        while t2 + 0.7 * b + k * 0.09 < t_a:
            self.sfx.append((t2 + 0.7 * b + k * 0.09, 'tick', 0))
            k += 1
        self.hit(t_h, 0.8, shake=8)
        self.hit(t_a, 0.9, shake=10)
        if self.mark:
            self.el(_pill('В ОВЕРТАЙМЕ' if self.mark == 'ОТ' else 'ПО БУЛЛИТАМ' if self.mark == 'Б' else self.mark, 'num', 38,
                          (255, 255, 255), (8, 12, 20, 215), (255, 255, 255, 110), pad=(34, 16)),
                    W / 2, 1125, t_a + b, t3 + 100, slam(0.2, 1.6))
            self.sfx.append((t_a + b, 'tick', 0))
        # 4. печать итога: снова бит, вспышка, конфетти или помехи
        if self.won is not None:
            col = GREEN if self.won else RED
            st = _pill('ЗАШЁЛ' if self.won else 'НЕ ЗАШЁЛ', 'num', 110, (255, 255, 255), col + (255,), pad=(70, 30)).rotate(-4, resample=Image.BICUBIC, expand=True)
            y = 1330
            self.el(st, W / 2, y, t3, t3 + 100, slam(0.22, 2.4))
            self.hit(t3, 1.2, flash=0.6, shake=24)
            if self.won:
                self.confetti.append((t3, W / 2, y, [GREEN, (255, 255, 255), self.accent, (90, 200, 255)]))
                self.sfx.append((t3, 'ding', 0))
            else:
                self.glitch.append((t3, 0.45))
                self.sfx.append((t3, 'buzz', 0))
            if self.note:
                self.el(_text(str(self.note).upper(), 'info', 30, fill=(235, 238, 244), max_w=960), W / 2, min(y + 145, SAFE_BOTTOM - 8),
                        t3 + 2 * b, t3 + 100, fade(0.3, 12))
            t4 = t3 + 6 * b
        else:
            t4 = t3 + 3 * b
        self.cover_t = t3 + 2.5 * b
        for e in self.els:
            if e[4] > t4 + 50:
                e[4] = t4
        self.dyn = [(a, min(z, t4), f) for a, z, f in self.dyn]
        self.whip(t4)
        # 5. подписка в Telegram
        return self.tg_cta(t4, extra='ВСЕ ИТОГИ — ДАЖЕ НЕУДАЧНЫЕ')


def _names(clip):
    return poster.SHORT.get(clip.home, clip.home).upper(), poster.SHORT.get(clip.away, clip.away).upper()


def _probs(odds):
    inv = [1 / float(x) for x in odds]
    return [x / sum(inv) for x in inv]


class _Stories(_Pick):
    """Вариант «Сторис»: как истории в Telegram/Instagram — полоски сверху заполняются, стеклянная карточка,
    слайды перелистываются влево; спокойная музыка с перебором. Слайды: матч → линия → прогноз → подписка."""

    def build(self):
        acc, b = self.accent, BEAT
        self.music_style = 'soft'
        hn, an = _names(self)
        L = 5 * b
        slides = ['match'] + (['odds'] if self.odds else []) + ['pick', 'cta']
        bounds = [(i * L, (i + 1) * L) for i in range(len(slides))]
        dur = bounds[-1][1] + b
        bounds[-1] = (bounds[-1][0], dur)
        card = Image.new('RGBA', (W - 80, 1310), (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle((0, 0, W - 81, 1309), radius=56, fill=(8, 12, 20, 150), outline=(255, 255, 255, 40), width=3)
        brand = _brand(self.tag, acc)
        self.under.append((0, dur + 1, lambda fr, t: (_put(fr, card, W / 2, 140 + 655), _put(fr, brand, W / 2, 215))))

        def bars(fr, t):
            d = ImageDraw.Draw(fr)
            n, gap, x0 = len(bounds), 10, 40
            bw = (W - 2 * x0 - gap * (n - 1)) / n
            for i, (a, z) in enumerate(bounds):
                x = x0 + i * (bw + gap)
                d.rounded_rectangle((x, 56, x + bw, 64), radius=4, fill=(255, 255, 255, 80))
                k = _p(t, a, z)
                if k > 0:
                    d.rounded_rectangle((x, 56, x + max(8, bw * k), 64), radius=4, fill=(255, 255, 255, 240))
        self.top.append((0, dur + 1, bars))
        for i, (kind, (a, z)) in enumerate(zip(slides, bounds)):
            if i:
                self.whip(a, d=(1, 0), blur=False, travel=1.0, d_out=0.16, d_in=0.22, sound='swish')
            if kind == 'match':
                self.el(_text('МАТЧ ДНЯ · ' + ('НХЛ' if self.tag == 'NHL' else 'КХЛ'), 'info', 30, fill=acc, spacing=9), W / 2, 330, a, z, fade(0.3, 12))
                e1, e2 = _emblem(self.home, self.c1, 380, 340), _emblem(self.away, self.c2, 380, 340)
                cx1, cx2 = W / 2 - 20 - (e1.width - 120) / 2, W / 2 + 20 + (e2.width - 120) / 2
                self.el(e1, cx1, 620, a + 0.15, z, pop(0.4, 0.6))
                self.el(e2, cx2, 620, a + 0.35, z, pop(0.4, 0.6))
                self.sfx += [(a + 0.15, 'tick', 0), (a + 0.35, 'tick', 0)]
                self.el(_text(hn, 'team', 70, max_w=440), cx1, 880, a + 0.6, z, fade(0.3, 20))
                self.el(_text(an, 'team', 70, max_w=440), cx2, 880, a + 0.7, z, fade(0.3, 20))
                if self.when:
                    self.el(_pill(self.when, 'time', 34, (255, 255, 255), (8, 12, 20, 210), acc + (230,)), W / 2, 1010, a + 1.0, z, pop(0.3, 0.7))
                self.el(_text('ПРОГНОЗЫ КАЖДЫЙ ДЕНЬ — В TELEGRAM @JARVIBET', 'info', 24, fill=(196, 202, 214), max_w=900), W / 2, 1360, a + 1.4, z, fade(0.3, 0))
            elif kind == 'odds':
                pr = _probs(self.odds)
                fav = max(range(3), key=lambda k: pr[k])
                self.el(_text('ЛИНИЯ НА МАТЧ', 'info', 30, fill=acc, spacing=9), W / 2, 330, a, z, fade(0.3, 12))
                for k, (nm, o) in enumerate(zip([hn, 'НИЧЬЯ', an], self.odds)):
                    tile = Image.new('RGBA', (300, 400), (0, 0, 0, 0))
                    d = ImageDraw.Draw(tile)
                    d.rounded_rectangle((3, 3, 296, 396), radius=36, fill=(255, 255, 255, 30),
                                        outline=(acc + (240,)) if k == fav else (255, 255, 255, 70), width=6 if k == fav else 3)
                    ln = _text(nm, 'team', 46, max_w=250)
                    tile.alpha_composite(ln, (150 - ln.width // 2, 70 - ln.height // 2))
                    d.text((150, 200), '%.2f' % float(o), font=_font('num', 96), fill=(acc + (255,)) if k == fav else (255, 255, 255, 255), anchor='mm')
                    d.text((150, 320), '%d%%' % round(pr[k] * 100), font=_font('info', 34), fill=(210, 216, 226, 255), anchor='mm')
                    self.el(tile, W / 2 + (k - 1) * 318, 680, a + 0.2 + k * 0.2, z, pop(0.35, 0.7))
                    self.sfx.append((a + 0.2 + k * 0.2, 'tick', 0))
                self.el(_text('ФАВОРИТ ЛИНИИ — %s' % [hn, 'НИЧЬЯ', an][fav], 'team', 64, max_w=940), W / 2, 980, a + 1.1, z, fade(0.35, 20))
                self.el(_text('проценты — шансы из коэффициентов без маржи букмекера', 'info', 22, fill=(196, 202, 214), max_w=940),
                        W / 2, 1070, a + 1.3, z, fade(0.3, 0))
            elif kind == 'pick':
                self.el(_text('НАШ ПРОГНОЗ', 'info', 30, fill=acc, spacing=9), W / 2, 330, a, z, fade(0.3, 12))
                items, f, size, nrows = _wrap_words(str(self.pred).upper(), 'team', 128, 900)
                lh = size * 1.06
                y0 = 640 - lh * nrows / 2
                for wd, x, li in items:
                    self.el(_text(wd, 'team', size), W / 2 + x, y0 + lh * li + lh / 2, a + 0.2 + li * 0.25, z, fade(0.35, 40))
                if self.coef:
                    self.el(_pill('%.2f' % float(self.coef), 'num', 92, (16, 18, 24), acc + (255,), label='КЭФ', label_size=34),
                            W / 2, 980, a + 0.9, z, pop(0.35, 0.5))
                    self.sfx.append((a + 0.9, 'ding', 0))
                    self.el(_text('коэффициент на момент публикации', 'info', 22, fill=(196, 202, 214)), W / 2, 1090, a + 1.2, z, fade(0.3, 0))
                self.cover_t = a + 2.0
            else:
                self.tg_cta(a, extra='ССЫЛКА — В ПРОФИЛЕ КАНАЛА', y0=470)
        return dur


class _Quiz(_Pick):
    """Вариант «Угадай»: «УГАДАЙ НАШ ПРОГНОЗ» → три варианта (А, Б, В) → обратный отсчёт 3-2-1 под тик-так →
    неверные гаснут, верный загорается → подписка. Зритель задерживается, чтобы проверить себя, и пишет букву в комментарии."""

    def __init__(self, *a, options=None, **kw):
        super().__init__(*a, **kw)
        self.options = options

    def build(self):
        acc, b = self.accent, BEAT
        self.music_style = 'show'
        hn, an = _names(self)
        pred = str(self.pred).upper()
        opts = [str(o).upper() for o in (self.options or [])] or [pred, 'ПОБЕДА: ' + hn, 'ПОБЕДА: ' + an]
        if pred not in opts:
            opts = [pred] + opts[:2]
        if not self.options:
            self.rnd.shuffle(opts)
        right = opts.index(pred)

        def rays(fr, t):                                              # лучи прожекторов из-за верхнего края
            lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            cx, cy, R = W / 2, -200, 2600
            for i in range(12):
                a0 = math.radians(i * 30 + t * 14)
                a1 = a0 + math.radians(11)
                d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos(a1), cy + R * math.sin(a1))],
                          fill=(255, 255, 255, 16))
            fr.alpha_composite(lay)
        self.under.append((0, 100, rays))
        # 1. крючок
        t1 = 4 * b
        self.brand(100)
        self.el(_text('УГАДАЙ', 'team', 230, max_w=980), W / 2, 560, 0, t1, slam())
        self.el(_text('НАШ ПРОГНОЗ', 'team', 130, fill=acc, max_w=980), W / 2, 760, 0.5 * b, t1, slam())
        self.hit(0, 1.0, flash=0.4)
        self.hit(0.5 * b, 0.8, shake=10)
        e1, e2 = _emblem(self.home, self.c1, 260, 230), _emblem(self.away, self.c2, 260, 230)
        self.el(e1, W / 2 - 170, 1030, 0.2, t1, clash(-700, 60, 1.5 * b - 0.2))
        self.el(e2, W / 2 + 170, 1030, 0.2, t1, clash(700, -60, 1.5 * b - 0.2))
        self.hit(1.5 * b, 0.9, flash=0.35, shake=14)
        if self.when:
            self.el(_pill(self.when, 'time', 30, (255, 255, 255), (8, 12, 20, 210), acc + (230,)), W / 2, 1230, 2 * b, t1, pop(0.3, 0.6))
        self.whip(t1)
        # 2. варианты, отсчёт, ответ
        letters = ['А', 'Б', 'В']
        ys = [560, 730, 900]
        t_c = t1 + 3 * b
        t_rev = t_c + 3 * b
        t2 = t_rev + 4 * b
        self.el(_text('%s — %s' % (hn, an), 'team', 60, max_w=960), W / 2, 330, t1, t2, fade(0.3, 12))
        self.el(_text('ВАШ ВАРИАНТ: А, Б ИЛИ В?', 'info', 30, fill=acc, spacing=4), W / 2, 420, t1 + 0.2, t2, fade(0.3, 12))

        def bar(i, text, state):
            w, h = 960, 140
            im = Image.new('RGBA', (w + 8, h + 8), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            fill = (acc + (255,)) if state == 'right' else (8, 12, 20, 200)
            d.rounded_rectangle((4, 4, 4 + w, 4 + h), radius=h // 2, fill=fill, outline=None if state == 'right' else (255, 255, 255, 80), width=4)
            d.ellipse((18, 18, 18 + h - 28, 18 + h - 28), fill=(16, 18, 24, 255) if state == 'right' else acc + (255,))
            d.text((18 + (h - 28) / 2, 4 + h / 2), letters[i], font=_font('num', 64), fill=(acc + (255,)) if state == 'right' else (16, 18, 24, 255), anchor='mm')
            tx = _text(text, 'team', 58, fill=(16, 18, 24) if state == 'right' else (255, 255, 255), max_w=w - 230)
            im.alpha_composite(tx, (int(4 + h + 10), int(4 + h / 2 - tx.height / 2)))
            if state == 'right':
                x, y = 4 + w - 70, 4 + h / 2
                d.line((x - 26, y, x - 6, y + 22, x + 30, y - 24), fill=(16, 18, 24, 255), width=12, joint='curve')
            return im
        for i, (txt, y) in enumerate(zip(opts, ys)):
            norm, good = bar(i, txt, 'norm'), bar(i, txt, 'right')
            ti = t1 + 0.4 + i * 0.5 * b

            def draw(ov, t, norm=norm, good=good, y=y, ti=ti, ok=(i == right)):
                dx = W * (1 - _out(_p(t, ti, ti + 0.3)))
                im = norm
                if t >= t_rev:
                    if ok:
                        sc = 1 + 0.12 * (1 - _p(t, t_rev, t_rev + 0.3))
                        im = good.resize((int(good.width * sc), int(good.height * sc)), Image.BILINEAR) if sc > 1.002 else good
                    else:
                        im = _alpha(norm, 1 - 0.65 * _p(t, t_rev, t_rev + 0.25))
                _put(ov, im, W / 2 + dx, y)
            self.dyn.append((ti, t2, draw))
            self.sfx.append((ti, 'swish', 0))
        # отсчёт
        cy = 1150
        fn = _font('num', 120)

        def ring(ov, t):
            u = (t - t_c) / (3 * b)
            n = 3 - int((t - t_c) / b)
            d = ImageDraw.Draw(ov)
            r = 100
            d.ellipse((W / 2 - r, cy - r, W / 2 + r, cy + r), fill=(8, 12, 20, 210))
            d.arc((W / 2 - r + 6, cy - r + 6, W / 2 + r - 6, cy + r - 6), -90, -90 + 360 * (1 - u), fill=acc + (255,), width=12)
            k = (t - t_c) % b / b
            lay = _text(str(n), 'num', 120)
            sc = 1.35 - 0.35 * _out(min(1, k * 4))
            lay = lay.resize((int(lay.width * sc), int(lay.height * sc)), Image.BILINEAR)
            _put(ov, lay, W / 2, cy)
        self.dyn.append((t_c, t_rev, ring))
        for k in range(6):
            self.sfx.append((t_c + k * b / 2, 'tock', k % 2 == 0))
        self.punch += [(t_c + k * b, 0.03) for k in range(3)]
        self.el(_text('ПИШИТЕ БУКВУ В КОММЕНТАРИЯХ', 'info', 28, fill=(230, 234, 242)), W / 2, 1310, t1 + 2 * b, t_rev, fade(0.3, 10))
        self.mute.append((t_c, t_rev))
        # ответ
        self.hit(t_rev, 1.1, flash=0.5, shake=16)
        self.sfx.append((t_rev, 'ding', 0))
        self.confetti.append((t_rev, W / 2, ys[right], [acc, (255, 255, 255), GREEN]))
        self.el(_text('ВЕРНЫЙ ОТВЕТ — %s' % letters[right], 'team', 76, fill=acc), W / 2, 1110, t_rev + 0.1, t2, slam(0.2, 1.6))
        if self.coef:
            self.el(_pill('%.2f' % float(self.coef), 'num', 84, (16, 18, 24), acc + (255,), label='КЭФ', label_size=32),
                    W / 2, 1250, t_rev + b, t2, pop(0.3, 0.5))
            self.sfx.append((t_rev + b, 'tick', 0))
        self.cover_t = t_rev + 2 * b
        self.whip(t2)
        return self.tg_cta(t2, extra='А ВЫ УГАДАЛИ? ПИШИТЕ В КОММЕНТАРИЯХ')


class _Kinetic(_Pick):
    """Вариант «Текстом»: быстрая нарезка на каждую долю — сплошной фон цвета клуба, одно-два огромных слова,
    удар камеры на каждой склейке; бит быстрее. Матч → линия → «наш выбор» → прогноз по словам → кэф → подписка."""

    def build(self):
        acc, b = self.accent, BEAT
        self.music_style = 'fast'
        hn, an = _names(self)
        dark = (12, 16, 26)
        t = [0.0]

        def ink(col):
            return (16, 18, 24) if _lum(col) > 165 else (255, 255, 255)

        def cut(beats, col, lines, emblem=None, sfx='impact'):
            a, z = t[0], t[0] + beats * b
            self.bgseg.append((a, z, _solid(col)))
            ims = [_text(tx, kind, size, fill=fc or ink(col), max_w=980) for tx, kind, size, fc in lines]
            hh = sum(im.height for im in ims) + (emblem.height - 60 if emblem else 0)
            y = 760 - hh / 2
            if emblem:
                self.el(emblem, W / 2, y + (emblem.height - 60) / 2, a, z, slam(0.18, 1.4))
                y += emblem.height - 60
            for k, im in enumerate(ims):
                self.el(im, W / 2, y + im.height / 2, a + k * 0.08, z, slam(0.16, 1.5 + 0.2 * k))
                y += im.height
            self.punch.append((a, 0.05))
            if sfx == 'impact':
                self.sfx.append((a, 'impact', 0.55))
            elif sfx:
                self.sfx.append((a, sfx, 0))
            t[0] = z
        cut(1.5, self.c1, [(hn, 'team', 220, None)], _emblem(self.home, self.c1, 420, 380))
        cut(0.5, dark, [('ПРОТИВ', 'team', 170, acc)], sfx='tick')
        cut(1.5, self.c2, [(an, 'team', 220, None)], _emblem(self.away, self.c2, 420, 380))
        if self.when:
            parts = self.when.split(' · ')
            cut(1.0, dark, [(parts[0], 'team', 150, None)] + ([(' · '.join(parts[1:]), 'team', 120, acc)] if len(parts) > 1 else []), sfx='tick')
        if self.odds:
            pr = _probs(self.odds)
            cut(1.5, dark, [('ЛИНИЯ', 'info', 44, acc)] + [('%s  %.2f' % (nm, float(o)), 'team', 110, None)
                                                            for nm, o in zip(['П1', 'Х', 'П2'], self.odds)], sfx='tick')
            fav = max(range(3), key=lambda k: pr[k])
            cut(1.0, dark, [('ФАВОРИТ', 'info', 44, acc), ([hn, 'НИЧЬЯ', an][fav], 'team', 160, None), ('%d%%' % round(pr[fav] * 100), 'num', 150, acc)])
        cut(1.0, acc, [('НАШ', 'team', 230, None), ('ВЫБОР', 'team', 230, None)])
        self.flashes.append((t[0] - b, 0.4, (255, 255, 255)))
        words = str(self.pred).upper().split()
        cols = [dark, self.c1, self.c2]
        for i, wd in enumerate(words):
            cut(0.75 if i < len(words) - 1 else 1.25, cols[i % 3], [(wd, 'team', 250, None)])
        if self.coef:
            cut(2.0, acc, [('ЗА', 'team', 120, None), ('%.2f' % float(self.coef), 'num', 330, None)])
            self.flashes.append((t[0] - 2 * b, 0.5, (255, 255, 255)))
            self.shakes.append((t[0] - 2 * b, 18, 0.35))
            self.sfx.append((t[0] - 2 * b, 'ding', 0))
        self.cover_t = t[0] - 0.5
        a = t[0]
        self.bgseg.append((a, a + 6 * b + 1, _solid(dark)))
        return self.tg_cta(a, extra='А ВЫ КАК ДУМАЕТЕ? ПИШИТЕ В КОММЕНТАРИЯХ')


STYLES = {'scenes': _Pick, 'stories': _Stories, 'quiz': _Quiz, 'kinetic': _Kinetic}


def pick(home, away, when, pred, coef, path, league='KHL', odds=None, hook=None, music=True, seed=None, style='scenes', options=None):
    """Ролик-прогноз. odds — (П1, Х, П2): сцена с линией; нет — без неё. hook — строка над командами.
    style: 'scenes' — динамичные сцены; 'stories' — как истории в Telegram; 'quiz' — «угадай наш прогноз»
    (options — три варианта, среди них pred; нет — pred и победы команд); 'kinetic' — быстрая нарезка крупным текстом."""
    cls = STYLES[style]
    if style == 'quiz':
        return cls(home, away, when, pred, coef, odds, hook, league, seed, options=options).render(path, music)
    return cls(home, away, when, pred, coef, odds, hook, league, seed).render(path, music)


def result(home, away, sh, sa, path, mark='', when=None, pred=None, coef=None, won=None, note=None, league='KHL',
           music=True, seed=None):
    """Ролик-итог: «зашёл или нет?» → прогноз → счёт барабаном → печать «ЗАШЁЛ / НЕ ЗАШЁЛ» (won=None — без печати).
    note — пояснение под печатью («3:3 в основное время — 6 шайб»)."""
    return _Result(home, away, sh, sa, mark, when, pred, coef, won, note, league, seed).render(path, music)
