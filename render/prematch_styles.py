"""Предматчевый постер — новые анимированные варианты (16.10.2026, просьба владельца: все баннеры к прогнозам —
анимация). Рядом с «Versus» (versus.py / versus_anim.py, их вывод не меняется); флаги, «парящие» эмблемы,
холст и кодирование — из versus_anim.

    tablo   «Табло»            — табло арены: светодиодные дата, время и линия, эмблемы на экранах, бегущие стрелки
    ice     «Лёд»              — каток сверху: центральная линия и круг вбрасывания со временем, эмблемы «подо льдом»,
                                 блик по льду и искры инея
    split   «Сплит-диагональ»  — кадр разрезан наискось на два флага клубов, по шву — светящаяся линия и искра,
                                 в центре шва — медальон с датой и временем
    pick    «Прогноз крупно»   — прогноз и кэф — главные, клубы маленькими флагами сверху; блик по плашке кэфа
    ticket  «Билет»            — билет на матч с отрывным корешком: ряд и место = время, прогноз на корешке;
                                 билет плавно покачивается, по фольге пробегает блик
    cards   «Карточки»         — две коллекционные карточки клубов наклонены друг к другу и парят, голографический
                                 блик; П1/П2 — на карточках, Х — монета между ними

    import prematch_styles as ps
    ps.render('Торпедо', 'Динамо Москва', 'out/pm_tablo.mp4', '16 октября', '19:00', odds=(2.12, 3.76, 3.00),
              style='tablo', pick='итоговая победа Торпедо', kef=2.01, plates_dir='out/anim/plates')
→ MP4 H.264 1080×1080, 30 fps, 4 с, бесшовный цикл, ≤ target_mb (Telegram показывает как GIF-анимацию);
  first=путь .jpg — первый кадр; sheet=True — контактный лист 6 кадров рядом (_frames.jpg).
Флаги «Сплит-диагонали» и «Прогноза крупно» — плашки versus_anim со своей геометрией (рисуются один раз в plates_dir).
Запуск из папки render.
"""
import functools
import itertools
import math
import os
import time as _clock
from collections import namedtuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import brand_kit
import nhl
import poster
import versus
import versus_anim as va

W, H = va.W, va.H
SS = va.SS                        # статичные слои рисуются в 3× и уменьшаются
GRAIN = va.GRAIN
FPS, SECONDS = 30, 4
F32 = np.float32

STYLES = ['tablo', 'ice', 'split', 'pick', 'ticket', 'cards']
NAMES = {'tablo': 'Табло', 'ice': 'Лёд', 'split': 'Сплит-диагональ', 'pick': 'Прогноз крупно', 'ticket': 'Билет',
         'cards': 'Карточки'}

OSW, MAN, ALU, UNB, TEK = 'Oswald[wght].ttf', 'Manrope[wght].ttf', 'AlumniSans[wght].ttf', 'Unbounded[wght].ttf', \
    'Tektur[wdth,wght].ttf'
WHITE = (246, 246, 248)
DIM = (172, 170, 180)


# ───────────────────────────── данные матча ─────────────────────────────
Match = namedtuple('Match', 'home away acc tag league date time odds pick kef')


def _club(ru, color, league):
    if league == 'NHL':
        sub = nhl.TEAMS[ru][5] + ' дивизион'
    else:
        city = versus.KHL_CITY.get(ru, '')
        sub = '' if city in ru else city
    return dict(ru=ru, short=poster.SHORT.get(ru, ru), sub=sub, color=tuple(int(c) for c in color),
                c2=tuple(poster.TEAMS[ru][2]))


def _match(home, away, league, date, time, odds, pick, kef):
    if league == 'NHL':
        nhl.register()
    (hn, hc, _, _), (an, ac, _, _), acc = versus._teams(home, away, league)
    import football
    tag = 'КХЛ' if league == 'KHL' else football.label(league) if football.is_foot(league) and league != 'FOOT' else \
        'ФУТБОЛ' if league == 'FOOT' else 'НХЛ'
    return Match(_club(hn, hc, league), _club(an, ac, league), tuple(acc), tag,
                 league, date or '', time or '', odds, pick, kef)


def _n(v):
    """Коэффициент по-русски: 2,12."""
    if v is None:
        return ''
    if isinstance(v, str):
        return v.strip().replace('.', ',')
    return ('%.2f' % v).replace('.', ',')


def _cap(s):
    return s[:1].upper() + s[1:] if s else s


# ───────────────────────────── шрифты и текст ─────────────────────────────
@functools.lru_cache(maxsize=512)
def _font(name, size, wght=None, wdth=None):
    f = ImageFont.truetype(os.path.join(brand_kit.FD, name), max(1, int(round(size))))
    try:
        axes = f.get_variation_axes()
    except Exception:
        return f
    vals = []
    for ax in axes:
        nm = ax.get('name', b'')
        nm = nm.decode('latin-1') if isinstance(nm, bytes) else str(nm)
        if 'eight' in nm and wght:
            vals.append(wght)
        elif 'idth' in nm and wdth:
            vals.append(wdth)
        else:
            vals.append(ax.get('default', ax['minimum']))
    f.set_variation_by_axes(vals)
    return f


def F(name, size, wght=None, wdth=None):
    """Шрифт для слоя 3×; size — в пикселях кадра 1080."""
    return _font(name, size * SS, wght, wdth)


def _fit(text, max_w, size, name=OSW, wght=700, wdth=None, min_size=12):
    s = size
    while s > min_size:
        f = F(name, s, wght, wdth)
        if f.getlength(text) <= max_w * SS:
            return f
        s -= 1
    return F(name, min_size, wght, wdth)


def _splits(words, k):
    n = len(words)
    for cut in itertools.combinations(range(1, n), k - 1):
        b = (0,) + cut + (n,)
        yield [' '.join(words[b[i]:b[i + 1]]) for i in range(k)]


def _wrap_fit(text, max_w, max_h, max_size, name=OSW, wght=700, wdth=None, max_lines=3, lead=1.0, min_size=14):
    """Самый крупный кегль, при котором text (по словам, ≤ max_lines строк, строки по ширине ровнее) влезает
    в max_w × max_h. → (шрифт, строки, шаг строк в px кадра)."""
    words = text.split()
    for size in range(int(max_size), min_size - 1, -1):
        f = F(name, size, wght, wdth)
        for k in range(1, min(max_lines, len(words)) + 1):
            if k * size * lead > max_h:
                break
            best = min(_splits(words, k), key=lambda ls: max(f.getlength(x) for x in ls))
            if max(f.getlength(x) for x in best) <= max_w * SS:
                return f, best, size * lead
    f = F(name, min_size, wght, wdth)
    return f, [text], min_size * lead


def _t(d, x, y, text, f, fill, anchor='mm'):
    d.text((x * SS, y * SS), text, font=f, fill=fill, anchor=anchor)


def _spaced(d, x, y, text, f, fill, sp, anchor='m'):
    """Текст разрядкой sp (px кадра); anchor 'l' / 'm' / 'r' по x, по y — середина строки."""
    sp *= SS
    tw = sum(f.getlength(c) for c in text) + sp * (len(text) - 1)
    cx = x * SS - {'l': 0, 'm': tw / 2, 'r': tw}[anchor]
    for c in text:
        d.text((cx, y * SS), c, font=f, fill=fill, anchor='lm')
        cx += f.getlength(c) + sp
    return tw / SS


def _shadow_text(layer, x, y, text, f, fill, anchor='mm', blur=10, off=(0, 4), alpha=170):
    sh = Image.new('L', layer.size, 0)
    ImageDraw.Draw(sh).text(((x + off[0]) * SS, (y + off[1]) * SS), text, font=f, fill=alpha, anchor=anchor)
    sh = sh.filter(ImageFilter.GaussianBlur(blur * SS / 2))
    blk = Image.new('RGBA', layer.size, (0, 0, 0, 255))
    blk.putalpha(sh)
    layer.alpha_composite(blk)
    ImageDraw.Draw(layer).text((x * SS, y * SS), text, font=f, fill=fill, anchor=anchor)


def _brand(d, cx, yb, acc, tag, size=24, color=WHITE):
    """Марка канала «JARVIS | КХЛ» по центру cx, базовая линия yb."""
    fm = F(OSW, size, 700)
    wj, wt = fm.getlength('JARVIS'), fm.getlength(tag)
    gx, bar = 14 * SS, 3 * SS
    x = cx * SS - (wj + 2 * gx + bar + wt) / 2
    y = yb * SS
    d.text((x, y), 'JARVIS', font=fm, fill=color, anchor='ls')
    x += wj + gx
    d.rectangle((x, y - size * 0.92 * SS, x + bar, y), fill=(220, 220, 225))
    d.text((x + bar + gx, y), tag, font=fm, fill=acc, anchor='ls')


def _odds_row(d, cx, y0, odds, acc, pw=100, ph=50, gap=14, size=30, fill=None, txt=(24, 20, 14),
              lab=DIM, outline=None, lab_size=15):
    """Плашки П1/Х/П2 (как у Versus): подпись над плашкой, число по центру."""
    fo, fl = F(OSW, size, 600), F(MAN, lab_size, 700)
    x = cx - (3 * pw + 2 * gap) / 2
    for name, v in zip(('П1', 'Х', 'П2'), odds):
        box = (x * SS, y0 * SS, (x + pw) * SS, (y0 + ph) * SS)
        if fill is not None or outline is None:
            d.rounded_rectangle(box, radius=ph * 0.28 * SS, fill=fill or acc)
        if outline is not None:
            d.rounded_rectangle(box, radius=ph * 0.28 * SS, outline=outline, width=2 * SS)
        _t(d, x + pw / 2, y0 + ph / 2 + 1, _n(v), fo, txt)
        _t(d, x + pw / 2, y0 - 10, name, fl, lab, anchor='md')
        x += pw + gap


