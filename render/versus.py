"""Предматчевый баннер «Versus» (14.10.2026, по образцу владельца): квадрат, две смещённые цветные панели клубов
с концентрическим узором и крупной эмблемой, справа сверху аббревиатуры «СЕВ vs СКА» в цветах клубов, по бокам
вертикально название и город, слева снизу дата, время МСК и линия П1/Х/П2 плашками.
Вместо фото игроков — эмблемы (права на фото у лиги и клубов); логотипов букмекеров нет.

    import versus
    versus.render('Северсталь', 'СКА', 'out/vs.jpg', date='13 октября', time='19:00', odds=(2.60, 4.20, 2.35))
    # НХЛ: league='NHL' (nhl.register() вызывается сам); odds=None — без плашек линии
Размер: 1080×1080 × quality.S (4К — 3240×3240).
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import brand_kit
import nhl
import poster
import quality

S = quality.S
W = H = 1080
BG = (22, 20, 24)

KHL_ABBR = {
    'Авангард': 'АВГ', 'Автомобилист': 'АВТ', 'Адмирал': 'АДМ', 'Ак Барс': 'АКБ', 'Амур': 'АМР', 'Барыс': 'БАР',
    'Динамо Москва': 'ДИН', 'Динамо Минск': 'ДМН', 'Лада': 'ЛАД', 'Локомотив': 'ЛОК', 'Металлург': 'ММГ',
    'Нефтехимик': 'НХК', 'Салават Юлаев': 'СЮЛ', 'Северсталь': 'СЕВ', 'Сибирь': 'СИБ', 'СКА': 'СКА', 'Сочи': 'СОЧ',
    'Спартак': 'СПР', 'Торпедо': 'ТОР', 'Трактор': 'ТРК', 'ЦСКА': 'ЦСК', 'Шанхайские Драконы': 'ШАН',
}
KHL_CITY = {
    'Авангард': 'Омск', 'Автомобилист': 'Екатеринбург', 'Адмирал': 'Владивосток', 'Ак Барс': 'Казань',
    'Амур': 'Хабаровск', 'Барыс': 'Астана', 'Динамо Москва': 'Москва', 'Динамо Минск': 'Минск', 'Лада': 'Тольятти',
    'Локомотив': 'Ярославль', 'Металлург': 'Магнитогорск', 'Нефтехимик': 'Нижнекамск', 'Салават Юлаев': 'Уфа',
    'Северсталь': 'Череповец', 'Сибирь': 'Новосибирск', 'СКА': 'Санкт-Петербург', 'Сочи': 'Сочи',
    'Спартак': 'Москва', 'Торпедо': 'Нижний Новгород', 'Трактор': 'Челябинск', 'ЦСКА': 'Москва',
    'Шанхайские Драконы': 'Шанхай',
}


def _team(name, league):
    """→ (ru-название, цвет панели, второй цвет клуба, аббревиатура, подпись сбоку)."""
    if league == 'NHL':
        ru = nhl.resolve(name)
        c1, c2, abbr, en = nhl.TEAMS[ru][1], nhl.TEAMS[ru][2], nhl.TEAMS[ru][3], nhl.TEAMS[ru][4]
        color, side = poster.BANNER.get(ru, c1), '%s · %s' % (ru, en)
    else:
        ru = name
        c2 = poster.TEAMS[ru][2]
        color, abbr = poster.BANNER[ru], KHL_ABBR[ru]
        side = ru if KHL_CITY[ru] in ru else '%s · %s' % (ru, KHL_CITY[ru])
    return ru, color, c2, abbr, side.upper()


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _distinct(hc, ac, ac2):
    """Цвета клубов почти одинаковые (оба красные и т. п.) — гостям второй фирменный цвет; тёмный осветляем,
    серый/белый не берём."""
    if sum((a - b) ** 2 for a, b in zip(hc, ac)) ** .5 >= 110:
        return ac
    if max(ac2) - min(ac2) < 40:                 # второй цвет без оттенка (белый, серый, чёрный) — оставляем основной
        return ac
    if _lum(ac2) < 70:                           # тёмный — осветляем, сохраняя насыщенность
        k = 170 / max(ac2)
        return tuple(min(255, int(v * k)) for v in ac2)
    return ac2


def _mix(c, k):
    """k > 0 — к белому, k < 0 — к чёрному."""
    t = (255, 255, 255) if k > 0 else (0, 0, 0)
    k = abs(k)
    return tuple(int(a + (b - a) * k) for a, b in zip(c, t))


def _smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def _panel(w, h, color, center, seed, fade='down', dim=0.42, pad=0, freq=15):
    """Панель клуба: концентрические «топографические» кольца тон-в-тон и перелив яркости:
    fade='down' — у верхнего края приглушённо, к низу ярче (хозяева); 'up' — наоборот (гости); None — ровно.
    dim — яркость у приглушённого края (доля от цвета клуба).
    freq — колец на ширину панели (15 — как у «Versus»).
    pad — тот же узор с запасом pad пикселей с каждой стороны (картинка (w + 2pad)×(h + 2pad); для анимации «флага»)."""
    y, x = np.mgrid[-pad:h + pad, -pad:w + pad].astype(np.float32)
    cx, cy = center
    dx, dy = (x - cx) / w, (y - cy) / w
    ang = np.arctan2(dy, dx)
    rng = np.random.default_rng(seed)
    wob = sum(a * np.sin(k * ang + p) for a, k, p in zip(rng.uniform(.004, .012, 3), (2, 3, 5), rng.uniform(0, 6, 3)))
    r = (np.abs(dx) ** 3 + np.abs(dy) ** 3) ** (1 / 3) + wob
    ring = np.sin(r * 2 * np.pi * freq)
    ring = np.clip(ring * 3, -1, 1)                      # чёткие полосы, мягкие края
    t = y / h if fade == 'down' else 1 - y / h
    light = np.ones_like(x) if fade is None else dim + (1.06 - dim) * _smooth(t * 1.15)
    light *= 1 + 0.10 * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * (0.38 * w) ** 2))   # подсвет за эмблемой
    base = np.array(color, np.float32)[None, None, :]
    shade = light[..., None] * (1 + 0.075 * ring[..., None])
    img = np.clip(base * shade, 0, 255).astype(np.uint8)
    return Image.fromarray(img, 'RGB')


def _paste_emblem(img, team, cx, cy, size):
    em = poster._emblem(team, size)
    a = em.getchannel('A')
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    blk = Image.new('RGBA', em.size, (0, 0, 0, 150))
    sh.paste(blk, (int(cx - em.width / 2 + 10 * S), int(cy - em.height / 2 + 22 * S)), a)
    sh = sh.filter(ImageFilter.GaussianBlur(26 * S))
    img.alpha_composite(sh)
    img.alpha_composite(em, (int(cx - em.width / 2), int(cy - em.height / 2)))


def _fit(text, box_w, box_h, wght=700, name='Oswald[wght].ttf'):
    """Шрифт максимального размера, при котором text влезает в box (по чернилам)."""
    size = int(box_h * 1.6)
    while size > 10:
        f = brand_kit.font(name, size, wght)
        l, t, r, b = f.getbbox(text)
        if r - l <= box_w and b - t <= box_h:
            return f
        size -= max(1, size // 40)
    return brand_kit.font(name, 10, wght)


def _text_ink(d, x, y, text, f, fill, anchor='l'):
    """Текст так, чтобы верх чернил был на y; anchor 'l' — левый край чернил на x, 'r' — правый, 'm' — центр."""
    l, t, r, b = f.getbbox(text)
    if anchor == 'l':
        ox = x - l
    elif anchor == 'r':
        ox = x - r
    else:
        ox = x - (l + r) / 2
    d.text((ox, y - t), text, font=f, fill=fill)
    return b - t


def _vertical(img, text, x, y_mid, f, fill, ccw=True, spacing=0.14):
    """Вертикальная подпись разрядкой: ccw — читается снизу вверх (левый край), иначе сверху вниз (правый)."""
    sp = f.size * spacing
    wid = sum(f.getlength(ch) for ch in text) + sp * (len(text) - 1)
    hgt = f.getbbox('ЁЙ')[3] + 4
    tile = Image.new('RGBA', (int(wid) + 8, int(hgt) + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    cx = 4
    for ch in text:
        d.text((cx, 4), ch, font=f, fill=fill)
        cx += f.getlength(ch) + sp
    tile = tile.rotate(90 if ccw else -90, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(tile, (int(x - tile.width / 2), int(y_mid - tile.height / 2)))


def _pill(d, box, text, label, f, fl, fill, txt):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=int((y1 - y0) * .28), fill=fill)
    d.text(((x0 + x1) / 2, (y0 + y1) / 2 + 1 * S), text, font=f, fill=txt, anchor='mm')
    d.text(((x0 + x1) / 2, y0 - 10 * S), label, font=fl, fill=(170, 168, 176), anchor='md')


# панели: хозяева — слева сверху, гости — справа снизу поверх (базовые пиксели 1080×1080)
P1 = (100, 0, 620, 672)
P2 = (460, 408, 980, 1080)
EMBLEM = 380                                         # сторона квадрата эмблемы
EMBLEM_DY = 6                                        # эмблема чуть ниже центра панели


def _teams(home, away, league):
    """→ (хозяева, гости, акцент); хозяева/гости — (ru, цвет, аббр., подпись сбоку)."""
    if league == 'NHL':
        nhl.register()
    hn, hc, _, ha, hs = _team(home, league)
    an, ac, ac2, aa, as_ = _team(away, league)
    ac = _distinct(hc, ac, ac2)
    acc = poster.ACC if league == 'KHL' else nhl.ICE
    return (hn, hc, ha, hs), (an, ac, aa, as_), acc


def _panel_specs(hc, ac, hn, an, fade):
    """Панели в порядке отрисовки: (прямоугольник, цвет, клуб эмблемы, seed узора, центр колец (доли), перелив)."""
    return ((P1, hc, hn, 11, (0.62, 0.42), fade[0]),
            (P2, ac, an, 23, (0.40, 0.55), fade[1]))


def _background():
    img = Image.new('RGBA', (W * S, H * S), BG + (255,))
    # фон: лёгкий подсвет и зерно
    g = np.mgrid[0:H, 0:W].astype(np.float32)
    vign = 1 + 0.10 * np.exp(-((g[1] - 760) ** 2 + (g[0] - 300) ** 2) / (2 * 380 ** 2))
    bgarr = np.clip(np.array(BG, np.float32)[None, None] * vign[..., None], 0, 255).astype(np.uint8)
    img.paste(Image.fromarray(bgarr, 'RGB').resize(img.size, Image.BILINEAR), (0, 0))
    return img


def _draw_panels(img, specs):
    for (x0, y0, x1, y1), col, emb, seed, ctr, fd in specs:
        w, h = (x1 - x0) * S, (y1 - y0) * S
        pn = _panel(w // S, h // S, col, (ctr[0] * (w // S), ctr[1] * (h // S)), seed, fd).resize((w, h), Image.BICUBIC)
        sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle((x0 * S + 14 * S, y0 * S + 20 * S, x1 * S + 14 * S, y1 * S + 20 * S),
                                     fill=(0, 0, 0, 120))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(24 * S)))
        img.paste(pn, (x0 * S, y0 * S))
        _paste_emblem(img, emb, (x0 + x1) / 2 * S, ((y0 + y1) / 2 + EMBLEM_DY) * S, EMBLEM * S)


def layers(home, away, date='', time='', odds=None, league='KHL', tz='время московское', fade=('down', 'up'), site=False):
    """Слои баннера по отдельности (для анимации, versus_anim.py), размер W*S × H*S, без текстуры холста:
    {'bg': фон RGBA, 'fg': текст/плашки/марка на прозрачном RGBA, 'specs': панели (_panel_specs)}."""
    (hn, hc, ha, hs), (an, ac, aa, as_), acc = _teams(home, away, league)
    fg = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    _draw_foreground(fg, hc, ha, hs, ac, aa, as_, acc, date, time, odds, league, tz, site=site)
    return {'bg': _background(), 'fg': fg, 'specs': _panel_specs(hc, ac, hn, an, fade)}


def render(home, away, path, date='', time='', odds=None, league='KHL', tz='время московское', fade=('down', 'up')):
    """fade — перелив яркости панелей хозяев и гостей (см. _panel); ('up', 'down') — яркие края, тёмная середина."""
    (hn, hc, ha, hs), (an, ac, aa, as_), acc = _teams(home, away, league)
    img = _background()
    _draw_panels(img, _panel_specs(hc, ac, hn, an, fade))
    _draw_foreground(img, hc, ha, hs, ac, aa, as_, acc, date, time, odds, league, tz)

    out = quality.texture(img, 2) if hasattr(quality, 'texture') else img.convert('RGB')
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    out.convert('RGB').save(path, quality=93, optimize=True)
    return path


def _draw_foreground(img, hc, ha, hs, ac, aa, as_, acc, date, time, odds, league, tz, site=False):
    """Аббревиатуры, вертикальные подписи, дата/время/линия и марка канала — поверх панелей.
    site=True — вариант для сайта (владелец 31.10): без «vs», аббревиатуры гостей плотно под хозяевами."""
    d = ImageDraw.Draw(img)
    # аббревиатуры: хозяева слева, «vs» между строк, гости справа — лесенкой
    AB = 'AlumniSans[wght].ttf'
    fa = min((_fit(t, 340 * S, 155 * S, 900, AB) for t in (ha, aa)), key=lambda f: f.size)
    hh = _text_ink(d, 684 * S, 36 * S, ha, fa, _mix(hc, 0.06) + (255,), anchor='l')
    if site:
        _text_ink(d, 1030 * S, 36 * S + hh + 16 * S, aa, fa, _mix(ac, 0.06) + (255,), anchor='r')
    else:
        fv = brand_kit.font('Oswald[wght].ttf', 40 * S, 600)
        d.text((690 * S, 218 * S), 'vs', font=fv, fill=(245, 245, 245), anchor='lm')
        _text_ink(d, 1030 * S, 241 * S, aa, fa, _mix(ac, 0.06) + (255,), anchor='r')

    # вертикальные подписи
    fs = brand_kit.font('Manrope[wght].ttf', 17 * S, 600)
    _vertical(img, '#' + hs, 50 * S, 336 * S, fs, hc + (255,), ccw=True)
    _vertical(img, '#' + as_, 1030 * S, 744 * S, fs, ac + (255,), ccw=False)

    # дата, время, линия
    X0, X1 = 130, 430
    cxm = (X0 + X1) / 2 * S
    dy = 0 if odds else 90                              # без линии — блок даты ниже, к центру пустого места
    if date:
        fd = _fit(date.upper(), (X1 - X0) * S, 30 * S, 600)
        d.text((cxm, (726 + dy) * S), date.upper(), font=fd, fill=acc, anchor='mm')
    if time:
        ft = _fit(time, (X1 - X0) * S, 74 * S, 700)
        d.text((cxm, (800 + dy) * S), time, font=ft, fill=(250, 250, 250), anchor='mm')
    fz = brand_kit.font('Manrope[wght].ttf', 19 * S, 600)
    d.text((cxm, (860 + dy) * S), tz, font=fz, fill=(205, 203, 210), anchor='mm')
    if odds:
        fo = brand_kit.font('Oswald[wght].ttf', 30 * S, 600)
        fl = brand_kit.font('Manrope[wght].ttf', 15 * S, 700)
        pw, gap, y0 = 88, 12, 930
        x = cxm / S - (3 * pw + 2 * gap) / 2
        for lab, v in zip(('П1', 'Х', 'П2'), odds):
            _pill(d, (x * S, y0 * S, (x + pw) * S, (y0 + 46) * S), '%.2f' % v, lab, fo, fl, acc, (24, 20, 14))
            x += pw + gap
        fn = brand_kit.font('Manrope[wght].ttf', 14 * S, 700)
        d.text((cxm, 1000 * S), 'ОСНОВНОЕ ВРЕМЯ', font=fn, fill=(150, 148, 156), anchor='mm')

    # марка канала
    fm = brand_kit.font('Oswald[wght].ttf', 24 * S, 700)
    tag = 'KXL' if league == 'KHL' else 'NHL'
    wj = fm.getlength('JARVIS')
    wt = fm.getlength(tag)
    gx, bar = 14 * S, 3 * S
    xr = (cxm + (wj + gx * 2 + bar + wt) / 2)
    yb = 1056 * S
    d.text((xr, yb), tag, font=fm, fill=acc, anchor='rs')
    d.rectangle((xr - wt - gx - bar, yb - 22 * S, xr - wt - gx, yb), fill=(220, 220, 225))
    d.text((xr - wt - 2 * gx - bar, yb), 'JARVIS', font=fm, fill=(245, 245, 245), anchor='rs')


if __name__ == '__main__':
    print(render('Северсталь', 'СКА', 'out/versus_demo.jpg', date='13 октября', time='19:00', odds=(2.60, 4.20, 2.35)))
