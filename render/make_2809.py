import os
os.makedirs('out/2809', exist_ok=True)
from PIL import Image
import poster
from poster import render_cards, team_info, TEAMS

# Разводим пары, где клубные цвета сливаются: берём вторые цвета клубов.
poster.BANNER['Металлург'] = (30, 48, 92)    # тёмно-синий из эмблемы — рядом с красным Авангардом
poster.BANNER['Лада'] = (36, 52, 74)         # графит — рядом с голубым Динамо Минск
poster.BANNER['Сочи'] = (28, 58, 116)        # синий из эмблемы — рядом с оранжевым Шанхаем

M = [
    ('Авангард', 'Металлург', 'ПН 28.09 · 16:30 МСК', (2.70, 4.28, 2.44), (8, 8, 'XXLLX'), (9, 15, 'LWWXW')),
    ('Динамо Минск', 'Лада', 'ПН 28.09 · 19:10 МСК', (1.50, 5.30, 6.33), (8, 8, 'LWWOL'), (9, 5, 'WLOLL')),
    ('Шанхайские Драконы', 'Сочи', 'ПН 28.09 · 19:30 МСК', (1.68, 4.38, 4.79), (6, 8, 'LXLWW'), (8, 2, 'LWLLL')),
    ('Динамо Москва', 'Трактор', 'ПН 28.09 · 19:30 МСК', (1.95, 4.10, 3.39), (10, 10, 'WLLXL'), (7, 4, 'OLLWL')),
    ('Торпедо', 'Салават Юлаев', 'ПН 28.09 · 19:30 МСК', (2.24, 4.23, 2.97), (8, 12, 'WWLWW'), (8, 11, 'LWWOW')),
]
for h, a, when, o, ih, ia in M:
    info = dict(when=when, odds=o, home=team_info(*ih), away=team_info(*ia))
    slug = '%s_%s' % (TEAMS[h][0], TEAMS[a][0])
    p = render_cards(h, a, info, 'out/2809/card_%s.png' % slug)
    Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
    os.remove(p)
    print(h, '—', a, '|', info['home']['line'], '/', info['away']['line'])
