# -*- coding: utf-8 -*-
"""Анимированные кастомные эмодзи Telegram (видео-эмодзи) для @jarvibet.

Те же рисунки, что и в make.py: каждая функция e_<ключ>() принимает параметры анимации (доля прорисовки,
масштаб, поворот, положение блика, фаза…), а здесь — только тайминги. Кадр рисуется в 8× (800×800),
проходит тот же finish() (контур + тень) и уменьшается до 100×100.

Требования Telegram к видео-эмодзи: WEBM / VP9 с альфой (yuva420p), ровно 100×100, ≤ 3 с, 30 fps,
без звука, бесшовная петля, ≤ 64 КБ.

Запуск:  python team/emoji/anim.py [папка] [ключи…] [--no-preview] [--encode-only]
         → <папка>/<ключ>.webm, preview.gif, preview.mp4, frames/<ключ>/NNN.png, sheets/<ключ>.png
"""
import json
import math
import os
import shutil
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make as mk  # noqa: E402
from make import finish, xform  # noqa: E402

DEFAULT_OUT = '/tmp/claude-0/-home-user--kaper-jarvis-bot/750ccff3-fed4-56c4-8b4f-e7d578ed1f4d/scratchpad/emoji_anim'
FPS = 30
MAX_BYTES = 64 * 1024                                 # лимит Telegram для видео-эмодзи
BUDGET = 60 * 1024                                    # целимся с запасом


# ───────────────────────────── тайминги ─────────────────────────────

def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def seg(t, a, b):
    """Доля пройденного отрезка [a, b] (0 до, 1 после)."""
    return clamp((t - a) / (b - a))


def smooth(x):
    return x * x * (3 - 2 * x)


def ease_out(x, p=3):
    return 1 - (1 - x) ** p


def ease_in(x, p=3):
    return x ** p


