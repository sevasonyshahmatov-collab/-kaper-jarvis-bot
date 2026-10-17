"""Баннер «Versus» к прогнозу на 16.10 (КХЛ): Торпедо — Динамо Москва, 19:00 МСК (приложение КХЛ, run 141).
Линия П1/Х/П2 основного времени — Pinnacle (как лист «Коэффициенты»), 10:34 МСК 15.10.
Запуск из корня: PYTHONPATH=render python team/out/2026-10-15/pick1610_make.py [папка] (по умолчанию out/1510)"""
import os
import sys

import versus

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out/1510'
os.makedirs(OUT, exist_ok=True)
print(versus.render('Торпедо', 'Динамо Москва', OUT + '/vs_torpedo_dinamo.jpg', date='16 октября', time='19:00',
                    odds=(2.12, 3.76, 3.00), league='KHL'))
