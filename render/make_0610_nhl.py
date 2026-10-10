"""Матчи НХЛ в ночь на 6 октября (МСК) в шаблоне «Бока» (nhl_kit.preview), названия по центру относительно логотипов.

Матчи, время и П1/Х/П2 — из «Матчей дня» НХЛ, которые таблица заказала в 18:00 МСК 5 октября.
Запуск из папки render: python make_0610_nhl.py → out/0610/*.jpg
"""
import os

import nhl
import nhl_kit

nhl.register()

OUT = 'out/0610'
MATCHES = [
    ('tampa_philadelphia', 'Тампа-Бэй', 'Филадельфия', '02:00', (1.78, 4.50, 3.73)),
    ('boston_ottawa', 'Бостон', 'Оттава', '02:30', (2.60, 4.14, 2.36)),
    ('pittsburgh_winnipeg', 'Питтсбург', 'Виннипег', '02:30', (1.92, 4.42, 3.30)),
    ('dallas_sanjose', 'Даллас', 'Сан-Хосе', '03:00', (1.96, 4.38, 3.20)),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, time, odds in MATCHES:
    print(nhl_kit.preview(home, away, dict(when='ВТ 06.10 · %s МСК' % time, odds=odds), '%s/nhl_%s.jpg' % (OUT, name)))
print('готово')
