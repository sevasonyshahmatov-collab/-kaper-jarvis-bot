# -*- coding: utf-8 -*-
"""«Живые» эмодзи клубов с настоящими эмблемами (как на баннерах): poster._emblem(team, size) — та же белая
«наклейка» вокруг логотипа, что на Versus; для НХЛ сначала nhl.register(). Движение — как у эмблем на анимированных
баннерах (render/versus_anim.py, _Emblem.motion): эмблема чуть «парит» — покачивается вверх-вниз, едва
заметно дрейфует вбок, наклоняется и «дышит» масштабом, мягкая тень отстаёт и расплывается, когда эмблема выше.

Два вида:
  A — эмблема сама по себе, парит над своей тенью (крупнее всего — лучше читается при 20 px);
  B — эмблема на маленьком флаге-квадрате цвета клуба, флаг колышется (волны и светотень — clubs_anim.fields/warp).

Формат Telegram для видео-эмодзи: WEBM VP9 с альфой, 100×100, ≤ 3 с, ≤ 64 КБ, без звука; петля бесшовная
(одно колебание за петлю, волны флага — целое число периодов). Порядок и эмодзи — как у опубликованного набора
jarvibet_clubs (make.GROUPS['khl'] + ['nhl'], эмодзи 🏒); текстовые плашки остаются в clubs_anim.py.

Запуск:  PYTHONPATH=render python team/emoji/clubs_logo.py [A|B] [папка] [ключи…] [--no-sheet]
         → <папка>/<ключ>.webm, frames/, decoded/, probe.json, sheet_clubs.png, sheet_clubs_20px.png
"""
import json
import math
import os
import shutil
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, '..', '..', 'render'))
import anim as A  # noqa: E402  — кодирование / проверка (encode_fit, probe, decode, seam)
import clubs_anim as CA  # noqa: E402  — волны флага
import make as mk  # noqa: E402
import nhl as _nhl  # noqa: E402
import poster as _poster  # noqa: E402

_nhl.register(make_placeholders=False)      # клубы НХЛ → poster.TEAMS (эмблемы уже лежат в render/emblems)

SCR = '/tmp/claude-0/-home-user--kaper-jarvis-bot/750ccff3-fed4-56c4-8b4f-e7d578ed1f4d/scratchpad/owner8_9/clubs_logo'
FPS = A.FPS
DUR = 3.0                     # одно спокойное колебание за 3 с (на баннерах — за 4 с)
NF = int(round(DUR * FPS))
SS = 4                        # кадр рисуем в 400×400 и уменьшаем до 100×100
KEYS = mk.GROUPS['khl'] + mk.GROUPS['nhl']
RU = {**{k: ru for ru, k in mk.KHL_KEY.items()}, **{k: ru for ru, k in mk.NHL_KEY.items()}}

# парение (px итогового кадра 100×100 / градусы / доля масштаба)
BOB, DRIFT, ROT, BREATH = 2.2, 0.7, 2.6, 0.022
LOOK = {'A': dict(box=(92, 84), cy=47.5), 'B': dict(box=(78, 62), cy=49.0)}   # эмблема вписана в прямоугольник, px


def club_color(key):
    ru = RU[key]
    if key.startswith('khl_'):
        return _poster.BANNER[ru], _poster.TEAMS[ru][1:3]
    v = _nhl.TEAMS[ru]
    return v[1], [v[2]]


_EM = {}


def emblem(key, box):
    """Эмблема в белой «наклейке» (poster._emblem), обрезанная по силуэту и вписанная в прямоугольник box px
    → PIL 'RGBa' (предумноженная альфа: повороты без тёмной каймы)."""
    k = (key, box)
    if k not in _EM:
        im = _poster._emblem(RU[key], int(max(box) * SS * 1.25))
        im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
        sc = min(box[0] * SS / im.width, box[1] * SS / im.height)
        im = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.LANCZOS)
        _EM[k] = im.convert('RGBa')
    return _EM[k]


def phase_of(key):
    return (KEYS.index(key) * 2.399) % (2 * math.pi)


