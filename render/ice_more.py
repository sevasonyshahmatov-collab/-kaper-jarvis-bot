"""Новые форматы в стиле «Лёд» (03.10.2026) — на выбор, автоматика их пока не использует.

Общее с утверждёнными шаблонами: светлый лёд с инеем сверху, шапка JARVIS | KXL/NHL, заголовок Oswald,
цифры Unbounded, подписи Manrope, внизу @jarvibet, портрет 1080×1350, больше матчей — та же раскладка.

    import ice_more as im
    im.matchi(items, 'm.jpg', style='ticket', league='KHL', date_title='суббота, 3 октября')
    im.itogi(items, 'r.jpg', style='dots', league='KHL', date_title='…')
    im.single(m, 's.jpg', style='split', league='NHL')

Матчи дня (items: {home, away, time, odds=(П1, Х, П2) | None}):
  ticket   — БИЛЕТ: матч как билет с отрывным корешком, на корешке время; эмблемы и названия, П1·Х·П2 под ними
  bars     — ШАНСЫ: полоса шансов по линии (победа с учётом ОТ) в цветах клубов, проценты внутри
  puck     — ШАЙБА: большая шайба со временем по центру, эмблемы в кольцах клубного цвета
  timeline — ЛЕНТА: матчи сгруппированы по времени начала на вертикальной ленте (удобно для 8–12 матчей НХЛ)
  halves   — ПОЛОВИНКИ: сетка плиток в 2 колонки, плитка — верх хозяева / низ гости, время на шве
Итоги дня (items: {home, away, sh, sa, mark}):
  ticket   — БИЛЕТ: на корешке счёт, цифра победителя золотая; проигравший серым
  dots     — ГОЛЫ ШАЙБАМИ: сколько забили — столько шайб, у победителя чёрные
  halves   — ПОЛОВИНКИ: половина победителя в цвете клуба, проигравшего — серая, счёт на шве
Матч дня (m: {home, away, date, time, tag, odds, win, total}):
  split    — ДИАГОНАЛЬ: поле разрезано наискось цветами клубов, огромные эмблемы, белая карточка со временем и линией
  ticket   — БИЛЕТ: большой билет на льду, корешок со временем, эмблемы VS, линия и полоса шансов
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import poster
import recap
import results_styles as rs
from results_styles2 import F, fit, club, spaced, OSW, UNB, _sticker
from results_ice2 import _background, _layout, _brand_big, MANROPE, NAVY, RED

S, W = rs.S, rs.W
GOLD = (255, 194, 61)
GOLD_T = (255, 214, 120)
INK = (40, 58, 92)
DARK = (14, 18, 28)
GREY = (150, 158, 172)
HEAD, GAP, FOOT = 270, 16, 120
FOOT_ODDS = recap.FOOT_ODDS
FOOT_CHANCE = 'ШАНСЫ НА ПОБЕДУ С УЧЁТОМ ОТ — ПО ЛИНИИ БУКМЕКЕРОВ НА МОМЕНТ ПУБЛИКАЦИИ'


# ------------------------------------------------------------------ общее
def _resolve(items, league, keys=('home', 'away')):
    if league != 'NHL':
        return [dict(i) for i in items]
    import nhl
    out = []
    for it in items:
        it = dict(it)
        for k in keys:
            try:
                it[k] = nhl.resolve(it[k])
            except KeyError:
                pass
        out.append(it)
    return out


def _start(H, league, title, date_title, cont=False):
    bg = _background(H, league)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    if cont:
        _brand_big(d, W * S / 2, 132 * S, league)
    else:
        rs._brand(d, W * S / 2, 58 * S, league, dark_text=True)
        spaced(d, (W * S / 2, 138 * S), title, F(OSW, 84 * S, 700), NAVY + (255,), 3 * S)
        if date_title:
            spaced(d, (W * S / 2, 206 * S), date_title.upper(), F(MANROPE, 21 * S, 800), INK + (255,), 3 * S)
    return bg, ov


def _end(bg, ov, H, path, note=None):
    d = ImageDraw.Draw(ov)
    if note:
        d.text((W * S / 2, (H - 70) * S), note, font=F(MANROPE, 13 * S, 800), anchor='mm', fill=(34, 50, 84, 255))
    spaced(d, (W * S / 2, (H - 40) * S), '@jarvibet', F(UNB, 20 * S, 700), RED + (255,), 2 * S)
    return rs._finish(bg, ov, H, path, grain=0.2)


def _emb(team, size, grey=False, alpha=1.0):
    e = poster._raw_emblem(team, int(size), int(size))
    if grey:
        g = e.convert('LA').convert('RGBA')
        g.putalpha(e.getchannel('A').point(lambda v: int(v * 0.55)))
        e = g
    if alpha < 1:
        e.putalpha(e.getchannel('A').point(lambda v: int(v * alpha)))
    return e


def _put(ov, im, cx, cy, shadow=True, blur=8):
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    if shadow:
        poster._shadowed(ov, im, (x, y), blur=blur * S, off=(0, 4 * S), color=(20, 40, 80, 80))
    else:
        ov.alpha_composite(im, (x, y))


def _card(ov, box, r, fill, shadow=True, outline=(255, 255, 255, 190)):
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    c = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(c).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=fill, outline=outline, width=max(2, S))
    if shadow:
        poster._shadowed(ov, c, (x0, y0), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 70))
    else:
        ov.alpha_composite(c, (x0, y0))
    return c


def _chance(o):
    """Шанс хозяев на победу с учётом ОТ по линии 1X2: ничья делится пропорционально силе."""
    p1, x, p2 = (1 / v for v in o)
    s = p1 + x + p2
    p1, x, p2 = p1 / s, x / s, p2 / s
    return p1 + x * p1 / (p1 + p2)


def _fav(o):
    if not o or o[0] == o[2]:
        return 0
    return -1 if o[0] < o[2] else 1


def _odds_line(d, cx, y, o, size=17, dark=False):
    """«П1 1.68 · Х 4.00 · П2 4.44»: подписи серые, кэф фаворита золотой."""
    if not o:
        return
    fav = _fav(o)
    parts = [('П1', o[0], fav == -1), ('Х', o[1], False), ('П2', o[2], fav == 1)]
    fl, fv = F(MANROPE, int(size * 0.8) * S, 800), F(MANROPE, size * S, 800)
    gap, dot = 10 * S, '  ·  '
    widths = [fl.getlength(a + ' ') + fv.getlength('%.2f' % b) for a, b, _ in parts]
    total = sum(widths) + fv.getlength(dot) * 2
    x = cx - total / 2
    base = (230, 236, 246) if dark else INK
    for i, (lab, v, hot) in enumerate(parts):
        d.text((x, y), lab + ' ', font=fl, anchor='lm', fill=GREY + (255,))
        x += fl.getlength(lab + ' ')
        d.text((x, y), '%.2f' % v, font=fv, anchor='lm', fill=((200, 140, 20) if not dark else GOLD) + (255,) if hot else base + (255,))
        x += fv.getlength('%.2f' % v)
        if i < 2:
            d.text((x, y), dot, font=fv, anchor='lm', fill=GREY + (255,))
            x += fv.getlength(dot)


def _short(t):
    return rs._short(t).upper()


def _rows(n, rows):
    row, top, H = _layout(n, rows, HEAD, FOOT)
    return row, top, H, min(row / 128, 1.35)


# ------------------------------------------------------------------ МАТЧИ ДНЯ
def _ticket_shape(w, h, stub, r, notch):
    """Маска билета: скруглённый прямоугольник с полукруглыми вырезами на линии отрыва."""
    m = Image.new('L', (w, h), 0)
    dm = ImageDraw.Draw(m)
    dm.rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    dm.ellipse((stub - notch, -notch, stub + notch, notch), fill=0)
    dm.ellipse((stub - notch, h - notch, stub + notch, h + notch), fill=0)
    return m


def _ticket(ov, x0, y0, w, h, stub, stub_fill, body_fill=(252, 253, 255)):
    notch = int(h * 0.11)
    m = _ticket_shape(w, h, stub, 22 * S, notch)
    c = Image.new('RGBA', (w, h), body_fill + (255,))
    ImageDraw.Draw(c).rectangle((0, 0, stub, h), fill=stub_fill + (255,))
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    a = np.asarray(c, np.float32).copy()
    a[..., :3] *= (1.03 - 0.07 * ys)                                       # чуть светлее сверху
    c = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    c.putalpha(m)
    dd = ImageDraw.Draw(c)
    for yy in range(notch + 6 * S, h - notch - 6 * S, 16 * S):              # пунктир отрыва
        dd.line((stub, yy, stub, yy + 8 * S), fill=(170, 182, 200, 255), width=2 * S)
    poster._shadowed(ov, c, (x0, y0), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 75))
    return notch


def _m_ticket(items, path, league, title, date_title, cont, rows, results=False):
    row, top, H, k = _rows(len(items), rows)
    bg, ov = _start(H, league, title, date_title, cont)
    w, x0 = (W - 64) * S, 32 * S
    for i, it in enumerate(items):
        y0 = (top + i * (row + GAP)) * S
        h = int(row * S)
        stub = int(w * 0.25)
        hw = results and it['sh'] > it['sa']
        _ticket(ov, x0, y0, w, h, stub, DARK)
        d = ImageDraw.Draw(ov)
        cy = y0 + h / 2
        sx = x0 + stub / 2
        if results:
            wv, lv = (it['sh'], it['sa'])
            fb = F(UNB, int(44 * k) * S, 700)
            d.text((sx - 26 * k * S, cy - 6 * k * S), str(wv), font=fb, anchor='mm', fill=(GOLD_T if hw else (110, 118, 134)) + (255,))
            d.text((sx, cy - 8 * k * S), ':', font=F(UNB, int(30 * k) * S, 500), anchor='mm', fill=(110, 118, 134, 255))
            d.text((sx + 26 * k * S, cy - 6 * k * S), str(lv), font=fb, anchor='mm', fill=((110, 118, 134) if hw else GOLD_T) + (255,))
            mk = rs.MARK_TEXT.get(it.get('mark') or '', '')
            d.text((sx, cy + 34 * k * S), mk or 'ОСНОВНОЕ ВРЕМЯ', font=F(MANROPE, int(11 * k) * S, 800), anchor='mm', fill=(150, 160, 178, 255))
        else:
            d.text((sx, cy - 8 * k * S), it.get('time', ''), font=F(UNB, int(36 * k) * S, 700), anchor='mm', fill=(255, 255, 255, 255))
            d.text((sx, cy + 28 * k * S), 'МСК', font=F(MANROPE, int(12 * k) * S, 800), anchor='mm', fill=(150, 160, 178, 255))
        # основная часть: эмблема — названия — эмблема
        bx0, bx1 = x0 + stub, x0 + w
        es = int(h * 0.56)
        lx, rx = bx0 + 24 * S + es / 2, bx1 - 24 * S - es / 2
        lose_h = results and not hw
        lose_a = results and hw
        _put(ov, _emb(it['home'], es, grey=lose_h), lx, cy - (8 * S if it.get('odds') and not results else 0), blur=6)
        _put(ov, _emb(it['away'], es, grey=lose_a), rx, cy - (8 * S if it.get('odds') and not results else 0), blur=6)
        d = ImageDraw.Draw(ov)
        mx = (lx + rx) / 2
        room = (rx - lx) - es - 20 * S
        fh = fit(_short(it['home']), OSW, int(30 * k) * S, room, 700)
        fa = fit(_short(it['away']), OSW, int(30 * k) * S, room, 700)
        ny = cy - (18 * k * S if (it.get('odds') and not results) else 6 * k * S)
        d.text((mx, ny - 20 * k * S), _short(it['home']), font=fh, anchor='mm', fill=(GREY if lose_h else NAVY) + (255,))
        d.line((mx - 18 * S, ny + 2 * k * S, mx + 18 * S, ny + 2 * k * S), fill=(190, 198, 212, 255), width=2 * S)
        d.text((mx, ny + 24 * k * S), _short(it['away']), font=fa, anchor='mm', fill=(GREY if lose_a else NAVY) + (255,))
        if it.get('odds') and not results:
            _odds_line(d, mx, cy + 40 * k * S, it['odds'], size=int(15 * k))
    return _end(bg, ov, H, path, None if results else FOOT_ODDS)


def _m_bars(items, path, league, title, date_title, cont, rows):
    row, top, H, k = _rows(len(items), rows)
    bg, ov = _start(H, league, title, date_title, cont)
    w, x0 = (W - 64) * S, 32 * S
    for i, it in enumerate(items):
        y0 = (top + i * (row + GAP)) * S
        h = int(row * S)
        _card(ov, (x0, y0, x0 + w, y0 + h), 22 * S, (252, 253, 255, 245))
        d = ImageDraw.Draw(ov)
        cy = y0 + h / 2
        es = int(h * 0.62)
        lx, rx = x0 + 26 * S + es / 2, x0 + w - 26 * S - es / 2
        _put(ov, _emb(it['home'], es), lx, cy, blur=6)
        _put(ov, _emb(it['away'], es), rx, cy, blur=6)
        d = ImageDraw.Draw(ov)
        bx0, bx1 = lx + es / 2 + 22 * S, rx - es / 2 - 22 * S
        bh = int(h * 0.26)
        by0 = cy - bh / 2 + 6 * k * S
        o = it.get('odds')
        p = _chance(o) if o else 0.5
        split = bx0 + (bx1 - bx0) * p
        ch, ca = club(it['home']), club(it['away'])
        d.rounded_rectangle((bx0, by0, bx1, by0 + bh), radius=bh / 2, fill=ca + (255,))
        d.rounded_rectangle((bx0, by0, max(bx0 + bh, split), by0 + bh), radius=bh / 2, fill=ch + (255,))
        d.rectangle((split - bh / 2, by0, split, by0 + bh), fill=ch + (255,))
        d.line((split, by0 - 3 * S, split, by0 + bh + 3 * S), fill=(255, 255, 255, 255), width=3 * S)
        fp = F(UNB, int(22 * k) * S, 700)
        if o:
            d.text((bx0 + 16 * S, by0 + bh / 2), '%d%%' % round(p * 100), font=fp, anchor='lm', fill=(255, 255, 255, 255), stroke_width=S, stroke_fill=(0, 0, 0, 60))
            d.text((bx1 - 16 * S, by0 + bh / 2), '%d%%' % round((1 - p) * 100), font=fp, anchor='rm', fill=(255, 255, 255, 255), stroke_width=S, stroke_fill=(0, 0, 0, 60))
        # время и названия над полосой
        fn = F(OSW, int(22 * k) * S, 700)
        d.text((bx0 + 4 * S, by0 - 22 * k * S), _short(it['home']), font=fit(_short(it['home']), OSW, int(22 * k) * S, (bx1 - bx0) * 0.4, 700), anchor='lm', fill=NAVY + (255,))
        d.text((bx1 - 4 * S, by0 - 22 * k * S), _short(it['away']), font=fit(_short(it['away']), OSW, int(22 * k) * S, (bx1 - bx0) * 0.4, 700), anchor='rm', fill=NAVY + (255,))
        tw = F(UNB, int(17 * k) * S, 700).getlength(it.get('time', '')) + 24 * S
        tx = (bx0 + bx1) / 2
        d.rounded_rectangle((tx - tw / 2, by0 - 36 * k * S, tx + tw / 2, by0 - 8 * k * S), radius=10 * S, fill=DARK + (255,))
        d.text((tx, by0 - 22 * k * S), it.get('time', ''), font=F(UNB, int(17 * k) * S, 700), anchor='mm', fill=GOLD_T + (255,))
        if o:
            _odds_line(d, tx, by0 + bh + 22 * k * S, o, size=int(14 * k))
    return _end(bg, ov, H, path, FOOT_CHANCE)


def _puck(size, label, k, sub=''):
    """Шайба в лёгком наклоне: верх-эллипс, ребро; на верхе — время (и ничья мелко под ним)."""
    w, h = size, int(size * 0.62)
    im = Image.new('RGBA', (w, h + int(size * 0.18)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    th = int(size * 0.18)
    d.rounded_rectangle((0, h / 2, w, h / 2 + th), radius=2, fill=(8, 10, 14, 255))
    d.ellipse((0, th, w, h + th), fill=(8, 10, 14, 255))
    d.ellipse((0, 0, w, h), fill=(24, 28, 36, 255))
    d.ellipse((w * 0.08, h * 0.1, w * 0.92, h * 0.9), outline=(60, 66, 80, 255), width=max(2, size // 90))
    d.text((w / 2, h / 2 - (size * 0.05 if sub else 0)), label, font=F(UNB, int(size * 0.17), 700), anchor='mm', fill=(255, 255, 255, 255))
    if sub:
        d.text((w / 2, h / 2 + size * 0.12), sub, font=F(MANROPE, int(size * 0.07), 800), anchor='mm', fill=(150, 158, 172, 255))
    return im


def _ring(team, size):
    """Эмблема в белом круге с кольцом клубного цвета."""
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = club(team)
    d.ellipse((0, 0, size - 1, size - 1), fill=c + (255,))
    b = max(3, size // 16)
    d.ellipse((b, b, size - 1 - b, size - 1 - b), fill=(252, 253, 255, 255))
    e = _emb(team, int(size * 0.66))
    im.alpha_composite(e, ((size - e.width) // 2, (size - e.height) // 2))
    return im


def _m_puck(items, path, league, title, date_title, cont, rows):
    row, top, H, k = _rows(len(items), rows)
    bg, ov = _start(H, league, title, date_title, cont)
    w, x0 = (W - 64) * S, 32 * S
    for i, it in enumerate(items):
        y0 = (top + i * (row + GAP)) * S
        h = int(row * S)
        _card(ov, (x0, y0, x0 + w, y0 + h), h // 2, (252, 253, 255, 240))
        cy = y0 + h / 2
        rs_ = int(h * 0.78)
        lx, rx = x0 + h / 2, x0 + w - h / 2
        _put(ov, _ring(it['home'], rs_), lx, cy, blur=6)
        _put(ov, _ring(it['away'], rs_), rx, cy, blur=6)
        o = it.get('odds')
        pk = _puck(int(h * 1.08), it.get('time', ''), k, ('Х %.2f' % o[1]) if o else '')
        _put(ov, pk, x0 + w / 2, cy, blur=10)
        d = ImageDraw.Draw(ov)
        room = (w / 2 - h / 2 - pk.width / 2 - rs_ / 2) - 30 * S
        nx_l = lx + rs_ / 2 + 18 * S
        nx_r = rx - rs_ / 2 - 18 * S
        d.text((nx_l, cy - 4 * S), _short(it['home']), font=fit(_short(it['home']), OSW, int(30 * k) * S, room, 700), anchor='lm', fill=NAVY + (255,))
        d.text((nx_r, cy - 4 * S), _short(it['away']), font=fit(_short(it['away']), OSW, int(30 * k) * S, room, 700), anchor='rm', fill=NAVY + (255,))
        if o:
            fav = _fav(o)
            fv = F(MANROPE, int(17 * k) * S, 800)
            for x, lab, v, hot, an in ((nx_l, 'П1', o[0], fav == -1, 'lm'), (nx_r, 'П2', o[2], fav == 1, 'rm')):
                d.text((x, cy + 30 * k * S), lab + ' %.2f' % v, font=fv, anchor=an, fill=((200, 140, 20) if hot else INK) + (255,))
    return _end(bg, ov, H, path, FOOT_ODDS)


def _m_timeline(items, path, league, title, date_title, cont, rows):
    groups = []
    for it in items:
        if groups and groups[-1][0] == it.get('time', ''):
            groups[-1][1].append(it)
        else:
            groups.append((it.get('time', ''), [it]))
    n = len(items) + 0.55 * len(groups)
    row, top, H, k = _rows(max(1, math.ceil(n)), max(rows or 0, math.ceil(n)))
    row = min(row, 170)
    bg, ov = _start(H, league, title, date_title, cont)
    d = ImageDraw.Draw(ov)
    lx = 92 * S
    used = len(items) * (row * 0.78 + 12) + len(groups) * row * 0.55
    y = top + max(0, (H - FOOT - top - used) / 2 - 10)
    line_top = y * S
    for tm, grp in groups:
        gy = y * S + row * 0.27 * S
        d = ImageDraw.Draw(ov)
        d.ellipse((lx - 15 * S, gy - 15 * S, lx + 15 * S, gy + 15 * S), fill=DARK + (255,))
        d.ellipse((lx - 7 * S, gy - 7 * S, lx + 7 * S, gy + 7 * S), fill=GOLD + (255,))
        d.text((lx + 34 * S, gy), tm + ' МСК', font=F(UNB, int(24 * min(k, 1.1)) * S, 700), anchor='lm', fill=NAVY + (255,))
        d.text((lx + 34 * S + F(UNB, int(24 * min(k, 1.1)) * S, 700).getlength(tm + ' МСК') + 18 * S, gy),
               '%d %s' % (len(grp), 'матч' if len(grp) == 1 else 'матча' if len(grp) < 5 else 'матчей'), font=F(MANROPE, 15 * S, 800), anchor='lm', fill=GREY + (255,))
        y += row * 0.55
        for it in grp:
            ph = int(row * 0.78 * S)
            py0 = int(y * S)
            px0, px1 = lx + 34 * S, (W - 32) * S
            _card(ov, (px0, py0, px1, py0 + ph), ph // 2, (252, 253, 255, 245))
            d = ImageDraw.Draw(ov)
            cy = py0 + ph / 2
            es = int(ph * 0.74)
            _put(ov, _emb(it['home'], es), px0 + ph / 2 + 4 * S, cy, blur=4)
            _put(ov, _emb(it['away'], es), px1 - ph / 2 - 4 * S, cy, blur=4)
            d = ImageDraw.Draw(ov)
            mid = (px0 + px1) / 2
            room = (px1 - px0) / 2 - ph - 50 * S
            fsz = int(min(34, ph / S * 0.42)) * S
            hx, ax = px0 + ph + 14 * S, px1 - ph - 14 * S                   # названия — у своих эмблем
            fh, fa = fit(_short(it['home']), OSW, fsz, room, 700), fit(_short(it['away']), OSW, fsz, room, 700)
            d.text((hx, cy), _short(it['home']), font=fh, anchor='lm', fill=NAVY + (255,))
            d.text((ax, cy), _short(it['away']), font=fa, anchor='rm', fill=NAVY + (255,))
            o = it.get('odds')
            f = _fav(o) if o else 0
            d.text((mid, cy), '—', font=F(OSW, fsz, 500), anchor='mm', fill=GREY + (255,))
            if f:                                                          # фаворит по линии — золотая точка у названия
                fx = hx + fh.getlength(_short(it['home'])) + 16 * S if f == -1 else ax - fa.getlength(_short(it['away'])) - 16 * S
                d.ellipse((fx - 7 * S, cy - 7 * S, fx + 7 * S, cy + 7 * S), fill=GOLD + (255,))
            y += row * 0.78 + 12
        d = ImageDraw.Draw(ov)
    d = ImageDraw.Draw(ov)
    ov_line = Image.new('RGBA', ov.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov_line).line((lx, line_top + row * 0.27 * S, lx, y * S - row * 0.3 * S), fill=NAVY + (90,), width=4 * S)
    ov_line.alpha_composite(ov)
    note = 'ФАВОРИТ ПО ЛИНИИ БУКМЕКЕРОВ · ВРЕМЯ МОСКОВСКОЕ'
    dl = ImageDraw.Draw(ov_line)
    fx = W * S / 2 - F(MANROPE, 13 * S, 800).getlength(note) / 2 - 16 * S
    dl.ellipse((fx - 6 * S, (H - 70) * S - 6 * S, fx + 6 * S, (H - 70) * S + 6 * S), fill=GOLD + (255,))
    return _end(bg, ov_line, H, path, note)


def _halves_tile(it, w, h, results=False):
    """Плитка: верх — хозяева, низ — гости; у проигравшего в итогах половина серая."""
    a = np.zeros((h, w, 4), np.float32)
    half = h // 2
    ch, ca = np.array(club(it['home']), np.float32), np.array(club(it['away']), np.float32)
    if results:
        hw = it['sh'] > it['sa']
        grey = lambda c: (c * 0.25 + c.mean() * 0.75) * 0.55 + 60
        ch, ca = (ch, grey(ca)) if hw else (grey(ch), ca)
    ys = np.linspace(0, 1, half, dtype=np.float32)[:, None, None]
    a[:half, :, :3] = ch * (1.08 - 0.25 * ys)
    a[half:, :, :3] = ca * (1.08 - 0.25 * ys[:h - half] if h - half == half else 1.0)
    a[..., 3] = 255
    tile = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    for team, y0, y1, lost in ((it['home'], 0, half, results and it['sh'] < it['sa']), (it['away'], half, h, results and it['sa'] < it['sh'])):
        e = _emb(team, int((y1 - y0) * 0.80), grey=lost, alpha=0.9 if lost else 1.0)
        if not lost:
            e = _sticker(e, 4 * S)                                         # белая обводка: эмблема не сливается с цветом своей половины
        layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        layer.alpha_composite(e, (int(w * 0.30 - e.width / 2), int((y0 + y1) / 2 - e.height / 2)))
        m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(m).rectangle((0, y0, w, y1), fill=255)
        layer.putalpha(Image.fromarray(np.minimum(np.asarray(layer.getchannel('A')), np.asarray(m))))
        tile.alpha_composite(layer)
    mk = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mk).rounded_rectangle((0, 0, w - 1, h - 1), radius=26 * S, fill=255)
    tile.putalpha(mk)
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, w - 1, h - 1), radius=26 * S, outline=(255, 255, 255, 200), width=3 * S)
    return tile


def _halves(items, path, league, title, date_title, cont, rows, results=False):
    n = len(items)
    cols = 2
    rws = max(math.ceil(n / cols), math.ceil((rows or 0) / cols))
    avail = 1350 - HEAD - FOOT
    th = int(min(330, (avail + 22) / rws - 22))
    H = 1350 if rws >= 2 else HEAD + th + FOOT
    top = HEAD + (avail - (rws * (th + 22) - 22)) // 2 if rws >= 2 else HEAD
    bg, ov = _start(H, league, title, date_title, cont)
    tw = (W - 64 - 22) // 2
    for i, it in enumerate(items):
        r, c = divmod(i, cols)
        if r == n // cols and n % cols:                                   # последняя неполная строка — по центру
            x = (W - tw) // 2
        else:
            x = 32 + c * (tw + 22)
        y = top + r * (th + 22)
        tile = _halves_tile(it, tw * S, th * S, results)
        poster._shadowed(ov, tile, (x * S, y * S), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 75))
        d = ImageDraw.Draw(ov)
        cx, cy = (x + tw * 0.72) * S, (y + th / 2) * S
        k = min(th / 300, 1.2)
        if results:
            hw = it['sh'] > it['sa']
            bw, bh = 150 * k * S, 64 * k * S
            d.rounded_rectangle((cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2), radius=bh / 2, fill=DARK + (255,), outline=(255, 255, 255, 220), width=3 * S)
            fb = F(UNB, int(32 * k) * S, 700)
            d.text((cx - 30 * k * S, cy), str(it['sh']), font=fb, anchor='mm', fill=(GOLD_T if hw else (120, 128, 142)) + (255,))
            d.text((cx, cy - 2 * S), ':', font=F(UNB, int(24 * k) * S, 500), anchor='mm', fill=(120, 128, 142, 255))
            d.text((cx + 30 * k * S, cy), str(it['sa']), font=fb, anchor='mm', fill=((120, 128, 142) if hw else GOLD_T) + (255,))
            mk = rs.MARK_TEXT.get(it.get('mark') or '', '')
            if mk:
                f = F(MANROPE, int(11 * k) * S, 800)
                tw2 = f.getlength(mk) + 18 * S
                d.rounded_rectangle((cx - tw2 / 2, cy + bh / 2 + 6 * S, cx + tw2 / 2, cy + bh / 2 + 30 * S), radius=10 * S, fill=(255, 255, 255, 235))
                d.text((cx, cy + bh / 2 + 18 * S), mk, font=f, anchor='mm', fill=DARK + (255,))
        else:
            bw, bh = 150 * k * S, 64 * k * S
            d.rounded_rectangle((cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2), radius=bh / 2, fill=DARK + (255,), outline=(255, 255, 255, 220), width=3 * S)
            d.text((cx, cy), it.get('time', ''), font=F(UNB, int(26 * k) * S, 700), anchor='mm', fill=(255, 255, 255, 255))
            o = it.get('odds')
            if o:
                fav = _fav(o)
                for yy, v, hot in ((cy - th * 0.27 * S, o[0], fav == -1), (cy + th * 0.27 * S, o[2], fav == 1)):
                    t = '%.2f' % v
                    f = F(UNB, int(20 * k) * S, 700)
                    d.text((cx, yy), t, font=f, anchor='mm', fill=(GOLD_T if hot else (255, 255, 255)) + (255,), stroke_width=2 * S, stroke_fill=(0, 0, 0, 90))
    return _end(bg, ov, H, path, None if results else FOOT_ODDS)


# ------------------------------------------------------------------ ИТОГИ ДНЯ
def _pucks_row(d, x_from, cy, n, size, color, direction):
    """n маленьких шайб в ряд от x_from в сторону direction (+1 вправо, -1 влево)."""
    step = size * 1.25
    for j in range(n):
        x = x_from + direction * (size / 2 + j * step)
        d.ellipse((x - size / 2, cy - size * 0.32 + size * 0.1, x + size / 2, cy + size * 0.32 + size * 0.1), fill=(0, 0, 0, 70))
        d.ellipse((x - size / 2, cy - size * 0.32, x + size / 2, cy + size * 0.32), fill=color + (255,))


def _r_dots(items, path, league, title, date_title, cont, rows):
    row, top, H, k = _rows(len(items), rows)
    bg, ov = _start(H, league, title, date_title, cont)
    w, x0 = (W - 64) * S, 32 * S
    for i, it in enumerate(items):
        y0 = (top + i * (row + GAP)) * S
        h = int(row * S)
        _card(ov, (x0, y0, x0 + w, y0 + h), 22 * S, (252, 253, 255, 245))
        cy = y0 + h / 2
        hw = it['sh'] > it['sa']
        es = int(h * 0.66)
        lx, rx = x0 + 22 * S + es / 2, x0 + w - 22 * S - es / 2
        _put(ov, _emb(it['home'], es, grey=not hw), lx, cy, blur=6)
        _put(ov, _emb(it['away'], es, grey=hw), rx, cy, blur=6)
        d = ImageDraw.Draw(ov)
        cx = x0 + w / 2
        bw = 120 * k * S
        d.rounded_rectangle((cx - bw / 2, y0 + 12 * S, cx + bw / 2, y0 + h - 12 * S), radius=18 * S, fill=DARK + (255,))
        fb = F(UNB, int(34 * k) * S, 700)
        d.text((cx - 28 * k * S, cy - 4 * S), str(it['sh']), font=fb, anchor='mm', fill=(GOLD_T if hw else (110, 118, 134)) + (255,))
        d.text((cx, cy - 6 * S), ':', font=F(UNB, int(24 * k) * S, 500), anchor='mm', fill=(110, 118, 134, 255))
        d.text((cx + 28 * k * S, cy - 4 * S), str(it['sa']), font=fb, anchor='mm', fill=((110, 118, 134) if hw else GOLD_T) + (255,))
        mk = rs.MARK_TEXT.get(it.get('mark') or '', '')
        if mk:
            d.text((cx, cy + 30 * k * S), mk.replace('ОТ / БУЛЛИТЫ', 'ОТ/Б'), font=F(MANROPE, int(10 * k) * S, 800), anchor='mm', fill=(170, 178, 192, 255))
        ps = int(min(30 * k * S, ((cx - bw / 2) - (lx + es / 2) - 30 * S) / 8.2))
        _pucks_row(d, cx - bw / 2 - 16 * S, cy, it['sh'], ps, (12, 14, 20) if hw else (178, 186, 198), -1)
        _pucks_row(d, cx + bw / 2 + 16 * S, cy, it['sa'], ps, (178, 186, 198) if hw else (12, 14, 20), +1)
    return _end(bg, ov, H, path, 'ОДНА ШАЙБА — ОДИН ГОЛ · У ПОБЕДИТЕЛЯ ЧЁРНЫЕ')


# ------------------------------------------------------------------ МАТЧ ДНЯ
def _s_split(m, path, league, title):
    m = _resolve([m], league)[0]
    H = 1350
    ch, ca = np.array(club(m['home']), np.float32), np.array(club(m['away']), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    side = (xx / W + yy / H * 0.55) < 0.78                                 # диагональ: хозяева слева-сверху
    a = np.where(side[..., None], ch, ca)
    a = a * (1.06 - 0.2 * (yy / H))[..., None]
    bg = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    # огромные эмблемы тон-в-тон за края
    for team, cx, cy, sz, ang in ((m['home'], W * 0.22, H * 0.25, 900, 12), (m['away'], W * 0.80, H * 0.80, 900, -12)):
        e = poster._raw_emblem(team, sz, sz).rotate(ang, Image.BICUBIC, expand=True)
        g = np.asarray(e.convert('L'), np.float32) / 255
        al = np.asarray(e.getchannel('A'), np.float32) / 255 * 0.5
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        tone = np.zeros((e.height, e.width, 4), np.float32)
        base = np.array(club(team), np.float32)
        tone[..., :3] = base * (0.55 + 0.9 * g[..., None])
        tone[..., 3] = al * 255
        lay.alpha_composite(Image.fromarray(np.clip(tone, 0, 255).astype(np.uint8), 'RGBA'), (int(cx - e.width / 2), int(cy - e.height / 2)))
        mk = Image.fromarray(((side if team == m['home'] else ~side) * 255).astype(np.uint8), 'L')
        lay.putalpha(Image.fromarray(np.minimum(np.asarray(lay.getchannel('A')), np.asarray(mk))))
        bg.alpha_composite(lay)
    rng = np.random.default_rng(7)
    noise = (rng.normal(0, 9, (H, W, 1))).astype(np.float32)
    arr = np.asarray(bg, np.float32).copy()
    arr[..., :3] += noise
    bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    rs._brand(d, W * S / 2, 58 * S, league, dark_text=False)
    # белая карточка по центру
    cw, chh = 800, 700
    x0, y0 = (W - cw) // 2, 350
    card = _card(ov, (x0 * S, y0 * S, (x0 + cw) * S, (y0 + chh) * S), 34 * S, (252, 253, 255, 250), outline=(255, 255, 255, 255))
    d = ImageDraw.Draw(ov)
    cx = W * S / 2
    spaced(d, (cx, (y0 + 62) * S), title, F(OSW, 58 * S, 700), NAVY + (255,), 3 * S)
    sub = ' · '.join(x for x in (m.get('date', ''), m.get('tag', '')) if x)
    if sub:
        d.text((cx, (y0 + 112) * S), sub.upper(), font=F(MANROPE, 16 * S, 800), anchor='mm', fill=INK + (255,))
    es = 230
    for team, ex in ((m['home'], x0 + 145), (m['away'], x0 + cw - 145)):
        _put(ov, _emb(team, es * S), ex * S, (y0 + 285) * S, blur=8)
    d = ImageDraw.Draw(ov)
    d.text((cx, (y0 + 262) * S), m.get('time', ''), font=F(UNB, 50 * S, 700), anchor='mm', fill=NAVY + (255,))
    d.text((cx, (y0 + 312) * S), 'МСК', font=F(MANROPE, 16 * S, 800), anchor='mm', fill=GREY + (255,))
    for team, ex in ((m['home'], x0 + 145), (m['away'], x0 + cw - 145)):
        d.text((ex * S, (y0 + 440) * S), _short(team), font=fit(_short(team), OSW, 36 * S, 280 * S, 700), anchor='mm', fill=NAVY + (255,))
    o = m.get('odds')
    if o:
        _odds_line(d, cx, (y0 + 516) * S, o, size=22)
        p = _chance(o)
        bx0, bx1, by = (x0 + 70) * S, (x0 + cw - 70) * S, (y0 + 580) * S
        bh = 34 * S
        split = bx0 + (bx1 - bx0) * p
        d.rounded_rectangle((bx0, by, bx1, by + bh), radius=bh / 2, fill=club(m['away']) + (255,))
        d.rounded_rectangle((bx0, by, max(bx0 + bh, split), by + bh), radius=bh / 2, fill=club(m['home']) + (255,))
        d.rectangle((split - bh / 2, by, split, by + bh), fill=club(m['home']) + (255,))
        d.line((split, by - 3 * S, split, by + bh + 3 * S), fill=(255, 255, 255, 255), width=3 * S)
        fp = F(UNB, 18 * S, 700)
        d.text((bx0 + 14 * S, by + bh / 2), '%d%%' % round(p * 100), font=fp, anchor='lm', fill=(255, 255, 255, 255))
        d.text((bx1 - 14 * S, by + bh / 2), '%d%%' % round((1 - p) * 100), font=fp, anchor='rm', fill=(255, 255, 255, 255))
        d.text((cx, by + bh + 26 * S), 'ШАНСЫ НА ПОБЕДУ С УЧЁТОМ ОТ', font=F(MANROPE, 13 * S, 800), anchor='mm', fill=GREY + (255,))
    extra = []
    if m.get('win'):
        extra.append('ПОБЕДА С ОТ %.2f / %.2f' % tuple(m['win']))
    if m.get('total'):
        extra.append('ТОТАЛ %g: Б %.2f · М %.2f' % tuple(m['total']))
    if extra:
        f = F(MANROPE, 18 * S, 800)
        tx = ' · '.join(extra)
        tw = f.getlength(tx) + 40 * S
        d.rounded_rectangle((cx - tw / 2, (y0 + chh + 34) * S, cx + tw / 2, (y0 + chh + 84) * S), radius=25 * S, fill=DARK + (235,))
        d.text((cx, (y0 + chh + 59) * S), tx, font=f, anchor='mm', fill=(255, 255, 255, 255))
    d.text((cx, (H - 70) * S), FOOT_ODDS, font=F(MANROPE, 13 * S, 800), anchor='mm', fill=(255, 255, 255, 220))
    spaced(d, (cx, (H - 40) * S), '@jarvibet', F(UNB, 20 * S, 700), (255, 255, 255, 255), 2 * S)
    return rs._finish(bg, ov, H, path, grain=0.25)


def _s_ticket(m, path, league, title):
    """МАТЧ ДНЯ — большой билет: корешок сверху со временем и датой, ниже эмблемы, линия и шансы."""
    m = _resolve([m], league)[0]
    H = 1350
    bg, ov = _start(H, league, title, m.get('date'))
    x0, y0, w, h = 70 * S, 300 * S, (W - 140) * S, 900 * S
    stub = int(h * 0.24)
    notch = int(w * 0.05)
    c = Image.new('RGBA', (w, h), (252, 253, 255, 255))
    dc = ImageDraw.Draw(c)
    dc.rectangle((0, 0, w, stub), fill=DARK + (255,))
    mk = Image.new('L', (w, h), 0)
    dm = ImageDraw.Draw(mk)
    dm.rounded_rectangle((0, 0, w - 1, h - 1), radius=30 * S, fill=255)
    dm.ellipse((-notch, stub - notch, notch, stub + notch), fill=0)
    dm.ellipse((w - notch, stub - notch, w + notch, stub + notch), fill=0)
    c.putalpha(mk)
    for xx in range(notch + 10 * S, w - notch - 10 * S, 22 * S):
        dc.line((xx, stub, xx + 11 * S, stub), fill=(170, 182, 200, 255), width=3 * S)
    # полосы клубов по краям корешка
    dc.rectangle((0, 0, 14 * S, stub), fill=club(m['home']) + (255,))
    dc.rectangle((w - 14 * S, 0, w, stub), fill=club(m['away']) + (255,))
    c.putalpha(mk)
    poster._shadowed(ov, c, (x0, y0), blur=16 * S, off=(0, 8 * S), color=(30, 60, 110, 90))
    d = ImageDraw.Draw(ov)
    cx = W * S / 2
    d.text((cx, y0 + stub * 0.42), m.get('time', ''), font=F(UNB, 70 * S, 700), anchor='mm', fill=(255, 255, 255, 255))
    d.text((cx, y0 + stub * 0.8), ('НАЧАЛО ПО МСК' + (' · ' + m['tag'].upper() if m.get('tag') else '')), font=F(MANROPE, 16 * S, 800), anchor='mm', fill=(150, 160, 178, 255))
    by = y0 + stub
    es = 260 * S
    for team, ex in ((m['home'], x0 + w * 0.25), (m['away'], x0 + w * 0.75)):
        _put(ov, _emb(team, es), ex, by + 200 * S, blur=8)
    d = ImageDraw.Draw(ov)
    d.text((cx, by + 200 * S), 'VS', font=F(OSW, 46 * S, 700), anchor='mm', fill=(190, 198, 212, 255))
    for team, ex in ((m['home'], x0 + w * 0.25), (m['away'], x0 + w * 0.75)):
        d.text((ex, by + 365 * S), _short(team), font=fit(_short(team), OSW, 40 * S, w * 0.42, 700), anchor='mm', fill=NAVY + (255,))
        d.text((ex, by + 405 * S), 'ХОЗЯЕВА' if team == m['home'] else 'ГОСТИ', font=F(MANROPE, 14 * S, 800), anchor='mm', fill=GREY + (255,))
    o = m.get('odds')
    if o:
        _odds_line(d, cx, by + 470 * S, o, size=24)
        p = _chance(o)
        bx0, bx1, yb, bh = x0 + 60 * S, x0 + w - 60 * S, by + 520 * S, 36 * S
        split = bx0 + (bx1 - bx0) * p
        d.rounded_rectangle((bx0, yb, bx1, yb + bh), radius=bh / 2, fill=club(m['away']) + (255,))
        d.rounded_rectangle((bx0, yb, max(bx0 + bh, split), yb + bh), radius=bh / 2, fill=club(m['home']) + (255,))
        d.rectangle((split - bh / 2, yb, split, yb + bh), fill=club(m['home']) + (255,))
        d.line((split, yb - 3 * S, split, yb + bh + 3 * S), fill=(255, 255, 255, 255), width=3 * S)
        fp = F(UNB, 18 * S, 700)
        d.text((bx0 + 14 * S, yb + bh / 2), '%d%%' % round(p * 100), font=fp, anchor='lm', fill=(255, 255, 255, 255))
        d.text((bx1 - 14 * S, yb + bh / 2), '%d%%' % round((1 - p) * 100), font=fp, anchor='rm', fill=(255, 255, 255, 255))
        d.text((cx, yb + bh + 26 * S), 'ШАНСЫ НА ПОБЕДУ С УЧЁТОМ ОТ', font=F(MANROPE, 13 * S, 800), anchor='mm', fill=GREY + (255,))
    extra = []
    if m.get('win'):
        extra.append('ПОБЕДА С ОТ %.2f / %.2f' % tuple(m['win']))
    if m.get('total'):
        extra.append('ТОТАЛ %g: Б %.2f · М %.2f' % tuple(m['total']))
    if extra:
        d.text((cx, y0 + h - 50 * S), ' · '.join(extra), font=F(MANROPE, 18 * S, 800), anchor='mm', fill=INK + (255,))
    return _end(bg, ov, H, path, FOOT_ODDS)


# ------------------------------------------------------------------ вход
MATCHI = {'ticket': _m_ticket, 'bars': _m_bars, 'puck': _m_puck, 'timeline': _m_timeline, 'halves': _halves}
ITOGI = {'ticket': lambda *a: _m_ticket(*a, results=True), 'dots': _r_dots, 'halves': lambda *a: _halves(*a, results=True)}
SINGLE = {'split': _s_split, 'ticket': _s_ticket}


def matchi(items, path, style='ticket', league='KHL', title='МАТЧИ ДНЯ', date_title=None, cont=False, rows=None):
    league = league.upper()
    return MATCHI[style](_resolve(items, league), path, league, title, date_title, cont, rows)


def itogi(items, path, style='dots', league='KHL', title='ИТОГИ ДНЯ', date_title=None, cont=False, rows=None):
    league = league.upper()
    return ITOGI[style](_resolve(items, league), path, league, title, date_title, cont, rows)


def single(m, path, style='split', league='KHL', title='МАТЧ ДНЯ'):
    return SINGLE[style](m, path, league.upper(), title)
