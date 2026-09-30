import os
from PIL import Image
from recap import render_results_day, render_slate

# Итоги 27.09 — все три матча в основное время
RES = [
    dict(home='Адмирал', away='Нефтехимик', sh=3, sa=5, mark=''),
    dict(home='Сибирь', away='Локомотив', sh=1, sa=2, mark=''),
    dict(home='Барыс', away='СКА', sh=3, sa=5, mark=''),
]
p1 = render_results_day(RES, 'out/2709/itogi_2709.png', date_title='воскресенье, 27 сентября')

# Афиша на 28.09 — пять матчей
DAY = [
    ('Авангард', 'Металлург', '16:30 МСК', (2.70, 4.28, 2.44)),
    ('Динамо Минск', 'Лада', '19:10 МСК', (1.50, 5.30, 6.33)),
    ('Шанхайские Драконы', 'Сочи', '19:30 МСК', (1.68, 4.38, 4.79)),
    ('Динамо Москва', 'Трактор', '19:30 МСК', (1.95, 4.10, 3.39)),
    ('Торпедо', 'Салават Юлаев', '19:30 МСК', (2.24, 4.23, 2.97)),
]
os.makedirs('out/2809', exist_ok=True)
p2 = render_slate([dict(home=h, away=a, when=w, odds=o) for h, a, w, o in DAY],
                  'out/2809/afisha_2809.png', date_title='понедельник, 28 сентября')

for p in (p1, p2):
    Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
    os.remove(p)
print('готово')
