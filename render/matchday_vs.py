"""«Матчи дня» в шаблоне «Versus» (versus.py, 14.10.2026): тёмный фон баннера, по матчу на «полосу».
Полоса — уменьшенный «Versus» в длину: слева панель хозяев, справа панель гостей (цвет клуба, концентрический
узор, крупная эмблема-наклейка; хозяева чуть выше, гости чуть ниже — как смещённые панели баннера), между ними
аббревиатуры в цветах клубов, «vs» над временем МСК и плашки П1/Х/П2 (если линия есть).

    import matchday_vs as mv
    mv.render(items, 'matchi_khl.jpg', league='KHL', date_title='пятница, 16 октября')
    # альбом (itogi_job.split_matchi): у всех постеров один rows, у второго и дальше cont=True
    mv.render(grp, path, league='NHL', date_title=..., cont=k > 0, rows=max(len(g) for g in groups))

Вызов как у preview_ice.render; style= принимается и не используется — в itogi_job достаточно заменить модуль.
items: [{home, away, time: '19:30', odds: (П1, Х, П2) | None}]; клубы НХЛ — в любом виде (nhl.resolve), КХЛ — как в
таблице (плюс KHL_ALIAS); неизвестный клуб — серая панель и круг с аббревиатурой, постер не падает.
cont=True — продолжение альбома: вместо заголовка и даты крупно «JARVIS | KXL/NHL», полосы на тех же местах.
rows — мест под матчи (общее для постеров альбома): размер постера и места полос зависят только от rows.
Размер: 1080 × до 1350 (4:5 — от 4 матчей; 1–3 матча — ниже) × quality.S (4К: 3240 × до 4050).
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import brand_kit
import nhl
import poster
import quality
import recap
import versus as vs

S = quality.S
W = 1080
H_MAX = 1350                 # 4:5 — в альбоме Telegram постеры встают рядом и крупно
BG = vs.BG
MX = 36                      # поле слева и справа
HEAD, FOOT = 236, 104        # шапка и подвал (база 1080)
GAP = 18                     # между полосами
ROW_MAX = 240                # выше полоса — перебор (1–3 матча)
OSW, ALU, MAN = 'Oswald[wght].ttf', 'AlumniSans[wght].ttf', 'Manrope[wght].ttf'
TAG = {'KHL': 'KXL', 'NHL': 'NHL'}
INK = (24, 20, 14)           # текст на плашках, как у versus
GREY = (150, 148, 156)
FOOT_ODDS = recap.FOOT_ODDS  # «…на момент публикации» — без упоминания таблицы
KHL_ALIAS = {'Металлург Мг': 'Металлург', 'Шанхай': 'Шанхайские Драконы', 'Шанхай Дрэгонс': 'Шанхайские Драконы',
             'Динамо М': 'Динамо Москва', 'Динамо Мск': 'Динамо Москва', 'Динамо Мн': 'Динамо Минск',
             'Салават': 'Салават Юлаев'}


def _layout(n, rows):
    """→ (высота полосы, верх первой полосы, высота постера). Зависит только от rows (≥ n): в альбоме у всех
    постеров одинаково, полосы на одних местах."""
    rows = max(rows or 0, n, 1)
    avail = H_MAX - HEAD - FOOT
    row = int(min(ROW_MAX, (avail + GAP) / rows - GAP))
    block = rows * (row + GAP) - GAP
    if row < ROW_MAX:                          # 4 и больше — ровно 4:5, остаток округления поровну сверху и снизу
        return row, HEAD + (avail - block) // 2, H_MAX
    return row, HEAD, HEAD + block + FOOT


def _club(name, league):
    """→ (ключ клуба, цвет панели, второй цвет, аббревиатура) через versus._team; неизвестный клуб не роняет постер."""
    name = str(name).strip()
    key = KHL_ALIAS.get(name, name) if league != 'NHL' else name
    try:
        ru, c1, c2, abbr, _ = vs._team(key, league)
        return ru, c1, c2, abbr
    except KeyError:
        return name, (110, 112, 120), (60, 60, 64), name.replace(' ', '').replace('-', '')[:3].upper()


def _readable(c, min_l=105):
    """Цвет клуба для текста на тёмном фоне: как у versus (чуть к белому); тёмный (тёмно-синий и т. п.) —
    ярче с тем же оттенком, а если и так темно — ещё к белому."""
    c = vs._mix(c, 0.06)
    if vs._lum(c) >= min_l:
        return c
    if max(c) < 235:
        k = 235 / max(1, max(c))
        c = tuple(min(255, int(v * k)) for v in c)
    lum = vs._lum(c)
    return vs._mix(c, (min_l - lum) / (255 - lum)) if lum < min_l else c


def _cap(name, wght, cap_px):
    """Шрифт, у которого высота прописных (по «Н») = cap_px."""
    f = brand_kit.font(name, 200, wght)
    l, t, r, b = f.getbbox('Н', anchor='ls')
    return brand_kit.font(name, max(8, round(200 * cap_px / (b - t))), wght)


def _txt(d, x, cy, text, f, fill, anchor='m', ref='Н'):
    """Текст по центру строки прописных (ref) на cy — хвосты Д/Ц/Щ ниже строки не сдвигают его;
    anchor: 'l' — левый край чернил на x, 'r' — правый, 'm' — центр. → ширина чернил."""
    l, _, r, _ = f.getbbox(text, anchor='ls')
    _, t, _, b = f.getbbox(ref, anchor='ls')
    ox = x - l if anchor == 'l' else x - r if anchor == 'r' else x - (l + r) / 2
    d.text((ox, cy - (t + b) / 2), text, font=f, fill=fill, anchor='ls')
    return r - l


def _spaced_w(text, f, sp):
    return sum(f.getlength(ch) for ch in text) + sp * (len(text) - 1)


def _spaced(d, x, cy, text, f, fill, sp, anchor='m'):
    """Разрядка; вертикаль — как у _txt (по строке прописных)."""
    w = _spaced_w(text, f, sp)
    x = x - w / 2 if anchor == 'm' else x - w if anchor == 'r' else x
    _, t, _, b = f.getbbox('Н', anchor='ls')
    for ch in text:
        d.text((x, cy - (t + b) / 2), ch, font=f, fill=fill, anchor='ls')
        x += f.getlength(ch) + sp
    return w


def _soft_shadow(img, mask, xy, blur, alpha):
    """Тень по маске (L) на локальном слое — без размытия всего постера. xy — где лежит маска на img."""
    m = int(blur * 3)
    tile = Image.new('L', (mask.width + 2 * m, mask.height + 2 * m), 0)
    tile.paste(mask.point(lambda v: v * alpha // 255), (m, m))
    sh = Image.new('RGBA', tile.size, (0, 0, 0, 0))
    sh.putalpha(tile.filter(ImageFilter.GaussianBlur(blur)))
    img.alpha_composite(sh, (max(0, int(xy[0]) - m), max(0, int(xy[1]) - m)))


def _panel(img, box, color, seed, fade, emb_c, dim=0.5, zoom=1.8):
    """Панель клуба из versus._panel с мягкой тенью вниз-вправо, как на баннере. Узор берём из панели в zoom раз
    больше и вырезаем середину — кольца такой же ширины относительно эмблемы, как на «Versus» (иначе на маленькой
    панели они мелкие, как отпечаток пальца). Центр колец — за эмблемой (emb_c — доли панели)."""
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    w, h = x1 - x0, y1 - y0
    _soft_shadow(img, Image.new('L', (w, h), 255), (x0 + 9 * S, y0 + 13 * S), 13 * S, 120)
    bw, bh = int(w * zoom), int(h * zoom)
    cx, cy = (bw - w) // 2, (bh - h) // 2
    big = vs._panel(bw, bh, color, (cx + emb_c[0] * w, cy + emb_c[1] * h), seed, fade, dim)
    img.paste(big.crop((cx, cy, cx + w, cy + h)), (x0, y0))


def _badge(abbr, color, size):
    """Нет эмблемы (клуба нет в наборе) — круг в цвете клуба с белым кантом и аббревиатурой, вместо пустой заглушки."""
    im = Image.new('RGBA', (int(size), int(size)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, size - 1, size - 1), fill=vs._mix(color, -0.25) + (255,), outline=(255, 255, 255, 255),
              width=max(3, int(size // 24)))
    _txt(d, size / 2, size / 2, abbr, _fit_w(abbr, ALU, 900, size * 0.30, size * 0.66), (255, 255, 255, 255))
    return im


def _emblem(img, team, cx, cy, size, abbr='', color=(110, 112, 120)):
    """Эмблема-наклейка (poster._emblem) с тенью, как versus._paste_emblem, но тень по размеру эмблемы."""
    slug = poster.TEAMS.get(team, (None,))[0]
    if slug and os.path.exists(os.path.join(poster.EMB, slug + '.png')):
        em = poster._emblem(team, int(size))
    else:
        em = _badge(abbr or team[:3].upper(), color, size)
    k = size / (380 * S)
    x, y = cx - em.width / 2, cy - em.height / 2
    _soft_shadow(img, em.getchannel('A'), (x + 10 * S * k, y + 22 * S * k), max(3 * S, 26 * S * k), 150)
    img.alpha_composite(em, (int(x), int(y)))


def _brand(d, cx, cy, league, size, acc):
    """Марка «JARVIS | KXL» как на баннере «Versus»: Oswald, JARVIS белым, черта, метка лиги акцентом."""
    fm = brand_kit.font(OSW, size * S, 700)
    tag = TAG[league]
    gx, bar = size * 0.58 * S, max(2.0, size * 0.125) * S
    wj, wt = fm.getlength('JARVIS'), fm.getlength(tag)
    x = cx - (wj + 2 * gx + bar + wt) / 2
    _, t, _, b = fm.getbbox('J', anchor='ls')
    base = cy - (t + b) / 2
    d.text((x, base), 'JARVIS', font=fm, fill=(245, 245, 245), anchor='ls')
    bx = x + wj + gx
    d.rectangle((bx, base + t * 1.08, bx + bar, base + 0.06 * size * S), fill=(220, 220, 225))
    d.text((bx + bar + gx, base), tag, font=fm, fill=acc, anchor='ls')


def _background(H):
    """Фон баннера: BG с лёгким подсветом (за заголовком и справа ниже); зерно и холст — в конце (quality.texture)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    k = (1 + 0.11 * np.exp(-((xx - 540) ** 2 + (yy - 120) ** 2) / (2 * 400 ** 2))
         + 0.05 * np.exp(-((xx - 820) ** 2 + (yy - 0.62 * H) ** 2) / (2 * 460 ** 2)))
    arr = np.clip(np.array(BG, np.float32)[None, None] * k[..., None], 0, 255).astype(np.uint8)
    return Image.fromarray(arr, 'RGB').resize((W * S, H * S), Image.BILINEAR).convert('RGBA')


