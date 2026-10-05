"""Двойной прогноз КХЛ на 5 октября (recap.render_picks, как «ДВОЙНОЙ ПРОГНОЗ» 28.09).

Ак Барс — Локомотив: фора (0) Локомотива; ЦСКА — Салават Юлаев: фора (0) ЦСКА в 1-м периоде. Вместе экспрессом 2.10
(кэфы по отдельности не названы — на карточках их нет).
Запуск из папки render: python make_double_0510_khl.py → out/0510/double_0510.jpg
"""
import os

from PIL import Image

from recap import render_picks

OUT = 'out/0510'
ITEMS = [
    dict(home='Ак Барс', away='Локомотив', pred='ЛОКОМОТИВ ФОРА (0)', coef=None, when='19:30'),
    dict(home='ЦСКА', away='Салават Юлаев', pred='ЦСКА ФОРА (0) В 1-М ПЕРИОДЕ', coef=None, when='19:30'),
]

os.makedirs(OUT, exist_ok=True)
p = render_picks(ITEMS, OUT + '/double_0510.png', 'понедельник, 5 октября', express=2.10, title='ДВОЙНОЙ ПРОГНОЗ')
Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
os.remove(p)
print(p.replace('.png', '.jpg'))
