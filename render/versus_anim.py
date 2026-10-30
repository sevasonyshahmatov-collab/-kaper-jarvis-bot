"""Анимированный «Versus» (15.10.2026, просьба владельца — «как GIF большого формата»): тот же баннер, что
versus.render, но фон панелей клубов колышется как флаг (бегущая волна со светотенью складок, край панели волнится),
а эмблемы плавно «парят» (покачивание на несколько px, лёгкий поворот, «дыхание» масштаба, тень отстаёт).
Текст, плашки и марка неподвижны и чёткие: рисуются один раз в 3× (versus.layers) и уменьшаются.
Цикл бесшовный: все периоды целое число раз укладываются в длительность.

    import versus_anim
    versus_anim.render_anim('Торпедо', 'Динамо Москва', 'out/vs.mp4', date='16 октября', time='19:00',
                            odds=(2.12, 3.76, 3.00), gif=True, sheet=True)
→ MP4 H.264 yuv420p 1080×1080, 30 fps, без звука — Telegram показывает его как GIF-анимацию (≤ target_mb);
  gif=True — превью 540×540, 15 fps рядом (.gif); sheet=True — контактный лист 6 кадров (_frames.jpg).

Быстрее для потока матчей — плашки клубов (рисуются один раз, ~1 мин; сборка матча — только кодирование):
    versus_anim.render_plate('Торпедо', 'home', 'KHL', (40, 80, 180), 'out/anim/plates')   # → .webm (VP9 + альфа) + .json
    versus_anim.compose('Торпедо', 'Динамо Москва', 'out/anim/vs.mp4', date='16 октября', time='19:00',
                        odds=(2.12, 3.76, 3.00), plates_dir='out/anim/plates', gif=True)   # недостающие плашки дорисует
Запуск из папки render.
"""
import hashlib
import json
import os
import subprocess
from collections import namedtuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import brand_kit
import football
import nhl
import poster
import versus

W, H = versus.W, versus.H
SS = 3                       # эмблемы и текст рисуются в SS раз крупнее и уменьшаются — без «лесенки» и мыла
PAD = 30                     # запас узора панели за краями (больше амплитуды волны)
GRAIN = 2                    # текстура холста как у статичного баннера (quality.texture(img, 2))

# Волны «флага»: (амплитуда px, длина волны px, наклон фронта °, циклов за цикл анимации (4 с), фаза, вес в светотени).
# Все бегут от «древка» к свободному краю почти с одной скоростью (~90–100 px/с) — ткань, а не желе; светотень
# в основном от длинной складки, мелкая рябь её только оживляет.
WAVES = ((6.5, 360, 10, 1, 0.0, 1.0), (2.2, 200, -14, 2, 1.7, 0.5), (0.8, 125, 24, 3, 4.1, 0.25))
DX_K = 0.16                  # горизонтальный сдвиг рисунка в складках (доля от вертикального, в квадратуре)
FOLD = 0.15                  # глубина светотени складок (доля яркости)
LIGHT = (0.85, 0.5)          # откуда свет (слева сверху): веса наклонов по u и v

# «Парение» эмблем: покачивание вверх-вниз, лёгкий дрейф вбок, поворот (°), масштаб; гости — со сдвигом фазы
BOB, DRIFT, ROT, BREATH = 5.0, 1.6, 1.4, 0.014


def _smooth(t):
    return versus._smooth(t)


