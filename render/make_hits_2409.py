import os
os.makedirs('out/2509', exist_ok=True)
from poster import BANNER
from recap import render_hits

# Оба прогноза за 24.09 сыграли:
#   Сибирь — Ак Барс 2:3 по буллитам → победа Ак Барса с учётом ОТ и буллитов
#   Спартак — Авангард 1:2 в овертайме → тотал 3 < 5.5
ITEMS = [
    dict(home='Сибирь', away='Ак Барс', score='2:3', mark='Б',
         pred='АК БАРС П2 С ОТ И БУЛЛИТАМИ', coef=1.59, ok=True),
    dict(home='Спартак', away='Авангард', score='1:2', mark='ОТ',
         pred='ТОТАЛ МЕНЬШЕ 5.5', coef=1.70, ok=True),
]

render_hits(ITEMS, 'out/2509/hits_2409.png', '24.09',
            colors=(BANNER['Ак Барс'], BANNER['Спартак']),
            express=1.59 * 1.70)
print('готово')
