# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-16/picks_khl.json — прогнозы КХЛ на 16.11."""
import json

D = '2026-11-16'
DATE = '16 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1611-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 16 ноября</b> — 3 матча\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nКэфы — Фонбет. «ВЫБОР» расчёта: Адмирал фора +1,5 (62,7 %; Pinnacle 1,58), Локомотив — Сочи ТМ 5,5 (65,5 %; Pinnacle 1,56). ЦСКА — Амур — «ВАРИАНТ» вместо «ВЫБОР» ради разных видов ставок: «ВЫБОР» там фора Амура +1,5 1,88 (56,0 %) — тот же вид, что у Адмирала; взял ТМ 4,5 за 2,10 (53,8 %; Pinnacle 1,96): у Амура меньше 5 шайб в 18 матчах из 25. Ниже порога «ВЫБОР» постов нет. Обе октябрьские встречи Локомотив — Сочи были крупными (6:3, 6:2) — в посте это сказано. Вратари КХЛ не подтверждены — в постах их нет.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
