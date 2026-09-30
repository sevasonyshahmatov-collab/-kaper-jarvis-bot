import os
os.makedirs('out/2509', exist_ok=True)
from PIL import Image
from poster import team_info
from recap import render_result, GREEN_HIT

# Трактор — СКА, 25.09: 3:4 в основное время. Ставка канала — СКА фора (0), зашла.
p = render_result('Трактор', 'СКА', 3, 4, 'out/2509/result_traktor_ska.png',
                  verdict='СКА ФОРА (0) — ЗАШЁЛ', verdict_color=GREEN_HIT,
                  when='ПТ 25.09 · ЧЕЛЯБИНСК · РЕГУЛЯРНЫЙ ЧЕМПИОНАТ КХЛ',
                  home_info=team_info(7, 4, 'OLLWL'),
                  away_info=team_info(7, 12, 'XLWWW'))
Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
print('готово')
