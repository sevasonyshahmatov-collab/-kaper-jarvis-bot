"""Послематчевые баннеры к прогнозам НХЛ в ночь на 9 октября (ice_more2, style='verdict').

Таблица НХЛ результаты ещё не подтянула — счёт по отчётам NHL.com, ESPN, Yahoo, Washington Post:
Бостон — Юта 6:1, Оттава — Филадельфия 2:1, Айлендерс — Чикаго 4:1, Сент-Луис — Сан-Хосе 2:3 ОТ (осн. время 2:2),
Калгари — Колорадо 3:7, Вегас — Торонто 4:3 Б (осн. время 3:3). Кэфы — из прогнозов владельца канала.
Запуск из папки render: python make_picks_0910.py → out/0910/pick_*.jpg
"""
import os

import ice_more2 as im2
import nhl

nhl.register()

OUT = 'out/0910'
BANNERS = [
    ('boston_utah', dict(home='Бостон', away='Юта', sh=6, sa=1, mark='', pick=dict(
        text='ЮТА НЕ ПРОИГРАЕТ (Х2)', odds=1.61, hit=False,
        checks=[('БОСТОН ВЫИГРАЛ 6:1', False)]))),
    ('ottawa_philadelphia', dict(home='Оттава', away='Филадельфия', sh=2, sa=1, mark='', pick=dict(
        text='ПОБЕДА ОТТАВЫ', odds=2.05, hit=True,
        checks=[('ОТТАВА ВЫИГРАЛА 2:1', True)]))),
    ('islanders_chicago', dict(home='Айлендерс', away='Чикаго', sh=4, sa=1, mark='', pick=dict(
        text='ПОБЕДА АЙЛЕНДЕРС', odds=1.90, hit=True,
        checks=[('АЙЛЕНДЕРС ВЫИГРАЛИ 4:1', True)]))),
    ('stlouis_sanjose', dict(home='Сент-Луис', away='Сан-Хосе', sh=2, sa=3, mark='ОТ', pick=dict(
        text='ИНДИВИДУАЛЬНЫЙ ТОТАЛ СЕНТ-ЛУИСА БОЛЬШЕ 2,5', odds=1.71, hit=False,
        checks=[('СЕНТ-ЛУИС ЗАБИЛ 2 ГОЛА', False)]))),
    ('calgary_colorado', dict(home='Калгари', away='Колорадо', sh=3, sa=7, mark='', pick=dict(
        text='ПОБЕДА КОЛОРАДО', odds=1.76, hit=True,
        checks=[('КОЛОРАДО ВЫИГРАЛ 7:3', True)]))),
    ('vegas_toronto', dict(home='Вегас', away='Торонто', sh=4, sa=3, mark='Б', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 5,5', odds=1.67, hit=True,
        checks=[('ОСНОВНОЕ ВРЕМЯ 3:3 — 6 ГОЛОВ', True)]))),
]

os.makedirs(OUT, exist_ok=True)
for name, m in BANNERS:
    m.update(date='пятница, 9 октября', tag='НХЛ')
    path = '%s/pick_%s.jpg' % (OUT, name)
    im2.single(m, path, style='verdict', league='NHL')
    print(path)
