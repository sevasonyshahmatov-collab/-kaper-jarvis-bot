# -*- coding: utf-8 -*-
"""Карусель Instagram на один матч дня — 5 слайдов 1080×1350 (владелец 22.10, docs/handoff/SMM_AGENT.md) в стиле
баннеров канала (render/versus.py, render/matchday_vs.py: тёмный фон, панели клубов, эмблемы, Alumni Sans / Oswald /
Manrope, золотые плашки). Каждый слайд рисуется целиком, без вставленных картинок, кроме обложки — баннер «Versus»
растворяется в том же фоне.
  1 — анонс матча (Versus);  2 — линия П1 · Х · П2 (без названия букмекера);  3 — последние 5 матчей обеих команд;
  4 — «Таблица JARVIS»: что чаще всего заходит у этих команд за последние 10 матчей;
  5 — прогноз (reveal=True, 1 день из 5) или «Полный прогноз — в Telegram».
D = dict(league, date='23 октября', time='19:30', home, away, line=(П1, Х, П2), last=dict(home=[(соперник, '3:2', 'В'|'П',
'ОТ'|'Б'|'')], away=[…]), freq=[(событие, x_хоз, n_хоз, x_гост, n_гост)], pick, odds='1,63', reveal)."""
import os
import sys
import tempfile

os.environ.setdefault('JARVIS_S', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'render'))

from PIL import Image, ImageDraw  # noqa: E402

import matchday_vs as mv  # noqa: E402
import poster  # noqa: E402
import quality  # noqa: E402

W, H = 1080, 1350
ACC = poster.ACC
INK = mv.INK
WHITE = (245, 245, 245)
GREY = mv.GREY
WIN, LOSS = (46, 160, 90), (196, 60, 60)
TAG = {'KHL': 'KHL', 'NHL': 'NHL'}


def _bg():
    return mv._background(H).convert('RGBA')


def _head(img, title, league, sub=None):
    d = ImageDraw.Draw(img)
    mv._brand(d, W / 2, 62, TAG[league], 26, ACC)
    mv._txt(d, W / 2, 150, title, mv._fit_w(title, mv.ALU, 900, 84, W - 120), WHITE)
    if sub:
        mv._spaced(d, W / 2, 222, sub.upper(), mv._cap(mv.OSW, 600, 21), ACC, 3)


def _foot(img, note=None):
    d = ImageDraw.Draw(img)
    if note:
        mv._spaced(d, W / 2, H - 70, note, mv._cap(mv.MAN, 700, 11), GREY, 1.2)
    mv._spaced(d, W / 2, H - 36, '@jarvibet', mv._cap(mv.OSW, 600, 20), ACC, 2)


def _save(img, path):
    quality.texture(img, 2).convert('RGB').save(path, quality=93)
    return path


def _club(name, league):
    ru, c1, c2, ab = mv._club(name, league)
    return ru, c1, ab


def cover(D, path):
    """1 — баннер «Versus» на всю ширину, растворяется в фоне; снизу «ЛИСТАЙ →»."""
    import versus
    p = os.path.join(tempfile.mkdtemp(), 'vs.jpg')
    versus.render(D['home'], D['away'], p, date=D['date'], time=D['time'], odds=None, league=D['league'])
    img = _bg().convert('RGB')
    with Image.open(p) as im:
        im = im.convert('RGB').resize((W, W), Image.LANCZOS)
        m = Image.new('L', im.size, 255)
        dm = ImageDraw.Draw(m)
        for i in range(90):
            v = int(255 * (i / 90) ** 1.5)
            dm.line([(0, i), (W, i)], fill=v)
            dm.line([(0, W - 1 - i), (W, W - 1 - i)], fill=v)
        img.paste(im, (0, 110), m)
    d = ImageDraw.Draw(img)
    mv._brand(d, W / 2, 62, TAG[D['league']], 26, ACC)
    mv._txt(d, W - 70, H - 62, 'ЛИСТАЙ →', mv._cap(mv.ALU, 900, 34), ACC, 'r')        # в Oswald нет стрелки
    return _save(img.convert('RGBA'), path)


