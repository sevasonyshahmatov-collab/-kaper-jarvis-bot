"""Ещё форматы в стиле «Лёд» (03.10.2026, вторая партия) — на выбор, автоматика их пока не использует.

Общее с утверждёнными шаблонами то же, что в ice_more: лёд с инеем, шапка JARVIS | KXL/NHL, Oswald/Unbounded/Manrope,
портрет 1080×1350, rows — общее число мест в альбоме (плашки на одном уровне), cont=True — крупно «JARVIS | KHL».

    import ice_more2 as im2
    im2.matchi(items, 'm.jpg', style='scales', league='KHL', date_title='суббота, 3 октября')
    im2.itogi(items, 'r.jpg', style='winner', league='KHL', date_title='…')
    im2.single(m, 's.jpg', style='tape', league='KHL')

Матчи дня (items: {home, away, time, odds=(П1, Х, П2) | None}):
  scales   — ВЕСЫ: коромысло на опоре, перевешивает фаворит по линии; время на опоре, шансы под эмблемами
  rink     — КАТОК: строка — площадка сверху (красная и синие линии), время в центральном круге вбрасывания
  pennant  — ВЫМПЕЛЫ: два вымпела в цветах клубов навстречу друг другу, время между остриями
  rings    — КОЛЬЦА: эмблемы в пересекающихся кольцах клубов, справа время и линия (компактно, для 8–12 матчей)
Итоги дня (items: {home, away, sh, sa, mark, pick={text, odds, hit: True|False|None} | None}):
  winner   — ПОБЕДИТЕЛЬ: половина победителя залита цветом клуба, проигравший бледный
  picks    — ПРОГНОЗЫ: счёт строками как в табло + справа наш прогноз и «ЗАШЁЛ / НЕ ЗАШЁЛ»; внизу итог дня в единицах
  numbers  — ДЕНЬ В ЦИФРАХ: матчей, голов, овертаймов, побед гостей, крупнейшая и самая результативная игра + все счета
  rink     — КАТОК: счёт в круге вбрасывания, зона победителя подкрашена цветом клуба
Матч (m: {home, away, date, time, tag, odds, ...}):
  tape     — ПРОТИВОСТОЯНИЕ: эмблемы и сравнение по строкам (stats=[(подпись, хозяева, гости, меньше_лучше)], form=('ВВПВП', 'ПВВПП'))
  final    — ИТОГ МАТЧА: крупный счёт в цвете победителя, голы по порядку (goals=[(время, игрок, команда)]), вердикт прогноза (pick)
"""
import math

import numpy as np
from PIL import Image, ImageDraw

import poster
import recap
import results_styles as rs
from results_styles2 import F, fit, club, spaced, OSW, UNB, _sticker
from results_ice2 import _background, MANROPE, NAVY, RED
from ice_more import (_resolve, _start, _end, _emb, _put, _card, _chance, _fav, _odds_line, _short, _rows, _ring,
                      GOLD, GOLD_T, INK, DARK, GREY, HEAD, GAP, FOOT, FOOT_ODDS, FOOT_CHANCE)

S, W = rs.S, rs.W
GREEN = (30, 170, 84)
LOSS = (214, 52, 70)
RINK_RED = (214, 40, 56)
RINK_BLUE = (40, 92, 200)


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _on(c):
    """Цвет текста поверх клубного цвета: белый, а на светлых клубах — тёмный."""
    return (16, 22, 34) if _lum(c) > 170 else (255, 255, 255)


def _mark(it):
    return rs.MARK_TEXT.get(it.get('mark') or '', '')


def _score_pill(d, cx, cy, it, k, w=128, h=58):
    hw = it['sh'] > it['sa']
    bw, bh = w * k * S, h * k * S
    d.rounded_rectangle((cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2), radius=bh / 2, fill=DARK + (255,), outline=(255, 255, 255, 230), width=3 * S)
    fb = F(UNB, int(30 * k) * S, 700)
    d.text((cx - 28 * k * S, cy), str(it['sh']), font=fb, anchor='mm', fill=(GOLD_T if hw else (120, 128, 142)) + (255,))
    d.text((cx, cy - 2 * S), ':', font=F(UNB, int(22 * k) * S, 500), anchor='mm', fill=(120, 128, 142, 255))
    d.text((cx + 28 * k * S, cy), str(it['sa']), font=fb, anchor='mm', fill=((120, 128, 142) if hw else GOLD_T) + (255,))


def _tag(d, cx, cy, text, k, fill=(255, 255, 255, 240), color=DARK):
    f = F(MANROPE, int(11 * k) * S, 800)
    tw = f.getlength(text) + 18 * S
    d.rounded_rectangle((cx - tw / 2, cy - 12 * S, cx + tw / 2, cy + 12 * S), radius=10 * S, fill=fill)
    d.text((cx, cy), text, font=f, anchor='mm', fill=color + (255,))