def _pick_bar(layer, box, pick, kef, acc, bg=(0, 0, 0, 150), size=32, label='Прогноз:'):
    """Плашка «Прогноз: … | Кэф: …»: тёмная со светлой кромкой, справа — капсула кэфа цвета акцента."""
    x0, y0, x1, y1 = box
    hgt = y1 - y0
    ov = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle((x0 * SS, y0 * SS, x1 * SS, y1 * SS), radius=hgt * 0.3 * SS, fill=bg,
                        outline=acc + (110,), width=2 * SS)
    xr = x1 - 8
    if kef is not None:
        fk = F(OSW, size * 0.95, 700)
        fl = F(MAN, size * 0.5, 800)
        kt = _n(kef)
        kw = (fk.getlength(kt) + fl.getlength('КЭФ:') + 14 * SS) / SS + 44
        d.rounded_rectangle(((x1 - 8 - kw) * SS, (y0 + 8) * SS, xr * SS, (y1 - 8) * SS), radius=(hgt - 16) * 0.3 * SS,
                            fill=acc)
        xl = x1 - 8 - kw + 22
        _t(d, xl, (y0 + y1) / 2 + 1, 'КЭФ:', fl, (30, 24, 12), anchor='lm')
        _t(d, xr - 22, (y0 + y1) / 2 + 1, kt, fk, (20, 16, 8), anchor='rm')
        xr = x1 - 8 - kw
    fl = F(MAN, size * 0.62, 800)
    lw = fl.getlength(label.upper()) / SS
    avail = xr - x0 - 32 - lw - 14
    fp = _fit(_cap(pick), avail, size, OSW, 500)
    _t(d, x0 + 24, (y0 + y1) / 2, label.upper(), fl, acc, anchor='lm')
    _t(d, x0 + 24 + lw + 14, (y0 + y1) / 2 + 1, _cap(pick), fp, WHITE, anchor='lm')
    layer.alpha_composite(ov)


# ───────────────────────────── слои и сцена ─────────────────────────────
def _layer(size=(W, H)):
    return Image.new('RGBA', (size[0] * SS, size[1] * SS), (0, 0, 0, 0))


def _arr(img, size=(W, H)):
    """Слой 3× → (RGB float, альфа 0..1) в размере кадра."""
    a = np.asarray(img.resize(size, Image.LANCZOS), F32)
    return a[..., :3], a[..., 3] / 255


def _grid(w=W, h=H):
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    return xx + 0.5, yy + 0.5


def _bg(base, glows=(), vignette=0.32, w=W, h=H):
    """Тёмный фон: base, мягкие пятна света (cx, cy, r, цвет, сила), виньетка."""
    xx, yy = _grid(w, h)
    img = np.empty((h, w, 3), F32)
    img[:] = base
    for cx, cy, r, col, k in glows:
        g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r))[..., None]
        img += np.array(col, F32) * k * g
    rr = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    img *= (1 - vignette * np.clip(rr / 1.414, 0, 1) ** 2)[..., None]
    return img


def _over(img, x0, y0, rgb, a):
    """rgb с альфой a поверх img в точке (x0, y0) — с обрезкой по кадру."""
    h, w = a.shape
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(img.shape[1], x0 + w), min(img.shape[0], y0 + h)
    if X1 <= X0 or Y1 <= Y0:
        return
    sl = (slice(Y0 - y0, Y1 - y0), slice(X0 - x0, X1 - x0))
    aa = a[sl][..., None]
    img[Y0:Y1, X0:X1] = img[Y0:Y1, X0:X1] * (1 - aa) + rgb[sl] * aa


class Scene:
    """Слои кадра по порядку: неподвижные (холст «вшит», соседние слиты в один) и движущиеся fn(img, i, tau)."""

    def __init__(self, grain=GRAIN):
        self.cv = va._Canvas(grain)
        self.items = []
        self.closers = []

    def static(self, rgb, a=None):
        if a is None:
            a = np.ones(rgb.shape[:2], F32)
        p = np.clip(va._Canvas.apply(rgb, self.cv.screen), 0, 255) * a[..., None]
        if self.items and self.items[-1][0] == 's':
            _, pb, ab = self.items[-1]
            self.items[-1] = ('s', pb * (1 - a[..., None]) + p, 1 - (1 - ab) * (1 - a))
        else:
            self.items.append(('s', p, a))

    def layer(self, img):
        self.static(*_arr(img))

    def dyn(self, fn):
        self.items.append(('d', fn))
        return fn

    def frame(self, i, tau):
        img = np.zeros((H, W, 3), F32)
        for it in self.items:
            if it[0] == 's':
                img *= 1 - it[2][..., None]
                img += it[1]
            else:
                it[1](img, i, tau)
        return np.clip(img, 0, 255).astype(np.uint8)

    def close(self):
        for c in self.closers:
            c()


class FloatEmblem:
    """«Парящая» эмблема versus_anim._Emblem над неподвижным фоном: покачивание, поворот, тень отстаёт."""

    def __init__(self, scene, team, cx, cy, size, phase=0.0, shadow=0.9):
        self.e = va._Emblem(team, cx, cy, size, scene.cv)
        self.ph, self.k = phase, shadow
        self.sh = Image.fromarray(self.e.shadow.astype(F32), 'F')

    def __call__(self, img, i, tau):
        (ox, oy), rgb, a, tex, (sx, sy), shk = self.e.frame(tau, self.ph)
        if self.k:
            sh = np.asarray(self.sh.transform(self.sh.size, Image.AFFINE, (1, 0, -sx, 0, 1, -sy),
                                              resample=Image.BILINEAR), F32)
            img *= (1 - np.clip(sh * shk * self.k, 0, 1))[..., None]
        _over(img, int(ox), int(oy), va._Canvas.apply(rgb, tex), a)


class Plate:
    """Плашка клуба versus_anim (флаг + парящая эмблема, холст вшит) со своей геометрией; mask — доля видимости
    (кадр 1080², 0..1) — например, половина «Сплит-диагонали»."""

    def __init__(self, scene, club, side, league, plates_dir, geom, mask=None):
        self.path, self.meta = va.get_plate(club['ru'], side, league, club['color'], plates_dir, SECONDS, FPS,
                                            geom=geom)
        self.mask, self.rd, self.next = mask, None, 0
        scene.closers.append(self.close)

    def close(self):
        if self.rd is not None:
            self.rd.close()
            self.rd = None

    def __call__(self, img, i, tau):
        if self.rd is None or i != self.next:
            self.close()
            self.rd = va._read_plate(self.path, self.meta)
            for _ in range(i):
                next(self.rd)
        fr = next(self.rd)
        self.next = i + 1
        x0, y0 = self.meta['origin']
        a = fr[..., 3].astype(F32) / 255
        h, w = a.shape
        if self.mask is not None:
            a = a * self.mask[y0:y0 + h, x0:x0 + w]
        _over(img, x0, y0, fr[..., :3].astype(F32), a)


class Rigid:
    """Жёсткий объект (карточка, билет): мастер RGBA в 3× с вшитым холстом, плавно покачивается вокруг (cx, cy)
    с базовым углом angle; мягкая тень на фоне; блик shine(tau, xx, yy, foil) → добавка света в координатах кадра
    (foil — маска «фольги», повёрнута вместе с объектом)."""

    def __init__(self, scene, master, cx, cy, angle=0.0, bob=6.0, sway=0.8, phase=0.0, foil=None, shine=None,
                 shadow=(10, 26, 26, 0.62)):
        w1, h1 = master.width // SS, master.height // SS
        tex = va._Canvas(GRAIN, seed=7, size=(w1, h1)).screen
        tex = np.asarray(Image.fromarray(tex, 'F').resize(master.size, Image.BICUBIC), F32)
        m = np.asarray(master, F32)
        rgb = np.clip(va._Canvas.apply(m[..., :3], tex), 0, 255)
        extra = [m[..., 3]] + ([np.asarray(foil.resize(master.size), F32)] if foil is not None else [])
        self.chan = [Image.fromarray(c.astype(np.uint8), 'L') for c in (rgb[..., 0], rgb[..., 1], rgb[..., 2])] + \
                    [Image.fromarray(c.astype(np.uint8), 'L') for c in extra]
        self.ms = np.array(master.size, F32)
        self.c = np.array((cx, cy), F32)
        self.angle, self.bob, self.sway, self.ph = angle, bob, sway, phase
        self.shine, self.shadow = shine, shadow
        self.T = int(math.ceil(math.hypot(w1, h1))) + 2 * (int(bob) + 8)

    def pose(self, tau):
        s = math.sin(2 * math.pi * tau + self.ph)
        ang = self.angle + self.sway * math.sin(2 * math.pi * tau + self.ph + 0.9)
        return np.array((1.6 * math.cos(2 * math.pi * tau + self.ph), self.bob * s), F32), ang, s

    def __call__(self, img, i, tau):
        d, ang, s = self.pose(tau)
        c = self.c + d
        T = self.T
        ox, oy = int(round(c[0] - T / 2)), int(round(c[1] - T / 2))
        th = math.radians(ang)
        cs, sn = math.cos(th), math.sin(th)
        # выход (тайл 3×) → вход (мастер 3×): in = Cm + R(θ)·(q − Ct)   (PIL: положительный угол — против часовой)
        ct = SS * (c - (ox, oy))
        cm = self.ms / 2
        a, b, dd, e = cs, -sn, sn, cs
        coef = (a, b, cm[0] - a * ct[0] - b * ct[1], dd, e, cm[1] - dd * ct[0] - e * ct[1])
        size = (T * SS, T * SS)
        ch = [np.asarray(c_.transform(size, Image.AFFINE, coef, resample=Image.BICUBIC)
                         .resize((T, T), Image.BOX), F32) for c_ in self.chan]
        rgb = np.dstack(ch[:3])
        al = ch[3] / 255
        foil = ch[4] / 255 if len(ch) > 4 else None
        if self.shadow:
            dx, dy, blur, k = self.shadow
            k = k * (1 - 0.18 * s)
            sh = Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur + 4 * s))
            sh = np.asarray(sh, F32) / 255 * k
            _over(img, ox + int(dx + 2 * s), oy + int(dy + 6 * s), np.zeros((T, T, 3), F32), sh)
        if self.shine:
            xx, yy = np.meshgrid(np.arange(T, dtype=F32) + ox, np.arange(T, dtype=F32) + oy)
            rgb = rgb + self.shine(tau, xx, yy, foil if foil is not None else al)
        _over(img, ox, oy, np.clip(rgb, 0, 255), al)


