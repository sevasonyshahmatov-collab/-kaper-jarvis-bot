# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-15/picks_khl.json — прогнозы КХЛ на 15.11."""
import json

D = '2026-11-15'
DATE = '15 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1511-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 15 ноября</b> — 4 матча\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nКэфы — Фонбет. «ВЫБОР» расчёта: Сибирь 1Х (57,1 %), Барыс фора +1,5 (64,9 %; у Pinnacle 1,67 — Фонбет даёт заметно выше), СКА — Трактор ТМ 5,5 (56,8 %). Торпедо — Динамо Минск — замена ради разных видов ставок: «ВЫБОР» там Х2 Динамо Минск 1,75 (56,5 %) — тот же вид, что у Сибири; взял итоговую победу Торпедо 1,67 (56,3 %, почти вровень). Запасной вариант по СКА — Трактор: Х2 Трактор 1,85 (55,2 %, «ВАРИАНТ»). Ниже порога «ВЫБОР» постов нет. Pinnacle: 1Х Сибирь 1,70; итоговая Торпедо 1,66; ТМ 5,5 — 1,66. Вратари КХЛ не подтверждены — в постах их нет.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
