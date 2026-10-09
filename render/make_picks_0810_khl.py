"""Послематчевые баннеры к прогнозам КХЛ 8 октября (ice_more2, style='verdict').

Счёт — из таблицы КХЛ (лист «результаты матчей», все три в основное время), сверено с «Спорт-Экспрессом» и Allhockey:
Нефтехимик — Авангард 0:1, Динамо Минск — СКА 4:2, Трактор — Амур 0:2. Кэфы владелец канала не прислал — карточки без кэфа.
Запуск из папки render: python make_picks_0810_khl.py → out/0810/pick_*.jpg
"""
import os

import ice_more2 as im2

OUT = 'out/0810'
BANNERS = [
    ('neftekhimik_avangard', dict(home='Нефтехимик', away='Авангард', sh=0, sa=1, mark='', pick=dict(
        text='ПОБЕДА НЕФТЕХИМИКА', hit=False,
        checks=[('АВАНГАРД ВЫИГРАЛ 1:0', False)]))),
    ('minsk_ska', dict(home='Динамо Минск', away='СКА', sh=4, sa=2, mark='', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 5,5', hit=True,
        checks=[('4:2 — 6 ГОЛОВ В МАТЧЕ', True)]))),
    ('traktor_amur', dict(home='Трактор', away='Амур', sh=0, sa=2, mark='', pick=dict(
        text='ТОТАЛ МАТЧА МЕНЬШЕ 4,5', hit=True,
        checks=[('0:2 — ВСЕГО 2 ГОЛА В МАТЧЕ', True)]))),
]

os.makedirs(OUT, exist_ok=True)
for name, m in BANNERS:
    m.update(date='четверг, 8 октября', tag='КХЛ')
    path = '%s/pick_%s.jpg' % (OUT, name)
    im2.single(m, path, style='verdict', league='KHL')
    print(path)