# ------------------------------------------------------------------ МАТЧИ ДНЯ
def _m_scales(items, path, league, title, date_title, cont, rows):
    row, top, H, k = _rows(len(items), rows)
    bg, ov = _start(H, league, title, date_title, cont)
    w, x0 = (W - 64) * S, 32 * S
    for i, it in enumerate(items):
        y0 = (top + i * (row + GAP)) * S
        h = int(row * S)
        _card(ov, (x0, y0, x0 + w, y0 + h), 22 * S, (252, 253, 255, 245))
        o = it.get('odds')
        p = _chance(o) if o else 0.5
        mx = x0 + w / 2
        by = y0 + h * 0.70                                                  # ось коромысла
        half = w / 2 - 110 * S
        dy = max(-1, min(1, (p - 0.5) * 3.2)) * h * 0.13                    # фаворит тяжелее — его край ниже
        yl, yr = by + dy, by - dy
        d = ImageDraw.Draw(ov)
        # опора
        d.polygon(((mx, by), (mx - 30 * k * S, y0 + h - 12 * S), (mx + 30 * k * S, y0 + h - 12 * S)), fill=(198, 206, 220, 255))
        d.line((mx - half, yl, mx + half, yr), fill=NAVY + (255,), width=int(9 * S))
        for x, y in ((mx - half, yl), (mx + half, yr)):
            d.ellipse((x - 9 * S, y - 9 * S, x + 9 * S, y + 9 * S), fill=NAVY + (255,))
        d.ellipse((mx - 13 * S, by - 13 * S, mx + 13 * S, by + 13 * S), fill=GOLD + (255,), outline=NAVY + (255,), width=3 * S)
        es = int(h * 0.56)
        for team, x, y in ((it['home'], mx - half, yl), (it['away'], mx + half, yr)):
            _put(ov, _emb(team, es), x, y - es / 2 - 6 * S, blur=5)
        d = ImageDraw.Draw(ov)
        # названия — над коромыслом ближе к центру, на своей высоте
        room = half - es / 2 - 110 * k * S
        fh = fit(_short(it['home']), OSW, int(28 * k) * S, room, 700)
        fa = fit(_short(it['away']), OSW, int(28 * k) * S, room, 700)
        t = lambda x: by + (x - mx) / half * (-dy)                          # высота коромысла в точке x
        hx, ax = mx - half + es / 2 + 18 * S, mx + half - es / 2 - 18 * S
        d.text((hx, t(hx) - 30 * k * S), _short(it['home']), font=fh, anchor='lm', fill=NAVY + (255,))
        d.text((ax, t(ax) - 30 * k * S), _short(it['away']), font=fa, anchor='rm', fill=NAVY + (255,))
        if o:
            fp = F(UNB, int(17 * k) * S, 700)
            d.text((hx, t(hx) + 24 * k * S), '%d%%' % round(p * 100), font=fp, anchor='lm', fill=((200, 140, 20) if p > .5 else INK) + (255,))
            d.text((ax, t(ax) + 24 * k * S), '%d%%' % round((1 - p) * 100), font=fp, anchor='rm', fill=((200, 140, 20) if p < .5 else INK) + (255,))
        # время над опорой
        ft = F(UNB, int(20 * k) * S, 700)
        tw = ft.getlength(it.get('time', '')) + 26 * S
        ty = y0 + h * 0.30
        d.rounded_rectangle((mx - tw / 2, ty - 18 * k * S, mx + tw / 2, ty + 18 * k * S), radius=12 * S, fill=DARK + (255,))
        d.text((mx, ty), it.get('time', ''), font=ft, anchor='mm', fill=GOLD_T + (255,))
    return _end(bg, ov, H, path, 'ПЕРЕВЕШИВАЕТ ФАВОРИТ · ' + FOOT_CHANCE)


def _rink_row(ov, x0, y0, w, h, it, k, results=False):
    """Площадка сверху: скруглённая «коробка», красная центральная, синие линии, круг вбрасывания в центре."""
    r = h // 2
    hw = results and it['sh'] > it['sa']
    a = np.zeros((h, w, 4), np.float32)
    a[..., :3] = (250, 252, 255)
    if results:                                                            # зона победителя — в цвет клуба, бледно
        c = np.array(club(it['home'] if hw else it['away']), np.float32)
        xs = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
        zone = (xs < 0.5) if hw else (xs > 0.5)
        g = (1 - xs * 1.7) if hw else ((xs - 0.41) * 1.7)
        g = np.clip(g, 0, 1) * 0.38 + 0.08
        a[..., :3] = np.where(zone, a[..., :3] * (1 - g) + c * g, a[..., :3])
    a[..., 3] = 255
    tile = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    d = ImageDraw.Draw(tile)
    lw = max(3, int(5 * S * k))
    cr = h * 0.40
    bl = cr + 22 * S                                                       # синие линии — сразу за кругом, названия до них
    for x, col in ((w / 2, RINK_RED), (w / 2 - bl, RINK_BLUE), (w / 2 + bl, RINK_BLUE)):
        d.rectangle((x - lw, 0, x + lw, h), fill=col + (170 if col == RINK_BLUE else 200,))
    d.ellipse((w / 2 - cr, h / 2 - cr, w / 2 + cr, h / 2 + cr), fill=(255, 255, 255, 255), outline=RINK_BLUE + (230,), width=lw)
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    tile.putalpha(m)
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, outline=(150, 166, 190, 255), width=max(3, 3 * S))
    poster._shadowed(ov, tile, (x0, y0), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 75))
    cy, cx = y0 + h / 2, x0 + w / 2
    es = int(h * 0.62)
    lx, rx = x0 + r * 1.05, x0 + w - r * 1.05
    lose_h, lose_a = results and not hw, results and hw
    _put(ov, _emb(it['home'], es, grey=lose_h), lx, cy, blur=5)
    _put(ov, _emb(it['away'], es, grey=lose_a), rx, cy, blur=5)
    d = ImageDraw.Draw(ov)
    room = (cx - cr - 22 * S - lw) - (lx + es / 2) - 34 * S
    o = it.get('odds') if not results else None
    ny = cy - (12 * k * S if o else 0)
    for team, x, an, lost in ((it['home'], lx + es / 2 + 16 * S, 'lm', lose_h), (it['away'], rx - es / 2 - 16 * S, 'rm', lose_a)):
        f = fit(_short(team), OSW, int(30 * k) * S, room, 700)
        d.text((x, ny), _short(team), font=f, anchor=an, fill=(GREY if lost else NAVY) + (255,))
    if o:
        fav = _fav(o)
        fv = F(MANROPE, int(15 * k) * S, 800)
        for x, lab, v, hot, an in ((lx + es / 2 + 16 * S, 'П1', o[0], fav == -1, 'lm'), (rx - es / 2 - 16 * S, 'П2', o[2], fav == 1, 'rm')):
            d.text((x, cy + 26 * k * S), lab + ' %.2f' % v, font=fv, anchor=an, fill=((200, 140, 20) if hot else INK) + (255,))
    if results:
        hwv = it['sh'] > it['sa']
        fb = F(UNB, int(34 * k) * S, 700)
        d.text((cx - 24 * k * S, cy - 4 * k * S), str(it['sh']), font=fb, anchor='mm', fill=((200, 140, 20) if hwv else (150, 158, 172)) + (255,))
        d.text((cx, cy - 6 * k * S), ':', font=F(UNB, int(24 * k) * S, 500), anchor='mm', fill=(150, 158, 172, 255))
        d.text((cx + 24 * k * S, cy - 4 * k * S), str(it['sa']), font=fb, anchor='mm', fill=((150, 158, 172) if hwv else (200, 140, 20)) + (255,))
        mk = _mark(it)
        if mk:
            d.text((cx, cy + 26 * k * S), mk.replace('ОТ / БУЛЛИТЫ', 'ОТ/Б'), font=F(MANROPE, int(10 * k) * S, 800), anchor='mm', fill=INK + (255,))
    else:
        d.text((cx, cy - 6 * k * S), it.get('time', ''), font=F(UNB, int(24 * k) * S, 700), anchor='mm', fill=NAVY + (255,))
        d.text((cx, cy + 22 * k * S), ('Х %.2f' % o[1]) if o else 'МСК', font=F(MANROPE, int(12 * k) * S, 800), anchor='mm', fill=GREY + (255,))


