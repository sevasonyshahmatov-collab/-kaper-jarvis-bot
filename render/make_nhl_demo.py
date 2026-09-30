# -*- coding: utf-8 -*-
"""Пробный лист: все семь типов баннеров НХЛ на выдуманных данных."""
import os

import nhl
import nhl_kit
from nhl import team_info as ti

nhl.register()
O = 'out/nhl_demo/'
os.makedirs(O, exist_ok=True)
paths = []

# 1 — предматчевая карточка «Бока» с линией П1/Х/П2
info = dict(when='ЧТ 01.10 · 03:00 МСК', odds=(2.05, 3.95, 3.30),
            home=ti(4, 6, 'WLXWW'), away=ti(4, 5, 'WWOLX'))
paths.append(nhl_kit.preview('Бостон', 'Торонто', info, O + '01_preview.png'))

# 2 — постер прогноза
m = dict(when='ЧТ 01.10 · 05:00 МСК',
         pred='Победа Вегаса с учётом ОТ и буллитов', coef=1.81,
         home=dict(team='Вегас', name='Вегас', **ti(4, 6, 'WWLXW')),
         away=dict(team='Сан-Хосе', name='Сан-Хосе', **ti(4, 2, 'LLWLL')))
paths.append(nhl_kit.pick(m, O + '02_pick.png'))

# 3 — постер результата
paths.append(nhl_kit.result(
    'Каролина', 'Нью-Джерси', 4, 1, O + '03_result.png',
    verdict='ЗАШЁЛ', when='СР 30.09 · 02:30 МСК',
    pred='Тотал больше 5.5', coef=1.74,
    home_info=ti(4, 6, 'WWLWW'), away_info=ti(4, 3, 'LWOLL')))

# 4 — афиша дня
rows = [dict(home='Бостон', away='Торонто', when='03:00 МСК', odds=(2.05, 3.95, 3.30)),
        dict(home='Вегас', away='Сан-Хосе', when='05:00 МСК', odds=(1.62, 4.30, 5.10)),
        dict(home='Каролина', away='Нью-Джерси', when='02:30 МСК', odds=(1.90, 4.05, 3.75)),
        dict(home='Эдмонтон', away='Ванкувер', when='06:00 МСК', odds=(1.70, 4.20, 4.60))]
paths.append(nhl_kit.slate([dict(r) for r in rows], O + '04_slate.png',
                           date_title='четверг, 1 октября'))

# 5 — прогнозы дня
picks = [dict(home='Бостон', away='Торонто', when='03:00', pred='Тотал больше 6', coef=1.85),
         dict(home='Вегас', away='Сан-Хосе', when='05:00', pred='Фора Вегаса (-1.5)', coef=2.10)]
paths.append(nhl_kit.picks(picks, O + '05_picks.png',
                           date_title='четверг, 1 октября', express=1.85 * 2.10))

# 6 — прогнозы зашли
hits = [dict(home='Каролина', away='Нью-Джерси', score='4:1', mark='',
             pred='Тотал больше 5.5', coef=1.74, ok=True),
        dict(home='Флорида', away='Тампа-Бэй', score='2:3', mark='ОТ',
             pred='П2 с учётом ОТ', coef=2.05, ok=True)]
paths.append(nhl_kit.hits(hits, O + '06_hits.png',
                          date_title='среда, 30 сентября', express=1.74 * 2.05))

# 7 — итоги дня
res = [dict(home='Каролина', away='Нью-Джерси', sh=4, sa=1, mark=''),
       dict(home='Флорида', away='Тампа-Бэй', sh=2, sa=3, mark='ОТ'),
       dict(home='Сиэтл', away='Сент-Луис', sh=1, sa=2, mark=''),
       dict(home='Питтсбург', away='Колорадо', sh=3, sa=5, mark='')]
paths.append(nhl_kit.results_day(res, O + '07_results.png',
                                 date_title='среда, 30 сентября'))

for p in paths:
    print('ok', nhl_kit._jpg(p))
