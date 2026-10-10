"""Матчи КХЛ 9 октября в шаблоне «Бока» (nhl_kit.preview), шапка JARVIS | KXL и золотой акцент КХЛ — в 4К (3840×1920, scale=3).

Матчи, время и П1/Х/П2 — с листа «Прогнозы КХЛ» таблицы (выгрузка 09.10 около 13:20 МСК).
Запуск из папки render: python make_0910_khl_side.py → out/0910/side_*.jpg
"""
import os

import nhl_kit
import poster

OUT = 'out/0910'
DAY = 'ПТ 09.10'
MATCHES = [
    ('metallurg_salavat', 'Металлург', 'Салават Юлаев', '17:00', (1.88, 3.80, 3.61)),
    ('dinamo_cska', 'Динамо Москва', 'ЦСКА', '19:30', (3.02, 3.61, 2.16)),
    ('sochi_spartak', 'Сочи', 'Спартак', '19:30', (4.95, 4.19, 1.58)),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, time, odds in MATCHES:
    print(nhl_kit.preview(home, away, dict(when='%s · %s МСК' % (DAY, time), odds=odds), '%s/side_%s.jpg' % (OUT, name),
                          tag='KXL', accent=poster.ACC, scale=3))
