"""Послематчевый баннер одного прогноза в графике анимированного «Versus» (16.10.2026, просьба владельца: «на такой же
лад, с такой же графикой, как новые предматчевые», гифкой). Квадрат 1080×1080, те же колышущиеся панели клубов и
«парящие» эмблемы (плашки versus_anim — общий кэш с предматчевыми), те же шрифты и место марки.
Вместо даты/времени/линии — итог: счёт, наш прогноз, кэф и вердикт. Панель проигравшего бледнеет.

Три подачи (variant):
    'score'  — справа сверху вместо «АДМ vs СПР» крупный счёт «1 : 5» (цифры в цветах клубов, у проигравшего бледная),
               под ним «ФИНАЛ» и сокращения; слева снизу «ИТОГ · дата», прогноз, кэф и плашка «✓ ЗАШЁЛ» / «✕ НЕ ЗАШЁЛ»
    'abbr'   — сокращения на месте, рядом с каждым его шайбы («АДМ 1» / «СПР 5»); блок слева — как у 'score'
    'stamp'  — как 'score', но вердикт — штамп наискосок поверх панелей (неровные чернила), слева без плашки вердикта

    import postmatch_vs as pv
    pv.render('Адмирал', 'Спартак', 1, 5, 'out/pv.mp4', date='16 октября', pick='победа Спартака в основное время',
              kef=1.95, hit=True, variant='score', plates_dir='out/anim/plates', first=True)
mark: '' | 'ОТ' | 'Б'. hit: True — зашёл, False — не зашёл, None — возврат.
→ MP4 H.264 1080×1080, 30 fps, 4 с, без звука (Telegram показывает как GIF); first=True — .jpg первого кадра рядом.
Запуск из папки render.
"""
import os

import numpy as np
from PIL import Image, ImageDraw

import brand_kit
import versus
import versus_anim as va

W, H = versus.W, versus.H
SS = va.SS
GREEN = (38, 178, 92)
RED = (214, 52, 70)
GREY = (120, 124, 134)


def _faded(c):
    """Бледный цвет проигравшего: к серому и темнее (плашка рисуется этим цветом)."""
    g = c[0] * 0.299 + c[1] * 0.587 + c[2] * 0.114
    return tuple(int((c[k] * 0.25 + g * 0.75) * 0.62 + 10) for k in range(3))


def _verdict(hit):
    if hit is None:
        return 'ВОЗВРАТ', GREY
    return ('ЗАШЁЛ', GREEN) if hit else ('НЕ ЗАШЁЛ', RED)


def _sym(d, cx, cy, r, hit, fill, w):
    """Нарисованные ✓ / ✕ (шрифты знаков не нужны)."""
    if hit:
        d.line([(cx - r * 0.95, cy + r * 0.02), (cx - r * 0.28, cy + r * 0.66), (cx + r * 0.98, cy - r * 0.72)],
               fill=fill, width=int(w), joint='curve')
    elif hit is False:
        for s in (1, -1):
            d.line([(cx - r * 0.75, cy - r * 0.75 * s), (cx + r * 0.75, cy + r * 0.75 * s)], fill=fill, width=int(w))
    else:
        d.arc((cx - r, cy - r, cx + r, cy + r), 40, 320, fill=fill, width=int(w))


def _wrap(text, f, max_w):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if f.getlength(t) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    for k in range(len(lines) - 1):                      # предлог/союз не оставляем в конце строки
        ws = lines[k].split()
        if len(ws) > 1 and len(ws[-1]) <= 2:
            lines[k] = ' '.join(ws[:-1])
            lines[k + 1] = ws[-1] + ' ' + lines[k + 1]
    return lines


