"""Послематчевые баннеры (ice_more2, style='verdict') к прогнозам владельца на НХЛ, ночь на 12 октября (МСК).

Прогнозы — от владельца (без кэфов). Счёт — таблица ещё не подтянула (обновление 06:40 МСК); по отчётам ESPN, NHL.com,
CBS / AP: Филадельфия — Каролина 1:4, Вашингтон — Сиэтл 3:5 (решающие голы в третьем периоде, без ОТ),
Рейнджерс — Ванкувер 6:2. Все три — в основное время, так что фора и тоталы считаются по ним без оговорок.
Запуск: python render/make_picks_1210.py [папка] → pick_*.jpg (по умолчанию out/1210)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ice_more2 as im2  # noqa: E402
import nhl  # noqa: E402

nhl.register()

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out/1210'
MON = 'понедельник, 12 октября'

PICKS = [
    ('philadelphia_carolina', dict(home='Филадельфия', away='Каролина', sh=1, sa=4, mark='', pick=dict(
        text='ПОБЕДА КАРОЛИНЫ С ФОРОЙ −1', odds=None, hit=True,
        checks=[('КАРОЛИНА ВЫИГРАЛА 4:1 — НА 3 ШАЙБЫ', True)]))),
    ('washington_seattle', dict(home='Вашингтон', away='Сиэтл', sh=3, sa=5, mark='', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 5,5', odds=None, hit=True, checks=[('3:5 — 8 ГОЛОВ В МАТЧЕ', True)]))),
    ('rangers_vancouver', dict(home='Рейнджерс', away='Ванкувер', sh=6, sa=2, mark='', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 5,5', odds=None, hit=True, checks=[('6:2 — 8 ГОЛОВ В МАТЧЕ', True)]))),
]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, m in PICKS:
        m.update(date=MON, tag='НХЛ')
        path = '%s/pick_nhl_%s.jpg' % (OUT, name)
        im2.single(m, path, style='verdict', league='NHL')
        print(path)
