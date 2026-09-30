import os
os.makedirs('out/2609/khl', exist_ok=True)
from PIL import Image
from poster import team_info, TEAMS
from recap import render_cards_pick, render_slate

# Прогноз: Барыс — Нефтехимик (перенос с 25.09), 11:00 МСК
info = dict(when='СБ 26.09 · 11:00 МСК',
            pred='ПОБЕДА БАРЫСА С ОТ И БУЛЛИТАМИ', coef=1.75,
            home=team_info(7, 10, 'LWLWW'), away=team_info(8, 11, 'WWLLW'))
p = render_cards_pick('Барыс', 'Нефтехимик', 'out/2609/khl/card_pick_barys_neftekhimik.png', info)
Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
print('прогноз готов')

# Афиша дня: шесть матчей 26.09
DAY = [
    ('Барыс', 'Нефтехимик', '11:00 МСК', (2.31, 4.34, 2.80)),
    ('Металлург', 'Ак Барс', '14:30 МСК', (1.75, 4.30, 3.95)),
    ('Динамо Москва', 'Салават Юлаев', '17:00 МСК', (2.00, 4.30, 3.15)),
    ('Шанхайские Драконы', 'Динамо Минск', '17:00 МСК', (2.65, 4.15, 2.30)),
    ('Северсталь', 'Сочи', '17:00 МСК', (1.71, 4.65, 4.60)),
    ('Спартак', 'Автомобилист', '17:00 МСК', (2.16, 4.30, 3.10)),
]
p = render_slate([dict(home=h, away=a, when=w, odds=o) for h, a, w, o in DAY],
                 'out/2609/khl/afisha_2609.png', date_title='суббота, 26 сентября')
Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
print('афиша готова')
