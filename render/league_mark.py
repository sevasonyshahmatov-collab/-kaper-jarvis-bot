"""Логотип лиги на фоне баннера: крупно, размыто и полупрозрачно, чтобы не мешал читать.

Логотипы лежат в league/: khl.png и nhl.png (PNG с прозрачным фоном).
Нет файла — баннер рисуется как раньше, без логотипа.

    import league_mark
    with league_mark.on('KHL'):
        recap.render_results_day(...)

Работает поверх recap._base, ни poster.py, ни recap.py не меняет.
"""
import os
from contextlib import contextmanager

from PIL import Image, ImageEnhance, ImageFilter

import recap

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = {'KHL': 'khl.png', 'NHL': 'nhl.png'}

OPACITY = 0.13     # насколько логотип виден: 0 — нет, 1 — как есть
BLUR = 7           # размытие, px на итоговом размере
DESAT = 0.35       # насыщенность: 1 — родные цвета, 0 — серый
MAX_W = 0.74       # доля ширины баннера
MAX_H = 0.70       # доля высоты баннера


def path_for(league):
    return os.path.join(HERE, 'league', FILES.get(league.upper(), league.lower() + '.png'))


def apply(bg, logo_path, opacity=OPACITY, blur=BLUR, desat=DESAT):
    """Кладёт размытый полупрозрачный логотип в центр фона (RGBA того же размера)."""
    if not logo_path or not os.path.exists(logo_path):
        return bg
    W, H = bg.size
    logo = Image.open(logo_path).convert('RGBA')
    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)
    k = min(W * MAX_W / logo.width, H * MAX_H / logo.height)
    logo = logo.resize((max(1, int(logo.width * k)), max(1, int(logo.height * k))), Image.LANCZOS)
    rgb = ImageEnhance.Color(logo.convert('RGB')).enhance(desat)
    alpha = logo.getchannel('A').point(lambda a: int(a * opacity))
    logo = Image.merge('RGBA', (*rgb.split(), alpha))
    pad = blur * 3                     # поля, чтобы размытие не обрезалось по краю картинки
    layer = Image.new('RGBA', (logo.width + 2 * pad, logo.height + 2 * pad), (0, 0, 0, 0))
    layer.paste(logo, (pad, pad))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    out = bg.copy()
    out.alpha_composite(layer, ((W - layer.width) // 2, (H - layer.height) // 2 + int(H * 0.04)))
    return out


@contextmanager
def on(league, **kw):
    """Пока контекст открыт, фон любого баннера recap получает логотип лиги."""
    orig = recap._base
    logo = path_for(league)

    def base(W, H, S, *a, **k):
        return apply(orig(W, H, S, *a, **k), logo, **kw)

    recap._base = base
    try:
        yield
    finally:
        recap._base = orig
