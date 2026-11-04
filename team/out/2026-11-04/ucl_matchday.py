"""«Матчи дня» — Лига чемпионов 04.11 (время МСК), общий постер → out/ucl0411/."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path[:0] = [os.path.join(ROOT, 'team', 'daily'), os.path.join(ROOT, 'render')]
os.environ.setdefault('JARVIS_S', '2')
import matchday_vs as mv
import banner
from PIL import Image
M = [('АЕК', 'Реал Мадрид', '20:45'), ('Фенербахче', 'Ливерпуль', '20:45'),
     ('Боруссия Дортмунд', 'Бетис', '23:00'), ('Порту', 'Наполи', '23:00'), ('Ланс', 'Комо', '23:00'),
     ('ПСВ', 'Брюгге', '23:00'), ('РБ Лейпциг', 'Манчестер Сити', '23:00'), ('Славия Прага', 'Арсенал', '23:00'),
     ('Викинг', 'Сабах', '23:00')]
items = [dict(home=h, away=a, time=t, odds=None, league='FOOT') for h, a, t in M]
OUT = os.path.join(ROOT, 'out', 'ucl0411')
os.makedirs(OUT, exist_ok=True)
sizes = [len(items)]            # владелец 04.11: один общий постер на все матчи
i = 0
for k, n in enumerate(sizes):
    p = os.path.join(OUT, 'matchi_%d.jpg' % (k + 1))
    mv.render(items[i:i + n], p, league='FOOT-RU', title='ЛИГА ЧЕМПИОНОВ', date_title='среда, 4 ноября', cont=k > 0, rows=max(sizes))
    with Image.open(p) as im:
        if im.width != mv.W:
            im.convert('RGB').resize((mv.W, round(im.height * mv.W / im.width)), Image.LANCZOS).save(p, quality=92, optimize=True)
    print(p)
    i += n
