import os
os.makedirs('out/2909', exist_ok=True)
from PIL import Image
from poster import render_cards, team_info, TEAMS
from recap import render_slate, render_hits

# --- 1. Прогнозы за 28.09: все три зашли ---
HITS = [
    dict(home='Динамо Москва', away='Трактор', score='1:2', mark='ОТ',
         pred='ТОТАЛ МЕНЬШЕ 5.5', coef=None, ok=True),
    dict(home='Торпедо', away='Салават Юлаев', score='0:3', mark='',
         pred='ТОТАЛ МЕНЬШЕ 6.5', coef=1.35, ok=True),
    dict(home='Шанхайские Драконы', away='Сочи', score='4:1', mark='',
         pred='ШАНХАЙ ФОРА (0)', coef=1.79, ok=True),
]
p1 = render_hits(HITS, 'out/2909/hits_2809.png', '28.09', H=760)

# --- 2. Матчи 29.09 ---
M = [
    ('Амур', 'Нефтехимик', 'ВТ 29.09 · 12:00 МСК', (2.42, 4.21, 2.70), (8, 7, 'WWLLW'), (10, 15, 'LLWWW')),
    ('ЦСКА', 'СКА', 'ВТ 29.09 · 19:30 МСК', (1.90, 4.30, 3.40), (9, 12, 'WWXWW'), (8, 14, 'LWWWW')),
]
paths = [p1]
for h, a, when, o, ih, ia in M:
    info = dict(when=when, odds=o, home=team_info(*ih), away=team_info(*ia))
    slug = '%s_%s' % (TEAMS[h][0], TEAMS[a][0])
    paths.append(render_cards(h, a, info, 'out/2909/card_%s.png' % slug))
    print(h, '—', a, '|', info['home']['line'], '/', info['away']['line'])

# --- 3. Афиша дня ---
paths.append(render_slate([dict(home=h, away=a, when=w.split('· ')[1], odds=o) for h, a, w, o, _, _ in M],
                          'out/2909/afisha_2909.png', date_title='вторник, 29 сентября'))

for p in paths:
    Image.open(p).convert('RGB').save(p.replace('.png', '.jpg'), quality=95, subsampling=0, optimize=True)
    os.remove(p)
print('готово')