def _sweep(tau, xx, yy, x_from, x_to, ang=-28, width=60, k=0.38, rainbow=0.0, t0=0.0, t1=1.0):
    """Диагональная полоса света, проходит от x_from до x_to за [t0, t1] доли цикла (вне — за краем).
    → добавка RGB (h, w, 3)."""
    p = np.clip((tau - t0) / (t1 - t0), 0, 1) if t1 > t0 else tau
    c = x_from + (x_to - x_from) * p
    u = xx + yy * math.tan(math.radians(ang))
    g = np.exp(-((u - c) / width) ** 2) + 0.35 * np.exp(-((u - c + width * 2.2) / (width * 0.35)) ** 2)
    out = np.empty(xx.shape + (3,), F32)
    out[:] = 255 * k
    if rainbow:
        hue = (u / 260.0 + tau) % 1.0
        rb = np.stack([0.5 + 0.5 * np.cos(2 * np.pi * (hue + o)) for o in (0, 1 / 3, 2 / 3)], -1)
        out = out * (1 - rainbow) + 255 * k * rainbow * rb * 1.4
    return out * g[..., None]


def _blur_arr(a, r):
    """Размытие по Гауссу для float-массива (через 16-битный канал: ореолам точности хватает)."""
    mx = float(a.max())
    if mx <= 0:
        return np.zeros_like(a, F32)
    im = Image.fromarray(np.clip(a / mx * 255, 0, 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, F32) / 255 * mx


# ───────────────────────────── светодиоды (табло) ─────────────────────────────
LED_FONT = (TEK, 700, 82)          # шрифт, вес, ширина: узкий «технический» Tektur хорошо ложится на точки


def _bits(text, rows, font=LED_FONT, thr=0.42):
    """Текст → решётка светодиодов (bool): высота прописной = rows точек, 2 ряда над ней и 3 под ней."""
    name, wght, wdth = font
    k = 12
    probe = _font(name, 200, wght, wdth)
    l0, t0, r0, b0 = probe.getbbox('Н')
    size = rows * k * 200 / (b0 - t0)
    f = _font(name, size, wght, wdth)
    top = f.getbbox('Н')[1]
    l, t, r, b = f.getbbox(text)
    cols = int(math.ceil((r - l) / k)) + 1
    im = Image.new('L', (cols * k, (rows + 5) * k), 0)
    ImageDraw.Draw(im).text((-l + k // 2, 2 * k - top), text, font=f, fill=255)
    a = np.asarray(im, F32).reshape(rows + 5, k, cols, k).mean((1, 3)) / 255
    bits = a > thr
    nz = np.where(bits.any(0))[0]
    return bits[:, nz[0]:nz[-1] + 1] if len(nz) else bits


def _led(bits, pitch, color, glow=0.55, off=0.07, r=0.40, ss=SS, margin=2.0):
    """Решётка → RGBA (в ss×): круглые точки шага pitch, горящие — color с горячей серединой и ореолом,
    погасшие — еле видны."""
    rows, cols = bits.shape
    ps = pitch * ss
    m = int(margin * ps)
    w, h = int(math.ceil(cols * ps)) + 2 * m, int(math.ceil(rows * ps)) + 2 * m
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    u, v = (xx + 0.5 - m) / ps, (yy + 0.5 - m) / ps
    i, j = np.floor(u).astype(np.int32), np.floor(v).astype(np.int32)
    inside = (i >= 0) & (i < cols) & (j >= 0) & (j < rows)
    ic, jc = np.clip(i, 0, cols - 1), np.clip(j, 0, rows - 1)
    dist = np.hypot((u - i - 0.5) * ps, (v - j - 0.5) * ps)
    dot = np.clip(r * ps - dist + 0.5, 0, 1) * inside
    on = bits[jc, ic] & inside
    a_on = dot * on
    a_off = dot * (~on) * off
    g = _blur_arr(a_on, ps * 0.9) * glow
    col = np.array(color, F32)
    hot = col + (255 - col) * 0.35
    alpha = 1 - (1 - a_on) * (1 - g) * (1 - a_off)
    rgb = (hot * a_on[..., None] + col * (g * (1 - a_on))[..., None] + np.array((90, 90, 96), F32) *
           (a_off * (1 - a_on))[..., None]) / np.maximum(alpha, 1e-4)[..., None]
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.clip(alpha * 255, 0, 255)]).astype(np.uint8), 'RGBA')


def _led_text(layer, text, cx, cy, rows, pitch, color, max_w=None, anchor='m', **kw):
    """Светодиодный текст по центру (cx, cy) прописных; шаг уменьшается, чтобы влезть в max_w. → (ширина, шаг)."""
    bits = _bits(text, rows)
    if max_w and bits.shape[1] * pitch > max_w:
        pitch = max_w / bits.shape[1]
    tile = _led(bits, pitch, color, **kw)
    m = (tile.width / SS - bits.shape[1] * pitch) / 2
    w = bits.shape[1] * pitch
    x = {'m': cx - w / 2, 'l': cx, 'r': cx - w}[anchor] - m
    y = cy - (2 + rows / 2) * pitch - m
    layer.alpha_composite(tile, (int(round(x * SS)), int(round(y * SS))))
    return w, pitch


def _led_mask(w, h, pitch=4.0, lo=0.55, r=0.42):
    """Маска экрана: сетка светодиодов шага pitch (lo — яркость между точками)."""
    k = 3
    yy, xx = np.mgrid[0:h * k, 0:w * k].astype(F32)
    u, v = (xx + 0.5) / (pitch * k), (yy + 0.5) / (pitch * k)
    dist = np.hypot(u - np.floor(u) - 0.5, v - np.floor(v) - 0.5) * pitch * k
    dot = np.clip(r * pitch * k - dist + 0.5, 0, 1)
    dot = dot.reshape(h, k, w, k).mean((1, 3))
    return lo + (1 - lo) * dot


def _chevrons(cols, rows=7, period=8, rev=False):
    """Бегущие стрелки «›››» для ленты табло: решётка rows × (cols + period)."""
    n = cols + period
    j, i = np.mgrid[0:rows, 0:n]
    mid = rows // 2
    x = (i + np.abs(j - mid)) % period if not rev else (i - np.abs(j - mid)) % period
    return x < 2


