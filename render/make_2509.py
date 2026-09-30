import os
os.makedirs('out/2509', exist_ok=True)

import poster
from poster import render_clean, render_cards, team_info, TEAMS
from recap import render_recap, render_slate

# «Куньлунь Ред Стар» — прежнее имя шанхайского клуба: берём его эмблему и цвета.
TEAMS['Куньлунь Ред Стар'] = TEAMS['Шанхайские Драконы']
poster.BANNER['Куньлунь Ред Стар'] = poster.BANNER['Шанхайские Драконы']
poster.SHORT['Куньлунь Ред Стар'] = 'Куньлунь'

# ---------- 1. Итоги дня: восемь прогнозов на одном баннере ----------
RECAP = [
    dict(home='Сибирь', away='Барыс', pred='Победа «Сибири» в основное время', coef=1.75, ok=True, score='2:1'),
    dict(home='Трактор', away='Адмирал', pred='Тотал меньше 4.5', coef=1.82, ok=True, score='1:0'),
    dict(home='Салават Юлаев', away='Сочи', pred='Тотал больше 5.5', coef=1.90, ok=False, score='2:1'),
    dict(home='Динамо Минск', away='Автомобилист', pred='Тотал больше 4.5', coef=1.78, ok=True, score='8:2'),
    dict(home='Локомотив', away='Металлург', pred='Победа «Локомотива» в основное время', coef=1.95, ok=True, score='4:1'),
    dict(home='СКА', away='Куньлунь Ред Стар', pred='Победа СКА с форой (-1.5)', coef=1.75, ok=True, score='5:1'),
    dict(home='Динамо Москва', away='Ак Барс', pred='Тотал меньше 5.5', coef=1.85, ok=False, score='5:7'),
    dict(home='Спартак', away='Нефтехимик', pred='Победа «Спартака» в основное время', coef=1.70, ok=False, score='2:3'),
]
render_recap(RECAP, 'out/2509/itogi_dnya.png')
print('итоги дня — готово')

# ---------- 2. Матчи 25.09 ----------
TODAY = [
    ('Амур', 'Локомотив', 'ПТ 25.09 · 12:00 МСК', (4.60, 4.50, 1.75), (7, 5, 'LWWLL'), (8, 14, 'WWWLW')),
    ('Трактор', 'СКА', 'ПТ 25.09 · 17:00 МСК', (2.65, 4.30, 2.25), (6, 4, 'OOLLW'), (6, 10, 'WXLWW')),
    ('Барыс', 'Нефтехимик', 'ПТ 25.09 · 17:30 МСК', (2.31, 4.34, 2.80), (7, 10, 'LWLWW'), (8, 11, 'WWLLW')),
    ('Лада', 'ЦСКА', 'ПТ 25.09 · 18:00 МСК', (5.20, 4.60, 1.55), (8, 5, 'LWLOL'), (8, 10, 'LWWXW')),
]

# ---------- 3. Сибирь — Ак Барс (24.09), результат не учитываем ----------
EXTRA = [
    ('Сибирь', 'Ак Барс', 'ЧТ 24.09 · 15:30 МСК', (2.80, 4.20, 2.17), (7, 5, 'WLLLW'), (8, 11, 'OLXLX')),
]

for h, a, when, o, ih, ia in TODAY + EXTRA:
    info = dict(when=when, odds=o, home=team_info(*ih), away=team_info(*ia))
    slug = '%s_%s' % (TEAMS[h][0], TEAMS[a][0])
    render_cards(h, a, info, 'out/2509/card_%s.png' % slug)
    render_clean(h, a, info, 'out/2509/side_%s.png' % slug)
    print(h, '—', a, '|', info['home']['line'], '/', info['away']['line'])

# ---------- 4. Афиша дня: все четыре матча на одном баннере ----------
render_slate([dict(home=h, away=a, when=when.split('· ')[1], odds=o)
              for h, a, when, o, ih, ia in TODAY],
             'out/2509/afisha_2509.png', date_title='пятница, 25 сентября')
print('афиша дня — готово')
