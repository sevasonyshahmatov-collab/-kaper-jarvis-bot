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


DARK = (40, 44, 56)                                # текст на светлом фоне


def canvas(league='KHL'):
    """Светлый фон-«шёлк» (владелец 22.10: «не всегда чёрный, посветлее»): render/bg_silk.py, режим league —
    КХЛ кремово-золотой → стальной, НХЛ серебро → ледяной голубой; водяной знак лиги."""
    import bg_silk
    im = bg_silk.background('league', H, 'NHL' if league == 'NHL' else 'KHL').convert('RGB')
    return im if im.size == (W, H) else im.resize((W, H))


def dark_canvas():
    """Фон шаблонов канала (matchday_vs / versus — тот же BG с лёгким подсветом) на весь экран истории."""
    im = mv._background(H).convert('RGB')
    return im if im.size == (W, H) else im.resize((W, H))


def blend(cv, path, y, f=110):
    """Шаблон канала — частью фона истории (владелец 22.10: «история — одно целое, не скриншот»): фон у шаблона тот же,
    края сверху и снизу растворяются в фоне на f px, шов не виден. → низ шаблона."""
    with Image.open(path) as im:
        im = im.convert('RGB')
        if im.width != W:
            im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
        m = Image.new('L', im.size, 255)
        dm = ImageDraw.Draw(m)
        for i in range(f):
            v = int(255 * (i / f) ** 1.5)
            dm.line([(0, i), (W, i)], fill=v)
            dm.line([(0, im.height - 1 - i), (W, im.height - 1 - i)], fill=v)
        cv.paste(im, (0, y), m)
        return y + im.height


CTA_Y = 1600                                        # призыв на тёмных историях — под шаблоном, выше строки ответа


def cta_dark(cv, line='ВСЕ ПРОГНОЗЫ — В TELEGRAM'):
    d = ImageDraw.Draw(cv)
    f = mv._fit_w(line, mv.OSW, 700, 34, W - 220)
    tw = d.textlength(line, font=f)
    d.rounded_rectangle([W / 2 - tw / 2 - 44, CTA_Y - 46, W / 2 + tw / 2 + 44, CTA_Y + 46], radius=14, fill=ACC)
    mv._txt(d, W / 2, CTA_Y, line, f, INK)
    mv._spaced(d, W / 2, CTA_Y + 92, '@jarvibet', mv._cap(mv.OSW, 600, 32), ACC, 3)


def _tall(h):
    """Шаблоны matchday_vs ровно h по высоте (полосы крупнее, блок по центру) — на время вызова."""
    orig = mv._layout

    class _Ctx:
        def __enter__(self):
            mv._layout = lambda n, rows, h_max=None: orig(n, rows, h_max or h)

        def __exit__(self, *a):
            mv._layout = orig
    return _Ctx()


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
    """Низ: золотая плашка с призывом (line=None — без неё), @jarvibet, «ссылка в шапке профиля» — шрифты шаблона."""
    d = ImageDraw.Draw(cv)
    y = BOT - 150
    if line:
        f = mv._fit_w(line, mv.OSW, 700, 34, W - 220)
        tw = d.textlength(line, font=f)
        d.rounded_rectangle([W / 2 - tw / 2 - 44, y - 46, W / 2 + tw / 2 + 44, y + 46], radius=14, fill=ACC)
        mv._txt(d, W / 2, y, line, f, INK)
    mv._spaced(d, W / 2, y + 100, '@jarvibet', mv._cap(mv.OSW, 600, 34), DARK, 3)
    mv._spaced(d, W / 2, y + 156, 'ССЫЛКА В ШАПКЕ ПРОФИЛЯ', mv._cap(mv.MAN, 700, 16), (90, 96, 110), 2)


def save(cv, path):
    quality.texture(cv, 2).convert('RGB').save(path, quality=93)
    return path


def _tmp(name):
    return os.path.join(tempfile.mkdtemp(), name)


def matches(path, day_title, items, league='KHL'):
    """items = [{home, away, time}] одной лиги; day_title — «четверг, 23 октября»."""
    p = _tmp('md.jpg')
    with _tall(1360):
        mv.render(items[:8], p, league=league, date_title=day_title, rows=min(len(items), 8))
    cv = dark_canvas()
    blend(cv, p, 190)
    cta_dark(cv)
    return save(cv, path)


def win(path, rows, day_title):
    """rows — рассчитанные прогнозы (team/daily: res, bet, kef, g, league) — только зашедшие."""
    import banner
    rows = rows[:6]
    leagues = {r['league'] for r in rows}
    league = 'KHL+NHL' if len(leagues) > 1 else leagues.pop() + '-RU'
    items = [dict(home=r['home'], away=r['away'], sh=r['g']['hg'], sa=r['g']['ag'], mark=r['g'].get('end') or '',
                  league=r['league'], verdict=r['res'], bet=banner.bet_label(r)) for r in rows]
    p = _tmp('win.jpg')
    mv.render(items, p, league=league, title='ИТОГИ ПРОГНОЗОВ', date_title=day_title, rows=len(items), results=True,
              style='strips', h_max=1360)
    cv = dark_canvas()
    blend(cv, p, 190)
    cta_dark(cv, 'СЕГОДНЯШНИЕ ПРОГНОЗЫ — В TELEGRAM')
    return save(cv, path)


def question(path, home, away, date, time, league='KHL'):
    import versus
    p = _tmp('vs.jpg')
    versus.render(home, away, p, date=date, time=time, odds=None, league=league)
    cv = dark_canvas()
    blend(cv, p, 420)
    d = ImageDraw.Draw(cv)
    mv._txt(d, W / 2, 340, 'КТО ВОЗЬМЁТ?', mv._fit_w('КТО ВОЗЬМЁТ?', mv.ALU, 900, 110, W - 120), WHITE)
    cta_dark(cv, 'ОТВЕТ JARVIS — В TELEGRAM')
    return save(cv, path)


def fact(path, title, text, label='КАК МЫ ДЕЛАЕМ ПРОГНОЗ', swap=False):
    """Светлый фон, заголовок тёмный. swap — плашка наоборот (владелец 22.10: подряд идущие карточки чередуются):
    обычно золотая плашка с тёмным текстом, swap — тёмная плашка с белым текстом и золотым заголовком-рубрикой."""
    plate, ink = ((30, 32, 40), WHITE) if swap else (ACC, INK)
    head = DARK
    cv = canvas()
    d = ImageDraw.Draw(cv)
    mv._spaced(d, W / 2, TOP + 60, label, mv._cap(mv.OSW, 600, 32), DARK, 4)        # рубрика (владелец 22.10)
    ft = mv._cap(mv.ALU, 900, 140)
    y = TOP + 290
    for ln in _wrap(d, title.upper(), ft, W - 140)[:3]:          # все строки заголовка — одним кеглем
        mv._txt(d, W / 2, y, ln, ft, head)
        y += 170
    fb = mv._cap(mv.MAN, 800, 34)
    rows = _wrap(d, text, fb, W - 280)
    by = y + 20
    d.rounded_rectangle([90, by, W - 90, by + 76 * len(rows) + 64], radius=22, fill=plate)
    for i, r in enumerate(rows):
        mv._txt(d, W / 2, by + 70 + i * 76, r, fb, ink)
    cta(cv, None)                                                # владелец 22.10: без призыва-плашки на этих карточках
    return save(cv, path)
