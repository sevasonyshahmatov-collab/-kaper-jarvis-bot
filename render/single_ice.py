"""Предматчевый постер на один матч в формате «Лёд» с ячейками-логотипами (как «Матчи дня» cells).

    import single_ice as si
    si.render(m, 'match.jpg', league='NHL')

m = dict(home, away, date='четверг, 1 октября', time='05:07', tag='ПРЕДСЕЗОННЫЙ МАТЧ',
         odds=(П1, Х, П2),            # основное время
         win=(П1, П2),                # победа с учётом ОТ и буллитов — можно None
         total=(6.0, больше, меньше), # можно None
         chance=66)                   # шанс хозяев на победу с ОТ, % — можно None
"""
import numpy as np
from PIL import Image, ImageDraw

import poster
import results_styles as rs
from results_styles2 import F, fit, club, spaced, OSW, UNB
from results_ice2 import _background, _paint, _light, MANROPE, NAVY, RED

S, W = rs.S, rs.W
H = 1180
GOLD = (255, 208, 90)
FOOT = 'КОЭФФИЦИЕНТЫ НА МОМЕНТ ПУБЛИКАЦИИ'   # без упоминания таблицы
INK = (40, 58, 92)


def _odds(v):
    return '—' if v is None else '%.2f' % v


def _cells(home, away, w, h, r, center, cw):
    """Две светлые ячейки с логотипами во всю ячейку и тёмное табло между ними."""
    a = np.zeros((h, w, 4), np.float32)
    half = (w - cw) // 2
    band = 12 * S
    a[..., :3] = _light(h, w)
    a[:, half:w - half, :3] = center
    a[:, half - band:half, :3] = club(home)
    a[:, w - half:w - half + band, :3] = club(away)
    for team, x0, x1 in ((home, 0, half - band), (away, w - half + band, w)):
        m = np.zeros((h, w), np.float32)
        m[:, x0:x1] = 1
        _paint(a, team, x0, x1, m, 'full', grow=1.0)
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=250)
    a[..., 3] = np.asarray(m, np.float32)
    card = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    ImageDraw.Draw(card).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, outline=(255, 255, 255, 190), width=3 * S)
    return card, half


