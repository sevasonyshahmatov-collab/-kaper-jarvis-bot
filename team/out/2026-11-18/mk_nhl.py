# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-18/picks_nhl.json — прогнозы НХЛ на 18.11 (игровой день)."""
import json

D = '2026-11-18'
DATE = '19 ноября'
N0 = 6
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1811-%d' % (N0 + i)
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на ночь на 19 ноября</b> — 3 матча\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nПорог «ВЫБОР» НХЛ прошла одна ставка — инд. тотал Колорадо больше 2,5 (63,5 %, кэф Pinnacle: у Фонбета инд. тоталов нет). '
        'Два поста ниже порога, самая вероятная ставка с кэфом от 1,6: Нью-Джерси итоговая 60,0 %; Детройт — Бостон ТБ 5,5 53,7 % '
        '(самая вероятная там — инд. тотал Детройта больше 2,5, 56,2 %, но у Фонбета его нет и был бы второй инд. тотал за ночь; '
        'учти: у Детройта подтверждён Тарасов, 93,1 % отражённых). У Бостона второй матч за два вечера.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
