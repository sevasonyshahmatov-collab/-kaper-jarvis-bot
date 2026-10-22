# -*- coding: utf-8 -*-
"""Картинки историй Instagram 1080×1920 (владелец 22.10): «Матчи дня», «Факт про таблицу», «Успех», «Вопрос дня»,
«Итоги дня». Владелец 22.10: «читается не очень — покрасочнее»: у каждого типа свой яркий градиент, хоккейная разметка
фоном, содержимое — на белых плашках тёмным текстом. Прогнозов нет — только повод перейти в Telegram.
Безопасные зоны историй: сверху 250, снизу 340 px — без текста."""
from PIL import ImageDraw

from reels import core as C
from reels.core import W, H

BG0, BG1 = (8, 10, 16), (18, 24, 40)
ACC = (42, 171, 238)
WHITE = (255, 255, 255)
GREY = (170, 178, 194)
GREEN = (52, 199, 120)
INK = (10, 16, 28)
TOP, BOT = 280, H - 360


THEMES = {   # верх, низ, пятно света
    'blue': ((10, 30, 92), (30, 107, 255), (90, 200, 255)),
    'violet': ((34, 12, 90), (123, 47, 247), (255, 120, 220)),
    'green': ((4, 52, 38), (18, 183, 106), (180, 255, 120)),
    'orange': ((70, 18, 4), (255, 106, 0), (255, 210, 80)),
}
PANEL_INK = (14, 20, 36)


def base(theme='blue'):
    c0, c1, glow = THEMES[theme]
    fr = C.lgrad(W, H, c0, c1, angle=70).convert('RGBA')
    C.put(fr, C.radial(1300, 1300, glow, a0=90), W * 0.85, H * 0.18)
    C.put(fr, C.radial(1100, 1100, c0, a0=140), W * 0.1, H * 0.95)
    rink = ImageDraw.Draw(fr)                                            # разметка площадки: круг вбрасывания и линии
    for r, wdt in ((430, 10), (60, 8)):
        rink.ellipse([W / 2 - r, H * 0.5 - r, W / 2 + r, H * 0.5 + r], outline=(255, 255, 255, 34), width=wdt)
    rink.line([(0, H * 0.5), (W, H * 0.5)], fill=(255, 255, 255, 30), width=10)
    for y in (H * 0.25, H * 0.75):
        rink.line([(0, y), (W, y)], fill=(255, 255, 255, 18), width=6)
    return fr


def tag(fr, s, y=TOP + 30, fill=WHITE, col=PANEL_INK):
    t = C.text(s, 'mont', 38, col, 900, track=0.12)
    C.put(fr, C.with_shadow(C.rrect(t.width + 60, t.height + 36, 40, fill=fill), r=16, a=0.35, dy=8), W / 2, y)
    C.put(fr, t, W / 2, y - 3)


def panel(fr, w, h, cy, a=255):
    C.put(fr, C.with_shadow(C.rrect(w, h, 36, fill=WHITE, a=a), r=30, a=0.35, dy=14), W / 2, cy)


def headline(fr, s, cy, size=104, maxw=W - 120):
    C.put(fr, C.with_shadow(C.lines(s, 'dela', size, maxw, fill=WHITE, max_lines=3), r=18, a=0.45, dy=8), W / 2, cy)


def cta(fr, line='Прогноз на каждый матч — в Telegram'):
    """Низ карточки: призыв, плашка Telegram, «ссылка в шапке профиля»."""
    t = C.lines(line, 'mont', 50, W - 160, fill=WHITE, wght=900, max_lines=2)
    C.put(fr, C.with_shadow(t, r=12, a=0.5, dy=6), W / 2, BOT - 310)
    C.put(fr, C.with_shadow(C.tg_plate(920, 200, font='unb'), r=24, a=0.4, dy=12), W / 2, BOT - 130)
    C.put(fr, C.text('ССЫЛКА В ШАПКЕ ПРОФИЛЯ', 'mont', 32, WHITE, 900, track=0.12), W / 2, BOT)


def done(fr, path):
    C.grain(fr.convert('RGB'), 0.3, k=4).save(path, quality=93)
    return path