# ═════════════════════════════ 1. ТАБЛО ═════════════════════════════
def _tablo(m, plates_dir):
    sc = Scene()
    acc = m.acc
    hc, ac = m.home['color'], m.away['color']
    sc.static(_bg((11, 11, 14), [(540, 980, 520, acc, 0.10), (540, 300, 700, (40, 44, 60), 0.35)], vignette=0.4))

    HX0, HY0, HX1, HY1 = 36, 34, 1044, 968           # корпус табло
    LX0, LY0, LX1, LY1 = 58, 56, 1022, 946           # светодиодное поле
    lay = _layer()
    d = ImageDraw.Draw(lay)
    sh = Image.new('L', lay.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle(((HX0 + 6) * SS, (HY0 + 22) * SS, (HX1 + 6) * SS, (HY1 + 28) * SS),
                                         radius=26 * SS, fill=200)
    blk = Image.new('RGBA', lay.size, (0, 0, 0, 255))
    blk.putalpha(sh.filter(ImageFilter.GaussianBlur(30 * SS)))
    lay.alpha_composite(blk)
    # корпус: тёмный металл с фаской
    d.rounded_rectangle((HX0 * SS, HY0 * SS, HX1 * SS, HY1 * SS), radius=26 * SS, fill=(34, 34, 40))
    d.rounded_rectangle((HX0 * SS, HY0 * SS, HX1 * SS, HY1 * SS), radius=26 * SS, outline=(78, 78, 88), width=3 * SS)
    d.rounded_rectangle(((HX0 + 8) * SS, (HY0 + 8) * SS, (HX1 - 8) * SS, (HY1 - 8) * SS), radius=20 * SS,
                        outline=(20, 20, 24), width=4 * SS)
    d.rectangle((LX0 * SS, LY0 * SS, LX1 * SS, LY1 * SS), fill=(5, 5, 7))
    # стыки светодиодных модулей
    for x in range(LX0 + 120, LX1, 120):
        d.line((x * SS, LY0 * SS, x * SS, LY1 * SS), fill=(14, 14, 18), width=SS)
    for y in range(LY0 + 110, LY1, 110):
        d.line((LX0 * SS, y * SS, LX1 * SS, y * SS), fill=(14, 14, 18), width=SS)
    # болты по углам корпуса
    for bx, by in ((HX0 + 18, HY0 + 18), (HX1 - 18, HY0 + 18), (HX0 + 18, HY1 - 18), (HX1 - 18, HY1 - 18)):
        d.ellipse(((bx - 4) * SS, (by - 4) * SS, (bx + 4) * SS, (by + 4) * SS), fill=(70, 70, 78))
    sc.layer(lay)

    # экраны с эмблемами: подсветка цветом клуба
    SCR = [(84, 150, 404, 470), (676, 150, 996, 470)]
    lay = _layer()
    d = ImageDraw.Draw(lay)
    for (x0, y0, x1, y1), col in zip(SCR, (hc, ac)):
        d.rectangle(((x0 - 6) * SS, (y0 - 6) * SS, (x1 + 6) * SS, (y1 + 6) * SS), outline=col + (150,), width=2 * SS)
    sc.layer(lay)
    xx, yy = _grid()
    scr_bg = np.zeros((H, W, 3), F32)
    scr_a = np.zeros((H, W), F32)
    for (x0, y0, x1, y1), col in zip(SCR, (hc, ac)):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 150 ** 2))
        sel = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
        c = np.array(col, F32)
        scr_bg[sel] = (c * (0.16 + 0.42 * g[..., None]))[sel]
        scr_a[sel] = 1
    sc.static(scr_bg, scr_a)
    sc.dyn(FloatEmblem(sc, m.home['ru'], (SCR[0][0] + SCR[0][2]) / 2, (SCR[0][1] + SCR[0][3]) / 2 + 2, 250, 0.0, 0.7))
    sc.dyn(FloatEmblem(sc, m.away['ru'], (SCR[1][0] + SCR[1][2]) / 2, (SCR[1][1] + SCR[1][3]) / 2 + 2, 250,
                       0.6 * np.pi, 0.7))
    masks = [_led_mask(x1 - x0, y1 - y0, 4.0, 0.5) for x0, y0, x1, y1 in SCR]

    def screens(img, i, tau):
        for (x0, y0, x1, y1), mk in zip(SCR, masks):
            reg = img[y0:y1, x0:x1]
            glow = np.dstack([_blur_arr(reg[..., c], 2.2) for c in range(3)])
            reg *= mk[..., None]
            reg += glow * 0.22
            # полоса обновления экрана
            yl = (np.arange(y1 - y0, dtype=F32) + 0.5) / (y1 - y0)
            p = (2 * tau) % 1.0
            band = np.exp(-((yl - p * 1.4 + 0.2) / 0.05) ** 2) * 0.10
            reg *= (1 + band)[:, None, None]
    sc.dyn(screens)

    lay = _layer()
    d = ImageDraw.Draw(lay)
    # дата
    if m.date:
        dw, _ = _led_text(lay, m.date.upper(), 540, 103, 9, 4.0, acc, max_w=560)
    else:
        dw = 0
    # центр: «НАЧАЛО», часы, «МСК»
    _led_text(lay, 'НАЧАЛО', 540, 194, 10, 3.0, (210, 210, 220))
    clock_parts = (m.time or '').split(':')
    colon = None
    if len(clock_parts) == 2:
        b1, bc, b2 = _bits(clock_parts[0], 16), _bits(':', 16), _bits(clock_parts[1], 16)
        gap = np.zeros((b1.shape[0], 2), bool)
        allb = np.hstack([b1, gap, np.zeros_like(bc), gap, b2])
        colb = np.hstack([np.zeros_like(b1), gap, bc, gap, np.zeros_like(b2)])
        pitch = min(6.6, 252 / allb.shape[1])
        tile = _led(allb, pitch, acc, glow=0.6)
        ctile = _led(colb, pitch, acc, glow=0.6, off=0)
        mm = (tile.width / SS - allb.shape[1] * pitch) / 2
        x = 540 - allb.shape[1] * pitch / 2 - mm
        y = 300 - (2 + 8) * pitch - mm
        lay.alpha_composite(tile, (int(round(x * SS)), int(round(y * SS))))
        cl = _layer()
        cl.alpha_composite(ctile, (int(round(x * SS)), int(round(y * SS))))
        colon = _arr(cl)
    elif m.time:
        _led_text(lay, m.time, 540, 300, 16, 6.0, acc, max_w=252)
    _led_text(lay, 'МСК', 540, 404, 10, 3.4, (210, 210, 220))
    # имена под экранами
    for (x0, y0, x1, y1), cl_ in zip(SCR, (m.home, m.away)):
        name = cl_['ru'].upper()
        if (x1 - x0 + 30) / _bits(name, 11).shape[1] < 3.2:
            name = cl_['short'].upper()
        _led_text(lay, name, (x0 + x1) / 2, 512, 11, 4.0, WHITE, max_w=x1 - x0 + 30)
    # линия
    if m.odds:
        BW, GAP = 250, 30
        x = 540 - (3 * BW + 2 * GAP) / 2
        for lab, v in zip(('П1', 'Х', 'П2'), m.odds):
            d.rectangle((x * SS, 578 * SS, (x + BW) * SS, 724 * SS), fill=(9, 9, 12), outline=(46, 46, 54), width=SS * 2)
            _led_text(lay, lab, x + BW / 2, 606, 10, 3.0, (200, 200, 210))
            _led_text(lay, _n(v), x + BW / 2, 672, 14, 5.0, acc, max_w=BW - 36)
            x += BW + GAP
    # прогноз
    if m.pick:
        d.rectangle((84 * SS, 762 * SS, 996 * SS, 922 * SS), fill=(9, 9, 12), outline=(46, 46, 54), width=SS * 2)
        lw, p = _led_text(lay, 'ПРОГНОЗ:', 110, 804, 11, 3.6, (255, 92, 92), anchor='l')
        _led_text(lay, m.pick.upper(), 110 + lw + 22, 804, 11, 3.6, WHITE, max_w=996 - 130 - lw - 22, anchor='l')
        if m.kef is not None:
            kw, _ = _led_text(lay, 'КЭФ:', 110, 878, 11, 3.6, (255, 92, 92), anchor='l')
            _led_text(lay, _n(m.kef), 110 + kw + 22, 874, 14, 4.6, acc, anchor='l')
        _led_text(lay, 'ОСНОВНОЕ ВРЕМЯ', 970, 880, 10, 2.6, (150, 150, 160), anchor='r')
    else:
        _led_text(lay, 'ОСНОВНОЕ ВРЕМЯ · ВРЕМЯ МОСКОВСКОЕ', 540, 842, 9, 4.0, (200, 200, 210), max_w=860)
    # марка канала — табличка под табло
    _brand(d, 540, 1040, acc, m.tag, 26)
    sc.layer(lay)

    # бегущие стрелки по бокам даты: хозяева — цвет клуба, к центру; гости — навстречу
    rib_w = int((540 - (dw / 2 if m.date else 0) - 34 - 84) / 3.6)
    ribs = []
    for side, col in (('l', hc), ('r', ac)):
        tiles = []
        for s in range(8):
            bits = _chevrons(rib_w, 7, 8, rev=(side == 'r'))
            sh_ = (8 - s) % 8 if side == 'l' else s
            b = bits[:, sh_:sh_ + rib_w]
            t = _led(b, 3.6, versus._mix(col, 0.25), glow=0.6, off=0.05)
            x = 84 if side == 'l' else 996 - rib_w * 3.6
            lay_ = _layer()
            mm = (t.width / SS - rib_w * 3.6) / 2
            lay_.alpha_composite(t, (int(round((x - mm) * SS)), int(round((103 - 3.5 * 3.6 - mm) * SS))))
            rgb, a = _arr(lay_)
            ys, xs = np.where(a > 0.003)
            y0_, y1_, x0_, x1_ = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            tiles.append((x0_, y0_, rgb[y0_:y1_, x0_:x1_], a[y0_:y1_, x0_:x1_]))
        ribs.append(tiles)

    def ribbons(img, i, tau):
        s = int(tau * 48) % 8                       # 48 шагов по точке за цикл = 6 периодов узора
        for tiles in ribs:
            x0, y0, rgb, a = tiles[s]
            _over(img, x0, y0, rgb, a)
    sc.dyn(ribbons)

    if colon is not None:
        crgb, ca = colon
        ys, xs = np.where(ca > 0.003)
        y0_, y1_, x0_, x1_ = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        crgb, ca = crgb[y0_:y1_, x0_:x1_], ca[y0_:y1_, x0_:x1_]

        def blink(img, i, tau):
            ph = (4 * tau) % 1.0                    # 1 Гц, как у настоящих часов
            on = 1.0 if ph < 0.5 else 0.12
            _over(img, x0_, y0_, crgb, ca * on)
        sc.dyn(blink)
    return sc


