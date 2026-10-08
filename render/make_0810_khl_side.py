"""Матчи КХЛ 8 октября в шаблоне «Бока» (nhl_kit.preview), шапка JARVIS | KXL и золотой акцент КХЛ — в 4К (3840×1920, scale=3).

Матчи, время и П1/Х/П2 — с листа «Прогнозы КХЛ» таблицы (выгрузка 08.10 около 12:40 МСК).
Динамо Минск — СКА: в таблице нет ни времени, ни линии; время 17:10 — со страницы матча Sport Mail, баннер без строки кэфов.
Динамо Минск (голубой) и СКА (синий) близки — на этом баннере СКА в своём красном.
Запуск из папки render: python make_0810_khl_side.py → out/0810/side_*.jpg
"""
import os

import nhl_kit
import poster

OUT = 'out/0810'
DAY = 'ЧТ 08.10'
MATCHES = [
    ('traktor_amur', 'Трактор', 'Амур', '17:00', (1.93, 3.69, 3.51), {}),
    ('minsk_ska', 'Динамо Минск', 'СКА', '17:10', None, {'СКА': (190, 25, 40)}),
    ('neftekhimik_avangard', 'Нефтехимик', 'Авангард', '19:30', (2.88, 3.70, 2.21), {}),
    ('torpedo_severstal', 'Торпедо', 'Северсталь', '19:30', (1.95, 3.81, 3.37), {}),
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
