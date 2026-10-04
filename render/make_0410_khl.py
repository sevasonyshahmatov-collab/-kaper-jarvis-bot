"""Предматчевые баннеры на матчи КХЛ 4 октября (single_ice, формат «Лёд»).

Линия П1/Х/П2 — та же, что ушла в «Матчи дня» в 09:00 МСК. Шанс на победу с ОТ считается из линии:
вероятности без маржи, ничья делится пополам (так же делает таблица, когда нет линии с ОТ).
Запуск из папки render: python make_0410_khl.py → out/0410/*.jpg
"""
import os

import single_ice as si

OUT = 'out/0410'
DAY = 'воскресенье, 4 октября'

MATCHES = [
    ('neftekhimik_sibir', dict(home='Нефтехимик', away='Сибирь', time='14:00', odds=(2.11, 3.62, 3.11))),
    ('avtomobilist_amur', dict(home='Автомобилист', away='Амур', time='14:30', odds=(1.81, 3.45, 4.39))),
    ('spartak_barys', dict(home='Спартак', away='Барыс', time='17:00', odds=(1.79, 3.97, 3.85))),
]


def chance(odds):
    inv = [1 / o for o in odds]
    p1, px, _ = [x / sum(inv) for x in inv]
    return 100 * (p1 + px / 2)


os.makedirs(OUT, exist_ok=True)
for name, m in MATCHES:
    m.update(date=DAY, tag='КХЛ', chance=chance(m['odds']))
    path = '%s/khl_%s.jpg' % (OUT, name)
    si.render(m, path, league='KHL', title='АНОНС МАТЧА')
    print(path, '— шанс хозяев %.0f%%' % m['chance'])
print('готово')
