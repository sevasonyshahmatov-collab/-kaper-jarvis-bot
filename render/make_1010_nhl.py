"""Матчи НХЛ в ночь на 10 октября (МСК) в шаблоне «Бока» (nhl_kit.preview) — в 4К (3840×1920, scale=3).

Матчи, время и П1/Х/П2 — с листа «Прогнозы НХЛ» таблицы (выгрузка 09.10 около 13:20 МСК).
Бостон — Филадельфия, Нью-Джерси — Ванкувер, Сан-Хосе — Эдмонтон — дневные матчи субботы 10 октября (20:00, 22:30, 23:00 МСК 10.10),
это уже следующий игровой день НХЛ вместе с ночью на 11-е — сюда не входят.
Запуск из папки render: python make_1010_nhl.py → out/1010/nhl_*.jpg
"""
import os

import nhl
import nhl_kit

nhl.register()

OUT = 'out/1010'
DAY = 'СБ 10.10'
MATCHES = [
    ('detroit_seattle', 'Детройт', 'Сиэтл', '02:00', (2.12, 4.21, 2.87)),
    ('washington_rangers', 'Вашингтон', 'Рейнджерс', '02:00', (2.18, 4.13, 2.80)),
    ('columbus_pittsburgh', 'Коламбус', 'Питтсбург', '02:00', (2.32, 4.18, 2.58)),
    ('winnipeg_anaheim', 'Виннипег', 'Анахайм', '03:00', (2.28, 4.18, 2.64)),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, time, odds in MATCHES:
    print(nhl_kit.preview(home, away, dict(when='%s · %s МСК' % (DAY, time), odds=odds), '%s/nhl_%s.jpg' % (OUT, name), scale=3))
