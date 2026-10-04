"""Аватарка футбольного канала — та же семья, что у хоккейного (brand_kit): золотая светящаяся «J», Unbounded.

    python3 render/brand_football.py out/football     # все варианты + лист предпросмотра

Аватарка 1024×1024 — Telegram обрежет в круг, всё важное в центральном круге.
  pitch  — ПОЛЕ: газон с полосами покоса и разметкой, в центральном круге тёмная медаль с «J», JARVIS по дуге
  jball  — J И МЯЧ: тёмный фон, крупная золотая «J», мяч лежит в её крючке
  badge  — МЯЧ-ЭМБЛЕМА: большой мяч на газоне, в центре тёмный круг с золотой «J»
Мяч рисуется сам (усечённый икосаэдр: 12 чёрных пятиугольников, 20 белых шестиугольников) — без чужих картинок и без символики АПЛ.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from brand_kit import GOLD, DEEP, UNB, _arc_text, _glow_text, _shadow, preview
from results_ice2 import NAVY

GRASS_A, GRASS_B = (38, 122, 58), (48, 140, 68)
GRASS_DARK = (10, 44, 26)
LINE = (255, 255, 255)


# ------------------------------------------------------------------ мяч
def _ball_centers():
    phi = (1 + 5 ** 0.5) / 2
    v = []
    for a in (-1, 1):
        for b in (-phi, phi):
            v += [(0, a, b), (a, b, 0), (b, 0, a)]
    v = np.array(v, np.float64)
    v /= np.linalg.norm(v, axis=1)[:, None]
    faces = []                                       # грани икосаэдра — тройки соседних вершин
    d = v @ v.T
    near = d > 0.4
    for i in range(12):
        for j in range(i + 1, 12):
            for k in range(j + 1, 12):
                if near[i, j] and near[j, k] and near[i, k]:
                    c = v[i] + v[j] + v[k]
                    faces.append(c / np.linalg.norm(c))
    return np.vstack([v, np.array(faces)])          # 12 пятиугольников + 20 шестиугольников


def _rot(ax, ay, az):
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz @ ry @ rx


def ball(D, rot=(0.35, -0.5, 0.2), ss=3):
    """Мяч D×D (RGBA): швы — границы ячеек Вороного 32 центров граней на сфере, свет сверху слева."""
    n = D * ss
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx + 0.5) / n * 2 - 1
    y = 1 - (yy + 0.5) / n * 2
    r2 = x * x + y * y
    inside = r2 <= 1
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    nrm = np.stack([x, y, z], -1)
    C = _ball_centers() @ _rot(*rot).T
    dots = nrm.reshape(-1, 3) @ C.T.astype(np.float32)
    top2 = np.sort(dots, axis=1)[:, -2:]
    first = np.argmax(dots, axis=1)
    a1 = np.arccos(np.clip(top2[:, 1], -1, 1))
    a2 = np.arccos(np.clip(top2[:, 0], -1, 1))
    seam = (a2 - a1) < 0.022
    col = np.where((first < 12)[:, None], np.array([22, 24, 30], np.float32), np.array([246, 247, 250], np.float32))
    col = np.where(seam[:, None], np.array([70, 74, 84], np.float32), col).reshape(n, n, 3)
    L = np.array([-0.45, 0.55, 0.70], np.float32)
    L /= np.linalg.norm(L)
    lam = np.clip((nrm @ L), 0, 1)
    H = L + np.array([0, 0, 1], np.float32)
    H /= np.linalg.norm(H)
    spec = np.clip(nrm @ H, 0, 1) ** 60
    shade = 0.30 + 0.80 * lam
    rim = 0.55 + 0.45 * z ** 0.35
    rgb = col * (shade * rim)[..., None] + 255 * 0.55 * spec[..., None]
    a = np.where(inside, 255, 0).astype(np.float32)
    img = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a]).astype(np.uint8), 'RGBA')
    return img.resize((D, D), Image.LANCZOS)


def _put_ball(img, D, cx, cy, rot=(0.35, -0.5, 0.2), shadow=(0, 0.04)):
    b = ball(D, rot)
    m = Image.new('L', img.size, 0)
    m.paste(b.getchannel('A'), (int(cx - D / 2), int(cy - D / 2)))
    _shadow(img, m, off=(int(D * shadow[0]), int(D * shadow[1])), blur=max(8, D // 18), alpha=150)
    img.alpha_composite(b, (int(cx - D / 2), int(cy - D / 2)))


# ------------------------------------------------------------------ фоны
def _grass(N, stripes=9, angle=0.0, vignette=0.55):
    """Газон с полосами покоса (светлая/тёмная полоса), лёгкая зернистость и затемнение к краям."""
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
    u = xx * math.cos(angle) + yy * math.sin(angle)
    band = (np.floor(u * stripes) % 2)[..., None]
    a = np.array(GRASS_A, np.float32) * (1 - band) + np.array(GRASS_B, np.float32) * band
    rng = np.random.default_rng(7)
    a = a * (1 + rng.normal(0, 0.035, (N, N, 1)).astype(np.float32))
    r = np.sqrt((xx - 0.5) ** 2 + (yy - 0.45) ** 2)[..., None]
    a = a * (1.15 - vignette * r) + np.array(GRASS_DARK, np.float32) * (vignette * r * 0.6)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')


def _night(N):
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
    r = np.sqrt((xx - 0.5) ** 2 + (yy - 0.42) ** 2)[..., None]
    a = np.array(NAVY, np.float32) * (1.35 - 1.1 * r) + np.array(DEEP, np.float32) * (r * 0.8)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')


def _pitch_lines(img, N, alpha=150, cy=0.5, r=0.30, w=0.009):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    W = max(3, int(N * w))
    d.line(((0, N * cy), (N, N * cy)), fill=LINE + (alpha,), width=W)
    d.ellipse((N / 2 - N * r, N * cy - N * r, N / 2 + N * r, N * cy + N * r), outline=LINE + (alpha,), width=W)
    img.alpha_composite(lay)


def _medal(img, N, cx, cy, R, fill=DEEP, ring=(255, 255, 255)):
    m = Image.new('L', img.size, 0)
    ImageDraw.Draw(m).ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
    _shadow(img, m, off=(0, int(N * 0.016)), blur=int(N * 0.025), alpha=150)
    yy = np.linspace(0, 1, img.size[1], dtype=np.float32)[:, None, None]
    a = np.zeros((img.size[1], img.size[0], 4), np.float32)
    a[..., :3] = np.array(fill, np.float32) * (1.25 - 0.55 * yy)
    a[..., 3] = np.asarray(m, np.float32)
    img.alpha_composite(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA'))
    d = ImageDraw.Draw(img)
    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=ring + (255,), width=int(N * 0.012))
    d.ellipse((cx - R * 0.88, cy - R * 0.88, cx + R * 0.88, cy + R * 0.88), outline=GOLD + (210,), width=int(N * 0.006))


# ------------------------------------------------------------------ варианты
def avatar_pitch(path, N=1024):
    img = _grass(N, stripes=8)
    _pitch_lines(img, N, alpha=170, r=0.385)
    cx = cy = N / 2
    R = N * 0.33
    _medal(img, N, cx, cy, R, fill=NAVY)
    _glow_text(img, (cx + N * 0.005, cy - N * 0.03), 'J', UNB(N * 0.36), blur=int(N * 0.03))
    _arc_text(img, 'JARVIS', cx, cy, R * 0.72, UNB(N * 0.052), (255, 255, 255), start_deg=90, bottom=True)
    img.convert('RGB').save(path, quality=95)
    return path


def avatar_jball(path, N=1024):
    img = _night(N)
    _pitch_lines(img, N, alpha=40, cy=0.5, r=0.33, w=0.007)
    f = UNB(N * 0.52)
    jx, jy = N * 0.60, N * 0.46
    _glow_text(img, (jx, jy), 'J', f, blur=int(N * 0.035))
    l, t, r_, b = ImageDraw.Draw(img).textbbox((jx, jy), 'J', font=f, anchor='mm')
    D = int(N * 0.22)
    _put_ball(img, D, l - D * 0.38, b - D * 0.50, rot=(0.5, -0.35, 0.3))   # мяч у кончика крючка, букву не закрывает
    img.convert('RGB').save(path, quality=95)
    return path


def avatar_badge(path, N=1024):
    img = _grass(N, stripes=7, angle=0.6)
    cx = cy = N / 2
    D = int(N * 0.80)
    _put_ball(img, D, cx, cy, rot=(0.0, 0.0, 0.0), shadow=(0.0, 0.025))
    _medal(img, N, cx, cy, N * 0.175, fill=NAVY, ring=GOLD)
    _glow_text(img, (cx + N * 0.003, cy - N * 0.008), 'J', UNB(N * 0.22), blur=int(N * 0.02))
    img.convert('RGB').save(path, quality=95)
    return path


AVATARS = {'pitch': avatar_pitch, 'jball': avatar_jball, 'badge': avatar_badge}


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(out, exist_ok=True)
    av = [(k, fn(os.path.join(out, 'football_%s.jpg' % k))) for k, fn in AVATARS.items()]
    preview(av, os.path.join(out, 'football_preview.jpg'), name='JARVIS', sub='Матчи дня: АПЛ, 10 матчей',
            post='МАТЧИ ДНЯ · суббота, 17 октября')
    print('\n'.join(p for _, p in av))