def ease_io(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back_out(x, s=1.70158):
    c = s + 1
    return 1 + c * (x - 1) ** 3 + s * (x - 1) ** 2


def back_io(x, s=1.0):
    c = s * 1.525
    if x < 0.5:
        return (2 * x) ** 2 * ((c + 1) * 2 * x - c) / 2
    return ((2 * x - 2) ** 2 * ((c + 1) * (x * 2 - 2) + c) + 2) / 2


def bump(t, c, w):
    v = math.exp(-((t - c) / w) ** 2)
    return v if v > 1e-3 else 0.0


# ───────────────────────────── кадры: t — секунды от начала петли ─────────────────────────────

CHECK_F1 = math.dist(mk.CHECK[0], mk.CHECK[1]) / (math.dist(mk.CHECK[0], mk.CHECK[1]) + math.dist(mk.CHECK[1], mk.CHECK[2]))


def f_zahod(t):
    """Галочка рисуется пером (короткий штрих, потом длинный) → жетон подпрыгивает, по нему бежит блик →
    пауза → галочка гаснет и петля начинается заново с пустого жетона."""
    draw = CHECK_F1 * ease_io(seg(t, 0.10, 0.30)) + (1 - CHECK_F1) * ease_out(seg(t, 0.30, 0.58), 2)
    alpha = 1 - smooth(seg(t, 2.60, 2.86))
    hop = seg(t, 0.62, 0.98)
    lift = 2.8 * 4 * hop * (1 - hop)
    sq = 0.06 * bump(t, 0.60, 0.035) + 0.045 * bump(t, 0.99, 0.04)          # приседание перед прыжком и при посадке
    sh = seg(t, 0.70, 1.35)
    art = mk.e_zahod(draw=draw, alpha=alpha, shine=sh if 0 < sh < 1 else None)
    art = xform(art, kx=1 + sq * 0.7, ky=1 - sq, cx=50, cy=93, dy=-lift)
    return finish(art, lift=lift)


def f_minus(t):
    """Крест влетает с поворотом и «перелётом» масштаба → жетон мотает головой «нет» → пауза → крест сжимается."""
    p = seg(t, 0.10, 0.42)
    k = back_out(p, 2.0) * (1 - ease_in(seg(t, 2.55, 2.80), 2))
    ang = -90 * (1 - ease_out(p, 3))
    s = seg(t, 0.42, 1.10)
    shake = math.sin(2 * math.pi * 3 * s) * (1 - s) ** 1.6 if 0 < s < 1 else 0.0
    art = mk.e_minus(k=k, ang=ang + 6 * shake)
    art = xform(art, dx=3.0 * shake)
    return finish(art)


def f_vozvrat(t):
    """Пауза → стрелка делает полный оборот против часовой (по направлению стрелки), с замахом и доводкой."""
    x = seg(t, 0.40, 1.55)
    ang = -360 * back_io(x, 1.0) if 0 < x < 1 else 0.0
    return finish(mk.e_vozvrat(ang=ang))


def f_live(t):
    """Каждую секунду точка «вздыхает» и испускает волну; волны расходятся и гаснут (живут 2 с, видно две)."""
    waves = []
    for e in (0.0, 1.0):
        age = (t - e) % 2.0
        op = smooth(seg(age, 0.0, 0.35)) * (1 - smooth(seg(age, 1.35, 1.97)))
        waves.append((13 + 9.5 * age, op))
    tau = (t + 0.5) % 1.0 - 0.5                             # время от ближайшего «вздоха»
    pulse = bump(tau, 0.05, 0.14)
    fx = []
    art = mk.e_live(pulse=pulse, waves=waves, fx=fx)
    return finish(art, fx=fx)


def f_goal_lamp(t):
    """Двойной отражатель вращается по часовой (270°/с, за петлю — полтора оборота, лучи меняются местами):
    конусы света обегают веер, лучи вспыхивают по очереди; когда луч смотрит вверх — вспышка купола и ореола."""
    b = -90 + 270 * t
    beams = (b, b + 180)
    flash = max(max(0.0, -math.sin(math.radians(a))) ** 3 for a in beams)
    fx = []
    art = mk.e_goal_lamp(beam=beams, flash=flash, fx=fx)
    return finish(art, fx=fx)


def f_seriya(t):
    """Языки пламени колышутся (гармоники 2 и 3 за петлю — бесшовно)."""
    return finish(mk.e_seriya(ph=t / 2.0))


SPARKS = [  # (x, y, r, когда): искорки в просветах между лучами звезды вслед за бликом, потом — на кончиках лучей
    (32.5, 23.5, 5.0, 0.40), (20.5, 57.5, 4.4, 0.52), (50.0, 79.0, 4.8, 0.74), (68.0, 23.0, 6.4, 0.86),
    (79.5, 57.5, 4.6, 1.02), (50.0, 16.5, 7.0, 1.75), (68.2, 72.6, 6.2, 2.15),
]


def f_stavka_dnya(t):
    """По звезде и ободку пробегает блик, звезда чуть «вдыхает», вокруг вспыхивают искорки."""
    sh = seg(t, 0.20, 1.00)
    k = 1 + 0.05 * bump(t, 0.60, 0.16)
    sp = []
    for x, y, r, t0 in SPARKS:
        a = seg(t, t0, t0 + 0.45)
        if 0 < a < 1:
            sp.append((x, y, r * math.sin(math.pi * a) ** 1.5, 45 * a))
    return finish(mk.e_stavka_dnya(k=k, shine=sh if 0 < sh < 1 else None, sparkles=sp))


_HG_EXT = {}


def _hg_scale(ang, lim=44.0):
    """Масштаб часов при повороте на ang°, чтобы углы крышек не вылезали за кадр (полу-габарит ≤ lim ед.)."""
    key = round(ang, 1)
    if key not in _HG_EXT:
        a = mk.e_zhdem().getchannel('A').resize((200, 200), Image.BILINEAR)
        bb = a.rotate(-ang, resample=Image.BILINEAR, center=(100, 100), expand=False).point(
            lambda v: 255 if v > 40 else 0).getbbox()
        ext = max(100 - bb[0], bb[2] - 100, 100 - bb[1], bb[3] - 100) / 2
        _HG_EXT[key] = min(1.0, lim / ext)
    return _HG_EXT[key]


def f_zhdem(t):
    """Песок пересыпается (струйка с бегущими песчинками, сверху уровень падает, снизу растёт горка) →
    часы переворачиваются на 180° (песок в мире «стекает» вниз) → петля: снова полный верх."""
    flow, fall = 2.25, 0.12
    flip = seg(t, 2.33, 2.93)
    if flip <= 0:
        head = clamp(t / fall) ** 2
        tail = clamp((t - flow) / fall) ** 2
        art = mk.e_zhdem(sand=clamp(t / flow), stream=(tail, head) if head > tail else None, grain=(t * 2.2) % 1)
    else:
        ang = 180 * ease_io(flip)
        art = mk.e_zhdem(sand=1.0, ang=ang, k=_hg_scale(ang), mound=1 - smooth(seg(flip, 0.0, 0.6)), stream=None)
    return finish(art)


def _puck_dx(t):
    if t < 0.5:                                               # влетает слева, тормозит с небольшим перелётом
        return -108 + 111 * ease_out(seg(t, 0.0, 0.5), 3)
    if t < 1.1:                                               # доводка к центру
        x = seg(t, 0.5, 1.1)
        return 3 * math.cos(math.pi * 1.5 * x) * (1 - x) ** 1.5
    if t < 2.45:
        return 0.0
    if t < 2.62:                                              # замах назад
        return -2.5 * smooth(seg(t, 2.45, 2.62))
    return -2.5 + 112 * ease_in(seg(t, 2.62, 3.0), 3)          # улетает вправо → снова влетает слева


def _puck_v(t):
    t = t % 3.0
    a, b = max(t - 1 / 240, 0.0), min(t + 1 / 240, 2.9999)
    return (_puck_dx(b) - _puck_dx(a)) / (b - a)


def f_puck(t):
    """Шайба влетает слева со «следами скорости», тормозит, покачивается и встаёт; пауза; улетает вправо.
    Следы тянутся за скоростью с запаздыванием (втягиваются ~0.3 с после остановки)."""
    dx = _puck_dx(t)
    v = _puck_v(t)
    streak = max(max(0.0, _puck_v(t - lag)) * 0.1 * (1 - lag / 0.3) for lag in np.linspace(0, 0.3, 13))
    streak = min(40.0, streak)
    kx = 1 + min(0.06, abs(v) / 11000)
    x = seg(t, 0.42, 1.2)
    tilt = 4.5 * math.sin(math.pi * 2 * x) * (1 - x) ** 1.3 if 0 < x < 1 else 0.0       # клюёт вперёд и качается
    tilt -= 3.0 * math.sin(math.pi * seg(t, 2.45, 2.75))                                 # отклоняется при старте
    art = mk.e_puck(dx=dx, kx=kx, streak=streak)
    art = xform(art, ang=tilt, cx=50 + dx, cy=81)
    return finish(art)


# ключ → (длительность, с; кадр(t); сдвиг старта, с). Петля бесшовная, поэтому старт можно сдвинуть:
# первый кадр — «спокойная» поза, как у статичной картинки (Telegram показывает его как превью,
# например в режиме энергосбережения, когда анимации выключены).
ANIMS = {
    'zahod': (3.0, f_zahod, 1.5),
    'minus': (3.0, f_minus, 1.5),
    'vozvrat': (2.0, f_vozvrat, 0.0),
    'live': (2.0, f_live, 0.6),
    'goal_lamp': (2.0, f_goal_lamp, 0.0),
    'seriya': (2.0, f_seriya, 0.0),
    'stavka_dnya': (3.0, f_stavka_dnya, 0.0),
    'zhdem': (3.0, f_zhdem, 1.0),
    'puck': (3.0, f_puck, 1.5),
}


def n_frames(key):
    return int(round(ANIMS[key][0] * FPS))


# ───────────────────────────── рендер и кодирование ─────────────────────────────

def frame(key, i):
    dur, fn, off = ANIMS[key]
    return fn(round((i / FPS + off) % dur, 6))


def _render_one(job):
    key, i, path = job
    im = frame(key, i)
    assert im.size == (mk.SIZE, mk.SIZE) and im.mode == 'RGBA'
    im.save(path)
    return path


def render_frames(keys, out):
    jobs = []
    for k in keys:
        d = os.path.join(out, 'frames', k)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        jobs += [(k, i, os.path.join(d, '%03d.png' % i)) for i in range(n_frames(k))]
    with Pool(os.cpu_count() or 2) as p:
        for n, _ in enumerate(p.imap_unordered(_render_one, jobs, chunksize=2), 1):
            if n % 100 == 0 or n == len(jobs):
                print('  frames %d/%d' % (n, len(jobs)), flush=True)


def encode(key, out, crf):
    src = os.path.join(out, 'frames', key, '%03d.png')
    dst = os.path.join(out, key + '.webm')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', src,
                    '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-auto-alt-ref', '0', '-b:v', '0', '-crf', str(crf),
                    '-deadline', 'good', '-cpu-used', '0', '-row-mt', '1', '-g', '300', '-an',
                    '-metadata:s:v:0', 'alpha_mode=1', dst], check=True)
    return dst


