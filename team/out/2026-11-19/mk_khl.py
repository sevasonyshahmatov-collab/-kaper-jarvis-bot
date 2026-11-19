# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-19/picks_khl.json — прогнозы КХЛ на 19.11."""
import json

D = '2026-11-19'
DATE = '19 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1911-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 19 ноября</b> — 3 матча\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nКэфы — Фонбет, все три ставки — «ВЫБОР» расчёта. Вероятности: фора Трактора +1,5 — 63,8 % (Pinnacle 1,56), Спартак Х2 — 63,2 % (Pinnacle 1,52), Нефтехимик 1Х — 59,1 % (Pinnacle 1,63). Ниже порога «ВЫБОР» постов нет. Два двойных шанса в один день (на хозяев и на гостей): ставка другого вида там на 6–10 п. п. менее вероятна — оставил «ВЫБОР». Самая уверенная ставка дня — фора Трактора. Вратари КХЛ не подтверждены — в постах их нет.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
