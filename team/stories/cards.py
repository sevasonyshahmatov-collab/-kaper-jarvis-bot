# -*- coding: utf-8 -*-
"""Картинки историй Instagram 1080×1920 — на шаблонах Telegram-канала (владелец 22.10: «посмотри шаблоны канала, там
красиво»; без подписей-ярлыков, логотипы клубов, один кегль для одинаковых вещей):
  matches  — «Матчи дня» (render/matchday_vs.py, макет strips) без линии;
  win      — «Итоги прогнозов» (team/daily/banner.py: счёт, знак, прогноз с кэфом) — только зашедшие;
  question — баннер «Versus» (render/versus.py) и заголовок «КТО ВОЗЬМЁТ?»;
  fact     — фон и шрифты шаблона: заголовок Alumni Sans, текст на золотой плашке.
Шаблон ставится на фон того же шаблона (matchday_vs._background), внизу — призыв в Telegram в том же стиле.
Безопасные зоны историй: сверху 250, снизу 340 px."""
import os
import sys
import tempfile

os.environ.setdefault('JARVIS_S', '1')            # истории — 1080 по ширине, 4К не нужно
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'render'))
sys.path.insert(0, os.path.join(HERE, '..', 'daily'))

from PIL import Image, ImageDraw  # noqa: E402

import matchday_vs as mv  # noqa: E402
import poster  # noqa: E402
import quality  # noqa: E402

W, H = 1080, 1920
TOP, BOT = 250, H - 340
ACC = poster.ACC                                   # золото канала
INK = mv.INK
WHITE = (245, 245, 245)


def canvas():
    im = mv._background(H).convert('RGB')
    return im if im.size == (W, H) else im.resize((W, H))


def place(cv, path, y, max_h):
    """Шаблон по ширине кадра (или по max_h), по центру, верх — y. → низ картинки."""
    with Image.open(path) as im:
        im = im.convert('RGB')
        k = min(W / im.width, max_h / im.height)
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        cv.paste(im, ((W - im.width) // 2, y))
        return y + im.height


def _wrap(d, text, f, max_w):
    rows, cur = [], ''
    for w_ in text.replace(' — ', '\u00a0— ').split(' '):          # тире не начинает строку
        t = (cur + ' ' + w_).strip()
        if d.textlength(t, font=f) <= max_w or not cur:
            cur = t
        else:
            rows.append(cur)
            cur = w_
    rows.append(cur)
    for k in range(len(rows) - 1):                       # предлог в конце строки — на следующую
        ws = rows[k].split()
        if len(ws) > 1 and len(ws[-1]) <= 2:
            rows[k], rows[k + 1] = ' '.join(ws[:-1]), ws[-1] + ' ' + rows[k + 1]
    return rows


def cta(cv, line='ВСЕ ПРОГНОЗЫ — В TELEGRAM'):
    """Низ: золотая плашка с призывом, @jarvibet, «ссылка в шапке профиля» — шрифты шаблона."""
    d = ImageDraw.Draw(cv)
    f = mv._fit_w(line, mv.OSW, 700, 34, W - 220)
    tw = d.textlength(line, font=f)
    y = BOT - 150
    d.rounded_rectangle([W / 2 - tw / 2 - 44, y - 46, W / 2 + tw / 2 + 44, y + 46], radius=14, fill=ACC)
    mv._txt(d, W / 2, y, line, f, INK)
    mv._spaced(d, W / 2, y + 100, '@jarvibet', mv._cap(mv.OSW, 600, 34), ACC, 3)
    mv._spaced(d, W / 2, y + 156, 'ССЫЛКА В ШАПКЕ ПРОФИЛЯ', mv._cap(mv.MAN, 700, 16), mv.GREY, 2)


def save(cv, path):
    quality.texture(cv, 2).convert('RGB').save(path, quality=93)
    return path


def _tmp(name):
    return os.path.join(tempfile.mkdtemp(), name)


def matches(path, day_title, items, league='KHL'):
    """items = [{home, away, time}] одной лиги; day_title — «четверг, 23 октября»."""
    p = _tmp('md.jpg')
    mv.render(items[:8], p, league=league, date_title=day_title, rows=min(len(items), 8))
    cv = canvas()
    place(cv, p, TOP - 20, BOT - 330 - TOP)
    cta(cv)
    return save(cv, path)


def win(path, rows, day_title):
    """rows — рассчитанные прогнозы (team/daily: res, bet, kef, g, league) — только зашедшие."""
    import banner
    out = banner.render(rows[:6], tempfile.mkdtemp(), day_title)
    cv = canvas()
    place(cv, out[0], TOP - 20, BOT - 330 - TOP)
    cta(cv, 'СЕГОДНЯШНИЕ ПРОГНОЗЫ — В TELEGRAM')
    return save(cv, path)


def question(path, home, away, date, time, league='KHL'):
    import versus
    p = _tmp('vs.jpg')
    versus.render(home, away, p, date=date, time=time, odds=None, league=league)
    cv = canvas()
    d = ImageDraw.Draw(cv)
    mv._txt(d, W / 2, TOP + 70, 'КТО ВОЗЬМЁТ?', mv._fit_w('КТО ВОЗЬМЁТ?', mv.ALU, 900, 96, W - 120), WHITE)
    place(cv, p, TOP + 150, 900)
    cta(cv, 'ОТВЕТ JARVIS — В TELEGRAM')
    return save(cv, path)


def fact(path, title, text, label='КАК МЫ ДЕЛАЕМ ПРОГНОЗ'):
    cv = canvas()
    d = ImageDraw.Draw(cv)
    mv._brand(d, W / 2, TOP + 20, 'KHL', 26, ACC)
    mv._spaced(d, W / 2, TOP + 90, label, mv._cap(mv.OSW, 600, 30), ACC, 4)        # рубрика (владелец 22.10)
    ft = mv._cap(mv.ALU, 900, 140)
    y = TOP + 290
    for ln in _wrap(d, title.upper(), ft, W - 140)[:3]:          # все строки заголовка — одним кеглем
        mv._txt(d, W / 2, y, ln, ft, WHITE)
        y += 170
    fb = mv._cap(mv.MAN, 800, 34)
    rows = _wrap(d, text, fb, W - 280)
    by = y + 20
    d.rounded_rectangle([90, by, W - 90, by + 76 * len(rows) + 64], radius=22, fill=ACC)
    for i, r in enumerate(rows):
        mv._txt(d, W / 2, by + 70 + i * 76, r, fb, INK)
    cta(cv, 'КАК ЭТО РАБОТАЕТ СЕГОДНЯ — В TELEGRAM')
    return save(cv, path)