def _pill(d, cx, cy, w, h, label, value, fl, fv, fill):
    """Плашка линии как у «Versus» (скругление 0.28 h, цвет акцента), подпись П1/Х/П2 — внутри, приглушённо."""
    d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=int(h * .28), fill=fill)
    gl = h * 0.2
    lw, vw = fl.getlength(label), fv.getbbox(value, anchor='ls')[2]
    x = cx - (lw + gl + vw) / 2
    _txt(d, x, cy, label, fl, INK + (150,), 'l')
    _txt(d, x + lw + gl, cy, value, fv, INK + (255,), 'l')


def _geom(R):
    """Размеры полосы высотой R (база 1080): ширина панели, смещение панелей, кегли."""
    off = round(R * 0.10)
    pw = int(min(236, max(150, (R - off) * 1.2)))
    return dict(pw=pw, off=off, zx0=MX + pw + 26, zx1=W - MX - pw - 26,
                ab=min(80, R * 0.40), tm=min(44, R * 0.20), ph=min(48, max(34, R * 0.27)))


def _strip(img, it, y0, R, g, league, acc, F, pill_w, i):
    hn, hc, _, ha = _club(it['home'], league)
    an, ac, ac2, aa = _club(it['away'], league)
    ac = vs._distinct(hc, ac, ac2)
    pw, off = g['pw'], g['off']
    # панели: хозяева слева и выше, гости справа и ниже (их рисуем второй — как на баннере, поверх)
    for x0, top, col, team, ab, seed, fade in ((MX, y0, hc, hn, ha, 11 + 7 * i, 'down'),
                                               (W - MX - pw, y0 + off, ac, an, aa, 23 + 7 * i, 'up')):
        box = (x0 * S, top * S, (x0 + pw) * S, (top + R - off) * S)
        _panel(img, box, col, seed, fade, (0.5, 0.52))
        es = min((R - off) * 0.84, pw * 0.76)
        _emblem(img, team, (x0 + pw / 2) * S, (top + (R - off) * 0.52) * S, es * S, ab, col)

    d = ImageDraw.Draw(img)
    o = it.get('odds')
    zc = (g['zx0'] + g['zx1']) / 2
    ya = y0 + (R * 0.33 if o else R * 0.5)                   # строка «ТОР  vs/19:00  ДИН» (хвост Д — не на плашку)
    t = (it.get('time') or '').strip()
    # середина: «vs» над временем
    if t:
        tw = F['tm'].getbbox(t, anchor='ls')[2]
        vs_h = F['vs'].getbbox('vs', anchor='ls')
        vs_h = vs_h[3] - vs_h[1]
        gap = g['tm'] * 0.30
        top = ya - (vs_h + gap + g['tm']) / 2
        _txt(d, zc * S, (top + vs_h / 2) * S, 'vs', F['vs'], (245, 245, 245), ref='v')
        _txt(d, zc * S, (top + vs_h + gap + g['tm'] / 2) * S, t, F['tm'], (250, 250, 250))
        mid = tw / S
    else:
        _txt(d, zc * S, ya * S, 'vs', F['vs_big'], (245, 245, 245), ref='v')
        mid = F['vs_big'].getlength('vs') / S
    # аббревиатуры: хозяева у своей панели слева, гости — справа (у versus так же: слева и справа по краю)
    room = (g['zx1'] - g['zx0']) / 2 - mid / 2 - 16
    for abbr, col, x, anchor in ((ha, hc, g['zx0'], 'l'), (aa, ac, g['zx1'], 'r')):
        f = F['ab']
        while f.getbbox(abbr, anchor='ls')[2] - f.getbbox(abbr, anchor='ls')[0] > room * S and f.size > 12 * S:
            f = brand_kit.font(ALU, f.size - S, 900)
        _txt(d, x * S, ya * S, abbr, f, _readable(col) + (255,), anchor)
    # линия: П1 под хозяевами (по левому краю аббревиатуры), П2 под гостями (по правому), Х посередине под временем
    if o:
        yp = y0 + R * 0.79
        xs = (g['zx0'] + pill_w / 2, zc, g['zx1'] - pill_w / 2)
        for x, lab, v in zip(xs, ('П1', 'Х', 'П2'), o):
            _pill(d, x * S, yp * S, pill_w * S, g['ph'] * S, lab, '%.2f' % v, F['pl'], F['pv'], acc)


