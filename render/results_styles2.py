"""«Итоги дня» — ещё пять форматов, у каждого свой шрифт и фон.

    import results_styles2 as rs2
    rs2.render(items, path, style='arena', league='KHL', date_title='...')

style:
  'arena'   — АРЕНА: строка в клубных цветах хозяев и гостей, счёт в чёрном табло. Oswald.
  'digital' — ЦИФРОВОЕ ТАБЛО: чёрный фон с сеткой, светящиеся цифры. Tektur.
  'gazeta'  — СПОРТ-ЭКСПРЕСС: косая плашка заголовка, счёт в косом блоке. Russo One + Golos.
  'minimal' — МИНИМАЛИЗМ: без карточек, команды столбиком, глубокий цвет фона. Unbounded + Onest.
  'ice'     — ЛЁД: светлый фон с разметкой площадки, красные цифры победителя. Exo 2 Italic.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import poster
import recap
import results_styles as rs

S, W = rs.S, rs.W


# ------------------------------------------------------------------ шрифты
def F(file, size, wght=None, wdth=None):
    f = ImageFont.truetype(os.path.join(recap._FD, file), int(size))
    try:
        axes = f.get_variation_axes()
        vals = []
        for a in axes:
            name = a.get('name', b'')
            name = name.decode() if isinstance(name, bytes) else str(name)
            if name.lower().startswith('weight') and wght:
                vals.append(wght)
            elif name.lower().startswith('width') and wdth:
                vals.append(wdth)
            else:
                vals.append(a.get('default'))
        if axes:
            f.set_variation_by_axes(vals)
    except Exception:
        pass
    return f


def fit(text, file, size, max_w, wght=None, wdth=None, min_size=12):
    f = F(file, size, wght, wdth)
    while f.getlength(text) > max_w and size > min_size:
        size -= 1
        f = F(file, size, wght, wdth)
    return f


OSW, TEK, RUSSO, GOLOS = 'Oswald[wght].ttf', 'Tektur[wdth,wght].ttf', 'RussoOne-Regular.ttf', 'GolosText[wght].ttf'
UNB, ONEST, EXOI = 'Unbounded[wght].ttf', 'Onest[wght].ttf', 'Exo2-Italic[wght].ttf'


def spaced(d, xy, text, font, fill, sp, anchor='m'):
    poster._spaced(d, xy, text, font, fill, sp, anchor=anchor)


def club(team):
    c = poster.BANNER.get(team)
    return tuple(c[:3]) if c else (60, 70, 90)


def _layered(bg, draw):
    """Рисует на прозрачном слое и накладывает на фон: полупрозрачные линии смешиваются, а не заменяют пиксели."""
    layer = Image.new('RGBA', bg.size, (0, 0, 0, 0))
    draw(ImageDraw.Draw(layer))
    return Image.alpha_composite(bg, layer)


def _canvas(H):
    return Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))


# ------------------------------------------------------------------ 1. АРЕНА (Oswald)
def _arena(items, path, league, title, date_title):
    ROW, gap, head, foot = 132, 14, 262, 96
    H = head + len(items) * (ROW + gap) - gap + foot
    acc = rs.ACCENT[league]
    bg = rs._gradient(W, H, (14, 15, 20), (6, 7, 10), glow=acc + (30,), glow_xy=(0.5, -0.1))
    bg = rs._watermark(bg, league, None, 0.10)
    ov = _canvas(H)
    d = ImageDraw.Draw(ov)
    rs._brand(d, W * S / 2, 58 * S, league)
    spaced(d, (W * S / 2, 138 * S), title, F(OSW, 78 * S, 700), (255, 255, 255, 255), 6 * S)
    if date_title:
        spaced(d, (W * S / 2, 206 * S), date_title.upper(), F(OSW, 22 * S, 400), (190, 196, 210, 255), 4 * S)
    for i, it in enumerate(items):
        y0 = head + i * (ROW + gap)
        home_win = it['sh'] > it['sa']
        # полосы клубных цветов: от краёв к центру гаснут в чёрное
        band = np.zeros((ROW * S, (W - 64) * S, 4), np.float32)
        xs = np.linspace(0, 1, band.shape[1], dtype=np.float32)
        for col, mask, won in ((club(it['home']), np.clip(1 - xs * 2.1, 0, 1), home_win),
                               (club(it['away']), np.clip(xs * 2.1 - 1.1, 0, 1), not home_win)):
            k = mask[None, :, None] * (0.95 if won else 0.45)
            band[..., :3] += np.array(col, np.float32) * k
            band[..., 3:] = np.maximum(band[..., 3:], k * 255)
        band[..., 3] = np.maximum(band[..., 3], 150)
        bim = Image.fromarray(band.clip(0, 255).astype(np.uint8), 'RGBA')
        m = Image.new('L', bim.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, bim.width - 1, bim.height - 1), radius=18 * S, fill=255)
        bim.putalpha(Image.fromarray(np.minimum(np.asarray(bim.getchannel('A')), np.asarray(m))))
        ov.alpha_composite(bim, (32 * S, y0 * S))
        cy = (y0 + ROW / 2) * S
        rs._emblem(ov, it['home'], 100 * S, cy, 86)
        rs._emblem(ov, it['away'], (W - 100) * S, cy, 86)
        d = ImageDraw.Draw(ov)
        for team, x, anchor, won in ((it['home'], 160, 'lm', home_win), (it['away'], W - 160, 'rm', not home_win)):
            name = rs._short(team)
            d.text((x * S, cy), name, font=fit(name, OSW, 40 * S, 230 * S, 700), anchor=anchor,
                   fill=(255, 255, 255, 255) if won else (255, 255, 255, 150))
        # табло счёта
        bw, bh = 196, 92
        d.rounded_rectangle(((W / 2 - bw / 2) * S, cy - bh / 2 * S, (W / 2 + bw / 2) * S, cy + bh / 2 * S),
                            radius=14 * S, fill=(6, 7, 10, 245), outline=acc + (255,), width=3 * S)
        fn = F(OSW, 70 * S, 700)
        d.text(((W / 2 - 14) * S, cy - 4 * S), str(it['sh']), font=fn, anchor='rm', fill=acc + (255,) if home_win else (255, 255, 255, 170))
        d.text((W / 2 * S, cy - 8 * S), '–', font=F(OSW, 54 * S, 500), anchor='mm', fill=(255, 255, 255, 120))
        d.text(((W / 2 + 14) * S, cy - 4 * S), str(it['sa']), font=fn, anchor='lm', fill=acc + (255,) if not home_win else (255, 255, 255, 170))
        if it.get('mark'):
            t = rs.MARK_TEXT[it['mark']]
            f = F(OSW, 15 * S, 600)
            w = f.getlength(t) + 18 * S
            d.rounded_rectangle((W / 2 * S - w / 2, cy + 38 * S, W / 2 * S + w / 2, cy + 60 * S), radius=5 * S, fill=acc + (255,))
            d.text((W / 2 * S, cy + 49 * S), t, font=f, anchor='mm', fill=(10, 10, 12, 255))
    spaced(d, (W * S / 2, (H - 42) * S), '@jarvibet', F(OSW, 22 * S, 500), acc + (255,), 3 * S)
    return rs._finish(bg, ov, H, path, grain=0.45)


# ------------------------------------------------------------------ 2. ЦИФРОВОЕ ТАБЛО (Tektur)
def _digital(items, path, league, title, date_title):
    ROW, gap, head, foot = 128, 12, 250, 96
    H = head + len(items) * (ROW + gap) - gap + foot
    acc = rs.ACCENT[league]
    bg = rs._gradient(W, H, (6, 8, 12), (2, 3, 5))
    def grid(g):                                   # тонкая сетка табло
        for x in range(0, W, 24):
            g.line(((x, 0), (x, H)), fill=(255, 255, 255, 10))
        for y in range(0, H, 24):
            g.line(((0, y), (W, y)), fill=(255, 255, 255, 10))
    bg = _layered(bg, grid)
    bg = rs._watermark(bg, league, None, 0.08)
    ov = _canvas(H)
    glow = _canvas(H)
    d, gd = ImageDraw.Draw(ov), ImageDraw.Draw(glow)
    rs._brand(d, W * S / 2, 58 * S, league)
    for dd, a in ((gd, 180), (d, 255)):
        dd.text((W * S / 2, 132 * S), title, font=F(TEK, 64 * S, 800, 110), anchor='mm', fill=acc + (a,))
    if date_title:
        d.text((W * S / 2, 196 * S), date_title.upper(), font=F(TEK, 20 * S, 500, 100), anchor='mm', fill=(170, 180, 196, 255))
    for i, it in enumerate(items):
        y0 = head + i * (ROW + gap)
        cy = (y0 + ROW / 2) * S
        home_win = it['sh'] > it['sa']
        d.rectangle((32 * S, y0 * S, (W - 32) * S, (y0 + ROW) * S), fill=(255, 255, 255, 8), outline=(255, 255, 255, 36), width=2 * S)
        for x in (32, W - 32 - 14):              # уголки-«скобы» табло
            d.rectangle((x * S, y0 * S, (x + 14) * S, (y0 + 4) * S), fill=acc + (255,))
            d.rectangle((x * S, (y0 + ROW - 4) * S, (x + 14) * S, (y0 + ROW) * S), fill=acc + (255,))
        rs._emblem(ov, it['home'], 96 * S, cy, 74)
        rs._emblem(ov, it['away'], (W - 96) * S, cy, 74)
        d = ImageDraw.Draw(ov)
        for team, x, anchor, won in ((it['home'], 148, 'lm', home_win), (it['away'], W - 148, 'rm', not home_win)):
            name = rs._short(team)
            d.text((x * S, cy), name, font=fit(name, TEK, 28 * S, 250 * S, 700, 90), anchor=anchor,
                   fill=(235, 240, 248, 255) if won else (120, 128, 142, 255))
        fn = F(TEK, 76 * S, 800, 100)
        for dd, a in ((gd, 200), (d, 255)):
            dd.text(((W / 2 - 18) * S, cy), str(it['sh']), font=fn, anchor='rm', fill=(acc if home_win else (150, 156, 168)) + (a if home_win or dd is d else 0,))
            dd.text(((W / 2 + 18) * S, cy), str(it['sa']), font=fn, anchor='lm', fill=(acc if not home_win else (150, 156, 168)) + (a if not home_win or dd is d else 0,))
        d.text((W / 2 * S, cy - 6 * S), ':', font=F(TEK, 56 * S, 700, 100), anchor='mm', fill=(150, 156, 168, 255))
        if it.get('mark'):
            d.text((W / 2 * S, cy + 46 * S), '[ ' + rs.MARK_TEXT[it['mark']] + ' ]', font=F(TEK, 14 * S, 600, 110), anchor='mm', fill=acc + (255,))
    d.text((W * S / 2, (H - 42) * S), '@jarvibet', font=F(TEK, 22 * S, 600, 110), anchor='mm', fill=acc + (255,))
    ov = Image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14 * S)), ov)
    return rs._finish(bg, ov, H, path, grain=0.3)


# ------------------------------------------------------------------ 3. СПОРТ-ГАЗЕТА (Russo One + Golos)
def _gazeta(items, path, league, title, date_title):
    ROW, gap, head, foot = 126, 16, 272, 96
    H = head + len(items) * (ROW + gap) - gap + foot
    acc = rs.ACCENT[league]
    bg = rs._gradient(W, H, (26, 30, 40), (13, 15, 21))
    def hatch(g):                                  # косая штриховка
        for x in range(-H, W, 34):
            g.line(((x, H), (x + H, 0)), fill=(255, 255, 255, 9), width=10)
    bg = _layered(bg, hatch)
    bg = rs._watermark(bg, league, None, 0.10)
    ov = _canvas(H)
    d = ImageDraw.Draw(ov)
    rs._brand(d, W * S / 2, 56 * S, league)
    tf = F(RUSSO, 62 * S)
    tw = tf.getlength(title)
    cx, ty, sk = W * S / 2, 142 * S, 26 * S
    d.polygon([(cx - tw / 2 - 40 * S + sk, ty - 46 * S), (cx + tw / 2 + 40 * S + sk, ty - 46 * S),
               (cx + tw / 2 + 40 * S - sk, ty + 46 * S), (cx - tw / 2 - 40 * S - sk, ty + 46 * S)], fill=acc + (255,))
    d.text((cx, ty + 2 * S), title, font=tf, anchor='mm', fill=(14, 16, 22, 255))
    if date_title:
        spaced(d, (cx, 226 * S), date_title.upper(), F(GOLOS, 20 * S, 700), (205, 210, 222, 255), 3 * S)
    for i, it in enumerate(items):
        y0 = head + i * (ROW + gap)
        cy = (y0 + ROW / 2) * S
        home_win = it['sh'] > it['sa']
        d.rounded_rectangle((32 * S, y0 * S, (W - 32) * S, (y0 + ROW) * S), radius=10 * S, fill=(255, 255, 255, 16))
        d.rectangle((32 * S, y0 * S, 40 * S, (y0 + ROW) * S), fill=(acc if home_win else (90, 96, 110)) + (255,))
        d.rectangle(((W - 40) * S, y0 * S, (W - 32) * S, (y0 + ROW) * S), fill=(acc if not home_win else (90, 96, 110)) + (255,))
        rs._emblem(ov, it['home'], 100 * S, cy, 80)
        rs._emblem(ov, it['away'], (W - 100) * S, cy, 80)
        d = ImageDraw.Draw(ov)
        for team, x, anchor, won in ((it['home'], 152, 'lm', home_win), (it['away'], W - 152, 'rm', not home_win)):
            name = rs._short(team)
            d.text((x * S, cy), name, font=fit(name, GOLOS, 30 * S, 230 * S, 900), anchor=anchor,
                   fill=(255, 255, 255, 255) if won else (160, 166, 180, 255))
        # косой блок счёта
        bw, bh, sk = 190, 78, 16
        x1, x2 = (W / 2 - bw / 2) * S, (W / 2 + bw / 2) * S
        d.polygon([(x1 + sk * S, cy - bh / 2 * S), (x2 + sk * S, cy - bh / 2 * S), (x2 - sk * S, cy + bh / 2 * S), (x1 - sk * S, cy + bh / 2 * S)],
                  fill=(250, 250, 252, 255))
        fn = F(RUSSO, 58 * S)
        d.text(((W / 2 - 16) * S, cy + 2 * S), str(it['sh']), font=fn, anchor='rm', fill=(14, 16, 22, 255) if home_win else (150, 156, 168, 255))
        d.text((W / 2 * S, cy), ':', font=F(RUSSO, 46 * S), anchor='mm', fill=(150, 156, 168, 255))
        d.text(((W / 2 + 16) * S, cy + 2 * S), str(it['sa']), font=fn, anchor='lm', fill=(14, 16, 22, 255) if not home_win else (150, 156, 168, 255))
        if it.get('mark'):
            t = rs.MARK_TEXT[it['mark']]
            f = F(GOLOS, 14 * S, 800)
            w = f.getlength(t) + 18 * S
            d.rectangle((W / 2 * S - w / 2, cy + 42 * S, W / 2 * S + w / 2, cy + 62 * S), fill=acc + (255,))
            d.text((W / 2 * S, cy + 52 * S), t, font=f, anchor='mm', fill=(14, 16, 22, 255))
    spaced(d, (W * S / 2, (H - 42) * S), '@jarvibet', F(RUSSO, 22 * S), acc + (255,), 3 * S)
    return rs._finish(bg, ov, H, path, grain=0.5)


# ------------------------------------------------------------------ 4. МИНИМАЛИЗМ (Unbounded + Onest)
def _minimal(items, path, league, title, date_title):
    ROW, head, foot = 168, 250, 100
    H = head + len(items) * ROW + foot
    acc = rs.ACCENT[league]
    top, bottom = ((46, 16, 58), (16, 8, 24)) if league == 'KHL' else ((8, 52, 60), (4, 20, 26))
    bg = rs._gradient(W, H, top, bottom, glow=acc + (26,), glow_xy=(0.9, 0.0), glow_r=0.7)
    bg = rs._watermark(bg, league, None, 0.09)
    ov = _canvas(H)
    d = ImageDraw.Draw(ov)
    rs._brand(d, 64 * S + 170 * S, 64 * S, league)          # шапка слева
    d.text((64 * S, 140 * S), title, font=F(UNB, 56 * S, 800), anchor='lm', fill=(255, 255, 255, 255))
    if date_title:
        d.text((66 * S, 196 * S), date_title, font=F(ONEST, 24 * S, 500), anchor='lm', fill=(210, 214, 226, 200))
    for i, it in enumerate(items):
        y0 = head + i * ROW
        home_win = it['sh'] > it['sa']
        d.line(((64 * S, y0 * S), ((W - 64) * S, y0 * S)), fill=(255, 255, 255, 40), width=2 * S)
        for k, (team, val, won) in enumerate(((it['home'], it['sh'], home_win), (it['away'], it['sa'], not home_win))):
            cy = (y0 + 46 + k * 74) * S
            rs._emblem(ov, team, 94 * S, cy, 58)
            d = ImageDraw.Draw(ov)
            name = poster.SHORT.get(team, team)
            d.text((142 * S, cy), name, font=fit(name, ONEST, 34 * S, 600 * S, 700 if won else 500), anchor='lm',
                   fill=(255, 255, 255, 255) if won else (255, 255, 255, 115))
            d.text(((W - 64) * S, cy), str(val), font=F(UNB, 50 * S, 800), anchor='rm',
                   fill=acc + (255,) if won else (255, 255, 255, 110))
        if it.get('mark'):
            d.text(((W - 150) * S, (y0 + 83) * S), rs.MARK_TEXT[it['mark']].lower(), font=F(ONEST, 18 * S, 600), anchor='rm', fill=acc + (230,))
    d.line(((64 * S, (head + len(items) * ROW) * S), ((W - 64) * S, (head + len(items) * ROW) * S)), fill=(255, 255, 255, 40), width=2 * S)
    d.text((64 * S, (H - 44) * S), '@jarvibet', font=F(UNB, 20 * S, 600), anchor='lm', fill=acc + (255,))
    return rs._finish(bg, ov, H, path, grain=0.35)


# ------------------------------------------------------------------ 5. ЛЁД (Exo 2 Italic)
def _ice(items, path, league, title, date_title, frost=False, colored=False, logos=False, over=False):
    ROW, gap, head, foot = 128, 16, 262, 96
    H = head + len(items) * (ROW + gap) - gap + foot
    red, navy = (214, 40, 57), (16, 34, 70)
    bg = rs._gradient(W, H, (236, 244, 251), (205, 224, 240), glow=(255, 255, 255, 120), glow_xy=(0.3, 0.1), glow_r=0.6)
    def rink(g):                                     # разметка площадки
        g.line(((0, H * 0.52), (W, H * 0.52)), fill=(214, 40, 57, 70), width=10)
        for y in (H * 0.30, H * 0.74):
            g.line(((0, y), (W, y)), fill=(40, 90, 200, 55), width=10)
        g.ellipse((W / 2 - 150, H * 0.52 - 150, W / 2 + 150, H * 0.52 + 150), outline=(40, 90, 200, 55), width=5)
    bg = _layered(bg, rink)
    bg = rs._watermark(bg, league, (16, 34, 70), 0.06)
    ov = _canvas(H)
    d = ImageDraw.Draw(ov)
    rs._brand(d, W * S / 2, 58 * S, league, dark_text=True)
    d.text((W * S / 2, 136 * S), title, font=F(EXOI, 76 * S, 900), anchor='mm', fill=navy + (255,))
    if date_title:
        spaced(d, (W * S / 2, 204 * S), date_title.upper(), F(EXOI, 22 * S, 600), (70, 90, 120, 255), 3 * S)
    for i, it in enumerate(items):
        y0 = head + i * (ROW + gap)
        cy = (y0 + ROW / 2) * S
        home_win = it['sh'] > it['sa']
        card = _team_plate(it['home'], it['away'], (W - 64) * S, ROW * S, 22 * S, logos and not over) if colored else Image.new('RGBA', ((W - 64) * S, ROW * S), (0, 0, 0, 0))
        if not colored:
            ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius=22 * S, fill=(255, 255, 255, 215))
        poster._shadowed(ov, card, (32 * S, y0 * S), blur=12 * S, off=(0, 5 * S), color=(30, 60, 110, 70 if colored else 55))
        nx = 196 if over else 72 if logos else 152  # внутри плашки — название у края; поверх — за логотипом
        if over:                                    # эмблема поверх плашки: там же, где «вплавленная», но в цвете, с обводкой-наклейкой и тенью
            for team, cx0, ang in ((it['home'], 32 + ROW * 0.60, 10), (it['away'], W - 32 - ROW * 0.60, -10)):
                e = _sticker(poster._raw_emblem(team, int(ROW * 1.0 * S), int(ROW * 1.0 * S)), 5 * S).rotate(ang, Image.BICUBIC, expand=True)
                poster._shadowed(ov, e, (int(cx0 * S - e.width / 2), int(cy - e.height / 2)), blur=10 * S, off=(0, 6 * S), color=(0, 0, 0, 120))
        elif not logos:
            rs._emblem(ov, it['home'], 100 * S, cy, 80)
            rs._emblem(ov, it['away'], (W - 100) * S, cy, 80)
        d = ImageDraw.Draw(ov)
        for team, x, anchor, won in ((it['home'], nx, 'lm', home_win), (it['away'], W - nx, 'rm', not home_win)):
            name = rs._short(team)
            f = fit(name, EXOI, 34 * S if over else 36 * S if logos else 34 * S, 200 * S if over else 300 * S if logos else 230 * S, 800)
            if colored:                               # белым по клубному цвету, с лёгкой тенью
                d.text((x * S, cy + 2 * S), name, font=f, anchor=anchor, fill=(0, 0, 0, 90))
                d.text((x * S, cy), name, font=f, anchor=anchor, fill=(255, 255, 255, 255 if won else 175))
            else:
                d.text((x * S, cy), name, font=f, anchor=anchor, fill=navy + (255,) if won else (140, 152, 172, 255))
        # «шайбы» со счётом
        for k, (val, won) in enumerate(((it['sh'], home_win), (it['sa'], not home_win))):
            px = (W / 2 + (-52 if k == 0 else 52)) * S
            r = 44 * S
            d.ellipse((px - r, cy - r, px + r, cy + r), fill=(18, 20, 26, 255) if won else (226, 232, 240, 255))
            d.text((px, cy - 2 * S), str(val), font=F(EXOI, 52 * S, 900), anchor='mm', fill=(255, 255, 255, 255) if won else (120, 130, 148, 255))
        if it.get('mark'):                          # под названием победителя, между шайбами места нет
            x, anchor = (nx, 'lm') if home_win else (W - nx, 'rm')
            t, f = rs.MARK_TEXT[it['mark']], F(EXOI, 16 * S, 800)
            if colored:                               # на клубном цвете красный текст теряется — белый на тёмной плашке
                w = f.getlength(t) + 16 * S
                x1 = x * S if anchor == 'lm' else x * S - w
                d.rounded_rectangle((x1, cy + 24 * S, x1 + w, cy + 46 * S), radius=8 * S, fill=(12, 16, 26, 200))
                d.text((x1 + w / 2, cy + 35 * S), t, font=f, anchor='mm', fill=(255, 255, 255, 255))
            else:
                d.text((x * S, cy + 34 * S), t, font=f, anchor=anchor, fill=red + (255,))
    if not frost:
        spaced(d, (W * S / 2, (H - 42) * S), '@jarvibet', F(EXOI, 24 * S, 800), red + (255,), 2 * S)
        return rs._finish(bg, ov, H, path, grain=0.2)
    out = _frost(Image.alpha_composite(bg, ov.resize((W, H), Image.LANCZOS)))
    # подпись — поверх инея, с мягкой светлой подложкой, иначе тонет
    tag = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    td = ImageDraw.Draw(tag)
    f = F(EXOI, 24 * S, 800)
    spaced(td, (W * S / 2, (H - 42) * S), '@jarvibet', f, (255, 255, 255, 255), 2 * S)
    halo = tag.filter(ImageFilter.GaussianBlur(10 * S))
    spaced(td, (W * S / 2, (H - 42) * S), '@jarvibet', f, red + (255,), 2 * S)
    out = Image.alpha_composite(out, Image.alpha_composite(halo, halo).resize((W, H), Image.LANCZOS))
    out = Image.alpha_composite(out, tag.resize((W, H), Image.LANCZOS))
    out = out.convert('RGB').filter(ImageFilter.UnsharpMask(radius=1.0, percent=40, threshold=2))
    out = poster._canvas_texture(out, 0.2)
    out.save(path, quality=95, subsampling=0, optimize=True)
    return path


def _sticker(e, border):
    """Белая обводка по контуру эмблемы, как у наклейки: отделяет тёмный логотип от фона того же цвета."""
    pad = border + 2
    big = Image.new('RGBA', (e.width + 2 * pad, e.height + 2 * pad), (0, 0, 0, 0))
    big.paste(e, (pad, pad))
    a = big.getchannel('A').point(lambda v: 255 if v > 60 else 0).filter(ImageFilter.MaxFilter(2 * (border // 2) + 1))
    for _ in range(max(0, border // 6)):
        a = a.filter(ImageFilter.MaxFilter(5))
    a = a.filter(ImageFilter.GaussianBlur(1))
    out = Image.new('RGBA', big.size, (255, 255, 255, 0))
    out.putalpha(a)
    return Image.alpha_composite(out, big)


def _team_plate(home, away, w, h, radius, logos=False):
    """Плашка матча: слева цвет хозяев, справа цвет гостей, плавный переход в центре и «ледяной» блик сверху.
    logos — эмблемы клубов «вплавлены» в плашку: крупно, срезаны краем, тон-в-тон с цветом клуба."""
    xs = np.linspace(0, 1, w, dtype=np.float32)
    k = np.clip((xs - 0.40) / 0.20, 0, 1)[None, :, None]          # переход в центральной пятой части
    a = np.array(club(home), np.float32) * (1 - k) + np.array(club(away), np.float32) * k
    a = np.repeat(a, h, axis=0)
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    a = a * (0.82 + 0.18 * (1 - ys))                                 # чуть темнее книзу
    if logos:
        for team, cx, ang in ((home, h * 0.66, 10), (away, w - h * 0.66, -10)):
            e = poster._raw_emblem(team, int(h * 1.55), int(h * 1.55)).rotate(ang, Image.BICUBIC, expand=True)
            gray = np.asarray(e.convert('L'), np.float32) / 255
            al = np.asarray(e.getchannel('A'), np.float32) / 255 * 0.72
            x0, y0 = int(cx - e.width / 2), int(h * 0.52 - e.height / 2)
            xa, ya, xb, yb = max(0, x0), max(0, y0), min(w, x0 + e.width), min(h, y0 + e.height)
            g = gray[ya - y0:yb - y0, xa - x0:xb - x0, None]
            k = al[ya - y0:yb - y0, xa - x0:xb - x0, None]
            # тон-в-тон: светлые части эмблемы осветляют цвет клуба, тёмные — затемняют
            a[ya:yb, xa:xb] = a[ya:yb, xa:xb] * (1 - k) + a[ya:yb, xa:xb] * (0.55 + 0.85 * g) * k
    a = a + (255 - a) * np.clip(0.22 - ys * 0.5, 0, 1)               # блик сверху
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=242)
    img.putalpha(m)
    ImageDraw.Draw(img).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, outline=(255, 255, 255, 150), width=max(2, h // 60))
    return img


def _noise(W, H, rng, scales=((6, 0.45), (14, 0.25), (34, 0.18), (80, 0.12))):
    """Фрактальный шум 0..1 — неровная граница инея."""
    n = np.zeros((H, W), np.float32)
    for sc, amp in scales:
        g = (rng.random((H // sc + 3, W // sc + 3)) * 255).astype(np.uint8)
        n += np.asarray(Image.fromarray(g).resize((W + 3 * sc, H + 3 * sc), Image.BICUBIC), np.float32)[:H, :W] / 255 * amp
    return (n - n.min()) / (n.max() - n.min() + 1e-6)


def _frost(img, reach=140, seed=11):
    """Иней по краям: неровная морозная кромка, узоры-«папоротники» и блёстки."""
    import math
    W_, H_ = img.size
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
    dist = np.minimum(np.minimum(xx, W_ - 1 - xx), np.minimum(yy, H_ - 1 - yy))
    n = _noise(W_, H_, rng)
    m = np.clip(1 - dist / (reach * (0.45 + 1.0 * n)), 0, 1) ** 1.5          # неровная граница
    hf = np.asarray(Image.fromarray((rng.random((H_, W_)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255
    alpha = np.clip(m * (0.62 + 0.55 * hf), 0, 1) * 0.95
    col = np.stack([230 + 25 * n, 240 + 15 * n, 250 + 5 * n], -1)
    frost = np.dstack([np.clip(col, 0, 255), alpha * 255]).astype(np.uint8)
    layer = Image.fromarray(frost, 'RGBA').filter(ImageFilter.GaussianBlur(1.2))

    # морозные узоры: ветвящиеся штрихи от краёв внутрь
    lines = Image.new('RGBA', (W_, H_), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)

    def fern(x, y, ang, length, depth):
        if depth < 0 or length < 6:
            return
        x2, y2 = x + math.cos(ang) * length, y + math.sin(ang) * length
        ld.line(((x, y), (x2, y2)), fill=(255, 255, 255, 170 - (2 - depth) * 40), width=max(1, depth + 1))
        steps = int(rng.integers(2, 5))
        for j in range(1, steps + 1):
            t = j / (steps + 1)
            bx, by = x + (x2 - x) * t, y + (y2 - y) * t
            for sgn in (-1, 1):
                fern(bx, by, ang + sgn * rng.uniform(0.6, 1.0), length * rng.uniform(0.28, 0.45), depth - 1)

    for _ in range(int((W_ + H_) / 16)):
        side = rng.integers(4)
        if side == 0:
            x, y, ang = rng.uniform(0, W_), 0, math.pi / 2
        elif side == 1:
            x, y, ang = rng.uniform(0, W_), H_ - 1, -math.pi / 2
        elif side == 2:
            x, y, ang = 0, rng.uniform(0, H_), 0.0
        else:
            x, y, ang = W_ - 1, rng.uniform(0, H_), math.pi
        fern(x, y, ang + rng.uniform(-0.7, 0.7), rng.uniform(30, 85), 2)
    la = np.asarray(lines, np.float32)
    la[..., 3] *= np.clip(m * 1.6, 0, 1)                                     # узоры гаснут к центру
    lines = Image.fromarray(la.astype(np.uint8), 'RGBA')

    # блёстки
    sp = Image.new('RGBA', (W_, H_), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sp)
    for _ in range(int(W_ * H_ / 900)):
        x, y = int(rng.integers(W_)), int(rng.integers(H_))
        if m[y, x] > 0.25:
            r = rng.uniform(0.6, 1.8)
            sd.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(160 + 90 * m[y, x])))
    # «толща льда» под инеем: голубая тень, иначе белый иней теряется на светлом фоне
    deep = np.dstack([np.full((H_, W_), 120, np.float32), np.full((H_, W_), 172, np.float32),
                      np.full((H_, W_), 226, np.float32), np.clip(m * 1.25, 0, 1) ** 1.2 * 150]).astype(np.uint8)
    under = Image.fromarray(deep, 'RGBA').filter(ImageFilter.GaussianBlur(6))
    # узоры: голубой контур под белой сердцевиной
    halo = Image.fromarray(np.dstack([np.full((H_, W_), 90, np.uint8), np.full((H_, W_), 150, np.uint8),
                                      np.full((H_, W_), 215, np.uint8), np.asarray(lines.getchannel('A'))]), 'RGBA').filter(ImageFilter.GaussianBlur(1.6))
    out = Image.alpha_composite(img.convert('RGBA'), under)
    out = Image.alpha_composite(out, layer)
    out = Image.alpha_composite(out, halo)
    out = Image.alpha_composite(out, lines)
    return Image.alpha_composite(out, sp)


STYLES = {'arena': _arena, 'digital': _digital, 'gazeta': _gazeta, 'minimal': _minimal, 'ice': _ice,
          'ice_frost': lambda *a: _ice(*a, frost=True),
          'ice_color': lambda *a: _ice(*a, colored=True),
          'ice_frost_color': lambda *a: _ice(*a, frost=True, colored=True),
          'ice_logo': lambda *a: _ice(*a, colored=True, logos=True),
          'ice_frost_logo': lambda *a: _ice(*a, frost=True, colored=True, logos=True),
          'ice_logo_over': lambda *a: _ice(*a, colored=True, logos=True, over=True),
          'ice_frost_logo_over': lambda *a: _ice(*a, frost=True, colored=True, logos=True, over=True)}


def render(items, path, style='arena', league='KHL', title='ИТОГИ ДНЯ', date_title=None):
    league = league.upper()
    return STYLES[style](rs._resolve(items, league), path, league, title, date_title)
