"""Послематчевые баннеры к прогнозам (ice_more2, style='verdict'): КХЛ 7 октября и НХЛ в ночь на 8 октября.

Счёт — из таблиц КХЛ и НХЛ (лист «результаты матчей», все четыре матча в основное время), сверено с отчётами:
НХЛ — NHL.com, ESPN, Yahoo: Вашингтон — Питтсбург 5:3, Виннипег — Колорадо 3:2 (победный гол Коннора на последней минуте),
Анахайм — Эдмонтон 2:5; КХЛ — «Спорт-Экспресс», Sports.ru: Динамо Москва — Шанхайские Драконы 2:3.
Кэфы владелец канала не прислал — карточки без кэфа, как у Юты 7 октября.
Запуск из папки render: python make_picks_0810.py → out/0710/pick_*.jpg (КХЛ), out/0810/pick_*.jpg (НХЛ)
"""
import os

import ice_more2 as im2
import nhl

nhl.register()

KHL = ('0710', 'среда, 7 октября', 'КХЛ', 'KHL', [
    ('dinamo_shanghai', dict(home='Динамо Москва', away='Шанхайские Драконы', sh=2, sa=3, mark='', pick=dict(
        text='ШАНХАЙ Х2 В ОСНОВНОЕ ВРЕМЯ', hit=True,
        checks=[('ШАНХАЙ ВЫИГРАЛ 3:2 В ОСНОВНОЕ ВРЕМЯ', True)]))),
])
NHL = ('0810', 'четверг, 8 октября', 'НХЛ', 'NHL', [
    ('washington_pittsburgh', dict(home='Вашингтон', away='Питтсбург', sh=5, sa=3, mark='', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 5,5', hit=True,
        checks=[('5:3 — 8 ГОЛОВ В МАТЧЕ', True)]))),
    ('winnipeg_colorado', dict(home='Виннипег', away='Колорадо', sh=3, sa=2, mark='', pick=dict(
        text='ПОБЕДА КОЛОРАДО В МАТЧЕ', hit=False,
        checks=[('ВИННИПЕГ ВЫИГРАЛ 3:2 НА ПОСЛЕДНЕЙ МИНУТЕ', False)]))),
    ('anaheim_edmonton', dict(home='Анахайм', away='Эдмонтон', sh=2, sa=5, mark='', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 6', hit=True,
        checks=[('2:5 — 7 ГОЛОВ В МАТЧЕ', True)]))),
])

for day, date, tag, league, banners in (KHL, NHL):
    out = 'out/' + day
    os.makedirs(out, exist_ok=True)
    for name, m in banners:
        m.update(date=date, tag=tag)
        path = '%s/pick_%s.jpg' % (out, name)
        im2.single(m, path, style='verdict', league=league)
        print(path)
