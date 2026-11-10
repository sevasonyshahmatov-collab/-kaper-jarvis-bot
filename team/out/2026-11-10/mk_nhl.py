# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-10/picks_nhl.json — прогнозы НХЛ, игровой день 10.11 (ночь на 11.11), данные run 1168."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

D = '2026-11-10'
N0 = 16
posts, summary = [], []
for i, (h, a, dt, t, bet, k, pr, odds, q, end) in enumerate(P):
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (dt, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': '1011-%d' % (N0 + i),
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': dt, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на ночь на 11 ноября</b> — 7 матчей\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nПорог «ВЫБОР» НХЛ прошёл один матч: Миннесота ИТБ 2,5 (63,0 %), кэф 1,61 — Pinnacle, у Фонбета инд. тоталов нет. '
        'Остальные 6 ниже порога (56–61 %): самая вероятная ставка с кэфом от 1,6. '
        'Сент-Луис ИТБ 2,5 — тоже кэф Pinnacle. '
        'Оттава — Вашингтон: ТБ 5,5 1,65 (61,2 %) вместо ИТБ Оттавы 1,60 (62,9 %, только Pinnacle); '
        'Коламбус — Флорида: ТБ 5,5 1,75 (56,4 %) вместо ИТБ Флориды 1,68 (58,2 %, только Pinnacle) — чтобы ставка была у Фонбета и не три инд. тотала за ночь. '
        'Первые матчи в 03:00 — пост выйдет в 23:00, если нажать до этого.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, p in enumerate(posts):
        print(i + 1, len(p['text']), len(P[i][8]))
