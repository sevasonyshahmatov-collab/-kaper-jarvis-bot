"""Анимированная вертикальная сторис «Прогноз дня» (15.10.2026, просьба владельца): 1080×1920, тот же стиль, что у
анимированного Versus (versus_anim) — панели клубов колышутся как флаг, эмблемы «парят», текст неподвижный и чёткий.

Раскладка (сверху вниз, «зигзагом», как у квадратного баннера):
    0…250      — зона интерфейса Telegram (полоска, аватар, имя канала): только ткань панели хозяев, без текста
    панель хозяев слева сверху (уходит за верх кадра), справа от неё — «ПРОГНОЗ ДНЯ», дата, время, МСК
    середина  — матч, «Прогноз:» и сам прогноз
    панель гостей справа снизу (уходит за низ кадра), слева от неё — «Кэф:», кэф крупно, линия П1/Х/П2 (если есть)
                и марка JARVIS | КХЛ
    1620…1920  — зона интерфейса (поле ответа): только ткань панели гостей
Панели — плашки versus_anim с геометрией сторис (STORY_GEOM): рисуются один раз на клуб/сторону/цвет (~1 мин)
и лежат в plates_dir рядом с баннерными; сборка сторис — только наложение и кодирование.
Длительность 8 с: плашки (цикл 4 с) проходят дважды, а блик по кэфу — один раз за 8 с, так что петля бесшовная.

    import story_anim
    story_anim.story('Торпедо', 'Динамо Москва', 'out/story.mp4', date='16 октября', time='19:00', league='KHL',
                     pick='итоговая победа Торпедо', kef=2.01, plates_dir='out/anim/plates', sheet=True)
→ MP4 H.264 yuv420p 1080×1920, 30 fps, без звука (≤ target_mb); sheet=True — контактный лист 6 кадров (_frames.jpg).
Запуск из папки render.
"""
import os
import time as _time

import numpy as np
from PIL import Image, ImageDraw

import brand_kit
import nhl
import versus
import versus_anim as va

SW, SH = 1080, 1920
SS = va.SS
SAFE_TOP, SAFE_BOTTOM = 250, 300          # зоны интерфейса Telegram в сторис: туда — только фон и ткань

# Геометрия плашек сторис: панель хозяев (80…700) уходит за верх кадра, гостей (380…1000) — за низ.
# Эмблемы — по центру видимой части панелей (вне зон интерфейса); центр колец смещён от эмблемы, как в баннере.
EMBLEM = 360
STORY_GEOM = {
    'home': va.side_geometry('story', 'home', (SW, SH), (80, 0, 700, 770), EMBLEM, (390, 512))._replace(
        ctr=(0.62, 0.58)),
    'away': va.side_geometry('story', 'away', (SW, SH), (380, 1150, 1000, SH), EMBLEM, (690, 1386))._replace(
        ctr=(0.40, 0.36)),
}
SECONDS = 8                                # длина сторис; плашки — цикл 4 с, повторяются SECONDS / 4 раза
PLATE_SECONDS = 4


def _f(name, size, wght):
    return brand_kit.font(name, size, wght)


def _spaced(d, x, y, text, f, fill, sp, anchor='m'):
    """Строка разрядкой; x — центр (anchor 'm'), левый ('l') или правый ('r') край, y — базовая линия."""
    ws = [f.getlength(c) for c in text]
    tw = sum(ws) + sp * (len(text) - 1)
    cx = x - tw / 2 if anchor == 'm' else (x if anchor == 'l' else x - tw)
    for c, w in zip(text, ws):
        d.text((cx, y), c, font=f, fill=fill, anchor='ls')
        cx += w + sp
    return tw


def _wrap_fit(text, box_w, line_h, max_lines=2, min_h=None, wght=700, name='Oswald[wght].ttf'):
    """Текст в одну строку высотой до line_h; если шрифт выходит мельче min_h — переносим по словам (до max_lines).
    → (шрифт, строки)."""
    min_h = min_h or line_h * 0.72
    f = versus._fit(text, box_w, line_h, wght, name)
    l, t, r, b = f.getbbox(text)
    if b - t >= min_h or ' ' not in text or max_lines < 2:
        return f, [text]
    words = text.split()
    best = None
    for k in range(1, len(words)):                       # разбиение на 2 строки с самым крупным шрифтом
        lines = [' '.join(words[:k]), ' '.join(words[k:])]
        ff = min((versus._fit(s, box_w, line_h * 0.86, wght, name) for s in lines), key=lambda q: q.size)
        if best is None or ff.size > best[0].size:
            best = (ff, lines)
    return best


def _team_label(ru, league):
    """Подпись вдоль панели — только по-русски (у НХЛ в баннере английское название; здесь — дивизион)."""
    if league == 'NHL':
        return '#%s · %s ДИВИЗИОН' % (ru.upper(), nhl.TEAMS[ru][5].upper())
    return '#' + versus._team(ru, league)[4]


def _kef_str(kef):
    return ('%.2f' % kef).replace('.', ',') if isinstance(kef, (int, float)) else str(kef).replace('.', ',')


