"""Вёрстка «Бока» (как в баннерах КХЛ) под пост-прогноз: снизу не линия П1/Х/П2, а сам прогноз.

accent=None  — золото, один в один со стилем КХЛ
accent=ICE   — та же сетка, но лига читается по цвету акцента
"""
from PIL import Image, ImageDraw, ImageFilter

import poster
import quality
from poster import (BANNER, SHORT, ACC, _fluid_bg, _canvas_texture, _raw_emblem,
                    _shadowed, _layer_draw, _spaced, _form_row)

ICE = (122, 202, 255)


def render_side_pick(m, path, accent=None, tag='NHL', W=1280, H=640, grain=1.0, seed=None):
    saved = poster.FONTS7
    poster.FONTS7 = dict(saved, **poster.FONTS_SIDE)
    try:
        return _render(m, path, accent or ACC, tag, W, H, grain, seed)
    finally:
        poster.FONTS7 = saved


def _render(m, path, acc, tag, W, H, grain, seed):
    import numpy as np
    S = quality.S
    WW, HH = W * S, H * S
    home, away = m['home'], m['away']
    c1 = BANNER.get(home['team'], (120, 120, 120))
    c2 = BANNER.get(away['team'], (120, 120, 120))
    if seed is None:
        seed = (sum(map(ord, home['team'] + away['team'])) % 997)

    # фон: перелив клубных цветов, затемнения по бокам и снизу, текстура
    bg = _fluid_bg(WW // 2, HH // 2, c1, c2, seed=seed).resize((W, H), Image.LANCZOS)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dim = (0.42 * np.exp(-(((yy / H) - 0.95) ** 2) / 0.02)
           + 0.26 * (np.exp(-(((xx / W) - 0.13) ** 2) / 0.02) + np.exp(-(((xx / W) - 0.87) ** 2) / 0.02))
           * np.exp(-(((yy / H) - 0.55) ** 2) / 0.06))
    shade = Image.new('RGBA', (W, H), (5, 8, 14, 0))
    shade.putalpha(Image.fromarray((np.clip(dim, 0, 1) * 255).astype('uint8'), 'L'))
    bg = Image.alpha_composite(bg.convert('RGBA'), shade).convert('RGB')
    bg = _canvas_texture(bg, grain).convert('RGBA')

    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    eh = int(H * 0.36) * S
    ew = int(W * 0.17) * S

    def needs_plate(team, col):
        e = _raw_emblem(team, 200, 200)
        a = np.asarray(e).astype(np.float32)
        op = a[..., 3] > 128
        if not op.any():
            return False
        mean = a[..., :3][op].mean(axis=0)
        return float(np.sqrt(((mean - np.array(col, np.float32)) ** 2).sum())) < 110

    e1 = _raw_emblem(home['team'], ew, eh, plate=needs_plate(home['team'], c1))
    e2 = _raw_emblem(away['team'], ew, eh, plate=needs_plate(away['team'], c2))
    gap = int(WW * 0.045)
    cy = int(HH * 0.47)
    _shadowed(ov, e1, (int(WW / 2 - gap / 2 - e1.width), cy - e1.height // 2), blur=26, off=(0, 14), color=(0, 0, 0, 120))
    _shadowed(ov, e2, (int(WW / 2 + gap / 2), cy - e2.height // 2), blur=26, off=(0, 14), color=(0, 0, 0, 120))
    d = ImageDraw.Draw(ov)

    # логотип канала
    fb = poster._f7('brand', 26 * S)
    sp, bar = 3 * S, 22 * S
    w1 = sum(fb.getlength(c) for c in 'JARVIS') + sp * 5
    w2 = sum(fb.getlength(c) for c in tag) + sp * (len(tag) - 1)
    x0 = WW / 2 - (w1 + 2 * bar + w2) / 2
    yb = int(58 * S)
    _spaced(d, (x0, yb), 'JARVIS', fb, (255, 255, 255, 255), sp)
    d.rounded_rectangle((x0 + w1 + bar - 1.5 * S, yb - 14 * S, x0 + w1 + bar + 1.5 * S, yb + 14 * S),
                        radius=S, fill=(255, 255, 255, 150))
    _spaced(d, (x0 + w1 + 2 * bar, yb), tag, fb, acc + (255,), sp)

    # блоки команд по бокам — посередине между краем картинки и эмблемой, по высоте — на центре эмблемы
    def team_block(t, emb, side):
        x0, x1 = (64 * S, WW / 2 - gap / 2 - emb.width - 18 * S) if side == 'left' else (WW / 2 + gap / 2 + emb.width + 18 * S, WW - 64 * S)
        x = int((x0 + x1) / 2)
        name = SHORT.get(t['team'], t['name']).upper()
        size = 66 * S
        ft = poster._f7('team', size)
        while ft.getlength(name) > min(318 * S, x1 - x0) and size > 34 * S:
            size -= 2 * S
            ft = poster._f7('team', size)
        y = int(cy - 50 * S)                                   # название, строка и форма — блок высотой 100
        d.text((x, y), name, font=ft, fill=(255, 255, 255, 255), anchor='mm')
        y += int(56 * S)
        d.text((x, y), t['line'], font=poster._f7('info', 22 * S), fill=(232, 236, 242, 255), anchor='mm')
        y += int(44 * S)
        _form_row(d, x, y, t.get('form', '')[-5:], S, align='center')

    team_block(home, e1, 'left')
    team_block(away, e2, 'right')

    # время
    ft = poster._f7('time', 22 * S)
    tw = ft.getlength(m['when'])
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((WW / 2 - tw / 2 - 30 * S, 486 * S, WW / 2 + tw / 2 + 30 * S, 540 * S),
                         radius=27 * S, fill=(8, 12, 20, 200), outline=acc + (220,), width=2 * S)
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    d.text((WW / 2, 513 * S), m['when'], font=ft, fill=(255, 255, 255, 255), anchor='mm')

    # прогноз и коэффициент — на месте строки коэффициентов
    fp = poster._f7('num', 20 * S)
    size = 20 * S
    while fp.getlength(m['pred']) > 560 * S and size > 13 * S:
        size -= 1
        fp = poster._f7('num', size)
    pw = fp.getlength(m['pred']) + 52 * S
    kw = 150 * S
    gp = 12 * S
    xs = WW / 2 - (pw + gp + kw) / 2
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((xs, 558 * S, xs + pw, 604 * S), radius=23 * S,
                         fill=(8, 12, 20, 180), outline=(255, 255, 255, 70), width=2 * S)
    ld.rounded_rectangle((xs + pw + gp, 558 * S, xs + pw + gp + kw, 604 * S), radius=23 * S, fill=acc + (255,))
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    d.text((xs + pw / 2, 581 * S), m['pred'], font=fp, fill=(255, 255, 255, 255), anchor='mm')
    d.text((xs + pw + gp + 40 * S, 581 * S), 'КЭФ', font=poster._f7('info', 14 * S), fill=(24, 20, 8, 255), anchor='mm')
    d.text((xs + pw + gp + 104 * S, 581 * S), '%.2f' % m['coef'], font=poster._f7('num', 22 * S),
           fill=(16, 14, 6, 255), anchor='mm')

    d.text((WW / 2, 624 * S), m.get('foot', 'прогноз канала · коэффициент на момент публикации'),
           font=poster._f7('info', 14 * S), fill=(196, 202, 214, 255), anchor='mm')

    out = quality.compose(bg, ov).convert('RGB')
    out.save(path, optimize=True) if path.lower().endswith('.png') else out.save(path, quality=96, subsampling=0)
    return path
