import os
os.makedirs('out/2609', exist_ok=True)
from PIL import Image
from poster import TEAMS
from nhl_style import render_pick_nhl

TEAMS['Миннесота'] = ('minnesota', (21, 71, 52), (166, 25, 46))
TEAMS['Даллас'] = ('dallas', (0, 104, 71), (140, 145, 148))

M = dict(
    league='ПРЕДСЕЗОННЫЙ МАТЧ · СЕНТ-ПОЛ',
    league_tag='NHL',
    home=dict(name='МИННЕСОТА', sub='УАЙЛД', team='Миннесота', color=(20, 66, 48)),
    away=dict(name='ДАЛЛАС', sub='СТАРЗ', team='Даллас', color=(24, 28, 34)),
    note='ВТОРОЙ МАТЧ СЕРИИ · 23.09 ДАЛЛАС ВЫИГРАЛ 2:0',
    when='СБ 26.09 · 03:00 МСК',
    pred='ПОБЕДА МИННЕСОТЫ В ОСНОВНОЕ ВРЕМЯ',
    coef=2.17,
)
p = render_pick_nhl(M, 'out/2609/nhl_pick_minnesota_dallas.png')
Image.open(p).convert('RGB').save('out/2609/nhl_pick_minnesota_dallas.jpg',
                                  quality=95, subsampling=0, optimize=True)
print('готово')
