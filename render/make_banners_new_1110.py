"""Примеры новых баннеров (banners_new) на прогнозах владельца на игровой день 10 октября.

До матча — прогнозы и кэфы владельца, время — с листа «Прогнозы — кратко» (как make_picks_pre_1010.py);
после матча — счета и разбор из make_picks_1110.py. Итог дня по прогнозам: 8 из 12.
Запуск из папки render: python make_banners_new_1110.py [папка] [стиль,стиль] → new_*.jpg (по умолчанию out/new1110)
"""
import os
import sys

import banners_new as B
import nhl

nhl.register()

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out/new1110'
ONLY = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
SAT, SUN = ('СБ 10.10', 'суббота, 10 октября'), ('ВС 11.10', 'воскресенье, 11 октября')


def M(league, home, away, day, time, pick, odds, sh=None, sa=None, mark='', hit=None):
    return dict(league=league, home=home, away=away, day=day[0], date_long=day[1], time=time, pick=pick, odds=odds,
                sh=sh, sa=sa, mark=mark, hit=hit)


NHL = [
    M('NHL', 'Бостон', 'Филадельфия', SAT, '20:00', 'ПОБЕДА БОСТОНА', 2.21, 5, 1, '', True),
    M('NHL', 'Нью-Джерси', 'Ванкувер', SAT, '22:30', 'ТОТАЛ МАТЧА БОЛЬШЕ 6', 1.91, 4, 1, '', False),
    M('NHL', 'Сан-Хосе', 'Эдмонтон', SAT, '23:00', 'ТОТАЛ МАТЧА БОЛЬШЕ 6', None, 1, 3, '', False),
    M('NHL', 'Флорида', 'Миннесота', SUN, '01:00', 'ТОТАЛ МАТЧА МЕНЬШЕ 6', 1.67, 1, 4, '', True),
    M('NHL', 'Чикаго', 'Каролина', SUN, '02:00', 'ПОБЕДА КАРОЛИНЫ', 1.66, 2, 5, '', True),
    M('NHL', 'Колорадо', 'Торонто', SUN, '02:00', 'ТОТАЛ МАТЧА БОЛЬШЕ 6,5', 2.08, 3, 6, '', True),
    M('NHL', 'Калгари', 'Анахайм', SUN, '05:00', 'ПОБЕДА АНАХАЙМА С УЧЁТОМ ОТ', 1.87, 2, 4, '', True),
    M('NHL', 'Вегас', 'Лос-Анджелес', SUN, '05:00', 'ТОТАЛ МАТЧА БОЛЬШЕ 5,5', 1.75, 2, 1, 'ОТ', False),
]
KHL = [
    M('KHL', 'Адмирал', 'Лада', SAT, '10:00', 'ИТОГОВАЯ ПОБЕДА АДМИРАЛА', 1.67, 4, 3, 'ОТ', True),
    M('KHL', 'Барыс', 'Авангард', SAT, '14:30', 'ИНДИВИДУАЛЬНЫЙ ТОТАЛ БАРЫСА БОЛЬШЕ 2,5', 1.79, 5, 1, '', True),
    M('KHL', 'Ак Барс', 'Северсталь', SAT, '17:00', 'ТОТАЛ МАТЧА МЕНЬШЕ 6', 1.52, 1, 4, '', True),
    M('KHL', 'Локомотив', 'Динамо Минск', SAT, '17:00', 'ПОБЕДА ЛОКОМОТИВА И ТОТАЛ МЕНЬШЕ 5,5', 2.12, 6, 1, '', False),
]
by = {(x['home']): x for x in NHL + KHL}

JOBS = [
    ('stamp', 'new_stamp_colorado_toronto.jpg', lambda p: B.stamp(by['Колорадо'], p)),
    ('stamp', 'new_stamp_vegas_losangeles.jpg', lambda p: B.stamp(by['Вегас'], p)),
    ('afisha', 'new_afisha_boston_philadelphia.jpg', lambda p: B.afisha(by['Бостон'], p)),
    ('afisha', 'new_afisha_akbars_severstal.jpg', lambda p: B.afisha(by['Ак Барс'], p)),
    ('diary', 'new_diary_1010.jpg', lambda p: B.diary(dict(khl=KHL, nhl=NHL, khl_title='КХЛ · суббота, 10 октября',
                                                            nhl_title='НХЛ · ночь на 11 октября'), p)),
    ('teletext', 'new_teletext_nhl_1010.jpg', lambda p: B.teletext(dict(
        items=NHL, title='НХЛ · ПРОГНОЗЫ НА НОЧЬ', day='СБ 10 ОКТ', clock='19:58:12'), p)),
    ('neon', 'new_neon_chicago_carolina.jpg', lambda p: B.neon(dict(by['Чикаго'], side='a', pick_script='Победа Каролины'), p)),
    ('neon', 'new_neon_lokomotiv_dinamo.jpg', lambda p: B.neon(dict(by['Локомотив'], side='h',
                                                                     pick_script='Локомотив и меньше 5,5'), p)),
    ('comic', 'new_comic_calgary_anaheim.jpg', lambda p: B.comic(by['Калгари'], p)),
    ('comic', 'new_comic_newjersey_vancouver.jpg', lambda p: B.comic(by['Нью-Джерси'], p)),
    ('blueprint', 'new_blueprint_florida_minnesota.jpg', lambda p: B.blueprint(by['Флорида'], p)),
    ('blueprint', 'new_blueprint_sanjose_edmonton.jpg', lambda p: B.blueprint(by['Сан-Хосе'], p)),
    ('swiss', 'new_swiss_barys_avangard.jpg', lambda p: B.swiss(by['Барыс'], p)),
    ('swiss', 'new_swiss_calgary_anaheim.jpg', lambda p: B.swiss(by['Калгари'], p)),
    ('vinyl', 'new_vinyl_admiral_lada.jpg', lambda p: B.vinyl(dict(by['Адмирал'], side='h'), p)),
    ('vinyl', 'new_vinyl_boston_philadelphia.jpg', lambda p: B.vinyl(dict(by['Бостон'], side='h'), p)),
]

os.makedirs(OUT, exist_ok=True)
for style, name, fn in JOBS:
    if ONLY and style not in ONLY:
        continue
    print(fn(os.path.join(OUT, name)))
