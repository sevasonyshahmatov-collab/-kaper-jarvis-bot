"""Эмблемы клубов для сайта v3a: render/emblems/<клуб>.png → team/site/v3a/assets/em/<клуб>.webp.

Владелец 11.11: эмблемы высокого качества и строго по центру. Каждая эмблема обрезается по прозрачности и ставится
в центр квадрата SIDE × SIDE с одинаковым полем, без подложки и обводки. Исходник меньше нужного размера не растягиваем
сильнее, чем в UP раз (мыло) — такие клубы печатаем в отчёте: им нужен исходник крупнее (render/emblems).
Запуск: python3 team/site/emblems_build.py
Уменьшенные копии (список 13.11, п. 7): assets/em/s/ — 128 px из готовых 384 px, для мест, где эмблема
показывается не крупнее 64 px (таблицы, списки, оборот карточки лиги): ~7 КБ вместо ~30 КБ, на телефоне так же чётко.
Делаются в конце каждого запуска; только они — python3 team/site/emblems_build.py --small. Нет копии — nav.js берёт полную.
"""
import glob
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'render', 'emblems')
DST = os.path.join(ROOT, 'team', 'site', 'v3a', 'assets', 'em')
SIDE, PAD, UP = 384, 0.04, 2.0


def build(path):
    im = Image.open(path).convert('RGBA')
    box = im.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox()
    if box:
        im = im.crop(box)
    inner = SIDE * (1 - 2 * PAD)
    k = min(inner / im.width, inner / im.height)
    small = k > 1.0
    k = min(k, UP)
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    out = Image.new('RGBA', (SIDE, SIDE), (0, 0, 0, 0))
    out.alpha_composite(im, ((SIDE - im.width) // 2, (SIDE - im.height) // 2))
    return out, small, box


SMALL = 128


def build_small():
    n = 0
    for sub in ('em',):   # fc/ (футбол) — уже 192 px и ~10 КБ, копии не нужны
        src = os.path.join(os.path.dirname(DST), sub)
        dst = os.path.join(src, 's')
        os.makedirs(dst, exist_ok=True)
        have = set()
        for p in sorted(glob.glob(os.path.join(src, '*.webp'))):
            name = os.path.basename(p)
            have.add(name)
            out = os.path.join(dst, name)
            if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(p):
                continue
            Image.open(p).convert('RGBA').resize((SMALL, SMALL), Image.LANCZOS).save(out, 'WEBP', quality=92, method=6, exact=True)
            n += 1
        for p in glob.glob(os.path.join(dst, '*.webp')):      # копии эмблем, которых больше нет
            if os.path.basename(p) not in have:
                os.remove(p)
    print('уменьшенные копии %d px: обновлено %d' % (SMALL, n))


def main():
    low = []
    for p in sorted(glob.glob(os.path.join(SRC, '*.png'))):
        name = os.path.splitext(os.path.basename(p))[0]
        out, small, _ = build(p)
        out.save(os.path.join(DST, name + '.webp'), 'WEBP', quality=92, method=6, exact=True)
        if small:
            w, h = Image.open(p).size
            low.append('%s %dx%d' % (name, w, h))
    print('готово: %d эмблем, %d px' % (len(glob.glob(os.path.join(DST, '*.webp'))), SIDE))
    print('исходник мельче %d px (нужен крупнее): %s' % (round(SIDE * (1 - 2 * PAD)), ', '.join(low) or 'нет'))


if __name__ == '__main__':
    import sys
    if '--small' not in sys.argv:
        main()
    build_small()
