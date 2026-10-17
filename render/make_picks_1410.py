"""Послематчевые баннеры (ice_more2, style='verdict') к прогнозам владельца на НХЛ, ночь на 14 октября (МСК).

Счёт — официальный API НХЛ (api-web.nhle.com/v1/score) и табло ESPN, совпадают:
Чикаго — Питтсбург 5:3, Филадельфия — Сиэтл 2:3 Б (2:2 в осн. время), Сан-Хосе — Бостон 3:6, Виннипег — Миннесота 5:2.
Индивидуальный тотал Сиэтла владелец считает по основному времени (победный буллит не в счёт) — не зашёл.
Запуск: python render/make_picks_1410.py [папка] → pick_nhl_*.jpg (по умолчанию out/1410)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ice_more2 as im2  # noqa: E402
import nhl  # noqa: E402

nhl.register()

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out/1410'
DAY = 'среда, 14 октября'

PICKS = [
    ('chicago_pittsburgh', dict(home='Чикаго', away='Питтсбург', sh=5, sa=3, mark='', pick=dict(
        text='ПОБЕДА ПИТТСБУРГА С УЧЁТОМ ОТ', odds=1.63, hit=False,
        checks=[('ЧИКАГО ВЫИГРАЛ 5:3 В ОСНОВНОЕ ВРЕМЯ', False)]))),
    ('philadelphia_seattle', dict(home='Филадельфия', away='Сиэтл', sh=2, sa=3, mark='Б', pick=dict(
        text='ТОТАЛ СИЭТЛА БОЛЬШЕ 2,5', odds=1.67, hit=False,
        checks=[('2:2 В ОСНОВНОЕ ВРЕМЯ — У СИЭТЛА 2 ШАЙБЫ', False)]))),
    ('sanjose_boston', dict(home='Сан-Хосе', away='Бостон', sh=3, sa=6, mark='', pick=dict(
        text='ПОБЕДА БОСТОНА С УЧЁТОМ ОТ', odds=1.84, hit=True,
        checks=[('БОСТОН ВЫИГРАЛ 6:3', True)]))),
    ('winnipeg_minnesota', dict(home='Виннипег', away='Миннесота', sh=5, sa=2, mark='', pick=dict(
        text='ТОТАЛ МАТЧА МЕНЬШЕ 6', odds=1.88, hit=False,
        checks=[('5:2 — 7 ГОЛОВ В МАТЧЕ', False)]))),
]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, m in PICKS:
        m.update(date=DAY, tag='НХЛ')
        path = '%s/pick_nhl_%s.jpg' % (OUT, name)
        im2.single(m, path, style='verdict', league='NHL')
        print(path)