def render(items, path, league='KHL', title='МАТЧИ ДНЯ', date_title=None, cont=False, rows=None, *, style='strips'):
    """style — макет (STYLES): strips (по умолчанию), diagonal, cards, center, fav, minimal. Неизвестный style
    (например, 'columns' из вызова preview_ice.render) — strips. Шапка, подвал, фон и размер постера — общие."""
    style = style if style in STYLES else 'strips'
    league = league.upper()
    if league == 'NHL':
        nhl.register()
    acc = poster.ACC if league == 'KHL' else nhl.ICE
    H, paint = _STYLE[style](items, rows, league, acc)

    img = _background(H)
    d = ImageDraw.Draw(img)
    if cont:                                   # продолжение альбома: крупно марка канала на месте заголовка и даты
        _brand(d, W / 2 * S, HEAD * 0.50 * S, league, 64, acc)
    else:
        _brand(d, W / 2 * S, 50 * S, league, 26, acc)
        ft = _fit_w(title, ALU, 900, 80 * S, (W - 2 * MX) * S)
        _txt(d, W / 2 * S, 124 * S, title, ft, (245, 245, 245))
        if date_title:
            _spaced(d, W / 2 * S, 196 * S, date_title.upper(), _cap(OSW, 600, 21 * S), acc, 3 * S)
    paint(img)

    d = ImageDraw.Draw(img)
    note = 'ВРЕМЯ МОСКОВСКОЕ' + (' · ' + FOOT_ODDS if any(it.get('odds') for it in items) else '')
    _spaced(d, W / 2 * S, (H - 66) * S, note, _cap(MAN, 700, 10 * S), GREY, 1.2 * S)
    _spaced(d, W / 2 * S, (H - 32) * S, '@jarvibet', _cap(OSW, 600, 19 * S), acc, 2 * S)

    out = quality.texture(img, 2)
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    out.save(path, quality=93, optimize=True)
    return path


