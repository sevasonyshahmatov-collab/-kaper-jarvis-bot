import os
from PIL import Image
from poster import BANNER
from recap import render_slate

M = [
    ('Амур', 'Нефтехимик', '12:00 МСК', (2.42, 4.21, 2.70)),
    ('ЦСКА', 'СКА', '19:30 МСК', (1.90, 4.30, 3.40)),
]
items = [dict(home=h, away=a, when=w, odds=o) for h, a, w, o in M]

VARIANTS = {
    'red_orange': (BANNER['Амур'], (205, 25, 40)),          # оранжевый Амура → красный ЦСКА/СКА
    'red_blue': (BANNER['Нефтехимик'], (205, 25, 40)),      # синий Нефтехимика → красный ЦСКА/СКА
}
for name, colors in VARIANTS.items():
    p = render_slate(items, 'out/2909/afisha_%s.png' % name,
                     date_title='вторник, 29 сентября', colors=colors)
    Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
    os.remove(p)
    print(name, 'ok')

sheet = Image.new('RGB', (1100, 2 * 700), (16, 20, 28))
for i, n in enumerate(('red_orange', 'red_blue')):
    im = Image.open('out/2909/afisha_%s.jpg' % n)
    sheet.paste(im.resize((1040, 660), Image.LANCZOS), (30, 20 + i * 700))
sheet.save('out/2909/_sheet_red.png')
