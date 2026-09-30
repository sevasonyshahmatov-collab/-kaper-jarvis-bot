import os
os.makedirs('out/2609/side', exist_ok=True)
from PIL import Image
import poster
from poster import TEAMS
from side_pick import render_side_pick, ICE

TEAMS['Миннесота'] = ('minnesota', (21, 71, 52), (166, 25, 46))
TEAMS['Даллас'] = ('dallas', (0, 104, 71), (140, 145, 148))
poster.BANNER['Миннесота'] = (24, 96, 62)
poster.BANNER['Даллас'] = (32, 44, 54)

# Предсезонка в московских датах: у Миннесоты 20.09 победа в ОТ, 22.09 поражение в ОТ,
# 24.09 поражение 0:2 в основное. У Далласа три победы в основное время.
M = dict(
    home=dict(team='Миннесота', name='МИННЕСОТА', line='1 победа в 3 матчах', form='XOL'),
    away=dict(team='Даллас', name='ДАЛЛАС', line='3 победы в 3 матчах', form='WWW'),
    when='СБ 26.09 · 03:00 МСК',
    pred='ПОБЕДА МИННЕСОТЫ С ОТ И БУЛЛИТАМИ',
    coef=1.81,
)

for name, acc, tag in (('gold', None, 'NHL'), ('ice', ICE, 'NHL')):
    p = render_side_pick(M, 'out/2609/side/nhl_side_ot_%s.png' % name, accent=acc, tag=tag)
    Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
    print(name, 'ok')

sheet = Image.new('RGB', (1300, 2 * 660 + 20), (18, 22, 30))
for i, n in enumerate(('gold', 'ice')):
    sheet.paste(Image.open('out/2609/side/nhl_side_ot_%s.png' % n), (10, 10 + i * 660))
sheet.save('out/2609/side/_sheet.png')
print('sheet ok')
