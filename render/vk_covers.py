# -*- coding: utf-8 -*-
"""Обложки клипов VK (владелец 19.10): 1080×1920, оформление «Гроза» как у канала — грозовое небо, молния, свечение
цветов клубов, эмблемы, «ПРОГНОЗ НА МАТЧ», лига, дата и время МСК. Сам прогноз на обложке не пишем — он в ролике.
Всё важное — в середине кадра (сетка клипов VK обрезает края).

    PYTHONPATH=render python render/vk_covers.py <папка> <json со списком матчей>
    матч: {"league": "KHL", "h": "Адмирал", "a": "Салават Юлаев", "d": "2026-10-19 12:30"}
"""
import json
import os
import sys
from datetime import date

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reels import core as C  # noqa: E402
import youtube_brand as Y  # noqa: E402

W, H = 1080, 1920
WEEK = ('ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС')


def sky(seed):
    n = Y.noise(W, H, 260, seed, 4) ** 1.5
    bolt = Y._bolt_light(W, H, seed + 40, W * 0.84, -30, W * 0.62, H * 0.62)
    bolt2 = Y._bolt_light(W, H, seed + 7, W * 0.1, -30, W * 0.22, H * 0.4) * 0.5
    lum = 6 + n * 64 + bolt * 0.7 + bolt2 * 0.7
    arr = np.clip(np.stack([lum, lum, lum * 1.03], -1), 0, 255)
    return Image.fromarray(arr.astype(np.uint8), 'RGB').convert('RGBA')


def cover(m, seed=3):
    h, a = C.match(m['h'], m['a'], m['league'])
    img = sky(seed)
    for t, y in ((h, 560), (a, 1300)):                                   # свечение цветов клубов за эмблемами
        C.put(img, C.radial(900, 700, t.c1, 120, 1.4), W / 2, y)
    img = C.vignette(img, 0.45, 2.0).convert('RGBA')
    for y in (250, 800, 1420):                                           # тёмная подложка под текстом — молния не спорит с надписью
        C.put(img, C.radial(1000, 200, (0, 0, 0), 200, 1.2), W / 2, y)
    d = date.fromisoformat(m['d'][:10])
    lg = 'КХЛ' if m['league'].upper() == 'KHL' else 'НХЛ'
    C.put(img, C.text('%s · %s %s · %s МСК' % (lg, WEEK[d.weekday()], d.strftime('%d.%m'), m['d'][11:16]), 'mont', 40,
                      (220, 222, 230), 800, track=0.12, max_w=W - 120), W / 2, 250)
    C.put(img, C.glow(h.emb(380), 30, 0.6, h.c1), W / 2, 560)
    C.put(img, C.text(h.up, 'unb', 64, (246, 246, 250), 800, max_w=W - 120), W / 2, 800)
    C.put(img, C.text('—', 'mont', 60, (200, 202, 210), 700), W / 2, 905)
    C.put(img, C.glow(a.emb(380), 30, 0.6, a.c1), W / 2, 1180)
    C.put(img, C.text(a.up, 'unb', 64, (246, 246, 250), 800, max_w=W - 120), W / 2, 1420)
    C.put(img, C.radial(1000, 260, (0, 0, 0), 190, 1.2), W / 2, 1600)
    C.put(img, C.glow(C.text('ПРОГНОЗ НА МАТЧ', 'unb', 66, (255, 214, 92), 800, max_w=W - 100), 16, 0.6, (255, 190, 60)),
          W / 2, 1585)
    C.put(img, C.text('JARVIS', 'unb', 34, (200, 202, 210), 800, track=0.3), W / 2, 1700)
    return img.convert('RGB')


def main():
    out, src = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for i, m in enumerate(json.load(open(src, encoding='utf-8'))):
        p = os.path.join(out, '%02d_%s_%s.jpg' % (i + 1, m['league'].lower(), C.match(m['h'], m['a'], m['league'])[0].short))
        cover(m, seed=3 + i).save(p, quality=92)
        print(p, flush=True)


if __name__ == '__main__':
    main()