def motion(tau, ph):
    """Как versus_anim._Emblem.motion: b > 0 — эмблема выше (ближе к зрителю)."""
    b = math.sin(2 * math.pi * tau + ph)
    ex = DRIFT * math.sin(2 * math.pi * tau + ph + math.pi / 2)
    ey = -BOB * b
    rot = ROT * math.sin(2 * math.pi * tau + ph + 0.9)
    sc = 1 + BREATH * b
    return ex, ey, rot, sc, b


def place(img, cx, cy, ang, k):
    """'RGBa' → кадр 400×400 'RGBa': центр картинки в (cx, cy) px итогового кадра, поворот ang° по часовой, масштаб k."""
    N = 100 * SS
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    a, b, d, e = c / k, s / k, -s / k, c / k
    X, Y = cx * SS, cy * SS
    w2, h2 = img.width / 2, img.height / 2
    return img.transform((N, N), Image.AFFINE, (a, b, w2 - a * X - b * Y, d, e, h2 - d * X - e * Y),
                         resample=Image.BICUBIC)


def shadow_of(lay, dx, dy, blur, alpha):
    """Мягкая тень слоя: силуэт со сдвигом (px 100×100), размытый, чёрный с прозрачностью alpha → 'RGBA' 400×400."""
    a = lay.getchannel('A')
    sh = Image.new('L', a.size, 0)
    sh.paste(a, (int(round(dx * SS)), int(round(dy * SS))))
    sh = sh.filter(ImageFilter.GaussianBlur(blur * SS)).point(lambda v: int(v * alpha))
    out = Image.new('RGBA', a.size, (6, 8, 14, 0))
    out.putalpha(sh)
    return out


def finish(rgba400):
    """400×400 → 100×100 LANCZOS и лёгкая резкость (логотипы при 100 px иначе мылятся)."""
    im = rgba400.resize((100, 100), Image.LANCZOS)
    rgb = im.convert('RGB').filter(ImageFilter.UnsharpMask(radius=0.8, percent=45, threshold=1))
    rgb.putalpha(im.getchannel('A'))
    return rgb


# ───────────────────────────── вид A: эмблема парит над тенью ─────────────────────────────

def frame_A(key, i):
    tau = (i % NF) / NF
    ex, ey, rot, sc, b = motion(tau, phase_of(key))
    cy = LOOK['A']['cy']
    em = place(emblem(key, LOOK['A']['box']), 50 + ex, cy + ey, rot, sc).convert('RGBA')
    # тень «на столе»: отстаёт от эмблемы, выше — мягче, светлее и дальше
    sh = shadow_of(em, 0.6 - 0.3 * ex, 3.2 - ey * 0.55 + 0.6 * b, 1.6 + 0.5 * b, 0.42 - 0.07 * b)
    out = Image.alpha_composite(sh, em)
    return finish(out)


# ───────────────────────────── вид B: эмблема на флаге-квадрате ─────────────────────────────

_FLAG = {}


def flag_art(key):
    """Плоский «флаг» цвета клуба 800×800 (как плашка e_club без текста): градиент, кольца Versus, кайма вторым
    цветом, блик → numpy предумноженный."""
    if key not in _FLAG:
        col, seconds = club_color(key)
        rim, _ = mk.club_colors(col, seconds)
        art = mk.new()
        box = (6, 14, 94, 86)
        x0, y0, x1, y1 = box
        w = 3.4
        pm = mk.rrect(mk.M(), box, 12)
        inner = mk.rrect(mk.M(), (x0 + w, y0 + w, x1 - w, y1 - w), 12 - w)
        mk.put(art, mk.lin([mk.mix(col, 0.22), col, mk.mix(col, -0.28)], pm), pm)
        mk.rings(art, inner, x0 + 6, y0 - 4, step=5.5, alpha=0.08)
        rm = mk.sub(pm, inner)
        mk.put(art, mk.lin([mk.mix(rim, 0.5), rim, mk.mix(rim, -0.4)], rm), rm)
        mk.bevel(art, rm, hi=0.5, lo=0.45, d=1.4, b=0.7)
        mk.gloss(art, inner, (x0 - 6, y0 - 12, x0 + 60, y0 + 26), alpha=0.12)
        a = np.asarray(art, np.float32) / 255
        a[..., :3] *= a[..., 3:4]
        _FLAG[key] = a
    return _FLAG[key]


