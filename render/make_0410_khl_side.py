"""Матчи КХЛ 4 октября в шаблоне «Бока» (nhl_kit.preview, как у НХЛ), с шапкой JARVIS | KXL и золотым акцентом КХЛ.

Линия П1/Х/П2 — из «Матчей дня» в 09:00 МСК. Нефтехимик и Сибирь почти одного синего — фон слился бы в один цвет,
поэтому на этом баннере Сибирь в серебристо-стальном (как Лос-Анджелес в НХЛ).
Запуск из папки render: python make_0410_khl_side.py → out/0410/side_*.jpg
"""
import os

import nhl_kit
import poster

OUT = 'out/0410'
MATCHES = [
    ('neftekhimik_sibir', 'Нефтехимик', 'Сибирь', 'ВС 04.10 · 14:00 МСК', (2.11, 3.62, 3.11), {'Сибирь': (150, 165, 190)}),
    ('avtomobilist_amur', 'Автомобилист', 'Амур', 'ВС 04.10 · 14:30 МСК', (1.81, 3.45, 4.39), {}),
    ('spartak_barys', 'Спартак', 'Барыс', 'ВС 04.10 · 17:00 МСК', (1.79, 3.97, 3.85), {}),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, when, odds, colors in MATCHES:
    saved = {t: poster.BANNER[t] for t in colors}
    poster.BANNER.update(colors)
    try:
        p = nhl_kit.preview(home, away, dict(when=when, odds=odds), '%s/side_%s.jpg' % (OUT, name),
                            tag='KXL', accent=poster.ACC)
    finally:
        poster.BANNER.update(saved)
    print(p)
print('готово')
