import os
from PIL import Image
from poster import team_info
from recap import render_cards_pick

info = dict(when='ВС 27.09 · 15:00 МСК',
            pred='ТОТАЛ СКА БОЛЬШЕ 3', coef=1.84,
            home=team_info(8, 10, 'WLWWL'), away=team_info(7, 12, 'XLWWW'))
p = render_cards_pick('Барыс', 'СКА', 'out/2709/pick_barys_ska.png', info)
jpg = p.replace('.png', '.jpg')
Image.open(p).convert('RGB').save(jpg, quality=95, subsampling=0, optimize=True)
os.remove(p)
print('готово')
