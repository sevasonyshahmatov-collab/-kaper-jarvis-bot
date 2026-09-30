import os
os.makedirs('out/2609/khl', exist_ok=True)
from PIL import Image
from poster import team_info
from recap import render_cards_pick, render_result, GREEN_HIT

# ДО матча: Металлург 13 очков в 8 играх (23.09 победа в ОТ у Салавата),
# Ак Барс 13 в 9 (три последние победы — в овертаймах и по буллитам).
pre = dict(when='СБ 26.09 · 14:30 МСК',
           pred='ТОТАЛ БРОСКОВ БОЛЬШЕ 59.5', coef=None,
           foot='ПРОГНОЗ КАНАЛА · КХЛ, РЕГУЛЯРНЫЙ ЧЕМПИОНАТ',
           home=team_info(8, 13, 'OLWWX'), away=team_info(9, 13, 'LXLXX'))
p1 = render_cards_pick('Металлург', 'Ак Барс', 'out/2609/khl/pick_metallurg_akbars.png', pre)

# ПОСЛЕ матча: 2:1 в основное время. Металлург 15 очков в 9 играх, Ак Барс 13 в 10.
p2 = render_result('Металлург', 'Ак Барс', 2, 1, 'out/2609/khl/result_metallurg_akbars.png',
                   verdict='ТОТАЛ БРОСКОВ БОЛЬШЕ 59.5 — ЗАШЁЛ', verdict_color=GREEN_HIT,
                   when='СБ 26.09 · МАГНИТОГОРСК · РЕГУЛЯРНЫЙ ЧЕМПИОНАТ КХЛ',
                   home_info=team_info(9, 15, 'LWWXW'),
                   away_info=team_info(10, 13, 'XLXXL'))
for p in (p1, p2):
    Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
print('готово')
