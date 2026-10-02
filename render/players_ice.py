"""«Игроки дня» — постер в стиле «Итогов дня» (лёд, иней сверху, шрифты «Боков»).

    import players_ice as pl
    pl.render(items, 'players.jpg', league='KHL', date_title='пятница, 2 октября')

items — по строке на игрока, сверху вниз:
    полевой: {name: 'Никита Гусев', team: 'СКА', g: 1, a: 2}
    вратарь: {name: 'Игорь Шестёркин', team: 'Рейнджерс', sv: 27, sa: 28}
Строка: слева ячейка в цвете клуба с эмблемой во всю ячейку, в центре тёмная плашка с именем
(фамилия крупно, имя над ней мелко) и клубом, справа табло: у полевого — очки золотом и «1 + 2» (голы + передачи),
у вратаря — процент отражённых и «27 из 28», сухой матч — отметкой.
Раскладка как у «Матчей дня» / «Итогов дня»: портрет 1080×1350 (от 3 строк), rows — мест под игроков
(в альбоме общее — плашки на одном уровне), cont=True — вместо заголовка и даты крупно «JARVIS | KHL/NHL».
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import poster
import results_styles as rs
from results_styles2 import F, fit, club, spaced, OSW, UNB
from results_ice2 import _background, _paint, _layout, _brand_big, MANROPE, NAVY, RED, ROW, GAP, HEAD, FOOT

S, W = rs.S, rs.W
DARK = (12, 14, 20)
BOARD = (22, 26, 36)
GOLD = (255, 194, 61)
CELL, STAT = 0.25, 0.25            # доли ширины: ячейка клуба, табло


def _is_gk(it):
    return it.get('sa') is not None


def _card(it, w, h, r):
    """Плашка строки: [клуб с эмблемой][полоска клуба][тёмная плашка имени][табло]."""
    team = it['team']
    cw, sw, band = int(w * CELL), int(w * STAT), 10 * S
    a = np.zeros((h, w, 4), np.float32)
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    c = np.array(club(team), np.float32)
    a[:, :cw, :3] = c * (1.06 - 0.22 * ys) + (255 - c) * np.clip(0.18 - ys * 0.5, 0, 1)   # клуб: блик сверху, темнее книзу
    a[:, cw:w - sw, :3] = DARK
    a[:, cw:cw + band, :3] = c                                                          # полоска клуба у плашки имени
    a[:, w - sw:, :3] = BOARD
    m = np.zeros((h, w), np.float32)
    m[:, :cw] = 1
    _paint(a, team, 0, cw, m, 'full', grow=1.15)
    mk = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mk).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=250)
    a[..., 3] = np.asarray(mk, np.float32)
    card = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    ImageDraw.Draw(card).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, outline=(255, 255, 255, 170), width=max(2, h // 60))
    return card


def _tag(d, cx, cy, text, k):
    f = F(MANROPE, int(12 * k) * S, 800)
    w, hh = f.getlength(text) + 16 * k * S, 11 * k * S
    d.rounded_rectangle((cx - w / 2, cy - hh, cx + w / 2, cy + hh), radius=8 * S, fill=(255, 255, 255, 235))
    d.text((cx, cy), text, font=f, anchor='mm', fill=(16, 22, 34, 255))


def _glow_text(ov, xy, text, font, color):
    glow = Image.new('RGBA', ov.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).text(xy, text, font=font, anchor='mm', fill=GOLD + (220,))
    ov.alpha_composite(glow.filter(ImageFilter.GaussianBlur(12 * S)))
    ImageDraw.Draw(ov).text(xy, text, font=font, anchor='mm', fill=color)


def _resolve(items, league):
    """Клубы НХЛ из таблицы («Рейнджерс») → ключи набора эмблем."""
    if league != 'NHL':
        return items
    import nhl
    out = []
    for it in items:
        it = dict(it)
        try:
            it['team'] = nhl.resolve(it['team'])
        except KeyError:
            pass
        out.append(it)
    return out


def render(items, path, league='KHL', title='ИГРОКИ ДНЯ', date_title=None, cont=False, rows=None):
    league = league.upper()
    items = _resolve(items, league)
    row, top, H = _layout(len(items), rows)
    k = min(row / ROW, 1.35)
    bg = _background(H, league)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    if cont:
        _brand_big(d, W * S / 2, 132 * S, league)
    else:
        rs._brand(d, W * S / 2, 58 * S, league, dark_text=True)
        spaced(d, (W * S / 2, 138 * S), title, F(OSW, 84 * S, 700), NAVY + (255,), 3 * S)
        if date_title:
            spaced(d, (W * S / 2, 206 * S), date_title.upper(), F(MANROPE, 21 * S, 800), (40, 58, 92, 255), 3 * S)
    w = (W - 64) * S
    cw, sw = int(w * CELL), int(w * STAT)
    for i, it in enumerate(items):
        y0 = top + i * (row + GAP)
        cy = (y0 + row / 2) * S
        h = int(row * S)
        poster._shadowed(ov, _card(it, w, h, 22 * S), (32 * S, y0 * S), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 70))
        d = ImageDraw.Draw(ov)
        # имя: фамилия крупно, имя мелко над ней; ниже — клуб (у вратаря — «вратарь · клуб»)
        x = 32 * S + cw + 34 * S
        room = w - cw - sw - 60 * S
        parts = str(it['name']).split()
        first, last = (' '.join(parts[:-1]), parts[-1]) if len(parts) > 1 else ('', parts[0] if parts else '')
        fl = fit(last.upper(), OSW, int(46 * k) * S, room, 700)
        if first:
            d.text((x, cy - 30 * k * S), first.upper(), font=F(MANROPE, int(15 * k) * S, 800), anchor='lm', fill=(150, 160, 178, 255))
        d.text((x, cy + 4 * k * S), last.upper(), font=fl, anchor='lm', fill=(255, 255, 255, 255))
        sub = ('вратарь · ' if _is_gk(it) else '') + rs._short(it['team'])
        d.text((x, cy + 40 * k * S), sub.upper(), font=F(MANROPE, int(13 * k) * S, 800), anchor='lm', fill=(120, 128, 142, 255))
        # табло
        sx = 32 * S + w - sw / 2
        if _is_gk(it):
            sv, sa = int(it['sv']), int(it['sa'])
            pct = '100' if sv == sa else ('%.1f' % (100.0 * sv / sa)).replace('.', ',') if sa else '—'
            _glow_text(ov, (sx, cy - 12 * k * S), pct + '%', F(UNB, int(38 * k) * S, 700), (255, 236, 170, 255))
            d = ImageDraw.Draw(ov)
            if sv == sa:
                _tag(d, sx, cy + 34 * k * S, 'СУХОЙ МАТЧ', k)
            else:
                d.text((sx, cy + 34 * k * S), '%d ИЗ %d' % (sv, sa), font=F(MANROPE, int(17 * k) * S, 800), anchor='mm', fill=(200, 206, 216, 255))
        else:
            g, a_ = int(it.get('g') or 0), int(it.get('a') or 0)
            _glow_text(ov, (sx, cy - 14 * k * S), str(g + a_), F(UNB, int(58 * k) * S, 700), (255, 236, 170, 255))
            d = ImageDraw.Draw(ov)
            d.text((sx, cy + 36 * k * S), '%d + %d' % (g, a_), font=F(MANROPE, int(19 * k) * S, 800), anchor='mm', fill=(200, 206, 216, 255))
    d.text((W * S / 2, (H - 70) * S), 'ОЧКИ: ГОЛЫ + ПЕРЕДАЧИ · ВРАТАРИ: ПРОЦЕНТ ОТРАЖЁННЫХ БРОСКОВ', font=F(MANROPE, 13 * S, 800),
           anchor='mm', fill=(34, 50, 84, 255))
    spaced(d, (W * S / 2, (H - 40) * S), '@jarvibet', F(UNB, 20 * S, 700), RED + (255,), 2 * S)
    return rs._finish(bg, ov, H, path, grain=0.2)


if __name__ == '__main__':                       # пример: python3 render/players_ice.py
    import nhl
    nhl.register()
    khl = [{'name': 'Никита Гусев', 'team': 'СКА', 'g': 1, 'a': 2}, {'name': 'Вадим Шипачёв', 'team': 'Динамо Москва', 'g': 0, 'a': 3},
           {'name': 'Джош Ливо', 'team': 'Металлург', 'g': 2, 'a': 0}, {'name': 'Станислав Галиев', 'team': 'Авангард', 'g': 1, 'a': 1},
           {'name': 'Александр Радулов', 'team': 'Локомотив', 'g': 0, 'a': 2}, {'name': 'Тимур Билялов', 'team': 'Ак Барс', 'sv': 31, 'sa': 31}]
    ours = [{'name': 'Никита Кучеров', 'team': 'Тампа-Бэй', 'g': 1, 'a': 2}, {'name': 'Матвей Мичков', 'team': 'Филадельфия', 'g': 1, 'a': 1},
            {'name': 'Артемий Панарин', 'team': 'Рейнджерс', 'g': 0, 'a': 2}, {'name': 'Кирилл Капризов', 'team': 'Миннесота', 'g': 1, 'a': 0},
            {'name': 'Игорь Шестёркин', 'team': 'Рейнджерс', 'sv': 27, 'sa': 29}]
    n = max(len(khl), len(ours))
    render(khl, 'players_khl.jpg', 'KHL', date_title='пятница, 2 октября', rows=n)
    render(ours, 'players_nhl.jpg', 'NHL', title='НАШИ В НХЛ', date_title='пятница, 2 октября', rows=n)
    print('players_khl.jpg, players_nhl.jpg')