def _rink(items, path, league, title, date_title, cont, rows, results=False):
    row, top, H, k = _rows(len(items), rows)
    bg, ov = _start(H, league, title, date_title, cont)
    w, x0 = (W - 64) * S, 32 * S
    for i, it in enumerate(items):
        y0 = int((top + i * (row + GAP)) * S)
        _rink_row(ov, x0, y0, w, int(row * S), it, k, results)
    return _end(bg, ov, H, path, None if results else FOOT_ODDS)


def _pennant(team, w, h, flip=False):
    """Вымпел: широкий край у борта, сужается к острию; клубный цвет, темнее к острию, эмблема-наклейка у широкого края."""
    c = np.array(club(team), np.float32)
    a = np.zeros((h, w, 4), np.float32)
    xs = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    a[..., :3] = c * (1.10 - 0.35 * xs) * (1.04 - 0.12 * ys)
    a[..., 3] = 255
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    m = Image.new('L', (w, h), 0)
    tip = h * 0.5
    ImageDraw.Draw(m).polygon(((0, 0), (w * 0.86, h * 0.20), (w, tip), (w * 0.86, h * 0.80), (0, h)), fill=255)
    im.putalpha(m)
    d = ImageDraw.Draw(im)
    d.line(((0, 0), (w * 0.86, h * 0.20), (w, tip), (w * 0.86, h * 0.80), (0, h)), fill=(255, 255, 255, 200), width=3 * S, joint='curve')
    d.rectangle((0, 0, 10 * S, h), fill=(255, 255, 255, 230))               # древко
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im


def _m_pennant(items, path, league, title, date_title, cont, rows):
    row, top, H, k = _rows(len(items), rows)
    bg, ov = _start(H, league, title, date_title, cont)
    w, x0 = (W - 64) * S, 32 * S
    for i, it in enumerate(items):
        y0 = int((top + i * (row + GAP)) * S)
        h = int(row * S)
        cy, cx = y0 + h / 2, x0 + w / 2
        pw = int(w / 2 - 54 * k * S)
        for team, flip, px in ((it['home'], False, x0), (it['away'], True, x0 + w - pw)):
            poster._shadowed(ov, _pennant(team, pw, h, flip), (int(px), y0), blur=10 * S, off=(0, 5 * S), color=(30, 60, 110, 70))
        es = int(h * 0.66)
        lx, rx = x0 + 22 * S + es / 2, x0 + w - 22 * S - es / 2
        for team, x in ((it['home'], lx), (it['away'], rx)):
            _put(ov, _sticker(_emb(team, es), 3 * S), x, cy, shadow=False)
        d = ImageDraw.Draw(ov)
        room = pw * 0.86 - es - 50 * S
        o = it.get('odds')
        fav = _fav(o) if o else 0
        for team, x, an, lab, v, hot in ((it['home'], lx + es / 2 + 16 * S, 'lm', 'П1', o and o[0], fav == -1),
                                         (it['away'], rx - es / 2 - 16 * S, 'rm', 'П2', o and o[2], fav == 1)):
            col = _on(club(team))
            d.text((x, cy - (12 * k * S if o else 0)), _short(team), font=fit(_short(team), OSW, int(30 * k) * S, room, 700), anchor=an, fill=col + (255,))
            if o:
                d.text((x, cy + 26 * k * S), '%s %.2f' % (lab, v), font=F(MANROPE, int(15 * k) * S, 800), anchor=an,
                       fill=(GOLD_T if hot and col == (255, 255, 255) else col) + (255 if hot else 200,))
        rr = 50 * k * S
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=DARK + (255,), outline=(255, 255, 255, 240), width=3 * S)
        d.text((cx, cy - 6 * k * S), it.get('time', ''), font=F(UNB, int(19 * k) * S, 700), anchor='mm', fill=(255, 255, 255, 255))
        d.text((cx, cy + 20 * k * S), ('Х %.2f' % o[1]) if o else 'МСК', font=F(MANROPE, int(10 * k) * S, 800), anchor='mm', fill=(150, 160, 178, 255))
    return _end(bg, ov, H, path, FOOT_ODDS)


def _m_rings(items, path, league, title, date_title, cont, rows):
    row, top, H, k = _rows(len(items), rows)
    bg, ov = _start(H, league, title, date_title, cont)
    w, x0 = (W - 64) * S, 32 * S
    for i, it in enumerate(items):
        y0 = int((top + i * (row + GAP)) * S)
        h = int(row * S)
        _card(ov, (x0, y0, x0 + w, y0 + h), h // 2, (252, 253, 255, 245))
        cy = y0 + h / 2
        rs_ = int(h * 0.84)
        lx = x0 + 10 * S + rs_ / 2
        _put(ov, _ring(it['away'], rs_), lx + rs_ * 0.80, cy, blur=6)          # гости — позади
        _put(ov, _ring(it['home'], rs_), lx, cy, blur=6)
        d = ImageDraw.Draw(ov)
        nx = lx + rs_ * 1.30 + 26 * S
        tx = x0 + w - 40 * S
        ft = F(UNB, int(32 * k) * S, 700)
        room = tx - ft.getlength('00:00') - 40 * S - nx
        o = it.get('odds')
        fav = _fav(o) if o else 0
        fn = int(30 * k) * S
        for j, (team, hot, v, lab) in enumerate(((it['home'], fav == -1, o and o[0], 'П1'), (it['away'], fav == 1, o and o[2], 'П2'))):
            yy = cy + (-1 if j == 0 else 1) * 22 * k * S
            f = fit(_short(team), OSW, fn, room * 0.72, 700)
            d.text((nx, yy), _short(team), font=f, anchor='lm', fill=NAVY + (255,))
            if o:
                d.text((nx + f.getlength(_short(team)) + 14 * S, yy + 2 * S), '%.2f' % v, font=F(MANROPE, int(15 * k) * S, 800), anchor='lm',
                       fill=((200, 140, 20) if hot else GREY) + (255,))
        d.text((tx, cy - 8 * k * S), it.get('time', ''), font=ft, anchor='rm', fill=NAVY + (255,))
        d.text((tx, cy + 24 * k * S), ('НИЧЬЯ %.2f' % o[1]) if o else 'МСК', font=F(MANROPE, int(12 * k) * S, 800), anchor='rm', fill=GREY + (255,))
    return _end(bg, ov, H, path, FOOT_ODDS)


# ------------------------------------------------------------------ ИТОГИ ДНЯ
def _r_winner(items, path, league, title, date_title, cont, rows):
    row, top, H, k = _rows(len(items), rows)
    bg, ov = _start(H, league, title, date_title, cont)
    w, x0 = (W - 64) * S, 32 * S
    for i, it in enumerate(items):
        y0 = int((top + i * (row + GAP)) * S)
        h = int(row * S)
        hw = it['sh'] > it['sa']
        win = it['home'] if hw else it['away']
        c = np.array(club(win), np.float32)
        a = np.zeros((h, w, 4), np.float32)
        a[..., :3] = (250, 252, 255)
        xs = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
        ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        xw = xs if hw else 1 - xs
        cut = 0.56 - (ys - 0.5) * 0.08                                       # скошенный край заливки
        col = c * (1.08 - 0.25 * ys) * (1.02 - 0.15 * xw)
        a[..., :3] = np.where(xw < cut, col, a[..., :3])
        a[..., 3] = 255
        tile = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
        m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=22 * S, fill=255)
        tile.putalpha(m)
        ImageDraw.Draw(tile).rounded_rectangle((0, 0, w - 1, h - 1), radius=22 * S, outline=(255, 255, 255, 220), width=3 * S)
        poster._shadowed(ov, tile, (x0, y0), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 75))
        cy, cx = y0 + h / 2, x0 + w / 2
        es_w, es_l = int(h * 0.80), int(h * 0.50)
        wx = x0 + 18 * S + es_w / 2 if hw else x0 + w - 18 * S - es_w / 2
        lx = x0 + w - 26 * S - es_l / 2 if hw else x0 + 26 * S + es_l / 2
        _put(ov, _sticker(_emb(win, es_w), 4 * S), wx, cy, blur=6)
        _put(ov, _emb(it['away'] if hw else it['home'], es_l, grey=True), lx, cy, shadow=False)
        d = ImageDraw.Draw(ov)
        tc = _on(tuple(int(v) for v in c))
        room = (cx - 80 * k * S) - (x0 + 18 * S + es_w) - 20 * S
        fw = fit(_short(win), OSW, int(34 * k) * S, room, 700)
        nx = (x0 + 18 * S + es_w + 14 * S) if hw else (x0 + w - 18 * S - es_w - 14 * S)
        d.text((nx, cy - 10 * k * S), _short(win), font=fw, anchor='lm' if hw else 'rm', fill=tc + (255,))
        d.text((nx, cy + 24 * k * S), 'ПОБЕДА', font=F(MANROPE, int(13 * k) * S, 800), anchor='lm' if hw else 'rm', fill=tc + (190,))
        loser = it['away'] if hw else it['home']
        lroom = (x0 + w - 26 * S - es_l) - (cx + 80 * k * S) - 20 * S
        lnx = (lx - es_l / 2 - 14 * S) if hw else (lx + es_l / 2 + 14 * S)
        d.text((lnx, cy), _short(loser), font=fit(_short(loser), OSW, int(24 * k) * S, lroom, 600), anchor='rm' if hw else 'lm', fill=GREY + (255,))
        _score_pill(d, cx, cy, it, k)
        mk = _mark(it)
        if mk:
            _tag(d, cx, cy + 46 * k * S, mk, k, fill=DARK + (255,), color=(255, 255, 255))
    return _end(bg, ov, H, path)


