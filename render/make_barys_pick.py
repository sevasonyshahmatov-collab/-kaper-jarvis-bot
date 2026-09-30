import os
os.makedirs('out/2609/khl', exist_ok=True)
from PIL import Image
from poster import team_info
from side_pick import render_side_pick

# Матч перенесён с 25.09 на 26.09, 11:00 МСК. Обе команды с 25-го не играли,
# поэтому очки и форма те же: Барыс 10 в 7, Нефтехимик 11 в 8.
b = team_info(7, 10, 'LWLWW')
n = team_info(8, 11, 'WWLLW')
M = dict(
    home=dict(team='Барыс', name='БАРЫС', line=b['line'], form=b['form']),
    away=dict(team='Нефтехимик', name='НЕФТЕХИМИК', line=n['line'], form=n['form']),
    when='СБ 26.09 · 11:00 МСК',
    pred='ПОБЕДА БАРЫСА С ОТ И БУЛЛИТАМИ',
    coef=1.75,
)
p = render_side_pick(M, 'out/2609/khl/pick_barys_neftekhimik.png', tag='KXL')
Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
print('готово:', b['line'], '/', n['line'])
