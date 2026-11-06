# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-06/picks_nhl.json — прогнозы НХЛ на ночь на 07.11 (данные: run 977)."""
import json

D = '2026-11-06'
DATE = '7 ноября'
N0 = 7
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '0611-%d' % (N0 + i)
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на 7 ноября (ночь)</b> — 3 матча\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nВсе три ставки ниже порога «ВЫБОР» НХЛ (65 %, у инд. тотала и форы +1,5 — 60 %): 60,0 / 61,9 / 62,0 %. Взял самую вероятную с кэфом от 1,6, кэфы — Фонбет. '
        'Баффало — Коламбус: самая вероятная была ТМ 6,5 (61,6 %, 1,65), но чтобы не ставить два тотала в один день, взял итоговую победу Баффало (60,0 %). '
        'В линии всего 3 матча.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
