"""«Итоги дня» — новые форматы с крупным счётом и другими фонами.

    import results_styles as rs
    rs.render(items, path, style='board', league='KHL', date_title='вторник, 29 сентября')

items: [{home, away, sh, sa, mark}], mark: '' | 'ОТ' | 'Б'.
style:
  'board'  — ТАБЛО: строка «эмблема ХОЗЯЕВА  3 : 2  ГОСТИ эмблема», графитовый фон;
  'tiles'  — ПЛИТКИ: сетка в две колонки, счёт крупно между эмблемами, фон — глубокий цвет лиги;
  'ticker' — СВЕТЛЫЙ: каждая команда своей строкой со счётом справа, как табло трансляции.
Для НХЛ перед вызовом нужен nhl.register() (эмблемы и названия клубов).
poster.py и recap.py не меняются — используются только их помощники.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import poster
import quality
import recap
import league_mark

S = 2
W = 1080
ACCENT = {'KHL': (255, 194, 61), 'NHL': (122, 202, 255)}
TAG = {'KHL': 'KXL', 'NHL': 'NHL'}
MARK_TEXT = {'ОТ': 'ОВЕРТАЙМ', 'Б': 'БУЛЛИТЫ', 'ОТ/Б': 'ОТ / БУЛЛИТЫ'}


def _short(team):
    return poster.SHORT.get(team, team).upper()


# ------------------------------------------------------------------ фоны
def _gradient(w, h, top, bottom, glow=None, glow_xy=(0.5, 0.0), glow_r=0.75, seed=3):
    """Вертикальный градиент + мягкое пятно света + лёгкий шум (без полос на градиенте)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = (yy / max(1, h - 1))[..., None]
    a = np.array(top, np.float32) * (1 - t) + np.array(bottom, np.float32) * t
    if glow:
        gx, gy = glow_xy[0] * w, glow_xy[1] * h
        r = glow_r * w
        k = np.clip(1 - np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2) / r, 0, 1)[..., None] ** 2
        a = a * (1 - k * glow[3] / 255) + np.array(glow[:3], np.float32) * k * glow[3] / 255
    a += np.random.default_rng(seed).normal(0, 1.2, a.shape)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')


def _bg(style, league, w, h):
    acc = ACCENT[league]
    if style == 'board':      # графит с тёплым (КХЛ) или ледяным (НХЛ) светом сверху
        bg = _gradient(w, h, (24, 26, 32), (9, 10, 13), glow=acc + (46,), glow_xy=(0.5, -0.05), glow_r=0.9)
        tint = None
    elif style == 'tiles':    # глубокий цвет лиги: бордо у КХЛ, тёмный лёд у НХЛ
        top, bottom = ((74, 12, 28), (14, 8, 20)) if league == 'KHL' else ((10, 44, 82), (5, 12, 26))
        bg = _gradient(w, h, top, bottom, glow=(255, 255, 255, 22), glow_xy=(0.85, 0.1), glow_r=0.8)
        tint = None
    else:                     # светлый «бумажный» фон, логотип лиги тёмным
        bg = _gradient(w, h, (242, 244, 248), (220, 226, 236), glow=acc + (40,), glow_xy=(0.5, -0.1), glow_r=0.9)
        tint = (20, 28, 44)
    return _watermark(bg, league, tint, 0.07 if tint else 0.12)


def _watermark(bg, league, tint, opacity):
    p = league_mark.path_for(league)
    if tint is None:
        return league_mark.apply(bg, p, opacity=opacity)
    import os
    if not os.path.exists(p):
        return bg
    logo = Image.open(p).convert('RGBA')
    dark = Image.new('RGBA', logo.size, tint + (0,))
    dark.putalpha(logo.getchannel('A'))
    tmp = p.replace('.png', '_dark.png')
    dark.save(tmp)
    return league_mark.apply(bg, tmp, opacity=opacity, desat=1.0)


