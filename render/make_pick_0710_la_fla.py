"""Послематчевый баннер: Лос-Анджелес — Флорида (НХЛ, ночь на 7 октября), тотал меньше 4,5 за 1.87 — зашёл.

Счёт 1:2 — от владельца канала. Было ли ОТ, не проверено (после двух периодов 1:1), поэтому без приписки про время (mark=None);
ставка зашла в любом случае: в матче всего 3 гола.
Запуск из папки render: python make_pick_0710_la_fla.py → out/0710/pick_losangeles_florida.jpg
"""
import os

import ice_more2 as im2
import nhl

nhl.register()

os.makedirs('out/0710', exist_ok=True)
m = dict(home='Лос-Анджелес', away='Флорида', sh=1, sa=2, mark=None, date='среда, 7 октября', tag='НХЛ', pick=dict(
    text='ТОТАЛ МАТЧА МЕНЬШЕ 4,5', odds=1.87, hit=True,
    checks=[('1:2 — ВСЕГО 3 ГОЛА В МАТЧЕ', True)]))
print(im2.single(m, 'out/0710/pick_losangeles_florida.jpg', style='verdict', league='NHL'))
