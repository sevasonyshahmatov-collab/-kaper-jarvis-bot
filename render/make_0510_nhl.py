"""Матчи НХЛ в ночь на 5 октября (МСК) в шаблоне «Бока» (nhl_kit.preview), как баннер Сан-Хосе — Лос-Анджелес.

Матчи, время и П1/Х/П2 — из «Матчей дня» НХЛ, которые таблица заказала в 18:00 МСК 4 октября.
Запуск из папки render: python make_0510_nhl.py → out/0510/*.jpg
"""
import os

import nhl
import nhl_kit

nhl.register()

OUT = 'out/0510'
MATCHES = [
    ('rangers_utah', 'Рейнджерс', 'Юта', '01:00', (2.29, 4.15, 2.68)),
    ('anaheim_florida', 'Анахайм', 'Флорида', '03:00', (2.80, 4.11, 2.22)),
    ('seattle_calgary', 'Сиэтл', 'Калгари', '03:00', (2.09, 4.20, 2.99)),
    ('vancouver_vegas', 'Ванкувер', 'Вегас', '04:00', (4.12, 4.74, 1.68)),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, time, odds in MATCHES:
    print(nhl_kit.preview(home, away, dict(when='ПН 05.10 · %s МСК' % time, odds=odds), '%s/nhl_%s.jpg' % (OUT, name)))
print('готово')
