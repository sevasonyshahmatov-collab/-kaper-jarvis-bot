# -*- coding: utf-8 -*-
"""Общее для «новой волны» роликов (11.10): частицы, жидкость, визуализатор, чернила.

Матч и прогноз — dict:
  m = dict(home, away, league='KHL'|'NHL', when='ПН 12.10 · 19:00', side='h'|'a' (за кого прогноз),
           pick='ПОБЕДА АК БАРСА', chance=75, line=(1.49, 4.47, 5.70) | None)
Шанс — «Лучший прогноз» с листа «Прогнозы — кратко» (победа с учётом ОТ и буллитов), линия П1 / Х / П2 — в основное время.
"""
import numpy as np
from PIL import Image

from reels import core as C


def club(t):
    """Клубный цвет: первый «цветной» из c1 / c0 / c2 (не серый, не чёрный, не белый)."""
    for c in (t.c1, t.c0, t.c2):
        if (max(c) - min(c)) / 255 > 0.2 and 40 < 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] < 235:
            return tuple(c)
    return tuple(t.c1)


def bright(c, k=0.35):
    """Тот же цвет, но светлее и насыщеннее — для свечения на тёмном фоне."""
    a = np.array(c, float)
    a = a + (255 - a) * k
    m = a.mean()
    a = m + (a - m) * 1.25
    return tuple(int(v) for v in np.clip(a, 0, 255))


def tag(m):
    return 'JARVIS | NHL' if str(m['league']).upper() == 'NHL' else 'JARVIS | KXL'


def lg_ru(m):
    return 'НХЛ' if str(m['league']).upper() == 'NHL' else 'КХЛ'


def line_text(m):
    if not m.get('line'):
        return ''
    return 'П1 %s · Х %s · П2 %s' % tuple(C.fmt_k(k) for k in m['line'])


def fav_kef(m):
    if not m.get('line'):
        return None
    return m['line'][0] if m['side'] == 'h' else m['line'][2]


def header(fr, m, a=1.0, col=(255, 255, 255)):
    C.put(fr, C.text(tag(m), 'unb', 34, col, 700, track=0.12), C.W / 2, 262, a)


HANDLE_Y = 1560                 # @jarvibet — у низа безопасной зоны Shorts (нижние ~18 % перекрывает интерфейс)


def handle(fr, a=1.0, col=(255, 255, 255), y=HANDLE_Y):
    C.put(fr, C.text(C.HANDLE, 'unb', 38, col, 600), C.W / 2, y, a * C.HANDLE_BOTTOM)    # выключен (core.HANDLE_BOTTOM, 19.10)


def cta(fr, t, t0, y=1430, dark=False, top='TELEGRAM', w=960, h=170):
    """Плашка Telegram: значок внутри левого края, «TELEGRAM / @jarvibet» ровно по центру плашки (C.tg_plate)."""
    q = C.out_expo(C.seg(t, t0, t0 + 0.5))
    if q <= 0:
        return
    pl = C.tg_plate(w, h, top, font='unb')
    ww = max(2, int(pl.width * q))
    C.put(fr, pl.crop((0, 0, ww, pl.height)), (C.W - pl.width) / 2, y - h / 2, anchor='tl')


def mask_points(img, n, rng, cx, cy, colorize=None):
    """Точки внутри непрозрачной части картинки (центр — cx, cy): (xy[n,2], rgb[n,3])."""
    a = np.asarray(img.getchannel('A'), np.float32)
    ys, xs = np.nonzero(a > 110)
    idx = rng.integers(0, len(xs), n)
    jitter = rng.uniform(-0.5, 0.5, (n, 2))
    xy = np.stack([xs[idx], ys[idx]], 1).astype(np.float32) + jitter
    xy[:, 0] += cx - img.width / 2
    xy[:, 1] += cy - img.height / 2
    if colorize is not None:
        rgb = np.tile(np.array(colorize, np.float32), (n, 1))
    else:
        rgb = np.asarray(img.convert('RGB'), np.float32)[ys[idx], xs[idx]]
        lum = rgb @ np.array([0.3, 0.59, 0.11], np.float32)
        dark = lum < 90                       # тёмные части эмблемы на тёмном фоне не видны — светлее
        rgb[dark] = rgb[dark] * 0.5 + 110
    return xy, rgb


def text_mask(lines_, size, max_w, gap=0.12, font='unb', wght=900):
    """Несколько строк белым (RGBA) — для облаков точек."""
    ims = [C.text(s, font, size, (255, 255, 255), wght, max_w=max_w) for s in lines_]
    lh = int(size * (1 + gap))
    out = Image.new('RGBA', (max(i.width for i in ims), lh * (len(ims) - 1) + ims[-1].height), (0, 0, 0, 0))
    for k, im in enumerate(ims):
        out.alpha_composite(im, ((out.width - im.width) // 2, k * lh))
    return out


def sentence(m):
    """Прогноз обычным предложением: «Победа Амура» (названия клубов — с заглавной)."""
    stems = [w.lower()[:4] for t in C.match(m['home'], m['away'], m['league']) for w in t.short.replace('-', ' ').split() if len(w) >= 2]
    out = []
    for w in m['pick'].lower().split():
        if any(w.replace('-', ' ').startswith(st) for st in stems):
            w = '-'.join(x.capitalize() for x in w.split('-'))
        elif w.strip('(),.') == 'от':
            w = w.upper()
        out.append(w)
    s = ' '.join(out)
    return s[:1].upper() + s[1:]
