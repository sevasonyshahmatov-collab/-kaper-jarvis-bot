# -*- coding: utf-8 -*-
"""Цифра дня 12.10 — баннер «Чертёж» (синька) 3840x1920: «6» как размерная величина.
Запуск из корня репозитория: PYTHONPATH=render python team/out/2026-10-12/make.py"""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'render'))
import banners_new as B  # noqa: E402
from banners_new import C, T, paper, vignette, lineart, _arrow, save, LW, LH  # noqa: E402

OUT = os.path.join(ROOT, 'team', 'out', '2026-10-12', 'cifra_1210.jpg')


def cifra(path):
    W, H = LW, LH
    dyn, ska = C.match('Динамо Москва', 'СКА', 'KHL')
    im = paper(W, H, (24, 66, 142), seed=101, k=0.9, fibers=0)
    S = 2
    lay = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    g1, g2 = (190, 214, 255, 34), (190, 214, 255, 70)
    for x in range(0, W, 48):
        d.line((x * S, 0, x * S, H * S), fill=g2 if x % 240 == 0 else g1, width=2 if x % 240 else 3)
    for y in range(0, H, 48):
        d.line((0, y * S, W * S, y * S), fill=g2 if y % 240 == 0 else g1, width=2 if y % 240 else 3)
    ink = (236, 244, 255, 255)
    inkc = ink[:3]
    P = lambda x, y: (x * S, y * S)  # noqa: E731

    # рамка листа
    d.rectangle((*P(90, 90), *P(W - 90, H - 90)), outline=ink, width=8 * S)
    d.rectangle((*P(120, 120), *P(W - 120, H - 120)), outline=ink, width=2 * S)

    # шапка: линия и надписи
    d.line((*P(120, 330), *P(W - 120, 330)), fill=ink, width=4 * S)

    # «6» — размерная величина
    digit = T('6', 'kelly', 1180, inkc, 400, trim=True)
    dcx, dcy = 880, 880
    dx0, dx1 = dcx - digit.width / 2, dcx + digit.width / 2
    dy0, dy1 = dcy - digit.height / 2, dcy + digit.height / 2
    # выносные и размерные линии: вертикаль слева, горизонталь снизу
    vx = dx0 - 150
    hy = dy1 + 110
    for yy in (dy0, dy1):
        d.line((*P(dx0 - 40, yy), *P(vx - 40, yy)), fill=ink, width=2 * S)
    for xx in (dx0, dx1):
        d.line((*P(xx, dy1 + 30), *P(xx, hy + 40)), fill=ink, width=2 * S)
    lab_v = T('6', 'kelly', 110, inkc, 400, trim=True)
    my, gl = dcy, lab_v.height / 2 + 40
    _arrow(d, vx * S, dy0 * S, vx * S, (my - gl) * S, ink, 3 * S, 36 * S, ends=(1, 0))
    _arrow(d, vx * S, (my + gl) * S, vx * S, dy1 * S, ink, 3 * S, 36 * S, ends=(0, 1))
    _arrow(d, dx0 * S, hy * S, dx1 * S, hy * S, ink, 3 * S, 36 * S)

    # правая часть: эмблемы линиями, осевая и выноски
    ax0, ax1 = 1960, W - 220
    d.line((*P(1800, 330), *P(1800, H - 120)), fill=ink, width=2 * S)
    ey = 800
    lay = lay.resize((W, H), Image.LANCZOS)
    im.alpha_composite(lay)
    dd = ImageDraw.Draw(im)

    C.put(im, digit, dcx, dcy)
    C.put(im, lab_v.rotate(90, Image.BICUBIC, expand=True), vx, my)

    # подпись под цифрой
    cap = T('ПОРАЖЕНИЙ ПОДРЯД — СЕРИЯ ПРЕРВАНА', 'kelly', 70, inkc, 400, trim=True)
    assert cap.width < 1560, cap.width
    C.put(im, cap, dcx, hy + 120)

    # эмблемы
    cxs = (2420, 3200)
    for t_, cx, nm in ((dyn, cxs[0], 'ДИНАМО'), (ska, cxs[1], 'СКА')):
        e = t_.emb(620)
        C.put(im, lineart(e, inkc, 0.95), cx, ey)
        lt = T(nm, 'kelly', 88, inkc, 400, trim=True)
        C.put(im, lt, cx, ey + 400)
        dd.line((cx - 250, ey + 330, cx + 250, ey + 330), fill=inkc, width=3)
    C.put(im, T('—', 'kelly', 150, inkc, 400, trim=True), (cxs[0] + cxs[1]) / 2, ey)

    # строка матча в рамке
    sc = T('ДИНАМО — СКА 4:3 ОТ · 11.10', 'kelly', 100, inkc, 400, trim=True, max_w=1900)
    bx0, bx1 = 1900, W - 150
    by0, by1 = 1370, 1500
    dd.rectangle((bx0 + 20, by0, bx1 - 20, by1), outline=inkc, width=5)
    C.put(im, sc, (bx0 + bx1) / 2, (by0 + by1) / 2)

    # шапка
    C.put(im, T('JARVIS | KXL', 'kelly', 96, inkc, 400), 190, 150, anchor='tl')
    ttl = T('ЦИФРА ДНЯ', 'kelly', 170, inkc, 400, trim=True)
    C.put(im, ttl, W - 190 - ttl.width / 2, 215)

    # низ: штамп-подпись и хэндл
    C.put(im, T('ЧЕРТЁЖ JRV-KHL-1110', 'kelly', 56, inkc, 400), 190, H - 190, anchor='tl')
    hd = T(B.HANDLE, 'mono', 64, inkc, 500)
    C.put(im, hd, W - 190 - hd.width / 2, H - 165)
    return save(vignette(im, 0.4, 2.2), path)


if __name__ == '__main__':
    print(cifra(OUT))
    prev = os.environ.get('PREVIEW')
    if prev:
        Image.open(OUT).resize((1280, 640), Image.LANCZOS).save(prev)