def encode_fit(key, out, crfs=(4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 45, 50)):
    """Лучшее качество (меньший crf), которое влезает в бюджет 60 КБ (лимит — 64 КБ).
    Низкий crf заодно убирает «залипшие» пиксели: при crf ≥ 12 libvpx оставляет на пустом жетоне
    следы погасшей галочки/искры на несколько кадров."""
    for crf in crfs:
        dst = encode(key, out, crf)
        if os.path.getsize(dst) <= BUDGET:
            return dst, crf
    return dst, crfs[-1]


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', path],
                       capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = [s for s in j['streams'] if s['codec_type'] == 'video'][0]
    tags = {k.lower(): val for k, val in v.get('tags', {}).items()}
    return dict(codec=v['codec_name'], w=v['width'], h=v['height'], fps=v['r_frame_rate'],
                frames=int(v.get('nb_read_frames', 0)), dur=float(j['format']['duration']),
                alpha=tags.get('alpha_mode', '-'), audio=sum(s['codec_type'] == 'audio' for s in j['streams']),
                size=os.path.getsize(path), fmt=j['format']['format_name'])


def decode(path, d):
    """Декодировать webm с альфой (libvpx-vp9 — родной декодер ffmpeg альфу не видит)."""
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-c:v', 'libvpx-vp9', '-i', path, '-pix_fmt', 'rgba',
                    os.path.join(d, '%03d.png')], check=True)
    return [Image.open(os.path.join(d, f)).convert('RGBA') for f in sorted(os.listdir(d))]


