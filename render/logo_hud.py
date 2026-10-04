"""Логотип канала «JARVIS KAPPER» в стиле HUD — чистая переработка присланного эскиза.

Идея эскиза сохранена: стальное кольцо с надписями, бирюзовый интерфейс «Джарвиса», щиты КХЛ и НХЛ, «J» по центру,
схема-«мозг» снизу. Убрано: нечитаемый мелкий текст, лишние стрелки за кругом, шум. Всё важное — внутри круга,
который оставит Telegram.

    python3 render/logo_hud.py out_dir
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, 'fonts')
TEAL = (86, 236, 224)
TEAL_D = (30, 150, 150)
AMBER = (255, 168, 60)


def font(name, size, wght=None):
    f = ImageFont.truetype(os.path.join(FD, name), int(size))
    if wght:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


def _polar(N, cx, cy):
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    return np.sqrt(dx * dx + dy * dy), np.arctan2(dy, dx)


def _carbon(N):
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    s = N / 64
    u, v = (xx + yy) / s, (xx - yy) / s
    chk = (np.floor(u) + np.floor(v)) % 2
    shade = np.where(chk > 0, np.sin((u % 1) * math.pi), np.sin((v % 1) * math.pi))
    base = 16 + 10 * shade
    img = np.dstack([base, base + 1, base + 3]).astype(np.float32)
    return img


def _glow(base, layer, blur, times=2):
    g = layer.filter(ImageFilter.GaussianBlur(blur))
    for _ in range(times):
        base.alpha_composite(g)
    base.alpha_composite(layer)


def _arc_text(img, text, cx, cy, r, f, fill, center_deg, bottom=False, track=0.0, engrave=None):
    """Буквы по дуге; сверху — читаются по часовой, снизу — против (как на монете)."""
    ws = [f.getlength(c) + track for c in text]
    total = sum(ws) - track
    ang = total / r
    a = math.radians(center_deg) + (-ang / 2 if not bottom else ang / 2)
    for c, w in zip(text, ws):
        mid = a + (w - track) / 2 / r * (1 if not bottom else -1)
        x, y = cx + r * math.cos(mid), cy + r * math.sin(mid)
        t = Image.new('RGBA', (int(f.size * 2), int(f.size * 2)), (0, 0, 0, 0))
        dt = ImageDraw.Draw(t)
        if engrave:
            dt.text((t.width / 2, t.height / 2 + max(2, f.size // 22)), c, font=f, anchor='mm', fill=engrave)
        dt.text((t.width / 2, t.height / 2), c, font=f, anchor='mm', fill=fill)
        deg = math.degrees(mid) + (90 if not bottom else -90)
        t = t.rotate(-deg, Image.BICUBIC, expand=True)
        img.alpha_composite(t, (int(x - t.width / 2), int(y - t.height / 2)))
        a += w / r * (1 if not bottom else -1)


def _shield(path, h):
    """Щит лиги из силуэта: металл на «краске», тёмное в вырезах (буквы)."""
    src = Image.open(path).convert('RGBA')
    src = src.crop(src.getbbox())
    w = int(src.width * h / src.height)
    src = src.resize((w, h), Image.LANCZOS)
    ink = src.getchannel('A')
    # силуэт целиком: заливаем всё, что не достижимо снаружи
    pad = 4
    m = Image.new('L', (w + 2 * pad, h + 2 * pad), 0)
    m.paste(ink.point(lambda v: 255 if v > 90 else 0), (pad, pad))
    ImageDraw.floodfill(m, (0, 0), 128)
    full = m.point(lambda v: 0 if v == 128 else 255).crop((pad, pad, pad + w, pad + h)).filter(ImageFilter.MaxFilter(3))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = (xx / w * 0.55 + yy / h * 0.45)
    chrome = 150 + 95 * np.cos(t * math.pi * 2.2 - 0.6) * 0.8 + 30 * (1 - yy / h)
    met = np.dstack([chrome * 0.97, chrome, chrome * 1.04]).clip(0, 255)
    dark = np.dstack([np.full((h, w), 18), np.full((h, w), 26), np.full((h, w), 32)]).astype(np.float32)
    inkf = (np.asarray(ink, np.float32) / 255)[..., None]
    rgb = met * inkf + dark * (1 - inkf)
    out = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    out.putalpha(full)
    # тонкий блик-кант
    edge = ImageChops.subtract(full, full.filter(ImageFilter.MinFilter(5)))
    hl = Image.new('RGBA', out.size, (255, 255, 255, 0))
    hl.putalpha(edge.point(lambda v: v * 160 // 255))
    out.alpha_composite(hl)
    return out


def render(path, N=1024, title='JARVIS KAPPER', bottom='KHL  |  NHL', circuit=True):
    S = 2
    M = N * S
    cx = cy = M / 2
    r, th = _polar(M, cx, cy)
    img = np.zeros((M, M, 3), np.float32)
    img[:] = _carbon(M)
    R1, R2 = 0.475 * M, 0.375 * M                                       # кольцо: внешний и внутренний радиусы
    # стекло внутри
    inner = r < R2
    glow = np.exp(-((r / (0.30 * M)) ** 2))
    glass = np.dstack([8 + 18 * glow, 24 + 58 * glow, 32 + 60 * glow])
    img = np.where(inner[..., None], glass, img)
    # сталь кольца: шлифовка по кругу + два блика
    ring = (r >= R2) & (r <= R1)
    rng = np.random.default_rng(4)
    brush = np.interp(r, np.linspace(0, M, 4000), rng.normal(0, 1, 4000)) * 7
    shine = 128 + 70 * np.cos(2 * (th + math.pi / 4)) + 18 * np.cos(th - 1.2) + brush
    rr = (r - R2) / (R1 - R2)
    bevel = 30 * np.exp(-((rr - 0.04) / 0.05) ** 2) - 34 * np.exp(-((rr - 0.97) / 0.04) ** 2) + 26 * np.exp(-((rr - 0.92) / 0.04) ** 2)
    steel = (shine + bevel)[..., None] * np.array([0.96, 0.99, 1.04], np.float32)
    img = np.where(ring[..., None], steel, img)
    # канавка посередине кольца
    groove = ring & (np.abs(r - (R2 + (R1 - R2) * 0.18)) < M * 0.0035)
    img = np.where(groove[..., None], img * 0.55, img)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    d = ImageDraw.Draw(im)
    # тень кольца на стекле
    sh = Image.new('L', (M, M), 0)
    ImageDraw.Draw(sh).ellipse((cx - R2 - 2, cy - R2 - 2, cx + R2 + 2, cy + R2 + 2), outline=255, width=int(M * 0.02))
    shade = Image.new('RGBA', (M, M), (0, 0, 0, 0))
    shade.putalpha(sh.filter(ImageFilter.GaussianBlur(M * 0.012)).point(lambda v: v * 150 // 255))
    msk = Image.new('L', (M, M), 0)
    ImageDraw.Draw(msk).ellipse((cx - R2, cy - R2, cx + R2, cy + R2), fill=255)
    shade.putalpha(ImageChops.multiply(shade.getchannel('A'), msk))
    im.alpha_composite(shade)
    # надписи на кольце — гравировка
    rt = (R1 + R2) / 2 + M * 0.004
    fr = font('Unbounded[wght].ttf', M * 0.043, 800)
    _arc_text(im, title, cx, cy, rt, fr, (34, 38, 46, 255), -90, track=M * 0.006, engrave=(235, 240, 246, 150))
    _arc_text(im, bottom, cx, cy, rt, fr, (34, 38, 46, 255), 90, bottom=True, track=M * 0.006, engrave=(235, 240, 246, 150))
    # болты слева и справа
    for ang in (0, 180):
        bx, by = cx + rt * math.cos(math.radians(ang)), cy + rt * math.sin(math.radians(ang))
        br = M * 0.017
        d.ellipse((bx - br, by - br, bx + br, by + br), fill=(70, 76, 86, 255), outline=(200, 206, 214, 255), width=int(M * 0.003))
        d.line((bx - br * 0.6, by, bx + br * 0.6, by), fill=(30, 34, 40, 255), width=int(M * 0.004))
    # ---- HUD
    hud = Image.new('RGBA', (M, M), (0, 0, 0, 0))
    h = ImageDraw.Draw(hud)
    w1 = max(2, int(M * 0.0022))
    for rr_, a in ((0.355, 120), (0.255, 90), (0.115, 70)):
        R = rr_ * M
        h.ellipse((cx - R, cy - R, cx + R, cy + R), outline=TEAL + (a,), width=w1)
    R = 0.335 * M                                                       # шкала-циферблат
    for i in range(120):
        a = math.radians(i * 3)
        L = M * (0.018 if i % 10 == 0 else 0.008)
        al = 200 if i % 10 == 0 else 110
        h.line((cx + R * math.cos(a), cy + R * math.sin(a), cx + (R - L) * math.cos(a), cy + (R - L) * math.sin(a)), fill=TEAL + (al,), width=w1)
    R = 0.305 * M                                                       # светящиеся дуги
    box = (cx - R, cy - R, cx + R, cy + R)
    for a0, a1, col in ((-160, -112, TEAL), (-68, -20, TEAL), (112, 160, TEAL), (20, 62, AMBER)):
        h.arc(box, a0, a1, fill=col + (255,), width=int(M * 0.007))
    for a0 in (-170, 100):                                              # пунктир
        for k in range(6):
            h.arc((cx - 0.28 * M, cy - 0.28 * M, cx + 0.28 * M, cy + 0.28 * M), a0 + k * 6, a0 + k * 6 + 3, fill=TEAL + (160,), width=w1 * 2)
    # радар — мягкий сектор
    sweep = Image.new('L', (M, M), 0)
    sd = ImageDraw.Draw(sweep)
    for k in range(30):
        sd.pieslice((cx - 0.33 * M, cy - 0.33 * M, cx + 0.33 * M, cy + 0.33 * M), -62 + k, -61 + k, fill=int(4 + k * 2.4))
    sw = Image.new('RGBA', (M, M), TEAL + (0,))
    sw.putalpha(sweep.filter(ImageFilter.GaussianBlur(M * 0.004)))
    hud.alpha_composite(sw)
    if circuit:                                                          # схема снизу, сходится к чипу
        chip_y = cy + 0.215 * M
        cs = 0.028 * M
        h.rounded_rectangle((cx - cs, chip_y - cs, cx + cs, chip_y + cs), radius=cs * 0.25, outline=TEAL + (230,), width=w1 * 2, fill=(10, 40, 46, 255))
        for k in range(-3, 4):
            if k == 0:
                continue
            x0 = cx + k * cs * 0.55
            x_end = cx + k * 0.06 * M
            y_mid = chip_y - cs - 0.03 * M - abs(k) * 0.006 * M
            pts = [(x0, chip_y - cs), (x0, y_mid), (x_end, y_mid - abs(x_end - x0) * 0.6)]
            h.line(pts, fill=TEAL + (190,), width=w1 * 2, joint='curve')
            ex, ey = pts[-1]
            h.ellipse((ex - M * 0.005, ey - M * 0.005, ex + M * 0.005, ey + M * 0.005), fill=TEAL + (230,))
        for side in (-1, 1):
            for j in range(3):
                y = chip_y - cs * 0.6 + j * cs * 0.6
                x1 = cx + side * (cs + 0.05 * M + j * 0.02 * M)
                pts = [(cx + side * cs, y), (x1, y), (x1 + side * 0.03 * M, y + 0.03 * M)]
                h.line(pts, fill=TEAL + (170,), width=w1 * 2, joint='curve')
                ex, ey = pts[-1]
                h.ellipse((ex - M * 0.004, ey - M * 0.004, ex + M * 0.004, ey + M * 0.004), fill=TEAL + (220,))
    hm = Image.new('L', (M, M), 0)
    ImageDraw.Draw(hm).ellipse((cx - R2 + 4, cy - R2 + 4, cx + R2 - 4, cy + R2 - 4), fill=255)
    hud.putalpha(ImageChops.multiply(hud.getchannel('A'), hm))
    _glow(im, hud, M * 0.006)
    # ---- щиты и «J»
    sh_h = int(0.205 * M)
    for name, x in (('khl.png', cx - 0.185 * M), ('nhl.png', cx + 0.185 * M)):
        s = _shield(os.path.join(HERE, 'league', name), sh_h)
        pos = (int(x - s.width / 2), int(cy - 0.01 * M - s.height / 2))
        sh = Image.new('RGBA', (M, M), (0, 0, 0, 0))
        sm = Image.new('L', (M, M), 0)
        sm.paste(s.getchannel('A'), pos)
        sh.putalpha(sm.filter(ImageFilter.GaussianBlur(M * 0.01)).point(lambda v: v * 170 // 255))
        im.alpha_composite(sh, (0, int(M * 0.008)))
        # бирюзовая подсветка контура
        halo = Image.new('RGBA', (M, M), TEAL + (0,))
        halo.putalpha(sm.filter(ImageFilter.GaussianBlur(M * 0.012)).point(lambda v: v * 90 // 255))
        im.alpha_composite(halo)
        im.alpha_composite(s, pos)
    jl = Image.new('RGBA', (M, M), (0, 0, 0, 0))
    ImageDraw.Draw(jl).text((cx + M * 0.004, cy - 0.015 * M), 'J', font=font('Unbounded[wght].ttf', M * 0.18, 800), anchor='mm', fill=(225, 255, 252, 255))
    glow_j = Image.new('RGBA', (M, M), TEAL + (0,))
    glow_j.putalpha(jl.getchannel('A'))
    for b, t in ((M * 0.03, 2), (M * 0.01, 1)):
        g = glow_j.filter(ImageFilter.GaussianBlur(b))
        for _ in range(t):
            im.alpha_composite(g)
    im.alpha_composite(jl)
    # ---- стеклянный блик сверху
    gl = Image.new('L', (M, M), 0)
    ImageDraw.Draw(gl).ellipse((cx - R2 * 0.95, cy - R2 * 1.02, cx + R2 * 0.95, cy - R2 * 0.05), fill=26)
    gl = ImageChops.multiply(gl.filter(ImageFilter.GaussianBlur(M * 0.02)), msk)
    wl = Image.new('RGBA', (M, M), (255, 255, 255, 0))
    wl.putalpha(gl)
    im.alpha_composite(wl)
    # внешняя тень кольца на карбоне
    om = Image.new('L', (M, M), 0)
    ImageDraw.Draw(om).ellipse((cx - R1, cy - R1, cx + R1, cy + R1), outline=255, width=int(M * 0.006))
    im = im.resize((N, N), Image.LANCZOS)
    im.convert('RGB').save(path, quality=95)
    return path


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(out, exist_ok=True)
    print(render(os.path.join(out, 'avatar_hud.jpg')))
    print(render(os.path.join(out, 'avatar_hud_clean.jpg'), circuit=False))
