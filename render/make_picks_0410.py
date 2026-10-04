"""Послематчевый баннер к прогнозу: Нефтехимик — Сибирь 4 октября, тотал больше 5 — возврат (ровно 5 голов, 3:2 в основное время).

Запуск из папки render: python make_picks_0410.py → out/0410/pick_neftekhimik_sibir.jpg
"""
import os

import ice_more2 as im2

OUT = 'out/0410'
os.makedirs(OUT, exist_ok=True)
m = dict(home='Нефтехимик', away='Сибирь', sh=3, sa=2, mark='', date='воскресенье, 4 октября', tag='КХЛ', pick=dict(
    text='ТОТАЛ МАТЧА БОЛЬШЕ 5', hit=None,
    checks=[('3:2 — РОВНО 5 ГОЛОВ, СТАВКА ВОЗВРАЩАЕТСЯ', None)]))
path = OUT + '/pick_neftekhimik_sibir.jpg'
im2.single(m, path, style='verdict', league='KHL')
print(path)