def _r_picks(items, path, league, title, date_title, cont, rows):
    row, top, H, k = _rows(len(items), rows)
    bg, ov = _start(H, league, title, date_title, cont)
    w, x0 = (W - 64) * S, 32 * S
    bw = int(w * 0.30)
    units, n_p, n_hit = 0.0, 0, 0
    for i, it in enumerate(items):
        y0 = int((top + i * (row + GAP)) * S)
        h = int(row * S)
        _card(ov, (x0, y0, x0 + w - bw - 14 * S, y0 + h), 22 * S, (252, 253, 255, 245))
        hw = it['sh'] > it['sa']
        es = int(h * 0.36)
        mid = y0 + h / 2
        for j, (team, g, won) in enumerate(((it['home'], it['sh'], hw), (it['away'], it['sa'], not hw))):
            yy = mid + (-1 if j == 0 else 1) * h * 0.22
            ex = x0 + 26 * S + es / 2
            _put(ov, _emb(team, es, grey=not won), ex, yy, shadow=False)
            d = ImageDraw.Draw(ov)
            room = (x0 + w - bw - 14 * S) - (ex + es / 2 + 16 * S) - 120 * S
            d.text((ex + es / 2 + 16 * S, yy), _short(team), font=fit(_short(team), OSW, int(26 * k) * S, room, 700 if won else 500), anchor='lm',
                   fill=(NAVY if won else GREY) + (255,))
            d.text((x0 + w - bw - 14 * S - 30 * S, yy), str(g), font=F(UNB, int(30 * k) * S, 700), anchor='rm', fill=(NAVY if won else GREY) + (255,))
            if won:
                d.polygon(((x0 + w - bw - 14 * S - 8 * S, yy), (x0 + w - bw - 14 * S - 18 * S, yy - 8 * S), (x0 + w - bw - 14 * S - 18 * S, yy + 8 * S)), fill=GOLD + (255,))
        d = ImageDraw.Draw(ov)
        mk = _mark(it)
        if mk:
            d.text((x0 + w - bw - 14 * S - 120 * S, mid), mk.replace('ОТ / БУЛЛИТЫ', 'ОТ/Б'), font=F(MANROPE, int(11 * k) * S, 800), anchor='rm', fill=GREY + (255,))
        # плашка прогноза
        pk = it.get('pick')
        px0 = x0 + w - bw
        if not pk:
            fill, head, sub, col = (226, 232, 242), 'БЕЗ СТАВКИ', 'перевеса не нашли', INK
        elif pk.get('hit') is None:
            fill, head, sub, col = (226, 232, 242), pk.get('text', ''), 'возврат', INK
        else:
            n_p += 1
            n_hit += bool(pk['hit'])
            units += (pk.get('odds', 0) - 1) if pk['hit'] else -1
            fill, col = (GREEN, (255, 255, 255)) if pk['hit'] else (LOSS, (255, 255, 255))
            head = pk.get('text', '') + (('  ' + ('%.2f' % pk['odds']).replace('.', ',')) if pk.get('odds') else '')
            sub = 'ЗАШЁЛ' if pk['hit'] else 'НЕ ЗАШЁЛ'
        _card(ov, (px0, y0, x0 + w, y0 + h), 22 * S, fill + (255,))
        d = ImageDraw.Draw(ov)
        pcx = px0 + bw / 2
        d.text((pcx, mid - 16 * k * S), head, font=fit(head, OSW, int(26 * k) * S, bw - 30 * S, 700), anchor='mm', fill=col + (255,))
        if pk and pk.get('hit') is not None:
            sy = mid + 22 * k * S
            f = F(MANROPE, int(15 * k) * S, 800)
            d.text((pcx + 12 * S, sy), sub, font=f, anchor='mm', fill=col + (255,))
            ix = pcx - f.getlength(sub) / 2 - 8 * S
            rr = 8 * k * S
            if pk['hit']:
                d.line(((ix - rr, sy), (ix - rr * 0.3, sy + rr * 0.7), (ix + rr, sy - rr * 0.7)), fill=col + (255,), width=3 * S, joint='curve')
            else:
                d.line((ix - rr * .7, sy - rr * .7, ix + rr * .7, sy + rr * .7), fill=col + (255,), width=3 * S)
                d.line((ix - rr * .7, sy + rr * .7, ix + rr * .7, sy - rr * .7), fill=col + (255,), width=3 * S)
        else:
            d.text((pcx, mid + 20 * k * S), sub.upper(), font=F(MANROPE, int(12 * k) * S, 800), anchor='mm', fill=GREY + (255,))
    note = 'ПОКАЗЫВАЕМ ВСЕ ПРОГНОЗЫ ДНЯ — И ЗАШЕДШИЕ, И НЕТ'
    if n_p:
        note = ('ПРОГНОЗОВ %d · ЗАШЛО %d · ИТОГ ДНЯ %+.2f ЕД. ПРИ СТАВКЕ 1 ЕД. · ПОКАЗЫВАЕМ ВСЕ' % (n_p, n_hit, units)).replace('.', ',', 1)
    return _end(bg, ov, H, path, note)


