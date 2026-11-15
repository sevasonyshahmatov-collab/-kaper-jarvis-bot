# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-15/picks_nhl.json — прогнозы НХЛ на 15.11 (игровой день)."""
import json

D = '2026-11-15'
DATE = '16 ноября'
N0 = 5
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1511-%d' % (N0 + i)
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на ночь на 16 ноября</b> — 5 матчей\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nВажно: ни одна ставка дня не прошла порог «ВЫБОР» НХЛ (65 %, инд. тотал и фора — 60 %) — все 5 постов ниже порога, '
        'взята самая вероятная ставка с кэфом от 1,6. Вероятности: Эдмонтон итоговая 56,8 %, Флорида Х2 59,2 %, Анахайм — Калгари ТМ 6,5 53,6 %, '
        'Вегас ИТБ 3,5 58,4 %, Нэшвилл итоговая 61,7 %. Анахайм — Калгари: замена ради разных видов ставок (самая вероятная там — итоговая '
        'Анахайма 1,70, 56,1 %). Кэфы — Фонбет; инд. тотал Вегаса у Фонбета нет — кэф Pinnacle 1,60. У Даллас — Флорида, Анахайм — Калгари, '
        'Сан-Хосе — Нэшвилл нет линии Pinnacle (вероятность только по модели). Стартовые вратари не подтверждены (кроме Владара) — в постах вратари не названы стартерами.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
