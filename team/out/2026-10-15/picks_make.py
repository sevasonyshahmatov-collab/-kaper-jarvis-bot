"""Баннеры «Versus» к прогнозам 15.10 (КХЛ): Лада — СКА 18:00, Северсталь — Локомотив 19:00 МСК.
Время — рассылка таблицы «Бока» 08:03 и приложение КХЛ; линия П1/Х/П2 осн. времени — Pinnacle (лист «Коэффициенты» таблицы),
08:44 МСК. Запуск из корня: PYTHONPATH=render python team/out/2026-10-15/picks_make.py [папка] (по умолчанию out/1510)"""
import os
import sys

import versus

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out/1510'
os.makedirs(OUT, exist_ok=True)
for home, away, time, odds, name in (('Лада', 'СКА', '18:00', (4.54, 4.13, 1.64), 'lada_ska'),
                                     ('Северсталь', 'Локомотив', '19:00', (3.51, 3.72, 1.93), 'sev_loko')):
    print(versus.render(home, away, '%s/vs_%s.jpg' % (OUT, name), date='15 октября', time=time, odds=odds, league='KHL'))
