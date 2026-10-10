"""Матчи КХЛ 6 октября в шаблоне «Бока» (nhl_kit.preview), шапка JARVIS | KXL и золотой акцент КХЛ.

Линия П1/Х/П2 — с листа «Прогнозы КХЛ» таблицы (обновлено 06.10 в 16:29 МСК). Названия — по центру относительно логотипов.
Автомобилист и Авангард оба красные — на этом баннере Авангард в чёрно-графитовом, чтобы половины не слились.
Запуск из папки render: python make_0610_khl_side.py → out/0610/side_*.jpg
"""
import os

import nhl_kit
import poster

OUT = 'out/0610'
DAY = 'ВТ 06.10'
MATCHES = [
    ('avtomobilist_avangard', 'Автомобилист', 'Авангард', '17:00', (2.47, 3.77, 2.49), {'Авангард': (38, 34, 40)}),
    ('traktor_amur', 'Трактор', 'Амур', '17:00', (1.93, 3.78, 3.47), {}),
    ('ska_severstal', 'СКА', 'Северсталь', '19:30', (1.81, 4.08, 3.67), {}),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, time, odds, colors in MATCHES:
    saved = {t: poster.BANNER[t] for t in colors}
    poster.BANNER.update(colors)
    try:
        p = nhl_kit.preview(home, away, dict(when='%s · %s МСК' % (DAY, time), odds=odds), '%s/side_%s.jpg' % (OUT, name),
                            tag='KXL', accent=poster.ACC)
    finally:
        poster.BANNER.update(saved)
    print(p)