# ------------------------------------------------------------------ общие куски
def _brand(d, cx, y, league, dark_text=False):
    fb = recap._fr('brand', 26 * S)
    sp, bar = 3 * S, 22 * S
    tag = TAG[league]
    w1 = sum(fb.getlength(c) for c in 'JARVIS') + sp * 5
    w2 = sum(fb.getlength(c) for c in tag) + sp * (len(tag) - 1)
    x0 = cx - (w1 + 2 * bar + w2) / 2
    ink = (18, 24, 36, 255) if dark_text else (255, 255, 255, 255)
    poster._spaced(d, (x0, y), 'JARVIS', fb, ink, sp)
    d.rounded_rectangle((x0 + w1 + bar - 1.5 * S, y - 14 * S, x0 + w1 + bar + 1.5 * S, y + 14 * S),
                        radius=S, fill=ink[:3] + (140,))
    acc = ACCENT[league] if not dark_text else _deepen(ACCENT[league])
    poster._spaced(d, (x0 + w1 + 2 * bar, y), tag, fb, acc + (255,), sp)


def _deepen(c):
    """Акцент для светлого фона: темнее, чтобы читался."""
    return tuple(int(v * 0.62) for v in c)


def _header(d, league, title, date_title, dark_text=False):
    _brand(d, W * S / 2, 62 * S, league, dark_text)
    ink = (16, 22, 34, 255) if dark_text else (255, 255, 255, 255)
    d.text((W * S / 2, 134 * S), title, font=recap._fr('title', 54 * S), fill=ink, anchor='mm')
    if date_title:
        d.text((W * S / 2, 192 * S), date_title.upper(), font=recap._fr('wide', 17 * S),
               fill=(84, 94, 112, 255) if dark_text else (198, 206, 220, 255), anchor='mm')


def _footer(d, H, league, dark_text=False):
    acc = _deepen(ACCENT[league]) if dark_text else ACCENT[league]
    poster._spaced(d, (W * S / 2, (H - 40) * S), '@jarvibet', recap._fr('wide', 17 * S), acc + (255,), 2 * S, anchor='m')


def _emblem(ov, team, cx, cy, d_pt):
    dd = int(d_pt * S)
    e = poster._circle_emblem(team, dd, S)
    poster._shadowed(ov, e, (int(cx - dd / 2), int(cy - dd / 2)), blur=9 * S, off=(0, 4 * S), color=(0, 0, 0, 130))


def _finish(bg, ov, H, path, grain):
    out = quality.compose(bg, ov).convert('RGB')                     # SCALE = 2 — без уменьшения, 2160×…
    out = out.filter(ImageFilter.UnsharpMask(radius=1.0, percent=40, threshold=2))
    if grain:
        out = quality.texture(out, grain)
    out.save(path, quality=95, subsampling=0, optimize=True)
    return path


def _mark_pill(d, cx, cy, mark, fg, bg, outline=None):
    if not mark:
        return
    t = MARK_TEXT.get(mark, mark)
    f = recap._fr('badge', 12 * S)
    w = f.getlength(t) + 22 * S
    d.rounded_rectangle((cx - w / 2, cy - 13 * S, cx + w / 2, cy + 13 * S), radius=13 * S, fill=bg,
                        outline=outline, width=2 * S if outline else 0)
    d.text((cx, cy), t, font=f, fill=fg, anchor='mm')


