"""«Матчи дня» в шаблоне «Versus» (versus.py, 14.10.2026): тёмный фон баннера, по матчу на «полосу».
Полоса — уменьшенный «Versus» в длину: слева панель хозяев, справа панель гостей (цвет клуба, концентрический
узор, крупная эмблема-наклейка; хозяева чуть выше, гости чуть ниже — как смещённые панели баннера), между ними
аббревиатуры в цветах клубов, «vs» над временем МСК и плашки П1/Х/П2 (если линия есть).

    import matchday_vs as mv
    mv.render(items, 'matchi_khl.jpg', league='KHL', date_title='пятница, 16 октября')
    # альбом (itogi_job.split_matchi): у всех постеров один rows, у второго и дальше cont=True
    mv.render(grp, path, league='NHL', date_title=..., cont=k > 0, rows=max(len(g) for g in groups))

Вызов как у preview_ice.render. style= — вариант макета (STYLES), всё остальное (шапка, подвал, фон, rows/cont) общее:
  strips   — (по умолчанию) полосы: панели клубов по краям, аббревиатуры, «vs» над временем, плашки П1/Х/П2;
  diagonal — панели хозяев и гостей встречаются косым срезом, время — на срезе в тёмной скошенной плашке;
  cards    — сетка 2 колонки из мини-«Versus»: две панели с эмблемами, строка «АББР время АББР», плашки линии;
  center   — цвет клубов от краёв гаснет к тёмной середине, полные названия под эмблемами, линия тонкой строкой;
  fav      — как strips, фаворит линии (меньший из П1/П2) крупнее и ярче, с меткой и залитой плашкой, второй приглушён;
  minimal  — без панелей: крупное время слева, эмблемы со свечением цвета клуба, названия, линия колонками.
Неизвестный style (например, 'columns' из вызова preview_ice.render) — strips: в itogi_job достаточно заменить модуль.
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
TAG = {'KHL': 'KXL', 'NHL': 'NHL', 'KHL+NHL': 'KXL · NHL'}   # 'KHL+NHL' — итоги прогнозов обеих лиг (team/daily)
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


def _emblem(img, team, cx, cy, size, abbr='', color=(110, 112, 120), dim=False):
    """Эмблема-наклейка (poster._emblem) с тенью, как versus._paste_emblem, но тень по размеру эмблемы.
    dim=True — проигравший в итогах: эмблема приглушена (_fade)."""
    slug = poster.TEAMS.get(team, (None,))[0]
    if slug and os.path.exists(os.path.join(poster.EMB, slug + '.png')):
        em = poster._emblem(team, int(size))
    else:
        em = _badge(abbr or team[:3].upper(), color, size)
    if dim:
        em = _fade(em)
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


def render(items, path, league='KHL', title='МАТЧИ ДНЯ', date_title=None, cont=False, rows=None, *, style='strips',
           results=False):
    """style — макет (STYLES): strips (по умолчанию), diagonal, cards, center, fav, minimal. Неизвестный style
    (например, 'columns' из вызова preview_ice.render) — strips. Шапка, подвал, фон и размер постера — общие.
    results=True — «Итоги дня»: items [{home, away, sh, sa, mark: '' | 'ОТ' | 'Б'}], заголовок «ИТОГИ ДНЯ»."""
    style = style if style in STYLES else 'strips'
    league = league.upper()
    if league == 'NHL' or any(str(it.get('league', '')).upper() == 'NHL' for it in items):
        nhl.register()
    acc = poster.ACC if 'KHL' in league else nhl.ICE
    if results:
        title = 'ИТОГИ ДНЯ' if title == 'МАТЧИ ДНЯ' else title
        H, paint = _RES[style](items, rows, league, acc)
    else:
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
    if results:
        note = 'ФИНАЛЬНЫЙ СЧЁТ' + (' · ' + RES_FOOT if any(_res(it)[2] for it in items) else '')
    else:
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



# ---------------------------------------------------------------- общие детали вариантов (style=)

def _pill_w(F, ph, items):
    """Ширина плашки — общая на постер (по самой длинной цифре), колонки П1/Х/П2 ровно; опора 8.88 — постеры
    альбома одной ширины."""
    vals = ['8.88', '0.00'] + ['%.2f' % v for it in items for v in (it.get('odds') or ())]
    return (max(F['pl'].getlength(l) for l in ('П1', 'П2')) + ph * 0.2
            + max(F['pv'].getbbox(v, anchor='ls')[2] for v in vals)) / S + ph * 0.8


def _rows(n, rows, row_max, gap):
    """Как _layout, но с другой предельной высотой ряда и зазором: → (высота ряда, верх, высота постера)."""
    rows = max(rows or 0, n, 1)
    avail = H_MAX - HEAD - FOOT
    row = int(min(row_max, (avail + gap) / rows - gap))
    block = rows * (row + gap) - gap
    if row < row_max:
        return row, HEAD + (avail - block) // 2, H_MAX
    return row, HEAD, HEAD + block + FOOT


def _pair(it, league):
    """→ ((имя, цвет, аббр.) хозяев, (…) гостей); цвета гостей разведены с хозяевами, как у versus."""
    hn, hc, _, ha = _club(it['home'], league)
    an, ac, ac2, aa = _club(it['away'], league)
    return (hn, hc, ha), (an, vs._distinct(hc, ac, ac2), aa)


def _fav(o):
    """Фаворит линии: 0 — хозяева, 2 — гости, None — линии нет или кэфы равны."""
    if not o or o[0] == o[2]:
        return None
    return 0 if o[0] < o[2] else 2


def _rings(w, h, color, ctr, seed, fade='down', dim=0.5, period=28, glow=0.10):
    """Узор панели как versus._panel, но шаг колец задан в пикселях (period, база 1080) — одинаковый у панелей
    любой ширины; считаем в базовом размере и увеличиваем в S раз (как versus.render). → RGB w·S × h·S."""
    w, h = max(1, int(round(w))), max(1, int(round(h)))
    L = period * 15
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = ctr
    dx, dy = (x - cx) / L, (y - cy) / L
    ang = np.arctan2(dy, dx)
    rng = np.random.default_rng(seed)
    wob = sum(a * np.sin(k * ang + p) for a, k, p in zip(rng.uniform(.004, .012, 3), (2, 3, 5), rng.uniform(0, 6, 3)))
    r = (np.abs(dx) ** 3 + np.abs(dy) ** 3) ** (1 / 3) + wob
    ring = np.clip(np.sin(r * 2 * np.pi * 15) * 3, -1, 1)
    if fade is None:
        light = np.ones_like(x)
    else:
        t = y / h if fade == 'down' else 1 - y / h
        light = dim + (1.06 - dim) * vs._smooth(t * 1.15)
    light *= 1 + glow * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * (0.38 * L) ** 2))
    arr = np.clip(np.array(color, np.float32)[None, None] * (light * (1 + 0.075 * ring))[..., None], 0, 255)
    return Image.fromarray(arr.astype(np.uint8), 'RGB').resize((w * S, h * S), Image.BICUBIC)


def _poly_mask(size, pts):
    """Маска многоугольника (координаты уже в масштабе S) со сглаженным краем: рисуем вдвое крупнее."""
    m = Image.new('L', (size[0] * 2, size[1] * 2), 0)
    ImageDraw.Draw(m).polygon([(x * 2, y * 2) for x, y in pts], fill=255)
    return m.resize(size, Image.LANCZOS)


def _box_shadow(img, box, radius, blur=6, alpha=110, off=(3, 6)):
    """Мягкая тень под скруглённым прямоугольником (box в масштабе S)."""
    x0, y0, x1, y1 = box
    m = Image.new('L', (max(1, int(x1 - x0)), max(1, int(y1 - y0))), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, m.width - 1, m.height - 1), radius=int(radius), fill=255)
    _soft_shadow(img, m, (x0 + off[0] * S, y0 + off[1] * S), blur * S, alpha)


def _txt_sh(img, x, cy, text, f, fill, anchor='m', ref='Н', blur=5, alpha=150, off=(2, 4)):
    """_txt с мягкой тенью — для текста на цветной панели. Всё в масштабе S (off, blur — база). → ширина чернил."""
    l, t, r, b = f.getbbox(text, anchor='ls')
    _, rt, _, rb = f.getbbox(ref, anchor='ls')
    ox = x - l if anchor == 'l' else x - r if anchor == 'r' else x - (l + r) / 2
    base = cy - (rt + rb) / 2
    X0, Y0 = int(ox + l), int(base + t)
    tile = Image.new('L', (int(r - l) + 4, int(b - t) + 4), 0)
    ImageDraw.Draw(tile).text((ox - X0 + 2, base - Y0 + 2), text, font=f, fill=255, anchor='ls')
    _soft_shadow(img, tile, (X0 - 2 + off[0] * S, Y0 - 2 + off[1] * S), blur * S, alpha)
    return _txt(ImageDraw.Draw(img), x, cy, text, f, fill, anchor, ref)


def _glow(img, cx, cy, r, color, alpha=150):
    """Мягкое свечение цвета клуба (круг r, размытый) — под эмблему без панели. Всё в масштабе S."""
    m = int(r * 1.5)
    size = int(2 * (r + m))
    tile = Image.new('L', (size, size), 0)
    ImageDraw.Draw(tile).ellipse((m, m, m + 2 * r, m + 2 * r), fill=alpha)
    tile = tile.filter(ImageFilter.GaussianBlur(r * 0.5))
    lay = Image.new('RGBA', (size, size), tuple(color) + (0,))
    lay.putalpha(tile)
    img.alpha_composite(lay, (int(cx - size / 2), int(cy - size / 2)))


def _fit_room(text, name, wght, f, room):
    """Тот же шрифт, но меньше, пока чернила text шире room (масштаб S)."""
    while f.getbbox(text, anchor='ls')[2] - f.getbbox(text, anchor='ls')[0] > room and f.size > 12 * S:
        f = brand_kit.font(name, f.size - S, wght)
    return f


def _over(c, a, bg=BG):
    """Цвет c с непрозрачностью a поверх фона — ImageDraw на RGBA не смешивает, а заменяет пиксели."""
    return tuple(int(x * a + y * (1 - a)) for x, y in zip(c, bg)) + (255,)


def _ink_on(col):
    """Текст на панели цвета col: белый с тенью, на светлой (золото, бирюза…) — тёмный почти без тени.
    → (цвет, непрозрачность тени)."""
    return ((26, 22, 18), 40) if vs._lum(col) > 140 else ((255, 255, 255), 150)


def _pill_out(d, cx, cy, w, h, label, value, fl, fv, col):
    """Плашка-контур (не фаворит в style='fav'): обводка и цифры цветом акцента, приглушённо."""
    d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=int(h * .28),
                        outline=_over(col, 0.6), width=max(2, int(h * 0.05)), fill=_over((255, 255, 255), 0.03))
    gl = h * 0.2
    lw, vw = fl.getlength(label), fv.getbbox(value, anchor='ls')[2]
    x = cx - (lw + gl + vw) / 2
    _txt(d, x, cy, label, fl, _over(col, 0.5), 'l')
    _txt(d, x + lw + gl, cy, value, fv, _over(col, 0.85), 'l')


def _fonts(ab, tm, ph):
    return dict(ab=_cap(ALU, 900, ab * S), tm=_cap(OSW, 700, tm * S),
                pv=_cap(OSW, 600, ph * 0.48 * S), pl=_cap(MAN, 800, ph * 0.30 * S))


# ---------------------------------------------------------------- diagonal: панели встречаются под углом

def _st_diagonal(items, rows, league, acc):
    gap = 20
    R, top, H = _rows(len(items), rows, 232, gap)
    ph = min(46, max(32, R * 0.25))
    F = _fonts(min(80, R * 0.38), min(42, R * 0.20), ph)
    pill_w = _pill_w(F, ph, items)

    def paint(img):
        for i, it in enumerate(items):
            _diag(img, it, top + i * (R + gap), R, league, acc, F, ph, pill_w, i)
    return H, paint


def _diag(img, it, y0, R, league, acc, F, ph, pill_w, i):
    (hn, hc, ha), (an, ac, aa) = _pair(it, league)
    x0, x1 = MX, W - MX
    xc, s, gw = W / 2, R * 0.21, 5          # срез: сверху правее центра, снизу левее («/»), щель 2·gw
    cut = lambda y: xc + s - 2 * s * (y - y0) / R
    _soft_shadow(img, Image.new('L', ((x1 - x0) * S, R * S), 255), ((x0 + 9) * S, (y0 + 13) * S), 13 * S, 120)
    es = R * 0.80
    ex = (x0 + R * 0.56, x1 - R * 0.56)
    # хозяева: от левого края до среза; гости — от среза до правого
    for k, (col, team, ab, fade) in enumerate(((hc, hn, ha, 'down'), (ac, an, aa, 'up'))):
        if k == 0:
            tx0, tx1 = x0, int(xc + s + 1)
            pts = [(0, 0), (xc + s - gw - tx0, 0), (xc - s - gw - tx0, R), (0, R)]
        else:
            tx0, tx1 = int(xc - s - 1), x1
            pts = [(xc + s + gw - tx0, 0), (tx1 - tx0, 0), (tx1 - tx0, R), (xc - s + gw - tx0, R)]
        tile = _rings(tx1 - tx0, R, col, (ex[k] - tx0, R * 0.5), 31 + 7 * i + 11 * k, fade, dim=0.55)
        img.paste(tile, (tx0 * S, int(y0 * S)), _poly_mask(tile.size, [(x * S, y * S) for x, y in pts]))
        _emblem(img, team, ex[k] * S, (y0 + R * 0.5) * S, es * S, ab, col)

    o = it.get('odds')
    t = (it.get('time') or '').strip() or 'vs'
    ya = y0 + (R * 0.34 if o else R * 0.5)
    # время — тёмная «скошенная» плашка на срезе
    ft = F['tm']
    tw = ft.getbbox(t, anchor='ls')[2] / S
    capt = ft.size / S * 0.72
    bh = R * 0.36
    bw = tw + bh * 0.9
    sl = 2 * s * bh / R
    bx = cut(ya)
    poly = [(bx - bw / 2 + sl / 2, ya - bh / 2), (bx + bw / 2 + sl / 2, ya - bh / 2),
            (bx + bw / 2 - sl / 2, ya + bh / 2), (bx - bw / 2 - sl / 2, ya + bh / 2)]
    m = _poly_mask((int((bw + sl + 4) * S), int((bh + 4) * S)),
                   [((x - bx + (bw + sl) / 2 + 2) * S, (y - ya + bh / 2 + 2) * S) for x, y in poly])
    _soft_shadow(img, m, ((bx - (bw + sl) / 2 - 2 + 4) * S, (ya - bh / 2 - 2 + 7) * S), 7 * S, 140)
    lay = Image.new('RGBA', m.size, BG + (0,))
    lay.putalpha(m)
    img.alpha_composite(lay, (int((bx - (bw + sl) / 2 - 2) * S), int((ya - bh / 2 - 2) * S)))
    d = ImageDraw.Draw(img)
    _txt(d, bx * S, ya * S, t, ft, (250, 250, 250))
    # аббревиатуры белым с тенью: хозяева — правее своей эмблемы, гости — левее своей
    ax = (x0 + R * 1.06, x1 - R * 1.06)
    for k, (ab, col, anchor) in enumerate(((ha, hc, 'l'), (aa, ac, 'r'))):
        edge = bx - bw / 2 - sl / 2 - 16 if k == 0 else bx + bw / 2 + sl / 2 + 16
        room = abs(edge - ax[k]) * S
        ink, sha = _ink_on(col)
        _txt_sh(img, ax[k] * S, ya * S, ab, _fit_room(ab, ALU, 900, F['ab'], room), ink, anchor, alpha=sha)
    if o:
        yp = y0 + R * 0.77
        d = ImageDraw.Draw(img)
        xs = (ax[0] + pill_w / 2, cut(yp), ax[1] - pill_w / 2)
        for x, lab, v in zip(xs, ('П1', 'Х', 'П2'), o):
            box = ((x - pill_w / 2) * S, (yp - ph / 2) * S, (x + pill_w / 2) * S, (yp + ph / 2) * S)
            _box_shadow(img, box, ph * .28 * S, 5, 120, (2, 4))
            _pill(ImageDraw.Draw(img), x * S, yp * S, pill_w * S, ph * S, lab, '%.2f' % v, F['pl'], F['pv'], acc)


# ---------------------------------------------------------------- cards: сетка мини-«Versus» в 2 колонки

def _st_cards(items, rows, league, acc):
    n = len(items)
    slots = max(rows or 0, n, 1)
    cols = 1 if slots == 1 else 2
    grows = -(-slots // cols)
    gx = gy = 22
    cw = (W - 2 * MX - gx) / 2 if cols == 2 else 660
    ch_max = 380 if cols == 2 else 460
    avail = H_MAX - HEAD - FOOT
    ch = int(min(ch_max, (avail + gy) / grows - gy))
    block = grows * (ch + gy) - gy
    if ch < ch_max:
        top, H = HEAD + (avail - block) // 2, H_MAX
    else:
        top, H = HEAD, HEAD + block + FOOT
    pad = round(cw * 0.032)
    plh = min(44, max(30, ch * 0.135))
    F = _fonts(min(54, ch * 0.12), min(40, ch * 0.10), plh)
    F['vs'] = brand_kit.font(OSW, int(ch * 0.06) * S, 600)
    pill_w = min(_pill_w(F, plh, items), (cw - 2 * pad - 24) / 3)

    def paint(img):
        for i, it in enumerate(items):
            r, c = divmod(i, cols)
            x = MX + c * (cw + gx) if cols == 2 else (W - cw) / 2
            if cols == 2 and i == n - 1 and n % 2 == 1:            # последняя без пары — по центру
                x = (W - cw) / 2
            _card(img, it, x, top + r * (ch + gy), cw, ch, pad, plh, league, acc, F, pill_w, i)
    return H, paint


def _card(img, it, x0, y0, cw, ch, pad, plh, league, acc, F, pill_w, i):
    (hn, hc, ha), (an, ac, aa) = _pair(it, league)
    o = it.get('odds')
    d = ImageDraw.Draw(img)
    _box_shadow(img, (x0 * S, y0 * S, (x0 + cw) * S, (y0 + ch) * S), 18 * S, 12, 110, (6, 10))
    d.rounded_rectangle((x0 * S, y0 * S, (x0 + cw) * S, (y0 + ch) * S), radius=18 * S, fill=(33, 31, 37))
    pa = ch * (0.53 if o else 0.66)           # высота зоны панелей
    off = pa * 0.08
    gap = 6
    half = (cw - 2 * pad - gap) / 2
    es = min(half * 0.70, (pa - off) * 0.80)
    for k, (col, team, ab, fade) in enumerate(((hc, hn, ha, 'down'), (ac, an, aa, 'up'))):
        px = x0 + pad + k * (half + gap)
        py = y0 + pad + (off if k else 0)
        tile = _rings(half, pa - off, col, (half / 2, (pa - off) * 0.5), 41 + 7 * i + 13 * k, fade, dim=0.55,
                      period=24)
        _soft_shadow(img, Image.new('L', tile.size, 255), ((px + 5) * S, (py + 8) * S), 8 * S, 110)
        img.paste(tile, (int(px * S), int(py * S)))
        _emblem(img, team, (px + half / 2) * S, (py + (pa - off) / 2) * S, es * S, ab, col)
    # «vs» — маленький тёмный кружок на стыке панелей
    vr = ch * 0.068
    cx, cy = x0 + cw / 2, y0 + pad + pa / 2
    _box_shadow(img, ((cx - vr) * S, (cy - vr) * S, (cx + vr) * S, (cy + vr) * S), vr * S, 5, 140, (2, 4))
    d = ImageDraw.Draw(img)
    d.ellipse(((cx - vr) * S, (cy - vr) * S, (cx + vr) * S, (cy + vr) * S), fill=BG + (255,),
              outline=_over((255, 255, 255), 0.25), width=max(1, int(S * 1.2)))
    _txt(d, cx * S, (cy - vr * 0.06) * S, 'vs', F['vs'], (245, 245, 245), ref='v')
    # строка «АДМ   12:30   СПР»: аббревиатуры по центру своих панелей, время между ними
    yp = y0 + ch - pad - plh / 2 - 2
    yi = (y0 + pad + pa + (yp - plh / 2 if o else y0 + ch - pad)) / 2 + 2
    t = (it.get('time') or '').strip()
    if t:
        _txt(d, cx * S, yi * S, t, F['tm'], (250, 250, 250))
    tw = (F['tm'].getbbox(t, anchor='ls')[2] / S) if t else 0
    for k, (ab, col) in enumerate(((ha, hc), (aa, ac))):
        ax = x0 + pad + half / 2 + k * (half + gap)
        room = min(half - 12, 2 * (abs(cx - ax) - tw / 2 - 14)) * S
        _txt(d, ax * S, yi * S, ab, _fit_room(ab, ALU, 900, F['ab'], room), _readable(col) + (255,))
    if o:
        xs = (x0 + pad + pill_w / 2, cx, x0 + cw - pad - pill_w / 2)
        for x, lab, v in zip(xs, ('П1', 'Х', 'П2'), o):
            _pill(d, x * S, yp * S, pill_w * S, plh * S, lab, '%.2f' % v, F['pl'], F['pv'], acc)


# ---------------------------------------------------------------- center: эмблемы смотрят на колонку времени

def _st_center(items, rows, league, acc):
    gap = 16
    R, top, H = _rows(len(items), rows, 236, gap)
    F = dict(tm=_cap(OSW, 700, min(58, R * 0.27) * S), nm=_cap(OSW, 600, max(17, min(24, R * 0.105)) * S),
             ol=_cap(MAN, 800, max(11, min(14, R * 0.068)) * S), ov=_cap(OSW, 600, max(17, min(22, R * 0.105)) * S),
             vs=brand_kit.font(OSW, int(min(24, R * 0.12)) * S, 600))

    def paint(img):
        for i, it in enumerate(items):
            _center_row(img, it, top + i * (R + gap), R, league, acc, F, i)
    return H, paint


def _center_row(img, it, y0, R, league, acc, F, i):
    (hn, hc, ha), (an, ac, aa) = _pair(it, league)
    o = it.get('odds')
    xc = W / 2
    es = R * 0.66
    ex = (xc - 286, xc + 286)
    ey = y0 + R * 0.42
    half = int(xc - MX)
    # подложка: цвет клуба от края к центру гаснет — тёмная середина под временем
    xs = np.arange(half, dtype=np.float32)
    for k, (col, fade) in enumerate(((hc, 'down'), (ac, 'up'))):
        tile = _rings(half, R, col, ((ex[0] - MX) if k == 0 else (ex[1] - xc), R * 0.42), 51 + 7 * i + 9 * k, fade,
                      dim=0.55)
        u = xs / half if k == 0 else 1 - xs / half                  # 0 — внешний край, 1 — центр
        a = 1 - vs._smooth((u - 0.55) / 0.42)
        a = Image.fromarray((np.tile(a[None], (R, 1)) * 255).astype(np.uint8), 'L').resize(tile.size, Image.BILINEAR)
        tx = MX if k == 0 else int(xc)
        lay = tile.convert('RGBA')
        lay.putalpha(a)
        img.alpha_composite(lay, (tx * S, int(y0 * S)))
    d = ImageDraw.Draw(img)
    for k, (team, ab, col, name) in enumerate(((hn, ha, hc, hn), (an, aa, ac, an))):
        _emblem(img, team, ex[k] * S, ey * S, es * S, ab, col)
    # «П1 3.40 · Х 3.78 · П2 1.95» тонкой строкой под временем
    parts = []
    for lab, v in zip(('П1', 'Х', 'П2'), o or ()):
        parts += [(lab, F['ol'], (175, 173, 182)), ('  ', F['ol'], GREY), ('%.2f' % v, F['ov'], acc)]
        parts.append(('  ·  ', F['ov'], (130, 128, 136)))
    parts = parts[:-1]
    wsum = sum(f.getlength(tx) for tx, f, _ in parts)
    oh = max(wsum / S / 2 + 34, 120)
    # названия под эмблемами (длинное — в две строки по пробелу, иначе мельче); не заходят на строку линии
    for k, (name, col) in enumerate(((hn, hc), (an, ac))):
        nm = name.upper()
        ink, sha = _ink_on(col)
        room = 2 * min(ex[k] - MX - 10, xc - oh - ex[k]) if k == 0 else 2 * min(W - MX - 10 - ex[k], ex[k] - xc - oh)
        f = F['nm']
        yn = y0 + R * 0.88
        if f.getlength(nm) * 0.8 > room * S and ' ' in nm:
            a_, b_ = nm.split(' ', 1)
            fs = _fit_room(max(a_, b_, key=len), OSW, 600, brand_kit.font(OSW, int(f.size * 0.86), 600), room * S)
            lh = fs.size / S * 0.95
            yn = min(yn, y0 + R - lh * 0.5 - 2)
            _txt_sh(img, ex[k] * S, (yn - lh * 0.5) * S, a_, fs, ink, blur=4, alpha=sha)
            _txt_sh(img, ex[k] * S, (yn + lh * 0.5) * S, b_, fs, ink, blur=4, alpha=sha)
        else:
            _txt_sh(img, ex[k] * S, yn * S, nm, _fit_room(nm, OSW, 600, f, room * S), ink, blur=4, alpha=sha)
    d = ImageDraw.Draw(img)
    t = (it.get('time') or '').strip()
    yt = y0 + (R * 0.40 if o else R * 0.5)
    th = F['tm'].size / S * 0.72
    if t:
        _txt(d, xc * S, (yt - th * 0.05) * S, t, F['tm'], (250, 250, 250))
        _txt(d, xc * S, (yt - th * 0.5 - R * 0.11) * S, 'vs', F['vs'], acc, ref='v')
    else:
        _txt(d, xc * S, yt * S, 'vs', F['tm'], (250, 250, 250), ref='v')
    if o:
        x = xc * S - wsum / 2
        yo = y0 + R * 0.80
        for tx, f, c in parts:
            _txt(d, x, yo * S, tx, f, c, 'l', ref='0' if f is F['ov'] else 'Н') if tx.strip() else None
            x += f.getlength(tx)


# ---------------------------------------------------------------- fav: полосы с выделенным фаворитом

def _st_fav(items, rows, league, acc):
    R, top, H = _layout(len(items), rows)
    g = _geom(R)
    F = dict(ab=_cap(ALU, 900, g['ab'] * S), tm=_cap(OSW, 700, g['tm'] * S),
             vs=brand_kit.font(OSW, int(g['tm'] * 0.62) * S, 600), vs_big=brand_kit.font(OSW, int(g['tm'] * 1.1) * S, 600),
             pv=_cap(OSW, 600, g['ph'] * 0.48 * S), pl=_cap(MAN, 800, g['ph'] * 0.30 * S),
             tag=_cap(MAN, 800, max(10, R * 0.056) * S))
    pill_w = _pill_w(F, g['ph'], items)

    def paint(img):
        for i, it in enumerate(items):
            _fav_strip(img, it, top + i * (R + GAP), R, g, league, acc, F, pill_w, i)
    return H, paint


def _fav_strip(img, it, y0, R, g, league, acc, F, pill_w, i):
    (hn, hc, ha), (an, ac, aa) = _pair(it, league)
    o = it.get('odds')
    fv = _fav(o)
    pw = g['pw']
    for k, (x0, col, team, ab, fade) in enumerate(((MX, hc, hn, ha, 'down'), (W - MX - pw, ac, an, aa, 'up'))):
        big = fv is None or fv == 2 * k
        if fv is None:                                # линии нет — как strips: хозяева выше, гости ниже
            px0, top, w, h, dim, c = x0, y0 + (g['off'] if k else 0), pw, R - g['off'], 0.5, col
        elif big:                                     # фаворит: во всю высоту, ровный яркий цвет
            px0, top, w, h, dim, c = x0, y0, pw, R, 0.82, col
        else:                                         # андердог: меньше, приглушён к фону
            sh = round(R * 0.12)
            w = pw - 2 * sh
            px0 = x0 + (sh * 2 if k else 0)
            top, h, dim = y0 + sh, R - 2 * sh, 0.45
            c = tuple(int(a * 0.55 + b * 0.45) for a, b in zip(vs._mix(col, -0.1), BG))
        tile = _rings(w, h, c, (w / 2, h * 0.52), 11 + 7 * i + 12 * k, fade, dim=dim)
        _soft_shadow(img, Image.new('L', tile.size, 255), ((px0 + 9) * S, (top + 13) * S), 13 * S, 120)
        img.paste(tile, (int(px0 * S), int(top * S)))
        es = min(h * 0.84, w * 0.76) * (1 if big else 0.92)
        _emblem(img, team, (px0 + w / 2) * S, (top + h * 0.52) * S, es * S, ab, col)
        if fv is not None and big:                    # метка «ФАВОРИТ» — золотой уголок сверху панели
            d = ImageDraw.Draw(img)
            tag = 'ФАВОРИТ'
            tw = _spaced_w(tag, F['tag'], 1.2 * S) / S
            th = F['tag'].size / S * 1.25
            bx0 = px0 + (w - tw - 16 if k else 0)
            d.rectangle((bx0 * S, top * S, (bx0 + tw + 16) * S, (top + th) * S), fill=acc)
            _spaced(d, (bx0 + 8) * S, (top + th / 2) * S, tag, F['tag'], INK, 1.2 * S, anchor='l')

    d = ImageDraw.Draw(img)
    zc = (g['zx0'] + g['zx1']) / 2
    ya = y0 + (R * 0.33 if o else R * 0.5)
    t = (it.get('time') or '').strip()
    if t:
        vs_h = F['vs'].getbbox('vs', anchor='ls')
        vs_h = vs_h[3] - vs_h[1]
        gap = g['tm'] * 0.30
        top = ya - (vs_h + gap + g['tm']) / 2
        _txt(d, zc * S, (top + vs_h / 2) * S, 'vs', F['vs'], (245, 245, 245), ref='v')
        _txt(d, zc * S, (top + vs_h + gap + g['tm'] / 2) * S, t, F['tm'], (250, 250, 250))
        mid = F['tm'].getbbox(t, anchor='ls')[2] / S
    else:
        _txt(d, zc * S, ya * S, 'vs', F['vs_big'], (245, 245, 245), ref='v')
        mid = F['vs_big'].getlength('vs') / S
    room = ((g['zx1'] - g['zx0']) / 2 - mid / 2 - 16) * S
    for k, (abbr, col, x, anchor) in enumerate(((ha, hc, g['zx0'], 'l'), (aa, ac, g['zx1'], 'r'))):
        c = _readable(col) if fv is None or fv == 2 * k else _over(_readable(col), 0.45, (96, 94, 102))[:3]
        _txt(d, x * S, ya * S, abbr, _fit_room(abbr, ALU, 900, F['ab'], room), c + (255,), anchor)
    if o:
        yp = y0 + R * 0.79
        xs = (g['zx0'] + pill_w / 2, zc, g['zx1'] - pill_w / 2)
        for k, (x, lab, v) in enumerate(zip(xs, ('П1', 'Х', 'П2'), o)):
            if k == fv:
                _pill(d, x * S, yp * S, pill_w * S, g['ph'] * S, lab, '%.2f' % v, F['pl'], F['pv'], acc)
            else:
                _pill_out(d, x * S, yp * S, pill_w * S, g['ph'] * S, lab, '%.2f' % v, F['pl'], F['pv'], acc)


# ---------------------------------------------------------------- minimal: без панелей, свечение и крупное время

def _st_minimal(items, rows, league, acc):
    R, top, H = _rows(len(items), rows, 176, 0)
    F = dict(tm=_cap(OSW, 700, min(54, R * 0.30) * S), nm=_cap(OSW, 600, min(30, R * 0.165) * S),
             ol=_cap(MAN, 800, max(11, min(12, R * 0.07)) * S), ov=_cap(OSW, 600, min(28, R * 0.155) * S),
             vs=brand_kit.font(OSW, int(min(22, R * 0.12)) * S, 500))

    def paint(img):
        d = ImageDraw.Draw(img)
        for i in range(1, len(items)):
            y = top + i * R
            d.line((MX * S, y * S, (W - MX) * S, y * S), fill=_over((255, 255, 255), 0.09), width=max(1, int(S * 1.2)))
        for i, it in enumerate(items):
            _min_row(img, it, top + i * R, R, league, acc, F, i)
    return H, paint


def _min_row(img, it, y0, R, league, acc, F, i):
    (hn, hc, ha), (an, ac, aa) = _pair(it, league)
    o = it.get('odds')
    cy = y0 + R / 2
    d = ImageDraw.Draw(img)
    t = (it.get('time') or '').strip()
    x = MX + 6
    if t:
        _txt(d, x * S, cy * S, t, F['tm'], (250, 250, 250), 'l')
    # тонкая черта-разделитель после времени
    xl = MX + 178
    d.line((xl * S, (cy - R * 0.22) * S, xl * S, (cy + R * 0.22) * S), fill=_over(acc, 0.8), width=max(2, int(S * 1.5)))
    es = R * 0.60
    e1 = xl + 34 + es / 2
    e2 = e1 + es + 36
    for k, (team, ab, col, ex) in enumerate(((hn, ha, hc, e1), (an, aa, ac, e2))):
        _glow(img, ex * S, cy * S, es * 0.62 * S, _readable(col, 120), 175)
    for k, (team, ab, col, ex) in enumerate(((hn, ha, hc, e1), (an, aa, ac, e2))):
        _emblem(img, team, ex * S, cy * S, es * S, ab, col)
    d = ImageDraw.Draw(img)
    _txt(d, (e1 + e2) / 2 * S, cy * S, 'vs', F['vs'], (200, 198, 206), ref='v')
    # названия — две строки в цветах клубов; справа линия «П1 / Х / П2» колонками
    xn = e2 + es / 2 + 34
    ow = 72
    ox1 = W - MX - 4
    room = ((ox1 - 3 * ow - 18 if o else ox1) - xn) * S
    for k, (name, col) in enumerate(((hn, hc), (an, ac))):
        nm = name.upper()
        _txt(d, xn * S, (cy + (-1 if k == 0 else 1) * R * 0.15) * S, nm, _fit_room(nm, OSW, 600, F['nm'], room),
             _readable(col, 120) + (255,), 'l')
    if o:
        for k, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), o)):
            x = ox1 - (2 - k) * ow - ow / 2
            _txt(d, x * S, (cy - R * 0.17) * S, lab, F['ol'], GREY)
            _txt(d, x * S, (cy + R * 0.10) * S, '%.2f' % v, F['ov'], acc, ref='0')


# ---------------------------------------------------------------- итоги дня (render(..., results=True))
# items: [{home, away, sh, sa, mark: '' | 'ОТ' | 'Б' | 'ОТ/Б'}]. На месте времени — крупный счёт (цифра победителя
# белая, проигравшего — серая), под ним плашка «ОТ»/«Б»; вместо плашек линии — «ПОБЕДА» на стороне победителя.
# Победитель — в полном цвете, проигравший приглушён (панель ближе к фону, эмблема бледнее, аббревиатура серее) —
# в языке каждого макета: в fav победитель получает большую панель и уголок «ПОБЕДА» вместо «ФАВОРИТ».

WIN = 'ПОБЕДА'
RES_FOOT = 'ОТ — ПОБЕДА В ОВЕРТАЙМЕ · Б — ПО БУЛЛИТАМ'
LOSE_INK = (132, 130, 140)       # цифра проигравшего: заметно тише белой, но читается на тёмном


def _res(it):
    """→ (шайбы хозяев, шайбы гостей, метка ОТ/Б, победитель: 0 — хозяева, 2 — гости, None — ничья/нет счёта)."""
    try:
        sh, sa = int(it.get('sh') or 0), int(it.get('sa') or 0)
    except (TypeError, ValueError):
        sh = sa = 0
    mark = str(it.get('mark') or '').strip().upper()
    return sh, sa, mark, (0 if sh > sa else 2 if sa > sh else None)


def _lost(win, k):
    """k — 0 хозяева, 1 гости: эта сторона проиграла?"""
    return win is not None and win != 2 * k


def _dim(col, keep=0.62):
    """Цвет панели проигравшего: чуть темнее и ближе к фону — оттенок клуба узнаётся (мягче, чем андердог в fav)."""
    return tuple(int(a * keep + b * (1 - keep)) for a, b in zip(vs._mix(col, -0.08), BG))


def _dim_ink(col):
    """Аббревиатура / название проигравшего на тёмном — как у андердога в fav."""
    return _over(_readable(col), 0.5, (96, 94, 102))[:3]


def _fade(em, keep=0.68, sat=0.55):
    """Эмблема проигравшего: наполовину обесцвечена и чуть утоплена в фон; альфа та же (тень и края как были)."""
    a = em.getchannel('A')
    rgb = em.convert('RGB')
    rgb = Image.blend(rgb, rgb.convert('L').convert('RGB'), sat)
    rgb = Image.blend(Image.new('RGB', rgb.size, BG), rgb, keep)
    out = rgb.convert('RGBA')
    out.putalpha(a)
    return out


def _ink_w(t, f):
    l, _, r, _ = f.getbbox(t, anchor='ls')
    return r - l


def _score_w(sh, sa, f):
    """Ширина чернил счёта (масштаб S) — как у _score."""
    return _ink_w(str(sh), f) + _ink_w(':', f) + _ink_w(str(sa), f) + 2 * f.size * 0.07


def _score(d, x, cy, sh, sa, f, win, anchor='m', hi=(250, 250, 250), lo=LOSE_INK, sep=(168, 166, 176)):
    """Счёт «4:2» (масштаб S): цифры по строке цифр, двоеточие тише; anchor 'm' / 'l' / 'r'. → ширина чернил."""
    a, b = str(sh), str(sa)
    gap = f.size * 0.07
    wa, wc, wb = _ink_w(a, f), _ink_w(':', f), _ink_w(b, f)
    tot = wa + wc + wb + 2 * gap
    x0 = x - tot / 2 if anchor == 'm' else x if anchor == 'l' else x - tot
    _txt(d, x0, cy, a, f, lo if win == 2 else hi, 'l', ref='0')
    _txt(d, x0 + wa + gap, cy, ':', f, sep, 'l', ref='0')
    _txt(d, x0 + wa + gap + wc + gap, cy, b, f, lo if win == 0 else hi, 'l', ref='0')
    return tot


def _res_fonts(ab, sc, ph):
    """Кегли итогов (база): аббревиатуры, счёт, «ПОБЕДА» и «ОТ/Б» на плашках высотой ph."""
    return dict(ab=_cap(ALU, 900, ab * S), sc=_cap(OSW, 700, sc * S), win=_cap(OSW, 600, ph * 0.40 * S),
                mk=_cap(OSW, 700, ph * 0.44 * S))


def _win_w(F, h):
    """Ширина плашки «ПОБЕДА» (база) при высоте h."""
    return _spaced_w(WIN, F['win'], 2 * S) / S + h * 0.95


def _win_pill(d, cx, cy, w, h, F, fill):
    """«ПОБЕДА» — залитая плашка цвета акцента, как плашки линии (масштаб S)."""
    d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=int(h * .28), fill=fill)
    _spaced(d, cx, cy, WIN, F['win'], INK, 2 * S)


def _mark_w(F, h, mark):
    return max(h * 1.55, F['mk'].getbbox(mark, anchor='ls')[2] + h * 0.8)


def _mark_pill(d, cx, cy, h, mark, F, col, fill=BG):
    """«ОТ» / «Б» — тёмная плашка с обводкой и буквами цвета акцента (масштаб S)."""
    w = _mark_w(F, h, mark)
    d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=int(h * .28), fill=tuple(fill) + (255,),
                        outline=_over(col, 0.85), width=max(2, int(h * 0.05)))
    _txt(d, cx, cy, mark, F['mk'], col)


def _skew_plate(img, bx, by, bw, bh, sl):
    """Тёмная скошенная плашка на срезе (как у времени в diagonal); база."""
    poly = [(bx - bw / 2 + sl / 2, by - bh / 2), (bx + bw / 2 + sl / 2, by - bh / 2),
            (bx + bw / 2 - sl / 2, by + bh / 2), (bx - bw / 2 - sl / 2, by + bh / 2)]
    m = _poly_mask((int((bw + sl + 4) * S), int((bh + 4) * S)),
                   [((x - bx + (bw + sl) / 2 + 2) * S, (y - by + bh / 2 + 2) * S) for x, y in poly])
    _soft_shadow(img, m, ((bx - (bw + sl) / 2 - 2 + 4) * S, (by - bh / 2 - 2 + 7) * S), 7 * S, 140)
    lay = Image.new('RGBA', m.size, BG + (0,))
    lay.putalpha(m)
    img.alpha_composite(lay, (int((bx - (bw + sl) / 2 - 2) * S), int((by - bh / 2 - 2) * S)))


# strips — полосы: счёт на месте «vs/время», «ПОБЕДА» под аббревиатурой победителя, «ОТ/Б» — посередине вместо «Х»

def _rs_strips(items, rows, league, acc):
    R, top, H = _layout(len(items), rows)
    g = _geom(R)
    F = _res_fonts(g['ab'], min(70, R * 0.34), g['ph'])

    def paint(img):
        for i, it in enumerate(items):
            _strip_res(img, it, top + i * (R + GAP), R, g, league, acc, F, i)
    return H, paint


def _strip_res(img, it, y0, R, g, league, acc, F, i):
    league = str(it.get('league') or league).upper()          # у итогов прогнозов в одном постере обе лиги
    (hn, hc, ha), (an, ac, aa) = _pair(it, league)
    sh, sa, mark, win = _res(it)
    pw, off, ph = g['pw'], g['off'], g['ph']
    for k, (x0, top, col, team, ab, seed, fade) in enumerate(((MX, y0, hc, hn, ha, 11 + 7 * i, 'down'),
                                                               (W - MX - pw, y0 + off, ac, an, aa, 23 + 7 * i, 'up'))):
        lose = _lost(win, k)
        box = (x0 * S, top * S, (x0 + pw) * S, (top + R - off) * S)
        _panel(img, box, _dim(col) if lose else col, seed, fade, (0.5, 0.52))
        es = min((R - off) * 0.84, pw * 0.76) * (0.92 if lose else 1)
        _emblem(img, team, (x0 + pw / 2) * S, (top + (R - off) * 0.52) * S, es * S, ab, col, dim=lose)
    d = ImageDraw.Draw(img)
    zc = (g['zx0'] + g['zx1']) / 2
    ya = y0 + R * 0.36
    sw = _score(d, zc * S, ya * S, sh, sa, F['sc'], win) / S
    room = ((g['zx1'] - g['zx0']) / 2 - sw / 2 - 18) * S
    for k, (abbr, col, x, anchor) in enumerate(((ha, hc, g['zx0'], 'l'), (aa, ac, g['zx1'], 'r'))):
        c = _dim_ink(col) if _lost(win, k) else _readable(col)
        _txt(d, x * S, ya * S, abbr, _fit_room(abbr, ALU, 900, F['ab'], room), c + (255,), anchor)
    yp = y0 + R * 0.79
    if it.get('verdict'):                                     # итоги прогнозов: вместо «ПОБЕДА» — знак и наша ставка
        _pick_row(d, it, yp, g, ph, F, acc)
        return
    if win is not None:
        ww = _win_w(F, ph)
        x = g['zx0'] + ww / 2 if win == 0 else g['zx1'] - ww / 2
        _win_pill(d, x * S, yp * S, ww * S, ph * S, F, acc)
    if mark:
        _mark_pill(d, zc * S, yp * S, ph * S, mark, F, acc)


VERDICT_COL = {'win': (46, 160, 67), 'loss': (218, 54, 51), 'push': (72, 132, 226)}   # как ✅ / ❌ / ↩️ у Telegram


def _verdict_icon(d, cx, cy, h, kind):
    """Знак вердикта, нарисованный (в шрифтах постера нет эмодзи): «зашло» — зелёный квадрат с белой галочкой (✅),
    «минус» — красный крест (❌), «возврат» — синий квадрат со стрелкой назад (↩️). Масштаб S."""
    r, w = h / 2, max(2, int(h * 0.14))
    col = VERDICT_COL[kind]
    if kind == 'loss':
        k = r * 0.78
        for a, b in (((cx - k, cy - k), (cx + k, cy + k)), ((cx - k, cy + k), (cx + k, cy - k))):
            d.line((a, b), fill=col, width=int(w * 1.6))
        return
    d.rounded_rectangle((cx - r, cy - r, cx + r, cy + r), radius=int(h * 0.22), fill=col)
    if kind == 'win':
        d.line([(cx - r * 0.50, cy + r * 0.02), (cx - r * 0.12, cy + r * 0.42), (cx + r * 0.55, cy - r * 0.45)], fill=(255, 255, 255),
               width=w, joint='curve')
    else:
        d.arc((cx - r * 0.45, cy - r * 0.45, cx + r * 0.55, cy + r * 0.55), 270, 90, fill=(255, 255, 255), width=w)
        d.line([(cx + r * 0.05, cy + r * 0.55), (cx - r * 0.35, cy + r * 0.55)], fill=(255, 255, 255), width=w)
        d.line([(cx + r * 0.05, cy - r * 0.45), (cx - r * 0.45, cy - r * 0.45)], fill=(255, 255, 255), width=w)
        d.polygon([(cx - r * 0.62, cy - r * 0.45), (cx - r * 0.25, cy - r * 0.72), (cx - r * 0.25, cy - r * 0.18)], fill=(255, 255, 255))


def _pick_row(d, it, yp, g, ph, F, acc):
    """Нижняя строка полосы итогов прогнозов: знак вердикта, ставка (it['bet']), справа «ОТ»/«Б»."""
    x0, x1 = g['zx0'], g['zx1']
    ih = ph * 0.92
    _verdict_icon(d, (x0 + ih / 2) * S, yp * S, ih * S, it['verdict'])
    mark = str(it.get('mark') or '').strip().upper()
    right = x1
    if mark:
        mw = _mark_w(F, ph * 0.86 * S, mark) / S
        _mark_pill(d, (x1 - mw / 2) * S, yp * S, ph * 0.86 * S, mark, F, acc)
        right = x1 - mw - 12
    if 'bet' not in F:
        F['bet'] = _cap(MAN, 800, max(12, min(22, ph * 0.40)) * S)
    room = (right - (x0 + ih + 12)) * S
    text = str(it.get('bet') or '')
    f = _fit_room(text, MAN, 800, F['bet'], room)
    _txt(d, (x0 + ih + 12) * S, yp * S, text, f, (238, 236, 244) + (255,), 'l')


# diagonal — счёт в тёмной скошенной плашке на срезе, «ОТ/Б» — такая же плашка поменьше ниже по срезу

def _rs_diagonal(items, rows, league, acc):
    gap = 20
    R, top, H = _rows(len(items), rows, 232, gap)
    ph = min(46, max(32, R * 0.25))
    F = _res_fonts(min(80, R * 0.38), min(50, R * 0.235), ph)
    F['mk'] = _cap(OSW, 700, ph * 0.5 * S)

    def paint(img):
        for i, it in enumerate(items):
            _diag_res(img, it, top + i * (R + gap), R, league, acc, F, ph, i)
    return H, paint


def _diag_res(img, it, y0, R, league, acc, F, ph, i):
    (hn, hc, ha), (an, ac, aa) = _pair(it, league)
    sh, sa, mark, win = _res(it)
    x0, x1 = MX, W - MX
    xc, s, gw = W / 2, R * 0.21, 5
    cut = lambda y: xc + s - 2 * s * (y - y0) / R
    _soft_shadow(img, Image.new('L', ((x1 - x0) * S, R * S), 255), ((x0 + 9) * S, (y0 + 13) * S), 13 * S, 120)
    es = R * 0.80
    ex = (x0 + R * 0.56, x1 - R * 0.56)
    cols = []
    for k, (col, team, ab, fade) in enumerate(((hc, hn, ha, 'down'), (ac, an, aa, 'up'))):
        lose = _lost(win, k)
        pc = _dim(col) if lose else col
        cols.append(pc)
        if k == 0:
            tx0, tx1 = x0, int(xc + s + 1)
            pts = [(0, 0), (xc + s - gw - tx0, 0), (xc - s - gw - tx0, R), (0, R)]
        else:
            tx0, tx1 = int(xc - s - 1), x1
            pts = [(xc + s + gw - tx0, 0), (tx1 - tx0, 0), (tx1 - tx0, R), (xc - s + gw - tx0, R)]
        tile = _rings(tx1 - tx0, R, pc, (ex[k] - tx0, R * 0.5), 31 + 7 * i + 11 * k, fade, dim=0.55)
        img.paste(tile, (tx0 * S, int(y0 * S)), _poly_mask(tile.size, [(x * S, y * S) for x, y in pts]))
        _emblem(img, team, ex[k] * S, (y0 + R * 0.5) * S, es * S * (0.92 if lose else 1), ab, col, dim=lose)

    ya = y0 + R * 0.34
    f = F['sc']
    sw = _score_w(sh, sa, f) / S
    bh = R * 0.38
    bw = sw + bh * 0.95
    sl = 2 * s * bh / R
    bx = cut(ya)
    _skew_plate(img, bx, ya, bw, bh, sl)
    d = ImageDraw.Draw(img)
    _score(d, bx * S, ya * S, sh, sa, f, win)
    ax = (x0 + R * 1.06, x1 - R * 1.06)
    for k, (ab, col, anchor) in enumerate(((ha, hc, 'l'), (aa, ac, 'r'))):
        edge = bx - bw / 2 - sl / 2 - 16 if k == 0 else bx + bw / 2 + sl / 2 + 16
        room = abs(edge - ax[k]) * S
        ink, sha = _ink_on(cols[k])
        if _lost(win, k) and ink[0] > 128:
            ink, sha = (178, 176, 186), 110
        _txt_sh(img, ax[k] * S, ya * S, ab, _fit_room(ab, ALU, 900, F['ab'], room), ink, anchor, alpha=sha)
    yp = y0 + R * 0.77
    if win is not None:
        ww = _win_w(F, ph)
        x = ax[0] + ww / 2 if win == 0 else ax[1] - ww / 2
        box = ((x - ww / 2) * S, (yp - ph / 2) * S, (x + ww / 2) * S, (yp + ph / 2) * S)
        _box_shadow(img, box, ph * .28 * S, 5, 120, (2, 4))
        _win_pill(ImageDraw.Draw(img), x * S, yp * S, ww * S, ph * S, F, acc)
    if mark:
        mh = ph
        mw = _mark_w(F, mh * S, mark) / S
        bx2 = cut(yp)
        _skew_plate(img, bx2, yp, mw, mh, 2 * s * mh / R)
        _txt(ImageDraw.Draw(img), bx2 * S, yp * S, mark, F['mk'], acc)


# cards — счёт в строке «АББР счёт АББР», «ПОБЕДА» под панелью победителя, «ОТ/Б» по центру

def _rs_cards(items, rows, league, acc):
    n = len(items)
    slots = max(rows or 0, n, 1)
    cols = 1 if slots == 1 else 2
    grows = -(-slots // cols)
    gx = gy = 22
    cw = (W - 2 * MX - gx) / 2 if cols == 2 else 660
    ch_max = 380 if cols == 2 else 460
    avail = H_MAX - HEAD - FOOT
    ch = int(min(ch_max, (avail + gy) / grows - gy))
    block = grows * (ch + gy) - gy
    if ch < ch_max:
        top, H = HEAD + (avail - block) // 2, H_MAX
    else:
        top, H = HEAD, HEAD + block + FOOT
    pad = round(cw * 0.032)
    plh = min(44, max(30, ch * 0.135))
    F = _res_fonts(min(54, ch * 0.12), min(48, ch * 0.125), plh)
    F['vs'] = brand_kit.font(OSW, int(ch * 0.06) * S, 600)

    def paint(img):
        for i, it in enumerate(items):
            r, c = divmod(i, cols)
            x = MX + c * (cw + gx) if cols == 2 else (W - cw) / 2
            if cols == 2 and i == n - 1 and n % 2 == 1:
                x = (W - cw) / 2
            _card_res(img, it, x, top + r * (ch + gy), cw, ch, pad, plh, league, acc, F, i)
    return H, paint


def _card_res(img, it, x0, y0, cw, ch, pad, plh, league, acc, F, i):
    (hn, hc, ha), (an, ac, aa) = _pair(it, league)
    sh, sa, mark, win = _res(it)
    d = ImageDraw.Draw(img)
    _box_shadow(img, (x0 * S, y0 * S, (x0 + cw) * S, (y0 + ch) * S), 18 * S, 12, 110, (6, 10))
    d.rounded_rectangle((x0 * S, y0 * S, (x0 + cw) * S, (y0 + ch) * S), radius=18 * S, fill=(33, 31, 37))
    pa = ch * 0.53
    off = pa * 0.08
    gap = 6
    half = (cw - 2 * pad - gap) / 2
    es = min(half * 0.70, (pa - off) * 0.80)
    for k, (col, team, ab, fade) in enumerate(((hc, hn, ha, 'down'), (ac, an, aa, 'up'))):
        lose = _lost(win, k)
        px = x0 + pad + k * (half + gap)
        py = y0 + pad + (off if k else 0)
        tile = _rings(half, pa - off, _dim(col) if lose else col, (half / 2, (pa - off) * 0.5), 41 + 7 * i + 13 * k,
                      fade, dim=0.55, period=24)
        _soft_shadow(img, Image.new('L', tile.size, 255), ((px + 5) * S, (py + 8) * S), 8 * S, 110)
        img.paste(tile, (int(px * S), int(py * S)))
        _emblem(img, team, (px + half / 2) * S, (py + (pa - off) / 2) * S, es * S * (0.92 if lose else 1), ab, col,
                dim=lose)
    vr = ch * 0.068
    cx, cy = x0 + cw / 2, y0 + pad + pa / 2
    _box_shadow(img, ((cx - vr) * S, (cy - vr) * S, (cx + vr) * S, (cy + vr) * S), vr * S, 5, 140, (2, 4))
    d = ImageDraw.Draw(img)
    d.ellipse(((cx - vr) * S, (cy - vr) * S, (cx + vr) * S, (cy + vr) * S), fill=BG + (255,),
              outline=_over((255, 255, 255), 0.25), width=max(1, int(S * 1.2)))
    _txt(d, cx * S, (cy - vr * 0.06) * S, 'vs', F['vs'], (245, 245, 245), ref='v')
    yp = y0 + ch - pad - plh / 2 - 2
    yi = (y0 + pad + pa + yp - plh / 2) / 2 + 2
    tw = _score(d, cx * S, yi * S, sh, sa, F['sc'], win) / S
    for k, (ab, col) in enumerate(((ha, hc), (aa, ac))):
        ax = x0 + pad + half / 2 + k * (half + gap)
        room = min(half - 12, 2 * (abs(cx - ax) - tw / 2 - 14)) * S
        c = _dim_ink(col) if _lost(win, k) else _readable(col)
        _txt(d, ax * S, yi * S, ab, _fit_room(ab, ALU, 900, F['ab'], room), c + (255,))
    if win is not None:
        ww = min(_win_w(F, plh), half - 8)
        x = x0 + pad + half / 2 + (half + gap if win == 2 else 0)
        _win_pill(d, x * S, yp * S, ww * S, plh * S, F, acc)
    if mark:
        _mark_pill(d, cx * S, yp * S, plh * S, mark, F, acc, (33, 31, 37))


# center — счёт крупно в тёмной середине, «ОТ/Б» под ним строкой акцента; проигравший гаснет вместе с подложкой

def _rs_center(items, rows, league, acc):
    gap = 16
    R, top, H = _rows(len(items), rows, 236, gap)
    F = dict(sc=_cap(OSW, 700, min(60, R * 0.28) * S), nm=_cap(OSW, 600, max(17, min(24, R * 0.105)) * S),
             mk=_cap(OSW, 600, max(15, min(20, R * 0.095)) * S))

    def paint(img):
        for i, it in enumerate(items):
            _center_res(img, it, top + i * (R + gap), R, league, acc, F, i)
    return H, paint


def _center_res(img, it, y0, R, league, acc, F, i):
    (hn, hc, ha), (an, ac, aa) = _pair(it, league)
    sh, sa, mark, win = _res(it)
    xc = W / 2
    es = R * 0.66
    ex = (xc - 286, xc + 286)
    ey = y0 + R * 0.42
    half = int(xc - MX)
    xs = np.arange(half, dtype=np.float32)
    for k, (col, fade) in enumerate(((hc, 'down'), (ac, 'up'))):
        tile = _rings(half, R, _dim(col, 0.55) if _lost(win, k) else col,
                      ((ex[0] - MX) if k == 0 else (ex[1] - xc), R * 0.42), 51 + 7 * i + 9 * k, fade, dim=0.55)
        u = xs / half if k == 0 else 1 - xs / half
        a = 1 - vs._smooth((u - 0.55) / 0.42)
        a = Image.fromarray((np.tile(a[None], (R, 1)) * 255).astype(np.uint8), 'L').resize(tile.size, Image.BILINEAR)
        tx = MX if k == 0 else int(xc)
        lay = tile.convert('RGBA')
        lay.putalpha(a)
        img.alpha_composite(lay, (tx * S, int(y0 * S)))
    for k, (team, ab, col) in enumerate(((hn, ha, hc), (an, aa, ac))):
        lose = _lost(win, k)
        _emblem(img, team, ex[k] * S, ey * S, es * S * (0.92 if lose else 1), ab, col, dim=lose)
    d = ImageDraw.Draw(img)
    yt = y0 + R * (0.40 if mark else 0.46)
    sw = _score(d, xc * S, yt * S, sh, sa, F['sc'], win) / S
    oh = max(sw / 2 + 34, 110)
    for k, (name, col) in enumerate(((hn, hc), (an, ac))):
        nm = name.upper()
        ink, sha = _ink_on(_dim(col, 0.55) if _lost(win, k) else col)
        if _lost(win, k) and ink[0] > 128:
            ink, sha = (176, 174, 184), 150
        room = 2 * min(ex[k] - MX - 10, xc - oh - ex[k]) if k == 0 else 2 * min(W - MX - 10 - ex[k], ex[k] - xc - oh)
        f = F['nm']
        yn = y0 + R * 0.88
        if f.getlength(nm) * 0.8 > room * S and ' ' in nm:
            a_, b_ = nm.split(' ', 1)
            fs = _fit_room(max(a_, b_, key=len), OSW, 600, brand_kit.font(OSW, int(f.size * 0.86), 600), room * S)
            lh = fs.size / S * 0.95
            yn = min(yn, y0 + R - lh * 0.5 - 2)
            _txt_sh(img, ex[k] * S, (yn - lh * 0.5) * S, a_, fs, ink, blur=4, alpha=sha)
            _txt_sh(img, ex[k] * S, (yn + lh * 0.5) * S, b_, fs, ink, blur=4, alpha=sha)
        else:
            _txt_sh(img, ex[k] * S, yn * S, nm, _fit_room(nm, OSW, 600, f, room * S), ink, blur=4, alpha=sha)
    if mark:
        d = ImageDraw.Draw(img)
        ym = y0 + R * 0.78
        w = _spaced(d, xc * S, ym * S, mark, F['mk'], acc, 3 * S) / S
        for sgn in (-1, 1):                                 # тонкие черты по бокам: «— ОТ —»
            xa = xc + sgn * (w / 2 + 12)
            d.line((xa * S, ym * S, (xa + sgn * 26) * S, ym * S), fill=_over(acc, 0.6), width=max(2, int(S * 1.5)))


# fav — победитель как фаворит: панель во всю высоту, уголок «ПОБЕДА»; проигравший меньше и приглушён

def _rs_fav(items, rows, league, acc):
    R, top, H = _layout(len(items), rows)
    g = _geom(R)
    F = _res_fonts(g['ab'], min(70, R * 0.34), g['ph'])
    F['tag'] = _cap(MAN, 800, max(10, R * 0.056) * S)
    marks = any(_res(it)[2] for it in items)

    def paint(img):
        for i, it in enumerate(items):
            _fav_res(img, it, top + i * (R + GAP), R, g, league, acc, F, i, marks)
    return H, paint


def _fav_res(img, it, y0, R, g, league, acc, F, i, marks):
    (hn, hc, ha), (an, ac, aa) = _pair(it, league)
    sh, sa, mark, fv = _res(it)
    pw = g['pw']
    for k, (x0, col, team, ab, fade) in enumerate(((MX, hc, hn, ha, 'down'), (W - MX - pw, ac, an, aa, 'up'))):
        big = fv is None or fv == 2 * k
        if fv is None:
            px0, top, w, h, dim, c = x0, y0 + (g['off'] if k else 0), pw, R - g['off'], 0.5, col
        elif big:
            px0, top, w, h, dim, c = x0, y0, pw, R, 0.82, col
        else:
            sh_ = round(R * 0.12)
            w = pw - 2 * sh_
            px0 = x0 + (sh_ * 2 if k else 0)
            top, h, dim = y0 + sh_, R - 2 * sh_, 0.45
            c = tuple(int(a * 0.55 + b * 0.45) for a, b in zip(vs._mix(col, -0.1), BG))
        tile = _rings(w, h, c, (w / 2, h * 0.52), 11 + 7 * i + 12 * k, fade, dim=dim)
        _soft_shadow(img, Image.new('L', tile.size, 255), ((px0 + 9) * S, (top + 13) * S), 13 * S, 120)
        img.paste(tile, (int(px0 * S), int(top * S)))
        es = min(h * 0.84, w * 0.76) * (1 if big else 0.92)
        _emblem(img, team, (px0 + w / 2) * S, (top + h * 0.52) * S, es * S, ab, col, dim=not big)
        if fv is not None and big:
            d = ImageDraw.Draw(img)
            tw = _spaced_w(WIN, F['tag'], 1.2 * S) / S
            th = F['tag'].size / S * 1.25
            bx0 = px0 + (w - tw - 16 if k else 0)
            d.rectangle((bx0 * S, top * S, (bx0 + tw + 16) * S, (top + th) * S), fill=acc)
            _spaced(d, (bx0 + 8) * S, (top + th / 2) * S, WIN, F['tag'], INK, 1.2 * S, anchor='l')
    d = ImageDraw.Draw(img)
    zc = (g['zx0'] + g['zx1']) / 2
    ya = y0 + R * (0.40 if marks else 0.5)
    sw = _score(d, zc * S, ya * S, sh, sa, F['sc'], fv) / S
    room = ((g['zx1'] - g['zx0']) / 2 - sw / 2 - 18) * S
    for k, (abbr, col, x, anchor) in enumerate(((ha, hc, g['zx0'], 'l'), (aa, ac, g['zx1'], 'r'))):
        c = _readable(col) if fv is None or fv == 2 * k else _over(_readable(col), 0.45, (96, 94, 102))[:3]
        _txt(d, x * S, ya * S, abbr, _fit_room(abbr, ALU, 900, F['ab'], room), c + (255,), anchor)
    if mark:
        _mark_pill(d, zc * S, (y0 + R * 0.79) * S, g['ph'] * S, mark, F, acc)


# minimal — крупный счёт слева (на месте времени), «ОТ/Б» под ним; «ПОБЕДА» справа в строке победителя

def _rs_minimal(items, rows, league, acc):
    R, top, H = _rows(len(items), rows, 176, 0)
    ph = min(36, max(26, R * 0.23))
    F = dict(sc=_cap(OSW, 700, min(52, R * 0.29) * S), nm=_cap(OSW, 600, min(30, R * 0.165) * S),
             win=_cap(OSW, 600, ph * 0.42 * S), mk=_cap(OSW, 700, max(13, min(17, R * 0.10)) * S))

    def paint(img):
        d = ImageDraw.Draw(img)
        for i in range(1, len(items)):
            y = top + i * R
            d.line((MX * S, y * S, (W - MX) * S, y * S), fill=_over((255, 255, 255), 0.09), width=max(1, int(S * 1.2)))
        for i, it in enumerate(items):
            _min_res(img, it, top + i * R, R, league, acc, F, ph, i)
    return H, paint


def _min_res(img, it, y0, R, league, acc, F, ph, i):
    (hn, hc, ha), (an, ac, aa) = _pair(it, league)
    sh, sa, mark, win = _res(it)
    cy = y0 + R / 2
    d = ImageDraw.Draw(img)
    xl = MX + 178
    ys = cy - (R * 0.10 if mark else 0)
    sw = _score(d, (MX + 6) * S, ys * S, sh, sa, _fit_room('%d:%d' % (sh, sa), OSW, 700, F['sc'], 160 * S), win,
                'l') / S
    if mark:
        _spaced(d, (MX + 6 + sw / 2) * S, (cy + R * 0.25) * S, mark, F['mk'], acc, 3 * S)
    d.line((xl * S, (cy - R * 0.22) * S, xl * S, (cy + R * 0.22) * S), fill=_over(acc, 0.8), width=max(2, int(S * 1.5)))
    es = R * 0.60
    e1 = xl + 34 + es / 2
    e2 = e1 + es + 36
    for k, (col, ex) in enumerate(((hc, e1), (ac, e2))):
        lose = _lost(win, k)
        _glow(img, ex * S, cy * S, es * 0.62 * S, _readable(_dim(col) if lose else col, 120 if not lose else 70),
              90 if lose else 175)
    for k, (team, ab, col, ex) in enumerate(((hn, ha, hc, e1), (an, aa, ac, e2))):
        lose = _lost(win, k)
        _emblem(img, team, ex * S, cy * S, es * S * (0.9 if lose else 1), ab, col, dim=lose)
    d = ImageDraw.Draw(img)
    _txt(d, (e1 + e2) / 2 * S, cy * S, 'vs', brand_kit.font(OSW, int(min(22, R * 0.12)) * S, 500), (200, 198, 206),
         ref='v')
    xn = e2 + es / 2 + 34
    ox1 = W - MX - 4
    ww = _win_w(F, ph)
    room = (ox1 - ww - 20 - xn) * S
    for k, (name, col) in enumerate(((hn, hc), (an, ac))):
        nm = name.upper()
        yk = cy + (-1 if k == 0 else 1) * R * 0.15
        c = _dim_ink(col) if _lost(win, k) else _readable(col, 120)
        _txt(d, xn * S, yk * S, nm, _fit_room(nm, OSW, 600, F['nm'], room), c + (255,), 'l')
        if win == 2 * k:
            _win_pill(d, (ox1 - ww / 2) * S, yk * S, ww * S, ph * S, F, acc)


_RES = dict(strips=_rs_strips, diagonal=_rs_diagonal, cards=_rs_cards, center=_rs_center, fav=_rs_fav,
            minimal=_rs_minimal)


STYLES = ('strips', 'diagonal', 'cards', 'center', 'fav', 'minimal')
_STYLE = dict(strips=_st_strips, diagonal=_st_diagonal, cards=_st_cards, center=_st_center, fav=_st_fav,
              minimal=_st_minimal)


if __name__ == '__main__':
    demo = [dict(home='Адмирал', away='Спартак', time='12:30', odds=(3.40, 3.78, 1.95)),
            dict(home='Торпедо', away='Динамо Москва', time='19:00', odds=(2.12, 3.76, 3.00))]
    print(render(demo, 'out/matchday_vs_demo.jpg', league='KHL', date_title='пятница, 16 октября'))
