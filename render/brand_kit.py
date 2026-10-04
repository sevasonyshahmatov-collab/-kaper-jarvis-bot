"""Фирменный стиль канала: аватарка и заставка (обложка закреплённого поста «О канале»).

Стиль тот же, что у постеров: светлый лёд с инеем, тёмно-синий, золото, Unbounded/Oswald/Manrope.

    python3 render/brand_kit.py out/        # все варианты + лист предпросмотра

Аватарка 1024×1024 — Telegram обрежет в круг, всё важное в центральном круге.
  ice    — ЛЁД: тёмная шайба-медаль на льду, золотая светящаяся «J», надпись JARVIS по дуге
  puck   — ШАЙБА: шайба в наклоне, на ней «J», за ней снежный след
  sticks — КЛЮШКИ: тёмный фон, скрещённые клюшки и золотая «J» (лучше всех видна в списке чатов)
Заставка 1280×720 (16:9, как картинка к посту):
  ice    — светлая: JARVIS крупно, «КХЛ · НХЛ», три правила канала
  dark   — тёмная версия той же заставки
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import results_styles as rs
from results_ice2 import _frost_top, NAVY, RED

FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
GOLD = (255, 194, 61)
GOLD_L = (255, 228, 150)
ICE_T, ICE_B = (236, 244, 251), (205, 224, 240)
DEEP = (10, 16, 30)


def font(name, size, wght=None):
    f = ImageFont.truetype(os.path.join(FD, name), int(size))
    if wght:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


UNB = lambda s: font('Unbounded[wght].ttf', s, 800)
OSW = lambda s: font('Oswald[wght].ttf', s, 700)
MAN = lambda s: font('Manrope[wght].ttf', s, 800)


def _ice(w, h, frost=260, lines=True):
    bg = rs._gradient(w, h, ICE_T, ICE_B, glow=(255, 255, 255, 120), glow_xy=(0.3, 0.15), glow_r=0.7)
    if lines:
        lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.line(((0, h * 0.5), (w, h * 0.5)), fill=RED + (55,), width=max(6, h // 90))
        for y in (h * 0.24, h * 0.76):
            d.line(((0, y), (w, y)), fill=(40, 90, 200, 45), width=max(6, h // 90))
        bg = Image.alpha_composite(bg.convert('RGBA'), lay)
    return _frost_top(bg.convert('RGBA'), reach=frost)


def _glow_text(img, xy, text, f, color=GOLD_L, glow=GOLD, blur=26, strength=2):
    g = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).text(xy, text, font=f, anchor='mm', fill=glow + (255,))
    g = g.filter(ImageFilter.GaussianBlur(blur))
    for _ in range(strength):
        img.alpha_composite(g)
    ImageDraw.Draw(img).text(xy, text, font=f, anchor='mm', fill=color + (255,))


def _shadow(img, shape_mask, off=(0, 18), blur=28, alpha=110):
    sh = Image.new('RGBA', img.size, (20, 40, 80, 0))
    a = shape_mask.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: v * alpha // 255)
    sh.putalpha(a)
    img.alpha_composite(sh, off)


def _arc_text(img, text, cx, cy, r, f, color, start_deg=-90, spread=None, bottom=False):
    """Текст по дуге (по верху круга или по низу)."""
    widths = [f.getlength(c) for c in text]
    total = sum(widths) + 0.0
    ang_total = total / r
    a = (start_deg * math.pi / 180) - (ang_total / 2 if not bottom else -ang_total / 2)
    for c, cw in zip(text, widths):
        mid = a + (cw / 2 / r) * (1 if not bottom else -1)
        x, y = cx + r * math.cos(mid), cy + r * math.sin(mid)
        tile = Image.new('RGBA', (int(cw * 3 + 20), int(f.size * 2)), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text((tile.width / 2, tile.height / 2), c, font=f, anchor='mm', fill=color + (255,))
        rot = -(mid * 180 / math.pi + 90) if not bottom else -(mid * 180 / math.pi - 90)
        tile = tile.rotate(rot, Image.BICUBIC, expand=True)
        img.alpha_composite(tile, (int(x - tile.width / 2), int(y - tile.height / 2)))
        a += (cw / r) * (1 if not bottom else -1)


# ------------------------------------------------------------------ аватарка
def avatar_ice(path, N=1024):
    img = _ice(N, N, frost=300)
    cx = cy = N / 2
    R = N * 0.36
    m = Image.new('L', (N, N), 0)
    ImageDraw.Draw(m).ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
    _shadow(img, m)
    disc = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    yy = np.linspace(0, 1, N, dtype=np.float32)[:, None, None]
    a = np.zeros((N, N, 4), np.float32)
    a[..., :3] = np.array(NAVY, np.float32) * (1.25 - 0.55 * yy)
    a[..., 3] = np.asarray(m, np.float32)
    disc = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    img.alpha_composite(disc)
    d = ImageDraw.Draw(img)
    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(255, 255, 255, 255), width=int(N * 0.012))
    d.ellipse((cx - R * 0.88, cy - R * 0.88, cx + R * 0.88, cy + R * 0.88), outline=GOLD + (200,), width=int(N * 0.006))
    _glow_text(img, (cx + N * 0.005, cy - N * 0.025), 'J', UNB(N * 0.40), blur=int(N * 0.03))
    _arc_text(img, 'JARVIS', cx, cy, R * 0.72, UNB(N * 0.055), (255, 255, 255), start_deg=90, bottom=True)
    img.convert('RGB').save(path, quality=95)
    return path


def _puck_img(w, top_text=None, f=None):
    h = int(w * 0.42)
    th = int(w * 0.16)
    im = Image.new('RGBA', (w, h + th + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, h / 2, w, h / 2 + th), fill=(6, 8, 12, 255))
    d.ellipse((0, th, w, h + th), fill=(6, 8, 12, 255))
    # рифление на ребре
    for i in range(1, 60):
        x = w * i / 60
        if abs(x - w / 2) < w * 0.49:
            d.line((x, h / 2 + th * 0.2 + (1 - ((x - w / 2) / (w / 2)) ** 2) ** .5 * h / 2 * 0.95,
                    x, h / 2 + th * 0.8 + (1 - ((x - w / 2) / (w / 2)) ** 2) ** .5 * h / 2 * 0.95), fill=(26, 30, 38, 255), width=max(2, w // 220))
    d.ellipse((0, 0, w, h), fill=(28, 32, 42, 255))
    d.ellipse((w * 0.06, h * 0.08, w * 0.94, h * 0.92), outline=(60, 66, 80, 255), width=max(3, w // 160))
    hl = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse((w * 0.12, h * 0.08, w * 0.6, h * 0.42), fill=(255, 255, 255, 30))
    im.alpha_composite(hl.filter(ImageFilter.GaussianBlur(w // 40)))
    return im, h


def avatar_puck(path, N=1024):
    img = _ice(N, N, frost=280)
    pw = int(N * 0.74)
    puck, ph = _puck_img(pw)
    px, py = int((N - pw) / 2), int(N * 0.40)
    # снежный след
    spray = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    rng = np.random.default_rng(3)
    d = ImageDraw.Draw(spray)
    for _ in range(420):
        t = rng.random()
        x = px + pw * 0.15 - t * N * 0.25 + rng.normal(0, 18)
        y = py + ph * 0.9 + rng.normal(0, 40 * (0.4 + t))
        r = rng.uniform(2, 9) * (1 - t * 0.6)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(200 * (1 - t))))
    img.alpha_composite(spray.filter(ImageFilter.GaussianBlur(1.2)))
    m = Image.new('L', (N, N), 0)
    m.paste(puck.getchannel('A'), (px, py))
    _shadow(img, m, off=(0, 26), blur=30, alpha=140)
    img.alpha_composite(puck, (px, py))
    # «J» на верхней грани — сплющена под наклон
    jt = Image.new('RGBA', (pw, pw), (0, 0, 0, 0))
    _glow_text(jt, (pw / 2, pw / 2), 'J', UNB(pw * 0.62), blur=int(pw * 0.03))
    jt = jt.resize((pw, int(pw * 0.48)), Image.LANCZOS)
    img.alpha_composite(jt, (px, int(py + ph / 2 - jt.height / 2)))
    d = ImageDraw.Draw(img)
    f = UNB(N * 0.085)
    sp = N * 0.012
    word = 'JARVIS'
    tw = sum(f.getlength(c) for c in word) + sp * (len(word) - 1)
    x = N / 2 - tw / 2
    for c in word:
        d.text((x, N * 0.27), c, font=f, anchor='lm', fill=NAVY + (255,))
        x += f.getlength(c) + sp
    img.convert('RGB').save(path, quality=95)
    return path


def _stick(w, h, color=(240, 244, 250), tape=(30, 34, 44)):
    """Клюшка вертикально: древко, внизу узкий крюк вправо с загнутым носком; намотка на рукоятке и крюке."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    sw = w * 0.15
    x0 = w * 0.22
    d.rounded_rectangle((x0, 0, x0 + sw, h * 0.92), radius=sw / 3, fill=color + (255,))
    bt = h * 0.06                                                          # толщина крюка
    d.polygon(((x0, h * 0.90), (x0 + sw, h * 0.92), (w * 0.90, h - bt), (w, h - bt * 1.3), (w * 0.98, h - 2),
               (x0 + sw * 0.3, h - 2), (x0, h * 0.97)), fill=color + (255,))
    d.rounded_rectangle((x0 - sw * 0.08, 0, x0 + sw * 1.08, h * 0.10), radius=sw / 2.5, fill=tape + (255,))
    for k in range(4):                                                     # намотка на крюке — тонкие витки
        xx = x0 + sw * (2.0 + k * 0.55)
        d.line((xx, h - bt * 0.9, xx - sw * 0.25, h - 3), fill=tape + (255,), width=max(3, int(sw * 0.22)))
    return im


