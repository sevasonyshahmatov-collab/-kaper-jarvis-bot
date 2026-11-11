# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-11/picks_khl.json — прогнозы КХЛ на 10.11."""
import json

D = '2026-11-11'
DATE = '11 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1111-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 11 ноября</b> — 3 матча\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nДва поста — «ВЫБОР» расчёта: Сочи — Лада ТМ 5,5 (61,1 %), ЦСКА — Торпедо фора Торпедо +1,5 (65,5 %; у Фонбета 1,70, Pinnacle 1,54). В СКА — Динамо Москва «ВЫБОР» был тоже ТМ 5,5 (57,7 %, 1,70) — второй тотал меньше за день, поэтому взял «Динамо не проиграет в осн. время» (56,4 %, 1,75; Pinnacle 1,70): ниже порога «ВЫБОР», в посте без пометок. Кэфы — Фонбет. Все три матча в 19:30 — посты выйдут в 18:00.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
