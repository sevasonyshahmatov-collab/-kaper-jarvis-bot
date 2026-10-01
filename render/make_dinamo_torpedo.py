import os
os.makedirs('out/dinamo_torpedo', exist_ok=True)
from PIL import Image
import poster
from poster import render_cards

# Торпедо рядом с Динамо — оба синие; уводим Торпедо в красный из эмблемы.
poster.BANNER['Торпедо'] = (176, 24, 40)

# Без даты, кэфов и формы — их нет в данных; подставить в info['when'/'odds'] и team_info(...) при появлении.
info = dict(when='КХЛ · РЕГУЛЯРНЫЙ ЧЕМПИОНАТ', home={}, away={})
p = render_cards('Динамо Москва', 'Торпедо', info, 'out/dinamo_torpedo/banner_dinamo_torpedo.png')
Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
os.remove(p)
print('готово')
