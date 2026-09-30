from PIL import Image
import poster
from poster import render_cards, team_info, TEAMS

# У Сочи и Автомобилиста берём вторые клубные цвета: иначе половины сливаются
# с хозяевами (жёлтый на жёлтом, красный на красном) и шапка канала пропадает.
poster.BANNER['Сочи'] = (28, 58, 116)        # синий из эмблемы Сочи
poster.BANNER['Автомобилист'] = (38, 42, 48)  # графит из эмблемы Автомобилиста

M = [
    ('Северсталь', 'Сочи', (1.71, 4.65, 4.60), (8, 7, 'LLLWW'), (7, 2, 'LLWLL')),
    ('Спартак', 'Автомобилист', (2.16, 4.30, 3.10), (8, 11, 'WWWLO'), (8, 6, 'WOLLL')),
]
for h, a, o, ih, ia in M:
    info = dict(when='СБ 26.09 · 17:00 МСК', odds=o, home=team_info(*ih), away=team_info(*ia))
    slug = '%s_%s' % (TEAMS[h][0], TEAMS[a][0])
    p = render_cards(h, a, info, 'out/2609/khl/card_%s.png' % slug)
    Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
    print(h, '—', a, 'перерисован')