# ───────────────────────────── превью ─────────────────────────────

CELL, GAP, LAB = 300, 20, 34


def preview(keys, decoded, info, out):
    """3×3 сетка в 3× на тёмном фоне Telegram, подписи; петля = НОК длительностей (6 с)."""
    cols = 3
    rows = (len(keys) + cols - 1) // cols
    W = cols * CELL + (cols + 1) * GAP
    H = rows * (CELL + LAB) + (rows + 1) * GAP
    W, H = W + W % 2, H + H % 2
    total = math.lcm(*[n_frames(k) for k in keys])
    fl = mk.font('JetBrainsMono[wght].ttf', 17, 600)
    fs = mk.font('JetBrainsMono[wght].ttf', 13, 400)
    d = os.path.join(out, 'preview_frames')
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    big = {k: [f.resize((CELL, CELL), Image.LANCZOS) for f in decoded[k]] for k in keys}
    base = Image.new('RGB', (W, H), mk.TG_DARK)
    dr = ImageDraw.Draw(base)
    for j, k in enumerate(keys):
        x = GAP + (j % cols) * (CELL + GAP)
        y = GAP + (j // cols) * (CELL + LAB + GAP)
        dr.text((x + CELL // 2, y + CELL + 4), k, font=fl, fill=(200, 204, 214), anchor='mt')
        dr.text((x + CELL // 2, y + CELL + 24), '%.1f s · %d KB' % (info[k]['dur'], math.ceil(info[k]['size'] / 1024)),
                font=fs, fill=(120, 124, 136), anchor='mt')
    for i in range(total):
        img = base.copy()
        for j, k in enumerate(keys):
            x = GAP + (j % cols) * (CELL + GAP)
            y = GAP + (j // cols) * (CELL + LAB + GAP)
            fr = big[k][i % len(big[k])]
            img.paste(fr, (x, y), fr)
        img.save(os.path.join(d, '%03d.png' % i))
    src = os.path.join(d, '%03d.png')
    gif = os.path.join(out, 'preview.gif')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', src, '-filter_complex',
                    '[0:v]split[a][b];[a]palettegen=stats_mode=full:max_colors=256[p];'      # bayer: ~16 МБ против 27 у sierra
                    '[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle', '-loop', '0', gif], check=True)
    mp4 = os.path.join(out, 'preview.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', src,
                    '-vf', 'loop=loop=2:size=%d:start=0' % total, '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-crf', '16', '-preset', 'slow', '-movflags', '+faststart', '-an', mp4], check=True)
    shutil.rmtree(d, ignore_errors=True)                # кадры сетки 980×1082 больше не нужны
    return gif, mp4


def sheets(keys, decoded, out, n=6):
    """Контрольные листы: n кадров каждой анимации в 2× на тёмном и светлом фоне."""
    d = os.path.join(out, 'sheets')
    os.makedirs(d, exist_ok=True)
    paths = []
    for k in keys:
        fr = decoded[k]
        idx = [round(i * len(fr) / n) for i in range(n)]
        img = Image.new('RGB', (n * 210 + 10, 2 * 210 + 10), mk.TG_DARK)
        img.paste((255, 255, 255), (0, 215, img.width, img.height))
        dr = ImageDraw.Draw(img)
        for c, i in enumerate(idx):
            f = fr[i].resize((200, 200), Image.LANCZOS)
            for r in range(2):
                img.paste(f, (10 + c * 210, 10 + r * 210), f)
            dr.text((14 + c * 210, 12), '%d' % i, fill=(150, 150, 160))
        p = os.path.join(d, k + '.png')
        img.save(p)
        paths.append(p)
    return paths


def seam(frames):
    """Насколько стык «последний → первый» похож на обычный шаг между кадрами (средняя |разница| RGBA)."""
    a = [np.asarray(f, np.float32) for f in frames]
    steps = [np.abs(a[i + 1] - a[i]).mean() for i in range(len(a) - 1)]
    return float(np.abs(a[0] - a[-1]).mean()), float(np.median(steps)), float(np.max(steps))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0] if args else DEFAULT_OUT
    keys = args[1:] or list(ANIMS)
    os.makedirs(out, exist_ok=True)
    if '--encode-only' not in sys.argv:                 # --encode-only: кадры уже есть в frames/
        print('render', ', '.join(keys), flush=True)
        render_frames(keys, out)
    info, decoded = {}, {}
    for k in keys:
        path, crf = encode_fit(k, out)
        info[k] = dict(probe(path), crf=crf)
        decoded[k] = decode(path, os.path.join(out, 'decoded', k))
        a = np.asarray(decoded[k][0])[..., 3]
        info[k]['alpha_px'] = '%d%%' % round(100 * (a < 8).mean())
        info[k]['seam'] = seam(decoded[k])
    print()
    hdr = '%-12s %-5s %-8s %-6s %-6s %-7s %-6s %-5s %-6s %-4s %-7s %s' % (
        'key', 'codec', 'size', 'fps', 'frames', 'dur,s', 'alpha', 'audio', 'KB', 'crf', 'transp', 'seam/med/max step')
    print(hdr)
    print('-' * len(hdr))
    for k in keys:
        i = info[k]
        print('%-12s %-5s %-8s %-6s %-6d %-7.3f %-6s %-5d %-6.1f %-4d %-7s %.2f / %.2f / %.2f' % (
            k, i['codec'], '%dx%d' % (i['w'], i['h']), i['fps'], i['frames'], i['dur'], i['alpha'], i['audio'],
            i['size'] / 1024, i['crf'], i['alpha_px'], *i['seam']))
    with open(os.path.join(out, 'probe.json'), 'w') as f:
        json.dump(info, f, indent=1)
    for p in sheets(keys, decoded, out):
        print(p)
    if '--no-preview' not in sys.argv:
        for p in preview(keys, decoded, info, out):
            print(p)
