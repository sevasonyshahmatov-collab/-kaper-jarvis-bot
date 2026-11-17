# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-17/picks_khl.json — прогнозы КХЛ на 16.11."""
import json

D = '2026-11-17'
DATE = '17 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1711-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 17 ноября</b> — 5 матчей\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nКэфы — Фонбет. «ВЫБОР» расчёта: Автомобилист — Спартак ТМ 5,5 (61,4 %; Pinnacle 1,61), Динамо Минск Х2 (64,8 %; Pinnacle 1,51), Динамо Москва Х2 (56,9 %; Pinnacle 1,71). '
        'Сибирь — Трактор: «ВЫБОР» был 1Х Сибирь 1,65 (57,6 %) — третий двойной шанс за день, взял итоговую победу Трактора 1,77 (55,4 %; Pinnacle 1,85). '
        'Лада — Металлург: «ВАРИАНТ» фора Лады +1,5 за 2,00 (51,2 %; Pinnacle 1,89) вместо «ВЫБОР» ТМ 5,5 1,85 (53,7 %) — второго тотала меньше. '
        'Ниже порога «ВЫБОР» постов нет; день ровный, сильных перевесов нет — самая уверенная ставка Динамо Минск Х2. Вратари КХЛ не подтверждены — в постах их нет.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
