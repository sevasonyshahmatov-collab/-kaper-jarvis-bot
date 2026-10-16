# -*- coding: utf-8 -*-
"""Серия 3 (16–17.10.2026): ролики-истории с «настоящими» предметами — монета, тактическая доска, табло арены, кейс,
секундомер, газета, кинопроектор, гроза. Общее: данные матча, крючок сверху, карточка прогноза, финальная заставка.

Матч — dict: league, date ('16 октября'), time ('12:30'), home, away, pick ('победа Спартака в основное время'), kef.
Подписей с фактами нет (решение владельца 16.10): только матч, прогноз и кэф. Финальная заставка — на непрозрачном фоне.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reels import core as C
from reels import fresh as F

W, H = C.W, C.H
GOLD = (222, 186, 110)
GOLD_D = (120, 88, 40)
WHITE = (255, 255, 255)


def kef_s(k):
    return ('%.2f' % float(k)).replace('.', ',')


def lg_ru(m):
    return 'НХЛ' if str(m['league']).upper() == 'NHL' else 'КХЛ'


def sub_line(m):
    return '%s · %s · %s МСК' % (lg_ru(m), m['date'].upper(), m['time'])


def pick_side(m, h, a):
    """Чья команда в ставке: 'h' / 'a' / None (тоталы и т. п.)."""
    p = m['pick'].lower()
    for side, t in (('a', a), ('h', h)):
        stem = t.short.lower().replace('-', ' ').split()[0][:5]
        if stem and stem in p.replace('-', ' '):
            return side
    return None


def ease(x):
    return C.in_out(C.clamp(x))


def snap(u, sec):
    return max(1, round(sec / u)) * u


# ─────────────────────────── карточка прогноза (как в «Чате»: эмблемы, ставка, кэф) ───────────────────────────
def pick_card(m, h, a, w=920, kef_q=1.0, dark=True):
    """Карточка прогноза: эмблемы, лига и время, ставка крупно, плашка кэфа. kef_q — доля появления плашки кэфа."""
    bg = (16, 18, 24) if dark else (250, 249, 246)
    ink = WHITE if dark else (14, 14, 18)
    pick = C.lines(m['pick'].upper(), 'unb', 64, w - 110, ink, 800, gap=0.08, max_lines=3)
    hh = 150 + 60 + pick.height + 170
    card = Image.new('RGBA', (w, hh), (0, 0, 0, 0))
    card.alpha_composite(C.rrect(w, hh, 44, bg, 245))
    ol = C.rrect(w, hh, 44, None, outline=(255, 255, 255) if dark else (0, 0, 0), width=2)
    ol.putalpha(ol.getchannel('A').point(lambda v: int(v * 0.14)))
    card.alpha_composite(ol)
    eh, ea = C.fit(h.emb(110), 110, 110), C.fit(a.emb(110), 110, 110)
    C.put(card, eh, 110, 95)
    C.put(card, ea, w - 110, 95)
    C.put(card, C.text('VS', 'unb', 34, (150, 154, 166) if dark else (120, 120, 130), 800), w / 2, 78)
    C.put(card, C.text(sub_line(m), 'mont', 24, (150, 154, 166) if dark else (110, 112, 120), 700, track=0.12, max_w=w - 320), w / 2, 122)
    C.put(card, pick, w / 2, 210 + pick.height / 2)
    if kef_q > 0:
        pill = C.rrect(380, 104, 52, GOLD)
        C.put(pill, C.text('КЭФ ' + kef_s(m['kef']), 'unb', 46, (24, 18, 8), 800), 190, 52)
        C.put(card, C.scale(pill, 0.85 + 0.15 * kef_q), w / 2, 210 + pick.height + 95, kef_q)
    return card


# ─────────────────────────── финальная заставка: непрозрачный фон, ничего не просвечивает ───────────────────────────
def end_card(t, t0, col=(10, 11, 14), accent=GOLD):
    """Кадр заставки (RGBA W×H, полностью непрозрачный) или None, если ещё рано. Въезд — шторка снизу за 0,4 с."""
    if t < t0:
        return None
    q = C.out_expo(C.seg(t, t0, t0 + 0.45))
    fr = Image.new('RGBA', (W, H), col + (255,))
    C.put(fr, C.text('JARVIS', 'unb', 150, WHITE, 800, track=0.06), W / 2, 760 + 40 * (1 - q), q)
    C.put(fr, C.text('ПРОГНОЗЫ НА КХЛ И НХЛ', 'mont', 40, (200, 202, 210), 800, track=0.16), W / 2, 880, q)
    C.put(fr, C.text('КАЖДЫЙ ДЕНЬ', 'mont', 40, accent, 800, track=0.16), W / 2, 935, q)
    F.cta(fr, t, t0 + 0.25, y=1150)
    return fr


def wipe_in(fr, end, t, t0, d=0.4):
    """Заставка въезжает снизу вверх поверх кадра (без просвечивания)."""
    if end is None:
        return fr
    q = C.in_out(C.seg(t, t0, t0 + d))
    if q >= 0.999:
        return end
    y = int(H * (1 - q))
    fr = fr.convert('RGBA')
    fr.paste(end.crop((0, 0, W, H - y)), (0, y))
    return fr


def hook(text, size=78, col=WHITE):
    return C.lines(text, 'unb', size, 960, col, 800, gap=0.08, max_lines=2)
