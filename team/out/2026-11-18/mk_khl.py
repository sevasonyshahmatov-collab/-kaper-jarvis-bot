# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-18/picks_khl.json — прогнозы КХЛ на 18.11."""
import json

D = '2026-11-18'
DATE = '18 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1811-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 18 ноября</b> — 5 матчей\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nКэфы — Фонбет. Все ставки — «ВЫБОР» расчёта, кроме первой: Авангард — Адмирал «ВЫБОР» был ТМ 5,5 за 1,70 (56,3 %), взял «ВАРИАНТ» фору Адмирала +1,5 за 1,90 (54,9 %; Pinnacle 1,92), чтобы не было двух ТМ 5,5 подряд. Вероятности: Салават Юлаев — Барыс ТМ 5,5 59,1 % (Pinnacle 1,64), Северсталь — Сочи ТБ 4,5 59,5 % (Pinnacle 1,69), Амур Х2 62,0 % (Pinnacle 1,55), Локомотив Х2 60,2 % (Pinnacle 1,65). Ниже порога «ВЫБОР» постов нет. Самая уверенная ставка дня — Амур Х2. Вратари КХЛ не подтверждены — в постах их нет.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