def _bilinear(arr, x, y):
    """arr[y, x] с билинейной интерполяцией в дробных точках (за краями — крайние значения)."""
    h, w = arr.shape[:2]
    x = np.clip(np.asarray(x, np.float32), 0, w - 1.001)
    y = np.clip(np.asarray(y, np.float32), 0, h - 1.001)
    x0 = x.astype(np.int32)
    y0 = y.astype(np.int32)
    fx, fy = x - x0, y - y0
    flat = arr.reshape(h * w, -1) if arr.ndim == 3 else arr.reshape(-1)
    i = (y0 * w + x0).ravel()
    a, b, c, d = (np.take(flat, j, axis=0) for j in (i, i + 1, i + w, i + w + 1))
    if arr.ndim == 3:
        shp = x.shape + (arr.shape[2],)
        fx, fy = fx.reshape(-1, 1), fy.reshape(-1, 1)
    else:
        shp = x.shape
        fx, fy = fx.ravel(), fy.ravel()
    return ((a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy).reshape(shp)


class _Canvas:
    """Текстура холста poster._canvas_texture (те же нити и зерно, seed 3), но как поле, которое можно взять в любой
    точке: на панелях и эмблемах она едет вместе с тканью/эмблемой, на неподвижном — стоит на месте."""

    def __init__(self, strength=GRAIN, seed=3, size=(W, H)):
        self.size = fw, fh = size                        # размер кадра (баннер 1080², сторис 1080×1920, аватар 800²)
        rng = np.random.default_rng(seed)
        low = rng.normal(0, 1, (fh // 8 + 2, fw // 8 + 2)).astype(np.float32)
        low = np.asarray(Image.fromarray(((low * 30) + 128).clip(0, 255).astype('uint8')).resize((fw, fh), Image.BICUBIC))
        self.phase = (low.astype(np.float32) - 128) / 30 * 0.9
        self.fine = rng.normal(0, 1, (fh, fw)).astype(np.float32)
        self.k = strength
        yy, xx = np.mgrid[0:fh, 0:fw].astype(np.float32)
        self.screen = self.at(xx, yy)

    def at(self, x, y):
        """Значение текстуры в точках (x, y) неподвижного кадра (баннер 1080×1080 или self.size)."""
        fw, fh = self.size
        ang = np.deg2rad(-30)
        u = x * np.cos(ang) + y * np.sin(ang)
        v = -x * np.sin(ang) + y * np.cos(ang)
        thread = np.sin(2 * np.pi * u / 4.6 + _bilinear(self.phase, x, y))
        cross = np.sin(2 * np.pi * v / 3.4) * 0.35
        weave = np.where(thread > 0, thread, thread * 0.6) + cross
        fine = self.fine[np.clip(np.rint(y).astype(np.int32), 0, fh - 1), np.clip(np.rint(x).astype(np.int32), 0, fw - 1)]
        return ((0.055 * weave + 0.045 * fine) * self.k).astype(np.float32)

    @staticmethod
    def apply(rgb, tex):
        """Та же формула, что в poster._canvas_texture."""
        lum = rgb.mean(axis=2, keepdims=True) / 255.0
        return rgb * (1 + tex[..., None] * (0.6 + 0.8 * lum)) + tex[..., None] * 10


class _Flag:
    """Панель клуба, колышущаяся как флаг. «Древко» — внешний край (хозяева слева, гости справа), волна бежит
    к середине баннера и к свободному краю нарастает. Край, упирающийся в рамку кадра, уходит за кадр.
    src(w, h, pad) → RGB (w + 2pad)×(h + 2pad) — свой рисунок ткани вместо колец versus._panel (аватар канала)."""

    def __init__(self, spec, pole, phase, canvas, src=None):
        (x0, y0, x1, y1), col, team, seed, ctr, fd = spec
        self.rect, self.pole, self.phase, self.cv = (x0, y0, x1, y1), pole, phase, canvas
        self.w, self.h = w, h = x1 - x0, y1 - y0
        img = src(w, h, PAD) if src else versus._panel(w, h, col, (ctr[0] * w, ctr[1] * h), seed, fd, pad=PAD)
        self.src = np.asarray(img.convert('RGB'), np.float32)
        # кусок кадра, который панель может занять
        FW, FH = canvas.size
        self.box = (max(0, x0 - PAD), max(0, y0 - PAD), min(FW, x1 + PAD), min(FH, y1 + PAD))
        bx0, by0, bx1, by1 = self.box
        yy, xx = np.mgrid[by0:by1, bx0:bx1].astype(np.float32)
        self.u, self.v = xx - x0, yy - y0
        q = self.u / w if pole == 'l' else 1 - self.u / w
        self.env = (0.4 + 0.6 * _smooth(q)).astype(np.float32)
        # края у рамки кадра не рисуем — там панель продолжается за кадр
        self.open = dict(l=x0 <= 0, t=y0 <= 0, r=x1 >= FW, b=y1 >= FH)

    def frame(self, tau, shadow, sh_off, sh_k):
        """→ (box, rgb, alpha, tex) куска кадра в момент tau ∈ [0, 1).
        shadow — тень эмблемы на ткани (весь кадр, 0..1), sh_off — её сдвиг (px), sh_k — множитель силы."""
        u, v, env = self.u, self.v, self.env
        sgn = 1.0 if self.pole == 'l' else -1.0
        z = np.zeros_like(u)
        zq = np.zeros_like(u)
        slope = np.zeros_like(u)
        smax = 0.0
        for amp, lam, ang, n, ph, wl in WAVES:
            kx = sgn * np.cos(np.radians(ang)) / lam
            ky = np.sin(np.radians(ang)) / lam
            p = (np.float32(2 * np.pi * kx) * u + np.float32(2 * np.pi * ky) * v
                 + np.float32((ph + self.phase - 2 * np.pi * n * tau) % (2 * np.pi)))
            s, c = np.sin(p), np.cos(p)
            z += amp * s
            zq += amp * c
            # наклон складки к свету слева сверху (вес wl — вклад волны в светотень)
            g = wl * amp * 2 * np.pi * (LIGHT[0] * kx + LIGHT[1] * ky)
            slope += np.float32(g) * c
            smax += abs(g)
        dy = env * z
        dx = DX_K * env * zq * sgn
        us, vs = u - dx, v - dy                       # откуда в неподвижной панели берётся точка
        rgb = _bilinear(self.src, us + PAD, vs + PAD)
        # светотень: −1…1 по наклону; блик чуть уже и ярче тени — похоже на атлас/полиэстер флага
        slope = env * slope / smax
        shade = 1 + FOLD * (slope + 0.3 * np.maximum(slope, 0) ** 2)
        x0, y0 = self.rect[:2]
        sh = _bilinear(shadow, x0 + us - sh_off[0], y0 + vs - sh_off[1]) * sh_k
        rgb = rgb * (shade * (1 - sh))[..., None]
        # маска панели со сглаженным волнистым краем
        dist = np.full_like(u, 1e3)
        if not self.open['l']:
            dist = np.minimum(dist, us + 0.5)
        if not self.open['r']:
            dist = np.minimum(dist, self.w - 0.5 - us)
        if not self.open['t']:
            dist = np.minimum(dist, vs + 0.5)
        if not self.open['b']:
            dist = np.minimum(dist, self.h - 0.5 - vs)
        alpha = np.clip(dist + 0.5, 0, 1)
        tex = self.cv.at(x0 + us, y0 + vs)
        return self.box, rgb, alpha, tex


class _Emblem:
    """Эмблема клуба, «парящая» над тканью: рисуется из мастера 3× (аффинное преобразование + уменьшение LANCZOS),
    тень на ткани отстаёт и чуть расходится, когда эмблема поднимается.
    art(size) → RGBA — своя «эмблема» вместо poster._emblem(team, size) (марка канала на аватаре)."""

    def __init__(self, team, cx, cy, size, canvas, margin=22, art=None):
        self.cv = canvas
        art = art or (lambda s: poster._emblem(team, s))
        em1 = art(size)                                  # 1× — как в статичном баннере (позиция и тень)
        self.master = art(size * SS)
        px, py = int(cx - em1.width / 2), int(cy - em1.height / 2)
        self.c = np.array((px + em1.width / 2, py + em1.height / 2))        # центр в покое (непрерывные координаты)
        self.tw, self.th = em1.width + 2 * margin, em1.height + 2 * margin
        self.ox, self.oy = px - margin, py - margin
        # тень — ровно как versus._paste_emblem при S = 1
        sh = Image.new('L', canvas.size, 0)
        sh.paste(Image.new('L', em1.size, 150), (int(cx - em1.width / 2 + 10), int(cy - em1.height / 2 + 22)),
                 em1.getchannel('A'))
        self.shadow = np.asarray(sh.filter(ImageFilter.GaussianBlur(26)), np.float32) / 255

    @staticmethod
    def motion(tau, ph):
        b = np.sin(2 * np.pi * tau + ph)
        ex = DRIFT * np.sin(2 * np.pi * tau + ph + np.pi / 2)
        ey = BOB * b
        rot = ROT * np.sin(2 * np.pi * tau + ph + 0.9)
        sc = 1 - BREATH * b                               # выше — крупнее (ближе к зрителю)
        return ex, ey, rot, sc, b

    def frame(self, tau, ph):
        """→ ((ox, oy), rgb, alpha, tex, (сдвиг тени), сила тени)."""
        ex, ey, rot, sc, b = self.motion(tau, ph)
        c = self.c + (ex, ey)
        th = np.radians(rot)
        cs, sn = np.cos(th), np.sin(th)
        # выход (тайл 3×) → вход (мастер): in = Cm + R(−θ)·(q − Ct)/s
        ct = SS * (c - (self.ox, self.oy))
        cm = np.array(self.master.size) / 2
        a, bb = cs / sc, sn / sc
        d, e = -sn / sc, cs / sc
        coef = (a, bb, cm[0] - a * ct[0] - bb * ct[1], d, e, cm[1] - d * ct[0] - e * ct[1])
        big = self.master.transform((self.tw * SS, self.th * SS), Image.AFFINE, coef, resample=Image.BICUBIC)
        tile = np.asarray(big.resize((self.tw, self.th), Image.LANCZOS), np.float32)
        alpha = tile[..., 3] / 255
        # текстура холста «приклеена» к эмблеме: точка тайла → точка эмблемы в покое
        yy, xx = np.mgrid[0:self.th, 0:self.tw].astype(np.float32)
        qx, qy = xx + self.ox + 0.5 - c[0], yy + self.oy + 0.5 - c[1]
        rx = self.c[0] + (cs * qx + sn * qy) / sc - 0.5
        ry = self.c[1] + (-sn * qx + cs * qy) / sc - 0.5
        tex = self.cv.at(rx, ry)
        sh_off = (0.5 * ex - 1.5 * b, 0.35 * ey - 3.0 * b)   # поднимается — тень отстаёт и уходит вниз-вправо
        return (self.ox, self.oy), tile[..., :3], alpha, tex, sh_off, 1 + 0.10 * b


def _over(dst, tdst, box, rgb, alpha, tex):
    x0, y0 = box[:2]
    h, w = alpha.shape
    a = alpha[..., None]
    dst[y0:y0 + h, x0:x0 + w] = dst[y0:y0 + h, x0:x0 + w] * (1 - a) + rgb * a
    tdst[y0:y0 + h, x0:x0 + w] = tdst[y0:y0 + h, x0:x0 + w] * (1 - alpha) + tex * alpha


def _drop_shadow(box, alpha, size=(W, H)):
    """Тень панели как в versus._draw_panels: сдвиг (14, 20), размытие 24, непрозрачность 120 → альфа на весь кадр."""
    x0, y0 = box[:2]
    h, w = alpha.shape
    fw, fh = size
    m = np.zeros((fh + 40, fw + 40), np.float32)
    m[y0 + 20:y0 + 20 + h, x0 + 14:x0 + 14 + w] = alpha
    m = Image.fromarray((m[:fh, :fw] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(24))
    return np.asarray(m, np.float32) / 255 * (120 / 255)


# Стороны баннера: (номер в versus._panel_specs, «древко» флага, фаза флага, фаза эмблемы). Фазы у стороны постоянные —
# любая плашка хозяев зациклена синхронно с любой плашкой гостей.
SIDES = {'home': (0, 'l', 0.0, 0.0), 'away': (1, 'r', 2.3, 0.6 * np.pi)}

# Геометрия плашки: имя (None — баннер Versus), кадр (w, h), прямоугольник панели, «древко» ('l'/'r'), фазы флага
# и эмблемы, seed и центр колец (доли), перелив, сторона эмблемы, центр эмблемы. Сторис и аватар задают свою геометрию —
# флаг, эмблема и плашки те же (render_plate(..., geom=...)).
Geometry = namedtuple('Geometry', 'name frame rect pole flag_phase emblem_phase seed ctr fade emblem emblem_c')


def banner_geometry(side, fade=('down', 'up')):
    """Геометрия стороны баннера Versus (versus._panel_specs, SIDES)."""
    i, pole, fph, eph = SIDES[side]
    (x0, y0, x1, y1), _, _, seed, ctr, fd = versus._panel_specs(None, None, None, None, fade)[i]
    return Geometry(None, (W, H), (x0, y0, x1, y1), pole, fph, eph, seed, ctr, fd, versus.EMBLEM,
                    ((x0 + x1) / 2, (y0 + y1) / 2 + versus.EMBLEM_DY))


def side_geometry(name, side, frame, rect, emblem, emblem_c, fade=None):
    """Своя геометрия для стороны side: фазы и рисунок колец — как у этой стороны в баннере (плашки хозяев и гостей
    по-прежнему зациклены синхронно), перелив — по умолчанию тоже."""
    b = banner_geometry(side)
    return b._replace(name=name, frame=tuple(frame), rect=tuple(rect), fade=b.fade if fade is None else fade,
                      emblem=emblem, emblem_c=tuple(emblem_c))


class _Side:
    """Половина баннера одного клуба: флаг-панель, «парящая» эмблема, её тень на ткани и тень панели на фоне.
    geom — своя геометрия (Geometry; по умолчанию сторона баннера), art/src — своя эмблема и рисунок ткани."""

    def __init__(self, team, side, color, canvas, fade=('down', 'up'), geom=None, art=None, src=None):
        g = geom or banner_geometry(side, fade)
        assert tuple(g.frame) == tuple(canvas.size), (g.frame, canvas.size)
        spec = (g.rect, color, team, g.seed, g.ctr, g.fade)
        self.rect, self.em_phase, self.size = g.rect, g.emblem_phase, canvas.size
        self.flag = _Flag(spec, g.pole, g.flag_phase, canvas, src)
        self.emblem = _Emblem(team, g.emblem_c[0], g.emblem_c[1], g.emblem, canvas, art=art)

    def layers(self, tau):
        """→ (тень панели на весь кадр, (box, rgb, alpha, tex) панели, (pos, rgb, alpha, tex) эмблемы)."""
        pos, ergb, ea, etex, sh_off, sh_k = self.emblem.frame(tau, self.em_phase)
        box, rgb, alpha, ftex = self.flag.frame(tau, self.emblem.shadow, sh_off, sh_k)
        return _drop_shadow(box, alpha, self.size), (box, rgb, alpha, ftex), (pos, ergb, ea, etex)


def _static(home, away, date, time, odds, league, tz, fade):
    """Неподвижные слои 1080²: фон (без текстуры), текст/плашки (rgb, alpha) и панели (versus._panel_specs)."""
    S0 = versus.S
    versus.S = SS                                         # текст — в 3× независимо от JARVIS_S
    try:
        ly = versus.layers(home, away, date, time, odds, league, tz, fade)
    finally:
        versus.S = S0
    bg = np.asarray(ly['bg'].convert('RGB').resize((W, H), Image.LANCZOS), np.float32)
    fg = np.asarray(ly['fg'].resize((W, H), Image.LANCZOS), np.float32)
    return bg, fg[..., :3], fg[..., 3] / 255, ly['specs']


class Banner:
    """Все слои один раз; frame(tau) → кадр uint8 1080×1080×3 (текстура холста — на итоговый кадр, как у статики)."""

    def __init__(self, home, away, date='', time='', odds=None, league='KHL', tz='время московское',
                 fade=('down', 'up'), grain=GRAIN):
        self.bg, self.fg_rgb, self.fg_a, specs = _static(home, away, date, time, odds, league, tz, fade)
        self.cv = _Canvas(grain)
        self.sides = [_Side(spec[2], side, spec[1], self.cv, fade) for spec, side in zip(specs, ('home', 'away'))]

    def frame(self, tau):
        return scene_frame(self.bg, self.cv, self.sides, self.fg_rgb, self.fg_a, tau)


def scene_frame(bg, cv, sides, fg_rgb, fg_a, tau):
    """Кадр сцены: фон bg (float RGB без зерна) → стороны (тень панели, флаг, эмблема) по порядку → неподвижный
    слой (fg_rgb, fg_a) → текстура холста cv на всё. → uint8 RGB."""
    img = bg.copy()
    tex = cv.screen.copy()
    for side in sides:                                    # хозяева, потом гости поверх
        sh, panel, emblem = side.layers(tau)
        img *= 1 - sh[..., None]
        _over(img, tex, *panel)
        _over(img, tex, *emblem)
    a = fg_a[..., None]
    img = img * (1 - a) + fg_rgb * a
    tex = tex * (1 - fg_a) + cv.screen * fg_a
    return np.clip(_Canvas.apply(img, tex), 0, 255).astype(np.uint8)


def _ffmpeg(args, frames=None):
    p = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + args, stdin=subprocess.PIPE)
    for f in frames or ():
        p.stdin.write(f.tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError('ffmpeg failed: %s' % ' '.join(args))


def _encode_mp4(frames, path, fps, target_mb):
    """H.264 yuv420p, весь цикл — одна GOP (ключевой только первый кадр), двухпроходный ABR под target_mb
    (зерно холста на движущейся ткани CRF-ом всё равно не влезает в 3 МБ)."""
    n = len(frames)
    fh, fw = frames[0].shape[:2]
    src = ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (fw, fh), '-r', str(fps), '-i', '-', '-an']
    common = ['-c:v', 'libx264', '-preset', 'veryslow', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
              '-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=lanczos+accurate_rnd+full_chroma_int',
              '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
              '-g', str(n), '-keyint_min', str(n), '-sc_threshold', '0', '-x264-params', 'ipratio=1.15',
              '-movflags', '+faststart']
    kbps = int(target_mb * 8e3 / (n / fps) * 0.94)
    log = path + '.x264pass'
    rate = ['-b:v', '%dk' % kbps, '-maxrate', '%dk' % int(kbps * 1.6), '-bufsize', '%dk' % (kbps * 2),
            '-passlogfile', log]
    _ffmpeg(src + common + rate + ['-pass', '1', '-f', 'mp4', os.devnull], frames)
    _ffmpeg(src + common + rate + ['-pass', '2', path], frames)
    for ext in ('-0.log', '-0.log.mbtree'):
        if os.path.exists(log + ext):
            os.remove(log + ext)
    return path


def _encode_gif(frames, path, fps, size=540, step=2):
    """Превью: 540², каждый 2-й кадр. Зерно холста перед уменьшением чуть размываем — иначе GIF вдвое тяжелее."""
    small = [np.asarray(Image.fromarray(f).filter(ImageFilter.GaussianBlur(1.2)).resize((size, size), Image.LANCZOS))
             for f in frames[::step]]
    _ffmpeg(['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (size, size), '-r', '%g' % (fps / step), '-i', '-',
             '-filter_complex', 'split[a][b];[a]palettegen=max_colors=128:stats_mode=full[p];'
                                '[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle',
             '-loop', '0', path], small)
    return path


def _sheet(frames, path, fps, n=6, cols=3, size=540):
    idx = [round(i * len(frames) / n) for i in range(n)]
    rows = (n + cols - 1) // cols
    gap, lab = 8, 30
    fh, fw = frames[0].shape[:2]
    th = round(size * fh / fw)                                    # высота плитки (сторис — вертикальные)
    sheet = Image.new('RGB', (cols * size + (cols + 1) * gap, rows * (th + lab) + (rows + 1) * gap), (40, 40, 44))
    d = ImageDraw.Draw(sheet)
    f = brand_kit.font('Manrope[wght].ttf', 18, 700)
    for k, i in enumerate(idx):
        x = gap + (k % cols) * (size + gap)
        y = gap + (k // cols) * (th + lab + gap)
        d.text((x + 4, y + 4), 'кадр %d · t = %.2f с' % (i, i / fps), font=f, fill=(230, 230, 235))
        sheet.paste(Image.fromarray(frames[i]).resize((size, th), Image.LANCZOS), (x, y + lab))
    sheet.save(path, quality=90)
    return path


def render_anim(home, away, path_mp4, date='', time='', odds=None, league='KHL', seconds=4, fps=30,
                tz='время московское', fade=('down', 'up'), gif=None, sheet=None, target_mb=3.0, grain=GRAIN):
    """Анимированный баннер «Versus» → path_mp4. Циклов волн/парения — целое число за seconds (база — 4 с),
    кадр seconds·fps совпадает с нулевым, так что зацикливание бесшовное.
    gif — путь превью .gif (True — рядом с mp4); sheet — путь контактного листа .jpg (True — рядом)."""
    banner = Banner(home, away, date, time, odds, league, tz, fade, grain)
    n = int(round(seconds * fps))
    reps = max(1, round(seconds / 4))                 # длиннее 4 с — те же скорости, цикл повторяется reps раз
    frames = [banner.frame((i / n * reps) % 1.0) for i in range(n)]
    os.makedirs(os.path.dirname(path_mp4) or '.', exist_ok=True)
    _encode_mp4(frames, path_mp4, fps, target_mb)
    base = os.path.splitext(path_mp4)[0]
    if gif:
        _encode_gif(frames, base + '.gif' if gif is True else gif, fps)
    if sheet:
        _sheet(frames, base + '_frames.jpg' if sheet is True else sheet, fps)
    return path_mp4


# ---------------- плашки клубов: рисуются один раз, матчи собираются из готовых ----------------
# Плашка — половина баннера одного клуба (флаг, эмблема, тень эмблемы на ткани, тень панели на фоне) с альфой и уже
# «вшитым» зерном холста; WEBM VP9 yuva420p + JSON рядом. Кэш — по клубу, стороне и цвету: цвет гостей меняется,
# если совпадает с цветом хозяев (versus._distinct), — например, Динамо против Торпедо и СКА — голубое.
#
#     versus_anim.compose('Торпедо', 'Динамо Москва', 'out/anim/vs.mp4', date='16 октября', time='19:00',
#                         odds=(2.12, 3.76, 3.00), plates_dir='out/anim/plates', gif=True)
PLATE_MARGIN = 100           # запас вокруг панели: волна + тень панели (сдвиг 14/20, размытие 24) целиком
PLATE_CRF = 20               # качество VP9 (меньше — точнее и тяжелее)


def plate_version(fps=30, frames=120, geom=None):
    """Версия плашки: меняется вместе с любым параметром вида — устаревшие плашки compose перерисует сам.
    geom — своя геометрия (сторис): входит в версию; у баннерных плашек версия прежняя."""
    look = (WAVES, DX_K, FOLD, LIGHT, BOB, DRIFT, ROT, BREATH, GRAIN, PAD, SS, SIDES, PLATE_MARGIN,
            versus.P1, versus.P2, versus.EMBLEM, versus.EMBLEM_DY, fps, frames)
    if geom is not None:
        look += (tuple(geom),)
    return 'versus-plate/1-' + hashlib.sha1(repr(look).encode()).hexdigest()[:10]


def _rgb(color):
    if isinstance(color, str):
        h = color.lstrip('#')
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(c) for c in color[:3])


def _club(team, league):
    """→ (ru-название, slug для имени файла)."""
    if league == 'NHL':
        nhl.register()
    elif football.is_foot(league):
        football.register()
    versus.PATTERN = 'lines' if football.is_foot(league) else 'rings'
    ru = versus._team(team, league)[0]
    return ru, poster.TEAMS[ru][0].replace('/', '_') if ru in poster.TEAMS else ru


def plate_path(team, side, league, color, out_dir, geom=None):
    """<slug>_<side>_<hex>.webm; с геометрией — <slug>_<side>_<имя геометрии>_<hex>.webm."""
    tag = side if geom is None else '%s_%s' % (side, geom.name)
    return os.path.join(out_dir, '%s_%s_%02x%02x%02x.webm' % ((_club(team, league)[1], tag) + _rgb(color)))


def _plate_box(rect, size=(W, H)):
    x0, y0, x1, y1 = rect
    m = PLATE_MARGIN
    return max(0, x0 - m), max(0, y0 - m), min(size[0], x1 + m), min(size[1], y1 + m)


def _plate_frame(side, tau, box):
    """Кадр плашки RGBA (прямая альфа) в box; зерно холста уже в пикселях, тень панели — чёрная с альфой."""
    px0, py0, px1, py1 = box
    sh, (fb, frgb, fa, ftex), (epos, ergb, ea, etex) = side.layers(tau)
    alpha = sh[py0:py1, px0:px1].copy()
    col = np.zeros(alpha.shape + (3,), np.float32)               # цвет × альфа (тень панели — чёрная)
    tex = np.zeros_like(alpha)                                   # зерно × покрытие панелью/эмблемой
    cov = np.zeros_like(alpha)
    for (x0, y0), rgb, a, t in ((fb[:2], frgb, fa, ftex), (epos, ergb, ea, etex)):
        h, w = a.shape
        sl = (slice(y0 - py0, y0 - py0 + h), slice(x0 - px0, x0 - px0 + w))
        col[sl] = col[sl] * (1 - a)[..., None] + rgb * a[..., None]
        tex[sl] = tex[sl] * (1 - a) + t * a
        cov[sl] = cov[sl] * (1 - a) + a
        alpha[sl] = alpha[sl] * (1 - a) + a
    # зерно — на смешанный цвет, как Banner.frame: где плашка непрозрачна, пиксели совпадают с ним точно
    rgb = _Canvas.apply(col / np.maximum(alpha, 1e-6)[..., None], tex / np.maximum(cov, 1e-6))
    return np.dstack([np.clip(rgb, 0, 255), np.clip(alpha * 255 + 0.5, 0, 255)]).astype(np.uint8)


_YUV = 'scale=%s_color_matrix=bt709:%s_range=tv:flags=accurate_rnd+full_chroma_int'
_TAGS = ['-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv']


def render_plate(team, side, league, color, out_dir, seconds=4, fps=30, crf=PLATE_CRF, grain=GRAIN, geom=None):
    """Плашка клуба team на стороне side ('home' — P1, «древко» слева; 'away' — P2, «древко» справа) цвета color
    ((r, g, b) или '#rrggbb') → out_dir/<slug>_<side>_<hex>.webm (VP9 yuva420p) + .json (начало box в координатах
    баннера, размер, fps, кадры, цвет, версия). geom — своя геометрия (Geometry, например сторис 1080×1920):
    тот же флаг и та же эмблема, другой кадр и прямоугольник панели."""
    ru, slug = _club(team, league)
    color = _rgb(color)
    n = int(round(seconds * fps))
    reps = max(1, round(seconds / 4))
    frame = (W, H) if geom is None else tuple(geom.frame)
    sd = _Side(ru, side, color, _Canvas(grain, size=frame), geom=geom)
    box = _plate_box(sd.rect, frame)
    w, h = box[2] - box[0], box[3] - box[1]
    path = plate_path(ru, side, league, color, out_dir, geom)
    os.makedirs(out_dir, exist_ok=True)
    tmp = path[:-5] + '.part.webm'
    frames = (_plate_frame(sd, (i / n * reps) % 1.0, box) for i in range(n))
    _ffmpeg(['-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', '%dx%d' % (w, h), '-r', str(fps), '-i', '-', '-an',
             '-vf', _YUV % ('out', 'out'), '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-crf', str(crf), '-b:v', '0',
             '-deadline', 'good', '-cpu-used', '2', '-row-mt', '1', '-g', str(n)] + _TAGS + [tmp], frames)
    os.replace(tmp, path)
    meta = {'version': plate_version(fps, n, geom), 'team': ru, 'slug': slug, 'side': side, 'league': league,
            'color': '#%02x%02x%02x' % color, 'origin': list(box[:2]), 'size': [w, h], 'banner': list(frame),
            'fps': fps, 'frames': n}
    if geom is not None:
        meta['geometry'] = geom.name
    with open(path[:-5] + '.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return path


def _plate_meta(path, fps, n, geom=None):
    """JSON готовой плашки, если она есть и нарисована текущей версией вида; иначе None."""
    mp = path[:-5] + '.json'
    if not (os.path.exists(path) and os.path.exists(mp)):
        return None
    with open(mp, encoding='utf-8') as f:
        meta = json.load(f)
    return meta if meta.get('version') == plate_version(fps, n, geom) else None


def get_plate(team, side, league, color, plates_dir, seconds=4, fps=30, geom=None):
    """Готовая плашка из plates_dir (нет или устарела — рисуется) → (путь, JSON)."""
    n = int(round(seconds * fps))
    path = plate_path(team, side, league, color, plates_dir, geom)
    meta = _plate_meta(path, fps, n, geom)
    if meta is None:
        render_plate(team, side, league, color, plates_dir, seconds, fps, geom=geom)
        meta = _plate_meta(path, fps, n, geom)
    return path, meta


def _read_plate(path, meta):
    """Кадры плашки RGBA uint8 по одному (декодер libvpx-vp9 — только он отдаёт альфу)."""
    w, h = meta['size']
    p = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-c:v', 'libvpx-vp9', '-i', path,
                          '-vf', _YUV % ('in', 'in'), '-f', 'rawvideo', '-pix_fmt', 'rgba', '-'], stdout=subprocess.PIPE)
    try:
        for _ in range(meta['frames']):
            buf = p.stdout.read(w * h * 4)
            if len(buf) < w * h * 4:
                raise RuntimeError('plate %s: short read' % path)
            yield np.frombuffer(buf, np.uint8).reshape(h, w, 4)
    finally:
        p.stdout.close()
        p.wait()


def _over_plate(img, fr, origin):
    x0, y0 = origin
    h, w = fr.shape[:2]
    a = fr[..., 3:4].astype(np.float32) / 255
    img[y0:y0 + h, x0:x0 + w] = img[y0:y0 + h, x0:x0 + w] * (1 - a) + fr[..., :3] * a


def _screen_bg(grain=GRAIN):
    """Фон баннера 1080² с зерном (как в compose) — подложка для превью плашек."""
    S0 = versus.S
    versus.S = SS
    try:
        bg = np.asarray(versus._background().convert('RGB').resize((W, H), Image.LANCZOS), np.float32)
    finally:
        versus.S = S0
    return np.clip(_Canvas.apply(bg, _Canvas(grain).screen), 0, 255)


def compose(home, away, path_mp4, date='', time='', odds=None, league='KHL', plates_dir='out/anim/plates', gif=False,
            tz='время московское', seconds=4, fps=30, target_mb=3.0, sheet=None, grain=GRAIN):
    """Баннер из готовых плашек: фон → плашка хозяев → плашка гостей → текст. Цвета берёт как versus (с заменой
    цвета гостей при совпадении), недостающие плашки рисует в plates_dir. → path_mp4 (+ .gif / контактный лист)."""
    (hn, hc, _, _), (an, ac, _, _), _ = versus._teams(home, away, league)
    plates = [get_plate(hn, 'home', league, hc, plates_dir, seconds, fps),
              get_plate(an, 'away', league, ac, plates_dir, seconds, fps)]
    bg, fg_rgb, fg_a, _ = _static(home, away, date, time, odds, league, tz, ('down', 'up'))
    scr = _Canvas(grain).screen
    fa = fg_a[..., None]
    # текст поверх фона — точно как у статики (зерно на смешанный цвет); здесь — вклад текста «с предумножением»:
    # кадр = под·(1 − a) + fgp, где фон без плашек даёт ровно статичный результат
    still = np.clip(_Canvas.apply(bg * (1 - fa) + fg_rgb * fa, scr), 0, 255)
    bg = np.clip(_Canvas.apply(bg, scr), 0, 255)
    fgp = still - bg * (1 - fa)
    readers = [_read_plate(p, m) for p, m in plates]
    frames = []
    for _ in range(plates[0][1]['frames']):
        img = bg.copy()
        for (p, m), rd in zip(plates, readers):          # хозяева, потом гости поверх
            _over_plate(img, next(rd), m['origin'])
        img = img * (1 - fa) + fgp
        frames.append(np.clip(img, 0, 255).astype(np.uint8))
    os.makedirs(os.path.dirname(path_mp4) or '.', exist_ok=True)
    _encode_mp4(frames, path_mp4, fps, target_mb)
    base = os.path.splitext(path_mp4)[0]
    if gif:
        _encode_gif(frames, base + '.gif' if gif is True else gif, fps)
    if sheet:
        _sheet(frames, base + '_frames.jpg' if sheet is True else sheet, fps)
    return path_mp4


def preview_plate(path, path_gif, grain=GRAIN):
    """GIF-превью одной плашки на тёмном фоне баннера (540², 15 fps)."""
    with open(path[:-5] + '.json', encoding='utf-8') as f:
        meta = json.load(f)
    bg = _screen_bg(grain)
    frames = []
    for fr in _read_plate(path, meta):
        img = bg.copy()
        _over_plate(img, fr, meta['origin'])
        frames.append(np.clip(img, 0, 255).astype(np.uint8))
    return _encode_gif(frames, path_gif, meta['fps'])


if __name__ == '__main__':
    print(render_anim('Торпедо', 'Динамо Москва', 'out/anim/vs_torpedo_dinamo.mp4', date='16 октября', time='19:00',
                      odds=(2.12, 3.76, 3.00), gif=True, sheet=True))
