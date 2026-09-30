"""Фоны-«ткань» для новых постеров (итоги и матчи дня): перелив как у шёлка (poster._fluid_bg)
и неровная текстура холста с диагональными нитями (poster._canvas_texture) — как на баннерах «Бока».

    import bg_silk
    with bg_silk.use('silver'):
        results_ice2.render(...)        # и любые другие форматы «Лёд»: results_ice3, results_styles2 (ice*), preview_ice

mode:
  'ice'      — светлый лёд, как было, но с переливом и текстурой ткани; иней сверху
  'silver'   — серебро → графит (как у «Тампа-Бэй»)
  'league'   — цвета лиги: КХЛ кремово-золотой → стальной; НХЛ серебро → ледяной голубой
  'twilight' — светлый верх под заголовком, глубокий тёмно-синий шёлк под матчами, светлый низ под подписью
"""
from contextlib import contextmanager

import numpy as np
from PIL import Image

import poster
import results_styles as rs
import results_styles2 as rs2
import results_ice2
import results_ice3
import preview_ice

W = rs.W
TEXTURE = 1.1          # сила «ткани» на фоне
GRAIN = 0.3            # лёгкое зерно поверх всей картинки, чтобы плашки не выглядели наклейкой на ткани

PAIRS = {
    'ice': ((240, 246, 252), (192, 212, 236)),
    'silver': ((236, 238, 242), (148, 158, 176)),
    'league_KHL': ((246, 232, 198), (178, 198, 226)),
    'league_NHL': ((234, 238, 244), (146, 190, 232)),
    'dark': ((30, 50, 92), (10, 18, 38)),
}


def _silk(H, c1, c2, seed):
    bg = poster._fluid_bg(W // 2, H // 2, c1, c2, seed=seed).resize((W, H), Image.LANCZOS)
    return poster._canvas_texture(bg.convert('RGB'), TEXTURE).convert('RGBA')


def _smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def background(mode, H, league):
    if mode == 'twilight':
        light = np.asarray(_silk(H, *PAIRS['ice'], seed=31), np.float32)
        dark = np.asarray(_silk(H, *PAIRS['dark'], seed=32), np.float32)
        y = np.arange(H, dtype=np.float32)[:, None, None]
        m = _smooth(y, 230, 400) * (1 - _smooth(y, H - 150, H - 70))
        bg = Image.fromarray((light * (1 - m) + dark * m).astype(np.uint8), 'RGBA')
    else:
        key = 'league_' + league if mode == 'league' else mode
        bg = _silk(H, *PAIRS[key], seed={'ice': 21, 'silver': 7, 'league_KHL': 13, 'league_NHL': 13}[key])
    bg = rs._watermark(bg, league, results_ice2.NAVY, 0.07)
    return results_ice2._frost_top(bg) if mode == 'ice' else bg


@contextmanager
def use(mode):
    bgf = lambda H, league: background(mode, H, league)
    saved = (results_ice2._background, results_ice3._background, preview_ice._background, preview_ice._bg_plain, rs2.ICE_BG, rs._finish)
    orig_finish = rs._finish

    def finish(bg, ov, H, path, grain):
        return orig_finish(bg, ov, H, path, GRAIN)

    results_ice2._background = results_ice3._background = preview_ice._background = preview_ice._bg_plain = bgf
    rs2.ICE_BG = bgf
    rs._finish = finish
    try:
        yield
    finally:
        (results_ice2._background, results_ice3._background, preview_ice._background, preview_ice._bg_plain, rs2.ICE_BG, rs._finish) = saved
