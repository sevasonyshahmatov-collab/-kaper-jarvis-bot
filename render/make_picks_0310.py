"""Послематчевые баннеры к прогнозам: КХЛ 3 октября и ночь НХЛ на 4 октября (ice_more2, style='verdict').

Ставки рассчитаны по основному времени: КХЛ 4:3 Б → 3:3, 2:1 ОТ → 1:1; НХЛ 5:4 ОТ → 4:4.
Запуск из папки render: python make_picks_0310.py → out/0310/*.jpg
"""
import os

import ice_more2 as im2
import nhl

nhl.register()                      # эмблемы и цвета клубов НХЛ

OUT = 'out/0310'
KHL_DAY, NHL_DAY = 'суббота, 3 октября', 'воскресенье, 4 октября'

BANNERS = [
    ('KHL', 'cska_dinamo', dict(home='ЦСКА', away='Динамо Москва', sh=4, sa=3, mark='Б', date=KHL_DAY, pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 5,5', hit=True,
        checks=[('ОСНОВНОЕ ВРЕМЯ 3:3 — 6 ГОЛОВ', True)]))),
    ('KHL', 'minsk_lokomotiv', dict(home='Динамо Минск', away='Локомотив', sh=4, sa=3, mark='', date=KHL_DAY, pick=dict(
        text='2Х И ТОТАЛ МЕНЬШЕ 6,5', odds=1.74, hit=False,
        checks=[('2Х: ЛОКОМОТИВ ПРОИГРАЛ В ОСНОВНОЕ ВРЕМЯ', False), ('ТОТАЛ: 7 ГОЛОВ — БОЛЬШЕ 6,5', False)]))),
    ('KHL', 'severstal_shanghai', dict(home='Северсталь', away='Шанхайские Драконы', sh=2, sa=1, mark='ОТ', date=KHL_DAY, pick=dict(
        text='Х2', odds=1.71, hit=True,
        checks=[('ОСНОВНОЕ ВРЕМЯ 1:1 — НИЧЬЯ', True)]))),
    ('NHL', 'sharks_kings', dict(home='Сан-Хосе', away='Лос-Анджелес', sh=5, sa=4, mark='ОТ', date=NHL_DAY, pick=dict(
        text='ТОТАЛ ШАРКС БОЛЬШЕ 3', odds=1.87, hit=True,
        checks=[('ШАРКС: 4 ГОЛА В ОСНОВНОЕ ВРЕМЯ', True)]))),
    ('NHL', 'toronto_ottawa', dict(home='Торонто', away='Оттава', sh=2, sa=3, mark='', date=NHL_DAY, pick=dict(
        text='ТОРОНТО 1Х + ТОТАЛ БОЛЬШЕ 4,5', odds=2.11, hit=False,
        checks=[('1Х: ТОРОНТО ПРОИГРАЛ 2:3', False), ('ТОТАЛ: 5 ГОЛОВ — БОЛЬШЕ 4,5', True)]))),
    ('NHL', 'colorado_stlouis', dict(home='Колорадо', away='Сент-Луис', sh=6, sa=1, mark='', date=NHL_DAY, pick=dict(
        text='ПОБЕДА КОЛОРАДО В ОСНОВНОЕ ВРЕМЯ', odds=1.67, hit=True,
        checks=[('6:1 В ОСНОВНОЕ ВРЕМЯ', True)]))),
]

os.makedirs(OUT, exist_ok=True)
for league, name, m in BANNERS:
    m['tag'] = 'КХЛ' if league == 'KHL' else 'НХЛ'
    path = '%s/%s_%s.jpg' % (OUT, league.lower(), name)
    im2.single(m, path, style='verdict', league=league)
    print(path)
print('готово')
