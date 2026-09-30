import os
os.makedirs('out/3009', exist_ok=True)
from PIL import Image
import poster
from poster import render_cards, team_info, TEAMS
from recap import render_slate

# Металлург рядом с Шанхаем — обе оранжевые, уводим Магнитку в синий из эмблемы.
poster.BANNER['Металлург'] = (30, 48, 92)

M = [
    ('Автомобилист', 'Лада',     'СР 30.09 · 17:00 МСК', (1.57, 5.20, 5.60), (9, 8, 'OLLLW'),  (10, 5, 'LOLLL')),
    ('Ак Барс', 'Барыс',         'СР 30.09 · 19:00 МСК', (1.80, 4.20, 3.90), (10, 13, 'XLXXL'), (9, 10, 'LWWLL')),
    ('Спартак', 'Трактор',       'СР 30.09 · 19:30 МСК', (1.84, 4.37, 3.91), (9, 11, 'WWLOL'),  (8, 6, 'LLWLX')),
    ('Сочи', 'Салават Юлаев',    'СР 30.09 · 19:30 МСК', (4.60, 4.65, 1.74), (9, 2, 'WLLLL'),   (9, 13, 'WWOWW')),
    ('Локомотив', 'Сибирь',      'СР 30.09 · 19:30 МСК', (1.61, 4.80, 5.53), (10, 16, 'WLWLW'), (9, 6, 'LLWOL')),
    ('Шанхайские Драконы', 'Металлург', 'СР 30.09 · 19:30 МСК', (4.30, 4.40, 1.67), (7, 10, 'XLWWW'), (10, 17, 'WWXWW')),
]
paths = []
for h, a, when, o, ih, ia in M:
    info = dict(when=when, odds=o, home=team_info(*ih), away=team_info(*ia))
    slug = '%s_%s' % (TEAMS[h][0], TEAMS[a][0])
    paths.append(render_cards(h, a, info, 'out/3009/card_%s.png' % slug))
    print(h, '—', a, '|', info['home']['line'], '/', info['away']['line'])

paths.append(render_slate([dict(home=h, away=a, when=w.split('· ')[1], odds=o) for h, a, w, o, _, _ in M],
                          'out/3009/afisha_3009.png', date_title='среда, 30 сентября',
                          colors=(poster.BANNER['Автомобилист'], (34, 62, 118))))
for p in paths:
    Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
    os.remove(p)
print('готово')
