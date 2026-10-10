"""Матчи КХЛ 5 октября в шаблоне «Бока» (nhl_kit.preview), шапка JARVIS | KXL и золотой акцент КХЛ.

Линия П1/Х/П2 — из «Матчей дня» КХЛ, которые таблица заказала утром 5 октября. Названия — по центру относительно логотипов.
Динамо Минск (голубой) и Торпедо (синий) близки по цвету — на этом баннере Торпедо в тёмно-синем, чтобы фон не слился.
Запуск из папки render: python make_0510_khl_side.py → out/0510/side_*.jpg
"""
import os

import nhl_kit
import poster

OUT = 'out/0510'
DAY = 'ПН 05.10'
MATCHES = [
    ('metallurg_admiral', 'Металлург', 'Адмирал', '17:00', (1.48, 4.58, 5.72), {}),
    ('lada_shanghai', 'Лада', 'Шанхайские Драконы', '18:00', (3.09, 3.83, 2.06), {}),
    ('akbars_lokomotiv', 'Ак Барс', 'Локомотив', '19:30', (2.98, 3.76, 2.13), {}),
    ('minsk_torpedo', 'Динамо Минск', 'Торпедо', '19:30', (2.21, 3.79, 2.81), {'Торпедо': (22, 44, 120)}),
    ('cska_salavat', 'ЦСКА', 'Салават Юлаев', '19:30', (1.80, 3.86, 3.89), {}),
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