# ------------------------------------------------------------------ ТАБЛО
def _board(items, path, league, title, date_title):
    ROW, head, foot = 150, 250, 96
    H = head + ROW * len(items) + foot
    acc = ACCENT[league]
    bg = _bg('board', league, W, H)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _header(d, league, title, date_title)
    for i, it in enumerate(items):
        y0 = head + i * ROW
        cy = (y0 + ROW / 2 - 6) * S
        home_win = it['sh'] > it['sa']
        L, ld = poster._layer_draw(ov)
        ld.rounded_rectangle((32 * S, (y0 + 8) * S, (W - 32) * S, (y0 + ROW - 12) * S), radius=26 * S,
                             fill=(255, 255, 255, 14), outline=(255, 255, 255, 34), width=2 * S)
        # полоса победителя по краю карточки
        side = 32 if home_win else W - 32 - 8
        ld.rounded_rectangle((side * S, (y0 + 30) * S, (side + 8) * S, (y0 + ROW - 34) * S), radius=4 * S, fill=acc + (255,))
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)
        _emblem(ov, it['home'], 104 * S, cy, 84)
        _emblem(ov, it['away'], (W - 104) * S, cy, 84)
        d = ImageDraw.Draw(ov)
        for team, x, anchor, won in ((it['home'], 420, 'rm', home_win), (it['away'], W - 420, 'lm', not home_win)):
            f = recap._fit(_short(team), 'team', 25 * S, 250 * S, min_size=14 * S)
            d.text((x * S, cy), _short(team), font=f, anchor=anchor,
                   fill=(255, 255, 255, 255) if won else (255, 255, 255, 120))
        fn = recap._fr('num', 66 * S)
        cxs = W / 2 * S
        d.text((cxs - 22 * S, cy - 2 * S), str(it['sh']), font=fn, anchor='rm',
               fill=acc + (255,) if home_win else (255, 255, 255, 140))
        d.text((cxs, cy - 8 * S), ':', font=fn, anchor='mm', fill=(255, 255, 255, 110))
        d.text((cxs + 22 * S, cy - 2 * S), str(it['sa']), font=fn, anchor='lm',
               fill=acc + (255,) if not home_win else (255, 255, 255, 140))
        _mark_pill(d, cxs, cy + 44 * S, it.get('mark'), (12, 14, 18, 255), acc + (255,))
    _footer(d, H, league)
    return _finish(bg, ov, H, path, grain=0.55)


# ------------------------------------------------------------------ ПЛИТКИ
def _tiles(items, path, league, title, date_title):
    cols, gap, TH, head, foot = 2, 20, 250, 250, 96
    rows = (len(items) + cols - 1) // cols
    H = head + rows * (TH + gap) - gap + foot
    TW = (W - 2 * 32 - gap) / cols
    acc = ACCENT[league]
    bg = _bg('tiles', league, W, H)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _header(d, league, title, date_title)
    for i, it in enumerate(items):
        r, c = divmod(i, cols)
        x0 = 32 + c * (TW + gap)
        if r == rows - 1 and len(items) % cols and c == 0:      # последняя непарная плитка — по центру
            x0 = (W - TW) / 2
        y0 = head + r * (TH + gap)
        home_win = it['sh'] > it['sa']
        L, ld = poster._layer_draw(ov)
        ld.rounded_rectangle((x0 * S, y0 * S, (x0 + TW) * S, (y0 + TH) * S), radius=28 * S,
                             fill=(0, 0, 0, 96), outline=(255, 255, 255, 40), width=2 * S)
        ov.alpha_composite(L)
        cx = (x0 + TW / 2) * S
        ey = (y0 + 88) * S
        _emblem(ov, it['home'], (x0 + 78) * S, ey, 96)
        _emblem(ov, it['away'], (x0 + TW - 78) * S, ey, 96)
        d = ImageDraw.Draw(ov)
        fn = recap._fr('num', 72 * S)
        d.text((cx - 16 * S, ey), str(it['sh']), font=fn, anchor='rm', fill=acc + (255,) if home_win else (255, 255, 255, 150))
        d.text((cx, ey - 6 * S), ':', font=recap._fr('num', 56 * S), anchor='mm', fill=(255, 255, 255, 110))
        d.text((cx + 16 * S, ey), str(it['sa']), font=fn, anchor='lm', fill=acc + (255,) if not home_win else (255, 255, 255, 150))
        for team, x, won in ((it['home'], x0 + 78, home_win), (it['away'], x0 + TW - 78, not home_win)):
            f = recap._fit(_short(team), 'team', 19 * S, 150 * S, min_size=11 * S)
            d.text((x * S, (y0 + 162) * S), _short(team), font=f, anchor='mm',
                   fill=(255, 255, 255, 255) if won else (255, 255, 255, 135))
        if it.get('mark'):
            _mark_pill(d, cx, (y0 + 212) * S, it['mark'], acc + (255,), (0, 0, 0, 0), outline=acc + (200,))
        else:
            d.text((cx, (y0 + 212) * S), 'ОСНОВНОЕ ВРЕМЯ', font=recap._fr('label', 12 * S), anchor='mm', fill=(255, 255, 255, 110))
    _footer(d, H, league)
    return _finish(bg, ov, H, path, grain=0.5)


