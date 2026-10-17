# -*- coding: utf-8 -*-
"""«Живые» плашки клубов: те же 54 текстовые плашки (make.e_club, без логотипов), но плашка колышется, как флаг
на баннерах канала (render/versus_anim.py): бегущие волны от «древка» (левый край) к свободному правому краю,
светотень складок и атласный блик; контур и тень (make.finish) повторяют волнистый силуэт.

Формат Telegram для видео-эмодзи: WEBM VP9 с альфой (yuva420p), 100×100, ≤ 3 с, ≤ 64 КБ, без звука.
Петля 2 с, бесшовная: у каждой волны целое число периодов за петлю. Амплитуда маленькая — аббревиатура
читается и при ~20 px.

Запуск:  python team/emoji/clubs_anim.py [папка] [ключи…] [--no-sheet]
         → <папка>/<ключ>.webm, frames/<ключ>/NNN.png, decoded/…, probe.json, sheet_clubs.png, sheet_clubs_20px.png
Эти WEBM build.py кладёт в набор jarvibet_clubs с пометкой "replace" (publish.py заменит статичные на месте).
"""
import json
import math
import os
import shutil
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import anim as A  # noqa: E402
import make as mk  # noqa: E402

DEFAULT_OUT = '/tmp/claude-0/-home-user--kaper-jarvis-bot/750ccff3-fed4-56c4-8b4f-e7d578ed1f4d/scratchpad/owner8_9/clubs_anim'
FPS = A.FPS
DUR = 2.0
NF = int(round(DUR * FPS))
KEYS = mk.GROUPS['khl'] + mk.GROUPS['nhl']

# Волны: (амплитуда, ед.; длина волны, ед.; наклон фронта, °; периодов за петлю; фаза; вес в светотени).
# Длинная складка несёт почти всю светотень, мелкая рябь только оживляет (как WAVES в versus_anim).
WAVES = ((2.1, 84, 10, 1, 0.0, 1.0), (0.75, 46, -16, 2, 1.7, 0.55), (0.3, 30, 24, 3, 4.1, 0.25))
DX_K = 0.18                 # продольный сдвиг ткани в складках (доля вертикального, в квадратуре)
FOLD = 0.17                 # глубина светотени складок
SATIN = 0.16                # сила атласного блика на гребнях
LIGHT = (0.85, 0.5)
X_POLE, X_FREE = mk.CLUB_BOX[0], mk.CLUB_BOX[2]

_X, _Y = mk._X, mk._Y       # координаты пикселей 800² в единицах
_ENV = (0.3 + 0.7 * np.clip((_X - X_POLE) / (X_FREE - X_POLE), 0, 1) ** 1.2).astype(np.float32)


def fields(tau, phase=0.0):
    """→ (dx, dy, shade) в единицах для момента tau ∈ [0, 1); phase — сдвиг фазы клуба (плашки в строке не синхронны)."""
    z = np.zeros_like(_X)
    zq = np.zeros_like(_X)
    slope = np.zeros_like(_X)
    smax = 0.0
    for amp, lam, ang, n, ph, wl in WAVES:
        kx = math.cos(math.radians(ang)) / lam
        ky = math.sin(math.radians(ang)) / lam
        p = (np.float32(2 * math.pi * kx) * _X + np.float32(2 * math.pi * ky) * _Y
             + np.float32((ph + phase * n - 2 * math.pi * n * tau) % (2 * math.pi)))
        s, c = np.sin(p), np.cos(p)
        z += amp * s
        zq += amp * c
        g = wl * amp * 2 * math.pi * (LIGHT[0] * kx + LIGHT[1] * ky)
        slope += np.float32(g) * c
        smax += abs(g)
    dy = _ENV * z
    dx = DX_K * _ENV * zq
    sl = _ENV * slope / smax
    shade = 1 + FOLD * sl
    spec = SATIN * np.clip(sl, 0, None) ** 3
    return dx, dy, shade, spec


def warp(src, dx, dy):
    """src (H, W, 4) float, премультиплицированная альфа; выход[p] = src[p − d] (билинейно, за краем — прозрачно)."""
    h, w = src.shape[:2]
    xs = (_X - dx) * mk.S - 0.5
    ys = (_Y - dy) * mk.S - 0.5
    x0 = np.floor(xs).astype(np.int32)
    y0 = np.floor(ys).astype(np.int32)
    fx = (xs - x0)[..., None]
    fy = (ys - y0)[..., None]
    pad = np.zeros((h + 2, w + 2, 4), np.float32)
    pad[1:-1, 1:-1] = src
    x0 = np.clip(x0 + 1, 0, w)
    y0 = np.clip(y0 + 1, 0, h)
    a = pad[y0, x0]
    b = pad[y0, x0 + 1]
    c = pad[y0 + 1, x0]
    d = pad[y0 + 1, x0 + 1]
    return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy


_ART = {}


def art_of(key):
    if key not in _ART:
        a = np.asarray(mk.EMOJI[key][0](), np.float32) / 255
        a[..., :3] *= a[..., 3:4]
        _ART[key] = a
    return _ART[key]


def phase_of(key):
    return (KEYS.index(key) * 2.399) % (2 * math.pi) if key in KEYS else 0.0