def render(m, path, league='NHL', title='МАТЧ ДНЯ'):
    league = league.upper()
    m = rs._resolve([m], league)[0]
    home, away = m['home'], m['away']
    bg = _background(H, league)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    cx = W * S / 2
    rs._brand(d, cx, 58 * S, league, dark_text=True)
    spaced(d, (cx, 138 * S), title, F(OSW, 84 * S, 700), NAVY + (255,), 3 * S)
    sub = ' · '.join(x for x in (m.get('date', '').upper(), m.get('tag', '')) if x)
    spaced(d, (cx, 206 * S), sub, F(MANROPE, 20 * S, 800), INK + (255,), 3 * S)

    # ── ячейки с логотипами и табло
    top, ch, cw = 262, 360, 196
    card, half = _cells(home, away, (W - 64) * S, ch * S, 30 * S, (12, 14, 20), cw * S)
    poster._shadowed(ov, card, (32 * S, top * S), blur=16 * S, off=(0, 7 * S), color=(30, 60, 110, 80))
    d = ImageDraw.Draw(ov)
    cy = (top + ch / 2) * S
    d.text((cx, cy - 70 * S), 'НАЧАЛО', font=F(MANROPE, 15 * S, 800), anchor='mm', fill=(120, 128, 142, 255))
    d.text((cx, cy - 22 * S), m.get('time', ''), font=F(UNB, 44 * S, 700), anchor='mm', fill=(255, 255, 255, 255))
    d.text((cx, cy + 22 * S), 'МСК', font=F(MANROPE, 17 * S, 800), anchor='mm', fill=(160, 168, 182, 255))
    d.text((cx, cy + 86 * S), 'VS', font=F(UNB, 30 * S, 700), anchor='mm', fill=GOLD + (255,))

    # ── названия под ячейками
    ny = (top + ch + 50) * S
    colw = (W - 64 - cw) / 2
    for team, x in ((home, 32 + colw / 2), (away, W - 32 - colw / 2)):
        name = rs._short(team).upper()
        d.text((x * S, ny), name, font=fit(name, OSW, 52 * S, (colw - 30) * S, 700), anchor='mm', fill=NAVY + (255,))
    for lab, x in (('ХОЗЯЕВА', 32 + colw / 2), ('ГОСТИ', W - 32 - colw / 2)):
        spaced(d, (x * S, ny + 42 * S), lab, F(MANROPE, 14 * S, 800), (110, 124, 150, 255), 3 * S)

    # ── линия П1 / Х / П2 в основное время
    o = m.get('odds') or (None, None, None)
    fav = 0 if o[0] is None or o[0] == o[2] else (0 if o[0] < o[2] else 2)
    oy = 800 * S
    spaced(d, (cx, oy - 44 * S), 'ОСНОВНОЕ ВРЕМЯ', F(MANROPE, 15 * S, 800), INK + (255,), 3 * S)
    pw, gap = 250, 24
    for k, lab in enumerate(('П1', 'Х', 'П2')):
        x = cx + (k - 1) * (pw + gap) * S
        hot = k == fav and o[k] is not None
        box = (x - pw / 2 * S, oy - 6 * S, x + pw / 2 * S, oy + 70 * S)
        d.rounded_rectangle(box, radius=18 * S, fill=(12, 14, 20, 245) if hot else (255, 255, 255, 235),
                            outline=(255, 255, 255, 200) if hot else (200, 212, 228, 255), width=2 * S)
        d.text((x - 58 * S, oy + 32 * S), lab, font=F(MANROPE, 22 * S, 800), anchor='mm',
               fill=(150, 158, 172, 255) if hot else (110, 124, 150, 255))
        d.text((x + 30 * S, oy + 32 * S), _odds(o[k]), font=F(UNB, 34 * S, 700), anchor='mm',
               fill=GOLD + (255,) if hot else NAVY + (255,))

    # ── шансы на победу с ОТ: полоса в цветах клубов
    y = 930
    if m.get('chance') is not None:
        p = max(1, min(99, int(round(m['chance']))))
        spaced(d, (cx, y * S), 'ШАНСЫ НА ПОБЕДУ · С УЧЁТОМ ОТ И БУЛЛИТОВ', F(MANROPE, 15 * S, 800), INK + (255,), 3 * S)
        bx0, bx1, by = 60 * S, (W - 60) * S, (y + 34) * S
        bh = 46 * S
        split = bx0 + (bx1 - bx0) * p / 100
        bar = Image.new('RGBA', ov.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(bar)
        bd.rounded_rectangle((bx0, by, bx1, by + bh), radius=bh / 2, fill=club(away) + (255,))
        mask = Image.new('L', ov.size, 0)
        ImageDraw.Draw(mask).rectangle((0, 0, split, H * S), fill=255)
        left = Image.new('RGBA', ov.size, (0, 0, 0, 0))
        ImageDraw.Draw(left).rounded_rectangle((bx0, by, bx1, by + bh), radius=bh / 2, fill=club(home) + (255,))
        bar.paste(left, (0, 0), mask)
        bd.line(((split, by - 4 * S), (split, by + bh + 4 * S)), fill=(255, 255, 255, 255), width=4 * S)
        poster._shadowed(ov, bar, (0, 0), blur=8 * S, off=(0, 3 * S), color=(30, 60, 110, 60))
        d = ImageDraw.Draw(ov)
        fb = F(UNB, 26 * S, 700)
        d.text((bx0 + 24 * S, by + bh / 2), '%d%%' % p, font=fb, anchor='lm', fill=(255, 255, 255, 255),
               stroke_width=2 * S, stroke_fill=(0, 0, 0, 90))
        d.text((bx1 - 24 * S, by + bh / 2), '%d%%' % (100 - p), font=fb, anchor='rm', fill=(255, 255, 255, 255),
               stroke_width=2 * S, stroke_fill=(0, 0, 0, 90))
        y += 124

    # ── победа с ОТ и тотал одной строкой
    bits = []
    if m.get('win'):
        bits.append('ПОБЕДА С ОТ  %s / %s' % (_odds(m['win'][0]), _odds(m['win'][1])))
    if m.get('total'):
        t = m['total']
        bits.append('ТОТАЛ %s  Б %s · М %s' % (('%g' % t[0]).replace('.', ','), _odds(t[1]), _odds(t[2])))
    if bits:
        d.text((cx, y * S), '   ·   '.join(bits), font=F(MANROPE, 19 * S, 800), anchor='mm', fill=INK + (255,))

    d.text((cx, (H - 70) * S), FOOT, font=F(MANROPE, 13 * S, 800), anchor='mm', fill=(34, 50, 84, 255))
    spaced(d, (cx, (H - 40) * S), '@jarvibet', F(UNB, 20 * S, 700), RED + (255,), 2 * S)
    return rs._finish(bg, ov, H, path, grain=0.2)
