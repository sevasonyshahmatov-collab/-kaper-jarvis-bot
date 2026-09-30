import os
os.makedirs('out/2609/pack10', exist_ok=True)
from PIL import Image
from poster import TEAMS
import nhl_pack10 as p10

TEAMS['Миннесота'] = ('minnesota', (21, 71, 52), (166, 25, 46))
TEAMS['Даллас'] = ('dallas', (0, 104, 71), (140, 145, 148))

M = dict(
    league='НХЛ · ПРЕДСЕЗОНКА',
    home=dict(name='МИННЕСОТА', sub='УАЙЛД', code='MIN', team='Миннесота', color=(20, 66, 48)),
    away=dict(name='ДАЛЛАС', sub='СТАРЗ', code='DAL', team='Даллас', color=(26, 32, 40)),
    note='23.09 ДАЛЛАС ВЫИГРАЛ 2:0',
    when='СБ 26.09 · 03:00 МСК',
    pred='ПОБЕДА МИННЕСОТЫ В ОСНОВНОЕ ВРЕМЯ',
    coef=2.17,
)

out = 'out/2609/pack10'
jobs = [('06_board', p10.render_board), ('07_paper', p10.render_paper), ('08_minimal', p10.render_minimal),
        ('09_neon', p10.render_neon), ('10_stripe', p10.render_stripe), ('11_sticker', p10.render_sticker),
        ('12_terminal', p10.render_terminal), ('13_magazine', p10.render_magazine),
        ('14_card', p10.render_card), ('15_app', p10.render_app)]
paths = []
for name, fn in jobs:
    try:
        pth = fn(M, '%s/nhl_%s.png' % (out, name))
        Image.open(pth).convert('RGB').save(pth.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
        paths.append(pth)
        print(name, 'ok')
    except Exception as e:
        print(name, 'FAIL', type(e).__name__, e)

for part in (0, 1):
    grp = paths[part * 5:(part + 1) * 5]
    if not grp:
        continue
    sheet = Image.new('RGB', (1300, len(grp) * 340 + 20), (18, 22, 30))
    for i, pth in enumerate(grp):
        sheet.paste(Image.open(pth).resize((1280, 320), Image.LANCZOS), (10, 10 + i * 340))
    sheet.save('%s/_sheet%d.png' % (out, part + 1))
print('sheets ok')
