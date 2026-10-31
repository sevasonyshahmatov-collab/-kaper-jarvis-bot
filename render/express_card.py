# -*- coding: utf-8 -*-
"""Купон «Экспресс» (рубрика-проба, владелец 31.10; team/picks/EXPRESS.md) — в семье баннеров «Матчи дня» / «Итоги
прогнозов» (matchday_vs.py): тёмный фон, марка JARVIS | NHL, полосы с панелями клубов и эмблемами, акцентные плашки.
Полоса ноги: хозяева слева, гости справа, посередине «АББР время АББР», ниже плашка «ставка · кэф». Внизу блок «общий кэф»
и «шанс по модели».
    import express_card as ec
    ec.render(legs, 'feed.jpg', fmt='feed')    # 1080×1350 — Telegram / лента Instagram
    ec.render(legs, 'story.jpg', fmt='story')  # 1080×1920 — сторис: крупнее, поля под интерфейс, призыв в Telegram
legs: [{home, away, time: '02:00', bet: 'инд. тотал Питтсбурга больше 1,5', kef: 1.22}]."""
import os

os.environ.setdefault('JARVIS_S', '2')

from PIL import ImageDraw

import brand_kit
import matchday_vs as mv
import nhl
import quality

S, W, MX, BG = mv.S, mv.W, mv.MX, mv.BG
OSW, ALU, MAN = mv.OSW, mv.ALU, mv.MAN


def _k(v):
    return ('%.2f' % v).replace('.', ',')


LG = {'НХЛ': 'NHL', 'КХЛ': 'KHL', 'NHL': 'NHL', 'KHL': 'KHL'}


def _lg(it):
    """Лига ноги для эмблем: НХЛ / КХЛ; футбол и неизвестное — 'FOOT' (серая панель и круг с аббревиатурой)."""
    return LG.get(str(it.get('league') or 'НХЛ'), 'FOOT')


def _leg(img, it, y0, R, acc, i, F):
    lg = _lg(it)
    hn, hc, _, ha = mv._club(it['home'], lg)
    an, ac, ac2, aa = mv._club(it['away'], lg)
    ac = mv.vs._distinct(hc, ac, ac2)
    g = mv._geom(R)
    pw, off = g['pw'], g['off']
    for x0, top, col, team, ab, seed, fade in ((MX, y0, hc, hn, ha, 11 + 7 * i, 'down'),
                                               (W - MX - pw, y0 + off, ac, an, aa, 23 + 7 * i, 'up')):
        box = (x0 * S, top * S, (x0 + pw) * S, (top + R - off) * S)
        mv._panel(img, box, col, seed, fade, (0.5, 0.52))
        es = min((R - off) * 0.84, pw * 0.76)
        mv._emblem(img, team, (x0 + pw / 2) * S, (top + (R - off) * 0.52) * S, es * S, ab, col)
    d = ImageDraw.Draw(img)
    zx0, zx1 = g['zx0'], g['zx1']
    zc = (zx0 + zx1) / 2
    ya = y0 + R * 0.34
    t = it.get('time') or ''
    mv._txt(d, zc * S, ya * S, t, F['tm'], (250, 250, 250))
    mid = F['tm'].getbbox(t, anchor='ls')[2] / S
    room = ((zx1 - zx0) / 2 - mid / 2 - 14) * S
    for abbr, col, x, anchor in ((ha, hc, zx0, 'l'), (aa, ac, zx1, 'r')):
        mv._txt(d, x * S, ya * S, abbr, mv._fit_room(abbr, ALU, 900, F['ab'], room), mv._readable(col) + (255,), anchor)
    # плашка ставки: текст ставки и кэф справа, фон — акцент
    ph = F['ph']
    yp = y0 + R * 0.76
    d.rounded_rectangle((zx0 * S, (yp - ph / 2) * S, zx1 * S, (yp + ph / 2) * S), radius=int(ph * .28 * S), fill=acc)
    kv = _k(it['kef'])
    kw = F['kef'].getbbox(kv, anchor='ls')[2] / S
    mv._txt(d, (zx1 - 14) * S, yp * S, kv, F['kef'], mv.INK + (255,), 'r')
    room = (zx1 - zx0 - kw - 42) * S
    mv._txt(d, (zx0 + 14) * S, yp * S, it['bet'], mv._fit_room(it['bet'], MAN, 800, F['bet'], room), mv.INK + (255,), 'l')


def render(legs, path, **kw):
    """Статичный баннер → path (JPG 1080 в ширину)."""
    out, _ = draw(legs, **kw)
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    out.save(path, quality=92, optimize=True)
    return path


