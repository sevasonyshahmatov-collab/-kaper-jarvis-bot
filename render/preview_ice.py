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
"""
import numpy as np
from PIL import Image, ImageDraw

import poster
import recap
import results_styles as rs
from results_styles2 import F, fit, club, spaced, _layered, _team_plate, TEK, RUSSO, EXOI
from results_ice2 import _background, _plate, _logo, _crown, NAVY, RED
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


def render(items, path, style='crown', league='KHL', title='МАТЧИ ДНЯ', date_title=None):
    league = league.upper()
    items = rs._resolve(items, league)
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
