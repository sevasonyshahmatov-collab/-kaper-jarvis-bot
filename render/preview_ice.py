"""«Матчи дня» (до игры) в трёх форматах «Итогов дня», которые выбраны 30.09.

    import preview_ice as pv
    pv.render(items, 'afisha.jpg', style='crown', league='KHL', date_title='среда, 30 сентября')

items: [{home, away, time: '19:30', odds: (П1, Х, П2)}] — odds можно не указывать (None).
Вместо счёта — время и П1/Х/П2 в основное время; вместо победителя выделен ФАВОРИТ
(у кого коэффициент ниже).
style:
  'crown'    — как «КОРОНА»: тёмная панель табло в центре со временем и линией, корона над логотипом фаворита. Tektur.
  'pucks'    — как «цветные плашки с шайбами»: коэффициенты П1 и П2 в шайбах, у фаворита чёрная. Exo 2 Italic.
  'favorite' — как «ЦВЕТ ПОБЕДЫ»: окрашена только сторона фаворита, время в белой таблетке. Russo One.
Только логотипы, без названий (как «Итоги дня» 10–12), шрифты «Боков» — Oswald, Unbounded, Manrope:
  'cells'    — светлые ячейки с логотипом во всю ячейку, тёмное табло: время, под ним П1 · Х · П2, фаворит золотом.
  'grid'     — скошенные ячейки как в сетке плей-офф: плашки цвета клуба с П1 и П2 (у фаворита крупнее), время в таблетке сверху, Х снизу.
  'columns'  — ячейки в цвете клуба, логотип во всю колонку, тёмное табло как у 'cells'.
"""
import numpy as np
from PIL import Image, ImageDraw

import poster
import recap
import results_styles as rs
from results_styles2 import F, fit, club, spaced, _layered, _team_plate, TEK, RUSSO, EXOI
from results_ice2 import _background, _plate, _logo, _crown, _cells, _brand_big, MANROPE, NAVY, RED
from results_ice2 import _layout as _layout_ri
from results_styles2 import OSW, UNB
from results_ice3 import _grad_box, _name, _ink, LIGHT, GREY, GOLD

S, W = rs.S, rs.W
ROW, GAP, HEAD, FOOT = 128, 16, 270, 120
FOOT_TEXT = recap.FOOT_ODDS                          # «…на момент публикации» — без упоминания таблицы


def _fav(it):
    """-1 — фаворит хозяева, 1 — гости, 0 — линии нет или равные шансы."""
    o = it.get('odds')
    if not o or o[0] == o[2]:
        return 0
    return -1 if o[0] < o[2] else 1


def _bg_plain(H, league):
    """Светлый «лёд» без инея (как у формата с шайбами)."""
    bg = rs._gradient(W, H, (236, 244, 251), (205, 224, 240), glow=(255, 255, 255, 120), glow_xy=(0.3, 0.1), glow_r=0.6)

    def rink(g):
        g.line(((0, H * 0.55), (W, H * 0.55)), fill=(214, 40, 57, 60), width=10)
        for y in (H * 0.36, H * 0.76):
            g.line(((0, y), (W, y)), fill=(40, 90, 200, 45), width=10)
    return rs._watermark(_layered(bg, rink), league, NAVY, 0.06)


def _header(d, league, title, date_title):
    rs._brand(d, W * S / 2, 58 * S, league, dark_text=True)
    d.text((W * S / 2, 136 * S), title, font=F(EXOI, 76 * S, 900), anchor='mm', fill=NAVY + (255,))
    if date_title:
        spaced(d, (W * S / 2, 206 * S), date_title.upper(), F(EXOI, 22 * S, 700), (40, 58, 92, 255), 3 * S)


def _footer(d, H):
    d.text((W * S / 2, (H - 70) * S), FOOT_TEXT, font=F(EXOI, 13 * S, 800), anchor='mm', fill=(34, 50, 84, 255))
    spaced(d, (W * S / 2, (H - 40) * S), '@jarvibet', F(EXOI, 24 * S, 800), RED + (255,), 2 * S)


def _odds_txt(v):
    return '—' if v is None else '%.2f' % v


CELLS = {'cells': 10, 'grid': 11, 'columns': 12}