def frame_B(key, i):
    tau = (i % NF) / NF
    ph = phase_of(key)
    # флаг: волны с периодом петли (clubs_anim — петля 2 с; здесь tau той же формы, n периодов за 3 с)
    dx, dy, shade, spec = CA.fields(tau, ph)
    p = CA.warp(flag_art(key), dx, dy)
    al = p[..., 3:4]
    rgb = p[..., :3] * shade[..., None] + spec[..., None] * al
    rgba = np.concatenate([np.clip(rgb / np.maximum(al, 1e-6), 0, 1), al], axis=2)
    fl = Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA')
    fl = mk.finish(fl).resize((100 * SS, 100 * SS), Image.LANCZOS)      # тёмный контур и тень семейства эмодзи
    ex, ey, rot, sc, b = motion(tau, ph + 1.0)
    k = 0.45                                                             # парит слабее, чем вид A
    em = place(emblem(key, LOOK['B']['box']), 50 + ex * k, LOOK['B']['cy'] + ey * k, rot * 0.6, 1 + (sc - 1) * k)
    em = em.convert('RGBA')
    sh = shadow_of(em, 1.2, 2.6 + 0.5 * b, 1.4 + 0.3 * b, 0.5)
    # тень эмблемы — только на ткани
    sha = np.asarray(sh.getchannel('A'), np.float32) * (np.asarray(fl.getchannel('A'), np.float32) / 255)
    sh.putalpha(Image.fromarray(sha.astype(np.uint8)))
    out = Image.alpha_composite(Image.alpha_composite(fl, sh), em)
    return finish(out)


FRAMES = {'A': frame_A, 'B': frame_B}


# ───────────────────────────── рендер, кодирование, листы ─────────────────────────────

def _render_key(job):
    look, key, out = job
    d = os.path.join(out, 'frames', key)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    for i in range(NF):
        im = FRAMES[look](key, i)
        assert im.size == (100, 100) and im.mode == 'RGBA'
        im.save(os.path.join(d, '%03d.png' % i))
    path, crf = A.encode_fit(key, out)
    info = dict(A.probe(path), crf=crf)
    fr = A.decode(path, os.path.join(out, 'decoded', key))
    info['seam'] = A.seam(fr)
    return key, info


def _decoded(out, k):
    d = os.path.join(out, 'decoded', k)
    return [Image.open(os.path.join(d, f)).convert('RGBA') for f in sorted(os.listdir(d))]


