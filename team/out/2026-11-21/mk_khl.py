# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-21/picks_khl.json — прогнозы КХЛ на 21.11."""
import json

D = '2026-11-21'
DATE = '21 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '2111-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 21 ноября</b> — 2 матча\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nВ субботу в КХЛ только два матча. Кэфы — Фонбет, у обоих матчей есть линии Фонбета и Pinnacle. Обе ставки — «ВЫБОР» расчёта, ниже порога — 0. Вероятности: ТБ 4,5 Нефтехимик — Спартак — 59,9 % (Pinnacle 1,57); фора Сочи +1,5 — 56,7 % (Pinnacle 1,68). В Нижнекамске рядом итоговая победа Спартака 1,72 (59,0 %), но у Спартака в овертаймах и буллитах 1 победа из 6 — оставил тотал. Вратари КХЛ не подтверждены — в постах их нет.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
