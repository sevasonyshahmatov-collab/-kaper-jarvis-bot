import os
os.makedirs('out/2609/variants', exist_ok=True)
from PIL import Image
from poster import TEAMS
import nhl_variants as nv

TEAMS['Миннесота'] = ('minnesota', (21, 71, 52), (166, 25, 46))
TEAMS['Даллас'] = ('dallas', (0, 104, 71), (140, 145, 148))

M = dict(
    league='НХЛ · ПРЕДСЕЗОНКА',
    league_tag='NHL',
    home=dict(name='МИННЕСОТА', sub='УАЙЛД', team='Миннесота',
              color=(20, 66, 48), stripe=(233, 205, 150)),
    away=dict(name='ДАЛЛАС', sub='СТАРЗ', team='Даллас',
              color=(24, 28, 34), stripe=(150, 158, 164)),
    note='ВТОРОЙ МАТЧ СЕРИИ · 23.09 ДАЛЛАС ВЫИГРАЛ 2:0',
    when='СБ 26.09 · 03:00 МСК',
    pred='ПОБЕДА МИННЕСОТЫ В ОСНОВНОЕ ВРЕМЯ',
    coef=2.17,
    stats=[('ПОСЛЕДНИЙ ОЧНЫЙ · 23.09', 'ДАЛЛАС 2:0'),
           ('ПРЕДСЕЗОНКА МИННЕСОТЫ', '1 ПОБЕДА В 3 МАТЧАХ'),
           ('РЕШЕНО В ОСНОВНОЕ ВРЕМЯ', '1 ИЗ 3 МАТЧЕЙ')],
)

out = 'out/2609/variants'
jobs = [('1_rink', nv.render_rink), ('2_jersey', nv.render_jersey), ('3_ticker', nv.render_ticker),
        ('4_poster', nv.render_poster), ('5_ticket', nv.render_ticket)]
paths = []
for name, fn in jobs:
    p = fn(M, '%s/nhl_%s.png' % (out, name))
    Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
    paths.append(p)
    print(name, 'ok')

# контактный лист для просмотра
sheet = Image.new('RGB', (1300, 5 * 340 + 20), (18, 22, 30))
for i, p in enumerate(paths):
    im = Image.open(p).resize((1280, 640), Image.LANCZOS).resize((1280, 320), Image.LANCZOS)
    sheet.paste(im, (10, 10 + i * 340))
sheet.save('out/2609/variants/_sheet.png')
print('sheet ok')
