"""Матчи НХЛ в ночь на 7 октября (МСК) в шаблоне «Бока» (nhl_kit.preview) — в 4К (3840×1920, scale=3).

Матчи, время и П1/Х/П2 — с листа «Прогнозы НХЛ» таблицы (обновлено 06.10 в 16:58 МСК).
Запуск из папки render: python make_0710_nhl.py → out/0710/nhl_*.jpg
"""
import os

import nhl
import nhl_kit

nhl.register()

OUT = 'out/0710'
MATCHES = [
    ('toronto_nashville', 'Торонто', 'Нэшвилл', '02:00', (2.07, 4.24, 3.01)),
    ('montreal_carolina', 'Монреаль', 'Каролина', '02:00', (2.55, 4.24, 2.37)),
    ('detroit_ottawa', 'Детройт', 'Оттава', '02:00', (2.49, 4.17, 2.44)),
    ('newjersey_utah', 'Нью-Джерси', 'Юта', '02:00', (2.28, 4.17, 2.69)),
    ('buffalo_minnesota', 'Баффало', 'Миннесота', '02:00', (2.48, 4.22, 2.43)),
    ('rangers_islanders', 'Рейнджерс', 'Айлендерс', '02:30', (2.12, 4.19, 2.95)),
    ('chicago_stlouis', 'Чикаго', 'Сент-Луис', '03:00', (2.86, 4.18, 2.16)),
    ('seattle_vegas', 'Сиэтл', 'Вегас', '04:40', (3.19, 4.31, 1.98)),
    ('losangeles_florida', 'Лос-Анджелес', 'Флорида', '05:00', (2.69, 4.14, 2.29)),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, time, odds in MATCHES:
    print(nhl_kit.preview(home, away, dict(when='СР 07.10 · %s МСК' % time, odds=odds), '%s/nhl_%s.jpg' % (OUT, name), scale=3))
print('готово')