def _render_cells(items, path, style, league, title, date_title, cont=False, rows=None):
    """Афиша в формате ячеек-логотипов: команда видна только эмблемой, в центре — время и линия.
    cont=True — продолжение (второй и следующие постеры дня): вместо заголовка и даты крупно «JARVIS | KHL/NHL»,
    ячейки на тех же местах.
    rows — число мест под матчи (общее для всех постеров альбома)."""
    variant = CELLS[style]
    row, top, H = _layout_ri(len(items), rows, HEAD, FOOT)
    k = min(row / ROW, 1.35)                       # текст на табло растёт с ячейкой, но не шире табло
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
    cx = W / 2 * S
    for i, it in enumerate(items):
        y0 = top + i * (row + GAP)
        cy = (y0 + row / 2) * S
        fav = _fav(it)
        o = it.get('odds') or (None, None, None)
        card = _cells(it, True, variant, (12, 14, 20), pre=True, row=row)
        if variant == 11:
            card, X, sk = card
        poster._shadowed(ov, card, (32 * S, y0 * S), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 70))
        d = ImageDraw.Draw(ov)
        if variant == 11:                          # П1 и П2 в плашках цвета клуба
            for (x0, x1), lab, v, hot in (((X[2], X[3]), 'П1', o[0], fav == -1), ((X[4], X[5]), 'П2', o[2], fav == 1)):
                x = 32 * S + (x0 + x1 + sk) / 2
                d.text((x, cy - 24 * S), lab, font=F(MANROPE, 14 * S, 800), anchor='mm', fill=(255, 255, 255, 190))
                d.text((x, cy + 12 * S), _odds_txt(v), font=F(UNB, 30 * S if hot else 26 * S, 800 if hot else 600), anchor='mm',
                       fill=(255, 255, 255, 255) if hot else (255, 255, 255, 185), stroke_width=(3 * S if hot else 0), stroke_fill=(0, 0, 0, 110))
            sx = cx + sk / 2 - 6 * S               # шов между плашками
            for ty, txt, f in ((cy - 50 * S, it.get('time', ''), F(UNB, 16 * S, 700)), (cy + 50 * S, 'Х ' + _odds_txt(o[1]), F(MANROPE, 14 * S, 800))):
                if ty > cy:
                    sx -= 2 * sk / 3               # внизу шов левее из-за скоса
                w = f.getlength(txt) + 22 * S
                d.rounded_rectangle((sx - w / 2, ty - 13 * S, sx + w / 2, ty + 13 * S), radius=9 * S, fill=(12, 14, 20, 245),
                                    outline=(255, 255, 255, 200), width=S)
                d.text((sx, ty), txt, font=f, anchor='mm', fill=(255, 236, 170, 255) if ty < cy else (220, 226, 236, 255))
            continue
        d.text((cx, cy - 20 * k * S), it.get('time', ''), font=F(UNB, int(40 * k) * S, 700), anchor='mm', fill=(255, 255, 255, 255))
        for j, dx, lab in ((0, -86, 'П1'), (1, 0, 'Х'), (2, 86, 'П2')):
            hot = (j == 0 and fav == -1) or (j == 2 and fav == 1)
            x = cx + dx * S
            d.text((x, cy + 18 * k * S), lab, font=F(MANROPE, int(12 * k) * S, 800), anchor='mm', fill=(120, 128, 142, 255))
            d.text((x, cy + 40 * k * S), _odds_txt(o[j]), font=F(MANROPE, int(21 * k) * S, 800), anchor='mm',
                   fill=(255, 208, 90, 255) if hot else (200, 206, 216, 255))
    d.text((W * S / 2, (H - 70) * S), FOOT_TEXT, font=F(MANROPE, 13 * S, 800), anchor='mm', fill=(34, 50, 84, 255))
    spaced(d, (W * S / 2, (H - 40) * S), '@jarvibet', F(UNB, 20 * S, 700), RED + (255,), 2 * S)
    return rs._finish(bg, ov, H, path, grain=0.2)


