"""Матчи НХЛ в ночь на 9 октября (МСК) в шаблоне «Бока» (nhl_kit.preview) — в 4К (3840×1920, scale=3).

Матчи, время и П1/Х/П2 — с листа «Прогнозы НХЛ» таблицы (выгрузка 08.10 около 12:40 МСК).
Похожие клубные цвета шаблон разводит сам (nhl.pair_colors): Филадельфия рядом с Оттавой и Колорадо рядом с Калгари — во вторых цветах.
Запуск из папки render: python make_0910_nhl.py → out/0910/nhl_*.jpg
"""
import os

import nhl
import nhl_kit
import poster

nhl.register()

OUT = 'out/0910'
DAY = 'ПТ 09.10'
MATCHES = [
    ('boston_utah', 'Бостон', 'Юта', '02:00', (2.68, 4.16, 2.25), {}),
    ('buffalo_dallas', 'Баффало', 'Даллас', '02:00', (2.63, 4.15, 2.29), {}),
    ('montreal_nashville', 'Монреаль', 'Нэшвилл', '02:00', (1.93, 4.34, 3.25), {}),
    ('ottawa_philadelphia', 'Оттава', 'Филадельфия', '02:00', (2.05, 4.22, 3.00), {}),
    ('tampa_minnesota', 'Тампа-Бэй', 'Миннесота', '02:00', (2.05, 4.22, 3.01), {}),
    ('carolina_vancouver', 'Каролина', 'Ванкувер', '02:00', (1.52, 5.03, 4.93), {}),
    ('islanders_chicago', 'Айлендерс', 'Чикаго', '02:30', (1.90, 4.26, 3.37), {}),
    ('stlouis_sanjose', 'Сент-Луис', 'Сан-Хосе', '03:00', (2.06, 4.19, 3.00), {}),
    ('calgary_colorado', 'Калгари', 'Колорадо', '04:00', (3.87, 4.45, 1.74), {}),
    ('vegas_toronto', 'Вегас', 'Торонто', '05:00', (1.95, 4.28, 3.21), {}),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, time, odds, colors in MATCHES:
    saved = {t: poster.BANNER.get(t) for t in colors}
    poster.BANNER.update(colors)
    try:
        p = nhl_kit.preview(home, away, dict(when='%s · %s МСК' % (DAY, time), odds=odds), '%s/nhl_%s.jpg' % (OUT, name), scale=3)
    finally:
        poster.BANNER.update(saved)
    print(p)
