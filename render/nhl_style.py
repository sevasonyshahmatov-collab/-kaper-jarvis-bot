"""Оформление постов НХЛ — намеренно другое, чем у КХЛ.

КХЛ: мягкий перелив клубных цветов, золото, стеклянные плашки по центру.
НХЛ: жёсткий диагональный раскол, ледяной акцент, нижняя плашка во всю ширину.
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from poster import TEAMS, _raw_emblem, _canvas_texture, _shadowed, _layer_draw, _spaced
from recap import _needs_plate

_FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
FONTS_N = {
    'brand': (_FD + '/Unbounded[wght].ttf', 800),      # шапка канала остаётся общей
    'display': (_FD + '/RussoOne-Regular.ttf', None),  # рубленый блочный — «американский спорт»
    'label': (_FD + '/Oswald[wght].ttf', 500),         # узкий гротеск для подписей
    'label_b': (_FD + '/Oswald[wght].ttf', 700),
}
ICE = (122, 202, 255)        # ледяной акцент вместо золота
ICE_DARK = (8, 26, 40)


def _fn(kind, size):
    p, w = FONTS_N[kind]
    f = ImageFont.truetype(p, int(size))
    if w:
        try:
            f.set_variation_by_axes([w])
        except Exception:
            pass
    return f


def _fit_n(text, kind, size, max_w, min_size=14):
    f = _fn(kind, size)
    while f.getlength(text) > max_w and size > min_size:
        size -= 1
        f = _fn(kind, size)
    return f


def _split_bg(W, H, c_left, c_right, lean=0.10, edge_x=0.54):
    """Диагональный раскол: цвет хозяев слева, гостей справа, светящаяся кромка по стыку."""
    import numpy as np
    x = np.arange(W, dtype=np.float32)[None, :]
    y = np.arange(H, dtype=np.float32)[:, None]
    edge = edge_x * W + ((y / H) - 0.5) * (-lean * W)
    t = np.clip((x - edge) / 2.4 + 0.5, 0, 1)[..., None]

    a = np.array(c_left, np.float32)[None, None, :]
    b = np.array(c_right, np.float32)[None, None, :]
    col = a * (1 - t) + b * t
    # вертикальный градиент: сверху светлее, к низу глубже
    vy = (y / H)[..., None]
    col = col * (1.18 - 0.46 * vy)
    # мягкий свет от центра каждой половины
    for cx, w in ((0.22, 1.0), (0.80, 1.0)):
        r = np.sqrt(((x / W - cx) * 1.6) ** 2 + ((y / H - 0.34) * 1.1) ** 2)[..., None]
        col += 26 * w * np.exp(-(r ** 2) / 0.22)
    # кромка раскола
    glow = np.exp(-((x - edge) ** 2) / (2 * 9.0 ** 2))[..., None]
    col = col * (1 - 0.35 * glow) + np.array(ICE, np.float32)[None, None, :] * glow * 0.85
    img = Image.fromarray(np.clip(col, 0, 255).astype('uint8'), 'RGB').convert('RGBA')

    # росчерки как следы коньков
    streaks = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(streaks)
    for i, (x0, wid, al) in enumerate(((0.06, 2, 20), (0.17, 1, 14), (0.70, 2, 18), (0.88, 1, 12))):
        sd.line((x0 * W + 0.12 * W, -10, x0 * W - 0.10 * W, H + 10), fill=(255, 255, 255, al), width=wid)
    img = Image.alpha_composite(img, streaks.filter(ImageFilter.GaussianBlur(1.2)))
    return img


def _brand_nhl(d, cx, y, S, size=25, league='NHL'):
    fb = _fn('brand', size * S)
    sp = 3 * S
    bar = 22 * S
    w1 = sum(fb.getlength(c) for c in 'JARVIS') + sp * 5
    w2 = sum(fb.getlength(c) for c in league) + sp * (len(league) - 1)
    x0 = cx - (w1 + 2 * bar + w2) / 2
    _spaced(d, (x0, y), 'JARVIS', fb, (255, 255, 255, 255), sp)
    d.rounded_rectangle((x0 + w1 + bar - 1.5 * S, y - 14 * S, x0 + w1 + bar + 1.5 * S, y + 14 * S),
                        radius=S, fill=(255, 255, 255, 150))
    _spaced(d, (x0 + w1 + 2 * bar, y), league, fb, ICE + (255,), sp)


def render_pick_nhl(m, path, handle='@jarvibet', W=1280, H=640, grain=0.9):
    """Прогноз на матч НХЛ: раскол по диагонали, эмблемы по бокам, нижняя плашка с прогнозом."""
    S = 2
    WW, HH = W * S, H * S
    bg = _split_bg(WW, HH, m['home']['color'], m['away']['color']).resize((W, H), Image.LANCZOS)
    bg = _canvas_texture(bg.convert('RGB'), grain).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    _brand_nhl(d, WW / 2, int(52 * S), S, size=25, league=m.get('league_tag', 'NHL'))
    _spaced(d, (WW / 2, 94 * S), m['league'], _fn('label_b', 17 * S), (226, 236, 248, 255), 3 * S, anchor='m')

    # эмблемы
    for side, cx in ((m['home'], 316), (m['away'], 964)):
        if side.get('team') in TEAMS:
            e = _raw_emblem(side['team'], 250 * S, 176 * S, plate=_needs_plate(side['team']))
            _shadowed(ov, e, (int(cx * S - e.width / 2), int(232 * S - e.height / 2)),
                      blur=30, off=(0, 16), color=(0, 0, 0, 150))
    d = ImageDraw.Draw(ov)

    # названия
    for side, cx in ((m['home'], 316), (m['away'], 964)):
        fnm = _fit_n(side['name'], 'display', 42 * S, 520 * S, min_size=26 * S)
        d.text((cx * S, 368 * S), side['name'], font=fnm, fill=(255, 255, 255, 255), anchor='mm')
        _spaced(d, (cx * S, 404 * S), side['sub'], _fn('label', 16 * S), (206, 220, 236, 255), 3 * S, anchor='m')

    if m.get('note'):
        _spaced(d, (WW / 2, 440 * S), m['note'], _fn('label', 14 * S), (198, 212, 230, 255), 2 * S, anchor='m')

    # нижняя плашка во всю ширину: время · прогноз · коэффициент
    y1, y2 = 472 * S, 566 * S
    L, ld = _layer_draw(ov)
    ld.rectangle((0, y1, WW, y2), fill=(6, 11, 18, 224))
    ld.rectangle((0, y1, WW, y1 + 3 * S), fill=ICE + (230,))
    ld.rectangle((940 * S, y1 + 3 * S, WW, y2), fill=ICE + (255,))
    for xd in (340 * S,):
        ld.line((xd, y1 + 20 * S, xd, y2 - 20 * S), fill=(255, 255, 255, 46), width=2 * S)
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)

    cy = (y1 + y2) / 2
    _spaced(d, (44 * S, cy - 15 * S), 'НАЧАЛО', _fn('label', 13 * S), (150, 176, 200, 255), 2.4 * S)
    d.text((44 * S, cy + 16 * S), m['when'], font=_fn('display', 21 * S), fill=(255, 255, 255, 255), anchor='lm')

    _spaced(d, (376 * S, cy - 15 * S), 'ПРОГНОЗ', _fn('label', 13 * S), (150, 176, 200, 255), 2.4 * S)
    fp = _fit_n(m['pred'], 'display', 26 * S, 548 * S, min_size=16 * S)
    d.text((376 * S, cy + 17 * S), m['pred'], font=fp, fill=(255, 255, 255, 255), anchor='lm')

    _spaced(d, (990 * S, cy - 15 * S), 'КЭФ', _fn('label_b', 13 * S), ICE_DARK + (255,), 2.4 * S)
    d.text((990 * S, cy + 18 * S), '%.2f' % m['coef'], font=_fn('display', 34 * S), fill=(6, 20, 32, 255), anchor='lm')

    _spaced(d, (WW / 2, 596 * S), m.get('foot', 'ПРОГНОЗ КАНАЛА · КОЭФФИЦИЕНТ НА МОМЕНТ ПУБЛИКАЦИИ'),
            _fn('label', 13 * S), (196, 210, 226, 255), 2 * S, anchor='m')
    if handle:
        _spaced(d, (WW / 2, 622 * S), handle, _fn('label_b', 14 * S), ICE + (255,), 2.4 * S, anchor='m')

    ov = ov.resize((W, H), Image.LANCZOS)
    out = Image.alpha_composite(bg, ov).convert('RGB')
    out = out.filter(ImageFilter.UnsharpMask(radius=1.0, percent=45, threshold=2))
    out.save(path, optimize=True) if path.lower().endswith('.png') else out.save(path, quality=96, subsampling=0)
    return path
