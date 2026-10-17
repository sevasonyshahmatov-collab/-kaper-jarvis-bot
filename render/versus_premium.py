"""«Versus» в премиальной подаче (14.10.2026, проба по просьбе владельца): та же раскладка, что у versus.py, но
глянец — панели со скруглением, золотой окантовкой и бликом, эмблемы с отблеском, аббревиатуры и цифры
градиентом «металл/стекло», золотые плашки линии, цветной отсвет клубов на тёмном фоне, без «холста».

    import versus_premium
    versus_premium.render('Северсталь', 'СКА', 'out/vsp.jpg', date='13 октября', time='19:00', odds=(2.60, 4.20, 2.35))
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import brand_kit
import nhl
import poster
import versus
from versus import S, W, H, _fit, _mix, _panel, _team, _distinct, _vertical

BG = (11, 11, 15)
GOLD_HI, GOLD, GOLD_LO = (255, 236, 170), (232, 186, 82), (150, 104, 28)


def _vgrad(h, stops):
    """Вертикальный градиент h×1×3 по точкам [(доля 0..1, (r, g, b)), …]."""
    t = np.linspace(0, 1, h, dtype=np.float32)
    pos = [p for p, _ in stops]
    return np.stack([np.interp(t, pos, [c[i] for _, c in stops]) for i in range(3)], -1)[:, None, :]


def _grad_text(img, x, y, text, f, stops, anchor='l', shadow=150, glow=None):
    """Текст с вертикальным градиентом (верх чернил — y). anchor: 'l' / 'r' / 'm' по чернилам."""
    l, t, r, b = f.getbbox(text)
    pad = int(f.size * .25)
    w, h = r - l + 2 * pad, b - t + 2 * pad
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).text((pad - l, pad - t), text, font=f, fill=255)
    ox = {'l': x - pad, 'r': x - w + pad, 'm': x - w / 2}[anchor]
    oy = y - pad
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        sh.putalpha(m.point(lambda v: v * shadow // 255))
        sh = sh.filter(ImageFilter.GaussianBlur(max(2, f.size // 18)))
        img.alpha_composite(sh, (int(ox + f.size * .02), int(oy + f.size * .05)))
    if glow:
        gl = Image.new('RGBA', (w, h), glow + (0,))
        gl.putalpha(m.point(lambda v: v * 50 // 255).filter(ImageFilter.GaussianBlur(f.size // 7)))
        img.alpha_composite(gl, (int(ox), int(oy)))
    ink0, ink1 = pad / h, (h - pad) / h
    st = [(ink0 + (ink1 - ink0) * p, c) for p, c in stops]
    col = np.broadcast_to(_vgrad(h, [(0, stops[0][1])] + st + [(1, stops[-1][1])]), (h, w, 3)).astype(np.uint8)
    tile = Image.fromarray(np.ascontiguousarray(col), 'RGB').convert('RGBA')
    tile.putalpha(m)
    img.alpha_composite(tile, (int(ox), int(oy)))


def _glass(c):
    """Стекло: светлый верх, резкий переход у середины, глубокий низ."""
    return [(0, _mix(c, .45)), (.46, _mix(c, .16)), (.5, c), (1, _mix(c, -.28))]


def _metal(lo, mid, hi):
    return [(0, hi), (.45, mid), (.55, lo), (1, mid)]


def _round_mask(w, h, r):
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    return m


def _gloss_panel(pn, r):
    """Блик и объём панели: светлый верх, диагональный «зайчик», светлая кромка сверху/слева, тень снизу/справа."""
    w, h = pn.size
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.asarray(pn).astype(np.float32)
    top = 0.20 * np.clip(1 - y / (h * .42), 0, 1) ** 1.6
    band = 0.13 * np.exp(-((x * .55 - y * .85 + h * .18) ** 2) / (2 * (w * .07) ** 2))
    band2 = 0.06 * np.exp(-((x * .55 - y * .85 + h * .02) ** 2) / (2 * (w * .025) ** 2))
    lift = (top + band + band2)[..., None]
    a = a + (255 - a) * lift
    e = 3 * S
    a[:e] = a[:e] * .55 + 255 * .45
    a[:, :e] = a[:, :e] * .7 + 255 * .3
    a[-e:] *= .72
    a[:, -e:] *= .78
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    out.putalpha(_round_mask(w, h, r))
    return out


def _gold_frame(img, box, r, wpx):
    """Золотая окантовка панели: градиент от светлого золота слева сверху к тёмному справа снизу."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, outline=255, width=wpx)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = np.clip((xx / w + yy / h) / 2, 0, 1)
    sheen = np.exp(-((t - .22) ** 2) / .004) * .8 + np.exp(-((t - .7) ** 2) / .01) * .35
    cols = [np.interp(t, [0, .5, 1], [GOLD_HI[i], GOLD[i], GOLD_LO[i]]) for i in range(3)]
    arr = np.stack(cols, -1)
    arr = arr + (255 - arr) * np.clip(sheen, 0, 1)[..., None]
    tile = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    tile.putalpha(m)
    img.alpha_composite(tile, (x0, y0))


