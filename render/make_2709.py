import os
os.makedirs('out/2709', exist_ok=True)
from PIL import Image
from poster import render_cards, team_info, TEAMS
from recap import render_slate

# 27.09. Данные — на момент до матчей, с учётом вчерашнего тура.
# Адмирал — Нефтехимик перенесён на два часа позже, старт в 12:00 МСК.
M = [
    ('Адмирал', 'Нефтехимик', 'ВС 27.09 · 12:00 МСК', (2.47, 4.21, 2.75), (8, 6, 'LLWOL'), (9, 13, 'WLLWW')),
    ('Сибирь', 'Локомотив', 'ВС 27.09 · 13:30 МСК', (4.60, 4.48, 1.74), (8, 6, 'LLLWO'), (9, 14, 'WWLWL')),
    ('Барыс', 'СКА', 'ВС 27.09 · 15:00 МСК', (3.08, 4.32, 2.22), (8, 10, 'WLWWL'), (7, 12, 'XLWWW')),
]
paths = []
for h, a, when, o, ih, ia in M:
    info = dict(when=when, odds=o, home=team_info(*ih), away=team_info(*ia))
    slug = '%s_%s' % (TEAMS[h][0], TEAMS[a][0])
    p = render_cards(h, a, info, 'out/2709/card_%s.png' % slug)
    jpg = p.replace('.png', '.jpg')
    Image.open(p).convert('RGB').save(jpg, quality=95, subsampling=0, optimize=True)
    os.remove(p)
    paths.append(jpg)
    print(h, '—', a, '|', info['home']['line'], '/', info['away']['line'])

p = render_slate([dict(home=h, away=a, when=w.split('· ')[1], odds=o) for h, a, w, o, _, _ in M],
                 'out/2709/afisha_2709.png', date_title='воскресенье, 27 сентября')
jpg = p.replace('.png', '.jpg')
Image.open(p).convert('RGB').save(jpg, quality=95, subsampling=0, optimize=True)
os.remove(p)
print('афиша готова')
