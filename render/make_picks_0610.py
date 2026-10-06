"""Послематчевые баннеры к прогнозам НХЛ в ночь на 6 октября (ice_more2, style='verdict').

Счёт — от владельца канала; Питтсбург — Виннипег 2:3 в основное время (протокол CBS Sports).
Даллас — Сан-Хосе 5:0: тотал больше 5 — ровно 5 голов, возврат.
Запуск из папки render: python make_picks_0610.py → out/0610/pick_*.jpg
"""
import os

import ice_more2 as im2
import nhl

nhl.register()

OUT = 'out/0610'
NIGHT = 'вторник, 6 октября'

BANNERS = [
    ('tampa_philadelphia', dict(home='Тампа-Бэй', away='Филадельфия', sh=3, sa=1, mark='', pick=dict(
        text='ПОБЕДА ТАМПЫ В ОСНОВНОЕ ВРЕМЯ', odds=1.78, hit=True,
        checks=[('ТАМПА-БЭЙ ВЫИГРАЛА 3:1 В ОСНОВНОЕ ВРЕМЯ', True)]))),
    ('dallas_sanjose', dict(home='Даллас', away='Сан-Хосе', sh=5, sa=0, mark='', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 5', hit=None,
        checks=[('5:0 — РОВНО 5 ГОЛОВ, СТАВКА ВОЗВРАЩАЕТСЯ', None)]))),
    ('pittsburgh_winnipeg', dict(home='Питтсбург', away='Виннипег', sh=2, sa=3, mark='', pick=dict(
        text='ПОБЕДА ПИТТСБУРГА', hit=False,
        checks=[('ВИННИПЕГ ВЫИГРАЛ 3:2 В ОСНОВНОЕ ВРЕМЯ', False)]))),
]

os.makedirs(OUT, exist_ok=True)
for name, m in BANNERS:
    m.update(date=NIGHT, tag='НХЛ')
    path = '%s/pick_%s.jpg' % (OUT, name)
    im2.single(m, path, style='verdict', league='NHL')
    print(path)