def _emblem_gloss(team, size):
    em = poster._emblem(team, size)
    w, h = em.size
    a = np.asarray(em).astype(np.float32)
    y = np.arange(h, dtype=np.float32)[:, None, None]
    lift = 0.22 * np.clip(1 - y / (h * .5), 0, 1) ** 1.3
    a[..., :3] = a[..., :3] + (255 - a[..., :3]) * lift
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def _pill_gold(img, box, text, f, stops, txt):
    x0, y0, x1, y1 = (int(v) for v in box)
    w, h = x1 - x0, y1 - y0
    r = int(h * .3)
    sh = Image.new('RGBA', (w + 60 * S, h + 60 * S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((30 * S, 36 * S, 30 * S + w, 36 * S + h), radius=r, fill=(0, 0, 0, 150))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9 * S)), (x0 - 30 * S, y0 - 30 * S))
    col = np.broadcast_to(_vgrad(h, stops), (h, w, 3)).astype(np.uint8)
    tile = Image.fromarray(np.ascontiguousarray(col), 'RGB').convert('RGBA')
    d = ImageDraw.Draw(tile)
    d.rounded_rectangle((1, 1, w - 2, h - 2), radius=r, outline=(255, 248, 220, 200), width=max(1, S))
    tile.putalpha(_round_mask(w, h, r))
    img.alpha_composite(tile, (x0, y0))
    ImageDraw.Draw(img).text(((x0 + x1) / 2, (y0 + y1) / 2 + 1 * S), text, font=f, fill=txt, anchor='mm')


def _hairline(img, cx, y, half, color):
    w, h = int(half * 2), max(2, S)
    t = np.linspace(-1, 1, w, dtype=np.float32)
    al = (np.clip(1 - np.abs(t), 0, 1) ** .7 * 230).astype(np.uint8)
    tile = Image.new('RGBA', (w, h), color + (0,))
    tile.putalpha(Image.fromarray(np.repeat(al[None, :], h, 0), 'L'))
    img.alpha_composite(tile, (int(cx - half), int(y)))


