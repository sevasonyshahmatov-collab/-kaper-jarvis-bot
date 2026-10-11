"""Баннеры к постам-прогнозам на игровой день 10 октября: НХЛ (ночь на 11.10) и КХЛ 10.10 — «Бока» с прогнозом и кэфом
(nhl_kit mode='pick') в 4К (scale=3), как make_picks_pre_0910.py.

Прогнозы и кэфы — от владельца канала; время и хозяева/гости — с листа «Прогнозы — кратко» обеих таблиц.
У Сан-Хосе — Эдмонтон кэф не указан — баннер без кэфа.
Запуск из папки render: python make_picks_pre_1010.py [папка] → prog_*.jpg (по умолчанию out/1010)
"""
import os
import sys

import nhl
import nhl_kit
import poster

nhl.register()

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out/1010'
NHL = [
    ('boston_philadelphia', 'Бостон', 'Филадельфия', 'СБ 10.10 · 20:00 МСК', 'ПОБЕДА БОСТОНА', 2.21),
    ('newjersey_vancouver', 'Нью-Джерси', 'Ванкувер', 'СБ 10.10 · 22:30 МСК', 'ТОТАЛ МАТЧА БОЛЬШЕ 6', 1.91),
    ('sanjose_edmonton', 'Сан-Хосе', 'Эдмонтон', 'СБ 10.10 · 23:00 МСК', 'ТОТАЛ МАТЧА БОЛЬШЕ 6', None),
    ('florida_minnesota', 'Флорида', 'Миннесота', 'ВС 11.10 · 01:00 МСК', 'ТОТАЛ МАТЧА МЕНЬШЕ 6', 1.67),
    ('chicago_carolina', 'Чикаго', 'Каролина', 'ВС 11.10 · 02:00 МСК', 'ПОБЕДА КАРОЛИНЫ', 1.66),
    ('colorado_toronto', 'Колорадо', 'Торонто', 'ВС 11.10 · 02:00 МСК', 'ТОТАЛ МАТЧА БОЛЬШЕ 6,5', 2.08),
    ('calgary_anaheim', 'Калгари', 'Анахайм', 'ВС 11.10 · 05:00 МСК', 'ПОБЕДА АНАХАЙМА С УЧЁТОМ ОТ', 1.87),
    ('vegas_losangeles', 'Вегас', 'Лос-Анджелес', 'ВС 11.10 · 05:00 МСК', 'ТОТАЛ МАТЧА БОЛЬШЕ 5,5', 1.75),
]
KHL = [
    ('admiral_lada', 'Адмирал', 'Лада', 'СБ 10.10 · 10:00 МСК', 'ИТОГОВАЯ ПОБЕДА АДМИРАЛА', 1.67),
    ('barys_avangard', 'Барыс', 'Авангард', 'СБ 10.10 · 14:30 МСК', 'ИНДИВИДУАЛЬНЫЙ ТОТАЛ БАРЫСА БОЛЬШЕ 2,5', 1.79),
    ('akbars_severstal', 'Ак Барс', 'Северсталь', 'СБ 10.10 · 17:00 МСК', 'ТОТАЛ МАТЧА МЕНЬШЕ 6', 1.52),
    ('lokomotiv_dinamominsk', 'Локомотив', 'Динамо Минск', 'СБ 10.10 · 17:00 МСК', 'ПОБЕДА ЛОКОМОТИВА И ТОТАЛ МЕНЬШЕ 5,5', 2.12),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, when, pred, coef in NHL:
    print(nhl_kit._side(home, away, '%s/prog_nhl_%s.jpg' % (OUT, name), 'pick', when=when, pred=pred, coef=coef, scale=3))
for name, home, away, when, pred, coef in KHL:
    print(nhl_kit._side(home, away, '%s/prog_khl_%s.jpg' % (OUT, name), 'pick', when=when, pred=pred, coef=coef,
                        tag='KXL', accent=poster.ACC, scale=3))