def _teams_row(img, D, y, size=230):
    """Две панели клубов с эмблемами и аббревиатурами под ними — одним кеглем."""
    d = ImageDraw.Draw(img)
    fa = mv._cap(mv.ALU, 900, 64)
    for k, (name, x) in enumerate(((D['home'], W * 0.27), (D['away'], W * 0.73))):
        ru, col, ab = _club(name, D['league'])
        box = (x - size / 2, y - size / 2, x + size / 2, y + size / 2)
        mv._panel(img, box, col, 11 + 12 * k, ('down', 'up')[k], (0.5, 0.5))
        mv._emblem(img, ru, x, y, size * 0.74, ab, col)
        mv._txt(d, x, y + size / 2 + 60, ab, fa, mv._readable(col))
    mv._txt(d, W / 2, y, 'vs', mv._cap(mv.OSW, 600, 40), GREY)


def line(D, path):
    """2 — линия П1 · Х · П2 крупными золотыми плашками."""
    img = _bg()
    _head(img, 'ЛИНИЯ НА МАТЧ', D['league'], '%s · %s МСК' % (D['date'], D['time']))
    _teams_row(img, D, 470)
    d = ImageDraw.Draw(img)
    fl, fv = mv._cap(mv.MAN, 800, 26), mv._cap(mv.OSW, 700, 72)
    pw, ph, gap = 290, 190, 30
    x0 = W / 2 - (3 * pw + 2 * gap) / 2
    fav = min(range(3), key=lambda i: D['line'][i]) if all(D['line']) else None
    for i, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), D['line'])):
        cx, cy = x0 + pw / 2 + i * (pw + gap), 930
        fill = ACC if i == fav else (58, 54, 50)
        txt = INK if i == fav else WHITE
        d.rounded_rectangle((cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2), radius=int(ph * 0.22), fill=fill)
        mv._txt(d, cx, cy - 52, lab, fl, txt)
        mv._txt(d, cx, cy + 22, ('%.2f' % v).replace('.', ',') if v else '—', fv, txt)
    _foot(img, 'ОСНОВНОЕ ВРЕМЯ · КОЭФФИЦИЕНТЫ НА МОМЕНТ ПУБЛИКАЦИИ')
    return _save(img, path)


def last5(D, path):
    """3 — последние 5 матчей: по команде — эмблема и пять ячеек (соперник, счёт, цвет результата)."""
    img = _bg()
    _head(img, 'ПОСЛЕДНИЕ 5 МАТЧЕЙ', D['league'])
    d = ImageDraw.Draw(img)
    fs, fo, fm = mv._cap(mv.OSW, 700, 40), mv._cap(mv.ALU, 900, 26), mv._cap(mv.MAN, 800, 15)
    for k, side in enumerate(('home', 'away')):
        name = D[side]
        ru, col, ab = _club(name, D['league'])
        y = 400 + k * 470
        box = (60, y - 95, 250, y + 95)
        mv._panel(img, box, col, 11 + 12 * k, 'down', (0.5, 0.5))
        mv._emblem(img, ru, 155, y, 140, ab, col)
        mv._txt(d, 155, y + 140, ab, mv._cap(mv.ALU, 900, 44), mv._readable(col))
        cw, gap = 140, 14
        for i, (opp, sc, res, mark) in enumerate(D['last'][side][:5]):
            cx = 300 + cw / 2 + i * (cw + gap)
            fill = WIN if res == 'В' else LOSS
            d.rounded_rectangle((cx - cw / 2, y - 120, cx + cw / 2, y + 120), radius=18, fill=(40, 38, 44))
            d.rounded_rectangle((cx - cw / 2, y + 74, cx + cw / 2, y + 120), radius=18, fill=fill)
            d.rectangle((cx - cw / 2, y + 74, cx + cw / 2, y + 92), fill=fill)
            ofull, ocol, oab = _club(opp, D['league'])
            mv._emblem(img, ofull, cx, y - 66, 74, oab, ocol)
            mv._txt(d, cx, y + 16, sc, fs, WHITE)
            mv._txt(d, cx, y + 98, ('ПОБЕДА' if res == 'В' else 'ПОРАЖ.') + (' ' + mark if mark else ''), fm, (255, 255, 255))
        mv._txt(d, 300, y - 160, 'НОВЫЕ →', fo, GREY, 'l')
    _foot(img, 'ОТ — ОВЕРТАЙМ · Б — БУЛЛИТЫ · СЛЕВА — ПОСЛЕДНИЙ МАТЧ')
    return _save(img, path)