def matches(path, day, groups):
    """groups = [('КХЛ', [(время, хоз, гости), …]), ('НХЛ · ночь', […])]."""
    fr = base('blue')
    tag(fr, 'МАТЧИ ДНЯ · %s' % day)
    groups = [(lg, rows) for lg, rows in groups if rows]
    n = sum(len(g) for _, g in groups)
    rh = 84 if n <= 8 else 66 if n <= 12 else 52
    fs = 44 if n <= 8 else 36 if n <= 12 else 30
    hh = len(groups) * rh * 1.1 + n * rh + 60
    hh = min(hh, BOT - 420 - (TOP + 120))
    top = TOP + 120
    panel(fr, W - 100, int(hh), top + hh / 2)
    y = top + 30 + rh / 2
    for lg, rows in groups:
        C.put(fr, C.text(lg, 'mont', 32, (30, 107, 255), 900, track=0.12), W / 2, y)
        y += rh * 1.1
        for tm, h, a in rows:
            if y > top + hh - rh / 2:
                break
            C.put(fr, C.text(tm, 'dela', fs, (30, 107, 255)), 175, y)
            _anchor_left(fr, C.text('%s — %s' % (h, a), 'mont', fs, PANEL_INK, 800, max_w=W - 380), 275, y)
            y += rh
    cta(fr)
    return done(fr, path)


def _anchor_left(fr, im, x, y):
    C.put(fr, im, x + im.width / 2, y)


def fact(path, n, title, text):
    fr = base('violet')
    tag(fr, 'ТАБЛИЦА JARVIS · ФАКТ %d' % n)
    headline(fr, title, 640, size=112)
    panel(fr, W - 120, 360, 970)
    C.put(fr, C.lines(text, 'mont', 56, W - 220, fill=PANEL_INK, wght=800, max_lines=4), W / 2, 970)
    cta(fr, 'Как это работает на сегодняшних матчах — в Telegram')
    return done(fr, path)


def win(path, title, rows):
    """rows = [(матч, счёт, прогноз, кэф)] — только зашедшие; первый — крупно."""
    fr = base('green')
    tag(fr, title)
    m, sc, bet, k = rows[0]
    panel(fr, W - 100, 560, TOP + 440)
    C.put(fr, C.lines(m, 'dela', 70, W - 200, fill=PANEL_INK, max_lines=2), W / 2, TOP + 260)
    C.put(fr, C.text(sc, 'dela', 150, (18, 150, 90)), W / 2, TOP + 430)
    C.put(fr, C.lines(bet, 'mont', 46, W - 220, fill=PANEL_INK, wght=800, max_lines=2), W / 2, TOP + 580)
    if k:
        kt = C.text('КЭФ %s · ЗАШЁЛ' % k, 'mont', 44, WHITE, 900, track=0.06)
        C.put(fr, C.rrect(kt.width + 60, kt.height + 34, 30, fill=(18, 150, 90)), W / 2, TOP + 680)
        C.put(fr, kt, W / 2, TOP + 680)
    y = TOP + 800
    for m2, sc2, bet2, k2 in rows[1:4]:
        C.put(fr, C.with_shadow(C.text('+ %s  %s  %s' % (m2, sc2, k2 or ''), 'mont', 38, WHITE, 900, max_w=W - 140), r=8, a=0.4, dy=4), W / 2, y)
        y += 66
    cta(fr, 'Сегодняшние прогнозы — уже в Telegram')
    return done(fr, path)


def question(path, home, away, when, league='KHL'):
    fr = base('orange')
    tag(fr, 'ВОПРОС ДНЯ')
    h, a = C.match(home, away, league)
    headline(fr, 'Кто возьмёт этот матч?', TOP + 200, size=92)
    panel(fr, W - 100, 440, TOP + 590)
    C.put(fr, h.emb(260), W / 2 - 250, TOP + 545)
    C.put(fr, a.emb(260), W / 2 + 250, TOP + 545)
    C.put(fr, C.text('VS', 'dela', 70, (255, 106, 0)), W / 2, TOP + 545)
    C.put(fr, C.text(h.up, 'dela', 46, PANEL_INK, max_w=400), W / 2 - 250, TOP + 715)
    C.put(fr, C.text(a.up, 'dela', 46, PANEL_INK, max_w=400), W / 2 + 250, TOP + 715)
    C.put(fr, C.with_shadow(C.text(when, 'mont', 40, WHITE, 900, track=0.1), r=8, a=0.4, dy=4), W / 2, TOP + 860)
    cta(fr, 'Ответ JARVIS на этот матч — в Telegram')
    return done(fr, path)


