"""Послематчевые баннеры (ice_more2, style='verdict') к прогнозам владельца на НХЛ, ночь на 13 октября (МСК).

Счёт — ESPN, NHL.com, CBS Sports / AP: Миннесота — Вегас 4:2, Нью-Джерси — Оттава 1:4 (обе — в основное время).
Запуск: python render/make_picks_1310.py [папка] → pick_nhl_*.jpg (по умолчанию out/1310)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ice_more2 as im2  # noqa: E402
import nhl  # noqa: E402

nhl.register()

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out/1310'
DAY = 'вторник, 13 октября'

PICKS = [
    ('minnesota_vegas', dict(home='Миннесота', away='Вегас', sh=4, sa=2, mark='', pick=dict(
        text='ТОТАЛ МАТЧА МЕНЬШЕ 6,5', odds=1.54, hit=True, checks=[('4:2 — 6 ГОЛОВ В МАТЧЕ', True)]))),
    ('newjersey_ottawa', dict(home='Нью-Джерси', away='Оттава', sh=1, sa=4, mark='', pick=dict(
        text='2X + ТОТАЛ БОЛЬШЕ 4,5', odds=2.12, hit=True,
        checks=[('ОТТАВА ВЫИГРАЛА 4:1 — 2X ЗАШЛА', True), ('5 ГОЛОВ — ТОТАЛ БОЛЬШЕ 4,5 ЗАШЁЛ', True)]))),
]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, m in PICKS:
        m.update(date=DAY, tag='НХЛ')
        path = '%s/pick_nhl_%s.jpg' % (OUT, name)
        im2.single(m, path, style='verdict', league='NHL')
        print(path)
