# -*- coding: utf-8 -*-
"""Картинка-превью страницы матча (og:image, 1200×630) — то, что видно, когда ссылку на матч пересылают в Telegram или чат
(владелец 09.11). Рисует seo/build_match.py рядом со страницей: <лига>/<дата>-<хозяева>-<гости>/og.jpg.
До матча — эмблемы, названия, дата и время, вероятности модели; после — счёт. Без кэфов и названий БК."""
import os

from PIL import Image, ImageDraw, ImageFont

V3A = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
FONT = os.path.normpath(os.path.join(V3A, '..', '..', '..', 'render', 'fonts', 'Manrope[wght].ttf'))
W, H = 1200, 630
BG = (8, 18, 36)
INK, INK2, INK3 = (240, 244, 250), (178, 192, 212), (112, 128, 150)
SIGNAL = (255, 202, 40)
SPORT = {'hockey': (88, 166, 255), 'football': (52, 199, 120)}
_F = {}


def font(size, weight='Bold'):
    k = (size, weight)
    if k not in _F:
        f = ImageFont.truetype(FONT, size)
        try:
            f.set_variation_by_name(weight)
        except Exception:  # noqa: BLE001
            pass
        _F[k] = f
    return _F[k]


def crest(sport, tid, size):
    p = os.path.join(V3A, 'assets', 'em' if sport == 'hockey' else 'fc', '%s.webp' % tid)
    try:
        im = Image.open(p).convert('RGBA')
    except Exception:  # noqa: BLE001
        return None
    im.thumbnail((size, size), Image.LANCZOS)
    return im


def fit(d, text, size, maxw, weight='ExtraBold', minsize=30):
    while size > minsize and d.textlength(text, font=font(size, weight)) > maxw:
        size -= 2
    return font(size, weight)


def draw(m, out, lg_name, date_txt):
    sport = m['sport']
    acc = SPORT.get(sport, SIGNAL)
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    # мягкий свет за эмблемами в цвет вида спорта
    glow = Image.new('L', (W, H), 0)
    gd = ImageDraw.Draw(glow)
    for cx in (300, 900):
        for r in range(260, 0, -20):
            gd.ellipse((cx - r, 250 - r, cx + r, 250 + r), fill=int(36 * (1 - r / 260)) + 6)
    im.paste(Image.new('RGB', (W, H), acc), (0, 0), glow.point(lambda v: min(v, 60)))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 8), fill=acc)
    # верхняя строка: лига · дата
    d.text((60, 44), ('%s · %s' % (lg_name, date_txt)).upper(), font=font(30, 'Bold'), fill=INK2)
    # эмблемы и названия
    for cx, tid, nm in ((300, m['h'], m['hn']), (900, m['a'], m['an'])):
        c = crest(sport, tid, 210)
        if c:
            im.paste(c, (cx - c.width // 2, 245 - c.height // 2), c)
        f = fit(d, nm, 46, 470)
        d.text((cx, 392), nm, font=f, fill=INK, anchor='mm')
    res = m.get('res')
    if res:
        sc = '%d : %d' % (res[0], res[1])
        d.text((W // 2, 245), sc, font=font(96, 'ExtraBold'), fill=INK, anchor='mm')
        if res[2]:
            d.text((W // 2, 315), str(res[2]), font=font(28, 'Bold'), fill=INK2, anchor='mm')
        d.text((60, 470), 'Итог матча', font=font(30, 'Bold'), fill=INK3)
    else:
        d.text((W // 2, 245), '—', font=font(80, 'Bold'), fill=INK3, anchor='mm')
        md = m.get('md') or {}
        if md.get('p1') is not None:
            pr = [md['p1'], md.get('x') or 0, md['p2']]
            lab = ['Победа хозяев', 'Ничья' if sport == 'football' else 'Ничья в осн. время', 'Победа гостей']
            mx = max(pr)
            d.text((60, 448), 'Модель JARVIS', font=font(26, 'Bold'), fill=INK3)
            x0, y0, bw = 60, 486, (W - 120 - 24) // 3
            for i, v in enumerate(pr):
                x = x0 + i * (bw + 12)
                on = v == mx
                d.rounded_rectangle((x, y0, x + bw, y0 + 70), 14, fill=acc if on else (40, 52, 74))
                d.text((x + 20, y0 + 35), '%d %%' % round(v * 100), font=font(38, 'ExtraBold'), fill=(8, 18, 36) if on else INK, anchor='lm')
                d.text((x + bw - 18, y0 + 35), lab[i], font=font(21, 'SemiBold'), fill=(8, 18, 36) if on else INK2, anchor='rm')
        else:
            d.text((60, 470), 'Форма команд, личные встречи, таблица', font=font(30, 'Bold'), fill=INK3)
    # подпись
    d.text((60, 590), 'JARVIS', font=font(28, 'ExtraBold'), fill=INK, anchor='ls')
    d.text((W - 60, 590), 'Прогнозы по расчёту · Telegram @jarvibet', font=font(24, 'SemiBold'), fill=INK3, anchor='rs')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + '.tmp.jpg'
    im.save(tmp, 'JPEG', quality=84, optimize=True, progressive=True)
    # не переписываем файл, если картинка та же (git не видит лишних изменений)
    if os.path.exists(out) and open(out, 'rb').read() == open(tmp, 'rb').read():
        os.remove(tmp)
    else:
        os.replace(tmp, out)
