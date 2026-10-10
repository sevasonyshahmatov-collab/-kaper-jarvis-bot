"""Баннеры к постам-прогнозам НХЛ в ночь на 9 октября («Бока» с прогнозом и кэфом, nhl_kit mode='pick') — в 4К (scale=3).

Прогнозы и кэфы — от владельца канала; время — с листа «Прогнозы НХЛ».
Запуск из папки render: python make_picks_pre_0910.py → out/0910/prog_*.jpg
"""
import os

import nhl
import nhl_kit

nhl.register()

OUT = 'out/0910'
PICKS = [
    ('boston_utah', 'Бостон', 'Юта', '02:00', 'ЮТА НЕ ПРОИГРАЕТ (Х2)', 1.61),
    ('ottawa_philadelphia', 'Оттава', 'Филадельфия', '02:00', 'ПОБЕДА ОТТАВЫ', 2.05),
    ('islanders_chicago', 'Айлендерс', 'Чикаго', '02:30', 'ПОБЕДА АЙЛЕНДЕРС', 1.90),
    ('stlouis_sanjose', 'Сент-Луис', 'Сан-Хосе', '03:00', 'ИНДИВИДУАЛЬНЫЙ ТОТАЛ СЕНТ-ЛУИСА БОЛЬШЕ 2,5', 1.71),
    ('calgary_colorado', 'Калгари', 'Колорадо', '04:00', 'ПОБЕДА КОЛОРАДО', 1.76),
    ('vegas_toronto', 'Вегас', 'Торонто', '05:00', 'ТОТАЛ МАТЧА БОЛЬШЕ 5,5', 1.67),
]

os.makedirs(OUT, exist_ok=True)
for name, home, away, time, pred, coef in PICKS:
    print(nhl_kit._side(home, away, '%s/prog_%s.jpg' % (OUT, name), 'pick', when='ПТ 09.10 · %s МСК' % time,
                        pred=pred, coef=coef, scale=3))