# ═════════════════════════════ 2. ЛЁД ═════════════════════════════
def _ice(m, plates_dir):
    sc = Scene()
    acc = m.acc
    RX0, RY0, RX1, RY1, RR = 40, 46, 1040, 776, 150
    CX, CY, CR = 540, 400, 118
    sc.static(_bg((10, 12, 17), [(540, 400, 600, (30, 44, 70), 0.5)], vignette=0.45))
    # лёд
    xx, yy = _grid()
    rink = Image.new('L', (W * SS, H * SS), 0)
    ImageDraw.Draw(rink).rounded_rectangle((RX0 * SS, RY0 * SS, RX1 * SS, RY1 * SS), radius=RR * SS, fill=255)
    rink_a = np.asarray(rink.resize((W, H), Image.LANCZOS), F32) / 255
    ice = np.empty((H, W, 3), F32)
    g = np.exp(-((xx - CX) ** 2 / (2 * 520 ** 2) + (yy - CY) ** 2 / (2 * 330 ** 2)))
    ice[:] = np.array((17, 24, 35), F32)
    ice += np.array((22, 32, 48), F32) * g[..., None]
    # царапины от коньков
    rng = np.random.default_rng(5)
    scr = Image.new('L', (W, H), 0)
    ds = ImageDraw.Draw(scr)
    for _ in range(260):
        x, y = rng.uniform(RX0, RX1), rng.uniform(RY0, RY1)
        ang = rng.normal(0, 0.35) + (0 if rng.random() < 0.7 else math.pi / 2)
        L = rng.uniform(40, 260)
        bend = rng.normal(0, 18)
        pts = [(x + math.cos(ang) * L * t - math.sin(ang) * bend * t * t, y + math.sin(ang) * L * t +
                math.cos(ang) * bend * t * t) for t in np.linspace(0, 1, 12)]
        ds.line(pts, fill=int(rng.uniform(14, 40)), width=1)
    scr = np.asarray(scr.filter(ImageFilter.GaussianBlur(0.6)), F32) / 255
    ice += 255 * 0.22 * scr[..., None]
    sc.static(ice, rink_a)

    # разметка
    lay = _layer()
    d = ImageDraw.Draw(lay)
    RED, BLUE = (205, 34, 48), (60, 120, 235)
    d.line((CX * SS, RY0 * SS, CX * SS, (CY - CR) * SS), fill=RED + (170,), width=12 * SS)
    d.line((CX * SS, (CY + CR) * SS, CX * SS, RY1 * SS), fill=RED + (170,), width=12 * SS)
    d.line((CX * SS, (CY - CR) * SS, CX * SS, (CY + CR) * SS), fill=RED + (60,), width=12 * SS)
    for gx in (RX0 + 64, RX1 - 64):
        d.line((gx * SS, (RY0 + 40) * SS, gx * SS, (RY1 - 40) * SS), fill=RED + (130,), width=4 * SS)
        sgn = 1 if gx < CX else -1
        cr = 44
        d.pieslice(((gx - cr) * SS, (CY - cr) * SS, (gx + cr) * SS, (CY + cr) * SS),
                   -90 if sgn > 0 else 90, 90 if sgn > 0 else 270, fill=(70, 130, 220, 70), outline=RED + (150,),
                   width=3 * SS)
        nx = gx - sgn * 26
        d.rectangle((min(gx, nx) * SS, (CY - 20) * SS, max(gx, nx) * SS, (CY + 20) * SS), outline=RED + (170,),
                    width=3 * SS)
    d.ellipse(((CX - CR) * SS, (CY - CR) * SS, (CX + CR) * SS, (CY + CR) * SS), outline=BLUE + (210,), width=6 * SS)
    d.ellipse(((CX - 7) * SS, (CY + CR - 30 - 7) * SS, (CX + 7) * SS, (CY + CR - 30 + 7) * SS), fill=BLUE + (200,))
    sc.layer(lay)
    # эмблемы «под льдом»: чуть приглушены и холодные, сверху — лёгкая дымка
    EMB = [(m.home, 282, 372), (m.away, 798, 372)]
    lay = _layer()
    for cl, ex, ey in EMB:
        em = poster._emblem(cl['ru'], 236 * SS)
        e = np.asarray(em, F32)
        e[..., :3] = e[..., :3] * 0.86 + np.array((150, 190, 230), F32) * 0.10
        e[..., 3] *= 0.94
        em = Image.fromarray(np.clip(e, 0, 255).astype(np.uint8), 'RGBA')
        lay.alpha_composite(em, (int(ex * SS - em.width / 2), int(ey * SS - em.height / 2)))
    sc.layer(lay)
    # бортик
    lay = _layer()
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle(((RX0 - 3) * SS, (RY0 - 3) * SS, (RX1 + 3) * SS, (RY1 + 3) * SS), radius=(RR + 3) * SS,
                        outline=(225, 232, 240, 235), width=7 * SS)
    d.rounded_rectangle(((RX0 - 12) * SS, (RY0 - 12) * SS, (RX1 + 12) * SS, (RY1 + 12) * SS), radius=(RR + 12) * SS,
                        outline=acc + (120,), width=2 * SS)
    sc.layer(lay)

    # блик по льду, искры инея, «дыхание» круга
    rmask = rink_a[..., None]
    rng = np.random.default_rng(11)
    sparks = [(rng.uniform(RX0 + 60, RX1 - 60), rng.uniform(RY0 + 40, RY1 - 40), rng.uniform(0, 1),
               int(rng.integers(1, 3)), rng.uniform(0.5, 1.0)) for _ in range(34)]
    ring = Image.new('L', (W, H), 0)
    ImageDraw.Draw(ring).ellipse((CX - CR, CY - CR, CX + CR, CY + CR), outline=255, width=6)
    ring = _blur_arr(np.asarray(ring, F32) / 255, 9) * 2.2
    RB = (CX - CR - 40, CY - CR - 40, CX + CR + 40, CY + CR + 40)
    ringc = ring[RB[1]:RB[3], RB[0]:RB[2], None] * np.array(BLUE, F32)
    star = np.zeros((15, 15), F32)
    star[7, :] = np.exp(-np.abs(np.arange(15) - 7) / 2.5)
    star[:, 7] = np.maximum(star[:, 7], np.exp(-np.abs(np.arange(15) - 7) / 2.5))
    star = np.maximum(star, _blur_arr(star, 1.0) * 1.5)

    def life(img, i, tau):
        y0, y1 = RY0, RY1
        sub = _sweep(tau, xx[y0:y1], yy[y0:y1], -500, 1700, ang=-32, width=110, k=0.16)
        img[y0:y1] += sub * rmask[y0:y1]
        k = 0.30 + 0.20 * math.sin(2 * math.pi * 2 * tau)
        img[RB[1]:RB[3], RB[0]:RB[2]] += ringc * k
        for x, y, ph, n, s in sparks:
            v = max(0.0, math.sin(2 * math.pi * (n * tau + ph))) ** 10 * s
            if v > 0.02:
                xi, yi = int(x) - 7, int(y) - 7
                img[yi:yi + 15, xi:xi + 15] += (star * v * 230)[..., None]
    sc.dyn(life)

    # текст
    lay = _layer()
    d = ImageDraw.Draw(lay)
    for cl, ex, ey in EMB:
        f = _fit(cl['ru'].upper(), 330, 50, OSW, 700)
        _shadow_text(lay, ex, 598, cl['ru'].upper(), f, WHITE, blur=10)
        if cl['sub']:
            _t(d, ex, 640, cl['sub'].upper(), _fit(cl['sub'].upper(), 300, 17, MAN, 700), (150, 175, 205))
    if m.date:
        _spaced(d, CX, CY - 60, m.date.upper(), _fit(m.date.upper(), 190, 19, MAN, 800), acc, 1.5)
    if m.time:
        _shadow_text(lay, CX, CY + 4, m.time, _fit(m.time, 200, 78, OSW, 700), WHITE, blur=8, off=(0, 3))
    _spaced(d, CX, CY + 60, 'МСК', F(MAN, 18, 800), (190, 205, 225), 4)
    y = 846
    if m.odds:
        _odds_row(d, 540, y, m.odds, acc, pw=104, ph=50, gap=16, size=31)
        _t(d, 540, y + 68, 'ОСНОВНОЕ ВРЕМЯ', F(MAN, 13, 700), (130, 136, 150))
        y = 944
    if m.pick:
        _pick_bar(lay, (90, y - 4, 990, y + 58), m.pick, m.kef, acc, bg=(10, 14, 22, 220), size=29)
        y += 92
    _brand(d, 540, max(y + 8, 1046) if not m.pick else 1060, acc, m.tag, 22)
    sc.layer(lay)
    return sc


# ═════════════════════════════ 3. СПЛИТ-ДИАГОНАЛЬ ═════════════════════════════
SPLIT_X = (620, 460)                         # шов: x вверху и внизу кадра
SPLIT_EY, SPLIT_EM = 392, 296                # центр эмблем по y и их размер
SPLIT_HOME_X, SPLIT_AWAY_X = 255, 845


def _seam_x(y):
    return SPLIT_X[0] + (SPLIT_X[1] - SPLIT_X[0]) * y / H


def split_geometry(side):
    if side == 'home':
        return va.side_geometry('split', 'home', (W, H), (0, 0, 720, H), SPLIT_EM, (SPLIT_HOME_X, SPLIT_EY), fade='up')
    return va.side_geometry('split', 'away', (W, H), (360, 0, W, H), SPLIT_EM, (SPLIT_AWAY_X, SPLIT_EY), fade='up')


def _split(m, plates_dir):
    sc = Scene()
    acc = m.acc
    xx, yy = _grid()
    sc.static(_bg((14, 13, 17), [], vignette=0.3))
    home_m = np.clip(_seam_x(yy) - xx + 0.5, 0, 1)
    sc.dyn(Plate(sc, m.home, 'home', m.league, plates_dir, split_geometry('home'), home_m))
    sc.dyn(Plate(sc, m.away, 'away', m.league, plates_dir, split_geometry('away'), 1 - home_m))

    # затемнение низа под текст + лёгкая виньетка сверху
    t = np.clip((yy - 640) / 300, 0, 1)
    shade = (t * t * (3 - 2 * t)) * 0.9 + np.clip((120 - yy) / 120, 0, 1) * 0.25
    sc.static(np.zeros((H, W, 3), F32) + 8, shade)

    # шов: ядро + свечение (статично) и пульс/искра (в движении)
    sx = SPLIT_X
    seam = Image.new('L', (W * SS, H * SS), 0)
    ImageDraw.Draw(seam).line((sx[0] * SS, -20 * SS, sx[1] * SS, (H + 20) * SS), fill=255, width=5 * SS)
    core = np.asarray(seam.resize((W, H), Image.LANCZOS), F32) / 255
    glow = _blur_arr(core, 14)
    gl = np.clip(core + glow * 1.6, 0, 1)
    seam_rgb = np.array(versus._mix(acc, 0.35), F32) * np.ones((H, W, 3), F32)
    sc.static(seam_rgb, gl * np.clip(1 - shade * 0.6, 0, 1))
    wide = _blur_arr(core, 40)

    # медальон в центре шва: дата, время, МСК
    BX, BY, BR = _seam_x(SPLIT_EY), SPLIT_EY, 100
    lay = _layer()
    d = ImageDraw.Draw(lay)
    sh = Image.new('L', lay.size, 0)
    ImageDraw.Draw(sh).ellipse(((BX - BR + 6) * SS, (BY - BR + 16) * SS, (BX + BR + 6) * SS, (BY + BR + 16) * SS),
                               fill=190)
    blk = Image.new('RGBA', lay.size, (0, 0, 0, 255))
    blk.putalpha(sh.filter(ImageFilter.GaussianBlur(18 * SS)))
    lay.alpha_composite(blk)
    d.ellipse(((BX - BR) * SS, (BY - BR) * SS, (BX + BR) * SS, (BY + BR) * SS), fill=(14, 13, 18),
              outline=acc, width=4 * SS)
    d.ellipse(((BX - BR + 10) * SS, (BY - BR + 10) * SS, (BX + BR - 10) * SS, (BY + BR - 10) * SS),
              outline=acc + (90,), width=SS)
    if m.date:
        _t(d, BX, BY - 44, m.date.upper(), _fit(m.date.upper(), 130, 17, MAN, 800), acc)
    if m.time:
        _t(d, BX, BY + 4, m.time, _fit(m.time, 150, 62, OSW, 700), WHITE)
    _spaced(d, BX, BY + 50, 'МСК', F(MAN, 15, 800), (200, 198, 206), 3)
    sc.layer(lay)

    rg = Image.new('L', (W, H), 0)
    ImageDraw.Draw(rg).ellipse((BX - BR, BY - BR, BX + BR, BY + BR), outline=255, width=4)
    ring = _blur_arr(np.asarray(rg, F32) / 255, 10)
    B = (int(BX - BR - 50), int(BY - BR - 50), int(BX + BR + 50), int(BY + BR + 50))
    accv = np.array(versus._mix(acc, 0.3), F32)
    X0, X1 = 360, 720
    wsl = wide[:, X0:X1, None] * accv
    ringc = ring[B[1]:B[3], B[0]:B[2], None] * accv
    xs, ys = xx[:, X0:X1], yy[:, X0:X1]

    def seam_life(img, i, tau):
        k = 0.5 + 0.5 * math.sin(2 * math.pi * 2 * tau)
        img[:, X0:X1] += wsl * (0.35 + 0.45 * k) * 2.2
        img[B[1]:B[3], B[0]:B[2]] += ringc * (1.2 + 1.6 * k)
        p = (2 * tau) % 1.0                                # искра бежит по шву сверху вниз дважды за цикл
        y = -120 + p * (H + 240)
        x = _seam_x(y)
        dist2 = (xs - x) ** 2 + (ys - y) ** 2
        along = (ys - y)
        g = np.exp(-dist2 / (2 * 9 ** 2)) * 1.0 + np.exp(-dist2 / (2 * 34 ** 2)) * 0.45
        tail = np.exp(-((xs - _seam_x(ys)) ** 2) / (2 * 3.5 ** 2)) * np.exp(-np.clip(-along, 0, None) / 160) * \
            (along < 0) * 0.8
        img[:, X0:X1] += (g + tail)[..., None] * np.array(versus._mix(acc, 0.6), F32)
    sc.dyn(seam_life)

    # имена клубов под эмблемами, линия, прогноз, марка
    lay = _layer()
    d = ImageDraw.Draw(lay)
    for cl, ex in ((m.home, SPLIT_HOME_X), (m.away, SPLIT_AWAY_X)):
        f = _fit(cl['ru'].upper(), 390, 76, ALU, 900)
        _shadow_text(lay, ex, 618, cl['ru'].upper(), f, WHITE, blur=14, off=(0, 5), alpha=220)
    y = 770
    if m.odds:
        _odds_row(d, 540, y, m.odds, acc, pw=104, ph=50, gap=16, size=31, lab=(205, 203, 212))
        _t(d, 540, y + 68, 'ОСНОВНОЕ ВРЕМЯ', F(MAN, 13, 700), (150, 148, 158))
        y = 878
    if m.pick:
        _pick_bar(lay, (80, y, 1000, y + 64), m.pick, m.kef, acc, bg=(12, 11, 16, 230), size=30)
    _brand(d, 540, 1050, acc, m.tag, 24)
    sc.layer(lay)
    return sc


