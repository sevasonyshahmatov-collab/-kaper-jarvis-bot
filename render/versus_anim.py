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
Запуск из папки render.
"""
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import brand_kit
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

    def __init__(self, strength=GRAIN, seed=3):
        rng = np.random.default_rng(seed)
        low = rng.normal(0, 1, (H // 8 + 2, W // 8 + 2)).astype(np.float32)
        low = np.asarray(Image.fromarray(((low * 30) + 128).clip(0, 255).astype('uint8')).resize((W, H), Image.BICUBIC))
        self.phase = (low.astype(np.float32) - 128) / 30 * 0.9
        self.fine = rng.normal(0, 1, (H, W)).astype(np.float32)
        self.k = strength
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.screen = self.at(xx, yy)

    def at(self, x, y):
        """Значение текстуры в точках (x, y) неподвижного баннера 1080×1080."""
        ang = np.deg2rad(-30)
        u = x * np.cos(ang) + y * np.sin(ang)
        v = -x * np.sin(ang) + y * np.cos(ang)
        thread = np.sin(2 * np.pi * u / 4.6 + _bilinear(self.phase, x, y))
        cross = np.sin(2 * np.pi * v / 3.4) * 0.35
        weave = np.where(thread > 0, thread, thread * 0.6) + cross
        fine = self.fine[np.clip(np.rint(y).astype(np.int32), 0, H - 1), np.clip(np.rint(x).astype(np.int32), 0, W - 1)]
        return ((0.055 * weave + 0.045 * fine) * self.k).astype(np.float32)

    @staticmethod
    def apply(rgb, tex):
        """Та же формула, что в poster._canvas_texture."""
        lum = rgb.mean(axis=2, keepdims=True) / 255.0
        return rgb * (1 + tex[..., None] * (0.6 + 0.8 * lum)) + tex[..., None] * 10


class _Flag:
    """Панель клуба, колышущаяся как флаг. «Древко» — внешний край (хозяева слева, гости справа), волна бежит
    к середине баннера и к свободному краю нарастает. Край, упирающийся в рамку кадра, уходит за кадр."""

    def __init__(self, spec, pole, phase, canvas):
        (x0, y0, x1, y1), col, team, seed, ctr, fd = spec
        self.rect, self.pole, self.phase, self.cv = (x0, y0, x1, y1), pole, phase, canvas
        self.w, self.h = w, h = x1 - x0, y1 - y0
        self.src = np.asarray(versus._panel(w, h, col, (ctr[0] * w, ctr[1] * h), seed, fd, pad=PAD), np.float32)
        # кусок кадра, который панель может занять
        self.box = (max(0, x0 - PAD), max(0, y0 - PAD), min(W, x1 + PAD), min(H, y1 + PAD))
        bx0, by0, bx1, by1 = self.box
        yy, xx = np.mgrid[by0:by1, bx0:bx1].astype(np.float32)
        self.u, self.v = xx - x0, yy - y0
        q = self.u / w if pole == 'l' else 1 - self.u / w
        self.env = (0.4 + 0.6 * _smooth(q)).astype(np.float32)
        # края у рамки кадра не рисуем — там панель продолжается за кадр
        self.open = dict(l=x0 <= 0, t=y0 <= 0, r=x1 >= W, b=y1 >= H)

    def frame(self, tau, shadow, sh_off, sh_k):
        """→ (box, rgb, alpha, tex) куска кадра в момент tau ∈ [0, 1).
        shadow — тень эмблемы на ткани (кадр 1080², 0..1), sh_off — её сдвиг (px), sh_k — множитель силы."""
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
    тень на ткани отстаёт и чуть расходится, когда эмблема поднимается."""

    def __init__(self, team, cx, cy, size, canvas, margin=22):
        self.cv = canvas
        em1 = poster._emblem(team, size)                 # 1× — как в статичном баннере (позиция и тень)
        self.master = poster._emblem(team, size * SS)
        px, py = int(cx - em1.width / 2), int(cy - em1.height / 2)
        self.c = np.array((px + em1.width / 2, py + em1.height / 2))        # центр в покое (непрерывные координаты)
        self.tw, self.th = em1.width + 2 * margin, em1.height + 2 * margin
        self.ox, self.oy = px - margin, py - margin
        # тень — ровно как versus._paste_emblem при S = 1
        sh = Image.new('L', (W, H), 0)
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


