"""Послематчевый баннер к прогнозу КХЛ 5 октября (ice_more2, style='verdict').

Металлург — Адмирал 2:5 (основное время): тотал больше 5,5 — 7 голов, ставка зашла.
Запуск из папки render: python make_picks_0510_khl.py → out/0510/pick_*.jpg
"""
import os

import ice_more2 as im2

OUT = 'out/0510'
DAY = 'понедельник, 5 октября'

BANNERS = [
    ('metallurg_admiral', dict(home='Металлург', away='Адмирал', sh=2, sa=5, mark='', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 5,5', hit=True,
        checks=[('2:5 — 7 ГОЛОВ В МАТЧЕ', True)]))),
]

os.makedirs(OUT, exist_ok=True)
for name, m in BANNERS:
    m.update(date=DAY, tag='КХЛ')
    path = '%s/pick_%s.jpg' % (OUT, name)
    im2.single(m, path, style='verdict', league='KHL')
    print(path)
