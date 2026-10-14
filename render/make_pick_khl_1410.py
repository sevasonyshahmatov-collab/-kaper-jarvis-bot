"""Послематчевый баннер (ice_more2, style='verdict') к прогнозу владельца на КХЛ, 14 октября:
Амур — Спартак, «тотал матча меньше 5,5»; Салават Юлаев — Сибирь, «тотал матча больше 4,5»; ЦСКА — Динамо Москва,
«победа ЦСКА» 1.91.

Счёт 1:2 (победа Спартака) — со слов владельца; итоговые отчёты на момент отрисовки не проиндексированы, второй источник
не найден. Был ли ОТ/буллиты, неизвестно — поэтому mark=None (без приписки про время). На исход ставки не влияет:
3 шайбы, и даже с победным буллитом тотал меньше 5,5. Кэф владелец не назвал — odds=None.
Салават Юлаев — Сибирь 2:4 (победа Сибири) — со слов владельца; хозяева — Салават (матч на «Уфа-Арене», превью
sportmail.ru). Итоговый отчёт к моменту отрисовки не проиндексирован. Разница в две шайбы — значит, без ОТ и буллитов
(mark=''). Кэф владелец не назвал — odds=None.
ЦСКА — Динамо Москва 1:0 (Полтапов, 48-я минута, основное время) — Спорт-Экспресс, LiveSport, Metaratings, 14.10.
Запуск: python render/make_pick_khl_1410.py [папка] → pick_khl_*.jpg (по умолчанию out/1410)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ice_more2 as im2  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out/1410'
DAY = 'среда, 14 октября'

PICKS = [
    ('amur_spartak', dict(home='Амур', away='Спартак', sh=1, sa=2, mark=None, pick=dict(
        text='ТОТАЛ МАТЧА МЕНЬШЕ 5,5', odds=None, hit=True, checks=[('1:2 — 3 ШАЙБЫ В МАТЧЕ', True)]))),
    ('salavat_sibir', dict(home='Салават Юлаев', away='Сибирь', sh=2, sa=4, mark='', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 4,5', odds=None, hit=True, checks=[('2:4 — 6 ШАЙБ В МАТЧЕ', True)]))),
    ('cska_dinamo', dict(home='ЦСКА', away='Динамо Москва', sh=1, sa=0, mark='', pick=dict(
        text='ПОБЕДА ЦСКА', odds=1.91, hit=True, checks=[('1:0 — ПОБЕДА ЦСКА В ОСНОВНОЕ ВРЕМЯ', True)]))),
]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, m in PICKS:
        m.update(date=DAY, tag='КХЛ')
        path = '%s/pick_khl_%s.jpg' % (OUT, name)
        im2.single(m, path, style='verdict', league='KHL')
        print(path)
