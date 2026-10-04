"""Послематчевые баннеры к прогнозам КХЛ 4 октября (ice_more2, style='verdict').

Ставки рассчитаны по основному времени: Спартак — Барыс 3:4 Б → 3:3.
Запуск из папки render: python make_picks_0410.py → out/0410/pick_*.jpg
"""
import os

import ice_more2 as im2

OUT = 'out/0410'
DAY = 'воскресенье, 4 октября'

BANNERS = [
    ('neftekhimik_sibir', dict(home='Нефтехимик', away='Сибирь', sh=3, sa=2, mark='', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 5', hit=None,
        checks=[('3:2 — РОВНО 5 ГОЛОВ, СТАВКА ВОЗВРАЩАЕТСЯ', None)]))),
    ('spartak_barys', dict(home='Спартак', away='Барыс', sh=3, sa=4, mark='Б', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 5,5', odds=1.98, hit=True,
        checks=[('ОСНОВНОЕ ВРЕМЯ 3:3 — 6 ГОЛОВ', True)]))),
]

os.makedirs(OUT, exist_ok=True)
for name, m in BANNERS:
    m.update(date=DAY, tag='КХЛ')
    path = '%s/pick_%s.jpg' % (OUT, name)
    im2.single(m, path, style='verdict', league='KHL')
    print(path)
