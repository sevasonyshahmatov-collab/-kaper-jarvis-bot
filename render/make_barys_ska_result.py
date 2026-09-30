import os
from PIL import Image
from poster import team_info
from recap import render_result, GREEN_HIT

# Барыс 3:5 СКА в основное время. После матча: Барыс 10 очков в 9, СКА 14 в 8.
p = render_result('Барыс', 'СКА', 3, 5, 'out/2709/result_barys_ska.png',
                  verdict='ТОТАЛ СКА БОЛЬШЕ 3 — ЗАШЁЛ', verdict_color=GREEN_HIT,
                  when='ВС 27.09 · АСТАНА · РЕГУЛЯРНЫЙ ЧЕМПИОНАТ КХЛ',
                  home_info=team_info(9, 10, 'LWWLL'),
                  away_info=team_info(8, 14, 'LWWWW'))
jpg = p.replace('.png', '.jpg')
Image.open(p).convert('RGB').save(jpg, quality=95, subsampling=0, optimize=True)
os.remove(p)
print('готово')