def _foreground(home, away, sh, sa, mark, league, date, pick, kef, hit, variant, colors):
    """Неподвижный слой 1080² × SS (RGBA): текст, плашки, марка — как у versus._draw_foreground, но итог."""
    S = SS
    (hn, hc, ha, hs), (an, ac, aa, as_), acc = versus._teams(home, away, league)
    hcol, acol = colors
    img = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    win = 'home' if sh > sa else 'away' if sa > sh else None
    ink_h = versus._mix(hc, 0.06) if win != 'away' else (150, 150, 158)
    ink_a = versus._mix(ac, 0.06) if win != 'home' else (150, 150, 158)
    AB = 'AlumniSans[wght].ttf'
    word, vcol = _verdict(hit)

    if variant == 'abbr':
        fa = min((versus._fit(t + ' 00', 340 * S, 155 * S, 900, AB) for t in (ha, aa)), key=lambda f: f.size)
        versus._text_ink(d, 684 * S, 36 * S, '%s %d' % (ha, sh), fa, ink_h + (255,), anchor='l')
        fv = brand_kit.font('Oswald[wght].ttf', 40 * S, 600)
        d.text((690 * S, 218 * S), 'vs', font=fv, fill=(245, 245, 245), anchor='lm')
        versus._text_ink(d, 1030 * S, 241 * S, '%s %d' % (aa, sa), fa, ink_a + (255,), anchor='r')
    else:
        fs = versus._fit('00:00', 346 * S, 215 * S, 900, AB)
        a, b = str(sh), str(sa)
        wa, wc, wb = fs.getlength(a), fs.getlength(':'), fs.getlength(b)
        gap = 18 * S
        x = (684 + 1030) / 2 * S - (wa + wc + wb + 2 * gap) / 2
        y = 52 * S
        versus._text_ink(d, x, y, a, fs, ink_h + (255,), anchor='l')
        versus._text_ink(d, x + wa + gap, y, ':', fs, (235, 235, 240, 255), anchor='l')
        versus._text_ink(d, x + wa + wc + 2 * gap, y, b, fs, ink_a + (255,), anchor='l')
        fl = brand_kit.font('Oswald[wght].ttf', 34 * S, 600)
        tail = {'ОТ': ' · ОВЕРТАЙМ', 'Б': ' · БУЛЛИТЫ'}.get(mark, '')
        d.text(((684 + 1030) / 2 * S, 312 * S), 'ФИНАЛ' + tail, font=fl, fill=(245, 245, 245), anchor='mm')
        fab = brand_kit.font('Oswald[wght].ttf', 30 * S, 600)
        d.text(((684 + 1030) / 2 * S, 358 * S), '%s — %s' % (ha, aa), font=fab, fill=(175, 173, 182), anchor='mm')

    # вертикальные подписи — как у Versus
    fsv = brand_kit.font('Manrope[wght].ttf', 17 * S, 600)
    versus._vertical(img, '#' + hs, 50 * S, 336 * S, fsv, hcol + (255,), ccw=True)
    versus._vertical(img, '#' + as_, 1030 * S, 744 * S, fsv, acol + (255,), ccw=False)

    # блок итога слева снизу (на месте даты / времени / линии)
    X0, X1 = 110, 450
    cx = (X0 + X1) / 2 * S
    top = 'ИТОГ · ' + date.upper() if date else 'ИТОГ МАТЧА'
    fd = versus._fit(top, (X1 - X0) * S, 30 * S, 600)
    d.text((cx, 712 * S), top, font=fd, fill=acc, anchor='mm')
    fl = brand_kit.font('Manrope[wght].ttf', 15 * S, 700)
    d.text((cx, 752 * S), 'НАШ ПРОГНОЗ', font=fl, fill=(170, 168, 176), anchor='mm')
    fp = brand_kit.font('Oswald[wght].ttf', 40 * S, 700)
    lines = _wrap(pick.upper(), fp, (X1 - X0) * S)
    while len(lines) > 2 and fp.size > 26 * S:
        fp = brand_kit.font('Oswald[wght].ttf', int(fp.size / S - 3) * S, 700)
        lines = _wrap(pick.upper(), fp, (X1 - X0) * S)
    lh = fp.size * 1.12
    y = 790 * S
    for ln in lines[:3]:
        d.text((cx, y), ln, font=fp, fill=(250, 250, 250), anchor='mm')
        y += lh
    y += 8 * S
    if kef:
        fo = brand_kit.font('Oswald[wght].ttf', 28 * S, 600)
        t = 'КЭФ %s' % ('%.2f' % kef).replace('.', ',')
        tw = fo.getlength(t) + 40 * S
        d.rounded_rectangle((cx - tw / 2, y, cx + tw / 2, y + 44 * S), radius=13 * S, fill=acc)
        d.text((cx, y + 23 * S), t, font=fo, fill=(24, 20, 14), anchor='mm')
        y += 58 * S
    if variant != 'stamp':
        fv = brand_kit.font('Oswald[wght].ttf', 40 * S, 700)
        tw = fv.getlength(word)
        r = 15 * S
        bw = tw + 2 * r + 22 * S + 52 * S
        y0, y1 = y, y + 62 * S
        d.rounded_rectangle((cx - bw / 2, y0, cx + bw / 2, y1), radius=31 * S, fill=vcol)
        sx = cx - bw / 2 + 26 * S + r
        _sym(d, sx, (y0 + y1) / 2, r, hit, (255, 255, 255), 6 * S)
        d.text((sx + r + 18 * S, (y0 + y1) / 2 + 1 * S), word, font=fv, fill=(255, 255, 255), anchor='lm')

    # марка канала — как у Versus
    fm = brand_kit.font('Oswald[wght].ttf', 24 * S, 700)
    tag = 'KXL' if league == 'KHL' else 'NHL'
    wj, wt = fm.getlength('JARVIS'), fm.getlength(tag)
    gx, bar = 14 * S, 3 * S
    xr = cx + (wj + gx * 2 + bar + wt) / 2
    yb = 1056 * S
    d.text((xr, yb), tag, font=fm, fill=acc, anchor='rs')
    d.rectangle((xr - wt - gx - bar, yb - 22 * S, xr - wt - gx, yb), fill=(220, 220, 225))
    d.text((xr - wt - 2 * gx - bar, yb), 'JARVIS', font=fm, fill=(245, 245, 245), anchor='rs')

    if variant == 'stamp':
        _stamp(img, word, vcol, hit)
    return img