def draw(legs, title='ЭКСПРЕСС', date_title='', total=None, chance=None, fmt='feed', cta=None, hide=False):
    """→ (картинка 1080 в ширину, места полос и итога в базовых px [(y0, y1), …]). hide=True — без ног и итога (фон
    для анимации)."""
    nhl.register()
    lgs = {_lg(it) for it in legs}
    brand = 'NHL' if lgs == {'NHL'} else 'KHL' if lgs == {'KHL'} else 'KHL+NHL'
    acc = nhl.ICE if brand != 'KHL' else mv.poster.ACC
    story = fmt == 'story'
    H = 1920 if story else 1350
    head = 330 if story else 236            # сторис: сверху ~250 px под полоску и имя профиля
    foot = 300 if story else 104
    tot_h = 210 if story else 170
    n = len(legs)
    R = int(min(300 if story else 290, (H - head - foot - tot_h - 40 - (n - 1) * mv.GAP) / n))
    block = n * R + (n - 1) * mv.GAP + 40 + tot_h
    top = head + (H - head - foot - block) // 2
    img = mv._background(H)
    d = ImageDraw.Draw(img)
    hy = head - 236                          # шапка как у matchday_vs, сдвинута вниз на сторис
    mv._brand(d, W / 2 * S, (hy + 50) * S, brand, 26, acc)
    mv._txt(d, W / 2 * S, (hy + 124) * S, title, mv._fit_w(title, ALU, 900, 80 * S, (W - 2 * MX) * S), (245, 245, 245))
    if date_title:
        mv._spaced(d, W / 2 * S, (hy + 196) * S, date_title.upper(), mv._cap(OSW, 600, 21 * S), acc, 3 * S)
    g = mv._geom(R)
    F = dict(ab=mv._cap(ALU, 900, g['ab'] * S), tm=mv._cap(OSW, 700, min(46, R * 0.2) * S),
             ph=min(60, max(40, R * 0.26)))
    F['bet'] = mv._cap(MAN, 800, F['ph'] * 0.36 * S)
    F['kef'] = mv._cap(OSW, 700, F['ph'] * 0.50 * S)
    boxes = [(top + i * (R + mv.GAP), top + i * (R + mv.GAP) + R) for i in range(n)]
    for i, it in enumerate(legs):
        if not hide:
            _leg(img, it, top + i * (R + mv.GAP), R, acc, i, F)
    # итог: общий кэф и шанс по модели
    d = ImageDraw.Draw(img)
    y = top + n * (R + mv.GAP) - mv.GAP + 40
    boxes.append((y, y + tot_h))
    if hide:
        cols = []
    else:
        d.rounded_rectangle((MX * S, y * S, (W - MX) * S, (y + tot_h) * S), radius=int(22 * S),
                            fill=mv._over((255, 255, 255), 0.05), outline=mv._over(acc, 0.55), width=max(2, int(2 * S)))
        cols = [('ОБЩИЙ КЭФ', _k(total) if total else '—')]
    if chance is not None and not hide:
        cols.append(('ШАНС ПО МОДЕЛИ', '%d %%' % round(chance * 100)))
    lab = mv._cap(MAN, 800, (16 if story else 14) * S)
    big = mv._cap(OSW, 700, (84 if story else 70) * S)
    cw = (W - 2 * MX) / max(1, len(cols))
    for j, (l, v) in enumerate(cols):
        cx = MX + cw * (j + 0.5)
        mv._spaced(d, cx * S, (y + tot_h * 0.27) * S, l, lab, mv.GREY, 2 * S)
        mv._txt(d, cx * S, (y + tot_h * 0.64) * S, v, big, acc if j == 0 else (245, 245, 245))
    if len(cols) > 1:
        d.line(((W / 2) * S, (y + 30) * S, (W / 2) * S, (y + tot_h - 30) * S), fill=mv._over(acc, 0.35), width=int(2 * S))
    if story and cta:
        cy = H - foot + 70
        f = mv._cap(MAN, 800, 26 * S)
        tw = f.getlength(cta) / S
        d.rounded_rectangle(((W / 2 - tw / 2 - 34) * S, (cy - 42) * S, (W / 2 + tw / 2 + 34) * S, (cy + 42) * S),
                            radius=int(42 * S), fill=acc)
        mv._txt(d, W / 2 * S, cy * S, cta, f, mv.INK + (255,))
    note = 'ВРЕМЯ МОСКОВСКОЕ'
    fy = H - (foot - 104) - 66 if not story else H - 150
    mv._spaced(d, W / 2 * S, fy * S, note, mv._cap(MAN, 700, 10 * S), mv.GREY, 1.2 * S)
    mv._spaced(d, W / 2 * S, (fy + 34) * S, '@jarvibet', mv._cap(OSW, 600, 19 * S), acc, 2 * S)
    out = quality.texture(img, 2).convert('RGB')
    if out.width != W:                                   # Telegram и Instagram — ровно 1080 в ширину
        from PIL import Image
        out = out.resize((W, round(out.height * W / out.width)), Image.LANCZOS)
    return out, boxes


def animate(legs, path, dur=4.6, fps=30, **kw):
    """MP4 (H.264, без звука) ≤ 5 с: на пустом купоне по очереди выезжают ноги (сдвиг вбок + проявление), затем блок
    общего кэфа; последние ~1,6 с — статичный кадр. Telegram показывает как гифку (type animation)."""
    import subprocess
    import numpy as np
    base, boxes = draw(legs, hide=True, **kw)
    full, _ = draw(legs, **kw)
    B, Fa = np.asarray(base, np.float32), np.asarray(full, np.float32)
    Hh = B.shape[0]
    starts = [0.25 + 0.45 * i for i in range(len(boxes))]
    starts[-1] += 0.15                                     # итог — с паузой после последней ноги
    span = 0.5
    proc = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                             '-s', '%dx%d' % (W, Hh), '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                             '-crf', '20', '-preset', 'medium', '-movflags', '+faststart', path], stdin=subprocess.PIPE)
    for f in range(int(dur * fps)):
        t = f / fps
        fr = B.copy()
        for (y0, y1), st in zip(boxes, starts):
            a = min(1.0, max(0.0, (t - st) / span))
            if a <= 0:
                continue
            e = 1 - (1 - a) ** 3                           # ease-out
            dx = int(round((1 - e) * 90))
            y0, y1 = max(0, int(y0) - 4), min(Hh, int(y1) + 4)
            src = np.roll(Fa[y0:y1], dx, axis=1)
            if dx:
                src[:, :dx] = B[y0:y1, :dx]
            fr[y0:y1] = B[y0:y1] * (1 - e) + src * e
        proc.stdin.write(fr.clip(0, 255).astype(np.uint8).tobytes())
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError('ffmpeg: не собрал %s' % path)
    return path
