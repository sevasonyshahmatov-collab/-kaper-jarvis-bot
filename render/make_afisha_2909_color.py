import os
from PIL import Image
from poster import BANNER
from recap import render_slate

M = [
    ('Амур', 'Нефтехимик', '12:00 МСК', (2.42, 4.21, 2.70)),
    ('ЦСКА', 'СКА', '19:30 МСК', (1.90, 4.30, 3.40)),
]
p = render_slate([dict(home=h, away=a, when=w, odds=o) for h, a, w, o in M],
                 'out/2909/afisha_2909_color.png', date_title='вторник, 29 сентября',
                 colors=(BANNER['Амур'], BANNER['СКА']))
Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
os.remove(p)
print('готово')
