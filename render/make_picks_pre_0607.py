"""Баннеры к постам-прогнозам («Бока» с прогнозом и кэфом, nhl_kit mode='pick') — в 4К (scale=3).

КХЛ 6 октября: Трактор — Амур (тотал меньше 5,5 за 1.78), СКА — Северсталь (фора СКА −1 за 2.01).
НХЛ, ночь на 7 октября: Баффало — Миннесота, Монреаль — Каролина, Нью-Джерси — Юта, Рейнджерс — Айлендерс.
Эмодзи из текста прогноза на картинку не идут. Кэф у тотала Юты не назван — без плашки кэфа.
Запуск из папки render: python make_picks_pre_0607.py → out/0610/prog_*.jpg, out/0710/prog_*.jpg
"""
import os

import nhl
import nhl_kit
import poster

nhl.register()

PICKS = [
    ('0610', 'KXL', 'traktor_amur', 'Трактор', 'Амур', 'ВТ 06.10 · 17:00 МСК', 'ТОТАЛ МЕНЬШЕ 5,5', 1.78),
    ('0610', 'KXL', 'ska_severstal', 'СКА', 'Северсталь', 'ВТ 06.10 · 19:30 МСК', 'ФОРА СКА (−1)', 2.01),
    ('0710', 'NHL', 'buffalo_minnesota', 'Баффало', 'Миннесота', 'СР 07.10 · 02:00 МСК', 'ТОТАЛ МЕНЬШЕ 6,5', 1.67),
    ('0710', 'NHL', 'montreal_carolina', 'Монреаль', 'Каролина', 'СР 07.10 · 02:00 МСК', 'ТОТАЛ МЕНЬШЕ 6,5', 1.59),
    ('0710', 'NHL', 'newjersey_utah', 'Нью-Джерси', 'Юта', 'СР 07.10 · 02:00 МСК', 'ИНДИВИДУАЛЬНЫЙ ТОТАЛ ЮТЫ БОЛЬШЕ 2,5', None),
    ('0710', 'NHL', 'rangers_islanders', 'Рейнджерс', 'Айлендерс', 'СР 07.10 · 02:30 МСК', 'ПОБЕДА РЕЙНДЖЕРС', 2.10),
]

for day, tag, name, home, away, when, pred, coef in PICKS:
    out = 'out/' + day
    os.makedirs(out, exist_ok=True)
    kw = dict(tag='KXL', accent=poster.ACC) if tag == 'KXL' else {}
    print(nhl_kit._side(home, away, '%s/prog_%s.jpg' % (out, name), 'pick', when=when, pred=pred, coef=coef, scale=3, **kw))
