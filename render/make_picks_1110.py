"""Послематчевые баннеры к прогнозам (ice_more2, style='verdict'): КХЛ 10 октября и НХЛ, игровой день 10 октября
(по Москве — вечер 10.10 и ночь на 11.10).

КХЛ — счёт из таблицы (сверена с приложением КХЛ); Адмирал — Лада 4:3 — овертайм (Спорт-Экспресс, Metaratings: 3:3
в основное время, решил Завгородний). НХЛ — таблица результаты ещё не подтянула; по отчётам NHL.com, ESPN и клубов:
Бостон — Филадельфия 5:1, Нью-Джерси — Ванкувер 4:1, Сан-Хосе — Эдмонтон 1:3, Флорида — Миннесота 1:4,
Чикаго — Каролина 2:5, Колорадо — Торонто 3:6, Калгари — Анахайм 2:4, Вегас — Лос-Анджелес 2:1 ОТ (Марнер в большинстве).
Разница в счёте 2+ — значит, основное время. Прогнозы и кэфы — от владельца канала; у Сан-Хосе — Эдмонтон кэф не указан.
Запуск из папки render: python make_picks_1110.py [папка] → pick_*.jpg (по умолчанию out/1110)
"""
import os
import sys

import ice_more2 as im2
import nhl

nhl.register()

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out/1110'
SAT, SUN = 'суббота, 10 октября', 'воскресенье, 11 октября'


def goals(n):
    return '%d %s' % (n, 'ГОЛ' if n % 10 == 1 and n % 100 != 11 else 'ГОЛА' if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else 'ГОЛОВ')


def total(sh, sa, mark=''):
    return '%d:%d%s — %s В МАТЧЕ' % (sh, sa, ' ' + mark if mark else '', goals(sh + sa))


NHL = [
    ('boston_philadelphia', SAT, dict(home='Бостон', away='Филадельфия', sh=5, sa=1, mark='', pick=dict(
        text='ПОБЕДА БОСТОНА', odds=2.21, hit=True, checks=[('БОСТОН ВЫИГРАЛ 5:1', True)]))),
    ('newjersey_vancouver', SAT, dict(home='Нью-Джерси', away='Ванкувер', sh=4, sa=1, mark='', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 6', odds=1.91, hit=False, checks=[(total(4, 1), False)]))),
    ('sanjose_edmonton', SAT, dict(home='Сан-Хосе', away='Эдмонтон', sh=1, sa=3, mark='', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 6', odds=None, hit=False, checks=[(total(1, 3), False)]))),
    ('florida_minnesota', SUN, dict(home='Флорида', away='Миннесота', sh=1, sa=4, mark='', pick=dict(
        text='ТОТАЛ МАТЧА МЕНЬШЕ 6', odds=1.67, hit=True, checks=[(total(1, 4), True)]))),
    ('chicago_carolina', SUN, dict(home='Чикаго', away='Каролина', sh=2, sa=5, mark='', pick=dict(
        text='ПОБЕДА КАРОЛИНЫ', odds=1.66, hit=True, checks=[('КАРОЛИНА ВЫИГРАЛА 5:2', True)]))),
    ('colorado_toronto', SUN, dict(home='Колорадо', away='Торонто', sh=3, sa=6, mark='', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 6,5', odds=2.08, hit=True, checks=[(total(3, 6), True)]))),
    ('calgary_anaheim', SUN, dict(home='Калгари', away='Анахайм', sh=2, sa=4, mark='', pick=dict(
        text='ПОБЕДА АНАХАЙМА С УЧЁТОМ ОТ', odds=1.87, hit=True, checks=[('АНАХАЙМ ВЫИГРАЛ 4:2', True)]))),
    ('vegas_losangeles', SUN, dict(home='Вегас', away='Лос-Анджелес', sh=2, sa=1, mark='ОТ', pick=dict(
        text='ТОТАЛ МАТЧА БОЛЬШЕ 5,5', odds=1.75, hit=False, checks=[(total(2, 1, 'ОТ'), False)]))),
]
KHL = [
    ('admiral_lada', SAT, dict(home='Адмирал', away='Лада', sh=4, sa=3, mark='ОТ', pick=dict(
        text='ИТОГОВАЯ ПОБЕДА АДМИРАЛА', odds=1.67, hit=True, checks=[('АДМИРАЛ ВЫИГРАЛ В ОВЕРТАЙМЕ 4:3', True)]))),
    ('barys_avangard', SAT, dict(home='Барыс', away='Авангард', sh=5, sa=1, mark='', pick=dict(
        text='ИНДИВИДУАЛЬНЫЙ ТОТАЛ БАРЫСА БОЛЬШЕ 2,5', odds=1.79, hit=True, checks=[('БАРЫС ЗАБИЛ 5 ГОЛОВ', True)]))),
    ('akbars_severstal', SAT, dict(home='Ак Барс', away='Северсталь', sh=1, sa=4, mark='', pick=dict(
        text='ТОТАЛ МАТЧА МЕНЬШЕ 6', odds=1.52, hit=True, checks=[(total(1, 4), True)]))),
    ('lokomotiv_dinamominsk', SAT, dict(home='Локомотив', away='Динамо Минск', sh=6, sa=1, mark='', pick=dict(
        text='ПОБЕДА ЛОКОМОТИВА И ТОТАЛ МЕНЬШЕ 5,5', odds=2.12, hit=False,
        checks=[('ЛОКОМОТИВ ВЫИГРАЛ 6:1', True), ('7 ГОЛОВ — ТОТАЛ БОЛЬШЕ 5,5', False)]))),
]

os.makedirs(OUT, exist_ok=True)
for tag, league, banners in (('НХЛ', 'NHL', NHL), ('КХЛ', 'KHL', KHL)):
    for name, date, m in banners:
        m.update(date=date, tag=tag)
        path = '%s/pick_%s_%s.jpg' % (OUT, league.lower(), name)
        im2.single(m, path, style='verdict', league=league)
        print(path)
