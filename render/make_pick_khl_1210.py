"""Послематчевый баннер (ice_more2, style='verdict') к прогнозу владельца на КХЛ, 12 октября: победа Амура за 1,84.

Счёт — Амур — Лада 1:0 в основное время (таблица КХЛ: «результаты матчей», ОТ/буллиты — нет; Спорт-Экспресс, LiveResult).
Запуск: python render/make_pick_khl_1210.py [папка] → pick_khl_amur_lada.jpg (по умолчанию out/1210)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ice_more2 as im2  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out/1210'
MON = 'понедельник, 12 октября'

PICKS = [
    ('amur_lada', dict(home='Амур', away='Лада', sh=1, sa=0, mark='', pick=dict(
        text='ПОБЕДА АМУРА', odds=1.84, hit=True, checks=[('АМУР ВЫИГРАЛ 1:0 В ОСНОВНОЕ ВРЕМЯ', True)]))),
]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, m in PICKS:
        m.update(date=MON, tag='КХЛ')
        path = '%s/pick_khl_%s.jpg' % (OUT, name)
        im2.single(m, path, style='verdict', league='KHL')
        print(path)