def sheet(keys, out, title, n=4):
    """Все клубы: n кадров в 1× на тёмном и светлом фоне, справа — те же кадры по 20 px."""
    cols = 3
    cw = n * 104 + 2 * 26 + 24
    ch = 2 * 104 + 18
    rows = (len(keys) + cols - 1) // cols
    img = Image.new('RGB', (cols * cw + 20, rows * ch + 40), (60, 62, 70))
    d = ImageDraw.Draw(img)
    fl = mk.font('JetBrainsMono[wght].ttf', 12, 600)
    d.text((10, 10), '%s · %d шт. · кадры 0, %s · справа 20 px' % (
        title, len(keys), ', '.join(str(round(j * NF / n)) for j in range(1, n))), font=fl, fill=(230, 230, 236))
    for j, k in enumerate(keys):
        x0 = 10 + (j % cols) * cw
        y0 = 34 + (j // cols) * ch
        fr = _decoded(out, k)
        for r, bg in enumerate((mk.TG_DARK, (255, 255, 255))):
            img.paste(bg, (x0, y0 + r * 104, x0 + cw - 14, y0 + r * 104 + 104))
            for c in range(n):
                f = fr[round(c * len(fr) / n)]
                img.paste(f, (x0 + 2 + c * 104, y0 + 2 + r * 104), f)
            for c in range(2):
                s = fr[round(c * len(fr) / 2)].resize((20, 20), Image.LANCZOS)
                img.paste(s, (x0 + n * 104 + 6 + c * 26, y0 + 42 + r * 104), s)
        d.text((x0 + 4, y0 + 2 * 104 + 2), '%s · %s' % (k, RU[k]), font=fl, fill=(220, 220, 228))
    p = os.path.join(out, 'sheet_clubs.png')
    img.save(p)
    return p


def strip20(keys, out):
    """Как в сообщении: все клубы по 20 px (кадр 0 и середина петли), тёмная и светлая тема; ниже — по 32 px."""
    W = 20 + len(keys) * 23
    img = Image.new('RGB', (W, 4 * 28 + 30 + 2 * 40 + 20), mk.TG_DARK)
    img.paste((255, 255, 255), (0, 2 * 28 + 15, W, 4 * 28 + 30))
    for j, k in enumerate(keys):
        fr = _decoded(out, k)
        for r in range(4):
            theme, ff = divmod(r, 2)
            s = fr[ff * len(fr) // 2].resize((20, 20), Image.LANCZOS)
            img.paste(s, (10 + j * 23, 10 + theme * 15 + r * 28), s)
    y = 4 * 28 + 30
    img.paste((255, 255, 255), (0, y + 40, W, img.height))
    for j, k in enumerate(keys[:len(keys)]):
        s = _decoded(out, k)[0].resize((32, 32), Image.LANCZOS)
        x = 10 + (j % 36) * 36
        if j < 36:
            img.paste(s, (x, y + 4), s)
        else:
            img.paste(s, (x, y + 44 + 4), s)
    p = os.path.join(out, 'sheet_clubs_20px.png')
    img.save(p)
    return p


def grid_mp4(keys, out, cols=9, cell=110):
    """MP4: все клубы двигаются, 1× (100 px) на тёмном и светлом фоне, 2 петли."""
    rows = (len(keys) + cols - 1) // cols
    W, H = cols * cell, rows * cell
    frames = {k: _decoded(out, k) for k in keys}
    d = os.path.join(out, 'grid_frames')
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    for i in range(NF * 2):
        img = Image.new('RGB', (W, H * 2), mk.TG_DARK)
        img.paste((255, 255, 255), (0, H, W, 2 * H))
        for half in range(2):
            for j, k in enumerate(keys):
                f = frames[k][i % len(frames[k])]
                img.paste(f, ((j % cols) * cell + 5, half * H + (j // cols) * cell + 5), f)
        img.save(os.path.join(d, '%03d.png' % i))
    p = os.path.join(out, 'preview_grid.mp4')
    import subprocess
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(d, '%03d.png'),
                    '-vf', 'scale=iw*2:ih*2:flags=neighbor', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16',
                    '-preset', 'medium', p], check=True)
    shutil.rmtree(d, ignore_errors=True)
    return p


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    look = args[0] if args and args[0] in FRAMES else 'A'
    args = args[1:] if args and args[0] in FRAMES else args
    out = args[0] if args else os.path.join(SCR, look)
    keys = args[1:] or KEYS
    os.makedirs(out, exist_ok=True)
    with Pool(os.cpu_count() or 2) as p:
        res = dict(p.imap_unordered(_render_key, [(look, k, out) for k in keys]))
    bad = 0
    for k in keys:
        i = res[k]
        ok = (i['codec'] == 'vp9' and (i['w'], i['h']) == (100, 100) and i['dur'] <= 3.0 and i['size'] <= A.MAX_BYTES
              and i['audio'] == 0)
        bad += not ok
        print('%-10s %dx%d %5.2fs %3d fr %5.1f KB crf %2d seam %.2f/%.2f %s' % (
            k, i['w'], i['h'], i['dur'], i['frames'], i['size'] / 1024, i['crf'], i['seam'][0], i['seam'][1],
            'OK' if ok else 'FAIL'), flush=True)
    pj = os.path.join(out, 'probe.json')
    old = json.load(open(pj)) if os.path.exists(pj) else {}
    old.update(res)
    json.dump(old, open(pj, 'w'), indent=1)
    print('не прошли:', bad)
    if '--no-sheet' not in sys.argv:
        print(sheet(keys, out, 'jarvibet_clubs · эмблемы · вид ' + look))
        print(strip20(keys, out))
        if '--mp4' in sys.argv:
            print(grid_mp4(keys, out))
