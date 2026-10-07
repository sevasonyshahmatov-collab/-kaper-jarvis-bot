"""Матчи НХЛ в ночь на 8 октября (МСК) в шаблоне «Бока» (nhl_kit.preview) — в 4К (3840×1920, scale=3).

Матчи, время и П1/Х/П2 — с листа «Прогнозы НХЛ» таблицы (выгрузка 07.10 около 10:00 МСК).
Анахайм и Эдмонтон оба оранжевые — на этом баннере Эдмонтон в своём синем, чтобы половины не слились.
Запуск из папки render: python make_0810_nhl.py → out/0810/nhl_*.jpg
"""
import os

import nhl
import nhl_kit
import poster

nhl.register()

OUT = 'out/0810'
DAY = 'ЧТ 08.10'
MATCHES = [
    ('washington_pittsburgh', 'Вашингтон', 'Питтсбург', '02:30', (2.03, 4.32, 3.00), {}),
    ('winnipeg_colorado', 'Виннипег', 'Колорадо', '02:30', (3.34, 4.41, 1.88), {}),
    ('anaheim_edmonton', 'Анахайм', 'Эдмонтон', '05:00', (2.71, 4.31, 2.19), {'Эдмонтон': (10, 48, 112)}),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, time, odds, colors in MATCHES:
    saved = {t: poster.BANNER[t] for t in colors}
    poster.BANNER.update(colors)
    try:
        p = nhl_kit.preview(home, away, dict(when='%s · %s МСК' % (DAY, time), odds=odds), '%s/nhl_%s.jpg' % (OUT, name), scale=3)
    finally:
        poster.BANNER.update(saved)
    print(p)