# ═════════════════════════════ 4. ПРОГНОЗ КРУПНО ═════════════════════════════
PICK_RECTS = {'home': (60, 44, 380, 290), 'away': (700, 44, 1020, 290)}
PICK_EM = 172


def pick_geometry(side):
    x0, y0, x1, y1 = PICK_RECTS[side]
    return va.side_geometry('pick', side, (W, H), (x0, y0, x1, y1), PICK_EM, ((x0 + x1) / 2, (y0 + y1) / 2 + 4))


def _pick(m, plates_dir):
    sc = Scene()
    acc = m.acc
    sc.static(_bg((14, 13, 17), [(540, 640, 460, acc, 0.07), (540, 120, 600, (36, 38, 50), 0.4)], vignette=0.35))
    sc.dyn(Plate(sc, m.home, 'home', m.league, plates_dir, pick_geometry('home')))
    sc.dyn(Plate(sc, m.away, 'away', m.league, plates_dir, pick_geometry('away')))

    lay = _layer()
    d = ImageDraw.Draw(lay)
    for cl, side in ((m.home, 'home'), (m.away, 'away')):
        x0, y0, x1, y1 = PICK_RECTS[side]
        f = _fit(cl['ru'].upper(), x1 - x0 + 10, 38, OSW, 700)
        _t(d, (x0 + x1) / 2, 336, cl['ru'].upper(), f, WHITE)
    # центр сверху: дата, время
    if m.date:
        _t(d, 540, 108, m.date.upper(), _fit(m.date.upper(), 290, 26, OSW, 600), acc)
    if m.time:
        _t(d, 540, 172, m.time, _fit(m.time, 290, 84, OSW, 700), WHITE)
    _t(d, 540, 238, 'время московское', F(MAN, 18, 600), (200, 198, 206))
    # разделитель с «ПРОГНОЗ»
    fl = F(MAN, 22, 800)
    label = 'ПРОГНОЗ' if m.pick else 'НАЧАЛО МАТЧА'
    lw = _spaced(d, 540, 404, label, fl, acc, 7)
    for s in (-1, 1):
        x_in = 540 + s * (lw / 2 + 22)
        x_out = 540 + s * 450
        d.line((x_in * SS, 404 * SS, x_out * SS, 404 * SS), fill=acc + (150,), width=2 * SS)
    # главное: прогноз
    hero = (m.pick or ('%s · %s' % (m.date, m.time))).upper()
    f, lines, lh = _wrap_fit(hero, 920, 270, 150, ALU, 900, max_lines=3, lead=0.94)
    y = 444 + (270 - lh * len(lines)) / 2
    for ln in lines:
        _shadow_text(lay, 540, y + lh / 2, ln, f, WHITE, blur=16, off=(0, 6), alpha=200)
        y += lh
    # линия снизу
    if m.odds:
        _odds_row(d, 540, 912, m.odds, acc, pw=92, ph=42, gap=14, size=25, fill=(30, 28, 34), txt=WHITE,
                  outline=acc + (150,), lab=(170, 168, 178), lab_size=13)
        _t(d, 540, 972, 'ОСНОВНОЕ ВРЕМЯ', F(MAN, 12, 700), (140, 138, 148))
    _brand(d, 540, 1052, acc, m.tag, 24)
    sc.layer(lay)

    # капсула кэфа: золото, блик, мягкое свечение вокруг
    if m.pick and m.kef is not None:
        KH = 104
        fk, fkl = F(OSW, 78, 700), F(MAN, 24, 800)
        kt = _n(m.kef)
        kw = (fk.getlength(kt) + fkl.getlength('КЭФ:') + 26 * SS) / SS + 84
        kx0, ky0 = 540 - kw / 2, 738
        box = (kx0, ky0, kx0 + kw, ky0 + KH)
        msk = Image.new('L', (W * SS, H * SS), 0)
        ImageDraw.Draw(msk).rounded_rectangle([v * SS for v in box], radius=KH / 2 * SS, fill=255)
        cap_a = np.asarray(msk.resize((W, H), Image.LANCZOS), F32) / 255
        glow = _blur_arr(cap_a, 26)
        gold = np.zeros((H, W, 3), F32)
        xx, yy = _grid()
        tt = np.clip((yy - ky0) / KH, 0, 1)[..., None]
        top, bot = np.array(versus._mix(acc, 0.45), F32), np.array(versus._mix(acc, -0.18), F32)
        gold[:] = top * (1 - tt) + bot * tt
        sc.static(gold, cap_a)
        lay = _layer()
        d = ImageDraw.Draw(lay)
        _t(d, kx0 + 42, ky0 + KH / 2 + 2, 'КЭФ:', fkl, (40, 30, 10), anchor='lm')
        _t(d, kx0 + kw - 42, ky0 + KH / 2 + 4, kt, fk, (22, 16, 6), anchor='rm')
        rgb_t, a_t = _arr(lay)
        y0, y1, x0, x1 = int(ky0) - 60, int(ky0 + KH) + 60, int(kx0) - 60, int(kx0 + kw) + 60
        gl = glow[y0:y1, x0:x1, None] * np.array(acc, F32)
        cm = cap_a[y0:y1, x0:x1, None]
        xs, ys = xx[y0:y1, x0:x1], yy[y0:y1, x0:x1]

        def kef_life(img, i, tau):
            k = 0.5 + 0.5 * math.sin(2 * math.pi * tau)
            img[y0:y1, x0:x1] += gl * (0.18 + 0.22 * k)
            img[y0:y1, x0:x1] += _sweep(tau, xs, ys, kx0 - 260, kx0 + kw + 260, ang=-22, width=34, k=0.55,
                                        t0=0.15, t1=0.75) * cm
        sc.dyn(kef_life)
        sc.static(rgb_t, a_t)
    return sc


# ═════════════════════════════ 5. БИЛЕТ ═════════════════════════════
TW, TH, TSTUB = 960, 600, 700        # билет, линия отрыва


