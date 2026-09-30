import os; os.makedirs("out/2309", exist_ok=True)
from poster import render_clean, render_cards, team_info, TEAMS

# КХЛ, среда 23.09.2026. Коэффициенты — линия в основное время (legalbet, маржа ~1-2%).
# Форма: последние 5 матчей, слева старые → справа свежие.
# W — победа в основное время, L — поражение в основное время,
# X — победа в ОТ/буллитах, O — поражение в ОТ/буллитах.
M = [
    # Амур — ЦСКА
    ('Амур', 'ЦСКА', 'СР 23.09 · 12:00 МСК', (4.03, 4.33, 1.85),
     (6, 5, 'OLWWL'), (7, 8, 'LLWWX')),
    # Адмирал — Локомотив
    ('Адмирал', 'Локомотив', 'СР 23.09 · 12:30 МСК', (5.00, 4.62, 1.68),
     (7, 6, 'WLLWO'), (7, 12, 'XWWWL')),
    # Салават Юлаев — Металлург Мг
    ('Салават Юлаев', 'Металлург', 'СР 23.09 · 17:00 МСК', (3.22, 4.32, 2.13),
     (6, 9, 'WLOWW'), (7, 11, 'XOLWW')),
    # Нефтехимик — Лада
    ('Нефтехимик', 'Лада', 'СР 23.09 · 19:30 МСК', (1.81, 4.50, 4.00),
     (7, 9, 'WWWLL'), (7, 5, 'OLWLO')),
]

for h, a, when, o, ih, ia in M:
    info = dict(when=when, odds=o, home=team_info(*ih), away=team_info(*ia))
    slug = '%s_%s' % (TEAMS[h][0], TEAMS[a][0])
    render_cards(h, a, info, 'out/2309/card_%s.png' % slug)
    render_clean(h, a, info, 'out/2309/side_%s.png' % slug)
    print(h, '—', a, '|', info['home']['line'], '/', info['away']['line'])