def table(D, path):
    """4 — «Таблица JARVIS»: события, которые чаще всего заходили у обеих команд за последние 10 матчей."""
    img = _bg()
    _head(img, 'ТАБЛИЦА JARVIS', D['league'], 'что чаще всего заходит · последние 10 матчей')
    d = ImageDraw.Draw(img)
    hx = (720, 930)
    for k, side in enumerate(('home', 'away')):
        ru, col, ab = _club(D[side], D['league'])
        mv._emblem(img, ru, hx[k], 320, 110, ab, col)
        mv._txt(d, hx[k], 405, ab, mv._cap(mv.ALU, 900, 34), mv._readable(col))
    fv = mv._cap(mv.OSW, 700, 44)
    rows = D['freq'][:5]
    cap = 26                                    # один кегль для всех событий (владелец 23.10): самый крупный, что влезает у всех
    while cap > 14 and any(d.textlength(r[0], font=mv._cap(mv.MAN, 800, cap)) > 500 for r in rows):
        cap -= 1
    fe = mv._cap(mv.MAN, 800, cap)
    rh = 150
    for i, (ev, xh, nh, xa, na) in enumerate(rows):
        y = 520 + i * rh
        d.rounded_rectangle((50, y - 60, W - 50, y + 60), radius=18, fill=(40, 38, 44) if i % 2 == 0 else (32, 30, 36))
        mv._txt(d, 90, y, ev, fe, WHITE, 'l')
        for k, (x, n) in enumerate(((xh, nh), (xa, na))):
            cx = hx[k]
            share = x / n if n else 0
            col = ACC if share >= 0.7 else WHITE
            mv._txt(d, cx, y - 8, '%d/%d' % (x, n), fv, col)
            d.rounded_rectangle((cx - 70, y + 34, cx + 70, y + 42), radius=4, fill=(70, 66, 72))
            d.rounded_rectangle((cx - 70, y + 34, cx - 70 + 140 * share, y + 42), radius=4, fill=col)
    _foot(img, 'ДАННЫЕ ТАБЛИЦЫ JARVIS · ОСНОВНОЕ ВРЕМЯ')
    return _save(img, path)


def final(D, path):
    """5 — прогноз (reveal) или призыв в Telegram."""
    img = _bg()
    d = ImageDraw.Draw(img)
    mv._brand(d, W / 2, 62, TAG[D['league']], 26, ACC)
    _teams_row(img, D, 330, size=200)
    if D.get('reveal'):
        mv._txt(d, W / 2, 640, 'ПРОГНОЗ JARVIS', mv._fit_w('ПРОГНОЗ JARVIS', mv.ALU, 900, 90, W - 120), WHITE)
        fp = mv._cap(mv.OSW, 700, 54)
        words, rows, cur = D['pick'].upper().split(), [], ''
        for w_ in words:
            t = (cur + ' ' + w_).strip()
            if d.textlength(t, font=fp) <= W - 180 or not cur:
                cur = t
            else:
                rows.append(cur)
                cur = w_
        rows.append(cur)
        for i, r in enumerate(rows[:3]):
            mv._txt(d, W / 2, 780 + i * 80, r, fp, ACC)
        y = 780 + len(rows[:3]) * 80 + 60
        fk = mv._cap(mv.OSW, 700, 60)
        kt = 'КЭФ %s' % D['odds']
        tw = d.textlength(kt, font=fk)
        d.rounded_rectangle((W / 2 - tw / 2 - 50, y - 60, W / 2 + tw / 2 + 50, y + 60), radius=26, fill=ACC)
        mv._txt(d, W / 2, y, kt, fk, INK)
        _foot(img, 'ПРОГНОЗ — МНЕНИЕ АВТОРА, НЕ СОВЕТ')
    else:
        t1, t2 = 'ПОЛНЫЙ ПРОГНОЗ', 'НА ЭТОТ МАТЧ'
        ft = mv._cap(mv.ALU, 900, 100)
        mv._txt(d, W / 2, 660, t1, ft, WHITE)
        mv._txt(d, W / 2, 790, t2, ft, WHITE)
        fk = mv._cap(mv.OSW, 700, 52)
        kt = 'В TELEGRAM @JARVIBET'
        tw = d.textlength(kt, font=fk)
        d.rounded_rectangle((W / 2 - tw / 2 - 50, 930, W / 2 + tw / 2 + 50, 1050), radius=26, fill=ACC)
        mv._txt(d, W / 2, 990, kt, fk, INK)
        mv._spaced(d, W / 2, 1110, 'ССЫЛКА В ШАПКЕ ПРОФИЛЯ', mv._cap(mv.MAN, 700, 18), GREY, 2)
        _foot(img)
    return _save(img, path)


def render(D, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    fns = (cover, line, last5, table, final)
    return [f(D, os.path.join(out_dir, '%d.jpg' % (i + 1))) for i, f in enumerate(fns)]
