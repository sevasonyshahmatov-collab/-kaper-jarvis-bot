# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-13/picks_khl.json — прогнозы КХЛ на 12.11."""
import json

D = '2026-11-13'
DATE = '13 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1311-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 13 ноября</b> — 3 матча\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nСеверсталь и Торпедо — «ВЫБОР» расчёта (59,4 и 58,3 %). СКА — замена ради разнообразия: «ВЫБОР» там Динамо Минск не проиграет в осн. время, 1,77 (58,6 %) — та же ставка, что у Трактора; взял следующую другого вида — итоговая победа СКА, 1,65 (53,8 %). Хотите по расчёту — поправьте пост 1311-3 на Х2 Динамо Минск 1,77. Ниже порога «ВЫБОР» по своей вероятности — только этот пост. Кэфы — Фонбет (Pinnacle: Трактор Х2 — 1,62; Лада +1,5 — 1,78; СКА итоговая — 1,69). Вратари КХЛ не подтверждены — в постах их нет. Выход: два матча в 19:00 — посты в 17:30, СКА в 19:30 — в 18:00.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