def avatar_sticks(path, N=1024):
    a = np.zeros((N, N, 3), np.float32)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
    r = np.sqrt((xx - 0.5) ** 2 + (yy - 0.45) ** 2)
    base = np.array(NAVY, np.float32)
    a[:] = base[None, None] * (1.35 - 1.1 * r[..., None]) + np.array(DEEP, np.float32) * (r[..., None] * 0.8)
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    # тонкие линии катка
    lay = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse((N * 0.17, N * 0.17, N * 0.83, N * 0.83), outline=(90, 140, 230, 70), width=int(N * 0.008))
    d.line(((0, N / 2), (N, N / 2)), fill=RED + (70,), width=int(N * 0.01))
    img.alpha_composite(lay)
    st = _stick(int(N * 0.26), int(N * 0.64))
    for ang, dx in ((32, -0.13), (-32, 0.13)):
        s = st if dx < 0 else st.transpose(Image.FLIP_LEFT_RIGHT)
        s = s.rotate(ang if dx < 0 else ang, Image.BICUBIC, expand=True)
        m = Image.new('L', (N, N), 0)
        pos = (int(N / 2 - s.width / 2), int(N * 0.44 - s.height / 2))
        m.paste(s.getchannel('A'), pos)
        _shadow(img, m, off=(0, 14), blur=18, alpha=150)
        img.alpha_composite(s, pos)
    rr = N * 0.20
    d = ImageDraw.Draw(img)
    m = Image.new('L', (N, N), 0)
    ImageDraw.Draw(m).ellipse((N / 2 - rr, N * 0.45 - rr, N / 2 + rr, N * 0.45 + rr), fill=255)
    _shadow(img, m, off=(0, 10), blur=20, alpha=160)
    d.ellipse((N / 2 - rr, N * 0.45 - rr, N / 2 + rr, N * 0.45 + rr), fill=DEEP + (255,), outline=GOLD + (255,), width=int(N * 0.01))
    _glow_text(img, (N / 2 + N * 0.004, N * 0.43), 'J', UNB(N * 0.25), blur=int(N * 0.025))
    d = ImageDraw.Draw(img)
    f = UNB(N * 0.075)
    sp = N * 0.012
    word = 'JARVIS'
    tw = sum(f.getlength(c) for c in word) + sp * (len(word) - 1)
    x = N / 2 - tw / 2
    for c in word:
        d.text((x, N * 0.83), c, font=f, anchor='lm', fill=(255, 255, 255, 255))
        x += f.getlength(c) + sp
    img.convert('RGB').save(path, quality=95)
    return path


