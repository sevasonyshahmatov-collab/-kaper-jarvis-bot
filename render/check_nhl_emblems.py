# -*- coding: utf-8 -*-
"""Контрольный лист: все 32 эмблемы НХЛ на тёмном фоне — видно, у кого
остался белый прямоугольник, кто потерялся на фоне, кто криво обрезан."""
import os

from PIL import Image, ImageDraw

import nhl
import poster

nhl.register()
os.makedirs('out/nhl_demo', exist_ok=True)

teams = sorted(nhl.TEAMS, key=lambda t: (nhl.TEAMS[t][5], t))
COLS, CELL, PAD = 8, 200, 16
rows = (len(teams) + COLS - 1) // COLS
W, H = COLS * CELL, rows * CELL + 60
img = Image.new('RGB', (W, H), (16, 22, 36))
d = ImageDraw.Draw(img)
d.text((PAD, 18), 'ЭМБЛЕМЫ НХЛ — 32 КЛУБА', font=poster._f7('brand', 22), fill=(255, 255, 255))

for i, t in enumerate(teams):
    cx = (i % COLS) * CELL + CELL // 2
    cy = 60 + (i // COLS) * CELL + CELL // 2 - 12
    e = poster._raw_emblem(t, CELL - 60, CELL - 70)
    img.paste(e, (cx - e.width // 2, cy - e.height // 2), e)
    lab = nhl.TEAMS[t][3]
    d.text((cx, cy + CELL // 2 - 26), lab, font=poster._f7('info', 13),
           fill=(190, 200, 216), anchor='mm')

img.save('out/nhl_demo/00_emblems.jpg', quality=94, subsampling=0)
print('готово out/nhl_demo/00_emblems.jpg  —', len(teams), 'клубов')