def _ticket_master(m):
    acc = m.acc
    hc, ac = m.home['color'], m.away['color']
    w, h = TW * SS, TH * SS
    s = SS
    # бумага: тёмная, к краям — цвета клубов
    xx, yy = np.meshgrid(np.linspace(0, 1, TW, dtype=F32), np.linspace(0, 1, TH, dtype=F32))
    base = np.zeros((TH, TW, 3), F32) + np.array((26, 24, 30), F32)
    base += np.array(hc, F32) * (0.30 * np.exp(-xx / 0.18))[..., None]
    base += np.array(ac, F32) * (0.30 * np.exp(-np.abs(xx - TSTUB / TW) / 0.16) * (xx < TSTUB / TW))[..., None]
    stub = xx >= TSTUB / TW
    base[stub] = np.array((32, 29, 26), F32) + np.array(acc, F32) * 0.07
    # гильош — тонкие волны по всему полю
    gu = np.sin(2 * np.pi * (yy * TH / 9 + 2.2 * np.sin(2 * np.pi * xx * 3)))
    base += (np.clip(gu, 0.85, 1) - 0.85)[..., None] * 60 * np.array((1.0, 0.95, 0.85), F32) * (~stub)[..., None]
    paper = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC).convert('RGBA')
    # форма: скругление, вырезы и перфорация
    mask = Image.new('L', (w, h), 0)
    dm = ImageDraw.Draw(mask)
    dm.rounded_rectangle((0, 0, w - 1, h - 1), radius=26 * s, fill=255)
    for cy in (0, TH):
        dm.ellipse(((TSTUB - 22) * s, (cy - 22) * s, (TSTUB + 22) * s, (cy + 22) * s), fill=0)
    for y in np.arange(36, TH - 30, 17):
        dm.ellipse(((TSTUB - 4) * s, (y - 4) * s, (TSTUB + 4) * s, (y + 4) * s), fill=0)
    foil = Image.new('L', (w, h), 0)
    df = ImageDraw.Draw(foil)
    lay = paper
    d = ImageDraw.Draw(lay)
    gold = versus._mix(acc, 0.15)
    # рамки фольгой
    d.rounded_rectangle((16 * s, 16 * s, (TSTUB - 18) * s, (TH - 16) * s), radius=16 * s, outline=gold + (200,), width=2 * s)
    df.rounded_rectangle((16 * s, 16 * s, (TSTUB - 18) * s, (TH - 16) * s), radius=16 * s, outline=255, width=2 * s)
    d.rounded_rectangle(((TSTUB + 18) * s, 16 * s, (TW - 16) * s, (TH - 16) * s), radius=16 * s, outline=gold + (160,),
                        width=2 * s)
    # шапка
    fh = _font(MAN, 17 * s, 800)
    _spaced_raw(d, 40 * s, 52 * s, 'ВХОДНОЙ БИЛЕТ', fh, gold, 5 * s)
    _spaced_raw(d, (TSTUB - 40) * s, 52 * s, '%s · СЕЗОН 2026/27' % m.tag, fh, (200, 196, 205), 3 * s, anchor='r')
    d.line((40 * s, 78 * s, (TSTUB - 40) * s, 78 * s), fill=gold + (120,), width=s)
    # эмблемы и имена
    EY, ES = 196, 168
    for cl, ex in ((m.home, 170), (m.away, TSTUB - 170)):
        em = poster._emblem(cl['ru'], ES * s)
        shd = Image.new('L', (w, h), 0)
        shd.paste(em.getchannel('A').point(lambda v: v * 0.6), (int(ex * s - em.width / 2 + 6 * s),
                                                                   int(EY * s - em.height / 2 + 12 * s)))
        blk = Image.new('RGBA', (w, h), (0, 0, 0, 255))
        blk.putalpha(shd.filter(ImageFilter.GaussianBlur(12 * s)))
        lay.alpha_composite(blk)
        lay.alpha_composite(em, (int(ex * s - em.width / 2), int(EY * s - em.height / 2)))
        nm = cl['ru'].upper()
        f = _fit_raw(nm, 270 * s, 34 * s, OSW, 700)
        d.text((ex * s, 314 * s), nm, font=f, fill=WHITE, anchor='mm')
    _t_raw = lambda x, y, t, f, c, a='mm': d.text((x * s, y * s), t, font=f, fill=c, anchor=a)
    _t_raw(TSTUB / 2, EY, '—', _font(OSW, 54 * s, 500), gold)
    # линия
    if m.odds:
        fo, fl = _font(OSW, 24 * s, 600), _font(MAN, 13 * s, 800)
        pw, gap = 96, 14
        x = TSTUB / 2 - (3 * pw + 2 * gap) / 2
        for lab, v in zip(('П1', 'Х', 'П2'), m.odds):
            d.rounded_rectangle((x * s, 352 * s, (x + pw) * s, 390 * s), radius=10 * s, outline=gold + (190,), width=2 * s)
            _t_raw(x + 26, 371, lab, fl, (190, 186, 196))
            _t_raw(x + pw - 12, 372, _n(v), fo, WHITE, 'rm')
            x += pw + gap
    # поля: дата, ряд, место (= время), пояс
    d.line((40 * s, 414 * s, (TSTUB - 40) * s, 414 * s), fill=gold + (90,), width=s)
    tparts = (m.time or '').split(':')
    hh, mm_ = (tparts + ['', ''])[:2] if len(tparts) == 2 else (m.time, '')
    fields = [('ДАТА', (m.date or '').upper(), 236), ('РЯД', hh, 124), ('МЕСТО', mm_, 136), ('ВРЕМЯ', 'МСК', 124)]
    x = 40
    fl = _font(MAN, 13 * s, 800)
    for i, (lab, val, fw) in enumerate(fields):
        _spaced_raw(d, (x + 6) * s, 444 * s, lab, fl, (170, 166, 176), 3 * s)
        fv = _fit_raw(val, (fw - 34) * s, 46 * s, OSW, 700)
        d.text(((x + 6) * s, 488 * s), val, font=fv, fill=gold if lab in ('РЯД', 'МЕСТО') else WHITE, anchor='lm')
        x += fw
        if i < len(fields) - 1:
            d.line(((x - 10) * s, 432 * s, (x - 10) * s, 512 * s), fill=gold + (70,), width=s)
    _t_raw(TSTUB / 2, 548, 'ряд и место — это время начала: %s по Москве' % (m.time or ''), _font(MAN, 14 * s, 600),
           (150, 146, 158))
    # корешок
    SX = (TSTUB + TW) / 2
    _spaced_raw(d, SX * s, 52 * s, 'КОНТРОЛЬ', fh, gold, 4 * s, anchor='m')
    d.line(((TSTUB + 36) * s, 78 * s, (TW - 34) * s, 78 * s), fill=gold + (120,), width=s)
    y = 120
    if m.pick:
        _spaced_raw(d, SX * s, y * s, 'ПРОГНОЗ', _font(MAN, 15 * s, 800), (200, 196, 206), 3 * s, anchor='m')
        f, lines, lh = _wrap_fit(_cap(m.pick), 210, 170, 38, OSW, 600, max_lines=4, lead=1.08)
        yy0 = y + 30
        for ln in lines:
            d.text((SX * s, (yy0 + lh / 2) * s), ln, font=f, fill=WHITE, anchor='mm')
            yy0 += lh
        y = max(yy0 + 18, 300)
        if m.kef is not None:
            _spaced_raw(d, SX * s, y * s, 'КЭФ', _font(MAN, 15 * s, 800), (200, 196, 206), 3 * s, anchor='m')
            d.text((SX * s, (y + 44) * s), _n(m.kef), font=_font(OSW, 62 * s, 700), fill=gold, anchor='mm')
            df.text((SX * s, (y + 44) * s), _n(m.kef), font=_font(OSW, 62 * s, 700), fill=255, anchor='mm')
    else:
        d.text((SX * s, 200 * s), m.time or '', font=_font(OSW, 66 * s, 700), fill=gold, anchor='mm')
        _spaced_raw(d, SX * s, 250 * s, 'МСК', _font(MAN, 15 * s, 800), (200, 196, 206), 3 * s, anchor='m')
    # штрихкод и марка
    rng = np.random.default_rng(sum(map(ord, m.home['ru'] + m.away['ru'])))
    bx = TSTUB + 46
    while bx < TW - 46:
        bw = float(rng.choice([1.5, 2.5, 3.5]))
        d.rectangle((bx * s, 470 * s, (bx + bw) * s, 530 * s), fill=(222, 218, 210))
        bx += bw + float(rng.choice([2, 3, 4.5]))
    d.text((SX * s, 556 * s), 'JARVIS', font=_font(OSW, 22 * s, 700), fill=WHITE, anchor='mm')
    # фольга — шапка и рамка
    _spaced_raw(df, 40 * s, 52 * s, 'ВХОДНОЙ БИЛЕТ', fh, 255, 5 * s)
    a = np.minimum(np.asarray(lay.getchannel('A')), np.asarray(mask))
    lay.putalpha(Image.fromarray(a))
    return lay, foil


def _spaced_raw(d, x, y, text, f, fill, sp, anchor='l'):
    tw = sum(f.getlength(c) for c in text) + sp * (len(text) - 1)
    cx = x - {'l': 0, 'm': tw / 2, 'r': tw}[anchor]
    for c in text:
        d.text((cx, y), c, font=f, fill=fill, anchor='lm')
        cx += f.getlength(c) + sp


