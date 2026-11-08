# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-08/picks_khl.json — прогнозы КХЛ на 08.11 (данные: run 1045)."""
import json

D = '2026-11-08'
DATE = '8 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '0811-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 8 ноября</b> — 4 матча\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nВыбор расчёта — Барыс (61,1 %), Трактор (64,5 %) и фора Сочи (59,0 %). В Нефтехимике «ВЫБОР» был «Нефтехимик не проиграет в основное время» (51,2 %, 1,88) — взял «ВАРИАНТ» ТМ 4,5 (50,5 %, 2,07): вероятность почти та же, кэф выше, и двух «не проиграет» в день уже хватает. Кэфы — Фонбет (Pinnacle 1,57 · 1,91 · 1,50 · 1,63). Первый матч в 10:00 — пост выйдет в 08:30, если нажать до этого.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