# ------------------------------------------------------------------ СВЕТЛЫЙ (табло трансляции)
def _ticker(items, path, league, title, date_title):
    ROW, gap, head, foot = 172, 18, 250, 96
    H = head + len(items) * (ROW + gap) - gap + foot
    acc = ACCENT[league]
    deep = _deepen(acc)
    bg = _bg('ticker', league, W, H)
    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _header(d, league, title, date_title, dark_text=True)
    for i, it in enumerate(items):
        y0 = head + i * (ROW + gap)
        home_win = it['sh'] > it['sa']
        # карточка с мягкой тенью
        card = Image.new('RGBA', ((W - 64) * S, ROW * S), (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius=24 * S, fill=(255, 255, 255, 245))
        poster._shadowed(ov, card, (32 * S, y0 * S), blur=14 * S, off=(0, 6 * S), color=(20, 30, 50, 60))
        d = ImageDraw.Draw(ov)
        # правый блок счёта — тёмный
        d.rounded_rectangle(((W - 32 - 190) * S, y0 * S, (W - 32) * S, (y0 + ROW) * S), radius=24 * S, fill=(18, 24, 36, 255))
        d.rectangle(((W - 32 - 190) * S, y0 * S, (W - 32 - 160) * S, (y0 + ROW) * S), fill=(18, 24, 36, 255))
        half = ROW / 2
        for k, (team, val, won) in enumerate(((it['home'], it['sh'], home_win), (it['away'], it['sa'], not home_win))):
            cy = (y0 + half / 2 + k * half) * S
            _emblem(ov, team, 96 * S, cy, 62)
            d = ImageDraw.Draw(ov)
            f = recap._fit(_short(team), 'team', 30 * S, 560 * S, min_size=16 * S)
            d.text((146 * S, cy), _short(team), font=f, anchor='lm', fill=(16, 22, 34, 255) if won else (130, 138, 152, 255))
            d.text(((W - 32 - 95) * S, cy), str(val), font=recap._fr('num', 58 * S), anchor='mm',
                   fill=acc + (255,) if won else (255, 255, 255, 120))
            if won:
                d.polygon([((W - 32 - 190 - 26) * S, cy), ((W - 32 - 190 - 12) * S, cy - 9 * S), ((W - 32 - 190 - 12) * S, cy + 9 * S)],
                          fill=deep + (255,))
        d.line(((146 * S, (y0 + half) * S), ((W - 32 - 210) * S, (y0 + half) * S)), fill=(220, 225, 234, 255), width=2 * S)
        if it.get('mark'):
            _mark_pill(d, (W - 32 - 300) * S, (y0 + half) * S, it['mark'], (255, 255, 255, 255), deep + (255,))
    _footer(d, H, league, dark_text=True)
    return _finish(bg, ov, H, path, grain=0.25)


STYLES = {'board': _board, 'tiles': _tiles, 'ticker': _ticker}


def _resolve(items, league):
    """Названия клубов НХЛ из таблицы («Рейнджерс») → ключи набора (как в nhl_kit)."""
    if league != 'NHL':
        return items
    import nhl
    out = []
    for it in items:
        it = dict(it)
        for k in ('home', 'away'):
            try:
                it[k] = nhl.resolve(it[k])
            except KeyError:
                pass
        out.append(it)
    return out


def render(items, path, style='board', league='KHL', title='ИТОГИ ДНЯ', date_title=None):
    league = league.upper()
    return STYLES[style](_resolve(items, league), path, league, title, date_title)
