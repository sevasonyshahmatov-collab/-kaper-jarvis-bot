import os
from PIL import Image
from poster import team_info, BANNER
from recap import render_result, render_hits, GREEN_HIT

# 1. Динамо Москва 1:2 ОТ Трактор — отдельный баннер, тотал меньше 5.5 за 1.80
p1 = render_result('Динамо Москва', 'Трактор', 1, 2, 'out/2909/result_dinamo_traktor.png',
                   verdict='ТОТАЛ МЕНЬШЕ 5.5 · КЭФ 1.80 — ЗАШЁЛ', verdict_color=GREEN_HIT,
                   when='ПН 28.09 · МОСКВА · ПОБЕДА ТРАКТОРА В ОВЕРТАЙМЕ',
                   home_info=team_info(11, 11, 'LLXLO'),
                   away_info=team_info(8, 6, 'LLWLX'))

# 2. Два других прогноза вместе, экспресс 1.35 × 1.79
HITS = [
    dict(home='Торпедо', away='Салават Юлаев', score='0:3', mark='',
         pred='ТОТАЛ МЕНЬШЕ 6.5', coef=1.35, ok=True),
    dict(home='Шанхайские Драконы', away='Сочи', score='4:1', mark='',
         pred='ШАНХАЙ ФОРА (0)', coef=1.79, ok=True),
]
p2 = render_hits(HITS, 'out/2909/hits_2809_pair.png', '28.09',
                 colors=(BANNER['Салават Юлаев'], BANNER['Шанхайские Драконы']),
                 express=1.35 * 1.79)

for p in (p1, p2):
    Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
    os.remove(p)
print('экспресс %.2f' % (1.35 * 1.79))
