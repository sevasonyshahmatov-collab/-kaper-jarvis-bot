"""Двойной прогноз КХЛ на 5 октября.

Ак Барс — Локомотив и ЦСКА — Салават Юлаев, 19:30: фора (0) Локомотива и фора (0) ЦСКА — обе в 1-м периоде. Экспресс 2.10.
Два шаблона: ice_more2.express (полосы-«Бока», основной) и прежний recap.render_picks («ДВОЙНОЙ ПРОГНОЗ» как 28.09).
Запуск из папки render: python make_double_0510_khl.py → out/0510/double_0510.jpg (+ double_0510_list.jpg)
"""
import os

from PIL import Image

import ice_more2 as im2
from recap import render_picks

OUT = 'out/0510'
DAY = 'понедельник, 5 октября'
ODDS = 2.10
ITEMS = [
    dict(home='Ак Барс', away='Локомотив', time='19:30', pick='Локомотив', text='ФОРА (0) В 1-М ПЕРИОДЕ'),
    dict(home='ЦСКА', away='Салават Юлаев', time='19:30', pick='ЦСКА', text='ФОРА (0) В 1-М ПЕРИОДЕ'),
]

os.makedirs(OUT, exist_ok=True)
p = im2.express(ITEMS, OUT + '/double_0510.jpg', league='KHL', date_title=DAY, odds=ODDS)
print(p)
old = [dict(home=i['home'], away=i['away'], pred=i['pick'].upper() + ' ФОРА (0) В 1-М ПЕРИОДЕ', coef=None, when=i['time']) for i in ITEMS]
p = render_picks(old, OUT + '/double_0510_list.png', DAY, express=ODDS, title='ДВОЙНОЙ ПРОГНОЗ')
Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
os.remove(p)
print(p.replace('.png', '.jpg'))
