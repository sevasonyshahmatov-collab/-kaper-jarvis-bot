"""Сводные баннеры JARVIS | KXL: итоги дня по прогнозам и афиша дня — все матчи на одном постере.

render_recap(items, path)  — итоги: прогноз, кэф, заход/незаход, счёт.
render_slate(items, path)  — афиша: время и коэффициенты П1/Х/П2.
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from poster import (TEAMS, SHORT, BANNER, ACC, _fluid_bg, _canvas_texture,
                    _circle_emblem, _raw_emblem, _shadowed, _layer_draw, _spaced)

_FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
FONTS_R = {
    'brand': (_FD + '/Unbounded[wght].ttf', 800),
    'title': (_FD + '/Montserrat[wght].ttf', 900),
    'team':  (_FD + '/Montserrat[wght].ttf', 900),
    'pred':  (_FD + '/Manrope[wght].ttf', 600),
    'label': (_FD + '/Manrope[wght].ttf', 700),
    'num':   (_FD + '/Montserrat[wght].ttf', 900),
    'badge': (_FD + '/Montserrat[wght].ttf', 800),
    'wide':  (_FD + '/Unbounded[wght].ttf', 400),
}
GREEN = (34, 197, 94)
RED = (226, 58, 78)

# Подпись под линией коэффициентов. Аудитория канала про аналитическую таблицу
# не знает, поэтому в тексте её не упоминаем.
FOOT_ODDS = 'КОЭФФИЦИЕНТЫ В ОСНОВНОЕ ВРЕМЯ НА МОМЕНТ ПУБЛИКАЦИИ'
INK = (8, 12, 20)


def _fr(kind, size):
    p, w = FONTS_R[kind]
    f = ImageFont.truetype(p, int(size))
    try:
        f.set_variation_by_axes([w])
    except Exception:
        pass
    return f


def _fit(text, kind, size, max_w, min_size=14):
    f = _fr(kind, size)
    while f.getlength(text) > max_w and size > min_size:
        size -= 1
        f = _fr(kind, size)
    return f


def _pill(d, box, text, font, fill, outline, color, radius=None):
    x1, y1, x2, y2 = box
    d.rounded_rectangle(box, radius=radius if radius is not None else int((y2 - y1) / 2),
                        fill=fill, outline=outline, width=max(1, int((y2 - y1) * 0.045)))
    d.text(((x1 + x2) / 2, (y1 + y2) / 2), text, font=font, fill=color, anchor='mm')


def _brand_kxl(d, cx, y, S, size=26):
    fb = _fr('brand', size * S)
    sp = 3 * S
    bar = 22 * S
    w1 = sum(fb.getlength(c) for c in 'JARVIS') + sp * 5
    w2 = sum(fb.getlength(c) for c in 'KXL') + sp * 2
    x0 = cx - (w1 + 2 * bar + w2) / 2
    _spaced(d, (x0, y), 'JARVIS', fb, (255, 255, 255, 255), sp)
    d.rounded_rectangle((x0 + w1 + bar - 1.5 * S, y - 14 * S, x0 + w1 + bar + 1.5 * S, y + 14 * S),
                        radius=S, fill=(255, 255, 255, 150))
    _spaced(d, (x0 + w1 + 2 * bar, y), 'KXL', fb, ACC + (255,), sp)


def _pair_name(home, away):
    return '%s — %s' % (SHORT.get(home, home).upper(), SHORT.get(away, away).upper())


def _base(W, H, S, seed=5, colors=None):
    """Тёмный фирменный фон с переливом и текстурой.

    colors=(c1, c2) — клубные цвета; приглушаем их к тёмной базе, иначе текст поверх плывёт.
    """
    if colors:
        def mute(c):
            return tuple(int(v * 0.48 + base * 0.28) for v, base in zip(c, (18, 26, 44)))
        c1, c2 = mute(colors[0]), mute(colors[1])
    else:
        c1, c2 = (30, 46, 78), (16, 22, 38)
    bg = _fluid_bg(W // 2, H // 2, c1, c2, seed=seed).resize((W, H), Image.LANCZOS)
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W * 0.18, -H * 0.06, W * 0.82, H * 0.10), fill=ACC + (34,))
    bg = Image.alpha_composite(bg.convert('RGBA'), glow.filter(ImageFilter.GaussianBlur(W // 10)))
    return bg


def _finish(bg, ov, W, H, path, grain=0.85):
    import quality
    out = quality.compose(bg, ov).convert('RGB')
    out = out.filter(ImageFilter.UnsharpMask(radius=1.0, percent=45, threshold=2))
    out = quality.texture(out, grain)
    out.save(path, optimize=True) if path.lower().endswith('.png') else out.save(path, quality=97, subsampling=0)
    return path


def _row_emblems(ov, home, away, cx, cy, S, d=74):
    """Две эмблемы в кругах, вторая чуть перекрывает первую."""
    dd = int(d * S)
    e1 = _circle_emblem(home, dd, S)
    e2 = _circle_emblem(away, dd, S)
    step = int(dd * 0.78)
    x0 = int(cx - (step + dd) / 2)
    _shadowed(ov, e1, (x0, int(cy - dd / 2)), blur=8 * S, off=(0, 3 * S), color=(0, 0, 0, 120))
    _shadowed(ov, e2, (x0 + step, int(cy - dd / 2)), blur=8 * S, off=(0, 3 * S), color=(0, 0, 0, 120))


def render_recap(items, path, title='ИТОГИ ДНЯ', date_title=None, handle='@jarvibet',
                 stake=1.0, W=1080, grain=0.85):
    """items: [{home, away, pred, coef, ok, score}] — ok=True «заход», False «незаход»."""
    S = 2
    ROW = 152
    head = 300 if not date_title else 348
    foot = 96
    H = head + ROW * len(items) + foot
    WW, HH = W * S, H * S

    bg = _base(W, H, S)
    bg = _canvas_texture(bg.convert('RGB'), grain).convert('RGBA')
    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # шапка
    _brand_kxl(d, WW / 2, int(62 * S), S, size=26)
    d.text((WW / 2, int(134 * S)), title, font=_fr('title', 54 * S), fill=(255, 255, 255, 255), anchor='mm')
    y_stat = int(206 * S)
    if date_title:
        d.text((WW / 2, int(190 * S)), date_title.upper(), font=_fr('wide', 17 * S),
               fill=(198, 206, 220, 255), anchor='mm')
        y_stat = int(254 * S)

    # статистика дня
    hits = sum(1 for it in items if it['ok'])
    misses = len(items) - hits
    profit = sum(((it.get('coef') or 1) - 1) * stake if it['ok'] else -stake for it in items)
    roi = profit / (stake * len(items)) * 100 if items else 0
    chips = [('ЗАХОДЫ', str(hits), GREEN),
             ('НЕЗАХОДЫ', str(misses), RED),
             ('ПРОФИТ', ('%+.2f' % profit).replace('.', ',') + ' ед.', ACC),
             ('ROI', ('%+.0f' % roi) + '%', ACC)]
    fl = _fr('label', 13 * S)
    fv = _fr('num', 21 * S)
    cw, gap = int(206 * S), int(14 * S)
    x = WW / 2 - (len(chips) * cw + (len(chips) - 1) * gap) / 2
    L, ld = _layer_draw(ov)
    for i, (lab, val, col) in enumerate(chips):
        bx = (x + i * (cw + gap), y_stat - 27 * S, x + i * (cw + gap) + cw, y_stat + 27 * S)
        ld.rounded_rectangle(bx, radius=18 * S, fill=(8, 12, 20, 170), outline=col + (150,), width=2 * S)
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    for i, (lab, val, col) in enumerate(chips):
        cx0 = x + i * (cw + gap) + cw / 2
        d.text((cx0, y_stat - 11 * S), lab, font=fl, fill=(168, 176, 192, 255), anchor='mm')
        d.text((cx0, y_stat + 14 * S), val, font=fv, fill=col + (255,), anchor='mm')

    # строки матчей
    for i, it in enumerate(items):
        y0 = head + i * ROW
        cy = (y0 + ROW / 2 - 6) * S
        col = GREEN if it['ok'] else RED
        L, ld = _layer_draw(ov)
        ld.rounded_rectangle((32 * S, (y0 + 6) * S, (W - 32) * S, (y0 + ROW - 14) * S),
                             radius=24 * S, fill=(8, 12, 20, 158), outline=(255, 255, 255, 40), width=2 * S)
        ld.rounded_rectangle((46 * S, (y0 + 30) * S, 53 * S, (y0 + ROW - 38) * S),
                             radius=4 * S, fill=col + (235,))
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)

        _row_emblems(ov, it['home'], it['away'], 158 * S, cy, S, d=74)
        d = ImageDraw.Draw(ov)

        name = _pair_name(it['home'], it['away'])
        fn = _fit(name, 'team', 27 * S, 470 * S, min_size=17 * S)
        d.text((248 * S, cy - 23 * S), name, font=fn, fill=(255, 255, 255, 255), anchor='lm')
        fp = _fit(it['pred'], 'pred', 19 * S, 480 * S, min_size=13 * S)
        d.text((248 * S, cy + 20 * S), it['pred'], font=fp, fill=(206, 214, 228, 255), anchor='lm')

        # правый блок: кэф · счёт · вердикт
        d.text((744 * S, cy - 22 * S), 'КЭФ', font=_fr('label', 13 * S), fill=(160, 168, 184, 255), anchor='mm')
        d.text((744 * S, cy + 12 * S), ('%.2f' % it['coef']) if it.get('coef') else '—',
               font=_fr('num', 25 * S), fill=(255, 255, 255, 255), anchor='mm')
        d.text((846 * S, cy - 22 * S), 'СЧЁТ', font=_fr('label', 13 * S), fill=(160, 168, 184, 255), anchor='mm')
        d.text((846 * S, cy + 12 * S), it['score'], font=_fr('num', 25 * S),
               fill=(232, 238, 248, 255), anchor='mm')
        L, ld = _layer_draw(ov)
        _pill(ld, (906 * S, cy - 26 * S, 1024 * S, cy + 26 * S),
              'ЗАХОД' if it['ok'] else 'НЕЗАХОД', _fr('badge', 15 * S),
              col + (56,), col + (255,), col + (255,), radius=16 * S)
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)

    d.text((WW / 2, (H - 52) * S), handle, font=_fr('wide', 17 * S), fill=ACC + (255,), anchor='mm')
    return _finish(bg, ov, W, H, path, grain=0.0)


def render_slate(items, path, title='МАТЧИ ДНЯ', date_title=None, handle='@jarvibet',
                 colors=None, W=1080, grain=0.85):
    """items: [{home, away, when, odds:(П1, Х, П2)}] — афиша дня, все матчи на одном баннере."""
    S = 2
    ROW = 158
    head = 236 if not date_title else 264
    foot = 118
    H = head + ROW * len(items) + foot
    WW, HH = W * S, H * S

    bg = _base(W, H, S, seed=9, colors=colors)
    bg = _canvas_texture(bg.convert('RGB'), grain).convert('RGBA')
    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    _brand_kxl(d, WW / 2, int(62 * S), S, size=26)
    d.text((WW / 2, int(134 * S)), title, font=_fr('title', 54 * S), fill=(255, 255, 255, 255), anchor='mm')
    if date_title:
        d.text((WW / 2, int(192 * S)), date_title.upper(), font=_fr('wide', 17 * S),
               fill=(198, 206, 220, 255), anchor='mm')

    for i, it in enumerate(items):
        y0 = head + i * ROW
        cy = (y0 + ROW / 2 - 8) * S
        L, ld = _layer_draw(ov)
        ld.rounded_rectangle((32 * S, (y0 + 6) * S, (W - 32) * S, (y0 + ROW - 16) * S),
                             radius=24 * S, fill=(8, 12, 20, 158), outline=(255, 255, 255, 40), width=2 * S)
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)

        _row_emblems(ov, it['home'], it['away'], 150 * S, cy, S, d=76)
        d = ImageDraw.Draw(ov)

        name = _pair_name(it['home'], it['away'])
        fn = _fit(name, 'team', 28 * S, 400 * S, min_size=17 * S)
        d.text((246 * S, cy - 20 * S), name, font=fn, fill=(255, 255, 255, 255), anchor='lm')
        d.text((246 * S, cy + 22 * S), it['when'], font=_fr('label', 18 * S),
               fill=ACC + (255,), anchor='lm')

        odds = it['odds']
        labels = ['П1', 'Х', 'П2']
        best = min(range(len(odds)), key=lambda k: odds[k])
        cw, gap = int(104 * S), int(12 * S)
        x = (W - 40) * S - (len(odds) * cw + (len(odds) - 1) * gap)
        L, ld = _layer_draw(ov)
        for k in range(len(odds)):
            bx = (x + k * (cw + gap), cy - 30 * S, x + k * (cw + gap) + cw, cy + 30 * S)
            ld.rounded_rectangle(bx, radius=18 * S, fill=(8, 12, 20, 180),
                                 outline=(ACC + (230,)) if k == best else (255, 255, 255, 70), width=2 * S)
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)
        for k, v in enumerate(odds):
            cx0 = x + k * (cw + gap) + cw / 2
            d.text((cx0, cy - 13 * S), labels[k], font=_fr('label', 13 * S),
                   fill=(160, 168, 184, 255), anchor='mm')
            d.text((cx0, cy + 13 * S), '%.2f' % v, font=_fr('num', 21 * S),
                   fill=(ACC + (255,)) if k == best else (255, 255, 255, 255), anchor='mm')

    d.text((WW / 2, (H - 76) * S), FOOT_ODDS,
           font=_fr('wide', 12 * S), fill=(190, 198, 212, 255), anchor='mm')
    d.text((WW / 2, (H - 44) * S), handle, font=_fr('wide', 17 * S), fill=ACC + (255,), anchor='mm')
    return _finish(bg, ov, W, H, path, grain=0.0)


# ----------------- постер «прогнозы зашли»: 1-3 прогноза с итогом -----------------
GREEN_HIT = (36, 200, 88)


def _needs_plate(team):
    """Тёмная эмблема на тёмном фоне — даём белую подложку."""
    import numpy as np
    e = _raw_emblem(team, 200, 200)
    a = np.asarray(e).astype(np.float32)
    op = a[..., 3] > 128
    if not op.any():
        return False
    m = a[..., :3][op].mean(axis=0)
    return float(0.3 * m[0] + 0.59 * m[1] + 0.11 * m[2]) < 95


def _check(d, cx, cy, r, color, width):
    """Галочка, нарисованная линиями — эмодзи в этих шрифтах нет."""
    d.line([(cx - r, cy + r * 0.05), (cx - r * 0.28, cy + r * 0.72), (cx + r, cy - r * 0.72)],
           fill=color, width=width, joint='curve')


def _cross(d, cx, cy, r, color, width):
    d.line([(cx - r * 0.7, cy - r * 0.7), (cx + r * 0.7, cy + r * 0.7)], fill=color, width=width)
    d.line([(cx - r * 0.7, cy + r * 0.7), (cx + r * 0.7, cy - r * 0.7)], fill=color, width=width)


def render_hits(items, path, date_title, colors=None, express=None, handle=None,
                W=1280, H=640, grain=0.9, seed=None):
    """items: [{home, away, score, mark, pred, coef, ok}] — итоги прогнозов на одном постере.

    mark — «ОТ» / «Б» или пусто; colors — пара RGB для фона (по умолчанию из цветов команд).
    """
    import numpy as np
    S = 2
    WW, HH = W * S, H * S
    n = len(items)
    all_ok = all(it.get('ok', True) for it in items)

    if colors is None:
        first, last = items[0], items[-1]
        colors = (BANNER.get(first['away'], (40, 120, 90)), BANNER.get(last['home'], (40, 80, 150)))

    def mute(c):
        """Клубный цвет приглушаем к тёмно-синей базе — иначе две разные команды дерутся на фоне."""
        return tuple(int(v * 0.52 + base * 0.30) for v, base in zip(c, (20, 30, 52)))
    c1, c2 = mute(colors[0]), mute(colors[1])
    if seed is None:
        seed = (sum(map(ord, items[0]['home'] + items[-1]['away'])) % 997)

    bg = _fluid_bg(WW // 2, HH // 2, c1, c2, seed=seed).resize((W, H), Image.LANCZOS)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dim = 0.34 * np.exp(-(((yy / H) - 0.97) ** 2) / 0.02) + 0.20 * np.exp(-(((yy / H) - 0.52) ** 2) / 0.10)
    shade = Image.new('RGBA', (W, H), (5, 8, 14, 0))
    shade.putalpha(Image.fromarray((np.clip(dim, 0, 1) * 255).astype('uint8'), 'L'))
    bg = Image.alpha_composite(bg.convert('RGBA'), shade).convert('RGB')
    bg = _canvas_texture(bg, grain).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # шапка
    _brand_kxl(d, WW / 2, int(52 * S), S, size=25)
    title = 'ПРОГНОЗЫ ЗАШЛИ' if all_ok else 'ИТОГИ ПРОГНОЗОВ'
    ft = _fit(title, 'title', 62 * S, 1080 * S, min_size=34 * S)
    d.text((WW / 2, int(118 * S)), title, font=ft, fill=(255, 255, 255, 255), anchor='mm')
    hits = sum(1 for it in items if it.get('ok', True))
    sub = '%s  ·  %d ИЗ %d' % (date_title, hits, n)
    if express and all_ok and n > 1:
        sub += '  ·  ВМЕСТЕ ЭКСПРЕССОМ %.2f' % express
    _spaced(d, (WW / 2, int(172 * S)), sub, _fr('wide', 15 * S),
            (GREEN_HIT if all_ok else ACC) + (255,), 2 * S, anchor='m')

    # строки прогнозов
    top = 208
    row_h = int((H - 74 - top) / n) - 18
    # общий кегль для всех прогнозов — по самому длинному, чтобы строки были одинаковыми
    pred_size = 27 * S
    for it in items:
        while _fr('team', pred_size).getlength(it['pred']) > 450 * S and pred_size > 17 * S:
            pred_size -= 1
    for i, it in enumerate(items):
        ok = it.get('ok', True)
        col = GREEN_HIT if ok else RED
        y0 = top + i * (row_h + 18)
        cy = (y0 + row_h / 2) * S
        L, ld = _layer_draw(ov)
        ld.rounded_rectangle((64 * S, y0 * S, (W - 64) * S, (y0 + row_h) * S),
                             radius=26 * S, fill=(8, 13, 22, 205), outline=col + (110,), width=2 * S)
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)

        # эмблемы и счёт
        eh = int(min(94, row_h - 46))
        for team, cx in ((it['home'], 136), (it['away'], 402)):
            e = _raw_emblem(team, int(112 * S), int(eh * S), plate=_needs_plate(team))
            _shadowed(ov, e, (int(cx * S - e.width / 2), int(cy - e.height / 2)),
                      blur=14, off=(0, 6), color=(0, 0, 0, 120))
        d = ImageDraw.Draw(ov)
        d.text((269 * S, cy - 9 * S), it['score'], font=_fr('num', 42 * S),
               fill=(255, 255, 255, 255), anchor='mm')
        label = 'СЧЁТ' + (('  ·  ' + it['mark']) if it.get('mark') else '')
        _spaced(d, (269 * S, cy + 26 * S), label, _fr('label', 12 * S), (168, 178, 196, 255), 1.5 * S, anchor='m')

        # название матча и прогноз
        _spaced(d, (472 * S, cy - 24 * S), _pair_name(it['home'], it['away']),
                _fr('label', 15 * S), (186, 196, 214, 255), 1.6 * S)
        d.text((472 * S, cy + 16 * S), it['pred'], font=_fr('team', pred_size),
               fill=(255, 255, 255, 255), anchor='lm')

        # плашка с коэффициентом
        L, ld = _layer_draw(ov)
        ld.rounded_rectangle((962 * S, cy - 33 * S, 1186 * S, cy + 33 * S), radius=33 * S, fill=col + (255,))
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)
        _spaced(d, (998 * S, cy), 'КЭФ', _fr('label', 13 * S), (10, 26, 14, 255), 1.5 * S, anchor='m')
        d.text((1086 * S, cy), ('%.2f' % it['coef']) if it.get('coef') else '—',
                font=_fr('num', 26 * S), fill=(8, 22, 12, 255), anchor='mm')
        if ok:
            _check(d, 1152 * S, cy, 15 * S, (8, 22, 12, 255), int(5 * S))
        else:
            _cross(d, 1152 * S, cy, 15 * S, (26, 8, 10, 255), int(5 * S))

    foot = 'КОЭФФИЦИЕНТЫ НА МОМЕНТ ПУБЛИКАЦИИ ПРОГНОЗА' if not handle else handle
    _spaced(d, (WW / 2, (H - 34) * S), foot, _fr('wide', 12 * S), (198, 206, 220, 255), 1.5 * S, anchor='m')
    return _finish(bg, ov, W, H, path, grain=0.0)


# ----------------- итог одного матча: счёт + обновлённые очки и форма -----------------
def render_result(home, away, sh, sa, path, verdict=None, verdict_color=None, when=None, handle='@jarvibet',
                  home_info=None, away_info=None, W=1280, H=640, grain=1.0, seed=None):
    """Баннер с итогом матча в стиле «Карточек»: эмблемы, счёт между ними, очки и форма после игры."""
    import numpy as np
    from poster import _form_row
    S = 2
    WW, HH = W * S, H * S
    c1 = BANNER.get(home, (120, 120, 120))
    c2 = BANNER.get(away, (120, 120, 120))
    if seed is None:
        seed = (sum(map(ord, home + away)) % 997)

    bg = _fluid_bg(WW // 2, HH // 2, c1, c2, seed=seed).resize((W, H), Image.LANCZOS)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dim = 0.40 * np.exp(-(((yy / H) - 0.97) ** 2) / 0.02)
    shade = Image.new('RGBA', (W, H), (5, 8, 14, 0))
    shade.putalpha(Image.fromarray((np.clip(dim, 0, 1) * 255).astype('uint8'), 'L'))
    bg = Image.alpha_composite(bg.convert('RGBA'), shade).convert('RGB')
    bg = _canvas_texture(bg, grain).convert('RGBA')

    cards = [(56, 104, 580, 470), (700, 104, 1224, 470)]
    for (x1, y1, x2, y2) in cards:            # стеклянные карточки: размытие под ними
        reg = bg.crop((x1, y1, x2, y2)).filter(ImageFilter.GaussianBlur(18))
        m = Image.new('L', (x2 - x1, y2 - y1), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, x2 - x1 - 1, y2 - y1 - 1), radius=28, fill=255)
        bg.paste(reg, (x1, y1), m)

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    win_h, win_a = sh > sa, sa > sh
    L, ld = _layer_draw(ov)
    for (x1, y1, x2, y2), won in zip(cards, (win_h, win_a)):
        ld.rounded_rectangle((x1 * S, y1 * S, x2 * S, y2 * S), radius=28 * S,
                             fill=(8, 12, 20, 158),
                             outline=(GREEN_HIT + (170,)) if won else (255, 255, 255, 46), width=2 * S)
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)

    _brand_kxl(d, WW / 2, int(56 * S), S, size=26)

    infos = (home_info or {}, away_info or {})
    for team, t, (x1, y1, x2, y2) in zip((home, away), infos, cards):
        cx = (x1 + x2) / 2 * S
        e = _raw_emblem(team, 200 * S, 150 * S, plate=_needs_plate(team))
        _shadowed(ov, e, (int(cx - e.width / 2), int(y1 * S + 24 * S + (150 * S - e.height) / 2)),
                  blur=20, off=(0, 10), color=(0, 0, 0, 110))
        d = ImageDraw.Draw(ov)
        name = SHORT.get(team, team).upper()
        fn = _fit(name, 'team', 54 * S, 440 * S, min_size=34 * S)
        d.text((cx, (y1 + 214) * S), name, font=fn, fill=(255, 255, 255, 255), anchor='mm')
        if t.get('line'):
            d.text((cx, (y1 + 260) * S), t['line'].upper(), font=_fr('wide', 17 * S),
                   fill=(214, 220, 230, 255), anchor='mm')
        d.line((cx - 150 * S, (y1 + 284) * S, cx + 150 * S, (y1 + 284) * S), fill=(255, 255, 255, 36), width=S)
        if t.get('form'):
            _form_row(d, cx, (y1 + 322) * S, t['form'][-5:], S)

    # счёт между карточками
    d.text((WW / 2, 274 * S), '%d:%d' % (sh, sa), font=_fr('num', 46 * S),
           fill=(255, 255, 255, 255), anchor='mm')
    _spaced(d, (WW / 2, 312 * S), 'СЧЁТ', _fr('label', 12 * S), (176, 186, 202, 255), 1.6 * S, anchor='m')

    # итог матча
    if verdict:
        fv = _fit(verdict, 'team', 23 * S, 640 * S, min_size=15 * S)
        tw = fv.getlength(verdict)
        L, ld = _layer_draw(ov)
        vc = verdict_color or ACC
        ld.rounded_rectangle((WW / 2 - tw / 2 - 34 * S, 488 * S, WW / 2 + tw / 2 + 34 * S, 542 * S),
                             radius=27 * S, fill=(8, 12, 20, 210), outline=vc + (230,), width=2 * S)
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)
        d.text((WW / 2, 515 * S), verdict, font=fv, fill=(255, 255, 255, 255), anchor='mm')
    if when:
        _spaced(d, (WW / 2, 578 * S), when, _fr('wide', 13 * S), (198, 206, 220, 255), 1.6 * S, anchor='m')
    if handle:
        _spaced(d, (WW / 2, 616 * S), handle, _fr('wide', 13 * S), ACC + (255,), 1.6 * S, anchor='m')
    return _finish(bg, ov, W, H, path, grain=0.0)


# ----------------- прогноз на матч без эмблем в наборе (НХЛ и прочие лиги) -----------------
def _patch(ov, cx, cy, size, code, fill, edge, S):
    """Монограмма клуба: плашка в цветах команды с диагональной полосой и трёхбуквенным кодом."""
    d_ = int(size * S)
    tile = Image.new('RGBA', (d_, d_), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    td.rounded_rectangle((0, 0, d_ - 1, d_ - 1), radius=int(d_ * 0.23), fill=fill + (255,))
    stripe = Image.new('RGBA', (d_, d_), (0, 0, 0, 0))
    ImageDraw.Draw(stripe).polygon([(0, d_), (d_ * 0.42, d_), (d_, d_ * 0.36), (d_, d_ * 0.62)],
                                   fill=edge + (58,))
    mask = Image.new('L', (d_, d_), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, d_ - 1, d_ - 1), radius=int(d_ * 0.23), fill=255)
    tile.alpha_composite(Image.composite(stripe, Image.new('RGBA', (d_, d_), (0, 0, 0, 0)), mask))
    td = ImageDraw.Draw(tile)
    td.rounded_rectangle((0, 0, d_ - 1, d_ - 1), radius=int(d_ * 0.23), outline=edge + (235,), width=int(3 * S))
    f = _fr('title', int(size * 0.33) * S)
    td.text((d_ / 2, d_ / 2), code, font=f, fill=(255, 255, 255, 255), anchor='mm')
    _shadowed(ov, tile, (int(cx * S - d_ / 2), int(cy * S - d_ / 2)), blur=22, off=(0, 12), color=(0, 0, 0, 130))


def render_pick(m, path, handle='@jarvibet', W=1280, H=640, grain=1.0, seed=17):
    """Прогноз на матч: монограммы команд, контекст, время и коэффициент."""
    import numpy as np
    S = 2
    WW, HH = W * S, H * S
    c1, c2 = m.get('colors', ((26, 60, 90), (30, 40, 70)))

    bg = _fluid_bg(WW // 2, HH // 2, c1, c2, seed=seed).resize((W, H), Image.LANCZOS)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dim = 0.36 * np.exp(-(((yy / H) - 0.98) ** 2) / 0.02) + 0.18 * np.exp(-(((yy / H) - 0.80) ** 2) / 0.06)
    shade = Image.new('RGBA', (W, H), (5, 8, 14, 0))
    shade.putalpha(Image.fromarray((np.clip(dim, 0, 1) * 255).astype('uint8'), 'L'))
    bg = Image.alpha_composite(bg.convert('RGBA'), shade).convert('RGB')
    bg = _canvas_texture(bg, grain).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _brand_kxl(d, WW / 2, int(52 * S), S, size=25)
    _spaced(d, (WW / 2, 92 * S), m['league'], _fr('wide', 14 * S), (206, 214, 228, 255), 2 * S, anchor='m')

    for side, cx in ((m['home'], 330), (m['away'], 950)):
        if side.get('team') in TEAMS:      # есть эмблема в наборе — ставим её
            e = _raw_emblem(side['team'], 210 * S, 150 * S, plate=_needs_plate(side['team']))
            _shadowed(ov, e, (int(cx * S - e.width / 2), int(198 * S - e.height / 2)),
                      blur=24, off=(0, 12), color=(0, 0, 0, 130))
        else:                               # эмблемы нет — монограмма в цветах клуба
            _patch(ov, cx, 198, 132, side['code'], side['color'], side['edge'], S)
    d = ImageDraw.Draw(ov)
    d.text((WW / 2, 198 * S), 'VS', font=_fr('team', 26 * S), fill=(255, 255, 255, 205), anchor='mm')
    for side, cx in ((m['home'], 330), (m['away'], 950)):
        fn = _fit(side['name'], 'team', 38 * S, 420 * S, min_size=24 * S)
        d.text((cx * S, 302 * S), side['name'], font=fn, fill=(255, 255, 255, 255), anchor='mm')
        _spaced(d, (cx * S, 336 * S), side['sub'], _fr('wide', 14 * S), (208, 216, 228, 255), 2 * S, anchor='m')
    if m.get('note'):
        _spaced(d, (WW / 2, 378 * S), m['note'], _fr('wide', 13 * S), (188, 198, 214, 255), 1.6 * S, anchor='m')

    # время
    fw = _fr('num', 22 * S)
    tw = fw.getlength(m['when'])
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((WW / 2 - tw / 2 - 30 * S, 408 * S, WW / 2 + tw / 2 + 30 * S, 460 * S),
                         radius=26 * S, fill=(8, 12, 20, 205), outline=ACC + (220,), width=2 * S)
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    d.text((WW / 2, 434 * S), m['when'], font=fw, fill=(255, 255, 255, 255), anchor='mm')

    # прогноз + коэффициент
    fp = _fit(m['pred'], 'team', 24 * S, 720 * S, min_size=16 * S)
    pw = fp.getlength(m['pred']) + 68 * S
    kw = 196 * S
    gap = 16 * S
    x0 = WW / 2 - (pw + gap + kw) / 2
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((x0, 486 * S, x0 + pw, 552 * S), radius=33 * S,
                         fill=(8, 12, 20, 215), outline=(255, 255, 255, 80), width=2 * S)
    ld.rounded_rectangle((x0 + pw + gap, 486 * S, x0 + pw + gap + kw, 552 * S), radius=33 * S, fill=ACC + (255,))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    d.text((x0 + pw / 2, 519 * S), m['pred'], font=fp, fill=(255, 255, 255, 255), anchor='mm')
    _spaced(d, (x0 + pw + gap + 52 * S, 519 * S), 'КЭФ', _fr('label', 13 * S), (34, 26, 6, 255), 1.5 * S, anchor='m')
    d.text((x0 + pw + gap + 132 * S, 519 * S), '%.2f' % m['coef'], font=_fr('num', 26 * S),
           fill=(26, 20, 4, 255), anchor='mm')

    _spaced(d, (WW / 2, 596 * S), 'ПРОГНОЗ КАНАЛА · КОЭФФИЦИЕНТ НА МОМЕНТ ПУБЛИКАЦИИ',
            _fr('wide', 12 * S), (196, 204, 218, 255), 1.5 * S, anchor='m')
    if handle:
        _spaced(d, (WW / 2, 624 * S), handle, _fr('wide', 13 * S), ACC + (255,), 1.6 * S, anchor='m')
    return _finish(bg, ov, W, H, path, grain=0.0)


# ----------------- прогноз в «Карточках» (формат КХЛ) -----------------
def render_cards_pick(home, away, path, info, W=1280, H=640, grain=1.0, seed=None):
    """Те же стеклянные карточки, что в баннерах матчей, но снизу — прогноз и коэффициент."""
    import numpy as np
    from poster import _form_row
    S = 2
    WW, HH = W * S, H * S
    c1 = BANNER.get(home, (120, 120, 120))
    c2 = BANNER.get(away, (120, 120, 120))
    if seed is None:
        seed = (sum(map(ord, home + away)) % 997)

    bg = _fluid_bg(WW // 2, HH // 2, c1, c2, seed=seed).resize((W, H), Image.LANCZOS)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dim = 0.40 * np.exp(-(((yy / H) - 0.97) ** 2) / 0.02)
    shade = Image.new('RGBA', (W, H), (5, 8, 14, 0))
    shade.putalpha(Image.fromarray((np.clip(dim, 0, 1) * 255).astype('uint8'), 'L'))
    bg = Image.alpha_composite(bg.convert('RGBA'), shade).convert('RGB')
    bg = _canvas_texture(bg, grain).convert('RGBA')

    cards = [(56, 104, 580, 470), (700, 104, 1224, 470)]
    for (x1, y1, x2, y2) in cards:
        reg = bg.crop((x1, y1, x2, y2)).filter(ImageFilter.GaussianBlur(18))
        m_ = Image.new('L', (x2 - x1, y2 - y1), 0)
        ImageDraw.Draw(m_).rounded_rectangle((0, 0, x2 - x1 - 1, y2 - y1 - 1), radius=28, fill=255)
        bg.paste(reg, (x1, y1), m_)

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    L, ld = _layer_draw(ov)
    for (x1, y1, x2, y2) in cards:
        ld.rounded_rectangle((x1 * S, y1 * S, x2 * S, y2 * S), radius=28 * S,
                             fill=(8, 12, 20, 150), outline=(255, 255, 255, 46), width=2 * S)
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    _brand_kxl(d, WW / 2, int(56 * S), S, size=26)

    for team, t, (x1, y1, x2, y2) in ((home, info['home'], cards[0]), (away, info['away'], cards[1])):
        cx = (x1 + x2) / 2 * S
        e = _raw_emblem(team, 200 * S, 150 * S, plate=_needs_plate(team))
        _shadowed(ov, e, (int(cx - e.width / 2), int(y1 * S + 24 * S + (150 * S - e.height) / 2)),
                  blur=20, off=(0, 10), color=(0, 0, 0, 110))
        d = ImageDraw.Draw(ov)
        name = SHORT.get(team, team).upper()
        size = 54 * S
        ft = _fr('team', size)
        while ft.getlength(name) > 440 * S and size > 34 * S:
            size -= 2 * S
            ft = _fr('team', size)
        d.text((cx, (y1 + 214) * S), name, font=ft, fill=(255, 255, 255, 255), anchor='mm')
        d.text((cx, (y1 + 260) * S), t['line'].upper(), font=_fr('wide', 17 * S),
               fill=(214, 220, 230, 255), anchor='mm')
        d.line((cx - 150 * S, (y1 + 284) * S, cx + 150 * S, (y1 + 284) * S), fill=(255, 255, 255, 36), width=S)
        _form_row(d, cx, (y1 + 322) * S, t.get('form', '')[-5:], S)

    d.text((WW / 2, (104 + 470) / 2 * S), 'VS', font=_fr('team', 26 * S), fill=(255, 255, 255, 200), anchor='mm')

    # время
    ft = _fr('num', 24 * S)
    tw = ft.getlength(info['when'])
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((WW / 2 - tw / 2 - 30 * S, 490 * S, WW / 2 + tw / 2 + 30 * S, 542 * S),
                         radius=26 * S, fill=(8, 12, 20, 210), outline=ACC + (220,), width=2 * S)
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    d.text((WW / 2, 516 * S), info['when'], font=ft, fill=(255, 255, 255, 255), anchor='mm')

    # прогноз и коэффициент (кэф необязателен)
    fp = _fit(info['pred'], 'team', 22 * S, 560 * S, min_size=14 * S)
    pw = fp.getlength(info['pred']) + 56 * S
    has_coef = info.get('coef') is not None
    kw = 152 * S if has_coef else 0
    gp = 12 * S if has_coef else 0
    xs = WW / 2 - (pw + gp + kw) / 2
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((xs, 558 * S, xs + pw, 606 * S), radius=24 * S,
                         fill=(8, 12, 20, 190), outline=(255, 255, 255, 70), width=2 * S)
    if has_coef:
        ld.rounded_rectangle((xs + pw + gp, 558 * S, xs + pw + gp + kw, 606 * S), radius=24 * S, fill=ACC + (255,))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    d.text((xs + pw / 2, 582 * S), info['pred'], font=fp, fill=(255, 255, 255, 255), anchor='mm')
    if has_coef:
        _spaced(d, (xs + pw + gp + 42 * S, 582 * S), 'КЭФ', _fr('label', 13 * S), (26, 20, 6, 255), 2 * S, anchor='m')
        d.text((xs + pw + gp + 106 * S, 582 * S), '%.2f' % info['coef'], font=_fr('num', 23 * S),
               fill=(16, 14, 6, 255), anchor='mm')

    _spaced(d, (WW / 2, 626 * S), info.get('foot', 'ПРОГНОЗ КАНАЛА · КОЭФФИЦИЕНТ НА МОМЕНТ ПУБЛИКАЦИИ'),
            _fr('wide', 11 * S), (196, 202, 214, 255), 1.5 * S, anchor='m')
    return _finish(bg, ov, W, H, path, grain=0.0)


# ----------------- итоги дня: все матчи со счётом на одном баннере -----------------
def render_results_day(items, path, title='ИТОГИ ДНЯ', date_title=None, handle='@jarvibet',
                       W=1080, grain=0.85):
    """items: [{home, away, sh, sa, mark}] — mark: '' | 'ОТ' | 'Б'."""
    S = 2
    ROW = 158
    head = 236 if not date_title else 264
    foot = 100
    H = head + ROW * len(items) + foot
    WW, HH = W * S, H * S

    bg = _base(W, H, S, seed=13)
    bg = _canvas_texture(bg.convert('RGB'), grain).convert('RGBA')
    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    _brand_kxl(d, WW / 2, int(62 * S), S, size=26)
    d.text((WW / 2, int(134 * S)), title, font=_fr('title', 54 * S), fill=(255, 255, 255, 255), anchor='mm')
    if date_title:
        d.text((WW / 2, int(192 * S)), date_title.upper(), font=_fr('wide', 17 * S),
               fill=(198, 206, 220, 255), anchor='mm')

    for i, it in enumerate(items):
        y0 = head + i * ROW
        cy = (y0 + ROW / 2 - 8) * S
        L, ld = _layer_draw(ov)
        ld.rounded_rectangle((32 * S, (y0 + 6) * S, (W - 32) * S, (y0 + ROW - 16) * S),
                             radius=24 * S, fill=(8, 12, 20, 158), outline=(255, 255, 255, 40), width=2 * S)
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)

        _row_emblems(ov, it['home'], it['away'], 150 * S, cy, S, d=76)
        d = ImageDraw.Draw(ov)

        name = _pair_name(it['home'], it['away'])
        fn = _fit(name, 'team', 28 * S, 430 * S, min_size=17 * S)
        d.text((246 * S, cy - 20 * S), name, font=fn, fill=(255, 255, 255, 255), anchor='lm')
        sub = {'ОТ': 'ПОБЕДА В ОВЕРТАЙМЕ', 'Б': 'ПОБЕДА ПО БУЛЛИТАМ'}.get(it.get('mark', ''), 'ОСНОВНОЕ ВРЕМЯ')
        _spaced(d, (246 * S, cy + 22 * S), sub, _fr('label', 14 * S),
                (ACC if it.get('mark') else (162, 172, 190)) + (255,), 2 * S)

        # счёт: две ячейки, у победителя — золотая
        cw, gap = int(104 * S), int(12 * S)
        x = (W - 40) * S - (2 * cw + gap)
        home_win = it['sh'] > it['sa']
        L, ld = _layer_draw(ov)
        for k, won in enumerate((home_win, not home_win)):
            bx = (x + k * (cw + gap), cy - 30 * S, x + k * (cw + gap) + cw, cy + 30 * S)
            ld.rounded_rectangle(bx, radius=18 * S, fill=(8, 12, 20, 180),
                                 outline=(ACC + (230,)) if won else (255, 255, 255, 70), width=2 * S)
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)
        for k, (val, won, lab) in enumerate(((it['sh'], home_win, SHORT.get(it['home'], it['home']).upper()),
                                             (it['sa'], not home_win, SHORT.get(it['away'], it['away']).upper()))):
            cx0 = x + k * (cw + gap) + cw / 2
            # название ужимаем шрифтом под ячейку, а не режем по символам:
            # иначе «Нефтехимик» превращается в «НЕФТЕХИМ»
            fl = _fit(lab, 'label', 11 * S, cw - 14 * S, min_size=7 * S)
            d.text((cx0, cy - 13 * S), lab, font=fl, fill=(150, 160, 178, 255), anchor='mm')
            d.text((cx0, cy + 14 * S), str(val), font=_fr('num', 24 * S),
                   fill=(ACC + (255,)) if won else (255, 255, 255, 255), anchor='mm')

    d.text((WW / 2, (H - 62) * S), 'ЦВЕТОМ ВЫДЕЛЕН ПОБЕДИТЕЛЬ МАТЧА', font=_fr('wide', 12 * S),
           fill=(190, 198, 212, 255), anchor='mm')
    _spaced(d, (WW / 2, (H - 34) * S), handle, _fr('wide', 17 * S), ACC + (255,), 2 * S, anchor='m')
    return _finish(bg, ov, W, H, path, grain=0.0)


# ----------------- двойной прогноз: несколько ставок до матчей -----------------
def render_picks(items, path, date_title, express=None, handle='@jarvibet',
                 title='ПРОГНОЗЫ ДНЯ', W=1080, grain=0.85):
    """items: [{home, away, pred, coef, when}] — постер со ставками до начала матчей."""
    S = 2
    ROW = 152
    head = 254
    foot = 96
    H = head + ROW * len(items) + foot
    WW, HH = W * S, H * S

    bg = _base(W, H, S, seed=21)
    bg = _canvas_texture(bg.convert('RGB'), grain).convert('RGBA')
    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    _brand_kxl(d, WW / 2, int(62 * S), S, size=26)
    d.text((WW / 2, int(136 * S)), title, font=_fr('title', 52 * S), fill=(255, 255, 255, 255), anchor='mm')
    sub = date_title.upper()
    if express and len(items) > 1:
        sub += '  ·  ВМЕСТЕ ЭКСПРЕССОМ %.2f' % express
    _spaced(d, (WW / 2, 194 * S), sub, _fr('wide', 15 * S), ACC + (255,), 2 * S, anchor='m')

    for i, it in enumerate(items):
        y0 = head + i * ROW
        cy = (y0 + ROW / 2 - 6) * S
        L, ld = _layer_draw(ov)
        ld.rounded_rectangle((32 * S, (y0 + 6) * S, (W - 32) * S, (y0 + ROW - 14) * S),
                             radius=24 * S, fill=(8, 12, 20, 158), outline=(255, 255, 255, 40), width=2 * S)
        ld.rounded_rectangle((46 * S, (y0 + 30) * S, 53 * S, (y0 + ROW - 38) * S), radius=4 * S, fill=ACC + (235,))
        ov.alpha_composite(L)
        d = ImageDraw.Draw(ov)

        _row_emblems(ov, it['home'], it['away'], 158 * S, cy, S, d=74)
        d = ImageDraw.Draw(ov)

        name = _pair_name(it['home'], it['away'])
        fn = _fit(name, 'team', 26 * S, 470 * S, min_size=16 * S)
        d.text((248 * S, cy - 23 * S), name, font=fn, fill=(255, 255, 255, 255), anchor='lm')
        fp = _fit(it['pred'], 'pred', 19 * S, 470 * S, min_size=13 * S)
        d.text((248 * S, cy + 20 * S), it['pred'], font=fp, fill=(206, 214, 228, 255), anchor='lm')

        d.text((800 * S, cy - 20 * S), 'НАЧАЛО', font=_fr('label', 12 * S), fill=(160, 168, 184, 255), anchor='mm')
        d.text((800 * S, cy + 12 * S), it['when'], font=_fr('num', 21 * S), fill=(255, 255, 255, 255), anchor='mm')

        if it.get('coef') is not None:
            L, ld = _layer_draw(ov)
            ld.rounded_rectangle((906 * S, cy - 30 * S, 1024 * S, cy + 30 * S), radius=20 * S, fill=ACC + (255,))
            ov.alpha_composite(L)
            d = ImageDraw.Draw(ov)
            _spaced(d, (965 * S, cy - 13 * S), 'КЭФ', _fr('label', 11 * S), (32, 24, 6, 255), 2 * S, anchor='m')
            d.text((965 * S, cy + 12 * S), '%.2f' % it['coef'], font=_fr('num', 23 * S),
                   fill=(16, 14, 4, 255), anchor='mm')

    d.text((WW / 2, (H - 62) * S), 'КОЭФФИЦИЕНТЫ НА МОМЕНТ ПУБЛИКАЦИИ ПРОГНОЗА',
           font=_fr('wide', 12 * S), fill=(190, 198, 212, 255), anchor='mm')
    _spaced(d, (WW / 2, (H - 34) * S), handle, _fr('wide', 17 * S), ACC + (255,), 2 * S, anchor='m')
    return _finish(bg, ov, W, H, path, grain=0.0)