def render(home, away, path, date='', time='', odds=None, league='KHL', tz='время московское', fade=('down', 'up')):
    if league == 'NHL':
        nhl.register()
    hn, hc, _, ha, hs = _team(home, league)
    an, ac, ac2, aa, as_ = _team(away, league)
    ac = _distinct(hc, ac, ac2)
    acc = poster.ACC if league == 'KHL' else nhl.ICE
    acc_stops = ([(0, GOLD_HI), (.45, GOLD), (.55, (214, 158, 52)), (1, GOLD_LO)] if league == 'KHL' else
                 [(0, _mix(acc, .6)), (.45, acc), (.55, _mix(acc, -.12)), (1, _mix(acc, -.42))])

    # фон: глубокий графит, цветной отсвет клубов, мягкая виньетка, тонкое зерно
    g = np.mgrid[0:H, 0:W].astype(np.float32)
    bg = np.broadcast_to(np.array(BG, np.float32), (H, W, 3)).copy()
    for (cx, cy, rad), col in (((330, 300, 420), hc), ((760, 780, 420), ac)):
        k = 0.30 * np.exp(-((g[1] - cx) ** 2 + (g[0] - cy) ** 2) / (2 * rad ** 2))
        bg += (np.array(col, np.float32) - bg) * k[..., None]
    vign = 1 - 0.35 * np.clip(np.hypot(g[1] / W - .5, g[0] / H - .5) / .72, 0, 1) ** 2
    bg *= vign[..., None]
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), 'RGB').resize((W * S, H * S), Image.BICUBIC)
    img = img.convert('RGBA')

    P1 = (100, 26, 620, 672)       # от краёв картинки отступ — золотая рамка видна целиком
    P2 = (460, 408, 980, 1054)
    R = 26 * S
    for (x0, y0, x1, y1), col, emb, seed, ctr, fd in ((P1, hc, hn, 11, (0.62, 0.42), fade[0]),
                                                       (P2, ac, an, 23, (0.40, 0.55), fade[1])):
        w, h = (x1 - x0) * S, (y1 - y0) * S
        pn = _panel(w // S, h // S, col, (ctr[0] * (w // S), ctr[1] * (h // S)), seed, fd, dim=0.5)
        pn = Image.blend(pn, pn.filter(ImageFilter.GaussianBlur(2)), .6).resize((w, h), Image.BICUBIC)   # кольца мягче
        sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((x0 * S + 18 * S, y0 * S + 30 * S, x1 * S + 18 * S, y1 * S + 30 * S),
                                             radius=R, fill=(0, 0, 0, 175))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(34 * S)))
        img.alpha_composite(_gloss_panel(pn, R), (x0 * S, y0 * S))
        _gold_frame(img, (x0 * S, y0 * S, x1 * S, y1 * S), R, 3 * S)
        em = _emblem_gloss(emb, 380 * S)
        cx, cy = (x0 + x1) / 2 * S, ((y0 + y1) / 2 + 6) * S
        es = Image.new('RGBA', img.size, (0, 0, 0, 0))
        es.paste(Image.new('RGBA', em.size, _mix(col, -.7) + (190,)),
                 (int(cx - em.width / 2 + 12 * S), int(cy - em.height / 2 + 28 * S)), em.getchannel('A'))
        img.alpha_composite(es.filter(ImageFilter.GaussianBlur(30 * S)))
        img.alpha_composite(em, (int(cx - em.width / 2), int(cy - em.height / 2)))

    # аббревиатуры «стеклом», vs — золотом
    AB = 'AlumniSans[wght].ttf'
    fa = min((_fit(t, 340 * S, 155 * S, 900, AB) for t in (ha, aa)), key=lambda f: f.size)
    _grad_text(img, 684 * S, 36 * S, ha, fa, _glass(_mix(hc, .04)), 'l', glow=hc)
    fv = brand_kit.font('Oswald[wght].ttf', 40 * S, 600)
    vb = fv.getbbox('vs')
    _grad_text(img, 690 * S, 218 * S - (vb[3] - vb[1]) // 2, 'vs', fv, acc_stops, 'l', shadow=120)
    _grad_text(img, 1030 * S, 241 * S, aa, fa, _glass(_mix(ac, .04)), 'r', glow=ac)

    fs = brand_kit.font('Manrope[wght].ttf', 17 * S, 600)
    _vertical(img, '#' + hs, 50 * S, 336 * S, fs, _mix(hc, .2) + (255,), ccw=True)
    _vertical(img, '#' + as_, 1030 * S, 744 * S, fs, _mix(ac, .2) + (255,), ccw=False)

    # дата, время, линия
    X0, X1 = 130, 430
    cxm = (X0 + X1) / 2 * S
    dy = 0 if odds else 90
    d = ImageDraw.Draw(img)
    if date:
        fdt = _fit(date.upper(), (X1 - X0) * S, 30 * S, 600)
        _grad_text(img, cxm, (711 + dy) * S, date.upper(), fdt, acc_stops, 'm', shadow=120)
    if time:
        ft = _fit(time, (X1 - X0) * S, 74 * S, 700)
        _grad_text(img, cxm, (763 + dy) * S, time, ft, _metal((178, 182, 192), (236, 238, 244), (255, 255, 255)), 'm')
    fz = brand_kit.font('Manrope[wght].ttf', 19 * S, 600)
    d.text((cxm, (860 + dy) * S), tz, font=fz, fill=(196, 194, 202), anchor='mm')
    if odds:
        _hairline(img, cxm, 884 * S, 150 * S, GOLD if league == 'KHL' else acc)
        fo = brand_kit.font('Oswald[wght].ttf', 30 * S, 600)
        fl = brand_kit.font('Manrope[wght].ttf', 15 * S, 700)
        pw, gap, y0 = 88, 12, 930
        x = cxm / S - (3 * pw + 2 * gap) / 2
        pill = [(0, _mix(acc_stops[0][1], .1)), (.48, acc_stops[1][1]), (.52, acc_stops[2][1]), (1, acc_stops[3][1])]
        for lab, v in zip(('П1', 'Х', 'П2'), odds):
            d.text(((x + pw / 2) * S, (y0 - 10) * S), lab, font=fl, fill=(170, 168, 176), anchor='md')
            _pill_gold(img, (x * S, y0 * S, (x + pw) * S, (y0 + 46) * S), '%.2f' % v, fo, pill, (28, 20, 6))
            x += pw + gap
        fn = brand_kit.font('Manrope[wght].ttf', 14 * S, 700)
        d.text((cxm, 1000 * S), 'ОСНОВНОЕ ВРЕМЯ', font=fn, fill=(140, 138, 148), anchor='mm')

    # марка канала
    fm = brand_kit.font('Oswald[wght].ttf', 24 * S, 700)
    tag = 'KXL' if league == 'KHL' else 'NHL'
    wj, wt = fm.getlength('JARVIS'), fm.getlength(tag)
    gx, bar = 14 * S, 3 * S
    xr = cxm + (wj + gx * 2 + bar + wt) / 2
    yb = 1056 * S
    tb = fm.getbbox(tag, anchor='rs')
    _grad_text(img, xr, yb + tb[1], tag, fm, acc_stops, 'r', shadow=0)
    d.rectangle((xr - wt - gx - bar, yb - 22 * S, xr - wt - gx, yb), fill=GOLD if league == 'KHL' else acc)
    d.text((xr - wt - 2 * gx - bar, yb), 'JARVIS', font=fm, fill=(245, 245, 245), anchor='rs')

    # тонкое зерно против полос в градиентах
    a = np.asarray(img.convert('RGB')).astype(np.int16)
    a += np.random.default_rng(5).integers(-2, 3, a.shape[:2], dtype=np.int16)[..., None]
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    out.save(path, quality=94, optimize=True)
    return path


if __name__ == '__main__':
    print(render('Северсталь', 'СКА', 'out/versus_premium.jpg', date='13 октября', time='19:00',
                 odds=(2.60, 4.20, 2.35)))
