"""Послематчевые баннеры к прогнозам НХЛ: Детройт — Виннипег (4 октября, 20:00) и ночь на 5 октября (ice_more2, style='verdict').

Счёт — из «Итогов дня» НХЛ (таблица, данные НХЛ). Тотал больше 5 — Детройт — Виннипег: ровно 5 голов в основное время, возврат.
Запуск из папки render: python make_picks_0510.py → out/0510/pick_*.jpg
"""
import os

import ice_more2 as im2
import nhl

nhl.register()

OUT = 'out/0510'
NIGHT = 'понедельник, 5 октября'

BANNERS = [
    ('seattle_calgary', dict(home='Сиэтл', away='Калгари', sh=6, sa=1, mark='', date=NIGHT, pick=dict(
        text='ИНДИВИДУАЛЬНЫЙ ТОТАЛ СИЭТЛА БОЛЬШЕ 2,5', odds=1.68, hit=True,
        checks=[('СИЭТЛ ЗАБИЛ 6 ГОЛОВ', True)]))),
    ('vancouver_vegas', dict(home='Ванкувер', away='Вегас', sh=2, sa=3, mark='', date=NIGHT, pick=dict(
        text='ПОБЕДА ВЕГАСА', odds=1.68, hit=True,
        checks=[('ВЕГАС ВЫИГРАЛ 3:2 В ОСНОВНОЕ ВРЕМЯ', True)]))),
    ('rangers_utah', dict(home='Рейнджерс', away='Юта', sh=4, sa=2, mark='', date=NIGHT, pick=dict(
        text='ИТОГОВАЯ ПОБЕДА РЕЙНДЖЕРС', odds=1.88, hit=True,
        checks=[('РЕЙНДЖЕРС ВЫИГРАЛИ 4:2', True)]))),
    ('detroit_winnipeg', dict(home='Детройт', away='Виннипег', sh=2, sa=3, mark='', date='воскресенье, 4 октября', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 5', odds=1.68, hit=None,
        checks=[('2:3 — РОВНО 5 ГОЛОВ, СТАВКА ВОЗВРАЩАЕТСЯ', None)]))),
]

os.makedirs(OUT, exist_ok=True)
for name, m in BANNERS:
    m['tag'] = 'НХЛ'
    path = '%s/pick_%s.jpg' % (OUT, name)
    im2.single(m, path, style='verdict', league='NHL')
    print(path)
