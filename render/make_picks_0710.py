"""Послематчевые баннеры к прогнозам (ice_more2, style='verdict'): КХЛ 6 октября и НХЛ в ночь на 7 октября.

КХЛ — счёт из таблицы (Трактор — Амур 1:2, СКА — Северсталь 2:5, оба в основное время).
НХЛ — по отчётам NHL.com, ESPN, TSN, Yahoo: Баффало — Миннесота 3:2 ОТ (основное время 2:2), Монреаль — Каролина 4:6,
Нью-Джерси — Юта 3:5, Рейнджерс — Айлендерс 5:2. Ставки — по основному времени.
Запуск из папки render: python make_picks_0710.py → out/0610/pick_*.jpg (КХЛ), out/0710/pick_*.jpg (НХЛ)
"""
import os

import ice_more2 as im2
import nhl

nhl.register()

KHL = ('0610', 'вторник, 6 октября', 'КХЛ', 'KHL', [
    ('traktor_amur', dict(home='Трактор', away='Амур', sh=1, sa=2, mark='', pick=dict(
        text='ТОТАЛ МАТЧА МЕНЬШЕ 5,5', odds=1.78, hit=True,
        checks=[('1:2 — 3 ГОЛА В МАТЧЕ', True)]))),
    ('ska_severstal', dict(home='СКА', away='Северсталь', sh=2, sa=5, mark='', pick=dict(
        text='ФОРА СКА (−1)', odds=2.01, hit=False,
        checks=[('СЕВЕРСТАЛЬ ВЫИГРАЛА 5:2', False)]))),
])
NHL = ('0710', 'среда, 7 октября', 'НХЛ', 'NHL', [
    ('buffalo_minnesota', dict(home='Баффало', away='Миннесота', sh=3, sa=2, mark='ОТ', pick=dict(
        text='ТОТАЛ МАТЧА МЕНЬШЕ 6,5', odds=1.67, hit=True,
        checks=[('ОСНОВНОЕ ВРЕМЯ 2:2 — 4 ГОЛА', True)]))),
    ('montreal_carolina', dict(home='Монреаль', away='Каролина', sh=4, sa=6, mark='', pick=dict(
        text='ТОТАЛ МАТЧА МЕНЬШЕ 6,5', odds=1.59, hit=False,
        checks=[('4:6 — 10 ГОЛОВ В МАТЧЕ', False)]))),
    ('newjersey_utah', dict(home='Нью-Джерси', away='Юта', sh=3, sa=5, mark='', pick=dict(
        text='ИНДИВИДУАЛЬНЫЙ ТОТАЛ ЮТЫ БОЛЬШЕ 2,5', hit=True,
        checks=[('ЮТА ЗАБИЛА 5 ГОЛОВ', True)]))),
    ('rangers_islanders', dict(home='Рейнджерс', away='Айлендерс', sh=5, sa=2, mark='', pick=dict(
        text='ПОБЕДА РЕЙНДЖЕРС', odds=2.10, hit=True,
        checks=[('РЕЙНДЖЕРС ВЫИГРАЛИ 5:2', True)]))),
])

for day, date, tag, league, banners in (KHL, NHL):
    out = 'out/' + day
    os.makedirs(out, exist_ok=True)
    for name, m in banners:
        m.update(date=date, tag=tag)
        path = '%s/pick_%s.jpg' % (out, name)
        im2.single(m, path, style='verdict', league=league)
        print(path)
