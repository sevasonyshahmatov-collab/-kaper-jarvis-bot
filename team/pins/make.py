# -*- coding: utf-8 -*-
"""Закрепы канала альбомами-каруселями (владелец 27.10: «посты в закрепе в виде картинок, как карусель, люди листают»;
«отдельный закреп с нашей таблицей — что в ней есть, с краткой подписью на картинках»). Стиль — карусель Instagram
(team/carousel/slides.py: тёмный фон, Alumni Sans / Oswald / Manrope, золотые плашки), 1080×1350.

  about — «О канале»: что выходит, как выбираю прогноз, результаты (stats/months.json сайта), дисклеймер;
  table — «Таблица JARVIS»: листы таблицы; примеры — настоящие данные приложения сайта (app/data.json).

    python team/pins/make.py <каталог сайта (клон …github.io)> <куда> [about|table]
Цифры — только из файлов сайта (их считает team/site/build.py); нет файла — слайд без цифр не рисуется.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'carousel'))

import slides as S  # noqa: E402
from slides import W, H, ACC, INK, WHITE, GREY, WIN, LOSS, mv  # noqa: E402
from PIL import ImageDraw  # noqa: E402

SITE = 'sevasonyshahmatov-collab.github.io'
PANEL, PANEL2 = (40, 38, 44), (32, 30, 36)


def page(title, sub=None):
    img = S._bg()
    d = ImageDraw.Draw(img)
    mv._brand(d, W / 2, 62, 'KHL+NHL', 26, ACC)
    mv._txt(d, W / 2, 158, title, mv._fit_w(title, mv.ALU, 900, 88, W - 120), WHITE)
    if sub:
        mv._spaced(d, W / 2, 232, sub.upper(), mv._cap(mv.OSW, 600, 22), ACC, 3)
    return img, d


def caption(img, text, y=None):
    """Краткая подпись внизу слайда (до двух строк)."""
    d = ImageDraw.Draw(img)
    f = mv._cap(mv.MAN, 700, 34)
    words, rows, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= W - 160 or not cur:
            cur = t
        else:
            rows.append(cur)
            cur = w
    rows.append(cur)
    y = y or H - 125 - 50 * (len(rows) - 1)          # последняя строка — над служебной
    for i, r in enumerate(rows[:3]):
        mv._txt(d, W / 2, y + i * 50, r, f, (220, 218, 224))


def foot(img, note=None):
    S._foot(img, note)


def pill(d, cx, cy, text, size=48):
    f = mv._cap(mv.OSW, 700, size)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle((cx - tw / 2 - 46, cy - size - 6, cx + tw / 2 + 46, cy + size + 6), radius=26, fill=ACC)
    mv._txt(d, cx, cy, text, f, INK)


def rows_block(d, items, y0, rh=150, left=90):
    """Строки «заголовок + пояснение» на плашках."""
    fh, fs = mv._cap(mv.OSW, 700, 40), mv._cap(mv.MAN, 700, 28)
    for i, (h, s) in enumerate(items):
        y = y0 + i * rh
        d.rounded_rectangle((50, y - rh / 2 + 10, W - 50, y + rh / 2 - 10), radius=18, fill=PANEL if i % 2 == 0 else PANEL2)
        mv._txt(d, left, y - 22, h, fh, ACC, 'l')
        mv._txt(d, left, y + 26, s, fs, WHITE, 'l')


def cover(title1, title2, sub, out):
    img = S._bg()
    d = ImageDraw.Draw(img)
    mv._brand(d, W / 2, 62, 'KHL+NHL', 26, ACC)
    ft = mv._cap(mv.ALU, 900, 150)
    mv._txt(d, W / 2, 520, title1, mv._fit_w(title1, mv.ALU, 900, 150, W - 100), WHITE)
    mv._txt(d, W / 2, 680, title2, mv._fit_w(title2, mv.ALU, 900, 150, W - 100), ACC)
    mv._spaced(d, W / 2, 820, sub.upper(), mv._cap(mv.OSW, 600, 28), (220, 218, 224), 3)
    mv._spaced(d, W / 2, 1120, 'ЛИСТАЙ ВПРАВО', mv._cap(mv.OSW, 700, 34), ACC, 4)
    del ft
    foot(img)
    return S._save(img, out)


# ---------- «О канале» ----------

def units(r):
    """Итог прогноза в единицах, как на сайте (team/site/months.py): зашёл — кэф − 1 (без кэфа — 0), не зашёл — −1."""
    if r['r'] == 'w':
        return (r['kef'] - 1) if r.get('kef') else 0.0
    return -1.0 if r['r'] == 'l' else 0.0


def num(x, sign=False):
    return (('%+.1f' if sign else '%.1f') % x).replace('.', ',')


EMB = os.path.join(HERE, '..', '..', 'render', 'emblems')
NHL_FILE = {'DAL': 'dallas', 'MIN': 'minnesota'}             # две эмблемы НХЛ лежат без префикса nhl_


def emb(img, team, lg, cx, cy, size):
    """Эмблема клуба: КХЛ — как на баннерах (matchday_vs), НХЛ — render/emblems/nhl_<аббревиатура>.png."""
    nhl = lg in ('НХЛ', 'NHL')
    ru, col, _, ab = mv._club(team, 'NHL' if nhl else 'KHL')
    f = os.path.join(EMB, (NHL_FILE.get(ab) or 'nhl_' + ab.lower()) + '.png') if nhl else ''
    if f and os.path.exists(f):
        from PIL import Image
        em = Image.open(f).convert('RGBA')
        em.thumbnail((int(size), int(size)), Image.LANCZOS)
        img.alpha_composite(em, (int(cx - em.width / 2), int(cy - em.height / 2)))
    else:
        mv._emblem(img, ru, cx, cy, size, ab, col)


def about(site, out_dir):
    with open(os.path.join(site, 'stats', 'months.json'), encoding='utf-8') as f:
        months = [m for m in json.load(f) if m.get('n')]
    rows = [r for m in months for r in m['rows'] if r['r'] in ('w', 'l', 'p')]
    w, l = sum(m['w'] for m in months), sum(m['l'] for m in months)
    total = sum(units(r) for r in rows)
    span = '%s — %s' % (months[0]['name'].lower(), months[-1]['name'].lower())
    out = []
    p = lambda n: os.path.join(out_dir, 'about_%d.jpg' % n)  # noqa: E731

    # 1 — обложка: главная цифра поверх кривой итога
    img = S._bg()
    d = ImageDraw.Draw(img)
    mv._brand(d, W / 2, 62, 'KHL+NHL', 26, ACC)
    cum, acc = [], 0.0
    for r in rows:
        acc += units(r)
        cum.append(acc)
    lo, hi = min(0, min(cum)), max(cum)
    pts = [(60 + (W - 120) * i / (len(cum) - 1), 1180 - 520 * (v - lo) / (hi - lo)) for i, v in enumerate(cum)]
    glow = S.Image.new('RGBA', (W, H), (0, 0, 0, 0)) if hasattr(S, 'Image') else None
    from PIL import Image
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.polygon(pts + [(pts[-1][0], 1180), (pts[0][0], 1180)], fill=ACC + (38,))
    ld.line(pts, fill=ACC + (150,), width=6, joint='curve')
    img.alpha_composite(lay)
    del glow
    mv._spaced(d, W / 2, 250, 'ИТОГ ВСЕХ ПРОГНОЗОВ ИЗ КАНАЛА', mv._cap(mv.OSW, 600, 26), (220, 218, 224), 3)
    mv._txt(d, W / 2, 400, num(total, True), mv._cap(mv.ALU, 900, 210), ACC)
    mv._spaced(d, W / 2, 545, ('ЕДИНИЦЫ · %s' % span).upper(), mv._cap(mv.OSW, 700, 34), WHITE, 3)
    mv._txt(d, W / 2, 640, '%d из %d прогнозов зашли' % (w, w + l), mv._cap(mv.MAN, 800, 40), WHITE)
    mv._spaced(d, W / 2, 1245, 'ЛИСТАЙ ВПРАВО', mv._cap(mv.OSW, 700, 30), ACC, 4)
    foot(img)
    out.append(S._save(img, p(1)))

    # 2 — график: как рос итог (один ряд, подпись у последней точки, неяркая сетка)
    img, d = page('КАК РОС ИТОГ', 'единицы · каждый прогноз из канала')
    x0, x1, y0, y1 = 120, W - 70, 1000, 360
    step = 10 if hi - lo > 30 else 5
    fax = mv._cap(mv.MAN, 700, 24)
    v = (int(lo // step)) * step
    while v <= hi + step:
        y = y0 - (y0 - y1) * (v - lo) / (hi - lo)
        if y1 - 10 <= y <= y0 + 5:
            d.line((x0, y, x1, y), fill=(255, 255, 255, 40) if v else (255, 255, 255, 110), width=2)
            mv._txt(d, x0 - 16, y, num(v).replace(',0', ''), fax, GREY, 'r')
        v += step
    P = [(x0 + (x1 - x0) * i / (len(cum) - 1), y0 - (y0 - y1) * (c - lo) / (hi - lo)) for i, c in enumerate(cum)]
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).polygon(P + [(P[-1][0], y0 - (y0 - y1) * (0 - lo) / (hi - lo)), (P[0][0], y0 - (y0 - y1) * (0 - lo) / (hi - lo))],
                                fill=ACC + (45,))
    img.alpha_composite(lay)
    d = ImageDraw.Draw(img)
    d.line(P, fill=ACC, width=7, joint='curve')
    d.ellipse((P[-1][0] - 12, P[-1][1] - 12, P[-1][0] + 12, P[-1][1] + 12), fill=ACC, outline=(20, 18, 22), width=4)
    mv._txt(d, P[-1][0] - 24, P[-1][1] - 52, num(total, True), mv._cap(mv.OSW, 700, 46), WHITE, 'r')
    k = 0                                     # подписи месяцев по оси X — в начале каждого месяца
    for m in months:
        x = x0 + (x1 - x0) * k / (len(cum) - 1)
        d.line((x, y0 + 8, x, y0 + 22), fill=GREY, width=2)
        mv._txt(d, x + 8, y0 + 44, m['name'][:3].upper(), mv._cap(mv.OSW, 600, 26), GREY, 'l')
        k += len([r for r in m['rows'] if r['r'] in ('w', 'l', 'p')])
    caption(img, '%d прогнозов подряд, ни один не удалён.' % len(rows))
    foot(img, SITE.upper())
    out.append(S._save(img, p(2)))

    # 3 — кольца: доля зашедших по месяцам
    img, d = page('СКОЛЬКО ЗАХОДИТ', 'доля зашедших прогнозов')
    ms = months[-2:]
    for i, m in enumerate(ms):
        cx = W / 2 if len(ms) == 1 else (300 if i == 0 else W - 300)
        cy, R = 610, 200
        n = m['w'] + m['l']
        share = m['w'] / n if n else 0
        box = (cx - R, cy - R, cx + R, cy + R)
        d.arc(box, 0, 360, fill=(70, 66, 72), width=38)
        d.arc(box, -90, -90 + 360 * share, fill=WIN, width=38)
        mv._txt(d, cx, cy - 14, '%d%%' % round(100 * share), mv._cap(mv.ALU, 900, 110), WHITE)
        mv._txt(d, cx, cy + 74, '%d из %d' % (m['w'], n), mv._cap(mv.MAN, 800, 32), GREY)
        mv._txt(d, cx, cy + R + 80, m['name'].upper() + (' *' if m.get('live') else ''), mv._cap(mv.OSW, 700, 44), ACC)
        mv._txt(d, cx, cy + R + 140, 'средний кэф %s' % ('%.2f' % m['kef']).replace('.', ','), mv._cap(mv.MAN, 700, 30), WHITE)
        mv._txt(d, cx, cy + R + 190, '%s ед.' % num(m['units'], True), mv._cap(mv.OSW, 700, 40), WIN if m['units'] >= 0 else LOSS)
    if any(m.get('live') for m in ms):
        caption(img, '* %s — на %s. Возвраты не считаются.' % (ms[-1]['name'], ms[-1]['upto']))
    foot(img, SITE.upper())
    out.append(S._save(img, p(3)))

    # 4 — последние прогнозы с эмблемами
    last = [r for r in rows if r['r'] in ('w', 'l')][-7:][::-1]
    img, d = page('ПОСЛЕДНИЕ ПРОГНОЗЫ', 'как есть — и зашедшие, и нет')
    fb, fk, fs = mv._cap(mv.MAN, 700, 26), mv._cap(mv.OSW, 700, 34), mv._cap(mv.OSW, 700, 40)
    for i, r in enumerate(last):
        y = 330 + i * 118
        d.rounded_rectangle((50, y, W - 50, y + 104), radius=18, fill=PANEL if i % 2 == 0 else PANEL2)
        emb(img, r['h'], r['lg'], 110, y + 52, 74)
        emb(img, r['a'], r['lg'], 195, y + 52, 74)
        d = ImageDraw.Draw(img)
        bet = (r['bet'].replace(' в основное время', '').replace('Индивидуальный тотал', 'Инд. тотал')
               .replace('Итоговая победа', 'Победа с ОТ'))
        fz = 26                                              # ставка целиком: кегль уменьшаем, текст не режем
        while fz > 18 and d.textlength(bet, font=mv._cap(mv.MAN, 700, fz)) > 500:
            fz -= 1
        mv._txt(d, 255, y + 34, '%s · %s' % (r['d'], r['lg']), mv._cap(mv.OSW, 600, 22), GREY, 'l')
        mv._txt(d, 255, y + 70, bet, mv._cap(mv.MAN, 700, fz), WHITE, 'l')
        mv._txt(d, 830, y + 52, ('%.2f' % r['kef']).replace('.', ',') if r.get('kef') else '—', fk, ACC, 'r')
        col = WIN if r['r'] == 'w' else LOSS
        d.rounded_rectangle((850, y + 20, W - 70, y + 84), radius=14, fill=col)
        mv._txt(d, (850 + W - 70) / 2, y + 52, r['sc'] + (' ' + r['end'] if r.get('end') else ''), fk, WHITE)
    foot(img, 'ЗЕЛЁНЫЙ — ЗАШЁЛ · КРАСНЫЙ — НЕ ЗАШЁЛ')
    out.append(S._save(img, p(4)))

    # 5 — подход (единственный текстовый слайд)
    img, d = page('КАК Я ВЫБИРАЮ ПРОГНОЗ', 'четыре правила')
    rows_block(d, [('1 · ФОРМА', 'Последние игры, очки, место в лиге'),
                   ('2 · ЛИНИЯ', 'Беру исход, только если кэф выше расчёта'),
                   ('3 · КЭФ 1,6–2,3', 'Ниже нет смысла, выше уже лотерея'),
                   ('4 · НЕТ ПЕРЕВЕСА', 'Тогда прогноза нет. Матч пропускаю')], 400, rh=180)
    caption(img, 'Прогноз выходит до матча и остаётся в ленте. Итоги — каждое утро.')
    foot(img)
    out.append(S._save(img, p(5)))

    # 6 — финал
    img, d = page('ВАЖНО')
    fb = mv._cap(mv.ALU, 900, 96)
    for i, t in enumerate(('ПРОГНОЗ —', 'ЭТО МНЕНИЕ,', 'А НЕ ГАРАНТИЯ')):
        mv._txt(d, W / 2, 470 + i * 110, t, fb, WHITE if i < 2 else ACC)
    caption(img, 'В хоккее много случайного, проигрыши будут. Рискуйте только тем, что готовы потерять. 18+', 850)
    pill(d, W / 2, 1120, 'ВСЕ ПРОГНОЗЫ — НА САЙТЕ', 40)
    foot(img, SITE.upper())
    out.append(S._save(img, p(6)))
    return out


# ---------- «Таблица JARVIS» ----------

def table(site, out_dir):
    with open(os.path.join(site, 'app', 'data.json'), encoding='utf-8') as f:
        A = json.load(f)
    khl = A['leagues']['khl']
    out = []
    p = lambda n: os.path.join(out_dir, 'table_%d.jpg' % n)  # noqa: E731
    out.append(cover('ТАБЛИЦА', 'JARVIS', 'КХЛ и НХЛ в одном месте · больше 20 листов', p(1)))

    # 2 — прогнозы и итоги (настоящие строки)
    res = [r for r in A.get('results') or [] if r.get('r') in ('win', 'loss')][:6]
    img, d = page('ПРОГНОЗЫ НА ВСЕ МАТЧИ', 'прогноз · кэф · счёт после игры')
    fm, fp, fk = mv._cap(mv.OSW, 700, 34), mv._cap(mv.MAN, 700, 25), mv._cap(mv.OSW, 700, 40)
    for i, r in enumerate(res):
        y = 330 + i * 125
        d.rounded_rectangle((50, y, W - 50, y + 110), radius=16, fill=PANEL if i % 2 == 0 else PANEL2)
        mv._txt(d, 80, y + 36, '%s — %s' % (r['h'], r['a']), fm, WHITE, 'l')
        pk = r['pick'].replace(' в основное время', '')
        while d.textlength(pk, font=fp) > 640 and ' ' in pk:
            pk = pk.rsplit(' ', 1)[0]
        mv._txt(d, 80, y + 80, pk, fp, GREY, 'l')
        mv._txt(d, W - 210, y + 55, r['k'], fk, ACC, 'r')
        mv._txt(d, W - 80, y + 55, r['sc'], fk, WIN if r['r'] == 'win' else LOSS, 'r')
    caption(img, 'Каждый день: расчёт модели рядом с линией, после игры — счёт.', None)
    foot(img, 'НАСТОЯЩИЕ ПРОГНОЗЫ ИЗ ТАБЛИЦЫ · %s' % A.get('updated', ''))
    out.append(S._save(img, p(2)))

    # 3 — что заходит у команд: тотал больше 4,5 (настоящие частоты)
    tops = sorted([t for t in khl if (t.get('tr') or {}).get('n')], key=lambda t: -t['tr']['o'].get('4.5', 0) / t['tr']['n'])[:6]
    img, d = page('ЧТО ЗАХОДИТ У КОМАНД', 'тотал больше 4,5 · КХЛ, этот сезон')
    fn, fv = mv._cap(mv.OSW, 700, 38), mv._cap(mv.OSW, 700, 42)
    for i, t in enumerate(tops):
        y = 330 + i * 125
        x, n = t['tr']['o'].get('4.5', 0), t['tr']['n']
        d.rounded_rectangle((50, y, W - 50, y + 110), radius=16, fill=PANEL if i % 2 == 0 else PANEL2)
        mv._txt(d, 80, y + 55, t['name'], fn, WHITE, 'l')
        mv._txt(d, W - 80, y + 40, '%d из %d' % (x, n), fv, ACC, 'r')
        d.rounded_rectangle((W - 330, y + 78, W - 80, y + 88), radius=5, fill=(70, 66, 72))
        d.rounded_rectangle((W - 330, y + 78, W - 330 + 250 * x / n, y + 88), radius=5, fill=ACC)
    caption(img, 'Как часто у команды бывает победа, тотал больше или меньше, овертайм. Видно сильные и слабые стороны.', None)
    foot(img, 'ДАННЫЕ ТАБЛИЦЫ · %s' % A.get('updated', ''))
    out.append(S._save(img, p(3)))

    # 4 — места, очки, форма (настоящая турнирная таблица)
    st = sorted(khl, key=lambda t: (-t['pts'], t['gp']))[:7]
    img, d = page('ФОРМА И ОЧКИ', 'КХЛ · лидеры по очкам')
    fn, fv = mv._cap(mv.OSW, 700, 36), mv._cap(mv.OSW, 700, 40)
    for i, t in enumerate(st):
        y = 320 + i * 110
        d.rounded_rectangle((50, y, W - 50, y + 96), radius=16, fill=PANEL if i % 2 == 0 else PANEL2)
        mv._txt(d, 85, y + 48, '%d' % (i + 1), fv, ACC, 'l')
        mv._txt(d, 145, y + 48, t['name'], fn, WHITE, 'l')
        mv._txt(d, 640, y + 48, '%d' % t['pts'], fv, WHITE, 'r')
        for k, c in enumerate(t.get('form', '')[-5:]):
            cx = 720 + k * 56
            d.rounded_rectangle((cx - 22, y + 26, cx + 22, y + 70), radius=10, fill=WIN if c == 'В' else LOSS)
            mv._txt(d, cx, y + 48, c, mv._cap(mv.OSW, 700, 26), WHITE)
    caption(img, 'Места, очки и последние пять игр каждой команды. Расписание и все результаты сезона.', None)
    foot(img, 'ДАННЫЕ ТАБЛИЦЫ · %s' % A.get('updated', ''))
    out.append(S._save(img, p(4)))

    # 5 — рейтинг силы (без цифр: в данных сайта его нет)
    img, d = page('РЕЙТИНГ СИЛЫ', 'Эло — сила команды одним числом')
    rows_block(d, [('ПОСЛЕ КАЖДОГО МАТЧА', 'Рейтинг пересчитывается сам'),
                   ('ПОБЕДА НАД СИЛЬНЫМ', 'Стоит больше, чем над слабым'),
                   ('ПОПРАВКА НА ИГРУ', 'Броски в створ, шайбы сверх ожидания'),
                   ('ВЕСЬ СЕЗОН', 'Как менялась сила команды')], 400, rh=180)
    foot(img)
    out.append(S._save(img, p(5)))

    # 6 — и ещё
    img, d = page('И ЕЩЁ 15+ ЛИСТОВ', 'что ещё внутри')
    chips = ['Коэффициенты', 'Купон дня', 'Точность модели', 'Модель против рынка', 'Карточки команд',
             'Травмы', 'Ключевые игроки', 'История прогнозов', 'Конструктор матча', 'Расписание']
    fc = mv._cap(mv.MAN, 800, 32)
    x, y = 60, 320
    for c in chips:
        tw = d.textlength(c, font=fc) + 70
        if x + tw > W - 60:
            x, y = 60, y + 100
        d.rounded_rectangle((x, y, x + tw, y + 84), radius=42, fill=PANEL, outline=ACC, width=3)
        mv._txt(d, x + tw / 2, y + 42, c, fc, WHITE)
        x += tw + 20
    caption(img, 'Обновляется каждый игровой день. Ничего не удаляется: видно, как часто модель угадывает.', None)
    foot(img)
    out.append(S._save(img, p(6)))

    # 7 — доступ
    img, d = page('КАК ПОЛУЧИТЬ ДОСТУП')
    fb = mv._cap(mv.ALU, 900, 100)
    mv._txt(d, W / 2, 520, 'НАПИШИТЕ', fb, WHITE)
    mv._txt(d, W / 2, 640, 'В TELEGRAM', fb, WHITE)
    pill(d, W / 2, 820, '@JARVIBET', 56)
    caption(img, 'Ответим и расскажем, как подключиться.', 1000)
    foot(img)
    out.append(S._save(img, p(7)))
    return out


if __name__ == '__main__':
    site, out_dir = sys.argv[1], sys.argv[2]
    what = sys.argv[3:] or ['about', 'table']
    os.makedirs(out_dir, exist_ok=True)
    for w in what:
        for path in {'about': about, 'table': table}[w](site, out_dir):
            print('PIN', path, flush=True)