def _st_strips(items, rows, league, acc):
    """Полосы (первый вариант): панели по краям, аббревиатуры, «vs» над временем, плашки П1/Х/П2."""
    R, top, H = _layout(len(items), rows)
    g = _geom(R)
    F = dict(ab=_cap(ALU, 900, g['ab'] * S), tm=_cap(OSW, 700, g['tm'] * S),
             vs=brand_kit.font(OSW, int(g['tm'] * 0.62) * S, 600), vs_big=brand_kit.font(OSW, int(g['tm'] * 1.1) * S, 600),
             pv=_cap(OSW, 600, g['ph'] * 0.48 * S), pl=_cap(MAN, 800, g['ph'] * 0.30 * S))
    pill_w = _pill_w(F, g['ph'], items)

    def paint(img):
        for i, it in enumerate(items):
            _strip(img, it, top + i * (R + GAP), R, g, league, acc, F, pill_w, i)
    return H, paint


def _fit_w(text, name, wght, cap_px, max_w):
    """Кегль по высоте прописных, но не шире max_w."""
    f = _cap(name, wght, cap_px)
    while f.getlength(text) > max_w and f.size > 10:
        f = brand_kit.font(name, f.size - S, wght)
    return f


if __name__ == '__main__':
    demo = [dict(home='Адмирал', away='Спартак', time='12:30', odds=(3.40, 3.78, 1.95)),
            dict(home='Торпедо', away='Динамо Москва', time='19:00', odds=(2.12, 3.76, 3.00))]
    print(render(demo, 'out/matchday_vs_demo.jpg', league='KHL', date_title='пятница, 16 октября'))