def _stamp(img, word, col, hit):
    """Штамп наискосок по центру панелей: двойная рамка, слово и знак; чернила неровные (шум по альфе)."""
    S = SS
    w, h = 560, 170
    m = Image.new('L', (w * S, h * S), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((6 * S, 6 * S, (w - 6) * S, (h - 6) * S), radius=26 * S, outline=255, width=11 * S)
    d.rounded_rectangle((24 * S, 24 * S, (w - 24) * S, (h - 24) * S), radius=14 * S, outline=255, width=3 * S)
    f = versus._fit(word, (w - 180) * S, 92 * S, 700, 'Oswald[wght].ttf')
    tw = f.getlength(word)
    r = 34 * S
    x = (w * S - (tw + 2 * r + 26 * S)) / 2
    _sym(d, x + r, h * S / 2, r, hit, 255, 13 * S)
    d.text((x + 2 * r + 26 * S, h * S / 2 + 2 * S), word, font=f, fill=255, anchor='lm')
    a = np.asarray(m, np.float32) / 255
    rng = np.random.default_rng(7)
    nz = rng.random((h // 4 + 1, w // 4 + 1)).astype(np.float32)
    nz = np.asarray(Image.fromarray((nz * 255).astype(np.uint8)).resize((w * S, h * S), Image.BICUBIC), np.float32) / 255
    a = a * np.clip(0.55 + 0.6 * nz, 0, 1) * 0.92
    rgba = np.zeros((h * S, w * S, 4), np.uint8)
    rgba[..., :3] = col
    rgba[..., 3] = np.clip(a * 255, 0, 255).astype(np.uint8)
    st = Image.fromarray(rgba, 'RGBA').rotate(14, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(st, (int(540 * S - st.width / 2), int(470 * S - st.height / 2)))


def render(home, away, sh, sa, path_mp4, mark='', league='KHL', date='', pick='', kef=None, hit=True, variant='score',
           plates_dir='out/anim/plates', seconds=4, fps=30, target_mb=3.0, first=False, sheet=None, grain=va.GRAIN):
    (hn, hc, _, _), (an, ac, _, _), _ = versus._teams(home, away, league)
    win = 'home' if sh > sa else 'away' if sa > sh else None
    hcol = hc if win != 'away' else _faded(hc)
    acol = ac if win != 'home' else _faded(ac)
    plates = [va.get_plate(hn, 'home', league, hcol, plates_dir, seconds, fps),
              va.get_plate(an, 'away', league, acol, plates_dir, seconds, fps)]
    fg = _foreground(home, away, sh, sa, mark, league, date, pick, kef, hit, variant, (hc, ac))
    fg = np.asarray(fg.resize((W, H), Image.LANCZOS), np.float32)
    S0 = versus.S
    versus.S = SS
    try:
        bg = np.asarray(versus._background().convert('RGB').resize((W, H), Image.LANCZOS), np.float32)
    finally:
        versus.S = S0
    fg_rgb, fg_a = fg[..., :3], fg[..., 3] / 255
    scr = va._Canvas(grain).screen
    fa = fg_a[..., None]
    still = np.clip(va._Canvas.apply(bg * (1 - fa) + fg_rgb * fa, scr), 0, 255)
    bg = np.clip(va._Canvas.apply(bg, scr), 0, 255)
    fgp = still - bg * (1 - fa)
    readers = [va._read_plate(p, m) for p, m in plates]
    frames = []
    for _ in range(plates[0][1]['frames']):
        img = bg.copy()
        for (p, m), rd in zip(plates, readers):
            va._over_plate(img, next(rd), m['origin'])
        img = img * (1 - fa) + fgp
        frames.append(np.clip(img, 0, 255).astype(np.uint8))
    os.makedirs(os.path.dirname(path_mp4) or '.', exist_ok=True)
    va._encode_mp4(frames, path_mp4, fps, target_mb)
    base = os.path.splitext(path_mp4)[0]
    if first:
        Image.fromarray(frames[0]).save(base + '.jpg' if first is True else first, quality=92)
    if sheet:
        va._sheet(frames, base + '_frames.jpg' if sheet is True else sheet, fps)
    return path_mp4


if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/pv'
    for v in ('score', 'abbr', 'stamp'):
        print(render('Адмирал', 'Спартак', 1, 5, '%s/admiral_spartak_%s.mp4' % (out, v), date='16 октября',
                     pick='победа Спартака в основное время', kef=1.95, hit=True, variant=v, first=True))
