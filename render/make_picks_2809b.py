import os
from PIL import Image
from recap import render_picks

ITEMS = [
    dict(home='Шанхайские Драконы', away='Сочи', pred='ШАНХАЙ ФОРА (0)', coef=1.79, when='19:30'),
    dict(home='Торпедо', away='Салават Юлаев', pred='ИТ САЛАВАТА ЮЛАЕВА БОЛЬШЕ 2.5', coef=1.80, when='19:30'),
]
p = render_picks(ITEMS, 'out/2809/picks_2809_v2.png', 'понедельник, 28 сентября',
                 express=1.79 * 1.80, title='ДВОЙНОЙ ПРОГНОЗ')
Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
os.remove(p)
print('готово')
