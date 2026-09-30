import os
os.makedirs('out/2609/khl', exist_ok=True)
from PIL import Image
from poster import render_cards, render_clean, team_info, TEAMS

# 26.09, 17:00 МСК. Очки/игры и формы — на момент до матчей.
M = [
    ('Динамо Москва', 'Салават Юлаев', (2.00, 4.30, 3.15), (9, 10, 'WWLLX'), (7, 10, 'LOWWO')),
    ('Шанхайские Драконы', 'Динамо Минск', (2.65, 4.15, 2.30), (5, 6, 'XLXLW'), (7, 8, 'OLWWO')),
    ('Северсталь', 'Сочи', (1.71, 4.65, 4.60), (8, 7, 'LLLWW'), (7, 2, 'LLWLL')),
    ('Спартак', 'Автомобилист', (2.16, 4.30, 3.10), (8, 11, 'WWWLO'), (8, 6, 'WOLLL')),
]
W = 'СБ 26.09 · 17:00 МСК'
for h, a, o, ih, ia in M:
    info = dict(when=W, odds=o, home=team_info(*ih), away=team_info(*ia))
    slug = '%s_%s' % (TEAMS[h][0], TEAMS[a][0])
    p = render_cards(h, a, info, 'out/2609/khl/card_%s.png' % slug)
    Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
    print(h, '—', a, '|', info['home']['line'], '/', info['away']['line'])