def _drop_shadow(dst, box, alpha):
    """Тень панели как в versus._draw_panels: сдвиг (14, 20), размытие 24, непрозрачность 120."""
    x0, y0 = box[:2]
    h, w = alpha.shape
    m = np.zeros((H + 40, W + 40), np.float32)
    m[y0 + 20:y0 + 20 + h, x0 + 14:x0 + 14 + w] = alpha
    m = Image.fromarray((m[:H, :W] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(24))
    dst *= (1 - np.asarray(m, np.float32)[..., None] / 255 * (120 / 255))


class Banner:
    """Все слои один раз; frame(tau) → кадр uint8 1080×1080×3."""

    def __init__(self, home, away, date='', time='', odds=None, league='KHL', tz='время московское',
                 fade=('down', 'up'), grain=GRAIN):
        S0 = versus.S
        versus.S = SS                                     # текст — в 3× независимо от JARVIS_S
        try:
            ly = versus.layers(home, away, date, time, odds, league, tz, fade)
        finally:
            versus.S = S0
        self.bg = np.asarray(ly['bg'].convert('RGB').resize((W, H), Image.LANCZOS), np.float32)
        fg = np.asarray(ly['fg'].resize((W, H), Image.LANCZOS), np.float32)
        self.fg_rgb, self.fg_a = fg[..., :3], fg[..., 3] / 255
        self.cv = _Canvas(grain)
        self.flags, self.emblems = [], []
        for i, spec in enumerate(ly['specs']):
            (x0, y0, x1, y1), team = spec[0], spec[2]
            self.flags.append(_Flag(spec, 'l' if i == 0 else 'r', (0.0, 2.3)[i], self.cv))
            self.emblems.append(_Emblem(team, (x0 + x1) / 2, (y0 + y1) / 2 + versus.EMBLEM_DY, versus.EMBLEM, self.cv))
        self.em_phase = (0.0, 0.6 * np.pi)

    def frame(self, tau):
        img = self.bg.copy()
        tex = self.cv.screen.copy()
        for flag, em, ph in zip(self.flags, self.emblems, self.em_phase):
            pos, ergb, ea, etex, sh_off, sh_k = em.frame(tau, ph)
            box, rgb, alpha, ftex = flag.frame(tau, em.shadow, sh_off, sh_k)
            _drop_shadow(img, box, alpha)
            _over(img, tex, box, rgb, alpha, ftex)
            _over(img, tex, pos, ergb, ea, etex)
        a = self.fg_a[..., None]
        img = img * (1 - a) + self.fg_rgb * a
        tex = tex * (1 - self.fg_a) + self.cv.screen * self.fg_a
        return np.clip(_Canvas.apply(img, tex), 0, 255).astype(np.uint8)


def _ffmpeg(args, frames=None):
    p = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + args, stdin=subprocess.PIPE)
    for f in frames or ():
        p.stdin.write(f.tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError('ffmpeg failed: %s' % ' '.join(args))


def _encode_mp4(frames, path, fps, target_mb, crf=19):
    """H.264 yuv420p, весь цикл — одна GOP (ключевой только первый кадр). Сначала CRF; не влезли в target_mb —
    двухпроходный ABR под размер."""
    n = len(frames)
    src = ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(fps), '-i', '-', '-an']
    common = ['-c:v', 'libx264', '-preset', 'veryslow', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
              '-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=lanczos+accurate_rnd+full_chroma_int',
              '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
              '-g', str(n), '-keyint_min', str(n), '-sc_threshold', '0', '-x264-params', 'ipratio=1.15',
              '-movflags', '+faststart']
    _ffmpeg(src + common + ['-crf', str(crf), path], frames)
    if os.path.getsize(path) <= target_mb * 1e6:
        return path
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
    sheet = Image.new('RGB', (cols * size + (cols + 1) * gap, rows * (size + lab) + (rows + 1) * gap), (40, 40, 44))
    d = ImageDraw.Draw(sheet)
    f = brand_kit.font('Manrope[wght].ttf', 18, 700)
    for k, i in enumerate(idx):
        x = gap + (k % cols) * (size + gap)
        y = gap + (k // cols) * (size + lab + gap)
        d.text((x + 4, y + 4), 'кадр %d · t = %.2f с' % (i, i / fps), font=f, fill=(230, 230, 235))
        sheet.paste(Image.fromarray(frames[i]).resize((size, size), Image.LANCZOS), (x, y + lab))
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


if __name__ == '__main__':
    print(render_anim('Торпедо', 'Динамо Москва', 'out/anim/vs_torpedo_dinamo.mp4', date='16 октября', time='19:00',
                      odds=(2.12, 3.76, 3.00), gif=True, sheet=True))