def frame(key, i):
    tau = (i % NF) / NF
    dx, dy, shade, spec = fields(tau, phase_of(key))
    p = warp(art_of(key), dx, dy)
    al = p[..., 3:4]
    rgb = p[..., :3] * shade[..., None] + spec[..., None] * al
    rgba = np.concatenate([np.clip(rgb / np.maximum(al, 1e-6), 0, 1), al], axis=2)
    art = Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA')
    return mk.finish(art)


def _render_key(job):
    key, out = job
    d = os.path.join(out, 'frames', key)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    for i in range(NF):
        frame(key, i).save(os.path.join(d, '%03d.png' % i))
    return key


def render(keys, out):
    with Pool(os.cpu_count() or 2) as p:
        for n, k in enumerate(p.imap_unordered(_render_key, [(k, out) for k in keys]), 1):
            print('  %2d/%d %s' % (n, len(keys), k), flush=True)


def _encode_key(job):
    key, out = job
    path, crf = A.encode_fit(key, out)
    info = dict(A.probe(path), crf=crf)
    fr = A.decode(path, os.path.join(out, 'decoded', key))
    info['seam'] = A.seam(fr)
    return key, info


# ───────────────────────────── контрольные листы ─────────────────────────────

def sheet(keys, out, n=4):
    """Все плашки: n кадров каждой в 1× (100 px) на тёмном и светлом фоне; справа — 20 px (тёмный/светлый)."""
    cols = 3
    cw = n * 104 + 2 * 26 + 24
    ch = 2 * 104 + 18
    rows = (len(keys) + cols - 1) // cols
    img = Image.new('RGB', (cols * cw + 20, rows * ch + 40), (60, 62, 70))
    d = ImageDraw.Draw(img)
    fl = mk.font('JetBrainsMono[wght].ttf', 12, 600)
    d.text((10, 10), 'jarvibet_clubs · живые плашки · %d шт. · кадры 0, %s · справа 20 px' % (
        len(keys), ', '.join(str(round(j * NF / n)) for j in range(1, n))), font=fl, fill=(230, 230, 236))
    for j, k in enumerate(keys):
        x0 = 10 + (j % cols) * cw
        y0 = 34 + (j // cols) * ch
        fr = A.decode(os.path.join(out, k + '.webm'), os.path.join(out, 'decoded', k))
        for r, bg in enumerate((mk.TG_DARK, (255, 255, 255))):
            img.paste(bg, (x0, y0 + r * 104, x0 + cw - 14, y0 + r * 104 + 104))
            for c in range(n):
                f = fr[round(c * len(fr) / n)]
                img.paste(f, (x0 + 2 + c * 104, y0 + 2 + r * 104), f)
            for c in range(2):
                s = fr[round(c * len(fr) / 2)].resize((20, 20), Image.LANCZOS)
                img.paste(s, (x0 + n * 104 + 6 + c * 26, y0 + 42 + r * 104), s)
        d.text((x0 + 4, y0 + 2 * 104 + 2), k, font=fl, fill=(220, 220, 228))
    p = os.path.join(out, 'sheet_clubs.png')
    img.save(p)
    return p


def strip20(keys, out):
    """Строки «как в сообщении»: все плашки по 20 px, кадр 0 и середина петли, тёмная и светлая тема."""
    W = 20 + len(keys) * 23
    img = Image.new('RGB', (W, 4 * 28 + 30), mk.TG_DARK)
    img.paste((255, 255, 255), (0, 2 * 28 + 15, W, img.height))
    for j, k in enumerate(keys):
        fr = [Image.open(os.path.join(out, 'decoded', k, f)).convert('RGBA')
              for f in sorted(os.listdir(os.path.join(out, 'decoded', k)))]
        for r in range(4):
            theme, ff = divmod(r, 2)
            s = fr[ff * len(fr) // 2].resize((20, 20), Image.LANCZOS)
            img.paste(s, (10 + j * 23, 10 + theme * 15 + r * 28), s)
    p = os.path.join(out, 'sheet_clubs_20px.png')
    img.save(p)
    return p


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0] if args else DEFAULT_OUT
    keys = args[1:] or KEYS
    os.makedirs(out, exist_ok=True)
    render(keys, out)
    with Pool(os.cpu_count() or 2) as p:
        res = dict(p.map(_encode_key, [(k, out) for k in keys]))
    bad = 0
    for k in keys:
        i = res[k]
        ok = (i['codec'] == 'vp9' and (i['w'], i['h']) == (100, 100) and i['dur'] <= 3.0 and i['size'] <= A.MAX_BYTES
              and i['audio'] == 0)
        bad += not ok
        print('%-10s %dx%d %5.2fs %3d fr %5.1f KB crf %2d seam %.2f/%.2f %s' % (
            k, i['w'], i['h'], i['dur'], i['frames'], i['size'] / 1024, i['crf'], i['seam'][0], i['seam'][1],
            'OK' if ok else 'FAIL'))
    with open(os.path.join(out, 'probe.json'), 'w') as f:
        json.dump(res, f, indent=1)
    print('не прошли:', bad)
    if '--no-sheet' not in sys.argv:
        print(sheet(keys, out))
        print(strip20(keys, out))