AVATARS = {'ice': avatar_ice, 'puck': avatar_puck, 'sticks': avatar_sticks}


# ------------------------------------------------------------------ заставка
RULES = ('ПРОГНОЗ — ДО МАТЧА', 'НИЧЕГО НЕ УДАЛЯЕМ', 'СЧИТАЕМ И ПЛЮСЫ, И МИНУСЫ')


def _spaced(d, xy, text, f, fill, sp, anchor='mm'):
    tw = sum(f.getlength(c) for c in text) + sp * (len(text) - 1)
    x = xy[0] - tw / 2 if anchor == 'mm' else xy[0]
    for c in text:
        d.text((x, xy[1]), c, font=f, anchor='lm', fill=fill)
        x += f.getlength(c) + sp
    return tw


def cover(path, style='ice', W=1280, H=720, avatar=None):
    dark = style == 'dark'
    if dark:
        a = np.zeros((H, W, 3), np.float32)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W * 0.5) / W) ** 2 + ((yy - H * 0.35) / H) ** 2)
        a[:] = np.array(NAVY, np.float32) * (1.3 - 1.2 * r[..., None]) + np.array(DEEP, np.float32) * r[..., None]
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.line(((W / 2, 0), (W / 2, H)), fill=RED + (60,), width=8)
        for x in (W * 0.26, W * 0.74):
            d.line(((x, 0), (x, H)), fill=(90, 140, 230, 50), width=8)
        d.ellipse((W / 2 - 150, H / 2 - 150, W / 2 + 150, H / 2 + 150), outline=(90, 140, 230, 50), width=6)
        img.alpha_composite(lay)
    else:
        img = _ice(W, H, frost=200, lines=False)
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.line(((W / 2, 0), (W / 2, H)), fill=RED + (50,), width=8)
        for x in (W * 0.26, W * 0.74):
            d.line(((x, 0), (x, H)), fill=(40, 90, 200, 40), width=8)
        d.ellipse((W / 2 - 150, H / 2 - 150, W / 2 + 150, H / 2 + 150), outline=(40, 90, 200, 40), width=6)
        img.alpha_composite(lay)
    ink = (255, 255, 255) if dark else NAVY
    sub = (170, 182, 204) if dark else (40, 58, 92)
    d = ImageDraw.Draw(img)
    # знак слева от названия
    if avatar:
        av = Image.open(avatar).convert('RGBA').resize((210, 210), Image.LANCZOS)
        m = Image.new('L', av.size, 0)
        ImageDraw.Draw(m).ellipse((0, 0, 209, 209), fill=255)
        av.putalpha(m)
        sm = Image.new('L', (W, H), 0)
        sm.paste(m, (120, 150))
        _shadow(img, sm, off=(0, 12), blur=18, alpha=120)
        img.alpha_composite(av, (120, 150))
        ImageDraw.Draw(img).ellipse((120, 150, 330, 360), outline=(255, 255, 255, 230), width=5)
        tx = 380
    else:
        tx = None
    d = ImageDraw.Draw(img)
    f = UNB(122)
    if tx:
        _spaced(d, (tx, 228), 'JARVIS', f, ink + (255,), 10, anchor='lm')
        _spaced(d, (tx + 4, 318), 'ХОККЕЙ · КХЛ · НХЛ', MAN(30), (GOLD if dark else (176, 120, 10)) + (255,), 6, anchor='lm')
    else:
        _spaced(d, (W / 2, 220), 'JARVIS', f, ink + (255,), 10)
        _spaced(d, (W / 2, 312), 'ХОККЕЙ · КХЛ · НХЛ', MAN(30), (GOLD if dark else (176, 120, 10)) + (255,), 6)
    d.text((W / 2, 410), 'Разбираем матчи и пишем, куда склоняемся и почему', font=MAN(30), anchor='mm', fill=sub + (255,))
    # три правила плашками (на отдельном слое — полупрозрачные плашки смешиваются с фоном)
    fr = OSW(25)
    pads, gap = 22, 14
    ws = [fr.getlength(t) + pads * 2 + 36 for t in RULES]
    total = sum(ws) + gap * (len(ws) - 1)
    x = W / 2 - total / 2
    y0, y1 = 482, 540
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for t, w in zip(RULES, ws):
        fill = (255, 255, 255, 26) if dark else (255, 255, 255, 235)
        dl.rounded_rectangle((x, y0, x + w, y1), radius=29, fill=fill, outline=((255, 255, 255, 80) if dark else (200, 212, 232, 255)), width=2)
        cx0 = x + pads + 10
        cy0 = (y0 + y1) / 2
        dl.ellipse((cx0 - 11, cy0 - 11, cx0 + 11, cy0 + 11), fill=GOLD + (255,))
        dl.line(((cx0 - 5, cy0), (cx0 - 1, cy0 + 4), (cx0 + 6, cy0 - 4)), fill=DEEP + (255,), width=3)
        dl.text((cx0 + 22, cy0), t, font=fr, anchor='lm', fill=ink + (255,))
        x += w + gap
    img.alpha_composite(lay)
    d = ImageDraw.Draw(img)
    _spaced(d, (W / 2, 640), '@jarvibet', UNB(30), RED + (255,), 3)
    d.text((W / 2, 684), 'БЕСПЛАТНО · БЕЗ «ВЕРНЯКОВ» И ПЛАТНЫХ VIP · 18+', font=MAN(18), anchor='mm', fill=sub + (200,))
    img.convert('RGB').save(path, quality=95)
    return path


