import os
from PIL import Image
from poster import team_info
from recap import render_result, GREEN_HIT

# Амур 1:0 Нефтехимик в основное время. После матча: Амур 9 очков в 9, Нефтехимик 15 в 11.
p = render_result('Амур', 'Нефтехимик', 1, 0, 'out/2909/result_amur_neftekhimik.png',
                  verdict='ТОТАЛ МЕНЬШЕ 5.5 · КЭФ 1.73 — ЗАШЁЛ', verdict_color=GREEN_HIT,
                  when='ВТ 29.09 · ХАБАРОВСК · РЕГУЛЯРНЫЙ ЧЕМПИОНАТ КХЛ',
                  home_info=team_info(9, 9, 'WLLWW'),
                  away_info=team_info(11, 15, 'LWWWL'))
Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
os.remove(p)
print('готово')
