"""Анимированная аватарка канала (15.10.2026, просьба владельца): короткое зацикленное видео 800×800 — Telegram
ставит его аватаркой канала (ставится вручную в приложении, бот этого не умеет).

Тот же стиль, что у анимированного Versus (versus_anim): тёмный фон, ткань колышется как флаг (те же волны,
светотень складок и текстура холста), марка канала «парит» над тканью с отстающей тенью. Всё важное — в центральном
круге (Telegram режет аватарку в круг) и крупно: в списке чатов аватарка ~40 px.

  puck  — ШАЙБА: синее полотнище с кольцами, над ним шайба с золотой «J» на скрещённых клюшках; под ним JARVIS | КХЛ·НХЛ
  flag  — ФЛАГ: золотое полотнище с напечатанным JARVIS, над ним шайба на клюшках; под ним «КХЛ · НХЛ»
  ice   — ЛЁД: «лёд» с разметкой центра площадки, над ним крупная «J»; JARVIS напечатан на льду

    python3 render/avatar_anim.py out/avatar          # все три + PNG первого кадра + контактный лист
    avatar_anim.render('ice', 'out/avatar/avatar_ice.mp4')

→ MP4 H.264 yuv420p 800×800, 30 fps, 4 с (бесшовная петля: все волны — целое число циклов), без звука, ≤ 1,8 МБ.
Запуск из папки render.
"""
import os
import sys
import time as _time

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import brand_kit
import versus
import versus_anim as va
from results_ice2 import NAVY, RED

N = 800                       # сторона кадра
SS = va.SS
SECONDS, FPS = 4, 30
GOLD = brand_kit.GOLD
INK = (22, 20, 24)