def _background():
    """Фон 1080×1920: тот же тёмный BG, что у баннера, мягкий подсвет за текстом в середине."""
    yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32)
    glow = 1 + 0.10 * np.exp(-((xx - 640) ** 2 + (yy - 980) ** 2) / (2 * 430 ** 2))
    glow += 0.06 * np.exp(-((xx - 900) ** 2 + (yy - 470) ** 2) / (2 * 300 ** 2))
    return np.array(versus.BG, np.float32)[None, None] * glow[..., None]


def _foreground(home, away, hc, ac, acc, date, time, league, pick, kef, odds, tz):
    """Текст и марка на прозрачном RGBA в SS× → (rgb, alpha) 1080×1920. Возвращает и рамку кэфа (для блика)."""
    S = SS
    img = Image.new('RGBA', (SW * S, SH * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    white, grey, dim = (248, 248, 250, 255), (196, 194, 202, 255), (150, 148, 156, 255)
    accA = tuple(acc) + (255,)

    # вертикальные подписи вдоль панелей (как в баннере): хозяева — слева, снизу вверх; гости — справа, сверху вниз
    fs = _f('Manrope[wght].ttf', 17 * S, 600)
    versus._vertical(img, _team_label(home, league), 42 * S, 512 * S, fs, tuple(hc) + (255,), ccw=True)
    versus._vertical(img, _team_label(away, league), 1040 * S, 1386 * S, fs, tuple(ac) + (255,), ccw=False)

    # справа сверху: «ПРОГНОЗ ДНЯ», дата, время, МСК
    X0, X1 = 735, 1045
    cx = (X0 + X1) / 2
    fh = _f('Manrope[wght].ttf', 21 * S, 800)
    _spaced(d, cx * S, 368 * S, 'ПРОГНОЗ ДНЯ', fh, grey, 4 * S)
    d.line(((cx - 40) * S, 392 * S, (cx + 40) * S, 392 * S), fill=accA, width=3 * S)
    if date:
        fd = versus._fit(date.upper(), (X1 - X0) * S, 36 * S, 600)
        versus._text_ink(d, cx * S, 428 * S, date.upper(), fd, accA, anchor='m')
    if time:
        ft = versus._fit(time, (X1 - X0) * S, 96 * S, 700)
        versus._text_ink(d, cx * S, 486 * S, time, ft, white, anchor='m')
    fz = _f('Manrope[wght].ttf', 24 * S, 700)
    _spaced(d, cx * S, 640 * S, tz, fz, grey, 3 * S)

    # середина: матч, «Прогноз:», прогноз
    MX0, MX1 = 70, 1010
    mid = (MX0 + MX1) / 2
    match = '%s — %s' % (home.upper(), away.upper())
    fm = versus._fit(match, (MX1 - MX0) * S, 44 * S, 600)
    versus._text_ink(d, mid * S, 836 * S, match, fm, white, anchor='m')
    fl = _f('Manrope[wght].ttf', 26 * S, 700)
    _spaced(d, mid * S, 948 * S, 'ПРОГНОЗ:', fl, grey, 3 * S)
    fp, lines = _wrap_fit(pick.upper(), (MX1 - MX0) * S, 84 * S)
    if len(lines) == 1:
        versus._text_ink(d, mid * S, 978 * S, lines[0], fp, accA, anchor='m')
    else:
        lh = fp.getbbox('ЁЙ')[3] - fp.getbbox('Н')[1]
        y = 970 * S
        for s in lines:
            versus._text_ink(d, mid * S, y, s, fp, accA, anchor='m')
            y += lh + 10 * S

    # слева снизу: «Кэф:», кэф, линия, марка
    KX0, KX1 = 40, 350
    kx = (KX0 + KX1) / 2
    oy = 0 if odds else 34                              # без линии блок ниже — к центру эмблемы гостей
    _spaced(d, kx * S, (1232 + oy) * S, 'КЭФ:', fl, grey, 3 * S)
    ks = _kef_str(kef)
    fk = versus._fit(ks, (KX1 - KX0) * S, 132 * S, 700)
    l, t, r, b = fk.getbbox(ks)
    ky = 1258 + oy
    kbox = (kx - (r - l) / S / 2 - 16, ky - 12, kx + (r - l) / S / 2 + 16, ky + (b - t) / S + 12)
    versus._text_ink(d, kx * S, ky * S, ks, fk, accA, anchor='m')
    ym = 1452 + oy
    if odds:
        fo = _f('Oswald[wght].ttf', 28 * S, 600)
        fol = _f('Manrope[wght].ttf', 15 * S, 700)
        pw, gap, y0 = 92, 12, 1440
        x = kx - (3 * pw + 2 * gap) / 2
        S0 = versus.S
        versus.S = S                                     # _pill отступает подпись на 10·versus.S
        try:
            for lab, v in zip(('П1', 'Х', 'П2'), odds):
                versus._pill(d, (x * S, y0 * S, (x + pw) * S, (y0 + 44) * S), _kef_str(v), lab, fo, fol, accA,
                             (24, 20, 14))
                x += pw + gap
        finally:
            versus.S = S0
        ym = 1556
    # марка канала — как в баннере: JARVIS | КХЛ
    fmk = _f('Oswald[wght].ttf', 34 * S, 700)
    tag = 'КХЛ' if league == 'KHL' else 'НХЛ'
    wj, wt = fmk.getlength('JARVIS'), fmk.getlength(tag)
    gx, bar = 18 * S, 4 * S
    xr = kx * S + (wj + gx * 2 + bar + wt) / 2
    yb = (ym + 34) * S
    d.text((xr, yb), tag, font=fmk, fill=accA, anchor='rs')
    d.rectangle((xr - wt - gx - bar, yb - 31 * S, xr - wt - gx, yb), fill=(220, 220, 225, 255))
    d.text((xr - wt - 2 * gx - bar, yb), 'JARVIS', font=fmk, fill=white, anchor='rs')

    fg = np.asarray(img.resize((SW, SH), Image.LANCZOS), np.float32)
    return fg[..., :3], fg[..., 3] / 255, tuple(int(round(v)) for v in kbox)


def _sheen(frame, fg_a, box, p, acc):
    """Блик по цифрам кэфа: узкая светлая полоса наискосок проходит слева направо (p ∈ [0, 1]), только по тексту."""
    x0, y0, x1, y1 = box
    out = frame.copy()
    reg = out[y0:y1, x0:x1].astype(np.float32)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    pos = x0 - 120 + p * (x1 - x0 + 240)
    band = np.exp(-(((xx + (yy - y0) * 0.35) - pos) / 34) ** 2)
    k = (band * fg_a[y0:y1, x0:x1] * np.sin(np.pi * p) * 0.75)[..., None]
    reg = reg + (255 - reg) * k * 0.9
    out[y0:y1, x0:x1] = np.clip(reg, 0, 255).astype(np.uint8)
    return out


def story(home, away, path_mp4, date='', time='', league='KHL', pick='', kef='', odds=None,
          plates_dir='out/anim/plates', tz='МСК', fps=30, target_mb=6.5, sheet=None, grain=va.GRAIN):
    """Сторис «Прогноз дня» → path_mp4 (1080×1920, 8 с, H.264). odds=(П1, Х, П2) — линия плашками под кэфом.
    sheet — путь контактного листа .jpg (True — рядом, 6 кадров). Недостающие плашки дорисует в plates_dir.
    → dict(path, seconds, mb, render_s, plates_s)."""
    t0 = _time.time()
    (hn, hc, _, _), (an, ac, _, _), acc = versus._teams(home, away, league)
    plates = [va.get_plate(hn, 'home', league, hc, plates_dir, PLATE_SECONDS, fps, geom=STORY_GEOM['home']),
              va.get_plate(an, 'away', league, ac, plates_dir, PLATE_SECONDS, fps, geom=STORY_GEOM['away'])]
    t1 = _time.time()
    cv = va._Canvas(grain, size=(SW, SH))
    fg_rgb, fg_a, kbox = _foreground(hn, an, hc, ac, acc, date, time, league, pick, kef, odds, tz)
    fa = fg_a[..., None]
    bg = _background()
    # как versus_anim.compose: текст поверх фона с зерном «на смешанный цвет», вклад текста — с предумножением
    still = np.clip(va._Canvas.apply(bg * (1 - fa) + fg_rgb * fa, cv.screen), 0, 255)
    bg = np.clip(va._Canvas.apply(bg, cv.screen), 0, 255)
    fgp = still - bg * (1 - fa)
    readers = [va._read_plate(p, m) for p, m in plates]
    base = []
    for _ in range(plates[0][1]['frames']):
        img = bg.copy()
        for (p, m), rd in zip(plates, readers):          # хозяева, потом гости поверх
            va._over_plate(img, next(rd), m['origin'])
        img = img * (1 - fa) + fgp
        base.append(np.clip(img, 0, 255).astype(np.uint8))
    # 8 с = плашки дважды; блик по кэфу — один раз за петлю (5,0…6,2 с), в начале и в конце петли его нет
    n = int(round(SECONDS * fps))
    s0, s1 = int(5.0 * fps), int(6.2 * fps)
    frames = []
    for i in range(n):
        f = base[i % len(base)]
        if s0 <= i < s1:
            f = _sheen(f, fg_a, kbox, (i - s0) / (s1 - s0 - 1), acc)
        frames.append(f)
    os.makedirs(os.path.dirname(path_mp4) or '.', exist_ok=True)
    va._encode_mp4(frames, path_mp4, fps, target_mb)
    if sheet:
        va._sheet(frames, os.path.splitext(path_mp4)[0] + '_frames.jpg' if sheet is True else sheet, fps,
                  size=360)
    t2 = _time.time()
    return {'path': path_mp4, 'seconds': n / fps, 'mb': os.path.getsize(path_mp4) / 1e6,
            'render_s': round(t2 - t0, 1), 'plates_s': round(t1 - t0, 1)}


if __name__ == '__main__':
    print(story('Торпедо', 'Динамо Москва', 'out/anim/story_torpedo_dinamo.mp4', date='16 октября', time='19:00',
                league='KHL', pick='итоговая победа Торпедо', kef=2.01, sheet=True))