def _fit_raw(text, max_w, size, name, wght):
    s = int(size)
    while s > 10:
        f = _font(name, s, wght)
        if f.getlength(text) <= max_w:
            return f
        s -= max(1, s // 40)
    return _font(name, 10, wght)


def _ticket(m, plates_dir):
    sc = Scene()
    acc = m.acc
    sc.static(_bg((13, 12, 16), [(300, 300, 420, m.home['color'], 0.12), (800, 700, 420, m.away['color'], 0.12),
                                 (540, 470, 500, acc, 0.05)], vignette=0.4))
    # фон: тонкая сетка мест на трибуне (точки)
    lay = _layer()
    d = ImageDraw.Draw(lay)
    for row in range(14):
        y = 60 + row * 74
        for k in range(16):
            x = 40 + k * 68 + (row % 2) * 34
            d.rounded_rectangle(((x - 14) * SS, (y - 8) * SS, (x + 14) * SS, (y + 8) * SS), radius=6 * SS,
                                fill=(255, 255, 255, 9))
    sc.layer(lay)
    master, foil = _ticket_master(m)

    def shine(tau, xx, yy, f):
        sw = _sweep(tau, xx, yy, -400, 1500, ang=-24, width=70, k=0.20, rainbow=0.55, t0=0.05, t1=0.8)
        sp = _sweep(tau, xx, yy, -400, 1500, ang=-24, width=110, k=0.30, rainbow=0.0, t0=0.05, t1=0.8)
        return sw + sp * f[..., None]
    sc.dyn(Rigid(sc, master, 540, 462, angle=-3.0, bob=7, sway=0.7, foil=foil, shine=shine, shadow=(12, 30, 26, 0.7)))
    lay = _layer()
    d = ImageDraw.Draw(lay)
    _t(d, 540, 872, ('%s — %s' % (m.home['ru'], m.away['ru'])).upper(),
       _fit(('%s — %s' % (m.home['ru'], m.away['ru'])).upper(), 860, 30, OSW, 600), (220, 218, 226))
    sub = ' · '.join(x for x in (m.date, (m.time + ' МСК') if m.time else '') if x)
    _t(d, 540, 916, sub.upper(), F(MAN, 18, 700), acc)
    _brand(d, 540, 1046, acc, m.tag, 24)
    sc.layer(lay)
    return sc


# ═════════════════════════════ 6. КАРТОЧКИ ═════════════════════════════
CW, CH = 392, 560


def _card_master(cl, side, m, odd, number):
    acc = m.acc
    s = SS
    w, h = CW * s, CH * s
    col = cl['color']
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # рамка: металл цвета клуба (вертикальный градиент), внутри тёмное поле
    yy = np.linspace(0, 1, CH, dtype=F32)[:, None, None]
    hi, lo = np.array(versus._mix(col, 0.55), F32), np.array(versus._mix(col, -0.35), F32)
    mid = np.array(col, F32)
    grad = np.where(yy < 0.5, hi * (1 - yy * 2) + mid * yy * 2, mid * (2 - yy * 2) + lo * (yy * 2 - 1))
    grad = np.repeat(grad, CW, axis=1)
    frame = Image.fromarray(np.clip(grad, 0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC).convert('RGBA')
    msk = Image.new('L', (w, h), 0)
    ImageDraw.Draw(msk).rounded_rectangle((0, 0, w - 1, h - 1), radius=24 * s, fill=255)
    lay.paste(frame, (0, 0), msk)
    d.rounded_rectangle((10 * s, 10 * s, (CW - 10) * s, (CH - 10) * s), radius=17 * s, fill=(18, 17, 22))
    d.rounded_rectangle((10 * s, 10 * s, (CW - 10) * s, (CH - 10) * s), radius=17 * s,
                        outline=versus._mix(col, 0.7) + (120,), width=s)
    # окно с узором клуба и эмблемой
    AX0, AY0, AX1, AY1 = 24, 76, CW - 24, 384
    pn = versus._panel(AX1 - AX0, AY1 - AY0, col, ((AX1 - AX0) * 0.5, (AY1 - AY0) * 0.45), 11 if side == 'home' else 23,
                       'down', dim=0.5).resize(((AX1 - AX0) * s, (AY1 - AY0) * s), Image.BICUBIC)
    pm = Image.new('L', pn.size, 0)
    ImageDraw.Draw(pm).rounded_rectangle((0, 0, pn.width - 1, pn.height - 1), radius=12 * s, fill=255)
    lay.paste(pn, (AX0 * s, AY0 * s), pm)
    em = poster._emblem(cl['ru'], 236 * s)
    ex, ey = (AX0 + AX1) / 2, (AY0 + AY1) / 2 + 4
    shd = Image.new('L', (w, h), 0)
    shd.paste(em.getchannel('A').point(lambda v: v * 0.6), (int(ex * s - em.width / 2 + 8 * s), int(ey * s - em.height / 2 + 16 * s)))
    blk = Image.new('RGBA', (w, h), (0, 0, 0, 255))
    blk.putalpha(shd.filter(ImageFilter.GaussianBlur(16 * s)))
    lay.alpha_composite(blk)
    lay.alpha_composite(em, (int(ex * s - em.width / 2), int(ey * s - em.height / 2)))
    # верх: «ХОЗЯЕВА/ГОСТИ», номер; значок с коэффициентом
    fl = _font(MAN, 15 * s, 800)
    _spaced_raw(d, 28 * s, 44 * s, 'ХОЗЯЕВА' if side == 'home' else 'ГОСТИ', fl, versus._mix(col, 0.55), 3 * s)
    if odd is not None:
        lab = 'П1' if side == 'home' else 'П2'
        bw, bh = 104, 40
        bx0, by0 = CW - 24 - bw, 24
        d.rounded_rectangle((bx0 * s, by0 * s, (bx0 + bw) * s, (by0 + bh) * s), radius=bh / 2 * s, fill=acc)
        d.text(((bx0 + 16) * s, (by0 + bh / 2 + 1) * s), lab, font=_font(MAN, 14 * s, 800), fill=(40, 30, 10), anchor='lm')
        d.text(((bx0 + bw - 14) * s, (by0 + bh / 2 + 1) * s), _n(odd), font=_font(OSW, 24 * s, 700), fill=(20, 16, 8),
               anchor='rm')
    # имя, город/дивизион
    nm = cl['ru'].upper()
    f = _fit_raw(nm, (CW - 56) * s, 50 * s, ALU, 900)
    d.text((CW / 2 * s, 428 * s), nm, font=f, fill=WHITE, anchor='mm')
    sub = (cl['sub'] or ('Москва' if 'Москва' in cl['ru'] else '')).upper()
    if sub:
        _spaced_raw(d, CW / 2 * s, 470 * s, sub, _fit_raw(sub, (CW - 80) * s, 14 * s, MAN, 700),
                    versus._mix(col, 0.55), 2 * s, anchor='m')
    d.line((40 * s, 498 * s, (CW - 40) * s, 498 * s), fill=(255, 255, 255, 40), width=s)
    fsm = _font(MAN, 12 * s, 700)
    d.text((40 * s, 524 * s), 'КОЛЛЕКЦИЯ JARVIS', font=fsm, fill=(150, 148, 158), anchor='lm')
    d.text(((CW - 40) * s, 524 * s), '№ %02d · %s' % (number, m.tag), font=fsm, fill=(150, 148, 158), anchor='rm')
    a = np.minimum(np.asarray(lay.getchannel('A')), np.asarray(msk))
    lay.putalpha(Image.fromarray(a))
    foil = Image.new('L', (w, h), 0)
    df = ImageDraw.Draw(foil)
    df.rounded_rectangle((0, 0, w - 1, h - 1), radius=24 * s, fill=150)
    df.rounded_rectangle((10 * s, 10 * s, (CW - 10) * s, (CH - 10) * s), radius=17 * s, fill=40)
    df.rounded_rectangle((AX0 * s, AY0 * s, AX1 * s, AY1 * s), radius=12 * s, fill=255)
    return lay, foil


def _cards(m, plates_dir):
    sc = Scene()
    acc = m.acc
    sc.static(_bg((13, 12, 16), [(290, 470, 330, m.home['color'], 0.20), (790, 470, 330, m.away['color'], 0.20),
                                 (540, 140, 380, acc, 0.05)], vignette=0.42))
    odds = m.odds or (None, None, None)
    hm, hf = _card_master(m.home, 'home', m, odds[0], 1)
    am, af = _card_master(m.away, 'away', m, odds[2], 2)

    def shine(tau, xx, yy, f):
        sw = _sweep(tau, xx, yy, -300, 1400, ang=-30, width=80, k=0.26, rainbow=0.75, t0=0.0, t1=1.0)
        return sw * (0.25 + 0.75 * f[..., None])
    sc.dyn(Rigid(sc, hm, 292, 498, angle=-7.5, bob=8, sway=1.1, phase=0.0, foil=hf, shine=shine,
                 shadow=(14, 30, 28, 0.75)))
    sc.dyn(Rigid(sc, am, 788, 498, angle=7.5, bob=8, sway=1.1, phase=math.pi, foil=af, shine=shine,
                 shadow=(14, 30, 28, 0.75)))
    lay = _layer()
    d = ImageDraw.Draw(lay)
    # верх: дата · время МСК
    if m.date or m.time:
        fd, ft = F(OSW, 32, 600), F(OSW, 58, 700)
        fz = F(MAN, 17, 800)
        parts = [(m.date.upper(), fd, acc), (m.time, ft, WHITE), ('МСК', fz, (200, 198, 206))]
        parts = [p for p in parts if p[0]]
        gap = 22 * SS
        tw = sum(p[1].getlength(p[0]) for p in parts) + gap * (len(parts) - 1)
        x = 540 * SS - tw / 2
        for t, f, c in parts:
            d.text((x, 104 * SS), t, font=f, fill=c, anchor='ls')
            x += f.getlength(t) + gap
    # монета «Х» между карточками
    if m.odds:
        CXc, CYc, R = 540, 498, 54
        sh = Image.new('L', lay.size, 0)
        ImageDraw.Draw(sh).ellipse(((CXc - R + 4) * SS, (CYc - R + 12) * SS, (CXc + R + 4) * SS, (CYc + R + 12) * SS),
                                   fill=200)
        blk = Image.new('RGBA', lay.size, (0, 0, 0, 255))
        blk.putalpha(sh.filter(ImageFilter.GaussianBlur(12 * SS)))
        lay.alpha_composite(blk)
        d.ellipse(((CXc - R) * SS, (CYc - R) * SS, (CXc + R) * SS, (CYc + R) * SS), fill=(20, 19, 24), outline=acc,
                  width=3 * SS)
        _t(d, CXc, CYc - 20, 'Х', F(OSW, 20, 600), (200, 198, 206))
        _t(d, CXc, CYc + 12, _n(m.odds[1]), F(OSW, 30, 700), acc)
    y = 862
    if m.pick:
        _pick_bar(lay, (70, y, 1010, y + 66), m.pick, m.kef, acc, bg=(16, 15, 20, 235), size=30)
        _t(d, 540, y + 98, 'основное время · коэффициенты на момент публикации' if m.odds else '', F(MAN, 13, 600),
           (130, 128, 138))
    elif m.odds:
        _t(d, 540, y + 30, 'ОСНОВНОЕ ВРЕМЯ', F(MAN, 14, 700), (150, 148, 158))
    _brand(d, 540, 1050, acc, m.tag, 24)
    sc.layer(lay)
    return sc


BUILDERS = {'tablo': _tablo, 'ice': _ice, 'split': _split, 'pick': _pick, 'ticket': _ticket, 'cards': _cards}


# ───────────────────────────── сборка ─────────────────────────────
def scene(home, away, date, time, odds=None, league='KHL', style='tablo', pick=None, kef=None,
          plates_dir='out/anim/plates'):
    return BUILDERS[style](_match(home, away, league, date, time, odds, pick, kef), plates_dir)


def still(home, away, path_jpg, date, time, odds=None, league='KHL', style='tablo', pick=None, kef=None,
          plates_dir='out/anim/plates', tau=0.0):
    """Один кадр (для проверки раскладки) → path_jpg."""
    sc = scene(home, away, date, time, odds, league, style, pick, kef, plates_dir)
    i = int(round(tau * SECONDS * FPS))
    if any(isinstance(it[1], Plate) for it in sc.items if it[0] == 'd'):
        fr = None
        for k in range(i + 1):
            fr = sc.frame(k, k / (SECONDS * FPS))
    else:
        fr = sc.frame(i, tau)
    sc.close()
    os.makedirs(os.path.dirname(path_jpg) or '.', exist_ok=True)
    Image.fromarray(fr).save(path_jpg, quality=92)
    return path_jpg


def render(home, away, path_mp4, date, time, odds=None, league='KHL', style='tablo', pick=None, kef=None,
           plates_dir='out/anim/plates', sheet=None, first=None, target_mb=2.8):
    """Анимированный предматчевый постер стиля style → path_mp4 (H.264 1080², 30 fps, 4 с, бесшовный цикл).
    odds — (П1, Х, П2) или None; pick/kef — прогноз и его коэффициент (необязательно).
    first — путь .jpg первого кадра (True — рядом с mp4); sheet — контактный лист 6 кадров (True — рядом).
    → dict(path, seconds — время сборки, mb — размер)."""
    t0 = _clock.time()
    sc = scene(home, away, date, time, odds, league, style, pick, kef, plates_dir)
    n = SECONDS * FPS
    try:
        frames = [sc.frame(i, i / n) for i in range(n)]
    finally:
        sc.close()
    os.makedirs(os.path.dirname(path_mp4) or '.', exist_ok=True)
    va._encode_mp4(frames, path_mp4, FPS, target_mb)
    base = os.path.splitext(path_mp4)[0]
    if first:
        Image.fromarray(frames[0]).save(base + '.jpg' if first is True else first, quality=92)
    if sheet:
        va._sheet(frames, base + '_frames.jpg' if sheet is True else sheet, FPS)
    return dict(path=path_mp4, seconds=_clock.time() - t0, mb=os.path.getsize(path_mp4) / 1e6)


def overview(tiles, path, cols=None, size=420):
    """Лист «все стили рядом»: tiles — [(подпись ряда, [(подпись, путь .jpg), …]), …]."""
    cols = cols or max(len(t[1]) for t in tiles)
    gap, lab, head = 12, 34, 40
    rows = len(tiles)
    sheet = Image.new('RGB', (cols * size + (cols + 1) * gap, rows * (size + lab + head) + (rows + 1) * gap),
                      (32, 32, 36))
    d = ImageDraw.Draw(sheet)
    fh, fl = brand_kit.font(MAN, 22, 800), brand_kit.font(MAN, 19, 700)
    y = gap
    for title, row in tiles:
        d.text((gap + 4, y + head / 2), title, font=fh, fill=(240, 240, 244), anchor='lm')
        y += head
        for k, (label, p) in enumerate(row):
            x = gap + k * (size + gap)
            d.text((x + 4, y + lab / 2), label, font=fl, fill=(230, 200, 120), anchor='lm')
            sheet.paste(Image.open(p).convert('RGB').resize((size, size), Image.LANCZOS), (x, y + lab))
        y += size + lab + gap
    sheet.save(path, quality=90)
    return path
