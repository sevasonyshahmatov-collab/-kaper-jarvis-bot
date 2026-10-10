"""Матчи КХЛ 10 октября в шаблоне «Бока» (nhl_kit.preview), шапка JARVIS | KXL и золотой акцент КХЛ — в 4К (3840×1920, scale=3).

Матчи, время и П1/Х/П2 — с листа «Прогнозы КХЛ» таблицы (выгрузка 10.10 около 09:00 МСК).
Запуск из папки render: python make_1010_khl_side.py → out/1010/side_*.jpg
"""
import os

import nhl_kit
import poster

OUT = 'out/1010'
DAY = 'СБ 10.10'
MATCHES = [
    ('admiral_lada', 'Адмирал', 'Лада', '10:00', (1.89, 3.72, 3.64)),
    ('traktor_sibir', 'Трактор', 'Сибирь', '14:00', (1.85, 3.95, 3.61)),
    ('barys_avangard', 'Барыс', 'Авангард', '14:30', (3.18, 3.85, 2.01)),
    ('akbars_severstal', 'Ак Барс', 'Северсталь', '17:00', (2.06, 3.67, 3.20)),
    ('lokomotiv_minsk', 'Локомотив', 'Динамо Минск', '17:00', (1.82, 3.83, 3.84)),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, time, odds in MATCHES:
    print(nhl_kit.preview(home, away, dict(when='%s · %s МСК' % (DAY, time), odds=odds), '%s/side_%s.jpg' % (OUT, name),
                          tag='KXL', accent=poster.ACC, scale=3))
