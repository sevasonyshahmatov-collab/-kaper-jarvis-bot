"""Матчи КХЛ 7 октября в шаблоне «Бока» (nhl_kit.preview), шапка JARVIS | KXL и золотой акцент КХЛ — в 4К (3840×1920, scale=3).

Матчи, время и П1/Х/П2 — с листа «Прогнозы КХЛ» таблицы (выгрузка 07.10 около 10:00 МСК). Названия — по центру относительно логотипов.
Запуск из папки render: python make_0710_khl_side.py → out/0710/side_*.jpg
"""
import os

import nhl_kit
import poster

OUT = 'out/0710'
DAY = 'СР 07.10'
MATCHES = [
    ('sibir_salavat', 'Сибирь', 'Салават Юлаев', '15:30', (3.13, 3.73, 2.07), {}),
    ('metallurg_admiral', 'Металлург', 'Адмирал', '17:00', (1.46, 4.51, 6.09), {}),
    ('dinamo_shanghai', 'Динамо Москва', 'Шанхайские Драконы', '19:30', (2.01, 3.78, 3.23), {}),
    ('sochi_spartak', 'Сочи', 'Спартак', '19:30', (4.68, 4.28, 1.60), {}),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, time, odds, colors in MATCHES:
    saved = {t: poster.BANNER[t] for t in colors}
    poster.BANNER.update(colors)
    try:
        p = nhl_kit.preview(home, away, dict(when='%s · %s МСК' % (DAY, time), odds=odds), '%s/side_%s.jpg' % (OUT, name),
                            tag='KXL', accent=poster.ACC, scale=3)
    finally:
        poster.BANNER.update(saved)
    print(p)