# ---------------- марка канала: «наклейки» в стиле эмблем клубов (белый контур, как poster._emblem) ----------------
def _sticker(im, size):
    """Белая «наклейка» под рисунком: скруглённый контур + залитые дырки (как у эмблем клубов в poster._emblem)."""
    pad = max(10, size // 14)
    canvas = Image.new('RGBA', (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    canvas.paste(im, (pad, pad), im)
    a = canvas.getchannel('A').point(lambda v: 255 if v > 40 else 0)
    sil = a.filter(ImageFilter.GaussianBlur(max(4, size // 40))).point(lambda v: 255 if v > 18 else 0)
    rgb = Image.merge('RGB', (sil, sil, sil))
    ImageDraw.floodfill(rgb, (0, 0), (255, 0, 0), thresh=10)
    filled = ImageChops.invert(rgb.getchannel('G').point(lambda v: 255 if v < 128 else 0))
    plate = Image.new('RGBA', canvas.size, (255, 255, 255, 0))
    plate.putalpha(filled.filter(ImageFilter.GaussianBlur(1.2)))
    return Image.alpha_composite(plate, canvas)


def _puck_top(d, cx, cy, r, letter_font=None):
    """Шайба сверху: тёмный диск, золотой обод, «J» золотом."""
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(14, 16, 22, 255))
    d.ellipse((cx - r * 0.86, cy - r * 0.86, cx + r * 0.86, cy + r * 0.86), outline=GOLD + (255,),
              width=max(2, int(r * 0.07)))
    if letter_font:
        d.text((cx + r * 0.02, cy + r * 0.02), 'J', font=letter_font, fill=GOLD + (255,), anchor='mm')


STICK = (38, 46, 66)          # клюшки тёмные: белые сливаются с белой «наклейкой»


def _sticks(size, k=0.86):
    """Две скрещённые клюшки (brand_kit._stick: тёмные, намотка золотом) на прозрачном квадрате size."""
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    st = brand_kit._stick(int(size * 0.34), int(size * k), color=STICK, tape=GOLD)
    for ang, flip in ((34, False), (-34, True)):
        s = st.transpose(Image.FLIP_LEFT_RIGHT) if flip else st
        s = s.rotate(ang, Image.BICUBIC, expand=True)
        im.alpha_composite(s, (int(size / 2 - s.width / 2), int(size * 0.47 - s.height / 2)))
    return im


def art_puck(size):
    """Шайба с золотой «J» на скрещённых клюшках."""
    s = int(size * 0.9)
    im = _sticks(s)
    d = ImageDraw.Draw(im)
    r = s * 0.27
    _puck_top(d, s / 2, s * 0.52, r, brand_kit.UNB(r * 1.25))
    return _sticker(im, size)


def art_j(size):
    """Крупная «J»: тёмно-синяя с золотым контуром (как «J» марки в brand_kit), белая наклейка вокруг."""
    s = int(size * 0.9)
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    f = brand_kit.UNB(s * 0.86)
    d = ImageDraw.Draw(im)
    d.text((s / 2 + s * 0.02, s / 2), 'J', font=f, fill=NAVY + (255,), anchor='mm',
           stroke_width=max(2, int(s * 0.028)), stroke_fill=GOLD + (255,))
    bb = im.getbbox()
    im = im.crop(bb)
    return _sticker(im, size)


# ---------------- рисунок ткани (src для versus_anim._Flag) ----------------
def _print_text(img, pad, text, font_name, wght, cap_h, cx, cy, color, alpha=0.92, spacing=0.0):
    """Текст «напечатан» на ткани: рисуется в SS× и уменьшается, затем ложится на рисунок (он колышется вместе с ним)."""
    w, h = img.size
    lay = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))
    f = versus._fit(text, w * SS, cap_h * SS, wght, font_name)
    d = ImageDraw.Draw(lay)
    if spacing:
        ws = [f.getlength(c) for c in text]
        tw = sum(ws) + spacing * SS * (len(text) - 1)
        x = (cx + pad) * SS - tw / 2
        for c, cw in zip(text, ws):
            d.text((x, (cy + pad) * SS), c, font=f, fill=color + (int(255 * alpha),), anchor='lm')
            x += cw + spacing * SS
    else:
        d.text(((cx + pad) * SS, (cy + pad) * SS), text, font=f, fill=color + (int(255 * alpha),), anchor='mm')
    lay = lay.resize((w, h), Image.LANCZOS)
    out = img.convert('RGBA')
    out.alpha_composite(lay)
    return out.convert('RGB')


def src_rings(color, ctr, seed=11, fade='down'):
    return lambda w, h, pad: versus._panel(w, h, color, (ctr[0] * w, ctr[1] * h), seed, fade, pad=pad)


def src_flag_text(color, seed=23):
    """Золотое полотнище с кольцами и напечатанным JARVIS."""
    def src(w, h, pad):
        img = versus._panel(w, h, color, (0.5 * w, 0.56 * h), seed, None, pad=pad)
        return _print_text(img, pad, 'JARVIS', 'Oswald[wght].ttf', 700, h * 0.5, w / 2, h * 0.57, INK)
    return src


def src_ice(seed=5):
    """«Лёд»: светлый голубоватый, иней, следы коньков, разметка центра площадки; внизу напечатан JARVIS."""
    def src(w, h, pad):
        W2, H2 = w + 2 * pad, h + 2 * pad
        yy, xx = np.mgrid[-pad:h + pad, -pad:w + pad].astype(np.float32)
        top, bot = np.array((236, 244, 252), np.float32), np.array((196, 216, 236), np.float32)
        t = np.clip((yy / h) * 0.8 + (xx / w) * 0.2, 0, 1)[..., None]
        a = top * (1 - t) + bot * t
        a *= (1 + 0.05 * np.exp(-((xx - 0.3 * w) ** 2 + (yy - 0.2 * h) ** 2) / (2 * (0.35 * w) ** 2)))[..., None]
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        S = SS
        lay = Image.new('RGBA', (W2 * S, H2 * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        rng = np.random.default_rng(seed)
        for _ in range(70):                                  # следы коньков — тонкие светлые и сероватые дуги
            x0, y0 = rng.uniform(0, W2), rng.uniform(0, H2)
            ln, ang = rng.uniform(60, 260), rng.uniform(-0.5, 0.5) + (0 if rng.random() < 0.6 else 1.4)
            col = (255, 255, 255, int(rng.uniform(60, 140))) if rng.random() < 0.6 else (150, 170, 190, 50)
            d.line(((x0 * S, y0 * S), ((x0 + ln * np.cos(ang)) * S, (y0 + ln * np.sin(ang)) * S)), fill=col,
                   width=max(1, int(rng.uniform(1, 2.5) * S)))
        cx, cy = (0.5 * w + pad) * S, (0.47 * h + pad) * S
        lw = int(0.018 * w * S)
        d.rectangle((0, cy - lw * 1.6, W2 * S, cy + lw * 1.6), fill=RED + (150,))                 # красная линия
        r = 0.40 * w * S
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(40, 90, 200, 170), width=lw)          # круг вбрасывания
        lay = lay.filter(ImageFilter.GaussianBlur(0.6 * S)).resize((W2, H2), Image.LANCZOS)
        img.alpha_composite(lay)
        img = img.convert('RGB')
        return _print_text(img, pad, 'JARVIS', 'Oswald[wght].ttf', 700, h * 0.075, w / 2, h * 0.905, NAVY,
                           alpha=0.9, spacing=0.03 * w)
    return src


# ---------------- сцены ----------------
def _bg(glow_c=(400, 380), glow_r=300, k=0.14):
    """Тёмный фон как у баннера (versus.BG) с мягким подсветом за полотнищем."""
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    g = 1 + k * np.exp(-((xx - glow_c[0]) ** 2 + (yy - glow_c[1]) ** 2) / (2 * glow_r ** 2))
    return np.array(versus.BG, np.float32)[None, None] * g[..., None]


def _mark(d, cx, yb, size, tag='КХЛ · НХЛ', S=SS):
    """Марка канала как в versus: JARVIS | тег (Oswald 700, белый, светлая черта, тег золотом); yb — базовая линия."""
    fm = brand_kit.font('Oswald[wght].ttf', size * S, 700)
    wj, wt = fm.getlength('JARVIS'), fm.getlength(tag)
    gx, bar = size * 0.55 * S, max(2, size * 0.12) * S
    xr = cx * S + (wj + gx * 2 + bar + wt) / 2
    y = yb * S
    d.text((xr, y), tag, font=fm, fill=GOLD + (255,), anchor='rs')
    d.rectangle((xr - wt - gx - bar, y - size * 0.92 * S, xr - wt - gx, y), fill=(220, 220, 225, 255))
    d.text((xr - wt - 2 * gx - bar, y), 'JARVIS', font=fm, fill=(245, 245, 245, 255), anchor='rs')


def _fg(draw):
    img = Image.new('RGBA', (N * SS, N * SS), (0, 0, 0, 0))
    draw(ImageDraw.Draw(img), img)
    fg = np.asarray(img.resize((N, N), Image.LANCZOS), np.float32)
    return fg[..., :3], fg[..., 3] / 255


def _scene(variant):
    """→ (bg, [стороны], fg_rgb, fg_a)."""
    cv = va._Canvas(va.GRAIN, size=(N, N))
    if variant == 'puck':
        g = va.side_geometry('avatar_puck', 'home', (N, N), (178, 92, 622, 592), 372, (400, 342), fade='down')
        g = g._replace(ctr=(0.5, 0.5))
        side = va._Side(None, 'home', (34, 70, 170), cv, geom=g, art=art_puck, src=src_rings((34, 70, 170), g.ctr))
        fg = _fg(lambda d, im: _mark(d, 400, 690, 50))
        bg = _bg((400, 360), 290)
    elif variant == 'flag':
        g = va.side_geometry('avatar_flag', 'home', (N, N), (62, 300, 738, 600), 250, (400, 246), fade=None)
        side = va._Side(None, 'home', (232, 168, 44), cv, geom=g, art=art_puck, src=src_flag_text((232, 168, 44)))

        def draw(d, im):
            f = brand_kit.font('Manrope[wght].ttf', 34 * SS, 800)
            text = 'КХЛ · НХЛ'
            ws = [f.getlength(c) for c in text]
            sp = 8 * SS
            x = 400 * SS - (sum(ws) + sp * (len(text) - 1)) / 2
            for c, w in zip(text, ws):
                d.text((x, 672 * SS), c, font=f, fill=(235, 233, 240, 255), anchor='ls')
                x += w + sp
        fg = _fg(draw)
        bg = _bg((400, 440), 320)
    elif variant == 'ice':
        g = va.side_geometry('avatar_ice', 'home', (N, N), (150, 138, 650, 662), 360, (400, 378), fade='down')
        side = va._Side(None, 'home', (220, 232, 245), cv, geom=g, art=art_j, src=src_ice())
        fg = (np.zeros((N, N, 3), np.float32), np.zeros((N, N), np.float32))
        bg = _bg((400, 400), 320, 0.18)
    else:
        raise ValueError(variant)
    return bg, cv, [side], fg[0], fg[1]


VARIANTS = ('puck', 'flag', 'ice')


def render(variant, path_mp4, target_mb=1.7, png=True):
    """Аватарка variant → path_mp4 (+ PNG первого кадра рядом). → dict(path, seconds, mb, render_s, frames)."""
    t0 = _time.time()
    bg, cv, sides, fg_rgb, fg_a = _scene(variant)
    n = SECONDS * FPS
    frames = [va.scene_frame(bg, cv, sides, fg_rgb, fg_a, i / n) for i in range(n)]
    os.makedirs(os.path.dirname(path_mp4) or '.', exist_ok=True)
    va._encode_mp4(frames, path_mp4, FPS, target_mb)
    if png:
        Image.fromarray(frames[0]).save(os.path.splitext(path_mp4)[0] + '.png', optimize=True)
    return {'path': path_mp4, 'seconds': n / FPS, 'mb': os.path.getsize(path_mp4) / 1e6,
            'render_s': round(_time.time() - t0, 1), 'frames': frames}


def _circle(im, size, bg):
    """Аватарка как в Telegram: круг size px на подложке bg (уменьшение LANCZOS, сглаженный край)."""
    big = im.resize((size * 4, size * 4), Image.LANCZOS)
    m = Image.new('L', big.size, 0)
    ImageDraw.Draw(m).ellipse((0, 0, big.width - 1, big.height - 1), fill=255)
    out = Image.new('RGB', big.size, bg)
    out.paste(big, (0, 0), m)
    return out.resize((size, size), Image.LANCZOS)


def contact_sheet(stills, path, names=None):
    """Лист: каждая аватарка 800 px (квадрат с кругом обрезки) и в круге 64 px и 40 px на тёмной и светлой
    подложке (как в списке чатов), плюс 64 px, увеличенные ×4 «по пикселям»."""
    names = names or [''] * len(stills)
    col_w, gap = 800, 30
    H = 40 + 800 + 30 + 300
    sheet = Image.new('RGB', (len(stills) * (col_w + gap) + gap, H), (40, 40, 44))
    d = ImageDraw.Draw(sheet)
    f = brand_kit.font('Manrope[wght].ttf', 22, 700)
    fs = brand_kit.font('Manrope[wght].ttf', 16, 600)
    for k, (im, name) in enumerate(zip(stills, names)):
        x = gap + k * (col_w + gap)
        d.text((x, 10), name, font=f, fill=(235, 235, 240))
        sheet.paste(im, (x, 40))
        ov = Image.new('RGBA', (800, 800), (0, 0, 0, 0))
        ImageDraw.Draw(ov).ellipse((0, 0, 799, 799), outline=(255, 0, 255, 160), width=2)
        sheet.paste(ov, (x, 40), ov)
        y = 40 + 800 + 30
        # тёмная и светлая подложки, как в Telegram
        for j, (bgc, lab) in enumerate((((24, 26, 32), 'тёмная тема'), ((255, 255, 255), 'светлая тема'))):
            bx = x + j * 200
            d.rectangle((bx, y, bx + 180, y + 150), fill=bgc)
            sheet.paste(_circle(im, 64, bgc), (bx + 12, y + 12))
            sheet.paste(_circle(im, 40, bgc), (bx + 100, y + 24))
            d.text((bx + 12, y + 92), '64 px', font=fs, fill=(150, 150, 160))
            d.text((bx + 100, y + 92), '40 px', font=fs, fill=(150, 150, 160))
            d.text((bx, y + 160), lab, font=fs, fill=(200, 200, 205))
        z = _circle(im, 64, (24, 26, 32)).resize((256, 256), Image.NEAREST)
        sheet.paste(z, (x + 420, y))
        d.text((x + 420, y + 262), '64 px ×4', font=fs, fill=(200, 200, 205))
    sheet.save(path, quality=92)
    return path


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/avatar'
    stills, names = [], []
    for v in VARIANTS:
        r = render(v, os.path.join(out, 'avatar_%s.mp4' % v))
        stills.append(Image.fromarray(r['frames'][0]))
        names.append('%s · %.1f с · %.2f МБ' % (v, r['seconds'], r['mb']))
        print(v, r['path'], '%.2f MB' % r['mb'], '%.1f s render' % r['render_s'])
    print(contact_sheet(stills, os.path.join(out, 'avatar_sheet.jpg'), names))
