import os
from PIL import Image
import poster
from poster import team_info
from recap import render_result, GREEN_HIT

poster.BANNER['Металлург'] = (30, 48, 92)   # тот же синий, что на предматчевом баннере

# Авангард 1:5 Металлург в основное время. После матча: Авангард 8 очков в 9, Металлург 17 в 10.
p = render_result('Авангард', 'Металлург', 1, 5, 'out/2809/result_avangard_metallurg.png',
                  verdict='ДВОЙНОЙ ШАНС Х2 — ЗАШЁЛ', verdict_color=GREEN_HIT,
                  when='ПН 28.09 · ОМСК · РЕГУЛЯРНЫЙ ЧЕМПИОНАТ КХЛ',
                  home_info=team_info(9, 8, 'XLLXL'),
                  away_info=team_info(10, 17, 'WWXWW'))
Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
os.remove(p)
print('готово')