def render(items, path, style='crown', league='KHL', title='МАТЧИ ДНЯ', date_title=None, cont=False, rows=None):
    league = league.upper()
    items = rs._resolve(items, league)
    if style in CELLS:
        return _render_cells(items, path, style, league, title, date_title, cont, rows)
    H = HEAD + len(items) * (ROW + GAP) - GAP + FOOT
    bg = _bg_plain(H, league) if style == 'pucks' else _background(H, league)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _header(d, league, title, date_title)
    cx = W / 2 * S
    for i, it in enumerate(items):
        y0 = HEAD + i * (ROW + GAP)
        cy = (y0 + ROW / 2) * S
        fav = _fav(it)
        o = it.get('odds') or (None, None, None)
        ch, ca = club(it['home']), club(it['away'])
        lx, rx = (32 + ROW * 0.60) * S, (W - 32 - ROW * 0.60) * S

        if style == 'crown':
            plate = _plate(it['home'], it['away'], (W - 64) * S, ROW * S, 22 * S, True, (12, 14, 20), loser='none')
            poster._shadowed(ov, plate, (32 * S, y0 * S), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 70))
            _logo(ov, it['home'], lx, cy, 10)
            _logo(ov, it['away'], rx, cy, -10)
            d = ImageDraw.Draw(ov)
            for team, x, anchor in ((it['home'], 196, 'lm'), (it['away'], W - 196, 'rm')):
                name = rs._short(team)
                _name(d, (x * S, cy), name, fit(name, EXOI, 34 * S, 196 * S, 800), anchor, True)
            d.text((cx, cy - 22 * S), it.get('time', ''), font=F(TEK, 44 * S, 800, 100), anchor='mm', fill=(255, 255, 255, 255))
            fo = F(TEK, 20 * S, 700, 100)
            for k, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), o)):
                x = cx + (k - 1) * 84 * S
                hot = (k == 0 and fav == -1) or (k == 2 and fav == 1)
                d.text((x, cy + 24 * S), _odds_txt(v), font=fo, anchor='mm', fill=GOLD + (255,) if hot else (150, 158, 172, 255))
                d.text((x, cy + 46 * S), lab, font=F(TEK, 11 * S, 600, 100), anchor='mm', fill=(96, 104, 118, 255))
            if fav:
                _crown(d, lx if fav == -1 else rx, cy - 62 * S, S, GOLD + (255,))

        elif style == 'pucks':
            plate = _team_plate(it['home'], it['away'], (W - 64) * S, ROW * S, 22 * S)
            poster._shadowed(ov, plate, (32 * S, y0 * S), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 70))
            _logo(ov, it['home'], lx, cy, 10, size=int(ROW * 0.92))
            _logo(ov, it['away'], rx, cy, -10, size=int(ROW * 0.92))
            d = ImageDraw.Draw(ov)
            for team, x, anchor in ((it['home'], 190, 'lm'), (it['away'], W - 190, 'rm')):
                name = rs._short(team)
                _name(d, (x * S, cy), name, fit(name, EXOI, 34 * S, 200 * S, 800), anchor, True)
            # шайбы с П1 и П2: у фаворита чёрная, у второго светлая; сверху время, снизу ничья
            for k, v in ((0, o[0]), (2, o[2])):
                px = cx + (-54 if k == 0 else 54) * S
                r = 42 * S
                hot = (k == 0 and fav == -1) or (k == 2 and fav == 1)
                d.ellipse((px - r, cy - r, px + r, cy + r), fill=(18, 20, 26, 255) if hot else (230, 235, 242, 255))
                d.text((px, cy - 1 * S), _odds_txt(v), font=F(EXOI, 27 * S, 900), anchor='mm', fill=(255, 255, 255, 255) if hot else (110, 120, 138, 255))
            t, ft = it.get('time', ''), F(EXOI, 15 * S, 800)
            w = ft.getlength(t) + 20 * S
            d.rounded_rectangle((cx - w / 2, cy - 62 * S, cx + w / 2, cy - 40 * S), radius=11 * S, fill=(16, 22, 34, 235))
            d.text((cx, cy - 51 * S), t, font=ft, anchor='mm', fill=(255, 255, 255, 255))
            if o[1] is not None:
                xt = 'Х ' + _odds_txt(o[1])
                w = ft.getlength(xt) + 20 * S
                d.rounded_rectangle((cx - w / 2, cy + 40 * S, cx + w / 2, cy + 62 * S), radius=11 * S, fill=(255, 255, 255, 235))
                d.text((cx, cy + 51 * S), xt, font=ft, anchor='mm', fill=(70, 80, 100, 255))

        else:                                        # 'favorite'
            fc = ch if fav <= 0 else ca                # нет линии — красим хозяев
            plate = _grad_box((W - 64) * S, ROW * S, 22 * S, fc if fav <= 0 else LIGHT, LIGHT if fav <= 0 else fc, split=0.5)
            poster._shadowed(ov, plate, (32 * S, y0 * S), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 70))
            _logo(ov, it['home'], lx, cy, 10)
            _logo(ov, it['away'], rx, cy, -10)
            d = ImageDraw.Draw(ov)
            for team, x, anchor, on in ((it['home'], 196, 'lm', fav <= 0), (it['away'], W - 196, 'rm', fav == 1)):
                name = rs._short(team)
                f = fit(name, EXOI, 34 * S, 190 * S, 800)
                _name(d, (x * S, cy - 10 * S), name, f, anchor, True, on_color=on)
            # коэффициент на победу — под названием своей команды, у фаворита в цвете клуба
            for k, x, anchor in ((0, 196, 'lm'), (2, W - 196, 'rm')):
                hot = (k == 0 and fav == -1) or (k == 2 and fav == 1)
                lab = ('П1 ' if k == 0 else 'П2 ') + _odds_txt(o[k])
                fo = F(RUSSO, 20 * S)
                w = fo.getlength(lab) + 20 * S
                x1 = x * S if anchor == 'lm' else x * S - w
                d.rounded_rectangle((x1, cy + 18 * S, x1 + w, cy + 46 * S), radius=14 * S,
                                    fill=(255, 255, 255, 250) if hot else (222, 228, 237, 255))
                d.text((x1 + w / 2, cy + 32 * S), lab, font=fo, anchor='mm', fill=_ink(fc) + (255,) if hot else (92, 102, 122, 255))
            d.rounded_rectangle((cx - 96 * S, cy - 44 * S, cx + 96 * S, cy + 44 * S), radius=44 * S, fill=(255, 255, 255, 250),
                                outline=fc + (255,), width=4 * S)
            d.text((cx, cy - 10 * S), it.get('time', ''), font=F(RUSSO, 40 * S), anchor='mm', fill=NAVY + (255,))
            d.text((cx, cy + 24 * S), 'Х ' + _odds_txt(o[1]), font=F(RUSSO, 16 * S), anchor='mm', fill=GREY + (255,))
    _footer(d, H)
    return rs._finish(bg, ov, H, path, grain=0.2)