def _plural(n, one, few, many):
    n10, n100 = n % 10, n % 100
    if n10 == 1 and n100 != 11:
        return one
    if 2 <= n10 <= 4 and not 12 <= n100 <= 14:
        return few
    return many


def _r_numbers(items, path, league, title, date_title, cont, rows):
    H = 1350
    bg, ov = _start(H, league, title, date_title, cont)
    n = len(items)
    goals = sum(it['sh'] + it['sa'] for it in items)
    ots = sum(1 for it in items if it.get('mark'))
    away = sum(1 for it in items if it['sa'] > it['sh'])
    big = max(items, key=lambda it: (abs(it['sh'] - it['sa']), it['sh'] + it['sa']))
    most = max(items, key=lambda it: (it['sh'] + it['sa'], -abs(it['sh'] - it['sa'])))
    tiles = [(str(n), _plural(n, 'МАТЧ', 'МАТЧА', 'МАТЧЕЙ'), 'в этот день'),
             (str(goals), _plural(goals, 'ГОЛ', 'ГОЛА', 'ГОЛОВ'), ('%.1f за матч' % (goals / n)).replace('.', ',')),
             (str(ots), 'С ОВЕРТАЙМОМ' if ots == 1 else 'С ОВЕРТАЙМАМИ' if ots else 'ОВЕРТАЙМОВ', 'или буллитами' if ots else 'всё решили за 60 минут'),
             (str(away), _plural(away, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД') + ' ГОСТЕЙ', 'хозяева выиграли %d' % (n - away))]
    per = 3 if n > 4 else max(1, n)
    chip_rows = math.ceil(n / per)
    gx, tw, th, gap = 32, (W - 64 - 20) // 2, 190, 20
    total = 2 * th + gap + 4 + 200 + 26 + 30 + chip_rows * 76
    gy = 270 + max(0, (1350 - 270 - 120 - total) // 2)
    for i, (num, lab, sub) in enumerate(tiles):
        r, c = divmod(i, 2)
        x, y = gx + c * (tw + gap), gy + r * (th + gap)
        dark = i in (0, 3)
        _card(ov, (x * S, y * S, (x + tw) * S, (y + th) * S), 26 * S, (DARK + (255,)) if dark else (252, 253, 255, 245))
        d = ImageDraw.Draw(ov)
        d.text(((x + 34) * S, (y + th / 2) * S), num, font=F(UNB, 88 * S, 700), anchor='lm', fill=(GOLD_T if dark else NAVY) + (255,))
        nx = x + 34 + F(UNB, 88 * S, 700).getlength(num) / S + 22
        d.text((nx * S, (y + th / 2 - 16) * S), lab, font=fit(lab, OSW, 34 * S, (x + tw - 24 - nx) * S, 700), anchor='lm', fill=((255, 255, 255) if dark else NAVY) + (255,))
        d.text((nx * S, (y + th / 2 + 22) * S), sub.upper(), font=F(MANROPE, 14 * S, 800), anchor='lm', fill=((150, 160, 178) if dark else GREY) + (255,))
    # две особые игры
    y = gy + 2 * (th + gap) + 4
    for j, (lab, it) in enumerate((('КРУПНЕЙШАЯ ПОБЕДА', big), ('САМЫЙ РЕЗУЛЬТАТИВНЫЙ', most))):
        x = gx + j * (tw + gap)
        _card(ov, (x * S, y * S, (x + tw) * S, (y + 200) * S), 26 * S, (252, 253, 255, 245))
        d = ImageDraw.Draw(ov)
        d.text(((x + tw / 2) * S, (y + 34) * S), lab, font=F(MANROPE, 15 * S, 800), anchor='mm', fill=GREY + (255,))
        cy = y + 118
        hw = it['sh'] > it['sa']
        for team, ex, lost in ((it['home'], x + 80, not hw), (it['away'], x + tw - 80, hw)):
            _put(ov, _emb(team, 100 * S, grey=lost), ex * S, cy * S, blur=5)
        d = ImageDraw.Draw(ov)
        fb = F(UNB, 40 * S, 700)
        cx = x + tw / 2
        d.text(((cx - 30) * S, (cy - 6) * S), str(it['sh']), font=fb, anchor='mm', fill=((200, 140, 20) if hw else GREY) + (255,))
        d.text((cx * S, (cy - 8) * S), ':', font=F(UNB, 28 * S, 500), anchor='mm', fill=GREY + (255,))
        d.text(((cx + 30) * S, (cy - 6) * S), str(it['sa']), font=fb, anchor='mm', fill=(GREY if hw else (200, 140, 20)) + (255,))
        pair = '%s — %s' % (_short(it['home']), _short(it['away']))
        d.text((cx * S, (cy + 52) * S), pair, font=fit(pair, OSW, 18 * S, (tw - 180) * S, 600), anchor='mm', fill=NAVY + (255,))
    # все счета — фишками
    y = y + 200 + 26
    d = ImageDraw.Draw(ov)
    spaced(d, (W * S / 2, (y + 8) * S), 'ВСЕ СЧЕТА', F(MANROPE, 15 * S, 800), INK + (255,), 3 * S)
    chips = list(items)
    cw_ = (W - 64 - (per - 1) * 14) / per
    ch_ = 64
    for i, it in enumerate(chips):
        r, c = divmod(i, per)
        left = len(chips) - r * per
        k_row = min(per, left)
        xx = (W - (k_row * cw_ + (k_row - 1) * 14)) / 2 + c * (cw_ + 14)
        yy = y + 30 + r * (ch_ + 12)
        if yy + ch_ > H - 100:
            break
        _card(ov, (xx * S, yy * S, (xx + cw_) * S, (yy + ch_) * S), 32 * S, (252, 253, 255, 245), shadow=False, outline=(214, 222, 236, 255))
        hw = it['sh'] > it['sa']
        for team, ex, lost in ((it['home'], xx + 36, not hw), (it['away'], xx + cw_ - 36, hw)):
            _put(ov, _emb(team, 46 * S, grey=lost), ex * S, (yy + ch_ / 2) * S, shadow=False)
        d = ImageDraw.Draw(ov)
        sc = '%d:%d' % (it['sh'], it['sa']) + (' ' + it['mark'] if it.get('mark') else '')
        d.text(((xx + cw_ / 2) * S, (yy + ch_ / 2) * S), sc, font=F(UNB, 22 * S, 700), anchor='mm', fill=NAVY + (255,))
    return _end(bg, ov, H, path)


# ------------------------------------------------------------------ МАТЧ
def _s_tape(m, path, league, title):
    """ПРОТИВОСТОЯНИЕ: как взвешивание перед боем — две команды и сравнение по строкам."""
    m = _resolve([m], league)[0]
    H = 1350
    bg, ov = _start(H, league, title, ' · '.join(x for x in (m.get('date', ''), m.get('time', '') and m['time'] + ' МСК') if x))
    ch, ca = club(m['home']), club(m['away'])
    # шапки команд
    for team, cx, col in ((m['home'], 270, ch), (m['away'], W - 270, ca)):
        x0 = cx - 230
        _card(ov, (x0 * S, 262 * S, (x0 + 460) * S, 520 * S), 28 * S, col + (255,))
        _put(ov, _sticker(_emb(team, 180 * S), 4 * S), cx * S, 370 * S, blur=8)
        d = ImageDraw.Draw(ov)
        d.text((cx * S, 488 * S), _short(team), font=fit(_short(team), OSW, 38 * S, 420 * S, 700), anchor='mm', fill=_on(col) + (255,))
    d = ImageDraw.Draw(ov)
    rr = 46
    d.ellipse(((W / 2 - rr) * S, (391 - rr) * S, (W / 2 + rr) * S, (391 + rr) * S), fill=DARK + (255,), outline=(255, 255, 255, 255), width=4 * S)
    d.text((W / 2 * S, 389 * S), 'VS', font=F(OSW, 36 * S, 700), anchor='mm', fill=GOLD_T + (255,))
    # строки сравнения
    stats = list(m.get('stats') or [])
    form = m.get('form')
    nrow = len(stats) + (1 if form else 0)
    y0, y1 = 556, 1075 if m.get('odds') else 1200
    rh = min(84, (y1 - y0) / max(1, nrow))
    _card(ov, (32 * S, y0 * S, (W - 32) * S, (y0 + rh * nrow + 16) * S), 26 * S, (252, 253, 255, 245))
    d = ImageDraw.Draw(ov)
    cx = W / 2
    bar_max = 250
    for i, st in enumerate(stats):
        lab, hv, av = st[0], st[1], st[2]
        low = len(st) > 3 and st[3]
        cy = y0 + 8 + rh * (i + 0.5)
        if i:
            d.line((70 * S, (cy - rh / 2) * S, (W - 70) * S, (cy - rh / 2) * S), fill=(232, 236, 244, 255), width=2 * S)
        d.text((cx * S, (cy - 16) * S), lab.upper(), font=F(MANROPE, 14 * S, 800), anchor='mm', fill=GREY + (255,))
        try:
            hn, an = float(str(hv).replace('%', '').replace(',', '.')), float(str(av).replace('%', '').replace(',', '.'))
        except ValueError:
            hn = an = None
        better = 0
        if hn is not None and hn != an:
            better = -1 if ((hn < an) if low else (hn > an)) else 1
        if hn is not None:
            tot = max(abs(hn), abs(an)) or 1
            for side, v, col, b in ((-1, hn, ch, better == -1), (1, an, ca, better == 1)):
                ln = 40 + (bar_max - 40) * (abs(v) / tot if not low else (min(abs(hn), abs(an)) or 1) / (abs(v) or 1))
                bx0, bx1 = (cx - 70 - ln, cx - 70) if side < 0 else (cx + 70, cx + 70 + ln)
                d.rounded_rectangle((bx0 * S, (cy + 6) * S, bx1 * S, (cy + 20) * S), radius=7 * S, fill=(col if b else (214, 220, 232)) + (255,))
        for side, v, b in ((-1, hv, better == -1), (1, av, better == 1)):
            x = 70 if side < 0 else W - 70
            d.text((x * S, (cy + 2) * S), str(v).replace('.', ','), font=F(UNB, 30 * S, 700), anchor='lm' if side < 0 else 'rm',
                   fill=(NAVY if b or not better else GREY) + (255,))
    if form:
        cy = y0 + 8 + rh * (len(stats) + 0.5)
        if stats:
            d.line((70 * S, (cy - rh / 2) * S, (W - 70) * S, (cy - rh / 2) * S), fill=(232, 236, 244, 255), width=2 * S)
        d.text((cx * S, (cy - 16) * S), 'ПОСЛЕДНИЕ 5 МАТЧЕЙ', font=F(MANROPE, 14 * S, 800), anchor='mm', fill=GREY + (255,))
        for side, fs in ((-1, form[0]), (1, form[1])):
            for j, ch_ in enumerate(fs[-5:]):
                x = (70 + 19 + j * 44) if side < 0 else (W - 70 - 19 - j * 44)
                col = GREEN if ch_ in 'ВW' else LOSS if ch_ in 'ПL' else GREY
                d.ellipse(((x - 17) * S, (cy - 15) * S, (x + 17) * S, (cy + 19) * S), fill=col + (255,))
                d.text((x * S, (cy + 2) * S), ch_, font=F(MANROPE, 16 * S, 800), anchor='mm', fill=(255, 255, 255, 255))
    o = m.get('odds')
    if o:
        yb = 1165
        _odds_line(d, cx * S, (yb - 30) * S, o, size=22)
        p = _chance(o)
        bx0, bx1, bh = 90 * S, (W - 90) * S, 30 * S
        split = bx0 + (bx1 - bx0) * p
        d.rounded_rectangle((bx0, yb * S, bx1, yb * S + bh), radius=bh / 2, fill=ca + (255,))
        d.rounded_rectangle((bx0, yb * S, max(bx0 + bh, split), yb * S + bh), radius=bh / 2, fill=ch + (255,))
        d.rectangle((split - bh / 2, yb * S, split, yb * S + bh), fill=ch + (255,))
        d.line((split, yb * S - 3 * S, split, yb * S + bh + 3 * S), fill=(255, 255, 255, 255), width=3 * S)
        fp = F(UNB, 16 * S, 700)
        d.text((bx0 + 14 * S, yb * S + bh / 2), '%d%%' % round(p * 100), font=fp, anchor='lm', fill=_on(ch) + (255,))
        d.text((bx1 - 14 * S, yb * S + bh / 2), '%d%%' % round((1 - p) * 100), font=fp, anchor='rm', fill=_on(ca) + (255,))
        d.text((cx * S, (yb + 52) * S), 'ШАНСЫ НА ПОБЕДУ С УЧЁТОМ ОТ', font=F(MANROPE, 13 * S, 800), anchor='mm', fill=GREY + (255,))
    return _end(bg, ov, H, path, FOOT_ODDS if o else None)


def _final_top(m, league, title, H=1350):
    """Верх «ИТОГА МАТЧА» (до 640 px): фон в цвете победителя, шапка, эмблемы, крупный счёт, плашка «ПОБЕДА …»."""
    hw = m['sh'] > m['sa']
    win = m['home'] if hw else m['away']
    c = np.array(club(win), np.float32)
    bg = _background(H, league)
    top_h = 640
    arr = np.asarray(bg, np.float32).copy()
    # верх — шёлк с переливами и текстурой холста, как фон «Боков»: в цвете победителя, на его стороне светлее
    hi, lo = tuple(int(v) for v in c), tuple(int(v * 0.62) for v in c)
    silk = poster._fluid_bg(W, top_h, *((hi, lo) if hw else (lo, hi)), seed=sum(map(ord, m['home'] + m['away'])) % 997)
    silk = poster._canvas_texture(silk, 0.8)
    arr[:top_h, :, :3] = np.asarray(silk, np.float32)[..., :3] * 1.12
    edge = np.linspace(1, 0, 40, dtype=np.float32)[:, None, None]            # мягкий переход ко льду
    arr[top_h:top_h + 40, :, :3] = arr[top_h:top_h + 40, :, :3] * (1 - edge * 0.5) + (c * 0.85) * edge * 0.5
    bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), bg.mode)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    tc = _on(tuple(int(v) for v in c))
    rs._brand(d, W * S / 2, 58 * S, league, dark_text=tc != (255, 255, 255))
    spaced(d, (W * S / 2, 128 * S), title, F(OSW, 64 * S, 700), tc + (255,), 3 * S)
    sub = ' · '.join(x for x in (m.get('date', ''), m.get('tag', '')) if x)
    if sub:
        d.text((W * S / 2, 182 * S), sub.upper(), font=F(MANROPE, 17 * S, 800), anchor='mm', fill=tc + (200,))
    for team, cx, lost in ((m['home'], 210, not hw), (m['away'], W - 210, hw)):
        e = _emb(team, (250 if not lost else 190) * S, grey=lost, alpha=0.85 if lost else 1)
        _put(ov, _sticker(e, 5 * S) if not lost else e, cx * S, 380 * S, blur=10)
    d = ImageDraw.Draw(ov)
    fb = F(UNB, 120 * S, 700)
    cx = W / 2
    dim = tc + (130,)
    d.text(((cx - 78) * S, 372 * S), str(m['sh']), font=fb, anchor='mm', fill=(tc + (255,)) if hw else dim)
    d.text((cx * S, 364 * S), ':', font=F(UNB, 80 * S, 500), anchor='mm', fill=dim)
    d.text(((cx + 78) * S, 372 * S), str(m['sa']), font=fb, anchor='mm', fill=dim if hw else (tc + (255,)))
    for team, x in ((m['home'], 210), (m['away'], W - 210)):
        d.text((x * S, 548 * S), _short(team), font=fit(_short(team), OSW, 36 * S, 330 * S, 700), anchor='mm', fill=tc + (255 if team == win else 150,))
    mk = rs.MARK_TEXT.get(m.get('mark') or '', '')
    lab = ('ПОБЕДА ' + _short(win) + (' · ' + mk if mk else ' · ОСНОВНОЕ ВРЕМЯ'))
    f = F(MANROPE, 17 * S, 800)
    tw = f.getlength(lab) + 40 * S
    d.rounded_rectangle((cx * S - tw / 2, 470 * S, cx * S + tw / 2, 512 * S), radius=21 * S, fill=DARK + (235,))
    d.text((cx * S, 491 * S), lab, font=f, anchor='mm', fill=GOLD_T + (255,))
    return bg, ov


def _s_final(m, path, league, title):
    """ИТОГ МАТЧА: верх в цвете победителя со счётом, ниже голы по порядку и вердикт прогноза."""
    m = _resolve([m], league)[0]
    H = 1350
    bg, ov = _final_top(m, league, title, H)
    d = ImageDraw.Draw(ov)
    cx = W / 2
    # голы
    goals = list(m.get('goals') or [])
    y = 690
    pk = m.get('pick')
    bottom = 1150 if pk else 1240
    if goals:
        rh = min(66, (bottom - y - 70) / len(goals))
        y = int(y + max(0, (bottom - y) - (60 + rh * len(goals))) / 2)        # блок голов — по центру свободного места
        _card(ov, (32 * S, y * S, (W - 32) * S, (y + 60 + rh * len(goals)) * S), 26 * S, (252, 253, 255, 245))
        d = ImageDraw.Draw(ov)
        spaced(d, (cx * S, (y + 34) * S), 'ГОЛЫ', F(MANROPE, 16 * S, 800), INK + (255,), 3 * S)
        sh = sa = 0
        for i, (tm, who, team) in enumerate(goals):
            team = _resolve([dict(home=team, away=team)], league)[0]['home']
            home = team == m['home']
            sh, sa = sh + home, sa + (not home)
            yy = y + 60 + rh * (i + 0.5)
            col = club(team)
            d.rounded_rectangle(((cx - 46) * S, (yy - rh * 0.36) * S, (cx + 46) * S, (yy + rh * 0.36) * S), radius=rh * 0.36 * S, fill=DARK + (255,))
            d.text((cx * S, yy * S), '%d:%d' % (sh, sa), font=F(UNB, int(min(20, rh * 0.38)) * S, 700), anchor='mm', fill=(255, 255, 255, 255))
            side = -1 if home else 1
            ax = cx + side * 66
            fn = F(OSW, int(min(26, rh * 0.48)) * S, 600)
            ft = F(MANROPE, int(min(16, rh * 0.3)) * S, 800)
            d.ellipse(((ax + side * 2 - 6) * S, (yy - 6) * S, (ax + side * 2 + 6) * S, (yy + 6) * S), fill=col + (255,))
            d.text(((ax + side * 18) * S, yy * S), str(who).upper(), font=fn, anchor='lm' if side > 0 else 'rm', fill=NAVY + (255,))
            d.text((((70 if home else W - 70)) * S, yy * S), tm, font=ft, anchor='lm' if home else 'rm', fill=GREY + (255,))
    if pk:
        hit = pk.get('hit')
        fill = GREEN if hit else LOSS if hit is not None else (120, 128, 142)
        txt = 'ПРОГНОЗ: %s — %s' % (pk.get('text', ''), 'ЗАШЁЛ' if hit else 'НЕ ЗАШЁЛ' if hit is not None else 'ВОЗВРАТ')
        f = F(OSW, 30 * S, 700)
        tw = f.getlength(txt) + 70 * S
        yb = 1190
        _card(ov, (cx * S - tw / 2, yb * S, cx * S + tw / 2, (yb + 70) * S), 35 * S, fill + (255,))
        d = ImageDraw.Draw(ov)
        d.text((cx * S, (yb + 35) * S), txt, font=f, anchor='mm', fill=(255, 255, 255, 255))
    return _end(bg, ov, H, path)


def _tick(d, x, y, r, ok, col, w):
    """Галочка (ok), крестик (False) или черта (None — возврат), нарисованные линиями (не эмодзи)."""
    if ok is None:
        d.line((x - r * .75, y, x + r * .75, y), fill=col, width=w)
    elif ok:
        d.line(((x - r, y), (x - r * 0.3, y + r * 0.7), (x + r, y - r * 0.7)), fill=col, width=w, joint='curve')
    else:
        d.line((x - r * .7, y - r * .7, x + r * .7, y + r * .7), fill=col, width=w)
        d.line((x - r * .7, y + r * .7, x + r * .7, y - r * .7), fill=col, width=w)


def _s_verdict(m, path, league, title):
    """РАЗБОР ПРОГНОЗА: верх как у «ИТОГА МАТЧА», ниже карточка прогноза — ставка и кэф, штамп «ЗАШЁЛ» / «НЕ ЗАШЁЛ» / «ВОЗВРАТ»
    и расчёт строками (pick.checks=[(текст, True | False | None)]): по чему ставка рассчитана — видно, почему так."""
    m = _resolve([m], league)[0]
    H = 1350
    bg, ov = _final_top(m, league, title, H)
    pk = m.get('pick') or {}
    hit = pk.get('hit')
    cx = W / 2
    y0, y1 = 690, 1258
    _card(ov, (32 * S, y0 * S, (W - 32) * S, y1 * S), 28 * S, (252, 253, 255, 245))
    d = ImageDraw.Draw(ov)
    spaced(d, (cx * S, (y0 + 48) * S), 'ПРОГНОЗ', F(MANROPE, 17 * S, 800), INK + (255,), 4 * S)
    txt = pk.get('text', '')
    lift = 0 if pk.get('odds') else 40                                    # без кэфа штамп ближе к прогнозу
    d.text((cx * S, (y0 + 122 + lift / 4) * S), txt, font=fit(txt, OSW, 68 * S, (W - 150) * S, 700), anchor='mm', fill=NAVY + (255,))
    if pk.get('odds'):
        lab = 'КЭФ ' + ('%.2f' % pk['odds']).replace('.', ',')
        f = F(UNB, 22 * S, 700)
        tw = f.getlength(lab) + 48 * S
        yo = y0 + 202
        d.rounded_rectangle((cx * S - tw / 2, (yo - 25) * S, cx * S + tw / 2, (yo + 25) * S), radius=25 * S, fill=DARK + (255,))
        d.text((cx * S, yo * S), lab, font=f, anchor='mm', fill=GOLD_T + (255,))
    # штамп
    fill = GREEN if hit else LOSS if hit is not None else (120, 128, 142)
    word = 'ЗАШЁЛ' if hit else 'НЕ ЗАШЁЛ' if hit is not None else 'ВОЗВРАТ'
    fs = F(OSW, 70 * S, 700)
    sw = fs.getlength(word) + (150 if hit is not None else 90) * S
    ys0, ys1 = y0 + 262 - lift, y0 + 372 - lift
    _card(ov, (cx * S - sw / 2, ys0 * S, cx * S + sw / 2, ys1 * S), 55 * S, fill + (255,))
    d = ImageDraw.Draw(ov)
    ym = (ys0 + ys1) / 2
    if hit is not None:
        tx = cx * S + 32 * S
        _tick(d, tx - fs.getlength(word) / 2 - 40 * S, ym * S, 21 * S, hit, (255, 255, 255, 255), 8 * S)
    else:
        tx = cx * S
    d.text((tx, (ym - 3) * S), word, font=fs, anchor='mm', fill=(255, 255, 255, 255))
    # расчёт
    checks = list(pk.get('checks') or [])
    if checks:
        fc = F(MANROPE, 22 * S, 800)
        lh = 54
        bw = max(fc.getlength(t) for t, _ in checks) + 46 * S
        bx = cx * S - bw / 2
        yc = (ys1 + y1) / 2 - lh * (len(checks) - 1) / 2
        for i, (t, ok) in enumerate(checks):
            yy = (yc + i * lh) * S
            col = (120, 128, 142) if ok is None else GREEN if ok else LOSS
            d.ellipse((bx, yy - 15 * S, bx + 30 * S, yy + 15 * S), fill=col + (255,))
            _tick(d, bx + 15 * S, yy, 8 * S, ok, (255, 255, 255, 255), 3 * S)
            d.text((bx + 46 * S, yy), t, font=fc, anchor='lm', fill=INK + (255,))
    return _end(bg, ov, H, path)


# ------------------------------------------------------------------ вход
MATCHI = {'scales': _m_scales, 'rink': _rink, 'pennant': _m_pennant, 'rings': _m_rings}
ITOGI = {'winner': _r_winner, 'picks': _r_picks, 'numbers': _r_numbers, 'rink': lambda *a: _rink(*a, results=True)}
SINGLE = {'tape': _s_tape, 'final': _s_final, 'verdict': _s_verdict}


def matchi(items, path, style='scales', league='KHL', title='МАТЧИ ДНЯ', date_title=None, cont=False, rows=None):
    league = league.upper()
    return MATCHI[style](_resolve(items, league), path, league, title, date_title, cont, rows)


def itogi(items, path, style='winner', league='KHL', title='ИТОГИ ДНЯ', date_title=None, cont=False, rows=None):
    league = league.upper()
    return ITOGI[style](_resolve(items, league), path, league, title, date_title, cont, rows)


def single(m, path, style='tape', league='KHL', title=None):
    league = league.upper()
    return SINGLE[style](m, path, league, title or ('ИТОГ МАТЧА' if style in ('final', 'verdict') else 'МАТЧ ДНЯ'))