# ------------------------------------------------------------------ предпросмотр
def preview(avatars, path):
    """Как аватарки смотрятся в Telegram: крупно в профиле, в списке чатов (светлая и тёмная тема), у поста."""
    cols = len(avatars)
    cw, H = 380, 820
    sheet = Image.new('RGB', (cw * cols + 40, H), (236, 242, 250))
    d = ImageDraw.Draw(sheet)
    for i, (name, p) in enumerate(avatars):
        av = Image.open(p).convert('RGBA')
        x0 = 20 + i * cw
        cx = x0 + cw / 2

        def circ(size):
            a = av.resize((size, size), Image.LANCZOS)
            m = Image.new('L', (size, size), 0)
            ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
            a.putalpha(m)
            return a
        big = circ(300)
        sheet.paste(big, (int(cx - 150), 30), big)
        d.text((cx, 360), name, font=OSW(30), anchor='mm', fill=NAVY)
        for j, (bgc, txt, sub) in enumerate((((255, 255, 255), (16, 22, 34), (130, 138, 150)), ((24, 33, 45), (240, 244, 250), (130, 150, 170)))):
            y = 410 + j * 110
            d.rounded_rectangle((x0 + 10, y, x0 + cw - 10, y + 92), radius=14, fill=bgc)
            s = circ(58)
            sheet.paste(s, (x0 + 26, y + 17), s)
            d.text((x0 + 98, y + 32), 'JARVIS', font=MAN(22), anchor='lm', fill=txt)
            d.text((x0 + 98, y + 62), 'Итоги дня: КХЛ, 6 матчей', font=MAN(16), anchor='lm', fill=sub)
        y = 650
        d.rounded_rectangle((x0 + 10, y, x0 + cw - 10, y + 120), radius=14, fill=(255, 255, 255))
        s = circ(34)
        sheet.paste(s, (x0 + 24, y + 14), s)
        d.text((x0 + 70, y + 31), 'JARVIS', font=MAN(18), anchor='lm', fill=(30, 110, 200))
        d.text((x0 + 24, y + 72), 'МАТЧИ ДНЯ · суббота, 3 октября', font=MAN(16), anchor='lm', fill=(16, 22, 34))
    sheet.save(path, quality=92)
    return path


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(out, exist_ok=True)
    av = [(k, fn(os.path.join(out, 'avatar_%s.jpg' % k))) for k, fn in AVATARS.items()]
    preview(av, os.path.join(out, 'avatar_preview.jpg'))
    cover(os.path.join(out, 'cover_ice.jpg'), 'ice', avatar=av[0][1])
    cover(os.path.join(out, 'cover_dark.jpg'), 'dark', avatar=av[2][1])
    print('\n'.join(sorted(os.listdir(out))))
