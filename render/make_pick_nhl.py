import os
os.makedirs('out/2609', exist_ok=True)
from PIL import Image
import poster
from poster import TEAMS
from recap import render_pick

# Клубы НХЛ с присланными эмблемами — регистрируем как обычные команды набора.
TEAMS['Миннесота'] = ('minnesota', (21, 71, 52), (166, 25, 46))
TEAMS['Даллас'] = ('dallas', (0, 104, 71), (140, 145, 148))
poster.BANNER['Миннесота'] = (24, 84, 58)
poster.BANNER['Даллас'] = (0, 104, 71)

# НХЛ, предсезонка: Миннесота — Даллас, 25.09 19:00 CDT = 26.09 03:00 МСК.
# 23.09 в Далласе тот же соперник выиграл 2:0 в основное время.
M = dict(
    league='НХЛ · ПРЕДСЕЗОННЫЙ МАТЧ',
    home=dict(name='МИННЕСОТА', sub='УАЙЛД', code='MIN', team='Миннесота',
              color=(21, 71, 52), edge=(234, 170, 0)),
    away=dict(name='ДАЛЛАС', sub='СТАРЗ', code='DAL', team='Даллас',
              color=(0, 104, 71), edge=(176, 182, 186)),
    note='ВТОРОЙ МАТЧ СЕРИИ · 23.09 ДАЛЛАС ВЫИГРАЛ 2:0',
    when='СБ 26.09 · 03:00 МСК',
    pred='ПОБЕДА МИННЕСОТЫ В ОСНОВНОЕ ВРЕМЯ',
    coef=2.17,
    colors=((24, 84, 58), (34, 50, 58)),
)
p = render_pick(M, 'out/2609/pick_minnesota_dallas.png')
Image.open(p).convert('RGB').save('out/2609/pick_minnesota_dallas.jpg',
                                  quality=95, subsampling=0, optimize=True)
print('готово')
