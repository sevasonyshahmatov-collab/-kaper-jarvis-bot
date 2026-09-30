# -*- coding: utf-8 -*-
"""Шаблон скрипта на игровой день НХЛ. Скопировать, подставить свои данные.

ПЕРЕД РЕНДЕРОМ каждая строка команды проверяется: очки == 2*победы + поражения в ОТ.
Не сошлось — скрипт падает, а не рисует неверный баннер.
"""
import os

import nhl
import nhl_kit
from nhl import team_info

nhl.register()
DAY = '0110'
DATE = 'ЧТ 01.10'
DATE_LONG = 'четверг, 1 октября'
O = 'out/nhl_%s/' % DAY
os.makedirs(O, exist_ok=True)


def check(name, gp, pts, form):
    """Сверка с таблицей: победа 2, поражение в ОТ/буллитах 1, в основное 0."""
    wins = form.count('W') + form.count('X')
    otl = form.count('O')
    if len(form) > 5:
        raise ValueError('%s: форма длиннее пяти матчей' % name)
    if len(form) == gp and pts != 2 * wins + otl:
        raise ValueError('%s: %d очков не сходится с формой %s (ожидалось %d)'
                         % (name, pts, form, 2 * wins + otl))
    return team_info(gp, pts, form)


# (хозяева, гости, время МСК, (П1, Х, П2), (игры, очки, форма), (игры, очки, форма))
M = [
    ('Бостон', 'Торонто', '03:00', (2.05, 3.95, 3.30), (4, 6, 'WLXW'), (4, 5, 'WWOL')),
    ('Каролина', 'Нью-Джерси', '02:30', (1.90, 4.05, 3.75), (4, 6, 'WWLW'), (4, 3, 'LWOL')),
]

paths = []
for h, a, when, odds, ih, ia in M:
    info = dict(when='%s · %s МСК' % (DATE, when), odds=odds,
                home=check(h, *ih), away=check(a, *ia))
    slug = '%s_%s' % (nhl.TEAMS[nhl.resolve(h)][3], nhl.TEAMS[nhl.resolve(a)][3])
    paths.append(nhl_kit.preview(h, a, info, O + 'card_%s.png' % slug.lower()))

paths.append(nhl_kit.slate(
    [dict(home=h, away=a, when=w + ' МСК', odds=o) for h, a, w, o, _, _ in M],
    O + 'afisha_%s.png' % DAY, date_title=DATE_LONG))

for p in paths:
    print('готово', nhl_kit._jpg(p))
