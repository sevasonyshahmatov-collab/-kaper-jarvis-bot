# -*- coding: utf-8 -*-
"""Общие детали роликов 15.10 (flap, pulse, scales, vault, chain): шапка JARVIS | лига, карточка прогноза,
фон-градиент, вспышка, плавные функции. Всё кешируется на уровне модуля (до fork — общее для процессов)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels.core import W, H

_P = {}
WHITE = (255, 255, 255)


def cached(key, fn):
    if key not in _P:
        _P[key] = fn()
    return _P[key]


def vbg(top, bottom, glow=None, glow_xy=(W / 2, H * 0.42), glow_r=760, glow_k=0.35):
    """Вертикальный градиент + мягкое пятно света (RGB, кеш)."""
    def make():
        y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        arr = np.array(top, np.float32) + (np.array(bottom, np.float32) - np.array(top, np.float32)) * y
        arr = np.broadcast_to(arr, (H, W, 3)).copy()
        if glow:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            k = glow_k * np.exp(-((xx - glow_xy[0]) ** 2 + (yy - glow_xy[1]) ** 2) / (2 * glow_r ** 2))
            arr += (np.array(glow, np.float32) - arr) * k[..., None]
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
    return cached(('vbg', top, bottom, glow, glow_xy, glow_r, glow_k), make)


def header(fr, league, when, y=258, col=WHITE, acc=(255, 196, 61), sub=(200, 206, 220)):
    """JARVIS | NHL и строка времени под ней — одинаково во всех роликах."""
    def make():
        tag = 'NHL' if str(league).upper() in ('NHL', 'НХЛ') else 'KXL'
        a = C.text('JARVIS', 'mont', 46, col, 900, track=0.18)
        b = C.text(tag, 'mont', 46, acc, 900, track=0.18)
        w = a.width + 40 + b.width
        im = Image.new('RGBA', (w, max(a.height, b.height) + 60), (0, 0, 0, 0))
        im.alpha_composite(a, (0, 0))
        ImageDraw.Draw(im).rectangle((a.width + 17, 6, a.width + 22, a.height - 4), fill=col + (200,))
        im.alpha_composite(b, (a.width + 40, 0))
        s = C.text(when, 'mont', 30, sub, 700, track=0.12)
        out = Image.new('RGBA', (max(w, s.width), im.height), (0, 0, 0, 0))
        out.alpha_composite(im, ((out.width - w) // 2, 0))
        out.alpha_composite(s, ((out.width - s.width) // 2, a.height + 16))
        return out
    im = cached(('hdr', league, when, col, acc, sub), make)
    C.put(fr, im, W / 2, y)


def pick_card(team, line1, line2, odds, acc=(255, 196, 61), w=960, h=330, dark=(14, 16, 22), label='ПРОГНОЗ'):
    """Карточка прогноза: эмблема слева, «ПРОГНОЗ», две строки, справа кэф на плашке цвета acc."""
    def make():
        pl = C.rrect(w, h, 36, dark, 236, outline=acc, width=4)
        em = team.emb(200) if team is not None else None
        x0 = 40
        if em is not None:
            C.put(pl, C.with_shadow(em, 14, 0.55, 8), 40 + 110, h / 2)
            x0 = 290
        kw = 230
        room = w - x0 - kw - 50
        C.put(pl, C.text(label, 'mont', 28, acc, 800, track=0.3), x0, 54, anchor='tl')
        t1 = C.text(line1, 'osw', 74, WHITE, 700, max_w=room)
        C.put(pl, t1, x0, 100, anchor='tl')
        if line2:
            C.put(pl, C.text(line2, 'mont', 32, (200, 206, 220), 700, max_w=room), x0, 112 + t1.height, anchor='tl')
        kb = C.rrect(kw, 170, 28, acc)
        C.put(kb, C.text('КЭФ', 'mont', 26, (30, 22, 8), 800, track=0.25), kw / 2, 40)
        C.put(kb, C.text(C.fmt_k(odds), 'osw', 82, (20, 16, 8), 700), kw / 2, 106)
        C.put(pl, kb, w - 30 - kw / 2, h / 2)
        return pl
    return cached(('pick', getattr(team, 'name', None), line1, line2, odds, acc, w, h, dark, label), make)


def flash(fr, k, col=WHITE):
    """Белая (или цветная) вспышка поверх кадра, k 0..1."""
    if k <= 0:
        return fr
    lay = Image.new('RGBA', (W, H), col + (int(255 * min(1.0, k)),))
    fr = fr.convert('RGBA')
    fr.alpha_composite(lay)
    return fr


def pop(t, t0, d=0.35, s=1.6):
    """Масштаб появления с перелётом: 0 → 1 за d секунд от t0."""
    if t < t0:
        return 0.0
    return C.out_back(C.clamp((t - t0) / d), s)


def beat_pulse(t, t0, u, d=0.22):
    """Пик 1 на каждой доле от t0, затухание за d секунд (для подпрыгиваний в такт)."""
    if t < t0:
        return 0.0
    ph = (t - t0) % u
    return max(0.0, 1 - ph / d)


def finish(fr, t, grain_k=8):
    fr = C.grain(fr.convert('RGB'), t, grain_k)
    return C.vignette(fr, 0.45)
